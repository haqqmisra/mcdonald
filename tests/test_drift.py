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
rotor's held beat fails T3).

    python3 tests/test_drift.py        # or: pytest tests/

No video data needed but for the command-line runs on the three clips (the video gives the frame rate).
"""
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
    print("\nT2: the winds")
    air, w_air, w_obj = 90.0, np.array([10.0, 0.0]), np.array([0.0, 8.0])      # heading east; the object drifts north
    ground = air * np.array([1.0, 0.0]) + w_air
    out = drift.test_wind(line_of(w_obj - ground), 90.0, winds_of(w_obj, w_air), air_min_kn=0, air_max_kn=240)
    check(out["outcome"] == drift.PASS and abs(np.mean(out["airspeed_kn"]) - air / drift.KN) < 10,
          "a body drifting with the winds: the airspeed it needs is the aircraft's, passes",
          f"{out['airspeed_kn']} kn of {air / drift.KN:.0f}")
    drone = w_obj + 25.0 * np.array([0.0, -1.0])                                  # flying south across the heading
    out = drift.test_wind(line_of(drone - ground), 90.0, winds_of(w_obj, w_air), air_min_kn=0, air_max_kn=240)
    check(out["outcome"] == drift.CANNOT and not out["same_side"],
          "a drone crossing the heading against the winds' difference: cannot say (the test never fails)",
          out["reading"][:70])
    check(out["drones"]["25 m/s"]["flying_its_way_kn"] is not None, "and the airspeeds a 25-m/s drone would need are given")
    out = drift.test_wind(line_of(w_obj - ground), 90.0, winds_of(w_obj, w_air), air_min_kn=0, air_max_kn=120)
    check(out["outcome"] == drift.CANNOT, "an airspeed beyond the aircraft's range: cannot say")


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
    check(drift.verdict([dict(test="T2", outcome=drift.PASS, reading="")])[0].startswith("consistent"),
          "a passing T2 from the track is a strong test")
    near = wind + 5.0 * np.array([0.5, -0.866])
    platform, los, _ = orbit(v_obj=tuple(near))
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    check(drift.test_wind_track(p, winds)["outcome"] == drift.CANNOT, "5 m/s through the air: a slow flier's, cannot say")


def test_track_t2_a_models_own_error():
    print("\nT2 from the aircraft's own track: a model's winds carry their own error (2026-11-13)")
    # The Galileo Project's clouds, triangulated from three sites 2-5 km up, needed 3-4 m/s through the air against
    # Open-Meteo's winds: more than the winds' hour-to-hour spread. So a model's winds now carry MODEL_WIND_ERR as well.
    wind = np.array([-6.0, -3.5])
    rng = np.random.default_rng(7)
    winds = [dict(label=f"model {i}", w=wind + rng.normal(0, 0.3, 2), counts=True, note="model", source="model")
             for i in range(2)]
    obs = [dict(w, source="observed", note="observed") for w in winds]
    off = wind + 3.5 * np.array([0.6, 0.8])                   # a cloud that drifts, 3.5 m/s off the model's wind
    platform, los, _ = orbit(v_obj=tuple(off))
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    out = drift.test_wind_track(p, winds)
    check(out["outcome"] == drift.PASS and out["model_wind_err_m_s"] == drift.MODEL_WIND_ERR
          and "a model's own error" in out["reading"],
          "3.5 m/s off a model's winds: within the model's own error, passes", out["reading"][:120])
    out = drift.test_wind_track(p, obs)
    check(out["outcome"] == drift.CANNOT and out["model_wind_err_m_s"] == 0.0,
          "the same off observed winds: no model's error allowed, cannot say (the rule before 2026-11-13)",
          out["reading"][:120])
    flier = wind + 25.0 * np.array([0.5, -0.866])
    platform, los, _ = orbit(v_obj=tuple(flier))
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    check(drift.test_wind_track(p, winds)["outcome"] == drift.FAIL, "a flier at 25 m/s through the air still fails")
    f = Path(tempfile.mkdtemp()) / "w.json"
    f.write_text(json.dumps(dict(elevation=0.0, hourly=dict(
        time=["2026-01-01T00:00"], wind_speed_850hPa=[10.0], wind_direction_850hPa=[270.0],
        geopotential_height_850hPa=[1500.0], wind_speed_700hPa=[20.0], wind_direction_700hPa=[270.0],
        geopotential_height_700hPa=[3000.0]))))
    tw = drift.track_winds(2000.0, model=[str(f)],
                           observed=[dict(source="sonde", height_m=1800.0, from_deg=270.0, speed_m_s=10.0),
                                     dict(source="sonde", height_m=2500.0, from_deg=270.0, speed_m_s=12.0)])
    check([w["source"] for w in tw] == ["model", "observed"], "each wind says where it came from",
          str([w["source"] for w in tw]))


def test_track_t2_holding_still_against_drifting():
    print("\nT2 from the aircraft's own track: drifting must fit better than holding still (2026-11-13)")
    # A body holding still over the ground needs the wind's own speed through the air. In a light wind that is within
    # T2's tolerance, and it passed as a drifter (IDEAS.md N2). The comparative rule asks every drifter's airspeed to be
    # under the weakest wind's: the Puerto Rico lanterns (1.4-3.6 m/s against 4.5-9.5) keep their pass.
    light = np.array([2.4, -1.8])                             # 3 m/s
    winds = [dict(label=f"model {i}", w=light + d, counts=True, note="model", source="model")
             for i, d in enumerate((np.zeros(2), np.array([0.3, 0.2])))]
    platform, los, _ = orbit(v_obj=(0.0, 0.0), climb=0.0)
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    out = drift.test_wind_track(p, winds)
    check(out["outcome"] == drift.CANNOT and "holding still fits as well" in out["reading"] and not out["drift_beats_hold"],
          "a body holding still in a 3 m/s wind: cannot say, where it passed before", out["reading"][:110])
    platform, los, _ = orbit(v_obj=tuple(light), climb=0.0)
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    out = drift.test_wind_track(p, winds)
    check(out["outcome"] == drift.PASS and out["drift_beats_hold"],
          "a drifter in that light wind still passes: it needs well under the 3 m/s holding still would", out["reading"][-90:])
    strong = [dict(w, w=w["w"] * 6.0) for w in winds]       # 18 m/s
    platform, los, _ = orbit(v_obj=tuple(strong[0]["w"]), climb=0.0)
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    out = drift.test_wind_track(p, strong)
    check(out["outcome"] == drift.PASS and out["drift_beats_hold"] and "holding still would need" in out["reading"],
          "a drifter in an 18 m/s wind: passes, holding still needing more at every wind", out["reading"][-90:])
    platform, los, _ = orbit(v_obj=(0.0, 0.0), climb=0.0)
    p = drift.fit_track(drift.rays(platform, los, FPS), (0.1, 0.03), nboot=200)
    check(drift.test_wind_track(p, strong)["outcome"] == drift.FAIL, "holding still in that 18 m/s wind: fails, as before")


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
    check(drift.verdict([P("T1"), P("T2"), F("T3"), other(P("T4a", tracer_depth="same"))])[0] == "not drifting",
          "any test failed (a beat held across the video, a hovering rotor's): not drifting, whatever passed")
    check(drift.verdict([P("T2"), C("T3")])[0].startswith("consistent with wind-borne drift"),
          "T3 without power (cannot say) leaves a strong pass (T2) standing")
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
          and abs(t2["sideways_right_kn"] - 23.2) < 0.5,
          "T2: the winds need 179-191 kn of the aircraft, and lie the way its motion does",
          f"{t2['airspeed_kn']} kn, {t2['sideways_right_kn']} kn to the right")
    left = [n[1] for n in t2["needs_kn"]]
    check(len(left) == t2["samples"] and 4 <= min(left) and max(left) <= 19,
          "and what the winds leave the aircraft to fly sideways is to its left, 5-18 kn (their shortfall)",
          f"{min(left)}-{max(left)} kn")
    check(t3["outcome"] == drift.PASS and t3["smallest_beat_seen"] == 0.41, "T3: no beat over 41 %")
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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print(f"\n{'ALL PASS' if not FAIL else f'{len(FAIL)} FAILED: ' + ', '.join(FAIL)}"
          f"{f'  ({len(SKIP)} skipped: ' + ', '.join(SKIP) + ')' if SKIP else ''}")
    sys.exit(1 if FAIL else 0)
