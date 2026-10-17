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

import numpy as np

SEEN = 40          # frames a proposal must be seen on
ROUND = 0.3        # the share of them it must stand against the background all round
SHARE = 5          # frames two proposals must share to be one
APART = 15.0       # px: and their median distance on those frames under this


def proposals(pid):
    """The kept proposals of prop/<pid>/*.json, seen longest first: [{tag, rank, dark, seen, a, b, t, strength, bg}]."""
    out = []
    for f in sorted(glob.glob(f"prop/{pid}/*.json")):
        if os.path.getsize(f) == 0:
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except ValueError:
            continue
        tag = os.path.basename(f)[:-5]
        for p in (d.get("results") or {}).get("proposals", []):
            if (p["strength"] in ("strong", "fair", "weak") and p["seen_in"] >= SEEN and p["background_all_round"] >= ROUND
                    and not p["scrolling_tape"]):
                t = {int(k): v for k, v in p["track"].items()}
                out.append(dict(tag=tag, rank=p["rank"], dark=p["dark"], seen=p["seen_in"], a=min(t), b=max(t), t=t,
                                strength=p["strength"], bg=p["against_background_px_per_frame"]))
    out.sort(key=lambda p: -p["seen"])
    return out


def merged(props):
    """The proposals as objects: one seen in two windows is one, its track the union, in order of first frame."""
    objs = []
    for p in props:
        for o in objs:
            com = set(p["t"]) & set(o["t"])
            if (len(com) >= SHARE and p["dark"] == o["dark"]
                    and np.median([np.hypot(p["t"][k][0] - o["t"][k][0], p["t"][k][1] - o["t"][k][1]) for k in com]) < APART):
                o["t"].update(p["t"])
                o["src"].append((p["tag"], p["rank"]))
                o["a"], o["b"] = min(o["a"], p["a"]), max(o["b"], p["b"])
                break
        else:
            objs.append(dict(p, src=[(p["tag"], p["rank"])], t=dict(p["t"])))
    objs.sort(key=lambda o: o["a"])
    return objs


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
