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


def pillbox(diam):
    """A defocus disc of diameter `diam` px, normalised, drawn on a 4x finer grid and binned."""
    r = int(np.ceil(diam / 2)) + 1
    yy, xx = (np.mgrid[-4 * r:4 * r + 4, -4 * r:4 * r + 4] + 0.5) / 4.0 - 0.5
    k = (np.hypot(xx, yy) <= diam / 2).astype(float)
    k = k.reshape(2 * r + 1, 4, 2 * r + 1, 4).sum(axis=(1, 3))
    return k / k.sum()


def dark_clip(diam, defocus, bg=150.0, black=0.0, n=12, points=True):
    """A scene at `bg` with thirty bright points 2 px wide, and a disc at `black` `diam` px across moving 0.5 px a
    frame, drawn through a defocus disc `defocus` px across (none for 0) and then the points' blur."""
    from scipy import ndimage, signal
    rng = np.random.default_rng(4)
    stars = [(rng.uniform(30, W - 30), rng.uniform(30, H - 30), rng.uniform(60, 100)) for _ in range(40)]
    stars = [s for s in stars if np.hypot(s[0] - 243, s[1] - 160) > 40][:30]
    frames, track = {}, {}
    yy, xx = np.mgrid[:H, :W]
    for i in range(1, n + 1):
        ox, oy = 240.0 + 0.5 * i, 160.0
        sub = np.zeros((H, W))
        hi = (np.mgrid[:4 * 81, :4 * 81] + 0.5) / 4.0 - 0.5          # the disc on a 4x finer grid, 81 px about it
        cx, cy = ox - (int(ox) - 40), oy - (int(oy) - 40)
        d = (np.hypot(hi[1] - cx, hi[0] - cy) <= diam / 2).astype(float).reshape(81, 4, 81, 4).mean(axis=(1, 3))
        if defocus:
            d = signal.fftconvolve(d, pillbox(defocus), mode="same")
        sub[int(oy) - 40:int(oy) + 41, int(ox) - 40:int(ox) + 41] = d
        g = bg - (bg - black) * sub
        g = ndimage.gaussian_filter(g, 2.0 / 2.3548)
        for x, y, a in (stars if points else []):
            g += gauss(x + 0.3 * i, y, 2.0, a)
        g += np.random.default_rng(i).normal(0, 1.5, (H, W))
        frames[i] = np.clip(g, 0, 255).astype(np.float32)
        track[i] = (ox, oy)
    return Frames(frames), track


def test_an_edge_bounds_the_disc_a_resolved_object_hides():
    print("\nfocus: a black disc 14 px across in focus, the same out of focus by 8 px, and a 4-px thing out of focus by 12")
    clip, trk = dark_clip(14.0, 0)
    f = focus.measure(clip, trk, 900.0, 0.0, masks=MASKS, dark=True, ground_m_per_px=0.05)
    e, dc = f.fields.get("edge") or {}, f.fields.get("disc") or {}
    check(f.fields["blur"]["resolved"] is True and e.get("sigma_px") is not None, "wider than a point, and its edge read",
          f"object {f.fields['blur']['object_fwhm_px']:.1f} px, edge sigma {e.get('sigma_px')}")
    check(e.get("sigma_px") is not None and abs(e["sigma_px"] / (2.0 / 2.3548) - 1) < 0.25,
          "in focus: its edge as sharp as the points (sigma 0.85)", f"{e.get('sigma_px')}")
    check(dc and dc["depth_share"] > 0.9, "its core all the way to black", f"{dc and dc['depth_share']:.2f}")
    check(dc and dc["blur_as_points"] < 3.0 and f.fields["bound"]["floor_m"] is not None,
          "a defocus disc under 3 px if the camera blurs as its points, and a floor on range",
          f"{dc and dc['blur_as_points']:.2f} px, {f.fields['bound']['floor_m']} m")
    check("r/R" in f.result and dc.get("r_over_R"), "r/R given with a ground scale", f.result.get("r/R", ""))
    clip, trk = dark_clip(6.0, 0)
    f = focus.measure(clip, trk, 900.0, 0.0, masks=MASKS, dark=True)
    e, dc = f.fields.get("edge") or {}, f.fields.get("disc") or {}
    check(f.fields["blur"]["resolved"] is not False and dc and dc["blur_as_points"] < 3.0,
          "a black disc 6 px across, clipped (width not known from it): read by its edge, a disc under 3 px",
          f"resolved {f.fields['blur']['resolved']}, clipped {f.fields['blur']['object_clipped']}, "
          f"edge sigma {e.get('sigma_px')}, disc {dc and dc['blur_as_points']:.2f} px")
    clip, trk = dark_clip(14.0, 0, points=False)
    f = focus.measure(clip, trk, 900.0, 0.0, masks=MASKS, dark=True, ground_m_per_px=0.05)
    dc = f.fields.get("disc") or {}
    check(dc and dc["blur_as_points"] is None and dc["assuming_nothing"] < 5.0 and f.fields["bound"]["floor_m"] is None
          and not f.no_power and "r/R" in f.result,
          "no points in the scene (ground streaming past): the edge read all the same, the bound assuming nothing alone, "
          "no floor in metres", dc and f"{dc['assuming_nothing']:.2f} px; {f.result.get('r/R', '')}")
    for diam, b in ((14.0, 8.0), (4.0, 12.0)):
        clip, trk = dark_clip(diam, b)
        f = focus.measure(clip, trk, 900.0, 0.0, masks=MASKS, dark=True)
        e, dc = f.fields.get("edge") or {}, f.fields.get("disc") or {}
        ok = bool(dc) and dc["blur_as_points"] >= b and dc["assuming_nothing"] >= b
        check(ok, f"a {diam:.0f}-px thing out of focus by {b:.0f} px: both bounds at least {b:.0f} px",
              dc and f"edge sigma {e['sigma_px']:.2f}, core {dc['depth_share']:.0%} to black, "
                     f"bounds {dc['blur_as_points']:.1f} / {dc['assuming_nothing']:.1f} px")


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
