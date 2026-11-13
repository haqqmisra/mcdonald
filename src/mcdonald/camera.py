"""`mcdonald camera` — what the camera did while it watched: a zoom inside the track, the steps in the
object's rate, which of them fall on the camera's own events, and whether a track that was let go
explains the object's departure.

The object's motion in the picture is the object's motion less the camera's. Two things the camera does
change that motion without the object doing anything:

- **It zooms.** The picture's scale changes from one frame to the next, so a rate in pixels before and
  after is two different rates. On the Navy's 2004 FLIR1 the picture doubles between two frames: the
  object's length (7 -> 14 px) and its offset from the boresight double with it, and the zoom's centre,
  solved from that jump, is the boresight to 0.3 px. The `2.0` readout says so three frames later and the
  gate one frame later, so the readout cannot be used to time it. `zoom_steps` finds such a step from the
  object alone: its size steps by a ratio held on both sides, and where it is off the zoom's centre its
  position jumps by the same ratio about one point -- the centre.
- **It stops following.** A camera that tracked the object turned at the object's own bearing rate. When
  the tracker lets go, the object drifts across the picture at the rate the camera had been turning, and
  no faster: that is the null a departure has to beat (`released`). On FLIR1 the pod had been turning at
  0.247 +- 0.005 deg/s (its azimuth readout's ticks, `mcdonald readout`), and the object left the picture
  at 0.13, then 0.26 +- 0.01, then 0.15 deg/s. A published fit made that 75.9 g of the object's own, with
  the camera held still. Where no readout gives the camera's rate, the scene does (`--scene`, a `layers` CSV):
  while the camera held the object the ground drifted through the picture at the object's own rate against it,
  and once let go the object crosses the ground at that rate and no faster, the other way. The track is taken
  relative to the scene's path, so the camera's motion after the release is out of it too, and the scale
  cancels (both rates go through one k). On PR051's MTS-B (2026-10-28) the ground held still in the gate for
  three seconds, so the camera had not been turning against it at all, and the object's walk out of the gate
  at 0.006 deg/s against the ground is the object's, not the release's.

- **It changes its field of view.** A zoom readout is not the whole scale. A pod with several fields (the
  ATFLIR's NAR 0.7 deg, MFOV 3 and WFOV 6, each but WFOV with a x2) changes scale when it changes field, by
  4.3 between NAR x2 and MFOV x2. FLIR1 does that 0.2 s before its exit, and the readout says `2.0` across it.
  The object, 14 px long at NAR x2, is at this copy's blur at MFOV x2, so its size cannot show the change.
  The fields as the display gives them, stretch by stretch (`--fields`, `field_steps`), are taken out of the
  track as zooms are, and the object's size checks each change where it can.

So the rate steps of a track (`rate_steps`: straight lines between breakpoints, as few as the noise allows)
are each set beside the camera's events -- the zoom steps found here, and any the person gives
(`--events`, such as a readout's ticks or the frame a gate vanished). A step in the rate within a few frames
of a camera event is the camera's until shown otherwise. A published fit ended its acceleration exactly on
FLIR1's zoom frame.

What this cannot do: tell a camera that stopped from one that slowed, or a crew slewing by hand from a
tracker coasting; read the camera's turn off an empty sky; or say anything about the object's own motion
along the line of sight. The size of its image changes as the range does, but by far less than a pixel
over the second or so these steps take: a radial acceleration is not measurable here and is not given.
"""
import csv
import math
from pathlib import Path

import numpy as np
from scipy import ndimage

from . import kinematics as kin
from .report import Found

ZOOM_MIN = 1.35          # a step in the object's size of at least this ratio (or its inverse) is looked at as a zoom
HOLD = 4                 # frames either side over which a size step must hold, and a straight line be fitted
SPREAD_MAX = 0.15        # the scatter (MAD of log size) allowed on either side of a step
OUTLIER_MAX = 0.30       # and no frame of either side further than this from its side's median (log size): a zoom holds,
                         # where a blob that takes in a neighbour or a wing for a frame or two flips back (PR135, 2026-10-20)
JUMP_MIN = 2.0           # px: an offset jump smaller than this cannot say where the zoom's centre is
CENTRE_NEAR = 0.05       # a zoom's centre within this share of the frame's larger side of the frame's centre
MIN_SEG = 4              # frames: the shortest stretch a rate is fitted on
NOISE_FLOOR = 0.25       # px: a compressed video's centroids carry no less noise than this; a held object's slower
                         # wander is the tracker's (FLIR1's locked stretch: 0.115 px from second differences)
SCALE_ERR = 0.10         # the share of a rate an ASSUMED field of view may be off by (a sourced one, the box it spans)
EVENT_NEAR = 3           # frames: a rate step this close to a camera event is at the event
BEFORE_MIN = 2.0         # px/s: a scene drifting slower than this before the release gives the camera's rate no heading
                         # (a tenth of a pixel a frame is inside the capture's own jitter; PR051's ground held to 0.3)
BLUR_FLOOR = 1.5         # an image under this many blurs long cannot show a change of scale: the blur sets its size
                         # (FLIR1's NAR x2 -> MFOV x2: 15.6 px x 0.23 = 3.6 px, against a VCD copy's 4-px blur)
AGREE = math.log(1.25)   # a size ratio within 25 % of a field's change confirms it; a size held within 25 % across a
CHANGE_MIN = math.log(1.5)  # change of more than x1.5 that the object would show contradicts it
BRIEF = 6                # more stretches than this are summed up in the report, and listed in the CSV
EVENTS_PAD = 300         # frames either side of the track that `--events auto` looks for the overlay's events over
JUMP_SIGMA = 5.0         # a break where the track's two lines part by this many errors (and JUMP_MIN px) is a jump
WINDOW = 4.0             # the shape is measured in a window this many object sizes across (at least 33 px)
SIZE_STRETCHES = 6       # a trend in the object's size: the track cut into this many, their median sizes all in order (`size_trend`)
SIZE_MIN = 12            # frames a trend in the size needs: two to a stretch
# Over the part of a 2-D Gaussian above half its peak, its second moment along an axis is (1 - ln 2) sigma^2
# (E[r^2] = 2 (1 - ln 2) inside r^2 = 2 ln 2, half of it on each axis): its sigma there is 0.554 of the whole.
HALF_CUT = math.sqrt(1.0 - math.log(2.0))


# ---- the object's image, frame by frame --------------------------------------------------
def shape(grey, x, y, size=9.0, dark=False, mask=None):
    """The object's image round (x, y): its centroid, and its extent along and across its long axis
    (the full width at half maximum of the Gaussian whose part above half its peak has the same second
    moments: cut at half maximum, a 2-D Gaussian keeps 0.554 of its sigma), with its peak over the
    window's median. None where there is nothing above the median.

    The image is cut at half its peak and the part joined to the brightest pixel near (x, y) is kept,
    so a neighbour or a line of the overlay that does not touch it is left out. `mask` (the clip's
    graphics, True where the overlay is drawn) is taken out first."""
    r = int(max(16, round(WINDOW * size)))
    H, W = grey.shape
    x0, x1, y0, y1 = max(0, int(x) - r), min(W, int(x) + r + 1), max(0, int(y) - r), min(H, int(y) + r + 1)
    if x1 - x0 < 5 or y1 - y0 < 5:
        return None
    v = grey[y0:y1, x0:x1].astype(float)
    v = (np.median(v) - v) if dark else (v - np.median(v))
    if mask is not None:
        v[mask[y0:y1, x0:x1]] = 0.0
    yy, xx = np.mgrid[y0:y1, x0:x1]
    near = np.hypot(xx - x, yy - y) <= max(3.0, 0.6 * size)
    if not near.any() or v[near].max() <= 0:
        return None
    i = np.flatnonzero(near.ravel())[np.argmax(v[near])]
    pk = v.ravel()[i]
    lab, _ = ndimage.label(v > 0.5 * pk)
    blob = lab == lab.ravel()[i]
    w = v[blob]
    bx, by = xx[blob], yy[blob]
    cx, cy = (w * bx).sum() / w.sum(), (w * by).sum() / w.sum()
    cov = np.cov(np.vstack([bx - cx, by - cy]), aweights=w) if blob.sum() > 2 else np.eye(2) * 0.25
    ev, evec = np.linalg.eigh(np.atleast_2d(cov))
    ev = np.clip(ev, 1.0 / 12, None)                 # a single pixel's own second moment, at least
    fwhm = 2.0 * math.sqrt(2.0 * math.log(2.0)) / HALF_CUT
    ax = evec[:, 1]
    return dict(cx=float(cx), cy=float(cy), length_px=float(fwhm * math.sqrt(ev[1])),
                width_px=float(fwhm * math.sqrt(ev[0])), angle_deg=float(math.degrees(math.atan2(ax[1], ax[0])) % 180),
                peak=float(pk), pixels=int(blob.sum()))


def shapes(clip, track, size=9.0, dark=False, mask=None):
    """{frame: shape} for every tracked frame on disk. The frames are read on threads of this process, as many as
    `progress.workers` allows, to `progress.READERS`: each frame's shape is its own, and reading them one after another
    was all of the stage's wait on a long track (2026-11-13: PR088's 3,558 frames, 22 s at any number of workers)."""
    from concurrent.futures import ThreadPoolExecutor
    from .progress import READERS, workers
    ns = [n for n in sorted(track) if clip.n0 <= n <= clip.n1]

    def one(n):
        return shape(clip.grey(n), track[n][0], track[n][1], size, dark, mask)
    threads = min(workers(None, clip.W * clip.H), READERS, len(ns))
    if threads > 1:
        with ThreadPoolExecutor(threads, thread_name_prefix="mcdonald-read") as ex:
            got = list(ex.map(one, ns))
    else:
        got = [one(n) for n in ns]
    return {n: s for n, s in zip(ns, got) if s}


# ---- zoom steps ----------------------------------------------------------------------------
def _line_at(frames, values, at):
    """A straight line through (frames, values), evaluated at `at`."""
    if len(frames) >= 2 and np.ptp(frames) > 0:
        return float(np.polyval(np.polyfit(frames, values, 1), at))
    return float(np.mean(values))


def _split(L, lo, hi):
    """The index in L[lo:hi] that best splits it into two steady parts (least absolute deviation from each
    part's median)."""
    best, at = None, None
    for s in range(lo + 1, hi):
        a, b = L[lo:s], L[s:hi]
        c = np.abs(a - np.median(a)).sum() + np.abs(b - np.median(b)).sum()
        if best is None or c < best:
            best, at = c, s
    return at


def _steady(v):
    """Does a side of a size step hold: its log sizes' MAD under SPREAD_MAX, and none further than OUTLIER_MAX
    from their median?"""
    m = np.median(v)
    return bool(np.median(np.abs(v - m)) <= SPREAD_MAX and np.abs(v - m).max() <= OUTLIER_MAX)


def zoom_steps(track, shp, frame_w, frame_h, min_ratio=ZOOM_MIN, hold=HOLD, ratios=None):
    """The steps in the object's size inside a track, and which of them are the picture's zoom:
    [{frame, ratio, centre, applied, ...}], `frame` the first frame drawn at the new size.

    A step is looked for where the median of the object's log length over the `hold` frames after a frame
    differs from that over the `hold` frames before by at least log(min_ratio), each side steady (`_steady`: a
    zoom holds, frame after frame) and the 2 x hold frames close together (no gap in the track inside them). The
    frame itself is then the best split of the frames round it into two steady parts, and the ratio is the ratio
    of their medians. Its centre: the track's straight line over the `hold` frames before, carried to the step's
    frame, and the line after, carried back to it, are p_b and p_a; a zoom by r about c puts
    p_a - c = r (p_b - c), so c = (r p_b - p_a) / (r - 1). A zoom is about the optical axis, near the
    frame's centre: `confirmed_by_offset` says the centre came out within CENTRE_NEAR of the frame's larger
    side of it. A change of the object's own size (a gain step can make a small hot object look larger, a streak
    grows as it speeds up, a blob takes in a neighbour) gives a centre anywhere. Where the object sits at the
    centre already (p_a and p_b within JUMP_MIN px) its position cannot say where the centre is, and nothing
    tells the step from a sudden change of the object's own size but its suddenness: the step is kept, `centre`
    is None and `confirmed_by_offset` False.

    Only a step its offset confirms, or one whose ratio the person gives (`ratios`), is `applied`: taken out of
    the track by `to_one_scale` and set among the camera's events. The others are reported as the object's size
    steps, `why_not` saying why. On the PURSUE reference cases (2026-10-20) every step found was of this kind --
    PR135's birds, whose half-maximum blob takes in a neighbour or a wing; PR43's streak, which grows in length
    and not in width -- and none came out about the frame's centre; FLIR1's zoom came out 5 px from it. The width
    is measured too (`width_ratio`): an electronic zoom, as the ATFLIR's x2 is, scales it with the length (1.85
    against 1.91 on FLIR1); an optical one leaves an unresolved object's width at the blur's.

    The size's ratio runs low where the chain after the zoom blurs the picture by a fixed amount (FLIR1: 1.91
    for an ATFLIR's x2). So a second ratio is given, the offset's about the frame's centre
    (`ratio_from_offset`), right where the zoom is about the middle; and `ratios`, the steps' own ratios where
    the sensor prints them (the readout's 1.0 -> 2.0), are taken instead of the size's, in order, and the
    centre solved with them (`ratio_from` says which)."""
    fr = np.array(sorted(shp), int)
    if len(fr) < 2 * hold + 1:
        return []
    L = np.log([shp[n]["length_px"] for n in fr])
    Wd = np.log([shp[n]["width_px"] for n in fr])
    d = np.full(len(fr), np.nan)
    for i in range(hold, len(fr) - hold + 1):
        pre, post = L[i - hold:i], L[i:i + hold]
        if _steady(pre) and _steady(post) and fr[i + hold - 1] - fr[i - hold] <= 2 * hold + 2:
            d[i] = np.median(post) - np.median(pre)
    steps, done = [], -10 ** 9
    for i in np.flatnonzero(np.abs(np.nan_to_num(d)) >= math.log(min_ratio)):
        if i <= done:
            continue
        lo, hi = max(0, i - hold), min(len(fr), i + 2 * hold)
        j = _split(L, lo, hi)
        if j is None or j < hold or j > len(fr) - hold:
            continue
        pre, post = L[j - hold:j], L[j:j + hold]
        if not (_steady(pre) and _steady(post)):
            continue
        done = j + hold
        r_size = float(math.exp(np.median(post) - np.median(pre)))
        if max(r_size, 1 / r_size) < min_ratio:
            continue
        given = ratios[len(steps)] if ratios and len(steps) < len(ratios) else None
        r = float(given) if given else r_size
        b, a = fr[j - hold:j], fr[j:j + hold]
        pb = np.array([_line_at(b, [track[n][k] for n in b], fr[j]) for k in (0, 1)])
        pa = np.array([_line_at(a, [track[n][k] for n in a], fr[j]) for k in (0, 1)])
        jump = float(np.hypot(*(pa - pb)))
        c0 = np.array([frame_w / 2, frame_h / 2])
        db, da = float(np.hypot(*(pb - c0))), float(np.hypot(*(pa - c0)))
        step = dict(frame=int(fr[j]), ratio=r, ratio_from="given" if given else "size", ratio_from_size=r_size,
                    ratio_from_offset=float(da / db) if db > 5 else None, size_before_px=float(math.exp(np.median(pre))),
                    size_after_px=float(math.exp(np.median(post))),
                    width_ratio=float(math.exp(np.median(Wd[j:j + hold]) - np.median(Wd[j - hold:j]))), jump_px=jump,
                    before_px=[float(pb[0]), float(pb[1])], after_px=[float(pa[0]), float(pa[1])],
                    centre=None, confirmed_by_offset=False, centre_from_frame_centre_px=None)
        if jump >= JUMP_MIN and abs(r - 1) > 1e-6:
            c = (r * pb - pa) / (r - 1)
            off = float(np.hypot(c[0] - frame_w / 2, c[1] - frame_h / 2))
            step["centre"] = [float(c[0]), float(c[1])]
            step["centre_from_frame_centre_px"] = off
            step["confirmed_by_offset"] = bool(off <= CENTRE_NEAR * max(frame_w, frame_h))
        step["applied"] = bool(step["confirmed_by_offset"] or given)
        moved = abs(r - 1) * db                    # how far a zoom about the frame's centre would have moved it
        step["why_not"] = None if step["applied"] else (
            f"its jump puts the centre {step['centre_from_frame_centre_px']:.0f} px from the frame's, where a zoom's is"
            if step["centre"] else
            f"its position holds, where a zoom about the frame's centre would have moved it {moved:.0f} px"
            if moved >= 3 * JUMP_MIN else "the object sits near the frame's centre, so its position cannot say it was a zoom")
        steps.append(step)
    return steps


def size_trend(shp, steps=()):
    """What the object's size did through the track, where `zoom_steps` looks only for a sudden change (fifteen airliners
    closing on a camera, 2026-10-30: their images grew threefold and the stage said the size held steady). Its length in
    the first frame's scale (the zooms in `steps` taken out; a step not taken as a zoom stays, and is named in its own
    row), the median over the first and last thirds of the frames read, and over SIZE_STRETCHES stretches of the track.

    It `grows` or `shrinks` where those stretches are all in order and the thirds are AGREE apart (the 25 % this stage
    calls a size held). All six in order is 2 chances in 720 for a size that holds, whatever its noise's shape, and it
    keeps that near the stated rate as the noise gets memory: of sizes drawn to hold, wander and read noise together, 12 to
    3,000 frames, at most 0.25 % pass with no memory, 1.0 % with a memory a tenth of the track's length, 1.9 % with a fifth.
    (A slower wander is a change of size through the track, which is what this says.) A line fitted through the sizes,
    the looming test's `kinematics._trend`, could not be held to a rate: read noise on a wander hides the wander's memory from
    its lag-one correlation, and 12-14 % of drawn sizes passed at 4 sigma, at any length. On the arrivals' sizes the
    stretches run 4.7 5.8 7.1 9.4 13.3 21.1 px. PR144's 11.6 8.6 65 22 26 77 and PR43's 5.4 4.4 5.5 10.1 19.1 10.7 are no
    trend, though their thirds are five and three times apart: `kind` "moves" says so, and gives the stretches.

    Which of its range, its aspect, its light or a slow zoom of the picture did it, this does not say. Returns
    dict(kind ("grows", "shrinks", "holds" where the thirds are within AGREE, or "moves"), first_px, last_px, ratio,
    stretches_px, frames (first, last), n), or None under SIZE_MIN frames read."""
    fr = sorted(shp)
    if len(fr) < SIZE_MIN:
        return None
    y = np.log([shp[n]["length_px"] / scale_at(n, steps) for n in fr])
    third = len(y) // 3
    a, b = float(np.median(y[:third])), float(np.median(y[-third:]))
    med = np.array([np.median(part) for part in np.array_split(y, SIZE_STRETCHES)])
    d = np.diff(med)
    kind = "holds" if abs(b - a) < AGREE else ("grows" if b > a else "shrinks") if (d > 0).all() or (d < 0).all() else "moves"
    return dict(kind=kind, first_px=math.exp(a), last_px=math.exp(b), ratio=math.exp(b - a),
                stretches_px=[float(v) for v in np.exp(med)], frames=[int(fr[0]), int(fr[-1])], n=len(fr))


def size_said(tr):
    """A `size_trend` in words."""
    ends = f"{tr['first_px']:.1f} -> {tr['last_px']:.1f} px long from its first third to its last"
    if tr["kind"] in ("grows", "shrinks"):
        return (f"the object's size {tr['kind']} through the track: {ends} (x{tr['ratio']:.2f}), each of its {SIZE_STRETCHES} stretches "
                f"{'larger' if tr['kind'] == 'grows' else 'smaller'} than the one before: its range, its aspect, its light, or a slow "
                "zoom of the picture")
    if tr["kind"] == "holds":
        return f"none: the object's size holds within 25 %, {ends}"
    return (f"none: the object's size goes up and down, {ends} (x{tr['ratio']:.2f}) but not in order: "
            + ", ".join(f"{v:.1f}" for v in tr["stretches_px"]) + f" px over {SIZE_STRETCHES} stretches")


def zooms(steps):
    """The steps taken as the picture's zoom."""
    return [s for s in steps if s.get("applied", True)]


def to_one_scale(track, steps, frame_w, frame_h):
    """The track in the pixels of its first frame's zoom: each position after an applied step taken back through it,
    about the step's centre (the frame's centre where the step's own is not known)."""
    out = {}
    use = zooms(steps)
    for n, (x, y) in track.items():
        p = np.array([x, y], float)
        for s in reversed([s for s in use if s["frame"] <= n]):
            c = np.array(s["centre"] if s["centre"] else [frame_w / 2, frame_h / 2], float)
            p = c + (p - c) / s["ratio"]
        out[n] = (float(p[0]), float(p[1]))
    return out


def field_at(n, fields):
    """The field (deg) of the stretch of `fields` [(first, last, deg)] holding frame n, or None."""
    for a, b, deg in fields:
        if a <= n <= b:
            return float(deg)
    return None


def field_steps(fields, track, shp, frame_w, frame_h, hold=HOLD, blur_px=None, centre=None):
    """The changes of the field the display gives (`fields`, [(first, last, deg)] in frame order) as zoom steps, each
    checked on the object: [{frame, ratio, ratio_from: "field", deg_before, deg_after, size_check, ...}].

    Where two stretches next to each other have different fields, the picture's scale changes by deg_before / deg_after
    at the second one's first frame. The change is applied -- taken out of the track about `centre` (the boresight;
    the frame's centre where not given) and set among the camera's events -- whatever the object shows: the display
    says so. The object's size on the `hold` tracked frames nearest each side checks it. `size_check` says:

    - "confirms": the object's size ratio is within 25 % of the field's;
    - "contradicts": the object's size holds within 25 % across a change of more than x1.5 that it would show;
    - "no power": the object is tracked on fewer than two frames on one side, or its image on the smaller side
      (measured, or expected from the other side and the field's ratio) is under BLUR_FLOOR blurs long, so the blur
      sets its size. FLIR1's NAR x2 -> MFOV x2: 15.6 px expected to become 3.6 px, against its copy's 4-px blur;
    - "unclear": neither.

    `blur_px` is the picture's blur, px (default: the widest a stroke of the overlay is drawn at this height, plus
    one: 4 px at up to 576 rows). Where the object's offset from the centre jumps, the centre it implies is reported
    (`centre_implied`) as a check, not used. Changes with fewer than two tracked frames between them are checked
    together, as one change (`checked_with`), on the tracked frames either side of the run."""
    from . import forensics as vf
    blur = float(blur_px or vf.stroke_step(frame_h) + 1)
    c0 = np.array(centre if centre else (frame_w / 2.0, frame_h / 2.0), float)
    fr = np.array(sorted(shp), int)
    ch = [(int(a1), float(d0), float(d1), (a0, b0), (a1, b1))
          for (a0, b0, d0), (a1, b1, d1) in zip(fields, fields[1:]) if abs(float(d0) - float(d1)) > 1e-9]
    # changes with fewer than two tracked frames between them are checked together, as one change: FLIR1's two frames
    # at NAR x2 before MFOV, and its WFOV interlude, where the object is not tracked
    groups, i = [], 0
    while i < len(ch):
        j = i
        while j + 1 < len(ch) and sum(1 for n in fr if ch[j][0] <= n < ch[j + 1][0]) < 2:
            j += 1
        groups.append(ch[i:j + 1])
        i = j + 1
    out = []
    for g in groups:
        at0, d0, _, (a0, b0), _ = g[0]
        at1, _, d1, _, (a1, b1) = g[-1]
        R = d0 / d1
        pre = [n for n in fr if a0 <= n <= b0 and n < at0][-hold:]
        post = [n for n in fr if a1 <= n <= b1][:hold]
        together = (f"checked as one change of x{R:.2f} ({d0:g} -> {d1:g} deg) with "
                    + ", ".join(str(c[0]) for c in g) + "; " if len(g) > 1 else "")
        chk = dict(size_before_px=None, size_after_px=None, ratio_from_size=None, ratio_from_offset=None, width_ratio=None,
                   jump_px=None, centre_implied=None, frames_before=len(pre), frames_after=len(post),
                   checked_with=[c[0] for c in g] if len(g) > 1 else None)
        if len(pre) < 2 or len(post) < 2:
            chk["size_check"] = "no power"
            chk["size_why"] = together + (f"the object is tracked on {len(pre)} frame{'s' if len(pre) != 1 else ''} "
                                          f"before it and {len(post)} after")
        else:
            Lb = float(np.median([shp[n]["length_px"] for n in pre]))
            La = float(np.median([shp[n]["length_px"] for n in post]))
            Wb = float(np.median([shp[n]["width_px"] for n in pre]))
            Wa = float(np.median([shp[n]["width_px"] for n in post]))
            rs = La / Lb
            chk.update(size_before_px=Lb, size_after_px=La, ratio_from_size=rs, width_ratio=Wa / Wb)
            # what the field's change predicts, from the side less held up by the blur (the larger image)
            Pb, Pa = (Lb, Lb * R) if Lb >= La else (La / R, La)
            floor = BLUR_FLOOR * blur
            small = "before" if Pb < Pa else "after"
            P_small, M_small = (Pb, Lb) if small == "before" else (Pa, La)
            frames = f"frames {pre[0]}-{pre[-1]} against {post[0]}-{post[-1]}"
            if P_small < floor:
                if M_small >= floor and M_small >= 1.5 * P_small:
                    chk["size_check"] = "contradicts"
                    chk["size_why"] = together + (f"the field's x{R:.2f} would leave the object {P_small:.1f} px long "
                                                  f"{small} it, at the picture's {blur:g}-px blur, but it is "
                                                  f"{M_small:.1f} px ({Lb:.1f} -> {La:.1f}, {frames})")
                else:
                    chk["size_check"] = "no power"
                    chk["size_why"] = together + (f"the field's x{R:.2f} leaves the object {P_small:.1f} px long {small} "
                                                  f"it, under {BLUR_FLOOR:g} times the picture's {blur:g}-px blur, which "
                                                  f"then sets its size ({Lb:.1f} -> {La:.1f} px, {frames})")
            elif abs(math.log(rs) - math.log(R)) <= AGREE:
                chk["size_check"] = "confirms"
                chk["size_why"] = together + f"the object {Lb:.1f} -> {La:.1f} px long, x{rs:.2f} for the field's x{R:.2f}"
            elif abs(math.log(rs)) <= AGREE and abs(math.log(R)) >= CHANGE_MIN:
                chk["size_check"] = "contradicts"
                chk["size_why"] = together + (f"the object's length holds ({Lb:.1f} -> {La:.1f} px, {frames}) where the "
                                              f"field's x{R:.2f} would show in it")
            else:
                chk["size_check"] = "unclear"
                chk["size_why"] = together + f"the object {Lb:.1f} -> {La:.1f} px long, x{rs:.2f} for the field's x{R:.2f}"
            pb = np.array([_line_at(pre, [track[n][k] for n in pre], at0) for k in (0, 1)])
            pa = np.array([_line_at(post, [track[n][k] for n in post], at1) for k in (0, 1)])
            chk["jump_px"] = float(np.hypot(*(pa - pb)))
            db = float(np.hypot(*(pb - c0)))
            chk["ratio_from_offset"] = float(np.hypot(*(pa - c0)) / db) if db > 5 else None
            if chk["jump_px"] >= JUMP_MIN and abs(R - 1) > 1e-6:
                chk["centre_implied"] = [float(v) for v in (R * pb - pa) / (R - 1)]
        for at, e0, e1, _, _ in g:
            out.append(dict(frame=at, ratio=e0 / e1, ratio_from="field", deg_before=e0, deg_after=e1,
                            centre=[float(c0[0]), float(c0[1])] if centre else None, confirmed_by_offset=False,
                            applied=True, why_not=None, blur_px=blur, **chk))
    return out


def imaged_steps(zoom, track, shp, frame_w, frame_h, blur_px=None, centre=None):
    """`mcdonald zoom`'s measured steps inside the track (its boundaries with the verdict "step", a burst of blank
    frames or a step of the picture with no blank) as zoom steps: [{frame, ratio, ratio_from: "imagery", ...}],
    `frame` the first frame after the burst. Each is applied at the imagery's scale -- taken out of the track about
    `centre` (the frame's centre where not given) and set among the camera's events -- and checked on the object's
    size as `field_steps` checks a display's change of field ("confirms", "contradicts", "no power", "unclear").
    Where the fit placed the narrower picture in the wider (`imaged_centre`) is kept as a check, not used: it holds
    the camera's own turn during the burst as well as the zoom's centre."""
    if not track or not zoom:
        return []
    n0, n1 = min(track), max(track)
    rows = [r for r in zoom.get("bursts", []) if r["verdict"] == "step" and n0 < first_new(r) <= n1]
    if not rows:
        return []
    fields, start, scale = [], n0, 1.0                  # the picture's scale as a field: 1 / magnification
    for r in rows:
        fields.append((start, first_new(r) - 1, scale))
        scale /= float(r["s"])
        start = first_new(r)
    fields.append((start, n1, scale))
    out = field_steps(fields, track, shp, frame_w, frame_h, blur_px=blur_px, centre=centre)
    for st, r in zip(out, rows):
        if st.get("size_why"):
            st["size_why"] = st["size_why"].replace("the field's", "the picture's")
        st.update(ratio=float(r["s"]), ratio_from="imagery", deg_before=None, deg_after=None, burst=r["frames"],
                  kind=r.get("kind", "blank"), zncc=r.get("zncc"), prominence=r.get("prominence"),
                  imaged_centre=r.get("centre"))
    return out


def first_new(row):
    """The first frame after a `mcdonald zoom` boundary: the one after its blank frames, or for a step of the picture
    with no blank, the frame it steps on."""
    a, b = row["frames"]
    return int(a) if row.get("kind") == "picture" else int(b) + 1


def burst_events(zoom, n0, n1):
    """`mcdonald zoom`'s bursts with no measured step, near frames n0-n1, as camera events [(frame, what)]: a rate step
    there is the camera's until shown otherwise, and across an unknown one the scale may have changed."""
    out = []
    for r in (zoom or {}).get("bursts", []):
        a, b = r["frames"]
        if r["verdict"] == "step" or b + 1 < n0 - EVENT_NEAR or a > n1 + EVENT_NEAR:
            continue
        out.append((first_new(r), f"blank frames {a}-{b}, " + ("the scale as before" if r["verdict"] == "no step" else
                                                               "a zoom not measured")))
    return out


# ---- the phone's record of its own zoom (`mcdonald phone`) ---------------------------------------
RECORD_PAD = 8           # tracked frames read either side of a stretch where the record's zoom moves
RECORD_MOVE = math.log(1.10)  # the record's zoom must move by x1.10 over the frames read, or the pictures cannot check it
RECORD_MIN = 12          # tracked frames, with a size, the check needs
# The slope of the object's log size on the record's log zoom is 1 where the picture's scale follows the record. A
# half-maximum size runs a little under it (a blur adds to the image in quadrature: a 20-px image with 4 px of blur
# reads a slope of 0.96), and an object's size wanders with its light and aspect; what the check is for is a record
# that is not this clip's zoom -- a field read in another phone's layout, a record shifted in time against its
# pictures -- whose slope is near 0 or anywhere. SLOPE_TOL is the margin: a JUDGEMENT, set from the one clip that carries
# the record (a witness's, not shared: its zoom slips followed by the object's height over the horizon at a slope near 1),
# not from a null; the slope's own 95 % interval (RECORD_Z errors, the residuals' memory counted) must be inside it for
# the check to decide.
SLOPE_TOL = 0.25
RECORD_Z = 1.96


def record_runs(curve, pad=0):
    """The stretches of frames over which a zoom record ({frame: zoom}) moves: [(first, last)], each widened by
    `pad` frames, those that then touch joined."""
    fr = sorted(curve)
    moving = [fr[i] for i in range(1, len(fr)) if abs(curve[fr[i]] - curve[fr[i - 1]]) > 1e-4]
    out = []
    for n in moving:
        a, b = n - 1 - pad, n + pad
        if out and a <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [tuple(r) for r in out]


def record_frames(curve, track, pad=RECORD_PAD):
    """The tracked frames the check reads: those within `pad` frames of a stretch where the record's zoom moves."""
    runs = record_runs(curve, pad)
    return sorted(n for n in track if n in curve and any(a <= n <= b for a, b in runs))


def record_check(curve, shp, frame_h=None, blur_px=None):
    """Does the picture's scale follow the phone's record of its zoom? Over the tracked frames near each stretch where
    the record's zoom moves (`record_frames`), the object's log length against the record's log zoom, each stretch's
    own means taken out (so that the object's own slow change of size between stretches does not count): the slope
    (1 where the picture follows the record), its error (the residuals' lag-one memory counted: the variance is
    (1 + rho) / (1 - rho) times the plain one's, for a smooth zoom), and r. dict(verdict, slope, err, r, n, frames,
    zoom (least, most over the frames read), why):

    - "agrees": the slope within SLOPE_TOL of 1, and known to better than that (RECORD_Z errors inside the margin);
    - "disagrees": the slope's interval (RECORD_Z errors either side) wholly outside 1 +- SLOPE_TOL -- the record is
      not this clip's zoom, and is not used;
    - "no power": the zoom does not move by x1.10 over the tracked frames, fewer than RECORD_MIN of them have a size,
      the object at the lowest zoom (its median length within 2 % of it) is under BLUR_FLOOR blurs long, or neither.

    `shp` is `shapes`' for (at least) those frames; `blur_px` the picture's blur (default as `field_steps` takes it)."""
    from . import forensics as vf
    fr = [n for n in sorted(shp) if n in curve]
    runs = record_runs(curve, RECORD_PAD)
    out = dict(verdict="no power", slope=None, err=None, r=None, n=0, frames=None, zoom=None, why=None)
    if not runs:
        z = sorted(set(round(curve[n], 4) for n in fr)) if fr else []
        out["why"] = (f"the record's zoom holds at {z[0]:.3g} on every tracked frame, so the pictures cannot check it"
                      if len(z) == 1 else "no tracked frame to check the record against")
        return out
    groups = [[n for n in fr if a <= n <= b] for a, b in runs]
    groups = [g for g in groups if len(g) >= 3]
    use = [n for g in groups for n in g]
    out.update(n=len(use), frames=[int(use[0]), int(use[-1])] if use else None)
    if len(use) < RECORD_MIN:
        out["why"] = (f"{len(use)} tracked frame{'s' if len(use) != 1 else ''} with a size where the record's zoom moves "
                      f"(frames {', '.join(f'{a + RECORD_PAD + 1}-{b - RECORD_PAD}' for a, b in runs)}), under {RECORD_MIN}")
        return out
    zs = np.array([curve[n] for n in use])
    out["zoom"] = [float(zs.min()), float(zs.max())]
    if math.log(zs.max() / zs.min()) < RECORD_MOVE:
        out["why"] = (f"the record's zoom moves only from {zs.min():.3g} to {zs.max():.3g} over the tracked frames, under "
                      f"x{math.exp(RECORD_MOVE):.2f}: too little for the pictures to check")
        return out
    blur = float(blur_px or vf.stroke_step(frame_h or 1080) + 1)
    small = float(np.median([shp[n]["length_px"] for n in use if curve[n] <= zs.min() * 1.02]))
    if small < BLUR_FLOOR * blur:
        out["why"] = (f"the object is {small:.1f} px long at the lowest zoom, under {BLUR_FLOOR:g} times the picture's "
                      f"{blur:g}-px blur, which then sets its size")
        return out
    x, y, res = [], [], []
    for g in groups:
        gx = np.log([curve[n] for n in g])
        gy = np.log([shp[n]["length_px"] for n in g])
        x.append(gx - gx.mean())
        y.append(gy - gy.mean())
    X, Y = np.concatenate(x), np.concatenate(y)
    sxx = float((X ** 2).sum())
    if sxx <= 0:
        out["why"] = "the record's zoom does not move within any stretch of tracked frames"
        return out
    slope = float((X * Y).sum() / sxx)
    for gx, gy in zip(x, y):
        res.append(gy - slope * gx)
    R = np.concatenate(res)
    lag = [np.corrcoef(e[:-1], e[1:])[0, 1] for e in res if len(e) > 3 and e[:-1].std() > 0 and e[1:].std() > 0]
    rho = float(np.mean(lag)) if lag else 0.0
    rho = min(max(rho if np.isfinite(rho) else 0.0, 0.0), 0.95)
    dof = max(len(R) - 1 - len(groups), 1)
    err = float(math.sqrt((R ** 2).sum() / dof / sxx * (1 + rho) / (1 - rho)))
    r = float(np.corrcoef(X, Y)[0, 1]) if Y.std() > 0 else 0.0
    out.update(slope=slope, err=err, r=r, rho=rho)
    said = (f"slope {slope:.2f} +- {err:.2f}, r {r:.3f}, over {len(use)} tracked frames as the zoom went {zs.min():.3g} "
            f"to {zs.max():.3g}")
    if abs(slope - 1) - RECORD_Z * err > SLOPE_TOL:
        out.update(verdict="disagrees", why=f"the object's size does not follow the record's zoom: {said}, where 1 is "
                                            "the picture following it")
    elif RECORD_Z * err > SLOPE_TOL:
        out["why"] = f"the object's size is too unsteady to check the record by: {said}"
    elif abs(slope - 1) <= SLOPE_TOL:
        out.update(verdict="agrees", why=f"the object's size follows the record's zoom: {said}")
    else:
        out["why"] = f"the object's size follows the record's zoom only in part: {said}"
    return out


def record_steps(curve, track, check=None):
    """The phone's record of its zoom ({frame: zoom}) as zoom steps inside the track: one at each tracked frame whose
    zoom differs from the tracked frame's before it, `ratio` theirs, about the frame's centre (a phone's zoom crops
    about the middle of its sensor), `ratio_from` "record". Applied -- taken out of the track by `to_one_scale` --
    unless the pictures disagree with the record (`check`, `record_check`'s): then none is applied, and each says
    why not."""
    fr = [n for n in sorted(track) if n in curve]
    out = []
    use = not (check and check.get("verdict") == "disagrees")
    for a, b in zip(fr, fr[1:]):
        za, zb = curve[a], curve[b]
        if abs(zb - za) > 1e-6:
            out.append(dict(frame=int(b), ratio=float(zb / za), ratio_from="record", zoom_before=float(za), zoom_after=float(zb),
                            centre=None, confirmed_by_offset=False, applied=use, size_check=(check or {}).get("verdict"),
                            why_not=None if use else "the object's size does not follow the phone's record"))
    return out


def scale_at(n, steps):
    """How many times the picture at frame n is magnified over the track's first frame."""
    use = zooms(steps)
    return float(np.prod([s["ratio"] for s in use if s["frame"] <= n])) if use else 1.0


# ---- rate steps ----------------------------------------------------------------------------
def _noise(fr, x, y):
    """Position noise per coordinate, px, from second differences of consecutive frames (6 sigma^2 each)."""
    ok = (np.diff(fr[:-1]) == 1) & (np.diff(fr[1:]) == 1)
    if ok.sum() < 3:
        return 0.5
    d2 = np.concatenate([(v[2:] - 2 * v[1:-1] + v[:-2])[ok] for v in (x, y)])
    return float(max(1.4826 * np.median(np.abs(d2 - np.median(d2))) / math.sqrt(6.0), 0.05))


def _sse_table(t, v):
    """Cumulative sums for the residual sum of squares of a straight line through any run t[i:j]."""
    c = lambda a: np.concatenate([[0.0], np.cumsum(a)])
    return c(np.ones_like(t)), c(t), c(t * t), c(v), c(t * v), c(v * v)


def _sse(tab, i, j):
    n, st, stt, sv, stv, svv = (a[j] - a[i] for a in tab)
    if n < 2:
        return 0.0
    vt = stt - st * st / n
    vv = svv - sv * sv / n
    cv = stv - st * sv / n
    return float(max(vv - (cv * cv / vt if vt > 0 else 0.0), 0.0))


def rate_steps(track, fps, min_seg=MIN_SEG, sigma=None):
    """The track as straight lines between breakpoints: as few as the noise allows (a residual sum of squares,
    over both coordinates, with log(n) sigma^2 for each of a stretch's four numbers -- the Schwarz criterion),
    each stretch at least `min_seg` frames. [{frames, n, vx, vy, v_px_per_s, err_px_per_s, ...}] and the noise.
    The noise is the track's from second differences, at least NOISE_FLOOR; a stretch's error is from the larger
    of it and the stretch's own residuals, which are larger where the object is fast or the picture zoomed in.

    `track` is {frame: (x, y)}, best in one scale (`to_one_scale`): a zoom inside it is otherwise a jump the
    fit must spend a stretch on.

    Each stretch after the first also says how far the track jumped where it begins (`jump_px`, with
    `jump_sigma`): the two lines either side, carried to the half frame between them, part by that much. An
    object's position does not jump, so a jump well over its error is the track's or the picture's -- a tracker
    that took another feature for a few frames, a frame dropped or repeated, a cut, a zoom not taken out -- and the
    stretch it starts is no rate of the object's (PR141's 440 px/s for four frames between 255 and 236)."""
    fr = np.array(sorted(track), int)
    if len(fr) < 2 * min_seg:
        return [], None
    t = (fr - 1) / float(fps)
    x = np.array([track[n][0] for n in fr], float)
    y = np.array([track[n][1] for n in fr], float)
    sig = float(sigma) if sigma else max(_noise(fr, x, y), NOISE_FLOOR)
    tx, ty = _sse_table(t, x), _sse_table(t, y)
    N = len(fr)
    pen = 4 * math.log(2 * N) * sig * sig
    # optimal partitioning with PELT's pruning: a start that cannot win now never wins later
    best = np.full(N + 1, np.inf)
    best[0] = 0.0
    prev = np.zeros(N + 1, int)
    cand = [0]
    for j in range(min_seg, N + 1):
        costs = {i: best[i] + _sse(tx, i, j) + _sse(ty, i, j) + pen for i in cand
                 if j - i >= min_seg and np.isfinite(best[i])}
        if costs:
            i = min(costs, key=costs.get)
            best[j], prev[j] = costs[i], i
            # a start whose cost without this stretch's penalty already passes the best cannot win later
            cand = [i for i in cand if i not in costs or costs[i] - pen <= best[j]]
        cand.append(j)
    cuts, j = [], N
    while j > 0:
        cuts.append((prev[j], j))
        j = prev[j]
    out, lines = [], []
    for i, j in reversed(cuts):
        tt = t[i:j]
        (vx, x0), (vy, y0) = np.polyfit(tt, x[i:j], 1), np.polyfit(tt, y[i:j], 1)
        sxx = ((tt - tt.mean()) ** 2).sum()
        n = j - i
        own = math.sqrt((_sse(tx, i, j) + _sse(ty, i, j)) / (2 * (n - 2))) if n > 2 else 0.0
        noise = max(sig, own)
        err = noise / math.sqrt(sxx) if sxx > 0 else float("inf")
        v = math.hypot(vx, vy)
        st = dict(frames=[int(fr[i]), int(fr[j - 1])], n=int(n), vx=float(vx), vy=float(vy),
                  v_px_per_s=float(v), err_px_per_s=float(err), noise_px=float(noise),
                  direction_deg=float(math.degrees(math.atan2(vx, -vy)) % 360))
        line = (vx, x0, vy, y0, float(tt.mean()), float(sxx), n, noise)
        if lines:
            tb = 0.5 * (t[i - 1] + t[i])
            a, b = lines[-1], line
            gap = math.hypot((b[1] + b[0] * tb) - (a[1] + a[0] * tb), (b[3] + b[2] * tb) - (a[3] + a[2] * tb))
            # each line's error at tb, per coordinate: noise^2 (1/n + (tb - mean)^2 / sxx); the gap is two coordinates
            e2 = sum(L[7] ** 2 * (1.0 / L[6] + ((tb - L[4]) ** 2 / L[5] if L[5] > 0 else 0.0)) for L in (a, b))
            st["jump_px"] = float(gap)
            st["jump_sigma"] = float(gap / math.sqrt(2.0 * e2)) if e2 > 0 else float("inf")
        lines.append(line)
        out.append(st)
    return out, sig


def at_events(stretches, events, near=EVENT_NEAR):
    """Each breakpoint (the first frame of every stretch after the first), with the nearest camera event and
    whether it is within `near` frames of it, and whether the track jumps there (`jump`: by more than JUMP_SIGMA
    times its error and JUMP_MIN px). `events` is [(frame, what)]."""
    rows = []
    for a, b in zip(stretches, stretches[1:]):
        n = b["frames"][0]
        e = min(events, key=lambda ev: abs(ev[0] - n)) if events else None
        rows.append(dict(frame=int(n), rate_before_px_per_s=a["v_px_per_s"], rate_after_px_per_s=b["v_px_per_s"],
                         jump_px=b.get("jump_px"), jump=bool(b.get("jump_px", 0) >= JUMP_MIN
                                                             and b.get("jump_sigma", 0) >= JUMP_SIGMA),
                         event=None if e is None else dict(frame=int(e[0]), what=e[1]),
                         frames_from_event=None if e is None else int(n - e[0]),
                         at_event=bool(e is not None and abs(n - e[0]) <= near)))
    return rows


def parse_events(text):
    """`2208:gate vanishes,2238:zoom readout` -> [(2208, 'gate vanishes'), (2238, 'zoom readout')]."""
    out = []
    for part in (text or "").split(","):
        part = part.strip()
        if not part:
            continue
        n, _, what = part.partition(":")
        out.append((int(n), what.strip() or "an event given"))
    return out


# ---- the released-track null ----------------------------------------------------------------------
def departure(track, after, fps, breaks=(), min_seg=MIN_SEG, size=9.0):
    """The object's rate over its departure as a whole: a straight line through the track from the release's frame
    `after` to the end of the track, or to the first break after it where the track jumps by more than the object's
    own width twice over (`rate_steps`'s `jump`, of at least 2 `size`: a dash, a tracker on another feature -- not a
    saturated bloom's centroid wobbling by a few pixels), whichever comes first. The line's error is from its own
    residuals. None under `min_seg` frames. A track cut into many short stretches by its own jitter still has one
    departure."""
    end = min([b["frame"] for b in breaks if b["frame"] > after and b.get("jump") and (b.get("jump_px") or 0) >= 2 * size],
              default=None)
    fr = sorted(n for n in track if n >= after and (end is None or n < end))
    if len(fr) < min_seg:
        return None
    t = (np.array(fr, float) - 1) / float(fps)
    x, y = np.array([track[n][0] for n in fr]), np.array([track[n][1] for n in fr])
    (vx, x0), (vy, y0) = np.polyfit(t, x, 1), np.polyfit(t, y, 1)
    sxx = float(((t - t.mean()) ** 2).sum())
    n = len(fr)
    ex, ey = [math.sqrt(((v - (a * t + b)) ** 2).sum() / max(n - 2, 1)) / math.sqrt(sxx) for v, a, b in ((x, vx, x0), (y, vy, y0))]
    v = math.hypot(vx, vy)
    err = math.hypot(vx * ex, vy * ey) / v if v > 0 else math.hypot(ex, ey)
    return dict(frames=[int(fr[0]), int(fr[-1])], n=int(n), vx=float(vx), vy=float(vy), v_px_per_s=float(v),
                err_px_per_s=float(err), direction_deg=float(math.degrees(math.atan2(vx, -vy)) % 360),
                cut_at_jump=None if end is None else int(end))


def released(stretches, los_rate_deg_s, los_err_deg_s=0.0, after=None, scale_err=0.0, heading_deg=None, against=None,
             whole=None):
    """Is the object's departure faster than the camera had been turning?

    A camera that held the object turned at its bearing rate; once it stops following, the object crosses
    the picture at that rate and no faster. Each stretch's rate in deg/s (`deg_per_s`, in one scale, so with
    the first frame's k) -- of those ending after frame `after`, if given -- is set against the camera's rate
    before, and the fastest decides. `scale_err` is the share by which k may be off: it scales every rate of
    the object's and none of the camera's (a readout's degrees are the sensor's own), so it is part of the
    comparison's error. Within two sigma of the camera's rate or below: what a camera that stopped following
    shows, and no acceleration of the object's own is needed. Faster: the release alone does not explain it.
    `z_without_scale` is the same comparison with the scale taken as exact.

    Every stretch after the release is compared the same way (`stretches`, each with its `z` and `within`), and
    the first of them is named beside the fastest: a drift the release explains can come before a departure it
    does not. With `heading_deg`, the direction the camera had been turning against the ground (the scene's drift
    through the picture, clockwise from screen-up), each stretch also says how far its own direction is from the
    one the release would send the object (`direction_off_deg`: the other way, 180 deg from the scene's), since an
    object let go keeps its motion, direction and all. `against` names what the camera's rate is set against
    ("the ground" with --scene) in what is said. `whole` (`departure`) is the object's rate over the departure as a
    whole, a line through the track from the release to its end or its first jump: compared the same way, and said
    first where it is there, since a track cut into short stretches by its own jitter has one departure all the same."""
    use = [s for s in stretches if (after is None or s["frames"][1] > after) and s["n"] >= MIN_SEG and "deg_per_s" in s]
    if not use:
        return None
    whole = whole if (whole and "deg_per_s" in whole) else None

    def compare(s):
        d = s["deg_per_s"] - los_rate_deg_s
        z0 = d / max(math.hypot(s["err_deg_per_s"], los_err_deg_s or 0.0), 1e-12)
        z = d / max(math.sqrt(s["err_deg_per_s"] ** 2 + (los_err_deg_s or 0.0) ** 2
                              + (scale_err * s["deg_per_s"]) ** 2), 1e-12)
        zw = (d / max(math.sqrt(s["err_wander_deg_per_s"] ** 2 + (los_err_deg_s or 0.0) ** 2
                                + (scale_err * s["deg_per_s"]) ** 2), 1e-12) if "err_wander_deg_per_s" in s else None)
        off = None
        if heading_deg is not None and "direction_deg" in s:
            off = abs((s["direction_deg"] - heading_deg - 180.0 + 180.0) % 360.0 - 180.0)
        return dict(frames=s["frames"], deg_per_s=s["deg_per_s"], err_deg_per_s=s["err_deg_per_s"], z=float(z),
                    z_without_scale=float(z0), within=bool(z <= 2.0), direction_deg=s.get("direction_deg"),
                    direction_off_deg=None if off is None else float(off),
                    z_wander=None if zw is None else float(zw), within_wander=None if zw is None else bool(zw <= 2.0))

    rows = [compare(s) for s in use]
    top = max(rows, key=lambda r: r["deg_per_s"])
    first = min(rows, key=lambda r: r["frames"][0])
    w = compare(whole) if whole else None
    z, z0, within = top["z"], top["z_without_scale"], top["within"]
    faster = [r for r in rows if not r["within"]]
    turning = f"turning against {against}" if against else "turning"
    crosses = f"crosses {against}" if against else "crosses the picture"
    camera = (f"against the {los_rate_deg_s:.4g}" + (f" +- {los_err_deg_s:.2g}" if los_err_deg_s else "")
              + f" deg/s the camera had been {turning}")

    def verdict(r):
        return (f"{r['z']:+.1f} sigma" + (f" ({r['z_without_scale']:+.1f} with the scale exact)" if scale_err else "") + ", "
                + ("no faster than a camera that stopped following would show it, so no acceleration of the object's "
                   "own is needed" if r["within"] else f"faster than the camera had been {turning}, which the release alone "
                   "does not explain"))

    def heading(r):
        return (f"; it heads {r['direction_deg']:.0f} deg (clockwise from screen-up), {r['direction_off_deg']:.0f} deg off "
                "the way the release would send it" if r["direction_off_deg"] is not None else "")

    if w:
        said = (f"over the departure as a whole, frames {w['frames'][0]}-{w['frames'][1]}"
                + (f" (to the jump at {whole['cut_at_jump']})" if whole.get("cut_at_jump") else "")
                + f", the object {crosses} at {w['deg_per_s']:.4g} +- {w['err_deg_per_s']:.2g} deg/s"
                + (f" (and +- {100 * scale_err:.0f} % for the scale)" if scale_err else "")
                + f", {camera}: {verdict(w)}{heading(w)}. Its fastest stretch, frames {top['frames'][0]}-{top['frames'][1]}, "
                f"{top['deg_per_s']:.4g} +- {top['err_deg_per_s']:.2g} deg/s ({top['z']:+.1f} sigma)")
    else:
        said = (f"the fastest stretch, frames {top['frames'][0]}-{top['frames'][1]}, {crosses} at "
                f"{top['deg_per_s']:.4g} +- {top['err_deg_per_s']:.2g} deg/s"
                + (f" (and +- {100 * scale_err:.0f} % for the scale)" if scale_err else "")
                + f", {camera}: {verdict(top)}{heading(top)}")
    if len(rows) > 1:
        said += (f". Of the {len(rows)} stretches after the release {len(faster)} " + ("is" if len(faster) == 1 else "are")
                 + f" faster than the camera had been {turning}; the first, frames "
                 f"{first['frames'][0]}-{first['frames'][1]} at {first['deg_per_s']:.4g} +- {first['err_deg_per_s']:.2g} deg/s "
                 f"({first['z']:+.1f} sigma), " + ("is not" if first["within"] else "is"))
    if top.get("z_wander") is not None:                 # B16: the same comparisons with the track's own wander in the errors
        said += (". With the departure's own wander in each rate's error (its fitted covariance, not white residuals), "
                 + (f"the departure as a whole is {w['z_wander']:+.1f} sigma and " if w and w.get("z_wander") is not None else "")
                 + f"the fastest stretch {top['z_wander']:+.1f} sigma"
                 + (": " + ("within" if (w or top)["within_wander"] else "faster than") + f" the camera's rate"
                    if (w or top).get("within_wander") is not None else ""))
    return dict(fastest=dict(frames=top["frames"], deg_per_s=top["deg_per_s"], err_deg_per_s=top["err_deg_per_s"],
                             direction_off_deg=top["direction_off_deg"]),
                first=dict(frames=first["frames"], deg_per_s=first["deg_per_s"], err_deg_per_s=first["err_deg_per_s"],
                           z=first["z"], within=first["within"], direction_off_deg=first["direction_off_deg"]),
                whole=None if not w else dict(frames=w["frames"], deg_per_s=w["deg_per_s"], err_deg_per_s=w["err_deg_per_s"],
                                              v_px_per_s=whole["v_px_per_s"], err_px_per_s=whole["err_px_per_s"], z=w["z"],
                                              within=w["within"], direction_deg=w["direction_deg"],
                                              direction_off_deg=w["direction_off_deg"], cut_at_jump=whole.get("cut_at_jump")),
                los_rate_deg_s=float(los_rate_deg_s), los_err_deg_s=float(los_err_deg_s or 0.0), scale_err=float(scale_err),
                z=float(z), z_without_scale=float(z0), within_camera_rate=within, n_faster=len(faster),
                z_wander=top.get("z_wander"), within_wander=top.get("within_wander"),
                whole_z_wander=w.get("z_wander") if w else None, whole_within_wander=w.get("within_wander") if w else None,
                heading_deg=None if heading_deg is None else float(heading_deg), against=against, said=said,
                stretches=rows)


# ---- the scene as the camera's own record --------------------------------------------------------
def read_scene(path):
    """A `layers` CSV as the scene's path: `slew.read_layers` and `slew.scene_path`, the pairs weighed by their own
    errors where the file has them. {frames, X, Y, S (the stretch each frame is on, -1 inside a gap), E (the path's
    own error from its stretch's start), k}."""
    from . import slew
    fr, _, dx, dy, k, _, err = slew.read_layers(path, errors=True)
    frames, X, Y, S, _, E = slew.scene_path(fr, dx, dy, k, err=err)
    return dict(frames=np.asarray(frames, int), X=np.asarray(X, float), Y=np.asarray(Y, float), S=np.asarray(S, int),
                E=np.asarray(E, float), k=int(k), path=str(path))


def relative_to_scene(track, scene, after=None):
    """The track with the camera's own motion taken out: each position less the scene's path at that frame, so the
    object's motion is against the ground, not the picture. The path is one stretch at a time (a gap in it starts
    its offset again), so the track is held to one stretch: the one the frame `after` is on, else the one with
    the most tracked frames on it. Returns ({frame: (x, y)}, the stretch's number, how many tracked frames fall
    off it)."""
    at = {int(n): i for i, n in enumerate(scene["frames"])}
    on = {n: scene["S"][at[n]] for n in track if n in at and scene["S"][at[n]] >= 0 and np.isfinite(scene["X"][at[n]])}
    if not on:
        return {}, None, len(track)
    if after is not None and after in on:
        s = int(on[after])
    else:
        counts = {}
        for v in on.values():
            counts[int(v)] = counts.get(int(v), 0) + 1
        s = max(counts, key=counts.get)
    rel = {n: (track[n][0] - scene["X"][at[n]], track[n][1] - scene["Y"][at[n]]) for n, v in on.items() if v == s}
    return rel, s, len(track) - len(rel)


def camera_before(scene, n0, n1, fps, stretch=None):
    """The camera's rate against the ground before the object left: the scene's drift through the picture over
    frames n0..n1 of its path, a straight line through its position there, on one stretch (`stretch`, else the one
    n1 is on). The error is the larger of the line's own and the path's (the pairs' errors summed along it,
    `slew.scene_path`). None where fewer than MIN_SEG frames of the window are on the stretch."""
    at = {int(n): i for i, n in enumerate(scene["frames"])}
    idx = [at[n] for n in range(int(n0), int(n1) + 1) if n in at and np.isfinite(scene["X"][at[n]])]
    if stretch is None and idx:
        stretch = int(scene["S"][idx[-1]])
    idx = [i for i in idx if scene["S"][i] == stretch]
    if len(idx) < MIN_SEG:
        return None
    t = (scene["frames"][idx] - 1) / float(fps)
    X, Y = scene["X"][idx], scene["Y"][idx]
    (vx, x0), (vy, y0) = np.polyfit(t, X, 1), np.polyfit(t, Y, 1)
    sxx = float(((t - t.mean()) ** 2).sum())
    n = len(idx)
    own = [math.sqrt(((v - (a * t + b)) ** 2).sum() / max(n - 2, 1)) / math.sqrt(sxx) for v, a, b in ((X, vx, x0), (Y, vy, y0))]
    E = scene["E"]
    span = float(t[-1] - t[0])
    chain = [math.sqrt(max(E[idx[-1], j] ** 2 - E[idx[0], j] ** 2, 0.0)) / span if np.isfinite(E[idx[-1], j]) else 0.0
             for j in range(2)]
    ex, ey = max(own[0], chain[0]), max(own[1], chain[1])
    v = math.hypot(vx, vy)
    err = math.hypot(vx * ex, vy * ey) / v if v > 0 else math.hypot(ex, ey)
    return dict(frames=[int(scene["frames"][idx[0]]), int(scene["frames"][idx[-1]])], n=n, vx=float(vx), vy=float(vy),
                v_px_per_s=float(v), err_px_per_s=float(err), err_x_px_per_s=float(ex), err_y_px_per_s=float(ey),
                direction_deg=float(math.degrees(math.atan2(vx, -vy)) % 360), stretch=int(stretch))


# ---- the stage -------------------------------------------------------------------------------
def measure(clip, track, size=9.0, dark=False, mask=None, fov=None, fov_px=None, graticule=None, los_rate=None,
            los_err=0.0, events=(), after=None, out=None, tag="", ratios=None, scale_err=None, fields=None,
            blur_px=None, centre=None, zoom=None, scene=None, pixel_aspect=1.0, record=None, checked=None, k_record=None):
    """The camera stage: zoom steps, the track in one scale, its rate steps against the camera's events, and
    -- with an angular scale and the camera's rate before -- the released-track null. A Found.

    `scene` (`read_scene`'s, from a `layers` CSV of the same frames) takes the camera's own motion out: the track
    is made relative to the scene's path (`relative_to_scene`), its rate steps are the object's against the ground,
    and the camera's rate before the release (`after`) is the scene's drift through the picture while the camera
    held the object (`camera_before`), in place of `los_rate`. `pixel_aspect` (the width of a pixel over its
    height, 4/3 for a 4:3 sensor shown on 16:9) puts the track, the scene and `fov_px` in square pixels first.

    `fields` ([(first, last, deg)], the field across `fov_px` stretch by stretch as the display gives it) puts
    the scale's changes in from the display (`field_steps`); the object's own size steps near one of them are
    that change, and the others are judged as without fields. The angular scale is then the field's at the
    track's first frame, an assumption unless `scale_err` says otherwise.

    `zoom` (`mcdonald zoom`'s fields) puts in the scale's changes the imagery measured (`imaged_steps`), where no
    `fields` are given, and its bursts with no measured step as the camera's events (`burst_events`).

    `record` ({frame: zoom}, the phone's own record of its zoom: `mcdonald phone`) puts in the zoom on every frame, where
    no `fields` are given: checked first on the object's size (`record_check`, or `checked` where the caller has done
    it), and taken out of the track (`record_steps`) unless the pictures disagree with it; the stretches where it moves
    are the camera's events. The angular scale is then `k_record` ((k px/rad at the track's first frame, how, the share
    it may be off by): `phone.k_at`'s) where no field of view or graticule is given."""
    W, H = clip.W, clip.H
    if not track:
        return Found("camera", no_power=[("camera", "no track, so nothing to measure the camera against")])
    shp = shapes(clip, track, size, dark, mask)
    fsteps, outside = [], []
    rcheck, rsteps = None, []
    if record and not fields:
        rcheck = checked if checked is not None else record_check(record, shp, H, blur_px)
        rsteps = record_steps(record, track, rcheck)
    usable = rcheck is not None and rcheck["verdict"] != "disagrees"   # the record says the zoom on every tracked frame
    used = usable and bool(rsteps)                                       # and it moves: taken out of the track
    imaged = imaged_steps(zoom, track, shp, W, H, blur_px, centre) if zoom and not fields and not usable else []
    if fields:
        fields = sorted((int(a), int(b), float(d)) for a, b, d in fields)
        fsteps = field_steps(fields, track, shp, W, H, blur_px=blur_px, centre=centre)
        outside = [n for n in track if field_at(n, fields) is None]
        own = [z for z in zoom_steps(track, shp, W, H)
               if not any(abs(z["frame"] - f["frame"]) <= EVENT_NEAR for f in fsteps)]
        steps = sorted(fsteps + own, key=lambda z: z["frame"])
        fov = field_at(min(n for n in track if field_at(n, fields) is not None), fields) if len(outside) < len(track) else fov
    elif usable:                                   # the zoom on every frame is known: a size step is the object's own
        steps = rsteps
    elif imaged:
        fsteps = imaged
        own = [z for z in zoom_steps(track, shp, W, H)
               if not any(abs(z["frame"] - f["frame"]) <= EVENT_NEAR for f in fsteps)]
        steps = sorted(fsteps + own, key=lambda z: z["frame"])
    else:
        steps = zoom_steps(track, shp, W, H, ratios=ratios)
    if zoom and not usable:
        events = list(events or ()) + burst_events(zoom, min(track), max(track))
    if record and not fields:                      # where the record's zoom moves, its start and its end: the camera's events
        for a, b in record_runs(record):
            if b >= min(track) and a <= max(track):
                # short, as the figure names each event down from the top beside its line (the line gives the frame;
                # the stage says the record is the phone's): "the phone's zoom settles (6 at frame 55, its record)"
                # ran down over the object's points
                events = list(events or ()) + [(a + 1, f"zoom moves from {record[a + 1]:.3g}x"),
                                               (b, f"zoom at {record[b]:.3g}x")]
    one = to_one_scale(track, steps, W, H)
    a = float(pixel_aspect or 1.0)
    if a != 1.0:
        one = {n: (x / a, y) for n, (x, y) in one.items()}
    zs = zooms(steps)
    evs = sorted([(s["frame"], f"the field {s['deg_before']:g} -> {s['deg_after']:g} deg" if s["ratio_from"] == "field"
                   else f"the picture zooms x{s['ratio']:.2f}") for s in zs if s["ratio_from"] != "record"] + list(events or ()))
    k, k_from, err = angular(W / a, fov, fov_px / a if fov_px else None, graticule, bool(fields))
    if k is None and k_record and not (rcheck and rcheck["verdict"] == "disagrees"):
        k, k_from, err = k_record[0] * math.pi / 180.0, k_record[1], k_record[2]
    scale_err = err if scale_err is None else scale_err
    picture, sig = rate_steps(one, clip.fps)
    in_degrees(picture, k)
    before, scene_said, ground, off_path = None, None, None, 0
    if scene:
        sc = dict(scene, X=scene["X"] / a, Y=scene["Y"]) if a != 1.0 else scene
        ground, on, off_path = relative_to_scene(one, sc, after)
        stretches, sig = rate_steps(ground, clip.fps) if len(ground) >= 2 * MIN_SEG else ([], sig)
        in_degrees(stretches, k)
        later = None
        if after is not None and ground:
            before = camera_before(sc, min(ground), after, clip.fps, stretch=on)
            later = camera_before(sc, after, max(ground), clip.fps, stretch=on)
            for r in (before, later):
                if r and k:
                    r["deg_per_s"], r["err_deg_per_s"] = r["v_px_per_s"] / k, r["err_px_per_s"] / k
        scene_said = dict(path=scene.get("path"), k=scene["k"], stretch=on, frames_off_path=off_path, before=before,
                          after=later, frames_on_path=len(ground))
    else:
        stretches = picture
    breaks = at_events(stretches, evs)
    dep = None
    if scene and before and k:
        dep = departure(ground, after, clip.fps, breaks, size=size)
        wander_errors(ground, stretches, clip.fps, after, dep)       # B16: the departure's own wander in each rate's error
        in_degrees(stretches, k)
        if dep:
            dep["deg_per_s"], dep["err_deg_per_s"] = dep["v_px_per_s"] / k, dep["err_px_per_s"] / k
            if "err_wander_px_per_s" in dep:
                dep["err_wander_deg_per_s"] = dep["err_wander_px_per_s"] / k
        scene_said["departure"] = dep
        # both rates go through one k, so the scale cancels in the comparison; a scene that drifted slower than
        # BEFORE_MIN, or not clearly at all, gives the camera's turn no heading to set the object's against
        turned = before["v_px_per_s"] >= BEFORE_MIN and before["v_px_per_s"] > 3 * before["err_px_per_s"]
        before["turned"] = bool(turned)
        rel = released(stretches, before["deg_per_s"], before["err_deg_per_s"], after, 0.0,
                       heading_deg=before["direction_deg"] if turned else None, against="the ground", whole=dep)
    else:
        rel = None
        if k and los_rate and not scene:
            wander_errors(one, stretches, clip.fps, after)              # B16
            in_degrees(stretches, k)
            rel = released(stretches, los_rate, los_err, after, scale_err or 0.0)
    res, npw, needs, notes = {}, [], [], []
    if scene:
        notes.append(f"The track is taken relative to the scene's path ({scene_said['frames_on_path']} frames on its stretch "
                     f"{on}" + (f", {off_path} off it" if off_path else "") + "), so the rates below are the object's against "
                     "the ground, with the camera's own motion out of them (`--scene`).")
    if rcheck is not None:
        z = [record[n] for n in track if n in record]
        res["phone's record"] = (
            (f"the zoom on every frame, from {min(z):.3g} to {max(z):.3g} over the track, "
             + ("taken out of it (the rates are in the first frame's scale)" if used else
                "holding on every tracked frame" if not rsteps else "NOT used")
             if z else "no zoom on the tracked frames")
            + f"; the pictures' check: {rcheck['verdict']}, {rcheck['why']}")
        if rcheck["verdict"] == "disagrees":
            npw.append(("phone's record", f"{rcheck['why']}: the record is not this clip's zoom, and is not used"))
        elif used:
            notes.append(f"The picture zooms inside the track as the phone's own record says ({len(rsteps)} frames where the "
                         "zoom changes); the rates are in the first frame's scale."
                         + ("" if rcheck["verdict"] == "agrees" else f" The pictures could not check the record: {rcheck['why']}."))
    isteps = [s for s in fsteps if s["ratio_from"] == "imagery"]
    fsteps = [s for s in fsteps if s["ratio_from"] == "field"]
    if isteps:
        res["zoom steps"] = "; ".join(
            f"frame {s['frame']}: x{s['ratio']:.3f} measured from the picture across "
            + ("its blank frames" if s["kind"] == "blank" else "a step with no blank")
            + f" {s['burst'][0]}-{s['burst'][1]} (`mcdonald zoom`), the object's size {s['size_check']}"
            + (f" ({s['size_why']})" if s.get("size_why") else "") for s in isteps)
        notes.append(f"The picture zooms {len(isteps)} time{'s' if len(isteps) != 1 else ''} inside the track, as "
                     "`mcdonald zoom` measured it from the picture; the rates are in the first frame's scale.")
    if fsteps:
        res["fields"] = "; ".join(
            f"frame {s['frame']}: {s['deg_before']:g} -> {s['deg_after']:g} deg (x{s['ratio']:.2f}), the object's size "
            f"{s['size_check']}" + (f" ({s['size_why']})" if s.get("size_why") else "") for s in fsteps)
        weak = [s for s in fsteps if s["size_check"] in ("no power", "unclear")]
        bad = [s for s in fsteps if s["size_check"] == "contradicts"]
        notes.append(f"The field changes {len(fsteps)} time{'s' if len(fsteps) != 1 else ''} inside the track, as the "
                     "display gives it; the rates are in the first frame's scale."
                     + (f" At {', '.join(str(s['frame']) for s in weak)} the object cannot check the change: the "
                        "display's field is all there is to go on there." if weak else "")
                     + (f" At {', '.join(str(s['frame']) for s in bad)} the object's size contradicts it: look again at "
                        "the readout, and at which frame the picture itself changes (it can lead its symbology by "
                        "frames)." if bad else ""))
        if outside:
            needs.append(f"the field on {len(outside)} tracked frame{'s' if len(outside) != 1 else ''} outside every "
                         f"stretch of --fields (first {min(outside)}): they are taken at the scale before them")
    zs_own = [z for z in zs if z["ratio_from"] not in ("field", "imagery", "record")]
    if zs_own:
        res["zoom steps"] = "; ".join(
            f"frame {s['frame']}: x{s['ratio']:.2f} ({s['ratio_from']}; the size's x{s['ratio_from_size']:.2f}"
            + (f", the offset's about the frame's centre x{s['ratio_from_offset']:.2f}" if s["ratio_from_offset"] else "")
            + f"; {s['size_before_px']:.1f} -> {s['size_after_px']:.1f} px)"
            + (f", centre ({s['centre'][0]:.1f}, {s['centre'][1]:.1f}) from a {s['jump_px']:.0f} px jump"
               if s["centre"] else ", the object at the zoom's centre: its position cannot place it")
            for s in zs_own)
        notes.append("The picture zooms inside the track (" + ", ".join(f"x{s['ratio']:.2f} at frame {s['frame']}"
                                                                     for s in zs_own)
                     + "): a rate in pixels across a zoom mixes two scales. The camera stage's rates are in the "
                       "first frame's scale.")
    elif not fsteps and not isteps and not used:
        res["zoom steps"] = "none: no step in the object's size" if not steps else "none that its position confirms"
    trend = size_trend(shp, steps)
    if trend:
        res["size trend"] = size_said(trend)
    own = [s for s in steps if not s["applied"] and s["ratio_from"] != "record"]
    if own:
        res["size steps"] = (f"{len(own)}, not taken as zooms: " + "; ".join(
            f"frame {s['frame']} x{s['ratio_from_size']:.2f} ({s['why_not']})" for s in own[:4])
            + (f"; and {len(own) - 4} more" if len(own) > 4 else "")
            + ". Where the sensor says it zoomed there, give the ratio (--zoom-ratio)")
    where = "first-frame scale" + (", relative to the scene" if scene else "") + (", square px" if a != 1.0 else "")
    if stretches:
        jumps = [b for b in breaks if b["jump"]]
        if len(stretches) <= BRIEF:
            res["rate steps"] = "; ".join(
                f"{s['frames'][0]}-{s['frames'][1]} {s['v_px_per_s']:.1f} +- {s['err_px_per_s']:.1f} px/s"
                for s in stretches) + f" ({where}; noise {sig:.2f} px)"
        else:
            v = [s["v_px_per_s"] for s in stretches]
            res["rate steps"] = (f"{len(stretches)} stretches, {min(v):.0f} to {max(v):.0f} px/s ({where}; noise "
                                 f"{sig:.2f} px), each in the camera CSV: a rate that changes smoothly, as a panning "
                                 "camera's does, is cut into many")
        if jumps:
            res["jumps"] = (f"the track jumps at {len(jumps)} of its {len(breaks)} breaks: " + ", ".join(
                f"{b['frame']} ({b['jump_px']:.1f} px)" for b in jumps[:6]) + (" ..." if len(jumps) > 6 else "")
                + " -- the track's or the picture's (a tracker on another feature, a frame dropped or repeated, a cut), "
                  "not the object's rate")
        at = [b for b in breaks if b["at_event"]]
        if breaks and not evs:
            res["at camera events"] = (f"no camera event is known to set its {len(breaks)} rate steps beside (none found "
                                       "in the track, none given: `mcdonald camera --events`)")
        elif breaks:
            res["at camera events"] = (f"{len(at)} of {len(breaks)} rate steps: " + ", ".join(
                f"{b['frame']} ({b['event']['what']}, {b['frames_from_event']:+d})" for b in at) if at else
                f"none of {len(breaks)} rate steps is within {EVENT_NEAR} frames of a camera event")
            if at:
                notes.append(f"{len(at)} of the track's {len(breaks)} rate steps fall within {EVENT_NEAR} frames of the "
                             "camera's own events: those are the camera's until shown otherwise.")
    else:
        npw.append(("rate steps", f"under {2 * MIN_SEG} tracked frames, so no stretch to fit a rate on"))
    if scene and before:
        res["camera before"] = (f"frames {before['frames'][0]}-{before['frames'][1]}: the scene drifts through the picture at "
                                f"{before['v_px_per_s']:.1f} +- {before['err_px_per_s']:.1f} px/s"
                                + (f" = {before['deg_per_s']:.4g} +- {before['err_deg_per_s']:.2g} deg/s" if k else "")
                                + (f", heading {before['direction_deg']:.0f} deg: the rate the camera turned against the "
                                   "ground while it held the object" if before.get("turned") else
                                   f": under {BEFORE_MIN:g} px/s, so the camera was not turning against the ground while it "
                                   "held the object"))
    if scene and scene_said.get("after"):
        l = scene_said["after"]
        res["camera after"] = (f"frames {l['frames'][0]}-{l['frames'][1]}: the scene drifts through the picture at "
                               f"{l['v_px_per_s']:.1f} +- {l['err_px_per_s']:.1f} px/s"
                               + (f" = {l['deg_per_s']:.4g} +- {l['err_deg_per_s']:.2g} deg/s" if k else "")
                               + ": the camera's rate against the ground after the release (the track's rates have it "
                               "taken out)")
    if rel:
        res["released track"] = rel["said"]
    elif scene and after is None:
        needs.append("the frame the camera let the object go (--after) for the released-track null against the scene")
    elif scene and not ground:
        npw.append(("released track", "no tracked frame is on the scene's path: the layers CSV covers other frames, "
                                      "or none of its pairs reached a consensus there"))
    elif scene and not before:
        npw.append(("released track", f"the scene's path does not cover {MIN_SEG} tracked frames before {after} in one "
                                      "stretch, so the camera's rate before is not measured"))
    elif scene and not k:
        needs.append("an angular scale for the released-track null: --fov (with --fov-px if the field of view spans "
                     "less than the frame) or --graticule")
    elif los_rate and not k:
        needs.append("an angular scale for the released-track null: --fov (with --fov-px if the field of view spans "
                     "less than the frame) or --graticule")
    elif k and not los_rate:
        needs.append("the camera's rate before the object left (--los-rate, deg/s; `mcdonald readout` times a "
                     "readout's ticks into one; or --scene, a `layers` CSV, where the ground is in the picture) for "
                     "the released-track null")
    given = fields
    fields = dict(zoom_steps=steps, stretches=stretches, noise_px=sig, breaks=breaks, events=[dict(frame=e[0], what=e[1])
                                                                                               for e in evs],
                  k_px_per_deg=k, k_from=k_from if k else None, released=rel, frames_measured=len(shp),
                  fields_given=[list(f) for f in given] if given else None, pixel_aspect=a,
                  scene=scene_said, picture_stretches=picture if scene else None, size_trend=trend)
    if rcheck is not None:                         # only where a record was given: any other case's fields are as they were
        fields["record"] = dict(check=rcheck, used=bool(used), steps=len(rsteps),
                                zoom=[float(min(record[n] for n in track if n in record)),
                                      float(max(record[n] for n in track if n in record))]
                                if any(n in record for n in track) else None)
    files = []
    if out:
        files = write(out, tag, track, shp, one, stretches, steps, evs, rel, clip.fps, k, ground=ground)
    return Found("camera", res, fields, no_power=npw, needs=needs, files=files, notes=notes)


def angular(width, fov=None, fov_px=None, graticule=None, from_fields=False):
    """The camera stage's angular scale: (k px/deg, what it came from, the share it may be off by), or (None, None, 0)
    with neither a graticule nor a field of view. A graticule is a measurement; a field of view an assumption,
    `from_fields` where it is the field the display gives at the track's first frame."""
    if graticule:
        return float(graticule), f"a graticule, {graticule:g} px per degree", 0.0
    if fov:
        k = kin.AngularScale.from_fov(fov_px or width, fov).k * math.pi / 180.0
        return k, (f"the fields given, {fov:g} deg over {fov_px or width:g} px at the track's first frame (ASSUMED: "
                   "a display's fields are its maker's numbers)" if from_fields else
                   f"an ASSUMED field of view of {fov:g} deg over {fov_px or width:g} px"), SCALE_ERR
    return None, None, 0.0


def in_degrees(stretches, k):
    """Each stretch's rate in deg/s at k px/deg, or none where there is no k (and its error with the wander in it,
    `wander_errors`, where it has one)."""
    for st in stretches:
        if k:
            st["deg_per_s"], st["err_deg_per_s"] = st["v_px_per_s"] / k, st["err_px_per_s"] / k
            if "err_wander_px_per_s" in st:
                st["err_wander_deg_per_s"] = st["err_wander_px_per_s"] / k
        else:
            st.pop("deg_per_s", None), st.pop("err_deg_per_s", None), st.pop("err_wander_deg_per_s", None)


def wander_errors(track, stretches, fps, after=None, whole=None):
    """B16 (the biology survey's Part 5 §4, 2026-11-01): each stretch's rate error with the track's own wander in it. The
    released-track null takes a stretch's error from its residuals as if they were white; a real track wanders, seconds
    long, and on tracks drawn with a recorded track's own wander and no departure at all the fastest stretch beat the
    camera's rate 97 % of the time and the whole departure 74 % (white jitter: 2 %). So the departure's covariance is
    fitted as the speed band fits a track's (`kinematics.speed_band`, on the frames from `after` on), and each straight
    line's slope gets its error under it -- the line's weights through the fitted covariance, c' K c -- the larger of that
    and the white one kept as `err_wander_px_per_s` on each stretch (and on `whole`, the departure as a whole). Returns
    the band's covariance (`breaks.thetas_of`), or None where no band could be fitted (fewer than its 10 points): then
    nothing is set."""
    from . import breaks
    part = {n: v for n, v in track.items() if after is None or n >= after}
    try:
        got = kin.speed_band(part, fps)
    except Exception:                            # noqa: BLE001 -- the white errors stand where no covariance will fit
        return None
    if not got:
        return None
    th = breaks.thetas_of(got[0])
    for st in list(stretches) + ([whole] if whole else []):
        fr = np.array(sorted(n for n in track if st["frames"][0] <= n <= st["frames"][1]), float)
        if len(fr) < 3:
            continue
        t = (fr - 1.0) / float(fps)
        c = (t - t.mean()) / float(((t - t.mean()) ** 2).sum())
        ex, ey = (math.sqrt(max(float(c @ breaks._cov(t, theta) @ c), 0.0)) for theta in th)
        v = math.hypot(st["vx"], st["vy"])
        err = math.hypot(st["vx"] * ex, st["vy"] * ey) / v if v > 0 else math.hypot(ex, ey)
        st["err_wander_px_per_s"] = float(max(err, st["err_px_per_s"]))
    return th


def rescale(fields, width, fov=None, fov_px=None, graticule=None, from_fields=False, pixel_aspect=1.0, k_record=None):
    """A camera stage's fields (`measure`'s) in another angular scale, nothing measured again: what a case is given
    afterwards (`stages.add_known`, `mcdonald report CASE --fov`) changes the stretches' deg/s and nothing in pixels.
    (Where the fields came from the display, `fov` is theirs at the track's first frame, and only --fov-px changes.)
    The released-track null needs the camera's rate before, which only `mcdonald camera` is given, so a case's camera
    stage has none to work out again. `pixel_aspect` as `measure` takes it: k over the frame's width in square pixels;
    the stretches' rates in pixels were put in square pixels when they were measured, at the stretch the fields keep,
    and a different one afterwards cannot redo that (the rate's direction is gone), so `k_from` says so."""
    a = float(pixel_aspect or 1.0)
    k, k_from, _ = angular(width / a, fov, fov_px / a if fov_px else None, graticule, from_fields)
    if k is None and k_record:                     # the phone's own record of its lens and zoom (`measure`'s k_record)
        k, k_from = k_record[0] * math.pi / 180.0, k_record[1]
    was = float(fields.get("pixel_aspect") or 1.0)
    if k and a != was:
        k_from += (f" -- this step's rates in pixels were measured with the pixels taken {was:.4g} times wider than tall, not "
                   f"{a:.4g}: measure the case again (mcdonald run --pixel-aspect) for them in square pixels")
    in_degrees(fields["stretches"], k)
    fields.update(k_px_per_deg=k, k_from=k_from)
    return fields


def write(out, tag, track, shp, one, stretches, steps, evs, rel, fps, k=None, ground=None):
    """<out>_camera.csv (frame by frame; with `ground`, the track relative to the scene, `x_scene` and `y_scene` too)
    and <out>_camera.png."""
    seg = {}
    for i, s in enumerate(stretches):
        for n in range(s["frames"][0], s["frames"][1] + 1):
            seg[n] = i + 1
    path = Path(f"{out}_camera.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "x", "y", "x_first_scale", "y_first_scale", "zoom", "length_px", "width_px", "stretch"]
                   + (["x_scene", "y_scene"] if ground is not None else []))
        for n in sorted(track):
            s = shp.get(n, {})
            w.writerow([n, f"{track[n][0]:.2f}", f"{track[n][1]:.2f}", f"{one[n][0]:.2f}", f"{one[n][1]:.2f}",
                        f"{scale_at(n, steps):.3f}", f"{s['length_px']:.2f}" if s else "",
                        f"{s['width_px']:.2f}" if s else "", seg.get(n, "")]
                       + ([f"{ground[n][0]:.2f}", f"{ground[n][1]:.2f}"] if ground and n in ground else
                          ["", ""] if ground is not None else []))
    png = Path(f"{out}_camera.png")
    figure(png, tag, shp, ground if ground else one, stretches, evs, rel, fps, k, relative=bool(ground))
    return [str(path), str(png)]


def figure(path, name, shp, one, stretches, evs, rel, fps, k=None, relative=False):
    """The object's size, its path in one scale (relative to the scene where `relative`), and its rate on each
    stretch, with the camera's events. In the house style (figures.setup)."""
    from . import figures
    plt = figures.setup()
    fr = np.array(sorted(one))
    t = (fr - 1) / float(fps)
    fig, (a, b, c) = plt.subplots(3, 1, figsize=(7.5, 8.4), sharex=True, constrained_layout=True)
    sz = [n for n in fr if n in shp]
    a.plot((np.array(sz) - 1) / fps, [shp[n]["length_px"] for n in sz], "o", ms=2.5, color=figures.BLUE)
    a.set_ylabel("Length of the object\n(pixels)")
    a.set_title("What the camera did")
    x0, y0 = one[fr[0]]
    b.plot(t, [one[n][0] - x0 for n in fr], "o", ms=2.5, color=figures.BLUE, label="Across")
    b.plot(t, [one[n][1] - y0 for n in fr], "o", ms=2.5, color=figures.AMBER, label="Down")
    for s in stretches:
        tt = (np.array(s["frames"]) - 1) / fps
        c.plot(tt, [s["v_px_per_s"]] * 2, "-", lw=2.2, color=figures.BLUE, solid_capstyle="butt")
    b.set_ylabel("Position on the scene\n(pixels)" if relative else "Position, first zoom\n(pixels)")
    c.set_ylabel("Speed\n(pixels a second)")
    if rel and k:
        c.axhline(rel["los_rate_deg_s"] * k, color="0.35", lw=1.0, ls="--",
                  label="The camera's own turn, before" + (" (against the ground)" if rel.get("against") else ""))
    c.set_xlabel("Time in the video (s)")
    tops = {a: 1.0}                                   # each legend in a band over its data, the event lines stopping under it
    for ax in (b, c):
        if ax.get_legend_handles_labels()[0]:
            figures.legend_above(ax, ncol=len(ax.get_legend_handles_labels()[0]), inside_first=not evs)
            lo, hi = ax.get_ylim()
            tops[ax] = min(1.0, (max(np.nanmax(ln.get_ydata()) for ln in ax.lines) - lo) / (hi - lo) + 0.04)
        else:
            tops[ax] = 1.0
    for ax in (a, b, c):
        for n, what in evs:
            ax.axvline((n - 1) / fps, ymax=tops[ax], color="0.5", lw=0.8, ls=":")
    if evs:                                           # each event named beside its line, in a band kept clear over the data
        lo, hi = a.get_ylim()
        a.set_ylim(lo, hi + 0.45 * (hi - lo))
        for n, what in evs:
            a.annotate(what, ((n - 1) / fps, 1.0), xycoords=("data", "axes fraction"), xytext=(2, -3),
                       textcoords="offset points", rotation=90, ha="left", va="top", fontsize=8, color="0.3")
    # the ticks fixed once the ranges are: matplotlib's own count follows each panel's height, so each pass of the layout
    # changed the ticks ("19.1" / "19.075"), so their width, so the margin, and a label ran off the figure (a two-object
    # test clip); and only ticks inside the range, so that none out of sight is taken for numbers under a label
    from matplotlib.ticker import MaxNLocator
    for ax in (a, b, c):
        lo, hi = ax.get_ylim()
        ax.set_yticks([v for v in MaxNLocator(nbins=6, steps=[1, 2, 2.5, 5, 10]).tick_values(lo, hi) if lo <= v <= hi])
        ax.set_ylim(lo, hi)
    figures.save(fig, path, dpi=200)
    plt.close(fig)


def said(fields, brief=False):
    """What the command prints for a person; `brief` (the stage in `run`) sums up a long list of stretches."""
    L = []
    for s in fields["zoom_steps"]:
        if s["ratio_from"] == "field":
            L.append(f"the field changes {s['deg_before']:g} -> {s['deg_after']:g} deg at frame {s['frame']} (x{s['ratio']:.2f}, "
                     f"as the display gives it): the object's size {s['size_check']}, {s['size_why']}")
        elif s["ratio_from"] == "imagery":
            L.append(f"the picture zooms x{s['ratio']:.3f} at frame {s['frame']}, measured from the picture across "
                     + ("its blank frames" if s.get("kind", "blank") == "blank" else "a step with no blank")
                     + f" {s['burst'][0]}-{s['burst'][1]} (`mcdonald zoom`): the object's size {s['size_check']}, "
                     f"{s['size_why']}")
    rec = fields.get("record")
    if rec:
        L.append("the phone's record of its zoom: " + ((f"from {rec['zoom'][0]:.3g} to {rec['zoom'][1]:.3g} over the track, "
                                                        + ("taken out of it" if rec["used"] else "holding" if not rec["steps"]
                                                           else "NOT used")) if rec["zoom"] else "none on the tracked frames")
                 + f"; checked on the object's size: {rec['check']['verdict']}, {rec['check']['why']}")
    for s in [z for z in zooms(fields["zoom_steps"]) if z["ratio_from"] not in ("field", "imagery", "record")]:
        L.append(f"the picture zooms x{s['ratio']:.2f} at frame {s['frame']} ({s['ratio_from']}; the object "
                 f"{s['size_before_px']:.1f} -> {s['size_after_px']:.1f} px long, x{s['ratio_from_size']:.2f}"
                 + (f"; its offset about the frame's centre x{s['ratio_from_offset']:.2f}" if s["ratio_from_offset"] else "")
                 + ")"
                 + (f", about ({s['centre'][0]:.1f}, {s['centre'][1]:.1f}), solved from its {s['jump_px']:.1f} px jump"
                    if s["centre"] else "; the object sits at its centre, so its position cannot place it"))
    if not zooms(fields["zoom_steps"]):
        L.append("no zoom step inside the track")
    elif not any(z["ratio_from"] != "field" for z in zooms(fields["zoom_steps"])) and not fields.get("fields_given"):
        L.append("no zoom step inside the track")
    for e in fields.get("events", []):
        if e["what"].startswith("blank frames "):
            L.append(f"{e['what']} (frame {e['frame']}, `mcdonald zoom`)")
    for s in fields["zoom_steps"]:
        if not s.get("applied", True) and s["ratio_from"] != "record":
            L.append(f"the object's size steps x{s['ratio_from_size']:.2f} at frame {s['frame']} ({s['size_before_px']:.1f} -> "
                     f"{s['size_after_px']:.1f} px long, its width x{s['width_ratio']:.2f}), not taken as a zoom: {s['why_not']}")
    if fields.get("size_trend"):
        L.append("size trend: " + size_said(fields["size_trend"]))
    if brief and len(fields["stretches"]) > BRIEF:
        v = [s["v_px_per_s"] for s in fields["stretches"]]
        at = sum(b["at_event"] for b in fields["breaks"])
        jumps = sum(b.get("jump", False) for b in fields["breaks"])
        L.append(f"{len(v)} stretches, {min(v):.0f} to {max(v):.0f} px/s; {at} of their {len(fields['breaks'])} steps at a "
                 f"camera event, {jumps} where the track jumps (each in the camera CSV)")
        if fields["released"]:
            L.append(fields["released"]["said"])
        return L
    sc = fields.get("scene")
    if sc:
        b = sc.get("before")
        L.append(f"the camera's own motion taken out: the track relative to the scene's path (`--scene`, {sc['frames_on_path']} "
                 f"frames on its stretch {sc['stretch']}" + (f", {sc['frames_off_path']} off it" if sc.get("frames_off_path") else "")
                 + "); the rates below are the object's against the ground"
                 + (f". Before the release (frames {b['frames'][0]}-{b['frames'][1]}) the scene drifted through the picture at "
                    f"{b['v_px_per_s']:.1f} +- {b['err_px_per_s']:.1f} px/s"
                    + (f" = {b['deg_per_s']:.4g} +- {b['err_deg_per_s']:.2g} deg/s" if "deg_per_s" in b else "")
                    + (f", heading {b['direction_deg']:.0f} deg: that is how fast the camera turned against the ground to "
                       "hold the object" if b.get("turned") else f": under {BEFORE_MIN:g} px/s, so the camera was not "
                       "turning against the ground while it held the object") if b else "")
                 + (f"; after it (frames {sc['after']['frames'][0]}-{sc['after']['frames'][1]}) at "
                    f"{sc['after']['v_px_per_s']:.1f} +- {sc['after']['err_px_per_s']:.1f} px/s" if sc.get("after") else ""))
    for s in fields["stretches"]:
        L.append(f"frames {s['frames'][0]}-{s['frames'][1]}: {s['v_px_per_s']:.1f} +- {s['err_px_per_s']:.1f} px/s"
                 + (f" = {s['deg_per_s']:.3f} +- {s['err_deg_per_s']:.3f} deg/s" if "deg_per_s" in s else "")
                 + (f", heading {s['direction_deg']:.0f} deg" if sc and "direction_deg" in s else ""))
    for b in fields["breaks"]:
        L.append(f"rate step at {b['frame']}: " + (f"at the camera's event at {b['event']['frame']} ({b['event']['what']})"
                                                    if b["at_event"] else "at no camera event")
                 + (f"; the track jumps {b['jump_px']:.1f} px there" if b.get("jump") else ""))
    if fields["released"]:
        L.append(fields["released"]["said"])
    return L


def main():
    import argparse
    from . import clip as vclip
    from . import forensics as vf
    from .report import emit, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", required=True, help="CSV with frame and x/y columns")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--workdir")
    ap.add_argument("--size", type=float, default=9.0, help="how wide the object is on the screen, px (default 9)")
    ap.add_argument("--dark", action="store_true", help="the object is darker than the scene")
    ap.add_argument("--events", metavar="N:WHAT,...|auto", help="the camera's own events, frame:what, comma separated: a "
                    "readout's change, the frame a gate vanished (`2208:gate vanishes,2238:zoom readout`); or `auto`, "
                    "found from the overlay by `mcdonald events` (its readouts' changes, the gate's, the picture's)")
    ap.add_argument("--fov", type=float, help="the field of view at the track's first frame, deg (an assumption, and said to be)")
    ap.add_argument("--fov-px", type=float, help="how many pixels that field of view spans (default: the frame's width; "
                    "less where the picture is a box inside the frame)")
    ap.add_argument("--graticule", type=float, help="px per degree, read off the camera's own scale, at the first frame's zoom")
    ap.add_argument("--los-rate", type=float, metavar="DEG_S",
                    help="how fast the camera was turning before the object left, deg/s (from `mcdonald readout`)")
    ap.add_argument("--los-err", type=float, default=0.0, help="its standard error, deg/s")
    ap.add_argument("--scene", metavar="LAYERS_CSV", help="the scene's own path, a `mcdonald layers` CSV over the same "
                    "frames: the track is taken relative to it (the camera's motion out of it), and the camera's rate "
                    "before the release is the scene's drift through the picture while the object was held, in place "
                    "of --los-rate (the ground must be in the picture)")
    ap.add_argument("--pixel-aspect", type=float, default=1.0, metavar="A", help="the width of a pixel over its height "
                    "(4/3 for a 4:3 sensor shown stretched on 16:9): positions are put in square pixels first")
    ap.add_argument("--after", type=int, help="the released-track null looks only at stretches ending after this frame")
    ap.add_argument("--zoom-ratio", metavar="R[,R...]", help="the zoom steps' own ratios where the sensor prints them "
                    "(a readout's 1.0 -> 2.0 is 2), in order; otherwise the object's size gives them")
    ap.add_argument("--fields", metavar="FIRST-LAST:DEG,...", help="the field of view across --fov-px, stretch by stretch, "
                    "as the display gives it (an ATFLIR's NAR 0.7, MFOV 3, WFOV 6 deg, halved at x2): "
                    "`1-2156:0.7,2157-2206:1.5`; frames from 1. Each change is taken out of the track as a zoom, and "
                    "checked on the object's size where it can be. In place of --fov and --zoom-ratio")
    ap.add_argument("--zoom", metavar="JSON", help="the clip's zoom states, a `mcdonald zoom` _zoom.json (default: "
                    "<out>/<tag>_zoom.json where it is there): its measured steps inside the track are taken out of it, "
                    "and its other bursts are the camera's events. Not with --fields, which gives the scale itself")
    ap.add_argument("--phone", action="store_true", help="take the zoom on every frame from the phone's own record of the "
                    "clip (an iPhone's LivePhotoInfo track, `mcdonald phone`), checked first on the object's size, and the "
                    "angular scale from its lens and zoom where no --fov or --graticule is given. Not with --fields")
    ap.add_argument("--blur", type=float, metavar="PX", help="the picture's blur, px, under which (x1.5) the object's size "
                    "cannot check a change of field (default: 4 px up to 576 rows, 5 to 800, 6 above)")
    ap.add_argument("--centre", metavar="X,Y", help="the point the picture zooms about, px (the boresight; default the "
                    "frame's centre)")
    ap.add_argument("--scale-err", type=float, help=f"the share by which the scale may be off, for the released-track "
                    f"null (default {SCALE_ERR:g} with --fov, 0 with --graticule)")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>; with --n0/--n1, the segment's own folder in it, <tag>/segment-<n0>-<n1>)")
    ap.add_argument("--json", action="store_true", help="print the measurement as JSON on stdout")
    args = ap.parse_args()
    if args.fields and (args.fov or args.zoom_ratio):
        ap.error("--fields gives the field and its changes: leave out --fov and --zoom-ratio")
    if args.fields and args.zoom:
        ap.error("--fields gives the scale's changes: leave out --zoom")
    if args.fields and args.phone:
        ap.error("--fields gives the scale's changes: leave out --phone")
    if args.scene and args.los_rate:
        ap.error("--scene gives the camera's rate before from the picture: leave out --los-rate, or the other way round")
    if args.fields:
        from .readout import parse_values
        try:
            given = parse_values(args.fields)
        except ValueError as e:
            ap.error(f"--fields: {e}")
    with said_to_stderr(args.json) as lines:
        video, tag, _ = vf.resolve(args.video)
        track = vf.read_track(args.track)
        n0, n1 = args.n0 or min(track), args.n1 or max(track)
        clip = vclip.Clip(video, args.workdir, n0, n1)
        out = vclip.out_prefix(args.out, tag, vclip.named(args.n0, args.n1, clip))
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
        track = {n: xy for n, xy in track.items() if clip.n0 <= n <= clip.n1}
        if (args.events or "").strip().lower() == "auto":
            # found over a wider window than the track's: each box's noise is judged on its own frames, and over the 66
            # of FLIR1's exit, the release among them, its zoom readout's 1.0 -> 2.0 did not stand out of it
            from . import events as overlay
            wide = vclip.Clip(video, args.workdir, max(1, clip.n0 - EVENTS_PAD), min(clip.total, clip.n1 + EVENTS_PAD))
            evs = [e for e in overlay.as_camera_events(overlay.find(wide, track, args.size).fields)
                   if clip.n0 - EVENT_NEAR <= e[0] <= clip.n1 + EVENT_NEAR]
            print(f"{len(evs)} events found in the overlay over frames {wide.n0}-{wide.n1} (`mcdonald events`)")
        else:
            evs = parse_events(args.events)
        zoom = None
        zj = Path(args.zoom) if args.zoom else Path(f"{out}_zoom.json")
        if args.zoom and not zj.exists():
            raise SystemExit(f"{zj} is not there: make it with `mcdonald zoom {args.video}`")
        if zj.exists():
            from . import zoom as zm
            zoom = zm.read(zj)
            print(f"zoom states from {zj}")
        record = k_record = None
        if args.phone:
            from . import phone
            try:
                rec = phone.read(video, clip.info)
            except phone.NoRecord as e:
                print(f"no power: the phone's record: {e}")
            else:
                record = phone.zoom_curve(rec)
                k_record = phone.k_at(rec, phone.provenance(video, clip.info, rec), clip.W, clip.H, min(track))
                print(f"the phone's record: {rec['records']} frames, zoom {rec['zoom']['least']:.3g} to {rec['zoom']['most']:.3g}")
        scene = None
        if args.scene:
            scene = read_scene(args.scene)
            on = int((scene["S"] >= 0).sum())
            print(f"the scene's path from {args.scene}: {on} of {len(scene['frames'])} frames on {int(scene['S'].max()) + 1} "
                  f"stretch{'es' if scene['S'].max() else ''} (k {scene['k']})")
        found = measure(clip, track, args.size, args.dark, fov=args.fov, fov_px=args.fov_px, graticule=args.graticule,
                        los_rate=args.los_rate, los_err=args.los_err, events=evs, after=args.after,
                        out=out, tag=tag, scale_err=args.scale_err,
                        ratios=[float(v) for v in args.zoom_ratio.split(",")] if args.zoom_ratio else None,
                        fields=given if args.fields else None, blur_px=args.blur,
                        centre=[float(v) for v in args.centre.split(",")] if args.centre else None, zoom=zoom,
                        scene=scene, pixel_aspect=args.pixel_aspect, record=record, k_record=k_record)
        print("\n".join(said(found.fields)) if found.fields else "")
        for w in found.no_power:
            print(f"no power: {w[1]}")
        for x in found.needs:
            print(f"needs: {x}")
        for f in found.files:
            print(f"wrote {f}")
    code = vclip.EXIT_NOTHING if found.no_power and not found.fields else 0
    if args.json:
        emit(found.envelope("camera", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
