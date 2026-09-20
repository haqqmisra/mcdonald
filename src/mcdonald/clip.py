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
import tempfile
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from . import catalog as _catalog


class MissingTool(RuntimeError):
    pass


def require_ffmpeg():
    """ffmpeg and ffprobe are hard requirements and cannot be pip-installed.

    Checked up front so a run fails in the first second with an actionable
    message rather than deep inside frame extraction."""
    missing = [t for t in ("ffmpeg", "ffprobe") if shutil.which(t) is None]
    if missing:
        raise MissingTool(
            f"{' and '.join(missing)} not found on PATH. The toolkit reads video through "
            "ffmpeg; install it from your package manager (e.g. `dnf install ffmpeg`, "
            "`apt install ffmpeg`, `brew install ffmpeg`) and try again.")


# ---- finding a clip -------------------------------------------------------------------
def resolve(arg):
    """A path, or a catalog record id such as DOW-UAP-PR144 / PR144 / 06:PR001.

    Returns (path, tag, record-or-None). `tag` is a short lowercase label used
    for output filenames: the record id where there is one, else the filename
    stem. A path always works; ids only resolve when a catalog is configured
    (see mcdonald.catalog)."""
    cat = _catalog.active()
    p = Path(arg).expanduser()
    if p.exists():
        rec = cat.by_path(p)
        return p, ((rec.get("id") or p.stem).lower() if rec else p.stem.lower()), rec

    release, _, key = arg.rpartition(":")
    hits = cat.by_id(key, release.zfill(2) if release else None)
    if len(hits) == 1:
        rec = hits[0]
        return Path(rec["path"]), (rec.get("id") or Path(rec["path"]).stem).lower(), rec
    if not hits and isinstance(cat, _catalog.NullCatalog):
        raise SystemExit(
            f"{arg}: no such file, and no catalog is configured to look up record ids.\n"
            "Pass a path to the video file, or set MCDONALD_CATALOG to a records.csv "
            "(see mcdonald.catalog).")
    raise SystemExit(
        f"{arg}: {len(hits)} matching records in the {cat.name} catalog"
        + "".join(f"\n  {r.get('release', '')}:{(r.get('title') or '')[:70]}" for r in hits)
        + ("\n(disambiguate as RELEASE:ID, e.g. 06:PR001)" if hits else ""))


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
    d = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)],
        capture_output=True, text=True, check=True).stdout)
    v = next(s for s in d["streams"] if s["codec_type"] == "video")
    return {"width": int(v["width"]), "height": int(v["height"]),
            "fps": Fraction(v["r_frame_rate"]), "nb_frames": int(v.get("nb_frames", 0) or 0),
            "duration": float(d["format"].get("duration", 0)), "format": d["format"], "stream": v,
            "streams": d["streams"]}


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
        self.dir = Path(workdir) if workdir else Path(tempfile.gettempdir()) / "mcdonald" / self.video.stem
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


@lru_cache(maxsize=6)
def _load(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    a.setflags(write=False)
    return a
