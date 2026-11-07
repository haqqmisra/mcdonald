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
             in docs/method.md -- tens of minutes -- and the exercises.
  --exercises  each exercise in docs/exercises, run as its page writes it, against
             the answer the page gives (PR44, PR149, PR113 and PR135: about 75 minutes on
             four CPUs); a page's number after it (--exercises 03) runs that page alone,
             and nothing else.
"""
import json
import math
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
    every frame it is in, 50-74, within 1.4 px of both marks. Frame 53 has no point, as before. Until 2026-10-30 it also took
    frame 75, a faint blob 9 px behind frame 74's position after the dash had left the picture: 25 points, the one
    that set the track's 8-px jitter (`autolink.MOTION_BACK`)."""
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
    check(L.track and min(L.track) == 50 and max(L.track) == 74 and len(L.track) == 24 and 53 not in L.track,
          "PR43: on the frames the thing is in, 50-74, and not on the frame after it left the picture",
          f"{len(L.track)} frames {min(L.track) if L.track else '-'}–{max(L.track) if L.track else '-'}")
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
    p = f.get("pictures") or {}
    check(p.get("held", 0) >= flicker.HELD_MIN and p.get("cadence") is False and abs(p.get("top_hz", 0) - 24.0) <= 0.01,
          "flyer 5: a third of its frames repeat, where the HEVC encoder skips a still sky -- not a cadence, so the band's top "
          "is the frame grid's 24 Hz, not 16.5 (M3)", f"{p.get('held', 0):.2f} held, {p.get('holds')}, balance {p.get('balance')}, "
          f"top {p.get('top_hz')} Hz")


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


def test_exercises(only=None):
    """docs/exercises (Jacob, 2026-10-20): what testers check their own work against. Each page's command-line steps
    are run as the page writes them (with --json, to read them), in a storage folder of their own that holds the video
    already, so nothing is downloaded: `look --propose`, then the line it prints to take its first row -- which must be
    the line the page shows, shortened -- with the reason finished, then `run`. Its report must start as the page
    quotes it, word for word, and the link say what the page says it says. A page that gives what is known goes on to
    `report` with it (the window's "Work out the speed"), and that report must start as the page quotes it too. The
    window's one press is the same job (stages.run_case, the same stages: integrity off), and gave the same reports in
    the real window when each page was written. A page of several objects (exercise 4, PR135, 2026-10-21) shows a
    line for each row `look --propose --objects N` prints, each with `--out` a folder of its own, and `run --each`:
    each object's report must start as the page quotes it (but one the list counts as another, which its first line
    names), and the list's first line be the page's. About 30 minutes for PR44, 12 for PR149, 4 for PR113 and 35 for
    PR135 on four CPUs, so it runs with --full or --exercises; `only`, pages' numbers ("03"), runs those pages and
    nothing else (`--exercises 03`)."""
    import re
    import shlex
    import shutil
    from test_reduction import exercise_commands
    for page in sorted((HERE.parent / "docs" / "exercises").glob("[0-9][0-9]-*.md")):
        if only and page.name[:2] not in only:
            continue
        text = page.read_text(encoding="utf-8")
        section = text.split("## On the command line", 1)[1].split("\n## ", 1)[0]
        steps = [c for c in exercise_commands(section) if c.split()[1] in ("look", "run", "report")]
        shown = [c for c in exercise_commands(section) if c.startswith("mcdonald mark ")]     # a row each, in order
        said_ = re.search(r'(?:It|They) should say\s+((?:"[^"]+"(?:,\s*|,?\s+and\s+)?)+)', section)
        links = re.findall(r'"([^"]+)"', said_.group(1)) if said_ else []                    # what each link says
        name = steps[0].split()[2]
        print(f"\n{page.name} -- {name}, its command-line steps as the page writes them")
        video, why = have_clip(name)
        if not video:
            print(f"  SKIP  {why}")
            SKIP.append(page.name)
            continue
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as td:
            home, work = Path(td) / "home", Path(td) / "work"
            (home / "videos").mkdir(parents=True)
            work.mkdir()
            try:
                (home / "videos" / video.name).symlink_to(video)
            except OSError:                       # Windows without the right to make links
                shutil.copy(video, home / "videos" / video.name)
            env = {**os.environ, "PYTHONPATH": str(HERE.parent / "src"), "MCDONALD_HOME": str(home),
                   "MCDONALD_NO_UPDATE_CHECK": "1"}
            env.pop("MCDONALD_CATALOG", None)     # the list the package ships, as a tester has it

            def mcdonald(words):
                r = subprocess.run([sys.executable, "-m", "mcdonald.cli"] + words + ["--json"], capture_output=True,
                                   text=True, cwd=work, env=env)
                if r.returncode != 0:
                    print(r.stderr[-2000:], file=sys.stderr)
                    raise SystemExit(f"mcdonald {' '.join(words)} exited {r.returncode}")
                return json.loads(r.stdout), r.stderr
            for step in steps:
                got, said = mcdonald(shlex.split(step)[1:])
                if step.split()[1] in ("run", "report"):        # each report it writes starts as the page quotes it
                    r = got["results"]
                    for o in [o for o in r["objects"] if not o.get("same_as")] if "objects" in r else [r]:   # one counted as another: the list's line
                        quoted = f"> **{o['conclusion']['label']}.** {o['conclusion']['headline']}"
                        check(quoted in text, f"{page.name}: after `mcdonald {step.split()[1]}` the report "
                              + (f"of object {o['object']} " if "object" in o else "") + "starts as the page quotes it", quoted)
                    if (r.get("tally") or {}).get("sentence"):
                        check(r["tally"]["sentence"] in text, f"{page.name}: the list's first line is the page's",
                              r["tally"]["sentence"])
                if step.split()[1] == "look":
                    props = got["results"]["proposals"]
                    check(len(shown) <= len(props), f"{page.name}: `look` lists a row for each line the page shows",
                          f"{len(props)} rows, {len(shown)} lines")
                    for i, line in enumerate(shown[:len(props)]):
                        line, out = re.fullmatch(r"(.*?)((?:\s+--out\s+\S+)?)", line).groups()
                        take = props[i]["to_accept"]
                        pieces = [p.strip() for p in line.split("…")]
                        check(all(p in take for p in pieces), f"{page.name}: the line `look` prints to take row {i + 1} is "
                              "the one the page shows", take[:160])
                        marked, said = mcdonald(shlex.split(take.replace("because ...", "because the page says so"))[1:]
                                                + shlex.split(out))
                        link = links[i] if i < len(links) else None
                        check(link is not None and link in said + json.dumps(marked, ensure_ascii=False),
                              f"{page.name}: the link of row {i + 1} says what the page says", link or "the page quotes nothing")


def test_checklist_on_the_case_files():
    """The checklist (Ravi, 2026-11-01) on every object of every reference case file: each row answered in one of its five
    words, with why; PR135's bird as the standard -- whether the camera moved not measured (its picture held still on screen,
    which the layers step cannot tell from a following camera; 0.4.2), the object moves across the picture, not straight and
    steady, beats as a wingbeat does, something moves with it, none of integrity's checks could decide, no real speed, the
    track not yet checked by eye."""
    print("\nthe checklist on the reference case files")
    import zipfile
    from mcdonald.report import ANSWERS, CANT, CHECKS, Case, NO, NOT_YET, YES
    folder = reference_data.root() / "cases"
    files = sorted(folder.glob("*.mcdonald")) if folder.exists() else []
    if not files:
        print(f"  SKIP  no case files in {folder}")
        SKIP.append("checklist on the case files")
        return
    seen, bad, tables = {}, [], 0
    with tempfile.TemporaryDirectory() as td:
        for path in files:
            with zipfile.ZipFile(path) as z:
                for name in sorted(n for n in z.namelist() if n.endswith("_case.json")):
                    out = Path(td) / path.stem / name
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(z.read(name))
                    c = Case.load(out)
                    rows = c.checklist()
                    seen[f"{path.stem}/{name.split('/')[-2]}"] = {r["key"]: r for r in rows}
                    bad += [f"{path.stem}: {r}" for r in rows if r["answer"] not in ANSWERS or not r["said"] or "|" in r["said"]
                            or r["test"] != CHECKS[r["key"]]]
                    md = c.markdown()
                    tables += "| What was checked | Answer | In short |" in md and md.index("## Conclusion") < md.index("| What was checked")
    check(len(seen) >= 14 and not bad and tables == len(seen),
          f"{len(seen)} objects in {len(files)} case files: every row answered in one of the five words, with why, and the table under "
          "each conclusion", "; ".join(bad[:3]))
    pr135 = seen.get("pr135/object-1") or {}
    want = dict(video=NO, camera=CANT, moves=YES, straight=NO, closing=CANT, beat=YES, lookalike=YES, flash=NO, added=CANT, real=NO, chosen=YES, checked=NOT_YET)
    want["with"] = YES
    check(all(pr135.get(k, {}).get("answer") == a for k, a in want.items()) and pr135.get("beat", {}).get("said", "").startswith("7.8 times a second")
          and pr135.get("moves", {}).get("said") == "about 103 pixels a second across the picture, which held still"
          and "whether the camera moved is not measured" in pr135.get("camera", {}).get("said", ""),
          "PR135 object 1: whether the camera moved is Can't tell (0.4.2: its picture held still on screen, the layers step's own no-power, which a camera "
          "following the bird over an empty sky gives too; 0.4.1 said No), it moves 103 pixels a second across the picture (0.4.1: that step gives no rate "
          "against the background there), not straight and steady, beats 7.8 times a second as a wingbeat does, a bright feature moves with it, none of "
          "integrity's checks could decide, no real speed, the track not yet checked", str({k: r["answer"] for k, r in pr135.items()}))
    held = {k: v["camera"]["answer"] for k, v in seen.items() if "camera" in v}
    check(held and NO not in held.values() and held.get("pr144/object-1") == YES and held.get("pr43/object-1") == YES
          and held.get("pr113/object-1") == "Partly" and held.get("pr097/object-6") == "Partly",
          "no reference object answers No to the camera's question: Yes where the background moved (PR144, PR43), Partly where the picture "
          "held in no more than half the pairs (PR113, PR097's object 6), Can't tell on the rest", str(held))
    moved = seen.get("pr149/object-1") or {}
    check(moved.get("camera", {}).get("answer") == YES and moved.get("moves", {}).get("answer") == CANT
          and moved.get("real", {}).get("answer") == "Partly" and "115 m/s" in moved.get("real", {}).get("said", ""),
          "PR149: the camera moved, so its rate against the background is Can't tell; the ship of known size gives a Partly",
          str({k: r["answer"] for k, r in moved.items()}))


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
        p = f.get("pictures") or {}
        check(p.get("cadence") is False and abs(p.get("top_hz", 0) - 24.0) <= 0.01,
              f"flyer {k}: what repeats is the encoder's, not a cadence -- the band's top the frame grid's 24 Hz (M3)",
              f"{p.get('held', 0):.2f} held, {p.get('holds')}, balance {p.get('balance')}, top {p.get('top_hz')} Hz")


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


def test_pr43_speed_band():
    """PR43's streak (the Technical Note: a rate rising from about 7 to 33 px/frame over frames 50-75), on the track
    its reference case file holds: `fit_v_px` refuses it as not uniform; the speed band (docs/method.md section 32)
    describes it -- the least and the most along the track where the Note's figures are, the velocity's change over
    the stretch many sigmas from zero."""
    print("\nPR43 -- the speed band on the streak's track")
    import csv
    import io
    import zipfile
    from mcdonald import kinematics as kin
    path = reference_data.root() / "cases" / "pr43.mcdonald"
    if not path.exists():
        print(f"  SKIP  {path} is not here")
        SKIP.append("PR43 band")
        return
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.endswith("pr43_autotrack.csv"))
        rows = list(csv.DictReader(l for l in io.StringIO(z.read(name).decode("utf-8")) if not l.startswith("#")))
    track = {int(float(r["frame"])): (float(r["x_px"]), float(r["y_px"])) for r in rows if r["x_px"] not in ("", "nan")}
    # The case file of 0.3.0 holds frame 75, a blob behind frame 74's position after the dash had left the picture (2026-10-30).
    # The link no longer takes it (`autolink.MOTION_BACK`, test_pr43_streak_by_motion); until the strict rerun rewrites the
    # case, it is left out here. It set this track's jitter at 8.0 px and its T at 0.91 ± 0.10 s
    track.pop(75, None)
    fit = kin.fit_v_px(track, 30.0)
    band, _ = kin.speed_band(track, 30.0)
    check(not fit["uniform"] and not band["constant"], "the line refuses it; the band describes it",
          f"residual {fit['resid_frac']:.0%} of the span; dlnl {band['dlnl']:.0f}")
    check(band["v_min"][1] / 30.0 < 14 and band["v_max"][1] / 30.0 > 28,
          "the least and the most along the track are where the Note's 7 and 33 px/frame are",
          f"{band['v_min'][1] / 30:.1f} to {band['v_max'][1] / 30:.1f} px/frame")
    check(band["accel_z"] >= 3 and band["v_end"][1] > band["v_start"][1],
          "the velocity's change over the stretch is many sigmas from zero, and it speeds up",
          f"{band['accel_px_per_s2']:.0f} ± {band['accel_err_px_per_s2']:.0f} px/s², {band['accel_z']:.1f} sigma")
    check(2 < max(band["nugget_px"]) < 9, "a streak's centroid jitters by pixels, not tenths", f"nugget {max(band['nugget_px']):.1f} px")
    # what survives (section 33): the Note's constant-velocity hypothesis on PR43 (the research repository's case note,
    # 2026-08-05: straight to 1.4 px, t_z 3.34 s on its 18 detections, the vanishing point inside the frame, theta 34° at
    # a 65.6° field) and the kinematic notes' turn radius (> 1,900 body widths at a 4.27-px width)
    from mcdonald import projective as pj
    f = pj.fit(track, 30.0, k=1920 / math.radians(65.6), centre=(960.0, 540.0))
    check(f["closing"] is True and f["straight_rms"] < 2.0 and 3.1 < f["t_z"] < 3.3 and 0.7 < f["T"] < 0.85,
          "PR43 passes the projective constant-velocity test: straight, closing, crossing the camera's plane under a second after its last frame",
          f"straight {f['straight_rms']:.1f} px, t_z {f['t_z']:.2f} s ({f['t_z_band'][0]:.2f}-{f['t_z_band'][1]:.2f}), T {f['T']:.2f} s")
    check(f["fits"] is True and f["misfit"] < 2.0, "and the model is held to the streak's own jitter: it fits to it (1.3, on 24 points)",
          f"{f['rms']:.1f} px rms, {f['misfit']:.2f} times its jitter ({f['jitter_px']:.2f} px)")
    # t_z's error under the streak's own covariance (M5's other half, 2026-10-30; two ranges of wander since 2026-10-31): about
    # 0.04 s on the 24 points, where frame 75 made it 0.48 (and the first covariance 0.10, the residual bootstrap about 0.07):
    # almost all of the error was that one point
    check(f["t_z_err"] is not None and 0.02 < f["t_z_err"] < 0.08 and 0.6 < f["T"] - 1.96 * f["t_z_err"] and f["T"] + 1.96 * f["t_z_err"] < 0.95,
          "and its time to the camera's plane has an error from the track's own covariance: under 0.95 s, more "
          "than 0.6 s, at 95 %", f"T {f['T']:.2f} ± {f['t_z_err']:.2f} s (95 % {f['T'] - 1.96 * f['t_z_err']:.2f}-"
          f"{f['T'] + 1.96 * f['t_z_err']:.2f})")
    check(30 < f["psi_deg"] < 40 and 0 < f["vp"][0] < 1920 and 0 < f["vp"][1] < 1080,
          "the vanishing point inside the frame; at a 65.6° field the aspect angle is the Note's 34°", f"psi {f['psi_deg']:.1f}°, vp ({f['vp'][0]:.0f}, {f['vp'][1]:.0f})")
    tn = pj.turn(track, 30.0, 4.27)
    check(tn["r_turn_over_D"] > 1000 and not tn["turned"], "and its turn radius is over a thousand body widths: it did not manoeuvre",
          f"{tn['r_turn_over_D']:.0f} ({'bent' if tn['bent'] else 'straight'})")


def test_the_birds_bands_held_to_their_tracks():
    """E1 and M8 (ROADMAP 0.4; docs/method.md section 32) on the birds of the reference set: the band held to its own
    track finds the wingbeat left in its innovations -- PR135's six (the paper's flock) at 7-8 Hz -- and the band fitted
    again with a beat beside its wander holds it there, Ljung-Box's p rising by twenty orders of magnitude and more; what
    is left is slow (the camera's turn at 44.5 s, the economics survey's common break). Galileo flyer 3's beat is held
    too; flyer 1's is tried and left, since with it the band misses more often (a bird that flaps and glides over 14 s:
    a beat fitted in the middle is not the beat at the ends); flyer 5 has no rhythm left to hold."""
    print("\nthe birds' bands held to their own tracks (E1, M8)")
    import csv
    import io
    import zipfile
    from mcdonald import forensics as vf, kinematics as kin
    path = reference_data.root() / "cases" / "pr135.mcdonald"
    if not path.exists():
        print(f"  SKIP  {path} is not here")
        SKIP.append("PR135 backtest")
    else:
        got = []
        with zipfile.ZipFile(path) as z:
            for member in range(1, 7):
                rows = list(csv.DictReader(l for l in io.StringIO(z.read(f"case/object-{member}/pr135_track.csv").decode("utf-8"))
                                           if not l.startswith("#")))
                track = {int(float(r["frame"])): (float(r["x_px"]), float(r["y_px"])) for r in rows if r["x_px"] not in ("", "nan")}
                band, _ = kin.speed_band(track, 30.0)
                got.append(band)
        ok = [b["beat"] and b["beat"]["kept"] and b["beat"]["without"]["light"] != "green"
              and 7.0 < b["beat"]["rhythm_hz"] < 8.5 and all(7.0 < h < 8.5 for h in b["beat"]["hz"] if h)
              and min(b["backtest"]["ljung_box_p"]) > 1e15 * min(b["beat"]["without"]["ljung_box_p"]) for b in got]
        check(all(ok), "PR135's six: the wingbeat is left in the band alone (7-8 Hz), and held beside the wander as a beat",
              "; ".join(f"{min(b['beat']['without']['ljung_box_p']):.0e} -> {min(b['backtest']['ljung_box_p']):.0e} at "
                        f"{[round(h, 1) for h in b['beat']['hz'] if h]} Hz" if b["beat"] else "no beat" for b in got))
        check(sum(any(r.startswith("something slow is left in it") for r in b["backtest"]["reasons"]) for b in got) >= 4,
              "and what is left in most of them is slow: the camera's turn", ", ".join(b["backtest"]["light"] for b in got))
    golden = HERE / "golden"
    b3, _ = kin.speed_band(vf.read_track(golden / "flyer3_paper_track.csv"), 60.0)
    b1, _ = kin.speed_band(vf.read_track(golden / "flyer1_paper_track.csv"), 60.0)
    b5, _ = kin.speed_band(vf.read_track(golden / "flyer5_paper_track.csv"), 60.0)
    check(b3["beat"] and b3["beat"]["kept"] and min(b3["backtest"]["ljung_box_p"]) > 0.01 > min(b3["beat"]["without"]["ljung_box_p"]),
          "Galileo flyer 3: its beat held, nothing left of it", f"{[round(h, 1) for h in b3['beat']['hz'] if h]} Hz" if b3["beat"] else "no beat")
    check(b1["beat"] and not b1["beat"]["kept"] and b1["beat"]["light_with"] == "red" and "so the band keeps its wander alone"
          in kin.backtest_said(b1["backtest"], b1["beat"]),
          "flyer 1: a beat tried and left -- with it the band misses more often over 14 s of flapping and gliding",
          kin.backtest_said(b1["backtest"], b1["beat"])[-160:])
    check(b5["beat"] is None and min(b5["backtest"]["ljung_box_p"]) > 0.01, "flyer 5: no rhythm left to hold",
          kin.backtest_said(b5["backtest"])[:100])


def test_projective_held_to_the_jitter():
    """The projective test's models compared only with one another said which was least wrong, not whether any was
    right (the pure-mathematics survey, 2026-10-29, M1): PR077's object loops through 705° in ten seconds and passed
    "no closing seen", PR135's members 5 and 6 carry the camera's slew and passed "receding". Held to their own jitter
    (the speed band's nugget), the model chosen follows their trend and misses them by tens to hundreds of times it,
    so the test says so and gives no time to the camera's plane."""
    print("\nprojective -- the model held to the track's own jitter (PR077, PR135)")
    import csv
    import io
    import zipfile
    from mcdonald import projective as pj
    for case, member, least in (("pr077", "object-1", 100), ("pr135", "object-5", 30), ("pr135", "object-6", 30)):
        path = reference_data.root() / "cases" / f"{case}.mcdonald"
        if not path.exists():
            print(f"  SKIP  {path} is not here")
            SKIP.append(f"{case} projective")
            continue
        with zipfile.ZipFile(path) as z:
            name = f"case/{member}/{case}_track.csv"
            rows = list(csv.DictReader(l for l in io.StringIO(z.read(name).decode("utf-8")) if not l.startswith("#")))
            fps = json.loads(z.read(next(n for n in z.namelist() if n.startswith(f"case/{member}/") and n.endswith("_case.json"))))["clip"]["fps"]
        track = {int(float(r["frame"])): (float(r["x_px"]), float(r["y_px"])) for r in rows if r["x_px"] not in ("", "nan")}
        f = pj.fit(track, float(fps), boot=0)
        said = pj.said(f)["constant velocity"]
        check(f["closing"] is not None and f["fits"] is False and f["misfit"] > least and "describes its trend" in said
              and "times its own jitter" in said and "camera's plane" in said and "crossed" not in said,
              f"{case.upper()} {member}: the models' own verdict was {'no closing seen' if f['closing'] is False else 'a closing or receding'}; "
              f"held to its jitter, the model follows only the trend", f"{f['misfit']:.0f} times its jitter ({f['jitter_px']:.2f} px)")
        if case == "pr077":
            # its sagitta reads "a hair off straight, about 117 widths" at the 9-px spot it was followed at, and an ellipse 212
            # by 23 px follows it through 585° (M4, 2026-10-30); held to its own wander (2026-10-31) that is no loop: its gain
            # over a wander is 39 and its minor axis 13 +- 20 px, so the words say it swings about and claim nothing more
            tn = pj.turn(track, float(fps), 9.0)
            words = pj.said(None, tn, None)["turn"]
            e = tn["swings"] or {}
            check(tn["how"] == "sagitta" and 20 < e.get("reach_widths", 0) < 27 and tn["sagitta_r_over_D"] > 100
                  and 0.9 < e.get("omega_rad_per_s", 0) < 1.1 and e.get("arc_deg", 0) > 500 and e.get("minor_sigmas", 9) < 1.5
                  and "swings about more than a bend does" in words and "no loop is claimed" in words and "back and forth along a line" in words,
                  "PR077 object-1: an ellipse follows it through more than a turn, about 24 body widths either side, and neither its "
                  "gain over its own wander nor its minor axis shows it going round: it swings about, no loop claimed",
                  f"{e.get('reach_widths', 0):.1f} widths either side (the sagitta {tn['sagitta_r_over_D']:.0f}), {e.get('omega_rad_per_s', 0):.2f} rad/s, "
                  f"{e.get('arc_deg', 0):.0f}°, gain {e.get('lr', 0):.0f}, minor axis {e.get('minor_sigmas', 0):.1f} errors")
    # "no closing seen" as a bound (M5): PR23's object and PR149's contact, the two whose speed change is known well enough
    # (the survey's table, 2026-10-29: under 1.0 and 4.5 % a second with the change's error taken along the change; along
    # the track, as the bound takes it, 1.5 and 0.62 % -- PR149's 4.6 % until its two glitches were named and left out of
    # its band, E4, 2026-10-29), each said under the condition its track does not meet
    from mcdonald import forensics as vf
    pr149 = reference_data.root() / "cases" / "pr149.mcdonald"
    tracks = [("PR23", vf.read_track(HERE / "golden" / "pr23_object_track.csv"), 30.0, (0.012, 0.02))]
    if pr149.exists():
        with zipfile.ZipFile(pr149) as z:
            rows = list(csv.DictReader(l for l in io.StringIO(z.read("case/object-1/pr149_track.csv").decode("utf-8")) if not l.startswith("#")))
        tracks.append(("PR149", {int(float(r["frame"])): (float(r["x_px"]), float(r["y_px"])) for r in rows if r["x_px"] not in ("", "nan")},
                       30.0, (0.004, 0.009)))
        from mcdonald import kinematics as kin
        band, _ = kin.speed_band(tracks[-1][1], 30.0)
        check([(f["kind"], f["frame"]) for f in band["jumps"]["flags"]] == [("glitch", 36), ("glitch", 76)] and band["clipped"] == 2
              and band["accel_z"] >= 3,
              "PR149: its two glitches (frames 36 and 76, 12 and 9 px) are named and left out of its band, and its change of speed is seen (E4)",
              f"{kin.jumps_said(band)[:90]}; {band['dv_px_per_s']:.0f} ± {band['dv_err_px_per_s']:.0f} px/s, {band['accel_z']:.1f} sigma")
    else:
        SKIP.append("pr149 depth bound")
    for name, track, fps, (lo, hi) in tracks:
        f = pj.fit(track, fps, boot=0)
        d, said = f["depth"], pj.said(f)["constant velocity"]
        check(f["closing"] is False and d is not None and lo < d["rate_max_per_s"] < hi
              and "if its trend is a straight flight at a steady speed, its depth changed by less than" in said,
              f"{name}: no closing seen, and how fast its depth could have changed, as a bound on its trend",
              f"under {100 * d['rate_max_per_s']:.1f} % a second; at least {d['T_closing_min_s']:.0f} s closing, "
              f"{d['T_receding_min_s']:.0f} s receding" if d else "no bound")
    pr097 = pr149.with_name("pr097.mcdonald")
    if pr097.exists():
        with zipfile.ZipFile(pr097) as z:
            rows = list(csv.DictReader(l for l in io.StringIO(z.read("case/object-1/pr097_track.csv").decode("utf-8")) if not l.startswith("#")))
        f = pj.fit({int(float(r["frame"])): (float(r["x_px"]), float(r["y_px"])) for r in rows if r["x_px"] not in ("", "nan")}, 30.0, boot=0)
        check(f["depth"] is None and "the track's wander's" in (f["depth_none"] or "") and "the track's wander's" in pj.said(f)["constant velocity"],
              "PR097 object 1: its ends run 2-3 times its mean speed, no straight flight's, so no bound on its depth, and it says why "
              "(16 % a second before 2026-10-30)", f["depth_none"] or "a bound")
    else:
        SKIP.append("pr097 depth bound")


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


def _flir1(name):
    p = reference_data.root() / "nimitz_flir1" / name
    return (p, None) if p.exists() else (None, f"{p} is not here")


def test_pr051_zoom_with_no_blank():
    """PR051's leak (Sitrec's copy of Corbell's upload, 2026-10-27): its MTS-B display goes from 2X to ULTN at frames
    1331-1341 with no blank, the picture brightening for a few frames, and its data bar's FVW goes 119 -> 238-239 m at a
    slant range that holds (x1/1.999). `mcdonald zoom` must find it as a step of the picture and measure it."""
    print("\nPR051's leak -- an electronic zoom out with no blank, against its data bar")
    mov = reference_data.root() / "pr051" / "syria_combined_B.mov"
    if not mov.exists():
        print(f"  SKIP  {mov} is not here")
        SKIP.append("PR051 zoom")
        return
    from mcdonald import zoom
    from mcdonald.clip import Clip
    clip = Clip(mov, None, extract=False)
    f = zoom.measure(mov, clip.W, clip.H, clip.fps, clip=clip).fields
    r = next((b for b in f["bursts"] if b["frames"][0] <= 1345 and b["frames"][1] >= 1325), None)
    check(r is not None and r.get("kind") == "picture", "a step of the picture with no blank, at frames 1331-1341",
          r and f"{r['kind']} {r['frames']}")
    check(r is not None and r["verdict"] == "step" and abs(r["s"] * 1.999 - 1) < 0.02,
          "x1/2 within 2 % of the data bar's x1/1.999", r and f"{r['verdict']} x{r.get('fitted_s') or 0:.4f} {r.get('why')}")


def test_pr051_scene_path_against_the_data_bar():
    """PR051's upload (2026-10-28): the scene's path over 5.0-9.5 s of the first framing, chained from `layers` on
    pairs of whole frames (every frame is doubled; the overlay boxed by hand), against TGT A's motion across the line
    of sight read off the data bar every 0.5 s (`pr051/pr051_databar_track.csv`) -- the known answer for a scene
    measurement on a picture that repeats and catches up over terrain streaked across the picture. Before K9
    (`docs/method.md` §31) 12 % of pairs reached a consensus and the chain broke at 7 s; with each template weighed by
    its own error, and the streak-bound ones counted across their streaks, it holds over the window at 95 % of the
    bar's path (the bar is read by eye, its uncertain digits marked; the window's hold 0.074 deg/s is in both)."""
    print("\nPR051's upload, 5.0-9.5 s -- the scene's path against the data bar")
    root = reference_data.root() / "pr051"
    video, bar = root / "yt_nKtJslcHlCQ_1080p60_h264.mp4", root / "pr051_databar_track.csv"
    if not (video.exists() and bar.exists()):
        print(f"  SKIP  {video} or {bar} is not here")
        SKIP.append("PR051 scene path")
        return
    import csv
    import math
    import numpy as np
    from mcdonald import slew
    boxes = [(30, 35, 630, 110), (660, 0, 1260, 140), (770, 135, 900, 215), (870, 210, 1010, 290),
             (1450, 110, 1890, 290), (30, 145, 270, 320), (100, 350, 200, 405), (0, 460, 320, 745),
             (820, 500, 1030, 620), (1390, 715, 1900, 1080), (30, 955, 210, 1080), (460, 245, 515, 295),
             (1405, 245, 1455, 300)]
    args = ["layers", str(video), "--n0", "301", "--n1", "811", "--k", "2", "--step", "2", "--max-shift", "100"]
    for b in boxes:
        args += ["--mask-box", ",".join(map(str, b))]
    with tempfile.TemporaryDirectory() as td:
        run(args + ["--out", td, "--fresh"], td)
        fr, _, dx, dy, k, groups, err = slew.read_layers(next(Path(td).glob("*_layers.csv")), errors=True)
    err[:, 0] /= 4 / 3
    frames, X, _, S, _, E = slew.scene_path(fr, dx / (4 / 3), dy, k, err=err)   # square px: the 4:3 sensor's 1440
    # the bar: TGT A's grid (MGRS 37S CS) rotated by the grid convergence to true, its motion across the line of
    # sight (true azimuth about 7 deg over the window) over FVW (654 m) times 1440 square px
    num = lambda s: float(s.replace("(?)", "")) if s.replace("(?)", "") else np.nan
    with open(bar, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(l for l in f if not l.startswith("#")) if 5.0 <= float(r["t_s"]) <= 13.5]
    gE, gN = np.array([num(r["tgt_e_m"]) for r in rows]), np.array([num(r["tgt_n_m"]) for r in rows])
    g = math.atan(math.tan(math.radians(36.9 - 39.0)) * math.sin(math.radians(32 + 3 / 60)))
    tE, tN = gE * math.cos(g) + gN * math.sin(g), -gE * math.sin(g) + gN * math.cos(g)
    az0 = math.radians(7.0)
    dT = (tE - tE[0]) * math.cos(az0) - (tN - tN[0]) * math.sin(az0)
    Xexp = -dT / 654.0 * 1440.0
    at = {int(f): i for i, f in enumerate(frames)}
    bf = [int(r["frame"]) for r in rows]
    t = np.array([float(r["t_s"]) for r in rows])
    xm = np.array([X[at[f]] if f in at else np.nan for f in bf])
    seg = np.array([S[at[f]] if f in at else -1 for f in bf])
    # 5.0-9.5 s (the third session's check: catch-up steps of 15-40 px), then through 13.5 s (the fourth session's:
    # steps of 70-140 px along the streaks that only the vote reads, holds that jitter by up to 2 px). With every
    # pair measured the chain runs at 0.91-0.93 of the bar's path over either window (2026-10-28), where the broken
    # chain, bridged at its neighbours' rate, had run at 0.95: the shortfall is steady, not lost steps, and whether
    # it is the bar's reading (the digits, the 7-deg azimuth, the picture against the data bar's own timing) or the
    # picture's is open (docs/handoff-v04.md); the longer window is held to 15 %.
    pairs = np.isfinite(groups) & (fr >= 301) & (fr < 811)          # the rows that are pairs (every other frame at --step 2)
    measured = np.isfinite(dx[pairs]).mean()
    check(measured > 0.95, "PR051: nearly every pair over 5.0-13.5 s has a consensus (the holds unmoved, the steps read)",
          f"{measured:.1%} of pairs")
    for t1, what, tol in ((9.5, "5.0-9.5 s", 0.10), (13.5, "5.0-13.5 s, through the big catch-up steps of 10-13 s", 0.15)):
        w = t <= t1
        one = np.isfinite(xm[w]).all() and seg[0] >= 0 and (seg[w] == seg[0]).all()
        check(one, f"PR051: the chain holds in one stretch over {what}", f"stretches {sorted(set(seg[w].tolist()))}")
        if not one:
            continue
        last = int(np.flatnonzero(w)[-1])
        rise, want = xm[last] - xm[0], Xexp[last] - Xexp[0]
        check(abs(rise / want - 1) < tol, f"PR051: its rise over {what.split(',')[0]} is within {tol:.0%} of the data bar's",
              f"{rise:.0f} against {want:.0f} square px (x{rise / want:.3f}); the path's own error +/-{E[at[bf[last]], 0]:.0f}")
        check(np.isfinite(E[at[bf[last]], 0]) and 0 < E[at[bf[last]], 0] < 0.05 * want,
              "PR051: the path carries its own error, small against the rise", f"+/-{E[at[bf[last]], 0]:.1f} square px")


def test_puerto_rico_k_from_the_data_bar():
    """AARO's Puerto Rico 2013 clip (2026-10-29): `slew` with the display's own readings in place of a pointer -- the
    aircraft's position and the line of sight's ground point every 2.5 s, as vendored for the drift stage
    (`golden/puerto_rico_drift/`), and the scene's 5-frame shifts over IR 675's 81.4-117.8 s with the display's graphics
    boxed out (`golden/puerto_rico_scene_layers.csv`, `layers --k 5 --max-shift 30`). The known answer is the uap case's
    1657 +- 79 px/deg from the same readings, regressed the other way (the scene on the bar: pulled low by the bar's
    29-m grain; the bar on the scene gives 1696-1727). No video is read: the series are vendored."""
    from mcdonald import slew
    print("\nAARO Puerto Rico, IR 675 -- k from the data bar against the known answer")
    bar = slew.bar_series(GOLDEN / "puerto_rico_drift" / "platform.csv", GOLDEN / "puerto_rico_drift" / "los.csv")
    got = {}
    for w in ((82.0, 100.0), (82.0, 107.0), (82.0, 117.0), (100.0, 117.0)):
        f = slew.measure(None, GOLDEN / "puerto_rico_scene_layers.csv", 1920, 1080, 30000 / 1001, [w], pixel_aspect=0.875,
                         n_boot=200, bar=bar).fields
        got[w] = f
        print(f"        {w[0]:.0f}-{w[1]:.0f} s: k {f['k_px_per_deg'] or float('nan'):.0f} px/deg at {f['depression_deg']:.2f} deg"
              f" ({f['windows'][0]['no_power'] or 'claimed'})")
    check(abs(bar["grain_m"] - 29.2) < 1.0, "the bar's positions are read on an arc-second's grain", f"{bar['grain_m']:.1f} m")
    f = got[(82.0, 107.0)]
    k = f["k_px_per_deg"]
    check(k is not None and not f["windows"][0]["no_power"] and f["degree"] == 0,
          "82-107 s: the stage claims k with the platform's share taken from the bar (no hold fitted)")
    check(k is not None and abs(k - 1657) <= 2 * 79, "82-107 s: within the known answer's two sigmas (1657 +- 158)",
          f"{k:.0f}" if k else "none")
    check(k is not None and abs(k / 1727 - 1) < 0.02, "82-107 s: k as measured on 2026-10-29 (1727; the bar on the scene, "
          "1727) within 2 %", f"{k:.0f}" if k else "none")
    ks = [got[w]["k_px_per_deg"] for w in ((82.0, 100.0), (82.0, 117.0))]
    check(all(v and abs(v - 1657) <= 2 * 79 for v in ks), "82-100 and 82-117 s: within the known answer's two sigmas",
          ", ".join(f"{v:.0f}" for v in ks if v))
    check(all(abs(got[w]["depression_deg"] - 8.0) < 0.6 for w in got), "the depression is the bar's (7.5-8.5 deg)",
          ", ".join(f"{got[w]['depression_deg']:.2f}" for w in got))


def _puerto_rico_range(frames):
    """The lanterns' range (m) at each frame: the uap case's straight path through the 39 lines of sight
    (`pr_drift_los.json`: at 69.5 s 18.50035 N 67.12954 W, 253 m above the sea; 6.39 m/s west, 3.62 south, 0.61 down)
    against the aircraft's printed positions (`golden/puerto_rico_drift/platform.csv`), drawn straight between them."""
    import csv
    import math
    import numpy as np
    with open(GOLDEN / "puerto_rico_drift" / "platform.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(l for l in f if not l.startswith("#")))
    fr = np.array([int(r["frame"]) for r in rows])
    lat, lon, alt = (np.array([float(r[c]) for r in rows]) for c in ("lat", "lon", "alt_m"))
    lat0, lon0 = 18.50035, -67.12954
    m_lat = 111132.954 - 559.822 * math.cos(2 * math.radians(lat0))
    m_lon = 111412.84 * math.cos(math.radians(lat0))
    t = (fr - 1) / (30000 / 1001)
    P = np.c_[-6.39 * (t - 69.5), -3.62 * (t - 69.5), 253.0 - 0.61 * (t - 69.5)]
    R = np.linalg.norm(P - np.c_[(lon - lon0) * m_lon, (lat - lat0) * m_lat, alt], axis=1)
    return np.interp(frames, fr, R)


def test_puerto_rico_lanterns_tau_against_their_range():
    """AARO's Puerto Rico lanterns (2026-10-29): tau's two routes on the flicker stage's own curves over 1640-2231
    (`golden/puerto_rico_lantern_curves.csv`), the range opening 2131 -> 2567 m (tau about -97 s on the track's
    log-line). The size route must see no closing (the lanterns recede at about five track lengths), its trend on the
    range's side; the light route, which the stage does not try on a resolved object, fails here as its condition says
    it may -- the lanterns' own light changed more than their range -- and its gate must claim nothing."""
    import csv
    import numpy as np
    from mcdonald import kinematics as kin
    print("\nAARO Puerto Rico's lanterns, 1640-2231 -- tau against the range their path gives")
    with open(GOLDEN / "puerto_rico_lantern_curves.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(l for l in f if not l.startswith("#")))
    num = lambda s: float(s) if s not in ("", None) else None
    fr = np.array([int(r["frame"]) for r in rows])
    t = (fr - 1) / (30000 / 1001)
    size, flux, level = ([num(r[c]) for r in rows] for c in ("object size", "object", "object level"))
    R = _puerto_rico_range(fr)
    truth = float(np.polyfit(t - t.mean(), -np.log(R), 1)[0])           # d ln s / dt if the size were the range's alone
    got = kin.tau_of(t, size, flux, level)
    lm = got["looming"] or {}
    print(f"        the range {R[0]:.0f} -> {R[-1]:.0f} m: d ln(1/R)/dt {truth:+.4f}/s; the size's {lm.get('dlns_dt', float('nan')):+.4f}"
          f" +- {lm.get('dlns_err', float('nan')):.4f}; {got['why']}")
    check(got["route"] is None and got["median_px"] and got["median_px"] >= kin.TAU_MIN_PX,
          "resolved, and no closing claimed (the size route reaches a thing closing in about the track's length)",
          f"radius {got['median_px']}, route {got['route']}")
    check(lm.get("dlns_dt") is not None and abs(lm["dlns_dt"] - truth) <= 2 * lm["dlns_err"] and lm["dlns_dt"] < 0,
          "the size shrinks as the range opens, within two of its sigmas", f"{lm.get('dlns_dt', float('nan')):+.4f} for {truth:+.4f}")
    light = kin.tau_of(t, None, flux, level)                            # the light route, tried as for a point
    F, L = np.array([v if v else np.nan for v in flux]), np.array([v if v else np.nan for v in level])
    ok = np.isfinite(F) & (F > 0) & np.isfinite(L) & (L > 0)
    b, e, _ = kin._trend(t[ok], np.log(F[ok] / L[ok]))
    print(f"        the light, its level out: d ln F/dt {b:+.4f} +- {e:.4f} against the range's {2 * truth:+.4f}")
    check(light["light"] is None, "the light route claims nothing (its gate: four sigmas and a tenth)", f"{light['light']}")
    check(abs(b - 2 * truth) > 2 * e, "and its curve does not follow the range: the lanterns' own light changed more",
          f"{(b - 2 * truth) / e:+.1f} sigmas off")


def test_puerto_rico_lanterns_over_the_doubling():
    """AARO's Puerto Rico lanterns over the range's doubling (2026-10-30): the frames over 54.7-117.8 s that they can be followed on
    (`golden/puerto_rico_lantern_curves_long.csv`), the range opening 2131 -> 4474 m, so the flux should fall x0.23. What holds. The
    size route, with the whole lever, says receding and places it near the range's own line; windows a frame or a second apart read -110
    to -195 s for about -109, so it is good to a factor of two and not to its 2 % here. Over the track's longest stretch it rightly
    holds. The stage does not try the light on a resolved object. The light by itself recedes, but how fast depends on the aperture,
    x2.4: the core is clipped, so a small disc reads the blob and not its light. Its bright state follows the range: the 90 % envelope
    in a wide disc, clear of the reticle's ticks, as R^-1.8, F R^2 flat within a fifth (off the lantern a disc that wide can read
    nearly as much in a bin, so -2 is allowed and not pinned). Its median does not, since the flame switches: by over x4 within half a
    second on 15 % of frames, where the range makes 6 %, and nothing can be seen for 5 s at 4.2 km, then black again. So in short
    windows a switch passes the gate as a false closing, and from 10 s it does not."""
    import csv
    import numpy as np
    from mcdonald import kinematics as kin
    print("\nAARO Puerto Rico's lanterns, 1641-3530 -- tau and the light against their range, x2.1")
    with open(GOLDEN / "puerto_rico_lantern_curves_long.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(l for l in f if not l.startswith("#")))
    num = lambda s: float(s) if s not in ("", None) else None
    FPS = 30000 / 1001
    fr = np.array([int(r["frame"]) for r in rows])
    t = (fr - 1) / FPS
    size, flux, level, wide, ring = ([num(r[c]) for r in rows] for c in ("object size", "object", "object level", "r22", "r22 level"))
    clear = np.array([r["clear"] == "1" for r in rows])
    R = _puerto_rico_range(fr)
    print(f"        {len(fr)} frames, the range {R[0]:.0f} -> {R[-1]:.0f} m; flux x{(R[0] / R[-1]) ** 2:.2f}")
    check(2.05 < R[-1] / R[0] < 2.15, "the range doubles over the stretch", f"x{R[-1] / R[0]:.2f}")
    check(not ((fr >= 3269) & (fr <= 3423)).any(), "nothing to follow over 3269-3423: left out, not read as a flux",
          "a search over rates finds nothing there, and finds them either side")
    b, a = np.polyfit(t, R, 1)
    line = -a / b - t[-1]
    got = kin.tau_of(t, size)
    print(f"        the size route: {got['route']}, tau {got['tau_s']} +- {got['tau_err_s']}; the range's line {line:+.1f} s")
    check(got["route"] == "looming" and got["closing"] is False and abs(got["tau_s"] / line - 1) < 0.15,
          "the whole lever: the size says receding, and places it within 15 % of the range's line",
          f"{got['tau_s']:+.1f} +- {got['tau_err_s']:.1f} s for {line:+.1f}")
    ahead = [kin.tau_of(t[i], [size[k] for k in i])["tau_s"] for i in (np.flatnonzero((t >= t[0] + d) & (t < t[0] + d + 60)) for d in range(4))]
    print(f"        60-s windows a second apart: {[round(v, 1) if v else v for v in ahead]} s")
    check(all(v and -2.1 * abs(line) < v < 0 for v in ahead), "windows a second apart all recede, within a factor of two of it: that is its worth here",
          ", ".join(f"{v:+.0f}" for v in ahead if v))
    near = np.flatnonzero(fr <= 2597)
    short = kin.tau_of(t[near], [size[i] for i in near])
    check(short["route"] is None and "held" in (short["why"] or ""), "its longest stretch, 1641-2597, the size holds: no claim", short["why"])
    check(kin.tau_of(t, size, flux, level)["light"] is None, "resolved, so the stage does not try the light")
    small, big = kin.tau_of(t, None, flux, level)["light"], kin.tau_of(t, None, wide, ring)["light"]
    print(f"        the light by itself: tau {small['tau']:+.0f} s in the stage's 6-px disc, {big['tau']:+.0f} s in 22 px; the range's -77")
    check(small["tau"] < 0 and big["tau"] < 0, "the light by itself recedes in both", f"{small['tau']:+.0f}, {big['tau']:+.0f} s")
    check(small["tau"] / big["tau"] > 2, "and how fast depends on the aperture, the clipped core's doing", f"x{small['tau'] / big['tau']:.1f}")
    F = np.array([np.nan if v is None else v for v in wide])
    edges = np.arange(fr[0], fr[-1] + 120, 120)
    bins = [(float(np.median(R[m])), float(np.percentile(F[m], 90)), float(np.median(F[m]))) for m in
            (clear & (fr >= lo) & (fr < hi) & np.isfinite(F) for lo, hi in zip(edges[:-1], edges[1:])) if m.sum() >= 25]
    Rb, top, mid = np.array(bins).T
    p = float(np.polyfit(np.log(Rb), np.log(top), 1)[0])
    q = float(np.polyfit(np.log(Rb[mid > 0]), np.log(mid[mid > 0]), 1)[0])
    flat = np.log(top * Rb ** 2)
    print(f"        over {len(bins)} 4-s bins: the 90 % envelope as R^{p:+.2f}, F R^2 scatters {flat.std():.2f} in ln; the median as R^{q:+.2f}")
    check(-2.3 < p < -1.4, "the bright state follows the range: the envelope falls as about R^-2", f"p {p:+.2f}")
    check(flat.std() < 0.2, "and F R^2 holds within a fifth over a flux falling x0.28", f"{flat.std():.2f}")
    check(q < p - 0.5, "the median does not: the flame switches, more of the time off as it goes", f"{q:+.2f} against {p:+.2f}")
    bad = {3: 0, 5: 0, 10: 0, 20: 0, 30: 0}
    for w in bad:
        for lo in np.arange(t[0], t[-1] - w + 1e-6, 1.0):
            i = np.flatnonzero((t >= lo) & (t < lo + w))
            if len(i) < 0.6 * w * FPS:
                continue
            for c, lv in ((flux, level), (wide, ring)):
                lc = kin.tau_of(t[i], None, [c[k] for k in i], [lv[k] for k in i])["light"]
                bad[w] += bool(lc and lc["tau"] > 0)
    print(f"        windows the light calls closing, in the two apertures, by length in s: {bad}")
    check(bad[3] + bad[5] > 0, "in windows of 3-5 s a switch passes the gate as a false closing (the reading says a flame can)", f"{bad}")
    check(bad[10] + bad[20] + bad[30] == 0, "from 10 s on it does not", f"{bad}")


def test_yemen_line_of_sight_against_the_laser():
    """The Yemen clip (2026-10-29): the MQ-9 flew straight and level at a steady speed, so the object's motion relative
    to it is a straight line at a steady velocity -- the projective test's premise for a camera that does not turn. Its
    line of sight from the display alone -- the azimuth off the north pointer (`golden/hellfire_drift/bearings.csv`),
    the depression off the laser's slant range (`slant.csv`; S² a quadratic through its 0.1-NM steps, exact for such a
    line) over the height below (3793 m) -- drawn by a camera looking along the middle line of sight: the test's T
    and depth bound against the range the laser and the uap case's straight line (fit3d) give, T = 92.6 s and
    |Zdot/Z| = 1.08 % a second at the last frame. The object's own track is held on the reticle, so the stage, rightly,
    reads neither from it."""
    import csv
    import math
    import numpy as np
    from mcdonald import kinematics as kin, projective as pj
    print("\nYemen, frames 130-590 -- the line of sight drawn by a camera that does not turn, against the laser")
    rows = lambda f: list(csv.DictReader(l for l in open(GOLDEN / "hellfire_drift" / f, encoding="utf-8") if not l.startswith("#")))
    b, s = rows("bearings.csv"), rows("slant.csv")
    fb = np.array([float(r["frame"]) for r in b])
    az = np.radians([float(r["value"]) for r in b])
    fs, S = np.array([float(r["frame"]) for r in s]), np.array([float(r["value_m"]) for r in s])
    dep = np.arcsin(3793.0 / np.sqrt(np.polyval(np.polyfit(fs, S ** 2, 2), fb)))
    d = np.c_[np.sin(az) * np.cos(dep), np.cos(az) * np.cos(dep), -np.sin(dep)]
    mid = d[len(d) // 2]
    right = np.cross(mid, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    down = np.cross(mid, right)
    f = 20.0 * 180 / math.pi                                          # 20 px/deg: k cancels in T
    track = {int(n): (320 + f * (u @ right) / (u @ mid), 164 + f * (u @ down) / (u @ mid)) for n, u in zip(fb, d)}
    r0, v = np.array([5010.0, -963.3, -3789.7]), np.array([-67.2, 74.81, -1.06])   # fit3d, at frame 336
    Z = (r0 + (fb[-1] - 336) / 30.0 * v) @ mid
    T_true, rate_true = Z / abs(v @ mid), abs(v @ mid) / Z
    band, _ = kin.speed_band(track, 30.0)
    p = pj.fit(track, 30.0, band=band)
    dpt = pj.depth_bound(band)
    print(f"        T {p['T']:.1f} s (t_z band {p['t_z_band']}), fits {p['fits']}, closing {p['closing']}; the laser's {T_true:.1f} s; "
          f"depth bound {dpt['rate_max_per_s'] if dpt else float('nan'):.4f}/s against {rate_true:.4f}")
    check(p["closing"] is True, "closing on the camera, as the laser says", f"{p['closing']}")
    check(p["T"] is not None and abs(p["T"] / T_true - 1) < 0.3 and p["t_z_err"] is not None and abs(p["T"] - T_true) <= p["t_z_err"],
          "T within 30 % of the laser's, and now within its own error (80.7 +- 55 s against 92.6; the residual bootstrap's "
          "75.9-87.2 did not hold it, 2026-10-29, nor did it say T is 5 times the track)", f"{p['T']:.1f} +- {p['t_z_err']:.1f} against {T_true:.1f}")
    check(dpt is not None and dpt["rate_max_per_s"] >= rate_true, "the depth bound holds the laser's |Zdot/Z| (2.1 % a "
          "second against 1.08 on 2026-10-29: twice wide)", f"{dpt['rate_max_per_s'] if dpt else None}")
    held = kin.fit_v_px({n: (318.10, 163.20) for n in range(110, 597)}, 30.0)
    check(held["held"], "the object's own track, one point on the reticle: held (no projective test, no bound)")


def test_pr051_released_track_against_the_scene():
    """PR051's upload (2026-10-28): the released-track null with the scene as the camera's own record (`camera --scene`,
    docs/method.md §20). The MTS-B held the object in its gate over 70-74 s of the upload (frames 4201-4437) while the
    ground, in the picture at 4X, held still too: the camera was not turning against the ground to hold it. From the
    frame the gate starts blinking (4439) the object walks out of it and crosses the ground at 0.0079 deg/s (the 4X
    field: FVW 58.5 m at 22.5 NM, 0.080 deg across the 4:3 sensor's 1440 square px) for 1.8 s, then becomes a dash
    475 px to the right. Neither is what a camera that stopped following shows, and the scene's own path says the
    camera did not move at the dash either. The track is `tests/golden/pr051_release_track.csv` (its header says how
    it was made); the scene is `layers` on the same frames, every frame doubled, the overlay boxed by hand."""
    print("\nPR051's upload, 70-76 s -- the released-track null against the scene")
    root = reference_data.root() / "pr051"
    video = root / "yt_nKtJslcHlCQ_1080p60_h264.mp4"
    if not video.exists():
        print(f"  SKIP  {video} is not here")
        SKIP.append("PR051 released track")
        return
    from mcdonald import camera, clip as vclip, forensics as vf
    boxes = [(30, 30, 630, 115), (660, 0, 1260, 205), (800, 215, 960, 295), (1440, 105, 1880, 295), (50, 155, 260, 325),
             (105, 355, 205, 410), (20, 460, 340, 745), (895, 500, 1005, 615), (800, 475, 1000, 620),
             (1380, 715, 1900, 1080), (50, 955, 220, 1080), (620, 260, 1010, 625), (1000, 290, 1600, 400)]
    args = ["layers", str(video), "--n0", "4201", "--n1", "4661", "--k", "2", "--step", "2", "--max-shift", "60"]
    for b in boxes:
        args += ["--mask-box", ",".join(map(str, b))]
    track = vf.read_track(str(HERE / "golden" / "pr051_release_track.csv"))
    with tempfile.TemporaryDirectory() as td:
        run(args + ["--out", td, "--fresh"], td)
        scene = camera.read_scene(next(Path(td).glob("*_layers.csv")))
        clip = vclip.Clip(video, None, 4201, 4567)
        f = camera.measure(clip, track, size=71, fov=0.080, scene=scene, after=4439, pixel_aspect=4 / 3)
    sc, r = f.fields["scene"], f.fields["released"]
    check(sc["frames_on_path"] == len(track) and not sc["frames_off_path"],
          "PR051: every tracked frame is on one stretch of the scene's path", f"{sc['frames_on_path']} of {len(track)}")
    b = sc["before"]
    check(b is not None and b["v_px_per_s"] < 3.0 and not b["turned"],
          "PR051: the ground held still while the gate held the object: the camera was not turning against it",
          f"{b['v_px_per_s']:.1f} +- {b['err_px_per_s']:.1f} square px/s over {b['frames']}" if b else "none")
    l = sc["after"]
    check(l is not None and l["v_px_per_s"] < 3.0,
          "PR051: and after the release, through the drift and the dash, the camera still did not move against the ground",
          f"{l['v_px_per_s']:.1f} +- {l['err_px_per_s']:.1f} square px/s over {l['frames']}" if l else "none")
    w = r["whole"] if r else None
    check(w is not None and w["frames"] == [4439, 4549] and w["cut_at_jump"] == 4553,
          "PR051: the departure as a whole runs from the gate's blink to the dash's jump",
          f"{w['frames']}, cut at {w['cut_at_jump']}" if w else "none")
    if w:
        check(0.0070 <= w["deg_per_s"] <= 0.0090 and not w["within"] and w["z"] > 10 and 300 <= w["direction_deg"] <= 345,
              "PR051: it crosses the ground at 0.0079 deg/s, up and to the left, far faster than the camera had been turning",
              f"{w['deg_per_s']:.4f} +- {w['err_deg_per_s']:.4f} deg/s ({w['v_px_per_s']:.0f} square px/s), heading "
              f"{w['direction_deg']:.0f} deg, {w['z']:+.1f} sigma")
        check(w["direction_off_deg"] is None, "PR051: with the camera not turning, the release sends the object no way")
    t = r["fastest"] if r else None
    check(t is not None and t["frames"] == [4561, 4567] and 0.07 <= t["deg_per_s"] <= 0.15 and not r["within_camera_rate"],
          "PR051: the fastest stretch is the dash, at a tenth of a degree a second after a jump of hundreds of pixels",
          f"{t['frames']} {t['deg_per_s']:.3f} +- {t['err_deg_per_s']:.3f} deg/s" if t else "none")
    said = " ".join(camera.said(f.fields))
    check("was not turning against the ground" in said and r is not None and "the release alone does not explain" in r["said"],
          "PR051: it says the camera was not turning, and that the release explains none of it")


def test_flir1_frame_rate():
    """The Navy's 2004 FLIR1, the 2007 copy (2026-10-20): an MPEG-1 VCD stream whose header gives the field rate.
    Read at 59.94 every time and rate on it was halved, and flicker's verdict changed on the same pixels."""
    print("\nFLIR1 -- the frame rate of an MPEG-1 file that gives the field rate")
    mpg, why = _flir1("f4_2007_archive.mpg")
    if mpg is None:
        print(f"  SKIP  {why}")
        SKIP.append("FLIR1 frame rate")
        return
    from fractions import Fraction
    from mcdonald import clip as vclip
    i = vclip.probe(mpg)
    check(i["stream"]["r_frame_rate"] == "60000/1001" and i["fps"] == Fraction(30000, 1001),
          "FLIR1: the header's 60000/1001 is read as 30000/1001", f"{i['fps']}")
    mkv, _ = _flir1("f4_2007_ffv1.mkv")
    if mkv is not None:
        check(vclip.probe(mkv)["fps"] == i["fps"], "FLIR1: the same as its lossless copy that carries the rate")


def test_flir1_zoom_and_release():
    """FLIR1's exit: the picture zooms x2 between frames 2234 and 2235, three frames before its readout says so;
    the object's rate steps at the zoom; its fastest stretch is near the 0.247 deg/s the pod had been turning."""
    print("\nFLIR1, frames 2185-2250 -- the zoom inside the track, and the track let go")
    mpg, why = _flir1("f4_2007_archive.mpg")
    if mpg is None:
        print(f"  SKIP  {why}")
        SKIP.append("FLIR1 zoom")
        return
    from mcdonald import camera, forensics as vf
    track = vf.read_track(str(HERE / "golden" / "flir1_exit_track.csv"))
    with tempfile.TemporaryDirectory() as td:
        clip = vf.Clip(mpg, f"{td}/frames", 2185, 2250)
        f = camera.measure(clip, track, fov=0.7, fov_px=244, los_rate=0.2466, los_err=0.0051, after=2207,
                           ratios=[2.0], events=[(2238, "the 2.0 readout")])
    z = f.fields["zoom_steps"]
    check(len(z) == 1 and z[0]["frame"] == 2235, "FLIR1: one zoom step, at frame 2235", f"{[s['frame'] for s in z]}")
    if not z:
        return
    check(1.8 <= z[0]["ratio_from_size"] <= 2.2 and 1.8 <= (z[0]["ratio_from_offset"] or 0) <= 2.2,
          "FLIR1: the size's and the offset's ratios both near 2",
          f"x{z[0]['ratio_from_size']:.2f}, x{z[0]['ratio_from_offset'] or 0:.2f}")
    check(z[0]["centre"] is not None and abs(z[0]["centre"][0] - 177.3) < 3 and z[0]["confirmed_by_offset"],
          "FLIR1: about the boresight, where the object was held", f"{z[0]['centre']}")
    b = [x for x in f.fields["breaks"] if x["at_event"]]
    check(any(x["frame"] == 2235 for x in b), "FLIR1: a rate step at the zoom, at the camera's event",
          f"{[(x['frame'], x['event']['what']) for x in b]}")
    r = f.fields["released"]
    check(r is not None and 0.25 <= r["fastest"]["deg_per_s"] <= 0.33 and r["within_camera_rate"],
          "FLIR1: the fastest stretch within two sigma of the pod's own slew, with the scale's 10 %",
          "" if r is None else f"{r['fastest']['deg_per_s']:.3f} deg/s, z {r['z']:+.1f} ({r['z_without_scale']:+.1f} exact)")


def test_flir1_readout():
    """FLIR1's pod azimuth readout, whole degrees, timed tick by tick: 0.2466 +- 0.0051 deg/s over 8 ticks, and its
    last value holds to the end, where at that rate the next tick was not due (frame ~2296 of 2289). Its tick from 1 L
    to 2 L is at 1437.5, where the readout changes (2026-10-20, a strip of every other frame): timed on the grey, it came
    out at 1477.5 and the rate at 0.2518 +- 0.0042, because the sky brightens behind the readout at 1486."""
    print("\nFLIR1 -- the azimuth readout's ticks")
    mpg, why = _flir1("f4_2007_archive.mpg")
    if mpg is None:
        print(f"  SKIP  {why}")
        SKIP.append("FLIR1 readout")
        return
    from mcdonald import forensics as vf, readout
    import csv as _csv
    with open(HERE / "golden" / "flir1_az_stretches.csv", encoding="utf-8") as fh:
        rows = list(_csv.DictReader(ln for ln in fh if not ln.startswith("#")))
    # from the 0 stretch on: the eight ticks of the steady turn, and half the frames to extract
    stretches = [(int(r["first"]), int(r["last"]), float(r["value"])) for r in rows if int(r["first"]) >= 1151]
    with tempfile.TemporaryDirectory() as td:
        clip = vf.Clip(mpg, f"{td}/frames", 1151, 2289)
        tk = readout.ticks(clip, (163, 21, 179, 34), stretches)
        r = readout.rate(tk, clip.fps, last_frame=2289)
    t2 = [t for t in tk if (t["from"], t["to"]) == (-1.0, -2.0)]
    check(len(t2) == 1 and abs(t2[0]["tick_frame"] - 1437.5) <= 1.5,
          "FLIR1: its 1 L -> 2 L where the readout changes, not where the sky behind it brightens (1486)",
          f"{t2[0]['tick_frame'] if t2 else None}")
    check(r["ticks_used"] == 8 and abs(r["rate_per_s"] + 0.2466) < 0.002, "FLIR1: the pod's slew from 8 ticks",
          f"{r['rate_per_s']:+.4f} +- {r['rate_err_per_s']:.4f} over {r['ticks_used']}")
    check(r["holds_to_end"] and r["next_tick_due_frame"] > 2289,
          "FLIR1: its 8 L holds to the end, and could not have ticked again before it", f"due {r['next_tick_due_frame']:.0f}")


FLIR1_AZ_TICKS = (256.5, 705.5, 963.5, 1034.5, 1149.5, 1335.5, 1437.5, 1593.5, 1713.5, 1839.5, 1947.5, 2043.5, 2187.5)


def test_flir1_events():
    """FLIR1's overlay events found with nothing given (2026-10-20): the box found for the pod's azimuth times its ticks
    as the hand-read stretches do; the zoom readout changes three frames after the picture zooms; the recording's held
    frames, among them the switch from the television camera to the infrared."""
    print("\nFLIR1 -- the overlay's own events, found")
    mpg, why = _flir1("f4_2007_archive.mpg")
    if mpg is None:
        print(f"  SKIP  {why}")
        SKIP.append("FLIR1 events")
        return
    from mcdonald import events, forensics as vf
    with tempfile.TemporaryDirectory() as td:
        clip = vf.Clip(mpg, f"{td}/frames")
        f = events.find(clip).fields
    inside = lambda b, x, y: b["box"][0] <= x <= b["box"][2] and b["box"][1] <= y <= b["box"][3]
    az = [b for b in f["boxes"] if inside(b, 172, 27)]
    zoom = [b for b in f["boxes"] if inside(b, 75, 71)]
    check(len(az) == 1 and len(zoom) == 1, "FLIR1: a box found for the azimuth and one for the zoom readout",
          f"{[b['name'] for b in f['boxes']]}")
    if az:
        tk = [t["frame"] for t in az[0]["ticks"]]
        exact = [g for g in FLIR1_AZ_TICKS if any(abs(g - t) <= 1 for t in tk)]
        check(len(exact) >= 12 and all(any(abs(g - t) <= 4 for t in tk) for g in FLIR1_AZ_TICKS),
              "FLIR1: the azimuth's 13 ticks, 12 of them to the frame, as the hand-read stretches time them",
              f"{len(exact)} to the frame; missed {[g for g in FLIR1_AZ_TICKS if g not in exact]}")
    if zoom:
        check(any(abs(t["frame"] - 2237.5) <= 1.5 for t in zoom[0]["ticks"]),
              "FLIR1: the zoom readout's 1.0 -> 2.0, three frames after the picture zooms", f"{[t['frame'] for t in zoom[0]['ticks']]}")
    check(any(a <= 1233 and b >= 1236 for a, b in f["held"]) and any(a <= 530 and b >= 532 for a, b in f["held"]),
          "FLIR1: frames held at 529-534 and 1233-1236 (the switch from TV to IR)", f"{f['held']}")
    # the field of view's mnemonic, `NAR` right under the picture's top edge: within the 8 px static_masks' blocks grow
    # the black surround by, and blurred into one stroke; found since 2026-10-20 (night), with its change to MFOV
    fov = [b for b in f["boxes"] if inside(b, 96, 19)]
    check(len(fov) == 1 and any(abs(t["frame"] - 2166.5) <= 2 for t in fov[0]["ticks"]),
          "FLIR1: a box found for the field of view's mnemonic under the top edge, changing at 2166.5 (NAR to MFOV)",
          f"{[(b['box'], [t['frame'] for t in b['ticks']]) for b in fov]}")


FLIR1_FIELDS = [(2045, 2084, 0.7), (2085, 2139, 0.35), (2140, 2155, 0.7), (2156, 2157, 0.35), (2158, 2207, 1.5),
                (2209, 2217, 6.0), (2218, 2234, 0.7), (2235, 2290, 0.35)]


def test_flir1_fields():
    """FLIR1's last 6 s with the fields its display gives (2026-10-20): the zoom readout's 2.0 over 2158-2209 is the
    medium field at x2 (1.5 deg), and 2209-2217 its wide one (6 deg); the object, 15 px long at NAR x2, is at the copy's
    blur there. The three x2 zooms its size confirms; the changes of field it has no power over; the released-track null
    as before. And `symbology --method atflir` times the field mnemonic's changes, which nobody read at first."""
    print("\nFLIR1, frames 2070-2250 -- the fields of view, as the display gives them")
    mpg, why = _flir1("f4_2007_archive.mpg")
    if mpg is None:
        print(f"  SKIP  {why}")
        SKIP.append("FLIR1 fields")
        return
    from mcdonald import camera, atflir, forensics as vf
    track = vf.read_track(str(HERE / "golden" / "flir1_fields_track.csv"))
    with tempfile.TemporaryDirectory() as td:
        clip = vf.Clip(mpg, f"{td}/frames", 2070, 2250)
        f = camera.measure(clip, track, fov_px=244, fields=FLIR1_FIELDS, centre=(177.5, 121.0), los_rate=0.2466,
                           los_err=0.0051, after=2207)
        st = {x["frame"]: x for x in f.fields["zoom_steps"] if x["ratio_from"] == "field"}
        check(sorted(st) == [2085, 2140, 2156, 2158, 2209, 2218, 2235], "FLIR1: the seven changes of field, as given",
              f"{sorted(st)}")
        check(all(st.get(n, {}).get("size_check") == "confirms" for n in (2085, 2140, 2235)),
              "FLIR1: the three x2 zooms, confirmed by the object's size",
              f"{[(n, st.get(n, {}).get('size_check'), round(st.get(n, {}).get('ratio_from_size') or 0, 2)) for n in (2085, 2140, 2235)]}")
        check(all(st.get(n, {}).get("size_check") == "no power" and "blur" in st.get(n, {}).get("size_why", "")
                  for n in (2156, 2158, 2209, 2218)),
              "FLIR1: NAR -> MFOV x2 and the wide-field interlude: no power, the object at the blur",
              f"{[(n, st.get(n, {}).get('size_check')) for n in (2156, 2158, 2209, 2218)]}")
        r = f.fields["released"]
        check(r is not None and abs(r["fastest"]["deg_per_s"] - 0.293) < 0.01 and r["within_camera_rate"]
              and 3.8 <= r["z_without_scale"] <= 4.8, "FLIR1: the released-track null as with one field: 0.293 deg/s, "
              "+1.5 sigma with the scale's 10 %, +4.3 exact",
              "" if r is None else f"{r['fastest']['deg_per_s']:.3f}, z {r['z']:+.1f} ({r['z_without_scale']:+.1f})")
        whole = vf.Clip(mpg, f"{td}/all")
        a = atflir.measure(whole).fields["fields"]
    ch = [c["frame"] for c in a.get("fov", {}).get("changes", [])]
    check(any(abs(c - 2166.5) <= 2 for c in ch) and any(abs(c - 2219.5) <= 2 for c in ch),
          "FLIR1: the field mnemonic's change of look to MFOV (2167) and back to NAR (2220), timed",
          f"{[c for c in ch if c > 2100]}")


FLIR1_CLOCK = (160, 218, 188, 231)      # the bottom line's `4135` (41:35 on frame 1), x0, y0, x1, y1
FLIR1_FIXED_TEXT = [((198, 15, 226, 24), "RTCL"), ((58, 23, 82, 32), "OPR"), ((234, 218, 268, 228), "DCLTR"),
                    ((258, 168, 290, 178), "LTD/R")]   # text that never changes, read off a frame (2026-10-20)
FLIR1_AZ_DIGIT = [((1, 256), 4), ((721, 961), 2), ((976, 1036), 1), ((1151, 1331), 0), ((1441, 1591), 2),
                  ((1606, 1726), 3), ((1741, 1846), 4), ((1861, 1951), 5), ((1966, 2056), 6), ((2071, 2191), 7),
                  ((2215, 2289), 8)]


def test_flir1_glyphs():
    """FLIR1's own clock as digit templates (2026-10-20): its last digit, read as 5 on frame 1, ticks at the clip's
    second; its ten looks are the display's digits; the azimuth's digit is then suggested on each stretch read by hand.
    Held at what it does now: 10 of 11 right, none wrong, one `?` (8 right, a 0 read as 1 and two `?` before glyphs the
    blur joined were cut at the pitch). And letters from the display's fixed text, read once (2026-10-20, night): with
    the azimuth read as digits and then L or R, its side right on 10 of 11 and wrong on none (over 1151-1331 its glyph
    comes out shorter than 0.7 of the digits, `?`); and atflir, given them and its field of view's `NAR`, gives 22 of
    the azimuth's looks a side and never the wrong one."""
    print("\nFLIR1 -- the clock's digits as templates, and the azimuth read with them")
    mpg, why = _flir1("f4_2007_archive.mpg")
    if mpg is None:
        print(f"  SKIP  {why}")
        SKIP.append("FLIR1 glyphs")
        return
    from mcdonald import glyphs, atflir, forensics as vf
    with tempfile.TemporaryDirectory() as td:
        clip = vf.Clip(mpg, f"{td}/frames")
        tpl, info = glyphs.templates(clip, FLIR1_CLOCK, 1, 5)
        check(tpl is not None and sorted(tpl) == list(range(10)), "FLIR1: ten digits from its clock's last digit",
              f"{sorted(tpl or {})} {info.get('why', '')}")
        if not tpl:
            return
        check(abs(info["clock"]["period_frames"] - clip.fps) < 0.02 and abs(info["clock"]["first_tick"] - 22.5) <= 1.5,
              "FLIR1: the clock's second is the clip's, and its first tick near frame 22.5 (41:35 -> 41:36)",
              f"{info['clock']['period_frames']:.3f} frames, first at {info['clock']['first_tick']:.1f}")
        box = atflir.field_boxes(clip, atflir.picture_box(clip))["az"]
        got = [glyphs.suggest(clip, box, {"x": [span]}, tpl, info["polarity"])["x"]["text"][:1] for span, _ in FLIR1_AZ_DIGIT]
        letters = {}
        for b, text in FLIR1_FIXED_TEXT:
            L, li = glyphs.letter_templates(clip, b, text, list(range(clip.n0, clip.n1 + 1)), info["polarity"])
            for c, Ts in (L or {}).items():
                letters.setdefault(c, []).extend(Ts)
        both = glyphs.with_letters(tpl, letters)
        side = [glyphs.suggest(clip, box, {"x": [span]}, both, info["polarity"], among=set(range(10)),
                               last={"L", "R"})["x"]["text"][-1:] for span, _ in FLIR1_AZ_DIGIT]
        f = atflir.measure(clip, atflir.parse_read("fov:A=NAR"), None, "flir1", clock=(FLIR1_CLOCK, 1, 5),
                           fixed=[(b, t, None) for b, t in FLIR1_FIXED_TEXT])
    right = sum(g == str(v) for g, (_, v) in zip(got, FLIR1_AZ_DIGIT))
    wrong = sum(g not in ("?", str(v)) for g, (_, v) in zip(got, FLIR1_AZ_DIGIT))
    check(right >= 10 and wrong == 0, "FLIR1: the azimuth's digit suggested right on 10 or more of 11 stretches, wrong on "
          "none", f"{right} right, {wrong} wrong: {got}")
    side_at = lambda a, b: "R" if (a + b) / 2 < 1034.5 else "L"     # read from a stretch's middle; R to L at 1034.5
    truth = [side_at(*span) for span, _ in FLIR1_AZ_DIGIT]
    check({"C", "L", "R", "T"} <= set(letters) and sum(a == b for a, b in zip(side, truth)) >= 10
          and all(a in ("?", b) for a, b in zip(side, truth)),
          "FLIR1: letters from RTCL, OPR, DCLTR and LTD/R; the azimuth's side read right on 10 or more of 11 stretches, "
          "wrong on none", f"{''.join(sorted(letters))}: {side}")
    az = f.fields["fields"]["az"]
    seen = {L: (a, b) for a, b, L in reversed(az["stretches"])}
    sides = [(L, t[-1], seen[L]) for L, t in az.get("suggested", {}).items() if t[-1:] in ("L", "R")]
    bad = [x for x in sides if x[1] != side_at(*x[2])]
    check(len(sides) >= 20 and not bad and {"A", "N", "R"} <= set(f.fields["letters"]["chars"]),
          "FLIR1: atflir with the letters (and NAR read off its sheet) gives a side on 20 or more of the azimuth's looks, "
          "never the wrong one", f"{len(sides)} sides, wrong {bad}")


def _aaro(name):
    p = reference_data.root() / "aaro" / "videos" / name
    return (p, None) if p.exists() else (None, f"{p} is not here")


GIMBAL_AZ_TICKS = [23, 41, 65, 89, 107, 131, 155, 173, 197, 221, 239, 257, 275]   # 54 L -> 41 L: the frame that holds a
                                                                                    # field of each, read off every frame
GOFAST_AZ_TICKS = [13.5, 85.5, 133.5, 151.5, 241.5, 259.5]                          # 35 L -> 41 L, read every 1-2 frames
GOFAST_EL_TICKS = [61.5, 139.5, 253.5]                                              # -22 -> -25


def test_atflir_navy():
    """`symbology --method atflir` on the Navy's 2015 GIMBAL and GOFAST, AARO's 1920 x 1080 renditions of a standard-
    definition display, frames 1-300 (2026-10-20): the picture's box, the five fields at their places, and the readouts'
    changes against ticks read by hand off strips. Held at what it does now: GIMBAL's azimuth 12 of 13 within 2 frames,
    and none where no tick is, since its noise is read from its quiet frames (9 before, against ticks first read off a
    strip of every tenth frame); one change of a single segment still does not stand out of its cell (GOFAST's 38 -> 39,
    an 8 to a 9, and GIMBAL's 49 -> 48). A halved cell, a per-segment statistic and keeping 16 times the pixels did no
    better."""
    print("\nGIMBAL and GOFAST, frames 1-300 -- the ATFLIR's fields on a 1080 rendition")
    from mcdonald import atflir, forensics as vf
    for name, file, truth in (("GIMBAL", "DOD_110891172.mp4", dict(az=(GIMBAL_AZ_TICKS, 12))),
                              ("GOFAST", "DOD_110886776.mp4", dict(az=(GOFAST_AZ_TICKS, 5), el=(GOFAST_EL_TICKS, 3)))):
        mp4, why = _aaro(file)
        if mp4 is None:
            print(f"  SKIP  {why}")
            SKIP.append(f"{name} atflir")
            continue
        with tempfile.TemporaryDirectory() as td:
            clip = vf.Clip(mp4, f"{td}/frames", 1, 300)
            f = atflir.measure(clip)
        box, fl = f.fields["picture_box"], f.fields["fields"]
        check(470 <= box[0] <= 480 and 1430 <= box[2] <= 1440 and box[3] - box[1] > 900,
              f"{name}: the picture's box, about 963 px square in the 1080 rendition", f"{box}")
        check({"az", "el", "zoom", "fov", "mode"} <= set(fl), f"{name}: the five fields placed", f"{sorted(fl)}")
        for k, (ticks, need) in truth.items():
            if k not in fl:
                continue
            ch = [c["frame"] for c in fl[k]["changes"] if c["frame"] > 7]     # the clips open on six blank frames
            hit = [t for t in ticks if any(abs(t - c) <= 2 for c in ch)]
            false = [c for c in ch if not any(abs(t - c) <= 4 for t in ticks)]
            check(len(hit) >= need and not false, f"{name}: {k}'s ticks, {need} or more of {len(ticks)} within 2 "
                  "frames, and no change where none is", f"{len(hit)} of {len(ticks)}; not at a tick {false}")
        for k in ("zoom", "fov"):
            st = [x for x in fl.get(k, {}).get("stretches", []) if x[1] > 7]
            check(len({x[2] for x in st}) == 1, f"{name}: {k} holds one look after the blank lead-in",
                  f"{[(a, b, L) for a, b, L in st]}")


def test_flir1_versions():
    """FLIR1's 2007 copy against the official 2020 file (2026-10-20): the 2007 copy keeps more detail and holds fewer of
    its blocks; the official one was relabelled to 30 a second, repeats a frame near 1000 and 2000 (985, 1986), and holds the
    recording's own frames where the 2007 copy does."""
    print("\nFLIR1 -- two copies set side by side")
    mpg, why = _flir1("f4_2007_archive.mpg")
    mp4, why2 = _flir1("DOD_110872545.mp4")
    if mpg is None or mp4 is None:
        print(f"  SKIP  {why or why2}")
        SKIP.append("FLIR1 versions")
        return
    from mcdonald import versions
    f = versions.compare([mpg, mp4], ["2007", "dvids"])
    c0, c1 = f.fields["copies"]
    check(f.fields["best"] == "2007" and 0.55 <= c1["detail_share"] <= 0.75 and c1["still"] > 2 * c0["still"],
          "FLIR1: the 2007 copy is the best source; the official keeps about two thirds of its detail and holds more blocks",
          f"detail {c1['detail_share']:.2f}, blocks held {100 * c1['still']:.0f} % against {100 * c0['still']:.0f} %")
    steps = c1["lag_steps"]
    check(len(steps) == 2 and all(x["by"] == 1 for x in steps) and 900 <= steps[0]["near"] <= 1100
          and 1900 <= steps[1]["near"] <= 2150, "FLIR1: the official copy repeats a frame twice, near 1000 and near 2000",
          f"{steps}")
    check(any("relabelled" in n for n in f.notes) and set(range(1233, 1236)) <= set(f.fields["held_in_every_copy"]),
          "FLIR1: relabelled to 30 a second, and the switch from TV to IR held in both", f"{f.fields['held_in_every_copy']}")


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


def test_svanstrom_helicopter_lights():
    """Item 13 (2026-10-20): two helicopters of the Svanstrom et al. (2021) labelled visible-band set whose lights flash
    in trains (the uap repository's analysis/methods/helicopter_lights.md). V_HELICOPTER_054 carries a white light
    that flashes every 1.00 s, which its dark body hides from the aperture's sum, and a red one every ~1.5 s;
    V_HELICOPTER_030 a red light at 0.74 Hz (44 a minute). Neither the background beside them flashes."""
    print("\nSvanstrom V_HELICOPTER_054 and _030 -- an anti-collision light's train")
    from mcdonald import forensics as vf
    base = reference_data.root() / "svanstrom2021" / "Drone-detection-dataset" / "Data" / "Video_V"
    for clip, curve, hz, tol in (("054", "white", 1.00, 0.02), ("030", "red", 0.74, 0.03)):
        video = base / f"V_HELICOPTER_{clip}.mp4"
        if not video.exists():
            print(f"  SKIP  {video} is not on this computer")
            SKIP.append(f"Svanstrom V_{clip} lights")
            continue
        track = vf.read_track(HERE / "golden" / f"svanstrom_v{clip}_track.csv")
        found = _flicker(video, {"object": track}, min(track), max(track), dark=True)
        b = (found.fields.get("blink") or {}).get("object") or {}
        c = (b.get("curves") or {}).get(curve) or {}
        check(c.get("train") and abs((c.get("hz") or 0) - hz) <= tol and c.get("rule") == "anti-collision",
              f"V_HELICOPTER_{clip}: its {curve} light flashes in a train at {hz:.2f} Hz, an anti-collision light's rate",
              f"{c.get('flashes')} flashes, {c.get('hz')} Hz, p {c.get('p')}, {c.get('rule')}")
        check(b.get("train") and not b.get("shared"), f"V_HELICOPTER_{clip}: the background beside it does not share the train",
              str(b.get("controls")))
        if clip == "054":
            check(not ((b.get("curves") or {}).get("brightness") or {}).get("train"),
                  "V_HELICOPTER_054: its dark body hides the white light from the aperture's sum",
                  str({k: ((b.get("curves") or {}).get("brightness") or {}).get(k) for k in ("flashes", "p")}))


def _thumbs(video, n0=None, n1=None):
    """Frames n0-n1 of a clip (the whole clip if not given) as `flicker.pictures` compares them (`flicker.thumb`), with
    their picture types."""
    from mcdonald import clip as clipmod, flicker, forensics as vf
    clip = vf.Clip(video, None, n0, n1)
    ns = range(clip.n0, clip.n1 + 1)
    return clip, [flicker.thumb(vf.grey_of(clip.rgb(n))) for n in ns], clipmod.picture_types(video, clip.n0, clip.n1)


def test_held_pictures_known_cadences():
    """M3 (2026-10-29; the pure-mathematics survey's census of the data folder, its section 6.1): only a cadence -- a
    slower source on the frame grid, its held frames a balanced word -- lowers the beat band's top. Clips whose cadence
    is known: the Svanstrom set's V_HELICOPTER_020-024, one recording of 25 pictures a second on 30 (one frame in six
    held; 024 to the frame, 020-023 with a frame in a hundred or so misread); PR051's YouTube copy, a 29.97 source doubled
    onto 59.94 (one in two), frames 452-601; PR055's sphere, 16 pictures a second on PURSUE's 30, frames 1068-1300 where it
    is tracked. Each is a cadence at its rate. And PR149's contact, frames 17-98 of its reference case, measured as the
    case measures it: a fifth of its frames repeat, at random. Until 2026-10-29 that put its band's top at 9.3 Hz, so its
    "no beat" covered 0-9.3 Hz; they are missing samples, and the top is the frame grid's 12 Hz."""
    print("\nheld pictures, tested -- known cadences, and PR149's holds at random (M3)")
    from mcdonald import flicker
    base = reference_data.root() / "svanstrom2021" / "Drone-detection-dataset" / "Data" / "Video_V"
    for k in range(20, 25):
        video = base / f"V_HELICOPTER_{k:03d}.mp4"
        if not video.exists():
            print(f"  SKIP  {video} is not on this computer")
            SKIP.append(f"Svanstrom V_{k:03d} cadence")
            continue
        clip, th, types = _thumbs(video)
        p = flicker.pictures(th, clip.fps, types=types)
        check(p["cadence"] is True and abs(p["rate"] - 25.0) <= 0.5 and abs(p["top_hz"] - 10.0) <= 0.2
              and (k != 24 or p["every"] == [1, 6]),
              f"V_HELICOPTER_{k:03d}: 25 pictures a second on 30, a cadence -- the band's top 10 Hz"
              + (", 1 of every 6 frames repeating" if k == 24 else ""),
              f"{p['held']:.3f} held, {p['holds']}, balance {p.get('balance') or 0:.2f} (random words {p.get('balance_random')}), "
              f"{p['rate']:.2f} a second, {p.get('every')}, top {p['top_hz']:.2f} Hz")
    video = reference_data.root() / "pr051" / "yt_nKtJslcHlCQ_1080p60_h264.mp4"
    if video.exists():
        clip, th, types = _thumbs(video, 452, 601)
        p = flicker.pictures(th, clip.fps, types=types)
        check(p["cadence"] is True and abs(p["rate"] - clip.fps / 2) <= 0.6 and abs(p["top_hz"] - flicker.TOP * clip.fps / 4) <= 0.3,
              "PR051's YouTube copy: a 29.97 source doubled onto 59.94, a cadence -- the top 12 Hz, not the grid's 24",
              f"{p['held']:.3f} held, {p['holds']}, balance {p.get('balance') or 0:.2f}, {p['rate']:.2f} a second, {p.get('every')}, "
              f"GOP {p.get('places')}, top {p['top_hz']:.2f} Hz")
    else:
        print(f"  SKIP  {video} is not on this computer")
        SKIP.append("PR051 YouTube cadence")
    video, why = have_clip("PR055")
    if video:
        clip, th, types = _thumbs(video, 1068, 1300)
        p = flicker.pictures(th, clip.fps, types=types)
        check(p["cadence"] is True and abs(p["rate"] - 16.0) <= 0.5 and abs(p["top_hz"] - 6.4) <= 0.3,
              "PR055's sphere, where it is tracked: 16 pictures a second on 30, a cadence -- the top stays lowered, near 6.4 Hz",
              f"{p['held']:.3f} held, {p['holds']}, balance {p.get('balance') or 0:.2f}, {p['rate']:.2f} a second, top {p['top_hz']:.2f} Hz")
    else:
        print(f"  SKIP  {why}")
        SKIP.append("PR055 cadence")
    video, why = have_clip("PR149")
    case = reference_data.root() / "cases" / "pr149.mcdonald"
    if not video or not case.exists():
        print(f"  SKIP  {why or case}")
        SKIP.append("PR149 holds at random")
        return
    import csv, io, zipfile
    with zipfile.ZipFile(case) as z:
        rows = list(csv.DictReader(l for l in io.StringIO(z.read("case/object-1/pr149_track.csv").decode("utf-8")) if not l.startswith("#")))
    track = {int(float(r["frame"])): (float(r["x_px"]), float(r["y_px"])) for r in rows if r["x_px"] not in ("", "nan")}
    f = _flicker(video, {"object": track}, 1, 158).fields
    p = f.get("pictures") or {}
    check(f.get("first") == 17 and f.get("last") == 98 and abs(p.get("held", 0) - 0.22) <= 0.02 and p.get("cadence") is False
          and p.get("holds") == "random" and p.get("top_hz") == flicker.TOP * 30.0 / 2,
          "PR149, frames 17-98: a fifth of its frames repeat at random -- missing samples, and the band's top is the frame "
          "grid's 12 Hz (its reference case's 9.3 until 2026-10-29)",
          f"frames {f.get('first')}-{f.get('last')}, {p.get('held', 0):.3f} held, {p.get('holds')}, balance {p.get('balance') or 0:.2f} "
          f"(random words {p.get('balance_random')}), top {p.get('top_hz')} Hz")


def main():
    full = "--full" in sys.argv
    print("mcDonald UAP Toolkit — golden check against real clips")
    print(f"catalog: {catalog.active().name}; reference data: {reference_data.root()}")
    pages = [a for a in sys.argv[sys.argv.index("--exercises") + 1:] if re.fullmatch(r"\d\d", a)] if "--exercises" in sys.argv else []
    if pages:                                     # one exercise page alone (2026-11-02): the page's own answers, nothing else
        test_exercises(pages)
        print(f"\n{len(FAIL)} FAILED: {', '.join(FAIL)}" if FAIL else f"\nALL PASS (exercise page{'s' if len(pages) > 1 else ''} {', '.join(pages)} alone)")
        return 1 if FAIL else 0
    test_pr113_two_clicks()
    test_pr144_window()
    test_pr43_streak_by_motion()
    test_pr43_speed_band()
    test_checklist_on_the_case_files()
    test_the_birds_bands_held_to_their_tracks()
    test_projective_held_to_the_jitter()
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
    test_pr051_zoom_with_no_blank()
    test_pr051_scene_path_against_the_data_bar()
    test_pr051_released_track_against_the_scene()
    test_puerto_rico_k_from_the_data_bar()
    test_puerto_rico_lanterns_tau_against_their_range()
    test_puerto_rico_lanterns_over_the_doubling()
    test_yemen_line_of_sight_against_the_laser()
    test_flir1_frame_rate()
    test_flir1_zoom_and_release()
    test_flir1_readout()
    test_flir1_events()
    test_flir1_fields()
    test_flir1_glyphs()
    test_atflir_navy()
    test_flir1_versions()
    test_svanstrom_helicopter_lights()
    test_held_pictures_known_cadences()
    if full:
        test_pr144_full()
    else:
        print("\n(--full also checks the whole-clip published values; tens of minutes)")
    if full or "--exercises" in sys.argv:
        test_exercises()
    else:
        print("(--exercises runs each exercise in docs/exercises as its page writes it, about an hour; --exercises 03 one page)")

    if FAIL:
        print(f"\n{len(FAIL)} FAILED: {', '.join(FAIL)}")
        return 1
    print(f"\n{'ALL PASS' if not SKIP else 'ALL PASS (skipped: ' + ', '.join(SKIP) + ')'}")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):           # a pipe or a log file on Windows is cp1252, and the checks' names have arrows
        _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
