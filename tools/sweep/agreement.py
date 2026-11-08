"""A look's agreement: the held-out third's rate against the tuning set's, as a difference with a by-video interval (B17).

    python3 tools/sweep/agreement.py SUMMARY.tsv [--column beats] [--holdout holdout.tsv]

SUMMARY.tsv is a table of objects, one a row, with the video's id (`id`) and a column that says whether the gate called
the object (`beats` by default, `True`/`False`; empty rows are left out) -- `summary.py --held-out`'s summary.tsv, or the
census's. The held-out third is `holdout.tsv`'s. What it prints, for the held-out videos, the others and their difference:

- the rate over objects, with a 95 % interval from resampling videos (a video's objects are not independent: one video
  held 29 % of the census's beats, the biology survey's X3), and the effective number of objects the design effect leaves;
- the difference held out minus tuning, in points, with its by-video interval: two rates that agree to a point can still
  hide a difference as large as the interval is wide, and that width is what the look could have shown;
- the same with each video left out in turn, where one video moves the held-out rate most (LLE-PR002 on 2026-10-18).

Running it IS a look when the table holds the held-out third's calls under a gate that has not met it: write the line in
`looks.tsv` first (date, commit, gate, set), and run it once."""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from holdout import held_out  # noqa: E402

BOOT = 20000
SEED = 7


def counts(rows, column="beats"):
    """{video: [objects, called]} over the rows with a value in `column`."""
    by = defaultdict(lambda: [0, 0])
    for r in rows:
        v = str(r.get(column, "")).strip()
        if v == "":
            continue
        by[r["id"]][0] += 1
        by[r["id"]][1] += v in ("True", "true", "1", "yes")
    return dict(by)


def rate(by, runs=BOOT, seed=SEED):
    """(share, lo, hi, objects, videos, effective objects) of {video: [objects, called]}, the interval by resampling videos."""
    a = np.array(list(by.values()), float)
    if not len(a) or a[:, 0].sum() == 0:
        return dict(share=None, lo=None, hi=None, objects=0, videos=len(a), effective=None)
    p = a[:, 1].sum() / a[:, 0].sum()
    s = a[np.random.default_rng(seed).integers(0, len(a), (runs, len(a)))]
    boot = s[..., 1].sum(1) / s[..., 0].sum(1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    binom = p * (1 - p) / a[:, 0].sum()
    eff = a[:, 0].sum() * binom / float(np.var(boot)) if np.var(boot) > 0 and binom > 0 else None
    return dict(share=float(p), lo=float(lo), hi=float(hi), objects=int(a[:, 0].sum()), videos=len(a),
                effective=None if eff is None else float(min(eff, a[:, 0].sum())))


def difference(held, tuning, runs=BOOT, seed=SEED):
    """The held-out rate minus the tuning rate, (median, lo, hi), each set resampled by video on its own."""
    a1, a2 = np.array(list(held.values()), float), np.array(list(tuning.values()), float)
    rng = np.random.default_rng(seed)
    s1, s2 = a1[rng.integers(0, len(a1), (runs, len(a1)))], a2[rng.integers(0, len(a2), (runs, len(a2)))]
    with np.errstate(invalid="ignore", divide="ignore"):
        d = s1[..., 1].sum(1) / s1[..., 0].sum(1) - s2[..., 1].sum(1) / s2[..., 0].sum(1)
    d = d[np.isfinite(d)]
    lo, med, hi = np.percentile(d, [2.5, 50, 97.5])
    return dict(median=float(med), lo=float(lo), hi=float(hi))


def agreement(rows, held, column="beats"):
    """{held, tuning, difference, without}: the look's agreement stated as B17 asks."""
    by = counts(rows, column)
    h = {v: c for v, c in by.items() if v in held}
    t = {v: c for v, c in by.items() if v not in held}
    out = dict(held=rate(h), tuning=rate(t), difference=difference(h, t) if h and t else None, without=None)
    if len(h) > 1:                                         # the video whose leaving out moves the held-out rate most
        moved = max(h, key=lambda v: abs(rate({k: c for k, c in h.items() if k != v}, runs=1)["share"] - out["held"]["share"]))
        out["without"] = dict(video=moved, held=rate({k: c for k, c in h.items() if k != moved}))
    return out


def pct(x):
    return "--" if x is None else f"{100 * x:.1f}"


def said(A):
    h, t, d = A["held"], A["tuning"], A["difference"]
    lines = [f"held out  {pct(h['share'])} % ({h['objects']} objects, {h['videos']} videos; by video {pct(h['lo'])}-{pct(h['hi'])})",
             f"tuning    {pct(t['share'])} % ({t['objects']} objects, {t['videos']} videos; by video {pct(t['lo'])}-{pct(t['hi'])})"]
    if d:
        lines.append(f"held out minus tuning: {100 * d['median']:+.1f} points, by video {100 * d['lo']:+.1f} to {100 * d['hi']:+.1f}: "
                     f"a difference inside that interval could not have shown")
    if A["without"]:
        w = A["without"]
        lines.append(f"held out without {w['video']}: {pct(w['held']['share'])} % (by video {pct(w['held']['lo'])}-{pct(w['held']['hi'])})")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("summary", help="a table of objects with an id column and the gate's call")
    ap.add_argument("--column", default="beats", help="the call's column (default: beats)")
    ap.add_argument("--holdout", default=str(HERE / "holdout.tsv"))
    a = ap.parse_args(argv)
    with open(a.summary, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader((l for l in f if not l.startswith("#")), delimiter="\t"))
    print("\n".join(said(agreement(rows, held_out(Path(a.holdout)), a.column))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
