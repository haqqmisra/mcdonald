"""Hold a filmed screen still: register every frame to the display, and write the display's own video.

Much UAP video is not the sensor's recording but a phone held up to the sensor's screen
(PURSUE's fifth tranche, PR117-PR122: an AC-130's infrared display over the Gulf of Oman,
filmed by a crew member). The phone's frame is then not the sensor's frame. A thing held
dead centre by the sensor still wanders across the video, because the hand is what moves,
and every rate read off the raw pixels measures the hand. The same goes for anything
filmed off a monitor, a cockpit display or a television.

What is fixed on the display, and on nothing else, is the display's own drawing: the
reticle, the gate, the symbols, the screen's edge, its blemishes. This stage finds where
that drawing lies in every frame and maps each frame back onto it, so that the sensor's
picture stands still and only what the sensor saw moves.

**The model.** A flat screen seen by a pinhole camera is a plane seen in perspective, so
one homography per frame (`H`: display -> video) maps the whole screen exactly: the phone's
pan and tilt, its roll, its distance (the screen breathing in scale) and its keystone
(PR117's two reticle arms are not perpendicular in the video, 0.5 and 3 degrees off the
frame axes). What one homography cannot hold is named, not hidden: the phone lens's
distortion and its rolling shutter (a shear while the hand moves fast) are left in the
residual, which is measured.

**What is matched.** Not the picture: the sensor's scene moves on the display whenever
the sensor slews, and a match on it would cancel the very motion that is wanted. The
match is on the display's *structure* -- the band-passed magnitude |G(1) - G(4)| of the
grey frame, which keeps thin strokes of either polarity and drops the screen's glow, the
phone's vignetting and the scene's soft gradients -- and only where a **template** of
that structure is strong. The template is found, not given: every frame is aligned once
to the sharpest frame's structure (pass 1, frame after frame from it, each from the last
one's answer, with the template growing as the hand shows more of the screen), then the
**median** of the aligned structure over frames spread across the clip is the template
(what is fixed on the display survives a median; the scene, the objects, the grain and
anything fixed to the phone smear out of it), and every frame is aligned again to that
one template, independently (pass 2). Nothing is chained frame to frame in the answer, so
nothing drifts.

**How.** The enhanced correlation coefficient (Evangelidis & Psarakis 2008, IEEE TPAMI
30:1858), Gauss-Newton on the eight homography parameters, over the template's strong
pixels only, coarse to fine on a four-level pyramid (1/8, 1/4, 1/2, full). The ECC score
is invariant to the display's gain and offset, so a polarity or gain change of the
picture costs little (the overlay does not change with it), and |DoG| does not care which
way a stroke points. At the coarsest level a search over whole-pixel shifts
(`SEARCH_PX`) catches a fast jerk of the hand before Gauss-Newton refines it.

**What it reports.** Each frame's `H`, and from it the screen's centre's place in the
video, its scale, roll and keystone; the ECC score per frame (`rho`; a frame under
`RHO_LOST` is said to be lost: motion-blurred, or the drawing out of view); the hand's
motion and its spectrum (a held phone has a tremor at 8-12 Hz, an airframe's vibration
folds in at its own rate -- PR117's four-bladed propeller at 67.7 Hz lands at 7.7 Hz at
30 frames a second, inside the bird band: a brightness beat at a frequency the hand or the
airframe also shows is suspect); and, with `--check X,Y`, a held-out test: a small
display-fixed feature left out of the template (PR117's ring) followed in the held video,
whose wander is the stage's error.

**What it writes.** `<tag>_stabilize.csv` (frame, t, H, the derived motion, rho), the
display's video `<tag>_stable.mkv` (FFV1, lossless, the same frame rate; the canvas is the
reference frame's view, extended where the hand showed more), and a figure. The held video
is a video like any other: give it to `mcdonald look`, `mark`, `flicker`, `groups` and the
rest, and their pixels are the display's. `--track CSV` maps a track made on the raw
video into the display's coordinates instead (the same frames, x and y replaced).

**When it has no power.** A native recording (the overlay does not move in the video:
nothing to remove, and it says so); a screen with no drawing on it (nothing fixed to the
display to anchor to); a clip where the drawing is out of view or blurred for most
frames. Then the scene is the only anchor, and that cancels the sensor's slew as well as
the hand -- a different question, not answered here.
"""
import csv
import math
from pathlib import Path

import numpy as np
from scipy import ndimage

LEVELS = 4                 # pyramid levels: 1/8, 1/4, 1/2, full
INNER, OUTER = 1.0, 4.0    # |DoG| scales, px: keeps strokes 1-4 px wide, drops glow and gradients
COHERE = 8.0               # px: the window the strokes' one-directionality is judged over (long and straight:
                           # a reticle or a box edge keeps its direction over it, cloud and sea texture do not)
SEARCH_PX = 48             # whole-pixel shift search at the coarsest level, +- full-resolution px
ITERS = (40, 30, 20, 12)   # Gauss-Newton iterations, coarsest level first
EPS_PX = 0.02              # stop when no corner of the frame moves more than this (full-resolution px)
PERSIST_MIN = 0.5          # the drawing at the clip's start against its end, at least (`persistence`)
RHO_LOST = 0.35            # an ECC score under this: the frame is lost (blurred, or the drawing out of view)
BLACK = 14.0               # grey under this, after a 3-px blur: not picture (a letterbox, a pillarbox)
BLACK_GROW = 10            # px the not-picture mask is grown by, so its edge is not read as drawing
FRAME_EDGE = 6             # px of the frame's own edge never matched
BAND = 0.9                 # a row or column at least this black, from the frame's edge in, is letterbox or pillarbox
MEDIAN_FRAMES = 80         # frames spread over the clip whose aligned structure makes the template
TPL_K = 5.0                # template pixels kept: over median + TPL_K x MAD of the template
FILL = 4                   # frames: the longest gap in a held track that `to_clip` fills before carrying it back
PASS1_FINEST = 2           # pass 1 stops at the quarter-resolution level: it has only to land in pass 2's reach
MAX_POINTS = 30000         # template points used a level, at most (a fixed random draw): precision is long since
                           # set by then, and time goes as the count
TPL_GROW = 2               # px (at each level) the kept template pixels are grown by
MARGIN = 0.25              # the canvas: the reference view plus this much of it on every side, at most
REPEAT = 0.15              # a frame whose mean change is under this share of the clip's median change repeats the last
JUMP_SCALE = 0.15          # at most this |log| change of scale from one frame to the next
JUMP_ROLL = 6.0            # deg of roll, at most, from one frame to the next
FAST_HZ = 2.0              # the shake's fast part (tremor, vibration) starts here; under it, the hand's drift
JUMP_FRAC = 0.25           # of the frame's diagonal, at most, that the screen's centre moves in one frame

MODELS = ("translation", "similarity", "affine", "homography")


# ---- the display's structure -----------------------------------------------------------
def not_picture(g):
    """Where a frame is no picture at all: letterbox or pillarbox bands -- whole rows or
    columns of black running in from the frame's edge -- grown so that their edge (fixed to
    the phone's frame, and the strongest edge in it) is never matched. Black *inside* the
    picture is kept: a redaction box or a black symbol is the display's own drawing, and its
    straight edges are the best anchors there are (PR144's boxes)."""
    dark = ndimage.uniform_filter(g, 3) < BLACK
    h, w = dark.shape
    m = np.zeros_like(dark)
    cols = dark.mean(0) > BAND
    rows = dark.mean(1) > BAND
    for line, n, put in ((cols, w, lambda a, b: m.__setitem__((slice(None), slice(a, b)), True)),
                         (rows, h, lambda a, b: m.__setitem__((slice(a, b), slice(None)), True))):
        k = 0
        while k < n and line[k]:
            k += 1
        if k:
            put(0, k)
        k = n
        while k > 0 and line[k - 1]:
            k -= 1
        if k < n:
            put(k, n)
    if m.any():
        m = ndimage.binary_dilation(m, iterations=BLACK_GROW)
    # and the frame's own outermost pixels: an encoder's or a phone's edge column (PR117 has a
    # one-pixel green one down its right side) is fixed to the video, and pulls a match to the identity
    m[:FRAME_EDGE] = m[-FRAME_EDGE:] = True
    m[:, :FRAME_EDGE] = m[:, -FRAME_EDGE:] = True
    return m


def structure(g, bad=None, lines=True, half=False):
    """|G(INNER) - G(OUTER)| of a grey frame: thin strokes of either polarity, no glow.

    With `lines`, weighted by how one-directional the structure is round each pixel (the
    coherence of the structure tensor, ((l1 - l2) / (l1 + l2))**2 over a COHERE-px
    window): a stroke is 1, a sensor's grain or a speckle of sea near 0. On a grainy
    re-photographed screen (PR117) the grain otherwise outweighs the reticle, and a
    template made of grain matches nothing two frames later.

    With `half`, at half resolution (pixel i is the full frame's pixel 2i, as on the
    pyramid's level 1), every scale halved: a quarter of the work, for the first pass."""
    g = np.asarray(g, np.float32)
    k = 1.0
    if half:
        g = np.ascontiguousarray(ndimage.gaussian_filter(g, 1.0)[::2, ::2])
        bad = None if bad is None else bad[::2, ::2]
        k = 0.5
    d = ndimage.gaussian_filter(g, INNER * k) - ndimage.gaussian_filter(g, OUTER * k)
    s = np.abs(d)
    if lines:
        gy, gx = np.gradient(d)
        jxx = ndimage.gaussian_filter(gx * gx, COHERE * k)
        jyy = ndimage.gaussian_filter(gy * gy, COHERE * k)
        jxy = ndimage.gaussian_filter(gx * gy, COHERE * k)
        tr = jxx + jyy
        dif = np.sqrt((jxx - jyy) ** 2 + 4 * jxy * jxy)
        s = s * np.where(tr > 0, dif / np.maximum(tr, 1e-12), 0.0) ** 2
    if bad is not None:
        s[bad] = 0.0
    return s.astype(np.float32)


def pyramid(a, levels=LEVELS, blur=True):
    """[full, 1/2, 1/4, ...]: each level blurred and taken at every second pixel, so that
    pixel i of level L is pixel i * 2**L of the full frame."""
    out = [a]
    for _ in range(levels - 1):
        b = ndimage.gaussian_filter(out[-1], 1.0) if blur else out[-1]
        out.append(np.ascontiguousarray(b[::2, ::2]))
    return out


# ---- the homography, conditioned ---------------------------------------------------------
class Frame:
    """A coordinate normaliser: pixel (x, y) <-> ((x - cx) / s, (y - cy) / s), so that
    Gauss-Newton on the eight parameters is well conditioned."""

    def __init__(self, w, h, s=None):
        self.cx, self.cy = (w - 1) / 2.0, (h - 1) / 2.0
        self.s = float(s or max(w, h) / 2.0)
        self.N = np.array([[1 / self.s, 0, -self.cx / self.s], [0, 1 / self.s, -self.cy / self.s], [0, 0, 1.0]])
        self.Ninv = np.linalg.inv(self.N)


def basis(model):
    """Columns: how each of the model's parameters moves the eight of a homography
    [k11 k12 k13 k21 k22 k23 k31 k32] (normalised coordinates, k33 = 1)."""
    I = np.eye(8)
    if model == "translation":
        return I[:, [2, 5]]
    if model == "similarity":                    # scale and roll together, and the shift
        a = I[:, 0] + I[:, 4]
        b = -I[:, 1] + I[:, 3]
        return np.stack([a, b, I[:, 2], I[:, 5]], 1)
    if model == "affine":
        return I[:, :6]
    return I


def apply(H, x, y):
    w = H[2, 0] * x + H[2, 1] * y + H[2, 2]
    return (H[0, 0] * x + H[0, 1] * y + H[0, 2]) / w, (H[1, 0] * x + H[1, 1] * y + H[1, 2]) / w


def corners_moved(Ha, Hb, w, h):
    """The most any corner of a w x h canvas lands apart under two homographies, px."""
    xs, ys = np.array([0, w - 1, 0, w - 1.0]), np.array([0, 0, h - 1, h - 1.0])
    xa, ya = apply(Ha, xs, ys)
    xb, yb = apply(Hb, xs, ys)
    return float(np.max(np.hypot(xa - xb, ya - yb)))


# ---- the template ------------------------------------------------------------------------
class Template:
    """The display's structure on the canvas, as points per pyramid level: where it is
    strong (over median + TPL_K x MAD), grown by TPL_GROW, with the value there."""

    def __init__(self, tpl, valid=None, levels=LEVELS, k=TPL_K, hold_out=None):
        self.h, self.w = tpl.shape
        self.levels = []
        tv = tpl if valid is None else np.where(valid, tpl, 0)
        for L, a in enumerate(pyramid(tv.astype(np.float32), levels)):
            a = ndimage.gaussian_filter(a, 1.0)                      # a wider basin at every level
            v = a[a > 0]
            med = float(np.median(v)) if v.size else 0.0
            mad = float(np.median(np.abs(v - med))) * 1.4826 if v.size else 1.0
            keep = a > med + k * max(mad, 1e-6)
            keep = ndimage.binary_dilation(keep, iterations=TPL_GROW)
            if valid is not None:
                vl = pyramid(valid.astype(np.float32), levels, blur=False)[L] > 0.5
                keep &= ndimage.binary_erosion(vl, iterations=2)
            if hold_out is not None:
                hx, hy, hr = hold_out
                yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
                keep &= np.hypot(xx - hx / 2 ** L, yy - hy / 2 ** L) > hr / 2 ** L
            yy, xx = np.nonzero(keep)
            if len(yy) > MAX_POINTS:                                   # a fixed draw: the same points every frame
                pick = np.sort(np.random.default_rng(L).choice(len(yy), MAX_POINTS, replace=False))
                yy, xx = yy[pick], xx[pick]
            self.levels.append(dict(u=xx * 2.0 ** L, v=yy * 2.0 ** L, t=a[yy, xx].astype(np.float64)))

    def n_points(self, L=0):
        return len(self.levels[L]["t"])


# ---- one frame's alignment ---------------------------------------------------------------
def _sample(a, x, y, order=1):
    return ndimage.map_coordinates(a, [y, x], order=order, mode="constant", cval=np.nan, prefilter=False)


def _shift_search(T, I_L, K, fc, fi, L, reach):
    """Best whole-pixel shift (level px) of the template's points into level image I_L, by ZNCC."""
    q = T["u"], T["v"]
    qx, qy = (q[0] - fc.cx) / fc.s, (q[1] - fc.cy) / fc.s
    rx, ry = apply(K, qx, qy)
    x = np.rint((fi.cx + fi.s * rx) / 2 ** L).astype(int)
    y = np.rint((fi.cy + fi.s * ry) / 2 ** L).astype(int)
    t = T["t"] - T["t"].mean()
    h, w = I_L.shape
    best = (-2.0, 0, 0)
    for dy in range(-reach, reach + 1):
        yy = y + dy
        oky = (yy >= 0) & (yy < h)
        for dx in range(-reach, reach + 1):
            xx = x + dx
            ok = oky & (xx >= 0) & (xx < w)
            if ok.sum() < 0.3 * len(t):
                continue
            s = I_L[yy[ok], xx[ok]]
            s = s - s.mean()
            tt = t[ok] - t[ok].mean()
            d = math.sqrt(float(s @ s) * float(tt @ tt))
            r = float(s @ tt) / d if d > 0 else -1.0
            if r > best[0]:
                best = (r, dx, dy)
    return best


def ecc_level(T, I_L, gx_L, gy_L, K, fc, fi, L, B, iters, eps):
    """Gauss-Newton ECC on one level, from K (normalised coordinates). Returns K, rho, n used."""
    qx, qy = (T["u"] - fc.cx) / fc.s, (T["v"] - fc.cy) / fc.s
    t_all = T["t"]
    g_scale = fi.s / 2 ** L                      # d(level px)/d(normalised r)
    rho, used = np.nan, 0
    for _ in range(iters):
        D = K[2, 0] * qx + K[2, 1] * qy + 1.0
        rx = (K[0, 0] * qx + K[0, 1] * qy + K[0, 2]) / D
        ry = (K[1, 0] * qx + K[1, 1] * qy + K[1, 2]) / D
        x = (fi.cx + fi.s * rx) / 2 ** L
        y = (fi.cy + fi.s * ry) / 2 ** L
        iw = _sample(I_L, x, y)
        ok = np.isfinite(iw)
        used = int(ok.sum())
        if used < 64:
            return K, np.nan, used
        iw = iw[ok]
        gx = _sample(gx_L, x[ok], y[ok]) * g_scale
        gy = _sample(gy_L, x[ok], y[ok]) * g_scale
        q1, q2, Dk, r1, r2 = qx[ok], qy[ok], D[ok], rx[ok], ry[ok]
        gr = gx * r1 + gy * r2
        G = np.stack([gx * q1, gx * q2, gx, gy * q1, gy * q2, gy, -gr * q1, -gr * q2], 1) / Dk[:, None]
        G = G @ B
        G -= G.mean(0)
        t = t_all[ok] - t_all[ok].mean()
        iw = iw - iw.mean()
        tn, inn = math.sqrt(float(t @ t)), math.sqrt(float(iw @ iw))
        if tn == 0 or inn == 0:
            return K, np.nan, used
        rho = float(t @ iw) / (tn * inn)
        Hs = G.T @ G
        try:
            Hinv = np.linalg.inv(Hs)
        except np.linalg.LinAlgError:
            return K, rho, used
        ip, tp = G.T @ iw, G.T @ t
        lam_n = float(iw @ iw - ip @ Hinv @ ip)
        lam_d = float(t @ iw - tp @ Hinv @ ip)
        lam = lam_n / lam_d if lam_d > 0 else inn / tn
        dp = Hinv @ (G.T @ (lam * t - iw))
        step = (B @ dp)
        Kn = K.copy()
        Kn.flat[:8] += step
        moved = corners_moved(fi.Ninv @ K @ fc.N, fi.Ninv @ Kn @ fc.N, 2 * fc.cx + 1, 2 * fc.cy + 1)
        K = Kn
        if moved < eps:
            break
    return K, rho, used


def align(tpl, img, img_bad, H0, fc, fi, model="homography", levels=LEVELS, search=SEARCH_PX,
          iters=ITERS, eps=EPS_PX, finest=0, img_level=0):
    """H (display canvas -> this video frame) by ECC, from H0. Returns H, rho, points used.

    tpl is a Template; img the frame's structure (`structure`), img_bad where it is no
    picture. Coarse to fine; the coarse levels fit fewer parameters (translation, then
    similarity, then the model), so that a long reticle line does not pull the
    perspective terms before the shift is right."""
    I = [None] * img_level + pyramid(img.astype(np.float32), levels - img_level)
    finest = max(finest, img_level)
    K = fi.N @ H0 @ fc.Ninv
    K /= K[2, 2]
    rho, used = np.nan, 0
    order = MODELS.index(model)
    for L in range(levels - 1, finest - 1, -1):
        T = tpl.levels[L]
        if len(T["t"]) < 64:
            continue
        a = ndimage.gaussian_filter(I[L], 1.0)
        gy_L, gx_L = np.gradient(a)
        if L == levels - 1 and search:
            reach = max(1, int(round(search / 2 ** L)))
            r, dx, dy = _shift_search(T, a, K, fc, fi, L, reach)
            if r > -2:
                K = K.copy()
                # a shift of the image by (dx, dy) level px is a shift of r by (dx, dy) * 2**L / s
                Sx, Sy = dx * 2 ** L / fi.s, dy * 2 ** L / fi.s
                K = np.array([[1, 0, Sx], [0, 1, Sy], [0, 0, 1.0]]) @ K
        steps = [MODELS[min(order, 1 if L == levels - 1 else 2 if L == levels - 2 else order)]] if L > 1 else [model]
        if L == levels - 1:
            steps = ["translation"] + steps
        for m in steps:
            K, rho, used = ecc_level(T, a, gx_L, gy_L, K, fc, fi, L, basis(m), iters[levels - 1 - L], eps * 2 ** L)
    H = fi.Ninv @ K @ fc.N
    return H / H[2, 2], rho, used


# ---- warping -----------------------------------------------------------------------------
def warp_to_canvas(a, H, cw, ch, order=1, cval=np.nan):
    """The frame `a` (2-D, or H x W x C) seen on the canvas: canvas pixel (u, v) takes the
    frame's value at H(u, v). Outside the frame: cval."""
    vv, uu = np.mgrid[:ch, :cw].astype(np.float64)
    x, y = apply(H, uu, vv)
    if a.ndim == 2:
        return ndimage.map_coordinates(a, [y, x], order=order, mode="constant", cval=cval, prefilter=order > 1)
    return np.stack([ndimage.map_coordinates(a[..., c], [y, x], order=order, mode="constant", cval=cval,
                                             prefilter=order > 1) for c in range(a.shape[2])], -1)


def motion_of(H, fc):
    """What a display->video homography says of the hand, at the canvas centre: where the
    centre lands (x, y px), the local scale and roll there (d video / d display), and the
    keystone (the ratio of the two axes' scales, and their skew, deg)."""
    cx, cy = fc.cx, fc.cy
    x, y = apply(H, cx, cy)
    d = 1.0
    xu, yu = apply(H, cx + d, cy)
    xv, yv = apply(H, cx, cy + d)
    a = np.array([[xu - x, xv - x], [yu - y, yv - y]]) / d
    su, sv = math.hypot(a[0, 0], a[1, 0]), math.hypot(a[0, 1], a[1, 1])
    roll = math.degrees(math.atan2(a[1, 0], a[0, 0]))
    skew = math.degrees(math.atan2(a[0, 1], a[1, 1])) + roll
    return dict(x=float(x), y=float(y), scale=float(math.sqrt(abs(np.linalg.det(a)))), roll_deg=float(roll),
                aspect=float(su / sv) if sv else float("nan"), skew_deg=float(skew))


# ---- repeated frames -----------------------------------------------------------------------
def repeats(clip, frames, every=4):
    """Which frames repeat the one before (a phone's variable rate padded to a constant one:
    PR121 repeats one frame in four). Judged on a 1/`every` grey: a repeat's mean change is
    under REPEAT of the clip's median change. Returns {frame: the frame it repeats}."""
    prev, d = None, {}
    for n in frames:
        g = clip.grey(n)[::every, ::every]
        if prev is not None:
            d[n] = float(np.abs(g - prev).mean())
        prev = g
    if not d:
        return {}
    med = float(np.median(list(d.values())))
    out, last = {}, None
    for n in frames:
        if n in d and d[n] < REPEAT * med:
            out[n] = out.get(last, last)
        last = n
    return out


# ---- the two passes ------------------------------------------------------------------------
_W = {}


def _init(video, workdir, n0, n1, tpl, fc, fi, model, drawing):
    from .clip import Clip
    _W.update(clip=Clip(video, workdir, n0, n1, extract=False), tpl=tpl, fc=fc, fi=fi, model=model, drawing=drawing)


def _struct(clip, n, half=False):
    """A frame's structure, and where it is no picture. With the drawing in colour (`drawing`
    "chroma": PR144's orange reticle, brackets and N), the structure is the colour's -- how far
    the three channels lie apart -- so that a grey scene, however textured, is not in it."""
    from .clip import chroma_of, grey_of
    rgb = clip.rgb(n)
    g = grey_of(rgb)
    bad = not_picture(g)
    src = chroma_of(rgb) if _W.get("drawing") == "chroma" else g
    return structure(src, bad, half=half), bad


def _pass2(job):
    n, H0 = job
    s, bad = _struct(_W["clip"], n)
    H, rho, used = align(_W["tpl"], s, bad, H0, _W["fc"], _W["fi"], _W["model"], search=SEARCH_PX // 2)
    return n, H, rho, used


def _warped_struct(job):
    n, H, cw, ch = job
    s, bad = _struct(_W["clip"], n)
    w = warp_to_canvas(s, H, cw, ch, order=1, cval=np.nan)
    return n, w.astype(np.float16)


def sane(H, Hprev, fc):
    """Is H a plausible next step from Hprev? A hand does not halve the screen's size, roll
    it by tens of degrees or throw it half a frame within one frame; a diverged
    Gauss-Newton does all three."""
    if Hprev is None:
        return True
    a, b = motion_of(H, fc), motion_of(Hprev, fc)
    if not all(np.isfinite([a["x"], a["y"], a["scale"]])) or a["scale"] <= 0:
        return False
    return (abs(math.log(a["scale"] / b["scale"])) < JUMP_SCALE and abs(a["roll_deg"] - b["roll_deg"]) < JUMP_ROLL
            and math.hypot(a["x"] - b["x"], a["y"] - b["y"]) < JUMP_FRAC * math.hypot(2 * fc.cx, 2 * fc.cy))


def sharpest(clip, frames, n_try=24):
    """The frame whose display drawing is strongest (least motion blur): the reference."""
    pick = frames[:: max(1, len(frames) // n_try)]
    best, score = pick[0], -1.0
    for n in pick:
        s, _ = _struct(clip, n, half=True)
        v = float(np.sort(s.ravel())[-20000:].sum())
        if v > score:
            best, score = n, v
    return best


def first_pass(clip, frames, ref, fc, fi, model, reps, progress=None, every=15, region=None):
    """Every frame aligned to a template that starts as the reference frame's structure and
    grows (a running mean on the canvas, at half resolution, rebuilt every `every` frames)
    as the hand shows more of the screen; outward from the reference, each frame started
    from its neighbour's answer. Fitted to half resolution: this pass only has to land
    near enough for pass 2."""
    cw, ch = int(2 * fc.cx + 1), int(2 * fc.cy + 1)
    s0, bad0 = _struct(clip, ref, half=True)
    acc = np.zeros((ch // 2 + 1, cw // 2 + 1), np.float64)
    cnt = np.zeros_like(acc)
    H_ref = np.array([[1, 0, -(cw - clip.W) / 2.0], [0, 1, -(ch - clip.H) / 2.0], [0, 0, 1.0]])

    def add(s, H):
        Hh = np.diag([0.5, 0.5, 1.0]) @ H @ np.diag([2.0, 2.0, 1.0])   # canvas half-res px -> video half-res px
        w = warp_to_canvas(s, Hh, acc.shape[1], acc.shape[0], order=1, cval=np.nan)
        ok = np.isfinite(w)
        acc[ok] += w[ok]
        cnt[ok] += 1

    def build():
        m = np.where(cnt > 0, acc / np.maximum(cnt, 1), 0.0).astype(np.float32)
        full = ndimage.zoom(m, 2.0, order=1)[:ch, :cw]
        full = np.pad(full, ((0, ch - full.shape[0]), (0, cw - full.shape[1])))
        valid = ndimage.zoom((cnt > 0).astype(np.float32), 2.0, order=0)[:ch, :cw] > 0.5
        valid = np.pad(valid, ((0, ch - valid.shape[0]), (0, cw - valid.shape[1])))
        if region is not None:
            valid &= region
        return Template(full, valid)

    add(s0, H_ref)
    tpl = build()
    out = {ref: (H_ref, 1.0, True)}
    order = [ref] + [n for n in frames if n > ref] + [n for n in reversed(frames) if n < ref]
    done = 0
    for side in (+1, -1):
        H_prev, since = H_ref, 0
        seq = [n for n in frames if n > ref] if side > 0 else [n for n in reversed(frames) if n < ref]
        for n in seq:
            done += 1
            if progress:
                progress("pass 1: each frame onto the display, from its neighbour", done, len(order) - 1)
            if n in reps and reps[n] in out:
                out[n] = out[reps[n]]
                continue
            s, bad = _struct(clip, n, half=True)
            H, rho, used = align(tpl, s, bad, H_prev, fc, fi, model, finest=PASS1_FINEST, img_level=1)
            ok = np.isfinite(rho) and rho >= RHO_LOST and sane(H, H_prev, fc)
            if not ok:
                # once more from scratch about the last good answer, with a wider shift search
                H2, rho2, _ = align(tpl, s, bad, H_prev, fc, fi, model, finest=PASS1_FINEST, search=2 * SEARCH_PX,
                                    img_level=1)
                if np.isfinite(rho2) and rho2 >= RHO_LOST and sane(H2, H_prev, fc):
                    H, rho, ok = H2, rho2, True
            out[n] = (H if ok else H_prev, float(rho) if np.isfinite(rho) else float("nan"), bool(ok))
            if ok:
                H_prev = H
                add(s, H)
                since += 1
                if since >= every:
                    tpl, since = build(), 0
    return out


def median_template(clip, frames, first, cw, ch, initargs, procs=None, progress=None, hold_out=None,
                    n_most=MEDIAN_FRAMES, region=None):
    """The display's drawing: the median, over up to `n_most` well-aligned frames spread across
    the clip, of their structure seen on the canvas. What is fixed on the display survives
    it; the scene, the objects, the grain and what is fixed to the phone do not."""
    from .progress import pooled
    good = [n for n in frames if first[n][2]]
    pick = good[:: max(1, len(good) // n_most)][:n_most]
    jobs = [(n, first[n][0], cw, ch) for n in pick]
    got = pooled(procs, _warped_struct, jobs, init=_init, initargs=initargs, progress=progress,
                 what="the display's drawing: the median of the aligned frames", pixels=cw * ch)
    stack = np.stack([w for _, w in got])
    med = np.empty((ch, cw), np.float32)
    seen = np.empty((ch, cw), np.int32)
    for y0 in range(0, ch, 128):
        blk = stack[:, y0:y0 + 128].astype(np.float32)
        seen[y0:y0 + 128] = np.isfinite(blk).sum(0)
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                med[y0:y0 + 128] = np.nanmedian(blk, 0)
    valid = seen >= max(3, len(pick) // 4)
    if region is not None:
        valid &= region
    med = np.where(valid & np.isfinite(med), med, 0.0).astype(np.float32)
    tpl = Template(med, valid, hold_out=hold_out)
    return tpl, med, valid, len(pick), persistence(stack, tpl)


def persistence(stack, tpl, parts=3):
    """Is the drawing that was held the same at the clip's start as at its end? The aligned
    structure's median over the first third of the frames, against the last third's, on the
    template's strong pixels (a correlation coefficient). The display's drawing is the same
    picture all clip long, so it is near 1 when the display was held. When the scene was held
    instead -- a sensor slewing over textured cloud, which a hand-held phone's video also
    shows moving, so that both layers are candidates -- the scene that was held at the start
    has left by the end, and it falls (the PR144 self-test: pass 1 followed the clouds). A
    sensor that never slews makes the two the same, and then holding either is right."""
    k = len(stack) // parts
    if k < 3:
        return None
    T = tpl.levels[0]
    u, v = T["u"].astype(int), T["v"].astype(int)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        a = np.nanmedian(stack[:k, v, u].astype(np.float32), 0)
        b = np.nanmedian(stack[-k:, v, u].astype(np.float32), 0)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 200:
        return None
    a, b = a[ok] - a[ok].mean(), b[ok] - b[ok].mean()
    d = math.sqrt(float(a @ a) * float(b @ b))
    return round(float(a @ b) / d, 3) if d > 0 else None


def canvas_for(clip, margin=MARGIN):
    """The canvas: the reference view, with `margin` of it added on every side (even sizes)."""
    cw = int(round(clip.W * (1 + 2 * margin) / 2)) * 2
    ch = int(round(clip.H * (1 + 2 * margin) / 2)) * 2
    return cw, ch


def footprint(H, w, h):
    """Where a w x h video frame lies on the canvas (H: canvas -> video): its four corners."""
    Hi = np.linalg.inv(H)
    return np.array(apply(Hi, np.array([0, w - 1, w - 1, 0.0]), np.array([0, 0, h - 1, h - 1.0]))).T


# ---- the hand's motion, in numbers --------------------------------------------------------
def shake_spectrum(t, x, y, fmax=None):
    """Amplitude spectrum of the hand's motion (the display's centre in the video, px), by
    Lomb-Scargle on the frames that are not repeats: the times are a constant rate's with
    gaps where a frame repeats, so a plain FFT would see the repeats as a rhythm. A slow
    trend (a 1-s running mean) is taken out first. Returns f (Hz), amplitude (px)."""
    from scipy.signal import lombscargle
    t = np.asarray(t, float)
    if len(t) < 16:
        return np.array([]), np.array([])
    dt = float(np.median(np.diff(t)))
    k = max(3, int(round(1.0 / dt)) | 1)
    f = np.linspace(0.2, fmax or 0.5 / dt, 400)
    amp = np.zeros_like(f)
    for v in (np.asarray(x, float), np.asarray(y, float)):
        r = v - ndimage.uniform_filter1d(v, k, mode="nearest")
        p = lombscargle(t, r - r.mean(), 2 * np.pi * f, normalize=False)
        amp += np.sqrt(4 * p / len(t)) ** 2
    return f, np.sqrt(amp)


def peaks_of(f, a, n=4, within=(0.5, None)):
    """The `n` strongest local maxima of a spectrum, as (Hz, amplitude)."""
    if not len(f):
        return []
    lo, hi = within[0], within[1] or f[-1]
    i = [k for k in range(1, len(a) - 1) if a[k] >= a[k - 1] and a[k] >= a[k + 1] and lo <= f[k] <= hi]
    i = sorted(i, key=lambda k: -a[k])[:n]
    return [(round(float(f[k]), 2), round(float(a[k]), 2)) for k in sorted(i)]


def _fill_lost(Hs, ok):
    """A lost frame's H, between its good neighbours' (element by element, which is close
    enough for the small steps a hand makes between two good frames)."""
    ns = sorted(Hs)
    good = [n for n in ns if ok[n]]
    if not good:
        return Hs
    out = dict(Hs)
    for n in ns:
        if ok[n]:
            continue
        a = max((g for g in good if g < n), default=None)
        b = min((g for g in good if g > n), default=None)
        if a is None or b is None:
            out[n] = Hs[a if a is not None else b]
        else:
            w = (n - a) / (b - a)
            H = (1 - w) * Hs[a] + w * Hs[b]
            out[n] = H / H[2, 2]
    return out


def _warp_rgb(job):
    n, H, x0, y0, w, h = job
    rgb = _W["clip"].rgb(n)
    S = H @ np.array([[1, 0, x0], [0, 1, y0], [0, 0, 1.0]])        # output px -> canvas px -> video px
    a = warp_to_canvas(rgb, S, w, h, order=1, cval=np.nan)
    fill = np.nanmedian(a[::4, ::4].reshape(-1, 3), 0) if np.isfinite(a).any() else np.zeros(3)
    a = np.where(np.isfinite(a), a, fill)
    return n, np.clip(a + 0.5, 0, 255).astype(np.uint8)


def write_video(path, clip, frames, Hs, box, procs=None, progress=None):
    """The display's video: every frame (repeats and lost frames too, so that frame n here is
    frame n of the clip) warped onto the canvas box, lossless FFV1, at the clip's own rate."""
    import subprocess
    from .progress import pool_of, streamed
    x0, y0, w, h = box
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(clip.info["fps"]), "-i", "-", "-c:v", "ffv1", "-level", "3", "-pix_fmt", "rgb24", str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    pool = pool_of(procs, _init, _W["initargs"], pixels=w * h)
    try:
        for _, a in streamed(pool, _warp_rgb, [(n, Hs[n], x0, y0, w, h) for n in frames], progress=progress,
                             what="writing the display's video", ahead=24):
            p.stdin.write(a.tobytes())
    finally:
        if pool is not None:
            pool.terminate()
            pool.join()
        p.stdin.close()
        p.wait()
    if p.returncode:
        raise RuntimeError(f"ffmpeg could not write {path}")
    return path


def output_box(Hs, ok, clip, cw, ch, cover=0.5):
    """The part of the canvas worth writing: where at least `cover` of the good frames show
    picture, as (x0, y0, w, h), even sizes."""
    acc = np.zeros((ch // 8 + 1, cw // 8 + 1))
    good = [n for n in Hs if ok[n]]
    vv, uu = np.mgrid[:acc.shape[0], :acc.shape[1]] * 8.0
    for n in good[:: max(1, len(good) // 200)]:
        x, y = apply(Hs[n], uu, vv)
        acc += (x >= 0) & (x < clip.W) & (y >= 0) & (y < clip.H)
    m = acc >= cover * acc.max()
    ys, xs = np.nonzero(m)
    if not len(xs):
        return 0, 0, cw, ch
    x0, x1 = int(xs.min() * 8), int(min(cw, xs.max() * 8 + 8))
    y0, y1 = int(ys.min() * 8), int(min(ch, ys.max() * 8 + 8))
    return x0, y0, (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2


def held_out_wander(clip, frames, Hs, ok, at, box, r=None):
    """A display-fixed feature left out of the template, followed in the held video: its
    position on the canvas by ZNCC against its own median look, frame by frame. Its
    wander is what the stage's registration is worth at that place. `at` is (x, y, r) on
    the canvas."""
    from .forensics import zncc
    x, y, rr = at
    half = int(max(12, 1.6 * rr))
    good = [n for n in frames if ok[n]]
    pick = good[:: max(1, len(good) // 60)]
    patches = []
    for n in pick:
        S = Hs[n] @ np.array([[1, 0, x - 2 * half], [0, 1, y - 2 * half], [0, 0, 1.0]])
        g = warp_to_canvas(clip.grey(n), S, 4 * half + 1, 4 * half + 1, order=1, cval=np.nan)
        if np.isfinite(g).all():
            patches.append((n, g - ndimage.gaussian_filter(g, 6)))
    if len(patches) < 8:
        return None
    tpl = np.median(np.stack([g[half:3 * half + 1, half:3 * half + 1] for _, g in patches]), 0)
    pos = []
    for n, g in patches:
        c = zncc(tpl, g)
        iy, ix = np.unravel_index(np.nanargmax(c), c.shape)
        pos.append((n, ix - half, iy - half, float(np.nanmax(c))))
    a = np.array([[p[1], p[2]] for p in pos], float)
    a -= np.median(a, 0)
    rms = float(np.sqrt((a ** 2).sum(1).mean()))
    return dict(frames=len(pos), rms_px=round(rms, 2), p95_px=round(float(np.percentile(np.hypot(*a.T), 95)), 2),
                zncc_median=round(float(np.median([p[3] for p in pos])), 3), at=[round(x, 1), round(y, 1)])


def measure(clip, model="homography", ref=None, procs=None, progress=None, out=None, write=True,
            hold_out=None, track=None, mark_hz=(), anchor=None, drawing="grey"):
    """The stage: H for every frame, the hand's motion, and (with `write`) the held video.

    hold_out: (x, y, r, n) -- a display-fixed feature at (x, y) in frame n, radius r px, to
    leave out of the template and follow afterwards as the stage's own error.
    track: {frame: (x, y)} on the raw video, to be returned (and written) on the display.
    mark_hz: frequencies to mark on the hand's spectrum (an airframe's folded rate).
    anchor: (x0, y0, x1, y1, n) -- the display's drawing is inside this box of frame n (which
    becomes the reference): only it is matched. For a screen whose scene is richer than its
    drawing, where the stage could otherwise hold the scene (see `persistence`).
    drawing: "grey" (the default: white, grey or black strokes) or "chroma" (a coloured drawing over a
    grey picture -- the scene is then left out of the match altogether)."""
    from .progress import pooled
    from .report import Found
    frames = list(clip.frames())
    cw, ch = canvas_for(clip)
    fc, fi = Frame(cw, ch), Frame(clip.W, clip.H)
    say = progress or (lambda *a, **k: None)
    reps = repeats(clip, frames)
    _W["drawing"] = drawing
    region = None
    if anchor is not None:
        ax0, ay0, ax1, ay1, ref = anchor
        ox, oy = (cw - clip.W) / 2.0, (ch - clip.H) / 2.0          # the reference frame sits centred on the canvas
        region = np.zeros((ch, cw), bool)
        region[int(max(0, ay0 + oy)):int(min(ch, ay1 + oy)), int(max(0, ax0 + ox)):int(min(cw, ax1 + ox))] = True
    if ref is None:
        ref = sharpest(clip, [n for n in frames if n not in reps])
    first = first_pass(clip, frames, ref, fc, fi, model, reps, progress=progress, region=region)
    initargs = (str(clip.video), str(clip.dir), clip.n0, clip.n1, None, fc, fi, model, drawing)
    _W["initargs"] = initargs
    ho = None
    if hold_out is not None:
        hx, hy, hr, hn = hold_out
        Hn = first[hn][0] if hn in first else first[ref][0]
        u, v = apply(np.linalg.inv(Hn), hx, hy)
        ho = (float(u), float(v), float(hr) * 1.6)
    tpl, med, valid, n_med, persist = median_template(clip, frames, first, cw, ch, initargs, procs, progress, hold_out=ho,
                                                      region=region)
    initargs = (str(clip.video), str(clip.dir), clip.n0, clip.n1, tpl, fc, fi, model, drawing)
    _W["initargs"] = initargs
    jobs = [(n, first[n][0]) for n in frames if n not in reps]
    got = pooled(procs, _pass2, jobs, init=_init, initargs=initargs, progress=progress,
                 what="pass 2: each frame onto the display's drawing", pixels=cw * ch)
    Hs, rho, ok = {}, {}, {}
    for n, H, r, used in got:
        good = np.isfinite(r) and r >= RHO_LOST and sane(H, first[n][0], fc) and \
            corners_moved(H, first[n][0], clip.W, clip.H) < 0.1 * clip.W
        Hs[n], rho[n], ok[n] = (H if good else first[n][0]), float(r), bool(good)
    for n, twin in reps.items():
        Hs[n], rho[n], ok[n] = Hs[twin], rho[twin], ok[twin]
    Hs = _fill_lost(Hs, ok)
    mot = {n: motion_of(Hs[n], fc) for n in frames}
    t = {n: (n - 1) / clip.fps for n in frames}
    uniq = [n for n in frames if n not in reps and ok[n]]
    f, amp = shake_spectrum([t[n] for n in uniq], [mot[n]["x"] for n in uniq], [mot[n]["y"] for n in uniq])
    xs = np.array([mot[n]["x"] for n in uniq])
    ys = np.array([mot[n]["y"] for n in uniq])
    sc = np.array([mot[n]["scale"] for n in uniq])
    ro = np.array([mot[n]["roll_deg"] for n in uniq])
    step = np.hypot(np.diff(xs), np.diff(ys)) if len(xs) > 1 else np.array([0.0])
    native = len(uniq) > 8 and np.ptp(xs) < 2 and np.ptp(ys) < 2 and np.ptp(sc) < 0.002
    box = output_box(Hs, ok, clip, cw, ch)
    files, ho_res, tr_out = [], None, None
    tag = Path(out).name if out else clip.video.stem.lower()
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        csv_path = Path(f"{out}_stabilize.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            fh.write(f"# mcdonald stabilize: H maps the held video's pixel (u, v) + ({box[0]}, {box[1]}) on the canvas to "
                     f"the clip's pixel; model {model}; reference frame {ref}\n")
            w = csv.writer(fh)
            w.writerow(["frame", "t_s", "repeat_of", "ok", "rho", "x_px", "y_px", "scale", "roll_deg", "aspect",
                        "skew_deg"] + [f"h{i}{j}" for i in range(3) for j in range(3)])
            for n in frames:
                m = mot[n]
                Ho = Hs[n] @ np.array([[1, 0, box[0]], [0, 1, box[1]], [0, 0, 1.0]])
                Ho = Ho / Ho[2, 2]
                w.writerow([n, f"{t[n]:.4f}", reps.get(n, ""), int(ok[n]), f"{rho[n]:.3f}", f"{m['x']:.2f}", f"{m['y']:.2f}",
                            f"{m['scale']:.5f}", f"{m['roll_deg']:.3f}", f"{m['aspect']:.5f}", f"{m['skew_deg']:.3f}"]
                           + [f"{v:.9g}" for v in Ho.ravel()])
        files.append(csv_path)
        if track:
            tr_out = {}
            for n, (x, y) in track.items():
                if n in Hs:
                    S = Hs[n] @ np.array([[1, 0, box[0]], [0, 1, box[1]], [0, 0, 1.0]])
                    u, v = apply(np.linalg.inv(S), x, y)
                    tr_out[n] = (float(u), float(v))
            tp = Path(f"{out}_track_on_display.csv")
            with open(tp, "w", newline="", encoding="utf-8") as fh:
                fh.write("# the track, mapped from the clip's pixels onto the held video's (mcdonald stabilize)\n")
                w = csv.writer(fh)
                w.writerow(["frame", "x", "y"])
                for n in sorted(tr_out):
                    w.writerow([n, f"{tr_out[n][0]:.2f}", f"{tr_out[n][1]:.2f}"])
            files.append(tp)
        if write and not native:
            vp = Path(f"{out}_stable.mkv")
            write_video(vp, clip, frames, Hs, box, procs, progress)
            files.append(vp)
        if ho is not None:
            ho_res = held_out_wander(clip, frames, Hs, ok, ho, box)
        try:
            files.append(figure(f"{out}_stabilize.png", clip, frames, t, mot, rho, ok, reps, f, amp, med, valid, mark_hz,
                                tag))
        except Exception as ex:                                 # a figure is never worth the measurement
            print(f"(no figure: {ex})")
    fields = dict(model=model, drawing=drawing, reference_frame=ref, frames=len(frames), repeats=len(reps),
                  unique_rate_hz=round(clip.fps * (1 - len(reps) / max(1, len(frames))), 2),
                  aligned=int(sum(ok[n] for n in frames)), lost=int(sum(not ok[n] for n in frames)),
                  rho_median=round(float(np.median([rho[n] for n in uniq])), 3) if uniq else None,
                  template_frames=n_med, template_points=tpl.n_points(0), native=bool(native),
                  drawing_persistence=persist, anchor=list(anchor) if anchor else None,
                  hand_ptp_px=[round(float(np.ptp(xs)), 1), round(float(np.ptp(ys)), 1)] if len(xs) else None,
                  hand_step_median_px=round(float(np.median(step)), 2), hand_step_p95_px=round(float(np.percentile(step, 95)), 2),
                  scale_range=[round(float(sc.min()), 4), round(float(sc.max()), 4)] if len(sc) else None,
                  roll_range_deg=[round(float(ro.min()), 2), round(float(ro.max()), 2)] if len(ro) else None,
                  shake_peaks_hz_px=peaks_of(f, amp, within=(0.2, FAST_HZ)),
                  shake_fast_peaks_hz_px=peaks_of(f, amp, n=3, within=(FAST_HZ, None)),
                  shake_fast_floor_px=round(float(np.median(amp[f >= FAST_HZ])), 3) if len(f) else None,
                  canvas=[cw, ch], box=list(box),
                  held_out=ho_res)
    no_power, needs = [], []
    if native:
        no_power.append(("stabilize", "the display's drawing does not move in the video: a native recording, nothing to remove"))
    if persist is not None and persist < PERSIST_MIN:
        no_power.append(("stabilize", f"the drawing held at the clip's start is not the one held at its end (correlation "
                                      f"{persist:.2f}): what was held may be the sensor's scene, not the display"))
        needs.append("--anchor X0,Y0,X1,Y1@N: a box of frame N round the display's drawing (the reticle, symbols, edges)")
    if uniq and fields["lost"] > 0.3 * len(frames):
        no_power.append(("stabilize", f"{fields['lost']} of {len(frames)} frames could not be put on the display "
                                      "(blurred, or the drawing out of view)"))
    found = Found("stabilize", result={"display": said(fields)[0] if said(fields) else ""}, fields=fields,
                  no_power=no_power, needs=needs, files=files)
    found.carry = dict(H=Hs, ok=ok, box=box, track=tr_out, reps=reps)
    return found


def figure(path, clip, frames, t, mot, rho, ok, reps, f, amp, med, valid, mark_hz, tag):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 3, figsize=(15, 8.2), constrained_layout=True)
    tt = np.array([t[n] for n in frames])
    good = np.array([ok[n] for n in frames])
    x = np.array([mot[n]["x"] for n in frames])
    y = np.array([mot[n]["y"] for n in frames])
    a = ax[0, 0]
    a.plot(tt, x - x[good].mean(), lw=0.9, label="Across (x)")
    a.plot(tt, y - y[good].mean(), lw=0.9, label="Down (y)")
    a.set(xlabel="Time (s)", ylabel="Display Centre in the Video (px)", title="The Hand's Motion")
    a.legend(frameon=False)
    a = ax[0, 1]
    a.plot(tt, [mot[n]["scale"] for n in frames], lw=0.9, color="C2")
    a.set(xlabel="Time (s)", ylabel="Scale (Video px per Display px)", title="Distance to the Screen")
    b = a.twinx()
    b.plot(tt, [mot[n]["roll_deg"] for n in frames], lw=0.9, color="C3")
    b.set_ylabel("Roll (deg)", color="C3")
    a = ax[0, 2]
    r = np.array([rho[n] for n in frames])
    a.plot(tt, r, lw=0.8, color="0.3")
    a.scatter(tt[~good], r[~good], s=10, color="C3", label="Lost", zorder=3)
    rep = np.array([n in reps for n in frames])
    a.scatter(tt[rep], np.full(rep.sum(), 0.02), s=4, color="C1", marker="|", label="Repeated Frame")
    a.axhline(RHO_LOST, color="C3", lw=0.6, ls="--")
    a.set(xlabel="Time (s)", ylabel="ECC Score", ylim=(0, 1), title="Match to the Display's Drawing")
    a.legend(frameon=False, loc="lower right")
    a = ax[1, 0]
    if len(f):
        a.plot(f, amp, lw=0.9, color="0.2")
        a.axvspan(8, 12, color="C1", alpha=0.15, label="Hand Tremor, 8-12 Hz")
        for k, h in enumerate(mark_hz or ()):
            a.axvline(h, color="C4", lw=1, ls="--", label="Marked" if k == 0 else None)
        a.legend(frameon=False)
    a.set(xlabel="Frequency (Hz)", ylabel="Amplitude (px)", title="The Hand's Spectrum")
    a = ax[1, 1]
    a.imshow(np.where(valid, med, np.nan), cmap="gray_r", interpolation="nearest")
    a.set(title="The Display's Drawing (Template)", xticks=[], yticks=[])
    a = ax[1, 2]
    a.plot(x[good], y[good], lw=0.5, color="C0")
    a.invert_yaxis()
    a.set_aspect("equal")
    a.set(xlabel="x (px)", ylabel="y (px)", title="Display Centre's Path in the Video")
    fig.suptitle(f"{tag}: the display held still (mcdonald stabilize)")
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def said(fields):
    f = fields
    if f.get("native"):
        return ["The display's drawing does not move in this video: it is a native recording, and there is nothing to hold still."]
    L = [f"Held on the display ({f['model']}): {f['aligned']} of {f['frames']} frames aligned to the display's drawing "
         f"(median ECC {f['rho_median']}), {f['lost']} lost; reference frame {f['reference_frame']}."]
    if f["repeats"]:
        L.append(f"{f['repeats']} frames repeat the one before: the camera took about {f['unique_rate_hz']} pictures a "
                 "second, not the file's rate. Rates and beats are read on the frames that are new.")
    if f.get("hand_ptp_px"):
        L.append(f"The hand moved the display {f['hand_ptp_px'][0]:.0f} x {f['hand_ptp_px'][1]:.0f} px in the video "
                 f"(median {f['hand_step_median_px']} px a frame, 95 % under {f['hand_step_p95_px']}); scale "
                 f"{f['scale_range'][0]:.3f}-{f['scale_range'][1]:.3f}, roll {f['roll_range_deg'][0]:+.1f} to "
                 f"{f['roll_range_deg'][1]:+.1f} deg.")
    if f.get("shake_peaks_hz_px"):
        L.append("The hand's slow motion peaks at " + ", ".join(f"{h:g} Hz ({a:g} px)" for h, a in f["shake_peaks_hz_px"]) + ".")
    if f.get("shake_fast_peaks_hz_px"):
        L.append(f"Above {FAST_HZ:g} Hz (tremor, an airframe's vibration) the shake is {f['shake_fast_floor_px']} px "
                 "(median), strongest at " + ", ".join(f"{h:g} Hz ({a:g} px)" for h, a in f["shake_fast_peaks_hz_px"])
                 + ": a brightness beat at one of these is the hand's or the airframe's before it is the object's.")
    if f.get("drawing_persistence") is not None:
        p = f["drawing_persistence"]
        L.append(f"The drawing held is the same at the clip's start and end (correlation {p:.2f})." if p >= PERSIST_MIN else
                 f"WARNING: the drawing held at the clip's start is not the one at its end (correlation {p:.2f}): the stage "
                 "may have held the sensor's scene instead of the display. Give --anchor round the display's drawing.")
    if f.get("held_out"):
        h = f["held_out"]
        L.append(f"Held-out check: a display-fixed feature left out of the template wanders {h['rms_px']} px rms "
                 f"(95 % within {h['p95_px']} px) in the held video, over {h['frames']} frames.")
    return L


def read_homographies(csv_path):
    """{frame: H (held video px -> clip px)} and {frame: repeat_of or None} from a `<tag>_stabilize.csv`."""
    with open(csv_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    H = {int(r["frame"]): np.array([float(r[f"h{a}{b}"]) for a in range(3) for b in range(3)]).reshape(3, 3) for r in rows}
    rep = {int(r["frame"]): (int(r["repeat_of"]) if r["repeat_of"] else None) for r in rows}
    return H, rep


def to_clip(track, H, fill=FILL):
    """A track made on the held video, {frame: (x, y)}, on the clip's own pixels.

    Gaps of at most `fill` frames are filled first, on the held video -- where the object's
    own motion is smooth and the hand's is not in it -- and only then carried through each
    frame's homography. Returns {frame: (x, y, held_x, held_y, filled)}. For a measurement
    that must be made on the clip's own pixels: `flicker`'s codec controls need the clip's
    GOP, which the lossless held video does not have (PR117, PR121)."""
    ns = sorted(n for n in track if n in H)
    held = {}
    for a, b in zip(ns, ns[1:] + [None]):
        held[a] = (track[a][0], track[a][1], False)
        if b is not None and 1 < b - a <= fill + 1:
            for n in range(a + 1, b):
                w = (n - a) / (b - a)
                held[n] = ((1 - w) * track[a][0] + w * track[b][0], (1 - w) * track[a][1] + w * track[b][1], True)
    out = {}
    for n, (u, v, filled) in held.items():
        if n in H:
            x, y = apply(H[n], u, v)
            out[n] = (float(x), float(y), float(u), float(v), filled)
    return out


def write_track(path, track, note):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fh.write(f"# {note}\n")
        w = csv.writer(fh)
        w.writerow(["frame", "x", "y", "held_x", "held_y", "filled"])
        for n in sorted(track):
            x, y, u, v, f = track[n]
            w.writerow([n, f"{x:.2f}", f"{y:.2f}", f"{u:.2f}", f"{v:.2f}", int(f)])
    return path


def main():
    import argparse
    from . import forensics as vf
    from . import clip as vclip
    from .progress import PROCS_HELP, to_stderr
    from .report import Found, emit, inputs_of, said_to_stderr

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--model", choices=MODELS, default="homography",
                    help="what the screen may do in the video (default homography: a flat screen seen in perspective)")
    ap.add_argument("--ref", type=int, help="the reference frame (default: the one whose drawing is sharpest)")
    ap.add_argument("--hold-out", metavar="X,Y,R@N",
                    help="a display-fixed feature at (X, Y), radius R px, in frame N: left out of the template and "
                         "followed afterwards, as the stage's own error")
    ap.add_argument("--anchor", metavar="X0,Y0,X1,Y1@N",
                    help="the display's drawing is inside this box of frame N: match only it (for a screen whose scene "
                         "is richer than its drawing; N becomes the reference frame)")
    ap.add_argument("--drawing", choices=("grey", "chroma"), default="grey",
                    help="what the display's drawing is: grey (white, grey or black strokes; the default) or chroma (a "
                         "coloured overlay on a grey picture, which leaves the scene out of the match altogether)")
    ap.add_argument("--track", help="a track on the raw video (CSV with frame and x/y), to map onto the display")
    ap.add_argument("--mark-hz", default="", help="comma-separated frequencies to mark on the hand's spectrum")
    ap.add_argument("--no-video", action="store_true", help="the transforms and the figure only, no held video")
    ap.add_argument("--to-clip", metavar="HELD_TRACK.csv",
                    help="carry a track made on the HELD video back onto the clip's own pixels, from this run's "
                         "<tag>_stabilize.csv (it is not run again if that file is there); writes <tag>_track_on_clip.csv")
    ap.add_argument("--fill", type=int, default=FILL, help=f"with --to-clip: fill gaps of at most this many frames on the "
                                                           f"held video first (default {FILL})")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--procs", type=int, default=None, help=PROCS_HELP)
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        video, tag, _ = vf.resolve(args.video)
        clip = vclip.Clip(video, args.workdir, args.n0, args.n1)
        out = vclip.out_prefix(args.out, tag)
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
        if args.to_clip and Path(f"{out}_stabilize.csv").exists():
            found = Found("stabilize")                       # held already: carry the track back, measure nothing again
        else:
            ho = None
            if args.hold_out:
                xy, _, n = args.hold_out.partition("@")
                p = [float(v) for v in xy.split(",")]
                ho = (p[0], p[1], p[2] if len(p) > 2 else 20.0, int(n) if n else clip.n0)
            anchor = None
            if args.anchor:
                box, _, n = args.anchor.partition("@")
                q = [float(v) for v in box.split(",")]
                anchor = (q[0], q[1], q[2], q[3], int(n) if n else clip.n0)
            track = vf.read_track(args.track) if args.track else None
            mark = [float(v) for v in args.mark_hz.split(",") if v.strip()]
            found = measure(clip, args.model, args.ref, args.procs, to_stderr(), out, not args.no_video, ho, track, mark,
                            anchor, args.drawing)
            print("\n".join(said(found.fields)))
            for f in found.files:
                print(f"  wrote {f}")
        if args.to_clip:
            H, _ = read_homographies(f"{out}_stabilize.csv")
            tr = to_clip(vf.read_track(args.to_clip), H, args.fill)
            p = write_track(f"{out}_track_on_clip.csv", tr, f"{args.to_clip} carried from the held video onto the clip's "
                                                           f"pixels through {out}_stabilize.csv; gaps up to {args.fill} filled")
            n_f = sum(1 for v in tr.values() if v[4])
            print(f"{args.to_clip}: {len(tr)} frames on the clip's pixels ({n_f} filled on the held video); wrote {p}")
            found.fields.update(to_clip=str(p), to_clip_frames=len(tr), to_clip_filled=n_f)
            found.files.append(str(p))
    code = vclip.EXIT_NOTHING if found.no_power else 0
    if args.json:
        emit(found.envelope("stabilize", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
