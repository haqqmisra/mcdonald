"""One file to send: a video's results, the part of it to look at, and what was said about it.

Jacob, 2026-10-15: "can we add a feature to the mcDonald GUI that allows me to load a particular analysis of a
video done by someone else (whether human or AI)? ... I might want to ask Ravi to do something similar, and it would
be useful if I had a single file that I could send him that contained the information that he could immediately pick
up where I left off."

A shared file (`<tag>_<who>_<date>.mcdonald`) is a zip:

    share.json      what it is: which video (by its catalog name, its file's name, size and SHA-256), the part of it
                    to open, the stretches to look at ("frames 3300-3500: the first flapping bout"), the objects, and
                    the thread -- every note said about it so far, oldest first, each with who said it, whether a
                    person or an agent, and when. The last note is what this file asks.
    case/...        the video's results folder as it is on the sender's computer: the marks (each still saying who
                    placed it -- a hand, an agent, Find), the tracks, each object's folder (object-N) with its report
    attached/...    anything else sent with it: a figure, a note

The video itself is never in it. A PURSUE video is 100-900 MB; the person it is sent to has, or can download, the
same file. It is named the way the window opens one by name (`forensics.resolve`: the catalog, and DVIDS for a video
not yet on the computer), and its size and SHA-256 say whether the file found is the one the sender measured.

Opening one (the window's File -> Open a shared file..., a drop, or `mcdonald share open FILE`) unpacks it into a
folder of its own beside the person's other results -- never over them -- opens the part of the video it names,
with every object's marks and track drawn, and puts the thread and the stretches to look at in the right column.
Answering is the same file again: what they did added to the folder, their note added to the thread.

Nothing in a shared file is run. It is unpacked only as data -- JSON, CSV, Markdown, text and pictures -- and a name
that would land outside the folder (an absolute path, `..`) is refused before anything is written.
"""
import argparse
import hashlib
import io
import json
import re
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path, PurePosixPath

from . import __version__, storage
from . import catalog as _catalog
from . import forensics as vf

SUFFIX = ".mcdonald"
FORMAT = "mcdonald-share/1"
MANIFEST = "share.json"
KEPT = "_share.json"                          # <tag>_share.json in an opened file's folder: the thread, kept for the answer
DATA = {".json", ".csv", ".md", ".txt", ".tsv", ".png", ".jpg", ".jpeg", ".svg", ".pdf"}
MAX_FILE = 40 * 2 ** 20                       # a figure or a long track CSV is a few MB; a frame dump is not a result
MAX_ALL = 200 * 2 ** 20
SKIP_DIRS = {"frames", "__pycache__", ".git"}


class ShareError(ValueError):
    """A shared file that cannot be made or opened, said in plain words."""


# ---- what the video is --------------------------------------------------------------------------------------
def sha256(path, chunk=8 * 2 ** 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                return h.hexdigest()
            h.update(b)


def video_identity(path):
    """What names this video on another computer: its catalog record (the name `forensics.resolve` opens it by,
    and where it can be downloaded), its file's name, size and SHA-256, and what ffprobe says of it."""
    path = Path(path)
    info = vf.probe(path)
    try:
        rec = _catalog.active().by_path(path)
    except Exception:                                  # a catalog that cannot be read is no catalog: the file's own name
        rec = None
    cat = None
    if rec:
        cat = {k: rec.get(k) for k in ("id", "release", "title", "url") if rec.get(k)}
    fps = info["fps"]
    return {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path), "catalog": cat,
            "fps": f"{fps.numerator}/{fps.denominator}", "frames": info["nb_frames"] or None,
            "width": info["width"], "height": info["height"]}


def catalog_name(video):
    """The name to open it by (`RELEASE:ID` where the catalog has a release, so that PR001 is not ambiguous)."""
    c = (video or {}).get("catalog") or {}
    if not c.get("id"):
        return None
    return f"{str(c['release']).zfill(2)}:{c['id']}" if c.get("release") else c["id"]


def describe_video(video):
    c = video.get("catalog") or {}
    return (f"{c['id']} ({video['name']})" if c.get("id") else video["name"]) + \
        f", {video['bytes'] / 2 ** 20:.0f} MB"


def check_video(path, video, full=True):
    """(same, sentence): is the file at `path` the one the sender measured? The size first (instant), then the
    SHA-256 (a second or two for a large video)."""
    path = Path(path)
    if not path.is_file():
        return False, f"{path} is not there"
    size = path.stat().st_size
    if video.get("bytes") and size != video["bytes"]:
        return False, (f"{path.name} on this computer is {size:,} bytes, and the one the file was made from was "
                       f"{video['bytes']:,}: it is not the same file, so the marks may not land on the same places")
    if full and video.get("sha256") and sha256(path) != video["sha256"]:
        return False, (f"{path.name} on this computer is the right size but not the same file (its SHA-256 differs): "
                       "the marks may not land on the same places")
    return True, f"{path.name} is the same file the marks were made on"


def find_video(manifest, fetch=None, also=()):
    """The video's path on this computer, or None: by its catalog name (downloaded from where the catalog says, as
    `forensics.resolve` does, `fetch` showing how far along), else by its file's name in the storage folder's videos,
    beside the shared file, or in any folder of `also`."""
    video = manifest["video"]
    name = catalog_name(video)
    if name:
        try:
            path, _, _ = vf.resolve(name, fetch=fetch)
            if Path(path).is_file():
                return Path(path)
        except vf.Stop:
            pass                                     # not in this computer's catalog: look for the file by its name
    for d in [storage.videos(), *[Path(a) for a in also]]:
        p = Path(d) / video["name"]
        if p.is_file():
            return p
    return None


# ---- making one ---------------------------------------------------------------------------------------------
def _slug(text):
    s = re.sub(r"[^A-Za-z0-9]+", "-", str(text or "")).strip("-").lower()
    return s[:24] or "someone"


def _case_files(folder):
    """(relative posix path, file) for what goes in from a results folder: data and pictures, not frames, nothing
    above MAX_FILE, and not the thread an opened file left there (`<tag>_share.json`: the new file carries it)."""
    out = []
    folder = Path(folder)
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder)
        if not p.is_file() or p.is_symlink() or any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.suffix.lower() not in DATA or p.name.endswith(KEPT):
            continue
        if p.stat().st_size > MAX_FILE:
            continue
        out.append((PurePosixPath(*rel.parts).as_posix(), p))
    return out


def thread_of(folder, tag=None):
    """The thread an opened file left in `folder` (`<tag>_share.json`), oldest first, or []; and that manifest."""
    folder = Path(folder)
    kept = sorted(folder.glob(f"{tag}{KEPT}" if tag else f"*{KEPT}"))
    if not kept:
        return [], None
    try:
        m = json.loads(kept[0].read_text(encoding="utf-8"))
        return list(m.get("thread") or []), m
    except (OSError, ValueError):
        return [], None


def make(out, video, folder=None, part=None, look=(), note="", by="", agent=False, attach=(), objects=None,
         identity=None, when=None):
    """Write a shared file at `out` and return its path.

    `video` is the video file; `folder` its results folder (the window's: the one with `<tag>_marks.json` and the
    object-N folders), or None; `part` (first, last) is the part to open; `look` is [(first, last, what)], the
    stretches to look at; `note` is what this file says or asks, `by` who says it and `agent` whether an agent
    does; `attach` is more files to send (a figure). `objects` is {k: label} for the objects' names, if any.
    A folder an opened shared file was unpacked into carries its thread on: the new note is added to it."""
    video = Path(video)
    ident = identity or video_identity(video)
    tag = (ident.get("catalog") or {}).get("id", "").lower() or video.stem.lower()
    when = when or datetime.now(timezone.utc).isoformat(timespec="seconds")
    thread, before = thread_of(folder, None) if folder else ([], None)
    if note or not thread:
        thread.append({"by": by or "someone", "agent": bool(agent), "when": when, "text": note or ""})
    files = _case_files(folder) if folder else []
    old_attached = [(rel, p) for rel, p in files if rel.startswith("attached/")]
    files = [(rel, p) for rel, p in files if not rel.startswith("attached/")]
    att = [(f"attached/{Path(a).name}", Path(a)) for a in attach] + old_attached
    for _, p in att:
        if not p.is_file():
            raise ShareError(f"{p} is not a file, so it cannot be sent with this")
        if p.suffix.lower() not in DATA:
            raise ShareError(f"{p.name} cannot be sent in a shared file: only data and pictures go in one "
                             f"({', '.join(sorted(DATA))})")
    total = sum(p.stat().st_size for _, p in files + att)
    if total > MAX_ALL:
        raise ShareError(f"this would be {total / 2 ** 20:.0f} MB, more than the {MAX_ALL / 2 ** 20:.0f} MB a shared file may be")
    if part is None and before and before.get("part"):
        part = before["part"]
    look = [dict(first=int(a), last=int(b), what=str(w or "")) for a, b, w in look] or \
        [dict(x) for x in (before or {}).get("look") or []]
    if objects is None and before:
        objects = {int(k): v for k, v in (before.get("objects") or {}).items()}
    manifest = {
        "format": FORMAT,
        "made": {"by": by or "someone", "agent": bool(agent), "when": when, "mcdonald": __version__},
        "tag": tag,
        "video": ident,
        "part": [int(part[0]), int(part[1])] if part else None,
        "look": look,
        "objects": {str(k): v for k, v in (objects or {}).items()},
        "thread": thread,
        "files": [{"path": f"case/{rel}", "bytes": p.stat().st_size} for rel, p in files],
        "attached": [rel for rel, _ in att],
    }
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".part")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(MANIFEST, json.dumps(manifest, indent=1))
        for rel, p in files:
            z.write(p, f"case/{rel}")
        seen = set()
        for rel, p in att:
            if rel not in seen:
                z.write(p, rel)
                seen.add(rel)
    tmp.replace(out)
    return out


def default_name(tag, by, when=None):
    when = when or datetime.now()
    return f"{tag}_{_slug(by)}_{when:%Y-%m-%d_%H%M}{SUFFIX}"


def objects_from_tracks(clip_video, fps, tag, base, tracks, every=10):
    """For an agent with tracks and no window: each (label, track CSV) as an object-N folder under `base`, its track
    as the object's automatic track and marks every `every` frames recorded as an agent's, so that the window shows it
    and can follow it again. Returns {k: label}."""
    from .mark import MarkSet
    base = Path(base)
    labels = {}
    for k, (label, track) in enumerate(tracks, start=1):
        t = vf.read_track(track)
        if not t:
            raise ShareError(f"{track} has no rows")
        folder = base / f"object-{k}"
        folder.mkdir(parents=True, exist_ok=True)
        ms = MarkSet(tag, clip_video, fps)
        ns = sorted(t)
        for n in ns[::every] + [ns[-1]]:
            ms.add("object", n, *t[n], how=f"agent: from the track {Path(track).name} ({label})")
        ms.save(folder / f"{tag}_marks.json")
        ms.write_track_csv(folder / f"{tag}_marks.csv")
        with open(folder / f"{tag}_autotrack.csv", "w", encoding="utf-8") as f:
            f.write(f"# {label}: track from {Path(track).name}, written by mcdonald share make\nframe,x_px,y_px\n")
            for n in ns:
                f.write(f"{n},{t[n][0]:.2f},{t[n][1]:.2f}\n")
        labels[k] = label
    return labels


# ---- reading and opening one --------------------------------------------------------------------------------
def read(path):
    """The manifest of a shared file, checked; ShareError says what is wrong with it."""
    path = Path(path)
    try:
        with zipfile.ZipFile(path) as z:
            m = json.loads(z.read(MANIFEST).decode("utf-8"))
    except (OSError, zipfile.BadZipFile) as ex:
        raise ShareError(f"{path.name} is not a shared mcdonald file: {ex}")
    except KeyError:
        raise ShareError(f"{path.name} is a zip file but not a shared mcdonald file: it has no {MANIFEST}")
    except ValueError as ex:
        raise ShareError(f"{path.name}: its {MANIFEST} cannot be read: {ex}")
    fmt = str(m.get("format", ""))
    if not fmt.startswith("mcdonald-share/"):
        raise ShareError(f"{path.name} is not a shared mcdonald file")
    if fmt != FORMAT:
        raise ShareError(f"{path.name} was made by a newer mcdonald ({fmt}); update this one to open it")
    if not isinstance(m.get("video"), dict) or not m["video"].get("name"):
        raise ShareError(f"{path.name} does not say which video it is about")
    return m


def _safe(name):
    """The member's path as parts, or None if it would land outside the folder it is unpacked into."""
    p = PurePosixPath(name.replace("\\", "/"))
    if p.is_absolute() or not p.parts or any(part in ("..", "") for part in p.parts) or ":" in p.parts[0]:
        return None
    return p.parts


def unpack(path, cases, folder=None):
    """Unpack a shared file into a folder of its own under `cases` -- `<tag>-from-<who>-<date>`, never over anything
    there -- and return (folder, manifest). Only data and pictures come out; a name that would land outside the
    folder stops it before anything is written. The manifest stays in the folder as `<tag>_share.json`."""
    m = read(path)
    tag = re.sub(r"[^a-z0-9_-]+", "-", str(m.get("tag") or Path(m["video"]["name"]).stem).lower()) or "video"
    made = m.get("made") or {}
    stamp = local_time(made.get("when")).replace(":", "").replace(" ", "_")
    if folder is None:
        root = Path(cases) / (f"{tag}-from-{_slug(made.get('by'))}" + (f"-{stamp}" if stamp else ""))
        folder, k = root, 2
        while folder.exists():
            folder = Path(f"{root}-{k}")
            k += 1
    folder = Path(folder)
    with zipfile.ZipFile(path) as z:
        members = []
        for info in z.infolist():
            if info.is_dir() or info.filename == MANIFEST:
                continue
            parts = _safe(info.filename)
            if parts is None:
                raise ShareError(f"{Path(path).name} has a file named {info.filename!r}, which would land outside the "
                                 "folder it is opened into: it was not opened")
            if Path(parts[-1]).suffix.lower() not in DATA:
                continue                              # only data and pictures come out; anything else stays in the zip
            if info.file_size > MAX_FILE:
                raise ShareError(f"{info.filename} in {Path(path).name} is {info.file_size / 2 ** 20:.0f} MB: "
                                 "more than a shared file's results may be")
            members.append((info, parts))
        folder.mkdir(parents=True, exist_ok=True)
        for info, parts in members:
            rel = parts[1:] if parts[0] == "case" else parts           # case/... is the folder itself; attached/ beside it
            if not rel:
                continue
            dest = folder.joinpath(*rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
    (folder / f"{tag}{KEPT}").write_text(json.dumps(m, indent=1), encoding="utf-8")
    return folder, m


def attached(folder):
    """The files that came with the thread (attached/...), as paths."""
    d = Path(folder) / "attached"
    return sorted(p for p in d.iterdir() if p.is_file()) if d.is_dir() else []


def local_time(when):
    """An ISO time as this computer's clock reads it, to the minute ('2026-10-15 08:28')."""
    try:
        return datetime.fromisoformat(str(when)).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return str(when or "")[:16].replace("T", " ")


def summary(m):
    """What a shared file holds, in plain words, line by line."""
    v = m["video"]
    lines = [f"About {describe_video(v)}" + (f", frames {m['part'][0]}–{m['part'][1]}" if m.get("part") else "")]
    for note in m.get("thread") or []:
        who = f"{note.get('by', 'someone')}" + (" (an AI agent)" if note.get("agent") else "")
        lines.append(f"{who}, {local_time(note.get('when'))}: {note.get('text') or '(no note)'}")
    for s in m.get("look") or []:
        lines.append(f"Look at frames {s['first']}–{s['last']}" + (f": {s['what']}" if s.get("what") else ""))
    objs = m.get("objects") or {}
    n_obj = len({f["path"].split("/")[1] for f in m.get("files", []) if re.match(r"case/object-\d+/", f["path"])})
    if n_obj or objs:
        lines.append(f"{max(n_obj, len(objs))} object(s)" + (": " + ", ".join(f"{k} {v}" for k, v in sorted(objs.items())) if objs else ""))
    if m.get("attached"):
        lines.append("With: " + ", ".join(PurePosixPath(a).name for a in m["attached"]))
    made = m.get("made") or {}
    lines.append(f"Made with mcdonald {made.get('mcdonald', '?')}; {len(m.get('files', []))} result files")
    return lines


# ---- the command line ---------------------------------------------------------------------------------------
def _span(text):
    """'3300-3500' or '3300-3500:what to look for' -> (3300, 3500, what)."""
    span, _, what = text.partition(":")
    a, _, b = span.replace("–", "-").partition("-")
    try:
        a, b = int(a), int(b or a)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r}: give frames as FIRST-LAST, optionally :what to look for")
    return (min(a, b), max(a, b), what.strip())


def _object(text):
    label, _, track = text.rpartition("=")
    if not track:
        raise argparse.ArgumentTypeError(f"{text!r}: give an object as LABEL=TRACK.csv")
    return (label.strip() or Path(track).stem, track)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mcdonald share", description=(
        "One file to send to someone else: a video's results, the part of it to look at, and what was said about it. "
        "They open it in the window (File -> Open a shared file...) and go on from there; the video itself is not in "
        "it -- their mcdonald finds or downloads the same one."))
    sub = ap.add_subparsers(dest="what", required=True)
    mk = sub.add_parser("make", help="make a shared file from a video's results")
    mk.add_argument("video", help="the video: a path, or a catalog name such as PR085")
    mk.add_argument("--case", help="its results folder (the one with <tag>_marks.json and the object-N folders)")
    mk.add_argument("--object", action="append", type=_object, default=[], metavar="LABEL=TRACK.csv",
                    help="an object from a track alone (an agent's): becomes object-N with marks every 10 frames")
    mk.add_argument("--n0", type=int, help="first frame of the part to open (default: the objects' frames)")
    mk.add_argument("--n1", type=int, help="last frame of the part to open")
    mk.add_argument("--look", action="append", type=_span, default=[], metavar="FIRST-LAST[:what]",
                    help="a stretch to look at, and what to look for (repeatable)")
    mk.add_argument("--note", default="", help="what this file says or asks")
    mk.add_argument("--by", default="", help="who it is from")
    mk.add_argument("--agent", action="store_true", help="it is from an AI agent, not a person")
    mk.add_argument("--attach", action="append", default=[], help="a file to send with it: a figure (repeatable)")
    mk.add_argument("--out", help=f"where to write it (default: <tag>_<by>_<date>{SUFFIX} here)")
    mk.add_argument("--json", action="store_true")
    sh = sub.add_parser("show", help="what a shared file holds")
    sh.add_argument("file")
    sh.add_argument("--json", action="store_true")
    op = sub.add_parser("open", help="open a shared file: in the window if there is a display, else unpack it")
    op.add_argument("file")
    op.add_argument("--cases", help="where to unpack it (default: where the window saves results)")
    op.add_argument("--no-window", action="store_true", help="unpack it and find the video, but open no window")
    op.add_argument("--json", action="store_true")
    rr = sub.add_parser("rerun", help="measure every object of a shared file again, by the command its report records, and "
                                      "say whether it gives back its own numbers (minutes an object)")
    rr.add_argument("files", nargs="+", help="shared files (.mcdonald)")
    rr.add_argument("--cases", help="where to unpack and rerun them (default: a temporary folder, removed after)")
    rr.add_argument("--video-dir", action="append", default=[], metavar="DIR",
                    help="a folder to look for the video in as well (repeatable); beside the file, $MCDONALD_DATA and the "
                         "storage folder are looked in anyway, and the catalog last")
    rr.add_argument("--procs", type=int, help="worker processes for the stages")
    rr.add_argument("--strict", action="store_true", help="an object whose report tracked nothing counts as not rerunning")
    rr.add_argument("--json", action="store_true", help="print the result as JSON")
    a = ap.parse_args(argv)

    try:
        if a.what == "make":
            return _make(a)
        if a.what == "show":
            m = read(a.file)
            if a.json:
                print(json.dumps(m, indent=1))
            else:
                print("\n".join(summary(m)))
            return 0
        if a.what == "rerun":
            return _rerun(a)
        return _open(a)
    except ShareError as ex:
        raise vf.Stop(str(ex))


def _make(a):
    path, tag, _ = vf.resolve(a.video)
    folder, objects = (Path(a.case) if a.case else None), None
    tmp = None
    if a.object:
        import tempfile
        tmp = tempfile.TemporaryDirectory(prefix="mcdonald-share-")
        staged = Path(tmp.name) / tag
        if folder:
            shutil.copytree(folder, staged, ignore=shutil.ignore_patterns("frames", "__pycache__"))
        staged.mkdir(parents=True, exist_ok=True)
        start = 1 + max((int(d.name.split("-")[1]) for d in staged.glob("object-*") if d.name.split("-")[1].isdigit()), default=0)
        fps = vf.probe(path)["fps"]
        labels = objects_from_tracks(str(path), float(fps), tag, Path(tmp.name) / "new", a.object)
        for k, label in labels.items():
            shutil.move(str(Path(tmp.name) / "new" / f"object-{k}"), staged / f"object-{start + k - 1}")
        objects = {start + k - 1: label for k, label in labels.items()}
        folder = staged
    part = (a.n0, a.n1) if a.n0 is not None and a.n1 is not None else None
    if part is None:
        frames = []
        for t in (folder.rglob("*_autotrack.csv") if folder else ()):
            try:
                frames += list(vf.read_track(t))
            except (OSError, ValueError):
                pass
        if not frames and a.look:
            frames = [x for s in a.look for x in s[:2]]
        if frames:
            part = (min(frames), max(frames))
    by = a.by or ("an AI agent" if a.agent else "someone")
    out = Path(a.out) if a.out else Path(default_name(tag, by))
    try:
        made = make(out, path, folder=folder, part=part, look=a.look, note=a.note, by=by, agent=a.agent,
                    attach=a.attach, objects=objects)
    finally:
        if tmp is not None:
            tmp.cleanup()
    m = read(made)
    if a.json:
        print(json.dumps({"file": str(made), "manifest": m}, indent=1))
    else:
        print(f"wrote {made} ({made.stat().st_size / 2 ** 10:.0f} KB)")
        print("\n".join("  " + s for s in summary(m)))
    return 0


def _rerun(a):
    """`mcdonald share rerun`: does each file give back its own numbers (`mcdonald.rerun`)? Exit 1 if any does not."""
    from . import rerun
    say = (lambda *x: print(*x, file=sys.stderr, flush=True)) if a.json else (lambda *x: print(*x, flush=True))
    results, ok = rerun.rerun_files(a.files, a.cases, procs=a.procs, strict=a.strict, also=a.video_dir, say=say)
    if a.json:
        print(json.dumps(results, indent=1, default=str))
    return 0 if ok else 1


def _open(a):
    m = read(a.file)
    if not a.no_window:
        try:
            from . import mark_qt                      # noqa: F401 -- the window, if PySide6 and a display are here
            from .mark import choose_gui
            if choose_gui("auto") == "qt":
                w = mark_qt.open_shared(a.file, cases=a.cases)
                return 0 if w is None else w.run()
        except (ImportError, SystemExit):              # no PySide6, or no display: unpack it here instead
            pass
    import os
    cases = Path(a.cases or os.environ.get("MCDONALD_CASES", "").strip() or storage.home())
    folder, m = unpack(a.file, cases)
    video = find_video(m, also=[Path(a.file).parent])
    same, said = check_video(video, m["video"]) if video else (False, "the video is not on this computer")
    if a.json:
        print(json.dumps({"folder": str(folder), "video": str(video) if video else None, "same": same, "said": said}, indent=1))
    else:
        print("\n".join(summary(m)))
        print(f"unpacked into {folder}")
        print(said if video else f"{describe_video(m['video'])} is not on this computer: open it there by its name, "
              f"or put the file in {storage.videos()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
