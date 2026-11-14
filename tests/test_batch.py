"""`mcdonald batch` (ROADMAP.md 0.6, objective 1; docs/method.md section 54): many videos with nobody looking, held on
clips drawn here.

    python3 tests/test_batch.py

What it holds the batch to:

- the rules that need no video: how a video is cut, which of Find's proposals are objects and in what order, a list
  file's forms, the audit's draw and its bound, a unit's lock, the job script;
- a list of drawn videos run through a pool, stopped half way and started again, gives the table a run left alone
  gives; what was done is not done twice; `--status` says how each video stands;
- a video that fails is a row with its error and does not stop the rest; one whose picture does not change, and one
  with nothing in it that lasts, are rows that say so;
- each video has its folder, its objects, its index and one case file, which measures again to its numbers;
- each object has its audit: the draw, the sheet, and where a look at it is recorded;
- options that decide results are kept with each video: a video done with others is left, and said.

Portable: needs ffmpeg, and no video data.
"""
import inspect
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcdonald import batch, propose, several, share  # noqa: E402

FAIL = []
W, H = 540, 300
FRAMES = 70


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  [' + str(detail) + ']' if detail != '' else ''}", flush=True)
    if not cond:
        FAIL.append(label)
    return cond


def env_of(td, **more):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent.parent / "src"), MCDONALD_HOME=str(Path(td) / "home"),
               TMPDIR=str(td), **more)
    for k in ("MCDONALD_CATALOG", "MCDONALD_CASES", "MCDONALD_DATA", "MCDONALD_CPUS", "SLURM_JOB_ID", "SLURM_ARRAY_JOB_ID"):
        env.pop(k, None)
    return env


def mcdonald(*args, td=None, **more):
    """(exit code, stdout, stderr) of `mcdonald batch ...`."""
    p = subprocess.run([sys.executable, "-m", "mcdonald.cli", "batch", *map(str, args)], capture_output=True, env=env_of(td, **more),
                       encoding="utf-8", errors="replace")
    return p.returncode, p.stdout, p.stderr


def drawn(td, name, discs, n=FRAMES, seed=7, still=False):
    """A video drawn here, lossless: a smooth sky that never moves, a bright disc that never moves either, and `discs`
    crossing it: [(x0, y0, vx, vy, first frame, last frame, contrast, radius)]."""
    from PIL import Image
    from scipy import ndimage
    src = Path(td) / f"src-{name}"
    src.mkdir(parents=True, exist_ok=True)
    yy, xx = np.mgrid[0:H, 0:W]
    rng = np.random.default_rng(seed)
    bg = ndimage.gaussian_filter(rng.normal(0, 1, (H, W)), 6.0) * 80 + 60 + 250 * (np.hypot(xx - 120.0, yy - 230.0) <= 9.0)
    for k in range(1, n + 1):
        g = bg.copy()
        if not still:
            for x0, y0, vx, vy, a, b, c, r in discs:
                if a <= k <= b:
                    g = g + c * (np.hypot(xx - (x0 + vx * (k - a)), yy - (y0 + vy * (k - a))) <= r)
        Image.fromarray(np.clip(g, 0, 255).astype(np.uint8)).save(src / f"f{k:05d}.png")
    out = Path(td) / f"{name}.mkv"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30000/1001", "-start_number", "1", "-i", str(src / "f%05d.png"),
                    "-c:v", "ffv1", "-pix_fmt", "gray", str(out)], check=True)
    shutil.rmtree(src)
    return out


def proposal(rank, frames, xy, dark=False, seen=None, score=5.0, round_=0.9, tape=False):
    return dict(rank=rank, strength="strong" if score >= 10 else "fair" if score >= 4 else "weak", score=score,
                seen_in=seen or len(frames), background_all_round=round_, scrolling_tape=tape, dark=dark, size_px=9.0, says="drawn",
                track={str(n): [xy[0] + n, xy[1]] for n in frames}, against_background_px_per_frame=1.0,
                mark_at={str(frames[0]): [xy[0] + frames[0], xy[1]], str(frames[-1]): [xy[0] + frames[-1], xy[1]]})


# ---------------------------------------------------------------- the rules, with no video
def test_rules():
    print("\nhow a video is cut, and which of Find's proposals are objects")
    check(batch.cut(2657, 400, 30)[-1] == (2591, 2657) and len(batch.cut(2657, 400, 30)) == 8 and batch.cut(322) == [(1, 322)],
          "a video is cut as the beat sweep cut it: PR073's eight windows, a short video one window")
    w = batch.cut(5291)
    check(w[0][0] == 1 and w[-1][1] == 5291 and all(b - a + 1 <= batch.WINDOW for a, b in w)
          and all(w[i + 1][0] <= w[i][1] - batch.OVERLAP + 1 for i in range(len(w) - 1)),
          "every frame is in a window, each window overlapping the next by 30 frames or more", f"{len(w)} windows")
    windows = {"w00": [proposal(1, range(1, 61), (100, 200), score=6.0), proposal(2, range(1, 61), (100, 200), dark=True, score=12.0),
                       proposal(3, range(10, 30), (500, 500)), proposal(4, range(1, 61), (300, 100), round_=0.1),
                       proposal(5, range(1, 61), (300, 250), tape=True)],
               "w01": [proposal(1, range(50, 120), (102, 201), score=3.0), proposal(2, range(50, 120), (700, 100), score=11.0)]}
    kept, refused = batch.long_lived(windows)
    why = sorted((p["tag"], p["rank"], tuple(p["why"])) for p in refused)
    check(len(kept) == 4 and why == [("w00", 3, ("brief",)), ("w00", 4, ("edge",)), ("w00", 5, ("tape",))],
          "kept: seen on 40 frames or more, with background all round, not a tape; each of the rest with why not", str(why))
    objs = batch.merged(kept)
    spans = sorted((o["a"], o["b"], o["dark"], len(o["src"])) for o in objs)
    check(spans == [(1, 60, True, 1), (1, 119, False, 2), (50, 119, False, 1)],
          "the bright one seen in both windows is one object; the dark one beside it another; one far off a third", str(spans))
    both = next(o for o in objs if len(o["src"]) == 2)
    check(sorted(both["marks"]) == [1, 50, 60, 119] and both["score"] == 6.0,
          "an object seen in two windows has its marks from both, and the better of its two scores", str(sorted(both["marks"])))
    order = [(o["dark"], o["a"]) for o in batch.ordered(objs)]
    check(order == [(True, 1), (False, 50), (False, 1)], "measured in the order of Find's score, the best first", str(order))

    rows = [dict(strength="weak"), dict(strength="fair"), dict(strength="weak"), dict(strength="strong")]
    check(propose.one_press_rows(rows) == [0, 1, 3] and propose.one_press_rows(rows, 2) == [0, 1]
          and propose.one_press_rows(rows, 9) == [0, 1, 2, 3] and propose.one_press_rows([]) == [],
          "the one press's rule is one function for the window and the command line: the first row, and any other not weak; "
          "or the N most likely where a count is given")

    print("\na list file, and what decides a video's results")
    with tempfile.TemporaryDirectory(prefix="mcdonald-batch-test-") as td:
        f = Path(td) / "list.txt"
        f.write_text("# a comment\nPR113 400 420\nPR149 1-158   # the contact\n/some where/a video.mp4\nDOD_1.mp4\n", encoding="utf-8")
        got = batch.read_list(f)
        check(got == [("PR113", 400, 420), ("PR149", 1, 158), ("/some where/a video.mp4", None, None), ("DOD_1.mp4", None, None)],
              "a list: one video a line, a segment as two numbers or A-B, comments left out", str(got))
        f.write_text("# the sweep's\nid\trelease\tfile\tpass\nPR19\t01\tDOD_111688723.mp4\tyes\nPR001\t06\tDOD_9.mp4\tno\n", encoding="utf-8")
        check(batch.read_list(f) == [("DOD_111688723.mp4", None, None), ("DOD_9.mp4", None, None)],
              "a list with named columns (tools/sweep/videos.tsv) is read by them: the video by its file")
    base = dict(window=400, overlap=30, most=12, skip=[], only=[], audit=59, keep_frames=False)
    a, b = batch.make_of(base), batch.make_of(dict(base, keep_frames=True))
    c, d = batch.make_of(dict(base, most=3)), batch.make_of(dict(base, skip=["layers"]))
    check(a == b and a != c and a != d and len({batch.make_id(x) for x in (a, c, d)}) == 3 and a["mcdonald"] == batch.__version__,
          "a video's make: the version and the options that reach the measuring, not where its frames are kept")
    sig = inspect.signature(propose.peaks).parameters
    check(batch.STILL == sig["floor"].default and batch.STILL_SIGMA == sig["sigma"].default,
          "a picture that does not change is held to Find's own floor for a candidate, smoothed as Find smooths",
          f"{batch.STILL} and {sig['floor'].default}")

    print("\nthe audit's draw, and what a look at it bounds")
    track = {n: (100.0 + n, 50.0) for n in range(11, 311)}
    w = batch.leverage(track)
    check(abs(w.sum() - 1) < 1e-12 and w[0] == w[-1] and w[0] > 3.9 * w[len(w) // 2] and abs(w[len(w) // 2] - 0.5 / len(w)) < 1e-6,
          "a frame's weight is half its leverage on a straight-line fit: even in the middle, four times that at the ends",
          f"{w[0] / w[len(w) // 2]:.2f}")
    d1, d2 = batch.audit_draw(track, "a.mp4", "object-1"), batch.audit_draw(track, "a.mp4", "object-1")
    d3 = batch.audit_draw(track, "a.mp4", "object-2")
    check(d1 == d2 and d1["drawn"] != d3["drawn"] and sum(x["times"] for x in d1["drawn"]) == 59 and not d1["whole"]
          and [x["k"] for x in d1["drawn"]] == list(range(1, len(d1["drawn"]) + 1))
          and [x["frame"] for x in d1["drawn"]] == sorted(x["frame"] for x in d1["drawn"]),
          "59 draws, the same every time for one object and others for another, numbered in the video's order",
          f"{len(d1['drawn'])} frames")
    short = batch.audit_draw({n: (1.0, 1.0) for n in range(5, 45)}, "a.mp4", "object-1")
    check(short["whole"] and len(short["drawn"]) == 40 and short["draws"] == 40, "a track of 59 frames or fewer is checked whole")
    ub = batch.upper_bound(0, 59)
    check(abs(ub - (1 - 0.05 ** (1 / 59))) < 1e-9 and ub < 0.05 and batch.upper_bound(0, 58) > 0.05,
          "59 draws with none wrong bound the wrong share under 5 %, and 58 do not", f"{100 * ub:.2f} %")
    from math import comb
    p2 = batch.upper_bound(2, 59)
    tail = sum(comb(59, j) * p2 ** j * (1 - p2) ** (59 - j) for j in range(3))
    check(abs(tail - 0.05) < 1e-9 and 0.09 < p2 < 0.12 and batch.upper_bound(59, 59) == 1.0,
          "with some wrong the bound is the exact binomial one: the share at which so few wrong would be seen 1 time in 20",
          f"{100 * p2:.1f} % for 2 of 59")

    print("\na video's lock, and the job script")
    with tempfile.TemporaryDirectory(prefix="mcdonald-batch-test-") as td:
        one, two = batch.Lock(td), batch.Lock(td)
        check(one.take() and not two.take(), "one process a video: a second cannot take a lock that is held")
        one.release()
        check(two.take(), "and can once it is released")
        two.release()
        (Path(td) / batch.LOCK).write_text(json.dumps(dict(host=batch.socket.gethostname(), pid=2 ** 22 + 12345)), encoding="utf-8")
        check(batch.Lock(td).dead() and one.take(), "a lock left by a process that is no longer running is taken over at once")
        one.release()
        (Path(td) / batch.LOCK).write_text(json.dumps(dict(host="elsewhere", pid=1)), encoding="utf-8")
        fresh = not batch.Lock(td).dead()
        old = time.time() - batch.STALE - 5
        os.utime(Path(td) / batch.LOCK, (old, old))
        check(fresh and batch.Lock(td).dead(), "one made on another computer only when it has shown no sign of life for ten minutes")
    units = [dict(k=0, frames=150, width=1920, height=1080, n0=None, n1=None), dict(k=1, frames=9000, width=1920, height=1080, n0=None, n1=None),
             dict(k=2, frames=200, width=1280, height=720, n0=None, n1=None), dict(k=5, frames=9000, width=1280, height=720, n0=101, n1=300)]
    cs = batch.classes(units, 8)
    check(sum(len(c["units"]) for c in cs) == 4 and cs == sorted(cs, key=lambda c: c["minutes"])
          and all(c["mem_mb"] >= batch.resources(u, 8)[0] for c in cs for u in units if u["k"] in c["units"]),
          "the videos in size classes: each in one, a class's memory its largest video's", str([(c["minutes"], c["units"]) for c in cs]))
    check(batch.resources(units[1], 8)[1] > 5 * batch.resources(units[3], 8)[1] and batch.resources(units[1], 4)[1] > batch.resources(units[1], 8)[1],
          "a segment is sized by its own frames, and fewer CPUs by more time")
    check(batch._ranges([0, 1, 2, 5, 7, 8]) == "0-2,5,7-8", "an array's tasks as sbatch takes them")
    with tempfile.TemporaryDirectory(prefix="mcdonald-batch-test-") as td:
        batch.write_json(Path(td) / batch.PLAN, dict(format=batch.FORMAT, options=base, units=[
            dict(u, name=f"v{u['k']}", folder=f"v{u['k']}", tag=f"v{u['k']}", id=f"V{u['k']}", file=f"v{u['k']}.mp4") for u in
            (dict(x, k=i) for i, x in enumerate(units))]))
        said = []
        r = batch.submit(td, cpus=8, throttle=6, extra="--nice=100 -p some_partition", dry=True, say=said.append)
        script = (Path(td) / "batch.sbatch").read_text(encoding="utf-8")
        lines = (Path(td) / "batch_submit.sh").read_text(encoding="utf-8")
        asks = sorted(ln.split()[1].split("=")[0] for ln in script.splitlines() if ln.startswith("#SBATCH"))
        check(asks == ["--job-name", "--ntasks"] and "--partition" not in script and "--account" not in script
              and '--unit "$SLURM_ARRAY_TASK_ID"' in script and "--table" in script,
              "the job script names no partition and no account; a task of an array is one video, and alone it writes the table")
        check(lines.count("-p some_partition") == len(r["classes"]) + 1 and "--dependency=afterany:" in lines and "%" in lines
              and not r["jobs"] and sum(len(c["units"]) for c in r["classes"]) == 4,
              "what the person passes for sbatch is on every line; the table's job waits for the arrays; --slurm-print submits nothing")


# ---------------------------------------------------------------- drawn videos, through the command
SAME = ("id", "file", "unit", "folder", "first", "last", "state", "outcome", "proposals", "found", "measured", "object", "object_state",
        "found_strength", "found_score", "found_frames", "found_first", "found_last", "found_dark", "followed_frames", "followed_first",
        "followed_last", "size_px", "dark", "label", "headline", "grade", "rate_px_per_s", "rate_is", "beat_hz", "checklist", "reasons",
        "no_power", "no_power_by_stage", "needs", "mcdonald", "make", "audit_frames")


def table(out):
    d = json.loads((Path(out) / "batch.json").read_text(encoding="utf-8"))
    return d, [{k: r.get(k) for k in SAME} for r in d["rows"]]


def states(out):
    return {p.parent.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(out).glob("*/batch_state.json"))}


def end_tree(proc):
    """End a batch and the videos it started: asked to stop where the system can ask, ended outright where it cannot."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=120)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_stop_and_go(td):
    print("\na list of drawn videos through a pool, stopped half way and started again")
    vids = Path(td) / "videos"
    vids.mkdir()
    one = drawn(vids, "one", [(80, 80, 5.0, 1.0, 1, FRAMES, 120, 5.0)])
    two = drawn(vids, "two", [(80, 60, 5.0, 1.0, 1, FRAMES, 120, 5.0), (470, 200, -5.0, -0.5, 4, FRAMES, -110, 5.0)], seed=11)
    brief = drawn(vids, "brief", [(80, 80, 6.0, 1.0, 10, 30, 120, 5.0)], seed=3)
    still = drawn(vids, "still", [], seed=5, still=True, n=45)
    gone = drawn(vids, "gone", [(80, 80, 5.0, 1.0, 1, FRAMES, 120, 5.0)], seed=13, n=45)
    lst = Path(td) / "list.txt"
    lst.write_text(f"# drawn for the test\n{one}\n{two}\n{brief}\n{still}\n{gone}\n", encoding="utf-8")
    a, b = Path(td) / "a", Path(td) / "b"

    # planned, with nothing run: --status
    rc, out, err = mcdonald("--list", lst, "--out", a, "--quick", "--status", "--json", td=td)
    d = json.loads(out) if rc == 0 and out.strip() else None
    check(d is not None and set(d) >= {"command", "results", "no_power", "needs", "exit"} and d["command"] == "batch"
          and [u["state"] for u in d["results"]["units"]] == ["waiting"] * 5 and not list(a.glob("*/object-*")),
          "--status plans and says how each video stands, alone on stdout as JSON, with nothing run", f"exit {rc}")
    plan = json.loads((a / batch.PLAN).read_text(encoding="utf-8"))
    check([u["name"] for u in plan["units"]] == ["one", "two", "brief", "still", "gone"] and plan["options"]["skip"] == sorted(batch.QUICK)
          and plan["units"][0]["frames"] == FRAMES, "the plan lists the videos with their frames, and keeps the options")
    gone.unlink()                                             # planned, and no longer there when its turn comes

    # started in a pool of two, and stopped once a video is being measured
    proc = subprocess.Popen([sys.executable, "-m", "mcdonald.cli", "batch", "--out", str(a), "--pool", "2"], env=env_of(td),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            **({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform == "win32" else {}))
    t0, seen = time.time(), {}
    while time.time() - t0 < 600 and proc.poll() is None:
        try:
            seen = states(a)
        except (OSError, ValueError):                         # a state caught between two names: read it the next time round
            seen = {}
        if any(str(s.get("step", "")).startswith("measuring") for s in seen.values()):
            break
        time.sleep(0.2)
    end_tree(proc)
    rc, out, err = mcdonald("--out", a, "--status", "--json", td=td)
    st = {u["name"]: u["state"] for u in json.loads(out)["results"]["units"]}
    check(any(v != "done" for k, v in st.items() if k in ("one", "two")) and "running" not in st.values()
          and set(st.values()) <= {"done", "stopped", "stalled", "waiting", "failed"},
          "stopped half way: --status says which videos are done, which were stopped and which wait", str(st))
    half = sorted(p.name for p in (a / "two").glob("object-*")) if (a / "two").exists() else []

    # started again: it goes on, and ends with every video an answer
    rc, out, err = mcdonald("--out", a, "--pool", "2", td=td)
    done = states(a)
    check(rc == 1 and {k: v["state"] for k, v in done.items()} == dict(one="done", two="done", brief="done", still="done", gone="failed"),
          "started again, it goes on to the end: four videos done and the one that is not there failed; the exit says a video failed",
          f"exit {rc}; {dict((k, v['state']) for k, v in done.items())}; had {half}")
    check(max(v["attempts"] for k, v in done.items() if k in ("one", "two")) == 2, "a video stopped half way was taken up a second time")

    # a run left alone, in another folder: the same table
    gone = drawn(vids, "gone", [(80, 80, 5.0, 1.0, 1, FRAMES, 120, 5.0)], seed=13, n=45)
    rc, out, err = mcdonald("--list", lst, "--out", b, "--quick", "--status", td=td)
    gone.unlink()
    rc, out, err = mcdonald("--out", b, "--pool", "3", td=td)
    da, ra = table(a)
    db, rb = table(b)
    diff = [(x["unit"], x["object"], k, x[k], y[k]) for x, y in zip(ra, rb) for k in SAME if x[k] != y[k]]
    check(len(ra) == len(rb) == 6 and not diff, "stopped and started again, the table is the one a run left alone gives: every row, "
          "every label and number", f"{len(ra)} and {len(rb)} rows; {diff[:3]}")
    by = {(r["unit"], r["object"]): r for r in da["rows"]}
    check(set(by) == {("one", 1), ("two", 1), ("two", 2), ("brief", None), ("still", None), ("gone", None)},
          "one row an object, and one for each video with none", str(sorted(by, key=str)))
    r = by[("two", 2)]
    check(r["object_state"] == "measured" and r["label"] and r["grade"] and r["followed_frames"] >= 40 and r["dark"] is True
          and r["found_frames"] >= 40 and r["rate_px_per_s"] and 140 < r["rate_px_per_s"] < 160 and r["checklist"].get("checked") == "Not yet"
          and r["sheet_looked"] is False and r["mcdonald"] == batch.__version__ and r["seconds"] > 0,
          "an object's row: how Find saw it, how far it was followed, its report's label, how sure, its rate, each test's answer",
          f"{r['label']}, {r['grade']}, {r['rate_px_per_s']} px/s")
    check(by[("brief", None)]["outcome"] == "nothing found" and "seen too briefly" in by[("brief", None)]["note"]
          and by[("brief", None)]["proposals"] >= 1 and (a / "brief" / "brief_refused.png").exists(),
          "a video with nothing that lasts is a row that says so, with a picture of what was refused", by[("brief", None)]["note"])
    check(by[("still", None)]["outcome"] == "still picture" and "is the same at" in by[("still", None)]["note"],
          "a video whose picture does not change is a row that says so, and is not searched", by[("still", None)]["note"][:60])
    check(by[("gone", None)]["state"] == "failed" and by[("gone", None)]["error"] and "gone.mkv" in by[("gone", None)]["error"],
          "a video that fails is a row with its error, and the others were done", str(by[("gone", None)]["error"])[:80])
    t = da["tally"]
    check(t["videos"] == 5 and t["objects"] == 3 and t["by_outcome"] == {"measured": 2, "failed": 1, "nothing found": 1, "still picture": 1}
          and sum(t["by_label"].values()) == 3 and t["other_make"] == 0,
          "the table's counts: videos by what became of them, objects by their report's label", str(t["by_outcome"]))
    tsv = (a / "batch.tsv").read_text(encoding="utf-8").splitlines()
    md = (a / "batch.md").read_text(encoding="utf-8")
    check(len(tsv) == 7 and len(set(len(ln.split("\t")) for ln in tsv)) == 1 and tsv[0].split("\t")[:3] == ["id", "release", "file"]
          and "check_checked" in tsv[0] and "provisional" in md and "| two |" in md and "failed:" in md,
          "batch.tsv has a row an object under one header; batch.md says the reports are provisional and lists each video")

    print("\nwhat is done is not done twice; other options are another make")
    before = {k: (v["finished"], v["attempts"]) for k, v in states(a).items()}
    stamp = (a / "two" / "object-1" / "two_case.json").stat().st_mtime_ns
    rc, out, err = mcdonald("--out", a, td=td)
    after = {k: (v["finished"], v["attempts"]) for k, v in states(a).items()}
    check(all(after[k] == before[k] for k in ("one", "two", "brief", "still")) and after["gone"][1] == before["gone"][1] + 1
          and (a / "two" / "object-1" / "two_case.json").stat().st_mtime_ns == stamp,
          "run again, the done videos are left as they are, and the failed one is tried again")
    rc, out, err = mcdonald("--out", a, "--most", "1", "--status", "--json", td=td)
    us = {u["name"]: u for u in json.loads(out)["results"]["units"]}
    check(us["two"]["state"] == "done" and us["two"]["make_same"] is False and "another version or with other options" in err,
          "with another cap the done videos are of another make: left as they are, and --status says so")
    rc, out, err = mcdonald("--out", a, "--again", "two", td=td)
    d2, r2 = table(a)
    aside = [p for p in a.iterdir() if p.name.startswith("two.before-")]
    two_rows = [r for r in d2["rows"] if r["unit"] == "two"]
    check(len(aside) == 1 and (aside[0] / "object-2" / "two_case.json").exists() and len(two_rows) == 1 and two_rows[0]["found"] == 2
          and two_rows[0]["measured"] == 1 and d2["tally"]["other_make"] == 3 and "another version of mcdonald or with other options" in
          (a / "batch.md").read_text(encoding="utf-8"),
          "--again does a video again by the new options, its old folder moved aside; two objects found, one measured, one listed; "
          "and the table says which videos are of another make", f"{len(two_rows)} rows, other make {d2['tally']['other_make']}")
    return a, b, vids


def test_folder(a, b, vids, td):
    print("\na video's folder: its objects, its index, its audit, and one case file")
    f = b / "two"
    names = sorted(p.name for p in f.iterdir())
    kept = Path(td) / "home" / "frames"
    check({"batch_state.json", "find", "object-1", "object-2", "two_batch.json", "two_batch.mcdonald", "two_objects.json", "two_objects.md"}
          <= set(names) and (not kept.exists() or not any(kept.iterdir())),
          "the folder holds Find's proposals, each object, the index, the rows and the case file; the frames are gone", str(names))
    idx = json.loads((f / "two_objects.json").read_text(encoding="utf-8"))
    how = idx["objects"][0]["chosen_as"]
    check(len(idx["objects"]) == 2 and how.startswith("agent: spot ") and "with nobody looking" in how and idx["objects"][0]["placed_by"] == ["agent"],
          "each object's marks are recorded as taken by the batch's rule with nobody looking, never as a person's", how[:70])
    case_md = (f / "object-1" / "two_case.md").read_text(encoding="utf-8")
    check("decided by an agent, not by a person looking at the frames" in case_md and "provisional" in case_md,
          "and its report says so on its face, and that its numbers are provisional")
    m = share.read(f / "two_batch.mcdonald")
    check(m["made"]["agent"] and m["made"]["by"] == "mcdonald batch" and "nobody looking" in m["thread"][0]["text"]
          and sum(1 for x in m["files"] if x["path"].endswith("_case.json")) == 2 and m["video"]["name"] == "two.mkv",
          "the case file is a shared file like any other: the video by name and SHA-256, both objects, a note saying how it was made")

    from mcdonald import rerun
    said, was = [], dict(os.environ)
    os.environ.update(env_of(td))                             # the run made again is this checkout's, its frames this test's
    try:
        r = rerun.rerun_file(b / "one" / "one_batch.mcdonald", Path(td) / "rerun", say=said.append, strict=True, also=[vids])
    except Exception as e:                                    # noqa: BLE001
        r = dict(reruns=False, error=f"{type(e).__name__}: {e}", objects={})
    finally:
        os.environ.clear()
        os.environ.update(was)
    check(r["reruns"] and list(r["objects"]) == ["object-1"] and not r["objects"]["object-1"]["differences"],
          "the case file measures again to its numbers by `mcdonald run` on its marks: what the batch gives is what `run` gives",
          r.get("error") or str(r["objects"].get("object-1", {}).get("differences", [])[:2]))

    obj = b / "two" / "object-1"
    au = json.loads((obj / "two_audit.json").read_text(encoding="utf-8"))
    from PIL import Image
    sheet = Image.open(obj / "two_audit.png")
    check(au["frames"] > 59 and au["draws"] == 59 and not au["whole"] and au["looked"] is None and au["sheet"] == "two_audit.png"
          and sheet.size[0] == 10 * 96 * 3 and len(au["drawn"]) <= 59,
          "each object has its audit: 59 draws from its track, and a sheet with a tile for each frame drawn", f"{len(au['drawn'])} frames of {au['frames']}")
    d = au["drawn"][0]
    tile = np.asarray(sheet.convert("L"), float)[:96 * 3, :96 * 3]
    check(tile[96 * 3 // 2 - 6:96 * 3 // 2 + 6, 96 * 3 // 2 - 6:96 * 3 // 2 + 6].mean() > tile.mean() + 60,
          "and the tile is the video's own pixels round the track: the bright disc is in its middle", f"frame {d['frame']}")
    rc, out, err = mcdonald("--audit", obj, td=td)
    check(rc == 0 and "Nobody has recorded a look" in out, "--audit says what was drawn, and that nobody has looked yet", out.strip()[:80])
    rc, out, err = mcdonald("--audit", obj, "--wrong", "none", "--by", "A. Reader", "--json", td=td)
    got = json.loads(out)["results"]["audits"]["object-1"]["looked"] if rc == 0 else {}
    check(got.get("by") == "A. Reader" and got.get("wrong") == [] and got.get("agent") is False and 0.049 < got.get("bound", 1) < 0.05
          and "under 5.0 %" in err,
          "a look with none wrong is recorded with who looked, and bounds the wrong share of the track's weight under 5 %", err.strip()[-90:])
    rc, out, err = mcdonald("--audit", obj, "--wrong", "3,7", "--by", "an agent", "--agent", td=td)
    again = json.loads((obj / "two_audit.json").read_text(encoding="utf-8"))["looked"]
    check(again["wrong"] == [3, 7] and again["agent"] and again["bound"] > 0.08 and "an agent (an AI agent)" in out,
          "a look that found frames wrong records which, and the bound that follows", f"{100 * again['bound']:.1f} %")
    rc, out, err = mcdonald("--audit", obj, "--wrong", "999", td=td)
    check(rc != 0 and "numbered 1 to" in err, "a number the sheet does not have is refused", f"exit {rc}")
    rc, out, err = mcdonald("--out", b, "--table", td=td)
    row = next(r for r in json.loads((b / "batch.json").read_text(encoding="utf-8"))["rows"] if r["unit"] == "two" and r["object"] == 1)
    check(row["audit_looked"] is True and row["audit_wrong"] == 2 and row["audit_bound"] == again["bound"],
          "--table writes the table again from the folders as they are now: the look is in the object's row")


def test_segment(td):
    print("\na named part of a video, and a video given on the command line")
    vids = Path(td) / "videos"
    one = vids / "one.mkv"
    c = Path(td) / "c"
    rc, out, err = mcdonald(f"{one}:11-70", "--out", c, "--quick", "--most", "1", "--json", td=td)
    d = json.loads(out) if out.strip() else {}
    rows = json.loads((c / "batch.json").read_text(encoding="utf-8"))["rows"] if (c / "batch.json").exists() else []
    check(rc == 0 and len(rows) == 1 and rows[0]["first"] == 11 and rows[0]["last"] == 70 and rows[0]["folder"] == "one/segment-11-70"
          and rows[0]["followed_first"] >= 11 and (c / "one" / "segment-11-70" / "object-1" / "one_case.json").exists()
          and d.get("results", {}).get("tally", {}).get("objects") == 1,
          "a part of a video (VIDEO:FIRST-LAST) is searched and measured alone, in its segment's folder", f"exit {rc}; {err[-200:] if rc else ''}")
    from mcdonald import segments
    seg = segments.listed(c / "one", "one")
    check(len(seg) == 1 and (seg[0].n0, seg[0].n1) == (11, 70), "and `mcdonald segments` lists it as it lists any segment")


def main():
    if shutil.which("ffmpeg") is None:
        print("SKIP  ffmpeg is not here")
        return 0
    test_rules()
    with tempfile.TemporaryDirectory(prefix="mcdonald-batch-test-") as td:
        a, b, vids = test_stop_and_go(td)
        test_folder(a, b, vids, td)
        test_segment(td)
    print(f"\n{'ALL PASS' if not FAIL else 'FAILED: ' + '; '.join(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
