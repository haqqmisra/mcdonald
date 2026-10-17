"""Is an object's beat the video's cadence? Its brightness on anchor frames (I, P) against B frames, on held pictures
against changed ones, and by frame number modulo 2..8. ROADMAP.md 0.3, objective 9 (`cadcheck.py` and `phaselock.py`
of the beat sweep, 2026-10-11/14, which cleared PR141's and PR077's beats of the encoder before anything else did).

    python3 tools/sweep/cadcheck.py ID oNN [oNN ...]      # in the pass's working folder, after post.py

For each object, over the frames its flicker stage measured: the strongest beat of its curve against its 0.5-s running
mean; the mean of that curve on anchor frames and on B frames (a beat the encoder makes follows the anchors); on held
frames and changed ones (held: the picture changes by under 0.2 of the 80th centile of changes -- a video of 10
pictures a second shown at 30 beats at its hold cadence); and the spread of its mean by frame number modulo p for p =
2..8, as a share of the curve's standard deviation (a frame-locked artefact shows one p far above the rest). A beat of
15-30 % with differences of a few per cent here is not the encoder's or the cadence's."""
import csv
import glob
import json
import subprocess
import sys

import numpy as np


def types(video):
    """Every frame's picture type, in the order shown (ffprobe, as `mcdonald.clip.gop` reads them)."""
    r = subprocess.run(["ffprobe", "-v", "error", "-skip_loop_filter", "all", "-skip_idct", "all", "-select_streams", "v:0",
                        "-show_frames", "-show_entries", "frame=pict_type", "-of", "csv=p=0", video],
                       capture_output=True, encoding="utf-8", errors="replace")
    return np.array([ln[0] for ln in r.stdout.splitlines() if ln[:1] in ("I", "P", "B") and ln[1:2] in ("", ",")])


def main(argv=None):
    args = argv or sys.argv[1:]
    pid, objs = args[0], args[1:]
    from mcdonald import flicker, storage
    from PIL import Image
    video = next(r[1] for r in csv.reader(open("clips.tsv", encoding="utf-8"), delimiter="\t") if r[0] == pid)
    frames = storage.frames() / video.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    pt = types(video)
    print(pid, "GOP", "".join(pt[:16]))
    for o in objs:
        J = json.load(open(f"beat/{pid}/{o}_flicker.json", encoding="utf-8"))
        r = J["results"]
        rows = list(csv.DictReader(open(glob.glob(f"cases/{pid}/obj/{o}/*_flicker.csv")[0], encoding="utf-8")))
        got = {int(q["frame"]): float(q["object"]) for q in rows if q.get("object")}
        fr = np.arange(r["first"], r["last"] + 1)
        v = np.interp(fr, sorted(got), [got[k] for k in sorted(got)])
        fps = float((J.get("clip") or {}).get("fps") or 30000 / 1001)
        x = flicker.deviation(v, fps)
        th = [np.asarray(Image.open(frames / f"f{n:05d}.png").convert("L").resize((96, 54)), float) for n in range(fr[0] - 1, fr[-1] + 1)]
        d = np.array([np.abs(th[i + 1] - th[i]).mean() for i in range(len(th) - 1)])
        held = d < 0.2 * np.percentile(d, 80)
        anchor = np.isin(pt[np.clip(fr - 1, 0, len(pt) - 1)], ["I", "P"])
        p = flicker.peak(v, fps)
        s = x.std() or 1.0
        lock = []
        for q in range(2, 9):
            m = [x[fr % q == k].mean() for k in range(q) if (fr % q == k).any()]
            lock.append(f"{q}:{(max(m) - min(m)) / s:.2f}")
        print(f"  {o} {fr[0]}-{fr[-1]}: {p['hz']:.2f} Hz {p['amplitude']:.0%} | anchor {100 * x[anchor].mean():+.1f}% vs B "
              f"{100 * x[~anchor].mean():+.1f}% | held {100 * x[held].mean():+.1f}% vs changed {100 * x[~held].mean():+.1f}% "
              f"({held.sum()}/{len(d)}) | by frame mod 2-8, spread / sd: {' '.join(lock)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
