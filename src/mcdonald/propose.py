"""Proposing the object: what moves against the background, with no marks to go on.

The package's founding claim is that no detector can say which thing in the frame
is the object, and someone looking can. This does not change it. It changes what
the person is asked: not "find it and click it", but "is it one of these?" --
a short list of the things that move against the background, each as a strip of
the clip's own pixels, best first. They pick one, or none and click as before.
A mark that comes from a proposal says so (`how = "proposed: ..."`), is never a
hand mark, and a report built on it says on its face that the detector proposed
the object and who accepted it.

How, and what each step is for:

1. **A double difference on the registered background.** Frame n is compared with
   n-k and n+k, each brought onto n's background by a global shift (phase
   correlation; kept only if it fits better than no shift, so a scene held still
   stays still). What is brighter than *both* neighbours, or darker than both, at
   the same place on the background is something that was there at n and not
   before or after: it moves against the background. An object the sensor is
   following is still on the screen while the background flows under it, and
   shows just the same (PR144). Static symbology cancels; the masks take the rest.
2. **Compact peaks** of that residual, a handful per frame and polarity.
3. **Chains at constant screen velocity**, three points or more, of steady size
   and amplitude; pieces of one thing are joined where the earlier was heading.
   Noise does not line up; a thing that moves does.
4. **Alone in its motion?** Several things going the same way at the same time in
   different places are a flow -- a second background layer, terrain under a pan
   the registration could not see, a heading tape that scrolls -- and are marked
   down for it. On PR113 that is what separates the four-frame transit from the
   scale sliding under it.
5. **A spot, or an edge or a stroke?** (`all_round`.) The residual cannot tell a
   compact thing from the edge of a redaction block that shifts, the rim of the
   picture, or a stroke of a symbol that scrolls: each is a compact peak that
   moves. The frame can. A compact thing has background on every side of it, and
   those have more of the same on one side, or two. On PR113 the ten proposals
   above the object were all of that kind, and it took one picture of their
   strips to see it.
6. **The thing itself, not what changed** (`thing_at`, `_own_centres`). The
   residual says where something changed, and for a thing that moves less than
   its own width in 2k frames that is its rim. A proposal's positions and width
   are the thing's own -- a small scale space in the frame, about each peak --
   wherever those make a steadier track than the peaks do; points where the
   thing has faded are left out; and a piece is joined to another only if it is
   like it, and lends it frames only if it runs on it and not beside it. All of
   this is for the marks: they have to be marks the package's linker can use,
   within its 6 px of a spot its own detector finds. On PR055 they were on the
   disc's rim, 11 px out, with a last one in a dark gap the disc had gone into;
   on PR142 the first were on a faint copy the object drags 20 px behind it.
   Each linked nothing. `tools/find_rank.py --link` is the check.
7. **A score**, from evidence (points beyond the two that define a velocity), how
   far the peaks stand out in their frames, motion against the background, the
   length and straightness of the path, that company, and how much of the way
   round it the background is seen. It orders a list for a person. It is not a
   probability and nothing downstream reads it.

What it is for, measured 2026-09-21 against every clip that has a recorded track
(the place of the recorded object on the list; before step 5, and with it):

    PR149 1-120     a contact crossing at 20 px/frame, a ship in frame     1 of 197 -> 1   strong
    PR144 300-500   the sensor follows the object; the background moves    1 of 509 -> 1   strong
    PR142 130-290   a small bright thing at 19 px/frame                    1 of 125 -> 1   strong
    PR148 140-440   a dark thing at 7 px/frame, then 3                     1 of 608 -> 1   strong
    PR113 380-440   a four-frame transit of a dark blob, past a scrolling  6 of 135 -> 1   weak
    PR113 348-471     heading tape, under a pan the registration cannot   11 of 294 -> 1   weak
    PR113 108-708     see (the last range was not looked at beforehand)         --  -> 1   weak
    PR055 90-350    a black disc 72 px across at 4.5 px/frame              not on the list, either way

So: where the object is the main compact thing moving against the background it
comes first, by a wide margin (the second row scores a fiftieth of it). On PR113
it comes first by a narrow one, and every row says weak: four frames are little
evidence, and the list says so. PR055 is the limit of step 1, not of the order:
a thing that moves less than its own size in 2k frames is at no place only at n,
so the double difference cancels it. More than one k would see it. Where the
object is missing the person's click is what it always was.

The positions are centroids of a smoothed residual, good to a few pixels. They are
for seeding `autolink.link_from_marks`, which chooses the detector from them and
measures the track with the package's own detector. Nothing published is read
off a proposal.

About 0.2 s a 1080p frame on ten processes, plus the static masks once.
"""
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from . import forensics as vf

K = 2                       # frames either side for the double difference
PER_FRAME = 10              # peaks kept per frame and polarity
SECTORS = 16                # of the ring round a peak, for `all_round`
LADDER = (2.0, 3.0, 4.5, 6.5, 9.5, 14.0, 20.0, 28.0)      # sigma, px: things 7 to 100 px across, for `thing_at`
VMAX = 220.0                # px/frame: nothing in the corpus is faster on screen (PR113 is 142)
_G = {}


@dataclass
class Proposal:
    """One thing that moves against the background."""
    track: dict                                 # {frame: (x, y)}, where its residual peaked
    dark: bool
    size_px: float                              # rough: the width of the residual blob
    velocity: tuple                             # px/frame on the screen
    against_background: float                   # px/frame relative to the background's own motion
    stands_out: float                           # its peaks over the typical peak of their frames
    path_px: float
    resid_px: float
    company: int                                # other things going the same way at the same time
    score: float = 0.0
    parts: int = 1
    all_round: float = 1.0                      # how much of the way round it the background is seen: a spot, or an edge or a stroke
    why: str = field(default="", compare=False)
    frame_size: tuple = None                    # (W, H), to keep the seeds off the frame's edge

    @property
    def frames(self):
        return sorted(self.track)

    def seeds(self, most=10, apart=8):
        """The frames to mark, for the link to start from: the ends of what was seen, and
        enough between them that no stretch between two marks is long. Every mark is a seed
        and the link runs both ways between each pair, so a short stretch is one it cannot
        wander off in: on PR149, linked from two marks 51 frames apart, it left the contact
        where that crosses the ship and came back with 16 px/frame for the published 20.
        From six marks 13 of the 34 frames it shares with the hand track were off it; from
        ten, one; from sixteen, none -- but each mark on a frame where the package's own
        detector cannot see the thing is a concern for the person to read, and sixteen made
        seventeen of those. Ten. Each is a place the thing was actually seen."""
        ns = self.frames
        if self.frame_size:                                 # the detector closes a border of 1.5 sizes: a mark there has no link under it
            W, H = self.frame_size
            inside = [n for n in ns if 70 <= self.track[n][0] <= W - 70 and 70 <= self.track[n][1] <= H - 70]
            ns = inside if len(inside) >= 2 else ns
        want = int(min(most, max(2, 1 + (ns[-1] - ns[0]) // apart), len(ns)))
        pick = sorted({ns[int(round(i))] for i in np.linspace(0, len(ns) - 1, want)})
        return {n: self.track[n] for n in pick}

    def strength(self):
        return "strong" if self.score >= 10 else "fair" if self.score >= 4 else "weak"

    def describe(self):
        ns = self.frames
        speed = float(np.hypot(*self.velocity))
        L = [f"{'dark' if self.dark else 'bright'}, about {self.size_px:.0f} pixels wide",
             f"frames {ns[0]}–{ns[-1]} (seen in {len(ns)})",
             f"moves {self.against_background:.0f} pixels each frame against the background"
             + (f", {speed:.0f} on the screen" if abs(speed - self.against_background) > 2 else ""),
             "a spot with background all round it" if self.all_round >= 0.3 else "more like an edge or a line than a spot",
             "nothing else moves the same way" if not self.company else
             f"{self.company} other thing{'s' if self.company != 1 else ''} move{'s' if self.company == 1 else ''} the same way: it may be "
             "part of the background, ground under a turning camera, or numbers that slide across the screen"]
        return "; ".join(L)

    def to_dict(self):
        s = self.seeds()
        return dict(frames=[self.frames[0], self.frames[-1]], seen_in=len(self.track), dark=self.dark, size_px=round(self.size_px, 1),
                    velocity_px_per_frame=[round(v, 2) for v in self.velocity],
                    against_background_px_per_frame=round(self.against_background, 2), stands_out=round(self.stands_out, 2),
                    path_px=round(self.path_px, 1), resid_px=round(self.resid_px, 2), going_the_same_way=self.company,
                    background_all_round=round(self.all_round, 2),
                    score=round(self.score, 2), strength=self.strength(), says=self.describe(),
                    mark_at={str(n): [round(x, 1), round(y, 1)] for n, (x, y) in s.items()},
                    track={str(n): [round(x, 1), round(y, 1)] for n, (x, y) in sorted(self.track.items())})


# ---- 1, 2: the residual of one frame, and its peaks -----------------------------------
def background_shift(ga, gb, ok, down=4):
    """(dx, dy): where the content of a is found in b, as one global translation, by phase
    correlation at 1/down of the resolution, to a fraction of that pixel."""
    a, b = ga[::down, ::down].copy(), gb[::down, ::down].copy()
    m = ok[::down, ::down]
    for im in (a, b):
        im -= ndimage.gaussian_filter(im, 6)
        im[~m] = 0
    w = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    R = np.fft.rfft2(a * w).conj() * np.fft.rfft2(b * w)
    R /= np.abs(R) + 1e-6
    c = ndimage.gaussian_filter(np.fft.irfft2(R, a.shape), 0.8, mode="wrap")
    py, px = np.unravel_index(np.argmax(c), c.shape)
    H, W = c.shape

    def sub(m1, m0, p1):
        d = m1 - 2 * m0 + p1
        return 0.0 if d >= 0 else float(np.clip(0.5 * (m1 - p1) / d, -0.5, 0.5))
    dy = (py if py <= H // 2 else py - H) + sub(c[(py - 1) % H, px], c[py, px], c[(py + 1) % H, px])
    dx = (px if px <= W // 2 else px - W) + sub(c[py, (px - 1) % W], c[py, px], c[py, (px + 1) % W])
    return dx * down, dy * down


def onto(g0, g, ok):
    """g brought onto g0's background, and the shift used: the estimate, unless leaving g
    where it is fits as well -- a scene held still, or too little texture to say."""
    dx, dy = background_shift(g0, g, ok)
    moved = ndimage.shift(g, (-dy, -dx), order=1, mode="nearest")
    sl = (slice(None, None, 4), slice(None, None, 4))
    if np.median(np.abs(g0[sl] - moved[sl])[ok[sl]]) < 0.97 * np.median(np.abs(g0[sl] - g[sl])[ok[sl]]):
        return moved, (dx, dy)
    return g, (0.0, 0.0)


def peaks(img, bad, n_max=PER_FRAME, sigma=2.0, floor=4.0):
    """[(x, y, amplitude, width)] of the compact maxima of a residual."""
    s = ndimage.gaussian_filter(np.clip(img, 0, None), sigma)
    s[bad] = 0
    v = s[~bad]
    noise = max(1.4826 * float(np.median(np.abs(v - np.median(v)))), 0.5)
    out = []
    for _ in range(n_max):
        py, px = np.unravel_index(np.argmax(s), s.shape)
        a = float(s[py, px])
        if a < 6 * noise or a < floor:
            break
        y0, x0 = max(py - 12, 0), max(px - 12, 0)
        win = s[y0:py + 13, x0:px + 13]
        lab, _ = ndimage.label(win >= 0.5 * a)
        blob = lab == lab[py - y0, px - x0]
        ys, xs = np.nonzero(blob)
        w = win[blob]
        out.append((x0 + float((xs * w).sum() / w.sum()), y0 + float((ys * w).sum() / w.sum()), a, float(np.sqrt(blob.sum()))))
        s[max(py - 20, 0):py + 21, max(px - 20, 0):px + 21] = 0
    return out


def all_round(g, x, y, pol, width):
    """How much of the way round a peak the background is seen, 0 to 1, in the frame's own
    pixels and not the residual's. A compact thing has background on every side of it. The
    edge of a redaction block, the rim of the picture and a stroke of a moving symbol do
    not: on one side, or two, there is more of the same. The residual cannot tell them
    apart -- each is a compact peak that moves -- and on PR113 those were ten of the eleven
    best proposals, with the object the eleventh (it took one picture of strips to see it).

    The core, a disc of the peak's own half-width, is compared with the sixteen sectors of
    a ring round it: what comes back is the worst sector's contrast as a share of the best.
    The residual's centroid is good to a few pixels, so the core is first moved onto the
    nearest extremum of the smoothed frame.

    Sixteen, measured on the six clips that have a recorded track: with eight a thin stroke
    fills too little of the two sectors it runs through to be noticed (0.58 for a 5 px bar),
    with twenty-four the sectors are small enough for noise to pull a real object down
    (PR149's contact 0.38, from 0.69). At sixteen the recorded objects are 0.31 to 0.83 and
    the median of the clutter is 0.00 on every clip but PR144 (0.10) and PR142 (0.16)."""
    r = max(0.5 * width, 3.0)
    reach = int(round(max(2.0, 0.5 * r)))
    R = int(np.ceil(2.8 * r)) + reach + 1
    H, W = g.shape
    xi, yi = int(round(x)), int(round(y))
    win = g[np.ix_(np.clip(np.arange(yi - R, yi + R + 1), 0, H - 1), np.clip(np.arange(xi - R, xi + R + 1), 0, W - 1))]
    near = (pol * ndimage.gaussian_filter(win, max(0.5 * r, 1.0)))[R - reach:R + reach + 1, R - reach:R + reach + 1]
    cy, cx = np.unravel_index(np.argmax(near), near.shape)
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1]
    yy, xx = yy - (cy - reach), xx - (cx - reach)
    rr = np.hypot(xx, yy)
    core = float(win[rr <= 0.8 * r].mean())
    ring = (rr > 1.8 * r) & (rr <= 2.8 * r)
    sector = np.floor((np.arctan2(yy, xx) + np.pi) / (2 * np.pi) * SECTORS).astype(int) % SECTORS
    contrast = np.array([pol * (core - float(win[ring & (sector == s)].mean())) for s in range(SECTORS)])
    return float(np.clip(contrast.min() / contrast.max(), 0.0, 1.0)) if contrast.max() > 0 else 0.0


def thing_at(g, x, y, pol):
    """(x, y, size, response): the compact thing in the frame that a residual peak belongs to --
    its own centre and its own width, from a small scale space (a difference of Gaussians at
    each of LADDER, the strongest within reach of the peak).

    The residual says where something *changed*, and for a thing that moves less than its
    own width in 2k frames that is its rim: on PR055, a black disc 24 px across at 1.5 px a
    frame, the peaks ride the leading and trailing edges, 11 px from the recorded centre and
    "about 5 pixels wide". Jacob took that proposal (2026-09-21: "Find the object worked, but
    linking did not"); the marks went on the rim, the package's detector found the disc at
    its centre 10 px away, no spot size came within the link's 6 px of the marks, and
    nothing was linked. From here the centres are 0.9 px from the recorded track.

    A coarse scale is looked for in a coarse picture, which keeps this near 10 ms a peak."""
    H, W = g.shape
    xi, yi = int(round(x)), int(round(y))
    best = None
    for s in LADDER:
        f = 1 if s < 6 else 2 if s < 13 else 4
        reach = 1.5 * s + 3.0                                 # a rim is one radius, about 1.4 s, from the centre
        half = int(np.ceil((reach + 5.0 * s) / f)) * f
        win = g[np.ix_(np.clip(np.arange(yi - half, yi + half + 1, f), 0, H - 1), np.clip(np.arange(xi - half, xi + half + 1, f), 0, W - 1))]
        dog = pol * (ndimage.gaussian_filter(win, s / f) - ndimage.gaussian_filter(win, 1.6 * s / f))
        c = half // f
        yy, xx = np.mgrid[-c:c + 1, -c:c + 1] * f
        dog = np.where(np.hypot(xx, yy) <= reach, dog, -np.inf)
        j = np.unravel_index(np.argmax(dog), dog.shape)
        if best is None or dog[j] > best[0]:
            best = (float(dog[j]), s, xi + float(xx[j]), yi + float(yy[j]))
    v, s, cx, cy = best
    return cx, cy, 3.7 * s, v                             # drawn discs 6 to 72 px across win at a sigma of their width / 3.4 to 4.0


def _init(clip, bad, k):
    _G.update(clip=clip, bad=bad, k=k)


def _frame(n):
    """(n, peaks, the background's px/frame). A peak is (x, y, amplitude, width, polarity, background all
    round) of the residual, and then (x, y, width, background all round, response) of the thing in the frame
    it belongs to."""
    clip, bad, k = _G["clip"], _G["bad"], _G["k"]
    g0 = clip.grey(n)
    (ga, sa), (gb, sb) = onto(g0, clip.grey(n - k), ~bad), onto(g0, clip.grey(n + k), ~bad)
    found = [(*p, +1) for p in peaks(g0 - np.maximum(ga, gb), bad)] + [(*p, -1) for p in peaks(np.minimum(ga, gb) - g0, bad)]
    found = [(*p, all_round(g0, p[0], p[1], p[4], p[3])) for p in found]
    H, W = bad.shape
    things = [thing_at(g0, p[0], p[1], p[4]) for p in found]
    # A "thing" whose centre is in a redaction block, in symbology or at the frame's edge is no thing in the scene: the
    # scale space has walked off the peak onto the block beside it. Size 0 says so, and `_own_centres` leaves it out.
    # (PR055: the disc goes behind a block at frame 1299; the chain's last point became the block, the last mark went
    # there, and the link -- which chooses its detector at the first and last marks -- linked nothing.)
    things = [t if not bad[int(np.clip(round(t[1]), 0, H - 1)), int(np.clip(round(t[0]), 0, W - 1))] else (p[0], p[1], 0.0, 0.0)
              for p, t in zip(found, things)]
    found = [(*p, t[0], t[1], t[2], all_round(g0, t[0], t[1], p[4], t[2]) if t[2] else 0.0, t[3]) for p, t in zip(found, things)]
    return n, found, ((sb[0] - sa[0]) / (2 * k), (sb[1] - sa[1]) / (2 * k))


def _frame_peaks(clip, masks, n, k=K):
    """One frame's peaks, in this process: for a test, or for looking at what the residual saw."""
    _init(clip, not_scene(clip, masks), k)
    return _frame(n)[1]


def not_scene(clip, masks, border=30):
    """Where a residual is not to be believed: the static masks, grown, and the frame's edge."""
    bad = ndimage.binary_dilation(masks["blocks"] | masks["graphics"], iterations=6)
    bad[:border, :] = bad[-border:, :] = True
    bad[:, :border] = bad[:, -border:] = True
    return bad


# ---- 3: chains ---------------------------------------------------------------------------
def off_path(dx, dy, v, steps=1.0, tol=6.0, slack=0.0):
    """How far a point is from where a thing moving at v should be, as a share of what is
    allowed: > 1 is off its path. Generous along the track and tight across it. A fast
    object's steps are uneven along its track -- repeated frames and catch-up steps; PR113's
    are 92, 111 and 104 px -- but it does not leave its line, and on PR113 that is what
    tells the transit from a stray peak 60 px to one side of where it was going. `slack` is
    for a velocity that is itself uncertain: one taken from two peaks a frame apart, each
    good to a few pixels, points a fast thing's next step several pixels to one side."""
    tol = tol + slack
    speed = np.hypot(*v)
    if speed < 1e-6:
        return np.hypot(dx, dy) / tol
    ux, uy = v[0] / speed, v[1] / speed
    along, across = dx * ux + dy * uy, -dx * uy + dy * ux
    return np.maximum(np.abs(along) / (tol + 0.15 * speed * steps), np.abs(across) / (tol + 0.03 * speed * steps))


def chains(found, vmax=VMAX, tol=6.0, max_skip=2):
    """[(frames, peaks)]: same-polarity peaks at constant screen velocity, three or more,
    of steady size and amplitude unless there are six. The gate about the prediction widens
    with speed: PR113's object steps 92, 111 and 104 px in its three intervals."""
    ns = sorted(found)
    at = {n: i for i, n in enumerate(ns)}
    arr = {n: np.array([(p[0], p[1], p[4]) for p in found[n]], float).reshape(-1, 3) for n in ns}
    out = []
    for i, n in enumerate(ns):
        for m in ns[i + 1:i + 2 + max_skip]:
            A, B, dt = arr[n], arr[m], m - n
            if not len(A) or not len(B):
                continue
            d = np.hypot(B[None, :, 0] - A[:, None, 0], B[None, :, 1] - A[:, None, 1])
            for ai, bi in zip(*np.nonzero((d <= vmax * dt) & (A[:, None, 2] == B[None, :, 2]))):
                a, b = found[n][ai], found[m][bi]
                v = ((b[0] - a[0]) / dt, (b[1] - a[1]) / dt)
                fr, pts, last_n, last, miss = [n, m], [a, b], m, b, 0
                for q in ns[at[m] + 1:]:
                    C = arr[q]
                    if len(C):
                        px, py = last[0] + v[0] * (q - last_n), last[1] + v[1] * (q - last_n)
                        slack = 8.0 * (q - last_n) / (last_n - n)           # the velocity is as good as its baseline is long
                        dd = np.where(C[:, 2] == a[4], off_path(C[:, 0] - px, C[:, 1] - py, v, q - last_n, tol, slack), np.inf)
                        j = int(np.argmin(dd))
                        if dd[j] <= 1.0:
                            c = found[q][j]
                            fr.append(q)
                            pts.append(c)
                            v = ((c[0] - a[0]) / (q - n), (c[1] - a[1]) / (q - n))      # refit from the ends
                            last_n, last, miss = q, c, 0
                            continue
                    miss += 1
                    if miss > max_skip:
                        break
                if len(fr) >= 3:
                    amp, size = np.array([p[2] for p in pts]), np.array([p[3] for p in pts])
                    if len(fr) >= 6 or (amp.max() <= 2.0 * amp.min() and size.max() <= 1.6 * size.min()):
                        out.append((fr, pts))
    return out


def _velocity(fr, pts):
    t = np.array(fr, float)
    return float(np.polyfit(t, [p[0] for p in pts], 1)[0]), float(np.polyfit(t, [p[1] for p in pts], 1)[0])


def things(raw):
    """The chains as things: the longest first, a chain most of whose points are already in
    a longer one dropped, and the pieces of one thing joined -- the later piece starts
    where the earlier was heading, at much the same velocity."""
    raw = sorted(raw, key=lambda c: -len(c[0]))
    kept, taken = [], set()
    for fr, pts in raw:
        key = {(n, round(p[0]), round(p[1])) for n, p in zip(fr, pts)}
        if len(key & taken) <= 0.5 * len(key):
            kept.append([list(fr), list(pts)])
            taken |= key
    kept.sort(key=lambda c: c[0][0])
    joined = []
    for fr, pts in kept:
        v = _velocity(fr, pts)
        for J in joined:
            gap, vj = fr[0] - J[0][-1], J[2]
            if 0 < gap <= 30 and J[1][-1][4] == pts[0][4]:
                pred = (J[1][-1][0] + vj[0] * gap, J[1][-1][1] + vj[1] * gap)
                if (off_path(pts[0][0] - pred[0], pts[0][1] - pred[1], vj, gap, 10.0) <= 1.0
                        and np.hypot(v[0] - vj[0], v[1] - vj[1]) <= max(2.5, 0.3 * np.hypot(*vj))):
                    J[0] += fr
                    J[1] += pts
                    J[2] = v
                    J[3] += 1
                    break
        else:
            joined.append([fr, pts, v, 1])
    return joined


# ---- 4, 5: what each is like, and the order ------------------------------------------------
def _on_the_path(fr, pts):
    """The points of a chain that lie on its own path. A chain of a fast thing is gated
    loosely, and picks up a stray peak or two past its end; a mark seeded from one of those
    would start the link somewhere the thing never was. A short chain is a straight line at
    constant velocity through two of its own points -- whichever two the most others agree
    with; a long one may curve, and loses only what stands well off a smooth fit."""
    fr, pts = list(fr), list(pts)
    t = np.array(fr, float)
    P = np.array([(p[0], p[1]) for p in pts], float)
    if 3 < len(fr) <= 12:
        best = None
        for i in range(len(fr)):
            for j in range(i + 1, len(fr)):
                v = (P[j] - P[i]) / (t[j] - t[i])
                d = P - (P[i] + np.outer(t - t[i], v))
                r = off_path(d[:, 0], d[:, 1], v)
                on = r <= 1.0
                key = (int(on.sum()), -float(r[on].sum()))
                if best is None or key > best[0]:
                    best = (key, on)
        if best[0][0] >= 3:
            keep = np.nonzero(best[1])[0]
            return [fr[i] for i in keep], [pts[i] for i in keep]
        return fr, pts
    for _ in range(3):
        if len(fr) <= 12:
            break
        t = np.array(fr, float)
        X, Y = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
        r = np.hypot(X - np.polyval(np.polyfit(t, X, 2), t), Y - np.polyval(np.polyfit(t, Y, 2), t))
        worst = int(np.argmax(r))
        if r[worst] <= max(8.0, 3.0 * float(np.sqrt((np.delete(r, worst) ** 2).mean()))):
            break
        del fr[worst], pts[worst]
    return fr, pts


def _own_centres(fr, pts, deg):
    """The chain's points as the centres of the thing itself (`thing_at`), if that is a
    better account of it than the residual's peaks: the thing is one size along the chain,
    and its centres lie on a path at least as smooth. Then (frames, [(x, y)], size, how
    much background is all round it); else None, and the residual's peaks stand. A small
    fast object is the same either way. A slow large one is a rim in the residual, wandering
    from the leading edge to the trailing one, and a steady centre in the frame. What is
    *not* one thing -- a peak on a cloud edge, whose nearest blob is a different one each
    frame -- fails both tests and stays as it was.

    A point where the thing has faded to nothing is left out. PR055's disc drifts into a
    dark gap between clouds at about frame 1300 and cannot be seen in it; the chain ran on
    six frames into the gap, the "thing" there was the gap, the last mark went on it, and
    the link -- which chooses its detector at the first and last marks -- linked nothing."""
    if len(pts[0]) < 11:
        return None
    t = np.array(fr, float)
    raw, own = np.array([(p[0], p[1]) for p in pts], float), np.array([(p[6], p[7]) for p in pts], float)
    size = np.array([p[8] for p in pts], float)
    med = float(np.median(size))
    same = (size >= med / 1.6) & (size <= med * 1.6)
    seen = np.array([p[10] for p in pts], float)
    if same.any():
        same &= seen >= 0.3 * float(np.median(seen[same]))

    def off(P, keep):
        """How far each point is from the line through its neighbours on either side, among
        the points kept. Local on purpose: PR142's object crosses 1800 px in a hundred
        frames under a camera that is not still, and no one parabola is within 6 px of all
        of that -- measured against one, whole stretches of a good track were thrown out."""
        k = np.nonzero(keep)[0]
        r = np.zeros(len(t))
        for i in range(len(t)):
            a, b = k[k < i], k[k > i]
            if len(a) and len(b):
                a, b = a[-1], b[0]
                r[i] = np.hypot(*(P[i] - (P[a] + (P[b] - P[a]) * (t[i] - t[a]) / (t[b] - t[a]))))
            else:                                                 # an end: carried on from the two nearest
                q = (k[k > i][:2] if len(b) >= 2 else k[k < i][-2:]) if (len(a) >= 2 or len(b) >= 2) else []
                if len(q) == 2:
                    r[i] = np.hypot(*(P[i] - (P[q[0]] + (P[q[1]] - P[q[0]]) * (t[i] - t[q[0]]) / (t[q[1]] - t[q[0]]))))
        return r
    if same.sum() < 3 or same.mean() < 0.7:
        return None
    r_own, r_raw = off(own, same), off(raw, np.ones(len(t), bool))
    if float(np.median(r_own[same])) > float(np.median(r_raw)) + 1.5:
        return None
    # What stands off the line of its neighbours goes, the worst first and one at a time -- a stray point drags its
    # neighbours' lines toward itself, so taken all at once they would go with it. The scale is a median's, which
    # a stray point cannot widen for itself. (PR142, frame 172: the chain took the object's faint copy, 19 px back.)
    keep = same.copy()
    for _ in range(max(1, len(t) // 4)):
        r = off(own, keep)
        worst = int(np.argmax(np.where(keep, r, -1.0)))
        if r[worst] <= max(6.0, 4.5 * float(np.median(r[keep]))) or keep.sum() <= 3:
            break
        keep[worst] = False
    if keep.sum() < 3:
        return None
    k = np.nonzero(keep)[0]
    return [fr[i] for i in k], [tuple(own[i]) for i in k], med, float(np.median([pts[i][9] for i in k])), [pts[i] for i in k]


def describe(joined, found, vbg):
    out = []
    for fr, pts, _, parts in joined:
        fr, pts = _on_the_path(fr, pts)
        deg = 1 if len(fr) < 8 else 2                       # a long track may curve; a short one is a line
        own = _own_centres(fr, pts, deg)
        if own:
            fr, xy, size, around, pts = own
        else:
            xy, size = [(p[0], p[1]) for p in pts], float(np.median([p[3] for p in pts]))
            around = float(np.median([p[5] for p in pts])) if len(pts[0]) > 5 else 1.0
        t = np.array(fr, float)
        X, Y = np.array([c[0] for c in xy]), np.array([c[1] for c in xy])
        d = max(1, min(deg, len(fr) - 2))
        rx, ry = X - np.polyval(np.polyfit(t, X, d), t), Y - np.polyval(np.polyfit(t, Y, d), t)
        v = (float(np.polyfit(t, X, 1)[0]), float(np.polyfit(t, Y, 1)[0]))
        rel = np.array([(v[0] - vbg[n][0], v[1] - vbg[n][1]) for n in fr])
        typical = lambda n, pol: max(float(np.median([q[2] for q in found[n] if q[4] == pol])), 1.0)
        out.append(Proposal(track={n: (float(c[0]), float(c[1])) for n, c in zip(fr, xy)}, dark=pts[0][4] < 0,
                            size_px=size, velocity=v,
                            against_background=float(np.median(np.hypot(rel[:, 0], rel[:, 1]))),
                            stands_out=min(float(np.median([p[2] / typical(n, p[4]) for n, p in zip(fr, pts)])), 5.0),
                            path_px=float(np.hypot(X[-1] - X[0], Y[-1] - Y[0])),
                            resid_px=float(np.sqrt((rx ** 2 + ry ** 2).mean())), company=0, parts=parts, all_round=around))
    return out


def _at(p, n):
    """Where a proposal is at frame n: between the frames it was seen in, along the line
    between them; before or after them, carried on at its velocity."""
    ns = p.frames
    if n <= ns[0] or n >= ns[-1]:
        e = ns[0] if n <= ns[0] else ns[-1]
        return p.track[e][0] + p.velocity[0] * (n - e), p.track[e][1] + p.velocity[1] * (n - e)
    return (float(np.interp(n, ns, [p.track[m][0] for m in ns])), float(np.interp(n, ns, [p.track[m][1] for m in ns])))


def score(props):
    """Count each thing's company, score it, and order the list."""
    for c in props:
        sc, (a, b) = float(np.hypot(*c.velocity)), (c.frames[0], c.frames[-1])
        c.company = 0
        for o in props:
            so = float(np.hypot(*o.velocity))
            if o is c or min(sc, so) < 1.0 or len(o.track) < 4 or o.frames[0] > b or o.frames[-1] < a:
                continue
            n = max(a, o.frames[0])
            cosang = (c.velocity[0] * o.velocity[0] + c.velocity[1] * o.velocity[1]) / (sc * so)
            far = np.hypot(_at(c, n)[0] - _at(o, n)[0], _at(c, n)[1] - _at(o, n)[1]) > 60
            if cosang > np.cos(np.radians(25)) and 0.5 <= sc / so <= 2.0 and far:
                c.company += 1                              # going the same way at the same time, somewhere else: a flow
        c.score = float(min(len(c.track) - 2, 12) * c.stands_out * min(c.against_background / 3.0, 1.0) * min(c.path_px / 60.0, 1.0)
                        / (1.0 + c.resid_px / (3.0 + 0.05 * sc)) / (1.0 + c.company) * (0.1 + c.all_round))
    return sorted(props, key=lambda c: -c.score)


def _apart(c, b, shared):
    """How far piece c runs from row b, px, on the frames they share. On the frames both have
    a point on, where there are two or more, it is the distance between the two points: that
    is what tells the faint copy PR142's object drags a frame behind it (20 px back, on every
    frame) from the object. Where they interleave -- two chains that took turns at the same
    object's peaks -- it is the distance from c's point to the *line* between b's points on
    either side of it in time, not to a position interpolated by time: a clip with repeated
    frames (PR149) moves nothing on one frame and two steps on the next, and interpolation
    put the same object 15-19 px "from" itself and left it in three rows."""
    both = [n for n in shared if n in b.track]
    if len(both) >= 2:
        return float(np.median([np.hypot(c.track[n][0] - b.track[n][0], c.track[n][1] - b.track[n][1]) for n in both]))
    ns, d = b.frames, []
    for n in shared:
        i = int(np.searchsorted(ns, n))
        lo, hi = ns[max(i - 1, 0)], ns[min(i, len(ns) - 1)]
        P, A, B = np.array(c.track[n]), np.array(b.track[lo]), np.array(b.track[hi])
        seg = B - A
        t = float(np.clip(np.dot(P - A, seg) / np.dot(seg, seg), 0.0, 1.0)) if np.dot(seg, seg) > 0 else 0.0
        d.append(float(np.hypot(*(P - (A + t * seg)))))
    return float(np.median(d))


def distinct(props, near=30.0):
    """One row for one thing. A lower-scored proposal that runs beside a better one for the
    frames they share -- a piece of it that did not join, or the dark undershoot trailing a
    bright object -- is folded into it, and lends it the frames it alone saw.

    Again, until nothing more folds: a row that has just been lent a piece's frames may now
    run over a row it had nothing to do with a moment before. On PR144 the object came in
    three pieces, last, first and middle by score; the first was not where the last was
    heading sixty frames on, and became a row; the middle joined the last -- which then
    shared twenty-four frames with the first, to the pixel, and one pass left them two rows."""
    rows = _fold(props, near)
    while True:
        again = _fold(rows, near)
        if len(again) == len(rows):
            return again
        rows = again


def _fold(props, near):
    out = []
    for c in props:
        for b in out:
            shared = [n for n in c.frames if b.frames[0] <= n <= b.frames[-1]]
            gap = max(c.frames[0] - b.frames[-1], b.frames[0] - c.frames[-1])
            # Alike: the same polarity and much the same width (within two steps of `thing_at`'s ladder: at x1.6 PR144's
            # object, 8 px and found at 7, 11 and 17, stayed two rows). Only what is alike lends its frames, and only what is
            # alike is taken for a later piece of the same thing. PR055's disc, 24 px, heads into a dark gap between
            # clouds; twenty frames on, "where it was heading", the residual finds the gap itself, 104 px and standing
            # still. Folded in, its six frames put the proposal's last mark where there was nothing to see.
            alike = c.dark == b.dark and b.size_px / 2.5 <= c.size_px <= b.size_px * 2.5     # widths come off a ladder of x1.45 steps
            if shared:
                # Beside it is not on it. What runs within `near` of a better thing is folded into its row, but only
                # what runs *on* it may lend it frames: PR142's object drags a fainter copy of itself a frame behind,
                # 20 px back along the track, and its frames put the proposal's first marks on the copy.
                apart = _apart(c, b, shared)
                same, alike = apart <= near, alike and apart <= 8.0
            else:                                          # one after the other: is the later where the earlier was heading?
                n = c.frames[0] if c.frames[0] > b.frames[-1] else c.frames[-1]
                same = (alike and gap <= 60 and off_path(c.track[n][0] - _at(b, n)[0], c.track[n][1] - _at(b, n)[1], b.velocity, gap, near) <= 1.0
                        and np.hypot(c.velocity[0] - b.velocity[0], c.velocity[1] - b.velocity[1]) <= max(4.0, 0.4 * np.hypot(*b.velocity)))
            if same:
                if alike:
                    for n in c.frames:
                        b.track.setdefault(n, c.track[n])
                    b.parts += c.parts
                break
        else:
            out.append(c)
    return out


# ---- the whole search ------------------------------------------------------------------------
def search(clip, masks=None, n_lo=None, n_hi=None, k=K, procs=10, block=90, progress=None, stop=None, keep=12):
    """Yields (frames done, frames in all, [Proposal], best first) as it goes, a block of
    frames at a time, so that a caller can show what has been found so far and stop when the
    object is on the list. `progress` and `stop` are mcdonald.progress's."""
    n_lo, n_hi = max(n_lo or clip.n0, clip.n0) + k, min(n_hi or clip.n1, clip.n1) - k
    if n_hi - n_lo < 2:
        return
    if masks is None:
        masks = vf.static_masks(clip, progress=progress)
    bad = not_scene(clip, masks)
    frames = list(range(n_lo, n_hi + 1))
    found, vbg, raw, back = {}, {}, [], 40
    for i in range(0, len(frames), block):
        part = frames[i:i + block]
        what = f"looking for things that move against the background: frames {part[0]}–{part[-1]} of {n_lo}–{n_hi}"
        offset, total = i, len(frames)
        tell = None if progress is None else (lambda text, done=None, n=None: progress(what, offset + (done or 0), total))
        for n, pk, v in vf.pooled(procs, _frame, part, _init, (clip, bad, k), 2, tell, stop, what) if procs else _inline(clip, bad, k, part, tell, stop):
            found[n], vbg[n] = pk, v
        # Chains are made afresh only where they could have changed: from `back` frames before this
        # block on. One that began earlier is kept as it was; if it runs on into this block its
        # continuation is a chain of its own, and `things` and `distinct` make one thing of the two.
        since = part[0] - back
        raw = [c for c in raw if c[0][0] < since] + chains({n: pk for n, pk in found.items() if n >= since})
        props = distinct(score(describe(things(raw), found, vbg)))[:keep]
        for p in props:
            p.why, p.frame_size = p.describe(), (clip.W, clip.H)
        yield offset + len(part), total, props


def _inline(clip, bad, k, part, tell, stop):
    """The same, in this process: for a caller that cannot start a pool."""
    _init(clip, bad, k)
    for n in vf.counted(part, tell, stop):
        yield _frame(n)


def find(clip, masks=None, **kw):
    """The proposals for a clip, best first: `search`, run to its end."""
    props = []
    for _, _, props in search(clip, masks, **kw):
        pass
    return props


def shortlist(props, most=8):
    """The rows worth showing: the best three whatever they score, and any other within a
    quarter of the best. One strong thing and eleven weak ones is a list of one, not twelve."""
    if not props:
        return []
    return [p for i, p in enumerate(props[:most]) if i < 3 or p.score >= 0.25 * props[0].score]



# ---- showing one to a person -------------------------------------------------------------------
def strip(clip, proposal, tiles=6, box=96, zoom=2):
    """(H x W x 3 uint8, the frames shown): crops of the clip's own pixels along a proposal,
    each centred where it was seen and ringed, enlarged without interpolation. No toolkit:
    the window and `mcdonald look --propose` both show this, so a person and an agent are
    asked about the same picture."""
    ns = proposal.frames
    shown = sorted({ns[int(round(i))] for i in np.linspace(0, len(ns) - 1, min(tiles, len(ns)))})
    r = box // 2
    yy, xx = np.mgrid[-r:r, -r:r]
    ring = np.abs(np.hypot(xx + 0.5, yy + 0.5) - max(1.6 * proposal.size_px, 9.0)) < 0.6
    out = np.full((box * zoom, tiles * (box * zoom + 4) - 4, 3), 24, np.uint8)
    for j, n in enumerate(shown):
        x, y = proposal.track[n]
        g = np.pad(clip.rgb(n).astype(np.uint8), ((r, r), (r, r), (0, 0)), mode="edge")
        xi, yi = int(round(x)) + r, int(round(y)) + r
        tile = g[yi - r:yi + r, xi - r:xi + r].copy()
        tile[ring] = (53, 224, 200)
        out[:, j * (box * zoom + 4):j * (box * zoom + 4) + box * zoom] = np.repeat(np.repeat(tile, zoom, 0), zoom, 1)
    return out, shown


def accept_command(video, proposal, rank, of):
    """What an agent types to take a proposal: marks at its seeds, with the reason recorded.
    The marks are the agent's -- it looked at the strip and said yes -- and say so."""
    sets = " ".join(f"--set object@{n}={x:.1f},{y:.1f}" for n, (x, y) in sorted(proposal.seeds().items()))
    return (f"mcdonald mark {video} --no-window --link {sets} "
            f"--why \"proposal {rank} of {of} from look --propose ({proposal.describe()}); I looked at its strip and it is the object because ...\"")
