"""The beat pass's result: one row per object measured, the candidates, and the strict list.
ROADMAP.md 0.3, objective 9 (`summary.py` and `strict.py` of the whole-video pass, 2026-10-12/14).

    python3 tools/sweep/summary.py [--held-out]      # in the pass's working folder: beat/*/*_flicker.json

summary.tsv has every object the flicker stage measured. A candidate is one the stage calls a beat of its own and whose
whole track stands over its drift or whose 2-s windows pass twice or more -- the sweep's watch list. strict.tsv keeps
those whose passing windows include two that do not overlap within 0.5 Hz of each other (a beat that comes back, not
one stretch), or that the stage calls a beat with the whole track over its drift at 5 % or more: the list the review
looks at (`review.sbatch`, the bird paper's rule). The held-out third (`holdout.tsv`) is left out of both and
counted, unless --held-out says the gates are frozen and it is time to look."""
import argparse
import csv
import glob
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEAR = 0.5         # Hz: passing windows this close are one beat come back
STRONG = 0.05      # a whole track over its drift at this amplitude or more is a candidate by itself


def held():
    sys.path.insert(0, str(HERE))
    from holdout import held_out
    return held_out()


def apart(ws):
    """(how many passing windows that do not overlap lie within NEAR of each other, at what frequency) -- the best."""
    best = (0, None)
    for w0 in ws:
        grp = sorted([w for w in ws if abs(w["hz"] - w0["hz"]) <= NEAR], key=lambda w: w["first"])
        n, last = 0, -1
        for w in grp:
            if w["first"] > last:
                n, last = n + 1, w["last"]
        if n > best[0]:
            best = (n, w0["hz"])
    return best


def review(pid, obj):
    """What the review (`review.sbatch`: the bird paper's rule) said of an object, where it has looked: {beats, finding}."""
    try:
        r = json.load(open(f"review/{pid}_{obj}.json", encoding="utf-8"))["results"]
        return dict(beats=r.get("beats"), finding=r.get("finding") or "")
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def rows(skip=()):
    out, left = [], 0
    for f in sorted(glob.glob("beat/*/*_flicker.json")):
        pid, obj = f.split(os.sep)[-2], os.path.basename(f)[:-len("_flicker.json")]
        if pid in skip:
            left += 1
            continue
        try:
            r = json.load(open(f, encoding="utf-8"))["results"]
        except (ValueError, KeyError, TypeError):
            out.append(dict(id=pid, obj=obj, status="error"))
            continue
        c = (r.get("curves") or {}).get("object") or {}
        b = (r.get("beat") or {}).get("object") or {}
        whole = c.get("over_drift") is not None and c.get("drift_needed") is not None and c["over_drift"] >= c["drift_needed"]
        wp = b.get("windows_passing") or 0
        n, hz = apart([w for w in (r.get("windows") or {}).get("object", []) if w.get("passes")])
        rv = review(pid, obj)
        out.append(dict(id=pid, obj=obj, status="ok", first=r.get("first"), last=r.get("last"), frames=r.get("frames"),
                        beats=r.get("beats"), whole_hz=round(c.get("hz") or 0, 2), whole_err=round(c.get("hz_err") or 0, 3),
                        whole_amp=round(100 * (c.get("amplitude") or 0), 1), over_drift=round(c.get("over_drift") or 0, 1),
                        drift_needed=round(c.get("drift_needed") or 0, 1), whole_pass=whole, win_hz=round(b.get("hz") or 0, 2),
                        win_pass=wp, win_n=b.get("windows", ""), indep_windows=n, indep_hz=round(hz, 2) if hz else "",
                        candidate=bool(r.get("beats")) and (whole or wp >= 2),
                        strict=n >= 2 or (bool(r.get("beats")) and whole and (c.get("amplitude") or 0) >= STRONG),
                        review_beats=rv.get("beats", ""), review_finding=(rv.get("finding") or "").replace("\t", " "),
                        finding=(r.get("finding") or "").replace("\t", " ")))
    return out, left


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--held-out", action="store_true", help="the gates are frozen: count the held-out third in")
    a = ap.parse_args(argv)
    out, left = rows(() if a.held_out else held())
    keys = ["id", "obj", "status", "first", "last", "frames", "beats", "candidate", "strict", "whole_hz", "whole_err", "whole_amp",
            "over_drift", "drift_needed", "whole_pass", "win_hz", "win_pass", "win_n", "indep_windows", "indep_hz", "review_beats",
            "review_finding", "finding"]
    with open("summary.tsv", "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, keys, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    with open("strict.tsv", "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, keys, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        w.writerows([r for r in out if r.get("strict")])
    ok = [r for r in out if r["status"] == "ok"]
    print(f"{len(ok)} objects measured in {len({r['id'] for r in ok})} videos"
          + (f" ({left} of the held-out third left out until the gates are frozen)" if left else "")
          + f"; {sum(r['candidate'] for r in ok)} candidates, {sum(r['strict'] for r in ok)} on the strict list:")
    for r in ok:
        if r["strict"]:
            print(f"  {r['id']} {r['obj']} {r['first']}-{r['last']}: whole {r['whole_hz']} ± {r['whole_err']} Hz {r['whole_amp']}% "
                  f"({r['over_drift']}/{r['drift_needed']}), {r['indep_windows']} windows apart at {r['indep_hz']} Hz, "
                  f"{r['win_pass']}/{r['win_n']} pass" + (f"; the paper's rule: {r['review_beats']}" if r.get("review_beats") != "" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
