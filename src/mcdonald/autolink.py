"""From a few hand marks to an automatic track -- and whether it is on the object.

`mcdonald mark` ends with two clicks. What they are for is the linker: the
first is its seed, the pair is the velocity it cannot acquire alone. This is
the step between, with no window in it, so it is tested headless and either
front end, or a script, can drive it.

1. Choose the detector's scale and polarity *from the marks* (`pick_detector`).
   The matched filter is tuned to one size and misses an object much larger
   than it outright: PR113's 25 px object is 71 px from the nearest candidate
   at the 9 px default and 1.9 px away at 21. A mark says where to look, so
   the sweep is easy to judge: the scale, in whichever polarity, whose
   candidate sits closest to the marks.
2. Run the detector forward from the first mark, exactly as `layers
   --auto-track` does (`forensics.frame_candidates`) -- on a process pool,
   because it costs 0.8 s a 1080p frame at 9 px and 4 s at 21.
3. Link with `forensics.link_track`, seeded and primed from the marks.
4. Hold the result against every hand mark, the ones it was not seeded from
   above all. That distance is the first answer to "did it lock onto the
   object?". The second is looking, which is what the track strip is for.

`link_from_marks` is a generator: it yields a `Link` after every step, so a
caller can draw the track as it grows and stop it when it has seen enough. A
whole clip at 21 px is ten minutes; nobody should have to wait for it to find
out that the track left the object in the first second.

It stops by itself when the object has been lost for `max_gap` frames. Past
that point `link_track` starts again on the strongest candidate in the frame,
which is no longer the thing that was marked, and drawing it would be showing
a track of something else under the object's name.
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
    seed: tuple = None
    velocity: tuple = None
    size: float = None
    dark: bool = None
    n_from: int = None
    n_done: int = None
    n_to: int = None
    lost_at: int = None                          # last linked frame, if it stopped because the object was lost
    residuals: dict = field(default_factory=dict)   # {marked frame: px from the track, or None where it has no link}
    sweep: list = field(default_factory=list)       # [(dark, size, [px to each mark shown])], the record of the choice
    masks: dict = None
    done: bool = False

    def worst(self):
        """The largest distance from a hand mark, or None if any mark has no link under it."""
        if not self.residuals or any(v is None for v in self.residuals.values()):
            return None
        return max(self.residuals.values())


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

    def imap(self, jobs):
        return self.pool.imap(_detect, jobs) if self.pool else map(_detect, jobs)

    def close(self):
        if self.pool:
            self.pool.terminate()
            self.pool.join()


def default_procs():
    return max(1, min(8, (os.cpu_count() or 2) - 2))


# ---- the choice of detector -------------------------------------------------------------
def _nearest(cands, xy):
    return min((float(np.hypot(c[0] - xy[0], c[1] - xy[1])) for c in cands), default=float("inf"))


def pick_detector(workers, marks, sizes=SIZES, tol=6.0, gain=0.5):
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
        got = {(n, d): c for n, _, d, c in workers.imap([(n, float(s), d) for d in (False, True) for n in shown])}
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
def _residuals(track, marks):
    return {n: (float(np.hypot(track[n][0] - xy[0], track[n][1] - xy[1])) if n in track else None)
            for n, xy in sorted(marks.items())}


def link_from_marks(clip, marks, masks=None, rows=None, n_to=None, size=None, dark=None,
                    sizes=SIZES, tol=6.0, procs=None, max_gap=40, stop=None):
    """Hand marks {frame: (x, y)} -> an automatic track forward from the first.

    A generator of `Link`s; the last has `.done`. Give `size` to skip the
    choice of detector (and `dark`, else bright). `stop` is a callable polled
    between frames. `procs=0` runs the detector inline."""
    stop = stop or (lambda: False)
    ns = sorted(marks)
    if not ns:
        yield Link("done", "no marks: the first mark is where the link starts", done=True)
        return
    seed = (ns[0], *marks[ns[0]])
    velocity = vf.velocity_from_marks(marks)
    n_to = int(min(n_to or clip.n1, clip.n1))
    base = dict(seed=seed, velocity=velocity, n_from=seed[0], n_to=n_to)

    if masks is None:
        yield Link("masks", "building the static masks, once per clip…", **base)
        masks = vf.static_masks(clip)
    base["masks"] = masks

    workers = _Workers(clip, masks, rows, default_procs() if procs is None else procs)
    try:
        sweep = []
        if size is None:
            yield Link("scale", "choosing the detector's scale from the marks…", **base)
            picking = pick_detector(workers, marks, sizes, tol)
            try:
                while True:
                    say, sweep = next(picking)
                    yield Link("scale", say, sweep=list(sweep), **base)
                    if stop():
                        yield Link("done", "stopped while choosing the detector", sweep=list(sweep), done=True, **base)
                        return
            except StopIteration as found:
                size, dark, sweep = found.value
            if size is None:
                d, s, dist = min(sweep, key=lambda r: max(r[2]))
                yield Link("done", f"no detector scale from {sizes[0]} to {sizes[-1]} px puts a candidate within {tol:g} px "
                           f"of the marks (closest: {max(dist):.0f} px away at {s} px, {'dark' if d else 'bright'}). "
                           "Nothing was linked.", sweep=sweep, done=True, **base)
                return
        dark = bool(dark)
        base.update(size=size, dark=dark, sweep=sweep)
        kind = f"{size:g} px, {'dark' if dark else 'bright'}"

        cands, track, n, lost = {}, {}, seed[0] - 1, None
        frames = range(seed[0], n_to + 1)
        for n, _, _, c in workers.imap([(k, size, dark) for k in frames]):
            cands[n] = c
            track = vf.link_track(cands, seed[0], n, seed, velocity, max_gap=max_gap)
            last = max(track) if track else seed[0]
            if n - last >= max_gap:                  # one more frame and link_track would start again on something else
                lost = last if track else seed[0]
                break
            if stop():
                break
            yield Link("linking", f"linking at {kind}: frame {n} of {n_to}, {len(track)} linked",
                       track=dict(track), n_done=n, residuals=_residuals(track, marks), **base)
        res = _residuals(track, marks)
        end = Link("done", "", track=dict(track), n_done=n, lost_at=lost, residuals=res, done=True, **base)
        if not track:
            end.say = (f"never acquired at {kind}: no candidate came within the gate of the prediction in "
                       f"{n - seed[0] + 1} frames")
        else:
            a, b = min(track), max(track)
            how = (f"lost: nothing within the gate for {max_gap} frames" if lost is not None else
                   f"stopped at frame {n}" if n < n_to else f"searched to frame {n}, the end")
            w = end.worst()
            against = ("a hand mark has no link under it" if w is None else
                       f"within {w:.1f} px of {'the mark' if len(res) == 1 else f'all {len(res)} marks'}")
            end.say = f"{len(track)} of {b - a + 1} frames linked, {a}–{b}, at {kind}; {against}; {how}"
        yield end
    finally:
        workers.close()


def write_track_csv(path, link, video, fps):
    """The automatic track as a CSV the other commands read, saying where it came from."""
    if not link or not link.track:
        return None
    v = link.velocity
    seed = (link.seed[0], round(link.seed[1], 2), round(link.seed[2], 2))
    res = ", ".join(f"{n}: {'no link' if d is None else f'{d:.1f} px'}" for n, d in link.residuals.items())
    with open(path, "w", newline="") as f:
        f.write(f"# automatic track on {Path(video).name}, linked forward from hand marks by `mcdonald mark`\n")
        f.write(f"# source_candidates(size={link.size:g}, dark={link.dark}, min_resp={MIN_RESP:g}); link_track(seed={seed}, "
                f"velocity={None if v is None else (round(v[0], 2), round(v[1], 2))})\n")
        f.write(f"# distance from each hand mark -- {res}\n")
        if link.lost_at is not None:
            f.write(f"# stopped: lost after frame {link.lost_at}\n")
        f.write("# CHECK the track strip before building anything on this\n")
        f.write("frame,t_s,x_px,y_px\n")
        for n in sorted(link.track):
            x, y = link.track[n]
            f.write(f"{n},{round((n - 1) / fps, 4)},{round(x, 2)},{round(y, 2)}\n")
    return path
