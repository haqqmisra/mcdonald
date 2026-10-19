"""Does `mcdonald stabilize` hold a filmed screen still? Synthetic phones with known answers.

A small display -- a reticle and a ring on a grey field with the detector's fixed pattern and
fresh grain every frame, as on the Oman AC-130 display -- is filmed through a known
homography per frame (a wandering hand, a roll, a change of distance, a keystone), with a
frame repeated now and then as a variable-rate phone padded to a constant rate does. The
stage's answer, carried back through the truth, must be one fixed map for every frame.

    python3 tests/test_stabilize.py        # or: pytest tests/

No video data needed: the clips are made here (ffmpeg, lossless FFV1).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import stabilize as st  # noqa: E402
from mcdonald.clip import Clip  # noqa: E402

RNG = np.random.default_rng(20261018)
FAIL = []
W, H = 480, 320


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def display_drawing():
    m = np.zeros((H, W), np.float32)
    cx, cy = W // 2, H // 2
    m[cy - 1:cy + 1, 40:cx - 25] = m[cy - 1:cy + 1, cx + 25:W - 40] = 1
    m[20:cy - 25, cx - 1:cx + 1] = m[cy + 25:H - 20, cx - 1:cx + 1] = 1
    for x in list(range(cx - 60, 39, -45)) + list(range(cx + 60, W - 39, 45)):
        m[cy - 6:cy + 6, x - 1:x + 1] = 1
    for y in list(range(cy - 60, 19, -45)) + list(range(cy + 60, H - 19, 45)):
        m[y - 1:y + 1, cx - 6:cx + 6] = 1
    yy, xx = np.mgrid[:H, :W]
    r = np.hypot(xx - (cx + 70), yy - (cy + 60))
    m[(r > 9) & (r < 12)] = 1
    return ndimage.gaussian_filter(m, 0.6)


def hands(n, still=False):
    """G_n: display px -> video px."""
    if still:
        return [np.eye(3) for _ in range(n)]
    t = np.arange(n) / 30.0
    walk = ndimage.gaussian_filter1d(np.cumsum(RNG.normal(0, 1.5, (n, 2)), 0), 3, axis=0)
    walk -= walk.mean(0)
    out = []
    c = np.array([[1, 0, -W / 2], [0, 1, -H / 2], [0, 0, 1.0]])
    for k in range(n):
        a = np.radians(0.8 * np.sin(2 * np.pi * t[k] / 1.3))
        s = 1.05 + 0.03 * np.sin(2 * np.pi * t[k] / 0.9)
        R = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
        K = np.array([[1, 0.015, 0], [0, 1, 0], [6e-5, 3e-5, 1]])
        T = np.array([[1, 0, W / 2 + walk[k, 0]], [0, 1, H / 2 + walk[k, 1]], [0, 0, 1.0]])
        G = T @ R @ np.diag([s, s, 1]) @ K @ c
        out.append(G / G[2, 2])
    return out


def film(path, n=40, still=False, repeat_every=5):
    drawing = display_drawing()
    fpn = ndimage.gaussian_filter(RNG.normal(0, 8.0, (H, W)), 1.0)
    Gs = hands(n, still)
    truth, frames, last = [], [], None
    for k in range(n):
        if repeat_every and k and k % repeat_every == 0:
            frames.append(last)
            truth.append(truth[-1])
            continue
        g = 110 + fpn + RNG.normal(0, 5.0, (H, W))
        g = g * (1 - drawing) + 235 * drawing
        a = st.warp_to_canvas(g, np.linalg.inv(Gs[k]), W, H, order=1, cval=110.0)
        last = np.clip(ndimage.gaussian_filter(a, 0.8) + RNG.normal(0, 3.0, a.shape), 0, 255).astype(np.uint8)
        frames.append(last)
        truth.append(Gs[k])
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", "30",
                          "-i", "-", "-c:v", "ffv1", "-pix_fmt", "gray", str(path)], stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.tobytes())
    p.stdin.close()
    p.wait()
    return truth


def spread(found, truth):
    """The stage's maps carried back through the truth, at a grid near the drawing: one map
    for every frame if it is right. Returns the rms and worst spread, display px."""
    gu, gv = np.meshgrid(np.linspace(0.25, 0.75, 5) * W, np.linspace(0.25, 0.75, 4) * H)
    gu, gv = gu.ravel(), gv.ravel()
    Hs, (x0, y0, _, _) = found.carry["H"], found.carry["box"]
    maps = np.array([np.stack(st.apply(np.linalg.inv(truth[k]) @ Hs[k + 1], gu + x0, gv + y0), 1) for k in range(len(truth))])
    e = np.hypot(*(maps - np.median(maps, 0)).transpose(2, 0, 1))
    return float(np.sqrt((e ** 2).mean())), float(e.max())


def test_a_filmed_screen_is_held_to_a_fraction_of_a_pixel():
    print("\nstabilize: a reticle on a grainy display, filmed by a wandering hand")
    with tempfile.TemporaryDirectory() as d:
        truth = film(Path(d) / "phone.mkv")
        clip = Clip(Path(d) / "phone.mkv", Path(d) / "frames")
        found = st.measure(clip, procs=0, write=False)
        rms, worst = spread(found, truth)
        f = found.fields
        check(f["aligned"] == 40 and f["lost"] == 0, "every frame aligned", f"{f['aligned']} aligned, {f['lost']} lost")
        check(rms < 0.5 and worst < 1.5, "held to the truth", f"rms {rms:.2f} px, worst {worst:.2f} px")
        check(f["repeats"] == 7, "the repeated frames are found", f"{f['repeats']} of 7")
        check(f["drawing_persistence"] is not None and f["drawing_persistence"] >= st.PERSIST_MIN,
              "the drawing held at the start is the one at the end", f"{f['drawing_persistence']}")
        check(not found.no_power, "nothing said to be missing", str(found.no_power))


def test_a_native_recording_is_left_alone():
    print("\nstabilize: a native recording (the drawing never moves) is said to be one")
    with tempfile.TemporaryDirectory() as d:
        film(Path(d) / "native.mkv", n=24, still=True, repeat_every=0)
        clip = Clip(Path(d) / "native.mkv", Path(d) / "frames")
        found = st.measure(clip, procs=0, write=False)
        check(found.fields["native"], "native", f"hand {found.fields['hand_ptp_px']} px")
        check(any("native" in w for _, w in found.no_power), "and said to have nothing to remove")


def test_black_inside_the_picture_is_drawing_and_a_pillarbox_is_not():
    print("\nstabilize: a redaction box is kept, a pillarbox band is left out")
    g = np.full((200, 300), 120.0)
    g[:, :40] = 0                          # pillarbox, from the frame's edge
    g[80:120, 140:200] = 0                 # a box inside the picture
    m = st.not_picture(g)
    check(m[:, :40].all(), "the pillarbox band is left out")
    check(not m[95:105, 160:180].any(), "the box inside the picture is kept")
    check(m[0].all() and m[:, -1].all(), "the frame's own edge pixels are left out")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{'ALL PASS' if not FAIL else f'{len(FAIL)} FAILED: ' + ', '.join(FAIL)}")
    sys.exit(1 if FAIL else 0)
