"""The lens's radial term k1: a straight line in the world is straight in the picture only through a pinhole.

A wide lens bends the picture: a barrel bows straight lines away from the frame's centre, and shrinks the scale toward
its edges. The one-term radial model, the first term of the usual calibration (Brown's; OpenCV's k1; the fit of the
Dalek's FLIR Bosons, k1 -0.41 to -0.45):

    x_d - c = (x_u - c) (1 + k1 r²),    r = |x_u - c| / f,

where x_u is where a pinhole of focal length f (pixels per radian at the axis) would draw the point, x_d where the lens
draws it, c the frame's centre, and r the tangent of the angle off the axis -- so k1 is counted in units of the focal
length, and a k1 from a calibration is entered as it is. Barrel below 0, pincushion above; 0 is a pinhole. Because r is
in units of f, k1 needs f: a graticule gives it (px per degree at the axis), and a field of view F across W pixels gives
it through the lens, not through a pinhole -- the frame's edge is at an angle F/2 off the axis, so W/2 = f t (1 + k1 t²),
t = tan(F/2) (`focal_px`; 50.2° over 640 px with k1 -0.43 gives 754 px/rad, where the fit found 750-757 and a pinhole says
683). One k1 is for one focal length: a zoom's changes with it.

`undistort` is the exact inverse, so a track can be drawn back to where a pinhole would have put it (`drawn`) and held
to the projective test, which knows only pinholes; `along` is the scale the lens has along a track, for turning its rate
into an angle. The model is good up to where it folds back on itself, r² = 1 / (3 |k1|) for a barrel: a point past
what it can reach has no undistorted place, and is left out (NaN).
"""
import math
from typing import NamedTuple

import numpy as np
from scipy import optimize

# how bent a lens can be and still have the one-term model reach the frame's corner: |k1| (R / f)², R the corner's distance
# from the centre -- the fold, where the corner bends in by a third; a pincushion is held to the same number (a miss is
# offered to a lens only inside these)
REACH = 4.0 / 27.0
SEGMENTS = 20        # the stretches a track is read in for the lens's scale along it

class Lens(NamedTuple):
    """The lens a scale was read through: its radial term and its focal length, px/rad at the axis."""
    k1: float
    f: float


def fold(k1):
    """The r (tangent of the angle off the axis) at which a barrel's radial function turns back, inf for a pincushion
    or a pinhole: r (1 + k1 r²) peaks at r² = 1 / (3 |k1|)."""
    return math.sqrt(1.0 / (3.0 * -k1)) if k1 < 0 else math.inf


def focal_px(k1, fov_deg, across):
    """f, px/rad at the axis, of a lens of radial term k1 whose field of view `fov_deg` spans `across` pixels, centred:
    across / 2 = f t (1 + k1 t²), t = tan(fov / 2). ValueError where that field reaches past the model's fold."""
    t = math.tan(math.radians(fov_deg) / 2.0)
    if t >= fold(k1):
        raise ValueError(f"--lens-k1 {k1:g}: a lens with that term folds back {math.degrees(math.atan(fold(k1))):.0f} degrees off "
                         f"its axis, inside the field of view given ({fov_deg:g} degrees across)")
    return (across / 2.0) / (t * (1.0 + k1 * t * t))


def distort(p, k1, f, centre):
    """Where the lens draws points a pinhole of focal length f would put at p (n x 2, px)."""
    q = (np.asarray(p, float) - np.asarray(centre, float)) / f
    return np.asarray(centre, float) + f * q * (1.0 + k1 * np.sum(q * q, axis=-1, keepdims=True))


def undistort(p, k1, f, centre):
    """Where a pinhole of focal length f would have put points the lens drew at p (n x 2, px): r (1 + k1 r²) = r_d solved
    by Newton's method, which approaches the root from one side only (the function is monotonic and concave for a barrel,
    convex for a pincushion, up to the fold), to a billionth of a pixel. NaN for a point past what the lens can reach."""
    p, c = np.asarray(p, float), np.asarray(centre, float)
    d = (p - c) / f
    rd = np.sqrt(np.sum(d * d, axis=-1))
    r = rd.copy()
    for _ in range(60):
        step = (r * (1.0 + k1 * r * r) - rd) / (1.0 + 3.0 * k1 * r * r)
        r = r - step
        if not np.nanmax(np.abs(step), initial=0.0) * f > 1e-9:
            break
    with np.errstate(invalid="ignore", divide="ignore"):
        gain = np.where(rd > 0, r / rd, 1.0)
    if k1 < 0:
        gain = np.where(rd > (2.0 / 3.0) * fold(k1), np.nan, gain)
    return c + (p - c) * gain[..., None]


def drawn(track, k1, f, centre):
    """A track {frame: (x, y)} as a pinhole of focal length f would have drawn it: {frame: (x, y)}, NaN where it cannot
    be (past the fold; as any other point a track lost)."""
    ns = sorted(track)
    p = undistort(np.array([track[n] for n in ns], float), k1, f, centre)
    return {n: (float(x), float(y)) for n, (x, y) in zip(ns, p)}


def along(track, k1, f, centre):
    """The lens's own scale along a track, px/rad: its length in the picture over the angle the line of sight swept.
    Across a radius a barrel's scale falls away from the axis as f (1 + 3 k1 r²)(1 + r²), around it as
    f (1 + k1 r²) √(1 + r²) (which can be above f), so one number for the frame is out by as much as the lens bends:
    this is the scale that turns the track's rate in pixels into an angular rate. Read on the means of SEGMENTS stretches
    of the track, not frame to frame: a frame's step can be mostly jitter, which goes every way and would mix the two
    scales (on a drawn crossing near the frame's edge, by 2 %). f where the track has no length."""
    ns = sorted(n for n in track if np.all(np.isfinite(track[n])))
    if len(ns) < 2:
        return float(f)
    p = np.array([track[n] for n in ns], float)
    p = np.array([s.mean(axis=0) for s in np.array_split(p, min(SEGMENTS, len(p)))])
    q = (undistort(p, k1, f, centre) - np.asarray(centre, float)) / f
    keep = np.all(np.isfinite(q), axis=1)
    p, q = p[keep], q[keep]
    if len(p) < 2:
        return float(f)
    a, b = np.c_[q, np.ones(len(q))][:-1], np.c_[q, np.ones(len(q))][1:]
    swept = float(np.sum(np.arctan2(np.linalg.norm(np.cross(a, b), axis=1), np.sum(a * b, axis=1))))
    long = float(np.sum(np.hypot(*(p[1:] - p[:-1]).T)))
    return long / swept if swept > 0 else float(f)


def carried(line_band, picture_band, track, k1, f, centre):
    """The band of a track drawn back (`line_band`) with its nugget read in the picture and carried through the lens. The
    jitter lives in the picture, the same each way; drawn back it is stretched, across a radius by 1 / (1 + 3 k1 r²) and
    around it by 1 / (1 + k1 r²), so that near the frame's edge one coordinate of the drawn track can hold most of it,
    and a low reading of that coordinate's nugget then has no other beside it: M1's null, off the axis, went past 5 %
    (method section 37). The picture's two readings are pooled and carried by the stretch's mean over the track, and
    `projective.fit` takes the larger of this and its other reading, as it does of any band's. `line_band` as it is
    with no nugget in the picture's."""
    if not line_band or not (picture_band or {}).get("nugget_px"):
        return line_band
    p = np.array([v for v in track.values() if np.all(np.isfinite(v))], float)
    q = (undistort(p, k1, f, centre) - np.asarray(centre, float)) / f
    r2 = np.sum(q * q, axis=1)
    r2 = r2[np.isfinite(r2)]
    share = float(np.mean(1.0 / (1.0 + 3.0 * k1 * r2) ** 2 + 1.0 / (1.0 + k1 * r2) ** 2))     # 2 where there is no bend
    sx, sy = picture_band["nugget_px"]
    each = math.sqrt(share * (sx * sx + sy * sy) / 4.0)
    return dict(line_band, nugget_px=(each, each))


def grown(track, line):
    """How much longer a track is drawn back (`drawn`) than in the picture, its path frame to frame: what a length read
    in the picture beside it is multiplied by, on the track's new pixels. 1.0 where it has no length."""
    a = np.array([(*track[n], *line[n]) for n in sorted(track) if np.all(np.isfinite(line[n])) and np.all(np.isfinite(track[n]))], float)
    if len(a) < 2:
        return 1.0
    before, after = float(np.sum(np.hypot(*np.diff(a[:, :2], axis=0).T))), float(np.sum(np.hypot(*np.diff(a[:, 2:], axis=0).T)))
    return after / before if before > 0 else 1.0


def moved(track, line):
    """The most a track's points moved, drawn back, px."""
    d = [math.hypot(line[n][0] - track[n][0], line[n][1] - track[n][1]) for n in track]
    d = [x for x in d if math.isfinite(x)]
    return max(d) if d else 0.0


def corner_bend(kappa, width, height):
    """The share a lens of k1 / f² = `kappa` (per px²) moves the frame's corner in by (below 0) or out by: x_d / x_u - 1
    there, -0.20 for the Boson's."""
    R = math.hypot(width, height) / 2.0 * (1.0 - 1e-9)           # a hair inside: REACH's edge is the fold itself
    u = undistort(np.array([[R, 0.0]]), kappa, 1.0, (0.0, 0.0))[0, 0]
    return float(R / u - 1.0) if math.isfinite(u) and u > 0 else None


def could_be(track, fps, width, height, proj, t0=None, t1=None, n0=None, n1=None):
    """Could a lens alone account for a miss of the projective test (`proj`, its result on the track itself)? The track
    is drawn back through every radial term the model allows (REACH either side, as k1 / f², which needs no focal length;
    30 steps, the best refined), the model fitted on the drawn track and drawn forward again, so the miss is read in the
    picture, where the jitter is. Where the best comes within NUGGETS of the track's own jitter the test itself is run
    on that drawn track. Returns dict(kappa, corner (the corner's share, `corner_bend`), rms_px, fits), or None for a
    track it cannot be asked of."""
    from . import projective as pj
    if not proj or not proj.get("jitter_px"):
        return None
    frames, t, p = pj._points(track, fps, t0, t1, n0, n1)
    if len(t) < 6:
        return None
    c, span = (width / 2.0, height / 2.0), float(t[-1] - t[0])
    edge = REACH / ((width / 2.0) ** 2 + (height / 2.0) ** 2)

    def miss(kappa):
        u = undistort(p, kappa, 1.0, c)
        if not np.all(np.isfinite(u)):
            return math.inf
        o, a, _ = pj.line_of(u)
        vp, b, tz, _ = pj._fit_along((u - o) @ a, t, span)
        back = distort(o + a[None, :] * (vp + b / (tz - t))[:, None], kappa, 1.0, c)
        return float(np.sqrt(np.mean(np.sum((p - back) ** 2, axis=1))))
    grid = np.linspace(-edge, edge, 31)
    got = [miss(x) for x in grid]
    i = int(np.argmin(got))
    best = optimize.minimize_scalar(miss, bounds=(grid[max(i - 1, 0)], grid[min(i + 1, 30)]), method="bounded",
                                    options=dict(xatol=edge * 1e-3))
    kappa, rms = (float(best.x), float(best.fun)) if best.fun <= got[i] else (float(grid[i]), float(got[i]))
    out = dict(kappa=kappa, corner=corner_bend(kappa, width, height), rms_px=rms, fits=False)
    if rms <= pj.NUGGETS * proj["jitter_px"]:
        line = {int(n): (float(x), float(y)) for n, (x, y) in zip(frames, undistort(p, kappa, 1.0, c))}
        out["fits"] = pj.fit(line, fps, boot=False)["fits"] is True
    return out
