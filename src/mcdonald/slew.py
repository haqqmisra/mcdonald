"""k from the camera's own slew: the scene's shift against the north pointer's turn.

  mcdonald slew VIDEO [--north CSV] [--layers CSV] [--window T0:T1 ...] [--depression D]

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


def read_layers(path, layer="all"):
    """(frames, t, dx, dy, k, groups) from a `layers` _layers.csv: each pair's k-frame shift of `layer`
    ("all" is the largest motion group), NaN where the pair had no consensus, and how many motion
    groups the pair's templates fell into (NaN where the file does not say)."""
    with open(path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        cx = next(c for c in rd.fieldnames if c.startswith(f"{layer}_dx"))
        k = int(cx[len(f"{layer}_dx"):])
        fr, t, dx, dy, gr = [], [], [], [], []
        for r in rd:
            fr.append(int(r["frame"]))
            t.append(float(r["t_s"]))
            dx.append(float(r[cx]) if r[cx] not in ("", None) else np.nan)
            dy.append(float(r[f"{layer}_dy{k}"]) if r[f"{layer}_dy{k}"] not in ("", None) else np.nan)
            gr.append(float(r["groups"]) if r.get("groups") not in ("", None) else np.nan)
    return np.array(fr, int), np.array(t), np.array(dx), np.array(dy), k, np.array(gr)


def kernel(k):
    """The weights a chain of k-frame shifts smooths the scene's path with: averaging the k pairs
    that span one frame step, each the sum of k steps, gives every step its neighbours' shares
    (k - |d|) / k^2. The pointer is smoothed with the same weights, so the two still agree."""
    d = np.arange(-(k - 1), k)
    return d, (k - np.abs(d)) / k ** 2


def scene_path(frames, dx, dy, k, need=None, bridge=None):
    """The scene's path X, Y (px) at every frame from frames[0] to frames[-1] + k, from the k-frame
    shifts of the pairs that start there, a stretch number for each frame (-1, and no place, inside a
    gap), and how many frame steps were bridged. A step that `need` (half, rounded up) of the k pairs spanning it measured moves by
    their mean; a run of up to `bridge` steps (default 2k) that none measured, with measured steps
    on both sides, moves by the velocity drawn straight across it; a longer run starts a new stretch,
    whose offset the fit carries.

    The bridge is for the slew's own start and end: `layers` leaves out shifts within 4 px of zero
    over k frames and measures a held scene again over a second, so a scene moving 1-4 px in five
    frames -- a slew easing in or out -- has no consensus at all (the synthetic pan of
    tools/slew_selftest.py broke into 24 stretches exactly there, and those steps are the lever)."""
    need = need or (k + 1) // 2
    bridge = 2 * k if bridge is None else bridge
    n0, n1 = int(frames.min()), int(frames.max()) + k
    at = {int(f): i for i, f in enumerate(frames)}
    vx, vy = np.full(n1 - n0, np.nan), np.full(n1 - n0, np.nan)
    for m in range(n0, n1):                                # the step from frame m to m + 1
        cover = [at[a] for a in range(m - k + 1, m + 1) if a in at and np.isfinite(dx[at[a]])]
        if len(cover) >= need:
            vx[m - n0], vy[m - n0] = np.mean(dx[cover]) / k, np.mean(dy[cover]) / k
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
            bridged += j - i
        i = j
    N = n1 - n0 + 1
    X, Y, S = np.full(N, np.nan), np.full(N, np.nan), np.full(N, -1)
    X[0], Y[0], S[0] = 0.0, 0.0, 0
    s, alive = 0, True
    for i in range(N - 1):
        if np.isfinite(vx[i]):
            if not alive:                                  # a new stretch begins where the steps are measured again
                s += 1
                X[i], Y[i], S[i], alive = 0.0, 0.0, s, True
            X[i + 1], Y[i + 1], S[i + 1] = X[i] + vx[i], Y[i] + vy[i], s
        else:
            alive = False                                  # frames inside a gap have no place on any stretch
    return np.arange(n0, n1 + 1), X, Y, S, bridged


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


def fit_window(t, theta, X, Y, seg, sigma_theta, degree=1, fps=30.0, n_boot=N_BOOT, seed=0, step_deg=None):
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
    bs = bootstrap(t, theta, X, seg, degree, n_boot, block=int(round(BLOCK_S * fps)), seed=seed)
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


# ---- the windows ------------------------------------------------------------------------
def slews(t, vx, fps, min_rate=None, smooth_s=0.5, gap_s=1.0, min_s=0.5, pad_s=3.0):
    """A window round each slew, from pad_s before it starts to pad_s after it stops. A slew is a run of
    frames where the scene's horizontal rate, smoothed over smooth_s, is above min_rate (px/s; default a
    fifth of its largest, at least 20), runs closer than gap_s joined and runs under min_s dropped.

    The whole slew, not its start and its stop apart: the fit takes the hold as steady over the window,
    and half a slew inside a window looks to that check like a hold that changes (the rendered pan read
    c 554 and 480 in windows round its start and its stop, each moved 34 % by a quadratic hold, and 524
    in one round all of it). Different slews are kept apart: PR148's platform share of the pointer's
    turn goes from +0.33 to -0.48 deg/s over the minute."""
    n = max(int(round(smooth_s * fps)), 1)
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
ASSUMES = ("the pointer reads the line of sight's azimuth (a dial, theta = -az) -- as PR051's MTS-B pointer does against "
           "its data bar's BRG -- not north against the heading, nor ground north projected into the image",
           "the pixels are square, or --pixel-aspect says how much wider the video draws them",
           "the image is level: a turn in azimuth moves the scene across it",
           "the hold rate (the platform's share of the pointer's turn) is steady over each window")


def series(north_csv, layers_csv, fps, layer="all", pixel_aspect=1.0):
    """The two series on the scene chain's frames: dict(frames, t, theta, X, Y, seg, k) and the
    pointer's own readings for the figure, with its radius, scatter and step. Both in square
    pixels: the scene's horizontal shift is divided by the pixel aspect too."""
    fn, _, r, th = read_north(north_csv, pixel_aspect)
    keep, thu = clean_pointer(fn, r, th, fps)
    fl, _, dx, dy, k, groups = read_layers(layers_csv, layer)
    frames, X, Y, S, bridged = scene_path(fl, dx / pixel_aspect, dy, k)
    theta = smooth_like_scene(fn[keep], thu[keep], k, frames)
    sigma, step = pointer_scatter(thu[keep], float(np.median(r[keep])))
    t = (frames - 1) / fps
    vx = np.full(len(frames), np.nan)
    for s in np.unique(S):
        m = np.where(S == s)[0]
        if len(m) >= 3:
            vx[m] = np.gradient(X[m]) * fps
    return dict(frames=frames, t=t, theta=theta, X=X, Y=Y, seg=S, k=k, vx=vx, bridged=bridged,
                pairs=dict(t=(fl - 1) / fps, groups=groups),
                pointer=dict(frames=fn[keep], t=(fn[keep] - 1) / fps, theta=thu[keep], dropped=int((~keep).sum()),
                             solved=int(len(fn)), r_px=float(np.median(r[keep])), r_sd_px=float(np.std(r[keep])),
                             sigma_deg=sigma, step_deg=step))


def measure(north_csv, layers_csv, W, H, fps, windows=None, degree=1, depression_deg=None, layer="all", out=None,
            name="clip", n_boot=N_BOOT, pixel_aspect=1.0):
    """The stage: every window's fit, the scale from the windows that claim one, and what is assumed."""
    from .report import Found
    s = series(north_csv, layers_csv, fps, layer, pixel_aspect)
    Wsq = W / pixel_aspect                                # the picture's width in square pixels
    ok = np.isfinite(s["theta"]) & np.isfinite(s["X"])
    auto = not windows
    if auto:
        windows = slews(s["t"], s["vx"], fps)          # from the scene alone: the pointer's gaps do not split a slew
    fits = []
    for i, (t0, t1) in enumerate(windows):
        m = ok & (s["t"] >= t0) & (s["t"] <= t1)
        f = fit_window(s["t"][m], s["theta"][m], s["X"][m], s["Y"][m], s["seg"][m], s["pointer"]["sigma_deg"], degree,
                       fps, n_boot, seed=i, step_deg=s["pointer"]["step_deg"])
        f.update(window=[float(t0), float(t1)])
        if layer == "all":
            pm = (s["pairs"]["t"] >= t0) & (s["pairs"]["t"] <= t1) & np.isfinite(s["pairs"]["groups"])
            share = float(np.mean(s["pairs"]["groups"][pm] >= 2)) if pm.any() else 0.0
            f["two_groups_share"] = share
            if share > MAX_TWO_GROUPS:
                f["no_power"].append(f"{share:.0%} of the pairs here hold two motion groups (over {MAX_TWO_GROUPS:.0%}): the "
                                     "largest group switches between layers that move at different rates, and the chain "
                                     "mixes them -- name a layer (--layer striated or isotropic)")
        fits.append(f)
    claim = [f for f in fits if f["registered"] and not f["no_power"]]
    floors = [f for f in fits if f.get("c_at_least_px_per_deg") and not f["no_power"]]
    p = s["pointer"]
    fields = dict(windows_chosen_automatically=auto, degree=degree, layer=layer, chain_k=s["k"], steps_bridged=s["bridged"],
                  pixel_aspect=pixel_aspect,
                  pointer=dict((key, v) for key, v in p.items() if key not in ("frames", "t", "theta")),
                  stretches=int(len(np.unique(s["seg"][ok]))) if ok.any() else 0,
                  windows=[{key: v for key, v in f.items() if not key.startswith("_")} for f in fits],
                  windows_claiming=len(claim), windows_not_registered=len(floors),
                  assumes=[STILL] + [a for a in ASSUMES if not a.startswith("the hold rate")] if degree == 0 else list(ASSUMES),
                  c_px_per_deg=None, c_spread=None, c_at_least_px_per_deg=None, floor_stands=None, c_below_a_floor=None)
    result, npw, needs, notes = {}, [], [], []
    registered = claim          # a window that registers the slew and passes every check: the pointer follows the turret
    if floors:
        lo = max(f["c_at_least_px_per_deg"] for f in floors)
        fields["c_at_least_px_per_deg"] = lo
        fields["floor_stands"] = bool(registered)
        big = max(floors, key=lambda f: f["scene_lever_px"])
        say = (f"{len(floors)} of {len(fits)} windows: the scene moves {big['scene_lever_px']:.0f} px (rms) across beyond "
               f"the hold and the pointer's turn beyond it is zero within its noise, so k cos(depression) is at least "
               f"{lo:.0f} px/deg (a field of view at most {Wsq / lo:.3f} x {H / lo:.3f} deg)")
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
    if claim:
        cs = np.array([f["c_px_per_deg"] for f in claim])
        wts = np.array([1.0 / max((f["c_p16_p84"][1] - f["c_p16_p84"][0]) / 2, 1e-9) ** 2 for f in claim])
        c = float((wts * cs).sum() / wts.sum())
        fields["c_px_per_deg"] = c
        fields["c_spread"] = float(cs.max() / cs.min()) if len(cs) > 1 else None
        fields.update(scale_from(c, Wsq, H, depression_deg))
        result["k cos(depression)"] = (f"{c:.0f} px/deg from {len(claim)} of {len(fits)} slew windows"
                                       + (f" (they agree to x{fields['c_spread']:.2f})" if fields["c_spread"] else ""))
        result["field of view"] = (f"at most {fields['fov_w_ceiling_deg']:.3f} x {fields['fov_h_ceiling_deg']:.3f} deg"
                                   + (f"; at a depression of {depression_deg:g} deg, {fields['fov_w_deg']:.3f} x "
                                      f"{fields['fov_h_deg']:.3f} deg" if depression_deg is not None else ""))
        if fields["c_at_least_px_per_deg"] and c < fields["c_at_least_px_per_deg"]:
            fields["c_below_a_floor"] = True
            npw.append(("k from a slew", f"the windows disagree: {len(claim)} measure {c:.0f} px/deg and another's floor is "
                                         f"{fields['c_at_least_px_per_deg']:.0f}: the pointer is not one instrument over "
                                         "the clip (a heading reference in places?) or the hold changed"))
    if claim or (floors and registered):
        if depression_deg is None:
            needs.append(("depression", "turns k cos(e) into k and the ceiling into the field of view: --depression, "
                                        "or q = 1/sin(e) from `mcdonald waves` or a ship's proportions"))
    elif not floors:
        why = ("no window found: the scene's horizontal rate never changed by enough to mark a slew" if not fits else
               "; ".join(f"t {f['window'][0]:.1f}-{f['window'][1]:.1f} s: {f['no_power'][0]}" for f in fits))
        npw.append(("k from a slew", why))
    needs.append(("pointer convention", "the sensor's azimuth from a data bar beside the pointer (PR051's BRG) says "
                                        "whether the pointer is a dial, ground north projected into the image, or "
                                        "north against the platform's heading"))
    notes.append(f"The pointer moves in steps of {p['step_deg']:.2f} deg (a reading's scatter {p['sigma_deg']:.2f} deg): "
                 "a slew must turn it by several steps beyond the hold to be measured.")
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
    """Per window: the pointer and the hold, the scene's path, and the pointer against the scene once
    the hold and the stretches' offsets are taken out (its slope is beta = 1 / c)."""
    from .figures import PRIMARY, setup, save
    plt = setup(9)
    n = max(len(fits), 1)
    fig, axes = plt.subplots(n, 3, figsize=(13, 3.4 * n), squeeze=False, constrained_layout=True)
    p = s["pointer"]
    for row, f in enumerate(fits or [None]):
        a, b, cpl = axes[row]
        t0, t1 = (f["window"] if f else (float(s["t"][0]), float(s["t"][-1])))
        pm = (p["t"] >= t0) & (p["t"] <= t1)
        sm = (s["t"] >= t0) & (s["t"] <= t1)
        a.plot(p["t"][pm], p["theta"][pm], ".", ms=2.5, color="C0", label="Pointer")
        a.plot(s["t"][sm], s["theta"][sm], "-", lw=1, color="C1", label="Smoothed as the Scene")
        if f and "_hold" in f:
            a.plot(*f["_hold"], ":", color="C2", lw=1.2, label="Fitted Hold, Scene Held")
        a.set_xlabel("Time (s)", fontweight="bold")
        a.set_ylabel("Pointer Angle (deg)", fontweight="bold")
        a.legend(loc="best", fontsize=7)
        b.plot(s["t"][sm], s["X"][sm], "-", color="C0", lw=1.2, label="Across")
        b.plot(s["t"][sm], s["Y"][sm], "-", color="C3", lw=1.0, label="Down")
        b.set_xlabel("Time (s)", fontweight="bold")
        b.set_ylabel("Scene Shift (px)", fontweight="bold")
        b.legend(loc="best", fontsize=7)
        if f and "_partial" in f:
            xp, thp = f["_partial"]
            cpl.plot(xp, thp, ".", ms=2, color="C0")
            if f.get("beta_deg_per_px") is not None:
                xx = np.linspace(xp.min(), xp.max(), 2)
                lab = (f"c = {f['c_px_per_deg']:.0f} px/deg (forward {f['c_forward_px_per_deg']:.0f})" if f.get("c_px_per_deg")
                       else f"not registered: c at least {f['c_at_least_px_per_deg']:.0f} px/deg"
                       if f.get("c_at_least_px_per_deg") else "against the scene")
                cpl.plot(xx, f["beta_deg_per_px"] * xx, "-", color="C1", lw=1.2, label=lab)
                if f.get("c_at_least_px_per_deg"):
                    cpl.plot(xx, xx / f["c_at_least_px_per_deg"], ":", color="C3", lw=1.0, label="97.5 % Bound")
                cpl.legend(loc="best", fontsize=7)
        cpl.set_xlabel("Scene Across, Hold Removed (px)", fontweight="bold")
        cpl.set_ylabel("Pointer, Hold Removed (deg)", fontweight="bold")
        title = (f"t {t0:.1f}-{t1:.1f} s: " + ("no power: " + f["no_power"][0] if f and f["no_power"] else
                                                "not registered: a floor" if f and f.get("c_at_least_px_per_deg") else
                                                "claims" if f else "no window"))
        cpl.set_title(textwrap.shorten(title, 150, placeholder=" ...") if len(title) > 150 else title, fontsize=7,
                      color="C3" if (not f or f["no_power"]) else PRIMARY, loc="left", wrap=True)
    fig.suptitle(f"{name}: k from the Slew", fontweight="bold")
    save(fig, path, dpi=110)
    plt.close(fig)
    return path


def said(f):
    p = f["pointer"]
    L = [f"pointer: {p['solved'] - p['dropped']} of {p['solved']} solved frames kept (radius {p['r_px']:.1f} +/- "
         f"{p['r_sd_px']:.1f} px); it moves in steps of {p['step_deg']:.2f} deg, a reading's scatter {p['sigma_deg']:.2f} deg"]
    if f.get("pixel_aspect", 1.0) != 1.0:
        L.append(f"pixels drawn {f['pixel_aspect']:g} times wider than tall: the pointer and the scene are read in square "
                 "pixels (the picture's height), and so is every k and px below")
    L.append(f"scene: the {f['layer']} layer's {f['chain_k']}-frame shifts chained in {f['stretches']} unbroken stretch(es), "
             f"{f['steps_bridged']} frame steps no pair measured bridged at the velocity either side")
    for w in f["windows"]:
        head = f"t {w['window'][0]:6.2f}-{w['window'][1]:6.2f} s ({w['n']} samples)"
        if w.get("beta_deg_per_px") is None:
            L.append(f"{head}: {w['no_power'][0]}")
            continue
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
        for why in w["no_power"]:
            L.append(f"    no power: {why}")
    if f["c_px_per_deg"]:
        L.append(f"k cos(depression) = {f['c_px_per_deg']:.0f} px/deg ({f['k_h_px_per_rad']:.3g} px/rad) from "
                 f"{f['windows_claiming']} window(s): k is at least this, so the field of view is at most "
                 f"{f['fov_w_ceiling_deg']:.3f} x {f['fov_h_ceiling_deg']:.3f} deg (reached only at a horizontal look)")
        if f.get("fov_w_deg"):
            L.append(f"at a depression of {f['depression_deg']:g} deg: k = {f['k_px_per_deg']:.0f} px/deg, field of view "
                     f"{f['fov_w_deg']:.3f} x {f['fov_h_deg']:.3f} deg")
    if f["c_at_least_px_per_deg"]:
        L.append(f"a slew the pointer does not register: k cos(depression) is at least {f['c_at_least_px_per_deg']:.0f} px/deg "
                 + ("(the pointer registers a slew elsewhere in the clip, so it follows the turret)" if f["floor_stands"] else
                    "IF the pointer follows the turret, which no window here shows; a pointer referenced to the platform's "
                    "heading registers no slew at any k"))
    L.append("assumes: " + "; ".join(f["assumes"]))
    return L


def main():
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
    ap.add_argument("--layer", default="all", choices=["all", "striated", "isotropic"],
                    help="which background's shifts (all: the largest motion group)")
    ap.add_argument("--window", action="append", metavar="T0:T1", help="a time window round a slew, s (repeat; "
                    "default: one round each slew the scene shows, start to stop, 3 s either side)")
    ap.add_argument("--degree", type=int, default=1, help="the hold rate as a polynomial in time of this degree")
    ap.add_argument("--still", action="store_true", help="the platform does not move (a camera on the ground, a ship at "
                    "anchor, an aerostat): no hold term, so a steady pan gives k too (the same as --degree 0)")
    ap.add_argument("--depression", type=float, help="the line of sight's depression, deg: k and the field of view "
                    "themselves instead of their bounds")
    ap.add_argument("--pixel-aspect", type=float, default=1.0, help="how much wider the video draws a pixel than it is "
                    "tall (a 4:3 sensor shown full-height in 16:9: 1.333). The pointer's angle and the scene's shift are "
                    "taken back to square pixels, and k is given in them")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        video, tag, _ = vf.resolve(args.video)
        clip = vclip.Clip(video, None, extract=False)
        out = vclip.out_prefix(args.out, tag)
        north, layers = Path(args.north or f"{out}_north.csv"), Path(args.layers or f"{out}_layers.csv")
        for pth, how in ((north, f"mcdonald symbology {args.video} --step 1 --out {args.out or '.'}"),
                         (layers, f"mcdonald layers {args.video} --out {args.out or '.'}")):
            if not pth.exists():
                raise SystemExit(f"{pth} is not there: make it first with `{how}`")
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps")
        wins = [tuple(float(v) for v in w.split(":")) for w in args.window] if args.window else None
        found = measure(north, layers, clip.W, clip.H, clip.fps, wins, 0 if args.still else args.degree, args.depression,
                        args.layer, out, tag,
                        pixel_aspect=args.pixel_aspect)
        print("\n".join(said(found.fields)))
        for w in found.no_power:
            print(f"no power: {w[1]}")
        for f in found.files:
            print(f"wrote {f}")
    code = vclip.EXIT_NOTHING if found.no_power else 0
    if args.json:
        emit(found.envelope("slew", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
