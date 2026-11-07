"""The bird floor set from a null, and held to sets it was not set on (ROADMAP.md 0.5.0; the ideas bank's B24, E19).

`report.BIRD_FLOOR` is the share of an object's brightness a beat must reach before the conclusion names a bird. It was
first chosen by eye on 2026-10-19 (the Svanstrom labelled infrared set: the calls on birds beat at a median 15-18 %, the
false ones at 1.8-2.3 %, and 8 % left 2 of 307 non-bird tracks called). This tool sets it by a rule instead, from the
non-bird objects of a labelled set, at a stated false-alarm rate; tests a frozen floor once on a set it was not set on;
and holds it against a challenger, the simplest rule that could do its job (SR 11-7's benchmarking, E19).

    python3 tools/sweep/floor.py set TRACKS.csv [--alpha 0.01] [--boot 2000]   # the floor from the null, and its rates
    python3 tools/sweep/floor.py test TRACKS.csv --floor 0.08                  # a frozen floor on a set it has not met
    python3 tools/sweep/floor.py challenger TRACKS.csv --floor 0.08            # the floor against the amplitude alone
    python3 tools/sweep/floor.py strata TRACKS.csv --floor 0.08                # its miss and false-alarm rates by stratum

TRACKS.csv has one row per labelled track: `clip`, `object`, `cls` (BIRD for a bird, anything else for the null), and for
each beat rule (stage, paper) `{rule}_call` (bird: the object's own beat at a wingbeat's rate that comes back, before any
floor; once, other, none, refused or missing otherwise), `{rule}_amplitude` (the beat's share of the brightness),
`{rule}_hz` and `{rule}_shaken_px` (the camera's shake at the beat, where it moves the picture; empty otherwise). The
controls harness's per-track table has these columns, and so does the session's own run (ROADMAP.md 0.5.0).

A track is named a bird under a floor where its call is bird, its amplitude reaches the floor, and the camera's shake is
not at its beat: the rule `report.Case.conclusion` keeps for one object. Every rate counts tracks, refused ones in the
denominator (an object the report does not name a bird); every interval resamples clips, since a clip's objects are not
independent (E10). Python's standard library only."""
import argparse
import csv
import math
import random
import sys
from statistics import NormalDist

RULES = ("stage", "paper")
WINGBEAT_HZ = (2.0, 25.0)   # report.WINGBEAT_HZ
ALPHA = 0.01                # the stated rate: the level of every null the package states (CONTINUUM_P, ONCE_P, FAP_MAX)
STEP = 0.001                # the floor's grid
ROUND = 0.005               # the floor committed: the larger rule's, rounded up to this
BOOT = 2000
SEED = "mcdonald-bird-floor-2026-11-07"


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(ln for ln in f if not ln.startswith("#")))


def number(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def bird(row):
    return row["cls"].strip().upper() == "BIRD"


def candidate(row, rule):
    """The amplitude of a beat that would name a bird at any floor (call bird, not shaken), inf where the case gives
    none (a case from before the floor names a bird whatever it is), or None where no floor could name one."""
    if row.get(f"{rule}_call") != "bird" or number(row.get(f"{rule}_shaken_px")) is not None:
        return None
    a = number(row.get(f"{rule}_amplitude"))
    return math.inf if a is None else a


def named(row, rule, floor):
    a = candidate(row, rule)
    return a is not None and a >= floor


def challenger_amplitude(row, rule):
    """The amplitude alone: the strongest peak the stage reports, if it lies at a wingbeat's rate, with none of the beat's
    tests (whether it is the object's own, whether it comes back, the shake); None for a track it did not measure."""
    hz, a = number(row.get(f"{rule}_hz")), number(row.get(f"{rule}_amplitude"))
    if row.get(f"{rule}_call") in ("refused", "missing", "error", None, "") or hz is None or a is None:
        return None
    return a if WINGBEAT_HZ[0] <= hz <= WINGBEAT_HZ[1] else None


def measured(rows, rule):
    """Whether the table holds this rule's calls at all (a set may be measured under one rule only)."""
    return any(r.get(f"{rule}_call") not in (None, "", "missing") for r in rows)


def by_clip(rows):
    out = {}
    for r in rows:
        out.setdefault(r["clip"], []).append(r)
    return out


def resample(groups, rng):
    """One bootstrap draw of clips, with replacement: the tracks of the clips drawn, each clip's together."""
    keys = list(groups)
    return [r for _ in keys for r in groups[rng.choice(keys)]]


def smallest_floor(scores, n, alpha=ALPHA, step=STEP):
    """The smallest floor on the grid at which no more than alpha of n tracks score at or over it."""
    k = math.floor(alpha * n + 1e-9)
    s = sorted((x for x in scores if x is not None), reverse=True)
    if len(s) <= k:
        return 0.0
    if math.isinf(s[k]):
        return math.inf
    return round((math.floor(s[k] / step + 1e-9) + 1) * step, 6)


def quantile(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    i = q * (len(xs) - 1)
    lo, hi = math.floor(i), math.ceil(i)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)


def boot_floor(null, score, alpha=ALPHA, boot=BOOT, seed=SEED):
    """The floor of each by-clip resample of the null: the smallest at which no more than alpha of its tracks score
    over it."""
    rng, groups = random.Random(seed), by_clip(null)
    out = []
    for _ in range(boot):
        rs = resample(groups, rng)
        out.append(smallest_floor([score(r) for r in rs], len(rs), alpha))
    return out


def binom_cdf(k, n, p):
    if k < 0:
        return 0.0
    return min(1.0, sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, min(k, n) + 1)))


def exact(k, n, conf=0.95):
    """The Clopper-Pearson interval of k in n, by bisection on the binomial."""
    a = (1 - conf) / 2

    def solve(f, lo=0.0, hi=1.0):
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return (lo + hi) / 2
    low = 0.0 if k == 0 else solve(lambda p: 1 - binom_cdf(k - 1, n, p) < a)
    high = 1.0 if k == n else solve(lambda p: binom_cdf(k, n, p) > a)
    return low, high


def upper(k, n, conf=0.95):
    """The exact one-sided upper bound of k in n: the rate at which k or fewer would be seen 1 - conf of the time. With
    none in 286 it is 1.04 %, so no set of about 300 tracks can show a rate under 1 % (the diagnostic-accuracy survey):
    a rate is stated as its count with this bound, never as "under"."""
    if k >= n:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if binom_cdf(k, n, mid) > 1 - conf else (lo, mid)
    return (lo + hi) / 2


def boot_rate(rows, hit, boot=BOOT, seed=SEED):
    """The 95 % interval of the share of rows `hit` names, resampling clips."""
    rng, groups = random.Random(seed + ":rate"), by_clip(rows)
    if not rows:
        return None, None
    vals = []
    for _ in range(boot):
        rs = resample(groups, rng)
        vals.append(sum(map(hit, rs)) / len(rs))
    return quantile(vals, 0.025), quantile(vals, 0.975)


def binom_upper(n, p, level=0.95):
    """The largest count of n at p that a one-sided test at 1 - level does not reject: the level-th quantile."""
    k = 0
    while binom_cdf(k, n, p) < level:
        k += 1
    return k


def operating_point(hit, fa, base=1 / 12):
    """The cost a rule implies (the biology survey's B24; Wiley 2006): with equal-variance normal evidence, the likelihood
    ratio at its criterion, beta = exp(d' c), equals (1 - pi) / pi times C(false alarm) / C(miss) at the best criterion.
    Returns (d', beta, the C(false bird) / C(missed bird) it implies at base rate pi)."""
    z = NormalDist().inv_cdf
    hit, fa = min(max(hit, 1e-4), 1 - 1e-4), min(max(fa, 1e-4), 1 - 1e-4)
    d = z(hit) - z(fa)
    c = -(z(hit) + z(fa)) / 2
    beta = math.exp(d * c)
    return d, beta, beta * base / (1 - base)


def pct(x):
    return "--" if x is None else f"{100 * x:.1f} %"


def rates(rows, floor, rule, boot=BOOT, seed=SEED, say=print):
    """Named-bird rates at a floor, for the null and the birds, with by-clip and exact intervals."""
    out = {}
    for side, keep in (("null", lambda r: not bird(r)), ("birds", bird)):
        rs = [r for r in rows if keep(r)]
        k = sum(named(r, rule, floor) for r in rs)
        lo, hi = boot_rate(rs, lambda r: named(r, rule, floor), boot, seed)
        ex = exact(k, len(rs)) if rs else (None, None)
        up = upper(k, len(rs)) if rs else None
        out[side] = dict(k=k, n=len(rs), rate=k / len(rs) if rs else None, boot=(lo, hi), exact=ex, upper=up)
        say(f"  {rule:5s} {side:5s}: {k} of {len(rs)} named a bird ({pct(out[side]['rate'])}; by clip {pct(lo)}-{pct(hi)}, "
            f"exact {pct(ex[0])}-{pct(ex[1])}, one-sided 95 % bound {pct(up)})")
    return out


def set_floor(rows, alpha=ALPHA, boot=BOOT, seed=SEED, say=print):
    """The floor from the null: for each rule, the median over by-clip resamples of the non-bird clips of the smallest
    floor at which no more than alpha of their tracks are named a bird; the larger rule's, rounded up to ROUND."""
    null = [r for r in rows if not bird(r)]
    per = {}
    for rule in [r for r in RULES if measured(rows, r)]:
        fs = boot_floor(null, lambda r: candidate(r, rule), alpha, boot, seed + ":" + rule)
        per[rule] = dict(median=quantile(fs, 0.5), p5=quantile(fs, 0.05), p95=quantile(fs, 0.95),
                         plain=smallest_floor([candidate(r, rule) for r in null], len(null), alpha))
        say(f"{rule}: the floor at which no more than {pct(alpha)} of {len(null)} non-bird tracks are named a bird: "
            f"{pct(per[rule]['plain'])} on the set as it is; over {boot} resamples of its clips median {pct(per[rule]['median'])}, "
            f"5-95 % {pct(per[rule]['p5'])}-{pct(per[rule]['p95'])}")
    top = max(p["median"] for p in per.values())
    floor = round(math.ceil(top / ROUND - 1e-9) * ROUND, 6)
    say(f"BIRD_FLOOR = {floor:.3f} (the larger rule's {pct(top)}, rounded up to {pct(ROUND)})")
    return floor, per


def cmd_set(a):
    rows = read(a.tracks)
    floor, _ = set_floor(rows, a.alpha, a.boot)
    for rule in [r for r in RULES if measured(rows, r)]:
        r = rates(rows, floor, rule, a.boot)
        for base in (1 / 12, 1 / 3):
            d, beta, cost = operating_point(r["birds"]["rate"], r["null"]["rate"], base)
            print(f"  {rule:5s} at one object in {round(1 / base)} a bird: d' {d:.2f}, likelihood ratio at the criterion {beta:.1f}, "
                  f"a false bird priced at {cost:.2f} of a missed one")
    return 0


def cmd_test(a):
    rows = read(a.tracks)
    ok = True
    for rule in RULES:
        if not measured(rows, rule):
            continue
        r = rates(rows, a.floor, rule, a.boot)
        top = binom_upper(r["null"]["n"], a.alpha)
        passed = r["null"]["k"] <= top
        ok &= passed
        n = r["null"]["n"]
        print(f"  {rule:5s}: {r['null']['k']} of {n} named against at most {top} for a rate of {pct(a.alpha)} "
              f"(one-sided at 5 %): {'PASS -- not shown above the stated rate' if passed else 'FAIL -- shown above the stated rate'}; "
              f"a rate of {pct(2 * a.alpha)} would pass {pct(binom_cdf(top, n, 2 * a.alpha))} of the time")
        r0 = rates(rows, 0.0, rule, a.boot, say=lambda *x: None)
        print(f"  {rule:5s} with no floor: null {r0['null']['k']} of {r0['null']['n']}, birds {r0['birds']['k']} of {r0['birds']['n']}")
    return 0 if ok else 1


def margin(rows, rule, gate, rival, boot=BOOT, seed=SEED):
    """The gate's hit rate on the birds minus the rival's, each at its own threshold, with a by-clip interval."""
    birds = [r for r in rows if bird(r)]
    diff = lambda rs: (sum(map(gate, rs)) - sum(map(rival, rs))) / len(rs) if rs else 0.0
    rng, groups = random.Random(seed + ":margin"), by_clip(birds)
    vals = [diff(resample(groups, rng)) for _ in range(boot)]
    return diff(birds), quantile(vals, 0.025), quantile(vals, 0.975)


def cmd_challenger(a):
    rows = read(a.tracks)
    null = [r for r in rows if not bird(r)]
    for rule in [r for r in RULES if measured(rows, r)]:
        fs = boot_floor(null, lambda r: challenger_amplitude(r, rule), a.alpha, a.boot, SEED + ":challenger:" + rule)
        ca = quantile(fs, 0.5)
        gate = lambda r: named(r, rule, a.floor)
        alone = lambda r: (challenger_amplitude(r, rule) or -1) >= ca
        tests = lambda r: named(r, rule, 0.0)
        for name, fn in (("the gate (beat tests and the floor)", gate), (f"the amplitude alone at {pct(ca)}", alone),
                         ("the beat's tests alone, no floor", tests)):
            k0, k1 = sum(map(fn, null)), sum(fn(r) for r in rows if bird(r))
            nb = sum(bird(r) for r in rows)
            print(f"  {rule:5s} {name:40s} null {k0} of {len(null)} ({pct(k0 / len(null))}), birds {k1} of {nb} ({pct(k1 / nb)})")
        m, lo, hi = margin(rows, rule, gate, alone, a.boot)
        print(f"  {rule:5s} the gate's margin over the amplitude alone, in birds named: {100 * m:+.1f} points "
              f"(by clip {100 * lo:+.1f} to {100 * hi:+.1f})")
    return 0


# what a clip offers, binned (the diagnostic-accuracy survey's spectrum bias: easy controls overstate power on hard
# footage): a column, and its bins' upper edges; a column of words is binned by its own values. Only what the outcome
# cannot set: not flicker's own power (`needs`), which is highest on the birds the stage names
STRATA = (("labelled", "track length, frames", (150, 300, math.inf)),
          ("w_med", "object size, label width px", (5, 10, 20, math.inf)),
          ("distance", "the set's distance bin", None),
          ("fps", "frame rate", None))


def stratum(row, col, edges, rule):
    v = row.get(col.format(rule=rule), "")
    if edges is None:
        return v or "(not given)"
    x = number(v)
    if x is None:
        return "(not measured)"
    lo = 0
    for e in edges:
        if x < e:
            return f"{lo:g}-{e:g}" if math.isfinite(e) else f"{lo:g} or more"
        lo = e
    return "?"


def cmd_strata(a):
    """The frozen floor's miss rate on the birds and false-alarm rate on the rest, by stratum of what a clip offers,
    beside the pooled rate, and how many of each class it answered at all: a description, never an input to the floor."""
    rows = read(a.tracks)
    for rule in RULES:
        if not measured(rows, rule):
            continue
        print(f"== {rule} rule, floor {pct(a.floor)}: miss (birds not named) and false alarm (non-birds named)")
        def line(label, rs):
            b = [r for r in rs if bird(r)]
            n = [r for r in rs if not bird(r)]
            kb = sum(not named(r, rule, a.floor) for r in b)
            kn = sum(named(r, rule, a.floor) for r in n)
            eb, en = (exact(kb, len(b)) if b else (None, None)), (exact(kn, len(n)) if n else (None, None))
            print(f"  {label:34s} miss {kb:3d}/{len(b):<3d} {pct(kb / len(b) if b else None):>7s} ({pct(eb[0])}-{pct(eb[1])})   "
                  f"false alarm {kn:3d}/{len(n):<3d} {pct(kn / len(n) if n else None):>7s} ({pct(en[0])}-{pct(en[1])})")
        line("pooled", rows)
        print("  coverage by class (NO POWER is not shown to carry the class, but some classes are refused far more often):")
        for cls in sorted({r["cls"] for r in rows}):
            rs = [r for r in rows if r["cls"] == cls]
            k = sum(r.get(f"{rule}_call") == "refused" for r in rs)
            print(f"    {cls:30s} answered {len(rs) - k} of {len(rs)}, refused {k} ({pct(k / len(rs))})")
        for col, what, edges in STRATA:
            groups = {}
            for r in rows:
                groups.setdefault(stratum(r, col, edges, rule), []).append(r)
            if len(groups) == 1 and next(iter(groups)) in ("(not given)", "(not measured)"):
                continue
            print(f"  by {what}:")
            for g in sorted(groups, key=lambda g: (number(g.split("-")[0].split(" ")[0]) is None, number(g.split("-")[0].split(" ")[0]) or 0, g)):
                line("    " + g, groups[g])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("set", cmd_set), ("test", cmd_test), ("challenger", cmd_challenger), ("strata", cmd_strata)):
        p = sub.add_parser(name)
        p.add_argument("tracks")
        p.add_argument("--alpha", type=float, default=ALPHA)
        p.add_argument("--boot", type=int, default=BOOT)
        if name != "set":
            p.add_argument("--floor", type=float, required=True)
        p.set_defaults(fn=fn)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
