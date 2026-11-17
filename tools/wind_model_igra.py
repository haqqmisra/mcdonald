"""How far does a weather model's wind miss the air's own motion, and what does `drift`'s T2 do with that? The
measurement behind docs/method.md section 68 (2026-11-17).

Truth: radiosondes, IGRA v2 (NOAA NCEI, public), the year-to-date 2026 files of 18 stations at 00 and 12 UTC, in the
data folder's `winds_igra/igra/`. The test's input: Open-Meteo's hourly model winds (its historical-forecast API with
no `models=`, the product the Yemen and Galileo wind files came from) at each station's point and at two more points
340 km west and 520 km east of it, in `winds_igra/model/<station>_<c|w|e>_<YYYY-MM>.json` (`--fetch` gets them: a
public API, no key, a generic client name).

    python tools/wind_model_igra.py $MCDONALD_DATA/winds_igra OUT_DIR [--workers N] [--fetch]

It imports the package (`drift.hourly_levels`, `drift._at`, `drift.wind_samples`, `drift.test_wind`), so it is a batch
job: about 25 minutes on 18 CPUs, 2 GB each. It prints, and writes to OUT_DIR:
- A. the model's vector wind error against the soundings by height above the station, place class, station and
  half-year, at the sounding's hour and the hour before (`wind_error.csv`);
- B1. the error of the model's wind DIFFERENCE between two heights, by their separation, as a vector and across a
  heading (`difference_error.csv`; the two tables together are the package's tests/golden/wind_model_soundings.csv);
- B2. what T2 "from the ranges" (`drift.test_wind`) says of drawn cases whose truth is a sounding: a body drifting
  with the sounding's wind at the object's height, and bodies flying 5, 10, 25 and 50 m/s through that air in eight
  directions, seen from an aircraft at the aircraft's height flying a heading at an MQ-9's airspeed, with the model's
  winds as the test's input (`cases.npz`, one row a call of `drift.test_wind`).
The design (heights, cells, hours, the split of the stations) is in the method section; nothing here sets a rule."""
import json
import math
import sys
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

KN = 0.514444
OBJ_M, AIR_M = 3695.0, 7488.0                  # the Yemen clip's heights above the sea (tests/golden/hellfire_drift)
V_ERR = (0.90, 0.33)                           # m/s, east and north: the Yemen line's own errors (drift.fit_line)
TAS_KN = (120.0, 220.0)                        # the aircraft's true airspeed, drawn uniformly (an MQ-9's; a judgement)
AIR_RANGE_KN = (0.0, 240.0)                    # --airspeed-kn, as the Yemen run gave it
HEADINGS = 12
SPEEDS = (5.0, 10.0, 25.0, 50.0)               # m/s through the air
DIRECTIONS = tuple(range(0, 360, 45))          # degrees clockwise from the aircraft's heading
HEIGHTS = (500, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 7500, 9000)      # m above the station
BANDS = ((0, 1000), (1000, 3000), (3000, 6000), (6000, 10000))
SEPARATIONS = (500, 1000, 2000, 3000, AIR_M - OBJ_M, 5000, 6000)            # m above OBJ_M
LEVEL_PAIRS = ((700, 500), (500, 400), (700, 400), (700, 300), (850, 700), (850, 400))
PL_ALL = (1000, 925, 850, 800, 700, 600, 500, 400, 300, 250, 200)
PL_YEMEN = (700, 600, 400)                     # the Yemen files' levels; heights for 600 and 400 only
PL_FULL = (700, 600, 500, 400)
PL_NB = (700, 600, 500, 400)
DESIGNS = ("Y3", "Y1", "T3", "S1")             # three cells x 24 h (the Yemen run's shape); one cell x 24 h; one cell, t-1..t+1; t
LEVELSETS = ("yemen", "full")
WEST_KM, EAST_KM = 340.0, 520.0
LEFT_OUT = "USM00072393"                       # Vandenberg: reported apart (bad wind levels; IGRA lists no height for it)
COLD = (11, 12, 1, 2, 3, 4)
MONTHS = [("2026-01-01", "2026-01-31"), ("2026-02-01", "2026-02-28"), ("2026-03-01", "2026-03-31"),
          ("2026-04-01", "2026-04-30"), ("2026-05-01", "2026-05-31"), ("2026-06-01", "2026-06-30"),
          ("2026-07-01", "2026-07-31"), ("2026-08-01", "2026-08-31"), ("2026-09-01", "2026-09-30"),
          ("2026-10-01", "2026-10-31"), ("2026-11-01", "2026-11-07")]
URL = "https://historical-forecast-api.open-meteo.com/v1/forecast?"


# ---- the model files ---------------------------------------------------------------------------------------------------
def variables(levels, heights=()):
    v = []
    for h in heights:
        v += [f"wind_speed_{h}m", f"wind_direction_{h}m"]
    for p in levels:
        v += [f"wind_speed_{p}hPa", f"wind_direction_{p}hPa", f"geopotential_height_{p}hPa"]
    return v


def fetch(sample, months=MONTHS, pause=3.0):
    """The model files, a month a request, paced; files already there are kept."""
    import urllib.parse
    import urllib.request
    st = json.loads((sample / "stations.json").read_text())
    (sample / "model").mkdir(exist_ok=True)
    for sid in sorted(st):
        lat, lon = st[sid]["lat"], st[sid]["lon"]
        km = 111.195 * math.cos(math.radians(lat))
        cells = dict(c=(lon, PL_ALL, (10, 100)), w=(lon - WEST_KM / km, PL_NB, ()), e=(lon + EAST_KM / km, PL_NB, ()))
        for a, b in months:
            for cell, (lo, levels, heights) in cells.items():
                p = sample / "model" / f"{sid}_{cell}_{a[:7]}.json"
                if p.exists() and p.stat().st_size > 500:
                    continue
                q = dict(latitude=f"{lat:.4f}", longitude=f"{lo:.4f}", start_date=a, end_date=b,
                         hourly=",".join(variables(levels, heights)), wind_speed_unit="kn", timezone="GMT")
                req = urllib.request.Request(URL + urllib.parse.urlencode(q), headers={"User-Agent": "python-urllib"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                json.loads(data)["hourly"]["time"][0]
                p.write_bytes(data)
                print(p.name, flush=True)
                time.sleep(pause)


def keep(d, levels, with_height):
    """A model file cut down to some pressure levels, as a file fetched with only those would be."""
    h = d["hourly"]
    out = dict(time=h["time"])
    for p in levels:
        out[f"wind_speed_{p}hPa"] = h[f"wind_speed_{p}hPa"]
        out[f"wind_direction_{p}hPa"] = h[f"wind_direction_{p}hPa"]
        if p in with_height:
            out[f"geopotential_height_{p}hPa"] = h[f"geopotential_height_{p}hPa"]
    return dict(d, hourly=out)


def model_hours(drift, folder, sid, cell, levels=None, with_height=None):
    """{time: (heights, winds)} over the year for one station's cell, read by drift.hourly_levels; an hour with a
    level missing is left out, so that every hour kept holds every level asked for."""
    out = {}
    for f in sorted(folder.glob(f"{sid}_{cell}_*.json")):
        d = json.loads(f.read_text())
        want = len(levels) if levels else None
        if levels:
            d = keep(d, levels, with_height)
        else:
            want = sum(1 for k in d["hourly"] if k.startswith("wind_speed_") and k.endswith("hPa"))
            d = dict(d, hourly={k: v for k, v in d["hourly"].items() if k == "time" or k.endswith("hPa")})
        for t, zs, us in drift.hourly_levels(d):
            if len(zs) == want:
                out[t] = (zs, us)
    return out


# ---- the soundings -----------------------------------------------------------------------------------------------------
def soundings(zpath, elev):
    """Each 00 or 12 UTC sounding's wind levels (IGRA v2's fixed columns): heights above the sea, winds east and north
    (m/s), and the standard pressure levels that carry both a height and a wind. A wind level given by pressure alone
    is placed at a height interpolated in ln(p) between the sounding's own levels that have a height (the Middle East
    stations report most wind levels so); `tools/shear_igra.py`'s reader drops such levels."""
    z = zipfile.ZipFile(zpath)
    txt = z.read(z.namelist()[0]).decode("ascii", "replace")
    cur = None

    def done(cur):
        if cur is None:
            return None
        anchors = sorted(set(cur["anchors"]), reverse=True)                  # (p, z), p falling
        lp = np.log([a[0] for a in anchors]) if len(anchors) >= 2 else None
        zs, u, v = [], [], []
        for p, gz, wu, wv in cur["winds"]:
            if gz is None:
                if lp is None or not (anchors[-1][0] <= p <= anchors[0][0]):
                    continue
                gz = float(np.interp(-math.log(p), -lp, [a[1] for a in anchors]))
            zs.append(gz)
            u.append(wu)
            v.append(wv)
        if len(zs) < 3:
            return None
        o = np.argsort(zs)
        zs, u, v = np.array(zs)[o], np.array(u)[o], np.array(v)[o]
        k = np.r_[True, np.diff(zs) > 1.0]
        return dict(time=cur["time"], month=cur["month"], z=zs[k], u=u[k], v=v[k], std=cur["std"])

    for line in txt.splitlines():
        if line.startswith("#"):
            s = done(cur)
            if s:
                yield s
            y, mo, d, hr = int(line[13:17]), int(line[18:20]), int(line[21:23]), int(line[24:26])
            cur = dict(time=f"{y:04d}-{mo:02d}-{d:02d}T{hr:02d}:00", month=mo, winds=[], anchors=[], std={}) if hr in (0, 12) else None
            continue
        if cur is None:
            continue
        p, gph, wd, ws = int(line[9:15]), int(line[16:21]), int(line[40:45]), int(line[46:51])
        surface = line[1] == "1"
        gz = (elev + 10.0) if surface else (float(gph) if gph > -8000 else None)
        if p > 0 and (surface or gph > -8000):
            cur["anchors"].append((float(p), elev if surface else float(gph)))
        if wd < 0 or ws < 0 or (gz is None and p <= 0):
            continue
        a = math.radians(wd)
        wu, wv = -ws / 10.0 * math.sin(a), -ws / 10.0 * math.cos(a)
        cur["winds"].append((float(p), gz, wu, wv))
        if p % 100 == 0 and p // 100 in (850, 700, 600, 500, 400, 300) and gph > -8000 and not surface:
            cur["std"][p // 100] = (float(gph), wu, wv)
    s = done(cur)
    if s:
        yield s


def sonde_at(s, z, elev):
    """The sounding's wind at a height: linear between the two wind levels that bracket it, only where they are no
    more than 1,000 m apart (under 3 km above the station) or 1,500 m (above); else None."""
    zs = s["z"]
    i = int(np.searchsorted(zs, z))
    if i == 0 or i >= len(zs):
        return None
    if zs[i] - zs[i - 1] > (1000.0 if z - elev < 3000.0 else 1500.0):
        return None
    f = (z - zs[i - 1]) / (zs[i] - zs[i - 1])
    return np.array([s["u"][i - 1] + f * (s["u"][i] - s["u"][i - 1]), s["v"][i - 1] + f * (s["v"][i] - s["v"][i - 1])])


def hour(t, dh):
    return (datetime.fromisoformat(t) + timedelta(hours=dh)).isoformat(timespec="minutes")


# ---- one station -------------------------------------------------------------------------------------------------------
def station(args):
    """Everything for one station: the rows of the three tables. A worker of the pool."""
    sample, k, sid, s, src = args
    if src:
        sys.path.insert(0, src)
    import mcdonald
    from mcdonald import drift
    sample = Path(sample)
    elev = s["elev"]
    full = model_hours(drift, sample / "model", sid, "c")
    sets = {(cell, ls): model_hours(drift, sample / "model", sid, cell, PL_YEMEN if ls == "yemen" else PL_FULL,
                                    (600, 400) if ls == "yemen" else PL_FULL)
            for cell in "cwe" for ls in LEVELSETS}
    rng = np.random.default_rng([20261117, k])
    err, dif, cases = [], [], []
    n = 0
    checked = 0
    for j, snd in enumerate(soundings(sample / "igra" / f"{sid}-data-beg2026.txt.zip", elev)):
        t = snd["time"]
        n += 1
        week = (datetime.fromisoformat(t) - datetime(2026, 1, 1)).days // 7
        tag = (k, j, snd["month"], week)
        # A: the model's wind against the sounding's, by height above the station
        for lag in (0, -1):
            m = full.get(hour(t, lag))
            if m is None:
                continue
            for h in HEIGHTS:
                w = sonde_at(snd, elev + h, elev)
                if w is None or not (m[0][0] <= elev + h <= m[0][-1]):
                    continue
                e = drift._at(*m, elev + h) - w
                err.append((*tag, lag, h, e[0], e[1], float(np.hypot(*w))))
        # B1: the model's wind difference between two heights against the sounding's
        pairs = [("H", dz, sonde_at(snd, OBJ_M, elev), sonde_at(snd, OBJ_M + dz, elev), OBJ_M, OBJ_M + dz) for dz in SEPARATIONS]
        for lo, hi in LEVEL_PAIRS:
            if lo in snd["std"] and hi in snd["std"]:
                a, b = snd["std"][lo], snd["std"][hi]
                pairs.append((f"L{lo}-{hi}", b[0] - a[0], np.array(a[1:]), np.array(b[1:]), a[0], b[0]))
        for geom, dz, w1, w2, z1, z2 in pairs:
            if w1 is None or w2 is None:
                continue
            for lag in (0, -1):
                for ls, table in (("all", full), ("yemen", sets[("c", "yemen")]), ("full", sets[("c", "full")])):
                    m = table.get(hour(t, lag))
                    if m is None or (ls == "all" and not (m[0][0] <= z1 and z2 <= m[0][-1])):
                        continue
                    d = (drift._at(*m, z2) - drift._at(*m, z1)) - (w2 - w1)
                    dif.append((*tag, lag, geom, ls, dz, d[0], d[1], float(np.hypot(*(w2 - w1)))))
        # B2: T2 "from the ranges" on drawn cases, at the clip's heights (H) and at the sounding's own levels (L)
        geoms = []
        wo, wa = sonde_at(snd, OBJ_M, elev), sonde_at(snd, AIR_M, elev)
        if wo is not None and wa is not None:
            geoms.append((0, OBJ_M, AIR_M, wo, wa))
        if 700 in snd["std"] and 400 in snd["std"]:
            a, b = snd["std"][700], snd["std"][400]
            geoms.append((1, a[0], b[0], np.array(a[1:]), np.array(b[1:])))
        day = [f"{t[:10]}T{h:02d}:00" for h in range(24)]
        head0 = rng.uniform(0.0, 360.0)
        tas = rng.uniform(*TAS_KN, HEADINGS)
        noise = rng.normal(0.0, 1.0, (HEADINGS, 2)) * np.array(V_ERR)
        for g, zo, za, wo, wa in geoms:
            for di, design in enumerate(DESIGNS):
                for li, ls in enumerate(LEVELSETS):
                    want = [(c, h) for c in ("cwe" if design == "Y3" else "c")
                            for h in (day if design in ("Y3", "Y1") else [hour(t, -1), t, hour(t, 1)] if design == "T3" else [t])]
                    if any(h not in sets[(c, ls)] for c, h in want):
                        continue
                    winds = [dict(file=c, time=h, w_obj=drift._at(*sets[(c, ls)][h], zo), w_air=drift._at(*sets[(c, ls)][h], za))
                             for c, h in want]
                    if design == "Y3" and ls == "yemen" and g == 0 and checked < 2:      # the same samples by drift.wind_samples
                        checked += check_samples(drift, sample, sid, t, winds, zo, za)
                    bodies = [(0.0, -1), (0.0, -2)]
                    if ls == "yemen" and design in ("Y3", "T3"):
                        bodies += [(sp, dr) for sp in SPEEDS for dr in DIRECTIONS]
                    for hi in range(HEADINGS):
                        hd = (head0 + hi * 360.0 / HEADINGS) % 360.0
                        r = math.radians(hd)
                        h_hat = np.array([math.sin(r), math.cos(r)])
                        p_hat = np.array([-math.cos(r), math.sin(r)])
                        base = (wo - wa) - tas[hi] * KN * h_hat
                        for sp, dr in bodies:
                            a = math.radians(hd + max(dr, 0))
                            v = base + sp * np.array([math.sin(a), math.cos(a)])
                            if dr == -2:                                     # the mirror: the sideways motion's sign turned
                                v = v - 2.0 * (v @ p_hat) * p_hat
                            v = v + noise[hi]
                            line = dict(v_m_s=[float(v[0]), float(v[1]), 0.0], speed_m_s=float(np.hypot(*v)),
                                        toward_deg=math.degrees(math.atan2(v[0], v[1])) % 360, range_rms_m=0.0)
                            out = drift.test_wind(line, hd, winds, speeds=(), air_min_kn=AIR_RANGE_KN[0], air_max_kn=AIR_RANGE_KN[1])
                            cases.append((*tag, g, di, li, hd, tas[hi], sp, dr, out["outcome"] == drift.PASS, out["same_side"],
                                          *out["airspeed_kn"], *out["shortfall_kn"], *out["wind_difference_right_kn"],
                                          out["sideways_right_kn"], float(-((wo - wa) @ p_hat) / KN), len(winds)))
    return dict(sid=sid, k=k, n=n, err=err, dif=dif, cases=np.array(cases, np.float32), file=mcdonald.__file__, checked=checked)


def check_samples(drift, sample, sid, t, winds, zo, za):
    """The samples built here against drift.wind_samples on files of the Yemen files' shape (three cells, one day,
    700/600/400 hPa with heights for 600 and 400), written to a temporary folder."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for c in "cwe":
            d = json.loads((sample / "model" / f"{sid}_{c}_{t[:7]}.json").read_text())
            d = keep(d, PL_YEMEN, (600, 400))
            i = [n for n, x in enumerate(d["hourly"]["time"]) if x[:10] == t[:10]]
            d["hourly"] = {key: [val[n] for n in i] for key, val in d["hourly"].items()}
            p = Path(tmp) / f"{c}.json"
            p.write_text(json.dumps(d))
            paths.append(str(p))
        ref = drift.wind_samples(paths, zo, za)
    same = len(ref) == len(winds) and all(np.allclose(a["w_obj"], b["w_obj"]) and np.allclose(a["w_air"], b["w_air"]) and a["time"] == b["time"]
                                          for a, b in zip(ref, winds))
    if not same:
        raise SystemExit(f"{sid} {t}: the samples differ from drift.wind_samples'")
    return 1


# ---- the tables --------------------------------------------------------------------------------------------------------
def boot(groups, stat, rng, n=400):
    """A statistic's 16th and 84th percentiles over a bootstrap of the groups (station-weeks)."""
    keys = np.unique(groups)
    idx = {g: np.flatnonzero(groups == g) for g in keys}
    vals = []
    for _ in range(n):
        pick = keys[rng.integers(0, len(keys), len(keys))]
        vals.append(stat(np.concatenate([idx[g] for g in pick])))
    return np.nanpercentile(vals, [16, 84])


def main(sample, outdir, workers=18, src=None):
    from multiprocessing import Pool
    sample, outdir = Path(sample), Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    st = json.loads((sample / "stations.json").read_text())
    names = sorted(st)
    jobs = [(str(sample), k, sid, st[sid], src) for k, sid in enumerate(names)]
    with Pool(min(workers, len(jobs))) as pool:
        res = sorted(pool.map(station, jobs, chunksize=1), key=lambda r: r["k"])
    print("mcdonald from", res[0]["file"])
    print(f"{sum(r['n'] for r in res)} soundings at {len(names)} stations; samples checked against drift.wind_samples: "
          f"{sum(r['checked'] for r in res)} soundings, all the same")
    cls = np.array([st[s]["cls"] for s in names])
    pooled = np.array([s != LEFT_OUT for s in names])
    rng = np.random.default_rng(20261117)
    ERR = np.array([r for x in res for r in x["err"]], float)          # k, j, month, week, lag, h, eE, eN, speed
    DIF = [r for x in res for r in x["dif"]]
    C = np.concatenate([x["cases"] for x in res if len(x["cases"])])
    np.savez_compressed(outdir / "cases.npz", cases=C, stations=np.array(names), classes=cls,
                        columns=np.array("k j month week geom design levelset heading tas_kn speed dir passes same_side air_min air_max "
                                         "slip_min slip_max dwr_min dwr_max side_right true_right samples".split()))
    np.save(outdir / "err.npy", ERR)
    with open(outdir / "dif.json", "w") as f:
        json.dump(DIF, f)

    def pct(x):
        return np.percentile(x, [50, 68, 90, 95])

    # ---- A
    k, month, week, lag, h = (ERR[:, i].astype(int) for i in (0, 2, 3, 4, 5))
    size = np.hypot(ERR[:, 6], ERR[:, 7])
    grp = k * 100 + week
    use = pooled[k]
    lines = ["# How far a model's wind misses a radiosonde's, and how far its wind DIFFERENCE between two heights does (m/s).",
             f"# IGRA v2 (NOAA NCEI), {len(names)} stations ({LEFT_OUT} reported apart: kind 'wind_left_out'), 00 and 12 UTC, 2026 to early November;",
             "# the model: Open-Meteo's historical-forecast API (no model named), read as mcdonald's drift.hourly_levels reads it.",
             "# Made by mcdonald's tools/wind_model_igra.py from the data folder's winds_igra/. lag_h: 0 the sounding's hour, -1 the hour before.",
             "# kind 'wind': low_m-high_m the height above the station. kind 'difference': the wind at 3,695 m above the sea against the wind",
             "# low_m (= high_m) above it; 'difference_levels': the sounding's own pressure levels, low_m-high_m in hPa. levels: the model",
             "# levels read. p50-p95: percentiles of the vector error; across_sd, across_p90, across_p95: its part across one heading.",
             "kind,lag_h,levels,low_m,high_m,soundings,p50,p68,p90,p95,rms,under_3,across_sd,across_p90,across_p95"]
    print("\n== A. the model's vector wind error against the soundings (m/s): median / 68th / 90th / 95th percentile, rms, share under 3 m/s")
    for lg, lab in ((0, "at the sounding's hour"), (-1, "the hour before")):
        print(f"  {lab}, {int(pooled.sum())} stations pooled; errors: 16th-84th percentile of a bootstrap over station-weeks")
        for lo, hi in BANDS + ((0, 10000),):
            m = use & (lag == lg) & (h > lo) & (h <= hi)
            if m.sum() < 30:
                continue
            q = pct(size[m])
            b90 = boot(grp[m], lambda i, s=size[m]: np.percentile(s[i], 90), rng)
            b50 = boot(grp[m], lambda i, s=size[m]: np.percentile(s[i], 50), rng)
            b3 = boot(grp[m], lambda i, s=size[m]: np.mean(s[i] <= 3.0), rng)
            ac = ERR[m, 6]                                             # one fixed direction: the east component
            print(f"   {lo / 1000:g}-{hi / 1000:g} km above the station: n {m.sum():6d} | {q[0]:.2f} ({b50[0]:.2f}-{b50[1]:.2f}) / {q[1]:.2f} / "
                  f"{q[2]:.2f} ({b90[0]:.2f}-{b90[1]:.2f}) / {q[3]:.2f} | rms {np.sqrt(np.mean(size[m] ** 2)):.2f} | under 3 m/s "
                  f"{np.mean(size[m] <= 3):.3f} ({b3[0]:.3f}-{b3[1]:.3f}) | one component sd {np.std(np.r_[ERR[m, 6], ERR[m, 7]]):.2f}")
            lines.append(f"wind,{lg},all,{lo},{hi},{len(np.unique(k[m] * 10000 + ERR[m, 1].astype(int)))},{q[0]:.2f},{q[1]:.2f},{q[2]:.2f},{q[3]:.2f},"
                         f"{np.sqrt(np.mean(size[m] ** 2)):.2f},{np.mean(size[m] <= 3):.3f},{np.std(ac):.2f},{np.percentile(np.abs(ac), 90):.2f},{np.percentile(np.abs(ac), 95):.2f}")
        m = (~use) & (lag == lg)
        if m.sum():
            q = pct(size[m])
            print(f"   {LEFT_OUT} alone, every height: n {m.sum()} | {q[0]:.2f} / {q[1]:.2f} / {q[2]:.2f} / {q[3]:.2f} | over 20 m/s: {np.mean(size[m] > 20):.3f} "
                  f"(the pooled stations: {np.mean(size[use & (lag == lg)] > 20):.4f})")
            lines.append(f"wind_left_out,{lg},all,0,10000,{len(np.unique(ERR[m, 1]))},{q[0]:.2f},{q[1]:.2f},{q[2]:.2f},{q[3]:.2f},"
                         f"{np.sqrt(np.mean(size[m] ** 2)):.2f},{np.mean(size[m] <= 3):.3f},,,")
    print("  by height above the station, the hour before / the sounding's hour: median, 90th, 95th percentile")
    for hh in HEIGHTS:
        row = []
        for lg in (-1, 0):
            m = use & (lag == lg) & (h == hh)
            row.append("  ".join(f"{x:.2f}" for x in np.percentile(size[m], [50, 90, 95])) + f" (n {m.sum()})" if m.sum() >= 30 else "-")
        print(f"   {hh:5d} m: {row[0]}   |   {row[1]}")
    print("  by place class, 1-6 km above the station, the hour before: median / 90th / 95th, share under 3 m/s; then November-April and May-October 90th")
    m0 = (lag == -1) & (h > 1000) & (h <= 6000)
    cold = np.isin(month, COLD)
    for c in sorted(set(cls)):
        m = m0 & use & (cls[k] == c)
        if m.sum() >= 30:
            q = pct(size[m])
            print(f"   {c:14s}: n {m.sum():6d} | {q[0]:.2f} / {q[2]:.2f} / {q[3]:.2f} | {np.mean(size[m] <= 3):.3f} | "
                  f"{np.percentile(size[m & cold], 90) if (m & cold).sum() > 30 else float('nan'):.2f}  {np.percentile(size[m & ~cold], 90) if (m & ~cold).sum() > 30 else float('nan'):.2f}")
    print("  by station, 1-6 km above the station, the hour before:")
    for kk, sid in enumerate(names):
        m = m0 & (k == kk)
        if m.sum() >= 30:
            q = pct(size[m])
            print(f"   {sid} {cls[kk]:14s}: n {m.sum():6d} | {q[0]:.2f} / {q[2]:.2f} / {q[3]:.2f} | {np.mean(size[m] <= 3):.3f}")
    for nm, mm in (("November-April", cold), ("May-October", ~cold)):
        m = m0 & use & mm
        q = pct(size[m])
        print(f"   {nm}: n {m.sum()} | {q[0]:.2f} / {q[2]:.2f} / {q[3]:.2f} | {np.mean(size[m] <= 3):.3f}")

    # ---- B1
    dk = np.array([r[0] for r in DIF])
    dlag = np.array([r[4] for r in DIF])
    dgeom = np.array([r[5] for r in DIF])
    dls = np.array([r[6] for r in DIF])
    ddz = np.array([r[7] for r in DIF], float)
    dE, dN = np.array([r[8] for r in DIF], float), np.array([r[9] for r in DIF], float)
    dtrue = np.array([r[10] for r in DIF], float)
    dweek = np.array([r[3] for r in DIF])
    dsize = np.hypot(dE, dN)
    duse = pooled[dk]
    print("\n== B1. the error of the model's wind DIFFERENCE between two heights (m/s): vector median / 68th / 90th / 95th; across one heading: "
          "sd, 90th and 95th percentile of its size; the true difference's median size")
    for lg, lab in ((-1, "the hour before"), (0, "at the sounding's hour")):
        for ls in ("all", "yemen", "full"):
            print(f"  {lab}; model levels: {ls}")
            for geom, dzs in (("H", SEPARATIONS), *[(f"L{a}-{b}", (None,)) for a, b in LEVEL_PAIRS]):
                for dz in dzs:
                    m = duse & (dlag == lg) & (dls == ls) & (dgeom == geom) & ((ddz == dz) if dz is not None else True)
                    if m.sum() < 30:
                        continue
                    q = pct(dsize[m])
                    ac = np.r_[dE[m], dN[m]]                             # every heading is as good as another: both components
                    g2 = (dk * 100 + dweek)[m]
                    b90 = boot(g2, lambda i, s=dsize[m]: np.percentile(s[i], 90), rng, 200)
                    what = f"3,695 m and {dz:g} m above it" if geom == "H" else f"the sounding's {geom[1:]} hPa levels ({np.median(ddz[m]):.0f} m apart)"
                    print(f"   {what}: n {m.sum():5d}, stations {len(set(dk[m]))} | {q[0]:.2f} / {q[1]:.2f} / {q[2]:.2f} ({b90[0]:.2f}-{b90[1]:.2f}) / {q[3]:.2f} | "
                          f"across: sd {np.std(ac):.2f}, {np.percentile(np.abs(ac), 90):.2f}, {np.percentile(np.abs(ac), 95):.2f} | true {np.median(dtrue[m]):.1f}")
                    lo, hi = (f"{dz:g}", f"{dz:g}") if geom == "H" else tuple(geom[1:].split("-"))
                    lines.append(f"{'difference' if geom == 'H' else 'difference_levels'},{lg},{ls},{lo},{hi},{m.sum()},{q[0]:.2f},{q[1]:.2f},"
                                 f"{q[2]:.2f},{q[3]:.2f},{np.sqrt(np.mean(dsize[m] ** 2)):.2f},{np.mean(dsize[m] <= 3):.3f},{np.std(ac):.2f},"
                                 f"{np.percentile(np.abs(ac), 90):.2f},{np.percentile(np.abs(ac), 95):.2f}")
    (outdir / "wind_model_table.csv").write_text("\n".join(lines) + "\n")
    print("  the 700-400 hPa pair by station, the hour before, every model level: vector median / 90th; across sd; true difference's median")
    for kk, sid in enumerate(names):
        m = (dk == kk) & (dlag == -1) & (dls == "all") & (dgeom == "L700-400")
        if m.sum() >= 20:
            print(f"   {sid} {cls[kk]:14s}: n {m.sum():4d} | {np.median(dsize[m]):.2f} / {np.percentile(dsize[m], 90):.2f} | {np.std(np.r_[dE[m], dN[m]]):.2f} | {np.median(dtrue[m]):.1f}")

    # ---- B2
    rates(C, names, cls, pooled, rng)


def rates(C, names, cls, pooled, rng):
    """T2 "from the ranges" on the drawn cases: what share passes, by body."""
    col = {n: i for i, n in enumerate("k j month week geom design levelset heading tas_kn speed dir passes same_side air_min air_max "
                                      "slip_min slip_max dwr_min dwr_max side_right true_right samples".split())}
    k = C[:, col["k"]].astype(int)
    use = pooled[k]
    grp = k * 100 + C[:, col["week"]].astype(int)
    g, de, ls, sp, dr = (C[:, col[n]].astype(int) for n in ("geom", "design", "levelset", "speed", "dir"))
    ok = C[:, col["passes"]] > 0
    side = C[:, col["same_side"]] > 0
    one_sign = np.sign(C[:, col["dwr_min"]]) == np.sign(C[:, col["dwr_max"]])
    inr = (C[:, col["air_min"]] >= AIR_RANGE_KN[0]) & (C[:, col["air_max"]] <= AIR_RANGE_KN[1])

    def share(m, x=ok, n=200):
        if m.sum() == 0:
            return "-"
        b = boot(grp[m], lambda i, s=x[m]: np.mean(s[i]), rng, n)
        return f"{100 * x[m].mean():5.1f} ({100 * b[0]:.1f}-{100 * b[1]:.1f})"

    print("\n== B2. T2 'from the ranges' (drift.test_wind) on drawn cases; per cent passing, with the 16th-84th percentile of a bootstrap over station-weeks")
    for gi, gl in ((0, f"the clip's heights ({OBJ_M:g} and {AIR_M:g} m above the sea)"), (1, "the sounding's own 700- and 400-hPa levels")):
        print(f"\n  geometry: {gl}")
        base = use & (g == gi)
        print(f"   soundings: {len(np.unique(k[base] * 10000 + C[base, col['j']].astype(int)))} at {len(np.unique(k[base]))} stations")
        print("   a true drifter, by the winds given:   passes | the winds' difference lies the same way | every sample lies one way at all | "
              "the airspeed in 0-240 kn | the mirror passes (same case, sideways motion's sign turned)")
        for li, ll in enumerate(LEVELSETS):
            for di, dl in enumerate(DESIGNS):
                m = base & (ls == li) & (de == di) & (dr == -1)
                mm = base & (ls == li) & (de == di) & (dr == -2)
                if m.sum():
                    print(f"     {dl} ({int(np.median(C[m, col['samples']]))} winds), {ll:5s} levels: {share(m)} | {share(m, side, 50)} | {share(m, one_sign, 50)} | "
                          f"{share(m, inr, 50)} | {share(mm)}   (n {m.sum()})")
        for di, dl in ((0, "Y3: three cells, 24 hours (the Yemen run's shape)"), (2, "T3: the station's cell, three hours")):
            m0 = base & (ls == 0) & (de == di)
            print(f"   {dl}, the Yemen files' levels: per cent passing by airspeed through the air and its direction from the heading")
            print("        m/s |  " + "  ".join(f"{d:5d}" for d in DIRECTIONS) + "  | every direction")
            print(f"          0 |  {'':46s} | {share(m0 & (dr == -1))}")
            for s in SPEEDS:
                row = [100 * ok[m0 & (sp == int(s)) & (dr == d)].mean() for d in DIRECTIONS]
                print(f"       {s:4g} |  " + "  ".join(f"{x:5.1f}" for x in row) + f"  | {share(m0 & (sp == int(s)) & (dr >= 0))}")
        m0 = base & (ls == 0) & (de == 0)
        print("   Y3 by place class: a drifter / the mirror / 10 m/s / 25 m/s (every direction)")
        for c in sorted(set(cls)):
            mc = m0 & (cls[k] == c)
            if mc.sum():
                print(f"     {c:14s}: {share(mc & (dr == -1), n=50)} / {share(mc & (dr == -2), n=50)} / {share(mc & (sp == 10) & (dr >= 0), n=50)} / {share(mc & (sp == 25) & (dr >= 0), n=50)}")
        print("   Y3 by station: a drifter / the mirror / 10 m/s; soundings")
        for kk, sid in enumerate(names):
            mc = (g == gi) & (ls == 0) & (de == 0) & (k == kk)
            if mc.sum():
                print(f"     {sid} {cls[kk]:14s}: {100 * ok[mc & (dr == -1)].mean():5.1f} / {100 * ok[mc & (dr == -2)].mean():5.1f} / "
                      f"{100 * ok[mc & (sp == 10) & (dr >= 0)].mean():5.1f}   ({len(np.unique(C[mc, col['j']]))})")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if "--fetch" in sys.argv:
        fetch(Path(a[0]))
    w = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 18
    s = sys.argv[sys.argv.index("--src") + 1] if "--src" in sys.argv else None
    a = [x for x in a if x not in (str(w), s)]
    main(a[0], a[1], w, s)
