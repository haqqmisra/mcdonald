#!/usr/bin/env python3
"""`mcdonald stabilize` against a phone it did not see: a native sensor clip filmed by a
simulated hand, with the true homography of every frame known.

The display is a native PURSUE clip with a reticle (PR144 by default: its overlay is fixed
in its frame, and its sensor slews, so the stage must hold the drawing and not the scene).
Each frame is shown to a pinhole "phone" through a known homography G_n (display ->
video): a wandering hand (a random walk of a few hundred pixels), a tremor at TREMOR_HZ
and an airframe's vibration at VIB_HZ, a slow roll and a change of distance, and a fixed
keystone, as a phone held up to a screen does. Then what a phone does to a picture: a
blur, its vignetting, grain, a repeated frame where a variable rate is padded to a constant
one (one in REPEAT_EVERY), and an H.264 encode.

The stage's H_n maps its canvas to the video, so G_n^-1 H_n maps the canvas to the display
and must be the same map for every frame. Its spread over the frames, at a grid of canvas
points inside the display, is the stage's error in display pixels: reported as rms, 95th
percentile and worst, with and without the frames the stage itself called lost.

    python tools/stabilize_selftest.py [VIDEO] [--frames 150] [--out DIR] [--seed 1]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from mcdonald import stabilize as st          # noqa: E402
from mcdonald.clip import Clip                # noqa: E402

TREMOR_HZ, TREMOR_PX = 9.0, 3.0               # a hand's physiological tremor
VIB_HZ, VIB_PX = 7.7, 1.5                     # an airframe's vibration, folded (PR117's propeller at 30 frames/s)
REPEAT_EVERY = 5
W, H = 1920, 1080
FPS = 30


def hand(n_frames, rng):
    """G_n for every frame: display px -> video px."""
    t = np.arange(n_frames) / FPS
    walk = np.cumsum(rng.normal(0, 4.0, (n_frames, 2)), 0)
    walk = ndimage.gaussian_filter1d(walk, 4, axis=0)
    walk -= walk.mean(0)
    tx = walk[:, 0] + TREMOR_PX * np.sin(2 * np.pi * TREMOR_HZ * t) + VIB_PX * np.sin(2 * np.pi * VIB_HZ * t + 1)
    ty = walk[:, 1] + TREMOR_PX * np.cos(2 * np.pi * TREMOR_HZ * t + 0.3) + VIB_PX * np.sin(2 * np.pi * VIB_HZ * t)
    roll = np.radians(1.5 * np.sin(2 * np.pi * t / 7.0) + 0.3 * rng.normal(0, 1, n_frames).cumsum() / np.sqrt(n_frames))
    scale = 1.15 * (1 + 0.04 * np.sin(2 * np.pi * t / 5.0))
    keystone = np.array([[1, 0.02, 0], [0.0, 1, 0], [2.0e-5, 1.0e-5, 1]])
    c = np.array([[1, 0, -W / 2], [0, 1, -H / 2], [0, 0, 1.0]])
    Gs = []
    for k in range(n_frames):
        R = np.array([[np.cos(roll[k]), -np.sin(roll[k]), 0], [np.sin(roll[k]), np.cos(roll[k]), 0], [0, 0, 1]])
        S = np.diag([scale[k], scale[k], 1.0])
        T = np.array([[1, 0, W / 2 + tx[k]], [0, 1, H / 2 + ty[k]], [0, 0, 1.0]])
        G = T @ R @ S @ keystone @ c
        Gs.append(G / G[2, 2])
    return Gs


def reticle(w, h):
    """A drawing that is fixed on the display, as on the Oman AC-130 display: two long arms with
    a gap at the centre and ticks every 110 px, and a ring off the boresight. 0-1, antialiased."""
    m = np.zeros((h, w), np.float32)
    cx, cy = w // 2, h // 2
    m[cy - 1:cy + 2, 200:cx - 80] = m[cy - 1:cy + 2, cx + 80:w - 200] = 1
    m[80:cy - 80, cx - 1:cx + 2] = m[cy + 80:h - 80, cx - 1:cx + 2] = 1
    for x in list(range(cx - 190, 199, -110)) + list(range(cx + 190, w - 199, 110)):
        m[cy - 12:cy + 13, x - 1:x + 2] = 1
    for y in list(range(cy - 190, 79, -110)) + list(range(cy + 190, h - 79, 110)):
        m[y - 1:y + 2, cx - 12:cx + 13] = 1
    yy, xx = np.mgrid[:h, :w]
    r = np.hypot(xx - (cx + 220), yy - (cy + 220))
    m[(r > 26) & (r < 30)] = 1
    return ndimage.gaussian_filter(m, 0.7)


def film(src, out_mp4, n_frames, rng, workdir, overlay=False, scene="clip"):
    """The simulated phone's video, and the true G of each of its frames (a repeat keeps the
    one before's picture and G). overlay: draw `reticle` on the display, white. scene "flat":
    no picture at all, as at the Oman display's zoom -- a grey level with the detector's fixed
    pattern (fixed on the display, as on PR118) and fresh grain every frame."""
    clip = Clip(src, workdir, 1, n_frames)
    Gs = hand(n_frames, rng)
    ret = reticle(clip.W, clip.H) if overlay else None
    fpn = ndimage.gaussian_filter(rng.normal(0, 9.0, (clip.H, clip.W)), 1.5) if scene == "flat" else None
    yy, xx = np.mgrid[:H, :W]
    vig = 1 - 0.35 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(out_mp4)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    truth, last = [], None
    for k in range(n_frames):
        if k and k % REPEAT_EVERY == 0:
            p.stdin.write(last)
            truth.append(truth[-1])
            continue
        if scene == "flat":
            g = 120 + fpn + ndimage.gaussian_filter(rng.normal(0, 7.0, (clip.H, clip.W)), 1.2)
            rgb = np.repeat(g[..., None], 3, 2).astype(np.float32)
        else:
            rgb = clip.rgb(k + 1).copy()
        if ret is not None:
            rgb = rgb * (1 - ret[..., None]) + 235 * ret[..., None]
        a = st.warp_to_canvas(rgb, np.linalg.inv(Gs[k]), W, H, order=1, cval=0.0)
        a = ndimage.gaussian_filter(a, (1.2, 1.2, 0)) * vig[..., None] + rng.normal(0, 5.0, a.shape)
        last = np.clip(a, 0, 255).astype(np.uint8).tobytes()
        p.stdin.write(last)
        truth.append(Gs[k])
    p.stdin.close()
    p.wait()
    return truth


def score(found_H, ok, truth, box, n_frames):
    """Spread of G_n^-1 H_n over the frames at a grid of canvas points, display px."""
    x0, y0, w, h = box
    gu, gv = np.meshgrid(np.linspace(x0 + 0.15 * w, x0 + 0.85 * w, 9), np.linspace(y0 + 0.15 * h, y0 + 0.85 * h, 7))
    gu, gv = gu.ravel(), gv.ravel()
    maps = []
    for k in range(n_frames):
        n = k + 1
        M = np.linalg.inv(truth[k]) @ found_H[n]
        dx, dy = st.apply(M, gu, gv)
        maps.append(np.stack([dx, dy], 1))
    maps = np.array(maps)                                     # frames x points x 2
    inside = np.all((maps[..., 0] > 0) & (maps[..., 0] < W) & (maps[..., 1] > 0) & (maps[..., 1] < H), 0)
    ref = np.median(maps[:, inside], 0)
    err = np.hypot(*(maps[:, inside] - ref).transpose(2, 0, 1))  # frames x points
    good = np.array([ok[k + 1] for k in range(n_frames)])
    pf = np.sqrt((err ** 2).mean(1))
    out = {}
    for name, sel in (("all", np.ones(n_frames, bool)), ("not_lost", good)):
        e = err[sel]
        out[name] = dict(frames=int(sel.sum()), rms_px=round(float(np.sqrt((e ** 2).mean())), 3),
                         p95_px=round(float(np.percentile(e, 95)), 3), max_px=round(float(e.max()), 3))
    out["worst_frames"] = [int(i + 1) for i in np.argsort(pf)[-5:][::-1]]
    out["grid_points"] = int(inside.sum())
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video", nargs="?", default=str(Path(__file__).resolve().parents[2] / "data/mcdonald/pursue/DOD_111985820.mp4"))
    ap.add_argument("--frames", type=int, default=150)
    ap.add_argument("--out", default="stabilize_selftest")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--procs", type=int, default=None)
    ap.add_argument("--anchor-display", metavar="X0,Y0,X1,Y1",
                    help="a box of the DISPLAY (the source video's pixels) holding its drawing; it is carried into the "
                         "simulated phone's first frame through the true homography and given to the stage as --anchor")
    ap.add_argument("--drawing", choices=("grey", "chroma"), default="grey")
    ap.add_argument("--overlay", action="store_true", help="draw a fixed Oman-style reticle on the display")
    ap.add_argument("--scene", choices=("clip", "flat"), default="clip",
                    help="the display's picture: the clip's own, or flat grey with a fixed pattern and grain (Oman)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    phone = out / "phone.mp4"
    truth = film(args.video, phone, args.frames, rng, out / "src_frames", overlay=args.overlay, scene=args.scene)
    np.save(out / "truth.npy", np.array(truth))
    clip = Clip(phone, out / "phone_frames", 1, args.frames)
    anchor = None
    if args.anchor_display:
        x0, y0, x1, y1 = (float(v) for v in args.anchor_display.split(","))
        cx, cy = st.apply(truth[0], np.array([x0, x1, x1, x0]), np.array([y0, y0, y1, y1]))
        anchor = (float(cx.min()), float(cy.min()), float(cx.max()), float(cy.max()), 1)
    found = st.measure(clip, procs=args.procs, out=str(out / "selftest"), write=False, anchor=anchor, drawing=args.drawing)
    res = score(found.carry["H"], found.carry["ok"], truth, found.carry["box"], args.frames)
    res["stage"] = {k: found.fields[k] for k in ("aligned", "lost", "rho_median", "repeats", "shake_peaks_hz_px",
                                                 "shake_fast_peaks_hz_px", "drawing_persistence", "anchor", "drawing")}
    res["stage"]["no_power"] = found.no_power
    res["planted"] = dict(tremor_hz=TREMOR_HZ, tremor_px=TREMOR_PX, vibration_hz=VIB_HZ, vibration_px=VIB_PX,
                          repeat_every=REPEAT_EVERY)
    (out / "selftest.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
