"""The segments of one video opened in the window: a folder each, and the list of them.

Until 2026-10-26 a video's results went in one folder (`<cases>/<tag>/`) whatever segment of it was open, so
measuring a second segment wrote over the first one's report. A tester on a Mac (Ravi Kopparapu, 2026-10-26):
"if i want to select a different segement, i have to close this and reopen again ... may be there is a way to have
a list of selected segment videos and corresponding reports"; Jacob chose a folder per segment. So a segment
chosen on the window's segment step goes in a folder of its own inside the video's, `segment-<first>-<last>`
(frames, as the step counts them, from 1), with its objects' folders inside it as before (`several`):

    <cases>/pr44/                       what was measured before there were segment folders, or from a command
      pr44_case.md ...                  line that named the frames (`run PR44 --n0 ... --n1 ...`): one segment
      segment-901-1680/pr44_case.md ...
      segment-2101-2400/object-1/ ...

The video's own folder is kept for the segment it already holds (`folder_for`): nothing written before is moved,
and opening that segment again opens its results. The command line is as it was: `--out` names the folder, and
without it a command writes in `<tag>/`; `--out pr44/segment-901-1680` is a window's segment.

`listed` is what the window's whole-video page shows: every segment with something in its folder, its report's
label (`Case.conclusion`), and its reports. No interface in it.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import several
from .mark import MarkSet
from .report import Case

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
