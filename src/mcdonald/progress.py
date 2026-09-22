"""Saying how far along a long step is, and stopping one, with no interface in it.

The measuring stages are minutes long and were silent: `Pool.map` says nothing
until it returns, so a person at the window (and one at a terminal) could not tell
a stage that was working from one that had hung. Every long loop now goes through
`pooled` or calls `progress` itself, and the two shells show it their own way: the
window as a bar with a count, the time gone and the time left; the command line as
`to_stderr` prints it.

    progress(text, done=None, total=None)

`text` names the step ("layers: frame pairs"). With `done` and `total` it is a
fraction; without, it is only "this has started" -- a step that cannot count is
shown as busy, never as a bar that does not move.

    stop()  ->  bool

asked between items. When it says yes the pool is ended and `Stopped` is raised:
a stage stops inside itself, not only between stages.
"""
import os
import sys
import time
from multiprocessing import Pool


class Stopped(Exception):
    """Someone asked for the step under way to stop, and it did."""


def cpus():
    """The CPUs this process may run on -- which under a batch scheduler is the allocation,
    not the machine. `os.cpu_count()` says 12 inside a four-CPU Slurm job, and ten worker
    processes on four CPUs finish no sooner and take ten processes' memory. The affinity
    mask is what a cgroup or `taskset` leaves; SLURM_CPUS_PER_TASK covers a site that
    confines jobs some other way."""
    try:
        n = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):                 # not Linux
        n = os.cpu_count() or 1
    asked = os.environ.get("SLURM_CPUS_PER_TASK", "")
    return max(1, min(n, int(asked)) if asked.isdigit() and int(asked) > 0 else n)


def pooled(procs, fn, jobs, init=None, initargs=(), chunksize=1, progress=None, stop=None, what=""):
    """`Pool(procs, init, initargs).map(fn, jobs)`, in order, saying how far it has got
    after every item and asking `stop` whether to go on. No more processes than there are
    CPUs to run them on (`cpus`), whatever was asked for."""
    jobs = list(jobs)
    total, out = len(jobs), []
    if progress:
        progress(what, 0, total)
    with Pool(max(1, min(procs, cpus())), init, initargs) as p:
        for r in p.imap(fn, jobs, chunksize):
            out.append(r)
            if progress:
                progress(what, len(out), total)
            if stop is not None and stop():
                p.terminate()
                raise Stopped(what)
    return out


def counted(items, progress=None, stop=None, what=""):
    """A plain loop's items, with the same two courtesies."""
    items = list(items)
    if progress:
        progress(what, 0, len(items))
    for i, x in enumerate(items, 1):
        yield x
        if progress:
            progress(what, i, len(items))
        if stop is not None and stop():
            raise Stopped(what)


def left(done, total, seconds):
    """Seconds still to go at the rate so far, or None while it is too early to say."""
    if not total or done < 3 or seconds < 2.0 or done >= total:
        return None
    return seconds / done * (total - done)


def clock(seconds):
    """1:05, or 1:02:03."""
    s = int(round(seconds))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def to_stderr(stream=None, every=10.0):
    """A `progress` for a command line. Each new step is a line, `[   42 s] name`, as
    `integrity` always printed. A count is kept up to date in place on a terminal; where
    stderr is a file or a pipe it is said every `every` seconds, so that a step of a
    second is one line and a step of an hour is not thousands."""
    stream = stream or sys.stderr
    tty = hasattr(stream, "isatty") and stream.isatty()
    t0, state = time.time(), dict(text=None, began=0.0, said=0.0, open=False)

    def progress(text, done=None, total=None):
        now = time.time()
        if text != state["text"]:
            if state["open"]:
                stream.write("\n")
            state.update(text=text, began=now, said=now, open=False)
            stream.write(f"[{now - t0:6.0f} s] {text}\n")
        if total:
            eta = left(done, total, now - state["began"])
            line = f"           {done} of {total}" + (f", about {clock(eta)} left" if eta is not None else "")
            if tty:
                stream.write("\r" + line.ljust(60) + ("\n" if done >= total else ""))
                state["open"] = done < total
            elif now - state["said"] >= every:
                state["said"] = now
                stream.write(line + "\n")
        stream.flush()
    return progress
