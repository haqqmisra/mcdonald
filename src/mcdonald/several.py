"""Several things in one video: a case each, in turn, and one page that lists them.

A case is one video, one object, and one report whose bottom line is about that object;
every measuring step takes one track. A video with four things in it -- Galileo flyer 1:
two birds, a streak and a spot (2026-09-29) -- is four cases, and until 2026-10-06 that
was four folders made by hand, one command at a time. This is that procedure as one
function. Each thing's marks go in a folder of its own under the video's (`object-1`,
`object-2` ...); `stages.run_case` is run on each in turn, over the frames the thing is in
(what `mcdonald run VIDEO --marks .../object-N/<tag>_marks.json --n0 A --n1 B --out
.../object-N` is, to the last digit); and `<tag>_objects.md` beside the folders lists
them: what each was chosen as, how far it was followed, its report's bottom line, and
whether anyone has looked at its track sheet.

Nothing is decided here that a case does not decide. Which things are objects is the
judgment of whoever chose them -- a person at Find's list in the window, an agent with
`mcdonald mark --set` -- and each case records that as it would alone. Nobody is asked
about a track sheet while the queue runs, so every report says its object's numbers are
provisional until someone has looked at the sheet and said so (`mcdonald report CASE.json
--i-looked`, or the banner on the report's page in the window); the list says which have
been. The background step (`layers`) is measured for each case on its own: its templates
are made with the object's track in hand, so two objects cannot share them.

Since 2026-10-08 the person can say how many objects they are looking for (`objects`:
`run --each DIR --objects N`, the box on the window's segment step). The count does two
things here. It is held against what was followed, on the list's first line ("You looked
for 6 objects: 6 were followed ..."). And where fewer things were found than asked for
and one of them is a group of points -- PR135's flock, which Find lists as two groups of
three -- the group's members become objects of their own (`split_group`): each a folder
with the member's positions as its track (`<tag>_autotrack.csv`, written here, so the link
cannot wander to a neighbour), marks every ten frames for the record, and `<tag>_group.json`
naming the group it came from. A member's case skips the groups stage, takes its beat from
the group's flicker stage (`flicker.of_member`: measured with its fellows, the beat its own
where it is out of step with one of them), and knows its fellows when the tether stage
finds "something moving with it". The group's own case stays: its report is the flock's.

No interface in it. `mcdonald run VIDEO --each DIR` and the window's "Follow and measure
the ticked ones" (`several_qt`) are the two shells, and what they write is the same.
"""
import csv
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import forensics as vf
from . import stages
from .mark import MarkSet, save_all
from .report import Case

NAME = re.compile(r"^object-(\d+)$")
PAD_SECONDS = 2.0           # each thing is measured over the frames it was marked on and this long either side (`stages.around`)
LIST = "_objects"           # <tag>_objects.md and .json, beside the folders
GROUP = "_group.json"       # in a member's folder: which object's group it is a member of
MARK_EVERY = 10             # a member's marks, for the record: every this many frames of its track, and its last


@dataclass
class Thing:
    """One of the things: its folder, its marks, and where its case has got to."""
    k: int
    folder: Path
    marks: Path                                 # its <tag>_marks.json
    tag: str
    state: str = "waiting"                      # waiting, measuring, done, stopped, failed
    frames: tuple = None                        # (first, last) of the frames it is measured over
    said: list = field(default_factory=list)    # what was said while it was measured, line by line
    case: object = None
    files: list = field(default_factory=list)
    error: str = None
    group: dict = None                          # a member of a group: {object, member, folder, siblings}, from <tag>_group.json

    @property
    def track(self):
        """A member's track, written when it was split from its group: measured as it is, not linked again."""
        p = self.folder / f"{self.tag}_autotrack.csv"
        return p if self.group and p.exists() else None

    @property
    def prefix(self):
        return self.folder / self.tag

    @property
    def report(self):
        """Its report's path, if it has one."""
        p = Path(f"{self.prefix}_case.md")
        return p if p.exists() else next(iter(sorted(self.folder.glob("*_case.md"))), None)

    @property
    def case_json(self):
        r = self.report
        return None if r is None else Path(str(r)[:-len("_case.md")] + "_case.json")


def things(base):
    """The things under `base`, in order: every `object-N` folder that holds one object's marks."""
    out = []
    for d in Path(base).iterdir() if Path(base).is_dir() else ():
        m = NAME.match(d.name)
        marks = sorted(d.glob("*_marks.json")) if m and d.is_dir() else []
        if marks:
            tag = marks[0].name[:-len("_marks.json")]
            group = None
            try:
                g = d / f"{tag}{GROUP}"
                group = json.loads(g.read_text(encoding="utf-8")) if g.exists() else None
            except (OSError, ValueError):
                group = None
            out.append(Thing(int(m.group(1)), d, marks[0], tag, group=group))
    return sorted(out, key=lambda t: t.k)


def place(clip, tag, base, marks, how=None, k=None, video=None, seen=None):
    """One thing's marks into a folder of its own, as a save would write them (`mark.save_all`:
    the marks, their table, and the strip that shows each on its frame). `marks` is {frame: (x, y)}
    and `how` what every one of them is recorded as -- "proposed: ..." from Find's list, "agent:
    ..." -- or None for a hand's. The folder is the next `object-N` not yet there, so that nothing
    measured earlier is written over; returns the Thing. `video` names the video in the marks
    file where the clip's own name for it is not the one to record, and `seen` is (first, last),
    the frames the thing was seen on by whatever proposed the marks: Find's marks keep off the
    frame's edge, where the detector cannot see, so a thing is seen on more frames than it is
    marked on, and `run_each` measures it over those."""
    base = Path(base)
    k = k or 1 + max((t.k for t in things(base)), default=0)
    while (base / f"object-{k}").exists():
        k += 1
    folder = base / f"object-{k}"
    folder.mkdir(parents=True)
    ms = MarkSet(tag, video or clip.video, clip.fps)
    ms.seen = tuple(seen) if seen else None
    for n, (x, y) in sorted(marks.items()):
        ms.add("object", n, x, y, how=how)
    save_all(clip, ms, str(folder / tag))
    return Thing(k, folder, folder / f"{tag}_marks.json", tag)


def measured(t):
    """Has this thing a report, made from the marks as they are now and measured to its end?"""
    js = t.case_json
    if js is None or not js.exists() or js.stat().st_mtime < t.marks.stat().st_mtime:
        return False
    try:
        return Case.load(js).stopped_in() is None
    except (OSError, ValueError, KeyError):
        return False


def member_tracks(members_csv):
    """{member id: {frame: (x, y)}} from a groups stage's <tag>_members.csv, longest first."""
    tracks = {}
    with open(members_csv, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            tracks.setdefault(int(r["member"]), {})[int(r["frame"])] = (float(r["x_px"]), float(r["y_px"]))
    return dict(sorted(tracks.items(), key=lambda kv: (-len(kv[1]), kv[0])))


def is_group(t):
    """Did this thing's case find it to be several points moving together, with their tracks written?"""
    js = t.case_json
    if t.group or js is None or not js.exists() or not Path(f"{t.prefix}_members.csv").exists():
        return False
    try:
        f = (Case.load(js).stages.get("groups") or {}).get("fields") or {}
    except (OSError, ValueError, KeyError):
        return False
    return bool(f.get("several")) and (f.get("members_followed") or 0) >= 2


def children(found, k):
    """The things that are members of object k's group."""
    return [t for t in found if t.group and t.group.get("object") == k]


def split_group(clip, t, base, asked, say=print):
    """Object `t`, a group of points: each member followed long enough for a beat (`flicker.MIN_FRAMES`,
    60 frames; PR135's birds found again after the group's track jumps, 32 frames each, are not made
    objects twice) becomes an object of its own under `base` -- the next folders -- with the member's
    positions as its track, marks every MARK_EVERY frames of it for the record (what it was chosen as,
    and by what), and <tag>_group.json naming the group. Nothing is measured here. Returns the new things."""
    from . import flicker
    tracks = {i: tr for i, tr in member_tracks(f"{t.prefix}_members.csv").items() if len(tr) >= flicker.MIN_FRAMES}
    made = []
    for i, tr in tracks.items():
        ns = sorted(tr)
        marks = {n: tr[n] for n in ns[::MARK_EVERY]}
        marks[ns[-1]] = tr[ns[-1]]
        how = (f"member {i} of object {t.k}, one of the {len(tracks)} points of that group followed on their own because "
               f"{asked} object{'s were' if asked != 1 else ' was'} looked for and fewer things were found")
        m = place(clip, t.tag, base, marks, how, video=clip.video, seen=(ns[0], ns[-1]))
        with open(m.folder / f"{t.tag}_autotrack.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["frame", "x", "y"])
            for n in ns:
                w.writerow([n, round(tr[n][0], 2), round(tr[n][1], 2)])
        m.group = dict(object=t.k, member=i, folder=t.folder.name, members=f"{t.folder.name}/{t.tag}_members.csv",
                       siblings=[j for j in tracks if j != i])
        (m.folder / f"{t.tag}{GROUP}").write_text(json.dumps(m.group, indent=1), encoding="utf-8")
        say(f"object {m.k}: member {i} of object {t.k}'s group, {len(ns)} frames {ns[0]}-{ns[-1]}, into {m.folder}")
        made.append(m)
    return made


def tally(found, asked=None):
    """The count against what was followed: {asked, followed, members, groups, others, missing, sentence}.
    A group whose members became objects is counted through them, not as a thing of its own."""
    parents = {t.k for t in found if children(found, t.k)}
    members = [t for t in found if t.group]
    others = [t for t in found if not t.group and t.k not in parents]
    done = lambda t: t.case is not None or (t.case_json is not None and t.case_json.exists())
    followed = [t for t in members + others if done(t) and _followed(t.case or Case.load(t.case_json))]
    d = dict(asked=asked, followed=len(followed), members=len([t for t in followed if t.group]), groups=sorted(parents),
             others=len([t for t in followed if not t.group]), missing=max(0, (asked or 0) - len(followed)), sentence="")
    if asked:
        ks = d["groups"]
        s = (f"You looked for {asked} object{'s' if asked != 1 else ''}: {d['followed']} "
             f"{'were' if d['followed'] != 1 else 'was'} followed")
        if d["members"]:
            s += (f", {d['members']} of them the members of {len(ks)} group{'s' if len(ks) != 1 else ''} "
                  f"(object{'s' if len(ks) != 1 else ''} {', '.join(str(k) for k in ks)})")
        if d["missing"]:
            s += f"; {d['missing']} {'were' if d['missing'] != 1 else 'was'} not found"
        elif d["followed"] > asked:
            s += f", {d['followed'] - asked} more than you looked for"
        d["sentence"] = s + "."
    return d


def run_each(video, base, workdir=None, n0=None, n1=None, clip=None, masks=None, pad_seconds=PAD_SECONDS, again=False,
             say=print, progress=None, stop=None, told=None, sheet=None, objects=None, **kw):
    """Every thing under `base`, linked from its marks and measured, one after another.

    `video` is a path or a record id, as for `run_case`, and `kw` is `run_case`'s own: what is
    known of the video (`fov`, `range_m` ...), `skip`, `only`, `procs`. Each thing is measured
    over the frames its marks are on (and the frames its marks file says it was seen on, where
    Find placed them) and `pad_seconds` either side, inside `n0`..`n1` (or the
    whole video), into its own folder; `clip` is an opened Clip of the frames those are taken
    from, for a caller that has one (the window: the segment that is open), and `masks` that
    clip's static masks, used where a thing's frames are all of it. One that has a report from
    the same marks, measured to its end, is not measured again unless `again`.

    `say` and `progress(text, done, total)` are `run_case`'s, the second with which thing it is
    put before each step's name; `stop` is asked before each thing and inside each, as
    `run_case` asks it: the step under way ends, that thing's report is written of the steps
    that ran, and the things not yet started are left as they are. `told(thing)` is called when
    a thing starts and when it ends. `sheet` is `run_case`'s track sheet layout, or a function
    of a thing's Clip that gives it (a window fits the sheet to a screen). The list (`index`)
    is written again after each, so that it is true whenever the queue stops. `objects` is how
    many the person is looking for, if they said: held against what was followed on the list,
    and, where fewer things were found than that, a thing found to be a group of points has its
    members made objects of their own (`split_group`) and measured after the rest. Returns the
    things, each with its state."""
    base = Path(base)
    found = things(base)
    if not found:
        raise vf.Stop(f"{base}: no folder object-1, object-2 ... with the marks of one object in it. Put each object's marks "
                      f"in its own: mcdonald mark VIDEO --set object@FRAME=X,Y ... --out {base}/object-1", vf.EXIT_NOTHING)
    outer = clip if clip is not None else vf.Clip(vf.resolve(str(video))[0], workdir, n0, n1, extract=False)
    todo = [t for t in found if again or not measured(t)]
    for t in found:
        if t not in todo:
            t.state = "done"
            t.case = Case.load(t.case_json)
    asked = int(objects) if objects else None
    j = 0
    while j < len(todo):
        t = todo[j]
        j += 1
        if stop is not None and stop():
            break
        ms = MarkSet(t.tag, outer.video, outer.fps).load(t.marks)
        frames = sorted(ms.marks.get("object", {})) + list(ms.seen or ())      # marked on, and seen on by whatever marked it
        frames = [n for n in frames if outer.n0 <= n <= outer.n1]
        if not frames:
            t.state, t.error = "failed", f"no mark of the object on frames {outer.n0}-{outer.n1} in {t.marks.name}"
            say(f"object {t.k}: {t.error}")
            continue
        a, b = stages.around(frames, outer, pad_seconds)
        sub = clip if clip is not None and (a, b) == (clip.n0, clip.n1) else vf.Clip(outer.video, clip.dir if clip is not None else workdir, a, b)
        t.state, t.frames, t.said = "measuring", (a, b), []
        if told is not None:
            told(t)
        say(f"== object {t.k} ({j} of {len(todo)}): frames {a}-{b}, into {t.folder}")

        def tell(line, lines=t.said):
            lines.append(str(line))
            say(line)

        def step(text, done=None, total=None, place=f"object {t.k} ({j} of {len(todo)}) · "):
            progress(place + text, done, total)
        own = dict(kw)
        if t.group:                                      # a member of a group: its track is written, its beat is the group's stage's
            parent = next((p for p in found if p.k == t.group["object"]), None)
            fellows = member_tracks(base / t.group["members"]) if (base / t.group["members"]).exists() else {}
            own.update(track=str(t.track) if t.track else None, size=own.get("size") or 5.0,
                       skip=sorted(set(own.get("skip") or ()) | {"groups"}),
                       flicker_of=(str(parent.case_json), f"member {t.group['member']}") if parent and parent.case_json else None,
                       siblings={f"member {i}": tr for i, tr in fellows.items() if i != t.group["member"]})
        try:
            t.case, _, t.files = stages.run_case(str(video), marks=str(t.marks), out=str(t.folder), n0=a, n1=b, clip=sub,
                                                 masks=masks if sub is clip else None, i_looked=False, say=tell,
                                                 progress=step if progress is not None else None, stop=stop,
                                                 sheet=sheet(sub) if callable(sheet) else sheet, **own)
            t.state = "stopped" if t.case.stopped_in() else "done"
        except vf.Stop:
            raise
        except Exception as e:                           # one thing's failure is not the queue's: say it, and go on to the next
            t.state, t.error = "failed", f"{type(e).__name__}: {e}"
            tell(f"object {t.k} could not be measured: {t.error}")
        try:
            Path(f"{t.prefix}_log.txt").write_text("\n".join(t.said) + "\n", encoding="utf-8")
        except OSError:
            pass
        # fewer things than the person is looking for, and this one is a group of points: its members, each on its own
        if asked and t.state == "done" and not t.group and not children(found, t.k) and is_group(t) \
                and len(found) - len({p.k for p in found if children(found, p.k)}) < asked:
            try:
                made = split_group(sub, t, base, asked, say=tell)
            except (OSError, ValueError) as e:
                made = []
                tell(f"object {t.k}'s members could not be made objects of their own: {type(e).__name__}: {e}")
            found += made
            todo += made
        index(base, objects=asked)
        if told is not None:
            told(t)
    index(base, objects=asked)
    return found


def _followed(case):
    """What a case's track step says of the link: {frames, first, last, size_px, dark}, or None where nothing was followed."""
    f = (case.stages.get("track") or {}).get("fields") or {}
    if not f.get("frames"):
        return None
    return dict(frames=f["frames"], first=f.get("first"), last=f.get("last"), size_px=f.get("object_size_px"), dark=f.get("object_is_dark"))


def row(t):
    """One thing as fields, read from its folder: what the list is written from."""
    ms = MarkSet(t.tag, "", 1.0).load(t.marks)
    obj = ms.marks.get("object", {})
    hows = [ms.how_of("object", n) for n in sorted(obj)]
    kinds = sorted({ms.kind("object", n) for n in obj})
    chosen = next((h for h in hows if h), None) or "marked by hand"
    d = dict(object=t.k, folder=t.folder.name, marks=len(obj), marked_frames=[min(obj), max(obj)] if obj else None, placed_by=kinds,
             chosen_as=chosen, measured=False, stopped=None, followed=None, frames=None, bottom_line=None, track_sheet_looked_at=None,
             report=None, track_sheet=None, error=t.error,
             group={k: t.group[k] for k in ("object", "member") if k in t.group} if t.group else None)
    js = t.case_json
    if js is not None and js.exists():
        try:
            case = Case.load(js)
        except (OSError, ValueError, KeyError) as e:
            d["error"] = f"its report could not be read: {e}"
            return d
        clip = case.clip or {}
        d.update(measured=True, stopped=case.stopped_in(), followed=_followed(case), bottom_line=case.bottom_line(),
                 frames=[clip.get("n0"), clip.get("n1")] if clip else None,
                 track_sheet_looked_at=((case.stages.get("verify") or {}).get("fields") or {}).get("reviewed"),
                 report=f"{t.folder.name}/{t.report.name}")
        sheet = next(iter(sorted(t.folder.glob("*_all_frames.jpg"))), None)
        d["track_sheet"] = f"{t.folder.name}/{sheet.name}" if sheet else None
    return d


def asked_before(base):
    """How many objects the person said they were looking for, from the list written last."""
    try:
        return int(json.loads(next(Path(base).glob(f"*{LIST}.json")).read_text(encoding="utf-8")).get("asked") or 0) or None
    except (StopIteration, OSError, ValueError, TypeError):
        return None


def index(base, objects=None):
    """The list, written from what is in the folders: `<tag>_objects.md` for a person and `.json`
    for a program, beside the `object-N` folders. `objects` is how many were looked for, if said
    (kept from the list before when not given), held against what was followed on the first line.
    Returns (the page's path, its rows as fields); (None, []) where there is nothing to list."""
    base = Path(base)
    found = things(base)
    if not found:
        return None, []
    asked = int(objects) if objects else asked_before(base)
    rows = [row(t) for t in found]
    tag = found[0].tag
    n = len(rows)
    count = tally(found, asked)
    L = [f"# {tag.upper()}: {n} object{'s' if n != 1 else ''}, a report each", "",
         "One video with more than one thing in it. Each was taken as the object of a case of its own: followed from its own "
         "marks, measured over the frames it is in, and reported in its own folder. The numbers are in each report; this page "
         "lists them.", ""]
    if count["sentence"]:
        L += [f"**{count['sentence']}**", ""]
    for r in rows:
        mf = r["marked_frames"]
        kids = children(found, r["object"])
        L += [f"## Object {r['object']}" + (f" — frames {r['frames'][0]}–{r['frames'][1]}" if r["frames"] and r["frames"][0] is not None else ""), "",
              f"- **chosen as:** {r['chosen_as']}" + (f" ({r['marks']} marks, frames {mf[0]}–{mf[1]})" if mf else "")]
        if kids:
            L.append(f"- **a group of points:** its members are objects {', '.join(str(c.k) for c in kids)}, each with a report of its own")
        if not r["measured"]:
            L += [f"- **not measured yet**" + (f": {r['error']}" if r["error"] else ""), ""]
            continue
        f = r["followed"]
        L.append("- **followed:** " + (f"{f['frames']} frames, {f['first']}–{f['last']}, as a {'dark' if f['dark'] else 'bright'} spot "
                                       f"{f['size_px']:g} pixels wide" if f else
                                       "nothing: the link from its marks found no track, so nothing about the object was measured"))
        if r["stopped"]:
            L.append(f"- **stopped** {r['stopped']}: the steps after that did not run")
        L.append(f"- **bottom line:** {r['bottom_line']}")
        if f:
            L.append("- **track sheet:** " + ("looked at: the track is on the object in every frame" if r["track_sheet_looked_at"] else
                                              "not looked at yet, so the numbers for the object are provisional"
                                              + (f" ([the sheet]({r['track_sheet']}))" if r["track_sheet"] else "")))
        L += [f"- [the report]({r['report']}), in `{r['folder']}/`", ""]
    waiting = [r for r in rows if r["followed"] and not r["track_sheet_looked_at"]]
    if waiting:
        L += ["Nobody was asked about a track sheet while these were measured. Open each one, and if the ring is on the object in "
              "every frame say so: `mcdonald report " + f"{base.name}/object-N/{tag}_case.json --i-looked`" + ", or the banner at the "
              "top of the report's page in the window. Nothing is measured again.", ""]
    page = base / f"{tag}{LIST}.md"
    page.write_text("\n".join(L), encoding="utf-8")
    (base / f"{tag}{LIST}.json").write_text(json.dumps(dict(tag=tag, written=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                                           asked=asked, tally=count, objects=rows), indent=1), encoding="utf-8")
    return page, rows


def listed(case_json):
    """A case that is one of several was changed (its track sheet looked at): write the list
    again. Returns the page's path, or None for a case that stands alone."""
    folder = Path(case_json).resolve().parent
    if NAME.match(folder.name) and any(folder.parent.glob(f"*{LIST}.md")):
        return index(folder.parent)[0]
    return None
