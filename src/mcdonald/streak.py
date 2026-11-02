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


def read(clip, track, blur_px, nfft=256):
    """The dashes along a track: per frame its speed, length at half its peak and peak (rows), and for each dash long
    enough to read, its profile's power at each frequency and the null line's, with its speed and its span in samples
    (spectra). The frames' step is the track's own, centred (`np.gradient`)."""
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


def measure(clip, track, blur_px=2.0):
    """The stage: per frame the dash's length and its profile; the exposure and shutter share; the summed spectra of the
    profiles inside the dashes, in hertz, and their peak over the lines beside them -- a reading, with the chance noise
    alone would give it and why that is not a false alarm (NOISE_ALONE, STEADY_PASS). A Found."""
    fr = sorted(track)
    if len(fr) < 3:
        return Found("streak", no_power=[("streak", "under three tracked frames: no speed to read a dash by")])
    nfft = 256
    rows, spectra = read(clip, track, blur_px, nfft)
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
    if f.get("bead_ratio") is not None:
        L.append(f"beads every {f['bead_spacing_px']:.1f} px, {f['bead_hz']:.0f} Hz, {f['bead_ratio']:.1f} times the power beside the "
                 f"dashes (a {f['bead_p_noise_alone']:.1e} chance from noise alone, which is not this test's false alarm through a codec: "
                 "a reading, not a flicker found)")
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
