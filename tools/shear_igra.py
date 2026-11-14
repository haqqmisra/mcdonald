"""How much does the wind change with height? The measurement behind `drift.wind_change` (SHEAR_AT_KM, SHEAR_POWER;
docs/method.md section 34; IDEAS.md DR4, 2026-11-13).

Measured on radiosondes: IGRA v2 (NOAA NCEI, public), the year-to-date 2026 files of 18 stations, 00 and 12 UTC, in the
data folder's `winds_igra/` (its README says where they came from). The quantity is the size of the vector difference
between two wind levels of one sounding, by their height difference and the lower level's height above the ground.

    python3 -I tools/shear_igra.py $MCDONALD_DATA/winds_igra OUT_DIR      (numpy on saved tables; 20 s, 0.7 GB: a batch job)

One pair in eight is kept, drawn by a seeded generator (the whole set is 79 million pairs). It prints the table of
percentiles and writes it as OUT_DIR/shear_table.csv (the package's tests/golden/shear_soundings.csv), fits a power
law to a percentile on the even-numbered stations and holds it against the odd-numbered ones, and counts what T2's
rule does to a true drifter given one wind read a height difference away: before (the wind taken as the object's, the
spread floored at 0.25 m/s) and with the law."""
import json
import math
import sys
import zipfile
from pathlib import Path

import numpy as np

DZ_EDGES = [50, 100, 200, 400, 800, 1600, 3200, 6400]
BANDS = [(0, 1000), (1000, 3000), (3000, 8000), (8000, 16000)]      # the lower level's height above the ground, m
PCT = (50, 68, 90, 95)
KEEP = 8                                                            # one pair in this many
FLIER_MIN, FLOOR, FIX = 10.0, 0.25, 5.0                             # drift's FLIER_MIN, its spread floor, VELOCITY_FIX


def soundings(zpath, elev):
    """The survey's reader (sonde_vs_model_py.py, 2026-11-07): each 00 or 12 UTC sounding's wind levels."""
    txt = zipfile.ZipFile(zpath).read(zipfile.ZipFile(zpath).namelist()[0]).decode("ascii", "replace")
    cur = None
    for line in txt.splitlines():
        if line.startswith("#"):
            if cur and len(cur["z"]) >= 3:
                yield cur
            y, mo, d, hr = int(line[13:17]), int(line[18:20]), int(line[21:23]), int(line[24:26])
            cur = dict(time=f"{y:04d}-{mo:02d}-{d:02d}T{hr:02d}:00", month=mo, z=[], u=[], v=[]) if hr in (0, 12) else None
            continue
        if cur is None:
            continue
        gph, wd, ws = int(line[16:21]), int(line[40:45]), int(line[46:51])
        if gph < -8000 or wd < 0 or ws < 0:
            continue
        z = (elev + 10.0) if line[1] == "1" else float(gph)
        s, a = ws / 10.0, math.radians(wd)
        cur["z"].append(z)
        cur["u"].append(-s * math.sin(a))
        cur["v"].append(-s * math.cos(a))
    if cur and len(cur["z"]) >= 3:
        yield cur


def main(sample, outdir):
    sample, outdir = Path(sample), Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    st = json.loads((sample / "stations.json").read_text())
    rng = np.random.default_rng(20261113)
    cols = dict(k=[], month=[], low=[], dz=[], d=[], snd=[])
    names, nsnd, total = sorted(st), 0, 0
    for k, sid in enumerate(names):
        s = st[sid]
        z = sample / "igra" / f"{sid}-data-beg2026.txt.zip"
        if not z.exists():
            continue
        elev = s["elev"]
        if elev < -900:                 # IGRA lists no height for the station: the data folder's stations.json gives one
            print(f"{sid}: no height above the sea in stations.json, left out", flush=True)
            continue
        n = 0
        for snd in soundings(z, elev):
            o = np.argsort(snd["z"])
            zs, u, v = np.array(snd["z"])[o], np.array(snd["u"])[o], np.array(snd["v"])[o]
            keep = np.r_[True, np.diff(zs) > 1.0]
            zs, u, v = zs[keep], u[keep], v[keep]
            i, j = np.triu_indices(len(zs), 1)
            dz = zs[j] - zs[i]
            m = (dz >= DZ_EDGES[0]) & (dz < DZ_EDGES[-1])
            total += int(m.sum())
            m &= rng.integers(0, KEEP, len(dz)) == 0
            i, j = i[m], j[m]
            cols["k"].append(np.full(len(i), k, np.uint8))
            cols["month"].append(np.full(len(i), snd["month"], np.uint8))
            cols["low"].append((zs[i] - elev).astype(np.float32))
            cols["dz"].append(dz[m].astype(np.float32))
            cols["d"].append(np.hypot(u[j] - u[i], v[j] - v[i]).astype(np.float32))
            cols["snd"].append(np.full(len(i), nsnd, np.uint16))
            n += 1
            nsnd += 1
        print(f"{sid} {s['cls']:14s} elev {elev:6.0f} m: {n} soundings", flush=True)
    K, MO, LOW, DZ, D, SND = (np.concatenate(cols[c]) for c in ("k", "month", "low", "dz", "d", "snd"))
    print(f"\n{nsnd} soundings at {len(names)} stations, {total:,} pairs of wind levels, {len(D):,} kept (one in {KEEP})\n")
    print("the size of the wind's vector change between two levels of one sounding, m/s: median / 68th / 90th / 95th percentile (pairs kept)")
    print("height above the ground of the lower level | " + " | ".join(f"dz {a}-{b} m" for a, b in zip(DZ_EDGES[:-1], DZ_EDGES[1:])))
    with open(outdir / "shear_table.csv", "w") as f:
        f.write(f"# The wind's vector change (m/s) between two wind levels of one radiosonde sounding, by the lower level's height above\n"
                f"# the ground and the levels' height difference: IGRA v2 (NOAA NCEI), {len(names)} stations, {nsnd} soundings at 00 and 12 UTC,\n"
                f"# 2026 to early November; one pair in {KEEP} kept of {total:,}. Made by mcdonald's tools/shear_igra.py from the data folder's winds_igra/.\n"
                "# low_m, high_m: the lower level's height above the ground; dz: the two levels' height difference; p50-p95: percentiles.\n"
                "low_m,high_m,dz_low_m,dz_high_m,dz_median_m,pairs,p50,p68,p90,p95\n")
        for lo, hi in BANDS + [(0, 16000)]:
            cells = []
            for a, b in zip(DZ_EDGES[:-1], DZ_EDGES[1:]):
                m = (LOW >= lo) & (LOW < hi) & (DZ >= a) & (DZ < b)
                if m.sum() < 30:
                    cells.append("-")
                    continue
                q = np.percentile(D[m], PCT)
                cells.append("/".join(f"{x:.1f}" for x in q) + f" ({m.sum():,})")
                f.write(f"{lo},{hi},{a},{b},{np.median(DZ[m]):.0f},{m.sum()}," + ",".join(f"{x:.2f}" for x in q) + "\n")
            print(f"{lo}-{hi} m | " + " | ".join(cells))
    even, odd = K % 2 == 0, K % 2 == 1
    laws = {}
    for pct in (68, 90, 95):
        print(f"\nthe {pct}th percentile as c (dz / 1 km)^g, set on the even-numbered stations ({even.sum():,} pairs), by height band:")
        for lo, hi in BANDS + [(0, 16000)]:
            xs, ys = [], []
            for a, b in zip(DZ_EDGES[:-1], DZ_EDGES[1:]):
                m = even & (LOW >= lo) & (LOW < hi) & (DZ >= a) & (DZ < b)
                if m.sum() >= 100:
                    xs.append(math.log(np.median(DZ[m]) / 1000.0))
                    ys.append(math.log(np.percentile(D[m], pct)))
            if len(xs) < 3:
                print(f"   {lo}-{hi} m: too few bins")
                continue
            g, lc = np.polyfit(xs, ys, 1)
            c = math.exp(lc)
            laws[(pct, lo, hi)] = (c, g)
            mB = odd & (LOW >= lo) & (LOW < hi)
            under = np.mean(D[mB] <= c * (DZ[mB] / 1000.0) ** g)
            by_dz = []
            for a, b in zip(DZ_EDGES[:-1], DZ_EDGES[1:]):
                mm = mB & (DZ >= a) & (DZ < b)
                if mm.sum() >= 100:
                    by_dz.append(f"{np.mean(D[mm] <= c * (DZ[mm] / 1000.0) ** g):.2f}")
            idx = np.flatnonzero(mB)
            idx = idx[np.random.default_rng(1).permutation(len(idx))]
            _, first = np.unique(SND[idx], return_index=True)          # one pair a sounding: pairs of one sounding are not independent
            jj = idx[first]
            print(f"   {lo}-{hi} m: c {c:.2f} m/s, g {g:.2f}; on the odd-numbered stations {under:.3f} of {mB.sum():,} pairs lie under it "
                  f"(by dz bin: {', '.join(by_dz)}); one pair a sounding: {np.mean(D[jj] <= c * (DZ[jj] / 1000.0) ** g):.3f} of {len(jj):,}")
    print("\nthe 90th percentile at dz 800-1600 m, the lower level 1-8 km above the ground: by station, and by half-year")
    m0 = (LOW >= 1000) & (LOW < 8000) & (DZ >= 800) & (DZ < 1600)
    for k, sid in enumerate(names):
        m = m0 & (K == k)
        if m.sum() >= 100:
            print(f"   {sid} {st[sid]['cls']:14s}: {np.percentile(D[m], 90):.1f} m/s ({m.sum():,} pairs)")
    for nm, months in (("November-April", (11, 12, 1, 2, 3, 4)), ("May-October", (5, 6, 7, 8, 9, 10))):
        m = m0 & np.isin(MO, months)
        print(f"   {nm}: {np.percentile(D[m], 90):.1f} m/s ({m.sum():,} pairs)")
    # what T2 does to a true drifter given one wind read dz away (the fitted velocity taken as exact), odd-numbered stations
    c, g = laws[(90, 0, 16000)]
    print(f"\na body drifting with the wind at its own height, T2 given one wind read dz away, on the odd-numbered stations; the law "
          f"{c:.2f} (dz / 1 km)^{g:.2f} m/s (the 90th percentile, every height):")
    print("   dz (m) | pairs | before: passes / cannot say / FAILS | with the law: passes / cannot say / fails | the law's allowance (m/s)")
    for mid in (100, 200, 300, 400, 800, 1422, 3000):
        m = odd & (DZ >= 0.85 * mid) & (DZ < 1.15 * mid)
        d = D[m]
        allow = c * (mid / 1000.0) ** g
        old = (np.mean(d <= FLOOR), np.mean((d > FLOOR) & (d < FLOOR + FLIER_MIN)), np.mean(d >= FLOOR + FLIER_MIN))
        if allow > FIX:
            new = (0.0, np.mean(d < FLOOR + allow + FLIER_MIN), np.mean(d >= FLOOR + allow + FLIER_MIN))
        else:
            new = (np.mean(d <= FLOOR + allow), np.mean((d > FLOOR + allow) & (d < FLOOR + allow + FLIER_MIN)), np.mean(d >= FLOOR + allow + FLIER_MIN))
        print(f"   {mid:5d} | {m.sum():,} | {old[0]:.3f} / {old[1]:.3f} / {old[2]:.3f} | {new[0]:.3f} / {new[1]:.3f} / {new[2]:.4f} | {allow:.1f}"
              + ("  (over 5 m/s: T2 cannot pass on it)" if allow > FIX else ""))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
