"""`flicker` on every labelled track of the infrared set, under both beat rules, with the curves saved (ROADMAP.md 0.5).

    python3 tools/controls/run_set.py RUNS --clips IR_BIRD_001,IR_DRONE_010     # some clips' tracks
    python3 tools/controls/run_set.py RUNS --task 7 --per 2                     # the 15th and 16th clips (a job array's task)
    python3 tools/controls/run_set.py RUNS --list                               # how many clips there are, for the array

Each labelled track (`tracks/index.tsv` beside the tracks `svanstrom_labels.py` wrote, in the reference-data folder) goes
through `flicker.measure` as `mcdonald run` puts an object through it -- the aperture following the object's size, the
object's polarity from its pixels, the clip's other tracks avoided, the scene's own motion read at a beat that would name
a bird (`scene="bird"`) -- once under the stage's rule and once under the paper's. Nothing is tuned per clip.

For each track, in RUNS/<clip>_<object>/:
  stage.json.gz, paper.json.gz   the measurement's fields (`Found.fields`), its no-power reasons and its notes
  curves.json.gz                 everything `flicker.judge` was given -- the curves of the object, of its background
                                 apertures and of its lights, its size and ring level on each frame, its smoothed track,
                                 the fields measured before the judging, and the planted dots of the encoding control where
                                 they were made -- so that the judging can be replayed with no video (`replay`)
  <rule>_flicker.csv             the light curves as the stage writes them
and the replay is checked against the measurement at once: `replay.json` says, rule by rule, whether the curves give back
the same call. The table of every track is `summarise.py`'s.

A clip's tracks run one after another in one task, into a frame folder of the task's own that is removed after it
(two tracks of one clip extracting at once into one folder once left a gap the package did not see, 2026-10-20).
Run through the job scheduler (`svanstrom.sbatch`): 432 tracks, two measurements each."""
import argparse
import copy
import csv
import gzip
import json
import shutil
import sys
import time
import traceback
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))
sys.path.insert(0, str(HERE.parent.parent / "tests"))

from mcdonald import flicker, forensics as vf, planted, report  # noqa: E402
import reference_data  # noqa: E402

RULES = ("stage", "paper")
SCENE = "bird"       # as `mcdonald run` asks it (stages.py): the scene's own motion at a beat that would name a bird


TRACKS = None        # the tracks' folder, where it is not the reference-data folder's (`--tracks`)


def tracks_dir():
    return Path(TRACKS) if TRACKS else reference_data.root() / "svanstrom2021" / "tracks"


def index(path=None):
    """The index's rows that have a track, in its order."""
    path = Path(path or tracks_dir() / "index.tsv")
    with open(path, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f, delimiter="\t") if r["track"]]


def clips(rows):
    """The clips with a track, in the index's order."""
    return list(dict.fromkeys(r["clip"] for r in rows))


def plain(x):
    """`x` with numpy's numbers and arrays made JSON's, tuples made lists."""
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    if isinstance(x, np.ndarray):
        return plain(x.tolist())
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(x)                     # json writes NaN and Infinity, and reads them back
    if isinstance(x, Path):
        return str(x)
    return x


def write_gz(path, obj):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(plain(obj), f, separators=(",", ":"))


def read_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


class Capture:
    """`flicker.judge`'s inputs and the planted dots, kept as the measurement passes them (the first judging only)."""

    def __init__(self):
        self.judged, self.dots = None, None
        self._judge, self._dots = flicker.judge, planted.dots

    def __enter__(self):
        def judge(raw, ns, fps, lines, fields, first, **kw):
            if self.judged is None:
                self.judged = copy.deepcopy(dict(raw=raw, ns=[ns[0], ns[-1]], fps=fps, lines=lines, fields=fields, first=first,
                                                 positions=kw.get("positions"), lit=kw.get("lit"), each=kw.get("each")))
            return self._judge(raw, ns, fps, lines, fields, first, **kw)

        def dots(*a, **kw):
            got = self._dots(*a, **kw)
            if self.dots is None:
                self.dots = {k: got[k] for k in ("before", "after", "skipped") if k in got}
            return got
        flicker.judge, planted.dots = judge, dots
        return self

    def __exit__(self, *exc):
        flicker.judge, planted.dots = self._judge, self._dots


def replay(saved, rule, nulls=False):
    """`flicker.judge` (and the lights' train, item 13) on saved curves, under `rule`: the measurement's Found, made with no
    video. The astronomer's fold and the scene's own motion need the frames, and are not replayed. The fold changes no call;
    the scene's motion at a beat (`beat.shaken`, which keeps a bird from being named) is carried over from the measurement
    (`saved["shake"][rule]`, `with_shake`) to a beat the replay finds at the same frequency, and is otherwise not read."""
    S = copy.deepcopy(saved)
    ns = list(range(S["ns"][0], S["ns"][1] + 1))
    raw = {k: list(v) for k, v in S["raw"].items()}
    fields = S["fields"]
    fields["spans"] = {k: tuple(v) for k, v in fields["spans"].items()}
    pos = {k: (np.asarray(v[0], float), np.asarray(v[1], float)) for k, v in (S.get("positions") or {}).items()}
    lit = {k: [None if q is None else tuple(q) for q in v] for k, v in (S.get("lit") or {}).items()}
    each = {k: [None if q is None else tuple(q) for q in v] for k, v in (S.get("each") or {}).items()}
    dots = S.get("dots")
    enc = (lambda hz, amp, top: planted.at_beat(dots, hz, amp, S["fps"], top=top)) if dots else None
    token = flicker._RULE.set(rule)
    try:
        fields["rule"] = rule
        found = flicker.judge(raw, ns, S["fps"], S["lines"], fields, S["first"], say=lambda *a: None, positions=pos or None,
                              nulls=nulls, encoding=enc, lit=lit or None, each=each or None)
        flicker.blink_reading(found, raw, lit, ns, S["fps"], bool(S.get("dark")), bool(S.get("black_hot")))
    finally:
        flicker._RULE.reset(token)
    found.fields["rule"] = rule
    for n, sh in ((S.get("shake") or {}).get(rule) or {}).items():
        b = (found.fields.get("beat") or {}).get(n)
        if b is not None and sh.get("hz") is not None and abs(b["hz"] - sh["hz"]) < 1e-9:
            b["shaken"] = sh["shaken"]
    return found


def with_shake(saved, fields_by_rule):
    """`saved` with each rule's reading of the scene's own motion at a beat (`beat.shaken`, from the measurement's fields)
    kept beside the curves, for `replay`."""
    saved["shake"] = {rule: {n: dict(hz=b.get("hz"), shaken=b["shaken"]) for n, b in ((ff or {}).get("beat") or {}).items()
                             if b.get("shaken")} for rule, ff in fields_by_rule.items()}
    return saved


def outcome(ff):
    """What a measurement's fields say, in the few values a control is held to: {beats, strong, hz, amplitude, comes_back,
    named (`report.bird_beats`, and no beat the camera's own shake may make: `report.Case.conclusion`'s rule), train}."""
    b = (ff.get("beat") or {}).get("object") or {}
    bl = ((ff.get("blink") or {}).get("object") or {})
    return dict(beats=ff.get("beats"), strong=list(ff.get("strong") or []), hz=b.get("hz"), amplitude=b.get("amplitude"),
                comes_back=b.get("comes_back"), named=any(not x.get("shaken") for x in report.bird_beats(ff).values()),
                train=bool(bl.get("train")))


def same(a, b):
    """Two outcomes agree: the same call, and the same beat to the rounding of the CSV."""
    if a["beats"] != b["beats"] or a["strong"] != b["strong"] or a["named"] != b["named"] or a["train"] != b["train"] \
            or a["comes_back"] != b["comes_back"]:
        return False
    for k in ("hz", "amplitude"):
        if (a[k] is None) != (b[k] is None) or (a[k] is not None and abs(a[k] - b[k]) > 1e-6 * max(1.0, abs(a[k]))):
            return False
    return True


def one(row, runs, workdir, procs=1, say=print):
    """One labelled track under both rules: writes RUNS/<clip>_<object>/ and returns its replay check."""
    d = Path(runs) / f"{row['clip']}_{row['object']}"
    d.mkdir(parents=True, exist_ok=True)
    root = tracks_dir().parent
    video = reference_data.root() / "svanstrom2021" / row["video"]
    track = vf.read_track(root / row["track"])
    avoid = {f"tracks/{Path(p).stem}": vf.read_track(root / p) for p in row["avoid"].split(",") if p} or None
    dark = row["dark"] == "1"
    clip = vf.Clip(video, workdir, min(track), max(track))
    live, saved = {}, None
    for rule in RULES:
        t0 = time.time()
        with Capture() as cap:
            try:
                found = flicker.measure(clip, {"object": track}, dark=dark, out=str(d / rule), say=lambda *a: None, procs=procs,
                                        rule=rule, avoid=avoid, scene=SCENE)
                rec = dict(fields=found.fields, no_power=found.no_power, notes=found.notes, error=None)
            except Exception as e:                      # a track the stage cannot measure is a result too, and said
                rec = dict(fields={}, no_power=[], notes=[], error=f"{type(e).__name__}: {e}",
                           traceback=traceback.format_exc()[-2000:])
        rec.update(seconds=round(time.time() - t0, 1), rule=rule, clip=row["clip"], object=row["object"], cls=row["cls"],
                   distance=row["distance"], dark=dark)
        write_gz(d / f"{rule}.json.gz", rec)
        live[rule] = outcome(rec["fields"]) if not rec["error"] else None
        if saved is None and cap.judged is not None:
            saved = dict(cap.judged, dots=cap.dots, dark=dark, black_hot=False, clip=row["clip"], object=row["object"],
                         cls=row["cls"], distance=row["distance"], track=row["track"], video=row["video"],
                         made_by="tools/controls/run_set.py")
        elif saved is not None and saved.get("dots") is None and cap.dots is not None:
            saved["dots"] = cap.dots
        say(f"  {row['clip']}_{row['object']} {rule}: {rec['seconds']:.0f} s, "
            + (rec["error"] or f"beats {rec['fields'].get('beats')}, named {live[rule]['named']}"))
    check = {}
    if saved is not None:
        with_shake(saved, {rule: (read_gz(d / f"{rule}.json.gz") or {}).get("fields") for rule in RULES})
        write_gz(d / "curves.json.gz", saved)
        for rule in RULES:
            try:
                got = outcome(replay(saved, rule).fields)
                check[rule] = dict(same=bool(live[rule] is not None and same(got, live[rule])), live=live[rule], replay=got)
            except Exception as e:
                check[rule] = dict(same=False, live=live[rule], error=f"{type(e).__name__}: {e}")
    (d / "replay.json").write_text(json.dumps(plain(check), indent=1))
    return check


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("runs", help="where each track's folder goes")
    ap.add_argument("--clips", help="clips by name, comma-separated")
    ap.add_argument("--task", type=int, help="a job array's task: clips task*per .. task*per+per-1 of the index's")
    ap.add_argument("--per", type=int, default=1, help="clips a task (default 1)")
    ap.add_argument("--tracks", help="the tracks' folder and its index.tsv (default: the reference-data folder's svanstrom2021/tracks)")
    ap.add_argument("--work", help="the frame folders' parent (default: RUNS/../frames)")
    ap.add_argument("--procs", type=int, default=1)
    ap.add_argument("--list", action="store_true", help="print the number of clips and tracks, and stop")
    ap.add_argument("--again", action="store_true", help="measure a track again even where its results are there")
    a = ap.parse_args(argv)
    global TRACKS
    TRACKS = a.tracks
    rows = index()
    names = clips(rows)
    if a.list:
        print(len(names), "clips,", len(rows), "tracks")
        return 0
    if a.clips:
        want = a.clips.split(",")
    elif a.task is not None:
        want = names[a.task * a.per:(a.task + 1) * a.per]
    else:
        ap.error("give --clips or --task")
    bad = 0
    for name in want:
        work = Path(a.work or Path(a.runs).parent / "frames") / name
        try:
            for row in [r for r in rows if r["clip"] == name]:
                d = Path(a.runs) / f"{row['clip']}_{row['object']}"
                if not a.again and (d / "replay.json").exists():
                    continue
                check = one(row, a.runs, work, a.procs)
                bad += sum(not c.get("same") for c in check.values())
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
