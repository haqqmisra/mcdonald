"""AARO's resolved cases run blind: the scorecard, read from the case files (ROADMAP 0.5.0; docs/method.md section 46).

    python3 tools/aaro_blind.py                      # from $MCDONALD_DATA/aaro/blind (tests/reference_data.py finds it)
    python3 tools/aaro_blind.py --blind DIR          # from another folder of .mcdonald files
    python3 tools/aaro_blind.py --markdown           # the table for the folder's README
    python3 tools/aaro_blind.py press CASE           # the protocol's first run of one case, into ./aaro-blind/CASE/first

Every video AARO has published with a stated resolution was run through `mcdonald run` with only what the video and
its public description give (the protocol is the method's section 46): first the one press, with nobody choosing the
object, and, where Find took something other than the object the description is about, a second run from marks
placed on that object. Each run is a shared case file in the folder. This reads each file's reports back
(`Case.load`, nothing measured), takes each conclusion's label, and scores it against AARO's answer by the rule fixed
before the runs (`verdict`). The scorecard of record -- AARO's class and confidence, which object each run followed,
and why it was judged on or off the description's object -- is tests/golden/aaro_blind.json; tests/test_golden.py
holds the files' labels and the verdicts to it.

Scoring measures nothing: the words and numbers are the case files'. `press` is the protocol's first run of one
video (`SEGMENTS` has each video's segment and count, fixed before the runs): the window's one press
(`auto_qt.AutoRun`) from the command line, `look --propose`, the rows the one press takes made object folders by
`mark --no-window --set`, then `run --each` with the quick pass's skip. Every command goes to the run folder's
commands.txt before it runs. It measures, so on a shared machine run it through the job scheduler.
"""
import argparse
import json
import math
import re
import shlex
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE.parent / "tests"))

import reference_data  # noqa: E402

RECORD = HERE.parent / "tests" / "golden" / "aaro_blind.json"

# Each video's segment and count, fixed before the runs (method section 46): (case, video under aaro/videos/, first and
# last frame or None for the whole video, the count of objects the description's account of the sighting gives or None).
# A video of 35 s or less is opened whole; a longer one on 20 s chosen from a 40-tile overview, where the description's
# object is in view and the picture steady, or where the description points.
SEGMENTS = [
    ("PR-016", "DOD_111415209.mp4", None, None),
    ("PR-002", "DOD_111216951.mp4", (1, 600), None),
    ("PR-004", "DOD_111300649.mp4", None, None),
    ("PR-005", "DOD_111311850.mp4", None, None),
    ("PR-006", "DOD_111311856.mp4", None, None),
    ("PR-009", "DOD_111311872.mp4", None, None),
    ("PR-010", "DOD_111294469.mp4", (5000, 5599), None),
    ("Middle East Red Balloon", "DOD_111038535.mp4", (900, 1499), 1),
    ("Al Taqaddum", "DOD_110956846.mp4", (1611, 2210), 1),
    ("Mt. Etna", "DOD_110692791.mp4", (5050, 5249), 1),
    ("Puerto Rico", "DOD_110692805-1920x1080-9000k.mp4", (4400, 4999), 2),
    ("Go Fast", "DOD_110886776.mp4", None, 1),
    ("Western United States", "DOD_109670991.mp4", (1, 600), None),
    ("Atmospheric Wakes, sensor 1", "DOD_109584436.mp4", None, None),
    ("Atmospheric Wakes, sensor 2", "DOD_109584439.mp4", (1600, 2199), None),
    ("PR-007", "DOD_111311861.mp4", None, None),
    ("Middle East Object", "DOD_109584445.mp4", None, None),
]
QUICK = "layers,integrity"          # the quick pass: neither enters the label with no scale or distance given

# The report's labels (report.py) that decline: no class, no speed regime. A "Conclusion" or "Tentative conclusion"
# reached here names neither, since none of these runs is given a scale or a distance.
DECLINES = ("No physical conclusion", "Indeterminate, range needed", "Indeterminate, angle needed", "No conclusion",
            "No conclusion yet", "Tentative conclusion", "Conclusion")
BIRD, SUBSONIC, SUPERSONIC = "Beats like a bird", "Subsonic motion", "Supersonic motion"
BIRDS = ("bird", "birds", "migratory birds")


OUTCOMES = ("agree, informative", "agree, consistent", "disagree", "no power", "Find failed")


def verdict(label, aaro_class):
    """One object's report against AARO's answer, by the rule fixed before the runs (method section 46).

    AARO's resolutions say two things: what the object is, and that it showed no anomalous performance. The report's
    label speaks to the second, and for a bird to the first. So a bird's beat agrees with birds and disagrees with any
    other class; a speed under the speed of sound agrees with any prosaic class, and one over it disagrees; every other
    label is the report declining ("no power"), an outcome of its own. An agreement is **informative** where the label
    names AARO's class (a bird's beat on birds) and **consistent** where no prosaic answer could have failed it
    ("Subsonic motion" beside a balloon): both are counted, apart (the coordinator's scoring, 2026-11-07, from the
    diagnostic-accuracy survey; fixed before AARO's answers were read)."""
    bird = aaro_class.strip().lower() in BIRDS
    if label == BIRD:
        return "agree, informative" if bird else "disagree"
    if label == SUBSONIC:
        return "agree, consistent"
    if label == SUPERSONIC:
        return "disagree"
    return "no power"


def case_verdict(objects, aaro_class):
    """A run's outcome from its objects: [(label, on_object)]. Only the objects on the description's object count; with
    none, Find failed (for a first run) or the marks did (for a second). Any disagreement is the run's; else an
    informative agreement; else a consistent one; else no power."""
    on = [verdict(label, aaro_class) for label, on_object in objects if on_object]
    if not on:
        return "Find failed"
    return next(v for v in ("disagree", "agree, informative", "agree, consistent", "no power") if v in on)


def clopper_pearson(k, n, level=0.95):
    """The exact two-sided interval for k successes in n (Clopper and Pearson 1934), by bisection on the binomial tail."""
    a = (1 - level) / 2
    tail_ge = lambda p: sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1))     # P(X >= k)
    tail_le = lambda p: sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(0, k + 1))     # P(X <= k)

    def solve(f, rising):
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2
            if (f(mid) < a) == rising:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    lower = 0.0 if k == 0 else solve(tail_ge, True)
    upper = 1.0 if k == n else solve(tail_le, False)
    return lower, upper


def labels_in(path):
    """{object-N: (label, headline, checklist answers)} of one case file, read back with nothing measured."""
    from mcdonald.report import Case
    out = {}
    with zipfile.ZipFile(path) as z, tempfile.TemporaryDirectory() as td:
        for name in sorted(n for n in z.namelist() if n.endswith("_case.json")):
            m = re.search(r"(object-\d+)/[^/]+_case\.json$", name)
            key = m[1] if m else "object-1"
            f = Path(td) / key / Path(name).name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(z.read(name))
            c = Case.load(f)
            label, head = c.conclusion()
            out[key] = (label, head, {r["key"]: r["answer"] for r in c.checklist()})
    return out


def scorecard(blind, record=None):
    """Every case of the record, each run's objects with their labels read from its case files (one a video: the
    Atmospheric Wakes case has two), and the verdicts. Returns (rows, summary)."""
    record = record or json.loads(RECORD.read_text(encoding="utf-8"))
    rows = []
    for case in record["cases"]:
        runs = {}
        for run, r in case["runs"].items():
            objs, got, found = [], {}, True
            for file, objects in r["files"].items():
                path = Path(blind) / file
                found = found and path.exists()
                here = labels_in(path) if path.exists() else {}
                for k, o in sorted(objects.items(), key=lambda kv: int(kv[0].split("-")[1])):
                    got[f"{file}:{k}"] = here.get(k, (None, None, {}))
                    objs.append((f"{file}:{k}", got[f"{file}:{k}"][0], o["on_object"]))
            runs[run] = dict(found=found, objects=objs, got=got,
                             verdict=case_verdict([(lab, on) for _, lab, on in objs], case["aaro_class"]))
        rows.append(dict(case=case["case"], aaro_class=case["aaro_class"], confidence=case["confidence"], use=case["use"],
                         runs=runs, scored=runs.get("marked", runs["first"])["verdict"] if case["use"] == "known" else None))
    known = [r for r in rows if r["use"] == "known"]
    return rows, summarize([r["scored"] for r in known], [r["runs"]["first"]["verdict"] for r in known])


def summarize(scored, first=()):
    """The scorecard's numbers over the known answers, each with its exact 95 % interval: the outcomes as they are (no
    power and Find failed beside agree and disagree, never folded into either: Shinkins et al. 2013); coverage, the
    share the report answered (agreed or disagreed); accuracy on the answered ones; and agreement over all, informative
    and consistent apart."""
    n = len(scored)
    tally = {v: sum(x == v for x in scored) for v in OUTCOMES}
    agree = tally["agree, informative"] + tally["agree, consistent"]
    answered = agree + tally["disagree"]
    ci = lambda k, m: list(clopper_pearson(k, m)) if m else None
    return dict(known=n, tally=tally, first={v: sum(x == v for x in first) for v in OUTCOMES},
                answered=answered, coverage=ci(answered, n), agree=agree, accuracy=ci(agree, answered),
                informative=tally["agree, informative"], informative_interval=ci(tally["agree, informative"], n),
                interval=ci(agree, n))


def markdown(rows, summary):
    out = ["| case | AARO's answer | first run (the one press) | marked run | scored |", "|---|---|---|---|---|"]
    for r in rows:
        cells = []
        for run in ("first", "marked"):
            x = r["runs"].get(run)
            if x is None:
                cells.append("--")
                continue
            n, off = len(x["objects"]), sum(not on for _, _, on in x["objects"])
            labs = ", ".join(sorted({str(lab) for _, lab, _ in x["objects"]}))
            cells.append(f"{x['verdict']}: {n} object{'s' if n != 1 else ''}"
                         + (f" ({off} not the description's object)" if off else "") + f", {labs}")
        out.append(f"| {r['case']} | {r['aaro_class']} ({r['confidence']}) | {cells[0]} | {cells[1]} | "
                   f"{r['scored'] or 'weak: not scored'} |")
    pc = lambda iv: f"{100 * iv[0]:.0f}-{100 * iv[1]:.0f} %"
    n, t = summary["known"], summary["tally"]
    out.append("")
    out.append(f"Over the {n} known answers (exact 95 % intervals): " + ", ".join(f"{v} {k}" for v, k in t.items()) + ". "
               f"Coverage, the share the report answered: {summary['answered']} of {n} ({pc(summary['coverage'])}). "
               + (f"Accuracy on those: {summary['agree']} of {summary['answered']} ({pc(summary['accuracy'])}). "
                  if summary["answered"] else "Accuracy on those: none answered. ")
               + f"Agreement over all: {summary['agree']} of {n} ({pc(summary['interval'])}), of which informative "
               f"{summary['informative']} of {n} ({pc(summary['informative_interval'])}). The one press alone: "
               + ", ".join(f"{v} {k}" for v, k in summary["first"].items()) + ".")
    return "\n".join(out)


def _call(cmd, log, out_json=None):
    """Run one command, written to `log` (with the time, and after it its exit and how long it took) before it runs."""
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"# {time.strftime('%H:%M:%S')}\n{' '.join(shlex.quote(str(c)) for c in cmd)}\n")
    t = time.time()
    p = subprocess.run([str(c) for c in cmd], stdout=subprocess.PIPE, text=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"# exit {p.returncode} after {time.time() - t:.0f} s\n")
    if out_json:
        Path(out_json).write_text(p.stdout, encoding="utf-8")
    return p


def press(video, folder, segment=None, objects=None, skip=QUICK):
    """The protocol's first run: the window's one press (`auto_qt.AutoRun`) from the command line. Find over the segment;
    the rows the one press takes (`AutoRun._found`: the N likeliest where a count is given, else row 1 whatever its
    strength and every other row that is not weak), each an object folder by `mark --no-window --set` at the row's own
    seeds, recorded as an agent's with the row and the rule as the reason; then `run --each`. Returns the rows taken."""
    d = Path(folder)
    d.mkdir(parents=True, exist_ok=True)
    log, mc = d / "commands.txt", [sys.executable, "-m", "mcdonald.cli"]
    seg = ["--n0", segment[0], "--n1", segment[1]] if segment else []
    p = _call(mc + ["look", video, "--propose", *seg, "--out", d / "find", "--json"], log, d / "look.json")
    try:
        props = json.loads(p.stdout)["results"]["proposals"]
    except (ValueError, KeyError):
        props = []
    if not props:
        return []
    rows = (list(range(min(objects, len(props)))) if objects else
            [i for i, q in enumerate(props) if i == 0 or q["strength"] != "weak"])
    for j, i in enumerate(rows, 1):
        q = props[i]
        sets = [x for s in re.findall(r"--set (object@\d+=[-\d.]+,[-\d.]+)", q["to_accept"]) for x in ("--set", s)]
        _call(mc + ["mark", video, "--no-window", *seg, *sets, "--why",
                    f"row {i + 1} of {len(props)} of look --propose ({q['strength']}, {q['says']}), taken by the one press's "
                    "rule (auto_qt.AutoRun._found) with nobody looking", "--out", d / f"object-{j}", "--json"],
              log, d / f"mark-{j}.json")
    _call(mc + ["run", video, "--each", d, *seg] + (["--objects", objects] if objects else []) + (["--skip", skip] if skip else [])
          + ["--json"], log, d / "run.json")
    return [r + 1 for r in rows]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["press"]:
        ap = argparse.ArgumentParser(prog="aaro_blind.py press", description=press.__doc__.split("\n")[0])
        ap.add_argument("case", choices=[c for c, *_ in SEGMENTS])
        ap.add_argument("--out", type=Path, default=Path("aaro-blind"), help="the cases' folder (default ./aaro-blind)")
        a = ap.parse_args(argv[1:])
        case, video, segment, objects = next(x for x in SEGMENTS if x[0] == a.case)
        path = reference_data.root() / "aaro" / "videos" / video
        if not path.exists():
            sys.exit(f"{path} is not here")
        folder = a.out / re.sub(r"[^a-z0-9]+", "-", case.lower()).strip("-") / "first"
        rows = press(path, folder, segment, objects)
        print(f"{case}: rows {rows} of Find's list taken; the run is in {folder}" if rows else f"{case}: Find found nothing")
        return 0
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--blind", type=Path, default=reference_data.root() / "aaro" / "blind")
    ap.add_argument("--markdown", action="store_true", help="print the README's table")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rows, summary = scorecard(a.blind)
    if a.json:
        print(json.dumps(dict(rows=[{k: v for k, v in r.items()} for r in rows], summary=summary), indent=1, default=str))
    else:
        print(markdown(rows, summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
