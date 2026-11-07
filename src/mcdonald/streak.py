"""`mcdonald streak` — the dash a fast object draws in one frame, read as a light curve inside the frame.

  mcdonald streak VIDEO --track CSV [--json]

A thing that crosses the picture during the exposure is drawn as a dash along its path: its brightness over the
exposure laid out in space (PR43's object is one; `autolink.follow_by_motion` follows it). Read along the track's own
direction, through the track's place in each frame, the dash is a light curve whose time step is one pixel over the
track's speed -- at 900 px/s, 1.1 ms a pixel, thirty times finer than the frame rate. Two things come of it:

- **The exposure.** The dash's length at half its peak (on the profile smoothed over three blurs, so that beads do not
  cut it short) is the motion during the exposure drawn through the blur: a box that long smeared by a Gaussian is that
  long at half its peak where the box is long (its ends are the box's), and the blur's width where it is short
  (`motion_px` inverts it exactly). That motion over the track's speed is the time the shutter was open; times the frame rate, the shutter's share of the frame (a 180-degree shutter is a half). A dash
  under one blur long is no dash: the exposure is then under (the blur over the speed), and nothing else is read.
- **A flicker far above the frame rate, as a reading and not a verdict.** A light that blinks while the shutter is
  open leaves beads along the dash, spaced by its period times the speed (the insect note's "rods"; a blinking aircraft
  light's dotted trail). The profile inside the dash (its soft ends, a blur each, left out, and a straight line taken
  out of it) is searched for a period: its power at each frequency in hertz (each dash's by its own speed), summed over
  every frame's dash, over the same from the lines beside the dash (their difference, scaled to the dash line's noise),
  and the largest such ratio within the band (two cycles over the dash to beads two blurs apart) is reported with the
  chance an F ratio would give it from noise alone. **That chance is not the test's false alarm**, and the stage no
  longer calls a flicker on it: measured on steady dashes drawn with no flicker (the single-camera survey's D4 of
  2026-11-01, rebuilt 2026-11-02; the method's section 30), that F test at 1e-3 passed 7-9 % of them with no codec and,
  through x264, 29-52 % on real PURSUE frames and 80-98 % on a flat sky -- a codec flattens the lines beside a dash to
  nothing and textures the dash, so a steady dash reaches any ratio a flicker does (ratios of 60 to 1,500 on steady
  dashes through CRF 23). Nor can the null be drawn in the clip: steady dashes drawn beside the object and put through a
  second encode at the clip's bit rate come out clean (the decoded frames have lost the noise the first encoder spent
  its bits on, so the second runs at a far lower quantizer), and such a control called 91-97 % of steady dashes a
  flicker on a flat sky, whatever the band's top. So the beads are a reading -- their spacing, their rate at the
  track's speed, their power over the lines beside them -- and the stage says, as no power, that they are not told
  from the encoder's texture. A steady body leaves a flat dash with soft ends.

What it assumes, and says on every run: (1) the object moves in a straight line during one exposure, at the speed the
track gives between frames; (2) the dash is the object's and not the camera's: a camera that turns during the exposure
smears the whole scene too (the scene's own points are drawn as dashes then, and the track's speed is not the object's
across the picture); (3) the beads are the object's brightness and not the scene behind it, which the profile beside the
dash (the same line, offset across it) is taken from and subtracted.

What it cannot do: read a dash shorter than three blurs (no light curve), a flicker whose beads are closer than two
blurs (they merge), or one slower than a period over the dash's length (one bead, or none).

**The scene taken out, and the dash fitted whole** (since 2026-11-07; the single-camera survey of 2026-11-01, F11 and
F12, its Part 9 §1.1-1.2 and the rebuild's M2; the method's section 42):

- Each frame is read less the median of its six neighbours 4-6 frames away, each brought onto it by one shift
  (`propose.onto`, as `autolink.follow_by_motion` brings its own neighbours): the object has moved on in them, the scene
  has not, so the dash stands on nothing. The scene's own structure otherwise rides on the profile and ends a dash at a
  dip or stretches it over a bright patch (PR43's frames 61, 67 and 73 read 22, 3 and 6.5 px where their neighbours say
  6, 15 and 29). Where the frame less its neighbours is no quieter round the dash than the frame itself -- a flat sky
  has nothing to take out; a scene that neither held still nor moved by one shift cannot be taken out -- the frame is
  read as it is, and the stage says on which frames (`SCENE_LEFT`).
- The dash is fitted whole (`fit_dash`): a Gaussian spot drawn along a straight segment over a plane, every pixel of a
  patch round the track's point at once -- the trailed point-spread function of Vereš et al. (2012), the parametric case
  of Kotera et al.'s (2019) I = H*F + (1 - H*M)B -- for its centre, length, direction, width and flux, the amplitude and
  the plane solved exactly at each step. Its length is the motion during the exposure with the blur in the model, not
  borrowed from the scene; it is read only up to the frame's step (a dash cannot outrun it: `FIT_CAP`), and not under
  `FIT_MIN_PX`, where a round spot is not told from a short dash. Where it holds (`FIT_Z`, from a null of fits at places
  with no object) the exposure is the fitted length over the speed, said beside the half-peak reading; its centres are
  the dash's own track points (`--centres` writes them as a track, the frames named), set against the track's own by
  the projective test's T and jitter; and its flux, if the object is a steady point closing at a steady speed (flux as
  1/R^2), is a second clock on T, said beside the track's, with what it assumes and what the clip shows of it.
"""
import math

import numpy as np
from scipy import ndimage, optimize
from scipy.special import erf

from .report import Found

STEP = 0.5            # px: the profile's sampling along the dash
ACROSS = 1.0          # px either side of the line averaged across it
SIDE = 6.0            # px: the background's lines, either side of the dash
MIN_BLURS = 3.0       # a dash this many blurs long or more is read as a light curve
BLUR_ASSUMED = 2.0    # px: the blur where the scene has too few points to measure it
# The band's top: beads at least this many blurs apart. Measured 2026-11-02 (the null study in the method's section 30):
# the false peaks of steady dashes through a codec sit at the band's top edge wherever it is put (2.0-2.1 blurs with the
# top at two, 3.0-3.1 at three) and the pass rate does not change, so the top is not the mechanism and stays at two,
# where a flicker's beads still carry 0.17 of their power through the blur and a dash of six blurs has a band at all.
BEAD_BLURS = 2.0
# The chance an F ratio gives the beads' peak from noise alone, over every frequency looked at, is reported as that and
# not as the test's false alarm: steady dashes pass it at this level on 7-9 % with no codec and on 29-98 % through x264
# (the method's section 30, 2026-11-02), so no flicker is called on it. The constant names the level the study measured.
NOISE_ALONE = 1e-3
# Measured on steady dashes drawn with no flicker (the null study of 2026-11-02; 12-24 frames at 30-70 px a frame, blur
# 1.8-3.5 px, a track's dashes one test): the share that the F chance under NOISE_ALONE calls a flicker.
STEADY_PASS = {"no codec": "7 of 90", "x264 on real frames": "13-23 of 45 (CRF 18-28)", "x264 on a flat sky": "36-44 of 45"}

# ---- the scene taken out (F11) ----------------------------------------------------------------------------------
# The frames whose median is the scene under a dash: 4-6 frames away, so that the object's own dash in them is clear of
# this frame's whenever it moves a blur's width in a frame (the survey's §1.1; `follow_by_motion` uses +-1 and +-2, which
# is enough to find a peak but lets a long dash's neighbours overlap it), and six, so that a neighbour holding something
# passing (a bird, a flash) is outvoted. Under NEIGHBOURS_MIN of them in the clip's frames, the scene is left in.
NEIGHBOURS = (-6, -5, -4, 4, 5, 6)
NEIGHBOURS_MIN = 3
# Which picture a frame is read on: the frame less its neighbours wherever it is quieter round the dash than the frame
# itself with a plane taken out (its rms over a patch with the dash's own place left out), else the frame. Not a tuned
# threshold: of two pictures of the same dash, the one with less else in it. On a flat sky the two are the same and
# either reads as well (the survey's rebuild, M2: 0.68 against 0.70 px rms); on cloud and on real frames the frame less
# its neighbours reads 8 and 3.2 times better; where the scene moved in a way one shift does not bring back, the
# difference has more in it than the frame, and the frame is read as it is.
SCENE_LEFT = 1.0

# ---- the dash fitted whole (F12, F41, F51) ---------------------------------------------------------------------
FIT_MIN_PX = 4.0      # px: no length is read under it. Under 4 px of motion every reader reads 2-4 px long and a round spot
                      # is not told from a short dash by its length (the survey's drawn dashes, 3,072, §2.1): NO POWER
FIT_CAP = (1.2, 3.0)  # a dash cannot outrun the frame's step: a fitted length over 1.2 steps + 3 px has taken in something
                      # beside the dash (the survey's cap; the next dash's ghost, a neighbour, the plane's edge)
FIT_MIN_FRAMES = 3    # frames the fit must hold on for an exposure, a share, or anything said of the dash from it
# The fit holds where its flux stands this many of its own errors from none (the amplitude over its least-squares error
# from the fit's residual). Set on a null (2026-11-07, the method's section 42): the same fit started at places with no
# object, on the picture the stage reads there, over flat sky, cloud and the survey's five other drawn families with the
# dash's own range of lengths, reached at most 5.0 (99th percentile 4.5) on 1,562 places, so none reaches 6. It is a
# guard against noise, not against the scene: on real PURSUE frames less their neighbours, 36-40 % of such places reach
# it, with the neighbours brought on or not (335 and 260 places): what a scene leaves behind fits as a dash, and the fit
# is only ever started where the track says the object is.
FIT_Z = 6.0
SIG = 2.3548          # a Gaussian's width at half its peak over its sigma


def profile(grey, x, y, ux, uy, half, blur):
    """The frame along the line through (x, y) in direction (ux, uy), from -half to +half px, averaged ACROSS px either
    side of it, less the mean of the same line SIDE px to each side: (s, values, the two side lines less their mean)."""
    g = np.asarray(grey, np.float32)
    s = np.arange(-half, half + 1e-9, STEP)
    wx, wy = -uy, ux
    def along(off):
        acc = 0.0
        offs = np.arange(-ACROSS, ACROSS + 1e-9, 0.5)
        for o in offs:
            xs, ys = x + s * ux + (off + o) * wx, y + s * uy + (off + o) * wy
            acc = acc + ndimage.map_coordinates(g, [ys, xs], order=1, mode="nearest")
        return acc / len(offs)
    a, b = along(SIDE + blur), along(-SIDE - blur)
    # the null: the two side lines' difference, scaled to the dash line's noise -- the dash line less the sides' mean
    # carries 1.5 times a line's noise variance, their difference 2 times
    return s, along(0.0) - 0.5 * (a + b), (a - b) * math.sqrt(0.75)


def fine_spectrum(seg, level, nfft):
    """A stretch's power at each frequency once a straight line is taken out of it, as a share of `level` squared,
    Hann-windowed: what a flicker adds and a steady body does not."""
    seg = np.asarray(seg, float)
    t = np.arange(len(seg))
    seg = seg - np.polyval(np.polyfit(t, seg, 1), t)
    return np.abs(np.fft.rfft(seg * np.hanning(len(seg)), nfft)) ** 2 / max(level, 1e-6) ** 2


def motion_px(length, blur):
    """The motion during the exposure (px) that, drawn as a box through a Gaussian blur `blur` px wide at half its peak,
    is `length` px long at half its peak: the inverse of that width, by bisection. A long dash's half-peak ends are the
    box's own (its width the motion, not the motion and a blur: subtracting the blur read a half-frame shutter as 0.46 of
    a frame at 51 px a frame and a 2-px blur, 0.34 at 20 px and 3.5); a dash no longer than the blur is no motion seen."""
    if length <= blur:
        return 0.0
    from scipy.special import ndtr
    sig = blur / 2.3548

    def width(box):
        x = np.linspace(0.0, box / 2 + 6 * sig, 4000)
        prof = ndtr((x + box / 2) / sig) - ndtr((x - box / 2) / sig)     # falls from the middle outward
        return 2.0 * float(np.interp(prof[0] / 2, prof[::-1], x[::-1]))
    lo, hi = 0.0, float(length)
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if width(mid) < length else (lo, mid)
    return (lo + hi) / 2


def dash_length(s, v):
    """The dash's length at half its peak (px), and its ends: the run above half the peak that holds the peak."""
    if not len(v) or v.max() <= 0:
        return 0.0, None
    i = int(np.argmax(v))
    half = 0.5 * v[i]
    a = i
    while a > 0 and v[a - 1] >= half:
        a -= 1
    b = i
    while b < len(v) - 1 and v[b + 1] >= half:
        b += 1
    return float(s[b] - s[a] + STEP), (a, b)


class Scene:
    """Each frame of a clip less the median of its neighbours (NEIGHBOURS), each brought onto it by one shift where that
    fits better than none (`propose.onto`): the scene taken out, the object left. `clip` needs `grey(n)`, `n0`, `n1`;
    with `masks` and a clip that has `rgb(n)`, the burned-in graphics are left out of the shift's estimate."""

    def __init__(self, clip, masks=None):
        self.clip, self.masks = clip, masks
        self._grey, self._out = {}, {}

    def grey(self, n):
        if n not in self._grey:
            if len(self._grey) > 16:
                del self._grey[max(self._grey, key=lambda k: abs(k - n))]
            self._grey[n] = np.asarray(self.clip.grey(n), np.float32)
        return self._grey[n]

    def ok(self, n, shape):
        if self.masks is not None and hasattr(self.clip, "rgb"):
            from . import forensics as vf
            return ~vf.frame_mask(self.clip.rgb(n), self.masks, None, n)
        ok = np.ones(shape, bool)
        ok[:6, :] = ok[-6:, :] = ok[:, :6] = ok[:, -6:] = False
        return ok

    def out(self, n):
        """(frame n less the median of its neighbours, [their shifts]) or (None, []) under NEIGHBOURS_MIN of them."""
        if n not in self._out:
            from . import propose
            g = self.grey(n)
            ok = self.ok(n, g.shape)
            others, shifts = [], []
            for d in NEIGHBOURS:
                m = n + d
                if self.clip.n0 <= m <= self.clip.n1:
                    moved, sh = propose.onto(g, self.grey(m), ok)
                    others.append(moved)
                    shifts.append((float(sh[0]), float(sh[1])))
            self._out[n] = (g - np.median(np.stack(others), 0), shifts) if len(others) >= NEIGHBOURS_MIN else (None, shifts)
            for k in [k for k in self._out if abs(k - n) > 8]:
                del self._out[k]
        return self._out[n]


def _patch(img, x, y, R, crop=False):
    """The (2R+1)-px square of img centred on the pixel nearest (x, y), and its corner; None where it leaves the picture
    -- or, with `crop`, the part of it inside the picture, None where that is under half of it."""
    x0, y0 = int(round(x)), int(round(y))
    a, b, c, d = x0 - R, y0 - R, x0 + R + 1, y0 + R + 1
    if a < 0 or b < 0 or c > img.shape[1] or d > img.shape[0]:
        if not crop:
            return None
        a, b, c, d = max(a, 0), max(b, 0), min(c, img.shape[1]), min(d, img.shape[0])
        if (c - a) * (d - b) < 0.5 * (2 * R + 1) ** 2 or not (a <= x0 < c and b <= y0 < d):
            return None
    return np.asarray(img[b:d, a:c], float), (a, b)


def _off_dash(shape, x, y, corner, ux, uy, half, blur):
    """The patch's pixels farther than a blur and 2 px from the segment the dash may lie on: (x, y) +- `half` along (ux, uy)."""
    Y, X = np.mgrid[0:shape[0], 0:shape[1]].astype(float)
    dx, dy = X + corner[0] - x, Y + corner[1] - y
    u = np.clip(dx * ux + dy * uy, -half, half)
    return np.hypot(dx - u * ux, dy - u * uy) > blur + 2.0


def quieter(raw, out, x, y, ux, uy, step, blur):
    """(take the scene out?, rms of the frame less its neighbours, rms of the frame): each over the patch the fit reads
    (the part inside the picture), with the dash's possible place left out and a plane taken from the frame -- the one
    with less else in it is read."""
    R = int(0.6 * step + 3 * blur + 5)
    a, b = _patch(raw, x, y, R, crop=True), _patch(out, x, y, R, crop=True) if out is not None else None
    if a is None or b is None:
        return False, None, None
    keep = _off_dash(a[0].shape, x, y, a[1], ux, uy, 0.75 * step + blur, blur)
    Y, X = np.mgrid[0:a[0].shape[0], 0:a[0].shape[1]].astype(float)
    A = np.c_[np.ones(keep.sum()), X[keep], Y[keep]]
    r_raw = a[0][keep] - A @ np.linalg.lstsq(A, a[0][keep], rcond=None)[0]
    r_out = b[0][keep] - float(np.median(b[0][keep]))
    s_raw, s_out = float(np.sqrt(np.mean(r_raw ** 2))), float(np.sqrt(np.mean(r_out ** 2)))
    return s_out < SCENE_LEFT * s_raw, s_out, s_raw


def trail(X, Y, cx, cy, L, phi, s):
    """The trailed point-spread function (Vereš et al. 2012): a Gaussian of sigma s drawn evenly along a segment of length
    L through (cx, cy) at angle phi; its integral over the plane is L sqrt(2 pi) s, its height 1 in a long dash's middle."""
    c, sn = math.cos(phi), math.sin(phi)
    dx, dy = X - cx, Y - cy
    u, w = dx * c + dy * sn, -dx * sn + dy * c
    r = math.sqrt(2.0) * s
    return 0.5 * (erf((u + L / 2) / r) - erf((u - L / 2) / r)) * np.exp(-0.5 * (w / s) ** 2)


def fit_dash(img, x, y, ux, uy, step, blur, L0=None):
    """The dash round the track's point (x, y), moving (ux, uy) at `step` px a frame, fitted whole: a trail (`trail`)
    times an amplitude over a plane, by least squares over every pixel of a patch 0.6 steps and three blurs and 5 px in
    radius, the amplitude and the plane solved exactly at each step and the centre, length, direction and width searched
    (from L0, half and one and a half times it, with the blur's width and the track's direction to start). Returns
    dict(x, y, length_px, angle_off_deg (the dash's axis against the track's direction), width_px (at half its peak), amp,
    flux (its integral), z (the amplitude over its error), rms) or None where under half the patch is in the picture."""
    R = int(0.6 * step + 3 * blur + 5)
    got = _patch(img, x, y, R, crop=True)                 # at the picture's edge, the part inside it
    if got is None:
        return None
    P, (x0, y0) = got
    xc, yc = int(round(x)), int(round(y))                  # the coordinates' origin, as for a whole patch
    Y, X = np.mgrid[0:P.shape[0], 0:P.shape[1]].astype(float)
    Xc, Yc = (X + x0 - xc).ravel(), (Y + y0 - yc).ravel()
    p = P.ravel()
    ones = np.ones_like(p)

    def design(th):
        cx, cy, L, phi, s = th
        return np.c_[trail(Xc, Yc, cx, cy, abs(L), phi, s), ones, Xc, Yc]

    def resid(th):
        D = design(th)
        return p - D @ np.linalg.lstsq(D, p, rcond=None)[0]
    phi0 = math.atan2(uy, ux)
    s0 = max(blur / SIG, 0.6)
    L0 = max(float(L0 if L0 is not None else 0.5 * step), 1.0)
    start = (x - xc, y - yc)
    best = None
    for L_ in (L0, max(0.5 * L0, 1.0), 1.5 * L0 + 2):
        try:
            r = optimize.least_squares(resid, [start[0], start[1], L_, phi0, s0],
                                       bounds=([-R, -R, 0.0, phi0 - math.pi, 0.5], [R, R, 3.0 * R, phi0 + math.pi, R / 4]),
                                       x_scale=[1, 1, 3, 0.3, 0.5], max_nfev=60, xtol=1e-3, ftol=1e-5)
        except ValueError:
            continue
        if best is None or r.cost < best.cost:
            best = r
    if best is None:
        return None
    cx, cy, L, phi, s = best.x
    L = abs(float(L))
    D = design(best.x)
    coef, *_ = np.linalg.lstsq(D, p, rcond=None)
    e = p - D @ coef
    dof = max(len(p) - 9, 1)
    s2 = float(e @ e) / dof
    try:
        var_a = float(np.linalg.inv(D.T @ D)[0, 0]) * s2
    except np.linalg.LinAlgError:
        var_a = float("inf")
    amp = float(coef[0])
    off = math.degrees((phi - phi0 + math.pi / 2) % math.pi - math.pi / 2)
    return dict(x=float(xc + cx), y=float(yc + cy), length_px=L, angle_off_deg=float(off), width_px=float(SIG * s),
                amp=amp, flux=float(amp * L * math.sqrt(2 * math.pi) * s), z=float(amp / math.sqrt(var_a)) if var_a > 0 else 0.0,
                rms=float(math.sqrt(s2)))


def fit_holds(f, step):
    """Why the fit does not hold on a frame, or None where it does: its flux stands FIT_Z of its errors from none, it is
    a bright dash on the picture (a dark one is fitted with its sign: `amp` negative fails), and its length is within
    the frame's step (FIT_CAP)."""
    if f is None:
        return "the dash is at the picture's edge"
    if f["z"] < FIT_Z:
        return f"its flux is {f['z']:.1f} of its errors from none, under {FIT_Z:g}"
    cap = FIT_CAP[0] * step + FIT_CAP[1]
    if f["length_px"] > cap:
        return f"its length, {f['length_px']:.0f} px, is longer than the frame's step allows ({cap:.0f})"
    return None


def read(clip, track, blur_px, nfft=256, scene=None, fit=True):
    """The dashes along a track: per frame its speed, length at half its peak and peak, the picture it was read on, and
    the whole dash fitted (rows); and for each dash long enough to read, its profile's power at each frequency and the
    null line's, with its speed and its span in samples (spectra). The frames' step is the track's own, centred
    (`np.gradient`). With `scene` (a `Scene`), each frame is read less its neighbours where that is quieter round the dash."""
    fr = sorted(track)
    xs, ys = np.array([track[n][0] for n in fr]), np.array([track[n][1] for n in fr])
    vx, vy = np.gradient(xs, fr), np.gradient(ys, fr)            # px a frame, centred
    rows, spectra = [], []
    for i, n in enumerate(fr):
        sp = math.hypot(vx[i], vy[i])
        if sp < 0.5:
            continue
        ux, uy = vx[i] / sp, vy[i] / sp
        half = 1.5 * sp + 4 * blur_px
        g = np.asarray(clip.grey(n), np.float32) if scene is None else scene.grey(n)
        picture, how = g, "frame"
        if scene is not None:
            out, shifts = scene.out(n)
            take, s_out, s_raw = quieter(g, out, xs[i], ys[i], ux, uy, sp, blur_px)
            if take:
                picture = out
                how = "less its neighbours" + (", brought onto it" if any(abs(a) + abs(b) > 0 for a, b in shifts) else "")
            else:
                how = ("frame: under three neighbours" if out is None else "frame: at the picture's edge" if s_raw is None else
                       f"frame: no quieter less its neighbours ({s_out:.1f} against {s_raw:.1f})")
        s, v, null = profile(picture, xs[i], ys[i], ux, uy, half, blur_px)
        # the dash's extent from the profile smoothed over three blurs: beads deep enough to dip under half the peak
        # would end the run at the first trough, and the half-peak ends of a long dash do not move under a symmetric
        # smoothing; a dash shorter than the smoothing is measured as it is
        box = max(3, int(round(3 * blur_px / STEP)))
        L, ends = dash_length(s, ndimage.uniform_filter1d(v, box, mode="nearest"))
        if L < 1.5 * box * STEP:
            L, ends = dash_length(s, v)
        row = dict(frame=n, speed_px_per_frame=sp, length_px=L, peak=float(v.max()), read_on=how)
        if fit:
            f = fit_dash(picture, xs[i], ys[i], ux, uy, sp, blur_px, L0=max(motion_px(L, blur_px), 1.0))
            row["fit"] = f
            row["fit_holds"] = fit_holds(f, sp) is None
            row["fit_why"] = fit_holds(f, sp)
            got = _patch(g, xs[i], ys[i], int(0.6 * sp + 3 * blur_px + 5), crop=True)
            row["level"] = float(np.median(got[0])) if got is not None else None     # the scene's level there: the gain
        if ends and L >= MIN_BLURS * blur_px:
            trim = int(round(blur_px / STEP))                     # the soft ends, a blur each, left out
            a, b = ends[0] + trim, ends[1] - trim
            if b - a >= 8:
                level = float(np.mean(v[a:b + 1]))
                spectra.append((fine_spectrum(v[a:b + 1], level, nfft), fine_spectrum(null[a:b + 1], level, nfft), sp,
                                b - a + 1, n))
        rows.append(row)
    return rows, spectra


def summed(spectra, fps, hz, nfft=256):
    """The dashes' power and the null lines', summed on the frequency axis `hz` (a flicker is so many hertz, not so many
    cycles a pixel: a dash's pixel is 1/speed seconds, and dashes of different speeds put the same flicker at different
    spacings). Each dash's spectrum, at k / (nfft STEP) cycles a pixel, is read at its own speed times the frame rate
    and interpolated onto `hz`; the spectra are oversampled (nfft against dashes of 10-70 samples), so that loses nothing."""
    k = np.arange(nfft // 2 + 1)
    tot, bg = np.zeros(len(hz)), np.zeros(len(hz))
    for p_dash, p_null, sp, *_ in spectra:
        own = k / (nfft * STEP) * sp * fps
        tot += np.interp(hz, own, p_dash)
        bg += np.interp(hz, own, p_null)
    return tot, bg


def measure(clip, track, blur_px=2.0, scene=True, masks=None, fit=True):
    """The stage: per frame the dash's length and its profile, on the frame less its neighbours where that is quieter
    round the dash (`scene`; `Scene`, `quieter`), and the dash fitted whole (`fit`; `fit_dash`); the exposure and shutter
    share, from the fit where it holds and from the half-peak length where it does not; the dash's centres as a track,
    the projective test's T on them and on the track's own points, and the flux as a second clock on T; the summed
    spectra of the profiles inside the dashes, in hertz, and their peak over the lines beside them -- a reading, with
    the chance noise alone would give it and why that is not a false alarm (NOISE_ALONE, STEADY_PASS). A Found."""
    fr = sorted(track)
    if len(fr) < 3:
        return Found("streak", no_power=[("streak", "under three tracked frames: no speed to read a dash by")])
    nfft = 256
    sc = Scene(clip, masks) if scene and hasattr(clip, "n0") else None
    rows, spectra = read(clip, track, blur_px, nfft, scene=sc, fit=fit)
    fields = dict(rows=rows, blur_px=blur_px, frames=len(fr))
    res, npw, notes = {}, [], []
    fps = getattr(clip, "fps", 30.0)
    if not rows:
        npw.append(("streak", "the track does not move: no dash"))
        return Found("streak", res, fields, no_power=npw)
    L = np.array([r["length_px"] for r in rows])
    sp = np.array([r["speed_px_per_frame"] for r in rows])
    share = np.array([motion_px(a, blur_px) for a in L]) / sp       # of a frame
    half_peak = dict(exposure_share=float(np.median(share)), exposure_s=float(np.median(share)) / fps, length_px=float(np.median(L)))
    fields.update(half_peak, half_peak=half_peak, exposure_from="the half-peak length", speed_px_per_frame=float(np.median(sp)))
    if sc is not None:
        out = [r["frame"] for r in rows if not r["read_on"].startswith("frame")]
        left = [r["frame"] for r in rows if r["read_on"].startswith("frame")]
        fields.update(scene_out_frames=out, scene_left_frames=left)
        if left:
            why = sorted({r["read_on"].split(": ")[1].split(" (")[0] for r in rows if r["read_on"].startswith("frame")})
            npw.append(("the scene taken out", f"the scene was left in on {len(left)} of {len(rows)} frames ({frames_said(left)}): "
                                               + "; ".join(why) + " -- a flat sky has nothing to take out, and a scene that "
                                               "neither held still nor moved by one shift cannot be taken out, so those frames "
                                               "are read as they are"))
    if np.median(L) < MIN_BLURS * blur_px:
        npw.append(("streak", f"the dash is {np.median(L):.1f} px long, under {MIN_BLURS:g} blurs: no light curve (the "
                              f"exposure is under {MIN_BLURS * blur_px / np.median(sp) / fps * 1000:.1f} ms)"))
    picture = ("" if sc is None else " on the frames less their neighbours" if not fields["scene_left_frames"] else
               f" on the frames less their neighbours ({len(fields['scene_out_frames'])} of {len(rows)})")
    res["exposure"] = (f"{fields['exposure_s'] * 1000:.1f} ms, {fields['exposure_share']:.2f} of a frame (a "
                       f"{fields['exposure_share'] * 360:.0f}-degree shutter): the dash {np.median(L):.1f} px long at its half "
                       f"peak{picture} at {np.median(sp):.1f} px a frame, drawn through a {blur_px:.1f}-px blur")
    if fit:
        dash_fitted(rows, track, fps, fields, res, npw, notes)
    if spectra:
        sp_med = float(np.median([x[2] for x in spectra]))
        hz = np.arange(nfft // 2 + 1) / (nfft * STEP) * sp_med * fps      # the frequency axis: the median dash's bins, in hertz
        cyc_px = hz / (sp_med * fps)                                       # ... which is this many cycles a pixel on it
        tot, bg = summed(spectra, fps, hz, nfft)
        span = float(np.median([x[3] for x in spectra])) * STEP
        band = (cyc_px >= 2.0 / span) & (cyc_px < 1.0 / (BEAD_BLURS * blur_px))
        fields.update(dashes_read=len(spectra), band_hz=[float(hz[band].min()), float(hz[band].max())] if band.any() else None)
        if band.sum() < 4:
            npw.append(("streak", f"the beads were not read: inside the dash ({span:.0f} px between its soft ends) there is no room "
                                  f"for two cycles of beads {BEAD_BLURS:g} blurs apart ({BEAD_BLURS * blur_px:.1f} px), the band the search covers"))
        else:
            from scipy.stats import f as fdist
            dof = 2 * len(spectra)
            eps = 1e-9 * max(float(tot.max()), 1e-30)
            ratio = tot / np.maximum(bg, eps)
            j = int(np.flatnonzero(band)[np.argmax(ratio[band])])
            p = min(float(fdist.sf(ratio[j], dof, dof)) * int(band.sum()), 1.0)      # over every frequency looked at
            fields.update(bead_spacing_px=float(1.0 / cyc_px[j]), bead_hz=float(hz[j]), bead_ratio=float(ratio[j]), bead_p_noise_alone=p)
            res["beads along the dash"] = (f"every {1.0 / cyc_px[j]:.1f} px along {len(spectra)} dashes, {hz[j]:.0f} Hz at the track's "
                                           f"speed, {ratio[j]:.1f} times the power beside the dashes there (a 1 in {1 / max(p, 1e-300):,.0f} "
                                           f"chance from noise alone over the band): a reading, not a flicker found" if p < NOISE_ALONE else
                                           f"nothing stands out: the dashes' power peaks at {ratio[j]:.1f} times that beside them, every "
                                           f"{1.0 / cyc_px[j]:.1f} px ({hz[j]:.0f} Hz), a {p:.2f} chance from noise alone")
            npw.append(("streak", "a flicker inside the frame is not decided: a steady dash through a codec reaches any ratio a "
                                  "flicker does (steady dashes drawn with no flicker pass this ratio's 1-in-1,000 from noise alone on "
                                  f"{STEADY_PASS['x264 on real frames']} through x264 on real frames, {STEADY_PASS['x264 on a flat sky']} "
                                  f"on a flat sky, {STEADY_PASS['no codec']} with no codec), so the beads are not told from the encoder's "
                                  "texture"))
    notes.append("Assumes the object moves straight during one exposure at the track's speed, and that the dash is the "
                 "object's: a camera that turns during the exposure draws the scene's points as dashes too.")
    return Found("streak", res, fields, no_power=npw, notes=notes)


def frames_said(ns):
    """Frame numbers as runs: 50-52, 54, 57-74."""
    ns, out = sorted(ns), []
    for n in ns:
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in out)


def _T_said(pj):
    """The projective test's T in a few words, or why there is none."""
    if not pj:
        return "no T: under six points"
    if pj.get("closing") is True and pj.get("fits") is not False and pj.get("T") is not None:
        e = pj.get("t_z_err")
        return f"T {pj['T']:.2f}" + (f" ± {e:.2f}" if e is not None else "") + " s"
    return ("no T: no closing seen" if pj.get("closing") is False else "no T: it describes the track's trend only"
            if pj.get("fits") is False else "no T: not a straight line at a constant velocity")


def dash_fitted(rows, track, fps, fields, res, npw, notes):
    """What the dash fitted whole says, into the stage's fields, results, no power and notes: the exposure from its length
    (replacing the half-peak length's, which is kept beside it), its centres as the dash's track points and the projective
    test's T on them against the track's own, and its flux as a second clock on T."""
    from . import kinematics as kin, projective
    held = [r for r in rows if r.get("fit_holds")]
    long_ = [r for r in held if r["fit"]["length_px"] >= FIT_MIN_PX]
    fields["fit"] = fit = dict(frames=[r["frame"] for r in held], tried=len(rows), lengths=len(long_), z=FIT_Z, min_px=FIT_MIN_PX)
    if len(held) < FIT_MIN_FRAMES:
        whys = sorted({r["fit_why"].split(",")[0].split(":")[0] for r in rows if r.get("fit_why")})
        npw.append(("the dash fitted whole", f"the fit holds on {len(held)} of {len(rows)} frames, under the {FIT_MIN_FRAMES} it needs"
                                             + (f" ({'; '.join(whys)})" if whys else "")))
        return
    if len(long_) < FIT_MIN_FRAMES:
        npw.append(("the dash fitted whole", f"its fitted length is under {FIT_MIN_PX:g} px on {len(held) - len(long_)} of the "
                                             f"{len(held)} frames it holds on: a round spot is not told from a short dash, so no "
                                             "exposure is read from it"))
    else:
        L = np.array([r["fit"]["length_px"] for r in long_])
        v = np.array([r["speed_px_per_frame"] for r in long_])
        sh = L / v
        third = max(len(sh) // 3, 1)
        fit.update(exposure_share=float(np.median(sh)), exposure_s=float(np.median(sh)) / fps, length_px=float(np.median(L)),
                   width_px=float(np.median([r["fit"]["width_px"] for r in long_])),
                   angle_off_deg=float(np.median([abs(r["fit"]["angle_off_deg"]) for r in long_])),
                   share_first=float(np.median(sh[:third])), share_last=float(np.median(sh[-third:])))
        hp = fields["half_peak"]
        fields.update(exposure_share=fit["exposure_share"], exposure_s=fit["exposure_s"], length_px=fit["length_px"],
                      exposure_from="the dash fitted whole")
        res["exposure"] = (f"{fit['exposure_s'] * 1000:.1f} ms, {fit['exposure_share']:.2f} of a frame (a {fit['exposure_share'] * 360:.0f}-"
                           f"degree shutter): the dash fitted whole on {len(long_)} frames, {fit['length_px']:.1f} px long at "
                           f"{np.median(v):.1f} px a frame and {fit['width_px']:.1f} px wide at half its peak; its length at half its "
                           f"peak read {hp['exposure_s'] * 1000:.1f} ms ({hp['exposure_share']:.2f})")
        if len(long_) >= 2 * FIT_MIN_FRAMES:
            res["exposure"] += (f". The dash's share of the step runs from {fit['share_first']:.2f} on its first third of frames to "
                                f"{fit['share_last']:.2f} on its last")
    # the centres: the dash's own track points where the fit holds, the track's elsewhere
    centres = {r["frame"]: (r["fit"]["x"], r["fit"]["y"]) for r in held}
    fields["centres"] = {str(n): [round(x, 2), round(y, 2)] for n, (x, y) in sorted(centres.items())}
    merged = dict(track)
    merged.update(centres)
    pt, pc = projective.fit(track, fps), projective.fit(merged, fps)
    keep = ("T", "t_z_err", "closing", "fits", "jitter_px", "misfit", "straight_rms")
    fields["projective"] = {"track": {k: (pt or {}).get(k) for k in keep}, "centres": {k: (pc or {}).get(k) for k in keep}}
    jt, jc = (pt or {}).get("jitter_px"), (pc or {}).get("jitter_px")
    res["the dash's centres"] = (f"the fit's centres on {len(centres)} of {len(rows)} frames ({frames_said(centres)}), the track's own "
                                 f"points elsewhere: {_T_said(pc)}" + (f", a jitter of {jc:.1f} px" if jc else "")
                                 + f"; on the track's points, {_T_said(pt)}" + (f", {jt:.1f} px" if jt else "")
                                 + " (T: the projective test's time to the camera's plane after the last frame)")
    # the flux: a second clock on T, for a steady point closing at a steady speed
    fx = [(r["frame"], r["fit"]["flux"], r.get("level")) for r in held if r["fit"]["flux"] > 0]
    if len(fx) < kin.TAU_MIN_POINTS:
        npw.append(("the flux as a clock", f"its flux was read on {len(fx)} frames, under the {kin.TAU_MIN_POINTS} a clock needs"))
        return
    t = np.array([a for a, _, _ in fx], float) / fps
    E = np.array([b for _, b, _ in fx])
    b, e, change = kin._trend(t, np.log(E))
    clock = fit["flux_clock"] = dict(n=len(fx), dlnE_dt=b, dlnE_err=e, change=change)
    if not (abs(b) >= kin.TAU_Z * e and abs(change) >= kin.TAU_LIGHT):
        npw.append(("the flux as a clock", f"no change in its flux stands out of its own wander ({change:+.2f} in ln over the "
                                           f"stretch, {abs(b) / e if e else 0:.1f} sigma): no clock"))
        return
    lm = kin.looming_fit(t, np.sqrt(E), offset=False)
    t_last = max(track) / fps
    span = float(t[-1] - t[0]) or 1.0
    quad = float(np.sqrt(np.mean((np.sqrt(E) - np.polyval(np.polyfit(t, np.sqrt(E), 2), t)) ** 2)))
    far = lm is None or not (-projective.FAR * span * 0.95 < lm["t_z"] - t[-1] < projective.FAR * span * 0.95)
    if lm is None or far or lm["rms"] > projective.QUAD_SLACK * quad:
        npw.append(("the flux as a clock", "its flux changes, but not as 1/R^2 of a straight approach at a steady speed draws it"
                                           + (" (the camera's plane too far off)" if far else
                                              f" (the root of the flux off that law by {lm['rms']:.1f} where a free curve is off by {quad:.1f})")))
        return
    band = [lm["t_z_band"][0] - t_last, lm["t_z_band"][1] - t_last] if lm.get("t_z_band") else None
    lv = np.array([c for _, _, c in fx if c is not None and c > 0], float)
    level = float(np.log(lv[-max(len(lv) // 3, 1):].mean() / lv[:max(len(lv) // 3, 1)].mean())) if len(lv) >= 6 else None
    clock.update(T=float(lm["t_z"] - t_last), band=band, level_change=level, rms=lm["rms"])
    res["its flux, a second clock"] = (
        f"T {clock['T']:.2f} s" + (f" (16-84 % {band[0]:.2f}-{band[1]:.2f})" if band else "")
        + f" from the dash's flux on {len(fx)} frames, which {'grows' if b > 0 else 'falls'} by {math.exp(abs(change)):.2f} times over the "
        f"stretch; the track's points give {_T_said(pt)}. A clock only if the change is the range's alone: a steady point "
        "(flux as 1/R^2), the exposure and the gain held, and the picture's gamma left out (a video's levels compress a change of "
        "brightness by up to 2.2, and this clock reads long by up to that)"
        + (f"; here the dash's share of the step runs {fit['share_first']:.2f} to {fit['share_last']:.2f}" if fit.get("share_first") else "")
        + (f" and the scene's level changes by {100 * (math.exp(level) - 1):+.0f} %" if level is not None else ""))


def scene_blur(clip, track, masks=None):
    """(blur px, from what): the picture's blur from the scene's own points (`forensics.point_blur`, as `focus` measures
    it), or BLUR_ASSUMED where the scene has too few points to say. PR43 (2026-10-29): its 43 compact spots read 3.6 px,
    and its dash, 11.5 ms at an assumed 2 px, is 6.4 ms at that -- under three blurs, so no light curve at all."""
    from . import forensics as vf
    b = vf.point_blur(clip, track, masks if masks is not None else vf.static_masks(clip))
    if b.get("blur_fwhm_px"):
        return float(b["blur_fwhm_px"]), f"the scene's points ({b['spots']} compact spots on {b['frames']} frames)"
    return BLUR_ASSUMED, f"assumed: too few points in the scene to measure it ({b.get('spots', 0)} spots)"


def said(f):
    L = []
    if f.get("blur_from"):
        L.append(f"the blur {f['blur_px']:.1f} px at half its peak, from {f['blur_from']}")
    if f.get("scene_out_frames") is not None:
        n_out, n_all = len(f["scene_out_frames"]), len(f["scene_out_frames"]) + len(f["scene_left_frames"])
        L.append(f"the scene taken out on {n_out} of {n_all} frames (each less the median of its neighbours 4-6 frames away)")
    if f.get("exposure_s") is not None:
        L.append(f"exposure {f['exposure_s'] * 1000:.1f} ms ({f['exposure_share']:.2f} of a frame) from {f.get('exposure_from', 'the half-peak length')}, "
                 f"the dash {f['length_px']:.1f} px at {f['speed_px_per_frame']:.1f} px a frame")
    hp, ft = f.get("half_peak"), f.get("fit") or {}
    if hp and f.get("exposure_from") == "the dash fitted whole":
        L.append(f"  its length at half its peak: {hp['exposure_s'] * 1000:.1f} ms ({hp['exposure_share']:.2f} of a frame), the dash {hp['length_px']:.1f} px")
    if ft.get("frames") is not None:
        L.append(f"the dash fitted whole on {len(ft['frames'])} of {ft['tried']} frames"
                 + (f" ({frames_said(ft['frames'])})" if ft["frames"] else "")
                 + (f", {ft['width_px']:.1f} px wide at half its peak, its axis {ft['angle_off_deg']:.1f}° off the track's" if ft.get("width_px") else ""))
    pj = f.get("projective")
    if pj:
        L.append(f"T on the dash's centres: {_T_said(pj['centres'])}" + (f" (jitter {pj['centres']['jitter_px']:.1f} px)" if pj["centres"].get("jitter_px") else "")
                 + f"; on the track's points: {_T_said(pj['track'])}" + (f" (jitter {pj['track']['jitter_px']:.1f} px)" if pj["track"].get("jitter_px") else ""))
    fc = ft.get("flux_clock") or {}
    if fc.get("T") is not None:
        L.append(f"T from the dash's flux: {fc['T']:.2f} s" + (f" (16-84 % {fc['band'][0]:.2f}-{fc['band'][1]:.2f})" if fc.get("band") else "")
                 + ", if the flux changes by the range alone (a steady point, the exposure and the gain held, the gamma left out)")
    if f.get("bead_ratio") is not None:
        L.append(f"beads every {f['bead_spacing_px']:.1f} px, {f['bead_hz']:.0f} Hz, {f['bead_ratio']:.1f} times the power beside the "
                 f"dashes (a {f['bead_p_noise_alone']:.1e} chance from noise alone, which is not this test's false alarm through a codec: "
                 "a reading, not a flicker found)")
    return L


def write_centres(path, track, centres, fps, video):
    """The track with the dash's fitted centres in place of its points where the fit holds: a CSV `run --track` reads,
    its header naming the frames of each."""
    from pathlib import Path
    got = {int(n): xy for n, xy in centres.items()}
    lines = [f"# the dash's centres on {video}, fitted whole by mcdonald.streak (fit_dash: the trailed point-spread function)",
             f"# the fit's centre on frames {frames_said(got)}; the track's own point on "
             + (frames_said(set(track) - set(got)) or "none"),
             "frame,t_s,x_px,y_px,source"]
    for n in sorted(track):
        x, y = got.get(n, track[n])
        lines.append(f"{n},{n / fps:.4f},{x:.2f},{y:.2f},{'dash fit' if n in got else 'track'}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def main():
    import argparse
    from . import clip as vclip
    from . import forensics as vf
    from .report import emit, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", required=True, help="CSV with frame and x/y columns: the object, on every frame of the dash")
    ap.add_argument("--blur", type=float, help="the picture's blur, px at half its peak (default: measured from the "
                    f"scene's compact points, as `mcdonald focus` measures it; {BLUR_ASSUMED:g} where there are too few)")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--scene-in", action="store_true", help="read each frame as it is, the scene left in (as before 2026-11-07); "
                    "by default each frame is read less the median of its neighbours 4-6 frames away where that is quieter round the dash")
    ap.add_argument("--centres", metavar="CSV", help="write the dash's fitted centres as a track: the fit's centre on each frame it holds on, "
                    "the track's own point elsewhere, the source column saying which")
    ap.add_argument("--workdir")
    ap.add_argument("--json", action="store_true", help="print the measurement as JSON on stdout")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        video, tag, _ = vf.resolve(args.video)
        track = vf.read_track(args.track)
        n0, n1 = args.n0 or min(track), args.n1 or max(track)
        reach = 0 if args.scene_in else max(abs(d) for d in NEIGHBOURS)       # the neighbours the scene is taken from
        clip = vclip.Clip(video, args.workdir, max(n0 - reach, 1), n1 + reach)
        track = {n: xy for n, xy in track.items() if n0 <= n <= n1 and clip.n0 <= n <= clip.n1}
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {min(track)}-{max(track)}"
              + (f" (and {clip.n0}-{clip.n1} for the scene)" if reach else ""))
        masks = vf.static_masks(clip)
        blur, blur_from = (args.blur, "given") if args.blur else scene_blur(clip, track, masks)
        found = measure(clip, track, blur, scene=not args.scene_in, masks=masks)
        found.fields["blur_from"] = blur_from
        if args.centres and found.fields.get("centres"):
            found.files.append(write_centres(args.centres, track, found.fields["centres"], clip.fps, video.name))
            print(f"the dash's centres as a track: {args.centres}")
        print("\n".join(said(found.fields)))
        for w in found.no_power:
            print(f"no power: {w[1]}")
    code = vclip.EXIT_NOTHING if found.no_power and not found.result else 0
    if args.json:
        emit(found.envelope("streak", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
