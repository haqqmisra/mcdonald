"""The beat pass's first step: each video found on this computer, and cut into the windows it is proposed over.
ROADMAP.md 0.3, objective 9 (the whole-video pass of 2026-10-12/14, made repeatable).

    python3 tools/sweep/windows.py WORK [--videos tools/sweep/videos.tsv] [--ids PR098,PR149] [--window 400] [--overlap 30]

Writes WORK/clips.tsv (id, the video's path here, frames, WxH, frame rate) and WORK/windows.tsv (id, tag, n0, n1): every
video cut into windows of `window` frames, each starting `window - overlap` after the last, the last ending on the
video's last frame -- an object that crosses a cut is whole in one of them (Find needs to see it 40 frames running).
Each video is found as the package finds one, by the release's file name in its catalog (`mcdonald.catalog`; a bare id
does not name every video of the list -- PR057a, the four LLE videos), and downloaded into the storage folder the first
time (`mcdonald.storage`; MCDONALD_HOME). The 126 videos are 7.5 GB; their frames, step 2, some 200 GB."""
import argparse
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def videos(path):
    """The list's rows: [{id, release, file, pass}]."""
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader((l for l in f if not l.startswith("#")), delimiter="\t"))


def found(file):
    """The video called `file` in the package's catalog, on this computer: its path, downloaded if need be."""
    from mcdonald import catalog, storage
    rec = next((r for r in catalog.active().videos() if Path(r.get("path", "")).name == file), None)
    if rec is None:
        raise SystemExit(f"{file} is not in the {catalog.active().label} catalog")
    path = Path(rec["path"])
    if not path.exists():
        if not rec.get("url"):
            raise SystemExit(f"{file} is not on this computer and its record says nowhere to fetch it from")
        storage.download_on_terminal(rec, path)
    return path


def cut(frames, window, overlap):
    """[(n0, n1)]: windows of `window` frames, `window - overlap` apart, the last ending on the last frame."""
    step = window - overlap
    out = [(a, min(a + window - 1, frames)) for a in range(1, max(2, frames - overlap), step)]
    if out and out[-1][1] < frames:
        out.append((max(1, frames - window + 1), frames))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("work", help="the pass's working folder")
    ap.add_argument("--videos", default=str(HERE / "videos.tsv"))
    ap.add_argument("--ids", default="", help="only these ids (comma-separated)")
    ap.add_argument("--window", type=int, default=400)
    ap.add_argument("--overlap", type=int, default=30)
    a = ap.parse_args(argv)
    from mcdonald.clip import probe
    work = Path(a.work)
    work.mkdir(parents=True, exist_ok=True)
    want = {v.strip() for v in a.ids.split(",") if v.strip()}
    rows = [r for r in videos(a.videos) if not want or r["id"] in want]
    with open(work / "clips.tsv", "w", encoding="utf-8") as c, open(work / "windows.tsv", "w", encoding="utf-8") as w:
        for r in rows:
            path = found(r["file"])
            info = probe(path)
            fps = float(info["fps"])
            frames = info["nb_frames"] or int(round(info["duration"] * fps))
            c.write(f"{r['id']}\t{path}\t{frames}\t{info['width']}x{info['height']}\t{info['fps']}\n")
            for k, (n0, n1) in enumerate(cut(frames, a.window, a.overlap)):
                w.write(f"{r['id']}\tw{k:02d}\t{n0}\t{n1}\n")
            print(f"{r['id']}: {frames} frames, {len(cut(frames, a.window, a.overlap))} windows", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
