"""Kriging -- a Gaussian process whose covariance is fitted to the data, with the error bar that comes with it.

Universal kriging, in geostatistics' words (Matheron 1963; Chilès & Delfiner 2012): a series y(t) is a
linear mean X beta plus a correlated part f(t) ~ GP(0, k) plus independent jitter e ~ N(0, tau^2), the
*nugget*. The covariance k here is Matérn-3/2 -- a process that is once differentiable, so its derivative
(a velocity) exists and has a band of its own (Rasmussen & Williams 2006 §9.4; Stein 1999 on why a
Gaussian kernel would make that band overconfident). The three numbers of the covariance -- the sill s^2,
the range ell and the nugget tau^2 -- are fitted by REML (Patterson & Thompson 1971), which does not charge
the mean's fit to the noise; beta by generalised least squares; leave-one-out residuals in closed form
(Dubrule 1983); predictions with the kriging variance, the mean's own uncertainty included.

What it is for in this toolkit (the kriging survey of 2026-10-15/16, its §1 and §3): a track's speed along
it with a band (`kinematics.speed_band`), and tracks drawn from a fitted covariance to hold that band to
(`simulate`). The toolkit was already kriging in several places with a covariance nobody fitted
(`fit_v_px` is this with a pure nugget); what this adds is the same three things each time: the covariance
fitted from the data, the variance reported, and a check on data held out.

numpy and scipy only; everything is dense, since a track has at most a few thousand points and a frame
pair a few hundred patches.
"""
import math

import numpy as np
from scipy import linalg, optimize

R3 = math.sqrt(3.0)
JITTER = 1e-9           # relative, on the diagonal: a Cholesky of a covariance that is exact to the bit
TAU2_FLOOR = 1e-6       # px^2: a nugget no smaller than 0.001 px, so a drawn track that lies on its line exactly fits
MAXITER = 600
BEAT_SPAN = 1.25        # M8's beat is fitted within this factor of the rhythm it starts from
BEAT_PERIODS = 2.0      # and holds its phase over two of its periods at least: a shorter envelope is a broad bump in the spectrum, not a beat
BUDGET = 60             # evaluations a start gets before the best of the starts is run to convergence


# ---- the Matérn-3/2 covariance and its derivatives ---------------------------------------------
def matern32(r, s2, ell):
    """Cov(f(s), f(t)) for r = s - t."""
    c = R3 * np.abs(r) / ell
    return s2 * (1.0 + c) * np.exp(-c)


def matern32_d(r, s2, ell):
    """Cov(f'(s), f(t)) for r = s - t (signed)."""
    c = R3 / ell
    return -s2 * c * c * r * np.exp(-c * np.abs(r))


def matern32_dd(r, s2, ell):
    """Cov(f'(s), f'(t)) for r = s - t: 3 s^2 / ell^2 at r = 0, the prior variance of the velocity."""
    c = R3 / ell
    a = c * np.abs(r)
    return s2 * c * c * (1.0 - a) * np.exp(-a)


def beat32(r, s2, ell, hz):
    """The quasi-periodic covariance (M8): the Matérn-3/2 times cos 2 pi hz r. A covariance by Schur's product theorem
    (the product of two is one), its spectrum the Matérn's shifted to +-hz (Bochner): a rhythm at hz whose phase and
    amplitude drift over ell, as a wingbeat's do -- the kernel astronomy fits to a star's rotation."""
    return matern32(r, s2, ell) * np.cos(2.0 * math.pi * hz * r)


def covariance(D, theta):
    """The covariance of the series without its nugget, at the signed time differences D: the wander's Matérn-3/2,
    theta = (s2, ell, tau2); with M8's beat beside it where theta = (s2, ell, tau2, s2_beat, ell_beat, hz); and with
    the beat's first harmonic at 2 hz too, on the same envelope, where a seventh number is its sill (a wingbeat's trace
    is no sine: Galileo flyer 5's beat came as a pair, 3.9 and 7.8 Hz)."""
    K = matern32(D, theta[0], theta[1]) if theta[0] > 0 else np.zeros_like(D, dtype=float)
    if len(theta) > 3 and theta[3] > 0:
        K = K + beat32(D, theta[3], theta[4], theta[5])
    if len(theta) > 6 and theta[6] > 0:
        K = K + beat32(D, theta[6], theta[4], 2.0 * theta[5])
    return K


def _nugget(K, theta):
    """K with the nugget (and a jitter relative to the whole variance) on its diagonal, in place."""
    K[np.diag_indices_from(K)] += theta[2] + JITTER * (theta[0] + theta[2] + sum(theta[i] for i in (3, 6) if len(theta) > i))
    return K


def _chol(K):
    try:
        return linalg.cho_factor(K, lower=True, check_finite=False)
    except linalg.LinAlgError:
        return None


def _design(t, tm):
    """The linear mean: an intercept and a slope about tm."""
    return np.c_[np.ones(len(t)), np.asarray(t, float) - tm]


# ---- the restricted likelihood ------------------------------------------------------------------
def reml(y, X, D, theta):
    """-2 log restricted likelihood (up to a constant) of theta = (s2, ell, tau2) on the series y with
    design X and signed time differences D; and the pieces a prediction reuses. (inf, None) where the
    covariance cannot be factored."""
    K = _nugget(covariance(D, theta), theta)
    L = _chol(K)
    if L is None:
        return math.inf, None
    Ki_X = linalg.cho_solve(L, X, check_finite=False)
    Ki_y = linalg.cho_solve(L, y, check_finite=False)
    A = X.T @ Ki_X
    LA = _chol(A)
    if LA is None:
        return math.inf, None
    beta = linalg.cho_solve(LA, X.T @ Ki_y, check_finite=False)
    r = y - X @ beta
    Ki_r = linalg.cho_solve(L, r, check_finite=False)
    val = 2.0 * np.log(np.diag(L[0])).sum() + 2.0 * np.log(np.diag(LA[0])).sum() + float(r @ Ki_r)
    return float(val), dict(L=L, LA=LA, beta=beta, Ki_r=Ki_r, A=A, Ki_X=Ki_X)


def white(y, X):
    """The line + white model in closed form: (tau2, -2 log REL on reml()'s scale, beta, the slope's
    standard error). REML's tau2 is RSS / (n - p): the mean's p parameters are not charged to the noise."""
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    r = y - X @ beta
    n, p = X.shape
    tau2 = max(float(r @ r) / max(n - p, 1), TAU2_FLOOR)
    XtX = X.T @ X
    val = (n - p) * math.log(tau2) + float(np.linalg.slogdet(XtX)[1]) + float(r @ r) / tau2
    se = math.sqrt(max(np.linalg.inv(XtX)[1, 1] * tau2, 0.0)) if p > 1 else None
    return tau2, val, beta, se


def fit(y, X, D, dt, span, starts=None, budget=BUDGET, beat=None, harmonic=False):
    """theta = (s2, ell, tau2) by REML, searched in logs (Nelder-Mead) from three starts (the range at a
    tenth, a third and a thirtieth of the span), each bounded: the range between one sample step and five
    spans, the sill and the nugget between TAU2_FLOOR and ten thousand times the residual variance. Each
    start gets `budget` evaluations, and the best of them is then run to convergence: the likelihood is
    multimodal in the range (a long wander against a short one), and the three starts find which, but
    each need not be polished. A single start given (`starts`, in logs: a warm start) is run to
    convergence alone. With `beat` (Hz), M8's beat is fitted beside the wander: theta = (s2, ell, tau2, s2_beat,
    ell_beat, hz), the beat's sill bounded as the others, its range between BEAT_PERIODS periods and five spans, its rate
    within a quarter of `beat` (a periodogram's peak, `kinematics.backtest`'s rhythm), and with `harmonic` its first
    harmonic's sill a seventh number; `starts` are then needed.
    Returns (theta, -2 log REL, pieces)."""
    y, X = np.asarray(y, float), np.asarray(X, float)
    var = max(float(np.var(y - X @ np.linalg.lstsq(X, y, rcond=None)[0])), TAU2_FLOOR)
    lo = np.log([TAU2_FLOOR, dt, TAU2_FLOOR])
    hi = np.log([1e4 * var, 5.0 * span + dt, 1e4 * var])
    if beat:
        lo = np.r_[lo, np.log([TAU2_FLOOR, BEAT_PERIODS / beat, beat / BEAT_SPAN])]
        hi = np.r_[hi, np.log([1e4 * var, 5.0 * span + dt, beat * BEAT_SPAN])]
        if harmonic:
            lo, hi = np.r_[lo, math.log(TAU2_FLOOR)], np.r_[hi, math.log(1e4 * var)]

    def f(p):
        p = np.asarray(p)
        if (p < lo).any() or (p > hi).any():
            return math.inf
        return reml(y, X, D, tuple(np.exp(p)))[0]

    polish = dict(xatol=1e-3, fatol=1e-5, maxiter=MAXITER * (2 if beat else 1))
    if starts is None:
        starts = [np.log([var * a, max(span * b, dt), var * c]) for a, b, c in
                  ((0.5, 0.1, 0.5), (0.9, 0.33, 0.1), (0.2, 0.033, 0.8))]
    best = None
    for p0 in starts:
        res = optimize.minimize(f, np.clip(p0, lo, hi), method="Nelder-Mead",
                                options=polish if len(starts) == 1 else dict(polish, maxfev=budget))
        if best is None or res.fun < best.fun:
            best = res
    if len(starts) > 1:
        best = optimize.minimize(f, best.x, method="Nelder-Mead", options=polish)
    theta = tuple(float(v) for v in np.exp(best.x))
    val, pc = reml(y, X, D, theta)
    return theta, val, pc


def loo(y, X, D, theta):
    """Exact leave-one-out residuals and their kriging sd (the mean re-estimated each time): (e, s)."""
    K = _nugget(covariance(D, theta), theta)
    Ki = linalg.pinvh(K)
    Ki = (Ki + Ki.T) / 2
    KiX = Ki @ X
    P = Ki - KiX @ linalg.solve(X.T @ KiX, KiX.T)
    d = np.maximum(np.diag(P), 1e-300)
    return (P @ y) / d, 1.0 / np.sqrt(d)


# ---- a fitted model, and what it predicts ------------------------------------------------------
class Model:
    """One coordinate of a series against time, fitted (or given theta): y = beta0 + beta1 (t - tm) + f(t) + e.

    `predict(ts, "f")` is the latent position (no nugget) at new times, `predict(ts, "df")` its rate;
    each returns (mean, variance) with the mean's own uncertainty in the variance; `joint` the same with
    the full covariance of the predicted values."""

    def __init__(self, t, y, tm, theta=None, dt=None, warm=None, beat=None, harmonic=False):
        self.t, self.y, self.tm = np.asarray(t, float), np.asarray(y, float), float(tm)
        self.X = _design(self.t, self.tm)
        self.D = self.t[:, None] - self.t[None, :]
        span = float(self.t[-1] - self.t[0]) if len(self.t) > 1 else 1.0
        dt = dt or (float(np.min(np.diff(self.t))) if len(self.t) > 1 else 1.0)
        if theta is None:
            if beat and harmonic:                 # the beat as fitted alone (`warm`, six numbers), its harmonic from a share of it
                starts = [np.log(list(warm[:6]) + [warm[3] * a]) for a in (0.25, 0.05)]
            elif beat:                            # the wander as fitted alone (`warm`), the beat from a share of its nugget
                s2, ell, tau2 = (tuple(warm) + (None,) * 3)[:3] if warm is not None else (None,) * 3
                var = float(np.var(self.y - self.X @ np.linalg.lstsq(self.X, self.y, rcond=None)[0]))
                s2, ell, tau2 = s2 or var, ell or span / 3.0, tau2 or var / 10.0
                starts = [np.log([s2, ell, tau2 * a, tau2 * b, c / beat, beat]) for a, b, c in
                          ((0.5, 0.5, 4.0), (0.2, 1.0, 10.0), (0.5, 0.2, 2.5))]
            else:
                starts = [np.log(np.asarray(warm, float))] if warm is not None else None
            self.theta, self.val, self.pc = fit(self.y, self.X, self.D, dt, span, starts=starts, beat=beat, harmonic=harmonic)
        else:
            self.theta = tuple(float(v) for v in theta)
            self.val, self.pc = reml(self.y, self.X, self.D, self.theta)
        self.white = white(self.y, self.X)             # (tau2, val, beta, se_slope): the line + white alternative

    @property
    def dlnl(self):
        """The log-likelihood gain of the fitted covariance over a line with white jitter (both REML, the
        same mean): the evidence that the series wanders about its line beyond independent jitter."""
        return (self.white[1] - self.val) / 2.0 if self.pc is not None else None

    def _cross(self, ts, what):
        ts = np.atleast_1d(np.asarray(ts, float))
        s2, ell = self.theta[:2]                  # the wander's alone: M8's beat is read as the noise around it
        r = ts[:, None] - self.t[None, :]
        if what == "f":
            return ts, matern32(r, s2, ell), _design(ts, self.tm), np.full(len(ts), s2)
        return ts, matern32_d(r, s2, ell), np.c_[np.zeros(len(ts)), np.ones(len(ts))], np.full(len(ts), 3.0 * s2 / ell ** 2)

    def predict(self, ts, what="f"):
        ts, ks, Xs, kss = self._cross(ts, what)
        L, LA, beta, Ki_r = self.pc["L"], self.pc["LA"], self.pc["beta"], self.pc["Ki_r"]
        mean = Xs @ beta + ks @ Ki_r
        Ki_ks = linalg.cho_solve(L, ks.T, check_finite=False)
        v = kss - np.einsum("ij,ji->i", ks, Ki_ks)
        R = Xs.T - self.X.T @ Ki_ks
        v = v + np.einsum("ij,ij->j", R, linalg.cho_solve(LA, R, check_finite=False))
        return mean, np.maximum(v, 0.0)

    def joint(self, ts, what="f"):
        ts, ks, Xs, _ = self._cross(ts, what)
        s2, ell = self.theta[:2]
        rr = ts[:, None] - ts[None, :]
        Kss = matern32(rr, s2, ell) if what == "f" else matern32_dd(rr, s2, ell)
        L, LA, beta, Ki_r = self.pc["L"], self.pc["LA"], self.pc["beta"], self.pc["Ki_r"]
        mean = Xs @ beta + ks @ Ki_r
        Ki_ks = linalg.cho_solve(L, ks.T, check_finite=False)
        C = Kss - ks @ Ki_ks
        R = Xs.T - self.X.T @ Ki_ks
        C = C + R.T @ linalg.cho_solve(LA, R, check_finite=False)
        return mean, C

    def loo(self):
        """Leave-one-out z-scores of the fitted model, one a point."""
        e, s = loo(self.y, self.X, self.D, self.theta)
        return e / s

    def innovations(self):
        """The one-step innovations, in time order: the GLS residual whitened by the Cholesky factor of the fitted
        covariance, L^-1 (y - X beta) -- each point's error predicting it from the points before it, over that
        prediction's own sd (the prediction-error decomposition: Harvey 1989). Independent N(0, 1) where the model
        is the track's, so what is left in them is what the model missed (`kinematics.backtest`)."""
        return linalg.solve_triangular(self.pc["L"][0], self.y - self.X @ self.pc["beta"], lower=True, check_finite=False)


# ---- drawing from a covariance -----------------------------------------------------------------
def simulate(t, theta, rng, nugget=True):
    """A draw of (y, f, f') at the times t from the covariance theta = (s2, ell, tau2) about a zero mean:
    the correlated part f and its rate f' drawn together from their joint covariance, the nugget added to
    y where asked. The unconditional simulation of geostatistics (Journel 1974): a track that has the
    fitted covariance, into which a known velocity or acceleration can then be put (`kinematics.simulate_track`).
    With M8's beat in theta (six numbers) a beat is drawn apart and added to y, f and f' staying the wander's."""
    t = np.asarray(t, float)
    s2, ell, tau2 = theta[:3]
    n = len(t)
    r = t[:, None] - t[None, :]
    C = np.empty((2 * n, 2 * n))
    C[:n, :n] = matern32(r, s2, ell)
    C[n:, :n] = matern32_d(r, s2, ell)              # Cov(f'(t_i), f(t_j))
    C[:n, n:] = C[n:, :n].T
    C[n:, n:] = matern32_dd(r, s2, ell)
    C[np.diag_indices_from(C)] += JITTER * max(s2, 1e-12) * (1.0 + 3.0 / ell ** 2)
    L = np.linalg.cholesky(C)
    z = L @ rng.standard_normal(2 * n)
    f, df = z[:n], z[n:]
    y = f + (math.sqrt(tau2) * rng.standard_normal(n) if nugget and tau2 > 0 else 0.0)
    if len(theta) > 3 and theta[3] > 0:
        B = covariance(r, (0.0, 1.0) + tuple(theta[2:]))           # the beat (and its harmonic) alone
        B[np.diag_indices_from(B)] += JITTER * sum(theta[i] for i in (3, 6) if len(theta) > i)
        y = y + np.linalg.cholesky(B) @ rng.standard_normal(n)
    return y, f, df
