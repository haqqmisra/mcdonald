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
      sinking at a steady rate, and a wreck falling as a 5-m body falls. How the parts combine
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
    check(model[0]["counts"] and abs(np.hypot(*model[0]["w"]) - 14 * drift.KN) < 1e-6,
          "a model held at its top level (100 m above its ground) for an object above it")
    s = W["sounding"]
    check(s["counts"] and 5.0 < np.hypot(*s["w"]) < 7.0, "a sounding that brackets it: interpolated, counts",
          f"{np.hypot(*s['w']):.2f} m/s")
    check(not W["metar"]["counts"], "a surface report far below it: read, not counted")
    b = W["between metar and the aircraft's own"]
    check(b["counts"] and 4.0 < np.hypot(*b["w"]) < np.hypot(-8, -4), "between the report below and the aircraft's own "
          "wind above: the measured profile, counts", f"{np.hypot(*b['w']):.2f} m/s")


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
    check(out["outcome"] == drift.PASS and out["excludes_wrecks_under_m"] >= 20,
          "a steady sink excludes a falling wreck of every body under 20 m: passes", f"{out['excludes_wrecks_under_m']} m")
    a = 9.81 * math.cos(math.radians(40)) / 5.0 * L                 # a 5-m body, 20 px long, falling
    fallen = {int(f): (0.0, 0.5 * a * s ** 2 + rng.normal(0, 0.3)) for f, s in zip(n, t)}
    f = drift.fall(fallen, FPS, np.random.default_rng(0))
    out = drift.test_wreck(f["accel_px_s2"] / L, f["accel_err"] / L, 40.0)
    check(out["outcome"] == drift.FAIL and abs(out["accel_L_per_s2"] - a / L) < 0.1,
          "a 5-m wreck falling at g: fails", f"{out['accel_L_per_s2']} of {a / L:.2f} lengths/s^2")
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
    check(t4b["outcome"] == drift.PASS and abs(t4b["accel_L_per_s2"] + 0.08) < 0.02
          and 60 <= t4b["excludes_wrecks_under_m"] <= 90,
          "T4b: no falling wreck under ~75 m", f"{t4b['accel_L_per_s2']} +- {t4b['accel_err']}, "
          f"{t4b['excludes_wrecks_under_m']} m")
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
