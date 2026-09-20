"""From a few hand marks to an automatic track -- and whether it is on the object.

`mcdonald mark` ends with a few clicks. What they are for is the linker: a mark
is a seed, a pair is the velocity it cannot acquire alone. This is the step
between, with no window in it, so it is tested headless and either front end,
a command (`layers --marks`, `integrity --marks`) or a script can drive it.

1. Choose the detector's scale and polarity *from the marks* (`pick_detector`).
   The matched filter is tuned to one size and misses an object much larger
   than it outright: PR113's 25 px object is 71 px from the nearest candidate
   at the 9 px default and 1.9 px away at 21. A mark says where to look, so
   the sweep is easy to judge: the scale, in whichever polarity, whose
   candidate sits closest to the marks.
2. Run the detector exactly as `layers --auto-track` does
   (`forensics.frame_candidates`) -- on a process pool, because it costs 0.8 s
   a 1080p frame at 9 px and 4 s at 21 -- and keep what it finds (`cache`), so
   that linking again after one more mark costs almost nothing.
3. Link with `forensics.link_track`, **from every mark, both ways in time**
   (`assemble`). Between two marks the track is linked forward from the earlier
   and backward from the later, each with the velocity the pair gives. Where
   the two agree, that is the track. Where they disagree the frame is
   *disputed*: the nearer mark's version is kept, and the frame is flagged, not
   smoothed over. Before the first mark it links backward, after the last
   forward, until the object is lost or the clip ends. A mark placed after a
   loss is therefore a new seed: the track resumes from it, and runs back
   toward the loss.
4. Hold the result against the marks, two ways. `residuals`: how far the track
   sits from each. `arrivals`: how far the forward link from one mark lands
   from the *next* -- a mark it was not seeded from, and so the first honest
   answer to "did it lock onto the object?". The second is looking, which is
   what the track strip is for.

`link_from_marks` is a generator: it yields a `Link` after every step, so a
caller can draw the track as it grows and stop it when it has seen enough. A
whole clip at 21 px is ten minutes; nobody should have to wait for it to find
out that the track left the object in the first second.

Every pass ends where the object is lost for `max_gap` frames. Past that point
`link_track` starts again on the strongest candidate in the frame, which is no
longer the thing that was marked, and drawing it would be showing a track of
something else under the object's name.
"""
import multiprocessing
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import forensics as vf

SIZES = (5, 9, 15, 21, 31, 45)
# The response a candidate needs. Low, as in forensics.detect_scale_sweep, and for
# the reason given in forensics.frame_candidates: this link never falls back on
# "the strongest candidate", so a weak one far from the prediction costs nothing,
# and a weak one on it is the object. At the blind track's 35, PR113 loses its
# last frame and the published 142 px/frame does not come back.
MIN_RESP = 5.0
_G = {}


@dataclass
class Link:
    """Where the link has got to. `done` marks the last one."""
    stage: str                                   # masks | scale | linking | done
    say: str                                     # one line, for a status bar
    track: dict = field(default_factory=dict)    # {frame: (x, y)}
    source: dict = field(default_factory=dict)   # {frame: both | forward | backward | disputed}
    marks: dict = field(default_factory=dict)    # the hand marks it was made from
    size: float = None
    dark: bool = None
    n_lo: int = None                             # how far back and
    n_hi: int = None                             # how far on the detector has been run
    lost_at: int = None                          # the last linked frame, if the forward end lost the object
    lost_before: int = None                      # the first linked frame, if the backward end did
    stopped: bool = False
    residuals: dict = field(default_factory=dict)   # {marked frame: px from the track, or None where it has no link}
    arrivals: dict = field(default_factory=dict)    # {marked frame: px at which the link from the mark before arrives}
    sweep: list = field(default_factory=list)       # [(dark, size, [px to each mark shown])], the record of the choice
    masks: dict = None
    done: bool = False

    def worst(self):
        """The largest distance from a hand mark, or None if any mark has no link under it."""
        if not self.residuals or any(v is None for v in self.residuals.values()):
            return None
        return max(self.residuals.values())

    def disputed(self):
        return sorted(n for n, how in self.source.items() if how == "disputed")


# ---- the pool ---------------------------------------------------------------------------
def _init(clip, masks, rows):
    _G.update(clip=clip, masks=masks, rows=rows)


def _detect(job):
    n, size, dark = job
    return n, size, dark, vf.frame_candidates(_G["clip"], n, _G["masks"], _G["rows"], size, dark, MIN_RESP)


class _Workers:
    """The detector on `procs` processes, or inline with procs=0.

    Never forked: the caller may be a GUI with threads running, and a forked
    child inherits their locks in whatever state they were in. The price is
    that the children import the caller's main module by path, and a program
    piped to `python -` has none; then the pool cannot start, and the detector
    runs inline instead -- slower, and the same answer."""

    def __init__(self, clip, masks, rows, procs):
        keep = {k: masks[k] for k in ("blocks", "graphics", "colour")}
        self.pool = None
        if procs:
            try:
                ctx = multiprocessing.get_context("spawn" if sys.platform == "win32" else "forkserver")
                self.pool = ctx.Pool(procs, _init, (clip, keep, rows))
            except (OSError, EOFError):
                self.pool = None
        if self.pool is None:
            _init(clip, keep, rows)

    def imap(self, jobs, cache=None):
        """Candidates for each (frame, size, dark), in order. What `cache` already holds is not run again."""
        cache = {} if cache is None else cache
        todo = [j for j in jobs if j not in cache]
        fresh = self.pool.imap(_detect, todo) if self.pool else map(_detect, todo)
        for job in jobs:
            if job not in cache:
                n, size, dark, c = next(fresh)
                cache[(n, size, dark)] = c
            yield (*job, cache[job])

    def close(self):
        if self.pool:
            self.pool.terminate()
            self.pool.join()


def default_procs():
    return max(1, min(8, (os.cpu_count() or 2) - 2))


# ---- the choice of detector -------------------------------------------------------------
def _nearest(cands, xy):
    return min((float(np.hypot(c[0] - xy[0], c[1] - xy[1])) for c in cands), default=float("inf"))


def pick_detector(workers, marks, sizes=SIZES, tol=6.0, gain=0.5, cache=None):
    """(size, dark, sweep): the scale and polarity whose candidate sits closest to the marks.

    Judged on the first and last marks, in both polarities, smallest scale
    first. A scale qualifies when it puts a candidate within `tol` of every
    mark shown -- but the first to qualify is not taken. A filter much smaller
    than the object fires on its rim, the rim of a small object is within tol
    of a mark on its centre, and the track then rides the rim, a radius off.
    So it climbs: on to the next scale while that brings the candidate at least
    `gain` px closer to the marks, and no further, because the large scales are
    the expensive ones. size is None when nothing qualifies; the sweep says how
    close each came. Yields (say, sweep) as it goes, then returns."""
    ns = sorted(marks)
    shown = [ns[0]] if len(ns) == 1 else [ns[0], ns[-1]]
    sweep, best = [], None
    for s in sizes:
        got = {(n, d): c for n, _, d, c in workers.imap([(n, float(s), d) for d in (False, True) for n in shown], cache)}
        ok = []
        for d in (False, True):
            dist = [_nearest(got[(n, d)], marks[n]) for n in shown]
            sweep.append((d, s, dist))
            if max(dist) <= tol:
                ok.append((float(np.mean(dist)), d))
        if ok and (best is None or min(ok)[0] < best[0] - gain):
            best = (min(ok)[0], float(s), min(ok)[1])
            yield f"detector: {s} px puts a candidate {best[0]:.1f} px from the marks; is the next scale closer?", sweep
        elif best is not None:
            break                                    # no closer than the scale below, or it has lost the object
        else:
            yield f"detector: nothing within {tol:g} px of the marks at {s} px", sweep
    return (best[1], best[2], sweep) if best else (None, None, sweep)


# ---- the link ---------------------------------------------------------------------------
def _dist(p, q):
    return float(np.hypot(p[0] - q[0], p[1] - q[1]))


def _pass(cands, a, b, xy, v, max_gap):
    """`link_track` from a mark on frame a toward frame b, whichever way in time
    that is, cut where it first loses the object for max_gap frames. Backward is
    the same linker on the frames in reverse, with the velocity reversed."""
    step = 1 if b >= a else -1
    have = {step * n: cands[n] for n in range(min(a, b), max(a, b) + 1) if n in cands}
    trk = vf.link_track(have, step * a, step * b, (step * a, *xy), (step * v[0], step * v[1]), max_gap=max_gap)
    out, last = {}, step * a
    for n in sorted(trk):
        if n - last > max_gap:                       # what follows is link_track starting again on something else
            break
        out[step * n], last = trk[n], n
    return out


def assemble(cands, marks, n_lo, n_hi, max_gap=40, agree=1.0):
    """(track, source, arrivals) from candidates on the frames n_lo..n_hi and the marks.

    Only that range is used, and it is taken to be complete: a pass over missing
    frames would see a gap, and link_track widens its gate with the gap."""
    ns = sorted(marks)
    track, source, arrivals = {}, {}, {}

    def put(n, xy, how):
        if source.get(n) != "disputed":
            track[n], source[n] = xy, how

    def v_between(a, b):
        return ((marks[b][0] - marks[a][0]) / (b - a), (marks[b][1] - marks[a][1]) / (b - a))

    for a, b in zip(ns, ns[1:]):
        if a > n_hi or a < n_lo:
            continue
        v = v_between(a, b)
        fwd = _pass(cands, a, min(b, n_hi), marks[a], v, max_gap)
        back = _pass(cands, b, a, marks[b], v, max_gap) if b <= n_hi else {}
        if b <= n_hi:
            arrivals[b] = _dist(fwd[b], marks[b]) if b in fwd else None
        for n in range(a, min(b, n_hi) + 1):
            f, k = fwd.get(n), back.get(n)
            if f and k:
                same = _dist(f, k) <= agree
                put(n, f if same or n - a <= b - n else k, "both" if same else "disputed")
            elif f or k:
                put(n, f or k, "forward" if f else "backward")
    first, last = ns[0], ns[-1]
    v0 = v_between(ns[0], ns[1]) if len(ns) > 1 else (0.0, 0.0)
    v1 = v_between(ns[-2], ns[-1]) if len(ns) > 1 else (0.0, 0.0)
    head = _pass(cands, first, n_lo, marks[first], v0, max_gap) if n_lo <= first <= n_hi else {}
    tail = _pass(cands, last, n_hi, marks[last], v1, max_gap) if n_lo <= last <= n_hi else {}
    for n, xy in head.items():
        if n not in track:
            put(n, xy, "both" if n == first and n in tail else "backward")
    for n, xy in tail.items():
        if n not in track:
            put(n, xy, "forward")
    return track, source, arrivals, head, tail


def _residuals(track, marks):
    return {n: (_dist(track[n], xy) if n in track else None) for n, xy in sorted(marks.items())}


def _summary(link, kind, max_gap):
    if not link.track:
        return (f"never acquired at {kind}: no candidate came within the gate of the prediction "
                f"on frames {link.n_lo}–{link.n_hi}")
    ns, res = sorted(link.marks), link.residuals
    a, b = min(link.track), max(link.track)
    w = link.worst()
    parts = [f"{len(link.track)} of {b - a + 1} frames linked, {a}–{b}, at {kind}",
             "a hand mark has no link under it" if w is None else
             f"within {w:.1f} px of {'the mark' if len(res) == 1 else f'all {len(res)} marks'}"]
    if link.arrivals:
        missed = [n for n, d in link.arrivals.items() if d is None]
        parts.append(f"the link from the mark before does not reach the mark on {', '.join(map(str, missed))}" if missed else
                     f"each mark's link arrives within {max(link.arrivals.values()):.1f} px of the next mark")
    d = link.disputed()
    if d:
        parts.append(f"{len(d)} frame{'s' if len(d) != 1 else ''} disputed between the forward and backward links "
                     f"({d[0]}–{d[-1]}): look at those")
    parts.append(f"lost going back from frame {link.lost_before}" if link.lost_before is not None else
                 f"searched back to frame {link.n_lo}")
    parts.append(f"lost after frame {link.lost_at}" if link.lost_at is not None else f"searched on to frame {link.n_hi}")
    if link.stopped:
        parts.append("stopped before it had finished")
    return "; ".join(parts)


def link_from_marks(clip, marks, masks=None, rows=None, n_lo=None, n_hi=None, size=None, dark=None,
                    sizes=SIZES, tol=6.0, procs=None, max_gap=40, stop=None, cache=None):
    """Hand marks {frame: (x, y)} -> an automatic track through all of them, and beyond both ends.

    A generator of `Link`s; the last has `.done`. Give `size` to skip the
    choice of detector (and `dark`, else bright). `stop` is a callable polled
    between frames. `procs=0` runs the detector inline. `cache` is a dict the
    candidates are kept in, {(frame, size, dark): [...]}: hand the same one back
    and linking again after another mark runs the detector on new frames only.
    n_lo and n_hi bound the search; the clip's window by default."""
    stop = stop or (lambda: False)
    ns = sorted(marks)
    if not ns:
        yield Link("done", "no marks: a mark is where a link starts", done=True)
        return
    cache = {} if cache is None else cache
    lo_end, hi_end = int(max(n_lo or clip.n0, clip.n0)), int(min(n_hi or clip.n1, clip.n1))
    base = dict(marks=dict(marks))

    if masks is None:
        yield Link("masks", "building the static masks, once per clip…", **base)
        masks = vf.static_masks(clip)
    base["masks"] = masks

    nprocs = default_procs() if procs is None else procs
    workers = _Workers(clip, masks, rows, nprocs)
    try:
        sweep = []
        if size is None:
            yield Link("scale", "choosing the detector's scale from the marks…", **base)
            picking = pick_detector(workers, marks, sizes, tol, cache=cache)
            try:
                while True:
                    say, sweep = next(picking)
                    yield Link("scale", say, sweep=list(sweep), **base)
                    if stop():
                        yield Link("done", "stopped while choosing the detector", sweep=list(sweep), stopped=True,
                                   done=True, **base)
                        return
            except StopIteration as found:
                size, dark, sweep = found.value
            if size is None:
                d, s, dist = min(sweep, key=lambda r: max(r[2]))
                yield Link("done", f"no detector scale from {sizes[0]} to {sizes[-1]} px puts a candidate within {tol:g} px "
                           f"of the marks (closest: {max(dist):.0f} px away at {s} px, {'dark' if d else 'bright'}). "
                           "Nothing was linked.", sweep=sweep, done=True, **base)
                return
        size, dark = float(size), bool(dark)
        base.update(size=size, dark=dark, sweep=sweep)
        kind = f"{size:g} px, {'dark' if dark else 'bright'}"

        cands, state = {}, dict(lo=ns[0], hi=ns[0] - 1, lost_at=None, lost_before=None, stopped=False)
        block = max(nprocs, 4)

        def snapshot(stage="linking", say=None):
            track, source, arrivals, head, tail = assemble(cands, marks, state["lo"], state["hi"], max_gap)
            link = Link(stage, "", track=track, source=source, arrivals=arrivals, residuals=_residuals(track, marks),
                        n_lo=state["lo"], n_hi=state["hi"], lost_at=state["lost_at"], lost_before=state["lost_before"],
                        stopped=state["stopped"], done=stage == "done", **base)
            link.say = say or _summary(link, kind, max_gap)
            return link, head, tail

        def run(frames):
            """The detector on these frames, in this order; False if asked to stop."""
            for n, _, _, c in workers.imap([(k, size, dark) for k in frames], cache):
                cands[n] = c
                state["lo"], state["hi"] = min(state["lo"], n), max(state["hi"], n)
                if stop():
                    state["stopped"] = True
                    return False
            return True

        # 1. between the first mark and the last, where every frame has a mark on each side of it
        going = True
        for k in range(ns[0], ns[-1] + 1, block):
            going = run(range(k, min(k + block, ns[-1] + 1)))
            if not going:
                break
            yield snapshot(say=f"linking at {kind}: between the marks, frame {state['hi']} of {ns[-1]}")[0]
        # 2. on from the last mark, until the object is lost or the clip ends
        k = ns[-1] + 1
        while going and k <= hi_end:
            going = run(range(k, min(k + block, hi_end + 1)))
            k = state["hi"] + 1
            link, _, tail = snapshot(say=f"linking at {kind}: on from the last mark, frame {state['hi']} of {hi_end}")
            last = max(tail) if tail else ns[-1]
            if state["hi"] - last >= max_gap:
                state["lost_at"] = last
                break
            if going:
                yield link
        # 3. back from the first mark, the same way
        k = ns[0] - 1
        while going and k >= lo_end:
            going = run(range(k, max(k - block, lo_end - 1), -1))
            k = state["lo"] - 1
            link, head, _ = snapshot(say=f"linking at {kind}: back from the first mark, frame {state['lo']} of {lo_end}")
            first = min(head) if head else ns[0]
            if first - state["lo"] >= max_gap:
                state["lost_before"] = first
                break
            if going:
                yield link
        yield snapshot("done")[0]
    finally:
        workers.close()


def track_from_marks(clip, marks, say=None, **kw):
    """`link_from_marks` run to its end, for a command or a script. `say` is called
    with a line each time the stage changes, and with the summary."""
    last, stage = None, None
    for last in link_from_marks(clip, marks, **kw):
        if say and (last.stage != stage or last.done):
            say(last.say)
        stage = last.stage
    return last


def track_from_marks_file(clip, marks_json, out_prefix, cls="object", say=print, **kw):
    """For a command's `--marks FILE`: the link, run to its end, and its track and
    strip written beside the command's other results. Returns the track, or
    None with the reason said."""
    from .mark import MarkSet
    ms = MarkSet(Path(marks_json).stem, clip.video, clip.fps).load(marks_json)
    marks = {n: xy for n, xy in ms.marks.get(cls, {}).items() if clip.n0 <= n <= clip.n1}
    if not marks:
        say(f"--marks: {marks_json} has no '{cls}' marks on frames {clip.n0}-{clip.n1}")
        return None
    snapped = [n for n in marks if ms.how_of(cls, n)]
    say(f"--marks: linking from {len(marks)} mark{'s' if len(marks) != 1 else ''} on "
        f"{', '.join(map(str, sorted(marks)))}" + (f" ({len(snapped)} snapped to the detector, not placed by hand)" if snapped else ""))
    link = track_from_marks(clip, marks, say=lambda line: say(f"  {line}"), **kw)
    if not link.track:
        return None
    path = write_track_csv(f"{out_prefix}_autotrack.csv", link, clip.video, clip.fps)
    shown = vf.track_strip(clip, link.track, f"{out_prefix}_autotrack_strip.png")
    say(f"wrote {path}. CHECK {out_prefix}_autotrack_strip.png (frames {shown[0]}..{shown[-1]}) before trusting it.")
    return link.track


def write_track_csv(path, link, video, fps):
    """The automatic track as a CSV the other commands read, saying where it came from."""
    if not link or not link.track:
        return None
    marks = ", ".join(f"{n} ({x:.2f}, {y:.2f})" for n, (x, y) in sorted(link.marks.items()))
    res = ", ".join(f"{n}: {'no link' if d is None else f'{d:.1f} px'}" for n, d in link.residuals.items())
    arr = ", ".join(f"{n}: {'does not reach it' if d is None else f'{d:.1f} px'}" for n, d in link.arrivals.items())
    d = link.disputed()
    with open(path, "w", newline="") as f:
        f.write(f"# automatic track on {Path(video).name}, linked from hand marks by mcdonald.autolink\n")
        f.write(f"# source_candidates(size={link.size:g}, dark={link.dark}, min_resp={MIN_RESP:g}); link_track forward and "
                f"backward from each mark, velocity from neighbouring marks; marks: {marks}\n")
        f.write(f"# distance from each hand mark -- {res}\n")
        if arr:
            f.write(f"# the forward link from the mark before arrives at -- {arr}\n")
        f.write(f"# disputed frames, where the forward and backward links disagree: "
                f"{', '.join(map(str, d)) if d else 'none'}\n")
        ends = [f"lost going back from frame {link.lost_before}" if link.lost_before is not None else
                f"searched back to frame {link.n_lo}",
                f"lost after frame {link.lost_at}" if link.lost_at is not None else f"searched on to frame {link.n_hi}"]
        f.write(f"# {'; '.join(ends)}{'; stopped before it had finished' if link.stopped else ''}\n")
        f.write("# CHECK the track strip before building anything on this\n")
        f.write("frame,t_s,x_px,y_px,source\n")
        for n in sorted(link.track):
            x, y = link.track[n]
            f.write(f"{n},{round((n - 1) / fps, 4)},{round(x, 2)},{round(y, 2)},{link.source.get(n, '')}\n")
    return path
