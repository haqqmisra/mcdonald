"""`mcdonald plant` -- synthetic objects written into a video's own frames, to learn what the search can find.

A search that reports what it found, and not what it could have found, reports no completeness (the SETI survey's
section 3.1: Margot et al. 2021 made the recovery rate of injected signals the headline number of a search). This
is the injection: objects of known place, size, contrast, motion and light are written into a stretch of a video's
decoded frames, the stretch is encoded again as the video is encoded, and a truth table says where every one of
them is on every frame. What Find, the link, `flicker` and `run` then make of the planted video is held against
that table (`recovered`). ROADMAP.md 0.6, objective 4; docs/method.md section 62.

    mcdonald plant VIDEO --n0 1 --n1 400 --draw 24 --seed 1 --out DIR      # 24 objects drawn over the grid
    mcdonald plant VIDEO --n0 1 --n1 400 --draw 12 --kinds dot,bird,flock   # which kinds
    mcdonald plant VIDEO --n0 1 --n1 400 --plants mine.json                 # the objects given, one a row
    mcdonald plant VIDEO --n0 1 --n1 400 --draw 0                           # nothing planted: the re-encode alone
    mcdonald plant --score TRUTH.json --proposals LOOK.json                 # Find's list held against the truth table

What it writes, in --out (default ./<tag>/planted):

    <tag>_planted_<n0>_<n1>_s<seed>.mp4          the stretch with the objects in it, encoded like the video
    <tag>_planted_<n0>_<n1>_s<seed>_truth.json   every object: its kind, its light, its path, and frame by frame
                                                  where it is, how bright, whether it clipped or went under the overlay
    <tag>_planted_<n0>_<n1>_s<seed>_truth.csv    the same rows as a table
    <tag>_planted_<n0>_<n1>_s<seed>_truth.png    each object as the encoder left it, the control under it: to look at
    <tag>_planted_<n0>_<n1>_none.mp4             the same stretch encoded the same way with nothing planted: the control

**A planted video is a test article, never footage.** Nothing in this package invents detail, and this is the one
place where it writes objects that were never there: so the file says what it is three ways. Its name has
`planted` in it; its container's comment begins with `mcdonald plant` and says how many objects were written in;
and its truth table lies beside it. Every command's `--json` and every case made from such a file carry it
(`clip.planted`; the report's first lines say so). It is never written beside the video it was made from, into the
storage folder's videos or into the reference-data folder (`refused`).

How the objects are written in.

- **Into the luma plane, in the file's own codes.** The stretch is decoded to the planes the file holds (yuv420p),
  with no conversion and no stretch of the levels; an object is added to the luma, and the planes go to the encoder
  as they are. A contrast is given in grey levels of the extracted frames (DN: what every stage reads), and is
  divided by the stretch the extraction applies (255/219 where the video is studio range, as 48 of the PURSUE
  videos say and 101 leave unsaid: method section 50) to get codes.
- **A point** is a Gaussian of a given sigma; **a body** is a disc of a given diameter with its rim blurred by the
  sigma, and hides what is behind it (`opaque`). With `exposure` (a share of the frame time) either is drawn out
  along its motion, as a shutter open that long would draw it. The default is a sharp picture in every frame.
- **It clips where the video clips.** The sum is cut at the ceiling and the floor of the stretch's own picture: the
  highest and lowest luma codes its sampled frames reach, and at least the nominal white and black of its declared
  range (`levels`). A hot object on a bright scene comes out flat-topped, as a real one does, and the truth table
  says on which frames.
- **Under the overlay.** Where the video's static masks (`forensics.static_masks`: burned-in symbology, redaction
  blocks) cover a pixel, nothing is written: the overlay was drawn over the scene, so an object in the scene is
  behind it. The truth table gives the hidden share of each object on each frame.
- **Its light**: constant (the null for `flicker`); a steady beat; a beat whose frequency wanders (a bird's); the
  twinkle of a point seen through turbulent air (a log-normal series with a Kolmogorov corner and a detector's
  time constant: IDEAS.md W29); a strobe (short pulses, a low duty cycle).
- **Its path**: a straight line at a constant velocity on the screen; held still on the screen; a line with a
  drawn wander of a given size and memory (`kriging.simulate`, K8); a recorded track moved elsewhere in the frame
  (so that the camera's own motion is in it); or with the scene (it moves as the background moves, frame by frame:
  a feature of the scene, which Find should not list).
- **Groups**: several points about one centre that keep their places (a formation) or wander about them (a flock):
  B22's warning is that single dots flatter Find where it fails, on members of groups.

How the stretch is encoded.

All 144 PURSUE files were written by one encoder that is not x264 (`Elemental H.264`), and none carries its
settings. What a decoder can read back is repeated: the profile, the pixel format and declared levels, the exact
frame rate, the number of reference frames, the bit rate *of this stretch* (its packets' sizes), and the picture
types -- an I frame is forced wherever the video has one, the B frames between anchors are as many as the video's,
and (by default) the stretch is begun at the I frame at or before --n0 so that the pattern lies on the same frames
as in the video. The encoder is libx264 on one thread: on several, with a target bit rate, it is not bit-exact from
one run to the next (`planted`'s docstring). So two runs with one seed give the same file, byte for byte. What cannot
be repeated is the first encoder itself, and the second encode starts from the first one's picture, not the
sensor's: the control for both is the `_none` file, the same stretch through the same encoder with nothing in it.

What a planted object can and cannot stand for is in docs/method.md, section 62. In short: it tests whether an
object *like the ones drawn* would have been found *in these frames*; it does not glide (B13), it has no wing and
no shape that turns, and a dot alone in the frame is found more often than a real member of a flock (B22).
"""
import csv
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy import ndimage, special

from . import __version__
from .clip import STUDIO, Stop, declared_levels, every_frame, picture_types, probe

MARK = "mcdonald plant"         # a planted file's container comment begins with this
MARGIN = 40                     # px: a drawn object keeps this far in from the frame's edge (as `planted`)
APART = 60.0                    # px: two drawn objects are never nearer than this on a frame they share
AT_ONCE = 4                     # drawn objects in the frame at one time, at most (a group counts once)
LIFE = 120                      # frames a drawn object lasts, at most
GAP = 10                        # frames between one drawn object's last frame and the next one's first, in a lane
HIDDEN_MOST = 0.2               # a drawn path with more than this share of its frames under the overlay is drawn again
SAMPLE = 40                     # frames of the stretch the masks and the levels are read from (`forensics.static_masks`)
CONTRAST = (10.0, 20.0, 40.0, 80.0, 160.0)      # DN of the extracted frames: the grid a draw takes from
SIGMA = (1.0, 1.5, 2.5, 4.0)                    # px
SPEED = (0.3, 1.0, 3.0, 10.0, 30.0)             # px a frame, on the screen
DIAMETER = (8.0, 16.0, 32.0)                    # px, a body's
LIGHTS = ("constant", "beat", "wander", "twinkle", "strobe")
PATHS = ("line", "still", "wander", "recorded", "scene")
# A kind is a preset of shape, light and path. `dot` is the plain one: a constant point on a straight line.
KINDS = {
    "dot": dict(shape="point", light=dict(kind="constant"), path="line"),
    "body": dict(shape="disc", light=dict(kind="constant"), path="line"),
    "still": dict(shape="point", light=dict(kind="constant"), path="still"),
    "beat": dict(shape="point", light=dict(kind="beat"), path="line"),
    "bird": dict(shape="point", light=dict(kind="wander"), path="wander"),
    "twinkle": dict(shape="point", light=dict(kind="twinkle"), path="scene"),
    "strobe": dict(shape="point", light=dict(kind="strobe"), path="line"),
    "scene": dict(shape="point", light=dict(kind="constant"), path="scene"),
    "flock": dict(shape="point", light=dict(kind="wander"), path="wander", group="flock"),
    "formation": dict(shape="point", light=dict(kind="constant"), path="line", group="formation"),
}
NOT_RECOVERED = ("the first encoder (its motion search, mode decisions and rate control), the quantiser it ran at, "
                 "and whether its B frames were used as references")


# ---- what a planted file says of itself --------------------------------------------------------------
def comment(n_objects, source, n0, n1, seed):
    """The container's comment of a planted file: what it is, in words a person reading the file's tags follows."""
    what = (f"{n_objects} synthetic object{'s' if n_objects != 1 else ''} written in" if n_objects
            else "nothing written in (the control)")
    return (f"{MARK}: a test video, not footage. Frames {n0}-{n1} of {source}, encoded again, {what}"
            + (f", seed {seed}" if n_objects else "") + f". mcdonald {__version__}.")


def test_article(info):
    """What a video's container says, if it is one this command wrote: dict(planted, comment) -- `planted` the
    number of synthetic objects in it (0 for the control) -- or None for any other video. `info` is `clip.probe`'s."""
    tags = ((info or {}).get("format") or {}).get("tags") or {}
    text = next((v for k, v in tags.items() if k.lower() == "comment"), "") or ""
    if not text.startswith(MARK):
        return None
    words = text.split("encoded again, ", 1)[-1].split()
    n = int(words[0]) if words and words[0].isdigit() else 0
    return dict(planted=n, comment=text)


def said(article):
    """The report's sentence for a case made from a planted file (`report.Case.markdown`)."""
    n = article.get("planted") or 0
    if n:
        return (f"**This is a test video, not footage.** `mcdonald plant` wrote {n} synthetic object{'s' if n != 1 else ''} "
                "into it to test the search. Nothing measured here describes a real object unless the truth table "
                "beside the video says the track is not one of them.")
    return ("**This is a test video, not footage.** `mcdonald plant` encoded a stretch of a video again with "
            "nothing added, as the control for its planted videos.")


def refused(out, video):
    """Why a planted file may not be written in `out`, or None: never beside the video it was made from, in the
    storage folder's videos, or anywhere in the reference-data folder -- where a person or a catalog would take
    it for a release video."""
    from . import storage
    out = Path(out).expanduser().resolve()
    inside = lambda d: d is not None and (out == d or d in out.parents)
    data = os.environ.get("MCDONALD_DATA", "").strip()
    if out == Path(video).resolve().parent:
        return "beside the video it was made from"
    if inside(storage.videos().resolve()):
        return "in the storage folder's videos"
    if data and inside(Path(data).expanduser().resolve()):
        return "in the reference-data folder"
    return None


# ---- the video's own encoding, read back --------------------------------------------------------------
def _packets(video):
    """[(pts, bytes)] of the video stream's packets in the order they are shown, read without decoding; [] where
    ffprobe gives none."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts,size",
                        "-of", "csv=p=0", str(video)], capture_output=True, encoding="utf-8", errors="replace")
    rows = []
    for ln in r.stdout.splitlines():
        p = ln.strip().split(",")
        if len(p) >= 2 and p[0].lstrip("-").isdigit() and p[1].isdigit():
            rows.append((int(p[0]), int(p[1])))
    return sorted(rows)


def settings(video, n0, n1, info=None, align=True):
    """The video's encoding over frames n0..n1 as libx264 can repeat it: dict(n0, n1 -- the stretch, begun at the I
    frame at or before n0 where `align` and the picture types are known --, asked, rate (the exact frame rate),
    pix_fmt, refs, types (the stretch's picture types as a string, or None), i_frames (their places, from 0),
    bframes, gop, bit_rate (of the stretch: its packets' bits over its length; else the stream's), bit_rate_from,
    colour (the declared range, matrix, transfer and primaries, where the stream gives them), encoder,
    not_recovered)."""
    from . import planted
    info = info or probe(video)
    s = info["stream"]
    n0, n1 = int(n0), int(n1)
    types = picture_types(video, 1, n1)
    a = n0
    if types and align:
        a = max((i + 1 for i in range(n0) if types[i] == "I"), default=n0)
    part = types[a - 1:n1] if types else None
    fps = info["fps"]
    pk = _packets(video)
    bits = 8 * sum(size for _, size in pk[a - 1:n1]) if len(pk) >= n1 else 0
    num = lambda v: int(v) if str(v or "").isdigit() else None
    if bits:
        rate, where = int(round(bits * float(fps) / (n1 - a + 1))), "the stretch's packets"
    else:
        rate = num(s.get("bit_rate")) or num(info["format"].get("bit_rate")) or 4_000_000
        where = "the stream's header"
    if part:
        runs, run = [0], 0
        for t in part:
            run = run + 1 if t == "B" else 0
            runs.append(run)
        bframes = min(max(runs), 16)
        at_i = [i for i, t in enumerate(part) if t == "I"]
        gop = int(np.median(np.diff(at_i))) if len(at_i) > 1 else len(part) + 1
    else:
        class _Clip:                                       # `planted.settings` reads these of a Clip
            pass
        c = _Clip()
        c.video, c.fps, c.info = Path(video), float(fps), dict(info, fps=fps)
        st = planted.settings(c)
        bframes, gop, at_i = st["bframes"], st["gop"], [0]
    pix = str(s.get("pix_fmt") or "yuv420p")
    ok = lambda v: v if v and v not in ("unknown", "reserved", "unspecified") else None
    colour = dict(range=ok(s.get("color_range")), matrix=ok(s.get("color_space")), transfer=ok(s.get("color_transfer")),
                  primaries=ok(s.get("color_primaries")))
    tags = s.get("tags") or {}
    return dict(n0=a, n1=n1, asked=[n0, n1], rate=str(fps), pix_fmt=pix if pix in ("yuv420p", "yuvj420p") else "yuv420p",
                converted_from=None if pix in ("yuv420p", "yuvj420p") else pix, refs=max(1, num(s.get("refs")) or 1),
                types=part, i_frames=at_i, bframes=int(bframes), gop=int(gop), bit_rate=int(rate), bit_rate_from=where,
                colour=colour, profile=s.get("profile"), first_encoder=tags.get("encoder"), encoder="libx264, preset medium, one thread",
                not_recovered=NOT_RECOVERED)


def _encode_command(path, W, H, st, text):
    """ffmpeg's command line for one encoder: raw planes on its stdin, the stretch as the video is encoded out."""
    n = st["n1"] - st["n0"] + 1
    if st["types"]:                                        # an I frame wherever the video has one, and nowhere else
        keys = ["-force_key_frames", "expr:" + "+".join(f"eq(n,{i})" for i in sorted(set([0] + st["i_frames"]))),
                "-g", str(n + 1)]
    else:
        keys = ["-g", str(st["gop"])]
    colour = []
    for opt, key in (("-color_range", "range"), ("-colorspace", "matrix"), ("-color_trc", "transfer"),
                     ("-color_primaries", "primaries")):
        if st["colour"].get(key):
            colour += [opt, st["colour"][key]]
    rate = int(st["bit_rate"])
    return ["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", st["pix_fmt"], "-s", f"{W}x{H}",
            "-framerate", st["rate"], "-i", "-", "-c:v", "libx264", "-threads", "1", "-preset", "medium", "-profile:v", "high",
            "-pix_fmt", st["pix_fmt"], "-refs", str(st["refs"]), "-bf", str(st["bframes"]), "-b_strategy", "0",
            "-x264-params", "b-adapt=0:scenecut=0", *keys, "-b:v", str(rate), "-maxrate", str(int(rate * 1.1)),
            "-bufsize", str(rate * 2), *colour, "-map_metadata", "-1", "-metadata", f"comment={text}",
            "-metadata", "title=mcdonald plant: a test video, not footage", str(path)]


# ---- the stretch's own picture: its levels and its overlay ------------------------------------------------
class _Sample:
    """The few frames `forensics.static_masks` reads, held in memory: all of a Clip it asks for."""

    def __init__(self, frames, W, H, n0, n1):
        self._f, self.W, self.H, self.n0, self.n1 = frames, W, H, n0, n1

    def rgb(self, n):
        return self._f[int(n)]


def survey(video, n0, n1, W, H, tmp, declared):
    """(masks, levels) of the stretch: the static masks the package would make of it (`forensics.static_masks`, from
    the same SAMPLE frames, read as the extraction reads them), and dict(floor, ceiling, lowest, highest, per_dn) --
    the luma codes an object is cut at (the lowest and highest the sampled frames reach, and at least the nominal
    black and white of the declared range) and how many grey levels of the extracted frames one code is."""
    from . import forensics as vf
    ns = sorted(set(np.linspace(n0, n1, min(SAMPLE, n1 - n0 + 1)).astype(int).tolist()))
    sel = "+".join(f"eq(n,{n - 1})" for n in ns)
    rgb, lum = Path(tmp) / "sample.rgb", Path(tmp) / "sample.y"
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(video), "-filter_complex",
                        f"[0:v:0]select='{sel}',split[a][b];[b]extractplanes=y[c]",
                        "-map", "[a]", *every_frame(), "-frames:v", str(len(ns)), "-f", "rawvideo", "-pix_fmt", "rgb24", str(rgb),
                        "-map", "[c]", *every_frame(), "-frames:v", str(len(ns)), "-f", "rawvideo", "-pix_fmt", "gray", str(lum)],
                       capture_output=True)
    if r.returncode != 0:
        raise Stop(f"ffmpeg could not read frames {n0}-{n1}: {r.stderr.decode('utf-8', 'replace').strip()[-300:]}")
    a = np.fromfile(rgb, np.uint8)
    got = len(a) // (W * H * 3)
    frames = {n: f.astype(np.float32) for n, f in zip(ns, a[:got * W * H * 3].reshape(got, H, W, 3))}
    for n in ns:                                           # a count a frame or two long: the last frames it has stand in
        frames.setdefault(n, frames[max(frames)])
    masks = vf.static_masks(_Sample(frames, W, H, n0, n1), n_sample=SAMPLE)
    y = np.fromfile(lum, np.uint8)
    lo, hi = (int(y.min()), int(y.max())) if len(y) else (0, 255)
    full = declared.get("range") == "full" or not declared.get("stretched")
    black, white = (0, 255) if full else STUDIO
    per_dn = 1.0 if full else (STUDIO[1] - STUDIO[0]) / 255.0
    rgb.unlink(missing_ok=True)
    lum.unlink(missing_ok=True)
    return masks, dict(floor=min(lo, black), ceiling=max(hi, white), lowest=lo, highest=hi, codes_per_dn=per_dn,
                       range=declared.get("range"))


# ---- an object's light and path -------------------------------------------------------------------------
def light(spec, n, fps, rng, exposure=0.0):
    """The object's brightness on n frames as a multiple of its contrast (mean about 1): `spec` is dict(kind, ...).

    constant   1.
    beat       1 + depth sin(2 pi hz t + phase) [+ depth2 sin(4 pi hz t + phase2)]: a steady rhythm.
    wander     the same with a frequency that wanders about hz (an Ornstein-Uhlenbeck walk of sd `hz_sd` and
               memory `hz_s` seconds): a wingbeat is not a clock.
    twinkle    a point through turbulent air: exp of a Gaussian series whose spectrum is flat to `corner_hz` and
               falls as f^(-8/3) past it (Kolmogorov), through a detector of time constant `tau_s`; `index` is
               the standard deviation of the brightness over its mean (the scintillation index's root).
    strobe     pulses `hz` times a second, on for `duty` of each period, over a steady light: while a pulse is on,
               `depth` times the steady light is added. A frame records the share of its exposure the pulse was on
               (of the whole frame time where the exposure is 0), so a pulse shorter than a frame is never missed
               and never read at its full height.
    """
    kind = spec.get("kind", "constant")
    t = np.arange(n) / float(fps)
    if kind == "constant":
        return np.ones(n)
    hz = float(spec.get("hz", 6.0))
    depth = float(spec.get("depth", 0.3))
    phase = float(spec["phase"]) if spec.get("phase") is not None else float(rng.uniform(0, 2 * np.pi))
    if kind == "beat":
        m = 1.0 + depth * np.sin(2 * np.pi * hz * t + phase)
        if spec.get("depth2"):
            p2 = float(spec["phase2"]) if spec.get("phase2") is not None else float(rng.uniform(0, 2 * np.pi))
            m = m + float(spec["depth2"]) * np.sin(4 * np.pi * hz * t + p2)
        return m
    if kind == "wander":
        sd, mem = float(spec.get("hz_sd", 0.4)), float(spec.get("hz_s", 0.5))
        a = math.exp(-1.0 / (fps * mem))
        f = np.empty(n)
        f[0] = rng.normal(0, sd)
        e = rng.normal(0, sd * math.sqrt(1 - a * a), n)
        for i in range(1, n):
            f[i] = a * f[i - 1] + e[i]
        ph = phase + 2 * np.pi * np.cumsum(hz + f) / fps
        return 1.0 + depth * np.sin(ph)
    if kind == "twinkle":
        index, corner, tau = float(spec.get("index", 0.3)), float(spec.get("corner_hz", 3.0)), float(spec.get("tau_s", 0.008))
        over = 8                                           # drawn finer than the frames, then averaged over each
        N = n * over
        fr = np.fft.rfftfreq(N, 1.0 / (fps * over))
        psd = np.where(fr <= corner, 1.0, (np.maximum(fr, 1e-9) / corner) ** (-8.0 / 3.0)) / (1.0 + (2 * np.pi * fr * tau) ** 2)
        psd[0] = 0.0
        g = np.fft.irfft(np.sqrt(psd) * (rng.standard_normal(len(fr)) + 1j * rng.standard_normal(len(fr))), N)
        var = math.log(1.0 + index ** 2)
        g *= math.sqrt(var) / max(float(g.std()), 1e-12)
        return np.exp(g - var / 2).reshape(n, over).mean(1)
    if kind == "strobe":
        duty = float(spec.get("duty", 0.05))
        e = (exposure if exposure > 0 else 1.0) / fps
        k = 64
        u = t[:, None] + e * (np.arange(k)[None, :] + 0.5) / k - e / 2
        on = ((u * hz + phase / (2 * np.pi)) % 1.0) < duty
        return 1.0 + depth * on.mean(1)
    raise ValueError(f"no light of kind {kind!r}: {', '.join(LIGHTS)}")


def path(spec, n, fps, rng, W, H):
    """(x, y) of the object on n frames from dict(kind, ...), each an array -- or None for `scene`, whose places are
    made as the frames are read (`make`).

    line       x, y at its first frame and vx, vy px a frame.
    still      held at x, y on the screen.
    wander     the line, and about it a drawn wander of `sill` px that keeps its memory for `range_s` seconds
               (a Matern-3/2 path with no jitter: the truth, not a measurement of it).
    recorded   a track, {frame: [x, y]}, begun at its first frame, moved by (dx, dy) and, with `mirror`, turned
               about the frame's centre: a real object's path somewhere it was not.
    """
    kind = spec.get("kind", "line")
    k = np.arange(n, dtype=float)
    if kind == "scene":
        return None
    if kind == "recorded":
        tr = {int(f): xy for f, xy in spec["track"].items()}
        fs = np.array(sorted(tr), float)
        want = fs[0] + k
        x = np.interp(want, fs, [tr[int(f)][0] for f in fs]) + float(spec.get("dx", 0.0))
        y = np.interp(want, fs, [tr[int(f)][1] for f in fs]) + float(spec.get("dy", 0.0))
        if spec.get("mirror"):
            x, y = (W - 1) - x, (H - 1) - y
        return x, y
    x0, y0 = float(spec["x"]), float(spec["y"])
    vx, vy = (0.0, 0.0) if kind == "still" else (float(spec.get("vx", 0.0)), float(spec.get("vy", 0.0)))
    x, y = x0 + vx * k, y0 + vy * k
    if kind == "wander" and float(spec.get("sill", 0.0)) > 0 and n > 2:
        from . import kriging
        theta = (float(spec["sill"]) ** 2, float(spec.get("range_s", 1.0)), 0.0)
        wx, wy = (kriging.simulate(k / fps, theta, rng, nugget=False)[1] for _ in (0, 1))
        x, y = x + wx - wx[0], y + wy - wy[0]
    return x, y


def _rng(seed, ident):
    return np.random.default_rng([int(seed), int(ident)])


# ---- drawing objects over a grid ------------------------------------------------------------------------
def draw(k, W, H, n, fps, seed=1, kinds=("dot",), contrast=CONTRAST, sigma=SIGMA, speed=SPEED, diameter=DIAMETER,
         polarity="both", at_once=AT_ONCE, life=LIFE, apart=APART, margin=MARGIN, masks=None, first_id=1, taken=()):
    """k objects (a group is one) drawn for a stretch of n frames: (plants, skipped). Each takes its kind in turn from
    `kinds` and its contrast, sigma and speed at random from the grids; its direction and where it starts are uniform;
    it lasts `life` frames or as long as it stays `margin` in from the edge (and is drawn again if that is not most of
    its life, or most of the way across for a fast one). At most `at_once` are in the frame
    together -- they are given turns in `at_once` lanes, one after another with GAP frames between -- and no two come
    within `apart` px on a frame they share, nor does one spend more than HIDDEN_MOST of its frames under the overlay
    (`masks`). Each object's draws come from a generator of its own, seeded by (seed, its number), so an object is the
    same whatever else is drawn after it. `taken`: objects already there, which the new ones keep clear of."""
    for kd in kinds:
        if kd not in KINDS:
            raise ValueError(f"no kind {kd!r}: {', '.join(KINDS)}")
    over = None if masks is None else (masks["blocks"] | masks["graphics"])
    plants, skipped = [], []
    placed = [(p, realise(p, n, fps, W, H, seed)) for p in taken]
    ident = int(first_id)
    life = int(min(life, n))
    turns = max(1, (n + GAP) // (life + GAP))
    if k > turns * at_once:
        raise ValueError(f"{k} objects do not fit in {n} frames at {at_once} at once, each for {life} frames: "
                         f"{turns * at_once} do (fewer frames each, more at once, or a longer stretch)")
    # how long a drawn object must stay inside the margin: its whole life, or for one too fast for that, most of the way
    # across the frame's shorter side (12 frames at the least). A fast object that starts near an edge and is gone in a
    # dozen frames is a draw of where it started, not of its speed.
    need = lambda sp: max(min(life, 12), int(min(life, 0.6 * (min(W, H) - 2 * margin) / max(sp, 1e-9))))
    for j in range(k):
        kind = kinds[j % len(kinds)]
        preset = KINDS[kind]
        lane, turn = j % at_once, j // at_once
        first = 1 + turn * (life + GAP)
        rng = _rng(seed, 100000 + ident)
        done = None
        for _ in range(200):
            sp = 0.0 if preset["path"] in ("still", "scene") else float(rng.choice(speed))
            th = float(rng.uniform(0, 2 * np.pi))
            vx, vy = sp * math.cos(th), sp * math.sin(th)
            x0, y0 = float(rng.uniform(margin, W - margin)), float(rng.uniform(margin, H - margin))
            frames = life
            if sp > 0:                                     # as long as it stays inside the margin, at most `life`
                tx = ((W - margin - x0) / vx if vx > 0 else (margin - x0) / vx) if abs(vx) > 1e-9 else np.inf
                ty = ((H - margin - y0) / vy if vy > 0 else (margin - y0) / vy) if abs(vy) > 1e-9 else np.inf
                frames = int(min(life, math.floor(min(tx, ty))))
            if frames < need(sp):                          # leaving so soon is no test of anything: draw it again
                continue
            base = dict(kind=kind, shape=preset["shape"], sigma=float(rng.choice(sigma)), contrast=float(rng.choice(contrast)),
                        dark=bool(rng.random() < 0.5) if polarity == "both" else polarity == "dark",
                        exposure=0.0, first=int(first), last=int(first + frames - 1))
            if preset["shape"] == "disc":
                base.update(diameter=float(rng.choice(diameter)), opaque=True)
            lt = dict(preset["light"])
            if lt["kind"] in ("beat", "wander"):
                lt.update(hz=float(rng.uniform(3.0, min(12.0, 0.4 * fps))), depth=float(rng.choice((0.15, 0.3, 0.6))))
            elif lt["kind"] == "strobe":
                lt.update(hz=float(rng.uniform(0.7, 2.0)), duty=0.05, depth=float(rng.choice((2.0, 5.0))))
            elif lt["kind"] == "twinkle":
                lt.update(index=float(rng.choice((0.15, 0.3, 0.6))), corner_hz=float(rng.uniform(1.0, 6.0)), tau_s=0.008)
            pt = dict(kind=preset["path"], x=x0, y=y0, vx=vx, vy=vy)
            if preset["path"] == "wander":
                pt.update(sill=float(rng.choice((1.0, 3.0))), range_s=float(rng.choice((0.5, 2.0))))
            group = []
            if preset.get("group"):
                m = int(rng.integers(3, 7))
                gid = ident
                for i in range(m):                         # members 12 to 40 px from the middle, 10 px or more apart
                    for _ in range(50):
                        off = rng.uniform(-40, 40, 2)
                        if 12 <= np.hypot(*off) <= 40 and all(np.hypot(*(off - g["_off"])) >= 10 for g in group):
                            break
                    q = dict(base, id=ident + i, group=gid, member=i + 1, grouped=preset["group"], _off=off,
                             light=dict(lt), path=dict(pt, x=x0 + float(off[0]), y=y0 + float(off[1])))
                    if preset["group"] == "flock":         # each bird its own beat and its own wander about its place
                        q["light"]["hz"] = float(lt["hz"] * rng.uniform(0.9, 1.1))
                        q["path"].update(sill=float(rng.choice((2.0, 5.0))), range_s=float(rng.choice((0.5, 2.0))))
                    group.append(q)
                for q in group:
                    q.pop("_off")
            else:
                group = [dict(base, id=ident, light=lt, path=pt)]
            real = [(q, realise(q, n, fps, W, H, seed)) for q in group]
            ok = True
            for q, r in real:
                rx, ry = _where(q, r)
                inside = (rx >= margin / 2) & (rx <= W - margin / 2) & (ry >= margin / 2) & (ry <= H - margin / 2)
                if not inside.all():
                    ok = False
                    break
                if over is not None:
                    xi, yi = np.clip(np.round(rx).astype(int), 0, W - 1), np.clip(np.round(ry).astype(int), 0, H - 1)
                    if over[yi, xi].mean() > HIDDEN_MOST:
                        ok = False
                        break
                for p, pr in placed:
                    if p.get("group") is not None and p.get("group") == q.get("group"):
                        continue
                    a, b = max(q["first"], p["first"]), min(q["last"], p["last"])
                    if a <= b:
                        px, py = _where(p, pr)
                        d = np.hypot(rx[a - q["first"]:b - q["first"] + 1] - px[a - p["first"]:b - p["first"] + 1],
                                     ry[a - q["first"]:b - q["first"] + 1] - py[a - p["first"]:b - p["first"] + 1])
                        if d.min() < apart:
                            ok = False
                            break
                if not ok:
                    break
            if ok:
                done = real
                break
        if done is None:
            skipped.append(dict(kind=kind, lane=lane, turn=turn, why="no place found clear of the edge, the overlay and the others"))
        else:
            for q, r in done:
                plants.append(q)
                placed.append((q, r))
        ident += max(len(group), 1) if preset.get("group") else 1
    return plants, skipped


def _where(plant, real):
    """(x, y) of a realised object over its frames, for the draw's checks: its path, or for one planted with the scene
    (whose path is made only as the frames are read) the place it starts at, held: where the scene takes it is not
    known when it is drawn."""
    if real["x"] is not None:
        return real["x"], real["y"]
    m = len(real["frames"])
    return np.full(m, float(plant["path"]["x"])), np.full(m, float(plant["path"]["y"]))


TWIN_APART = 80.0       # px: a recorded path moved elsewhere keeps this far from where it was recorded


def place_recorded(plants, masks, W, H, n, fps, seed, margin=MARGIN):
    """Say where the recorded paths go that ask to be placed (`path.place` is "auto"): all of them together, turned
    about the frame's centre or moved whole by one of a few offsets -- whichever keeps most of their frames inside
    the margin, out from under the overlay, and TWIN_APART px or more from where any of them was recorded (so a copy
    never touches an object it copies, and the copies keep the places the objects have among themselves). Changes
    the plants' `path` in place."""
    over = None if masks is None else (masks["blocks"] | masks["graphics"])
    members = [p for p in plants if (p.get("path") or {}).get("kind") == "recorded" and p["path"].get("place") == "auto"]
    if not members:
        return
    ways = [dict(mirror=True, dx=0.0, dy=0.0)] + [dict(mirror=False, dx=float(dx), dy=float(dy))
                                                   for dx in (0, -W // 3, W // 3, -W // 6, W // 6) for dy in (0, -H // 3, H // 3, -H // 6, H // 6)
                                                   if (dx, dy) != (0, 0)]
    was = [(p, realise(dict(p, path=dict(p["path"], place=None, mirror=False, dx=0.0, dy=0.0)), n, fps, W, H, seed)) for p in members]
    best = None
    for way in ways:
        good = total = 0
        for p in members:
            r = realise(dict(p, path=dict(p["path"], place=None, **way)), n, fps, W, H, seed)
            ok = (r["x"] >= margin) & (r["x"] <= W - margin) & (r["y"] >= margin) & (r["y"] <= H - margin)
            for q, r0 in was:                              # clear of every recorded object, on the frames both are there
                lo, hi = max(p["first"], q["first"]), min(p["last"], q["last"])
                if lo <= hi:
                    d = np.hypot(r["x"][lo - p["first"]:hi - p["first"] + 1] - r0["x"][lo - q["first"]:hi - q["first"] + 1],
                                 r["y"][lo - p["first"]:hi - p["first"] + 1] - r0["y"][lo - q["first"]:hi - q["first"] + 1])
                    ok[lo - p["first"]:hi - p["first"] + 1] &= d >= TWIN_APART
            if over is not None:
                xi, yi = np.clip(np.round(r["x"]).astype(int), 0, W - 1), np.clip(np.round(r["y"]).astype(int), 0, H - 1)
                ok &= ~over[yi, xi]
            good, total = good + int(ok.sum()), total + len(ok)
        if best is None or good > best[0]:
            best = (good, total, way)
    for p in members:
        p["path"].update(best[2], place="placed", frames_clear=round(best[0] / max(best[1], 1), 3))


def realise(plant, n, fps, W, H, seed):
    """One object's draws over its own frames: dict(frames -- of the planted video, from 1 --, x, y (None for a path
    made with the scene), light). The generator is the object's own (`_rng`), so nothing else changes them."""
    first, last = int(plant.get("first", 1)), int(min(plant.get("last", n), n))
    m = max(0, last - first + 1)
    rng = _rng(seed, plant["id"])
    xy = path(plant.get("path") or {}, m, fps, rng, W, H) if m else (np.zeros(0), np.zeros(0))
    lt = light(plant.get("light") or {}, m, fps, rng, float(plant.get("exposure") or 0.0)) if m else np.zeros(0)
    return dict(frames=np.arange(first, last + 1), x=None if xy is None else np.asarray(xy[0], float),
                y=None if xy is None else np.asarray(xy[1], float), light=lt)


# ---- writing one object into one frame --------------------------------------------------------------------
def stamp(Y, plant, x, y, level, vel, lv, hide=None, UV=None):
    """Write one object into the luma plane `Y` (uint8, changed in place) at (x, y) with `level` times its contrast.
    `vel` is its motion this frame (px), for a picture drawn out over its exposure; `lv` the stretch's levels
    (`survey`); `hide` the overlay's mask (nothing is written under it); `UV` the two chroma planes, greyed under an
    opaque body. Returns dict(bg -- the median luma about it before --, added -- the codes written, summed --, peak --
    the most any pixel was changed by, in codes: its contrast as written --, clipped, hidden -- the share of it under
    the overlay), or None where it is off the frame."""
    H, W = Y.shape
    s = float(plant.get("sigma", 1.5))
    disc = plant.get("shape") == "disc"
    half = 0.5 * float(plant.get("diameter", 0.0)) if disc else 0.0
    e = float(plant.get("exposure") or 0.0)
    smear = e * math.hypot(*vel)
    R = int(math.ceil(half + 4 * s + 0.5 * smear)) + 2
    xi, yi = int(round(x)), int(round(y))
    x0, x1, y0, y1 = max(xi - R, 0), min(xi + R + 1, W), max(yi - R, 0), min(yi + R + 1, H)
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    steps = max(1, int(math.ceil(smear / max(0.5 * s, 0.25))))
    shape = np.zeros(yy.shape, np.float32)
    for i in range(steps):                                 # the middle of the exposure is where the truth table has it
        u = ((i + 0.5) / steps - 0.5) * e
        rr = np.hypot(xx - (x + u * vel[0]), yy - (y + u * vel[1]))
        shape += (0.5 * special.erfc((rr - half) / (math.sqrt(2) * s)) if disc else np.exp(-rr * rr / (2 * s * s))).astype(np.float32)
    shape /= steps
    was = Y[y0:y1, x0:x1].astype(np.float32)
    bg = float(np.median(was))
    amp = (-1.0 if plant.get("dark") else 1.0) * float(plant["contrast"]) * lv["codes_per_dn"] * float(level)
    if disc and plant.get("opaque", True):                 # a body hides what is behind it: its own level, not a sum
        new = was + shape * (bg + amp - was)
    else:
        new = was + amp * shape
    if hide is not None:
        h = hide[y0:y1, x0:x1]
        new = np.where(h, was, new)
        hidden = float((shape * h).sum() / max(float(shape.sum()), 1e-9))
    else:
        hidden = 0.0
    clipped = bool(((new > lv["ceiling"]) | (new < lv["floor"])).any())
    out = np.clip(np.rint(new), lv["floor"], lv["ceiling"]).astype(np.uint8)
    Y[y0:y1, x0:x1] = out
    if UV is not None and disc and plant.get("opaque", True):
        for P in UV:
            a = shape[(y0 % 2)::2, (x0 % 2)::2]
            sub = P[(y0 + 1) // 2:(y0 + 1) // 2 + a.shape[0], (x0 + 1) // 2:(x0 + 1) // 2 + a.shape[1]]
            a = a[:sub.shape[0], :sub.shape[1]]
            sub[...] = np.rint(sub + a * (128.0 - sub)).astype(np.uint8)
    diff = out.astype(np.float32) - was
    return dict(bg=bg, added=float(diff.sum()), peak=float(np.abs(diff).max()), clipped=clipped, hidden=hidden)


def _label(W, H):
    """A small line of text for the frame's lower left corner, as a luma patch: for a copy meant to be shown."""
    from PIL import Image, ImageDraw
    from .figures import pil_font
    size = int(max(10, round(H / 60)))
    font = pil_font(size)
    text = "TEST VIDEO: SYNTHETIC OBJECTS ADDED (mcdonald plant)"
    im = Image.new("L", (min(W - 8, int(size * 0.62 * len(text)) + 8), size + 6), 16)
    ImageDraw.Draw(im).text((4, 2), text, fill=235, font=font)
    return np.asarray(im)


# ---- the whole job ------------------------------------------------------------------------------------------
def _sha256(path, block=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(block), b""):
            h.update(b)
    return h.hexdigest()


def make(video, n0, n1, plants=None, out=".", tag=None, seed=1, drawn=None, null=True, align=True, label=False,
         look=True, scene=True, say=lambda *a: None, progress=None, stop=None):
    """Write `plants` into frames n0..n1 of `video` and encode the stretch as the video is encoded: the planted file,
    its truth table (JSON and CSV) and, with `null`, the same stretch with nothing planted. `plants` is a list of
    objects (dicts: see `draw`), or `drawn` is dict(k, kinds, contrast, ...) for `draw` to make them on the stretch
    as it is cut (after `align`). With `look`, a picture of every object as the encoder left it (`sheet`). With
    `scene`, the scene's own shift from each frame to the next is measured as the frames go by (`propose.onto`, the
    registration Find uses) and each object's speed is given against it as well as on the screen. Returns
    dict(planted, truth, table, none, sheets, truth_data) -- or raises `Stop` with why
    it cannot (no libx264; an odd frame size; a place a planted file may not go)."""
    from . import planted
    video = Path(video)
    why = refused(out, video)
    if why:
        raise Stop(f"a planted video is a test article and is never written {why}: name another folder with --out")
    if not planted.has_x264():
        raise Stop("this ffmpeg has no libx264 encoder, so the video's encoding cannot be repeated", 3)
    info = probe(video)
    W, H = info["width"], info["height"]
    if W % 2 or H % 2:
        raise Stop(f"{video.name} is {W}x{H}: a frame of odd width or height cannot be encoded as the video's kind of picture")
    total = info["frames"]
    n0, n1 = max(1, int(n0 or 1)), min(int(n1 or total), total)
    if n1 - n0 < 4:
        raise Stop(f"frames {n0}-{n1}: too few to plant in")
    tag = tag or video.stem.lower()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    st = settings(video, n0, n1, info, align)
    a, n = st["n0"], st["n1"] - st["n0"] + 1
    fps = float(info["fps"])
    declared = declared_levels(info)
    tmp = Path(tempfile.mkdtemp(prefix="mcdonald-plant-"))
    try:
        masks, lv = survey(video, a, n1, W, H, tmp, declared)
        skipped = []
        if plants is None:
            d = dict(drawn or {})
            k = int(d.pop("k", 0))
            fill = d.pop("fill", None)
            extra = [dict(p) for p in d.pop("extra", None) or []]        # objects given beside the draw: placed first, kept clear of
            for p in extra:
                p["first"], p["last"] = max(1, int(p.get("first", 1))), min(n, int(p.get("last", n)))
            place_recorded(extra, masks, W, H, n, fps, seed)
            plants, skipped = draw(k, W, H, n, fps, seed=seed, masks=masks, taken=extra, **d) if k else ([], [])
            plants = extra + plants
            if fill:                                       # more objects round the first ones, which stay as they were drawn
                fill = dict(fill)
                more, sk = draw(int(fill.pop("k")), W, H, n, fps, seed=seed, masks=masks, first_id=10001, taken=plants, **fill)
                plants, skipped = plants + more, skipped + sk
        plants = [dict(p) for p in plants]
        for i, p in enumerate(plants, 1):
            p.setdefault("id", i)
            p["first"], p["last"] = max(1, int(p.get("first", 1))), min(n, int(p.get("last", n)))
        place_recorded(plants, masks, W, H, n, fps, seed)
        real = {p["id"]: realise(p, n, fps, W, H, seed) for p in plants}
        if len(real) != len(plants):
            raise ValueError("two planted objects have the same id")
        stem = f"{tag}_planted_{n0}_{n1}"
        f_planted, f_none = out / f"{stem}_s{seed}.mp4", out / f"{stem}_none.mp4"
        hide = masks["blocks"] | masks["graphics"]
        with_scene = [p for p in plants if (p.get("path") or {}).get("kind") == "scene"]
        scene_at = {p["id"]: [float(p["path"]["x"]), float(p["path"]["y"])] for p in with_scene}     # as the frames go by
        say(f"  frames {a}-{n1} of {video.name}" + (f" (begun at the I frame before {n0})" if a != n0 else "")
            + f": {len(plants)} object{'s' if len(plants) != 1 else ''} to write in; encoding like the video: "
            f"{st['bit_rate'] / 1e6:.2f} Mb/s over this stretch, {st['bframes']} B frames between anchors, "
            f"{len(st['i_frames'])} I frame{'s' if len(st['i_frames']) != 1 else ''} where the video has them")
        cw, ch = (W + 1) // 2, (H + 1) // 2
        size = W * H + 2 * cw * ch
        dec = subprocess.Popen(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-map", "0:v:0", "-vf",
                                f"select='between(n,{a - 1},{n1 - 1})'", *every_frame(), "-frames:v", str(n),
                                "-f", "rawvideo", "-pix_fmt", st["pix_fmt"], "-"], stdout=subprocess.PIPE,
                               stderr=open(tmp / "decode.log", "wb"))
        encs = [subprocess.Popen(_encode_command(f_planted, W, H, st, comment(len(plants), video.name, a, n1, seed)),
                                 stdin=subprocess.PIPE, stderr=open(tmp / "planted.log", "wb"))]
        if null:
            encs.append(subprocess.Popen(_encode_command(f_none, W, H, st, comment(0, video.name, a, n1, seed)),
                                         stdin=subprocess.PIPE, stderr=open(tmp / "none.log", "wb")))
        mark = _label(W, H) if label else None
        rows, got = [], 0
        moving = _Scene(~hide, fine=bool(with_scene)) if (scene or with_scene) else None
        scene_from = {}
        try:
            for m in range(1, n + 1):
                buf = dec.stdout.read(size)
                if len(buf) < size:
                    break
                got = m
                frame = np.frombuffer(buf, np.uint8).copy()
                Y = frame[:W * H].reshape(H, W)
                UV = [frame[W * H:W * H + cw * ch].reshape(ch, cw), frame[W * H + cw * ch:].reshape(ch, cw)]
                if mark is not None:
                    Y[H - mark.shape[0] - 4:H - 4, 4:4 + mark.shape[1]] = mark
                    for P in UV:
                        P[(H - mark.shape[0] - 4) // 2:(H - 4) // 2 + 1, 2:(4 + mark.shape[1]) // 2 + 1] = 128
                if null:
                    encs[1].stdin.write(frame.tobytes())
                if moving is not None:                     # where the scene has got to: what moves with it follows it,
                    at = moving.at(m, Y.astype(np.float32))    # and every object's speed is also said against it
                    for p in with_scene:
                        if p["first"] <= m <= p["last"]:
                            o = scene_from.setdefault(p["id"], at)
                            scene_at[p["id"]] = [float(p["path"]["x"]) + at[0] - o[0], float(p["path"]["y"]) + at[1] - o[1]]
                for p in plants:
                    if not p["first"] <= m <= p["last"]:
                        continue
                    r, i = real[p["id"]], m - p["first"]
                    if r["x"] is None:
                        x, y = scene_at[p["id"]]
                        vel = (0.0, 0.0)
                    else:
                        x, y = float(r["x"][i]), float(r["y"][i])
                        j = min(i + 1, len(r["x"]) - 1)
                        vel = (float(r["x"][j] - r["x"][j - 1]), float(r["y"][j] - r["y"][j - 1])) if j > 0 else (0.0, 0.0)
                    w = stamp(Y, p, x, y, float(r["light"][i]), vel, lv, hide, UV)
                    rows.append(dict(frame=m, source_frame=a + m - 1, id=p["id"], x=round(x, 3), y=round(y, 3),
                                     light=round(float(r["light"][i]), 4), on=w is not None,
                                     bg=None if w is None else round(w["bg"], 1),
                                     added=None if w is None else round(w["added"], 1),
                                     peak=None if w is None else round(w["peak"] / lv["codes_per_dn"], 1),
                                     clipped=bool(w and w["clipped"]), hidden=0.0 if w is None else round(w["hidden"], 3)))
                encs[0].stdin.write(frame.tobytes())
                if progress is not None:
                    progress("Writing the planted video", m, n)
                if stop is not None and stop():
                    raise Stop("stopped before the planted video was written", 5)
        finally:
            for e in encs:
                try:
                    e.stdin.close()
                except OSError:
                    pass
            dec.stdout.close()
            dec.wait()
            codes = [e.wait() for e in encs]
        if got < n or any(codes):
            logs = " ".join((tmp / f).read_text(errors="replace").strip()[-300:] for f in ("decode.log", "planted.log", "none.log")
                            if (tmp / f).exists())
            for f in (f_planted, f_none):
                f.unlink(missing_ok=True)
            raise Stop(f"the planted video could not be written ({got} of {n} frames read): {logs or 'the encoder failed'}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # what the encoder made of it: the picture types beside the video's own, and the bit rate it came to
    made = picture_types(f_planted, 1, n)
    same = None if not (made and st["types"]) else float(np.mean([x == y for x, y in zip(made, st["types"])]))
    after = _packets(f_planted)
    st.update(types_made=made, types_same=same,
              bit_rate_made=int(round(8 * sum(s for _, s in after) * fps / n)) if after else None)
    by = {}
    for r in rows:
        by.setdefault(r["id"], []).append(r)
    drift = moving.velocity() if moving is not None else {}
    for p in plants:
        mine = [r for r in by.get(p["id"], []) if r["on"]]
        p.update(frames_on=len(mine), frames_clipped=sum(r["clipped"] for r in mine),
                 frames_hidden=sum(r["hidden"] > 0.5 for r in mine),
                 contrast_codes=round(float(p["contrast"]) * lv["codes_per_dn"], 2),
                 contrast_written=None if not mine else round(float(np.median([r["peak"] for r in mine if r["hidden"] <= 0.5] or [0.0])), 1),
                 fwhm_px=round(2.3548 * float(p.get("sigma", 1.5)), 2),
                 speed_px_per_frame=None if len(mine) < 2 else round(float(np.median(
                     [math.hypot(b["x"] - a_["x"], b["y"] - a_["y"]) for a_, b in zip(mine, mine[1:])])), 3),
                 speed_against_scene=_against(mine, drift),
                 track={str(r["frame"]): [r["x"], r["y"]] for r in mine},
                 light_by_frame={str(r["frame"]): r["light"] for r in mine})
    seen = {i: [r["frame"] for r in v if r["on"] and r["hidden"] <= 0.5] for i, v in by.items()}
    after = after_the_encoder(plants, seen, f_planted, f_none, W, H, lv) if null else {}
    for p in plants:
        p["contrast_after"] = after.get(p["id"])
    truth = dict(
        what=("mcdonald plant: the truth table of a test video with synthetic objects written into it. The video is "
              "a test article, not footage."),
        mcdonald=__version__, seed=int(seed),
        source=dict(video=video.name, bytes=video.stat().st_size, sha256=_sha256(video)),
        stretch=dict(n0=a, n1=n1, asked=[n0, n1], frames=n, width=W, height=H, fps=fps, fps_exact=str(info["fps"])),
        frame_numbers="`frame` is the planted video's, from 1; `source_frame` the video's it was made from",
        units=dict(contrast="grey levels of the extracted frames (DN), the object's peak over what is behind it, as asked",
                   contrast_written="the same as written: the median over its frames of the most a pixel was changed by "
                                    "(less than asked where the picture's floor or ceiling cut it, or its light was low)",
                   contrast_after="what the encoder left of it: the median, over up to 8 of its frames, of the planted video "
                                  "less the control at the object (DN). Read a completeness against this where the bit "
                                  "rate is low: an object asked at 25 DN can come out at 5. None where no control was written",
                   peak="the contrast written, frame by frame (DN)",
                   contrast_codes="the same in the file's luma codes", sigma="px", speed="px a frame", hz="Hz"),
        settings=st, levels=lv, labelled=bool(label), plants=plants, skipped=skipped,
        overlay=dict(share=float(hide.mean()), still_scene=bool(masks.get("still_scene"))),
        scene=None if moving is None else dict(
            speed_px_per_frame=round(float(np.median([math.hypot(*v) for v in drift.values()] or [0.0])), 3),
            held_still=round(float(np.mean([math.hypot(*v) < 0.05 for v in drift.values()] or [1.0])), 3),
            how=("the background's shift from a reference frame to each frame, by the registration Find uses "
                 "(`propose.onto`), the reference renewed every 15 frames or 24 px; a scene with too little texture "
                 "to register, or one that fits as well unshifted, reads as held still"
                 + ("; finished by least squares on the picture's gradients, for the objects planted with the scene"
                    if with_scene else "")),
            at={str(m): [round(x, 2), round(y, 2)] for m, (x, y) in moving.places.items()}),
        files=dict(planted=f_planted.name, none=f_none.name if null else None))
    f_truth, f_table = out / f"{stem}_s{seed}_truth.json", out / f"{stem}_s{seed}_truth.csv"
    f_truth.write_text(json.dumps(truth, indent=1, default=_plain), encoding="utf-8")
    with open(f_table, "w", newline="", encoding="utf-8") as f:
        f.write(f"# {comment(len(plants), video.name, a, n1, seed)}\n")
        w = csv.DictWriter(f, ["frame", "source_frame", "id", "x", "y", "light", "on", "bg", "added", "peak", "clipped", "hidden"])
        w.writeheader()
        w.writerows(rows)
    sheets = sheet(truth, out, out / f"{stem}_s{seed}_truth.png") if look else []
    return dict(planted=str(f_planted), truth=str(f_truth), table=str(f_table), none=str(f_none) if null else None,
                sheets=sheets, truth_data=truth)


class _Scene:
    """Where the scene has got to on each frame, as a displacement from the stretch's first frame: `at(m, g)` for frame
    m's luma. Each frame is registered to a reference frame as `propose.onto` registers (the registration Find uses: one
    shift for the whole picture, kept only where it fits better than none), and the reference is renewed once the scene
    has moved `reach` px from it or after `most` frames -- so a shift is read over a baseline long enough to read it on
    (frame to frame, half a pixel reads as a quarter), and the errors of a long pan do not add up frame by frame.

    With `fine`, that shift is then finished by least squares on the picture's own gradients (`flicker.lk_shift`, at
    half the resolution): what is planted *with* the scene has to sit on it more closely than Find can see. The
    correlation's peak alone is good to about half a pixel a frame on a soft scene (measured on the drawn video of
    tests/test_plant.py: a step scatter of 0.50 px), and a bright point that jitters so about the scene is a faint
    mover to Find, which listed it."""

    def __init__(self, ok, reach=24.0, most=15, fine=False):
        self.ok, self.reach, self.most, self.fine = ok, reach, most, fine
        self.ref = self.ref_m = self.ref_band = None
        self.base = (0.0, 0.0)
        self.places = {}

    def at(self, m, g):
        if self.ref is None:
            self.ref, self.ref_m, here = g, m, (0.0, 0.0)
        else:
            dx, dy = self.shift(self.ref, g)
            here = (self.base[0] + float(dx), self.base[1] + float(dy))
            if math.hypot(dx, dy) > self.reach or m - self.ref_m >= self.most:
                self.ref, self.ref_m, self.base, self.ref_band = g, m, here, None
        self.places[m] = here
        return here

    def shift(self, g0, g):
        """(dx, dy): where g0's background is found in g."""
        from . import propose
        dx, dy = propose.onto(g0, g, self.ok)[1]
        if not self.fine:
            return float(dx), float(dy)
        from .flicker import _bandpass, lk_shift
        if self.ref_band is None:
            self.ref_band = _bandpass(g0[::2, ::2])
        half = ndimage.shift(g[::2, ::2], (-dy / 2.0, -dx / 2.0), order=1, mode="nearest")
        fy, fx, _ = lk_shift(self.ref_band, _bandpass(half), self.ok[::2, ::2])
        if not (np.isfinite(fy) and np.isfinite(fx)) or math.hypot(fy, fx) > 2.0:      # no texture to read, or it ran away
            return float(dx), float(dy)
        return float(dx + 2.0 * fx), float(dy + 2.0 * fy)

    def velocity(self, half=5):
        """{frame: (vx, vy)} px a frame, each from the places `half` frames either side (fewer at the ends)."""
        ms = sorted(self.places)
        out = {}
        for m in ms:
            a, b = max(ms[0], m - half), min(ms[-1], m + half)
            if b > a:
                out[m] = ((self.places[b][0] - self.places[a][0]) / (b - a), (self.places[b][1] - self.places[a][1]) / (b - a))
        return out


def _against(rows, drift, half=5):
    """An object's speed against the scene, px a frame: the median over its frames of its own velocity (over `half`
    frames either side) less the scene's there. None where the scene was not measured or the object has under 3 frames."""
    if not drift or len(rows) < 3:
        return None
    at = {r["frame"]: (r["x"], r["y"]) for r in rows}
    ms = sorted(at)
    out = []
    for m in ms:
        a, b = max(ms[0], m - half), min(ms[-1], m + half)
        if b > a and m in drift and a in at and b in at:
            v = ((at[b][0] - at[a][0]) / (b - a), (at[b][1] - at[a][1]) / (b - a))
            out.append(math.hypot(v[0] - drift[m][0], v[1] - drift[m][1]))
    return round(float(np.median(out)), 3) if out else None


def _plain(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    return str(o)


def after_the_encoder(plants, seen, f_planted, f_none, W, H, lv, most=8, reach=3):
    """{id: contrast in DN} of each planted object as the encoder left it: over up to `most` of the frames it is seen
    on (`seen`, {id: frames}: on the frame and not under the overlay), the planted video's luma less the control's, in the object's polarity, at its largest within `reach` px
    of where the truth table has it; the median of those. The contrast *written* is what went into the encoder. At a
    release video's few megabits a second the two are close; at a tenth of a megabit (the labelled infrared set) a
    faint point is mostly quantised away, and a completeness read against the contrast written would blame the search
    for what the encoder did."""
    want = {}
    for p in plants:
        ns = sorted(int(n) for n in seen.get(p["id"], ()))
        if ns:
            want[p["id"]] = sorted({ns[int(round(i))] for i in np.linspace(0, len(ns) - 1, min(most, len(ns)))})
    every = {n for v in want.values() for n in v}
    A, B = _luma_frames(f_planted, every, W, H), _luma_frames(f_none, every, W, H)
    out = {}
    for p in plants:
        got = []
        for n in want.get(p["id"], ()):
            if n not in A or n not in B:
                continue
            x, y = p["track"][str(n)]
            xi, yi = int(round(x)), int(round(y))
            x0, x1, y0, y1 = max(xi - reach, 0), min(xi + reach + 1, W), max(yi - reach, 0), min(yi + reach + 1, H)
            if x1 <= x0 or y1 <= y0:
                continue
            d = A[n][y0:y1, x0:x1].astype(np.float32) - B[n][y0:y1, x0:x1].astype(np.float32)
            got.append(float((-d if p.get("dark") else d).max()) / lv["codes_per_dn"])
        if got:
            out[p["id"]] = round(max(float(np.median(got)), 0.0), 1)
    return out


# ---- looking at what was planted ----------------------------------------------------------------------------------
def _luma_frames(video, frames, W, H):
    """{frame: H x W uint8 luma} of the frames asked for, by one pass of ffmpeg over the file."""
    frames = sorted(set(int(n) for n in frames))
    if not frames:
        return {}
    sel = "+".join(f"eq(n,{n - 1})" for n in frames)
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-vf", f"select='{sel}',extractplanes=y",
                        *every_frame(), "-frames:v", str(len(frames)), "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8)
    got = len(a) // (W * H)
    return dict(zip(frames, a[:got * W * H].reshape(got, H, W)))


def sheet(truth, folder, out, per=6, box=48, zoom=4, page=10):
    """The planted objects as the encoder left them, for someone to look at before a recovery curve is believed: a row
    for each object, `per` frames spread over its life, each a `box`-px crop about where the truth table has it,
    enlarged without interpolation, with the same place in the control (nothing planted) under it where the control
    was written. The levels are the extracted frames'. `page` objects to a picture: `out`, then `<out>_2.png` and
    on. Returns the pictures written."""
    from PIL import Image, ImageDraw
    from .figures import pil_font
    folder = Path(folder)
    st, lv = truth["stretch"], truth["levels"]
    W, H = st["width"], st["height"]
    plants = [p for p in truth["plants"] if p.get("track")]
    if not plants:
        return []
    want = {}
    for p in plants:
        ns = sorted(int(n) for n in p["track"])
        want[p["id"]] = sorted({ns[int(round(i))] for i in np.linspace(0, len(ns) - 1, min(per, len(ns)))})
    every = {n for v in want.values() for n in v}
    A = _luma_frames(folder / truth["files"]["planted"], every, W, H)
    B = _luma_frames(folder / truth["files"]["none"], every, W, H) if truth["files"].get("none") else {}
    k = 1.0 / lv["codes_per_dn"]
    black = STUDIO[0] if lv["codes_per_dn"] < 1 else 0

    def crop(F, n, x, y):
        g = F.get(n)
        t = np.full((box, box), 24, np.uint8)
        if g is None:
            return t
        xi, yi, r = int(round(x)), int(round(y)), box // 2
        x0, x1, y0, y1 = max(xi - r, 0), min(xi + r, W), max(yi - r, 0), min(yi + r, H)
        if x1 > x0 and y1 > y0:
            t[y0 - (yi - r):y1 - (yi - r), x0 - (xi - r):x1 - (xi - r)] = np.clip((g[y0:y1, x0:x1].astype(np.float32) - black) * k, 0, 255)
        return np.repeat(np.repeat(t, zoom, 0), zoom, 1)
    font, cell, bar = pil_font(14), box * zoom, 22
    rows_h = cell * (2 if B else 1) + bar + 6
    files = []
    for k0 in range(0, len(plants), page):
        part = plants[k0:k0 + page]
        im = Image.new("L", (per * (cell + 4) + 4, len(part) * rows_h), 17)
        dr = ImageDraw.Draw(im)
        for i, p in enumerate(part):
            y = i * rows_h
            lt = p.get("light") or {}
            words = (f"object {p['id']}: {p.get('kind') or p.get('shape')}, {'dark' if p.get('dark') else 'bright'}, "
                     f"{p['contrast']:g} DN asked, {p.get('contrast_written')} written, {p.get('contrast_after')} after the encoder, "
                     f"sigma {p.get('sigma'):g} px"
                     + (f", {p['diameter']:g} px wide" if p.get("diameter") else "")
                     + (f", {p['speed_px_per_frame']:g} px a frame" if p.get("speed_px_per_frame") is not None else "")
                     + (f", light {lt.get('kind')}" + (f" {lt['hz']:.1f} Hz" if lt.get("hz") else "") if lt.get("kind", "constant") != "constant" else "")
                     + f"; frames {', '.join(map(str, want[p['id']]))}")
            dr.text((6, y + 3), words[:int(im.size[0] / 7.6)], fill=235, font=font)
            for j, n in enumerate(want[p["id"]]):
                x, yy = p["track"][str(n)]
                im.paste(Image.fromarray(crop(A, n, x, yy)), (4 + j * (cell + 4), y + bar))
                if B:
                    im.paste(Image.fromarray(crop(B, n, x, yy)), (4 + j * (cell + 4), y + bar + cell + 2))
        path_ = str(out) if not k0 else str(out).replace(".png", f"_{k0 // page + 1}.png")
        im.save(path_)
        files.append(path_)
    return files


# ---- holding a search against the truth table ----------------------------------------------------------------
def wilson(k, n, z=1.96):
    """(low, high) of a share k of n at 95 %, by Wilson's score interval: honest at 0 and at n, where the usual
    k/n +- its error is not. (None, None) for n = 0."""
    if not n:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def on_path(track, truth, size=0.0, px=12.0, share=0.7):
    """(frames shared, median px apart) if `track` {frame: (x, y)} is on the planted path `truth` {frame: (x, y)}, else
    None: `tools/find_rank.py`'s rule for a recorded track -- more than `share` of the frames they share within `px`,
    or within a third of the found spot's own width if that is more, on two frames or more."""
    shared = [n for n in track if n in truth]
    if len(shared) < 2:
        return None
    px = max(px, size / 3.0)
    d = np.array([math.hypot(track[n][0] - truth[n][0], track[n][1] - truth[n][1]) for n in shared])
    return (len(shared), float(np.median(d))) if float(np.mean(d <= px)) > share else None


def recovered(truth, proposals, px=12.0):
    """Find's list held against a truth table: dict(plants: one row an object -- id, kind, group, contrast, sigma,
    speed, dark, frames (seen: on the frame, not hidden), found, rank (the place on the list of the first row on its
    path), rank_alone (that place less the rows above it that are on planted paths: where it would stand with no other
    object planted), strength, score, shared, px (the median distance), polarity (the row's is the object's), points
    (how many points the row holds: a group's) --, others: the rows on no planted path, each with rank, strength, score and
    frames --, found, planted, rows). `proposals` are `look --propose --json`'s (`results.proposals`: each with
    `track`, `dark`, `size_px`, `score`, `strength`), best first, on the planted video's own frames."""
    props = []
    for p in proposals:
        tr = {int(n): (float(xy[0]), float(xy[1])) for n, xy in (p.get("track") or {}).items()}
        props.append((tr, p))
    rows, taken = [], set()
    for pl in truth["plants"]:
        path_ = {int(n): xy for n, xy in pl["track"].items()}
        hit = None
        for i, (tr, p) in enumerate(props, 1):
            got = on_path(tr, path_, float(p.get("size_px") or 0.0), px)
            if got:
                hit = (i, p, got)
                taken.add(i)
                break
        for i, (tr, p) in enumerate(props, 1):             # every row on it, not only the first: none of them is "another"
            if i not in taken and on_path(tr, path_, float(p.get("size_px") or 0.0), px):
                taken.add(i)
        rows.append(dict(id=pl["id"], kind=pl.get("kind"), group=pl.get("group"), contrast=pl["contrast"],
                         contrast_written=pl.get("contrast_written"), contrast_after=pl.get("contrast_after"), sigma=pl.get("sigma"),
                         diameter=pl.get("diameter"), speed=pl.get("speed_px_per_frame"),
                         speed_scene=pl.get("speed_against_scene"), dark=bool(pl.get("dark")),
                         light=(pl.get("light") or {}).get("kind"), hz=(pl.get("light") or {}).get("hz"),
                         frames=pl.get("frames_on", len(path_)) - pl.get("frames_hidden", 0),
                         clipped=pl.get("frames_clipped", 0), found=hit is not None,
                         rank=hit[0] if hit else None, rank_alone=None, strength=hit[1].get("strength") if hit else None,
                         score=hit[1].get("score") if hit else None, shared=hit[2][0] if hit else None,
                         px=round(hit[2][1], 2) if hit else None,
                         polarity=bool(hit[1].get("dark")) == bool(pl.get("dark")) if hit else None,
                         points=hit[1].get("points") if hit else None))
    for r in rows:                                         # its place if the rows above it that are other planted objects were
        if r["found"]:                                     # not there: with twenty planted, a faint one's place is theirs to push down
            r["rank_alone"] = r["rank"] - sum(1 for i in taken if i < r["rank"])
    others = [dict(rank=i, strength=p.get("strength"), score=p.get("score"), frames=p.get("frames"), dark=p.get("dark"),
                   size_px=p.get("size_px")) for i, (tr, p) in enumerate(props, 1) if i not in taken]
    return dict(plants=rows, others=others, found=sum(r["found"] for r in rows), planted=len(rows), rows=len(props))


def tabulate(rows, by=("kind",), found="found"):
    """Completeness by cell: [dict(cell values..., n, found, share, low, high)] over `rows` (`recovered`'s plants, from
    any number of planted videos), grouped by the fields in `by`, with Wilson's 95 % interval."""
    cells = {}
    for r in rows:
        cells.setdefault(tuple(r.get(k) for k in by), []).append(bool(r.get(found)))
    out = []
    for key in sorted(cells, key=lambda k: tuple((v is None, str(type(v)), v) for v in k)):
        v = cells[key]
        lo, hi = wilson(sum(v), len(v))
        out.append(dict(zip(by, key), n=len(v), found=sum(v), share=sum(v) / len(v), low=lo, high=hi))
    return out


# ---- the command --------------------------------------------------------------------------------------------------
def _numbers(text, name):
    try:
        return tuple(float(v) for v in str(text).split(",") if v.strip())
    except ValueError:
        raise Stop(f"--{name} {text}: give numbers with commas between them, such as 20,40,80", 2)


def main():
    import argparse
    from . import forensics as vf
    from .report import emit, envelope, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(
        prog="mcdonald plant",
        description="Write synthetic objects into a stretch of a video, to test what the search can find. The result is a "
                    "test video, never footage: its name and its tags say so, and a table beside it says where every "
                    "object is in every frame.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__[__doc__.index("    mcdonald plant VIDEO"):__doc__.index("**A planted video")])
    ap.add_argument("video", nargs="?", help="the video to plant in: a path, or a record id such as PR113")
    ap.add_argument("--n0", type=int, help="first frame of the stretch (default: the video's first)")
    ap.add_argument("--n1", type=int, help="last frame of the stretch (default: the video's last)")
    ap.add_argument("--draw", type=int, metavar="K", help="draw K objects over the grids below (0: plant nothing, and "
                                                         "write only the stretch encoded again)")
    ap.add_argument("--kinds", default="dot", help="with --draw: the kinds to draw, in turn (default dot): "
                                                   + ", ".join(KINDS))
    ap.add_argument("--contrast", metavar="DN,...", help="with --draw: how far an object stands out from what is behind "
                    f"it, in grey levels of the frames (default {','.join(f'{v:g}' for v in CONTRAST)})")
    ap.add_argument("--sigma", metavar="PX,...", help="with --draw: an object's blur, the sigma of a Gaussian, in pixels "
                    f"(default {','.join(f'{v:g}' for v in SIGMA)})")
    ap.add_argument("--speed", metavar="PX,...", help="with --draw: speeds on the screen, in pixels a frame "
                    f"(default {','.join(f'{v:g}' for v in SPEED)})")
    ap.add_argument("--diameter", metavar="PX,...", help="with --draw: a body's width in pixels "
                    f"(default {','.join(f'{v:g}' for v in DIAMETER)})")
    ap.add_argument("--polarity", choices=("both", "bright", "dark"), default="both",
                    help="with --draw: brighter than what is behind them, darker, or either by chance (default both)")
    ap.add_argument("--at-once", type=int, default=AT_ONCE, help=f"with --draw: the most objects in the frame at one time (default {AT_ONCE})")
    ap.add_argument("--life", type=int, default=LIFE, help=f"with --draw: the most frames one object lasts (default {LIFE})")
    ap.add_argument("--apart", type=float, default=APART, help=f"with --draw: the least distance between two objects, in pixels (default {APART:g})")
    ap.add_argument("--plants", metavar="JSON", help="the objects to plant, as a list in a file (or a truth table: its "
                                                    "objects are planted again)")
    ap.add_argument("--seed", type=int, default=1, help="the draw's seed: one seed, one video, byte for byte (default 1)")
    ap.add_argument("--no-none", action="store_true", help="do not write the control, the stretch with nothing planted")
    ap.add_argument("--no-align", action="store_true", help="begin exactly at --n0, not at the I frame at or before it")
    ap.add_argument("--label", action="store_true", help="write a line of text into every frame saying it is a test video "
                                                         "(for a copy meant to be shown; it changes what is encoded)")
    ap.add_argument("--no-sheet", action="store_true", help="do not write the picture of the planted objects")
    ap.add_argument("--no-scene", action="store_true", help="do not measure how the scene moves from frame to frame (each "
                    "object's speed is then given on the screen only)")
    ap.add_argument("--score", metavar="TRUTH", help="hold a search against a truth table and plant nothing: with --proposals")
    ap.add_argument("--proposals", metavar="JSON", help="with --score: what `mcdonald look --propose --more --json` printed "
                                                       "for the planted video")
    ap.add_argument("--out", metavar="DIR", help="where the planted video and its table go (default: ./<tag>/planted)")
    ap.add_argument("--json", action="store_true", help="print what was written, and the truth table, as JSON on stdout")
    args = ap.parse_args()
    inputs = inputs_of(args)

    if args.score:
        if not args.proposals:
            raise Stop("--score needs --proposals, what `mcdonald look --propose --more --json` printed", 2)
        with said_to_stderr(args.json) as lines:
            truth = json.loads(Path(args.score).read_text(encoding="utf-8"))
            d = json.loads(Path(args.proposals).read_text(encoding="utf-8"))
            props = d if isinstance(d, list) else (d.get("results") or d).get("proposals") or []
            res = recovered(truth, props)
            print(f"{res['found']} of {res['planted']} planted objects are on the list of {res['rows']} spots; "
                  f"{len(res['others'])} spots are on no planted path")
            for r in res["plants"]:
                print(f"  object {r['id']:<4} {r['kind'] or '':9s} {'dark' if r['dark'] else 'bright':6s} {r['contrast']:5g} DN, "
                      f"sigma {r['sigma']:g} px, {(r['speed'] or 0):5.1f} px a frame: "
                      + (f"spot {r['rank']} ({r['strength']}), {r['px']:.1f} px from it on {r['shared']} frames" if r["found"] else "not on the list"))
        if args.json:
            emit(envelope("plant", inputs, None, [], dict(res, said=lines)))
        return 0

    if not args.video:
        raise Stop("give a video to plant in (a path, or a record id such as PR113), or --score TRUTH --proposals JSON", 2)
    if args.draw is None and not args.plants:
        raise Stop("say what to plant: --draw K for K drawn objects (0 for none), or --plants FILE", 2)
    video, tag, _ = vf.resolve(args.video)
    out = Path(args.out) if args.out else vf.case_dir(None, tag) / "planted"
    plants = drawn = None
    if args.plants:
        d = json.loads(Path(args.plants).read_text(encoding="utf-8"))
        plants = d if isinstance(d, list) else d.get("plants") or []
        for p in plants:                                   # a truth table's objects carry what `make` adds: taken off again
            for k in ("frames_on", "frames_clipped", "frames_hidden", "contrast_codes", "contrast_written", "contrast_after", "fwhm_px",
                      "speed_px_per_frame",
                      "speed_against_scene",
                      "track", "light_by_frame"):
                p.pop(k, None)
    else:
        drawn = dict(k=args.draw, kinds=tuple(k.strip() for k in args.kinds.split(",") if k.strip()),
                     polarity=args.polarity, at_once=args.at_once, life=args.life, apart=args.apart)
        for name in ("contrast", "sigma", "speed", "diameter"):
            if getattr(args, name):
                drawn[name] = _numbers(getattr(args, name), name)
    with said_to_stderr(args.json) as lines:
        from .progress import to_stderr
        try:
            res = make(video, args.n0, args.n1, plants, out, tag, args.seed, drawn, null=not args.no_none,
                       align=not args.no_align, label=args.label, look=not args.no_sheet, scene=not args.no_scene, say=print,
                       progress=to_stderr())
        except ValueError as e:
            raise Stop(str(e), 2)
        t = res["truth_data"]
        st = t["settings"]
        print(f"wrote {res['planted']}: a test video, not footage, with {len(t['plants'])} synthetic "
              f"object{'s' if len(t['plants']) != 1 else ''} in frames {t['stretch']['n0']}-{t['stretch']['n1']} of {video.name}")
        print(f"wrote {res['truth']} and {Path(res['table']).name}: where each object is in every frame")
        if res["none"]:
            print(f"wrote {res['none']}: the same frames encoded the same way with nothing added, the control")
        if res["sheets"]:
            print(f"wrote {res['sheets'][0]}" + (f" (and {len(res['sheets']) - 1} more)" if len(res["sheets"]) > 1 else "")
                  + ": each object as the encoder left it, with the same place in the control under it. Look at it before "
                  "trusting what a search finds of them.")
        if st.get("types_same") is not None:
            print(f"  the encoder gave {100 * st['types_same']:.0f} % of the frames the picture type the video gives them, "
                  f"at {st['bit_rate_made'] / 1e6:.2f} Mb/s for the video's {st['bit_rate'] / 1e6:.2f}")
        for s in t["skipped"]:
            print(f"  one {s['kind']} was not planted: {s['why']}")
    if args.json:
        files = [res["planted"], res["truth"], res["table"]] + ([res["none"]] if res["none"] else []) + res["sheets"]
        notes = ["A planted video is a test article, not footage: its name, its container's comment and the truth table "
                 "beside it say so, and every case made from it carries `clip.planted`.",
                 f"Not repeated from the video, because no file records it: {NOT_RECOVERED}. The control for that is the "
                 "stretch encoded the same way with nothing planted."]
        results = {k: v for k, v in t.items() if k != "plants"}
        if results.get("scene"):
            results["scene"] = {k: v for k, v in results["scene"].items() if k != "at"}
        results["plants"] = [{k: v for k, v in p.items() if k not in ("track", "light_by_frame")} for p in t["plants"]]
        results["said"] = lines
        emit(envelope("plant", inputs, None, files, results, notes=notes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
