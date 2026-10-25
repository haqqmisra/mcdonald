"""Does this install measure correctly? Synthetic scenes with known answers.

These tests ship with the package and need no video data: each builds a scene
whose true answer is known by construction, then checks the library recovers
it. Run them after installing, before trusting a number from a real clip.

    python3 tests/test_measurement.py        # or: pytest tests/

The separate tests/test_golden.py checks the published results of real clips,
and needs the corpus.
"""
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import catalog, clip as clipmod, forensics as vf  # noqa: E402

RNG = np.random.default_rng(20260919)
FAIL = []


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def isotropic(h, w, scale=3.0):
    """Cloud-like texture: smoothed noise, no preferred direction."""
    from scipy import ndimage
    return ndimage.gaussian_filter(RNG.normal(0, 1, (h, w)), scale) * 400 + 128


def striated(h, w):
    """Sea-like texture: wave crests along one axis, so the correlation peak is
    much flatter along the crests (the aperture problem, on purpose)."""
    from scipy import ndimage
    a = ndimage.gaussian_filter(RNG.normal(0, 1, (h, w)), (1.0, 9.0))
    return a * 700 + 128


def roll(a, dx, dy):
    return np.roll(np.roll(a, dy, axis=0), dx, axis=1)


# ---------------------------------------------------------------- registration
def test_recovers_a_known_shift():
    """The ruler itself: shift a real-looking scene by a known amount."""
    print("\nregistration: a known rigid shift")
    base = isotropic(600, 900)
    bad = np.zeros(base.shape, bool)
    for dx, dy in ((20, 0), (-37, 11), (5, -23)):
        f = vf.shift_field(base, roll(base, dx, dy), bad, bad, tpl=128, stride=96, reach=120)
        con = vf.consensus(vf.good(f)[:, 3:5])
        ok = con is not None and abs(con[0][0] - dx) < 0.5 and abs(con[0][1] - dy) < 0.5
        check(ok, f"recovers ({dx:+d}, {dy:+d})",
              f"got ({con[0][0]:+.2f}, {con[0][1]:+.2f}) from {con[1]} templates" if con else "no consensus")


def test_two_layers_are_not_averaged():
    """The PR144 failure: two backgrounds at different ranges. A single
    consensus would return a blend of the two and name neither."""
    print("\nlayers: two backgrounds moving differently")
    h, w = 600, 900
    scene_a, scene_b = striated(h, w), isotropic(h, w)
    split = 300
    f0 = np.vstack([scene_b[:split], scene_a[split:]])
    f1 = np.vstack([roll(scene_b, 12, 0)[:split], roll(scene_a, 40, 0)[split:]])
    bad = np.zeros(f0.shape, bool)
    g = vf.good(vf.shift_field(f0, f1, bad, bad, tpl=128, stride=64, reach=120))
    lay = vf.layers_of(g)
    check(lay["groups"] == 2, "two motion groups, not one blended rate",
          f"groups={lay['groups']}, gap={lay.get('group_gap', 0):.1f} px")
    iso, stri = lay["isotropic"], lay["striated"]
    check(iso is not None and abs(iso[0][0] - 12) < 2, "the isotropic (cloud-like) layer",
          f"{iso[0][0]:+.1f} px from {iso[1]} templates (truth +12)" if iso else "not found")
    check(stri is not None and abs(stri[0][0] - 40) < 2, "the striated (sea-like) layer",
          f"{stri[0][0]:+.1f} px from {stri[1]} templates (truth +40)" if stri else "not found")
    if iso and stri:
        check(abs((stri[0][0] - iso[0][0]) - 28) < 3, "layer against layer",
              f"{stri[0][0] - iso[0][0]:.1f} px apart (truth 28)")
    mixed = vf.consensus(g[:, 3:5])
    if mixed is not None:
        print(f"         (a single consensus over both would have said {mixed[0][0]:+.1f} px "
              "-- a rate against neither layer)")


def test_a_slow_scene_is_not_held_by_a_pattern_on_the_sensor():
    """PR135 (2026-09-22, an agent's run): an island drifting 10 px/s behind fixed speckle
    and column stripes. Over 5 frames the scene moves 1.6 px, inside the +-4 px left out
    about zero, so zero shift is allowed -- and the pattern, which does not move, holds
    the estimate there: `layers` read 0.3 px/s for the scene, and the island's own hot
    building 10 px/s "against the background". A pair held still is measured again over
    a second. A scene that is still is still over a second too, and is said to be."""
    print("\nlayers: a slow scene behind a pattern that stays on the sensor")
    from scipy import ndimage
    from mcdonald import layers
    h, w = 480, 720
    scene = isotropic(h + 80, w + 80, scale=4.0)
    pattern = RNG.normal(0, 1, (h, w)) * 6 + np.tile(RNG.normal(0, 1, w) * 4, (h, 1))

    class Drifting:
        H, W, n0, n1, fps = h, w, 1, 40, 30.0
        v = (-0.30, -0.14)                                # px a frame: 9 and 4 px/s

        def rgb(self, n):
            g = ndimage.shift(scene, (self.v[1] * n, self.v[0] * n), order=3)[40:40 + h, 40:40 + w] * 0.15 + pattern
            return np.repeat(g[:, :, None], 3, 2)

    none = np.zeros((h, w), bool)
    for v, name in (((-0.30, -0.14), "drifting"), ((0.0, 0.0), "still")):
        clip = Drifting()
        clip.v = v
        layers._G.update(clip=clip, masks=dict(blocks=none, graphics=none, colour=True), rows=None, k=5, reach=245,
                         pos=None, longer=30)
        ga, ba = layers._bad(10)
        gb, bb = layers._bad(15)
        before, still = vf.shift_field_auto(ga, gb, ba, bb, reach=245)
        b = vf.consensus(vf.good(before)[:, 3:5])
        f = layers._pair(10)
        c = vf.consensus(vf.good(f)[:, 3:5])
        truth = 5 * np.array(v)
        if name == "drifting":
            check(still and b is not None and np.hypot(*(b[0] - truth)) > 1.0,
                  "over 5 frames alone the pattern holds a drifting scene near zero (the bug, drawn)",
                  f"({b[0][0]:+.2f}, {b[0][1]:+.2f}) px, truth ({truth[0]:+.2f}, {truth[1]:+.2f})" if b else "no consensus")
            check(set(f[:, -2]) == {layers.AGAIN} and c is not None and np.hypot(*(c[0] - truth)) < 0.15,
                  "measured again over a second, it is the scene's shift, given as a 5-frame shift",
                  f"({c[0][0]:+.2f}, {c[0][1]:+.2f}) px from {c[1]} templates" if c else "no consensus")
        else:
            check(set(f[:, -2]) == {layers.STILL} and c is not None and np.hypot(*c[0]) < 0.1,
                  "a scene that is still is still over a second too, and is marked so",
                  f"({c[0][0]:+.2f}, {c[0][1]:+.2f}) px" if c else "no consensus")


def test_the_zncc_window_variance_is_summed_in_float64():
    """The audit of 2026-09-26 (§4.5): shift_field normalised each placement by a window variance
    summed in float32 as E[x²] - E[x]², which cancels catastrophically where a window is nearly
    flat, and a flat-sky template then matched rounding noise. The whole frame's summed-area
    tables in float64 give the same box sums where float32 was fine, and the true variance
    where it was not."""
    print("\nshift_field: the window variance in float64")
    rng = np.random.default_rng(3)
    a = rng.normal(0, 1, (300, 400)).astype(np.float32)
    box, alt = vf.boxsum(a, 128, 128), vf.box_of(vf.integral(a), 0, 300, 0, 400, 128, 128)
    check(box.shape == alt.shape and np.allclose(box, alt, rtol=0, atol=1e-3 * np.abs(box).max()),
          "box sums from the summed-area table are the direct ones", f"largest difference {np.abs(box - alt).max():.2g}")
    # A band-passed frame with texture in one part and sky, flat but for faint noise, in the other: the
    # running sums over the whole window reach the texture's millions, where a float32 step is 1 or 2,
    # and a flat patch's own sum of squares (a fraction of one) comes out as anything. A nearly flat
    # template -- sky, as in frame a -- then matches sky anywhere, with peaks far above 1; in float64 it
    # is found where it is, with a peak of 1 and nothing above it.
    img = np.zeros((400, 400), np.float32)
    img[:, :200] = rng.normal(0, 30, (400, 200))
    img[:, 200:] = rng.normal(0, 0.01, (400, 200))
    tpl_ = img[170:234, 290:354].copy()
    S1, S2 = vf.integral(img), vf.integral(img.astype(np.float64) ** 2)
    s1, s2 = vf.box_of(S1, 0, 400, 0, 400, 64, 64), vf.box_of(S2, 0, 400, 0, 400, 64, 64)
    good_norm = np.sqrt(np.maximum(s2 - s1 * s1 / 4096, 1e-6))
    c64, c32 = vf.zncc(tpl_, img, norm=good_norm), vf.zncc(tpl_, img)
    at64, at32 = tuple(map(int, np.unravel_index(np.argmax(c64), c64.shape))), tuple(map(int, np.unravel_index(np.argmax(c32), c32.shape)))
    check(at64 == (170, 290) and abs(c64[170, 290] - 1.0) < 1e-3 and (c64 <= 1.001).all(),
          "with the sums in float64 a sky template is found where it is, with a peak of 1 and nothing above it",
          f"peak {c64.max():.4f} at {at64}")
    check(not (at32 == (170, 290) and abs(c32[170, 290] - 1.0) < 1e-3 and (c32 <= 1.001).all()),
          "summed in float32 it is not (the trap, drawn)", f"peak {c32.max():.3g} at {at32}")
    # on textured frames the two agree, and shift_field's rows are what they were
    base = isotropic(400, 600, scale=3.0) * 40
    bad = np.zeros(base.shape, bool)
    f = vf.shift_field(base, roll(base, 7, -3), bad, bad, tpl=128, stride=96, reach=60)
    g = vf.good(f)
    check(len(g) >= 4 and np.allclose(g[:, 3:5], (7, -3), atol=0.05),
          "and a drawn shift is found to 0.05 px, as before", f"{len(g)} templates, median ({np.median(g[:, 3]):+.3f}, {np.median(g[:, 4]):+.3f})")


def test_held_still_pairs_share_their_second_pass():
    """2026-09-26 (the audit's §3.5, §5.4): a pair held still over k frames is measured again over
    a second; consecutive still pairs used to each get their own second pass, one frame apart -- 21
    passes of 20 s on PR113 380-440, 70 % of the stage. A window starts every L/2 frames now and is
    shared by the pairs nearest it; every pair still lies well inside its window."""
    print("\nlayers: held-still pairs share a window")
    from mcdonald import layers
    k, L, n0, n1 = 5, 30, 380, 440
    starts = {a: layers.window_start(a, k, L, n0, n1) for a in range(n0, n1 - k + 1)}
    check(sorted(set(starts.values())) == [380, 390, 405, 410], "PR113 380-440: four windows for 56 pairs", str(sorted(set(starts.values()))))
    inside = all(s <= a and a + k <= s + L for a, s in starts.items())
    away = {a: s for a, s in starts.items() if n0 + L / 4 <= a + k / 2 <= n1 - L / 4}      # where the clip's ends do not move the window
    centred = max(abs((a + k / 2) - (s + L / 2)) for a, s in away.items())
    check(inside and centred <= L / 4 + 0.5, "each pair inside its window, and away from the clip's ends within L/4 of its middle",
          f"farthest from the middle {centred:.1f} frames")
    check(layers.window_start(10, 5, 30, 1, 40) == 1 and layers.window_start(35, 5, 30, 1, 40) == 10,
          "a short clip's windows stay inside it")


def test_integrity_keeps_a_frame_for_the_next_pair():
    """The audit's §4.4: integrity's per-frame background reads, masks and band-passes every frame
    twice, once as the second frame of a pair and once as the first of the next. A worker keeps the
    last frame; the numbers are the same arrays either way."""
    print("\nintegrity: a frame kept for the next pair")
    from scipy import ndimage
    from mcdonald import integrity
    h, w = 480, 720
    scene = isotropic(h + 80, w + 80, scale=4.0) * 40

    class Drifting:
        H, W, n0, n1, fps = h, w, 1, 40, 30.0

        def rgb(self, n):
            g = ndimage.shift(scene, (-2.5 * n, -6.0 * n), order=3)[40:40 + h, 40:40 + w]      # 6 px a frame: outside the zero zone, inside the reach
            return np.repeat(g[:, :, None], 3, 2)
    none = np.zeros((h, w), bool)
    integrity._G.update(clip=Drifting(), masks=dict(blocks=none, graphics=none, colour=True), rows=None, reach=65, zero=4, pos=None)

    def cold(a):
        integrity._G.pop("frame_n", None)
        return integrity._pair1(a)
    fresh = [cold(a) for a in (10, 11, 12)]
    integrity._G.pop("frame_n", None)
    warm = [integrity._pair1(a) for a in (10, 11, 12)]
    same = all(f[0] == w_[0] and all((f[1][c] is None) == (w_[1][c] is None) and (f[1][c] is None or (np.array_equal(f[1][c][0], w_[1][c][0]) and f[1][c][1] == w_[1][c][1]))
                                   for c in f[1]) for f, w_ in zip(fresh, warm))
    kept = integrity._G.get("frame_n") == 13
    check(same and kept and fresh[0][1]["all"] is not None and np.allclose(fresh[0][1]["all"][0], (-6.0, -2.5), atol=0.1),
          "three pairs in a row, cold and with the last frame kept: the same numbers, and the drawn drift",
          f"{fresh[0][1]['all'][0] if fresh[0][1]['all'] else None}; kept frame {integrity._G.get('frame_n')}")


def test_integrity_sees_symbology_drawn_frame_by_frame():
    """FLIR1 (2026-10-20): integrity said "the object never crosses the symbology" while the object crossed the tracking
    gate's bars and passed under a readout. A mask made from the whole clip holds only what is drawn in one place
    throughout; a gate that moves, and text that is drawn for a stretch, are found in each frame (`forensics.ridges`).
    Drawn at 352 x 240: a crosshair that never moves (the symbology's level), a gate that follows the object for ten
    frames and then stays at the boresight while the object drifts across its bars, and a readout drawn for frames
    10-30 that the object passes under. Each is drawn on top of the object, as a sensor draws it, or under it, as an
    object pasted on afterwards would be; and once white on a white-hot object, which decides nothing."""
    print("\nintegrity: symbology drawn frame by frame -- a moving gate and a readout")
    from mcdonald import integrity
    H, W, LV = 240, 352, 235.0
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[:H, :W]
    cross = ((np.abs(yy - 40) <= 0) & (np.abs(xx - 40) <= 12)) | ((np.abs(xx - 40) <= 0) & (np.abs(yy - 40) <= 12))
    seg = {"a": (0, 0, 1, 0), "b": (1, 0, 1, 1), "c": (1, 1, 1, 2), "d": (0, 2, 1, 2), "e": (0, 1, 0, 2), "f": (0, 0, 0, 1),
           "g": (0, 1, 1, 1)}                         # a seven-segment digit's strokes, corners in units of the glyph

    def digit(x0, y0, on, w=7, h=8):
        m = np.zeros((H, W), bool)
        for k in on:
            a, b, c, d = seg[k]
            ya, yb = sorted((y0 + b * h, y0 + d * h))
            xa, xb = sorted((x0 + a * w, x0 + c * w))
            m[ya:yb + 1, xa:xb + 1] = True
        return m

    class Drawn:
        n0, n1, fps = 1, 40, 30.0

        def __init__(self, kind, on_top, obj_level, bg):
            self.W, self.H = W, H
            self.kind, self.on_top, self.obj, self.bg = kind, on_top, obj_level, bg
            self.noise = {n: rng.normal(0, 3.0, (H, W)) for n in range(1, 41)}
            self.trk = {}
            for n in range(1, 41):
                self.trk[n] = (200.0 - 1.25 * (n - 1), 120.0) if kind == "gate" else (128.0 - 1.4 * (n - 1), 151.0)

        def grey(self, n):
            x, y = self.trk[n]
            p = np.exp(-0.5 * (((xx - x) / 2.5) ** 2 + ((yy - y) / 1.5) ** 2))
            ov = cross.copy()
            if self.kind == "gate":
                gx = x if n <= 10 else 177.0
                for bx in (gx - 7, gx + 7):
                    ov |= (np.abs(xx - bx) <= 0.6) & (np.abs(yy - 120) <= 12)
            elif 10 <= n <= 30:
                ov |= digit(98, 144, "abcdefg" if n < 20 else "abcdfg")
            f = self.bg + self.noise[n]
            if self.on_top:
                f = f * (1 - p) + self.obj * p
                f[ov] = LV
            else:
                f[ov] = LV
                f = f * (1 - p) + self.obj * p
            return f

        def rgb(self, n):
            return np.repeat(self.grey(n)[:, :, None], 3, 2).astype(np.float32)

    def verdict(kind, on_top, obj, bg, dark):
        c = Drawn(kind, on_top, obj, bg)
        masks = vf.static_masks(c)
        o = integrity.Obj(c, c.trk, 6.0, dark)
        old = integrity._overlay_static(o, masks)
        return integrity.t_overlay(o, masks), old, masks
    (v, txt, d), old, masks = verdict("gate", True, 10.0, 110.0, True)
    lvl = vf.overlay_level(masks)
    check(lvl is not None and abs(lvl - LV) < 10 and vf.overlay_polarity(masks) == 1 and not masks["graphics_raw"][120, 170],
          "the fixed crosshair gives the symbology's level, brighter than the sky; the gate, which moves, is in no "
          "whole-clip mask", f"{lvl}")
    check(old[1] == "the object never crosses the symbology" and v == "PASS" and "lines drawn frame by frame" in txt,
          "a gate drawn on top of a dark object it crosses: the whole-clip mask misses it, the frame's own finds it on top",
          txt)
    v, txt, d = verdict("gate", False, 10.0, 110.0, True)[0]
    check(v == "FLAG" and "lines drawn frame by frame" in txt, "the same gate under the object, as a paste would leave it: FLAG",
          txt)
    v, txt, d = verdict("gate", True, 250.0, 40.0, False)[0]
    check(v == "NO POWER" and "crosses lines drawn frame by frame" in txt and "same side" in txt,
          "a white-hot object crossing white bars (FLIR1): it crosses them, and on the same side of the picture's level "
          "that decides nothing", txt)
    (v, txt, d), old, _ = verdict("text", True, 10.0, 110.0, True)
    check(old[1] == "the object never crosses the symbology" and v == "PASS" and "drawn f" in txt,
          "a readout drawn for frames 10-30 over the object: missed by the whole-clip mask, found on top", txt)
    v, txt, d = verdict("text", False, 10.0, 110.0, True)[0]
    check(v == "FLAG" and "drawn f" in txt, "the readout under the object: FLAG", txt)


def test_the_mark_gate_grows_with_the_spot_size():
    """2026-09-27: a spot may sit 6 px from a mark for spots up to 30 px, a fifth of the size above it. Find's
    mark on a 74-px disc (PR055 enlarged three times) was 13 px from its centre, and under 6 px no size
    could qualify. The recorded clips, whose objects are 7-24 px, are unchanged by it: their sizes stay under
    the knee, and the sweep only reaches a large size by climbing through the small ones."""
    print("\nlink: the gate at the marks grows with the spot size")
    from mcdonald import autolink
    gates = {s: autolink.mark_gate(s) for s in autolink.SIZES}
    check(all(gates[s] == 6.0 for s in (5, 9, 15, 21)) and abs(gates[31] - 6.2) < 1e-9 and gates[45] == 9.0 and abs(gates[71] - 14.2) < 1e-9,
          "6 px up to 21, 6.2 at 31, 9 at 45, 14.2 at 71", str(gates))
    check(autolink.mark_gate(9, tol=10.0) == 10.0 and abs(autolink.mark_gate(71, tol=10.0) - 14.2) < 1e-9, "a wider tol given still wins where it is wider")


def test_a_streak_is_followed_by_its_motion():
    """PR43 (Jacob, 2026-09-27): a thing drawn out into a dash by its own speed, which Find sees and no spot size
    holds. When the sweep finds no size, the link follows the marks' motion: each frame less the median of its
    four neighbours on its background, a peak at least 5 x the noise and a quarter of the object's own, from
    each mark both ways. Drawn: the dash crosses 20 px a frame over ground full of specks; the marks sit 8-10 px
    off it, as Find's did; the disc's own link does not take this way."""
    print("\nautolink: a streak, followed by its motion")
    from mcdonald import autolink
    clip = StreakClip()
    none = np.zeros((clip.H, clip.W), bool)
    masks = dict(blocks=none, graphics=none, colour=True)
    marks = {8: (clip.truth(8)[0] + 3, clip.truth(8)[1] + 8), 20: (clip.truth(20)[0] - 4, clip.truth(20)[1] - 8)}
    steps = list(autolink.link_from_marks(clip, marks, masks=masks, procs=0, max_gap=6))
    L = steps[-1]
    check(L.done and L.track and set(L.source.values()) == {"motion"} and any(s.stage == "motion" for s in steps),
          "no spot size holds it, and the link follows its motion instead", L.say[:90])
    off = _off(L.track, clip) if L.track else None
    check(L.track and len(L.track) >= 20 and min(L.track) <= 4 and max(L.track) >= 23 and off < 2.5,
          "the track covers the frames it is on, to the dash's centre within 2.5 px",
          f"{len(L.track)} frames {min(L.track) if L.track else '-'}–{max(L.track) if L.track else '-'}, {off if off is None else round(off, 2)} px off at worst")
    check(L.say.startswith("followed by its motion, not as a spot") and "drawn out along its path" in L.say and L.dark is False
          and 5 <= L.size <= 20 and L.worst() is not None and L.worst() < 12,
          "and says so, bright, about how wide, and how close to the marks", f"size {L.size}, worst {L.worst()}")
    with tempfile.TemporaryDirectory() as td:
        path = autolink.write_track_csv(f"{td}/t_autotrack.csv", L, "x.mp4", clip.fps)
        head = [ln for ln in open(path, encoding="utf-8") if ln.startswith("#")]
        rows = vf.read_track(path)
        check(any("followed by its motion" in ln for ln in head) and len(rows) == len(L.track),
              "the track file says how it was followed, and reads back through the package's own reader")
    disc = list(autolink.link_from_marks(PlantedClip(), {2: PlantedClip().truth(2), 5: PlantedClip().truth(5)}, masks=masks, procs=0, max_gap=6))
    check(disc[-1].track and "motion" not in set(disc[-1].source.values()) and not any(s.stage == "motion" for s in disc),
          "a spot is still linked as a spot, without this way")
    beside = {8: (clip.truth(8)[0], clip.truth(8)[1] + 20), 20: (clip.truth(20)[0], clip.truth(20)[1] - 20)}
    B = list(autolink.link_from_marks(clip, beside, masks=masks, procs=0, max_gap=6))[-1]
    check(not B.track and "Nothing was linked" in B.say, "marks 20 px beside the dash have nothing under them, by motion too: nothing is linked", B.say[:70])
    one_off = {8: marks[8], 20: (clip.truth(20)[0], clip.truth(20)[1] - 20)}
    O = list(autolink.link_from_marks(clip, one_off, masks=masks, procs=0, max_gap=6))[-1]
    check(not O.track and "the mark on frame 20 has no motion within" in O.say, "and one mark beside it is enough to refuse, naming the mark", O.say[-120:])


def test_propose_measures_a_slow_background_again():
    """The same trap in `propose` (2026-09-23): its background shift is a phase correlation
    over K frames either side, kept only if it fits better than none. On PR135 150-320 every
    frame but one was held still, and each proposal's "against the background" was against
    the screen. A background held still, or nearly, over K frames is measured again over a
    second, where no shift is left out and what is found must stand clear of the next peak;
    a still scene finds nothing clear there, and stays still."""
    print("\npropose: a slow background behind a pattern that stays on the sensor")
    from scipy import ndimage
    from mcdonald import propose
    h, w = 480, 720
    scene = isotropic(h + 80, w + 80, scale=4.0)
    pattern = RNG.normal(0, 1, (h, w)) * 6 + np.tile(RNG.normal(0, 1, w) * 4, (h, 1))

    class Drifting:
        H, W, n0, n1, fps = h, w, 1, 40, 30.0
        v = (-0.30, -0.14)

        def grey(self, n):
            return ndimage.shift(scene, (self.v[1] * n, self.v[0] * n), order=3)[40:40 + h, 40:40 + w] * 0.15 + pattern

    ok = np.ones((h, w), bool)
    for v, name in (((-0.30, -0.14), "drifting"), ((0.0, 0.0), "still")):
        clip = Drifting()
        clip.v = v
        g0 = clip.grey(20)
        (_, sa), (_, sb) = propose.onto(g0, clip.grey(18), ok), propose.onto(g0, clip.grey(22), ok)
        k2 = np.subtract(sb, sa) / 4
        again = propose.still_again(clip, 20, ~ok, 2)
        if name == "drifting":
            check(np.hypot(*(k2 - v)) > 0.1, "over 2 frames either side the pattern holds a drifting background (the bug, drawn)",
                  f"({k2[0]:+.3f}, {k2[1]:+.3f}) px/frame, truth ({v[0]:+.2f}, {v[1]:+.2f})")
            check(again is not None and np.hypot(*np.subtract(again, v)) < 0.03,
                  "measured again over a second, it is the background's speed",
                  f"{again and tuple(round(a, 3) for a in again)} px/frame")
        else:
            check(again is None and np.hypot(*k2) < 0.02, "a still background finds nothing clear over a second, and stays still",
                  f"over 2 frames ({k2[0]:+.3f}, {k2[1]:+.3f}) px/frame")


def test_a_scrolling_tape_is_recognised_and_a_flock_is_not():
    """PR113's heading tape: numbers and ticks sliding across the screen together, which `propose`
    only marked down as company (a flow). Four marks in a row along their own motion are a tape
    and are said to be one; four things in a cluster going the same way -- a flock, PR135's group
    -- are not; nor is one thing alone."""
    print("\npropose: a scrolling tape, said to be one")
    from mcdonald import propose

    def thing(x0, y0, v, n0=10, n=12):
        return propose.Proposal(track={k: (x0 + v[0] * (k - n0), y0 + v[1] * (k - n0)) for k in range(n0, n0 + n)}, dark=False,
                                size_px=6.0, velocity=v, against_background=float(np.hypot(*v)), stands_out=2.0, path_px=100.0,
                                resid_px=0.5, company=0)
    tape = [thing(200 + 60 * i, 900, (-8.0, 0.0)) for i in range(5)]
    flock = [thing(700 + dx, 300 + dy, (5.0, -3.0)) for dx, dy in ((0, 0), (14, 9), (-11, 17), (22, -8))]
    alone = [thing(400, 500, (2.0, 6.0))]
    props = propose.score(tape + flock + alone)
    check(all(p.tape for p in tape) and "scrolling tape" in tape[0].describe(),
          "five marks in a row, sliding along it together: each is said to be part of a scrolling tape", tape[0].describe()[-120:])
    check(not any(p.tape for p in flock + alone), "a cluster going the same way is not a tape, nor is a thing alone")


def test_striation_is_classified():
    """Sea and cloud must be told apart by peak anisotropy, or the two layers
    cannot be named."""
    print("\nlayers: texture classes")
    bad = np.zeros((600, 900), bool)
    for name, scene, want_striated in (("striated (sea-like)", striated(600, 900), True),
                                       ("isotropic (cloud-like)", isotropic(600, 900), False)):
        g = vf.good(vf.shift_field(scene, roll(scene, 25, 0), bad, bad, tpl=128, stride=96, reach=120))
        ani = float(np.median(g[:, 7]))
        check((ani < 0.25) == want_striated, f"{name} classified",
              f"median anisotropy {ani:.3f}")


def test_windowed_correlation_would_have_been_biased():
    """Documents why the library searches for a whole template: the
    same-position windowed estimate under-reads a large shift."""
    print("\nregistration: whole-template search has no taper bias")
    base = isotropic(600, 900)
    bad = np.zeros(base.shape, bool)
    dx = 30
    f = vf.shift_field(base, roll(base, dx, 0), bad, bad, tpl=128, stride=96, reach=120)
    con = vf.consensus(vf.good(f)[:, 3:5])
    err = abs(con[0][0] - dx) / dx if con else 1.0
    check(err < 0.01, "large shift recovered to better than 1 %", f"error {err:.3%}")


# ---------------------------------------------------------------- cadence
def test_repeated_frames_are_found():
    """Clips that repeat ~7 % of frames make per-frame differences meaningless."""
    print("\ncadence: repeated frames")
    n, d = np.arange(1, 61), np.full(60, 4.0) + RNG.normal(0, 0.1, 60)
    planted = [11, 23, 24, 47]
    d[[p - 1 for p in planted]] = 0.001
    found = vf.repeats(np.column_stack([n, d]))
    check(found == planted, "finds exactly the planted repeats", f"{found}")


# ---------------------------------------------------------------- detection
def test_a_compact_source_is_found_and_linked():
    """A bright disc on a known path: detection, then linking into a track."""
    print("\ndetection: a compact source on a known path")
    h, w = 400, 700
    truth = {n: (60 + 9.0 * n, 150 + 3.0 * n) for n in range(1, 21)}
    cands = {}
    yy, xx = np.mgrid[0:h, 0:w]
    for n, (x, y) in truth.items():
        g = isotropic(h, w, scale=6.0) * 0.2 + 60
        g += 900 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 3.0 ** 2))
        cands[n] = vf.source_candidates(g, np.zeros(g.shape, bool), size=6.0)
    found = sum(1 for n in truth if any(
        np.hypot(c[0] - truth[n][0], c[1] - truth[n][1]) < 2.0 for c in cands.get(n, [])))
    check(found == len(truth), "the object is among the candidates in every frame",
          f"{found} of {len(truth)}")
    trk = vf.link_track(cands, 1, 20)
    check(len(trk) >= 18, "the linker covers the path", f"{len(trk)} of 20 frames")
    if trk:
        err = max(np.hypot(xy[0] - truth[n][0], xy[1] - truth[n][1])
                  for n, xy in trk.items() if n in truth)
        check(err < 2.0, "and lands on the object", f"worst error {err:.2f} px")


def test_a_fast_object_needs_a_velocity_prior():
    """The linker's gate is 25 + 12*gap px. Anything faster than that per
    frame is outside its own gate on the first step, and the track dies at one
    point -- which is what happened to PR113 (142 px/frame) before the
    velocity argument existed."""
    print("\ndetection: acquiring a fast object")
    h, w = 700, 1400
    vx, vy = -103.0, 98.0
    truth = {n: (1100 + vx * (n - 1), 120 + vy * (n - 1)) for n in range(1, 5)}
    yy, xx = np.mgrid[0:h, 0:w]
    cands = {}
    for n, (x, y) in truth.items():
        g = isotropic(h, w, scale=6.0) * 0.2 + 60
        g += 900 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 4.0 ** 2))
        cands[n] = vf.source_candidates(g, np.zeros(g.shape, bool), size=8.0)

    blind = vf.link_track(cands, 1, 4, seed=(1, *truth[1]))
    check(len(blind) == 1, "without a velocity it dies after the seed frame",
          f"{len(blind)} of 4 frames")

    primed = vf.link_track(cands, 1, 4, seed=(1, *truth[1]), velocity=(vx, vy))
    check(len(primed) == 4, "with one it follows the whole transit",
          f"{len(primed)} of 4 frames")
    if len(primed) == 4:
        err = max(np.hypot(p[0] - truth[n][0], p[1] - truth[n][1]) for n, p in primed.items())
        check(err < 2.0, "and lands on the object every frame", f"worst {err:.2f} px")

    wide = vf.link_track(cands, 1, 4, seed=(1, *truth[1]), gate=(25.0, 200.0))
    check(len(wide) == 4, "a widened gate also works, when the velocity is unknown",
          f"{len(wide)} of 4 frames")


def test_two_marks_give_the_velocity():
    print("\ndetection: velocity from hand marks")
    v = vf.velocity_from_marks({408: (1009.0, 313.0), 411: (702.0, 604.0)})
    check(v is not None and abs(v[0] + 102.3) < 0.2 and abs(v[1] - 97.0) < 0.2,
          "two clicks on PR113 give (-102.3, +97.0) px/frame",
          f"({v[0]:+.1f}, {v[1]:+.1f}); documented (-103, +98)")
    check(vf.velocity_from_marks({5: (1.0, 2.0)}) is None, "one mark gives None, not a guess")


def test_the_detector_scale_must_match_the_object():
    """A matched filter much smaller than the object misses it outright, not
    merely weakly: PR113's 25 px object is 71 px from the nearest candidate at
    the 9 px default."""
    print("\ndetection: scale sweep")
    h, w = 400, 700
    cx, cy, rad = 350.0, 200.0, 12.0
    yy, xx = np.mgrid[0:h, 0:w]
    g = isotropic(h, w, scale=6.0) * 0.2 + 60
    g += 700 * (np.hypot(xx - cx, yy - cy) <= rad)
    bad = np.zeros(g.shape, bool)

    small = vf.source_candidates(g, bad, size=5.0, n_max=25, min_resp=5.0)
    d_small = min(np.hypot(c[0] - cx, c[1] - cy) for c in small) if small else 1e9
    best, sweep = vf.best_scale(g, bad, (cx, cy), sizes=(5, 9, 15, 21, 31), tol=5.0)
    check(best is not None, "the sweep finds a scale that works", f"size={best}")
    if best:
        check(sweep[best]["nearest_px"] < 5.0, "and it lands on the object",
              f"{sweep[best]['nearest_px']:.1f} px at size={best}")
        check(best >= 15, "which is comparable to the object, not the default 9",
              f"object diameter {2 * rad:.0f} px, chosen scale {best}")
    check(d_small > sweep[best]["nearest_px"], "a too-small filter does worse",
          f"size=5 misses by {d_small:.0f} px")


class _Blurred:
    """Grey frames with 30 points of the scene drawn as Gaussians of sigma 1 px (2.35 px wide at
    half their peak), panning 1 px a frame, 12 hot 2 x 2 blocks that stay on the sensor (narrower
    than a point: ~1.9 px), and an object
    moving 3 px a frame: a point like them, a disc `obj` px across, or a point clipped at white."""
    n0, n1, W, H = 1, 60, 640, 480

    def __init__(self, obj, points=30):
        self.obj, self.cache = obj, {}
        yy, xx = np.mgrid[-6:7, -6:7]
        self.stamp = 120 * np.exp(-(xx ** 2 + yy ** 2) / 2.0)
        self.at = np.random.default_rng(7).integers(40, [520, 440], (points, 2))
        self.hot = np.random.default_rng(8).integers(40, [600, 440], (12, 2))

    def rgb(self, n):
        if n not in self.cache:
            g = 60 + np.random.default_rng(n).normal(0, 3, (self.H, self.W))
            for x, y in self.at:
                g[y - 6:y + 7, x + n - 6:x + n + 7] += self.stamp
            for x, y in self.hot:
                g[y:y + 2, x:x + 2] += 150
            ox, oy = 100 + 3 * n, 240
            if self.obj == "point":
                g[oy - 6:oy + 7, ox - 6:ox + 7] += self.stamp
            elif self.obj == "clipped":
                g[oy - 6:oy + 7, ox - 6:ox + 7] += 4 * self.stamp
            elif self.obj == "clipped disc":
                yy, xx = np.mgrid[0:self.H, 0:self.W]
                g += 250 * (np.hypot(xx - ox, yy - oy) <= 12)
            else:
                yy, xx = np.mgrid[0:self.H, 0:self.W]
                g += 120 * (np.hypot(xx - ox, yy - oy) <= self.obj / 2)
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


def test_a_point_is_told_from_a_body_by_the_blur_of_the_clip():
    """PR135's agent divided by 7.4 px for a group of hot points and got 28.6 body lengths a
    second: 7.4 is the detector's smallest scale, which a point reads as. Where there are
    frames, how wide a point is drawn is measured on the clip's sharpest spots, and the object
    against it; a speed in body lengths of an object no wider than a point is NO POWER."""
    print("\nthe blur of a point, and whether the object is wider")
    masks = dict(blocks=np.zeros((480, 640), bool), graphics=np.zeros((480, 640), bool), colour=True)
    track = {n: (100.0 + 3 * n, 240.0) for n in range(1, 61)}
    p = vf.point_blur(_Blurred("point"), track, masks)
    check(p["spots"] >= vf.BLUR_SPOTS and abs(p["blur_fwhm_px"] - 2.35) < 0.15 and p["resolved"] is False,
          "points 2.35 px wide: the blur is read as that, and an object that is one is not resolved",
          f"blur {p['blur_fwhm_px']:.2f} px from {p['spots']} spots, object {p['object_fwhm_px']:.2f}")
    check(p["on_the_sensor"] >= 12 * p["frames"] // 2,
          "hot pixels that stay on the sensor are left out: drawn without the optics, they are narrower than a point",
          f"{p['on_the_sensor']} left out")
    c = vf.point_blur(_Blurred("clipped"), track, masks)
    check(c["object_clipped"] > c["frames"] // 2 and c["resolved"] is None,
          "a point clipped at white looks wider than the blur, and cannot be told from a body: not measured "
          "(PR135's hot points)", f"clipped on {c['object_clipped']} of {c['frames']} frames, {c['object_fwhm_px']:.1f} px")
    k = vf.point_blur(_Blurred("clipped disc"), track, masks)
    check(k["object_clipped"] > k["frames"] // 2 and k["resolved"] is True,
          "a disc 24 px across clipped at white is wider than clipping can make a point: resolved (PR055's disc)",
          f"{k['object_fwhm_px']:.1f} px against {k['blur_fwhm_px']:.2f}")
    for d in (6, 24):
        q = vf.point_blur(_Blurred(d), track, masks)
        check(q["resolved"] is True and q["object_fits"] == q["frames"],
              f"a disc {d} px across is resolved", f"object {q['object_fwhm_px']:.1f} px, blur {q['blur_fwhm_px']:.2f}")
    e = vf.point_blur(_Blurred("point", points=0), track, masks)
    check(e["blur_fwhm_px"] is None and e["resolved"] is None,
          "with no points but the object to measure the blur on, it is not measured, and nothing is claimed",
          f"{e['spots']} spots")


class _Flock:
    """Six points (Gaussians, sigma 1 px) about a centre moving (4, 1) px a frame, drawn between
    pixels, with 0.3 px of jitter: `kind` "rigid" keeps their places (the whole growing 0.1 % a
    frame, as a slow zoom does), "shuffle" lets each drift 8 px about its place, over two
    seconds, as birds in a flock do, "one" is one point.
    And four hot 2 x 2 blocks that stay on the sensor."""
    n0, n1, W, H = 1, 90, 640, 480

    def __init__(self, kind):
        self.kind, self.cache = kind, {}
        rng = np.random.default_rng(3)
        self.home = np.array([(-40, -10), (-20, 15), (0, -20), (15, 10), (35, -5), (50, 20)], float)
        t = np.arange(self.n1 + 1)[:, None, None]         # each drifts 8 px about its place, over two seconds
        self.walk = 8 * np.sin(2 * np.pi * t / 60.0 + rng.uniform(0, 2 * np.pi, (1, 6, 2)))
        self.jit = rng.normal(0, 0.3, (self.n1 + 1, 6, 2))
        self.hot = [(150, 330), (420, 80), (500, 400), (260, 150)]

    def centre(self, n):
        return 150.0 + 4 * n, 220.0 + 1 * n

    def points(self, n):
        c = np.array(self.centre(n))
        if self.kind == "one":
            return c[None] + self.jit[n, :1]
        at = self.home * (1 + 0.001 * n) + (self.walk[n] if self.kind == "shuffle" else 0)
        return c + at + self.jit[n]

    def rgb(self, n):
        if n not in self.cache:
            g = 50 + np.random.default_rng(n).normal(0, 2, (self.H, self.W))
            yy, xx = np.mgrid[-6:7, -6:7]
            for x, y in self.points(n):
                xi, yi = int(round(x)), int(round(y))
                g[yi - 6:yi + 7, xi - 6:xi + 7] += 150 * np.exp(-((xx - (x - xi)) ** 2 + (yy - (y - yi)) ** 2) / 2.0)
            for x, y in self.hot:
                g[y:y + 2, x:x + 2] += 150
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


def test_a_group_is_told_to_be_one_and_whether_its_members_keep_their_places():
    """PR135's "6X SMALL SPHERICAL OBJECTS" were linked as one track, and `propose` listed them
    as one thing; the agent wrote its own member tracker to ask what tells a flock from a
    formation -- do the members keep their places? `groups` asks it: the points near the track,
    followed frame to frame against the group's own motion, sensor defects left out, and every
    pair's separation held against the members' own position noise."""
    print("\ngroups: several points, and whether they keep their places")
    from mcdonald import groups
    masks = dict(blocks=np.zeros((480, 640), bool), graphics=np.zeros((480, 640), bool), colour=True)
    got = {}
    for kind in ("rigid", "shuffle", "one"):
        clip = _Flock(kind)
        track = {n: clip.centre(n) for n in range(1, 91)}
        got[kind] = groups.measure(clip, track, masks, out=None, say=lambda *a: None).fields
    r, s, o = got["rigid"], got["shuffle"], got["one"]
    check(r["several"] and r["points_per_frame"]["median"] == 6 and r["members_followed"] == 6,
          "six points about the track: several, and six members followed", f"{r['points_per_frame']}, {r['members_followed']} followed")
    check(r["rigid"] is True and len(r["pairs"]) == 15,
          "a formation that keeps its places, under a slow zoom and 0.3 px of jitter: rigid", r["finding"][:90])
    check(s["rigid"] is False, "members that wander about the group: they change places", s["finding"][:90])
    check(o["several"] is False and o["rigid"] is None, "one point: a single thing, and nothing is claimed about places",
          o["finding"])
    disc = _Blurred(24)
    d = groups.measure(disc, {n: (100.0 + 3 * n, 240.0) for n in range(1, 61)}, masks, out=None, say=lambda *a: None).fields
    check(d["several"] is False, "a disc 24 px across, whose rim the small detector fires on all the way round, is not a group",
          f"{d['points_per_frame']}")
    clip = _Flock("rigid")
    tracks, _, fixed, _ = groups.members(clip, {n: clip.centre(n) for n in range(1, 91)}, masks)
    moved = [np.hypot(*np.subtract(t[max(t)][:2], t[min(t)][:2])) for t in tracks.values() if len(t) >= groups.MIN_FRAMES]
    check(fixed > 0 and min(moved) > 100,
          "the hot pixels the group runs past are left out, and every member followed moves with it",
          f"{fixed} spots on the sensor; members moved {min(moved):.0f}-{max(moved):.0f} px")


class _Beating:
    """Points 2.35 px wide on a grainy background, each moving `v` px a frame -- a fraction, so a
    small aperture on the rounded position would make a beat of its own -- and each at `beats`
    = [(Hz, share, phase)] (share 0: constant)."""
    n0, n1, W, H, fps = 1, 150, 400, 300, 30000 / 1001

    def __init__(self, beats, v=(0.37, 0.21)):
        self.beats, self.v, self.cache = beats, v, {}

    def at(self, j, n):
        return 80.0 + 60 * j + self.v[0] * n, 120.0 + 25 * j + self.v[1] * n

    def rgb(self, n):
        if n not in self.cache:
            g = 60 + np.random.default_rng(n).normal(0, 2, (self.H, self.W))
            yy, xx = np.mgrid[-7:8, -7:8]
            for j, (hz, share, ph) in enumerate(self.beats):
                x, y = self.at(j, n)
                xi, yi = int(round(x)), int(round(y))
                a = 120 * (1 + share * np.sin(2 * np.pi * hz * n / self.fps + np.radians(ph)))
                g[yi - 7:yi + 8, xi - 7:xi + 8] += a * np.exp(-((xx - (x - xi)) ** 2 + (yy - (y - yi)) ** 2) / 2.0)
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


class _Brief(_Beating):
    """_Beating's points over 40 frames: too short for the stage's beat, read anyway (item 8). At module level, as a
    class a process pool pickles must be."""
    n1 = 40


class _Flasher(_Beating):
    """A dark body, 12 px across in radius, on a grainy sky, carrying a small light 8 px from its middle that flashes
    `rate` times a second for `width` s each time -- red (the red channel only), white, or "black-hot" (dark, as a hot
    light is on a black-hot thermal display, where the hot body is dark too) -- or never (rate 0). Ten seconds at 29.97
    frames a second. At module level, for the process pools (item 13)."""
    n1 = 300

    def __init__(self, rate=1.0, colour="red", width=0.2, start=0.45):
        super().__init__([], v=(0.31, 0.17))
        self.rate, self.colour, self.width, self.start = rate, colour, width, start

    def at(self, j, n):
        return 150.0 + self.v[0] * n, 140.0 + self.v[1] * n

    def lit(self, n):
        if not self.rate:
            return False
        t = (n - 1) / self.fps - self.start
        return t >= 0 and (t * self.rate) % 1.0 < self.width * self.rate

    def rgb(self, n):
        if n not in self.cache:
            rng = np.random.default_rng(n)
            g = 150 + rng.normal(0, 2, (self.H, self.W))
            x, y = self.at(0, n)
            yy, xx = np.mgrid[:self.H, :self.W]
            g -= 90 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 6.0 ** 2))
            c = np.repeat(g[..., None], 3, 2) + rng.normal(0, 1.5, (self.H, self.W, 3))     # each channel's own grain
            if self.lit(n):
                spot = 100 * np.exp(-((xx - x - 8) ** 2 + (yy - y + 3) ** 2) / 2.0)
                if self.colour == "red":
                    c[..., 0] += spot
                elif self.colour == "black-hot":
                    c -= spot[..., None]
                else:
                    c += spot[..., None]
            self.cache[n] = np.clip(c, 0, 255).astype(np.uint8)
        return self.cache[n]


class _Jittered(_Beating):
    """_Beating's one point over a textured scene, the whole picture -- scene and point -- moved `jitter` px along x at
    `jitter_hz` (a cooler's or a gimbal's jitter); with `flat`, over a featureless grey instead. At module level, for the
    process pools."""
    scene = None

    def __init__(self, beats, jitter=0.0, jitter_hz=6.0, flat=False):
        super().__init__(beats, v=(0.37, 0.21))
        self.jitter, self.jitter_hz, self.flat = jitter, jitter_hz, flat

    def rgb(self, n):
        if n not in self.cache:
            from scipy import ndimage
            if _Jittered.scene is None:
                _Jittered.scene = np.clip(ndimage.gaussian_filter(np.random.default_rng(3).normal(0, 1, (self.H, self.W)), 2.5)
                                          * 80 + 60, 20, 110)        # about 9 grey levels of detail: the point stays above it
            dx = self.jitter * np.sin(2 * np.pi * self.jitter_hz * n / self.fps)
            base = np.full((self.H, self.W), 60.0) if self.flat else ndimage.shift(_Jittered.scene, (0, dx), order=3, mode="nearest")
            g = base + np.random.default_rng(n).normal(0, 1.0, (self.H, self.W))
            yy, xx = np.mgrid[-7:8, -7:8]
            hz, share, ph = self.beats[0]
            x, y = self.at(0, n)
            x += dx
            xi, yi = int(round(x)), int(round(y))
            a = 120 * (1 + share * np.sin(2 * np.pi * hz * n / self.fps + np.radians(ph)))
            g[yi - 7:yi + 8, xi - 7:xi + 8] += a * np.exp(-((xx - (x - xi)) ** 2 + (yy - (y - yi)) ** 2) / 2.0)
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


class _Flyer(_Beating):
    """A bird drawn as flyer 5 was measured (2026-09-29): a point faint far off and bright as it comes,
    whose brightness beats twice a stroke -- the double of the wingbeat stronger than the beat itself --
    at a rate that settles from 4.8 to 3.9 Hz over the first half of the clip and holds after."""
    n0, n1 = 1, 210

    def __init__(self):
        super().__init__([(0, 0, 0)])
        n = np.arange(self.n1 + 2)
        rate = np.where(n < 105, 4.8 - 0.9 * n / 105, 3.9)                     # Hz, frame by frame
        self.phase = 2 * np.pi * np.cumsum(rate) / self.fps

    def rgb(self, n):
        if n not in self.cache:
            g = 60 + np.random.default_rng(n).normal(0, 2, (self.H, self.W))
            yy, xx = np.mgrid[-7:8, -7:8]
            x, y = self.at(0, n)
            xi, yi = int(round(x)), int(round(y))
            bright = 0.25 + 0.75 * min(n / 140, 1.0)                              # faint, then bright
            a = 120 * bright * (1 + 0.08 * np.sin(self.phase[n]) + 0.16 * np.sin(2 * self.phase[n]))
            g[yi - 7:yi + 8, xi - 7:xi + 8] += a * np.exp(-((xx - (x - xi)) ** 2 + (yy - (y - yi)) ** 2) / 2.0)
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


def test_a_wingbeat_is_found_in_a_window_and_named_by_its_fundamental():
    """Flyer 5 (Jacob, 2026-09-29; the Galileo paper's 3.90 / 7.80 Hz): one spectrum over the whole track,
    a faint approach and then bright flapping at a changing rate, peaked at 5.11 Hz between the two. The
    beat is looked for in 2-s windows along the track too, the clearest that passes gives the frequency
    where it is clearer than the whole, and a peak with another at half its frequency is the double of
    the beat: the fundamental is reported, its double named."""
    print("\nflicker: a wingbeat, in a window, by its fundamental")
    from mcdonald import flicker
    clip = _Flyer()
    f = flicker.measure(clip, {"object": {n: clip.at(0, n) for n in range(1, clip.n1 + 1)}}, say=lambda *a: None).fields
    b = (f.get("beat") or {}).get("object")
    whole = f["curves"]["object"]
    check(f["beats"] is True and b is not None and abs(b["hz"] - 3.9) <= 0.25 and b["double_hz"] is not None and abs(b["double_hz"] - 7.8) <= 0.5,
          "reported: the wingbeat 3.9 Hz and its double 7.8, though the double is the stronger peak",
          f"{b['hz']:.2f} Hz, double {b['double_hz']}; the whole track's strongest {whole['hz']:.2f} Hz" if b else str(f.get("finding")))
    check(b is not None and b["source"] != "the whole track" and b["first"] >= 90 and b["windows_passing"] >= 3,
          "from a window over the bright, steady flapping, not the whole track", f"frames {b['first']}-{b['last']}, {b['source']}" if b else "")
    check("its double" in (f.get("finding") or "") and f"frames {b['first']}" in f.get("finding", ""), "and the finding says so", (f.get("finding") or "")[:110])
    one = _Beating([(8.0, 0.2, 0)])
    g = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=lambda *a: None).fields
    check(g["beat"]["member 0"]["double_hz"] is None and abs(g["beat"]["member 0"]["hz"] - 8.0) < 0.3 and g["beat"]["member 0"]["source"] == "the whole track",
          "a steady 8-Hz beat over the whole track is still reported from the whole track, with no double named", str(g["beat"]["member 0"])[:100])


class _FoldedDouble(_Beating):
    """A bird drawn as PR089's C was measured in a 6-px disc (2026-10-25): a point beating at 10.5 Hz whose double,
    at 21 Hz, is past the frame rate's half and so appears folded, at fps - 21 = 8.97 Hz -- and is the stronger."""
    n0, n1 = 1, 240

    def rgb(self, n):
        if n not in self.cache:
            g = 60 + np.random.default_rng(n).normal(0, 2, (self.H, self.W))
            yy, xx = np.mgrid[-7:8, -7:8]
            x, y = self.at(0, n)
            xi, yi = int(round(x)), int(round(y))
            p = 2 * np.pi * 10.5 * n / self.fps
            a = 120 * (1 + 0.06 * np.sin(p) + 0.12 * np.sin(2 * p + 0.4))
            g[yi - 7:yi + 8, xi - 7:xi + 8] += a * np.exp(-((xx - (x - xi)) ** 2 + (yy - (y - yi)) ** 2) / 2.0)
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


def test_a_beat_whose_double_folds_is_named_by_its_fundamental():
    """PR089's bird C (2026-10-25): in a 6-px disc its 10.50-Hz beat's double, folded through 30 frames a second to
    30 - 21.0 = 9.0 Hz, stood taller than the beat, and the stage named 8.99 Hz -- a frequency the bird does not beat
    at. A strongest f with a peak of its own at (fps - f)/2 is that beat's folded double: the fundamental is reported,
    its double named as folded. A beat with nothing at (fps - f)/2 keeps its own frequency."""
    print("\nflicker: a beat whose double folds through the frame rate, by its fundamental")
    from mcdonald import flicker
    clip = _FoldedDouble([(0, 0, 0)])
    f = flicker.measure(clip, {"object": {n: clip.at(0, n) for n in range(1, clip.n1 + 1)}}, say=lambda *a: None).fields
    b = (f.get("beat") or {}).get("object")
    whole = f["curves"]["object"]
    folded = clip.fps - 21.0
    check(abs(whole["hz"] - folded) <= 0.2, "the strongest peak is the folded double", f"{whole['hz']:.2f} Hz against {folded:.2f}")
    check(f["beats"] is True and b is not None and abs(b["hz"] - 10.5) <= 0.15 and b["double_hz"] is not None
          and abs(b["double_hz"] - folded) <= 0.3,
          "reported: the beat 10.5 Hz and its folded double", f"{b['hz']:.2f} Hz, double {b['double_hz']}" if b else str(f.get("finding")))
    check("folded through the frame rate" in (f.get("finding") or ""), "and the finding says the double is folded", (f.get("finding") or "")[:140])
    one = _Beating([(9.0, 0.2, 0)])
    g = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=lambda *a: None).fields
    check(abs(g["beat"]["member 0"]["hz"] - 9.0) < 0.3 and g["beat"]["member 0"]["double_hz"] is None,
          "a plain 9-Hz beat keeps its own frequency", str(g["beat"]["member 0"])[:100])
    t = np.arange(600) / 30.0
    y = 1000 * (1 + 0.02 * np.sin(2 * np.pi * 10.5 * t) + 0.03 * np.cos(2 * np.pi * 21 * t)) + np.random.default_rng(1).normal(0, 3, 600)
    h = flicker.harmonics(y, 30.0, drift_too=True, top_hz=10.0)[:2]
    check(abs(h[0] - 9.0) < 0.1 and h[1] is None, "a fundamental above the band's top is not offered", str(h))
    check(abs(flicker.half_err(10.5, 9.0, 0.02) - 0.01) < 1e-12 and flicker.half_err(9.0, 9.0, 0.02) == 0.02,
          "the folded fundamental's error is half the strongest's", "")


def test_a_beat_is_the_objects_only_past_the_traps_that_fake_one():
    """PR135's agent found each of its points flickering 7-8 Hz, and the two traps that fake a
    flicker: a small aperture on a point moving a fraction of a pixel a frame (constant dots
    "beat" 3-6 Hz), and the codec's rhythm, which beats every member alike. `flicker` builds
    both in, holds every beat against apertures of background beside it, and where there are
    members asks whether they beat as one."""
    print("\nflicker: a beat of its own, or a trap")
    from mcdonald import flicker
    tracks = lambda c, k: {f"member {j}": {n: c.at(j, n) for n in range(1, 151)} for j in range(k)}
    say = lambda *a: None
    one = _Beating([(8.0, 0.2, 0)])
    f = flicker.measure(one, tracks(one, 1), say=say).fields
    p = f["curves"]["member 0"]
    check(f["beats"] is True and abs(p["hz"] - 8.0) <= p["resolution_hz"] and abs(p["amplitude"] - 0.2) < 0.04,
          "a point beating 8 Hz by 20 %, moving a fraction of a pixel a frame: 8 Hz, 20 %, its own",
          f"{p['hz']:.2f} Hz, {p['amplitude']:.1%}; background {f['noise_floor']:.1%}")
    still = _Beating([(0, 0, 0)])
    f = flicker.measure(still, tracks(still, 1), say=say).fields
    check(f["beats"] is False, "a constant point moving 0.37 px a frame: no beat -- the aperture's sub-pixel weights "
          "leave nothing of the pixel phase", f["finding"][:80])
    small = [flicker.brightness(still.rgb(n).mean(2), round(still.at(0, n)[0]), round(still.at(0, n)[1]), r=1.5)
             for n in range(1, 151)]
    q = flicker.peak(small, still.fps)
    phase_hz = still.fps * 0.37                                   # the fraction of a pixel it moves, turning over
    big = [flicker.brightness(still.rgb(n).mean(2), *still.at(0, n)) for n in range(1, 151)]
    fr, F, _, wsum, _ = flicker.spectrum(big, still.fps)
    at = float(2 * np.abs(F[np.argmin(np.abs(fr - q["hz"]))]) / wsum)
    check(abs(q["hz"] - phase_hz) <= q["resolution_hz"] and at < q["amplitude"] / 3,
          "which a small aperture on the rounded position does not: it beats at the pixel phase, 30 x 0.37 = 11.1 Hz, "
          "where the sub-pixel aperture has a third of it or less", f"{q['hz']:.2f} Hz, {q['amplitude']:.1%} against {at:.1%}")
    both = _Beating([(8.0, 0.2, 0), (8.0, 0.2, 0)])
    f = flicker.measure(both, tracks(both, 2), say=say).fields
    check(f["beats"] is None and "as one" in f["finding"], "two members beating at one frequency, in step: what a rhythm "
          "of the video would do, so it is not called theirs", f["finding"][:80])
    two = _Beating([(8.0, 0.2, 0), (6.0, 0.2, 90)])
    f = flicker.measure(two, tracks(two, 2), say=say).fields
    check(f["beats"] is True and f["pairs"][0]["independent"], "two at 8 and 6 Hz over the same frames: theirs",
          f"{f['pairs'][0]['hz'][0]:.2f} and {f['pairs'][0]['hz'][1]:.2f} Hz")
    # members that come and go (PR135's flock, 2026-10-08): the second is seen from frame 61 only, and they share
    # 90 frames; before, the stage took the frames all members share, and with a member seen late that was none
    late = {"member 0": {n: two.at(0, n) for n in range(1, 151)}, "member 1": {n: two.at(1, n) for n in range(61, 151)}}
    f = flicker.measure(two, late, say=say).fields
    b0, b1 = f["beat"].get("member 0"), f["beat"].get("member 1")
    check(f["beats"] is True and b0 and b1 and abs(b0["hz"] - 8.0) < 0.3 and abs(b1["hz"] - 6.0) < 0.3
          and (b1["first"], b1["last"]) == (61, 150) and f["pairs"][0]["frames"] == [61, 150] and f["pairs"][0]["independent"],
          "a member seen late is measured over its own frames, and the pair over the frames both have: theirs",
          f"{b0 and b0['hz']:.2f} over {b0 and (b0['first'], b0['last'])}, {b1 and b1['hz']:.2f} over {b1 and (b1['first'], b1['last'])}; "
          f"pair {f['pairs'][0].get('frames') if f['pairs'] else None}; {f.get('finding')}")
    apart = {"member 0": {n: two.at(0, n) for n in range(1, 81)}, "member 1": {n: two.at(1, n) for n in range(91, 151)}}
    f = flicker.measure(two, apart, say=say).fields
    check(f["beats"] is None and "no two members share" in (f.get("finding") or "") and f["beat"].get("member 0") and not f["pairs"],
          "members that never share the frames a beat needs are each measured, and nothing is said of their beating as one",
          (f.get("finding") or "")[:90])


class _Shown(_Beating):
    """One point drawn as _Beating draws them, at `level[n]` of its usual brightness on frame n: to plant what is
    not a beat -- a point lost against what is behind it, or one whose brightness only wanders. `width` is its
    sigma in pixels: a wider point carries more light against the ring's median, which moves by whole grey
    levels (one level over the aperture is 50 against a 1-px point's 750 -- the background's floor)."""

    def __init__(self, level, v=(0.37, 0.21), width=1.0):
        super().__init__([(0, 0, 0)], v)
        self.level, self.width = level, width

    def rgb(self, n):
        if n not in self.cache:
            g = 60 + np.random.default_rng(n).normal(0, 2, (self.H, self.W))
            yy, xx = np.mgrid[-7:8, -7:8]
            x, y = self.at(0, n)
            xi, yi = int(round(x)), int(round(y))
            g[yi - 7:yi + 8, xi - 7:xi + 8] += 120 * self.level[n] * np.exp(-((xx - (x - xi)) ** 2 + (yy - (y - yi)) ** 2)
                                                                           / (2.0 * self.width ** 2))
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


class _Disc(_Beating):
    """One disc 30 px across (soft-edged) on the same grainy background, drifting 0.3 px a frame, its brightness
    beating at `hz` by `share` (0: constant) -- a thing wider than the point-sized aperture."""

    def __init__(self, hz=0.0, share=0.0, radius=15.0):
        super().__init__([(hz, share, 0)], v=(0.3, 0.2))
        self.radius = radius

    def at(self, j, n):
        return 200.0 + self.v[0] * n, 150.0 + self.v[1] * n

    def rgb(self, n):
        if n not in self.cache:
            g = 60 + np.random.default_rng(n).normal(0, 2, (self.H, self.W))
            x, y = self.at(0, n)
            yy, xx = np.mgrid[0:self.H, 0:self.W]
            hz, share, _ = self.beats[0]
            a = 90 * (1 + share * np.sin(2 * np.pi * hz * n / self.fps))
            g += a / (1 + np.exp((np.hypot(xx - x, yy - y) - self.radius) / 1.2))
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


def test_the_continuum_null_finds_a_line_and_lets_red_noise_be():
    """The paper's continuum null (2026-10-16, ROADMAP.md 0.3; the bird sweep's beat_stability.py): a peak against a
    power law fitted to its own spectrum, held against noise curves of that continuum read at their strongest anywhere
    in the band. A 6-Hz line in red noise stands far over it; red noise with no line passes about once in a hundred,
    as a null at 0.01 should; and the stage reports it for every track over the stretch its beat is from."""
    print("\nflicker: the paper's continuum null")
    from mcdonald import flicker
    fps, n = 30.0, 300
    t = np.arange(n) / fps

    def red(seed):
        rng = np.random.default_rng(seed)
        f = np.fft.rfftfreq(n, 1 / fps)
        Z = (rng.normal(size=len(f)) + 1j * rng.normal(size=len(f))) / np.maximum(f, f[1]) ** 0.8
        y = np.fft.irfft(Z, n)
        return 0.05 * y / y.std()
    line = flicker.continuum(red(1) + 0.03 * np.sin(2 * np.pi * 6.0 * t), fps, top=12.0)
    check(abs(line["hz"] - 6.0) < 0.15 and line["p"] < 0.01 and line["ratio"] > line["needed99"],
          "a 6-Hz line at 3 % in red noise of 5 %: found, standing over the 99 % level", f"{line['hz']:.2f} Hz {line['ratio']:.1f} vs {line['needed99']:.1f}, p {line['p']:.3f}")
    alarms = [s for s in range(40) if flicker.continuum(red(100 + s), fps, top=12.0, runs=500)["p"] < flicker.CONTINUUM_P]
    check(len(alarms) <= 3, "red noise with no line: about one curve in a hundred under 0.01 (at most 3 of 40 here)", f"{len(alarms)} of 40: {alarms}")
    one = _Beating([(8.0, 0.2, 0)])
    track = {k: one.at(0, k) for k in range(1, 151)}
    f = flicker.measure(one, {"object": track}, say=lambda *a: None).fields
    c = (f.get("continuum") or {}).get("object") or {}
    check(c.get("p") is not None and c["p"] < 0.01 and abs(c["hz"] - 8.0) < 0.3 and c.get("frames"),
          "and the stage reports it for a planted 8-Hz beat, with the frames it read", str({k: c.get(k) for k in ("hz", "ratio", "p", "frames")}))


def test_the_encoding_control_tells_a_beat_from_the_encoders_rhythm():
    """The paper's encoding control (2026-10-16, ROADMAP.md 0.3; `planted`): constant dots like the object, planted in
    the clip's own frames and grain and encoded like it -- its GOP, its B frames, its bit rate -- then measured as the
    object is. A beat as strong as PR135's points' (20 %) is far over what the encoder makes at its own rhythm, 7.49 Hz
    with a P frame every fourth: cleared. One at the encoder's own level is not. Without libx264 it says so and decides
    nothing. A drawn clip, encoded here: no video data."""
    print("\nflicker: the planted-dot encoding control")
    import shutil
    import subprocess
    import tempfile
    from mcdonald import flicker, planted, forensics as vf
    if not planted.has_x264():
        print("  SKIP  this ffmpeg has no libx264")
        return
    W, H, n_fr, fps = 480, 320, 170, "30000/1001"
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:H, 0:W]
    pos = {n: (120.0 + 0.6 * n, 140.0 + 0.25 * n) for n in range(1, n_fr + 1)}
    with tempfile.TemporaryDirectory(prefix="mcdonald-planted-test-") as td:
        td = Path(td)
        video = td / "drawn.mp4"
        cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-framerate", fps,
               "-i", "-", "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-g", "60", "-bf", "3", "-b_strategy", "0",
               "-x264-params", "b-adapt=0:scenecut=0", "-b:v", "1500k", str(video)]
        pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        base = 70 + 6 * np.sin(xx / 37.0) * np.cos(yy / 53.0)
        for n in range(1, n_fr + 1):
            x, y = pos[n]
            img = base + rng.normal(0, 2.0, (H, W)) + 110 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.3 ** 2))
            pr.stdin.write(np.clip(np.round(img), 0, 255).astype(np.uint8).tobytes())
        pr.stdin.close()
        pr.wait()
        clip = vf.Clip(video, td / "frames", 1, n_fr)
        D = planted.dots(clip, pos, dark=False, ap=flicker.sized(None))
        check(not D.get("skipped") and len(D["before"]) >= 4 and all(len(a) == planted.N for a in D["after"]),
              "dots planted on clean paths, encoded like the clip and measured before and after", D.get("skipped") or f"{len(D['before'])} dots")
        again = planted.dots(clip, pos, dark=False, ap=flicker.sized(None))
        check(again.get("after") == D.get("after") and again.get("before") == D.get("before"),
              "planted and encoded twice, the dots measure the same to the last digit: one answer, run after run")
        e = planted.at_beat(D, 7.49, 0.20, clip.fps)
        check(e.get("clears") is True and e["ratio"] >= planted.ABOVE and e["clean"] >= 3,
              "a 20 % beat at the encoder's own 7.49 Hz is many times what the encoder makes there: cleared",
              f"dots {e.get('at_beat_max', 0):.2%} at the beat, ratio {e.get('ratio', 0):.0f}, line {e.get('line_at_beat')}")
        fps_ = clip.fps
        t_ = np.arange(planted.N) / fps_
        g = np.random.default_rng(3)
        noisy = [list(1000 * (1 + 0.004 * g.normal(size=planted.N))) for _ in range(4)]
        lined = [list(1000 * (1 + 0.004 * g.normal(size=planted.N) + 0.03 * np.sin(2 * np.pi * 7.49 * t_ + j))) for j in range(4)]
        quiet = planted.at_beat(dict(before=noisy, after=noisy), 7.49, 0.002, fps_)
        loud = planted.at_beat(dict(before=noisy, after=lined), 7.49, 0.04, fps_)
        strong = planted.at_beat(dict(before=noisy, after=lined), 7.49, 0.20, fps_)
        check(quiet.get("line_at_beat") is False and quiet.get("clears") is True,
              "dots with no line at the beat: the encoder makes no rhythm there, however weak the beat (the null judges that)",
              f"ratio {quiet.get('ratio', 0):.2f}")
        check(loud.get("line_at_beat") is True and loud.get("clears") is False and strong.get("clears") is True,
              "dots with the encoder's line at the beat: a beat under three times it is the encoder's, one far over it is not",
              f"line {loud.get('at_beat_max', 0):.1%}; ratios {loud.get('ratio', 0):.1f}, {strong.get('ratio', 0):.1f}")
        real = planted.has_x264
        planted.has_x264 = lambda: False
        try:
            gone = planted.dots(clip, pos, ap=flicker.sized(None))
        finally:
            planted.has_x264 = real
        check("libx264" in (gone.get("skipped") or "") and planted.at_beat(gone, 7.49, 0.2, clip.fps).get("skipped"),
              "without libx264 the control says so and decides nothing", gone.get("skipped"))


class _Pair(_Beating):
    """Two of _Beating's points 25 px apart along x, both beating 8 Hz, out of step: A's background aperture at +25,+0
    lies on B -- PR135's six measured one by one, whose neighbours beat at their rates."""

    def at(self, j, n):
        return 150.0 + 25.0 * j + self.v[0] * n, 150.0 + self.v[1] * n


def test_the_background_keeps_clear_of_other_tracked_things():
    """`--avoid` (2026-10-16, ROADMAP.md 0.3): measured alone, a point whose neighbour sits where a background aperture
    goes has its beat 'shared by the background' -- the neighbour's. Told where the neighbour is, the stage moves its
    background apertures clear of it, says so, and the beat is the point's own. Not told, nothing changes: an object
    measured in a queue still gives what it gives alone."""
    print("\nflicker: background apertures clear of the other tracked things")
    from mcdonald import flicker
    pair = _Pair([(8.0, 0.2, 0), (8.0, 0.2, 120)])
    A = {k: pair.at(0, k) for k in range(1, 151)}
    B = {k: pair.at(1, k) for k in range(1, 151)}
    alone = flicker.measure(pair, {"object": A}, say=lambda *a: None)
    check(alone.fields["beats"] is None and "background beside it beats at the same frequency" in str(alone.no_power),
          "measured alone, A's beat is called the background's: an aperture lies on B", str(alone.no_power)[:120])
    told = flicker.measure(pair, {"object": A}, say=lambda *a: None, avoid={"B": B})
    f = told.fields
    clear = all(np.hypot(dx - 25.0, dy) > 2 * flicker.RING[1] + flicker.AVOID_MARGIN for dx, dy in f.get("background_offsets") or [])
    check(f["beats"] is True and abs(f["beat"]["object"]["hz"] - 8.0) < 0.3 and clear and len(f["background_offsets"]) == 4
          and any("moved clear" in n for n in told.notes),
          "told where B is, the four background apertures keep clear of it, and the beat is A's own",
          f"{f.get('background_offsets')}; {(f.get('finding') or str(told.no_power))[:80]}")
    import tempfile
    with tempfile.TemporaryDirectory(prefix="mcdonald-avoid-test-") as td:
        for k in (2, 3):
            (Path(td) / f"object-{k}").mkdir()
            (Path(td) / f"object-{k}" / "x_track.csv").write_text("frame,x_px,y_px\n" + "".join(f"{n},{B[n][0]:.2f},{B[n][1]:.2f}\n" for n in B),
                                                                  encoding="utf-8")
        named = flicker.read_avoid(f"{td}/object-2/x_track.csv,{td}/object-3/x_track.csv")
    check(sorted(named) == ["object-2/x_track", "object-3/x_track"], "tracks of one name in folders of their own are each kept, "
          "named by folder and file", str(sorted(named)))
    far = {k: (B[k][0] + 200, B[k][1]) for k in B}
    same = flicker.measure(pair, {"object": A}, say=lambda *a: None, avoid={"far": far}).fields
    check(same.get("background_offsets") == [[0.0, 25.0], [25.0, 0.0], [0.0, -25.0], [-25.0, 0.0]] and same["beats"] is None,
          "a thing far away leaves them where they were", str(same.get("background_offsets")))


class _Edgeward(_Beating):
    """One of _Beating's points running for the frame's right edge: the background aperture 25 px to its right leaves the
    frame on frame 129, while the point's own ring stays in -- PR141's infrared half."""

    def at(self, j, n):
        return 300.0 + 0.5 * n, 150.0 + 0.1 * n


def test_the_paper_rule_reads_the_background_over_its_own_stretch():
    """Under the paper's rule (2026-10-16) a background aperture that leaves the frame before the object does is read over
    its own stretch for the background at the beat, as the shared test reads it -- it had come out as nothing, and the
    beat was refused (PR141's infrared half). And a whole track that passes is what is reported, as the paper read
    whole tracks."""
    print("\nflicker: the paper's rule -- the background over its own stretch, the whole track reported")
    from mcdonald import flicker
    edge = _Edgeward([(8.0, 0.2, 0)])
    track = {k: edge.at(0, k) for k in range(1, 151)}
    f = flicker.measure(edge, {"object": track}, say=lambda *a: None, rule="paper").fields
    cur = f["curves"]["object"]
    right = f.get("curves", {}).get("background +25,+0")
    check(f.get("rule") == "paper" and np.isfinite(cur.get("background_at_beat", np.nan)) and f["beats"] is True
          and abs(f["beat"]["object"]["hz"] - 8.0) < 0.3,
          "the point beats at 8 Hz by the paper's rule, the background at its beat read where each aperture was in the frame",
          f"background at the beat {cur.get('background_at_beat')}; {(f.get('finding') or '')[:70]}")
    check(f["beat"]["object"]["source"] == "the whole track", "and the whole track is what is reported", f["beat"]["object"]["source"])


def test_a_fixed_aperture_is_measured_as_given():
    """The paper's aperture (2026-10-16, ROADMAP.md 0.3): each Table 1 object was measured in a disc of its own size,
    2.5-12 px, never re-centred -- where a flock's members fly close, the aperture that follows the object takes in its
    neighbours. `--aperture R[,R1,R2[,BG]]` fixes it; without one the aperture still follows the object's size."""
    print("\nflicker: a fixed aperture, as given")
    from mcdonald import flicker
    check(flicker.fixed("8,11,16") == (8.0, (11.0, 16.0), 37, False) and flicker.fixed(4) == (4.0, (7.0, 10.0), 25, False)
          and flicker.fixed("12,16,22,45") == (12.0, (16.0, 22.0), 45, False),
          "R, R,R1,R2 and R,R1,R2,BG: a 4-px disc's ring is the paper's 7-10 px, its background apertures 25 px away",
          f"{flicker.fixed('8,11,16')} {flicker.fixed(4)}")
    refused = []
    for bad in ("8,7,16", "0", "8,11", "4,7,10,12", "eight"):
        try:
            flicker.fixed(bad)
        except ValueError:
            refused.append(bad)
    check(len(refused) == 5, "a ring inside the disc, no disc, a ring with one edge, background apertures on the ring and words "
                             "are each refused", str(refused))
    disc = _Disc(hz=6.0, share=0.2)
    track = {k: disc.at(0, k) for k in range(1, 151)}
    f0 = flicker.measure(disc, {"object": track}, say=lambda *a: None).fields
    found = flicker.measure(disc, {"object": track}, say=lambda *a: None, aperture="20,23,28")
    f1 = found.fields
    check(f0.get("recentred") == ["object"] and not f0.get("aperture_fixed"),
          "without it, the aperture follows the 30-px disc's size and is re-centred on it", str(f0.get("aperture_px")))
    check(f1.get("aperture_fixed") == {"radius_px": 20.0, "ring_px": [23.0, 28.0], "background_px": 61}
          and f1["aperture_px"]["object"] == 20.0 and f1.get("recentred") == [] and f1["background_px"] == 61,
          "with it, every aperture is the disc given, never re-centred, and the fields say so", str(f1.get("aperture_fixed")))
    check(f1["beats"] is True and abs(f1["beat"]["object"]["hz"] - 6.0) < 0.3 and any("fixed, as given" in n for n in found.notes),
          "the disc's 6-Hz beat is measured in it, and the notes say the aperture was fixed", (f1.get("finding") or "")[:100])


def test_the_aperture_follows_a_thing_wider_than_a_point():
    """The bird sweep (2026-10-10): with a fixed 4-px aperture and its ring at 7-10 px, the ring lay on objects
    15-100 px across and the stage called a thing anyone could see "lost". The extent is read off the object's
    radial profile; a point keeps the 4-px aperture; a wider thing is measured whole -- a steady disc has no beat,
    a beating one beats."""
    print("\nflicker: the aperture follows a thing wider than a point")
    from mcdonald import flicker
    say = lambda *a: None
    pt = _Beating([(8.0, 0.2, 0)])
    f = flicker.measure(pt, {"member 0": {n: pt.at(0, n) for n in range(1, 151)}}, say=say).fields
    check(f["aperture_px"]["member 0"] == flicker.APERTURE and not f["recentred"],
          "a point 2.35 px wide keeps the 4-px aperture, its ring and the background apertures as they were",
          f"extent {f['extent_px']['member 0']}, aperture {f['aperture_px']['member 0']}")
    still = _Disc()
    f = flicker.measure(still, {"object": {n: still.at(0, n) for n in range(1, 151)}}, say=say).fields
    e, a = f["extent_px"]["object"], f["aperture_px"]["object"]
    check(e is not None and 13 <= e <= 20 and a > e and f["recentred"] == ["object"],
          "a disc 15 px in radius: its extent read off its own frames, the aperture wider and re-centred",
          f"extent {e}, aperture {a}")
    check(f["beats"] is False and not f.get("lost"), "a steady disc: no frame lost and no beat -- before, its ring lay on "
          "it and it was 'lost'", str(f.get("finding"))[:90])
    beating = _Disc(6.0, 0.2)
    f = flicker.measure(beating, {"object": {n: beating.at(0, n) for n in range(1, 151)}}, say=say).fields
    b = (f.get("beat") or {}).get("object") or {}
    check(f["beats"] is True and abs(b.get("hz", 0) - 6.0) < 0.3 and 0.15 < b.get("amplitude", 0) < 0.25,
          "the same disc beating 6 Hz by 20 %: 6 Hz, 20 %, measured whole", f"{b.get('hz')} Hz, {b.get('amplitude')}")


class _Smeared(_Beating):
    """PURSUE PR089's bird C after the sensor blank, built: a faint point (2.4 px across, 12 grey levels at its peak) with
    a trail of five fading echoes behind it and a pedestal of 3 grey levels out to 18 px -- what a compressed video makes
    of a faint mover -- going round a loop at about 2.5 px a frame over a sky in column bands 96 px wide, each band
    10 grey levels or so from the next, and grain. `peak` changes its height: at 90 the frames agree on its size."""
    W, H = 640, 480

    def __init__(self, peak=12.0):
        super().__init__([], v=(0.0, 0.0))
        self.peak = peak
        self.bands = np.repeat(np.random.default_rng(7).normal(0, 10, self.W // 96 + 1), 96)[:self.W]

    def at(self, j, n):
        a = 0.025 * n
        return 320.0 + 100.0 * np.cos(a), 240.0 + 60.0 * np.sin(a)

    def rgb(self, n):
        if n not in self.cache:
            g = 60 + self.bands[None, :] + np.random.default_rng(n).normal(0, 3, (self.H, self.W))
            x, y = self.at(0, n)
            x1, y1 = self.at(0, n + 1)
            ux, uy = (x1 - x) / np.hypot(x1 - x, y1 - y), (y1 - y) / np.hypot(x1 - x, y1 - y)
            yy, xx = np.mgrid[0:self.H, 0:self.W]
            g += 3.0 / (1 + np.exp((np.hypot(xx - x, yy - y) - 18.0) / 2.0))
            for k in range(6):
                cx, cy = x - 2.5 * k * ux, y - 2.5 * k * uy
                g += self.peak * 0.6 ** k * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 1.0 ** 2))
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


def test_a_faint_smeared_point_is_sized_off_its_stack():
    """PR089's bird C after a sensor blank (2026-10-23): a faint dot with a trail, over a sea in column bands. The single
    frames mostly found nothing standing out of the far ring, and on the others its profile never fell before the bands
    did, so the median of the few gave a 48-px radius and a 58-px aperture to a dot 5-9 px across, and nothing could be
    measured. Where the frames do not agree the size is read off the median of the stamps along the track, turned to its
    travel and read on the half ahead of it, against the level just outside it; where they agree, nothing changes."""
    print("\nflicker: a faint smeared point is sized off its stack")
    from mcdonald import flicker
    faint = _Smeared()
    ns = list(range(1, 151))
    how = {}
    sz = flicker.sizes(faint, {"object": {n: faint.at(0, n) for n in ns}}, ns, how=how)
    rec, (e, (ap, ring, _, _)) = how["object"], sz["object"]
    check(rec["used"] == "stack" and rec.get("along") is True and (rec["median"] is None or rec["median"] >= 15),
          "the single frames do not agree on its size -- the few that give one put it at 15 px or more, the trap -- so it is "
          "read off their stack, along its travel",
          f"{rec['read']} of {rec['frames']} frames gave a size (median {rec['median']}, spread {rec['spread']})")
    check(e is not None and 2 <= e <= 9 and ap <= 11,
          "the stack's size is the dot's, not the trail's, the pedestal's or the bands': 2-9 px, an aperture of 11 px or less",
          f"extent {e}, aperture {ap:.1f}, ring {ring}")
    bright = _Smeared(peak=90.0)
    how = {}
    sz = flicker.sizes(bright, {"object": {n: bright.at(0, n) for n in ns}}, ns, how=how)
    check(how["object"]["used"] == "frames" and sz["object"][0] == how["object"]["median"],
          "the same dot 7.5 times brighter: the frames agree, and their median is the size, as before",
          f"{how['object']['read']} of {how['object']['frames']}, spread {how['object']['spread']}, extent {sz['object'][0]}")
    class _Small(_Smeared):                      # the Svanstrom set's frames are this small: no stamp fits, none is read
        W, H = 320, 200

        def at(self, j, n):
            a = 0.025 * n
            return 160.0 + 100.0 * np.cos(a), 100.0 + 60.0 * np.sin(a)
    small = _Small()
    how = {}
    sz = flicker.sizes(small, {"object": {n: small.at(0, n) for n in ns}}, ns, how=how)
    check(how["object"]["fit"] == 0 and how["object"]["used"] == "frames" and sz["object"][0] is None
          and sz["object"][1][0] == flicker.APERTURE,
          "on a frame too small for any stamp, nothing is read and the point's aperture is kept, as before",
          f"{how['object']}")
    disc = _Disc()
    greys = [np.asarray(disc.rgb(n), float)[..., 0] for n in range(1, 151, 8)]
    xy = [disc.at(0, n) for n in range(1, 151, 8)]
    e1 = [flicker.extent(g, x, y) for g, (x, y) in zip(greys, xy)]
    e2, along = flicker.stacked_extent(greys, np.array([p[0] for p in xy]), np.array([p[1] for p in xy]))
    check(e2 is not None and abs(e2 - np.median(e1)) <= 2 and not along,
          "a steady disc 15 px in radius, read off its stack: within 2 px of its frames' median, and not turned",
          f"stack {e2}, frames {np.median(e1)}")


def test_a_point_like_things_disc_is_capped_and_its_ring_is_not():
    """The aperture study (2026-10-24): for a thing under POINT_EXTENT across, the ring and the background apertures stay
    where APERTURE_OVER times its extent puts them -- clear of it -- and the disc is no wider than POINT_DISC; a point keeps
    APERTURE as it was, and a wider thing (a disc 15 px in radius, test_the_aperture_follows_a_thing_wider_than_a_point)
    is measured whole."""
    print("\nflicker: a point-like thing's disc is capped, and its ring is not")
    from mcdonald import flicker
    p4, p5, p8, p9, p10 = (flicker.sized(r) for r in (4, 5, 8, 9, 10))
    check(p4 == (flicker.APERTURE, flicker.RING, 25, False) and p5[0] == 6.0 and p5[1] == (9.0, 13.5) and p5[3],
          "a point keeps the 4-px disc, its ring and the background apertures; a thing 5 px across, 6 px, its ring at 9-13.5 "
          "and re-centred, as before", f"{p4} {p5}")
    check(p8[0] == flicker.POINT_DISC and p8[1] == (9.6 + 3.0, 9.6 + 6.0 + 0.25 * 9.6) and p8[2] == int(np.ceil(2 * p8[1][1] + 5))
          and p9[0] == flicker.POINT_DISC and not p8[3] and not p9[3],
          "a thing 8 or 9 px across: a 6-px disc on the smoothed track, not re-centred, the ring and background apertures beyond "
          "1.2 times its extent", f"{p8} {p9}")
    check(abs(p10[0] - 12.0) < 1e-9 and p10[1][0] == 15.0 and p10[3],
          "a thing 10 px across (PR41's bird), at POINT_EXTENT: the disc follows its extent, re-centred, as before", f"{p10}")


class _OffMiddle(_Beating):
    """A steady body (a Gaussian 1.5 px wide) with a small light `off` px to one side beating at 8 Hz by 60 % -- a beat that
    sits off the object's middle, as a rotor's blades or a tail rotor's would (flicker's item 14) -- or, at off 0, a point
    whose own brightness beats. Drifting 0.3 px a frame; the track follows the body."""

    def __init__(self, off=5.0):
        super().__init__([], v=(0.3, 0.2))
        self.off = off

    def at(self, j, n):
        return 200.0 + self.v[0] * n, 150.0 + self.v[1] * n

    def rgb(self, n):
        if n not in self.cache:
            g = 60 + np.random.default_rng(n).normal(0, 2, (self.H, self.W))
            x, y = self.at(0, n)
            yy, xx = np.mgrid[0:self.H, 0:self.W]
            beat = 1 + 0.6 * np.sin(2 * np.pi * 8.0 * n / self.fps)
            if self.off:
                g += 120 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.5 ** 2))
                g += 60 * beat * np.exp(-((xx - x - self.off) ** 2 + (yy - y) ** 2) / 2.0)
            else:
                g += 120 * beat * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.5 ** 2))
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


def test_a_beat_off_the_middle_is_marked_as_a_rotors_look():
    """Flicker's item 14 (2026-10-25): of the Svanstrom set's tracks that would be named birds, the helicopters' beats sat off
    the object's middle or reached the background beside it in step; the birds' did not. A light 5 px off a steady body that
    beats is marked (the fold's offset over ROTOR_OFFSET_PX); a point whose own brightness beats is not. Both in a fixed 8-px
    disc: the size read off a ring's median does not see a small light to one side, and the point's disc would miss it."""
    print("\nflicker: a beat off the middle is marked as a rotor's look")
    from mcdonald import flicker
    say = lambda *a: None
    side = _OffMiddle(5.0)
    f = flicker.measure(side, {"object": {n: side.at(0, n) for n in range(1, 151)}}, say=say, aperture="8").fields
    b = (f.get("beat") or {}).get("object") or {}
    r = b.get("rotor") or {}
    check(f["beats"] is True and abs(b.get("hz", 0) - 8.0) < 0.3 and "off its middle" in r.get("marked", [])
          and r.get("offset_px", 0) >= flicker.ROTOR_OFFSET_PX,
          "a light 5 px off a steady body beating at 8 Hz: the beat is found, and marked as sitting off its middle",
          f"{b.get('hz')} Hz, rotor {r}")
    mid = _OffMiddle(0.0)
    f = flicker.measure(mid, {"object": {n: mid.at(0, n) for n in range(1, 151)}}, say=say, aperture="8").fields
    b = (f.get("beat") or {}).get("object") or {}
    check(f["beats"] is True and not (b.get("rotor") or {}).get("marked"),
          "a point whose own brightness beats: found, and not marked", f"{b.get('hz')} Hz, rotor {b.get('rotor')}")


def test_a_beat_of_its_own_is_drawn_and_no_beat_is_not():
    """Every case the flicker stage flags with a beat comes with its figure (PR41, 2026-10-10): the beat
    curve and its spectrum beside the background's, `<case>_beat.png`, listed in the stage's files so the
    report shows it. A point with no beat gets none."""
    print("\nflicker: a beat is drawn, no beat is not")
    from mcdonald import flicker
    say = lambda *a: None
    with tempfile.TemporaryDirectory() as td:
        one = _Beating([(8.0, 0.2, 0)])
        found = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, out=f"{td}/beat", say=say)
        png = Path(f"{td}/beat_beat.png")
        check(found.fields["beats"] is True and png.exists() and png.stat().st_size > 20000 and any(Path(f) == png for f in found.files),
              "an 8-Hz beat of its own: <case>_beat.png drawn and listed with the stage's files",
              f"{png.stat().st_size if png.exists() else 0} bytes; files {found.files}")
        still = _Beating([(0, 0, 0)])
        found = flicker.measure(still, {"member 0": {n: still.at(0, n) for n in range(1, 151)}}, out=f"{td}/still", say=say)
        check(found.fields["beats"] is False and not Path(f"{td}/still_beat.png").exists(),
              "a constant point: no beat, and no beat figure", str(found.files))


def test_a_point_lost_against_what_is_behind_it_is_not_heard_as_a_beat():
    """PR23 (2026-10-09), a look-down clip over a town: the object crossed a hot roof, its brightness over the
    ring fell to nothing and below for seven frames, and that one dip, read as a beat at 2.1 Hz, made "a bird"
    the report's leading explanation. A point of constant brightness that vanishes for seven frames: the dip
    alone stands far over the background beside it, as PR23's did; the stage finds the seven frames, leaves
    them out, and hears no beat."""
    print("\nflicker: a point lost against what is behind it")
    from mcdonald import flicker
    level = np.ones(152)
    level[70:77] = 0.0
    clip = _Shown(level)
    track = {n: clip.at(0, n) for n in range(1, 151)}
    raw = flicker.curves(clip, {"object": track}, list(range(1, 151)))
    dip = flicker.peak(raw["object"], clip.fps)
    found = flicker.measure(clip, {"object": track}, say=lambda *a: None)
    f = found.fields
    check(dip["amplitude"] >= 3 * flicker.ABOVE * f["noise_floor"],
          "the dip alone is a 'beat' far over the background beside it -- the trap", f"{dip['hz']:.2f} Hz, {dip['amplitude']:.1%} "
          f"against {f['noise_floor']:.1%}")
    check((f.get("lost") or {}).get("object") == list(range(70, 77)), "the seven frames it vanishes on are the ones found lost",
          str(f.get("lost")))
    check(f["beats"] is False and "frames 70–76, where it was lost against what is behind it, are left out" in f["finding"]
          and any("Lost against what is behind it" in n for n in found.notes),
          "they are left out, the finding and the notes say so, and there is no beat", f["finding"][:120])
    gone = np.ones(152)
    gone[20:60] = 0.0                                      # lost for 40 of 150 frames: too many to hear anything in
    many = _Shown(gone)
    g = flicker.measure(many, {"object": {n: many.at(0, n) for n in range(1, 151)}}, say=lambda *a: None)
    check(g.fields["beats"] is None and "lost against what is behind it on 40 of its 150 frames" in g.no_power[0][1],
          "lost on 40 of its 150 frames: no beat is looked for, and it says why", g.no_power[0][1][:100] if g.no_power else "")


def test_a_beating_point_under_its_ring_at_every_trough_is_measured():
    """PR097's dark dots (2026-10-15): a point beating at 25-60 % of its brightness falls under DROP of its level
    for a frame or two at every trough, so `lost` marked a fifth of its frames and the stage refused the clearest
    beaters in the clip. Those frames come in short runs, one per cycle, at the troughs of the curve's own beat:
    they are kept, the beat is measured, and the finding says why. PR23's seven-frame crossing (the test above)
    is still left out, and a block of 40 lost frames is still refused."""
    print("\nflicker: a point that goes under its ring at every trough of its own beat")
    from mcdonald import flicker
    n = np.arange(152)
    clip = _Shown(1 + 0.75 * np.sin(2 * np.pi * 6.5 * n / 30.0))
    track = {k: clip.at(0, k) for k in range(1, 151)}
    raw = flicker.curves(clip, {"object": track}, list(range(1, 151)))
    bad = flicker.lost(raw["object"], clip.fps)
    check(bad.sum() > flicker.LOST_MAX * len(bad), "the guard alone would refuse it: under its ring on more than a tenth of its frames",
          f"{bad.sum()} of {len(bad)}")
    found = flicker.measure(clip, {"object": track}, say=lambda *a: None)
    f = found.fields
    lab = (f.get("lost_at_beat") or {}).get("object")
    check(lab is not None and lab["runs"] >= flicker.LOST_RUNS and abs(lab["hz"] - 6.5) < 0.3 and lab["share"] >= flicker.LOST_TROUGH,
          "the lost frames come in short runs at the troughs of a 6.5-Hz beat, and the fields say so", str(lab))
    check(f.get("beats") is True and abs(f["beat"]["object"]["hz"] - 6.5) < 0.3 and not found.no_power,
          "so the beat is measured, not refused", (f.get("finding") or str(found.no_power))[:140])
    check("troughs of its own" in (f.get("finding") or "") and any("troughs of its own strongest beat" in m for m in found.notes),
          "and the finding and the notes say the frames were kept", (f.get("finding") or "")[-160:])


def test_a_dip_with_a_few_stray_lost_frames_is_still_left_out():
    """The troughs rule's other side (2026-10-16): PR23's roof crossing is one dip of seven frames, and the golden track
    has two more single frames under the ring elsewhere -- three runs with a median of one, which the rule as first
    written took for the troughs of a beat (any low-frequency wobble of the filled curve puts the dip in its lower half).
    The WA9ONY-5 balloon likewise. A dip with a couple of stray lost frames is a crossing: the frames are found lost,
    left out, and no beat is read from them."""
    print("\nflicker: one dip and two stray lost frames are a crossing, not the troughs of a beat")
    from mcdonald import flicker
    n = np.arange(212)
    level = np.ones(212)
    level[131:138] = 0.0                                      # the roof: seven frames under the ring
    level[40] = 0.0                                           # and two stray frames
    level[170] = 0.0
    rng = np.random.default_rng(23)
    level += 0.03 * rng.standard_normal(212)                  # grain, so the filled curve has a strongest peak somewhere
    clip = _Shown(np.clip(level, 0, None))
    track = {k: clip.at(0, k) for k in range(1, 209)}
    raw = flicker.curves(clip, {"object": track}, list(range(1, 209)))
    bad = flicker.lost(raw["object"], clip.fps)
    runs = flicker.runs_of(bad)
    check(3 <= len(runs) <= 4 and np.median([b - a for a, b in runs]) <= flicker.LOST_RUN,
          "the lost frames come in three short runs, which the first rule's run test let through", f"runs {runs}")
    check(flicker.lost_at_beat(np.asarray(raw["object"], float), bad, clip.fps) is None,
          "but they are not the troughs of a beat: the rule refuses them")
    found = flicker.measure(clip, {"object": track}, say=lambda *a: None)
    f = found.fields
    lost = (f.get("lost") or {}).get("object") or []
    check(set(range(132, 138)) <= set(lost) and len(lost) <= 10 and not f.get("lost_at_beat"),
          "so the frames are found lost and left out, as PR23's are", str(lost))
    check(f.get("beats") is not True, "and no beat is read from the dip", (f.get("finding") or str(found.no_power))[:140])


def test_the_troughs_are_kept_only_for_the_beat_they_belong_to():
    """The second half of the troughs rule (2026-10-16), on the numbers of the whole-video pass's refused objects
    measured again: PR097's three dark dots beat at 6.94, 6.69 and 2.34 Hz, at troughs of 7.16, 6.72 and 2.28 -- theirs;
    two objects of PR149 beat (in one or two windows) at 9.16 and 4.84 Hz against troughs of 3.13 and 3.07 -- not
    theirs, so their frames stay lost, as before. And a beat read as a fundamental with its double is at its troughs
    where the troughs are at the double (the brightness beats twice a stroke)."""
    print("\nflicker: the troughs are kept only where the beat found is the one they belong to")
    from mcdonald import flicker
    for beat, at, want in (({"hz": 6.94, "double_hz": None}, {"hz": 7.16}, True), ({"hz": 6.69, "double_hz": None}, {"hz": 6.72}, True),
                           ({"hz": 2.34, "double_hz": None}, {"hz": 2.28}, True), ({"hz": 9.16, "double_hz": None}, {"hz": 3.13}, False),
                           ({"hz": 4.84, "double_hz": None}, {"hz": 3.07}, False), ({"hz": 3.9, "double_hz": 7.8}, {"hz": 7.7}, True),
                           ({"hz": 3.9, "double_hz": None}, {"hz": 7.7}, False)):
        got = flicker.at_the_troughs(beat, at)
        check(got is want, f"a beat at {beat['hz']}{' (double ' + str(beat['double_hz']) + ')' if beat['double_hz'] else ''} Hz "
                           f"with troughs at {at['hz']} Hz: {'theirs' if want else 'not theirs'}", str(got))
    check(flicker.LOST_RUNS >= 6, "troughs are suspected from six runs or more (PR23's roof and the balloon have three)", str(flicker.LOST_RUNS))


def test_a_beat_where_a_supply_would_fold_is_marked_as_a_look_alike():
    """The look-alikes (2026-10-16, the SETI survey's first port): a lamp on 50-Hz mains flickers at 100 Hz, an
    aircraft's lights on its 400-Hz power at 400 or 800 Hz, and a video at 30 frames a second folds every one of them
    to 10 Hz (9.19-10.39 at 29.97), where small birds beat. The table for the clip's frame rate is in the fields, a
    beat within its resolution of one is marked with it -- marked, not refused -- and the finding says so."""
    print("\nflicker: the look-alikes of a frame rate, and a beat at one of them marked, not refused")
    from mcdonald import flicker
    at10 = {d["source"] for d in flicker.lookalikes(30.0) if abs(d["hz"] - 10.0) < 0.01}
    check({"50 Hz", "100 Hz", "400 Hz", "800 Hz", "fps/3"} <= at10,
          "at 30 frames a second 50, 100, 400 and 800 Hz all fold to 10 Hz, with a rhythm on every third frame", str(sorted(at10)))
    hz = {d["source"]: d["hz"] for d in flicker.lookalikes(30000 / 1001)}
    check(abs(hz["50 Hz"] - 9.94) < 0.01 and abs(hz["100 Hz"] - 10.09) < 0.01 and abs(hz["400 Hz"] - 10.39) < 0.01
          and abs(hz["800 Hz"] - 9.19) < 0.01, "at 29.97 they spread to 9.19-10.39 Hz", str(hz))
    check("60 Hz" not in hz and "120 Hz" not in hz and all(v >= flicker.LOW for v in hz.values()),
          "60-Hz mains and its lamps fold to nought there, so they are not in the band", str(sorted(hz)))
    T60 = {d["source"]: d["hz"] for d in flicker.lookalikes(60.0)}
    check(abs(T60["50 Hz"] - 10.0) < 0.01 and abs(T60["100 Hz"] - 20.0) < 0.01,
          "at 60 frames a second 50 Hz folds to 10 and a lamp on it to 20", str(T60))
    ten = _Beating([(10.0, 0.2, 0)])
    track = {k: ten.at(0, k) for k in range(1, 151)}
    found = flicker.measure(ten, {"object": track}, say=lambda *a: None)
    f = found.fields
    b = f["beat"]["object"]
    check(f["beats"] is True and abs(b["hz"] - 10.0) < 0.3, "a planted 10-Hz beat is still the object's own", (f.get("finding") or "")[:100])
    srcs = {d["source"] for d in b.get("lookalike") or []}
    third = abs(b["hz"] - ten.fps / 3) <= flicker.Z_LINE * b["hz_err"]
    check({"50 Hz", "100 Hz"} <= srcs and ("fps/3" in srcs) == third,
          "and it is marked with the supplies' look-alikes within its resolution -- and with every third frame's rhythm "
          "only within three of its errors, as that has no width (2026-10-17)",
          f"{sorted(srcs)}; {b['hz']:.3f} ± {b['hz_err']:.3f} Hz against fps/3 = {ten.fps / 3:.3f}")
    table = flicker.lookalikes(30.0)
    near = lambda hz, err: {d["source"] for d in flicker.at_lookalikes(hz, 0.5, table, err)}
    check("fps/3" in near(10.0, 0.01) and "fps/3" not in near(10.1, 0.01) and "100 Hz" in near(10.1, 0.01),
          "a beat on the 3rd frame's 10 Hz is marked with it; one 0.1 Hz off, known to 0.01, is not -- but a supply's line, "
          "which has a width, still marks it within the resolution", f"{sorted(near(10.0, 0.01))} / {sorted(near(10.1, 0.01))}")
    check(f.get("lookalikes") and "look-alike" in (f.get("finding") or "") and any("marked, not refused" in m for m in found.notes),
          "the table is in the fields, and the finding and the notes say so", (f.get("finding") or "")[-140:])
    # 3.5 Hz, not the 8.5 of the first version: since the bands (2026-10-20) 8.5 Hz is inside a sky lantern's 4.7-8.7 Hz
    # and the 400-Hz bus as heard (8.80-11.66 at 29.97), so it is no longer clear of them all
    far = _Beating([(3.5, 0.2, 0)])
    track = {k: far.at(0, k) for k in range(1, 151)}
    f = flicker.measure(far, {"object": track}, say=lambda *a: None).fields
    check(f["beats"] is True and not f["beat"]["object"].get("lookalike") and "look-alike" not in (f.get("finding") or ""),
          "a planted 3.5-Hz beat, clear of them all, carries none", str(f["beat"]["object"].get("lookalike")))


def test_look_alikes_that_are_bands_and_those_that_cover_the_band():
    """The bands (item 11, 2026-10-20; the bird paper's chain-rate table): the 400-Hz power aircraft sound actually
    records, 398.41-401.27 Hz, folds to 8.41-11.27 Hz at 30 frames a second and 8.80-11.66 at 29.97, and a lamp on it
    twice that; a sky lantern's flame puffs at 4.7-8.7 Hz and a bundle of candles near 10, unfolded; a rotor's, a
    propeller's and a multirotor's blade-pass and a cooler's drive fold over the whole band at video rates, so they are
    listed and mark nothing. A beat inside a band is marked with it, within the resolution of its edges."""
    print("\nflicker: look-alikes that are bands, and the bands that cover the whole band")
    from mcdonald import flicker
    fb = lambda lo, hi, fps: [(round(a, 2), round(b, 2)) for a, b in flicker.fold_band(lo, hi, fps)]
    check(fb(398.41, 401.27, 30.0) == [(8.41, 11.27)] and fb(398.41, 401.27, 30000 / 1001) == [(8.8, 11.66)],
          "the bus as heard lands at 8.41-11.27 Hz at 30 frames a second and 8.80-11.66 at 29.97",
          f"{fb(398.41, 401.27, 30.0)} / {fb(398.41, 401.27, 30000 / 1001)}")
    check(fb(10, 30, 30.0) == [(0.0, 15.0)] and fb(4.7, 8.7, 30.0) == [(4.7, 8.7)] and fb(14, 16, 30.0) == [(14.0, 15.0)],
          "a rotor's 10-30 Hz covers 0-15 at 30; a lantern's 4.7-8.7 is not folded; a band across Nyquist folds onto itself",
          f"{fb(10, 30, 30.0)} {fb(4.7, 8.7, 30.0)} {fb(14, 16, 30.0)}")
    table = flicker.lookalikes(30.0)
    bands = {d["source"]: d for d in table if d.get("band") is not None}
    check(all(bands[k]["covers"] for k in ("rotor", "propeller", "multirotor", "cryocooler"))
          and not any(bands[k]["covers"] for k in ("400-Hz bus, as heard", "sky lantern", "candle flames")),
          "at 30 frames a second the rotor, propeller, multirotor and cooler bands cover the band; the bus, lantern and "
          "candles do not", str({k: d["covers"] for k, d in bands.items()}))
    near = lambda hz: {d["source"] for d in flicker.at_lookalikes(hz, 0.1, table, 0.03)}
    check({"400-Hz bus, as heard", "sky lantern"} <= near(8.5) and not near(3.5) & set(bands)
          and not near(8.5) & {"rotor", "propeller", "multirotor", "cryocooler"},
          "a beat at 8.5 Hz is inside the bus as heard and the lantern's band; one at 3.5 Hz is in none; a band that covers "
          "everything marks nothing", f"8.5: {sorted(near(8.5))}; 3.5: {sorted(near(3.5))}")
    check("candle flames" in near(10.59) and "400-Hz bus, as heard" in near(10.59) and "50 Hz" not in near(10.59),
          "PR088's 10.59 Hz is inside the candles' and the heard bus's bands, though 0.59 Hz off the 400.000-Hz line",
          str(sorted(near(10.59))))
    lantern = _Beating([(6.0, 0.2, 0)])
    track = {k: lantern.at(0, k) for k in range(1, 151)}
    found = flicker.measure(lantern, {"object": track}, say=lambda *a: None)
    f = found.fields
    srcs = {d["source"] for d in f["beat"]["object"].get("lookalike") or []}
    check(f["beats"] is True and "sky lantern" in srcs and "inside the band of" in (f.get("finding") or "")
          and any("excludes none of them" in m for m in found.notes),
          "a planted 6.0-Hz beat is marked with the lantern's band, the finding says it is inside it, and the notes say once "
          "that frequency excludes none of the bands that cover everything", (f.get("finding") or "")[-160:])


def test_steadiness_tells_a_clock_from_a_beat_that_wanders():
    """Steady as a clock, or not (item 12, 2026-10-20; the information-theory survey's D2). Planted steady beats in grain
    (PR135's length, 150 frames at 29.97) are not called wandering; beats whose rate steps 5 % between the halves (the
    Galileo birds and PR135's members wander 2-5 %) are; a stretch too short for two halves of MIN_FRAMES is not read
    (NO POWER); a long one is cut in 4-s pieces; and the stage carries it for every beat, its notes saying it where the
    beat sits at a look-alike."""
    print("\nflicker: steadiness against planted clocks")
    from mcdonald import flicker
    rng = np.random.default_rng(7)
    fps, n = 30000 / 1001, 150
    t = np.arange(n) / fps

    def curve(f_of_t, amp=0.15, noise=0.06):
        return amp * np.cos(2 * np.pi * np.cumsum(f_of_t(t)) / fps + rng.uniform(0, 2 * np.pi)) + noise * rng.standard_normal(n)
    steady = [flicker.steadiness(curve(lambda t: 7.6 + 0 * t), fps, 7.6, runs=100, seed=k) for k in range(12)]
    wander = [flicker.steadiness(curve(lambda t: np.where(t < t[-1] / 2, 7.4, 7.8)), fps, 7.6, runs=100, seed=k) for k in range(8)]
    check(sum(s["wanders"] for s in steady) <= 1 and all(s["power"] for s in steady),
          "of 12 planted steady beats, at most 1 is called wandering", str([round(s["p"], 2) for s in steady]))
    check(sum(s["wanders"] for s in wander) >= 7,
          "of 8 beats that step 7.4 -> 7.8 Hz between the halves, 7 or more are", str([round(s["p"], 3) for s in wander]))
    short = flicker.steadiness(curve(lambda t: 7.6 + 0 * t)[:100], fps, 7.6)
    check(short["power"] is False and short["p"] is None and "too short" in (short["why"] or ""),
          "100 frames are too short for two halves of 60: not read", str(short["why"]))
    long_t = np.arange(600) / 30.0                       # 20 s at 30 frames a second: five pieces of 120 frames
    long_r = 0.15 * np.cos(2 * np.pi * 6.0 * long_t) + 0.05 * rng.standard_normal(len(long_t))
    lng = flicker.steadiness(long_r, 30.0, 6.0, runs=20)
    check(lng["pieces"] == 5 and len(lng["hz"]) == 5, "a 20-s stretch is read in five 4-s pieces", str(lng["hz"]))
    ten = _Beating([(10.0, 0.2, 0)])
    track = {k: ten.at(0, k) for k in range(1, 151)}
    found = flicker.measure(ten, {"object": track}, say=lambda *a: None)
    st = found.fields.get("steadiness", {}).get("object") or {}
    check(st.get("power") and st.get("p") is not None and st.get("frames") == [1, 150] and not st.get("wanders")
          and any("steady beats planted" in m for m in found.notes),
          "the stage reads a planted 10-Hz beat over its frames, finds it as steady as a clock, and says so where it sits "
          "at a look-alike", f"p {st.get('p')}; " + next((m[-160:] for m in found.notes if "steady beats" in m), ""))


def test_a_light_that_flashes_in_a_train():
    """Item 13 (2026-10-20, a council member's question): an aircraft's anti-collision light flashes 40-100 times a minute.
    On planted curves: a train of 0.2-s flashes at 1.00 Hz is read as a train at its rate, with the anti-collision rule;
    one at 2.5 Hz is said to be two lights overlapping; flashes at random times are not a train (at most 1 in 12, at p
    0.01); a sinusoid as strong has no flashes at all; a flat-topped flash is timed at its middle, not its highest frame;
    and with the flashes taken out, the train's own harmonic -- what the stage would hear as a beat -- loses most of its
    amplitude. On a planted clip -- a dark body carrying a small light -- the stage finds a red light's train in the
    reddest pixels and a white one's in the brightest, where the body hides it from the sum; the background beside it
    does not flash; a body with no light has no train; and the report's bottom line says the rate."""
    print("\nflicker: a light that flashes in a train (item 13)")
    from mcdonald import flicker, report
    fps, n = 30000 / 1001, 330
    t = np.arange(n) / fps
    rng = np.random.default_rng(11)

    def train(rate, start=0.6, width=0.2, jitter=0.0):
        f = 100 + rng.normal(0, 1, n)
        for c in np.arange(start, t[-1] - 0.5, 1 / rate):
            c = c + rng.normal(0, jitter)
            f[(t >= c) & (t < c + width)] += 25
        return f
    one = flicker.blinks(train(1.0), fps, runs=500)
    check(one["train"] and abs(one["hz"] - 1.0) < 0.01 and one["rule"] == "anti-collision" and one["flashes"] >= 9,
          "0.2-s flashes at 1.00 Hz: a train at 1.00 Hz, 60 a minute, an anti-collision light's rate",
          f"{one['flashes']} flashes, {one['hz']} Hz, p {one['p']}, {one['rule']}")
    two = flicker.blinks(train(2.5, width=0.1), fps, runs=500)
    check(two["train"] and abs(two["hz"] - 2.5) < 0.03 and two["rule"] == "overlap",
          "0.1-s flashes at 2.5 Hz: a train, faster than one light may flash, as two lights overlapping",
          f"{two['hz']} Hz, p {two['p']}, {two['rule']}")
    rand = []
    for k in range(12):
        f = 100 + rng.normal(0, 1, n)
        for c in rng.uniform(0.5, t[-1] - 0.6, 8):
            f[(t >= c) & (t < c + 0.2)] += 25
        rand.append(flicker.blinks(f, fps, runs=500, seed=k))
    check(sum(r["train"] for r in rand) <= 1, "eight flashes at random times, twelve times over: at most one is called a train",
          str([r.get("p") for r in rand]))
    sine = flicker.blinks(100 + 25 * np.sin(2 * np.pi * 7.0 * t) + rng.normal(0, 1, n), fps, runs=100)
    check(sine["flashes"] == 0 and not sine["train"], "a 7-Hz sinusoid as strong has no flashes", str(sine["flashes"]))
    flat = 100 + rng.normal(0, 0.5, n)
    for c in (2.0, 4.0, 6.0, 8.0):
        flat[(t >= c) & (t < c + 0.3)] += 25
        flat[int(round((c + 0.27) * fps))] += 3                      # the highest frame at the end of a flat top
    fl, _ = flicker.flashes(flat, fps)
    mids = [c_ / fps for _, _, c_, _ in fl]
    check(len(fl) == 4 and all(abs(m - (c + 0.15)) < 0.05 for m, c in zip(mids, (2.0, 4.0, 6.0, 8.0))),
          "a flat-topped flash is timed at its middle, not at its highest frame", str([round(m, 3) for m in mids]))
    f = train(1.0)
    r = flicker.blinks(f, fps, runs=100)
    kept = flicker.amp_at(flicker.deflash(f, r["runs"]), fps, 3.0) / flicker.amp_at(f, fps, 3.0)
    check(kept < flicker.BLINK_KEEP, "with the flashes taken out, the train's third harmonic keeps under half its amplitude",
          f"kept {kept:.0%}")

    red = _Flasher(1.0, "red")
    track = {k: red.at(0, k) for k in range(1, red.n1 + 1)}
    import csv, tempfile
    with tempfile.TemporaryDirectory() as td:
        found = flicker.measure(red, {"object": track}, dark=True, say=lambda *a: None, out=f"{td}/flasher")
        rows = list(csv.DictReader(open(f"{td}/flasher_flicker.csv", encoding="utf-8")))
    heads = list(rows[0]) if rows else []
    check("object white" in heads and "object red" in heads and any(h.startswith("background light") for h in heads)
          and sum(1 for r in rows if r["object red"] != "") > 0.9 * len(rows),
          "the light curves are written beside the brightness in <out>_flicker.csv, the object's and its controls'",
          ", ".join(h for h in heads if "white" in h or "red" in h)[:160])
    b = (found.fields.get("blink") or {}).get("object") or {}
    check(b.get("train") and b.get("best") == "red" and abs((b.get("hz") or 0) - 1.0) < 0.02 and b.get("rule") == "anti-collision"
          and not b.get("controls") and any("regular train" in m for m in found.notes),
          "a dark body's red light at 1.00 Hz: a train in its reddest pixels, an anti-collision light's rate, the background "
          "beside it quiet, and the notes say it", f"{b.get('best')} {b.get('hz')} Hz p {b.get('p')} {b.get('rule')}; "
                                                    f"controls {b.get('controls')}")
    nbg, read = b.get("controls_n") or 0, b.get("controls_read")
    check(nbg and read is not None and len(read) == nbg and any(f"None of the {nbg} background apertures" in m for m in found.notes),
          "every background aperture beside it is read, and the note counts them", f"{len(read or [])} of {nbg}")
    off = flicker.said_blink("object", dict(b, controls_read=read[:1]), nbg=nbg)
    gone = flicker.said_blink("object", dict(b, controls_read=[]), nbg=nbg)
    check(f"Only 1 of the {nbg} background apertures" in off and "could be read (off the frame" in gone and "nothing here says" in gone,
          "controls off the frame are not counted as quiet: the note says how many were read, and that none means no control",
          off[off.index("Only"):][:90] if "Only" in off else off[-120:])
    sums = (b.get("curves") or {}).get("brightness") or {}
    check(not sums.get("train"), "the body hides the light from the aperture's sum", str({k: sums.get(k) for k in ("flashes", "p")}))
    white = _Flasher(0.8, "white", width=0.15)
    found_w = flicker.measure(white, {"object": track}, dark=True, say=lambda *a: None)
    w = (found_w.fields.get("blink") or {}).get("object") or {}
    wc = w.get("curves") or {}
    check(w.get("train") and abs((w.get("hz") or 0) - 0.8) < 0.02 and (wc.get("white") or {}).get("train")
          and not (wc.get("red") or {}).get("train"),
          "a white light at 0.80 Hz: a train in its brightest pixels (on a body this small, in its sum too), none in its reddest",
          f"{w.get('best')} {w.get('hz')} Hz; red {((w.get('curves') or {}).get('red') or {}).get('flashes')} flashes")
    hot = _Flasher(1.0, "black-hot")
    found_h = flicker.measure(hot, {"object": track}, dark=True, black_hot=True, say=lambda *a: None)
    h = (found_h.fields.get("blink") or {}).get("object") or {}
    h0 = (flicker.measure(hot, {"object": track}, dark=True, say=lambda *a: None).fields.get("blink") or {}).get("object") or {}
    hw = (h.get("curves") or {}).get("white") or {}
    check(h.get("train") and abs((h.get("hz") or 0) - 1.0) < 0.02 and hw.get("train") and not h0.get("train")
          and "hottest pixels" in flicker.said_blink("object", dict(h, best="white"), nbg=h.get("controls_n") or 0),
          "on a black-hot display a light is dark, as the hot body is: with black_hot a train, in its hottest (darkest) "
          "pixels too, said so; none read the white-hot way",
          f"{h.get('best')} {h.get('hz')} Hz p {h.get('p')}; hottest pixels p {hw.get('p')}; without: {h0.get('train')}")
    none = _Flasher(0)
    found_n = flicker.measure(none, {"object": track}, dark=True, say=lambda *a: None)
    check(not ((found_n.fields.get("blink") or {}).get("object") or {}).get("train"), "a body with no light has no train")
    case = report.Case("flasher", "synthetic")
    case.add("flicker", result=found.result, fields=found.fields, no_power=found.no_power)
    bl = case.bottom_line()
    bl = " ".join(bl) if isinstance(bl, (list, tuple)) else str(bl)
    check("anti-collision light" in bl and "1.00 Hz" in bl, "the report's bottom line says the light's rate",
          next((x for x in bl.split(". ") if "train" in x), bl[-200:]))
    row = next((r for r in case.summary() if r[0].startswith("flashing light")), None)
    check(row is not None and row[2].startswith("60 a minute") and "anti-collision" in row[3],
          "and the summary has a row for it, the rate a minute first (the card's \"Light\")", str(row))


def test_the_scenes_own_motion_at_the_beat():
    """`--scene-shift` (2026-10-20; the bird paper's chain-rate table): does the sensor's own motion sit at the beat? A
    whole picture jittered 0.3 px at the object's own 6-Hz beat is read as the sensor moving there, and its shift comes
    back near 0.3 px; the same scene held still is not, and its planted 0.05-px shift comes back near its size; a
    featureless sky has nothing to register (NO POWER). The object's own centroid is read beside it."""
    print("\nflicker: the scene's own motion at the beat (--scene-shift)")
    from mcdonald import flicker
    said = {}
    for name, clip in (("jitter", _Jittered([(6.0, 0.25, 0)], jitter=0.3, jitter_hz=6.0)),
                       ("still", _Jittered([(6.0, 0.25, 0)], jitter=0.0)), ("flat", _Jittered([(6.0, 0.25, 0)], flat=True))):
        track = {k: clip.at(0, k) for k in range(1, 151)}
        found = flicker.measure(clip, {"object": track}, say=lambda *a: None, scene=True)
        said[name] = (found.fields.get("scene_shift") or {}, found)
    jit, still, flat = (said[k][0] for k in ("jitter", "still", "flat"))
    j, s = jit.get("object") or {}, still.get("object") or {}
    check(jit.get("scene", {}).get("power") and j.get("moves") and 0.2 <= (j.get("at_beat_px") or 0) <= 0.4,
          "a picture jittered 0.3 px at the beat: the sensor moves there, and by about that much",
          f"{j.get('at_beat_px')} px, stands {j.get('stands')}, registered {jit.get('scene', {}).get('registered')}")
    check(still.get("scene", {}).get("power") and s.get("moves") is False and (s.get("at_beat_px") or 1) < 0.02
          and 0.7 <= (s.get("recovered") or 0) <= 1.3,
          "the same scene held still: no jitter there, and a planted 0.05-px shift comes back near its size",
          f"{s.get('at_beat_px')} px, planted read {s.get('recovered')}")
    check(flat.get("scene", {}).get("power") is False and "no texture" in (flat.get("scene", {}).get("why") or ""),
          "a featureless sky has nothing to register: not read", str(flat.get("scene")))
    check(any("no jitter of the sensor there" in m for m in said["still"][1].notes)
          and any("the sensor moves at the beat" in m for m in said["jitter"][1].notes),
          "the notes say which", next((m[:150] for m in said["jitter"][1].notes if "scene's own motion" in m), ""))


def test_a_frequency_is_known_to_its_error_and_the_codecs_mark_is_held_to_it():
    """Frequencies with their errors (2026-10-17; the information-theory survey's D1, ROADMAP.md 0.3 objective 2). The
    resolution 1/T says when two sinusoids in one curve can be told apart; how well one is known is its error, a block
    bootstrap in the curve's own residual floored at the Cramer-Rao bound (`hz_error`). Planted in grain over 4.5 s
    (PR135's length), the frequency falls within three of its errors of the truth as often as it should, and the error is
    the scatter's size, a small part of the resolution. The codec's mark is held to it: a rhythm on the codec's line is
    marked every time, and a strong beat a quarter of a hertz beside it in a 2-s window is not -- which the mark at the
    resolution, 0.5 Hz there, refused every time: the slice of the bird band no window passed on 93 of 112 sensor videos."""
    print("\nflicker: a frequency's error, and the codec's mark held to it")
    from mcdonald import flicker
    fps = 30000 / 1001
    line = fps / 4
    rng = np.random.default_rng(3)
    t = np.arange(136) / fps
    hz, err = [], []
    for _ in range(60):
        f = 1000 * (1 + 0.1 * np.sin(2 * np.pi * 7.1 * t + rng.uniform(0, 2 * np.pi))) + rng.normal(0, 70, len(t))
        p = flicker.peak(f, fps, err=True)
        hz.append(p["hz"])
        err.append(p["hz_err"])
    hz, err = np.array(hz), np.array(err)
    inside = float(np.mean(np.abs(hz - 7.1) <= 3 * err))
    check(inside >= 0.95 and 0.5 <= np.median(err) / hz.std() <= 2.0 and np.median(err) < 0.25 * fps / len(t),
          "a beat planted in grain over 4.5 s: within three of its errors of the truth, the error the scatter's size and a "
          "small part of the resolution", f"within 3 errors {inside:.0%}; error {np.median(err):.4f} Hz, scatter {hz.std():.4f}, "
          f"resolution {fps / len(t):.3f}")
    e = flicker.hz_error(flicker.deviation(f, fps), fps, p["hz"])
    check(e["hz_err"] >= e["bound"] and e["hz_err"] >= e["grid"] and e["hz_err"] == max(e["boot"], e["bound"], e["grid"]),
          "the error is the bootstrap's, never under the Cramer-Rao bound or the spectrum's own step",
          str({k: round(v, 5) for k, v in e.items()}))
    t = np.arange(60) / fps
    on, beside, old = 0, 0, 0
    for _ in range(30):
        f = 1000 * (1 + 0.05 * np.sin(2 * np.pi * line * t + rng.uniform(0, 2 * np.pi))) + rng.normal(0, 20, len(t))
        on += flicker.peak(f, fps, [line])["at_the_codec_line_hz"] == line
        f = 1000 * (1 + 0.2 * np.sin(2 * np.pi * (line + 0.25) * t + rng.uniform(0, 2 * np.pi))) + rng.normal(0, 50, len(t))
        p = flicker.peak(f, fps, [line])
        beside += p["at_the_codec_line_hz"] is None
        old += flicker.at_line(p["hz"], None, [line], p["resolution_hz"]) is not None
    check(on == 30, "a rhythm on the codec's line is marked at it, every time", f"{on} of 30")
    check(beside >= 28 and old == 30, "a strong beat 0.25 Hz beside it in a 2-s window is not -- which the mark at the "
          "resolution was, every time", f"clear of the line {beside} of 30; by the resolution marked {old} of 30")
    bg = [rng.normal(0, 10, len(t)) for _ in range(4)]          # background apertures, in the object's brightness
    f = 1000 * (1 + 0.2 * np.sin(2 * np.pi * (line + 0.25) * t)) + rng.normal(0, 20, len(t))
    w = flicker.window_test(f, bg, fps, [line], 0.8 * fps / 2)
    check(w["passes"] and not w["passes_by_resolution"] and w["codec_by_resolution_hz"] == line and w["at_the_codec_line_hz"] is None,
          "such a window passes the windows' tests now; by the mark at the resolution it would not have",
          str({k: w[k] for k in ("hz", "hz_err", "passes", "passes_by_resolution")}))


def test_a_beat_in_one_stretch_does_not_come_back():
    """The headline rule (Jacob, 2026-10-17; ROADMAP.md decision 6, on the gate study's evidence): a beat comes back
    where the whole track beats, or two passing 2-s windows that do not overlap agree within 0.5 Hz (`apart_windows`),
    and the report names a bird only from such a beat. A 7-Hz beat planted for 45 frames near a track's end passes in
    the windows over it -- each overlapping the next -- and not over the whole track: one stretch, marked so, and the
    finding says it; planted for 65 frames in the middle, the whole track beats too, and it comes back."""
    print("\nflicker: a beat in one stretch, and one that comes back")
    from mcdonald import flicker
    win = lambda a, hz: dict(first=a, last=a + 59, fundamental_hz=hz)
    check(flicker.apart_windows([win(1, 7.0), win(61, 7.2)])[0] == 2 and flicker.apart_windows([win(1, 7.0), win(30, 7.1)])[0] == 1
          and flicker.apart_windows([win(1, 7.0), win(61, 7.8)])[0] == 1 and flicker.apart_windows([])[0] == 0,
          "windows apart: two that do not overlap and agree within half a hertz count two; overlapping, or apart in frequency, one")
    fps, n = 30.0, 300
    t = np.arange(n) / fps

    def planted(first, last, amp, bg):
        rng = np.random.default_rng(4)
        on = (np.arange(n) >= first) & (np.arange(n) < last)
        raw = {"object": list(1000 + rng.normal(0, 20, n) + amp * on * np.sin(2 * np.pi * 7.0 * t))}
        for dx, dy in flicker.BACKGROUND:
            raw[f"background {dx:+d},{dy:+d}"] = list(rng.normal(0, bg, n))
        fields = dict(frames=n, first=1, last=n, codec=None, aperture_px=4.0, tracks=["object"], spans={"object": (1, n)})
        return flicker.judge(raw, list(range(1, n + 1)), fps, [], fields, "object", say=lambda *a: None).fields
    f = planted(245, 290, 300, 40)
    b = f["beat"]["object"]
    check(f["beats"] is True and b["whole_passes"] is False and b["windows_apart"] == 1 and b["comes_back"] is False
          and b["windows_passing"] >= 2 and "that is one stretch" in (f.get("finding") or ""),
          "45 frames near the end: its windows pass, overlapping, and the whole track does not -- one stretch, and the finding says so",
          f"whole {b['whole_passes']}, {b['windows_passing']} windows, {b['windows_apart']} apart; {(f.get('finding') or '')[-80:]}")
    f = planted(120, 185, 120, 20)
    b = f["beat"]["object"]
    check(f["beats"] is True and b["whole_passes"] is True and b["comes_back"] is True and "one stretch" not in (f.get("finding") or ""),
          "65 frames in the middle: the whole track beats as well, and the beat comes back",
          f"whole {b['whole_passes']}, {b['windows_apart']} apart")


def test_members_are_apart_by_their_errors():
    """Members apart (`common`, 2026-10-17; D1): two whose frequencies differ by more than Z_APART of their combined errors
    are not one rhythm of the video -- not by more than the resolution, as until then: PR135's members over 4.5 s are
    known to 0.02-0.03 Hz, and three of its pairs, 0.15-0.20 Hz apart, were called one frequency. Over all the pairs
    judged at once (Sidak), so that fifteen pairs of one rhythm seem apart no oftener than one does."""
    print("\nflicker: members apart by their errors")
    from mcdonald import flicker
    fps = 30000 / 1001
    n = 136
    t = np.arange(n) / fps
    rng = np.random.default_rng(5)
    curve = lambda hz: list(1000 * (1 + 0.15 * np.sin(2 * np.pi * hz * t)) + rng.normal(0, 30, n))
    seg = {"a": (0, n), "b": (0, n)}
    q = flicker.common({"a": curve(7.70), "b": curve(7.85)}, seg, ["a", "b"], list(range(n)), fps)[0]
    check(q["independent"] and q["apart_hz"] < q["resolution_hz"] and q["apart_z"] > q["z_needed"],
          "two 0.15 Hz apart over 4.5 s, inside the resolution: apart by their errors, so not one rhythm",
          f"{q['hz'][0]:.3f} and {q['hz'][1]:.3f} Hz, {q['apart_z']:.1f} errors apart ({q['z_needed']:.1f} needed); "
          f"resolution {q['resolution_hz']:.2f}")
    q = flicker.common({"a": curve(7.70), "b": curve(7.70)}, seg, ["a", "b"], list(range(n)), fps)[0]
    check(not q["independent"], "two at one frequency, in step: one rhythm, as before",
          f"{q['apart_z']:.1f} errors apart, phase {q['phase_deg']:+.0f} deg")
    check(abs(flicker.z_apart(1) - 3.0) < 1e-6 and 3.6 < flicker.z_apart(15) < 3.8, "three errors for one pair, 3.7 for fifteen",
          f"{flicker.z_apart(1):.2f}, {flicker.z_apart(15):.2f}")


def test_beats_planted_beside_the_codecs_line_are_recovered():
    """The codec's slice measured (`sliced`, 2026-10-17; D1 and D6): beats planted 0.1-0.4 Hz either side of the codec's
    line in 2-s windows of the background apertures, and 1 Hz off it as the control, put through a window's tests. Until
    then the mark at the resolution refused every one inside half a hertz, and the planted beats were moved off the line,
    so the slice's completeness was never seen. Now those a quarter of a hertz or more off it are recovered at 20 %, as the
    control is; and the amplitude a beat needs there, in closed form (`analytic`), is beside it."""
    print("\nflicker: beats planted in the codec's slice")
    from mcdonald import flicker
    fps = 30000 / 1001
    line = fps / 4
    n = 150
    rng = np.random.default_rng(11)
    bgs = [f"background {k}" for k in range(4)]
    use = {b: list(rng.normal(0, 10, n)) for b in bgs}
    sl = flicker.sliced(use, {b: (0, n) for b in bgs}, bgs, fps, [line], 1000.0, 0.8 * fps / 2)
    rec, old = np.array(sl["recovered"]), np.array(sl["by_resolution"])
    j = {o: i for i, o in enumerate(sl["offsets_hz"])}
    check(sl["trials"] == 4 and min(rec[-1, j[0.25]], rec[-1, j[0.4]], rec[-1, j[1.0]]) >= 0.75,
          "at 20 % those a quarter of a hertz or more off the line are recovered, as the control a hertz away is", str(sl["recovered"]))
    check(old[:, [j[0.1], j[0.25], j[0.4]]].max() == 0 and old[-1, j[1.0]] >= 0.75,
          "where the mark at the resolution recovered none inside half a hertz, and the control as now", str(sl["by_resolution"]))
    an = sl["analytic"]
    check(an and 0 < an["amplitude"] <= an["with_floor"] < 0.2, "and the amplitude a beat needs there, in closed form, is beside it",
          f"{an['amplitude']:.1%} in the noise, {an['with_floor']:.1%} with the background's own flicker" if an else "none")
    check(flicker.sliced(use, {b: (0, n) for b in bgs}, bgs, fps, [], 1000.0, 0.8 * fps / 2) is None,
          "with no codec line in the band there is no slice to plant in", "")


def test_the_amplitude_a_beat_needs_in_closed_form():
    """The completeness in closed form (`analytic`, 2026-10-17; the information-theory survey's D6): from the error
    exponent of the test between noise and noise with a sinusoid in it, the amplitude a beat needs to be heard three
    times in four, given the noise, the frames and the band's look-elsewhere. More frames, a fainter beat; the
    background's own flicker, where it is the larger, sets it; and how long a clip must be for a beat of 10 %."""
    print("\nflicker: the amplitude a beat needs, in closed form")
    from mcdonald import flicker
    fps = 30.0
    a60, a240 = flicker.analytic(0.03, 60, fps, 12.0), flicker.analytic(0.03, 240, fps, 12.0)
    check(a240["amplitude"] < a60["amplitude"] < 3 * a240["amplitude"], "four times the frames, a beat about half as strong",
          f"{a60['amplitude']:.2%} over 60 frames, {a240['amplitude']:.2%} over 240")
    hi = flicker.analytic(0.03, 60, fps, 12.0, floor=0.05)
    check(abs(hi["with_floor"] - flicker.ABOVE * 0.05) < 1e-9 and hi["amplitude"] == a60["amplitude"],
          "where the background's own flicker is the larger, ABOVE times it is what a beat needs", f"{hi['with_floor']:.1%}")
    s = flicker.analytic(0.1, 60, fps, 12.0)["seconds_for"]
    check(s["0.05"] is not None and s["0.2"] is not None and s["0.05"] > s["0.1"] >= s["0.2"] >= flicker.MIN_FRAMES / fps,
          "and the fainter the beat, the longer the clip it needs: in 10 % noise a beat of 5 % takes seconds more than one of 10", str(s))


class _Held(_Shown):
    """_Shown, but the video carries a new picture only every `hold` frames and repeats it between (a clip of 10
    pictures a second shown at 30 fps, PR34): frame n shows the picture of the first frame of its hold, the point
    where it was then."""

    def __init__(self, level, hold, v=(0.37, 0.21), width=1.0):
        super().__init__(level, v, width)
        self.hold = hold

    def shown(self, n):
        return 1 + ((n - 1) // self.hold) * self.hold

    def at(self, j, n):
        return super().at(j, self.shown(n))

    def rgb(self, n):
        return super().rgb(self.shown(n))


def test_a_video_that_holds_its_pictures_does_not_beat_at_its_cadence():
    """PR34 (2026-10-11): a clip of 10 pictures a second shown at 30 fps, each held for three frames. The object's
    brightness changes once a picture, so its curve steps every three frames, and the stage heard "a beat at 5.02 Hz
    (and at 10.03, its double), 31% of its brightness, 6 of 8 windows": the hold cadence and its half. A point whose
    brightness is new and random on each of 50 pictures, held three frames (the steps alone do not make PR34's line:
    holding puts a zero in the spectrum at the picture rate; what made it there is the encoder's, and is not drawn
    here): the stage finds the held frames, carries the picture rate (about 10 a second), hears beats only below TOP
    of its Nyquist frequency -- 4 Hz -- and finds no beat. A real beat of 3 Hz in a video of 15 pictures a second (PR44, held two frames) is still a beat, at 3 Hz."""
    print("\nflicker: a video that holds its pictures")
    from mcdonald import flicker
    rng = np.random.default_rng(34)
    level = np.repeat(1 + 0.2 * rng.normal(size=60), 3)[:152]            # a new brightness each picture, held 3 frames
    clip = _Held(np.r_[level[:1], level], hold=3, width=1.5)
    track = {n: clip.at(0, n) for n in range(1, 151)}
    raw = flicker.curves(clip, {"object": track}, list(range(1, 151)))
    trap = flicker.peak(raw["object"], clip.fps)
    found = flicker.measure(clip, {"object": track}, say=lambda *a: None)
    f = found.fields
    pic = f.get("pictures") or {}
    check(abs(pic.get("held", 0) - 2 / 3) <= 0.05 and abs(pic.get("rate", 0) - clip.fps / 3) <= 0.6,
          "two frames in three are found held, and the picture rate is a third of the frame rate", str(pic))
    check(abs(pic.get("top_hz", 0) - flicker.TOP * clip.fps / 6) <= 0.3 and f["beats"] is not True
          and all(not w["passes"] or w["hz"] <= pic["top_hz"] for w in f["windows"].get("object", [])),
          "a beat is heard only up to TOP of the picture rate's Nyquist frequency (4 Hz), and none is",
          f"curve's strongest {trap['hz']:.2f} Hz {trap['amplitude']:.1%}; heard up to {pic.get('top_hz', 0):.1f} Hz; "
          f"{str(f.get('finding'))[:90]}")
    t = (np.arange(152) // 2) * 2 / clip.fps                              # 15 pictures a second, beating at 3 Hz
    slow = _Held(1 + 0.3 * np.sin(2 * np.pi * 3.0 * t), hold=2, width=1.5)
    g = flicker.measure(slow, {"object": {n: slow.at(0, n) for n in range(1, 151)}}, say=lambda *a: None).fields
    b = (g.get("beat") or {}).get("object") or {}
    check(g["beats"] is True and abs(b.get("hz", 0) - 3.0) <= 0.3 and abs(g["pictures"]["rate"] - clip.fps / 2) <= 0.6,
          "a real beat of 3 Hz at 15 pictures a second is still a beat, at 3 Hz", f"{g['pictures']}; {str(g.get('finding'))[:80]}")


def test_a_beat_is_not_heard_near_the_frame_rates_limit():
    """PR27 (2026-10-11): six windows passed at 13.5 Hz, 0.9 of the 15-Hz Nyquist frequency, on frame-to-frame noise
    with no rhythm in the curve. A beat is heard only up to TOP of the Nyquist frequency (12 Hz at 30 fps): a point
    beating 30% at 13.5 Hz is not called a beat, and the finding says why; the same at 6 Hz is."""
    print("\nflicker: a beat near the frame rate's limit")
    from mcdonald import flicker
    hi = _Beating([(13.5, 0.3, 0.0)])
    f = flicker.measure(hi, {"member 0": {n: hi.at(0, n) for n in range(1, 151)}}, say=lambda *a: None).fields
    check(f["beats"] is False and "above the highest frequency" in f["finding"] and not any(
              w["passes"] for w in f["windows"]["member 0"]),
          "30% at 13.5 Hz: above the highest frequency heard (12 Hz), and no window passes", str(f["finding"])[:110])
    lo = _Beating([(6.0, 0.3, 0.0)])
    g = flicker.measure(lo, {"member 0": {n: lo.at(0, n) for n in range(1, 151)}}, say=lambda *a: None).fields
    check(g["beats"] is True and abs(g["beat"]["member 0"]["hz"] - 6.0) <= 0.3 and g["pictures"]["held"] < 0.1,
          "30% at 6 Hz, every frame a new picture: a beat, at 6 Hz", str(g.get("finding"))[:80])


def test_a_brightness_that_only_wanders_is_not_a_beat():
    """PR23's other trap, and every clip's: a curve taken against its 0.5-s running mean keeps little under 2 Hz,
    so a brightness that only wanders slowly comes out peaked just above that (64% of random walks put through
    the stage's steps peak at 1.5-2.5 Hz), and against a quiet background the peak stands far over the
    apertures beside it. A point whose brightness wanders by 4% a frame: no beat. The same wander with a beat
    of 12% at 6 Hz on it: a beat, at 6 Hz."""
    print("\nflicker: a wander is not a beat; a beat on a wander is")
    from mcdonald import flicker
    walk = 1.0 + np.cumsum(np.random.default_rng(3).normal(0, 0.04, 152))
    walk /= walk.mean()
    clip = _Shown(walk, width=2.0)
    track = {n: clip.at(0, n) for n in range(1, 151)}
    f = flicker.measure(clip, {"object": track}, say=lambda *a: None).fields
    p = f["curves"]["object"]
    check(walk.min() > 0.3 and p["amplitude"] >= flicker.ABOVE * f["noise_floor"] and f["beats"] is False
          and "only wanders slowly" in f["finding"],
          "a wandering brightness peaks far over the background beside it, and is no beat: no more than its drift",
          f"{p['hz']:.2f} Hz, {p['amplitude']:.1%} against {f['noise_floor']:.1%}; {p['over_drift']:.1f} times its drift, "
          f"{p['drift_needed']:.1f} needed")
    n = np.arange(152)
    both = _Shown(walk * (1 + 0.12 * np.sin(2 * np.pi * 6.0 * n / _Beating.fps)), width=2.0)
    g = flicker.measure(both, {"object": track}, say=lambda *a: None).fields
    b = (g.get("beat") or {}).get("object")
    check(g["beats"] is True and b is not None and abs(b["hz"] - 6.0) <= 0.3,
          "a beat of 12% at 6 Hz on the same wander is a beat, at 6 Hz", str(g.get("finding"))[:100])
    rng = np.random.default_rng(12)                       # the test's own promise: one in a hundred
    walks = [100 + np.cumsum(rng.normal(0, 1, 120)) + rng.normal(0, 1, 120) for _ in range(40)]
    passed = sum(flicker.drift(w, 30.0)["passes"] for w in walks)
    check(passed <= 2, "40 random walks with grain: no more than 2 pass the drift test, held to 1 in 100", f"{passed} passed")


def test_a_beat_is_not_its_own_double_nor_the_edge_of_the_band():
    """PR23's windows (2026-10-09): each 2-s window found the "half" of its strongest on the strongest's own
    flank -- at 2 Hz the half is looked for within a resolution of the peak -- and named fundamentals under the
    1.5 Hz the band starts at. And WA9ONY-5, a pico balloon whose payload swings about once a second: its
    strongest was the band's first frequency, 1.53 Hz, with the spectrum still rising below it, and was read as
    a beat. A point beating at 2.4 Hz: 2.4 Hz, no double, no window naming a fundamental under the band. A curve
    swinging at 0.8 Hz: its strongest is only the band's edge; one beating at 3 Hz is a peak."""
    print("\nflicker: no double on the flank, no beat at the band's edge")
    from mcdonald import flicker
    one = _Beating([(2.4, 0.25, 0)])
    f = flicker.measure(one, {"object": {n: one.at(0, n) for n in range(1, 151)}}, say=lambda *a: None).fields
    b = f["beat"]["object"]
    wins = f["windows"]["object"]
    check(f["beats"] is True and abs(b["hz"] - 2.4) <= 0.2 and b["double_hz"] is None
          and wins and all(w["fundamental_hz"] >= flicker.LOW and w["fundamental_hz"] == w["hz"] for w in wins),
          "a beat at 2.4 Hz: 2.4 Hz, no double, and no window names its own flank as the fundamental",
          f"{b['hz']:.2f} Hz, double {b['double_hz']}; windows' fundamentals {sorted({round(w['fundamental_hz'], 2) for w in wins})}")
    t = np.arange(150) / 30.0
    grain = np.random.default_rng(4).normal(0, 1, 150)
    slow = flicker.peak(1000 * (1 + 0.3 * np.sin(2 * np.pi * 0.8 * t)) + grain, 30.0)
    fast = flicker.peak(1000 * (1 + 0.2 * np.sin(2 * np.pi * 3.0 * t)) + grain, 30.0)
    check(slow["edge"] and slow["hz"] <= flicker.LOW + flicker.LOBE * slow["resolution_hz"] and not fast["edge"]
          and abs(fast["hz"] - 3.0) < 0.2,
          "a swing at 0.8 Hz: its strongest, a side lobe just inside the band, is only the band's edge; a beat at 3 Hz is a peak",
          f"{slow['hz']:.2f} Hz edge={slow['edge']}; {fast['hz']:.2f} Hz edge={fast['edge']}")


class PlantedClip:
    """What the linker asks of a Clip -- n0, n1, W, H, fps, rgb(n), grey(n) -- with a
    disc on a known path, there on the frames in `seen`, and a brighter disc that
    never moves, for the linker to be tempted by. Module level, because it goes
    to the detector's processes by pickle."""
    W, H, n0, fps = 540, 300, 1, 30000 / 1001
    P0, RADIUS, DECOY, CONTRAST = (80.0, 80.0), 9.0, (120.0, 230.0), 120

    def __init__(self, v=(41.0, 6.0), n1=24, seen=range(1, 11)):
        from scipy import ndimage
        self.V, self.n1, self.seen = v, n1, set(seen)
        rng = np.random.default_rng(7)
        self._sky = ndimage.gaussian_filter(rng.normal(0, 1, (self.H, self.W)), 6.0) * 80 + 60
        self._yx = np.mgrid[0:self.H, 0:self.W]

    def truth(self, n):
        return self.P0[0] + self.V[0] * (n - 1), self.P0[1] + self.V[1] * (n - 1)

    def grey(self, n):
        yy, xx = self._yx
        g = self._sky + 250 * (np.hypot(xx - self.DECOY[0], yy - self.DECOY[1]) <= self.RADIUS)
        if n in self.seen:
            x, y = self.truth(n)
            g = g + self.CONTRAST * (np.hypot(xx - x, yy - y) <= self.RADIUS)
        return g.astype(np.float32)

    def rgb(self, n):
        return np.repeat(self.grey(n)[..., None], 3, axis=2)


class TwoPlanted(PlantedClip):
    """A video with more than one object in it: PlantedClip's disc, and a second that comes in later
    from the right, lower down and slower, going the other way. `truth2(n)` is the second's centre;
    it is there on the frames in `SEEN2`."""
    P2, V2, SEEN2 = (470.0, 190.0), (-30.0, -3.0), range(6, 22)

    def truth2(self, n):
        return self.P2[0] + self.V2[0] * (n - 6), self.P2[1] + self.V2[1] * (n - 6)

    def grey(self, n):
        g = super().grey(n)
        if n in self.SEEN2:
            yy, xx = self._yx
            x, y = self.truth2(n)
            g = g + self.CONTRAST * (np.hypot(xx - x, yy - y) <= self.RADIUS)
        return g.astype(np.float32)


class StreakClip(PlantedClip):
    """PR43 drawn (2026-09-27): a small bright thing crossing 20 px a frame over textured ground with bright
    specks, smeared into a dash 16 px long and 3 px across along its motion. No spot size holds it; its
    motion does. `truth(n)` is the dash's centre."""
    W, H, n0, fps = 540, 300, 1, 30000 / 1001
    P0, V = (60.0, 70.0), (20.0, 5.0)

    def __init__(self, n1=30, seen=None):
        rng = np.random.default_rng(11)
        self.n1, self.seen = n1, set(seen if seen is not None else range(3, 25))
        self._ground = isotropic(self.H, self.W, scale=2.5) * 30 + 60
        yy, xx = np.mgrid[0:self.H, 0:self.W]
        for _ in range(140):                                          # rocks: the spots a disc filter finds everywhere
            x, y, r = rng.uniform(0, self.W), rng.uniform(0, self.H), rng.uniform(1.5, 3.0)
            self._ground = self._ground + rng.uniform(40, 120) * np.exp(-0.5 * ((xx - x) ** 2 + (yy - y) ** 2) / r ** 2)
        self._yx = (yy, xx)
        u = np.array(self.V) / np.hypot(*self.V)
        self._along, self._across = u, np.array([-u[1], u[0]])

    def grey(self, n):
        g = self._ground
        if n in self.seen:
            yy, xx = self._yx
            x, y = self.truth(n)
            dx, dy = xx - x, yy - y
            a, c = dx * self._along[0] + dy * self._along[1], dx * self._across[0] + dy * self._across[1]
            g = g + 70 * np.exp(-0.5 * (a / 6.0) ** 2 - 0.5 * (c / 1.3) ** 2)
        return g.astype(np.float32)


class SlowDisc(PlantedClip):
    """PR055's situation: a dark disc 24 px across that moves a pixel and a half a frame --
    less than its own width in the four frames the double difference spans."""
    P0, RADIUS, CONTRAST = (200.0, 120.0), 12.0, -150


class Crawler(PlantedClip):
    """Galileo flyer 1's situation (2026-09-29): a sky that holds still at 60 frames a second, and a
    bright spot 5 px across that crawls a third of a pixel a frame -- less than its own width in
    the four frames the double difference spans -- for the whole clip; and a second one 18 px from
    the top, inside the 30 px band a registered residual is not believed in. No decoy. `truth(n)`
    is the first's centre, `second(n)` the other's."""
    W, H, n0, fps = 540, 300, 1, 60.0
    P0, CONTRAST = (200.0, 150.0), 30                 # faint, as a bird far off is; drawn bright and clean on a drawn sky, a
    Q0, V2 = (400.0, 18.0), (-0.25, 0.0)              # crawler is the sharpest thing in it and `still_again` takes its motion

    def __init__(self, v=(0.3, 0.1), n1=150, noise=True):
        super().__init__(v=v, n1=n1, seen=range(1, n1 + 1))
        from scipy import ndimage
        rng = np.random.default_rng(3)
        # What stays on the sensor, at every scale a sensor has it: speckle, blobs of a few pixels, column stripes. A
        # sky drawn without it has nothing sharp in it but the crawler, whose motion `still_again` then takes for the
        # background's (the noise=False case, which its zero-peak guard is for).
        self._pattern = (rng.normal(0, 3.0, (self.H, self.W)) + ndimage.gaussian_filter(rng.normal(0, 1.0, (self.H, self.W)), 2.0) * 12.0
                         + np.tile(rng.normal(0, 2.0, self.W), (self.H, 1))) if noise else 0.0
        self._noise = rng.normal(0, 2.0, (n1 + 1, self.H, self.W)).astype(np.float32) if noise else None      # a Boson's, after HEVC

    def second(self, n):
        return self.Q0[0] + self.V2[0] * (n - 1), self.Q0[1] + self.V2[1] * (n - 1)

    def grey(self, n):
        yy, xx = self._yx
        g = self._sky + self._pattern + (self._noise[n] if self._noise is not None else 0.0)
        for x, y in (self.truth(n), self.second(n)):
            g = g + self.CONTRAST * np.exp(-0.5 * ((xx - x) ** 2 + (yy - y) ** 2) / 2.0 ** 2)
        return g.astype(np.float32)


class Clouded(PlantedClip):
    """A disc, and other things like it that come and go where it is not: `others` is
    {frame: [(x, y, contrast)]}, each drawn the disc's size."""

    def __init__(self, others, **kw):
        super().__init__(**kw)
        self.others = others

    def grey(self, n):
        g = super().grey(n)
        yy, xx = self._yx
        for x, y, c in self.others.get(n, []):
            g = g + c * (np.hypot(xx - x, yy - y) <= self.RADIUS)
        return g.astype(np.float32)


def _off(track, clip):
    return max(np.hypot(x - clip.truth(n)[0], y - clip.truth(n)[1]) for n, (x, y) in track.items())


def test_marks_become_a_track_that_stays_on_the_object():
    """autolink: from two hand marks to an automatic track. The object moves 41
    px a frame, faster than the linker's gate, is larger than the default
    scale, and is weaker than something else in the frame -- PR113's situation,
    each part of which once produced a track of the wrong thing or of nothing."""
    print("\nautolink: from two marks to a track")
    from mcdonald import autolink
    clip = PlantedClip()
    marks = {2: tuple(np.add(clip.truth(2), (1.5, -1.0))), 5: tuple(np.add(clip.truth(5), (-1.0, 2.0)))}
    steps = list(autolink.link_from_marks(clip, marks, procs=0, max_gap=6))
    L = steps[-1]
    check([s.stage for s in steps][:2] == ["masks", "scale"] and L.done, "it reports as it goes: masks, scale, linking, done",
          " > ".join(dict.fromkeys(s.stage for s in steps)))
    check(L.size is not None and L.size >= 15 and L.dark is False,
          "the scale comes from the marks: comparable to the object, not the default 9", f"{L.size:g} px, dark={L.dark}")
    rim = [max(dist) for d, s, dist in L.sweep if s == 5 and not d]
    check(bool(rim) and rim[0] <= 6.0,
          "and not simply the smallest that comes within tolerance: 5 px does, on the disc's rim",
          f"5 px: {rim[0]:.1f} px from the marks; chosen {L.size:g} px: {L.worst():.1f} px")
    check(sorted(L.track) == list(range(1, 11)),
          "linked back from the first mark to the object's first frame, and on from the last to its last",
          f"{min(L.track)}–{max(L.track)}, {len(L.track)} frames; the marks are on 2 and 5")
    check(_off(L.track, clip) < 1.0, "on the object in every frame, though it moves faster than the gate",
          f"worst {_off(L.track, clip):.2f} px")
    check(set(L.residuals) == {2, 5} and L.worst() < 3.0, "it says how far it sits from each hand mark",
          ", ".join(f"{n}: {d:.1f} px" for n, d in L.residuals.items()))
    check(set(L.arrivals) == {5} and L.arrivals[5] < 3.0,
          "and how far the link from one mark lands from the next, which it was not seeded from",
          f"{L.arrivals[5]:.1f} px")
    check(all(L.source[n] == "both" for n in range(2, 6)) and L.source[1] == "backward" and L.source[9] == "forward"
          and not L.disputed(), "between the marks the forward and backward links agree, frame for frame")
    # the important one. The decoy is the strongest candidate in every frame, and a linker
    # that has lost its object and starts again takes the strongest candidate
    near_decoy = [n for n, (x, y) in L.track.items() if np.hypot(x - clip.DECOY[0], y - clip.DECOY[1]) < 40]
    check(L.lost_at == 10 and L.lost_before is None and not near_decoy,
          "when the object goes it stops, rather than starting again on the brightest thing in the frame",
          f"lost after {L.lost_at}; searched {L.n_lo}–{L.n_hi}")
    plain = vf.link_track({n: vf.frame_candidates(clip, n, L.masks, None, L.size, L.dark, autolink.MIN_RESP)
                           for n in range(2, 20)}, 2, 19, (2, *marks[2]), vf.velocity_from_marks(marks), max_gap=6)
    on_decoy = [n for n, (x, y) in plain.items() if np.hypot(x - clip.DECOY[0], y - clip.DECOY[1]) < clip.RADIUS]
    check(bool(on_decoy), "which is what link_track alone does with the same candidates",
          f"on the decoy from frame {min(on_decoy) if on_decoy else None}")


def test_a_mark_after_a_loss_is_a_new_seed():
    """The object goes behind something for longer than the linker will wait. The
    track ends there, as it should. One more mark, after it comes out, and the
    track resumes -- forward from that mark and back toward the loss -- without
    the detector being run again on a frame it has already seen."""
    print("\nautolink: a mark after a loss")
    from mcdonald import autolink
    clip = PlantedClip(v=(14.0, 3.0), n1=30, seen=list(range(1, 9)) + list(range(19, 31)))
    masks, cache = vf.static_masks(clip), {}
    marks = {2: clip.truth(2), 5: clip.truth(5)}
    L = list(autolink.link_from_marks(clip, marks, masks=masks, size=15.0, procs=0, max_gap=6, cache=cache))[-1]
    check(sorted(L.track) == list(range(1, 9)) and L.lost_at == 8, "two marks: linked until it disappears, and lost there",
          f"{min(L.track)}–{max(L.track)}; {L.say[-40:]}")
    ran = len(cache)
    marks[22] = clip.truth(22)
    L = list(autolink.link_from_marks(clip, marks, masks=masks, size=15.0, procs=0, max_gap=6, cache=cache))[-1]
    check(sorted(L.track) == list(range(1, 9)) + list(range(19, 31)),
          "a third mark, after it reappears: the track resumes from it, both ways", f"{len(L.track)} frames")
    check(_off(L.track, clip) < 1.0, "on the object throughout", f"worst {_off(L.track, clip):.2f} px")
    check(L.arrivals.get(22, 0) is None and "does not reach the mark on frame 22" in L.say,
          "and it says the link from the mark before never reached that one, rather than joining them up")
    check(L.source[19] == "backward" and L.source[25] == "forward" and L.lost_at is None,
          "back from the new mark to where it came out, on from it to the end")
    check(len(cache) == 30 and ran < 30, "the detector ran on the new frames only", f"{ran} frames the first time, {len(cache)} in all")


def test_a_link_that_loses_the_object_does_not_take_the_next_thing_it_sees():
    """Jacob, 2026-09-22, on PR055: "The object is located correctly, but linking seemed to
    find a different track." Between the marks the link was on the disc to 2 px. Past the
    first mark and the last it went on looking while the disc was hidden in cloud, and the
    gate it looked in grew 12 px for every frame it had not seen it on -- 205 px after
    fifteen -- until a dark patch of cloud fell inside it, and it followed that. For a disc
    moving 2.5 px a frame. The gate now grows by a share of the object's own speed, and past
    the end marks the link waits END_GAP frames, not max_gap, before it says it is lost."""
    print("\nautolink: when the object goes, the link stops")
    from mcdonald import autolink
    V = (2.5, 0.5)
    path = lambda n: (100.0 + V[0] * (n - 1), 120.0 + V[1] * (n - 1))
    # dark cloud where the disc is not: 40 px beside its path before it comes and after it goes
    others = {n: [(path(n)[0] - 5.0, path(n)[1] - 40.0, -110)] for n in range(1, 9)}
    others.update({n: [(path(n)[0] + 5.0, path(n)[1] + 40.0, -110)] for n in range(34, 47)})
    clip = Clouded(others, v=V, n1=46, seen=range(11, 31))
    clip.P0, clip.RADIUS, clip.CONTRAST = path(1), 12.0, -150
    masks = vf.static_masks(clip)
    marks = {n: clip.truth(n) for n in (13, 18, 23, 28)}
    L = list(autolink.link_from_marks(clip, marks, masks=masks, size=15.0, dark=True, procs=0))[-1]
    cloud = [n for n, (x, y) in L.track.items() if any(np.hypot(x - a, y - b) < 12 for a, b, _ in others.get(n, []))]
    check(sorted(L.track) == list(range(11, 31)) and not cloud and _off(L.track, clip) < 1.5,
          "linked on the frames the disc is seen, and on none of the cloud beside where it went",
          f"{min(L.track)}–{max(L.track)}, {len(L.track)} frames; on the cloud: {cloud or 'none'}")
    check(L.lost_before == 11 and L.lost_at == 30 and "lost before frame 11" in L.say and "lost after frame 30" in L.say,
          "and it says where it lost the disc, going back and going on", L.say[-90:])
    check(autolink.gate_for(V)[1] < 1.0 and autolink.gate_for((142.0, 0.0)) == autolink.GATE,
          "the gate grows with the object's own speed, and never past link_track's own (PR113 is linked as before)",
          f"{autolink.gate_for(V)[1]:.2f} px a frame at 2.5 px a frame; {autolink.gate_for((142.0, 0.0))[1]:g} at 142")
    saved = autolink.SHARE, autolink.END_GAP
    try:                                                    # the fix taken out: the test has to fail without it
        autolink.SHARE, autolink.END_GAP = float("inf"), 40
        old = list(autolink.link_from_marks(clip, marks, masks=masks, size=15.0, dark=True, procs=0))[-1]
    finally:
        autolink.SHARE, autolink.END_GAP = saved
    took = [n for n, (x, y) in old.track.items() if any(np.hypot(x - a, y - b) < 12 for a, b, _ in others.get(n, []))]
    check(bool(took), "which the gate it had before does not: it goes on along the cloud",
          f"on the cloud on {len(took)} frames, {min(took) if took else '-'}–{max(took) if took else '-'}")

    # PR149: between two marks the contact crosses a ship and the detector cannot see it. The link from each side
    # waited, its gate grew, and it took things 100-160 px off the path. Now the stretch stays a gap.
    F = (16.0, 3.0)
    fast = lambda n: (60.0 + F[0] * (n - 1), 100.0 + F[1] * (n - 1))
    ship = {n: [(fast(n)[0], fast(n)[1] + 80.0, -110)] for n in range(12, 20)}
    clip2 = Clouded(ship, v=F, n1=24, seen=list(range(1, 11)) + list(range(20, 25)))
    clip2.P0, clip2.RADIUS, clip2.CONTRAST = fast(1), 12.0, -150
    masks2 = vf.static_masks(clip2)
    L2 = list(autolink.link_from_marks(clip2, {n: clip2.truth(n) for n in (3, 8, 21, 24)}, masks=masks2, size=15.0, dark=True,
                                       procs=0))[-1]
    on_ship = [n for n, (x, y) in L2.track.items() if any(np.hypot(x - a, y - b) < 12 for a, b, _ in ship.get(n, []))]
    check(sorted(L2.track) == list(range(1, 11)) + list(range(20, 25)) and not on_ship and _off(L2.track, clip2) < 1.5,
          "where it cannot be seen between two marks, the link leaves a gap rather than taking what is beside the path",
          f"{len(L2.track)} frames; on what is beside it: {on_ship or 'none'}")
    check(L2.arrivals.get(21) is not None and L2.arrivals[21] < 2.0,
          "and where it comes out again on its path, the link from one side still reaches the mark on the other",
          f"{L2.arrivals[21]:.1f} px" if L2.arrivals.get(21) is not None else "it does not")
    try:
        autolink.SHARE = float("inf")
        old2 = list(autolink.link_from_marks(clip2, {n: clip2.truth(n) for n in (3, 8, 21, 24)}, masks=masks2, size=15.0,
                                             dark=True, procs=0))[-1]
    finally:
        autolink.SHARE = saved[0]
    took = [n for n, (x, y) in old2.track.items() if any(np.hypot(x - a, y - b) < 12 for a, b, _ in ship.get(n, []))]
    check(bool(took), "which, again, the gate it had before does not", f"on what is beside the path on frames {took}")


class _Specked(PlantedClip):
    """PR148's case: an object answering the detector more weakly than 40 specks of texture
    in every frame, which come and go frame to frame -- it is never among the 25 strongest."""

    def __init__(self, **kw):
        super().__init__(v=(12.0, 3.0), n1=24, seen=range(1, 25), **kw)
        self.specks = {}
        for n in range(1, 25):                     # 40 a frame, none within 45 px of the object (on it, or in its ring)
            at = np.random.default_rng(100 + n).uniform(40, [500, 260], (120, 2))
            self.specks[n] = at[np.hypot(*(at - self.truth(n)).T) > 45][:40]

    CONTRAST = 60

    def grey(self, n):
        yy, xx = self._yx
        g = super().grey(n)
        for x, y in self.specks[n]:
            g = g + 160 * (np.hypot(xx - x, yy - y) <= self.RADIUS)
        return g.astype(np.float32)


def test_the_detector_the_link_is_given_and_how_it_chooses_its_size():
    """Three things found on 2026-09-22 and fixed on 2026-09-23 (Next 1d): the detector stopped
    at the first spot in the band at the edge of the frame, and every weaker one went with it;
    a mark off the object's centre held the choice of size on a small one; and an object weaker
    than 25 specks of texture was never linked (PR148). Each is checked with its fix taken out."""
    print("\nthe detector's spots at the edge, the choice of size, and a weak object between marks")
    from mcdonald import autolink
    g = np.full((200, 300), 50.0)
    yy, xx = np.mgrid[0:200, 0:300]
    for x, y, a in [(8, 100, 250)] + [(60 + 40 * i, 60 + 30 * (i % 3), 120) for i in range(5)]:
        g += a * (np.hypot(xx - x, yy - y) <= 4)
    got = vf.source_candidates(g, np.zeros(g.shape, bool), 9.0)
    check(len(got) == 5, "a strong spot in the band at the edge is left out, and the five weaker ones are all found",
          f"{len(got)} spots (the stop at the first spot in the band found none)")
    every = vf.source_candidates(g, np.zeros(g.shape, bool), 5.0, n_max=None, min_resp=5.0)
    check(every[:5] == vf.source_candidates(g, np.zeros(g.shape, bool), 5.0, n_max=5, min_resp=5.0),
          "every spot, n_max=None: the strongest found exactly as with a limit, and first", f"{len(every)} spots")

    clip = PlantedClip()
    masks = vf.static_masks(clip)
    marks = {3: (clip.truth(3)[0] + 4, clip.truth(3)[1]), 8: (clip.truth(8)[0] + 4, clip.truth(8)[1])}
    L = list(autolink.link_from_marks(clip, marks, masks=masks, procs=0))[-1]
    was = autolink.STRONGER
    autolink.STRONGER = float("inf")
    try:
        L0 = list(autolink.link_from_marks(clip, marks, masks=masks, procs=0))[-1]
    finally:
        autolink.STRONGER = was
    check(L.size == 15.0 and _off(L.track, clip) < 1.0 and L0.size == 9.0,
          "marks 4 px off the disc's centre: the size that answers most strongly (15), whose spot is on the centre, "
          "not the smaller one nearer the marks (9, the choice before)", f"{L.size} ({_off(L.track, clip):.1f} px); before {L0.size}")

    sp = _Specked()
    masks = vf.static_masks(sp)
    marks = {4: sp.truth(4), 20: sp.truth(20)}
    L = list(autolink.link_from_marks(sp, marks, masks=masks, procs=0, size=15.0))[-1]
    on = [n for n in range(4, 21) if n in L.track and np.hypot(*np.subtract(L.track[n], sp.truth(n))) < 2]
    was = autolink.NEAR
    autolink.NEAR = 0.0
    try:
        L0 = list(autolink.link_from_marks(sp, marks, masks=masks, procs=0, size=15.0))[-1]
    finally:
        autolink.NEAR = was
    on0 = [n for n in range(4, 21) if n in L0.track and np.hypot(*np.subtract(L0.track[n], sp.truth(n))) < 2]
    check(len(on) == 17 and _off(L.track, sp) < 2.0 and len(on0) < 5,
          "an object weaker than 40 specks a frame is linked between its marks, from the spots near their path",
          f"{len(on)} of 17 frames on it; with the 25 strongest only, {len(on0)}")


def test_where_the_two_links_disagree_the_frame_is_flagged():
    """Candidates by hand, no detector. The object is missed on frame 4, where
    there is only something 8 px off its path; a forward link takes that and is
    carried along a false branch for two more frames, while the backward link,
    coming from the far mark, stays on the path. Neither is privileged. The
    frames are flagged for a person to look at."""
    print("\nautolink: disputed frames")
    from mcdonald import autolink
    path = {n: (10.0 * n, 100.0) for n in range(1, 10)}
    cands = {n: [(*path[n], 50.0)] for n in path}
    cands[4] = [(40.0, 108.0, 50.0)]
    for n in (5, 6):
        cands[n].append((10.0 * n, 108.0, 50.0))
    marks = {1: path[1], 9: path[9]}
    track, source, arrivals, _, _ = autolink.assemble(cands, marks, 1, 9)
    disputed = sorted(n for n, how in source.items() if how == "disputed")
    check(disputed == [5, 6], "the frames where the two disagree are flagged", f"{disputed}")
    check(source[4] == "both" and track[4] == (40.0, 108.0), "not the one where both took the only candidate there was")
    check(track[5] == (50.0, 108.0) and track[6] == path[6], "each disputed frame keeps the version from the nearer mark",
          f"5: {track[5]}, 6: {track[6]}")
    check(arrivals[9] == 0.0 and all(source[n] == "both" for n in (1, 2, 3, 7, 8, 9)), "and the rest is agreed")


def test_a_link_that_cannot_find_the_object_says_so():
    print("\nautolink: refusing")
    from mcdonald import autolink
    clip = PlantedClip()
    marks = {2: clip.truth(2), 5: clip.truth(5)}
    masks = vf.static_masks(clip)
    far = {n: (x + 20.0, y) for n, (x, y) in marks.items()}      # marks beside the object, not on it
    L = list(autolink.link_from_marks(clip, far, masks=masks, sizes=(5, 9, 15, 21), procs=0))[-1]
    check(L.done and not L.track and "Nothing was linked" in L.say,
          "marks with no candidate under them at any scale link nothing", L.say[:70])
    check(len(L.sweep) == 8 and "closest" in L.say, "and it says how close each scale came",
          L.say[L.say.index("closest"):][:60] if "closest" in L.say else "")
    check("Neither the first mark nor the last" in L.say, "and that neither end mark has anything under it")
    one = {2: marks[2], 5: far[5]}                                # PR055: nine good marks, and a last one where the disc had gone
    L1 = list(autolink.link_from_marks(clip, one, masks=masks, sizes=(5, 9, 15, 21), procs=0))[-1]
    check(not L1.track and "The mark on frame 5 is the one" in L1.say and "delete that mark and link again" in L1.say,
          "one end mark with nothing under it links nothing too -- and it says which mark, and what to do about it", L1.say[-150:])
    polled = []
    L = list(autolink.link_from_marks(clip, marks, masks=masks, size=21.0, procs=0,
                                      stop=lambda: polled.append(1) or len(polled) >= 3))[-1]
    check(L.done and L.stopped and "stopped" in L.say and sorted(L.track) == [2, 3, 4],
          "it stops when asked, and keeps what it had", L.say[-32:])
    check(list(autolink.link_from_marks(clip, {}, procs=0))[-1].done, "and no marks is not an error")


def test_the_link_runs_on_processes_and_saves_its_provenance():
    print("\nautolink: the pool, and the file")
    import tempfile
    from mcdonald import autolink
    clip = PlantedClip()
    marks = {2: clip.truth(2), 5: clip.truth(5)}
    masks = vf.static_masks(clip)
    inline = autolink.track_from_marks(clip, marks, masks=masks, size=15.0, procs=0, max_gap=6)
    said = []
    pooled = autolink.track_from_marks(clip, marks, say=said.append, masks=masks, size=15.0, procs=2, max_gap=6)
    check(pooled.track == inline.track and len(pooled.track) == 10,
          "two processes give the track one gives", f"{len(pooled.track)} frames")
    check(len(said) >= 2 and said[-1] == pooled.say, "track_from_marks runs it to the end, saying each stage once")
    with tempfile.TemporaryDirectory() as td:
        path = autolink.write_track_csv(f"{td}/t_autotrack.csv", pooled, "/nowhere/planted.mp4", clip.fps)
        back = vf.read_track(path)
        head = [ln for ln in open(path, encoding="utf-8") if ln.startswith("#")]
        rows = [ln for ln in open(path, encoding="utf-8") if not ln.startswith("#")]
    check(back == {n: (round(x, 2), round(y, 2)) for n, (x, y) in pooled.track.items()},
          "the CSV reads back through the package's own reader")
    check(any("size=15" in ln and "min_resp=5" in ln and "marks: 2 (" in ln for ln in head),
          "and its header is enough to make it again: scale, polarity, threshold, and the marks")
    check(any("lost after frame 10" in ln for ln in head) and any("2: 0." in ln and "5: 0." in ln for ln in head)
          and any("disputed frames" in ln and "none" in ln for ln in head),
          "with where it lost the object, how far it sat from each mark, and which frames are disputed")
    check(rows[0].strip().endswith(",source") and rows[1].strip().endswith(",backward") and rows[2].strip().endswith(",both"),
          "each row says which way it was linked")
    check(autolink.write_track_csv("/nowhere/x.csv", None, "v", 30.0) is None, "no track, no file")


def test_a_track_file_may_carry_a_provenance_header():
    """A track that will be quoted in a paper should say where it came from,
    so the reader must tolerate comment lines."""
    print("\ndetection: track files with headers")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "t.csv"
        p.write_text("# where this came from\n# and why\n\nframe,x_px,y_px\n"
                     "1,10.0,20.0\n2,12.0,23.0\n3,14.0,26.0\n", encoding="utf-8")
        t = vf.read_track(p)
        check(len(t) == 3 and t[1] == (10.0, 20.0), "comments and blanks are skipped",
              f"{len(t)} rows")


# ---------------------------------------------------------------- masks
def test_a_redaction_block_is_masked_but_a_dark_scene_is_not():
    """Masking every dark pixel takes an object's sharpening halo with it. A
    block is large, static and black; a night sky is merely dark."""
    print("\nmasks: redaction blocks vs a dark scene")

    class Fake:
        def __init__(self, frames):
            self._f = frames
            self.n0, self.n1 = 1, len(frames)
            self.H, self.W = frames[0].shape[:2]

        def frames(self):
            return range(self.n0, self.n1 + 1)

        def rgb(self, n):
            return self._f[n - 1]

        def grey(self, n):
            return self._f[n - 1].mean(2)

    blocked = []
    for i in range(12):
        f = np.repeat(isotropic(300, 500, 4.0)[:, :, None], 3, axis=2).clip(0, 255)
        f[20:120, 30:200] = 0.0                      # a static black block
        blocked.append(f.astype(np.float32))
    m = vf.static_masks(Fake(blocked), n_sample=8)
    frac = m["blocks"][20:120, 30:200].mean()
    check(frac > 0.9, "a static black block is masked", f"{frac:.0%} of it")

    dark = []
    for i in range(12):
        f = np.repeat((isotropic(300, 500, 4.0) * 0.06 + 6).clip(0, 40)[:, :, None], 3, axis=2)
        dark.append(np.ascontiguousarray(roll(f, 3 * i, 0)).astype(np.float32))
    m2 = vf.static_masks(Fake(dark), n_sample=8)
    check(m2["blocks"].mean() < 0.10, "a dark moving scene is not",
          f"{m2['blocks'].mean():.0%} masked")


# ---------------------------------------------------------------- packaging
def test_output_never_lands_in_the_package():
    """The defect this package was split out to fix: a tool must not write into
    its own source tree because that is where the code happens to live."""
    print("\npackaging: where results go")
    pkg = Path(vf.__file__).resolve().parent
    with tempfile.TemporaryDirectory() as td:
        cwd = os.getcwd()
        try:
            os.chdir(td)
            os.environ.pop("MCDONALD_CASES", None)
            p = clipmod.out_prefix(None, "somecase")
            check(Path(td).resolve() in p.resolve().parents, "default case dir is under the cwd", str(p))
            check(pkg not in p.resolve().parents, "and nowhere near the package", str(pkg))
            check(p.parent.is_dir(), "the case dir is created")
            os.environ["MCDONALD_CASES"] = str(Path(td) / "cases")
            p2 = clipmod.out_prefix(None, "somecase")
            check(p2.parent.parent.name == "cases", "MCDONALD_CASES is honoured", str(p2))
            os.environ.pop("MCDONALD_CASES", None)
            p3 = clipmod.out_prefix(Path(td) / "explicit", "somecase")
            check(p3.parent.name == "explicit", "--out wins", str(p3))
        finally:
            os.chdir(cwd)


def test_no_catalog_is_a_normal_condition():
    """Most clips are not in any catalog. That must not be an error, and must
    not silently borrow another release's provenance."""
    print("\npackaging: the catalog is optional")
    catalog.use(None)
    os.environ["MCDONALD_CATALOG"] = "none"
    cat = catalog.active()
    check(isinstance(cat, catalog.NullCatalog), "MCDONALD_CATALOG=none is no catalog", cat.name)
    os.environ.pop("MCDONALD_CATALOG", None)
    check(cat.videos() == [], "which has no records")
    check(cat.by_path("/anything/at/all.mp4") is None, "and matches nothing")
    check(cat.disclosure_rate() == (0, 0), "and reports no disclosure rate")

    with tempfile.TemporaryDirectory() as td:
        idx = Path(td) / "pursue_index"
        idx.mkdir()
        (idx / "records.csv").write_text(
            "type,title,release,redacted,blurb,out_path\n"
            "video,\"DOW-UAP-PR999, Test Clip\",06,no,\"This video was digitally altered before being reported.\",data/x.mp4\n"
            "video,\"DOW-UAP-PR998, Other\",06,no,\"Nothing unusual stated.\",data/y.mp4\n"
            "document,\"A document\",06,no,\"text\",data/d.pdf\n", encoding="utf-8")
        c = catalog.PursueCatalog(idx / "records.csv")
        check(len(c.videos()) == 2, "a PURSUE catalog reads only videos", f"{len(c.videos())} records")
        check(c.disclosure_rate() == (1, 2), "and counts disclosures", str(c.disclosure_rate()))
        rec = c.by_id("PR999")
        check(len(rec) == 1 and "digitally altered" in (c.disclosure(rec[0]) or ""),
              "and quotes the release's own sentence")
        catalog.use(None)


def test_the_pursue_videos_ship_with_the_package():
    """With nothing set up, PR113 means something: the package carries the PURSUE videos'
    list, and a record says where its file can be downloaded and how large it is. A video
    that is not in it borrows nothing (Jacob, 2026-09-24)."""
    print("\npackaging: the PURSUE list ships, and says where each video can be had")
    catalog.use(None)
    os.environ.pop("MCDONALD_CATALOG", None)
    with tempfile.TemporaryDirectory() as td:
        os.environ["MCDONALD_HOME"] = td
        try:
            cat = catalog.active()
            recs = cat.videos()
            check(isinstance(cat, catalog.ShippedCatalog) and len(recs) == 144, "with nothing set, the catalog is the shipped one",
                  f"{cat.name}, {len(recs)} videos")
            check(all(r["url"].startswith("https://") and r["url"].endswith(".mp4") and r["bytes"] > 0 for r in recs),
                  "every video has an address to download it from, and a size")
            pr113 = cat.by_id("PR113")
            check(len(pr113) == 1 and pr113[0]["path"] == str(Path(td) / "videos" / "DOD_111830133.mp4"),
                  "a record's file is in the storage folder's videos, under the mirror's name", pr113[0]["path"] if pr113 else "")
            check(cat.by_path("/anything/at/all.mp4") is None, "a video that is not in it matches nothing")
            check(cat.by_path("/a/mirror/DOD_111830133.mp4")["id"] == "PR113", "and a copy of one, wherever it is, is known")
        finally:
            os.environ.pop("MCDONALD_HOME", None)
            catalog.use(None)


def test_a_catalog_video_is_downloaded_whole_or_not_at_all():
    """resolve() fetches a record's file when it is not on this computer, through a
    .part file, so that a video under its real name is always whole."""
    print("\npackaging: downloading a catalog's video")
    import io
    import urllib.request
    from mcdonald import storage
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "served.mp4"
        src.write_bytes(os.urandom(300_000))
        url = src.as_uri()

        class One(catalog.Catalog):
            name = "test"

            def __init__(self, size):
                self.rec = dict(path=str(Path(td) / "home" / "videos" / "x.mp4"), id="PR999", title="DOW-UAP-PR999, x",
                                url=url, bytes=size)

            def videos(self):
                return [self.rec]
        catalog.use(One(300_000))
        seen = []

        def fetch(rec, dest):
            seen.append(dest)
            return storage.download(rec["url"], dest, rec["bytes"], chunk=65536,
                                    progress=lambda done, total: seen.append((done, total)))
        try:
            path, tag, rec = clipmod.resolve("PR999", fetch=fetch)
            check(path.read_bytes() == src.read_bytes() and tag == "pr999" and seen[0] == path,
                  "a record whose file is not here is downloaded to its path", str(path))
            check(seen[-1] == (300_000, 300_000) and len(seen) > 3, "saying how far along it is", f"{len(seen) - 1} steps")
            seen.clear()
            clipmod.resolve("PR999", fetch=fetch)
            check(not seen, "and once it is there, it is not downloaded again")
            path.unlink()
            try:
                clipmod.resolve("PR999", fetch=lambda rec, dest: None)
                said = None
            except clipmod.Declined as ex:
                said = str(ex)
            check(said and not path.exists(), "said no to, it is not downloaded, and resolve says so", said)
            catalog.use(One(295_000))
            try:
                clipmod.resolve("PR999", fetch=fetch)
                said = str(seen[-1:])
            except clipmod.Stop as ex:
                said = str(ex)
            check(path.exists() and path.read_bytes() == src.read_bytes() and seen[-1] == (300_000, 300_000),
                  "the server's own length says whether it is whole, not the catalog's (DVIDS re-wrapped PR135 a few kB "
                  "larger after the catalog was written, and a tester's laptop refused it: 2026-10-22)", said)
            path.unlink(missing_ok=True)

            class Served:                                # what urlopen hands back, and the server's headers
                def __init__(self, body, headers):
                    self.body, self.headers = io.BytesIO(body), headers

                def read(self, n):
                    return self.body.read(n)

                def close(self):
                    pass

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    pass
            real = urllib.request.urlopen
            for name, served, size, words in [
                    ("less than the server said it would send", Served(b"x" * 200_000, {"Content-Length": "300000"}), 300_000, "of 300000"),
                    ("less than the catalog says, when the server does not say", Served(b"x" * 200_000, {}), 300_000, "of 300000"),
                    ("a web page instead of the video", Served(b"<html>sign in</html>", {"Content-Type": "text/html; charset=utf-8"}),
                     300_000, "web page")]:
                urllib.request.urlopen = lambda *a, served=served, **k: served
                try:
                    storage.download(url, path, size, chunk=65536)
                    said = None
                except OSError as ex:
                    said = str(ex)
                finally:
                    urllib.request.urlopen = real
                check(said and words in said and not path.exists() and not list(path.parent.glob("*.part")),
                      f"{name}: not kept, whole or part", said)
            stops = iter([False, False, True])
            try:
                storage.download(url, path, chunk=65536, stop=lambda: next(stops))
                said = None
            except storage.Incomplete as ex:
                said = str(ex)
            check(said and not path.exists() and not list(path.parent.glob("*.part")), "stopped, nothing is left of it", said)
        finally:
            catalog.use(None)


def test_frames_go_in_the_storage_folder():
    """Not the temporary directory, which on Fedora is memory (2026-09-24)."""
    print("\npackaging: where the frames go")
    from mcdonald import storage
    with tempfile.TemporaryDirectory() as td:
        os.environ["MCDONALD_HOME"] = td
        try:
            check(storage.frames() == Path(td) / "frames" and storage.videos() == Path(td) / "videos",
                  "MCDONALD_HOME is the storage folder, with frames and videos in it")
        finally:
            os.environ.pop("MCDONALD_HOME", None)
        check(storage.home().name == "mcdonald" and storage.home().parent in (Path.home() / "Documents", Path.home()),
              "without it, Documents/mcdonald", str(storage.home()))


def test_an_ambiguous_record_id_is_reported_not_guessed():
    """Bare ids are not unique across releasing bodies: PR001-PR004 each exist
    under two prefixes in the PURSUE corpus. Returning the first match would
    quietly analyse the wrong clip."""
    print("\npackaging: ambiguous record ids")
    with tempfile.TemporaryDirectory() as td:
        idx = Path(td) / "pursue_index"
        idx.mkdir()
        (idx / "records.csv").write_text(
            "type,title,release,redacted,blurb,out_path\n"
            "video,\"FBI-UAP-PR001, One\",03,no,\"x\",data/a.mp4\n"
            "video,\"LLE-UAP-PR001, Two\",06,no,\"x\",data/b.mp4\n"
            "video,\"DOW-UAP-PR144, Three\",06,no,\"x\",data/c.mp4\n", encoding="utf-8")
        c = catalog.PursueCatalog(idx / "records.csv")
        check(len(c.by_id("PR001")) == 2, "a bare ambiguous id returns both",
              f"{len(c.by_id('PR001'))} records")
        check(len(c.by_id("FBI-UAP-PR001")) == 1, "a qualified id picks one")
        check(len(c.by_id("PR001", release="06")) == 1, "a release qualifier picks one")
        check(len(c.by_id("PR144")) == 1, "an unambiguous bare id still works")
        check(c.by_id("DOW-UAP-PR144")[0]["title"].startswith("DOW-UAP-PR144"),
              "and so does its qualified form")
        catalog.use(None)


def test_a_clip_can_be_opened_before_it_is_extracted():
    """For a window that wants to show progress and offer a way out. Needs no
    video data: ffmpeg draws the clip."""
    print("\nclip: opening without extracting")
    import shutil
    import subprocess
    import tempfile
    from fractions import Fraction
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    with tempfile.TemporaryDirectory() as td:
        video = Path(td) / "drawn.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=30000/1001",
                        "-frames:v", "40", "-pix_fmt", "yuv420p", str(video)], check=True)
        clip = vf.Clip(video, f"{td}/frames", 11, 30, extract=False)
        check(clip.info["fps"] == Fraction(30000, 1001) and (clip.W, clip.H) == (320, 180),
              "it knows the clip without having extracted a frame", f"{clip.info['fps']} fps")
        check(not clip.extracted() and clip.n_extracted() == 0, "and says nothing is extracted yet")
        check(clip.extract(stop=lambda: True) is False and not clip.extracted(), "asked to stop, it stops, and is not fooled afterwards")
        check(clip.extract(stop=lambda: False) is True and clip.extracted() and clip.n_extracted() == 20,
              "left alone, it extracts the window", f"{clip.n_extracted()} frames")
        check(clip.path(11).exists() and clip.path(30).exists() and not clip.path(10).exists() and not clip.path(31).exists(),
              "under their absolute frame numbers, and no others")
        again = vf.Clip(video, f"{td}/frames", 11, 30)
        check(again.extracted() and again.rgb(11).shape == (180, 320, 3), "and the ordinary way of opening it finds them there")
        # two windows extracted apart leave a third's ends on disk and a gap between them (V_BIRD_020, 2026-10-20)
        vf.Clip(video, f"{td}/frames", 31, 34)
        for n in range(21, 26):
            again.path(n).unlink()
        gap = vf.Clip(video, f"{td}/frames", 15, 34, extract=False)
        check(gap.path(15).exists() and gap.path(34).exists() and not gap.extracted(),
              "a window whose ends are on disk but not all between is not taken for extracted", f"{gap.n_extracted()} of 20 from its start")
        gap.extract()
        check(gap.extracted() and all(gap.path(n).exists() for n in range(15, 35)), "and extracting it fills the gap")


def test_a_clip_can_be_watched_before_it_is_extracted():
    """reel.Reel is what the range chooser plays: frames from an ffmpeg pipe, under the
    numbers extraction will give them. The first version was right on the first frame of
    every seek and a frame out on all the others (ffmpeg fills a constant rate with a copy
    of the first frame unless told -vsync 0), so runs of frames are checked, not one."""
    print("\nreel: watching a clip that has not been extracted")
    import shutil
    import subprocess
    import tempfile
    import time
    from mcdonald.reel import Reel
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    with tempfile.TemporaryDirectory() as td:
        video = Path(td) / "drawn.mp4"                        # a counter and a moving bar: no two frames alike
        # With a sound track, as real clips have: it is the sound track that makes ffmpeg copy
        # the first frame after a seek. Without one this check passes with -vsync 0 taken out
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=30000/1001",
                        "-f", "lavfi", "-i", "sine=frequency=440", "-frames:v", "200", "-g", "25", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-shortest", str(video)], check=True)
        clip = vf.Clip(video, f"{td}/frames")
        truth = {n: clip.rgb(n) for n in clip.frames()}
        arrived = []
        reel = Reel(video, clip.info, on_frame=arrived.append)

        def wait(n, seconds=20):
            t0 = time.monotonic()
            while reel.get(n) is None and time.monotonic() - t0 < seconds:
                time.sleep(0.002)
            return reel.get(n) is not None

        def is_frame(n):
            """Which extracted frame the reel's frame n is most like: it should be n."""
            f = np.frombuffer(reel.get(n), np.uint8).reshape(reel.h, reel.w, 3).astype(np.float32)
            err = {m: float(np.abs(truth[m] - f).mean()) for m in range(max(1, n - 3), min(200, n + 3) + 1)}
            return min(err, key=err.get)

        check((reel.w, reel.h, reel.total, reel.exact) == (320, 180, 200, True),
              "it is no wider than the clip, and knows a constant rate from time zero when it sees one")
        reel.want(150)
        got = wait(150) and wait(190)
        wrong = [n for n in range(150, 191) if is_frame(n) != n] if got else None
        check(got and not wrong, "a seek into the middle of a group of pictures lands on the frame asked for, "
              "and the frames read on after it keep their numbers", f"wrong: {wrong}")
        check(reel.seeks == 1 and arrived[0] == 150, "reading on is one ffmpeg, not one for each frame", f"{reel.seeks} started")
        ok = True
        for n in range(149, 39, -1):                          # a step back at a time, as a person would
            reel.want(n, -1)
            ok = ok and wait(n) and is_frame(n) == n
        check(ok and reel.seeks <= 5, "going backward is served in chunks read ahead of the steps, under the same numbers",
              f"110 steps back, {reel.seeks - 1} more started")
        reel.want(120, +1, around=True)
        check(wait(120) and wait(119) and wait(95), "stopped on a frame, what is just behind it is fetched as well as what is ahead")
        reel.want(200)
        check(wait(200) and is_frame(200) == 200 and reel.last == 200 and reel.error is None, "the last frame is the last frame")
        reel.close()
        reel._thread.join(5)
        check(not reel._thread.is_alive() and reel._proc is None, "closing it ends the thread and ffmpeg")

        long = Reel(video, {**clip.info, "nb_frames": 260, "frames": 260})   # a header that counts a sound track's length
        long.want(260)
        t0 = time.monotonic()
        while long.last != 200 and long.error is None and time.monotonic() - t0 < 20:
            time.sleep(0.01)
        check(long.last == 200 and long.error is None, "a file that ends before its header said is found to, and is not an error",
              f"last {long.last}, {long.error}")
        long.close()
        junk = Path(td) / "junk.mp4"
        junk.write_bytes(b"not a video at all")
        none = Reel(junk, clip.info)
        none.want(1)
        t0 = time.monotonic()
        while none.error is None and time.monotonic() - t0 < 20:
            time.sleep(0.01)
        check(none.error is not None and "junk.mp4" in none.error, "a file ffmpeg cannot read is said to be, once, and not retried forever",
              f"{none.error}; {none.seeks} started")
        none.close()


def test_ffmpeg_is_checked_up_front():
    print("\npackaging: runtime dependencies")
    try:
        clipmod.require_ffmpeg()
        check(True, "ffmpeg and ffprobe are present")
    except clipmod.MissingTool as e:
        check(False, "ffmpeg and ffprobe are present", str(e))


def test_the_object_is_proposed_with_no_marks_to_go_on():
    """mcdonald.propose: what moves against the background, best first, for someone to say
    yes or no to. The scene is autolink's: a disc on a known path and a brighter disc that
    never moves -- which is the strongest thing in every frame, and is not a proposal at
    all, because it does not move against the background."""
    print("\npropose: what moves against the background, with no marks to go on")
    from mcdonald import autolink, propose
    clip = PlantedClip(n1=24, seen=range(1, 13))
    masks = vf.static_masks(clip)                          # as the window and `look --propose` make them
    seen = []
    steps = list(propose.search(clip, masks, procs=0, block=8, progress=lambda *a: seen.append(a)))
    props = steps[-1][2]
    check(len(steps) == 3 and [d for d, _, _ in steps] == [8, 16, 20] and seen and seen[-1][1:] == (20, 20),
          "it yields what it has found so far, a block of frames at a time, and says how far it has got", f"{[d for d, _, _ in steps]}")
    ok = check(bool(props), "something is proposed")
    if not ok:
        return
    first = props[0]
    off = max(np.hypot(first.track[n][0] - clip.truth(n)[0], first.track[n][1] - clip.truth(n)[1]) for n in first.frames)
    check(off < 3.0 and len(first.track) >= 6 and not first.dark, "the first proposal is the disc that moves, along its path", f"{len(first.track)} frames, worst {off:.1f} px")
    check(abs(first.velocity[0] - 41.0) < 1.0 and abs(first.velocity[1] - 6.0) < 1.0 and abs(first.against_background - np.hypot(41, 6)) < 1.5,
          "at the velocity it was given, which is its velocity against a background that is still", f"({first.velocity[0]:+.1f}, {first.velocity[1]:+.1f})")
    decoy = [p for p in props if any(np.hypot(x - clip.DECOY[0], y - clip.DECOY[1]) < 15 for x, y in p.track.values())]
    check(not decoy, "the brighter disc that never moves is not proposed: it is the strongest thing in the frame, and it does not move")
    seeds = first.seeds()
    check(len(seeds) >= 2 and all(np.hypot(x - clip.truth(n)[0], y - clip.truth(n)[1]) < 3.0 for n, (x, y) in seeds.items())
          and all(70 <= x <= clip.W - 70 for x, _ in seeds.values()),
          "its seeds are places it was seen, off the frame's edge, where the detector can go", str(sorted(seeds)))
    link = list(autolink.link_from_marks(clip, seeds, masks=masks, procs=0))[-1]
    check(link.track and _off(link.track, clip) < 1.0, "and the package's own linker, started from them, is on the disc",
          f"{len(link.track)} frames, worst {_off(link.track, clip):.2f} px")
    check(first.strength() in ("strong", "fair") and "against the background" in first.describe() and "nothing else moves the same way" in first.describe(),
          "a proposal says what it is like, in words", first.describe())
    check(first.all_round > 0.5 and "a spot with background all round it" in first.describe(),
          "and that the disc is a spot: there is background on every side of it", f"{first.all_round:.2f}")
    d = first.to_dict()
    check(set(d["mark_at"]) == {str(n) for n in seeds} and isinstance(d["score"], float) and d["frames"] == [first.frames[0], first.frames[-1]]
          and d["background_all_round"] == round(first.all_round, 2),
          "and as fields, with the marks that would take it")

    # a spot, or an edge or a stroke? Jacob, 2026-09-21: "worked on PR144 but not on PR113". On PR113 the ten
    # proposals above the object were the edges of redaction blocks, the rim of the picture and the strokes of a
    # scrolling heading tape: compact peaks in the residual, and none of them a compact thing in the frame.
    yy, xx = np.mgrid[:121, :121].astype(float)
    flat = np.full((121, 121), 120.0)
    disc = flat - 60.0 * (np.hypot(xx - 60, yy - 60) <= 10)                  # a dark blob, as PR113's object is
    edge = flat - 60.0 * (yy > 60)                                          # the edge of a block
    bar = flat + 90.0 * (np.abs(yy - 60) <= 2)                              # a stroke of a symbol
    slant = flat + 90.0 * (np.abs((yy - 60) * 0.92 - (xx - 60) * 0.38) <= 2)
    corner = flat - 60.0 * ((yy > 60) & (xx > 60))
    got = {name: propose.all_round(img, 60.0, 60.0, pol, 20.0) for name, img, pol in
           (("disc", disc, -1), ("edge", edge, -1), ("bar", bar, +1), ("slanted bar", slant, +1), ("corner", corner, -1))}
    check(got["disc"] > 0.9 and max(got["edge"], got["corner"]) < 0.05 and max(got["bar"], got["slanted bar"]) < 0.3,
          "a compact thing has background all round it; the edge of a block, a stroke and a corner do not",
          ", ".join(f"{k} {v:.2f}" for k, v in got.items()))
    check(propose.all_round(disc, 64.0, 57.0, -1, 20.0) > 0.9, "and a centroid a few pixels off the thing still finds it")
    check(propose.all_round(disc, 60.0, 60.0, +1, 20.0) < 0.05, "asked about a bright thing where the thing is dark, it says no")
    P = propose.Proposal
    track = lambda k: {n: (100.0 + 100.0 * n, 100.0 + 5.0 * n) for n in range(1, k + 1)}
    spot = P(track(4), True, 21.0, (100.0, 5.0), 100.0, 1.5, 300.0, 1.0, 0, all_round=0.65)
    block = P({n: (x, y + 400) for n, (x, y) in track(9).items()}, True, 17.0, (100.0, 5.0), 100.0, 1.5, 800.0, 1.0, 0, all_round=0.0)
    ranked = propose.score([block, spot])
    check(ranked[0] is spot and block.score > 0, "so a spot seen in four frames comes before an edge seen in nine -- which stays on the list, lower down",
          f"spot {spot.score:.2f}, edge {block.score:.2f}")

    # a thing slower than its own width. Jacob, 2026-09-21, on PR055: "Find the object worked, but linking did
    # not". The residual of a slow large disc is its rim; the marks went on the rim, 11 px from the centre, and
    # no spot size came within the link's 6 px of them. The proposal is now of the thing itself.
    slow = SlowDisc(v=(1.5, 0.4), n1=50, seen=range(1, 51))
    slow_masks = vf.static_masks(slow)
    props = propose.find(slow, slow_masks, procs=0)
    ok = check(bool(props), "a disc slower than its own width is still proposed")
    if ok:
        disc = props[0]
        rim = max(np.hypot(p[0] - slow.truth(n)[0], p[1] - slow.truth(n)[1])
                  for n, pk in ((n, propose._frame_peaks(slow, slow_masks, n)) for n in disc.frames[:6]) for p in pk
                  if np.hypot(p[0] - slow.truth(n)[0], p[1] - slow.truth(n)[1]) < 30)
        centre = max(np.hypot(disc.track[n][0] - slow.truth(n)[0], disc.track[n][1] - slow.truth(n)[1]) for n in disc.frames)
        check(rim > 8.0 and centre < 3.0, "what changed is its rim, a radius from the centre; the proposal is where the thing is",
              f"the residual's peaks up to {rim:.1f} px off, the proposal at most {centre:.1f} px")
        check(disc.dark and 18 <= disc.size_px <= 32 and disc.all_round > 0.5 and "a spot" in disc.describe(),
              "and says what the thing is like -- its own width, and that it is a spot -- not what its rim is like",
              f"{disc.size_px:.0f} px, all round {disc.all_round:.2f}")
        link = list(autolink.link_from_marks(slow, disc.seeds(), masks=slow_masks, procs=0))[-1]
        check(bool(link.track) and _off(link.track, slow) < 1.5 and len(link.track) >= 30 and link.size >= 15,
              "so the link from its marks is on the disc, with a spot size that fits it",
              f"{len(link.track)} frames, worst {_off(link.track, slow) if link.track else float('nan'):.2f} px, {link.size:g} px")
        on_rim = {}
        for n in disc.seeds():
            near = [p for p in propose._frame_peaks(slow, slow_masks, n) if np.hypot(p[0] - slow.truth(n)[0], p[1] - slow.truth(n)[1]) < 30]
            if near:
                on_rim[n] = max(near, key=lambda p: p[2])[:2]
        rim_link = list(autolink.link_from_marks(slow, on_rim, masks=slow_masks, procs=0))[-1]
        check(not rim_link.track or rim_link.size <= 9,
              "where marks on its rim get nothing (PR055) or a small spot that rides the rim (here): a clean track of the wrong thing",
              rim_link.say[:80])
    yy, xx = np.mgrid[:301, :301].astype(float)
    sized = {d: propose.thing_at(120.0 - 70.0 * (np.hypot(xx - 150, yy - 150) <= d / 2), 150 + d / 2, 150.0, -1) for d in (8, 18, 36, 72)}
    check(all(np.hypot(t[0] - 150, t[1] - 150) <= 4.0 and 0.7 * d <= t[2] <= 1.4 * d for d, t in sized.items()),
          "asked at the rim of a disc 8 to 72 px across, it answers with the centre and the width",
          ", ".join(f"{d}: {t[2]:.0f} px, {np.hypot(t[0] - 150, t[1] - 150):.0f} off" for d, t in sized.items()))

    # ... and where it ends. PR055's disc drifts into a dark gap between clouds and cannot be seen in it. The chain
    # ran on into the gap, and a later "piece" -- the gap itself, 104 px and still -- was joined on where the disc
    # was heading; the last mark went there, and the link, which chooses its detector at the first and last marks,
    # linked nothing.
    path = lambda n: (100.0 + 3.0 * n, 100.0 + 0.6 * n)
    seen = [(*path(n), 30.0, 5.0, -1, 0.1, *path(n), 24.0, 0.8, 40.0) for n in range(1, 13)]           # the disc, well seen
    faded = [(*path(n), 30.0, 5.0, -1, 0.1, *path(n), 24.0, 0.1, 2.0) for n in range(13, 16)]         # the same place, nothing there
    own = propose._own_centres(list(range(1, 16)), seen + faded, 2)
    check(own is not None and own[0] == list(range(1, 13)), "a point where the thing has faded to nothing is left out of the proposal",
          str(own[0] if own else None))
    P2 = propose.Proposal
    mk2 = lambda frames, size, v, score: P2({n: path(n) for n in frames}, True, size, v, 3.0, 2.0, 60.0, 1.0, 0, score=score)
    disc_p, gap_p, later = mk2(range(1, 21), 24.0, (3.0, 0.6), 8.0), mk2(range(40, 46), 104.0, (-0.5, -0.3), 0.01), mk2(range(30, 36), 22.0, (3.0, 0.6), 2.0)
    rows = propose.distinct([disc_p, later, gap_p])
    check(gap_p in rows and max(disc_p.track) == 35 and later not in rows,
          "a later piece is joined on only if it is like the thing: the same disc seen again is, a cloud gap where it was heading is not",
          f"the proposal runs to frame {max(disc_p.track)}; rows {len(rows)}")

    # PR142: the object drags a fainter copy of itself a frame behind, 20 px back along the track. The copy's chain
    # "ran beside" the object's, was folded into its row, and lent it frames -- and the proposal's first marks went
    # on the copy, where the link found nothing. Beside it is not on it.
    body = mk2(range(20, 61), 7.0, (3.0, 0.6), 20.0)
    copy = P2({n: (path(n)[0] - 19.6, path(n)[1] - 3.9) for n in range(5, 31)}, True, 7.0, (3.0, 0.6), 3.0, 1.1, 60.0, 1.0, 0, score=3.0)
    piece = P2({n: (path(n)[0] + 1.0, path(n)[1] - 1.0) for n in range(8, 20)}, True, 7.0, (3.0, 0.6), 3.0, 2.0, 30.0, 1.0, 0, score=2.0)
    rows = propose.distinct([body, copy, piece])
    check(rows == [body] and min(body.track) == 8 and all(abs(body.track[n][0] - path(n)[0]) < 2 for n in body.track),
          "what runs beside a thing is folded into its row and lends it nothing; what runs on it lends the frames it alone saw",
          f"the proposal now runs {min(body.track)}-{max(body.track)}")
    # One thing in three pieces, best-scored last: PR144. The first piece is not where the last was heading sixty
    # frames on, and becomes a row; the middle joins the last, which now runs over the first to the pixel.
    turn = lambda n: (300.0 + (5.0 * n if n <= 90 else 450.0 + 1.0 * (n - 90)), 200.0 + (0.0 if n <= 90 else 1.5 * (n - 90)))
    part = lambda frames, v, score: P2({n: turn(n) for n in frames}, False, 11.0, v, 10.0, 3.0, 100.0, 0.5, 0, score=score)
    last, first_, middle = part(range(150, 200), (1.0, 1.5), 28.0), part(range(2, 91), (5.0, 0.0), 21.0), part(range(55, 135), (2.0, 1.2), 14.0)
    rows = propose.distinct([last, first_, middle])
    check(rows == [last] and (min(last.track), max(last.track)) == (2, 199),
          "pieces of one thing end as one row whatever order their scores put them in", f"{len(rows)} rows; the first runs {min(last.track)}-{max(last.track)}")

    # ... and a long track is not a parabola. PR142's object crosses 1800 px in a hundred frames, in uneven steps, under
    # a camera that is not still; measured against one curve, stretches of a good track were thrown out (and the copy
    # lent its frames there). Each point is held against the line of its neighbours instead.
    ns = list(range(1, 101))
    far = lambda n: (19.0 * n + 60.0 * np.sin(n / 9.0) + (4.0 if n % 3 == 0 else 0.0), 300.0 + 0.004 * n * n + 25.0 * np.sin(n / 14.0))
    wob = np.random.default_rng(3).normal(0, 2.5, (len(ns), 2))
    long_pts = [(far(n)[0] + w[0], far(n)[1] + w[1], 25.0, 6.0, 1, 0.5, *far(n), 7.0, 0.6, 12.0) for n, w in zip(ns, wob)]
    own = propose._own_centres(ns, long_pts, 2)
    check(own is not None and len(own[0]) >= 98, "a long track that winds keeps its points", f"{len(own[0]) if own else 0} of 100 kept")
    stray = list(long_pts)
    stray[49] = (*stray[49][:6], far(50)[0] - 19.0, far(50)[1], 7.0, 0.5, 7.0)          # frame 50: the copy was taken, a step behind
    own = propose._own_centres(ns, stray, 2)
    check(own is not None and 50 not in own[0] and 49 in own[0] and 51 in own[0] and len(own[0]) >= 97,
          "and a stray point goes without taking its neighbours with it", f"{len(own[0]) if own else 0} kept")

    # the gate: generous along the track, tight across it
    v = (-102.0, 96.0)
    u = np.array(v) / np.hypot(*v)
    along, across = 19.0 * u, 19.0 * np.array([-u[1], u[0]])
    check(propose.off_path(along[0], along[1], v) <= 1.0 < propose.off_path(across[0], across[1], v),
          "a fast thing may be 19 px early or late along its track -- PR113's steps are 92, 111 and 104 px -- and not 19 px to one side",
          f"{propose.off_path(along[0], along[1], v):.2f} along, {propose.off_path(across[0], across[1], v):.2f} across")
    P = propose.Proposal
    mk = lambda score: P({1: (0, 0), 2: (1, 1), 3: (2, 2)}, False, 9.0, (1.0, 1.0), 1.4, 1.0, 3.0, 0.0, 0, score=score)
    check([p.score for p in propose.shortlist([mk(36), mk(3.1), mk(3.0), mk(2.8), mk(2.7)])] == [36, 3.1, 3.0],
          "one strong thing and a tail of weak ones is a short list: the best three, and any other within a quarter of the best")
    check(len(propose.shortlist([mk(3.5), mk(2.1), mk(1.9), mk(1.7), mk(1.6), mk(1.6)])) == 6,
          "where nothing stands out -- PR113, where every row says weak -- the list is longer")



def test_a_crawler_in_a_still_scene_is_proposed():
    """Jacob, 2026-09-29: Galileo flyer 1 "actually has 4 different objects". Find had two of them; the
    paper's bird, a quarter of a pixel a frame for 18 s, was two three-frame fragments scored 0.0, and
    a second bird along the top edge was not on the list. A thing that has not moved its own width in
    2k frames leaves nothing in the double difference at k; where the scene holds still it is compared
    again half a second either side (`propose.still_peaks`), and a still scene's edge is scene."""
    print("\npropose: a thing too slow for the double difference, in a scene that holds still")
    from mcdonald import propose
    clip = Crawler()
    masks = vf.static_masks(clip)
    bad = propose.not_scene(clip, masks)
    n = 75
    g0 = clip.grey(n)
    near = lambda pk, xy, r=4.0: [p for p in pk if np.hypot(p[0] - xy[0], p[1] - xy[1]) <= r]
    rk = g0 - np.maximum(clip.grey(n - propose.K), clip.grey(n + propose.K))
    at_k = propose.peaks(rk, bad)
    r = rk[int(clip.truth(n)[1]) - 3:int(clip.truth(n)[1]) + 4, int(clip.truth(n)[0]) - 3:int(clip.truth(n)[0]) + 4].max()
    check(not near(at_k, clip.truth(n)), "over 2 frames either side, a spot that crawls a third of a pixel a frame leaves nothing above the floor",
          f"{r:.1f} grey levels at the crawler, noise included; the floor is 4 after smoothing")
    check(propose.still_again(clip, n, bad, propose.K) is None and propose.still_again(Crawler(noise=False), n, bad, propose.K) is None,
          "the background measured again over a second is not the crawler's own motion -- not with a sensor's pattern and noise, "
          "and not in a drawn sky with nothing else sharp in it, where its peak stands above the one at zero shift")
    pk = propose._frame_peaks(clip, masks, n)
    got, got2 = near(pk, clip.truth(n)), near(pk, clip.second(n))
    check(bool(got) and got[0][11] == 1 and got[0][2] > 6, "half a second either side, the still pass has it, and marks the peak as its alone",
          f"{got[0][2]:.0f} grey levels, {np.hypot(got[0][0] - clip.truth(n)[0], got[0][1] - clip.truth(n)[1]):.1f} px off" if got else "nothing")
    check(bool(got2), "and the one 18 px from the top, inside the band a registered residual is not believed in",
          f"{np.hypot(got2[0][0] - clip.second(n)[0], got2[0][1] - clip.second(n)[1]):.1f} px off" if got2 else "nothing")
    props = propose.find(clip, masks, procs=0)
    on = lambda p, where: p is not None and float(np.median([np.hypot(p.track[m][0] - where(m)[0], p.track[m][1] - where(m)[1]) for m in p.frames])) < 2.0
    first = props[0] if props else None
    ok = check(on(first, clip.truth), "the crawler is the first proposal, on its path", f"{len(props)} proposals")
    if ok:
        check(abs(first.velocity[0] - clip.V[0]) < 0.08 and abs(first.velocity[1] - clip.V[1]) < 0.08, "at its velocity",
              f"({first.velocity[0]:+.2f}, {first.velocity[1]:+.2f}) for ({clip.V[0]:+.2f}, {clip.V[1]:+.2f})")
        span = first.frames[-1] - first.frames[0]
        check(span >= 100 and first.path_px > 0.9 * span * np.hypot(*clip.V) and first.strength() != "weak",
              "for the whole clip but its ends, its path end to end and not one block's, and not weak",
              f"frames {first.frames[0]}-{first.frames[-1]}, path {first.path_px:.0f} px, {first.strength()} {first.score:.1f}")
        check("moves 0.3 pixels each frame against the background, " in first.describe(), "said in tenths of a pixel, with the whole of it", first.describe())
    check(any(on(p, clip.second) for p in props), "the one along the top edge is on the list too",
          "; ".join(f"{p.track[p.frames[0]][0]:.0f},{p.track[p.frames[0]][1]:.0f}" for p in props[:4]))
    # its marks keep off the band at the frame's edge that the smallest detector closes (15 px), since none can be 70 px in
    P = propose.Proposal
    along = P({m: (634.0 - 0.25 * m, 18.0) for m in range(1, 301)}, False, 7.0, (-0.25, 0.0), 0.25, 2.0, 75.0, 0.5, 0, all_round=0.5,
              frame_size=(640, 512))
    seeds = along.seeds()
    check(len(seeds) >= 2 and all(15 <= x <= 625 for x, _ in seeds.values()) and min(seeds) >= 36,
          "a thing that runs 18 px from the top for 300 frames is marked 15 px in from the right edge, not at its first frames",
          f"frames {sorted(seeds)}")
    # the still pass's chains are held to what the pass is for: a thing that lasts the half second it compares across,
    # and crawls -- what moves a pixel a frame has moved enough in k frames for the residual there to have it
    still = lambda n, x: (x, 50.0, 5.0, 4.0, 1, 0.5, x, 50.0, 7.0, 0.5, 5.0, 1)
    short = ([1, 2, 3], [still(1, 10.0), still(2, 20.0), still(3, 30.0)])
    slow = ([1, 15, 31], [still(1, 10.0), still(15, 12.0), still(31, 14.0)])
    fast = ([1, 15, 31], [still(1, 10.0), still(15, 40.0), still(31, 70.0)])
    check(propose.lasting([short, slow, fast], 30) == [slow],
          "of the still pass's chains, one that lasts the half second and crawls is kept; a short one and a fast one are not")
    # a folded row's path is the whole of what it was lent, and a crawler that crosses 90 px in 300 frames moves
    P = propose.Proposal
    p = P({m: (100.0 + 0.3 * m, 50.0) for m in range(1, 301)}, False, 7.0, (0.3, 0.0), 0.3, 2.0, 27.0, 0.5, 0, all_round=0.7)
    propose.score([p])
    check(abs(p.path_px - 89.7) < 0.1 and p.strength() == "strong",
          "scored, a row's path is end to end of all it was lent, and a third of a pixel a frame for 300 frames is motion against the background",
          f"{p.path_px:.1f} px, {p.score:.1f}")

def _pid(x):
    import os
    return os.getpid()


def test_a_frame_is_read_the_quick_way_and_the_same_way():
    """`clip.grey_of` and `chroma_of`: what `rgb.mean(2)` and `rgb.max(2) - rgb.min(2)` give, bit for bit,
    at a fifth and a fifteenth of the time -- every stage reads every frame through them. An integer
    frame takes the slow way, as `mean` promotes it."""
    from mcdonald.clip import chroma_of, grey_of
    rng = np.random.default_rng(7)
    f = rng.uniform(0, 255, (48, 64, 3)).astype(np.float32)
    f[3, 4], f[5, 6], f[7, 8] = (255, 0, 0), (1e-3, 200.5, 255), (0.1, 0.2, 0.3)
    g = grey_of(f)
    check(np.array_equal(g, f.mean(2)) and g.dtype == f.mean(2).dtype, "grey_of is mean(2), bit for bit, on a float32 frame")
    d = f.astype(np.float64)
    check(np.array_equal(grey_of(d), d.mean(2)), "and on a float64 one")
    check(np.array_equal(chroma_of(f), f.max(2) - f.min(2)), "chroma_of is max(2) - min(2)")
    u = f.astype(np.uint8)
    check(np.array_equal(grey_of(u), u.mean(2)) and np.array_equal(chroma_of(u), u.max(2) - u.min(2)),
          "and an integer frame gives what the reductions give too")


def test_the_fft_convolution_is_scipys_to_the_bit():
    """`forensics.fftconvolve` is scipy.signal's on scipy.fft alone (the window's start no longer imports
    scipy.signal for it): the same transforms at the same sizes, so the same numbers."""
    from scipy.signal import fftconvolve as scipys
    rng = np.random.default_rng(3)
    for dt in (np.float32, np.float64):
        a, b = rng.normal(size=(61, 77)).astype(dt), rng.normal(size=(9, 12)).astype(dt)
        for mode in ("full", "same", "valid"):
            ours, theirs = vf.fftconvolve(a, b, mode), scipys(a, b, mode)
            check(ours.shape == theirs.shape and ours.dtype == theirs.dtype and np.array_equal(ours, theirs),
                  f"{mode}, {np.dtype(dt).name}: the same numbers, bit for bit",
                  f"max |diff| {np.abs(ours - theirs).max() if ours.shape == theirs.shape else 'shape'}")


def test_the_detector_by_fft_finds_the_same_spots():
    """From 9 px the spot kernel is applied by FFT (direct correlation is 21 s a frame at 45 px, 0.4 by
    FFT): the same spots, in the same order, at the same positions, the responses to a part in a
    million -- on a frame with spots of four sizes, both polarities, every size the link may choose."""
    rng = np.random.default_rng(11)
    yy, xx = np.mgrid[:480, :640]
    g = 60 + rng.normal(0, 3, (480, 640))
    for (x, y), w, amp in (((200, 200), 4.0, 120), ((400, 180), 9.0, 80), ((300, 300), 15.0, 60), ((480, 320), 3.0, -50)):
        g += amp * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * w ** 2))
    g = np.clip(g, 0, 255).astype(np.float32)
    bad = np.zeros(g.shape, bool)
    for size in (9.0, 15.0, 21.0, 31.0, 45.0):
        for dark in (False, True):
            direct = vf.source_candidates(g, bad, size, dark, n_max=None, min_resp=5.0, fft=False)
            by_fft = vf.source_candidates(g, bad, size, dark, n_max=None, min_resp=5.0, fft=True)
            same = len(direct) == len(by_fft) and all(a[:2] == b[:2] and abs(a[2] - b[2]) <= 1e-5 * max(abs(a[2]), 1.0)
                                                      for a, b in zip(direct, by_fft))
            check(same, f"size {size:g}, {'dark' if dark else 'bright'}: the {len(direct)} spots are the same by FFT",
                  "" if same else f"direct {direct[:3]} fft {by_fft[:3]}")
    check(vf.spot_response(g, 5.0).dtype == vf.spot_response(g, 9.0).dtype == np.float32, "and the response keeps the frame's precision either way")


def test_pools_are_no_larger_than_the_cpus_there_are_to_run_them():
    """Under a batch scheduler the machine has twelve CPUs and the job has four. `os.cpu_count()`
    says twelve; ten worker processes on four CPUs finish no sooner and take ten processes' memory."""
    print("\nprogress: pools follow the allocation, not the machine")
    import os
    from mcdonald import autolink, progress
    here = progress.cpus()
    check(1 <= here <= (os.cpu_count() or 1), "cpus() is what this process may run on", f"{here} of {os.cpu_count()}")
    keep = os.environ.get("SLURM_CPUS_PER_TASK")
    os.environ["SLURM_CPUS_PER_TASK"] = "2"
    try:
        pids = set(progress.pooled(6, _pid, range(24)))
        check(progress.cpus() == min(2, here) and len(pids) <= 2 and autolink.default_procs() == min(2, here),
              "in a two-CPU job a pool asked for six has two, and so has the link's", f"{len(pids)} worker processes")
    finally:
        if keep is None:
            del os.environ["SLURM_CPUS_PER_TASK"]
        else:
            os.environ["SLURM_CPUS_PER_TASK"] = keep


def test_a_person_can_say_how_many_cpus_to_use():
    """Jacob, 2026-10-11: "mcdonald CLI should have an optional flag to choose the maximum number of CPU cores to
    allow". `--cpus N`, before the command or after it, caps every pool (MCDONALD_CPUS, so the processes it starts
    see it too), the link's included; it is never more than there are, and a bad number is a usage error."""
    print("\nprogress: --cpus N caps every pool")
    import os
    from mcdonald import autolink, cli, progress
    keep = os.environ.pop(progress.CPUS_VAR, None)
    here = progress.cpus()
    try:
        rest = cli.take_cpus(["--cpus", "2", "run", "PR113", "--json"])
        check(rest == ["run", "PR113", "--json"] and os.environ[progress.CPUS_VAR] == "2" and progress.cpus() == min(2, here)
              and progress.cpus(allowed=False) == here, "--cpus 2 before the command: taken out, and two is the most",
              f"{rest}, cpus() {progress.cpus()} of {here}")
        pids = set(progress.pooled(6, _pid, range(24)))
        check(len(pids) <= 2 and autolink.default_procs() == min(2, here) and progress.workers(None) <= 2,
              "a pool asked for six has two, and so has the link's", f"{len(pids)} worker processes")
        check(cli.take_cpus(["layers", "PR113", "--cpus=1"]) == ["layers", "PR113"] and progress.cpus() == 1,
              "--cpus=1 after the command says the same")
        cli.take_cpus(["--cpus", str(here + 100), "run", "x"])
        check(progress.cpus() == here, "more than there are is all there are", f"{progress.cpus()} of {here}")
        bad = []
        for argv in (["--cpus"], ["--cpus", "0", "run"], ["--cpus=two", "run"], ["--cpus", "-1", "run"]):
            try:
                cli.take_cpus(argv)
            except ValueError:
                bad.append(argv)
        check(len(bad) == 4 and cli.main(["--cpus", "0", "run", "x"]) == cli.EXIT_USAGE,
              "no number, 0, a word or a negative one is a usage error", f"{len(bad)} of 4 refused")
        progress.limit_cpus(None)
        check(progress.CPUS_VAR not in os.environ and progress.cpus() == here, "and the limit can be lifted")
    finally:
        os.environ.pop(progress.CPUS_VAR, None)
        if keep is not None:
            os.environ[progress.CPUS_VAR] = keep


def _square(x):
    return x * x


def test_a_long_step_says_how_far_it_has_got_and_can_be_stopped():
    """The measuring stages were minutes of silence: Pool.map says nothing until it
    returns, and someone at the window could not tell working from hung."""
    print("\nprogress: a long step counts, and stops when asked")
    import io
    from mcdonald import progress as pg
    seen = []
    out = pg.pooled(2, _square, range(7), progress=lambda *a: seen.append(a), what="squares")
    check(out == [x * x for x in range(7)], "pooled gives what Pool.map gives, in order", str(out))
    check(seen[0] == ("squares", 0, 7) and seen[-1] == ("squares", 7, 7) and [d for _, d, _ in seen] == list(range(8)),
          "and says how far it has got after every item", f"{len(seen)} calls")
    seen, asked = [], []
    try:
        pg.pooled(2, _square, range(50), progress=lambda *a: seen.append(a), stop=lambda: asked.append(1) or len(asked) >= 3, what="squares")
        stopped = False
    except pg.Stopped:
        stopped = True
    check(stopped and seen[-1][1] == 3, "asked to stop, it stops at the next item and says so by raising Stopped", f"at {seen[-1][1]} of 50")
    got = list(pg.counted("abc", lambda *a: seen.append(a), what="letters"))
    check(got == list("abc") and seen[-1] == ("letters", 3, 3), "a plain loop has the same courtesy")
    check(pg.left(1, 100, 10.0) is None and pg.left(10, 100, 1.0) is None and abs(pg.left(25, 100, 50.0) - 150.0) < 1e-9,
          "time left is said only once there is a rate to say it from", f"{pg.left(25, 100, 50.0):.0f} s")
    check(pg.clock(65) == "1:05" and pg.clock(3723) == "1:02:03", "as a clock")
    pipe = io.StringIO()
    say = pg.to_stderr(pipe, every=0.0)
    say("step 5 of 9 · layers: comparing pairs of frames", 0, 4)
    say("step 5 of 9 · layers: comparing pairs of frames", 2, 4)
    say("step 6 of 9 · scale")
    lines = pipe.getvalue().splitlines()
    check(len(lines) == 4 and lines[0].endswith("step 5 of 9 · layers: comparing pairs of frames") and lines[0].startswith("[")
          and "2 of 4" in lines[2] and lines[3].endswith("step 6 of 9 · scale"),
          "on a command line a step is a line with the seconds gone, and its count is said beneath it", repr(lines[2].strip()))


# ---------------------------------------------------------------- every CPU (2026-10-09)
def _threads_here(_):
    return tuple(os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"))


def _late_square(x):
    import time
    time.sleep(0.02 * ((7 * x) % 5))                       # the jobs finish out of order
    return x * x


def test_pools_take_every_cpu_as_far_as_memory_allows():
    """Until 2026-10-09 a pool had ten workers at most and Follow's eight, whatever the machine: a
    machine of 32 CPUs used ten. Now a pool has one for every CPU this process may use -- unless the
    memory free has room for fewer, at what a worker holds for frames of the clip's size -- and a
    stage's jobs are handed out in runs short enough that every worker gets some."""
    print("\nprogress: a worker for every CPU, as far as memory allows")
    from mcdonald import progress as pg
    here = pg.cpus()
    free = pg.free_memory()
    check(free is None or free > 0, "the memory free is read here, or said to be unknown",
          "unknown" if free is None else f"{free / 2 ** 30:.1f} GB")
    keep = pg.free_memory
    each = pg.WORKER_BASE + pg.WORKER_PER_PIXEL * 1920 * 1080
    try:
        pg.free_memory = lambda: 2 ** 40
        check(pg.workers() == here and pg.workers(10 ** 6) == here and pg.workers(1) == 1 and pg.workers(0) == 0,
              "with memory to spare: one a CPU, no more than the CPUs whatever is asked, and 0 for none (in this process)",
              f"{pg.workers()} of {here} CPUs")
        pg.free_memory = lambda: int(2.5 * each / pg.SPARE)
        small = pg.workers(pixels=640 * 512)
        check(pg.workers() == min(here, 2) and small >= pg.workers() and (here <= 2 or small > 2),
              "with room for two workers' 1080p frames, two -- and more for smaller frames", f"{pg.workers()}, {small} at 640 x 512")
        pg.free_memory = lambda: 0
        check(pg.workers() == 1, "with no room at all, still one")
        pg.free_memory = lambda: None
        check(pg.workers() == here, "and memory that cannot be read limits nothing")
    finally:
        pg.free_memory = keep
    check(pg.chunk(60, 32, 8) == 2 and pg.chunk(60, 4, 8) == 8 and pg.chunk(5, 10, 8) == 1 and pg.chunk(7, 2, 1) == 1,
          "runs of a stage's own length, shorter where there are too few to go round: 60 pairs in twos on 32 workers")
    pool = pg.pool_of(3)
    try:
        seen = []
        got = list(pg.streamed(pool, _late_square, range(12), progress=lambda *a: seen.append(a), what="squares", ahead=4))
    finally:
        pool.terminate()
        pool.join()
    check(got == [x * x for x in range(12)] and seen[-1] == ("squares", 12, 12),
          "a stream of results comes back in order, however the jobs finish, with no more than a few out at once")


def test_a_pool_s_workers_have_one_library_thread_each():
    """A worker whose numpy starts a thread for every CPU, times a worker for every CPU, is thousands of
    threads. The batch scripts set the libraries' threads to one; nobody does that for a person at the
    window, so the pools do it for their own processes, and leave this one's as it was."""
    print("\nprogress: numpy's own threads, one in each worker")
    from mcdonald import progress as pg
    keep = {k: os.environ.get(k) for k in pg.ONE_THREAD}
    os.environ.update({k: "7" for k in pg.ONE_THREAD})
    try:
        got = set(pg.pooled(2, _threads_here, range(4)))
        check(got == {("1", "1", "1")}, "every worker has one thread for OpenMP, OpenBLAS and MKL, whatever this process has",
              str(got))
        check(all(os.environ[k] == "7" for k in pg.ONE_THREAD), "and this process keeps the seven it was given")
    finally:
        for k, v in keep.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _fields(p):
    import dataclasses
    return repr(dataclasses.asdict(p)) + p.why


def test_the_stages_find_the_same_on_a_pool_as_in_one_process():
    """2026-10-09: Find feeds one pool every frame at once (it waited for each block of 90); groups and
    flicker read their frames on a pool (they read them in one process, one after another); tether
    reads its frames ahead on threads, as the static masks read and reduce theirs. Each frame is the
    same arithmetic wherever it is done, and what comes of the frames is put together here in their
    order: the same, to the bit."""
    print("\nevery CPU: the same answers on a pool as in one process")
    from mcdonald import flicker, groups, propose, tether
    clip = PlantedClip(n1=24, seen=range(1, 13))
    one, many = vf.static_masks(clip, threads=1), vf.static_masks(clip, threads=4)
    check(one.keys() == many.keys() and all(np.array_equal(one[k], many[k]) for k in one),
          "the static masks on four threads are those of one", ", ".join(sorted(one)))
    a = list(propose.search(clip, one, procs=0, block=8))
    b = list(propose.search(clip, one, procs=2, block=8))
    check([d for d, _, _ in a] == [d for d, _, _ in b] == [8, 16, 20]
          and all([_fields(p) for p in x] == [_fields(p) for p in y] for (_, _, x), (_, _, y) in zip(a, b)) and a[-1][2],
          "Find: the same proposals, block by block, from one pool fed every frame", f"{len(a[-1][2])} proposals")
    masks = dict(blocks=np.zeros((480, 640), bool), graphics=np.zeros((480, 640), bool), colour=True)
    track = {n: _Flock("rigid").centre(n) for n in range(1, 91)}
    x, y = groups.members(_Flock("rigid"), track, masks, procs=0), groups.members(_Flock("rigid"), track, masks, procs=3)
    check(repr(x) == repr(y) and len(x[0]) >= 6, "groups: the same members, spots and background shifts",
          f"{len(x[0])} members, {sum(len(v) for v in x[1].values())} spots")
    beat = lambda: _Beating([(4.0, 0.3, 0.0), (7.0, 0.2, 90.0)])
    tracks = {f"member {j}": {n: beat().at(j, n) for n in range(1, 151)} for j in (0, 1)}
    x = flicker.curves(beat(), tracks, list(range(1, 151)), procs=0)
    y = flicker.curves(beat(), tracks, list(range(1, 151)), procs=3)
    check(repr(x) == repr(y) and len(x) == 2 + len(flicker.BACKGROUND), "flicker: the same brightness in every aperture",
          f"{len(x)} apertures")
    ns = sorted(track)
    for cache in (True, False):
        here, there = (tether.Frames(_Flock("rigid"), masks, track, 60, cache=cache, procs=p) for p in (0, 3))
        same = True
        for _ in range(2):                                   # the first pass reads; the second reads again, or what was kept
            for (n, g, bad), (m, h, bad2) in zip(here.each(ns), there.each(ns)):
                same &= n == m and np.array_equal(g, h) and np.array_equal(bad, bad2) and g.dtype == h.dtype
        check(same, f"tether: the same frames and masks on both passes, {'kept' if cache else 'read again'} between them")


def test_layers_second_pass_shared_out_is_the_same():
    """2026-10-09: a held-still window's second pass is many seconds, and a still scene has few windows
    (four on PR113, so all but four workers waited). Its rows of templates are shared among the workers
    now, and the field joined before it is judged -- zero shift allowed where the window is held still,
    or where with zero left out under a fifth of its templates are good -- as `shift_field_auto` judges
    the whole: the same rows as `_again`'s, to the bit, for a drifting scene, a still one, and one
    whose templates find nothing with zero left out (frames of noise)."""
    print("\nlayers: a second pass shared among workers is the window's own")
    from scipy import ndimage
    from mcdonald import layers
    h, w = 480, 720
    scene = isotropic(h + 80, w + 80, scale=4.0)
    pattern = RNG.normal(0, 1, (h, w)) * 6 + np.tile(RNG.normal(0, 1, w) * 4, (h, 1))

    class Drawn:
        H, W, n0, n1, fps = h, w, 1, 40, 30.0
        v, noise = (0.0, 0.0), False

        def rgb(self, n):
            if self.noise:
                g = np.random.default_rng(n).normal(128, 30, (h, w))
            else:
                g = ndimage.shift(scene, (self.v[1] * n, self.v[0] * n), order=3)[40:40 + h, 40:40 + w] * 0.15 + pattern
            return np.repeat(g[:, :, None], 3, 2)

    none = np.zeros((h, w), bool)
    for v, noise, name in (((-0.30, -0.14), False, "a drifting scene"), ((0.0, 0.0), False, "a still one"),
                           ((0.0, 0.0), True, "frames of noise")):
        clip = Drawn()
        clip.v, clip.noise = v, noise
        layers._G.clear()
        layers._G.update(clip=clip, masks=dict(blocks=none, graphics=none, colour=True), rows=None, k=5, reach=245,
                         pos=None, longer=30)
        ref = layers._again(1)
        got = layers.second_pass(None, [1], h, 5, 30, parts=3)[0]
        check(np.array_equal(ref[0], got[0]) and ref[1] == got[1], f"{name}: the window's rows, in three parts",
              f"{len(ref[0])} rows, {'still' if ref[1] else 'moved'}")


class _Gained(_Beating):
    """_Beating's points on a textured background (so that an aperture's contrast over its ring is not nothing), with
    the whole frame's brightness -- texture, grain, points and all -- swinging by `share` at `hz`: a camera's gain
    changing, or a display's brightness as a phone films it. Every aperture carries it at once."""

    def __init__(self, beats, hz, share, v=(0.37, 0.21)):
        super().__init__(beats, v)
        self.gain = (hz, share)
        from scipy import ndimage
        t = ndimage.gaussian_filter(np.random.default_rng(7).normal(0, 1, (self.H, self.W)), 6.0)
        self.texture = 4 * t / t.std()                        # 4 grey levels rms of cloud-like texture, so an aperture has contrast

    def rgb(self, n):
        if n not in self.cache:
            g = 60 + self.texture + np.random.default_rng(n).normal(0, 2, (self.H, self.W))
            yy, xx = np.mgrid[-7:8, -7:8]
            for j, (hz, share, ph) in enumerate(self.beats):
                x, y = self.at(j, n)
                xi, yi = int(round(x)), int(round(y))
                a = 120 * (1 + share * np.sin(2 * np.pi * hz * n / self.fps + np.radians(ph)))
                g[yi - 7:yi + 8, xi - 7:xi + 8] += a * np.exp(-((xx - (x - xi)) ** 2 + (yy - (y - yi)) ** 2) / 2.0)
            gh, gs = self.gain
            g = g * (1 + gs * np.sin(2 * np.pi * gh * n / self.fps))
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


def test_the_lomb_scargle_periodogram_and_its_false_alarm_probability():
    """The astronomer's tests (2026-10-15, item 7 of the flicker docstring): the strongest beat again by the Lomb-Scargle
    periodogram, which takes the samples it is given and no others -- a held picture or a lost frame is a missing sample
    -- with Baluev's false-alarm probability and the sampling's own rhythms read off its spectral window. The numbers are
    astropy's (checked against its exact method where astropy is installed); on every frame of an even cadence the peak
    is where the Hann spectrum's is, with no line of the sampling; a clip holding every picture three frames keeps a
    third of its frames as samples, and its window has a line at a third of the frame rate."""
    print("\nflicker: the Lomb-Scargle periodogram, its false-alarm probability and the sampling's own rhythm")
    from mcdonald import flicker
    say = lambda *a: None
    rng = np.random.default_rng(5)
    t = np.sort(rng.uniform(0, 5, 120))
    y = 0.3 * np.sin(2 * np.pi * 4.2 * t) + rng.normal(0, 0.5, 120)
    freqs = np.linspace(0.5, 12, 3000)
    P = flicker.lombscargle(t, y, freqs)
    k = int(np.argmax(P))
    fap = flicker.fap_baluev(P[k], t, 0.0, 12.0)
    check(abs(freqs[k] - 4.2) < 0.1 and fap < 0.05, "120 uneven samples of a 4.2-Hz sinusoid in noise: the peak at 4.2 Hz, "
          "unlikely by chance", f"{freqs[k]:.2f} Hz, power {P[k]:.2f}, FAP {fap:.2e}")
    try:
        from astropy.timeseries import LombScargle
    except ImportError:
        LombScargle = None
    if LombScargle is not None:
        ls = LombScargle(t, y)
        Pa = ls.power(freqs, normalization="standard", method="slow")
        fa = float(ls.false_alarm_probability(P[k], method="baluev", maximum_frequency=12.0))
        check(float(np.max(np.abs(P - Pa))) < 1e-9 and abs(fap - fa) <= 1e-3 * fa,
              "the same numbers as astropy's exact method and its Baluev false-alarm probability over the same band",
              f"power differs by {float(np.max(np.abs(P - Pa))):.1e}; FAP {fap:.6e} against {fa:.6e}")
    else:
        print("  SKIP  astropy is not installed: the periodogram is not checked against it")
    W = flicker.window(np.arange(0, 150, 3) / 30.0, np.array([5.0, 10.0, 15.0]))
    check(W[1] > 0.99 and W[0] < 0.01 and W[2] < 0.01, "every third frame of 30 a second: the window is 1 at 10 Hz, nought at 5 and 15",
          str(W.round(3)))
    one = _Beating([(8.0, 0.2, 0)])
    f = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=say).fields
    p, ls_ = f["curves"]["member 0"], f["astro"]["member 0"]["lombscargle"]
    check(abs(ls_["hz"] - p["hz"]) <= p["resolution_hz"] and ls_["fap"] < 1e-6 and ls_["dropped"] == 0 and not ls_["window_lines_hz"]
          and ls_["at_a_window_line"] is False,
          "an 8-Hz beat on every frame: the Lomb-Scargle peak is the spectrum's, its false-alarm probability under a millionth, "
          "no frame left out and no line of the sampling", f"{ls_['hz']:.2f} Hz, FAP {ls_['fap']:.1e}, kept {ls_['kept']}")
    rng = np.random.default_rng(34)
    level = np.repeat(1 + 0.2 * rng.normal(size=60), 3)[:152]
    held = _Held(np.r_[level[:1], level], hold=3, width=1.5)
    g = flicker.measure(held, {"object": {n: held.at(0, n) for n in range(1, 151)}}, say=say).fields
    ls_ = g["astro"]["object"]["lombscargle"]
    check(ls_["dropped"] >= 90 and ls_["kept"] <= 60 and any(abs(L - held.fps / 3) < 0.3 for L in ls_["window_lines_hz"]),
          "every picture held three frames: two frames in three are missing samples, and the sampling's rhythm, a third of "
          "the frame rate, is a line of its window", f"kept {ls_['kept']}, dropped {ls_['dropped']}, lines {[round(v, 1) for v in ls_['window_lines_hz']]}")
    flicker.GATE_ASTRO, p_max = True, flicker.P_MAX
    try:
        h = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=say).fields
        flicker.P_MAX = 0.0                                   # no scrambled copy may stand as high: 1 in 201 always does
        i = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=say).fields
    finally:
        flicker.GATE_ASTRO, flicker.P_MAX = False, p_max
    check(h["beats"] is True and h["strong"] == ["member 0"] and i["beats"] is False and i["strong"] == []
          and "astronomer's tests" in (i.get("finding") or "") and "scrambled" in (i.get("finding") or ""),
          "with GATE_ASTRO the tests decide as well: the beat stands at P_MAX 0.01 and falls at a P_MAX of nought, and the "
          "finding says which test; off by default, they report", f"{h['beats']} / {i['beats']}: {str(i.get('finding'))[:90]}")


def test_a_beat_stands_over_its_scrambled_copies_and_a_constant_does_not():
    """The curve's strongest held against copies of itself scrambled in chunks (Kepler's scrambled runs; Theiler's
    surrogates): the chunks keep the grain, the codec and the frame-to-frame jitter and their order destroys every
    rhythm. An 8-Hz beat stands over 99 in 100 of its copies; a constant point's strongest does not."""
    print("\nflicker: a beat stands over its scrambled copies")
    from mcdonald import flicker
    say = lambda *a: None
    one = _Beating([(8.0, 0.2, 0)])
    f = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=say).fields
    sc = f["astro"]["member 0"]["scramble"]
    check(sc["p"] <= 0.01 and sc["stands"] > sc["needed"] and sc["runs"] == flicker.SCRAMBLES and sc["valid_above_hz"] > flicker.LOW,
          "an 8-Hz beat: under 1 in 100 of its scrambled copies stand as high", f"p {sc['p']:.3f}, {sc['stands']:.0f}x against {sc['needed']:.0f}x needed")
    still = _Beating([(0, 0, 0)])
    g = flicker.measure(still, {"member 0": {n: still.at(0, n) for n in range(1, 151)}}, say=say).fields
    sc = g["astro"]["member 0"]["scramble"]
    check(sc["p"] > 0.05, "a constant point: its strongest is what the grain makes, as the copies do", f"p {sc['p']:.3f}")
    rng = np.random.default_rng(11)
    ps = [flicker.scrambled(rng.normal(0, 1, 150), 30.0)["p"] for _ in range(12)]
    check(min(ps) > 0.005 and max(ps) > 0.2, "on curves of grain alone the chance is spread, not small",
          ", ".join(f"{p:.2f}" for p in ps))


def test_a_gain_the_whole_frame_shares_is_the_backgrounds_common_mode():
    """A camera's gain changing, or a display's brightness as a phone films it, is in every aperture at once: the first
    components of the background apertures' curves (SysRem/TFA), regressed out of the object's, take it with them
    and leave a beat the background does not share alone. The pixel phase, likewise regressed, accounts for little of
    a point measured through the disc aperture."""
    print("\nflicker: the background's common mode, and the pixel phase")
    from mcdonald import flicker
    say = lambda *a: None
    gained = _Gained([(0, 0, 0)], 7.0, 0.25)
    found = flicker.measure(gained, {"member 0": {n: gained.at(0, n) for n in range(1, 151)}}, say=say)
    f = found.fields
    cm = f["astro"]["member 0"]["common_mode"]
    check(cm is not None and cm["r2"] >= 0.5 and cm["r2_scene"] >= 0.5 and cm["after_amplitude"] < 0.5 * cm["before_amplitude"],
          "the whole frame swinging 25% at 7 Hz: the scene's level and contrast account for over half the point's curve, "
          "and without them the point's beat is less than half", f"r2 {cm['r2']:.2f} (scene {cm['r2_scene']:.2f}), "
          f"{cm['before_amplitude']:.1%} -> {cm['after_amplitude']:.1%}" if cm else "no common mode")
    check(f["beats"] is True and any("astronomer's checks disagree" in n and "common mode" in n for n in found.notes),
          "the stage's own tests still call it the object's (the apertures beside it carry the gain only as their own contrast, "
          "in either sign), and the notes say the astronomer's checks disagree", "; ".join(n[:80] for n in found.notes if "disagree" in n))
    one = _Beating([(8.0, 0.2, 0)])
    g = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=say).fields
    cm, pp = g["astro"]["member 0"]["common_mode"], g["astro"]["member 0"]["pixel_phase"]
    check(cm["r2"] < 0.2 and cm["r2_scene"] < 0.2 and cm["after_amplitude"] > 0.8 * cm["before_amplitude"] and abs(cm["after_hz"] - 8.0) < 0.3,
          "a beat the scene and the background do not share loses next to nothing to them", f"r2 {cm['r2']:.2f}, {cm['before_amplitude']:.1%} -> {cm['after_amplitude']:.1%}")
    check(pp["r2"] < 0.2 and abs(pp["after_hz"] - 8.0) < 0.3, "and the pixel phase accounts for little of it", f"r2 {pp['r2']:.2f}")


def test_the_fold_puts_the_beat_where_it_is():
    """The frames folded on the beat (epoch folding; Kepler's difference image): the bright half of the cycle less
    the dim half shows where the brightness that beats is. A point's beat sits in the aperture, at the object, and the
    rest of the frame does not change; a gain the whole frame shares changes the whole frame. The fold is drawn with
    the beat figure."""
    print("\nflicker: the fold puts the beat where it is")
    from mcdonald import flicker
    say = lambda *a: None
    one = _Beating([(8.0, 0.2, 0)])
    with tempfile.TemporaryDirectory() as td:
        found = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=say, out=f"{td}/one")
        fo = found.fields["fold"]["member 0"]
        png = Path(f"{td}/one_fold.png")
        check(fo["concentration"] > 3 and fo["offset_px"] <= 2 and abs(fo["amplitude"] - 0.2 * 2 / np.pi) < 0.04
              and abs(fo["controls_amplitude"]) < 0.02 and fo["bright_frames"] + fo["dim_frames"] == 150,
              "an 8-Hz beat of 20%: the bright half stands 2/pi of it over the dim, the background beside it does not, and the "
              "difference picture is concentrated in the aperture, at the object",
              f"amplitude {fo['amplitude']:.1%} (background {fo['controls_amplitude']:.1%}), {fo['in_aperture_share']:.0%} in the "
              f"aperture ({fo['concentration']:.1f}x), {fo['offset_px']:.1f} px off")
        check(png.exists() and png.stat().st_size > 20000 and any(Path(f) == png for f in found.files),
              "and the fold is drawn, <case>_fold.png, listed with the stage's files", f"{png.stat().st_size if png.exists() else 0} bytes")
    gained = _Gained([(0, 0, 0)], 7.0, 0.25)
    g = flicker.measure(gained, {"member 0": {n: gained.at(0, n) for n in range(1, 151)}}, say=say).fields
    fg = g["fold"]["member 0"]
    check(fg["scene_rms"] > 5 * fo["scene_rms"], "the whole frame swinging 25%: the rest of the frame changes with the beat, "
          "which a point's own beat leaves alone", f"{fg['scene_rms']:.2f} against {fo['scene_rms']:.2f} levels rms")


def test_the_background_apertures_are_judged_and_planted_beats_recovered():
    """Data known to hold no object through the object's own tests (the Robovetter's inverted and scrambled runs), and
    beats planted in it and recovered (injection and recovery): the background apertures beside a point are judged as
    the object is -- none passes -- and a beat planted in them at 20% of the object's brightness is recovered at every
    frequency, at 2% not. `nulls` runs the slower of these; without it the windows and the planting are left out."""
    print("\nflicker: the background apertures judged, and planted beats recovered")
    from mcdonald import flicker
    say = lambda *a: None
    one = _Beating([(8.0, 0.2, 0)])
    f = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=say, nulls=True).fields
    far, ctrl = f["false_alarm"], f["controls"]
    check(far["whole"] == [0, 4] and far["windows"][1] >= 40 and far["windows"][0] <= 0.1 * far["windows"][1]
          and len(ctrl) == 4 and all(c["passes"] is False for c in ctrl.values()),
          "none of the four background apertures passes the object's tests over the whole track, and few of their windows do",
          f"whole {far['whole']}, windows {far['windows']}")
    inj = f["injection"]
    rec = np.array(inj["recovered"])
    check(inj["trials"] == 4 and rec.shape == (len(flicker.INJECT_AMPL), flicker.INJECT_N) and rec[-1].min() >= 0.75
          and rec[0].mean() <= rec[-1].mean() and inj["complete_from"] is not None and inj["complete_from"] <= 0.2,
          "a beat planted at 20% is recovered at every frequency, at 2% less often, and the stage says from what amplitude it is complete",
          f"recovered {inj['recovered']}, complete from {inj['complete_from']}, at {inj['hz']} Hz")
    an = inj.get("analytic") or {}
    check(an.get("with_floor") is not None and inj["complete_from"] is not None and 0.3 <= inj["complete_from"] / an["with_floor"] <= 4,
          "and the amplitude it is complete from, in closed form from the apertures' own noise (D6), is within a small factor of it",
          f"planted {inj['complete_from']}, closed form {an.get('with_floor')}")
    g = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=say).fields
    check("injection" not in g and all(c["windows"] is None for c in g["controls"].values()) and g["false_alarm"]["whole"] == [0, 4],
          "without `nulls` the background apertures are still judged over the whole track, their windows and the planting left out",
          str(g["false_alarm"]))
    lines = flicker.said(f)
    check(sum("Lomb-Scargle" in L for L in lines) == 1 and any("scrambled" in L for L in lines) and any("common mode" in L for L in lines)
          and any("planted" in L for L in lines) and any("folded on" in L for L in lines) and any("through the object's own tests" in L for L in lines),
          "and `mcdonald flicker` says each of them", "\n".join(L[:70] for L in lines if "Lomb" in L or "planted" in L))


def test_the_multitaper_line_test_coherence_and_the_noise_as_a_distribution():
    """The seismologist's tests (2026-10-15, item 8 of the flicker docstring): Thomson's harmonic F-test on the multitaper
    spectrum -- the chance of a line at the beat against a continuum smooth over the tapers' bandwidth -- calibrated on
    grain (1 in 100 frequencies under 0.01); the coherence of the object's curve with each background aperture's and
    with the frame's own level and contrast, with the level chance clears; the background windows' spectra as a
    distribution and the centile the object's windows sit at; the one-bit reading; and GATE_SEIS, off by default."""
    print("\nflicker: the multitaper F-test, coherence with what is not the object, the noise as a distribution, one bit")
    from mcdonald import flicker
    say = lambda *a: None
    rng = np.random.default_rng(3)
    share = []
    for _ in range(50):
        M = flicker.multitaper(rng.normal(0, 1, 150), 30.0)
        band = (M["fr"] >= flicker.LOW) & (M["fr"] <= 12.0)
        share.append(float(np.mean(M["p"][band] < 0.01)))
    check(0.003 <= float(np.mean(share)) <= 0.03, "on grain alone the F-test calls a line at 1 in 100 frequencies, as its chance says",
          f"{float(np.mean(share)):.4f} of the band under 0.01")
    one = _Beating([(8.0, 0.2, 0)])
    found = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=say)
    f = found.fields
    S = f["seis"]["member 0"]
    ln, ob, nz, co = S["line"], S["onebit"], S["noise"], S["coherence"]
    check(ln["p"] < 1e-5 and ln["p_band"] < 1e-3 and abs(ln["hz"] - 8.0) <= 0.3 and 0.15 <= ln["amplitude"] <= 0.25
          and any(abs(q["hz"] - 8.0) <= 0.3 for q in ln["lines"]) and ln["K"] == 4,
          "an 8-Hz beat of 20%: the F-test's chance of a line at it is under a hundred-thousandth, its amplitude read, and it is a line of the band",
          f"{ln['hz']:.2f} Hz, {ln['amplitude']:.1%}, F {ln['F']:.0f}, chance {ln['p']:.1e} ({ln['p_band']:.1e} in the band)")
    lw = S["line_windows"]
    check(lw["windows"] >= 5 and lw["share"] >= 0.5 and lw["best_p"] < 1e-3 and S["comb"] is None,
          "and in windows of 2 s along the track most have the line (the frequency given beforehand); one line is no comb",
          f"{lw['passing']} of {lw['windows']}, best chance {lw['best_p']:.1e}")
    check(ob["agrees"] and abs(ob["hz"] - 8.0) <= 0.3, "with every sample its sign alone the beat is where it was", f"{ob['hz']:.2f} Hz, {ob['stands']:.0f}x")
    check(nz["centile"] >= 99 and nz["share_over_99"] >= 0.75 and nz["windows"] >= 8,
          "its windows' amplitude at the beat sits above the background's own windows' 99th centile",
          f"{nz['object_amplitude']:.1%} at the {nz['centile']:.0f}th centile of {nz['windows']} windows (their 99th {nz['level99']:.1%})")
    bgs = [c for c in co if c.startswith("background")]
    check(len(bgs) == 4 and sum(co[c]["above"] for c in bgs) <= 1 and all(co[c]["looks"] >= 4 for c in bgs)
          and "scene level" in co and not co["scene level"]["above"],
          "a beat of its own is coherent with none of the background apertures, nor with the frame's level",
          ", ".join(f"{c.replace('background ', '')} {co[c]['gamma2']:.2f}" for c in co) + f" (chance clears {co[bgs[0]]['level']:.2f})")
    gained = _Gained([(0, 0, 0)], 7.0, 0.25)
    g = flicker.measure(gained, {"member 0": {n: gained.at(0, n) for n in range(1, 151)}}, say=say)
    co = g.fields["seis"]["member 0"]["coherence"]
    check(co["scene level"]["above"] and co["scene level"]["gamma2"] > 0.9 and co["scene contrast"]["above"]
          and any("seismologist's checks disagree" in n and "coherent" in n for n in g.notes),
          "the whole frame swinging 25% at 7 Hz: the point's beat is coherent with the frame's level and contrast, and the notes say so",
          f"level {co['scene level']['gamma2']:.2f}, contrast {co['scene contrast']['gamma2']:.2f}")
    lines = flicker.said(f)
    check(any("multitaper F-test" in L for L in lines) and any("one bit" in L for L in lines) and any("centile" in L for L in lines)
          and any("coherence at the beat" in L for L in lines) and any("by Sompi" in L for L in lines),
          "and `mcdonald flicker` says each of them", "\n".join(L[:72] for L in lines if "multitaper" in L or "centile" in L))
    flicker.GATE_SEIS, p_max = True, flicker.MT_P
    try:
        h = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=say).fields
        flicker.MT_P = 0.0
        i = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=say).fields
    finally:
        flicker.GATE_SEIS, flicker.MT_P = False, p_max
    check(h["beats"] is True and h["strong"] == ["member 0"] and i["beats"] is False and i["strong"] == []
          and "seismologist's line test" in (i.get("finding") or "") and "windows" in (i.get("finding") or ""),
          "with GATE_SEIS the line test decides as well: the beat stands at MT_P 0.01 and falls at an MT_P of nought, and the "
          "finding says so; off by default, it reports", f"{h['beats']} / {i['beats']}: {str(i.get('finding'))[:90]}")


def test_sompi_reads_a_line_from_a_few_cycles_and_a_short_record_is_read_anyway():
    """The Sompi method (Hori et al. 1989): the record as a linear system's output, whose roots that hold still across
    model orders are its lines, a frequency and a decay each -- a planted 3-Hz line decaying with Q 20 is read from 40
    frames, grain alone gives no line -- and with it a track too short for the stage's spectrum is read anyway: the
    stage still says it is too short, and the short-record reading is in the fields and the notes, a reading and not
    a beat; a brief member beside a long one likewise."""
    print("\nflicker: Sompi on a few cycles, and the short record read anyway")
    from mcdonald import flicker
    say = lambda *a: None
    rng = np.random.default_rng(1)
    t = np.arange(40) / 30.0
    y = 0.2 * np.exp(-np.pi * 3.0 / 20 * t) * np.cos(2 * np.pi * 3.0 * t + 0.7) + rng.normal(0, 0.04, 40)
    so = flicker.sompi(y, 30.0, top=12)
    check(so["hz"] is not None and abs(so["hz"] - 3.0) <= 0.15 and so["q"] is not None and 8 <= so["q"] <= 60 and so["stability"] >= 0.7
          and so["over"] >= 1.0, "a 3-Hz line decaying with Q 20, in grain, over 40 frames: read, with its decay",
          f"{so['hz']:.2f} Hz, Q {so['q']:.0f}, {so['amplitude']:.2f} over {so['over']:.1f}x the grain, still at {so['stability']:.0%} of the orders" if so["hz"] else "no line")
    none = sum(flicker.sompi(rng.normal(0, 1, 40), 30.0, top=12)["hz"] is None for _ in range(20))
    check(none >= 18, "grain alone: no root holds still and stands over the grain", f"no line in {none} of 20")
    sh = _Brief([(8.0, 0.2, 0)])
    found = flicker.measure(sh, {"member 0": {n: sh.at(0, n) for n in range(1, 41)}}, say=say)
    sr = (found.fields.get("short_record") or {}).get("member 0") or {}
    check(found.fields["beats"] is None and found.no_power == [("flicker", "40 frames, under the 60 a beat needs")]
          and sr.get("sompi", {}).get("hz") is not None and abs(sr["sompi"]["hz"] - 8.0) <= 0.3 and abs(sr["peak"]["hz"] - 8.0) <= 0.5
          and sr["frames"] == [1, 40] and any("read anyway" in n and "A reading, not a beat" in n for n in found.notes),
          "a 40-frame track: too short for a beat as before, and read anyway -- an 8-Hz line in the fields and the notes",
          f"{found.no_power}; Sompi {sr.get('sompi', {}).get('hz')}; {found.notes[0][:90] if found.notes else 'no note'}")
    two = _Beating([(8.0, 0.2, 0), (8.0, 0.2, 90)])
    g = flicker.measure(two, {"member 0": {n: two.at(0, n) for n in range(1, 151)}, "member 1": {n: two.at(1, n) for n in range(1, 41)}}, say=say).fields
    sr = (g.get("short_record") or {}).get("member 1") or {}
    check(g["short"] == ["member 1"] and sr.get("sompi", {}).get("hz") is not None and abs(sr["sompi"]["hz"] - 8.0) <= 0.3
          and g["beats"] is True and any("read anyway" in L for L in flicker.said(g)),
          "a member seen 40 frames beside one seen 150: too brief for a beat, read anyway, and said",
          f"short {g['short']}, Sompi {sr.get('sompi', {}).get('hz')}")


def test_the_comb_and_the_glide():
    """A wingbeat is harmonic tremor: its lines sit at multiples of one fundamental and move together. The multitaper's
    lines read as a comb give the fundamental where the stage's `harmonics` picks between two peaks (`comb`), and the
    fundamental followed along the whole track with its double (`glide`) shows a rate that settles -- _Flyer's, from
    4.8 to 3.9 Hz over its approach, the double stronger -- where a steady beat shows none and a constant point
    nothing that stands."""
    print("\nflicker: the comb, and the fundamental followed along the track")
    from mcdonald import flicker
    say = lambda *a: None
    fl = _Flyer()
    f = flicker.measure(fl, {"object": {n: fl.at(0, n) for n in range(1, 211)}}, say=say).fields
    S = f["seis"]["object"]
    cb, gl = S["comb"], S["glide"]
    check(cb is not None and abs(cb["fundamental_hz"] - 3.9) <= 0.3 and cb["n_lines"] == 2 and cb["missing"] == 0 and cb["agrees"],
          "the flyer's lines, 3.9 and 7.8 Hz, are one comb with the fundamental at 3.9 -- the stage's beat, read from the comb as a whole",
          f"{cb}" if cb else "no comb")
    check(gl["frames"] == [1, 210] and gl["slope_hz_per_s"] is not None and gl["slope_hz_per_s"] < -0.03 and gl["start_hz"] - gl["end_hz"] >= 0.4
          and gl["r2"] >= 0.3 and gl["windows"] >= 40,
          "its fundamental followed over the whole track settles from about 4.6 to 3.9 Hz: a glide, as drawn",
          f"{gl['start_hz']:.2f} -> {gl['end_hz']:.2f} Hz, {gl['slope_hz_per_s']:+.2f} Hz/s, r2 {gl['r2']:.2f}, {sum(gl['stands'])} of {gl['windows']} windows stand")
    one = _Beating([(8.0, 0.2, 0)])
    g = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=say).fields
    gl = g["seis"]["member 0"]["glide"]
    check(gl["slope_hz_per_s"] is not None and abs(gl["slope_hz_per_s"]) < 0.1 and gl["range_hz"] < 0.5 and sum(gl["stands"]) >= 0.6 * gl["windows"],
          "a steady 8-Hz beat: followed, it holds within half a hertz, standing in nearly every window",
          f"{gl['start_hz']:.2f} -> {gl['end_hz']:.2f}, {gl['slope_hz_per_s']:+.3f} Hz/s, {sum(gl['stands'])} of {gl['windows']}")
    still = _Beating([(0, 0, 0)])
    h = flicker.measure(still, {"member 0": {n: still.at(0, n) for n in range(1, 151)}}, say=say).fields
    gl, cb = h["seis"]["member 0"]["glide"], h["seis"]["member 0"]["comb"]
    check(gl["slope_hz_per_s"] is None and sum(gl["stands"]) <= 0.15 * gl["windows"] and cb is None,
          "a constant point: nothing stands in its windows, so nothing is followed, and there is no comb",
          f"{sum(gl['stands'])} of {gl['windows']} windows stand; comb {cb}")


def test_members_in_step_by_their_phases_and_the_phase_map():
    """Members' phases held together (the phase-weighted stack's coherence, Schimmel & Paulssen 1997; the array
    F-statistic, Blandford 1974): two points beating in step are coherent, with a shared component past chance; two
    opposite, or at different rates, are not. And the same by pixel beside the fold: a point's own beat is coherent
    within the aperture and not outside it; a gain the whole frame shares everywhere. The noise figure is drawn."""
    print("\nflicker: members in step by their phases, and the beat's place by phase")
    from mcdonald import flicker
    say = lambda *a: None
    def two(ph, hz2=8.0):
        c = _Beating([(8.0, 0.2, 0), (hz2, 0.2, ph)])
        return flicker.measure(c, {f"member {j}": {n: c.at(j, n) for n in range(1, 151)} for j in range(2)}, say=say).fields
    a, b, d = two(0), two(180), two(0, 6.0)
    sa, sb, sd = a["in_step"], b["in_step"], d["in_step"]
    check(sa and sa["R"] > 0.9 and sa["p_F"] < 1e-4 and sa["n"] == 2 and abs(sa["hz"] - 8.0) <= 0.3,
          "two points beating in step: phase coherence near 1, the array F past chance", f"R {sa['R']:.2f}, F {sa['F']:.0f}, chance {sa['p_F']:.1e}" if sa else "none")
    check(sb and sb["R"] < 0.2 and sb["p_F"] > 0.5 and sb["p_slides"] > 0.5, "two points opposite in phase: no coherence, no shared component",
          f"R {sb['R']:.2f}, F {sb['F']:.2f}, chance {sb['p_F']:.2f}, slides {sb['p_slides']:.2f}" if sb else "none")
    check(sd and sd["R"] < 0.75 and sd["p_F"] > 0.1, "two points at 8 and 6 Hz: no shared component at the frequency between",
          f"R {sd['R']:.2f}, F {sd['F']:.2f}, chance {sd['p_F']:.2f}" if sd else "none")
    one = _Beating([(8.0, 0.2, 0)])
    with tempfile.TemporaryDirectory() as td:
        found = flicker.measure(one, {"member 0": {n: one.at(0, n) for n in range(1, 151)}}, say=say, out=f"{td}/one")
        fo = found.fields["fold"]["member 0"]
        check(fo.get("phase_inside") is not None and fo["phase_inside"] > 0.6 and fo["phase_outside"] < 0.5
              and fo["phase_inside"] > fo["phase_outside"] + 0.2 and fo["phase_frames"] == 150,
              "a point's own beat is coherent with the aperture's curve within the aperture and not beyond twice it",
              f"{fo.get('phase_inside', 0):.2f} in, {fo.get('phase_outside', 0):.2f} out")
        fold_png, noise_png = Path(f"{td}/one_fold.png"), Path(f"{td}/one_noise.png")
        check(fold_png.exists() and noise_png.exists() and noise_png.stat().st_size > 20000 and any(Path(x) == noise_png for x in found.files),
              "the fold is drawn with its phase column, and the noise figure, <case>_noise.png, listed with the stage's files",
              f"fold {fold_png.stat().st_size if fold_png.exists() else 0} bytes, noise {noise_png.stat().st_size if noise_png.exists() else 0}")
    gained = _Gained([(0, 0, 0)], 7.0, 0.25)
    g = flicker.measure(gained, {"member 0": {n: gained.at(0, n) for n in range(1, 151)}}, say=say).fields
    fg = g["fold"]["member 0"]
    check(fg.get("phase_outside") is not None and fg["phase_outside"] > 0.9, "the whole frame swinging 25%: coherent everywhere",
          f"{fg.get('phase_inside', 0):.2f} in, {fg.get('phase_outside', 0):.2f} out")
    lines = flicker.said(a)
    check(any("in step at" in L and "phase coherence" in L for L in lines), "and `mcdonald flicker` says whether the members are in step",
          next((L[:90] for L in lines if "in step at" in L), ""))


def test_a_box_mask_keeps_mid_picture_graphics_from_holding_the_scene():
    """AARO Puerto Rico 2013 (2026-10-20): a display's tape, arrow and reticle sit in the picture's middle band, which
    whole-row masks cannot take out without the scene; left in, their templates read zero shift and held 60 % of the
    pairs there. A box mask (`parse_boxes`, `layers --mask-box`) takes out the graphics and keeps the rows."""
    print("\nlayers: graphics drawn in place mid-picture, masked by boxes")
    rows = vf.parse_boxes(["100,50,300,350", "400,200,500,260:5:9"])
    check(rows == [(50, 350, 1, 10 ** 9, 100, 300), (200, 260, 5, 9, 400, 500)], "boxes parse to row entries with an x-range",
          f"{rows}")
    H, W, shift = 600, 1100, 9
    world = isotropic(H, W + 40) * 0.25 + 96                           # a faint scene, as a low-contrast thermal ground is
    a, b = world[:, 20:W + 20].copy(), world[:, 20 - shift:W + 20 - shift].copy()     # the scene moves right by `shift`
    drawn = np.random.default_rng(7).integers(0, 2, (H, W)).astype(bool)
    drawn = np.kron(drawn[::4, ::4], np.ones((4, 4), bool))[:H, :W]   # a high-contrast pattern drawn in place, not periodic
    box = (60, 60, 560, 540)                                           # x0, y0, x1, y1: about two fifths of the picture
    inside = np.zeros((H, W), bool)
    inside[box[1]:box[3], box[0]:box[2]] = True
    a[inside & drawn] = b[inside & drawn] = 250.0
    a[inside & ~drawn] = b[inside & ~drawn] = 10.0
    masks = {"blocks": np.zeros((H, W), bool), "graphics": np.zeros((H, W), bool), "colour": True}
    rgb = np.repeat(a[..., None], 3, 2).astype(np.uint8)
    got = {}
    for name, extra in (("none", []), ("box", vf.parse_boxes([f"{box[0] - 6},{box[1] - 6},{box[2] + 6},{box[3] + 6}"]))):
        bad = vf.frame_mask(rgb, masks, extra, n=1)
        f, _ = vf.shift_field_auto(a, b, bad, bad, reach=40, zero=-1)
        lay = vf.layers_of(f)
        got[name] = lay["all"][0][0] if lay["all"] else None
    check(got["none"] is not None and abs(got["none"]) < 2, "unmasked, the drawn pattern holds the consensus at zero",
          f"{got['none']}")
    check(got["box"] is not None and abs(got["box"] - shift) < 1, "box-masked, the scene's shift comes back",
          f"{got['box']} against {shift}")


def main():
    print("McDonald UAP Toolkit — measurement self-check")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{'ALL PASS' if not FAIL else str(len(FAIL)) + ' FAILED: ' + ', '.join(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):           # a pipe or a log file on Windows is cp1252, and the checks' names have arrows
        _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
