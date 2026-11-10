"""How often `mcdonald tether` calls a slow wander a swing, and how often it finds a pendulum (docs/method.md, section 6;
`tether.WANDER_P` was set from this in 0.5.2, 2026-11-10).

An angle is drawn at 30 frames a second: an Ornstein-Uhlenbeck series of correlation time `tau`, with white reading noise
of `noise` times its size, seen on a share `seen` of the frames in stretches of a second or so; or a random walk; or two
wanders at once, one ten times slower. For each kind: the share of draws the cycles rule alone calls a swing (as the
stage did until 0.5.2), and the share the whole rule calls one at each threshold on the wander null's p. Then the same
for pendulums drawn over a wander: the rule's power.

    python3 tools/tether_wander_rate.py OUT.json [N a kind, default 600] [processes, default 6]

Pure arithmetic, no video; about a quarter of an hour on six processes. The table of 2026-11-10 is in the
reference-data folder, `tether_null/wander_rate.json`.
"""
import itertools
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from mcdonald import tether  # noqa: E402

FPS = 30.0
THRESHOLDS = (0.01, 0.005, 0.002, 0.001, 0.0005)


def draw(rng, span, tau, noise, seen, kind="ou", period=None, amp=1.0):
    """(times, angle in units of the wander's own size) of one drawn series."""
    n = int(span * FPS)
    t = np.arange(n) / FPS

    def ou(tt):
        a = np.exp(-1 / (FPS * tt))
        e = rng.standard_normal(n)
        z = np.empty(n)
        z[0] = e[0]
        for q in range(1, n):
            z[q] = a * z[q - 1] + np.sqrt(1 - a * a) * e[q]
        return z
    if kind == "ou":
        y = ou(tau)
    elif kind == "walk":                             # a random walk: no restoring pull at all
        y = np.cumsum(rng.standard_normal(n))
        y = (y - y.mean()) / max(y.std(), 1e-9)
    else:                                            # "two": two wanders at once, one ten times slower than the other
        y = (ou(tau) + ou(10 * tau)) / np.sqrt(2)
    y = y + noise * rng.standard_normal(n)
    if period:                                       # a pendulum on top, `amp` times the wander's size
        y = y + amp * np.sin(2 * np.pi * t / period + rng.uniform(0, 2 * np.pi))
    keep = np.ones(n, bool)
    if seen < 1:                                     # seen in stretches: on for a second on average, off to make the share
        on, q = rng.random() < seen, 0
        while q < n:
            length = max(1, int(rng.exponential(FPS * (1.0 if on else (1 - seen) / max(seen, 1e-6)))))
            keep[q:q + length] = on
            q += length
            on = not on
    return t[keep], y[keep]


def one(args):
    cfg, seed, N = args
    rng = np.random.default_rng(seed)
    out = dict(cfg=cfg, n=0, cycles=0, untestable=0, ps=[])
    tether._bootstrap_period = lambda *a, **k: 0.01              # the period's error is not what is measured here
    tether.WANDER_P = 2.0                                        # the cycles rule alone decides; the null's p is kept
    for _ in range(N):
        t, y = draw(rng, **cfg)
        if len(t) < 40:
            continue
        out["n"] += 1
        ns = np.round(t * FPS).astype(int) + 1                   # the angle about straight down on a 100-px line, 5 deg of wander
        track = {int(n): (0.0, 0.0) for n in ns}
        comp = {int(n): (100 * np.sin(np.radians(5 * a)), 100 * np.cos(np.radians(5 * a)), 0.0) for n, a in zip(ns, y)}
        sw = tether.swing(track, comp, FPS)
        if not sw.get("swings") and "wander" not in sw:          # no period by the cycles rule: the null was not asked
            continue
        out["cycles"] += 1
        if sw.get("wander") is None:                             # a period, and too few bins to hold it against a wander
            out["untestable"] += 1
        else:
            out["ps"].append(sw["wander"]["p"])
    return out


def main():
    N = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    cfgs = [dict(span=s, tau=tau, noise=noise, seen=seen)
            for s, tau, noise, seen in itertools.product((4.3, 10.0, 32.0), (0.1, 0.3, 1.0, 3.0), (0.0, 0.5), (1.0, 0.4))]
    for s in (4.3, 10.0, 32.0):
        cfgs += [dict(span=s, tau=1.0, noise=0.2, seen=1.0, kind="walk"), dict(span=s, tau=0.3, noise=0.2, seen=1.0, kind="two"),
                 dict(span=s, tau=0.3, noise=0.2, seen=0.4, kind="two")]
    cfgs += [dict(span=s, tau=1.0, noise=0.3, seen=1.0, period=share * s, amp=amp)       # pendulums: the period as a share of the span
             for s, share, amp in itertools.product((4.3, 10.0, 32.0), (0.6, 0.25), (1.0, 2.0, 4.0))]
    with Pool(int(sys.argv[3]) if len(sys.argv) > 3 else 6) as pool:
        res = pool.map(one, [(c, 1000 + i, N) for i, c in enumerate(cfgs)])
    json.dump(res, open(sys.argv[1], "w"), indent=1)
    share = lambda r, a: sum(p <= a for p in r["ps"]) / max(r["n"], 1)
    print("%-78s %5s %6s %5s " % ("kind", "n", "cycles", "untst") + " ".join("p<=%-6g" % a for a in THRESHOLDS))
    for r in res:
        print("%-78s %5d %6.3f %5d " % (json.dumps(r["cfg"])[:78], r["n"], r["cycles"] / max(r["n"], 1), r["untestable"])
              + " ".join("%8.4f" % share(r, a) for a in THRESHOLDS))
    null = [r for r in res if "period" not in r["cfg"]]
    total = sum(r["n"] for r in null)
    cyc = [r["cycles"] / r["n"] for r in null]
    print(f"\n{len(null)} kinds of wander, {total} series. The cycles rule alone: {100 * min(cyc):.0f}-{100 * max(cyc):.0f} % a swing "
          f"({100 * np.median(cyc):.0f} % at the median).")
    for a in THRESHOLDS:
        v = [share(r, a) for r in null]
        print(f"  the whole rule at p <= {a:g}: {100 * min(v):.1f}-{100 * max(v):.1f} % by kind, {sum(x > 0.01 for x in v)} kinds over 1 %, "
              f"{sum(sum(p <= a for p in r['ps']) for r in null)} of {total} in all")
    for amp in (1.0, 2.0, 4.0):
        rs = [r for r in res if r["cfg"].get("amp") == amp and "period" in r["cfg"]]
        print(f"  a pendulum {amp:g} times the wander's size: found in " + ", ".join(
            f"{100 * min(share(r, a) for r in rs):.0f}-{100 * max(share(r, a) for r in rs):.0f} % at p <= {a:g}" for a in (0.01, 0.001)))


if __name__ == "__main__":
    main()
