#!/usr/bin/env python3
"""Does the scene move under the sensor's fixed pattern?  A reading of whole blocks of frames, with no templates.

  mcdonald scene VIDEO|ID [--n0 N --n1 N] [--track CSV ...] [--sample N] [--out DIR] [--json]

`layers` matches templates between frames, and a pattern fixed on the sensor (speckle, column stripes, a dead-pixel map,
the coder's held blocks) matches best at no shift at all: that is its NO POWER, "held still even over a second". This
stage asks the same question of a block of 60 frames at once, in the way microscopy separates what moves from what stays
(Hebert, Costantino & Wiseman 2005, the immobile filter of spatio-temporal image correlation), one step further:

  1. Each frame's mean out, then each pixel's mean over the block. A pattern that stays put goes, and so does a burned-in
     symbol. What still flickers hard (digits, the object) is masked, and the tracked object's own place besides.
  2. The block's Fourier transforms, kept in a low band (BAND: periods of 11-83 reduced px). The grain does not last from
     frame to frame in a coded picture, and the coder's own 8- and 16-px lattice is notched out of the band.
  3. For each lag, the cross-spectrum of the frames with the same frames that lag later, each spatial frequency whitened by
     its own power, and its ODD part alone. Anything that stays put, however it breathes with the gain, has a real
     cross-spectrum; only a shift makes it imaginary. Back to a map r_lag(y, x).
  4. S(v), the maps read along the straight line (v lag) through (x, y, lag). Its highest place is the scene's velocity,
     and the next one is kept. The low band finds a scene and reads it coarsely (11 % slow on one of PR144's blocks), so the
     band above it, an independent set of coefficients, reads it again near that place where it stands (UPPER): to a fine
     velocity, and, where two places stand, to two layers (PR144's sea and cloud, 3.3 px/frame apart, flip the low band's top).
  5. The tests. z: the peak against S's own spread, and against the same with the block's frames shuffled, where nothing
     moves coherently. The stack: the frames added up along v, against -v, 0.8 v and 1.2 v and against adding them up
     with no alignment at all. And does the picture last: the velocity near v the stack likes best, then the block's first
     half and its last half added up along it, two sets of frames with none in common and up to 59 apart. A scene shows the
     same picture in both. What only looks like motion at the reading's short lags does not.

v is image motion in px/frame of the file, +x right, +y down, as `layers`' shifts. A block's reading is not a `layers`
reading and nothing downstream takes it for one: it goes to <tag>_scene.csv and to this stage's own output only.

What it cannot say.  Below about 1 DN rms a coded clip loses faint motion, so "no scene read" means none above that, not
none (planted textures through the clip's own encoder: read at 1 DN, the slow one alone at 0.5, none at 0.25). A slow scene
loses part of itself to the block's mean. The reading is in file pixels: on a stretched clip it is not an angle until the
stretch is known. And a velocity is what was measured. What the moving thing is, sea or cloud or coder, is not.
"""
import argparse
import csv
import subprocess
from pathlib import Path

import numpy as np
from scipy import fft as sfft
from scipy import ndimage

from .clip import MissingTool, every_frame, probe
from .progress import PROCS_HELP, pooled, to_stderr
from .report import Found, emit, inputs_of, said_to_stderr

BLOCK = 60                       # frames a block
MIN_FRAMES = 30                  # a block shorter than this is not read
WIDE = 660                       # px: frames are box-reduced to this width or under
BAND = (0.012, 0.09)             # cycles per reduced px: the lowest carry the gain's breathing and the taper; above, the grain
FAST = ((1, 2, 3, 4, 6, 8), 30.0, 0.125)             # lags, largest v, step: px/frame of the reduced picture
SLOW = ((2, 3, 4, 6, 8, 12, 16, 24), 2.0, 0.025)     # the same for a slow scene, read finer where it stands against its null
RHO = 1.0                        # reduced px: the disc about zero shift left out of each lag's map
MASK_K = 6.0                     # a pixel flickering this many times the median is masked
SURROGATES = 2                   # shuffled blocks a block
UPPER = (0.09, 0.25)             # cycles per reduced px: the band above, where the coder has kept it
NEAR_FINE = 1.5                  # reduced px/frame: how far from the low band's place the upper band is asked
APART = 0.75                     # reduced px/frame: two places nearer than this are one
NEAR_HOLD, STEP_HOLD = 1.0, 0.125   # reduced px/frame: where near v the stack is asked, for the low band's coarseness


def down_of(width):
    """The box reduction that brings a frame `width` px wide to WIDE or under."""
    return max(int(np.ceil(width / WIDE)), 1)


def frames(video, n0, n1, down, fps, size=None):
    """Frames n0..n1 of the video (1-based, inclusive), grey float32 T x h x w, box-reduced by `down`, one at a time off an
    ffmpeg pipe so that no more than the reduced frames are ever held: a block is 60 frames, and at 1080p the full frames
    would be half a gigabyte of float32 a worker. Seeked as `reel.py` seeks: half a frame before frame n, one frame out for
    each in. `size` is (W, H), where the caller has it."""
    W, H = size or (lambda i: (i["width"], i["height"]))(probe(video))
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{max(n0 - 1.5, 0.0) / fps:.6f}", "-i", str(video), "-frames:v", str(n1 - n0 + 1),
           *every_frame(), "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1"]
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except FileNotFoundError as e:
        raise MissingTool("ffmpeg") from e
    h, w = H // down, W // down
    out = []
    try:
        while True:
            b = p.stdout.read(W * H)
            if len(b) < W * H:
                break
            a = np.frombuffer(b, np.uint8).reshape(H, W)
            if down > 1:
                a = a[:h * down, :w * down].reshape(h, down, w, down).mean((1, 3), dtype=np.float32)
            out.append(a.astype(np.float32))
    finally:
        p.stdout.close()
        p.wait()
    return np.array(out, np.float32) if out else np.zeros((0, h, w), np.float32)


def active_box(a):
    """The rectangle of the picture that changes at all, (top, bottom, left, right): letterbox and pillarbox out."""
    sd = a[:: max(a.shape[0] // 40, 1)].std(0)
    good = sd > 0.25
    rows, cols = np.where(good.mean(1) > 0.3)[0], np.where(good.mean(0) > 0.3)[0]
    if len(rows) < 32 or len(cols) < 32:
        return 0, a.shape[1], 0, a.shape[2]
    return int(rows[0]) + 2, int(rows[-1]) - 1, int(cols[0]) + 2, int(cols[-1]) - 1


def taper(h, w, frac=0.08):
    """A raised-cosine edge on each side, so that the frame's own edges do not read as a texture that stays put."""
    def one(n):
        m = max(int(n * frac), 2)
        t = np.ones(n, np.float32)
        ramp = 0.5 - 0.5 * np.cos(np.pi * (np.arange(m) + 0.5) / m)
        t[:m], t[-m:] = ramp, ramp[::-1]
        return t
    return np.outer(one(h), one(w))


def prep(block, exclude=None):
    """The block with each frame's mean out, each pixel's mean over the block out (the immobile filter), the pixels that
    flicker hard masked (with `exclude`) and the edges tapered. (frames, share of the picture masked)."""
    x = block - block.mean((1, 2), keepdims=True)
    x = x - x.mean(0, keepdims=True)
    sd = x.std(0)
    bad = ndimage.binary_dilation(sd > MASK_K * (np.median(sd) + 1e-6), iterations=3)
    if exclude is not None:
        bad |= exclude
    return x * (~bad)[None] * taper(*x.shape[1:])[None], float(bad.mean())


def band_of(shape, down, lo=BAND[0], hi=BAND[1]):
    """Which of an rfft2's frequencies are kept: lo..hi cycles per reduced px, the coder's lattice left out. A lattice
    correlates with itself at its own multiples, and reads as a velocity of a whole number of blocks; 8 and 16 px on the full
    picture are multiples of 1/16 cycle a full px. (bool mask, fy, fx)."""
    fy = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.rfftfreq(shape[1])[None, :]
    q = np.hypot(fx, fy)
    keep = (q >= lo) & (q <= hi)
    step = down / 16.0
    for f, n in ((fx, shape[1]), (fy, shape[0])):
        phase = np.abs(np.abs(f) / step - np.round(np.abs(f) / step)) * step
        keep = keep & ~((phase < 2.0 / n) & (np.abs(f) > 0.5 * step))
    return keep, fy, fx


class Spectra:
    """A block's Fourier transforms, only the band's: 6 % of the coefficients, the same maps to rounding. With the frames reduced as
    they arrive, a block costs 5-6 s and 400 MB, against the prototype's 15 s and 830 MB. `band` is `band_of`'s mask."""

    def __init__(self, x, band, fy, fx):
        self.band, self.shape = band, x.shape[1:]
        self.F = np.array([sfft.rfft2(a)[band] for a in x], np.complex64)
        self.P = (np.abs(self.F) ** 2).mean(0) + 1e-9
        self.unit = max(float(band.sum()) * 2.0 / (self.shape[0] * self.shape[1]), 1e-9)
        yy, xx = np.nonzero(band)
        self.fy, self.fx = fy[yy, 0].astype(np.float32), fx[0, xx].astype(np.float32)

    def maps(self, lags, order=None):
        """{lag: r(y, x)}: the odd part of the whitened cross-spectrum over that lag, back in the picture and centred. A peak
        of height h means h of the band's power in the block is carried to that shift. `order` shuffles the frames: the null."""
        F = self.F if order is None else self.F[order]
        h, w = self.shape
        out = {}
        for lag in lags:
            if lag >= F.shape[0]:
                continue
            c = (F[:-lag] * np.conj(F[lag:])).mean(0) / self.P
            C = np.zeros(self.band.shape, np.complex64)
            C[self.band] = 1j * c.imag            # anything that stays put has a real cross-spectrum, however it breathes
            out[lag] = np.fft.fftshift(sfft.irfft2(C, s=(h, w))).astype(np.float32) / self.unit
        return out

    def gain(self, vx, vy):
        """The frames added up along (vx, vy), reduced px/frame, over adding them up with no alignment at all, in amplitude:
        1 is noise, the square root of the frames is a picture that carries itself whole along v. In the Fourier plane, so
        on exactly the band S was read in, and a frame's edge wraps instead of being cropped."""
        t = np.arange(self.F.shape[0], dtype=np.float32)[:, None]
        phase = np.exp(2j * np.pi * t * (self.fx * vx + self.fy * vy)[None, :])
        coherent = float((np.abs((self.F * phase).sum(0)) ** 2).sum())
        return float(np.sqrt(coherent / max(float((np.abs(self.F) ** 2).sum()), 1e-30)))


def vmap(rm, vmax, dv):
    """S(v) on a square grid: r_lag read at (v lag) summed over the lags, over the square root of the lags that count, a
    matched filter with each lag's noise alike. The disc RHO about zero shift is left out of each lag's map, and a velocity
    counts only with two lags that reach past it. r as made has its peak at -shift, so it is read at -v lag."""
    vs = np.arange(-vmax, vmax + dv / 2, dv)
    vy, vx = np.meshgrid(vs, vs, indexing="ij")
    S, n = np.zeros_like(vx), np.zeros_like(vx)
    for lag, r in rm.items():
        h, w = r.shape
        yy, xx = (h // 2 - vy * lag) % h, (w // 2 - vx * lag) % w
        far = np.hypot(vx, vy) * lag >= RHO
        S += np.where(far, ndimage.map_coordinates(r, [yy, xx], order=1, mode="wrap"), 0.0)
        n += far
    return np.where(n >= 2, S / np.sqrt(np.maximum(n, 1)), np.nan), vs


def _top(S, vs):
    """S's highest place and how it stands against S's own spread: (vx, vy, S, z)."""
    i, j = np.unravel_index(np.nanargmax(S), S.shape)
    vals = S[np.isfinite(S)]
    med = np.median(vals)
    mad = 1.4826 * np.median(np.abs(vals - med)) + 1e-12
    return float(vs[j]), float(vs[i]), float(S[i, j]), float((S[i, j] - med) / mad)


def second_peak(S, vs, top, apart=APART):
    """The highest true local maximum of S at least `apart` reduced px/frame from `top`, (vx, vy, S), or None. A true one, not
    the first's shoulder: PR144's two layers are 1.1 reduced px/frame apart and both are there."""
    dv = vs[1] - vs[0]
    f = np.nan_to_num(S, nan=-np.inf)
    size = 2 * max(int(round(0.25 / dv)), 1) + 1
    peaks = np.argwhere((f == ndimage.maximum_filter(f, size=size)) & np.isfinite(f))
    v = np.array([(vs[j], vs[i]) for i, j in peaks])
    if not len(v):
        return None
    keep = np.hypot(v[:, 0] - top[0], v[:, 1] - top[1]) >= apart
    if not keep.any():
        return None
    p, v = peaks[keep], v[keep]
    best = int(np.argmax(f[p[:, 0], p[:, 1]]))
    return float(v[best, 0]), float(v[best, 1]), float(f[p[best, 0], p[best, 1]])


def holds(sp, vx, vy):
    """Does the picture read at (vx, vy), reduced px/frame, last the block? The velocity within NEAR_HOLD of it whose whitened stack
    is strongest (a third of the coefficients: the search is all it is for), then, at that velocity, the first half of the block
    and the last half each added up, and how well the two agree. (coherence, vx, vy). 0 is two unrelated pictures. The search is
    needed: 1 px/frame off, frames 30 apart are 30 px out, and a real scene read coarsely scores nothing."""
    F = sp.F / np.sqrt(sp.P)[None, :]
    T = F.shape[0]
    t = np.arange(T, dtype=np.float32)[:, None]
    some, fx, fy = F[:, ::3], sp.fx[::3], sp.fy[::3]
    grid = np.arange(-NEAR_HOLD, NEAR_HOLD + STEP_HOLD / 2, STEP_HOLD)
    best, at = -1.0, (vx, vy)
    for dy in grid:
        for dx in grid:
            e = float((np.abs((some * np.exp(2j * np.pi * t * (fx * (vx + dx) + fy * (vy + dy))[None, :])).sum(0)) ** 2).sum())
            if e > best:
                best, at = e, (vx + dx, vy + dy)
    G = F * np.exp(2j * np.pi * t * (sp.fx * at[0] + sp.fy * at[1])[None, :])
    a, b = G[: T // 2].sum(0), G[T // 2:].sum(0)
    return float((a * np.conj(b)).real.sum() / (np.sqrt((np.abs(a) ** 2).sum() * (np.abs(b) ** 2).sum()) + 1e-30)), at[0], at[1]


def _sub(S, i, j):
    """The peak of S at (i, j), to a fraction of a grid step: a parabola through it and its neighbours on each axis."""
    def one(m, c, p):
        d = m - 2 * c + p
        return 0.0 if not np.isfinite(d) or d == 0 else float(np.clip(0.5 * (m - p) / d, -0.5, 0.5))
    h, w = S.shape
    if not (0 < i < h - 1 and 0 < j < w - 1):
        return 0.0, 0.0
    return one(S[i, j - 1], S[i, j], S[i, j + 1]), one(S[i - 1, j], S[i, j], S[i + 1, j])


def finer(S, vs, vx, vy):
    """The upper band's places near the low band's (vx, vy), highest first: [(vx, vy, z)], true local maxima of S within
    NEAR_FINE, at least APART apart, each to a fraction of a grid step, z against S's own spread over all its velocities."""
    dv = vs[1] - vs[0]
    vals = S[np.isfinite(S)]
    med = np.median(vals)
    mad = 1.4826 * np.median(np.abs(vals - med)) + 1e-12
    f = np.nan_to_num(S, nan=-np.inf)
    peak = (f == ndimage.maximum_filter(f, size=3)) & np.isfinite(f)
    near = np.hypot(*np.meshgrid(vs - vx, vs - vy, indexing="xy")) <= NEAR_FINE
    found = sorted(((f[i, j], i, j) for i, j in np.argwhere(peak & near)), reverse=True)
    out = []
    for value, i, j in found:
        dx, dy = _sub(f, i, j)
        v = (float(vs[j] + dx * dv), float(vs[i] + dy * dv))
        if all(np.hypot(v[0] - a, v[1] - b) >= APART for a, b, _ in out):
            out.append((v[0], v[1], float((value - med) / mad)))
    return out


def read_block(block, down=1, seed=0, exclude=None):
    """One block of box-reduced frames: the fast search and the slow, each with its shuffled nulls, the one that stands,
    and its tests. A dict of plain numbers, velocities in px/frame of the file, or None where the block has nothing to read
    (see `reason`)."""
    r0, r1, c0, c1 = active_box(block)
    fr = block[:, r0:r1, c0:c1]
    ex = None if exclude is None else exclude[r0:r1, c0:c1]
    change = float(np.mean(np.abs(np.diff(fr, axis=0)).mean((1, 2)) > 0.02))
    x, masked = prep(fr, ex)
    band, fy, fx = band_of(x.shape[1:], down)
    sp = Spectra(x, band, fy, fx)
    rng = np.random.default_rng(seed)
    orders = [rng.permutation(sp.F.shape[0]) for _ in range(SURROGATES)]
    res = []
    for lags, vmax, dv in (FAST, SLOW):
        rm = sp.maps(lags)
        S, vs = vmap(rm, vmax, dv)
        vx, vy, s, z = _top(S, vs)
        null = [_top(vmap(sp.maps(lags, o), vmax, dv)[0], vs)[3] for o in orders]
        res.append(dict(rm=rm, S=S, vs=vs, vx=vx, vy=vy, s=s, z=z, null=null, vmax=vmax))
    b = res[1] if res[1]["z"] >= 1.5 * max(res[1]["null"]) else res[0]
    vx, vy = b["vx"], b["vy"]
    second = second_peak(b["S"], b["vs"], (vx, vy))
    p, m = sp.gain(vx, vy), sp.gain(-vx, -vy)
    row = dict(frames=int(fr.shape[0]), changing=change, down=down, grid=b["vmax"], masked=masked,
               vx=vx * down, vy=vy * down, S=b["s"], z=b["z"], null_z=float(max(b["null"])),
               vx2=None if second is None else second[0] * down, vy2=None if second is None else second[1] * down,
               S2=None if second is None else second[2], gain=p, gain_back=m, hold=None, fine_vx=None, fine_vy=None, fine_z=None, layer2_vx=None, layer2_vy=None, layer2_z=None)
    if b["z"] >= Z_MIN:                   # the search is seconds, and asked only of a reading that may stand
        row["hold"] = holds(sp, vx, vy)[0]
    if b is res[0]:                       # the slow grid's reading is fine already, and the upper band cannot reach under RHO
        band2, fy2, fx2 = band_of(x.shape[1:], down, *UPPER)
        S2, vs2 = vmap(Spectra(x, band2, fy2, fx2).maps(FAST[0]), FAST[1], FAST[2])
        places = [q for q in finer(S2, vs2, vx, vy) if q[2] >= Z_FINE]
        if places:
            row.update(fine_vx=places[0][0] * down, fine_vy=places[0][1] * down, fine_z=places[0][2])
        if len(places) > 1:
            row.update(layer2_vx=places[1][0] * down, layer2_vy=places[1][1] * down, layer2_z=places[1][2])
    return row


def exclusion(shape, down, tracks, s, n, half=16):
    """The places of the tracked things over a block's frames s..s + n - 1, as a mask of the reduced picture: what moves on its
    own is not the scene. `tracks` are {frame: (x, y)}."""
    ex = np.zeros(shape, bool)
    for trk in tracks or ():
        for m in range(s, s + n):
            if m in trk:
                x, y = int(trk[m][0] / down), int(trk[m][1] / down)
                ex[max(y - half, 0):y + half + 1, max(x - half, 0):x + half + 1] = True
    return ex


_G = {}


def _init(video, fps, down, tracks, n, size):
    _G.update(video=video, fps=fps, down=down, tracks=tracks, n=n, size=size)


def _one(s):
    """The block from frame s, read, with its first frame: small enough for a pool's pipe."""
    down = _G["down"]
    fr = frames(_G["video"], s, s + _G["n"] - 1, down, _G["fps"], _G["size"])
    if fr.shape[0] < MIN_FRAMES:
        return dict(start=s, frames=int(fr.shape[0]), passed=False, reason="too few frames")
    row = read_block(fr, down, seed=s, exclude=exclusion(fr.shape[1:], down, _G["tracks"], s, fr.shape[0]))
    return dict(row, start=s)


def block_starts(n0, n1, sample=None):
    """Where the blocks of frames n0..n1 start: end to end, or `sample` of them spread evenly over the clip."""
    n = n1 - n0 + 1
    if n < MIN_FRAMES:
        return []
    count = max(n // BLOCK, 1)
    if sample and sample < count:
        return [int(s) for s in np.unique(np.linspace(n0, n1 - BLOCK + 1, sample).astype(int))]
    return [n0 + i * BLOCK for i in range(count)]


def read_clip(video, n0=None, n1=None, tracks=(), sample=None, starts=None, procs=None, progress=None, stop=None):
    """The blocks of a clip, read, in order: [row]. `starts` names them, else `block_starts`."""
    info = probe(video)
    fps = float(info["fps"])
    n0, n1 = n0 or 1, min(n1 or info["frames"], info["frames"])
    down = down_of(info["width"])
    starts = block_starts(n0, n1, sample) if starts is None else list(starts)
    n = min(BLOCK, n1 - n0 + 1)
    return pooled(procs, _one, starts, _init, (str(video), fps, down, tracks, n, (info["width"], info["height"])), progress=progress,
                  stop=stop, what="Scene", pixels=int(info["width"]) * int(info["height"]) // (down * down))


# ---- the gate ------------------------------------------------------------------------------------------------------
Z_MIN = 15.2                     # the peak against S's own spread: the 234-block shuffled null's own maximum (the survey's)
Z_FINE = 9.0                     # the upper band's own peak: above the largest of 86 still-camera blocks' top peaks anywhere (8.6)
BACK_MIN = 1.4                   # stack along v over stack along -v: about the 99th percentile of the coded null (1.38)
HOLD_MIN = 0.07                  # the two halves' coherence: above all 258 searches on the still cameras (at v, -v and turned: 0.068)
SLOWEST = 1.0                    # reduced px/frame: under this the first lag drops out of S, which steps up on a ring. 9 of the coded null's 13
#                                  strongest blocks sit on it (0.78-0.97), and on PR123 "reads" hold their speed and turn every block
FINE_FROM = 4.0                  # reduced px/frame: the upper band is believed only this far from the residue it keeps about zero


def judge(b):
    """(passed, reason): whether a block's reading stands. `reason` is what stopped it, or "read"."""
    if b.get("vx") is None:
        return False, b.get("reason", "nothing to read")
    if b["changing"] < 0.5:
        return False, "the picture is frozen"
    if b["z"] < Z_MIN:
        return False, "no peak over the null"
    if np.hypot(b["vx"], b["vy"]) < SLOWEST * b["down"]:
        return False, "too slow to tell from what stayed put"
    if max(abs(b["vx"]), abs(b["vy"])) >= (FAST[1] - 2 * FAST[2]) * b["down"]:
        return False, "at the edge of the search: faster than it can read"
    if b["gain"] < BACK_MIN * max(b["gain_back"], 1e-9):
        return False, "the stack does not tell v from -v"
    if b["hold"] is None or b["hold"] < HOLD_MIN:
        return False, "the picture does not last the block"
    return True, "read"


def velocity(b):
    """A block's velocity in px/frame: the upper band's where it stands, on a scene at least FINE_FROM fast and within half the low band's
    speed of it, else the low band's. The upper band keeps a residue of what stayed put about zero, and a slow scene's reading would snap
    onto it (PR085: 5.5 px/frame read as 0.9)."""
    speed = float(np.hypot(b["vx"], b["vy"]))
    if b.get("fine_vx") is None or speed < FINE_FROM * b["down"] or np.hypot(b["fine_vx"] - b["vx"], b["fine_vy"] - b["vy"]) > 0.5 * speed:
        return b["vx"], b["vy"]
    return b["fine_vx"], b["fine_vy"]


def judged(blocks):
    """The blocks with `passed` and `reason` set."""
    for b in blocks:
        b["passed"], b["reason"] = judge(b)
    return blocks


SETTINGS = dict(block=BLOCK, wide=WIDE, band=BAND, fast=FAST, slow=SLOW, rho=RHO, surrogates=SURROGATES, upper=UPPER, near=NEAR_FINE,
                apart=APART, z_fine=Z_FINE, near_hold=NEAR_HOLD, step_hold=STEP_HOLD)

COLUMNS = ["start", "frames", "t_s", "best_vx_px_frame", "best_vy_px_frame", "vx_px_frame", "vy_px_frame", "z", "null_z", "S", "fine_vx_px_frame", "fine_vy_px_frame", "fine_z",
           "layer2_vx_px_frame", "layer2_vy_px_frame", "layer2_z", "vx2_px_frame", "vy2_px_frame", "S2", "gain", "gain_back",
           "hold", "masked", "passed", "reason", "tpl_vx_px_frame", "tpl_vy_px_frame", "tpl_pairs_read",
           "tpl_pairs_tried"]
_OLD = dict(vx_px_frame="vx", vy_px_frame="vy", vx2_px_frame="vx2", vy2_px_frame="vy2", tpl_vx_px_frame="tpl_vx", tpl_vy_px_frame="tpl_vy",
            fine_vx_px_frame="fine_vx", fine_vy_px_frame="fine_vy", layer2_vx_px_frame="layer2_vx", layer2_vy_px_frame="layer2_vy")


def write_csv(path, blocks):
    """One row a block: what was read and how it stood, passed or not, and the reason. v is image motion in px/frame of the
    file, +x right, +y down, as `layers`' shifts; best is the one `velocity` gives; the tpl columns are the templates' third pass
    where it ran."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(COLUMNS)
        for b in judged(blocks):
            best = velocity(b) if b.get("vx") is not None else (None, None)
            row = [best[0] if c == "best_vx_px_frame" else best[1] if c == "best_vy_px_frame" else b.get(_OLD.get(c, c)) for c in COLUMNS]
            wr.writerow(["" if v is None else round(v, 4) if isinstance(v, float) else v for v in row])


def read_csv(path):
    """A <tag>_scene.csv back as rows of numbers: [dict] with `COLUMNS`' names, an empty cell None, `passed` a bool and `reason` a string."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            row = {}
            for key, val in r.items():
                if key == "passed":
                    row[key] = val == "True"
                elif key == "reason":
                    row[key] = val
                elif val in ("", None):
                    row[key] = None
                else:
                    row[key] = int(val) if key in ("start", "frames", "tpl_pairs_read", "tpl_pairs_tried") else float(val)
            rows.append(row)
    return rows


def as_layers(scene_csv, fps, path, k=5):
    """A <tag>_scene.csv's blocks that passed, written as a `layers` CSV for `slew` to read when it is asked to (`--scene-blocks`):
    every pair inside a block the block's velocity over k frames, and the frames no block read left empty, so the path has a
    gap there and starts a new stretch. A block's velocity is its steadiest, held over its 60 frames: on a block across a
    reversal it is one side of it (method 41). No shift error: `slew` weighs these pairs as its median pair."""
    with open(scene_csv, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("best_vx_px_frame")]
    if not rows:
        raise ValueError(f"{scene_csv}: no block was read")
    first, last = min(int(r["start"]) for r in rows), max(int(r["start"]) + int(r["frames"]) - 1 for r in rows)
    shift = {}
    for r in rows:
        if r["passed"] == "True":
            vx, vy = float(r["best_vx_px_frame"]), float(r["best_vy_px_frame"])
            for a in range(int(r["start"]), int(r["start"]) + int(r["frames"]) - k):
                shift[a] = (vx * k, vy * k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["frame", "t_s", f"all_dx{k}", f"all_dy{k}", "groups", "over_frames"])
        for a in range(first, last - k + 1):
            v = shift.get(a)
            wr.writerow([a, round((a - 1) / fps, 4)] + ([round(v[0], 3), round(v[1], 3), 1, k] if v else ["", "", "", ""]))
    return len(shift)


def summary(blocks):
    """A clip's blocks as a stage's fields: how many read and at what speeds, with the floor the reading has."""
    judged(blocks)
    read = [b for b in blocks if b["passed"]]
    vel = [velocity(b) for b in read]
    speed = [float(np.hypot(*v)) for v in vel]
    why = {}
    for b in blocks:
        if not b["passed"]:
            why[b["reason"]] = why.get(b["reason"], 0) + 1
    return dict(blocks=len(blocks), read=len(read), of="the scene under the sensor's pattern, block by block",
                speed_px_frame=dict(median=float(np.median(speed)), min=min(speed), max=max(speed)) if speed else None,
                velocity_px_frame=[float(np.median([v[0] for v in vel])), float(np.median([v[1] for v in vel]))] if read else None,
                fine=sum(1 for b in read if velocity(b) != (b["vx"], b["vy"])), two_layers=sum(1 for b in read if b.get("layer2_vx") is not None),
                templates_read=sum(1 for b in blocks if b.get("tpl_pairs_read")), not_read=why,
                block_frames=BLOCK, floor_dn_rms=1.0)


def reported(s):
    """The line a report prints beside `layers`' NO POWER (the maintainer's choice, 2026-11-02: beside it, not in its place), or None
    where no block was read."""
    if not s or not s.get("read"):
        return None
    sp, v = s["speed_px_frame"], s["velocity_px_frame"]
    return (f"read by whole blocks of {s['block_frames']} frames on {s['read']} of {s['blocks']}: the scene moves "
            f"{sp['min']:.1f}-{sp['max']:.1f} px/frame (median {sp['median']:.1f}; velocity {v[0]:+.1f}, {v[1]:+.1f}). The pattern held the "
            "templates at zero, so a rate above against the background is against a scene read as still (method 41)")


def said(s):
    """What a stage prints of `summary`'s fields, line by line."""
    L = [f"the scene under the sensor's pattern: read on {s['read']} of {s['blocks']} blocks of {s['block_frames']} frames"]
    if s["speed_px_frame"]:
        sp = s["speed_px_frame"]
        L[0] += (f", {sp['min']:.1f}-{sp['max']:.1f} px/frame (median {sp['median']:.1f}, "
                 f"velocity {s['velocity_px_frame'][0]:+.1f}, {s['velocity_px_frame'][1]:+.1f})")
    if s["fine"]:
        L.append(f"  the band above read it again on {s['fine']} of them, fine to a fraction of a px/frame"
                 + (f"; on {s['two_layers']} it found two places, which may be two layers" if s["two_layers"] else ""))
    if s["templates_read"]:
        L.append(f"  templates read it too, with each pixel's block mean out, on {s['templates_read']} blocks")
    if s["not_read"]:
        L.append("  not read: " + "; ".join(f"{n}: {w}" for w, n in sorted(s["not_read"].items(), key=lambda kv: -kv[1])))
    L.append(f"  a floor: a coded clip loses motion fainter than about {s['floor_dn_rms']:.0f} DN rms, so unread means none above that, "
             "not none. Blocks are this stage's own, in <tag>_scene.csv: no other stage takes them.")
    return L


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--track", action="append", default=[], metavar="CSV", help="a tracked object to keep out of the reading (repeat)")
    ap.add_argument("--sample", type=int, help="read this many blocks spread over the clip, not every block")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>)")
    ap.add_argument("--procs", type=int, default=None, help=PROCS_HELP)
    ap.add_argument("--json", action="store_true", help="print the reading as JSON on stdout, its numbers as fields (the envelope every "
                    "command prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        found, clip = _main(args)
    if args.json:
        emit(found.envelope("scene", inputs_of(args), clip, said=lines))
    return 0


def _main(args):
    from . import forensics as vf
    video, tag, _ = vf.resolve(args.video)
    clip = vf.Clip(video, None, args.n0, args.n1, extract=False)
    out = vf.out_prefix(args.out, tag, vf.named(args.n0, args.n1, clip))
    tracks = [vf.read_track(t) for t in args.track]
    blocks = read_clip(video, clip.n0, clip.n1, tracks=tracks, sample=args.sample, procs=args.procs, progress=to_stderr())
    for b in blocks:
        b["t_s"] = round(float(clip.t(b["start"])), 4)
    fields = summary(blocks)
    fields["rows"] = blocks
    write_csv(f"{out}_scene.csv", blocks)
    print("\n".join(said(fields)))
    short = [("scene", f"no block to read: a block needs {MIN_FRAMES} frames or more")] if not blocks else []
    return Found("scene", {"the scene": said(fields)[0]}, fields, no_power=short, files=[f"{out}_scene.csv"]), clip


if __name__ == "__main__":
    raise SystemExit(main())
