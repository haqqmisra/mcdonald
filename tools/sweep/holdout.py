"""The held-out third (ROADMAP.md 0.3, objective 3; the ideas bank's D5): a third of the beat sweep's videos, drawn on
2026-10-17 before the gate work began, and not looked at again until the gates are frozen on the controls and the rest.
Then the frozen gates run on them once, and their call rate is reported beside the others'.

    python3 tools/sweep/holdout.py                 # draw again from videos.tsv and check it against holdout.tsv
    python3 tools/sweep/holdout.py --list          # the held-out videos' ids, one a line (for a script to skip them)

The draw is a hash, not a random-number generator, so that anyone can repeat it in any language and get the same third.
Within each release the eligible videos are sorted by the SHA-256 of "<SEED>:<id>" and the first n are taken, n by
release in proportion to its eligible videos (largest remainder), N = a third of all 126.

Not eligible, by name: the videos the gate work has to use -- the goldens and the controls it is judged on, the
reference cases (their files are remade with the release), the codec slice's worklist (objective 2 re-runs it), and the
two videos the bird headline rule was proposed on. Nor a video the whole-video pass followed no objects in: there would
be nothing to run the gates on.

What it does not hold out: decisions taken before the draw used every video -- the troughs rule and the stage's rule
kept as the default over the paper's (both 2026-10-16). The held-out third tests what is decided from now on: the
z-tests of objective 2, GATE_ASTRO, GATE_SEIS and the bird headline rule."""
import argparse
import csv
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = "mcdonald-0.3-holdout-2026-10-17"
SHARE = 1 / 3

IN_USE = {   # id -> why the gate work needs it by name
    **{v: "golden for the gates" for v in ("PR135", "PR41", "PR44", "PR099")},
    **{v: "control for the gates" for v in ("PR23", "PR055", "PR071")},
    **{v: "reference case" for v in ("PR113", "PR149", "PR43", "PR144", "PR077", "PR079", "PR085", "PR088", "PR097",
                                     "PR141")},
    **{v: "the codec slice's worklist" for v in ("PR098", "PR084")},
    **{v: "the headline rule's example" for v in ("PR094", "PR052")},
}


def videos(path=HERE / "videos.tsv"):
    """The sweep's videos: [{id, release, file, pass}] in the list's order."""
    with open(path) as f:
        return list(csv.DictReader((l for l in f if not l.startswith("#")), delimiter="\t"))


def key(vid):
    return hashlib.sha256(f"{SEED}:{vid}".encode()).hexdigest()


def draw(rows):
    """{id: (role, why)} for every video: role "held out", "open" (eligible, not drawn) or "in use"."""
    out, pool = {}, {}
    for r in rows:
        if r["id"] in IN_USE:
            out[r["id"]] = ("in use", IN_USE[r["id"]])
        elif r["pass"] != "yes":
            out[r["id"]] = ("in use", "not in the whole-video pass")
        else:
            pool.setdefault(r["release"], []).append(r["id"])
    n = round(SHARE * len(rows))
    eligible = sum(len(v) for v in pool.values())
    quota = {rel: n * len(v) / eligible for rel, v in pool.items()}
    take = {rel: int(q) for rel, q in quota.items()}
    for rel in sorted(quota, key=lambda rel: (-(quota[rel] - take[rel]), rel))[:n - sum(take.values())]:
        take[rel] += 1
    for rel, ids in pool.items():
        chosen = set(sorted(ids, key=key)[:take[rel]])
        out.update({v: ("held out" if v in chosen else "open", "") for v in ids})
    return out


def write(rows, roles, path):
    with open(path, "w") as f:
        f.write(f"# The held-out third, drawn 2026-10-17 by tools/sweep/holdout.py (seed {SEED!r}). Not to be looked at\n"
                "# until the gates are frozen; then the gates run on it once. See the script's docstring.\n")
        f.write("id\trelease\tfile\trole\twhy\n")
        for r in rows:
            f.write("\t".join((r["id"], r["release"], r["file"], *roles[r["id"]])) + "\n")


def held_out(path=HERE / "holdout.tsv"):
    """The held-out videos' ids, as the committed table has them."""
    with open(path) as f:
        return {r["id"] for r in csv.DictReader((l for l in f if not l.startswith("#")), delimiter="\t")
                if r["role"] == "held out"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true", help="print the held-out videos' ids")
    ap.add_argument("--write", action="store_true", help="write holdout.tsv (done once, on the day of the draw)")
    a = ap.parse_args(argv)
    if a.list:
        print("\n".join(sorted(held_out())))
        return 0
    rows = videos()
    roles = draw(rows)
    if a.write:
        write(rows, roles, HERE / "holdout.tsv")
    drawn = {v for v, (role, _) in roles.items() if role == "held out"}
    by = {}
    for r in rows:
        by.setdefault(r["release"], [0, 0])[roles[r["id"]][0] == "held out"] += 1
    print(f"{len(drawn)} of {len(rows)} held out ({sum(role == 'in use' for role, _ in roles.values())} in use, "
          f"{sum(role == 'open' for role, _ in roles.values())} open); by release: "
          + ", ".join(f"{rel} {h}/{o + h}" for rel, (o, h) in sorted(by.items())))
    if drawn != held_out():
        print("holdout.tsv does NOT match the draw", file=sys.stderr)
        return 1
    print("holdout.tsv matches the draw")
    return 0


if __name__ == "__main__":
    sys.exit(main())
