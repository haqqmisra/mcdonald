"""k from the camera's own slew: the scene's shift against the north pointer's turn.

  mcdonald slew VIDEO [--north CSV] [--layers CSV] [--window T0:T1 ...] [--depression D]
  mcdonald slew VIDEO --platform CSV --los CSV [--layers CSV] [--window T0:T1 ...]   # a data bar in place of the pointer

During a slew the scene moves on the screen by the camera's rotation. `symbology` reads the
north pointer every frame, and its angle theta (clockwise from screen-up, = -azimuth) is the
line of sight's azimuth; `layers` measures the scene's shift in pixels. Regressed one on the
other over a slew, the scene's horizontal shift has slope k cos(e) in pixels per degree of
the pointer, with e the line of sight's depression: the matchmove with survey data (a nodal
solve, Hartley 1997, with the angles read off the screen). It is the fourth route to the
angular scale in `scale` and the only one that is a measurement on a clip with no graticule.

**The model.** With X the scene's horizontal shift (px, image-right positive) and theta the
pointer's angle (deg),

    X(t) = a_s + c theta(t) + b t   (+ b2 t^2 with --degree 2),   c = k cos(e)

The b term is the platform: a camera that holds the ground still (PR148, PR149) turns the
pointer at the rate the aircraft's motion across the line of sight asks for, d(theta)/dt =
-b / c, while the scene stays where it is. Only the turn beyond that hold moves the scene, so
a window where the pointer turns at one steady rate cannot separate c from b: the lever is
the part of theta that a steady rate does not explain, the slew's start and stop. a_s is one
offset for each unbroken stretch of the scene's chain (short runs of steps with no consensus
are bridged at the velocity either side; a longer run breaks it).

**Which way round.** The pointer is the noisy one (a glyph drawn on a grid, PR148's about
3.25 px across, so it sits still and jumps) and the scene's chain is not, so theta is regressed
on X and t, and c is the inverse of that slope: noise in theta does not bias it. The forward
fit, X on theta and t, is the check: the pointer's noise pulls it low by 1 - 1 / (1 + (scatter
/ lever)^2), and with noise in both the true slope lies between the two, which is reported
beside it. Apart by more than MAX_APART, the noise decides the slope and the stage says so.

**Three outcomes a window.** The pointer REGISTERS the slew (beta's 95 % interval above zero):
c, checked. It does NOT: a floor, c >= 1 / B with B the interval's larger side -- which stands
only where another window of the clip registers a slew, because a pointer blind to the turret
(north against the platform's heading) gives a floor at any k. It turns AGAINST the scene: the
pointer is not reading the turret's azimuth with this sign.

**What it gives.** c is k cos(e): a lower bound on k (cos e <= 1), so W / c is a CEILING on
the horizontal field of view, reached only at a horizontal look. With the depression known
(`--depression`; from the ship's proportions on PR149, or from `waves`' q = 1 / sin e) the
field of view itself. An upper bound on the field is an upper bound on every angular rate,
so it is the direction a ceiling on a speed needs.

**What it assumes, each said on every run.**
- The pointer reads azimuth (a dial, theta = -az). If it draws ground north *projected* into
  the image, its rate is the azimuth's times sin(e) / (sin^2(e) cos^2(b) + sin^2(b)), b the
  bearing of north from the line of sight: up to 1 / sin(e) faster or sin(e) slower, and c
  is off by that factor. A clip whose data bar gives the sensor's azimuth (PR051's BRG)
  settles it for that sensor.
- The image is level (no roll about the line of sight), so a turn in azimuth moves the scene
  across the image, not up it. The scene's vertical shift is fitted the same way: a
  theta-driven motion off the horizontal by more than MAX_TILT_DEG means the image is rolled
  or the elevation moved in step with the azimuth, and then c lies between the horizontal
  slope and the whole one, which the stage reports as the bracket.
- The hold rate is steady over the window (the aircraft's speed and the aim point's range
  constant): the fit with a quadratic in time is the check, and a window round each whole
  slew, a few seconds either side, is the defence.
"""
import csv
import math
import shlex
import textwrap
from pathlib import Path

import numpy as np

from . import symbology

MIN_LEVER = 1.5       # the pointer's swing beyond a steady rate (rms) must be this many times a reading's scatter
MIN_LEVER_STEPS = 0.55  # ... and this share of the pointer's grid step: on synthetic staircases (eight phases of the
                        # grid each) c came back within 9 % at 0.55 of a step, 6 % at 0.7, 1.5 % at 1, and 15-26 %
                        # off under 0.45 (2026-10-19)
GRID_ERR = 0.025      # the grid's share of c at a lever of L steps is about GRID_ERR / L^2 at worst (the same runs)
MIN_SCENE_LEVER = 8.0  # px: the scene's motion beyond a steady drift (rms); under it the camera did not slew
MAX_APART = 0.35      # the forward slope is pulled low by the pointer's noise, by 1 - 1/(1 + (scatter/lever)^2):
                      # further apart than this and the noise, not the slew, decides the slope
MAX_REL_ERR = 0.25    # the bootstrap's 16-84 % half-width over c
MAX_DEGREE_SHIFT = 0.15  # c with a quadratic hold rate may differ from c with a steady one by this share
MAX_TILT_DEG = 20.0   # the theta-driven scene motion may be this far off the horizontal before it is a bracket
MIN_SAMPLES = 30
LINE_SHARE = 0.9      # the path filter's line judges unless it misses more than this share of its window...
CURVE_SHARE = 0.95    # ...and a parabola by consensus explains this much of it: then the camera is turning round
MIN_STRETCH_S = 1.0   # the scene's chain must hold together this long on average in a window: each piece has its own
                      # offset, and the lever between pieces is lost (PR144's sea alone came in 241 pieces)
MAX_TWO_GROUPS = 0.2  # with --layer all, pairs with two motion groups over this share: the largest group switches between
                      # layers moving at different rates, and the chain mixes them (PR144: sea and cloud tops 97 px/s apart)
MIN_COVER = 0.6       # a pointer reading smoothed as the scene's chain is smoothed needs this share of its kernel
N_BOOT = 400
BLOCK_S = 1.0         # the bootstrap's blocks: neighbouring samples share the smoothing and the pointer's step
MIN_PIECE_S = 3.0     # an automatic window cut at a burst of blank frames keeps the pieces at least this long
MIN_RATE_R = 0.5      # a claim's pointer rate and scene rate must correlate this well at their best lag: PR076's 46-s
                      # window passed every other check on slow curvature a drifting hold mimics, at r 0.24 at every
                      # lag, where PR27's main slew is at 0.98 and PR057a's at 0.90-0.99 (2026-10-20)
RATE_SMOOTH_S = 0.2   # s: the rates are smoothed over this (a Gaussian's sigma) before they are correlated
LAGS = 6              # frames: the pointer is tried this far either way against the scene (PR27's slews peak at -2
                      # and -3: the picture reaches the screen a few frames after the pointer drawn over it)
ZOOM_AGREE = 0.05     # the slew's ratio of c across a measured zoom and the imagery's ratio agree within twice their
                      # combined error, or this share, whichever is larger


# ---- the two series ---------------------------------------------------------------------
def read_north(path, pixel_aspect=1.0):
    """(frame, t, r, theta) from a `symbology` _north.csv, unsolved frames left out.

    With a pixel aspect other than 1 -- a picture drawn wider than it was made, as a 4:3 sensor shown
    full-height in 16:9 is, 1.333 -- the glyph's place is taken back to square pixels before its angle
    is read: theta = atan2(dx / aspect, -dy) about the boresight, which each row gives back as its
    glyph's place minus r along theta. Near the top or bottom of its circle the pointer moves
    sideways, and its angle in the stretched picture is the true one times the stretch (PR051's
    upload: 1.25-1.28 deg of pointer per degree of BRG, 0.94-0.97 at 1.333)."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("theta_deg") not in (None, ""):
                rows.append((int(r["frame"]), float(r["t_s"]), float(r["r_px"]), float(r["theta_deg"]),
                             float(r["glyph_x"]), float(r["glyph_y"])))
    a = np.array(rows, float).reshape(-1, 6)
    fr, t, r, th = a[:, 0].astype(int), a[:, 1], a[:, 2], a[:, 3]
    if pixel_aspect != 1.0 and len(a):
        rad = np.radians(th)
        bx, by = a[:, 4] - r * np.sin(rad), a[:, 5] + r * np.cos(rad)       # the boresight each reading was made about
        dx, dy = (a[:, 4] - bx) / pixel_aspect, a[:, 5] - by
        r, th = np.hypot(dx, dy), np.degrees(np.arctan2(dx, -dy)) % 360.0
    return fr, t, r, th


def read_layers(path, layer="all", errors=False):
    """(frames, t, dx, dy, k, groups) from a `layers` _layers.csv: each pair's k-frame shift of `layer`
    ("all" is the largest motion group), NaN where the pair had no consensus, and how many motion
    groups the pair's templates fell into (NaN where the file does not say). With `errors`, a seventh
    value: each pair's shift error (n, 2) in px over k frames (the largest group's, from its templates'
    own errors; NaN where the file has none -- written before K9)."""
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(ln for ln in f if not ln.startswith("#"))      # a vendored copy says where it came from
        cx = next(c for c in rd.fieldnames if c.startswith(f"{layer}_dx"))
        k = int(cx[len(f"{layer}_dx"):])
        num = lambda s: float(s) if s not in ("", None) else np.nan
        fr, t, dx, dy, gr, er = [], [], [], [], [], []
        for r in rd:
            fr.append(int(r["frame"]))
            t.append(float(r["t_s"]))
            dx.append(num(r[cx]))
            dy.append(num(r[f"{layer}_dy{k}"]))
            gr.append(num(r.get("groups")))
            er.append((num(r.get("err_x_px")), num(r.get("err_y_px"))))
    out = np.array(fr, int), np.array(t), np.array(dx), np.array(dy), k, np.array(gr)
    return out + (np.array(er, dtype=np.float64).reshape(-1, 2),) if errors else out


def kernel(k):
    """The weights a chain of k-frame shifts smooths the scene's path with: averaging the k pairs
    that span one frame step, each the sum of k steps, gives every step its neighbours' shares
    (k - |d|) / k^2. The pointer is smoothed with the same weights, so the two still agree."""
    d = np.arange(-(k - 1), k)
    return d, (k - np.abs(d)) / k ** 2


def scene_path(frames, dx, dy, k, need=None, bridge=None, err=None):
    """The scene's path X, Y (px) at every frame from frames[0] to frames[-1] + k, from the k-frame
    shifts of the pairs that start there, a stretch number for each frame (-1, and no place, inside a
    gap), and how many frame steps were bridged. A step that `need` (half, rounded up) of the k pairs spanning it measured moves by
    their mean; a run of up to `bridge` steps (default 2k) that none measured, with measured steps
    on both sides, moves by the velocity drawn straight across it; a longer run starts a new stretch,
    whose offset the fit carries.

    With `err`, each pair's shift error (n, 2) as `read_layers(errors=True)` gives it, a step is the
    pairs' mean weighed by their inverse variances (a pair without one weighs as the median pair), and
    a sixth value comes back: the path's own error (N, 2) in px along each stretch, from its start --
    the pairs' errors summed as each pair's whole shift enters the path once over its k steps (the k
    steps a pair covers share it, so the steps' errors are not independent); a bridged step adds the
    error of the step before it.

    The bridge is for the slew's own start and end: `layers` leaves out shifts within 4 px of zero
    over k frames and measures a held scene again over a second, so a scene moving 1-4 px in five
    frames -- a slew easing in or out -- has no consensus at all (the synthetic pan of
    tools/slew_selftest.py broke into 24 stretches exactly there, and those steps are the lever)."""
    need = need or (k + 1) // 2
    bridge = 2 * k if bridge is None else bridge
    n0, n1 = int(frames.min()), int(frames.max()) + k
    at = {int(f): i for i, f in enumerate(frames)}
    vx, vy = np.full(n1 - n0, np.nan), np.full(n1 - n0, np.nan)
    ex, ey = np.full(n1 - n0, np.nan), np.full(n1 - n0, np.nan)
    if err is not None:
        err = np.asarray(err, dtype=np.float64).reshape(-1, 2).copy()
        fill = np.nanmedian(err[np.isfinite(dx)], axis=0) if np.isfinite(err[np.isfinite(dx)]).any() else np.ones(2)
        err[~np.isfinite(err)] = np.broadcast_to(fill, err.shape)[~np.isfinite(err)]
        err = np.maximum(err, 1e-3)
    for m in range(n0, n1):                                # the step from frame m to m + 1
        cover = [at[a] for a in range(m - k + 1, m + 1) if a in at and np.isfinite(dx[at[a]])]
        if len(cover) >= need:
            if err is None:
                vx[m - n0], vy[m - n0] = np.mean(dx[cover]) / k, np.mean(dy[cover]) / k
            else:
                wx, wy = 1 / err[cover, 0] ** 2, 1 / err[cover, 1] ** 2
                vx[m - n0], vy[m - n0] = (wx @ dx[cover]) / wx.sum() / k, (wy @ dy[cover]) / wy.sum() / k
                # the step's variance 1 / (k^2 sum w), times k: each pair's whole shift enters the path once over its k steps
                ex[m - n0], ey[m - n0] = np.sqrt(1 / (k * wx.sum())), np.sqrt(1 / (k * wy.sum()))
    bridged = 0
    i = 0
    while i < len(vx):
        if np.isfinite(vx[i]):
            i += 1
            continue
        j = i
        while j < len(vx) and not np.isfinite(vx[j]):
            j += 1
        if i > 0 and j < len(vx) and j - i <= bridge:
            w = (np.arange(i, j) - (i - 1)) / (j - (i - 1))
            vx[i:j] = vx[i - 1] + w * (vx[j] - vx[i - 1])
            vy[i:j] = vy[i - 1] + w * (vy[j] - vy[i - 1])
            ex[i:j], ey[i:j] = ex[i - 1], ey[i - 1]
            bridged += j - i
        i = j
    N = n1 - n0 + 1
    X, Y, S = np.full(N, np.nan), np.full(N, np.nan), np.full(N, -1)
    E = np.full((N, 2), np.nan)
    X[0], Y[0], S[0], E[0] = 0.0, 0.0, 0, 0.0
    s, alive = 0, True
    for i in range(N - 1):
        if np.isfinite(vx[i]):
            if not alive:                                  # a new stretch begins where the steps are measured again
                s += 1
                X[i], Y[i], S[i], E[i], alive = 0.0, 0.0, s, 0.0, True
            X[i + 1], Y[i + 1], S[i + 1] = X[i] + vx[i], Y[i] + vy[i], s
            E[i + 1] = np.sqrt(E[i] ** 2 + np.array([ex[i], ey[i]]) ** 2)
        else:
            alive = False                                  # frames inside a gap have no place on any stretch
    out = np.arange(n0, n1 + 1), X, Y, S, bridged
    return out + (E,) if err is not None else out


def repeated_median(t, y):
    """Siegel's repeated-median line through (t, y): the median over points of the median slope to
    every other point. It stands with up to half the points wrong. Returns (slope, intercept)."""
    dt = t[:, None] - t[None, :]
    dy = y[:, None] - y[None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        sl = np.where(dt != 0, dy / dt, np.nan)
    b = float(np.nanmedian(np.nanmedian(sl, axis=1)))
    return b, float(np.median(y - b * t))


def robust_curve(t, y, tol, tries=60, seed=0):
    """A parabola through (t, y) that most points lie within `tol` of: RANSAC over triples of points (and the
    repeated-median line among the candidates), refitted by least squares on the winner's inliers. It follows a
    pointer that turns round or speeds up, which a line through three seconds does not (a broadcast camera's pan
    reversing at 2.6 deg/s bends 2 deg off any line), and still outvotes a run of mislocks under half the points.
    Returns the polynomial coefficients (highest power first)."""
    t0 = t.mean()
    tc = t - t0
    b, a = repeated_median(tc, y)
    best = np.array([0.0, b, a])
    best_n = int((np.abs(y - np.polyval(best, tc)) <= tol).sum())
    if len(t) >= 6:
        rng = np.random.default_rng(seed)
        for _ in range(tries):
            i = rng.choice(len(t), 3, replace=False)
            if len(np.unique(tc[i])) < 3:
                continue
            c = np.polyfit(tc[i], y[i], 2)
            n_in = int((np.abs(y - np.polyval(c, tc)) <= tol).sum())
            if n_in > best_n:
                best, best_n = c, n_in
    inl = np.abs(y - np.polyval(best, tc)) <= tol
    if inl.sum() >= 4 and len(np.unique(tc[inl])) >= 3:
        best = np.polyfit(tc[inl], y[inl], 2)
    return best, t0


def clean_pointer(frames, r, theta, fps=30.0, tol_px=3.0, jump_px=3.5, window_s=3.0):
    """The pointer's readings with mislocated frames dropped, and theta unwrapped. Returns (keep mask,
    unwrapped theta).

    Two tests. The radius: off the clip's by more than three robust scatters or tol_px -- the pointer
    is drawn at one radius, but on a grid (PR148's "N" moves in 3.25-px steps across, so its radius
    wanders by 2.5 px with the angle and that is not a mislock). The path: more than jump_px along the
    arc off the repeated-median line through the readings within window_s -- the pointer is a gimbal's
    angle and cannot jump and come back, and a template matched at a low score locks onto a stroke of the
    glyph or onto the sea beside it (PR148 read at NCC 0.55-0.65: 0.9-1.4 deg under its neighbours for
    1.2 s at t 3.5-4.7, and at 9-10 and 39-40 s, the second just before the slew, where it would have read
    as the slew's turn). A line by consensus, not a running median, so a run of mislocks up to half the
    window long is outvoted. Where the line misses more than a tenth of the window and a parabola by
    consensus (`robust_curve`) explains 95 % of it, the camera is turning round or speeding up, and the
    parabola judges instead: a broadcast camera's pan, 2026-10-20, lost 48 of 330 true readings at its
    reversals to the line alone. A window holding a mislock run reaches 95 % with neither, and stays with
    the line, which drops the run (a parabola alone kept 22 of a synthetic 30)."""
    med = float(np.median(r))
    mad = 1.4826 * float(np.median(np.abs(r - med)))
    keep = np.abs(r - med) <= max(3 * mad, tol_px)
    th = np.full(len(theta), np.nan)
    th[keep] = symbology.unwrap_theta(theta[keep])
    tol = math.degrees(jump_px / med)
    half = window_s * fps / 2
    idx = np.where(keep)[0]
    fr = frames[idx].astype(float)
    bad = []
    for j in idx:
        near = idx[np.abs(fr - frames[j]) <= half]
        if len(near) >= 7:
            x, y = frames[near].astype(float), th[near]
            b, a = repeated_median(x, y)
            line = a + b * x
            curve = None
            if np.mean(np.abs(y - line) <= tol) < LINE_SHARE:      # the line misses much of the window: a turn,
                c, t0 = robust_curve(x, y, tol, seed=int(frames[j]))   # or a run of mislocks; a parabola that
                fit = np.polyval(c, x - t0)                             # explains nearly all of it is a turn
                if np.mean(np.abs(y - fit) <= tol) >= CURVE_SHARE:
                    curve = np.polyval(c, frames[j] - t0)
            ref = curve if curve is not None else a + b * frames[j]
            if abs(th[j] - ref) > tol:
                bad.append(j)
    keep[bad] = False
    th[~keep] = np.nan
    return keep, th


def smooth_like_scene(frames, theta, k, at_frames):
    """theta at `at_frames`, smoothed with the scene chain's kernel over the readings there are;
    NaN where they cover under MIN_COVER of the kernel's weight."""
    d, w = kernel(k)
    val = dict(zip(frames.tolist(), theta.tolist()))
    out = np.full(len(at_frames), np.nan)
    for i, n in enumerate(at_frames):
        got = [(wi, val[n + di]) for di, wi in zip(d, w) if (n + di) in val and np.isfinite(val[n + di])]
        if got and sum(g[0] for g in got) >= MIN_COVER:
            ws = np.array([g[0] for g in got])
            out[i] = float((ws * np.array([g[1] for g in got])).sum() / ws.sum())
    return out


def pointer_scatter(theta, r_px):
    """(scatter, step) of one reading in degrees. The step is the median jump between successive
    readings that moved at all -- a pointer drawn on a coarse grid sits still and then jumps
    (PR148's "N" moves in steps of about 3.25 px across, so 0.3-0.6 deg at r = 295) -- and is at
    least one pixel across the radius; the scatter is the larger of the step over sqrt(12) and
    what successive differences show (the turn between two frames is far below either)."""
    px = math.degrees(1.0 / r_px)
    dd = np.diff(theta[np.isfinite(theta)])
    if len(dd) < 5:
        return px / math.sqrt(12), px
    moved = np.abs(dd)[np.abs(dd) > 0.25 * px]
    step = max(px, float(np.median(moved))) if len(moved) >= 3 else px
    white = 1.4826 * float(np.median(np.abs(dd - np.median(dd)))) / math.sqrt(2)
    return max(step / math.sqrt(12), white), step


# ---- the fit ----------------------------------------------------------------------------
def _design(seg, t, degree, extra=()):
    """Columns: one offset per stretch, then any extra regressors, then t, t^2 ... (t centred)."""
    segs = np.unique(seg)
    tc = t - t.mean()
    cols = [(seg == s).astype(float) for s in segs] + list(extra) + [tc ** p for p in range(1, degree + 1)]
    return np.column_stack(cols), len(segs)


def _ols(A, y):
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return beta, y - A @ beta


def fit_once(t, theta, X, seg, degree=1):
    """The reverse and forward fits on one set of samples. beta: the pointer's turn per pixel of the
    scene (deg/px), with theta regressed on X and the hold, so c = 1 / beta; hold: the pointer's rate
    while the scene stands still (deg/s, at the window's middle); c_forward: X regressed on theta."""
    A, ns = _design(seg, t, degree, extra=(X,))
    g, _ = _ols(A, theta)
    B, _ = _design(seg, t, degree, extra=(theta,))
    h, _ = _ols(B, X)
    return dict(beta=float(g[ns]), hold=float(g[ns + 1]) if degree >= 1 else 0.0, c_forward=float(h[ns]))


def partial(t, theta, X, seg, degree=1):
    """theta and X with each stretch's offset and the hold (a polynomial in t) taken out: the plot
    whose slope is beta, and whose spreads are the levers."""
    A, _ = _design(seg, t, degree)
    return _ols(A, theta)[1], _ols(A, X)[1]


def bootstrap(t, theta, X, seg, degree=1, n_boot=N_BOOT, block=30, seed=0):
    """beta refitted on moving blocks of the samples, drawn with replacement. beta, not c: the
    pointer may not register a slew at all, and then beta's interval holds zero while c's has no
    top."""
    rng = np.random.default_rng(seed)
    N = len(t)
    block = max(2, min(block, N // 3))
    starts = np.arange(0, N - block + 1)
    out = []
    for _ in range(n_boot):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.choice(starts, size=int(np.ceil(N / block)))])[:N]
        try:
            out.append(fit_once(t[idx], theta[idx], X[idx], seg[idx], degree)["beta"])
        except np.linalg.LinAlgError:
            continue
    return np.array([b for b in out if np.isfinite(b)])


def fit_window(t, theta, X, Y, seg, sigma_theta, degree=1, fps=30.0, n_boot=N_BOOT, seed=0, step_deg=None, block_s=BLOCK_S):
    """Everything the stage says about one window. Three outcomes: the pointer REGISTERS the slew
    (beta's 95 % interval above zero): c = 1 / beta with its interval and checks; it does NOT (the
    interval holds zero): c is at least 1 / beta's 97.5th percentile -- a floor on k and a ceiling
    on the field, or a pointer that is not the line of sight's azimuth; or it turns AGAINST the
    scene (the interval below zero). Samples must be finite."""
    n = len(t)
    out = dict(n=int(n), t0=float(t.min()) if n else None, t1=float(t.max()) if n else None, degree=degree,
               sigma_theta_deg=float(sigma_theta), registered=None, no_power=[])
    if n < MIN_SAMPLES:
        out["no_power"].append(f"only {n} samples with both the pointer and the scene (under {MIN_SAMPLES})")
        return out
    pieces = len(np.unique(seg))
    out.update(pieces=pieces, mean_piece_s=float(n / pieces / fps))
    if out["mean_piece_s"] < MIN_STRETCH_S:
        out["no_power"].append(f"the scene's chain is in {pieces} pieces here, {out['mean_piece_s']:.2f} s each on average "
                               f"(under {MIN_STRETCH_S:g}): each piece's offset is free, and the lever between them is lost")
        return out
    th_p, x_p = partial(t, theta, X, seg, degree)
    _, y_p = partial(t, theta, Y, seg, degree)
    lev_th, lev_x = float(np.sqrt(np.mean(th_p ** 2))), float(np.sqrt(np.mean(x_p ** 2)))
    step_deg = step_deg or sigma_theta * math.sqrt(12)
    out.update(lever_deg=lev_th, lever_over_scatter=lev_th / sigma_theta, lever_over_step=lev_th / step_deg,
               step_deg=float(step_deg), scene_lever_px=lev_x,
               scene_lever_down_px=float(np.sqrt(np.mean(y_p ** 2))),
               slew_direction_deg=float(np.degrees(0.5 * np.arctan2(2 * (x_p * y_p).sum(), (x_p ** 2 - y_p ** 2).sum()))),
               theta_span_deg=float(np.ptp(theta)), scene_span_px=float(np.ptp(X)))
    out["_partial"] = (x_p, th_p)
    if lev_x < MIN_SCENE_LEVER:
        out["no_power"].append(f"the scene moves {lev_x:.1f} px (rms) across beyond a steady drift, under "
                               f"{MIN_SCENE_LEVER:g}: the camera did not slew in azimuth in this window")
        return out
    f = fit_once(t, theta, X, seg, degree)
    out.update(beta_deg_per_px=f["beta"], hold_rate_deg_per_s=f["hold"], c_forward_px_per_deg=f["c_forward"])
    A, ns = _design(seg, t, degree, extra=(X,))
    g, _ = _ols(A, theta)
    out["_hold"] = (t, A @ g - g[ns] * (X - X[0]))           # the fitted pointer with the scene held where it began
    bs = bootstrap(t, theta, X, seg, degree, n_boot, block=int(round(block_s * fps)), seed=seed)
    if len(bs) < 20:
        out["no_power"].append("the bootstrap could not refit the window")
        return out
    q = {p: float(np.percentile(bs, p)) for p in (2.5, 16, 84, 97.5)}
    out["beta_p2_p98"] = [q[2.5], q[97.5]]
    if q[97.5] <= 0:
        out["registered"] = False
        out["no_power"].append("the pointer turns against the scene's motion: it is not reading the camera's azimuth "
                               "here (or reads it with the other sign), or the scene's motion is not the camera's")
        return out
    if q[2.5] <= 0:
        # not registered: the pointer's turn per px of scene is within +-B of zero, so c >= 1 / B -- B the interval's
        # larger side, so an interval pushed below zero by a hold that is not quite steady cannot make a huge floor
        # (PR148 29.8-35.8 s: -7.8e-4 to 5.6e-5 would have read c >= 17756). And only for a slew mostly across: a
        # slew mostly in elevation moves the scene where the azimuth does not reach, and a tilt or a convention
        # leaks into it.
        out["registered"] = False
        if abs(out["slew_direction_deg"]) <= MAX_TILT_DEG:
            out["c_at_least_px_per_deg"] = 1.0 / max(q[97.5], -q[2.5])
        else:
            out["no_power"].append(f"the slew is {out['slew_direction_deg']:+.0f} deg off the horizontal (over "
                                   f"{MAX_TILT_DEG:g}): its elevation share can reach the pointer through a tilted image "
                                   "or a projected north, so it gives no floor")
        return out
    out["registered"] = True
    c = 1.0 / f["beta"]
    out.update(c_px_per_deg=c, c_p16_p84=[1 / q[84], 1 / q[16]], c_p2_p98=[1 / q[97.5], 1 / q[2.5]],
               rel_err=float((1 / q[16] - 1 / q[84]) / 2 / c),
               apart=float(abs(c - f["c_forward"]) / c),
               apart_expected=float(1 - 1 / (1 + (sigma_theta / max(lev_th, 1e-9)) ** 2)),
               between_px_per_deg=sorted([f["c_forward"], c]))
    out["grid_error_share"] = float(GRID_ERR / max(lev_th / step_deg, 1e-9) ** 2)
    if lev_th < MIN_LEVER * sigma_theta:
        out["no_power"].append(f"the pointer turns {lev_th:.3f} deg (rms) beyond a steady rate, {lev_th / sigma_theta:.1f} "
                               f"times a reading's scatter ({sigma_theta:.3f} deg), under {MIN_LEVER:g}: the slew barely "
                               "shows in the pointer")
    elif lev_th < MIN_LEVER_STEPS * step_deg:
        out["no_power"].append(f"the pointer turns {lev_th:.3f} deg (rms) beyond a steady rate, {lev_th / step_deg:.2f} of "
                               f"its grid step ({step_deg:.2f} deg), under {MIN_LEVER_STEPS:g}: the grid can put c off by "
                               f"{out['grid_error_share']:.0%}")
    if out["apart"] > MAX_APART:
        out["no_power"].append(f"the reverse and forward slopes are {out['apart']:.0%} apart (over {MAX_APART:.0%}): "
                               "the pointer's noise is too large for the lever")
    if out["rel_err"] > MAX_REL_ERR:
        out["no_power"].append(f"the bootstrap puts c within +/-{out['rel_err']:.0%} (16-84 %), over +/-{MAX_REL_ERR:.0%}")
    # the steady hold against one that changes: the same samples with the next power of t
    b2 = fit_once(t, theta, X, seg, degree + 1)["beta"]
    out["c_next_degree_px_per_deg"] = float(1 / b2) if b2 > 0 else None
    out["degree_shift"] = float(abs(b2 - f["beta"]) / f["beta"])
    # a still platform (degree 0) has no hold to be unsteady: a steady pan is then the lever itself, and a hold term
    # would take it away -- the shift is reported, and refuses nothing
    if degree >= 1 and out["degree_shift"] > MAX_DEGREE_SHIFT:
        out["no_power"].append(f"with the hold rate allowed to change (a t^{degree + 1} term) c moves by "
                               f"{out['degree_shift']:.0%}: the hold was not steady over the window -- shorten it")
    # the theta-driven motion's direction: Y's slope on theta beside X's
    B, ns = _design(seg, t, degree, extra=(theta,))
    cy = float(_ols(B, Y)[0][ns])
    out["c_vertical_px_per_deg"] = cy
    out["tilt_deg"] = float(math.degrees(math.atan2(cy, c)))
    out["c_whole_px_per_deg"] = float(math.hypot(c, cy))
    out["bracket_px_per_deg"] = sorted([c, out["c_whole_px_per_deg"]]) if abs(out["tilt_deg"]) > MAX_TILT_DEG else None
    return out


def scale_from(c, W, H, depression_deg=None):
    """What c says about k and the field of view: k >= c (cos e <= 1), so W / c and H / c are
    ceilings on the field; with the depression, the field itself."""
    s = dict(k_h_px_per_deg=c, k_h_px_per_rad=c * 180 / math.pi,
             fov_w_ceiling_deg=W / c if c > 0 else None, fov_h_ceiling_deg=H / c if c > 0 else None,
             depression_deg=depression_deg, k_px_per_deg=None, fov_w_deg=None, fov_h_deg=None)
    if depression_deg is not None and c > 0:
        ce = math.cos(math.radians(depression_deg))
        s.update(k_px_per_deg=c / ce, fov_w_deg=W * ce / c, fov_h_deg=H * ce / c)
    return s


# ---- the scene from blocks: `--scene-blocks` (2026-11-02) ---------------------------------
MIN_BLOCKS = 3         # blocks a window needs before the block rule says anything: a slope, an offset and a spread
SHIFT_ALPHA = 0.05     # the level of "the blocks and the pointer agree". The test: across a window's blocks, the correlation between
                       # each block's velocity and the pointer's rate over the same frames, against the same rates circularly shifted
                       # by 1..n-1 blocks -- a null that keeps each series' own smoothness. It passes where the share of shifts
                       # reaching the true alignment's r is SHIFT_ALPHA or under. With n - 1 shifts that takes n >= 1 + 1 / SHIFT_ALPHA
                       # = 21 blocks (42 s at 30 fps), and a window with fewer says so and claims nothing. Measured (2026-11-02, method
                       # 39) against drawn pointers with no relation to the blocks: on PR088 object 2's 51 real blocks the test alone
                       # passes 4.5 % and on a drawn walk of 60 blocks 4.2 % -- its level -- but on PR41's 43 blocks, whose velocity
                       # trends over the clip, 6.5-17.6 % by the pointer's correlation time, and on a drawn scene of one slow swing
                       # 10-12 %: a circular shift breaks a smooth or trending series at the wrap, so there the true alignment's r is
                       # more extreme than its shifts' and the test alone is no guard. A CLAIM -- the test, the bootstrap and every
                       # check below -- came 0-1.5 % of the time on the real blocks and 0.9-2.1 % on the drawn ones, two ramps 0 %:
                       # on a trending series it is the hold's steadiness (MAX_DEGREE_SHIFT) and the bootstrap's width that hold it
BLOCK_UNEVEN = 3.0     # a block's pointer readings must sit on a line within this many of a reading's scatter (rms); further off, the
                       # pointer turned unevenly inside the block (a pan reversing, as the soccer camera's does) and the block has no
                       # one rate to set against the scene's one velocity. A judgement call, measured 2026-11-02 (method 41): steady
                       # blocks of the real clips sit 0.6-2.6 scatters off their line (PR088 median 1.3, max 2.1; PR135 max 1.1; PR41
                       # median 1.5, max 2.6 where the chroma method reads the pointer on half the frames), the soccer camera's three
                       # blocks across a reversal 2.1-4.3: the two overlap, so no cut parts them. 3 keeps every steady real block and
                       # sets aside the sharpest reversal; the verdicts on PR41 and PR088 are the same at 2, 2.5, 3 and no cut, and
                       # a kept reversal block reads c two to five times wrong, so the cut is kept rather than dropped


def block_rates(blocks, pf, pth, sigma, pixel_aspect=1.0, min_readings=10):
    """Each block's velocity beside the pointer's rate over the block's own frames: [dict(start, frames, mid, vx, vy, rate,
    resid_scatters, readings)] for the blocks the pointer covers (readings on `min_readings` frames or more, spanning half the
    block). The rate (deg/frame) is a line through the readings there, and resid_scatters the readings' rms about that line in
    units of one reading's scatter. vx is in square pixels (divided by the pixel aspect) like everything `slew` fits."""
    out = []
    pf = np.asarray(pf)
    pth = np.asarray(pth, float)
    for b in blocks:
        a, n = int(b["start"]), int(b["frames"])
        m = (pf >= a) & (pf < a + n) & np.isfinite(pth)
        if m.sum() < min_readings or np.ptp(pf[m]) < n / 2:
            continue
        x, y = pf[m].astype(float), pth[m]
        p = np.polyfit(x, y, 1)
        resid = float(np.sqrt(np.mean((y - np.polyval(p, x)) ** 2)))
        out.append(dict(start=a, frames=n, mid=a + (n - 1) / 2, vx=float(b["vx"]) / pixel_aspect, vy=float(b["vy"]), rate=float(p[0]),
                        resid_scatters=resid / max(sigma, 1e-9), readings=int(m.sum())))
    return out


def fit_blocks(rows, sigma_theta, degree=1, fps=30.0, n_boot=N_BOOT, seed=0, step_deg=None, alpha=SHIFT_ALPHA):
    """Everything the stage says about one window whose scene is `mcdonald scene`'s blocks (`block_rates`' rows): the rule of
    its own for a scene read 60 frames at a time (method 41).

    In rates, not places: a block gives one velocity, the pointer one rate over the same frames, and the slew's model
    differentiated is  rate = h + v_x / c,  with h the hold (the platform's share of the pointer's turn) and no offset per
    stretch, so the chain's pieces do not enter. The pointer's rate is the noisy one (a glyph on a grid turning a step or
    two a block), so it is regressed on the blocks' velocity and c is the inverse slope, as `fit_window` regresses theta on
    X. The lever is the spread of the blocks' velocities: a steady pan under a hold has none, as in `fit_window`.

    Three outcomes a window, as there. REGISTERED: beta's block bootstrap above zero AND the agreement rarer than SHIFT_ALPHA
    of the circular shifts (degree 1 and up; with no hold fitted, --still or --hold-rate, a steady pan's rates have nothing to
    share, and the bootstrap alone decides, as `measure` skips the rate test there). NOT: a floor from beta's interval, as in
    `fit_window`, where the pointer does not register the blocks' motion; no number at all where the shifts could do it or
    there are too few of them. AGAINST: the pointer turns the other way. The checks a claim must pass are `fit_window`'s,
    with the same constants: the pointer's lever against its scatter and its step, the bootstrap's half-width, the hold
    steady over the window (a hold linear in time moves c by under MAX_DEGREE_SHIFT), and the motion's tilt. The forward
    slope is reported beside the reverse and refuses nothing: with the pointer's rate quantised over 60 frames the two are
    always far apart, and the blocks' own error (about 5 % of a velocity on the soccer camera) is the small one."""
    use = [r for r in rows if r["resid_scatters"] <= BLOCK_UNEVEN]
    n = len(use)
    out = dict(from_blocks=True, n=n, blocks_covered=len(rows), blocks_uneven=len(rows) - n, degree=degree,
               sigma_theta_deg=float(sigma_theta), registered=None, no_power=[],
               t0=float(min(r["mid"] for r in use) - 1) / fps if use else None, t1=float(max(r["mid"] for r in use) - 1) / fps if use else None)
    if n < MIN_BLOCKS:
        out["no_power"].append(f"only {n} block(s) here with the pointer turning evenly over them (under {MIN_BLOCKS})"
                               + (f"; {len(rows) - n} more turned the pointer unevenly inside the block" if len(rows) > n else ""))
        return out
    v = np.array([r["vx"] for r in use])
    w = np.array([r["vy"] for r in use])
    a = np.array([r["rate"] for r in use])
    tm = np.array([r["mid"] for r in use]) / fps
    B = float(np.mean([r["frames"] for r in use]))
    vc, wc, ac = (v - v.mean(), w - w.mean(), a - a.mean()) if degree >= 1 else (v, w, a)
    rms = lambda q: float(np.sqrt(np.mean(q ** 2)))
    lev_x, lev_y, lev_th = rms(vc) * B, rms(wc) * B, rms(ac) * B
    step_deg = step_deg or sigma_theta * math.sqrt(12)
    out.update(lever_deg=lev_th, lever_over_scatter=lev_th / sigma_theta, lever_over_step=lev_th / step_deg, step_deg=float(step_deg),
               scene_lever_px=lev_x, scene_lever_down_px=lev_y, block_frames=B,
               slew_direction_deg=float(np.degrees(0.5 * np.arctan2(2 * (vc * wc).sum(), (vc ** 2 - wc ** 2).sum()))))
    if lev_x < MIN_SCENE_LEVER:
        out["no_power"].append(f"the blocks' velocities differ by {lev_x:.1f} px a block (rms) across"
                               + (" beyond their common motion" if degree >= 1 else "") + f", under {MIN_SCENE_LEVER:g}: the camera "
                               + ("did not change its slew in azimuth in this window" if degree >= 1 else "did not slew in azimuth in this window"))
        return out

    def fit(idx, with_t=False):
        cols = [v[idx]] + ([np.ones(len(idx))] if degree >= 1 else []) + ([tm[idx] - tm.mean()] if with_t else [])
        g, *_ = np.linalg.lstsq(np.column_stack(cols), a[idx], rcond=None)
        return g

    every = np.arange(n)
    g = fit(every)
    beta, hold = float(g[0]), float(g[1]) if degree >= 1 else 0.0
    F = np.column_stack([a] + ([np.ones(n)] if degree >= 1 else []))
    c_forward = float(np.linalg.lstsq(F, v, rcond=None)[0][0])
    out.update(beta_deg_per_px=beta, hold_rate_deg_per_s=hold * fps, c_forward_px_per_deg=c_forward)
    if degree >= 1:
        r = float(np.corrcoef(v, a)[0, 1]) if v.std() > 0 and a.std() > 0 else 0.0
        null = np.array([np.corrcoef(v, np.roll(a, k))[0, 1] for k in range(1, n)])
        reach = int((null >= r).sum())
        out.update(shift_r=r, shift_p=reach / (n - 1), shift_reaching=reach, shifts=n - 1, shift_null_max=float(null.max()))
    rng = np.random.default_rng(seed)
    bs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        if (len(np.unique(v[idx])) < 2) if degree >= 1 else not np.any(v[idx]):     # a slope needs two velocities; through zero, one
            continue
        bs.append(fit(idx)[0])
    bs = np.array([b for b in bs if np.isfinite(b)])
    if len(bs) < 20:
        out["no_power"].append("the bootstrap could not refit the blocks")
        return out
    q = {p: float(np.percentile(bs, p)) for p in (2.5, 16, 84, 97.5)}
    out["beta_p2_p98"] = [q[2.5], q[97.5]]
    if degree >= 1 and n - 1 < 1.0 / alpha:
        out["registered"] = False
        out["no_power"].append(f"{n} blocks: {n - 1} circular shifts of the pointer cannot show their agreement with the blocks to be rarer "
                               f"than 1 in {1 / alpha:.0f} (that takes {math.ceil(1 + 1 / alpha)} blocks, {math.ceil(1 + 1 / alpha) * B / fps:.0f} s: "
                               "the whole clip's, where the case is a part of it)")
        return out
    if q[97.5] <= 0:
        out["registered"] = False
        out["no_power"].append("the pointer turns against the blocks' motion: it is not reading the camera's azimuth here (or reads "
                               "it with the other sign), or the scene's motion is not the camera's")
        return out
    if degree >= 1 and out["shift_p"] > alpha:
        out["registered"] = False
        if q[2.5] > 0:
            out["no_power"].append(f"the blocks and the pointer agree no better than {out['shift_reaching']} of {n - 1} circular shifts of "
                                   f"the pointer do (r {out['shift_r']:.2f}; 1 in {1 / alpha:.0f} allowed): slow changes in both could do it")
            return out
    if q[2.5] <= 0:
        # not registered: the pointer's turn per px of the blocks' motion is within +-B of zero, so c >= 1 / B -- as `fit_window`,
        # and only where the blocks' motion changes mostly across
        out["registered"] = False
        if abs(out["slew_direction_deg"]) <= MAX_TILT_DEG:
            out["c_at_least_px_per_deg"] = 1.0 / max(q[97.5], -q[2.5])
        else:
            out["no_power"].append(f"the blocks' motion changes {out['slew_direction_deg']:+.0f} deg off the horizontal (over "
                                   f"{MAX_TILT_DEG:g}): its elevation share can reach the pointer through a tilted image or a projected "
                                   "north, so it gives no floor")
        return out
    out["registered"] = True
    c = 1.0 / beta
    out.update(c_px_per_deg=c, c_p16_p84=[1 / q[84], 1 / q[16]], c_p2_p98=[1 / q[97.5], 1 / q[2.5]],
               rel_err=float((1 / q[16] - 1 / q[84]) / 2 / c), apart=float(abs(c - c_forward) / c),
               between_px_per_deg=sorted([c_forward, c]), grid_error_share=float(GRID_ERR / max(lev_th / step_deg, 1e-9) ** 2))
    if lev_th < MIN_LEVER * sigma_theta:
        out["no_power"].append(f"the pointer's turn over a block differs from its mean by {lev_th:.3f} deg (rms), {lev_th / sigma_theta:.1f} "
                               f"times a reading's scatter ({sigma_theta:.3f} deg), under {MIN_LEVER:g}: the slew's changes barely show in "
                               "the pointer")
    elif lev_th < MIN_LEVER_STEPS * step_deg:
        out["no_power"].append(f"the pointer's turn over a block differs from its mean by {lev_th:.3f} deg (rms), {lev_th / step_deg:.2f} of "
                               f"its grid step ({step_deg:.2f} deg), under {MIN_LEVER_STEPS:g}: the grid can put c off by "
                               f"{out['grid_error_share']:.0%}")
    if out["rel_err"] > MAX_REL_ERR:
        out["no_power"].append(f"the bootstrap over the blocks puts c within +/-{out['rel_err']:.0%} (16-84 %), over +/-{MAX_REL_ERR:.0%}")
    if degree >= 1:
        b2 = float(fit(every, with_t=True)[0])
        out["c_next_degree_px_per_deg"] = float(1 / b2) if b2 > 0 else None
        out["degree_shift"] = float(abs(b2 - beta) / beta)
        if out["degree_shift"] > MAX_DEGREE_SHIFT:
            out["no_power"].append(f"with the hold rate allowed to change (a term in t) c moves by {out['degree_shift']:.0%}: the hold "
                                   "was not steady over the window -- shorten it (--window)")
    cy = float(np.linalg.lstsq(F, w, rcond=None)[0][0])              # the forward slope down, beside the forward slope across
    out["c_vertical_px_per_deg"] = cy
    out["tilt_deg"] = float(math.degrees(math.atan2(cy, abs(c_forward))))
    out["c_whole_px_per_deg"] = float(c / math.cos(math.radians(out["tilt_deg"]))) if abs(out["tilt_deg"]) < 89 else None
    out["bracket_px_per_deg"] = sorted([c, out["c_whole_px_per_deg"]]) if abs(out["tilt_deg"]) > MAX_TILT_DEG and out["c_whole_px_per_deg"] else None
    return out


def rate_lag(t, theta, X, seg, fps, degree=1, lags=LAGS):
    """How the pointer's rate follows the scene's over a window, and how far c moves if the two are a frame out.

    The rates come from the longest unbroken stretch of the chain, each smoothed over RATE_SMOOTH_S, and are
    correlated with the pointer moved by -lags..lags frames (positive: the pointer's turn after the scene's shift).
    c is refitted (`fit_once`) with the pointer moved by -1, 0 and +1 frames, and at the best lag. A one-frame offset
    is what the k = 2 chain's half-pair would give, and the display may draw the pointer a frame late: on PR27's main
    slew the best lag is -1 (r 0.9813 against 0.9799 at 0) and moves c by 1 %; on PR057a's 2.7-s slew by 5 %."""
    from scipy import ndimage
    fr = np.round(t * fps).astype(int)
    val = dict(zip(fr.tolist(), theta.tolist()))
    segs, counts = np.unique(seg, return_counts=True)
    m = seg == segs[np.argmax(counts)]
    out = dict(rate_r_by_lag={}, best_lag_frames=None, rate_r=None, c_at_lag={})
    if m.sum() >= 3 * LAGS + 10:
        full = np.arange(fr[m].min(), fr[m].max() + 1)
        th_f, X_f = np.interp(full, fr[m], theta[m]), np.interp(full, fr[m], X[m])
        sg = max(RATE_SMOOTH_S * fps, 1.0)
        vth = ndimage.gaussian_filter1d(np.gradient(th_f) * fps, sg)
        vx = ndimage.gaussian_filter1d(np.gradient(X_f) * fps, sg)
        for L in range(-lags, lags + 1):
            p, q = (vth[L:], vx[:len(vx) - L]) if L >= 0 else (vth[:L], vx[-L:])
            r = float(np.corrcoef(p, q)[0, 1]) if p.std() > 0 and q.std() > 0 else 0.0
            out["rate_r_by_lag"][L] = r
        best = max(out["rate_r_by_lag"], key=out["rate_r_by_lag"].get)
        out.update(best_lag_frames=int(best), rate_r=out["rate_r_by_lag"][best])
    for L in sorted({-1, 0, 1} | ({out["best_lag_frames"]} if out["best_lag_frames"] is not None else set())):
        th_l = np.array([val.get(int(n) + L, np.nan) for n in fr])
        k = np.isfinite(th_l)
        if k.sum() >= MIN_SAMPLES:
            b = fit_once(t[k], th_l[k], X[k], seg[k], degree)["beta"]
            out["c_at_lag"][L] = float(1 / b) if b > 0 else None
    c0 = out["c_at_lag"].get(0)
    near = [out["c_at_lag"].get(L) for L in (-1, 1)]
    out["c_shift_one_frame"] = (float(max(abs(c - c0) for c in near if c) / c0)
                                if c0 and any(near) else None)
    return out


# ---- the windows ------------------------------------------------------------------------
def cut(windows, gaps, min_s=MIN_PIECE_S):
    """Windows (t0, t1) with every gap (g0, g1) taken out of them, the pieces under min_s dropped."""
    out = []
    for t0, t1 in windows:
        pieces = [(t0, t1)]
        for g0, g1 in gaps:
            nxt = []
            for a, b in pieces:
                if g1 <= a or g0 >= b:
                    nxt.append((a, b))
                    continue
                if g0 - a >= min_s:
                    nxt.append((a, g0))
                if b - g1 >= min_s:
                    nxt.append((g1, b))
            pieces = nxt
        out += [p for p in pieces if p[1] - p[0] >= min_s]
    return sorted(set((round(a, 3), round(b, 3)) for a, b in out))


def one_state(s):
    """The whole series as one zoom state, where the clip's zooms were not looked for."""
    return dict(bursts=[], states=[dict(state=0, chain=0, magnification=1.0, frames=[int(s["frames"][0]), int(s["frames"][-1])],
                                        t_s=[float(s["t"][0]), float(s["t"][-1])])], looked=False)


def slews(t, vx, fps, min_rate=None, smooth_s=0.5, gap_s=1.0, min_s=0.5, pad_s=3.0):
    """A window round each slew, from pad_s before it starts to pad_s after it stops. A slew is a run of
    frames where the scene's horizontal rate, smoothed over smooth_s, is above min_rate (px/s; default a
    fifth of its largest, at least 20), runs closer than gap_s joined and runs under min_s dropped.

    The whole slew, not its start and its stop apart: the fit takes the hold as steady over the window,
    and half a slew inside a window looks to that check like a hold that changes (the rendered pan read
    c 554 and 480 in windows round its start and its stop, each moved 34 % by a quadratic hold, and 524
    in one round all of it). Different slews are kept apart: PR148's platform share of the pointer's
    turn goes from +0.33 to -0.48 deg/s over the minute."""
    if len(vx) == 0:
        return []
    n = min(max(int(round(smooth_s * fps)), 1), len(vx))   # a zoom state shorter than the smoothing (PR40's: 5 frames)
    v = np.abs(np.where(np.isfinite(vx), vx, 0.0))
    v = np.convolve(v, np.ones(n) / n, mode="same")
    v[~np.isfinite(vx)] = 0.0
    if not v.any():
        return []
    thr = max(min_rate or 0.2 * float(v.max()), 20.0)
    on = v >= thr
    runs, i = [], 0
    while i < len(t):
        if not on[i]:
            i += 1
            continue
        j = i
        while j < len(t) and on[j]:
            j += 1
        if runs and t[i] - runs[-1][1] < gap_s:
            runs[-1][1] = float(t[j - 1])
        else:
            runs.append([float(t[i]), float(t[j - 1])])
        i = j
    return [(max(a - pad_s, float(t[0])), min(b + pad_s, float(t[-1]))) for a, b in runs if b - a >= min_s]


# ---- the stage --------------------------------------------------------------------------
STILL = "the platform does not move (--still): none of the pointer's turn is its own, so the whole turn is the slew's"
HOLD_GIVEN = ("the platform's share of the pointer's turn is {:+.4f} deg/s (--hold-rate, from its own motion): it is "
              "taken out, and the rest of the turn is the slew's")
BLOCKS = ("the scene is `mcdonald scene`'s block reading (--scene-blocks): each block's steadiest velocity, held over its frames, "
          "set against the pointer's rate over the same frames, and the blocks' agreement with the pointer tested against circular "
          "shifts of it (method 41)")
ASSUMES = ("the pointer reads the line of sight's azimuth (a dial, theta = -az) -- as PR051's MTS-B pointer does against "
           "its data bar's BRG -- not north against the heading, nor ground north projected into the image",
           "the pixels are square, or --pixel-aspect says how much wider the video draws them",
           "the image is level: a turn in azimuth moves the scene across it",
           "the hold rate (the platform's share of the pointer's turn) is steady over each window")


# ---- a data bar in place of the pointer (2026-10-29) --------------------------------------
BAR_GRAIN_FLOOR_M = 1.0   # m: the least grain a data bar's positions are taken to be printed on. The grain is read off the
                          # readings themselves, the least step between two of them: one arc-second, 31 m, on AARO's Puerto
                          # Rico display, which prints degrees:minutes:seconds
BAR_BLOCK_READINGS = 2    # the bootstrap's blocks span this many of the bar's readings: between two readings the line of
                          # sight is drawn straight, so the frames there are one reading's worth, not one each
BAR_GIVEN = ("the pointer is the data bar's line of sight (--platform, --los): its azimuth at each reading, drawn straight "
             "between readings, and the platform's share of its turn from the aircraft's own move -- the bearing of the "
             "ground the boresight was on, seen from where the aircraft has got to -- taken out frame by frame, so the "
             "rest of the turn is the line of sight's against the ground and no hold is fitted")
BAR_AZIMUTH = ("the pointer is the data bar's line-of-sight azimuth (--platform, --los with az_deg, dep_deg), drawn "
               "straight between readings")


def _rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(ln for ln in f if ln.strip() and not ln.lstrip().startswith("#")))


def _num(r, *keys):
    for key in keys:
        if r.get(key) not in (None, ""):
            return float(r[key])
    return None


def read_bar(platform_csv, los_csv):
    """The readings a data bar gives, in the drift stage's files (`mcdonald drift --platform --los`): the aircraft's
    position at each reading (frame, lat, lon -- decimal degrees, west and south negative -- and alt_m or alt_ft above
    the sea) and the line of sight (frame and either tgt_lat, tgt_lon, tgt_elev_m or tgt_elev_ft, the ground point the
    display prints, or az_deg, dep_deg, its true azimuth and depression). Returns (frames, A, G, az, dep): A and G in
    metres east, north and up of the readings' mean (flat: over a turret's few kilometres the earth's curve is a
    metre), G None unless every reading has its ground point; az and dep at the aircraft, in degrees."""
    plat, los = {}, {}
    for r in _rows(platform_csv):
        alt = _num(r, "alt_m")
        plat[int(float(r["frame"]))] = (float(r["lat"]), float(r["lon"]), alt if alt is not None else _num(r, "alt_ft") * 0.3048)
    for r in _rows(los_csv):
        el = _num(r, "tgt_elev_m")
        if el is None:
            el = _num(r, "tgt_elev_ft") * 0.3048 if _num(r, "tgt_elev_ft") is not None else 0.0
        tgt = (float(r["tgt_lat"]), float(r["tgt_lon"]), el) if r.get("tgt_lat") not in (None, "") else None
        los[int(float(r["frame"]))] = (tgt, _num(r, "az_deg"), _num(r, "dep_deg"))
    frames = np.array(sorted(n for n in set(plat) & set(los) if los[n][0] is not None or los[n][1] is not None), int)
    if len(frames) < 3:
        raise SystemExit(f"{platform_csv} and {los_csv} share {len(frames)} readings: a data bar needs at least 3")
    pts = [plat[n] for n in frames] + [los[n][0] for n in frames if los[n][0] is not None]
    lat0, lon0 = float(np.mean([p[0] for p in pts])), float(np.mean([p[1] for p in pts]))
    m_lat = 111132.954 - 559.822 * math.cos(2 * math.radians(lat0))
    m_lon = 111412.84 * math.cos(math.radians(lat0)) - 93.5 * math.cos(3 * math.radians(lat0))
    enu = lambda p: ((p[1] - lon0) * m_lon, (p[0] - lat0) * m_lat, p[2])
    A = np.array([enu(plat[n]) for n in frames])
    G = np.array([enu(los[n][0]) for n in frames]) if all(los[n][0] is not None for n in frames) else None
    if G is not None:
        d = G - A
        az = np.degrees(np.arctan2(d[:, 0], d[:, 1])) % 360
        dep = np.degrees(np.arctan2(-d[:, 2], np.hypot(d[:, 0], d[:, 1])))
    elif any(los[n][1] is None or los[n][2] is None for n in frames):
        raise SystemExit(f"{los_csv}: every reading needs its ground point (tgt_lat, tgt_lon) or its az_deg and dep_deg")
    else:
        az, dep = np.array([los[n][1] for n in frames]), np.array([los[n][2] for n in frames])
    return frames, A, G, az, dep


def bar_series(platform_csv, los_csv):
    """The pointer from a data bar: the line of sight's azimuth at every frame from the first reading to the last (drawn
    straight between readings), in the pointer's sense (theta = -az, unwrapped), and -- where the bar gives the ground
    point -- the platform's share of that turn, frame by frame: how far the ground the boresight was on turns as seen
    from where the aircraft has got to (the bearing of G(n) from A(n+1) less its bearing from A(n)), summed from the
    first frame, in the pointer's sense. What is left, theta - hold, is the line of sight's turn against the ground --
    the ground point's own move across the line of sight over the horizontal range, which is what the scene shows: the
    uap case's known answer for AARO's Puerto Rico clip (-k (dG . right) / R px), taken frame by frame. With only the
    azimuth and depression (no ground point) the hold is None, and is fitted as with a pointer.

    Returns dict(frames, theta, hold (or None), depression, range_m (slant, to the ground point; None without it),
    readings, grain_m, sigma_deg, step_deg): the grain is the least step between two of the positions
    (BAR_GRAIN_FLOOR_M at least), a reading's scatter that grain over sqrt(12) at each end across the median horizontal
    range, and its step one grain there; with only the azimuth, its step is the decimal it is printed to (0.1 deg) and
    its scatter that over sqrt(12)."""
    fr, A, G, az, dep = read_bar(platform_csv, los_csv)
    n = np.arange(fr[0], fr[-1] + 1)
    lerp = lambda v: np.interp(n, fr, v)
    out = dict(frames=n, theta=-lerp(np.degrees(np.unwrap(np.radians(az)))), hold=None, depression=lerp(dep),
               range_m=None, readings=int(len(fr)))
    cols = [A[:, 0], A[:, 1]] + ([G[:, 0], G[:, 1]] if G is not None else [])
    steps = np.concatenate([np.diff(np.unique(np.round(c, 2))) for c in cols])
    grain = max(float(steps[steps > 0].min()) if (steps > 0).any() else BAR_GRAIN_FLOOR_M, BAR_GRAIN_FLOOR_M)
    if G is not None:
        Ai = np.c_[lerp(A[:, 0]), lerp(A[:, 1]), lerp(A[:, 2])]
        Gi = np.c_[lerp(G[:, 0]), lerp(G[:, 1]), lerp(G[:, 2])]
        d = Gi - Ai
        bearing = lambda v: np.arctan2(v[:, 0], v[:, 1])
        turn = bearing(Gi[:-1] - Ai[1:]) - bearing(d[:-1])          # the ground left behind, seen from the next place
        turn = (turn + np.pi) % (2 * np.pi) - np.pi
        out.update(hold=np.r_[0.0, np.cumsum(-np.degrees(turn))], range_m=np.linalg.norm(d, axis=1))
        horiz, ends = float(np.median(np.hypot(d[:, 0], d[:, 1]))), 2  # the ground point's grain as well as the aircraft's
        out.update(grain_m=grain, step_deg=math.degrees(grain / horiz),
                   sigma_deg=math.degrees(grain / math.sqrt(12) * math.sqrt(ends) / horiz))
    else:                                                   # the azimuth as printed: the coarsest decimal it is a multiple of
        g = next((q for q in (1.0, 0.5, 0.1, 0.05, 0.01) if np.all(np.abs(az / q - np.round(az / q)) < 1e-6)), 0.001)
        out.update(grain_m=grain, step_deg=g, sigma_deg=g / math.sqrt(12))
    return out


def series(north_csv, layers_csv, fps, layer="all", pixel_aspect=1.0, bar=None):
    """The two series on the scene chain's frames: dict(frames, t, theta, X, Y, seg, k) and the
    pointer's own readings for the figure, with its radius, scatter and step. Both in square
    pixels: the scene's horizontal shift is divided by the pixel aspect too. `bar` (`bar_series`'s
    dict) is a data bar in place of the pointer: its theta at every frame, and its hold beside
    theta, smoothed as the scene is ("hold"; None where the bar gives no ground point)."""
    fl, _, dx, dy, k, groups, err = read_layers(layers_csv, layer, errors=True)
    err[:, 0] /= pixel_aspect
    frames, X, Y, S, bridged, E = scene_path(fl, dx / pixel_aspect, dy, k, err=err)
    if bar is not None:
        fn, thu, r = bar["frames"], bar["theta"], np.full(len(bar["frames"]), np.nan)
        keep = np.ones(len(fn), bool)
        sigma, step = bar["sigma_deg"] or 0.01, bar["step_deg"] or 0.01
    else:
        fn, _, r, th = read_north(north_csv, pixel_aspect)
        keep, thu = clean_pointer(fn, r, th, fps)
        sigma, step = pointer_scatter(thu[keep], float(np.median(r[keep])))
    theta = smooth_like_scene(fn[keep], thu[keep], k, frames)
    t = (frames - 1) / fps
    vx = np.full(len(frames), np.nan)
    for s in np.unique(S):
        m = np.where(S == s)[0]
        if len(m) >= 3:
            vx[m] = np.gradient(X[m]) * fps
    out = dict(frames=frames, t=t, theta=theta, X=X, Y=Y, seg=S, k=k, vx=vx, bridged=bridged, path_err=E,
               pairs=dict(t=(fl - 1) / fps, groups=groups),
               pointer=dict(frames=fn[keep], t=(fn[keep] - 1) / fps, theta=thu[keep], dropped=int((~keep).sum()),
                            solved=int(len(fn)), r_px=float(np.median(r[keep])) if bar is None else None,
                            r_sd_px=float(np.std(r[keep])) if bar is None else None, sigma_deg=sigma, step_deg=step))
    if bar is not None:
        out["pointer"].update(bar=True, readings=bar["readings"], grain_m=bar["grain_m"])
        out["hold"] = smooth_like_scene(fn, bar["hold"], k, frames) if bar["hold"] is not None else None
        out["bar_hold"] = bar["hold"]
        out["depression"] = np.interp(frames, fn, bar["depression"], left=np.nan, right=np.nan)
    return out


def measure(north_csv, layers_csv, W, H, fps, windows=None, degree=1, depression_deg=None, layer="all", out=None,
            name="clip", n_boot=N_BOOT, pixel_aspect=1.0, zoom=None, hold_rate=None, bar=None, blocks=None):
    """The stage: every window's fit, the scale from the windows that claim one, and what is assumed.

    `blocks` (`--scene-blocks`): the scene is `mcdonald scene`'s block reading, [dict(start, frames, vx, vy)] for the blocks that
    passed, and `layers_csv` the same blocks written as pairs (`scene.as_layers`, for the path, the windows' cut and the figure).
    Each window is then judged by `fit_blocks`, the rule for a scene read 60 frames at a time, not by `fit_window`; and the
    automatic windows are each zoom state whole (cut at bursts), since the block rule needs the blocks of a whole clip, where
    `slews` would cut a slew into pieces of a few blocks each.

    `hold_rate` (deg/s, in the pointer's own sense): the platform's share of the pointer's turn, known from its own
    motion -- for a camera holding a ground point, the bearing's rate v_perp / R from the aircraft's velocity across
    the line of sight and the range. It is taken out of the pointer and the fit has no hold term (as with `--still`,
    whose hold is zero), so a steady pan gives k: on a moving platform a steady pan is otherwise the hold's twin
    (PR051's NAR stretch: the scene at a steady 455 px/s, the pointer at 0.20 deg/s, a floor and no k).

    `zoom`: the clip's zoom states (`mcdonald.zoom.measure`'s fields, or a _zoom.json read back). Automatic windows
    are then found within each state and cut at every burst of blank frames (PAD frames clear), so no window fits one
    c to two fields; claims are compared within a state only, and across a measured step the ratio of the states' c
    is set against the step the imagery measured. Without it the clip is taken as one state, and the result says so."""
    from . import zoom as zm
    from .report import Found
    s = series(north_csv, layers_csv, fps, layer, pixel_aspect, bar=bar)
    bar_hold = bar is not None and s.get("hold") is not None
    if hold_rate is not None:                             # the platform's own share, known: out of the pointer
        s["theta"] = s["theta"] - hold_rate * s["t"]
        s["pointer"] = dict(s["pointer"], theta=s["pointer"]["theta"] - hold_rate * s["pointer"]["t"])
        degree = 0
    elif bar_hold:                                        # ... or frame by frame, from the data bar's aircraft and ground point
        s["theta"] = s["theta"] - s["hold"]
        s["pointer"] = dict(s["pointer"], theta=s["pointer"]["theta"] - s["bar_hold"])
        degree = 0
    block_s = BLOCK_S
    if bar is not None:                                   # the bar's readings, not its frames, are what the bootstrap draws
        block_s = max(BLOCK_S, BAR_BLOCK_READINGS * (bar["frames"][-1] - bar["frames"][0]) / max(bar["readings"] - 1, 1) / fps)
    Wsq = W / pixel_aspect                                # the picture's width in square pixels
    brows = None
    if blocks is not None:                                # each block beside the pointer's rate over its own frames (method 41)
        brows = block_rates(blocks, s["pointer"]["frames"], s["pointer"]["theta"], s["pointer"]["sigma_deg"], pixel_aspect)
    ok = np.isfinite(s["theta"]) & np.isfinite(s["X"])
    zoom = zoom or one_state(s)
    states = zoom["states"]
    gaps = [((r["frames"][0] - 1 - zm.PAD) / fps, (r["frames"][1] - 1 + zm.PAD) / fps, r) for r in zoom["bursts"]]
    auto = not windows
    if auto:
        windows = []
        for st in states:                              # from the scene alone: the pointer's gaps do not split a slew
            m = (s["t"] >= st["t_s"][0]) & (s["t"] <= st["t_s"][1])
            if brows is not None:                      # the block rule wants every block of the state
                windows.append((float(st["t_s"][0]), float(st["t_s"][1])))
            elif m.sum() >= 3:
                windows += slews(s["t"][m], s["vx"][m], fps)
        windows = cut(windows, [(g0, g1) for g0, g1, _ in gaps])
    fits = []
    for i, (t0, t1) in enumerate(windows):
        m = ok & (s["t"] >= t0) & (s["t"] <= t1)
        if brows is not None:
            f = fit_blocks([r for r in brows if t0 <= (r["mid"] - 1) / fps <= t1], s["pointer"]["sigma_deg"], degree, fps, n_boot,
                           seed=i, step_deg=s["pointer"]["step_deg"])
        else:
            f = fit_window(s["t"][m], s["theta"][m], s["X"][m], s["Y"][m], s["seg"][m], s["pointer"]["sigma_deg"], degree,
                           fps, n_boot, seed=i, step_deg=s["pointer"]["step_deg"], block_s=block_s)
        f.update(window=[float(t0), float(t1)], state=zm.state_at(states, 0.5 * (t0 + t1)))
        pe = s["path_err"][m]                                 # the chain's own error across the window (K9), px
        f["scene_path_err_px"] = [float(np.nanmax(pe[:, 0])), float(np.nanmax(pe[:, 1]))] if len(pe) and np.isfinite(pe).any() else None
        across = [r for g0, g1, r in gaps if min(g1, t1) - max(g0, t0) > 0.5 / fps and r["verdict"] != "no step"]
        if across:
            f["state"] = None
            f["no_power"].append("the window spans the burst of blank frames at " + ", ".join(
                f"{r['t_s'][0]:.2f} s ({'a zoom step of x' + format(r['s'], '.2f') if r['verdict'] == 'step' else 'a zoom not measured'})"
                for r in across) + ": it would fit one c to two fields of view")
        if layer == "all":
            pm = (s["pairs"]["t"] >= t0) & (s["pairs"]["t"] <= t1) & np.isfinite(s["pairs"]["groups"])
            share = float(np.mean(s["pairs"]["groups"][pm] >= 2)) if pm.any() else 0.0
            f["two_groups_share"] = share
            if share > MAX_TWO_GROUPS:
                f["no_power"].append(f"{share:.0%} of the pairs here hold two motion groups (over {MAX_TWO_GROUPS:.0%}): the "
                                     "largest group switches between layers that move at different rates, and the chain "
                                     "mixes them -- name a layer (--layer striated or isotropic)")
        if f["registered"] and brows is None:                 # the blocks have their own test, inside fit_blocks
            f.update(rate_lag(s["t"][m], s["theta"][m], s["X"][m], s["seg"][m], fps, degree))
            # a drifting hold mimics a slew through slow changes the rates do not share (PR076); with no hold fitted
            # (--still, or --hold-rate given) there is none to mimic one, and a steady pan's rates have nothing to share
            if f["rate_r"] is not None and f["rate_r"] < MIN_RATE_R and degree >= 1:
                f["no_power"].append(f"the pointer's rate and the scene's correlate at r = {f['rate_r']:.2f} at best "
                                     f"(lags of up to {LAGS} frames; under {MIN_RATE_R:g}): the turn does not follow the "
                                     "scene, and c came from slower changes a drifting hold can mimic")
        fits.append(f)
    claim = [f for f in fits if f["registered"] and not f["no_power"]]
    floors = [f for f in fits if f.get("c_at_least_px_per_deg") and not f["no_power"]]
    p = s["pointer"]
    depression_from = "given" if depression_deg is not None else None
    if depression_deg is None and bar is not None:        # the data bar's own, the median over the windows
        inw = np.zeros(len(s["t"]), bool)
        for t0, t1 in windows:
            inw |= (s["t"] >= t0) & (s["t"] <= t1)
        dd = s["depression"][inw & np.isfinite(s["depression"])]
        if len(dd):
            depression_deg, depression_from = float(np.median(dd)), "the data bar (the median over the windows)"
    base = [a for a in ASSUMES if not (bar is not None and a.startswith("the pointer reads"))]
    if bar is not None and not bar_hold:
        base = [BAR_AZIMUTH] + base
    if degree == 0:
        first = [BAR_GIVEN] if bar_hold else [HOLD_GIVEN.format(hold_rate)] if hold_rate is not None else [STILL]
        assumes = first + [a for a in base if not a.startswith("the hold rate")]
    else:
        assumes = base
    if brows is not None:
        assumes = [BLOCKS] + list(assumes)
    fields = dict(windows_chosen_automatically=auto, degree=degree, layer=layer, chain_k=s["k"], steps_bridged=s["bridged"],
                  pixel_aspect=pixel_aspect, zoom_looked_for=zoom.get("looked", True),
                  bursts=[{key: r.get(key) for key in ("frames", "t_s", "verdict", "s", "zncc", "prominence", "why")}
                          for r in zoom["bursts"]],
                  pointer=dict((key, v) for key, v in p.items() if key not in ("frames", "t", "theta")),
                  stretches=int(len(np.unique(s["seg"][ok]))) if ok.any() else 0,
                  windows=[{key: v for key, v in f.items() if not key.startswith("_")} for f in fits],
                  windows_claiming=len(claim), windows_not_registered=len(floors),
                  hold_rate_given=hold_rate, data_bar=bar is not None, hold_from_bar=bar_hold,
                  scene_from="blocks" if brows is not None else "layers",
                  blocks=None if brows is None else dict(passed=len(blocks), with_pointer=len(brows),
                                                         uneven=sum(r["resid_scatters"] > BLOCK_UNEVEN for r in brows)),
                  depression_from=depression_from, assumes=assumes,
                  c_px_per_deg=None, c_state=None, c_spread=None, c_at_least_px_per_deg=None, floor_stands=None,
                  c_below_a_floor=None, states=[], zoom_checks=[])
    result, npw, needs, notes = {}, [], [], []
    registered = claim          # a window that registers the slew and passes every check: the pointer follows the turret
    # ---- each state on its own: its claims agree with each other, and its floors with its claims
    in_claim, in_floors = {id(f) for f in claim}, {id(f) for f in floors}
    one_each = {}                                  # a state joined across a "no step" burst is two stretches: one row
    for st in states:
        u = one_each.setdefault(st["state"], dict(st, t_s=list(st["t_s"])))
        u["t_s"] = [min(u["t_s"][0], st["t_s"][0]), max(u["t_s"][1], st["t_s"][1])]
    for st in one_each.values():
        mine = [i for i, f in enumerate(fits) if f["state"] == st["state"]]
        sc = [fits[i] for i in mine if id(fits[i]) in in_claim]
        sf = [fits[i] for i in mine if id(fits[i]) in in_floors]
        row = dict(state=st["state"], chain=st["chain"], magnification=st["magnification"], t_s=st["t_s"],
                   windows=mine, windows_claiming=len(sc), c_px_per_deg=None, c_err_px_per_deg=None,
                   c_spread=None, c_at_least_px_per_deg=max(f["c_at_least_px_per_deg"] for f in sf) if sf else None,
                   c_below_a_floor=None)
        if sc:
            cs = np.array([f["c_px_per_deg"] for f in sc])
            wts = np.array([1.0 / max((f["c_p16_p84"][1] - f["c_p16_p84"][0]) / 2, 1e-9) ** 2 for f in sc])
            c = float((wts * cs).sum() / wts.sum())
            row.update(c_px_per_deg=c, c_err_px_per_deg=float(1 / np.sqrt(wts.sum())),
                       c_spread=float(cs.max() / cs.min()) if len(cs) > 1 else None, **scale_from(c, Wsq, H, depression_deg))
            if row["c_at_least_px_per_deg"] and c < row["c_at_least_px_per_deg"]:
                row["c_below_a_floor"] = True
                npw.append(("k from a slew", f"the windows of zoom state {st['state']} (t {st['t_s'][0]:.1f}-{st['t_s'][1]:.1f} "
                                             f"s) disagree: {len(sc)} measure {c:.0f} px/deg and another's floor is "
                                             f"{row['c_at_least_px_per_deg']:.0f}: the pointer is not one instrument over the "
                                             "state (a heading reference in places?), the hold changed, or a zoom was missed"))
        fields["states"].append(row)
    rows = fields["states"]
    claimed = [r for r in rows if r["c_px_per_deg"]]
    # ---- across the states: what the zoom says c should do, against what it did
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if not (a["c_px_per_deg"] and (b["c_px_per_deg"] or b["c_at_least_px_per_deg"])) and not (
                    b["c_px_per_deg"] and a["c_at_least_px_per_deg"]):
                continue
            chk = dict(states=[a["state"], b["state"]])
            if a["chain"] != b["chain"]:
                chk.update(compared=False, why="a burst between them has no trusted zoom fit: the fields either side are "
                                               "not known to be the same, nor known to differ")
                fields["zoom_checks"].append(chk)
                continue
            imaged = b["magnification"] / a["magnification"]
            chk.update(compared=True, imaged_ratio=imaged)
            if a["c_px_per_deg"] and b["c_px_per_deg"]:
                ratio = b["c_px_per_deg"] / a["c_px_per_deg"]
                err = math.hypot(a["c_err_px_per_deg"] / a["c_px_per_deg"], b["c_err_px_per_deg"] / b["c_px_per_deg"])
                tol = max(2 * err, ZOOM_AGREE)
                chk.update(kind="claims", c_ratio=ratio, tolerance=tol, agree=bool(abs(math.log(ratio / imaged)) <= tol))
                if not chk["agree"]:
                    npw.append(("k from a slew", f"zoom states {a['state']} and {b['state']}: c goes x{ratio:.3f} "
                                                 f"({a['c_px_per_deg']:.0f} to {b['c_px_per_deg']:.0f} px/deg) where the "
                                                 f"imagery's zoom is x{imaged:.3f}, outside {tol:.0%}: one of them is wrong "
                                                 "(or the depression changed by enough to move cos e)"))
            else:                                      # a claim in one, a floor in the other: the claim, zoomed, must clear it
                cl, fl = (a, b) if a["c_px_per_deg"] else (b, a)
                want = cl["c_px_per_deg"] * fl["magnification"] / cl["magnification"]
                chk.update(kind="floor", c_expected=want, c_at_least=fl["c_at_least_px_per_deg"],
                           agree=bool(want >= fl["c_at_least_px_per_deg"] * (1 - ZOOM_AGREE)))
                if not chk["agree"]:
                    npw.append(("k from a slew", f"zoom state {cl['state']}'s c ({cl['c_px_per_deg']:.0f} px/deg), carried "
                                                 f"through the imagery's zoom, is {want:.0f} in state {fl['state']}, under that "
                                                 f"state's floor of {fl['c_at_least_px_per_deg']:.0f}"))
            fields["zoom_checks"].append(chk)
    if floors:
        lo = max(f["c_at_least_px_per_deg"] for f in floors)
        fields["c_at_least_px_per_deg"] = lo
        fields["floor_stands"] = bool(registered)
        big = max(floors, key=lambda f: f["scene_lever_px"])
        say = (f"{len(floors)} of {len(fits)} windows: the scene moves {big['scene_lever_px']:.0f} px (rms) across beyond "
               f"the hold and the pointer's turn beyond it is zero within its noise, so k cos(depression) is at least "
               f"{lo:.0f} px/deg (a field of view at most {Wsq / lo:.3f} x {H / lo:.3f} deg)"
               + (" in its zoom state" if len(states) > 1 else ""))
        if registered:
            result["the pointer does not register a slew"] = say + (f"; the pointer registers the slew in {len(registered)} "
                                                                   "other window(s), so it follows the turret")
        else:
            result["the pointer registers no slew"] = say + " -- IF the pointer follows the turret, which nothing here shows"
            npw.append(("k from a slew", "the pointer registers none of the slews: either the field is that narrow or the "
                                         "pointer does not follow the turret (north against the platform's heading turns "
                                         "only with the platform), and this clip cannot tell which"))
        notes.append("A slew the pointer does not register is a floor on k only if the pointer follows the turret; a "
                     "pointer referenced to the platform's heading registers no slew at any k (tools/slew_selftest.py "
                     "--pointer heading: a floor of 3468 px/deg against a true 520).")
    if claimed:
        best = min(claimed, key=lambda r: r["c_err_px_per_deg"] / r["c_px_per_deg"])
        c = best["c_px_per_deg"]
        fields.update(c_px_per_deg=c, c_state=best["state"], c_spread=best["c_spread"], c_below_a_floor=best["c_below_a_floor"])
        fields.update(scale_from(c, Wsq, H, depression_deg))
        for r in claimed:
            key = "k cos(depression)" + (f", zoom state {r['state']} (t {r['t_s'][0]:.1f}-{r['t_s'][1]:.1f} s)" if len(states) > 1 else "")
            result[key] = (f"{r['c_px_per_deg']:.0f} px/deg from {r['windows_claiming']} of {len(r['windows'])} slew windows"
                           + (f" (they agree to x{r['c_spread']:.2f})" if r["c_spread"] else "")
                           + f"; field of view at most {r['fov_w_ceiling_deg']:.3f} x {r['fov_h_ceiling_deg']:.3f} deg"
                           + (f"; at a depression of {depression_deg:g} deg, {r['fov_w_deg']:.3f} x {r['fov_h_deg']:.3f} deg"
                              if depression_deg is not None else ""))
        for chk in fields["zoom_checks"]:
            if chk.get("kind") == "claims":
                result[f"zoom states {chk['states'][0]} to {chk['states'][1]}"] = (
                    f"c x{chk['c_ratio']:.3f}, the imagery's zoom x{chk['imaged_ratio']:.3f}: "
                    + ("they agree" if chk["agree"] else "they DISAGREE") + f" (within {chk['tolerance']:.0%})")
    if claim or (floors and registered):
        if depression_deg is None:
            needs.append(("depression", "turns k cos(e) into k and the ceiling into the field of view: --depression, "
                                        "or q = 1/sin(e) from `mcdonald waves` or a ship's proportions"))
    elif not floors:
        why = ("no window found: the scene's horizontal rate never changed by enough to mark a slew" if not fits else
               "; ".join(f"t {f['window'][0]:.1f}-{f['window'][1]:.1f} s: {f['no_power'][0]}" for f in fits))
        npw.append(("k from a slew", why))
    if not zoom.get("looked", True):
        notes.append("The clip's zooms were not looked for (--no-zoom): a window that spans a change of field fits one c "
                     "to two fields, and windows either side of one compare c's that should differ.")
    elif any(r["verdict"] == "unknown" for r in zoom["bursts"]):
        notes.append(f"{sum(r['verdict'] == 'unknown' for r in zoom['bursts'])} burst(s) of blank frames have no trusted "
                     "zoom fit: no c is carried or compared across them.")
    if bar is None:
        needs.append(("pointer convention", "the sensor's azimuth from a data bar beside the pointer (PR051's BRG) says "
                                            "whether the pointer is a dial, ground north projected into the image, or "
                                            "north against the platform's heading"))
        notes.append(f"The pointer moves in steps of {p['step_deg']:.2f} deg (a reading's scatter {p['sigma_deg']:.2f} deg): "
                     "a slew must turn it by several steps beyond the hold to be measured.")
    else:
        notes.append(f"The data bar's {p['readings']} readings print positions to {p['grain_m']:.1f} m (the least step "
                     f"between two of them): a reading's scatter {p['sigma_deg']:.3f} deg at the median range, and the "
                     "bootstrap draws blocks of two readings' frames, since the line of sight is drawn straight between them.")
    files = []
    if out:
        files.append(write(f"{out}_slew.csv", s))
        files.append(figure(f"{out}_slew.png", name, s, fits, fields))
    return Found("slew", result, fields, no_power=npw, needs=needs, files=files, notes=notes)


def write(path, s):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["frame", "t_s", "theta_smoothed_deg", "scene_x_px", "scene_y_px", "stretch", "scene_vx_px_per_s"])
        for i, n in enumerate(s["frames"]):
            v = lambda a: "" if not np.isfinite(a[i]) else round(float(a[i]), 4)
            w.writerow([int(n), round(float(s["t"][i]), 4), v(s["theta"]), v(s["X"]), v(s["Y"]), int(s["seg"][i]), v(s["vx"])])
    return path


def figure(path, name, s, fits, fields):
    """The clip on one row -- the scene's path across, the zoom's boundaries and each state's c -- then one row a zoom
    state with windows: the pointer and the scene over the state, its windows shaded (claims, floors, refused), and
    every window's pointer against the scene with the hold and the stretches' offsets taken out (slope beta = 1 / c).
    One row a state, not a window: PR27's windows made a figure 64 inches tall."""
    from .figures import PRIMARY, setup, save
    plt = setup(9)
    p = s["pointer"]
    states = fields.get("states") or []
    groups = []                                   # (label, state row or None, [window indices])
    for st in states:
        mine = [i for i, f in enumerate(fits) if f.get("state") == st["state"]]
        if mine and not any(g[1] is not None and g[1]["state"] == st["state"] for g in groups):
            groups.append((f"state {st['state']}", st, mine))
    across = [i for i, f in enumerate(fits) if f.get("state") is None]
    if across:
        groups.append(("across a change of field", None, across))
    if not groups:
        groups = [("no window", None, [])]
    n = 1 + len(groups)
    fig = plt.figure(figsize=(13, 2.9 * n), constrained_layout=True)
    gs = fig.add_gridspec(n, 3)
    top = fig.add_subplot(gs[0, :])
    axes = [None] + [[fig.add_subplot(gs[r, c]) for c in range(3)] for r in range(1, n)]

    def look(f):
        if f["no_power"]:
            return "C3", "refused"
        if f.get("c_px_per_deg"):
            return "C2", f"{f['c_px_per_deg']:.0f}"
        if f.get("c_at_least_px_per_deg"):
            return "C7", f">= {f['c_at_least_px_per_deg']:.0f}"
        return "C7", "?"

    # ---- the clip: the scene's path, the zoom's boundaries, each state's c
    top.plot(s["t"], s["X"], "-", color="C0", lw=1.0, label="Scene Across")
    for r in fields.get("bursts", []):
        t0b, t1b = r["t_s"]
        style = {"step": "-", "no step": ":", "unknown": "--"}.get(r["verdict"], "--")
        top.axvspan(t0b, max(t1b, t0b + 0.05), color="C3" if r["verdict"] == "unknown" else "C1", alpha=0.25, lw=0)
        top.axvline(0.5 * (t0b + t1b), color="C3" if r["verdict"] == "unknown" else "C1", ls=style, lw=1.0)
        if r["verdict"] == "step":
            top.annotate(f"x{r['s']:.2f}", (0.5 * (t0b + t1b), 1.0), xycoords=("data", "axes fraction"), fontsize=7,
                         ha="center", va="bottom", color="C1")
    for st in states:
        c = st.get("c_px_per_deg")
        lab = f"{c:.0f}" if c else (f">= {st['c_at_least_px_per_deg']:.0f}" if st.get("c_at_least_px_per_deg") else "")
        if lab:
            top.annotate(lab, (0.5 * (st["t_s"][0] + st["t_s"][1]), 0.04), xycoords=("data", "axes fraction"),
                         fontsize=7, ha="center", color="C2" if c else "C7")
    top.set_xlabel("Time (s)", fontweight="bold")
    top.set_ylabel("Scene Shift (px)", fontweight="bold")
    checks = [c for c in fields.get("zoom_checks", []) if c.get("kind") == "claims"]
    top.set_title("Zoom boundaries (solid: a measured step; dotted: no step; dashed red: not measured), c by state"
                  + ("; " + "; ".join(f"states {c['states'][0]}-{c['states'][1]}: c x{c['c_ratio']:.2f}, imaged "
                                       f"x{c['imaged_ratio']:.2f} ({'agree' if c['agree'] else 'DISAGREE'})"
                                       for c in checks) if checks else ""), fontsize=8, loc="left")
    # ---- a row a state
    for row, (label, st, idx) in enumerate(groups, start=1):
        a, b, cpl = axes[row]
        span = [x["t_s"] for x in states if st and x["state"] == st["state"]]   # a state joined across "no step"
        t0, t1 = ((min(v[0] for v in span), max(v[1] for v in span)) if st else
                  (min(fits[i]["window"][0] for i in idx), max(fits[i]["window"][1] for i in idx)) if idx else
                  (float(s["t"][0]), float(s["t"][-1])))
        pm = (p["t"] >= t0) & (p["t"] <= t1)
        sm = (s["t"] >= t0) & (s["t"] <= t1)
        a.plot(p["t"][pm], p["theta"][pm], ".", ms=2, color="C0", label="Pointer")
        a.plot(s["t"][sm], s["theta"][sm], "-", lw=1, color="C1", label="Smoothed as the Scene")
        b.plot(s["t"][sm], s["X"][sm], "-", color="C0", lw=1.2, label="Across")
        b.plot(s["t"][sm], s["Y"][sm], "-", color="C3", lw=1.0, label="Down")
        for i in idx:
            f = fits[i]
            col, _ = look(f)
            for ax in (a, b):
                ax.axvspan(*f["window"], color=col, alpha=0.12, lw=0)
            if "_partial" in f:
                xp, thp = f["_partial"]
                cpl.plot(xp, thp, ".", ms=1.6, color=col, alpha=0.6)
                if f.get("beta_deg_per_px") is not None and len(xp):
                    xx = np.linspace(xp.min(), xp.max(), 2)
                    cpl.plot(xx, f["beta_deg_per_px"] * xx, "-", color=col, lw=1.2,
                             label=f"{f['window'][0]:.1f}-{f['window'][1]:.1f} s: {look(f)[1]}")
        for ax, yl in ((a, "Pointer Angle (deg)"), (b, "Scene Shift (px)")):
            ax.set_xlabel("Time (s)", fontweight="bold")
            ax.set_ylabel(yl, fontweight="bold")
            ax.legend(loc="best", fontsize=7)
        if cpl.lines:
            cpl.legend(loc="best", fontsize=7)
        cpl.set_xlabel("Scene Across, Hold Removed (px)", fontweight="bold")
        cpl.set_ylabel("Pointer, Hold Removed (deg)", fontweight="bold")
        ok = [fits[i] for i in idx if not fits[i]["no_power"] and fits[i].get("c_px_per_deg")]
        head = (f"{label}, t {t0:.1f}-{t1:.1f} s" + (f" ({len(span)} stretches joined across no step)" if len(span) > 1
                                                      else "") + (f", x{st['magnification']:.2f} on chain {st['chain']}"
                                                      if st and len(states) > 1 else "") + f": {len(idx)} window(s), ")
        if st and st.get("c_px_per_deg"):
            head += f"c {st['c_px_per_deg']:.0f} +- {st['c_err_px_per_deg']:.0f} px/deg from {len(ok)}"
        elif st and st.get("c_at_least_px_per_deg"):
            head += f"a floor of {st['c_at_least_px_per_deg']:.0f} px/deg"
        elif idx:
            first = next((fits[i]["no_power"][0] for i in idx if fits[i]["no_power"]), "no claim")
            head += "none claims: " + first
        else:
            head += "no slew found"
        cpl.set_title(textwrap.shorten(head, 150, placeholder=" ..."), fontsize=7,
                      color=PRIMARY if ok else "C3", loc="left", wrap=True)
    fig.suptitle(f"{name}: k from the Slew", fontweight="bold")
    save(fig, path, dpi=110)
    plt.close(fig)
    return path


def said(f):
    p = f["pointer"]
    if p.get("bar"):
        L = [f"pointer: the data bar's line of sight, {p['readings']} readings drawn straight between over {p['solved']} "
             f"frames, positions to {p['grain_m']:.1f} m (a reading's scatter {p['sigma_deg']:.3f} deg)"
             + ("; the platform's share of its turn taken out frame by frame from the aircraft's move against the ground "
                "point, so no hold is fitted" if f.get("hold_from_bar") else "; no ground point, so the hold is fitted")]
    else:
        L = [f"pointer: {p['solved'] - p['dropped']} of {p['solved']} solved frames kept (radius {p['r_px']:.1f} +/- "
             f"{p['r_sd_px']:.1f} px); it moves in steps of {p['step_deg']:.2f} deg, a reading's scatter {p['sigma_deg']:.2f} deg"]
    if f.get("pixel_aspect", 1.0) != 1.0:
        L.append(f"pixels drawn {f['pixel_aspect']:g} times wider than tall: the pointer and the scene are read in square "
                 "pixels (the picture's height), and so is every k and px below")
    L.append(f"scene: the {f['layer']} layer's {f['chain_k']}-frame shifts chained in {f['stretches']} unbroken stretch(es), "
             f"{f['steps_bridged']} frame steps no pair measured bridged at the velocity either side")
    if not f.get("zoom_looked_for", True):
        L.append("zoom: not looked for (--no-zoom): the clip is taken as one field of view")
    elif not f["bursts"]:
        L.append("zoom: no burst of blank or flash frames, so one zoom state")
    else:
        L.append(f"zoom: {len(f['bursts'])} burst(s) of blank frames, the windows cut at each: " + "; ".join(
            f"{r['t_s'][0]:.2f} s " + (f"x{r['s']:.3f}" if r["verdict"] == "step" else r["verdict"]) for r in f["bursts"]))
    if f.get("blocks"):
        b = f["blocks"]
        L.append(f"blocks: {b['passed']} passed the scene's gate, {b['with_pointer']} with the pointer read over them"
                 + (f", {b['uneven']} of those turning it unevenly inside the block (left out)" if b["uneven"] else ""))
    for w in f["windows"]:
        blocks = w.get("from_blocks")
        head = (f"t {w['window'][0]:6.2f}-{w['window'][1]:6.2f} s ({w['n']} {'blocks' if blocks else 'samples'}"
                + (f", state {w['state']})" if len(f.get("states", [])) > 1 and w.get("state") is not None else ")"))
        if w.get("beta_deg_per_px") is None:
            L.append(f"{head}: {w['no_power'][0]}")
            continue
        if blocks:
            lev = (f"the blocks' velocities differ by {w['scene_lever_px']:.0f} px a block rms across, {w['scene_lever_down_px']:.0f} down "
                   f"(the change {w['slew_direction_deg']:+.0f} deg off the horizontal); the pointer's turn a block differs by "
                   f"{w['lever_deg']:.2f} deg rms = {w['lever_over_scatter']:.1f} scatters; hold rate {w['hold_rate_deg_per_s']:+.3f} deg/s")
        else:
            lev = (f"scene beyond the hold {w['scene_lever_px']:.0f} px rms across, {w['scene_lever_down_px']:.0f} down "
                   f"(the slew {w['slew_direction_deg']:+.0f} deg off the horizontal); pointer beyond the hold "
                   f"{w['lever_deg']:.2f} deg rms = {w['lever_over_scatter']:.1f} scatters; hold rate "
                   f"{w['hold_rate_deg_per_s']:+.3f} deg/s")
        if w.get("c_px_per_deg"):
            L.append(f"{head}: c {w['c_px_per_deg']:.0f} px/deg, 16-84 % {w['c_p16_p84'][0]:.0f}-{w['c_p16_p84'][1]:.0f} "
                     f"(forward {w['c_forward_px_per_deg']:.0f}; with a changing hold "
                     + (f"{w['c_next_degree_px_per_deg']:.0f}" if w.get("c_next_degree_px_per_deg") else "none")
                     + f"; the pointer's grid up to {w['grid_error_share']:.0%}); theta-driven motion {w['tilt_deg']:+.0f} "
                     "deg off the horizontal; " + lev)
            if w.get("bracket_px_per_deg"):
                L.append(f"    off the horizontal by more than {MAX_TILT_DEG:g} deg: c lies in {w['bracket_px_per_deg'][0]:.0f}-"
                         f"{w['bracket_px_per_deg'][1]:.0f} px/deg (a level image with the elevation in step, or a rolled one)")
        elif w.get("c_at_least_px_per_deg"):
            L.append(f"{head}: the pointer does NOT register the slew (its turn per px of scene {w['beta_deg_per_px']:.2e} "
                     f"deg, 95 % {w['beta_p2_p98'][0]:.1e} to {w['beta_p2_p98'][1]:.1e}): c at least "
                     f"{w['c_at_least_px_per_deg']:.0f} px/deg; " + lev)
        else:
            L.append(f"{head}: " + lev)
        if w.get("shift_r") is not None:
            L.append(f"    blocks against the pointer: r {w['shift_r']:.2f}; {w['shift_reaching']} of {w['shifts']} circular shifts of the "
                     f"pointer reach it (the largest {w['shift_null_max']:.2f}; 1 in {1 / SHIFT_ALPHA:.0f} allowed)")
        if w.get("rate_r") is not None:
            sh = w.get("c_shift_one_frame")
            L.append(f"    rates: r {w['rate_r']:.3f} at a lag of {w['best_lag_frames']:+d} frame(s) (at 0: "
                     f"{w['rate_r_by_lag'].get(0, float('nan')):.3f})"
                     + (f"; c at that lag {w['c_at_lag'][w['best_lag_frames']]:.0f}" if w["c_at_lag"].get(w["best_lag_frames"]) else "")
                     + (f"; a frame either way moves c by up to {sh:.1%}" if sh is not None else ""))
        for why in w["no_power"]:
            L.append(f"    no power: {why}")
    if len(f.get("states", [])) > 1:
        for r in f["states"]:
            head = (f"state {r['state']} (t {r['t_s'][0]:.1f}-{r['t_s'][1]:.1f} s, chain {r['chain']}, x{r['magnification']:.3f}"
                    " of its chain's first)")
            if r["c_px_per_deg"]:
                L.append(f"{head}: c {r['c_px_per_deg']:.0f} +/- {r['c_err_px_per_deg']:.0f} px/deg from {r['windows_claiming']} "
                         f"window(s); field at most {r['fov_w_ceiling_deg']:.3f} x {r['fov_h_ceiling_deg']:.3f} deg"
                         + (f"; a floor of {r['c_at_least_px_per_deg']:.0f} too" if r["c_at_least_px_per_deg"] else ""))
            elif r["c_at_least_px_per_deg"]:
                L.append(f"{head}: a floor, c at least {r['c_at_least_px_per_deg']:.0f} px/deg")
            else:
                L.append(f"{head}: " + ("no window claims" if r["windows"] else "no window"))
        for chk in f["zoom_checks"]:
            a, b = chk["states"]
            if not chk["compared"]:
                L.append(f"states {a} and {b}: not compared -- {chk['why']}")
            elif chk["kind"] == "claims":
                L.append(f"states {a} to {b}: c x{chk['c_ratio']:.3f} against the imagery's zoom x{chk['imaged_ratio']:.3f}: "
                         + ("AGREE" if chk["agree"] else "DISAGREE") + f" (within {chk['tolerance']:.0%})")
            else:
                L.append(f"states {a} and {b}: the claim carried through the zoom gives {chk['c_expected']:.0f} px/deg against "
                         f"a floor of {chk['c_at_least']:.0f}: " + ("consistent" if chk["agree"] else "INCONSISTENT"))
    if f["c_px_per_deg"]:
        L.append(f"k cos(depression) = {f['c_px_per_deg']:.0f} px/deg ({f['k_h_px_per_rad']:.3g} px/rad) from "
                 + (f"zoom state {f['c_state']}, the best measured, " if len(f.get("states", [])) > 1 else "")
                 + f"{f['windows_claiming']} window(s) in all: k is at least this, so the field of view is at most "
                 f"{f['fov_w_ceiling_deg']:.3f} x {f['fov_h_ceiling_deg']:.3f} deg (reached only at a horizontal look)")
        if f.get("fov_w_deg"):
            L.append(f"at a depression of {f['depression_deg']:.2f} deg"
                     + (f" ({f['depression_from']})" if f.get("depression_from") not in (None, "given") else "")
                     + f": k = {f['k_px_per_deg']:.0f} px/deg, field of view {f['fov_w_deg']:.3f} x {f['fov_h_deg']:.3f} deg")
    if f["c_at_least_px_per_deg"]:
        L.append(f"a slew the pointer does not register: k cos(depression) is at least {f['c_at_least_px_per_deg']:.0f} px/deg "
                 + ("(the pointer registers a slew elsewhere in the clip, so it follows the turret)" if f["floor_stands"] else
                    "IF the pointer follows the turret, which no window here shows; a pointer referenced to the platform's "
                    "heading registers no slew at any k"))
    L.append("assumes: " + "; ".join(f["assumes"]))
    return L


def main():
    from .report import case_option, command_line, into_case
    import argparse
    from . import clip as vclip
    from . import forensics as vf
    from .report import emit, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--north", metavar="CSV", help="the pointer's readings, a `mcdonald symbology` _north.csv "
                    "(default: <out>/<tag>_north.csv); read it on every frame, --step 1")
    ap.add_argument("--layers", metavar="CSV", help="the scene's shifts, a `mcdonald layers` _layers.csv "
                    "(default: <out>/<tag>_layers.csv)")
    ap.add_argument("--scene-blocks", nargs="?", const="", metavar="CSV",
                    help="take the scene from `mcdonald scene`'s block reading (default: <out>/<tag>_scene.csv), not from `layers`: for a clip "
                         "`layers` holds still under its sensor's pattern. Only when asked. Each zoom state is then one window, judged by the "
                         "blocks' own rule -- each block's velocity against the pointer's rate over the same frames, their agreement tested "
                         "against circular shifts of the pointer, which takes 21 blocks (42 s) or more -- so read the pointer on every frame "
                         "(--step 1) over the whole clip (method 41)")
    ap.add_argument("--layer", default="all", choices=["all", "striated", "isotropic"],
                    help="which background's shifts (all: the largest motion group)")
    ap.add_argument("--window", action="append", metavar="T0:T1", help="a time window round a slew, s (repeat; "
                    "default: one round each slew the scene shows, start to stop, 3 s either side)")
    ap.add_argument("--degree", type=int, default=1, help="the hold rate as a polynomial in time of this degree")
    ap.add_argument("--still", action="store_true", help="the platform does not move (a camera on the ground, a ship at "
                    "anchor, an aerostat): no hold term, so a steady pan gives k too (the same as --degree 0)")
    ap.add_argument("--hold-rate", type=float, metavar="DEG_S", help="the platform's share of the pointer's turn, deg/s "
                    "in the pointer's own sense, if its motion is known (a ground point's bearing rate, v_perp / R): taken "
                    "out, so a steady pan gives k too")
    ap.add_argument("--depression", type=float, help="the line of sight's depression, deg: k and the field of view "
                    "themselves instead of their bounds")
    ap.add_argument("--platform", metavar="CSV", help="a data bar in place of the pointer, with --los: the aircraft's "
                    "position at each reading the display prints (frame,lat,lon,alt_m; decimal degrees, west and south "
                    "negative -- the file `mcdonald drift --platform` reads)")
    ap.add_argument("--los", metavar="CSV", help="with --platform: the line of sight at each reading, the ground point "
                    "the display prints (frame,tgt_lat,tgt_lon,tgt_elev_m) or its azimuth and depression (frame,az_deg,"
                    "dep_deg). With the ground point the platform's share of the turn is known frame by frame (no hold "
                    "is fitted, so a camera that follows something round an orbit gives k) and so is the depression")
    ap.add_argument("--pixel-aspect", type=float, default=1.0, help="how much wider the video draws a pixel than it is "
                    "tall (a 4:3 sensor shown full-height in 16:9: 1.333). The pointer's angle and the scene's shift are "
                    "taken back to square pixels, and k is given in them")
    ap.add_argument("--zoom", metavar="JSON", help="the clip's zoom states, a `mcdonald zoom` _zoom.json (default: "
                    "<out>/<tag>_zoom.json, made now if it is not there: a pass over the whole clip)")
    ap.add_argument("--no-zoom", action="store_true", help="do not look for the clip's zooms: take it as one field of "
                    "view (windows are then not cut at blank bursts, and claims either side of one are compared)")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    case_option(ap)
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        video, tag, _ = vf.resolve(args.video)
        clip = vclip.Clip(video, None, extract=False)
        out = vclip.out_prefix(args.out, tag)
        zoom = None
        if not args.no_zoom:
            from . import zoom as zm
            zj = Path(args.zoom or f"{out}_zoom.json")
            if zj.exists():
                zoom = zm.read(zj)
                print(f"zoom states from {zj}")
            elif args.zoom:
                raise SystemExit(f"{zj} is not there: make it with `mcdonald zoom {args.video} --out {args.out or '.'}`")
            else:
                print("finding the clip's zooms (a pass over the whole clip; `mcdonald zoom` makes the same file)")
                zoom = zm.measure(video, clip.W, clip.H, clip.fps, clip=clip, out=out).fields
                print("  " + "\n  ".join(zm.said(zoom)))
        north, layers = Path(args.north or f"{out}_north.csv"), Path(args.layers or f"{out}_layers.csv")
        blocks = None
        if args.scene_blocks is not None:
            from . import scene as sc
            if args.layers:
                raise SystemExit("--scene-blocks takes the scene from the block reading: leave out --layers")
            bpath = Path(args.scene_blocks or f"{out}_scene.csv")
            if not bpath.exists():
                raise SystemExit(f"{bpath} is not there: make it first with `mcdonald scene {shlex.quote(str(args.video))} --out {args.out or '.'}`")
            layers = Path(f"{out}_scene_as_layers.csv")
            print(f"the scene from the block reading in {bpath}, asked for by name: {sc.as_layers(bpath, clip.fps, layers)} pairs "
                  f"from its blocks that passed, written as {layers}")
            blocks = [dict(start=r["start"], frames=r["frames"], vx=r["best_vx_px_frame"], vy=r["best_vy_px_frame"])
                      for r in sc.read_csv(bpath) if r["passed"]]
        if bool(args.platform) != bool(args.los):
            raise SystemExit("a data bar needs both --platform and --los")
        bar = bar_series(args.platform, args.los) if args.platform else None
        if bar is not None and bar["hold"] is not None and (args.hold_rate is not None or args.still):
            raise SystemExit("the data bar's ground point gives the platform's share of the turn: leave out --hold-rate and --still")
        for pth, how in (((north, f"mcdonald symbology {shlex.quote(str(args.video))} --step 1 --out {args.out or '.'}"),) if bar is None else ()) + (
                (layers, f"mcdonald layers {shlex.quote(str(args.video))} --out {args.out or '.'}"),):
            if not pth.exists():
                raise SystemExit(f"{pth} is not there: make it first with `{how}`")
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps")
        wins = [tuple(float(v) for v in w.split(":")) for w in args.window] if args.window else None
        found = measure(north, layers, clip.W, clip.H, clip.fps, wins, 0 if args.still else args.degree, args.depression,
                        args.layer, out, tag, pixel_aspect=args.pixel_aspect, zoom=zoom, hold_rate=args.hold_rate, bar=bar,
                        blocks=blocks)
        if args.scene_blocks is not None:
            found.notes.append("The scene here is `mcdonald scene`'s block reading, asked for by name: each block's steadiest velocity held "
                               "over its 60 frames, set against the pointer's rate over the same frames and judged by the blocks' own rule "
                               "(method 41), not `layers`' pairs.")
        print("\n".join(said(found.fields)))
        for w in found.no_power:
            print(f"no power: {w[1]}")
        for f in found.files:
            print(f"wrote {f}")
        if args.case:
            print(f"recorded in {into_case(found, args.case, command_line())}")
    code = vclip.EXIT_NOTHING if found.no_power else 0
    if args.json:
        emit(found.envelope("slew", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
