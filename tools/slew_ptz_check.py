#!/usr/bin/env python3
"""`mcdonald slew` against real footage whose answer is known: a broadcast camera with every frame's pan, tilt and
focal length.

PTZ-SLAM's soccer sequence (reference data `ptzslam_soccer/`, its README): 330 consecutive 1280x720 frames from a
camera on a fixed base, the pan reversing three times while the zoom holds within +-3 % over frames 31-196. The
pointer is the ground truth's pan (theta = -pan, a dial; once exact and once on a 0.25-deg grid, as PURSUE's are
drawn), the scene is `mcdonald layers` with the score banner box-masked, and `mcdonald slew --still` (a still
platform: no hold term) must read c = f pi/180 cos(tilt), averaged over its window. The camera is real, the
compression is a broadcast's, the players move through the scene; only the pointer is not read off the picture.

    python3 tools/slew_ptz_check.py [--work DIR]

Result (2026-10-20): c 73 px/deg (16-84 % 73-74) against 72.0 over t 1.0-6.5 s, with either pointer, with and
without --still; the wide end (t 9-11 s, a 1.1-deg pan) 37 against 33.3 with --still and refused without it.
"""
import argparse
import csv
import json
import math
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
from reference_data import root   # noqa: E402

SRC = Path(__file__).resolve().parent.parent / "src"
FPS = 30.0                     # the dataset gives frames, not a rate; with --still the time base does not enter c
FIRST = 515                    # the first image's number
BANNER = "50,50,500,110"       # the blurred score banner, x0,y0,x1,y1
WINDOW = (1.0, 6.5)            # frames 31-196: the zoom within +-3 %, three reversals of the pan


def mcdonald(*args):
    env = dict(os.environ, PYTHONPATH=str(SRC))
    r = subprocess.run([sys.executable, "-m", "mcdonald.cli", *map(str, args)], capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr


def build(data, work):
    """The clip (an mp4 for its metadata, and its frames as f%05d.png numbered from 1) and the truth."""
    import scipy.io as sio
    from PIL import Image
    frames = work / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    ptz = sio.loadmat(data / "ground_truth.mat")["ptz"]
    if not (frames / f"f{len(ptz):05d}.png").exists():
        with zipfile.ZipFile(data / "soccer_images.zip") as z:
            for i in range(len(ptz)):
                with z.open(f"images/{FIRST + i:08d}.jpg") as f:
                    Image.open(f).convert("RGB").save(frames / f"f{i + 1:05d}.png")
    video = work / "ptz_soccer.mp4"
    if not video.exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(frames / "f%05d.png"),
                        "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(video)], check=True)
    return video, frames, ptz


def pointer(path, ptz, step=None):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame", "t_s", "glyph_x", "glyph_y", "r_px", "theta_deg", "quality"])
        for i, (pan, tilt, fl) in enumerate(ptz):
            th = -pan if step is None else round(-pan / step) * step
            th %= 360.0
            r = math.radians(th)
            w.writerow([i + 1, round(i / FPS, 4), round(640 + 100 * math.sin(r), 4), round(360 - 100 * math.cos(r), 4),
                        100.0, round(th, 4), 1.0])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--work", default="slew_ptz_check")
    a = ap.parse_args()
    data = root() / "ptzslam_soccer"
    if not (data / "ground_truth.mat").exists():
        print(f"no {data}: see the reference data's README for where the PTZ-SLAM soccer sequence comes from")
        return 2
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    video, frames, ptz = build(data, work)
    t = np.arange(len(ptz)) / FPS
    true_c = ptz[:, 2] * math.pi / 180 * np.cos(np.radians(ptz[:, 1]))
    m = (t >= WINDOW[0]) & (t <= WINDOW[1])
    truth = float(true_c[m].mean())
    out = work / "run"
    out.mkdir(exist_ok=True)
    code, so, se = mcdonald("layers", video, "--workdir", frames, "--k", 5, "--mask-box", BANNER, "--out", out)
    if code:
        print(se[-2000:])
        return 1
    layers = next(out.glob("*_layers.csv"))
    ok = True
    for name, step in (("exact", None), ("grid 0.25 deg", 0.25)):
        north = out / f"north_{'exact' if step is None else 'grid'}.csv"
        pointer(north, ptz, step)
        for still in (True, False):
            code, so, se = mcdonald("slew", video, "--north", north, "--layers", layers, "--out", out, "--json",
                                    "--window", f"{WINDOW[0]}:{WINDOW[1]}", *(["--still"] if still else []))
            res = json.loads(so)["results"]
            c = res.get("c_px_per_deg")
            good = c is not None and abs(c / truth - 1) <= 0.05
            ok &= good
            print(f"{'PASS' if good else 'FAIL'}  pointer {name}, {'--still' if still else 'hold fitted'}: c {c} against "
                  f"{truth:.1f} px/deg (f pi/180 cos(tilt) over t {WINDOW[0]}-{WINDOW[1]} s)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
