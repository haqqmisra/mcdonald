"""Breaks beyond the wander, dated, and each set against the scene (E2, E3, B16; method section 51).

The speed band (`kinematics.speed_band`, section 32) found that every recorded track wanders: the scatter about a straight
line is the path bending, seconds long, not the centroid's jitter. `camera.rate_steps` cuts a track into straight lines with
a penalty computed from white jitter, so on a wandering track it finds a "step in the rate" wherever the wander bends --
1,267 stretches on 44 recorded tracks, 12-16 on each of PR135's 150-frame members, about one a wingbeat wiggle (the
economics survey of 2026-10-28, its §1.3 and §6.3). What a case needs is a change the wander cannot explain, and when it
happened, with an interval on the date. Econometrics has asked that question for sixty years: Chow (1960) at a known date,
Andrews (1993) at an unknown one -- the largest Wald statistic over the candidate dates, with 15 % of the stretch trimmed
from each end, where nothing can be said -- and Bai (1997) for an interval on the date.

**The scan** (`scan`). Each coordinate is the band's model -- a line, the fitted Matérn wander (and the bird's beat beside
it, M8, where the band holds one), the nugget -- with a hinge (t - tau)+ added to the mean: a change of velocity at tau. Its
generalised-least-squares Wald statistic under the fitted covariance, both coordinates summed, is maximised over tau inside
the trimmed stretch. The null is drawn, not read off a table: tracks with the same covariance and no break (the whitened
draws are standard normal, so a draw costs a projection), the sup taken the same way on each, and p is the share at or above
the track's own (a parametric bootstrap of Andrews' test). The change's size and direction are the hinge's coefficients at
the date. The interval on the date is the same bootstrap with the break put in: the track's own change at its own date
added to every draw, the date found again on each, and the middle 95 % of those dates (Bai's interval in its simulated
form, since the noise is the fitted covariance and not white). The trimmed ends are NO POWER and are said as such. A track
longer than the band's window is scanned in the band's own windows (`kinematics._windows`), each p multiplied by their
number (Bonferroni).

**Against the scene** (`against_scene`). An event study sets a stock against its market at an announcement (Fama, Fisher,
Jensen & Roll 1969; MacKinlay 1997); for a turning camera the market model is exact -- a rotation moves every point of the
picture by the same pixels, so beta is 1 -- and the object's *abnormal* change of velocity at its break is its own less the
scene's. The scene's motion frame by frame comes from `layers`' overlapping k-frame shifts, S[n + k] - S[n] = dx[n], solved
for S at every frame by least squares with a light penalty on its second differences (`scene_path`): Denton's (1971)
benchmarking turned round, the per-frame series recovered from overlapping sums. A held picture comes out as a frame that
did not move, on the video's clock, which a k-frame average never shows (PR144's hold at frame 732: 0.1 px,
then -42 at the catch-up, against -21 a frame around it). The object's change is the difference of two straight lines a
second long either side of the date (two frames left out), its error from the track's own fitted covariance over both
windows (the lines' weights through the covariance: their errors are not independent where the wander is longer than a
second); the scene's is the difference of its mean rates over the same frames, each with a Newey-West (1987) error. Where
`layers` holds the scene still on screen even over a second in more than `layers.SCENE_SHARE` of its pairs -- its own NO
POWER, "an upper limit, not a measurement" -- there is no market to set the object against: NO POWER, never a zero (13 of
the 14 reference case files). The event date is chosen where the object's break is largest, so the abnormal change's z
measures attribution given a break, not whether there is one; the scan does that.

**For a group** (`common`, `dispersion`). A break common to several members (Bai, Lumsdaine & Stock 1998): their Wald
statistics summed at a shared date, the null drawn for each from its own covariance, independently -- the date sharpens the
more members share it, and members not significant alone can be decisive together (PR097's objects 1-4). And event-induced
dispersion (Boehmer, Musumeci & Poulsen 1991), read across members: a camera's slew adds one velocity to every member, so the
members' changes at the event are no more spread than on ordinary dates; members that turn on their own spread more.

numpy and scipy only.
"""
import csv
import math

import numpy as np
from scipy import linalg, stats

from . import kriging as kg

TRIM = 0.15              # the share of the stretch at each end where no break is looked for (Andrews 1993): NO POWER there
BREAK_MIN = 40           # points the scan needs (the survey's floor: fewer, and a 15 % end is a handful of points)
DRAWS = 400              # tracks drawn from the fitted covariance with no break: the scan's null, and the date's interval
GROUP_DRAWS = 2000       # ... for a group's common break (the survey's B)
SEED = 20261107          # the draws' seed: the same track gives the same p and interval twice
ALPHA = 0.05             # a break is named where its p is under this: on tracks drawn with a recorded track's own covariance
                         # and no break, the scan names one 5 % of the time by construction (measured: the survey's 1 of 40
                         # at 5 %; this module's own draws in tests/test_breaks.py and method section 51). A judgement call
                         # on the level, flagged: the survey's measurements (22 of 44 recorded tracks) are at 5 %
DATE_LEVEL = 0.95        # the interval on the date: the middle 95 % of the dates found again on the draws with the break in.
                         # Measured on drawn tracks with the recorded tracks' own covariances and a change of four of the
                         # wander's velocity sds (method section 51): it held the planted date more often than 95 % -- wider
                         # than it need be, so the words give the interval and not its level
EVENT_S = 1.0            # s: the event study's windows either side of the date (the survey's)
EVENT_GAP = 2            # frames left out either side of the date
EVENT_SHARE = 0.8        # the share of a window's frame steps the scene must cover for its rate there to count
EVENT_P = 0.05           # an abnormal (or a scene's) change is said to be there where its two-coordinate test passes this
SCENE_LAMBDA = 0.01      # the second-difference penalty's weight against the shifts' rows (px per px): the survey's
PLACEBO_STEP = 0.1       # s between a group's placebo dates
PLACEBO_AWAY = 1.0       # s: placebo dates at least this far from the event
SPREAD_CENTILE = 0.95    # the members' spread at the event past this centile of the placebo dates' is extra spread


# ---- the covariance the band fitted -------------------------------------------------------------------------------
def thetas_of(band):
    """Each coordinate's fitted covariance as `kriging` takes it, from the band's own numbers: (sill^2, range, nugget^2),
    with M8's beat (sill^2, range, hz) and its harmonic's sill^2 beside the wander where the band kept one."""
    out = []
    beat = band.get("beat") or {}
    for i in range(2):
        th = (band["sill_px"][i] ** 2, band["range_s"][i], band["nugget_px"][i] ** 2)
        if beat.get("kept") and (beat.get("hz") or [None, None])[i]:
            th = th + (beat["sill_px"][i] ** 2, beat["range_s"][i], beat["hz"][i])
            if (beat.get("harmonic_px") or [None, None])[i]:
                th = th + (beat["harmonic_px"][i] ** 2,)
        out.append(tuple(float(v) for v in th))
    return out


def _cov(t, theta):
    t = np.asarray(t, float)
    return kg._nugget(kg.covariance(t[:, None] - t[None, :], theta), theta)


def kept_points(track, fps, t0=None, t1=None, n0=None, n1=None):
    """(frames, t, x, y): the points the speed band was fitted on -- `kinematics._band_points`, with the glitches and
    excursions `kinematics.jumps` names left out, as `speed_band` leaves them out. None under BREAK_MIN of them."""
    from . import kinematics as kin
    got = kin._band_points(track, fps, t0, t1, n0, n1)
    if got is None:
        return None
    frames, t, x, y, _ = got
    if len(t) < kin.BAND_MIN:
        return None
    jp = kin.jumps(frames, x, y, fps)
    keep = ~jp["drop"] if jp is not None and int((~jp["drop"]).sum()) >= kin.BAND_MIN else np.ones(len(t), bool)
    return frames[keep], t[keep], x[keep], y[keep]


# ---- the scan: a change of velocity at an unknown date ----------------------------------------------------------
def _hinge_parts(t, v, theta, taus, tm):
    """One coordinate's whitened pieces for the hinge scan at the dates taus: (num (m,), den (m,), Hr (n, m), Q (n, 2)) --
    num / den is the hinge's GLS coefficient at each date and num^2 / den its Wald statistic; Hr the whitened hinges with
    the line projected out, Q the whitened line's basis (a draw from the null, whitened, is standard normal)."""
    L = linalg.cholesky(_cov(t, theta), lower=True)
    X = np.c_[np.ones(len(t)), t - tm]
    Q, _ = np.linalg.qr(linalg.solve_triangular(L, X, lower=True))
    H = np.maximum(t[:, None] - taus[None, :], 0.0)
    Hw = linalg.solve_triangular(L, H, lower=True)
    Hr = Hw - Q @ (Q.T @ Hw)
    yw = linalg.solve_triangular(L, np.asarray(v, float), lower=True)
    yr = yw - Q @ (Q.T @ yw)
    den = np.maximum(np.sum(Hr * Hr, axis=0), 1e-300)
    return Hr.T @ yr, den, Hr, Q


def _null(Hr, Q, rng, draws):
    """The hinge's numerator on `draws` whitened null draws: (m, draws)."""
    z = rng.standard_normal((Hr.shape[0], draws))
    return Hr.T @ (z - Q @ (Q.T @ z))


def scan(t, x, y, thetas, draws=DRAWS, seed=SEED, trim=TRIM):
    """The sup-Wald scan for one change of velocity (module docstring), on points at times t (s) with each coordinate's
    fitted covariance `thetas`. None under BREAK_MIN points; else dict(t_s (the date: the change follows this point),
    i (its index), p, sup_wald, null95 (the null's 95th centile), dv_xy (the change, px/s), dv_px_per_s, interval_s
    (DATE_LEVEL), looked_s (the stretch looked in: the trimmed ends are NO POWER), n, draws)."""
    t = np.asarray(t, float)
    n = len(t)
    if n < BREAK_MIN:
        return None
    lo, hi = int(math.ceil(trim * n)), int((1.0 - trim) * n)
    if hi - lo < 3:
        return None
    taus = t[lo:hi]
    tm = float(t.mean())
    rng = np.random.default_rng(seed)
    W = np.zeros(len(taus))
    Wnull = np.zeros((draws, len(taus)))
    parts = []
    for v, th in zip((x, y), thetas):
        num, den, Hr, Q = _hinge_parts(t, v, th, taus, tm)
        nn = _null(Hr, Q, rng, draws)
        W += num ** 2 / den
        Wnull += (nn ** 2 / den[:, None]).T
        parts.append((num, den, Hr, nn))
    j = int(np.argmax(W))
    sup = float(W[j])
    sims = Wnull.max(axis=1)
    p = (1 + int(np.sum(sims >= sup))) / (draws + 1)
    dv = [float(num[j] / den[j]) for num, den, _, _ in parts]
    # the date found again on the same draws with the track's own change put in at its own date
    Walt = np.zeros((draws, len(taus)))
    for (num, den, Hr, nn), d in zip(parts, dv):
        alt = nn + d * (Hr.T @ Hr[:, j])[:, None]
        Walt += (alt ** 2 / den[:, None]).T
    found = taus[np.argmax(Walt, axis=1)]
    a = (1.0 - DATE_LEVEL) / 2.0
    lo_s, hi_s = (float(q) for q in np.quantile(found, [a, 1.0 - a]))
    return dict(t_s=float(taus[j]), i=int(lo + j), p=float(p), sup_wald=sup, null95=float(np.quantile(sims, 0.95)),
                dv_xy=dv, dv_px_per_s=float(math.hypot(*dv)), interval_s=[min(lo_s, float(taus[j])), max(hi_s, float(taus[j]))],
                looked_s=[float(taus[0]), float(taus[-1])], n=int(n), draws=int(draws))


def of_track(track, fps, band, t0=None, t1=None, n0=None, n1=None, n_max=None, alpha=ALPHA):
    """The scan on a track, with the band's covariance (`thetas_of`): on the band's points (`kept_points`), in the band's
    windows where the track is longer than one (each p multiplied by their number). None where the band or the points
    are missing or too few; else the scan of the window with the least p, with `frame` (the date's), `frames_interval`,
    `frames_looked`, `windows`, `p_each` (each window's, multiplied), `found` (p under alpha) and `alpha`."""
    from . import kinematics as kin
    if not band:
        return None
    got = kept_points(track, fps, t0, t1, n0, n1)
    if got is None or len(got[1]) < BREAK_MIN:
        return None
    frames, t, x, y = got
    th = thetas_of(band)
    wins = kin._windows(len(t), n_max or kin.BAND_NMAX)
    best, each = None, []
    for w, (a, b) in enumerate(wins):
        s = scan(t[a:b], x[a:b], y[a:b], th, seed=SEED + w)
        if s is None:
            continue
        s["p"] = min(1.0, s["p"] * len(wins))
        s["i"] += a
        each.append(round(s["p"], 4))
        if best is None or s["p"] < best["p"] or (s["p"] == best["p"] and s["sup_wald"] > best["sup_wald"]):
            best = s
    if best is None:
        return None
    at = lambda ts: int(round(float(ts) * float(fps))) + 1           # t = (frame - 1) / fps
    best.update(frame=int(frames[best["i"]]), frames_interval=[at(v) for v in best["interval_s"]],
                frames_looked=[at(v) for v in best["looked_s"]], windows=len(wins), p_each=each,
                found=bool(best["p"] < alpha), alpha=float(alpha), fps=float(fps))
    return best


# ---- the scene frame by frame -------------------------------------------------------------------------------------
def read_layers_rows(path):
    """A `layers` CSV's rows: (frames, dx, dy, k) of the pairs' k-frame shifts -- the largest motion group's ("all"),
    else the streaked or the evenly textured layer's where that is all the pair has; NaN where none."""
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(ln for ln in f if not ln.startswith("#"))
        cx = next(c for c in rd.fieldnames if c.startswith("all_dx"))
        k = int(cx[len("all_dx"):])
        fr, dx, dy = [], [], []
        for r in rd:
            if not str(r.get("frame", "")).strip().isdigit():
                continue
            vals = []
            for q in (f"dx{k}", f"dy{k}"):
                v = np.nan
                for c in ("all", "striated", "isotropic"):
                    s = r.get(f"{c}_{q}")
                    if s not in (None, "") and not math.isfinite(v):
                        v = float(s)
                vals.append(v)
            fr.append(int(r["frame"]))
            dx.append(vals[0])
            dy.append(vals[1])
    return np.array(fr, int), np.array(dx), np.array(dy), k


def scene_path(frames, dx, dy, k, lam=SCENE_LAMBDA):
    """The scene's position in the picture at every frame (module docstring: Denton turned round), from the pairs' k-frame
    shifts: least squares on S[a + k] - S[a] = dx[a] with lam times each second difference of S pulled to zero and S at the
    first frame 0, solved banded. Returns dict(frames (every frame from the first pair's to the last's + k), X, Y (px),
    covered (bool a frame step: a measured pair spans it), k) or None under ten measured pairs."""
    frames = np.asarray(frames, int)
    ok = np.isfinite(dx) & np.isfinite(dy)
    if ok.sum() < 10:
        return None
    f0 = int(frames.min())
    N = int(frames.max()) - f0 + k + 1
    idx = frames[ok] - f0
    u = max(k, 2)
    diag = {d: np.zeros(N - d) for d in range(u + 1)}
    np.add.at(diag[0], idx, 1.0)
    np.add.at(diag[0], idx + k, 1.0)
    np.add.at(diag[k], idx, -1.0)
    l2 = lam * lam
    for j in range(1, N - 1):                       # (e[j-1] - 2 e[j] + e[j+1]) as an outer product
        diag[0][j - 1] += l2
        diag[0][j] += 4 * l2
        diag[0][j + 1] += l2
        diag[1][j - 1] += -2 * l2
        diag[1][j] += -2 * l2
        diag[2][j - 1] += l2
    diag[0][0] += 1.0                               # the first frame's place, 0
    ab = np.zeros((u + 1, N))
    for d in range(u + 1):
        ab[u - d, d:] = diag[d]
    out = {}
    for name, v in (("X", dx), ("Y", dy)):
        rhs = np.zeros(N)
        np.add.at(rhs, idx + k, v[ok])
        np.add.at(rhs, idx, -v[ok])
        out[name] = linalg.solveh_banded(ab, rhs, lower=False)
    cover = np.zeros(N - 1, int)
    for i in idx:
        cover[i:i + k] += 1
    return dict(frames=np.arange(f0, f0 + N), X=out["X"], Y=out["Y"], covered=cover > 0, k=int(k))


def _newey_west(v):
    """Newey-West (1987) standard error of the mean of v: Bartlett weights, 4 (n/100)^(2/9) lags."""
    v = np.asarray(v, float)
    n = len(v)
    lags = int(4 * (n / 100.0) ** (2.0 / 9.0))
    e = v - v.mean()
    s = float(e @ e) / n
    for q in range(1, min(lags, n - 1) + 1):
        s += 2 * (1 - q / (lags + 1)) * float(e[:-q] @ e[q:]) / n
    return float(math.sqrt(max(s, 0.0) / n))


def _slope_weights(tt):
    c = tt - tt.mean()
    return c / float(c @ c)


def against_scene(brk, frames, t, x, y, thetas, scene, fps, held_share=None):
    """The event study at the break `brk` (`of_track`'s): the object's change of velocity, the scene's (`scene_path`'s) over
    the same frames, and the abnormal change, each coordinate with its error, and the verdict. `held_share` is `layers`'
    share of pairs held still even over a second: past `layers.SCENE_SHARE` there is no scene to set the object against.
    The verdict reads two tests at EVENT_P: whether the abnormal change is there (both coordinates, chi-square on two degrees
    of freedom), and whether the scene changed the way the object did (its change along the object's, `share` of it, one
    coordinate, past the two-sided z): the scene changed that way and nothing is left over, "the camera's"; something is left
    over and the scene did not change that way, "not the camera's"; both, "partly the camera's"; neither, "undecidable" (a
    second either side does not hold enough of the track or the scene to say).
    Returns dict(power (False with `why` where it cannot decide), frames (the two windows), object, scene, abnormal (px/s,
    [x, y]), each's *_err, p_abnormal, share, share_err, z_scene, verdict)."""
    from . import layers
    if held_share is not None and held_share > layers.SCENE_SHARE:
        return dict(power=False, why=f"the scene is held still on screen even over a second in {held_share:.0%} of its frame "
                                     "pairs: the background's motion is an upper limit there, not a measurement")
    if scene is None:
        return dict(power=False, why="no measured scene: `layers` found no motion of the background to set the object against")
    f = int(brk["frame"])
    w = int(round(EVENT_S * fps))
    wins = ((f - EVENT_GAP - w, f - EVENT_GAP), (f + EVENT_GAP, f + EVENT_GAP + w))
    frames = np.asarray(frames, int)
    sel = [np.nonzero((frames >= a) & (frames < b))[0] for a, b in wins]
    if min(len(s) for s in sel) < 8:
        return dict(power=False, why=f"fewer than 8 tracked points in a second either side of frame {f}")
    sf = scene["frames"]
    steps = [np.nonzero((sf[:-1] >= a) & (sf[:-1] < b))[0] for a, b in wins]
    if min(len(s) for s in steps) < max(4, int(EVENT_SHARE * w)) or min(scene["covered"][s].mean() for s in steps) < EVENT_SHARE:
        return dict(power=False, why=f"the scene's motion was not measured over a second either side of frame {f}")
    both = np.r_[sel[0], sel[1]]
    out = dict(power=True, frames=[[int(a), int(b) - 1] for a, b in wins])
    obj, oerr, scn, serr = [], [], [], []
    for v, th, S in ((x, thetas[0], scene["X"]), (y, thetas[1], scene["Y"])):
        v = np.asarray(v, float)
        tb, ta = (np.asarray(t, float)[s] for s in sel)
        c = np.r_[-_slope_weights(tb), _slope_weights(ta)]
        obj.append(float(c @ v[both]))
        oerr.append(float(math.sqrt(max(c @ _cov(np.asarray(t, float)[both], th) @ c, 0.0))))
        rate = [np.diff(S)[s] * fps for s in steps]
        scn.append(float(rate[1].mean() - rate[0].mean()))
        serr.append(float(math.hypot(_newey_west(rate[0]), _newey_west(rate[1]))))
    ab = [o - s for o, s in zip(obj, scn)]
    aerr = [math.hypot(a, b) for a, b in zip(oerr, serr)]
    p_ab = float(stats.chi2.sf(sum((a / max(e, 1e-12)) ** 2 for a, e in zip(ab, aerr)), 2))
    # the scene's change along the object's: the share of it the camera accounts for, and whether the scene changed that way
    size = math.hypot(*obj)
    u = (obj[0] / size, obj[1] / size) if size > 0 else (1.0, 0.0)
    along = scn[0] * u[0] + scn[1] * u[1]
    along_err = math.hypot(serr[0] * u[0], serr[1] * u[1])
    z_scene = along / max(along_err, 1e-12)
    zc = stats.norm.isf(EVENT_P / 2.0)
    moved, own = z_scene >= zc, p_ab < EVENT_P
    verdict = ("partly the camera's" if moved and own else "the camera's" if moved else "not the camera's" if own else "undecidable")
    out.update(object=obj, object_err=oerr, scene=scn, scene_err=serr, abnormal=ab, abnormal_err=aerr, p_abnormal=p_ab,
               share=along / size if size > 0 else None, share_err=along_err / size if size > 0 else None, z_scene=float(z_scene),
               verdict=verdict)
    return out


def matched(brk, events, near=0):
    """The camera's events (`[{frame, what}]`, the camera stage's) inside the break's date interval, `near` frames either
    side (the report gives `camera.EVENT_NEAR`, the frames within which the camera stage puts a rate step at an event: a date
    found to the frame is matched as a step is): the match rule -- a break with a camera event inside its interval is the
    camera's until shown otherwise."""
    if not brk or not events:
        return []
    a, b = brk["frames_interval"]
    return [e for e in events if a - near <= int(e["frame"]) <= b + near]


# ---- a group: a break common to its members, and the spread at it ----------------------------------------------------
def common(members, fps, draws=GROUP_DRAWS, seed=SEED, trim=TRIM, alpha=ALPHA):
    """A break common to a group's members (Bai, Lumsdaine & Stock 1998): `members` [(t, x, y, thetas)], each on the video's
    clock. Their hinge Wald statistics summed at each date on the frame grid all of them cover (15 % trimmed), the null drawn
    for each member from its own covariance, independently. None where they share under BREAK_MIN frames; else dict(t_s, p,
    sup_wald, null95, interval_s (the date found again with each member's own change put in), dv_xy (each member's change at
    the date), each_t_s (each member's own date), looked_s, members, found)."""
    lo_t = max(float(np.min(m[0])) for m in members)
    hi_t = min(float(np.max(m[0])) for m in members)
    span = hi_t - lo_t
    if span * fps < BREAK_MIN or len(members) < 2:
        return None
    taus = np.arange(lo_t + trim * span, hi_t - trim * span, 1.0 / fps)
    if len(taus) < 3:
        return None
    rng = np.random.default_rng(seed)
    W, Wnull = np.zeros(len(taus)), np.zeros((draws, len(taus)))
    parts, each = [], []
    for t, x, y, th in members:
        t = np.asarray(t, float)
        tm = float(t.mean())
        wm = np.zeros(len(taus))
        for v, theta in zip((x, y), th):
            num, den, Hr, Q = _hinge_parts(t, v, theta, taus, tm)
            nn = _null(Hr, Q, rng, draws)
            W += num ** 2 / den
            wm += num ** 2 / den
            Wnull += (nn ** 2 / den[:, None]).T
            parts.append((num, den, Hr, nn))
        each.append(float(taus[int(np.argmax(wm))]))
    j = int(np.argmax(W))
    sims = Wnull.max(axis=1)
    p = (1 + int(np.sum(sims >= W[j]))) / (draws + 1)
    Walt = np.zeros((draws, len(taus)))
    dv = []
    for num, den, Hr, nn in parts:
        d = float(num[j] / den[j])
        dv.append(d)
        Walt += ((nn + d * (Hr.T @ Hr[:, j])[:, None]) ** 2 / den[:, None]).T
    found = taus[np.argmax(Walt, axis=1)]
    a = (1.0 - DATE_LEVEL) / 2.0
    lo_s, hi_s = (float(q) for q in np.quantile(found, [a, 1.0 - a]))
    return dict(t_s=float(taus[j]), p=float(p), sup_wald=float(W[j]), null95=float(np.quantile(sims, 0.95)),
                interval_s=[min(lo_s, float(taus[j])), max(hi_s, float(taus[j]))],
                dv_xy=[[dv[2 * i], dv[2 * i + 1]] for i in range(len(members))], each_t_s=each,
                looked_s=[float(taus[0]), float(taus[-1])], members=len(members), draws=int(draws), found=bool(p < alpha))


def _dv_window(t, v, tau, gap):
    a = (t >= tau - gap - EVENT_S) & (t < tau - gap)
    b = (t >= tau + gap) & (t < tau + gap + EVENT_S)
    if a.sum() < 8 or b.sum() < 8:
        return None
    return float(np.polyfit(t[b], v[b], 1)[0] - np.polyfit(t[a], v[a], 1)[0])


def dispersion(members, tau, fps):
    """Event-induced dispersion read across a group's members (Boehmer, Musumeci & Poulsen 1991): each member's change of
    velocity at `tau` (two lines a second long, EVENT_GAP frames left out), their mean (the common change) and spread (the
    sd across members, both coordinates), against the same on placebo dates every PLACEBO_STEP s at least PLACEBO_AWAY from
    it. None under two members or three placebo dates; else dict(common_px_per_s, spread_px_per_s, placebo_n,
    placebo_common_median, placebo_common_95, spread_centile, extra_spread)."""
    gap = EVENT_GAP / float(fps)
    if len(members) < 2:
        return None
    lo = max(float(np.min(m[0])) for m in members) + EVENT_S + 2 * gap
    hi = min(float(np.max(m[0])) for m in members) - EVENT_S - 2 * gap

    def at(tt):
        d = [(_dv_window(np.asarray(t, float), np.asarray(x, float), tt, gap), _dv_window(np.asarray(t, float), np.asarray(y, float), tt, gap))
             for t, x, y, _ in members]
        if any(q[0] is None or q[1] is None for q in d):
            return None
        d = np.array(d)
        return float(np.hypot(*d.mean(axis=0))), float(np.hypot(*d.std(axis=0, ddof=1)))

    ev = at(tau)
    pl = [at(tt) for tt in np.arange(lo, hi, PLACEBO_STEP) if abs(tt - tau) >= PLACEBO_AWAY]
    pl = np.array([q for q in pl if q is not None])
    if ev is None or len(pl) < 3:
        return None
    centile = float(np.mean(pl[:, 1] < ev[1]))
    return dict(common_px_per_s=ev[0], spread_px_per_s=ev[1], placebo_n=int(len(pl)),
                placebo_common_median=float(np.median(pl[:, 0])), placebo_common_95=float(np.quantile(pl[:, 0], 0.95)),
                placebo_spread_median=float(np.median(pl[:, 1])), spread_centile=centile,
                extra_spread=bool(centile > SPREAD_CENTILE))


def together(objects, fps):
    """The objects of one video followed over the same frames, tested for a change common to them (`common`) and, where one
    is found, for the spread at it (`dispersion`). `objects` is [(number, track, band)], each object's whole track and its
    speed band. Objects are taken in the order they start, and one joins the set before it while their common stretch stays
    BREAK_MIN frames or more (else it starts a set of its own); a set of two or more is tested. Returns [dict(objects
    (their numbers), span_s, common, dispersion, alone (each one's own scan found it: [bool or None]))]."""
    pts = []
    for k, trk, band in objects:
        got = kept_points(trk, fps) if band else None
        if got is not None and len(got[1]) >= BREAK_MIN:
            pts.append((k, got, thetas_of(band)))
    pts.sort(key=lambda p: float(p[1][1][0]))
    sets, cur = [], []
    for p in pts:
        trial = cur + [p]
        lo, hi = max(float(q[1][1][0]) for q in trial), min(float(q[1][1][-1]) for q in trial)
        if (hi - lo) * fps >= BREAK_MIN:
            cur = trial
        else:
            if len(cur) >= 2:
                sets.append(cur)
            cur = [p]
    if len(cur) >= 2:
        sets.append(cur)
    out = []
    for s in sets:
        members = [(g[1], g[2], g[3], th) for _, g, th in s]
        c = common(members, fps)
        if c is None:
            continue
        d = dispersion(members, c["t_s"], fps) if c["found"] else None
        lo, hi = max(float(m[0][0]) for m in members), min(float(m[0][-1]) for m in members)
        out.append(dict(objects=[k for k, _, _ in s], span_s=[lo, hi], common=c, dispersion=d, fps=float(fps)))
    return out


def together_said(t, alone=None):
    """A set of objects tested together (`together`), in sentences for the objects' page (sciencespeak). `alone` is each
    one's own scan's verdict where known ([bool or None])."""
    names = [str(k) for k in sorted(t["objects"])]
    who = "Objects " + (", ".join(names[:-1]) + " and " + names[-1])
    c, d = t["common"], t.get("dispersion")
    if not c["found"]:
        return [f"{who}, followed over the same {t['span_s'][1] - t['span_s'][0]:.1f} s, show no change of velocity together "
                "beyond their own slow weaving."]
    a, b = c["interval_s"]
    when = (f"at {c['t_s']:.2f} s, to within a frame or two" if (b - a) * t.get("fps", 30.0) <= 2.5 else
            f"at {c['t_s']:.2f} s, somewhere between {a:.2f} and {b:.2f} s")
    S = [f"{who} change their velocity together {when}.",
         (f"In {c['draws']:,} sets of tracks drawn with each one's slow weaving alone, none shares a change so large."
          if c["p"] * (c["draws"] + 1) < 1.5 else
          f"Sets of tracks drawn with each one's slow weaving alone share a change so large only {100 * c['p']:.1f} % of the time.")]
    if alone and None not in alone and not any(alone):
        S.append("No one of them shows it clearly alone.")
    if d and not d["extra_spread"]:
        S += [f"At that moment they all change by about the same velocity, {d['common_px_per_s']:.0f} pixels a second, and spread "
              "apart no more than at ordinary moments.",
              "A turn of the camera adds the same velocity to everything in the picture, and so would a turn they all made together."]
    elif d:
        S += ["At that moment they spread apart more than at ordinary moments.", "A turn of the camera alone would not spread them."]
    return S


# ---- the stage's record, and what is said of it -----------------------------------------------------------------
def of_stage(track, fps, band, t0=None, t1=None, n0=None, n1=None, scene_csv=None, layers_fields=None):
    """What the kinematics stage records (`fields["breaks"]`): the scan (`of_track`) and, where it found a break, the event
    study against the scene (`against_scene`, from `scene_csv`, a `layers` CSV of the same frames, and `layers_fields`, its
    stage's fields). None where there is no band or too few points."""
    brk = of_track(track, fps, band, t0, t1, n0, n1)
    if brk is None:
        return None
    brk.pop("i", None)
    if not brk["found"]:
        return brk
    held = ((layers_fields or {}).get("held_still") or {}).get("still_again_share")
    scene = None
    if scene_csv and (held is None or held <= _scene_share()):
        try:
            scene = scene_path(*read_layers_rows(scene_csv))
        except (OSError, StopIteration, ValueError, KeyError):
            scene = None
    if scene_csv is None and held is None:
        brk["scene"] = dict(power=False, why="the background was not measured (the layers step did not run)")
        return brk
    frames, t, x, y = kept_points(track, fps, t0, t1, n0, n1)
    brk["scene"] = against_scene(brk, frames, t, x, y, thetas_of(band), scene, fps, held_share=held)
    return brk


def _scene_share():
    from . import layers
    return layers.SCENE_SHARE


def said(brk):
    """The scan and the event study in a line, for the command line and Measurements (technical)."""
    if not brk:
        return None
    a, b = brk["looked_s"]
    head = (f"none beyond the wander (p {brk['p']:.3g}, the largest at {brk['t_s']:.2f} s"
            if not brk["found"] else
            f"a change of velocity at {brk['t_s']:.2f} s (frame {brk['frame']}; between {brk['interval_s'][0]:.2f} and "
            f"{brk['interval_s'][1]:.2f} s, frames {brk['frames_interval'][0]}-{brk['frames_interval'][1]}, the middle 95 % of "
            f"the dates found again on draws with it in) by "
            f"({brk['dv_xy'][0]:+.1f}, {brk['dv_xy'][1]:+.1f}) px/s, more than the track's own wander explains (p {brk['p']:.3g}")
    head += (f" against {brk['draws']} tracks drawn with its fitted covariance and no break"
             + (f", {brk['windows']} windows, each p times {brk['windows']}" if brk.get("windows", 1) > 1 else "")
             + f"); looked for over {a:.2f}-{b:.2f} s, none in the first and last {100 * TRIM:.0f} % (no power there)")
    sc = brk.get("scene")
    if not sc:
        return head
    if not sc.get("power"):
        return head + f"; against the scene: no power ({sc['why']})"
    fx = lambda v, e: f"({v[0]:+.1f} ± {e[0]:.1f}, {v[1]:+.1f} ± {e[1]:.1f})"
    return (head + f"; against the scene, a second either side: the object's velocity changed by {fx(sc['object'], sc['object_err'])} "
            f"px/s, the scene's by {fx(sc['scene'], sc['scene_err'])}, the abnormal change {fx(sc['abnormal'], sc['abnormal_err'])} "
            f"(p {sc['p_abnormal']:.2g}); the scene's change along the object's is {sc['share']:.2f} ± {sc['share_err']:.2f} of it "
            f"({sc['z_scene']:+.1f} sigma): {sc['verdict']}")
