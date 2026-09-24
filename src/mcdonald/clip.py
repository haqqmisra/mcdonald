"""Opening a clip, and deciding where its results go.

Conventions the whole package depends on
- Frame numbers are ffmpeg's, 1-based: t = (n - 1) / fps.
- fps is an exact rational from ffprobe. Most sensor clips that present as
  "30 fps" are really 30000/1001, and a rounded 30 drifts a frame every ~33 s.
  Never round it, and never take it from a catalog column.
- A shift (dx, dy) is where the content of frame a is found in frame b.
"""
import json
import os
import shutil
import subprocess
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from . import catalog as _catalog
from . import storage


class MissingTool(RuntimeError):
    pass


# What `mcdonald` exits with. 1 is left to Python: an uncaught exception, which is a bug.
# The others are failures the package expected and explains, so that something driving it
# from a script can tell "the clip is not there" from "mcdonald is broken".
EXIT_USAGE, EXIT_MISSING, EXIT_INPUT, EXIT_NOTHING = 2, 3, 4, 5
EXIT_CODES = """exit codes
  0  done
  1  a bug: a Python traceback, which should be reported
  2  the command line was wrong: an unknown command or option
  3  this machine lacks something: ffmpeg, or a window to open
  4  the input is not there, is not a video, or is a record id that resolves to none or several
  5  nothing to work on: no marks or track on these frames, or the link acquired nothing
"""


class Stop(SystemExit):
    """An expected failure: what to tell the person, and what to exit with. A SystemExit,
    so that a script calling into the package still stops with the message; the command
    line catches it for the code."""

    def __init__(self, message, exit_code=EXIT_INPUT):
        super().__init__(message)
        self.exit_code = exit_code


class NotAVideo(RuntimeError):
    """ffprobe could not read it, or there is no video stream in it."""


def require_ffmpeg():
    """ffmpeg and ffprobe are hard requirements and cannot be pip-installed.

    Checked up front so a run fails in the first second with an actionable
    message rather than deep inside frame extraction."""
    missing = [t for t in ("ffmpeg", "ffprobe") if shutil.which(t) is None]
    if missing:
        raise MissingTool(
            f"mcdonald reads videos with ffmpeg, and {' and '.join(missing)} was not found on this computer (it is not "
            "on the PATH). Install it (for example `dnf install ffmpeg`, `apt install ffmpeg` or "
            "`brew install ffmpeg`) and try again.")


# ---- finding a clip -------------------------------------------------------------------
class Declined(Stop):
    """The person was asked whether to download a video, and said no."""


def resolve(arg, fetch=None):
    """A path, or a catalog record id such as DOW-UAP-PR144 / PR144 / 06:PR001.

    Returns (path, tag, record-or-None). `tag` is a short lowercase label used
    for output filenames: the record id where there is one, else the filename
    stem. A path always works; ids resolve in the catalog (see mcdonald.catalog).

    A record whose file is not on this computer, and that says where it can be
    had, is downloaded into the storage folder: `fetch(record, dest)` does it
    and returns dest, or None if the person would rather not (the window asks
    first, and shows how far along it is); by default it is fetched with its
    progress on stderr."""
    cat = _catalog.active()
    p = Path(arg).expanduser()
    if p.exists():
        rec = cat.by_path(p)
        return p, ((rec.get("id") or p.stem).lower() if rec else p.stem.lower()), rec

    release, _, key = arg.rpartition(":")
    hits = cat.by_id(key, release.zfill(2) if release else None)
    if len(hits) == 1:
        rec = hits[0]
        path = Path(rec["path"])
        if not path.exists() and rec.get("url"):
            try:
                got = (fetch or storage.download_on_terminal)(rec, path)
            except OSError as ex:
                raise Stop(f"{arg} is not on this computer, and could not be downloaded from {rec['url']}: {ex}")
            if got is None:
                raise Declined(f"{arg} was not downloaded.")
        return path, (rec.get("id") or path.stem).lower(), rec
    if not hits and isinstance(cat, _catalog.NullCatalog):
        raise Stop(
            f"{arg}: no such file, and no catalog has been chosen to look that name up in.\n"
            "Give the path to the video file, or set MCDONALD_CATALOG to a records.csv "
            "(see mcdonald.catalog).")
    if not hits:
        raise Stop(f"{arg}: no such file, and no video with that name in the {cat.label} catalog.")
    raise Stop(
        f"{arg}: {len(hits)} videos in the {cat.label} catalog have that name"
        + "".join(f"\n  {r.get('release', '')}:{(r.get('title') or '')[:70]}" for r in hits)
        + ("\n(say which one as RELEASE:NAME, such as 06:PR001)" if hits else ""))


# ---- where results go -----------------------------------------------------------------
def case_dir(out, tag, create=True):
    """The directory this run's outputs belong in.

    --out DIR wins; else $MCDONALD_CASES/<tag>; else ./<tag> in the working
    directory. Never anywhere near the installed package: a tool must not write
    into its own source tree just because that is where the code lives."""
    if out:
        d = Path(out).expanduser()
    else:
        base = os.environ.get("MCDONALD_CASES", "").strip()
        d = (Path(base).expanduser() if base else Path.cwd()) / tag
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def out_prefix(out, tag):
    """Path prefix for this run's files: <case dir>/<tag>, so that a file keeps
    saying which clip it came from after someone copies it out of the folder."""
    return case_dir(out, tag) / tag


# ---- reading it -----------------------------------------------------------------------
def probe(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)],
                       capture_output=True, text=True)
    d = json.loads(r.stdout or "{}") if r.returncode == 0 else {}
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    if v is None:
        why = (r.stderr.strip().splitlines() or ["there is no video stream in it"])[-1]
        raise NotAVideo(f"{Path(video).name} is not a video ffmpeg can read: {why}")
    return {"width": int(v["width"]), "height": int(v["height"]),
            "fps": Fraction(v["r_frame_rate"]), "nb_frames": int(v.get("nb_frames", 0) or 0),
            "duration": float(d["format"].get("duration", 0)), "format": d["format"], "stream": v,
            "streams": d["streams"]}


def gop(video, fps, frames=600):
    """The codec's own rhythm, from the first `frames` frames' picture types (ffprobe, in the
    order they are shown): how often an I frame comes, how often an anchor (I or P) does, and
    the frequencies they beat at -- a brightness that follows the anchors is the codec's, not
    the object's (PR135: P every 4th frame, 30/4 = 7.49 Hz, which is where its points flicker).
    None where ffprobe gives no picture types.

    The frames are decoded to be typed, without the loop filter or the inverse transform (a
    quarter faster, and the types are the same): 600 frames of PR135 are 2.7 s. Each frame's
    type is the first thing on its own line; what else ffprobe prints about a frame (side
    data, "H.26[45] User Data Unregistered SEI message") is not a type."""
    r = subprocess.run(["ffprobe", "-v", "error", "-skip_loop_filter", "all", "-skip_idct", "all",
                        "-select_streams", "v:0", "-read_intervals", f"%+#{frames}",
                        "-show_frames", "-show_entries", "frame=pict_type", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True)
    types = "".join(ln[0] for ln in r.stdout.splitlines() if ln[:1] in ("I", "P", "B") and ln[1:2] in ("", ","))
    if not types:
        return None
    at = lambda kinds: [i for i, t in enumerate(types) if t in kinds]
    spacing = lambda idx: float(np.median(np.diff(idx))) if len(idx) > 1 else None
    i_period, anchor_period = spacing(at("I")), spacing(at("IP"))
    # the anchors' beat and its harmonics under Nyquist; of the I frames' only the fundamental -- its
    # harmonics at a GOP of 60 are every half hertz, near which any frequency is
    lines = sorted({round(k * fps / anchor_period, 3) for k in range(1, int(anchor_period))
                    if k * fps / anchor_period < fps / 2}) if anchor_period and anchor_period > 1 else []
    return dict(types=types[:60], frames_read=len(types), i_period=i_period, anchor_period=anchor_period,
                b_frames="B" in types, lines_hz=lines, i_hz=round(fps / i_period, 3) if i_period else None)


@lru_cache(maxsize=16)
def encoding(video, fps):
    """How the clip was encoded, for every command's envelope (`clip.encoding`): the codec, its
    profile, the pixel format, the bit rates, whether frames are reordered (B frames), and the
    GOP from the first 150 frames' types (`gop`) -- the codec's rhythm, a systematic for any
    brightness or step that repeats (flicker, hold-and-jump). An agent asked for it in the
    envelope, not only in `flicker`'s fields (PR135, item 23). About 0.7 s, once a process."""
    try:
        i = probe(video)
    except NotAVideo:
        return None
    s, f = i["stream"], i["format"]
    num = lambda v: int(v) if str(v or "").isdigit() else None
    return dict(codec=s.get("codec_name"), profile=s.get("profile"), pix_fmt=s.get("pix_fmt"),
                reorder_depth=num(s.get("has_b_frames")), bit_rate=num(s.get("bit_rate")), container_bit_rate=num(f.get("bit_rate")),
                container=f.get("format_name"), gop=gop(video, fps, frames=150))


class Clip:
    """Lossless frames of a clip (or of a frame window of it) on disk.

    workdir may be an existing dump made with `ffmpeg -vsync 0 <dir>/f%04d.png`
    (whole clip, numbered from 1); otherwise frames n0..n1 are extracted with
    their absolute numbers.

    extract=False opens the clip without extracting, for a caller that wants to
    show progress and offer a way out: a long clip is a minute or more of
    ffmpeg. `extracted()` says whether there is anything to do, `extract()`
    does it, `n_extracted()` counts."""

    def __init__(self, video, workdir=None, n0=None, n1=None, extract=True):
        self.video = Path(video)
        self.info = probe(video)
        self.fps = float(self.info["fps"])
        self.W, self.H = self.info["width"], self.info["height"]
        total = self.info["nb_frames"] or int(round(self.info["duration"] * self.fps))
        self.n0, self.n1 = n0 or 1, min(n1 or total, total)
        self.dir = Path(workdir) if workdir else storage.frames() / self.video.stem
        self.dir.mkdir(parents=True, exist_ok=True)
        self.pat = next((p for p in ("f%04d.png", "f%05d.png") if (self.dir / (p % self.n0)).exists()), "f%05d.png")
        if extract:
            self.extract()

    def extracted(self):
        return (self.dir / (self.pat % self.n0)).exists() and (self.dir / (self.pat % self.n1)).exists()

    def n_extracted(self):
        """How many of the window's frames are on disk. ffmpeg writes them in order, so
        this counts up from n0 and stops at the first that is missing."""
        n = self.n0
        while n <= self.n1 and (self.dir / (self.pat % n)).exists():
            n += 1
        return n - self.n0

    def cost(self, n0=None, n1=None):
        """What having frames n0..n1 on disk will take, before anything is extracted:
        how many are not there yet, about how many bytes they will be, and how much room
        there is where they go. A lossless 1080p frame is most of a megabyte, so a whole
        clip is easily a gigabyte -- and where the temporary directory is a tmpfs, as it
        is on Fedora, that gigabyte is memory.

        The size is an estimate: from the frames already there if there are any, else
        0.12 of the raw size, which is the middle of what five 1080p sensor clips came
        to (0.09 to 0.14)."""
        n0, n1 = n0 or self.n0, n1 or self.n1
        pat = self.pat
        have = [p for p in (self.dir / (pat % n) for n in range(n0, n1 + 1)) if p.exists()]
        sample = have[:: max(1, len(have) // 20)]
        per = (sum(p.stat().st_size for p in sample) / len(sample)) if sample else 0.12 * self.W * self.H * 3
        missing = (n1 - n0 + 1) - len(have)
        return {"frames": n1 - n0 + 1, "missing": missing, "bytes": int(missing * per),
                "free": shutil.disk_usage(self.dir).free, "dir": str(self.dir), "in_memory": _is_tmpfs(self.dir)}

    def extract(self, stop=None):
        """Extract the window if it is not there. `stop` is polled while ffmpeg runs;
        if it turns true ffmpeg is ended and False comes back. What it had written
        is left behind: the last frame is missing, so the next run starts over."""
        if self.extracted():
            return True
        sel = f"select='between(n,{self.n0 - 1},{self.n1 - 1})'"
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(self.video), "-vf", sel, "-vsync", "0",
               "-start_number", str(self.n0), str(self.dir / self.pat)]
        if stop is None:
            subprocess.run(cmd, check=True)
            return True
        p = subprocess.Popen(cmd)
        while p.poll() is None:
            if stop():
                p.terminate()
                p.wait()
                return False
            try:
                p.wait(timeout=0.1)
            except subprocess.TimeoutExpired:
                pass
        if p.returncode:
            raise subprocess.CalledProcessError(p.returncode, cmd)
        return True

    def t(self, n):
        return (np.asarray(n) - 1) / self.fps

    def path(self, n):
        return self.dir / (self.pat % n)

    def rgb(self, n):
        return _load(str(self.path(n)))

    def grey(self, n):
        return self.rgb(n).mean(2)

    def frames(self):
        return range(self.n0, self.n1 + 1)


def _is_tmpfs(path):
    """Is this directory held in memory? Linux only; elsewhere, not as far as we know."""
    try:
        mounts = [ln.split() for ln in Path("/proc/mounts").read_text().splitlines()]
    except OSError:
        return False
    path = Path(path).resolve()
    under = [(len(m[1]), m[2]) for m in mounts if len(m) > 2 and (path == Path(m[1]) or Path(m[1]) in path.parents)]
    return bool(under) and max(under)[1] == "tmpfs"


def cost_text(c):
    """A Clip.cost() for people, one sentence. The window's range chooser and the
    command line say the same thing."""
    if not c["missing"]:
        return f"All {c['frames']} frames are already saved as pictures, in {c['dir']}."
    gb = 1024.0 ** 3
    size = f"{c['bytes'] / gb:.1f} GB" if c["bytes"] >= 0.1 * gb else f"{c['bytes'] / 1024.0 ** 2:.0f} MB"
    text = (f"{c['missing']} of {c['frames']} frames still have to be saved as pictures, with nothing lost. This is done "
            f"once, and takes about {size} in {c['dir']}"
            + (", a folder that is kept in the computer's memory and not on its disk" if c["in_memory"] else "")
            + f" ({c['free'] / gb:.1f} GB free).")
    if c["bytes"] > 0.8 * c["free"]:
        text += " That is more than there is room for: choose a shorter part."
    return text


@lru_cache(maxsize=6)
def _load(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    a.setflags(write=False)
    return a
