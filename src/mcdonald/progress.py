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

A pool has a worker for every CPU this process may use, to MOST_WORKERS and as far as
memory allows (`workers`), unless a caller asks for fewer; `procs=0` runs the same work in
this process, which is how a test holds the pooled result against the plain one.
"""
import contextlib
import multiprocessing
import os
import sys
import time
from collections import deque


class Stopped(Exception):
    """Someone asked for the step under way to stop, and it did."""


def cpus(allowed=True):
    """The CPUs this process may run on -- which under a batch scheduler is the allocation,
    not the machine. `os.cpu_count()` says 12 inside a four-CPU Slurm job, and ten worker
    processes on four CPUs finish no sooner and take ten processes' memory. The affinity
    mask is what a cgroup or `taskset` leaves; SLURM_CPUS_PER_TASK covers a site that
    confines jobs some other way. MCDONALD_CPUS is the most a person allows (`mcdonald --cpus N`, or
    Preferences in the window): never more than there are, and the least of the three wins; with
    `allowed` False it is left out, which is what a person may choose from."""
    try:
        n = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):                 # not Linux
        n = os.cpu_count() or 1
    for name in ("SLURM_CPUS_PER_TASK", CPUS_VAR) if allowed else ("SLURM_CPUS_PER_TASK",):
        asked = os.environ.get(name, "").strip()
        if asked.isdigit() and int(asked) > 0:
            n = min(n, int(asked))
    return max(1, n)


CPUS_VAR = "MCDONALD_CPUS"


def limit_cpus(n):
    """Allow pools at most `n` CPUs from now on, in this process and every one it starts; None or 0 lifts
    the limit. An `n` that is not a whole number above 0 is a mistake, said as a ValueError."""
    if n in (None, 0, "", "0"):
        os.environ.pop(CPUS_VAR, None)
        return
    if not str(n).strip().isdigit():
        raise ValueError(f"the number of CPU cores must be a whole number above 0, not {n!r}")
    os.environ[CPUS_VAR] = str(int(n))


def _text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _cgroup_left():
    """Bytes left under this process's cgroup memory limit (a batch job's, a container's), the
    tightest of its own and its parents'; None where there is none or it cannot be read. What
    the cgroup has used counts the frames read lately as cached file pages, which the kernel
    gives back when asked; the inactive ones are not counted as used."""
    try:
        lines = _text("/proc/self/cgroup").splitlines()
    except OSError:
        return None
    left = []
    for ln in lines:
        try:
            _, ctrl, path = ln.split(":", 2)
        except ValueError:
            continue
        if ctrl == "":                                          # cgroup v2: one tree
            root, limit, used, cache = "/sys/fs/cgroup", "memory.max", "memory.current", "inactive_file"
        elif "memory" in ctrl.split(","):                       # cgroup v1: the memory controller's tree
            root, limit, used, cache = ("/sys/fs/cgroup/memory", "memory.limit_in_bytes", "memory.usage_in_bytes",
                                        "total_inactive_file")
        else:
            continue
        parts = [p for p in path.split("/") if p]
        for i in range(len(parts), -1, -1):
            d = os.path.join(root, *parts[:i])
            try:
                cap = _text(os.path.join(d, limit)).strip()
                now = int(_text(os.path.join(d, used)).strip())
            except (OSError, ValueError):
                continue
            if not cap.isdigit() or int(cap) >= 2 ** 60:            # "max", or v1's "no limit" (a page short of 2**63)
                continue
            try:
                stat = dict(row.split() for row in _text(os.path.join(d, "memory.stat")).splitlines() if len(row.split()) == 2)
                now -= int(stat.get(cache, 0))
            except (OSError, ValueError):
                pass
            left.append(int(cap) - now)
    return max(0, min(left)) if left else None


def free_memory():
    """Bytes this process may still take: what the system says is available, or what is left under
    a batch job's (or a container's) own limit if that is less. None where neither can be read."""
    free = None
    try:
        if sys.platform.startswith("linux"):
            for ln in _text("/proc/meminfo").splitlines():
                if ln.startswith("MemAvailable:"):
                    free = int(ln.split()[1]) * 1024
                    break
        elif sys.platform == "win32":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = MemoryStatus()
            m.dwLength = ctypes.sizeof(MemoryStatus)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                free = int(m.ullAvailPhys)
        else:                                                   # macOS: what is free is not one number; half of all of it
            free = os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") // 2
    except Exception:                                           # a guess at the room, never a reason a pool fails
        free = None
    try:
        capped = _cgroup_left()
    except Exception:
        capped = None
    if capped is not None:
        free = capped if free is None else min(free, capped)
    return free


# What one worker process holds at its worst, by the frame size it works on: the modules and its share of
# the fork server's pages (BASE), and per pixel of a frame the frames it keeps (`clip._load` holds six) and a
# registration's arrays (PER_PIXEL). Measured 2026-10-09 on every pool of a Measure, a Find and a Follow
# (the resident set, sampled four times a second): at 1920 x 1080 (PR113) the worst was integrity's
# background pass, 399 MiB (layers 391, Find 307, the link 248), at 1280 x 720 (PR135) layers', 216 MiB --
# 70 MiB and 167 bytes a pixel. A quarter more than that:
WORKER_BASE = 100 * 2 ** 20
WORKER_PER_PIXEL = 200
SPARE = 0.8         # of the memory free when a pool starts, the share its workers may take


# The most worker processes a pool has when nobody has said how many. Measured on arthur (48 cores, 96 threads),
# 2026-11-13, whole `mcdonald run`s of three reference objects at 8 to 88 workers, with the graphics card and
# without: 32 to 48 workers were the fastest on every one, and 64 or 88 slower by up to 15 % (each worker's start
# and its own reading of the frames, at every pool of a Measure, for no more arithmetic done at once). Under 32 a
# worker for each hardware thread is the right count: in a job of 4 or 8 whole cores, two workers a core beat one a
# core by 5 to 20 %. A person's own number (`--cpus`, MCDONALD_CPUS, Preferences, `--procs`) is not held to it.
MOST_WORKERS = 32


def default_workers(allowed=True):
    """How many worker processes a pool has when no caller says: one for every CPU this process may run on (`cpus`),
    to MOST_WORKERS unless a person allowed more (MCDONALD_CPUS: theirs is the count). With `allowed` False, what it
    is when no person has said, which is what Preferences shows as its default."""
    n = cpus(allowed)
    return n if allowed and os.environ.get(CPUS_VAR, "").strip() else min(n, MOST_WORKERS)


def workers(procs=None, pixels=None):
    """How many worker processes a pool gets: `default_workers`, or `procs` if a caller says (never more than
    there are CPUs to run them on) -- and never more than the memory free has room for, at what a worker holds
    for frames of `pixels` (1920 x 1080 if not said). At least one; and 0 when `procs` is 0, which callers take
    to mean "in this process, no pool"."""
    if procs == 0:
        return 0
    n = default_workers() if procs is None else max(1, min(int(procs), cpus()))
    free = free_memory()
    if free is not None:
        each = WORKER_BASE + WORKER_PER_PIXEL * (pixels or 1920 * 1080)
        n = min(n, max(1, int(SPARE * free // each)))
    return n


PROCS_HELP = ("worker processes (default: one for each CPU this process may use -- a batch job's allocation, not the "
              f"machine -- to {MOST_WORKERS} unless `mcdonald --cpus` allows more, and as far as memory allows)")


def chunk(jobs, size, most=1):
    """How many jobs a worker takes at once: `most` (what a stage's reuse of one job's frames in the
    next wants), but few enough that each of `size` workers has some -- 60 pairs in eights would
    leave all but eight of 32 workers idle."""
    return max(1, min(int(most), -(-int(jobs) // max(int(size), 1))))


# The modules whose functions run in the pools' workers, imported once in the fork server so that every
# worker of every pool is forked with them: without this each worker imports numpy, scipy and the package
# afresh -- 2.9 s a pool on this machine (Python 3.14 starts workers by forkserver; macOS spawns them),
# and a Measure starts a dozen pools.
WORKER_MODULES = ["mcdonald.forensics", "mcdonald.layers", "mcdonald.propose", "mcdonald.integrity",
                  "mcdonald.tracksheet", "mcdonald.groups", "mcdonald.flicker", "mcdonald.symbology",
                  "mcdonald.autolink", "mcdonald.comotion", "mcdonald.stabilize"]
_context = None


def context():
    """The multiprocessing context every pool of the package is made from. Never fork: the caller may be
    a window with threads running, and a forked child inherits their locks as they were. A fork server
    where there is one (Linux, macOS), told to import the worker modules once before it forks anything
    (0.05 s a pool after the first, against 2.9); spawn on Windows, which has no fork server."""
    global _context
    if _context is None:
        if sys.platform == "win32":
            _context = multiprocessing.get_context("spawn")
        else:
            _context = multiprocessing.get_context("forkserver")
            _context.set_forkserver_preload(WORKER_MODULES)
    return _context


# numpy's and scipy's own threads (OpenBLAS, OpenMP, MKL, Accelerate): one in each worker. The pool's
# processes are the parallelism; a worker whose OpenBLAS starts a thread for every CPU of the machine, times
# a worker for every CPU, is thousands of threads. The batch scripts said so in their environment; a person
# at the window has nobody to say it for them.
ONE_THREAD = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")


@contextlib.contextmanager
def _one_thread_each():
    """The environment a process started now starts in, with one thread each for the libraries; this
    process's own is put back after."""
    old = {k: os.environ.get(k) for k in ONE_THREAD}
    os.environ.update({k: "1" for k in ONE_THREAD})
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


_server_told = False


def new_pool(n, init=None, initargs=()):
    """A pool of `n` worker processes from `context()`, each with one thread for numpy's and scipy's own.
    The libraries read that from the environment as they load: on Windows as each worker starts, and
    elsewhere once, in the fork server every worker is forked from, as it starts with the first pool. So
    the environment is changed for that moment only -- once a process outside Windows, since changing it
    while the window's other threads read theirs is a risk worth taking once, not at every pool."""
    global _server_told
    if sys.platform != "win32" and _server_told:
        return context().Pool(max(1, int(n)), init, initargs)
    with _one_thread_each():
        pool = context().Pool(max(1, int(n)), init, initargs)
    _server_told = True
    return pool


def pool_of(procs, init=None, initargs=(), pixels=None):
    """A pool of as many processes as `workers` allows: no more than there are CPUs to run them
    on, nor than memory has room for at frames of `pixels`, whatever was asked for."""
    return new_pool(workers(procs, pixels) or 1, init, initargs)


def size_of(pool):
    """How many workers a pool has; 0 for none (the work is done in this process)."""
    return 0 if pool is None else getattr(pool, "_processes", None) or 1


def streamed(pool, fn, jobs, chunksize=1, progress=None, stop=None, what="", ahead=None):
    """fn of each job, in order, as each comes back from `pool` (None: in this process), saying how
    far it has got after every item and asking `stop` whether to go on -- when it says yes the pool
    is ended and `Stopped` raised. `chunksize` is the most jobs a worker takes at once (`chunk`).
    With `ahead`, no more than that many jobs are out at a time: for results as large as a frame,
    which would otherwise pile up here while this process works through them in order."""
    jobs = list(jobs)
    total = len(jobs)
    if progress:
        progress(what, 0, total)
    if pool is None:
        results = map(fn, jobs)
    elif ahead:
        results = _ahead(pool, fn, jobs, ahead)
    else:
        results = pool.imap(fn, jobs, chunk(total, size_of(pool), chunksize))
    for i, r in enumerate(results, 1):
        if progress:                                    # as each comes back, not when the next is asked for: a caller
            progress(what, i, total)                    # that takes a block at a time asks for no more after its last
        if stop is not None and stop():
            if pool is not None:
                pool.terminate()
            raise Stopped(what)
        yield r


_END = object()


def _ahead(pool, fn, jobs, ahead):
    """`pool.imap(fn, jobs)` with no more than `ahead` jobs given out and not yet taken back."""
    out, it = deque(), iter(jobs)
    for job in it:
        out.append(pool.apply_async(fn, (job,)))
        if len(out) >= ahead:
            break
    while out:
        r = out.popleft().get()
        job = next(it, _END)
        if job is not _END:
            out.append(pool.apply_async(fn, (job,)))
        yield r


def pooled(procs, fn, jobs, init=None, initargs=(), chunksize=1, progress=None, stop=None, what="", pool=None,
           pixels=None):
    """`Pool(procs, init, initargs).map(fn, jobs)`, in order, saying how far it has got
    after every item and asking `stop` whether to go on. As many processes as `workers`
    allows (None: one a CPU, as memory allows for frames of `pixels`); `procs=0` does the work
    in this process, `init` first. `chunksize` is the most jobs a worker takes at once, and
    fewer when there are too few to go round (`chunk`). With `pool`, that pool (made by
    `pool_of`, its workers already initialised) does the work and is left open: a caller
    with several rounds of jobs makes one pool, not one a round."""
    jobs = list(jobs)
    if pool is None and workers(procs, pixels) == 0:
        if init is not None:
            init(*initargs)
        return list(streamed(None, fn, jobs, chunksize, progress, stop, what))
    p = pool or pool_of(procs, init, initargs, pixels)
    try:
        return list(streamed(p, fn, jobs, chunksize, progress, stop, what))
    finally:
        if pool is None:
            p.terminate()                                 # what `with Pool()` did: the workers are ended, not waited for
            p.join()


READERS = 16        # the most threads that read ahead: past this a card's loop is not waiting for frames


class Ahead:
    """What `read(key)` gives for each key of `asks`, read by threads before a loop in this process asks for it.

    Where a graphics card does a stage's arithmetic, the stage runs in this one process (`gpu.card`), and what is left
    for the CPUs is reading the frames: decoding a 1080p picture and masking it is 30 ms and more, the card's share
    of a pair of frames less than that. `asks` is every key the loop will ask for, in its order and as often as it
    will ask (a frame is the second of one pair and the first of a later one). `get(key)` gives the next: threads
    have read up to `depth` keys ahead of it, a key asked for again is not read again, and one is let go after its
    last asking. A key that was not foreseen is read there and then. As many threads as `cpus()` allows, to READERS."""

    def __init__(self, read, asks, threads=None, depth=None):
        from concurrent.futures import ThreadPoolExecutor
        self.read = read
        self.left = {}                                # each key: how often it will still be asked for
        for key in asks:
            self.left[key] = self.left.get(key, 0) + 1
        self.order = iter(list(self.left))            # the keys, each once, in the order they are first asked for
        n = max(1, min(int(threads or cpus()), READERS))
        self.depth = int(depth or 2 * n)
        self.pool = ThreadPoolExecutor(n, thread_name_prefix="mcdonald-read")
        self.out = {}                                 # each key read or being read, until its last asking
        self.fresh = set()                            # those of them not asked for yet: the reads ahead of the loop
        self._more()

    def _start(self, key):
        self.out[key] = self.pool.submit(self.read, key)
        self.fresh.add(key)

    def _more(self):
        while self.pool is not None and len(self.fresh) < self.depth:
            key = next(self.order, _END)
            if key is _END:
                return
            self._start(key)

    def get(self, key):
        if self.left.get(key, 0) <= 0 or self.pool is None:
            return self.read(key)                     # not foreseen, or asked for once more than was said
        while key not in self.out:                    # further on than the reads have got: bring them up to it
            nxt = next(self.order, _END)
            if nxt is _END:
                return self.read(key)
            self._start(nxt)
        self.fresh.discard(key)
        value = self.out[key].result()
        self.left[key] -= 1
        if self.left[key] <= 0:
            del self.out[key]
        self._more()
        return value

    def close(self):
        """The threads ended, and what they had read let go; reads not yet begun are not made."""
        pool, self.pool = self.pool, None
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)
        self.out.clear()
        self.fresh.clear()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


BESIDE = 8          # the most threads that work beside a stage's own: its side jobs are few (a control aperture each)


class Beside:
    """A stage's own side jobs, done beside its main work in threads of this process: `call(fn, ...)` starts one and
    gives back what will hold its answer, `.result()` waits for it (and raises what it raised).

    For arithmetic that is one job's worth of NumPy or SciPy on a whole track or a whole frame -- a drawn null of
    thousands of spectra, a frame's filters -- where the libraries let the interpreter go while they work, so two such
    jobs take the time of one (measured 2026-11-13: SciPy's filters, a median and NumPy's larger loops run 3.3 to 4.7
    times sooner on 8 threads of 4 cores). Not a pool: nothing is pickled or sent, no process starts, and each job is
    the same function on the same arguments as it would have been in line, so its numbers are the same to the bit.
    Each job runs in a copy of the caller's context (a measurement's own settings: `flicker`'s rule). With `threads`
    0, or where this process has one CPU, a job is done there and then, in line. As many threads as `cpus()` allows,
    to BESIDE."""

    def __init__(self, threads=None):
        from concurrent.futures import ThreadPoolExecutor
        n = min(cpus(), BESIDE) if threads is None else int(threads)
        self.pool = ThreadPoolExecutor(n, thread_name_prefix="mcdonald-beside") if n > 1 else None

    def call(self, fn, *args, **kw):
        import contextvars
        from concurrent.futures import Future
        if self.pool is not None:
            return self.pool.submit(contextvars.copy_context().run, fn, *args, **kw)
        f = Future()
        try:
            f.set_result(fn(*args, **kw))
        except Exception as e:                        # kept for `.result()`, as a thread's would be
            f.set_exception(e)
        return f

    def close(self):
        if self.pool is not None:
            self.pool.shutdown(wait=False, cancel_futures=True)
            self.pool = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


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
