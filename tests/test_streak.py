"""Does `mcdonald streak` read the exposure from a dash, and report a flicker far above the frame rate as a reading?

Rendered frames: a point crossing the picture at 51 px a frame, drawn through a 2-px blur while a 180-degree shutter is
open (half of each frame), steady or blinking at 300 Hz (ten times a frame, its beads 5.2 px apart along the dash, half
a blur inside the band's top). The steady dash gives the exposure (half a frame, 16.7 ms at 30 fps) and nothing
standing out among its beads; the blinking one the same exposure and beads at 300 Hz, read and said -- and in both the
stage says, as no power, that a flicker inside the frame is not decided, since a steady dash through a codec reaches
any ratio a flicker does (the null study of 2026-11-02, method section 30: the reason the stage calls none); a point
crossing at 2 px a frame draws no dash long enough to read. And steady dashes through x264 at CRF 28: every one a
reading and none a verdict, the blink read through the same codec.

    python3 tests/test_streak.py        # or: pytest tests/

No video data needed; the codec check needs an ffmpeg with libx264 and says so where there is none.
"""
import math
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import streak  # noqa: E402

FAIL = []
W, H = 400, 240
FPS = 30.0
# The blink the tests draw: its beads (speed x frame rate / hz) sit half a blur inside the band's top (streak.BEAD_BLURS):
# 300 Hz, 5.2 px apart, with the top at two blurs.
BLINK_HZ = float(round(math.hypot(51.0, 10.0) * FPS / ((streak.BEAD_BLURS + 0.6) * 2.0)))


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


class Frames:
    def __init__(self, frames):
        self._f = frames
        self.n0, self.n1 = min(frames), max(frames)
        self.fps = FPS

    def grey(self, n):
        return self._f[n]


def render(v=(51.0, 10.0), share=0.5, hz=None, n=14, blur=2.0, amp=600.0, seed=0, noise=1.5, sky=30.0):
    """Frames of a point moving v px a frame, drawn while the shutter is open (`share` of a frame), its light steady or
    1 + 0.8 sin(2 pi hz t); the track at the middle of each exposure."""
    s = blur / 2.3548
    frames, track = {}, {}
    steps = 400
    for i in range(1, n + 1):
        g = sky + np.random.default_rng(1000 * seed + i).normal(0, noise, (H, W))
        x0, y0 = 40.0 + v[0] * (i - 1), 60.0 + v[1] * (i - 1)
        for j in range(steps):
            f = (j + 0.5) / steps * share                            # of a frame, from the shutter opening
            t = ((i - 1) + f) / FPS
            light = 1.0 if hz is None else 1.0 + 0.8 * math.sin(2 * math.pi * hz * t)
            x, y = x0 + v[0] * f, y0 + v[1] * f
            a, b = int(x) - 6, int(y) - 6
            yy, xx = np.mgrid[b:b + 13, a:a + 13]
            ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W)
            add = amp / steps * light * np.exp(-0.5 * ((xx - x) ** 2 + (yy - y) ** 2) / s ** 2)
            g[yy[ok], xx[ok]] += add[ok]
        frames[i] = g.astype(np.float32)
        track[i] = (x0 + v[0] * share / 2, y0 + v[1] * share / 2)
    return Frames(frames), track


def not_decided(found):
    """Whether the stage said, as no power, that a flicker inside the frame is not decided, and called none."""
    return any("not decided" in w and "steady dash through a codec" in w for _, w in found.no_power) and "flicker inside the frame" not in found.result


def test_the_exposure_and_a_steady_body():
    print("\nstreak: a steady point at 51 px a frame under a 180-degree shutter")
    clip, trk = render()
    f = streak.measure(clip, trk, blur_px=2.0)
    e = f.fields.get("exposure_share")
    check(e is not None and abs(e - 0.5) < 0.03, "the exposure: half a frame", e and f"{e:.3f} ({f.fields['exposure_s'] * 1000:.1f} ms)")
    p = f.fields.get("bead_p_noise_alone")
    check(p is not None and p >= streak.NOISE_ALONE and f.result.get("beads along the dash", "").startswith("nothing stands out") and not_decided(f),
          "nothing stands out among a steady dash's beads, and the stage says a flicker inside the frame is not decided",
          f"{f.fields.get('bead_ratio', 0):.2f} times the power beside the dashes, a {p or 0:.2f} chance from noise alone")


def test_a_flicker_far_above_the_frame_rate():
    print(f"\nstreak: the same point blinking at {BLINK_HZ:.0f} Hz (beads {math.hypot(51.0, 10.0) * FPS / BLINK_HZ:.2f} px apart)")
    clip, trk = render(hz=BLINK_HZ)
    f = streak.measure(clip, trk, blur_px=2.0)
    hz, p = f.fields.get("bead_hz"), f.fields.get("bead_p_noise_alone")
    check(hz is not None and abs(hz / BLINK_HZ - 1) < 0.1 and p < streak.NOISE_ALONE, f"beads at {BLINK_HZ:.0f} Hz, standing out of the noise",
          f"{hz and round(hz)} Hz, {f.fields.get('bead_ratio', 0):.1f} times the power beside the dashes, a {p:.1e} chance from noise alone, every "
          f"{f.fields.get('bead_spacing_px', 0):.2f} px")
    said = f.result.get("beads along the dash", "")
    check(said.startswith("every ") and "Hz" in said and said.endswith("a reading, not a flicker found") and not_decided(f),
          "and said as a reading, not a flicker found: the stage cannot tell beads from a codec's texture", said)


def test_steady_dashes_through_a_codec():
    """Steady dashes drawn on a sky with a little texture and put through libx264 at CRF 28 (the null study's harshest
    chain, where a codec flattens the lines beside a dash and textures it): the stage reports each as a reading and calls
    no flicker, saying it is not decided; the blinking dash through the same codec is read at its rate. How many of the
    eight the chance from noise alone would have called a flicker at 1 in 1,000 is printed, not pinned: the defect's rate
    is measured on the method's null of 45 tracks a chain (section 30: 36-44 of 45 on a flat sky at 1280x720), and a
    400x240 sky at this grain need not reach it."""
    print("\nstreak: steady dashes through x264 at CRF 28 -- readings, no verdict")
    from mcdonald import planted
    if not planted.has_x264():
        print("  SKIP  this ffmpeg has no libx264")
        return
    st = dict(rate="30", gop=30, bframes=2, crf=28)

    def coded(clip):
        fr = sorted(clip._f)
        out = planted.encoded(np.stack([np.clip(np.round(clip._f[n]), 0, 255).astype(np.uint8) for n in fr]), st)
        return Frames({n: out[i].astype(np.float32) for i, n in enumerate(fr)}) if out is not None else None
    ps, ratios, decided, read = [], [], 0, 0
    for seed, v, blur, amp in ((1, (51.0, 10.0), 2.0, 600.0), (2, (56.0, -6.0), 2.5, 300.0), (3, (60.0, 0.0), 2.0, 900.0), (4, (62.0, 12.0), 3.0, 400.0),
                               (5, (45.0, 4.0), 2.2, 250.0), (6, (58.0, -10.0), 2.8, 700.0), (7, (44.0, 8.0), 2.0, 350.0), (8, (54.0, -3.0), 2.4, 500.0)):
        clip, trk = render(v=v, blur=blur, amp=amp, seed=seed, noise=2.5, sky=60.0)
        enc = coded(clip)
        if enc is None:
            check(False, "the frames went through libx264")
            return
        f = streak.measure(enc, trk, blur_px=blur)
        ps.append(f.fields.get("bead_p_noise_alone", 1.0))
        ratios.append(f.fields.get("bead_ratio", 0.0))
        decided += not not_decided(f)
        read += "beads along the dash" in f.result
    passes = sum(p < streak.NOISE_ALONE for p in ps)
    check(read == 8 and decided == 0,
          f"eight steady dashes through x264 at CRF 28: a reading each, no flicker called, each time said not decided (the chance from noise "
          f"alone would have called {passes} of them one at {streak.NOISE_ALONE:g})",
          f"ratios {[f'{r:.0f}' for r in ratios]}, chances {[f'{p:.1g}' for p in ps]}")
    clip, trk = render(hz=BLINK_HZ, seed=9, noise=2.5, sky=60.0)
    f = streak.measure(coded(clip), trk, blur_px=2.0).fields
    hz = f.get("bead_hz")
    check(hz is not None and abs(hz / BLINK_HZ - 1) < 0.1, f"the blinking dash through the same codec: its beads read at {BLINK_HZ:.0f} Hz",
          f"{hz and round(hz)} Hz, {f.get('bead_ratio', 0):.1f} times the power beside the dashes")


def test_a_slow_point_draws_no_dash():
    print("\nstreak: a point crossing at 2 px a frame")
    clip, trk = render(v=(2.0, 0.0))
    f = streak.measure(clip, trk, blur_px=2.0)
    said = [w for _, w in f.no_power]
    check(any("under 3 blurs" in w for w in said), "no light curve: the dash is under three blurs", "; ".join(said))
    check(any(t == "the dash fitted whole" and f"under {streak.FIT_MIN_PX:g} px" in w for t, w in f.no_power)
          and f.fields["exposure_from"] == "the half-peak length",
          f"and the dash fitted whole reads no length under {streak.FIT_MIN_PX:g} px: a round spot is not told from a short dash",
          next((w for t, w in f.no_power if t == "the dash fitted whole"), ""))


class Scene(Frames):
    """The frames with `points` of the scene in them, panning 1 px a frame, drawn through the same blur as the dash."""

    def __init__(self, frames, blur, points=24):
        super().__init__(frames)
        s = blur / 2.3548
        yy, xx = np.mgrid[-7:8, -7:8]
        stamp = 100 * np.exp(-0.5 * (xx ** 2 + yy ** 2) / s ** 2)
        for x, y in np.random.default_rng(5).integers(20, [W - 40, H - 20], (points, 2)):
            for n, g in self._f.items():
                g[y - 7:y + 8, x + n - 7:x + n + 8] += stamp

    def rgb(self, n):
        return np.clip(self._f[n], 0, 255)[..., None].repeat(3, 2).astype(np.uint8)


def test_the_blur_from_the_scene():
    print("\nstreak: the blur from the scene's own points (PR43, 2026-10-29: 3.6 px, where 2 was assumed)")
    masks = dict(blocks=np.zeros((H, W), bool), graphics=np.zeros((H, W), bool), colour=True)
    frames, trk = render(v=(20.0, 4.0), blur=3.5)
    plain = Scene({n: g.copy() for n, g in frames._f.items()}, 3.5, points=0)
    scene = Scene(frames._f, 3.5)
    b, how = streak.scene_blur(scene, trk, masks)
    b0, how0 = streak.scene_blur(plain, trk, masks)
    check(abs(b - 3.5) < 0.35 and "the scene's points" in how and b0 == streak.BLUR_ASSUMED and "too few" in how0,
          "the blur is read off the scene's points; with none, 2 px is assumed and said to be", f"{b:.2f} px ({how}); {how0}")
    (got, fit_got), (two, fit_two) = ((f["half_peak"]["exposure_share"], f["exposure_share"])
                                      for f in (streak.measure(scene, trk, x).fields for x in (b, 2.0)))
    check(abs(got - 0.5) < 0.04 and abs(two - 0.5) < 0.04,
          "a dash three blurs long: half a frame at the picture's own blur and at an assumed 2 px alike (its half-peak ends "
          "are the motion's; less a blur, it read 0.34)", f"{got:.3f} at {b:.2f} px, {two:.3f} at 2 px")
    check(abs(fit_got - 0.5) < 0.04 and abs(fit_two - 0.5) < 0.04,
          "and the dash fitted whole, its width its own, half a frame whichever blur it starts from", f"{fit_got:.3f}, {fit_two:.3f}")
    frames, trk = render(v=(10.0, 0.0), blur=3.5)
    short = streak.measure(frames, trk, 3.5).fields["half_peak"]
    e, L = short["exposure_share"], short["length_px"]
    check(abs(e - 0.5) < 0.08 and (L - 3.5) / 10.0 < 0.3,
          "a dash under twice the blur long: still half a frame, the blur taken out exactly (less a blur, it reads "
          f"{(L - 3.5) / 10.0:.2f})", f"{e:.3f} from a dash {L:.1f} px long")


def textured(n, seed=7, drift=(0.0, 0.0), changing=False, w=None, h=None):
    """A ground of bright and dark patches (a few px to 20 px across, 25 DN), one picture moved by `drift` px a frame --
    or, `changing`, a new one each frame: a scene no shift brings back."""
    w, h = w or W, h or H
    rng = np.random.default_rng(seed)
    base = None
    out = {}
    for i in range(1, n + 1):
        if base is None or changing:
            big = ndimage.gaussian_filter(rng.normal(0, 1, (h + 80, w + 80)), 4.0)
            base = 25.0 * big / big.std()
        dx, dy = drift[0] * (i - 1), drift[1] * (i - 1)
        out[i] = ndimage.shift(base, (dy, dx), order=1, mode="nearest")[40:40 + h, 40:40 + w].astype(np.float32)
    return out


def test_the_scene_taken_out():
    """F11 (the single-camera survey's §1.1): each frame read less the median of its neighbours 4-6 frames away. A steady
    dash at 20 px a frame on a textured ground: held still and moving 3 px a frame (its neighbours brought onto it), the
    scene comes out and the dash reads half a frame from its half-peak length, where on the frame as it is the ground's
    patches end it short or stretch it (the frames' spread is the test); on a ground that changes every frame nothing
    brings the scene back, and the stage reads the frames as they are and says so."""
    print("\nstreak: the scene taken out -- a dash on a textured ground, still, moving, and changing")
    def run(drift=(0.0, 0.0), changing=False, scene=True):
        clip, trk = render(v=(20.0, 6.0), n=16, amp=300.0, seed=3, noise=1.5, sky=60.0)
        ground = textured(16, drift=drift, changing=changing)
        for n in clip._f:
            clip._f[n] = clip._f[n] + ground[n]
        f = streak.measure(clip, trk, blur_px=2.0, scene=scene)
        sh = np.array([streak.motion_px(r["length_px"], 2.0) / r["speed_px_per_frame"] for r in f.fields["rows"]])
        return f, sh
    for drift, label in (((0.0, 0.0), "held still"), ((3.0, -1.0), "moving 3 px a frame")):
        f, sh = run(drift)
        f0, sh0 = run(drift, scene=False)
        out = len(f.fields["scene_out_frames"])
        check(out == 16 and abs(np.median(sh) - 0.5) < 0.04 and np.std(sh) < 0.5 * np.std(sh0)
              and (drift == (0.0, 0.0) or any("brought onto it" in r["read_on"] for r in f.fields["rows"])),
              f"a ground {label}: taken out on every frame, the half-peak length half a frame and its spread under half the frame's",
              f"{out} of 16 frames; share {np.median(sh):.3f} spread {np.std(sh):.3f}, on the frames as they are {np.median(sh0):.3f} "
              f"spread {np.std(sh0):.3f}")
    f, sh = run(changing=True)
    said = next((w for t, w in f.no_power if t == "the scene taken out"), "")
    check(len(f.fields["scene_left_frames"]) >= 14 and "left in" in said and "no quieter" in said,
          "a ground that changes every frame: no shift brings it back, the frames are read as they are, and the stage says so", said[:160])


def test_the_dash_fitted_whole():
    """F12 (the survey's §1.2; Vereš et al. 2012): the dash fitted whole -- its centre, length, direction, width and
    flux -- on a steady dash at 30 px a frame under a 180-degree shutter, its last frames at the picture's edge (the part
    of the patch inside it fitted): the exposure half a frame from the fitted
    length, its width the blur's, its axis on the track's, its centres on the true ones; the half-peak reading kept
    beside it; and the centres written as a track that reads back."""
    print("\nstreak: the dash fitted whole")
    clip, trk = render(v=(30.0, 6.0), n=12)
    truth = {n: xy for n, xy in trk.items()}
    f = streak.measure(clip, trk, blur_px=2.0)
    ft = f.fields["fit"]
    check(len(ft["frames"]) == 12 and f.fields["exposure_from"] == "the dash fitted whole" and abs(f.fields["exposure_share"] - 0.5) < 0.02
          and abs(ft["width_px"] - 2.0) < 0.2 and ft["angle_off_deg"] < 1.0,
          "held on every frame: half a frame, its width the blur's, its axis on the track's",
          f"{len(ft['frames'])} frames, {f.fields['exposure_share']:.3f} of a frame, {ft['width_px']:.2f} px wide, {ft['angle_off_deg']:.2f}° off")
    off = max(float(np.hypot(*(np.array(xy) - truth[int(n)]))) for n, xy in f.fields["centres"].items())
    check(off < 0.3 and "half its peak read" in f.result["exposure"] and "the dash fitted whole" in f.result["exposure"],
          "its centres within 0.3 px of the true ones, and the half-peak length said beside it", f"{off:.2f} px; {f.result['exposure'][:120]}")
    from mcdonald import forensics as vf
    import tempfile, os
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
        path = streak.write_centres(Path(d) / "c.csv", trk, f.fields["centres"], FPS, "drawn")
        back = vf.read_track(path)
        head = Path(path).read_text().splitlines()[1]
    check(sorted(back) == sorted(trk) and abs(back[5][0] - f.fields["centres"]["5"][0]) < 0.01 and "frames 1-12" in head,
          "the centres written as a track `run --track` reads, its header naming the frames", head)


def test_two_clocks_on_an_approach():
    """F51 and F41: a steady point closing straight at a steady speed, drawn as a pinhole draws it -- its distance from
    the vanishing point as 1/(t_z - t) and its flux as 1/(t_z - t)^2, T = 0.6 s after the last frame. The projective test
    on the dash's centres and the dash's flux each give T; the stage says both, and the flux's conditions."""
    print("\nstreak: two clocks on a straight approach, T 0.6 s")
    ww, hh, n, T = 720, 300, 14, 0.6
    t_last = n / FPS
    tz = t_last + T
    C = 1500.0 * T ** 2                                   # px s: 50 px a frame at the end
    ux, uy = 51.0 / math.hypot(51, 10), 10.0 / math.hypot(51, 10)
    s = 2.0 / 2.3548
    rng = np.random.default_rng(4)
    frames, trk, steps = {}, {}, 300
    for i in range(1, n + 1):
        g = 30.0 + rng.normal(0, 1.5, (hh, ww))
        for j in range(steps):
            t = (i + (j + 0.5) / steps * 0.5 - 1) / FPS + 1.0 / FPS
            d = C / (tz - t)
            x, y = -400.0 + d * ux, 40.0 - 400.0 * uy / ux + d * uy
            light = 3e4 / (tz - t) ** 2 / FPS / 1000.0
            a, b = int(x) - 6, int(y) - 6
            yy, xx = np.mgrid[b:b + 13, a:a + 13]
            ok = (yy >= 0) & (yy < hh) & (xx >= 0) & (xx < ww)
            g[yy[ok], xx[ok]] += (light / steps * 400 * np.exp(-0.5 * ((xx - x) ** 2 + (yy - y) ** 2) / s ** 2))[ok]
        t = (i - 1 + 0.25) / FPS + 1.0 / FPS
        d = C / (tz - t)
        frames[i], trk[i] = g.astype(np.float32), (-400.0 + d * ux, 40.0 - 400.0 * uy / ux + d * uy)
    f = streak.measure(Frames(frames), trk, blur_px=2.0)
    pj, fc = f.fields["projective"], f.fields["fit"].get("flux_clock") or {}
    tc = pj["centres"].get("T")
    check(tc is not None and abs(tc - T) < 0.08 and fc.get("T") is not None and abs(fc["T"] - T) < 0.1,
          "the dash's centres and its flux give T 0.6 s each", f"centres {tc and round(tc, 3)}, flux {fc.get('T') and round(fc['T'], 3)} "
          f"({fc.get('band')}), on {fc.get('n')} frames")
    said = f.result.get("its flux, a second clock", "")
    check("the track's points give T" in said and "steady point" in said and "gamma" in said,
          "and the stage says the flux's clock beside the track's, with what it assumes", said[:200])


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
