"""`mcdonald events` — the overlay's own events, found from its pixels: when a readout changes, when a clock ticks,
when the gate round the object collapses, grows or vanishes, and when the whole picture steps (a gain reset, a switch
between the infrared and the television camera, frames held).

A step in an object's rate within a few frames of one of the camera's own events is the camera's until shown otherwise
(`mcdonald camera`): a published fit of the Navy's 2004 FLIR1 ended its "acceleration" on the frame the picture zoomed,
and its other steps came where the gate collapsed, where a new gate grew and where the zoom readout changed. Those
events were given by hand (`camera --events`). Here they are found:

- **Text and readouts.** The overlay's text is found in a sample of frames as thin strokes on the symbology's side of
  the picture (`forensics.strokes`, a top-hat), joined along a line into boxes of a glyph's height, two strokes or more
  and away from the object's path. Each box (or each given with `--box`) is followed through every frame by its
  strokes, and a change is where the mean of the six frames before a frame and the six from it differ, in any
  glyph-sized cell of the box, by eight sigmas of that cell's own noise through the clip (`change_score`). Each change is then timed frame by frame against the box's looks either side, as
  `mcdonald readout` times a tick, with its dithering counted. On FLIR1 (2026-10-20) the box found for the pod's
  azimuth times 12 of the 13 ticks read by hand to the half frame, and the 13th (1 R to 1 L, at 1034.5) within 4.
  Values are not read -- that is `mcdonald readout`'s, with a person reading the strip -- but every change is timed.
  A change in three boxes or more at once is the overlay's as a whole; one within two frames of a step of the whole
  picture is the picture's; a box whose changes are mostly long back-and-forth runs has something moving in it and is
  not a readout.
- **Clocks.** A box that changes once a second, steadily, is a clock. Its ticks are no camera event, but they are a
  second ruler: frames held or dropped show as ticks that come early or late, and the frame rate as their spacing.
- **The gate.** With a track, the strokes in a ring round the object: how many, and how far out. A gate that vanishes,
  one that grows or shrinks (a ratio held on both sides), and one that appears.
- **The picture.** The scene's level and contrast in the middle of the frame, stepping and staying (a gain reset, a
  switch of camera), runs of contrast collapse (`forensics.transients`), and runs of held frames.

What it cannot do: say why the overlay changed (a tracker that let go and an operator who switched it off draw the same
collapse), read a value, or find symbology drawn in the scene's own grey on a busy scene. A box whose text is moved
behind (a readout that scrolls) changes on every frame and is reported as such, not as events.
"""
import csv
import math
from pathlib import Path

import numpy as np
from scipy import ndimage

from . import forensics as vf
from .report import Found

SAMPLE = 41            # frames spread over the window: where the text is
WIN = 6                # frames: a box's mean over the WIN before a frame against the WIN from it
K_MAD = 8.0            # a change stands this many sigmas of a cell's noise over its level (`change_score`)
TOGETHER = 3           # boxes: a change in this many at once (within WITH_PICTURE frames) is the overlay's, not a readout's
KEEP_PX = 600          # a box's strokes are kept shrunk to at most this many pixels a frame
NEAR = 15              # frames: a box that goes back to the look it left within this many frames dithers
MAX_LOOKS = 120        # a box with more looks than this is not a readout (text scrolled, the scene behind)
WITH_PICTURE = 2       # frames: a box's change this close to a step of the whole picture is the picture's (FLIR1's
                         # zoom steps the picture at 2235 and its readout at 2238, and both are timed to a frame)
CLOCK_TOL = 0.12       # a box whose changes come every second, to this share, is a clock
GATE_RATIO = 1.6       # the gate's strokes or its size stepping by this much, held on both sides, is a gate event
GATE_HOLD = 4          # frames either side over which a gate step must hold
SCENE_HOLD = 8         # frames either side over which a step in the picture's level must hold
SCENE_K = 6.0          # and its size, in MADs of the level's own frame-to-frame changes
RING = 1               # px at 240 rows (scaled with the height) round the dark that text is not looked for in
RULE_GLYPHS = 3        # a straight stroke this many glyphs long, beside the dark, is a rule (a border), not text


# ---- strokes ------------------------------------------------------------------------------------
strokes = vf.strokes


def _noise(a):
    hp = a - ndimage.uniform_filter(a, 5)
    return float(1.4826 * np.median(np.abs(hp - np.median(hp))))


def text_strokes(stack, H, masks=None):
    """Where the overlay's text may be, from a sample of frames' strokes (`stack`): where strokes stand in at least a
    quarter of the frames, less the dark that holds in nearly every frame (`static_masks`' `blocks_raw`: a redaction, a
    display's black surround, a black sky) and a ring of RING px round it, and less the straight lines (RULE_GLYPHS
    glyphs long or more) that run along that dark for most of their length (a picture's border, a box drawn round a
    word). Not less `blocks` itself, the dark grown by 8 px against a
    redaction's codec ringing: text drawn against a border is within 8 px of it (FLIR1's field of view, `NAR`, under the
    picture's top edge; all of GIMBAL's top line, its azimuth among it, on a sky black above the clouds), and on PURSUE's
    redacted clips (PR27, PR144) the boxes found are the same either way (2026-10-20)."""
    q = np.percentile(stack, 75, axis=0)
    on = q > max(12.0, 4.0 * _noise(q))
    if masks is None:
        return on
    dark = masks.get("blocks_raw")
    if dark is None:                                     # masks made without their parts: the grown dark is all there is
        return on & ~masks["blocks"] if masks.get("blocks") is not None else on
    gh = max(5, round(7 * H / 240))
    ring = max(1, round(RING * H / 240))
    R = RULE_GLYPHS * gh
    line = ndimage.binary_opening(on, np.ones((1, R), bool)) | ndimage.binary_opening(on, np.ones((R, 1), bool))
    # a line goes whole where most of it runs along the dark, within a stroke's reach (a border, blurred over several px);
    # a line of the scene that only meets a redaction box at one end stays, and keeps its neighbours in one large group
    lab, n = ndimage.label(line, structure=np.ones((3, 3), bool))
    if n:
        along = ndimage.binary_dilation(dark, iterations=ring + 2 * vf.stroke_step(H) + 1)
        share = ndimage.mean(along, lab, np.arange(1, n + 1))
        rules = np.isin(lab, 1 + np.flatnonzero(share >= 0.5))
        on &= ~ndimage.binary_dilation(rules, iterations=1)
    return on & ~ndimage.binary_dilation(dark, iterations=ring)


def find_boxes(stack, H, W, masks=None, most=24):
    """Boxes of text in a sample of frames' strokes (`stack`: the strokes of each frame): where text may be
    (`text_strokes`), joined across the gaps between glyphs and words, and kept where the group is the size of a line
    of text -- 2-9 % of the frame's height (7 px of FLIR1's 240 rows, 30 of GOFAST's 1080), at least half as wide as
    high, and its strokes neither a single line nor a block -- unless they are one band a glyph high and two or more
    wide (`_band`: a word the copy has blurred together). Strokes are joined along a line only: a label written down
    the side (FLIR1's `ZOOM`) is not one box with the readout beside it. [(x0, y0, x1, y1)], the largest first."""
    on = text_strokes(stack, H, masks)
    gh = max(5, round(7 * H / 240))
    joined = ndimage.binary_dilation(on, structure=np.ones((1, max(3, gh)), bool))   # along the line only
    lab, n = ndimage.label(joined)
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if not (0.02 * H <= h <= 0.09 * H and w >= 0.5 * h):
            continue
        fill = float(on[sl][lab[sl] == i].mean())
        if not (0.08 <= fill <= 0.6 or _band(on[sl] & (lab[sl] == i), H)):
            continue
        pad = max(2, gh // 4)
        out.append((max(0, sl[1].start - pad), max(0, sl[0].start - pad), min(W, sl[1].stop + pad), min(H, sl[0].stop + pad)))
    out.sort(key=lambda b: -(b[2] - b[0]) * (b[3] - b[1]))
    return out[:most]


def where(box, W, H):
    """A box's place on the screen in words: `top left`, `middle right`, ..."""
    cx, cy = (box[0] + box[2]) / 2 / W, (box[1] + box[3]) / 2 / H
    row = "top" if cy < 1 / 3 else "bottom" if cy > 2 / 3 else "middle"
    col = "left" if cx < 1 / 3 else "right" if cx > 2 / 3 else "centre"
    return f"{row} {col}" if (row, col) != ("middle", "centre") else "centre"


# ---- a box through the clip ---------------------------------------------------------------------
class BoxSeries:
    """A box's strokes on every frame, kept small: shrunk to at most KEEP_PX pixels and stored as bytes, so that a box
    of a 10-minute 1080p clip is a few megabytes."""

    def __init__(self, box, name="", glyph=7):
        self.box, self.name = box, name
        w, h = box[2] - box[0], box[3] - box[1]
        self.f = max(1, int(math.ceil(math.sqrt(w * h / KEEP_PX))))
        self.cell = max(2, int(round(glyph / self.f)))   # a glyph's height, in the kept pixels
        self.frames, self.data = [], []

    def push(self, n, s):
        f = self.f
        if f > 1:
            h, w = s.shape[0] // f * f, s.shape[1] // f * f
            s = s[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))
        self.frames.append(n)
        self.data.append(np.clip(s, 0, 255).astype(np.uint8))

    def array(self):
        return np.stack(self.data).astype(np.float32) if self.data else np.zeros((0, 1, 1), np.float32)


def two_window(A, w=WIN, cell=None):
    """The squared difference between the mean of the w frames before frame i and the w from it -- a change at i stands
    out of the noise about w times more than frame against frame would -- averaged over each `cell` x `cell` square
    of the box: (frames x cells). One digit changing in a line of text is then not lost in the rest of it (FLIR1's
    azimuth box, `8° L` with `IR` above it, lost three of its ticks averaged whole)."""
    n, h, wd = A.shape
    c = int(cell or max(h, wd))
    ch, cw = max(1, -(-h // c)), max(1, -(-wd // c))
    D = np.full((n, ch * cw), np.nan)
    if n < 2 * w + 1:
        return D
    cs = np.concatenate([np.zeros((1, h, wd), np.float64), np.cumsum(A, 0, dtype=np.float64)])
    pad = np.zeros((ch * c, cw * c))
    cnt = np.zeros((ch * c, cw * c))
    cnt[:h, :wd] = 1
    cnt = cnt.reshape(ch, c, cw, c).sum(axis=(1, 3)).ravel()
    for i in range(w, n - w + 1):
        pad[:h, :wd] = (((cs[i + w] - cs[i]) - (cs[i] - cs[i - w])) / w) ** 2
        D[i] = pad.reshape(ch, c, cw, c).sum(axis=(1, 3)).ravel() / np.maximum(cnt, 1)
    return D


def change_score(D, k=K_MAD, w=WIN):
    """Each cell's two-window difference, as the logarithm of it plus its 20th percentile through the clip, in sigmas of
    its noise over the noise's level, and the largest cell's. The noise is read from the lower part of the distribution
    (its 5th to 40th percentiles: for noise alone sigma is (P40 - P5) / 1.39, and its middle P20 + 0.84 sigma); the
    logarithm tames the long tail a codec's own rhythm gives the differences. A change scores K_MAD or more.

    Then once more, from the quiet frames alone: those more than `w` from a change the first pass found. A readout that
    ticks every 20 frames, as GIMBAL's azimuth does, keeps the windows' difference up on some 12 frames of every 20, and
    even the lower part of its distribution is then partly the changes': the ticks of many segments stood out of it and
    those of one or two did not (53 -> 52, 46 -> 45, 43 -> 42). Read from its quiet frames, GIMBAL's azimuth gives 12 of
    its 13 ticks within a frame in its first 300, where it gave 9, and GOFAST loses a change where none is (the sea
    behind its text); FLIR1's azimuth still times 12 of its 13 ticks to the half frame (2026-10-20, night). A third pass
    found a change where none is on GIMBAL. Set at 8 on FLIR1 and GIMBAL (2026-10-20); the whole series' median and MAD
    found 6 of GIMBAL's ticks."""
    ok = np.isfinite(D).all(axis=1)
    if ok.sum() < 5:
        return np.full(len(D), np.nan)

    def score(use):
        floor = np.percentile(D[use], 20, axis=0)
        p5, p20, p40 = np.percentile(np.log(D[use] + floor + 1e-6), [5, 20, 40], axis=0)
        sig = (p40 - p5) / 1.39 + 1e-6
        z = np.full(len(D), np.nan)
        z[ok] = ((np.log(D[ok] + floor + 1e-6) - (p20 + 0.84 * sig)) / sig).max(axis=1)
        return z
    z = score(ok)
    quiet = ok.copy()
    for i in np.flatnonzero(np.nan_to_num(z, nan=-np.inf) >= k):
        quiet[max(0, i - w):i + w + 1] = False
    return score(quiet) if quiet.sum() >= 20 and quiet.sum() < ok.sum() else z


def changes_of(series, w=WIN, k=K_MAD):
    """A box's changes: peaks of `change_score` at k MADs or more, each the largest within w frames. Then the looks
    between them (the mean of each stretch, stretches that look alike being one look) and, for each change, the look
    before and after, the tick timed frame by frame and its dither. Returns ([(tick frame, from, to, dither frames)],
    [(first, last, look)], number of looks, k)."""
    A = series.array()
    fr = np.array(series.frames)
    Dc = two_window(A, w, cell=series.cell)
    z = change_score(Dc, k, w)
    ok = np.isfinite(z)
    if ok.sum() < 5:
        return [], [], 0, None
    pk = [i for i in range(len(z)) if ok[i] and z[i] >= k and z[i] == np.nanmax(z[max(0, i - w):i + w + 1])]
    # two stretches are one look only where they differ by under a quarter of the smallest change found: a look's letter
    # must never stand for two values (GIMBAL's 49 and 46 L were one look at half), while one value under two letters
    # costs the person reading the sheet nothing
    D = np.full(len(Dc), np.nan)
    D[ok] = Dc[ok].max(axis=1)
    same = 0.25 * min((D[i] for i in pk), default=np.inf)
    cuts = [0] + pk + [len(A)]
    means = [A[a:b].mean(0) for a, b in zip(cuts[:-1], cuts[1:])]
    looks, ids = [], []
    for m in means:
        # a stretch is never the look of the one before it: a change was found between them (GOFAST's 38 and 39 L,
        # a stroke apart, were one look before)
        d = [float(two_cells(m, L, series.cell).max()) if not (ids and q == ids[-1]) else np.inf
             for q, L in enumerate(looks)]
        j = int(np.argmin(d)) if d else -1
        if d and d[j] < same:
            ids.append(j)
        else:
            looks.append(m)
            ids.append(len(looks) - 1)
    ch = []
    for j, i in enumerate(pk):
        if ids[j] == ids[j + 1]:
            continue
        # frame by frame near the change, against the two looks either side, as `readout` times a tick: the tick at the
        # half frame with the fewest frames on the wrong side, and the frames between the first that looks new and the
        # last that looks old (a readout dithering between two values, which the windows' means smooth over)
        a, b = looks[ids[j]], looks[ids[j + 1]]
        lo, hi = max(cuts[j], i - NEAR), min(cuts[j + 2], i + NEAR)
        new = np.array([two_cells(A[m], b, series.cell).max() < two_cells(A[m], a, series.cell).max()
                        for m in range(lo, hi)])
        wrong = np.array([new[:q].sum() + (~new[q:]).sum() for q in range(len(new) + 1)])
        q = int(np.argmin(wrong))
        fn, fo = np.flatnonzero(new), np.flatnonzero(~new)
        first_new = int(fr[lo + fn.min()]) if len(fn) else int(fr[min(lo + q, hi - 1)])
        last_old = int(fr[lo + fo.max()]) if len(fo) else int(fr[max(lo + q - 1, lo)])
        ch.append((float(fr[lo]) + q - 0.5, ids[j], ids[j + 1], max(0, last_old - first_new + 1)))
    runs = [(int(fr[a]), int(fr[b - 1]), ids[k]) for k, (a, b) in enumerate(zip(cuts[:-1], cuts[1:]))]
    return ch, runs, len(looks), float(k)


def two_cells(a, b, cell):
    """The mean squared difference of two looks of a box over each `cell` x `cell` square: [cells]."""
    h, w = a.shape
    c = int(cell or max(h, w))
    ch, cw = max(1, -(-h // c)), max(1, -(-w // c))
    pad, cnt = np.zeros((ch * c, cw * c)), np.zeros((ch * c, cw * c))
    pad[:h, :w], cnt[:h, :w] = (np.asarray(a, float) - b) ** 2, 1
    return pad.reshape(ch, c, cw, c).sum(axis=(1, 3)).ravel() / np.maximum(cnt.reshape(ch, c, cw, c).sum(axis=(1, 3)).ravel(), 1)


def ticks(changes):
    """A box's changes as ticks: [{frame, from, to, dither_frames}] -- the tick at the half frame `changes_of` timed it
    to, and how many frames it went back and forth between the two looks."""
    return [dict(frame=float(t), **{"from": int(a)}, to=int(b), dither_frames=int(d)) for t, a, b, d in changes]


def clock(tk, fps):
    """Is a box's run of ticks a clock -- once a second, steadily? {period_frames, fps_from_clock, early_late} or None.
    `early_late` lists the ticks more than a frame and a half from the steady second: frames held or dropped there."""
    if len(tk) < 4:
        return None
    t = np.array([x["frame"] for x in tk])
    gaps = np.diff(t)
    med = float(np.median(gaps))
    if abs(med - fps) > CLOCK_TOL * fps or np.mean(np.abs(gaps - med) <= 0.25 * fps) < 0.7:
        return None
    k = np.round((t - t[0]) / med)
    p = np.polyfit(k, t, 1)
    off = t - np.polyval(p, k)
    return dict(period_frames=float(p[0]), fps_from_clock=float(p[0]), ticks=len(tk),
                early_late=[dict(frame=float(f), off_frames=float(o)) for f, o in zip(t, off) if abs(o) > 1.5])


# ---- the gate and the picture -----------------------------------------------------------------
def _held_step(v, hold, ratio):
    """Frames where a series steps by `ratio` (as a ratio of values + 1) and holds for `hold` frames either side:
    [(index, before, after)], one per step (the largest in a run)."""
    v = np.asarray(v, float)
    out, best = [], None
    for i in range(hold, len(v) - hold + 1):
        b, a = np.median(v[i - hold:i]), np.median(v[i:i + hold])
        r = (a + 1) / (b + 1)
        steady = (np.abs(v[i - hold:i] - b) <= 0.5 * (b + 1)).all() and (np.abs(v[i:i + hold] - a) <= 0.5 * (a + 1)).all()
        if steady and max(r, 1 / r) >= ratio:
            if best is None or i - best[0] > hold:
                if best:
                    out.append(best)
                best = (i, b, a, max(r, 1 / r))
            elif max(r, 1 / r) > best[3]:
                best = (i, b, a, max(r, 1 / r))
    if best:
        out.append(best)
    return [(i, b, a) for i, b, a, _ in out]


def gate_series(g, x, y, size, polarity=1, static=None):
    """The strokes in a ring round the object at (x, y) in the frame g: (how many pixels, their rms distance from it).
    The ring runs from just outside the object to three times its size or 0.08 of the frame's height (FLIR1's gate: its
    bars 7 px either side of a 7-px object at 240 rows, 14 at its x2), and a stroke stands four noises out of it."""
    H, W = g.shape
    r_in, r_out = max(3.0, 0.8 * size), max(3.0 * size, 0.08 * H)
    R = int(math.ceil(r_out))
    x0, x1, y0, y1 = max(0, int(x) - R), min(W, int(x) + R + 1), max(0, int(y) - R), min(H, int(y) + R + 1)
    if x1 <= x0 or y1 <= y0:
        return 0.0, 0.0
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.hypot(xx - x, yy - y)
    s = strokes(g[y0:y1, x0:x1], polarity, H)
    on = (s > max(12.0, 4.0 * _noise(s))) & (d >= r_in) & (d <= r_out)
    if static is not None:
        on &= ~static[y0:y1, x0:x1]
    if not on.any():
        return 0.0, 0.0
    return float(on.sum()), float(np.sqrt((d[on] ** 2).mean()))


# ---- the stage --------------------------------------------------------------------------------
def _band(on, H):
    """Is a crop's strokes one band a glyph high (2 % of the frame's height to 1.3 glyphs) and two glyphs wide or more,
    filling most of its own box, with little else beside it? A word whose letters the copy has blurred together: at
    352 x 240 the top-hat's opening (7 px) is taller than FLIR1's glyphs, and its `NAR` is a single stroke that fills
    0.74 of its box. At 1080 rows the opening is a third of a glyph, and text makes no such band."""
    gh = max(5, round(7 * H / 240))
    lab, n = ndimage.label(on, structure=np.ones((3, 3), bool))
    if not n:
        return False
    sizes = ndimage.sum(on, lab, np.arange(1, n + 1))
    k = int(np.argmax(sizes))
    sl = ndimage.find_objects(lab)[k]
    h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
    return bool(0.02 * H <= h <= 1.3 * gh and w >= 2 * gh and (lab[sl] == k + 1).mean() >= 0.6
                and sizes[k] >= 0.8 * sizes.sum())


def _texty(on, box):
    """Is a box of strokes a line of text, and not a reticle's bar or a bracket: two or more separate strokes, and no
    one of them as wide as most of a box over three times as wide as it is high -- or one band of blurred text?"""
    x0, y0, x1, y1 = box
    lab, n = ndimage.label(on[y0:y1, x0:x1], structure=np.ones((3, 3), bool))
    if n < 2:
        return _band(on[y0:y1, x0:x1], on.shape[0])
    widths = [sl[1].stop - sl[1].start for sl in ndimage.find_objects(lab)]
    return not (x1 - x0 > 3 * (y1 - y0) and max(widths) > 0.8 * (x1 - x0))


def find(clip, track=None, size=9.0, boxes=None, names=None, masks=None, out=None, tag="", progress=None):
    """The overlay's events over the clip's window: a Found whose fields hold the boxes (each with its stretches and
    ticks, and whether it is a clock), the gate's steps, the picture's steps, held runs and transients, and `events`:
    [{frame, what, kind}] sorted, the clocks' ticks left out. `boxes` are given [(x0, y0, x1, y1)] (with `names`), else
    found: lines of text away from the object's path."""
    H, W = clip.H, clip.W
    frames = list(clip.frames())
    masks = masks if masks is not None else vf.static_masks(clip)
    polarity = vf.overlay_polarity(masks) or 1
    static = masks.get("graphics_raw")
    found_boxes = boxes is None
    if found_boxes:
        sample = sorted(set(np.linspace(clip.n0, clip.n1, min(SAMPLE, len(frames))).astype(int).tolist()))
        st = np.stack([strokes(clip.grey(n), polarity, H) for n in sample])
        on = text_strokes(st, H, masks)                  # the strokes the boxes were found in, borders out
        boxes = [b for b in find_boxes(st, H, W, masks) if _texty(on, b)]
        if track:                                        # the object, its gate and what it passes are not text
            xs, ys = np.array([p[0] for p in track.values()]), np.array([p[1] for p in track.values()])
            pad = 2.0 * max(size, 6.0)
            boxes = [b for b in boxes if not np.any((xs >= b[0] - pad) & (xs <= b[2] + pad) & (ys >= b[1] - pad)
                                                     & (ys <= b[3] + pad))]
    boxes = list(boxes)
    names = list(names) if names else [f"{where(b, W, H)} ({b[0]},{b[1]})-({b[2]},{b[3]})" for b in boxes]
    seg = [BoxSeries(b, nm, glyph=max(5, round(7 * H / 240))) for b, nm in zip(boxes, names)]
    pol_box = [polarity if found_boxes else vf.text_polarity(clip.grey(clip.n0)[b[1]:b[3], b[0]:b[2]]) for b in boxes]
    pos = vf.interp_track(track) if track else None
    gate, level, prev, held = [], [], None, []
    h0, h1, w0, w1 = H // 7, 6 * H // 7, W // 9, 8 * W // 9
    ok = np.ones((h1 - h0, w1 - w0), bool)
    if masks.get("blocks") is not None:
        ok &= ~(masks["blocks"] | masks["graphics"])[h0:h1, w0:w1]
    for b in boxes:
        ok[max(0, b[1] - h0):max(0, b[3] - h0), max(0, b[0] - w0):max(0, b[2] - w0)] = False
    if not ok.any():
        ok[:] = True
    for i, n in enumerate(frames):
        if progress and i % 50 == 0:
            progress("Overlay events", i, len(frames))
        g = clip.grey(n)
        for s_, pb in zip(seg, pol_box):
            x0, y0, x1, y1 = s_.box
            s_.push(n, strokes(g[y0:y1, x0:x1], pb, H))
        mid = g[h0:h1, w0:w1]
        level.append((n, float(np.median(mid[ok])), float(mid[ok].std())))
        if prev is not None:
            held.append((n, float(np.abs(mid - prev)[ok].mean())))
        prev = mid
        if pos is not None and min(track) - 2 <= n <= max(track) + 2:
            x, y = track[n] if n in track else pos(n)
            gate.append((n,) + gate_series(g, x, y, size, polarity, static))
    # the whole picture first: its steps, held runs and contrast collapses are what the boxes' changes are set against
    events, picture_frames = [], []
    Lv = np.array(level)
    scene_steps = []
    for idx, what in ((1, "level"), (2, "contrast")):
        v = Lv[:, idx]
        dv = np.abs(np.diff(v))
        mad = 1.4826 * float(np.median(np.abs(dv - np.median(dv)))) + 1e-6
        for i in range(SCENE_HOLD, len(v) - SCENE_HOLD + 1):
            b, a = np.median(v[i - SCENE_HOLD:i]), np.median(v[i:i + SCENE_HOLD])
            if abs(a - b) >= SCENE_K * mad and abs(a - b) >= (3.0 if idx == 1 else 0.15 * max(b, 1.0)):
                if scene_steps and scene_steps[-1]["what_key"] == what and i - scene_steps[-1]["i"] <= SCENE_HOLD:
                    if abs(a - b) > abs(scene_steps[-1]["after"] - scene_steps[-1]["before"]):
                        scene_steps[-1].update(i=i, frame=int(Lv[i, 0]), before=float(b), after=float(a))
                    continue
                scene_steps.append(dict(i=i, frame=int(Lv[i, 0]), what_key=what, before=float(b), after=float(a)))
    for s_ in scene_steps:
        s_["what"] = f"the picture's {s_['what_key']} steps {s_['before']:.0f} -> {s_['after']:.0f}"
        events.append(dict(frame=float(s_["frame"]), kind="picture", what=s_["what"]))
        picture_frames.append(s_["frame"])
        del s_["i"]
    held_runs = []
    if held:
        Hd = np.array(held)
        loc = ndimage.median_filter(Hd[:, 1], size=21, mode="nearest")
        rep = (Hd[:, 1] < 0.2 * loc) & (Hd[:, 1] < 0.35)
        i = 0
        while i < len(rep):
            if rep[i]:
                j = i
                while j + 1 < len(rep) and rep[j + 1]:
                    j += 1
                if j - i + 1 >= 2:
                    held_runs.append([int(Hd[i, 0]), int(Hd[j, 0])])
                    events.append(dict(frame=float(Hd[i, 0]), kind="picture",
                                       what=f"the picture holds still for {j - i + 2} frames"))
                    picture_frames += [int(Hd[i, 0]) - 1, int(Hd[j, 0]) + 1]
                i = j + 1
            else:
                i += 1
    collapses = []
    if len(Lv) > 61:
        diff = dict((int(n), d) for n, d in held)
        series = np.array([(n, diff.get(int(n), np.nan), sd) for n, _, sd in Lv])
        for a, b in vf.transients(series):
            collapses.append([int(a), int(b)])
            events.append(dict(frame=float(a), kind="picture", what=f"the picture's contrast collapses, frames {a}-{b}"))
            picture_frames += [int(a), int(b) + 1]
    near_picture = lambda f: any(abs(f - p) <= WITH_PICTURE for p in picture_frames)
    box_fields, all_ticks = [], []
    found = [changes_of(s_) for s_ in seg]
    found_ticks = [ticks(x[0]) for x in found]
    for tk in found_ticks:
        all_ticks += [t["frame"] for t in tk]
    together = []                                        # changes in TOGETHER boxes or more at once: the whole overlay's
    for f in sorted(all_ticks):
        if sum(any(abs(t["frame"] - f) <= WITH_PICTURE for t in tk) for tk in found_ticks) >= TOGETHER and \
                not any(abs(f - g) <= WITH_PICTURE for g in together):
            together.append(f)
    for f in together:
        n_boxes = sum(any(abs(t["frame"] - f) <= WITH_PICTURE for t in tk) for tk in found_ticks)
        events.append(dict(frame=float(f), kind="picture", what=f"the overlay changes in {n_boxes} boxes at once"))
        picture_frames.append(f)
    for s_, tk, (ch, runs, nl, thr) in zip(seg, found_ticks, found):
        for t in tk:
            t["with_picture"] = near_picture(t["frame"])
        ck = clock([t for t in tk if not t["with_picture"]], clip.fps)
        # a readout ticks cleanly and now and then dithers; a box with something moving in it (the object, its gate, the
        # scene behind) "changes" in long back-and-forth runs: FLIR1's boresight, found as text without a track, 51
        # changes, most of them dithering 8-30 frames
        unsteady = len(tk) >= 4 and np.median([t["dither_frames"] for t in tk]) > NEAR / 2
        scrolls = nl > MAX_LOOKS or unsteady
        box_fields.append(dict(box=list(s_.box), name=s_.name, looks=nl, stretches=[list(r) for r in runs], ticks=tk,
                               clock=ck, scrolls=bool(scrolls), unsteady=bool(unsteady), threshold=thr))
        if ck or scrolls:
            continue
        for t in tk:
            if not t["with_picture"]:
                events.append(dict(frame=t["frame"], kind="readout", what=f"{s_.name} changes"
                                   + (f" (dithers {t['dither_frames']} frames)" if t["dither_frames"] else "")))
    gate_steps = []
    if gate:
        G = np.array(gate)
        for idx, key in ((1, "count"), (2, "radius")):
            for i, b, a in _held_step(G[:, idx], GATE_HOLD, GATE_RATIO):
                n = int(G[i, 0])
                if key == "count":
                    w = ("the gate round the object vanishes" if a < 0.2 * (b + 1) else
                         "a gate appears round the object" if b < 0.2 * (a + 1) else
                         f"the strokes round the object {'thin' if a < b else 'thicken'} ({b:.0f} -> {a:.0f} px)")
                else:
                    w = f"the strokes round the object {'draw in' if a < b else 'spread out'} ({b:.1f} -> {a:.1f} px out)"
                gate_steps.append(dict(frame=n, what=w, before=float(b), after=float(a), measure=key,
                                       with_picture=near_picture(n)))
                events.append(dict(frame=float(n), kind="gate", what=w))
    events.sort(key=lambda e: e["frame"])
    fields = dict(boxes=box_fields, boxes_found=found_boxes, polarity=polarity, gate=gate_steps, picture=scene_steps,
                  held=held_runs, collapses=collapses, events=events, frames=[clip.n0, clip.n1])
    res, npw, notes = {}, [], []
    clocks = [b for b in box_fields if b["clock"]]
    if boxes:
        res["text boxes"] = (f"{len(boxes)} {'found' if found_boxes else 'given'}: " + "; ".join(
            f"{b['name']}, {b['looks']} look{'s' if b['looks'] != 1 else ''}, {len(b['ticks'])} change"
            f"{'s' if len(b['ticks']) != 1 else ''}" + (" (a clock)" if b["clock"] else " (scrolls)" if b["scrolls"] else "")
            for b in box_fields[:8]) + (f"; and {len(box_fields) - 8} more" if len(box_fields) > 8 else ""))
    else:
        res["text boxes"] = "none found"
        npw.append(("text boxes", "no text found on the symbology's side of the picture: give --box"))
    for c in clocks:
        ck = c["clock"]
        res[f"clock, {c['name']}"] = (f"ticks every {ck['period_frames']:.2f} frames over {ck['ticks']} ticks: "
                                      + (f"{len(ck['early_late'])} come early or late (held or dropped frames there)"
                                         if ck["early_late"] else "steady, so no frame is held or dropped between them"))
        if abs(ck["period_frames"] - clip.fps) > 0.02 * clip.fps:
            notes.append(f"The clock at the {c['name']} ticks every {ck['period_frames']:.2f} frames, not every "
                         f"{clip.fps:.2f}: the clip's frame rate is not the recording's.")
    if gate_steps:
        res["gate"] = "; ".join(f"frame {g['frame']}: {g['what']}" for g in gate_steps)
    elif track:
        res["gate"] = "no step in the strokes round the object"
    if scene_steps:
        res["picture"] = "; ".join(f"frame {s_['frame']}: {s_['what']}" for s_ in scene_steps)
    if held_runs:
        res["held frames"] = ", ".join(f"{a}-{b}" for a, b in held_runs)
    if collapses:
        res["contrast collapses"] = ", ".join(f"{a}-{b}" for a, b in collapses)
    res["events"] = (f"{len(events)}: " + ", ".join(f"{e['frame']:.0f} {e['kind']}" for e in events[:20])
                     + (" ..." if len(events) > 20 else "")) if events else "none"
    files = write(out, tag, fields) if out else []
    return Found("events", res, fields, no_power=npw, files=files, notes=notes)


def write(out, tag, fields):
    """<out>_events.csv: one row an event."""
    p = Path(f"{out}_events.csv")
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "kind", "what"])
        for e in fields["events"]:
            w.writerow([f"{e['frame']:.1f}", e["kind"], e["what"]])
    return [str(p)]


def as_camera_events(fields, kinds=("readout", "gate", "picture")):
    """The events `camera` sets the rate's steps beside: [(frame, what)]."""
    return [(int(round(e["frame"])), e["what"]) for e in fields["events"] if e["kind"] in kinds]


def said(fields):
    L = []
    for b in fields["boxes"]:
        L.append(f"{b['name']}: {b['looks']} look{'s' if b['looks'] != 1 else ''}, {len(b['ticks'])} change"
                 f"{'s' if len(b['ticks']) != 1 else ''}"
                 + (f" -- a clock, ticking every {b['clock']['period_frames']:.2f} frames" if b["clock"] else "")
                 + (" -- scrolls or follows the scene, so no events" if b["scrolls"] else ""))
    for g in fields["gate"]:
        L.append(f"frame {g['frame']}: {g['what']}")
    for s in fields["picture"]:
        L.append(f"frame {s['frame']}: {s['what']}")
    for a, b in fields["held"]:
        L.append(f"frames {a}-{b}: the picture holds still")
    for a, b in fields.get("collapses", []):
        L.append(f"frames {a}-{b}: the picture's contrast collapses")
    if fields["events"]:
        L.append(f"{len(fields['events'])} events for `mcdonald camera --events auto` (clocks left out)")
    return L


def parse_boxes(text):
    """`name:x0,y0,x1,y1;...` or `x0,y0,x1,y1;...` -> ([boxes], [names])."""
    boxes, names = [], []
    for part in (text or "").split(";"):
        part = part.strip()
        if not part:
            continue
        name, _, b = part.rpartition(":")
        x0, y0, x1, y1 = (int(round(float(v))) for v in b.split(","))
        if x1 <= x0 or y1 <= y0:
            raise ValueError(f"--box {part}: it is x0,y0,x1,y1 with x1 > x0 and y1 > y0")
        boxes.append((x0, y0, x1, y1))
        names.append(name or f"box ({x0},{y0})-({x1},{y1})")
    return boxes, names


def main():
    import argparse
    from . import clip as vclip
    from .report import emit, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", help="CSV with frame and x/y columns: the gate round the object is followed too")
    ap.add_argument("--size", type=float, default=9.0, help="how wide the object is on the screen, px (default 9)")
    ap.add_argument("--box", metavar="NAME:x0,y0,x1,y1;...", help="the boxes to follow, instead of those found")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--workdir")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>; with --n0/--n1, the segment's own folder in it, <tag>/segment-<n0>-<n1>)")
    ap.add_argument("--json", action="store_true", help="print the measurement as JSON on stdout")
    args = ap.parse_args()
    try:
        boxes, names = parse_boxes(args.box) if args.box else (None, None)
    except ValueError as e:
        ap.error(str(e))
    with said_to_stderr(args.json) as lines:
        video, tag, _ = vf.resolve(args.video)
        track = vf.read_track(args.track) if args.track else None
        clip = vclip.Clip(video, args.workdir, args.n0, args.n1)
        out = vclip.out_prefix(args.out, tag, vclip.named(args.n0, args.n1, clip))
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
        found = find(clip, track, args.size, boxes, names, out=out, tag=tag)
        print("\n".join(said(found.fields)))
        for w in found.no_power:
            print(f"no power: {w[1]}")
        for f in found.files:
            print(f"wrote {f}")
    code = 0
    if args.json:
        emit(found.envelope("events", inputs_of(args), clip, said=lines, exit_code=code))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
