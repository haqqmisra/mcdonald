"""Does `mcdonald focus` bound the range of a thing as sharp as a point, and refuse one that is not?

Rendered frames: thirty points of the scene drawn 2 px wide at half their peak on a noisy ground, and the object either
one more such point or a flat-topped disc 9 px across (a near thing out of focus). The first gets a floor on range --
at k 900 px/deg, through diffraction at 4 um, the arithmetic checked by hand; with a pupil given, D over the disc -- and
the second none, its width said. A clip with no points in it: no blur, no bound. The disc's own arithmetic: what an
object's width leaves over the blur, never under half a blur.

    python3 tests/test_focus.py        # or: pytest tests/

No video data needed.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import focus  # noqa: E402

FAIL = []
W, H = 480, 320


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


class Frames:
    def __init__(self, frames):
        self._f = frames
        self.n0, self.n1 = min(frames), max(frames)
        self.H, self.W = H, W
        self.fps = 30.0

    def grey(self, n):
        return self._f[n]

    def rgb(self, n):
        return np.repeat(self._f[n][..., None], 3, axis=2)


def gauss(x, y, fwhm, amp):
    yy, xx = np.mgrid[:H, :W]
    s = fwhm / 2.3548
    return amp * np.exp(-0.5 * ((xx - x) ** 2 + (yy - y) ** 2) / s ** 2)


def disc(x, y, diam, amp):
    yy, xx = np.mgrid[:H, :W]
    from scipy import ndimage
    d = (np.hypot(xx - x, yy - y) <= diam / 2).astype(np.float32) * amp
    return ndimage.gaussian_filter(d, 2.0 / 2.3548)


def clip_of(obj, points=True, n=12):
    rng = np.random.default_rng(4)
    stars = [(rng.uniform(30, W - 30), rng.uniform(30, H - 30), rng.uniform(60, 120)) for _ in range(40)]
    stars = [s for s in stars if np.hypot(s[0] - 243, s[1] - 160) > 30][:30]      # none on the object's path
    frames, track = {}, {}
    for i in range(1, n + 1):
        g = 40.0 + np.random.default_rng(i).normal(0, 1.5, (H, W))
        if points:
            for x, y, a in stars:
                g += gauss(x + 0.3 * i, y, 2.0, a)
        ox, oy = 240.0 + 0.5 * i, 160.0
        g += obj(ox, oy)
        frames[i] = g.astype(np.float32)
        track[i] = (ox, oy)
    return Frames(frames), track


MASKS = {"blocks": np.zeros((H, W), bool), "graphics": np.zeros((H, W), bool)}


def test_the_disc():
    print("\nfocus: the widest disc a width can hide")
    check(abs(focus.disc_max_px(2.0, 2.0) - math.sqrt((2.3 ** 2) - 4)) < 1e-9, "as wide as a point: 1.15 x it, less the blur",
          f"{focus.disc_max_px(2.0, 2.0):.3f} px")
    check(focus.disc_max_px(1.0, 2.0) == focus.disc_max_px(2.0, 2.0), "narrower than a point reads as a point")
    check(abs(focus.disc_max_px(2.0, 2.0) - 1.135) < 0.01 and focus.disc_max_px(2.0, 2.0) >= focus.DISC_FLOOR * 2.0,
          "never under half a blur")


def test_a_sharp_object_is_far_and_a_disc_is_not_bounded():
    print("\nfocus: a sharp object among the scene's points, then a flat disc 9 px across")
    clip, trk = clip_of(lambda x, y: gauss(x, y, 2.0, 90.0))
    f = focus.measure(clip, trk, 900.0, 0.0, band="mwir", masks=MASKS)
    bl, b = f.fields["blur"], f.fields["bound"]
    check(bl["blur_fwhm_px"] is not None and abs(bl["blur_fwhm_px"] / 2.0 - 1) < 0.2, "the points' width, about 2 px",
          f"{bl['blur_fwhm_px']} px from {bl['spots']} spots")
    check(bl["resolved"] is False, "the object is as sharp as a point", f"{bl['object_fwhm_px']} px")
    if b["floor_m"]:
        want = 1.22 * 3e-6 / (math.radians(bl["blur_fwhm_px"] / 900) * math.radians(b["disc_px"] / 900))
        check(abs(b["floor_m"] / want - 1) < 1e-6 and b["floor_m"] > 1000, "a floor on range, by hand: 1.22 lambda / (b disc)",
              f"{b['floor_m'] / 1000:.2f} km against {want / 1000:.2f}")
        check("IF the sensor is focused far" in f.result.get("range", ""), "said with its condition", f.result.get("range", ""))
    else:
        check(False, "a floor on range", b["why"])
    p = focus.measure(clip, trk, 900.0, 0.0, pupil_m=0.1, masks=MASKS).fields["bound"]
    check(p["floor_m"] and abs(p["floor_m"] / (0.1 / math.radians(p["disc_px"] / 900)) - 1) < 1e-6,
          "with a 10-cm pupil given: D over the disc", p["floor_m"] and f"{p['floor_m'] / 1000:.2f} km")
    clip, trk = clip_of(lambda x, y: disc(x, y, 9.0, 60.0))
    f = focus.measure(clip, trk, 900.0, 0.0, band="mwir", masks=MASKS)
    check(f.fields["bound"]["floor_m"] is None and f.no_power and "wider than a point" in f.no_power[0][1],
          "a disc 9 px across: no bound, and its width said", f.no_power and f.no_power[0][1])
    clip, trk = clip_of(lambda x, y: gauss(x, y, 2.0, 90.0), points=False)
    f = focus.measure(clip, trk, 900.0, 0.0, masks=MASKS)
    check(f.no_power and "blur is not measured" in f.no_power[0][1], "no points in the scene: no blur, no bound",
          f.no_power and f.no_power[0][1])


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
