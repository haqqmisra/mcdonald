"""Shared measurement routines: masks, registration, layers, cadence, detection.

Everything here was first worked out on one clip (DOW-UAP-PR144) and then made
independent of it: any frame size, any frame range, coloured or white symbology,
bright or dark objects. `mcdonald.layers` and `mcdonald.integrity` are the two
tools built on it.

Traps these routines are built around (each one cost a wrong number once)
- A static pattern (sensor fixed-pattern noise, codec blocking, symbology)
  correlates at zero shift. Exclude a zone about zero, and reject peaks on the
  rim of that zone: they are not verified maxima.
- Same-position windowed cross-correlation under-reads large shifts (overlap
  taper). Search for a whole template instead; it has no taper.
- Many sensor clips repeat frames and catch up with a double step. Never use
  per-frame differences as rates; average over >= 1 s of wall-clock time.
- A pixel-darkness mask for redaction blocks swallows the dark sharpening halo
  of a bright object over a dark scene. Blocks are large, static and dark.
- The corner brackets of turret symbology mark the NEXT field of view. Fit a
  zoom ratio from the imagery (zoom_ratio), never from the brackets.
- "Striated" texture has a correlation peak much flatter along one direction
  (open sea: along the wave crests); "isotropic" texture does not (cloud, land).
  The two classes are tracked separately because layers at different ranges do
  not move together when the platform moves (PR144: 98 px/s apart).

Frame numbering, fps and shift conventions live in mcdonald.clip.
"""
import csv

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.signal import fftconvolve

# Re-exported so tools can reach the whole measurement surface through one
# import, as they did when this was a single module.
from .progress import Stopped, counted, pooled  # noqa: F401
from .clip import (EXIT_INPUT, EXIT_MISSING, EXIT_NOTHING, Clip, MissingTool, NotAVideo, Stop,  # noqa: F401
                   case_dir, cost_text, out_prefix, probe, require_ffmpeg, resolve)


# ---- what is not scene: symbology, redaction blocks, captions --------------------------
def scene_sd(g):
    h, w = g.shape
    return float(g[h // 6:5 * h // 6, w // 6:5 * w // 6].std())


def static_masks(clip, n_sample=40, progress=None):
    """Masks that hold for the whole clip, from an even sample of its frames.
    blocks: large regions that are dark in nearly every frame (redaction).
    graphics: pixels that keep a colour cast, or stay put and sharp, while the
    scene changes (burned-in symbology of any colour)."""
    ns = np.linspace(clip.n0, clip.n1, min(n_sample, clip.n1 - clip.n0 + 1)).astype(int)
    gs, ch, cols = [], [], []
    for n in counted(ns, progress, what="finding what never changes in the picture: reading frames"):
        rgb = clip.rgb(int(n))
        gs.append(rgb.mean(2))
        ch.append(rgb.max(2) - rgb.min(2))
        cols.append(rgb.astype(np.uint8))
    gs, ch = np.stack(gs), np.stack(ch)
    sd = np.array([scene_sd(g) for g in gs])
    live = sd > 0.5 * np.median(sd)                      # leave flat calibration frames out
    gs, ch = gs[live], ch[live]
    ref_rgb = np.median(np.stack([c for c, ok in zip(cols, live) if ok][::2]), 0).astype(np.float32)
    del cols
    dark = (gs < 5).mean(0) > 0.95                         # redaction is black; a night sky is merely dark
    lab, nl = ndimage.label(dark)
    if nl:
        size = ndimage.sum(dark, lab, np.arange(1, nl + 1))
        dark = np.isin(lab, 1 + np.nonzero(size >= 1500)[0])
    med = np.median(gs, 0)
    sharp = np.abs(med - ndimage.gaussian_filter(med, 4.0)) > 20
    static = gs.std(0) < 2.0
    still_scene = static[~dark].mean() > 0.3               # then "static and sharp" is the scene, not graphics
    colour = float((ch > 40).mean()) > 0.2                 # a colour clip: colour is scene, not symbology
    graphics = (((ch > 40).mean(0) > 0.5) & (not colour)) | (static & sharp & ~dark & (not still_scene))
    return {"blocks": ndimage.binary_dilation(dark, iterations=8),
            "graphics": ndimage.binary_dilation(graphics, iterations=4),
            "blocks_raw": dark, "graphics_raw": graphics, "ref_rgb": ref_rgb, "still_scene": bool(still_scene),
            "colour": bool(colour)}


def refine_graphics(clip, masks, moving, n_sample=40):
    """Symbology of any colour or opacity, from frames in which the scene
    sweeps the detector. Their temporal median smooths the scene away, so
    whatever is still sharp in it stays put on the screen. (A variance test
    misses dark, semi-transparent symbology: PR148's reticle varies by 3-6 DN
    as the sea passes under it.) Needed whenever the scene is still for part
    of the clip, because static_masks then cannot tell symbology from scenery."""
    if len(moving) < 20:
        return masks
    ns = [moving[i] for i in np.unique(np.linspace(0, len(moving) - 1, n_sample).astype(int))]
    med = np.median(np.stack([clip.grey(n) for n in ns]), 0)
    g = (np.abs(med - ndimage.gaussian_filter(med, 4.0)) > 20) & ~masks["blocks"]
    out = dict(masks)
    out["graphics_raw"] = masks["graphics_raw"] | g
    out["graphics"] = masks["graphics"] | ndimage.binary_dilation(g, iterations=4)
    return out


def frame_mask(rgb, masks, rows=None, n=None, grow=4):
    """Static masks plus this frame's own coloured symbology and any burned-in
    caption rows given as (y0, y1, first frame, last frame)."""
    bad = masks["blocks"] | masks["graphics"]
    if not masks.get("colour"):
        bad = bad | ndimage.binary_dilation((rgb.max(2) - rgb.min(2)) > 40, iterations=grow)
    bad[:6, :] = bad[-6:, :] = True
    bad[:, :6] = bad[:, -6:] = True
    for y0, y1, a, b in rows or []:
        if n is None or a <= n <= b:
            bad[y0:y1, :] = True
    return bad


def parse_rows(spec):
    """'985:1080:1:165,0:40' -> [(985, 1080, 1, 165), (0, 40, 1, 10**9)]"""
    out = []
    for part in filter(None, (spec or "").split(",")):
        v = [int(x) for x in part.split(":")]
        out.append((v[0], v[1], v[2] if len(v) > 2 else 1, v[3] if len(v) > 3 else 10 ** 9))
    return out


# ---- registration ---------------------------------------------------------------------
def boxsum(a, h, w):
    c = np.cumsum(np.cumsum(np.pad(a, ((1, 0), (1, 0))), 0), 1)
    return c[h:, w:] - c[:-h, w:] - c[h:, :-w] + c[:-h, :-w]


def zncc(tpl, img):
    """Zero-mean normalised cross-correlation of a template over an image
    ('valid' placements). No window, so no pull toward zero shift."""
    h, w = tpl.shape
    tz = tpl - tpl.mean()
    e = np.sqrt((tz * tz).sum())
    if e < 1e-6:                                          # a flat template matches nothing
        return np.zeros((img.shape[0] - h + 1, img.shape[1] - w + 1))
    num = fftconvolve(img, tz[::-1, ::-1], mode="valid")
    s1, s2 = boxsum(img, h, w), boxsum(img * img, h, w)
    return num / (e * np.sqrt(np.maximum(s2 - s1 * s1 / (h * w), 1e-6)))


def _par(m1, m0, p1):
    d = m1 - 2 * m0 + p1
    return 0.0 if d == 0 else 0.5 * (m1 - p1) / d


def bandpass(g, lo=1.0, hi=12.0):
    return ndimage.gaussian_filter(g, lo) - ndimage.gaussian_filter(g, hi)


SHIFT_COLS = "a x y dx dy pk pk2 ani theta mean".split()


def shift_field(ga, gb, bad_a, bad_b, a=0, tpl=128, stride=96, reach=245, zero=4):
    """Where each clean tpl-px template of frame a is found in frame b.
    Rows of SHIFT_COLS: template centre, shift, ZNCC peak and runner-up, the
    peak's anisotropy (smaller / larger curvature; ~0 striated, ~1 isotropic)
    and the direction of its flat axis [deg], and the template's mean level.
    A zone of +-zero px about zero shift is excluded, and peaks on its rim
    are dropped (see the module docstring)."""
    H, W = ga.shape
    ha, hb = bandpass(ga), bandpass(gb)
    out = []
    for y0 in range(16, H - tpl - 16, stride):
        for x0 in range(16, W - tpl - 16, stride):
            if bad_a[y0:y0 + tpl, x0:x0 + tpl].any():
                continue
            ys, ye = max(0, y0 - reach), min(H, y0 + tpl + reach)
            xs, xe = max(0, x0 - reach), min(W, x0 + tpl + reach)
            c = zncc(ha[y0:y0 + tpl, x0:x0 + tpl], hb[ys:ye, xs:xe])
            c = np.where(boxsum(bad_b[ys:ye, xs:xe].astype(np.float32), tpl, tpl) > 0, -1.0, c)
            oy, ox = y0 - ys, x0 - xs
            if zero >= 0:
                c[max(oy - zero, 0):oy + zero + 1, max(ox - zero, 0):ox + zero + 1] = -1.0
            py, px = np.unravel_index(np.argmax(c), c.shape)
            if not (0 < py < c.shape[0] - 1 and 0 < px < c.shape[1] - 1):
                continue
            n9 = c[py - 1:py + 2, px - 1:px + 2]
            if n9.min() <= -1.0:                          # on the rim of the excluded zone or of a mask
                continue
            pk = float(c[py, px])
            kxx = 2 * pk - n9[1, 0] - n9[1, 2]
            kyy = 2 * pk - n9[0, 1] - n9[2, 1]
            kxy = (n9[2, 2] + n9[0, 0] - n9[0, 2] - n9[2, 0]) / 4
            ev, evec = np.linalg.eigh(np.array([[kxx, -kxy], [-kxy, kyy]]))
            ani = float(max(ev[0], 0) / max(ev[1], 1e-9))
            theta = float(np.degrees(np.arctan2(evec[1, 0], evec[0, 0])))   # flat axis
            c2 = c.copy()
            c2[max(py - 12, 0):py + 13, max(px - 12, 0):px + 13] = -1.0
            out.append((a, x0 + tpl / 2, y0 + tpl / 2,
                        px - ox + _par(n9[1, 0], pk, n9[1, 2]), py - oy + _par(n9[0, 1], pk, n9[2, 1]),
                        pk, float(c2.max()), ani, theta, float(ga[y0:y0 + tpl, x0:x0 + tpl].mean())))
    return np.array(out, dtype=np.float64).reshape(-1, len(SHIFT_COLS))


def still_score(ga, gb, bad_a, bad_b, tpl=128, stride=192):
    """Median same-position ZNCC of clean templates: near 1 when the scene (or
    a static pattern that dominates it) has not moved between the two frames."""
    ha, hb = bandpass(ga), bandpass(gb)
    out = []
    for y0 in range(16, ga.shape[0] - tpl - 16, stride):
        for x0 in range(16, ga.shape[1] - tpl - 16, stride):
            sl = (slice(y0, y0 + tpl), slice(x0, x0 + tpl))
            if bad_a[sl].any() or bad_b[sl].any():
                continue
            a, b = ha[sl] - ha[sl].mean(), hb[sl] - hb[sl].mean()
            d = np.sqrt((a * a).sum() * (b * b).sum())
            if d > 1e-6:
                out.append(float((a * b).sum() / d))
    return float(np.median(out)) if out else 0.0


def shift_field_auto(ga, gb, bad_a, bad_b, **kw):
    """shift_field, with zero shift allowed when the scene is held still on
    screen: its true peak then lies inside the excluded zone, and what is left
    are chance peaks far away. Still means a same-position ZNCC >= 0.9, or an
    exclusion that leaves almost no clean match. Returns (field, still). A still
    field can be locked by a static pattern, so read its shifts as "no more than"."""
    if still_score(ga, gb, bad_a, bad_b) < 0.9:
        f = shift_field(ga, gb, bad_a, bad_b, **kw)
        if len(f) and len(good(f)) >= 0.2 * len(f):
            return f, False
    return shift_field(ga, gb, bad_a, bad_b, **{**kw, "zero": -1}), True


def good(f, pk_min=0.5, pk_gap=0.05):
    return f[(f[:, 5] >= pk_min) & (f[:, 5] - f[:, 6] >= pk_gap)]


def consensus(v, tolx=6.0, toly=2.5, minn=8):
    """Median of the largest group of shifts agreeing within the tolerances.
    Returns (shift, members, boolean membership) or None."""
    if len(v) < minn:
        return None
    near = lambda p: (np.abs(v[:, 0] - p[0]) < tolx) & (np.abs(v[:, 1] - p[1]) < toly)
    seed = v[int(np.argmax([near(p).sum() for p in v]))]
    keep = near(np.median(v[near(seed)], 0))
    if keep.sum() < minn:
        return None
    return np.median(v[keep], 0), int(keep.sum()), keep


def layers_of(f, ani_striated=0.25, ani_isotropic=0.4, dark_below=None, tol=(6.0, 2.5), minn=8):
    """Per-class consensus for one frame pair, and how many motion groups the
    good templates fall into regardless of texture.
    dark_below: keep only striated templates darker than this level (open sea
    is dark in white-hot IR; striated cloud is not)."""
    g = good(f)
    res = {"n_good": len(g), "n_tpl": len(f)}
    sel = {"all": np.ones(len(g), bool), "striated": g[:, 7] < ani_striated, "isotropic": g[:, 7] >= ani_isotropic}
    if dark_below is not None:
        sel["striated"] &= g[:, 9] < dark_below
    for name, m in sel.items():
        c = consensus(g[m][:, 3:5], tol[0], tol[1], minn)
        res[name] = None if c is None else (c[0], c[1])
    first = consensus(g[:, 3:5], tol[0], tol[1], minn)
    res["groups"], res["inliers"] = 0, 0.0
    if first is not None:
        rest = g[~first[2]]
        second = consensus(rest[:, 3:5], tol[0], tol[1], minn)
        if second is not None and np.hypot(*(second[0] - first[0])) < 2 * tol[0]:
            second = None                                 # the first group's own scatter, not a layer
        res["groups"] = 1 + (second is not None)
        res["inliers"] = (first[1] + (second[1] if second else 0)) / max(len(g), 1)
        res["group_gap"] = float(np.hypot(*(second[0] - first[0]))) if second else 0.0
    return res


def windowed(series, n0, n1, k, half=15, need=24):
    """Mean vector over +-half frames of a {first frame of pair: vector} series
    whose pairs span k frames; needs `need` pairs so that a window at the edge
    of a gap is not part-filled."""
    out = {}
    for n in range(n0, n1 + 1):
        v = [series[a] for a in range(n - half - k // 2, n + half - k // 2) if a in series]
        if len(v) >= need:
            out[n] = np.mean(v, 0)
    return out


# ---- cadence and transients -------------------------------------------------------------
def _series_chunk(job):
    video, workdir, n0, n1, a, b, ok = job
    clip = Clip(video, workdir, n0, n1)
    h0, h1, w0, w1 = clip.H // 7, 6 * clip.H // 7, clip.W // 9, 8 * clip.W // 9
    prev, rows = None, []
    for n in range(max(a - 1, n0), b + 1):
        g = clip.grey(n)[h0:h1, w0:w1]
        if n >= a:
            d = np.nan if prev is None else float(np.abs(g - prev)[ok].mean())
            rows.append((n, d, float(g[ok].std())))
        prev = g
    return rows


def frame_series(clip, masks=None, procs=10, progress=None, stop=None):
    """Per frame: mean |difference| from the previous frame and the scene's sd,
    both over the central, unmasked area."""
    h0, h1, w0, w1 = clip.H // 7, 6 * clip.H // 7, clip.W // 9, 8 * clip.W // 9
    ok = np.ones((h1 - h0, w1 - w0), bool) if masks is None else ~(masks["blocks"] | masks["graphics"])[h0:h1, w0:w1]
    edges = np.linspace(clip.n0, clip.n1 + 1, procs * 3 + 1).astype(int)
    jobs = [(clip.video, clip.dir, clip.n0, clip.n1, int(a), int(b) - 1, ok) for a, b in zip(edges[:-1], edges[1:]) if b > a]
    done = pooled(procs, _series_chunk, jobs, progress=progress, stop=stop, what="survey: reading the frames, in groups")
    return np.array([r for rows in done for r in rows])


def repeats(series):
    """Frames that repeat their predecessor: a difference far below the local
    norm (a fixed threshold mistakes quiet, low-contrast footage for repeats)."""
    n, d = series[:, 0].astype(int), series[:, 1]
    out = []
    for i in range(1, len(n)):
        loc = d[max(1, i - 10):i + 11]
        loc = loc[np.isfinite(loc)]
        if np.isfinite(d[i]) and d[i] < 0.2 * np.median(loc) and d[i] < 0.35:
            out.append(int(n[i]))
    return out


def transients(series, frac=0.35, max_len=40):
    """Runs of frames whose scene contrast collapses (flat calibration field,
    gain transient, blank between fields of view). Returns [(first, last)]."""
    n, sd = series[:, 0].astype(int), series[:, 2]
    ref = ndimage.median_filter(sd, size=61, mode="nearest")
    low = sd < frac * ref
    runs, i = [], 0
    while i < len(n):
        if low[i]:
            j = i
            while j + 1 < len(n) and low[j + 1]:
                j += 1
            if j - i + 1 <= max_len:
                runs.append((int(n[i]), int(n[j])))
            i = j + 1
        else:
            i += 1
    return runs


def zoom_ratio(clip, n_before, n_after, masks, boresight=None):
    """Zoom ratio across a blank, from the imagery: the later frame shrunk by s
    and matched about the boresight of the earlier one (s > 1: zoomed in), and
    the reverse (reported as s < 1). Coarse scan, then a fine one. Returns
    (s, ZNCC, (dx, dy) of the match from a boresight-centred zoom, ZNCC at s = 1).
    Trust s only when the ZNCC is high (>= 0.6)."""
    bx, by = boresight or (clip.W / 2, clip.H / 2)

    def clean(n):
        g = clip.grey(n)
        return np.where(frame_mask(clip.rgb(n), masks), ndimage.median_filter(g, 25), g)

    fb, fa = clean(n_before), clean(n_after)

    def fit(wide, nar, s):
        same = s < 1.25                                   # same scale: the scene may have swept on, so
        fx, fy, m = (0.35, 0.30, int(0.33 * clip.W)) if same else (0.17, 0.14, 60)   # a small template, a wide search
        x0, x1, y0, y1 = int(fx * clip.W), int((1 - fx) * clip.W), int(fy * clip.H), int((1 - fy) * clip.H)
        small = ndimage.zoom(ndimage.gaussian_filter(nar, max(0.5 * s, 0.5)), 1 / s, order=1)
        t = small[int(y0 / s):int(y1 / s), int(x0 / s):int(x1 / s)]
        if min(t.shape) < 24:
            return -1.0, (0.0, 0.0)
        hp = 30 if same else 8                            # fine texture (sea) decorrelates in ~0.3 s
        t = t - ndimage.gaussian_filter(t, hp)
        ex, ey = bx + (x0 - bx) / s, by + (y0 - by) / s
        ya, xa = max(int(ey) - min(m, int(0.28 * clip.H)), 0), max(int(ex) - m, 0)
        img = wide[ya:int(ey) + t.shape[0] + m, xa:int(ex) + t.shape[1] + m]
        if img.shape[0] <= t.shape[0] or img.shape[1] <= t.shape[1]:
            return -1.0, (0.0, 0.0)
        c = zncc(t, img - ndimage.gaussian_filter(img, hp))
        py, px = np.unravel_index(np.argmax(c), c.shape)
        return float(c[py, px]), (xa + px - ex, ya + py - ey)

    best = {}
    for sign, wide, nar in ((+1, fb, fa), (-1, fa, fb)):
        coarse = {s: fit(wide, nar, s) for s in np.arange(1.0, 9.01, 0.5)}
        s0 = max(coarse, key=lambda k: coarse[k][0])
        fine = {round(float(s), 2): fit(wide, nar, s) for s in np.arange(max(s0 - 0.5, 1.0), s0 + 0.51, 0.1)}
        for s, v in {**coarse, **fine}.items():
            key = round(float(s) if sign > 0 else 1 / float(s), 4)
            if key not in best or v[0] > best[key][0]:
                best[key] = v
    s = max(best, key=lambda k: best[k][0])
    return s, best[s][0], best[s][1], best.get(1.0, (np.nan,))[0]


# ---- a compact source -------------------------------------------------------------------
def read_track(path, cols=None):
    """{frame: (x, y)} from a CSV with a frame column and x/y columns.

    Leading `#` lines and blank lines are skipped, so a track file can carry
    its own provenance header -- which a track that will be quoted in a paper
    should."""
    with open(path, newline="") as f:
        lines = [ln for ln in f if ln.strip() and not ln.lstrip().lstrip('"').startswith("#")]
    rows = list(csv.DictReader(lines))
    if not rows:
        raise ValueError(f"{path}: no data rows")
    keys = rows[0].keys()
    fc = next(k for k in ("frame", "n", "frame_n") if k in keys)
    xc, yc = cols or next((a, b) for a, b in (("x_px", "y_px"), ("x", "y"), ("x1", "y1"), ("grp_x", "grp_y")) if a in keys)
    return {int(float(r[fc])): (float(r[xc]), float(r[yc])) for r in rows if r[xc] not in ("", "nan") and r[yc] != ""}


def _kernel(size):
    r = int(np.ceil(1.35 * size)) + 1
    rr = np.hypot(*np.mgrid[-r:r + 1, -r:r + 1])
    core, ann = (rr <= 0.39 * size).astype(float), ((rr >= 0.83 * size) & (rr <= 1.28 * size)).astype(float)
    return core / core.sum() - ann / ann.sum()


N_STRONG = 25       # the spots a frame the blind tracker, Find and the choice of detector look at


def source_candidates(g, bad, size=9.0, dark=False, n_max=N_STRONG, min_resp=35.0):
    """Strongest compact sources of about `size` px: disk minus annulus. Keep many:
    a noisy detector zone can out-score the object, and the linker picks by position.

    n_max=None keeps every spot over min_resp: the N_STRONG strongest found exactly as
    with a limit, strongest first, then the rest, each the peak of its own 2r+1 square of
    the response and not within r of one of those, weakest last. A link from marks takes them all and chooses by position and likeness
    (autolink.LIKE): on PR148 the object is 69th to 460th of 900-2,258 specks of sea."""
    img = -g if dark else g
    resp = ndimage.correlate(img, _kernel(size), mode="nearest")
    resp[bad] = 0
    out, r = [], int(size)
    # a spot is measured on the 3r about it, so the band 3r wide at the edge is left out before
    # looking -- until 2026-09-23 the search stopped at the first spot in it, and every weaker
    # spot in the frame went with it (12 on a PR148 frame instead of 25)
    resp[:3 * r], resp[g.shape[0] - 3 * r:] = 0, 0
    resp[:, :3 * r], resp[:, g.shape[1] - 3 * r:] = 0, 0
    ys, xs = np.mgrid[-r:r + 1, -r:r + 1]

    def centre(py, px, v):
        sub = img[py - r:py + r + 1, px - r:px + r + 1]
        loc = float(np.median(img[py - 3 * r:py + 3 * r + 1, px - 3 * r:px + 3 * r + 1]))
        m = (sub >= loc + 0.5 * (sub.max() - loc)) & (np.hypot(xs, ys) <= 0.9 * size)
        w = (sub - loc)[m]
        if w.sum() > 0:
            out.append((px + float((xs[m] * w).sum() / w.sum()), py + float((ys[m] * w).sum() / w.sum()), v))

    whole = resp.copy() if n_max is None else None
    taken = []
    for _ in range(N_STRONG if n_max is None else n_max):
        py, px = np.unravel_index(np.argmax(resp), resp.shape)
        v = float(resp[py, px])
        if v < min_resp:
            return out
        centre(py, px, v)
        taken.append((py, px))
        resp[max(py - 2 * r, 0):py + 2 * r + 1, max(px - 2 * r, 0):px + 2 * r + 1] = 0
    if n_max is None:
        # the rest on the response as it was: each the peak of its own size, not of the 4r+1 square the
        # strongest clear about them -- on a sea of specks one is within 2r of nearly everything
        peak = (whole >= min_resp) & (whole == ndimage.maximum_filter(whole, size=2 * r + 1, mode="constant"))
        for py, px in taken:
            peak[max(py - r, 0):py + r + 1, max(px - r, 0):px + r + 1] = False
        py, px = np.nonzero(peak)
        for i in np.argsort(-whole[py, px], kind="stable"):
            centre(int(py[i]), int(px[i]), float(whole[py[i], px[i]]))
    return out


def spot_fwhm(g, x, y, dark=False, r=7):
    """The width at half its peak (px) of an isotropic Gaussian on a level, fitted to the
    (2r+1)-px patch round (x, y), with its peak over the fit's scatter. None off the frame
    or where nothing rises above the level. `at_edge` is a width held by the patch's own
    size: the thing is at least that wide, and the patch should be larger. `clipped`: its
    core reaches black or white (CLIP), where the width follows the brightness -- PR135's
    hot points are clipped at 255 over 4-6 px, and a brighter one only looks wider."""
    from scipy.optimize import least_squares
    H, W = g.shape
    xi, yi = int(round(x)), int(round(y))
    if xi < r or yi < r or xi >= W - r or yi >= H - r:
        return None
    p = g[yi - r:yi + r + 1, xi - r:xi + r + 1].astype(float)
    p = -p if dark else p
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    c0 = float(np.median(p))
    a0 = float(p[r - 1:r + 2, r - 1:r + 2].max() - c0)
    if a0 <= 0:
        return None
    top = r / 2.0
    res = lambda q: (q[0] * np.exp(-((xx - q[1]) ** 2 + (yy - q[2]) ** 2) / (2 * q[3] ** 2)) + q[4] - p).ravel()
    fit = least_squares(res, [a0, x - xi, y - yi, 1.2, c0],
                        bounds=([0, -2, -2, 0.3, -np.inf], [np.inf, 2, 2, top, np.inf]))
    a, dx, dy, sg, _ = fit.x
    core = g[yi - 1:yi + 2, xi - 1:xi + 2]
    return dict(fwhm=float(2.3548 * sg), snr=float(a / max(np.std(fit.fun), 1e-9)),
                x=xi + float(dx), y=yi + float(dy), at_edge=bool(sg > 0.98 * top),
                clipped=bool(core.min() <= CLIP[0] if dark else core.max() >= CLIP[1]))


BLUR_FRAMES = 12      # of the track's frames, spread over it, that the blur and the object are measured on
BLUR_SNR = 8.0        # a spot's peak over the fit's scatter, to count
BLUR_SPOTS = 8        # fewer spots than this, and the blur is not measured
RESOLVED = 1.5        # the object's width over the blur's, above which it shows its own shape
CLIP = (5.0, 250.0)   # grey levels at or past which a spot's core is clipped
# A point clipped at level L with its peak at A is sqrt(ln(2A/L) / ln 2) times as wide at half its
# (clipped) peak as the blur: 4 times would need A = 30,000 L, past any sensor's range. A clipped
# object wider than that is resolved (PR055's dark disc, 8.5 times); narrower, it cannot be told
# from a point (PR135's hot points, ~2.8 times).
CLIPPED_RESOLVED = 4.0
FIXED = 0.5           # a spot in the same place (1 px) on this share of the frames is on the sensor


def point_blur(clip, track, masks, rows=None, dark=False, avoid=20.0, frames=BLUR_FRAMES):
    """How wide a point is drawn on this clip, and how wide the object is, both as the width at half
    the peak of a Gaussian fitted to it -- the one question behind a speed in body lengths: is the
    size the object's, or the blur's?

    The blur is read from the clip's sharpest compact spots, bright and dark, away from the object
    (`avoid` px) on `frames` of the track's frames: a point is drawn as the blur and nothing is
    drawn narrower, so the sharpest quarter of them (their 25th percentile) is the blur, and a
    few narrower specks of noise do not set it. The detector's own size cannot answer this: its
    smallest scale reads everything under ~7 px as 7.4 (PR135's group of hot points, "7.4 px").
    Fewer than BLUR_SPOTS spots, and the blur is not measured: a clip of sea or sky may have
    no point in it. The object is resolved when its width is over RESOLVED times the blur's.

    Two kinds of spot are not points of the scene, and are left out (PR135, where both were
    taken and a group of hot points 5.4 px wide read as resolved against a 1.7 px "blur"):
    a spot clipped at white or black, whose width follows its brightness; and a spot in the
    same place on the screen on FIXED of the frames, a defect of the sensor, drawn without
    the optics (PR135 has eleven). An object clipped on most frames is resolved only if it
    is over CLIPPED_RESOLVED times the blur, which clipping cannot make of a point; else
    `resolved` is None, and `object_clipped` says why."""
    ns = sorted(n for n in track if getattr(clip, "n0", n) <= n <= getattr(clip, "n1", n))
    if len(ns) > frames:
        ns = [ns[i] for i in np.unique(np.linspace(0, len(ns) - 1, frames).round().astype(int))]
    spots, obj, clipped = [], [], 0
    for n in ns:
        rgb = clip.rgb(n)
        g = rgb.mean(2)
        bad = frame_mask(rgb, masks, rows, n, grow=6)
        ox, oy = track[n]
        for pol in (False, True):
            for x, y, _ in source_candidates(g, bad, 5.0, pol):
                if np.hypot(x - ox, y - oy) < avoid:
                    continue
                f = spot_fwhm(g, x, y, pol)
                if f and f["snr"] >= BLUR_SNR and not f["at_edge"] and not f["clipped"]:
                    spots.append((n, f["x"], f["y"], f["fwhm"]))
        # a patch sized from the object's own scale (propose.thing_at): one too small to hold a
        # flat-topped disc sees only its top, and fits a speck of noise on it
        from .propose import thing_at
        _, _, across, _ = thing_at(g, ox, oy, -1 if dark else 1)
        f = spot_fwhm(g, ox, oy, dark, max(7, int(round(1.2 * across))))
        if f and f["snr"] >= BLUR_SNR:
            clipped += f["clipped"]
            obj.append(f["fwhm"])
    at = np.array([(x, y) for _, x, y, _ in spots]).reshape(-1, 2)
    frames_of = np.array([n for n, _, _, _ in spots])
    fixed = np.array([len(set(frames_of[np.hypot(*(at - p).T) <= 1.0])) >= max(2, FIXED * len(ns)) for p in at], bool)
    widths = [w for (_, _, _, w), f in zip(spots, fixed) if not f]
    blur = float(np.percentile(widths, 25)) if len(widths) >= BLUR_SPOTS else None
    size = float(np.median(obj)) if obj else None
    if blur is None or size is None:
        resolved = None
    elif 2 * clipped <= len(obj):
        resolved = bool(size > RESOLVED * blur)
    else:                                  # clipped: only a width far past what clipping can make of a point
        resolved = True if size > CLIPPED_RESOLVED * blur else None
    return dict(frames=len(ns), spots=len(widths), on_the_sensor=int(fixed.sum()), blur_fwhm_px=blur,
                object_fits=len(obj), object_fwhm_px=size, object_clipped=clipped, resolved=resolved)


def frame_candidates(clip, n, masks, rows=None, size=9.0, dark=False, min_resp=35.0, n_max=N_STRONG):
    """The detector on frame n as every automatic track runs it: this frame's
    mask grown a little further than for registration, and a border of 1.5
    sizes closed, where the filter's annulus hangs off the frame.

    One definition, because `layers --auto-track`, `integrity --auto-track` and
    `mcdonald mark`'s link all have to mean the same thing by "a candidate".

    min_resp is the one thing they do not share. A blind track starts on the
    strongest candidate in the frame, so it needs the default 35 to keep noise
    out. A track seeded from a hand mark chooses by position, inside a gate,
    and can afford to listen for weak ones -- and has to: PR113's object
    responds at 44 on its first frame and 32 on its last."""
    rgb = clip.rgb(n)
    bad = frame_mask(rgb, masks, rows, n, grow=6)
    m = int(1.5 * size)
    bad[:m, :] = bad[-m:, :] = True
    bad[:, :m] = bad[:, -m:] = True
    return source_candidates(rgb.mean(2), bad, size, dark, n_max=n_max, min_resp=min_resp)


def link_track(cands, n0, n1, seed=None, velocity=None, max_gap=40, gate=(25.0, 12.0)):
    """Nearest candidate to a constant-velocity prediction.

    seed = (n, x, y) starts the track at a known position; without one it
    starts on the strongest candidate, so CHECK WHAT IT LOCKED ONTO
    (track_strip, or tracksheet) before building anything on it.

    velocity = (vx, vy) in px/frame primes the prediction. **A fast object
    cannot be acquired without it.** The gate is `gate[0] + gate[1] * gap` px
    about the prediction, 37 px at gap 1 by default; an object moving faster
    than that per frame is outside its own gate on the very first step and the
    track dies at one point. PR113 moves 142 px/frame — the gate rejects it
    from a standing start, and with velocity=(-103, 98) it links cleanly.

    Widen `gate` instead only if you do not know the velocity: a wide gate on
    a cluttered frame links whatever is nearest, which is how a tracker ends
    up on terrain."""
    trk, last = {}, None
    vel = np.zeros(2) if velocity is None else np.asarray(velocity, float)
    order = list(range(n0, n1 + 1))
    if seed:
        last = tuple(seed)
        order = [n for n in order if n >= seed[0]]
    for n in order:
        cs = cands.get(n, [])
        if not cs:
            continue
        if last is not None and n - last[0] > max_gap:
            last = None
        if last is None:
            c = max(cs, key=lambda q: q[2])
        else:
            gap = max(n - last[0], 1)
            pred = np.array(last[1:3]) + vel * (n - last[0])
            d = [np.hypot(c[0] - pred[0], c[1] - pred[1]) for c in cs]
            c = cs[int(np.argmin(d))]
            if min(d) > gate[0] + gate[1] * gap:
                continue
            if n > last[0]:
                nv = (np.array(c[:2]) - np.array(last[1:3])) / gap
                vel = 0.5 * vel + 0.5 * nv if gap <= 3 else nv
        trk[n] = (c[0], c[1])
        last = (n, c[0], c[1])
    return trk


def velocity_from_marks(marks):
    """(vx, vy) px/frame from two or more hand marks {frame: (x, y)}.

    The cheapest way to prime the linker: two clicks on a fast object give it
    the velocity it cannot otherwise acquire."""
    ns = sorted(marks)
    if len(ns) < 2:
        return None
    a, b = ns[0], ns[-1]
    if b == a:
        return None
    return ((marks[b][0] - marks[a][0]) / (b - a), (marks[b][1] - marks[a][1]) / (b - a))


def detect_scale_sweep(g, bad, sizes=(5, 9, 15, 21, 31, 45), dark=False, at=None,
                       n_max=25, min_resp=5.0):
    """Run the compact-source detector at several scales.

    The matched filter is tuned to one size, and an object much larger than it
    is missed entirely, not merely down-weighted: PR113's 25 px object sits
    71 px from the nearest candidate at the 9 px default and 1.9 px away at
    21 px. When the object's extent is unknown, sweep before concluding there
    is nothing there.

    With `at` = (x, y), reports how close each scale gets to that position,
    which is how to choose the scale from one hand mark."""
    out = {}
    for s in sizes:
        c = source_candidates(g, bad, size=float(s), dark=dark, n_max=n_max, min_resp=min_resp)
        row = {"n": len(c), "candidates": c}
        if at is not None and c:
            d = [np.hypot(q[0] - at[0], q[1] - at[1]) for q in c]
            j = int(np.argmin(d))
            row["nearest_px"] = float(d[j])
            row["nearest"] = c[j]
            row["resp_rank"] = int(sorted(c, key=lambda q: -q[2]).index(c[j])) + 1
        out[s] = row
    return out


def best_scale(g, bad, at, sizes=(5, 9, 15, 21, 31, 45), dark=False, tol=6.0, gain=0.5):
    """The detector scale whose candidate sits closest to the object at `at`.

    Not the smallest that comes within tol. A filter much smaller than the
    object fires on its rim, and the rim of a small object is within tol of a
    mark on its centre; a track made at that scale rides the rim, a radius off.
    So it climbs from the first scale within tol, on to the next while that
    brings the candidate at least `gain` px closer. (`autolink.pick_detector`
    is the same rule over several marks and both polarities.)"""
    sw = detect_scale_sweep(g, bad, sizes, dark, at)
    best = None
    for s in sizes:
        d = sw[s].get("nearest_px", 1e9)
        if d <= tol and (best is None or d < sw[best]["nearest_px"] - gain):
            best = s
        elif best is not None:
            break
    return best, sw


def track_strip(clip, trk, out, k=16, box=24, zoom=5):
    """Crops along a track, for the eye: is this the object, all the way?"""
    ns = [sorted(trk)[i] for i in np.unique(np.linspace(0, len(trk) - 1, k).astype(int))]
    tiles = []
    for n in ns:
        x, y = (int(round(v)) for v in trk[n])
        g = np.pad(clip.grey(n), box, mode="edge")[y:y + 2 * box, x:x + 2 * box]
        lo, hi = np.percentile(g, [1, 100])
        tiles.append(Image.fromarray(((g - lo) / max(hi - lo, 1) * 255).clip(0, 255).astype(np.uint8))
                     .resize((2 * box * zoom, 2 * box * zoom), Image.NEAREST))
    sheet = Image.new("L", (len(tiles) * 2 * box * zoom, 2 * box * zoom))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, (i * 2 * box * zoom, 0))
    sheet.save(out)
    return ns


def interp_track(trk):
    tn = np.array(sorted(trk))
    tx, ty = np.array([trk[i][0] for i in tn]), np.array([trk[i][1] for i in tn])
    return lambda n: (float(np.interp(n, tn, tx)), float(np.interp(n, tn, ty)))


# ---- the sensor's static pattern --------------------------------------------------------
def _pattern_chunk(job):
    video, workdir, n0, n1, ns, groups, masks, trk, keep_out, rows = job
    clip = Clip(video, workdir, n0, n1)
    acc = np.zeros((8, clip.H, clip.W), np.float32)           # (sum, count) for each of four groups
    yy, xx = np.mgrid[:clip.H, :clip.W]
    pos = interp_track(trk) if trk else None
    for n, k in zip(ns, groups):
        rgb = clip.rgb(n)
        g = rgb.mean(2)
        ok = ~frame_mask(rgb, masks, rows, n, grow=5) & (g > 8) & (g < 247)
        if pos:
            cx, cy = pos(n)
            ok &= (xx - cx) ** 2 + (yy - cy) ** 2 > keep_out ** 2
        hp = g - ndimage.gaussian_filter(g, 2.0)
        acc[2 * k][ok] += hp[ok]
        acc[2 * k + 1][ok] += 1
    return acc


def static_pattern(clip, ns, masks, trk=None, keep_out=40, rows=None, procs=10, n_max=400, block=25,
                   progress=None, stop=None):
    """Temporal mean of high-passed frames: what stays put on the detector
    while the scene sweeps across it. Pixels within keep_out px of the tracked
    object are never used (it would print itself into the estimate).

    Frames are split two ways. Alternate blocks of `block` frames (A, B) give a
    split-half test of where a static pattern is measurable: odd/even frames
    would not do, because a striated scene moving along its striations leaks
    into both halves alike. The first and second half of the span (H1, H2)
    give a pattern estimated far in time from any given frame.
    Returns {"A","B","H1","H2": mean or NaN, "half_of": {frame: 1|2}, "frames"}."""
    ns = list(ns)
    if len(ns) > n_max:
        ns = [ns[i] for i in np.linspace(0, len(ns) - 1, n_max).astype(int)]
    grp = [2 * int(i >= len(ns) / 2) + (i // block) % 2 for i in range(len(ns))]     # 0 H1A, 1 H1B, 2 H2A, 3 H2B
    slim = {k: v for k, v in masks.items() if k in ("blocks", "graphics", "colour")}
    jobs = [(clip.video, clip.dir, clip.n0, clip.n1, ns[i::procs], grp[i::procs], slim, trk, keep_out, rows) for i in range(procs)]
    acc = np.sum(pooled(procs, _pattern_chunk, [j for j in jobs if j[4]], progress=progress, stop=stop,
                        what="integrity: looking for a pattern that stays still"), 0)
    mean = lambda ks: np.where(sum(acc[2 * k + 1] for k in ks) >= 30,
                               sum(acc[2 * k] for k in ks) / np.maximum(sum(acc[2 * k + 1] for k in ks), 1), np.nan)
    return {"A": mean((0, 2)), "B": mean((1, 3)), "H1": mean((0, 1)), "H2": mean((2, 3)),
            "half_of": {n: 1 + (k >= 2) for n, k in zip(ns, grp)}, "frames": ns}


def pattern_power(even, odd, box=41):
    """Local split-half covariance [DN^2]: the static pattern's own variance."""
    m = np.isfinite(even) & np.isfinite(odd)
    a, b = np.where(m, even, 0), np.where(m, odd, 0)
    cnt = np.maximum(ndimage.uniform_filter(m.astype(float), box), 1e-6)
    cov = ndimage.uniform_filter(a * b, box) / cnt - (ndimage.uniform_filter(a, box) / cnt) * (ndimage.uniform_filter(b, box) / cnt)
    return np.where(ndimage.uniform_filter(m.astype(float), box) > 0.6, cov, np.nan)
