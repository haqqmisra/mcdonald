"""The controls harness's saved curves: one clip of everything, measured once from its video and kept (ROADMAP.md 0.5).

    python3 tools/controls/save_controls.py OUT [--only flyer1,pr23] [--set RUNS]

`tests/test_controls.py` replays `flicker.judge` on these curves after every change, in minutes and with no video. This
script makes them: each control in `CONTROLS` (the package's own, from `tests/golden/` and the reference-data folder) is
measured by `flicker.measure` as `tests/test_golden.py` measures it, under both beat rules, with everything the judging is
given kept (`run_set.Capture`); and the labelled infrared set's sample (`tests/golden/controls.csv`, `source` svanstrom) is
copied from the whole-set run's folder (`--set`, `run_set.py`'s RUNS). Every control's replay is checked against its
measurement before it is written. OUT is the reference-data folder's `controls/curves/` when the set is made for keeps.

`--record` measures nothing: it judges the saved curves again with the code as it stands and writes each control's
outcome into the manifest's record columns, which the suite holds the stage to -- after a change to the judging, the one
step, and the manifest's diff says what moved.

Takes some minutes: the Galileo flyers are 60 frames a second, PR135's six members and PR055 are 1080p. Run it through the
job scheduler on a shared machine."""
import argparse
import csv
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))
sys.path.insert(0, str(HERE.parent.parent / "tests"))
sys.path.insert(0, str(HERE))

from mcdonald import catalog, flicker, forensics as vf  # noqa: E402
import reference_data  # noqa: E402
from run_set import RULES, Capture, outcome, read_gz, replay, same, with_shake, write_gz  # noqa: E402

GOLDEN = reference_data.GOLDEN
MANIFEST = GOLDEN / "controls.csv"


def galileo(k):
    """(video, {object: track}, n0, n1) for Galileo flyer k on the paper's track, as test_golden reads it."""
    rows = {int(r["flyer"]): r for r in csv.DictReader(open(GOLDEN / "galileo_clips.csv", encoding="utf-8"))}
    off = int(rows[k]["src_frame0"])
    track = {int(r["frame"]) - off: (float(r["x"]), float(r["y"]))
             for r in csv.DictReader(open(GOLDEN / f"flyer{k}_paper_track.csv", encoding="utf-8"))}
    return reference_data.galileo() / rows[k]["clip"], {"object": track}, min(track), max(track)


def pursue(record, track_file, n0=None, n1=None):
    video, why = reference_data.pursue_clip(record)
    if video is None:
        raise FileNotFoundError(why)
    track = vf.read_track(GOLDEN / track_file)
    return video, {"object": track}, n0 or min(track), n1 or max(track)


def pr135():
    video, why = reference_data.pursue_clip("PR135")
    if video is None:
        raise FileNotFoundError(why)
    tracks = {}
    for r in csv.DictReader(open(GOLDEN / "pr135_tracks.csv", encoding="utf-8")):
        if 1240 <= int(r["frame"]) <= 1389 and r["x"] and r["y"]:
            tracks.setdefault(f"member {r['letter']}", {})[int(r["frame"])] = (float(r["x"]), float(r["y"]))
    return video, tracks, 1240, 1389


def balloon():
    track = vf.read_track(GOLDEN / "wa9ony5_balloon_track.csv")
    return reference_data.footage() / "tl8_etApsro.mp4", {"object": track}, min(track), max(track)


def visible(clip):
    track = vf.read_track(GOLDEN / f"svanstrom_v{clip}_track.csv")
    video = reference_data.root() / "svanstrom2021" / "Drone-detection-dataset" / "Data" / "Video_V" / f"V_HELICOPTER_{clip}.mp4"
    return video, {"object": track}, min(track), max(track)


# name -> (how to read it, dark): each measured as test_golden measures it (its polarity, its frames, the default aperture,
# the stage's rule), no clip's other objects avoided and the scene's motion not read (golden reads neither)
CONTROLS = {
    **{f"flyer{k}": ((lambda k=k: galileo(k)), False) for k in range(1, 6)},
    "pr135_flock": (pr135, False),
    "pr23": ((lambda: pursue("PR23", "pr23_object_track.csv", 1, 208)), False),
    "wa9ony5": (balloon, True),
    "pr055": ((lambda: pursue("PR055", "pr055_sphere_track.csv")), True),
    "pr071": ((lambda: pursue("PR071", "pr071_object_track.csv")), False),
    "v054": ((lambda: visible("054")), True),
    "v030": ((lambda: visible("030")), True),
}


def measure_one(name, out, say=print):
    """Measure one package control under both rules, keep what the judging was given, check its replay, write it."""
    how, dark = CONTROLS[name]
    video, tracks, n0, n1 = how()
    saved, live = None, {}
    with tempfile.TemporaryDirectory(dir=str(Path(out).parent)) as td:
        clip = vf.Clip(video, f"{td}/frames", n0, n1)
        for rule in RULES:
            with Capture() as cap:
                found = flicker.measure(clip, tracks, dark=dark, say=lambda *a: None, rule=rule)
            live[rule] = outcome(found.fields)
            if saved is None:
                saved = dict(cap.judged, dots=cap.dots, dark=dark, black_hot=False, control=name, video=video.name,
                             made_by="tools/controls/save_controls.py")
            elif saved.get("dots") is None and cap.dots is not None:
                saved["dots"] = cap.dots
            say(f"  {name} {rule}: beats {found.fields.get('beats')}, strong {found.fields.get('strong')}, "
                f"named {live[rule]['named']}, train {live[rule]['train']}")
    saved["live"] = live
    for rule in RULES:
        got = outcome(replay(saved, rule).fields)
        if not same(got, live[rule]):
            raise RuntimeError(f"{name} {rule}: the replay {got} is not the measurement {live[rule]}")
    write_gz(Path(out) / f"{name}.json.gz", saved)
    return live


RECORD = ("beats", "named", "hz", "amplitude", "train")      # what the manifest records of each control, rule by rule


def said(o, k):
    v = o[k]
    if k in ("named", "train"):
        return str(int(bool(v)))
    if k in ("hz", "amplitude"):
        return "" if v is None else f"{v:.6f}"
    return str(v)


def record(out, say=print):
    """Each control's saved curves judged again with the code as it stands, its outcome written into the manifest's record
    columns (`<rule>_<what>`, RECORD): what `tests/test_controls.py` holds the stage to. After a change to the judging -- a
    gate, a floor, a rule -- this is the whole of what moves, and the manifest's diff shows it; the curves stay as they were."""
    lines = open(MANIFEST, encoding="utf-8").read().splitlines(keepends=True)
    head = [l for l in lines if l.startswith("#")]
    rows = list(csv.DictReader(l for l in lines if not l.startswith("#")))
    cols = [c for c in rows[0] if not any(c == f"{rule}_{k}" for rule in RULES for k in RECORD)]
    cols += [f"{rule}_{k}" for rule in RULES for k in RECORD]
    for r in rows:
        path = Path(out) / f"{r['name']}.json.gz"
        if not path.exists():
            say(f"  ! {r['name']}: no saved curves in {out}; its record is left as it was")
            continue
        saved = read_gz(path)
        for rule in RULES:
            o = outcome(replay(saved, rule).fields)
            r.update({f"{rule}_{k}": said(o, k) for k in RECORD})
        say(f"  {r['name']}: " + "; ".join(f"{rule} " + " ".join(f"{k} {r[f'{rule}_{k}']}" for k in RECORD) for rule in RULES))
    with open(MANIFEST, "w", newline="", encoding="utf-8") as f:
        f.writelines(head)
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows({c: r.get(c, "") for c in cols} for r in rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out")
    ap.add_argument("--only", help="controls by name, comma-separated")
    ap.add_argument("--set", help="the whole-set run's folder (run_set.py's RUNS): the labelled set's sample is copied from it")
    ap.add_argument("--record", action="store_true", help="measure nothing: judge the saved curves in OUT again and write each "
                                                          "control's outcome into tests/golden/controls.csv (after a change "
                                                          "to the judging)")
    a = ap.parse_args(argv)
    if a.record:
        record(a.out, say=lambda *x: print(*x, flush=True))
        return 0
    print(f"catalog: {catalog.active().name}; reference data: {reference_data.root()}", flush=True)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    want = a.only.split(",") if a.only else None
    rows = list(csv.DictReader(l for l in open(MANIFEST, encoding="utf-8") if not l.startswith("#")))
    bad = 0
    for r in rows:
        if want and r["name"] not in want:
            continue
        if r["source"] == "svanstrom":
            if not a.set:
                continue
            d = Path(a.set) / r["track"]
            saved = with_shake(read_gz(d / "curves.json.gz"), {rule: read_gz(d / f"{rule}.json.gz")["fields"] for rule in RULES})
            saved["live"] = {rule: outcome(read_gz(d / f"{rule}.json.gz")["fields"]) for rule in RULES}
            for rule in RULES:
                got = outcome(replay(saved, rule).fields)
                if not same(got, saved["live"][rule]):
                    bad += 1
                    print(f"  ! {r['name']} {rule}: the replay {got} is not the measurement {saved['live'][rule]}", flush=True)
            write_gz(Path(a.out) / f"{r['name']}.json.gz", saved)
            print(f"  {r['name']}: from {d}: " + "; ".join(f"{rule} {saved['live'][rule]}" for rule in RULES), flush=True)
            continue
        try:
            measure_one(r["name"], a.out, say=lambda *x: print(*x, flush=True))
        except Exception as e:
            bad += 1
            print(f"  ! {r['name']}: {type(e).__name__}: {e}", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
