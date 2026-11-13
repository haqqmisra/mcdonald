"""Is something tethered to the object -- a line or a payload that moves with it -- and does it swing?

A sounding balloon carries its radiosonde 25-55 m below it on a line; a hobby balloon a
few grams a metre or two below. A pilot's "strings hanging off" (the Lake Huron object
of 2023-02-12, PR071) is the same thing. Nothing else in the sky is a body with a point
hanging under it, and a hanging point is a pendulum: its period is set by gravity and
the line, T = 2 pi sqrt(L/g), so T read off the video in seconds gives L in metres with
no range and no field of view, and the line's length in pixels then scales the whole
image. That is the balloon analogue of PR135's wingbeat.

The question is asked in two parts (`stack_both` with `candidates`, `examine` with a
`Follower` for each candidate and `judge`, then `swing`), reading every frame three
times in all:

1. **Does anything move with the object?** Every frame, overlay masked, is shifted so
   the tracked position lands at the centre and the frames are averaged: a feature tied
   to the object adds up at its offset; the scene and the overlay smear by however far
   the object moved on the screen. A candidate is a compact feature of that stack, `Z_MIN`
   times its noise, between `r_min` and `r_max` object sizes of the centre (and outside
   the object's own footprint: `searched_px` is the ring in pixels, and a line that
   starts at the object, inside it, is not looked for). Three things then say whether it
   is the object's (`judge`):
   - *the control*: the same frames stacked on the track run backwards in time have the
     same set of positions and the wrong one each frame, so a feature tied to the object
     smears there while anything that only looked sharp because the object hardly moved
     stays sharp (PR055's edge peaks reappeared there identically). `z_control` at most
     `CONTROL` of `z`. Both stacks are made in the one pass.
   - *frame by frame*: the candidate is re-found on the frames themselves, starting
     where the stack put it (`Follower`): the strongest compact feature of its polarity
     within `STEP` px of the stack's offset, `SIGHT` times the frame's noise (by MAD
     over a wide crop, so the overlay's lines do not set it) and at least `HALF` as
     strong as the stack's own; then, frame to frame, the nearest feature to where it
     was last seen. It may swing, to `LEASH` of its distance from the stack's offset, and
     no farther: it is never followed away, and after `MISS` frames unseen the search
     starts again at the stack's offset. The frames are gone through in order and in
     reverse, and the two ways put together (`merge_ways`). A companion is held: it lies
     in stretches of `HOLD` frames or more on `FOLLOWED` of the frames, along a path
     smooth to `STEADY` px (noise and texture met near the offset come and go).
     Until 0.5.2 the gate moved to whatever was last found, the strongest feature in it:
     on PR105 the follower went 1,290 px from the object with the scene, and on two
     birds of the released reference reports it went round the object and read a
     pendulum of 9.71 m and one of 2.52 m (session 19, 2026-11-10).
   - *with the object, the scene or the screen*: the re-found place against the object
     is regressed on the scene's place against the object (the background's own shift,
     `propose.background_shift`) and on the screen's. A feature tied to the object makes
     none of either motion; a piece of cloud drifting past makes all of the scene's, a
     mark left on the display all of the screen's. `SCENE` of either, where it moved
     `STILL` px or more, and the candidate is not the object's.
   These numbers were set against a null (docs/method.md, section 6;
   tools/tether_null.py): every recorded track run again on tracks that nothing in the
   picture keeps step with, the known companions kept.
   **The overlay's strokes are masked first** (`stroke_mask`): thin bright lines --
   reticle arms, a tracking gate's box, brackets -- are found by a morphological
   opening (what survives a line-shaped opening along either axis but not a square
   one) and left out of every stack and every test, because a tracking gate *is* tied
   to the object, by the tracker, late, and its edges passed every test above on PR071
   until they were masked. A thin *bright* line on the object would be masked with
   them (`--no-stroke-mask`); PR071's string is dark and is not. When the object moves
   less than `STILL` px on the screen, nothing can be told apart and the stage says so.
2. **Does it swing?** Asked of the companion alone -- the one kept, or an offset given
   with --seed -- on the frames that show it. The separation vector from the object
   gives the swing angle (0 = straight down the image, + = to the right), which needs no
   scale and survives any camera motion short of a roll. Repeated frames (the
   hold-and-jump cadence sensor clips have) are left out of the series. A Lomb-Scargle
   periodogram starts it; the estimator is a sinusoid with a drift fitted to the angle,
   kept when it is clean (residual under half the amplitude) -- a periodogram's peak on
   a window of a few cycles slides up to whatever cap the window sets, and a peak at the
   longest period asked is never a period. The period's uncertainty is a block bootstrap
   of the fit's residuals (`BOOT` resamples, blocks of `BLOCK_S`), and `line_length_m` =
   g T^2 / 4 pi^2 carries it doubled. A swing is **claimed** from `CLAIM_CYCLES` cycles
   of the window and **tentative** from `TENTATIVE_CYCLES` -- and, since 0.5.2, only
   where the period beats a slow wander (`wander_null`): an angle that only wanders shows
   a cycle or two in a short window most of the time, and the cycles rule alone read
   "2.0 m" off AARO's known balloon PR-004 from two 6-7-s windows. The one calibration
   with ground truth (WA9ONY-5, a 13 g pico payload "a little over one metre" below the
   balloon, 2021-07-13) is tentative -- 1.7 cycles, 2.59 s, 1.66 m, which is the line
   plus the balloon's radius and the payload's own offset, the pivot of a balloon's
   pendulum being the balloon's centre, not its neck -- and passes the null (none of
   2,000 wanders as strong).

What it cannot do: a payload too faint for single frames that swings more than its own
size evades the stack (it smears by its swing) and the follower both; that needs a
search over the pendulum's own motion, not done here. A line that starts at the object
(PR28's stem) is inside the ring searched. A line held at a steady angle by drag (PR071:
no swing in 8 s) gives no length. And the companion's pixel offset is in pixels for the
reasons every separation is; only the period is a metre.
"""
import csv
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from scipy import ndimage
from scipy.ndimage import gaussian_filter

from . import forensics as vf
from .progress import BESIDE, PROCS_HELP, Beside, counted, to_stderr, workers
from .report import Found, emit, inputs_of, said_to_stderr

R_MIN = 1.2          # x the object's size: the first ring a companion is looked for in (inside is the object)
R_MAX = 40.0         # x the object's size: a radiosonde hangs 10-35 diameters below a sounding balloon
NOISE_SIZES = 8.0    # the stack's noise is measured out to this many object sizes (see `candidates`)
TOP = 200            # candidates the control does not show that get their single-frame support ...
FOLLOW = 60          # ... and how many of those, strongest first, are re-found frame by frame
COVERED = 0.6        # a candidate's pixel was covered by the frames on this share of them at least: a tracking gate's
                     # strokes, masked, sweep the object's neighbourhood by the tracker's lag, and 0.95 here dropped
                     # PR071's string out of the search
COVERED_EXTENT = 0.95   # the object's own footprint is traced only through pixels covered on nearly every frame
Z_MIN = 5.0          # a candidate is at least this many times the stack's noise (DoG units)
CONTROL = 0.6        # ... and the reversed-track control shows at most this share of it at the same place (held against
                     # the null in 0.5.2 and left: 0.3 changes no count there)
STILL = 20.0         # px moved on the screen below which nothing can be told from the overlay or the scene
SIGMA = 1.2          # DoG inner scale, px: a line or a point a few px across
SIGMA_OUT = 6.0      # DoG outer scale, px
FRAME_Z = 2.5        # a candidate counts as seen at its own offset on a frame at this many times the frame's noise
                     # (`seen_on_frames`, with `jitter_px`: reported; the verdict is the follower's, since 0.5.2)
SMOOTH = 0.08        # x its distance: a companion moving under this much a frame is `smooth` in the swing's record (a
                     # pendulum's payload, 2.5 s and 14 deg on 170 px: 2 %)
STEP = 12.0          # px: from one frame to the next a companion is re-found no farther than this from where it was
                     # last seen (WA9ONY-5's payload moves 3 px a frame at the middle of its swing), and a stretch starts
                     # no farther than this from the stack's offset
LEASH = 0.75         # x its distance on the stack: the companion is looked for no farther than this from where the stack
                     # put it. It may swing, and a swing's stack peaks at one end of it (WA9ONY-5's payload is found up to
                     # 0.70 of its 158 px from the stack's offset); it is never followed away (0.5.1 followed PR077 object
                     # 1's from 13 to 400 px and PR105's from 14 to 1,290 px, and read a swing off each)
MISS = 5             # frames unseen after which a stretch ends; the next starts at the stack's offset
HALF = 0.5           # a single-frame feature is at least this share of the stack feature's own strength: the stack is the
                     # mean of the frames, so a companion is at least as strong as its stack on the frames that show it
PEAK = 9             # px: two compact features of one frame are at least half of this apart
SIGHT = 5.0          # a companion re-found on a frame is at least this many times the frame's own noise, the multiple
                     # the stack asks of a candidate: within STEP px of a place a feature at FRAME_Z times the noise is
                     # there by chance on a quarter of the frames, and the null's followers were made of them (3 to 4
                     # times the noise at the median; every known companion is 8 to 111)
HOLD = 45            # frames: a companion is held in stretches at least this long (nearly the whole of a shorter track) ...
FOLLOWED = 0.3       # ... on at least this share of the frames (PR105's lower point, which fades and returns: 0.34) ...
STEADY = 1.5         # ... along a path smooth to this many px (the known companions: 0.4 to 0.6) ...
SCENE = 0.5          # ... making under this share of the scene's motion against the object, and of the screen's: nearer
                     # the object's motion than theirs (the known companions make 0.00 to 0.26, the scene's features 0.7 on)
MIN_SWING_FRAMES = 20
CLAIM_CYCLES = 2.0       # a period is claimed from this many cycles of the window ...
TENTATIVE_CYCLES = 1.5   # ... and reported as tentative from this many: a clean sinusoid over 1.5 fixes it to ~10%
SWING_POWER = 0.3    # Lomb-Scargle normalised power below which the angle is called steady
WANDER_P = 0.001     # a period is a swing only when a slow wander of the angle's own size and correlation shows one as
                     # strong less often than this (`wander_null`). Set on drawn wanders, 57 kinds and 600 of each
                     # (2026-11-10): with the cycles rule, which alone calls up to 78 % of them a swing, this holds the
                     # false swings to 1 in 100 at the worst (0-1.0 %); 0.01 here left up to 3.3 %
WANDER_DRAWS = 2000  # wanders drawn for it
WANDER_BINS = 60     # the angle is read in this many bins of its span (wider where a bin would hold under 3.5 samples)
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

    def each(self, ns, progress=None, stop=None, what="", also=None):
        """(n, grey, bad) for each frame of `ns`, in order, exactly as `self(n)` gives them, saying how far
        the pass has got and asking `stop` after each (`progress.counted`). With `also`, (n, grey, bad,
        also(n, grey, bad)): what a pass computes from one frame alone, done in the thread that read the frame
        and not by the pass, which then waits on nothing but what ties one frame to the next. The same function on
        the same frame, so the same numbers (2026-11-13: PR088's 3,558 frames, the frame's noise 17 ms each in the
        pass's own thread, 59 of the pass's 97 s; SciPy's filters let other threads run)."""
        ns = list(ns)
        fresh = {n for n in ns if self.cache is None or n not in self.cache}
        size = workers(self.procs, self.clip.W * self.clip.H) if fresh or also is not None else 0

        def one(n):
            if n in fresh:
                grey, bad = self._read(n)
                g, bad = self._keep(n, grey.astype(np.float64), bad)
            else:
                g, bad = self(n)
            return (n, g, bad) if also is None else (n, g, bad, also(n, g, bad))
        if not size:
            for n in counted(ns, progress, stop, what):
                yield one(n)
            return
        out, it = deque(), iter(ns)
        ex = ThreadPoolExecutor(size)

        def more():
            n = next(it, None)
            if n is not None:
                out.append(ex.submit(one, n))
        try:
            for _ in range(2 * size):
                more()
            for n in counted(ns, progress, stop, what):
                got = out.popleft().result()
                more()
                yield got
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
    cap = min(cap, R)              # a stack smaller than the cap (an object given as under 5 px: the stack is 42 sizes)
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

    def weighed(n, g, bad):                                # in the thread that read the frame (`Frames.each`)
        w = (~bad).astype(np.float64)
        return w, g * w

    def put(a, c, xy, w, gw):                              # one frame into one stack, where (x, y) puts it
        ox, oy = int(round(R - xy[0])), int(round(R - xy[1]))
        x0, y0 = max(ox, 0), max(oy, 0)
        x1, y1 = min(ox + clip.W, S), min(oy + clip.H, S)
        if x1 <= x0 or y1 <= y0:
            return
        a[y0:y1, x0:x1] += gw[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        c[y0:y1, x0:x1] += w[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
    # The two stacks are filled beside each other, each in the frames' own order (a sum of doubles depends on its
    # order, so no stack's frames are shared out): the object's in a thread beside this one, the mirror's here.
    beside = Beside(None if frames.procs is None else min(int(frames.procs), 2))
    try:
        for i, (n, g, bad, (w, gw)) in enumerate(frames.each(ns, progress, stop, "Stack", also=weighed)):
            own = beside.call(put, acc, cnt, pos[i], w, gw)
            put(accr, cntr, pos[len(ns) - 1 - i], w, gw)
            own.result()
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
    finally:
        beside.close()
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)
        mc = np.where(cntr > 0, accr / np.maximum(cntr, 1), np.nan)
    return m, cnt, mc, repeats


def object_size(m, cnt, R, cap=200):
    """The object's own size in the stack, px: the width at half its central contrast,
    measured along four directions and averaged. None when there is no central contrast."""
    cap = min(cap, R)
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
                 dog_dn=float(abs(dog[y, x])), z=float(z[y, x]), z_control=zc, frames=int(cnt[y, x]),
                 not_on_control=bool(zc <= control * z[y, x]), seen_on_frames=None, jitter_px=None, co_moving=False)
        (out if c["not_on_control"] and len(out) < top else on_control if len(on_control) < 5 else []).append(c)
    out = out + on_control
    return out, sig


# ---- pass 2: single frames, and following ----------------------------------------------
def leash_px(r):
    """How far from the stack's offset a companion `r` px from the object is looked for."""
    return max(LEASH * r, 2 * SIGMA_OUT)


def _dog_valid(g, bad):
    """The DoG of a crop with what is masked left out of both of its means (a normalised convolution),
    NaN where either mean rests on less than half its weight: a mask's edge is not a feature."""
    w = (~bad).astype(np.float64)
    gw = np.where(bad, 0.0, g)
    a0, b0 = gaussian_filter(w, SIGMA), gaussian_filter(w, SIGMA_OUT)
    with np.errstate(invalid="ignore", divide="ignore"):
        d = gaussian_filter(gw, SIGMA) / a0 - gaussian_filter(gw, SIGMA_OUT) / b0
    return np.where((a0 > 0.5) & (b0 > 0.5), d, np.nan)


def feature_near(g, bad, noise, obj, place, anchor, leash, dark, least, keep, strongest=False):
    """The compact feature of one frame nearest to `place` (dx, dy from the object at `obj`), or with
    `strongest` the strongest about it: a local maximum of the DoG of that polarity within STEP px of the
    place, at least `least` DN strong and SIGHT times the frame's `noise`, at least `keep` px from the
    object and no farther than `leash` from `anchor`. Its centroid, as (dx, dy, strength in units of the
    noise, contrast DN), or None when nothing is there."""
    ox, oy = obj
    px, py = ox + place[0], oy + place[1]
    pad = STEP + 3 * SIGMA_OUT
    x0, y0 = int(max(px - pad, 0)), int(max(py - pad, 0))
    x1, y1 = int(min(px + pad + 1, g.shape[1])), int(min(py + pad + 1, g.shape[0]))
    if x1 - x0 < 8 or y1 - y0 < 8:
        return None
    sub, sbad = g[y0:y1, x0:x1], bad[y0:y1, x0:x1]
    d = _dog_valid(sub, sbad)
    resp = np.where(np.isfinite(d), -d if dark else d, -np.inf)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    far = np.hypot(xx - px, yy - py)
    top = ((resp == ndimage.maximum_filter(resp, size=PEAK)) & (resp >= max(SIGHT * noise, least)) & (far <= STEP)
           & (np.hypot(xx - ox, yy - oy) >= keep) & (np.hypot(xx - (ox + anchor[0]), yy - (oy + anchor[1])) <= leash))
    if not top.any():
        return None
    iy, ix = np.unravel_index(int(np.argmax(np.where(top, resp, -np.inf)) if strongest else np.argmin(np.where(top, far, np.inf))),
                              top.shape)
    # its centroid, over its own peak alone: a stronger spot passing 9 px away is another peak, and a centroid that
    # reached it was pulled to it, and the follower after it
    wgt = np.where((resp >= 0.5 * resp[iy, ix]) & (np.hypot(xx - (x0 + ix), yy - (y0 + iy)) <= PEAK // 2 + 1), resp, 0.0)
    cx_, cy_ = float((xx * wgt).sum() / wgt.sum()), float((yy * wgt).sum() / wgt.sum())
    around = sub[~sbad]
    return (cx_ - ox, cy_ - oy, float(resp[iy, ix] / noise), float(sub[iy, ix] - np.median(around)) if around.size else 0.0)


class Follower:
    """One candidate's companion, re-found frame by frame. A stretch starts where the stack put the
    candidate: at the strongest compact feature of its polarity within STEP px of the stack's offset, at
    least HALF as strong as the stack's own. After that the feature nearest to where the companion was last seen is taken,
    within STEP px of it and within the candidate's leash of the stack's offset (a brighter spot passing by
    is not taken; the companion may swing, and is never followed away). When nothing has been there for MISS
    frames the stretch ends, and the next starts at the stack's offset as the first did.

    The frames are gone through twice, `look(n, ...)` with way 0 in order and with way 1 in reverse, each
    way a follower of its own. The second reaches the frames before the companion first came by the stack's
    offset; and where a stronger spot of the scene passed right over the companion, each way is carried off
    with it on the far side of the crossing only. `merged()` puts the two together: where they disagree, the
    feature nearer the stack's offset is the companion -- what is tied stays about it, what passes leaves."""

    def __init__(self, c, keep):
        self.anchor = (c["dx_px"], c["dy_px"])
        self.dark, self.leash, self.keep = c["sign"] == "dark", leash_px(c["r_px"]), keep
        self.least = HALF * (c.get("dog_dn") or 0.0)
        self.got = ({}, {})                   # each way's {frame: (dx, dy, strength, contrast)}
        self.place, self.last = [None, None], [None, None]

    def look(self, way, n, g, bad, noise, obj):
        held = self.place[way] is not None and abs(n - self.last[way]) <= MISS
        f = feature_near(g, bad, noise, obj, self.place[way] if held else self.anchor, self.anchor, self.leash, self.dark,
                         self.least, self.keep, strongest=not held)
        if f is not None:
            self.place[way], self.last[way], self.got[way][n] = f[:2], n, f

    def merged(self):
        return merge_ways(self.anchor, self.got)


def stretches(got):
    """{frame: stretch} of a chain {frame: (dx, dy, ...)}: frames no more than MISS apart whose places are no
    more than STEP px apart."""
    run, runs, last = 0, {}, None
    for n in sorted(got):
        if last is None or n - last > MISS or np.hypot(got[n][0] - got[last][0], got[n][1] - got[last][1]) > STEP:
            run += 1
        runs[n], last = run, n
    return runs


def merge_ways(anchor, ways):
    """({frame: (dx, dy, strength, contrast)}, {frame: stretch}): a Follower's two ways as one. Over a run of
    frames on which they hold different features, the one followed for longer is the companion (scene texture
    met at the stack's offset while a swinging companion is elsewhere lasts a few frames); where both were
    followed about as long, less than twice apart, the one nearer the stack's offset `anchor` over the run.
    One way is taken for the whole run: along a line the two sit at different points of it, and frame by
    frame the choice would jump between them."""
    runs = [stretches(g) for g in ways]
    size = [{r: sum(1 for v in rr.values() if v == r) for r in set(rr.values())} for rr in runs]
    off = lambda f: np.hypot(f[0] - anchor[0], f[1] - anchor[1])
    differ = lambda n: (n in ways[0] and n in ways[1]
                        and np.hypot(ways[0][n][0] - ways[1][n][0], ways[0][n][1] - ways[1][n][1]) > 2.0)
    frames, got, i = sorted(set(ways[0]) | set(ways[1])), {}, 0
    while i < len(frames):
        n = frames[i]
        if not differ(n):
            got[n] = ways[0][n] if n in ways[0] else ways[1][n]
            i += 1
            continue
        j = i
        while j < len(frames) and differ(frames[j]) and frames[j] - frames[max(j - 1, i)] <= MISS:
            j += 1
        run = frames[i:j]
        la, lb = (np.mean([size[w][runs[w][m]] for m in run]) for w in (0, 1))
        way = 0 if la >= 2 * lb else 1 if lb >= 2 * la else int(np.median([off(ways[1][m]) for m in run])
                                                                  < np.median([off(ways[0][m]) for m in run]))
        got.update({m: ways[way][m] for m in run})
        i = j
    return got, stretches(got)


def followed_how(ns, got, runs, track, bg, repeats=()):
    """How a re-found companion behaves, from its places against the object over the frames `ns` of the track
    (`got`: {frame: (x, y, ...)}, `runs`: {frame: stretch}, repeated frames left out):
    `followed_on`, the share of the frames it was seen on, and `held_on`, the share of the frames that lie in
    stretches of HOLD frames or more (a companion is held; noise and texture met near the offset come and go; on
    a track shorter than HOLD the stretch asked is nearly the whole track, `hold_frames`);
    `followed_jitter_px`, its scatter about a smooth path: how far each place lies from the line between the
    places before and after it in the same stretch, scaled to one reading's error (a swing's motion drops
    out; noise picked up near the offset does not);
    `scene_share`, the share of the scene's motion against the object that the companion makes: its place
    against the object regressed on the scene's place against the object, each stretch about its own mean
    (about 0 for what is tied to the object, 1 for a piece of the scene passing by), with `scene_moved_px`,
    how far the scene moved against the object within a stretch at the most (under STILL px the two cannot be
    told apart);
    `screen_share` and `screen_moved_px`, the same against the screen: 1 for what stays put on the screen while
    the object moves across it (the display's, or the sensor's).
    Places are regressed, not the steps between frames: a step of the companion against the object and a step
    of the scene against the object carry the same error of the track, which alone made a drawn companion,
    tied exactly, 0.7 of a scene that hardly moved."""
    rep = set(repeats)
    fs = [n for n in ns if n in got and n not in rep]
    rel = {n: np.array([got[n][0] - track[n][0], got[n][1] - track[n][1]]) for n in fs}
    length = {}
    for n in fs:
        length[runs[n]] = length.get(runs[n], 0) + 1
    count = max(len([n for n in ns if n not in rep]), 1)
    hold = min(HOLD, max(count - MISS, MIN_SWING_FRAMES))        # on a track shorter than HOLD, nearly the whole of it
    out = dict(followed_on=float(len(fs) / count), held_on=float(sum(v for v in length.values() if v >= hold) / count),
               hold_frames=int(hold), followed_frames=len(fs), stretches=len(length), longest_stretch=max(length.values(), default=0),
               followed_jitter_px=None, scene_share=None, scene_moved_px=0.0, screen_share=None, screen_moved_px=0.0)
    # a place read off a held picture is the same reading again, to the last digit, not a second one: left out of the
    # scatter (PR29 holds each picture three or four frames, and a feature that jumped 5-10 px from one picture to the
    # next read as steady to 0.0 px)
    fresh = [n for i, n in enumerate(fs) if i == 0 or abs(got[n][0] - got[fs[i - 1]][0]) + abs(got[n][1] - got[fs[i - 1]][1]) > 1e-6]
    e = []
    for a, b, c in zip(fresh, fresh[1:], fresh[2:]):
        if runs[a] == runs[c]:
            h1, h2 = b - a, c - b
            e.append((rel[b] - (rel[a] * h2 + rel[c] * h1) / (h1 + h2)) / np.sqrt(1 + (h1 * h1 + h2 * h2) / (h1 + h2) ** 2))
    if len(e) >= 5:
        out["followed_jitter_px"] = float(1.4826 * np.median(np.abs(np.array(e))))
    sums = dict(scene=[0.0, 0.0], screen=[0.0, 0.0])
    for run in sorted({runs[n] for n in fs}):
        f = [n for n in fs if runs[n] == run and n in bg]
        if len(f) < 3:
            continue
        own = np.array([rel[n] for n in f])
        own = own - own.mean(0)
        at = np.array([track[n] for n in f], float)
        for name, v in (("scene", np.array([bg[n] for n in f], float) - at), ("screen", -at)):
            out[f"{name}_moved_px"] = max(out[f"{name}_moved_px"], float(np.hypot(*(v.max(0) - v.min(0)))))
            v = v - v.mean(0)
            sums[name][0] += float((own * v).sum())
            sums[name][1] += float((v ** 2).sum())
    for name, (num, den) in sums.items():
        if den > 0:
            out[f"{name}_share"] = num / den
    return out


def judge(c):
    """A followed candidate's verdict, written into it: `co_moving` when the control does not show it and,
    re-found frame by frame, it is held in stretches of HOLD frames on FOLLOWED of the frames, along a path
    smooth to STEADY px, making less than SCENE of the scene's motion against the object and of the screen's
    (each asked where it moved STILL px or more). Else why not: `scene`, `screen`, `seldom` or `jumps`."""
    c["scene"] = bool(c.get("scene_share") is not None and c["scene_moved_px"] >= STILL and c["scene_share"] >= SCENE)
    c["screen"] = bool(not c["scene"] and c.get("screen_share") is not None and c["screen_moved_px"] >= STILL
                       and c["screen_share"] >= SCENE)
    c["seldom"] = bool((c.get("held_on") or 0.0) < FOLLOWED)
    c["jumps"] = bool(not c["seldom"] and (c.get("followed_jitter_px") is None or c["followed_jitter_px"] > STEADY))
    c["co_moving"] = bool(c["not_on_control"] and not (c["scene"] or c["screen"] or c["seldom"] or c["jumps"]))
    return c["co_moving"]


def why_not(c):
    """Why a candidate is not the object's, in a few words; '' for one that moves with it."""
    if c.get("co_moving"):
        return ""
    return ("as sharp on the reversed track" if not c.get("not_on_control") else
            "the scene's, once followed" if c.get("scene") else
            "stays put on the screen, once followed" if c.get("screen") else
            "not held for long, once followed" if c.get("seldom") else
            "jumps about, once followed" if c.get("jumps") else "not followed")


def examine(clip, track, frames, cands, size=None, follow=(), progress=None, stop=None, keep=None):
    """One pass over the frames, and for the followed candidates a second, in reverse. For every candidate:
    `seen_on_frames` (the share of frames on which the feature is there at its own offset, FRAME_Z times
    the frame's noise, with the same sign) and `jitter_px` (where it is on those frames, across its own
    spread). And each candidate in `follow` (indices into cands) re-found frame by frame from the stack's
    offset (`Follower`: it is counted where it is seen and never followed away), with the background's own
    displacement since the first frame (`propose.background_shift`). Returns (cands, {index: {frame: (x, y,
    contrast)}}, bg); a followed candidate carries the stretches it was seen in as `_runs` ({frame:
    stretch}) and each way's own chain as `_ways`. `keep` is how near the object, in px, a re-found feature
    may be. The verdict is `judge`'s, from `followed_how`."""
    from .propose import background_shift
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    w = int(4 * SIGMA_OUT)
    hits, seen, where = np.zeros(len(cands)), np.zeros(len(cands)), [[] for _ in cands]
    follow = list(follow)
    bg, last, noises = {}, None, {}
    # nearer the object than `keep` px nothing is taken for a companion: the ring's inner edge where the stage gives
    # it (inside is the object's own picture; PR105's middle point, 15 px out, took the follower from the lower one)
    keep = max(0.6 * (size or 0), 2 * SIGMA_OUT) if keep is None else keep
    followers = {k: Follower(cands[k], keep) for k in follow}

    def alone(n, g, bad):          # what the pass needs of one frame alone: in the thread that read it (`Frames.each`)
        return wide_noise(g, bad, *track[n]), g.astype(np.float32) if follow else None

    def stepped(a, b, bad_a, bad_b):                        # the background's step from one frame to the next
        return background_shift(a, b, ~(bad_b | bad_a))
    # Each step of the background is read beside the pass (two frames each, no step needs another's), and they are
    # summed in the frames' order once the pass is through: the sums the pass made as it went.
    beside, steps, waiting = Beside(None if frames.procs is None else int(frames.procs)), [], deque()

    def looked(way, n, g, bad, noise, obj):                 # every follower's look at one frame, beside each other:
        jobs = [beside.call(f.look, way, n, g, bad, noise, obj) for f in followers.values()]     # each has its own state,
        for job in jobs:                                    # and the frame is not gone on from until all have looked
            job.result()
    try:
        for n, g, bad, (noise, g32) in frames.each(ns, progress, stop, "Frames", also=alone):
            ox, oy = track[n]
            if follow:
                job = None if last is None else beside.call(stepped, last[1], g32, last[2], bad)
                steps.append((n, None if last is None else last[0], job))
                if job is not None:
                    waiting.append(job)
                    while len(waiting) > 4 * BESIDE:            # never far ahead of the steps: each holds two frames
                        waiting.popleft().result()
                last = (n, g32, bad)
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
            if follow and noise > 0:
                noises[n] = noise
                looked(0, n, g, bad, noise, (ox, oy))
        for n, before, job in steps:
            if job is None:
                bg[n] = (0.0, 0.0)
            else:
                d = job.result()
                bg[n] = (bg[before][0] + d[0], bg[before][1] + d[1])
        if followers and noises:                        # and again in reverse: see Follower
            for n, g, bad in frames.each(ns[::-1], progress, stop, "Frames"):
                if n in noises:
                    looked(1, n, g, bad, noises[n], track[n])
    finally:
        beside.close()
    gots = {}
    for k, f in followers.items():
        got, cands[k]["_runs"] = f.merged()
        cands[k]["_ways"] = f.got
        gots[k] = {n: (track[n][0] + d[0], track[n][1] + d[1], d[3]) for n, d in got.items()}
    for k, c in enumerate(cands):
        c["seen_on_frames"] = float(hits[k] / seen[k]) if seen[k] else None
        pts = np.array(where[k]) if len(where[k]) >= 3 else None
        c["jitter_px"] = float(np.sqrt(max(np.linalg.eigvalsh(np.cov(pts.T)).min(), 0.0))) if pts is not None else None
    return cands, gots, bg


# ---- the swing ----------------------------------------------------------------------------
def _model(tt, A, T, ph, c, s):
    return A * np.sin(2 * np.pi * tt / T + ph) + c + s * (tt - tt.mean())


def _ls_power(t, Y, om):
    """The normalised Lomb-Scargle power of each row of `Y` (series at times `t`, their means taken out) at the
    angular frequencies `om`: what `scipy.signal.lombscargle(t, y, om, normalize=True)` gives a row, for all of
    them in two matrix products (the wander null asks it of 2,000 drawn series)."""
    wt = np.outer(om, t)
    tau = np.arctan2(np.sin(2 * wt).sum(1), np.cos(2 * wt).sum(1)) / 2
    c, sn = np.cos(wt - tau[:, None]), np.sin(wt - tau[:, None])
    p = (Y @ c.T) ** 2 / (c ** 2).sum(1) + (Y @ sn.T) ** 2 / (sn ** 2).sum(1)
    return p / (Y ** 2).sum(1, keepdims=True)


def wander_null(t, y, draws=None, seed=20261110, bins=None, min_in_bin=3):
    """Is the strongest period of the series `y` at times `t` (s) more than a slow wander would show?
    The series is put in bins of 1/WANDER_BINS of its span, or of 3.5 samples where that is wider (medians;
    `min_in_bin` samples a bin at the least), and a line is taken out. Its strongest Lomb-Scargle power
    between 4 bins and two thirds of the span is then ranked among the same statistic on `draws`
    Ornstein-Uhlenbeck series of the same variance and the same correlation between neighbouring bins,
    drawn at the same bin times, a line taken out of each. dict(p, period_s, power, cycles, r1, bins),
    or None where fewer than 12 bins are filled or too few of them are neighbours to read the wander's
    correlation. `p` is the share of the draws at least as strong: a wander's own slow excursions look
    like a cycle or two in a short window, and this is how often."""
    from scipy.signal import lombscargle
    draws, bins = draws or WANDER_DRAWS, bins or WANDER_BINS
    t, y = np.asarray(t, float), np.asarray(y, float)
    ok = np.isfinite(t) & np.isfinite(y)
    t, y = t[ok], y[ok]
    if len(t) < 12 * min_in_bin:
        return None
    span = float(t.max() - t.min())
    w = max(span / bins, 3.5 * float(np.median(np.diff(np.sort(t)))))
    if not w > 0:
        return None
    b = np.floor((t - t.min()) / w).astype(int)
    full = [k for k in np.unique(b) if (b == k).sum() >= min_in_bin]
    if len(full) < 12:
        return None
    T = np.array([t[b == k].mean() for k in full])
    Y = np.array([np.median(y[b == k]) for k in full])
    Y = Y - np.polyval(np.polyfit(T, Y, 1), T)
    per = np.linspace(4 * w, span / 1.5, 500)
    if not per[-1] > per[0]:
        return None
    om = 2 * np.pi / per
    P = lombscargle(T, Y - Y.mean(), om, normalize=True)
    i = int(np.argmax(P))
    d, yy = np.diff(T), Y - Y.mean()
    near = d < 1.6 * w
    if near.sum() < 8 or not np.sum(yy[:-1][near] ** 2) > 0:
        return None
    r1 = float(np.sum(yy[:-1][near] * yy[1:][near]) / np.sum(yy[:-1][near] ** 2))
    r1 = min(max(r1, 0.05), 0.995)
    tau, s = -float(np.median(d[near])) / np.log(r1), float(Y.std())
    a = np.exp(-d / tau)
    b = s * np.sqrt(1 - a ** 2)
    Z = s * np.random.default_rng(seed).standard_normal((draws, len(T)))     # every draw at once, a row each
    Z[:, 1:] /= s
    for q in range(1, len(T)):
        Z[:, q] = a[q - 1] * Z[:, q - 1] + b[q - 1] * Z[:, q]
    X = np.column_stack([T - T.mean(), np.ones(len(T))])                     # a line out of each
    Z -= Z @ X @ np.linalg.inv(X.T @ X) @ X.T
    mx = _ls_power(T, Z - Z.mean(1, keepdims=True), om).max(1)
    return dict(p=float((mx >= P[i]).mean()), period_s=float(per[i]), power=float(P[i]), cycles=float(span / per[i]),
                r1=r1, bins=len(T), draws=int(draws))


def _share(p):
    """A share of the wander draws as a per cent: '55%', '1.7%'; under one draw in a thousand, 'under 0.1%'."""
    return "under 0.1%" if p < 0.001 else f"{100 * p:.{0 if p >= 0.095 else 1}f}%"


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
    mid = float(np.degrees(np.arctan2(sx.mean(), sy.mean())))     # about its mean direction: a companion straight above
    ang = mid + (ang - mid + 180.0) % 360.0 - 180.0               # the object sits at +-180, and must not wrap there
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
    # a period, by the cycles in the window: now against a slow wander of the angle's own size and correlation, which
    # shows a cycle or two in a short window most of the time (AARO's known balloon PR-004: "2.0 m" from two 6-7-s windows)
    null = out["wander"] = wander_null(t, ang)
    if null is None or null["p"] > WANDER_P:
        out.update(swings=False, tentative=False, line_length_m=None, period_refused_s=float(T))
        if null is None:
            why = (f"a period of {T:.2f} s fits, but the companion is seen on too few frames, too far apart, to tell that "
                   "from a slow wander")
        else:
            why = (f"its strongest period, {null['period_s']:.2f} s, is no stronger than a slow wander of the same size and "
                   f"correlation shows {_share(null['p'])} of the time (a swing is claimed under {100 * WANDER_P:g}%)")
        out["finding"] = f"the companion's angle does not swing: {why}; no line length from it"
        return out
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
        npw.append(("tether: a feature on the object or on the screen",
                    f"the object moves only {moved:.0f} px on the screen over these frames: what is tied to it "
                    "cannot be told from the overlay or the scene, which stay as sharp"))
    sw, followed, best, bg = None, {}, None, {}
    inner, outer = r_min_used * size, min(r_max * size, float(R))
    fields["searched_px"] = [float(inner), float(outer)]
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
        c0.update(followed_how(ns, followed, c0["_runs"], track, bg, repeats))
        judge(c0)
        sw = swing(track, followed, clip.fps, repeats)
        sw.update(seed=[float(seed[0]), float(seed[1])], dark=c0["sign"] == "dark",
                  **{k: c0[k] for k in ("followed_on", "followed_jitter_px", "scene_share", "scene_moved_px", "screen_share", "screen_moved_px")})
        how = c0
    else:
        # every candidate gets its single-frame support, and the strongest the control does not show are re-found
        # frame by frame from where the stack put them, in the same pass and its reverse. One that is held there
        # in long stretches, along a smooth path, and moves neither with the scene nor with the screen moves with
        # the object (`judge`); the one held on most frames, and of those the nearest, is the companion. The others are marked.
        follow = [k for k, c in sorted(enumerate(cands), key=lambda kc: -kc[1]["z"]) if c["not_on_control"]][:FOLLOW]
        cands, gots, bg = examine(clip, track, frames, cands, size, follow=follow, progress=progress, stop=stop, keep=inner)
        for k in follow:
            cands[k].update(followed_how(ns, gots[k], cands[k]["_runs"], track, bg, repeats))
            judge(cands[k])
        # of those held about as well (to a tenth of the frames), the nearest to the object: what is tied to it is likelier
        # near it than a neighbour 40 sizes off (PR097 object 6 has both), and a swinging payload's several stack peaks
        # along its arc each lead their follower to the same payload
        with_it = sorted((k for k in follow if cands[k]["co_moving"]), key=lambda k: (-round(cands[k]["held_on"], 1), cands[k]["r_px"]))
        if with_it:
            best, followed = cands[with_it[0]], gots[with_it[0]]
            best["followed"] = True
            sw = swing(track, followed, clip.fps, repeats)
            sw.update(seed=[best["dx_px"], best["dy_px"]], dark=best["sign"] == "dark")
        how = best
    cands = sorted(cands, key=lambda c: (not c["co_moving"], -(c.get("followed_on") or 0), -(c["seen_on_frames"] or 0), -c["z"]))
    cands = [c for c in cands if c["co_moving"]][:8] + [c for c in cands if not c["co_moving"]][:3]
    fields["candidates"] = [{k: v for k, v in c.items() if not k.startswith("_")} for c in cands]
    fields["companion"] = {k: v for k, v in best.items() if not k.startswith("_")} if best else None
    fields["swing"] = sw                            # the companion's, or the seed's: never a candidate's that was refused
    ring = f"between {inner:.0f} and {outer:.0f} px of it ({r_min_used:.1f} to {r_max:g} object sizes)"
    if seed is None and best is None:
        scene = [c for c in cands if c.get("scene") or c.get("screen")]
        if not np.isfinite(sig):
            finding = "the stack is too small to ask"
        elif scene:
            c = scene[0]
            finding = (f"the stack's feature(s) move with the {'scene' if c.get('scene') else 'screen'}, not the object (the "
                       f"{'scene' if c.get('scene') else 'screen'} moves {c['scene_moved_px' if c.get('scene') else 'screen_moved_px']:.0f} px "
                       f"against the object over the frames they were followed on); nothing tied to the object {ring}")
        else:
            finding = f"nothing moves with the object {ring} at {Z_MIN:g} x the stack's noise ({sig:.1f} DN)"
            if cands:
                finding += (f"; the {len(cands)} strongest feature(s) are as sharp on the reversed track, or not there from frame to "
                            "frame: the frame or the scene, not the object")
        if np.isfinite(sig):
            finding += f"; nearer than {inner:.0f} px is the object's own picture, and was not searched"
    else:
        if best is not None:
            finding = (f"a {best['sign']} feature moves with the object {best['r_px']:.0f} px ({best['r_over_size']:.1f} object "
                       f"sizes) away at {best['direction_deg']:+.0f} deg from straight down, {best['z']:.1f} x the noise "
                       f"({best['z_control']:.1f} on the reversed track), re-found on {100 * best['followed_on']:.0f}% of the frames "
                       f"to {best['followed_jitter_px']:.1f} px")
        else:
            finding = (f"companion followed from the given offset {tuple(round(v) for v in seed)} on "
                       f"{100 * how['followed_on']:.0f}% of the frames")
        if sw:
            finding += "; " + sw["finding"]
            if max(how.get("scene_moved_px") or 0.0, how.get("screen_moved_px") or 0.0) < STILL:
                npw.append(("tether: with the object or with the scene",
                            f"the object moves only {max(how.get('scene_moved_px') or 0.0, how.get('screen_moved_px') or 0.0):.0f} px "
                            "against the scene and the screen over the frames the feature was followed on: a feature of the scene "
                            "or the screen at that offset cannot be told from a feature tied to the object"))
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
                        "frames", "seen_on_frames", "jitter_px", "co_moving", "scene", "followed_on", "followed_jitter_px",
                        "scene_share", "scene_moved_px", "screen_share", "screen_moved_px", "why_not"])
            num = lambda v, n: "" if v is None else round(v, n)
            for c in cands:
                w.writerow([round(c["dx_px"], 1), round(c["dy_px"], 1), round(c["r_px"], 1), round(c["r_over_size"], 2),
                            round(c["direction_deg"], 1), c["sign"], num(c.get("contrast_dn"), 1), num(c.get("z"), 1),
                            num(c.get("z_control"), 1), c["frames"], num(c.get("seen_on_frames"), 2), num(c.get("jitter_px"), 1),
                            c["co_moving"], bool(c.get("scene")), num(c.get("followed_on"), 2), num(c.get("followed_jitter_px"), 2),
                            num(c.get("scene_share"), 2), num(c.get("scene_moved_px"), 0), num(c.get("screen_share"), 2),
                            num(c.get("screen_moved_px"), 0), why_not(c)])
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
    """Left: the object-centred stack with the candidates ringed (solid red: moves with the object;
    dashed amber: not the object's). Middle: the reversed-track control. Right: the companion's angle,
    frame by frame. In the house style (figures.setup)."""
    from matplotlib.lines import Line2D
    from . import figures
    plt = figures.setup()
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.6), constrained_layout=True)
    fig.get_layout_engine().set(w_pad=0.1, wspace=0.06)      # room for the angle's label beside the pictures
    crop = int(min(R, max(60, (max((c["r_px"] for c in cands), default=0) + 4 * size), 6 * size)))
    for ax, img, title in ((axes[0], m, "Stacked on the object"), (axes[1], mc, "Check: the track run backwards")):
        sub = img[R - crop:R + crop + 1, R - crop:R + crop + 1]
        lo, hi = np.nanpercentile(sub, [1, 99])
        ax.imshow(sub, cmap="gray", vmin=lo, vmax=hi, extent=(-crop, crop, crop, -crop))
        ax.set_title(title)
        ax.set_xlabel("Distance from the object (pixels)")
    for c in cands:
        axes[0].add_patch(plt.Circle((c["dx_px"], c["dy_px"]), 2.5 * SIGMA_OUT, fill=False, lw=1.4,
                                     ec=figures.RED if c["co_moving"] else figures.AMBER, ls="-" if c["co_moving"] else "--"))
    kinds = [(figures.RED, "-", "moves with the object")] * any(c["co_moving"] for c in cands) + \
            [(figures.AMBER, "--", "does not")] * any(not c["co_moving"] for c in cands)
    if kinds:
        axes[0].legend(handles=[Line2D([], [], color=col, ls=ls, lw=1.4, marker="o", mfc="none", ms=7, label=lab)
                                for col, ls, lab in kinds], loc="best")
    ax = axes[2]
    if followed and sw and "angle_mean_deg" in sw:
        ns = sorted(n for n in followed if n in track and n not in repeats)
        t = np.array([(n - ns[0]) / fps for n in ns])
        sx, sy = np.array([(followed[n][0] - track[n][0], followed[n][1] - track[n][1]) for n in ns]).T
        mid = float(np.degrees(np.arctan2(sx.mean(), sy.mean())))
        ang = mid + (np.degrees(np.arctan2(sx, sy)) - mid + 180.0) % 360.0 - 180.0
        ax.plot(t, ang, "o", ms=2.5, color=figures.BLUE, label="the companion")
        ax.set_title("Angle of the companion")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Angle (degrees, + is right)")
    else:
        ax.text(0.5, 0.5, "no companion followed", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    figures.save(fig, path, dpi=200)
    plt.close(fig)


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
                 + (f"{c['jitter_px']:.0f} px" if c.get("jitter_px") is not None else "n/a")
                 + (f"; re-found on {100 * c['followed_on']:3.0f}%, held on {100 * c['held_on']:3.0f}%"
                    + (f", to {c['followed_jitter_px']:.1f} px" if c.get("followed_jitter_px") is not None else "")
                    if c.get("followed_on") is not None else "") + " -> " + (why_not(c) or "moves with the object"))
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
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>; with --n0/--n1, the segment's own folder in it, <tag>/segment-<n0>-<n1>)")
    ap.add_argument("--procs", type=int, default=None, help=PROCS_HELP)
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        found, clip = _main(args)
    code = vf.EXIT_NOTHING if any(t.startswith("tether: a feature") or t == "tether" for t, _ in found.no_power) else 0
    if args.json:
        emit(found.envelope("tether", inputs_of(args), clip, said=lines, exit_code=code, error=None))
    return code


def _main(args):
    video, tag, _ = vf.resolve(args.video)
    track = vf.read_track(args.track)
    n0 = args.n0 if args.n0 is not None else min(track)
    n1 = args.n1 if args.n1 is not None else max(track)
    clip = vf.Clip(video, args.workdir, n0, n1)
    out = vf.out_prefix(args.out, tag, vf.named(args.n0, args.n1, clip))
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
