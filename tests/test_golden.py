"""Do the real clips still give the published numbers?

test_measurement.py proves the library measures synthetic scenes correctly.
This proves it has not drifted on the clips whose results have been published
or circulated — the ones where a changed number would mean a retraction.

It needs the video files, which are too large for the repository. They are
found in the reference-data folder, $MCDONALD_DATA or data/mcdonald beside the
repository (see tests/reference_data.py and that folder's README.md):

    python3 tests/test_golden.py

A PURSUE clip that is not there is looked for where the active catalog keeps it
(the folder `mcdonald` downloads into). A clip that is nowhere is skipped, and
said. Every track and table the tests read is vendored in tests/golden/, so only
the video has to be found.

Two levels:
  (default)  a 200-frame window of PR144 -- about 5 minutes, catches any
             regression in masks, registration, layer classes or consensus.
             It passes --fresh: `layers` keeps its templates beside the frames,
             and until 2026-09-20 this test found the ones an earlier run had
             left there and took 25 s: the masks, the layer classes and the
             consensus were tested, and the registration not at all.
  --full     the documented whole-clip commands against the published values
             in docs/method.md -- tens of minutes.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

sys.path.insert(0, str(HERE))

from mcdonald import catalog  # noqa: E402
import reference_data  # noqa: E402

FAIL, SKIP = [], []

# Frames 300-500 of PR144, measured 2026-09-19 with the command in run_window().
# Tolerances are wider than any float or thread-ordering difference and far
# tighter than any real regression: these are consensus medians over dozens of
# templates, and a broken mask or a mis-set zero zone moves them by tens.
WINDOW_BASELINE = {
    "object vs sea": (599, 4),
    "object vs cloud tops": (500, 4),
    "cloud tops vs sea": (99, 3),
    "ratio": (6.0, 0.4),
    "group gap": (97, 5),
}

# The whole-clip results in docs/method.md, section 4. Checked only with --full.
PUBLISHED = {
    "object vs sea": (648, 12),
    "object vs cloud tops": (510, 12),
    "cloud tops vs sea": (98, 4),
    "ratio": (6.2, 0.5),
}


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def parse(out):
    """The numbers a reader would take off the tool's own summary."""
    got = {}
    for label, key in (("the sea", "object vs sea"),
                       ("the cloud tops", "object vs cloud tops"),
                       ("the cloud tops against the sea", "cloud tops vs sea")):
        m = re.search(rf"^\s+{re.escape(label)}\s+median\s+(-?\d+)", out, re.M)
        if m:
            got[key] = float(m.group(1))
    m = re.search(r"ratio ([\d.]+)", out)
    if m:
        got["ratio"] = float(m.group(1))
    m = re.search(r"two in [\d.]+% of pairs, (\d+) px/s apart", out)
    if m:
        got["group gap"] = float(m.group(1))
    return got


def fields(out, what):
    """The same numbers as `layers --json` has them: fields, not sentences. And what it
    printed for a person, read the way `parse` reads it, has to be those fields rounded."""
    r = json.loads(out)["results"]
    med = lambda s: None if not s else s["median"]
    got = {"object vs sea": med(r["px_per_s"]["striated"]), "object vs cloud tops": med(r["px_per_s"]["isotropic"]),
           "cloud tops vs sea": med(r["layer_against_layer"]), "ratio": (r["object_over_parallax"] or {}).get("ratio"),
           "group gap": r["motion_groups"]["apart_px_per_s"]}
    got = {k: v for k, v in got.items() if v is not None}
    read = parse("\n".join(r["said"]))
    check(set(read) == set(got) and all(abs(read[k] - got[k]) <= (0.051 if k == "ratio" else 0.51) for k in got),
          f"{what}: what it prints for a person is its fields, rounded", ", ".join(f"{k} {read.get(k)} / {got[k]:.2f}" for k in got))
    return got


def have_clip(record_id):
    return reference_data.pursue_clip(record_id)


def run(args, workdir):
    r = subprocess.run([sys.executable, "-m", "mcdonald.cli"] + args,
                       capture_output=True, text=True, cwd=workdir,
                       env={**os.environ, "PYTHONPATH": str(HERE.parent / "src")})
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-2000:], file=sys.stderr)
        raise SystemExit(f"mcdonald {' '.join(args)} exited {r.returncode}")
    return r.stdout


def compare(got, expected, what):
    for key, (want, tol) in expected.items():
        if key not in got:
            check(False, f"{what}: {key}", "not present in the tool's output")
            continue
        check(abs(got[key] - want) <= tol, f"{what}: {key}",
              f"{got[key]:g} (expected {want:g} +/- {tol:g})")


def test_pr113_two_clicks():
    """Technical Note Sec. 5. Two clicks are the whole human input: the link has to
    choose the detector from them, follow a 142 px/frame object that the blind
    tracker cannot acquire, and land on the four positions the published rate
    was measured over."""
    print("\nPR113, frames 400-420 -- from two clicks to the published track")
    video, why = have_clip("PR113")
    if not video:
        print(f"  SKIP  {why}")
        SKIP.append("PR113 two clicks")
        return
    import numpy as np
    from mcdonald import autolink, forensics as vf
    clip = vf.Clip(video, None, 400, 420)
    marks = {408: (1009.0, 313.0), 411: (702.0, 604.0)}          # the identification in pr113_track.py's docstring
    L = list(autolink.link_from_marks(clip, marks))[-1]
    check(L.size == 21.0 and L.dark is True, "PR113: the detector chosen from the marks is 21 px, dark",
          f"{L.size:g} px, dark={L.dark}")
    gold = vf.read_track(HERE / "golden" / "pr113_transit_curated.csv")
    check(sorted(L.track) == sorted(gold), "PR113: linked on the four frames of the transit, and no others",
          f"{sorted(L.track)}")
    worst = max((float(np.hypot(L.track[n][0] - x, L.track[n][1] - y)) for n, (x, y) in gold.items() if n in L.track),
                default=float("inf"))
    check(worst <= 0.05, "PR113: at the vendored positions", f"worst {worst:.3f} px")
    check(L.worst() is not None and L.worst() <= 3.0, "PR113: and within a click's error of both hand marks",
          ", ".join(f"{n}: {d:.1f} px" for n, d in L.residuals.items()))
    if len(L.track) > 1:
        v = vf.velocity_from_marks({n: L.track[n] for n in (min(L.track), max(L.track))})
        check(abs(float(np.hypot(*v)) - 142.0) <= 1.0, "PR113: the automatic track gives back the published 142 px/frame",
              f"({v[0]:+.1f}, {v[1]:+.1f}) = {np.hypot(*v):.1f}")


def test_pr43_streak_by_motion():
    """PR43 (Jacob, 2026-09-27): a small bright thing crossing about 20 px a frame over ground, drawn out into a
    dash by the exposure. Find's first proposal is it; no spot size holds its marks (the nearest spot 61 px
    away); the link follows its motion instead, from the two marks Find placed, and lands on the dash on
    every frame it is in, 50-75, within 1.4 px of both marks."""
    print("\nPR43, frames 1-88 -- a streak followed by its motion from Find's two marks")
    video, why = have_clip("PR43")
    if not video:
        print(f"  SKIP  {why}")
        SKIP.append("PR43 streak")
        return
    import numpy as np
    from mcdonald import autolink, forensics as vf
    clip = vf.Clip(video, None, 1, 88)
    marks = {57: (1039.0, 836.0), 71: (1301.8, 1000.8)}            # Find's marks on its first proposal, as Jacob's save has them
    steps = list(autolink.link_from_marks(clip, marks))
    L = steps[-1]
    check(L.done and L.track and set(L.source.values()) == {"motion"} and any(s.stage == "motion" for s in steps),
          "PR43: no spot size holds the marks, and the link follows the motion instead", L.say[:80])
    check(L.track and 49 <= min(L.track) <= 52 and 74 <= max(L.track) <= 77 and len(L.track) >= 23,
          "PR43: on the frames the thing is in, 50-75", f"{len(L.track)} frames {min(L.track) if L.track else '-'}–{max(L.track) if L.track else '-'}")
    at65 = L.track.get(65)
    check(at65 is not None and np.hypot(at65[0] - 1158.2, at65[1] - 913.5) <= 4.0, "PR43: on the dash at frame 65, to 4 px",
          f"{at65}")
    check(L.worst() is not None and L.worst() <= 3.0 and L.dark is False, "PR43: within 3 px of both marks, bright",
          ", ".join(f"{n}: {d:.1f} px" for n, d in L.residuals.items()))
    if L.track and 57 in L.track and 71 in L.track:
        v = vf.velocity_from_marks({57: L.track[57], 71: L.track[71]})
        check(abs(float(np.hypot(*v)) - 22.0) <= 2.5, "PR43: about 22 px a frame between the two marks (660 px/s)",
              f"({v[0]:+.1f}, {v[1]:+.1f}) = {np.hypot(*v):.1f} px/frame")


GALILEO = reference_data.galileo()      # the flyer clips; their tracks and galileo_clips.csv are in tests/golden/
GOLDEN = HERE / "golden"


def test_flyer5_wingbeat():
    """Galileo Project Dalek flyer 5 (Jacob's bird control, 2026-09-29): the paper measured its wingbeat at
    3.90 Hz with the double at 7.80, over source frames 52322-52456. The stage, on the paper's own track,
    finds the beat in a window over the flapping and names the fundamental."""
    print("\nflyer 5 (Galileo Dalek) -- the paper's wingbeat, 3.90 / 7.80 Hz")
    video = next(iter(GALILEO.glob("flyer5_*.mp4")), None)
    track_csv = GOLDEN / "flyer5_paper_track.csv"
    if video is None or not track_csv.exists():
        print("  SKIP  the Galileo clips are not on this computer")
        SKIP.append("flyer 5")
        return
    import csv
    from mcdonald import flicker, forensics as vf
    track = {int(r["frame"]) - 51720: (float(r["x"]), float(r["y"])) for r in csv.DictReader(open(track_csv, encoding="utf-8"))}
    clip = vf.Clip(video, None, min(track), max(track))
    found = flicker.measure(clip, {"object": track}, say=lambda *a: None)
    f = found.fields
    b = (f.get("beat") or {}).get("object")
    check(f["beats"] is True and b is not None, "flyer 5: its brightness beats, the object's own",
          str(f.get("finding") or found.no_power)[:120] + f"; trimmed {f.get('trimmed')}")
    check(b is not None and abs(b["hz"] - 3.90) <= 0.2 and b["double_hz"] is not None and abs(b["double_hz"] - 7.80) <= 0.4,
          "flyer 5: 3.9 Hz and its double 7.8, as the paper has them", f"{b['hz']:.2f} Hz, double {b['double_hz']}" if b else "")


def _flicker(video, tracks, n0, n1, dark=False):
    """`flicker.measure` on tracks of a real clip, frames n0-n1."""
    from mcdonald import flicker, forensics as vf
    clip = vf.Clip(video, None, n0, n1)
    return flicker.measure(clip, tracks, dark=dark, say=lambda *a: None)


def test_pr23_no_bird():
    """PR23 (2026-10-09), a look-down IR clip over a town: the one-press run called it "a bird", from a beat at
    2.1 Hz -- which was one dip, the object lost against a hot roof for seven frames, read through the running
    mean that turns any slow change into a peak near 2 Hz. On the track that run followed: the frames it was
    lost on are found and left out, and there is no beat of its own."""
    print("\nPR23, frames 1-208 -- no beat: the roof it crossed is left out")
    video, why = have_clip("PR23")
    if not video:
        print(f"  SKIP  {why}")
        SKIP.append("PR23 no bird")
        return
    from mcdonald import report, forensics as vf
    found = _flicker(video, {"object": vf.read_track(HERE / "golden" / "pr23_object_track.csv")}, 1, 208)
    f = found.fields
    lost = (f.get("lost") or {}).get("object") or []
    check(set(range(131, 137)) <= set(lost) and len(lost) <= 10, "PR23: the frames it crossed the roof on are found lost", str(lost))
    check(f["beats"] is not True and not report.own_beats(f) and "left out" in (f.get("finding") or ""),
          "PR23: and with them left out, no beat of its own -- so no bird", (f.get("finding") or str(found.no_power))[:120])


def test_pr135_flock():
    """PR135 (the paper, 2026-10-08's standard): the six birds A-F on the paper's tracks, frames 1240-1389, as the
    members of one group. Each beats at its wingbeat -- the paper's 7.85, 7.38, 7.85, 7.11, 7.64 and 7.60 Hz, read over
    the whole track, as the stage's whole-track peak is -- out of step with the others: theirs, past the drift and the
    lost frames held against them since 2026-10-09. And since 2026-10-17 (ROADMAP.md 0.3 objective 2) each frequency
    has its error, a fraction of the resolution, and the codec's mark is held to it: the 2-s windows of the four
    members within half a hertz of the clip's 7.49-Hz line, which that mark at the resolution refused every one of,
    beat; where a window is clearer than the whole track the stage reports it (E's clearest, 7.90 Hz)."""
    print("\nPR135, frames 1240-1389 -- the paper's six birds beat as a flock")
    import csv
    video, why = have_clip("PR135")
    tracks_csv = GOLDEN / "pr135_tracks.csv"
    if video is None:
        print(f"  SKIP  {why}")
        SKIP.append("PR135 flock")
        return
    tracks = {}
    for r in csv.DictReader(open(tracks_csv, encoding="utf-8")):
        if 1240 <= int(r["frame"]) <= 1389 and r["x"] and r["y"]:
            tracks.setdefault(f"member {r['letter']}", {})[int(r["frame"])] = (float(r["x"]), float(r["y"]))
    f = _flicker(video, tracks, 1240, 1389).fields
    paper = {"A": 7.85, "B": 7.38, "C": 7.85, "D": 7.11, "E": 7.64, "F": 7.60}
    whole = {k[-1]: c for k, c in (f.get("curves") or {}).items() if c and k.startswith("member ")}   # not the apertures beside them
    check(f["beats"] is True and sorted(f.get("strong") or []) == sorted(tracks),
          "PR135: the six beat, each its own (out of step), every one past its own tests", (f.get("finding") or "")[:100])
    check(all(abs(whole[L]["hz"] - hz) <= 0.25 for L, hz in paper.items() if L in whole) and len(whole) == 6,
          "PR135: each at the paper's wingbeat over the whole track, to a quarter of a hertz",
          ", ".join(f"{L} {whole[L]['hz']:.2f}/{hz}" for L, hz in paper.items() if L in whole))
    res = 30000 / 1001 / 150                               # 1/T over the 150 frames
    check(all(c.get("hz_err") is not None and 0.005 <= c["hz_err"] <= 0.75 * res for c in whole.values()),
          f"PR135: and each with its error, under three quarters of the resolution ({res:.2f} Hz)",
          ", ".join(f"{L} ±{c['hz_err']:.3f}" for L, c in sorted(whole.items())))
    beat = {k[-1]: b for k, b in (f.get("beat") or {}).items()}
    near = [L for L in "ABEF" if L in beat]
    check(len(near) == 4 and all(beat[L]["windows_passing"] > 0 and beat[L].get("windows_passing_by_resolution") == 0 for L in near),
          "PR135: A, B, E and F, within half a hertz of the codec's line, now beat in 2-s windows; by the mark at the resolution none did",
          ", ".join(f"{L} {beat[L]['windows_passing']}/{beat[L]['windows']} (was {beat[L].get('windows_passing_by_resolution')})" for L in near))
    ob = ((f.get("seis") or {}).get("member B") or {}).get("onebit") or {}
    check(ob.get("hz") is not None and ob.get("at_the_codec_line_hz") is None and abs(ob["hz"] - 7.493) <= res,
          "PR135: B's one-bit reading, inside the resolution of the line, is clear of it by its error (the survey's example)",
          f"{ob.get('hz', 0):.3f} ± {ob.get('hz_err') or 0:.3f} Hz, codec {ob.get('at_the_codec_line_hz')}")
    st = {k[-1]: s for k, s in (f.get("steadiness") or {}).items() if k.startswith("member ")}
    check(len(st) == 6 and all(s.get("power") and s.get("p") is not None for s in st.values()),
          "PR135: each member's steadiness is read against steady clocks over its stretch (item 12)",
          ", ".join(f"{L} " + (f"p {s['p']:.3f}" if s.get("p") is not None else f"not read ({s.get('why')})") for L, s in sorted(st.items())))
    check(sum(bool(s.get("wanders")) for s in st.values()) >= 3,
          "PR135: and at least half of them wander more than a clock can (the information-theory survey: 2.4-5.0 % "
          "between halves; the case files, 2026-10-19: p 0.005-0.035)",
          ", ".join(f"{L} {100 * (s.get('wander_share') or 0):.1f} % (p {s['p']:.3f})" if s.get("p") is not None else f"{L} not read"
                    for L, s in sorted(st.items())))


GALILEO_BEATS = {1: 3.36, 2: 4.49, 3: 10.04, 4: 3.85}    # the paper's Fig. 3 (flyer 5 has its own test, its double named)


def test_galileo_flyers_beat():
    """Galileo Project Dalek flyers 1-4 (Jacob's bird controls; 60 fps IR, a camera that does not move): on the
    paper's tracks each beats within half a hertz of the paper's wingbeat -- or of its double -- past the drift
    and the lost frames held against it since 2026-10-09 (and at the paper's 0.5-s running mean, 30 frames at
    60 fps, not 15)."""
    print("\nGalileo flyers 1-4 -- the paper's wingbeats")
    import csv
    clips = GOLDEN / "galileo_clips.csv"
    if not clips.exists():
        print("  SKIP  the Galileo clips are not on this computer")
        SKIP.append("Galileo flyers 1-4")
        return
    rows = {int(r["flyer"]): r for r in csv.DictReader(open(clips, encoding="utf-8"))}
    for k, hz in GALILEO_BEATS.items():
        video, track_csv = GALILEO / rows[k]["clip"], GOLDEN / f"flyer{k}_paper_track.csv"
        if not video.exists() or not track_csv.exists():
            print(f"  SKIP  flyer {k}: {video.name} or its track is not on this computer")
            SKIP.append(f"flyer {k}")
            continue
        off = int(rows[k]["src_frame0"])
        track = {int(r["frame"]) - off: (float(r["x"]), float(r["y"])) for r in csv.DictReader(open(track_csv, encoding="utf-8"))}
        f = _flicker(video, {"object": track}, min(track), max(track)).fields
        b = (f.get("beat") or {}).get("object") or {}
        near = [v for v in (b.get("hz"), b.get("double_hz"), b.get("hz", 0) / 2) if v]
        check(f["beats"] is True and any(abs(v - hz) <= 0.5 for v in near),
              f"flyer {k}: its brightness beats at the paper's {hz} Hz", f"{b.get('hz', 0):.2f} Hz, double {b.get('double_hz')}; "
              f"{(f.get('finding') or '')[:70]}")


def test_wa9ony5_no_beat():
    """WA9ONY-5, a pico balloon whose payload swings (the tether test's clip): the stage had called its brightness a beat
    at 1.53 Hz -- the band's edge, the flank of the swing's slower change -- from five of its 2-s windows. It is lost
    against the sky on a quarter of its frames, and no beat is looked for; and there is none."""
    print("\nWA9ONY-5, 85.8-90.0 s -- a balloon has no beat")
    video = reference_data.footage() / "tl8_etApsro.mp4"
    if not video.exists():
        print(f"  SKIP  {video} is not on this computer")
        SKIP.append("WA9ONY-5 no beat")
        return
    from mcdonald import report, forensics as vf
    track = vf.read_track(HERE / "golden" / "wa9ony5_balloon_track.csv")
    found = _flicker(video, {"object": track}, min(track), max(track), dark=True)
    check(found.fields["beats"] is not True and not report.own_beats(found.fields),
          "WA9ONY-5: no beat of its own", (found.fields.get("finding") or str(found.no_power))[:120])


def test_pr144_window():
    """PR144 is the clip every one of these routines was derived from, and the
    one whose published rate was wrong before layers were separated."""
    print("\nPR144, frames 300-500 -- layer separation")
    video, why = have_clip("PR144")
    if not video:
        print(f"  SKIP  {why}")
        SKIP.append("PR144 window")
        return
    with tempfile.TemporaryDirectory() as td:
        out = run(["layers", str(video),
                   "--track", str(HERE / "golden" / "pr144_track.csv"),
                   "--names", "striated=sea,isotropic=cloud tops",
                   "--dark-below", "100", "--mask-rows", "985:1080:1:165",
                   "--n0", "300", "--n1", "500", "--out", td, "--fresh", "--json"], td)
    got = fields(out, "PR144/300-500")
    compare(got, WINDOW_BASELINE, "PR144/300-500")
    check(got.get("object vs sea", 0) - got.get("object vs cloud tops", 0) > 50,
          "PR144/300-500: the two layers are still distinguishable",
          "a single blended rate would be the regression this test exists to catch")


def test_pr144_full():
    """The published whole-clip numbers (docs/method.md section 4)."""
    print("\nPR144, whole clip -- the published values")
    video, why = have_clip("PR144")
    if not video:
        print(f"  SKIP  {why}")
        SKIP.append("PR144 full")
        return
    with tempfile.TemporaryDirectory() as td:
        out = run(["layers", str(video),
                   "--track", str(HERE / "golden" / "pr144_track.csv"),
                   "--names", "striated=sea,isotropic=cloud tops",
                   "--dark-below", "100", "--mask-rows", "985:1080:1:165",
                   "--out", td, "--fresh", "--json"], td)
    compare(fields(out, "PR144/full"), PUBLISHED, "PR144/full")


def _tether(video, track_file, **kw):
    """`tether.measure` on a vendored track, frames extracted into a temporary directory."""
    from mcdonald import forensics as vf, tether
    track = vf.read_track(str(HERE / "golden" / track_file))
    with tempfile.TemporaryDirectory() as td:
        clip = vf.Clip(video, f"{td}/frames", min(track), max(track))
        return tether.measure(clip, track, out=f"{td}/case", say=lambda line: None, **kw)


def test_pr071_string():
    """PR071, the Lake Huron object: a dark line hangs from it on most frames, steady -- no length."""
    print("\nPR071, frames 367-603 -- a line hangs from the object, and does not swing")
    video, why = have_clip("PR071")
    if video is None:
        print(f"  SKIP  {why}")
        SKIP.append("PR071 string")
        return
    f = _tether(video, "pr071_object_track.csv", r_max=6.0)
    c = f.fields["companion"]
    check(c is not None and c["sign"] == "dark", "PR071: a dark feature moves with the object",
          "" if c is None else f"{c['r_over_size']:.1f} sizes at {c['direction_deg']:+.0f} deg")
    check(c is not None and 1.2 <= c["r_over_size"] <= 2.6 and -35 <= c["direction_deg"] <= 0,
          "PR071: below it, a little to the left")
    check(c is not None and (c["seen_on_frames"] or 0) >= 0.5 and c["jitter_px"] is not None and c["jitter_px"] <= 6,
          "PR071: on most single frames, at the same place",
          "" if c is None else f"{100 * (c['seen_on_frames'] or 0):.0f}%, jitter {c['jitter_px']}")
    sw = f.fields["swing"]
    check(sw is not None and sw.get("swings") is False and sw["angle_sd_deg"] < 15,
          "PR071: steady, no swing, no length", "" if sw is None else sw["finding"])


def test_pr055_nothing_tied():
    """PR055, the sphere among clouds: the stack's features are the clouds, and move with them."""
    print("\nPR055, frames 1068-1300 -- nothing tied to the sphere")
    video, why = have_clip("PR055")
    if video is None:
        print(f"  SKIP  {why}")
        SKIP.append("PR055 nothing tied")
        return
    f = _tether(video, "pr055_sphere_track.csv", size=24.0)
    check(f.fields["companion"] is None, "PR055: no companion", f.fields["finding"])
    check(any(c.get("scene") for c in f.fields["candidates"]) or "nothing" in f.fields["finding"],
          "PR055: the stack's features were followed and moved with the scene")


def test_wa9ony5_swing():
    """WA9ONY-5, a pico balloon with a 13 g payload 'a little over one metre' below: the swing gives
    the line. Needs the clip: YouTube id tl8_etApsro, saved as footage/tl8_etApsro.mp4 in the reference-data folder
    (yt-dlp -f "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b" -o "%(id)s.%(ext)s" ...)."""
    print("\nWA9ONY-5, 85.8-90.0 s -- the payload swings, and the swing gives the line")
    video = reference_data.footage() / "tl8_etApsro.mp4"
    if not video.exists():
        print(f"  SKIP  {video} is not on this computer")
        SKIP.append("WA9ONY-5 swing")
        return
    f = _tether(video, "wa9ony5_balloon_track.csv", r_max=12.0)
    c, sw = f.fields["companion"], f.fields["swing"]
    check(c is not None and c["sign"] == "dark" and 2 <= c["r_over_size"] <= 8, "WA9ONY-5: the payload moves with the balloon",
          "" if c is None else f"{c['r_over_size']:.1f} sizes, z {c['z']:.1f} vs {c['z_control']:.1f} on the control")
    check(sw is not None and sw.get("swings") is True and sw.get("tentative") is True, "WA9ONY-5: it swings, tentatively (1.7 cycles)",
          "" if sw is None else f"{sw.get('cycles', 0):.1f} cycles")
    check(sw is not None and sw.get("period_used_s") and 2.4 <= sw["period_used_s"] <= 2.8,
          "WA9ONY-5: period 2.4-2.8 s", "" if sw is None else f"{sw.get('period_used_s')}")
    check(sw is not None and sw.get("line_length_m") and 1.4 <= sw["line_length_m"] <= 1.95,
          "WA9ONY-5: a pendulum of 1.4-1.95 m (the line, the balloon's radius and the payload's offset)",
          "" if sw is None else f"{sw.get('line_length_m')} m")


def _audio(path, **kw):
    from mcdonald import audio
    return audio.measure(path, **kw).fields


def _airframes(f):
    """[(airframe's first word, how it was read, companion ratio heard or None)] of a sound track's fields."""
    fam = f.get("families") or {}
    out = []
    for s in fam.get("series", []):
        for m in (s.get("propeller") or {}).get("matches_in_flight", []):
            if not m.get("identified"):                 # a blade-pass without its second tone identifies nothing
                continue
            c = m.get("companion") or {}
            out.append((m["airframe"].split()[0], "series", c.get("ratio_heard") if c.get("found_hz") else None))
    for m in fam.get("single", []):
        c = m.get("companion") or {}
        out.append((m["airframe"].split()[0], "single", c.get("ratio_heard") if c.get("found_hz") else None))
    return out


def test_flyover_cases():
    """A source passing a microphone, its speed and closest range from its Doppler curve (`audio.flyover`): two
    Connecticut ANG C-130Hs over a camera (DVIDS 752745, May 2020, four-bladed 54H60s), the T56's in-flight 68.06 Hz
    held; and two Dash 8-300s on the approach to Adelaide (AeroSonicDB), the rest tone free, their closest range
    against the ADS-B altitude at the start of the recording (which a descending approach sits a little under)."""
    print("\na source passing the microphone -- speed and closest range")
    from mcdonald import audio
    p = reference_data.aircraft_audio() / "dvids_752745.m4a"
    if not p.exists():
        print(f"  SKIP  {p} is not here")
        SKIP.append("flyover DVIDS 752745")
    else:
        for t0, dur in ((41.0, 7.3), (58.0, 6.6)):
            r = audio.flyover(audio.decode(p, t0, dur, fs=audio.FLY_FS), 52, 100, rest_hz=68.06)
            check(r is not None and 180 <= r["v_kn"] <= 260 and 250 <= r["r0_m"] <= 600 and r["rms_hz"] < 0.7,
                  f"DVIDS 752745 at {t0:g} s: a C-130H flyover's speed and range, 68.06 Hz held",
                  f"{r and (r['v_kn'], r['r0_m'], r['rms_hz'])}")
    root = reference_data.root() / "aerosonicdb" / "audio"
    for name, t0, dur, alt_ft in (("7C627C_2023-04-17_15-36-20_0_1.wav", 5.0, 44.0, 2700),
                                  ("7C6277_2023-04-22_11-33-28_0_1.wav", 0.0, 50.0, 2875)):
        hits = list(root.rglob(name)) if root.exists() else []
        if not hits:
            print(f"  SKIP  AeroSonicDB {name} is not here")
            SKIP.append(f"flyover {name}")
            continue
        r = audio.flyover(audio.decode(hits[0], t0, dur, fs=audio.FLY_FS), 40, 400)
        ratio = r and r["r0_ft"] / alt_ft
        check(r is not None and 0.8 <= ratio <= 1.15 and 150 <= r["v_kn"] <= 240 and abs(r["f0_hz"] - 60.6) < 1.0,
              f"AeroSonicDB {name[:6]}: a Dash 8-300's closest range against its ADS-B altitude ({alt_ft} ft), rest tone free",
              f"{r and (r['f0_hz'], r['v_kn'], r['r0_ft'], round(ratio, 2))}")


def test_audio_cases():
    """The sound tracks with a known reading (the aviation methods survey, 2026-10-16): the Gulf of Oman phone
    captures are a T56 C-130 in flight with its second tone at 8.13x; DVIDS cabins of known type in known phases
    of flight read as themselves; PR106/PR107 carry the 400-Hz bus, PR113 the mains and the NTSC frame clock, PR39 the
    codec; and a C-130J on the ground, PR113's 68.92 Hz and PR39's 101.37 Hz are no reading."""
    print("\nsound tracks -- propellers, supplies, the codec")
    t56 = [("PR117", {}), ("PR118", {}), ("PR119", {})]
    for rid, kw in t56:
        path, why = have_clip(rid)
        if path is None:
            print(f"  SKIP  {why}")
            SKIP.append(f"audio {rid}")
            continue
        a = _airframes(_audio(path, **kw))
        check(len(a) == 1 and a[0][0] == "C-130" and a[0][2] and abs(a[0][2] - 8.129) < 0.01,
              f"{rid}: a T56 C-130 in flight, its second tone at 8.13x", f"{a}")
    for rid, lo, hi in (("PR106", 399.5, 399.9), ("PR107", 399.6, 399.9)):
        path, why = have_clip(rid)
        if path is None:
            print(f"  SKIP  {why}")
            SKIP.append(f"audio {rid}")
            continue
        f = _audio(path)
        b = (f.get("families") or {}).get("bus")
        check(b is not None and lo <= b["f0_hz"] <= hi, f"{rid}: the 400-Hz bus at {lo}-{hi} Hz", f"{b and b['f0_hz']}")
        check(not (f.get("families") or {}).get("mains") and not _airframes(f), f"{rid}: no mains, no airframe")
    path, why = have_clip("PR113")
    if path is None:
        print(f"  SKIP  {why}")
        SKIP.append("audio PR113")
    else:
        f = _audio(path)
        fam = f.get("families") or {}
        m = fam.get("mains")
        check(m is not None and m["nominal_hz"] == 60 and 60.005 <= m["f0_hz"] <= 60.020,
              "PR113: 60-Hz mains at its own frequency (60.011), apart from the field rate", f"{m and m['f0_hz']}")
        fr = fam.get("frame") or {}
        check(fr.get("ntsc") and fr.get("field_hz") and abs(fr["field_hz"] - 59.944) < 0.01,
              "PR113: its NTSC frame clock and field rate (59.944) are heard", f"{fr.get('hz')}, {fr.get('field_hz')}")
        check(fam.get("bus") is None and fam.get("bus_possible") is not None,
              "PR113: its 400-Hz power is possible, not shown (x3, x6, x9 are the field comb's)")
        check(not _airframes(f), "PR113: its 68.92-Hz line is no airframe", f"{_airframes(f)}")
    flir = reference_data.root() / "aaro" / "videos" / "DOD_110872545-1920x1080-9000k.mp4"
    if not flir.exists():
        print(f"  SKIP  AARO's FLIR video is not in {flir.parent}")
        SKIP.append("audio FLIR")
    else:
        f = _audio(flir)
        fam = f.get("families") or {}
        fr, b = fam.get("frame") or {}, fam.get("bus") or {}
        r = b.get("refined") or {}
        check(fr.get("ntsc") and fr.get("field_hz") and abs(fr["field_hz"] - 59.935) < 0.01,
              "FLIR (AARO): its 59.94-Hz line is the video's field rate", f"{fr.get('field_hz')}")
        check(abs((b.get("f0_hz") or 0) - 399.095) < 0.01 and not r.get("pulldown_if"),
              "FLIR (AARO): its 400-Hz power at 399.095 Hz, fitted harmonic by harmonic", f"{b.get('f0_hz')}")
        m = fam.get("mains") or {}
        check(m.get("grid") is False and abs(m.get("f0_hz", 0) - 60.32) < 0.02,
              "FLIR (AARO): an odd-harmonic power hum at 60.32 Hz, not a grid's", f"{m.get('f0_hz')}, grid {m.get('grid')}")
    path, why = have_clip("PR39")
    if path is None:
        print(f"  SKIP  {why}")
        SKIP.append("audio PR39")
    else:
        f = _audio(path)
        c = (f.get("families") or {}).get("codec") or []
        check(any(q["sample_rate"] == 48000 for q in c), "PR39: AAC frame products at 48 kHz", f"{[q['what'] for q in c]}")
        check(not _airframes(f), "PR39: its 101.37-Hz line is no airframe", f"{_airframes(f)}")
    controls = [("dvids_387408.m4a", dict(t0=90, seconds=116), "C-130", 8.129, "T56 AC-130H/U in flight"),
                ("dvids_387446.m4a", dict(t0=70), "C-130", 8.129, "T56 AC-130H/U in flight"),
                ("dvids_826283.m4a", dict(t0=62, seconds=158), "C-130J", 5.390, "AC-130J in flight, live fire"),
                ("dvids_1016616.m4a", dict(t0=100), "C-130J", 5.390, "AC-130J in flight, RIMPAC"),
                ("dvids_1012667.m4a", dict(t0=48, seconds=20), "C-130J", 5.390, "C-130J cockpit in flight"),
                ("dvids_1012745.m4a", dict(seconds=38), None, None, "C-130J on the ground at idle"),
                ("nasa_d026_0-900s.m4a", dict(), None, None, "Apollo 14 debriefing tape (mains sidebands at 67.7 Hz)"),
                ("dvids_878819.m4a", dict(), "H-60", 4.611, "UH-60 in flight, aerial gunnery"),
                ("dvids_776121.m4a", dict(), None, None, "MQ-9 heard from the ground (blade-pass over a T56's, second tone 9.00x)")]
    for name, kw, frame, ratio, what in controls:
        path = reference_data.aircraft_audio() / name
        if not path.exists():
            print(f"  SKIP  {path} is not on this computer")
            SKIP.append(f"audio {name}")
            continue
        a = _airframes(_audio(path, **kw))
        if frame is None:
            check(not a, f"{what}: no reading", f"{a}")
        else:
            check(len(a) == 1 and a[0][0] == frame and a[0][2] and abs(a[0][2] - ratio) < 0.01,
                  f"{what}: read as {frame}, its second tone at {ratio:.2f}x", f"{a}")


def main():
    full = "--full" in sys.argv
    print("McDonald UAP Toolkit — golden check against real clips")
    print(f"catalog: {catalog.active().name}; reference data: {reference_data.root()}")
    test_pr113_two_clicks()
    test_pr144_window()
    test_pr43_streak_by_motion()
    test_flyer5_wingbeat()
    test_pr23_no_bird()
    test_pr135_flock()
    test_galileo_flyers_beat()
    test_wa9ony5_no_beat()
    test_pr071_string()
    test_pr055_nothing_tied()
    test_wa9ony5_swing()
    test_audio_cases()
    test_flyover_cases()
    if full:
        test_pr144_full()
    else:
        print("\n(--full also checks the whole-clip published values; tens of minutes)")

    if FAIL:
        print(f"\n{len(FAIL)} FAILED: {', '.join(FAIL)}")
        return 1
    print(f"\n{'ALL PASS' if not SKIP else 'ALL PASS (skipped: ' + ', '.join(SKIP) + ')'}")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):           # a pipe or a log file on Windows is cp1252, and the checks' names have arrows
        _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
