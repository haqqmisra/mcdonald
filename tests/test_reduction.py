"""Do the Phase 2 modules reduce correctly? Known answers, no video data.

Covers symbology (angle conventions, bearings), kinematics (the three
equations, and the robust fit that keeps a bad track from producing a clean
wrong number), scale (the routes to k), comotion (the verdict boundaries) and
report (that a case with nothing in it still says so honestly).

    python3 tests/test_reduction.py        # or: pytest tests/

Several checks below are anchored to published values — PR113's graticule,
PR149's ship bound, PR142's transit — so a change that moves them fails here
rather than in a manuscript.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import comotion, kinematics as kin, report, scale, symbology as sym  # noqa: E402

FAIL = []


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def close(a, b, tol):
    return a is not None and abs(a - b) <= tol


# ---------------------------------------------------------------- symbology
def test_the_angle_convention_is_what_it_claims():
    """One convention package-wide: clockwise from screen-up, so that a motion
    direction and a north-pointer reading can be differenced."""
    print("\nsymbology: the angle convention")
    bore = (100.0, 100.0)
    for (px, py), want, name in (((100, 50), 0, "straight up"),
                                 ((150, 100), 90, "to the right"),
                                 ((100, 150), 180, "straight down"),
                                 ((50, 100), 270, "to the left")):
        r, th = sym.bearing(px, py, bore)
        check(close(th, want, 0.01), f"{name} reads {want} deg", f"got {th:.1f}")
    r, _ = sym.bearing(100, 50, bore)
    check(close(r, 50, 0.01), "radius is the distance from the boresight", f"{r:.2f}")


def test_a_bearing_is_the_difference():
    print("\nsymbology: screen direction -> bearing")
    # north drawn straight down (theta 180) means the camera looks north
    check(close(sym.true_bearing(0, 180), 180, 0.01),
          "moving up the screen while north points down is due south")
    check(close(sym.true_bearing(90, 0), 90, 0.01),
          "moving right while north points up is due east")
    check(close(sym.true_bearing(10, 350), 20, 0.01), "wraps across 0/360")


def test_rotation_rate_and_its_sanity_check():
    """The radius is the check: the pointer is drawn at a fixed radius, so a
    wandering radius means mislocated frames and untrustworthy angles."""
    print("\nsymbology: rotation rate, and the radius check")
    t = np.arange(0, 10, 0.5)
    good = np.column_stack([t * 30 + 1, t, np.zeros_like(t), np.zeros_like(t),
                            np.full_like(t, 295.0), (250 + 0.4 * t) % 360, np.ones_like(t)])
    rr = sym.rotation_rate(good)
    check(close(rr["dtheta_dt"], 0.4, 0.01), "recovers +0.400 deg/s", f"{rr['dtheta_dt']:+.3f}")
    check(rr["r_frac_sd"] < 1e-6, "a fixed radius reads as fixed", f"{rr['r_frac_sd']:.1e}")
    s = sym.cross_los_sense(rr["dtheta_dt"])
    check(s["platform"] == "image-right" and s["parallax"] == "image-left",
          "positive rotation -> platform right, parallax left")
    s2 = sym.cross_los_sense(-0.4)
    check(s2["platform"] == "image-left" and s2["parallax"] == "image-right",
          "and the mirror case")
    check(sym.cross_los_sense(0.0)["platform"] is None,
          "no measurable rotation is undetermined, not zero")

    wild = good.copy()
    wild[:, 4] += np.linspace(0, 60, len(t))
    check(sym.rotation_rate(wild)["r_frac_sd"] > 0.02,
          "a wandering radius is flagged", f"{sym.rotation_rate(wild)['r_frac_sd']:.3f}")


def test_seam_crossing_does_not_break_the_fit():
    print("\nsymbology: angles across the 0/360 seam")
    t = np.arange(0, 10, 0.5)
    th = (355 + 1.0 * t) % 360          # crosses 360 -> 0
    s = np.column_stack([t * 30 + 1, t, np.zeros_like(t), np.zeros_like(t),
                         np.full_like(t, 295.0), th, np.ones_like(t)])
    rr = sym.rotation_rate(s)
    check(close(rr["dtheta_dt"], 1.0, 0.01), "unwrapped before fitting",
          f"{rr['dtheta_dt']:+.3f} deg/s (a naive fit gives a large negative)")


# ---------------------------------------------------------------- kinematics
def test_the_three_equations_against_published_values():
    """PR113, as published in the Technical Note."""
    print("\nkinematics: the published PR113 reduction")
    k = kin.AngularScale.from_graticule(35.4)
    check(close(k.k, 2028.3, 0.1), "k from the graticule", f"{k.k:.1f} px/rad (published 2028.3)")
    om = kin.omega(142.0 * 30.0, k)
    check(close(om, 2.100, 0.002), "omega = v_px f / k", f"{om:.3f} rad/s (published 2.100)")
    check(close(25.0 / k.k, 0.01233, 1e-5), "object angular size", f"{25.0 / k.k:.5f} rad")
    check(close(kin.fov_from_k(k.k, 1920, small_angle=True), 54.2, 0.2),
          "small-angle FOV", f"{kin.fov_from_k(k.k, 1920, small_angle=True):.1f} deg (paper: ~54)")
    check(close(kin.fov_from_k(k.k, 1920), 50.7, 0.2),
          "full sec^2 FOV", f"{kin.fov_from_k(k.k, 1920):.1f} deg")
    k54s = 1920 / math.radians(54)
    k54f = 960 / math.tan(math.radians(27))
    check(close(k54s / k54f, 1.08, 0.005),
          "the small-angle form overstates k by 8 % at FOV 54", f"{k54s / k54f:.3f}")


def test_k_grows_toward_the_frame_edge():
    print("\nkinematics: k is not a constant across the frame")
    k0 = kin.AngularScale.from_fov(1920, 54.0, 0.0)
    corner = math.degrees(math.atan(math.hypot(960, 540) / kin.f_px_from_fov(1920, 54.0)))
    ke = k0.at(corner)
    check(ke.k > k0.k, "k is larger at the corner", f"{k0.k:.0f} -> {ke.k:.0f} px/rad")
    check(close(ke.k / k0.k, 1.34, 0.06), "by about a third", f"ratio {ke.k / k0.k:.2f} (paper: 34 %)")


def test_the_scale_bar_route_reproduces_the_published_bound():
    """PR149: 920 px of hull, a 150-200 m vessel."""
    print("\nkinematics: the in-frame scale bar (PR149)")
    lo = kin.scale_bar_speed(604.5, 920.0, 150.0) * 1.94384
    hi = kin.scale_bar_speed(604.5, 920.0, 200.0) * 1.94384
    check(close(lo, 192, 2), "150 m LOA -> 192 kn", f"{lo:.0f} kn")
    check(close(hi, 255, 3), "200 m LOA -> 255 kn", f"{hi:.0f} kn (published ceiling 192-257)")
    check(close(kin.scale_bar_speed(604.5, 920.0, 180.0, range_ratio=0.5),
                kin.scale_bar_speed(604.5, 920.0, 180.0) * 0.5, 1e-9),
          "a nearer object scales down linearly with the range ratio")


def test_the_range_free_speed():
    print("\nkinematics: body-lengths per second (needs nothing)")
    v = kin.body_lengths_per_s(604.5, 4.18)
    check(close(v, 145, 1), "PR149 contact", f"{v:.0f} /s (published: above 110)")
    check(kin.body_lengths_per_s(100.0, 0) is None, "a zero size yields None, not infinity")


def test_a_speed_needs_everything_and_says_so():
    print("\nkinematics: the refusal to invent a speed")
    r = kin.Reduction(540.0, 30.0)
    check(r.speed() is None, "no k, no R -> no speed")
    check(len(r.missing) == 4, "and all four unknowns are named", ", ".join(r.missing))
    check("Nothing here converts to m/s" in r.report(), "the report says so plainly")

    r2 = kin.Reduction(540.0, 30.0, kin.AngularScale.from_fov(1920, 10.0), R_m=5000)
    check(r2.speed() is not None, "with k and R a speed appears")
    check(close(r2.lower_bound(), r2.omega * 5000, 1e-6), "theta=90 is the lower bound")
    check(r2.speed() >= r2.lower_bound() - 1e-9, "and no aspect angle goes below it")
    check("RELATIVE" in r2.report(), "and it is labelled relative, not object, speed")


def test_a_bad_track_cannot_produce_a_clean_number():
    """The PR142 lesson: a detection file is not a track. Spurious detections
    must be clipped, and motion that is not uniform must be flagged."""
    print("\nkinematics: robust fitting")
    t = np.arange(0, 3, 1 / 30)
    n = np.arange(len(t)) + 1
    x, y = 100 + 500 * t, 200 + 120 * t
    clean = np.column_stack([n, x, y])
    f = kin.fit_v_px(clean, 30.0)
    check(close(f["v_px"], math.hypot(500, 120), 0.01), "recovers a clean rate",
          f"{f['v_px']:.1f} px/s")
    check(f["uniform"], "and calls it uniform")

    dirty = clean.copy()
    dirty[::4, 1] += 700           # a quarter of frames latch onto something else
    fd = kin.fit_v_px(dirty, 30.0)
    check(close(fd["v_px"], math.hypot(500, 120), 3.0),
          "clips outliers and still recovers it", f"{fd['v_px']:.1f} px/s, {fd['n_clipped']} clipped")
    check(fd["n_clipped"] > 0, "and reports how many it dropped")

    curved = np.column_stack([n, 100 + 300 * t ** 2, y])
    fc = kin.fit_v_px(curved, 30.0, clip_sigma=1e9, iters=0)
    check(not fc["uniform"], "accelerating motion is flagged NOT uniform",
          f"residual {fc['resid_frac']:.1%} of span")
    check("NOT UNIFORM" in kin.Reduction(fc["v_px"], 30.0, fit=fc).report(),
          "and the reduction refuses to let it pass quietly")


def test_time_not_frames():
    """Repeated frames make position-against-frame a staircase; the rate
    against wall-clock time survives it."""
    print("\nkinematics: rates are against wall-clock time")
    fps, V = 30.0, 350.0                     # the object really moves 350 px/s
    n, x = [], []
    for i in range(1, 91):
        # every 7th frame repeats its predecessor: the display did not update,
        # so the recorded position is the PREVIOUS frame's, not this frame's
        src = i - 1 if i % 7 == 0 else i
        n.append(i)
        x.append(V * (src - 1) / fps)
    a = np.column_stack([n, x, np.zeros(len(n))])
    f = kin.fit_v_px(a, fps, clip_sigma=1e9, iters=0)
    check(close(f["v_px"], V, V * 0.02), "mean rate survives repeated frames",
          f"{f['v_px']:.1f} px/s (truth {V:.0f})")

    # the same data read per frame: the median survives, individual readings do not
    d = np.diff(x) * fps
    zero = float((np.abs(d) < 1).mean())
    double = float((d > 1.5 * V).mean())
    check(zero > 0.1 and double > 0.1,
          "while individual per-frame readings are 0 or double",
          f"{zero:.0%} read as stationary, {double:.0%} read as ~2x -- "
          "which is why a single frame pair is never a rate")


# ---------------------------------------------------------------- scale
def test_the_fov_ladder_shows_the_spread():
    print("\nscale: the FOV ladder")
    rows = scale.fov_ladder(540.0, 1920, (3, 10, 30, 54), ranges_m=(5000,))
    lo, hi = rows[0]["speeds"][5000], rows[-1]["speeds"][5000]
    check(hi / lo > 15, "plausible fields span more than an order of magnitude",
          f"{lo:.0f} to {hi:.0f} m/s at 5 km = x{hi / lo:.0f}")
    check(rows[0]["k"] > rows[-1]["k"], "a narrow field means a larger k")


def test_k_from_a_reference_at_known_range():
    print("\nscale: k from a known-size object at a known range")
    k = scale.k_from_reference(920.0, 180.0, 12000.0)
    check(close(k, 920 * 12000 / 180, 1e-6), "k = p R / S", f"{k:.0f} px/rad")
    back = kin.object_size(920.0, 12000.0, k)
    check(close(back, 180.0, 1e-6), "and it round-trips through the size equation")


def test_measure_reference_finds_a_synthetic_bar():
    """A dark bar of known length and angle on a noisy field."""
    print("\nscale: measuring an in-frame reference")
    rng = np.random.default_rng(7)
    g = rng.normal(180, 6, (400, 700))
    L, ang = 240.0, 12.0
    ax = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
    c = np.array([350.0, 200.0])
    for s_ in np.arange(-L / 2, L / 2, 0.25):
        for o in np.arange(-6, 6.5, 0.5):
            p = c + ax * s_ + np.array([-ax[1], ax[0]]) * o
            g[int(round(p[1])), int(round(p[0]))] = 40
    m = scale.measure_reference(g, (350, 200), angles=np.arange(0, 25, 0.5), extent=220)
    check(m is not None, "the bar is found")
    if m:
        check(close(m["length_px"], L, 8), "length within 8 px", f"{m['length_px']:.1f} (truth {L})")
        check(close(m["angle_deg"], ang, 1.5), "angle within 1.5 deg",
              f"{m['angle_deg']:.1f} (truth {ang})")


# ---------------------------------------------------------------- comotion
def test_comotion_verdicts_have_an_honest_middle():
    print("\ncomotion: verdict boundaries")
    check(comotion.verdict(0.4, 0.2)[0] == "CARRIED", "under one diameter is carried")
    check(comotion.verdict(2.0, 1.0)[0] == "INCONCLUSIVE", "the middle is named, not forced")
    check(comotion.verdict(18.1, 2.47)[0] == "MOVES THROUGH", "PR055 moves through")
    check(comotion.verdict(None, None)[0] == "NO POWER", "nothing measured is NO POWER")
    check("NOT a statement that the motion is anomalous" in comotion.verdict(18.1, 2.47)[1],
          "and the strong verdict carries its own caveat")


def test_comotion_integrates_relative_motion_correctly():
    print("\ncomotion: object minus field")
    # object moves 10 px/pair, the field 4 px/pair, both to the right
    rows = [(i, i + 5, 1 / 6, 10.0, 0.0, 4.0, 0.0, 6.0, 0.0, 12, 0.3) for i in range(1, 31, 5)]
    s = np.array(rows, float)
    tot = comotion.integrate(s, diameter_px=12.0)
    check(close(tot["rel_D"], 6 * len(rows) / 12.0, 1e-6), "relative displacement in D",
          f"{tot['rel_D']:.2f} D")
    check(close(tot["obj_D"] - tot["flow_D"], tot["rel_D"], 1e-6),
          "object - field is the difference, measured on the same pairs")
    check(close(tot["rel_dir_deg"], 90.0, 0.01), "direction is clockwise from screen-up")


# ---------------------------------------------------------------- marking
def test_marks_carry_everything_the_linker_needs():
    """Two clicks are the whole human input: a seed and a velocity."""
    print("\nmark: what two clicks produce")
    import matplotlib
    matplotlib.use("Agg")
    from mcdonald.mark import MarkSet
    ms = MarkSet("pr113", "/tmp/x.mp4", 30.0)
    check(ms.velocity() is None, "no velocity from zero marks")
    ms.add("object", 408, 1009.0, 313.0)
    check(ms.velocity() is None, "nor from one")
    ms.add("object", 411, 702.0, 604.0)
    v = ms.velocity()
    check(v is not None and abs(v[0] + 102.3) < 0.2 and abs(v[1] - 97.0) < 0.2,
          "two marks give the velocity", f"({v[0]:+.1f}, {v[1]:+.1f})")
    check(ms.seed() == (408, 1009.0, 313.0), "and the seed is the first mark")
    check(ms.count() == 2, "count is across all classes")
    ms.add("boresight", 408, 960.0, 540.0)
    check(ms.count() == 3 and ms.velocity() == v,
          "a mark of another class does not disturb the object track")
    check(ms.remove_last("object", 411) is not None and ms.velocity() is None,
          "deleting a mark takes the velocity with it")


def test_marks_round_trip_and_read_back_as_a_track():
    print("\nmark: files")
    import tempfile
    import matplotlib
    matplotlib.use("Agg")
    from mcdonald import forensics as vf
    from mcdonald.mark import MarkSet
    with tempfile.TemporaryDirectory() as td:
        ms = MarkSet("t", "/tmp/x.mp4", 30.0)
        for n, x, y in ((10, 100.0, 200.0), (20, 300.0, 260.0), (30, 500.0, 320.0)):
            ms.add("object", n, x, y)
        j = ms.save(f"{td}/t_marks.json")
        again = MarkSet("t", "/tmp/x.mp4", 30.0).load(j)
        check(again.track() == ms.track(), "JSON round-trips")
        c = ms.write_track_csv(f"{td}/t_marks.csv")
        t = vf.read_track(c)
        check(t == ms.track(), "and the CSV reads back through the package's own reader",
              f"{len(t)} rows")
        check(open(c).readline().startswith("#"),
              "the CSV carries a provenance header, which read_track skips")


def test_a_snapped_mark_never_passes_for_a_hand_mark():
    """A mark snapped to the detector's centroid agrees with the detector because
    it is the detector's. It has to say so everywhere it goes."""
    print("\nmark: provenance")
    import tempfile
    import matplotlib
    matplotlib.use("Agg")
    from mcdonald import forensics as vf
    from mcdonald.mark import MarkSet
    ms = MarkSet("t", "/tmp/x.mp4", 30.0)
    ms.add("object", 10, 100.0, 200.0)
    ms.add("object", 20, 300.4, 260.2, how="snapped to the 21 px dark candidate 1.8 px from a click at (301.9, 259.2)")
    check(ms.how_of("object", 10) is None and "snapped" in ms.how_of("object", 20), "a mark is by hand unless it says otherwise")
    check(ms.by_hand() == {10: (100.0, 200.0)}, "and the hand marks can be asked for alone")
    check(ms.velocity() is not None, "a snapped mark still counts toward the velocity: it is a position")
    with tempfile.TemporaryDirectory() as td:
        again = MarkSet("t", "/tmp/x.mp4", 30.0).load(ms.save(f"{td}/t_marks.json"))
        check(again.how == ms.how and again.marks == ms.marks, "provenance round-trips through the JSON")
        c = ms.write_track_csv(f"{td}/t_marks.csv")
        text = open(c).read()
        check(vf.read_track(c) == ms.track(), "the CSV still reads back as the same track")
        rows = [ln for ln in text.splitlines() if not ln.startswith("#")]
        check("1 of 2 are NOT hand positions" in text and rows[1].endswith(",hand") and "snapped to the 21 px" in rows[2],
              "and says, in its header and on the row, which mark is not a hand's")
    ms.add("object", 20, 301.0, 259.0)
    check(ms.how_of("object", 20) is None, "placing it again by hand makes it a hand mark")
    ms.add("object", 30, 1.0, 1.0, how="snapped")
    ms.remove_last("object", 30)
    check("how" not in ms.to_dict(), "and a file with only hand marks is the file it always was")
    ms.add("horizon", 7, 1.0, 1.0)
    ms.remove_last("horizon", 7)
    check("horizon" not in ms.marks, "deleting a class's last mark leaves no empty class behind")
    old = MarkSet("t", "/tmp/x.mp4", 30.0)
    old.marks = {"object": {5: (1.0, 2.0)}}
    with tempfile.TemporaryDirectory() as td:
        import json as _json
        p = f"{td}/old_marks.json"
        open(p, "w").write(_json.dumps({"tag": "t", "video": "/tmp/x.mp4", "fps": 30.0, "classes": {"object": {"5": [1.0, 2.0]}}}))
        check(MarkSet("t", "/tmp/x.mp4", 30.0).load(p).marks == old.marks, "a marks file from before provenance still loads")
        open(p, "w").write(_json.dumps({"classes": {"object": {"408": [1009, 313]}}}))
        by_hand = MarkSet("t", "/tmp/x.mp4", 30.0).load(p)
        check(by_hand.marks == {"object": {408: (1009.0, 313.0)}} and isinstance(by_hand.marks["object"][408][0], float),
              "and so does one written by hand or by an agent: four lines, whole numbers, nothing but the marks")


# ---------------------------------------------------------------- report
def test_an_empty_case_still_says_something_honest():
    print("\nreport: a case with nothing in it")
    c = report.Case("testclip", "/tmp/testclip.mp4")
    md = c.markdown()
    check("No stage produced a result" in md, "says no result rather than implying one")
    check("No catalog record" in md, "and disclaims provenance")
    c.add("kinematics", dict(v_px="540 px/s"),
          no_power=[("speed", "no k and no R")], needs=["a sourced range"])
    md = c.markdown()
    check("What this clip cannot decide" in md and "no k and no R" in md,
          "no-power entries are rendered, never dropped")
    check("a sourced range" in md, "and so is what would close it")
    check("custody question" in md, "the composite caveat is always present")
    import json as _json
    check(_json.loads(c.json())["stages"]["kinematics"]["needs"] == ["a sourced range"],
          "the JSON carries the same structure")


def test_the_bottom_line_calls_a_rate_the_objects_only_when_it_is():
    """Until 2026-09-20 `mcdonald run` with no track at all printed "The object moves 340
    px/s against the striated" on PR144: the sea's screen speed over one frame pair, from
    the look at the background, under the object's name. The object against the sea on
    those frames is 599."""
    print("\nreport: whose rate the bottom line says it is")
    from mcdonald import layers, stages
    c = report.Case("testclip", "/tmp/testclip.mp4")
    c.add("track", no_power=[("track", "no track supplied, so every object measurement is skipped")])
    report.Found("layers", {"motion groups": 2, "striated layer": "340 px/s (40 templates)"},
                 dict(pair=[300, 305], motion_groups=2, scene_held_still=False, screen_px_per_s={"striated": 340.1},
                      templates={"striated": 40})).into(c)
    line = c.bottom_line()
    check("object moves" not in line and "340" not in line, "a look at the background, with no track, is not the object's rate", line[:90])
    check("No object was tracked" in line, "and the bottom line says that nothing was tracked")

    spread = lambda m: dict(median=m, p16=m - 9, p84=m + 9, min=m - 20, max=m + 20, windows=80)
    fields = dict(of="the object's rate against each layer", tracked=True, k=5, step=1,
                  names={"striated": "sea", "isotropic": "cloud tops"},
                  px_per_s={"striated": spread(599.0), "isotropic": spread(500.0), "all": spread(507.0)},
                  layer_against_layer=spread(99.0),
                  object_over_parallax=dict(ratio=6.0, ratio_p16=6.0, ratio_p84=6.4, directions_apart_deg=10.0),
                  motion_groups=dict(two_in_share_of_pairs=0.403, apart_px_per_s=97.0, inside_a_group_share=0.71))
    c = report.Case("testclip", "/tmp/testclip.mp4")
    c.add("track", dict(source="t.csv", frames=201, span="300-500"))
    report.Found("layers", fields=fields).into(c)
    line = c.bottom_line()
    check("599 px/s against the sea" in line and "500 px/s against the cloud tops" in line and "name neither layer" in line,
          "a measurement of the object against each layer is named by layer", line[:120])
    said = "\n".join(layers.said(fields))
    check("the sea" in said and "median   599" in said and "ratio 6.0 (6.0-6.4), directions +10 deg apart" in said
          and "two in 40.3% of pairs, 97 px/s apart" in said,
          "and what `mcdonald layers` prints is written from the same fields, so the prose cannot disagree with them")

    track = {n: (100.0 + 18.0 * (n - 1), 50.0 + 2.0 * (n - 1)) for n in range(1, 40)}
    f = stages.kinematics(track, 30.0, 1920, "t", size_px=12.0)
    v = float(np.hypot(18.0, 2.0)) * 30.0
    check(abs(f.fields["v_px_per_s"] - v) < 1e-6 and f.result["v_px"] == f"{v:.1f} px/s" and f.fields["relative_speed_m_per_s"] is None
          and abs(f.fields["body_lengths_per_s"] - v / 12.0) < 1e-6,
          "stages.kinematics: the fields are the numbers, and the report's lines are made from them",
          f"{f.fields['v_px_per_s']:.3f} px/s")
    c = report.Case("testclip", "/tmp/testclip.mp4")
    f.into(c)
    line = c.bottom_line()
    check(f"The object moves {v:.0f} px/s in the image" in line and "does not convert to a physical speed" in line
          and "k (angular scale)" in line, "with no scale and no range the bottom line says the rate does not convert, and names what is missing",
          line[:130])
    import json as _json
    back = _json.loads(c.json())["stages"]["kinematics"]
    check(back["fields"]["v_px_per_s"] == f.fields["v_px_per_s"] and back["result"]["v_px"] == f.result["v_px"],
          "and the case file carries both: the number, and the line")
    f = stages.kinematics({1: (0.0, 0.0), 2: (1.0, 1.0)}, 30.0, 1920)
    check(f.no_power == [("kinematics", "track too short to fit a rate")] and not f.result and f.carry is None,
          "a track too short to fit is a stage with no power, not an exception")


def main():
    print("McDonald UAP Toolkit — reduction self-check")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{'ALL PASS' if not FAIL else str(len(FAIL)) + ' FAILED: ' + ', '.join(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
