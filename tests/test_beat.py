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
        r = beatpos.reading(f, x, y, FPS, beat=dict(hz=6.2, hz_err=0.03, double_hz=None), draws=300)
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
    x = codec[1] + 0.25 * np.sign(np.sin(2 * np.pi * 12.0 * (codec[0] - 1) / 60.0))       # a centroid that stops at the GOP's rate
    r = beatpos.reading(codec[0], x, codec[2], 60.0, lines=[12.0], draws=300, hole=False)
    check(r.get("codec") is not None and r["codec"]["line"] and abs(r["hz"] - 12.0) > 0.25,
          "a rhythm at the codec's own rate is left out of the search and said apart",
          f"codec {r.get('codec')}; the track's strongest {r['hz']:.2f} Hz, chance {r['p']:.2f}")


class _Scene:
    """Points on a textured background that a camera shakes: every point and the texture move together `shake` px at
    `shake_hz`; each point is [(x, y, bob px, beat Hz, brightness share)] -- it rises and falls `bob` px at its beat, and its
    brightness beats there by `share`. At module level, as a class a process pool pickles must be."""
    n0, n1, W, H, fps = 1, 150, 320, 240, 30000 / 1001

    def __init__(self, points, shake=0.0, shake_hz=3.5, texture=True, sigma=1.2):
        self.points, self.shake, self.shake_hz, self.texture, self.sigma, self.cache = points, shake, shake_hz, texture, sigma, {}
        from scipy import ndimage
        self.back = ndimage.gaussian_filter(np.random.default_rng(5).normal(0, 1, (self.H, self.W)), 3.0) * 250 if texture else None

    def moved(self, n):
        return self.shake * np.sin(2 * np.pi * self.shake_hz * n / self.fps)

    def at(self, j, n):
        x, y, bob, hz, _ = self.points[j]
        return x + 0.31 * n + self.moved(n), y + 0.17 * n + bob * np.sin(2 * np.pi * hz * n / self.fps + j)

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
    lamp = _measure(_Scene([(60.0, 80.0, 0.0, 6.3, 0.2)], texture=False))
    pl = (lamp.fields.get("position_beat") or {}).get("object") or {}
    check(lamp.fields["beats"] is True and pl.get("power") and not (pl.get("at_beat") or {}).get("line"),
          "a point whose brightness alone beats: the beat is not in its position",
          next((m for m in lamp.notes if m.startswith("Its position")), "")[:200])


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
    alone = {k: beatpos.reading(ns, [m[k][0] for m in moves], [m[k][1] for m in moves], clip.fps, draws=300, hole=False) for k in moves[0]}
    check(all(r["line"] and abs(r["hz"] - 3.5) <= 0.2 for r in alone.values()),
          "alone, each track's strongest rhythm is the camera's 3.5 Hz", " ".join(f"{r['hz']:.2f}" for r in alone.values()))
    got = beatpos.of_stage(ns, clip.fps, moves, fields, draws=300)
    check(all(r["how"] == "members" and r["against"] == 2 for r in got.values()), "in a group each is read against the other two")
    check(all(r["at_beat"]["line"] and r["at_beat"]["agrees"] and r["own"] is True for r in got.values()),
          "against them each carries its own beat", " ".join(f"{r['at_beat']['position_hz']:.2f}" for r in got.values()))
    check(all(abs(r["hz"] - 3.5) > 0.3 for r in got.values()), "and the shake is gone from every one",
          " ".join(f"{r['hz']:.2f}" for r in got.values()))


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
          f"scene {sc}; how {pb.get('how')}")
    check(pb.get("power") and not pb.get("line") and pb.get("own") is False,
          "against the scene the shake is gone: no rhythm of its own", next((m for m in found.notes if m.startswith("Its position")), "")[:200])
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
        r, R = _curves(rng, line=(10.5, 0.044))
        got = beatlines.search(r, R, 30.0, table, 12.0, beat=dict(hz=flicker._peak(r, 30.0)["hz"], double_hz=None, resolution_hz=0.125))
        lines = [b for b in beatlines.lines_of(got) if not b["the_beat"]]
        found += bool(lines and abs(lines[0]["hz"] - 10.5) <= 0.15)
        where += [b["band"] for b in lines[:1]]
    traffic.rate(check, "a 4.4 % line at 10.5 Hz behind an 8 % drift is missed 5 % of the time at most (a judgement)", 10 - found, 10, 0.05,
                 f"named by the band {sorted(set(where))}")
    r, R = _curves(rng, line=(10.5, 0.044))
    got = beatlines.search(r, R, 30.0, table, 12.0)
    row = beatlines.lines_of(got)[0]
    check(0.03 <= row["amplitude"] <= 0.06 and row["p"] < beatlines.LINE_P and row["stands"] > max(row["background"]),
          "with its amplitude, its chance and the background apertures' own standing beside it",
          f"{row['amplitude']:.3f}, chance {row['p']:.2g}, {row['stands']:.0f} against {max(row['background']):.1f}")
    said = beatlines.said("object", got, calls=False)
    check(said and "which the background's apertures do not show" in said and "does not call it a beat" in said, "said in the row's words", said)
    r, R = _curves(rng, line=(10.5, 0.044), shared=True)
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
            check(bool(lines) and abs(lines[0]["hz"] - 10.5) <= 0.2 and any("which the background's apertures do not show" in m for m in with_.notes),
                  "the stage reports the 10.5-Hz line under its call, whatever the call is",
                  f"beats {a['beats']}: {(a.get('finding') or '')[:90]} | " + next((m for m in with_.notes if "apertures do not show" in m), "")[:160])
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
    check(any("every 3th frame" in m or "locked to every 3" in m for m in at(10.0)) and at(6.0) == [] and len(at(9.0)) >= 1,
          "10.0 Hz at 30 frames a second is the chain's (a third of the frame rate, the folded supplies); 6.0 Hz is only the lantern's, and is not",
          f"10.0: {len(at(10.0))} marks; 9.0: {at(9.0)[:1]}; 6.0: {at(6.0)}")


# ---- the look-alike mark's base rate (E11) -------------------------------------------------------------------------
def test_the_marks_base_rate():
    """From the table itself: 70 % of 1.5-12 Hz at 29.97 and 30 frames a second (IDEAS.md E11, measured 2026-10-28), all of
    the band at 59.94 and 60; wider as a beat's resolution grows; and said where a mark is said."""
    print("\nthe look-alike mark's base rate")
    share = lambda fps, **k: flicker.marked_share(flicker.lookalikes(fps), flicker.TOP * fps / 2, **k)
    check(all(abs(share(f)["share"] - 0.695) < 0.005 for f in (30.0, FPS)) and share(30.0)["marked_hz"] == [[4.7, 12.0]],
          "70 % of 1.5-12 Hz at 29.97 and 30 frames a second: one piece, 4.7-12 Hz", f"{share(FPS)['share']:.3f}, {share(30.0)['marked_hz']}")
    check(all(share(f)["share"] == 1.0 for f in (60.0, 60000 / 1001)), "all of 1.5-24 Hz at 59.94 and 60")
    check(share(30.0, resolution=0.5)["share"] > share(30.0, resolution=0.2)["share"] > share(30.0)["share"],
          "a beat read at a coarser resolution is marked over more of the band",
          f"{share(30.0, resolution=0.2)['share']:.3f}, {share(30.0, resolution=0.5)['share']:.3f}")
    found = _measure(_Scene([(60.0, 80.0, 0.0, 6.0, 0.2)], texture=False))
    b = found.fields["beat"]["object"]
    check(found.fields["beats"] is True and 0.69 <= b["lookalike_share"] <= 0.76 and "such marks cover" in found.fields["finding"]
          and abs(found.fields["lookalike_share"]["share"] - 0.695) < 0.005,
          "a planted 6-Hz beat, marked with the lantern's band: the finding says how much of the band carries such a mark",
          found.fields["finding"][-150:])


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
