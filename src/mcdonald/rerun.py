"""Does a shared case file give back its own numbers?  The check ROADMAP.md's 0.3 asks of every reference case, and
anyone's of a file someone sent them: `mcdonald share rerun FILE.mcdonald` (and tools/rerun_cases.py in the repository,
which looks in the reference-data folder too).

Each file is opened as anyone opens one (`mcdonald share open --no-window`: unpacked into a folder of its own, the
video the very file it was made from -- found beside the file, in the storage folder, in a folder named by the caller
or $MCDONALD_DATA, or by its catalog name), every object in it is measured again by the very command its report records
-- the same marks or track, frames, known quantities, polarity, aperture, beat rule, other objects kept clear of and
skipped stages, into a fresh folder -- and the new report is held against the one in the file: every stage's fields,
results, what had no power and what is needed, number for number (strings that are paths are compared by their file
name; a float may differ by one part in a billion, the floating-point noise of another machine, no more). The file
reruns to its numbers when nothing differs. With `strict`, an object whose report tracked nothing counts as not
rerunning: it does rerun -- to an empty result -- and a reference case that measures nothing is a mistake (the first
PR43 file, 2026-10-16: marks four frames off the streak, nothing linked, and the plain check passed it).

Takes minutes per object: the Technical Note's cases 3-11 min with integrity, the bird videos' stretches longer."""
import json
import math
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

from . import share, storage
from .report import Case

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


def rerun_args(rec, folder, tag):
    """The flags to measure an unpacked object again: the recorded `mcdonald run` command's (`rec`, its words), with its
    marks, or its track, and the other objects' tracks it kept clear of, all taken from the unpacked folders beside it
    (`folder` is the object's own), and its own out, workdir, worker count and --json left out. Returns (flags, marks?):
    whether the object is followed again from its marks, rather than measured on its track."""
    args, given, i = [], rec[3:], 0                     # after `mcdonald run VIDEO`: the flags; the video is this computer's copy
    track = False
    while i < len(given):
        a = given[i]
        if a in ("--marks", "--out", "--workdir", "--procs") and i + 1 < len(given):
            i += 2
            continue
        if a == "--track" and i + 1 < len(given):        # the track the report was measured on: the one in the object's folder
            args += ["--track", str(Path(folder) / Path(given[i + 1]).name)]
            track = True
            i += 2
            continue
        if a == "--avoid" and i + 1 < len(given):        # the other objects' tracks: in their folders beside this one
            args += ["--avoid", ",".join(str(Path(folder).parent / Path(v).parent.name / Path(v).name)
                                         for v in given[i + 1].split(",") if v)]
            i += 2
            continue
        if a != "--json":
            args.append(a)
        i += 1
    return ([] if track else ["--marks", str(Path(folder) / f"{tag}_marks.json")]) + args, not track


def rerun_object(folder, video, out, procs=None, say=print):
    """Measure one unpacked object again by the command its report records, into `out`; the new case json's path."""
    tag = next(p for p in Path(folder).glob("*_case.json")).name[:-len("_case.json")]
    rec = recorded_run(Path(folder) / f"{tag}_case.json")
    if rec is None:
        raise RuntimeError(f"{folder}: the report records no `mcdonald run` command to repeat")
    flags, _ = rerun_args(rec, folder, tag)
    cmd = [sys.executable, "-m", "mcdonald.cli", "run", str(video), "--out", str(out)] + flags + (["--procs", str(procs)] if procs else [])
    say("  " + " ".join(shlex.quote(x) for x in cmd[3:]))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"run exited {r.returncode}: {r.stderr[-800:]}")
    return Path(out) / f"{tag}_case.json"


def places(beside=None, also=()):
    """Where the video is looked for, in order: beside the shared file, the folders the caller names, the reference-data
    folder ($MCDONALD_DATA's pursue/ and footage/), and the storage folder."""
    out = [Path(beside)] if beside else []
    out += [Path(d) for d in also]
    data = os.environ.get("MCDONALD_DATA", "").strip()
    if data:
        out += [Path(data).expanduser() / "pursue", Path(data).expanduser() / "footage"]
    return out + [storage.videos()]


def the_video(m, beside=None, also=()):
    """The very file the case was made from: looked for by name in `places`, and taken where its size and SHA-256 are the
    file's; only then by its catalog name (which downloads DVIDS's per-file copy -- for PR113 5,082 bytes larger than the
    release-zip copy the published numbers were measured on, and so refused). (path, why), path None where none matches."""
    name = m["video"]["name"]
    tried = []
    for d in places(beside, also):
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


def objects(folder):
    """The object-N folders of an unpacked file, in order."""
    return sorted((p for p in Path(folder).glob("object-*") if p.is_dir()), key=lambda p: (len(p.name), p.name))


def rerun_file(path, cases, procs=None, say=print, strict=False, also=()):
    """One shared file: unpacked into `cases`, every object measured again, each held against its report. Returns
    {file, folder, video, objects: {k: {differences: [...], seconds}}, reruns: bool}."""
    t0 = time.time()
    folder, m = share.unpack(path, cases)
    video, said = the_video(m, Path(path).parent, also)
    if video is None:
        raise RuntimeError(f"{Path(path).name}: {said}")
    say(f"{Path(path).name}: {len(objects(folder))} objects, video {video}")
    result = dict(file=str(path), **rerun_folder(folder, video, procs=procs, say=say, strict=strict))
    say(f"{Path(path).name}: {'reruns to its numbers' if result['reruns'] else 'DOES NOT rerun to its numbers'} ({time.time() - t0:.0f} s)")
    return result


def rerun_folder(folder, video, procs=None, say=print, strict=False, progress=None):
    """The objects of an unpacked file (`folder`, its object-N folders) measured again on `video`, each into
    <folder>-rerun/object-N, and held against its report: {folder, video, objects: {k: {differences, seconds}},
    reruns}. `progress(done, name)` is told as each object starts (the window's bar)."""
    folder = Path(folder)
    result = dict(folder=str(folder), video=str(video), objects={}, reruns=True)
    for k, obj in enumerate(objects(folder)):
        if progress:
            progress(k, obj.name)
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
    return result


def rerun_files(files, cases=None, procs=None, strict=False, also=(), say=print):
    """Each file through `rerun_file`, into `cases` (a temporary folder, removed after, if not given): (results, all
    rerun). One file's trouble is reported and the next still checked."""
    import tempfile
    tmp = None
    if not cases:
        tmp = tempfile.TemporaryDirectory(prefix="mcdonald-rerun-")
        cases = tmp.name
    results, ok = [], True
    try:
        for f in files:
            try:
                r = rerun_file(f, cases, procs=procs, say=say, strict=strict, also=also)
            except Exception as e:
                r = dict(file=str(f), error=f"{type(e).__name__}: {e}", reruns=False)
                say(f"{Path(f).name}: {r['error']}")
            results.append(r)
            ok = ok and r.get("reruns", False)
    finally:
        if tmp:
            tmp.cleanup()
    return results, ok
