#!/usr/bin/env python3
"""The flat top's null and power (docs/method.md §42; `forensics.flat_top`, FLAT_TOL, FLAT_K, FLAT_AMP).

How often does an UNCLIPPED peak, drawn through the same chain as a clip -- 8-bit luma, libx264, decoded, its Y plane
read with no conversion -- show FLAT_K of its 3 x 3 core within FLAT_TOL codes of its top, standing FLAT_AMP codes over
its surroundings, or a top at 255? And how often does a peak CLIPPED before the encoder (at 180, a sensor's ceiling; at
235, a camera's studio cut; at 255, the 8-bit top) show it?

Frames 512 x 512, 30 a run, a 12 x 12 grid of Gaussian points 40 px apart, each with its own width (sigma 0.7, 1.0, 1.4,
2.0 or 3.0 px) and amplitude and a random sub-pixel centre on every frame, on a level of 30-140 codes with Gaussian noise
of 1, 2 or 4 codes; yuv420p (chroma 128) through libx264 (high, GOP 30, two B frames) at CRF 14, 20, 26 and 32. Unclipped:
peaks under 250. Clipped: peaks 1.05-3 times the ceiling, cut at it before the encoder. Two seeds gave the constants
(2026-11-07, 207,360 peaks): 30 of 103,680 unclipped peaks called clipped (0.029 %; 0.18 % in the worst cell of width
and CRF, 0.3 % of the peaks there that stand 50 codes up); 89 % of the peaks clipped at 255 called (73 % at CRF 32 to
98 % at CRF 14), 10-12 % of those clipped below it (5-21 % by CRF).

    sbatch -n 1 -c 1 --mem=3G --time=00:40:00 -o logs/%x_%j.out -J flat_null \\
        --wrap "python3 -u tools/flat_top_null.py --out /scratch/flat_null --seed 1"

About two minutes a seed; a second run with --read reads every seed's table in the folder (no video).
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcdonald import forensics as vf  # noqa: E402

W = H = 512
N, G, SP = 30, 12, 40
SIGMAS = np.array([0.7, 1.0, 1.4, 2.0, 3.0])
COLS = ("clipped", "noise", "crf", "sigma", "amp", "ceil", "base", "amp_meas", "top", "on_top", "pre_flat")


def encode(Y, crf, where):
    """N x H x W uint8 luma through libx264 as yuv420p (chroma 128), decoded, its Y plane read as it is."""
    uv = np.full((H // 2, W // 2), 128, np.uint8).tobytes()
    with tempfile.TemporaryDirectory(dir=str(where)) as d:
        enc = Path(d) / "x.mp4"
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-color_range", "tv",
                        "-s", f"{W}x{H}", "-framerate", "30", "-i", "-", "-c:v", "libx264", "-threads", "1", "-profile:v", "high",
                        "-pix_fmt", "yuv420p", "-g", "30", "-bf", "2", "-crf", str(crf), str(enc)],
                       input=b"".join(f.tobytes() + uv + uv for f in Y), check=True)
        dec = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-threads", "1", "-i", str(enc), "-vf", "extractplanes=y",
                              "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(dec, np.uint8).reshape(-1, H, W)[:len(Y)]


def draw(seed, where):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    ry, rx = np.mgrid[-10:11, -10:11]
    c0 = SP // 2 + SP * np.arange(G)
    cx, cy = (a.ravel().astype(float) for a in np.meshgrid(c0, c0))
    rows = []
    for kind in ("unclipped", "clipped"):
        for noise in (1.0, 2.0, 4.0):
            for crf in (14, 20, 26, 32):
                base = rng.uniform(30, 140)
                sig = rng.choice(SIGMAS, G * G)
                if kind == "unclipped":
                    ceil = np.full(G * G, 255.0)
                    amp = np.exp(rng.uniform(np.log(base + 12), np.log(250), G * G)) - base
                else:
                    ceil = rng.choice([180.0, 235.0, 255.0], G * G)
                    amp = ceil * np.exp(rng.uniform(np.log(1.05), np.log(3.0), G * G)) - base
                frames, at = np.empty((N, H, W), np.uint8), []
                for i in range(N):
                    ox, oy = rng.uniform(-0.5, 0.5, G * G), rng.uniform(-0.5, 0.5, G * G)
                    img = base + rng.normal(0, noise, (H, W))
                    for j in range(G * G):
                        x0, y0 = cx[j] + ox[j], cy[j] + oy[j]
                        sl = (slice(int(y0) - 12, int(y0) + 13), slice(int(x0) - 12, int(x0) + 13))
                        img[sl] += amp[j] * np.exp(-((xx[sl] - x0) ** 2 + (yy[sl] - y0) ** 2) / (2 * sig[j] ** 2))
                        if kind == "clipped":
                            img[sl] = np.minimum(img[sl], ceil[j])
                    frames[i] = np.clip(np.round(img), 0, 255)
                    at.append((ox, oy))
                dec = encode(frames, crf, where)
                for i in range(N):
                    ox, oy = at[i]
                    for j in range(G * G):
                        x0, y0 = cx[j] + ox[j], cy[j] + oy[j]
                        xi, yi = int(round(x0)), int(round(y0))
                        p = dec[i][yi - 10:yi + 11, xi - 10:xi + 11].astype(float)
                        rr = np.hypot(rx - (x0 - xi), ry - (y0 - yi))
                        core, level = p[9:12, 9:12], float(np.median(p[(rr >= 6) & (rr <= 9)]))
                        top = core.max()
                        rows.append((kind == "clipped", noise, crf, sig[j], amp[j], ceil[j], base, top - level, top,
                                     int((core >= top - vf.FLAT_TOL - 0.01).sum()),
                                     int((frames[i][yi - 1:yi + 2, xi - 1:xi + 2] >= ceil[j]).sum() >= 3)))
                print(kind, noise, crf, len(rows), flush=True)
    return np.array(rows, float)


def read(tables):
    X = np.vstack(tables)
    c = {k: X[:, i] for i, k in enumerate(COLS)}
    call = (c["top"] >= 255) | ((c["amp_meas"] >= vf.FLAT_AMP) & (c["on_top"] >= vf.FLAT_K))
    unc, clp = c["clipped"] == 0, (c["clipped"] == 1) & (c["pre_flat"] == 1)
    worst = max(call[unc & (c["sigma"] == s) & (c["crf"] == q)].mean() for s in SIGMAS for q in (14, 20, 26, 32))
    print(f"flat top (tol {vf.FLAT_TOL}, k {vf.FLAT_K}, amplitude {vf.FLAT_AMP}): {int(call[unc].sum())} of {int(unc.sum())} unclipped "
          f"peaks called clipped ({100 * call[unc].mean():.3f} %; worst cell of width and CRF {100 * worst:.2f} %)")
    for ce in (180, 235, 255):
        m = clp & (c["ceil"] == ce)
        print(f"  clipped at {ce:.0f} before the encoder: {100 * call[m].mean():.0f} % called ("
              + ", ".join(f"CRF {q} {100 * call[m & (c['crf'] == q)].mean():.0f} %" for q in (14, 20, 26, 32)) + ")")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True, help="a folder for the tables (and the encoder's scratch)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--read", action="store_true", help="only read the tables already in --out")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if not a.read:
        np.save(out / f"flat_top_null_{a.seed}.npy", draw(a.seed, out))
    read([np.load(p) for p in sorted(out.glob("flat_top_null_*.npy"))])


if __name__ == "__main__":
    main()
