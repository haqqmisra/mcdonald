"""How overfit is a gate's setting? The probability of backtest overfitting (PBO) by combinatorially symmetric
cross-validation (Bailey, Borwein, Lopez de Prado & Zhu 2017; the economics survey's E9, its section 4.1).

A gate's setting is chosen as the best of several candidates on labelled data. CSCV asks how much of that choice is
noise: the clips are split into S blocks; for every way of taking half the blocks, the best candidate on that half is
found and ranked among all the candidates on the other half. PBO is the share of halves where the best in sample ranks
at or under the median out of sample: near 0 a choice that carries over, near 0.5 or above one that is mostly noise. It
needs no held-out set, so it can be run again after every change; the held-out sets stay for the final check.

    python3 tools/sweep/pbo.py floor TRACKS.csv [--rule stage] [--w 11]     # BIRD_FLOOR's candidates, 0-20 % by 0.5 %
    python3 tools/sweep/pbo.py floor TRACKS.csv --alpha 0.01               # ... chosen in sample as floor.py sets it
    python3 tools/sweep/pbo.py configs LONG.csv [--w 11]                   # any gate's candidates (POINT_DISC's discs)

TRACKS.csv is `floor.py`'s per-track table. LONG.csv has a row per candidate and track: `config`, `clip`, `cls` (BIRD
or not) and `named` (1 where that candidate names the track a bird), the candidates in the order they are listed.
A candidate's performance on a set of clips is U = TPR - w FPR over their tracks: the birds named less w times the
non-birds named. w = 11 prices a false bird and a missed one alike where one object in twelve is a bird (the biology
survey's B24 anchor: w = (1 - pi) / pi times C(false) / C(miss)). The blocks hold whole clips, dealt round within each
class after a seeded shuffle, so that every block holds every class (a clip's objects are not independent: split by
clip, never by track). Ties in sample go to the middle of the tied candidates; ranks out of sample are averaged over
ties. Python's standard library only."""
import argparse
import csv
import itertools
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from floor import RULES, bird, named, read   # noqa: E402

BLOCKS = 16
W = 11.0
SEED = "mcdonald-pbo-2026-11-07"
FLOORS = [round(0.005 * i, 3) for i in range(41)]      # 0-20 % by 0.5 %


def blocks_of(clips, s=BLOCKS, seed=SEED):
    """{clip: block}: the clips of each class shuffled (seeded) and dealt round the s blocks in turn."""
    rng = random.Random(seed)
    out, k = {}, 0
    for cls in sorted({c for c in clips.values()}):
        cs = sorted(c for c, v in clips.items() if v == cls)
        rng.shuffle(cs)
        for c in cs:
            out[c] = k % s
            k += 1
    return out


def counts(table, s):
    """table: [(config index, clip block, positive?, named?)] -> per block and config: [TP, P, FP, N]."""
    n = 1 + max(t[0] for t in table)
    c = [[[0, 0, 0, 0] for _ in range(n)] for _ in range(s)]
    for j, b, pos, hit in table:
        cell = c[b][j]
        if pos:
            cell[0] += hit
            cell[1] += 1
        else:
            cell[2] += hit
            cell[3] += 1
    return c


def sums(c, blocks):
    """Per config, [TP, P, FP, N] summed over the blocks."""
    return [[sum(c[b][j][i] for b in blocks) for i in range(4)] for j in range(len(c[0]))]


def performance(sm, w):
    return [(tp / p if p else 0.0) - w * (fp / n if n else 0.0) for tp, p, fp, n in sm]


def ranks(xs):
    """Average ranks, 1 the lowest."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def best_of(sm, w):
    """The candidate that does best on these sums: the largest U, ties to the middle of the tied."""
    ins = performance(sm, w)
    tied = [j for j in range(len(ins)) if ins[j] == max(ins)]
    return tied[(len(tied) - 1) // 2]


def at_rate(alpha):
    """The candidate the floor's own rule takes (`floor.py set`): the first, in the order listed (the floors rising),
    that names no more than alpha of the non-birds."""
    return lambda sm, w: next((j for j, (tp, p, fp, n) in enumerate(sm) if fp <= alpha * n), len(sm) - 1)


def cscv(c, s, w=W, choose=best_of, ref=0):
    """(PBO, the logits, the index chosen in sample on each half, its U out of sample less candidate `ref`'s) over every
    half of the s blocks. `choose(sums, w)` picks in sample (the best U by default); out of sample the pick is ranked by U
    among all the candidates. PBO is the share of halves whose pick ranks at or under the median out of sample; the
    last list says whether the pick beat the reference (for a floor, none at all) out of sample: a choice can be noise
    among good candidates and still beat having none."""
    n = len(c[0])
    total = sums(c, range(s))
    logits, chosen, gain = [], [], []
    for half in itertools.combinations(range(s), s // 2):
        sm = sums(c, half)
        oos = performance([[t - h for t, h in zip(tt, hh)] for tt, hh in zip(total, sm)], w)
        pick = choose(sm, w)
        omega = ranks(oos)[pick] / (n + 1)
        logits.append(math.log(omega / (1 - omega)))
        chosen.append(pick)
        gain.append(oos[pick] - oos[ref])
    pbo = sum(x <= 0 for x in logits) / len(logits)
    return pbo, logits, chosen, gain


def table_floor(rows, rule, floors=FLOORS, s=BLOCKS, seed=SEED):
    clips = {r["clip"]: ("BIRD" if bird(r) else "OTHER") for r in rows}
    blk = blocks_of(clips, s, seed)
    return [(j, blk[r["clip"]], bird(r), named(r, rule, f)) for j, f in enumerate(floors) for r in rows
            if r.get(f"{rule}_call")]


def table_long(rows, s=BLOCKS, seed=SEED):
    configs = list(dict.fromkeys(r["config"] for r in rows))
    clips = {r["clip"]: ("BIRD" if bird(r) else "OTHER") for r in rows}
    blk = blocks_of(clips, s, seed)
    return configs, [(configs.index(r["config"]), blk[r["clip"]], bird(r), int(r["named"]) == 1) for r in rows]


def said(name, configs, pbo, logits, chosen, gain):
    picks = sorted(chosen)
    q = lambda p: configs[picks[min(len(picks) - 1, int(p * len(picks)))]]
    med = sorted(logits)[len(logits) // 2]
    g = sorted(gain)
    print(f"{name}: PBO {pbo:.3f} over {len(logits)} halves (median logit {med:+.2f}); chosen in sample: "
          f"median {q(0.5)}, 5-95 % {q(0.05)}-{q(0.95)}; out of sample it beats {configs[0]} on "
          f"{100 * sum(x > 0 for x in g) / len(g):.0f} % of halves (U {g[len(g) // 2]:+.3f}, 5-95 % {g[len(g) // 20]:+.3f} to "
          f"{g[-1 - len(g) // 20]:+.3f})")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("floor")
    p.add_argument("tracks")
    p.add_argument("--rule", choices=RULES, action="append")
    p.add_argument("--w", type=float, action="append")
    p.add_argument("--blocks", type=int, default=BLOCKS)
    p.add_argument("--alpha", type=float, help="choose in sample by the floor's own rule at this rate, not by the best U")
    q = sub.add_parser("configs")
    q.add_argument("long")
    q.add_argument("--w", type=float, action="append")
    q.add_argument("--blocks", type=int, default=BLOCKS)
    a = ap.parse_args(argv)
    for w in a.w or [W]:
        if a.cmd == "floor":
            rows = read(a.tracks)
            for rule in a.rule or RULES:
                c = counts(table_floor(rows, rule, s=a.blocks), a.blocks)
                how = at_rate(a.alpha) if a.alpha else best_of
                said(f"BIRD_FLOOR, {rule} rule, w {w:g}" + (f", chosen at {100 * a.alpha:g} %" if a.alpha else ""),
                     [f"{100 * f:.1f} %" for f in FLOORS], *cscv(c, a.blocks, w, how))
        else:
            configs, t = table_long(read(a.long), a.blocks)
            said(f"{Path(a.long).stem}, w {w:g}", configs, *cscv(counts(t, a.blocks), a.blocks, w))
    return 0


if __name__ == "__main__":
    sys.exit(main())
