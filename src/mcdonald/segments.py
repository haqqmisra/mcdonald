"""The segments of one video: a folder each, and the list of them (`mcdonald segments VIDEO`).

Until 2026-10-26 a video's results went in one folder (`<cases>/<tag>/`) whatever segment of it was open, so
measuring a second segment wrote over the first one's report. A tester on a Mac (Ravi Kopparapu, 2026-10-26):
"if i want to select a different segement, i have to close this and reopen again ... may be there is a way to have
a list of selected segment videos and corresponding reports"; Jacob chose a folder per segment, in the window first
and then ("go ahead and update the command line too") for every command. So a segment of a video -- chosen on the
window's segment step, or named with --n0/--n1 -- has a folder of its own inside the video's,
`segment-<first>-<last>` (frames, counted from 1), with its objects' folders inside it as before (`several`); the
whole video's results are the video's folder's own (`clip.named`, `clip.out_prefix`):

    <cases>/pr44/                       the whole video's, or what was measured before there were segment folders
      pr44_case.md ...
      segment-901-1680/pr44_case.md ...
      segment-2101-2400/object-1/ ...

The video's own folder is kept for the segment it already holds (`folder_for`): nothing written before is moved,
and naming that segment again goes on with its results. `--out` still names the folder outright. `mark --segment
A-B` puts marks in a segment's folder without changing the frames the link searches: `look --propose --n0 A --n1 B`
prints it on the lines that take its rows, so that look, mark and run meet in one folder.

`listed` is the window's list on the whole-video page and this command's: every segment with something in its
folder, its report's label (`Case.conclusion`), and its reports.
"""
import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import clip as vf
from . import several
from .mark import MarkSet
from .report import Case, emit, envelope

NAME = re.compile(r"^segment-(\d+)-(\d+)$")


def name(n0, n1):
    return f"segment-{int(n0)}-{int(n1)}"


@dataclass
class Segment:
    """One segment of the video, and what its folder holds."""
    n0: int
    n1: int
    folder: Path
    marked: bool = False                         # its marks are saved
    reports: list = field(default_factory=list)  # [(object number or None for the segment's own, its report's path)]
    label: str = None                            # its report's label ("Beats like a bird", "No conclusion yet" ...)
    headline: str = None


def _case(folder, tag):
    p = Path(folder) / f"{tag}_case.json"
    try:
        return Case.load(p) if p.exists() else None
    except (OSError, ValueError, KeyError):
        return None


def _span(case):
    """(first, last) of the segment a case was measured on: the one the person chose, else its clip's frames."""
    if case is None:
        return None
    if case.segment:
        return int(case.segment[0]), int(case.segment[1])
    c = case.clip or {}
    return (int(c["n0"]), int(c["n1"])) if c.get("n0") is not None and c.get("n1") is not None else None


def _objects(folder):
    """The folder's objects with a report: [(Thing, its Case or None)]."""
    out = []
    for t in several.things(folder):
        js = t.case_json
        if js is not None and js.exists():
            try:
                out.append((t, Case.load(js)))
            except (OSError, ValueError, KeyError):
                out.append((t, None))
    return out


def _segment(folder, tag, span):
    """A Segment for `folder`, or None where nothing is in it."""
    folder = Path(folder)
    own, objects = _case(folder, tag), _objects(folder)
    marks = (folder / f"{tag}_marks.json").exists()
    if span is None:
        span = _span(own) or next((_span(c) for _, c in objects if _span(c)), None)
    if span is None or not (own or objects or marks):
        return None
    s = Segment(span[0], span[1], folder, marked=marks)
    if own is not None and (folder / f"{tag}_case.md").exists():
        s.reports.append((None, folder / f"{tag}_case.md"))
    s.reports += [(t.k, t.report) for t, _ in objects]
    try:
        if own is not None:
            s.label, s.headline = own.conclusion()
        elif objects:
            s.label = f"{len(objects)} objects" if len(objects) > 1 else "1 object"
            if len(objects) == 1 and objects[0][1] is not None:
                s.label, s.headline = objects[0][1].conclusion()
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):     # a case from long ago that today's words cannot read: its report stands
        s.label = s.label or "Report"
    return s


def listed(base, tag):
    """The video's segments with something in their folders, in the video's order: the video's own folder (what was
    measured before segments had folders, or by a command line) and each `segment-A-B` folder in it."""
    base = Path(base)
    out = [_segment(base, tag, None)] if base.is_dir() else []
    for d in sorted(base.iterdir()) if base.is_dir() else ():
        m = NAME.match(d.name)
        if m and d.is_dir():
            out.append(_segment(d, tag, (int(m.group(1)), int(m.group(2)))))
    return sorted((s for s in out if s is not None), key=lambda s: (s.n0, s.n1, s.folder != base))


def folder_for(base, tag, n0, n1):
    """Where segment n0..n1 of the video keeps its results: the video's own folder where that already holds this segment
    (its report's, or marks made before segments had folders, all on its frames), else `segment-n0-n1` in it."""
    base = Path(base)
    own = _case(base, tag)
    span = _span(own) or next((_span(c) for _, c in _objects(base) if _span(c)), None)
    if span == (int(n0), int(n1)):
        return base
    marks = base / f"{tag}_marks.json"
    if span is None and marks.exists():
        try:
            frames = [n for c in MarkSet(tag, "", 1.0).load(marks).marks.values() for n in c]
        except (OSError, ValueError, KeyError):
            frames = []
        if frames and n0 <= min(frames) and max(frames) <= n1:
            return base
    return base / name(n0, n1)


def clock(seconds):
    return f"{int(seconds // 60)}:{seconds % 60:05.2f}"


def _fps(base, tag, video):
    """The video's frame rate, for the segments' times: from the video where it is here, else from a report."""
    if video is not None and Path(video).exists():
        try:
            return float(vf.probe(video)["fps"])
        except (vf.Stop, OSError, KeyError, ValueError):
            pass
    for js in sorted(Path(base).rglob(f"{tag}_case.json")):
        c = _case(js.parent, tag)
        if c is not None and (c.clip or {}).get("fps"):
            return float(c.clip["fps"])
    return None


def _shown(path):
    """A path as short as it can be said: from here where it is under here."""
    try:
        return os.path.relpath(path)
    except ValueError:                                # another drive, on Windows
        return str(path)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="mcdonald segments",
        description="The segments of a video that have results, each in its own folder: its frames and times, what its "
                    "report says, and where its reports are -- what the window lists on the whole video's page. Nothing "
                    "is measured, and nothing is downloaded.")
    ap.add_argument("video", help="a path to the video, or its catalog name (PR44)")
    ap.add_argument("--out", metavar="DIR", help="the video's results folder (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true", help="print the list as JSON on stdout")
    args = ap.parse_args(argv)
    try:
        video, tag, _ = vf.resolve(args.video, fetch=lambda rec, dest: dest)     # its name is enough: never downloaded
    except vf.Stop as e:
        ap.exit(2, f"mcdonald segments: {e}\n")
    base = vf.case_dir(args.out, tag, create=False)
    found = listed(base, tag)
    fps = _fps(base, tag, video) if found else None
    rows = []
    for seg in found:
        rows.append(dict(first=seg.n0, last=seg.n1, folder=str(seg.folder),
                         time=f"{clock((seg.n0 - 1) / fps)} to {clock((seg.n1 - 1) / fps)}" if fps else None,
                         marked=seg.marked, label=seg.label, headline=seg.headline,
                         reports=[dict(object=k, report=str(r)) for k, r in seg.reports],
                         to_open=f"mcdonald mark {args.video} --n0 {seg.n0} --n1 {seg.n1}"
                                 + (f" --out {seg.folder}" if args.out else "")))
    if args.json:
        emit(envelope("segments", {"video": args.video, **({"out": args.out} if args.out else {})}, None, [],
                      {"folder": str(base), "segments": rows}))
        return 0
    if not rows:
        print(f"{tag}: no segment has results in {_shown(base)}")
        return 0
    print(f"{tag}: {len(rows)} segment{'s' if len(rows) != 1 else ''} with results in {_shown(base)}")
    for r in rows:
        print(f"  frames {r['first']}-{r['last']}" + (f"  ({r['time']})" if r["time"] else "")
              + f"  {r['label'] or ('no report yet: marks only' if r['marked'] else 'no report yet')}")
        for o in r["reports"]:
            print(f"      {'object ' + str(o['object']) + ': ' if o['object'] is not None else ''}{_shown(o['report'])}")
    print(f"to open one in the window: {rows[0]['to_open']} (its frames), and its results come with it")
    return 0


if __name__ == "__main__":
    sys.exit(main())

