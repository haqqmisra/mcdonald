"""Four readings that need none of the unknowns, or say what each is worth (method section 61).

Drawn data with known answers, and the vendored tracks of known objects; no video needed.

- the class table: every number has a source beside it;
- the speed in body lengths a second (IDEAS.md Av11): a lower bound at every aspect, exact where the body's length shows
  longest; what a lower bound excludes and what it cannot; NO POWER where the camera moved;
- a turn as a load-factor curve (Av10): the turn rate from a loop and from a bend with the tilt's band, the fastest each
  class could have flown it, and the class that could not;
- the value of information per unknown (D8): one unknown by hand, two against quadrature, both measures; an unknown
  ranked first only where the two measures agree;

    python3 tests/test_unknowns.py        # or: pytest tests/
"""
import math
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import envelopes as env, forensics as vf, kinematics as kin, projective, stages  # noqa: E402
from mcdonald.report import Case  # noqa: E402
import traffic  # noqa: E402 -- the binomial zone for checks on drawn data (E20)

FAIL = []
GOLDEN = Path(__file__).resolve().parent / "golden"
HEAD = "class,member,length_m,span_m,speed_min_m_s,speed_min_is,speed_max_m_s,load_limit_g,size_source,speed_source,load_source,note\n"
# a small table with round numbers, for answers worked by hand
DRAWN = HEAD + ("big jets,jet A,30,30,60,least,250,2.5,a,b,c,\n"
                "small birds,bird B,0.2,0.3,8,least,20,7.8,a,b,c,\n"
                "balloons,balloon C,0.5,,0,drifts,0,,a,b,,\n"
                "wind,a strong jet stream,,,,,100,,,b,,\n")


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


MADE = []                                 # the drawn tables written to the temporary folder: taken away again by main()


def drawn_table(text=DRAWN):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
    f.write(text)
    f.close()
    MADE.append(f.name)
    return f.name


def words_ok(sentences, label):
    long = [s for s in sentences if len(s.split()) > 40]
    check(not long and not any(" thing" in s for s in sentences), f"{label}: every sentence under 40 words, and no 'thing'",
          f"{long}")


# ------------------------------------------------------------------------------------------ the class table
def test_every_number_of_the_class_table_has_a_source():
    print("\nthe class table: every number with its source")
    bad = env.unsourced()
    check(not bad, "no number of class_envelopes.csv is without a source", f"{bad[:5]}")
    cl = env.classes()
    names = " ".join(cl)
    for want in ("bird", "airliner", "light aircraft", "fighter", "helicopter", "balloon", "multirotor"):
        check(want in names, f"the table has a class of {want}s", names if want not in names else "")
    groups = [n for n in cl if "group" in n]
    check(len(groups) == 5, "and the five unmanned aircraft groups of the US Department of Defense", f"{groups}")
    check(all(c["per_s"][0] <= c["per_s"][1] for c in cl.values() if c["per_s"]), "each class's range runs from low to high")
    wind, src = env.strongest_wind()
    check(wind and wind > 50 and src, "the strongest wind is in the table, with its source", f"{wind} m/s")
    limits = {n: c["load_limit_g"] for n, c in cl.items() if c["load_limit_g"]}
    check(len(limits) >= 5 and all(c["load_source"] for c in cl.values() if c["load_limit_g"]),
          "at least five classes carry a limit load, each sourced", f"{limits}")
    a = next(c for n, c in cl.items() if "airliner" in n)
    check(2.0 < a["per_s"][1] < 12.0, "an airliner at its fastest covers a handful of its lengths a second",
          f"{a['per_s'][0]:.1f}-{a['per_s'][1]:.1f}")
    check(env.unsourced(drawn_table(HEAD + "x,y,1,,,,,,,,,\n")) == [("x", "y", "length_m")], "a number without a source is caught")
    t = drawn_table(HEAD + "jets,a,30,,65,approach,250,2.5,s,s,s,\njets,b,60,,78,approach,,2.5,s,s,s,\n")
    c = env.classes(t)["jets"]
    check(abs(c["speed_m_s"][0] - 50.0) < 1e-9 and abs(c["per_s"][0] - 1.0) < 1e-9 and abs(c["per_s"][1] - 250 / 30) < 1e-9,
          "an approach speed is 1.3 times the stall speed (14 CFR 97.3): the least speed is the stall's; a row with no greatest "
          "speed still gives its length and its least speed", f"{c['speed_m_s']}, {c['per_s']}")


# ------------------------------------------------------------------------------------------ Av11
def picture(theta_deg, psi_deg, L=30.0, b=34.0, v=200.0, R=3.0e5, f=2000.0, dt=0.01):
    """A body of length L along its velocity and span b across it, at the aspect angle theta and with its wings rolled
    psi about the velocity (0: the wing axis in the plane of the velocity and the line of sight), through a pinhole at
    range R: (rate px/s, largest extent px, the fuselage's projected length px, the span's)."""
    th, ps = math.radians(theta_deg), math.radians(psi_deg)
    vh = np.array([math.sin(th), 0.0, math.cos(th)])
    wh = math.cos(ps) * np.array([math.cos(th), 0.0, -math.sin(th)]) + math.sin(ps) * np.array([0.0, 1.0, 0.0])
    c0 = np.array([0.0, 0.0, R])
    proj = lambda X: f * X[:2] / X[2]
    rate = float(np.linalg.norm(proj(c0 + v * dt * vh) - proj(c0))) / dt
    body = float(np.linalg.norm(proj(c0 + L / 2 * vh) - proj(c0 - L / 2 * vh)))
    span = float(np.linalg.norm(proj(c0 + b / 2 * wh) - proj(c0 - b / 2 * wh)))
    return rate, max(body, span), body, span


def test_body_lengths_a_second_is_a_lower_bound_at_every_aspect():
    """The geometry behind Av11's bound: the picture shows the speed across the line of sight and the body's length along
    its travel, each foreshortened by sin(theta), and anything else of the body that shows can only widen the extent."""
    print("\nAv11: the rate over the extent, on drawn bodies at every aspect")
    L, v = 30.0, 200.0
    worst, exact, low = 0.0, [], []
    for th in (5, 15, 30, 45, 60, 75, 90, 105, 135, 165):
        for ps in (0, 20, 45, 70, 90):
            rate, extent, body, span = picture(th, ps, L=L, v=v)
            ratio = rate / extent
            worst = max(worst, ratio / (v / L))
            (exact if body >= span else low).append(ratio / (v / L))
    check(worst <= 1.001, "the ratio is never above the true speed over the true length", f"at most {worst:.4f} of it")
    check(exact and all(abs(x - 1) < 1e-3 for x in exact), "it equals it wherever the body's own length shows longest",
          f"{len(exact)} aspects, {min(exact):.4f}-{max(exact):.4f}")
    check(low and min(low) < 0.2, "and reads far under it where the body points nearly at the camera with its wings across",
          f"{len(low)} aspects, down to {min(low):.3f}")
    rate, extent, _, _ = picture(40, 0, L=2.0, b=0.0, v=10.0)        # a slender body: the two foreshortenings cancel
    check(abs(rate / extent - 5.0) < 5e-3, "a slender body reads its true 5 lengths a second at 40 degrees to the line of sight",
          f"{rate / extent:.4f}")
    rate, _, _, _ = picture(30, 0, L=0.5, b=0.5, v=10.0)             # a ball 0.5 m across shows its diameter at any aspect
    ball = rate / (0.5 * 2000.0 / 3.0e5)
    check(abs(ball - 10.0) < 0.05, "a ball at 30 degrees reads sin(30) of its 20 diameters a second", f"{ball:.3f}")


def test_what_a_lower_bound_excludes():
    print("\nAv11: a lower bound against the classes (a drawn table)")
    t = drawn_table()
    cl = env.classes(t)
    check(np.allclose(cl["big jets"]["per_s"], (2.0, 250 / 30)) and np.allclose(cl["small birds"]["per_s"], (40.0, 100.0)),
          "a class's range is its least and greatest speeds over its length", f"{cl['big jets']['per_s']}")
    c = env.against_classes(5.0, t)
    check(c["within"] == ["big jets"] and c["faster"] == ["small birds"] and c["with_wind"] == [("balloons", 2.5)],
          "5 a second: within the jets, under the birds (not excluded), a balloon in a wind of 2.5 m/s", f"{c}")
    c = env.against_classes(9.0, t)
    check(c["with_wind"][0] == ("big jets", 20.0), "9 a second: a jet only with a tail wind of 9 x 30 - 250 = 20 m/s", f"{c['with_wind']}")
    c = env.against_classes(20.0, t)
    check(c["outside"] == ["big jets"] and c["faster"] == ["small birds"],
          "20 a second: outside the jets even with the strongest wind (350 m/s needed, 100 the most); birds not excluded", f"{c}")
    c = env.against_classes(50.0, t)
    check(c["within"] == ["small birds"] and "balloons" in [n for n, _ in c["with_wind"]], "50 a second: within the birds")
    c = env.against_classes(0.5, t)
    check(not c["outside"] and c["with_wind"] == [("balloons", 0.25)] and c["faster"] == ["big jets", "small birds"],
          "nothing is excluded for being slow: a lower bound excludes only from above", f"{c}")


def test_body_lengths_has_no_power_where_the_camera_moved():
    print("\nAv11: the reading, and where it has none")
    t = drawn_table()
    still, held, moved = dict(moving=False, why=None), dict(moving=None, why="the picture behind it held still on screen"), \
        dict(moving=True, why="the camera flew at 100 m/s")
    b = env.body_lengths(150.0, 30.0, "given", True, still, t)
    check(b["power"] and b["per_s"] == 5.0 and b["classes"]["within"] == ["big jets"] and b["bound"] == "at least",
          "a still camera and a resolved object: at least 5 a second, against the classes")
    value, how = env.lengths_said(b)
    check(value == "at least 5 body lengths a second" and "in the range of big jets" in how and "lower bound" in how,
          "said as a bound, with the classes it is in the range of", value)
    S = env.lengths_plain(b)
    check(any("at least 5 body lengths a second" in s for s in S) and any("does not identify" in s for s in S),
          "the plain sentences say it is a lower limit and that sharing a range identifies nothing")
    words_ok(S, "body lengths")
    for plat, word in ((held, "unless the camera stood still"), (moved, "the camera flew")):
        b = env.body_lengths(150.0, 30.0, "given", True, plat, t)
        check(not b["power"] and word in b["why"] and b["classes"] is None and not env.lengths_plain(b),
              f"no power where the camera {'moved' if plat is moved else 'may have followed it'}", b["why"][:90])
    b = env.body_lengths(150.0, None, None, None, still, t)
    check(not b["power"] and "length" in b["why"], "no power with no length", b["why"])
    b = env.body_lengths(150.0, 3.0, "given", False, still, t)
    check(b["power"] and b["unit"] == "blur widths" and b["classes"] is None, "an unresolved object: blur widths, and no class")
    S = env.lengths_plain(b)
    check(any("No kind of object is read from a blur" in s for s in S) and not any("range of" in s for s in S),
          "the sentences name no class for a blur")
    words_ok(S, "blur widths")


# ------------------------------------------------------------------------------------------ Av10
def test_the_tilt_band_of_a_turn_rate_read_from_a_short_arc():
    """TILT_RATE recomputed: the picture's heading turns at cos i / (sin²φ + cos²i cos²φ) of the turn's own rate."""
    print("\nAv10: the tilt's band on a turn rate")
    n = 4000
    ci = (np.arange(n) + 0.5) / n
    ph = (np.arange(n) + 0.5) / n * 2 * np.pi
    C, P = np.meshgrid(ci, ph, indexing="ij")
    own = (np.sin(P) ** 2 + C ** 2 * np.cos(P) ** 2) / C            # the turn's own rate over the picture's
    lo, hi = np.percentile(own, [5, 95])
    check(abs(lo - env.TILT_RATE[0]) < 0.005 and abs(hi - env.TILT_RATE[1]) < 0.1,
          "the turn's own rate is 0.44 to 10 times the picture's nine times in ten", f"{lo:.3f}-{hi:.2f}")


def arc(deg, tilt_deg=0.0, phase_deg=0.0, r=120.0, w=0.8, fps=30.0, jitter=0.0, seed=0, turn_in_view=0.0):
    """A track going round a circle of radius r px at w rad/s through `deg` degrees, its plane tilted, from the phase
    given: {frame: (x, y)}."""
    rng = np.random.default_rng(seed)
    n = max(int(round(math.radians(deg) / w * fps)), 8)
    t = np.arange(n) / fps
    ph = math.radians(phase_deg) + w * t
    x, y = r * np.cos(ph), r * math.cos(math.radians(tilt_deg)) * np.sin(ph)
    a = math.radians(turn_in_view)
    x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
    return {i + 1: (float(600 + x[i] + rng.normal(0, jitter)), float(400 + y[i] + rng.normal(0, jitter))) for i in range(n)}, t[-1] - t[0]


def test_the_load_factor_and_the_speed_it_allows():
    print("\nAv10: the arithmetic")
    check(abs(env.load_factor(1.0, 15.0) - 1.83) < 0.01 and abs(env.load_factor(1.0, 200.0) - 20.4) < 0.05,
          "1 rad/s: 1.8 g at a bird's 15 m/s, 20 g at 200 m/s (the aviation survey's two)", f"{env.load_factor(1.0, 15.0):.2f}, {env.load_factor(1.0, 200.0):.1f}")
    v = env.speed_at(1.0, 2.5)
    check(abs(v - env.G * math.sqrt(5.25)) < 1e-9 and abs(env.load_factor(1.0, v) - 2.5) < 1e-9,
          "held to 2.5 g at 1 rad/s: no faster than g sqrt(2.5² - 1) = 22.5 m/s", f"{v:.2f}")
    check(env.speed_at(1.0, 1.0) is None and env.speed_at(0.0, 2.5) is None, "no speed from a limit of 1 g, or from no turn")


def test_the_turn_rate_from_a_loop_and_from_a_bend():
    print("\nAv10: the turn rate, from drawn turns")
    trk, span = arc(420, tilt_deg=40.0, jitter=0.2, seed=3)
    tn = projective.turn(trk, 30.0, 6.0)
    r = env.turn_rate(tn, span)
    check(tn["how"] == "ellipse" and r["how"] == "loop" and abs(r["omega_rad_per_s"] - 0.8) < 0.02,
          "a loop of 420 degrees tilted 40: the rate read whole, the same at any tilt", f"{r.get('omega_rad_per_s', 0):.3f} for 0.800")
    check(r.get("omega_err_rad_per_s") and r["lo"] <= 0.8 <= r["hi"], "with its error from the track's own covariance",
          f"{r.get('lo', 0):.4f}-{r.get('hi', 0):.4f}")
    trk, span = arc(40, jitter=0.05, seed=1)
    tn = projective.turn(trk, 30.0, 6.0)
    r = env.turn_rate(tn, span)
    check(r.get("how") == "bend" and abs(r["omega_rad_per_s"] / 0.8 - 1) < 0.05 and abs(r["heading_deg"] - 40) < 3,
          "a bend of 40 degrees seen face on: the heading swept over the time", f"{r.get('omega_rad_per_s', 0):.3f} rad/s, {r.get('heading_deg', 0):.1f} deg")
    # the tilt's band: arcs of 30 degrees at random tilts and places on the circle, no jitter
    rng = np.random.default_rng(11)
    n, miss = 200, 0
    for _ in range(n):
        tilt, ph = math.degrees(math.acos(rng.uniform(0.0, 1.0))), rng.uniform(0, 360)
        trk, span = arc(30, tilt_deg=tilt, phase_deg=ph, turn_in_view=rng.uniform(0, 360))
        tn = projective.turn(trk, 30.0, 1.0)
        r = env.turn_rate(dict(tn, bent=True, swings=None), span)      # every drawn arc is a bend: no noise to hold it to
        miss += not (r["lo"] <= 0.8 <= r["hi"])
    traffic.rate(check, "the band from the tilt holds the turn's own rate about nine times in ten", miss, n, 0.10, two_sided=True)
    check("why" in env.turn_rate(dict(bent=False, swings=None, how="sagitta"), 3.0), "no rate from a track that does not bend")
    check("swings" in env.turn_rate(dict(bent=True, swings=dict(arc_deg=705), how="sagitta", sagitta_px=5, length_px=200), 3.0)["why"],
          "nor from one that swings about with no loop claimed (PR077's object 1): a sagitta is for a small bend")


def test_which_class_could_have_flown_the_turn():
    print("\nAv10: the curve against the classes (a drawn table)")
    t = drawn_table()
    still = dict(moving=False, why=None)
    loop = dict(how="ellipse", ellipse=dict(omega_rad_per_s=1.0, omega_err_rad_per_s=0.0, arc_deg=400.0), bent=True, swings=None)
    c = env.load_curve(loop, 7.0, still, None, t)
    by = {r["cls"]: r for r in c["limits"]}
    check(c["power"] and abs(by["big jets"]["v_max_m_s"] - 22.47) < 0.01 and by["big jets"]["could"] is False,
          "at 1 rad/s a body held to 2.5 g flies no faster than 22.5 m/s: under the jets' least 60, so not theirs",
          f"{by['big jets']['v_max_m_s']:.2f}")
    check(abs(by["small birds"]["v_max_m_s"] - env.G * math.sqrt(7.8 ** 2 - 1)) < 1e-6 and by["small birds"]["could"],
          "a bird held to 7.8 g could have, at up to 76 m/s", f"{by['small birds']['v_max_m_s']:.1f}")
    check("balloons" not in by, "a class with no limit load has no row")
    slow = dict(loop, ellipse=dict(omega_rad_per_s=0.2, omega_err_rad_per_s=0.0, arc_deg=400.0))
    check({r["cls"]: r for r in env.load_curve(slow, 30.0, still, None, t)["limits"]}["big jets"]["could"],
          "at 0.2 rad/s the jets could have flown it (112 m/s)")
    bend = dict(how="sagitta", bent=True, swings=None, sagitta_px=10.0, length_px=200.0, ellipse=None)
    c = env.load_curve(bend, 0.5, still, None, t)
    w = 4 * math.atan(0.1) / 0.5
    r = {x["cls"]: x for x in c["limits"]}["big jets"]
    check(c["how"] == "bend" and abs(c["omega_rad_per_s"] - w) < 1e-9 and abs(r["v_max_most_m_s"] - env.speed_at(env.TILT_RATE[0] * w, 2.5)) < 1e-9,
          "a bend: each class's speed at the slowest turn the tilt allows, the most it could be", f"{r['v_max_most_m_s']:.0f} m/s")
    lengths = env.body_lengths(150.0, 30.0, "given", True, still, t)       # 5 lengths a second
    c = env.load_curve(loop, 7.0, still, lengths, t)
    r = {x["cls"]: x for x in c["limits"]}["small birds"]
    check(abs(r["length_max_m"] - r["v_max_most_m_s"] / 5.0) < 1e-9 and r["could"] and not r["too_long"],
          "with 5 lengths a second: the longest body within a class's limit is its speed limit over 5", f"{r['length_max_m']:.1f} m")
    j = {x["cls"]: x for x in c["limits"]}["big jets"]
    check(j["too_long"] and abs(j["length_max_m"] - 22.47 / 5) < 0.01 and "no longer than 4.49 m" in env.load_said(c)[1],
          "a jet within 2.5 g at 5 lengths a second would be under 4.5 m long, and they are 30: said beside the speed's verdict",
          f"{j['length_max_m']:.2f} m")
    slow_c = env.load_curve(slow, 30.0, still, None, t)
    jb = {x["cls"]: x for x in slow_c["limits"]}
    check(jb["big jets"]["binds"] and not jb["small birds"]["binds"] and any("gentle enough for small birds" in s_ for s_ in env.load_plain(slow_c)),
          "a limit binds only inside the speeds a class flies at: at 0.2 rad/s the jets' does (112 m/s), the birds' does not (379)")
    for plat in (dict(moving=None, why="held"), dict(moving=True, why="moved")):
        c = env.load_curve(loop, 7.0, plat, None, t)
        check(not c["power"] and "camera" in c["why"] and not c["limits"] and not env.load_plain(c),
              f"no power where the camera {'moved' if plat['moving'] else 'may have turned'}", c["why"][:80])
    c = env.load_curve(loop, 7.0, still, None, t)
    S = env.load_plain(c)
    check(any("not theirs" in s for s in S) and any("level turn" in s for s in S), "the plain sentences name the class that could not, and the conditions")
    words_ok(S, "the load")
    value, how = env.load_said(c)
    check(value.startswith("n(V)") and "could not have flown it" in how, "the trade's row carries the curve and the verdict")


def test_the_stage_reads_both_and_draws_the_curve():
    print("\nthe kinematics stage: the two readings, their rows and the figure")
    trk, _ = arc(420, tilt_deg=30.0, jitter=0.2, seed=5)
    with tempfile.TemporaryDirectory() as d:
        f = stages.kinematics(trk, 30.0, 1280, "drawn", None, size_px=8.0, out=str(Path(d) / "drawn"), height=720)
        kf = f.fields
        check(kf["body_lengths"]["power"] and kf["load_curve"]["power"] and kf["load_curve"]["how"] == "loop",
              "a drawn loop on a camera nothing says moved: both readings have power")
        check(abs(kf["body_lengths"]["per_s"] - kf["body_lengths_per_s"]) < 1e-12, "the bound is the row's own number, unmoved")
        check(any(p.endswith("_load.png") for p in f.files) and Path(d, "drawn_load.png").stat().st_size > 10000,
              "the load-factor figure is drawn")
        check("turn as a load factor" in f.result and "body lengths against the classes" in f.result, "each has its result line")
        check(not any(n in ("body lengths against the classes", "turn as a load factor") for n, _ in f.no_power),
              "and neither adds to the stage's no-power list")
        case = Case("drawn", "drawn.mp4")
        case.add("kinematics", f.result, fields=kf, no_power=f.no_power)
        rows = {r[0]: r for r in case.summary()}
        check(rows["speed in body lengths"][2].startswith("at least") and rows["turn as a load factor"][2].startswith("n(V)"),
              "the summary has both rows")
        said = " ".join(case.track_said())
        check("body lengths a second" in said and "load factor" in said, "and the paragraph both readings")
    moved = dict(held_still=dict(share_of_pairs=0.9, still_again_share=0.9))
    f = stages.kinematics(trk, 30.0, 1280, "drawn", None, size_px=8.0, layers=moved)
    np0 = len(f.no_power)
    check(not f.fields["load_curve"]["power"] and not f.fields["body_lengths"]["power"]
          and "turn as a load factor" not in f.result, "where the picture behind held still on screen, neither has power")
    case = Case("drawn", "drawn.mp4")
    case.add("kinematics", f.result, fields=f.fields, no_power=f.no_power)
    rows = {r[0]: r for r in case.summary()}
    check(rows["turn as a load factor"][2] is None and rows["turn as a load factor"][3].startswith("NO POWER")
          and rows["speed in body lengths"][2] is None, "the summary's rows say NO POWER, with why", rows["turn as a load factor"][3][:80])
    f2 = stages.kinematics(trk, 30.0, 1280, "drawn", None, layers=moved)
    check(f2.fields["body_lengths"]["why"].startswith("needs the object's length") and len(f2.no_power) <= np0,
          "with no length given the row says what it needs")


def test_a_known_bird_on_a_still_camera():
    """Galileo flyer 4 (a bird over the one camera known to stand still, its track vendored): the loop the turn test reads
    is a turn rate, and the load it takes at a bird's speed is within what birds are measured to bear."""
    print("\nAv10 on a known bird: Galileo flyer 4's loop")
    trk = vf.read_track(GOLDEN / "flyer4_paper_track.csv")
    f = stages.kinematics(trk, 60.0, 640, "flyer4", None, size_px=9.0, height=512)
    c = f.fields["load_curve"]
    check(c["power"] and c["how"] == "loop", "the loop gives a turn rate", f"{c.get('omega_rad_per_s', 0):.2f} rad/s, {c.get('lo', 0):.2f}-{c.get('hi', 0):.2f}")
    birds = [r for r in c["limits"] if "bird" in r["cls"]]
    check(birds and all(r["could"] for r in birds), "and birds could have flown it",
          "; ".join(f"{r['cls']} to {r['v_max_most_m_s'] or r['v_max_m_s']:.0f} m/s" for r in birds))
    n15 = env.load_factor(c["omega_rad_per_s"], 15.0)
    check(1.0 < n15 < 3.0, "at a bird's 15 m/s the turn takes under 3 times its weight", f"{n15:.2f}")


# ------------------------------------------------------------------------------------------ D8
def H(p):
    p = np.clip(p, 1e-300, 1 - 1e-16)
    return -(p * np.log2(p) + (1 - p) * np.log2(1 - p))


def test_the_value_of_information_where_it_can_be_worked_by_hand():
    print("\nD8: one unknown, answers by hand")
    # k 1000 px/rad and 100 px/s: 0.1 rad/s. Across the line of sight, a still camera, the range 10 m to 10 km: v = 0.1 R
    v = kin.value_of_information(100.0, 1000, k=1000.0, R_min=10.0, R_max=10000.0, theta_deg=90.0, v_own=0.0, v_cap=1e9)
    check(v["unknown"] == ["R"], "only the range is unknown")
    for i, (v0, lo_p, ev_p) in enumerate(((30.0, math.log(30) / math.log(1000), 290 / 9990), (343.0, math.log(343) / math.log(1000), 3420 / 9990))):
        inv, ev = v["measures"]["invariant"]["questions"][i], v["measures"]["evenly"]["questions"][i]
        check(abs(inv["p"] - lo_p) < 0.006 and abs(ev["p"] - ev_p) < 0.004,
              f"under {v0:g} m/s: {lo_p:.3f} with the range log-uniform and {ev_p:.3f} evenly, by hand (the same region, two answers)",
              f"{inv['p']:.4f}, {ev['p']:.4f}")
        check(inv["asks"]["R"]["share"] > 0.9 and ev["asks"]["R"]["share"] > 0.85 and inv["first"] == "R" and v["questions"][i]["first"] == "R",
              "knowing the range settles nearly all of it (all but the one bin the threshold falls in), and both measures say so",
              f"{inv['asks']['R']['share']:.3f}, {ev['asks']['R']['share']:.3f}")
        check(inv["asks"]["R"]["p_lo"] == 0.0 and inv["asks"]["R"]["p_hi"] == 1.0, "once known, the answer is yes or no")
    # the range known too, the direction free: v = 20 / sin(theta); under 30 m/s where sin(theta) > 2/3
    v = kin.value_of_information(100.0, 1000, k=1000.0, R=200.0, v_own=0.0)
    inv, ev = v["measures"]["invariant"]["questions"][0], v["measures"]["evenly"]["questions"][0]
    check(v["unknown"] == ["θ"] and abs(inv["p"] - math.sqrt(1 - 4 / 9)) < 0.005,
          "the direction isotropic: under 30 m/s with the chance sqrt(1 - (20/30)²) = 0.745", f"{inv['p']:.4f}")
    cap = kin.V_CAP
    check(abs(ev["p"] - math.sqrt(500) / math.sqrt(cap ** 2 - 400)) < 0.002,
          "the range rate drawn evenly up to the speed cap: 0.022 (the same clip, another answer: why two measures are kept)", f"{ev['p']:.4f}")
    check(inv["first"] == "θ" and inv["asks"]["θ"]["share"] > 0.8, "and the aspect angle would settle it", f"{inv['asks']['θ']['share']:.3f}")
    v = kin.value_of_information(100.0, 1000, k=1000.0, R=200.0, theta_deg=90.0, v_own=0.0)
    check(v["power"] is False and "none of the four" in v["why"], "nothing unknown: nothing to ask for", v.get("why", ""))
    check(kin.value_of_information(0.0, 1000)["power"] is False, "no rate: no question")


def test_the_value_of_information_of_two_unknowns_against_quadrature():
    """k and R both unknown, the motion across the line of sight, a still camera, no cap: v = 100 R / k, and the mutual
    information of [v < 30] with each is an integral over one variable, done here on a grid."""
    print("\nD8: two unknowns, against quadrature")
    W, vpx, v0, R1, R2, (f1, f2) = 1000, 100.0, 30.0, 100.0, 100000.0, kin.VOI_FOV
    k_of = lambda f: (W / 2) / np.tan(np.radians(f) / 2)
    k1, k2 = float(k_of(f2)), float(k_of(f1))
    got = kin.value_of_information(vpx, W, R_min=R1, R_max=R2, theta_deg=90.0, v_own=0.0, v_cap=1e12)
    n = 20001
    # invariant: ln k and ln R uniform
    lr, lk = np.linspace(math.log(R1), math.log(R2), n), np.linspace(math.log(k1), math.log(k2), n)
    c = math.log(v0 / vpx)
    pR = np.clip((math.log(k2) - (lr - c)) / (math.log(k2) - math.log(k1)), 0, 1)        # P(ln k > ln R - c)
    pk = np.clip(((lk + c) - math.log(R1)) / (math.log(R2) - math.log(R1)), 0, 1)        # P(ln R < ln k + c)
    exact = {"invariant": (float(pR.mean()), float(H(pR.mean()) - H(pR).mean()), float(H(pk.mean()) - H(pk).mean()))}
    # evenly: the field of view and the range uniform
    R, f = np.linspace(R1, R2, n), np.linspace(f1, f2, n)
    f_at = lambda k: 2 * np.degrees(np.arctan(W / 2 / k))                                # the field whose k is this
    pR = np.clip((f_at(vpx * R / v0) - f1) / (f2 - f1), 0, 1)                            # P(k > 100 R / 30) = P(f < f_at)
    pk = np.clip((v0 * k_of(f) / vpx - R1) / (R2 - R1), 0, 1)
    exact["evenly"] = (float(pR.mean()), float(H(pR.mean()) - H(pR).mean()), float(H(pk.mean()) - H(pk).mean()))
    for m in ("invariant", "evenly"):
        q = got["measures"][m]["questions"][0]
        p, bR, bk = exact[m]
        check(abs(q["p"] - p) < 0.005, f"{m}: the chance now", f"{q['p']:.4f} for {p:.4f}")
        check(abs(q["asks"]["R"]["bits"] - bR) < 0.02 and abs(q["asks"]["k"]["bits"] - bk) < 0.02,
              f"{m}: the bits the range and the scale would each settle, to 0.02 of the integral",
              f"R {q['asks']['R']['bits']:.3f} for {bR:.3f}, k {q['asks']['k']['bits']:.3f} for {bk:.3f}")
        check(q["order"][0] == ("R" if bR > bk else "k"), f"{m}: and their order", f"{q['order']}")
    again = kin.value_of_information(vpx, W, R_min=R1, R_max=R2, theta_deg=90.0, v_own=0.0, v_cap=1e12)
    check(again == got, "the same case gives the same table twice (seeded draws)")


def test_the_asks_are_ranked_only_where_both_measures_agree():
    print("\nD8: the ranking, and where there is none")
    q = lambda p, bits, first: dict(p=p, bits_open=float(H(p)), first=first, order=sorted(bits, key=lambda s: -bits[s]),
                                    asks={s: dict(bits=b, bits_err=0.001, share=b / float(H(p)), p_lo=0.0, p_hi=1.0) for s, b in bits.items()})
    def voi(a, b, agree):
        return dict(power=True, unknown=["k", "R"], measures=dict(evenly=dict(questions=[a]), invariant=dict(questions=[b])),
                    questions=[dict(v0=30.0, what="under 30 m/s", agree=agree, first=a["first"] if agree else None, settled=False)])
    S = kin.information_said(voi(q(0.3, dict(k=0.1, R=0.6), "R"), q(0.5, dict(k=0.2, R=0.7), "R"), True))
    check(len(S) == 1 and "the range would settle the most" in S[0] and "68 to 70 %" in S[0], "both name the range: it is ranked first", S[0])
    S = kin.information_said(voi(q(0.3, dict(k=0.5, R=0.2), "k"), q(0.5, dict(k=0.2, R=0.7), "R"), False))
    check("disagree" in S[0] and "none is ranked" in S[0] and "One names the angular scale, and the other the range" in S[0],
          "one names the scale, the other the range: the row says so and ranks nothing", S[0])
    S = kin.information_said(voi(q(0.3, dict(k=0.40, R=0.401), None), q(0.5, dict(k=0.2, R=0.7), "R"), False))
    check("too close to rank" in S[0], "the same first, but not clear of the next in one: too close to rank", S[0])
    words_ok(S, "the asks")
    S = kin.information_said(voi(q(0.00002, dict(k=0.0, R=0.0), None), q(0.5, dict(k=0.2, R=0.7), "R"), False))
    check("One names nothing, the answer being all but settled there, and the other the range" in S[0],
          "a chance of one in fifty thousand under one measure: nothing is left to settle there, and the row says so", S[0])
    # a real disagreement, from the measures themselves: a camera that may be standing still or flying, the range bounded
    v = kin.value_of_information(100.0, 1000, k=1000.0, R_min=100.0, R_max=400.0, theta_deg=90.0)
    a, b = (v["measures"][m]["questions"][0] for m in ("evenly", "invariant"))
    print(f"        evenly: p {a['p']:.3f}, " + ", ".join(f"{s} {a['asks'][s]['bits']:.3f}" for s in a["order"])
          + f"; invariant: p {b['p']:.3f}, " + ", ".join(f"{s} {b['asks'][s]['bits']:.3f}" for s in b["order"]))
    check(v["questions"][0]["agree"] == (a["first"] is not None and a["first"] == b["first"]), "agreement is the two firsts being one and the same")


def test_the_ledger_carries_the_asks():
    print("\nD8: in the case's ledger")
    trk = {i + 1: (100.0 + 3.0 * i, 300.0 + 0.5 * i) for i in range(90)}
    f = stages.kinematics(trk, 30.0, 1280, "drawn", None)
    case = Case("drawn", "drawn.mp4")
    case.clip = dict(width=1280, height=720, fps=30.0)
    case.add("kinematics", f.result, fields=f.fields, no_power=f.no_power)
    v = case.value_of_information()
    check(v and v["power"] and v["unknown"] == ["k", "R", "θ", "v_own"], "a track and nothing else: all four are unknown")
    L = case._ledger()
    text = "\n".join(L)
    check("### Which missing quantity to ask for first" in text and text.count("| Is its own speed") == 8,
          "the report's ledger has the table: two questions by four unknowns")
    check("it says nothing about the object" in text, "and says what it is not")
    prose = [s for line in L if line and not line.startswith(("|", "#")) for s in line.lstrip("- ").split(". ")]
    words_ok(prose, "the asks' words")
    import json
    check("value_of_information" in json.loads(case.json()), "the case's JSON carries it")
    check(case.value_of_information() is v, "worked out once for a case as it stands")
    held = Case("held", "held.mp4")
    held.clip = dict(width=1280, height=720, fps=30.0)
    still = {i + 1: (400.0 + 0.01 * (i % 2), 300.0) for i in range(90)}
    fh = stages.kinematics(still, 30.0, 1280, "held", None)
    held.add("kinematics", fh.result, fields=fh.fields, no_power=fh.no_power)
    check(held.value_of_information() is None and held._asks() == [], "a track the camera held has no rate of its own: no table")


def main():
    try:
        for name, fn in list(globals().items()):
            if name.startswith("test_") and callable(fn):
                fn()
    finally:
        for made in MADE:
            Path(made).unlink(missing_ok=True)
    for w in traffic.WARNS:
        print("  WARN ", w)
    print(f"\n{len(FAIL)} FAILED: {', '.join(FAIL)}" if FAIL else "\nALL PASS")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
