"""Does `mcdonald haze` bound the range of a dark object by its contrast in haze, in linear light?

Rendered frames through BT.709's transfer function: a sky, and an object whose own light is black (or half its sky's)
seen 5 km off through air of 20-km visibility (Koschmieder: its apparent light is the sky's (1 - e^(-sigma d)) plus its
own times e^(-sigma d)). A black object is bounded at its own range, a grey one beyond it (a bound, never short of it);
a black reference at 3 km in the frame gives sigma back; a bright object gets no bound; and the video's levels are not
light: a grey of 128 is about a quarter of white's.

    python3 tests/test_haze.py        # or: pytest tests/

No video data needed.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import haze  # noqa: E402

FAIL = []
W, H = 320, 240
SIGMA = haze.KOSCHMIEDER / 20000.0


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def video(lin):
    """Linear light (0-1) as BT.709 video levels (0-255)."""
    lin = np.clip(lin, 0, 1)
    v = np.where(lin < 0.018, 4.5 * lin, 1.099 * lin ** 0.45 - 0.099)
    return 255.0 * v


class Frames:
    def __init__(self, frames):
        self._f = frames
        self.n0, self.n1 = min(frames), max(frames)

    def grey(self, n):
        return self._f[n]


def scene(objects, sky=0.6, n=6):
    """A sky of linear light `sky` with a faint gradient, and discs (x, y, radius, own light as a share of the sky's,
    range m), each seen through the haze; a little noise in video levels."""
    yy, xx = np.mgrid[:H, :W].astype(float)
    frames = {}
    for i in range(1, n + 1):
        lin = sky * (1 + 0.02 * (yy / H - 0.5))
        for x, y, r, own, d in objects:
            t = math.exp(-SIGMA * d)
            disc = np.hypot(xx - x - 0.5 * i, yy - y) <= r
            lin = np.where(disc, sky * (1 - t) + own * sky * t, lin)
        frames[i] = (video(lin) + np.random.default_rng(i).normal(0, 0.5, (H, W))).astype(np.float32)
    return Frames(frames)


def track(x, y, n=6):
    return {i: (x + 0.5 * i, y) for i in range(1, n + 1)}


def test_levels_are_not_light():
    print("\nhaze: BT.709's levels against linear light")
    check(abs(float(haze.linear(128)) - 0.2615) < 0.005, "a grey of 128 is about a quarter of white's light, not half",
          f"{float(haze.linear(128)):.4f}")
    check(abs(float(haze.linear(video(np.array(0.37)))) - 0.37) < 1e-6, "and the two curves are each other's inverse")


def test_black_grey_bright_and_a_reference():
    print("\nhaze: 5 km off in 20-km visibility; black, grey and bright objects; a black reference at 3 km")
    clip = scene([(150, 120, 6, 0.0, 5000.0)])
    f = haze.measure(clip, track(150, 120), 12.0, visibility_m=20000.0)
    d = f.fields["bound_m"]
    check(d is not None and abs(d / 5000 - 1) < 0.04, "a black object: bounded at its own range", d and f"{d:.0f} m")
    check("factor of about 4" in f.result.get("range", ""), "said with its factor of four", f.result.get("range", ""))
    clip = scene([(150, 120, 6, 0.5, 5000.0)])
    f = haze.measure(clip, track(150, 120), 12.0, visibility_m=20000.0)
    d = f.fields["bound_m"]
    want = 5000 + math.log(2) / SIGMA
    check(d is not None and d > 5000 and abs(d / want - 1) < 0.05, "a grey one (half its sky's light): beyond its range, "
          "never short of it", d and f"{d:.0f} m against {want:.0f}")
    clip = scene([(150, 120, 6, 1.6, 5000.0)])
    f = haze.measure(clip, track(150, 120), 12.0, visibility_m=20000.0)
    check(f.fields["bound_m"] is None and f.no_power and "not darker" in f.no_power[0][1], "a bright one: no bound",
          f.no_power and f.no_power[0][1])
    clip = scene([(150, 120, 6, 0.0, 5000.0), (60, 60, 6, 0.0, 3000.0)])
    f = haze.measure(clip, track(150, 120), 12.0, reference=(1, 60.5, 60.0, 3000.0))
    s = f.fields["sigma_per_m"]
    check(s is not None and abs(s / SIGMA - 1) < 0.05, "the black reference gives sigma back", s and f"{s * 1000:.4f}/km "
          f"against {SIGMA * 1000:.4f}")
    check(f.fields["bound_m"] and abs(f.fields["bound_m"] / 5000 - 1) < 0.06, "and with it the object's bound",
          f.fields["bound_m"] and f"{f.fields['bound_m']:.0f} m")
    f = haze.measure(scene([(150, 120, 6, 0.0, 5000.0)]), track(150, 120), 12.0)
    check(f.no_power and "no extinction" in f.no_power[0][1], "neither visibility nor reference: no power, saying what to give",
          f.no_power and f.no_power[0][1])


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
