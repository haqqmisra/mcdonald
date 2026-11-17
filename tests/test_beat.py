"""Do the beat's readings beside the call say what they should -- and leave the call alone? (docs/method.md section 59)

Four readings of `mcdonald flicker` that report and never decide (2026-11-13; ROADMAP.md 0.3 objectives 4 and 5, IDEAS.md
K2, T2, E11 and the row "uap PR089"), each on drawn data with a known answer:

- **the beat in the position** (`beatpos`): a track drawn from a wander and jitter with no rhythm is given one about one
  time in a hundred; a planted wobble is found at its frequency; a bird that bobs as it beats agrees with its brightness,
  a lamp that only flashes does not; a camera's shake is in every member's track and in none of their differences, and
  it leaves a track taken against the registered scene; the codec's own rate is left out and said;
- **a line in a look-alike band** (`beatlines`): a 10.5-Hz line of 4.4 % behind a slow drift (the row's PR089) is found
  and the stage's call does not move; curves with no line give one about one time in a hundred; a line the background
  shares is not one;
- **the shape of a beat on a look-alike** (`beatshape`): a steady beat's depth does not "change", one that deepens along
  the track does; a blob whose brightness alone beats has no line in its width outside a fixed core, one whose width
  beats has, and a point has no power;
- **the look-alike mark's base rate** (`flicker.marked_share`): 70 % of the band at 30 frames a second, all of it at 60.

And one reading that decides (method section 69, 2026-11-17), held here because its scenes are these:

- **the track's own jitter** (`flicker.jitter_reading`): a steady, ragged cloud under a track that hops half a pixel is
  heard as a beat without the reading and given to the track with it; a spot that beats, and a bird whose track bobs
  with its wings, keep their beats; on drawn curves, a brightness made by where the aperture sits is the track's, and a
  beat beside an unrelated jitter is kept.

    python3 tests/test_beat.py        # or: pytest tests/

No video data needed.
"""
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcdonald import beatlines, beatpos, beatreadings, beatshape, flicker  # noqa: E402
import traffic  # noqa: E402 -- the binomial zone for checks on drawn data (E20)

FAIL = []
FPS = 30000 / 1001


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def wander(n, fps, rng, sill=3.0, range_s=1.0, jitter=0.3, v=(40.0, 15.0)):
    """A drawn track with no rhythm: a line, a Matérn-3/2 wander and white jitter a coordinate (`kriging.simulate`)."""
    from mcdonald import kriging
    t = np.arange(n) / fps
    xy = [v[c] * t + kriging.simulate(t, (sill ** 2, range_s, jitter ** 2), rng)[0] for c in (0, 1)]
    return np.arange(1, n + 1), xy[0], xy[1]


# ---- the beat in the position (K2) ---------------------------------------------------------------------------------
def test_a_track_with_no_rhythm_is_given_none():
    """The reading's false alarm on drawn tracks: its own null drawn afresh, and two it was not fitted to (jitter with a
    frame's memory, as a detector's has; a faster wander)."""
    print("\nthe beat in the position: tracks drawn with no rhythm")
    rng = np.random.default_rng(591)
    got = []
    for k in range(36):
        kind = k % 3
        f, x, y = wander(150, FPS, rng, sill=(3.0, 3.0, 1.0)[kind], range_s=(1.0, 1.0, 0.25)[kind])
        if kind == 1:                                       # the detector's memory: AR(1) at 0.4 on the jitter
            e = rng.standard_normal((150, 2)) * 0.3
            for i in range(1, 150):
                e[i] += 0.4 * e[i - 1]
            x, y = x + e[:, 0], y + e[:, 1]
        got.append(beatpos.reading(f, x, y, FPS, draws=300, hole=False))
    check(all(r["power"] for r in got), "every drawn track of 150 frames is read")
    traffic.rate(check, "a track drawn with no rhythm is given one about one time in a hundred (ALPHA)",
                 sum(r["line"] for r in got), len(got), beatpos.ALPHA, "p " + " ".join(f"{r['p']:.2f}" for r in got))
    short = beatpos.reading(*[a[:40] for a in wander(150, FPS, rng)], FPS)
    check(short["power"] is False and "under the 60" in short["why"], "40 frames are not read: NO POWER, and why", short["why"])


def test_a_planted_wobble_is_found_at_its_frequency():
    """A wobble of 0.4 px at 6.2 Hz in 0.3 px of jitter: found, at its frequency within its error, with its amplitude; the
    variogram's hole is beside it; and the same wobble read at a frequency given beforehand (`at_beat`)."""
    print("\nthe beat in the position: a planted wobble")
    rng = np.random.default_rng(592)
    found, near, amp, agree, holes = 0, 0, [], 0, 0
    runs = 10
    for k in range(runs):
        f, x, y = wander(150, FPS, rng)
        t = (f - 1) / FPS
        y = y + 0.4 * np.sin(2 * np.pi * 6.2 * t + rng.uniform(0, 6.28))
        r = beatpos.reading(f, x, y, FPS, beat=dict(hz=6.2, hz_err=0.03, double_hz=None), draws=300, hole=True)
        found += r["line"]
        near += abs(r["hz"] - 6.2) <= max(0.1, 3 * (r["hz_err"] or 0))
        amp.append(r["amplitude_px"][1])
        agree += bool(r["at_beat"] and r["at_beat"]["agrees"])
        holes += bool(r.get("hole") and r["hole"]["p"] < 0.05)
    traffic.rate(check, "a wobble of 0.4 px in 0.3 px of jitter is missed 5 % of the time at most (a judgement)", runs - found, runs, 0.05)
    check(near >= runs - 1, "at its frequency, within its error", f"{near} of {runs}")
    check(0.3 <= float(np.median(amp)) <= 0.5, "its amplitude read back", f"median {np.median(amp):.2f} px of 0.40 planted")
    check(agree >= runs - 1, "and read at the frequency given beforehand it agrees with it", f"{agree} of {runs}")
    print(f"        the variogram's hole beside it stood past 1 in 20 on {holes} of {runs}")
    f, x, y = wander(150, FPS, rng)
    r = beatpos.reading(f, x, y, FPS, beat=dict(hz=6.2, hz_err=0.03, double_hz=None), draws=300, hole=False)
    check(r["at_beat"] is not None and not r["at_beat"]["agrees"], "a track with no wobble does not agree with a beat it is given",
          f"chance {r['at_beat']['p']:.2f}")
    codec = wander(300, 60.0, rng, v=(18.0, 0.0))
    t = (codec[0] - 1) / 60.0
    x = codec[1] + 0.25 * np.sign(np.sin(2 * np.pi * 12.0 * t))            # a centroid that stops and starts at the GOP's rate
    r = beatpos.reading(codec[0], x, codec[2], 60.0, lines=[12.0, 24.0], draws=300, hole=False)
    check(r.get("codec") is not None and r["codec"]["line"] and abs(r["codec"]["hz"] - 12.0) < 0.1 and not r["line"],
          "a rhythm at the codec's own rate is the video's: said apart, and the track is given no rhythm for it",
          f"codec {r['codec']['hz']:.2f} Hz, {r['codec']['stands']:.0f} times; the track's own strongest {r['hz']:.2f} Hz, chance {r['p']:.2f}")
    y = codec[2] + 0.3 * np.sin(2 * np.pi * 3.4 * t)
    r = beatpos.reading(codec[0], x, y, 60.0, lines=[12.0, 24.0], draws=300, hole=False)
    check(r["line"] and abs(r["hz"] - 3.4) <= 0.15 and r["codec"]["line"],
          "and a wobble under it is found all the same, where the codec's rate is the stronger of the two",
          f"{r['hz']:.2f} Hz, chance {r['p']:.3f}; codec {r['codec']['stands']:.0f} times against its {r['stands']:.0f}")
    y = codec[2] + 0.3 * np.sin(2 * np.pi * 11.6 * t)
    r = beatpos.reading(codec[0], codec[1], y, 60.0, lines=[12.0, 24.0], draws=300, hole=False)
    check(r["line"] and abs(r["hz"] - 11.6) <= 0.1 and r.get("codec") is None,
          "a wobble 0.4 Hz from a codec line is not at it: a line has no width, and the wobble's frequency is known to less",
          f"{r['hz']:.2f} ± {r['hz_err']:.2f} Hz")
    # held pictures: a 20-a-second source on a 30-a-second grid. Every third frame repeats the one before, and the fresh
    # ones show the source a sixtieth of a second off the frames' own times by turns: a steady motion steps at 10 Hz
    k = np.arange(300)
    src = np.floor(k * 2 / 3)
    f, wx, wy = wander(300, 30.0, rng, sill=0.5, jitter=0.05, v=(0.0, 0.0))
    pick = (src * 1.5).astype(int)                           # the frame's own time the picture shown was taken at, in frames
    x, y = 27.0 * src / 20.0 + wx[pick], 9.0 * src / 20.0 + wy[pick]
    held = [int(n) for n in f[1:][src[1:] == src[:-1]]]
    step = beatpos.reading(f, x + 0.02 * rng.standard_normal(300), y + 0.02 * rng.standard_normal(300), 30.0, draws=300)
    r = beatpos.reading(f, x, y, 30.0, held=beatpos.still_held(f, np.c_[x, y], held), draws=300)
    check(len(held) == 100 and step["line"] and abs(step["hz"] - 10.0) < 0.2,
          "a steady motion on held pictures, every frame read as a sample: a \"rhythm\" at a third of the frame rate",
          f"{step['hz']:.2f} Hz, chance {step['p']:.3f}")
    check(not r["power"] and any(abs(v - 10.0) < 0.1 for v in r.get("sampling_lines_hz") or []) and "steady rate" in (r.get("why") or ""),
          "the held frames left out, the positions that are left keep the video's rhythm: the reading is not made, and says why",
          f"sampling lines {r.get('sampling_lines_hz')}; {r.get('why')}")
    b = beatpos.reading(f, x, y, 30.0, held=beatpos.still_held(f, np.c_[x, y], held), draws=300, beat=dict(hz=10.0, hz_err=0.03))
    check(not b["power"] and "at_beat" not in b,
          "nor at a brightness beat given beforehand: what moves at that rate is the video's",
          f"power {b['power']}")
    gap = np.ones(300, bool)
    gap[np.random.default_rng(3).choice(300, 60, replace=False)] = False
    check(beatpos.sampling_lines(gap, 30.0, 13.0) == [] and len(beatpos.sampling_lines(np.arange(300) % 5 != 4, 30.0, 13.0)) == 2,
          "frames missing at random keep no cadence; one held in five keeps two (6 and 12 Hz)",
          f"{beatpos.sampling_lines(gap, 30.0, 13.0)}; {beatpos.sampling_lines(np.arange(300) % 5 != 4, 30.0, 13.0)}")


class _Scene:
    """Points on a textured background that a camera shakes: every point and the texture move together `shake` px at
    `shake_hz`; each point is [(x, y, bob px, beat Hz, brightness share)] -- it rises and falls `bob` px at its beat, and its
    brightness beats there by `share`. At module level, as a class a process pool pickles must be."""
    n0, n1, W, H, fps = 1, 150, 320, 240, 30000 / 1001

    def __init__(self, points, shake=0.0, shake_hz=3.5, texture=True, sigma=1.2, contrast=60.0):
        self.points, self.shake, self.shake_hz, self.texture, self.sigma, self.cache = points, shake, shake_hz, texture, sigma, {}
        from scipy import ndimage
        self.back = ndimage.gaussian_filter(np.random.default_rng(5).normal(0, 1, (self.H, self.W)), 3.0) * contrast if texture else None

    def moved(self, n):
        return self.shake * np.sin(2 * np.pi * self.shake_hz * n / self.fps)

    def at(self, j, n):
        x, y, bob, hz, _ = self.points[j]
        return x + 0.31 * n + self.moved(n), y + 0.17 * n + bob * np.cos(2 * np.pi * hz * n / self.fps + j)     # a quarter cycle from its brightness

    def rgb(self, n):
        if n not in self.cache:
            g = 60 + np.random.default_rng(n).normal(0, 1.5, (self.H, self.W))
            if self.back is not None:
                from mcdonald.flicker import _fshift
                g = g + _fshift(self.back.astype(np.float32), 0.0, self.moved(n))
            yy, xx = np.mgrid[0:self.H, 0:self.W]
            for j, (_, _, _, hz, share) in enumerate(self.points):
                x, y = self.at(j, n)
                a = 120 * (1 + share * np.sin(2 * np.pi * hz * n / self.fps + j))
                g = g + a * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * self.sigma ** 2))
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


def _measure(clip, scene=False):
    tracks = {(f"member {j + 1}" if len(clip.points) > 1 else "object"): {n: clip.at(j, n) for n in range(clip.n0, clip.n1 + 1)}
              for j in range(len(clip.points))}
    return flicker.measure(clip, tracks, say=lambda *a: None, procs=0, scene=scene)


def test_the_stage_reads_a_bird_and_a_lamp():
    """Through `flicker.measure`: a point that bobs 0.5 px as its brightness beats carries its beat in its position, and
    the note says the camera's motion was not taken out; a point whose brightness alone beats does not; neither call
    moves."""
    print("\nthe beat in the position, through the stage: a bird and a lamp")
    bird = _measure(_Scene([(60.0, 80.0, 0.5, 6.3, 0.2)], texture=False))
    pb = (bird.fields.get("position_beat") or {}).get("object") or {}
    ab = pb.get("at_beat") or {}
    check(bird.fields["beats"] is True and pb.get("power") and ab.get("line") and ab.get("agrees") and pb["how"] == "picture"
          and pb["own"] is None, "a point that bobs as it beats: its position carries the beat, read as the picture has it",
          f"position {ab.get('position_hz')} Hz, chance {ab.get('p')}, beat {bird.fields['beat']['object']['hz']:.2f} Hz")
    note = next((m for m in bird.notes if m.startswith("Its position")), "")
    check("may be the camera's" in note and "position" in bird.result, "and the note says whose motion it is cannot be told", note[:200])
    wb = ab.get("without_brightness") or {}
    check(wb.get("beyond_background") is True and wb.get("line") is True,
          "it is more than a brightness beating over an uneven background gives, and still there with the brightness's share out",
          f"{wb.get('px_per_brightness', 0):.2f} px for a unit of brightness against {wb.get('reach_px')} within the background's reach; "
          f"{wb.get('share', 0):.0%} went with the brightness, chance {wb.get('p')} of the rest")
    lamp = _measure(_Scene([(60.0, 80.0, 0.0, 6.3, 0.2)], texture=False))
    pl = (lamp.fields.get("position_beat") or {}).get("object") or {}
    check(lamp.fields["beats"] is True and pl.get("power") and not (pl.get("at_beat") or {}).get("line"),
          "a point whose brightness alone beats: the beat is not in its position",
          next((m for m in lamp.notes if m.startswith("Its position")), "")[:200])
    # the trap: the same lamp over an uneven background. Its light and the background's are weighed together, so the
    # centroid leans toward the background as the lamp dims: a rhythm in the position with no motion at all
    over = _measure(_Scene([(60.0, 80.0, 0.0, 6.3, 0.3)], contrast=150.0))
    po = (over.fields.get("position_beat") or {}).get("object") or {}
    ao = po.get("at_beat") or {}
    wo = ao.get("without_brightness") or {}
    check(over.fields.get("beats") is True and po.get("power") and (not ao.get("line") or wo.get("beyond_background") is False)
          and po.get("own") is None,
          "the same lamp over an uneven background: the rhythm its position shows is no more than such a background gives, and is said so",
          f"beats {over.fields.get('beats')}; at the beat: line {ao.get('line')}, {np.hypot(*ao['amplitude_px']) if ao else 0:.3f} px, "
          f"{wo.get('px_per_brightness')} px for a unit of brightness; " + next((m for m in over.notes if m.startswith("Its position")), "")[-330:])


def test_a_cameras_shake_is_in_the_track_and_not_in_the_members_differences():
    """Three points on a camera that shakes 0.6 px at 3.5 Hz, each bobbing 0.5 px at its own beat. Alone, each track has the
    shake; against the other two, each has its own beat and the shake is gone."""
    print("\nthe beat in the position: a camera's shake, and members' differences")
    clip = _Scene([(60.0, 60.0, 0.5, 5.3, 0.2), (150.0, 110.0, 0.5, 6.6, 0.2), (230.0, 70.0, 0.5, 8.1, 0.2)], shake=0.6, texture=False)
    ns = list(range(clip.n0, clip.n1 + 1))
    moves = [{f"member {j + 1}": clip.at(j, n) for j in range(3)} for n in ns]
    rng = np.random.default_rng(593)
    for m in moves:                                        # a centroid's own jitter
        for k in m:
            m[k] = (m[k][0] + 0.1 * rng.standard_normal(), m[k][1] + 0.1 * rng.standard_normal())
    fields = dict(spans={f"member {j + 1}": (1, 150) for j in range(3)}, top_hz=12.0,
                  beat={f"member {j + 1}": dict(hz=hz, hz_err=0.03, double_hz=None) for j, hz in enumerate((5.3, 6.6, 8.1))})
    shake = dict(hz=3.5, hz_err=0.03, double_hz=None)
    alone = {k: beatpos.reading(ns, [m[k][0] for m in moves], [m[k][1] for m in moves], clip.fps, beat=shake, draws=300, hole=False)
             for k in moves[0]}
    check(all(r["at_beat"]["line"] and r["at_beat"]["at"] == "the beat" for r in alone.values()),
          "alone, every track carries the camera's 3.5 Hz", " ".join(f"{r['at_beat']['position_hz']:.2f} (chance {r['at_beat']['p']:.3f})" for r in alone.values()))
    # the stage's curves beside them: each member's brightness, beating a quarter cycle from its bob, and an even background
    raw = {f"member {j + 1}": [1000.0 * (1 + 0.2 * np.sin(2 * np.pi * hz * n / clip.fps + j)) for n in ns] for j, hz in enumerate((5.3, 6.6, 8.1))}
    raw.update({f"background {d}": list(10.0 * rng.standard_normal(len(ns))) for d in ("+0,+25", "+25,+0", "+0,-25", "-25,+0")})
    got = beatpos.of_stage(ns, clip.fps, moves, fields, raw=raw, draws=300)
    check(all(r["how"] == "members" and r["against"] == 2 for r in got.values()), "in a group each is read against the other two")
    check(all(r["at_beat"]["line"] and r["at_beat"]["agrees"] and r["own"] is True for r in got.values()),
          "against them each carries its own beat, more than its background could make of its brightness",
          " ".join(f"{r['at_beat']['position_hz']:.2f} (own {r['own']}, {(r['at_beat'].get('without_brightness') or {}).get('px_per_brightness')} "
                   f"against {(r['at_beat'].get('without_brightness') or {}).get('reach_px')})" for r in got.values()))
    bare = beatpos.of_stage(ns, clip.fps, moves, fields, draws=300)
    check(all(r["at_beat"]["line"] and r["own"] is None for r in bare.values()),
          "with no brightness to hold the rhythm against, it is found and not called the object's own")
    gone = beatpos.of_stage(ns, clip.fps, moves, dict(fields, beat={k: shake for k in fields["beat"]}), raw=raw, draws=300)
    check(all(not r["at_beat"]["line"] for r in gone.values()), "and the shake is gone from every one",
          " ".join(f"chance {r['at_beat']['p']:.2f}" for r in gone.values()))


def test_a_track_against_the_registered_scene():
    """Through `flicker.measure(scene=True)`: a point that only rides a camera shaking 0.6 px at 3.5 Hz over a textured
    scene, its brightness beating at 6.3 Hz. As the picture has it the track has the shake; against the registered scene
    it has no rhythm, and the reading says the scene's motion was taken out."""
    print("\nthe beat in the position: a track against the registered scene")
    clip = _Scene([(90.0, 100.0, 0.0, 6.3, 0.2)], shake=0.6)
    found = _measure(clip, scene=True)
    pb = (found.fields.get("position_beat") or {}).get("object") or {}
    sc = (found.fields.get("scene_shift") or {}).get("scene") or {}
    check(sc.get("power") and pb.get("how") == "scene", "the scene is registered, and the track is read against it",
          f"scene {sc}; how {pb.get('how')}; beats {found.fields.get('beats')}: {(found.fields.get('finding') or str(found.no_power))[:200]}")
    ns_ = list(range(clip.n0, clip.n1 + 1))
    shake = beatpos.of_stage(ns_, clip.fps, [{"object": clip.at(0, n)} for n in ns_],
                             dict(spans={"object": (clip.n0, clip.n1)}, top_hz=12.0, beat={"object": dict(hz=3.5, hz_err=0.03, double_hz=None)}),
                             draws=300)["object"]
    check(pb.get("power") and pb.get("own") is not True and abs(pb["hz"] - 3.5) > 0.3 and shake["at_beat"]["line"],
          "against the scene the camera's 3.5 Hz is gone, and nothing is called the object's own",
          f"own {pb.get('own')}; strongest {pb.get('hz')} Hz, chance {pb.get('p')}; " + next((m for m in found.notes if m.startswith("Its position")), "")[:260])
    ns = list(range(clip.n0, clip.n1 + 1))
    raw = beatpos.reading(ns, [clip.at(0, n)[0] for n in ns], [clip.at(0, n)[1] for n in ns], clip.fps, draws=300, hole=False)
    check(raw["line"] and abs(raw["hz"] - 3.5) <= 0.2, "as the picture has it, the same track carries the camera's 3.5 Hz",
          f"{raw['hz']:.2f} Hz, chance {raw['p']:.3f}")


# ---- a line in a look-alike band ------------------------------------------------------------------------------------
def _curves(rng, n=240, line=None, drift=0.08, grain=0.02, shared=False):
    """(the object's deviation curve, four background apertures') drawn: a slow wander at 1.5-3 Hz, grain, and `line` =
    (Hz, amplitude) in the object's (and, with `shared`, in the backgrounds')."""
    t = np.arange(n) / 30.0
    from scipy import ndimage

    def one(with_line):
        walk = np.cumsum(rng.standard_normal(n + 200))[200:]         # a wander: a random walk against its running mean
        slow = walk - ndimage.uniform_filter1d(walk, 15, mode="nearest")
        y = drift * slow / max(slow.std(), 1e-9) + grain * rng.standard_normal(n)
        if line and with_line:
            y = y + line[1] * np.sin(2 * np.pi * line[0] * t + rng.uniform(0, 6.28))
        return y - y.mean()
    return one(True), [one(shared) for _ in range(4)]


def test_a_line_behind_a_drift_is_found_in_its_band():
    """The IDEAS row's case drawn: 240 frames, a slow wander of 8 % at 1.5-3 Hz and a line of 4.4 % at 10.5 Hz. The
    strongest peak of the curve is the drift; the band search finds the line in the band that holds 10.5 Hz."""
    print("\na line in a look-alike band: behind a slow drift")
    rng = np.random.default_rng(594)
    table = flicker.lookalikes(30.0)
    found, where = 0, []
    for _ in range(10):
        r, R = _curves(rng, line=(10.5, 0.044), grain=0.01)
        got = beatlines.search(r, R, 30.0, table, 12.0, beat=dict(hz=2.1, double_hz=None, resolution_hz=0.125))     # the stage's beat: the drift's
        lines = [b for b in beatlines.lines_of(got) if not b["the_beat"]]
        found += bool(lines and abs(lines[0]["hz"] - 10.5) <= 0.15)
        where += [b["band"] for b in lines[:1]]
    traffic.rate(check, "a 4.4 % line at 10.5 Hz behind an 8 % drift, in grain of 1 %, is missed 5 % of the time at most (a judgement)",
                 10 - found, 10, 0.05, f"named by the band {sorted(set(where))}")
    r, R = _curves(rng, line=(10.5, 0.044), grain=0.01)
    got = beatlines.search(r, R, 30.0, table, 12.0)
    row = beatlines.lines_of(got)[0]
    check(0.03 <= row["amplitude"] <= 0.06 and row["p"] < beatlines.LINE_P and row["stands"] > max(row["background"]),
          "with its amplitude, its chance and the background apertures' own standing beside it",
          f"{row['amplitude']:.3f}, chance {row['p']:.2g}, {row['stands']:.0f} against {max(row['background']):.1f}")
    said = beatlines.said("object", got, calls=False)
    check(said and "which the background beside it does not show" in said and "does not call it a beat" in said, "said in the row's words", said)
    r, R = _curves(rng, line=(10.5, 0.044), grain=0.01, shared=True)
    got = beatlines.search(r, R, 30.0, table, 12.0)
    check(not beatlines.lines_of(got), "a line the background's apertures share is not the object's",
          str([(b["band"], round(b["stands"], 1), b["shared"]) for b in got["bands"]]))
    short = beatlines.search(r[:45], [b[:45] for b in R[:1]], 30.0, table, 12.0)
    check(short["power"] is False and "too short" in (short["why"] or ""), "too few background frequencies: NO POWER", str(short["why"]))


def test_curves_with_no_line_hold_none():
    """The search's false alarm, the band's width and the number of bands paid for: curves with a drift and grain and no
    line, the object's and four backgrounds', 240 frames and 90."""
    print("\na line in a look-alike band: curves with no line")
    rng = np.random.default_rng(595)
    table = flicker.lookalikes(30.0)
    lines = 0
    runs = 120
    for k in range(runs):
        r, R = _curves(rng, n=240 if k % 2 else 90)
        lines += bool(beatlines.lines_of(beatlines.search(r, R, 30.0, table, 12.0)))
    traffic.rate(check, "a curve with no line is given one about one time in a hundred, all its bands together (LINE_P)", lines, runs, beatlines.LINE_P)


def test_an_object_that_fades_for_a_moment():
    """An object that all but vanishes for two seconds (its brightness a hundredth of its median), with a steady 12 %
    beat at 9.99 Hz and grain: read against its running mean, those two seconds explode (the running mean nears
    nought), and on PR088's object 2 they alone made a "line" and a depth of 690 %. Through `beatreadings.beside`, the
    readings the stage makes: the band search holds the beat and no other line, and the depth leaves the faded pieces
    out."""
    print("\nthe readings on an object that fades for a moment")
    rng = np.random.default_rng(597)
    n = 600
    t = np.arange(n) / FPS
    table = flicker.lookalikes(FPS)
    found, depth = [], []
    for k in range(8):
        level = 1000.0 * (1 + 0.12 * np.sin(2 * np.pi * 9.99 * t + rng.uniform(0, 6.28))) * (1 + 0.01 * rng.standard_normal(n))
        a = 240 + 60 * (k % 3)
        level[a:a + 60] = 10.0 * (1 + 0.5 * rng.standard_normal(60))      # the object all but gone
        use = {"object": [float(v) for v in level]}
        bgs = [f"background {j}" for j in range(4)]
        for c in bgs:
            use[c] = [float(v) for v in 15.0 * rng.standard_normal(n)]
        seg = {c: (0, n) for c in use}
        b = dict(hz=9.99, hz_err=0.02, resolution_hz=0.25, double_hz=19.98, lookalike=flicker.at_lookalikes(9.99, 0.25, table, 0.02))
        fields = {"beat": {"object": b}, "lookalikes": table, "steadiness": {}}
        beatreadings.beside(fields, ["object"], ["object"], use, seg, bgs, {}, 1000.0, FPS, [], 12.0, say=lambda *a: None)
        f = fields["band_lines"]["object"]
        found.append([(round(x["hz"], 2), x["the_beat"]) for x in beatlines.lines_of(f)])
        depth.append(fields["morphology"]["object"]["depth"])
    other = [x for x in found if any(not the for _, the in x)]
    check(not other and all(x for x in found), "the band search holds the beat, and no line that is not it",
          f"{found[:3]}; with another line: {len(other)} of 8")
    check(all(d["power"] and d["left_out"] >= 1 and d["most"] < 0.3 for d in depth),
          "the depth leaves out the pieces where the object is not all there, and reads the rest",
          str([(d["pieces"], d["left_out"], round(d["most"] or 0, 3)) for d in depth[:4]]))
    traffic.rate(check, "a steady beat with a faded moment is said to change depth about one time in a hundred (DEPTH_P)",
                 sum(bool(d["changes"]) for d in depth), 8, beatshape.DEPTH_P, str([round(d["p"], 2) for d in depth]))


class _Drifting(_Scene):
    """A point whose brightness wanders slowly by 25 % and carries a line of 5 % at 10.5 Hz. Eight seconds."""
    n1 = 240
    fps = 30.0

    def rgb(self, n):
        if n not in self.cache:
            g = 60 + np.random.default_rng(n).normal(0, 1.5, (self.H, self.W))
            x, y = self.at(0, n)
            t = n / self.fps
            a = 120 * (1 + 0.25 * np.sin(2 * np.pi * 0.35 * t) + 0.12 * np.sin(2 * np.pi * 2.2 * t + 1.0) * np.sin(2 * np.pi * 0.21 * t)
                       + 0.05 * np.sin(2 * np.pi * 10.5 * t))
            yy, xx = np.mgrid[0:self.H, 0:self.W]
            g = g + a * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * self.sigma ** 2))
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


def test_the_readings_change_no_call():
    """Through `flicker.measure`, with the readings and with them taken out: the call, the beat, its frequency and every
    field the stage had before are the same; the readings only add."""
    print("\nthe readings beside the call: the call is as it was without them")
    clips = {"a point that bobs as it beats": lambda: _Scene([(60.0, 80.0, 0.5, 6.3, 0.2)], texture=False),
             "a line behind a drift": lambda: _Drifting([(60.0, 80.0, 0.0, 0.0, 0.0)], texture=False),
             "a beat at a third of the frame rate": lambda: _Scene([(60.0, 80.0, 0.0, FPS / 3, 0.2)], texture=False, sigma=3.0)}
    for what, make in clips.items():
        with_ = _measure(make())
        keep = beatreadings.beside, beatreadings.said, beatpos.of_stage
        beatreadings.beside = beatreadings.said = lambda *a, **k: None
        beatpos.of_stage = lambda *a, **k: {}
        try:
            without = _measure(make())
        finally:
            beatreadings.beside, beatreadings.said, beatpos.of_stage = keep
        a, b = with_.fields, without.fields
        new = set(a) - set(b)
        # E11's clause is the one thing said inside a sentence the stage had: taken out, the sentence is as it was
        plain = lambda m: re.sub(r" \(at this frame rate such marks cover \d+% of the frequencies a beat is looked for at, so a mark is "
                                 r"weak evidence\)| A mark is common: read as this beat was, \d+% of the band from [\d.]+ to [\d.]+ Hz "
                                 r"carries one at this frame rate\.", "", m)
        same = all(repr(a[k]) == repr(b[k]) for k in b if k not in ("beat", "finding")) and plain(a["finding"]) == b["finding"]
        beat_same = all(repr({k: v for k, v in a["beat"][n].items() if k != "lookalike_share"}) == repr(b["beat"][n]) for n in b.get("beat") or {})
        check(same and beat_same and a["beats"] == b["beats"] and a.get("strong") == b.get("strong"),
              f"{what}: the call and every field the stage had are the same", f"beats {a['beats']}; added {sorted(new)}")
        was = [plain(m) for m in with_.notes]
        check(new <= {"lookalike_share", "band_lines", "morphology", "position_beat"} and all(m in was for m in without.notes)
              and all(with_.result.get(k) == v or k == "finding" for k, v in without.result.items()),
              f"{what}: the readings only add fields, notes and result lines", str(sorted(new)))
        if what.startswith("a line"):
            lines = [x for x in beatlines.lines_of((a.get("band_lines") or {}).get("object")) if not x["the_beat"]]
            check(bool(lines) and abs(lines[0]["hz"] - 10.5) <= 0.2 and any("which the background beside it does not show" in m for m in with_.notes),
                  "the stage reports the 10.5-Hz line under its call, whatever the call is",
                  f"beats {a['beats']}: {(a.get('finding') or '')[:90]} | " + next((m for m in with_.notes if "beside it does not show" in m), "")[:160]
                  + " | " + str([(b["band"], round(b["hz"], 2), round(b["stands"], 1), b["p"], b["shared"], b["the_beat"], [round(v, 1) for v in b["background"]])
                                 for b in ((a.get("band_lines") or {}).get("object") or {}).get("bands", [])]) + str((a.get("band_lines") or {}).get("object", {}).get("why")))
        if what.startswith("a beat at a third"):
            m = (a.get("morphology") or {}).get("object")
            check(a["beats"] is True and m is not None and m["depth"]["power"] and not m["depth"]["changes"] and any("Three readings" in s for s in with_.notes),
                  "a steady beat at a third of the frame rate gets the three readings of its shape, its depth held",
                  next((s for s in with_.notes if "Three readings" in s), str(m))[:420])
            w = (m or {}).get("width") or {}
            check(w.get("power") is not None and (not w.get("power") or not w["width"]["line"]),
                  "and its width outside a fixed core does not beat, or is not read", str({k: w.get(k) for k in ("power", "why", "width", "planted")})[:300])


# ---- the shape of a beat on a look-alike (T2) ----------------------------------------------------------------------
def test_depth_along_the_track():
    """A beat of one depth is not said to change; one whose depth doubles along the track is; a short stretch is not
    read."""
    print("\nthe shape of a beat: its depth along the track")
    rng = np.random.default_rng(596)
    n = 300
    t = np.arange(n) / FPS
    curve = lambda depth: depth * np.cos(2 * np.pi * 9.99 * t + rng.uniform(0, 6.28)) + 0.05 * rng.standard_normal(n)
    steady = [beatshape.depth_along(curve(0.12 + 0 * t), FPS, 9.99, runs=100, seed=k) for k in range(12)]
    grows = [beatshape.depth_along(curve(0.08 + 0.10 * t / t[-1]), FPS, 9.99, runs=100, seed=k) for k in range(8)]
    check(all(s["power"] and s["pieces"] == 5 for s in steady), "ten seconds are read in five pieces of two")
    traffic.rate(check, "a beat of one depth is said to change about one time in a hundred (DEPTH_P)", sum(s["changes"] for s in steady),
                 12, beatshape.DEPTH_P, str([round(s["p"], 2) for s in steady]))
    traffic.rate(check, "a beat whose depth doubles along the track is missed 5 % of the time at most (a judgement)",
                 8 - sum(s["changes"] for s in grows), 8, 0.05, str([round(s["p"], 3) for s in grows]))
    short = beatshape.depth_along(curve(0.12 + 0 * t)[:100], FPS, 9.99)
    check(short["power"] is False and "too short" in short["why"], "100 frames: not read, and why", short["why"])


def _stamps(rng, n, sigma, hz, bright=0.0, width=0.0, peak=120.0, grain=1.5):
    """Stamps of a blob (33 px square, as `flicker.stamp` cuts them) whose brightness beats by `bright` and whose width
    by `width`, at hz."""
    yy, xx = np.mgrid[-16:17, -16:17]
    t = np.arange(n) / FPS
    out = []
    for k in range(n):
        s = sigma * (1 + width * np.sin(2 * np.pi * hz * t[k]))
        a = peak * (1 + bright * np.sin(2 * np.pi * hz * t[k]))
        out.append((60 + a * np.exp(-(xx ** 2 + yy ** 2) / (2 * s * s)) + grain * rng.standard_normal(xx.shape)).astype(np.float32))
    return out, bright * np.sin(2 * np.pi * hz * t)


def test_width_outside_a_fixed_core():
    """A blob 3 px in sigma: its brightness alone beating leaves the width outside a 3-px core still, and a planted
    change of width would have shown; its width beating by 8 % shows; a point (1 px) has too little light outside the core
    to say."""
    print("\nthe shape of a beat: its width outside a fixed core")
    rng = np.random.default_rng(597)
    hz = 9.99
    S, r = _stamps(rng, 240, 3.0, hz, bright=0.2)
    w = beatshape.width_outside_core(S, r, FPS, hz, ring_in=10.0, top=12.0)
    check(w["power"] and not w["width"]["line"] and w["planted"]["shows"],
          "brightness alone beating: no line in the width outside the core, where a planted change of 10 % shows",
          f"chance {w['width']['p']:.2f}; planted chance {w['planted']['p']:.2g}; {w['outside_share']:.0%} of its light outside the core")
    check(w["area"] is not None and w["area"]["line"], "though its pixel area beats in step, as a brighter blob's does",
          f"area chance {w['area']['p']:.2g}, {w['area']['phase_deg']:+.0f} deg from the brightness")
    S, r = _stamps(rng, 240, 3.0, hz, bright=0.2, width=0.08)
    w = beatshape.width_outside_core(S, r, FPS, hz, ring_in=10.0, top=12.0)
    check(w["power"] and w["width"]["line"], "its width beating by 8 %: a line in the width outside the core", f"chance {w['width']['p']:.2g}")
    S, r = _stamps(rng, 240, 1.0, hz, bright=0.2)
    w = beatshape.width_outside_core(S, r, FPS, hz, ring_in=7.0, top=12.0)
    check(w["power"] is False and ("a point" in w["why"] or "does not show" in w["why"]), "a point: NO POWER, and why", w["why"])
    S, r = _stamps(rng, 240, 3.0, hz, bright=0.2, peak=400.0)
    S = [np.clip(s, 0, 255) for s in S]
    w = beatshape.width_outside_core(S, r, FPS, hz, ring_in=10.0, top=12.0)
    check(w["power"] is False and "ceiling" in w["why"], "a blob clipped beyond its core: NO POWER, and why", w["why"])


def test_which_beats_get_the_readings():
    """A look-alike the chain or a supply makes is read; a flame's band and a rotor's are the object's own, and are not."""
    print("\nthe shape of a beat: which marks ask for it")
    table = flicker.lookalikes(30.0)
    at = lambda hz: beatshape.chain_marked(dict(lookalike=flicker.at_lookalikes(hz, 0.1, table, 0.03)))
    check(any("locked to every 3" in m for m in at(10.0)) and at(5.5) == [] and len(at(9.0)) >= 1,
          "10.0 Hz at 30 frames a second is the chain's (a third of the frame rate, the folded supplies); 5.5 Hz is only the lantern's, and is not",
          f"10.0: {len(at(10.0))} marks; 9.0: {at(9.0)[:1]}; 5.5: {at(5.5)}")


# ---- the look-alike mark's base rate (E11) -------------------------------------------------------------------------
def test_the_marks_base_rate():
    """From the table itself: 70 % of 1.5-12 Hz at 29.97 and 30 frames a second (IDEAS.md E11, measured 2026-10-28), all of
    the band at 59.94 and 60; wider as a beat's resolution grows; and said where a mark is said."""
    print("\nthe look-alike mark's base rate")
    share = lambda fps, **k: flicker.marked_share(flicker.lookalikes(fps), flicker.TOP * fps / 2, **k)
    check(all(abs(share(f)["share"] - 0.695) < 0.005 for f in (30.0, FPS)) and share(30.0)["marked_hz"] == [[4.7, 12.0]],
          "70 % of 1.5-12 Hz at 29.97 and 30 frames a second: one piece, 4.7-12 Hz", f"{share(FPS)['share']:.3f}, {share(30.0)['marked_hz']}")
    check(all(share(f)["share"] > 0.999 for f in (60.0, 60000 / 1001)), "all of 1.5-24 Hz at 59.94 and 60",
          " ".join(f"{share(f)['share']:.4f}" for f in (60.0, 60000 / 1001)))
    check(share(30.0, resolution=0.5)["share"] > share(30.0, resolution=0.2)["share"] > share(30.0)["share"],
          "a beat read at a coarser resolution is marked over more of the band",
          f"{share(30.0, resolution=0.2)['share']:.3f}, {share(30.0, resolution=0.5)['share']:.3f}")
    found = _measure(_Scene([(60.0, 80.0, 0.0, 6.0, 0.2)], texture=False))
    b = found.fields["beat"]["object"]
    check(found.fields["beats"] is True and 0.69 <= b["lookalike_share"] <= 0.76 and "such marks cover" in found.fields["finding"]
          and abs(found.fields["lookalike_share"]["share"] - 0.695) < 0.005,
          "a planted 6-Hz beat, marked with the lantern's band: the finding says how much of the band carries such a mark",
          found.fields["finding"][-150:])


# ---- the track's own jitter (method section 69) ---------------------------------------------------------------------
class _Cloud:
    """A steady, ragged bright patch drifting slowly over a plain sky, and a track that hops about its true place as a
    detector's box does: `hop` px of a rhythm near `hop_hz` that never keeps time, and `grain` px of scatter with no
    rhythm. Its brightness does not change, unless `beat` (a share, at `beat_hz`). `lumps`: how ragged it is (0: smooth);
    `width`: its half-width, px. It sits where the stage reads no size for it (the frame's edge is nearer than the size's
    far ring), so the aperture is the point's and rides the track, as on the Galileo Project's clouds. At module level,
    as a class a process pool pickles must be."""
    n0, n1, W, H, fps = 1, 600, 320, 240, 60.0

    def __init__(self, hop=0.5, grain=0.25, hop_hz=2.6, beat=0.0, beat_hz=4.3, width=9.0, lumps=0.9, seed=11, speed=(0.14, 0.05)):
        from scipy import ndimage
        rng = np.random.default_rng(seed)
        self.cache, self.beat, self.beat_hz, self.speed, self.x0, self.y0 = {}, beat, beat_hz, speed, 150.0, 60.0
        yy, xx = np.mgrid[0:self.H, 0:self.W].astype(float)
        tex = ndimage.gaussian_filter(rng.normal(0, 1, (self.H, self.W)), 1.6)
        self.body = (70.0 * np.exp(-(np.hypot(xx - self.x0, yy - self.y0) / width) ** 4)
                     * np.clip(1 + lumps * tex / tex.std(), 0.05, None)).astype(np.float32)
        n = self.n1 + 1
        t = np.arange(n) / self.fps
        tone = hop * np.sin(2 * np.pi * hop_hz * t + np.cumsum(rng.normal(0, 0.12, n)))
        ang = rng.uniform(0, np.pi)
        scatter = lambda: ndimage.gaussian_filter1d(rng.normal(0, 1, n), 2.0) * grain * 2.66
        self.hx, self.hy = tone * np.cos(ang) + scatter(), tone * np.sin(ang) + scatter()

    def at(self, j, n):
        return self.x0 + self.speed[0] * n + self.hx[n], self.y0 + self.speed[1] * n + self.hy[n]

    def rgb(self, n):
        if n not in self.cache:
            from mcdonald.flicker import _fshift
            g = 60 + np.random.default_rng(n).normal(0, 1.5, (self.H, self.W))
            g = g + (1 + self.beat * np.sin(2 * np.pi * self.beat_hz * n / self.fps)) * _fshift(self.body, self.speed[1] * n, self.speed[0] * n)
            self.cache[n] = np.clip(g, 0, 255)[..., None].repeat(3, 2).astype(np.uint8)
        return self.cache[n]


def _tracked(clip, keep=None):
    """`flicker.measure` on the clip's own track; `keep`: JITTER_KEEP for this measurement (0: the reading decides nothing)."""
    was = flicker.JITTER_KEEP
    if keep is not None:
        flicker.JITTER_KEEP = keep
    try:
        return flicker.measure(clip, {"object": {n: clip.at(0, n) for n in range(clip.n0, clip.n1 + 1)}}, say=lambda *a: None, procs=0)
    finally:
        flicker.JITTER_KEEP = was


def test_a_steady_cloud_under_a_hopping_track_has_no_beat_of_its_own():
    """A ragged patch of steady brightness, wider than the aperture, under a track that hops half a pixel: without the
    reading the stage hears a beat that comes back along the whole track; with it the beat is the track's, and the
    stage's own numbers for the beat are as they were."""
    print("\nthe track's own jitter: a steady cloud under a hopping track")
    cloud = _Cloud()
    off, on = _tracked(cloud, keep=0.0), _tracked(cloud)
    b0, b1 = off.fields["beat"]["object"], on.fields["beat"]["object"]
    check(off.fields["beats"] is True and b0["comes_back"] and off.fields["recentred"] == [],
          "without the reading, the hop is heard as a beat of the object's own that comes back",
          f"{b0['hz']:.2f} Hz, {b0['amplitude']:.0%}, {b0['windows_passing']} of {b0['windows']} windows; its brightness is steady")
    j = b1.get("jitter") or {}
    check(on.fields["beats"] is False and on.fields.get("jittered") == ["object"] and on.fields["strong"] == []
          and j.get("holds") is False and j["kept"] < 0.3,
          "with it, the beat is the track's: no beat of its own", f"{j.get('kept', 0):.0%} of the beat left; the fit took "
          f"{j.get('share', 0):.0%} of the curve's variance; jitter {j.get('px', 0):.2f} px")
    check("follows the track's own jitter" in on.fields["finding"] and "the beat is the track's, not the object's" in on.fields["finding"]
          and any(m.startswith("A beat at") and "follows the track's jitter" in m for m in on.notes),
          "the finding and a note say so", on.fields["finding"][:150])
    same = all(b0[k] == b1[k] for k in ("hz", "amplitude", "first", "last", "comes_back", "whole_passes", "windows_passing"))
    check(same and any("the track's own jitter" in line and "the track's, not the object's" in line for line in flicker.said(on.fields)),
          "the beat's own numbers are as they were, and `mcdonald flicker` prints the reading")
    still = _tracked(_Cloud(hop=0.0, grain=0.0))
    check(still.fields["beats"] is False and not still.fields.get("jittered"),
          "the same cloud under a track that does not hop: no beat, and nothing given to the track", (still.fields["finding"] or "")[:90])


def test_a_beating_spot_keeps_its_beat_under_a_hopping_track():
    """A spot whose own brightness beats, under the same hop; and a bird that bobs as it beats, its track following the
    bob (the paper's flyers: method section 59.1): each keeps its beat."""
    print("\nthe track's own jitter: a spot that beats keeps its beat")
    spot = _tracked(_Cloud(width=1.7, lumps=0.0, beat=0.2))
    b = spot.fields["beat"]["object"]
    j = b.get("jitter") or {}
    check(spot.fields["beats"] is True and abs(b["hz"] - 4.3) < 0.2 and j.get("holds") is True and j["kept"] > 0.8
          and not spot.fields.get("jittered"),
          "a spot beating 20 % at 4.3 Hz under a hop of half a pixel: the beat is its own",
          f"{b['hz']:.2f} Hz, {b['amplitude']:.0%}; {j.get('kept', 0):.0%} of it left with what follows the jitter out")
    bird = _measure(_Scene([(60.0, 80.0, 0.5, 6.3, 0.2)], texture=False))
    bb = bird.fields["beat"]["object"]
    jb = bb.get("jitter") or {}
    check(bird.fields["beats"] is True and jb.get("holds") is True and jb["kept"] > 0.7 and jb["px"] > 0.05,
          "a bird that bobs half a pixel at its own beat, its track bobbing with it: the beat is its own",
          f"{bb['hz']:.2f} Hz; {jb.get('kept', 0):.0%} left; the track's jitter {jb.get('px', 0):.2f} px")


def test_the_jitter_reading_on_drawn_curves():
    """`flicker.jitter_reading` on curves drawn with a known answer: a brightness that is a function of where the
    aperture sits is the track's; a beat beside a jitter that has nothing to do with it is kept; a jitter that keeps
    time with the beat at the beat's frequency only (a bird's bob) is kept, because the fit is learned away from it."""
    print("\nthe track's own jitter: the reading on drawn curves")
    from scipy import ndimage
    fps, n = 30.0, 60
    t = np.arange(n) / fps
    red = lambda rng, k=n: ndimage.gaussian_filter1d(rng.normal(0, 1, k), 1.5)
    follows, beside, bobs, plain = [], [], [], []
    for seed in range(40):
        rng = np.random.default_rng(100 + seed)
        jx, jy = 0.3 * red(rng), 0.3 * red(rng)
        made = 0.2 * jx - 0.15 * jy + rng.normal(0, 0.004, n)                # the brightness follows the aperture's place
        hz = flicker._peak(made - made.mean(), fps)["hz"]
        follows.append(flicker.jitter_reading(made - made.mean(), jx, jy, fps, hz)["kept"])
        own = 0.1 * np.sin(2 * np.pi * 4.0 * t + rng.uniform(0, 6.28)) + rng.normal(0, 0.01, n)
        beside.append(flicker.jitter_reading(own - own.mean(), jx, jy, fps, 4.0)["kept"])
        ph = rng.uniform(0, 6.28)
        bx, by = 0.1 * np.sin(2 * np.pi * 4.0 * t + ph) + 0.05 * red(rng), 0.4 * np.sin(2 * np.pi * 4.0 * t + ph + 1.0) + 0.05 * red(rng)
        wing = 0.1 * np.sin(2 * np.pi * 4.0 * t + ph + 0.4) + rng.normal(0, 0.01, n)
        bobs.append(flicker.jitter_reading(wing - wing.mean(), bx, by, fps, 4.0)["kept"])
        A = np.c_[bx - bx.mean(), by - by.mean()]                             # the same fit with the beat left in
        res = (wing - wing.mean()) - A @ np.linalg.lstsq(A, wing - wing.mean(), rcond=None)[0]
        fr, F0, _, _, _ = flicker._spec(wing - wing.mean(), fps)
        k = int(np.argmin(np.abs(fr - 4.0)))
        plain.append(float(np.abs(flicker._spec(res, fps)[1][k]) / np.abs(F0[k])))
    check(max(follows) < flicker.JITTER_KEEP, "a brightness made by where the aperture sits: the track's, 40 times in 40",
          f"kept {min(follows):.2f}-{max(follows):.2f}")
    k = sum(v >= flicker.JITTER_KEEP for v in beside)
    traffic.rate(check, "a beat beside a jitter that has nothing to do with it is given to the track 1 time in 100 at most", 40 - k, 40, 0.01,
                 f"kept {min(beside):.2f}-{max(beside):.2f}")
    k = sum(v >= flicker.JITTER_KEEP for v in bobs)
    check(k >= 38 and float(np.median(plain)) < flicker.JITTER_KEEP,
          "a track that bobs in time with the beat, at the beat's frequency only: kept, where a fit with the beat left in takes it",
          f"{k} of 40 kept (kept {min(bobs):.2f}-{max(bobs):.2f}); with the beat left in, the median kept {np.median(plain):.2f}")
    z = flicker.jitter_reading(own - own.mean(), np.zeros(n), np.zeros(n), fps, 4.0)
    check(z["kept"] == 1.0 and z["holds"] and z["px"] == 0.0, "a track with no jitter has nothing to follow: the beat is kept whole")
    # a long curve whose answer to the hop turns over along the track: one fit for the whole of it sees nothing, blocks do
    fps2, n2 = 60.0, 900
    rng = np.random.default_rng(7)
    jx, jy = 0.3 * red(rng, n2), 0.3 * red(rng, n2)
    made = np.sin(2 * np.pi * np.arange(n2) / n2 * 2) * 0.3 * jx + rng.normal(0, 0.004, n2)
    hz = flicker._peak(made - made.mean(), fps2)["hz"]
    got = flicker.jitter_reading(made - made.mean(), jx, jy, fps2, hz)
    check(got["blocks"] > 1 and not got["holds"], "a hop whose effect changes sign along the track is still the track's, block by block",
          f"{got['blocks']} blocks, kept {got['kept']:.2f}")


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    if traffic.WARNS:
        print(f"\n{len(traffic.WARNS)} WARN (a count on drawn data in the yellow, not failed): " + "; ".join(traffic.WARNS))
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        _s.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
