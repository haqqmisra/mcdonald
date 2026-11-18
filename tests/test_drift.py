"""Does `mcdonald drift` give each of its tests the outcome the evidence holds, and the verdict its rule says?

Synthetic cases first, each built so that its answer is known by construction (the three main tests, then the fourth,
other evidence; until 2026-10-28 the tracer and the remains were T1 and T2, the height, winds and beat T3-T5):
  T1  a body holding its height and one climbing faster than any balloon, read off stepped range readouts (0.1 NM,
      timed to the frame) as the display gives them
  T2  a straight line in space recovered from those readouts and the bearings; the winds' test, passed by a body that
      drifts and not by a drone flying across the heading; the winds read from an archive file, a level's missing
      height filled by the hypsometric equation; T1 and T2 from the aircraft's own track as it turns
  T3  the flicker stage's three answers, and the smallest beat a clip could have shown
  T4  other evidence. T4a, pieces shed by a body that floats and by one that flies, timed against the remains; a cloud
      the object is carried by, at its own depth and only within the layer, and one it moves through. T4b, remains
      sinking at a steady rate, and a wreck falling as a 5-m body falls, each read by the quadratic and by the track's
      own speed band; a drawn track with a slow wander, whose band's bound outreaches the bootstrap's error (the Yemen
      remains' case); the pass and fail thresholds. How the parts combine
Then the verdict's rule (a beat decides only where it holds across the video). Then the known answers. The
Hellfire/Yemen clip: its inputs, read off the display, are in tests/golden/hellfire_drift/, and every test runs as in
the case (every test from the inputs alone, and the command line on the clip when $MCDONALD_DATA holds it, else
skipped). AARO's Puerto Rico lanterns, a known drifter (tests/golden/puerto_rico_drift/: T1/T2 from the aircraft's own
track). Santa Barbara's Huey, a helicopter known to have hovered in calm air (tests/golden/santa_barbara_drift/: its
rotor's held beat fails T3). And PR051's second leg (tests/golden/pr051_drift/: a second display for the route from the
aircraft's own track, from an agent's readings of its data bar that no person has checked; no verdict is drawn).
Cameras on the ground (method section 66) are drawn only: lines of sight with their own time and camera from three
places, a drifter and a flier; one camera refused; each camera's own pointing error and scatter carried; the command
line with no video; and the aircraft's route untouched.

    python3 tests/test_drift.py        # or: pytest tests/

No video data needed but for the command-line runs on the three clips (the video gives the frame rate).
"""
import contextlib
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcdonald import drift  # noqa: E402
import reference_data  # noqa: E402

FAIL, SKIP = [], []
FPS = 30.0
NM_TENTH = 185.2                     # one step of a range readout, m
GOLDEN = reference_data.GOLDEN / "hellfire_drift"
CLIP = reference_data.root() / "hellfire_yemen" / "x_burlison_1965438792493355291.mp4"


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


@contextlib.contextmanager
def resamples(n):
    """`drift.fit_track` with n resamples wherever its caller names no count (the stage, `measure`, names none and so
    takes 2,000, about 6 s a fit). For a test that goes through the stage or the command's own `main` and whose checks
    do not turn on the count: the known answers, and the command-line runs on them, keep the 2,000."""
    real = drift.fit_track
    drift.fit_track = lambda *a, **k: real(*a, **dict(dict(nboot=n), **k))
    try:
        yield
    finally:
        drift.fit_track = real


# ---------------------------------------------------------------- scenes
def pieces_scene(v_px_s, noise=0.3, seed=1):
    """Remains sinking and drifting on the screen, and one piece leaving them at v_px_s (vx, vy)."""
    rng = np.random.default_rng(seed)
    n = np.arange(100, 200)
    t = (n - n[0]) / FPS
    rem = {int(f): (40 + 3 * s + rng.normal(0, noise), 60 + 5 * s + rng.normal(0, noise)) for f, s in zip(n, t)}
    piece = {int(f): (rem[int(f)][0] + v_px_s[0] * s + rng.normal(0, noise),
                      rem[int(f)][1] + v_px_s[1] * s + rng.normal(0, noise)) for f, s in zip(n, t)}
    return rem, piece


def readouts(values, frames):
    """A range readout in tenths of a nautical mile, as the drift stage reads one: the frame at which the true range
    first passes each step, and the step's value (frame error 1)."""
    out = []
    for k in range(int(values.min() // NM_TENTH) + 1, int(values.max() // NM_TENTH) + 1):
        b = k * NM_TENTH
        cross = np.nonzero(np.diff(np.sign(values - b)))[0]
        if len(cross):
            out.append((frames[cross[0] + 1], b))
    out.sort()
    return (np.array([f for f, _ in out], float), np.array([b for _, b in out]), np.ones(len(out)))


def flight(climb_m_s=0.0, v=(-67.0, 75.0), seconds=15.0, b0_deg=105.0, g0=5200.0, dh0=3800.0, seed=2):
    """The object relative to the aircraft on a straight line in space (east, north, up), seen for `seconds`: the slant
    and horizontal readouts, the bearings every 5 frames (0.05 deg noise), and the aircraft's own height readings."""
    rng = np.random.default_rng(seed)
    frames = np.arange(1, int(seconds * FPS) + 1)
    t = (frames - 1) / FPS
    b0 = math.radians(b0_deg)
    x = g0 * math.sin(b0) + v[0] * t
    y = g0 * math.cos(b0) + v[1] * t
    z = -dh0 + climb_m_s * t
    S, G = np.sqrt(x ** 2 + y ** 2 + z ** 2), np.hypot(x, y)
    bf = frames[::5]
    B = (np.degrees(np.arctan2(x, y))[::5] + rng.normal(0, 0.05, len(bf))) % 360
    own_f = np.array([1, 100, 200, 300, 400], float)
    return dict(slant=readouts(S, frames), horiz=readouts(G, frames), bearings=(bf.astype(float), B, np.full(len(bf), 0.05)),
                own=(own_f, np.full(len(own_f), 7500.0), np.full(len(own_f), 12.0)), v=v, climb=climb_m_s)


# ---------------------------------------------------------------- T1
def test_t1_height_from_stepped_readouts():
    print("\nT1: the height, from the readouts")
    hold = flight()
    out, delta = drift.test_vertical(hold["slant"], hold["horiz"], hold["own"], FPS)
    check(len(hold["horiz"][0]) >= 3 and len(hold["slant"][0]) >= 3, "the scene gives three readings of each or more",
          f"{len(hold['slant'][0])} slant, {len(hold['horiz'][0])} horizontal")
    check(out["outcome"] == drift.PASS and abs(out["climb_m_s"]) < 2 * out["climb_err_m_s"] + 0.5,
          "a body holding its height holds it, to its error: passes", f"{out['climb_m_s']} +- {out['climb_err_m_s']} m/s")
    check(abs(out["height_below_m"] - 3800) < 15, "the height difference is the scene's", f"{out['height_below_m']} m")
    truth = math.degrees(math.asin(3800 / math.hypot(3800, np.hypot(5200 * math.sin(math.radians(105)) - 67 * 15,
                                                                         5200 * math.cos(math.radians(105)) + 75 * 15))))
    check(delta is not None and abs(delta - truth) < 0.5, "and the depression at the end", f"{delta:.2f} of {truth:.2f} deg")
    up = flight(climb_m_s=12.0)
    out, _ = drift.test_vertical(up["slant"], up["horiz"], up["own"], FPS)
    check(out["outcome"] == drift.FAIL and abs(out["climb_m_s"] - 12.0) < 1.5,
          "a body climbing at 12 m/s, faster than any balloon: fails", f"{out['climb_m_s']} +- {out['climb_err_m_s']} m/s")
    out, d = drift.test_vertical(None, None)
    check(out["outcome"] == drift.CANNOT and d is None, "no ranges: cannot say")


# ---------------------------------------------------------------- T2
def test_t2_the_line_in_space_is_recovered():
    print("\nT2: the straight line, from ranges and bearings")
    sc = flight()
    line = drift.fit_line(sc["slant"], sc["horiz"], sc["bearings"], FPS, np.random.default_rng(0))
    v = np.array(line["v_m_s"][:2])
    check(np.all(np.abs(v - np.array(sc["v"])) < 3.0), "its velocity against the aircraft, within 3 m/s",
          f"{v.round(1).tolist()} of {list(sc['v'])}")
    check(abs(line["speed_m_s"] - math.hypot(*sc["v"])) < 2.0 and line["speed_err_m_s"] is not None,
          "its speed, with a bootstrap error", f"{line['speed_m_s']:.1f} +- {line['speed_err_m_s']:.2f} m/s")


def winds_of(w_obj, w_air, n=6, spread=1.0, seed=4):
    rng = np.random.default_rng(seed)
    return [dict(w_obj=np.array(w_obj) + rng.normal(0, spread, 2), w_air=np.array(w_air) + rng.normal(0, spread, 2))
            for _ in range(n)]


def line_of(v):
    return dict(v_m_s=list(v) + [0.0], speed_m_s=float(np.hypot(*v)), toward_deg=float(np.degrees(np.arctan2(*v)) % 360),
                range_rms_m=1.0)


def test_t2_a_drifting_body_fits_the_winds_and_a_crossing_drone_does_not():
    """T2 from the ranges, the rule since 2026-11-17 (the maintainer's choice of the rule drafted and scored in method
    section 68). It passes where the nearest sample's shortfall across the heading is within two errors of the fit plus
    `WIND_DIFF_ERR` (4.8 m/s: what a model's error on the difference of the winds at two heights stays under nine times
    in ten), fails where even the nearest leaves the body a flier's 10 m/s beyond that, and cannot say between. Until
    then it read a side and no size: it passed where every sample lay on the measured motion's side of the heading,
    could not say otherwise, and never failed. So the drone crossing at 25 m/s, which could not be said, now fails;
    a body crossing at 4 m/s passes as a drifter does, which is why this route's pass is no strong test; and winds
    that straddle the heading no longer stop a pass."""
    print("\nT2: the winds")
    air, w_air, w_obj = 90.0, np.array([10.0, 0.0]), np.array([0.0, 8.0])      # heading east; the object drifts north
    ground = air * np.array([1.0, 0.0]) + w_air
    out = drift.test_wind(line_of(w_obj - ground), 90.0, winds_of(w_obj, w_air), air_min_kn=0, air_max_kn=240)
    check(out["outcome"] == drift.PASS and abs(np.mean(out["airspeed_kn"]) - air / drift.KN) < 10 and out["source"] == "ranges"
          and out["tolerance_m_s"] == drift.WIND_DIFF_ERR == 4.8 and out["shortfall_m_s"][0] < 2.0 and "not a strong test" in out["reading"],
          "a body drifting with the winds: the airspeed it needs is the aircraft's and the nearest sample is within a "
          "model's own error of its sideways motion, passes; the reading says the pass is not a strong one",
          f"{out['airspeed_kn']} kn of {air / drift.KN:.0f}; {out['shortfall_m_s'][0]} m/s short of {out['tolerance_m_s']}")
    drone = w_obj + 25.0 * np.array([0.0, -1.0])                                  # flying south across the heading
    out = drift.test_wind(line_of(drone - ground), 90.0, winds_of(w_obj, w_air), air_min_kn=0, air_max_kn=240)
    check(out["outcome"] == drift.FAIL and not out["same_side"] and 22 < out["shortfall_m_s"][0] < 28 and "it flies" in out["reading"],
          "a drone crossing the heading at 25 m/s: even the nearest sample leaves it over 10 m/s beyond the tolerance, "
          "fails (cannot say until 2026-11-17, when the test never failed)", out["reading"][:150])
    check(out["drones"]["25 m/s"]["flying_its_way_kn"] is not None, "and the airspeeds a 25-m/s drone would need are given")
    exact = [dict(w_obj=w_obj, w_air=w_air, file="cell", time="2024-10-30T05:00")]       # one sample: the edges to the digit

    def crossing(u, **kw):                                         # a body flying u m/s to the left of the heading (north)
        return drift.test_wind(dict(line_of(w_obj + u * np.array([0.0, 1.0]) - ground), **kw), 90.0, exact, air_min_kn=0, air_max_kn=240)
    edges = [crossing(u)["outcome"] for u in (4.79, 4.81, 14.79, 14.81)]
    check(edges == [drift.PASS, drift.CANNOT, drift.CANNOT, drift.FAIL],
          "the edges, with one sample and a fit taken as exact: 4.8 m/s across the heading passes, 14.8 fails, between "
          "the two it cannot say", ", ".join(edges))
    slow, mid = crossing(4.0), crossing(10.0)
    check(slow["outcome"] == drift.PASS and mid["outcome"] == drift.CANNOT and "not beyond them by a flier's 10 m/s" in mid["reading"]
          and slow["nearest_sample"] == dict(file="cell", time="2024-10-30T05:00") and slow["samples"] == 1
          and "the winds' difference is 16 kn to the left" in mid["reading"] and "The one hour and place given leaves it" in mid["reading"],
          "a body flying 4 m/s across the heading passes as a drifter does (the route's pass is not a strong test); at "
          "10 m/s it cannot say, and says by how much", mid["reading"][:160])
    wide = crossing(10.0, v_err_m_s=[1.0, 3.0, 0.0])            # heading east: the error across it is the north one's
    check(wide["outcome"] == drift.PASS and wide["fit_err_across_m_s"] == 3.0 and wide["tolerance_m_s"] == 10.8,
          "the fit's own error across the heading is in the tolerance, twice over: 3 m/s of it, and 10 m/s across passes",
          f"tolerance {wide['tolerance_m_s']} m/s")
    both = [dict(w_obj=np.array([0.0, d]), w_air=np.zeros(2)) for d in (3.0, -3.0)]      # 3 m/s to the left, and to the right
    lone = drift.test_wind(line_of(np.array([0.0, 1.0]) - air * np.array([1.0, 0.0])), 90.0, both, air_min_kn=0, air_max_kn=240)
    check(lone["outcome"] == drift.PASS and not lone["same_side"] and lone["wind_difference_right_kn"][0] < 0 < lone["wind_difference_right_kn"][1]
          and lone["shortfall_m_s"] == [2.0, 4.0] and "between 6 kn to the left and 6 kn to the right" in lone["reading"],
          "samples whose difference straddles the heading no longer stop a pass (they did until 2026-11-17): the nearest "
          "one is asked, and `same_side` is still recorded", f"{lone['wind_difference_right_kn']} kn, same_side {lone['same_side']}")
    out = drift.test_wind(line_of(w_obj - ground), 90.0, winds_of(w_obj, w_air), air_min_kn=0, air_max_kn=120)
    check(out["outcome"] == drift.CANNOT and "outside the aircraft's range" in out["reading"] and out["airspeed_in_range"] is False,
          "an airspeed beyond the aircraft's range: cannot say, though the sideways motion fits")
    V = drift.verdict
    t2 = drift.test_wind(line_of(w_obj - ground), 90.0, winds_of(w_obj, w_air), air_min_kn=0, air_max_kn=240)
    v, why = V([t2])
    check(v == "cannot say" and "no strong test (T2 from lines of sight, or T4a" in why and "T2 passed from the ranges" in why
          and not drift.strong(t2) and drift.strong(dict(t2, source="lines of sight")),
          "a pass of T2 from the ranges does not carry the verdict (it did until 2026-11-17): cannot say, and the reason "
          "says that it passed and why that is not enough", why)


def test_t2_winds_from_an_archive_file():
    print("\nT2: the archive's winds")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "w.json"
        p.write_text(json.dumps({"hourly": {
            "time": ["2024-10-30T00:00", "2024-10-30T01:00"],
            "wind_speed_700hPa": [10.0, 12.0], "wind_direction_700hPa": [270.0, 270.0],
            "wind_speed_400hPa": [30.0, 30.0], "wind_direction_400hPa": [0.0, 0.0],
            "geopotential_height_400hPa": [7500.0, 7500.0]}}), encoding="utf-8")
        z700 = 7500.0 - 287.05 * drift.T_LAYER / 9.80665 * math.log(700 / 400)
        s = drift.wind_samples([p], z700, 7500.0)
    check(len(s) == 2, "an hour's winds per sample", f"{len(s)}")
    check(np.allclose(s[0]["w_obj"], [10 * drift.KN, 0.0], atol=1e-6),
          "a level with no height placed by the hypsometric equation: its wind at that height (from the west, 10 kn)",
          f"{np.round(s[0]['w_obj'], 3).tolist()}")
    check(np.allclose(s[0]["w_air"], [0.0, -30 * drift.KN], atol=1e-6), "the upper level's (from the north, 30 kn)",
          f"{np.round(s[0]['w_air'], 3).tolist()}")


def drawn_station(folder, sid="XXM00000001", off_400=(0.0, 0.0)):
    """A drawn radiosonde station for tools/wind_model_igra.py: one sounding in IGRA v2's columns whose wind is
    (2 + z / 500, -3 + z / 1000) m/s at height z, two of its wind levels given by pressure alone; and a month of model
    files at three cells that hold the same wind at every level and hour, but for `off_400` (m/s, east and north)
    added at 400 hPa. Returns the station's entry."""
    import zipfile

    def wind(z):
        return np.array([2.0 + z / 500.0, -3.0 + z / 1000.0])

    def height(p):                                                    # an isothermal air at 280 K, 1013 hPa at the sea
        return 287.05 * 280.0 / 9.80665 * math.log(1013.0 / p)

    def row(p, with_height=True, surface=False):                      # IGRA's fixed columns: pressure in Pa, tenths of a m/s
        z = height(p)
        u, v = wind(10.0 if surface else z)
        gph = f"{round(z):5d}" if with_height else "-9999"
        return (f"{'21' if surface else '10'} -9999 {round(p * 100):6d} {gph} -9999 -9999 -9999 "
                f"{round(math.degrees(math.atan2(-u, -v)) % 360):5d} {round(math.hypot(u, v) * 10):5d}")

    levels = [1013, 925, 850, 800, 760, 700, 660, 620, 600, 560, 520, 500, 460, 430, 400, 370, 340, 300, 250, 200]
    lines = [f"#{sid} 2026 01 01 12 1130 {len(levels):4d} drawn    drawn     150000   450000"]
    lines += [row(p, with_height=p not in (660, 430), surface=p == 1013) for p in levels]
    (folder / "igra").mkdir(exist_ok=True)
    (folder / "model").mkdir(exist_ok=True)
    with zipfile.ZipFile(folder / "igra" / f"{sid}-data-beg2026.txt.zip", "w") as z:
        z.writestr(f"{sid}-data.txt", "\n".join(lines) + "\n")
    times = [f"2026-01-{d:02d}T{h:02d}:00" for d in (1, 2) for h in range(24)]
    hourly = dict(time=times)
    for p in (1000, 925, 850, 800, 700, 600, 500, 400, 300, 250, 200):
        u, v = wind(height(p)) + (np.array(off_400) if p == 400 else 0.0)
        hourly[f"wind_speed_{p}hPa"] = [math.hypot(u, v) / drift.KN] * len(times)
        hourly[f"wind_direction_{p}hPa"] = [math.degrees(math.atan2(-u, -v)) % 360] * len(times)
        hourly[f"geopotential_height_{p}hPa"] = [height(p)] * len(times)
    for cell in "cwe":
        (folder / "model" / f"{sid}_{cell}_2026-01.json").write_text(json.dumps(dict(elevation=0.0, hourly=hourly)))
    return dict(cls="drawn", lat=15.0, lon=45.0, elev=0.0)


def test_t2_from_the_ranges_against_soundings():
    """Method section 68 (2026-11-17). T2 "from the ranges" compares the measured sideways motion with the model winds'
    difference between the object's height and the aircraft's. What that is worth was measured with radiosondes as the
    truth and the model as the test's input (tools/wind_model_igra.py): the rule it had then, which read a side and no
    size, passed a true drifter 27 times in 100 and a body flying 50 m/s 12. The maintainer chose the rule the note
    drafted (the nearest sample's shortfall against two errors of the fit and a model's own error on the difference,
    `WIND_DIFF_ERR`), and that it is no strong test. Here the tool is held on a drawn station whose answer is known,
    under the rule as built and, from the fields the test still records, under the rule before; the table it made on
    the real soundings is held to the numbers the method note quotes; and the built rule's scores on the stations its
    allowance was not set on are held to the draft's (tests/golden/wind_model_t2_ranges.csv)."""
    print("\nT2 from the ranges against soundings: the tool on a drawn station, and its table")
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
    import wind_model_igra as tool
    c = {n: i for i, n in enumerate(tool.COLUMNS.split())}
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        st = drawn_station(td)
        snd = list(tool.soundings(td / "igra" / "XXM00000001-data-beg2026.txt.zip", st["elev"]))
        z660 = 287.05 * 280.0 / 9.80665 * math.log(1013.0 / 660.0)
        check(len(snd) == 1 and len(snd[0]["z"]) == 20 and np.min(np.abs(snd[0]["z"] - z660)) < 2.0,
              "the reader: one sounding of 20 wind levels, a level given by pressure alone placed by ln(p) between its "
              "neighbours", f"{np.min(np.abs(snd[0]['z'] - z660)):.2f} m from its true height")
        w = tool.sonde_at(snd[0], tool.OBJ_M, st["elev"])
        check(w is not None and np.allclose(w, [2 + tool.OBJ_M / 500, -3 + tool.OBJ_M / 1000], atol=0.25)
              and tool.sonde_at(snd[0], 13000.0, st["elev"]) is None,
              "the sounding's wind at the object's height, between its levels; none above its top level",
              f"{np.round(w, 2).tolist()}")
        res = tool.station((str(td), 0, "XXM00000001", st, None))
        err = np.array(res["err"])
        dif = [r for r in res["dif"] if r[6] == "all"]
        check(len(err) == 2 * len(tool.HEIGHTS) and np.abs(err[:, 6:8]).max() < 0.25 and len(dif) > 10
              and max(math.hypot(r[8], r[9]) for r in dif) < 0.4,
              "a model that holds the sounding's own winds: no error at any height, at the hour or the hour before, nor in "
              "the difference between two heights (but IGRA's rounding)", f"{np.abs(err[:, 6:8]).max():.2f} m/s")
        C = res["cases"]
        main = (C[:, c["geom"]] == 0) & (C[:, c["design"]] == 0) & (C[:, c["levelset"]] == 0)
        drifter, mirror = main & (C[:, c["dir"]] == -1), main & (C[:, c["dir"]] == -2)
        ok, bad, was = C[:, c["passes"]], C[:, c["fails"]], C[:, c["passes_before"]]
        true_ms = np.abs(C[:, c["true_right"]]) * drift.KN            # the winds' true difference across the heading
        at = lambda speed, a: main & (C[:, c["speed"]] == speed) & (C[:, c["dir"]] == a)     # noqa: E731
        check(res["checked"] == 1 and drifter.sum() == tool.HEADINGS and ok[drifter].sum() == tool.HEADINGS and bad[drifter].sum() == 0,
              "drawn cases through drift.test_wind, three cells and 24 hours as the Yemen run had (the samples the same as "
              "drift.wind_samples'): where the model holds the true winds a drifter passes on every heading",
              f"{int(ok[drifter].sum())} of {tool.HEADINGS}")
        near, far = mirror & (2 * true_ms < 3.0), mirror & (2 * true_ms > 8.5)
        check(near.sum() >= 1 and far.sum() >= 3 and ok[near].all() and not ok[far].any() and was[mirror].sum() <= 2,
              "the same case with its sideways motion's sign turned is twice the winds' difference off: it passes where "
              "that is under 3 m/s and not where it is over 8.5 (the rule reads a size; the rule before, which read "
              "the side, passed it on nearly no heading)",
              f"passes {int(ok[mirror].sum())} of {tool.HEADINGS}, {int(ok[near].sum())} of the {int(near.sum())} near and "
              f"{int(ok[far].sum())} of the {int(far.sum())} far; the rule before {int(was[mirror].sum())}")
        check(all(bad[at(v, a)].sum() == tool.HEADINGS for v in (25, 50) for a in (90, 270))
              and np.all(was[at(50, 90)] + was[at(50, 270)] == 1),
              "a body crossing the heading at 25 or 50 m/s fails either way, on every heading; by the rule before it "
              "passed one way and not the other (a side, not a size), and the tool still gives that rule's answer")
        check(all(ok[at(10, a)].sum() == 0 and bad[at(10, a)].sum() == 0 for a in (90, 270))
              and all(ok[at(5, a)].sum() >= tool.HEADINGS - 3 for a in (90, 270)),
              "crossing at 10 m/s it cannot be said, on every heading; crossing at 5 m/s it passes as a drifter does, on "
              "nearly every one: the pass is not a strong test",
              f"at 5 m/s {int(ok[at(5, 90)].sum())} and {int(ok[at(5, 270)].sum())} of {tool.HEADINGS}")
        along, back = at(50, 0), at(50, 180)
        fast = C[back, c["tas_kn"]] > 150.0
        check(np.array_equal(ok[along], ok[drifter]) and fast.sum() > 0 and not ok[back][fast].any() and not bad[back].any()
              and not was[back][fast].any() and was[along].sum() >= tool.HEADINGS - 2,
              "a body flying 50 m/s along the heading passes wherever the drifter does (nothing of it shows across the "
              "heading, and 0-240 kn takes it in); flying the other way from an aircraft over 150 kn it cannot be said, "
              "the airspeed it implies being out of the range, and it does not fail; nor did it pass by the rule before, "
              "whose answer the tool keeps with the airspeed's range in it")
        st = drawn_station(td, off_400=(4.0, 0.0))
        res = tool.station((str(td), 0, "XXM00000001", st, None))
        pair = [r for r in res["dif"] if r[5] == "L700-400" and r[6] == "all" and r[4] == 0]
        top = [r for r in res["err"] if r[5] == 7500 and r[4] == 0]
        check(len(pair) == 1 and abs(pair[0][8] - 4.0) < 0.4 and abs(pair[0][9]) < 0.4 and len(top) == 1 and 3.0 < top[0][6] < 4.2,
              "the model's 400-hPa wind 4 m/s off to the east: the 700-400 hPa difference errs by 4 m/s east, the wind at "
              "7.5 km by nearly as much", f"{pair[0][8]:.2f} and {top[0][6]:.2f} m/s" if pair and top else "")
    # the table the tool made on the real soundings (7,688 of 17 stations, 2026), held to what the method note quotes
    rows = drift.read_rows(reference_data.GOLDEN / "wind_model_soundings.csv")

    def row(kind, lag, levels, low, high=None):
        r = [x for x in rows if (x["kind"], x["lag_h"], x["levels"], x["low_m"], x["high_m"]) == (kind, str(lag), levels, str(low), str(high or low))]
        return {k: float(v) for k, v in r[0].items() if k not in ("kind", "levels") and v != ""} if len(r) == 1 else None

    bands = [row("wind", -1, "all", 1000, 3000), row("wind", -1, "all", 3000, 6000)]
    check(all(b and 1.9 < b["p50"] < 2.4 and 4.0 < b["p90"] < 4.9 and 0.65 < b["under_3"] < 0.78
              and abs(b["p50"] - drift.MODEL_WIND_ERR) < 0.3 for b in bands),
          "a model's wind against a balloon, 1-6 km above the station at the hour before the sounding: about 2.1 m/s off "
          "(median), 4.3-4.6 at the 90th percentile; MODEL_WIND_ERR, 2 m/s since 2026-11-17 (3 before), is that median "
          "miss as a vector (and what a balloon needs beyond the hours' spread and the fit's errors 91 times in 100)",
          ", ".join(f"{b['p50']} / {b['p90']} / {b['under_3']}" for b in bands if b))
    clip = row("difference", -1, "yemen", 3793)
    least, largest = 5.2 * drift.KN, 18.4 * drift.KN                 # the Yemen clip's T2: its shortfall across the heading
    check(clip and 2.7 < clip["across_sd"] < 3.3 and 4.5 < clip["across_p90"] < 5.1 and least < clip["across_sd"]
          and largest > clip["across_p95"],
          "the model's wind DIFFERENCE between the Yemen clip's two heights, across a heading: one standard deviation 3.0 "
          "m/s, 4.8 nine times in ten; the clip's least shortfall (2.7 m/s) is inside one, its largest (9.5) beyond 95 in 100",
          f"sd {clip['across_sd']}, 90th {clip['across_p90']}, 95th {clip['across_p95']} m/s" if clip else "")
    was_set, held = row("difference_set", -1, "yemen", 3793), row("difference_held", -1, "yemen", 3793)
    check(was_set and held and abs(was_set["across_p90"] - drift.WIND_DIFF_ERR) < 0.06 and abs(held["across_p90"] - drift.WIND_DIFF_ERR) < 0.15
          and was_set["soundings"] > 3000 and held["soundings"] > 3000 and held["across_p95"] > drift.WIND_DIFF_ERR + 0.8,
          "WIND_DIFF_ERR (4.8 m/s) is the size that error stays under nine times in ten on the even-numbered stations "
          "(4.84), and on the odd-numbered, which it was not set on, the 90th percentile is 4.77",
          f"{was_set['across_p90']} on {was_set['soundings']:.0f} soundings, {held['across_p90']} on {held['soundings']:.0f}" if was_set and held else "")
    # the rule as built, scored by the tool on the stations its allowance was not set on (the odd-numbered)
    scored = drift.read_rows(reference_data.GOLDEN / "wind_model_t2_ranges.csv")

    def rate(winds, body, stations="odd", geometry="clip"):
        r = [x for x in scored if (x["stations"], x["geometry"], x["winds"], x["body"]) == (stations, geometry, winds, str(body))]
        return {k: float(v) for k, v in r[0].items() if k in ("cases", "passes", "cannot_say", "fails", "tolerance")} if len(r) == 1 else None

    y = {b: rate("Y3", b) for b in (0, "mirror", 5, 10, 25, 50)}
    check(all(y.values()) and y[0]["cases"] > 40000 and 96.0 <= y[0]["passes"] <= 97.6 and y[0]["fails"] <= 0.02
          and 5.4 < y[0]["tolerance"] < 6.7,
          "three cells and 24 hours, as the Yemen run had: a true drifter passes 96.8 times in 100 (the draft's score: "
          "96.9) and fails under 2 in 10,000", f"{y[0]['passes']} % of {y[0]['cases']:.0f}, fails {y[0]['fails']} %" if y[0] else "")
    check(all(y.values()) and 93.5 <= y[5]["passes"] <= 96 and 81 <= y[10]["passes"] <= 85.5 and 28 <= y[25]["passes"] <= 32
          and 12.5 <= y[50]["passes"] <= 15 and y[5]["fails"] < 0.1 and y[10]["fails"] < 0.2 and 20 <= y[25]["fails"] <= 25
          and 70 <= y[50]["fails"] <= 74,
          "bodies flying 5, 10, 25 and 50 m/s through the air pass 95, 83, 30 and 14 times in 100 and fail 0, 0, 23 and "
          "72 (the draft's: 95, 84, 30, 14; 22, 72): no strong test, since a slow flier passes nearly as often as a drifter",
          "; ".join(f"{b}: {y[b]['passes']} / {y[b]['fails']}" for b in (5, 10, 25, 50)) if all(y.values()) else "")
    t = {b: rate("T3", b) for b in (0, 5, 10, 25, 50)}
    check(all(t.values()) and 97.8 <= t[0]["passes"] <= 99.3 and t[0]["fails"] <= 0.02 and 88 <= t[5]["passes"] <= 92
          and 48 <= t[10]["passes"] <= 54 and 20 <= t[25]["passes"] <= 22 and 52 <= t[25]["fails"] <= 58 and 73 <= t[50]["fails"] <= 77,
          "with one cell and three hours a drifter passes 98.5 (the draft's: 98.8), 10 m/s passes half the time, and 25 "
          "and 50 m/s fail 56 and 75 times in 100", "; ".join(f"{b}: {t[b]['passes']} / {t[b]['fails']}" for b in t) if all(t.values()) else "")
    same = [abs(rate(w, b, "even")["passes"] - rate(w, b)["passes"]) for w in ("Y3", "T3") for b in (0, 5, 10, 25, 50)]
    other = [abs(rate(w, b, geometry="levels")["passes"] - rate(w, b)["passes"]) for w in ("Y3", "T3") for b in (0, 5, 10, 25, 50)]
    check(max(same) < 0.5 and max(other) < 2.5 and y["mirror"]["passes"] < y[0]["passes"] - 25 and y["mirror"]["fails"] > 5,
          "the stations the allowance was set on score the same within half a point (nothing was fitted to them but one "
          "percentile), and the soundings' own 700- and 400-hPa levels within 2.5; the same cases with the sideways "
          "motion's sign turned pass far less often and fail one time in nine",
          f"largest difference {max(same):.1f} and {max(other):.1f} points; the mirror {y['mirror']['passes']} / {y['mirror']['fails']}")
    grow = [row("difference", -1, "all", dz) for dz in (1000, 2000, 3000, 3793, 5000, 6000)]
    one = bands[1]["p50"] if bands[1] else float("nan")
    check(all(grow) and max(g["p50"] for g in grow) / min(g["p50"] for g in grow) < 1.25
          and all(1.25 < g["p50"] / one < 1.65 for g in grow) and row("difference", -1, "all", 500)["p50"] < grow[0]["p50"],
          "that error stops growing past 1 km of separation, at about the square root of two times one wind's error: the "
          "model's errors at two heights a kilometre or more apart are nearly independent",
          ", ".join(f"{g['p50'] / one:.2f}" for g in grow if g))
    pairs = [(row(k, 0, lv, lo, hi), row(k, -1, lv, lo, hi)) for k, lv, lo, hi in
             (("wind", "all", 3000, 6000), ("difference", "yemen", 3793, None), ("difference_levels", "all", 700, 400))]
    out = (row("wind_left_out", -1, "all", 0, 10000), row("wind", -1, "all", 0, 10000))
    check(all(a and b and a["p50"] < b["p50"] and a["p90"] < b["p90"] for a, b in pairs) and out[0]["p95"] > 2.5 * out[1]["p95"],
          "at the sounding's own hour the model is nearer the balloon than an hour before (it has just been given the "
          "sounding); the station left out of the pooled rows has a tail the others do not",
          f"{pairs[1][0]['p50']} against {pairs[1][1]['p50']} m/s; 95th pct {out[0]['p95']} against {out[1]['p95']}")


# ---------------------------------------------------------------- T1/T2 from the aircraft's own track
def orbit(v_obj=(-6.0, -3.5), climb=-0.5, h_obj=250.0, turn=True, w_air=(-9.0, -3.0), seconds=95.0, every=2.5,
          noise=(0.1, 0.03), seed=5, lat0=18.5, lon0=-67.13):
    """An aircraft at 100 m/s through the air, turning 1.65 deg/s (or flying straight), in a wind w_air, climbing from
    520 m; an object on a straight path at v_obj (east, north, m/s) and `climb` about h_obj; the line of sight every
    `every` s as an azimuth and a depression with `noise` (deg). Returns (platform, los, truth)."""
    rng = np.random.default_rng(seed)
    plane = drift.Plane(lat0, lon0)
    tt = np.arange(0.0, seconds + 1e-9, 0.05)
    hd = np.radians(310.0 - 1.65 * tt) if turn else np.radians(np.full_like(tt, 250.0))
    E = 2600.0 + np.concatenate([[0.0], np.cumsum((100.0 * np.sin(hd[:-1]) + w_air[0]) * 0.05)])
    N = 2900.0 + np.concatenate([[0.0], np.cumsum((100.0 * np.cos(hd[:-1]) + w_air[1]) * 0.05)])
    platform, los = {}, {}
    tm = seconds / 2
    for t in np.arange(0.0, seconds + 1e-9, every):
        i = int(round(t / 0.05))
        f = int(round(t * FPS)) + 1
        la, lo = plane.latlon(E[i], N[i])
        alt = 520.0 + 2.7 * t
        platform[f] = (float(la), float(lo), alt, float(np.degrees(hd[i]) % 360))
        ola, olo = plane.latlon(v_obj[0] * t, 600.0 + v_obj[1] * t)
        d = drift.enu_rows(float(la), float(lo)) @ (drift.ecef(ola, olo, h_obj + climb * (t - tm))
                                                    - drift.ecef(float(la), float(lo), alt))
        los[f] = dict(az=float(np.degrees(np.arctan2(d[0], d[1])) % 360 + rng.normal(0, noise[0])),
                      dep=float(np.degrees(np.arctan2(-d[2], np.hypot(d[0], d[1]))) + rng.normal(0, noise[1])),
                      tgt=None, off=(0.0, 0.0))
    return platform, los, dict(v=np.array(v_obj), climb=climb, h=h_obj, w_air=np.array(w_air))


def test_track_the_path_from_the_lines_of_sight():
    print("\nT1/T2 from the aircraft's own track: the path")
    platform, los, truth = orbit()
    R = drift.rays(platform, los, FPS)
    p = drift.fit_track(R, (0.1, 0.03), ground_m=70.0, nboot=200)
    v = np.array(p["v_m_s"])
    check(np.all(np.abs(v - truth["v"]) < 0.4) and p["velocity_err_m_s"] < 0.5,
          "an orbit fixes the object's velocity over the ground", f"{v.round(2).tolist()} of {truth['v'].tolist()}, "
          f"error {p['velocity_err_m_s']:.2f}")
    check(abs(p["height_m"] - truth["h"]) < 10 and abs(p["climb_m_s"] - truth["climb"]) < 0.15,
          "and its height and climb", f"{p['height_m']:.0f} m, {p['climb_m_s']:+.2f} m/s")
    check(abs(p["above_ground_m"] - (truth["h"] - 70.0)) < 10 and p["los_turn_deg"] > 100,
          "height above the ground given; the line of sight turns", f"{p['above_ground_m']:.0f} m, {p['los_turn_deg']:.0f} deg")
    t1 = drift.test_vertical_track(p)
    check(t1["outcome"] == drift.PASS, "T1: a slow sink holds its height, passes", t1["reading"])
    own = drift.aircraft_wind(platform, FPS)
    check(own is not None and np.all(np.abs(own["w"] - truth["w_air"]) < 0.3) and abs(own["airspeed_m_s"] - 100) < 1,
          "the aircraft's own wind and airspeed, from its turn", f"{np.round(own['w'], 2).tolist()} of "
          f"{truth['w_air'].tolist()}, {own['airspeed_m_s']:.1f} m/s")
    tgt = {}
    for f, L in los.items():                                     # the same rays, as the ground points a display prints
        la, lo, alt, _ = platform[f]
        a, e = math.radians(L["az"]), math.radians(L["dep"])
        u = drift.enu_rows(la, lo).T @ np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), -math.sin(e)])
        x = drift.ecef(la, lo, alt) + (alt - 70.0) / math.sin(e) * u
        g = drift._geodetic(x)
        tgt[f] = dict(az=None, dep=None, tgt=g, off=(0.0, 0.0))
    p2 = drift.fit_track(drift.rays(platform, tgt, FPS), (0.1, 0.03), nboot=20)
    check(np.all(np.abs(np.array(p2["v_m_s"]) - v) < 0.05), "the same rays given as ground points: the same path",
          f"{np.round(p2['v_m_s'], 3).tolist()}")
    sp, sl, _ = orbit(turn=False)
    ps = drift.fit_track(drift.rays(sp, sl, FPS), (0.1, 0.03), nboot=200)
    t2 = drift.test_wind_track(ps, [dict(label="w", w=truth["v"], counts=True, note="")])
    check(t2["outcome"] == drift.CANNOT, "a straight-flying aircraft cannot range what it sees: cannot say",
          t2["reading"][:90])


def test_track_errors_from_the_rays_own_scatter():
    """DR3 (IDEAS.md; 2026-11-13). The covariance was scaled up by the rays' misfit and never down, so rays that fit far
    better than the errors given for them (`--los-sigma`, 0.3 and 0.1 deg by default) were judged at those: PR051's 23
    rays scatter by 0.017 and 0.003 deg, and its climb read +0.08 +- 2.74 m/s where their own scatter gives 0.16. Rays
    drawn with a known scatter and fitted with errors given three times too wide must come back with the scatter they
    were drawn with, and with errors that hold the truth as often as two errors should."""
    print("\nT1/T2 from the aircraft's own track: errors from the rays' own scatter where they fit better than the errors given")
    drawn = (0.09, 0.03)                         # azimuth to depression as the default errors weigh them, 3 to 1
    platform, los, truth = orbit(noise=drawn)
    R = drift.rays(platform, los, FPS)
    told = drift.fit_track(R, drawn, nboot=0)
    wide = drift.fit_track(R, (0.3, 0.1), nboot=0)
    check(told["errors_from"] == "the errors given" and told["chi2_p_low"] > drift.OWN_P and told["sigma_deg"] == list(drawn),
          "rays fitted with the scatter they were drawn with: the errors given stand",
          f"reduced chi-square {told['chi2_dof']:.2f}, lower tail {told['chi2_p_low']:.2f}")
    check(wide["errors_from"] == "the rays' own scatter" and wide["chi2_p_low"] < 1e-6
          and all(0.75 < s / d < 1.35 for s, d in zip(wide["sigma_deg"], drawn)),
          "the same rays with errors given three times too wide: the rays' own scatter takes their place, and it is the "
          "scatter they were drawn with", f"{wide['sigma_deg'][0]:.3f} and {wide['sigma_deg'][1]:.3f} deg of {drawn}")
    check(0.7 < wide["velocity_err_rays_m_s"] / told["velocity_err_rays_m_s"] < 1.4
          and 0.7 < wide["climb_err_rays_m_s"] / told["climb_err_rays_m_s"] < 1.4,
          "and the path's errors from the rays' scatter are those of the right errors given, not three times them",
          f"velocity {wide['velocity_err_rays_m_s']:.3f} against {told['velocity_err_rays_m_s']:.3f} m/s, climb "
          f"{wide['climb_err_rays_m_s']:.3f} against {told['climb_err_rays_m_s']:.3f}")
    check(np.allclose(wide["v_m_s"], told["v_m_s"], atol=1e-2) and wide["range_bound"] < told["range_bound"] * 1.5,
          "the path itself is unchanged (the errors given weigh azimuth against depression as before); only its errors, "
          "and the range's bound, are read anew", f"bound {wide['range_bound']:.4f} against {told['range_bound']:.4f}")
    # coverage: 40 orbits drawn with a scatter a sixth of the errors given; the truth within two errors. Over 400 such
    # orbits (session 23's notes, job 1125) two errors held the east and north velocity and the climb 94.5, 95.3 and
    # 94.5 times in 100, as they do where the errors given are the scatter drawn (95.5, 96.0, 95.0); the 40 here are a
    # guard on that, not the measurement (their three numbers a draw err together, so 120 hits scatter as 40 do)
    hit, total, used = 0, 0, 0
    for seed in range(40):
        pl, lo, tr = orbit(noise=(0.05, 0.02), seed=100 + seed)
        f = drift.fit_track(drift.rays(pl, lo, FPS), (0.3, 0.1), nboot=0)
        used += f["errors_from"] == "the rays' own scatter"
        e = f["v_err_m_s"]
        for got, want, err in ((f["v_m_s"][0], tr["v"][0], e[0]), (f["v_m_s"][1], tr["v"][1], e[1]),
                               (f["climb_m_s"], tr["climb"], f["climb_err_m_s"])):
            total += 1
            hit += abs(got - want) <= 2 * err
    check(used == 40 and 0.85 * total <= hit, "over 40 drawn orbits two such errors hold the truth as often as two errors "
          "should (95 times in 100 over 400 orbits; 85 at the least over these 40)",
          f"{hit} of {total} velocities and climbs, the rays' own scatter used on {used} of 40")
    loose = drift.fit_track(R, (0.03, 0.01), nboot=0)
    check(loose["errors_from"].startswith("the errors given, scaled up") and loose["chi2_dof"] > 5 and loose["chi2_p_low"] is None
          and abs(loose["velocity_err_m_s"] / told["velocity_err_m_s"] - 1) < 0.35,
          "errors given three times too tight: scaled up by the misfit, as before",
          f"reduced chi-square {loose['chi2_dof']:.1f}, velocity {loose['velocity_err_m_s']:.3f} m/s")
    pl, lo, _ = orbit(noise=(0.0, 0.0))
    exact = drift.fit_track(drift.rays(pl, lo, FPS), (0.3, 0.1), nboot=0)
    check(exact["errors_from"] == "the rays' own scatter" and np.allclose(exact["sigma_deg"], [0.3 * drift.OWN_LEAST, 0.1 * drift.OWN_LEAST])
          and exact["velocity_err_m_s"] > 0, "rays with no scatter at all (drawn, not read): their errors are held at a "
          "hundredth of those given, not at nothing", f"{exact['sigma_deg']}")
    sp, sl, _ = orbit(turn=False, noise=(0.02, 0.01))
    ps = drift.fit_track(drift.rays(sp, sl, FPS), (0.3, 0.1), nboot=100)
    t2 = drift.test_wind_track(ps, [dict(label="w", w=truth["v"], counts=True, note="")])
    check(not ps["path_gate"] and t2["outcome"] == drift.CANNOT and "flew straight" in t2["reading"],
          "a straight flight whose rays fit tightly is refused all the same: the refusal reads the aircraft's path, not "
          "the errors", t2["reading"][:80])
    said = "\n".join(drift.said(dict(tests=[], verdict="", why="", ground_path=dict(wide, above_ground_m=None))))
    check("fit better than the errors given for them allow" in said and "the rays' own scatter" in said,
          "and the command's own words say where the errors came from")


def boxed(platform, off=0.0):
    """The platform's readings as a display prints them: a heading box in whole degrees, the aircraft flying `off` deg
    to the right of it."""
    return {f: (la, lo, alt, float(round((h - off) % 360) % 360)) for f, (la, lo, alt, h) in platform.items()}


def test_track_the_heading_box_is_not_taken_as_the_direction_of_flight():
    """DR2 (IDEAS.md; 2026-11-13). `aircraft_wind` took the heading box as the direction of flight. On PR051's upload
    the aircraft's own positions put it 14.2 +- 0.3 deg right of its box on both legs, and the wind the box alone gives
    (21.6 m/s from 211 deg) is 17 m/s from the one its path gives; T2 then failed a body within 4-6 m/s of the wind.
    An aircraft drawn with a known angle between its box and its flight must give back that angle and the true wind;
    one drawn without must be left alone; and a turn too short to tell the wind from the angle must say so."""
    print("\nT2 from the aircraft's own track: the heading box is not taken as the direction of flight")
    platform, los, truth = orbit(h_obj=600.0)
    own = drift.aircraft_wind(boxed(platform), FPS)
    miss = float(np.hypot(*(own["w"] - truth["w_air"])))
    check(not own["heading_offset_seen"] and own["heading_offset_deg"] == 0.0 and miss < 0.3 and own["heading_step_deg"] == 1.0
          and own["fixed"] and miss < 2 * own["err_m_s"] < 1.5,
          "a box that reads the direction of flight, in whole degrees: no offset is seen, the wind is the true one",
          f"{np.round(own['w'], 2).tolist()} of {truth['w_air'].tolist()} +- {own['err_m_s']:.2f}, the offset's p {own['heading_offset_p']:.2f}")
    crab = drift.aircraft_wind(boxed(platform, 14.2), FPS)
    miss = float(np.hypot(*(crab["w"] - truth["w_air"])))
    shown = float(np.hypot(*(crab["w_as_displayed"] - truth["w_air"])))
    check(crab["heading_offset_seen"] and abs(crab["heading_offset_deg"] - 14.2) < 0.4 and miss < 0.3 and crab["fixed"],
          "the aircraft flying 14.2 deg right of its box: the offset is seen and read, and the wind is the true one",
          f"{crab['heading_offset_deg']:.2f} +- {crab['heading_offset_err_deg']:.2f} deg, the wind {np.round(crab['w'], 2).tolist()}")
    check(shown > 10.0, "where the box alone would have put the wind 10 m/s or more off (PR051's case)",
          f"{np.round(crab['w_as_displayed'], 1).tolist()}, {shown:.1f} m/s from the true wind")
    small = drift.aircraft_wind(boxed(platform, 0.4), FPS)
    miss = float(np.hypot(*(small["w"] - truth["w_air"])))
    check(not small["heading_offset_seen"] and miss <= 2 * small["err_m_s"],
          "an offset inside the box's own step (0.4 deg) is not seen, and the wind's error carries it",
          f"the wind {miss:.2f} m/s off, its error {small['err_m_s']:.2f}")
    # T2 whole, the aircraft's own wind the only one, on a body that drifts with it and on one that flies
    drifter, flier = truth["w_air"], truth["w_air"] + 25.0 * np.array([0.5, -0.866])
    for off in (0.0, 14.2):
        pl, lo, _ = orbit(h_obj=600.0, v_obj=tuple(drifter), climb=0.0)
        p = drift.fit_track(drift.rays(pl, lo, FPS), (0.1, 0.03), nboot=200)
        o = drift.aircraft_wind(boxed(pl, off), FPS)
        t2 = drift.test_wind_track(p, drift.track_winds(p["height_m"], None, own=o))
        check(t2["outcome"] == drift.PASS and "two errors of the aircraft's own wind" in t2["reading"],
              f"a drifter, the box {'true' if not off else 'off by 14.2 deg'}: passes, the wind's own error in the tolerance",
              t2["reading"][45:170])
        if off:
            old = drift.test_wind_track(p, [dict(label="the box alone", w=o["w_as_displayed"], counts=True, note="")])
            check(old["outcome"] == drift.FAIL, "which the wind from the box alone failed (\"it flies\"), as the stage did until now",
                  old["reading"][:90])
        pl, lo, _ = orbit(h_obj=600.0, v_obj=tuple(flier), climb=0.0)
        p = drift.fit_track(drift.rays(pl, lo, FPS), (0.1, 0.03), nboot=200)
        t2 = drift.test_wind_track(p, drift.track_winds(p["height_m"], None, own=drift.aircraft_wind(boxed(pl, off), FPS)))
        check(t2["outcome"] == drift.FAIL, f"a flier at 25 m/s through the air, the box {'true' if not off else 'off'}: fails all the same")
    # too little turn: the wind cannot be told from the offset and the airspeed
    pl, lo, _ = orbit(h_obj=600.0, seconds=25.0)
    short = drift.aircraft_wind(boxed(pl, 14.2), FPS)
    W = drift.track_winds(600.0, None, own=short)
    check(short is not None and 40 < short["heading_turn_deg"] < 45 and not short["fixed"] and not W[0]["counts"]
          and "does not fix it" in W[0]["note"],
          "a turn of 41 deg: two errors of the wind are over 5 m/s with the offset open, and the wind is not counted",
          f"error {short['err_m_s']:.1f} m/s; {W[0]['note'][-60:]}")
    check(drift.aircraft_wind(boxed(orbit(seconds=17.0)[0]), FPS) is None, "a turn under 30 deg gives no wind, as before")


def test_track_the_azimuth_reference_is_carried():
    """DR2's second half (2026-11-13). Every ray's azimuth rests on the display's own true north. An error in it turns
    every ray alike, the rays' scatter cannot show it, and the fitted velocity moves (Puerto Rico: 1.4 m/s a degree,
    three times its quoted error). Rays drawn with a known constant azimuth error must move the path by the pull the
    fit reports, and the errors must hold the truth when that error is allowed for and not when it is ruled out."""
    print("\nT1/T2 from the aircraft's own track: a constant error of the display's azimuths is carried")
    platform, los, truth = orbit()
    R = drift.rays(platform, los, FPS)
    p = drift.fit_track(R, (0.1, 0.03), nboot=0)
    exact = drift.fit_track(R, (0.1, 0.03), nboot=0, az_ref_err=1e-9)
    free = drift.fit_track(R, (0.1, 0.03), nboot=0, az_ref_err=float("inf"))
    check(p["az_reference_known_deg"] == 0.1 and abs(exact["velocity_err_m_s"] - exact["velocity_err_rays_m_s"]) < 1e-6
          and exact["velocity_err_m_s"] < p["velocity_err_m_s"] < free["velocity_err_m_s"]
          and p["velocity_err_rays_m_s"] == exact["velocity_err_rays_m_s"],
          "by default the reference is as well known as an azimuth is given to be (0.1 deg here): the velocity's error lies "
          "between a reference taken as exact and one left to the rays",
          f"{exact['velocity_err_m_s']:.3f} < {p['velocity_err_m_s']:.3f} < {free['velocity_err_m_s']:.3f} m/s; the rays fix it "
          f"to {p['az_reference_err_deg']:.2f} deg")
    check(np.allclose(p["v_m_s"], exact["v_m_s"]) and np.allclose(p["v_m_s"], free["v_m_s"]),
          "the path itself does not move with what is known of the reference")
    off = drift.fit_track(drift.rays(platform, {f: dict(L, az=L["az"] + 1.0) for f, L in los.items()}, FPS), (0.1, 0.03),
                          nboot=200, az_ref_err=1.0)
    moved = float(np.hypot(*(np.array(off["v_m_s"]) - np.array(p["v_m_s"]))))
    check(abs(moved / p["az_reference_pull_m_s"] - 1) < 0.15 and p["az_reference_pull_m_s"] > 0.5,
          "every azimuth a degree off: the velocity moves by the pull the fit reports for a degree",
          f"{moved:.2f} m/s against {p['az_reference_pull_m_s']:.2f}")
    miss = float(np.hypot(*(np.array(off["v_m_s"]) - truth["v"])))
    check(miss <= 2 * off["velocity_err_m_s"] and miss > 2 * off["velocity_err_rays_m_s"],
          "with the reference given as known to a degree, two errors hold the true velocity; the rays' scatter alone "
          "would not have", f"{miss:.2f} m/s off, two errors {2 * off['velocity_err_m_s']:.2f} (the rays' alone {2 * off['velocity_err_rays_m_s']:.2f})")
    check(abs(off["az_reference_fitted_deg"] + 1.0) < 2.5 * off["az_reference_err_deg"] and off["az_reference_used_deg"] == 1.0,
          "the rays' own reading of the reference is reported beside it (they read the degree they were turned by, to "
          "their error), and what is carried is the degree given, not the rays' tighter reading",
          f"{off['az_reference_fitted_deg']:+.2f} +- {off['az_reference_err_deg']:.2f} deg")
    t1 = drift.test_vertical_track(off)
    check(t1["outcome"] == drift.PASS, "T1 still passes: the climb is hardly moved", t1["reading"])
    # where only the reference leaves the velocity open, T2 says so
    fixed = dict(off, velocity_err_m_s=3.0, velocity_err_rays_m_s=1.0, velocity_err_reference_m_s=2.83, az_reference_used_deg=2.5,
                 az_reference_pull_m_s=1.15)
    t2 = drift.test_wind_track(fixed, [dict(label="w", w=truth["v"], counts=True, note="")])
    check(t2["outcome"] == drift.CANNOT and "azimuth reference open to 2.5 deg" in t2["reading"],
          "a velocity the rays' scatter would fix and the reference leaves open: cannot say, naming the reference",
          t2["reading"][:150])
    said = "\n".join(drift.said(dict(tests=[], verdict="", why="", ground_path=dict(p, above_ground_m=None))))
    check("the display's azimuth reference" in said and "taken as known to 0.1 deg beforehand" in said,
          "and the command's own words give the reference, its pull and what the rays alone would give")


def test_track_t2_a_drifter_fits_the_winds_and_a_flier_does_not():
    print("\nT2 from the aircraft's own track: the winds")
    rng = np.random.default_rng(6)
    wind = np.array([-6.0, -3.5])
    winds = [dict(label=f"model {i}", w=wind + rng.normal(0, 0.7, 2), counts=True, note="") for i in range(6)]
    platform, los, _ = orbit(v_obj=tuple(wind))
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    out = drift.test_wind_track(p, winds)
    check(out["outcome"] == drift.PASS, "a drifter: every wind leaves it under their spread through the air, passes",
          out["reading"][:100])
    flier = wind + 25.0 * np.array([0.5, -0.866])
    platform, los, _ = orbit(v_obj=tuple(flier))
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    out = drift.test_wind_track(p, winds)
    check(out["outcome"] == drift.FAIL, "a flier at 25 m/s through the air: fails", out["reading"][:100])
    check(drift.verdict([dict(test="T2", outcome=drift.PASS, reading="", source="lines of sight")])[0].startswith("consistent")
          and drift.verdict([out])[0] == "not drifting" and out["source"] == "lines of sight",
          "a passing T2 from the track is a strong test (it says where it came from: lines of sight)")
    near = wind + 5.0 * np.array([0.5, -0.866])
    platform, los, _ = orbit(v_obj=tuple(near))
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    check(drift.test_wind_track(p, winds)["outcome"] == drift.CANNOT, "5 m/s through the air: a slow flier's, cannot say")


def test_track_t2_a_models_own_error():
    """A model's winds carry their own error, `MODEL_WIND_ERR` (2026-11-13). It was 3 m/s, chosen on the Galileo
    Project's clouds, which need 3-4 m/s through the air against Open-Meteo's winds. Since 2026-11-17 it is 2 m/s, the
    maintainer's choice after it was measured against weather balloons (method section 68): 2 m/s covers what a
    drifting balloon needs 91 times in 100, and a body flying 5 m/s through the air then passes 20 times in 100 where
    it passed 33 at 3 m/s. So the cloud of this test that is 3.5 m/s off the model's winds, which passed until then,
    cannot be said now; one 2.2 m/s off passes."""
    print("\nT2 from the aircraft's own track: a model's winds carry their own error (2026-11-13; 2 m/s since 2026-11-17)")
    wind = np.array([-6.0, -3.5])
    rng = np.random.default_rng(7)
    winds = [dict(label=f"model {i}", w=wind + rng.normal(0, 0.3, 2), counts=True, note="model", source="model")
             for i in range(2)]
    obs = [dict(w, source="observed", note="observed") for w in winds]
    check(drift.MODEL_WIND_ERR == 2.0, "MODEL_WIND_ERR is 2 m/s", f"{drift.MODEL_WIND_ERR:g}")
    near = wind + 2.2 * np.array([0.6, 0.8])                  # a cloud that drifts, 2.2 m/s off the model's wind
    platform, los, _ = orbit(v_obj=tuple(near))
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    out = drift.test_wind_track(p, winds)
    check(out["outcome"] == drift.PASS and out["model_wind_err_m_s"] == drift.MODEL_WIND_ERR
          and "a model's own error (2)" in out["reading"] and out["tolerance_m_s"] - out["winds_spread_m_s"] - 2 * out["velocity_err_m_s"] < 2.05,
          "2.2 m/s off a model's winds: within their spread, the fit's errors and the model's own error (2), passes",
          out["reading"][:150])
    lone = drift.test_wind_track(p, obs)
    check(lone["outcome"] == drift.CANNOT and lone["model_wind_err_m_s"] == 0.0 and abs(out["tolerance_m_s"] - lone["tolerance_m_s"] - 2.0) < 0.011,
          "the same off observed winds: no model's error allowed, cannot say (the rule before 2026-11-13)",
          lone["reading"][:120])
    off = wind + 3.5 * np.array([0.6, 0.8])                   # 3.5 m/s off: inside 3 m/s of allowance, outside 2
    platform, los, _ = orbit(v_obj=tuple(off))
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    out = drift.test_wind_track(p, winds)
    check(out["outcome"] == drift.CANNOT and out["needs_m_s"][1] > out["tolerance_m_s"] > out["needs_m_s"][1] - 1.0
          and "not by a flier's" in out["reading"],
          "3.5 m/s off a model's winds: beyond the tolerance by under 1 m/s, cannot say (it passed until 2026-11-17, "
          "when the model's own error was 3 m/s)", f"needs {out['needs_m_s']}, tolerance {out['tolerance_m_s']}")
    flier = wind + 25.0 * np.array([0.5, -0.866])
    platform, los, _ = orbit(v_obj=tuple(flier))
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    check(drift.test_wind_track(p, winds)["outcome"] == drift.FAIL, "a flier at 25 m/s through the air still fails")


def test_track_t2_a_flier_fails_whatever_its_velocitys_error():
    """Since 2026-11-17 the fail rule is asked before the velocity's gate (the maintainer's decision; IDEAS.md C1). T2's
    tolerance already holds two errors of the fitted velocity, so a body a flier's 10 m/s or more beyond the whole of it
    fails however large that error is. Until then two errors over 5 m/s (`VELOCITY_FIX`) made T2 say "cannot say" before
    any wind was read: once each camera's own pointing was carried (method section 66), an aircraft at 120 m/s known to
    10 m/s could not be called a flier, and 24 to 52 of the 54 Galileo aircraft T2 had failed read "cannot say". Short of
    a flier's margin the gate speaks as before, in the words and with the fields it had: T2 never passes, and never
    says "between", on a velocity the rays do not fix."""
    print("\nT2 from the lines of sight: a flier fails whatever its velocity's error (2026-11-17)")
    w0 = np.array([8.0, 3.0])
    wind = dict(label="sounding", w=w0, counts=True, note="observed", source="observed")

    def path(through_air, ev, **more):
        v = w0 + through_air * np.array([0.6, 0.8])
        return dict(dict(v_m_s=v.tolist(), speed_m_s=float(np.hypot(*v)), toward_deg=float(np.degrees(np.arctan2(*v)) % 360),
                         velocity_err_m_s=ev, los_turn_deg=90.0, height_m=3000.0, path_off_line_m=500.0, path_gate=True,
                         range_bound=0.1, model_p=0.5, boots=2000, boots_of=2000, readings=30), **more)

    gate = "the lines of sight do not fix its velocity ("
    fast = drift.test_wind_track(path(110.0, 6.0), [wind])                 # two errors 12 m/s: over VELOCITY_FIX
    check(fast["outcome"] == drift.FAIL and "it flies" in fast["reading"] and "two errors of the fit (12.0)" in fast["reading"]
          and fast["tolerance_m_s"] == 12.25 and abs(fast["needs_m_s"][0] - 110.0) < 0.01 and fast["velocity_err_m_s"] == 6.0,
          "a body 110 m/s through the air whose velocity is known to 6 m/s: it fails (cannot say until 2026-11-17), and "
          "the reading gives the two errors it was allowed", fast["reading"][:150])
    slow = drift.test_wind_track(path(20.0, 6.0), [wind])                  # 20 - 12.25 = 7.75 beyond: under a flier's 10
    check(slow["outcome"] == drift.CANNOT and slow["reading"].startswith(gate) and "two errors 12.0" in slow["reading"]
          and "needs_m_s" not in slow and "winds" not in slow and "tolerance_m_s" not in slow,
          "the same error on a body 20 m/s through the air, 7.8 beyond the tolerance: not a flier's margin, so the "
          "velocity's gate answers as it always did, with its own words and fields", slow["reading"][:110])
    still = drift.test_wind_track(path(0.0, 6.0), [wind])
    check(still["outcome"] == drift.CANNOT and still["reading"].startswith(gate),
          "and on a drifter: T2 does not pass a body whose velocity the rays do not fix")
    edge = [drift.test_wind_track(path(22.25 + d, 6.0), [wind])["outcome"] for d in (-0.05, 0.05)]
    check(edge == [drift.CANNOT, drift.FAIL], "the edge is the fail rule's own: the whole tolerance (the winds' spread 0.25 "
          "and two errors 12) plus a flier's 10 m/s", f"22.2 m/s {edge[0]}, 22.3 m/s {edge[1]}")
    model = dict(wind, source="model", note="model")
    edge = [drift.test_wind_track(path(22.25 + drift.MODEL_WIND_ERR + d, 6.0), [model])["outcome"] for d in (-0.05, 0.05)]
    check(edge == [drift.CANNOT, drift.FAIL] and drift.test_wind_track(path(22.3, 6.0), [model])["outcome"] == drift.CANNOT,
          "against a model's wind the tolerance holds the model's own error too, and the edge moves out by it")
    none = drift.test_wind_track(path(110.0, float("inf")), [wind])
    far = drift.test_wind_track(path(110.0, 6.0), [dict(wind, counts=False)])
    bare = drift.test_wind_track(path(110.0, 6.0), [])
    check(all(t["outcome"] == drift.CANNOT and t["reading"].startswith(gate) for t in (none, far, bare)),
          "an error that is not finite, or no wind that counts, leaves the fail rule nothing to ask with: the gate "
          "answers, as before", none["reading"][:80])
    fixed = drift.test_wind_track(path(110.0, 2.0), [wind])
    check(fixed["outcome"] == drift.FAIL and {k: v for k, v in fast.items() if k not in ("reading", "velocity_err_m_s", "tolerance_m_s")}
          == {k: v for k, v in fixed.items() if k not in ("reading", "velocity_err_m_s", "tolerance_m_s")},
          "a fail on a velocity that is not fixed carries the fields of any other fail: the winds, the airspeeds needed, "
          "the tolerance")
    # the same from cameras whose pointing is known only to three degrees: the cameras' words where it cannot say
    from mcdonald import sightlines
    opt = dict(sig=(0.3, 0.1), ground_m=600.0, pointing_err=(3.0, 3.0), nboot=60)
    out = {}
    for name, through in (("an aircraft", 110.0), ("a slow flier", 15.0)):
        rd, _ = cameras_scene(v=tuple(w0 + through * np.array([0.6, 0.8])), seconds=30.0, every=1.0, h=3000.0)
        p = drift.fit_track(sightlines.rays(rd), rng=np.random.default_rng(1), **opt)
        out[name] = (p, drift.test_wind_track(p, [wind]))
    (pa, ta), (ps, ts) = out["an aircraft"], out["a slow flier"]
    check(2 * pa["velocity_err_m_s"] > drift.VELOCITY_FIX and ta["outcome"] == drift.FAIL and "it flies" in ta["reading"],
          "three cameras whose pointing is known to three degrees see an aircraft at 110 m/s through the air: two errors of its "
          "velocity are over 5 m/s, and it fails", f"two errors {2 * pa['velocity_err_m_s']:.1f} m/s; {ta['reading'][:90]}")
    check(2 * ps["velocity_err_m_s"] > drift.VELOCITY_FIX and ts["outcome"] == drift.CANNOT and ts["reading"].startswith(gate)
          and "Each camera's pointing is taken as known to 3 deg" in ts["reading"],
          "and a body at 15 m/s through the air: cannot say, in the cameras' own words for a velocity left open",
          f"two errors {2 * ps['velocity_err_m_s']:.1f} m/s; {ts['reading'][:120]}")


def test_track_t2_holding_still_against_drifting():
    """A body holding still over the ground needs the wind's own speed through the air. In a wind lighter than T2's
    tolerance that fits, and it passed as a drifter (IDEAS.md N2, 2026-11-13). The comparative rule asks every
    drifter's airspeed to be under the weakest wind's: the Puerto Rico lanterns (1.4-3.6 m/s against 4.5-9.5) keep
    their pass. The winds here are a model's, so the tolerance holds `MODEL_WIND_ERR`, and since that went from 3 to
    2 m/s (2026-11-17) the wind in which holding still "fits as well" is a 2 m/s one: in the 3 m/s wind this test
    used until then, a body holding still is now beyond the tolerance, and cannot be said for that reason."""
    print("\nT2 from the aircraft's own track: drifting must fit better than holding still (2026-11-13)")
    light = np.array([1.6, -1.2])                             # 2 m/s
    winds = [dict(label=f"model {i}", w=light + d, counts=True, note="model", source="model")
             for i, d in enumerate((np.zeros(2), np.array([0.3, 0.2])))]
    platform, los, _ = orbit(v_obj=(0.0, 0.0), climb=0.0)
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    out = drift.test_wind_track(p, winds)
    check(out["outcome"] == drift.CANNOT and "holding still fits as well" in out["reading"] and not out["drift_beats_hold"],
          "a body holding still in a 2 m/s wind: cannot say, where it passed before", out["reading"][:110])
    three = [dict(w, w=w["w"] * 1.5) for w in winds]         # 3 m/s
    out = drift.test_wind_track(p, three)
    check(out["outcome"] == drift.CANNOT and "not by a flier's" in out["reading"] and out["needs_m_s"][0] > out["tolerance_m_s"],
          "holding still in a 3 m/s wind: beyond a model's 2 m/s of allowance, so cannot say for that (until 2026-11-17, "
          "at 3 m/s, it was within it, and this rule spoke)", f"needs {out['needs_m_s']}, tolerance {out['tolerance_m_s']}")
    platform, los, _ = orbit(v_obj=tuple(light), climb=0.0)
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    out = drift.test_wind_track(p, winds)
    check(out["outcome"] == drift.PASS and out["drift_beats_hold"],
          "a drifter in that light wind still passes: it needs well under the 2 m/s holding still would", out["reading"][-90:])
    strong = [dict(w, w=w["w"] * 9.0) for w in winds]       # 18 m/s
    platform, los, _ = orbit(v_obj=tuple(strong[0]["w"]), climb=0.0)
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    out = drift.test_wind_track(p, strong)
    check(out["outcome"] == drift.PASS and out["drift_beats_hold"] and "holding still would need" in out["reading"],
          "a drifter in an 18 m/s wind: passes, holding still needing more at every wind", out["reading"][-90:])
    platform, los, _ = orbit(v_obj=(0.0, 0.0), climb=0.0)
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    check(drift.test_wind_track(p, strong)["outcome"] == drift.FAIL, "holding still in that 18 m/s wind: fails, as before")


def test_track_t2_one_wind_far_from_its_height():
    """DR4 (IDEAS.md; 2026-11-13). One wind alone has no spread, so T2 held it at 0.25 m/s and took it as the wind at
    the object's height wherever it counted: within a factor of 4 in height. On PR051 the aircraft's own wind, read
    1,422 m above the object, decided a fail. The wind's own change with height is now allowed for, as radiosondes
    measure it (`drift.wind_change`: nine soundings in ten change less), and a wind read so far from the object that
    this change is over 5 m/s cannot pass T2 or fail a slow flier."""
    print("\nT2 from the aircraft's own track: one wind read far from the object's height")
    check(drift.wind_change(0) == 0.0 and abs(drift.wind_change(100) - 2.8) < 0.15 and abs(drift.wind_change(400) - 6.1) < 0.2
          and abs(drift.wind_change(1422) - 12.6) < 0.3 and drift.wind_change(-400) == drift.wind_change(400),
          "the wind's change with height, nine soundings in ten: 2.8 m/s over 100 m, 6.1 over 400, 12.6 over 1,422",
          f"{drift.wind_change(100):.2f}, {drift.wind_change(400):.2f}, {drift.wind_change(1422):.2f}")
    table = [r for r in drift.read_rows(reference_data.GOLDEN / "shear_soundings.csv")
             if (r["low_m"], r["high_m"]) == ("0", "16000")]
    ratio = [drift.wind_change(float(r["dz_median_m"])) / float(r["p90"]) for r in table]
    under = [float(r["p68"]) < drift.wind_change(float(r["dz_median_m"])) < float(r["p95"]) for r in table]
    check(len(table) == 7 and all(0.85 < x < 1.15 for x in ratio) and all(under),
          "the law against the soundings' own table (8,125 soundings at 18 stations): within 15 % of the 90th percentile at "
          "every height difference from 50 m to 6.4 km, between the 68th and the 95th", f"{min(ratio):.2f}-{max(ratio):.2f}")
    wind = np.array([-6.0, -3.5])
    platform, los, _ = orbit(v_obj=tuple(wind), climb=0.0)                      # a drifter 250 m above the sea
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)

    def level(height, w):                                                       # one observed wind level, as --obs-winds gives it
        return [dict(source="one level", height_m=height, from_deg=drift._from(w), speed_m_s=float(np.hypot(*w)))]
    W = drift.track_winds(p["height_m"], None, observed=level(p["height_m"] + 100.0, wind + np.array([1.6, 1.2])))
    t2 = drift.test_wind_track(p, W)
    check(W[0]["counts"] and abs(W[0]["level_gap_m"] - 100.0) < 1e-6 and t2["outcome"] == drift.PASS
          and abs(t2["wind_change_m_s"] - drift.wind_change(100.0)) < 0.01 and "the wind's own change over the 100 m" in t2["reading"],
          "one wind read 100 m above a drifter and 2 m/s off its own wind: within the wind's change over 100 m, passes "
          "(it could not say until now)", t2["reading"][45:230])
    W = drift.track_winds(p["height_m"], None, observed=level(p["height_m"] + 650.0, wind + np.array([8.8, 6.6])))
    t2 = drift.test_wind_track(p, W)
    old = drift.test_wind_track(p, [dict(W[0], level_gap_m=None)])
    check(W[0]["counts"] and old["outcome"] == drift.FAIL,
          "one wind read 650 m above a drifter and 11 m/s off its own wind (one sounding in twenty changes that much): "
          "taken as the wind at its height, as until now, T2 fails the drifter", old["reading"][:110])
    check(t2["outcome"] == drift.CANNOT and "no wind was read near its height" in t2["reading"] and t2["winds_level_gap_m"] == 650
          and t2["wind_change_m_s"] > drift.VELOCITY_FIX,
          "with the wind's change over 650 m allowed for: cannot say, and says that no wind was read near its height",
          t2["reading"][:200])
    W = drift.track_winds(p["height_m"], None, observed=level(p["height_m"] + 650.0, wind))
    check(drift.test_wind_track(p, W)["outcome"] == drift.CANNOT,
          "the same level with the drifter's own wind on it: cannot say either (a wind that far off cannot pass a body)")
    flier = wind + 40.0 * np.array([0.5, -0.866])
    platform, los, _ = orbit(v_obj=tuple(flier), climb=0.0)
    pf = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    t2 = drift.test_wind_track(pf, drift.track_winds(pf["height_m"], None, observed=level(pf["height_m"] + 650.0, wind)))
    check(t2["outcome"] == drift.FAIL and "the wind's own change over the 650 m" in t2["reading"],
          "a body 40 m/s through the air is failed all the same: beyond that change by a flier's 10 m/s", t2["reading"][:120])
    near = dict(label="at its height", w=wind, counts=True, note="", level_gap_m=0.0)
    far = dict(label="far above", w=wind + np.array([8.8, 6.6]), counts=True, note="", level_gap_m=650.0)
    t2 = drift.test_wind_track(p, [near, far])
    check(t2["winds_level_gap_m"] == 0 and t2["wind_change_m_s"] == 0.0 and t2["winds_spread_m_s"] > 10,
          "with a second wind at its own height nothing is added: the winds' own spread says how they differ",
          f"spread {t2['winds_spread_m_s']} m/s")


def test_track_winds_at_the_objects_height():
    print("\nT2 from the aircraft's own track: which winds bear on its height")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "w.json"
        p.write_text(json.dumps({"elevation": 50.0, "hourly": {
            "time": ["2013-04-27T00:00", "2013-04-27T01:00", "2013-04-27T02:00", "2013-04-27T05:00"],
            "wind_speed_10m": [10.0] * 4, "wind_direction_10m": [60.0] * 4,
            "wind_speed_100m": [14.0] * 4, "wind_direction_100m": [60.0] * 4,
            "wind_speed_925hPa": [None] * 4, "wind_direction_925hPa": [None] * 4}}), encoding="utf-8")
        obs = [dict(source="sounding", height_m=h, from_deg=d, speed_m_s=s) for h, d, s in
               ((10, 40, 3.0), (150, 40, 5.0), (400, 40, 7.0))] + [dict(source="metar", height_m=60, from_deg=60,
                                                                        speed_m_s=4.0)]
        own = dict(w=np.array([-8.0, -4.0]), err_m_s=0.3, airspeed_m_s=100.0, height_m=700.0, heights_m=[600, 800],
                   heading_turn_deg=150.0)
        W = {w["label"]: w for w in drift.track_winds(250.0, 50.0, [p], "2013-04-27T01:22", obs, own)}
    model = [w for k, w in W.items() if k.startswith("w ")]
    check(len(model) == 2, "the model's hours within one of the clip's time", f"{len(model)} of 4")
    check(model[0]["counts"] and abs(np.hypot(*model[0]["w"]) - 14 * drift.KN) < 1e-6 and "2.0 times" in model[0]["note"],
          "a model held at its top level (100 m above its ground) for an object twice as high: counts, the note saying so",
          model[0]["note"])
    s = W["sounding"]
    check(s["counts"] and 5.0 < np.hypot(*s["w"]) < 7.0, "a sounding that brackets it: interpolated, counts",
          f"{np.hypot(*s['w']):.2f} m/s")
    check(not W["metar"]["counts"], "a surface report far below it: read, not counted")
    b = W["between metar and the aircraft's own"]
    check(b["counts"] and 4.0 < np.hypot(*b["w"]) < np.hypot(-8, -4), "between the report below and the aircraft's own "
          "wind above: the measured profile, counts", f"{np.hypot(*b['w']):.2f} m/s")


def flight_drawn(rng, R0, turn, sig, rd=None):
    """The single-camera survey's drawn flight (verify-measures/scripts/d2_flights.py `fly`, 2026-11-01, call for call so
    that its trials come back): an aircraft at 60-120 m/s and 1.5-6 km, 20-80 readings over 60-240 s, turning `turn`
    deg, an object R0 off drifting at 3-15 m/s; the line of sight with `sig` deg of noise; the position block rounded
    to `rd` (arcseconds, feet) where given."""
    M = 110574.0
    lat0, lon0 = 18.4 + rng.uniform(-1, 1), -67.0 + rng.uniform(-1, 1)
    me = M * math.cos(math.radians(lat0))
    n = int(rng.choice([20, 40, 80]))
    dur = float(rng.choice([60.0, 120.0, 240.0]))
    t = np.linspace(0, dur, n)
    v = rng.uniform(60, 120)
    alt = rng.uniform(1500, 6000)
    h0 = rng.uniform(0, 360)
    rel = rng.uniform(20, 160) * rng.choice([-1, 1])
    hr = np.radians(h0 + turn * t / dur)
    dt = t[1] - t[0]
    E = np.r_[0, np.cumsum(v * 0.5 * (np.sin(hr[1:]) + np.sin(hr[:-1])) * dt)]
    N = np.r_[0, np.cumsum(v * 0.5 * (np.cos(hr[1:]) + np.cos(hr[:-1])) * dt)]
    b = math.radians(h0 + rel)
    zo = rng.uniform(300, 3000)
    w = rng.uniform(3, 15)
    wd = rng.uniform(0, 2 * math.pi)
    O = np.array([R0 * math.sin(b), R0 * math.cos(b), zo])
    W = np.array([w * math.sin(wd), w * math.cos(wd), 0.0])
    plat, los = {}, {}
    fr = (1 + np.round(t * 30)).astype(int)
    for i, f in enumerate(fr):
        la, lo = lat0 + N[i] / M, lon0 + E[i] / me
        if rd:
            la, lo = round(la * 3600 / rd[0]) * rd[0] / 3600, round(lo * 3600 / rd[0]) * rd[0] / 3600
            plat[int(f)] = (la, lo, round(alt / 0.3048 / rd[1]) * rd[1] * 0.3048, float((h0 + turn * t[i] / dur) % 360))
        else:
            plat[int(f)] = (la, lo, alt, float((h0 + turn * t[i] / dur) % 360))
    for i, f in enumerate(fr):
        la, lo = lat0 + N[i] / M, lon0 + E[i] / me
        pt = O + W * t[i]
        d = drift.enu_rows(la, lo) @ (drift.ecef(lat0 + pt[1] / M, lon0 + pt[0] / me, pt[2]) - drift.ecef(la, lo, alt))
        az = math.degrees(math.atan2(d[0], d[1])) % 360 + rng.normal(0, sig[0])
        dep = math.degrees(math.atan2(-d[2], math.hypot(d[0], d[1]))) + rng.normal(0, sig[1])
        los[int(f)] = dict(az=az, dep=dep, tgt=None, off=(0.0, 0.0))
    return plat, los, dict(n=n, dur=dur, w=np.array(W[:2]))


def test_track_a_straight_flight_fixes_nothing_whatever_the_fits_error_says():
    """F4 (the single-camera survey, 2026-11-01, Part 5 1.5; fixed 2026-11-02): the refusal read the fit's velocity error,
    which on a cost flat along range tells where the 28 starts landed, not what the rays hold; a landing beside the
    aircraft at 1-2 % of the true range gave a tight error in m/s and passed, and T2 then called a drifter a flier. The
    path gate reads the aircraft's own path instead."""
    print("\nT1/T2 from the aircraft's own track: a straight flight fixes nothing, whatever the fit's error says")
    sp, sl, truth = orbit(turn=False)
    wind = [dict(label="w", w=truth["v"], counts=True, note="")]
    ps = drift.fit_track(drift.rays(sp, sl, FPS), (0.1, 0.03), nboot=100)
    check(ps["path_off_line_m"] < 2.0 and not ps["path_gate"],
          "a straight flight's path leaves a straight line by under 2 m: the path gate shuts", f"{ps['path_off_line_m']:.2f} m")
    t1, t2 = drift.test_vertical_track(ps), drift.test_wind_track(ps, wind)
    check(t1["outcome"] == drift.CANNOT and "flew straight" in t1["reading"] and t2["outcome"] == drift.CANNOT
          and "flew straight" in t2["reading"], "T1 and T2 cannot say, and say why", t2["reading"][:110])
    phantom = dict(ps, velocity_err_m_s=0.4, speed_m_s=100.0, range_m=[300.0, 400.0])
    t2 = drift.test_wind_track(phantom, wind)
    check(t2["outcome"] == drift.CANNOT and "flew straight" in t2["reading"],
          "the landing the survey found (beside the aircraft, a 0.4 m/s error) is refused all the same: the refusal reads "
          "the path, not the error")
    p = drift.fit_track(drift.rays(*orbit()[:2], FPS), (0.1, 0.03), nboot=100)
    check(p["path_off_line_m"] > 100 and p["path_gate"] and p["range_bound"] < 0.05 and drift.unfixed(p) is None,
          "the orbit: its path leaves a line by hundreds of metres, the range's bound under 0.05, nothing refused",
          f"{p['path_off_line_m']:.0f} m, bound {p['range_bound']:.4f}, model p {p['model_p']:.2f}")
    for rd, name, lim in (((1.0, 1.0), "an arcsecond and a foot", 16.0), ((0.1, 1.0), "a tenth of an arcsecond", 2.0)):
        offs = []
        for i in range(10):
            plat, los, _ = flight_drawn(np.random.default_rng([20000, 30, 0, i]), 20e3, 0.0, (0.3, 0.1), rd)
            R = drift.rays(plat, los, 30.0)
            offs.append(drift.path_off_line(R, drift.Plane(float(np.mean(R["platform"][:, 0])), float(np.mean(R["platform"][:, 1])))))
        check(max(offs) < lim and lim <= drift.PATH_GATE * drift.POSITION_ERR,
              f"the gate's null: a straight flight whose positions are rounded to {name} leaves a line by under {lim:g} m "
              f"(the gate opens at {drift.PATH_GATE * drift.POSITION_ERR:.0f})", f"{min(offs):.2f}-{max(offs):.2f} m")
    plat, los, _ = flight_drawn(np.random.default_rng([20000, 30, 30, 0]), 20e3, 30.0, (0.3, 0.1), (1.0, 1.0))
    R = drift.rays(plat, los, 30.0)
    off = drift.path_off_line(R, drift.Plane(float(np.mean(R["platform"][:, 0])), float(np.mean(R["platform"][:, 1]))))
    check(off > 200, "and a 30-deg turn, rounded the same, opens it", f"{off:.0f} m")
    # the survey's own phantom (verify-measures d2_flights.py, trial 122: 20 km off, 80 readings over 240 s, the a priori
    # sigma): it landed at 2.3 % of the range with a 0.84 m/s velocity error, passed VELOCITY_FIX, and T2 said "it flies"
    plat, los, meta = flight_drawn(np.random.default_rng([20000, 30, 0, 22]), 20e3, 0.0, (0.3, 0.1))
    tr = drift.fit_track(drift.rays(plat, los, 30.0), (0.3, 0.1), None, np.random.default_rng(122), nboot=300)
    t2 = drift.test_wind_track(tr, [dict(label="model", w=meta["w"], counts=True, note="the true wind")])
    frac = float(np.mean(tr["range_m"])) / 20e3
    old = 2 * tr["velocity_err_m_s"] <= drift.VELOCITY_FIX
    check(t2["outcome"] == drift.CANNOT and "flew straight" in t2["reading"] and not tr["path_gate"],
          "the survey's phantom (trial 122) cannot say: the aircraft flew straight",
          f"landed at {100 * frac:.1f} % of the true range with a {tr['velocity_err_m_s']:.2f} m/s error; VELOCITY_FIX "
          f"alone {'passed' if old else 'refused'} it; bound {tr['range_bound']:.3g}")


def test_track_too_few_readings_say_so():
    """F5 (the survey's D1): `measure` admitted 6 readings, the bootstrap fitted only resamples with 8 distinct ones, which 6
    or 7 readings never give, and the stage crashed on the empty sample; 8 readings kept 4.7 of 2,000. The guard is
    now computed from the resamples kept (`boot_kept`), and the two agree."""
    print("\nT1/T2 from the aircraft's own track: too few readings")
    k = {n: drift.boot_kept(n) for n in (6, 7, 8, 9, 10, 12)}
    check(k[6] == 0 and k[7] == 0 and abs(k[8] - 4.8) < 0.1 and abs(k[9] - 69.3) < 0.5 and abs(k[10] - 305.5) < 1
          and abs(k[12] - 1209.6) < 1, "resamples kept of 2,000: none at 6 or 7, 4.8 at 8, 69 at 9, 306 at 10, 1,210 at 12 "
          "(exact; the survey's 4.7, 69.5, 306, 1,257 by simulation)", str({n: round(v, 1) for n, v in k.items()}))
    check(drift.READINGS_MIN == 9 and drift.BOOT_MIN == 20, "so 9 readings are the least: the first to keep the 20 resamples "
          "the errors are read from")
    platform, los, _ = orbit()
    frames = sorted(platform)
    for n in (5, 6, 7, 8):
        sub = frames[:: max(1, len(frames) // n)][:n]
        found = drift.measure(FPS, platform={f: platform[f] for f in sub}, los={f: los[f] for f in sub})
        T = {t["test"]: t for t in drift.flat(found.fields["tests"])}
        check(T["T1"]["outcome"] == drift.CANNOT and T["T2"]["outcome"] == drift.CANNOT and "at least 9 are needed" in T["T2"]["reading"]
              and f"{n} readings keep {drift.boot_kept(n):.0f} of them" in T["T2"]["reading"] and "ground_path" not in found.fields,
              f"{n} readings: no crash, T1 and T2 cannot say and say how many are needed and why", T["T2"]["reading"][-75:])
    sub = frames[::4][:9]
    found = drift.measure(FPS, platform={f: platform[f] for f in sub}, los={f: los[f] for f in sub})
    gp = found.fields.get("ground_path")
    check(gp is not None and 40 <= gp["boots"] <= 100 and gp["boots_of"] == 2000 and found.fields["tests"][0]["outcome"] != drift.CANNOT,
          "9 readings: fitted, with about 69 of the 2,000 resamples, T1 speaks", f"{gp and gp['boots']} resamples")
    sub = frames[::5][:7]
    tr = drift.fit_track(drift.rays({f: platform[f] for f in sub}, {f: los[f] for f in sub}, FPS), (0.1, 0.03), nboot=200)
    check(tr is not None and tr["boots"] == 0 and tr["speed_p05_p95"] is None and math.isfinite(tr["velocity_err_m_s"])
          and "kept 0 of 200" in drift.unfixed(tr), "fit_track itself on 7 readings: no error, the covariance's errors alone, "
          "and `unfixed` says the bootstrap kept nothing")


def test_track_a_model_wind_file_lacking_the_height():
    """F6 (the survey's D3): a model file was held beyond its levels and counted at any height, where an observed level
    counts only within a factor of 4; a 100-m-only file counted at 3,960 m and T2 passed or failed on it."""
    print("\nT2 from the aircraft's own track: a model wind counts only near its levels")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "only100.json"
        p.write_text(json.dumps({"elevation": 0.0, "hourly": {"time": ["2013-04-26T22:00"], "wind_speed_100m": [20.0],
                                                               "wind_direction_100m": [90.0]}}), encoding="utf-8")
        W = {h: drift.track_winds(float(h), None, [p], "2013-04-26T22:00")[0] for h in (100, 250, 400, 500, 3960)}
    check(W[100]["counts"] and W[250]["counts"] and W[400]["counts"] and "interpolated" in W[100]["note"],
          "a 100-m-only file counts at 100, 250 and 400 m (within a factor of 4 of its level above its ground)")
    check(not W[500]["counts"] and not W[3960]["counts"] and "39.6 times" in W[3960]["note"] and "levels 100-100 m" in W[3960]["note"]
          and np.allclose(W[3960]["w"], W[100]["w"]), "not at 500 or 3,960 m (it counted there until 2026-11-02); the note "
          "says which heights the file covers", W[3960]["note"])
    obs = [dict(source="one level", height_m=100.0, from_deg=90.0, speed_m_s=20 * drift.KN)]
    check(not drift.track_winds(3960.0, None, observed=obs)[0]["counts"], "the same level as an observed source: not counted either")
    path = dict(v_m_s=W[3960]["w"].tolist(), speed_m_s=float(np.hypot(*W[3960]["w"])), toward_deg=270.0, velocity_err_m_s=0.5,
                los_turn_deg=90.0, height_m=3960.0, path_off_line_m=500.0, path_gate=True, range_bound=0.1, model_p=0.5,
                boots=2000, boots_of=2000, readings=30)
    t2 = drift.test_wind_track(path, [W[3960]])
    check(t2["outcome"] == drift.CANNOT and "none of the winds given bears on its height (3960 m" in t2["reading"]
          and "levels 100-100 m" in t2["reading"], "T2 on a body at 3,960 m moving with that 100-m wind: cannot say, naming the "
          "file's levels (it passed until 2026-11-02, and failed a body 30 m/s off it)", t2["reading"][:120])


# ---------------------------------------------------------------- planted fliers (docs/method.md, section 67)
def planted_case(v_obj=(-6.0, -3.5), turn=True, nboot=60):
    """A drawn orbit round a body moving at v_obj, six winds near (-6.0, -3.5) m/s, and the case as `measure` makes it:
    (rays, fitted path, winds, the case's T2)."""
    rng = np.random.default_rng(6)
    wind = np.array([-6.0, -3.5])
    winds = [dict(label=f"wind {i}", w=wind + rng.normal(0, 0.7, 2), counts=True, note="") for i in range(6)]
    platform, los, _ = orbit(v_obj=tuple(v_obj), turn=turn)
    R = drift.rays(platform, los, FPS)
    path = drift.fit_track(R, (0.1, 0.03), None, np.random.default_rng(20261021), nboot=nboot)
    return R, path, winds, drift.test_wind_track(path, winds, readings=len(R["t"]))


def test_fliers_planted_on_a_drawn_orbit():
    """`mcdonald drift --plant` (fliers.plant_track): bodies planted at the place a case's rays fixed, moving with the
    air plus an airspeed, each through the case's own fit and T2. On a drawn orbit round a drifter the answer is known:
    a planted drifter passes, a body at 40 m/s through the air fails whichever way it flies, one at 10 m/s is beyond the
    winds but not by a flier's margin, and the same seed gives the same table."""
    from mcdonald import fliers
    print("\nPlanted fliers: on a drawn orbit round a drifter")
    R, path, winds, t2 = planted_case()
    opts = dict(fit=dict(sig=(0.1, 0.03)), case_t2=t2, speeds=(10.0, 40.0), draws=2, nboot=60, procs=0)
    f = fliers.plant_track(R, path, winds, **opts)
    T = {t["airspeed_m_s"]: t for t in f["table"]}
    check(t2["outcome"] == drift.PASS and f["air"] == "path" and f["air_chosen_by"] == "the case passed the wind test"
          and f["plants"] == 48 and sorted(T) == [0.0, 10.0, 40.0] and all(t["plants"] == 16 for t in T.values()),
          "the case passes T2, so the plants ride its own path's velocity: 16 at each of 10 and 40 m/s, and 16 at zero, "
          "which is added", f"air {f['air']}, {f['plants']} plants at {sorted(T)}")
    c = f["case_again"]
    check(c["as_the_case"] is True and c["outcome"] == t2["outcome"] and np.allclose(c["needs_m_s"], t2["needs_m_s"], atol=fliers.AGAIN)
          and not fliers.as_the_case(dict(c, needs_m_s=[c["needs_m_s"][0] + 0.1, c["needs_m_s"][1]]), t2) and not fliers.as_the_case(dict(c, outcome=drift.FAIL), t2)
          and not fliers.as_the_case(dict(c, tolerance_m_s=c["tolerance_m_s"] + 0.1), t2),
          "the check: the case's own rays, planted again as they are, come out as the case did",
          f"T2 {c['outcome']}, needs {c['needs_m_s']} of {t2['needs_m_s']} m/s")
    z = f["drifter"]
    check(z["plants"] == 16 and z["passes"] >= 15 and z["pass_rate"] == round(z["passes"] / 16, 3) and T[0.0]["passes"] == z["passes"]
          and f"passed {z['passes']} times in 16" in f["sentence"],
          "plants at zero airspeed are the drifter itself: they pass 15 times in 16 or more, and the rate stated is the count",
          f"{z['passes']} of {z['plants']}, rate {z['pass_rate']}")
    check(T[40.0]["fails"] == 16 and f["fails_from_m_s"] == 40.0 and "40 m/s or more through the air would have failed" in f["sentence"],
          "plants at 40 m/s fail whichever way they fly, and the sentence says so", f["sentence"])
    check(T[10.0]["cannot_say"] == 16 and T[10.0]["cannot_say_because"] == {fliers.BETWEEN: 16} and f["passes_up_to_m_s"] is None
          and f["cannot_say_m_s"] == [10.0, 10.0] and "At 10 m/s the wind test could not say." in f["sentence"]
          and "No planted flier passed as a drifter, down to the slowest tried, 10 m/s" in f["sentence"],
          "plants at 10 m/s are beyond the winds but not by a flier's margin: cannot say, 16 of 16, and none passes",
          f"{T[10.0]}")
    v = np.array([r["fitted_m_s"] for r in f["runs"]]) - np.array([r["ground_m_s"] for r in f["runs"]])
    check(0.02 < np.sqrt((v ** 2).mean()) < 0.5 and all(len(r["needs_m_s"]) == 2 for r in f["runs"]),
          "each plant's fit finds the velocity it was given, to the rays' errors (a typical miss under 0.5 m/s, and not none)",
          f"rms {np.sqrt((v ** 2).mean()):.2f} m/s over {len(v)} plants")
    few = dict(opts, speeds=(40.0,), directions=2, draws=1)      # 4 plants: 2 at zero, 2 at 40 m/s
    once, again = fliers.plant_track(R, path, winds, **few), fliers.plant_track(R, path, winds, **few)
    other = fliers.plant_track(R, path, winds, **dict(few, seed=7))
    check(json.dumps(again, sort_keys=True) == json.dumps(once, sort_keys=True)
          and [r["fitted_m_s"] for r in other["runs"]] != [r["fitted_m_s"] for r in once["runs"]],
          "the same seed gives the same result, to the last digit; another seed draws other errors")
    pooled = fliers.plant_track(R, path, winds, **dict(few, procs=2))
    check(json.dumps(pooled, sort_keys=True) == json.dumps(once, sort_keys=True), "and the same in two worker processes as in one")
    # the winds as the air: each plant rides one of the six, each as often as any other
    w = fliers.plant_track(R, path, winds, **dict(opts, air="winds", speeds=(40.0,)))
    rides = [sum(r["air"] == f"wind {i}" for r in w["runs"] if r["airspeed_m_s"] == 40.0) for i in range(6)]
    check(w["air"] == "winds" and len(w["airs"]) == 6 and sorted(rides) == [2, 2, 3, 3, 3, 3] and w["drifter"]["passes"] >= 15
          and w["fails_from_m_s"] == 40.0 and "as one of the winds given says" in w["sentence"],
          "asked to ride the winds, the 16 plants at each speed take the six winds in turn (2 or 3 each); a drifter in "
          "any of them passes, 40 m/s fails", f"rides {rides}; {w['sentence']}")
    # what the module does not know of goes through it untouched: the rays' other keys, the fit's other options
    Rx = dict(R, camera=np.arange(len(R["t"])) % 2, cameras=("a", "b"))
    P = fliers.planted_rays(Rx, path, np.array(path["v_m_s"]), fliers.misses(R, path))
    check(set(P) == set(Rx) and all(P[k] is Rx[k] for k in Rx if k not in ("az", "dep")) and np.allclose(P["az"], R["az"], atol=1e-9)
          and np.allclose(P["dep"], R["dep"], atol=1e-9),
          "a plant's rays are the case's with the two angles alone replaced, so a camera named for each ray goes with them; "
          "and the case planted as it is gives the case's own rays back")
    one = dict(opts, speeds=(), directions=1, draws=1)
    wide = fliers.plant_track(R, path, winds, **dict(one, fit=dict(sig=(0.1, 0.03), az_ref_err=5.0)))
    usual = fliers.plant_track(R, path, winds, **one)
    check(wide["runs"][0]["velocity_err_m_s"] > 3 * usual["runs"][0]["velocity_err_m_s"] and wide["runs"][0]["fitted_m_s"] == usual["runs"][0]["fitted_m_s"],
          "the fit's options are handed to each plant's fit as given: an azimuth reference known to 5 deg widens a plant's "
          "velocity error and moves no fitted number",
          f"{usual['runs'][0]['velocity_err_m_s']} -> {wide['runs'][0]['velocity_err_m_s']} m/s")
    lines = "\n".join(fliers.said(f))
    check("| 40 | 16 | 0 | 0 | 16 |" in lines and f["sentence"] in lines and "WARNING" not in lines,
          "the printed lines: the table by airspeed, then the sentence")


def test_fliers_are_not_planted_where_the_case_gives_no_ground():
    """No path, no plants, and the reason: rays that fix no path (a straight flight, too few readings), no wind that
    counts, the route from the ranges (not built), and the object's own motion as the air where the object failed T2."""
    from mcdonald import fliers
    print("\nPlanted fliers: no plants where there is no path to plant on, with the reason")
    R, path, winds, t2 = planted_case(turn=False)
    f = fliers.plant_track(R, path, winds, fit=dict(sig=(0.1, 0.03)), case_t2=t2, nboot=60, procs=0)
    check(f["plants"] == 0 and "runs" not in f and "fix no path" in f.get("why", "") and "flew straight" in f.get("why", "")
          and f["sentence"].startswith("No bodies were planted: ") and fliers.said(f) == [f"\nplanted fliers: {f['sentence']}"],
          "a straight flight fixes no path: no plants, and it says why", f["sentence"][:140])
    few = {k: (v[:6] if isinstance(v, np.ndarray) and len(v) == len(R["t"]) else v) for k, v in R.items()}
    f = fliers.plant_track(few, None, winds, procs=0)
    check(f["plants"] == 0 and "6 lines of sight, where at least 9 are needed" in f.get("why", ""), "six lines of sight: no path, no plants",
          f.get("why", "")[:80])
    R, path, winds, t2 = planted_case()
    f = fliers.plant_track(R, path, [dict(w, counts=False) for w in winds], fit=dict(sig=(0.1, 0.03)), nboot=60, procs=0)
    check(f["plants"] == 0 and "no wind that bears on its height" in f.get("why", ""), "no wind that counts: no plants", f.get("why", "")[:80])
    R, path, winds, t2 = planted_case(v_obj=np.array([-6.0, -3.5]) + 25.0 * np.array([0.5, -0.866]))
    f = fliers.plant_track(R, path, winds, fit=dict(sig=(0.1, 0.03)), case_t2=t2, air="path", nboot=60, procs=0)
    check(t2["outcome"] == drift.FAIL and f["plants"] == 0 and "failed the wind test" in f.get("why", ""),
          "a flier's own motion is not the air's: asked to ride the path of a case that failed T2, no plants", f.get("why", "")[:90])
    f = fliers.plant_track(R, path, winds, fit=dict(sig=(0.1, 0.03)), case_t2=t2, speeds=(40.0,), draws=1, nboot=60, procs=0)
    check(f["air"] == "winds" and f["air_chosen_by"] == "the case did not pass the wind test" and f["drifter"]["passes"] == 8
          and f["fails_from_m_s"] == 40.0, "left to itself there, it plants in the winds: a drifter in them passes, 40 m/s fails",
          f["sentence"])


def test_fliers_through_the_stage_change_nothing_else():
    """`measure(plant=...)`: the field `planted_fliers` and nothing else. Every other field of the result is the same
    with and without it, and a call that does not ask has no such field. From the ranges it says they are not built."""
    print("\nPlanted fliers: through the stage, a field of their own and nothing else moved")
    platform, los, _ = orbit()
    obs = [dict(source="mast", height_m=h, from_deg=59.7, speed_m_s=s) for h, s in ((100.0, 6.5), (400.0, 7.4))]
    kw = dict(platform=platform, los=los, los_sigma=(0.1, 0.03), observed_winds=obs, ground_m=70.0)
    with resamples(60):                                       # the case's own count here; the lanterns' run holds 2,000
        plain = drift.measure(FPS, **kw)
        asked = drift.measure(FPS, plant=dict(speeds=(40.0,), directions=1, draws=1, procs=0), **kw)
    f = asked.fields.get("planted_fliers") or {}
    rest = {k: v for k, v in asked.fields.items() if k != "planted_fliers"}
    dump = lambda d: json.dumps(d, sort_keys=True, default=lambda o: o.tolist())            # noqa: E731
    check("planted_fliers" not in plain.fields and dump(rest) == dump(plain.fields) and asked.result == plain.result,
          "without `plant` there is no such field; with it every other field and every printed result is the same")
    check(f.get("plants") == 2 and f["case_again"]["as_the_case"] is True and f["resamples"] == asked.fields["ground_path"]["boots_of"] == 60
          and f["fails_from_m_s"] == 40.0
          and f["sentence"] in "\n".join(drift.said(asked.fields)) and "planted fliers" not in "\n".join(drift.said(plain.fields)),
          "the field holds the plants (2, each fitted with as many resamples as the case's own fit, and the case again, "
          "which comes out as the case), and the stage prints their sentence after the verdict",
          f.get("sentence", "")[:150])
    g = golden()
    ranges = drift.measure(FPS, slant=g["slant"], horiz=g["horiz"], own=g["own"], bearings=g["bearings"], heading_deg=144.9,
                           winds=g["winds"], air_min_kn=0.0, air_max_kn=240.0, plant={})
    f = ranges.fields["planted_fliers"]
    check(f["plants"] == 0 and f["route"] == "ranges" and "not built yet" in f.get("why", ""),
          "from the ranges (the Yemen clip's route) no fliers are planted yet, and it says so", f["sentence"][:120])


def test_fliers_by_the_command_line_on_the_lanterns():
    print("\nPlanted fliers: by the command line, on the Puerto Rico lanterns")
    if not PR_CLIP.exists():
        print(f"  SKIP  the clip is not on this computer ({PR_CLIP})")
        SKIP.append("planted fliers, Puerto Rico command line")
        return
    g = PR_GOLDEN
    with tempfile.TemporaryDirectory() as td:
        cmd = [sys.executable, "-m", "mcdonald.cli", "drift", str(PR_CLIP), "--platform", str(g / "platform.csv"),
               "--los", str(g / "los.csv"), "--winds", ",".join(sorted(str(p) for p in g.glob("wind_*.json"))),
               "--obs-winds", str(g / "obs_winds.csv"), "--ground-m", "72", "--when", "2013-04-27T01:22:47",
               "--flicker", str(g / "flicker.json"), "--out", str(Path(td) / "p"), "--json",
               "--plant", "--plant-speeds", "40", "--plant-draws", "1", "--procs", "4"]
        env = dict(__import__("os").environ, PYTHONPATH=str(reference_data.REPO / "src"))
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
        d = json.loads(p.stdout) if p.stdout.strip().startswith("{") else None
        bad = subprocess.run(cmd[:cmd.index("--plant")] + ["--plant-speeds", "40"], capture_output=True, text=True,
                             encoding="utf-8", env=env)
    if not check(p.returncode == 0 and d is not None and d["command"] == "drift", "one envelope on stdout",
                 f"exit {p.returncode} {p.stderr[-200:]}"):
        return
    f = d["results"].get("planted_fliers") or {}
    T = {t["airspeed_m_s"]: t for t in f.get("table", [])}
    check(f.get("air") == "path" and f.get("resamples") == 2000 and f["case_again"]["as_the_case"] is True
          and np.allclose(f["case_again"]["needs_m_s"], [1.37, 3.64], atol=0.011),
          "the lanterns pass T2, so the plants ride their own path; each fit resamples 2,000 times, as the case's did; "
          "the case planted again needs 1.37-3.64 m/s, as the case", f"{f.get('case_again')}")
    check(T[0.0]["passes"] == 8 and T[40.0]["fails"] == 8 and f["fails_from_m_s"] == 40.0
          and any("40 m/s or more through the air would have failed" in ln for ln in d["results"]["said"]),
          "planted in the lanterns' own air: a drifter passes 8 times in 8, and 40 m/s fails in every direction",
          f.get("sentence", ""))
    check(bad.returncode != 0 and "go with --plant" in bad.stderr, "--plant-speeds without --plant is refused, with the reason")


# ---------------------------------------------------------------- T1/T2 from cameras on the ground (method section 66)
SITES = ((0.0, 0.0, 740.0), (8600.0, -5500.0, 583.0), (7100.0, -7300.0, 560.0))     # east, north (m), height above the sea:
#                                                                                     three places about 10 and 2 km apart


def cameras_scene(v=(8.0, 3.0), climb=0.0, h=3600.0, at=(6000.0, 5000.0), sites=SITES, seconds=60.0, every=0.5,
                  noise=(0.03, 0.03), offsets=None, seed=7, lat0=36.1, lon0=-115.1, epoch=None):
    """Cameras standing at `sites` on a map about (lat0, lon0), all reading every `every` s an object on a straight path
    through `at` (east, north at the middle of the span) at height h, velocity v and `climb`. `noise` (azimuth across
    the line of sight, elevation; deg) is each reading's own error, one pair for all or a pair a camera; `offsets` a
    constant (azimuth, elevation) added to each camera's angles; `epoch` a unix time for the first reading (else the
    times are seconds from zero). Returns (readings as `sightlines.read_sightlines` gives them, truth)."""
    rng = np.random.default_rng(seed)
    plane = drift.Plane(lat0, lon0)
    noise = np.broadcast_to(np.asarray(noise, float), (len(sites), 2))
    out, tm = [], seconds / 2
    for t in np.arange(0.0, seconds + 1e-9, every):
        ola, olo = plane.latlon(at[0] + v[0] * (t - tm), at[1] + v[1] * (t - tm))
        X = drift.ecef(float(ola), float(olo), h + climb * (t - tm))
        for i, (e, n, alt) in enumerate(sites):
            la, lo = plane.latlon(e, n)
            d = drift.enu_rows(float(la), float(lo)) @ (X - drift.ecef(float(la), float(lo), alt))
            el = math.atan2(d[2], math.hypot(d[0], d[1]))
            off = offsets[i] if offsets is not None else (0.0, 0.0)
            out.append(dict(time=(epoch or 0.0) + float(t), absolute=epoch is not None, camera=f"camera {chr(65 + i)}",
                            lat=float(la), lon=float(lo), alt=alt,
                            az=(math.degrees(math.atan2(d[0], d[1])) + off[0] + rng.normal(0, noise[i][0]) / math.cos(el)) % 360,
                            dep=-(math.degrees(el) + off[1] + rng.normal(0, noise[i][1]))))
    return out, dict(v=np.array(v, float), climb=climb, h=h)


def _from_deg(w):
    return (math.degrees(math.atan2(w[0], w[1])) + 180) % 360


def _soundings(w, heights=(3000.0, 4200.0)):
    """Two observed sources that bracket the object's height, their winds 1.2 and 1.4 m/s either side of `w`."""
    return [dict(source=name, height_m=z, from_deg=_from_deg(np.array(w) + d), speed_m_s=float(np.hypot(*(np.array(w) + d))))
            for name, d in (("sounding", np.array([0.9, -0.8])), ("profiler", np.array([-1.0, 1.0]))) for z in heights]


def test_cameras_a_drifter_and_a_flier_from_three_cameras():
    """Lines of sight with their own time and camera (`--rays`; method section 66): three cameras standing about 10 and
    2 km apart read a drawn object at the same instants. Their rays cross without any camera moving, so the path, T1
    and T2 come out as from an aircraft's turn, with no video and no frame rate."""
    print("\nT1/T2 from cameras on the ground: a drifter and a flier seen by three cameras at once")
    from mcdonald import sightlines
    rd, truth = cameras_scene(epoch=1779917405.25)
    R = sightlines.rays(rd)
    check(len(R["t"]) == 363 and len(set(R["t"].tolist())) == 121 and R["cameras"] == ("camera A", "camera B", "camera C")
          and np.bincount(R["camera"]).tolist() == [121] * 3 and R["epoch"] == 1779917405.0 and abs(R["t"][0] - 0.25) < 1e-6
          and all(k in R for k in ("frames", "t", "A", "az", "dep", "platform", "rot")),
          "363 readings, three at each of 121 instants, each with its camera; the times kept from their own clock",
          f"{len(R['t'])} readings, cameras {R['cameras']}")
    with resamples(200):
        found = drift.measure(None, sight=R, observed_winds=_soundings(truth["v"]), ground_m=600.0)
    T = {t["test"]: t for t in drift.flat(found.fields["tests"])}
    p = found.fields["ground_path"]
    miss = float(np.hypot(*(np.array(p["v_m_s"]) - truth["v"])))
    check(miss < 0.3 and miss <= 2 * p["velocity_err_m_s"] and abs(p["height_m"] - truth["h"]) < 30 and abs(p["climb_m_s"]) < 0.1,
          "the rays of three cameras fix the drifter's velocity, its height and its climb",
          f"{np.round(p['v_m_s'], 2).tolist()} of {truth['v'].tolist()}, two errors {2 * p['velocity_err_m_s']:.2f}; "
          f"{p['height_m']:.0f} m; climb {p['climb_m_s']:+.2f} m/s")
    check(p["places"] == 3 and 10000 < p["baseline_m"] < 10500 and 30 < p["los_cross_deg"] < 120 and p["los_turn_deg"] < 10
          and [c["name"] for c in p["cameras"]] == list(R["cameras"]) and p["reference"] == "camera"
          and p["time_utc"] == "2026-05-27T21:30:35" and found.fields["winds_when"] == p["time_utc"],
          "the path says where the rays came from: three places 10 km apart at most, lines of sight that cross at tens of "
          "degrees though none turned, and the rays' own mean time",
          f"{p['places']} places, {p['baseline_m']:.0f} m, crossing at {p['los_cross_deg']:.0f} deg, {p['time_utc']}")
    check(T["T1"]["outcome"] == drift.PASS and T["T2"]["outcome"] == drift.PASS and "aircraft_wind" not in T["T2"]
          and found.fields["verdict"].startswith("consistent"),
          "the drifter: T1 and T2 pass against winds that bracket its height, and no aircraft's own wind is looked for",
          T["T2"]["reading"][:110])
    rd, tr = cameras_scene(v=(8.0 + 20.0, 3.0 - 15.0), climb=1.5)
    with resamples(200):
        found = drift.measure(None, sight=sightlines.rays(rd), observed_winds=_soundings(truth["v"]), ground_m=600.0)
    T = {t["test"]: t for t in drift.flat(found.fields["tests"])}
    check(T["T2"]["outcome"] == drift.FAIL and found.fields["verdict"] == "not drifting" and "it flies" in T["T2"]["reading"],
          "a flier at 25 m/s through the same air: T2 fails, not drifting", T["T2"]["reading"][:110])
    text = "\n".join(drift.said(found.fields))
    check("of 3 cameras (camera A 121, camera B 121, camera C 121" in text and "aircraft" not in text and "display" not in text
          and "| camera B | 121 |" in text,
          "the printed lines name the cameras and their readings, and speak of no aircraft and no display")
    few = sightlines.rays(rd[:8])
    found = drift.measure(None, sight=few)
    check(len(few["t"]) == 8 and "at least 9 are needed" in found.fields["tests"][1]["reading"],
          "eight readings are too few, as they are from an aircraft", found.fields["tests"][1]["reading"][:60])


def test_cameras_one_camera_cannot_range_what_it_sees():
    """The bearings-only problem for a camera on a roof: any path scaled along its rays fits as well. The path gate and
    the range's bound are the aircraft route's, read for cameras, and their words must fit: no aircraft flew."""
    print("\nT1/T2 from cameras on the ground: rays from one place fix nothing")
    from mcdonald import sightlines
    rd, truth = cameras_scene()
    winds = _soundings(truth["v"])
    one = sightlines.rays([r for r in rd if r["camera"] == "camera A"])
    with resamples(200):                                      # refused either way; on a path the gate refuses each
        found = drift.measure(None, sight=one, observed_winds=winds)      # resample is slow (IDEAS.md N14)
    T = {t["test"]: t for t in drift.flat(found.fields["tests"])}
    p = found.fields["ground_path"]
    check(T["T1"]["outcome"] == drift.CANNOT and T["T2"]["outcome"] == drift.CANNOT and found.fields["verdict"] == "cannot say"
          and "One camera standing still cannot range what it sees" in T["T2"]["reading"] and "all 121 lines of sight start from one place" in T["T1"]["reading"]
          and p["places"] == 1 and p["path_off_line_m"] < 1e-6 and not p["path_gate"],
          "one camera standing still: T1 and T2 cannot say, and say why", T["T2"]["reading"])
    text = "\n".join(drift.said(found.fields))
    check("aircraft" not in text and "flew" not in text and "all from one place" in text,
          "in words that fit a camera on a roof: no aircraft, no flight")
    near = sightlines.rays(cameras_scene(sites=((0.0, 0.0, 700.0), (25.0, 0.0, 700.0)))[0])
    with resamples(200):
        found = drift.measure(None, sight=near, observed_winds=winds)
    t2, p = found.fields["tests"][1], found.fields["ground_path"]
    check(t2["outcome"] == drift.CANNOT and "so nearly one place" in t2["reading"] and p["places"] == 2 and 12 < p["path_off_line_m"] < 13,
          "two cameras 25 m apart: within the path gate's 20 m of one place, refused", t2["reading"][:130])
    # 45 m apart, 8 km from the object: the path gate opens, the rays cross at a third of a degree and scatter by a
    # tenth of that, so the rays alone would fix a range; each camera's own pointing (0.3 deg) does not allow one
    pair = sightlines.rays(cameras_scene(sites=((0.0, 0.0, 700.0), (45.0, 0.0, 700.0)))[0])
    p = drift.fit_track(pair, nboot=100)
    t2 = drift.test_wind_track(p, [dict(label="w", w=truth["v"], counts=True, note="")])
    check(p["path_gate"] and p["range_bound_rays"] < 0.3 and p["range_bound"] > drift.RANGE_FIX and t2["outcome"] == drift.CANNOT
          and "do not fix its range" in t2["reading"] and "The cameras stand 45 m apart" in t2["reading"]
          and "Each camera's pointing is taken as known to 0.3 deg" in t2["reading"],
          "two cameras 45 m apart: their rays' scatter alone would give a range, each camera's own pointing does not; the "
          "range's bound counts it, and T2 cannot say", f"bound {p['range_bound']:.2f} (the rays alone {p['range_bound_rays']:.3f}); "
          + t2["reading"][:100])
    exact = drift.fit_track(pair, nboot=100, pointing_err=(0.002, 0.002))
    check(exact["range_bound"] < drift.RANGE_FIX and drift.unfixed(exact) is None,
          "the same pair with its pointing known a hundred times better: the range is fixed", f"bound {exact['range_bound']:.3f}")


def test_cameras_each_cameras_own_pointing_is_carried():
    """An aircraft's rays share one azimuth reference, and `az_reference` carries one constant. Calibrated cameras each
    have their own pointing error, in azimuth and in elevation, and two cameras' errors change the angle at which their
    rays cross: on two cameras 2 km apart, 10 km from the object, that is the range itself. Rays drawn with a known
    constant error of each camera must move the path by the pull the fit reports, and the errors must hold the truth
    with each camera's pointing allowed for, and not with one shared reference."""
    print("\nT1/T2 from cameras on the ground: each camera's own pointing error is carried")
    from mcdonald import sightlines
    two = (SITES[1], SITES[2])
    rd, truth = cameras_scene(sites=two)
    R = sightlines.rays(rd)
    p = drift.fit_track(R, nboot=0)
    exact = drift.fit_track(R, nboot=0, pointing_err=(1e-9, 1e-9))
    wide = drift.fit_track(R, nboot=0, pointing_err=(1.0, 1.0))
    check(p["pointing_known_deg"] == [0.3, 0.1] and abs(exact["velocity_err_m_s"] - exact["velocity_err_rays_m_s"]) < 1e-6
          and exact["velocity_err_m_s"] < p["velocity_err_m_s"] < wide["velocity_err_m_s"]
          and p["velocity_err_rays_m_s"] == exact["velocity_err_rays_m_s"] and "az_reference_err_deg" not in p,
          "by default each camera's pointing is as well known as one of its readings is given to be (0.3 and 0.1 deg): the "
          "velocity's error lies between pointing taken as exact and pointing known to a degree",
          f"{exact['velocity_err_m_s']:.3f} < {p['velocity_err_m_s']:.3f} < {wide['velocity_err_m_s']:.3f} m/s")
    check(np.allclose(p["v_m_s"], exact["v_m_s"]) and np.allclose(p["v_m_s"], wide["v_m_s"]) and p["height_m"] == wide["height_m"],
          "the path itself does not move with what is known of the pointing")
    B = p["cameras"][1]
    for j, (angle, add) in enumerate((("azimuth", 0.5), ("elevation", 0.3))):
        off = [(0.0, 0.0), (add, 0.0) if j == 0 else (0.0, add)]
        q = drift.fit_track(sightlines.rays(cameras_scene(sites=two, offsets=off)[0]), nboot=0)
        moved = float(np.hypot(*(np.array(q["v_m_s"]) - np.array(p["v_m_s"])))) / add
        check(B["pull_m_s"][j] > 0.3 and abs(moved / B["pull_m_s"][j] - 1) < 0.15,
              f"camera B's {angle}s {add} deg off: the velocity moves by the pull the fit reports for a degree of it",
              f"{moved:.2f} m/s a degree against {B['pull_m_s'][j]:.2f}")
    off = [(0.25, -0.08), (-0.2, 0.09)]                        # within what is taken as known, and against each other
    rdo = cameras_scene(sites=two, offsets=off)[0]
    own = drift.fit_track(sightlines.rays(rdo), nboot=200)
    one = drift.fit_track(sightlines.rays(rdo, reference="shared"), nboot=200)
    dh = abs(own["height_m"] - truth["h"])
    check(100 < dh <= 2 * own["height_err_m"] and dh > 2 * own["height_err_rays_m"]
          and float(np.hypot(*(np.array(own["v_m_s"]) - truth["v"]))) <= 2 * own["velocity_err_m_s"],
          "each camera's pointing off by its own quarter of a degree: the height is 200 m out, and two errors hold it, and "
          "the velocity; the rays' scatter alone would not have", f"{dh:.0f} m out, two errors {2 * own['height_err_m']:.0f} (the rays' "
          f"alone {2 * own['height_err_rays_m']:.0f})")
    check(np.allclose(one["v_m_s"], own["v_m_s"]) and one["height_m"] == own["height_m"] and dh > 2 * one["height_err_m"]
          and "pointing_known_deg" not in one and one["az_reference_known_deg"] == 0.3 and one["reference"] == "shared",
          "the same rays read with one azimuth reference for both cameras (an aircraft's model): the same path, and two "
          "errors that do not hold its height", f"{dh:.0f} m out, two errors {2 * one['height_err_m']:.0f}")
    tight = (0.03, 0.03)                                       # the errors given as the scatter drawn: the velocity too
    own = drift.fit_track(sightlines.rays(rdo), tight, nboot=200, pointing_err=(0.3, 0.1))
    one = drift.fit_track(sightlines.rays(rdo, reference="shared"), tight, nboot=200, az_ref_err=0.3)
    miss = float(np.hypot(*(np.array(own["v_m_s"]) - truth["v"])))
    check(2 * one["velocity_err_m_s"] < miss <= 2 * own["velocity_err_m_s"],
          "with the errors given equal to the scatter drawn, the velocity too: held with each camera's own pointing, not "
          "with one shared reference", f"{miss:.2f} m/s off, two errors {2 * own['velocity_err_m_s']:.2f} against "
          f"{2 * one['velocity_err_m_s']:.2f}")
    # coverage: 40 pairs of cameras, each camera's offsets drawn at what is taken as known (0.3 and 0.1 deg). The
    # measurement is method section 66's (400 draws of each of three layouts); the 40 here are a guard on it
    hit = total = high = shared_high = 0
    rng = np.random.default_rng(66)
    for seed in range(40):
        offs = [(rng.normal(0, 0.3), rng.normal(0, 0.1)) for _ in two]
        rds, tr = cameras_scene(sites=two, offsets=offs, seed=200 + seed, every=1.0)
        f = drift.fit_track(sightlines.rays(rds), nboot=0)
        g = drift.fit_track(sightlines.rays(rds, reference="shared"), nboot=0)
        for got, want, err in ((f["v_m_s"][0], tr["v"][0], f["v_err_m_s"][0]), (f["v_m_s"][1], tr["v"][1], f["v_err_m_s"][1]),
                               (f["climb_m_s"], tr["climb"], f["climb_err_m_s"]), (f["height_m"], tr["h"], f["height_err_m"])):
            total += 1
            hit += abs(got - want) <= 2 * err
        high += abs(f["height_m"] - tr["h"]) <= 2 * f["height_err_m"]
        shared_high += abs(g["height_m"] - tr["h"]) <= 2 * g["height_err_m"]
    check(0.85 * total <= hit and high >= 34 and shared_high < 20,
          "over 40 drawn pairs two such errors hold the true velocity, climb and height as often as two errors should (85 "
          "of 100 at the least over these 40); with one shared reference the height is held on fewer than half",
          f"{hit} of {total}; the height on {high} of 40 with each camera's own pointing, {shared_high} with one shared reference")
    own = drift.fit_track(sightlines.rays(rdo), nboot=100)
    t2 = drift.test_wind_track(dict(own, velocity_err_m_s=3.0, velocity_err_rays_m_s=1.0, velocity_err_pointing_m_s=2.83),
                               [dict(label="w", w=truth["v"], counts=True, note="")])
    check(t2["outcome"] == drift.CANNOT and "Each camera's pointing is taken as known to 0.3 deg in azimuth and to 0.1 deg in elevation" in t2["reading"]
          and "An error of one degree at camera" in t2["reading"] and "display" not in t2["reading"],
          "a velocity the rays' scatter would fix and the pointing leaves open: cannot say, naming the camera it hangs on",
          t2["reading"][:170])
    free = drift.fit_track(R, nboot=0, pointing_err=(float("inf"), float("inf")))
    check(not math.isfinite(free["velocity_err_m_s"]) or 2 * free["velocity_err_m_s"] > drift.VELOCITY_FIX,
          "nothing taken as known of two cameras' pointing: their rays cannot read it themselves, and the velocity is open",
          f"two errors {2 * free['velocity_err_m_s']:.1f} m/s")
    text = "\n".join(drift.said(dict(tests=[], verdict="", why="", ground_path=dict(own, above_ground_m=None))))
    check("Each camera's pointing is taken as known to 0.3 deg in azimuth and to 0.1 deg in elevation beforehand" in text
          and "read each camera's pointing as" in text and "one degree of its azimuth" in text,
          "and the command's own words give what is taken as known, each camera's pull and what the rays alone would give")


def test_cameras_each_cameras_own_scatter():
    """`own_scatter`'s rule, camera by camera: cameras differ (their pixels, their range, what part of the object each
    sees), and one pooled scatter gives a quiet camera a noisy one's errors."""
    print("\nT1/T2 from cameras on the ground: each camera's rays have their own scatter")
    from mcdonald import sightlines
    drawn = ((0.02, 0.02), (0.08, 0.06), (0.5, 0.2))           # against the 0.3 and 0.1 deg given: far better, better, worse
    rd, truth = cameras_scene(noise=drawn)
    p = drift.fit_track(sightlines.rays(rd), nboot=0)
    A, B, C = p["cameras"]
    check(A["errors_from"] == "the rays' own scatter" and B["errors_from"] == "the rays' own scatter"
          and all(0.75 < s / d < 1.35 for c, dr in ((A, drawn[0]), (B, drawn[1])) for s, d in zip(c["sigma_deg"], dr))
          and p["errors_from"] == "each camera's own",
          "two cameras whose rays fit better than the errors given allow: each read with its own scatter, the scatter it "
          "was drawn with", f"A {A['sigma_deg'][0]:.3f}, {A['sigma_deg'][1]:.3f} of {drawn[0]}; B {B['sigma_deg'][0]:.3f}, "
          f"{B['sigma_deg'][1]:.3f} of {drawn[1]}")
    check(C["errors_from"].startswith("the errors given, scaled up") and C["sigma_deg"][0] > 0.4 and C["chi2_p_low"] is None,
          "a third whose rays fit worse than the errors given: its errors scaled up by its own misfit, the others' not",
          f"C {C['sigma_deg'][0]:.3f}, {C['sigma_deg'][1]:.3f} of {drawn[2]}")
    same = drift.fit_track(sightlines.rays(cameras_scene(noise=(0.28, 0.093), seed=3)[0]), nboot=0)
    check(same["errors_from"] == "the errors given" and all(c["sigma_deg"] == [0.3, 0.1] for c in same["cameras"]),
          "rays drawn with nearly the errors given: they stand, for every camera")
    # coverage where the cameras differ: each camera's scatter drawn from 0.015, 0.05 and 0.15 deg, no offsets
    hit = total = 0
    rng = np.random.default_rng(67)
    for seed in range(30):
        ns = [(s, s) for s in rng.choice((0.015, 0.05, 0.15), 3)]
        rds, tr = cameras_scene(noise=ns, seed=300 + seed, every=1.0)
        f = drift.fit_track(sightlines.rays(rds), nboot=0, pointing_err=(1e-9, 1e-9))
        for k, (got, want) in enumerate(((f["v_m_s"][0], tr["v"][0]), (f["v_m_s"][1], tr["v"][1]), (f["climb_m_s"], tr["climb"]))):
            total += 1
            hit += abs(got - want) <= 2 * (f["v_err_m_s"][k] if k < 2 else f["climb_err_m_s"])
    check(0.85 * total <= hit, "over 30 drawn scenes with unlike cameras two such errors hold the truth as often as two "
          "errors should (85 of 100 at the least over these 30)", f"{hit} of {total}")
    # a camera with few readings: which camera read how often is the design, so the bootstrap resamples each camera's
    # own. Drawn from all 126 readings alike, 1 resample in 160 holds none of camera B's 5 and is one camera's fit
    rd2, _ = cameras_scene(sites=(SITES[0], SITES[1]))
    few = sightlines.rays([r for j, r in enumerate(rd2) if r["camera"] == "camera A" or (j // 2) % 30 == 0])
    cov, boot = drift.fit_track(few, nboot=0), drift.fit_track(few, nboot=400)
    check(np.bincount(few["camera"]).tolist() == [121, 5] and boot["boots"] == 400
          and boot["velocity_err_rays_m_s"] < 4 * cov["velocity_err_rays_m_s"] and boot["height_err_rays_m"] < 5 * cov["height_err_rays_m"],
          "a camera with five readings beside one with 121: every resample keeps five of its readings, and the bootstrap's "
          "errors are near the covariance's, not ten and forty times them", f"velocity {boot['velocity_err_rays_m_s']:.2f} against "
          f"{cov['velocity_err_rays_m_s']:.2f} m/s, height {boot['height_err_rays_m']:.1f} against {cov['height_err_rays_m']:.1f} m")


def _write_rays(td, rd, when=True):
    """The readings as a rays file and a cameras file: ISO times, elevations, the cameras' places apart."""
    from datetime import datetime, timezone
    rays, cams = Path(td) / "rays.csv", Path(td) / "cameras.csv"
    lines = ["# a drawn object seen by cameras on the ground", "time_utc,camera,az_deg,el_deg"]
    for r in rd:
        t = datetime.fromtimestamp(r["time"], tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        lines.append(f"{t},{r['camera']},{r['az']:.7f},{-r['dep']:.7f}")
    rays.write_text("\n".join(lines) + "\n", encoding="utf-8")
    seen = {}
    for r in rd:
        seen.setdefault(r["camera"], (r["lat"], r["lon"], r["alt"]))
    cams.write_text("camera,lat,lon,alt_m\n" + "".join(f"{k},{la:.8f},{lo:.8f},{al:.3f}\n" for k, (la, lo, al) in seen.items()),
                    encoding="utf-8")
    return rays, cams


def test_cameras_by_the_command_line_with_no_video():
    """`mcdonald drift --rays rays.csv --cameras cameras.csv`: no video is given, since nothing here is timed by a
    video's frames; the winds' hours come from the rays' own times. And the calls that do need a frame rate say so."""
    print("\nT1/T2 from cameras on the ground: by the command line, with no video")
    from mcdonald import sightlines
    rd, truth = cameras_scene(epoch=1779917405.25)
    env = dict(__import__("os").environ, PYTHONPATH=str(reference_data.REPO / "src"))
    kn = float(np.hypot(*truth["v"])) / drift.KN
    with tempfile.TemporaryDirectory() as td:
        rays, cams = _write_rays(td, rd)
        back = sightlines.read_sightlines(rays, sightlines.read_cameras(cams))
        check(len(back) == len(rd) and all(abs(a["time"] - b["time"]) < 2e-3 and a["camera"] == b["camera"] and abs(a["dep"] - b["dep"]) < 1e-6
                                           and abs(a["lat"] - b["lat"]) < 1e-7 for a, b in zip(back, rd)) and back[0]["absolute"],
              "a rays file with ISO times and elevations, the cameras' places in a file of their own: read back as written")
        rows = Path(td) / "rows.csv"                           # unix times, depressions, the places in the rows
        rows.write_text("t_unix_s,camera,az_deg,dep_deg,lat,lon,alt_m\n" + "".join(
            f"{r['time']:.6f},{r['camera']},{r['az']:.7f},{r['dep']:.7f},{r['lat']:.8f},{r['lon']:.8f},{r['alt']:.3f}\n"
            for r in rd), encoding="utf-8")
        again = sightlines.read_sightlines(rows)
        check(all(abs(a["time"] - b["time"]) < 1e-5 and abs(a["az"] - b["az"]) < 1e-6 and a["alt"] == b["alt"] for a, b in zip(again, rd))
              and abs(sightlines._unix("2026-05-27T23:30:05.25+02:00") - 1779917405.25) < 1e-6
              and abs(sightlines._unix("2026-05-27 21:30:05.25") - 1779917405.25) < 1e-6,
              "the same with unix times, depressions and each camera's place in its rows; an ISO time with a zone, or with "
              "none (taken as UTC), is the same instant")
        try:
            sightlines.read_sightlines(rays)
            said = ""
        except ValueError as ex:
            said = str(ex)
        check("no place for the camera 'camera A'" in said, "rays with no place for a camera, in the rows or in a cameras "
              "file: refused, naming the camera", said[-70:])
        wind = Path(td) / "model.json"                         # the drifter's wind in the two hours about the rays' time,
        hours = ["2026-05-27T20:00", "2026-05-27T21:00", "2026-05-27T22:00", "2026-05-28T03:00"]   # 30 kn more in the others
        wind.write_text(json.dumps({"elevation": 600.0, "hourly": {
            "time": hours, "wind_speed_700hPa": [kn + 30, kn, kn, kn + 30], "wind_direction_700hPa": [_from_deg(truth["v"])] * 4,
            "geopotential_height_700hPa": [3100.0] * 4, "wind_speed_600hPa": [kn + 30, kn, kn, kn + 30],
            "wind_direction_600hPa": [_from_deg(truth["v"])] * 4, "geopotential_height_600hPa": [4300.0] * 4}}), encoding="utf-8")
        cmd = [sys.executable, "-m", "mcdonald.cli", "drift", "--rays", str(rays), "--cameras", str(cams), "--winds", str(wind),
               "--ground-m", "600", "--out", str(Path(td) / "c"), "--json"]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
        d = json.loads(p.stdout) if p.stdout.strip().startswith("{") else None
        wrote = (Path(td) / "c_drift.json").exists()
        if check(p.returncode == 0 and d is not None and d["command"] == "drift" and wrote and d["clip"] is None
                 and "video" not in d["inputs"], "no video given: one envelope on stdout, the drift file written",
                 f"exit {p.returncode} {p.stderr[-300:]}"):
            T = {t["test"]: t for t in drift.flat(d["results"]["tests"])}
            g = d["results"]["ground_path"]
            check(T["T1"]["outcome"] == drift.PASS and T["T2"]["outcome"] == drift.PASS
                  and d["results"]["verdict"] == "consistent with wind-borne drift (tentative)" and len(g["cameras"]) == 3,
                  "T1 and T2 pass on the drifter; the verdict is tentative drift", T["T2"]["reading"][:100])
            check(T["T2"]["winds_counted"] == 2 and d["results"]["winds_when"] == "2026-05-27T21:30:35" == g["time_utc"]
                  and any("the lines of sight's own mean time, 2026-05-27T21:30:35 UTC" in ln for ln in d["results"]["said"]),
                  "the model's hours are those within one of the rays' own mean time: two of the file's four, with no --when",
                  f"{T['T2']['winds_counted']} winds counted, at {d['results']['winds_when']}")
        p = subprocess.run(cmd + ["--when", "2026-05-28T03:10:00"], capture_output=True, text=True, encoding="utf-8", env=env)
        d = json.loads(p.stdout) if p.stdout.strip().startswith("{") else {}
        t2 = (d.get("results") or {}).get("tests", [{}, {}])[1]
        check(t2.get("outcome") == drift.FAIL and t2.get("winds_counted") == 1, "a --when given still decides the hour: "
              "against the wind of another hour the same object fails", str(t2.get("reading"))[:80])
        p = subprocess.run(cmd[:8] + ["--reference", "shared", "--json"], capture_output=True, text=True, encoding="utf-8", env=env)
        d = json.loads(p.stdout) if p.stdout.strip().startswith("{") else {}
        g = (d.get("results") or {}).get("ground_path") or {}
        check(g.get("reference") == "shared" and g.get("az_reference_known_deg") == 0.3 and "pointing_known_deg" not in g
              and any("the cameras' shared azimuth reference" in ln for ln in d["results"]["said"]),
              "--reference shared: one azimuth reference for every camera, said as the cameras'")
        # what needs a frame rate says so, and what does not runs without a video
        g = PR_GOLDEN
        p = subprocess.run([sys.executable, "-m", "mcdonald.cli", "drift", "--platform", str(g / "platform.csv"), "--los",
                            str(g / "los.csv")], capture_output=True, text=True, encoding="utf-8", env=env)
        check(p.returncode != 0 and "give the video, or --fps" in p.stderr and "--platform" in p.stderr,
              "an aircraft's track without its video or --fps: refused, saying which inputs are timed by frames",
              p.stderr.strip()[-110:])
        p = subprocess.run([sys.executable, "-m", "mcdonald.cli", "drift", "--platform", str(g / "platform.csv"), "--los",
                            str(g / "los.csv"), "--fps", str(PR_FPS), "--ground-m", "72", "--json"],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        d = json.loads(p.stdout) if p.stdout.strip().startswith("{") else {}
        gp = (d.get("results") or {}).get("ground_path") or {}
        check(p.returncode == 0 and gp.get("readings") == 39 and 7.2 < gp.get("speed_m_s", 0) < 7.5 and "cameras" not in gp,
              "the same track with --fps and no video: the Puerto Rico path, as with the video", f"{gp.get('speed_m_s')}")
        p = subprocess.run([sys.executable, "-m", "mcdonald.cli", "drift", "--flicker", str(SB_GOLDEN / "flicker.json"), "--json"],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        d = json.loads(p.stdout) if p.stdout.strip().startswith("{") else {}
        check(p.returncode == 0 and (d.get("results") or {}).get("verdict") == "not drifting",
              "a flicker envelope alone needs no video: the Huey's held beat, not drifting")
        p = subprocess.run(cmd[:8] + ["--platform", str(g / "platform.csv"), "--los", str(g / "los.csv"), "--fps", "30"],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        check(p.returncode != 0 and "one of the three" in p.stderr, "--rays beside --platform: refused")


def test_cameras_the_aircrafts_route_is_untouched():
    """The route from an aircraft's own track must give what it gave: its rays carry no camera, its one azimuth
    reference is carried as before, and its words speak of the aircraft. And cameras written as one aircraft that jumps
    between them, a frame a reading (how several cameras went in before `--rays`), give the same path and errors as
    `--rays` with one shared reference and the same times: the two inputs are one fit."""
    print("\nT1/T2 from cameras on the ground: the aircraft's route untouched, and the two inputs one fit")
    from mcdonald import sightlines
    platform, los, truth = orbit()
    R = drift.rays(platform, los, FPS)
    p = drift.fit_track(R, (0.1, 0.03), nboot=100)
    check("camera" not in R and "cameras" not in p and "reference" not in p and "pointing_known_deg" not in p and "time_utc" not in p
          and p["az_reference_known_deg"] == 0.1 and p["errors_from"] == "the errors given" and p["los_turn_deg"] > 100,
          "an aircraft's rays: no camera in them, one azimuth reference carried, the fields as they were")
    said = "\n".join(drift.said(dict(tests=[], verdict="", why="", ground_path=dict(p, above_ground_m=None))))
    check("the aircraft's path left a straight line by" in said and "the display's azimuth reference" in said and "camera" not in said,
          "and its words speak of the aircraft and its display")
    sp, sl, _ = orbit(turn=False)
    t2 = drift.test_wind_track(drift.fit_track(drift.rays(sp, sl, FPS), (0.1, 0.03), nboot=100),
                               [dict(label="w", w=truth["v"], counts=True, note="")])
    check("the aircraft flew straight" in t2["reading"] and "a straight-flying aircraft cannot range what it sees" in t2["reading"],
          "a straight flight is refused in the aircraft's words, as before", t2["reading"][:60])
    # three cameras as one aircraft that jumps between them: the reading of camera i at step k on frame 3k + i + 1 at
    # three times the step's rate
    rd, tr = cameras_scene(every=0.5, offsets=[(0.1, 0.0), (-0.1, 0.05), (0.0, -0.05)])
    plat, lo2, shifted = {}, {}, []
    for j, r in enumerate(rd):
        k, i = divmod(j, 3)
        f = 3 * k + i + 1
        plat[f] = (r["lat"], r["lon"], r["alt"], None)
        lo2[f] = dict(az=r["az"], dep=r["dep"], tgt=None, off=(0.0, 0.0))
        shifted.append(dict(r, time=(f - 1) / 6.0))
    old = drift.fit_track(drift.rays(plat, lo2, 6.0), nboot=100, rng=np.random.default_rng(5))
    new = drift.fit_track(sightlines.rays(shifted, reference="shared"), nboot=100, rng=np.random.default_rng(5))
    keys = [k for k in old if k != "frames"]
    check(all(old[k] == new.get(k) for k in keys) and new["reference"] == "shared" and len(keys) > 40,
          "cameras written as one jumping aircraft, and the same rays by --rays with one shared reference: every number "
          "of the path the same", f"{sum(old[k] == new.get(k) for k in keys)} of {len(keys)} fields")
    true = drift.fit_track(sightlines.rays(rd, reference="shared"), nboot=100, rng=np.random.default_rng(5))
    dv = float(np.hypot(*(np.array(true["v_m_s"]) - np.array(old["v_m_s"]))))
    check(0 < dv < 0.01, "with each reading at its own time, not a third or two of a step late: the path moves, by under "
          "a hundredth of a m/s here", f"{dv:.5f} m/s")
    cam = drift.fit_track(sightlines.rays(rd), nboot=0)
    check(old["los_turn_deg"] > 30 and cam["los_turn_deg"] < 5 and 30 < cam["los_cross_deg"] < 120,
          "what the old way could not say: its \"turn\" of the line of sight is the jump between cameras; by --rays it is "
          "the most one camera's own line of sight turned, and the angle the cameras' lines cross at is a field of its own",
          f"{old['los_turn_deg']:.0f} deg; {cam['los_turn_deg']:.1f} deg, crossing at {cam['los_cross_deg']:.0f} deg")


def test_fliers_planted_from_cameras_of_their_own():
    """`--plant` where the case came through `--rays` (method sections 66 and 67; the two were built on branches apart,
    and the planted fliers had never been run on cameras until they met, 2026-11-17). Three drawn cameras, one of them
    three to four times poorer than the best. A plant's rays must be what section 67 says they are for cameras: the
    case's rays with the two angles alone replaced, so each keeps its camera; each ray's own miss about the fitted
    path kept at its own reading (so the poorer camera stays the poorer), its pair of misses under one sign drawn
    afresh, enlarged by sqrt(2n / (2n - 6)) -- which is each camera's own factor under section 66's rule, where a
    camera's share of the six parameters is its share of the readings. And each plant's fit must be handed the
    case's own options, the cameras' pointing error among them. The rays handed to every fit are caught on the way."""
    from mcdonald import fliers, sightlines
    print("\nPlanted fliers: on a case seen by cameras of their own (--rays)")
    rd, truth = cameras_scene(seconds=40.0, every=1.0, noise=((0.02, 0.02), (0.08, 0.06), (0.04, 0.03)))
    R = sightlines.rays(rd)
    n = len(R["t"])
    rng = np.random.default_rng(66)
    winds = [dict(label=f"wind {i}", w=truth["v"] + rng.normal(0, 0.5, 2), counts=True, note="") for i in range(4)]
    opt = dict(sig=(0.3, 0.1), ground_m=600.0, pointing_err=(0.05, 0.05))
    path = drift.fit_track(R, rng=np.random.default_rng(20261021), nboot=60, **opt)
    t2 = drift.test_wind_track(path, winds, readings=n)
    seen, real = [], drift.fit_track

    def spy(Rp, *a, **k):
        seen.append((Rp, dict(k)))
        return real(Rp, *a, **k)
    drift.fit_track = spy
    try:
        f = fliers.plant_track(R, path, winds, fit=opt, case_t2=t2, speeds=(10.0, 40.0), draws=2, nboot=60, procs=0)
    finally:
        drift.fit_track = real
    T = {t["airspeed_m_s"]: t for t in f.get("table", [])}
    if not check(t2["outcome"] == drift.PASS and f.get("plants") == 48 and len(seen) == 49 and f["route"] == "lines of sight"
                 and f["air"] == "path" and f["case_again"]["as_the_case"] is True,
                 "three cameras' rays fix the drifter and it passes T2; 48 bodies are planted in its own air, and the case "
                 "planted again comes out as the case", f"T2 {t2['outcome']}: {t2['reading'][:90]}; {f.get('sentence', f.get('why'))}"):
        return
    check(T[0.0]["passes"] >= 15 and T[40.0]["fails"] == 16 and T[10.0]["cannot_say"] == 16 and f["fails_from_m_s"] == 40.0,
          "from cameras as from an aircraft: a planted drifter passes (15 times in 16 or more), 40 m/s fails whichever way "
          "it flies, 10 m/s cannot be judged", f["sentence"])
    ca, cd = fliers.misses(R, path)
    grow = math.sqrt(2 * n / (2 * n - 6))
    q0 = np.asarray(path["params"], float)
    kept, paired, signs, cams_kept, opts_kept, poorer = [], [], [], [], [], []
    for (Rp, kw), row in zip(seen[1:], f["runs"]):
        th = math.radians(row["toward_deg"] or 0.0)
        q = q0.copy()
        q[3:5] = np.array(path["v_m_s"]) + row["airspeed_m_s"] * np.array([math.sin(th), math.cos(th)])
        ma, md = fliers.misses(Rp, dict(path, params=q.tolist()))          # the plant's rays about the path it was planted on
        kept.append(np.allclose(np.abs(ma), np.abs(ca) * grow, atol=1e-7) and np.allclose(np.abs(md), np.abs(cd) * grow, atol=1e-7))
        sa, sd = np.sign(ma * ca), np.sign(md * cd)
        paired.append(bool(np.all(sa == sd)))
        signs.append(tuple(sa.astype(int)))
        cams_kept.append(Rp["camera"] is R["camera"] and Rp["cameras"] == R["cameras"] and Rp["reference"] == "camera"
                         and set(Rp) == set(R))
        opts_kept.append(kw.get("pointing_err") == (0.05, 0.05) and kw.get("sig") == (0.3, 0.1) and kw.get("ground_m") == 600.0
                         and kw.get("nboot") == 60)
        rms = [float(np.sqrt(np.mean(ma[R["camera"] == c] ** 2 + md[R["camera"] == c] ** 2))) for c in range(3)]
        poorer.append(rms[1] > 1.5 * rms[2] > 1.5 * rms[0])
    case_rms = [float(np.sqrt(np.mean(ca[R["camera"] == c] ** 2 + cd[R["camera"] == c] ** 2))) for c in range(3)]
    first, kw0 = seen[0]
    check(np.allclose(first["az"], R["az"], atol=1e-9) and np.allclose(first["dep"], R["dep"], atol=1e-9) and first["camera"] is R["camera"]
          and kw0.get("pointing_err") == (0.05, 0.05),
          "the case planted again is the case's own rays, each with its camera, fitted with the case's own pointing error")
    check(all(cams_kept), "every plant's rays are the case's with the two angles alone replaced: each ray keeps its camera, "
          "the cameras their names and their own pointing")
    check(all(kept), f"every ray of every plant keeps its own miss at its own reading, enlarged by sqrt(2n / (2n - 6)) "
          f"({grow:.4f} at {n} rays)", f"{sum(kept)} of {len(kept)} plants")
    check(all(poorer) and case_rms[1] > 1.5 * case_rms[2] > 1.5 * case_rms[0],
          "so the poorer camera stays the poorer in every plant, as in the case",
          "the case's misses by camera, rms deg: " + ", ".join(f"{x:.3f}" for x in case_rms))
    frac = np.mean([np.mean(np.array(s) > 0) for s in signs])
    check(all(paired) and len(set(signs)) == len(signs) and 0.4 < frac < 0.6 and all(0.25 < np.mean(np.array(s) > 0) < 0.75 for s in signs),
          "a reading's two misses take one sign, drawn afresh for every plant: no two plants share their signs, and half "
          "of them are turned", f"{len(set(signs))} different draws of {len(signs)}; {frac:.2f} of the signs kept")
    check(all(opts_kept), "every plant's fit is handed the case's own options: the errors given, the ground, the cameras' "
          "pointing error and the count of resamples")
    one = dict(case_t2=t2, speeds=(), directions=1, draws=1, nboot=60, procs=0)
    usual = fliers.plant_track(R, path, winds, fit=opt, **one)["runs"][0]
    wide = fliers.plant_track(R, path, winds, fit=dict(opt, pointing_err=(1.0, 1.0)), **one)["runs"][0]
    check(wide["velocity_err_m_s"] > 3 * usual["velocity_err_m_s"] and wide["fitted_m_s"] == usual["fitted_m_s"],
          "and it is carried there: cameras whose pointing is known to a degree widen a plant's velocity error and move no "
          "fitted number", f"{usual['velocity_err_m_s']} -> {wide['velocity_err_m_s']} m/s")
    # through the stage and through the command line, with no video (60 resamples a fit: nothing here needs the 2,000)
    with resamples(60):
        kw = dict(sight=R, observed_winds=_soundings(truth["v"]), ground_m=600.0, pointing_err=(0.05, 0.05))
        plain = drift.measure(None, **kw)
        asked = drift.measure(None, plant=dict(speeds=(40.0,), directions=2, draws=1, procs=0), **kw)
        with tempfile.TemporaryDirectory() as td:
            import io
            rays, cams = _write_rays(td, rd)
            obs = Path(td) / "obs.csv"
            obs.write_text("source,height_m,from_deg,speed_m_s\n" + "".join(
                f"{w['source']},{w['height_m']},{w['from_deg']:.3f},{w['speed_m_s']:.3f}\n" for w in _soundings(truth["v"])),
                encoding="utf-8")
            argv, out = sys.argv, io.StringIO()
            sys.argv = ["mcdonald drift", "--rays", str(rays), "--cameras", str(cams), "--obs-winds", str(obs), "--ground-m", "600",
                        "--pointing-err", "0.05,0.05", "--plant", "--plant-speeds", "40", "--plant-draws", "1", "--procs", "0",
                        "--json"]
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                    rc = drift.main()
            finally:
                sys.argv = argv
    g = asked.fields.get("planted_fliers") or {}
    rest = {k: v for k, v in asked.fields.items() if k != "planted_fliers"}
    dump = lambda d: json.dumps(d, sort_keys=True, default=lambda o: o.tolist())            # noqa: E731
    check("planted_fliers" not in plain.fields and dump(rest) == dump(plain.fields) and asked.result == plain.result,
          "through the stage on cameras' rays: with `plant` every other field and every printed result is the same")
    lines = "\n".join(drift.said(asked.fields))
    t2s = asked.fields["tests"][1]
    check(g.get("route") == "lines of sight" and g.get("plants") == 4 and g["case_again"]["as_the_case"] is True and g["fails_from_m_s"] == 40.0
          and abs(g["case_again"]["tolerance_m_s"] - t2s["tolerance_m_s"]) <= fliers.AGAIN and t2s["velocity_err_m_s"] < 0.3
          and g["drifter"]["passes"] == 2 and g["sentence"] in lines and "not built yet" not in lines,
          "and the field holds the plants: the case again as the case, to its tolerance (which a fit without the cameras' "
          "own pointing error would move), a planted drifter passing, 40 m/s failing; the stage prints their sentence "
          "after the verdict", g.get("sentence", g.get("why", ""))[:160])
    d = json.loads(out.getvalue()) if out.getvalue().strip().startswith("{") else {}
    c = (d.get("results") or {}).get("planted_fliers") or {}
    Tc = {t["airspeed_m_s"]: t for t in c.get("table", [])}
    check(rc == 0 and d.get("clip") is None and c.get("plants") == 16 and Tc[0.0]["passes"] >= 7 and Tc[40.0]["fails"] == 8
          and c["case_again"]["as_the_case"] is True and len(d["results"]["ground_path"]["cameras"]) == 3
          and any("40 m/s or more through the air would have failed" in ln for ln in d["results"]["said"]),
          "`mcdonald drift --rays ... --plant`, with no video: 16 bodies planted on the three cameras' case, a drifter "
          "passes and 40 m/s fails in every direction", c.get("sentence", c.get("why", str(d)[:200])))


# ---------------------------------------------------------------- T3
def test_t3_the_flicker_stages_answers():
    print("\nT3: the beat")
    out = drift.test_beat({"results": {"beats": True, "finding": "a beat at 7.5 Hz"}})
    check(out["outcome"] == drift.FAIL, "a beat of its own: fails")
    held = {"results": {"beats": True, "finding": "it beats at 10.8 Hz over the whole track",
                        "beat": {"object": {"whole_passes": True, "comes_back": True, "windows_passing": 40,
                                            "windows": 50, "windows_apart": 9}}}}
    out = drift.test_beat(held)
    check(out["outcome"] == drift.FAIL and out["held"], "a beat that holds across the video (a rotor's): fails")
    stretch = {"results": {"beats": True, "finding": "it beats at 3.00 Hz ...; that is one stretch: the whole track does "
                                                     "not beat, and no window apart from it does",
                           "beat": {"object": {"whole_passes": False, "comes_back": False, "windows_passing": 1,
                                               "windows": 109, "windows_apart": 1}}}}
    out = drift.test_beat(stretch)
    check(out["outcome"] == drift.PASS and not out["held"] and "1 of 109" in out["reading"],
          "a beat in one stretch of many (a flame's, or chance) is not counted: passes on the whole stretch",
          out["reading"][:60])
    bare = {"results": {"beats": True, "finding": "it beats at 3 Hz; that is one stretch: the whole track does not beat"}}
    check(drift.test_beat(bare)["outcome"] == drift.PASS, "the same read from the finding where the envelope has no "
                                                          "beat record")
    out = drift.test_beat({"results": {"beats": False, "injection": {"analytic": {"with_floor": 0.41}}}})
    check(out["outcome"] == drift.PASS and out["smallest_beat_seen"] == 0.41 and "weak" not in out["reading"],
          "no beat: passes, with the smallest beat the injections show it could have seen")
    out = drift.test_beat({"results": {"beats": False, "noise_floor": 0.1}})
    from mcdonald.flicker import ABOVE
    check(out["outcome"] == drift.PASS and abs(out["smallest_beat_seen"] - round(ABOVE * 0.1, 2)) < 1e-9,
          "without injections, the smallest is the flicker rule's own threshold", f"{out['smallest_beat_seen']}")
    # an envelope out of `mcdonald run` or a case file has no injection run; it carries the track's own closed-form floor
    case = {"results": {"beats": False, "noise_floor": 0.0069, "analytic": {"object": {"amplitude": 0.084, "with_floor": 0.084}}}}
    out = drift.test_beat(case)
    check(out["outcome"] == drift.PASS and out["smallest_beat_seen"] == 0.08 and "over 8%" in out["reading"],
          "without injections but with the track's own floor (a case file's result): the smallest beat is the track's own, "
          "8 %, not three times the background's 0.7 % (PR097 object 4, as the stage read it until 2026-11-13: 2 %)",
          out["reading"])
    case["results"]["injection"] = {"analytic": {"with_floor": 0.3}}
    check(drift.test_beat(case)["smallest_beat_seen"] == 0.3, "an injection run's floor still comes first")
    bare = {"results": {"beats": False, "noise_floor": 0.1, "analytic": {"object": {"amplitude": 0.05, "with_floor": None}}}}
    check(abs(drift.test_beat(bare)["smallest_beat_seen"] - round(ABOVE * 0.1, 2)) < 1e-9,
          "a track's floor recorded without the background's part falls back to the rule's own threshold")
    check(drift.test_beat({"results": {"beats": None}})["outcome"] == drift.CANNOT, "no power: cannot say")
    check(drift.test_beat(None)["outcome"] == drift.CANNOT, "no flicker run: cannot say")


def _windows(n, passing_at=(), hz=2.4, frames=120):
    """n windows of `frames` that do not overlap, those indexed in `passing_at` passing at `hz`."""
    return [dict(first=1 + i * (frames + 1), last=1 + i * (frames + 1) + frames - 1, fundamental_hz=hz, hz=hz,
                 passes=i in passing_at) for i in range(n)]


def test_t3_windows_apart_against_chance():
    print("\nT3: windows apart weighed against chance (2026-11-13)")
    from mcdonald import flicker
    check(flicker.independent_windows(_windows(40)) == 40, "40 windows that do not overlap: 40")
    overlapping = [dict(first=1 + 15 * i, last=120 + 15 * i) for i in range(50)]
    check(flicker.independent_windows(overlapping) == 7, "50 windows an eighth apart over 855 frames: 7 that do not overlap",
          str(flicker.independent_windows(overlapping)))
    p2, p12 = flicker.windows_chance(2, 40, 2.4), flicker.windows_chance(12, 40, 2.4)
    check(p2 > 0.5 and p12 < 1e-3, "2 of 40 at the drift test's 9 % is chance; 12 of 40 is not", f"{p2:.2f}, {p12:.1e}")

    def env(apart, n=40, whole=False, new=False):
        b = dict(hz=2.4, amplitude=0.05, whole_passes=whole, comes_back=True, windows_passing=apart, windows=n,
                 windows_apart=apart)
        if new:
            b.update(windows_independent=n, windows_chance_p=flicker.windows_chance(apart, n, 2.4),
                     comes_back=whole or flicker.windows_chance(apart, n, 2.4) <= flicker.CHANCE_P)
        return {"results": {"beats": True, "finding": "it beats at 2.40 Hz", "noise_floor": 0.004,
                            "beat": {"object": b}, "windows": {"object": _windows(n, range(0, 2 * apart, 2))}}}
    out = drift.test_beat(env(2))
    check(out["outcome"] == drift.PASS and "as often as chance gives" in out["reading"] and out["windows_independent"] == 40,
          "an envelope from before: 2 windows apart of 40 is chance, passes (the Galileo clouds' case)", out["reading"][:110])
    check(drift.test_beat(env(12))["outcome"] == drift.FAIL, "12 windows apart of 40: beyond chance, fails")
    check(drift.test_beat(env(2, whole=True))["outcome"] == drift.FAIL, "a whole track that beats: fails, as before")
    check(drift.test_beat(env(2, new=True))["outcome"] == drift.PASS
          and drift.test_beat(env(12, new=True))["outcome"] == drift.FAIL, "the same from flicker's own new fields")
    # chance from the clip's own background windows (the N3 revision, 2026-11-13): a short track's two windows apart of
    # five are chance at the census's 9 %, and not where the clip's own background windows rarely pass (IR_BIRD_017)
    census, own = flicker.windows_chance(2, 5, 2.7), flicker.windows_chance(2, 5, 2.7, flicker.CHANCE_FLOOR)
    check(census > flicker.CHANCE_P >= own, "2 windows apart of 5: chance at the census's rate, beyond it at the floor",
          f"{census:.3f}, {own:.4f}")
    import numpy as np
    from mcdonald.progress import Beside
    rng = np.random.default_rng(7)
    fps, frames = 30.0, 150
    own_ = {f"background {i}": list(100.0 + rng.normal(0, 0.3, frames)) for i in range(3)}
    ns = list(range(1, frames + 1))
    bw = flicker.background_windows(Beside(0), own_, "object", sorted(own_), ns, fps, (), [], 0.8 * fps / 2, 100.0)
    n_each = len(flicker.windows({m: own_[m] for m in own_}, "background 0", ["background 1", "background 2"], ns, fps, (),
                                 top=0.8 * fps / 2, scale=100.0))
    check(bw is not None and bw[1] == 3 * n_each and bw[0] <= bw[1] // 10,
          "background windows: each aperture's windows judged as the object's, few passing on grain alone", str(bw))
    check(flicker.background_windows(Beside(0), own_, "object", ["background 0"], ns, fps, (), [], 12.0, 100.0) is None,
          "one aperture alone has nothing to be held against: no measured chance")


def test_t3_two_cameras():
    print("\nT3 from two cameras watching at the same time (2026-11-13)")

    def env(hz, amp, floor, held=True, beats=True, video="cam.mp4"):
        b = dict(hz=hz, amplitude=amp, whole_passes=held, comes_back=held, windows_passing=10, windows=40,
                 windows_apart=5 if held else 1)
        return {"clip": {"video": video}, "results": {"beats": beats, "finding": f"it beats at {hz:.2f} Hz",
                                                      "noise_floor": floor / 3.0, "beat": {"object": b}}}
    a = env(2.44, 0.05, 0.01, video="hideout-cam-1.mp4")
    out = drift.test_beat_cameras([a, env(3.2, 0.006, 0.01, held=False, beats=False, video="sphere-cam-2.mp4")])
    check(out["outcome"] == drift.PASS and "its own view" in out["reading"] and out["cameras"] == 2,
          "a beat one camera sees and another, able to see a third of it, does not: that camera's view, passes",
          out["reading"][:130])
    out = drift.test_beat_cameras([a, env(2.47, 0.03, 0.01, held=False, video="w.mp4")])
    check(out["outcome"] == drift.FAIL and "sees 2.47 Hz" in out["reading"], "another camera agrees: fails",
          out["reading"][-80:])
    out = drift.test_beat_cameras([a, env(2.45, 0.008, 0.02, held=False, video="w.mp4")])
    check(out["outcome"] == drift.FAIL and "could have seen" in out["reading"],
          "another camera too noisy to see a third of it (the Galileo cloud at 5 % and 0.8 %, floor 2 %): fails as before",
          out["reading"][-80:])
    check(drift.test_beat_cameras([a])["outcome"] == drift.test_beat(a)["outcome"], "one envelope: test_beat's own answer")
    # The other camera's floor is compared as the envelope gives it, not rounded to whole per cents (2026-11-17, IDEAS.md
    # N11: `smallest_beat_seen` is rounded for the reading, and the lines the Galileo clouds' cameras were held to are
    # 1.3-1.8 %). A held beat of 4 %: a third of it is 1.33 %. A camera whose floor is 1.4 % could not have seen that
    # (rounded, its floor read 1 % and it took the beat back); one whose floor is 1.3 % could.
    b = env(3.0, 0.04, 0.01, video="one.mp4")
    blind = drift.test_beat_cameras([b, env(3.0, 0.002, 0.014, held=False, beats=False, video="two.mp4")])
    sees = drift.test_beat_cameras([b, env(3.0, 0.002, 0.013, held=False, beats=False, video="two.mp4")])
    check(blind["outcome"] == drift.FAIL and "no other camera could have seen a beat a third as strong" in blind["reading"]
          and sees["outcome"] == drift.PASS and "a beat of 1.3% would have shown" in sees["reading"],
          "a 4 % beat and another camera whose floor is 1.4 %: it could not have seen a third of it (1.33 %), so the beat "
          "stays and T3 fails; at 1.3 % it could, and takes it back", blind["reading"][-70:])
    c = env(3.0, 0.046, 0.01, video="one.mp4")                # a third of it is 1.53 %
    near = drift.test_beat_cameras([c, env(3.0, 0.002, 0.0152, held=False, beats=False, video="two.mp4")])
    check(near["outcome"] == drift.PASS and drift.test_beat(env(3.0, 0.002, 0.0152, held=False, beats=False))["smallest_beat_seen"] == 0.02,
          "a 4.6 % beat and a floor of 1.52 %: it could have seen a third (1.53 %) and takes the beat back; rounded for "
          "the reading that floor is 2 %, which until then kept the beat", near["reading"][:120])


def _heard(top, rate=None, held=0.0, fps=60.0, every=None, blocks=None, beats=False, floor=0.01, video=None, **more):
    """A drawn `flicker` envelope that records the band it listened in, as every one since 0.4.0 does: `top_hz`, and
    `pictures` with whether its frames were read as a cadence. `rate`: the pictures a second of a cadence (the band's
    top is then `top`, under the frame rate's); None for a video whose clock is its frame rate."""
    pic = dict(rate=fps if rate is None else rate, held=held, top_hz=top, holds="cadence" if rate else "none",
               cadence=rate is not None, slope=None if rate is None else 1 - rate / fps, every=every)
    if blocks:                                           # a cadence by most of its blocks: the rate from their slope
        pic.update(slope=0.9 * (1 - rate / fps), blocks=dict(of=blocks[1], cadence=blocks[0], slope=1 - rate / fps))
    r = dict(beats=beats, finding="no beat reaches 3 times what the background beside it does", noise_floor=floor / 3.0,
             top_hz=top, pictures=pic, **more)
    return dict(results=r, **({"clip": {"video": video}} if video else {}))


def test_t3_says_the_band_it_listened_in():
    """The maintainer's decision of 2026-11-17, "say the band in words". `flicker` listens for a beat between 1.5 Hz and
    0.8 of the Nyquist frequency of the frame rate -- or of the picture rate, where the frames were read as a cadence.
    On 98 of the Galileo Project's 494 clips with power that is about 5 Hz of the 24 the frame rate carries, and T3 said
    "passes: no beat of its own" of them as of the rest. Every pass now names its band; a band cut short says how far,
    that faster beats were not listened for, what was measured that cut it and the two things that make it. An envelope
    that does not record the band reads as it did. No outcome and no number reads the band: drawn envelopes here, each
    judged with the record and without."""
    print("\nT3 says the band it listened in (2026-11-17)")
    bare = lambda e: {"results": {k: v for k, v in e["results"].items() if k not in ("top_hz", "pictures")}}
    same = lambda a, b: {k: v for k, v in a.items() if k != "reading"} == {k: v for k, v in b.items() if k != "reading"}
    full, cut = _heard(24.0), _heard(4.84, rate=12.1, held=0.78)
    t, was = drift.test_beat(full), drift.test_beat(bare(full))
    check(t["reading"] == "no beat of its own between 1.5 and 24.0 Hz; only a beat over 1% of its brightness would have shown"
          and was["reading"] == "no beat of its own; only a beat over 1% of its brightness would have shown" and same(t, was),
          "a video whose clock is its frame rate: the pass names the whole band, 1.5 to 24.0 Hz, and nothing else moves",
          t["reading"])
    t, was = drift.test_beat(cut), drift.test_beat(bare(cut))
    check(t["reading"].startswith("no beat of its own between 1.5 and 4.8 Hz; only a beat over 1% of its brightness would have "
                                  "shown. Faster beats, up to the 24.0 Hz this frame rate could carry, were not listened for. "
                                  "78% of the frames nearly repeat the one before in a steady pattern, so the picture is new "
                                  "only 12.1 times a second. A source that delivers pictures at that rate does this. So does "
                                  "compression that copies a still scene from frame to frame")
          and t["reading"].endswith("This test cannot tell which, so a beat faster than 4.8 Hz may have gone unheard")
          and t["outcome"] == drift.PASS and same(t, was),
          "frames read as a cadence of 12.1 pictures a second on 60: the pass covers 1.5 to 4.8 Hz and says so, that beats up "
          "to 24.0 Hz were not listened for, what was measured, and both things that make it", t["reading"])
    check(was["reading"] == "no beat of its own; only a beat over 1% of its brightness would have shown"
          and drift.beat_band(bare(cut)) is None and drift.beat_band(None) is None
          and drift.beat_band({"results": dict(cut["results"], pictures={k: v for k, v in cut["results"]["pictures"].items()
                                                                         if k != "cadence"})}) is None,
          "an envelope that records no band (no top_hz, or no word for how its pictures fall) reads as it did: none is guessed",
          was["reading"])
    t = drift.test_beat(_heard(8.0, rate=20.0, held=0.39, fps=30.0, blocks=(4, 5)))
    two = drift.test_beat(_heard(11.99, rate=29.97, held=0.5, fps=59.94, every=[1, 2]))
    check("up to the 12.0 Hz this frame rate could carry" in t["reading"]
          and "in a steady pattern over most of the track (4 of its 5 stretches of about 60 frames)" in t["reading"]
          and "between 1.5 and 12.0 Hz;" in two["reading"] and "up to the 24.0 Hz this frame rate could carry" in two["reading"]
          and "in a steady pattern (1 of every 2), so the picture is new only 30.0 times a second" in two["reading"],
          "a cadence by most of its blocks says where it holds, and one with a period names it (PR051's doubled source)",
          two["reading"][70:260])
    one = dict(whole_passes=False, comes_back=False, windows_passing=1, windows=109, windows_apart=1)
    stretch = _heard(4.84, rate=12.1, held=0.78, beats=True, beat={"object": one})
    stretch["results"]["finding"] = "it beats at 3.00 Hz; that is one stretch: the whole track does not beat"
    t, was = drift.test_beat(stretch), drift.test_beat(bare(stretch))
    check(t["reading"].startswith("no beat across the video between 1.5 and 4.8 Hz: a beat in one stretch only (1 of 109 windows)")
          and t["reading"].endswith("so a beat faster than 4.8 Hz may have gone unheard") and same(t, was)
          and was["reading"].startswith("no beat across the video: a beat in one stretch only"),
          "a pass on a beat in one stretch says its band too", t["reading"][:90])
    beat = _heard(24.0, beats=True, beat={"object": dict(one, whole_passes=True, comes_back=True)})
    t = drift.test_beat(beat)
    check(t["outcome"] == drift.FAIL and "between" not in t["reading"] and t["reading"] == drift.test_beat(bare(beat))["reading"],
          "a fail is not a pass: its reading is the beat, as before")
    refused = _heard(24.0, beats=None)
    check(drift.test_beat(refused)["reading"] == "the flicker test had no power on this clip", "nor is a test with no power")
    # several cameras: the reading names its first passing camera's band, as it names its floor, then each camera's
    # where they differ, and why for one cut short
    a, b, c = _heard(4.84, rate=12.1, held=0.78, video="hideout-1.mp4"), _heard(24.0, floor=0.02, video="sphere-2.mp4"), \
        _heard(5.29, rate=13.2, held=0.76, video="wildhorse-5.mp4")
    t = drift.test_beat_cameras([b, _heard(24.0, video="w.mp4")])
    check(t["reading"] == "no beat of its own between 1.5 and 24.0 Hz; only a beat over 2% of its brightness would have shown "
                          "(camera 1 (sphere-2), of 2 cameras). Every camera listened in that band, and every one passes",
          "two cameras that listened in one band: said once, that it is every camera's, and that every one passes", t["reading"])
    t = drift.test_beat_cameras([b, _heard(24.0, beats=None, video="refused.mp4")])
    check(t["reading"].endswith("(camera 1 (sphere-2), of 2 cameras). Every camera listened in that band"),
          "one band from every camera does not say that every one passes where one could not say", t["reading"][-70:])
    t = drift.test_beat_cameras([a, b])
    check(t["outcome"] == drift.PASS and t["reading"] == (
              "no beat of its own between 1.5 and 4.8 Hz; only a beat over 1% of its brightness would have shown (camera 1 "
              "(hideout-1), of 2 cameras). The cameras' bands: camera 1 (hideout-1) between 1.5 and 4.8 Hz only, camera 2 "
              "(sphere-2) between 1.5 and 24.0 Hz (it passes too: only a beat over 2% would have shown). Camera 1 listened no "
              "higher because 78% of its frames nearly repeat the one before in a steady pattern: its picture is new only 12.1 "
              "times a second")
          and [e["reading"] for e in t["each"]] == [drift.test_beat(a)["reading"], drift.test_beat(b)["reading"]],
          "one camera cut short and one that listened to the frame rate's top: each camera's band, that the other passes too "
          "and what it could have shown, why the first stops, and no gap claimed; each camera's own reading is whole", t["reading"])
    t = drift.test_beat_cameras([a, c])
    check("The cameras' bands: camera 1 (hideout-1) between 1.5 and 4.8 Hz only, camera 2 (wildhorse-5) between 1.5 and 5.3 Hz "
          "only (it passes too: only a beat over 1% would have shown). Camera 1 and camera 2 listened no higher because 78% and 76% of their frames nearly repeat the one before in a "
          "steady pattern: their pictures are new only 12.1 and 13.2 times a second. A source that delivers" in t["reading"]
          and t["reading"].endswith("This test cannot tell which, so a beat faster than 5.3 Hz may have gone unheard"),
          "every camera cut short: both makers are said, and that a beat faster than the higher top may have gone unheard",
          t["reading"][-150:])
    t = drift.test_beat_cameras([b, bare(a)])
    u = drift.test_beat_cameras([b, {"clip": {"video": "dark.mp4"}, "results": {"beats": None}}])
    check("The cameras' bands: camera 1 (sphere-2) between 1.5 and 24.0 Hz; camera 2 records none" in t["reading"]
          and u["reading"].endswith("The cameras' bands: camera 1 (sphere-2) between 1.5 and 24.0 Hz; camera 2 (dark) could not say"),
          "a camera whose envelope records no band is said to record none, and one without power to say nothing",
          u["reading"][-100:])
    old = drift.test_beat_cameras([bare(a), bare(b)])
    check(old["reading"] == "no beat of its own; only a beat over 1% of its brightness would have shown (camera 1, of 2 cameras)",
          "and with no band recorded by any camera the reading is as it was", old["reading"])
    for cams in ([a, b], [a, c], [b, a, c]):
        t, was = drift.test_beat_cameras(cams), drift.test_beat_cameras([bare(e) for e in cams])
        strip = lambda t: {k: v for k, v in t.items() if k not in ("reading", "each")}
        if strip(t) != strip(was) or [e["outcome"] for e in t["each"]] != [e["outcome"] for e in was["each"]]:
            check(False, "several cameras: nothing but the readings differs with the band recorded", str(strip(t)))
            break
    else:
        check(True, "several cameras: nothing but the readings differs with the band recorded")
    # a beat one camera holds, taken back by another that could have seen a third of it: the pass says the bands, and
    # says so where the beat's rate is above the band the other camera listened in (IDEAS.md N20: the rule does not ask)
    held = dict(hz=3.0, amplitude=0.05, whole_passes=True, comes_back=True, windows_passing=10, windows=40, windows_apart=5)
    low = _heard(24.0, beats=True, beat={"object": held}, video="one.mp4")
    high = _heard(24.0, beats=True, beat={"object": dict(held, hz=9.0)}, video="one.mp4")
    for e in (low, high):
        e["results"]["finding"] = f"it beats at {e['results']['beat']['object']['hz']:.2f} Hz"
    other = _heard(4.84, rate=12.1, held=0.78, video="two.mp4")
    t, u = drift.test_beat_cameras([low, other]), drift.test_beat_cameras([high, other])
    check(t["outcome"] == u["outcome"] == drift.PASS and "is its own view" in t["reading"] and "above the" not in t["reading"]
          and "The cameras' bands: camera 1 (one) between 1.5 and 24.0 Hz (its beat is its own view), camera 2 (two) between 1.5 "
              "and 4.8 Hz only (it passes too: only a beat over 1% would have shown). Camera 2 listened no higher" in t["reading"]
          and "would have shown (but that rate is above the 4.8 Hz this camera listened to, where no beat could have shown)" in u["reading"]
          and u["outcome"] == drift.test_beat_cameras([bare(high), bare(other)])["outcome"],
          "a beat taken back by another camera: the bands are said; where its 9 Hz is above the 4.8 Hz the other listened "
          "to, the reading says that camera could not have shown it (the outcome is the rule's, as before)", u["reading"][:330])


def _given(hz=1.72, amp=0.21, kept=0.08, top=24.0, floor=0.05, video=None, back=True, whole=False, **more):
    """A drawn `flicker` envelope whose beat was seen and given to the track (method section 69), as the stage writes
    one since 2026-11-17: `beats` False, `jittered` naming the object, and the object's beat record with its frequency,
    its amplitude, the windows' own `comes_back` (true on 7 of the 8 Galileo clips that have one) and the reading."""
    e = _heard(top, floor=floor, video=video, **more)
    e["results"].update(
        jittered=["object"], strong=[],
        finding=f"what beats at {hz:.2f} Hz, {amp:.0%} of its brightness, over frames 3917–4036 follows the track's own jitter",
        beat={"object": dict(hz=hz, amplitude=amp, whole_passes=whole, comes_back=back, windows_passing=10, windows=40,
                             windows_apart=5, first=3917, last=4036,
                             jitter=dict(kept=kept, share=0.95, px=1.13, blocks=1, hz=hz, holds=False, frames=[3917, 4036]))})
    return e


def test_t3_a_beat_given_to_the_track():
    """The maintainer's decision 13 of 2026-11-17. With `flicker`'s control against the track's own jitter (method section
    69) an envelope can say `beats: false` of a clip where a beat was seen and set aside. T3 read "no beat of its own;
    only a beat over 5% of its brightness would have shown" there, on one Galileo cloud beside a 21 % beat at 1.72 Hz;
    with several cameras the reading quoted the longest track and said nothing of another camera's; and the
    several-camera rule read a beat record whether or not it was the object's. Drawn envelopes: no Galileo data."""
    print("\nT3 says where a beat was seen and given to the track (2026-11-17)")
    plain = lambda e: {"results": {k: v for k, v in e["results"].items() if k != "jittered"}, **{k: v for k, v in e.items() if k != "results"}}
    strip = lambda t: {k: v for k, v in t.items() if k not in ("reading", "each", "given_to_track", "cameras_given_to_track")}
    g = _given()
    t, was = drift.test_beat(g), drift.test_beat(plain(g))
    check(t["reading"] == "no beat of its own between 1.5 and 24.0 Hz. A beat was seen at 1.72 Hz, 21% of its brightness, but it "
                          "follows the track's own jitter. Jitter is the small scatter of the object's measured position from "
                          "frame to frame. With the jitter's share taken out, 8% of the beat is left, where a beat of the "
                          "object's own keeps 50% or more. So it is counted as the track's, not the object's. A weaker beat of "
                          "the object's own could be hidden under it, and only a stronger one would have shown",
          "one camera: the pass says the beat that was seen, its frequency, its strength and the share it kept, and that it "
          "is the track's", t["reading"])
    check("only a beat over" not in t["reading"] and "5%" not in t["reading"],
          "and does not say that only a beat over 5 % would have shown, beside a beat of 21 % that did", t["reading"][-110:])
    check(t["outcome"] == drift.PASS and strip(t) == strip(was) and t["smallest_beat_seen"] == 0.05
          and t["given_to_track"] == dict(hz=1.72, amplitude=0.21, kept=0.08, jitter_px=1.13, frames=[3917, 4036]),
          "the outcome and every number are as the envelope gives them; the beat set aside is recorded under its own name",
          str(t.get("given_to_track")))
    check(was["reading"] == "no beat of its own between 1.5 and 24.0 Hz; only a beat over 5% of its brightness would have shown"
          and "given_to_track" not in was and drift.given_to_track(plain(g)) is None and drift.given_to_track(None) is None,
          "an envelope without the new field reads exactly as before, whatever its beat record holds", was["reading"])
    cut = drift.test_beat(_given(top=4.84, rate=12.1, held=0.78))
    check(cut["reading"].startswith("no beat of its own between 1.5 and 4.8 Hz. A beat was seen at 1.72 Hz")
          and "only a stronger one would have shown. Faster beats, up to the 24.0 Hz this frame rate could carry" in cut["reading"]
          and cut["reading"].endswith("so a beat faster than 4.8 Hz may have gone unheard"),
          "a band cut short is still said, after the beat that was set aside", cut["reading"][:80])
    # an envelope of two objects: the first's beat went to its track and the second beats. The envelope's `beats` is
    # true, and the first's record keeps `comes_back` as its windows gave it; T3 reads the first object
    two = _given()
    two["results"].update(beats=True, strong=["object-2"], finding="object-2 beats at 6.10 Hz")
    two["results"]["beat"]["object-2"] = dict(hz=6.1, amplitude=0.3, whole_passes=True, comes_back=True)
    t = drift.test_beat(two)
    check(t["outcome"] == drift.PASS and t["held"] is False and drift.held_beat(two["results"])[0] is False
          and t["reading"].startswith("no beat of its own between 1.5 and 24.0 Hz. A beat was seen at 1.72 Hz"),
          "a record given to the track does not hold across the video, though it keeps the windows' own `comes_back`: T3 "
          "of the first object passes where another object of the envelope beats", f"{t['outcome']}: {t['reading'][:60]}")
    check(drift.test_beat(plain(two))["outcome"] == drift.FAIL, "(the same record not given to the track holds, and fails)")

    # ---- several cameras
    quiet = _heard(24.0, floor=0.03, video="hideout-7.mp4")
    aside = _given(video="sphere-3.mp4")
    t = drift.test_beat_cameras([quiet, aside])
    check(t["outcome"] == drift.PASS and t["reading"] == (
              "no beat of its own between 1.5 and 24.0 Hz; only a beat over 3% of its brightness would have shown (camera 1 "
              "(hideout-7), of 2 cameras). Camera 2 (sphere-3) saw a beat at 1.72 Hz, 21% of its brightness, but it follows "
              "the jitter of that camera's own track. Jitter is the small scatter of the object's measured position from "
              "frame to frame. With the jitter's share taken out, 8% of the beat is left, where a beat of the object's own "
              "keeps 50% or more. So it is counted as the track's, not the object's. In that camera's view a weaker beat of "
              "the object's own could be hidden under it, and only a stronger one would have shown. Every camera listened "
              "in that band, and every one passes"),
          "two cameras, the reading led by the one with no beat: it says all the same what the other saw and set aside",
          t["reading"])
    check(t["cameras_given_to_track"] == [dict(hz=1.72, amplitude=0.21, kept=0.08, jitter_px=1.13, frames=[3917, 4036],
                                               camera="camera 2 (sphere-3)")]
          and "given_to_track" not in t and t["each"][1]["given_to_track"]["hz"] == 1.72
          and t["each"][1]["reading"] == drift.test_beat(aside)["reading"] and t["smallest_beat_seen"] == 0.03,
          "the answer records which camera's beat went to its track; each camera's own reading is whole")
    was = drift.test_beat_cameras([quiet, plain(aside)])
    check(was["reading"] == "no beat of its own between 1.5 and 24.0 Hz; only a beat over 3% of its brightness would have shown "
                            "(camera 1 (hideout-7), of 2 cameras). Every camera listened in that band, and every one passes"
          and strip(t) == strip(was) and "cameras_given_to_track" not in was,
          "without the new field the two cameras read exactly as before, and nothing but the words differs", was["reading"])
    t = drift.test_beat_cameras([aside, quiet])
    check(t["reading"].startswith("no beat of its own between 1.5 and 24.0 Hz (camera 1 (sphere-3), of 2 cameras). Camera 1 "
                                  "(sphere-3) saw a beat at 1.72 Hz, 21% of its brightness")
          and "only a beat over 5%" not in t["reading"] and t["given_to_track"]["amplitude"] == 0.21,
          "led by the camera whose beat went to its track: its floor is not quoted", t["reading"][:120])
    lower = _heard(4.84, rate=12.1, held=0.78, floor=0.03, video="hideout-7.mp4")
    t = drift.test_beat_cameras([lower, aside, _given(hz=2.44, amp=0.05, kept=0.27, video="wildhorse-1.mp4")])
    check("camera 2 (sphere-3) between 1.5 and 24.0 Hz (it passes too: the beat it saw was given to its track)" in t["reading"]
          and "only a beat over 5% would have shown" not in t["reading"] and t["reading"].count("Jitter is the small scatter") == 1
          and "Camera 3 (wildhorse-1) saw a beat at 2.44 Hz, 5% of its brightness" in t["reading"]
          and len(t["cameras_given_to_track"]) == 2,
          "in the list of bands such a camera passes too, without a floor; two such cameras are each said, jitter defined once",
          t["reading"][-330:-200])

    # ---- the rule: a record given to the track is not a beat that agrees
    held = dict(hz=2.44, amplitude=0.05, whole_passes=True, comes_back=True, windows_passing=10, windows=40, windows_apart=5)
    a = _heard(24.0, beats=True, beat={"object": held}, video="hideout-5.mp4")
    a["results"]["finding"] = "it beats at 2.44 Hz"
    near = _given(hz=2.47, amp=0.03, kept=0.2, floor=0.04, video="sphere-3.mp4")       # too noisy to take a third back
    t, was = drift.test_beat_cameras([a, near]), drift.test_beat_cameras([a, plain(near)])
    check(was["outcome"] == drift.FAIL and "camera 2 (sphere-3) sees 2.47 Hz at 3%" in was["reading"],
          "(before: another camera's record at the same rate agrees, given to its track or not)", was["reading"][-60:])
    check(t["outcome"] == drift.FAIL and "sees 2.47 Hz" not in t["reading"]
          and t["reading"].endswith("(camera 1 (hideout-5); no other camera could have seen a beat a third as strong; camera 2 "
                                    "(sphere-3) saw 3.0% at 2.47 Hz, but that beat follows its own track's jitter and is not "
                                    "counted)"),
          "a held beat and another camera's record at the same rate that was given to its track: the record does not agree, "
          "and the failure rests on what no other camera could have seen", t["reading"][-150:])
    quiet = _heard(24.0, floor=0.01, video="wildhorse-5.mp4")
    t = drift.test_beat_cameras([a, near, quiet])
    check(t["outcome"] == drift.PASS and "camera 1 (hideout-5)'s beat at 2.44 Hz (5% of its brightness) is its own view: "
          "camera 3 (wildhorse-5), watching at the same time, sees no beat at that rate where a beat of 1.0% would have shown" in t["reading"]
          and "camera 2 (sphere-3)," not in t["reading"].split(". Camera 2")[0]
          and "Camera 2 (sphere-3) saw a beat at 2.47 Hz, 3% of its brightness" in t["reading"],
          "with a third camera that could have seen it and does not, the beat is taken back as before; the camera that saw "
          "the same rate follow its track neither agrees nor takes it back, and is said", t["reading"][:200])
    check(drift.test_beat_cameras([a, plain(near), quiet])["outcome"] == drift.FAIL,
          "(before, that record agreed and kept the failure against the third camera)")
    # at the same rate too it vouches for what it could have shown: a beat it set aside at a tenth of the held one's
    # strength says that no beat a third as strong was there, and takes the held beat back, as its record did before
    sure = _given(hz=2.47, amp=0.005, kept=0.2, floor=0.004, video="sphere-3.mp4")
    t, was = drift.test_beat_cameras([a, sure]), drift.test_beat_cameras([a, plain(sure)])
    check(t["outcome"] == was["outcome"] == drift.PASS and "camera 2 (sphere-3), watching at the same time, sees 0.5% at 2.47 "
          "Hz, which follows its own track's jitter, where only a beat over 0.5%, the strength of the one given to its track, "
          "would have shown" in t["reading"],
          "a camera that saw the same rate at a tenth of the strength, following its own track, still takes the held beat "
          "back, and the reading says whose that 0.5 % was", t["reading"][:250])
    # at another rate it vouches only for a beat stronger than the one it set aside, not for its floor
    far = _given(hz=6.0, amp=0.04, kept=0.2, floor=0.01, video="sphere-3.mp4")       # floor 1 %, a beat of 4 % given away
    t, was = drift.test_beat_cameras([a, far]), drift.test_beat_cameras([a, plain(far)])
    check(drift.shown_floor(far) == 0.04 and abs(drift.beat_floor(far) - 0.01) < 1e-12 and t["outcome"] == drift.FAIL
          and was["outcome"] == drift.PASS and "no other camera could have seen a beat a third as strong" in t["reading"],
          "a camera that set a 4 % beat aside at another rate cannot vouch that a 1.7 % beat was absent (a third of the "
          "held 5 %), though its floor is 1 %: the held beat stays", t["reading"][-70:])
    weak = _given(hz=6.0, amp=0.015, kept=0.2, floor=0.01, video="sphere-3.mp4")     # 1.5 % set aside: under a third of 5 %
    t = drift.test_beat_cameras([a, weak])
    check(t["outcome"] == drift.PASS and "sees no beat at that rate where only a beat over 1.5%, the strength of the one given "
          "to its track, would have shown" in t["reading"] and "Camera 2 (sphere-3) saw a beat at 6.00 Hz" in t["reading"],
          "where the beat it set aside is under a third of the held one, it takes the held beat back, and the reading "
          "says what it could have shown", t["reading"][:260])


# ---------------------------------------------------------------- T4, other evidence: T4a, a tracer
def test_t4a_pieces_left_slowly_bound_the_airspeed():
    print("\nT4a: pieces shed, against the remains")
    rem, piece = pieces_scene((12.0, -5.0))
    r = drift.relative(rem, piece, FPS, np.random.default_rng(0))
    check(r is not None and abs(r["speed_px_s"] - 13.0) < 0.5, "the piece's speed against the remains is recovered",
          f"{r and r['speed_px_s']:.2f} px/s of 13")
    out = drift.test_tracer((20.0, 20.0), [r], 40.0)
    check(out["outcome"] == drift.PASS and abs(out["airspeed_bound_L_per_s"] - 0.65 / math.sin(math.radians(40))) < 0.05,
          "0.65 lengths/s at 40 deg bounds the airspeed under 2 lengths/s: passes", f"{out['outcome']}, "
          f"{out.get('airspeed_bound_L_per_s')}")
    fast = drift.relative(*pieces_scene((60.0, 0.0)), FPS, np.random.default_rng(0))
    out = drift.test_tracer((20.0, 20.0), [fast], 40.0)
    check(out["outcome"] == drift.FAIL, "pieces leaving at 3 lengths/s: it flies, fails", out["reading"][:80])
    mid = drift.relative(*pieces_scene((30.0, 0.0)), FPS, np.random.default_rng(0))
    out = drift.test_tracer((20.0, 20.0), [mid], 40.0)
    check(out["outcome"] == drift.CANNOT, "1.5 lengths/s at 40 deg: a slow flier's, cannot say", out["reading"][:80])
    out = drift.test_tracer((20.0, 20.0), [r], None)
    check(out["outcome"] == drift.CANNOT, "no depression: flight along the line of sight could hide, cannot say")
    out = drift.test_tracer((20.0, 20.0), [fast], None)
    check(out["outcome"] == drift.FAIL and "at any depression" in out["reading"],
          "pieces leaving at 3 lengths/s with no depression given: fails all the same, since what shows across the line of "
          "sight is the least its airspeed can be (it could not say until 2026-11-13)", out["reading"][:80])
    for dep in (2.0, 40.0, 88.0):
        check(drift.test_tracer((20.0, 20.0), [fast], dep)["outcome"] == drift.FAIL, f"as they do at a depression of {dep:g} deg")
    out = drift.test_tracer((20.0, 20.0), [mid], None)
    check(out["outcome"] == drift.CANNOT, "1.5 lengths/s with no depression: still cannot say")
    out = drift.test_tracer((20.0, 20.0), [None], 40.0)
    check(out["outcome"] == drift.CANNOT, "no pieces: cannot say")


def test_t4a_cloud_is_a_tracer_only_at_the_objects_depth():
    print("\nT4a: the cloud around it")
    carried = {"results": {"verdict": "CARRIED", "legs": [{"rel_D_per_s": 0.2}]}}
    through = {"results": {"verdict": "MOVES THROUGH", "legs": [{"rel_D_per_s": 1.3}, {"rel_D_per_s": 3.7}]}}
    out = drift.test_tracer(None, [], None, "same", carried)
    check(out["outcome"] == drift.PASS and out["tracer_depth"] == "same", "carried by cloud at its own depth: passes")
    check(drift.verdict([drift.test_other([out])])[0].startswith("consistent"),
          "and that is a strong test: the verdict is tentative drift")
    out = drift.test_tracer(None, [], None, "layer", carried)
    check(out["outcome"] == drift.PASS and drift.verdict([drift.test_other([out])])[0] == "cannot say",
          "carried by cloud it is only within: passes, but is no strong test (the verdict cannot say)")
    out = drift.test_tracer(None, [], None, "layer", through)
    check(out["outcome"] == drift.CANNOT and out["rel_D_per_s"] == [1.3, 3.7],
          "moving through the layer it is in: a depth offset could do that, cannot say", out["reading"][:70])
    out = drift.test_tracer(None, [], None, "unknown", carried)
    check(out["outcome"] == drift.CANNOT, "cloud at an unknown depth is no tracer: cannot say")


# ---------------------------------------------------------------- T4b, the remains
def test_t4b_a_heavy_wreck_falls_and_a_cloud_of_debris_does_not():
    print("\nT4b: the remains")
    rng = np.random.default_rng(3)
    n = np.arange(640, 740)
    t = (n - n[0]) / FPS
    L = 20.0
    sink = {int(f): (0.0, 5 * s + rng.normal(0, 0.3)) for f, s in zip(n, t)}
    f = drift.fall(sink, FPS, np.random.default_rng(0))
    out = drift.test_wreck(f["accel_px_s2"] / L, f["accel_err"] / L, 40.0)
    check(out["outcome"] == drift.PASS and out["excludes_wrecks_under_m"] >= 20 and out["reach_by"] == "a + 3 sigma",
          "a steady sink excludes a falling wreck of every body under 20 m: passes (no band given: the reach by a + 3 sigma)",
          f"{out['excludes_wrecks_under_m']} m")
    band = lambda f, L: dict(accel_L=f["band_accel_px_s2"] / L, accel_err_L=f["band_accel_err_px_s2"] / L,   # noqa: E731
                             accel_max_L=f["band_accel_max_px_s2"] / L if f["band_accel_max_px_s2"] is not None else None)
    check(f["band_accel_max_px_s2"] is not None and f["band_light"] is not None and f["band_nugget_px"] is not None,
          "its own band: a bound on a steady change of speed, the nugget, a backtest light",
          f"{f['band_accel_max_px_s2']:.3f} px/s^2, {f['band_nugget_px']:.2f} px, {f['band_light']}")
    out = drift.test_wreck(f["accel_px_s2"] / L, f["accel_err"] / L, 40.0, band=band(f, L))
    check(out["outcome"] == drift.PASS and out["reach_by"].startswith("the band") and out["excludes_wrecks_under_m"] >= 20
          and "(a band)" in out["reading"] and "either way (95 %)" in out["reading"],
          "with its band the reach is the band's bound, said in the reading; the steady sink still passes",
          f"{out['excludes_wrecks_under_m']} m")
    a = 9.81 * math.cos(math.radians(40)) / 5.0 * L                 # a 5-m body, 20 px long, falling
    fallen = {int(f): (0.0, 0.5 * a * s ** 2 + rng.normal(0, 0.3)) for f, s in zip(n, t)}
    f = drift.fall(fallen, FPS, np.random.default_rng(0))
    out = drift.test_wreck(f["accel_px_s2"] / L, f["accel_err"] / L, 40.0, band=band(f, L))
    check(out["outcome"] == drift.FAIL and abs(out["accel_L_per_s2"] - a / L) < 0.1,
          "a 5-m wreck falling at g: fails", f"{out['accel_L_per_s2']} of {a / L:.2f} lengths/s^2")
    check(f["band_accel_max_px_s2"] is None and out["reach_by"] == "a + 3 sigma"
          and abs(out["band_accel_L_per_s2"] - a / L) < 0.1,
          "its band saw the change, so it gives no bound and the reach is a + 3 sigma; the band's acceleration is the fall's",
          f"band {out['band_accel_L_per_s2']} +- {out['band_accel_err']} lengths/s^2")
    # a drawn track with a slow wander, its range 0.65 s against the bootstrap's 0.5-s blocks, as the Yemen remains
    # have: the bootstrap's error is too small, and the band's bound is the honest reach (2026-11-02)
    from mcdonald import kinematics
    track, _ = kinematics.simulate_track(106, 30.0, v=(2.0, 32.0), nugget=0.35, sill=5.0, range_s=0.65,
                                         start=(-45.0, 27.0), frame0=640, rng=np.random.default_rng(1))
    f = drift.fall(track, FPS, np.random.default_rng(0))
    check(f["band_accel_max_px_s2"] is not None and f["band_accel_max_px_s2"] > 3 * f["accel_err"]
          and f["band_accel_err_px_s2"] > f["accel_err"],
          "a drawn track with a slow wander: the band's bound is over three of the bootstrap's errors, its own error larger",
          f"bound {f['band_accel_max_px_s2']:.2f}, band error {f['band_accel_err_px_s2']:.2f}, bootstrap error "
          f"{f['accel_err']:.2f} px/s^2; range {f['band_range_s']:.2f} s against {drift.BLOCK / FPS:.2f}-s blocks")
    L2 = 22.3
    out = drift.test_wreck(f["accel_px_s2"] / L2, f["accel_err"] / L2, 40.5, band=band(f, L2))
    gc = 9.81 * math.cos(math.radians(40.5))
    check(out["reach_by"].startswith("the band")
          and abs(out["excludes_wrecks_under_m"] - gc / (f["band_accel_max_px_s2"] / L2)) <= 1,
          "and test_wreck's reach is g cos(delta) over the band's bound", f"{out['excludes_wrecks_under_m']} m, {out['outcome']}")
    # the thresholds (2026-11-02): a pass needs a reach of 10 m, every drone's and every bird's size; the fail rule
    # keeps its 20-m constant, and is tried first
    gc = 9.81 * math.cos(math.radians(40.0))
    out = drift.test_wreck(0.0, gc / 15.0 / 3, 40.0)
    check(drift.WRECK_MIN_M == 10.0 and out["outcome"] == drift.PASS and abs(out["excludes_wrecks_under_m"] - 15) <= 1,
          "a reach of 15 m passes (the pass needs 10 m)", f"{out['excludes_wrecks_under_m']} m")
    out = drift.test_wreck(0.0, gc / 8.0 / 3, 40.0)
    check(out["outcome"] == drift.CANNOT and "only below" in out["reading"], "a reach of 8 m cannot say", out["reading"][:50])
    out = drift.test_wreck(gc / 10.0, 0.05, 40.0)
    check(out["outcome"] == drift.FAIL, "a 10-m body's own fall, measured to 0.05 lengths/s^2: fails", out["reading"][:60])
    out = drift.test_wreck(gc / 20.0, 0.05, 40.0)
    check(drift.WRECK_FAIL_M == 20.0 and out["outcome"] == drift.FAIL and out["excludes_wrecks_under_m"] >= 10,
          "a 20-m body's fall, measured to 0.05: fails (the fail rule's own constant, tried before the pass, whose "
          "reach it would meet)", f"reach {out['excludes_wrecks_under_m']} m")
    check(drift.test_wreck(None, None, 40.0)["outcome"] == drift.CANNOT, "nothing struck: cannot say")


# ---------------------------------------------------------------- T4: the parts together
def test_t4_the_parts_combined():
    print("\nT4: other evidence, its parts together")
    P = lambda name, **k: dict(test=name, outcome=drift.PASS, reading="it moves with the air", **k)   # noqa: E731
    F = lambda name: dict(test=name, outcome=drift.FAIL, reading="the remains fall as a heavy body")  # noqa: E731
    C = lambda name: dict(test=name, outcome=drift.CANNOT, reading="nothing to run on")               # noqa: E731
    out = drift.test_other([P("T4a", tracer_depth="same"), C("T4b")])
    check(out["test"] == "T4" and out["outcome"] == drift.PASS and [q["test"] for q in out["parts"]] == ["T4a", "T4b"],
          "a part passes and none fails: passes, its parts kept", out["reading"])
    out = drift.test_other([P("T4a", tracer_depth="same"), F("T4b")])
    check(out["outcome"] == drift.FAIL and "T4b" in out["reading"], "a part fails: fails, whatever passed", out["reading"])
    out = drift.test_other([C("T4a"), C("T4b")])
    check(out["outcome"] == drift.CANNOT and out["reading"].startswith("no part decided"),
          "no part decided (nothing shed, no strike): cannot say", out["reading"][:60])
    check(drift.verdict([drift.test_other([C("T4a"), P("T4b")])])[0] == "cannot say",
          "the remains alone are no strong test: T4 passing on T4b cannot carry the verdict")
    v, why = drift.verdict([P("T1"), P("T2"), drift.test_other([P("T4a", tracer_depth="same"), F("T4b")])])
    check(v == "not drifting" and why.startswith("T4b"), "a failing part decides, and the verdict names it", why[:60])


# ---------------------------------------------------------------- the verdict
def test_the_verdicts_rule():
    print("\nthe verdict")
    P = lambda name, **k: dict(test=name, outcome=drift.PASS, reading="", **k)   # noqa: E731
    F = lambda name: dict(test=name, outcome=drift.FAIL, reading="it beats")    # noqa: E731
    C = lambda name: dict(test=name, outcome=drift.CANNOT, reading="")          # noqa: E731
    other = lambda *parts: drift.test_other(list(parts))                         # noqa: E731
    v = drift.verdict([C("T1"), C("T2"), P("T3"), other(P("T4a", tracer_depth="same"), C("T4b"))])[0]
    check(v.startswith("consistent with wind-borne drift"),
          "a strong test (a tracer at its own depth) passed and none failed: tentative drift")
    los = dict(source="lines of sight")
    check(drift.verdict([P("T1"), P("T2", **los), F("T3"), other(P("T4a", tracer_depth="same"))])[0] == "not drifting",
          "any test failed (a beat held across the video, a hovering rotor's): not drifting, whatever passed")
    check(drift.verdict([P("T2", **los), C("T3")])[0].startswith("consistent with wind-borne drift"),
          "T3 without power (cannot say) leaves a strong pass (T2 from lines of sight) standing")
    # T2 is a strong test only where it came from lines of sight (2026-11-17, the maintainer's decision on method
    # section 68: from the ranges a body flying 5-10 m/s passes nearly as often as a drifter)
    v, why = drift.verdict([P("T1"), P("T2", source="ranges"), P("T3"), other(C("T4a"), C("T4b"))])
    check(v == "cannot say" and why == ("no strong test (T2 from lines of sight, or T4a with a tracer at the object's depth) "
                                        "passed. T2 passed from the ranges, where it cannot tell a drifter from a slow flier"),
          "T2 passing from the ranges alone: cannot say (tentative drift until 2026-11-17), and the reason says both", why)
    v, why = drift.verdict([P("T1"), P("T2", source="ranges"), P("T3"), other(P("T4a", tracer_depth="same"), P("T4b"))])
    check(v.startswith("consistent") and why == "passed T4a and failed none; it names no object",
          "with a tracer at its depth beside it, the verdict rests on the tracer alone: \"passed T4a and failed none\"", why)
    v, why = drift.verdict([P("T2", **los), other(P("T4a", tracer_depth="same"))])
    check(why == "passed T2, T4a and failed none; it names no object", "from lines of sight T2 is named with it", why)
    check(drift.verdict([F("T2") | dict(source="ranges")])[0] == "not drifting",
          "a fail of T2 from the ranges still decides: any failure is not drifting")
    check(drift.verdict([C("T1"), C("T2"), P("T3")])[1] == "no strong test (T2 from lines of sight, or T4a with a tracer at "
          "the object's depth) passed", "and where T2 did not pass the reason does not speak of it")
    check(drift.verdict([P("T1"), P("T3"), other(P("T4b"))])[0] == "cannot say",
          "no strong test passed (T1, T3 and T4b only): cannot say")
    check(drift.verdict([C("T1"), C("T2"), C("T3"), other(C("T4a"), C("T4b"))])[0] == "cannot say",
          "nothing ran: cannot say")


# ---------------------------------------------------------------- the known answer
def golden():
    g = GOLDEN
    return dict(L=(22.3, 14.6), remains=drift.read_track(g / "remains.csv"),
                pieces=[drift.read_track(g / f"piece_{c}.csv") for c in "AB"],
                slant=drift.read_series(g / "slant.csv"), horiz=drift.read_series(g / "horizontal.csv"),
                own=drift.read_series(g / "own_height.csv", ("value_m", "value"), ("err_m", "err"), 10.0),
                bearings=drift.read_series(g / "bearings.csv", ("value",), ("err_deg",), 0.1),
                winds=sorted(str(p) for p in g.glob("wind_*.json")),
                flicker=json.loads((g / "flicker.json").read_text(encoding="utf-8")))


def test_hellfire_yemen_from_its_readings():
    """The case's numbers (analysis of 2026-10-21, mcdonald drift on the same inputs): it holds its height to
    -0.9 +- 1.1 m/s at a depression of 40.55 deg; the winds need the MQ-9 at 179-191 kn and lie the way the 23-kn
    sideways motion does; no beat over 41 % of its brightness; and other evidence, since it was struck: the pieces bound
    its airspeed under 1.93 of its lengths a second, and the remains sink with no fall."""
    print("\nHellfire/Yemen: from its readings (no video)")
    g = golden()
    found = drift.measure(FPS, g["L"], g["remains"], g["pieces"], slant=g["slant"], horiz=g["horiz"], own=g["own"],
                          bearings=g["bearings"], heading_deg=144.9, winds=g["winds"], air_min_kn=0.0, air_max_kn=240.0,
                          flicker=g["flicker"])
    T = {t["test"]: t for t in drift.flat(found.fields["tests"])}
    t1, t2, t3, t4, t4a, t4b = (T[k] for k in ("T1", "T2", "T3", "T4", "T4a", "T4b"))
    check(t1["outcome"] == drift.PASS and abs(t1["climb_m_s"] + 0.92) < 0.05 and abs(t1["climb_err_m_s"] - 1.08) < 0.05,
          "T1: it holds its height", f"{t1['climb_m_s']} +- {t1['climb_err_m_s']} m/s")
    check(abs(found.fields["depression_deg"] - 40.55) < 0.05, "and the depression from the ranges",
          f"{found.fields['depression_deg']:.2f} deg")
    check(t2["outcome"] == drift.PASS and abs(t2["airspeed_kn"][0] - 179.1) < 1 and abs(t2["airspeed_kn"][1] - 190.5) < 1
          and abs(t2["sideways_right_kn"] - 23.2) < 0.5 and t2["same_side"],
          "T2: the winds need 179-191 kn of the aircraft, and lie the way its motion does",
          f"{t2['airspeed_kn']} kn, {t2['sideways_right_kn']} kn to the right")
    check(t2["source"] == "ranges" and abs(t2["shortfall_m_s"][0] - 2.7) < 0.1 and abs(t2["shortfall_m_s"][1] - 9.5) < 0.1
          and abs(t2["fit_err_across_m_s"] - 0.76) < 0.03 and abs(t2["tolerance_m_s"] - 6.3) < 0.1 and t2["samples"] == 72
          and "5 kn (2.7 m/s) short" in t2["reading"] and "not a strong test" in t2["reading"],
          "T2 by the rule of 2026-11-17: the nearest of its 72 hours and places is 2.7 m/s short of the measured sideways "
          "motion, within two errors of the fit (1.5) and a model's own error on such a difference (4.8); it passes, and "
          "says the pass is not a strong one", t2["reading"])
    check(found.fields["why"] == "passed T4a and failed none; it names no object",
          "the verdict rests on the tracer alone since then (\"passed T2, T4a\" before): T2 from the ranges is no strong "
          "test", found.fields["why"])
    left = [n[1] for n in t2["needs_kn"]]
    check(len(left) == t2["samples"] and 4 <= min(left) and max(left) <= 19,
          "and what the winds leave the aircraft to fly sideways is to its left, 5-18 kn (their shortfall)",
          f"{min(left)}-{max(left)} kn")
    check(t3["outcome"] == drift.PASS and t3["smallest_beat_seen"] == 0.41, "T3: no beat over 41 %")
    check(t3["reading"] == "no beat of its own; only a beat over 41% of its brightness would have shown",
          "T3's words are as they were: this envelope, cut down for the test, records no band, and none is guessed", t3["reading"])
    check(t4a["outcome"] == drift.PASS and abs(t4a["airspeed_bound_L_per_s"] - 1.93) < 0.03,
          "T4a: the two pieces bound its airspeed under 2 lengths/s", f"{t4a.get('airspeed_bound_L_per_s')} L/s")
    bands = t4a.get("pieces_band_L_per_s") or []
    check(len(bands) == 2 and all(b is not None and 0.9 <= b / l <= 1.0 for b, l in zip(bands, t4a["pieces_L_per_s"]))
          and abs(bands[0] - 0.79) < 0.02 and abs(bands[1] - 0.62) < 0.02,
          "and the pieces' speeds from their own bands (0.79 and 0.62 L/s) agree with the lines' within 10 %",
          f"bands {bands}, lines {t4a['pieces_L_per_s']}")
    check(t4b["outcome"] == drift.PASS and abs(t4b["accel_L_per_s2"] + 0.08) < 0.02
          and 12 <= t4b["excludes_wrecks_under_m"] <= 22 and t4b["reach_by"].startswith("the band"),
          "T4b: no falling wreck under ~17 m (16.5), by the band's bound (75 m by a + 3 sigma until 2026-11-02)",
          f"{t4b['accel_L_per_s2']} +- {t4b['accel_err']}, {t4b['excludes_wrecks_under_m']} m")
    check(abs(t4b["band_accel_L_per_s2"] + 0.17) < 0.03 and abs(t4b["band_accel_err"] - 0.145) < 0.03
          and abs(t4b["band_accel_max_L_per_s2"] - 0.45) < 0.05 and t4b["band_accel_err"] > 2 * t4b["accel_err"]
          and t4b["band_range_s"] > t4b["bootstrap_block_s"],
          "the band: -0.17 +- 0.14 L/s^2, its error over twice the bootstrap's, a steady change over 0.45 would have shown;"
          " the wander outlasts the bootstrap's blocks",
          f"{t4b['band_accel_L_per_s2']} +- {t4b['band_accel_err']}, bound {t4b['band_accel_max_L_per_s2']}, range "
          f"{t4b['band_range_s']} s against {t4b['bootstrap_block_s']}-s blocks, {t4b['band_light']}")
    check(t4["outcome"] == drift.PASS, "T4: other evidence, both parts pass", t4["reading"])
    rels = [drift.relative(g["remains"], q, FPS, np.random.default_rng(20261021)) for q in g["pieces"]]
    fast = drift.test_tracer(g["L"], [dict(r, speed_px_s=5 * r["speed_px_s"]) for r in rels], None)
    slow = drift.test_tracer(g["L"], rels, None)
    check(fast["outcome"] == drift.FAIL and fast["fastest_L_per_s"][0] > 4 and slow["outcome"] == drift.CANNOT,
          "the same pieces five times faster and no depression given: T4a fails (4 lengths/s or more at any depression); "
          "at their own speed and no depression it cannot say, as before", f"{fast['fastest_L_per_s']} L/s")
    check([t["test"] for t in found.fields["tests"]] == ["T1", "T2", "T3", "T4"]
          and [q["test"] for q in t4["parts"]] == ["T4a", "T4b"],
          "three main tests, then other evidence with its two parts", ", ".join(T))
    check(found.fields["verdict"] == "consistent with wind-borne drift (tentative)", "verdict: tentative drift",
          found.fields["verdict"])


def test_hellfire_yemen_by_the_command_line():
    print("\nHellfire/Yemen: by the command line, on the clip")
    if not CLIP.exists():
        print(f"  SKIP  the clip is not on this computer ({CLIP})")
        SKIP.append("Hellfire/Yemen command line")
        return
    g = GOLDEN
    with tempfile.TemporaryDirectory() as td:
        cmd = [sys.executable, "-m", "mcdonald.cli", "drift", str(CLIP), "--size-px", "22.3,14.6",
               "--remains", str(g / "remains.csv"), "--pieces", f"{g / 'piece_A.csv'},{g / 'piece_B.csv'}",
               "--slant", str(g / "slant.csv"), "--horizontal", str(g / "horizontal.csv"),
               "--own-height", str(g / "own_height.csv"), "--bearings", str(g / "bearings.csv"), "--heading", "144.9",
               "--winds", ",".join(sorted(str(p) for p in g.glob("wind_*.json"))), "--airspeed-kn", "0,240",
               "--flicker", str(g / "flicker.json"), "--out", str(Path(td) / "h"), "--json"]
        env = dict(__import__("os").environ, PYTHONPATH=str(reference_data.REPO / "src"))
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
        d = json.loads(p.stdout) if p.stdout.strip().startswith("{") else None
        wrote = (Path(td) / "h_drift.json").exists()
    if not check(p.returncode == 0 and d is not None and d["command"] == "drift", "one envelope on stdout",
                 f"exit {p.returncode} {p.stderr[-200:]}"):
        return
    T = {t["test"]: t["outcome"] for t in drift.flat(d["results"]["tests"])}
    check(T == {k: drift.PASS for k in ("T1", "T2", "T3", "T4", "T4a", "T4b")}, "every test passes, as from the readings",
          ", ".join(f"{k} {v}" for k, v in sorted(T.items())))
    t4b = next(t for t in drift.flat(d["results"]["tests"]) if t["test"] == "T4b")
    check(abs(t4b["accel_L_per_s2"] + 0.08) < 0.02 and 12 <= t4b["excludes_wrecks_under_m"] <= 22
          and abs(t4b["band_accel_L_per_s2"] + 0.17) < 0.03 and "(a band)" in t4b["reading"],
          "T4b in the envelope: -0.08 by the quadratic, -0.17 by the band, no wreck under ~17 m",
          f"{t4b['accel_L_per_s2']}, {t4b['band_accel_L_per_s2']}, {t4b['excludes_wrecks_under_m']} m")
    check(d["results"]["verdict"] == "consistent with wind-borne drift (tentative)" and wrote,
          "verdict: tentative drift, and <out>_drift.json written")


PR_GOLDEN = reference_data.GOLDEN / "puerto_rico_drift"
PR_CLIP = reference_data.root() / "aaro" / "videos" / "DOD_110692805-1920x1080-9000k.mp4"
PR_FPS = 30000 / 1001


def test_puerto_rico_lanterns_from_their_readings():
    """The known drifter: AARO's Puerto Rico 2013 video, two sky lanterns (AARO case resolution, 20 March 2025). Its
    display ranges only the ground (the laser is off), so T1/T2 come from the aircraft's own track: 39 readings over a
    157-deg turn (the uap repository's analysis/cases/aaro_puerto_rico/, section 5, 2026-10-21). They moved at 7.3-7.4
    m/s toward 240 deg, sinking 0.6 m/s, 181 m above the airfield; the aircraft's own wind is 9.5 m/s from 071 deg; every
    wind at their height leaves them 1.4-3.7 m/s through the air. `flicker` found 3.0 Hz in one window of 109, a beat in
    one stretch, which is not counted: T3 passes on the whole stretch. Nothing was shed or struck, so T4 cannot say,
    and the verdict is tentative drift."""
    print("\nPuerto Rico lanterns: from their readings (no video)")
    g = PR_GOLDEN
    found = drift.measure(PR_FPS, platform=drift.read_platform(g / "platform.csv"), los=drift.read_los(g / "los.csv"),
                          winds=sorted(str(p) for p in g.glob("wind_*.json")), when="2013-04-27T01:22:47",
                          observed_winds=drift.read_rows(g / "obs_winds.csv"), ground_m=72.0,
                          flicker=json.loads((g / "flicker.json").read_text(encoding="utf-8")))
    T = {t["test"]: t for t in drift.flat(found.fields["tests"])}
    gp = found.fields["ground_path"]
    check(7.0 <= gp["speed_m_s"] <= 7.8 and 237 <= gp["toward_deg"] <= 244 and 170 <= gp["above_ground_m"] <= 195,
          "the path: 7.3-7.4 m/s toward 240 deg, 181 m above the field",
          f"{gp['speed_m_s']:.2f} m/s toward {gp['toward_deg']:.1f}, {gp['above_ground_m']:.0f} m")
    check(T["T1"]["outcome"] == drift.PASS and abs(T["T1"]["climb_m_s"] + 0.6) < 0.1, "T1: a slow sink, passes",
          T["T1"]["reading"])
    aw = T["T2"].get("aircraft_wind") or {}
    check(abs(aw.get("speed_m_s", 0) - 9.5) < 0.3 and abs(aw.get("from_deg", 0) - 70.6) < 2,
          "the aircraft's own wind from its turn", f"{aw.get('speed_m_s')} m/s from {aw.get('from_deg')}")
    check(T["T2"]["outcome"] == drift.PASS and T["T2"]["needs_m_s"][1] < 4.0, "T2: every wind at their height "
          "leaves them under 4 m/s through the air, passes", f"{T['T2']['needs_m_s']} m/s")
    check(T["T2"]["winds_counted"] == 14 and gp["path_gate"] and 800 < gp["path_off_line_m"] < 900 and gp["range_bound"] < 0.005
          and gp["boots"] == 2000 and drift.unfixed(gp) is None,
          "14 winds counted, as before the gates (2026-11-02): the aircraft's path left a line by 855 m, the range's bound 0.0025, "
          "all 2,000 resamples fitted", f"{gp['path_off_line_m']:.0f} m, bound {gp['range_bound']:.4f}, {gp['boots']} resamples")
    check(gp["model_p"] is not None and 0.02 < gp["model_p"] < 0.2, "the model gate's F test is reported, not a refusal: p 0.054 on "
          "the known drifter", f"F {gp['model_F']:.2f}, p {gp['model_p']:.3f}")
    check(T["T3"]["outcome"] == drift.PASS and "one stretch" in T["T3"]["reading"],
          "T3: a beat in one window of 109, one stretch, not counted: passes", T["T3"]["reading"][:60])
    check(all(T[k]["outcome"] == drift.CANNOT for k in ("T4", "T4a", "T4b")), "T4: nothing shed, nothing struck, cannot "
          "say", T["T4"]["reading"][:60])
    check(found.fields["verdict"] == "consistent with wind-borne drift (tentative)", "verdict: tentative drift",
          found.fields["why"][:80])


def test_puerto_rico_lanterns_by_the_command_line():
    print("\nPuerto Rico lanterns: by the command line, from the aircraft's own track")
    if not PR_CLIP.exists():
        print(f"  SKIP  the clip is not on this computer ({PR_CLIP})")
        SKIP.append("Puerto Rico command line")
        return
    g = PR_GOLDEN
    with tempfile.TemporaryDirectory() as td:
        cmd = [sys.executable, "-m", "mcdonald.cli", "drift", str(PR_CLIP), "--platform", str(g / "platform.csv"),
               "--los", str(g / "los.csv"), "--winds", ",".join(sorted(str(p) for p in g.glob("wind_*.json"))),
               "--obs-winds", str(g / "obs_winds.csv"), "--ground-m", "72", "--when", "2013-04-27T01:22:47",
               "--flicker", str(g / "flicker.json"), "--out", str(Path(td) / "p"), "--json"]
        env = dict(__import__("os").environ, PYTHONPATH=str(reference_data.REPO / "src"))
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
        d = json.loads(p.stdout) if p.stdout.strip().startswith("{") else None
    if not check(p.returncode == 0 and d is not None and d["command"] == "drift", "one envelope on stdout",
                 f"exit {p.returncode} {p.stderr[-200:]}"):
        return
    T = {t["test"]: t["outcome"] for t in drift.flat(d["results"]["tests"])}
    check(T["T1"] == drift.PASS and T["T2"] == drift.PASS and T["T3"] == drift.PASS and T["T4"] == drift.CANNOT,
          "T1 and T2 pass from the track, T3 passes (one stretch, not counted), T4 cannot say",
          ", ".join(f"{k} {v}" for k, v in sorted(T.items())))
    check(d["results"]["verdict"] == "consistent with wind-borne drift (tentative)", "verdict: tentative drift")


SB_GOLDEN = reference_data.GOLDEN / "santa_barbara_drift"
SB_CLIP = reference_data.root() / "santa_barbara_2018" / "yt_7N8_g3pCK2o.mkv"
SB_FPS = 30000 / 1001


def test_santa_barbara_huey_from_its_beat():
    """The known flier: Santa Barbara County's UH-1H Huey, hovering in calm air to hoist two hikers off a ridge (12 Aug
    2018), filmed by a sheriff's OH-58A circling it (its pilot's upload, YouTube 7N8_g3pCK2o; the uap repository's
    analysis/cases/santa_barbara_hoist_2018/). Hovering in calm air it has no airspeed, so T1, T2 and T4 could not tell
    it from a drifter, and here they have nothing to run on: the turret held the stored hoist site, so no range or line
    of sight reaches the Huey, and nothing was shed or struck. `flicker` found 10.645 Hz, its main rotor's blade-pass,
    over the whole stretch (frames 13250-13530) and in windows apart: a beat that holds, so T3 fails and the verdict is
    not drifting."""
    print("\nSanta Barbara Huey: from its beat (no video)")
    found = drift.measure(SB_FPS, flicker=json.loads((SB_GOLDEN / "flicker.json").read_text(encoding="utf-8")))
    T = {t["test"]: t for t in drift.flat(found.fields["tests"])}
    check(all(T[k]["outcome"] == drift.CANNOT for k in ("T1", "T2", "T4", "T4a", "T4b")),
          "T1, T2 and T4: nothing to run on, cannot say", ", ".join(f"{k} {T[k]['outcome']}" for k in sorted(T)))
    check(T["T3"]["outcome"] == drift.FAIL and T["T3"].get("held") and "10.645" in T["T3"]["reading"],
          "T3: the rotor's 10.645 Hz holds across the stretch: fails", T["T3"]["reading"][:60])
    check(found.fields["verdict"] == "not drifting", "verdict: not drifting", found.fields["why"][:80])


def test_santa_barbara_huey_by_the_command_line():
    print("\nSanta Barbara Huey: by the command line, from its beat alone")
    if not SB_CLIP.exists():
        print(f"  SKIP  the clip is not on this computer ({SB_CLIP})")
        SKIP.append("Santa Barbara command line")
        return
    g = SB_GOLDEN
    with tempfile.TemporaryDirectory() as td:
        cmd = [sys.executable, "-m", "mcdonald.cli", "drift", str(SB_CLIP), "--flicker", str(g / "flicker.json"),
               "--out", str(Path(td) / "h"), "--json"]
        env = dict(__import__("os").environ, PYTHONPATH=str(reference_data.REPO / "src"))
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
        d = json.loads(p.stdout) if p.stdout.strip().startswith("{") else None
    if not check(p.returncode == 0 and d is not None and d["command"] == "drift", "one envelope on stdout",
                 f"exit {p.returncode} {p.stderr[-200:]}"):
        return
    T = {t["test"]: t["outcome"] for t in drift.flat(d["results"]["tests"])}
    check(T["T3"] == drift.FAIL and all(T[k] == drift.CANNOT for k in ("T1", "T2", "T4", "T4a", "T4b")),
          "T3 fails on the rotor's held beat, T1, T2 and T4 cannot say",
          ", ".join(f"{k} {v}" for k, v in sorted(T.items())))
    check(d["results"]["verdict"] == "not drifting", "verdict: not drifting")


P51_GOLDEN = reference_data.GOLDEN / "pr051_drift"
P51_FPS = 60000 / 1001


def test_pr051_second_leg_from_its_readings():
    """A second display for the route from the aircraft's own track: PR051's unredacted upload, the second leg of the
    MQ-9's turn (IDEAS.md DR1; 2026-11-13). The readings in tests/golden/pr051_drift/ were read off the data bar by an
    agent and have not been checked by a person; their headers say what a second agent checked, and which of them lie
    where the scene's motion is read (the ULTN field) and which where the bar alone carries them (the 4X zoom). Three of
    this session's rows show on it: the rays fit a hundred times closer than the errors given (DR3), the aircraft flew
    14.7 deg right of its heading box (DR2), and its one wind was read 1.4 km above the object (DR4)."""
    print("\nPR051, the second leg: from its readings (an agent's, not checked by a person; no video)")
    g = P51_GOLDEN
    platform, los = drift.read_platform(g / "platform.csv"), drift.read_los(g / "los.csv")
    flk = json.loads((g / "flicker.json").read_text(encoding="utf-8"))
    found = drift.measure(P51_FPS, platform=platform, los=los, ground_m=525.8, flicker=flk)
    T = {t["test"]: t for t in drift.flat(found.fields["tests"])}
    p, w = found.fields["ground_path"], T["T2"].get("aircraft_wind") or {}
    check(len(platform) == 23 and 9.0 <= p["speed_m_s"] <= 9.8 and 100 <= p["toward_deg"] <= 106 and 4270 <= p["height_m"] <= 4330
          and 10.9e3 <= p["range_m"][0] and p["range_m"][1] <= 11.8e3 and p["path_gate"] and p["range_bound"] < 0.05,
          "the path from 23 rays: 9.4 m/s toward 103 deg, 4,298 m above the sea, 11.0-11.7 km from the aircraft",
          f"{p['speed_m_s']:.2f} m/s toward {p['toward_deg']:.1f}, {p['height_m']:.0f} m, {p['range_m'][0] / 1e3:.2f}-{p['range_m'][1] / 1e3:.2f} km, "
          f"bound {p['range_bound']:.4f}")
    check(p["errors_from"] == "the rays' own scatter" and p["chi2_dof"] < 0.01 and 0.014 <= p["sigma_deg"][0] <= 0.023
          and p["sigma_deg"][1] < 0.006 and p["velocity_err_rays_m_s"] < 2.5,
          "DR3: the rays fit far closer than the errors given (reduced chi-square 0.0024), and the errors are their own scatter's",
          f"{p['sigma_deg'][0]:.4f} and {p['sigma_deg'][1]:.4f} deg; velocity +- {p['velocity_err_rays_m_s']:.2f} m/s from the scatter")
    check(T["T1"]["outcome"] == drift.PASS and abs(T["T1"]["climb_m_s"] - 0.08) <= 0.05 and 0.14 <= T["T1"]["climb_err_m_s"] <= 0.24,
          "T1: it holds its height, +0.08 +- 0.19 m/s (+- 2.74 until 2026-11-13)", T["T1"]["reading"])
    check(w.get("heading_offset_seen") and 13.0 <= w["heading_offset_deg"] <= 16.5 and abs(w["speed_m_s"] - 11.2) < 0.6
          and abs(w["from_deg"] - 265.7) < 4 and abs(w["as_displayed_speed_m_s"] - 21.6) < 0.5 and w["fixed"],
          "DR2: the aircraft flew 14.7 deg right of its heading box; its own wind is 11.2 m/s from 266 deg, where the box "
          "alone gives 21.6 from 211", f"{w.get('heading_offset_deg')} deg; {w.get('speed_m_s')} m/s from {w.get('from_deg')}")
    check(T["T2"]["outcome"] == drift.CANNOT and "no wind was read near its height" in T["T2"]["reading"]
          and 1380 <= T["T2"]["winds_level_gap_m"] <= 1460 and T["T2"]["wind_change_m_s"] > 12,
          "DR4: T2 cannot say, the only wind having been read 1.4 km above the object (it failed on that wind before)",
          T["T2"]["reading"][:110])
    check(T["T3"]["outcome"] == drift.PASS and found.fields["verdict"] == "cannot say",
          "T3 passes on the 4 s of the hold it was given; the verdict is cannot say", found.fields["verdict"])
    # this envelope records its band (0.5.3): a doubled source, 29.97 pictures a second on 59.94 frames, one frame in
    # two a repeat, heard to 12.0 Hz of the 24.0 its frame rate carries. The pass says so since 2026-11-17
    check(T["T3"]["reading"].startswith("no beat of its own between 1.5 and 12.0 Hz; only a beat over 12% of its brightness "
                                        "would have shown. Faster beats, up to the 24.0 Hz this frame rate could carry, were "
                                        "not listened for. 50% of the frames nearly repeat the one before in a steady pattern "
                                        "(1 of every 2), so the picture is new only 30.0 times a second.")
          and T["T3"]["smallest_beat_seen"] == 0.12,
          "T3 says the band it listened in, 1.5 to 12.0 Hz, and why it stops there: every second frame repeats the one "
          "before, a source of 30 pictures a second on 60 frames", T["T3"]["reading"][:120])
    # the readings of the ULTN field alone, the stretch where the scene's motion behind the object is read
    ultn = {f: v for f, v in platform.items() if f <= 3507}
    part = drift.measure(P51_FPS, platform=ultn, los={f: los[f] for f in ultn}, ground_m=525.8)
    Tu = {t["test"]: t for t in drift.flat(part.fields["tests"])}
    pu = part.fields.get("ground_path")
    check(len(ultn) == 13 and pu is not None and 4200 <= pu["height_m"] <= 4450 and Tu["T2"]["outcome"] == drift.CANNOT,
          "the 13 readings of the ULTN field alone put it at the same height, and T2 cannot say",
          f"{pu and round(pu['height_m'])} m; T1 {Tu['T1']['outcome']}: {Tu['T1']['reading'][:70]}; T2: {Tu['T2']['reading'][:100]}")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print(f"\n{'ALL PASS' if not FAIL else f'{len(FAIL)} FAILED: ' + ', '.join(FAIL)}"
          f"{f'  ({len(SKIP)} skipped: ' + ', '.join(SKIP) + ')' if SKIP else ''}")
    sys.exit(1 if FAIL else 0)
