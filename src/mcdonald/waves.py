"""The sea as a ruler: metres per pixel from the dispersion of its waves.

Deep-water gravity waves obey omega^2 = g |K|: a wave's speed fixes its length in metres. Where
a clip shows the sea, every Fourier component of the sea's texture has a wavenumber in rad per
PIXEL and a measurable rate in rad per second, and the one number that turns the first into
rad per metre so that the rates obey the dispersion relation is the image scale, metres per
pixel. No field of view, no range and no telemetry enter. The sensor's or platform's motion
puts a uniform drift U (px/s) on every component, which the fit carries; an oblique view
foreshortens the along-sight axis, so the scale is m_x across and m_y = q m_x along, with
q = 1 / sin(depression) for a flat sea.

**What a component does.** With the frame s(x, t) and its 2-D Fourier transform F(k, t), a
wave travelling along +k puts the phase -(Omega(K) + k.U) t on F(k, t), and a wave travelling
along -k, which the same bin holds as the conjugate, +Omega(K) - k.U, where
K = (k_x / m_x, k_y / m_y) is the true wavenumber and Omega = sqrt(g |K|). So each bin's
spectrum in time may hold energy at two places, nu_+- = -+Omega - k.U, split by 2 Omega:
the split measures the dispersion whatever the drift, and the shape of nu(k) along one branch,
sqrt(k) against the drift's k, tells the scale from the drift when only one branch is lit.

**Two estimators, kept because they fail differently.**
- `fit_rates`: one rate per bin, the circular mean of the frame-to-frame phase steps (a
  phase vocoder), fitted to the branch on its side of a dominant direction theta0. It is sharp on
  a record of one second, where a periodogram would be 6 rad/s wide, but it assumes one wave per
  bin: bins holding waves both ways are biased.
- `fit_shell`: the periodogram of each bin's time series, evaluated at both branches (the
  dispersion shell of marine-radar practice, Young et al. 1985; Senet et al. 2001), scored by the
  share of the sea's energy that sits on the shell. Times need not be uniform (a hold-and-jump
  cadence is read at its true times). It sees both branches and so resolves a sea with waves
  both ways, but its resolution is the record's length.

**What it cannot do, and says so.** At one wavelength the dispersion term and the drift are one
number: a narrow-band swell gives a scale only with the drift assumed. The fit therefore reports
the span of |k| that carried its weight (`k_span`) and the band of scales whose score is within
reach of the best (`band_m`), and the nulls: the same frames shuffled in time (no dispersion,
the same per-frame spectra) and a drift-only model (Omega = 0). A scale is claimed only where the
band is bounded, the shell beats drift alone, and the null is well below.

The synthetic sea (`synth`) is the test bed: linear deep-water waves on a periodic world grid,
with a chosen spectrum (a broad wind sea, a narrow swell, or both), direction and spread, imaged
at m_x, q, with uniform, affine or rotating drift, perspective, a radiance that is not linear in
slope, noise, repeated frames and jittered frame times.
"""
import numpy as np
from scipy import ndimage, optimize

G = 9.81

# ---- defaults ---------------------------------------------------------------------------------
LAM_MIN = 6.0        # px: shortest wave read (under this the texture is noise and codec)
N_ANN = 12           # log-annuli of |k| in the band; the top TOP of each by amplitude are kept
TOP = 0.25
M_GRID = np.exp(np.linspace(np.log(0.004), np.log(4.0), 75))     # m/px
Q_GRID = np.exp(np.linspace(np.log(1.0), np.log(3.5), 15))      # q = 1 / sin(depression): 1 at nadir, never under
U_MAX = 150.0        # px/s: the drift box of the shell fit's first pass
N_U = 13
BAND = 0.10          # band_m: scales whose score is within this share of (best - null) of the best
MIN_SPAN = 2.0       # k_span under this: one wavelength, the scale is the drift's shadow
MIN_RESOLVE = 1.0    # the shell needs the dispersion to spread the lit bins over this many resolution elements
PEAK_SPAN_S = 3.0    # records this long read each bin's rate off its periodogram's peak; shorter ones step the phase
CODEC_FRAC = 0.45    # rates beyond this share of the Nyquist rate are the codec's (7.5 Hz on a 30-fps PURSUE clip), masked
ALIAS = 0.8          # bins whose model rate is beyond this share of the Nyquist rate are dropped from the rates fit
MIN_SHARE = 0.15     # share on the shell under this: no sea (a real thermal sea reaches 0.2-0.35: only the along-look
                     # slopes are imaged, and much of the texture is not a wave; a synthetic sea reaches 0.8)
MAX_BAND = 6.0       # a band of scales wider than this factor pins nothing
MIN_RATE_SPREAD = 0.5  # the lit bins' rates must spread (a weighted MAD, as a sigma) over this many resolution elements
                       # (shell) or MIN_RATE_SPREAD_RATES rad/s (rates): one strong wave leaks through the taper into every
                       # bin, each then lit at the one rate; a robust spread, because the faint bins' peaks are random
MIN_RATE_SPREAD_RATES = 1.0
MIN_OVER_DRIFT = 0.05  # the shell must beat drift alone by this much of the share
MIN_OVER_NULL = 2.0  # (best - null) must exceed this many times the null's spread... kept simple: best > null + MIN_GAP
MIN_GAP = 0.15
MIN_DRIFT_RATIO = 2.0  # the rates fit must leave under half the residual that a drift alone leaves
DETREND_S = 4.0      # a running mean this long is taken out of every pixel when the record is twice as long: what
                     # does not propagate (thermal streaks, a slow level drift) sits at zero rate and drags every fit there
N_SHUFFLE = 3
MAX_DRIFT_SPREAD = 0.35   # the quadrants' drifts may differ by this share of the drift (or 8 px/s) before the drift is not uniform


# ---- synthetic sea ----------------------------------------------------------------------------
def synth(m_x, q=1.0, U=(0.0, 0.0), N=384, n_frames=26, fps=26.0, spectrum="wind", theta0_deg=25.0,
          spread_deg=30.0, lam_m=(0.3, 60.0), beta=0.5, swell_m=20.0, swell_bw=0.10, swell_spread_deg=8.0,
          swell_share=0.7, affine=None, rot_deg_s=0.0, persp=0.0, nonlin=0.0, noise=0.3, repeat=0.0,
          jitter=0.0, seed=1, world_max=4096):
    """Frames of sea texture at m_x metres per pixel across, q times that along (image y), the
    texture drifting U px/s. Returns (S [n, N, N], t [n] the frames' nominal times, rep [n] bool:
    the frame repeats the one before).

    spectrum  "wind": slope energy per log |K| rising as |K|^beta between the lam_m wavelengths,
              directions theta0 +- spread (Gaussian); "swell": a narrow band at swell_m (log
              width swell_bw) and spread swell_spread; "both": the two, the swell holding
              swell_share of the slope variance.
    affine    ((Jxx, Jxy), (Jyx, Jyy)) in 1/s: the drift grows across the patch, U + J (x - c).
    rot_deg_s the picture turns about its centre.
    persp     the pixel scale grows by this share from the patch's centre to its top row.
    nonlin    radiance = slope + nonlin (slope^2 - 1), slope in units of its rms.
    noise     white noise, in units of the texture's rms.
    repeat    share of frames that repeat the one before (hold-and-jump), times still advance.
    jitter    rms of the frame times' wander, in frame periods.
    The angle convention is the image's: theta is measured from +x towards +y (down the picture).
    """
    rng = np.random.default_rng(seed)
    T = n_frames / fps
    J = np.zeros((2, 2)) if affine is None else np.asarray(affine, float)
    reach = N * m_x * max(1.0, q) * (1 + abs(persp)) + (np.hypot(*U) + np.abs(J).sum() * N) * m_x * max(1.0, q) * T
    dX = m_x * min(1.0, q) / 1.5
    Nw = 1 << int(np.ceil(np.log2(1.25 * reach / dX)))
    if Nw > world_max:
        dX *= Nw / world_max
        Nw = world_max
    kw = 2 * np.pi * np.fft.fftfreq(Nw, dX)
    KX, KY = np.meshgrid(kw, kw)                       # KX along columns (x), KY along rows (y)
    K = np.hypot(KX, KY)
    ang = np.arctan2(KY, KX)
    th0 = np.radians(theta0_deg)

    def dir_w(spread):
        d = (ang - th0 + np.pi) % (2 * np.pi) - np.pi
        return np.exp(-0.5 * (d / np.radians(spread)) ** 2)

    def rayleigh_phase(shape):
        return rng.rayleigh(1.0, shape) * np.exp(1j * rng.uniform(0, 2 * np.pi, shape))

    A = np.zeros((Nw, Nw), complex)
    Kp = np.maximum(K, 1e-9)
    if spectrum in ("wind", "both"):
        band = (K >= 2 * np.pi / lam_m[1]) & (K <= 2 * np.pi / lam_m[0])
        Aw = np.where(band, Kp ** (-2.5 + beta / 2) * dir_w(spread_deg), 0.0) * rayleigh_phase(K.shape)
        Aw[0, 0] = 0
        A += Aw / _slope_rms(Aw, K)
    if spectrum in ("swell", "both"):
        Ks = 2 * np.pi / swell_m
        As = np.exp(-0.5 * (np.log(Kp / Ks) / swell_bw) ** 2) * dir_w(swell_spread_deg) * rayleigh_phase(K.shape)
        As[0, 0] = 0
        share = swell_share if spectrum == "both" else 1.0
        wind_share = 1.0 - share if spectrum == "both" else 0.0
        A *= np.sqrt(wind_share) if spectrum == "both" else 1.0
        A += np.sqrt(share) * As / _slope_rms(As, K)
    Om = np.sqrt(G * K)
    slope_op = 1j * KY                                  # slope along y (the line of sight), the sky-reflection signal

    # image pixels -> world metres
    yy, xx = np.mgrid[:N, :N].astype(float)
    xx -= (N - 1) / 2
    yy -= (N - 1) / 2
    scale = 1.0 + persp * yy / N
    frames, times, rep = [], [], []
    t_nom = np.arange(n_frames) / fps
    t_true = np.sort(t_nom + jitter * rng.normal(0, 1, n_frames) / fps) if jitter else t_nom.copy()
    t_true[0] = 0.0
    prev = None
    for i in range(n_frames):
        if i and rng.uniform() < repeat and prev is not None:
            frames.append(prev)
            rep.append(True)
            times.append(t_nom[i])
            continue
        t = t_true[i]
        c, s = np.cos(np.radians(rot_deg_s) * t), np.sin(np.radians(rot_deg_s) * t)
        xr, yr = c * xx - s * yy, s * xx + c * yy
        dx = (U[0] + J[0, 0] * xx + J[0, 1] * yy) * t
        dy = (U[1] + J[1, 0] * xx + J[1, 1] * yy) * t
        X = m_x * (xr - dx) * scale
        Y = m_x * q * (yr - dy) * scale
        field = np.real(np.fft.ifft2(A * slope_op * np.exp(-1j * Om * t))) * Nw * Nw
        img = ndimage.map_coordinates(field, [Y / dX, X / dX], order=1, mode="wrap")
        frames.append(img)
        rep.append(False)
        times.append(t_nom[i])
        prev = img
    S = np.array(frames)
    S = (S - S.mean()) / S.std()
    if nonlin:
        S = S + nonlin * (S ** 2 - 1.0)
        S = (S - S.mean()) / S.std()
    S = S + noise * rng.normal(0, 1, S.shape)
    return S.astype(np.float32), np.array(times), np.array(rep)


def _slope_rms(A, K):
    return np.sqrt(np.sum(np.abs(A * K) ** 2)) + 1e-30


# ---- holding the sea: the texture's affine motion taken out ------------------------------------
def _peak_shift(c):
    """Sub-pixel location of the peak of a (fftshifted) correlation surface, about its centre."""
    N = c.shape[0]
    iy, ix = np.unravel_index(np.argmax(c), c.shape)

    def par(a, b, cc):
        d = a - 2 * b + cc
        return 0.0 if abs(d) < 1e-12 else float(np.clip(0.5 * (a - cc) / d, -1, 1))

    dy = iy - N // 2 + par(c[iy - 1, ix], c[iy, ix], c[(iy + 1) % N, ix])
    dx = ix - N // 2 + par(c[iy, ix - 1], c[iy, ix], c[iy, (ix + 1) % N])
    return dx, dy, float(c[iy, ix])


def local_shifts(a, b, grid=3, frac=0.5):
    """Where the texture of frame a is in frame b, in a grid x grid set of overlapping sub-blocks
    (each frac of the side): the blocks' centres (x, y) and their shifts (dx, dy), by phase
    correlation. The sea's own waves move too, so each shift is the texture's blended motion;
    what differs between blocks is the platform's parallax."""
    N = a.shape[0]
    n = int(N * frac)
    win = np.outer(np.hanning(n), np.hanning(n))
    k1 = 2 * np.pi * np.fft.fftfreq(n)
    kk = np.hypot(*np.meshgrid(k1, k1))
    band = (kk >= 2 * np.pi / (n / 3.0)) & (kk <= 2 * np.pi / LAM_MIN)
    starts = np.linspace(0, N - n, grid).astype(int)
    cen, sh, pk = [], [], []
    for y0 in starts:
        for x0 in starts:
            A = np.fft.fft2((a[y0:y0 + n, x0:x0 + n] - a[y0:y0 + n, x0:x0 + n].mean()) * win)
            B = np.fft.fft2((b[y0:y0 + n, x0:x0 + n] - b[y0:y0 + n, x0:x0 + n].mean()) * win)
            X = B * np.conj(A) * band
            eps = 0.3 * np.median(np.abs(X[band])) + 1e-30
            c = np.fft.fftshift(np.real(np.fft.ifft2(X / (np.abs(X) + eps))))
            dx, dy, v = _peak_shift(c)
            cen.append((x0 + n / 2, y0 + n / 2))
            sh.append((dx, dy))
            pk.append(v)
    return np.array(cen), np.array(sh), np.array(pk)


def affine_from_shifts(cen, sh, c):
    """The affine motion M (3x3, homogeneous) taking a point p of one frame to M p in the next,
    least squares over the blocks' shifts about the centre c: p' = p + T + J (p - c)."""
    X = np.c_[np.ones(len(cen)), cen[:, 0] - c, cen[:, 1] - c]
    cx, *_ = np.linalg.lstsq(X, sh[:, 0], rcond=None)
    cy, *_ = np.linalg.lstsq(X, sh[:, 1], rcond=None)
    M = np.eye(3)
    M[0, 0] += cx[1]; M[0, 1] += cx[2]; M[0, 2] = cx[0] - cx[1] * c - cx[2] * c
    M[1, 0] += cy[1]; M[1, 1] += cy[2]; M[1, 2] = cy[0] - cy[1] * c - cy[2] * c
    return M


def hold_sea(S, t, grid=3):
    """Every frame warped onto the middle frame's texture positions, by the texture's cumulative
    affine motion measured frame to frame (`local_shifts`, `affine_from_shifts`). A platform
    moving over an oblique sea makes the near sea stream faster than the far: a uniform drift
    then fits none of it, and the fit fails (PR149, 22 px/s apart across 320 px). After the hold
    the drift that remains is uniform (the blended wave motion the registration also took out
    is uniform, so the dispersion fit's U absorbs it). Returns the held frames (edges the warp
    brought nothing to are zero), the translation rate (px/s) and the gradient (1/s) that were
    taken out, and the correlation peaks (low: the texture decorrelated between frames)."""
    n, N, _ = S.shape
    c = (N - 1) / 2
    S = S - S.mean(axis=0, keepdims=True)            # the fixed pattern stays where it is: only the sea is moved
    Ms, Ts, Js, pks = [np.eye(3)], [], [], []
    for i in range(n - 1):
        cen, sh, pk = local_shifts(S[i], S[i + 1], grid)
        M = affine_from_shifts(cen, sh, c)
        dt = max(t[i + 1] - t[i], 1e-6)
        Ts.append((M[:2, 2] + (M[:2, :2] - np.eye(2)) @ [c, c]) / dt)
        Js.append((M[:2, :2] - np.eye(2)) / dt)
        pks.append(pk.mean())
        Ms.append(M @ Ms[-1])
    r = n // 2
    Cr_inv = np.linalg.inv(Ms[r])
    yy, xx = np.mgrid[:N, :N].astype(float)
    P = np.stack([xx.ravel(), yy.ravel(), np.ones(N * N)])
    held = np.empty_like(S)
    for i in range(n):
        C = Ms[i] @ Cr_inv
        Q = C @ P
        held[i] = ndimage.map_coordinates(S[i], [Q[1].reshape(N, N), Q[0].reshape(N, N)], order=1, mode="constant", cval=0.0)
    return held, dict(drift_px_s=np.mean(Ts, 0).tolist(), gradient_per_s=np.mean(Js, 0).tolist(),
                      gradient_rms_per_s=float(np.sqrt(np.mean(np.array(Js) ** 2))), peak=float(np.median(pks)))


# ---- the bins ---------------------------------------------------------------------------------
class Bins:
    """The Fourier components of a patch that carry the sea: their wavenumbers (rad/px, the
    half plane k_y > 0 or k_y = 0 & k_x > 0), their complex amplitudes on every frame, and their
    mean amplitude."""

    def __init__(self, kx, ky, F, amp, N, lam, noise=1.0):
        self.kx, self.ky, self.F, self.amp, self.N, self.lam, self.noise = kx, ky, F, amp, N, lam, noise

    def weights(self, kind="snr"):
        """Per-bin weights: "snr" a^2 / (a^2 + noise^2), so a bin well above the floor counts once
        however bright (the dominant band does not own the fit); "amp2" a^2; "amp" a."""
        a = self.amp
        if kind == "snr":
            w = 1.0 / (1.0 + (2.0 * self.noise / np.maximum(a, 1e-30)) ** 4)
        elif kind == "amp2":
            w = a ** 2
        else:
            w = a
        return w / w.sum()

    @property
    def k(self):
        return np.hypot(self.kx, self.ky)


def detrended(S, t=None, detrend_s=DETREND_S):
    """The frames less their mean over time (what stands still: a fixed pattern, the texture's
    skew the median frame leaves) and, when the record is at least twice detrend_s, less a
    running mean that long (what varies slowly: thermal streaks, a level drift). Both sit at
    zero rate, and a bin that holds them beside a wave reads a rate between the two."""
    S = S - S.mean(axis=0, keepdims=True)
    if t is not None and detrend_s and (t[-1] - t[0]) >= 2 * detrend_s:
        size = max(3, int(round(detrend_s / np.median(np.diff(t)))))
        S = S - ndimage.uniform_filter1d(S, size, axis=0, mode="nearest")
    return S


def bins_of(S, lam_min=LAM_MIN, lam_max=None, n_ann=N_ANN, top=TOP, t=None, detrend_s=DETREND_S):
    """2-D spectra of the frames (Hanning taper, means removed, `detrended` in time) and the bins
    kept: within the wavelength band, the top share of each log-annulus of |k| by mean amplitude,
    so every wavelength the band holds is represented, not only the dominant one."""
    n, H, W = S.shape
    assert H == W, "square patches"
    N = H
    lam_max = lam_max or N / 3.0
    win = np.outer(np.hanning(N), np.hanning(N))
    S = detrended(S, t, detrend_s)
    F = np.fft.fft2((S - S.mean(axis=(1, 2), keepdims=True)) * win)
    k1 = 2 * np.pi * np.fft.fftfreq(N)
    KX, KY = np.meshgrid(k1, k1)
    k = np.hypot(KX, KY)
    lam = np.where(k > 0, 2 * np.pi / np.maximum(k, 1e-12), np.inf)
    amp = np.sqrt(np.mean(np.abs(F) ** 2, 0))
    half = (KY > 0) | ((KY == 0) & (KX > 0))
    inband = half & (lam >= lam_min) & (lam <= lam_max)
    edges = np.exp(np.linspace(np.log(2 * np.pi / lam_max), np.log(2 * np.pi / lam_min), n_ann + 1))
    keep = np.zeros_like(inband)
    for a, b in zip(edges[:-1], edges[1:]):
        ann = inband & (k >= a) & (k < b)
        if ann.sum() == 0:
            continue
        thr = np.quantile(amp[ann], 1 - top)
        keep |= ann & (amp >= thr)
    idx = np.flatnonzero(keep)
    floors = []
    for a, b_ in zip(edges[:-1], edges[1:]):
        rest = inband & ~keep & (k >= a) & (k < b_)
        if rest.sum() >= 8:
            floors.append(float(np.median(amp[rest])))
    noise = min(floors) if floors else float(np.median(amp[inband]))
    return Bins(KX.ravel()[idx], KY.ravel()[idx], F.reshape(n, -1)[:, idx], amp.ravel()[idx], N, (lam_min, lam_max), noise)


# ---- estimator 1: one rate per bin ----------------------------------------------------------
def phase_rates(b, t):
    """Each bin's rate (rad/s) as the circular mean of its frame-to-frame phase steps, each step
    normalised to the median frame period, and its coherence (1: a steady rate; 0: noise)."""
    dt = np.diff(t)
    steps = b.F[1:] * np.conj(b.F[:-1])
    dmed = np.median(dt)
    ang = np.angle(steps) / dt[:, None]
    w = np.abs(steps)
    rate = np.angle(np.sum(w * np.exp(1j * ang * dmed), 0)) / dmed
    coh = np.abs(np.sum(steps / (np.abs(steps) + 1e-12), 0)) / len(steps)
    return rate, coh


def fit_rates(b, rate, coh, m_grid=M_GRID, q_grid=Q_GRID, th_step_deg=6.0, min_coh=0.5, weight="snr", fixed_q=None):
    """Grid fit of r(k) = -(s Omega(K; m, q) + k.U) over theta0 (the side s), m and q, U linear in
    each cell, then a polish off the grid; weights (SNR) x coherence. Returns the best, the cost
    profile in m and the band: the scales whose cost is within BAND of the way from the best up
    to the total (what no fit at all leaves)."""
    g = coh >= min_coh
    if g.sum() < 20:
        return dict(ok=False, why=f"only {int(g.sum())} coherent bins", n=int(g.sum()))
    if fixed_q is not None:
        q_grid = np.atleast_1d(float(fixed_q))
    kx, ky, r, w = b.kx[g], b.ky[g], rate[g], b.weights(weight)[g] * coh[g]
    w = w / w.sum()
    sw = np.sqrt(w)
    A = np.c_[kx, ky] * sw[:, None]
    AtA_inv = np.linalg.inv(A.T @ A)
    P = A @ AtA_inv                                        # (B, 2): U = P^T y, residual = y - A (P^T y)
    y0 = -r * sw
    ang = np.arctan2(ky, kx)
    tot = float(np.sum(r ** 2 * w))
    best = None
    prof = np.full(len(m_grid), np.inf)
    for th in np.radians(np.arange(0, 360, th_step_deg)):
        s = np.sign(np.cos(ang - th))
        s[s == 0] = 1
        for iq, q in enumerate(q_grid):
            Kq = np.hypot(kx[:, None] / m_grid[None, :], ky[:, None] / (m_grid[None, :] * q))   # (B, M)
            Z = s[:, None] * np.sqrt(G * Kq) * sw[:, None]
            Y = y0[:, None] - Z                               # (B, M)
            Uall = P.T @ Y                                    # (2, M)
            R = Y - A @ Uall
            cost = np.sum(R ** 2, 0)
            prof = np.minimum(prof, cost)
            i = int(np.argmin(cost))
            if best is None or cost[i] < best[0]:
                best = (float(cost[i]), float(m_grid[i]), float(q), float(np.degrees(th)), Uall[:, i].copy())
    cost, m, q, th, U = best

    def cost_at(p):
        mm, qq, tt = np.exp(p[0]), (np.exp(p[1]) if fixed_q is None else fixed_q), p[2]
        s = np.sign(np.cos(ang - tt))
        s[s == 0] = 1
        Z = s * np.sqrt(G * np.hypot(kx / mm, ky / (mm * qq))) * sw
        Y = y0 - Z
        return float(np.sum((Y - A @ (P.T @ Y)) ** 2))

    p0 = [np.log(m), np.log(q), np.radians(th)]
    bounds = [(np.log(m_grid[0]), np.log(m_grid[-1])), (np.log(q_grid[0]), np.log(q_grid[-1])), (p0[2] - 0.3, p0[2] + 0.3)]
    try:
        rr = optimize.minimize(cost_at, p0, method="Nelder-Mead", bounds=bounds, options=dict(xatol=1e-3, fatol=1e-9))
        if rr.fun < cost:
            cost, m, q, th = float(rr.fun), float(np.exp(rr.x[0])), float(np.exp(rr.x[1]) if fixed_q is None else fixed_q), float(np.degrees(rr.x[2]) % 360)
            s = np.sign(np.cos(ang - rr.x[2]))
            s[s == 0] = 1
            Y = y0 - s * np.sqrt(G * np.hypot(kx / m, ky / (m * q))) * sw
            U = P.T @ Y
    except ValueError:
        pass
    inband = prof <= cost * (1 + BAND)
    if not inband.any():
        inband[int(np.argmin(prof))] = True
    lo, hi = float(m_grid[inband].min()), float(m_grid[inband].max())
    # drift alone (Omega = 0): what the sqrt(k) shape adds, as the ratio of the residuals
    Ud = P.T @ y0
    cost_d = float(np.sum((y0 - A @ Ud) ** 2))
    # the bins that carried it: weight x how well each is fit, and their |k| span
    s = np.sign(np.cos(ang - np.radians(th)))
    s[s == 0] = 1
    model = -(s * np.sqrt(G * np.hypot(kx / m, ky / (m * q))) + kx * U[0] + ky * U[1])
    ww = w
    kk = np.hypot(kx, ky)
    order = np.argsort(kk)
    cw = np.cumsum(ww[order]) / max(ww.sum(), 1e-30)
    k10, k90 = kk[order][np.searchsorted(cw, 0.1)], kk[order][min(np.searchsorted(cw, 0.9), len(order) - 1)]
    th_dom = float(dominant_direction(b, np.where(g, b.weights(weight) * np.where(g, coh, 0), 0)))
    rate_spread = robust_spread(np.abs(r), w)
    return dict(ok=True, m=m, q=q, theta_deg=th, U=(float(U[0]), float(U[1])), explained=1 - cost / tot,
                dominant_deg=float(np.degrees(th_dom)), m_along=float(m_along(m, q, th_dom)), along_factor=float(m_along(m, q, th_dom) / m),
                rate_spread=rate_spread,
                band_along=(lo * float(m_along(m, q, th_dom) / m), hi * float(m_along(m, q, th_dom) / m)),
                drift_only=1 - cost_d / tot, drift_ratio=float(cost_d / max(cost, 1e-30)), band_m=(lo, hi), band_open=bool(inband[0] or inband[-1]), profile=prof,
                m_grid=m_grid, n=int(g.sum()), coh_median=float(np.median(coh)), k_span=float(k90 / max(k10, 1e-12)),
                q_edge=bool(fixed_q is None and (q <= q_grid[0] * 1.02 or q >= q_grid[-1] / 1.02)), model_rate=model, used=g)


def fit_rates_unaliased(b, rate, coh, t, **kw):
    """fit_rates, then once more without the bins whose model rate is past ALIAS of the Nyquist
    rate (the sampling wraps them, and the fit cannot): a fast drift aliases the short waves."""
    fr = fit_rates(b, rate, coh, **kw)
    if not fr["ok"]:
        return fr
    nyq = np.pi / np.median(np.diff(t))
    bad = np.zeros(len(b.k), bool)
    bad[fr["used"]] = np.abs(fr["model_rate"]) > ALIAS * nyq
    fr["aliased"] = int(bad.sum())
    if bad.any():
        coh2 = np.where(bad, 0.0, coh)
        fr2 = fit_rates(b, rate, coh2, **kw)
        if fr2["ok"]:
            fr2["aliased"] = int(bad.sum())
            return fr2
    return fr


def verdict_rates(fr):
    why = []
    if fr["explained"] < 0.8:
        why.append(("share", f"the rates fit explains only {fr['explained']:.2f} of the bins' rates"))
    if fr["drift_ratio"] < MIN_DRIFT_RATIO:
        why.append(("drift", f"a drift alone leaves only x{fr['drift_ratio']:.1f} the residual of the fit: the sqrt(k) shape is not seen"))
    if fr["k_span"] < MIN_SPAN:
        why.append(("k_span", f"the fit rests on one wavelength (|k| span x{fr['k_span']:.1f})"))
    if fr["rate_spread"] < MIN_RATE_SPREAD_RATES:
        why.append(("one_rate", f"the coherent bins share one rate (spread {fr['rate_spread']:.2f} rad/s): one wave leaking into "
                                "every bin, not a sea"))
    if "null_explained" in fr and fr["explained"] - fr["null_explained"] < 0.3:
        why.append(("null", f"the frames shuffled in time are explained {fr['null_explained']:.2f} against {fr['explained']:.2f}"))
    if fr["band_open"]:
        why.append(("band", "the band of scales reaches the grid's edge"))
    elif fr["band_m"][1] / max(fr["band_m"][0], 1e-12) > MAX_BAND:
        why.append(("wide", f"the band of scales is x{fr['band_m'][1] / fr['band_m'][0]:.1f} wide: nothing pinned"))
    return why


# ---- estimator 2: the dispersion shell on each bin's periodogram -------------------------------
def periodogram(b, t, oversample=4.0, nu_max=None):
    """Each bin's energy against frequency nu (rad/s), from its time series at the frames' true
    times: E[b, nu] = |sum_i F_i exp(-i nu t_i)|^2, scaled so that a single steady tone has E = 1
    at its peak and the share of the bin's energy at a frequency is E times the window's
    bandwidth over the bin's total. Also the window's own shape W(d nu), for the two branches'
    overlap. Returns nu, E (unit-max tones), share (E scaled to energy share), W(dnu) callable."""
    t = np.asarray(t, float)
    span = t[-1] - t[0]
    dt_min = np.min(np.diff(t))
    nu_max = nu_max or (np.pi / dt_min) * 1.05
    res = 2 * np.pi / span
    dnu = res / oversample
    nu = np.arange(-nu_max, nu_max + dnu, dnu)
    n = len(t)
    E = np.empty((b.F.shape[1], len(nu)), np.float32)
    ph = np.exp(-1j * np.outer(nu, t))                    # (Nnu, n)
    chunk = max(1, int(2e7 // (len(nu) * n)))
    for i in range(0, b.F.shape[1], chunk):
        E[i:i + chunk] = (np.abs(ph @ b.F[:, i:i + chunk]) ** 2).T / n ** 2
    # the window: a tone's periodogram shape, unit at its peak
    Wn = np.abs(np.sum(np.exp(-1j * np.outer(nu, t)), 1)) ** 2 / n ** 2
    bw = float(np.trapezoid(Wn, nu))                      # equivalent bandwidth of a tone
    tot = np.trapezoid(E, nu, axis=1)                     # each bin's total energy over nu
    share = np.minimum(E * (bw / np.maximum(tot, 1e-30))[:, None], 1.0)    # a lone tone: 1 at its peak
    return nu, E, share.astype(np.float32), (lambda d: np.interp(np.abs(d), nu[nu >= 0], Wn[nu >= 0], right=0.0))


def masked_share(share, nu, t):
    """The share with what is not a wave taken out: within one resolution element of zero rate
    (what stands still) and beyond CODEC_FRAC of the Nyquist rate (the codec's cadence)."""
    res = 2 * np.pi / (t[-1] - t[0])
    nyq = np.pi / np.median(np.diff(t))
    keep = (np.abs(nu) >= res) & (np.abs(nu) <= CODEC_FRAC * nyq)
    return np.where(keep[None, :], share, 0.0).astype(np.float32)


def peak_rates(share, nu):
    """Each bin's rate as the peak of its (masked) periodogram, to sub-bin precision, and how
    tonal the bin is: the share at that peak (1: a lone steady wave; near 0: noise or a broad
    spread). Records of a few seconds read rates this way; a zero-rate remainder or a codec
    line beside the wave, which bias the stepped phase, do not move a peak."""
    i = np.argmax(share, 1)
    tonal = share[np.arange(len(i)), i]
    i = np.clip(i, 1, share.shape[1] - 2)
    a, b, c = share[np.arange(len(i)), i - 1], share[np.arange(len(i)), i], share[np.arange(len(i)), i + 1]
    d = a - 2 * b + c
    off = np.where(np.abs(d) > 1e-12, 0.5 * (a - c) / np.where(np.abs(d) > 1e-12, d, 1), 0.0)
    return nu[i] + np.clip(off, -1, 1) * (nu[1] - nu[0]), tonal


def robust_spread(x, w):
    """1.4826 x the weighted median absolute deviation of x: a sigma that the faint bins' random
    values do not reach."""
    x = np.asarray(x, float)
    w = np.asarray(w, float)
    if w.sum() <= 0:
        return 0.0
    o = np.argsort(x)
    c = np.cumsum(w[o]) / w.sum()
    med = x[o][min(np.searchsorted(c, 0.5), len(o) - 1)]
    d = np.abs(x - med)
    o = np.argsort(d)
    c = np.cumsum(w[o]) / w.sum()
    return float(1.4826 * d[o][min(np.searchsorted(c, 0.5), len(o) - 1)])


def dominant_direction(b, w):
    """The axial direction (rad, from +x towards +y) the weight runs along."""
    return 0.5 * np.angle(np.sum(w * np.exp(2j * np.arctan2(b.ky, b.kx))))


def m_along(m_x, q, theta):
    """The scale along a direction, from m_x across and m_x q along the picture's y."""
    return 1.0 / np.sqrt(np.cos(theta) ** 2 / m_x ** 2 + np.sin(theta) ** 2 / (m_x * q) ** 2)


def _gather(table, nu, x):
    """Linear interpolation of table[b, :] (over nu) at x[b, ...]; zero outside."""
    dnu = nu[1] - nu[0]
    f = (x - nu[0]) / dnu
    i0 = np.floor(f).astype(int)
    fr = f - i0
    ok = (i0 >= 0) & (i0 < len(nu) - 1)
    i0c = np.clip(i0, 0, len(nu) - 2)
    bidx = np.arange(table.shape[0])
    bidx = bidx.reshape((-1,) + (1,) * (x.ndim - 1))
    v = table[bidx, i0c] * (1 - fr) + table[bidx, i0c + 1] * fr
    return np.where(ok, v, 0.0)


def shell_score(b, share, nu, Wfun, m, q, U, w, nyq=None, both=False):
    """Each bin's energy share at the better of the model's two branches nu_+- = -+Omega - k.U: a
    bin may hold a wave going either way, and a lone tone on either branch scores 1 whether the
    branches are apart or coincide (a drift-only model, Omega = 0), so one bin cannot tell
    dispersion from drift: the scale comes from the shape of nu(k) across bins, sqrt(k) against
    the drift's k, and from bins lit on both branches, which no single drift reaches. Rates beyond
    the Nyquist rate `nyq` are wrapped, as the sampling wraps them. The weighted mean over bins;
    with `both`, also each bin's shares on the two branches. m may be an array; U (2,) or (n, 2)."""
    U = np.atleast_2d(np.asarray(U, float))
    m = np.atleast_1d(np.asarray(m, float))
    kx, ky = b.kx, b.ky
    K = np.hypot(kx[:, None] / m[None, :], ky[:, None] / (m[None, :] * q))     # (B, M)
    Om = np.sqrt(G * K)
    kU = kx[:, None] * U[None, :, 0] + ky[:, None] * U[None, :, 1]             # (B, nU)
    nup = -Om[:, :, None] - kU[:, None, :]                                      # (B, M, nU)
    num = Om[:, :, None] - kU[:, None, :]
    if nyq:
        nup = (nup + nyq) % (2 * nyq) - nyq
        num = (num + nyq) % (2 * nyq) - nyq
    Ep, Em = _gather(share, nu, nup), _gather(share, nu, num)
    sc = np.tensordot(w, np.maximum(Ep, Em), axes=(0, 0)) / w.sum()            # (M, nU)
    return (sc, Ep, Em) if both else sc


def fit_shell(b, t, m_grid=M_GRID, q_grid=Q_GRID, u_max=U_MAX, n_u=N_U, weight="snr", pg=None, fixed_q=None):
    """The shell fit: grid over m and q, a drift box for U, then a refinement; the profile over
    m (the best of the rest at each m), and the bins' |k| span that carried the fit."""
    nu, E, share, Wfun = pg or periodogram(b, t)
    nyq = np.pi / np.median(np.diff(t))
    res = 2 * np.pi / (t[-1] - t[0])
    share = masked_share(share, nu, t)
    tonal = share.max(1)
    w = b.weights(weight) * tonal                   # a bin with no steady wave in it has no say
    w = w / max(w.sum(), 1e-30)
    qs = np.atleast_1d(fixed_q) if fixed_q is not None else q_grid
    ug = np.linspace(-u_max, u_max, n_u)
    UU = np.array(np.meshgrid(ug, ug)).reshape(2, -1).T
    best = None
    prof = np.full(len(m_grid), -np.inf)
    prof_q = np.zeros(len(m_grid))
    prof_U = np.zeros((len(m_grid), 2))
    for q in qs:
        sc = shell_score(b, share, nu, Wfun, m_grid, q, UU, w, nyq)         # (M, nU)
        j = np.argmax(sc, 1)
        scm = sc[np.arange(len(m_grid)), j]
        upd = scm > prof
        prof[upd] = scm[upd]
        prof_q[upd] = q
        prof_U[upd] = UU[j[upd]]
        i = int(np.argmax(scm))
        if best is None or scm[i] > best[0]:
            best = (float(scm[i]), float(m_grid[i]), float(q), UU[j[i]].copy())
    # at every m, polish q and U off the grid from that m's best cell, so the profile is the best
    # the rest can do there and the band and the best agree
    du = ug[1] - ug[0]
    qlo, qhi = np.log(qs[0]), np.log(qs[-1])
    for i, m in enumerate(m_grid):
        def neg_m(p, m=m):
            qq = np.exp(p[0]) if fixed_q is None else fixed_q
            return -shell_score(b, share, nu, Wfun, m, qq, p[1:3], w, nyq)[0, 0]
        p0 = [np.log(prof_q[i]), prof_U[i][0], prof_U[i][1]]
        bnd = [(qlo, qhi), (p0[1] - du, p0[1] + du), (p0[2] - du, p0[2] + du)]
        rr = optimize.minimize(neg_m, p0, method="Nelder-Mead", bounds=bnd, options=dict(xatol=2e-3, fatol=1e-5, maxiter=150))
        if -rr.fun > prof[i]:
            prof[i], prof_q[i], prof_U[i] = float(-rr.fun), float(np.exp(rr.x[0]) if fixed_q is None else fixed_q), rr.x[1:3]
    i = int(np.argmax(prof))
    m0, q0, U0 = m_grid[i], prof_q[i], prof_U[i]
    prof_free = prof.copy()

    def neg(p):
        mq = np.exp(p[0]); qq = np.exp(p[1]) if fixed_q is None else fixed_q
        return -shell_score(b, share, nu, Wfun, mq, qq, p[2:4], w, nyq)[0, 0]

    p0 = [np.log(m0), np.log(q0), U0[0], U0[1]]
    bounds = [(np.log(m_grid[0]), np.log(m_grid[-1])), (qlo, qhi), (-2 * u_max, 2 * u_max), (-2 * u_max, 2 * u_max)]
    r = optimize.minimize(neg, p0, method="Nelder-Mead", bounds=bounds, options=dict(xatol=1e-3, fatol=1e-5, maxiter=400))
    m, q, U = float(np.exp(r.x[0])), float(np.exp(r.x[1])) if fixed_q is None else float(fixed_q), (float(r.x[2]), float(r.x[3]))
    score = float(-r.fun)
    FF = np.array(np.meshgrid(np.linspace(-du, du, 9), np.linspace(-du, du, 9))).reshape(2, -1).T
    # the profile over m_x with q held at the fit's: along a one-way sea m_x and q trade, and only
    # the scale along the waves is fixed; this profile, read along that direction, is its band
    prof_q_held = np.full(len(m_grid), -np.inf)
    for i, mm in enumerate(m_grid):
        def neg_u(p, mm=mm):
            return -shell_score(b, share, nu, Wfun, mm, q, p, w, nyq)[0, 0]
        rr = optimize.minimize(neg_u, list(U), method="Nelder-Mead", bounds=[(U[0] - 2 * du, U[0] + 2 * du), (U[1] - 2 * du, U[1] + 2 * du)],
                               options=dict(xatol=2e-3, fatol=1e-5, maxiter=100))
        prof_q_held[i] = float(-rr.fun)
    j = int(np.argmin(np.abs(np.log(m_grid) - np.log(m))))
    prof_q_held[j] = max(prof_q_held[j], score)
    prof[j] = max(prof[j], score)
    # drift alone: Omega = 0 is m -> infinity; score the best drift with no dispersion
    sc0 = shell_score(b, share, nu, Wfun, 1e9, 1.0, UU, w, nyq)[0]
    j = int(np.argmax(sc0))
    sc0f = shell_score(b, share, nu, Wfun, 1e9, 1.0, UU[j] + FF, w, nyq)[0]
    drift_only = float(sc0f.max())
    # which bins carried it: their share at the fitted branches, the |k| span of that weight, the
    # dispersion's spread over those bins against the record's resolution, and the bins lit both ways
    _, Ep, Em = shell_score(b, share, nu, Wfun, m, q, U, w, nyq, both=True)
    Ep, Em = Ep[:, 0, 0], Em[:, 0, 0]
    on = np.maximum(Ep, Em)
    ww = w
    order = np.argsort(b.k)
    cw = np.cumsum(ww[order]) / max(ww.sum(), 1e-30)
    k10, k90 = b.k[order][np.searchsorted(cw, 0.1)], b.k[order][min(np.searchsorted(cw, 0.9), len(order) - 1)]
    Om = np.sqrt(G * np.hypot(b.kx / m, b.ky / (m * q)))
    oo = np.argsort(Om)
    co = np.cumsum(ww[oo]) / max(ww.sum(), 1e-30)
    om_spread = float(Om[oo][min(np.searchsorted(co, 0.9), len(oo) - 1)] - Om[oo][np.searchsorted(co, 0.1)])
    two_way = float(np.sum(ww * (np.minimum(Ep, Em) > 0.5)) / max(ww.sum(), 1e-30))
    pk, _ = peak_rates(share, nu)
    rate_spread = robust_spread(np.abs(pk), ww)
    q_edge = fixed_q is None and (q <= qs[0] * 1.02 or q >= qs[-1] / 1.02)
    theta = float(dominant_direction(b, ww))
    return dict(ok=True, m=m, q=q, U=U, score=score, drift_only=drift_only, profile=prof_q_held, profile_free=prof_free,
                m_grid=m_grid, k_span=float(k90 / max(k10, 1e-12)), omega_spread=om_spread, resolution=float(res),
                two_way=two_way, rate_spread=rate_spread, q_edge=bool(q_edge), theta_deg=float(np.degrees(theta)), m_along=float(m_along(m, q, theta)),
                along_factor=float(m_along(m, q, theta) / m), tonal=float(np.mean(tonal)), on=on, n=len(b.k),
                pg=(nu, E, share, Wfun))


def band_of(prof, m_grid, best, floor, frac=BAND):
    """The scales whose profile is within frac of the way from the best down to the floor."""
    thr = best - frac * max(best - floor, 1e-9)
    ok = prof >= thr
    if not ok.any():
        return (float("nan"), float("nan")), True
    return (float(m_grid[ok].min()), float(m_grid[ok].max())), bool(ok[0] or ok[-1])


# ---- the whole measurement on one patch ------------------------------------------------------
def measure_patch(S, t, rep=None, static=None, lam_min=LAM_MIN, lam_max=None, n_shuffle=N_SHUFFLE, seed=0,
                  fixed_q=None, rates=True, shell=True, m_grid=M_GRID, q_grid=Q_GRID, u_max=U_MAX, keep=False,
                  quadrants=True, hold=False, margin=0, rates_by_peak=False):
    """Both estimators on one square patch, with their nulls and verdicts. S [n, N, N] frames at
    nominal times t; rep marks frames that repeat the one before (dropped); static (N, N) is
    subtracted (what does not move: fixed pattern, overlay)."""
    S = np.asarray(S, np.float32)
    t = np.asarray(t, float)
    if rep is not None:
        kept = ~np.asarray(rep, bool)
        S, t = S[kept], t[kept]
    if static is not None:
        S = S - static[None]
    out = dict(n_frames=int(len(t)), span_s=float(t[-1] - t[0]))
    if hold:
        S, held = hold_sea(S, t)
        out["hold"] = held
    if margin:
        S = S[:, margin:-margin, margin:-margin]
    if quadrants and S.shape[1] >= 128:
        out["quadrants"] = drift_by_quadrant(S, t, None, None, lam_min, fixed_q, m_grid, q_grid)
    b = bins_of(S, lam_min, lam_max, t=t)
    out["n_bins"] = len(b.k)
    rng = np.random.default_rng(seed)
    if keep:
        out["_bins"] = b
    long_record = (t[-1] - t[0]) >= PEAK_SPAN_S
    by_peak = rates_by_peak and long_record
    pg = periodogram(b, t) if (shell or by_peak) else None

    def rates_of(bb, pgb=None):
        if by_peak:
            nu_, _, share_, _ = pgb or periodogram(bb, t)
            return peak_rates(masked_share(share_, nu_, t), nu_)
        return phase_rates(bb, t)

    if rates:
        r, c = rates_of(b, pg)
        if keep:
            out["_rate"], out["_coh"] = r, c
        fr = fit_rates_unaliased(b, r, c, t, m_grid=m_grid, q_grid=q_grid, fixed_q=fixed_q, min_coh=0.3 if by_peak else 0.5)
        if fr["ok"]:
            fr["by_peak"] = by_peak
            nulls = []
            for _ in range(n_shuffle):
                bs = Bins(b.kx, b.ky, b.F[rng.permutation(len(t))], b.amp, b.N, b.lam, b.noise)
                rs, cs = rates_of(bs)
                fn = fit_rates(bs, rs, cs, m_grid, q_grid, fixed_q=fixed_q, min_coh=0.3 if by_peak else 0.5)
                nulls.append(fn["explained"] if fn["ok"] else 0.0)
            fr["null_explained"] = float(max(nulls))
            fr["no_power"] = verdict_rates(fr)
            if long_record and shell:
                fr["no_power"].append(("long", "a record this long is the shell's: the stepped phase is reported, not claimed"))
            if out.get("quadrants", {}).get("ok") and not out["quadrants"]["uniform"]:
                fr["no_power"].append(("gradient", f"the drift differs across the patch (quadrants {out['quadrants']['spread']:.0f} px/s "
                                                   f"apart about ({out['quadrants']['mean'][0]:.0f}, {out['quadrants']['mean'][1]:.0f})): "
                                                   "use smaller patches"))
            fr.pop("model_rate", None)
            fr.pop("used", None)
        out["rates"] = fr
    if shell:
        fs = fit_shell(b, t, m_grid, q_grid, u_max, fixed_q=fixed_q, pg=pg)
        nulls = []
        for _ in range(n_shuffle):
            bs = Bins(b.kx, b.ky, b.F[rng.permutation(len(t))], b.amp, b.N, b.lam, b.noise)
            fn = fit_shell(bs, t, m_grid[::3], q_grid[::4], u_max, n_u=7, fixed_q=fixed_q)
            nulls.append(fn["score"])
        fs["null"] = float(max(nulls))
        fs["band_m"], fs["band_open"] = band_of(fs["profile"], m_grid, fs["score"], fs["null"])
        fs["band_along"] = (fs["band_m"][0] * fs["along_factor"], fs["band_m"][1] * fs["along_factor"])
        fs["no_power"] = verdict_shell(fs)
        if out.get("quadrants", {}).get("ok") and not out["quadrants"]["uniform"]:
            fs["no_power"].append(("gradient", f"the drift differs across the patch (quadrants {out['quadrants']['spread']:.0f} px/s apart): "
                                               "use smaller patches"))
        if keep:
            out["_pg"] = fs["pg"]
            out["_t"] = t
        fs.pop("pg", None)
        out["shell"] = fs
    return out


def drift_by_quadrant(S, t, rep=None, static=None, lam_min=LAM_MIN, fixed_q=None, m_grid=M_GRID, q_grid=Q_GRID):
    """The drift U fitted in each quadrant of the patch (the rates fit, the dispersion carried):
    a platform moving over an oblique sea gives a drift that grows across the picture, and one
    uniform U then fits none of it. Returns the four U, their spread (rms about the mean, px/s)
    and the mean drift's size."""
    S = np.asarray(S, np.float32)
    t = np.asarray(t, float)
    if rep is not None:
        kept = ~np.asarray(rep, bool)
        S, t = S[kept], t[kept]
    if static is not None:
        S = S - static[None]
    N = S.shape[1]
    h = N // 2
    Us = []
    for y0 in (0, h):
        for x0 in (0, h):
            b = bins_of(S[:, y0:y0 + h, x0:x0 + h], lam_min, h / 3.0, t=t)
            r, c = phase_rates(b, t)
            fr = fit_rates(b, r, c, m_grid, q_grid, th_step_deg=10.0, fixed_q=fixed_q)
            Us.append(fr["U"] if fr["ok"] else (np.nan, np.nan))
    Us = np.array(Us, float)
    good = ~np.isnan(Us).any(1)
    if good.sum() < 3:
        return dict(ok=False, U=Us.tolist())
    mean = Us[good].mean(0)
    spread = float(np.sqrt(np.mean(np.sum((Us[good] - mean) ** 2, 1))))
    return dict(ok=True, U=Us.tolist(), mean=(float(mean[0]), float(mean[1])), spread=spread,
                uniform=bool(spread <= max(8.0, MAX_DRIFT_SPREAD * np.hypot(*mean))))


def verdict_shell(fs):
    """Why the shell fit cannot claim a scale, if it cannot."""
    why = []
    if fs["omega_spread"] < MIN_RESOLVE * fs["resolution"]:
        why.append(("resolution", f"the record ({fs['resolution']:.2f} rad/s resolution) cannot resolve the dispersion across "
                                  f"the lit bins ({fs['omega_spread']:.2f} rad/s): too short for the shell"))
    if fs["k_span"] < MIN_SPAN:
        why.append(("k_span", f"the fit rests on one wavelength (|k| span x{fs['k_span']:.1f} < x{MIN_SPAN:.0f}): "
                              "the scale is the drift's shadow"))
    if fs["rate_spread"] < MIN_RATE_SPREAD * fs["resolution"]:
        why.append(("one_rate", f"the lit bins share one rate (spread {fs['rate_spread']:.2f} rad/s at {fs['resolution']:.2f} resolution): "
                                "one wave leaking into every bin, not a sea"))
    if fs["score"] < MIN_SHARE:
        why.append(("share", f"only {fs['score']:.2f} of the texture's energy sits on the dispersion shell"))
    if fs["score"] - fs["drift_only"] < MIN_OVER_DRIFT:
        why.append(("drift", f"a drift alone does as well ({fs['drift_only']:.2f} against {fs['score']:.2f})"))
    if fs["score"] - fs["null"] < MIN_GAP:
        why.append(("null", f"the frames shuffled in time score {fs['null']:.2f} against {fs['score']:.2f}"))
    if fs["band_open"]:
        why.append(("band", "the band of scales reaches the grid's edge"))
    elif fs["band_m"][1] / max(fs["band_m"][0], 1e-12) > MAX_BAND:
        why.append(("wide", f"the band of scales is x{fs['band_m'][1] / fs['band_m'][0]:.1f} wide: nothing pinned"))
    return why


def said_patch(res, truth=None):
    """Plain lines for one patch."""
    lines = [f"{res['n_frames']} frames over {res['span_s']:.2f} s, {res['n_bins']} bins"]
    hd = res.get("hold")
    if hd:
        J = np.array(hd["gradient_per_s"])
        lines.append(f"  held: the texture's drift ({hd['drift_px_s'][0]:.1f}, {hd['drift_px_s'][1]:.1f}) px/s and gradient "
                     f"[{J[0, 0]:+.3f} {J[0, 1]:+.3f}; {J[1, 0]:+.3f} {J[1, 1]:+.3f}] /s taken out (correlation peak {hd['peak']:.2f})")
    qd = res.get("quadrants")
    if qd and qd.get("ok"):
        lines.append(f"  quadrants' drift: {qd['spread']:.1f} px/s apart about ({qd['mean'][0]:.1f}, {qd['mean'][1]:.1f}); "
                     f"{'uniform' if qd['uniform'] else 'NOT uniform'}")
    if "rates" in res:
        fr = res["rates"]
        if fr["ok"]:
            lines.append(f"  rates{' (peaks)' if fr.get('by_peak') else ' (steps)'}: m_x {fr['m']:.4f} m/px (10 % band {fr['band_m'][0]:.4f}-{fr['band_m'][1]:.4f}"
                         f"{', open' if fr['band_open'] else ''}), q {fr['q']:.2f}, theta0 {fr['theta_deg']:.0f}, "
                         f"U ({fr['U'][0]:.1f}, {fr['U'][1]:.1f}) px/s; explained {fr['explained']:.2f}, "
                         f"drift alone {fr['drift_only']:.2f}, shuffled {fr.get('null_explained', float('nan')):.2f}; "
                         f"{fr['n']} coherent bins, |k| span x{fr['k_span']:.1f}, {fr.get('aliased', 0)} aliased")
            lines.append(f"    along the waves ({fr['dominant_deg']:.0f} deg): {fr['m_along']:.4f} m/px, band "
                         f"{fr['band_along'][0]:.4f}-{fr['band_along'][1]:.4f}" + ("; q at the grid's edge" if fr.get("q_edge") else ""))
            for _, why in fr.get("no_power", []):
                lines.append(f"    no power: {why}")
        else:
            lines.append(f"  rates: no fit ({fr['why']})")
    if "shell" in res:
        fs = res["shell"]
        lines.append(f"  shell: m_x {fs['m']:.4f} m/px (band {fs['band_m'][0]:.4f}-{fs['band_m'][1]:.4f}"
                     f"{', open' if fs['band_open'] else ''}), q {fs['q']:.2f}, U ({fs['U'][0]:.1f}, {fs['U'][1]:.1f}) px/s; "
                     f"on shell {fs['score']:.2f}, drift alone {fs['drift_only']:.2f}, shuffled {fs['null']:.2f}; "
                     f"|k| span x{fs['k_span']:.1f}, dispersion spread {fs['omega_spread']:.1f} rad/s at {fs['resolution']:.2f} resolution, "
                     f"two-way {fs['two_way']:.2f}, tonal {fs['tonal']:.2f}")
        lines.append(f"    along the waves ({fs['theta_deg']:.0f} deg): {fs['m_along']:.4f} m/px, band "
                     f"{fs['band_along'][0]:.4f}-{fs['band_along'][1]:.4f}" + ("; q at the grid's edge" if fs.get("q_edge") else ""))
        for _, why in fs["no_power"]:
            lines.append(f"    no power: {why}")
    if truth is not None:
        th = res.get("shell", res.get("rates", {})).get("theta_deg", res.get("rates", {}).get("dominant_deg"))
        extra = f"; along {th:.0f} deg: {m_along(truth[0], truth[1], np.radians(th)):.4f}" if th is not None else ""
        lines.append(f"  truth: m_x {truth[0]:.4f}, q {truth[1]:.2f}{extra}")
    return lines


# ---- the stage ---------------------------------------------------------------------------------
def stream_grey(video, n0, n1, W, H):
    """Frames n0..n1 (1-based) of the video as 8-bit grey arrays, one at a time, straight from ffmpeg."""
    import subprocess
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"select='between(n,{n0 - 1},{n1 - 1})'",
                          "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    try:
        n = n0
        while n <= n1:
            b = p.stdout.read(W * H)
            if len(b) < W * H:
                break
            yield n, np.frombuffer(b, np.uint8).reshape(H, W)
            n += 1
    finally:
        p.stdout.close()
        p.wait()


def default_patches(W, H, N=384, margin=48):
    """Square patches tiling the picture inside a margin: as many as fit, N px each, or as large as
    fit where the picture is smaller than one patch and its margins (a 640x328 copy once got one
    384-px patch starting above its top edge, and the crop of it was not square)."""
    N = min(N, W - 2 * margin, H - 2 * margin)
    if N < 4 * LAM_MIN:                 # no room inside the margin for a wave: the whole picture's short side
        margin, N = 0, min(W, H)
    nx, ny = max(1, (W - 2 * margin) // N), max(1, (H - 2 * margin) // N)
    x0 = (W - nx * N) // 2
    y0 = (H - ny * N) // 2
    return [(x0 + i * N, y0 + j * N, N) for j in range(ny) for i in range(nx)]


def repeats_of(crops):
    """Frames whose patches all barely change from the one before: a padded variable-rate clip."""
    d = None
    for S in crops.values():
        dd = np.abs(np.diff(S, axis=0)).mean(axis=(1, 2))
        d = dd if d is None else d + dd
    if d is None or len(d) == 0:
        return np.zeros(1, bool)
    med = np.median(d)
    return np.r_[False, d < 0.15 * med]


def measure(video, W, H, fps, n0, n1, patches=None, held_csv=None, static_ranges=None, lam_min=LAM_MIN, lam_max=None,
            fixed_q=None, truth=None, out=None, progress=None, n_shuffle=N_SHUFFLE):
    """The ruler on frames n0..n1 of a clip: every patch measured by both estimators with their
    nulls, and one scale from the patches that can claim one. Returns report.Found."""
    import csv as _csv
    from pathlib import Path
    from .report import Found
    say = progress or (lambda *a: None)
    patches = patches or default_patches(W, H)
    n_lo, n_hi = n0, n1
    static_ranges = static_ranges or []
    for lo, hi in static_ranges:
        n_lo, n_hi = min(n_lo, lo), max(n_hi, hi)
    crops = {pt: [] for pt in patches}
    frames = []
    for n, f in stream_grey(video, n_lo, n_hi, W, H):
        frames.append(n)
        for (x0, y0, N) in patches:
            crops[(x0, y0, N)].append(f[y0:y0 + N, x0:x0 + N].astype(np.float32))
    frames = np.array(frames)
    crops = {k: np.array(v) for k, v in crops.items()}
    say(f"frames {n_lo}-{frames[-1]} read; {len(patches)} patches")
    ok = np.ones(len(frames), bool)
    rep = repeats_of(crops)
    if held_csv:
        rows = {int(r["frame"]): r for r in _csv.DictReader(l for l in open(held_csv) if not l.startswith("#"))}
        ok = np.array([rows.get(int(n), {}).get("ok", "1") == "1" for n in frames])
        rep = np.array([bool(rows.get(int(n), {}).get("repeat_of", "")) for n in frames])
    win = (frames >= n0) & (frames <= n1)
    fields = dict(n0=int(n0), n1=int(n1), frames=int(win.sum()), repeats=int((rep & win).sum()), lost=int((~ok & win).sum()),
                  patches=[])
    results = {}
    for pt in patches:
        S = crops[pt]
        if static_ranges:
            sm = np.zeros(len(frames), bool)
            for lo, hi in static_ranges:
                sm |= (frames >= lo) & (frames <= hi)
            sm &= ok & ~rep
        else:
            sm = win & ok & ~rep
        static = np.median(S[sm], axis=0) if sm.sum() >= 3 else None
        sel = win & ok
        t = (frames[sel] - 1) / fps
        res = measure_patch(S[sel], t, rep[sel], static=static, lam_min=lam_min, lam_max=lam_max, fixed_q=fixed_q,
                            n_shuffle=n_shuffle, keep=True)
        results[pt] = res
        lines = said_patch(res, truth)
        say(f"  patch x{pt[0]} y{pt[1]} N{pt[2]}: {lines[0]}")
        for line in lines[1:]:
            say("    " + line)
        rec = dict(x0=pt[0], y0=pt[1], N=pt[2], n_frames=res["n_frames"], span_s=res["span_s"], n_bins=res["n_bins"])
        for key in ("rates", "shell"):
            if key in res:
                rec[key] = {k: v for k, v in res[key].items() if k not in ("profile", "profile_free", "m_grid", "on", "pg", "no_power")}
                if "no_power" in res[key]:
                    rec[key]["no_power"] = [w[1] for w in res[key]["no_power"]]
        fields["patches"].append(rec)
    # one scale, from the patches whose shell fit can claim one
    claims = []
    for pt in patches:
        r = results[pt]
        if "shell" in r and not r["shell"]["no_power"]:
            claims.append(r["shell"])
        elif r.get("rates", {}).get("ok") and not r["rates"].get("no_power"):
            claims.append(r["rates"])
    no_power, needs, notes = [], [], []
    if claims:
        ms = np.array([c["m"] for c in claims])
        qs = np.array([c["q"] for c in claims])
        lo = min(c["band_m"][0] for c in claims)
        hi = max(c["band_m"][1] for c in claims)
        fields.update(m_x_m_per_px=float(np.median(ms)), m_x_band=(float(lo), float(hi)), q=float(np.median(qs)),
                      m_y_m_per_px=float(np.median(ms * qs)), depression_deg=float(np.degrees(np.arcsin(min(1.0, 1 / np.median(qs))))),
                      patches_claiming=len(claims), m_x_spread=float(ms.max() / ms.min()))
        needs.append("the range at which the sea is seen: the scale is the sea's, and holds for an object only at the sea's distance")
    else:
        fields.update(patches_claiming=0)
        whys = {}
        for pt in patches:
            for est in ("rates", "shell"):
                for key, why in results[pt].get(est, {}).get("no_power", []):
                    whys.setdefault(f"{est}:{key}", why)
        for key, why in whys.items():
            no_power.append((f"waves:{key}", why))
        if not whys:
            no_power.append(("waves", "no patch could be measured"))
    files = []
    if out:
        files.append(figure(f"{out}_waves.png", Path(str(video)).stem, patches, results, truth))
        files.append(write(f"{out}_waves.csv", patches, results))
    return Found("waves", result={"waves": said(fields)[0]}, fields=fields, no_power=no_power, needs=needs, files=files,
                 notes=notes)


def write(path, patches, results):
    import csv as _csv
    with open(path, "w", newline="") as f:
        w = _csv.writer(f)
        w.writerow(["x0", "y0", "N", "estimator", "m_x_m_per_px", "band_lo", "band_hi", "band_open", "q", "U_x_px_s", "U_y_px_s",
                    "score", "drift_only", "null", "k_span", "no_power"])
        for pt in patches:
            r = results[pt]
            if r.get("rates", {}).get("ok"):
                fr = r["rates"]
                w.writerow([*pt, "rates", f"{fr['m']:.5f}", f"{fr['band_m'][0]:.5f}", f"{fr['band_m'][1]:.5f}", int(fr["band_open"]),
                            f"{fr['q']:.3f}", f"{fr['U'][0]:.2f}", f"{fr['U'][1]:.2f}", f"{fr['explained']:.3f}", f"{fr['drift_only']:.3f}",
                            f"{fr.get('null_explained', float('nan')):.3f}", f"{fr['k_span']:.2f}", "; ".join(x[0] for x in fr.get("no_power", []))])
            if "shell" in r:
                fs = r["shell"]
                w.writerow([*pt, "shell", f"{fs['m']:.5f}", f"{fs['band_m'][0]:.5f}", f"{fs['band_m'][1]:.5f}", int(fs["band_open"]),
                            f"{fs['q']:.3f}", f"{fs['U'][0]:.2f}", f"{fs['U'][1]:.2f}", f"{fs['score']:.3f}", f"{fs['drift_only']:.3f}",
                            f"{fs['null']:.3f}", f"{fs['k_span']:.2f}", "; ".join(x[0] for x in fs["no_power"])])
    return path


def figure(path, name, patches, results, truth=None):
    """Per patch: the bins' rates against |K| along the fitted direction with the dispersion curve,
    and the score profiles over the scale."""
    from .figures import setup, save
    plt = setup(9)
    n = len(patches)
    fig, axes = plt.subplots(n, 2, figsize=(12, 3.6 * n), squeeze=False, constrained_layout=True)
    for row, pt in enumerate(patches):
        r = results[pt]
        a, bprof = axes[row]
        fs = r.get("shell")
        fr = r.get("rates", {})
        b = r.get("_bins")
        if b is not None and fs and "_pg" in r:
            m, q, U = fs["m"], fs["q"], fs["U"]
            nu, _, share, _ = r["_pg"]
            share = masked_share(share, nu, r["_t"])
            th = np.radians(fs["theta_deg"])
            ang = np.arctan2(b.ky, b.kx)
            d = (ang - th + np.pi / 2) % np.pi - np.pi / 2
            sel = np.abs(d) < np.radians(20)
            side = np.sign(np.cos(ang - th))
            edges = np.exp(np.linspace(np.log(b.k[sel].min()), np.log(b.k[sel].max()), 25))
            kc = np.sqrt(edges[:-1] * edges[1:])
            img = np.full((len(kc), len(nu)), np.nan)
            for i, (lo, hi) in enumerate(zip(edges[:-1], edges[1:])):
                m_ = sel & (b.k >= lo) & (b.k < hi)
                if m_.sum() >= 2:
                    rows = np.where(side[m_][:, None] > 0, share[m_], share[m_][:, ::-1])
                    img[i] = (rows * (b.amp[m_] ** 2)[:, None]).sum(0) / (b.amp[m_] ** 2).sum()
            lim = min(30.0, float(nu.max()))
            pc = a.pcolormesh(nu, kc, np.nan_to_num(img), cmap="magma", shading="nearest", vmin=0, vmax=max(np.nanmax(img), 1e-6))
            fig.colorbar(pc, ax=a, fraction=0.04, pad=0.02).set_label("Energy Share", fontweight="bold")
            kk = np.linspace(kc.min(), kc.max(), 200)
            K = np.hypot(kk * np.cos(th) / m, kk * np.sin(th) / (m * q))
            Om = np.sqrt(G * K)
            kU = kk * (np.cos(th) * U[0] + np.sin(th) * U[1])
            a.plot(-Om - kU, kk, color="C2", lw=1.3, label="Fitted Scale")
            a.plot(Om - kU, kk, color="C2", lw=1.3, ls="--")
            if truth:
                Kt = np.hypot(kk * np.cos(th) / truth[0], kk * np.sin(th) / (truth[0] * truth[1]))
                a.plot(-np.sqrt(G * Kt) - kU, kk, color="w", lw=0.9, ls=":", label="Known Scale")
                a.plot(np.sqrt(G * Kt) - kU, kk, color="w", lw=0.9, ls=":")
            a.set_yscale("log")
            a.set_xlim(-lim, lim)
            a.set_xlabel("Rate (rad/s)", fontweight="bold")
            a.set_ylabel("|k| (rad/px)", fontweight="bold")
            a.set_title(f"Patch x{pt[0]} y{pt[1]} N{pt[2]}, along {fs['theta_deg']:.0f} deg: m_x {m:.3f} m/px, q {q:.2f}, "
                        f"U ({U[0]:.0f}, {U[1]:.0f}) px/s", fontweight="bold", fontsize=9)
            a.legend(loc="upper right", fontsize=8)
        if fs:
            bprof.plot(fs["m_grid"], fs["profile"], color="C0", lw=1.5, label="Shell Score")
            bprof.axhline(fs["null"], color="C0", ls=":", lw=1, label="Shuffled")
            bprof.axhline(fs["drift_only"], color="C0", ls="--", lw=1, label="Drift Alone")
            bprof.axvspan(*fs["band_m"], color="C0", alpha=0.12)
        if fr.get("ok"):
            tot = fr["profile"].min() / max(1e-12, 1 - fr["explained"]) if fr["explained"] < 1 else None
            expl = 1 - fr["profile"] / tot if tot else 1 - fr["profile"] / fr["profile"].max()
            bprof.plot(fr["m_grid"], expl, color="C1", lw=1.5, label="Rates Explained")
        if truth:
            bprof.axvline(truth[0], color="k", lw=1, ls="-.", label="Known Scale")
        bprof.set_xscale("log")
        bprof.set_ylim(0, 1.05)
        bprof.set_xlabel("Scale m_x (m/px)", fontweight="bold")
        bprof.set_ylabel("Score", fontweight="bold")
        bprof.legend(loc="lower left", fontsize=8)
        if fs and fs["no_power"]:
            bprof.set_title("no power: " + "; ".join(w[0] for w in fs["no_power"]), fontsize=9, color="C3")
        else:
            bprof.set_title("claims a scale", fontsize=9)
    fig.suptitle(f"{name}: the Sea as a Ruler", fontweight="bold")
    save(fig, path, dpi=110)
    plt.close(fig)
    return path


def said(f):
    if f.get("patches_claiming", 0):
        lo, hi = f["m_x_band"]
        L = [f"The sea's dispersion puts the scale at {f['m_x_m_per_px']:.3f} m per pixel across (bands {lo:.3f}-{hi:.3f}) "
             f"and {f['m_y_m_per_px']:.3f} along, q {f['q']:.2f} (a depression of {f['depression_deg']:.0f} deg for a flat sea), "
             f"from {f['patches_claiming']} of {len(f['patches'])} patches over frames {f['n0']}-{f['n1']} "
             f"({f['frames']} frames, {f['repeats']} repeats); the patches agree to x{f['m_x_spread']:.2f}."]
    else:
        L = [f"No patch of frames {f['n0']}-{f['n1']} can claim a scale from the sea's dispersion."]
    for p in f["patches"]:
        fs = p.get("shell")
        if fs:
            L.append(f"Patch x{p['x0']} y{p['y0']} N{p['N']}: shell m_x {fs['m']:.4f} (band {fs['band_m'][0]:.4f}-{fs['band_m'][1]:.4f}), "
                     f"q {fs['q']:.2f}, U ({fs['U'][0]:.0f}, {fs['U'][1]:.0f}) px/s, on the shell {fs['score']:.2f} against drift alone "
                     f"{fs['drift_only']:.2f} and shuffled {fs['null']:.2f}, |k| span x{fs['k_span']:.1f}"
                     + ("; no power: " + "; ".join(fs["no_power"]) if fs.get("no_power") else "") + ".")
    return L


def main():
    import argparse
    from . import forensics as vf
    from . import clip as vclip
    from .report import emit, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", help="a clip, or the held display video `mcdonald stabilize` wrote")
    ap.add_argument("--n0", type=int, default=1)
    ap.add_argument("--n1", type=int, required=True)
    ap.add_argument("--patch", action="append", metavar="X0,Y0,N", help="a square patch of sea (repeat; default: a tiling)")
    ap.add_argument("--held", metavar="STABILIZE_CSV", help="the stabilize CSV of a held video: its ok and repeat flags")
    ap.add_argument("--static", metavar="A-B,C-D", help="frame ranges whose median is the fixed pattern to take out "
                                                        "(default: the window's own median)")
    ap.add_argument("--lam-min", type=float, default=LAM_MIN, help="shortest wavelength read, px")
    ap.add_argument("--lam-max", type=float, help="longest wavelength read, px (default: a third of the patch)")
    ap.add_argument("--q", type=float, help="hold the along/across ratio at this value (1/sin depression)")
    ap.add_argument("--truth", metavar="M_X,Q", help="a scale known from the scene, drawn on the figure")
    ap.add_argument("--shuffles", type=int, default=N_SHUFFLE)
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        video, tag, _ = vf.resolve(args.video)
        clip = vclip.Clip(video, None, args.n0, args.n1, extract=False)
        out = vclip.out_prefix(args.out, tag)
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
        patches = [tuple(int(v) for v in s.split(",")) for s in args.patch] if args.patch else None
        static = [tuple(int(v) for v in r.split("-")) for r in args.static.split(",")] if args.static else None
        truth = tuple(float(v) for v in args.truth.split(",")) if args.truth else None
        found = measure(video, clip.W, clip.H, clip.fps, clip.n0, clip.n1, patches, args.held, static, args.lam_min, args.lam_max,
                        args.q, truth, out, progress=print, n_shuffle=args.shuffles)
        print("\n".join(said(found.fields)))
        for w in found.no_power:
            print(f"  no power: {w[1]}")
        for f in found.files:
            print(f"  wrote {f}")
    code = vclip.EXIT_NOTHING if found.no_power else 0
    if args.json:
        emit(found.envelope("waves", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
