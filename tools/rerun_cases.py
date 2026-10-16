"""Does a shared case file give back its own numbers?  The check ROADMAP.md's 0.3 asks of every reference case.

    python3 tools/rerun_cases.py FILE.mcdonald [FILE ...] [--cases DIR] [--procs N] [--strict] [--json]

Each file is opened as anyone opens one (`mcdonald share open --no-window`: unpacked into a folder of its own, the
video the very file it was made from, found in the reference-data folder, beside the file or by its catalog name), every object in it is measured again by the very
command its report records -- the same marks, frames, known quantities, polarity and skipped stages, into a fresh
folder -- and the new report is held against the one in the file: every stage's fields, results, what had no power
and what is needed, number for number (strings that are paths are compared by their file name; a float may differ
by one part in a billion, the floating-point noise of another machine, no more). The file reruns to its numbers
when nothing differs. Exit code 1 if any file does not. With --strict, an object whose report tracked nothing counts
as not rerunning: it does rerun -- to an empty result -- and a reference case that measures nothing is a mistake (the
first PR43 file, 2026-10-16: marks four frames off the streak, nothing linked, and the plain check passed it).

Needs the video on this computer (the reference-data folder's pursue/ or footage/, the storage folder, or the
catalog's download). Takes minutes per object: the Technical Note's cases 3-11 min with integrity, the bird
videos' stretches longer. Run it through the job scheduler on a shared machine."""
import argparse
import json
import math
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE.parent / "tests"))

from mcdonald import share  # noqa: E402
from mcdonald.report import Case  # noqa: E402
import reference_data  # noqa: E402

REL = 1e-9                       # a float may differ by this, relative: another machine's rounding, not a different number
VOLATILE = {"started", "mcdonald", "python", "ffmpeg", "commands", "figures", "files", "video", "clip"}   # the case's own, not the measurement's


def _same(a, b, path, diffs):
    """Compare two JSON-ish values; record each difference as (path, old, new)."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in ("source", "path", "file", "files", "out", "figure", "png", "csv"):     # paths: by their file name
                va, vb = a.get(k), b.get(k)
                if isinstance(va, str) and isinstance(vb, str):
                    if Path(va).name != Path(vb).name:
                        diffs.append((f"{path}.{k}", va, vb))
                    continue
            if k not in a or k not in b:
                diffs.append((f"{path}.{k}", a.get(k, "<absent>"), b.get(k, "<absent>")))
                continue
            _same(a[k], b[k], f"{path}.{k}", diffs)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append((f"{path}[]", f"{len(a)} items", f"{len(b)} items"))
            return
        for i, (x, y) in enumerate(zip(a, b)):
            _same(x, y, f"{path}[{i}]", diffs)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        if not (a == b or (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b))
                or abs(a - b) <= REL * max(abs(a), abs(b))):
            diffs.append((path, a, b))
    elif isinstance(a, str) and isinstance(b, str) and ("/" in a or "\\" in a) and ("/" in b or "\\" in b):
        if Path(a).name != Path(b).name:
            diffs.append((path, a, b))
    elif a != b:
        diffs.append((path, a, b))


def compare_cases(old_json, new_json):
    """The differences between two case files' measurements: [(where, old, new)]."""
    old, new = json.loads(Path(old_json).read_text(encoding="utf-8")), json.loads(Path(new_json).read_text(encoding="utf-8"))
    diffs = []
    for k in sorted((set(old) | set(new)) - VOLATILE):
        _same(old.get(k), new.get(k), k, diffs)
    co, cn = Case.load(old_json), Case.load(new_json)
    if co.bottom_line() != cn.bottom_line():
        diffs.append(("bottom line", co.bottom_line(), cn.bottom_line()))
    if co.conclusion() != cn.conclusion():
        diffs.append(("conclusion", co.conclusion(), cn.conclusion()))
    return diffs


def recorded_run(case_json):
    """The `mcdonald run` command the case records, as a list of arguments, or None."""
    c = json.loads(Path(case_json).read_text(encoding="utf-8"))
    for cmd in c.get("commands") or []:
        parts = shlex.split(cmd)
        if parts[:2] == ["mcdonald", "run"]:
            return parts
    return None


def rerun_object(folder, video, out, procs=None, say=print):
    """Measure one unpacked object again by the command its report records, into `out`; the new case json's path."""
    tag = next(p for p in Path(folder).glob("*_case.json")).name[:-len("_case.json")]
    rec = recorded_run(Path(folder) / f"{tag}_case.json")
    if rec is None:
        raise RuntimeError(f"{folder}: the report records no `mcdonald run` command to repeat")
    args, skip = [], False
    for i, a in enumerate(rec[2:]):                        # after `mcdonald run`: the video, then the flags
        if skip:
            skip = False
            continue
        if i == 0:
            continue                                       # the video: this computer's copy
        if a in ("--marks", "--track", "--out", "--workdir", "--procs"):
            skip = True
            continue
        if a == "--json":
            continue
        args.append(a)
    cmd = [sys.executable, "-m", "mcdonald.cli", "run", str(video), "--marks", str(Path(folder) / f"{tag}_marks.json"),
           "--out", str(out)] + args + (["--procs", str(procs)] if procs else [])
    say("  " + " ".join(shlex.quote(x) for x in cmd[3:]))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"run exited {r.returncode}: {r.stderr[-800:]}")
    return Path(out) / f"{tag}_case.json"


def the_video(m, beside):
    """The very file the case was made from: looked for by name in the reference-data folder, beside the shared file
    and in the storage folder, and taken where its size and SHA-256 are the file's; only then by its catalog name
    (which downloads DVIDS's per-file copy -- for PR113 5,082 bytes larger than the release-zip copy the published
    numbers were measured on, and so refused). (path, why) with path None where none matches."""
    name = m["video"]["name"]
    from mcdonald import storage
    tried = []
    for d in (reference_data.root() / "pursue", reference_data.footage(), beside, storage.videos()):
        p = Path(d) / name
        if p.is_file():
            same, said = share.check_video(p, m["video"])
            if same:
                return p, said
            tried.append(f"{p}: {said}")
    p = share.find_video(m)
    if p is not None:
        same, said = share.check_video(p, m["video"])
        if same:
            return p, said
        tried.append(f"{p}: {said}")
    return None, (f"{share.describe_video(m['video'])} is not on this computer" if not tried else "; ".join(tried))


def tracked(case_json):
    """Did the report track the object (a track stage with a result)?"""
    st = Case.load(case_json).stages.get("track")
    return bool(st and st.get("result"))


def rerun_file(path, cases, procs=None, say=print, strict=False):
    """One shared file: unpacked, every object measured again, each held against its report. Returns
    {file, folder, video, objects: {k: {differences: [...], seconds}}, reruns: bool}."""
    t0 = time.time()
    folder, m = share.unpack(path, cases)
    video, said = the_video(m, Path(path).parent)
    if video is None:
        raise RuntimeError(f"{Path(path).name}: {said}")
    say(f"{Path(path).name}: {len([p for p in folder.glob('object-*') if p.is_dir()])} objects, video {video}")
    result = dict(file=str(path), folder=str(folder), video=str(video), objects={}, reruns=True)
    for obj in sorted(p for p in folder.glob("object-*") if p.is_dir()):
        t1 = time.time()
        old = next(obj.glob("*_case.json"), None)
        if old is None:
            result["objects"][obj.name] = dict(differences=[("report", "present", "absent: the object has no report in the file")], seconds=0)
            result["reruns"] = False
            continue
        if Case.load(old).stopped_in():
            say(f"  {obj.name}: its report was stopped before the end; not rerun")
            result["objects"][obj.name] = dict(differences=[], seconds=0, skipped="stopped report")
            continue
        if strict and not tracked(old):
            say(f"  {obj.name}: its report tracked nothing, so it measures nothing: not a reference case (--strict)")
            result["objects"][obj.name] = dict(differences=[("track", "a track", "none: the report tracked nothing")], seconds=0)
            result["reruns"] = False
            continue
        new_dir = folder.parent / (folder.name + "-rerun") / obj.name
        new_dir.mkdir(parents=True, exist_ok=True)
        new = rerun_object(obj, video, new_dir, procs=procs, say=say)
        diffs = compare_cases(old, new)
        result["objects"][obj.name] = dict(differences=diffs, seconds=round(time.time() - t1))
        if diffs:
            result["reruns"] = False
            say(f"  {obj.name}: {len(diffs)} difference{'s' if len(diffs) != 1 else ''} ({time.time() - t1:.0f} s):")
            for where, a, b in diffs[:40]:
                say(f"    {where}: {str(a)[:90]!s}  ->  {str(b)[:90]!s}")
        else:
            say(f"  {obj.name}: reruns to its numbers ({time.time() - t1:.0f} s)")
    say(f"{Path(path).name}: {'reruns to its numbers' if result['reruns'] else 'DOES NOT rerun to its numbers'} ({time.time() - t0:.0f} s)")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="+", help="shared case files (.mcdonald)")
    ap.add_argument("--cases", help="where to unpack and rerun (default: a temporary folder, removed after)")
    ap.add_argument("--procs", type=int, help="worker processes for the stages")
    ap.add_argument("--strict", action="store_true", help="an object whose report tracked nothing counts as not rerunning")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    a = ap.parse_args(argv)
    tmp = None
    cases = a.cases
    if not cases:
        tmp = tempfile.TemporaryDirectory(prefix="mcdonald-rerun-")
        cases = tmp.name
    say = (lambda *x: print(*x, file=sys.stderr, flush=True)) if a.json else (lambda *x: print(*x, flush=True))
    results, ok = [], True
    for f in a.files:
        try:
            r = rerun_file(f, cases, procs=a.procs, say=say, strict=a.strict)
        except Exception as e:                             # one file's trouble is reported, the next is still checked
            r = dict(file=str(f), error=f"{type(e).__name__}: {e}", reruns=False)
            say(f"{Path(f).name}: {r['error']}")
        results.append(r)
        ok = ok and r.get("reruns", False)
    if a.json:
        print(json.dumps(results, indent=1, default=str))
    if tmp:
        tmp.cleanup()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
