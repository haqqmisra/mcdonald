"""Can the whole job be done from the command line alone, by something that cannot click?

    python3 tests/test_cli.py

The windows are held to one list of checks by test_gui.py. This is the third
shell: no display, no window, only `mcdonald <command>` run as a subprocess --
so that the exit code, and a stdout with nothing on it but JSON, are the real
ones -- on a clip made here, with a disc on a known path and a brighter decoy
that never moves (test_measurement's PlantedClip, written out as a lossless
video). It does what an agent would: look at the clip, ask the detector, place
marks with --set, link, and read the answer as JSON.

What it holds the command line to:

- `look` shows the frames it says it shows, and a position read off one of its
  enlarged views is a position in the clip, to the pixel centre;
- `look --propose` lists what moves against the background, the planted object
  first and the brighter static decoy not at all, with the marks that take each;
- a mark placed with --set is an agent's, in every file it reaches, and never a
  hand mark; the case report says so above its bottom line;
- what --set writes is what the window's save writes, from the same marks;
- every command prints the same envelope for --json, alone on stdout, with its
  numbers as fields -- and a number `run` reports is the one the stage's own
  command reports, to the last digit, because both call one function;
- a failure the package expected has its own exit code and a sentence, and is
  told apart from a bug.

Portable: needs ffmpeg, and no video data.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcdonald import forensics as vf  # noqa: E402
from mcdonald import look, mark  # noqa: E402
from test_measurement import PlantedClip  # noqa: E402

FAIL = []
TMP = []                                          # the run's own temporary directory, once there is one
ENVELOPE = {"command", "mcdonald", "inputs", "clip", "files", "results", "no_power", "needs", "notes", "exit", "error"}


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}", flush=True)
    if not cond:
        FAIL.append(label)
    return cond


def mcdonald(*args, cwd=None):
    """(exit code, stdout, stderr) of `mcdonald ...`, as something driving it would see them."""
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent.parent / "src"))
    env.pop("MCDONALD_CATALOG", None)
    env.pop("MCDONALD_CASES", None)
    if TMP:                                       # a command given no --workdir extracts under the temporary directory:
        env["TMPDIR"] = TMP[0]                    # ours, not the machine's shared frame cache
    p = subprocess.run([sys.executable, "-m", "mcdonald.cli", *map(str, args)], capture_output=True, text=True, cwd=cwd, env=env)
    return p.returncode, p.stdout, p.stderr


def as_json(stdout):
    try:
        return json.loads(stdout)
    except ValueError:
        return None


def planted_video(td):
    """PlantedClip as a video file: its frames, encoded losslessly (FFV1), so that what
    ffmpeg hands back is what was planted."""
    from PIL import Image
    clip = PlantedClip(n1=24, seen=range(1, 25))
    src = Path(td) / "src"
    src.mkdir()
    for n in range(clip.n0, clip.n1 + 1):
        Image.fromarray(np.clip(clip.grey(n), 0, 255).astype(np.uint8)).save(src / f"f{n:05d}.png")
    video = Path(td) / "planted.mkv"
    subprocess.run(["ffmpeg", "-v", "error", "-framerate", "30000/1001", "-start_number", "1", "-i", str(src / "f%05d.png"),
                    "-c:v", "ffv1", "-pix_fmt", "gray", str(video)], check=True)
    return clip, video


# ---------------------------------------------------------------- looking
def drive_looking(clip, video, td):
    print("\nlook: seeing the clip with no window")
    case, work = Path(td) / "case", Path(td) / "frames"
    # frames 1-12: the object is 41 px a frame and has left the frame by 13, after which every frame is the same
    rc, out, err = mcdonald("look", video, "--n0", 1, "--n1", 12, "--out", case, "--workdir", work, "--tiles", 6, "--json")
    d = as_json(out)
    check(rc == 0 and d is not None and set(d) == ENVELOPE, "--json is one object, alone on stdout, in the envelope every command prints",
          f"exit {rc}; {sorted(set(d or {}) ^ ENVELOPE) or 'every key'}")
    if not d:
        print(err[-600:])
        return None
    sheet, shown = Path(d["files"][0]), d["results"]["frames_shown"]
    check(sheet.exists() and shown == look.overview_frames(1, 12, 6) and not any(work.glob("*.png")),
          "the overview is written without extracting the clip", f"frames {shown}")
    # are they the frames they say? Each tile against the true frame of that number, and of its neighbours
    from PIL import Image
    tiles, width = np.asarray(Image.open(sheet).convert("L"), float), 384
    th = int(round(width * clip.H / clip.W / 2)) * 2
    wrong = []
    for i, n in enumerate(shown):
        tile = tiles[i // 8 * (th + 26):i // 8 * (th + 26) + th, i % 8 * width:(i % 8 + 1) * width]

        def off(k):
            true = np.asarray(Image.fromarray(np.clip(clip.grey(k), 0, 255).astype(np.uint8)).resize((width, th), Image.LANCZOS), float)
            return np.abs(tile - true).mean()
        if min((k for k in (n - 1, n, n + 1) if 1 <= k <= 12), key=off) != n:
            wrong.append(n)
    check(not wrong, "and each tile is the frame its label says, not a neighbour: ffmpeg selects by number", f"wrong: {wrong}" if wrong else "")

    n = 5
    rc, out, err = mcdonald("look", video, "--frame", n, "--size", 21, "--n0", 1, "--n1", 24, "--at", "244,104",
                            "--out", case, "--workdir", work, "--json")
    d = as_json(out)
    ok = check(rc == 0 and d is not None and len(d["files"]) == 3 and all(Path(f).exists() for f in d["files"]),
               "--frame writes the frame, a sheet of its candidates enlarged, and with --at the loupe", f"exit {rc}")
    if not ok:
        print(err[-600:])
        return None
    cands = d["results"]["candidates"]
    near = min(cands, key=lambda c: np.hypot(c["x"] - clip.truth(n)[0], c["y"] - clip.truth(n)[1]))
    dist = float(np.hypot(near["x"] - clip.truth(n)[0], near["y"] - clip.truth(n)[1]))
    check(dist < 1.5 and [c["rank"] for c in cands] == list(range(1, len(cands) + 1)),
          "the candidates are numbers as well as rings, and one of them is the planted object",
          f"#{near['rank']} of {len(cands)}, {dist:.2f} px from it")
    check(near["rank"] != 1, "and it is not the strongest: the decoy is, which is why choosing is a judgment and not a sort",
          f"#1 is at ({cands[0]['x']:.0f}, {cands[0]['y']:.0f}); the decoy is at {clip.DECOY}")
    check(Image.open(d["files"][0]).size == (clip.W, clip.H), "the frame is written at its own size: a position in the file is a position in the clip")
    return near


def test_a_position_read_off_the_loupe_is_a_position_in_the_clip():
    """The half-pixel question, asked of `look`'s enlarged view as test_gui asks it of the
    windows: one red pixel, and the red block has to be centred on its coordinates."""
    print("\nlook: pixel centres at integers, in the enlarged view too")

    class OneRed:
        W, H, n0, n1, fps = 200, 120, 1, 1, 30.0
        RED = (57, 43)

        def rgb(self, n):
            a = np.full((self.H, self.W, 3), 90, np.float32)
            a[self.RED[1], self.RED[0]] = (255, 0, 0)
            return a
    clip, zoom, box = OneRed(), 6, 96
    x, y = clip.RED
    for at in ((x, y), (x + 7.4, y - 11.2), (20.0, 10.0)):    # centred on it, off to one side, and hanging off the frame's corner
        tile = np.asarray(look.crop_view(clip, 1, at[0], at[1], box=box, zoom=zoom))
        x0, y0 = int(round(at[0])) - box // 2, int(round(at[1])) - box // 2

        def red(dx, dy):
            px, py = (x + dx - x0 + 0.5) * zoom - 0.5, (y + dy - y0 + 0.5) * zoom - 0.5
            r, g, b = tile[int(round(py)), int(round(px))][:3]
            return r > 200 and g < 60 and b < 60
        check(red(0, 0) and all(red(dx, dy) for dx in (-0.4, 0.4) for dy in (-0.4, 0.4))
              and not any(red(dx, dy) for dx, dy in ((-0.6, 0), (0.6, 0), (0, -0.6), (0, 0.6))),
              f"viewed about ({at[0]:g}, {at[1]:g}): red at the pixel's coordinates and 0.4 px either side, not at 0.6")


# ---------------------------------------------------------------- marking and linking
def drive_marking(clip, video, td, found):
    print("\nmark --set --no-window: placing marks with no click, and linking from them")
    case, work = Path(td) / "case", Path(td) / "frames"
    a, b = 2, 6
    # as an agent would: the detector's position on one frame, a position read off the frame on the other
    sets = [f"object@{a}={clip.truth(a)[0] + 0.8:.1f},{clip.truth(a)[1] - 0.6:.1f}",
            f"object@{b}={clip.truth(b)[0] - 0.5:.1f},{clip.truth(b)[1] + 0.7:.1f}"]
    why = "the disc that moves: candidate 2 of 3 at 21 px on frame 5, not the brighter one, which never moves"
    rc, out, err = mcdonald("mark", video, "--no-window", "--link", "--json", "--n0", 1, "--n1", 24, "--out", case,
                            "--workdir", work, "--set", sets[0], "--set", sets[1], "--why", why)
    d = as_json(out)
    ok = check(rc == 0 and d is not None and set(d) == ENVELOPE and d["exit"] == 0 and d["error"] is None,
               "it exits 0 with the envelope, and nothing else on stdout", f"exit {rc}")
    if not ok:
        print(err[-800:])
        return
    names = {Path(f).name for f in d["files"]}
    check(names == {"planted_marks.json", "planted_marks.csv", "planted_marks.png", "planted_autotrack.csv", "planted_autotrack_strip.png"}
          and all(Path(f).exists() for f in d["files"]), "it writes what the window's 's' writes: marks, CSV, contact strip, and the automatic track with its strip",
          ", ".join(sorted(names)))
    v = d["results"]["velocity_px_per_frame"]
    check(v is not None and np.allclose(v, clip.V, atol=0.5), "two marks give the velocity", f"{v} for {clip.V}")

    # whose marks they are
    ms = mark.MarkSet("planted", video, clip.fps).load(case / "planted_marks.json")
    check(all(m["placed_by"] == "agent" and m["how"] == f"agent: {why}" for m in d["results"]["marks"]["object"].values()),
          "the marks are recorded as an agent's, with what it chose and why")
    check(ms.by_hand() == {} and set(ms.not_by_hand()) == {a, b} and ms.kind("object", a) == "agent",
          "and never pass for hand marks: by_hand() has none of them")
    rows = (case / "planted_marks.csv").read_text().splitlines()
    head = [ln for ln in (case / "planted_autotrack.csv").read_text().splitlines() if ln.startswith("#")]
    check("2 of 2 are NOT hand positions" in rows[1] and "agent's judgment" in rows[1] and not rows[0].startswith("# hand marks")
          and [ln for ln in head if "NOT placed by a hand" in ln and why in ln] == [
              f"# the marks on frames {a}, {b} were NOT placed by a hand on the frame -- agent: {why}"] and "linked from marks" in head[0],
          "the marks CSV and the automatic track's header both say so, with the reason -- once, not once per mark")
    by_hand = mark.MarkSet("planted", video, clip.fps)
    for n, (x, y) in ms.marks["object"].items():
        by_hand.add("object", n, x, y)
    saved = json.loads((case / "planted_marks.json").read_text())
    check(saved["classes"] == by_hand.to_dict()["classes"] and set(saved) - set(by_hand.to_dict()) == {"how"},
          "otherwise it is the file a window saves from the same marks: only `how` is added")

    # the link, as fields
    L = d["results"]["link"]["object"]
    track = vf.read_track(case / "planted_autotrack.csv")
    worst = max(np.hypot(x - clip.truth(n)[0], y - clip.truth(n)[1]) for n, (x, y) in track.items())
    size = L["detector"]["size_px"]                  # the detector closes a border of 1.5 sizes, at the scale it chose
    on_frame = [n for n in range(1, 25) if clip.truth(n)[0] < clip.W - int(1.5 * size)]
    check(L["frames_linked"] == len(track) and sorted(track) == on_frame and worst < 1.5,
          "the link follows the planted object for as long as it is in the frame, and not the brighter decoy",
          f"frames {min(track)}-{max(track)}, worst {worst:.2f} px from the truth")
    check(L["concerns"] == [] and L["disputed_frames"] == [] and all(v is not None and v < 2 for v in L["px_from_each_mark"].values()),
          "a link with nothing wrong with it has no concerns", L["summary"][:70])
    check(any("strip" in n for n in d["needs"]), "and still says what it cannot know: that the marks were on the object -- look at the strip")

    # a link that should worry whoever reads it says so in a field, not only in prose
    rc, out, err = mcdonald("mark", video, "--no-window", "--link", "--json", "--n0", 1, "--n1", 24, "--out", Path(td) / "case2",
                            "--workdir", work, "--set", sets[0], "--set", f"object@{b}={clip.DECOY[0]},{clip.DECOY[1]}")
    d2 = as_json(out)
    L2 = ((d2 or {}).get("results", {}).get("link") or {}).get("object", {})
    check(d2 is not None and (L2.get("concerns") or d2["exit"] == 5), "marks that are not on one thing give a link with concerns, or none at all",
          "; ".join(L2.get("concerns", []))[:110] or str((d2 or {}).get("error")))
    check(d2 is not None and any("no --why" in n for n in d2["notes"]), "and marks set without --why are told that the record has no reason in it")
    return case


def drive_the_report(video, td, case):
    print("\nrun --marks: a report built on an agent's marks says so on its face")
    rc, out, err = mcdonald("run", video, "--marks", case / "planted_marks.json", "--n0", 1, "--n1", 24, "--out", case,
                            "--workdir", Path(td) / "frames", "--only", "ingest,track,kinematics,report", "--json")
    d = as_json(out)
    ok = check(rc == 0 and d is not None and set(d) == ENVELOPE and d["command"] == "run", "run --json prints the case in the same envelope", f"exit {rc}")
    if not ok:
        print(err[-800:])
        return
    md = (case / "planted_case.md").read_text()
    top = md[:md.index("## Bottom line")]
    check("decided by an agent, not by a person" in top and "agent: the disc that moves" in top,
          "the report says who identified the object, above the bottom line, with the reason given")
    check(d["results"]["identified_by"]["not_by_hand"] and json.loads((case / "planted_case.json").read_text())["identified_by"],
          "and so do the JSON on stdout and the case file")
    check(any("kinematics" in k for k in d["results"]["stages"]) and isinstance(d["no_power"], list),
          "the stages' results are fields, with what had no power beside them", ", ".join(d["results"]["stages"]))
    return d


def drive_proposing(clip, video, td):
    """`look --propose`: the window's Find the object, for something that cannot click."""
    print("\nlook --propose: what moves against the background, to say yes or no to")
    case = Path(td) / "proposing"
    rc, out, err = mcdonald("look", video, "--n0", 1, "--n1", 24, "--propose", "--procs", 2, "--out", case, "--workdir", Path(td) / "frames", "--json")
    d = as_json(out)
    ok = check(rc == 0 and d is not None and set(d) == ENVELOPE and d["results"]["proposals"], "the same envelope, with the proposals as fields", f"exit {rc}")
    if not ok:
        print(err[-800:])
        return
    first = d["results"]["proposals"][0]
    far = max(np.hypot(x - clip.truth(int(n))[0], y - clip.truth(int(n))[1]) for n, (x, y) in first["track"].items())
    check(first["rank"] == 1 and far < 3.0 and not first["dark"] and abs(first["against_background_px_per_frame"] - np.hypot(41, 6)) < 1.5,
          "the first is the planted disc -- not the brighter one that never moves, which is no proposal at all", f"worst {far:.1f} px; {first['says']}")
    check(first["background_all_round"] > 0.5, "and says how much of the way round it the frame shows background: a spot, not an edge",
          str(first["background_all_round"]))
    rc2, out2, _ = mcdonald("look", video, "--n0", 1, "--n1", 24, "--propose", "--more", "--procs", 2, "--out", case,
                            "--workdir", Path(td) / "frames", "--json")
    more = json.loads(out2)["results"]["proposals"] if rc2 == 0 else []
    check(rc2 == 0 and len(more) >= len(d["results"]["proposals"]) and more[0]["track"] == first["track"],
          "--more lists everything that was kept, best first, as the window's Show more does", f"{len(d['results']['proposals'])} rows, {len(more)} with --more")
    check(Path(d["files"][0]).exists() and "proposals" in Path(d["files"][0]).name and any("judgment" in n for n in d["needs"]),
          "a sheet of strips is written to be looked at, and `needs` says the choice is the looker's")
    check(first["to_accept"].startswith("mcdonald mark ") and "--no-window --link" in first["to_accept"] and "--why" in first["to_accept"]
          and all(f"object@{n}=" in first["to_accept"] for n in first["mark_at"]),
          "each proposal comes with the command that takes it: marks at its seeds, and a --why to be finished by whoever looked")
    sets = [a for n, (x, y) in first["mark_at"].items() for a in ("--set", f"object@{n}={x},{y}")]
    rc, out, err = mcdonald("mark", video, "--no-window", "--link", "--n0", 1, "--n1", 24, "--out", case, "--workdir", Path(td) / "frames",
                            *sets, "--why", "proposal 1: I looked at its strip; the disc that moves", "--json")
    m = as_json(out)
    link = ((m or {}).get("results", {}).get("link") or {}).get("object", {})
    check(rc == 0 and link.get("frames_linked", 0) >= 10 and not link.get("concerns")
          and all(v["placed_by"] == "agent" for v in m["results"]["marks"]["object"].values()),
          "taken that way, the marks are the agent's, and the link from them has no concerns", link.get("summary", str((m or {}).get("error")))[:100])
    rc, out, err = mcdonald("look", video, "--n0", 14, "--n1", 24, "--propose", "--procs", 2, "--out", case, "--workdir", Path(td) / "frames", "--json")
    d = as_json(out)
    check(rc == 5 and d is not None and d["exit"] == 5 and not d["results"]["proposals"] and d["no_power"],
          "5: where nothing moves -- the disc has left the frame -- there is no proposal, and that is said, not an empty sheet", str((d or {}).get("error"))[:90])


# ---------------------------------------------------------------- failing
def drive_failing(video, td):
    print("\nexit codes: an expected failure is told apart from a bug")
    rc, out, err = mcdonald("nonsense")
    check(rc == 2 and "unknown command" in err, "2: an unknown command")
    rc, out, err = mcdonald("--help")
    check(rc == 0 and "exit codes" in out and all(f"\n  {k}  " in out for k in range(6)), "`mcdonald --help` lists what each code means")
    rc, out, err = mcdonald("mark", video, "--no-window", "--set", "object@2=nowhere", "--out", Path(td) / "c3")
    check(rc == 2 and "CLASS@FRAME=X,Y" in err, "2: a --set that cannot be read, with the form it should take", err.strip()[-70:])
    rc, out, err = mcdonald("mark", video, "--no-window", "--set", "object@2=9000,10", "--out", Path(td) / "c3")
    check(rc == 2 and "not on it" in err, "2: a mark that is not on the clip")
    rc, out, err = mcdonald("look", Path(td) / "no-such-clip.mp4", "--json")
    d = as_json(out)
    check(rc == 4 and d is not None and d["exit"] == 4 and "no such file" in d["error"] and "Traceback" not in err,
          "4: a clip that is not there -- and with --json the sentence is in the envelope")
    rc, out, err = mcdonald("look", Path(__file__))
    check(rc == 4 and "is not a video ffmpeg can read" in err and "Traceback" not in err, "4: a file that is not a video")
    rc, out, err = mcdonald("mark", video, "--no-window", "--out", Path(td) / "c4")
    check(rc == 5 and "there are no marks" in err, "5: nothing to work on -- no marks")
    rc, out, err = mcdonald("mark", video, "--no-window", "--link", "--json", "--n0", 1, "--n1", 24, "--out", Path(td) / "c5",
                            "--workdir", Path(td) / "frames", "--set", "boresight@3=270,150")
    d = as_json(out)
    check(rc == 5 and d is not None and d["exit"] == 5 and "no marks of object" in d["error"] and Path(d["files"][0]).exists(),
          "5: --link with no object marked; the marks are still saved, and the envelope says both")


def drive_the_other_commands(video, td, case, ran):
    print("\n--json on a measuring command: its numbers are fields, and the same numbers `run` has")
    track = case / "planted_autotrack.csv"
    rc, out, err = mcdonald("kinematics", video, "--track", track, "--json")
    d = as_json(out)
    ok = check(rc == 0 and d is not None and set(d) == ENVELOPE and d["command"] == "kinematics", "kinematics --json: the same envelope", f"exit {rc}")
    if ok:
        v = d["results"].get("v_px_per_s")
        want = float(np.hypot(41.0, 6.0)) * 30000 / 1001  # PlantedClip moves (41, 6) px a frame, at the video's 30000/1001 fps
        check(isinstance(v, float) and abs(v / want - 1) < 0.002, "v_px is a number in the results, and the planted rate",
              f"{v} px/s; planted {want:.1f}")
        mine = ((ran or {}).get("results", {}).get("fields", {}).get("kinematics") or {}).get("v_px_per_s")
        check(mine == v, "and `run` reports the same number, to the last digit: it is the same function", f"run {mine}, kinematics {v}")
        check(any("v_px" in ln for ln in d["results"]["said"]) and f"{v:.1f} px/s" in " ".join(d["results"]["said"]),
              "what it printed for a person is beside the fields, and says the same")
    else:
        print(err[-800:])
    rc, out, err = mcdonald("layers", video, "--track", track, "--n0", 1, "--n1", 24, "--out", case, "--workdir", Path(td) / "frames",
                            "--procs", 2, "--json")
    d = as_json(out)
    check(rc == 0 and d is not None and d["results"]["px_per_s"]["all"] is None and any(t == "layers" for t, _ in d["no_power"]),
          "layers --json on 24 frames: under a second of clip gives no one-second window, and that is a no_power entry, not an empty table",
          str((d or {}).get("no_power"))[:90])

    rc, out, err = mcdonald("groups", video, "--track", track, "--workdir", Path(td) / "frames", "--out", case, "--json")
    d = as_json(out)
    check(rc == 0 and d is not None and set(d) == ENVELOPE and d["command"] == "groups" and d["results"]["several"] is False
          and d["results"]["frames"] > 0 and any("not a group" in ln for ln in d["results"]["said"]),
          "groups --json: the planted disc is one thing, not a group of points, as a field and as a line",
          f"exit {rc}; {str((d or {}).get('results', {}).get('finding'))[:70]}")
    rc, out, err = mcdonald("run", video, "--track", track, "--n0", 1, "--n1", 24, "--out", case, "--workdir", Path(td) / "frames",
                            "--size", 15, "--only", "ingest,track,groups,report", "--json")
    mine = ((as_json(out) or {}).get("results", {}).get("fields", {}).get("groups") or {})
    check(rc == 0 and mine.get("skipped_because_size_px") == 15.0 and mine.get("several") is None,
          "and `run` does not ask it of a thing linked as a spot larger than a point", str(mine)[:80])

    print("\n--json on a command that writes a picture")
    rc, out, err = mcdonald("tracksheet", video, "--track", case / "planted_autotrack.csv", "--n0", 1, "--n1", 24, "--out", case,
                            "--workdir", Path(td) / "frames", "--cols", 8, "--tile", 128, "--procs", 2, "--json")
    d = as_json(out)
    ok = check(rc == 0 and d is not None and set(d) == ENVELOPE and d["command"] == "tracksheet", "the same envelope, alone on stdout", f"exit {rc}")
    if not ok:
        print(err[-800:])
        return
    check(any(f.endswith("_all_frames.jpg") for f in d["files"]) and d["results"]["said"] and "frames" in " ".join(d["results"]["said"]),
          "with the files it wrote, and what it said as lines", ", ".join(Path(f).name for f in d["files"]))
    r = d["results"]
    check(r["frames"] == 24 and r["detected"] + r["interpolated"] + r["outside_every_track"] == 24 and r["detected"] >= 10
          and isinstance(r["contrast_dn"]["median"], float) and isinstance(r["weak_frames"], list),
          "and what the sheet found as fields: frames detected, interpolated and outside the track, the contrast under it",
          f"{r['detected']} detected, {r['interpolated']} interpolated, {r['outside_every_track']} outside; median {r['contrast_dn']['median']:.0f} DN")
    rc, out, err = mcdonald("tracksheet", video, "--track", Path(td) / "no-such-track.csv", "--json")
    d = as_json(out)
    check(rc == 4 and d is not None and d["exit"] == 4 and d["error"], "and a track file that is not there is a 4 with a sentence, not a traceback",
          str((d or {}).get("error"))[:80])


def test_the_whole_job_from_the_command_line():
    if shutil.which("ffmpeg") is None:
        print("\n  SKIP  ffmpeg is not installed")
        return
    with tempfile.TemporaryDirectory() as td:
        TMP[:] = [td]
        clip, video = planted_video(td)
        found = drive_looking(clip, video, td)
        case = drive_marking(clip, video, td, found)
        drive_proposing(clip, video, td)
        if case:
            ran = drive_the_report(video, td, case)
            drive_the_other_commands(video, td, case, ran)
        drive_failing(video, td)


def main():
    print("McDonald UAP Toolkit — the command line alone")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{'ALL PASS' if not FAIL else str(len(FAIL)) + ' FAILED: ' + ', '.join(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
