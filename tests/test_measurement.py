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


class SlowDisc(PlantedClip):
    """PR055's situation: a dark disc 24 px across that moves a pixel and a half a frame --
    less than its own width in the four frames the double difference spans."""
    P0, RADIUS, CONTRAST = (200.0, 120.0), 12.0, -150


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
        head = [ln for ln in open(path) if ln.startswith("#")]
        rows = [ln for ln in open(path) if not ln.startswith("#")]
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
                     "1,10.0,20.0\n2,12.0,23.0\n3,14.0,26.0\n")
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
    os.environ.pop("MCDONALD_CATALOG", None)
    cat = catalog.active()
    check(isinstance(cat, catalog.NullCatalog), "defaults to no catalog", cat.name)
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
            "document,\"A document\",06,no,\"text\",data/d.pdf\n")
        c = catalog.PursueCatalog(idx / "records.csv")
        check(len(c.videos()) == 2, "a PURSUE catalog reads only videos", f"{len(c.videos())} records")
        check(c.disclosure_rate() == (1, 2), "and counts disclosures", str(c.disclosure_rate()))
        rec = c.by_id("PR999")
        check(len(rec) == 1 and "digitally altered" in (c.disclosure(rec[0]) or ""),
              "and quotes the release's own sentence")
        catalog.use(None)


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
            "video,\"DOW-UAP-PR144, Three\",06,no,\"x\",data/c.mp4\n")
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


def _pid(x):
    import os
    return os.getpid()


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


def main():
    print("McDonald UAP Toolkit — measurement self-check")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{'ALL PASS' if not FAIL else str(len(FAIL)) + ' FAILED: ' + ', '.join(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
