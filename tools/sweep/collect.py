"""The beat pass's objects: the long-lived proposals of one video's windows, the same thing seen in two windows merged.
ROADMAP.md 0.3, objective 9 (`collect.py` of the whole-video pass, 2026-10-12/14).

    python3 tools/sweep/collect.py ID          # in the pass's working folder: prop/ID/*.json -> objects/ID.tsv

A proposal is kept when Find rated it strong, fair or weak, saw it on 40 frames or more, found it against the
background all round on at least 0.3 of them, and did not take it for a scrolling tape. Two proposals are one object
where they share five frames or more, have one polarity, and lie under 15 px apart (the median over their shared
frames); the one seen longest leads. objects/ID.tsv: oNN, the window and rank it came from first, its first and last
frame, dark or bright, its strength, how many frames it was seen on, where it went, its speed against the background
(px a frame), and every window:rank it was seen in -- the rows `post.py` follows and measures."""
import glob
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# The rules are the package's own since 2026-11-13 (`mcdonald.batch`: `mcdonald batch` makes objects of Find's proposals
# the same way). This file reads the pass's files and writes its table.
from mcdonald.batch import APART, ROUND, SEEN, SHARE, long_lived, merged  # noqa: E402,F401


def proposals(pid):
    """The kept proposals of prop/<pid>/*.json, seen longest first: [{tag, rank, dark, seen, a, b, t, strength, bg}]."""
    windows = {}
    for f in sorted(glob.glob(f"prop/{pid}/*.json")):
        if os.path.getsize(f) == 0:
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except ValueError:
            continue
        windows[os.path.basename(f)[:-5]] = (d.get("results") or {}).get("proposals", [])
    return long_lived(windows)[0]


def main(argv=None):
    pid = (argv or sys.argv[1:])[0]
    props = proposals(pid)
    objs = merged(props)
    os.makedirs("objects", exist_ok=True)
    with open(f"objects/{pid}.tsv", "w", encoding="utf-8") as f:
        for i, o in enumerate(objs):
            t = o["t"]
            k0, k1 = min(t), max(t)
            f.write(f"o{i:02d}\t{o['src'][0][0]}\t{o['src'][0][1]}\t{o['a']}\t{o['b']}\t{'dark' if o['dark'] else 'bright'}\t"
                    f"{o['strength']}\t{o['seen']}\t{t[k0][0]:.0f},{t[k0][1]:.0f}->{t[k1][0]:.0f},{t[k1][1]:.0f}\t{o['bg']}\t"
                    f"{';'.join(f'{a}:{b}' for a, b in o['src'])}\n")
    print(pid, len(props), "proposals ->", len(objs), "objects")
    return 0


if __name__ == "__main__":
    sys.exit(main())
