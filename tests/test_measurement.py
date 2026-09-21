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


class PlantedClip:
    """What the linker asks of a Clip -- n0, n1, W, H, fps, rgb(n), grey(n) -- with a
    disc on a known path, there on the frames in `seen`, and a brighter disc that
    never moves, for the linker to be tempted by. Module level, because it goes
    to the detector's processes by pickle."""
    W, H, n0, fps = 540, 300, 1, 30000 / 1001
    P0, RADIUS, DECOY = (80.0, 80.0), 9.0, (120.0, 230.0)

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
            g = g + 120 * (np.hypot(xx - x, yy - y) <= self.RADIUS)
        return g.astype(np.float32)

    def rgb(self, n):
        return np.repeat(self.grey(n)[..., None], 3, axis=2)


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
    check(L.arrivals.get(22, 0) is None and "does not reach the mark on 22" in L.say,
          "and it says the link from the mark before never reached that one, rather than joining them up")
    check(L.source[19] == "backward" and L.source[25] == "forward" and L.lost_at is None,
          "back from the new mark to where it came out, on from it to the end")
    check(len(cache) == 30 and ran < 30, "the detector ran on the new frames only", f"{ran} frames the first time, {len(cache)} in all")


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


def test_ffmpeg_is_checked_up_front():
    print("\npackaging: runtime dependencies")
    try:
        clipmod.require_ffmpeg()
        check(True, "ffmpeg and ffprobe are present")
    except clipmod.MissingTool as e:
        check(False, "ffmpeg and ffprobe are present", str(e))


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
    say("stage 5 of 9 · layers: frame pairs", 0, 4)
    say("stage 5 of 9 · layers: frame pairs", 2, 4)
    say("stage 6 of 9 · scale")
    lines = pipe.getvalue().splitlines()
    check(len(lines) == 4 and lines[0].endswith("stage 5 of 9 · layers: frame pairs") and lines[0].startswith("[")
          and "2 of 4" in lines[2] and lines[3].endswith("stage 6 of 9 · scale"),
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
