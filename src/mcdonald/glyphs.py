"""Digits in a display's own font, taken from its clock and offered as readings of its other readouts.

`events` and `symbology --method atflir` time every change of a readout but read no value. At 352 x 240 a glyph is 7 px
high and the copies blur it to 4-px strokes, and no general reader reads that reliably. A clip's clock does better. Its
seconds digit runs through 0-9 once every ten seconds, so once a person has read it on one frame, each of its looks is a
known digit, drawn in the display's own font, at its size, through its blur. Those ten looks are templates. A readout
drawn in the same font (the ATFLIR draws all its text with one character generator) is matched against them glyph by
glyph, and its likeliest digits are offered beside the sheet a person reads it off.

They are suggestions, never readings. A person still says what each look reads. A suggestion with a low score, one
whose best glyph is barely ahead of the next, or a glyph shorter than the digits (a degree mark, a point) is shown as
`?`. Letters (`L`, `R`) are not among the clock's digits, and with digits alone they match a digit well: on FLIR1's VCD
copy an `L` comes out as an 8 or a 1. So letters can be given too, from text that does not change and that a person has
read once (`letter_templates`: FLIR1's `RTCL` and `NAR` give R, T, C, L, N and A). They are not matched beside the digits
everywhere: cut from text that holds still, they are sharper than the clock's digits and outscore them on true digits
(on FLIR1's azimuth `O` took the 0, the 2, the 3 and the 6, and the digits read right fell from 8 of 11 to 1). A reading
is told which glyphs each place may hold (`read`'s `among` and `last`): the display's grammar, which `atflir` knows for the
ATFLIR (its azimuth is digits, then L or R). The sheet shows each suggestion beside its picture, so a glyph read as
another is seen at once.

How the clock's digits are told apart: the units digit's change from frame to frame, folded at the clip's second (a
median over every second, so that a flash or a weak tick does not move it), gives the clock's period and phase; each
frame's digit is the anchor's plus the whole seconds since it (mod 10). A clock that does not tick once a second,
steadily, is not used.
"""
import math

import numpy as np

from . import forensics as vf
from .report import Found

EDGE = 3               # frames left out either side of each of the clock's ticks when its templates are averaged
MIN_SCORE = 0.55       # a glyph whose best match is under this (normalised correlation) is shown as `?`
MIN_MARGIN = 0.04      # and so is one whose best digit leads the next by less than this
SHORT = 0.7            # and one under this share of the digits' height (a degree mark, a point)
SHIFT = 2              # px either way the templates are slid over a glyph
GAP = 1                # columns without strokes that end one glyph
RULE = 0.8             # a row lit over this share of a box's width is a rule (a border), not text
FAINT = 0.4            # a slot whose strongest stroke is under this share of the slots' median is residue, not a glyph
SHALLOW = 0.8          # a pitch cut moves to a low column only where it dips under this share of the columns round it
MIN_FRAMES = 3         # a digit needs this many frames to make a template
CONTRAST = 1.8         # the clock's changes, folded at its second, must stand this many times the box's usual change
                       # (FLIR1's clock: 2.6-3.7 at its ticks, against flashes that a median over its seconds ignores)


def _strokes(clip, box, frames, polarity=None):
    x0, y0, x1, y1 = box
    if polarity is None:
        polarity = vf.text_polarity(clip.grey(frames[len(frames) // 2])[y0:y1, x0:x1])
    return np.stack([vf.strokes(clip.grey(n)[y0:y1, x0:x1], polarity, clip.H) for n in frames]), polarity


def slots(img, min_frac=0.25, dip=0.6):
    """The glyphs of a box's strokes, left to right: [(x0, x1)]. A column belongs to a glyph where its strongest stroke is
    at least `min_frac` of the box's. Glyphs are split where GAP columns or more have none, and also at a column that
    dips under `dip` of the smaller of the peaks either side of it: a copy that blurs its text joins glyphs drawn a
    column apart (FLIR1's clock, `4135`, has no empty column between its digits). Rows lit over RULE of the width are
    left out first: a border drawn through the box is no glyph."""
    a_ = np.asarray(img, float)
    # a rule across the box (the picture's border under a clock) is no glyph: rows lit over most of the width go
    lit = a_ >= min_frac * max(a_.max(), 1e-6)
    rows = lit.mean(axis=1) < RULE
    col = (a_[rows] if rows.any() else a_).max(axis=0)
    on = col >= min_frac * max(col.max(), 1e-6)
    runs, start, gap = [], None, 0
    for x, v in enumerate(on):
        if v:
            if start is None:
                start = x
            gap = 0
        elif start is not None:
            gap += 1
            if gap >= GAP:
                runs.append((start, x - gap + 1))
                start, gap = None, 0
    if start is not None:
        runs.append((start, len(on)))
    out = []
    for a, b in runs:
        cut = [a]
        for x in range(a + 2, b - 2):
            left, right = col[max(a, x - 4):x].max(), col[x + 1:min(b, x + 5)].max()
            if col[x] < dip * min(left, right) and col[x] <= col[x - 1] and col[x] <= col[x + 1] and x - cut[-1] >= 2:
                cut.append(x)
        cut.append(b)
        out += [(c0, c1) for c0, c1 in zip(cut[:-1], cut[1:])]
    out = [(a, b) for a, b in out if b - a >= 1]
    # a slot much wider than the others holds two glyphs the blur joined without a dip: split at its lowest column in
    # its middle third (FLIR1's clock: `35` as one slot of 10 px beside slots of 5 and 6)
    if len(out) >= 3:
        w = float(np.median([b - a for a, b in out]))
        split = []
        for a, b in out:
            if b - a > 1.6 * w:
                lo, hi = a + (b - a) // 3, b - (b - a) // 3
                x = lo + int(np.argmin(col[lo:hi + 1])) if hi > lo else (a + b) // 2
                split += [(a, x), (x, b)]
            else:
                split.append((a, b))
        out = split
    return out


def clock_ticks(st, frames, fps, tol=0.01):
    """The ticks of a clock's last digit, found by folding: d(n), the mean change of its strokes from frame n-1 to n,
    is averaged (as a median, against flashes and weak ticks) at phase phi + k P for every whole second k, over
    periods P within `tol` of the clip's second and every half-frame phase; the best (P, phi) is the clock's.
    Returns (P, phi, contrast) or None: contrast is the median of d at the ticks over the median of d."""
    d = np.r_[np.nan, np.abs(np.diff(st, axis=0)).mean(axis=(1, 2))]
    n = len(d)
    base = float(np.nanmedian(d))
    best = None
    for P in np.linspace(fps * (1 - tol), fps * (1 + tol), 21):
        for phi in np.arange(1.0, P + 1.0, 0.5):
            idx = np.round(phi + P * np.arange(int((n - phi) / P) + 1)).astype(int)
            idx = idx[(idx >= 1) & (idx < n)]
            if len(idx) < 4:
                continue
            sc = float(np.median(d[idx]))
            if best is None or sc > best[0]:
                best = (sc, float(P), float(phi))
    if best is None or base <= 0:
        return None
    sc, P, phi = best
    # refined: the largest change within a frame of each folded tick, and a straight line through them -- the fold's
    # grid is half a frame, and a period a few hundredths of a frame out puts a boundary inside the clip's first second
    k = np.arange(int((n - phi) / P) + 1)
    near = []
    for kk in k:
        c = int(round(phi + P * kk))
        lo, hi = max(1, c - 1), min(n, c + 2)
        if hi > lo:
            j = lo + int(np.nanargmax(d[lo:hi]))
            near.append((kk, j))
    if len(near) >= 4:
        kk, jj = np.array(near, float).T
        P, a = np.polyfit(kk, jj, 1)
    else:
        a = round(phi)
    # index j of d is the change between frames[j - 1] and frames[j]: the tick is half a frame before frames[j]
    return float(P), float(frames[0]) + float(a) - 0.5, sc / base


def text_side(clip, box, frames):
    """The text's polarity in a box (+1 brighter than round it, -1 darker): the one whose median strokes split into the
    more glyphs. A box that text fills most of fools a guess from its grey's tails (FLIR1's clock: the gaps between its
    white glyphs came out as the strokes, and the box as one glyph)."""
    best = None
    for pol in (1, -1):
        st, _ = _strokes(clip, box, frames, pol)
        n = len(slots(np.median(st, axis=0)))
        if best is None or n > best[0]:
            best = (n, pol)
    return best[1]


def units_box(clip, clock_box, frames=None, polarity=None):
    """The box of the clock's last digit: its rightmost glyph, from the median of its strokes, with a pixel either side."""
    frames = frames or list(range(clip.n0, clip.n1 + 1, max(1, (clip.n1 - clip.n0) // 40)))
    polarity = polarity or text_side(clip, clock_box, frames)
    st, _ = _strokes(clip, clock_box, frames, polarity)
    med = np.median(st, axis=0)
    sl = slots(med)
    if not sl:
        return None
    a, b = sl[-1]
    x0, y0, x1, y1 = clock_box
    return (max(x0, x0 + a - 1), y0, min(x1, x0 + b + 1), y1)


def templates(clip, clock_box, at_frame, at_digit, step=1):
    """Ten digit templates from the clock's units digit: ({digit: strokes image}, fields). `at_frame` shows `at_digit`;
    the digit goes up by `step` (+1; -1 for a countdown) at each of the clock's seconds, timed from its changes."""
    sample = list(range(clip.n0, clip.n1 + 1, max(1, (clip.n1 - clip.n0) // 40)))
    pol = text_side(clip, clock_box, sample)
    ub = units_box(clip, clock_box, sample, pol)
    if ub is None:
        return None, dict(why="no glyph found in the clock's box")
    frames = list(range(clip.n0, clip.n1 + 1))
    st, pol = _strokes(clip, ub, frames, pol)
    found = clock_ticks(st, frames, clip.fps)
    if not found or found[2] < CONTRAST:
        return None, dict(units_box=list(ub), why="its last digit does not change once a second, steadily"
                          + (f" (its changes at the clip's second stand {found[2]:.1f} times its usual change, under "
                             f"{CONTRAST:g})" if found else "") + ": not a clock, or the copy blurs it past telling")
    P, t0, contrast = found
    p = (P, t0)                                               # tick k at t0 + P k, frames
    clk = dict(period_frames=P, first_tick=t0, contrast=contrast)
    def second(n):                                            # how many of the clock's seconds have begun by frame n
        return int(math.floor((n - p[1]) / p[0])) + 1
    s0 = second(at_frame)
    digit = {n: (at_digit + step * (second(n) - s0)) % 10 for n in frames}
    tick_at = p[0] * np.arange(math.floor((frames[0] - p[1]) / p[0]) - 1, math.ceil((frames[-1] - p[1]) / p[0]) + 2) + p[1]
    near = np.zeros(len(frames), bool)
    for i, n in enumerate(frames):
        near[i] = np.min(np.abs(tick_at - n)) <= EDGE
    tpl, counts = {}, {}
    for d in range(10):
        use = [i for i, n in enumerate(frames) if digit[n] == d and not near[i]]
        counts[d] = len(use)
        if len(use) >= MIN_FRAMES:
            tpl[d] = st[use].mean(axis=0)
    if tpl:
        # one crop for all ten, from their mean: the border's rows go and the digits keep their common frame
        box = trim_box(np.mean(list(tpl.values()), axis=0))
        tpl = {d: T[box[0]:box[1], box[2]:box[3]] for d, T in tpl.items()}
    # do the templates hold together? each digit's template against the others: a clock read wrongly (a tick missed by
    # the line, an anchor misread) makes two digits' templates the same glyph
    sim = {}
    for a in tpl:
        for b in tpl:
            if a < b:
                sim[(a, b)] = match(tpl[a], {b: tpl[b]})[0][1]
    worst = max(sim.items(), key=lambda kv: kv[1]) if sim else None
    return tpl, dict(units_box=list(ub), polarity=pol, clock=clk, ticks=int(len(frames) / P), frames_per_digit=counts,
                     most_alike=None if worst is None else dict(digits=list(worst[0]), ncc=float(worst[1])))


def pitch_cut(img, n, min_frac=0.25):
    """A box's strokes cut into `n` glyphs at a fixed pitch: the text's extent (its columns with a stroke at least
    `min_frac` of the strongest, rule rows left out as `slots` leaves them) in n equal steps, each cut where it falls,
    or at the lowest column within a quarter of a step of it where the strokes dip there (under SHALLOW of the columns
    round it). For text whose glyphs the blur has joined: a character generator draws every glyph in the same cell, and
    FLIR1's `NAR` dips nowhere under 0.85 of its peak between letters, so its cuts are the pitch's."""
    a_ = np.asarray(img, float)
    lit = a_ >= min_frac * max(a_.max(), 1e-6)
    rows = lit.mean(axis=1) < RULE
    col = (a_[rows] if rows.any() else a_).max(axis=0)
    on = np.flatnonzero(col >= min_frac * max(col.max(), 1e-6))
    if n < 1 or not len(on):
        return []
    a, b = int(on[0]), int(on[-1]) + 1
    step = (b - a) / n
    if step < 2:
        return []
    cuts = [a]
    for k in range(1, n):
        c = a + k * step
        lo, hi = max(cuts[-1] + 1, int(round(c - step / 4))), min(b - 1, int(round(c + step / 4)))
        if hi < lo:
            cuts.append(int(round(c)))
            continue
        w = col[lo:hi + 1]
        if w.min() >= SHALLOW * w.max():                  # no dip to follow: the pitch's own place
            cuts.append(min(max(int(round(c)), cuts[-1] + 1), b - 1))
            continue
        low = np.flatnonzero(w <= w.min() + 0.05 * (w.max() - w.min()))       # of columns about as low, the nearest
        cuts.append(lo + int(low[np.argmin(np.abs(lo + low - c))]))
    cuts.append(b)
    return [(c0, c1) for c0, c1 in zip(cuts[:-1], cuts[1:])]


def letter_templates(clip, box, text, frames, polarity=None, most=40):
    """Templates from a box of text that does not change, read once by a person: `text` is what the box says, one
    character to a glyph left to right (spaces left out), on `frames`. ({character: [strokes image, ...]}, fields), or
    (None, fields with `why`). Where the glyphs do not come out one to a character, the text is cut at the display's
    fixed pitch into as many as it has (`pitch_cut`, said in `cut`). A character seen more than once keeps each look:
    they are the same glyph drawn at different places on the copy's grid, and a reading takes the best of them."""
    chars = [c for c in str(text) if not c.isspace()]
    pick = list(frames)[:: max(1, len(frames) // most)][:most]
    info = dict(box=list(box), text=str(text), frames=[int(min(frames)), int(max(frames))] if len(frames) else [])
    if not chars or not pick:
        return None, dict(info, why="no text, or no frames to take it from")
    st, pol = _strokes(clip, box, pick, polarity)
    img = st.mean(axis=0)
    sl = slots(img)
    info.update(polarity=pol, glyphs=len(sl), cut="where the strokes part")
    if len(sl) != len(chars):
        sl = pitch_cut(img, len(chars))
        info["cut"] = f"at a fixed pitch, {len(sl)} cells ({info['glyphs']} glyphs parted on their own)"
    if len(sl) != len(chars):
        return None, dict(info, why=f"{info['glyphs']} glyphs found in the box, and the text has {len(chars)} characters, "
                                    "too narrow to cut at a pitch")
    out = {}
    for (a, b), c in zip(sl, chars):
        out.setdefault(c, []).append(trim(img[:, max(0, a - 1):b + 1]))
    info["pitch"] = float(sl[-1][1] - sl[0][0]) / len(sl)       # px from one glyph to the next: a word is read at it
    return out, info


def with_letters(tpl, *letters):
    """The clock's digit templates and letter templates (`letter_templates`'s) as one set to match against: a digit is
    its int, a letter its character, each a list of looks."""
    out = {d: [T] for d, T in (tpl or {}).items()}
    for L in letters:
        for c, Ts in (L or {}).items():
            key = int(c) if c.isdigit() else c
            out.setdefault(key, []).extend(Ts)
    return out


def _looks(T):
    return T if isinstance(T, list) else [T]


def _ncc(a, b):
    a = np.asarray(a, float) - np.mean(a)
    b = np.asarray(b, float) - np.mean(b)
    d = math.sqrt(float((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d > 0 else 0.0


def trim_box(img, min_frac=0.25):
    """(r0, r1, c0, c1): the rows and columns of a glyph's strokes with a stroke at least `min_frac` of the strongest,
    a pixel either side, leaving out rows lit over RULE of the width (a border through the box) and those under them."""
    a = np.asarray(img, float)
    lit = a >= min_frac * max(a.max(), 1e-6)
    rule = np.flatnonzero(lit.mean(axis=1) >= RULE)
    end = int(rule[0]) if len(rule) and rule[0] > a.shape[0] // 2 else a.shape[0]
    start = int(rule[-1]) + 1 if len(rule) and rule[-1] < a.shape[0] // 2 else 0
    sub = lit[start:end]
    r, c = np.flatnonzero(sub.any(axis=1)), np.flatnonzero(sub.any(axis=0))
    if not len(r) or not len(c):
        return 0, a.shape[0], 0, a.shape[1]
    return start + max(0, r[0] - 1), start + min(sub.shape[0], r[-1] + 2), max(0, c[0] - 1), min(a.shape[1], c[-1] + 2)


def trim(img, min_frac=0.25):
    """A glyph's strokes cropped to themselves (`trim_box`)."""
    r0, r1, c0, c1 = trim_box(img, min_frac)
    return np.asarray(img, float)[r0:r1, c0:c1]


def match(glyph, tpl, shift=SHIFT):
    """[(glyph, score)], best first: each template slid over the glyph by up to `shift` px either way, the best
    normalised correlation over the overlap of the glyph's padded box and the template. A template may be a list of
    looks of one glyph (`with_letters`): the best of them is its score."""
    g = np.asarray(glyph, float)
    out = []
    for d, Ts in tpl.items():
        best = -1.0
        for T in _looks(Ts):
            th, tw = T.shape
            H, W = max(th, g.shape[0]) + 2 * shift, max(tw, g.shape[1]) + 2 * shift
            G = np.zeros((H, W))
            gy, gx = (H - g.shape[0]) // 2, (W - g.shape[1]) // 2
            G[gy:gy + g.shape[0], gx:gx + g.shape[1]] = g
            cy, cx = (H - th) // 2, (W - tw) // 2
            for dy in range(-shift, shift + 1):
                for dx in range(-shift, shift + 1):
                    y, x = cy + dy, cx + dx
                    if 0 <= y and y + th <= H and 0 <= x and x + tw <= W:
                        best = max(best, _ncc(G[y:y + th, x:x + tw], T))
        out.append((d, best))
    return sorted(out, key=lambda x: -x[1])


def read(img, tpl, unit_width=None, among=None, last=None):
    """A box's strokes (one look of it) read glyph by glyph: (text, [(x0, x1, best glyph or None, score, margin)]).
    `tpl` is the clock's digits, or those and letters (`with_letters`). Each glyph is matched among `among` (default:
    all of them) and the last among `last` where given (an azimuth's side, L or R). The glyphs matched among set the
    width and the height (the digits, where `among` is not given and there are any), or `unit_width` (a word's pitch,
    `letter_templates`' `pitch`: a letter's template is trimmed to its strokes, wider than its step). A glyph wider than 1.6 times
    that is cut at the pitch into as many as it holds (glyphs drawn touching, `pitch_cut`); a slot far fainter than the
    others (FAINT) is no glyph."""
    pick = lambda keys: {k: v for k, v in (tpl or {}).items() if keys is None or k in keys}
    body = pick(among)
    tail = pick(last) if last is not None else body
    if not body:
        return "", []
    cells = ([T for d, Ts in body.items() if isinstance(d, int) for T in _looks(Ts)] if among is None else []) or \
        [T for Ts in body.values() for T in _looks(Ts)]
    tw = unit_width or int(np.median([T.shape[1] for T in cells]))
    img = np.asarray(img, float)
    sl = []
    for a, b in slots(img):
        if b - a > 1.6 * tw:                      # glyphs the blur joined: as many as the slot's width holds, at the pitch
            cut = pitch_cut(img[:, a:b], max(2, int(round((b - a) / tw))))
            sl += [(a + c0, a + c1) for c0, c1 in cut] or [(a, (a + b) // 2), ((a + b) // 2, b)]
        else:
            sl.append((a, b))
    if len(sl) > 1:
        peak = [float(img[:, a:b].max()) for a, b in sl]
        sl = [x for x, v in zip(sl, peak) if v >= FAINT * float(np.median(peak))]
    th = float(np.median([T.shape[0] for T in cells]))
    text, rows = "", []
    for i, (a, b) in enumerate(sl):
        g = trim(img[:, max(0, a - 1):b + 1])
        r = match(g, tail if i == len(sl) - 1 and tail else body)
        best, score = r[0]
        margin = score - (r[1][1] if len(r) > 1 else 0.0)
        if len(r) == 1:                            # one glyph to choose from: its score alone says whether it is that
            margin = MIN_MARGIN
        # a digit fills the text's height; a degree mark or a point does not, and is no digit however well it matches
        ok = score >= MIN_SCORE and margin >= MIN_MARGIN and g.shape[0] >= SHORT * th
        text += str(best) if ok else "?"
        rows.append((a, b, best if ok else None, float(score), float(margin)))
    return text, rows


def suggest(clip, box, stretches, tpl, polarity=None, most=15, among=None, last=None, unit_width=None):
    """For each look of a box ({letter: [(first, last), ...]}): what its glyphs suggest, from up to `most` frames of its
    first stretch's middle, each matched among `among` and the last among `last` (`read`). {letter: {"text", "glyphs"}}."""
    out = {}
    for L, spans in stretches.items():
        a, b = spans[0]
        lo, hi = a + (b - a) // 4, b - (b - a) // 4
        frames = list(range(lo, hi + 1, max(1, (hi - lo + 1) // most))) or [a]
        st, polarity = _strokes(clip, box, frames, polarity)
        text, rows = read(st.mean(axis=0), tpl, unit_width=unit_width, among=among, last=last)
        out[L] = dict(text=text, glyphs=rows)
    return out


def measure(clip, clock_box, at_frame, at_digit, step=1):
    """The templates from the clock: (a Found, {digit: template})."""
    tpl, info = templates(clip, clock_box, at_frame, at_digit, step)
    if not tpl:
        return Found("glyphs", no_power=[("glyphs", info.get("why", "no templates"))]), {}
    res = {"templates": f"{len(tpl)} of 10 digits from the clock's last digit at ({info['units_box'][0]},"
                        f"{info['units_box'][1]})-({info['units_box'][2]},{info['units_box'][3]}), its second "
                        f"{info['clock']['period_frames']:.2f} frames over {info['ticks']} ticks"}
    if info.get("most_alike"):
        res["most alike"] = (f"{info['most_alike']['digits'][0]} and {info['most_alike']['digits'][1]}, correlation "
                             f"{info['most_alike']['ncc']:.2f}")
    notes = []
    if len(tpl) < 10:
        notes.append(f"Digits {sorted(set(range(10)) - set(tpl))} have no template: the clip is too short for the clock "
                     "to show them, so they cannot be suggested.")
    fields = dict(info, digits=sorted(tpl))
    return Found("glyphs", res, fields, notes=notes), tpl
