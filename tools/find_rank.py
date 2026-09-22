"""Where is the recorded object on Find's list? -- for every clip that has a recorded track.

`mcdonald.propose` (the window's Track -> Find the object, `mcdonald look --propose`) orders a
list of what moves against the background. Whether the order is any good cannot be read off
one clip: while its score was being got right PR113's transit went 67th, 3rd, off the list,
6th, and the clips it already ranked first never moved. So after any change to propose.py,
run this, and write the table into docs/handoff-ui.md.

    python3 tools/find_rank.py                       # every case
    python3 tools/find_rank.py PR113 PR055 --link    # some; and link from the marks the row would place
    sbatch tools/find_rank.sbatch --link             # on a machine with a queue (see the script)

For each case: the place of the first row that is *on* the recorded track (more than 70 % of
the frames they share within 12 px), its strength and score, the next row's score, and how
far it sits from the recorded positions. With --link: the package's own linker, started from
the marks that row would place (`Proposal.seeds`), as "This is it" does in the window -- how
many frames it linked, how far from the recorded track, and what it said. Find's marks have
to be marks the linker can use: on PR055 they were on the disc's rim and it linked nothing,
and on PR142 the first of them were on a faint copy the object drags behind it.

It is not a test: the recorded tracks are not in the repository (two are, in tests/golden).
MCDONALD_TRACKS is the folder the others are in, MCDONALD_CATALOG the catalog that resolves the
ids, and --work a folder for the frames (about 1.6 GB for all of it; they are kept, so a
second run extracts nothing). A case whose track or clip is not there is skipped, and said.
Process pools follow the CPUs this process may use (`progress.cpus`), so under Slurm it is
the allocation that decides.
"""
import argparse
import csv
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

from mcdonald import autolink, propose
from mcdonald import forensics as vf
from mcdonald.progress import cpus

GOLDEN = Path(__file__).resolve().parent.parent / "tests" / "golden"
TRACKS = Path(os.environ.get("MCDONALD_TRACKS", "/hugespace/local/research/uap/analysis"))


def columns(path, frame, x, y):
    """{frame: (x, y)} from a CSV with a header, its '#' lines and its unseen rows left out."""
    out = {}
    for r in csv.DictReader(ln for ln in open(path) if not ln.startswith("#")):
        if r.get("visible", "1") in ("1", "") and r.get("det", "1") in ("1", "") and r[x] not in ("", "nan"):
            out[int(float(r[frame]))] = (float(r[x]), float(r[y]))
    return out


def pr055_whole(path):
    """PR055 holds its scene twice: enlarged three times at frames 97-343, which is what the
    track was measured on (frame_A, x_A, y_A), and whole 970 frames later. Enlarged pixel
    (0, 0) is whole-frame (732, 70.5) -- pr055_cloud_comotion.md -- good to a pixel or two."""
    return {n: (732.0 + x / 3.0, 70.5 + y / 3.0) for n, (x, y) in columns(path, "frame_C", "x_A", "y_A").items()}


CASES = [  # name, clip, first frame, last frame, the recorded track
    ("PR149 1-120", "PR149", 1, 120, lambda: columns(TRACKS / "pr149_transit.csv", "frame", "x_px", "y_px")),
    ("PR144 300-500", "PR144", 300, 500, lambda: vf.read_track(GOLDEN / "pr144_track.csv")),
    ("PR142 130-290", "PR142", 130, 290, lambda: columns(TRACKS / "pr142_transit.csv", "frame", "x_px", "y_px")),
    ("PR148 140-440", "PR148", 140, 440, lambda: columns(TRACKS / "pr148_transit.csv", "frame", "x_px", "y_px")),
    ("PR113 380-440", "PR113", 380, 440, lambda: vf.read_track(GOLDEN / "pr113_transit_curated.csv")),
    ("PR113 348-471", "PR113", 348, 471, lambda: vf.read_track(GOLDEN / "pr113_transit_curated.csv")),
    ("PR055 957-1418", "PR055", 957, 1418, lambda: pr055_whole(TRACKS / "pr055_track.csv")),
    ("PR055 90-350", "PR055", 90, 350, lambda: columns(TRACKS / "pr055_track.csv", "frame_A", "x_A", "y_A")),
]


def on(p, truth, px=12.0):
    """(frames shared, median px apart) if the proposal is on the recorded track, else None."""
    shared = [n for n in p.frames if n in truth]
    if len(shared) < 2:
        return None
    d = np.array([np.hypot(p.track[n][0] - truth[n][0], p.track[n][1] - truth[n][1]) for n in shared])
    return (len(shared), float(np.median(d))) if np.mean(d <= px) > 0.7 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("only", nargs="*", help="cases whose name contains one of these (default: all)")
    ap.add_argument("--link", action="store_true", help="also link from the marks the row would place, as the window's This is it does")
    ap.add_argument("--work", default=str(Path(tempfile.gettempdir()) / "mcdonald-find-rank"), help="where the frames go, and stay")
    args = ap.parse_args()
    procs = cpus()
    print(f"{procs} process{'es' if procs != 1 else ''}; frames in {args.work}", flush=True)
    for name, cid, n0, n1, truth_of in CASES:
        if args.only and not any(o in name for o in args.only):
            continue
        try:
            path, _, _ = vf.resolve(cid)
            truth = truth_of()
        except (SystemExit, OSError) as ex:
            print(f"{name:15s} skipped: {str(ex).splitlines()[0]}", flush=True)
            continue
        clip = vf.Clip(path, Path(args.work) / cid, n0, n1)
        t0 = time.time()
        masks = vf.static_masks(clip)
        props = propose.find(clip, masks, procs=procs, keep=400)
        hit = next(((i, p, on(p, truth)) for i, p in enumerate(props, 1) if on(p, truth)), None)
        if not hit:
            print(f"{name:15s} the object is NOT on the list of {len(props)}   ({time.time() - t0:.0f} s)", flush=True)
            continue
        i, p, (k, med) = hit
        nxt = next((q.score for q in props if q is not p), 0.0)
        same = sum(1 for q in props[:12] if on(q, truth))
        print(f"{name:15s} the object is {i:3d} of {len(props):3d}  {p.strength():6s} {p.score:6.2f} (next {nxt:5.2f})  on {k} of {len(truth)} "
              f"recorded frames, {med:.1f} px; {p.describe().split(';')[0]}; all round {p.all_round:.2f}; "
              f"{same} of the first 12 rows are on it   ({time.time() - t0:.0f} s)", flush=True)
        if args.link:
            seeds = p.seeds()
            last = list(autolink.link_from_marks(clip, seeds, masks=masks, procs=procs))[-1]
            shared = [n for n in last.track if n in truth]
            d = [np.hypot(last.track[n][0] - truth[n][0], last.track[n][1] - truth[n][1]) for n in shared]
            print(f"{'':15s}   linked from its {len(seeds)} marks: {len(last.track)} frames"
                  + (f", median {np.median(d):.1f} px (worst {max(d):.1f}) from the recorded track on the {len(shared)} they share" if d else "")
                  + f". {last.say}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
