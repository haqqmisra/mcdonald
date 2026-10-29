"""Does `mcdonald streak` read the exposure from a dash, and a flicker far above the frame rate from its beads?

Rendered frames: a point crossing the picture at 51 px a frame, drawn through a 2-px blur while a 180-degree shutter is
open (half of each frame), steady or blinking at 360 Hz (12 times a frame, its beads 4.25 px apart along the dash).
The steady dash gives the exposure (half a frame, 16.7 ms at 30 fps) and no flicker; the blinking one the same exposure
and beads at 360 Hz; a point crossing at 2 px a frame draws no dash long enough to read.

    python3 tests/test_streak.py        # or: pytest tests/

No video data needed.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import streak  # noqa: E402

FAIL = []
W, H = 400, 240
FPS = 30.0


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


def render(v=(51.0, 10.0), share=0.5, hz=None, n=14, blur=2.0, amp=600.0):
    """Frames of a point moving v px a frame, drawn while the shutter is open (`share` of a frame), its light steady or
    1 + 0.8 sin(2 pi hz t); the track at the middle of each exposure."""
    s = blur / 2.3548
    frames, track = {}, {}
    steps = 400
    for i in range(1, n + 1):
        g = 30.0 + np.random.default_rng(i).normal(0, 1.5, (H, W))
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


def test_the_exposure_and_a_steady_body():
    print("\nstreak: a steady point at 51 px a frame under a 180-degree shutter")
    clip, trk = render()
    f = streak.measure(clip, trk, blur_px=2.0)
    e = f.fields.get("exposure_share")
    check(e is not None and abs(e - 0.5) < 0.03, "the exposure: half a frame", e and f"{e:.3f} ({f.fields['exposure_s'] * 1000:.1f} ms)")
    check(f.fields.get("bead_p") is not None and f.fields["bead_p"] >= streak.FALSE_ALARM, "no flicker in a steady dash",
          f"ratio {f.fields.get('bead_ratio', 0):.2f}, false alarm {f.fields.get('bead_p', 0):.2f}")


def test_a_flicker_far_above_the_frame_rate():
    print("\nstreak: the same point blinking at 360 Hz (beads 4.25 px apart)")
    clip, trk = render(hz=360.0)
    f = streak.measure(clip, trk, blur_px=2.0)
    hz, p = f.fields.get("bead_hz"), f.fields.get("bead_p")
    check(hz is not None and abs(hz / 360 - 1) < 0.1 and p < streak.FALSE_ALARM, "beads at 360 Hz, standing out",
          f"{hz and round(hz)} Hz, ratio {f.fields.get('bead_ratio', 0):.1f}, false alarm {p}, every "
          f"{f.fields.get('bead_spacing_px', 0):.2f} px")
    check("flicker inside the frame" in f.result and "Hz" in f.result["flicker inside the frame"], "and said",
          f.result.get("flicker inside the frame", ""))


def test_a_slow_point_draws_no_dash():
    print("\nstreak: a point crossing at 2 px a frame")
    clip, trk = render(v=(2.0, 0.0))
    f = streak.measure(clip, trk, blur_px=2.0)
    check(f.no_power and "under 3 blurs" in f.no_power[0][1], "no light curve: the dash is under three blurs",
          f.no_power and f.no_power[0][1])


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
    got, two = (streak.measure(scene, trk, x).fields["exposure_share"] for x in (b, 2.0))
    check(abs(got - 0.5) < 0.04 and abs(two - 0.5) < 0.04,
          "a dash three blurs long: half a frame at the picture's own blur and at an assumed 2 px alike (its half-peak ends "
          "are the motion's; less a blur, it read 0.34)", f"{got:.3f} at {b:.2f} px, {two:.3f} at 2 px")
    frames, trk = render(v=(10.0, 0.0), blur=3.5)
    short = streak.measure(frames, trk, 3.5)
    e, L = short.fields["exposure_share"], short.fields["length_px"]
    check(abs(e - 0.5) < 0.08 and short.no_power and (L - 3.5) / 10.0 < 0.3,
          "a dash under twice the blur long: still half a frame, the blur taken out exactly (less a blur, it reads "
          f"{(L - 3.5) / 10.0:.2f}); no light curve", f"{e:.3f} from a dash {L:.1f} px long")


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
