#!/usr/bin/env python3
"""`mcdonald slew` against a slew it did not see: a rendered pan with a north pointer drawn on a
coarse grid, and k known.

A rigid textured scene is seen by a camera that first holds the ground still while the
platform's motion turns the pointer at HOLD deg/s (the scene does not move), then slews: an
extra turn in azimuth of AZ_DEG over SLEW_S seconds, eased in and out, with an elevation
change in step (EL_SHARE of it), then holds again. The scene moves across the image by
k cos(e) per degree of the extra turn and down by k per degree of elevation; the pointer, a
white "N" with a black edge at a fixed radius from the reticle, is drawn at theta = theta0 +
HOLD t + the extra turn, its place rounded to a GRID-pixel grid as PURSUE overlays are (PR148's
moves in steps of about 3.25 px across). Then what a sensor video does: grain, one frame in
REPEAT_EVERY repeated, and an H.264 encode.

`mcdonald symbology` (template, every frame), `mcdonald layers` and `mcdonald slew` are run
on it as a user would run them, and the c it reports is compared with k cos(e).

    python tools/slew_selftest.py [--out DIR] [--grid 1.6] [--az 2.0] [--el-share 0.3] [--pointer dial|heading]

--pointer heading draws a pointer that turns with the platform only (north against the aircraft's
heading): it registers no slew, and the stage must claim no k, only a floor or nothing.
"""
import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

W, H, FPS = 960, 540, 30
K_PX_PER_DEG = 600.0          # a 1.6-deg field across 960 px
DEPRESSION = 30.0
HOLD = 0.33                   # deg/s: the pointer's turn while the camera holds the ground (PR148: 0.33)
THETA0 = 250.0
REPEAT_EVERY = 9              # PR148 repeats about one frame in nine
FONT = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf"
SRC = Path(__file__).resolve().parent.parent / "src"


def ease(t, t0, dur):
    """0 before t0, 1 after t0 + dur, a cosine ramp between."""
    x = np.clip((t - t0) / dur, 0, 1)
    return 0.5 - 0.5 * np.cos(np.pi * x)


def world(w, h, rng):
    """A rigid texture: two scales of smoothed noise, like cloud tops or land."""
    a = ndimage.gaussian_filter(rng.normal(0, 1, (h, w)), 3) * 3.0 + ndimage.gaussian_filter(rng.normal(0, 1, (h, w)), 14) * 10
    a = (a - a.mean()) / a.std()
    return np.clip(128 + 32 * a, 20, 235)


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def render(out, n_frames, grid, az_deg, slew_t0, slew_s, el_share, seed, pointer="dial"):
    rng = np.random.default_rng(seed)
    t = np.arange(n_frames) / FPS
    extra = az_deg * ease(t, slew_t0, slew_s)                       # the turn beyond the hold, deg of azimuth
    c_true = K_PX_PER_DEG * math.cos(math.radians(DEPRESSION))
    X = c_true * extra                                              # the scene across, px (right positive)
    Y = K_PX_PER_DEG * el_share * extra                             # and down, px
    theta = THETA0 + HOLD * t + (extra if pointer == "dial" else 0.0)
    pad = 40
    big = world(W + int(abs(X).max()) + 2 * pad, H + int(abs(Y).max()) + 2 * pad, rng)
    bore = (W / 2, H / 2)
    r = 0.28 * H
    f = font(18)
    frames = out / "frames_src"
    frames.mkdir(parents=True, exist_ok=True)
    first_box = None
    prev = None
    for n in range(n_frames):
        if n and n % REPEAT_EVERY == 0:
            img = prev                                               # a repeated frame: the one before, again
        else:
            ox, oy = pad + X.max() - X[n], pad + Y.max() - Y[n]      # the window moves left as the scene moves right
            i0, j0 = int(math.floor(oy)), int(math.floor(ox))
            crop = big[i0:i0 + H + 2, j0:j0 + W + 2]
            crop = ndimage.shift(crop, (-(oy - i0), -(ox - j0)), order=1, mode="nearest")[:H, :W]
            crop = crop + rng.normal(0, 2.0, crop.shape)
            img = Image.fromarray(np.clip(crop, 0, 255).astype(np.uint8)).convert("RGB")
            d = ImageDraw.Draw(img)
            cx, cy = bore
            for (x0, y0, x1, y1) in ((cx - 60, cy, cx - 15, cy), (cx + 15, cy, cx + 60, cy),
                                     (cx, cy - 60, cx, cy - 15), (cx, cy + 15, cx, cy + 60)):
                d.line((x0, y0, x1, y1), fill=(255, 255, 255), width=2)
            th = math.radians(theta[n])
            gx = round((cx + r * math.sin(th)) / grid) * grid           # the overlay's coarse grid
            gy = round((cy - r * math.cos(th)) / grid) * grid
            d.text((gx, gy), "N", font=f, fill=(255, 255, 255), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
            if first_box is None:
                b = d.textbbox((gx, gy), "N", font=f, anchor="mm", stroke_width=2)
                first_box = (int(b[0]) - 3, int(b[1]) - 3, int(b[2]) + 3, int(b[3]) + 3)
        img.save(frames / f"f{n + 1:05d}.png")
        prev = img
    video = out / "slew_synth.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", str(frames / "f%05d.png"),
                    "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(video)], check=True)
    truth = dict(c_px_per_deg=c_true, k_px_per_deg=K_PX_PER_DEG, depression_deg=DEPRESSION, hold_deg_per_s=HOLD,
                 az_deg=az_deg, slew_t0=slew_t0, slew_s=slew_s, el_share=el_share, grid_px=grid, pointer=pointer,
                 bore=list(bore), r_px=r, tpl_box=list(first_box))
    (out / "truth.json").write_text(json.dumps(truth, indent=1))
    return video, truth


def mcdonald(*args):
    env = dict(os.environ, PYTHONPATH=str(SRC))
    r = subprocess.run([sys.executable, "-m", "mcdonald.cli", *map(str, args)], capture_output=True, text=True, env=env)
    return r.returncode, r.stdout, r.stderr


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default="slew_selftest")
    ap.add_argument("--grid", type=float, default=1.6, help="the overlay's grid, px (PR148's 3.25 at twice this size)")
    ap.add_argument("--az", type=float, default=2.0, help="the slew's extra turn in azimuth, deg")
    ap.add_argument("--el-share", type=float, default=0.3, help="elevation change per degree of azimuth in the slew")
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--pointer", default="dial", choices=["dial", "heading"])
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    n = int(args.seconds * FPS)
    video, truth = render(out, n, args.grid, args.az, 0.4 * args.seconds, 0.3 * args.seconds, args.el_share, args.seed,
                          args.pointer)
    print(f"rendered {video}: k cos(e) = {truth['c_px_per_deg']:.1f} px/deg; the glyph's box {truth['tpl_box']}")
    work = out / "frames"
    bore = ",".join(f"{v:g}" for v in truth["bore"])
    box = ",".join(map(str, truth["tpl_box"]))
    for cmd in (("symbology", video, "--workdir", work, "--step", 1, "--method", "template", "--bore", bore, "--tpl-box", box,
                 "--search", "30,60,60", "--out", out),
                ("layers", video, "--workdir", work, "--out", out)):
        code, so, se = mcdonald(*cmd)
        print(f"mcdonald {cmd[0]}: exit {code}")
        if code not in (0, 5):
            print(se[-3000:])
            return 1
    code, so, se = mcdonald("slew", video, "--out", out, "--json")
    print(se[-4000:])
    res = json.loads(so)["results"]
    c, floor, true = res.get("c_px_per_deg"), res.get("c_at_least_px_per_deg"), truth["c_px_per_deg"]
    verdict = dict(truth=true, pointer=args.pointer, measured=c, ratio=(c / true) if c else None, floor=floor,
                   windows=[{k: w.get(k) for k in ("window", "registered", "c_px_per_deg", "c_at_least_px_per_deg",
                                                   "c_forward_px_per_deg", "c_p16_p84", "bracket_px_per_deg", "tilt_deg",
                                                   "hold_rate_deg_per_s", "lever_over_scatter", "no_power")}
                            for w in res["windows"]])
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    print(json.dumps(verdict, indent=1))
    if args.pointer == "heading":
        ok = c is None                        # a blind pointer must not yield a k; a floor is all it can give
        why = f"no k claimed (floor {floor})" if ok else f"claimed k cos(e) = {c:.0f} from a pointer blind to the slew"
    elif c is not None:
        ok = abs(c / true - 1) <= 0.10
        why = f"k cos(e): measured {c:.1f} against {true:.1f}"
    else:
        ok = floor is not None and floor <= true
        why = f"not measured; floor {floor} against {true:.1f}"
    print("PASS" if ok else "FAIL", why)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
