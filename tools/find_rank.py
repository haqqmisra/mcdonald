"""Where is the recorded object on Find's list? -- for every clip that has a recorded track.

`mcdonald.propose` (the window's Track -> Find the object, `mcdonald look --propose`) orders a
list of what moves against the background. Whether the order is any good cannot be read off
one clip: while its score was being got right PR113's transit went 67th, 3rd, off the list,
6th, and the clips it already ranked first never moved. So after any change to propose.py,
run this, and write the table into docs/handoff-ui.md.

    python3 tools/find_rank.py                       # every case
    python3 tools/find_rank.py PR113 PR055 --link    # some; and link from the marks the row would place
    sbatch tools/find_rank.sbatch --link             # on a machine with a queue (see the script)
    sbatch tools/find_rank.sbatch --link --keep DIR  # and keep what the link needs to be run again...
    python3 tools/find_rank.py --replay DIR          # ...which, after a change to autolink, is seconds
    sbatch tools/find_rank.sbatch --link --seeds DIR --keep NEW   # a change to the detector: Find's marks, no Find
    python3 tools/find_rank.py --replay DIR --pick   # and choose the spot size again, as the window does

For each case: the place of the first row that is *on* the recorded track (more than 70 % of
the frames they share within 12 px), its strength and score, the next row's score, and how
far it sits from the recorded positions. With --link: the package's own linker, started from
the marks that row would place (`Proposal.seeds`), as "This is it" does in the window -- how
many frames it linked, how far from the recorded track, how many of those frames are off it,
the fastest step, and what it said. Find's marks have to be marks the linker can use: on PR055
they were on the disc's rim and it linked nothing, and on PR142 the first of them were on a
faint copy the object drags behind it. And the linker has to stay on what they mark: on PR055
it went on past the marks onto cloud, and a median distance from the recorded track did not
show it (the frames on cloud were mostly frames with no recorded position to compare).

--keep keeps, for each case, the marks and the detector's spots on every frame of it (about
30 MB a case); --replay links from them again with whatever autolink now is, reading no
frame: the way to try a change to the linker on every recorded track in seconds.

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
import pickle
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
    ("PR055 1007-1418", "PR055", 1007, 1418, lambda: pr055_whole(TRACKS / "pr055_track.csv")),   # Jacob's, 2026-09-22
    ("PR055 90-350", "PR055", 90, 350, lambda: columns(TRACKS / "pr055_track.csv", "frame_A", "x_A", "y_A")),
]


def on(p, truth, px=12.0):
    """(frames shared, median px apart) if the proposal is on the recorded track, else None: more than
    70 % of the frames they share within `px`, or within a third of the thing's own width if that is
    more. Until 2026-09-23 it was 12 px for everything, and PR055's enlarged copy -- a disc 74 px across,
    which Find had as its first two rows, 13 and 15 px from the recorded centre -- was "not on the list"."""
    shared = [n for n in p.frames if n in truth]
    if len(shared) < 2:
        return None
    px = max(px, p.size_px / 3.0)
    d = np.array([np.hypot(p.track[n][0] - truth[n][0], p.track[n][1] - truth[n][1]) for n in shared])
    return (len(shared), float(np.median(d))) if np.mean(d <= px) > 0.7 else None


def link_line(link, truth, n_seeds, px=12.0):
    """What the link from a proposal's marks did, held against the recorded track: how many
    frames, how far from it where they share frames, how many of those are *off* it (a link
    that jumps to something else is off on every frame after the jump, and a median does not
    see it), and the fastest step between two linked points against the median one, for a
    jump where nothing is recorded to hold it against (PR055's link went from a disc moving
    2.5 px a frame to a cloud 190 px away, across 15 frames it had not seen it on)."""
    tr = link.track
    shared = [n for n in tr if n in truth]
    d = np.array([np.hypot(tr[n][0] - truth[n][0], tr[n][1] - truth[n][1]) for n in shared])
    ns = sorted(tr)
    steps = [(np.hypot(tr[b][0] - tr[a][0], tr[b][1] - tr[a][1]) / (b - a), a, b) for a, b in zip(ns, ns[1:])]
    moving = [s for s, _, _ in steps if s > 0]                  # a repeated frame is not a speed
    fast = max(steps, default=None)
    return (f"linked from its {n_seeds} marks: {len(tr)} frames, {ns[0] if ns else '-'}–{ns[-1] if ns else '-'}"
            + (f", median {np.median(d):.1f} px from the recorded track on the {len(shared)} they share, "
               f"{int((d > px).sum())} of them more than {px:g} px off" if len(d) else "")
            + (f"; fastest step {fast[0]:.0f} px a frame, {fast[1]}→{fast[2]} (median {np.median(moving):.0f})" if moving else "")
            + f". {link.say}")


PICK = False      # --pick: with --replay, choose the spot size from the kept marks again, as the window does


class Kept:
    """What a kept case needs of a clip to link again: the frames it spans."""
    def __init__(self, n0, n1):
        self.n0, self.n1 = n0, n1


def replay(keep, only):
    """Link again from kept marks and candidates: the linker alone, in seconds, no frame read."""
    for pkl in sorted(Path(keep).glob("*.pkl")):
        k = pickle.load(open(pkl, "rb"))
        if only and not any(o in k["name"] for o in only):
            continue
        if k["size"] is None:
            print(f"{k['name']:15s} nothing to link again: {k['say']}", flush=True)
            continue
        t0 = time.time()
        pick = PICK and all((n, float(s), d) in k["cache"] for s in autolink.SIZES for d in (False, True)
                            for n in (min(k["seeds"]), max(k["seeds"])))
        last = list(autolink.link_from_marks(Kept(k["n0"], k["n1"]), k["seeds"], masks=k["masks"], procs=0,
                                             size=None if pick else k["size"], dark=None if pick else k["dark"],
                                             cache=k["cache"]))[-1]
        if pick and last.size != k["size"]:
            print(f"{'':15s} (chose {last.size} px {'dark' if last.dark else 'bright'}, where it was kept at {k['size']})")
        if pick and (last.size, last.dark) != (k["size"], k["dark"]) and not all(
                (n, last.size, last.dark) in k["cache"] for n in range(k["n0"], k["n1"] + 1)):
            print(f"{k['name']:15s} chose a spot size whose spots were not kept on every frame: run it again with --link --keep")
            continue
        print(f"{k['name']:15s} {link_line(last, k['truth'], len(k['seeds']))}   ({time.time() - t0:.1f} s)", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("only", nargs="*", help="cases whose name contains one of these (default: all)")
    ap.add_argument("--link", action="store_true", help="also link from the marks the row would place, as the window's This is it does")
    ap.add_argument("--work", default=str(Path(tempfile.gettempdir()) / "mcdonald-find-rank"), help="where the frames go, and stay")
    ap.add_argument("--keep", metavar="DIR", help="with --link: keep each case's marks and the detector's spots on every frame "
                    "in DIR, so that --replay can link again in seconds")
    ap.add_argument("--replay", metavar="DIR", help="link again from what --keep kept; nothing else is run")
    ap.add_argument("--seeds", metavar="DIR", help="with --link: take each case's marks from what --keep kept there, and do not "
                    "run Find -- for a change to the detector, which the kept spots cannot answer")
    ap.add_argument("--pick", action="store_true", help="with --replay: choose the spot size again from the marks "
                    "(kept at every size since 2026-09-23), rather than using the size kept")
    args = ap.parse_args()
    global PICK
    PICK = args.pick
    if args.replay:
        return replay(args.replay, args.only)
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
        kept = Path(args.seeds or "") / (name.replace(" ", "_") + ".pkl")
        if args.seeds and args.link and kept.exists():
            k = pickle.load(open(kept, "rb"))
            print(f"{name:15s} the marks Find placed, from {kept}", flush=True)
            link_case(args, name, clip, k["masks"], k["seeds"], truth, n0, n1, procs)
            continue
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
            link_case(args, name, clip, masks, p.seeds(), truth, n0, n1, procs)


def link_case(args, name, clip, masks, seeds, truth, n0, n1, procs):
    """The link from these marks, as the window's This is it runs it; with --keep, and what it needs kept."""
    cache = {}
    last = list(autolink.link_from_marks(clip, seeds, masks=masks, procs=procs, cache=cache))[-1]
    print(f"{'':15s}   {link_line(last, truth, len(seeds))}", flush=True)
    if args.keep:
        if last.size is not None:                    # the spots on every frame, not only as far as this link looked
            workers = autolink._Workers(clip, masks, None, procs)
            ends = (min(seeds), max(seeds))                  # and every size at the end marks, for --replay --pick
            try:
                for _ in workers.imap([(n, last.size, last.dark) for n in range(n0, n1 + 1)]
                                      + [(n, float(s), d) for s in autolink.SIZES for d in (False, True) for n in ends], cache):
                    pass
            finally:
                workers.close()
        Path(args.keep).mkdir(parents=True, exist_ok=True)
        with open(Path(args.keep) / (name.replace(" ", "_") + ".pkl"), "wb") as f:
            pickle.dump(dict(name=name, n0=n0, n1=n1, seeds=seeds, size=last.size, dark=last.dark, say=last.say,
                             masks=masks, cache=cache, truth=truth), f)


if __name__ == "__main__":
    sys.exit(main())
