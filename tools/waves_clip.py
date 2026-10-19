"""The ruler on a real clip: square sea patches of a frame window, repeats dropped, the static
pattern (the median over the window) taken out, both estimators with their nulls.

    python3 tools/waves_clip.py VIDEO --n0 1 --n1 130 --patch X0,Y0,N [--patch ...] [--lam-max L] [--truth M,Q]
    python3 tools/waves_clip.py HELD.mkv --csv STABILIZE.csv --n0 277 --n1 305 --static 235-262,318-345 ...

Frames are read as 8-bit grey straight from ffmpeg, one at a time, and only the patches kept.
"""
import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from mcdonald import waves  # noqa: E402


def probe(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate", "-of", "csv=p=0", video], capture_output=True, text=True).stdout
    w, h, fr = out.strip().split(",")
    num, den = fr.split("/")
    return int(w), int(h), int(num) / int(den)


def read_patches(video, n0, n1, patches, W, H):
    """{(x0,y0,N): [frames]} for frames n0..n1 (1-based), streamed."""
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", f"select='between(n,{n0 - 1},{n1 - 1})'",
                          "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    crops = {pt: [] for pt in patches}
    full_mean = []
    n = n0
    while n <= n1:
        b = p.stdout.read(W * H)
        if len(b) < W * H:
            break
        f = np.frombuffer(b, np.uint8).reshape(H, W)
        for (x0, y0, N) in patches:
            crops[(x0, y0, N)].append(f[y0:y0 + N, x0:x0 + N].astype(np.float32))
        full_mean.append(float(f[::4, ::4].mean()))
        n += 1
    p.stdout.close()
    p.wait()
    return {k: np.array(v) for k, v in crops.items()}, n - 1


def repeats_of(crops):
    """Frames whose patches all barely change from the one before: a padded variable-rate clip."""
    d = None
    for S in crops.values():
        dd = np.abs(np.diff(S, axis=0)).mean(axis=(1, 2))
        d = dd if d is None else d + dd
    med = np.median(d)
    rep = np.r_[False, d < 0.15 * med]
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--n0", type=int, default=1)
    ap.add_argument("--n1", type=int, required=True)
    ap.add_argument("--patch", action="append", required=True, help="X0,Y0,N")
    ap.add_argument("--csv", help="a `mcdonald stabilize` CSV: its ok and repeat_of flags are used")
    ap.add_argument("--static", help="frame ranges whose median is the static pattern, A-B,C-D (default: the window's)")
    ap.add_argument("--lam-min", type=float, default=waves.LAM_MIN)
    ap.add_argument("--lam-max", type=float)
    ap.add_argument("--truth", help="M_X,Q known from the scene")
    ap.add_argument("--fixed-q", type=float)
    ap.add_argument("--u-max", type=float, default=waves.U_MAX)
    ap.add_argument("--no-rates", action="store_true")
    ap.add_argument("--json", metavar="FILE")
    ap.add_argument("--hold", action="store_true", help="hold the sea (affine registration) before measuring")
    ap.add_argument("--margin", type=int, default=48, help="with --hold: extra border read round each patch, px")
    a = ap.parse_args()
    W, H, fps = probe(a.video)
    patches = [tuple(int(v) for v in s.split(",")) for s in a.patch]
    margin = a.margin if a.hold else 0
    reads = {}
    for (x0, y0, N) in patches:
        m = min(margin, x0, y0, W - x0 - N, H - y0 - N)
        reads[(x0, y0, N)] = (x0 - m, y0 - m, N + 2 * m, m)
    n_lo, n_hi = a.n0, a.n1
    static_ranges = []
    if a.static:
        static_ranges = [tuple(int(v) for v in r.split("-")) for r in a.static.split(",")]
        n_lo, n_hi = min([n_lo] + [r[0] for r in static_ranges]), max([n_hi] + [r[1] for r in static_ranges])
    t0 = time.time()
    crops, last = read_patches(a.video, n_lo, n_hi, [r[:3] for r in reads.values()], W, H)
    frames = np.arange(n_lo, last + 1)
    print(f"{Path(a.video).name}: {W}x{H} {fps:.3f} fps, frames {n_lo}-{last} read in {time.time() - t0:.0f} s")
    ok = np.ones(len(frames), bool)
    rep = repeats_of(crops)
    if a.csv:
        rows = {int(r["frame"]): r for r in csv.DictReader(l for l in open(a.csv) if not l.startswith("#"))}
        ok = np.array([rows.get(int(n), {}).get("ok", "1") == "1" for n in frames])
        rep = np.array([bool(rows.get(int(n), {}).get("repeat_of", "")) for n in frames])
    win = (frames >= a.n0) & (frames <= a.n1)
    print(f"window {a.n0}-{a.n1}: {int(win.sum())} frames, {int((rep & win).sum())} repeats, {int((~ok & win).sum())} not ok")
    truth = tuple(float(v) for v in a.truth.split(",")) if a.truth else None
    results = {}
    for pt in patches:
        rx, ry, rN, m = reads[pt]
        S = crops[(rx, ry, rN)]
        if static_ranges:
            sm = np.zeros(len(frames), bool)
            for lo, hi in static_ranges:
                sm |= (frames >= lo) & (frames <= hi)
            sm &= ok & ~rep
        else:
            sm = win & ok & ~rep
        static = np.median(S[sm], axis=0)
        sel = win & ok
        t = (frames[sel] - 1) / fps
        t1 = time.time()
        res = waves.measure_patch(S[sel], t, rep[sel], static=static, lam_min=a.lam_min, lam_max=a.lam_max,
                                  fixed_q=a.fixed_q, rates=not a.no_rates, u_max=a.u_max, hold=a.hold, margin=m)
        print(f"patch x{pt[0]} y{pt[1]} N{pt[2]} ({time.time() - t1:.0f} s):")
        for line in waves.said_patch(res, truth):
            print("  " + line)
        rec = {}
        for key in ("rates", "shell"):
            if key in res:
                rec[key] = {k: v for k, v in res[key].items() if k not in ("profile", "profile_free", "m_grid", "on", "pg")}
                if "profile" in res[key]:
                    rec[key]["profile"] = [float(x) for x in res[key]["profile"]]
        rec.update(n_frames=res["n_frames"], span_s=res["span_s"], n_bins=res["n_bins"], hold=res.get("hold"),
                   quadrants=res.get("quadrants"))
        results[f"{pt[0]},{pt[1]},{pt[2]}"] = rec
    if a.json:
        Path(a.json).write_text(json.dumps(dict(video=a.video, n0=a.n0, n1=a.n1, truth=truth, patches=results),
                                           indent=1, default=float))


if __name__ == "__main__":
    main()
