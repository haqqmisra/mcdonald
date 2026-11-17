"""`mcdonald batch` -- every frame of every video: found, followed, measured and reported, with nobody at the window.

ROADMAP.md 0.6, objective 1. Until 2026-11-13 a pass over the whole catalog was a folder of scripts run by hand
(`tools/sweep/`: the beat pass of October, which followed 1,576 objects in 122 videos and measured each by `flicker`
alone). This is that pass as one command, with the whole of `mcdonald run` behind each object:

    mcdonald batch PR113 PR149 --out DIR                  # these videos, one after another, on this computer
    mcdonald batch --list videos.txt --out DIR --pool 4   # a list, four videos side by side
    mcdonald batch --catalog --out DIR --slurm            # every video of the catalog, as a scheduler's job arrays
    mcdonald batch --catalog --out DIR --slurm --card 8   # ... or as one job given the graphics card, 8 videos at a time
    mcdonald batch --out DIR --status                     # what is done, running, failed and why; nothing is run
    mcdonald batch --out DIR                              # go on with what DIR's plan still has to do

**The unit is one video** (or one named segment of one). A video owns its frames from the moment they are extracted to
the moment they are removed, so the disk a batch holds at once is bounded by the videos running at once; a window of a
video cannot be a unit, because overlapping windows that extract at once leave gaps (the sweep's trap), and an object
cannot, because the objects are not known until every window's proposals are merged. One unit, in order (`_unit`):

1. **The picture.** A file with no picture, or whose picture is the same at every instant looked at (`picture`: a
   sound recording released as a video), is an answer by itself, and nothing more is done with it.
2. **The frames**, whole and once, into a folder of the unit's own.
3. **Find on every frame** (`propose.find`), a window of 400 frames at a time, each overlapping the next by 30.
4. **The objects** (`long_lived`, `merged`): what Find saw on 40 frames or more, the same object in two windows made
   one, the likeliest first; the first `most` are measured and the rest are listed.
5. **A case for each** (`several.place`, `several.run_each`): marks at Find's own seeds, recorded as taken by a rule
   with nobody looking, then `stages.run_case`, as `mcdonald run VIDEO --each DIR` does it. Every report is provisional.
6. **The index** (`several.index`), **the audit's draw** for each object and **samples of what the rules refused** (E8).
7. **The case file** (`share.make`), which `mcdonald share rerun` measures again to its numbers.
8. **The rows** of the corpus table.

**Resumable.** `DIR/batch_plan.json` lists the units; each unit's folder holds `batch_state.json` and, while it runs,
a lock whose time is kept fresh (`Lock`, `Watch`). A unit that is done is never done twice. One that died half way is
taken up again from the windows and objects it finished, each of which is a file written under another name and
renamed; an object half measured is removed and measured again. A unit's state records the package's version and the
options that decide its results (`make_of`); one finished by another version or with other options is left as it is,
and `--status`, every row of the table and `batch.md` say so. `--again` does units again, their old folders moved aside.

**One command runs a unit whatever starts it**: `mcdonald batch --out DIR --unit K`. A pool here (`--pool N`) starts N
of those at a time, each with its share of the CPUs (MCDONALD_CPUS), so that the stages' own pools ask for no more.
`--slurm` writes `DIR/batch.sbatch` and submits it as job arrays, one a size class (`classes`), with no partition or
account in it: those, and anything else, go through `--sbatch`. `--slurm --card N` submits instead one job given the
graphics card (`--gres=gpu:1`), which runs the videos N side by side (`run_pool`, `card_job`): an array's tasks given
the one card would each hold it, and run one after another. The N processes share the card, each planning its batches
on it within its part of the card's memory (`gpu.part`), and each video's state says what computed it.

No interface in it, as `several` has none: `main` is the command line and nothing else.
"""
import argparse
import bisect
import hashlib
import json
import math
import os
import random
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from . import __version__, several, storage
from . import catalog as _catalog
from . import forensics as vf
from .clip import EXIT_USAGE
from .progress import default_workers
from .report import Case, emit, envelope, said_to_stderr

FORMAT = "mcdonald-batch/1"
PLAN, STATE, LOCK = "batch_plan.json", "batch_state.json", "batch.lock"
FIND = "find"                  # in a unit's folder: Find's proposals, a window a file
TABLE = "batch"                # DIR/batch.tsv, .json, .md

# How a video is cut for Find, and which of Find's proposals are objects: the beat sweep's numbers (tools/sweep/, the
# whole-video pass of 2026-10-12/14 over 126 videos). They have that record and no null: where they came from is
# judgement, written down as such in docs/method.md section 54.
WINDOW, OVERLAP = 400, 30      # frames a window, and how many it shares with the next
KEEP = 30                      # proposals kept a window (`look --propose --more`)
SEEN = 40                      # frames a proposal must be seen on
ROUND = 0.3                    # the share of them it must stand against the background all round
SHARE = 5                      # frames two proposals must share to be one object
APART = 15.0                   # px: and their median distance on those frames under this
MOST = 12                      # objects measured a video, the likeliest first; the rest are listed
QUICK = ("layers", "integrity")     # --quick: the two long stages left out (neither enters the label with no scale given)

# A picture that does not change: at every instant looked at, no part of it differs from the first instant by as much
# as STILL grey levels, the difference smoothed as Find smooths its residual (STILL_SIGMA). STILL is Find's own floor,
# the least a residual's peak must reach to be a candidate (`propose.peaks`: floor 4.0, sigma 2.0), so such a picture
# holds nothing Find could propose at those moments. Not a level of the batch's own; tests/test_batch.py holds the
# two together. It is a guard against a picture that truly never changes, and a strict one: of the 144 PURSUE videos
# none lies under it (the one sound recording on a single card differs by 5.8 at some point; method section 54).
STILL, STILL_SIGMA = 4.0, 2.0
STILL_EVERY, STILL_LEAST, STILL_MOST = 10.0, 40, 600      # an instant every 10 s, at least 40 and at most 600 of them

AUDIT = 59                     # frames drawn for a person to check: 0.95 ** 59 < 0.05
REFUSED = 5                    # proposals sampled of each kind the rules refused
STALE = 600.0                  # s: a running unit's lock older than this was killed, and is taken over
BEAT = 30.0                    # s: how often a running unit says it is alive
SHEET = "_all_frames"          # a track sheet's pages, the first pictures left out of a case file too large to send


class Killed(KeyboardInterrupt):
    """The process was told to end (SIGTERM, a scheduler's time limit) while a unit ran."""


# ---- small files, written whole or not at all ------------------------------------------------------------------
def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path, data):
    """`data` as JSON at `path`, by way of another name: a reader never meets half a file."""
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.part")
    tmp.write_text(json.dumps(data, indent=1, default=_plain), encoding="utf-8")
    os.replace(tmp, path)
    return path


def write_text(path, text):
    path = Path(path)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.part")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    return path


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _plain(v):
    return v.tolist() if hasattr(v, "tolist") else str(v)


# ---- the windows and the objects (the beat sweep's `windows.py` and `collect.py`) ---------------------------------
def cut(frames, window=WINDOW, overlap=OVERLAP):
    """[(n0, n1)]: windows of `window` frames, `window - overlap` apart, the last ending on the last frame. An object
    that crosses a cut is whole in one window where it is in view no longer than the overlap."""
    step = window - overlap
    out = [(a, min(a + window - 1, frames)) for a in range(1, max(2, frames - overlap), step)]
    if out and out[-1][1] < frames:
        out.append((max(1, frames - window + 1), frames))
    return out


def refusals(p, seen=SEEN, round_=ROUND):
    """Why a proposal of Find's is not an object of the batch: [] where it is one; else each rule it fails, of "brief"
    (seen on fewer than SEEN frames), "edge" (background all round it on less than ROUND of them: an edge or a line
    more than a spot) and "tape" (one of a row of marks that slide together). `seen` and `round_` are the rule's two
    numbers, given otherwise only to ask what another setting would take (`plant.recovered_batch`); a batch runs with
    SEEN and ROUND."""
    why = []
    if p["seen_in"] < seen:
        why.append("brief")
    if p["background_all_round"] < round_:
        why.append("edge")
    if p["scrolling_tape"]:
        why.append("tape")
    if p["strength"] not in ("strong", "fair", "weak"):
        why.append("unrated")
    return why


def long_lived(windows, seen=SEEN, round_=ROUND):
    """The proposals of a video's windows that are objects, seen longest first, and the rest with why not.

    `windows` is {window's name: [proposal as `Proposal.to_dict` gives it, with its `rank`]}. Returns (kept, refused):
    kept as [{tag, rank, dark, seen, a, b, t, strength, bg, score, size, marks, says}] -- the sweep's fields, and what
    the batch needs to mark and order them -- and refused as [{tag, rank, why, seen, a, b, dark, size, t}]. `seen` and
    `round_` are `refusals`'."""
    kept, refused = [], []
    for tag in sorted(windows):
        for p in windows[tag]:
            t = {int(k): tuple(v) for k, v in p["track"].items()}
            row = dict(tag=tag, rank=p["rank"], dark=bool(p["dark"]), seen=p["seen_in"], a=min(t), b=max(t), t=t,
                       strength=p["strength"], bg=p["against_background_px_per_frame"], score=p.get("score", 0.0),
                       size=p.get("size_px"), marks={int(k): tuple(v) for k, v in (p.get("mark_at") or {}).items()},
                       says=p.get("says", ""))
            why = refusals(p, seen, round_)
            if why:
                refused.append(dict(row, why=why))
            else:
                kept.append(row)
    kept.sort(key=lambda p: -p["seen"])
    return kept, refused


def merged(props):
    """Kept proposals as objects: one seen in two windows is one, its track the union, in order of first frame. Two are
    one where they share SHARE frames or more, have one polarity, and lie under APART px apart (the median over the
    frames they share); the one seen longest leads, and gives the object its strength."""
    objs = []
    for p in props:
        for o in objs:
            com = set(p["t"]) & set(o["t"])
            if (len(com) >= SHARE and p["dark"] == o["dark"]
                    and np.median([np.hypot(p["t"][k][0] - o["t"][k][0], p["t"][k][1] - o["t"][k][1]) for k in com]) < APART):
                o["t"].update(p["t"])
                o["src"].append((p["tag"], p["rank"]))
                o["a"], o["b"] = min(o["a"], p["a"]), max(o["b"], p["b"])
                o["score"] = max(o.get("score", 0.0), p.get("score", 0.0))
                for k, v in (p.get("marks") or {}).items():
                    o["marks"].setdefault(k, v)
                break
        else:
            objs.append(dict(p, src=[(p["tag"], p["rank"])], t=dict(p["t"]), marks=dict(p.get("marks") or {})))
    objs.sort(key=lambda o: o["a"])
    return objs


def ordered(objs):
    """The objects in the order they are measured: Find's own score, the best an object had in any window, highest
    first; of two alike, the one seen on more frames, then the earlier."""
    return sorted(objs, key=lambda o: (-float(o.get("score") or 0.0), -len(o["t"]), o["a"]))


# ---- which videos: a list, the catalog, the plan -----------------------------------------------------------------
def read_list(path):
    """A list file's videos: [(what names the video, first frame or None, last frame or None)].

    One video a line: a path, a record id (`PR113`, `06:PR001`) or a release's file name, then, if only part of it is
    wanted, its first and last frame (`PR113 400 420`, or `PR113 400-420`). `#` starts a comment. A first line that
    names its columns (as `tools/sweep/videos.tsv` does: `id release file ...`) is read by those names: the video is
    `video`, else `file`, else `release:id`; `n0` and `n1` the frames."""
    lines = [ln.split("#", 1)[0].rstrip() for ln in Path(path).read_text(encoding="utf-8").splitlines()]
    lines = [ln for ln in lines if ln.strip()]
    if not lines:
        return []
    split = (lambda ln: ln.split("\t")) if any("\t" in ln for ln in lines) else (lambda ln: ln.split())
    head = [h.strip().lower() for h in split(lines[0])]
    out = []
    if {"video", "file", "id"} & set(head):
        for ln in lines[1:]:
            r = dict(zip(head, (c.strip() for c in split(ln))))
            name = r.get("video") or r.get("file") or (f"{r['release']}:{r['id']}" if r.get("release") else r.get("id"))
            if name:
                out.append((name, int(r["n0"]) if r.get("n0") else None, int(r["n1"]) if r.get("n1") else None))
        return out
    for ln in lines:
        parts = [c.strip() for c in split(ln) if c.strip()]
        n0 = n1 = None
        if len(parts) >= 2:
            m = re.fullmatch(r"(\d+)\s*[-–]\s*(\d+)", parts[-1])
            if m:
                n0, n1, parts = int(m.group(1)), int(m.group(2)), parts[:-1]
            elif len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
                n0, n1, parts = int(parts[-2]), int(parts[-1]), parts[:-2]
        out.append((" ".join(parts), n0, n1))
    return out


def places(also=()):
    """Where a video's file is looked for before the catalog is asked to download it: the folders the caller names,
    the reference-data folder ($MCDONALD_DATA's pursue/ and footage/) and the storage folder (`rerun.places`)."""
    from . import rerun
    return rerun.places(also=also)


def locate(name, also=(), fetch=True):
    """(path, tag, record) of the video `name` names: a file's path; else a file of that name in `places`; else the
    catalog's video with that file name or record id, looked for in `places` under its own file name and only then
    fetched as `forensics.resolve` fetches one (`fetch` False: not fetched, its path where it would be)."""
    p = Path(name).expanduser()
    if p.exists() and not p.is_dir():
        return vf.resolve(str(p))
    cat = _catalog.active()
    rec = next((r for r in cat.videos() if Path(r.get("path", "")).name == name), None)
    if rec is None:
        release, _, key = name.rpartition(":")
        hits = cat.by_id(key, release.zfill(2) if release else None)
        if len(hits) > 1:
            raise vf.Stop(f"{name}: {len(hits)} videos in the {cat.label} catalog have that name; say which one as "
                          "RELEASE:NAME, such as 06:PR001, or by its file's name")
        rec = hits[0] if hits else None
    file = Path(rec["path"]).name if rec else Path(name).name
    for d in places(also):
        q = Path(d) / file
        if q.is_file():
            return vf.resolve(str(q))
    if rec is None:
        raise vf.Stop(f"{name}: no such file, and no video with that name in the {cat.label} catalog.")
    path = Path(rec["path"])
    if not path.exists():
        if not fetch:
            return path, (rec.get("id") or path.stem).lower(), rec
        if not rec.get("url"):
            raise vf.Stop(f"{name} is not on this computer, and its record says nowhere to fetch it from")
        try:
            storage.download_on_terminal(rec, path)
        except OSError as ex:
            raise vf.Stop(f"{name} is not on this computer, and could not be downloaded from {rec['url']}: {ex}")
    return vf.resolve(str(path))


def unit_of(name, n0=None, n1=None, also=(), fetch=True):
    """One unit of a plan, as a dict: the video's path here, what the release calls it, its size and frames, the
    segment (None, None: the whole video) and the key it is known by when the plan is read again."""
    path, tag, rec = locate(name, also, fetch)
    path = Path(path)
    u = dict(video=str(path), file=path.name, tag=tag, id=(rec.get("title") or "").split(",")[0].strip() if rec else path.stem,
             release=str(rec.get("release") or "") if rec else "", disclosure=_catalog.active().disclosure(rec) if rec else None,
             bytes=None, frames=None, width=None, height=None, fps=None, duration=None, picture=True, n0=None, n1=None)
    if path.is_file():
        u["bytes"] = path.stat().st_size
        try:
            info = vf.probe(path)
            u.update(frames=int(info["frames"]), width=info["width"], height=info["height"], fps=str(info["fps"]),
                     duration=float(info["duration"] or 0))
        except vf.NotAVideo as e:                       # no picture in it: the unit says so, and is an answer
            u.update(picture=False, why=str(e))
    elif rec and rec.get("bytes"):
        u["bytes"] = int(rec["bytes"])
    if n0 is not None or n1 is not None:
        a, b = max(1, int(n0 or 1)), int(n1) if n1 is not None else u["frames"]
        if u["frames"]:
            b = min(b, u["frames"])
        if b is not None and a > b:
            raise vf.Stop(f"{name}: frames {n0}-{n1} are not a part of it ({u['frames']} frames)")
        if not (u["frames"] and (a, b) == (1, u["frames"])):
            u["n0"], u["n1"] = a, b
    u["key"] = f"{u['file']}|{u['bytes']}|{u['n0'] or ''}-{u['n1'] or ''}"
    return u


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")


def _name_units(units):
    """Each unit's folder under the batch's: the video's tag (`pr113`), as everywhere in the package; the release's own
    name for it (`nasa-uap-d024`, `fbi-uap-pr001`) where it has no record id of its own or two videos of the plan share
    one (PR001 is the FBI's and a police force's); else its file's. A segment's is its own folder inside
    (`segments.name`)."""
    from . import segments
    by_tag = {}
    for u in units:
        by_tag.setdefault(u["tag"], set()).add(u["file"])
    taken = {}
    for u in units:
        if "name" not in u:
            stem = Path(u["file"]).stem.lower()
            name = u["tag"]
            if len(by_tag[u["tag"]]) > 1 or u["tag"] == stem:
                name = _slug(u["id"]) or _slug(stem) or u["tag"]
            if taken.get(name, u["file"]) != u["file"]:
                name = f"{name}-{_slug(stem)}"
            u["name"] = name
        taken[u["name"]] = u["file"]
        u["folder"] = u["name"] if u["n0"] is None else f"{u['name']}/{segments.name(u['n0'], u['n1'])}"
    return units


def options_of(args):
    """The options a plan keeps, from the command's: those that decide results (`make_of`) and those that do not."""
    skip = sorted(set(x for x in (args.skip or "").split(",") if x) | (set(QUICK) if args.quick else set()))
    return dict(window=int(args.window), overlap=int(args.overlap), most=int(args.most), keep=int(getattr(args, "keep", KEEP) or KEEP), skip=skip,
                only=sorted(x for x in (args.only or "").split(",") if x), audit=int(args.audit_frames),
                keep_frames=bool(args.keep_frames), video_dir=[str(Path(d).resolve()) for d in args.video_dir or ()],
                note=str(getattr(args, "note", "") or ""))


def make_of(options):
    """What decides a unit's results: the package's version, the options that reach the measuring, and the rules' own
    numbers. Two units of one make can share a table without a word; two of different makes cannot."""
    return dict(mcdonald=__version__, window=options["window"], overlap=options["overlap"], most=options["most"],
                skip=list(options.get("skip") or []), only=list(options.get("only") or []), audit=options.get("audit", AUDIT),
                rule=dict(keep=options.get("keep", KEEP), seen=SEEN, round=ROUND, share=SHARE, apart=APART, still=STILL))


def make_id(make):
    """A make in eight letters, for a table's column."""
    return hashlib.sha256(json.dumps(make, sort_keys=True).encode()).hexdigest()[:8] if make else ""


def read_plan(out):
    plan = read_json(Path(out) / PLAN)
    if not plan or not str(plan.get("format", "")).startswith("mcdonald-batch/"):
        raise vf.Stop(f"{out} holds no batch: give the videos (some, --list FILE or --catalog) with --out {out} to plan one")
    return plan


def plan(out, names, options=None, fetch=True, say=print):
    """Write (or add to) the plan in `out` and return it. `names` is [(video, n0, n1)]; a video the plan already has,
    by its file's name and size and its segment, keeps its number and folder, and new ones are added after. `options`
    replace the plan's (each unit's state keeps the ones it was done with)."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    old = read_json(out / PLAN) or {}
    units = list(old.get("units") or [])
    known = {u["key"] for u in units}
    opts = dict(old.get("options") or {})
    opts.update(options or {})
    for name, n0, n1 in names:
        u = unit_of(name, n0, n1, also=opts.get("video_dir") or (), fetch=fetch)
        if u["key"] not in known:
            known.add(u["key"])
            units.append(u)
    _name_units(units)
    for k, u in enumerate(units):
        u["k"] = k
    p = dict(format=FORMAT, made=old.get("made") or _now(), planned=_now(), mcdonald=__version__, options=opts, units=units)
    write_json(out / PLAN, p)
    return p


# ---- a unit's state, and who has it -----------------------------------------------------------------------------
def read_state(folder):
    return read_json(Path(folder) / STATE) or {}


def write_state(folder, state):
    return write_json(Path(folder) / STATE, state)


def _alive(pid):
    """Is a process of this number running on this computer? None where that cannot be told."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return None
    if sys.platform == "win32":                           # os.kill would end it: ask the system instead
        try:
            import ctypes
            h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)        # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            code = ctypes.c_ulong()
            ok = ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
            ctypes.windll.kernel32.CloseHandle(h)
            return bool(ok) and code.value == 259                             # STILL_ACTIVE
        except Exception:                                 # noqa: BLE001
            return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None


class Lock:
    """One process a unit. The lock is a file made only if it is not there; whoever holds it keeps its time fresh
    (`Watch`). A lock is dead, and taken over, when its time is older than STALE, or when it was made on this computer
    by a process that is no longer running (a job the scheduler killed): it is renamed away first, which only one of
    two takers can do."""

    def __init__(self, folder):
        self.path = Path(folder) / LOCK
        self.held = False

    def age(self):
        try:
            return time.time() - self.path.stat().st_mtime
        except OSError:
            return None

    def dead(self):
        """Whether the lock that is there belongs to nobody any more."""
        age = self.age()
        if age is None or age >= STALE:
            return True
        who = read_json(self.path) or {}
        return who.get("host") == socket.gethostname() and _alive(who.get("pid")) is False

    def take(self):
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                if not self.dead():
                    return False
                aside = self.path.with_name(f"{LOCK}.stale.{os.getpid()}")
                try:                                     # away with it, if nobody else was quicker
                    os.replace(self.path, aside)
                    aside.unlink(missing_ok=True)
                except OSError:
                    pass
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(dict(host=socket.gethostname(), pid=os.getpid(), job=os.environ.get("SLURM_JOB_ID"), since=_now()), f)
            self.held = True
            return True
        return False

    def touch(self):
        if self.held:
            try:
                os.utime(self.path)
            except OSError:
                pass

    def release(self):
        if self.held:
            self.held = False
            self.path.unlink(missing_ok=True)


def _pss(pid):
    """A process's fair share of memory in bytes (its own pages, and its share of those it has in common with others:
    a pool's workers share what their fork server loaded), or None where the kernel does not say."""
    try:
        with open(f"/proc/{pid}/smaps_rollup", encoding="utf-8", errors="replace") as f:
            for ln in f:
                if ln.startswith("Pss:"):
                    return int(ln.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def _tree_rss():
    """The memory this process and every process it started hold now, in bytes: each one's fair share (`_pss`), else
    its resident set (Linux: /proc); None elsewhere."""
    try:
        page = os.sysconf("SC_PAGE_SIZE")
        kids, rss = {}, {}
        for d in os.listdir("/proc"):
            if not d.isdigit():
                continue
            try:
                with open(f"/proc/{d}/stat", encoding="utf-8", errors="replace") as f:
                    s = f.read()
                rest = s[s.rindex(")") + 2:].split()
                kids.setdefault(int(rest[1]), []).append(int(d))
                rss[int(d)] = int(rest[21]) * page
            except (OSError, ValueError, IndexError):
                continue
        total, todo = 0, [os.getpid()]
        while todo:
            p = todo.pop()
            total += _pss(p) or rss.get(p, 0)
            todo += kids.get(p, [])
        return total
    except (OSError, ValueError, AttributeError):
        return None


class Watch(threading.Thread):
    """While a unit runs: its lock kept fresh, and the most memory the unit's processes held at once (`peak`, bytes),
    sampled every few seconds. A thread, so that a step with nothing to say (ffmpeg on a long video) is still alive."""

    def __init__(self, lock, every=5.0):
        super().__init__(daemon=True, name="mcdonald-batch-watch")
        self.lock, self.every, self.peak, self._end = lock, every, 0, threading.Event()

    def run(self):
        last = 0.0
        while not self._end.wait(self.every):
            now = time.time()
            if now - last >= BEAT:
                self.lock.touch()
                last = now
            rss = _tree_rss()
            if rss:
                self.peak = max(self.peak, rss)

    def stop(self):
        self._end.set()


# ---- 1: the picture -----------------------------------------------------------------------------------------
def _grey_at(video, t, width, height):
    """The picture `t` seconds into the video, as grey levels (H x W float32), or None where ffmpeg gives none."""
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    if r.returncode != 0 or len(r.stdout) < width * height:
        return None
    return np.frombuffer(r.stdout[:width * height], np.uint8).reshape(height, width).astype(np.float32)


def picture(video, info=None, progress=None, stop=None, whole=False):
    """Does the video's picture change at all? {instants, every_s, change, changes, said}.

    The picture is read at instants spread evenly over the video -- one every STILL_EVERY seconds, at least
    STILL_LEAST and at most STILL_MOST of them, each a seek, so a video of an hour costs a minute -- and each is held
    against the first: their difference, smoothed as Find smooths a residual, at the point where it is largest.
    `change` is the largest of those, in grey levels, and `changes` whether it reaches STILL, the floor Find holds a
    candidate to. A sound recording released as a video (a caption card for six minutes) does not change, and there is
    nothing in it for Find; a small object crossing a still sky changes the picture where it is, however little of
    the picture that is. What this cannot see is a change shorter than the gap between two instants, which
    `every_s` says. The reading stops once the picture has plainly changed (ten times STILL) unless `whole`."""
    from scipy import ndimage
    info = info or vf.probe(video)
    W, H = info["width"], info["height"]                    # the frames as ffmpeg decodes them, turned upright
    dur = float(info.get("duration") or 0) or info["frames"] / float(info["fps"])
    n = int(min(STILL_MOST, max(STILL_LEAST, math.ceil(dur / STILL_EVERY))))
    n = max(2, min(n, int(info["frames"])))
    last = max(0.0, dur - 2.0 / float(info["fps"]))
    ts = [last * i / (n - 1) for i in range(n)]
    first, diffs = None, []
    for i, t in enumerate(ts):
        if stop is not None and stop():
            raise vf.Stopped("The picture")
        g = _grey_at(video, t, W, H)
        if progress:
            progress("The picture", i + 1, n)
        if g is None:
            continue
        if first is None:
            first = g
            continue
        diffs.append(float(np.abs(ndimage.gaussian_filter(g - first, STILL_SIGMA)).max()))
        if not whole and diffs[-1] >= 10 * STILL and len(diffs) >= 3:     # it changes, and by a wide margin: no need of the rest
            break
    if not diffs:
        return dict(instants=0, every_s=None, change=None, changes=True,
                    said="the picture could not be read at the moments looked at, so it was taken to change")
    change = max(diffs)
    every = dur / (n - 1) if n > 1 else None
    return dict(instants=len(diffs) + 1, every_s=round(every, 2) if every else None, change=round(change, 2), changes=change >= STILL,
                said=(f"the picture differs between moments by up to {change:.0f} grey levels at some point" if change >= STILL else
                      f"The picture is the same at {len(diffs) + 1} moments, one every {every:.2g} s. No part of it differs from "
                      f"the first by more than {change:.1f} grey levels, and Find needs {STILL:g} to see a spot. A change "
                      "shorter than the gap between two moments would be missed."))


# ---- 6: the audit (E8) -----------------------------------------------------------------------------------------
def leverage(frames):
    """Each frame's share of the weight an audit's draw gives it: half its leverage on a straight-line fit of position
    against time (the hat matrix's diagonal, 1/N + (t - mean)^2 / sum, which adds to 2). Half the weight is even over
    the frames and half grows toward the track's ends, which move a fitted rate most. Adds to 1."""
    t = np.asarray(sorted(frames), float)
    if len(t) < 2:
        return np.ones(len(t))
    d = (t - t.mean()) ** 2
    return (1.0 / len(t) + d / d.sum()) / 2.0


def audit_seed(file, object_name, frames):
    """The draw's seed: from the video's file name, the object's folder and its track's frames, so that the draw is
    nobody's choice and anyone can make it again."""
    text = f"{file}|{object_name}|{min(frames)}-{max(frames)}|{len(frames)}"
    return int(hashlib.sha256(text.encode()).hexdigest()[:12], 16)


def audit_draw(track, file, object_name, n=AUDIT):
    """The frames of a track for a person to check: {seed, draws, frames, whole, rule, drawn: [{k, frame, x, y,
    weight, times}]}.

    `n` draws with replacement, each frame's chance its `leverage`; the frames drawn are numbered in the order of the
    video, and `times` is how often each came up. A track of `n` frames or fewer is checked whole. If every draw is
    right, then with 95 % confidence the wrong frames hold under 1 - 0.05^(1/n) of the weight (4.9 % for 59): with
    even weights that is the share of frames that are wrong, and here it is the share of the answer that rests on
    them. Python's own generator (`random.Random`), whose `random()` is the same in every version."""
    frames = sorted(track)
    w = leverage(frames)
    seed = audit_seed(file, object_name, frames)
    whole = len(frames) <= n
    if whole:
        times = {f: 1 for f in frames}
    else:
        cum = np.cumsum(w)
        cum[-1] = 1.0
        rng, times = random.Random(seed), {}
        for _ in range(n):
            f = frames[min(bisect.bisect_left(cum, rng.random()), len(frames) - 1)]
            times[f] = times.get(f, 0) + 1
    wt = dict(zip(frames, (float(x) for x in w)))
    return dict(seed=seed, draws=len(frames) if whole else n, frames=len(frames), whole=whole,
                rule=("every frame of the track" if whole else
                      f"{n} draws with replacement, a frame's chance its leverage on a straight-line fit of position on time"),
                drawn=[dict(k=k, frame=f, x=round(track[f][0], 2), y=round(track[f][1], 2), weight=round(wt[f], 6), times=times[f])
                       for k, f in enumerate(sorted(times), 1)])


def upper_bound(wrong, draws, level=0.95):
    """The largest share consistent, at `level`, with `wrong` of `draws` independent draws being wrong: the exact
    one-sided binomial bound (Clopper and Pearson 1934), by bisection. For none wrong it is 1 - (1 - level)^(1/draws)."""
    if draws <= 0:
        return 1.0
    if wrong >= draws:
        return 1.0
    a = 1.0 - level
    tail = lambda p: sum(math.comb(draws, j) * p ** j * (1 - p) ** (draws - j) for j in range(0, wrong + 1))     # P(X <= wrong)
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if tail(mid) > a:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _frames_of(video, frames, clip=None):
    """{frame: H x W x 3 uint8} for a few frames of a video: from the frames on disk where `clip` has them, else by
    one pass of ffmpeg that keeps exactly these, by number (as `look.thumbnails` does)."""
    import tempfile
    from PIL import Image
    from .clip import every_frame
    if clip is not None and all(clip.path(n).exists() for n in frames):
        return {n: clip.rgb(n).astype(np.uint8) for n in frames}
    out = {}
    with tempfile.TemporaryDirectory(prefix="mcdonald-audit-") as td:
        sel = "+".join(f"eq(n,{n - 1})" for n in frames)
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(video), "-vf", f"select='{sel}'", *every_frame(),
                        "-frames:v", str(len(frames)), f"{td}/%05d.png"], check=True)
        for n, p in zip(frames, sorted(Path(td).glob("*.png"))):
            out[n] = np.asarray(Image.open(p).convert("RGB"))
    return out


def audit_sheet(video, drawn, out, size=9.0, clip=None, box=96, zoom=3, cols=10):
    """The audit's picture: each drawn frame's own pixels round the track's position, enlarged without interpolation,
    with a ring where the track says the object is, numbered as the draw numbers them. Returns `out`, or None where
    the frames could not be read."""
    from PIL import Image, ImageDraw
    from .figures import pil_font
    frames = [d["frame"] for d in drawn]
    try:
        pix = _frames_of(video, frames, clip)
    except (OSError, subprocess.CalledProcessError):
        return None
    drawn = [d for d in drawn if d["frame"] in pix]
    if not drawn:
        return None
    cols = min(cols, len(drawn))
    rows = (len(drawn) + cols - 1) // cols
    cell, bar, font = box * zoom, 22, pil_font(14)
    sheet = Image.new("RGB", (cols * cell, rows * (cell + bar)), "#111111")
    dr = ImageDraw.Draw(sheet)
    r = box // 2
    ring = max(1.6 * float(size or 9.0), 9.0) * zoom
    for i, d in enumerate(drawn):
        cx, cy = i % cols * cell, i // cols * (cell + bar)
        g = np.pad(pix[d["frame"]], ((r, r), (r, r), (0, 0)), mode="edge")
        xi, yi = int(round(d["x"])) + r, int(round(d["y"])) + r
        tile = Image.fromarray(g[yi - r:yi + r, xi - r:xi + r]).resize((cell, cell), Image.NEAREST)
        sheet.paste(tile, (cx, cy))
        px = cx + (d["x"] - (xi - 2 * r) + 0.5) * zoom - 0.5
        py = cy + (d["y"] - (yi - 2 * r) + 0.5) * zoom - 0.5
        dr.ellipse([px - ring, py - ring, px + ring, py + ring], outline=(53, 224, 200), width=1)
        dr.text((cx + 4, cy + cell + 3), f"{d['k']}   frame {d['frame']}" + (f"   x{d['times']}" if d["times"] > 1 else ""),
                fill="#f2f0e9", font=font)
    sheet.save(out)
    return out


def audit_object(thing, video, file, clip=None, n=AUDIT):
    """An object's audit, made where it is not there: `<tag>_audit.json` (the draw, and where the answer is recorded)
    and `<tag>_audit.png` (the sheet), in its folder. None where the object was not followed."""
    track_csv = Path(f"{thing.prefix}_autotrack.csv")
    js = Path(f"{thing.prefix}_audit.json")
    if js.exists():
        return read_json(js)
    if not track_csv.exists():
        return None
    try:
        track = vf.read_track(track_csv)
    except (OSError, ValueError, KeyError, StopIteration):
        return None
    if not track:
        return None
    a = audit_draw(track, file, thing.folder.name, n)
    size = None
    try:
        size = ((Case.load(thing.case_json).stages.get("track") or {}).get("fields") or {}).get("object_size_px") if thing.case_json else None
    except (OSError, ValueError, KeyError):
        pass
    sheet = audit_sheet(video, a["drawn"], f"{thing.prefix}_audit.png", size=size, clip=clip)
    a.update(made=_now(), mcdonald=__version__, object=thing.folder.name, track=track_csv.name,
             sheet=Path(sheet).name if sheet else None, looked=None)
    write_json(js, a)
    return a


def audit_said(a, sheet=None):
    """An audit in a sentence or two, for a person. `sheet` is how its picture is named in the sentence (a page gives a
    link); by default its file's name."""
    if not a:
        return "No audit: the object was not followed, so there is no track to check."
    what = (f"all {a['frames']} frames of its track" if a["whole"] else
            f"{len(a['drawn'])} frames of its track's {a['frames']}, from {a['draws']} draws at random")
    s = f"The audit drew {what}" + (f" ({sheet or a['sheet']})." if a.get("sheet") else " (the sheet could not be drawn).")
    L = a.get("looked")
    if not L:
        return s + " Nobody has recorded a look at it yet."
    who = f"{L['by']}" + (" (an AI agent)" if L.get("agent") else "")
    share = (f"The wrong frames hold {100 * L['bound']:.1f} % of the track's weight." if L.get("exact") else
             f"With 95 % confidence, the wrong frames hold under {100 * L['bound']:.1f} % of the track's weight.")
    if not L["wrong"]:
        return s + f" {who} looked and found the ring on the object in every one." + ("" if L.get("exact") else " " + share)
    return (s + f" {who} looked and found the ring off the object in {len(L['wrong'])} of them"
            + ("" if a["whole"] else f" ({L['wrong_draws']} of {a['draws']} draws)") + f". {share}")


def audit_record(folder, wrong, by="", agent=False):
    """Record what someone saw on an object's audit sheet: `wrong` the numbers (as the sheet numbers them) of the
    frames whose ring is not on the object, [] for none. Returns the audit, with the bound that follows."""
    js = next(iter(sorted(Path(folder).glob("*_audit.json"))), None)
    if js is None:
        raise vf.Stop(f"{folder}: no audit here (an object's folder holds <tag>_audit.json once `mcdonald batch` has measured it)")
    a = json.loads(js.read_text(encoding="utf-8"))
    ks = {d["k"]: d for d in a["drawn"]}
    bad = [k for k in wrong if k not in ks]
    if bad:
        raise vf.Stop(f"--wrong {','.join(map(str, bad))}: the sheet's frames are numbered 1 to {len(ks)}", EXIT_USAGE)
    wrong_draws = sum(ks[k]["times"] for k in wrong)
    if a["whole"]:                                        # every frame was looked at: the share is known, not bounded
        bound = sum(ks[k]["weight"] for k in wrong)
    else:
        bound = upper_bound(wrong_draws, a["draws"])
    a["looked"] = dict(by=by or "someone", agent=bool(agent), when=_now(), wrong=sorted(wrong), wrong_draws=wrong_draws,
                       bound=round(float(bound), 4), exact=bool(a["whole"]))
    write_json(js, a)
    return a


def refused_sheet(clip, refused, listed, out, seed, per=REFUSED):
    """Samples of what the rules refused, for a person to look at: up to `per` proposals, drawn at random, of each
    kind -- seen too briefly, an edge or a line more than a spot, a scrolling tape, and the objects past the cap --
    each as a strip of the video's own pixels along it (`propose.strip`). Returns (the picture or None, the samples)."""
    from PIL import Image, ImageDraw
    from . import propose
    from .figures import pil_font
    kinds = [("brief", f"seen on fewer than {SEEN} frames"), ("edge", "an edge or a line more than a spot"),
             ("tape", "one of a row of marks that slide together"), ("cap", "past the cap: listed, not measured")]
    pools = {k: [p for p in refused if k in p["why"]] for k, _ in kinds[:3]}
    pools["cap"] = list(listed)
    rng, rows, samples = random.Random(seed), [], []
    for kind, words in kinds:
        pool = sorted(pools[kind], key=lambda p: (p.get("tag", ""), p.get("rank", 0), p["a"]))
        for p in (rng.sample(pool, per) if len(pool) > per else pool):
            t = {n: xy for n, xy in p["t"].items() if clip.n0 <= n <= clip.n1 and clip.path(n).exists()}
            if not t:
                continue
            prop = SimpleNamespace(track=t, frames=sorted(t), size_px=float(p.get("size") or 9.0))
            try:
                pix, shown = propose.strip(clip, prop)
            except (OSError, ValueError, IndexError):
                continue
            where = (f"window {p['tag']} row {p['rank']}" if "src" not in p else
                     "windows " + ", ".join(f"{a}:{b}" for a, b in p["src"]))
            rows.append((f"refused: {words} ({len(pools[kind])} in all)   {where}   {'dark' if p['dark'] else 'bright'}, "
                         f"seen on {p['seen']} frames, {p['a']}–{p['b']}", shown, pix))
            samples.append(dict(kind=kind, window=p.get("tag"), rank=p.get("rank"), first=p["a"], last=p["b"], seen=p["seen"]))
    if not rows:
        return None, samples
    font = pil_font(15)
    w = max(r[2].shape[1] for r in rows)
    sheet = Image.new("RGB", (w, sum(r[2].shape[0] + 44 for r in rows)), "#111111")
    dr, y = ImageDraw.Draw(sheet), 0
    for text, shown, pix in rows:
        dr.text((6, y + 3), text[:int(w / 7.4)], fill="#f2f0e9", font=font)
        dr.text((6, y + 23), "frames " + ", ".join(map(str, shown)), fill="#35e0c8", font=font)
        sheet.paste(Image.fromarray(pix), (0, y + 44))
        y += pix.shape[0] + 44
    sheet.save(out)
    return out, samples


# ---- one unit ---------------------------------------------------------------------------------------------------
HOW = ("agent: spot {rank} of {of} that Find proposed in frames {a}–{b} ({says}); seen on {seen} frames in {n} window{s}, "
       "frames {first}–{last}; taken by `mcdonald batch`, whose rule takes every spot seen on {least} frames or more, "
       "with nobody looking: check the track sheet in its report")
NOTE = ("Made by `mcdonald batch` with nobody looking. Find searched every frame of {what}. Each spot it saw on {least} "
        "frames or more was followed and measured as an object, the most likely first{cap}. Nobody chose the objects and "
        "nobody has looked at a track sheet, so every report here is provisional.")


def frames_dir(out, u):
    """Where a unit keeps its frames: a folder of its own in the storage folder's frames, named for the video, the
    batch (eight letters from its folder's path) and the unit. Two units never share frames, nor remove each other's:
    not two parts of one video, and not the same video in two batches that share a storage folder (the pilot of
    2026-11-13: one batch's unit finished and removed the frames under another's, whose integrity step then failed)."""
    batch = hashlib.sha256(os.path.realpath(out).encode()).hexdigest()[:8]
    return storage.frames() / f"{Path(u['file']).stem}.batch-{batch}-{u['folder'].replace('/', '-')}"


def _wipe(folder, tag):
    """A unit's products removed, for a clean start: what another make left unfinished."""
    folder = Path(folder)
    for d in list(folder.glob("object-*")) + [folder / FIND]:
        shutil.rmtree(d, ignore_errors=True)
    for f in list(folder.glob(f"{tag}_*")):
        if f.is_file():
            f.unlink(missing_ok=True)


def _clock(seconds, step):
    """A context that adds the time it took to `seconds[step]`."""
    class T:
        def __enter__(self):
            self.t = time.time()

        def __exit__(self, *exc):
            seconds[step] = round(seconds.get(step, 0.0) + time.time() - self.t, 1)
            return False
    return T()


def _unit(out, u, opt, folder, state, say, progress, stop):
    """The steps of one unit (the module's docstring), each skipped where its product is there. Fills `state` as it
    goes and returns the unit's record (what `<tag>_batch.json` holds)."""
    from . import propose
    tag, video = u["tag"], Path(u["video"])
    secs = state["seconds"]
    info_path = folder / f"{tag}_batch.json"
    rec = read_json(info_path) or {}
    rec = rec if rec.get("make") == state["make"] else {}
    rec.update(format=FORMAT, make=state["make"], unit=u["name"], video=dict(file=u["file"], bytes=u["bytes"], id=u["id"],
                                                                             release=u["release"], disclosure=u.get("disclosure")))

    def step(name):
        state["step"] = name
        write_state(folder, state)
        say(f"== {u['name']}: {name}")

    def at(place):
        return None if progress is None else (lambda text, done=None, total=None: progress(f"{place} · {text}", done, total))

    if not video.is_file():                                # planned from the catalog, not yet on this computer
        step("fetching the video")
        video = Path(locate(u["video"] if Path(u["video"]).exists() else u["file"], opt.get("video_dir") or ())[0])
    # 1 the picture
    step("the picture")
    try:
        info = vf.probe(video)
    except vf.NotAVideo as e:
        rec.update(picture=dict(changes=None, said=str(e)), outcome="no picture", objects=[], windows=[])
        write_json(info_path, rec)
        return rec
    if "picture" not in rec:
        with _clock(secs, "picture"):
            rec["picture"] = picture(video, info, at("the picture"), stop)
        write_json(info_path, rec)
    if not rec["picture"]["changes"]:
        rec.update(outcome="still picture", objects=[], windows=[])
        write_json(info_path, rec)
        return rec

    # 2 the frames, whole and once -- only where a later step still needs them
    wd = frames_dir(out, u)
    whole = vf.Clip(video, wd, u["n0"], u["n1"], extract=False)
    need = (not rec.get("windows") or any(not (folder / FIND / f"{w[0]}.json").exists() for w in rec["windows"])
            or not rec.get("measured") or not rec.get("audited"))
    if need and not whole.extracted():
        step(f"frames {whole.n0}-{whole.n1}")
        say("  " + vf.cost_text(whole.cost()))
        with _clock(secs, "frames"):
            if whole.extract(stop=stop) is False:
                raise vf.Stopped("frames")
        whole = vf.Clip(video, wd, u["n0"], u["n1"], extract=False)       # its end, where the count was a frame long
        try:                                                 # what the frames take on disk while the unit runs
            state["frames_mb"] = rec["frames_mb"] = round(sum(e.stat().st_size for e in os.scandir(wd) if e.is_file()) / 2 ** 20)
        except OSError:
            pass
    if whole.extracted() or "frames" not in rec:
        rec["frames"] = [whole.n0, whole.n1]
    rec["size"] = [whole.W, whole.H]
    rec["fps"] = str(whole.info["fps"])
    first, last = rec["frames"]

    # 3 Find on every frame, a window at a time
    if not rec.get("windows"):
        rec["windows"] = [[f"w{k:02d}", a + first - 1, b + first - 1]
                          for k, (a, b) in enumerate(cut(last - first + 1, opt["window"], opt["overlap"]))]
        write_json(info_path, rec)
    (folder / FIND).mkdir(exist_ok=True)
    for i, (wtag, a, b) in enumerate(rec["windows"], 1):
        f = folder / FIND / f"{wtag}.json"
        if f.exists():
            continue
        step(f"Find, window {i} of {len(rec['windows'])} (frames {a}-{b})")
        with _clock(secs, "find"):
            p = at(f"window {i} of {len(rec['windows'])}")
            try:
                clip = vf.Clip(video, wd, a, b)
                props = propose.find(clip, vf.static_masks(clip, progress=p), progress=p, stop=stop, keep=opt.get("keep", KEEP))
                write_json(f, dict(window=wtag, n0=a, n1=b, proposals=[dict(q.to_dict(), rank=r) for r, q in enumerate(props, 1)]))
            except vf.Stopped:
                raise
            except Exception as e:                           # noqa: BLE001 -- one window's trouble is said, and the rest searched
                say(f"  ! Find failed on frames {a}-{b}: {type(e).__name__}: {e}")
                write_json(f, dict(window=wtag, n0=a, n1=b, proposals=[], error=f"{type(e).__name__}: {e}"))

    # 4 the objects
    read = {w[0]: read_json(folder / FIND / f"{w[0]}.json") or {} for w in rec["windows"]}
    windows = {k: v.get("proposals", []) for k, v in read.items()}
    rec["find_failed"] = [dict(window=k, error=v["error"]) for k, v in read.items() if v.get("error")]
    kept, refused = long_lived(windows)
    objs = ordered(merged(kept))
    taken, listed = objs[:opt["most"]], objs[opt["most"]:]
    counts = {k: sum(k in p["why"] for p in refused) for k in ("brief", "edge", "tape")}
    counts["brief_spots"] = sum(p["why"] == ["brief"] for p in refused)     # spots in all but how long they were seen: a short transit is one
    counts["brief_longest"] = max((p["seen"] for p in refused if p["why"] == ["brief"]), default=0)
    rec.update(proposals=sum(len(v) for v in windows.values()), kept=len(kept), refused=counts, found=len(objs),
               objects=[dict(object=k if k <= len(taken) else None, first=o["a"], last=o["b"], dark=o["dark"], strength=o["strength"],
                             score=round(float(o.get("score") or 0), 2), seen=len(o["t"]), size_px=o.get("size"),
                             windows=[f"{a}:{b}" for a, b in o["src"]], marks=len(o["marks"]),
                             why_not=None if k <= len(taken) else f"past the cap of {opt['most']}")
                        for k, o in enumerate(objs, 1)])
    write_json(info_path, rec)
    say(f"  {rec['proposals']} proposals in {len(windows)} window{'s' if len(windows) != 1 else ''}; {len(objs)} object"
        f"{'s' if len(objs) != 1 else ''} seen on {SEEN} frames or more"
        + (f"; the first {len(taken)} are measured, {len(listed)} listed" if listed else ""))

    # 5 a case for each: marks at Find's seeds, then the queue `run --each` is
    things = []
    if taken and not rec.get("measured"):
        found = {t.k: t for t in several.things(folder)}
        lookup = {(p["tag"], p["rank"]): p for p in kept}
        for k, o in enumerate(taken, 1):
            d = folder / f"object-{k}"
            if k in found and several.measured(found[k]):
                continue
            shutil.rmtree(d, ignore_errors=True)               # half made, or half measured: again from its marks
            lead = lookup[tuple(o["src"][0])]
            wa, wb = next((w[1], w[2]) for w in rec["windows"] if w[0] == lead["tag"])
            how = HOW.format(rank=lead["rank"], of=len(windows[lead["tag"]]), a=wa, b=wb, says=lead["says"], seen=len(o["t"]),
                             n=len(o["src"]), s="" if len(o["src"]) == 1 else "s", first=o["a"], last=o["b"], least=SEEN)
            several.place(whole, tag, folder, o["marks"], how, k=k, video=whole.video, seen=(o["a"], o["b"]))
        for d in folder.glob("object-*"):                      # a folder past the ones taken is of another plan: not this unit's
            m = several.NAME.match(d.name)
            if m and int(m.group(1)) > len(taken):
                shutil.rmtree(d, ignore_errors=True)
        step(f"measuring {len(taken)} object{'s' if len(taken) != 1 else ''}")
        cur = {}                                             # the object being measured: its number, when it began, its stage

        def close():
            if cur.get("stage"):
                st = state["objects"][str(cur["k"])]["stages"]
                st[cur["stage"]] = round(st.get(cur["stage"], 0.0) + time.time() - cur["since"], 1)

        def told(t):
            o = state["objects"].setdefault(str(t.k), dict(seconds=0.0, stages={}))
            if t.state == "measuring":
                cur.update(k=t.k, t0=time.time(), stage=None, since=time.time())
                o.update(seconds=0.0, stages={})
                state["step"] = f"measuring object {t.k} of {len(taken)}"
                write_state(folder, state)
            else:
                if cur.get("k") == t.k:
                    close()
                    o["seconds"] = round(time.time() - cur["t0"], 1)
                    cur.clear()
                o["state"], o["error"] = t.state, t.error

        def started(name):
            if cur and cur.get("stage") != name:
                close()
                cur.update(stage=name, since=time.time())

        with _clock(secs, "measure"):
            things = several.run_each(str(video), folder, workdir=str(wd), n0=whole.n0, n1=whole.n1, clip=whole,
                                      say=lambda line: say(f"  {line}"), progress=progress, stop=stop, told=told,
                                      skip=list(opt.get("skip") or []) or None, only=list(opt.get("only") or []) or None,
                                      started=started)
        if stop is not None and stop():
            raise vf.Stopped("measuring")
        rec["measured"] = True
        write_json(info_path, rec)
    elif not taken:
        rec["measured"] = True
    things = several.things(folder)

    # 6 the audit's draw for each object, samples of what the rules refused, and the index, which says both
    if not rec.get("audited"):
        step("the audit's draws")
        with _clock(secs, "audit"):
            try:
                for t in things:
                    audit_object(t, video, u["file"], clip=whole, n=opt.get("audit", AUDIT))
                if refused or listed:
                    sheet, samples = refused_sheet(whole, refused, listed, str(folder / f"{tag}_refused.png"),
                                                   audit_seed(u["file"], "refused", [first, last]))
                    rec["refused_sheet"], rec["refused_samples"] = (Path(sheet).name if sheet else None), samples
            except Exception as e:                           # noqa: BLE001 -- a picture that cannot be drawn is said, not fatal
                rec["audit_error"] = f"{type(e).__name__}: {e}"
                say(f"  ! the audit's pictures were not all drawn: {rec['audit_error']}")
        rec["audited"] = True
        write_json(info_path, rec)
    if things:
        several.index(folder)

    # 7 the case file
    rec["outcome"] = "measured" if things else "listed" if objs else "nothing found"
    if things:
        step("the case file")
        with _clock(secs, "share"):
            try:
                rec["case_file"] = case_file(folder, video, u, opt, (first, last), len(listed))
            except Exception as e:                           # noqa: BLE001 -- the measurements stand without it, and the row says so
                rec["case_file"] = dict(file=None, error=f"{type(e).__name__}: {e}")
            if rec["case_file"].get("error"):
                say(f"  ! the case file was not made: {rec['case_file']['error']}")
    write_json(info_path, rec)
    return rec


def case_file(folder, video, u, opt, frames, listed=0):
    """A unit's results as one file to send (`share.make`): {file, bytes, left_out}. A video's folder can be larger
    than a shared file may be (a track sheet's pages for twelve long tracks): the pictures are then left out, the
    track sheets' pages first, and the file says so. It still measures again to its numbers, which need the marks and
    the reports and no picture."""
    from . import share
    tag = u["tag"]
    out = folder / f"{tag}_batch.mcdonald"
    what = "the video" if u["n0"] is None else f"frames {frames[0]} to {frames[1]} of the video"
    cap = f". The first {opt['most']} were measured and {listed} more are listed" if listed else ""
    note = NOTE.format(what=what, least=SEEN, cap=cap)
    part = tuple(frames) if u["n0"] is not None else None
    left = []
    for leave in ((), (f"*{SHEET}*.jpg",), ("*.jpg", "*.png", "*.pdf")):
        try:
            said = note + (" Left out to keep the file small enough to send: " + ("the track sheets' pages" if len(leave) == 1 else
                           "every picture") + ". `mcdonald share rerun` draws them again." if leave else "")
            share.make(out, video, folder=folder, part=part, note=said, by="mcdonald batch", agent=True, leave_out=leave)
            left = list(leave)
            break
        except share.ShareError as e:
            err = str(e)
    else:
        return dict(file=None, error=err)
    return dict(file=out.name, bytes=out.stat().st_size, left_out=left)


def _computes(state, say):
    """What computes this unit, said in its log and kept in its state: the graphics card this process has (`gpu.said`:
    its name, and where several processes share it, the part of its memory this one plans within), or None and why
    not. Returns the card."""
    from . import gpu
    try:
        line = gpu.said()
        c = gpu.card()
        why = None if c is not None else gpu.why()
    except Exception as e:                                   # noqa: BLE001 -- the unit is measured all the same, on the CPU
        line, c, why = f"graphics card: not asked ({type(e).__name__}: {e})", None, f"{type(e).__name__}: {e}"
    state["card"] = f"{c.name} ({c.library})" if c is not None else None
    state["card_shared"] = c.shared if c is not None and c.part else None
    state["card_why"] = why
    say(f"  {line}")
    return c


def run_unit(out, k, say=print, progress=None, stop=None):
    """Unit `k` of the plan in `out`, done or taken up again; returns its state. A unit that is done, or that another
    process has, is left (`elsewhere` true in what is returned). A unit that fails is a state with its error, and a row."""
    out = Path(out)
    p = read_plan(out)
    if not 0 <= k < len(p["units"]):
        raise vf.Stop(f"--unit {k}: the plan in {out} has units 0 to {len(p['units']) - 1}", EXIT_USAGE)
    u, opt = p["units"][k], p["options"]
    make = make_of(opt)
    folder = out / u["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    was = read_state(folder)
    if was.get("state") == "done":
        if not opt.get("keep_frames"):
            shutil.rmtree(frames_dir(out, u), ignore_errors=True)
        say(f"{u['name']}: done already" + ("" if was.get("make") == make else
                                           " by another version or with other options: left as it is (--again does it again)"))
        return was
    lock = Lock(folder)
    if not lock.take():
        say(f"{u['name']}: another process is running it")
        return dict(was, elsewhere=True)
    same = was.get("make") == make
    if was and not same:
        _wipe(folder, u["tag"])
    state = dict(state="running", unit=k, name=u["name"], make=make, step="", host=socket.gethostname(), pid=os.getpid(),
                 job=os.environ.get("SLURM_JOB_ID"), array=os.environ.get("SLURM_ARRAY_JOB_ID"), started=_now(), finished=None,
                 seconds=dict(was.get("seconds") or {}) if same else {}, objects=dict(was.get("objects") or {}) if same else {},
                 attempts=(was.get("attempts", 0) if same else 0) + 1, wall_s=float(was.get("wall_s") or 0) if same else 0.0,
                 peak_rss_mb=was.get("peak_rss_mb") if same else None, frames_mb=was.get("frames_mb") if same else None,
                 cpus=default_workers(), error=None)
    card = _computes(state, say)
    write_state(folder, state)
    watch = Watch(lock)
    watch.start()
    t0, interrupted = time.time(), None
    try:
        _unit(out, u, opt, folder, state, say, progress, stop)
        state["state"] = "done"
    except vf.Stopped:
        state.update(state="stopped", error="stopped before it finished; `mcdonald batch --out DIR` takes it up again")
    except KeyboardInterrupt as e:                          # Ctrl-C, or a second SIGTERM (`Killed`): the unit's state says so, then on
        interrupted = e
        state.update(state="stopped", error="the process was ended before the unit finished; `mcdonald batch --out DIR` takes it up again")
    except (Exception, SystemExit) as e:                    # a unit's failure is a row, not the batch's end
        state.update(state="failed", error=f"{type(e).__name__}: {e}"[:600])
        say(f"{u['name']} failed: {state['error']}\n{traceback.format_exc()}")
    finally:
        watch.stop()
        peak = max(watch.peak, _tree_rss() or 0) / 2 ** 20
        state.update(finished=_now(), wall_s=round(state["wall_s"] + time.time() - t0, 1), step="" if state["state"] == "done" else state["step"],
                     peak_rss_mb=round(max(peak, state.get("peak_rss_mb") or 0)) or None)
        if card is not None and card.stopped:                # it stopped part-way: the CPUs did the rest
            state["card_stopped"] = card.stopped
        try:
            rec = read_json(folder / f"{u['tag']}_batch.json") or dict(format=FORMAT, make=make, unit=u["name"])
            rec["rows"] = rows_of(out, u, state, rec)
            write_json(folder / f"{u['tag']}_batch.json", rec)
        except Exception as e:                              # noqa: BLE001 -- the state is written all the same
            say(f"{u['name']}: its rows were not written: {type(e).__name__}: {e}")
        write_state(folder, state)
        lock.release()
        if state["state"] in ("done", "failed") and not opt.get("keep_frames"):
            shutil.rmtree(frames_dir(out, u), ignore_errors=True)
    say(f"{u['name']}: {state['state']}" + (f" ({state['error']})" if state["error"] else "") + f", {state['wall_s']:.0f} s")
    if interrupted is not None:
        raise interrupted
    return state


# ---- the rows, and the table over the corpus ---------------------------------------------------------------------
def _video_row(u, state, rec):
    """What every row of a unit starts with: the video, the unit, its state and make."""
    make = state.get("make") or rec.get("make") or {}
    size = rec.get("size") or [u.get("width"), u.get("height")]
    frames = rec.get("frames") or ([u["n0"], u["n1"]] if u.get("n0") else [1, u.get("frames")])
    return dict(id=u["id"], release=u["release"], file=u["file"], unit=u["name"], folder=u["folder"],
                video_frames=u.get("frames"), width=size[0], height=size[1], fps=u.get("fps"), first=frames[0], last=frames[1],
                disclosure=u.get("disclosure"), state=state.get("state") or "waiting", outcome=rec.get("outcome"), note=None,
                error=state.get("error"), mcdonald=make.get("mcdonald"), make=make_id(make), host=state.get("host"),
                unit_seconds=state.get("wall_s"), peak_rss_mb=state.get("peak_rss_mb"), frames_mb=rec.get("frames_mb"),
                cpus=state.get("cpus"),
                proposals=rec.get("proposals"), brief=(rec.get("refused") or {}).get("brief"),
                brief_spots=(rec.get("refused") or {}).get("brief_spots"), brief_longest=(rec.get("refused") or {}).get("brief_longest"),
                edge=(rec.get("refused") or {}).get("edge"), tape=(rec.get("refused") or {}).get("tape"),
                found=rec.get("found"), measured=None, object=None)


def rows_of(out, u, state=None, rec=None):
    """A unit's rows of the corpus table, read from its folder as it is now: one an object measured or tried; else one
    for the video, which says what there is to say -- nothing found, a picture that does not change, no picture, a
    failure with its error, or not done yet."""
    folder = Path(out) / u["folder"]
    state = state if state is not None else read_state(folder)
    rec = rec if rec is not None else (read_json(folder / f"{u['tag']}_batch.json") or {})
    head = _video_row(u, state, rec)
    if state.get("state") != "done":
        return [dict(head, note=f"at: {state['step']}" if state.get("step") else None)]
    if rec.get("outcome") in ("no picture", "still picture"):
        return [dict(head, note=(rec.get("picture") or {}).get("said"))]
    things = several.things(folder)
    failed = rec.get("find_failed") or []
    notes = []
    if failed:
        notes.append(f"Find failed on {len(failed)} of {len(rec.get('windows') or [])} windows ({failed[0]['error']}): "
                     "those frames were not searched")
    if (rec.get("case_file") or {}).get("error"):
        notes.append(f"no case file was made ({rec['case_file']['error']})")
    elif (rec.get("case_file") or {}).get("left_out"):
        notes.append("the case file leaves out " + ("the track sheets' pages" if len(rec["case_file"]["left_out"]) == 1 else "every picture")
                     + ", to be small enough to send")
    if rec.get("found") and rec["found"] > len(things):
        notes.append(f"{rec['found'] - len(things)} more spots that lasted are listed, not measured (past the cap)")
    head["note"] = "; ".join(notes) or None
    if not things and rec.get("outcome") == "listed":
        return [dict(head, note=f"{rec.get('found', 0)} spots that lasted are listed; none was measured, as asked (--most 0)")]
    if not things:
        r = rec.get("refused") or {}
        return [dict(head, note=(head["note"] + "; " if head["note"] else "")
                     + f"{rec.get('proposals', 0)} proposals of Find's, none seen on {SEEN} frames or more as a spot "
                     f"({r.get('brief', 0)} seen too briefly, {r.get('edge', 0)} an edge or a line, {r.get('tape', 0)} a "
                     "scrolling tape)")]
    twice = several.same_things(things)
    found = {o["object"]: o for o in rec.get("objects") or [] if o.get("object")}
    rows = []
    for t in things:
        r = several.row(t, twice.get(t.k))
        o = found.get(t.k, {})
        timing = (state.get("objects") or {}).get(str(t.k), {})
        row = dict(head, measured=len(things), object=t.k, object_folder=f"{u['folder']}/{t.folder.name}",
                   found_strength=o.get("strength"), found_score=o.get("score"), found_frames=o.get("seen"), found_first=o.get("first"),
                   found_last=o.get("last"), found_dark=o.get("dark"), found_windows=len(o.get("windows") or []),
                   followed_frames=None, followed_first=None, followed_last=None, size_px=None, dark=None,
                   same_as=(r.get("same_as") or {}).get("same_as"), several=None, members=None, label=None, headline=None, grade=None,
                   rate_px_per_s=None,
                   rate_is=None, beat_hz=None, beat_share=None, checklist={}, reasons=[], no_power=None, no_power_by_stage={},
                   needs=None, computed_on=None, seconds=timing.get("seconds"), seconds_by_stage=timing.get("stages") or {},
                   sheet_looked=None, audit_frames=None, audit_looked=None, audit_wrong=None, audit_bound=None,
                   object_state="measured", error=r.get("error") or timing.get("error"))
        js = t.case_json
        case = None
        if js is not None and js.exists():
            try:
                case = Case.load(js)
            except (OSError, ValueError, KeyError) as e:
                row["error"] = f"its report could not be read: {e}"
        if case is None:
            row["object_state"] = "failed" if row["error"] else "not measured"
        else:
            f = r.get("followed")
            if f:
                row.update(followed_frames=f["frames"], followed_first=f["first"], followed_last=f["last"], size_px=f["size_px"], dark=f["dark"])
            else:
                row["object_state"] = "not followed"
            if case.stopped_in():
                row["object_state"] = "stopped"
            try:
                label, head_said = case.conclusion()
                grade = case.grade()
                rate, rate_is = case.rate()
                beats = ((case.stages.get("flicker") or {}).get("fields") or {}).get("beat") or {}
                beat = beats.get("object") or {}
                if not beat and beats:                       # a group: its members' beats; the strongest stands for the row
                    beat = max(beats.values(), key=lambda b: float(b.get("amplitude") or 0))
                gf = (case.stages.get("groups") or {}).get("fields") or {}
                row.update(several=gf.get("several"), members=gf.get("members_followed"))
                row.update(label=label, headline=head_said, grade=(grade or {}).get("level"),
                           rate_px_per_s=round(float(rate), 2) if rate is not None else None, rate_is=rate_is,
                           beat_hz=round(float(beat["hz"]), 3) if beat.get("hz") else None,
                           beat_share=round(float(beat["amplitude"]), 4) if beat.get("amplitude") else None,
                           checklist={c["key"]: c["answer"] for c in case.checklist()},
                           reasons=[x["key"] for x in case.reasons()],
                           no_power_by_stage={n: len(st["no_power"]) for n, st in case.stages.items() if st["no_power"]},
                           needs=sum(len(st["needs"]) for st in case.stages.values()), computed_on=case.computed_on, case_started=case.started,
                           mcdonald=case.measured_by or row["mcdonald"], sheet_looked=bool(r.get("track_sheet_looked_at")))
                row["no_power"] = sum(row["no_power_by_stage"].values())
            except Exception as e:                           # noqa: BLE001 -- a report today's words cannot read is said, not fatal
                row["error"] = f"its report could not be read: {type(e).__name__}: {e}"
        a = read_json(Path(f"{t.prefix}_audit.json"))
        if a:
            L = a.get("looked") or {}
            row.update(audit_frames=len(a["drawn"]), audit_looked=bool(L), audit_wrong=len(L["wrong"]) if L else None,
                       audit_bound=L.get("bound"))
        rows.append(row)
    return rows


COLUMNS = ["id", "release", "file", "unit", "video_frames", "width", "height", "fps", "first", "last", "state", "outcome", "note",
           "proposals", "brief", "brief_spots", "brief_longest", "edge", "tape", "found", "measured", "object", "object_state",
           "found_strength", "found_score", "found_frames", "found_first", "found_last", "found_dark", "found_windows",
           "followed_frames", "followed_first", "followed_last", "size_px", "dark", "same_as", "several", "members", "label", "grade",
           "rate_px_per_s", "rate_is", "beat_hz", "beat_share"]
COLUMNS_AFTER = ["reasons", "no_power", "needs", "sheet_looked", "audit_frames", "audit_looked", "audit_wrong", "audit_bound",
                 "computed_on", "seconds", "seconds_paused", "unit_seconds", "paused", "paused_s", "running_s", "cpus", "peak_rss_mb",
                 "frames_mb", "host", "mcdonald", "make", "disclosure",
                 "folder", "error"]
WAITING = ("waiting", "running", "stopped")


PAUSES = "batch_pauses.tsv"     # in a batch's folder, written by a person: when the scheduler held its jobs stopped


def _when(text):
    """An ISO time as a datetime with its zone, or None."""
    try:
        t = datetime.fromisoformat(str(text).strip())
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.astimezone()


def pauses(out):
    """[(from, to, what)] of `DIR/batch_pauses.tsv`: the times the scheduler held the batch's jobs stopped (a queue
    paused by suspending its jobs, a machine put to sleep), one a line, `from<TAB>to<TAB>what`, as ISO times with
    their zone (`2026-11-13T21:57-05:00`); `#` starts a comment. A suspended job's clock runs on, so a unit that ran
    across one counts the pause as its own time; the table takes it out (`with_pauses`). [] where there is no file."""
    f = Path(out) / PAUSES
    if not f.exists():
        return []
    got = []
    for ln in f.read_text(encoding="utf-8").splitlines():
        cells = ln.split("#", 1)[0].split("\t")
        a, b = (_when(cells[0]), _when(cells[1])) if len(cells) >= 2 else (None, None)
        if a and b and b > a:
            got.append((a, b, cells[2].strip() if len(cells) > 2 else ""))
    return got


def _overlap(a, b, ps):
    """Seconds of [a, b] that lie in the pauses `ps`."""
    if a is None or b is None:
        return 0.0
    return sum(max(0.0, (min(b, t) - max(a, f)).total_seconds()) for f, t, _ in ps)


def with_pauses(out, p, rows):
    """Each row's times with the pauses taken out, in place: `paused` -- "yes" where the unit's last try ran across a
    pause and that much is taken out, "perhaps" where an earlier try (one stopped and taken up again) may have, which
    its record cannot date, "no", or None with no pauses given --, `paused_s`, `running_s` (`unit_seconds` less
    `paused_s`), and an object's own `seconds_paused` from its case's start and its seconds."""
    ps = pauses(out)
    made = _when(p.get("made"))
    units = {}
    for u in p["units"]:
        st = read_state(Path(out) / u["folder"])
        a, b = _when(st.get("started")), _when(st.get("finished"))
        wall = float(st.get("wall_s") or 0)
        lap = _overlap(a, b, ps) if b else 0.0
        earlier = wall - (b - a).total_seconds() if a and b and (st.get("attempts") or 1) > 1 else 0.0
        perhaps = earlier > 60 and any(f < a and t > (made or f) for f, t, _ in ps) if a else False
        units[u["folder"]] = dict(paused=None if not ps else "yes" if lap > 0 else "perhaps" if perhaps else "no",
                                  paused_s=round(lap, 1) if ps else None, running_s=round(wall - lap, 1) if st.get("wall_s") else None)
    for r in rows:
        r.update(units.get(r["folder"], {}))
        if r.get("object") and ps and r.get("case_started") and r.get("seconds"):
            a = _when(r["case_started"])
            r["seconds_paused"] = round(_overlap(a, a + timedelta(seconds=float(r["seconds"])), ps), 1) if a else None
    return rows


def collect(out):
    """Every unit's rows, read from the folders as they are now, and the plan: (plan, rows). A unit's times are those
    its record gives, less any pause of the scheduler's that `DIR/batch_pauses.tsv` names (`with_pauses`)."""
    out = Path(out)
    p = read_plan(out)
    rows = []
    for u in p["units"]:
        try:
            rows += rows_of(out, u)
        except Exception as e:                               # noqa: BLE001 -- one unit's trouble is a row
            rows.append(dict(_video_row(u, read_state(out / u["folder"]), {}), state="failed",
                             error=f"its rows could not be read: {type(e).__name__}: {e}"))
    return p, with_pauses(out, p, rows)


def tally(p, rows):
    """The table's counts: videos by what became of them, objects by their report's label and by how sure, the tests
    that could not decide by step, and how many makes the rows are of."""
    videos = {}
    for r in rows:
        videos.setdefault(r["unit"] + "|" + r["folder"], r)
    what = lambda r: (r["outcome"] or "done") if r["state"] == "done" else ("failed" if r["state"] == "failed" else "not done yet")
    by = lambda key, rs: dict(sorted(((k, sum(1 for r in rs if key(r) == k)) for k in {key(r) for r in rs}), key=lambda kv: (-kv[1], str(kv[0]))))
    objs = [r for r in rows if r.get("object")]
    stages = {}
    for r in objs:
        for n, c in (r.get("no_power_by_stage") or {}).items():
            stages[n] = stages.get(n, 0) + c
    # the table's own make: the one most of its done videos have (on a tie, this code's with the plan's options). A
    # table read by a later version than made it is still of one make; videos of another are the ones counted apart.
    done_makes = [r["make"] for r in videos.values() if r["state"] == "done" and r["make"]]
    this = make_id(make_of(p["options"]))
    if done_makes:
        most = max(done_makes.count(m) for m in set(done_makes))
        this = this if done_makes.count(this) == most else sorted(m for m in set(done_makes) if done_makes.count(m) == most)[0]
    return dict(videos=len(videos), by_outcome=by(what, list(videos.values())), objects=len(objs),
                by_object_state=by(lambda r: r["object_state"], objs),
                by_label=by(lambda r: r["label"] or "no report", objs), by_grade=by(lambda r: r["grade"] or "none", objs),
                no_power_by_stage=dict(sorted(stages.items(), key=lambda kv: -kv[1])),
                makes=by(lambda r: f"{r['mcdonald'] or '?'} {r['make'] or '?'}", [r for r in videos.values() if r["state"] == "done"]),
                this_make=this, other_make=sum(1 for r in videos.values() if r["state"] == "done" and r["make"] != this),
                sheets_looked=sum(1 for r in objs if r.get("sheet_looked")), audits_looked=sum(1 for r in objs if r.get("audit_looked")),
                unit_seconds=round(sum(float(r.get("unit_seconds") or 0) for r in videos.values()), 1),
                running_seconds=round(sum(float(r.get("running_s") or r.get("unit_seconds") or 0) for r in videos.values()), 1),
                paused=by(lambda r: r.get("paused") or "not said", list(videos.values())))


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (list, tuple)):
        return ",".join(str(x) for x in v)
    return str(v).replace("\t", " ").replace("\n", " ")


def markdown(p, rows, t):
    """`batch.md`: the table for a person."""
    n = t["videos"]
    words = {"measured": "at least one object measured", "nothing found": "nothing found that lasted",
             "listed": "spots that lasted are listed, none measured",
             "still picture": "the picture does not change", "no picture": "no picture in the file",
             "failed": "failed", "not done yet": "not done yet", "done": "done"}
    opt = p["options"]
    L = [f"# A batch of {n} video{'s' if n != 1 else ''}", "",
         f"mcdonald {__version__} went through {'these videos' if n != 1 else 'this video'} with nobody looking. In each video "
         "the computer searched every frame for spots that move against the background. It followed each spot it saw on "
         f"{SEEN} frames or more, measured it as an object, and wrote a report on it. At most {opt['most']} objects a video "
         "were measured, the most likely first.", "",
         "Nobody chose the objects. Nobody has yet looked at a track sheet, the page of small pictures that shows the object "
         "ringed in each frame. So every report here is provisional, and an object may be a feature of the background or of "
         "the display.", "",
         f"A spot in view for fewer than {SEEN} frames is counted and not measured, however clear it is. An object that "
         "crosses the picture in a few frames is such a spot. The last table gives each video's count. One object can also "
         "have several rows: it is found again after a gap, or it is one of a group that is measured together.", ""]
    if opt.get("note"):
        L += [f"About this batch: {opt['note']}", ""]
    if opt.get("skip"):
        L += [f"These steps were left out of every report: {', '.join(opt['skip'])}.", ""]
    held = t.get("paused") or {}
    if held.get("yes") or held.get("perhaps"):
        L += [f"The scheduler held some jobs stopped while they ran ({PAUSES}). A stopped job's clock runs on, so those "
              f"videos' times would count the pause. In {held.get('yes', 0)} videos the pause is taken out (`running_s`). In "
              f"{held.get('perhaps', 0)} more an earlier try may have run across one, which the record cannot date: their "
              "times are marked `perhaps` and are upper limits.", ""]
    if t["other_make"]:
        L += [f"**{t['other_make']} of the videos were done by another version of mcdonald, or with other options, than the rest.** Their rows "
              "say which (the columns `mcdonald` and `make`). Do not compare them with the rest without checking.", ""]
    L += ["## What became of each video", "", "| | videos |", "|---|---:|"]
    L += [f"| {words.get(k, k)} | {v} |" for k, v in t["by_outcome"].items()]
    if t["objects"]:
        L += ["", "## What the reports say", "", f"{t['objects']} objects have a row. The label is the first words of each report.", "",
              "| label | objects |", "|---|---:|"]
        L += [f"| {k} | {v} |" for k, v in t["by_label"].items()]
        L += ["", "| how sure | objects |", "|---|---:|"] + [f"| {k} | {v} |" for k, v in t["by_grade"].items()]
        L += ["", f"A person has looked at the track sheet of {t['sheets_looked']} of them, and at the audit's frames of "
              f"{t['audits_looked']}."]
        if t["no_power_by_stage"]:
            L += ["", "## Tests that could not decide", "",
                  "A test that cannot decide on a video says so. It has not passed. The counts are over all the objects.", "",
                  "| step | tests that could not decide |", "|---|---:|"]
            L += [f"| {k} | {v} |" for k, v in t["no_power_by_stage"].items()]
    L += ["", "## The videos", "", "| video | frames | what became of it | spots seen too briefly | spots that lasted | measured | labels | folder |",
          "|---|---:|---|---:|---:|---:|---|---|"]
    seen = {}
    for r in rows:
        seen.setdefault(r["folder"], []).append(r)
    for folder, rs in seen.items():
        r = rs[0]
        what = (words.get(r["outcome"] or "done", r["outcome"]) if r["state"] == "done" else
                f"failed: {r['error']}" if r["state"] == "failed" else "not done yet")
        labels = {}
        for x in rs:
            if x.get("object"):
                labels[x["label"] or x["object_state"]] = labels.get(x["label"] or x["object_state"], 0) + 1
        L.append(f"| {r['id']} | {r['first']}–{r['last']} | {what} | {_cell(r.get('brief_spots'))} | {_cell(r['found'])} | {_cell(r['measured'])} | "
                 + ", ".join(f"{v} {k}" for k, v in sorted(labels.items(), key=lambda kv: -kv[1])) + f" | `{folder}/` |")
    L += ["", "Each folder holds the video's objects (`object-1`, `object-2`, ...), each with its report and its track sheet, "
          "the list of them (`<name>_objects.md`), and one file to send (`<name>_batch.mcdonald`). `batch.tsv` has a row for "
          "each object, with what its report found.", ""]
    return "\n".join(L)


def write_table(out):
    """The corpus table, written again from what is in `out`: `batch.json` (everything), `batch.tsv` (a row an object,
    flat) and `batch.md` (for a person). Nothing is measured. Returns (files, tally, rows)."""
    out = Path(out)
    p, rows = collect(out)
    t = tally(p, rows)
    checks = []
    for r in rows:
        for k in (r.get("checklist") or {}):
            if k not in checks:
                checks.append(k)
    cols = COLUMNS + [f"check_{k}" for k in checks] + COLUMNS_AFTER
    lines = ["\t".join(cols)]
    for r in rows:
        flat = dict(r, **{f"check_{k}": (r.get("checklist") or {}).get(k) for k in checks})
        lines.append("\t".join(_cell(flat.get(c)) for c in cols))
    write_text(out / f"{TABLE}.tsv", "\n".join(lines) + "\n")
    write_json(out / f"{TABLE}.json", dict(format=FORMAT, written=_now(), mcdonald=__version__, options=p["options"],
                                           make=make_of(p["options"]), tally=t, columns=cols, rows=rows))
    write_text(out / f"{TABLE}.md", markdown(p, rows, t))
    return [str(out / f"{TABLE}.{e}") for e in ("tsv", "json", "md")], t, rows


# ---- what is done, running, failed ---------------------------------------------------------------------------------
def chosen(units, only=None, leave=None):
    """The units of a plan a run takes: all of them, or those named in `only`, less those named in `leave`. A unit is
    named by its folder's name, its record id, its tag or its number."""
    names = lambda u: {u["name"].lower(), str(u["k"]), (u["id"] or "").lower(), u["tag"].lower()}
    want = {str(x).strip().lower() for x in only or () if str(x).strip()}
    drop = {str(x).strip().lower() for x in leave or () if str(x).strip()}
    unknown = (want | drop) - set().union(*(names(u) for u in units)) if units else want | drop
    if unknown:
        raise vf.Stop(f"no video of this batch is called {', '.join(sorted(unknown))}", EXIT_USAGE)
    return [u for u in units if (not want or names(u) & want) and not (names(u) & drop)]


def status(out):
    """Each unit as it stands, with nothing run: [{k, name, state, step, error, make_same, since, alive_s, ...}].
    `state` is waiting, running, stalled (running, with no sign of life for STALE seconds: it was killed, and the next
    run takes it up), stopped, failed or done."""
    out = Path(out)
    p = read_plan(out)
    this = make_of(p["options"])
    rows = []
    for u in p["units"]:
        folder = out / u["folder"]
        st = read_state(folder)
        state = st.get("state") or "waiting"
        lock = Lock(folder)
        age = lock.age()
        if state == "running" and lock.dead():
            state = "stalled"
        rows.append(dict(k=u["k"], name=u["name"], folder=u["folder"], id=u["id"], state=state, step=st.get("step") or None,
                         error=st.get("error"), make_same=(st.get("make") == this) if st.get("make") else None,
                         mcdonald=(st.get("make") or {}).get("mcdonald"), started=st.get("started"), finished=st.get("finished"),
                         alive_s=round(age) if age is not None else None, wall_s=st.get("wall_s"), host=st.get("host"),
                         job=st.get("job"), attempts=st.get("attempts"), peak_rss_mb=st.get("peak_rss_mb"),
                         frames_on_disk=frames_dir(out, u).is_dir()))
    return p, rows


def status_said(p, rows):
    """`--status` for a person, line by line."""
    count = {}
    for r in rows:
        count[r["state"]] = count.get(r["state"], 0) + 1
    order = ["done", "running", "stalled", "stopped", "failed", "waiting"]
    L = [f"{len(rows)} video{'s' if len(rows) != 1 else ''}: " + ", ".join(f"{count[s]} {s}" for s in order if count.get(s))]
    other = [r for r in rows if r["state"] == "done" and r["make_same"] is False]
    if other:
        L.append(f"{len(other)} of the done were made by another version or with other options, and are left as they are "
                 f"(--again does them again): {', '.join(r['name'] for r in other[:12])}" + (" ..." if len(other) > 12 else ""))
    for r in rows:
        if r["state"] == "running":
            L.append(f"  running  {r['name']}: {r['step'] or 'starting'} (on {r['host']}"
                     + (f", job {r['job']}" if r["job"] else "") + f", a sign of life {r['alive_s']} s ago)")
        elif r["state"] == "stalled":
            L.append(f"  stalled  {r['name']}: no sign of life since it was at \"{r['step']}\"; the next run takes it up")
        elif r["state"] in ("failed", "stopped"):
            L.append(f"  {r['state']:8s} {r['name']}: {r['error']}" + (f" (at: {r['step']})" if r["step"] else ""))
    left = [r for r in rows if r["frames_on_disk"] and r["state"] not in ("running",)]
    if left:
        L.append(f"{len(left)} video{'s have' if len(left) != 1 else ' has'} frames on disk that no running unit is using "
                 f"(in {storage.frames()}): they are used when the unit is taken up again, and removed when it is done")
    return L


# ---- a scheduler's arrays ------------------------------------------------------------------------------------------
# What a unit needs, measured on the pilot of 2026-11-13 (eleven PURSUE videos on a 48-core Xeon of 2025; method
# section 54), not guessed. They are one machine's: elsewhere they are wrong by the ratio of the machines.
FIND_S = 0.2                   # s Find takes a frame at 8 CPUs: 0.11 to 0.22 measured, 720p and 1080p alike
OBJECT_MIN = 3.0               # minutes to measure an object at 8 CPUs, every stage: 0.6 to 9.2 measured, 2.8 on average
UNIT_MIN = 5.0                 # the rest of a unit: the picture, the frames (150 a second), the index, the case file
CPU_POWER = 0.6                # half the CPUs take 2 ** 0.6 = 1.5 times as long: 1.35 (an object) to 1.8 (Find) from 8 to 4
# MB a unit's processes held at their most, each counted by its fair share (`_tree_rss`), fitted to the pilot's units at
# 4 and at 8 CPUs: 3.0 and 4.1 GB at 1920x1080, 1.7 and 2.6 GB at 1280x720, 2.8 GB at 608x1080 and 8 CPUs.
MEM_FIXED, MEM_PER_MPX = 300.0, 900.0          # the unit's own process: a part that is there anyway, and a part by the frame's size
MEM_CPU, MEM_CPU_PER_MPX = 185.0, 45.0         # each worker: its own, and by the frame's size
MEM_ROOM = 1.3                                 # asked for over the measured peak
MEM_STEP = 1500                                # MB: a class's memory is rounded up to this, so a batch is a few arrays, not one a frame size
TIME_CLASSES = (60, 240, 720, 2880)        # minutes: a unit goes in the first class its estimate fits twice over


def resources(u, cpus=8, most=MOST):
    """(megabytes, minutes) to ask a scheduler for, for one unit on `cpus` CPUs with `most` objects measured, from the
    constants above: the minutes it is expected to take, and MEM_ROOM times the memory its processes are expected to
    hold at their most. (A scheduler's own count of a job's memory reads higher, up to the job's limit: it counts the
    frames the system keeps to hand, which it gives back when asked.)"""
    mpx = (u.get("width") or 1920) * (u.get("height") or 1080) / 1e6
    n = (u["n1"] - u["n0"] + 1) if u.get("n0") else (u.get("frames") or 3000)
    minutes = (UNIT_MIN + FIND_S * n / 60.0 + OBJECT_MIN * most) * (8.0 / max(1, cpus)) ** CPU_POWER
    return MEM_ROOM * (MEM_FIXED + MEM_PER_MPX * mpx + cpus * (MEM_CPU + MEM_CPU_PER_MPX * mpx)), minutes


def classes(units, cpus=8, most=MOST):
    """The units in size classes, each to be one job array: [{minutes, mem_mb, units: [k, ...], work}]. A unit goes in
    the first time class that holds twice its estimate (a class's limit kills what runs past it, and a killed unit is
    only taken up again by the next submission), with the units whose memory, rounded up to MEM_STEP, is its own."""
    out = {}
    for u in units:
        mem, minutes = resources(u, cpus, most)
        limit = next((c for c in TIME_CLASSES if 2 * minutes <= c), TIME_CLASSES[-1])
        mem = int(math.ceil(mem / MEM_STEP) * MEM_STEP)
        c = out.setdefault((limit, mem), dict(minutes=limit, mem_mb=mem, units=[], work=0.0))
        c["units"].append(u["k"])
        c["work"] += minutes
    return [out[k] for k in sorted(out)]


def _ranges(ks):
    """Array indices as sbatch takes them: 0-3,7,9-12."""
    ks, parts, i = sorted(ks), [], 0
    while i < len(ks):
        j = i
        while j + 1 < len(ks) and ks[j + 1] == ks[j] + 1:
            j += 1
        parts.append(str(ks[i]) if i == j else f"{ks[i]}-{ks[j]}")
        i = j + 1
    return ",".join(parts)


CARRIED = ("MCDONALD_HOME", "MCDONALD_DATA", "MCDONALD_CATALOG", "MCDONALD_CASES", "MCDONALD_GPU", "PYTHONPATH", "TMPDIR")


def slurm_script(out):
    """The job script of a batch: one task of an array is one unit, and the same script submitted alone writes the
    table. No partition, account or resources are in it: those are the site's, and go on the sbatch line
    (`slurm_lines`, `--sbatch`). The Python that planned the batch, and the folders it was told of, are."""
    out = Path(os.path.abspath(out))
    env = "".join(f"export {k}={shlex.quote(os.environ[k])}\n" for k in CARRIED if os.environ.get(k, "").strip())
    run = f"{shlex.quote(sys.executable)} -m mcdonald.cli batch --out {shlex.quote(str(out))}"
    return f"""#!/bin/bash
#SBATCH --job-name=mcdonald_batch
#SBATCH --ntasks=1
# One video of a `mcdonald batch` run: an array's task id is the unit's number in batch_plan.json; submitted with no
# array, it writes the table; submitted with arguments (--pool N: the job given the graphics card), it runs the videos
# still to do with them. Written by mcdonald {__version__} on {_now()}. The CPUs, the memory, the time and the
# array are on the sbatch line (batch_submit.sh beside this file has the lines), a size class at a time. A task whose
# unit is done exits at once.
set -uo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
{env}if [ -n "${{SLURM_ARRAY_TASK_ID:-}}" ]; then
    exec {run} --unit "$SLURM_ARRAY_TASK_ID"
fi
if [ "$#" -gt 0 ]; then
    exec {run} "$@"
fi
exec {run} --table
"""


def card_job(todo, cpus=8, n=4, most=MOST):
    """The one job given the graphics card (`--card N`): {cpus, mem_mb, minutes, n} for a pool of `n` videos side by
    side, each with `cpus` CPUs. Its memory is the `n` largest videos' (`resources`) together, rounded up to MEM_STEP;
    its time twice the work on CPUs alone shared among the `n`, or the longest video's twice, at most the largest
    class (TIME_CLASSES). That is the CPUs' estimate, an upper bound with a card: eight parts of 1080p videos in a pool
    on the card (2026-11-14) took 1,933 s together where it says 30,451, most of the gap its twelve objects a video
    (they had none to three). A video still running when the job ends is taken up by the next submission."""
    sized = sorted((resources(u, cpus, most) for u in todo), reverse=True)
    n = max(1, min(int(n), len(todo) or 1))
    mem = int(math.ceil(sum(m for m, _ in sized[:n]) / MEM_STEP) * MEM_STEP)
    work = sum(t for _, t in sized)
    minutes = min(TIME_CLASSES[-1], int(math.ceil(max(2 * work / n, 2 * max((t for _, t in sized), default=0)))))
    return dict(cpus=n * cpus, mem_mb=mem, minutes=max(minutes, 10), n=n)


def slurm_lines(out, cpus=8, throttle=None, extra="", todo=None, name="mcdonald_batch", card=None, only=None):
    """The sbatch commands of a batch, as lists of words: an array for each size class of the units still to do, then
    one small job after them all that writes the table. `throttle` is the most tasks at once over all the arrays,
    shared among them by the work each holds; `extra` is passed to every sbatch as it is.

    With `card` (N), one job given the graphics card (`--gres=gpu:1`) in place of the arrays, which runs the units still
    to do N side by side (`run_pool`): an array's tasks given the card would each hold it, and run one after another.
    `only` is the units it is to take, by number, where a person chose some (`--units`, `--except`)."""
    out = Path(os.path.abspath(out))
    p = read_plan(out)
    todo = p["units"] if todo is None else todo
    if card:
        j = card_job(todo, cpus, card, p["options"].get("most", MOST))
        line = ["sbatch", "--parsable", "-J", name, "-c", str(j["cpus"]), f"--mem={j['mem_mb']}M",
                f"--time={j['minutes'] // 60:02d}:{j['minutes'] % 60:02d}:00", "--gres=gpu:1", "-o", str(out / "logs" / "%x_%j.out"),
                *shlex.split(extra or ""), str(out / "batch.sbatch"), "--pool", str(j["n"])]
        if only is not None:
            line += ["--units", ",".join(str(u["k"]) for u in only)]
        table = ["sbatch", "--parsable", "-J", f"{name}_table", "-c", "1", "--mem=2000M", "--time=00:30:00",
                 "-o", str(out / "logs" / "%x_%j.out"), *shlex.split(extra or ""), str(out / "batch.sbatch")]
        return [line], table, [dict(minutes=j["minutes"], mem_mb=j["mem_mb"], units=[u["k"] for u in todo], card=j["n"], cpus=j["cpus"],
                                    work=sum(resources(u, cpus, p["options"].get("most", MOST))[1] for u in todo))]
    cs = classes(todo, cpus, p["options"].get("most", MOST))
    work = sum(c["work"] for c in cs) or 1.0
    share = [max(1, min(len(c["units"]), int(round((throttle or 0) * c["work"] / work)) or 1)) for c in cs]
    while throttle and sum(share) > max(int(throttle), len(cs)):      # rounding up must not pass the most asked for
        share[share.index(max(share))] -= 1
    lines = []
    for c, most in zip(cs, share):
        t = ""
        if throttle:
            t = f"%{most}"
        lines.append(["sbatch", "--parsable", "-J", name, "-c", str(cpus), f"--mem={c['mem_mb']}M", f"--time={c['minutes'] // 60:02d}:{c['minutes'] % 60:02d}:00",
                      f"--array={_ranges(c['units'])}{t}", "-o", str(out / "logs" / "%x_%A_%a.out"), *shlex.split(extra or ""),
                      str(out / "batch.sbatch")])
    table = ["sbatch", "--parsable", "-J", f"{name}_table", "-c", "1", "--mem=2000M", "--time=00:30:00",
             "-o", str(out / "logs" / "%x_%j.out"), *shlex.split(extra or ""), str(out / "batch.sbatch")]
    return lines, table, cs


def submit(out, cpus=8, throttle=None, extra="", dry=False, say=print, name="mcdonald_batch", only=None, leave=None, card=None):
    """Write `batch.sbatch` and `batch_submit.sh` in `out`, and, unless `dry`, submit them: the arrays (or with `card`,
    the one job given the graphics card: `slurm_lines`), then the table's job after them. Returns {script, lines, jobs,
    classes}. Units that are done are not submitted."""
    out = Path(os.path.abspath(out))
    p, rows = status(out)
    waiting = {r["k"] for r in rows if r["state"] not in ("done", "running")}
    todo = [u for u in chosen(p["units"], only, leave) if u["k"] in waiting]
    named = [x for x in (only or []) + (leave or []) if str(x).strip()]
    (out / "logs").mkdir(exist_ok=True)
    write_text(out / "batch.sbatch", slurm_script(out))
    lines, table, cs = slurm_lines(out, cpus, throttle, extra, todo, name, card=card, only=todo if named else None)
    text = ["#!/bin/bash", "# The sbatch lines of this batch, as `mcdonald batch --slurm` submits them. The last waits for the others.", "set -euo pipefail"]
    text += [f"j{i}=$({' '.join(shlex.quote(w) for w in ln)})" for i, ln in enumerate(lines)]
    dep = ":".join(f"$j{i}" for i in range(len(lines)))
    text.append(" ".join(shlex.quote(w) for w in table[:2]) + (f" --dependency=afterany:{dep} " if lines else " ")
                + " ".join(shlex.quote(w) for w in table[2:]))
    result_name = name
    write_text(out / "batch_submit.sh", "\n".join(text) + "\n")
    result = dict(script=str(out / "batch.sbatch"), submit=str(out / "batch_submit.sh"), units=len(todo), jobs=[], table_job=None,
                  classes=[dict(c, array=_ranges(c["units"])) for c in cs])
    if not todo:
        say("every video of the plan is done: nothing to submit")
        return result
    if dry:
        how = (f"one job given the graphics card, {cs[0]['card']} at a time" if card else
               f"{len(lines)} job array{'s' if len(lines) != 1 else ''}")
        say(f"{len(todo)} video{'s' if len(todo) != 1 else ''} to do, in {how}. "
            f"Nothing was submitted. The lines are in {out / 'batch_submit.sh'}:")
        for ln in text[3:]:
            say("  " + ln)
        return result
    if shutil.which("sbatch") is None:
        raise vf.Stop("--slurm needs the Slurm scheduler, and `sbatch` is not on this computer. `--pool N` runs the "
                      "videos here, N at a time.", vf.EXIT_MISSING)
    for ln, c in zip(lines, cs):
        r = subprocess.run(ln, capture_output=True, text=True)
        if r.returncode != 0:
            raise vf.Stop(f"sbatch refused the {'job' if card else 'array'}: {r.stderr.strip() or r.stdout.strip()}\n  {' '.join(ln)}")
        job = r.stdout.strip().split(";")[0]
        result["jobs"].append(job)
        if c.get("card"):
            say(f"submitted job {job}: {len(c['units'])} video{'s' if len(c['units']) != 1 else ''}, {c['card']} at a time on the "
                f"graphics card with {cpus} CPUs each; {c['cpus']} CPUs and {c['mem_mb']} MB in all, up to {c['minutes']} min")
            continue
        say(f"submitted job {job}: {len(c['units'])} video{'s' if len(c['units']) != 1 else ''}, {cpus} CPUs and "
            f"{c['mem_mb']} MB each, up to {c['minutes']} min")
    r = subprocess.run(table[:2] + [f"--dependency=afterany:{':'.join(result['jobs'])}"] + table[2:], capture_output=True, text=True)
    if r.returncode == 0:
        result["table_job"] = r.stdout.strip().split(";")[0]
        say(f"submitted job {result['table_job']}: the table, after them")
    hist = read_json(out / "batch_jobs.json") or []
    hist.append(dict(when=_now(), name=result_name, jobs=result["jobs"], table_job=result["table_job"], cpus=cpus, throttle=throttle, extra=extra,
                     classes=result["classes"], card=card))
    write_json(out / "batch_jobs.json", hist)
    return result


# ---- a pool here ---------------------------------------------------------------------------------------------------
def run_pool(out, n=1, say=print, stop=None, quiet=True, only=None, leave=None):
    """The units still to do, `n` at a time on this computer, each in a process of its own (`mcdonald batch --out DIR
    --unit K`: what a scheduler's task runs), each allowed its share of the CPUs. Returns {unit: exit code}. `stop` is
    asked while they run: on yes the running units are told to end, and are taken up again by the next run.

    Where this process may compute on a graphics card (a job given one: `--gres=gpu:1`), each unit's process opens it
    for itself, and the `n` share it: each is told how many (`gpu.SHARED_VAR`), and plans its batches on the card
    within its part of the card's memory (`gpu.part`). Each unit's log says what computes it, and so does the line
    here when it ends."""
    from . import gpu
    from .progress import CPUS_VAR, cpus
    out = Path(out)
    p, rows = status(out)
    take = {u["k"] for u in chosen(p["units"], only, leave)}
    todo = [r["k"] for r in rows if r["state"] not in ("done", "running") and r["k"] in take]
    n = max(1, min(int(n), len(todo) or 1))
    each = max(1, cpus() // n)
    (out / "logs").mkdir(exist_ok=True)
    env = dict(os.environ, **{CPUS_VAR: str(each), gpu.SHARED_VAR: str(n * gpu.sharers())})
    running, codes = {}, {}
    try:
        while todo or running:
            while todo and len(running) < n:
                k = todo.pop(0)
                log = open(out / "logs" / f"unit_{k}.log", "a", encoding="utf-8")
                running[k] = (subprocess.Popen([sys.executable, "-m", "mcdonald.cli", "batch", "--out", str(out), "--unit", str(k)],
                                               stdout=log if quiet else None, stderr=subprocess.STDOUT if quiet else None, env=env,
                                               stdin=subprocess.DEVNULL), log)
                say(f"started {p['units'][k]['name']} ({each} CPU{'s' if each != 1 else ''})")
            time.sleep(0.5)
            for k, (proc, log) in list(running.items()):
                if proc.poll() is not None:
                    codes[k] = proc.returncode
                    log.close()
                    del running[k]
                    st = read_state(out / p["units"][k]["folder"])
                    say(f"{p['units'][k]['name']}: {st.get('state', 'ended')}" + (f" ({st['error']})" if st.get("error") else "")
                        + (f", on the graphics card{' until it stopped' if st.get('card_stopped') else ''}" if st.get("card") else "")
                        + f"; {len(todo) + len(running)} still to do")
            if stop is not None and stop():
                raise Killed()
    except KeyboardInterrupt:
        for proc, log in running.values():
            proc.terminate()
        for proc, log in running.values():
            try:
                proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                proc.kill()
            log.close()
        say("stopped: the videos under way are taken up again by the next `mcdonald batch --out` of this folder")
        raise
    return codes


def again(out, names=None, say=print):
    """Units to be done again: all that are done or failed, or those named (by unit name, record id or number). Each
    one's folder is moved aside (`<folder>.before-<time>`), never deleted, and its state forgotten. Returns the names."""
    out = Path(out)
    p, rows = status(out)
    want = {str(x).strip().lower() for x in names or () if str(x).strip()}
    done = []
    for r, u in zip(rows, p["units"]):
        if r["state"] == "running":
            continue
        if want and not ({u["name"].lower(), str(u["k"]), (u["id"] or "").lower(), u["tag"].lower()} & want):
            continue
        folder = out / u["folder"]
        if folder.exists() and any(folder.iterdir()):
            aside = folder.with_name(f"{folder.name}.before-{datetime.now():%Y%m%d-%H%M%S}")
            os.replace(folder, aside)
            say(f"{u['name']}: what was there is now in {aside}")
        shutil.rmtree(frames_dir(out, u), ignore_errors=True)
        done.append(u["name"])
    return done


# ---- the command line ------------------------------------------------------------------------------------------------
def _signals(flag):
    """SIGTERM (a scheduler ending the job) asks the unit to stop where it can write what it has; a second one ends it."""
    def handler(signum, frame):
        if flag.is_set():
            raise Killed()
        flag.set()
    try:
        signal.signal(signal.SIGTERM, handler)
    except (ValueError, OSError):                          # not the main thread
        pass


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="mcdonald batch", formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Many videos, with nobody looking. In each video the computer searches every frame for spots that move "
                    "against the background. It follows each spot it sees on 40 frames or more, measures it as an object and "
                    "writes a report. Each video gets a folder in --out, and one table covers them all. A batch can be "
                    "stopped and started again: what is done is not done twice.",
        epilog="examples:\n"
               "  mcdonald batch PR113 PR149 --out runs            these two videos, one after the other\n"
               "  mcdonald batch --list videos.txt --out runs --pool 4\n"
               "  mcdonald batch --catalog --out runs --slurm --sbatch=\"--nice=100\"\n"
               "  mcdonald batch --catalog --out runs --slurm --card 8 --cpus-per-video 4\n"
               "  mcdonald batch --out runs --status               what is done, running and failed\n"
               "  mcdonald batch --out runs                        go on with what is left\n"
               "  mcdonald batch --audit runs/pr113/object-1 --wrong none --by \"A. Reader\"\n\n"
               "A list is a text file with one video a line: a path, a record id or a release's file name.\n"
               "To take only part of a video, add its first and last frame (PR113 400-420).\n\n"
               "Every report a batch writes is provisional. It stays so until a person has looked at its track sheet,\n"
               "the page that shows the object ringed in each frame (`mcdonald report CASE.json --i-looked`).")
    ap.add_argument("videos", nargs="*", help="videos: paths, record ids (PR113) or release file names")
    ap.add_argument("--list", metavar="FILE", help="a text file of videos, one a line")
    ap.add_argument("--catalog", action="store_true", help="every video of the catalog in use")
    ap.add_argument("--out", metavar="DIR", help="the batch's folder: one folder a video in it, the plan and the table")
    ap.add_argument("--video-dir", action="append", default=[], metavar="DIR",
                    help="a folder to look for the videos' files in before any is downloaded (repeatable); $MCDONALD_DATA and "
                         "the storage folder are looked in anyway")
    how = ap.add_argument_group("how it runs")
    how.add_argument("--pool", type=int, metavar="N", help="N videos side by side on this computer, each with its share of the CPUs")
    how.add_argument("--slurm", action="store_true", help="write a job script and submit it to the Slurm scheduler as job arrays")
    how.add_argument("--slurm-print", action="store_true", help="write the job script and print the sbatch lines; submit nothing")
    how.add_argument("--sbatch", default="", metavar="ARGS", help="more arguments for every sbatch line, such as a partition or --nice=100")
    how.add_argument("--cpus-per-video", type=int, default=8, metavar="C", help="with --slurm: the CPUs one video's job asks for (default 8)")
    how.add_argument("--throttle", type=int, metavar="T", help="with --slurm: about this many videos at once, at most")
    how.add_argument("--card", type=int, metavar="N",
                     help="with --slurm: in place of job arrays, one job that is given the graphics card runs the videos, N at a "
                          "time, each with --cpus-per-video CPUs (the tasks of an array given the card would wait for each other)")
    how.add_argument("--job-name", default="mcdonald_batch", metavar="NAME", help="with --slurm: what the jobs are called in the queue")
    how.add_argument("--unit", type=int, metavar="K", help="run unit K of the plan and nothing else (what a job array's task runs)")
    how.add_argument("--units", metavar="NAMES", help="only these videos of the batch (comma-separated names, as --status lists them)")
    how.add_argument("--except", dest="leave", metavar="NAMES", help="every video of the batch but these")
    how.add_argument("--status", action="store_true", help="say what is done, running and failed; run nothing")
    how.add_argument("--table", action="store_true", help="write the table again from what is in --out; run nothing")
    how.add_argument("--again", nargs="?", const="", metavar="NAMES",
                     help="do videos again: all that are done or failed, or those named (comma-separated); what was there is moved aside")
    what = ap.add_argument_group("what it does")
    what.add_argument("--window", type=int, default=None, metavar="N", help=f"frames Find takes at a time (default {WINDOW})")
    what.add_argument("--overlap", type=int, default=None, metavar="N", help=f"frames one window shares with the next (default {OVERLAP})")
    what.add_argument("--most", type=int, default=None, metavar="M",
                      help=f"measure at most M objects a video, the most likely first; the rest are listed (default {MOST}; "
                           "0 lists them all and measures none)")
    what.add_argument("--keep", type=int, default=None, metavar="N",
                      help=f"spots Find keeps in each stretch of frames, the most likely first (default {KEEP}, the number a person is shown)")
    what.add_argument("--quick", action="store_true", default=None,
                      help=f"leave out the two long steps ({', '.join(QUICK)}): the reports say what was not measured")
    what.add_argument("--skip", default=None, metavar="STEPS", help="steps to leave out, comma-separated, as `mcdonald run` takes them")
    what.add_argument("--only", default=None, metavar="STEPS", help="only these steps, comma-separated")
    what.add_argument("--audit-frames", type=int, default=None, metavar="N", help=f"frames drawn for each object's audit (default {AUDIT})")
    what.add_argument("--keep-frames", action="store_true", default=None, help="leave each video's frames on disk when it is done")
    what.add_argument("--note", default=None, metavar="TEXT",
                      help="a line about this batch, kept with it and printed at the head of its table: which copy of the "
                           "code made it, what it is for")
    aud = ap.add_argument_group("an object's audit")
    aud.add_argument("--audit", metavar="FOLDER", help="an object's folder: say what its audit drew, or record a look with --wrong")
    aud.add_argument("--wrong", metavar="NUMBERS", help="with --audit: the sheet's numbers whose ring is off the object, or `none`")
    aud.add_argument("--by", default="", metavar="NAME", help="with --audit --wrong: who looked")
    aud.add_argument("--agent", action="store_true", help="with --audit --wrong: an AI agent looked, not a person")
    ap.add_argument("--json", action="store_true", help="print one JSON object on stdout; everything else goes to stderr")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    say = (lambda *a: print(*a, file=sys.stderr, flush=True)) if args.json else (lambda *a: print(*a, flush=True))
    inputs = {k: v for k, v in vars(args).items() if v not in (None, False, "", []) and k != "json"}

    if args.audit:
        return _audit(args, say, inputs)
    if args.card is not None and (args.card < 1 or not (args.slurm or args.slurm_print) or args.throttle):
        ap.error("--card N goes with --slurm (or --slurm-print), N 1 or more, and without --throttle: its one job runs N videos at a time")
    if not args.out:
        ap.error("--out DIR is needed: the folder the batch keeps its plan, its videos' folders and its table in")
    out = Path(args.out)
    given = [(v, None, None) for v in args.videos]
    for v in list(given):
        m = re.fullmatch(r"(.+?):(\d+)-(\d+)", v[0])            # PR113:400-420 on the command line
        if m and not Path(v[0]).exists():
            given[given.index(v)] = (m.group(1), int(m.group(2)), int(m.group(3)))
    if args.list:
        given += read_list(args.list)
    if args.catalog:
        given += [(Path(r["path"]).name, None, None) for r in _catalog.active().videos()]
    for x in (args.only or "").split(",") + (args.skip or "").split(","):
        from .stages import STAGES
        if x and x not in STAGES:
            ap.error(f"no such step: {x} (the steps are {', '.join(STAGES)})")

    # the plan: made, added to, or read. An option not given keeps the plan's; a new plan takes the defaults
    old = read_json(out / PLAN)
    said = {k: v for k, v in dict(window=args.window, overlap=args.overlap, most=args.most, keep=args.keep,
                                  audit_frames=args.audit_frames).items() if v is not None}
    if (given or old is None or said or args.quick or args.skip is not None or args.only is not None or args.keep_frames or args.video_dir
            or args.note is not None):
        if old is None and not given:
            ap.error(f"{out} holds no batch yet: name the videos, or give --list FILE or --catalog")
        o = dict((old or {}).get("options") or {})
        ns = argparse.Namespace(window=args.window or o.get("window", WINDOW), overlap=args.overlap if args.overlap is not None else o.get("overlap", OVERLAP),
                                most=args.most if args.most is not None else o.get("most", MOST),
                                keep=args.keep or o.get("keep", KEEP), audit_frames=args.audit_frames or o.get("audit", AUDIT),
                                quick=args.quick, skip=args.skip if args.skip is not None else ",".join(o.get("skip") or []),
                                only=args.only if args.only is not None else ",".join(o.get("only") or []),
                                keep_frames=args.keep_frames if args.keep_frames is not None else o.get("keep_frames", False),
                                video_dir=args.video_dir or o.get("video_dir") or [],
                                note=args.note if args.note is not None else o.get("note", ""))
        if ns.overlap >= ns.window:
            ap.error("--overlap must be fewer frames than --window")
        if ns.most < 0 or ns.keep < 1:
            ap.error("--most is 0 or more (0: the spots are listed and none is measured), and --keep 1 or more")
        p = plan(out, given, options_of(ns), fetch=bool(args.slurm or args.slurm_print), say=say)
    else:
        p = read_plan(out)

    only, leave = (args.units or "").split(","), (args.leave or "").split(",")
    chosen(p["units"], only, leave)                             # a name that is no video's is said now
    if args.again is not None:
        moved = again(out, [x for x in args.again.split(",") if x.strip()], say)
        say(f"{len(moved)} video{'s' if len(moved) != 1 else ''} to be done again")
    if args.status or args.table:
        files, t = [], None
        if args.table:
            files, t, _ = write_table(out)
        p, rows = status(out)
        for line in status_said(p, rows):
            say(line)
        if args.table:
            say(f"wrote {files[2]} (and .tsv, .json): {t['videos']} videos, {t['objects']} objects")
        if args.json:
            emit(envelope("batch", inputs, None, files, dict(out=str(out), units=rows, tally=t)))
        return 0
    if args.unit is not None:
        flag = threading.Event()
        _signals(flag)
        from .progress import to_stderr
        with said_to_stderr(args.json):                       # with --json, stdout is the envelope's alone: a stage's own lines go to stderr
            st = run_unit(out, args.unit, say=say, progress=to_stderr(), stop=flag.is_set)
        if args.json:
            emit(envelope("batch", inputs, None, [], dict(out=str(out), unit=st)))
        return 0 if st.get("state") in ("done", "running") or st.get("elsewhere") else 1
    if args.slurm or args.slurm_print:
        r = submit(out, args.cpus_per_video, args.throttle, args.sbatch, dry=not args.slurm, say=say, name=args.job_name,
                   only=only, leave=leave, card=args.card)
        if args.json:
            emit(envelope("batch", inputs, None, [r["script"], r["submit"]], dict(out=str(out), **r)))
        return 0

    # here: the units still to do, one at a time (each with every CPU) or --pool N side by side
    flag = threading.Event()
    _signals(flag)
    take = {u["k"] for u in chosen(p["units"], only, leave)}
    todo = [r for r in status(out)[1] if r["state"] not in ("done", "running") and r["k"] in take]
    say(f"{len(p['units'])} video{'s' if len(p['units']) != 1 else ''} in {out}, {len(todo)} to do")
    try:
        if args.pool and args.pool > 1:
            run_pool(out, args.pool, say=say, stop=flag.is_set, only=only, leave=leave)
        else:
            from .progress import to_stderr
            with said_to_stderr(args.json):                   # with --json, stdout is the envelope's alone
                for r in todo:
                    if flag.is_set():
                        break
                    run_unit(out, r["k"], say=say, progress=to_stderr(), stop=flag.is_set)
    except KeyboardInterrupt:
        say("stopped: `mcdonald batch --out` of this folder goes on from here")
    files, t, _ = write_table(out)
    p, rows = status(out)
    for line in status_said(p, rows):
        say(line)
    say(f"the table: {files[2]} (and .tsv, .json)")
    if args.json:
        emit(envelope("batch", inputs, None, files, dict(out=str(out), units=rows, tally=t),
                      notes=["Every report of a batch is provisional: nobody chose the objects, and nobody has looked at a track sheet."]))
    return 0 if all(r["state"] == "done" for r in rows) else 1


def _audit(args, say, inputs):
    """`--audit FOLDER`: an object's audit, said; with `--wrong`, a look at its sheet recorded."""
    folder = Path(args.audit)
    if not folder.is_dir():
        raise vf.Stop(f"{folder}: no such folder")
    objs = [folder] if several.NAME.match(folder.name) else [t.folder for t in several.things(folder)]
    if not objs:
        raise vf.Stop(f"{folder}: not an object's folder (object-1, object-2 ...) nor a video's folder with objects in it")
    if args.wrong is not None:
        if len(objs) != 1:
            raise vf.Stop("--wrong goes with one object's folder (.../object-1): an audit is of one track", EXIT_USAGE)
        text = args.wrong.strip().lower()
        try:
            wrong = [] if text in ("none", "0", "") else [int(x) for x in re.split(r"[,\s]+", text) if x]
        except ValueError:
            raise vf.Stop("--wrong takes the sheet's numbers, comma-separated, or `none`", EXIT_USAGE)
        audit_record(objs[0], wrong, by=args.by, agent=args.agent)
        try:
            several.index(objs[0].parent)                    # the list beside the objects says who has looked
        except Exception as e:                               # noqa: BLE001 -- the look is recorded all the same
            say(f"the list of objects was not written again: {type(e).__name__}: {e}")
    found = {}
    for d in objs:
        js = next(iter(sorted(d.glob("*_audit.json"))), None)
        a = read_json(js) if js else None
        found[d.name] = a
        say(f"{d.name}: {audit_said(a)}")
    if args.json:
        emit(envelope("batch", inputs, None, [str(f) for d in objs for f in sorted(d.glob("*_audit.*"))], dict(audits=found)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
