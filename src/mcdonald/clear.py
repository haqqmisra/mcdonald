"""Starting a case over: what a results folder remembers, set aside (`mcdonald clear DIR`).

Jacob, 2026-11-22, after PR169 in the window. The one press had followed the one bird as three objects; he opened
the video again, said he was looking for 1 object, and the press measured the three old folders again: "this could
be because the old report was still present. It may be helpful for the user to have a way to "clear" the memory of
a specific case, if they want to start over." What a case remembers is what is in its results folder: the next
`mark`, `run` or press of the window's one button goes on from the marks, the track and the objects' folders it
finds there. So starting over is moving those out of the way, and this is the one function that does it
(`set_aside`), for the window's "Start over" (`mark_qt.QtMarker.start_over`, `auto_qt.AutoCard`) and for the
command, which is for an agent with no display.

A results folder is a video's (`<tag>/`) or a segment's (`<tag>/segment-A-B/`: `segments`), or whatever `--out`
named. What is set aside, worked out from what writes there and not from one folder:

- every file there whose name starts with the case's tag and an underscore. Every command writes through one
  prefix, `<folder>/<tag>` (`clip.out_prefix`), so that is the marks and their strip (`mark.save_all`), the
  automatic track (`autolink.save_track`), every stage's tables and pictures and the report (`stages.run_case`),
  the list of several objects (`several.index`), the sound's reading, a PDF `report --pdf` wrote, and whatever a
  stage added since this was written;
- every `object-N` folder (`several`), whole: each is a case of its own, made by this one.

What stays where it is:

- other segments' folders (`segment-A-B`), and anything set aside before (`earlier`);
- the two files in `KEEP`: the zoom states `mcdonald zoom` wrote, which a later `run` reads as given (a case started
  over is then measured with the same zoom states, and so is a segment that reads the whole video's), and the
  thread of a shared file (`share.KEPT`), which is correspondence, not a measurement;
- any file or folder not named for the case: someone's notes, a PDF saved under a name of their own;
- the video, and its frames (the work folder is elsewhere, and its caches are keyed by content).

Nothing is deleted unless asked. The results go into a folder of their own inside the results folder,
`earlier/<date>_<time>/`, so that a slip is undone by moving them back, and a second start over does not write over
the first. `several.things` and `segments.listed` read only `object-N` and `segment-A-B`, so neither takes
`earlier` for an object or a segment, and `share` leaves it out of a file to send (test_cli holds all three).

No interface in it. What the window remembers of a video in its own settings (how many objects were said last
time: `mark_qt.remembered_objects`) is the window's to reset.
"""
import argparse
import glob
import shutil
import sys
import types
from datetime import datetime
from pathlib import Path

from . import clip as vf
from . import segments, several
from .report import emit, envelope

EARLIER = "earlier"                              # in a results folder: what was set aside, a dated folder each time
STAMP = "%Y-%m-%d_%H%M"                          # that folder's name: the day and the minute, local time
ANCHORS = ("_marks.json", "_case.json", f"{several.LIST}.json")     # the files a case's tag is read from
KEEP = ("_zoom.json", "_share.json")             # <tag>_zoom.json (`mcdonald zoom`), <tag>_share.json (`share.KEPT`): see above


def tags(folder):
    """The tags of the cases a results folder holds: what its files' names start with. A case is known by its marks
    (`<tag>_marks.json`), its report (`<tag>_case.json`) or its list of objects (`<tag>_objects.json`), here or in one
    of its `object-N` folders (as `several.things` reads an object's tag). A folder with none of these -- one stage's
    command run alone -- has the tag every command gives it, its own name (`clip.case_dir`), or its video's folder's
    for a segment, where a file starts with that."""
    folder = Path(folder)
    if not folder.is_dir():
        return []
    found = set()
    for where in [folder] + [d for d in folder.iterdir() if d.is_dir() and several.NAME.match(d.name)]:
        for end in ANCHORS:
            found |= {p.name[:-len(end)] for p in where.glob(f"*{end}") if p.is_file() and p.name != end}
    if not found:
        name = folder.parent.name if segments.NAME.match(folder.name) else folder.name
        if any(p.is_file() for p in folder.glob(f"{glob.escape(name)}_*")):
            found.add(name)
    return sorted(found)


def _of(d, names):
    """Is an `object-N` folder one of these cases': has it a file named for one of them, or nothing in it at all?"""
    inside = [p.name for p in d.iterdir()]
    return not inside or any(n.startswith(f"{t}_") for n in inside for t in names)


def remembered(folder, tag=None):
    """(what `set_aside` would move, what it keeps of the case's own, what else is there), each a sorted list of
    paths in `folder`: the rule at the top of this module. `tag` is the one case to look for (the window's: the
    video that is open); without it, every case the folder holds (`tags`)."""
    folder = Path(folder)
    names = [tag] if tag else tags(folder)
    move, kept, left = [], [], []
    for p in sorted(folder.iterdir()) if folder.is_dir() else ():
        if p.is_dir() and not p.is_symlink():
            if p.name == EARLIER:
                continue                              # what was set aside before: neither moved again nor anyone else's
            (move if several.NAME.match(p.name) and _of(p, names) else left).append(p)
        elif any(p.name.startswith(f"{t}_") for t in names):
            (kept if p.name.endswith(KEEP) else move).append(p)
        else:
            left.append(p)
    return move, kept, left


def holds(folder, tag=None):
    """Has this results folder anything a start over would set aside? (The window asks at every step.)"""
    return bool(remembered(folder, tag)[0])


def _dated(folder, when=None):
    """The folder the results go into: `earlier/<date>_<time>` in `folder`, with -2, -3 ... where that minute's is
    there already (two starts over in one minute)."""
    stamp = (when or datetime.now()).strftime(STAMP)
    dest, k = Path(folder) / EARLIER / stamp, 1
    while dest.exists():
        k += 1
        dest = Path(folder) / EARLIER / f"{stamp}-{k}"
    return dest


def _files(p):
    """Every file of a path to move: itself, or what is in the folder it is."""
    return [q for q in sorted(p.rglob("*")) if q.is_file()] if p.is_dir() else [p]


def set_aside(folder, tag=None, delete=False, dry_run=False, when=None):
    """What the results folder `folder` remembers of its case, moved into `earlier/<date>_<time>/` inside it -- or,
    with `delete`, removed for good. `tag` names the one case to set aside where the folder may hold another video's
    too (the window passes the open video's); `dry_run` moves nothing and says what would move; `when` is the time the
    dated folder is named for (now). All of it moves or none of it: where one move fails, those made are put back and
    the OSError is raised. (A delete cannot be put back: it stops at the failure, and the error says so.)

    Returns what was done, as fields: `folder`, `tags`, `moved` (the names set aside, as they were in the folder),
    `into` (the dated folder, None where nothing moved or it was deleted), `deleted`, `dry_run`, `kept` and `left`
    (names that stayed: the case's own in `KEEP`, and what is not the case's), and counts a caller can say:
    `objects` (object folders), `marks`, `tracks` and `reports` (files of each, the objects' too) and `files` (all of
    them). `said` makes the sentences."""
    folder = Path(folder)
    move, kept, left = remembered(folder, tag)
    inside = [q for p in move for q in _files(p)]
    count = lambda end: sum(q.name.endswith(end) for q in inside)
    got = dict(folder=str(folder), tags=[tag] if tag else tags(folder), moved=[p.name for p in move], into=None,
               deleted=bool(delete and move and not dry_run), dry_run=bool(dry_run), kept=[p.name for p in kept],
               left=[p.name for p in left], objects=sum(p.is_dir() for p in move), marks=count("_marks.json"),
               tracks=count("_autotrack.csv"), reports=count("_case.md"), files=len(inside))
    if not move:
        return got
    if delete:
        if not dry_run:
            for p in move:
                try:
                    shutil.rmtree(p) if p.is_dir() else p.unlink()
                except OSError as e:
                    raise OSError(f"{p} could not be deleted ({e}); what came before it in {folder} is gone") from e
        return got
    dest = _dated(folder, when)
    got["into"] = str(dest)
    if dry_run:
        return got
    dest.mkdir(parents=True)
    done = []
    try:
        for p in move:
            shutil.move(str(p), str(dest / p.name))
            done.append(p)
    except OSError:
        for p in reversed(done):                      # all or none: what moved goes back where it was
            try:
                shutil.move(str(dest / p.name), str(p))
            except OSError:
                pass
        try:
            dest.rmdir()
            dest.parent.rmdir()                       # `earlier` itself, where this was the first time
        except OSError:
            pass
        raise
    return got


def _n(n, one, many=None):
    return f"{n} {one if n == 1 else many or one + 's'}"


def said(got):
    """What `set_aside` did, in sentences for a person: [the finding, where the results are and that nothing was
    deleted, what stayed]. The window says its own short one from `into`."""
    folder = got["folder"]
    if not got["moved"]:
        return [f"Nothing is saved for a case in {folder}, so there is nothing to set aside."]
    n_files = len(got["moved"]) - got["objects"]
    what = " and ".join(x for x in (_n(n_files, "file") if n_files else "",
                                    _n(got["objects"], "object folder") if got["objects"] else "") if x)
    holds_ = ", ".join(x for x in (_n(got["marks"], "set of marks", "sets of marks") if got["marks"] else "",
                                   _n(got["tracks"], "track") if got["tracks"] else "",
                                   _n(got["reports"], "report") if got["reports"] else "") if x)
    with_ = f" ({holds_})" if holds_ else ""
    if got["dry_run"]:
        out = [f"This would {'delete' if got['into'] is None else 'set aside'} {what}{with_} from {folder}. Nothing was changed."]
        if got["into"]:
            out.append(f"They would go into {got['into']}.")
    elif got["deleted"]:
        out = [f"Deleted {what}{with_} from {folder}. They cannot be brought back."]
    else:
        out = [f"Set aside {what}{with_} from {folder}.",
               f"They are in {got['into']}. Nothing was deleted: to bring a result back, move it out of that folder."]
    stay = got["kept"] + got["left"]
    if stay:
        out.append("Left where " + ("it was: " if len(stay) == 1 else "they were: ") + ", ".join(stay) + ".")
    return out


def folder_of(what, out=None, n0=None, n1=None):
    """The results folder a command line means: `what` itself where it is a folder and nothing else was said, else
    the folder every command gives the video `what` (a path or a catalog name): `--out`, or ./<tag> (`clip.case_dir`),
    and for a segment named with --n0/--n1 its own folder in that (`clip.named`, `segments.folder_for`). The video is
    never downloaded: its name is enough. Returns (the folder, the tag or None for a folder given outright)."""
    if out is None and n0 is None and n1 is None and Path(what).expanduser().is_dir():
        return Path(what).expanduser(), None
    try:
        video, tag, _ = vf.resolve(str(what), fetch=lambda rec, dest: dest)
    except vf.Stop as e:                              # neither a folder nor a video: said as both, in the words resolve has for it
        if out is None and n0 is None and n1 is None:
            raise vf.Stop(f"{what} is not a results folder on this computer, and not a video either ({str(e).splitlines()[0]})",
                          e.exit_code)
        raise
    base = vf.case_dir(out, tag, create=False)
    if out or (n0 is None and n1 is None):
        return base, tag
    if Path(video).is_file():                         # the segment as every command names it: the whole video is the video's folder
        segment = vf.named(n0, n1, types.SimpleNamespace(total=vf.probe(video)["frames"]))
    elif n0 is None or n1 is None:
        raise vf.Stop(f"{what} is not on this computer, so its length is not known: name the segment with both --n0 and --n1",
                      vf.EXIT_USAGE)
    else:
        segment = (int(n0), int(n1))
    return (segments.folder_for(base, tag, *segment) if segment else base), tag


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="mcdonald clear",
        description="Start a case over. A case's results folder holds what the next run goes on from: the marks, the "
                    "track, the reports and each object's folder. This sets them aside, so the next run starts with "
                    "nothing saved. They are moved into a dated folder inside the results folder, earlier/DATE_TIME. "
                    "Nothing is deleted unless you give --delete. The video, its saved frames, other segments' folders "
                    "and files not named for the case are not touched.")
    ap.add_argument("what", metavar="DIR", help="the results folder to start over: a video's (./pr44), a segment's "
                                                "(./pr44/segment-901-1680), or the folder --out named. Or a video, as a "
                                                "path or its catalog name (PR44): its results folder is then found as "
                                                "every command finds it")
    ap.add_argument("--out", metavar="DIR", help="with a video: its results folder, where a command was given --out "
                                                 "(default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--n0", type=int, help="with a video: the first frame of the segment to start over (its own folder, "
                                           "./<tag>/segment-<n0>-<n1>)")
    ap.add_argument("--n1", type=int, help="with a video: the last frame of that segment")
    ap.add_argument("--delete", action="store_true", help="delete the results for good, in place of setting them aside")
    ap.add_argument("--dry-run", action="store_true", help="change nothing: list what would be set aside, and what would stay")
    ap.add_argument("--json", action="store_true", help="print what was done as JSON on stdout (the envelope every command prints)")
    args = ap.parse_args(argv)
    inputs = {k: v for k, v in vars(args).items() if v not in (None, False) and k != "json"}
    folder, tag = folder_of(args.what, args.out, args.n0, args.n1)
    try:
        got = set_aside(folder, tag, delete=args.delete, dry_run=args.dry_run)
    except OSError as e:
        raise vf.Stop(f"the results in {folder} could not be {'deleted' if args.delete else 'set aside'}: {e}", vf.EXIT_INPUT)
    lines = said(got)
    out = sys.stderr if args.json else sys.stdout
    print(lines[0], file=out)
    for name in got["moved"]:
        print(f"  {name}{'/' if several.NAME.match(name) else ''}", file=out)
    for line in lines[1:]:
        print(line, file=out)
    if args.json:
        files = [str(Path(got["into"]) / m) for m in got["moved"]] if got["into"] and not got["dry_run"] else []
        emit(envelope("clear", inputs, None, files, dict(got, said=lines)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
