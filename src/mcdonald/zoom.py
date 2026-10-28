"""The camera's zoom states: where its optics change, and by how much, from the picture alone.

  mcdonald zoom VIDEO [--out DIR] [--json]

The MQ-9's MTS-B changes its field of view during a short burst of blank or flash frames, and every PURSUE clip
tried has them (PR27 four in 297 s, PR067 nine). A stage that fits one scale across such a burst fits two fields at
once. Here the bursts are found from a cheap pass over the whole clip (`scan`: every frame at 192 px wide, its
contrast and its change from the frame before, overlay left out), bursts under a second apart are merged (PR27 at
82 s is grey, then white, then grey within half a second), and each is fitted from the last good frame before it to
the first settled frame after it (`forensics.zoom_fit_frames`: the later frame shrunk by s and found anywhere in the
earlier, the overlay filled and zeroed, each side's fixed pattern taken out).

Each burst is then a boundary of one of three kinds:

- **step**: the scale changed by s (a measured number, with its ZNCC and the ZNCC at x1 it beat);
- **no step**: the picture matches itself at x1 better than at any scale a quarter or more off it -- a gain reset
  or a flash, the optics as they were;
- **unknown**: no trusted fit. Never a step, and never none: PR27's 134-s burst fits x1.00 on fixed pattern and
  haze where AARO's description says the camera zoomed, and its 89-s burst fits x6.00 at the grid's edge.

The stretches between boundaries are the zoom states. A state joined to the next by "no step" is the same state;
across "unknown", nothing about the scale carries over.

A zoom with no blank (an electronic zoom: PR051's leak, 2X to ULTN) steps the picture's level or contrast instead, and
those steps (`events.picture_steps` on the same scan, and any `--events` gives) are fitted the same way. One whose fit
measures a step is a boundary like a burst; one that does not is kept apart (`picture_steps`) and the scale is taken
to hold across it, since a gain reset or a switch of camera steps the picture too.

What it cannot do: see a continuous zoom, or measure one over a scene with no detail of its own (haze, a clear sky:
the fixed pattern is all there is).
"""
import json
import math
import subprocess

import numpy as np
from scipy import ndimage

from . import forensics as vf
from .clip import chroma_of, every_frame, grey_of

SCAN_WIDTH = 192        # px: the scan's frames, wide enough to tell a blank from a picture
MERGE_S = 1.0           # s: bursts closer than this are one change of the optics
PAD = 12                # frames: kept clear either side of a burst by any fit that must not span it
QUIET_X = 2.0           # a settled frame's change from its neighbours is within this many times the clip's usual there
SEARCH_S = 3.0          # s: how far either side of a burst a settled frame is looked for
FIXED_S = 8.0           # s: the stretch of each side whose fixed pattern is taken out
FIXED_N = 12            # frames sampled over it
JUMP_DN = 20.0          # grey levels: a frame whose mean level jumps this far from the last, its change also JUMP_X
JUMP_X = 5.0            # times the usual there, is part of a burst even with its contrast intact (AARO's Puerto Rico
                        # clip goes dark for three frames at each switch, contrast 15 of the usual 20-29, then white)
MAX_TERMS = 40          # runs of frames one ffmpeg select may name: its expression parser stops at about a hundred
MAX_PICTURE = 24        # the picture's steps with no blank fitted at most, the largest first (each fit takes seconds)
CONFIRM_D = (1, 2, 3)   # frames further out either side: the pairs a marginal fit is fitted again from
CONFIRM_N = 2           # of them, how many must be steps on their own, within CONFIRM_TOL of it and of each other
CONFIRM_TOL = 0.03


# ---- the scan ---------------------------------------------------------------------------
def scan(video, W, H, width=SCAN_WIDTH, progress=None):
    """Per frame of the whole clip (numbered from 1): its change from the previous frame (mean |difference|), its
    contrast (standard deviation) and its level (mean), all over the middle of a copy 192 px wide, leaving out pixels
    with a colour cast and pixels black or white -- a redaction box on a blank white frame would otherwise read as
    contrast. A frame with under a tenth of its pixels left has contrast 0. Columns as `forensics.frame_series` gives
    them (frame, change, contrast) and the level, so `forensics.transients` reads it as it is."""
    w = int(width)
    h = max(2, int(round(width * H / W / 2)) * 2)
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-vf", f"scale={w}:{h}:flags=area,format=rgb24",
           *every_frame(), "-f", "rawvideo", "-"]
    y0, y1, x0, x1 = h // 7, 6 * h // 7, w // 9, 8 * w // 9
    size = w * h * 3
    rows, prev, n = [], None, 0
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    try:
        while True:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            n += 1
            a = np.frombuffer(buf, np.uint8).reshape(h, w, 3)[y0:y1, x0:x1].astype(np.float32)
            g = grey_of(a)
            ok = (g > 8) & (g < 247) & ~ndimage.binary_dilation(chroma_of(a) > 40)
            if ok.mean() >= 0.1:
                sd, lv = float(g[ok].std()), float(g[ok].mean())
            else:
                sd, lv = 0.0, float(g.mean())
            d = float(np.abs(g - prev[0])[ok & prev[1]].mean()) if prev is not None and (ok & prev[1]).any() else np.nan
            rows.append((n, d, sd, lv))
            prev = (g, ok)
            if progress and n % 500 == 0:
                progress("Zoom scan", n, None)
    finally:
        p.stdout.close()
        p.wait()
    if p.returncode:
        raise RuntimeError(f"ffmpeg could not read {video} (exit {p.returncode})")
    return np.array(rows, float).reshape(-1, 4)


def merge(runs, gap):
    """Runs of frames (first, last) closer than `gap` frames joined into one."""
    out = []
    for a, b in sorted(runs):
        if out and a - out[-1][1] <= gap:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def jumps(series):
    """Frames whose mean level jumps by JUMP_DN or more from the frame before while their change is JUMP_X times the
    usual there (the 61-frame median): a blank that keeps its contrast, a flash's edge, a cut. A scene that moves
    changes the picture, not its mean level."""
    n, d, lv = series[:, 0].astype(int), series[:, 1], series[:, 3]
    dd = np.where(np.isfinite(d), d, 0.0)
    usual = ndimage.median_filter(dd, size=61, mode="nearest")
    step = np.abs(np.diff(lv, prepend=lv[:1]))
    return [(int(f), int(f)) for f in n[(step >= JUMP_DN) & (dd >= JUMP_X * np.maximum(usual, 0.5))]]


def bursts(series, fps, frac=0.35):
    """The blank or flash bursts: runs of contrast collapse (`forensics.transients`) and jumps of the level
    (`jumps`), those under MERGE_S apart merged."""
    return merge(vf.transients(series, frac=frac) + jumps(series), int(round(MERGE_S * fps)))


def edges(series, a, b, fps, last=None, first=None):
    """(the last good frame before the burst a..b, the first settled frame after it, the change counted quiet), with
    None for a side that has none within SEARCH_S (or before `last` / after `first`, the bursts either side).

    Good and settled: over the frame and the two after it, the change from frame to frame and the drift of the mean
    level both within QUIET_X times what is usual for the clip there -- the larger of the medians over the 2 s before
    the burst and over 1-3 s after it (a zoom in doubles the scene's motion in pixels, so the far side's usual is no
    smaller than its own) -- and the contrast not collapsed. The level is the gain: on AARO's Puerto Rico clip it
    climbs 2 grey levels a frame for ten frames after each blank, while the ground's own motion makes the change from
    frame to frame as large as that anyway (2026-10-20: the change alone took a frame one after the blank, mid-climb).
    PR27's 58-s step has a vignetted frame mid-zoom, held for several frames: it is no settled frame either, since the
    picture jumps again after it."""
    n, d, sd, lv = series[:, 0].astype(int), series[:, 1], series[:, 2], series[:, 3]
    at = {int(v): i for i, v in enumerate(n)}
    ref = ndimage.median_filter(sd, size=61, mode="nearest")
    drift = np.full(len(lv), np.nan)
    drift[:-2] = np.abs(lv[2:] - lv[:-2])
    w2 = int(round(2 * fps))
    pre = slice(max(at[a] - w2, 0), at[a] - 2)
    post = slice(at[b] + int(fps), at[b] + 3 * int(fps))

    def usual(x):
        vals = [float(np.nanmedian(x[sl])) for sl in (pre, post) if np.isfinite(x[sl]).any()]
        return max(vals) if vals else 0.0

    q = QUIET_X * usual(d) + 0.5
    q_lv = max(1.0, QUIET_X * usual(drift))

    def good(m):
        idx = [at.get(m + j) for j in (0, 1, 2)]
        if any(i is None for i in idx):
            return False
        i = idx[0]
        return (all(np.isfinite(d[j]) and d[j] <= q for j in idx) and np.isfinite(drift[i]) and drift[i] <= q_lv
                and sd[i] >= 0.6 * ref[i])

    reach = int(round(SEARCH_S * fps))
    lo = max(a - reach, (last or 0) + 1)
    before = next((m for m in range(a - 3, lo - 1, -1) if good(m)), None)
    hi = min(b + reach, (first or 10 ** 9) - 1)
    after = next((m for m in range(b + 1, hi - 2) if good(m)), None)
    return before, after, q


# ---- the fits ---------------------------------------------------------------------------
def picture_candidates(series, fps, blanks, extra=()):
    """Frames where the picture steps with no blank (`events.picture_steps` on the scan's level and contrast, and any
    `extra` frames given, such as `mcdonald events`' picture steps), those within MERGE_S of a burst left to it and
    those under MERGE_S apart merged; at most MAX_PICTURE, the largest steps first. PR051's leak's electronic zoom out
    (frames 1331-1341) is one. FLIR1's zoom at 2235 is not: over its sky neither the level nor the contrast of the
    scan steps, and the fixed pattern is most of the detail there (`camera` finds it from the object)."""
    from .events import SCENE_HOLD, picture_steps
    gap = int(round(MERGE_S * fps))
    st = picture_steps(series[:, 0], series[:, 3], series[:, 2])
    n = series[:, 0].astype(int)
    d = np.nan_to_num(series[:, 1])
    at = {int(v): i for i, v in enumerate(n)}

    def sharpest(f):
        """The frame of the largest change from the one before within SCENE_HOLD of f: where a step's medians tie
        over several frames, the step itself (a zoom with no blank changes the whole picture in one frame)."""
        i = at.get(int(f))
        if i is None:
            return int(f)
        lo, hi = max(0, i - SCENE_HOLD), min(len(n), i + SCENE_HOLD + 1)
        return int(n[lo + int(np.argmax(d[lo:hi]))])

    size = {}
    for x in st:
        f = sharpest(x["frame"])
        size[f] = max(size.get(f, 0.0), abs(x["after"] - x["before"]) / max(abs(x["before"]), 1.0))
    for f in extra or ():
        size.setdefault(sharpest(f), 1.0)
    keep = sorted(size, key=lambda f: -size[f])[:MAX_PICTURE]
    keep = [f for f in sorted(keep) if not any(a - gap <= f <= b + gap for a, b in blanks)]
    return merge([(f, f) for f in keep], gap)


def plan(series, fps, extra=()):
    """Each burst with what its fit needs: the frames either side (`edges`) and, for each side, FIXED_N frames
    spread over up to FIXED_S s of the same optics (kept PAD frames from the bursts either side) whose fixed pattern
    is taken out of it. The picture's steps with no blank (`picture_candidates`) are planned the same way, `kind`
    "picture" against a burst's "blank"."""
    n_last = int(series[-1, 0])
    blank = bursts(series, fps)
    B = sorted([(a, b, "blank") for a, b in blank] + [(a, b, "picture") for a, b in
                                                       picture_candidates(series, fps, blank, extra)])
    out = []
    for i, (a, b, kind) in enumerate(B):
        last = B[i - 1][1] if i else 0
        first = B[i + 1][0] if i + 1 < len(B) else n_last + 1
        before, after, q = edges(series, a, b, fps, last, first)
        fb = fa = None
        if before is not None:
            lo = max(before - int(FIXED_S * fps), last + PAD, 1)
            fb = sorted(set(np.linspace(lo, before, FIXED_N).round().astype(int).tolist()))
        if after is not None:
            hi = min(after + int(FIXED_S * fps), first - PAD, n_last)
            fa = sorted(set(np.linspace(after, hi, FIXED_N).round().astype(int).tolist()))
        out.append(dict(frames=[int(a), int(b)], kind=kind, before=before, after=after, quiet=q, fixed_before=fb,
                        fixed_after=fa))
    return out


def fetch(video, numbers):
    """Yield (n, rgb) for the frames `numbers` (from 1) in one pass of ffmpeg: a select of their runs."""
    numbers = sorted(set(int(n) for n in numbers))
    if not numbers:
        return
    info = vf.probe(video)
    W, H = info["width"], info["height"]
    runs = merge([(n, n) for n in numbers], 1)
    while len(runs) > MAX_TERMS:                       # join the two runs closest together; the frames between are
        i = int(np.argmin([b[0] - a[1] for a, b in zip(runs[:-1], runs[1:])]))   # read and passed over
        runs[i:i + 2] = [(runs[i][0], runs[i + 1][1])]
    want = set(numbers)
    sel = "+".join(f"between(n,{a - 1},{b - 1})" for a, b in runs)
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-vf", f"select='{sel}',format=rgb24", *every_frame(),
           "-f", "rawvideo", "-"]
    size = W * H * 3
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    got = 0
    try:
        for n in (m for a, b in runs for m in range(a, b + 1)):
            buf = p.stdout.read(size)
            if len(buf) < size:
                if not got:
                    p.wait()
                    raise RuntimeError(f"ffmpeg read no frame of {video}: "
                                       + p.stderr.read().decode("utf-8", "replace").strip()[-300:])
                break
            got += 1
            if n in want:
                yield n, np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    finally:
        p.stdout.close()
        p.kill()
        p.wait()


def fit_all(video, todo, masks=None, clip=None, progress=None):
    """Each planned burst fitted (`forensics.zoom_fit_frames`). The frames come from `clip` where it has every one
    of them saved as a picture already, else from one pass of ffmpeg; either way each is kept only until the last
    burst that needs it is fitted."""
    need = {}
    for i, p in enumerate(todo):
        if p["before"] is None or p["after"] is None:
            continue
        for n in [p["before"], p["after"]] + (p["fixed_before"] or []) + (p["fixed_after"] or []):
            need.setdefault(int(n), []).append(i)
    last_use = {n: max(v) for n, v in need.items()}
    store, done = {}, set()
    results = [None] * len(todo)

    def fit_one(i):
        p = todo[i]
        fixed = []
        for ns in (p["fixed_before"], p["fixed_after"]):
            sc, ms = [], []
            for n in ns or []:
                g, col = store[n]
                m = vf.zoom_mask(g, col)
                sc.append(vf.zoom_scene(g, m))
                ms.append(m)
            fixed.append(vf.zoom_fixed(sc, ms))
        r = vf.zoom_fit_frames(store[p["before"]], store[p["after"]], *fixed, masks=masks)
        results[i] = r
        done.add(i)
        if progress:
            progress("Zoom fits", len(done), len(todo))

    saved = clip is not None and all(clip.path(n).exists() for n in need)
    frames = ((n, clip.rgb(n)) for n in sorted(need)) if saved else fetch(video, sorted(need))
    for n, a in frames:
        a = np.asarray(a, np.float32)
        store[n] = (grey_of(a), chroma_of(a) > 30)
        for i in sorted(set(need[n])):
            if i not in done and all(m in store for m, users in need.items() if i in users):
                fit_one(i)
        for m in [m for m in store if last_use[m] in done and all(u in done for u in need[m])]:
            del store[m]
    return results


def marginal(r):
    """Is a fit unknown only for want of a lead over the best scale a quarter or more from it -- on the grid inside its
    edges, ZOOM_MIN_PROM MADs or more over its surface, leading x1 as a step must, its ZNCC over the floor, its fixed
    pattern not most of its detail, and a step of scale, not none? AARO's Puerto Rico clip's 142.6-s switch is one
    (x1/3.096, the readout's 1/3, leading the next scale by x1.13); so is PR27's 89-s haze, which matches its fixed
    pattern."""
    if r is None or r["verdict"] != "unknown" or r["at_edge"]:
        return False
    fs = [x for x in (r.get("fixed_share") or []) if x is not None]
    return (r["prominence"] >= vf.ZOOM_MIN_PROM and r["prominence"] < vf.ZOOM_PROM_RATIO * r["prominence_off"]
            and r["prominence"] >= vf.ZOOM_PROM_RATIO * r["prominence_at_1"] and r["zncc"] >= vf.ZOOM_MIN_ZNCC
            and abs(math.log(r["s"])) > math.log(vf.ZOOM_SAME) and all(x <= vf.ZOOM_FIXED_MAX for x in fs))


def confirm(video, todo, results, masks=None, clip=None, n_last=None, progress=None):
    """A marginal fit (`marginal`) fitted again from the pairs CONFIRM_D frames further out either side, the same
    fixed patterns taken out: a step where CONFIRM_N of them are steps on their own -- each passing every rule, its
    lead too -- within CONFIRM_TOL of it and of each other, at their median with it (`confirmed_by` the pairs'
    offsets). Each pair must pass the whole bar by itself, so the bar for a trap is not lowered: PR27's 89-s haze
    fits x3.127 from every pair out to 4 frames -- the same scale to the digit, as a match on what does not move with
    the scene would -- and no pair leads by x1.25. The pairs tried are kept with the burst (`confirm`)."""
    extra, owner = [], []
    for i, (p, r) in enumerate(zip(todo, results)):
        if not marginal(r):
            continue
        lo = todo[i - 1]["frames"][1] + 1 if i else 1
        hi = todo[i + 1]["frames"][0] - 1 if i + 1 < len(todo) else (n_last or 10 ** 9)
        for d in CONFIRM_D:
            b, a = p["before"] - d, p["after"] + d
            if b >= lo and a <= hi:
                extra.append(dict(p, before=b, after=a))
                owner.append((i, d))
    if not extra:
        return results
    again = fit_all(video, extra, masks, clip, progress)
    out = list(results)
    for i in sorted({o[0] for o in owner}):
        r = results[i]
        tried = [(d, x) for (j, d), x in zip(owner, again) if j == i and x is not None]
        ok = [(d, x["s"]) for d, x in tried if x["verdict"] == "step" and abs(math.log(x["s"] / r["s"])) <= math.log1p(CONFIRM_TOL)]
        agree = len(ok) >= CONFIRM_N and max(v for _, v in ok) / min(v for _, v in ok) <= 1 + CONFIRM_TOL
        rec = [dict(d=d, s=round(float(x["s"]), 4), verdict=x["verdict"]) for d, x in tried]
        if agree:
            out[i] = dict(r, verdict="step", s=float(np.median([r["s"]] + [v for _, v in ok])), confirm=rec,
                          confirmed_by=[d for d, _ in ok],
                          why=f"marginal across the burst (x{r['s']:.3f}), confirmed by {len(ok)} of the "
                              f"{len(tried)} pairs further out: " + ", ".join(f"x{v:.3f}" for _, v in ok))
        else:
            out[i] = dict(r, confirm=rec, why=r["why"] + f"; the pairs further out do not confirm it ("
                                                          + ", ".join(f"{x['d']}: {x['verdict']} x{x['s']:.2f}" for x in rec) + ")")
    return out


class _Sample:
    """Frames held in memory with the face of a Clip that `forensics.static_masks` reads: n0, n1, W, H, rgb(n)."""

    def __init__(self, frames, n0, n1, W, H):
        self.frames, self.n0, self.n1, self.W, self.H = frames, n0, n1, W, H

    def rgb(self, n):
        return np.asarray(self.frames[int(n)], np.float32)


def overlay_masks(video, W, H, n_last, clip=None, n_sample=40):
    """The clip's static overlay (`forensics.static_masks`) from n_sample frames spread over the whole clip, read
    from `clip` where it has them all saved, else from one pass of ffmpeg. A display that draws grey or white text and
    tapes over a light scene (AARO's Puerto Rico clip) is not caught by the fit's own colour and black-or-white mask."""
    ns = np.linspace(1, n_last, min(n_sample, n_last)).astype(int).tolist()
    if clip is not None and all(clip.path(n).exists() for n in ns):
        frames = {n: clip.rgb(n) for n in ns}
    else:
        frames = {n: np.array(a) for n, a in fetch(video, ns)}
    return vf.static_masks(_Sample(frames, 1, n_last, W, H), n_sample=n_sample)


# ---- the states -------------------------------------------------------------------------
def boundaries(todo, results, fps):
    """One row a burst: where it is, the frames fitted, and the verdict -- "step" with s, "no step", or "unknown"
    with why (a side with no settled frame is unknown too)."""
    out = []
    for p, r in zip(todo, results):
        a, b = p["frames"]
        row = dict(frames=[a, b], t_s=[round((a - 1) / fps, 3), round((b - 1) / fps, 3)], kind=p.get("kind", "blank"),
                   before=p["before"], after=p["after"])
        if r is None:
            side = "before" if p["before"] is None else "after" if p["after"] is None else None
            row.update(verdict="unknown", s=None, why=f"no settled frame {side} the burst within {SEARCH_S:g} s" if side
                       else "its frames could not be read")
        else:
            r = dict(r)
            r.pop("scores", None)
            row.update(verdict=r["verdict"], s=r["s"] if r["verdict"] != "unknown" else None, fitted_s=r["s"],
                       zncc=r["zncc"], zncc_at_1=r["zncc_at_1"], prominence=r["prominence"],
                       prominence_at_1=r["prominence_at_1"], prominence_off=r["prominence_off"],
                       zncc_off=r.get("zncc_off"), led_by_zncc=r.get("led_by_zncc", False), at_edge=r["at_edge"],
                       centre=r["centre"], fixed_share=r["fixed_share"], why=r["why"],
                       **({"confirmed_by": r["confirmed_by"]} if r.get("confirmed_by") else {}),
                       **({"confirm": r["confirm"]} if r.get("confirm") else {}))
        out.append(row)
    return out


def states_of(rows, n_last, fps):
    """The stretches between bursts, numbered; a burst that is "no step" joins the stretches either side into one
    state. Each state's magnification against the first state of its chain (the product of the measured steps
    since the last "unknown"), and the chain it is on: across an unknown boundary nothing about the scale carries."""
    st, cur, chain, mag = [], 0, 0, 1.0
    start = 1
    for r in rows + [None]:
        end = (r["frames"][0] - 1) if r else n_last
        st.append(dict(state=cur, chain=chain, magnification=round(mag, 4), frames=[start, end],
                       t_s=[round((start - 1) / fps, 3), round((end - 1) / fps, 3)]))
        if r is None:
            break
        start = r["frames"][1] + 1
        if r["verdict"] == "step":
            cur, mag = cur + 1, mag * r["s"]
        elif r["verdict"] == "unknown":
            cur, chain, mag = cur + 1, chain + 1, 1.0
    return st


def state_at(states, t):
    """The state a time (s) falls in, or None inside a burst."""
    for s in states:
        if s["t_s"][0] <= t <= s["t_s"][1]:
            return s["state"]
    return None


def measure(video, W, H, fps, series=None, masks=None, clip=None, out=None, progress=None, extra=()):
    """The stage: the scan (unless `series` is given), the bursts, their fits, and the states. `clip`: a Clip whose
    saved frames are read where it has them all. `extra`: frames where the picture is known to step (`mcdonald
    events`' picture steps), fitted beside the scan's own.

    A picture step with no blank is a boundary only where its fit measures a step: a gain reset or a switch of
    camera steps the level too, and an unknown there is no reason to doubt the scale either side (a blank burst's
    is). The others are kept in `picture_steps`, each with its verdict."""
    from .report import Found
    if series is None:
        series = scan(video, W, H, progress=progress)
    todo = plan(series, fps, extra)
    n_last = int(series[-1, 0]) if len(series) else 0
    if masks is None and any(p["before"] is not None and p["after"] is not None for p in todo):
        masks = overlay_masks(video, W, H, n_last, clip)
    results = fit_all(video, todo, masks, clip, progress)
    results = confirm(video, todo, results, masks, clip, n_last, progress)
    every = boundaries(todo, results, fps)
    rows = [r for r in every if r["kind"] == "blank" or r["verdict"] == "step"]
    pictures = [r for r in every if r["kind"] == "picture"]
    states = states_of(rows, n_last, fps)
    n_step = sum(r["verdict"] == "step" for r in rows)
    n_unk = sum(r["verdict"] == "unknown" for r in rows)
    fields = dict(frames=n_last, bursts=rows, states=states, steps=n_step, no_steps=sum(r["verdict"] == "no step" for r in rows),
                  unknown=n_unk, pad_frames=PAD, merge_s=MERGE_S, picture_steps=pictures)
    n_blank = sum(r["kind"] == "blank" for r in rows)
    result = {"bursts": f"{n_blank} of blank or flash frames, {len(rows) - n_blank} a step of the picture with no blank: "
                        f"{n_step} a step, {fields['no_steps']} no step, {n_unk} unknown",
              "states": f"{len(states)} in {states[-1]['chain'] + 1 if states else 0} chain(s) of known scale"}
    if pictures:
        result["picture steps"] = (f"{len(pictures)} with no blank fitted: "
                                   f"{sum(r['verdict'] == 'step' for r in pictures)} a zoom (a boundary above), "
                                   f"{sum(r['verdict'] == 'no step' for r in pictures)} no change of scale, "
                                   f"{sum(r['verdict'] == 'unknown' for r in pictures)} not measured (taken as none)")
    npw = []
    if n_unk:
        npw.append(("zoom", f"{n_unk} of {len(rows)} bursts have no trusted fit: the scale either side of them is not "
                            "known to be the same, nor known to differ"))
    files = []
    if out:
        files.append(write(f"{out}_zoom.json", fields))
    return Found("zoom", result, fields, no_power=npw, files=files,
                 notes=["A zoom is found only where the picture blanks, flashes or steps while it happens; a continuous "
                        "zoom is not seen."])


def write(path, fields):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fields, f, indent=1)
    return path


def read(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def picture_events(path):
    """The frames of a `mcdonald events` _events.csv where the whole picture steps (its level or its contrast), the
    first frame at the new value: what `measure`'s `extra` takes."""
    import csv
    with open(path, newline="", encoding="utf-8") as fh:
        return sorted({int(round(float(r["frame"]))) for r in csv.DictReader(fh)
                       if r["kind"] == "picture" and " steps " in r["what"]})


def said(f):
    n_blank = sum(r.get("kind", "blank") == "blank" for r in f["bursts"])
    L = [f"{n_blank} burst(s) of blank or flash frames (those under {f['merge_s']:g} s apart merged)"
         + (f", and {len(f['bursts']) - n_blank} zoom(s) with no blank" if len(f["bursts"]) > n_blank else "")]
    for r in f["bursts"]:
        head = (f"t {r['t_s'][0]:7.2f}-{r['t_s'][1]:7.2f} s (frames {r['frames'][0]}-{r['frames'][1]}"
                + (", no blank: the picture steps" if r.get("kind") == "picture" else "") + ")")
        if r["verdict"] == "step":
            L.append(f"{head}: a STEP of x{r['s']:.3f} (ZNCC {r['zncc']:.2f}; its peak {r['prominence']:.1f} MADs over its "
                     f"surface, at x1 {r['prominence_at_1']:.1f}, a quarter or more off {r['prominence_off']:.1f}), frames "
                     f"{r['before']} | {r['after']}" + (f"; {r['why']}" if r.get("confirmed_by") else ""))
        elif r["verdict"] == "no step":
            L.append(f"{head}: no step (x{r['s']:.3f}, ZNCC {r['zncc']:.2f}; {r['prominence']:.1f} MADs, a quarter or more "
                     f"off {r['prominence_off']:.1f}), frames {r['before']} | {r['after']}")
        else:
            L.append(f"{head}: UNKNOWN -- {r['why']}")
    others = [r for r in f.get("picture_steps", []) if r["verdict"] != "step"]
    if others:
        L.append(f"{len(others)} step(s) of the picture with no blank, not a zoom: " + ", ".join(
            f"{r['t_s'][0]:.2f} s ({'no change of scale' if r['verdict'] == 'no step' else 'not measured'})"
            for r in others[:8]) + (" ..." if len(others) > 8 else ""))
    for s in f["states"]:
        L.append(f"state {s['state']}: t {s['t_s'][0]:.2f}-{s['t_s'][1]:.2f} s, "
                 + (f"x{s['magnification']:.3f} of the first state on its chain" if s["magnification"] != 1.0 else
                    "the first state of its chain") + f" (chain {s['chain']})")
    return L


def main():
    import argparse
    from . import clip as vclip
    from .report import emit, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--workdir", help="where the clip's frames are saved as pictures (f%%05d.png, numbered from 1; "
                                      "default: the storage folder's, as `layers` leaves them): read from there where "
                                      "they are all saved, else from the video")
    ap.add_argument("--events", metavar="CSV", help="a `mcdonald events` _events.csv: its steps of the whole picture "
                    "are fitted too, beside those this pass finds itself")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        video, tag, _ = vf.resolve(args.video)
        clip = vclip.Clip(video, args.workdir, extract=False)
        out = vclip.out_prefix(args.out, tag)
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps")
        extra = picture_events(args.events) if args.events else ()
        if args.events:
            print(f"{len(extra)} step(s) of the picture from {args.events}")
        found = measure(video, clip.W, clip.H, clip.fps, clip=clip, out=out, extra=extra)
        print("\n".join(said(found.fields)))
        for w in found.no_power:
            print(f"no power: {w[1]}")
        for f in found.files:
            print(f"wrote {f}")
    code = 0
    if args.json:
        emit(found.envelope("zoom", inputs_of(args), clip, said=lines, exit_code=code))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
