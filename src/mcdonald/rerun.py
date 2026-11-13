"""Does a shared case file give back its own numbers?  The check ROADMAP.md's 0.3 asks of every reference case, and
anyone's of a file someone sent them: `mcdonald share rerun FILE.mcdonald` (and tools/rerun_cases.py in the repository,
which looks in the reference-data folder too).

Each file is opened as anyone opens one (`mcdonald share open --no-window`: unpacked into a folder of its own, the
video the very file it was made from -- found beside the file, in the storage folder, in a folder named by the caller
or $MCDONALD_DATA, or by its catalog name), every object in it is measured again by the very command its report records
-- the same marks or track, frames, known quantities, polarity, aperture, beat rule, other objects kept clear of and
skipped stages, into a fresh folder -- and the new report is held against the one in the file: every stage's fields,
results, what had no power and what is needed, number for number (a string that is a file's path is compared by its file
name, since a run made again is in another folder; every other string, each sentence of the report among them, has to
be the same to the letter (`is_path`); a float may differ by one part in a billion, the floating-point noise of another
machine, no more). The file
reruns to its numbers when nothing differs. One thing is left out of that: the review state, whether a person said
they looked at the track sheet (`stages.confirm_sheet`, `--i-looked`). A run made again cannot say that, so the two
reports always differ there when the file's was confirmed; it is reported beside the comparison, and decides nothing
(2026-11-09: the Technical Note's two case files gave back every number and still "did not rerun"). With `strict`, an
object whose report tracked nothing counts as not
rerunning: it does rerun -- to an empty result -- and a reference case that measures nothing is a mistake (the first
PR43 file, 2026-10-16: marks four frames off the streak, nothing linked, and the plain check passed it).

Takes minutes per object: the Technical Note's cases 3-11 min with integrity, the bird videos' stretches longer."""
import json
import math
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

from . import gpu, share, storage
from .report import Case

REL = 1e-9                       # a float may differ by this, relative: another machine's rounding, not a different number
# Where a graphics card took part in measuring either of the two (`report.Case.computed_on`), a float may differ by
# CARD_REL, relative, or by CARD_ABS: the card's agreement with the CPU, whose arithmetic is the reference. The card
# matches a pair's templates in single precision as the CPU does, by another transform in another order (method
# section 52). On the first case measured both ways (PR135 object 2, 270 frames, 2026-11-12) 10 of the case's 4,042
# values differed past one in a billion, the farthest by 1.3 parts in 100,000 (a median error of 0.002 px); no count,
# verdict or sentence differed. CARD_REL is eight times that.
CARD_REL, CARD_ABS = 1e-4, 1e-7
VOLATILE = {"started", "mcdonald", "python", "ffmpeg", "commands", "figures", "files", "video", "clip",
            "segment", "measured_by", "computed_on"}    # the case's own, not the measurement's


def held_to(old, new):
    """(relative, absolute, card): how far a float of two cases (their dictionaries) may differ. One part in a billion
    and nothing more, where the CPU measured both; where a graphics card took part in either, the card's agreement
    (CARD_REL, CARD_ABS), and its name, for the comparison to say so."""
    card = (old or {}).get("computed_on") or (new or {}).get("computed_on")
    return (CARD_REL, CARD_ABS, card) if card else (REL, 0.0, None)


_ENDING = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,7}$")      # a file's ending: ".csv", ".mp4"; not the ".32" of "0.35/0.32", nor "1.5x"
_DRIVE = re.compile(r"[A-Za-z]:[\\/]")


def is_path(s):
    """Is this string a file's path, which a run made again in another folder gives with another folder in front? Only
    what is one: an absolute path ("/...", "~/...", "C:\\..."), or a string with no space in it and a file's ending
    ("out/object-1/x_track.csv", "x_track.csv"). A sentence is not, whatever is in it: until 2026-11-13 any two strings
    that both held a slash were compared by what followed the last one, so "median 103 px/s (...)" and "median 250 px/s
    (...)" were the same wherever the words after "px/s" were (IDEAS.md G6)."""
    if not isinstance(s, str):
        return False
    if s.startswith(("/", "\\", "~/")) or _DRIVE.match(s):
        return True
    return not re.search(r"\s", s) and bool(_ENDING.search(s))


def _name(s):
    """A path's file name, whichever computer wrote it (a Windows path read on Linux has no "/" in it)."""
    return re.split(r"[\\/]", s.rstrip("\\/"))[-1]


def _same(a, b, path, diffs, rel=REL, floor=0.0):
    """Compare two JSON-ish values; record each difference as (path, old, new). A float may differ by `rel`, relative,
    or by `floor`. Two strings that are both paths (`is_path`) are the same where their file names are; any other two
    strings where they are the same string."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                diffs.append((f"{path}.{k}", a.get(k, "<absent>"), b.get(k, "<absent>")))
                continue
            _same(a[k], b[k], f"{path}.{k}", diffs, rel, floor)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append((f"{path}[]", f"{len(a)} items", f"{len(b)} items"))
            return
        for i, (x, y) in enumerate(zip(a, b)):
            _same(x, y, f"{path}[{i}]", diffs, rel, floor)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        if not (a == b or (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b))
                or abs(a - b) <= max(rel * max(abs(a), abs(b)), floor if isinstance(a, float) or isinstance(b, float) else 0.0)):
            diffs.append((path, a, b))
    elif is_path(a) and is_path(b):
        if _name(a) != _name(b):
            diffs.append((path, a, b))
    elif a != b:
        diffs.append((path, a, b))


def review_state(case):
    """Take the review state out of a case's dict and return it: whether a person said they looked at the track sheet
    (`stages.verify`'s `reviewed`, in its fields and its result), the need that stands until they do and the note that
    made the object's numbers provisional. A measurement made again cannot give these back, so they are compared
    apart from the numbers (`compare_cases`). {} where the case has no track sheet."""
    from .stages import SHEET_NEEDED, SHEET_PROVISIONAL, SHEET_PROVISIONAL_BEFORE
    v = (case.get("stages") or {}).get("verify")
    if not isinstance(v, dict) or "reviewed" not in (v.get("fields") or {}):
        return {}
    state = {"reviewed": v["fields"].pop("reviewed"), "said": (v.get("result") or {}).pop("reviewed", None)}
    v["needs"] = [x for x in v.get("needs") or [] if x != SHEET_NEEDED]
    case["notes"] = [x for x in case.get("notes") or [] if x not in (SHEET_PROVISIONAL, SHEET_PROVISIONAL_BEFORE)]
    return state


def compare_cases(old_json, new_json, review=None):
    """The differences between two case files' measurements: [(where, old, new)]. The review state (`review_state`) is
    not among them; where `review` is a list, its differences are added to that instead. Numbers are held to one part
    in a billion, or to a graphics card's agreement with the CPU where one took part in either (`held_to`)."""
    old, new = json.loads(Path(old_json).read_text(encoding="utf-8")), json.loads(Path(new_json).read_text(encoding="utf-8"))
    ro, rn = review_state(old), review_state(new)
    if review is not None and ro != rn:
        for k in ("reviewed", "said"):
            if ro.get(k) != rn.get(k):
                review.append((f"stages.verify.{k if k == 'reviewed' else 'result.reviewed'}", ro.get(k), rn.get(k)))
    diffs = []
    rel, floor, _ = held_to(old, new)
    for k in sorted((set(old) | set(new)) - VOLATILE):
        _same(old.get(k), new.get(k), k, diffs, rel, floor)
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
    # Measured again by the arithmetic it was measured by. A case the CPU measured alone -- every case from before
    # 2026-11-12 -- is measured on the CPU, also on a computer with a graphics card: a card's numbers agree with the
    # CPU's to about a part in a million, and a file is held to one in a billion. A case a card took part in is left to
    # this computer's own choice (its card, if it has one), and held to the card's agreement (`CARD_REL`).
    env = dict(os.environ)
    if not Case.load(Path(folder) / f"{tag}_case.json").computed_on:
        env[gpu.GPU_VAR] = gpu.NONE
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
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
        review = []
        diffs = compare_cases(old, new, review=review)
        result["objects"][obj.name] = dict(differences=diffs, seconds=round(time.time() - t1), review_state=review)
        rel, _, card = held_to(json.loads(old.read_text(encoding="utf-8")), json.loads(Path(new).read_text(encoding="utf-8")))
        if card:
            result["objects"][obj.name]["held_to"] = rel
            say(f"  {obj.name}: a graphics card took part in the measuring ({card}). A card's numbers agree with the "
                f"CPU's to about one part in a million, so these are held to one part in {1 / rel:,.0f}, not one in a billion.")
        if review:
            said = next((b for w, a, b in review if w.endswith("result.reviewed")), None) or "that nobody has looked at it yet"
            was = next((a for w, a, b in review if w.endswith("result.reviewed")), None) or "that it was"
            say(f"  {obj.name}: the review state is not compared. The file says its track sheet was looked at ({was}). "
                f"A run made again cannot say that, and says {said}.")
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
