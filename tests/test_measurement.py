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
            catalog.use(One(300_001))
            try:
                clipmod.resolve("PR999", fetch=fetch)
                said = None
            except clipmod.Stop as ex:
                said = str(ex)
            check(said and "could not be downloaded" in said and not path.exists() and not list(path.parent.glob("*.part")),
                  "a download that comes to less than the catalog says is not kept, whole or part", said)
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

        long = Reel(video, {**clip.info, "nb_frames": 260})   # a header that counts a sound track's length
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
