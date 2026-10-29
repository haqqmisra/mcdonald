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
- **A flicker far above the frame rate.** A light that blinks while the shutter is open leaves beads along the dash,
  spaced by its period times the speed (the insect note's "rods"; a blinking aircraft light's dotted trail). The
  profile inside the dash (its soft ends, a blur each, left out, and a straight line taken out of it) is searched for a
  period: its power at each frequency, summed over every frame's dash, over the same from the lines beside the dash
  (their difference, scaled to the dash line's noise), and the largest such ratio tested as an F ratio with twice as
  many degrees of freedom as dashes on each side, its chance multiplied by the frequencies looked at; under 1e-3, a
  flicker. A steady body leaves a flat dash with soft ends.

What it assumes, and says on every run: (1) the object moves in a straight line during one exposure, at the speed the
track gives between frames; (2) the dash is the object's and not the camera's: a camera that turns during the exposure
smears the whole scene too (the scene's own points are drawn as dashes then, and the track's speed is not the object's
across the picture); (3) the beads are the object's brightness and not the scene behind it, which the profile beside the
dash (the same line, offset across it) is taken from and subtracted.

What it cannot do: read a dash shorter than three blurs (no light curve), a flicker whose beads are closer than two
blurs (they merge), or one slower than a period over the dash's length (one bead, or none).
"""
import math

import numpy as np
from scipy import ndimage

from .report import Found

STEP = 0.5            # px: the profile's sampling along the dash
ACROSS = 1.0          # px either side of the line averaged across it
SIDE = 6.0            # px: the background's lines, either side of the dash
MIN_BLURS = 3.0       # a dash this many blurs long or more is read as a light curve
BLUR_ASSUMED = 2.0    # px: the blur where the scene has too few points to measure it
FALSE_ALARM = 1e-3    # a flicker's peak: the chance of a ratio that large from noise, over every frequency looked at


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


def measure(clip, track, blur_px=2.0):
    """The stage: per frame the dash's length and its profile; the exposure and shutter share; the summed spectra of the
    profiles inside the dashes and their peak. A Found."""
    fr = sorted(track)
    if len(fr) < 3:
        return Found("streak", no_power=[("streak", "under three tracked frames: no speed to read a dash by")])
    xs, ys = np.array([track[n][0] for n in fr]), np.array([track[n][1] for n in fr])
    vx, vy = np.gradient(xs, fr), np.gradient(ys, fr)            # px a frame, centred
    rows, spectra = [], []
    nfft = 256
    for i, n in enumerate(fr):
        sp = math.hypot(vx[i], vy[i])
        if sp < 0.5:
            continue
        ux, uy = vx[i] / sp, vy[i] / sp
        half = 1.5 * sp + 4 * blur_px
        s, v, null = profile(clip.grey(n), xs[i], ys[i], ux, uy, half, blur_px)
        # the dash's extent from the profile smoothed over three blurs: beads deep enough to dip under half the peak
        # would end the run at the first trough, and the half-peak ends of a long dash do not move under a symmetric
        # smoothing; a dash shorter than the smoothing is measured as it is
        box = max(3, int(round(3 * blur_px / STEP)))
        L, ends = dash_length(s, ndimage.uniform_filter1d(v, box, mode="nearest"))
        if L < 1.5 * box * STEP:
            L, ends = dash_length(s, v)
        row = dict(frame=n, speed_px_per_frame=sp, length_px=L, peak=float(v.max()))
        if ends and L >= MIN_BLURS * blur_px:
            trim = int(round(blur_px / STEP))                     # the soft ends, a blur each, left out
            a, b = ends[0] + trim, ends[1] - trim
            if b - a >= 8:
                level = float(np.mean(v[a:b + 1]))
                spectra.append((fine_spectrum(v[a:b + 1], level, nfft), fine_spectrum(null[a:b + 1], level, nfft), sp,
                                b - a + 1))
        rows.append(row)
    fields = dict(rows=rows, blur_px=blur_px, frames=len(fr))
    res, npw, notes = {}, [], []
    fps = getattr(clip, "fps", 30.0)
    if not rows:
        npw.append(("streak", "the track does not move: no dash"))
        return Found("streak", res, fields, no_power=npw)
    L = np.array([r["length_px"] for r in rows])
    sp = np.array([r["speed_px_per_frame"] for r in rows])
    share = np.array([motion_px(a, blur_px) for a in L]) / sp       # of a frame
    fields.update(exposure_share=float(np.median(share)), exposure_s=float(np.median(share)) / fps,
                  length_px=float(np.median(L)), speed_px_per_frame=float(np.median(sp)))
    if np.median(L) < MIN_BLURS * blur_px:
        npw.append(("streak", f"the dash is {np.median(L):.1f} px long, under {MIN_BLURS:g} blurs: no light curve (the "
                              f"exposure is under {MIN_BLURS * blur_px / np.median(sp) / fps * 1000:.1f} ms)"))
    res["exposure"] = (f"{fields['exposure_s'] * 1000:.1f} ms, {fields['exposure_share']:.2f} of a frame (a "
                       f"{fields['exposure_share'] * 360:.0f}-degree shutter): the dash {np.median(L):.1f} px long at "
                       f"{np.median(sp):.1f} px a frame, drawn through a {blur_px:.1f}-px blur")
    if spectra:
        tot = np.sum([x[0] for x in spectra], axis=0)
        bg = np.sum([x[1] for x in spectra], axis=0)                  # the same, on the lines beside the dash
        k = np.arange(len(tot))
        cyc_px = k / (nfft * STEP)                                     # cycles a pixel along the dash
        span = float(np.median([x[3] for x in spectra])) * STEP
        band = (cyc_px >= 2.0 / span) & (cyc_px < 1.0 / (2.0 * blur_px))
        if band.sum() >= 4:
            from scipy.stats import f as fdist
            ratio = tot / np.maximum(bg, 1e-30)
            j = int(np.flatnonzero(band)[np.argmax(ratio[band])])
            dof = 2 * len(spectra)
            p = float(fdist.sf(ratio[j], dof, dof)) * int(band.sum())       # over every frequency looked at
            hz = cyc_px[j] * np.median(sp) * fps
            fields.update(bead_spacing_px=float(1.0 / cyc_px[j]), bead_hz=float(hz), bead_ratio=float(ratio[j]),
                          bead_p=min(p, 1.0), dashes_read=len(spectra))
            if p < FALSE_ALARM:
                res["flicker inside the frame"] = (f"beads every {1.0 / cyc_px[j]:.1f} px along {len(spectra)} dashes: "
                                                   f"{hz:.0f} Hz at the track's speed ({ratio[j]:.1f} times the power "
                                                   f"beside the dashes there; false alarm {p:.1e} over the band)")
            else:
                res["flicker inside the frame"] = (f"none: the dashes' power peaks at {ratio[j]:.1f} times that beside "
                                                   f"them (false alarm {min(p, 1.0):.2f}); a steady body over the exposure")
    notes.append("Assumes the object moves straight during one exposure at the track's speed, and that the dash is the "
                 "object's: a camera that turns during the exposure draws the scene's points as dashes too.")
    return Found("streak", res, fields, no_power=npw, notes=notes)


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
    if f.get("exposure_s") is not None:
        L.append(f"exposure {f['exposure_s'] * 1000:.1f} ms ({f['exposure_share']:.2f} of a frame), the dash "
                 f"{f['length_px']:.1f} px at {f['speed_px_per_frame']:.1f} px a frame")
    if f.get("bead_hz") is not None:
        L.append(f"beads every {f['bead_spacing_px']:.1f} px, {f['bead_hz']:.0f} Hz, {f['bead_ratio']:.1f} times the "
                 f"power beside the dashes (false alarm {f['bead_p']:.1e})" + (" -- a flicker" if f["bead_p"] < FALSE_ALARM
                                                                               else " -- none to speak of"))
    return L


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
    ap.add_argument("--workdir")
    ap.add_argument("--json", action="store_true", help="print the measurement as JSON on stdout")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        video, tag, _ = vf.resolve(args.video)
        track = vf.read_track(args.track)
        n0, n1 = args.n0 or min(track), args.n1 or max(track)
        clip = vclip.Clip(video, args.workdir, n0, n1)
        track = {n: xy for n, xy in track.items() if clip.n0 <= n <= clip.n1}
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
        blur, blur_from = (args.blur, "given") if args.blur else scene_blur(clip, track)
        found = measure(clip, track, blur)
        found.fields["blur_from"] = blur_from
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
