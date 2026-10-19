"""Does `mcdonald aspect` tell a body that looks the same from every side from one that does not?

A dark blob loops on a grainy background with a fixed pattern (as a held display shows): with a
constant flux it must not be called; with its flux following its heading by 25 % it must; and a
track that never turns must be said to have no power.

    python3 tests/test_aspect.py        # or: pytest tests/

No video data needed: the clips are made here (ffmpeg, lossless FFV1).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import aspect  # noqa: E402
from mcdonald.clip import Clip  # noqa: E402

FAIL = []
W, H, N, FPS = 560, 320, 300, 30


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def make(path, mod=lambda th: 1.0, loops=True, seed=5):
    rng = np.random.default_rng(seed)
    fpn = ndimage.gaussian_filter(rng.normal(0, 6, (H, W)), 1.0)
    t = np.arange(N) / FPS
    if loops:
        ph = 2 * np.pi * t / 2.5 + 0.6 * np.sin(2 * np.pi * t / 3.7)       # loops that wander, as real ones do
        rad = 30 + 12 * np.sin(2 * np.pi * t / 4.3)
        x, y = 90 + 12 * t + rad * np.sin(ph), 150 + 25 * np.sin(2 * np.pi * t / 6.1) - rad * np.cos(ph)
    else:
        x, y = 60 + 20 * t, 110 + 0 * t
    vx, vy = np.gradient(x, t), np.gradient(y, t)
    theta = np.arctan2(vx, -vy)
    yy, xx = np.mgrid[:H, :W]
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "ffv1", "-pix_fmt", "gray", str(path)], stdin=subprocess.PIPE)
    for k in range(N):
        g = 130 + fpn + rng.normal(0, 4, (H, W))
        g -= 45 * mod(theta[k]) * np.exp(-0.5 * ((xx - x[k]) ** 2 + (yy - y[k]) ** 2) / 2.5 ** 2)
        p.stdin.write(np.clip(g, 0, 255).astype(np.uint8).tobytes())
    p.stdin.close()
    p.wait()
    return {k + 1: (float(x[k]), float(y[k])) for k in range(N) if k % 11 != 5}       # a mark missing now and then


def run(tmp, name, **kw):
    track = make(Path(tmp) / f"{name}.mkv", **kw)
    clip = Clip(Path(tmp) / f"{name}.mkv", Path(tmp) / f"{name}_frames")
    aspect.N_SLIDE = 300
    return aspect.measure(clip, track, dark=True, still=True, depression=45.0)


def test_a_round_body_is_not_called():
    print("\naspect: a round dark blob looping, its flux constant")
    with tempfile.TemporaryDirectory() as d:
        found = run(d, "round")
        f, b = found.fields, found.fields["brightness"]
        check(f["turns"] > 2.5, "it turned", f"{f['turns']} turns")
        check(f["heading_place_r2"] < aspect.MAX_TANGLE, "heading and place can be told apart", f"R^2 {f['heading_place_r2']}")
        check(not found.no_power, "and nothing is said to be missing", str(found.no_power))
        check(b["p_heading"] > 0.01, "no heading effect is called", f"1st {100 * b['amp1']:.1f} %, 2nd {100 * b['amp2']:.1f} %, p {b['p_heading']}")
        check(f["controls"]["2theta"]["p_heading"] < 0.05 and f["controls"]["theta"]["p_heading"] < 0.05,
              "the planted modulations are recovered beside it")
        check("bank_bound" in f and f["bank_bound"]["bank_max_deg"] < 15, "a bank bound is given", str(f.get("bank_bound")))


def test_a_body_whose_brightness_follows_its_heading_is_called():
    print("\naspect: the same blob, its flux following its heading by 25 %")
    with tempfile.TemporaryDirectory() as d:
        f = run(d, "winged", mod=lambda th: 1 + 0.25 * np.cos(th - 1.0)).fields
        b = f["brightness"]
        check(b["p_heading"] < 0.01, "the heading effect is called", f"1st {100 * b['amp1']:.1f} %, p {b['p_heading']}")
        check(abs(b["amp1"] - 0.25) < 0.08, "at about its size", f"{100 * b['amp1']:.1f} % for 25 %")


def test_a_track_that_never_turns_has_no_power():
    print("\naspect: a straight track")
    with tempfile.TemporaryDirectory() as d:
        found = run(d, "straight", loops=False)
        check(any("full turn" in w for _, w in found.no_power), "said to have no power", str(found.no_power[:1]))




def test_a_clean_circle_has_no_power():
    print("\naspect: a clean circle (the heading is a function of the place)")
    import types
    with tempfile.TemporaryDirectory() as d:
        rng = np.random.default_rng(3)
        path = Path(d) / "circle.mkv"
        t = np.arange(N) / FPS
        x, y = 200 + 40 * np.sin(2 * np.pi * t / 2.5), 150 - 40 * np.cos(2 * np.pi * t / 2.5)
        yy, xx = np.mgrid[:H, :W]
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(FPS),
                              "-i", "-", "-c:v", "ffv1", "-pix_fmt", "gray", str(path)], stdin=subprocess.PIPE)
        for k in range(N):
            g = 130 + rng.normal(0, 4, (H, W)) - 45 * np.exp(-0.5 * ((xx - x[k]) ** 2 + (yy - y[k]) ** 2) / 2.5 ** 2)
            p.stdin.write(np.clip(g, 0, 255).astype(np.uint8).tobytes())
        p.stdin.close()
        p.wait()
        aspect.N_SLIDE = 100
        found = aspect.measure(Clip(path, Path(d) / "f"), {k + 1: (float(x[k]), float(y[k])) for k in range(N)}, dark=True)
        check(any("goes with the place" in w for _, w in found.no_power), "said to have no power",
              f"R^2 {found.fields['heading_place_r2']}")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{'ALL PASS' if not FAIL else f'{len(FAIL)} FAILED: ' + ', '.join(FAIL)}")
    sys.exit(1 if FAIL else 0)
