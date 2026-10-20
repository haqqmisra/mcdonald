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
  the camera held still.

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
BLUR_FLOOR = 1.5         # an image under this many blurs long cannot show a change of scale: the blur sets its size
                         # (FLIR1's NAR x2 -> MFOV x2: 15.6 px x 0.23 = 3.6 px, against a VCD copy's 4-px blur)
AGREE = math.log(1.25)   # a size ratio within 25 % of a field's change confirms it; a size held within 25 % across a
CHANGE_MIN = math.log(1.5)  # change of more than x1.5 that the object would show contradicts it
BRIEF = 6                # more stretches than this are summed up in the report, and listed in the CSV
EVENTS_PAD = 300         # frames either side of the track that `--events auto` looks for the overlay's events over
JUMP_SIGMA = 5.0         # a break where the track's two lines part by this many errors (and JUMP_MIN px) is a jump
WINDOW = 4.0             # the shape is measured in a window this many object sizes across (at least 33 px)
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
    """{frame: shape} for every tracked frame on disk."""
    out = {}
    for n in sorted(track):
        if not clip.n0 <= n <= clip.n1:
            continue
        x, y = track[n]
        s = shape(clip.grey(n), x, y, size, dark, mask)
        if s:
            out[n] = s
    return out


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
def released(stretches, los_rate_deg_s, los_err_deg_s=0.0, after=None, scale_err=0.0):
    """Is the object's departure faster than the camera had been turning?

    A camera that held the object turned at its bearing rate; once it stops following, the object crosses
    the picture at that rate and no faster. Each stretch's rate in deg/s (`deg_per_s`, in one scale, so with
    the first frame's k) -- of those ending after frame `after`, if given -- is set against the camera's rate
    before, and the fastest decides. `scale_err` is the share by which k may be off: it scales every rate of
    the object's and none of the camera's (a readout's degrees are the sensor's own), so it is part of the
    comparison's error. Within two sigma of the camera's rate or below: what a camera that stopped following
    shows, and no acceleration of the object's own is needed. Faster: the release alone does not explain it.
    `z_without_scale` is the same comparison with the scale taken as exact."""
    use = [s for s in stretches if (after is None or s["frames"][1] > after) and s["n"] >= MIN_SEG and "deg_per_s" in s]
    if not use:
        return None
    top = max(use, key=lambda s: s["deg_per_s"])
    d = top["deg_per_s"] - los_rate_deg_s
    z0 = d / max(math.hypot(top["err_deg_per_s"], los_err_deg_s or 0.0), 1e-12)
    z = d / max(math.sqrt(top["err_deg_per_s"] ** 2 + (los_err_deg_s or 0.0) ** 2
                          + (scale_err * top["deg_per_s"]) ** 2), 1e-12)
    within = bool(z <= 2.0)
    said = (f"the fastest stretch, frames {top['frames'][0]}-{top['frames'][1]}, crosses the picture at "
            f"{top['deg_per_s']:.3f} +- {top['err_deg_per_s']:.3f} deg/s"
            + (f" (and +- {100 * scale_err:.0f} % for the scale)" if scale_err else "")
            + f", against the {los_rate_deg_s:.3f}" + (f" +- {los_err_deg_s:.3f}" if los_err_deg_s else "")
            + " deg/s the camera had been turning: "
            + (f"{z:+.1f} sigma" + (f" ({z0:+.1f} with the scale exact)" if scale_err else "") + ", "
               + ("no faster than a camera that stopped following would show it, so no acceleration of the object's "
                  "own is needed" if within else
                  "faster than the camera had been turning, which the release alone does not explain")))
    return dict(fastest=dict(frames=top["frames"], deg_per_s=top["deg_per_s"], err_deg_per_s=top["err_deg_per_s"]),
                los_rate_deg_s=float(los_rate_deg_s), los_err_deg_s=float(los_err_deg_s or 0.0), scale_err=float(scale_err),
                z=float(z), z_without_scale=float(z0), within_camera_rate=within, said=said,
                stretches=[dict(frames=s["frames"], deg_per_s=s["deg_per_s"], err_deg_per_s=s["err_deg_per_s"]) for s in use])


# ---- the stage -------------------------------------------------------------------------------
def measure(clip, track, size=9.0, dark=False, mask=None, fov=None, fov_px=None, graticule=None, los_rate=None,
            los_err=0.0, events=(), after=None, out=None, tag="", ratios=None, scale_err=None, fields=None,
            blur_px=None, centre=None):
    """The camera stage: zoom steps, the track in one scale, its rate steps against the camera's events, and
    -- with an angular scale and the camera's rate before -- the released-track null. A Found.

    `fields` ([(first, last, deg)], the field across `fov_px` stretch by stretch as the display gives it) puts
    the scale's changes in from the display (`field_steps`); the object's own size steps near one of them are
    that change, and the others are judged as without fields. The angular scale is then the field's at the
    track's first frame, an assumption unless `scale_err` says otherwise."""
    W, H = clip.W, clip.H
    if not track:
        return Found("camera", no_power=[("camera", "no track, so nothing to measure the camera against")])
    shp = shapes(clip, track, size, dark, mask)
    fsteps, outside = [], []
    if fields:
        fields = sorted((int(a), int(b), float(d)) for a, b, d in fields)
        fsteps = field_steps(fields, track, shp, W, H, blur_px=blur_px, centre=centre)
        outside = [n for n in track if field_at(n, fields) is None]
        own = [z for z in zoom_steps(track, shp, W, H)
               if not any(abs(z["frame"] - f["frame"]) <= EVENT_NEAR for f in fsteps)]
        steps = sorted(fsteps + own, key=lambda z: z["frame"])
        fov = field_at(min(n for n in track if field_at(n, fields) is not None), fields) if len(outside) < len(track) else fov
    else:
        steps = zoom_steps(track, shp, W, H, ratios=ratios)
    one = to_one_scale(track, steps, W, H)
    stretches, sig = rate_steps(one, clip.fps)
    zs = zooms(steps)
    evs = sorted([(s["frame"], f"the field {s['deg_before']:g} -> {s['deg_after']:g} deg" if s["ratio_from"] == "field"
                   else f"the picture zooms x{s['ratio']:.2f}") for s in zs] + list(events or ()))
    breaks = at_events(stretches, evs)
    k = None
    if graticule:
        k = float(graticule)
        k_from = f"a graticule, {graticule:g} px per degree"
        scale_err = 0.0 if scale_err is None else scale_err
    elif fov:
        k = kin.AngularScale.from_fov(fov_px or W, fov).k * math.pi / 180.0
        k_from = (f"the fields given, {fov:g} deg over {fov_px or W:g} px at the track's first frame (ASSUMED: "
                  "a display's fields are its maker's numbers)" if fields else
                  f"an ASSUMED field of view of {fov:g} deg over {fov_px or W:g} px")
        scale_err = SCALE_ERR if scale_err is None else scale_err
    if k:
        for st in stretches:
            st["deg_per_s"], st["err_deg_per_s"] = st["v_px_per_s"] / k, st["err_px_per_s"] / k
    rel = released(stretches, los_rate, los_err, after, scale_err or 0.0) if (k and los_rate) else None
    res, npw, needs, notes = {}, [], [], []
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
    zs_own = [z for z in zs if z["ratio_from"] != "field"]
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
    elif not fsteps:
        res["zoom steps"] = ("none: the object's size holds steady through the track" if not steps else
                             "none that its position confirms")
    own = [s for s in steps if not s["applied"]]
    if own:
        res["size steps"] = (f"{len(own)}, not taken as zooms: " + "; ".join(
            f"frame {s['frame']} x{s['ratio_from_size']:.2f} ({s['why_not']})" for s in own[:4])
            + (f"; and {len(own) - 4} more" if len(own) > 4 else "")
            + ". Where the sensor says it zoomed there, give the ratio (--zoom-ratio)")
    if stretches:
        jumps = [b for b in breaks if b["jump"]]
        if len(stretches) <= BRIEF:
            res["rate steps"] = "; ".join(
                f"{s['frames'][0]}-{s['frames'][1]} {s['v_px_per_s']:.1f} +- {s['err_px_per_s']:.1f} px/s"
                for s in stretches) + f" (first-frame scale; noise {sig:.2f} px)"
        else:
            v = [s["v_px_per_s"] for s in stretches]
            res["rate steps"] = (f"{len(stretches)} stretches, {min(v):.0f} to {max(v):.0f} px/s (first-frame scale; noise "
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
    if rel:
        res["released track"] = rel["said"]
    elif los_rate and not k:
        needs.append("an angular scale for the released-track null: --fov (with --fov-px if the field of view spans "
                     "less than the frame) or --graticule")
    elif k and not los_rate:
        needs.append("the camera's rate before the object left (--los-rate, deg/s; `mcdonald readout` times a "
                     "readout's ticks into one) for the released-track null")
    given = fields
    fields = dict(zoom_steps=steps, stretches=stretches, noise_px=sig, breaks=breaks, events=[dict(frame=e[0], what=e[1])
                                                                                               for e in evs],
                  k_px_per_deg=k, k_from=k_from if k else None, released=rel, frames_measured=len(shp),
                  fields_given=[list(f) for f in given] if given else None)
    files = []
    if out:
        files = write(out, tag, track, shp, one, stretches, steps, evs, rel, clip.fps, k)
    return Found("camera", res, fields, no_power=npw, needs=needs, files=files, notes=notes)


def write(out, tag, track, shp, one, stretches, steps, evs, rel, fps, k=None):
    """<out>_camera.csv (frame by frame) and <out>_camera.png."""
    seg = {}
    for i, s in enumerate(stretches):
        for n in range(s["frames"][0], s["frames"][1] + 1):
            seg[n] = i + 1
    path = Path(f"{out}_camera.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "x", "y", "x_first_scale", "y_first_scale", "zoom", "length_px", "width_px", "stretch"])
        for n in sorted(track):
            s = shp.get(n, {})
            w.writerow([n, f"{track[n][0]:.2f}", f"{track[n][1]:.2f}", f"{one[n][0]:.2f}", f"{one[n][1]:.2f}",
                        f"{scale_at(n, steps):.3f}", f"{s['length_px']:.2f}" if s else "",
                        f"{s['width_px']:.2f}" if s else "", seg.get(n, "")])
    png = Path(f"{out}_camera.png")
    figure(png, tag, shp, one, stretches, evs, rel, fps, k)
    return [str(path), str(png)]


def figure(path, name, shp, one, stretches, evs, rel, fps, k=None):
    """The object's size, its path in one scale, and its rate on each stretch, with the camera's events."""
    from .figures import setup, save
    plt = setup(9)
    fr = np.array(sorted(one))
    t = (fr - 1) / float(fps)
    fig, (a, b, c) = plt.subplots(3, 1, figsize=(7.5, 8), sharex=True, constrained_layout=True)
    sz = [n for n in fr if n in shp]
    a.plot((np.array(sz) - 1) / fps, [shp[n]["length_px"] for n in sz], ".", ms=3, color="C0")
    a.set_ylabel("Object Length (px)", fontweight="bold")
    x0, y0 = one[fr[0]]
    b.plot(t, [one[n][0] - x0 for n in fr], ".", ms=3, color="C0", label="Across")
    b.plot(t, [one[n][1] - y0 for n in fr], ".", ms=3, color="C3", label="Down")
    for s in stretches:
        tt = (np.array(s["frames"]) - 1) / fps
        c.plot(tt, [s["v_px_per_s"]] * 2, "-", lw=2.5, color="C0")
    b.set_ylabel("Position, First-Frame Scale (px)", fontweight="bold")
    b.legend(loc="best", fontsize=7)
    c.set_ylabel("Rate On Each Stretch (px/s)", fontweight="bold")
    if rel and k:
        c.axhline(rel["los_rate_deg_s"] * k, color="0.4", lw=1.2, label="The Camera's Own Rate Before")
        c.legend(loc="best", fontsize=7)
    c.set_xlabel("Time (s)", fontweight="bold")
    for ax in (a, b, c):
        for n, what in evs:
            ax.axvline((n - 1) / fps, color="0.5", lw=0.8, ls=":")
    for n, what in evs:
        a.text((n - 1) / fps, a.get_ylim()[1], f" {what}", rotation=90, va="top", fontsize=6, color="0.35")
    fig.suptitle(f"{name}: what the camera did", fontweight="bold")
    save(fig, path, dpi=110)
    plt.close(fig)


def said(fields, brief=False):
    """What the command prints for a person; `brief` (the stage in `run`) sums up a long list of stretches."""
    L = []
    for s in fields["zoom_steps"]:
        if s["ratio_from"] == "field":
            L.append(f"the field changes {s['deg_before']:g} -> {s['deg_after']:g} deg at frame {s['frame']} (x{s['ratio']:.2f}, "
                     f"as the display gives it): the object's size {s['size_check']}, {s['size_why']}")
    for s in [z for z in zooms(fields["zoom_steps"]) if z["ratio_from"] != "field"]:
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
    for s in fields["zoom_steps"]:
        if not s.get("applied", True):
            L.append(f"the object's size steps x{s['ratio_from_size']:.2f} at frame {s['frame']} ({s['size_before_px']:.1f} -> "
                     f"{s['size_after_px']:.1f} px long, its width x{s['width_ratio']:.2f}), not taken as a zoom: {s['why_not']}")
    if brief and len(fields["stretches"]) > BRIEF:
        v = [s["v_px_per_s"] for s in fields["stretches"]]
        at = sum(b["at_event"] for b in fields["breaks"])
        jumps = sum(b.get("jump", False) for b in fields["breaks"])
        L.append(f"{len(v)} stretches, {min(v):.0f} to {max(v):.0f} px/s; {at} of their {len(fields['breaks'])} steps at a "
                 f"camera event, {jumps} where the track jumps (each in the camera CSV)")
        if fields["released"]:
            L.append(fields["released"]["said"])
        return L
    for s in fields["stretches"]:
        L.append(f"frames {s['frames'][0]}-{s['frames'][1]}: {s['v_px_per_s']:.1f} +- {s['err_px_per_s']:.1f} px/s"
                 + (f" = {s['deg_per_s']:.3f} +- {s['err_deg_per_s']:.3f} deg/s" if "deg_per_s" in s else ""))
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
    ap.add_argument("--after", type=int, help="the released-track null looks only at stretches ending after this frame")
    ap.add_argument("--zoom-ratio", metavar="R[,R...]", help="the zoom steps' own ratios where the sensor prints them "
                    "(a readout's 1.0 -> 2.0 is 2), in order; otherwise the object's size gives them")
    ap.add_argument("--fields", metavar="FIRST-LAST:DEG,...", help="the field of view across --fov-px, stretch by stretch, "
                    "as the display gives it (an ATFLIR's NAR 0.7, MFOV 3, WFOV 6 deg, halved at x2): "
                    "`1-2156:0.7,2157-2206:1.5`; frames from 1. Each change is taken out of the track as a zoom, and "
                    "checked on the object's size where it can be. In place of --fov and --zoom-ratio")
    ap.add_argument("--blur", type=float, metavar="PX", help="the picture's blur, px, under which (x1.5) the object's size "
                    "cannot check a change of field (default: 4 px up to 576 rows, 5 to 800, 6 above)")
    ap.add_argument("--centre", metavar="X,Y", help="the point the picture zooms about, px (the boresight; default the "
                    "frame's centre)")
    ap.add_argument("--scale-err", type=float, help=f"the share by which the scale may be off, for the released-track "
                    f"null (default {SCALE_ERR:g} with --fov, 0 with --graticule)")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true", help="print the measurement as JSON on stdout")
    args = ap.parse_args()
    if args.fields and (args.fov or args.zoom_ratio):
        ap.error("--fields gives the field and its changes: leave out --fov and --zoom-ratio")
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
        out = vclip.out_prefix(args.out, tag)
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
        found = measure(clip, track, args.size, args.dark, fov=args.fov, fov_px=args.fov_px, graticule=args.graticule,
                        los_rate=args.los_rate, los_err=args.los_err, events=evs, after=args.after,
                        out=out, tag=tag, scale_err=args.scale_err,
                        ratios=[float(v) for v in args.zoom_ratio.split(",")] if args.zoom_ratio else None,
                        fields=given if args.fields else None, blur_px=args.blur,
                        centre=[float(v) for v in args.centre.split(",")] if args.centre else None)
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
