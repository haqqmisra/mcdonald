#!/usr/bin/env python3
"""How does the background of a clip move -- and is it one background?

  bg_layers.py VIDEO|ID [--track CSV | --auto-track] [options]

Measures the scene's screen motion with whole-template matching over a k-frame
baseline (forensics.shift_field), separately for striated texture (open sea)
and isotropic texture (cloud, land), and reports
  - each layer's screen velocity, and the rate of one layer against the other
    (layer parallax: own-ship motion seen against two ranges);
  - how many motion groups the templates fall into, whatever their texture;
  - with a track, the object's rate against EACH layer in 1-s windows of
    wall-clock time. "Against the background" is only one number when there is
    one layer. On PR144 there were two, 98 px/s apart, and a single-consensus
    tracker had blended them into a rate against neither.

Writes <tag>_layers.csv and <tag>_layers.png into the case directory
(--out DIR; default ./<tag>).

  --validate      check the ruler first: recover known synthetic shifts of real
                  frames (bias), and compare 2k-frame shifts with the sum of two
                  k-frame shifts (chain consistency)
  --composite N   red/cyan composites of frames N and N+k aligned on each
                  layer's shift; the other layer shows colour fringes

VIDEO is a path or a record id (PR144, DOW-UAP-PR144, 06:PR001). Frames are
ffmpeg's, 1-based. A full-rate run is ~1 s per frame pair on 10 cores.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from . import forensics as vf
from . import gpu
from . import scene as whole
from .progress import PROCS_HELP, pool_of, pooled, size_of, to_stderr
from .report import Found, emit, inputs_of, said_to_stderr

_G = {}

# The templates' size. 128 px a template (stride 96) unless too few of them fit between the masks and have texture to
# match on: then 64 px (stride 48). A consensus needs 8 templates that agree (`forensics.consensus`), so under twice
# that a pair can hardly have one. AARO's "Middle East Object" (2026-10-26) leaves a 560-px strip clear between blurred
# panels, crossed by a reticle, grey boxes and a horizon line: 4 textured 128-px templates on its median frame, and
# `layers` read 92 % of its pairs "held still" through every slew; 64-px templates recover the scene's shift there
# (35, -51 px against a hand chain's 35.2, -51.4).
TEMPLATES = (128, 96, 48)           # px, stride, the second pass's stride
SMALL_TEMPLATES = (64, 48, 32)
FEW_TEMPLATES = 16
TEXTURE_DN = 1.0          # band-passed grey's std under which a template has nothing to match on (a blurred panel: 0.3-0.7)


def template_size(clip, masks, rows=None, n_sample=9):
    """((px, stride, second pass's stride), fields): the templates `measure` uses on this clip, and why -- how many
    128-px templates fit clear of the masks with texture on the sampled frames (the median), against FEW_TEMPLATES."""
    ns = np.unique(np.linspace(clip.n0, clip.n1, min(n_sample, clip.n1 - clip.n0 + 1)).astype(int))
    tpl, stride, _ = TEMPLATES
    counts = []
    for n in ns:
        rgb = clip.rgb(int(n))
        bad = vf.frame_mask(rgb, masks, rows, int(n))
        h = vf.bandpass(vf.grey_of(rgb).astype(np.float32))
        counts.append(sum(1 for y0 in vf.template_rows(clip.H, tpl, stride) for x0 in range(16, clip.W - tpl - 16, stride)
                          if not bad[y0:y0 + tpl, x0:x0 + tpl].any() and h[y0:y0 + tpl, x0:x0 + tpl].std() >= TEXTURE_DN))
    median = float(np.median(counts)) if counts else 0.0
    small = median < FEW_TEMPLATES
    chosen = SMALL_TEMPLATES if small else TEMPLATES
    return chosen, dict(px=chosen[0], stride=chosen[1], clear_textured_128px=median, sampled_frames=len(ns),
                        smaller_because_few=small)


def _init(video, workdir, n0, n1, masks, rows, trk, k, reach, size, dark, longer=None, tpl=TEMPLATES):
    masks = {key: v for key, v in masks.items() if key in ("blocks", "graphics", "colour", "tinted")}
    _G.update(clip=vf.Clip(video, workdir, n0, n1), masks=masks, rows=rows, k=k, reach=reach,
              pos=vf.interp_track(trk) if trk else None, size=size, dark=dark, longer=longer or k,
              tpl=tpl[0], stride=tpl[1], stride_again=tpl[2])


def _bad(n):
    """Frame n's grey and its mask: read here, or taken from the threads that read ahead of a loop on a graphics
    card (`_G["ahead"]`, `measure`)."""
    ahead = _G.get("ahead")
    return ahead.get(n) if ahead is not None else _read(n)


def _read(n):
    clip = _G["clip"]
    rgb = clip.rgb(n)
    bad = vf.frame_mask(rgb, _G["masks"], _G["rows"], n)
    if _G["pos"]:
        cx, cy = _G["pos"](n)
        yy, xx = np.ogrid[:clip.H, :clip.W]
        bad = bad | ((xx - cx) ** 2 + (yy - cy) ** 2 < 28 ** 2)
    return vf.grey_of(rgb), bad


def _filtered(n, g):
    """Frame n band-passed, for `_first`: None with no card (`shift_field_auto` filters it, as ever); on a card, the
    filtered frame left there and kept for the pair k frames on, whose first frame it is."""
    kept = _G.get("filtered")
    if kept is None:
        return None
    if n not in kept:
        kept[n] = vf.bandpass_kept(g)
        for m in [m for m in kept if m < n - 2 * _G["k"]]:      # long past: every pair that had it is done
            del kept[m]
    return kept[n]


def _forget_card():
    """What a round on a graphics card left in `_G` let go: the filtered frames kept there, and a window's."""
    _G.pop("filtered", None)
    _G.pop("window_from", None)
    _G.pop("window", None)


# How each pair was measured: the last two columns of a template row, after vf.SHIFT_COLS. UNMOVED: held still, between
# the catch-up steps of a picture that repeats (`repeating`), and so not moved at all -- not measured again.
MOVED, AGAIN, STILL, UNMOVED = 0, 1, 2, 3
# MEAN_OUT: a third pass's rows, a pair the second pass left STILL read again with each pixel's mean over a block taken out
# (`_mean_out`). These rows are never `tpl`'s and never reach <tag>_layers.csv: `slew`, `camera` and the report read those
# columns and have no way to see where a shift came from, so a reading made this way waits in the scene's own rows
# (`read_scene_under`) until each of them is turned on by name.
MEAN_OUT = 4
BLOCK_PAIRS = (5, 20, 35)  # the pairs of a block read this way, frames into it: a block's reading, at a third of the cost of
#                            one, as the second pass's windows are shared; each pixel's mean is the whole block's
SCENE_SHARE = 0.5          # a clip is read by whole blocks where more than this share of its pairs is STILL: the NO POWER's line
# A picture that repeats and catches up (2026-10-28, PR051's upload, the maintainer's choice): the same picture again with
# new capture noise for a few frames, then a step of tens of pixels. A pair inside a hold is held still over k frames,
# and measured again over a second it was given the second's mean rate -- the catch-up steps' motion counted twice.
# A one-step sub-pixel test cannot tell such a hold from a slow scene behind a fixed pattern (PR135's island read
# 0.04-0.07 px over 5 frames where it moved 1.6, PR051's holds 0.04-0.09), but the pairs' sequence can: a window is
# one where the picture repeats when its held pairs and its catch-ups (CATCH_UP px or more over k frames) alternate
# MIN_SWITCHES times or more, with few pairs between the two -- a slew starting or stopping switches once, a slow
# scene has no catch-ups, a fast one no held pairs.
CATCH_UP = 12.0           # px over k frames: three times the zero zone either side of zero
MIN_SWITCHES = 4          # held <-> catch-up changes along a window's pairs
MAX_BETWEEN = 0.3         # share of a window's pairs that moved but under CATCH_UP
# ... and a held pair is unmoved only where its own field, zero allowed, agrees on a shift inside the zero zone
# `shift_field` leaves out (AT_ZERO, the capture's jitter: PR051's holds read 0.3-1.9 px, and at 0.5 half of them were
# measured again over a second and lost) with nearly all its templates in the one group (REPEAT_SHARE): a repeated
# picture matches itself everywhere, where a catch-up along streaks whose match failed is matched at zero by a few
# (PR051 603-605: 16 of 79 templates at zero, the step 89 px).
AT_ZERO = 4.0
REPEAT_SHARE = 0.8
# ... and a pair called held whose own field, zero allowed, agrees on a shift past the zero zone moved: a streaky scene
# moving along its streaks keeps its same-place correlation high (PR051's terrain: 100 px across, still score 0.7-0.95),
# and that field found the step (frames 439-441: 108 px, nine templates, against the data bar's 99). It keeps its own.
HELD_BUT_MOVED = 5.0      # px: past the +-4 px zone about zero, as `_kept`'s 5


def _first(a):
    """One k-frame pair: its template rows as k-frame shifts, and whether it was held still."""
    k = _G["k"]
    ga, ba = _bad(a)
    gb, bb = _bad(a + k)
    return vf.shift_field_auto(ga, gb, ba, bb, _filtered(a, ga), _filtered(a + k, gb), a=a, reach=_G["reach"],
                               tpl=_G.get("tpl", TEMPLATES[0]), stride=_G.get("stride", TEMPLATES[1]))


def window_start(a, k, L, n0, n1):
    """The first frame of the L-frame window a held-still pair (a, a + k) is measured again over:
    the nearest to the pair of the windows starting every L/2 frames, kept inside the clip.
    Pairs a few frames apart share a window -- a still scene's neighbours mostly are still too --
    so a run of held-still pairs costs a few second passes, not one each (2026-09-26: on PR113
    380-440 the second passes were 70 % of the stage, 21 windows one frame apart)."""
    every = max(L // 2, 1)
    s = int(round((a + k // 2 - L // 2) / every)) * every
    return int(min(max(s, n0), n1 - L))


def _again(s):
    """The templates of the L-frame window from s -- denser (stride 48), each shift given as a
    k-frame shift, keeping only shifts a held-still pair can have (under 5 px in k: a second may
    take in a slew, PR135's at 312) -- and whether the scene was still over the window too."""
    k, clip = _G["k"], _G["clip"]
    L = min(_G["longer"], clip.n1 - clip.n0)
    (gs, bs), (ge, be) = _bad(s), _bad(s + L)
    g, still_too = vf.shift_field_auto(gs, ge, bs, be, a=s, reach=_G["reach"], tpl=_G.get("tpl", TEMPLATES[0]),
                                       stride=_G.get("stride_again", TEMPLATES[2]))
    g = vf.scaled_shifts(g, k / L)
    # Denser templates, because over featureless sea the pattern still wins at zero, zero is left out,
    # and only textured templates are left.
    return _kept(g), still_too


def _kept(g):
    """A second pass's field as `_again` keeps it, its shifts already given over k frames."""
    return g[np.abs(g[:, 3:5]).max(1) <= 5]


def _window(s):
    """The L-frame window from s as the second pass reads it -- its two frames' grey and masks,
    band-passed -- kept for the window's other parts, which a worker is often given next."""
    if _G.get("window_from") != s:
        clip = _G["clip"]
        L = min(_G["longer"], clip.n1 - clip.n0)
        (gs, bs), (ge, be) = _bad(s), _bad(s + L)
        _G["window_from"], _G["window"] = s, (gs, ge, bs, be, vf.bandpass_kept(gs), vf.bandpass_kept(ge))
    return _G["window"]


def _again_part(job):
    """(s, field with zero left out, field with zero allowed) for some rows of templates of the window from s,
    both from the one search, as `shift_field_auto` reads a pair."""
    s, only = job
    gs, ge, bs, be, ha, hb = _window(s)
    f, fz = vf.shift_field(gs, ge, bs, be, a=s, reach=_G["reach"], tpl=_G.get("tpl", TEMPLATES[0]),
                           stride=_G.get("stride_again", TEMPLATES[2]), ha=ha, hb=hb, only=only, zeros=(4, -1))
    return s, f, fz


def second_pass(pool, starts, H, k, L, progress=None, stop=None, parts=None, tpl=TEMPLATES):
    """`_again` of each window in `starts`, on `pool` (None: in this process, `_G` already set):
    [(rows, still_too)] in their order, the same to the bit. A window's rows of templates are
    shared among the workers -- a still scene has few windows and each is many seconds (2026-10-09:
    four of 20 s on PR113, so all but four workers waited) -- in `parts` a window (as many as the
    workers go round, if not said), and the field is joined before it is judged, as
    `shift_field_auto` judges it: the field with zero left out where it found the scene moving
    (`forensics.moved`), else the one with zero allowed, the window held still."""
    rows = vf.template_rows(H, tpl[0], tpl[2])
    parts = parts or max(1, size_of(pool) // max(len(starts), 1))
    parts = [[int(y) for y in p] for p in np.array_split(rows, min(len(rows), parts)) if len(p)]
    got = pooled(None if pool else 0, _again_part, [(s, p) for s in starts for p in parts], progress=progress, stop=stop,
                 what="Layers again", pool=pool)
    kept = []
    for s in starts:
        f = np.vstack([x for t, x, _ in got if t == s])
        fz = np.vstack([x for t, _, x in got if t == s])
        g, still_too = (f, False) if vf.moved(f, len(fz)) else (fz, True)
        kept.append((_kept(vf.scaled_shifts(g, k / L)), still_too))
    return kept


def held_but_moved(first):
    """The first pass with each pair called held still whose own field (zero allowed) agrees on a shift of more than
    HELD_BUT_MOVED px taken as moved: [(field, held still)], and how many were."""
    out, n = [], 0
    for f, still in first:
        c = vf.layers_of(f)["all"] if still else None
        if c is not None and np.hypot(*c[0]) > HELD_BUT_MOVED:
            still, n = False, n + 1
        out.append((f, still))
    return out, n


def repeating(pairs, first, k, L, n0, n1):
    """The windows (`window_start`'s) in which the picture repeats and catches up, and the held pairs there whose own
    field, zero shift allowed, agrees on zero -- a shift inside the zero zone, nearly every template in the one group
    (AT_ZERO, REPEAT_SHARE): (set of window starts, set of pairs that are UNMOVED). `first` is the first pass, (field,
    held still) a pair. A held pair whose field does not agree so -- a catch-up step whose match failed falls back to
    zero allowed, and is held still too, a few of its templates matched at zero -- is measured again as before."""
    kind, zero = {}, set()
    for a, (f, still) in zip(pairs, first):
        lay = vf.layers_of(f)
        c = lay["all"]
        if still:
            kind[a] = "held"
            if c is not None and np.hypot(*c[0]) <= AT_ZERO and lay["groups"] == 1 and lay["inliers"] >= REPEAT_SHARE:
                zero.add(a)
        else:
            kind[a] = "catch" if c is not None and np.hypot(*c[0]) >= CATCH_UP else "between"
    windows = set()
    for s in {window_start(a, k, L, n0, n1) for a in pairs}:        # every pair inside the window's own span
        kinds = [kind[a] for a in sorted(kind) if s <= a and a + k <= s + L]
        ends = [x for x in kinds if x != "between"]
        switches = sum(p != q for p, q in zip(ends, ends[1:]))
        if (ends.count("held") >= 2 and ends.count("catch") >= 2 and switches >= MIN_SWITCHES
                and kinds.count("between") <= MAX_BETWEEN * len(kinds)):
            windows.add(s)
    return windows, {a for a in zero if window_start(a, k, L, n0, n1) in windows}


def _rows(a, f, still, again, k, L, unmoved=False):
    """Pair a's rows as `measure` keeps them, two columns after vf.SHIFT_COLS: how it was measured
    (MOVED with its own rows; a held-still pair with its window's, `again` = (rows, still_too),
    the pair's number on them: AGAIN where the window moved, STILL where it did not; UNMOVED with
    its own rows, between a repeating picture's catch-up steps) and over how many frames."""
    how, over = MOVED, k
    if still and unmoved:
        how = UNMOVED
    elif still and again is not None:
        g, still_too = again
        f = g.copy()
        f[:, 0] = a
        how, over = (STILL if still_too else AGAIN), L
    return np.hstack([f, np.tile([how, over], (len(f), 1))])


def _pair(a):
    """One pair, both passes: the templates of a k-frame pair, or, held still over k frames,
    of the L-frame window nearest it (`window_start`), as k-frame shifts.

    Held still over k frames is what a slow scene is as well as a scene held still: a
    shift under the +-4 px left out about zero falls back to zero allowed, and a pattern
    that stays on the sensor (fixed speckle, column stripes) then holds the estimate at
    zero. PR135 150-320, an island drifting 10 px/s: every 5-frame pair read 0.0-0.1 px
    where the scene moved 1.6; over 30 frames it read -9.3 px, where a hand measurement
    had -9.0. `measure` shares each window between the pairs nearest it."""
    k, clip = _G["k"], _G["clip"]
    L = min(_G["longer"], clip.n1 - clip.n0)
    f, still = _first(a)
    again = _again(window_start(a, k, L, clip.n0, clip.n1)) if still and L > k else None
    return _rows(a, f, still, again, k, L)


def _thing_at(n):
    """The tracked thing's place in frame n, as `_bad` masks it."""
    clip = _G["clip"]
    if not _G["pos"]:
        return np.zeros((clip.H, clip.W), bool)
    cx, cy = _G["pos"](n)
    yy, xx = np.ogrid[:clip.H, :clip.W]
    return (xx - cx) ** 2 + (yy - cy) ** 2 < 28 ** 2


def _mean_out(job):
    """A third pass, B3 of the survey: (s, rows, tried) for the block of frames from s and the pairs (first frames) it is given
    to read. Each pixel's mean over the block is taken out of both frames of a pair and the same templates are matched:
    a pattern on the sensor is gone, so a scene the pattern held at zero can win. The shift is over k frames and may be any
    size, where a second pass's are held under 5 px. A pair whose field finds nothing moved reads nothing.

    The mean and the spread are running sums, 16 MB at 1080p, not the block's frames (500 MB a worker as prototyped). Where a
    scene is slow the mean takes part of it along, and a pattern that breathes with the gain leaves its breathing behind:
    this helps some clips (10 of 24 pairs on PR099 object 3, 3 of 24 on PR41), and the block's whole reading the others."""
    s, pairs = job
    clip, k = _G["clip"], _G["k"]
    frames = range(s, min(s + whole.BLOCK, clip.n1 + 1))
    total, square = np.zeros((clip.H, clip.W), np.float64), np.zeros((clip.H, clip.W), np.float64)
    for m in frames:
        g = clip.grey(m).astype(np.float64)
        total += g
        square += g * g
    mean = total / len(frames)
    sd = np.sqrt(np.maximum(square / len(frames) - mean * mean, 0.0))
    flicker = ndimage.binary_dilation((mean < 5) | (sd > whole.MASK_K * np.median(sd)), iterations=4)
    rows = []
    for a in pairs:
        ba, bb = flicker | _thing_at(a), flicker | _thing_at(a + k)
        f, still = vf.shift_field_auto(clip.grey(a) - mean + 128.0, clip.grey(a + k) - mean + 128.0, ba, bb, a=a, reach=_G["reach"],
                                       tpl=_G.get("tpl", TEMPLATES[0]), stride=_G.get("stride", TEMPLATES[1]))
        if not still and len(f):
            rows.append(np.hstack([f, np.tile([MEAN_OUT, k], (len(f), 1))]))
    return s, np.vstack(rows) if rows else np.zeros((0, len(vf.SHIFT_COLS) + 2)), len(pairs)


def _block_pairs(s, how, k, n1):
    """The pairs of the block from s for a third pass: BLOCK_PAIRS, those that are STILL. What the first two passes read they
    keep, and an UNMOVED pair is the same picture again: no reading can be had of it."""
    return [s + d for d in BLOCK_PAIRS if how.get(s + d) == STILL and s + d + k <= n1]


def _templates_read(rows):
    """A block's third-pass rows as (vx, vy, pairs with a consensus): the median of its pairs' consensus shifts, px/frame."""
    v = []
    for a in np.unique(rows[:, 0]):
        c = vf.layers_of(rows[rows[:, 0] == a])["all"]
        if c is not None:
            v.append(np.array(c[0], float) / rows[0, -1])
    return (float(np.median([q[0] for q in v])), float(np.median([q[1] for q in v])), len(v)) if v else (None, None, 0)


def read_scene_under(clip, masks, rows, trk, how, k, reach, size, longer, made_from, procs=None, fresh=False, say=print,
                     progress=None, stop=None):
    """Where the scene is held still and a clip says NO POWER: the block's mean out and the templates again (`_mean_out`), and
    the block's whole reading (`scene.read_clip`). [one row a block], for <tag>_scene.csv, and the third pass's template rows
    (SHIFT_COLS, then how and over how many frames).

    Kept apart from `tpl` with its own cache: the first two passes' numbers, their cache and every column of <tag>_layers.csv
    are what they were, whether or not this ran. A block is read when at least half its pairs were left STILL."""
    key = repr((made_from, "scene under the pattern", whole.SETTINGS, BLOCK_PAIRS, whole.MASK_K))
    cache = clip.dir / f"bg_scene_k{k}_{clip.n0}_{clip.n1}_{hashlib.sha1(key.encode()).hexdigest()[:10]}.npz"
    if cache.exists() and not fresh:
        z = np.load(cache)
        say(f"the scene's blocks from {cache} (read earlier; --fresh reads them again)")
        return json.loads(str(z["blocks"])), z["tpl"]
    starts = []
    for s in whole.block_starts(clip.n0, clip.n1):
        held = [a for a in range(s, s + whole.BLOCK) if a in how]
        if held and sum(how[a] == STILL for a in held) >= 0.5 * len(held):
            starts.append(s)
    jobs = [(s, p) for s in starts if (p := _block_pairs(s, how, k, clip.n1))]
    got = {}
    if jobs:
        args = (clip.video, clip.dir, clip.n0, clip.n1, masks, rows, trk, k, reach, 9.0, False, longer, size)
        got = {s: (f, n) for s, f, n in pooled(procs, _mean_out, jobs, _init, args, progress=progress, stop=stop, what="Layers, mean out",
                                               pixels=clip.W * clip.H)}
    blocks = whole.read_clip(clip.video, clip.n0, clip.n1, tracks=[trk] if trk else (), starts=starts, procs=procs, progress=progress,
                             stop=stop)
    tpl = np.vstack([f for f, _ in got.values()]) if got else np.zeros((0, len(vf.SHIFT_COLS) + 2))
    for b in blocks:
        f, n = got.get(b["start"], (tpl[:0], 0))
        vx, vy, read = _templates_read(f) if len(f) else (None, None, 0)
        b.update(tpl_vx=vx, tpl_vy=vy, tpl_pairs_read=read, tpl_pairs_tried=n, t_s=round(float(clip.t(b["start"])), 4))
    np.savez_compressed(cache, blocks=json.dumps(blocks), tpl=tpl)
    return blocks, tpl


def _cands(n):
    return n, vf.frame_candidates(_G["clip"], n, _G["masks"], _G["rows"], _G["size"], _G["dark"])


def validate(clip, masks, rows, k, reach, say=print):
    """The ruler, on this clip's own texture: known shifts of real frames recovered, and the 2k-frame
    shift against the sum of two k-frame shifts. Returns what it printed as fields (until 2026-09-23 it
    only printed, and an agent reading --json had none of it)."""
    ns = np.linspace(clip.n0 + 5, clip.n1 - 2 * k - 5, 6).astype(int)
    out = dict(known_shifts=[], chains=[])
    say("known shifts of real frames (truth -> recovered consensus):")
    for n in ns[::2]:
        g = clip.grey(int(n))
        bad = vf.frame_mask(clip.rgb(int(n)), masks, rows, int(n))
        for dx, dy in ((-20, -8), (37, 11), (-96, 40)):
            gb = ndimage.shift(g, (dy, dx), order=0, mode="nearest")
            bb = ndimage.shift(bad.astype(float), (dy, dx), order=0, mode="constant", cval=1) > 0
            f = vf.good(vf.shift_field(g, gb, bad, bb, stride=192, reach=reach))
            c = vf.consensus(f[:, 3:5])
            got = "none" if c is None else f"({c[0][0]:+.2f},{c[0][1]:+.2f}) from {c[1]} templates"
            say(f"  n = {n}: ({dx:+d},{dy:+d}) -> {got}")
            out["known_shifts"].append(dict(frame=int(n), truth=[dx, dy], recovered=None if c is None else [float(c[0][0]), float(c[0][1])],
                                            templates=None if c is None else int(c[1])))
    say(f"chain consistency: the {2 * k}-frame shift against the sum of two {k}-frame shifts:")
    for n in ns:
        n = int(n)
        fr = {m: (clip.grey(m), vf.frame_mask(clip.rgb(m), masks, rows, m)) for m in (n, n + k, n + 2 * k)}
        sh = {}
        for a, b in ((n, n + k), (n + k, n + 2 * k), (n, n + 2 * k)):
            f = vf.shift_field(fr[a][0], fr[b][0], fr[a][1], fr[b][1], stride=144, reach=reach * (b - a) // k)
            sh[(a, b)] = vf.layers_of(f)
        for name in ("striated", "isotropic"):
            p = [sh[q][name] for q in ((n, n + k), (n + k, n + 2 * k), (n, n + 2 * k))]
            if all(p):
                s, d = p[0][0] + p[1][0], p[2][0]
                say(f"  n = {n} {name:9s}: sum ({s[0]:+7.1f},{s[1]:+6.1f})  direct ({d[0]:+7.1f},{d[1]:+6.1f})  "
                    f"difference {np.hypot(*(d - s)):.1f} px ({100 * np.hypot(*(d - s)) / max(np.hypot(*d), 1):.1f} %)")
                out["chains"].append(dict(frame=n, layer=name, sum_px=[float(s[0]), float(s[1])], direct_px=[float(d[0]), float(d[1])],
                                          difference_px=float(np.hypot(*(d - s)))))
    return out


def composite(clip, n, k, lay, out):
    """Frame n in red against n + k shifted by each layer's shift: grey where aligned. Returns the
    shifts it used, as fields."""
    ga, gb = clip.grey(n), clip.grey(n + k)
    used = {}
    lo, hi = np.percentile(ga, [1, 99.5])
    st = lambda g: ((g - lo) / max(hi - lo, 1) * 255).clip(0, 255)
    tiles = []
    for name in ("striated", "isotropic"):
        if lay.get(name):
            dx, dy = lay[name][0]
            bs = ndimage.shift(gb, (-dy, -dx), order=1, mode="constant")
            tiles.append(np.stack([st(ga), st(bs), st(bs)], -1).astype(np.uint8))
            print(f"composite: frame {n} (red) against {n + k} shifted by the {name} layer ({dx:+.1f},{dy:+.1f})")
            used[name] = [float(dx), float(dy)]
    if tiles:
        Image.fromarray(np.vstack(tiles)).save(out)
        print(f"wrote {out}  (grey = aligned; colour fringes = the other layer)")
    return dict(frame=n, against=n + k, shift_px=used, file=str(out) if tiles else None)


# the background layers' default names in a figure's words (sciencespeak's mcdonald glossary, 2026-11-07); a name given
# with --names (the sea, the clouds) is the person's and stays
LAYER_WORDS = {"striated layer": "streaked background", "isotropic layer": "evenly textured background"}


def figure(out, clip, names, w, par, groups, say=print):
    """The object's speed against each kind of background, a point a second; under it, the one background against the other
    where both are in the picture, else how many groups the background moves in. In the house style (figures.setup)."""
    import matplotlib
    matplotlib.use("Agg")
    from . import figures
    plt = figures.setup()
    ns = np.arange(clip.n0, clip.n1 + 1)
    ser = lambda d: np.array([np.hypot(*d[n]) if n in d else np.nan for n in ns])
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(10, 6.6), sharex=True, constrained_layout=True,
                                 gridspec_kw=dict(height_ratios=[3, 1.5]))
    words = {k_: LAYER_WORDS.get(v_, v_) for k_, v_ in names.items()}      # the default names in plain words; a name given stays
    ax.set_title("Speed against the background" if w["striated"] or w["isotropic"] or w["all"] else
                 "Speed of the background")
    for key, col in (("striated", figures.BLUE), ("isotropic", figures.AMBER)):
        if w[key]:
            ax.plot(clip.t(ns), ser(w[key]), color=col, lw=2, solid_capstyle="round", label=f"against the {words[key]}",
                    zorder=3)
    if not (w["striated"] and w["isotropic"]) and w["all"]:         # wider and under the others: where one background is
        sub = w["striated"] or w["isotropic"]                        # the whole of it (PR135), both lines still show
        ax.plot(clip.t(ns), ser(w["all"]), color=figures.PURPLE if sub else figures.BLUE, lw=4.5 if sub else 2,
                alpha=0.55 if sub else 1.0, label="against the whole background", zorder=2)
    ax.set_ylabel("Speed (pixels a second)")
    if ax.get_legend_handles_labels()[0]:
        ax.legend(loc="best", handlelength=1.6)
    if par:
        bx.plot(clip.t(ns), ser(par), color=figures.PURPLE, lw=2, solid_capstyle="round")
        bx.set_title("One background against the other")
    else:
        bx.plot(clip.t(ns), [groups.get(n, np.nan) for n in ns], color=figures.PURPLE, lw=1.8)
        bx.set_title("Groups the background moves in")
        from matplotlib.ticker import MaxNLocator
        bx.yaxis.set_major_locator(MaxNLocator(integer=True))     # a count: whole numbers only
    bx.set_ylim(bottom=0)
    bx.set_ylabel("Speed\n(pixels a second)" if par else "Number of groups")
    bx.set_xlabel("Time in the video (s)")
    figures.save(fig, out, dpi=200, quiet=True)
    plt.close(fig)
    say(f"wrote {out}")


def auto_track(clip, masks, rows=None, size=9.0, dark=False, seed=None, out=None, procs=None, say=print,
               progress=None, stop=None):
    """Track a compact source with no marks to go on: the detector on every frame, linked
    from `seed` (n, x, y) or from the strongest. Writes <out>_track_strip.png, which has
    to be looked at before the track is believed. `layers` and `integrity` both offer it."""
    args = (clip.video, clip.dir, clip.n0, clip.n1, masks, rows, None, 5, 0, size, dark)
    cands = dict(vf.pooled(procs, _cands, clip.frames(), _init, args, 4, progress, stop, "Spot detection",
                           pixels=clip.W * clip.H))
    trk = vf.link_track(cands, clip.n0, clip.n1, (int(seed[0]), seed[1], seed[2]) if seed else None)
    strip = Path(f"{out}_track_strip.png")
    shown = vf.track_strip(clip, trk, strip)
    say(f"auto-track: {len(trk)} of {clip.n1 - clip.n0 + 1} frames. CHECK {strip} (frames {shown[0]}..{shown[-1]}) "
        "before trusting it.")
    return trk


def _spread(d):
    """Median, the 16-84 % interval and the range of a set of windowed rates, px/s."""
    v = np.array([np.hypot(*p) for p in d.values()])
    if not len(v):
        return None
    return dict(median=float(np.median(v)), p16=float(np.percentile(v, 16)), p84=float(np.percentile(v, 84)),
                min=float(v.min()), max=float(v.max()), windows=len(v))


def over_track(trk, vel, k, fps, half):
    """The object's velocity against a layer at every k-frame pair of its track, for one-second windows over the whole
    track: against the layer's velocity at that pair -- a running median of its readings over +-half frames (one pair
    that read something moving is not the background), carried across the frames where it was not read (linear between
    readings, held at the ends). ({first frame of pair: px/s vector}, the share of pairs the layer was read on), or
    ({}, 0.0) without both.

    The windows of the layer's own readings (`px_per_s`) exist only where the background was read, so their median is
    the rate of those stretches, and it moved when a change read others: PR44's bird, flying 20-40 px/s along a still
    background, was 21.8 px/s at f7f7fad and 28.0 at 82f6c13. With every second of the track counted once it is 32.3
    and 32.6. Not the net rate over the track (25.7 and 26.0 there): on PR135, whose relative motion turns back with the
    camera, a net rate fell from 99 to 8 px/s on one member while each second read about a hundred (session 12,
    2026-10-30)."""
    a = sorted(n for n in trk if n + k in trk)
    h = sorted(vel)
    if not a or not h:
        return {}, 0.0
    hv = np.array([vel[n] for n in h], float)
    hn = np.array(h)
    med = np.array([np.median(hv[np.abs(hn - n) <= half], 0) for n in h])
    bg = np.c_[np.interp(a, h, med[:, 0]), np.interp(a, h, med[:, 1])]
    fk = fps / k
    rel = np.array([(np.array(trk[n + k], float) - np.array(trk[n], float)) * fk for n in a]) - bg
    return {n: rel[i] for i, n in enumerate(a)}, float(np.mean(np.isin(a, hn)))


def glance(clip, masks, rows=None):
    """One frame pair at the start of the window: how many motion groups, and how fast
    each texture class crosses the screen. Seconds, where `measure` is minutes -- and a
    look, not a measurement: one pair, no windows, and nothing about the object."""
    a, b = clip.n0, min(clip.n0 + 5, clip.n1)
    ga, gb = clip.grey(a), clip.grey(b)
    bad_a = vf.frame_mask(clip.rgb(a), masks, rows, a)
    bad_b = vf.frame_mask(clip.rgb(b), masks, rows, b)
    field, still = vf.shift_field_auto(ga, gb, bad_a, bad_b)
    f = vf.good(field)
    lay = vf.layers_of(f) if len(f) else {"groups": 0}
    groups = lay.get("groups", 0)
    res = {"motion groups": groups}
    fields = dict(pair=[a, b], motion_groups=groups, scene_held_still=bool(still), screen_px_per_s={}, templates={})
    if still:
        res["scene held still"] = ("yes -- zero shift was allowed, so a static "
                                   "pattern could be locking these estimates; read "
                                   "them as 'no more than'")
    for name in ("striated", "isotropic"):
        v = lay.get(name)
        if v is not None:
            rate = float(np.hypot(*v[0])) * clip.fps / max(b - a, 1)
            fields["screen_px_per_s"][name], fields["templates"][name] = rate, int(v[1])
            res[f"{name} layer"] = f"{rate:.0f} px/s ({v[1]} templates)"
    npw, notes = [], []
    if groups == 0:
        npw.append(("layers", "no consensus background motion: the scene is held still "
                              "or has too little texture"))
    if still:
        npw.append(("layers", "the scene is held still on screen, so a background rate "
                              "here is an upper limit, not a measurement"))
    if len(fields["screen_px_per_s"]) > 1:
        notes.append("More than one background layer: any rate quoted here must name "
                     "which layer it is against.")
    return Found("layers", res, fields, no_power=npw, notes=notes)


def measure(clip, masks, rows=None, track=None, k=5, step=1, max_shift=45.0, names=None, dark_below=None,
            out=None, procs=None, fresh=False, say=print, progress=None, stop=None, scene=False):
    """Every frame pair of the window: each layer's screen velocity, the rate of one layer
    against the other, and with a track the object's rate against EACH layer, in 1-s
    windows of wall-clock time. Writes <out>_layers.csv and <out>_layers.png.

    With `scene`, a clip left STILL in over SCENE_SHARE of its pairs is read under its pattern too (`read_scene_under`): its
    own fields["scene"], <out>_scene.csv, and a line beside the NO POWER where a block was read. Every other number this function
    returns or writes is what it was: `slew`, `camera` and `over_track` take nothing from it.

    The findings come back as numbers (Found.fields); what `mcdonald layers` prints is
    written from them by `said`, so the prose and the fields cannot disagree. The
    templates are cached in the clip's work directory; `fresh` measures them again."""
    names = dict(names or {})
    names.setdefault("striated", "striated layer")
    names.setdefault("isotropic", "isotropic layer")
    reach = int(max_shift * k + 20)
    longer = max(int(round(clip.fps)), k)                 # a pair held still over k frames is measured again over a second
    trk = {n: p for n, p in track.items() if clip.n0 <= n <= clip.n1} if track else None
    with gpu.on(gpu.card()):                              # nine frames filtered: on a card where there is one, which
        size, size_fields = template_size(clip, masks, rows)      # gives the CPU's filtered frame to the last bit

    # The templates are minutes of work and are kept beside the frames. What they depend on is in the
    # name: until 2026-09-20 the track was there only as "is there one", and --mask-rows and --max-shift
    # not at all, so a second run with a different track or caption mask silently reused the first's.
    # The templates' size is in it where it is not the usual 128 px, so that every earlier cache still holds.
    made_from = repr((reach, rows, sorted((n, round(x, 2), round(y, 2)) for n, (x, y) in trk.items()) if trk else None,
                      "held still: again over", longer, "stride 48, within 5 px, a window every", max(longer // 2, 1),
                      "unmoved between catch-ups", CATCH_UP, MIN_SWITCHES, MAX_BETWEEN, AT_ZERO, REPEAT_SHARE, "held but moved", HELD_BUT_MOVED,
                      "each template's own error", vf.PEAK_ERR_SCALE, vf.PEAK_FLOOR_PX, vf.PK_GAP,
                      "the vote along the streaks", vf.VOTE_LEAD, vf.VOTE_FLOOR_PX, "zero left out read first",
                      "a tint is not symbology", vf.TINT_FIFTH, vf.TINT_SHARE)
                     + (() if size == TEMPLATES else ("templates", size)))
    # ... and what computes them, where it is a graphics card: its templates agree with the CPU's to a hundredth of
    # their own errors and not to the last bit (method section 52), so they are kept apart. A run on the CPU never
    # reads a card's, and its own cache is named as it always was.
    card = gpu.card()
    if card is not None:
        made_from = repr((made_from, "matched on a graphics card"))
    cache = clip.dir / (f"bg_layers_k{k}_s{step}_{clip.n0}_{clip.n1}_"
                        f"{hashlib.sha1(made_from.encode()).hexdigest()[:10]}.npz")
    if cache.exists() and not fresh:
        tpl = np.load(cache)["tpl"]
        gpu.took_part(card)
        say(f"templates from {cache} (measured earlier with the same frames, track and masks; --fresh measures again)")
    else:
        # Two rounds on one pool: every pair over k frames, then, for the pairs held still, the second
        # passes -- one an L-frame window, shared by the pairs nearest it (`window_start`), not one a pair.
        # On a graphics card (`gpu.card`) the same two rounds in this process: the card matches a pair's templates
        # together, threads read the frames ahead of it (`Ahead`), and no pool is made.
        pairs = list(range(clip.n0, clip.n1 - k + 1, step))
        L = min(longer, clip.n1 - clip.n0)
        args = (clip.video, clip.dir, clip.n0, clip.n1, masks, rows, trk, k, reach, 9.0, False, longer, size)
        pool = first = None
        try:
            if card is not None:
                say(f"the frame pairs are matched on the graphics card, {card.name}")
                _G["filtered"] = {}
                first = vf.pooled_or_on_card(_G, _read, [n for a in pairs for n in (a, a + k)], procs, _first, pairs, _init, args,
                                             2, progress, stop, "Layers", pixels=clip.W * clip.H)
                _forget_card()
            if gpu.card() is None:                    # no card, or one that stopped: a pool of CPUs for what is left
                pool = pool_of(procs, _init, args, pixels=clip.W * clip.H)
                if first is None:
                    first = pooled(procs, _first, pairs, chunksize=2, progress=progress, stop=stop, what="Layers", pool=pool)
            first, _ = held_but_moved(first)
            _, unmoved = repeating(pairs, first, k, L, clip.n0, clip.n1) if L > k else (set(), set())
            starts = sorted({window_start(a, k, L, clip.n0, clip.n1) for a, (f, still) in zip(pairs, first)
                             if still and L > k and a not in unmoved})
            with gpu.on(None if pool is not None else gpu.card()):     # the card's round again, where it did the first
                again = dict(zip(starts, second_pass(pool, starts, clip.H, k, L, progress, stop, tpl=size)))
        finally:
            _forget_card()
            if pool is not None:
                pool.terminate()
                pool.join()
            if gpu.card() is not None:
                gpu.card().tidy()
        tpl = np.vstack([_rows(a, f, still, again.get(window_start(a, k, L, clip.n0, clip.n1)) if still and L > k else None, k, L,
                               unmoved=a in unmoved) for a, (f, still) in zip(pairs, first)])
        np.savez_compressed(cache, tpl=tpl)

    lay = {int(a): vf.layers_of(tpl[tpl[:, 0] == a], dark_below=dark_below) for a in np.unique(tpl[:, 0])}
    how = {int(r[0]): int(r[-2]) for r in tpl}           # MOVED, AGAIN, STILL or UNMOVED, one per pair
    for a, h in how.items():                             # the same picture, repeated: no layer of it moved
        if h == UNMOVED:
            own = lay[a]["all"][2] if lay[a].get("all") else None   # its own field's covariance: it agreed on zero
            lay[a].update({c: (np.zeros(2), max(lay[a]["n_good"], 1), own) for c in ("striated", "isotropic", "all")},
                          groups=1, inliers=1.0, group_gap=0.0)
    err = {a: np.sqrt(np.diag(l["all"][2])) for a, l in lay.items() if l.get("all") and l["all"][2] is not None}
    files = []
    if out:
        with open(f"{out}_layers.csv", "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["frame", "t_s", "x_px", "y_px"] + [f"{c}_{q}" for c in ("striated", "isotropic", "all")
                                                           for q in (f"dx{k}", f"dy{k}", "tpl")]
                        + ["groups", "inliers", "over_frames", "err_x_px", "err_y_px"])
            for n in clip.frames():
                row = [n, round(float(clip.t(n)), 4)] + ([round(v, 2) for v in trk[n]] if trk and n in trk else ["", ""])
                for c in ("striated", "isotropic", "all"):
                    v = lay.get(n, {}).get(c)
                    row += [round(v[0][0], 2), round(v[0][1], 2), v[1]] if v else ["", "", ""]
                wr.writerow(row + ([lay[n]["groups"], round(lay[n]["inliers"], 3), k if how[n] in (MOVED, UNMOVED) else longer]
                                   if n in lay else ["", "", ""])
                            + ([round(float(err[n][0]), 3), round(float(err[n][1]), 3)] if n in err else ["", ""]))
        files.append(f"{out}_layers.csv")
        say(f"wrote {out}_layers.csv")

    fk = clip.fps / k
    half = int(round(clip.fps / 2))
    need = int(0.8 * 2 * half / step)
    win = lambda s: vf.windowed(s, clip.n0, clip.n1, k, half, need) if s else {}
    vel = {c: {a: l[c][0] * fk for a, l in lay.items() if l[c]} for c in ("striated", "isotropic", "all")}
    par = win({a: vel["isotropic"][a] - vel["striated"][a] for a in set(vel["striated"]) & set(vel["isotropic"])})
    if trk:
        rel = {c: {a: (np.array(trk[a + k]) - np.array(trk[a])) * fk - v for a, v in vel[c].items()
                   if a in trk and a + k in trk} for c in vel}
    else:
        rel = vel
    w = {c: win(rel[c]) for c in rel}

    fields = dict(of="the object's rate against each layer" if trk else "each layer's screen speed",
                  tracked=bool(trk), k=k, step=step, names=names,
                  px_per_s={c: _spread(w[c]) for c in ("striated", "isotropic", "all")},
                  layer_against_layer=_spread(par) if par else None, object_over_parallax=None, templates=size_fields,
                  over_track=None)
    if trk:
        fields["over_track"] = {}
        for c in vel:
            s, read = over_track(trk, vel[c], k, clip.fps, half)
            sp = _spread(win(s))
            fields["over_track"][c] = dict(sp, read_share=read) if sp else None
    both = sorted(set(w["striated"]) & set(par)) if trk and par else []
    if both:
        rat = [np.hypot(*w["striated"][n]) / max(np.hypot(*par[n]), 1e-6) for n in both]
        ang = [np.degrees(np.arctan2(w["striated"][n][1], w["striated"][n][0]) - np.arctan2(par[n][1], par[n][0])) for n in both]
        ang = (np.array(ang) + 180) % 360 - 180
        fields["object_over_parallax"] = dict(ratio=float(np.median(rat)), ratio_p16=float(np.percentile(rat, 16)),
                                              ratio_p84=float(np.percentile(rat, 84)),
                                              directions_apart_deg=float(np.median(ang)))
    g = np.array([l["groups"] for l in lay.values()])
    two = np.array([l.get("group_gap", 0) for l in lay.values() if l["groups"] == 2]) * fk
    fields["motion_groups"] = dict(two_in_share_of_pairs=float(np.mean(g == 2)),
                                   apart_px_per_s=float(np.median(two)) if len(two) >= 5 else None,
                                   inside_a_group_share=float(np.median([l["inliers"] for l in lay.values()])))
    h = np.array(list(how.values()))
    fields["held_still"] = dict(over_frames=k, share_of_pairs=float(np.mean(h != MOVED)) if len(h) else 0.0,
                                again_over_frames=longer,
                                still_again_share=float(np.mean(h == STILL)) if len(h) else 0.0,
                                unmoved_share=float(np.mean(h == UNMOVED)) if len(h) else 0.0)
    # each pair's shift error over k frames, from its templates' own errors scaled to their scatter (K9)
    e = np.array(list(err.values())).reshape(-1, 2)
    fields["shift_error_px"] = (dict(over_frames=k, pairs=len(e), median=[float(x) for x in np.median(e, 0)],
                                     p84=[float(x) for x in np.percentile(e, 84, axis=0)],
                                     ridge_share=float(np.mean([l["n_ridge"] / max(l["n_good"] + l["n_ridge"], 1) for l in lay.values()])))
                                if len(e) else None)

    written = []
    if scene and fields["held_still"]["still_again_share"] > SCENE_SHARE:
        blocks, _ = read_scene_under(clip, masks, rows, trk, how, k, reach, size, longer, made_from, procs=procs, fresh=fresh, say=say,
                                     progress=progress, stop=stop)
        fields["scene"] = whole.summary(blocks)
        if out:
            whole.write_csv(f"{out}_scene.csv", blocks)
            written.append(f"{out}_scene.csv")
            say(f"wrote {out}_scene.csv")

    result, npw, notes = {}, [], []
    for c in ("striated", "isotropic", "all"):
        s = fields["px_per_s"][c]
        if s:
            result[("object against the " if trk else "screen speed of the ") + names.get(c, "whole scene (largest group)")] = (
                f"median {s['median']:.0f} px/s (16-84 %: {s['p16']:.0f}-{s['p84']:.0f}; {s['windows']} one-second windows)"
                + (f"; over the whole track, every second once, median {o['median']:.0f} px/s ({o['windows']} windows; "
                   f"the layer read on {o['read_share']:.0%} of it)"
                   if trk and (o := (fields["over_track"] or {}).get(c)) else ""))
    if fields["layer_against_layer"]:
        s = fields["layer_against_layer"]
        result[f"the {names['isotropic']} against the {names['striated']}"] = (
            f"median {s['median']:.0f} px/s (16-84 %: {s['p16']:.0f}-{s['p84']:.0f})")
        notes.append("More than one background layer: any rate quoted here must name "
                     "which layer it is against.")
    if size_fields["smaller_because_few"]:
        result["templates"] = _templates_said(size_fields)
    hs = fields["held_still"]
    if hs["share_of_pairs"] > 0:
        result["scene held still"] = (f"in {hs['share_of_pairs']:.0%} of pairs over {k} frames, which were measured again "
                                      f"over {longer}; held still over those too in {hs['still_again_share']:.0%}"
                                      + (f"; {hs['unmoved_share']:.0%} of pairs sit between the catch-up steps of a picture "
                                         "that repeats, and were taken as unmoved, not measured again"
                                         if hs.get("unmoved_share") else ""))
    under = whole.reported(fields.get("scene"))
    if under:
        result["the scene under the sensor's pattern"] = under
    if hs["still_again_share"] > 0.5:
        npw.append(("layers", f"the scene is held still on screen even over {longer} frames in "
                              f"{hs['still_again_share']:.0%} of pairs: a background rate there is an upper limit, "
                              f"not a measurement (a pattern on the sensor can hold it at zero)"))
    if not any(fields["px_per_s"].values()):
        npw.append(("layers", "no one-second window had enough frame pairs with a consensus background motion: "
                              "the scene is held still, has too little texture, or the window is under a second"))
    if out:
        figure(Path(f"{out}_layers.png"), clip, names, w, par, {a: l["groups"] for a, l in lay.items()}, say=say)
        files.append(f"{out}_layers.png")
    return Found("layers", result, fields, no_power=npw, notes=notes, files=files + written, carry=dict(reach=reach))


def _templates_said(t):
    return (f"{t['px']} px (stride {t['stride']}), not 128: on the median of {t['sampled_frames']} frames only "
            f"{t['clear_textured_128px']:.0f} templates of 128 px fit clear of the symbology and the masks with texture to "
            f"match on (under {FEW_TEMPLATES}, and a consensus needs 8)")


def said(fields):
    """What `mcdonald layers` prints of a measurement, line by line, from its fields."""
    names, L = fields["names"], []

    def describe(label, s):
        if s:
            L.append(f"  {label:44s} median {s['median']:5.0f}  16-84 %: {s['p16']:5.0f}-{s['p84']:5.0f}"
                     f"  range {s['min']:5.0f}-{s['max']:5.0f} px/s  ({s['windows']} windows)")

    L.append("object's rate against" if fields["tracked"] else "screen speed of")
    for c in ("striated", "isotropic", "all"):
        describe(f"the {names.get(c, 'whole scene (largest group)')}", fields["px_per_s"][c])
        o = (fields.get("over_track") or {}).get(c)
        if o and fields["px_per_s"][c]:
            L.append(f"  {'':44s} over the whole track, every second once: median {o['median']:.0f}  16-84 %: "
                     f"{o['p16']:.0f}-{o['p84']:.0f} px/s  ({o['windows']} windows; the layer read on "
                     f"{o['read_share']:.0%} of its pairs, carried across the rest)")
    if fields["layer_against_layer"]:
        L.append("layer against layer")
        describe(f"the {names['isotropic']} against the {names['striated']}", fields["layer_against_layer"])
        r = fields["object_over_parallax"]
        if r:
            L.append(f"  object-vs-{names['striated']} over {names['isotropic']}-vs-{names['striated']}: ratio "
                     f"{r['ratio']:.1f} ({r['ratio_p16']:.1f}-{r['ratio_p84']:.1f}), directions "
                     f"{r['directions_apart_deg']:+.0f} deg apart. A stationary object gives parallel motion at a constant ratio.")
    t = fields.get("templates")
    if t and t["smaller_because_few"]:
        L.append("templates: " + _templates_said(t))
    h = fields.get("held_still")
    if h and h["share_of_pairs"] > 0:
        L.append(f"held still over {h['over_frames']} frames in {h['share_of_pairs']:.0%} of pairs, measured again over "
                 f"{h['again_over_frames']}; still over those too in {h['still_again_share']:.0%} (an upper limit there)"
                 + (f"; {h['unmoved_share']:.0%} between the catch-up steps of a picture that repeats, unmoved"
                    if h.get("unmoved_share") else ""))
    m = fields["motion_groups"]
    L.append(f"motion groups: two in {m['two_in_share_of_pairs']:.1%} of pairs"
             + (f", {m['apart_px_per_s']:.0f} px/s apart (median)" if m["apart_px_per_s"] is not None else "")
             + f"; templates inside a group: {m['inside_a_group_share']:.0%} (rigid scenes are near 100 %)")
    e = fields.get("shift_error_px")
    if e:
        L.append(f"each pair's shift error over {e['over_frames']} frames, from its templates' own errors scaled to their "
                 f"scatter: median +/-{e['median'][0]:.2f}, +/-{e['median'][1]:.2f} px (x, y); 84 % under "
                 f"+/-{e['p84'][0]:.2f}, +/-{e['p84'][1]:.2f}"
                 + (f"; {e['ridge_share']:.0%} of the templates sure only across a ridge" if e["ridge_share"] >= 0.05 else ""))
    if fields.get("scene"):
        L += whole.said(fields["scene"])
    return L


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--k", type=int, default=5, help="baseline, frames")
    ap.add_argument("--step", type=int, default=1, help="measure every step-th pair")
    ap.add_argument("--max-shift", type=float, default=45, help="fastest scene motion to look for, px/frame")
    ap.add_argument("--track", help="CSV with frame and x/y columns")
    ap.add_argument("--auto-track", action="store_true", help="track a compact source (check the strip it writes)")
    ap.add_argument("--size", type=float, default=9.0, help="source diameter for --auto-track, px")
    ap.add_argument("--dark", action="store_true", help="the source is darker than the scene")
    ap.add_argument("--seed", help="n,x,y: where the source is in frame n")
    ap.add_argument("--marks", metavar="JSON",
                    help="a _marks.json from `mcdonald mark`: link the track from the hand marks, which give it the "
                    "detector's scale, its polarity and the velocity. The way to track an object too fast "
                    "for --auto-track to acquire")
    ap.add_argument("--mask-rows", help="y0:y1[:n0:n1],... burned-in captions the static masks miss")
    ap.add_argument("--mask-box", action="append", metavar="X0,Y0,X1,Y1[:N0:N1]",
                    help="a box of graphics drawn in place mid-picture -- a tape, an arrow, a reticle -- that the static "
                         "masks miss and would hold pairs at zero shift (repeat)")
    ap.add_argument("--dark-below", type=float, help="striated templates must be darker than this (open sea in white-hot IR)")
    ap.add_argument("--names", default="striated=striated layer,isotropic=isotropic layer",
                    help="e.g. striated=sea,isotropic=cloud tops")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--composite", type=int)
    ap.add_argument("--out", metavar="DIR", help="case directory for results "
                    "(default: ./<tag>, or $MCDONALD_CASES/<tag>; with --n0/--n1, the segment's own folder in it, <tag>/segment-<n0>-<n1>)")
    ap.add_argument("--procs", type=int, default=None, help=PROCS_HELP)
    ap.add_argument("--no-scene", action="store_true",
                    help="do not read a clip held still under its sensor's pattern by whole blocks (`mcdonald scene`, <tag>_scene.csv)")
    ap.add_argument("--fresh", action="store_true",
                    help="measure again: do not reuse the templates an earlier run left in the work directory")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        found, clip = _main(args)
    if args.json:
        emit(found.envelope("layers", inputs_of(args), clip, said=lines))
    return 0


def _main(args):
    video, tag, _ = vf.resolve(args.video)
    clip = vf.Clip(video, args.workdir, args.n0, args.n1)
    out = vf.out_prefix(args.out, tag, vf.named(args.n0, args.n1, clip))
    names = dict(p.split("=") for p in args.names.split(","))
    rows = vf.parse_rows(args.mask_rows) + vf.parse_boxes(args.mask_box)
    masks = vf.static_masks(clip)
    reach = int(args.max_shift * args.k + 20)
    print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}; "
          f"masked: blocks {masks['blocks'].mean():.1%}, graphics {masks['graphics'].mean():.1%}")
    checked = validate(clip, masks, rows, args.k, reach) if args.validate else None

    trk = vf.read_track(args.track) if args.track else None
    from . import autolink
    here = None if trk else autolink.marks_here(out, args.marks)
    if here:
        print(here)
    if args.marks and not trk:
        trk = autolink.track_from_marks_file(clip, args.marks, out, masks=masks, rows=rows, procs=args.procs)
    elif args.auto_track:
        seed = tuple(float(v) for v in args.seed.split(",")) if args.seed else None
        trk = auto_track(clip, masks, rows, args.size, args.dark, seed, out, args.procs, progress=to_stderr())

    found = measure(clip, masks, rows, trk, k=args.k, step=args.step, max_shift=args.max_shift, names=names,
                    dark_below=args.dark_below, out=out, procs=args.procs, fresh=args.fresh, progress=to_stderr(),
                    scene=not args.no_scene)
    if args.marks and trk and not args.track:             # the link wrote these on the way: they are this command's files too
        found.files[:0] = [f"{out}_autotrack.csv", f"{out}_autotrack_strip.png"]
    elif args.auto_track and trk:
        found.files.insert(0, f"{out}_track_strip.png")
    if here:
        found.notes.append(here)
    print("\n".join(said(found.fields)))
    if args.composite:
        fa = args.composite
        ga, ba = clip.grey(fa), vf.frame_mask(clip.rgb(fa), masks, rows, fa)
        gb, bb = clip.grey(fa + args.k), vf.frame_mask(clip.rgb(fa + args.k), masks, rows, fa + args.k)
        name = Path(f"{out}_composite_{fa}.png")
        found.fields["composite"] = composite(clip, fa, args.k, vf.layers_of(vf.shift_field(ga, gb, ba, bb, reach=reach),
                                                                             dark_below=args.dark_below), name)
        if name.exists():
            found.files.append(str(name))
    if checked is not None:
        found.fields["validation"] = checked
    return found, clip


if __name__ == "__main__":
    raise SystemExit(main())
