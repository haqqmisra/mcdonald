"""Is something tethered to the object -- a line or a payload that moves with it -- and does it swing?

A sounding balloon carries its radiosonde 25-55 m below it on a line; a hobby balloon a
few grams a metre or two below. A pilot's "strings hanging off" (the Lake Huron object
of 2023-02-12, PR071) is the same thing. Nothing else in the sky is a body with a point
hanging under it, and a hanging point is a pendulum: its period is set by gravity and
the line, T = 2 pi sqrt(L/g), so T read off the video in seconds gives L in metres with
no range and no field of view, and the line's length in pixels then scales the whole
image. That is the balloon analogue of PR135's wingbeat.

The question is asked in two parts (`stack_both` with `candidates` and `support`, then
`follow_many` and `swing`), reading every frame three times in all:

1. **Does anything move with the object?** Every frame, overlay masked, is shifted so
   the tracked position lands at the centre and the frames are averaged: a thing tied
   to the object adds up at its offset; the scene and the overlay smear by however far
   the object moved on the screen. A candidate is a compact feature of that stack, `Z_MIN`
   times its noise, between `r_min` and `r_max` object sizes of the centre. Three things
   then say whether it is the object's:
   - *the control*: the same frames stacked on the track run backwards in time have the
     same set of positions and the wrong one each frame, so a thing tied to the object
     smears there while anything that only looked sharp because the object hardly moved
     stays sharp (PR055's edge peaks reappeared there identically). `z_control` at most
     `CONTROL` of `z`. Both stacks are made in the one pass.
   - *single frames*: a thing tied to the object is there at its offset on single frames,
     `FRAME_Z` times the frame's noise (by MAD over a wide crop, so the overlay's lines do
     not set it), on `SUPPORT` of them, and at the same place to within `JITTER_PX`
     across its own spread (along a line the darkest point wanders, and that is not a
     jitter). Cloud texture is dark *somewhere* in a patch on many frames, but spread
     over the patch (PR055: 11-14 px); PR071's string sits at 4.
   - *with the object or with the scene*: the candidate followed frame by frame (below)
     moves with the object rather than with the background's own shift
     (`groups.with_the_group`), when the object moves at least `STILL` px against the
     scene. The one test that catches a piece of cloud drifting steadily past.
   A payload that swings more than a patch is at its mean offset on few single frames:
   the strongest features the control does not show are followed anyway, and one that
   moves smoothly (`SMOOTH`) and with the object is kept.
   **The overlay's strokes are masked first** (`stroke_mask`): thin bright lines --
   reticle arms, a tracking gate's box, brackets -- are found by a morphological
   opening (what survives a line-shaped opening along either axis but not a square
   one) and left out of every stack and every test, because a tracking gate *is* tied
   to the object, by the tracker, late, and its edges passed every test above on PR071
   until they were masked. A thin *bright* line on the object would be masked with
   them (`--no-stroke-mask`); PR071's string is dark and is not. When the object moves
   less than `STILL` px on the screen, nothing can be told apart and the stage says so.
2. **Does it swing?** The companion -- the one kept, or an offset given with --seed --
   is followed: in a gate about where it was last, the compact feature of its polarity.
   The separation vector from the object gives the swing angle (0 = straight down the
   image, + = to the right), which needs no scale and survives any camera motion short
   of a roll. Repeated frames (the hold-and-jump cadence sensor clips have) are left out
   of the series. A Lomb-Scargle periodogram starts it; the estimator is a sinusoid with
   a drift fitted to the angle, kept when it is clean (residual under half the
   amplitude) -- a periodogram's peak on a window of a few cycles slides up to whatever
   cap the window sets, and a peak at the longest period asked is never a period. The
   period's uncertainty is a block bootstrap of the fit's residuals (`BOOT` resamples,
   blocks of `BLOCK_S`), and `line_length_m` = g T^2 / 4 pi^2 carries it doubled. A
   swing is **claimed** from `CLAIM_CYCLES` cycles of the window and **tentative** from
   `TENTATIVE_CYCLES`: the one calibration with ground truth (WA9ONY-5, a 13 g pico
   payload "a little over one metre" below the balloon, 2021-07-13) is tentative -- 1.7
   cycles, 2.59 s, 1.66 m, which is the line plus the balloon's radius and the payload's
   own offset, the pivot of a balloon's pendulum being the balloon's centre, not its neck.

What it cannot do: a payload too faint for single frames that swings more than its own
size evades the stack (it smears by its swing) and the follower both; that needs a
search over the pendulum's own motion, not done here. A line held at a steady angle by
drag (PR071: no swing in 8 s) gives no length. And the companion's pixel offset is in
pixels for the reasons every separation is; only the period is a metre.
"""
import csv
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from scipy import ndimage
from scipy.ndimage import gaussian_filter

from . import forensics as vf
from .progress import PROCS_HELP, WINDOWS_AS_BEFORE, counted, to_stderr, workers
from .report import Found, emit, inputs_of, said_to_stderr

R_MIN = 1.2          # x the object's size: the first ring a companion is looked for in (inside is the object)
R_MAX = 40.0         # x the object's size: a radiosonde hangs 10-35 diameters below a sounding balloon
NOISE_SIZES = 8.0    # the stack's noise is measured out to this many object sizes (see `candidates`)
TOP = 200            # candidates the control does not show that get their single-frame support ...
FOLLOW = 12          # ... and how many of those, by support then strength, are followed
COVERED = 0.6        # a candidate's pixel was covered by the frames on this share of them at least: a tracking gate's
                     # strokes, masked, sweep the object's neighbourhood by the tracker's lag, and 0.95 here dropped
                     # PR071's string out of the search
COVERED_EXTENT = 0.95   # the object's own footprint is traced only through pixels covered on nearly every frame
NEAR = 2.5           # x the object's size: nearer than this, a feature single frames cannot confirm is the object's own
                     # halo or glint, however strong on the stack (WA9ONY's balloon: a glint at 1.2 sizes, 30 x noise)
Z_MIN = 5.0          # a candidate is at least this many times the stack's noise (DoG units)
CONTROL = 0.6        # ... and the reversed-track control shows at most this share of it at the same place
STILL = 20.0         # px moved on the screen below which nothing can be told from the overlay or the scene
SIGMA = 1.2          # DoG inner scale, px: a line or a point a few px across
SIGMA_OUT = 6.0      # DoG outer scale, px
SUPPORT = 0.3        # a companion is seen on at least this share of single frames at its offset ...
FRAME_Z = 2.5        # ... at this many times the frame's own noise there
STRONG = 2.0         # x Z_MIN: a stack feature this strong is kept even when single frames cannot show it
JITTER_PX = 6.0      # px, across its own spread: a thing tied to the object is at the same place on every frame to
                     # within this (PR071's string: 4; WA9ONY's payload sweeps an arc, 4 across it); texture that happens
                     # to be dark somewhere in the patch is spread over it (PR055's clouds: 11-14)
SMOOTH = 0.08        # x its distance: a followed companion moves at most this much a frame (a pendulum's payload,
                     # 2.5 s and 14 deg on 170 px, 2 %); texture caught in the gate jumps by the gate
GATE = 0.25          # per frame, the companion may move this share of its separation from where it was predicted
MIN_SWING_FRAMES = 20
CLAIM_CYCLES = 2.0       # a period is claimed from this many cycles of the window ...
TENTATIVE_CYCLES = 1.5   # ... and reported as tentative from this many: a clean sinusoid over 1.5 fixes it to ~10%
SWING_POWER = 0.3    # Lomb-Scargle normalised power below which the angle is called steady
BOOT, BLOCK_S = 200, 0.3   # bootstrap resamples of the fit's residuals, in blocks this long
STROKE_LEN = 21      # px: a bright line at least this long is the overlay's
STROKE_DN = 20.0     # ... standing this far above what a 9x9 opening leaves (PR071's reticle arm: 25-45)
STROKE_MIN = 180.0   # ... and this bright in absolute terms (overlays are drawn near white)
STROKE_REGION = 600  # px about the object the strokes are looked for in: a reticle or a gate is here; brackets at the
                     # frame's corners are static, and the static masks have them
G = 9.80665


# ---- frames --------------------------------------------------------------------------
def stroke_mask(g, length=STROKE_LEN, above=STROKE_DN, bright=STROKE_MIN):
    """Thin bright strokes: what survives a grey opening with a line along x or y of
    `length` but not with a 9x9 square, standing `above` DN over the square's remainder,
    and at least `bright` itself. Dilated 2 px. The overlay's reticle, gate and brackets;
    not a bright blob (it survives the square) and not a dark line."""
    gg = np.where(np.isfinite(g), g, 0.0)
    sq = ndimage.grey_opening(gg, size=(9, 9))
    lines = np.maximum(ndimage.grey_opening(gg, size=(1, length)), ndimage.grey_opening(gg, size=(length, 1)))
    m = ((lines - sq) >= above) & (gg >= bright)
    return ndimage.binary_dilation(m, iterations=2) if m.any() else m


CACHE_BYTES = 600 * 1024 ** 2   # frames are kept between passes as uint8 while they fit in this
# On Windows the frames are read one after another, as until 0.2.16 (`progress.WINDOWS_AS_BEFORE`).
SERIAL_HERE = WINDOWS_AS_BEFORE


def _read(clip, masks, rows, track, radius, strokes, n):
    """Frame n as the stage reads it: (its grey as the clip gives it, what of it is not scene -- the static
    masks, its own coloured symbology and, within `radius` of the object, the overlay's strokes)."""
    rgb = clip.rgb(n)
    grey = vf.grey_of(rgb)
    bad = vf.frame_mask(rgb, masks, rows, n, grow=2)
    if strokes and n in track:
        g = grey.astype(np.float64)
        ox, oy = track[n]
        x0, y0 = int(max(ox - radius, 0)), int(max(oy - radius, 0))
        x1, y1 = int(min(ox + radius + 1, clip.W)), int(min(oy + radius + 1, clip.H))
        if x1 > x0 and y1 > y0:
            bad = bad.copy()
            bad[y0:y1, x0:x1] |= stroke_mask(g[y0:y1, x0:x1])
    return grey, bad


class Frames:
    """The clip's frames as the stage reads them: grey, with the static masks and the
    overlay's strokes (within `radius` of the track) as `bad`. One place, so every pass
    sees the same pixels; and a cache, uint8 and packed bits, while the window fits in
    CACHE_BYTES, so the second pass decodes nothing. A pass takes them in order from
    `each`, which reads the frames not kept ahead of it, on as many threads of this
    process as `progress.workers` allows for `procs` (0: none, one after another).
    Threads, not a pool's processes: a frame is 8.6 MB at 1080p, and sent back through a
    pipe it took four times what reading it does (2026-10-10, measured on PR144: 130
    frames 54 s in one process, 220 s on four workers)."""

    def __init__(self, clip, masks, track, radius, rows=None, strokes=True, cache=True, procs=None):
        self.clip, self.masks, self.track, self.radius, self.rows, self.strokes = clip, masks, track, int(radius), rows, strokes
        self.procs = procs
        n = sum(1 for k in track if clip.n0 <= k <= clip.n1)
        self.cache = {} if cache and n * clip.W * clip.H * 1.125 <= CACHE_BYTES else None

    def _keep(self, n, g, bad):
        if self.cache is not None:
            self.cache[n] = (np.clip(np.rint(g), 0, 255).astype(np.uint8), np.packbits(bad))
        return g, bad

    def _read(self, n):
        return _read(self.clip, self.masks, self.rows, self.track, self.radius, self.strokes, n)

    def __call__(self, n):
        if self.cache is not None and n in self.cache:
            g8, packed = self.cache[n]
            return g8.astype(np.float64), np.unpackbits(packed, count=g8.size).reshape(g8.shape).astype(bool)
        grey, bad = self._read(n)
        return self._keep(n, grey.astype(np.float64), bad)

    def each(self, ns, progress=None, stop=None, what=""):
        """(n, grey, bad) for each frame of `ns`, in order, exactly as `self(n)` gives them, saying how far
        the pass has got and asking `stop` after each (`progress.counted`)."""
        ns = list(ns)
        todo = [n for n in ns if self.cache is None or n not in self.cache]
        size = workers(self.procs, self.clip.W * self.clip.H) if todo and not SERIAL_HERE else 0
        if not size:
            for n in counted(ns, progress, stop, what):
                yield (n, *self(n))
            return
        fresh, out, it = set(todo), deque(), iter(todo)
        ex = ThreadPoolExecutor(size)

        def more():
            n = next(it, None)
            if n is not None:
                out.append(ex.submit(self._read, n))
        try:
            for _ in range(2 * size):
                more()
            for n in counted(ns, progress, stop, what):
                if n in fresh:
                    grey, bad = out.popleft().result()
                    more()
                    yield (n, *self._keep(n, grey.astype(np.float64), bad))
                else:
                    yield (n, *self(n))
        finally:
            ex.shutdown(wait=False, cancel_futures=True)


def wide_noise(g, bad, ox, oy, half=256):
    """The frame's own noise about the object: the DoG over a wide crop, by MAD, so the
    overlay's lines and the object itself (a small share of it) do not set it."""
    X0, Y0 = int(max(ox - half, 0)), int(max(oy - half, 0))
    X1, Y1 = int(min(ox + half, g.shape[1])), int(min(oy + half, g.shape[0]))
    wide = g[Y0:Y1, X0:X1].copy()
    wide[bad[Y0:Y1, X0:X1]] = np.nan
    k = 3 * int(SIGMA_OUT)
    dw = _dog(wide)[k:-k, k:-k]
    dw = dw[np.isfinite(dw)]
    return float(1.4826 * np.median(np.abs(dw - np.median(dw)))) if dw.size else 0.0


def object_extent(m, cnt, R, size, cap=200):
    """How far the object itself reaches in the stack, px from the centre: the connected area
    about the centre, through pixels the frames covered on nearly every frame, that stands
    out from the outer ring by more than 4 x the ring's scatter (or 5 DN). A crumpled
    balloon's glints and facets are part of it, well outside the half-max width
    `object_size` gives (WA9ONY: 44 px wide, glints at 59 px out); a tracking gate's box,
    masked as a stroke on the frames it was seen on, is not covered and does not join."""
    sub = m[R - cap:R + cap + 1, R - cap:R + cap + 1]
    cov = cnt[R - cap:R + cap + 1, R - cap:R + cap + 1] >= COVERED_EXTENT * cnt.max()
    ok = np.isfinite(sub) & cov
    if not ok[cap, cap] or ok.sum() < 100:
        return 0.0
    yy, xx = np.mgrid[-cap:cap + 1, -cap:cap + 1]
    ring = ok & (np.hypot(xx, yy) >= 0.6 * cap)
    if ring.sum() < 100:
        ring = ok
    bg = float(np.median(sub[ring]))
    sig = float(1.4826 * np.median(np.abs(sub[ring] - bg)))
    hot = ok & (np.abs(sub - bg) > max(5.0, 4 * sig))
    hot = ndimage.binary_closing(hot, iterations=2) & ok
    lab, _ = ndimage.label(hot)
    k = lab[cap, cap]
    if k == 0:
        return 0.0
    ys, xs = np.nonzero(lab == k)
    return float(np.hypot(xs - cap, ys - cap).max())


def _dog(m):
    mm = np.where(np.isfinite(m), m, np.nanmedian(m) if np.isfinite(m).any() else 0.0)
    return gaussian_filter(mm, SIGMA) - gaussian_filter(mm, SIGMA_OUT)


# ---- pass 1: the stacks ------------------------------------------------------------------
def stack_both(clip, track, frames, radius=None, progress=None, stop=None):
    """(object stack, count, reversed-track stack, repeated frames): the frames centred on
    the track, pixel (R, R) the object, and the same frames placed by the position of the
    track's mirror frame -- one pass. A frame whose crop about the object differs from
    its predecessor's by far less than the local norm is a repeat (the hold-and-jump
    cadence), listed for `swing` to leave out."""
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    R = int(radius or max(clip.W, clip.H))
    S = 2 * R + 1
    acc, cnt = np.zeros((S, S), np.float64), np.zeros((S, S), np.float64)
    accr, cntr = np.zeros((S, S), np.float64), np.zeros((S, S), np.float64)
    pos = [track[n] for n in ns]
    repeats, diffs, last = [], [], None
    for i, (n, g, bad) in enumerate(frames.each(ns, progress, stop, "Stack")):
        w = (~bad).astype(np.float64)
        gw = g * w
        for a, c, (x, y) in ((acc, cnt, pos[i]), (accr, cntr, pos[len(ns) - 1 - i])):
            ox, oy = int(round(R - x)), int(round(R - y))
            x0, y0 = max(ox, 0), max(oy, 0)
            x1, y1 = min(ox + clip.W, S), min(oy + clip.H, S)
            if x1 <= x0 or y1 <= y0:
                continue
            a[y0:y1, x0:x1] += gw[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
            c[y0:y1, x0:x1] += w[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        # the cadence: the crop about the object against the last frame's
        x, y = pos[i]
        X0, Y0 = int(max(x - 128, 0)), int(max(y - 128, 0))
        crop = g[Y0:Y0 + 256, X0:X0 + 256]
        if last is not None and last[1].shape == crop.shape and last[2] == (X0, Y0):
            d = float(np.abs(crop - last[1]).mean())
            loc = [v for v in diffs[-10:] if np.isfinite(v)]
            if loc and d < 0.2 * np.median(loc) and d < 0.35:
                repeats.append(n)
            diffs.append(d)
        elif last is not None:
            diffs.append(np.nan)
        last = (n, crop, (X0, Y0))
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)
        mc = np.where(cntr > 0, accr / np.maximum(cntr, 1), np.nan)
    return m, cnt, mc, repeats


def object_size(m, cnt, R, cap=200):
    """The object's own size in the stack, px: the width at half its central contrast,
    measured along four directions and averaged. None when there is no central contrast."""
    c = m[R, R]
    ring = m[R - cap:R + cap + 1, R - cap:R + cap + 1]
    bg = np.nanmedian(ring)
    if not np.isfinite(c) or not np.isfinite(bg) or abs(c - bg) < 3:
        return None
    half = bg + 0.5 * (c - bg)
    widths = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for k in range(1, cap):
            v = m[R + k * dy, R + k * dx]
            if not np.isfinite(v) or (v - half) * np.sign(c - bg) < 0:
                widths.append(k)
                break
        else:
            widths.append(cap)
    return 2.0 * float(np.mean(widths))


def _ring_noise(dog, rr, valid, floor, bins=20):
    """The DoG's scatter by MAD in log-spaced rings of the valid area, interpolated over the
    radius; `floor` where a ring has too few pixels."""
    r = rr[valid]
    edges = np.geomspace(max(r.min(), 1.0), r.max() + 1e-6, bins + 1)
    mids, mads = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        v = dog[valid & (rr >= a) & (rr < b)]
        if v.size >= 200:
            mids.append(float(np.sqrt(a * b)))
            mads.append(float(np.std(v)))
    if len(mids) < 2:
        return np.full(dog.shape, floor)
    return np.interp(rr, mids, mads, left=mads[0], right=mads[-1])


def candidates(m, cnt, mc, size, R, r_min=R_MIN, r_max=R_MAX, top=TOP, z_min=Z_MIN, control=CONTROL):
    """Compact features of the object stack `m` between r_min and r_max object sizes of the
    centre, scored against the stack's own noise and against the reversed-track stack `mc`
    at the same place. [{...}], strongest first, `top` at most; the verdict `co_moving` is
    filled in by `support` once the frames have been looked at."""
    dog, dogc = _dog(m), _dog(mc)
    S = m.shape[0]
    yy, xx = np.mgrid[0:S, 0:S]
    rr = np.hypot(xx - R, yy - R)
    # pixels the frames covered on (nearly) every frame: where a mask's edge or the frame's own edge
    # smeared through, the mean has a step the DoG answers to, and that is not a feature
    covered = ndimage.binary_erosion(cnt >= max(3, COVERED * cnt.max()), iterations=int(3 * SIGMA_OUT))
    valid = covered & (rr >= r_min * size) & (rr <= r_max * size)
    if valid.sum() < 100:
        return [], float("nan")
    # the noise, by MAD, on the inner annulus: where a companion would be, and where the object's own
    # neighbourhood sets the floor. Far out, the stacked frame's edges and the overlay's bars smear into
    # structure that would set one global noise for the whole annulus (PR071: 1.7 DN over 40 sizes
    # against 0.4 near the object); and a ring far out that is mostly flat masked area has none
    inner = valid & (rr <= min(r_max, NOISE_SIZES) * size)
    v = dog[inner if inner.sum() >= 100 else valid]
    sig = max(float(np.std(v)), 1e-3)                   # std, not MAD: on a flat sky the MAD is 0.1 DN and admits everything
    # and never less than that farther out, where the scatter is its own ring's: the frame's edges and the
    # display's fields smear into structure that is large against the inner noise and ordinary against their own
    sig_r = np.maximum(_ring_noise(dog, rr, valid, sig), sig)
    sigc = sig_r
    z = np.where(valid, np.abs(dog) / sig_r, 0.0)
    # the strongest peaks, but those the control does not show first: the frame's own edges and the overlay's
    # bars are sharp on both stacks and can be the forty strongest things in a stack (PR071, forty object sizes
    # out), and a line on the object at twenty times the noise would never be looked at behind them
    out, on_control = [], []
    order = np.argsort(z.ravel())[::-1][:40000]
    for i in order:
        y, x = divmod(int(i), S)
        if z[y, x] < z_min or (len(out) >= top and len(on_control) >= 5):
            break
        if any(np.hypot(x - c["_x"], y - c["_y"]) < 3 * SIGMA_OUT for c in out + on_control):
            continue
        zc = float(abs(dogc[y, x]) / sigc[y, x])
        dx, dy = x - R, y - R
        c = dict(_x=x, _y=y, dx_px=float(dx), dy_px=float(dy), r_px=float(np.hypot(dx, dy)),
                 r_over_size=float(np.hypot(dx, dy) / size),
                 direction_deg=float(np.degrees(np.arctan2(dx, dy))),
                 sign="dark" if dog[y, x] < 0 else "bright",
                 contrast_dn=float(m[y, x] - np.nanmedian(m[max(y - 30, 0):y + 31, max(x - 30, 0):x + 31])),
                 z=float(z[y, x]), z_control=zc, frames=int(cnt[y, x]),
                 not_on_control=bool(zc <= control * z[y, x]), seen_on_frames=None, jitter_px=None, co_moving=False)
        (out if c["not_on_control"] and len(out) < top else on_control if len(on_control) < 5 else []).append(c)
    out = out + on_control
    return out, sig


# ---- pass 2: single frames, and following ----------------------------------------------
def examine(clip, track, frames, cands, size=None, follow=(), progress=None, stop=None):
    """One pass over the frames. For every candidate: `seen_on_frames` (the share of frames
    on which the feature is there at its offset, FRAME_Z times the frame's noise, with the
    same sign), `jitter_px` (where it is on those frames, across its own spread) and the
    verdict `co_moving`: not on the control, seen on SUPPORT of the frames or STRONG x Z_MIN,
    and steady to JITTER_PX. And each candidate in `follow` (indices into cands) followed
    from its offset -- in a gate about where it was last, the compact feature of its
    polarity -- with the background's own displacement since the first frame
    (`propose.background_shift`). Returns (cands, {index: {frame: (x, y, contrast)}}, bg)."""
    from .propose import background_shift
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    w = int(4 * SIGMA_OUT)
    hits, seen, where = np.zeros(len(cands)), np.zeros(len(cands)), [[] for _ in cands]
    follow = list(follow)
    offs = {k: np.array([cands[k]["dx_px"], cands[k]["dy_px"]]) for k in follow}
    gots = {k: {} for k in follow}
    bg, last = {}, None
    keep = max(0.6 * (size or 0), 2 * SIGMA_OUT)
    for n, g, bad in frames.each(ns, progress, stop, "Frames"):
        ox, oy = track[n]
        if follow:
            g32 = g.astype(np.float32)
            if last is None:
                bg[n] = (0.0, 0.0)
            else:
                d = background_shift(last[1], g32, ~(bad | last[2]))
                bg[n] = (bg[last[0]][0] + d[0], bg[last[0]][1] + d[1])
            last = (n, g32, bad)
        noise = wide_noise(g, bad, ox, oy)
        for k, c in enumerate(cands):
            if noise > 0:
                x, y = int(round(ox + c["dx_px"])), int(round(oy + c["dy_px"]))
                if w <= x < clip.W - w and w <= y < clip.H - w:
                    sub = g[y - w:y + w + 1, x - w:x + w + 1].copy()
                    sub[bad[y - w:y + w + 1, x - w:x + w + 1]] = np.nan
                    if np.isfinite(sub).sum() > 0.8 * sub.size:
                        d = _dog(sub)
                        core = d[w - 2:w + 3, w - 2:w + 3]
                        v = core.min() if c["sign"] == "dark" else core.max()
                        seen[k] += 1
                        hit = (abs(v) / noise >= FRAME_Z) and ((v < 0) == (c["sign"] == "dark"))
                        hits[k] += hit
                        if hit:
                            dd = np.where(np.isfinite(d), d, 0.0)
                            iy, ix = np.unravel_index(int(np.argmin(dd) if c["sign"] == "dark" else np.argmax(dd)), dd.shape)
                            where[k].append((ix - w, iy - w))
            if k not in offs:
                continue
            dark = c["sign"] == "dark"
            px, py = ox + offs[k][0], oy + offs[k][1]
            gate = max(GATE * np.hypot(*offs[k]), 4 * SIGMA_OUT)
            pad = gate + 3 * SIGMA_OUT
            x0, y0 = int(max(px - pad, 0)), int(max(py - pad, 0))
            x1, y1 = int(min(px + pad + 1, clip.W)), int(min(py + pad + 1, clip.H))
            if x1 - x0 < 8 or y1 - y0 < 8:
                continue
            sub = g[y0:y1, x0:x1].copy()
            sub[bad[y0:y1, x0:x1]] = np.nan
            resp = -_dog(sub) if dark else _dog(sub)
            yy, xx = np.mgrid[y0:y1, x0:x1]
            inside = (np.hypot(xx - px, yy - py) <= gate) & (np.hypot(xx - ox, yy - oy) >= keep)
            resp = np.where(inside & np.isfinite(resp), resp, -np.inf)
            if not np.isfinite(resp).any():
                continue
            iy, ix = np.unravel_index(int(np.argmax(resp)), resp.shape)
            if resp[iy, ix] <= 0:
                continue
            m = (resp >= 0.5 * resp[iy, ix]) & np.isfinite(resp)
            m &= np.hypot(xx - (x0 + ix), yy - (y0 + iy)) <= 2 * SIGMA_OUT
            wgt = np.where(m, resp, 0.0)
            cx_, cy_ = float((xx * wgt).sum() / wgt.sum()), float((yy * wgt).sum() / wgt.sum())
            gots[k][n] = (cx_, cy_, float(sub[iy, ix] - np.nanmedian(sub)))
            offs[k] = np.array([cx_ - ox, cy_ - oy])
    for k, c in enumerate(cands):
        c["seen_on_frames"] = float(hits[k] / seen[k]) if seen[k] else None
        pts = np.array(where[k]) if len(where[k]) >= 3 else None
        c["jitter_px"] = float(np.sqrt(max(np.linalg.eigvalsh(np.cov(pts.T)).min(), 0.0))) if pts is not None else None
        steady = c["jitter_px"] is None or c["jitter_px"] <= JITTER_PX
        near = c["r_px"] < NEAR * (size or 0)
        strong = c["z"] is not None and c["z"] >= STRONG * Z_MIN and not near
        need = 2 * SUPPORT if near else SUPPORT          # hugging the object, a glint or a halo is there on some frames; a line on most
        c["co_moving"] = bool(c["not_on_control"] and ((c["seen_on_frames"] or 0) >= need or strong) and steady)
    return cands, gots, bg


def with_the_object(companion, track, bg):
    """(moves with the object rather than the scene, the object's own motion against the scene in px):
    over the frames followed, the companion's displacement is nearer the object's than the
    background's (groups.with_the_group). Under STILL px the two cannot be told apart."""
    from .groups import with_the_group, _against
    ns = [n for n in sorted(companion) if n in track and n in bg]
    if len(ns) < 2:
        return None, 0.0
    moved = _against(track, bg, ns)
    return (bool(with_the_group({n: companion[n][:2] for n in ns}, track, bg)) if moved >= STILL else None), moved


# ---- the swing ----------------------------------------------------------------------------
def _model(tt, A, T, ph, c, s):
    return A * np.sin(2 * np.pi * tt / T + ph) + c + s * (tt - tt.mean())


def swing(track, companion, fps, repeats=()):
    """The companion's separation and angle, frame by frame (repeated frames left out), and
    whether the angle swings: dict of fields (see the module doc)."""
    rep = set(repeats)
    ns = sorted(n for n in companion if n in track and n not in rep)
    dropped = sum(1 for n in companion if n in track and n in rep)
    if len(ns) < MIN_SWING_FRAMES:
        return dict(frames=len(ns), repeated_frames_dropped=dropped,
                    finding=f"the companion was followed on {len(ns)} frames, fewer than {MIN_SWING_FRAMES}")
    t = np.array([(n - ns[0]) / fps for n in ns])
    sx = np.array([companion[n][0] - track[n][0] for n in ns])
    sy = np.array([companion[n][1] - track[n][1] for n in ns])
    sep = np.hypot(sx, sy)
    ang = np.degrees(np.arctan2(sx, sy))
    span = t[-1] - t[0]
    step = np.hypot(np.diff(sx), np.diff(sy)) / np.maximum(np.diff(np.array(ns, float)), 1)
    out = dict(frames=len(ns), repeated_frames_dropped=dropped, first=ns[0], last=ns[-1], span_s=float(span),
               separation_px=float(np.median(sep)), separation_range_px=[float(sep.min()), float(sep.max())],
               step_over_separation=float(np.median(step) / max(np.median(sep), 1e-6)),
               angle_mean_deg=float(ang.mean()), angle_sd_deg=float(ang.std()))
    out["smooth"] = bool(out["step_over_separation"] <= SMOOTH)
    if span < 1.0 or len(ns) < 10:
        out["finding"] = "too short to ask whether the angle swings"
        return out
    from scipy.signal import lombscargle
    trend = np.polyval(np.polyfit(t, ang, 1), t)
    P = np.linspace(0.5, max(0.6, 1.2 * span / TENTATIVE_CYCLES), 600)
    pw = lombscargle(t, ang - trend, 2 * np.pi / P, normalize=True)
    k = int(np.argmax(pw))
    period, power = float(P[k]), float(pw[k])
    out.update(period_s=period, power=power, cycles=float(span / period))
    # the sinusoid itself, with a drift: on a window of a few cycles this is the estimator, the
    # periodogram only its starting point (a peak slides up to whatever cap the window sets)
    amp = per_fit = resid = err = None
    try:
        from scipy.optimize import curve_fit
        p, cov = curve_fit(_model, t, ang, p0=[ang.std() * 1.4, period, 0.0, ang.mean(), 0.0], maxfev=20000)
        amp, per_fit = float(abs(p[0])), float(abs(p[1]))
        res = ang - _model(t, *p)
        resid = float(np.std(res))
        if amp > 90 or not (0.5 <= per_fit <= span / TENTATIVE_CYCLES) or not np.isfinite(cov[1, 1]) or resid > 0.5 * amp:
            out["fit_rejected"] = dict(period_s=per_fit, amplitude_deg=amp, residual_deg=resid)
            amp = per_fit = None
        else:
            err = _bootstrap_period(t, _model(t, *p), res, p, fps)
            out.update(amplitude_deg=amp, period_fit_s=per_fit, period_err_s=err, residual_deg=resid)
    except Exception:                               # the fit is one estimator; the periodogram stands without it
        pass
    at_edge = period >= 0.9 * P[-1]
    by_periodogram = power >= SWING_POWER and out["cycles"] >= TENTATIVE_CYCLES and not at_edge
    if per_fit is None and not by_periodogram:
        out.update(swings=False, tentative=False, line_length_m=None)
        if power >= SWING_POWER and (at_edge or out["cycles"] < TENTATIVE_CYCLES):
            why = (f"a swing, if it is one, is slower than {span / TENTATIVE_CYCLES:.1f} s a cycle, and {span:.1f} s show "
                   f"fewer than {TENTATIVE_CYCLES:g} of them")
        else:
            why = f"steady to +-{ang.std():.1f} deg over {span:.1f} s"
        out["finding"] = f"the companion's angle does not swing: {why}; no line length from it"
        return out
    T = per_fit if per_fit is not None else period
    cycles = float(span / T)
    L = G * T ** 2 / (4 * np.pi ** 2)
    tentative = cycles < CLAIM_CYCLES
    out.update(swings=True, tentative=tentative, period_used_s=float(T), cycles=cycles, line_length_m=float(L),
               line_length_err_m=float(2 * L * err / T) if err else None)
    pm = f" +- {err:.2f}" if err else ""
    lm = f" +- {2 * L * err / T:.2f}" if err else ""
    out["finding"] = (f"the companion swings: period {T:.2f}{pm} s" + (f", amplitude {amp:.1f} deg" if amp else "")
                      + f", {cycles:.1f} cycles" + (f" (tentative: fewer than {CLAIM_CYCLES:g})" if tentative else "")
                      + f" -> a pendulum of {L:.2f}{lm} m from its pivot "
                      "(the balloon's centre, not its neck: the line is shorter by the balloon's radius)")
    return out


def _bootstrap_period(t, fit, res, p, fps, n=BOOT, block_s=BLOCK_S):
    """The period's spread over `n` refits to the fit plus its own residuals resampled in
    blocks of `block_s` (the residuals are correlated frame to frame; single draws would
    say the period is known to a thousandth)."""
    from scipy.optimize import curve_fit
    rng = np.random.default_rng(20261007)
    N = len(t)
    b = max(2, int(round(block_s * fps)))
    starts = np.arange(0, N - b + 1)
    got = []
    for _ in range(n):
        idx = np.concatenate([np.arange(s, s + b) for s in rng.choice(starts, size=N // b + 1)])[:N]
        try:
            q, _ = curve_fit(_model, t, fit + res[idx], p0=p, maxfev=5000)
            got.append(abs(q[1]))
        except Exception:
            continue
    return float(np.std(got)) if len(got) >= 20 else None


# ---- the stage -------------------------------------------------------------------------
def measure(clip, track, masks=None, rows=None, size=None, seed=None, dark=None, r_min=R_MIN, r_max=R_MAX,
            strokes=True, out=None, say=print, progress=None, stop=None, procs=None):
    """The stage. Writes <out>_tether.png, <out>_tether_candidates.csv and, when a companion is
    followed, <out>_tether_companion.csv."""
    masks = masks if masks is not None else vf.static_masks(clip)
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    if len(ns) < 5:
        return Found("tether", fields=dict(frames=len(ns)), no_power=[("tether", "fewer than 5 frames of the track are in the clip")])
    xy = np.array([track[n] for n in ns])
    moved = float(np.hypot(*(xy.max(0) - xy.min(0))))
    radius = int(min(0.75 * max(clip.W, clip.H), (r_max + 2) * (size or 40)))
    frames = Frames(clip, masks, track, min(radius, STROKE_REGION), rows, strokes, procs=procs)
    m, cnt, mc, repeats = stack_both(clip, track, frames, radius=radius, progress=progress, stop=stop)
    R = radius
    est = object_size(m, cnt, R)
    size = size or est or 10.0
    extent = object_extent(m, cnt, R, size)
    r_min_used = max(r_min, (extent + 2 * SIGMA_OUT) / size)      # the object's own footprint is not a companion
    cands, sig = candidates(m, cnt, mc, size, R, r_min_used, r_max)
    fields = dict(frames=len(ns), repeated_frames=len(repeats), moved_on_screen_px=moved, object_size_px=float(size),
                  object_size_measured=est is not None, object_extent_px=extent, stack_noise_dn=sig, r_min=r_min_used, r_max=r_max,
                  stroke_mask=strokes)
    npw, notes, files = [], [], []
    if moved < STILL:
        npw.append(("tether: a thing on the object or on the screen",
                    f"the object moves only {moved:.0f} px on the screen over these frames: what is tied to it "
                    "cannot be told from the overlay or the scene, which stay as sharp"))
    sw, followed, best = None, {}, None
    if seed is not None:
        c0 = dict(dx_px=float(seed[0]), dy_px=float(seed[1]), r_px=float(np.hypot(*seed)), r_over_size=float(np.hypot(*seed) / size),
                  direction_deg=float(np.degrees(np.arctan2(seed[0], seed[1]))),
                  sign="dark" if dark else ("bright" if dark is False else None), z=None, z_control=None, frames=len(ns),
                  not_on_control=True, seen_on_frames=None, jitter_px=None, co_moving=False, contrast_dn=None)
        if c0["sign"] is None:                      # whichever is stronger at the seed, in the stack
            v = _dog(m)[int(round(R + seed[1])), int(round(R + seed[0]))]
            c0["sign"] = "dark" if v < 0 else "bright"
        _, gots, bg = examine(clip, track, frames, [c0], size, follow=[0], progress=progress, stop=stop)
        followed = gots[0]
        sw = swing(track, followed, clip.fps, repeats)
        sw["with_the_object"], sw["object_against_scene_px"] = with_the_object(followed, track, bg)
        sw["seed"], sw["dark"] = [float(seed[0]), float(seed[1])], c0["sign"] == "dark"
    else:
        # every candidate gets its single-frame support; the strongest the control does not show are also
        # followed, in the same pass. The first that moves with the object -- not with the scene -- and is
        # co-moving on the stack, or else moves smoothly, is the companion. The others are marked.
        cands, _, _ = examine(clip, track, frames, cands, size, follow=(), progress=progress, stop=stop)
        follow = [k for k, c in sorted(enumerate(cands), key=lambda kc: (not kc[1]["co_moving"], -(kc[1]["seen_on_frames"] or 0), -kc[1]["z"]))
                  if c["not_on_control"]][:FOLLOW]
        cands, gots, bg = examine(clip, track, frames, cands, size, follow=follow, progress=progress, stop=stop)
        order = sorted(follow, key=lambda k: (not cands[k]["co_moving"], -(cands[k]["seen_on_frames"] or 0), -cands[k]["z"]))
        for k in order:
            c, got = cands[k], gots[k]
            w = swing(track, got, clip.fps, repeats)
            w["with_the_object"], w["object_against_scene_px"] = with_the_object(got, track, bg)
            w["seed"], w["dark"] = [c["dx_px"], c["dy_px"]], c["sign"] == "dark"
            c["followed_frames"] = w["frames"]
            if w["with_the_object"] is False:
                c["co_moving"], c["scene"] = False, True
                sw = sw or w
                continue
            enough = w["frames"] >= max(MIN_SWING_FRAMES, 0.5 * len(ns))
            consistent = w.get("angle_sd_deg", 999) <= 30 and w.get("step_over_separation", 1) <= SMOOTH / 2
            if best is None and w.get("smooth") and enough and (c["co_moving"] or (w["with_the_object"] and consistent)):
                c["co_moving"], c["followed"] = True, True
                best, followed, sw = c, got, w
            elif c["co_moving"] and not w.get("smooth"):
                c["co_moving"], c["jumps"] = False, True          # followed, it jumps by its gate: not one thing
    cands = sorted(cands, key=lambda c: (not c["co_moving"], -(c["seen_on_frames"] or 0), -c["z"]))
    cands = [c for c in cands if c["co_moving"]][:8] + [c for c in cands if not c["co_moving"]][:3]
    fields["candidates"] = [{k: v for k, v in c.items() if not k.startswith("_")} for c in cands]
    fields["companion"] = {k: v for k, v in best.items() if not k.startswith("_")} if best else None
    fields["swing"] = sw
    if seed is None and best is None:
        if sw and sw.get("with_the_object") is False:
            finding = (f"the stack's feature(s) move with the scene, not the object (the object moves "
                       f"{sw['object_against_scene_px']:.0f} px against the scene over the window); nothing tied to the object")
        else:
            finding = (f"nothing moves with the object between {r_min_used:.1f} and {r_max:g} object sizes of it at "
                       f"{Z_MIN:g} x the stack's noise ({sig:.1f} DN)" if np.isfinite(sig) else "the stack is too small to ask")
            if cands:
                finding += (f"; the {len(cands)} strongest feature(s) are as sharp on the reversed track, or not there on single "
                            "frames: the frame or the scene, not the object")
    else:
        if best is not None:
            finding = (f"a {best['sign']} feature moves with the object {best['r_px']:.0f} px ({best['r_over_size']:.1f} object "
                       f"sizes) away at {best['direction_deg']:+.0f} deg from straight down, {best['z']:.1f} x the noise "
                       f"({best['z_control']:.1f} on the reversed track), there on {100 * (best['seen_on_frames'] or 0):.0f}% of single frames")
        else:
            finding = f"companion followed from the given offset {tuple(round(v) for v in seed)}"
        if sw:
            finding += "; " + sw["finding"]
            if sw.get("with_the_object") is None and sw.get("object_against_scene_px", STILL) < STILL:
                npw.append(("tether: with the object or with the scene",
                            f"the object moves only {sw['object_against_scene_px']:.0f} px against the scene over the window: "
                            "a thing of the scene at that offset cannot be told from a thing tied to the object"))
            if sw.get("tentative"):
                npw.append(("tether: the period", f"{sw['cycles']:.1f} cycles of the swing are in the window, fewer than "
                                                  f"{CLAIM_CYCLES:g}: the period and the line are tentative"))
    fields["finding"] = finding
    if repeats:
        notes.append(f"{len(repeats)} repeated frames were left out of the swing series.")
    if out:
        with open(f"{out}_tether_candidates.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["dx_px", "dy_px", "r_px", "r_over_size", "direction_deg", "sign", "contrast_dn", "z", "z_control",
                        "frames", "seen_on_frames", "jitter_px", "co_moving", "scene"])
            for c in cands:
                w.writerow([round(c["dx_px"], 1), round(c["dy_px"], 1), round(c["r_px"], 1), round(c["r_over_size"], 2),
                            round(c["direction_deg"], 1), c["sign"], round(c["contrast_dn"], 1), round(c["z"], 1),
                            round(c["z_control"], 1), c["frames"], "" if c["seen_on_frames"] is None else round(c["seen_on_frames"], 2),
                            "" if c.get("jitter_px") is None else round(c["jitter_px"], 1), c["co_moving"], bool(c.get("scene"))])
        files.append(f"{out}_tether_candidates.csv")
        if followed:
            with open(f"{out}_tether_companion.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["frame", "x_px", "y_px", "dx_px", "dy_px", "angle_deg", "contrast_dn", "repeated"])
                for n, (x, y, c) in sorted(followed.items()):
                    dx, dy = x - track[n][0], y - track[n][1]
                    w.writerow([n, round(x, 2), round(y, 2), round(dx, 2), round(dy, 2), round(np.degrees(np.arctan2(dx, dy)), 2),
                                round(c, 1), n in set(repeats)])
            files.append(f"{out}_tether_companion.csv")
        figure(m, mc, R, size, cands, track, followed, sw, clip.fps, set(repeats), f"{out}_tether.png")
        files.append(f"{out}_tether.png")
        say(f"wrote {', '.join(files)}")
    return Found("tether", dict(finding=finding), fields, files=files, no_power=npw, notes=notes, carry=followed or None)


def figure(m, mc, R, size, cands, track, followed, sw, fps, repeats, path):
    """Left: the object-centred stack with the candidates ringed (solid: moves with the object;
    dashed: not the object's). Middle: the reversed-track control. Right: the companion's angle,
    frame by frame, with the fitted swing when there is one."""
    from . import figures
    plt = figures.setup()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4))
    crop = int(min(R, max(60, (max((c["r_px"] for c in cands), default=0) + 4 * size), 6 * size)))
    for ax, img, title in ((axes[0], m, "stacked on the object"), (axes[1], mc, "control: track run backwards")):
        sub = img[R - crop:R + crop + 1, R - crop:R + crop + 1]
        lo, hi = np.nanpercentile(sub, [1, 99])
        ax.imshow(sub, cmap="gray", vmin=lo, vmax=hi, extent=(-crop, crop, crop, -crop))
        ax.set_title(title)
        ax.set_xlabel("px from the object")
    for c in cands:
        axes[0].add_patch(plt.Circle((c["dx_px"], c["dy_px"]), 2.5 * SIGMA_OUT, fill=False, lw=1.2,
                                     ec="tab:red" if c["co_moving"] else "tab:orange", ls="-" if c["co_moving"] else "--"))
    ax = axes[2]
    if followed and sw and "angle_mean_deg" in sw:
        ns = sorted(n for n in followed if n in track and n not in repeats)
        t = np.array([(n - ns[0]) / fps for n in ns])
        ang = np.degrees(np.arctan2(*np.array([(followed[n][0] - track[n][0], followed[n][1] - track[n][1]) for n in ns]).T))
        ax.plot(t, ang, ".", ms=3, color="tab:blue", label="companion")
        if sw.get("swings") and sw.get("amplitude_deg"):
            T = sw["period_used_s"]
            err = f" +- {sw['line_length_err_m']:.2f}" if sw.get("line_length_err_m") else ""
            ax.set_title(f"swing: T = {T:.2f} s -> L = {sw['line_length_m']:.2f}{err} m" + (" (tentative)" if sw.get("tentative") else ""))
        else:
            ax.set_title("angle from straight down")
        ax.set_xlabel("s")
        ax.set_ylabel("deg (+ right)")
    else:
        ax.text(0.5, 0.5, "no companion followed", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    figures.save(fig, path, tight=True)


def said(fields):
    """What `mcdonald tether` prints, from the fields."""
    L = [f"object {fields['object_size_px']:.0f} px across" + ("" if fields.get("object_size_measured") else " (assumed)")
         + (f", reaching {fields['object_extent_px']:.0f} px from its centre" if fields.get("object_extent_px") else "")
         + f", moved {fields['moved_on_screen_px']:.0f} px on the screen over {fields['frames']} frames"
         + (f" ({fields['repeated_frames']} repeated)" if fields.get("repeated_frames") else "")
         + f"; stack noise {fields['stack_noise_dn']:.1f} DN" + ("" if fields.get("stroke_mask", True) else "; overlay strokes not masked")]
    for c in fields.get("candidates", []):
        L.append(f"  {c['sign']:6s} feature {c['r_px']:6.0f} px ({c['r_over_size']:5.1f} sizes) at {c['direction_deg']:+5.0f} deg: "
                 f"z {c['z']:5.1f} on the object, {c['z_control']:5.1f} on the reversed track, on "
                 f"{100 * (c['seen_on_frames'] or 0):3.0f}% of frames, jitter "
                 + (f"{c['jitter_px']:.0f} px" if c.get("jitter_px") is not None else "n/a") + " -> "
                 + ("moves with the object" if c["co_moving"] else ("the scene's, once followed" if c.get("scene")
                    else "jumps about, once followed" if c.get("jumps") else "not the object's")))
    sw = fields.get("swing")
    if sw and "separation_px" in sw:
        L.append(f"  companion followed on {sw['frames']} frames ({sw['span_s']:.1f} s"
                 + (f", {sw['repeated_frames_dropped']} repeats left out" if sw.get("repeated_frames_dropped") else "")
                 + f"): {sw['separation_px']:.0f} px from the object, moving {100 * sw['step_over_separation']:.1f}% of that a frame, "
                 f"angle {sw['angle_mean_deg']:+.1f} +- {sw['angle_sd_deg']:.1f} deg"
                 + (f"; periodogram peak {sw['period_s']:.2f} s (power {sw['power']:.2f})" if "period_s" in sw else ""))
    L.append(fields.get("finding", ""))
    return L


# ---- CLI ----------------------------------------------------------------------------
def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", required=True, help="CSV with frame and x/y columns: the object, as linked")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--size", type=float, help="the object's size, px (default: measured in the stack)")
    ap.add_argument("--seed", help="DX,DY: follow a companion from this offset (px) from the object on the first frame")
    ap.add_argument("--dark", action="store_true", help="the companion is darker than what is round it")
    ap.add_argument("--bright", action="store_true", help="... or brighter (default: whichever is stronger at the seed)")
    ap.add_argument("--r-min", type=float, default=R_MIN, help=f"inner ring, object sizes (default {R_MIN:g})")
    ap.add_argument("--r-max", type=float, default=R_MAX, help=f"outer ring, object sizes (default {R_MAX:g})")
    ap.add_argument("--no-stroke-mask", action="store_true",
                    help="do not mask the overlay's thin bright strokes (needed when the line on the object is itself bright)")
    ap.add_argument("--mask-rows")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--procs", type=int, default=None, help=PROCS_HELP)
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        found, clip = _main(args)
    code = vf.EXIT_NOTHING if any(t.startswith("tether: a thing") or t == "tether" for t, _ in found.no_power) else 0
    if args.json:
        emit(found.envelope("tether", inputs_of(args), clip, said=lines, exit_code=code, error=None))
    return code


def _main(args):
    video, tag, _ = vf.resolve(args.video)
    track = vf.read_track(args.track)
    n0 = args.n0 if args.n0 is not None else min(track)
    n1 = args.n1 if args.n1 is not None else max(track)
    clip = vf.Clip(video, args.workdir, n0, n1)
    out = vf.out_prefix(args.out, tag)
    print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
    seed = tuple(float(v) for v in args.seed.split(",")) if args.seed else None
    dark = True if args.dark else (False if args.bright else None)
    found = measure(clip, track, rows=vf.parse_rows(args.mask_rows), size=args.size, seed=seed, dark=dark,
                    r_min=args.r_min, r_max=args.r_max, strokes=not args.no_stroke_mask, out=out, progress=to_stderr(),
                    procs=args.procs)
    print("\n".join(said(found.fields)))
    return found, clip


if __name__ == "__main__":
    raise SystemExit(main())
