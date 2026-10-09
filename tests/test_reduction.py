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


class _Overlay:
    """A 300-frame clip whose pointer is a 16 x 12 block 150 px above the centre, in
    `colour`: white like PR135's "N", or orange like PR144's. Counts the frames read."""
    n0, n1, W, H, fps = 1, 300, 480, 400, 30.0

    def __init__(self, colour):
        self.colour, self.read = colour, 0

    def t(self, n):
        return (n - self.n0) / self.fps

    def rgb(self, n):
        self.read += 1
        a = np.random.default_rng(n).integers(40, 90, (self.H, self.W, 1)).repeat(3, 2).astype(np.uint8)
        a[44:60, 234:246] = self.colour
        return a

    def grey(self, n):
        return self.rgb(n).mean(2)


def test_symbology_auto_gives_up_early_on_a_pointer_it_cannot_see():
    """PR135 draws north as a white "N". `auto` found no colour on the first frame, fell
    to hue (warm colours), read 600 frames for eight minutes and found nothing. A method
    chosen for it is now tried on a few frames first, and the stage ends there, saying
    what would find a white glyph; one that finds the pointer goes on over the clip."""
    print("\nsymbology: auto tries a few frames before the whole clip")
    said = []
    white = _Overlay((255, 255, 255))
    f = sym.measure(white, step=3, progress=lambda text, done=None, total=None: said.append((text, done, total)))
    F = f.fields
    check(F["method"] == "hue" and F["trial"] == dict(frames=sym.TRIAL, solved=0) and F["frames_solved"] == 0,
          "a white pointer: hue is tried on 20 frames and solves none", str(F["trial"]))
    check(white.read <= 2 * sym.TRIAL + 3, "and the other 80 frames are not read (the 20 twice: to try, and to list glyphs)",
          f"{white.read} frames read")
    check("--method template --tpl-box" in f.no_power[0][1], "it says what finds a white pointer", f.no_power[0][1][:60])
    g = F["glyphs_to_try"] or []
    check(len(g) >= 1 and np.hypot(g[0]["x"] - 239.5, g[0]["y"] - 51.5) < 8 and "--tpl-box " + ",".join(map(str, g[0]["tpl_box"]))
          in f.no_power[0][1], "and it lists the glyph the template can follow, with its box (the agent's 9 a)",
          str(g[:1]))
    check(said and said[-1][1:] == (sym.TRIAL, sym.TRIAL), "and it says how far along it is while it tries")
    orange = _Overlay((255, 128, 0))
    F = sym.measure(orange, step=3, progress=lambda *a, **k: None).fields
    check(F["trial"] == dict(frames=sym.TRIAL, solved=sym.TRIAL) and F["frames_solved"] == 100,
          "an orange pointer passes the trial and every frame is read", f"{F['frames_solved']} solved")
    check(sym.measure(_Overlay((255, 255, 255)), step=3, method="hue").fields["frames_tried"] == 100,
          "hue asked for by name is not second-guessed: every frame is tried")


class _Turning(_Overlay):
    """The white 16 x 12 block turning about (240, 202) at `rate` deg/s, 150.5 px out, drawn
    with each pixel as bright as the share of it the block covers, so it sits between pixels."""

    def __init__(self, rate, colour=(255, 255, 255)):
        super().__init__(colour)
        self.rate = rate

    def rgb(self, n):
        self.read += 1
        a = np.random.default_rng(n).integers(40, 90, (self.H, self.W)).astype(float)
        th = np.radians(self.rate * self.t(n))
        cx, cy = 240.0 + 150.5 * np.sin(th), 202.0 - 150.5 * np.cos(th)      # the centre of the block
        cover = lambda lo, hi, m: np.clip(np.minimum(np.arange(m) + 1, hi) - np.maximum(np.arange(m), lo), 0, 1)
        k = np.outer(cover(cy - 8, cy + 8, self.H), cover(cx - 6, cx + 6, self.W))
        a = a * (1 - k) + 255 * k
        return a[..., None].repeat(3, 2).astype(np.uint8)


def test_symbology_says_how_finely_it_reads_the_angle_and_how_the_boresight_moves_it():
    """PR135's template reading put the "N" at one whole-pixel position on 600 frames:
    honest for a glyph that does not move, but at r = 198 a pixel is 0.29 deg, and nothing
    said so. And its theta was 1.3 deg from the hand tool's, whose boresight was ~4 px away:
    theta is only as good as the boresight, and nothing said that either. Jacob then asked
    for the template's peak between pixels (2026-09-23): the step is gone, and what the
    method can see is set by the scatter of its own readings."""
    print("\nsymbology: the angle between pixels, and the boresight's share")
    white = _Overlay((255, 255, 255))
    box = (230, 40, 250, 64)
    F = sym.measure(white, step=3, method="template", bore=(240.0, 202.0), tpl_box=box).fields
    per_px = np.degrees(1 / F["radius"]["mean_px"])              # the glyph's centre is 150.5 px up
    check(F["frames_solved"] == 100 and close(F["theta_deg_per_px_of_boresight"], per_px, 1e-3),
          "a pointer 150 px out: 0.38 deg of theta per pixel of boresight", f"{F['theta_deg_per_px_of_boresight']:.3f}")
    rr = F["rotation"][0]
    check(F["drawn_at_whole_pixels"] is True and F["position_step_px"] == 1.0 and close(F["theta_step_deg"], per_px, 1e-3)
          and close(F["radius"]["mean_px"], 150.5, 0.05),
          "a block drawn at whole pixels is found there between pixels, so the step is the video's: 1 px, 0.38 deg",
          f"r = {F['radius']['mean_px']:.3f}")
    check(rr["resolvable_by"] == "one step" and close(rr["resolvable_deg_per_s"], per_px / (rr["t1"] - rr["t0"]), 1e-6)
          and rr["sense"]["platform"] is None,
          "over the 9.9 s window a rotation under 0.038 deg/s is not seen, and the sense is not claimed (PR135)",
          f"{rr['resolvable_deg_per_s']:.4f} deg/s")
    check("steps of 0.38 deg" in "\n".join(sym.said(F)) and "the step is the video's" in "\n".join(sym.said(F)),
          "and it says the step is the video's")
    moved = sym.measure(_Overlay((255, 255, 255)), step=3, method="template", bore=(244.0, 202.0), tpl_box=box).fields
    d = moved["rotation"][0]["theta_mean"] - F["rotation"][0]["theta_mean"]
    check(abs(abs(d) - np.degrees(np.arctan(4 / F["radius"]["mean_px"]))) < 0.01 and abs(d) <= 4 * per_px,
          "a boresight 4 px to the side moves theta by atan(4/150) = 1.53 deg, inside what it says", f"{d:+.2f} deg")

    # 0.1 deg/s for 10 s is 2.6 px along the arc: at whole pixels a staircase of three
    # treads, whose residual is ~0.1 deg (1 px / sqrt(12) at 0.38 deg a pixel)
    T = sym.measure(_Turning(0.1), step=3, method="template", bore=(240.0, 202.0), tpl_box=box).fields
    rr = T["rotation"][0]
    check(T["drawn_at_whole_pixels"] is False and T["position_step_px"] is None and T["theta_step_deg"] is None,
          "a glyph drawn between pixels has no step")
    check(T["frames_solved"] == 100 and close(rr["dtheta_dt"], 0.1, 0.005),
          "a pointer turning 0.1 deg/s reads 0.1 deg/s", f"{rr['dtheta_dt']:+.4f} deg/s")
    check(rr["resid_rms"] < 0.03, "and follows the turn between pixels, not in whole-pixel treads",
          f"residual {rr['resid_rms']:.4f} deg (treads: ~0.1)")
    check(rr["resolvable_by"] == "scatter" and close(rr["resolvable_deg_per_s"], 2 * rr["dtheta_dt_se"], 1e-12)
          and rr["resolvable_deg_per_s"] < 0.02 and rr["sense"]["platform"] == "image-right",
          "the slowest rotation it could see is twice the fit's standard error, and 0.1 deg/s is well over it: a sense",
          f"{rr['resolvable_deg_per_s']:.4f} deg/s")
    L = "\n".join(sym.said(T))
    check("only as good as it" in L and "between pixels" in L and "standard error" in L, "and it prints all three")
    check(sym.cross_los_sense(0.02, 0.039)["platform"] is None and sym.cross_los_sense(0.05, 0.039)["platform"] == "image-right",
          "a rate under what can be seen is no sense; over it, a sense")
    H = sym.measure(_Overlay((255, 128, 0)), step=3, method="hue", bore=(240.0, 202.0)).fields
    check(H["position_step_px"] == 0.5 and close(H["theta_step_deg"], per_px / 2, 1e-2)
          and H["rotation"][0]["resolvable_by"] == "one step",
          "hue still places a box's centre to half a pixel, and its step still binds", f"{H['theta_step_deg']:.3f} deg")


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


def test_the_range_ratio_is_a_field_of_the_form_and_run():
    """Jacob, 2026-09-27: the speed from a reference object of known size assumed the object at the
    reference's range. `--range-ratio` (the form's "range ratio R_obj / R_ref", from the same KNOWN
    row) scales it, and the report says the ratio was given; without it the row still shows the
    factor, as before."""
    print("\nkinematics: the range ratio, given or not")
    from mcdonald import stages
    names = [k.name for k in stages.KNOWN]
    check("range_ratio" in names and names.index("range_ratio") == names.index("ref_m") + 1
          and next(k for k in stages.KNOWN if k.name == "range_ratio").flag == "--range-ratio",
          "a row of KNOWN, after the reference object's length, so the form and `run --range-ratio` both have it")
    track = {n: (100.0 + 30.0 * n, 200.0) for n in range(1, 31)}
    ref = dict(px=920.0, len_m=180.0)
    a = stages.kinematics(track, 30.0, 1920, "t", None, ref=dict(ref))
    b = stages.kinematics(track, 30.0, 1920, "t", None, ref=dict(ref, range_ratio=2.0))
    check(close(b.fields["scale_bar_m_per_s"], 2 * a.fields["scale_bar_m_per_s"], 1e-9) and a.fields["range_ratio"] is None
          and b.fields["range_ratio"] == 2.0, "the scale-bar speed scales with it, and the fields carry it",
          f"{a.fields['scale_bar_m_per_s']:.1f} -> {b.fields['scale_bar_m_per_s']:.1f}")
    check("2 times the reference's range" in b.result["scale-bar speed"] and "a ceiling" in a.result["scale-bar speed"],
          "the stage's line says at how many times the reference's range, or that it is a ceiling", b.result["scale-bar speed"][:70])
    rows = {}
    for name, f in (("without", a), ("with", b)):
        c = report.Case("t", "/tmp/x.mp4")
        f.into(c)
        rows[name] = next(ln for ln in c.markdown().splitlines() if "transverse relative speed" in ln)
    check("× R_obj/R_ref" in rows["without"] and "R_obj/R_ref = 2 (given)" in rows["with"] and "× R_obj/R_ref" not in rows["with"]
          and "**352 m/s**" in rows["with"], "the report's row: the factor left to the reader without it, the speed with it", rows["with"][:120])


def test_what_is_known_afterwards_and_the_speed_from_a_thing_of_known_size():
    """Jacob, 2026-10-09: "prompt the user to ask if any additional quantities are known (FOV, object of known
    reference size, range to object, etc.)". What can be given to a case already measured is what changes only the
    speed's arithmetic (`stages.AFTER`); a case keeps what it was told, and one written before it did is read off
    its command. A speed from a thing of known size is a physical answer, and the conclusion and the bottom line
    now say it, where they had said that nothing converts to a speed."""
    print("\nwhat is known: afterwards, and the speed from a thing of known size")
    from mcdonald import stages
    names = {k.name for k in stages.KNOWN}
    check(set(stages.AFTER) <= names and not {"size", "diameter", "names", "dark_below", "mask_rows"} & set(stages.AFTER),
          "what can be given afterwards is KNOWN's rows that only reckon, not those that change what other steps look at",
          ", ".join(stages.AFTER))
    old = report.Case("t", "/tmp/x.mp4")
    old.commands = ["mcdonald run x.mp4 --track t.csv --fov 30 --range 8046.72 --ref-px 120 --own-ship 180kt --skip layers"]
    new = report.Case("t", "/tmp/x.mp4")
    new.add("ingest", fields=dict(known={"fov": 12.5, "range_m": 3000.0}))
    new.commands = ["mcdonald run x.mp4 --fov 99"]
    check(stages.known_of(old) == {"fov": 30.0, "range_m": 8046.72, "ref_px": 120.0, "own_ship": "180kt"}
          and stages.known_of(new) == {"fov": 12.5, "range_m": 3000.0} and stages.known_of(report.Case("t", "/x")) == {},
          "a case keeps what it was told (`known` in its ingest step); an older one is read off the command it records",
          str(stages.known_of(old)))
    try:
        stages.add_known("/nonexistent_case.json", diameter=9.0)
        refused = False
    except ValueError as e:
        refused = "--diameter" in str(e) and "measure" in str(e)
    check(refused, "and what changes more than the arithmetic is refused before anything is read: measure again for that")
    track = {n: (100.0 + 30.0 * n, 200.0) for n in range(1, 31)}
    ref = dict(px=920.0, len_m=180.0)
    said = {}
    for name, r in (("same distance", dict(ref)), ("ratio", dict(ref, range_ratio=0.5))):
        c = report.Case("t", "/tmp/x.mp4")
        c.add("track", {"source": "t.csv"}, fields=dict(source="t.csv", frames=30, first=1, last=30))
        stages.scale(type("C", (), dict(W=1920, H=1080, n0=1, rgb=lambda self, n: np.zeros((1080, 1920, 3))))(),
                     ref_px=920.0, ref_m=180.0).into(c)
        stages.kinematics(track, 30.0, 1920, "t", None, ref=r).into(c)
        said[name] = (c.conclusion(), c.bottom_line(), c.stages["kinematics"]["fields"]["scale_bar_m_per_s"])
    (label, head), line, bar = said["same distance"]
    check(label != "No physical conclusion" and f"about {bar:.0f} m/s across the line of sight if it is as far away as the thing "
          "of known size" in head and "(180 m over 920 px)" in line
          and "less if it is nearer, more if it is farther" in line and "does not convert" not in line,
          "a thing of known size gives a speed: the conclusion says it, at that thing's distance, and the bottom line how",
          head[:100])
    (label, head), line, bar = said["ratio"]
    check(f"about {bar:.0f} m/s across the line of sight, at 0.5 times the distance of the thing of known size (as given)" in head
          and "at 0.5 times its distance, as given" in line, "and with a range ratio, at that ratio, said to be given", head[:100])


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
def test_the_parallax_ladder():
    """An agent's first request after `layers` (PR135, items 1 and 15): how much of a speed along
    the ground is the aircraft's own motion, seen through an object nearer than the ground.
    v_G = k v_O - (k - 1) v_A, k = h_A / (h_A - h_O). Checked against what it must give in closed
    form, and against the rule of thumb for indicated airspeed; without the two speeds it is
    NO POWER, naming what is missing."""
    print("\nkinematics: the parallax ladder")
    from mcdonald import stages
    vg, va = 200.0, 100.0
    p = kin.parallax_ladder(vg, va)
    still = p["rows"][0]
    check(abs(still["k_min"] - 3.0) < 1e-9 and abs(still["k_max"] - 3.0) < 1e-9 and abs(still["h_ratio_min"] - 2 / 3) < 1e-3,
          "a still object: k = 1 + v_G / v_A, two thirds of the way down", f"k {still['k_min']}, h {still['h_ratio_min']}")
    r = p["rows"][2]                                        # 10 m/s of its own
    check(abs(r["k_min"] - 300 / 110) < 1e-9 and abs(r["k_max"] - 300 / 90) < 1e-9,
          "an object with a speed of its own: the range every direction allows", f"{r['k_min']:.3f} to {r['k_max']:.3f}")
    # the same, with the directions: a ground motion due west from an aircraft heading east
    v = kin.parallax_ladder(vg, va, own_heading=90.0, ground_bearing=270.0)
    check(v["stationary_off_deg"] == 0.0 and v["rows"][0]["k"] and abs(v["rows"][0]["k"][0] - 3.0) < 1e-3,
          "with both directions, the still object is k = 3 again, and exactly opposite the heading", str(v["rows"][0]))
    k = v["rows"][2]["k"]
    G, A = vg * np.array([-1.0, 0.0]), va * np.array([1.0, 0.0])
    check(k and all(abs(np.hypot(*(G + (x - 1) * A)) - 10.0 * x) < 0.05 for x in k),
          "and each k for 10 m/s of its own solves k v_O = |v_G + (k - 1) v_A|", str(k))
    off = kin.parallax_ladder(vg, va, own_heading=90.0, ground_bearing=260.0)["rows"][0]
    check(not off["k"] and abs(off["closest"]["own_speed_needed_m_s"] - vg * math.sin(math.radians(10))) < 0.05,
          "10 deg off the heading, a still object fits nowhere, and the nearest needs v_G sin 10 deg of its own",
          str(off["closest"]))
    tas = kin.tas_from_ias(250 * kin.KNOTS, 10000 * 0.3048) / kin.KNOTS
    check(abs(kin.tas_from_ias(100.0, 0.0) - 100.0) < 1e-9 and 285 < tas < 295,
          "indicated airspeed: true at sea level, and 250 kt at 10,000 ft is about 290 kt true", f"{tas:.1f} kt")
    got = kin.speed_of("480mph")[0], kin.speed_of("250kt")[0], kin.speed_of("400 km/h")[0]
    check(abs(got[0] - 214.58) < 0.01 and abs(got[1] - 128.61) < 0.01 and abs(got[2] - 111.11) < 0.01,
          "speeds in the units reports give them", str([round(x, 2) for x in got]))
    fields, npw, _ = stages.parallax(None, "180kt")
    check(fields is None and npw and "--ground-speed" in npw[0][1] and "--own-ship" not in npw[0][1],
          "without a ground speed it is NO POWER, and says which of the two is missing", npw[0][1][:80] if npw else "")
    fields, npw, _ = stages.parallax("fast", "180kt")
    check(fields is None and npw and "480mph" in npw[0][1], "a speed it cannot read says how to write one", npw[0][1][:80] if npw else "")
    fields, npw, lines = stages.parallax("480mph,265", "250kias@7000ft,85")
    check(fields and not npw and fields["own_band"] and "with_the_air_15C_colder_and_warmer" in fields and fields["h_own_m"] > 2000,
          "an indicated airspeed at a height gives the band a day 15 C colder or warmer, and the height", lines[1])


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
        check(open(c, encoding="utf-8").readline().startswith("#"),
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
        text = open(c, encoding="utf-8").read()
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
        open(p, "w", encoding="utf-8").write(_json.dumps({"tag": "t", "video": "/tmp/x.mp4", "fps": 30.0, "classes": {"object": {"5": [1.0, 2.0]}}}))
        check(MarkSet("t", "/tmp/x.mp4", 30.0).load(p).marks == old.marks, "a marks file from before provenance still loads")
        open(p, "w", encoding="utf-8").write(_json.dumps({"classes": {"object": {"408": [1009, 313]}}}))
        by_hand = MarkSet("t", "/tmp/x.mp4", 30.0).load(p)
        check(by_hand.marks == {"object": {408: (1009.0, 313.0)}} and isinstance(by_hand.marks["object"][408][0], float),
              "and so does one written by hand or by an agent: four lines, whole numbers, nothing but the marks")


def test_a_mark_a_person_typed_is_a_persons_and_not_a_hands():
    """`mark --set` recorded every mark as an agent's -- a person at a terminal who read the
    positions off `look` as well (2026-09-23, the handoff's Next 7). With --typed they are a
    person's, typed: not an agent's, and not a hand's either, and the report says whose."""
    print("\nmark: typed by a person")
    from mcdonald.mark import MarkSet, apply_sets

    class Whole:
        n1, W, H = 100, 640, 480
    ms = MarkSet("t", "/tmp/x.mp4", 30.0)
    apply_sets(ms, Whole(), ["object@10=100,200", "object@20=300,260"], [], why="the dark speck, read off look --at", typed=True)
    check(ms.kind("object", 10) == "typed" and ms.by_hand() == {} and ms.how_of("object", 20).startswith("typed: the dark speck"),
          "--typed marks are a person's, typed: never a hand's", ms.how_of("object", 20))
    apply_sets(ms, Whole(), ["object@30=1,1"], [])
    check(ms.kind("object", 30) == "agent", "and without it, an agent's, as before")
    c = report.Case("t", "/tmp/x.mp4")
    c.identified({10: ms.how_of("object", 10), 20: ms.how_of("object", 20)}, 2)
    md = c.markdown()
    check("decided by a person, who typed the positions" in md and "agent" not in md[md.index("## Where the marks came from"):],
          "a report on typed marks says a person decided, and how", md[md.index(">"):md.index(">") + 90])


# ---------------------------------------------------------------- report
def test_the_report_shows_a_beat_that_is_the_objects():
    """Jacob, 2026-09-29, a bird clip: the flicker stage had found a beat and the report kept it under
    the folded measurements, so it read as no beat found. A beat that is the object's own is a row of
    the summary (the last, after the Technical Note's variables) and a sentence of the bottom line;
    a stage that found none puts its reason in the row."""
    print("\nreport: the beat, in the summary and the bottom line")
    c = report.Case("t", "/tmp/x.mp4")
    c.clip = dict(width=640, height=512, fps=60.0, fps_exact="60", n0=369, n1=721)
    beat = dict(hz=3.94, double_hz=7.88, first=602, last=721, amplitude=0.097, stands=399.0, resolution_hz=0.5,
                source="the clearest of 11 windows of 2 s that beat, of 17", hz_range=[3.94, 3.97], windows_passing=11, windows=17)
    report.Found("flicker", {"object": "3.94 Hz (and 7.88, its double), 9.7%, 399x the band, frames 602–721",
                             "finding": "it beats at 3.94 Hz (and at 7.88, its double)"},
                 fields=dict(beats=True, beat={"object": beat}, finding="it beats at 3.94 Hz (and at 7.88, its double)")).into(c)
    rows = {r[0]: (r[2], r[3]) for r in c.summary()}
    check(rows.get("brightness beat", (None,))[0] == "3.9 Hz (and 7.9 Hz, its double)" and "602–721" in rows["brightness beat"][1]
          and "wingbeat" in rows["brightness beat"][1] and list(r[0] for r in c.summary())[-1] == "brightness beat",
          "the summary's last row: the beat, its double, its frames, and that a wingbeat is one of the things that beat",
          str(rows.get("brightness beat"))[:120])
    label, head = c.conclusion()
    check(label == "Tentative conclusion" and head.startswith("A bird is the leading explanation: its brightness beats at 3.9 Hz")
          and "7.9 Hz, its double" in head and "wingbeat" in head and "tumbling body" in head,
          "a beat at a wingbeat's rate makes a bird the leading explanation of the conclusion, with the alternatives named "
          "(Jacob, Galileo flyer 2, 2026-10-07)", head[:100])
    flock = report.Case("t", "/tmp/x.mp4")                 # a group whose members beat, each its own: PR135's six (2026-10-08)
    members = {f"member {i}": dict(hz=hz, double_hz=None, first=1240, last=1392, amplitude=0.2, stands=100.0)
               for i, hz in enumerate((7.85, 7.38, 8.02, 7.10, 7.66, 7.61), 1)}
    report.Found("flicker", {"finding": "members over the same frames beat at different frequencies or out of step"},
                 fields=dict(beats=True, beat=members, finding="members over the same frames beat at different frequencies or out of step")).into(flock)
    label, head = flock.conclusion()
    rows = {r[0]: (r[2], r[3]) for r in flock.summary()}
    check(label == "Tentative conclusion" and head.startswith("A flock of birds is the leading explanation: its 6 members each beat at 7.1–8.0 Hz")
          and "out of step" in head and "too briefly" not in head and rows["brightness beat"][0] == "6 members: 7.1–8.0 Hz"
          and "each member's own" in rows["brightness beat"][1]
          and "6 members beat at 7.8, 7.4, 8.0, 7.1, 7.7, 7.6 Hz" in flock.bottom_line(),
          "a group whose members each beat at a wingbeat's rate, out of step: a flock of birds, in the conclusion, the summary "
          "and the bottom line", head[:110])
    part = report.Case("t", "/tmp/x.mp4")                  # one member beating too slowly for wings, and three seen too briefly
    members["member 6"] = dict(members["member 6"], hz=1.0)
    report.Found("flicker", {"finding": "members over the same frames beat at different frequencies or out of step"},
                 fields=dict(beats=True, beat=members, short=["member 7", "member 8", "member 9"],
                             finding="members over the same frames beat at different frequencies or out of step")).into(part)
    label, head = part.conclusion()
    check(head.startswith("A flock of birds is the leading explanation: 5 of its 6 members each beat at 7.1–8.0 Hz")
          and head.endswith("would beat too; 3 more were seen too briefly to tell).") and part.conclusion()[0] == "Tentative conclusion",
          "a member beating outside the wingbeat band is counted among the members, not the flock; members too brief for a beat "
          "(under 60 frames: PR135's after the group's jump) are said", head[-80:])
    check("beats at 3.9 Hz (and at 7.9 Hz, its double): the object's own, not the video's" in c.bottom_line(),
          "the bottom line says it", c.bottom_line()[:120])
    d = report.Case("t", "/tmp/x.mp4")
    report.Found("flicker", {}, fields=dict(beats=False, beat={}, finding="no beat reaches 3 times what the background beside it does"),
                 no_power=[("flicker", "no beat reaches 3 times what the background beside it does")]).into(d)
    rows = {r[0]: (r[2], r[3]) for r in d.summary()}
    check(rows.get("brightness beat", ("x",))[0] is None and "no beat reaches" in rows["brightness beat"][1] and "beats at" not in d.bottom_line(),
          "with none found, the row says why and the bottom line says nothing of it", str(rows.get("brightness beat"))[:100])


def test_the_summary_is_the_technical_notes_variables():
    """Jacob, 2026-09-24: at the top of the report, the Technical Note's variables -- pixel velocity
    first, then FOV, then the rest in the order they are likely to be known. PR113's published numbers
    (JAIS Technical Note, Sec. IV): 142 px/frame at 30 fps, a graticule of 35.4 px/deg, so k = 2.03e3
    px/rad, FOV about 54 deg and omega about 2.10 rad/s; R, theta and v_own not available."""
    print("\nreport: the summary of variables, on PR113's published numbers")
    import numpy as np
    from mcdonald import stages

    class Clip:
        W, H, fps, n0, n1 = 1920, 1080, 30.0, 408, 411

        def rgb(self, n):
            return np.zeros((self.H, self.W, 3), np.float32)
    clip = Clip()
    track = {n: (1009.0 - 102.4 * (n - 408), 313.0 + 97.0 * (n - 408)) for n in range(408, 412)}   # 141 px/frame
    sc = stages.scale(clip, graticule=35.4)
    kf = stages.kinematics(track, 30.0, 1920, "pr113", sc.carry)
    c = report.Case("pr113", "/tmp/DOD_111830133.mp4")
    c.clip = dict(width=1920, height=1080, fps=30.0, fps_exact="30", n0=408, n1=411)
    c.add("track", {"frames": 4}, fields=dict(frames=4, object_size_px=21.0))
    sc.into(c)
    kf.into(c)
    rows = c.summary()
    names = [r[0] for r in rows]
    check(names[:7] == ["pixel velocity", "pixel velocity against the striated background",
                        "pixel velocity against the isotropic background", "horizontal field of view", "angular scale",
                        "angular rate", "image extent"],
          "pixel velocity first, then against each layer of the background, FOV, k, omega and the image extent",
          ", ".join(names[:7]))
    val = {r[0]: r[2] for r in rows}
    check(val["pixel velocity"].startswith("141.") and "px/frame" in val["pixel velocity"]
          and val["horizontal field of view"].startswith("54.") and val["angular scale"].startswith("2028 px/rad")
          and val["angular rate"][:4] in ("2.09", "2.10"),
          "the Technical Note's numbers: v_px, FOV about 54 deg, k 2.03e3 px/rad, omega about 2.10 rad/s",
          "; ".join(f"{k}: {v}" for k, v in list(val.items())[:4]))
    check(val["range"] is None and val["platform velocity"] is None and val["relative speed"] is None and val["object velocity"] is None,
          "R, v_own and the speeds that need them are not available, and the table says what would give each")
    md = c.markdown()
    check(md.index("## Conclusion") < md.index("## Summary of variables") and "| pixel velocity | v_px | **141." in md
          and "Read from the video" not in md and "1920x1080" in md[:md.index("## Conclusion")],
          "and it is near the top of the report, under the conclusion; W x H and f are said once, above it")
    label, head = c.conclusion()
    check(label == "No physical conclusion" and head.startswith("The object moved about") and "pixels a second" in head
          and "cannot be found from this video alone" in head and f"**{label}.** {head}" in md[:md.index("## Summary of variables")],
          "the conclusion comes first, and with no range and no scale it says there is no physical one, and why", f"{label}: {head[:90]}")
    import tempfile
    from mcdonald import figures
    with tempfile.TemporaryDirectory() as td:
        c.figures = figures.report_figures(c, clip, track, f"{td}/pr113")
        md = c.markdown()
        check(len(c.figures) == 2 and all(Path(f).exists() for f in c.figures)
              and md.index("## Missing quantities") < md.index("## Figures") < md.index("## Measurements")
              and "pr113_track_frame.png" in md and "pr113_size_speed.png" in md,
              "the two figures (a frame with the path; size and speed against range) are drawn, after Missing quantities",
              ", ".join(Path(f).name for f in c.figures))


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
    check("no power -- speed: no k and no R" in md[md.index("## Measurements"):],
          "no-power entries are rendered under Measurements, never dropped")
    check("a sourced range" in md[md.index("## Missing quantities"):md.index("## Measurements")],
          "and what would close it is under Missing quantities")
    order = [md.index(h) for h in ("## Conclusion", "## Summary of variables", "## Missing quantities", "## Measurements",
                                   "## Reproduce on command line")]
    check(order == sorted(order) and "What this clip cannot decide" not in md and "What the clip is" not in md
          and "custody question" not in md and "method.md" not in md and md.count("<details>") == 2 and "## Bottom line" not in md,
          "the order Jacob asked for (2026-09-24), the conclusion first (2026-10-07), with Measurements and Reproduce folded, "
          "and the sections he struck gone")
    check(c.conclusion()[0] == "No conclusion" and "Nothing was measured about the object" in c.conclusion()[1]
          and report.Case("t", "/tmp/t.mp4").conclusion() == ("No conclusion", "No step produced a result."),
          "a case with a pixel velocity typed in but nothing measured, and an empty case, say there is no conclusion", str(c.conclusion()))
    import json as _json
    check(_json.loads(c.json())["stages"]["kinematics"]["needs"] == ["a sourced range"],
          "the JSON carries the same structure")


def test_a_stopped_measurement_says_so_rather_than_what_it_lacks():
    """PR23 (Jacob, 2026-09-25): the measuring was stopped during layers, kinematics never ran, and
    the report said v_px "needs a track of the object" of a case with a good 202-frame track."""
    print("\nreport: a measurement that was stopped")
    for how, where in (("during", "during layers"), ("between", "before kinematics")):
        c = report.Case("testclip", "/tmp/testclip.mp4")
        c.add("track", dict(frames=202), fields=dict(frames=202, first=3, last=206))
        if how == "during":
            c.add("layers", no_power=[("layers", "stopped before it finished, so it found nothing")])
        else:
            c.note(report.STOPPED_BEFORE + "kinematics")
        md = c.markdown()
        row = next(line for line in md.splitlines() if line.startswith("| pixel velocity | v_px |"))
        check(f"stopped {where}" in row and "needs a track" not in row and f"stopped {where}, so the steps after it did not run"
              in md[md.index("## Conclusion"):], f"stopped {how} steps: v_px and the bottom line say it was stopped {where}", row)
        check(c.conclusion()[0] == "No conclusion yet" and f"stopped {where}" in c.conclusion()[1],
              "and the conclusion is that there is none yet", str(c.conclusion()))
        check(f"- {report.STOPPED_BEFORE}" not in md, "and the note is not repeated as a line of its own")


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
    check("only if the object shows its own shape" in f.result["body-lengths/s"]
          and any("only if the object is resolved" in n and "12 px" in n for n in f.notes)
          and "only if the object shows its own shape" in f.carry["reduction"].report(),
          "a speed in body lengths says, wherever it is printed, that it is one only if the object is resolved "
          "(PR135: 28.6 /s from a point's 7.4 px)")
    check(any("which was not measured (there were no frames to measure it on)" in n for n in f.notes),
          "with no frames, the blur is said not to have been measured, and why")
    point = dict(frames=12, spots=288, blur_fwhm_px=2.3, object_fits=12, object_fwhm_px=2.4, resolved=False)
    g = stages.kinematics(track, 30.0, 1920, "t", size_px=7.4, blur=point)
    npw = dict(g.no_power)
    check("body lengths" in npw and "not resolved" in npw["body lengths"] and "7.4 px" in npw["body lengths"]
          and "blur widths" in npw["body lengths"] and "NOT resolved" in g.result["resolution"]
          and g.fields["resolution"] == point and g.fields["body_lengths_per_s"] is not None,
          "an object no wider than a point: its speed in body lengths is NO POWER, and the number is still there",
          npw.get("body lengths", "")[:80])
    disc = dict(point, object_fwhm_px=9.2, resolved=True)
    g = stages.kinematics(track, 30.0, 1920, "t", size_px=12.0, blur=disc)
    check("body lengths" not in dict(g.no_power) and any("The object is resolved" in n and "9.2 px" in n for n in g.notes),
          "a resolved one: no NO POWER, and a note that says it was measured", g.result["resolution"])
    few = dict(point, spots=3, blur_fwhm_px=None, resolved=None)
    g = stages.kinematics(track, 30.0, 1920, "t", size_px=12.0, blur=few)
    check(any("fewer than 8 compact spots" in n for n in g.notes) and "body lengths" not in dict(g.no_power),
          "a clip with no points to measure the blur on says so, and claims nothing either way")
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
    check(f.no_power[0] == ("kinematics", "track too short to fit a rate") and [t for t, _ in f.no_power[1:]] == ["parallax"]
          and not f.result and f.carry is None,
          "a track too short to fit is a stage with no power, not an exception")


def test_a_mark_taken_from_a_proposal_says_so():
    """The window can propose the object (mcdonald.propose) and a person can take the
    proposal. The suggestion of which thing, and the positions, were the detector's; the
    yes was theirs. Neither a hand mark nor an agent's, and the report says which."""
    print("\nmarks: taken from a proposal")
    from mcdonald.mark import MarkSet
    ms = MarkSet("t", "/tmp/x.mp4", 30.0)
    how = "proposed: 1 of 3 things found moving against the background in frames 1–120 (bright, about 9 px); accepted at the window"
    ms.add("object", 17, 1637.5, 893.2, how=how)
    ms.add("object", 95, 77.0, 669.1, how=how)
    ms.add("object", 50, 976.0, 790.0)
    check(ms.kind("object", 17) == "proposed" and ms.kind("object", 50) == "hand", "its kind is 'proposed'")
    check(sorted(ms.by_hand()) == [50] and sorted(ms.not_by_hand()) == [17, 95], "it is never a hand mark: by_hand() leaves it out")
    c = report.Case("t", "/tmp/x.mp4")
    c.identified({17: how, 95: how}, 2)
    top = c.markdown()
    top = top[:top.index("## Measurements")]
    whole = c.markdown()
    below = whole[whole.index("## Where the marks came from"):]
    check("the detector's proposal" not in top and "the detector's proposal" in below and "the yes was theirs" in below
          and "frame 17: proposed: 1 of 3" not in top and "<details>" in below and "frame 17: proposed: 1 of 3" in below,
          "a report built on proposed marks says on its face that the detector proposed the object and a person accepted it; "
          "each mark's record is further down, folded")
    c = report.Case("t", "/tmp/x.mp4")
    c.identified({17: how, 95: "agent: candidate 1"}, 2)
    check("an agent or the detector, not by a hand" in c.markdown(), "and mixed with an agent's marks, that neither was a hand's")


def test_how_many_objects_are_looked_for():
    """Jacob, 2026-10-08: "Would it be helpful if the user told mcdonald at the start how many objects to look
    for?" The count is held against what was followed (`several.tally`, the list's first line), and where
    fewer things were found than asked for and one is a group of points -- PR135's flock, which Find lists as
    two groups of three -- the group's members become objects of their own (`several.split_group`), each with
    the member's positions as its track, its beat read from the group's flicker stage (`flicker.of_member`),
    and a fellow member found moving with it named as such by the tether stage (`stages.fellow_member`)."""
    print("\nhow many objects: the count against what was followed, and a group's members as objects")
    import csv
    import tempfile
    from mcdonald import several, flicker, stages, mark, forensics as vf
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "flock"
        # object 1: a group of three points moving together over frames 1-120, 20 px apart, its case says so
        track = {n: (100.0 + 2.0 * n, 200.0 + 0.5 * n) for n in range(1, 121)}
        members = {1: {n: (x - 20, y) for n, (x, y) in track.items()},
                   2: {n: (x, y + 20) for n, (x, y) in track.items() if n >= 30},
                   3: {n: (x + 20, y) for n, (x, y) in track.items() if n <= 40}}       # 40 frames: too brief for a beat
        one = base / "object-1"
        one.mkdir(parents=True)
        ms = mark.MarkSet("flock", "/tmp/flock.mp4", 30.0)
        ms.add("object", 1, 100.0, 200.0, how="proposed: 1 of 2 things found")
        ms.add("object", 120, 340.0, 260.0, how="proposed: 1 of 2 things found")
        ms.save(one / "flock_marks.json")
        with open(one / "flock_members.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["frame", "member", "x_px", "y_px", "response"])
            for i, tr in members.items():
                for n, (x, y) in sorted(tr.items()):
                    w.writerow([n, i, x, y, 10.0])
        with open(one / "flock_autotrack.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["frame", "x", "y"])
            for n, (x, y) in sorted(track.items()):
                w.writerow([n, x, y])
        case = report.Case("flock", "/tmp/flock.mp4")
        report.Found("track", dict(frames=120), fields=dict(frames=120, first=1, last=120, object_size_px=5.0, object_is_dark=False)).into(case)
        report.Found("groups", dict(points="3 a frame"), fields=dict(several=True, members_followed=3, rigid=False)).into(case)
        beat = lambda hz, a, b: dict(hz=hz, double_hz=None, first=a, last=b, amplitude=0.2, stands=80.0, resolution_hz=0.3, source="the whole track")
        gf = dict(codec=None, frames=120, first=1, last=120, aperture_px=5, spans={"member 1": [1, 120], "member 2": [30, 120], "member 3": [1, 40]},
                  curves={"member 1": dict(hz=7.8), "member 2": dict(hz=7.4), "member 3": None},
                  beat={"member 1": beat(7.8, 1, 120), "member 2": beat(7.4, 30, 120)}, short=["member 3"],
                  pairs=[dict(members=["member 1", "member 2"], hz=[7.8, 7.4], frames=[30, 120], apart_hz=0.4, phase_deg=-150.0, independent=True)],
                  beats=True, finding="members over the same frames beat at different frequencies or out of step")
        report.Found("flicker", {"finding": gf["finding"]}, fields=gf).into(case)
        case.write(str(one / "flock"))
        (one / "flock_case.md").write_text("# flock\n", encoding="utf-8")
        found = several.things(base)
        check(len(found) == 1 and several.is_group(found[0]) and not found[0].group and found[0].track is None,
              "an object whose case found several points moving together, their tracks written, is a group")
        # the count, before any split: one thing followed where six were looked for
        d = several.tally(found, 6)
        check(d["followed"] == 1 and d["missing"] == 5 and d["sentence"] == "You looked for 6 objects: 1 was followed; 5 were not found.",
              "the count against what was followed, in one sentence, with nothing invented to make the number", d["sentence"])
        check(several.tally(found, None)["sentence"] == "" and several.tally(found, 1)["sentence"] == "You looked for 1 object: 1 was followed.",
              "no count, no sentence; the count met is said as met")

        class Stub:                                   # what `place` needs of a clip: its video and rate (the strip's failure is caught)
            video, fps = Path("/tmp/flock.mp4"), 30.0
        made = several.split_group(Stub(), found[0], base, 6, say=lambda *a: None)
        found = several.things(base)
        check([m.k for m in made] == [2, 3] and [m.group["member"] for m in made] == [1, 2] and len(found) == 3
              and all(m.track is not None and m.track.exists() for m in made) and (base / "object-2" / "flock_group.json").exists(),
              "its members seen on 60 frames or more become the next objects, longest first, each with its positions written as its "
              "track and a file naming the group; one seen on 40 frames does not", str([(m.k, m.group) for m in made]))
        tr2 = vf.read_track(made[0].track)
        ms2 = mark.MarkSet("flock", "", 1.0).load(made[0].marks)
        check(len(tr2) == 120 and tr2[50] == (180.0, 225.0) and sorted(ms2.marks["object"]) == list(range(1, 121, 10)) + [120]
              and "member 1 of object 1" in ms2.how_of("object", 1) and "6 objects were looked for" in ms2.how_of("object", 1)
              and ms2.seen == (1, 120) and made[0].group["siblings"] == [2],
              "the member's track is its positions to the digit, its marks every ten frames and its last say what it is and why, "
              "and it knows its fellows", ms2.how_of("object", 1)[:80])
        check(several.children(found, 1) == [found[1], found[2]] and several.tally(found, 6)["groups"] == [1]
              and several.tally(found, 6)["followed"] == 0,
              "the group is counted through its members from then on, which have no report yet")
        page, rows = several.index(base, objects=6)
        text = page.read_text(encoding="utf-8")
        check("**You looked for 6 objects: 0 were followed; 6 were not found.**" in text and "its members are objects 2, 3" in text
              and rows[1]["group"] == dict(object=1, member=1) and "member 1 of object 1" in rows[1]["chosen_as"]
              and several.asked_before(base) == 6 and "You looked for 6" in several.index(base)[0].read_text(encoding="utf-8"),
              "the list's first line holds the count, the group names its members, each member's row names its group, and the count "
              "is remembered when the list is written again", text.splitlines()[4][:70])
        # the member's flicker stage, from the group's: measured with its fellows
        f = flicker.of_member(gf, "member 2", "object-1", tr2)
        check(f.fields["beats"] is True and f.fields["beat"] == {"object": gf["beat"]["member 2"]} and f.fields["first"] == 30
              and "out of step with, or at another frequency from, member 1 of its group: the beat is its own" in f.fields["finding"]
              and f.result["object"].startswith("7.40 Hz, 20.0%, 80x the band, frames 30–120") and f.fields["of_group"]["member"] == "member 2"
              and not f.no_power,
              "a member's beat is read from the group's stage, its own where it is out of step with a fellow's", f.fields["finding"][:90])
        c = report.Case("flock", "/tmp/flock.mp4")
        f.into(c)
        label, head = c.conclusion()
        check(label == "Tentative conclusion" and head.startswith("A bird is the leading explanation: its brightness beats at 7.4 Hz"),
              "and its report leads with the bird, as a thing alone would", head[:80])
        g = flicker.of_member(gf, "member 3", "object-1")
        check(g.fields["beats"] is None and g.no_power == [("flicker", "seen on 40 frames, under the 60 a beat needs")],
              "a member too brief for a beat says so, with no power")
        same = dict(gf, pairs=[dict(gf["pairs"][0], independent=False, phase_deg=5.0, apart_hz=0.1)])
        h = flicker.of_member(same, "member 1", "object-1")
        check(h.fields["beats"] is None and "as one with member 2 of its group, at one frequency and in step" in h.fields["finding"],
              "in step with every fellow, the beat may be the video's: no power, said")
        # the tether stage's companion, where it is a fellow member
        companion = dict(r_px=19.0, direction_deg=92.0, sign="bright", r_over_size=3.8, z=6.0, z_control=0.2, seen_on_frames=0.5)
        fellows = {f"member {i}": tr for i, tr in members.items()}
        check(stages.fellow_member(companion, track, fellows) == "member 3"
              and stages.fellow_member(dict(companion, direction_deg=-92.0), track, fellows) == "member 1"
              and stages.fellow_member(dict(companion, direction_deg=0.0, r_px=20.0), track, fellows) == "member 2"
              and stages.fellow_member(dict(companion, r_px=45.0), track, fellows) is None
              and stages.fellow_member(dict(companion, direction_deg=140.0), track, fellows) is None
              and stages.fellow_member(None, track, fellows) is None and stages.fellow_member(companion, track, {}) is None,
              "a feature moving with the object at a member's offset (within 4 px or 30%, and 20 degrees) is that member; "
              "elsewhere it is not (PR135: the next bird, 29 px away)")
        tcase = report.Case("flock", "/tmp/flock.mp4")
        report.Found("tether", dict(finding="x"), fields=dict(companion=None, fellow_member=dict(companion, member="member 3"), swing=None)).into(tcase)
        check("The bright feature 3.8 object sizes away that moves with it is member 3 of the group it is in, not something tied to it."
              in tcase.bottom_line() and "Something moves with it" not in tcase.conclusion()[1],
              "the report says the fellow member, and the conclusion does not call it something moving with the object")


def test_the_window_imports_without_scipy_signal():
    """The window's start is its imports (2.1 of the 2.65 s to the first screen), and half of them was
    scipy.signal -- with scipy.stats, interpolate and optimize behind it -- for one function, fftconvolve,
    which forensics now has on scipy.fft. Neither the window nor the stages may bring it back."""
    import subprocess
    r = subprocess.run([sys.executable, "-c", "import sys, mcdonald.mark_qt, mcdonald.stages, mcdonald.integrity, mcdonald.layers, "
                        "mcdonald.propose, mcdonald.autolink; print(sorted(m for m in sys.modules if m.startswith('scipy.signal')))"],
                       capture_output=True, text=True)
    check(r.returncode == 0 and r.stdout.strip() == "[]", "the window and the stages import without scipy.signal",
          (r.stdout.strip() + r.stderr.strip()[-300:]).strip())


def test_one_version_everywhere_it_is_said():
    """pip --upgrade from GitHub installs only a newer version, so the number goes up with every
    change sent out (Jacob, 2026-09-25). It is written once, in mcdonald/__init__.py; pyproject
    reads it, and the READMEs' status lines, CITATION.cff and the CHANGELOG's newest entry must
    say the same (the last two since 2026-10-09, after the citation file was found a release behind)."""
    print("\nthe version")
    import re
    import mcdonald
    root = Path(__file__).resolve().parent.parent
    toml = (root / "pyproject.toml").read_text(encoding="utf-8")
    check('dynamic = ["version"]' in toml and 'attr = "mcdonald.__version__"' in toml and not re.search(r'^version = "', toml, re.M),
          "pyproject takes the version from mcdonald.__version__, and writes none of its own")
    said = {f: re.findall(r"\*\*Status:[^(]*\((\d+\.\d+\.\d+)\)", (root / f).read_text(encoding="utf-8"))
            for f in ("README.md", "README-technical.md")}
    check(all(v == [mcdonald.__version__] for v in said.values()),
          "both READMEs' status lines say the version the package is", f"{mcdonald.__version__}: {said}")
    cff = (root / "CITATION.cff").read_text(encoding="utf-8")
    check(re.search(r"^version: " + re.escape(mcdonald.__version__) + r"$", cff, re.M) is not None
          and re.search(r"^date-released: " + re.escape(mcdonald.__released__) + r"$", cff, re.M) is not None,
          "CITATION.cff says the version and the day it was released",
          f"{mcdonald.__version__} {mcdonald.__released__}: {[l for l in cff.splitlines() if l.startswith(('version:', 'date-released:'))]}")
    log = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    check(f"\n## {mcdonald.__version__} ({mcdonald.__released__})\n" in log,
          "CHANGELOG.md has this version's entry, with its day", f"## {mcdonald.__version__} ({mcdonald.__released__})")
    import datetime
    try:
        day = datetime.date.fromisoformat(mcdonald.__released__)
    except ValueError:
        day = None
    check(day is not None and day <= datetime.date.today(), "the version has the day it was released, and it is not to come",
          mcdonald.__released__)


def test_help_about_says_what_the_readme_says():
    """Help -> About (Jacob, 2026-09-25): the README's one sentence, its quote, its license line
    and (2026-09-27) where to donate, word for word, so that the two cannot drift apart."""
    print("\nHelp -> About")
    import re
    from mcdonald import actions
    readme = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
    plain = re.sub(r"\s+", " ", re.sub(r"\*\*|\[([^]]*)\]\([^)]*\)|^> ?", r"\1", readme, flags=re.M))
    for what, text in (("the one sentence", actions.ABOUT), ("the quote", actions.QUOTE[0]), ("who said it", actions.QUOTE[1]),
                       ("the copyright and license", actions.COPYRIGHT), ("where to donate", actions.DONATE[0])):
        check(text in plain, f"About has {what} as the README says it", text[:60])


# ---------------------------------------------------------------- files, on a Windows code page
def test_files_are_utf8_whatever_the_locale():
    """Windows' default code page (cp1252) has no θ or →, and cannot decode the shipped catalog at
    all: before 2026-09-26 every text file went through the platform default, so on Windows the
    first screen failed on the catalog and `run` failed writing its report. Every text file the
    package writes or reads is UTF-8 now. Held under the C locale (ASCII), which is stricter still;
    where the locale cannot be changed that way (Windows itself) the check is the real thing."""
    print("\nfiles: UTF-8 whatever the locale")
    import locale
    import tempfile
    from mcdonald import catalog, mark
    was = locale.setlocale(locale.LC_CTYPE)
    try:
        try:
            locale.setlocale(locale.LC_CTYPE, "C")
        except locale.Error:
            print("  SKIP  no C locale here")
            return
        strict = "utf" not in locale.getencoding().lower() and not sys.flags.utf8_mode
        print(f"  (the default encoding is now {locale.getencoding()}{'' if strict else ': a weak check'})")
        with tempfile.TemporaryDirectory() as td:
            c = report.Case("t", "/tmp/x.mp4")
            c.identified({10: "agent: the θ of the line → 5°"}, 1)
            prefix = str(Path(td) / "t")
            try:
                c.write(prefix)
                md = Path(prefix + "_case.md").read_text(encoding="utf-8")
                back = report.Case.load(prefix + "_case.json")
                check("θ of the line → 5°" in md and back.tag == "t", "the case report is written and read back as UTF-8")
            except (UnicodeEncodeError, UnicodeDecodeError) as ex:
                check(False, "the case report is written and read back as UTF-8", str(ex)[:100])
            ms = mark.MarkSet("t", "/tmp/x.mp4", 30.0)
            ms.add("object", 5, 1.0, 2.0, how="agent: θ")
            p = Path(td) / "t_marks.json"
            try:
                ms.save(p)
                again = mark.MarkSet("t", "/tmp/x.mp4", 30.0)
                again.load(p)
                check(again.how_of("object", 5) == "agent: θ", "so are the marks", again.how_of("object", 5))
            except (UnicodeEncodeError, UnicodeDecodeError) as ex:
                check(False, "so are the marks", str(ex)[:100])
        try:
            recs = catalog.ShippedCatalog().videos()
            accents = sum(1 for r in recs for v in r.values() if isinstance(v, str) and any(ord(ch) > 127 for ch in v))
            check(len(recs) > 100 and accents > 50, "the shipped catalog reads, its accents intact", f"{len(recs)} records, {accents} with accents")
        except UnicodeDecodeError as ex:
            check(False, "the shipped catalog reads, its accents intact", str(ex)[:100])
    finally:
        locale.setlocale(locale.LC_CTYPE, was)


# ---------------------------------------------------------------- a download that cannot start
def test_a_download_that_cannot_start_says_why():
    """No network, an address that does not answer, or a certificate Python cannot check (Python from
    python.org on a Mac, until its own command is run): the person is told which, in a sentence, and
    for the certificate what to do. `mcdonald setup` says the same sentence, from the same place."""
    print("\nstorage: a download that cannot start says why")
    import ssl
    import tempfile
    import urllib.error
    import urllib.request
    from mcdonald import setup_cli, storage

    def raising(err):
        def urlopen(*a, **k):
            raise err
        return urlopen
    real = urllib.request.urlopen
    cert = urllib.error.URLError(ssl.SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: "
                                                                "unable to get local issuer certificate (_ssl.c:1000)"))
    cases = [("certificate", cert, ("certificate", "Install Certificates.command" if sys.platform == "darwin" else "certifi")),
             ("no answer", urllib.error.URLError(ConnectionRefusedError(111, "Connection refused")), ("could not reach DVIDS", "Connection refused")),
             ("gone", urllib.error.HTTPError("https://x/v.mp4", 404, "Not Found", {}, None), ("answered 404",))]
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / "v.mp4"
        for name, err, words in cases:
            urllib.request.urlopen = raising(err)
            try:
                storage.download("https://x/v.mp4", dest, 1000)
                got = None
            except storage.Unreachable as ex:
                got = str(ex)
            except Exception as ex:                                  # noqa: BLE001 -- the check says what came instead
                got = f"{type(ex).__name__}: {ex}"
            finally:
                urllib.request.urlopen = real
            check(got is not None and all(w in got for w in words) and "Traceback" not in got and "urlopen error" not in got
                  and not dest.with_name("v.mp4.part").exists() and not dest.exists(),
                  f"{name}: one sentence that says why, and nothing left on disk", got or "downloaded?")
    urllib.request.urlopen = raising(cert)
    try:
        ok, found, fix = setup_cli._can_download("https://x/v.mp4")
    finally:
        urllib.request.urlopen = real
    check(ok is False and found == "certificate not trusted" and fix == storage.certificate_fix(),
          "setup's certificate line is the same sentence", f"{found}: {fix[:60]}")


def main():
    print("McDonald UAP Toolkit — reduction self-check")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{'ALL PASS' if not FAIL else str(len(FAIL)) + ' FAILED: ' + ', '.join(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):           # a pipe or a log file on Windows is cp1252, and the checks' names have arrows
        _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
