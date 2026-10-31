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
    white = _Overlay((255, 255, 255))                    # in this process (procs=0), so that the frames it reads are counted here
    f = sym.measure(white, step=3, progress=lambda text, done=None, total=None: said.append((text, done, total)), procs=0)
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


def test_symbology_fits_the_circle_the_pointer_draws():
    """PR062's cyan "N" (MTS-B, 2021/04/12) circles a point 8.6 px from the reticle: about the reticle its radius ran
    from 206 to 191 px as it turned 136 deg, so the stage called it mislocated and its angles off by 3 deg. Glyphs
    drawn on that circle with 0.3 px of scatter and one in twenty mislocated: the circle is found to a fifth of a pixel,
    the mislocated ones dropped; a sweep of 25 deg (PR063's) is too short to fit one, and is left about the boresight."""
    print("\nsymbology: the circle the pointer draws, off the boresight")
    rng = np.random.default_rng(3)
    th = np.radians(np.linspace(188, 325, 300))
    x = 644.7 + 199.9 * np.sin(th) + rng.normal(0, 0.3, th.size)
    y = 366.0 - 199.9 * np.cos(th) + rng.normal(0, 0.3, th.size)
    bad = rng.random(th.size) < 0.05
    x[bad] += rng.normal(0, 25, bad.sum()); y[bad] += rng.normal(0, 25, bad.sum())
    c = sym.pointer_centre(x, y, (640.3, 358.5))
    check(c is not None and abs(c["x"] - 644.7) < 0.2 and abs(c["y"] - 366.0) < 0.2 and abs(c["r"] - 199.9) < 0.2,
          "the centre to a fifth of a pixel, 8.6 px from the reticle", c and f"({c['x']:.2f}, {c['y']:.2f}) r {c['r']:.2f}")
    check(c is not None and c["rms"] < 0.5 and (~c["kept"] & bad).sum() >= 0.8 * bad.sum() and (~c["kept"] & ~bad).sum() <= 2,
          "the mislocated glyphs dropped, the rest kept", c and f"rms {c['rms']:.2f}, dropped {(~c['kept']).sum()} of {bad.sum()} bad")
    th = np.radians(np.linspace(329, 354, 300))
    check(sym.pointer_centre(644.7 + 199.9 * np.sin(th), 366.0 - 199.9 * np.cos(th), (640.3, 358.5)) is None,
          "a sweep of 25 deg is too short: no circle fitted")


def test_symbology_reads_the_same_on_a_pool_as_in_one_process():
    """2026-10-09: the pointer is read on a pool, a frame a job (it was one process, frame after frame).
    Every frame is solved on its own, so the readings are the same to the bit, and so are the glyphs
    listed for a pointer no method found -- whose gradients are now made on the pool too."""
    print("\nsymbology: the same readings on a pool as in one process")
    box = (230, 40, 250, 64)
    for make, kw, what in ((lambda: _Overlay((255, 128, 0)), dict(method="hue", bore=(240.0, 202.0)), "an orange pointer, by hue"),
                           (lambda: _Turning(0.1), dict(method="template", bore=(240.0, 202.0), tpl_box=box), "a turning glyph, by template"),
                           (lambda: _Overlay((255, 255, 255)), {}, "a white pointer auto cannot see, and the glyphs it lists")):
        one, many = sym.measure(make(), step=3, procs=0, **kw).fields, sym.measure(make(), step=3, procs=2, **kw).fields
        check(repr(one) == repr(many), f"{what}: the same on two processes as in one",
              f"{one['frames_solved']} frames solved, {len(one.get('glyphs_to_try') or [])} glyphs listed")


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
    check(label == report.SUBSONIC and f"at most about {bar:.0f} m/s across the line of sight, relative to the camera's platform, "
          "if it is no farther away than the thing of known size: under the speed of sound (Mach 0.51)" in head
          and "(180 m over 920 px)" in line and "less if it is nearer, more if it is farther" in line
          and "no more than Mach 0.51, under the speed of sound" in line and "does not convert" not in line,
          "a thing of known size gives a speed: the conclusion says it, at most at that thing's distance, and the bottom line how",
          f"{label}: {head[:100]}")
    (label, head), line, bar = said["ratio"]
    check(f"about {bar:.0f} m/s across the line of sight, relative to the camera's platform, at 0.5 times the distance of the "
          "thing of known size (as given)" in head and "at 0.5 times its distance, as given" in line
          and "no farther away than 0.5 times that thing's distance" in line,
          "and with a range ratio, at that ratio, said to be given", head[:100])


def test_every_stage_has_a_command_that_exists():
    """The window names, in an oval beside a moving bar, the command that does what it is busy with (Jacob,
    2026-10-19); while it measures, the stage under way's, from `stages.COMMAND`. Every stage `run_case` adds has one,
    and each is a command `mcdonald` has: a name that a terminal answers with "unknown command" would teach the wrong
    thing. A stage that records a command of its own in the case is named by it."""
    print("\nthe window's oval: each stage's command")
    import inspect
    from mcdonald import cli, stages
    check(set(stages.COMMAND) == set(stages.ORDER) and set(stages.COMMAND.values()) <= set(cli.COMMANDS),
          "every stage has a command, and every one is a command of mcdonald's", ", ".join(sorted(set(stages.COMMAND.values()))))
    import re
    src = inspect.getsource(stages.run_case)
    own = set(re.findall(r'f"mcdonald (\w+) ', src))
    check(own and own <= set(stages.COMMAND.values()), "the commands run_case records for its stages are among them", ", ".join(sorted(own)))


def test_the_stages_planned_are_the_ones_run_case_goes_through():
    """The window puts a jewel under step 3's bar for each stage Measure will go through (Jacob, 2026-10-20), counted
    before the first begins: `stages.planned`, in run_case's order, with co-motion only where a D is given, as run_case
    runs it only then -- and the horizon and the haze (2026-10-29) only where their height or visibility is."""
    print("\nthe window's jewels: the stages planned")
    from mcdonald import stages
    plain = [s for s in stages.ORDER if s not in stages.OPTIONAL]
    check(stages.planned() == plain and stages.planned(diameter=12.0, height="7000ft", visibility="20km", band="mwir") == stages.ORDER
          and stages.planned(diameter=12.0) == [s for s in stages.ORDER if s not in ("horizon", "haze", "focus")],
          "everything, in the order run_case goes through it; co-motion only with a D, the horizon with a height, the haze "
          "with a visibility", ", ".join(stages.planned()))
    check(stages.planned(skip=["layers", "integrity"]) == [s for s in plain if s not in ("layers", "integrity")]
          and stages.planned(skip=["comotion"], diameter=12.0) == plain and stages.planned(only=["survey", "report"]) == ["survey", "report"],
          "what is skipped is left out, and `only` is all there is")
    check(stages.asked_for(skip=["layers"]) == [s for s in stages.STAGES if s != "layers"],
          "and the stages asked for are run_case's own rule (`asked_for`)")


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


def test_the_speed_band_on_drawn_tracks():
    """K1 held by K8 (ROADMAP 0.4; docs/method.md section 32): the band's coverage on tracks drawn from the
    covariance it fits, the honest error of the average speed, no false alarm of a changing velocity on
    tracks that have none, and a planted acceleration seen. The tracks are `kin.simulate_track`'s: a line,
    a Matérn-3/2 wander of the given sill and range, a nugget, and an acceleration on top; the truth is the
    drawn velocity at every frame, the wander's own rate included."""
    print("\nkinematics: the speed band on drawn tracks (K8)")
    rng = np.random.default_rng(11)
    fps, n = 30.0, 120
    zs, inside, zbar, calls = [], [], [], 0
    for _ in range(16):
        trk, truth = kin.simulate_track(n, fps, v=(120.0, -40.0), nugget=0.5, sill=5.0, range_s=1.0, rng=rng)
        band, series = kin.speed_band(trk, fps)
        vx, vy = np.array(truth["vx"]), np.array(truth["vy"])
        for k, true in (("vx", vx), ("vy", vy)):
            z = (np.array(series[k]) - true) / np.array(series["sd_" + k])
            zs.append(z)
            inside.append(np.abs(z) < 2)
        vb = np.hypot(*truth["vbar"])
        zbar.append((band["v_mean_px_per_s"] - vb) / band["v_mean_err_px_per_s"])
        calls += band["constant"]
    z_sd = float(np.concatenate(zs).std())
    cover = float(np.concatenate(inside).mean())
    check(0.9 <= cover <= 0.99, "the rate's ±2 sd band holds the drawn velocity about 95 % of the time", f"{cover:.3f} over 16 tracks")
    check(0.75 <= z_sd <= 1.35, "and its sd is the right size", f"z sd {z_sd:.2f}")
    check(0.5 <= float(np.std(zbar)) <= 1.7, "the average speed's error is honest", f"z sd {np.std(zbar):.2f} over 16 tracks")
    check(calls == 0, "a track that wanders is never called constant", f"{calls} of 16 called constant")

    quiet, loud, nug = 0, 0, []
    for _ in range(16):
        trk, truth = kin.simulate_track(n, fps, v=(120.0, -40.0), nugget=0.5, sill=0.0, rng=rng)
        band, _ = kin.speed_band(trk, fps)
        quiet += band["constant"]
        loud += band["accel_z"] is not None and band["accel_z"] >= kin.BAND_Z
        nug.append(max(band["nugget_px"]))
    check(quiet == 16, "a line with jitter is constant within its band every time", f"{quiet} of 16")
    check(loud <= 1, "and its velocity is not said to have changed", f"{loud} of 16 at {kin.BAND_Z:.0f} sigma or more")
    check(0.35 <= float(np.median(nug)) <= 0.65, "the nugget is the jitter planted", f"median {np.median(nug):.2f} px for 0.5")

    seen, got = 0, []
    for _ in range(8):
        trk, truth = kin.simulate_track(n, fps, v=(120.0, -40.0), nugget=0.5, sill=2.0, range_s=1.0, accel=(200.0, 0.0), rng=rng)
        band, _ = kin.speed_band(trk, fps)
        seen += (not band["constant"]) and band["accel_z"] >= kin.BAND_Z
        got.append(band["accel_px_per_s2"])
    check(seen == 8, "a planted acceleration of 200 px/s² is seen every time", f"{seen} of 8")
    check(abs(float(np.median(got)) - 200.0) < 40.0, "and read near its value", f"median {np.median(got):.0f} px/s² (the wander's own rate adds to it)")

    trk = {n: (100.0 + 18.0 * (n - 1), 50.0 + 2.0 * (n - 1)) for n in range(1, 40)}
    band, _ = kin.speed_band(trk, fps)
    check(band["constant"] and max(band["nugget_px"]) < 0.01 and abs(band["v_mean_px_per_s"] - math.hypot(18, 2) * fps) < 1e-3,
          "a drawn track that lies on its line exactly: constant, nugget nil, the rate exact",
          f"{band['v_mean_px_per_s']:.3f} px/s, nugget {max(band['nugget_px']):.4f}")
    check(kin.speed_band({n: (float(n), 0.0) for n in range(1, 6)}, fps) is None, "under 10 points there is no band")
    trk = {n: (100.0 + 18.0 * (n - 1) + (0.0 if n % 7 else -18.0), 50.0) for n in range(1, 60)}
    band, _ = kin.speed_band(trk, fps)
    check(band["repeats_dropped"] == 8, "a frame that repeats the one before is dropped first (the picture did not update)",
          f"{band['repeats_dropped']} dropped")
    a, _ = kin.speed_band(trk, fps)
    check(a == band, "and the same track gives the same band twice (nothing in it is random)")


def test_jumps_are_named_on_drawn_tracks():
    """E4 (ROADMAP 0.4; docs/method.md section 32): the band's one-pass 4-sigma clip replaced by jumps named -- a
    glitch, an excursion or a step, against a threshold drawn on the track's own frames and gaps. Clean drawn tracks
    have a jump named about one time in a hundred; a planted glitch or excursion is found, named and left out of the
    fit; a planted step is found, named and kept; a quantised track and one with no jitter at all are not jumpy."""
    print("\nkinematics: jumps named (E4)")
    rng = np.random.default_rng(4)
    fps, n = 30.0, 300
    named = 0
    for _ in range(40):
        trk, _ = kin.simulate_track(n, fps, v=(20.0, -5.0), nugget=0.4, sill=5.0, range_s=1.0, rng=rng)
        fr = np.array(sorted(trk), float)
        xy = np.array([trk[f] for f in sorted(trk)])
        named += bool(kin.jumps(fr, xy[:, 0], xy[:, 1], fps)["flags"])
    check(named <= 2, "a clean wandering track has a jump named about one time in a hundred", f"{named} of 40")
    j = kin.jumps(fr, xy[:, 0], xy[:, 1], fps)
    check(5.0 < j["threshold"] < 6.5 and kin.jumps(fr, xy[:, 0], xy[:, 1], fps)["threshold"] == j["threshold"],
          "the threshold is drawn on the track's own frames, the same every time", f"{j['threshold']:.2f} times the local scale over 300 frames")

    def planted(what):
        trk, _ = kin.simulate_track(n, fps, v=(20.0, -5.0), nugget=0.4, sill=5.0, range_s=1.0, rng=rng)
        if what == "glitch":
            trk[151] = (trk[151][0] + 6.0, trk[151][1])
        elif what == "excursion":
            for f in (151, 152, 153):
                trk[f] = (trk[f][0] + 6.0, trk[f][1] - 1.0)
        else:
            for f in range(151, n + 1):
                trk[f] = (trk[f][0] + 6.0, trk[f][1])
        band, _ = kin.speed_band(trk, fps)
        return band, [f for f in band["jumps"]["flags"] if abs(f["frame"] - 151) <= 2]
    band, near = planted("glitch")
    check(len(near) == 1 and near[0]["kind"] == "glitch" and near[0]["off"] == [151] and band["clipped"] == 1 and band["n"] == n - 1,
          "a planted 6-px glitch is found, named a glitch, and its point left out of the band's fit", str(near))
    band, near = planted("excursion")
    check(len(near) == 1 and near[0]["kind"] == "excursion" and near[0]["off"] == [151, 152, 153] and band["clipped"] == 3,
          "a 3-frame excursion of 6 px is named an excursion, its three points left out", str(near))
    band, near = planted("step")
    check(len(near) == 1 and near[0]["kind"] == "step" and near[0]["off"] == [] and band["clipped"] == 0 and band["n"] == n,
          "a 6-px step is found and named a step, and kept: dropping points cannot undo it", str(near))
    said = kin.jumps_said(band)
    check("a step kept" in said and "frame 151" in said and "the camera's field changed" in said, "and said as such", said[:150])

    trk = {f: (100.0 + 0.37 * f + (0.29 * (f - 150) if f > 150 else 0.0), 50.0 - 0.13 * f) for f in range(1, 301)}
    trk = {f: (round(x, 2), round(y, 2)) for f, (x, y) in trk.items()}     # interpolated boxes written to 0.01 px: no jitter
    fr = np.array(sorted(trk), float)
    xy = np.array([trk[f] for f in sorted(trk)])
    j = kin.jumps(fr, xy[:, 0], xy[:, 1], fps)
    check(not j["flags"] and j["grid_px"] == 0.01, "a track with no jitter that turns at a knot is not jumpy (the floor)", f"{len(j['flags'])} named")
    rng2 = np.random.default_rng(7)
    named = 0
    for _ in range(20):
        trk, _ = kin.simulate_track(n, fps, v=(60.0, 10.0), nugget=0.05, sill=2.0, range_s=1.0, rng=rng2)
        fr = np.array(sorted(trk), float)
        xy = np.round(np.array([trk[f] for f in sorted(trk)]), 1)        # a track written on a 0.1-px grid, its jitter under it
        j = kin.jumps(fr, xy[:, 0], xy[:, 1], fps)
        named += bool(j["flags"])
    check(named <= 1 and j["grid_px"] == 0.1, "a track written on a 0.1-px grid with less jitter than that is not jumpy",
          f"{named} of 20 named")
    check(kin.jumps(np.arange(1, 6.0), np.zeros(5), np.zeros(5), fps) is None, "under 10 points there is no test")
    check(kin.jumps_said({"jumps": {"threshold": 5.6, "alpha": 0.01, "flags": []}}).startswith("none past 5.6 times"),
          "a track with no jump says the test found none")


def test_the_band_is_held_to_its_own_track():
    """E1 (ROADMAP 0.4; docs/method.md section 32): the band backtested on its own track, as a bank's value-at-risk model
    is -- its one-step innovations (`kriging.Model.innovations`) counted past +-1.96 (Kupiec), their misses tested for
    clustering (Christoffersen), for a rhythm left (Ljung-Box), a jitter that changes (ARCH) and the tails (Jarque-Bera),
    with a light and a reason. On tracks drawn from the band's own covariance the light is green about nine times in
    ten; a beat in the position turns it yellow with the beat's rate in the reason, and M8 holds the beat beside the
    wander; a band too narrow for its track is red."""
    print("\nkinematics: the band held to its own track (E1, M8)")
    from mcdonald import kriging as kg
    rng = np.random.default_rng(12)
    fps = 30.0
    t = np.arange(200) / fps
    y = kg.simulate(t, (25.0, 1.0, 0.25), rng)[0]
    m = kg.Model(t, y, float(t.mean()), dt=1 / fps)
    w = m.innovations()
    check(0.85 < float(np.std(w)) < 1.15 and abs(float(np.mean(w))) < 0.25, "the one-step innovations of a drawn series are N(0, 1)",
          f"mean {np.mean(w):+.2f}, sd {np.std(w):.2f}")
    lights = []
    for _ in range(20):
        trk, _ = kin.simulate_track(150, fps, v=(60.0, -20.0), nugget=0.5, sill=5.0, range_s=1.0, rng=rng)
        b, _ = kin.speed_band(trk, fps)
        lights.append(b["backtest"]["light"])
    check(lights.count("green") >= 16 and "red" not in lights,
          "on tracks drawn from its own covariance the band is green about nine times in ten", ", ".join(lights))
    bt = b["backtest"]
    check(bt["n"] == 150 and 0 <= bt["share"] < 0.12 and len(bt["ljung_box_p"]) == 2 and kin.backtest_said(bt).startswith(bt["light"]),
          "its fields: the count of misses, each test's p by coordinate, and a sentence that begins with the light", kin.backtest_said(bt)[:120])

    # a beat in the position: a wingbeat of 0.8 px at 6 Hz, its phase drifting
    n = 240
    tt = np.arange(n) / fps
    trk, _ = kin.simulate_track(n, fps, v=(60.0, -20.0), nugget=0.3, sill=5.0, range_s=1.0, rng=rng)
    ph = rng.uniform(0, 2 * math.pi) + np.cumsum(rng.normal(0, 0.05, n))
    trk = {f: (x + 0.3 * math.sin(2 * math.pi * 6.0 * tt[f - 1] + ph[f - 1]), y + 0.8 * math.sin(2 * math.pi * 6.0 * tt[f - 1] + ph[f - 1]))
           for f, (x, y) in trk.items()}
    b, _ = kin.speed_band(trk, fps)
    beat, bt = b["beat"], b["backtest"]
    check(beat is not None and beat["without"]["light"] != "green" and 5.0 < beat["rhythm_hz"] < 7.0
          and any("a rhythm is left in it, strongest near" in r for r in beat["without"]["reasons"]),
          "a beat in the position: the band alone is not green, and the reason names a rhythm at the beat's rate",
          f"{beat and beat['without']['light']}: {beat and beat['without']['reasons']}")
    held = [h for h in beat["hz"] if h] if beat else []
    check(held and all(5.4 < h < 6.6 for h in held) and min(bt["ljung_box_p"]) > min(beat["without"]["ljung_box_p"]) * 1e3,
          "M8 holds it beside the wander as a beat at its rate, and the rhythm is gone from the innovations",
          f"beat at {held}, Ljung-Box p {min(beat['without']['ljung_box_p']):.1e} -> {min(bt['ljung_box_p']):.1e}, light {bt['light']}")
    said = kin.backtest_said(bt, beat)
    check("is held beside the wander as a beat at" in said and "the rate is the wander's" in said, "and says so", said[-150:])

    # the light's own rule, on innovations given
    tt = np.arange(300) / fps
    wide = kin.backtest({"x": rng.normal(0, 1.4, 300), "y": rng.normal(0, 1.4, 300)}, tt)
    check(wide["light"] == "red" and "too narrow for this track" in wide["reasons"][0], "a band too narrow for its track is red",
          f"{wide['share']:.1%} missed: {wide['reasons'][0][:60]}")
    tails = kin.backtest({"x": rng.standard_t(3, 300) / math.sqrt(3.0), "y": rng.normal(0, 1, 300)}, tt)
    check(tails["light"] != "green" and any("tails heavier than a normal's" in r for r in tails["reasons"]), "tails heavier than a normal's are a reason",
          "; ".join(tails["reasons"])[:100])
    check(kin.backtest({"x": np.zeros(20), "y": np.zeros(20)}, tt[:20]) is None, "under 30 points there is no backtest")


def test_a_beat_is_held_as_covariance():
    """M8 (ROADMAP 0.4; the pure-mathematics survey's §4.1): the Matérn-3/2 times cos 2 pi f r is a covariance (Schur's
    product theorem: its matrices have no negative eigenvalue), and fitted beside the wander by REML it finds a beat
    drawn into a series at its rate, its gain over the wander alone past BEAT_DLNL, while a series with no beat gains
    little from one."""
    print("\nkriging: a beat held as covariance (M8)")
    from mcdonald import kriging as kg
    t = np.arange(240) / 30.0
    D = t[:, None] - t[None, :]
    lo = min(float(np.linalg.eigvalsh(kg.beat32(D, 1.0, ell, hz)).min()) for ell in (0.2, 1.0, 5.0) for hz in (2.0, 7.0, 13.0))
    check(lo > -1e-8, "the Matérn times a cosine has no negative eigenvalue on a track's times", f"least {lo:.1e}")
    rng = np.random.default_rng(14)
    y = kg.simulate(t, (25.0, 1.0, 0.04, 0.5, 1.5, 6.0), rng)[0]
    plain = kg.Model(t, y, float(t.mean()), dt=1 / 30.0)
    beat = kg.Model(t, y, float(t.mean()), dt=1 / 30.0, warm=plain.theta, beat=6.3)
    gain = (plain.val - beat.val) / 2.0
    check(gain >= kin.BEAT_DLNL and abs(beat.theta[5] - 6.0) < 0.3 and len(beat.theta) == 6,
          "a beat drawn at 6 Hz (0.7 px) is found beside the wander at its rate", f"{beat.theta[5]:.2f} Hz, gain {gain:.0f}")
    y = kg.simulate(t, (25.0, 1.0, 0.04), rng)[0]
    plain = kg.Model(t, y, float(t.mean()), dt=1 / 30.0)
    gain = (plain.val - kg.Model(t, y, float(t.mean()), dt=1 / 30.0, warm=plain.theta, beat=6.0).val) / 2.0
    check(gain < kin.BEAT_DLNL, "a series with no beat gains little from one", f"gain {gain:.1f}")


def test_constant_is_an_upper_bound():
    """E12 (ROADMAP 0.4; docs/method.md section 32): where the band says the speed is constant it says that no change was
    seen, not that there was none (the pile-up problem), so it gives the largest steady change of speed it could have
    missed: on lines with jitter and a steady acceleration too small to show, the bound holds the truth about 95 % of the
    time; where the band sees a wander but its change over the stretch is within its noise, the band's own change and
    error bound it; where the change is seen, there is no bound to give."""
    print("\nkinematics: \"constant\" as an upper bound (E12)")
    rng = np.random.default_rng(13)
    fps, n = 30.0, 120
    v = np.array([60.0, -20.0])
    u = v / np.linalg.norm(v)
    held, const, bounds = 0, 0, []
    for _ in range(20):
        trk, truth = kin.simulate_track(n, fps, v=tuple(v), nugget=0.5, sill=0.0, accel=tuple(0.2 * u), rng=rng)
        b, _ = kin.speed_band(trk, fps)
        if not b["constant"]:
            continue
        const += 1
        cb = b["change_bound"]
        held += abs(0.2 * (n - 1) / fps) <= cb["dv_max_px_per_s"]
        bounds.append(cb["dv_max_px_per_s"])
    check(const >= 20 - 2 and held >= const - 2,
          "a steady change of 0.8 px/s over 4 s under half a pixel of jitter: the band says constant, and its bound holds the change",
          f"{const} of {20} constant, the bound held {held}; median bound {np.median(bounds):.1f} px/s")
    second = kin.band_said(b, fps)[1]
    check(second.startswith("constant within its band") and "a steady change of its speed of more than" in second
          and "would have shown (95 %)" in second, "and the band's own words say so", second[-110:])
    trk = {f: (100.0 + 18.0 * (f - 1), 50.0 + 2.0 * (f - 1)) for f in range(1, 40)}
    b, _ = kin.speed_band(trk, fps)
    check(b["constant"] and b["change_bound"]["dv_max_px_per_s"] < 1e-3, "a track exactly on its line: the bound is nil", str(b["change_bound"]))
    trk, _ = kin.simulate_track(n, fps, v=(60.0, -20.0), nugget=0.5, sill=2.0, range_s=1.0, accel=(200.0, 0.0), rng=rng)
    b, _ = kin.speed_band(trk, fps)
    check(b["change_bound"] is None and b["accel_z"] >= kin.BAND_Z, "a change the band sees needs no bound", f"{b['accel_z']:.1f} sigma")


def test_the_speed_band_on_recorded_tracks():
    """The band on the tracks vendored in tests/golden, against the kriging survey's anchor (uap
    `analysis/methods/kriging_methods_survey.md` §1.1, 2026-10-15/16, the same model on the same tracks): the
    nugget is the centroid's jitter, sub-pixel on every spot-filter track; the band is tighter than a pair of
    frames by the survey's ratios; and PR43's streak, which the Technical Note reads as a rate rising from about
    7 to 33 px/frame, is described rather than refused."""
    print("\nkinematics: the speed band on recorded tracks")
    from mcdonald import forensics as vf
    golden = Path(__file__).resolve().parent / "golden"
    anchor = {"pr055_sphere_track.csv": (0.50, 8.0), "pr071_object_track.csv": (0.33, 4.0), "pr144_track.csv": (0.80, 7.0),
              "pr23_object_track.csv": (0.65, 2.1), "wa9ony5_balloon_track.csv": (0.44, 7.9)}
    for name, (nugget, ratio) in anchor.items():
        band, series = kin.speed_band(vf.read_track(golden / name), 30.0)
        got = max(band["nugget_px"])
        tighter = band["pairs_sd_px_per_s"] / band["band_err_px_per_s"]
        check(0.5 * nugget <= got <= 1.6 * nugget, f"{name}: the nugget is the survey's {nugget:.2f} px", f"{got:.2f} px")
        check(tighter >= 0.6 * ratio, f"   and the band is tighter than the scatter of single pairs of frames by about {ratio:.0f}x", f"{tighter:.1f}x")
        check(not band["constant"], "   the velocity wanders (no recorded track is a line with white jitter)", f"dlnl {band['dlnl']:.0f}")
    band, _ = kin.speed_band(vf.read_track(golden / "pr144_track.csv"), 30.0)
    check(band["windows"] > 1 and band["n"] > kin.BAND_NMAX, "PR144's 672 points are read window by window", f"{band['windows']} windows")
    band, _ = kin.speed_band(vf.read_track(golden / "flir1_exit_track.csv"), 30.0)
    step = [f for f in band["jumps"]["flags"] if f["frame"] == 2235]
    check(step and step[0]["kind"] == "step" and step[0]["px"] > 25 and band["clipped"] == 0 and "a step kept" not in (kin.jumps_said(band) or "")
          and "6 steps kept (27.2 px at frame 2235" in kin.jumps_said(band),
          "FLIR1's exit: the 27-px step at its field change (frame 2235) is named a step and kept (E4)", kin.jumps_said(band)[:110])
    second = kin.band_said(band, 30.0)[1]
    check(not band["constant"] and abs(band["accel_z"]) < kin.BAND_Z and band["change_bound"]
          and "; within its noise: its speed along the track changed by less than" in second,
          "and its change of speed over the stretch, within its noise, is bounded (E12)", second[-110:])
    band, _ = kin.speed_band(vf.read_track(golden / "pr055_sphere_track.csv"), 30.0)
    check(band["clipped"] == 3 and [f["frame"] for f in band["jumps"]["flags"] if f["kind"] == "glitch"] == [1207, 1210, 1268],
          "PR055's sphere: three glitches of 2-3 px named and left out of its band", kin.jumps_said(band)[:110])
    band, _ = kin.speed_band(vf.read_track(golden / "flyer5_paper_track.csv"), 60.0)
    check(max(band["nugget_px"]) < 0.15 and band["v_min"][1] < 120 < 160 < band["v_max"][1],
          "Galileo flyer 5's paper track: the bird holds to a tenth of a pixel and speeds up along it",
          f"nugget {max(band['nugget_px']):.2f} px, {band['v_min'][1]:.0f}-{band['v_max'][1]:.0f} px/s")


def test_the_speed_band_in_the_stage_and_the_report():
    """What the stage records and the report says of it: the band's fields beside the line's, the files beside
    the case, and the words -- an average over a changing speed in place of a refusal, the constant case said
    as such, the band's absence NO POWER."""
    print("\nkinematics: the speed band in the stage and the report")
    from mcdonald import forensics as vf, stages
    import json as _json
    import tempfile
    golden = Path(__file__).resolve().parent / "golden"
    with tempfile.TemporaryDirectory() as td:
        trk = vf.read_track(golden / "pr055_sphere_track.csv")
        f = stages.kinematics(trk, 30.0, 1920, "pr055", out=str(Path(td) / "pr055"))
        b = f.fields["band"]
        check(b and not b["constant"] and not f.fields["uniform"] and "speed band" in f.result and "speed change" in f.result,
              "PR055's sphere: not uniform, and the band says how the speed ran", f.result["speed change"][:90])
        check("ran from 26 to 99 px/s" in f.result["uniform_motion"] and "an average over a changing speed" not in f.result.get("body-lengths/s", ""),
              "the not-uniform line carries the band's range", f.result["uniform_motion"])
        check(all(Path(x).exists() for x in f.files) and [Path(x).name for x in f.files] == ["pr055_speed.csv", "pr055_speed.png"],
              "the rate frame by frame and its figure are written beside the case", ", ".join(Path(x).name for x in f.files))
        rows = [l for l in Path(f.files[0]).read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
        check(len(rows) == b["n"] + 1 and rows[0].startswith("frame,t_s,vx_px_per_s"), "the CSV has a row a point under its header", rows[0])
        _json.dumps(f.fields)
        c = report.Case("pr055", str(Path(td) / "pr055.mp4"))
        f.into(c)
        line = c.bottom_line()
        check("speed in the image changed" in line and "least 26, most 99" in line and "**not** a rate it held" in line,
              "the bottom line describes the change instead of refusing", line[:160])
        row = c.summary()[0]
        check("ran from 26 to 99 px/s" in row[3] and "not a rate it held" in row[3], "and the summary's row says it", row[3][:120])
        check(f.result.get("band backtest", "").startswith(b["backtest"]["light"] + ": ") and
              f"held to its own track, the band is {b['backtest']['light']}" in row[3]
              and f"held to its own track, the band is {b['backtest']['light']}" in Path(f.files[0]).read_text(encoding="utf-8").splitlines()[0],
              "the band's backtest (E1): its light and reasons in the stage, the light in the summary's row and the CSV's header",
              f.result.get("band backtest", "")[:120])
        check(any(n.startswith("The track is not uniform straight-line motion: the speed ran from") for n in f.notes),
              "the note begins as add_known expects (KIN_NOTES) and goes on with the band")
        g = stages.kinematics(trk, 30.0, 1920, "pr055", size_px=12.0)
        check("[an average over a changing speed: it ran from 26 to 99 px/s (the speed band)]" in g.result["body-lengths/s"],
              "a speed in body lengths of a changing speed is marked an average, not unquotable", g.result["body-lengths/s"][-70:])
        check("NOT UNIFORM" in g.carry["reduction"].report() and "numbers below are for its average" in g.carry["reduction"].report(),
              "the reduction's own print says the same")

        trk = {n: (100.0 + 18.0 * (n - 1), 50.0 + 2.0 * (n - 1)) for n in range(1, 40)}
        f = stages.kinematics(trk, 30.0, 1920, "t")
        c = report.Case("t", "/tmp/t.mp4")
        f.into(c)
        check(f.fields["band"]["constant"] and "constant within its band" in f.result["speed change"]
              and "(constant within ±0 px/s, the speed band; a steady change of its speed of more than 0.0 px/s over the 1.3 s "
              "would have shown (95 %))." in c.bottom_line() and "± 0.00" in c.summary()[0][2]
              and "a steady change of its speed of more than 0.0 px/s" in c.summary()[0][3],
              "a constant rate is said to be, with its band and the most it could have changed (E12), in the stage, the bottom "
              "line and the row", c.summary()[0][2])
        f = stages.kinematics({n: (float(n), 0.0) for n in range(1, 6)}, 30.0, 1920, "t")
        check(f.fields["band"] is None and dict(f.no_power).get("speed band", "").startswith("fewer than 10 points"),
              "a track too short for a band: NO POWER, and the line's rate stands", f.result["v_px"])


def _pinhole(X0, V, k, c, t):
    X = np.asarray(X0, float)[None, :] + np.asarray(V, float)[None, :] * t[:, None]
    return np.c_[c[0] + k * X[:, 0] / X[:, 2], c[1] + k * X[:, 1] / X[:, 2]]


WANDER_FALSE = 4          # of 40 slowly wandering size series, the most that may pass as looming (these seeds give 3; the sweep 2 in 100)


def test_what_survives_the_missing_variables():
    """ROADMAP 0.4, objective 3 (docs/method.md section 33): the projective constant-velocity test, the turn radius in
    body widths and the smear number, each on drawn tracks whose answer is known by construction -- a pinhole camera
    and an object at constant velocity, one that closes (t_z, the aspect angle and v / R recovered), one far away
    (no closing seen), one that curves (the test fails as it should); an arc of known radius for the turn."""
    print("\nprojective: what survives the missing variables")
    from mcdonald import projective as pj
    rng = np.random.default_rng(5)
    fps, k, c = 30.0, 1920 / math.radians(30), (960.0, 540.0)
    t = np.arange(0, 1.0, 1 / fps)
    X0, V = np.array([-200.0, 50.0, 1000.0]), np.array([60.0, -10.0, -400.0])          # crosses the camera's plane at 2.5 s
    p = _pinhole(X0, V, k, c, t) + rng.normal(0, 0.5, (len(t), 2))
    trk = {i + 1: tuple(p[i]) for i in range(len(t))}
    f = pj.fit(trk, fps, k=k, centre=c)
    Xl = X0 + V * t[-1]
    v_over_R = np.linalg.norm(V) / np.linalg.norm(Xl)
    theta = math.degrees(math.acos(abs(np.dot(V, Xl)) / np.linalg.norm(V) / np.linalg.norm(Xl)))
    hw = (f["t_z_band"][1] - f["t_z_band"][0]) / 2
    check(f["closing"] is True and abs(f["t_z"] - 2.5) < 0.15 and 0.01 < hw < 0.1 and abs(hw - f["t_z_err"]) < 1e-12,
          "a closing object: the model fits, t_z found with its band, one of its errors either side (over 100 such draws "
          "the band holds the truth 76 % of the time, its 95 % 96 %; 2026-10-30)",
          f"t_z {f['t_z']:.2f} ({f['t_z_band'][0]:.2f}-{f['t_z_band'][1]:.2f}) for 2.5")
    # t_z's error under the track's own covariance (the pure-mathematics survey's M5, its other half): the same object
    # with jitter that has memory (AR(1), φ 0.6, as a centroid drifts for a few frames), where the residual bootstrap
    # it replaced, resampling the points as if each were drawn alone, held the truth 39 % of the time at 16-84 % and 70 %
    # at 2.5-97.5 % (100 draws, 2026-10-30; the sandwich 68 and 91 %)
    held, n_tz = [0, 0], 0
    for seed in range(30):
        g = np.random.default_rng(700 + seed)
        e = np.zeros((len(t), 2))
        e[0] = g.normal(0, 0.5, 2)
        for i in range(1, len(t)):
            e[i] = 0.6 * e[i - 1] + g.normal(0, 0.5 * math.sqrt(1 - 0.6 ** 2), 2)
        h = pj.fit({i + 1: tuple(q) for i, q in enumerate(_pinhole(X0, V, k, c, t) + e)}, fps)
        if h.get("t_z_err"):
            n_tz += 1
            held = [held[0] + (abs(h["t_z"] - 2.5) <= h["t_z_err"]), held[1] + (abs(h["t_z"] - 2.5) <= 1.959964 * h["t_z_err"])]
    check(n_tz >= 27 and 0.5 <= held[0] / n_tz <= 0.9 and held[1] / n_tz >= 0.83,
          "with jitter that has memory, t_z's error is the track's own covariance's: its band holds the truth about as often "
          "as it says", f"{held[0]} of {n_tz} within one error, {held[1]} within 1.96")
    check(abs(f["v_over_R"] - v_over_R) < 0.1 * v_over_R, "its speed in units of its range at the last frame", f"{f['v_over_R']:.3f} for {v_over_R:.3f} /s")
    check(abs(f["psi_deg"] - theta) < 1.0, "and the aspect angle there, from the vanishing point with k", f"{f['psi_deg']:.1f}° for {theta:.1f}°")
    check(f["rms"] < 1.25 * f["rms_quad"] and f["rms"] < 0.5 * f["rms_const"], "it describes the track as a free quadratic does, and constant image speed does not",
          f"{f['rms']:.2f} px against {f['rms_quad']:.2f} and {f['rms_const']:.2f}")
    check(f["fits"] is True and f["misfit"] < 1.5 and abs(f["jitter_px"] - 0.5 * math.sqrt(2)) < 0.15,
          "and it fits to the track's own jitter (the larger of two readings of it): the half pixel drawn", f"{f['misfit']:.2f} times {f['jitter_px']:.2f} px")
    X0, V = np.array([-200.0, 50.0, 10000.0]), np.array([600.0, -100.0, -4.0])          # far away: the range hardly changes
    p = _pinhole(X0, V, k, c, t) + rng.normal(0, 0.5, (len(t), 2))
    f = pj.fit({i + 1: tuple(p[i]) for i in range(len(t))}, fps)
    check(f["closing"] is False and f["straight_rms"] < 1.0 and f["fits"] is True, "a far object at constant velocity: no closing seen, the track straight",
          f"straight to {f['straight_rms']:.2f} px, t_z {f['t_z']:.0f} s, {f['misfit']:.2f} times its jitter")
    # the same far object under a camera that sways by 2 px (the slew a gimbal adds), its centroid read to a tenth: the
    # models, compared only with one another, still pass it (no closing seen); held to its jitter, constant speed
    # follows only its trend (PR077's loop and PR135's members, the pure-mathematics survey, 2026-10-29)
    p = (_pinhole(X0, V, k, c, t) + rng.normal(0, 0.1, (len(t), 2))
         + 2.0 * np.c_[np.sin(2 * math.pi * t / 0.8), np.cos(2 * math.pi * t / 1.1)])
    f = pj.fit({i + 1: tuple(p[i]) for i in range(len(t))}, fps)
    said = pj.said(f)["constant velocity"]
    check(f["closing"] is False and f["fits"] is False and f["misfit"] > 2 * pj.NUGGETS and "describes its trend" in said
          and "no time to the camera's plane" in said and pj.trend_px(f) == f"{f['rms_const']:.1f}",
          "a camera's sway: the models pass it, but held to its jitter the model follows only the trend, and says so",
          f"{f['misfit']:.1f} times its jitter ({f['jitter_px']:.2f} px)")
    # "no closing seen" as a bound (M5): the band's change of speed along the track bounds how fast the depth changed,
    # if it flew straight at a steady speed -- held to drawn objects whose depth rate is known (2026-10-29: four
    # approaches and retreats, 40 draws each, held the truth 40, 40, 38 and 36 times at 95 %)
    held, n_dep = 0, 0
    for seed in range(20):
        g = np.random.default_rng(300 + seed)
        T2 = np.arange(0, 2.0, 1 / fps)
        q = _pinhole([-200.0, 50.0, 5000.0], [600.0, -100.0, -100.0], k, c, T2) + g.normal(0, 0.5, (len(T2), 2))
        d = pj.fit({i + 1: tuple(q[i]) for i in range(len(T2))}, fps, boot=0)["depth"]
        n_dep += d is not None
        held += d is not None and d["rate_max_per_s"] >= 100.0 / (5000.0 - 100.0 * T2[-1])
    check(n_dep >= 15 and held >= 0.85 * n_dep, "no closing seen, bounded: the depth's rate is under the bound the speed change gives, "
          "nearly every time", f"{held} of {n_dep} for a truth of {100.0 / (5000.0 - 100.0 * T2[-1]):.4f}/s")
    far = pj.fit({i + 1: tuple(p_) for i, p_ in enumerate(_pinhole(X0, V, k, c, t) + rng.normal(0, 0.5, (len(t), 2)))}, fps, boot=0)
    d = far["depth"]
    check(d and d["rate_max_per_s"] >= 4.0 / 10000.0 and math.isfinite(d["T_closing_min_s"]) and math.isfinite(d["T_receding_min_s"])
          and "its depth changed by less than" in pj.said(far)["constant velocity"] and "says nothing" not in pj.said(far)["constant velocity"],
          "and said in place of 'the track says nothing of how its range changed'", pj.said(far)["constant velocity"][-120:])
    flat = dict(v_mean_px_per_s=600.0, vx_mean=600.0, vy_mean=0.0, t0=0.0, t1=1.0, dv_xy=[0.0, 0.0],
                dv_err_xy=[1e-6, 1e-6])
    check(pj.depth_bound(flat)["rate_max_per_s"] < 1e-5 and pj.depth_bound(flat, floor=5.0)["rate_max_per_s"] > 0.005,
          "a band that reads the velocity as unchanging to within nothing (its wander fitted to nothing) is floored by a "
          "free quadratic's error, which `fit` gives it")
    # the mean speed is the ends' geometric mean under the model (session 13, 2026-10-30): every change of speed has its T,
    # past twice the mean too, where the split v -/+ dv / 2 went through zero
    off = 0.0
    for T_, L_ in ((100.0, 2.0), (10.0, 35.0), (1.0, 9.0), (-50.0, 2.0), (-40.0, 35.0), (-3.0, 2.0)):
        a_ = 1000.0
        v_, dv_ = a_ / (T_ * (T_ + L_)), a_ / T_ ** 2 - a_ / (T_ + L_) ** 2
        off = max(off, abs(pj._T_from(abs(v_), dv_ * (1 if v_ > 0 else -1), L_) / T_ - 1.0))
    check(off < 1e-9, "T from the mean speed and the change of speed, exactly, closing and receding, at r 1.02 to 10", f"{off:.1g}")
    band_of = lambda dv, a=None, b=None: dict(v_mean_px_per_s=100.0, vx_mean=100.0, vy_mean=0.0, t0=0.0, t1=2.0, dv_xy=[dv, 0.0],
                                              dv_err_xy=[1.0, 1.0], v_start=[0.0, a, 1.0], v_end=[2.0, b, 1.0])
    d = pj.depth_bound(band_of(250.0, 39.0, 289.0))
    check(d is not None and d["dv_err_px_per_s"] > 0.1 * 250.0 and math.isfinite(d["T_closing_min_s"]) and d["T_closing_min_s"] < 2.0,
          "a change past twice the mean has its bound now, with a tenth of the change in its error (the band's ends lag a steep curve)",
          f"{100 * d['rate_max_per_s']:.0f} % a second" if d else "none")
    got, why = pj.depth_read(band_of(450.0, 12.0, 830.0))
    check(got is None and "more than 4 times over" in why, "past DEPTH_X times the mean no bound, and it says why", why)
    got, why = pj.depth_read(band_of(30.0, 300.0, 330.0))
    check(got is None and "the track's wander's" in why, "ends three times the mean are no straight flight's: the model has their "
          "geometric mean equal to it, and it says so", why)
    check(pj.depth_read(band_of(30.0, 85.0, 115.0))[0] is not None and pj.depth_bound({}) is None and pj.depth_read({}) == (None, None),
          "ends about the mean are read; no band, no reason to give")
    closing_ = band_of(90.0, 65.0, 155.0)
    check(pj.depth_read(closing_, t_z=5.8)[0] is not None and pj.depth_read(closing_)[0] is not None,
          "a bound is of the trend the test chose: a change of speed that trend draws is read")
    got, why = pj.depth_read(closing_, t_z=2.4)
    check(got is None and "not that trend's" in why, "one that trend does not draw is none: a link hopping on a large object reads its ends' speed anywhere", why)
    held, n_dep = 0, 0
    for seed in range(12):                                   # r = 2.4, x = 2: 6 of 10 on the geometric form alone, every one of 12 with the share
        g = np.random.default_rng(800 + seed)
        T2, L2 = np.arange(61) / 30.0, 2.0
        T3 = L2 / (2.414 - 1.0)
        a_ = 1200.0 * T3 * (T3 + L2) / L2
        q = np.c_[300 + a_ / (L2 + T3 - T2) - a_ / (L2 + T3), 200 + 0.0 * T2] + g.normal(0, 0.5, (61, 2))
        d = pj.depth_bound(pj.band_of({i + 1: tuple(q[i]) for i in range(61)}, 30.0))
        n_dep += d is not None
        held += d is not None and d["rate_max_per_s"] >= 1.0 / T3
    check(n_dep >= 11 and held >= n_dep - 1, "a drawn approach whose speed changes by twice its mean: bounded, and the bound holds the truth",
          f"{held} of {n_dep}")
    wander = {i + 1: (300 + 40 * math.cos(i / 6.0) + 0.05 * i, 300 + 40 * math.sin(i / 6.0)) for i in range(120)}
    wa = pj.depth_read(pj.band_of(wander, 30.0))
    check(wa[0] is None and wa[1], "a track looping over a short chord gets no bound, and the reason", str(wa[1])[:90])
    far_f = dict(closing=False, fits=True, misfit=2.0, jitter_px=0.5, straight_rms=1.0, rms_const=1.0, depth=None, depth_none="no bound on how fast its depth changed: X")
    far_t = dict(far_f, fits=False, rms=1.0, rms_quad=1.0, depth_none="no bound on how fast its depth changed: Y")
    check("and no bound on how fast its depth changed: X" in pj.said(far_f)["constant velocity"]
          and "; no bound on how fast its depth changed: Y" in pj.said(far_t)["constant velocity"], "and the sentence gives that reason")
    exact = pj.fit({i + 1: (300.0 + 2.0 * i, 100.0 + 0.5 * i) for i in range(30)}, fps)
    check(exact["fits"] is True and abs(exact["jitter_px"] - pj.JITTER_FLOOR * math.sqrt(2)) < 1e-9,
          "a drawn track with no jitter at all is held to the floor, a tenth of a pixel, and fits", f"{exact['misfit']:.1g}")
    rel = pj.fit({i + 1: tuple(p[i]) for i in range(8)}, fps, band={})
    check(rel["fits"] is None and rel["misfit"] is None and "not held to the track's own jitter" in pj.said(rel)["constant velocity"],
          "under ten points with no band there is no jitter to hold it to: the verdict is the models' alone, and says so")
    p = np.c_[300 + 500 * t + 300 * t ** 2, 500 + 100 * t - 400 * t ** 2] + rng.normal(0, 0.5, (len(t), 2))
    f = pj.fit({i + 1: tuple(p[i]) for i in range(len(t))}, fps)
    check(f["closing"] is None and f["straight_rms"] > 5, "a curving track fails the test", f"straight to {f['straight_rms']:.1f} px: neither model")
    check(pj.fit({i + 1: tuple(p[i]) for i in range(4)}, fps) is None, "under six points there is no test")
    # the turn number: an arc of radius 500 px over a 400-px chord, the object 10 px wide
    r, L = 500.0, 400.0
    ang = np.linspace(-math.asin(L / 2 / r), math.asin(L / 2 / r), 40)
    arc = np.c_[800 + r * np.sin(ang), 900 - r * np.cos(ang)] + rng.normal(0, 0.3, (40, 2))
    tn = pj.turn({i + 1: tuple(arc[i]) for i in range(40)}, fps, 10.0)
    check(tn["turned"] and abs(tn["r_turn_over_D"] - 50) < 5, "an arc of 500 px drawn by a 10-px object: a turn of about 50 body widths",
          f"{tn['r_turn_over_D']:.1f}, sagitta {tn['sagitta_px']:.1f} ± {tn['sagitta_err_px']:.1f} px")
    words = pj.said(None, tn, None)["turn"]
    own = f"the turn's own radius is {0.118 * tn['r_turn_over_D']:,.0f} to {6.57 * tn['r_turn_over_D']:,.0f} body widths nine times in ten"
    check(tn["how"] == "sagitta" and own in words,
          "an arc of 47° is read by its sagitta, and said as the picture's radius, the turn's own 0.12 to 6.6 times it (M4: "
          "the tilt of its plane)", words[words.index(" -- ") + 4:][:110])
    line = np.c_[300 + 500 * t, 500 + 100 * t] + rng.normal(0, 0.3, (len(t), 2))
    tn = pj.turn({i + 1: tuple(line[i]) for i in range(len(t))}, fps, 10.0)
    check(not tn["bent"] and tn["r_turn_over_D_low"] > 300, "a straight track with jitter: did not turn, the radius at least hundreds of body widths",
          f"at least {tn['r_turn_over_D_low']:.0f} (95 %)")
    words = pj.said(None, tn, None)["turn"]
    check("did not turn" in words and "one 10 times tighter looks this straight for 4 % of the ways its plane can lie, 40 times "
          "tighter for 1 %" in words, "and 'did not turn' says how a turn hides: its plane holding the line of sight", words[-100:])
    check(pj.turn(trk, fps, None) is None, "no width, no turn number")
    exact = pj.turn({i + 1: (300.0 + 2.0 * i, 100.0) for i in range(20)}, fps, 9.0)      # drawn, with no jitter at all
    check(exact["r_turn_over_D_low"] is None and "no bend at all: it did not turn" in pj.said(None, exact, None)["turn"],
          "a track with no bend at all (drawn): did not turn, with no bound to give -- said, not a crash (2026-10-29: the "
          "kinematics stage raised on one)", pj.said(None, exact, None)["turn"][:80])
    check(abs(pj.smear(609.0, 30.0, 4.27) - 4.754) < 0.01, "the smear number: PR43's 609 px/s over a 4.27-px width is 4.75 widths a frame")
    said = pj.said(f, tn, pj.smear(609.0, 30.0, 4.27))
    check("did not turn" in said["turn"] and "streaks within a frame" in said["smear"] and "not a straight line at constant velocity" in said["constant velocity"],
          "each has its sentence")


def test_a_turn_seen_past_150_degrees_is_read_whole():
    """The turn as an ellipse (the pure-mathematics survey's M4, docs/method.md section 33): a body going round a circle
    at a steady rate draws, through an affine camera at any range, field of view and tilt, the affine image of uniform
    circular motion -- an ellipse whose semi-major axis is the circle's radius unforeshortened, its minor over its
    major |cos i|. Past 150° of turn `projective.turn` reads it so; the sagitta, a formula for a small bend, read a drawn
    286° arc of 25 body widths as 12 and a whole circle as thousands (the survey's §6.2). Under it the sagitta stays,
    with the tilt's band in its words, the constants of which are recomputed here."""
    print("\nprojective: the turn read whole past 150 degrees (M4)")
    from mcdonald import projective as pj
    rng = np.random.default_rng(29)

    def circle(arc_deg, incl_deg, drift=(0.0, 0.0), w=0.6, r=100.0, fps=30.0):
        t = np.arange(int(round(math.radians(arc_deg) / w * fps))) / fps
        ph, rot, ci = w * t + rng.uniform(0, 2 * math.pi), rng.uniform(0, 2 * math.pi), math.cos(math.radians(incl_deg))
        R = np.array([[math.cos(rot), -math.sin(rot)], [math.sin(rot), math.cos(rot)]])
        p = (R @ np.vstack([r * np.cos(ph), r * ci * np.sin(ph)])).T + np.outer(t, drift) + rng.normal(0, 0.3, (len(t), 2)) + 500
        return {i + 1: (float(x), float(y)) for i, (x, y) in enumerate(p)}
    for arc, incl in ((286, 0), (286, 70), (360, 45), (540, 85), (180, 0)):
        tn = pj.turn(circle(arc, incl), 30.0, 4.0)
        e = tn["ellipse"] or {}
        check(tn["how"] == "ellipse" and abs(tn["r_turn_over_D"] - 25) < 1.0 and abs(e["cos_i"] - math.cos(math.radians(incl))) < 0.03
              and abs(e["omega_rad_per_s"] - 0.6) < 0.01 and tn["turned"],
              f"a {arc}° turn of 25 body widths, its plane {incl}° from facing the camera: read whole, the radius, the tilt and the rate",
              f"{tn['r_turn_over_D']:.2f} widths (the sagitta {tn['sagitta_r_over_D']:.0f}), cos i {e.get('cos_i', 0):.3f}, "
              f"{e.get('omega_rad_per_s', 0):.3f} rad/s")
    words = pj.said(None, tn, None)["turn"]
    check("the track loops" in words and "body widths a second" in words and "foreshortening" in words and "Π_L" not in words
          and abs(e["speed_widths_per_s"] - 15) < 0.5 and abs(e["accel_widths_per_s2"] - 9) < 0.3,
          "and said: the speed and the acceleration toward its centre in body widths, with no range, field of view or foreshortening",
          f"{e['speed_widths_per_s']:.1f} widths/s, {e['accel_widths_per_s2']:.2f} widths/s²")
    tn = pj.turn(circle(90, 45), 30.0, 4.0)
    check(tn["how"] == "sagitta", "a quarter turn is not read whole: a short arc does not fix a circle", f"{tn['r_turn_over_D']:.0f}")
    tn = pj.turn(circle(540, 0, drift=(100.0, 30.0)), 30.0, 4.0)
    check(tn["how"] == "sagitta", "a circle drifting faster than it goes round draws a wave, not a loop: not read as one",
          f"{tn['r_turn_over_D']:.0f}")
    t = np.arange(150) / 30.0
    tn = pj.turn({i + 1: (300 + 200 * x + rng.normal(0, 0.5), 400 + 50 * x + rng.normal(0, 0.5)) for i, x in enumerate(t)}, 30.0, 4.0)
    check(tn["how"] == "sagitta" and not tn["bent"], "a straight track is not a loop")
    sway = 300 + 20 * t + 40 * np.cos(2.0 * t)              # back and forth along a line, reversing (a turn seen edge-on, or a sway)
    tn = pj.turn({i + 1: (x + rng.normal(0, 0.5), 0.5 * x + rng.normal(0, 0.5)) for i, x in enumerate(sway)}, 30.0, 4.0)
    check(tn["how"] == "sagitta", "nor is a thing that goes back and forth along a line: it does not go round",
          f"{(tn['ellipse'] or {}).get('minor_px', 0):.1f}")
    # the tilt's band (the survey's §6.5), recomputed on a grid: the picture's radius of curvature over the turn's own,
    # (sin²φ + cos²i cos²φ)^1.5 / cos i, with cos i and φ uniform
    c = (np.arange(1000) + 0.5) / 1000
    C, P = np.meshgrid(c, c * 2 * math.pi, indexing="ij")
    rho = ((np.sin(P) ** 2 + C ** 2 * np.cos(P) ** 2) ** 1.5 / C).ravel()
    lo, hi = np.percentile(rho, [5, 95])
    check(abs(1 / hi - pj.TILT_OWN[0]) < 0.002 and abs(1 / lo - pj.TILT_OWN[1]) < 0.03
          and all(abs(np.mean(rho > m) - share) < 0.0005 for m, share in pj.TILT_STRAIGHTER),
          "the tilt's band in the words is the geometry's: the turn's own radius 0.118 to 6.57 times the picture's, ten times "
          "straighter 4.25 % of the time, forty 1.06 %", f"{1 / hi:.3f}-{1 / lo:.2f}; {np.mean(rho > 10):.4f}, {np.mean(rho > 40):.4f}")


def test_tau_and_the_admissible_region():
    """tau from looming on a rendered approaching disc (its size read frame by frame by flicker's own `extent`) and from
    a light curve with a gain on it; the aspect angle from tau; and the admissible region in (R, Rdot), whose rim and
    samples follow from the bounds by construction."""
    print("\nkinematics: tau from looming and the light curve; the admissible region")
    from mcdonald import flicker
    rng = np.random.default_rng(7)
    fps, t_z = 30.0, 4.0
    t = np.arange(0, 2.0, 1 / fps)
    sizes = []
    yy, xx = np.mgrid[0:301, 0:301]
    for ti in t:
        sig = 18.0 / (t_z - ti)                                 # a Gaussian blob whose width goes as 1 / (t_z - t): 4.5 to 9 px
        g = 40 + 120 * np.exp(-((xx - 150) ** 2 + (yy - 150) ** 2) / (2 * sig ** 2)) + rng.normal(0, 2.0, xx.shape)
        sizes.append(flicker.extent(g, 150.0, 150.0))          # read in whole pixels, as the stage reads it
    lm = kin.looming_fit(t, sizes)
    check(lm is not None and abs(lm["t_z"] - t_z) < 0.5 and lm["t_z_band"][0] - 0.3 < t_z < lm["t_z_band"][1] + 0.3,
          "a rendered disc growing as 1/(t_z - t): t_z from its sizes alone, read in whole pixels",
          f"t_z {lm['t_z']:.2f} ({lm['t_z_band'][0]:.2f}-{lm['t_z_band'][1]:.2f}) for {t_z}")
    check(abs(lm["tau_last"] - (t_z - t[-1])) < 0.5, "and tau at the last frame", f"{lm['tau_last']:.2f} s for {t_z - t[-1]:.2f}")
    gain = 1.0 + 0.3 * np.sin(2 * np.pi * t / 1.3)                  # AGC on both apertures
    F = 50.0 / (t_z - t) ** 2 * gain * (1 + rng.normal(0, 0.01, len(t)))
    B = 20.0 * gain * (1 + rng.normal(0, 0.01, len(t)))
    lc = kin.tau_from_light_curve(t, F, B)
    tau_mid = t_z - t.mean()
    check(lc is not None and abs(lc["tau"] - tau_mid) < 0.35 * tau_mid, "a 1/R² light curve under a gain, the gain taken out by a background aperture: tau",
          f"{lc['tau']:.2f} s for about {tau_mid:.2f} at the arc's middle")
    bad = kin.tau_from_light_curve(t, F)
    check(abs(bad["tau"] - tau_mid) > abs(lc["tau"] - tau_mid), "without the background the gain leaks in", f"{bad['tau']:.2f} s")
    check(abs(kin.aspect_from_tau(0.02, 3.0) - math.degrees(math.atan(0.06))) < 1e-9 and kin.aspect_from_tau(None, 3.0) is None,
          "theta = atan(omega tau), nothing without either")
    reg = kin.admissible_region(0.01, R_min=1000.0, R_max=5000.0, v_cap=1029.0)
    check(reg and abs(reg["speed_min"] - 10.0) < 1e-9 and abs(reg["speed_max"] - 1029.0) < 2.0 and reg["R_lo"] == 1000.0 and reg["R_hi"] == 5000.0,
          "the region: the least speed is omega R at the floor, the most the cap", f"{reg['speed_min']:.0f}-{reg['speed_max']:.0f} m/s")
    check(all(abs(rd) <= math.sqrt(1029.0 ** 2 - (0.01 * R) ** 2) + 1e-6 for R, rd in reg["edge"]), "its rim is the speed cap")
    sz = kin.admissible_region(0.01, k=3000.0, p_px=6.0, R_min=1000.0, S_max=4.0, v_cap=1029.0)
    check(abs(sz["R_hi"] - 2000.0) < 1e-6 and sz["bounds"][-1] == ("largest size", "high") and "size_m" in sz["samples"],
          "a size ceiling cuts the range where S = p R / k reaches it", f"R_hi {sz['R_hi']:.0f} m")
    tau = kin.admissible_region(0.01, R_min=1000.0, R_max=5000.0, v_cap=1029.0, tau_s=20.0)
    check(tau and abs(tau["samples"]["theta_deg"][1] - math.degrees(math.atan(0.2))) < 2.0, "with tau the region is one line, and the aspect angle one value",
          f"theta median {tau['samples']['theta_deg'][1]:.1f}° for {math.degrees(math.atan(0.2)):.1f}")
    check(kin.admissible_region(0.01, R_min=6000.0, R_max=5000.0).get("empty"), "bounds that cross leave nothing, and say so")
    check("at least 10 m/s and at most 1029" in kin.admissible_said(reg) and "the floor a stage measured" in kin.admissible_said(reg),
          "and the region has its sentence, naming what bounds it")
    check(kin.admissible_said(kin.admissible_region(0.01)) is None, "a region nothing bounds but the cap has no sentence: the figure is the fan")
    # the same region drawn two ways (the pure-mathematics survey's M2, its table: omega 0.01 rad/s, 2-20 km -- 31 % under
    # the speed of sound drawn evenly in R and Rdot, 97 % with the range log-uniform and the direction isotropic): the
    # extent is the clip's, and the region's sentence says it first and gives both draws beside it
    two = kin.admissible_region(0.01, R_min=2000.0, R_max=20000.0)
    iv, said = two["invariant"], kin.admissible_said(two)
    check(abs(two["share_subsonic"] - 0.31) < 0.03 and abs(iv["share_subsonic"] - 0.97) < 0.02 and abs(two["samples"]["speed"][1] - 525) < 25
          and abs(iv["speed"][1] - 84) < 10 and two["speed_min"] == 20.0 and two["speed_max"] == two["v_cap"]
          and said.index("that much is the clip's") < said.index("evenly in R and Ṙ") < said.index("the direction isotropic"),
          "one region, two draws: the extent stands, the share under the speed of sound is the draw's",
          f"{two['share_subsonic']:.0%} drawn evenly (median {two['samples']['speed'][1]:.0f} m/s), {iv['share_subsonic']:.0%} "
          f"invariantly (median {iv['speed'][1]:.0f})")
    odds = {m: 1 - math.sqrt(1 - 1 / m ** 2) for m in (1.155, 2, 10)}
    check(abs(odds[1.155] - 0.5) < 0.001 and abs(1 / odds[2] - 7.5) < 0.05 and abs(1 / odds[10] - 200) < 1
          and "half the time, more than twice it one time in 7.5 and more than ten times it one time in 200" in report.ISOTROPIC,
          "the fan's one-sidedness under an isotropic direction: the words the transverse row adds are the formula's",
          ", ".join(f"{m}: {p:.4f}" for m, p in odds.items()))
    wedge = kin.admissible_region(0.01, R_min=2000.0, R_max=20000.0, rate_max=0.005)
    check(wedge["invariant"]["theta_deg"][0] >= math.degrees(math.atan(0.01 / 0.005)) - 0.5 and abs(wedge["speed_max"] - 20000.0 * math.hypot(0.01, 0.005)) < 1e-6,
          "a wedge from the depth bound: the invariant draw's aspect stays inside it, and the extent's most is where the wedge meets the farthest range",
          f"theta {wedge['invariant']['theta_deg']}, at most {wedge['speed_max']:.0f} m/s")


def test_tau_of_reads_a_size_that_looms_and_nothing_else():
    """`kinematics.tau_of`'s rules (docs/method.md section 33) on drawn size series, read as the flicker stage reads them --
    a radius in whole pixels, the blur's reach on top: a size growing as a straight approach draws it gives tau at the
    last frame (and the plain law, with no room for the blur, puts it late); one that holds gives none; one read on too
    few of the frames it was tried on gives none; slips to a neighbour are dropped; a size that wanders slowly rarely
    passes; a point has no size, and its light curve is read only as what it would say, never by a thing that beats."""
    print("\nkinematics: tau from a size series, and when there is none")
    fps, tz = 30.0, 6.0
    t = np.arange(0, 4.0, 1 / fps)
    truth = tz - t[-1]
    rng = np.random.default_rng(11)
    s = np.round(24 / (tz - t) + 2.6 + rng.normal(0, 0.3, len(t)))
    r = kin.tau_of(t, s)
    plain = kin.looming_fit(t, s, offset=False)
    check(r["route"] == "looming" and r["closing"] and abs(r["tau_s"] - truth) < max(2 * r["tau_err_s"], 0.25)
          and plain["tau_last"] - truth > 0.5,
          "a size growing as 1/(t_z - t) on top of the blur's reach: tau at the last frame; the law with no room for the blur puts it late",
          f"{r['tau_s']:.2f} ± {r['tau_err_s']:.2f} s for {truth:.2f} (offset {r['looming']['offset']:.1f} px); without it {plain['tau_last']:.2f}")
    held = kin.tau_of(t, np.round(9 + rng.normal(0, 0.6, len(t))))
    check(held["route"] is None and "held" in held["why"], "a size that holds: no tau", held["why"])
    gaps = [v if i % 3 == 0 else float("nan") for i, v in enumerate(s)]
    few = kin.tau_of(t, gaps)
    check(few["route"] is None and "comes and goes" in few["why"], "read on a third of the frames it was tried on: none", few["why"])
    slips = s.copy()
    slips[::11] = 70.0                                       # the far ring reaching a neighbour
    got = kin.tau_of(t, slips)
    check(got["route"] == "looming" and got["dropped"] >= len(s[::11]) and abs(got["tau_s"] - truth) < max(2 * got["tau_err_s"], 0.25),
          "slips to a neighbour are dropped against the running median, and tau stands", f"{got['dropped']} dropped, {got['tau_s']:.2f} s")
    false = 0
    for seed in range(40):                                   # a size that wanders slowly (a second's memory): rarely a tau
        g = np.random.default_rng(100 + seed)
        e = np.zeros(len(t))
        for i in range(1, len(t)):
            e[i] = 0.97 * e[i - 1] + g.normal(0, math.sqrt(1 - 0.97 ** 2))
        false += kin.tau_of(t, np.round(9 + e))["route"] == "looming"
    check(false <= WANDER_FALSE, f"a size that wanders with a second's memory passes at most {WANDER_FALSE} times in 40", f"{false} of 40")
    point = kin.tau_of(t, np.full(len(t), 2.0), flux=50.0 / (tz - t) ** 2 * (1 + 0.2 * np.sin(t)), level=20.0 * (1 + 0.2 * np.sin(t)))
    mid = tz - t.mean()
    check(point["route"] is None and "blur" in point["why"] and abs(point["light"]["tau"] - mid) < 0.1 * mid,
          "a point: no size to read; its light curve, the gain out by its ring, says what tau it would be", f"{point['light']['tau']:.2f} s for {mid:.2f}")
    beat = kin.tau_of(t, np.full(len(t), 2.0), flux=50.0 / (tz - t) ** 2, level=np.full(len(t), 20.0), beats=True)
    check(beat["light"] is None, "a thing that beats has no light-curve reading")
    capped = kin.tau_of(t, np.where(np.arange(len(t)) % 4 == 0, 3.0, kin.TAU_CAP_PX),
                        flux=50.0 / (tz - t) ** 2, level=np.full(len(t), 20.0))
    check(capped["route"] is None and capped["n"] == len(t[::4]) and "comes and goes" in capped["why"] and capped["light"],
          "a size read out to the extent's cap is no size (the Yemen object inside its gate, 2026-10-29): not \"held at "
          "80 px\", and not resolved, so its light curve is read", capped["why"])


def test_what_survives_reaches_the_stage_and_the_report():
    """The stage records the three with the band, and the report prints them as rows and a paragraph; the window
    reads the same fields."""
    print("\nstages: what survives, in the stage and the report")
    from mcdonald import stages
    rng = np.random.default_rng(9)
    fps, k, c = 30.0, 1920 / math.radians(30), (960.0, 540.0)
    t = np.arange(0, 1.0, 1 / fps)
    p = _pinhole([-200.0, 50.0, 1000.0], [60.0, -10.0, -400.0], k, c, t) + rng.normal(0, 0.5, (len(t), 2))
    trk = {i + 1: tuple(p[i]) for i in range(len(t))}
    sc = kin.AngularScale.from_fov(1920, 30.0)
    f = stages.kinematics(trk, fps, 1920, "t", sc, height=1080, size_px=8.0)
    kf = f.fields
    check(kf["projective"]["closing"] is True and kf["turn"] is not None and kf["smear"] is not None and kf["width_px"]["how"] == "given",
          "the fields: the projective test, the turn and the smear, from the width given")
    check(all(n in f.result for n in ("turn", "constant velocity", "smear")), "and their sentences in the result")
    c_ = report.Case("t", "/tmp/t.mp4")
    report.Found("scale", {"k": f"{sc.k:.0f} px/rad"}, fields=dict(k_px_per_rad=float(sc.k), k_from="an ASSUMED field of view of 30 deg",
                                                                 fov_deg=30.0)).into(c_)
    f.into(c_)
    rows = {r[0]: r for r in c_.summary()}
    check(rows["constant velocity, as a pinhole draws it"][2].startswith("passes: closing, T = ") and "θ = " in rows["constant velocity, as a pinhole draws it"][2]
          and rows["turn radius in body widths"][2] is not None and rows["smear"][2].endswith("widths a frame"),
          "the summary's rows", rows["constant velocity, as a pinhole draws it"][2])
    line = c_.bottom_line()
    check("Without a range, a field of view or the platform's speed, the track itself says this." in line and "closing on the camera" in line,
          "and the bottom line's paragraph", line[line.find("Without a range"):][:140])
    reg = c_.admissible()
    check(reg and not reg.get("empty") and reg["bounds"] == [("speed cap", "high")] and "size_m" in reg["samples"],
          "the admissible region from the case: the cap alone bounds it, the size from the extent and k")
    g = stages.kinematics(trk, fps, 1920, "t", sc, height=1080)
    check("turn" in dict(g.no_power) and g.fields["turn"] is None and g.fields["projective"] is not None,
          "with no width the turn and the smear are NO POWER, the projective test stands")
    check("times the track's own jitter" in rows["constant velocity, as a pinhole draws it"][3]
          and f.fields["projective"]["fits"] is True
          and f.fields["projective"]["jitter_from"] in ("the model's residual", "the speed band's nugget"),
          "held to the track's own jitter (the larger of the band's nugget and its residual's), which it fits",
          rows["constant velocity, as a pinhole draws it"][3][-60:])
    sway = _pinhole([-200.0, 50.0, 10000.0], [600.0, -100.0, -4.0], k, c, t) + rng.normal(0, 0.1, (len(t), 2)) \
        + 2.0 * np.c_[np.sin(2 * math.pi * t / 0.8), np.cos(2 * math.pi * t / 1.1)]
    w = stages.kinematics({i + 1: tuple(sway[i]) for i in range(len(t))}, fps, 1920, "t", sc, height=1080, size_px=8.0)
    c_ = report.Case("t", "/tmp/t.mp4")
    w.into(c_)
    row = {r[0]: r for r in c_.summary()}["constant velocity, as a pinhole draws it"]
    check(w.fields["projective"]["fits"] is False and row[2].startswith("describes its trend to ") and "times its own jitter" in row[3]
          and "describes its trend" in c_.bottom_line() and "no closing seen" not in c_.bottom_line(),
          "a camera's sway: the row and the bottom line say the model describes its trend, not that it passes", row[2])
    # a far object that fits, with no closing seen: how fast its depth could change bounds θ with k (the ledger and the
    # summary) and cuts the admissible region to a wedge (M5)
    farp = _pinhole([-200.0, 50.0, 10000.0], [600.0, -100.0, -4.0], k, c, t) + rng.normal(0, 0.5, (len(t), 2))
    g = stages.kinematics({i + 1: tuple(farp[i]) for i in range(len(t))}, fps, 1920, "t", sc, height=1080, size_px=8.0)
    cf = report.Case("t", "/tmp/t.mp4")
    report.Found("scale", {"k": f"{sc.k:.0f} px/rad"}, fields=dict(k_px_per_rad=float(sc.k), k_from="a field of view of 30 deg",
                                                                 fov_deg=30.0)).into(cf)
    g.into(cf)
    pjf, th = g.fields["projective"], {r["symbol"]: r for r in cf.ledger()}["θ"]
    b, om = pjf["depth"]["rate_max_per_s"], g.fields["omega_rad_per_s"]
    reg = cf.admissible()
    row = {r[0]: r for r in cf.summary()}["aspect angle / range rate"]
    check(pjf["closing"] is False and pjf["fits"] is True and th["status"] == "bounded"
          and th["value"] == f"at least {math.degrees(math.atan(om / b)):.0f}°" and row[2].startswith("θ ≥ ")
          and reg["rate_max"] == b and all(rd <= b * R + 1e-9 for R, rd in reg["edge"]) and "a wedge" in kin.admissible_said(reg),
          "no closing seen on a track that fits: θ bounded below by atan(ω / the depth's rate), and the region a wedge",
          f"{th['value']} at {100 * b:.2f} % a second; {row[2]}")
    held = {n: (500.0 + 0.3 * math.sin(n), 500.0 + 0.2 * math.cos(n)) for n in range(1, 60)}
    h = stages.kinematics(held, fps, 1920, "t", sc, height=1080, size_px=8.0)
    check(h.fields["fit"]["held"] and h.fields["projective"] is None and h.fields["turn"] is None and "turn" not in dict(h.no_power),
          "a track the camera held has none of them, and no NO POWER for it either: the motion is the camera's")


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
def test_a_beat_inside_a_flames_band_is_said_with_what_can_tell_them_apart():
    """A flame is a look-alike the beat cannot clear (flicker's item 11, 2026-10-20; Jacob: "important for mcdonald to note
    and handle"): a sky lantern's flame puffs at 4.7-8.7 Hz and a bundle of candles flickers near 10, each with its own
    phase, so members out of step do not clear it either. The bottom line says so wherever a beat is marked with one, and
    says which way the group's rigidity (`groups`) points: lanterns drifting on one wind keep their places, a flock
    rearranges. For one object it says that nothing here decides it. The headline is not touched."""
    print("\nreport: a beat inside a flame's band, and the group's rigidity beside it")
    from mcdonald import report
    lantern = [dict(hz=6.7, what="a sky lantern's flame, which puffs at 4.7-8.7 Hz with its own phase", source="sky lantern",
                    band=[[4.7, 8.7]], covers=False)]
    one = report.Case("t", "/tmp/x.mp4")
    report.Found("flicker", {"finding": "it beats"}, fields=dict(beats=True, beat={"object": dict(
        hz=6.43, double_hz=None, first=1, last=300, amplitude=0.12, stands=80.0, lookalike=lantern)}, finding="it beats")).into(one)
    line = one.bottom_line()
    check("where a flame flickers" in line and "Nothing here decides it for one object" in line and one.conclusion()[0] == report.BIRD,
          "one object's beat inside the lantern's band: the bottom line says a flame flickers there and nothing here decides "
          "it; the headline still names a bird", line[-200:])
    members = {f"member {i}": dict(hz=hz, double_hz=None, first=1240, last=1389, amplitude=0.15, stands=90.0, lookalike=lantern)
               for i, hz in enumerate((7.85, 7.38, 7.11), 1)}
    said = {}
    for rigid in (False, True, None):
        flock = report.Case("t", "/tmp/x.mp4")
        report.Found("flicker", {"finding": "out of step"}, fields=dict(beats=True, beat=members, finding="out of step")).into(flock)
        report.Found("groups", {"finding": "-"}, fields=dict(several=True, rigid=rigid, finding="-")).into(flock)
        said[rigid] = flock.bottom_line()
    check("being out of step does not tell a flame from a wingbeat" in said[False] and "does not keep its shape" in said[False]
          and "keeps its shape, as lanterns" in said[True] and "was not read" in said[None],
          "a flock's beats inside it: out of step does not clear a flame; the group that rearranges, keeps its shape, or was "
          "not read is said each way", said[False][-160:])
    plain = report.Case("t", "/tmp/x.mp4")
    report.Found("flicker", {"finding": "it beats"}, fields=dict(beats=True, beat={"object": dict(
        hz=3.5, double_hz=None, first=1, last=300, amplitude=0.12, stands=80.0, lookalike=[])}, finding="it beats")).into(plain)
    check("flame" not in plain.bottom_line(), "a beat outside every flame's band says nothing of flames", plain.bottom_line()[-120:])


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
    check(label == "Beats like a bird" and head.startswith("A bird is the leading explanation: its brightness beats at 3.9 Hz")
          and "7.9 Hz, its double" in head and "wingbeat" in head and "tumbling body" in head,
          "a beat at a wingbeat's rate makes a bird the leading explanation of the conclusion, labelled Beats like a bird (2026-10-12), with the alternatives named "
          "(Jacob, Galileo flyer 2, 2026-10-07)", head[:100])
    flock = report.Case("t", "/tmp/x.mp4")                 # a group whose members beat, each its own: PR135's six (2026-10-08)
    members = {f"member {i}": dict(hz=hz, double_hz=None, first=1240, last=1392, amplitude=0.2, stands=100.0)
               for i, hz in enumerate((7.85, 7.38, 8.02, 7.10, 7.66, 7.61), 1)}
    report.Found("flicker", {"finding": "members over the same frames beat at different frequencies or out of step"},
                 fields=dict(beats=True, beat=members, finding="members over the same frames beat at different frequencies or out of step")).into(flock)
    label, head = flock.conclusion()
    rows = {r[0]: (r[2], r[3]) for r in flock.summary()}
    check(label == "Beats like a bird" and head.startswith("A flock of birds is the leading explanation: its 6 members each beat at 7.1–8.0 Hz")
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
          and head.endswith("would beat too; 3 more were seen too briefly to tell).") and part.conclusion()[0] == "Beats like a bird",
          "a member beating outside the wingbeat band is counted among the members, not the flock; members too brief for a beat "
          "(under 60 frames: PR135's after the group's jump) are said", head[-80:])
    held = report.Case("t", "/tmp/x.mp4")                  # a member whose own beat did not pass the tests (2026-10-09)
    six = {n: dict(b, hz=7.5) if n == "member 6" else b for n, b in members.items()}
    report.Found("flicker", {"finding": "members over the same frames beat at different frequencies or out of step"},
                 fields=dict(beats=True, beat=six, strong=[f"member {i}" for i in range(1, 6)],
                             finding="members over the same frames beat at different frequencies or out of step")).into(held)
    label, head = held.conclusion()
    rows = {r[0]: (r[2], r[3]) for r in held.summary()}
    check(head.startswith("A flock of birds is the leading explanation: 5 of its 6 members each beat at 7.1–8.0 Hz")
          and rows["brightness beat"][0] == "5 of 6 members: 7.1–8.0 Hz" and "5 of its 6 members beat at" in held.bottom_line(),
          "a member whose beat did not pass the stage's tests (`strong`) is not counted among those that beat, in the "
          "conclusion, the summary or the bottom line, though its strongest is at a wingbeat's rate", head[:100])
    check("beats at 3.9 Hz (and at 7.9 Hz, its double): the object's own, not the video's" in c.bottom_line(),
          "the bottom line says it", c.bottom_line()[:120])
    # the headline rule (Jacob, 2026-10-17): a bird is named only from a beat that comes back -- the whole track beats, or
    # two windows apart agree (flicker's `comes_back`); a case from before has no mark, and its beats came back
    one = dict(hz=7.1, double_hz=None, first=300, last=359, amplitude=0.08, stands=60.0, resolution_hz=0.5,
               source="the clearest of 2 windows of 2 s that beat, of 40", windows_passing=2, windows=40)

    def beating(**marks):
        k = report.Case("t", "/tmp/x.mp4")
        report.Found("flicker", {"finding": "it beats at 7.1 Hz"},
                     fields=dict(beats=True, beat={"object": dict(one, **marks)}, finding="it beats at 7.1 Hz")).into(k)
        return k
    once = beating(whole_passes=False, windows_apart=1, comes_back=False)
    label, head = once.conclusion()
    rows = {r[0]: (r[2], r[3]) for r in once.summary()}
    check(label != report.BIRD and "bird is the leading" not in head and "for one stretch, frames 300–359" in head
          and "too little to name a bird" in head and "One stretch only" in rows["brightness beat"][1]
          and "beats at 7.1 Hz for one stretch, frames 300–359: the object's own" in once.bottom_line(),
          "a beat in one stretch names no bird: the conclusion, the summary and the bottom line say it is one stretch", head[:110])
    check(beating(whole_passes=False, windows_apart=2, comes_back=True).conclusion()[0] == report.BIRD
          and beating(whole_passes=True, windows_apart=0, comes_back=True).conclusion()[0] == report.BIRD
          and beating().conclusion()[0] == report.BIRD,
          "two windows apart that agree, or the whole track, name a bird -- and so does a case from before the rule, with no mark")
    # the floor (2026-10-24): a beat that comes back at a wingbeat's rate names a bird only at BIRD_FLOOR of the brightness
    # or more -- false calls on known aircraft, drones and helicopters beat at 1.6-7.8 % (the Svanstrom set); a case from
    # before, with no amplitude, is judged as it was
    faint = beating(comes_back=True, amplitude=0.05)
    label, head = faint.conclusion()
    check(label != report.BIRD and "bird is the leading" not in head and "beats at 7.1 Hz" in head and "by only 5.0 %" in head
          and "too faint to name a bird" in head,
          "a beat that comes back at a wingbeat's rate but by only 5 % names no bird, and the headline says why", head[:150])
    check(beating(comes_back=True, amplitude=0.09).conclusion()[0] == report.BIRD
          and beating(comes_back=True, amplitude=None).conclusion()[0] == report.BIRD,
          "at 9 % it names a bird, and so does a case from before the floor, with no amplitude")
    soft = {f"member {i}": dict(one, hz=hz, comes_back=True, amplitude=0.04) for i, hz in enumerate((7.8, 7.4, 7.1), 1)}
    quiet = report.Case("t", "/tmp/x.mp4")
    report.Found("flicker", {"finding": "members over the same frames beat at different frequencies"},
                 fields=dict(beats=True, beat=soft, finding="members over the same frames beat at different frequencies")).into(quiet)
    check(quiet.conclusion()[0] != report.BIRD and "flock" not in quiet.conclusion()[1],
          "members that each beat by 4 % make no flock", quiet.conclusion()[1][:120])
    # a rotor's look (flicker's item 14, 2026-10-25): said beside the headline, and the label left as it was
    rot = beating(comes_back=True, amplitude=0.12, rotor=dict(coherence=0.81, background="background +25,+0", offset_px=1.2,
                                                                marked=["background"]))
    line = rot.bottom_line()
    check(rot.conclusion()[0] == report.BIRD and "reaches the background beside it in step (coherence 0.81 with background +25,+0)" in line
          and "as a helicopter's rotor does" in line and "not a test" in line,
          "a beat that reaches the background beside it in step is said to look like a rotor's, and the bird is still named",
          line[-220:])
    off = beating(comes_back=True, amplitude=0.12, rotor=dict(coherence=0.3, background="background +0,+25", offset_px=4.4,
                                                                marked=["off its middle"]))
    check("sits 4.4 px off its middle" in off.bottom_line() and "rotor" not in beating(comes_back=True, amplitude=0.12,
          rotor=dict(coherence=0.3, background="background +0,+25", offset_px=1.0, marked=[])).bottom_line(),
          "the light that beats sitting off its middle is said too; a beat with neither says nothing of a rotor")
    three = {f"member {i}": dict(one, hz=hz, comes_back=back) for i, (hz, back) in enumerate(((7.8, True), (7.4, False), (7.1, True)), 1)}
    group = report.Case("t", "/tmp/x.mp4")
    report.Found("flicker", {"finding": "members over the same frames beat at different frequencies"},
                 fields=dict(beats=True, beat=three, finding="members over the same frames beat at different frequencies")).into(group)
    label, head = group.conclusion()
    check(label == report.BIRD and head.startswith("A flock of birds is the leading explanation: 2 of its 3 members each beat at 7.1–7.8 Hz"),
          "of a group, only the members whose beats come back make the flock", head[:100])
    d = report.Case("t", "/tmp/x.mp4")
    report.Found("flicker", {}, fields=dict(beats=False, beat={}, finding="no beat reaches 3 times what the background beside it does"),
                 no_power=[("flicker", "no beat reaches 3 times what the background beside it does")]).into(d)
    rows = {r[0]: (r[2], r[3]) for r in d.summary()}
    check(rows.get("brightness beat", ("x",))[0] is None and "no beat reaches" in rows["brightness beat"][1] and "beats at" not in d.bottom_line(),
          "with none found, the row says why and the bottom line says nothing of it", str(rows.get("brightness beat"))[:100])


def test_a_speed_on_the_screen_is_no_physical_conclusion_whatever_is_beside_it():
    """Jacob, 2026-10-21, exercise 2 (PR149): before the ship was given, the report said "Tentative conclusion" with
    604 pixels a second and nothing else conclusive. A second piece of the headline -- "something moves with it" --
    had taken it past the rule, which looked for the pixel rate alone; integrity's "it behaves like imagery from this
    sensor chain" did the same to PR113, PR144 and PR43's reference cases. With a pixel rate and no m/s, and no bird,
    the label is "No physical conclusion" whatever else is said; the rest is still said."""
    print("\nreport: a speed on the screen is no physical conclusion, whatever is beside it")
    from mcdonald.stages import SHEET_PROVISIONAL
    one = dict(hz=7.1, double_hz=None, first=300, last=359, amplitude=0.08, stands=60.0, resolution_hz=0.5)

    def case(*beside, **kin):
        c = report.Case("t", "/tmp/x.mp4")
        c.notes.append(SHEET_PROVISIONAL)
        report.Found("kinematics", {"v_px": "604 px/s"}, fields=dict(v_px_per_s=604.0, **kin)).into(c)
        if "companion" in beside or "pendulum" in beside:
            report.Found("tether", {"companion": "yes"}, fields=dict(companion=True, swing=dict(swings="pendulum" in beside))).into(c)
        if "imagery" in beside:
            report.Found("integrity", {"object_verdicts": {"ela": "PASS", "noise": "PASS"}}).into(c)
        if "flagged" in beside:
            report.Found("integrity", {"object_verdicts": {"ela": "FLAG", "noise": "PASS"}}).into(c)
        for name, b in (("stretch", dict(one, comes_back=False)), ("slow", dict(one, hz=1.2)), ("bird", one)):
            if name in beside:
                report.Found("flicker", {"finding": "it beats"}, fields=dict(beats=True, beat={"object": b}, finding="it beats")).into(c)
        return c.conclusion()
    for beside, said in ((("pendulum",), "something moves with it, swinging like a pendulum"),
                         (("imagery",), "behaves like imagery from this sensor chain"),
                         (("flagged",), "1 integrity test flag it (ela)"), (("stretch",), "for one stretch, frames 300–359"),
                         (("slow",), "beats at 1.2 Hz, a rhythm of its own"), (("companion", "imagery"), "behaves like imagery")):
        label, head = case(*beside)
        check(label == "No physical conclusion" and "about 604 pixels a second" in head and said in head,
              f"pixels a second and {' and '.join(beside)}: no physical conclusion, and the rest still said", f"{label}: {head[:110]}")
    label, head = case("companion", scale_bar_m_per_s=115.0)
    check(label == report.SUBSONIC and "at most about 115 m/s across the line of sight" in head,
          "with a thing of known size it is subsonic motion, the speed under the speed of sound (the exercise's second report)",
          f"{label}: {head[:110]}")
    check(case("companion", "bird")[0] == report.BIRD and case()[0] == "No physical conclusion",
          "a bird is named with pixels a second, as before; pixels a second alone is no physical conclusion, as before")


def test_a_field_of_view_without_a_range_is_indeterminate():
    """Jacob, 2026-10-22, exercise 3 (PR113): "When I enter the FOV, I'd like this to change to 'Indeterminite, range
    needed' and then the text below should list the different ranges that correspond to a Bird, Balloon, and Fighter
    Jet. This gives a sense of what is learned by obtaining FOV". A scale (a field of view, or angle marks) and no
    distance: the turn rate and the size in the picture, then where each would be (`figures.BIRDS`, `OBJECTS`) and its
    speed across the line of sight there, at least. A point no wider than the blur puts each at least that far; with no
    size in the picture, the speed at 100 m and 1 km. A bird is named first; a distance or a ruler takes it past."""
    print("\nreport: a field of view without a range is indeterminate, with a bird, a balloon and a jet placed")
    one = dict(hz=7.1, double_hz=None, first=300, last=359, amplitude=0.08, stands=60.0, resolution_hz=0.5)

    def case(p=21.0, resolved=None, bird=False, **kin):
        c = report.Case("t", "/tmp/x.mp4")
        c.add("track", {"frames": 4}, fields=dict(frames=4, **({"object_size_px": p} if p else {})))
        report.Found("scale", {"k": "1884 px/rad"}, fields=dict(k_px_per_rad=1884.0, fov_deg=54.0)).into(c)
        report.Found("kinematics", {"v_px": "4269 px/s"}, fields=dict(
            v_px_per_s=4269.0, omega_rad_per_s=4269.0 / 1884.0, resolution=None if resolved is None else dict(resolved=resolved),
            **kin)).into(c)
        if bird:
            report.Found("flicker", {"finding": "it beats"}, fields=dict(beats=True, beat={"object": one}, finding="it beats")).into(c)
        return c
    c = case()
    label, head = c.conclusion()
    check(label == report.INDETERMINATE and label == "Indeterminate, range needed"
          and head == ("The object moved about 130° a second in the image and is 21 pixels across (0.64°); what it is depends on "
                       "how far away it is: as a bird (0.2–2 m) it would be 18–180 m away and moving at least 41–410 m/s across the "
                       "line of sight; as a weather balloon (2 m), 180 m away and 410 m/s; as a fighter jet (17 m), 1.5 km away and "
                       "3,500 m/s.")
          and "at least 2.27 R m/s across the line of sight, relative to the camera's platform, and is 21/1884 R m across" in c.bottom_line(),
          "PR113 at 54 degrees: indeterminate, a range needed, and where a bird, a balloon and a jet would be", head[:120])
    label, head = case(resolved=False).conclusion()
    check("is no wider than a point here, 21 pixels (0.64°)" in head and "at least 18–180 m away" in head
          and "as a fighter jet (17 m), at least 1.5 km away" in head, "a point no wider than the blur: each at least that far",
          head[:120])
    label, head = case(p=None).conclusion()
    check(label == report.INDETERMINATE and "at 100 m away that is at least 230 m/s across the line of sight, at 1 km 2,300 m/s" in head,
          "no size in the picture: the speed at 100 m and at 1 km", head[:120])
    check(case(bird=True).conclusion()[0] == report.BIRD and "as a weather balloon" in case(bird=True).conclusion()[1]
          and case(scale_bar_m_per_s=115.0).conclusion()[0] == report.SUBSONIC
          and case(range_m=3000.0, relative_speed_m_per_s=6798.0, lower_bound_m_per_s=6798.0).conclusion()[0] == report.SUPERSONIC,
          "a bird is named first; a ruler or a distance takes it past")


def test_a_field_of_view_and_a_range_give_the_least_speed():
    """Jacob, 2026-10-22: "it is worth thinking about how the headline conclusion should change if both FOV and range are
    provided", and of the proposal, "those look good to me". A field of view and a distance give omega R, the speed
    across the line of sight -- the least the speed relative to the platform can be, which the headline had called the
    speed. Past the speed of sound: "Supersonic motion" whatever the angle. Under it with no angle: "Indeterminate, angle
    needed". With an angle (theta, or a range rate): the speed itself, "Subsonic motion" or "Supersonic motion". The
    sentence gives its size at that distance and the kind it is near in size. Held in view by the camera: no speed."""
    print("\nreport: a field of view and a range give the least speed, and the label follows it")
    import math as m

    def case(R, theta=None, held=False, omega=4269.0 / 1884.0):
        c = report.Case("t", "/tmp/x.mp4")
        c.add("track", {"frames": 4}, fields=dict(frames=4, object_size_px=21.0))
        report.Found("scale", {"k": "1884 px/rad"}, fields=dict(k_px_per_rad=1884.0, fov_deg=54.0)).into(c)
        full = omega * R / m.sin(m.radians(90.0 if theta is None else theta))
        report.Found("kinematics", {"v_px": "4269 px/s"}, fields=dict(
            v_px_per_s=4269.0, omega_rad_per_s=omega, range_m=R, theta_deg=theta, relative_speed_m_per_s=full,
            lower_bound_m_per_s=omega * R, fit=dict(held=held))).into(c)
        return c
    c = case(3000.0)
    label, head = c.conclusion()
    check(label == report.SUPERSONIC and head == ("At the given distance of 3 km, it is about 33 m across, about a fighter jet's "
                                                 "size, and moving at least 6,800 m/s across the line of sight, relative to the "
                                                 "camera's platform (Mach 20).")
          and "the least its speed relative to the platform can be" in c.bottom_line()
          and "two aircraft meeting head-on can pass it between them" in c.bottom_line(),
          "PR113 at 54 degrees and 3 km: even the least speed is past the speed of sound -- supersonic, relative", head[:110])
    label, head = case(100.0).conclusion()
    check(label == report.ANGLE_NEEDED and label == "Indeterminate, angle needed" and "about 1.1 m across, about a bird's or a "
          "weather balloon's size, and moving at least 230 m/s across the line of sight" in head and "(Mach 0.66)" in head
          and "head-on" not in case(100.0).bottom_line(),
          "at 100 m the least speed is under it, and with no angle nothing settles it: an angle is needed", f"{label}: {head[:110]}")
    for theta, want in ((60.0, report.SUBSONIC), (30.0, report.SUPERSONIC)):
        label, head = case(100.0, theta).conclusion()
        check(label == want and f"moving at {theta:.0f}° to the line of sight" in head and "relative to the camera's platform" in head
              and "at least" not in head, f"with an angle of {theta:.0f} degrees the speed itself: {want}", f"{label}: {head[:120]}")
    label, head = case(100.0, held=True).conclusion()
    check(label == "Conclusion" and head.endswith("the camera kept it in view, so its speed is not measured here.")
          and "m/s" not in head, "held in view by the camera: its size at that distance, and no speed", head[-90:])
    hand = report.Case("t", "/tmp/x.mp4")                   # put together by hand, with only a speed: as before
    report.Found("kinematics", {"speed_m_s": "250 m/s"}).into(hand)
    check(hand.conclusion() == ("Conclusion", "The object moved about 250 m/s relative to the camera's platform, with the stated "
                                              "range and scale."), "a case with only a speed is read as before", hand.conclusion()[1])


def test_something_that_only_moves_with_it_is_not_in_the_headline():
    """Jacob, 2026-10-22, exercise 2 (PR149): its headline ended "something moves with it" -- a faint dark spot 17
    object sizes behind the object, found at the stage's least strength, on a quarter of single frames -- and he asked:
    "leave it out of the headline, it is confusing". It is said in the bottom line, with how far away and at what
    angle; a companion that swings like a pendulum is a finding (the tether stage's reason to be), and stays."""
    print("\nreport: something that only moves with the object is the bottom line's, not the headline's")
    one = dict(hz=7.1, double_hz=None, first=300, last=359, amplitude=0.08, stands=60.0, resolution_hz=0.5)
    near = dict(sign="dark", r_over_size=16.9, direction_deg=108.9)

    def case(swings, rate=True, bird=False, bar=None):
        c = report.Case("t", "/tmp/x.mp4")
        if rate:
            report.Found("kinematics", {"v_px": "604 px/s"},
                         fields=dict(v_px_per_s=604.0, **({"scale_bar_m_per_s": bar} if bar else {}))).into(c)
        if bird:
            report.Found("flicker", {"finding": "it beats"}, fields=dict(beats=True, beat={"object": one}, finding="it beats")).into(c)
        report.Found("tether", {"companion": "yes"}, fields=dict(companion=near, swing=dict(
            swings=swings, **(dict(period_used_s=1.9, line_length_m=0.9) if swings else {})))).into(c)
        return c.conclusion(), c.bottom_line()
    for name, kw in (("pixels a second", {}), ("a ship for a ruler", dict(bar=115.0)), ("a bird", dict(bird=True))):
        (label, head), line = case(False, **kw)
        check("moves with it" not in head and "Something moves with it: a dark feature 16.9 object sizes away, +109° from "
              "straight down, at a steady angle (no swing, so no length)." in line,
              f"{name}: not in the headline, and the bottom line says where it is", f"{label}: {head[-80:]}")
    (label, head), line = case(True)
    check(head.endswith("; something moves with it, swinging like a pendulum.") and "a pendulum of 0.90 m" in line,
          "one that swings is in the headline, as a pendulum, and the bottom line has its length", head[-80:])
    (label, head), line = case(False, rate=False)
    check(head == "Something moves with it." and "Something moves with it: a dark feature" in line,
          "and where it is all there is, it is said, not \"nothing was measured\"", f"{label}: {head}")


def test_a_thing_of_known_size_under_the_speed_of_sound_is_subsonic_motion():
    """Jacob, 2026-10-22, exercise 2 (PR149): "Knowing the range ratio provides an upper bound on relative velocity (we
    showed this in the JAIS Technical Note). This means for PR149, after the reference length is taken, we can report
    'Subsonic motion' as the headline". A thing of known size gives the speed across the line of sight at its distance,
    and no more where the object is no farther away; under the speed of sound (kinematics.A_SOUND) the label is
    "Subsonic motion", the bound in its sentence and the bottom line. At or over it the bound says nothing of the kind,
    and the label is what it was. A bird is still named first; an unchecked track sheet is still said, in the report's
    note (and the window's banner), as for a bird."""
    print("\nreport: a thing of known size under the speed of sound is subsonic motion")
    from mcdonald.stages import SHEET_PROVISIONAL
    one = dict(hz=7.1, double_hz=None, first=300, last=359, amplitude=0.08, stands=60.0, resolution_hz=0.5)

    def case(bar, looked=False, bird=False, **kin):
        c = report.Case("t", "/tmp/x.mp4")
        if not looked:
            c.notes.append(SHEET_PROVISIONAL)
        report.Found("kinematics", {"v_px": "604 px/s"}, fields=dict(v_px_per_s=604.0, scale_bar_m_per_s=bar, **kin)).into(c)
        if bird:
            report.Found("flicker", {"finding": "it beats"}, fields=dict(beats=True, beat={"object": one}, finding="it beats")).into(c)
        return c
    for looked in (False, True):
        c = case(115.0, looked)
        label, head = c.conclusion()
        check(label == report.SUBSONIC and "at most about 115 m/s across the line of sight, relative to the camera's platform, if it "
              "is no farther away than the thing of known size: under the speed of sound (Mach 0.34)" in head
              and "no more than Mach 0.34, under the speed of sound" in c.bottom_line()
              and "toward or away from the camera is not measured" in c.bottom_line()
              and (f"> {SHEET_PROVISIONAL}" in c.markdown()) is not looked,
              "115 m/s at the ship's distance: subsonic motion, the bound said, " + ("the sheet looked at" if looked else
                                                                                      "and the unchecked sheet still said"),
              f"{label}: {head[:110]}")
    for looked, was in ((False, "Tentative conclusion"), (True, "Conclusion")):
        label, head = case(400.0, looked).conclusion()
        check(label == was and "at most about 400 m/s" in head and "(Mach 1.17)" in head and "under the speed of sound" not in head
              and "upper bound" not in case(400.0, looked).bottom_line(),
              f"400 m/s at the ship's distance bounds nothing under the speed of sound: {was}, as before", f"{label}: {head[:110]}")
    label, head = case(115.0, range_ratio=2.0).conclusion()
    check(label == report.SUBSONIC and "at 2 times the distance of the thing of known size (as given): under the speed of sound" in head,
          "with a range ratio given, the speed at that ratio, under the speed of sound", head[:110])
    check(case(115.0, bird=True).conclusion()[0] == report.BIRD and case(342.9).conclusion()[0] == report.SUBSONIC
          and case(343.0).conclusion()[0] == "Tentative conclusion",
          "a bird is named first; the line is the speed of sound itself, 343 m/s")
    label, head = case(115.0, relative_speed_m_per_s=500.0).conclusion()
    check(label == "Tentative conclusion" and "500 m/s relative to the camera's platform" in head,
          "a relative speed from the range and the field of view is the headline's, and not a bound", f"{label}: {head[:90]}")


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
    check(label == report.INDETERMINATE and head.startswith("The object moved about 120° a second in the image and is 21 pixels "
                                                            "across (0.59°); what it is depends on how far away it is: as a bird")
          and "as a weather balloon (2 m), 190 m away and 400 m/s; as a fighter jet (17 m), 1.6 km away and 3,400 m/s." in head
          and f"**{label}.** {head}" in md[:md.index("## Summary of variables")]
          and "at least 2.09 R m/s across the line of sight" in c.bottom_line(),
          "the conclusion comes first: with the angle marks and no range, where a bird, a balloon and a jet would be (Jacob, "
          "2026-10-22; the Technical Note's ~37 m craft at 3 km is the same line)", f"{label}: {head[:90]}")
    import tempfile
    from mcdonald import figures
    with tempfile.TemporaryDirectory() as td:
        c.figures = figures.report_figures(c, clip, track, f"{td}/pr113")
        md = c.markdown()
        check(len(c.figures) == 3 and all(Path(f).exists() for f in c.figures)
              and md.index("## Missing quantities") < md.index("## Figures") < md.index("## Measurements")
              and "pr113_track_frame.png" in md and "pr113_size_speed.png" in md and "pr113_admissible.png" in md,
              "the three figures (a frame with the path; size and speed against range; the admissible region, since k is known) "
              "are drawn, after Missing quantities", ", ".join(Path(f).name for f in c.figures))


def test_the_four_unknowns_say_where_each_stands():
    """ROADMAP 0.4, objective 6: every report says, for k, R, theta and v_own, whether it is constrained, assumed,
    bounded or missing, by which route, and which released datum would close it -- and a stage that needs no `run`
    (horizon, haze, focus, slew) reaches a case through --case, its bound then in the table."""
    print("\nreport: the four unknowns")
    import json as js
    import tempfile
    import numpy as np
    from mcdonald import stages

    class Clip:
        W, H, fps, n0, n1 = 1920, 1080, 30.0, 408, 411

        def rgb(self, n):
            return np.zeros((self.H, self.W, 3), np.float32)
    led = lambda c: {r["symbol"]: r for r in c.ledger()}
    empty = report.Case("t", "/tmp/x.mp4")
    e = led(empty)
    check(list(e) == ["k", "R", "θ", "v_own"] and all(r["status"] == "missing" and r["closes"] for r in e.values())
          and "FVW / SLR" in e["k"]["closes"] and "range rate" in e["θ"]["closes"],
          "a case with nothing: all four missing, each with the datum that would close it", str([r["status"] for r in e.values()]))
    known = report.Case("pr113", "/tmp/x.mp4")
    stages.scale(Clip(), graticule=35.4).into(known)
    report.Found("kinematics", {}, fields=dict(range_m=5000.0, theta_deg=60.0, parallax=dict(v_own=120.0))).into(known)
    g = led(known)
    check(all(r["status"] == "constrained" and r["closes"] is None for r in g.values()) and g["k"]["value"] == "35.4 px/deg"
          and "graticule" in g["k"]["by"] and g["R"]["value"] == "5,000 m" and g["v_own"]["value"] == "120 m/s",
          "a graticule and a given range, angle and platform speed: all four constrained, nothing to close",
          "; ".join(f"{s}: {r['value']} ({r['by']})" for s, r in g.items()))
    guess = report.Case("t", "/tmp/x.mp4")
    stages.scale(Clip(), fov=40.0).into(guess)
    check(led(guess)["k"]["status"] == "assumed" and led(guess)["k"]["closes"],
          "a field of view given with no source is assumed, as scale says, and still names what would close it",
          led(guess)["k"]["by"][:60])
    bounded = report.Case("t", "/tmp/x.mp4")
    report.Found("slew", {}, fields=dict(c_px_per_deg=None, c_at_least_px_per_deg=1087.0, floor_stands=True)).into(bounded)
    report.Found("horizon", {}, fields=dict(bounds=dict(range_max_m=57000.0))).into(bounded)
    report.Found("focus", {}, fields=dict(bound=dict(floor_m=2500.0))).into(bounded)
    b = led(bounded)
    check(b["k"]["status"] == "bounded" and b["k"]["value"] == "at least 1087 px/deg" and "slew" in b["k"]["by"]
          and b["R"]["status"] == "bounded" and b["R"]["value"].startswith("at most 57 km, by the horizon")
          and "at least 2.5 km, by sharp as a point" in b["R"]["value"] and b["θ"]["status"] == "missing",
          "slew's standing floor bounds k; the horizon's ceiling and focus's floor bound R, each by its route",
          f"{b['k']['value']}; {b['R']['value']}")
    loose = report.Case("t", "/tmp/x.mp4")
    report.Found("slew", {}, fields=dict(c_px_per_deg=None, c_at_least_px_per_deg=1087.0, floor_stands=False)).into(loose)
    check(led(loose)["k"]["status"] == "missing", "a floor that does not stand (no window of the clip registered a slew) is no bound")
    # a reference of known length is a range of its own, L k / l: with the range ratio given, the object's range
    yard = {}
    for name, scl, kin_f in (("ratio, fov", dict(fov=40.0), dict(range_ratio=2.0, size_px=30.0)),
                             ("ratio, graticule", dict(graticule=35.4), dict(range_ratio=2.0)),
                             ("no ratio", dict(fov=40.0), {}), ("no k", {}, dict(range_ratio=2.0))):
        c = report.Case("t", "/tmp/x.mp4")
        stages.scale(Clip(), ref_px=920.0, ref_m=180.0, **scl).into(c)
        report.Found("kinematics", {}, fields=kin_f).into(c)
        yard[name] = c
    k40 = yard["ratio, fov"].stages["scale"]["fields"]["k_px_per_rad"]
    R = 2.0 * 180.0 * k40 / 920.0
    r, rows = led(yard["ratio, fov"])["R"], {n: (v, h) for n, _, v, h in yard["ratio, fov"].summary()}
    check(r["status"] == "assumed" and r["value"] == f"{R:,.0f} m" and "L k / l" in r["by"] and "2 times as far" in r["by"]
          and rows["range"][0] == f"{R:,.0f} m" and yard["ratio, fov"].range_bounds() == (R, R, True)
          and rows["object size"][0] == f"{30.0 * 2.0 * 180.0 / 920.0:.1f} m" and "k cancels" in rows["object size"][1],
          "a reference of known length, the range ratio and k give the range (as assumed as k is), in the ledger, the summary "
          "and the admissible region's bounds; the size needs no k", f"{r['value']} ({r['status']}); {rows['object size'][0]}")
    check(led(yard["ratio, graticule"])["R"]["status"] == "constrained" and led(yard["ratio, graticule"])["R"]["closes"] is None,
          "with a measured k the range from the ratio is constrained", led(yard["ratio, graticule"])["R"]["value"] or "")
    check(led(yard["no ratio"])["R"]["status"] == "missing" and "the reference of known length is at" in led(yard["no ratio"])["R"]["by"]
          and "not given" in led(yard["no ratio"])["R"]["by"] and led(yard["no k"])["R"]["status"] == "missing"
          and "with k" in led(yard["no k"])["R"]["by"] and "k cancels" in led(yard["no k"])["k"]["by"]
          and "reference" not in e["k"]["by"],
          "without the ratio, or without k, the range stays missing, and the row says what the reference would give; k's row "
          "says the reference gives the speed without it (it gives no k)",
          f"{led(yard['no ratio'])['R']['by']} / {led(yard['no k'])['R']['by']}")
    with tempfile.TemporaryDirectory() as td:
        empty.write(f"{td}/t")
        md = report.into_case(report.Found("haze", {"range": "at most 8 km"}, fields=dict(bound_m=8000.0, factor=4.0)),
                              f"{td}/t_case.json", "mcdonald haze x.mp4 --track t.csv --visibility 20km")
        back = report.Case.load(f"{td}/t_case.json")
        text = Path(md).read_text(encoding="utf-8")
        saved = js.loads(Path(f"{td}/t_case.json").read_text(encoding="utf-8"))
        check(led(back)["R"]["status"] == "bounded" and led(back)["R"]["value"] == "at most 8 km"
              and "factor of about 4" in led(back)["R"]["by"] and "mcdonald haze x.mp4" in back.commands[-1]
              and text.index("## Summary of variables") < text.index("## The four unknowns") < text.index("## Missing quantities")
              and [r["symbol"] for r in saved["ledger"]] == ["k", "R", "θ", "v_own"],
              "--case records a stage run on its own in the case: its bound in the table (after the summary), its command "
              "in the record, the table in the JSON too", led(back)["R"]["value"] or "")


# ---------------------------------------------------------------- report
def test_the_report_names_the_segment_and_its_figure_needs_no_k():
    """A tester on a Mac, 2026-10-18 and 19, on PR44 opened at 30-56 s: the report did not say the segment chosen (it named
    only the frames measured, the part round the object's track); the size-and-speed figure showed where a weather
    balloon and a fighter jet would sit but not a bird, where the report named a bird; and its axes carried an
    equation with k in it ("People may not know what 'k' is and they dont have to I think. The different FOV
    lines are fine")."""
    print("\nreport: the segment chosen, and the figure in plain words with the birds on it")
    import re
    import tempfile
    from matplotlib.text import Text
    from mcdonald import figures
    c = report.Case("dow-uap-pr44", "/tmp/DOD_111689115.mp4")
    c.clip = dict(width=1920, height=1080, fps=30.0, fps_exact="30", n0=1012, n1=1351)
    c.segment = [901, 1681]
    md = c.markdown()
    top = md[:md.index("## Conclusion")]
    check("**Segment:** 0:30.00 to 0:56.00 of the video, 26.0 s (frames 901–1681). Measured over 0:33.70 to 0:45.00 "
          "(frames 1012–1351), the part of it round the object's track." in top and "1920x1080" in top,
          "the segment chosen is said at the top, in the video's time as the segment step shows it, and the frames "
          "measured where they are fewer", top.split("\n")[2][:120])
    with tempfile.TemporaryDirectory() as td:
        c.write(f"{td}/pr44")
        back = report.Case.load(f"{td}/pr44_case.json")
    check(back.segment == [901, 1681] and back.markdown() == md, "the case file keeps it, and the report read back says it again")
    old = report.Case("dow-uap-pr44", "/tmp/DOD_111689115.mp4")
    old.clip = dict(c.clip)
    said = old.markdown().split("\n")[2]
    check(said == "**Segment:** 0:33.70 to 0:45.00 of the video, 11.3 s (frames 1012–1351).",
          "a case from before the segment was kept says the frames it has, as a segment", said)

    texts = {}

    def kept(fig, path, **kw):                    # the figure's words, instead of a file
        texts[Path(path).stem] = " | ".join(t.get_text() for t in fig.findobj(Text) if t.get_text())
    real, figures.save = figures.save, kept
    try:
        figures.size_speed(300.0, 6.0, 1920, "unknown.png", bird=True)
        figures.size_speed(300.0, 6.0, 1920, "plain.png")
        k = 960 / math.tan(math.radians(2.5) / 2)
        figures.size_speed(300.0, 6.0, 1920, "given.png", k=k, k_from="an ASSUMED field of view of 2.5 deg", fov=2.5,
                           R_known=3000)
        figures.size_speed(300.0, None, 1920, "speed.png")
    finally:
        figures.save = real
    every = " | ".join(texts.values())
    check(not re.search(r"\bk\b|ωR|S = p", every) and "size  [m]" in texts["unknown"]
          and "speed across the line of sight  [m/s]" in texts["unknown"] and "distance to the object" in texts["unknown"]
          and "speed across the line of sight  [m/s]" in texts["speed"],
          "its axes are named in words: no k, no equation", every[:160])
    check("birds, ~0.2–2 m  (it beats like a bird)" in texts["unknown"] and "birds, ~0.2–2 m" in texts["plain"]
          and "(it beats like a bird)" not in texts["plain"] and "weather balloon, ~2 m" in texts["plain"]
          and "fighter jet, ~17 m" in texts["plain"],
          "the band a bird's size would sit in is drawn with the weather balloon and the fighter jet, and said as the "
          "case's own where its brightness beats like a bird's")
    check("FOV 0.7°" in texts["plain"] and "FOV 3°" in texts["plain"] and "FOV 10°" in texts["plain"]
          and "FOV 30°" in texts["plain"] and "The field of view is not known" in texts["plain"]
          and "FOV 2.5°" in texts["given"] and "Field of view 2.5°, as given" in texts["given"]
          and "3,000 m away (given)" in texts["given"],
          "a line for each of four fields of view where none is known, a targeting pod's 0.7° among them, and the one "
          "given where it is", texts["given"][:120])


def test_a_report_from_an_older_version_says_what_its_card_says():
    """A tester on a Mac, 2026-10-18, on PR44: the cards said "A bird is the leading explanation", and the full report "doesn't say
    bird at all". Most likely the report was written by a version before 0.2.14, which named no bird, and the cards read
    its case's beat by a later version's rules (the same segment measured again on 0.2.20 finds no beat). The report's
    page writes the report again from its case file where this version words it otherwise, and the report and the card
    say which version measured it."""
    print("\nreport: a report from an older version, written again to say what its card says")
    import json
    import tempfile
    c = report.Case("t", "/tmp/x.mp4")
    c.clip = dict(width=640, height=512, fps=60.0, fps_exact="60", n0=369, n1=721)
    beat = dict(hz=3.94, double_hz=None, first=602, last=721, amplitude=0.097, stands=399.0, resolution_hz=0.5)
    report.Found("flicker", {"object": "3.94 Hz, 9.7%, 399x the band, frames 602–721"},
                 fields=dict(beats=True, beat={"object": beat}, finding="it beats at 3.94 Hz")).into(c)
    with tempfile.TemporaryDirectory() as td:
        md = Path(c.write(f"{td}/t"))
        js = Path(f"{td}/t_case.json")
        check(not report.written_again(md) and c.older() is None and "Measured with" not in md.read_text(encoding="utf-8"),
              "a report written by this version is left as it is, and says nothing of versions")
        d = json.loads(js.read_text(encoding="utf-8"))
        d.pop("measured_by")
        d.pop("segment")
        d["mcdonald"] = "0.2.12"                      # as a version from before the bird was named wrote it
        js.write_text(json.dumps(d), encoding="utf-8")
        md.write_text("# T: case report\n\n## Conclusion\n\n**Conclusion.** Its brightness beats at 3.9 Hz.\n", encoding="utf-8")
        old = report.Case.load(js)
        check(old.older() == "0.2.12" and old.conclusion()[0] == report.BIRD and "Measured with mcdonald 0.2.12" in old.older_said(),
              "read by this version, the old case's beat is a bird's -- its card says so -- and the case knows which version "
              "measured it", old.older_said()[:80])
        again = report.written_again(md)
        text = md.read_text(encoding="utf-8")
        check(again and f"**{report.BIRD}.** A bird is the leading explanation" in text
              and "> Measured with mcdonald 0.2.12, and read with" in text and text.index("Measured with") < text.index("## Conclusion")
              and not report.written_again(md),
              "the report's page writes it again from the case file, so that the page says what the card says, with which "
              "version measured it above the conclusion; once written, it is left alone",
              next((ln for ln in text.splitlines() if ln.startswith("> Measured")), "")[:90])


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
        check(label == "Beats like a bird" and head.startswith("A bird is the leading explanation: its brightness beats at 7.4 Hz"),
              "and its report leads with the bird, as a thing alone would", head[:80])
        g = flicker.of_member(gf, "member 3", "object-1")
        check(g.fields["beats"] is None and g.no_power == [("flicker", "seen on 40 frames, under the 60 a beat needs")],
              "a member too brief for a beat says so, with no power")
        weak = flicker.of_member(dict(gf, strong=["member 1"]), "member 2", "object-1", tr2)
        check(weak.fields["beats"] is None and "nothing past the background beside it and its own slow change" in weak.fields["finding"],
              "a member whose own beat did not pass the group's tests (not `strong`: under the background's, or no more than its "
              "drift) has none, though it is out of step with a fellow (2026-10-09)", weak.fields["finding"][:90])
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


def test_a_thing_followed_twice_is_counted_once():
    """Jacob, 2026-10-21, exercise 4 (PR135 looked for as six): the list said "7 were followed ... 1 more than you looked
    for", and the seventh, Find's third row, had been followed onto the second group's path -- on its pixels on 36 of its
    67 frames. Two tracks within 2 px on 10 frames or more, and on half or more of the frames both were followed on, are on
    one thing (`several.same_things`), and the later is counted through the earlier: on the list's first line, its row,
    and the count that decides whether a group is split. A group and its own member are not compared; a neighbour 8 px
    away, and a track that crosses another for 5 frames, are things of their own."""
    print("\nseveral objects: a thing followed twice is counted once")
    import csv
    import json as _json
    import tempfile
    from mcdonald import several, mark
    P = {n: (100.0 + 3.0 * n, 300.0 - 1.0 * n) for n in range(1, 151)}          # one bird's path

    def put(base, k, track, group=None):
        d = base / f"object-{k}"
        d.mkdir(parents=True)
        ms = mark.MarkSet("t", "/tmp/t.mp4", 30.0)
        for n in (min(track), max(track)):
            ms.add("object", n, *track[n], how=f"proposed: {k} of 5 things found")
        ms.save(d / "t_marks.json")
        with open(d / "t_autotrack.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["frame", "t_s", "x_px", "y_px", "source"])
            for n, (x, y) in sorted(track.items()):
                w.writerow([n, n / 30.0, round(x, 2), round(y, 2), "forward"])
        if group:
            (d / f"t{several.GROUP}").write_text(_json.dumps(group), encoding="utf-8")
        case = report.Case("t", "/tmp/t.mp4")
        report.Found("track", dict(frames=len(track)), fields=dict(frames=len(track), first=min(track), last=max(track),
                                                                    object_size_px=5.0, object_is_dark=False)).into(case)
        case.write(str(d / "t"))
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "pieces"
        put(base, 1, {n: P[n] for n in range(1, 101)})                                   # the bird, frames 1-100
        put(base, 2, {n: P[n] if n <= 100 else (P[n][0], P[n][1] + 30) for n in range(60, 151)})   # on it 60-100, then on
        put(base, 3, {n: (x + 8, y) for n, (x, y) in P.items()})                         # a neighbour 8 px away all along
        put(base, 4, {n: (P[n][0] + (0 if 70 <= n < 75 else 40), P[n][1]) for n in range(40, 121)})  # crosses it on 5 frames
        found = several.things(base)
        same = several.same_things(found)
        check(same == {2: dict(same_as=1, on=41, shared=41)},
              "a track on another's pixels on every frame both were followed on (41 of them) is the same thing, followed again; "
              "a neighbour 8 px away and one that crosses for 5 frames are not", str(same))
        d = several.tally(found, 3)
        check(d["followed"] == 3 and d["others"] == 3 and d["same"] == {2: 1}
              and d["sentence"] == "You looked for 3 objects: 3 were followed; object 2 followed the same thing as object 1.",
              "it is not counted: three looked for are three followed, and the list's first line names the one followed twice",
              d["sentence"])
        page, rows = several.index(base, objects=3)
        text = page.read_text(encoding="utf-8")
        listed = _json.loads((base / "t_objects.json").read_text(encoding="utf-8"))
        check(rows[1]["same_as"] == dict(same_as=1, on=41, shared=41) and rows[0]["same_as"] is None
              and "- **the same thing as object 1:** its track is on object 1's, within 2 pixels, on 41 of the 41 frames both "
                  "were followed on, so it is counted once, as object 1" in text
              and listed["tally"]["same"] == {"2": 1} and listed["objects"][1]["same_as"]["same_as"] == 1,
              "its row says so, on the page and in the list's json", text.splitlines()[4][:90])
        # a group, its member on its track by design, and a row on the group's path (PR135's objects 2, 9 and 3)
        flock = Path(td) / "flock"
        put(flock, 1, P)
        put(flock, 2, {n: P[n] for n in range(1, 68)})                                   # Find's weak row, on the group's path
        put(flock, 3, dict(P), group=dict(object=1, member=4))                           # the member the group's track follows
        put(flock, 4, {n: (x + 20, y) for n, (x, y) in P.items()}, group=dict(object=1, member=7))
        found = several.things(flock)
        check(several.same_things(found) == {2: dict(same_as=3, on=67, shared=67)}
              and several.tally(found, 2)["sentence"] == "You looked for 2 objects: 2 were followed, 2 of them the members of "
                                                         "1 group (object 1); object 2 followed the same thing as object 3.",
              "a row on a group's path and its member's is counted through them, named as the member (one point), and the "
              "group's member on the group's track is not a thing followed twice", several.tally(found, 2)["sentence"])
        alone = Path(td) / "alone"                                                        # the group, and the row on its path
        put(alone, 1, P)
        put(alone, 2, {n: P[n] for n in range(1, 68)})
        put(alone, 3, {n: (x + 20, y) for n, (x, y) in P.items()}, group=dict(object=1, member=7))
        check(several.same_things(several.things(alone)) == {2: dict(same_as=1, on=67, shared=67)},
              "on a group's path where no member of it is, the row is named as the group")


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
    and (2026-09-27) where to donate, word for word, so that the two cannot drift apart. Since
    2026-10-20 (mcdonald's own donation form) the form's link is the same in About, both READMEs
    and GitHub's Sponsor button, and since 2026-10-24 the website's Donate button (mkdocs.yml)."""
    print("\nHelp -> About")
    import re
    from mcdonald import actions
    root = Path(__file__).resolve().parent.parent
    readme = (root / "README.md").read_text(encoding="utf-8")
    plain = re.sub(r"\s+", " ", re.sub(r"\*\*|\[([^]]*)\]\([^)]*\)|^> ?", r"\1", readme, flags=re.M))
    for what, text in (("the one sentence", actions.ABOUT), ("the quote", actions.QUOTE[0]), ("who said it", actions.QUOTE[1]),
                       ("the copyright and license", actions.COPYRIGHT), ("where to donate", actions.DONATE[0])):
        check(text in plain, f"About has {what} as the README says it", text[:60])
    for f in ("README.md", "README-technical.md", ".github/FUNDING.yml", "mkdocs.yml"):
        check(actions.DONATE[2] in (root / f).read_text(encoding="utf-8"), f"{f} links the donation form About links", actions.DONATE[2])


def exercise_commands(text):
    """Every `mcdonald` command an exercise page shows: in inline code, and on the lines of its code blocks (from the
    word mcdonald on, so that a line printed as `to take one:  mcdonald mark ...` is the command it prints)."""
    import re
    said = re.findall(r"(?<!`)`(mcdonald [^`]+)`(?!`)", text)
    for block in re.findall(r"^```[a-z]*\n(.*?)^```", text, re.M | re.S):
        said += [line[line.index("mcdonald "):] for line in block.splitlines() if "mcdonald " in line]
    return said


def test_exercises_are_listed_and_their_commands_exist():
    """docs/exercises (Jacob, 2026-10-20): short exercises for testers on the PURSUE videos, each with the steps in the
    window and on the command line and the answer to expect. Every page is in the list on docs/exercises/README.md and
    in the issue form testers send their results with, under the same number and name; and every `mcdonald` command a
    page shows is a command, with options that command has. That the answers are still the tool's is test_golden's
    (--exercises), which needs the videos."""
    print("\nthe exercises")
    import importlib.util
    import re
    import shlex
    from mcdonald import cli, stages
    root = Path(__file__).resolve().parent.parent
    pages = sorted((root / "docs" / "exercises").glob("[0-9][0-9]-*.md"))
    index = (root / "docs" / "exercises" / "README.md").read_text(encoding="utf-8")
    form = (root / ".github" / "ISSUE_TEMPLATE" / "exercise-result.yml").read_text(encoding="utf-8")
    offered = re.findall(r'^\s+- "(\d+)\. (.+)"$', form, re.M)
    check(pages and len(offered) == len(pages), "the issue form offers as many exercises as there are pages",
          f"{len(offered)} offered, {len(pages)} pages")
    known = {k.flag for k in stages.KNOWN}
    for page in pages:
        text = page.read_text(encoding="utf-8")
        m = re.match(r"# Exercise (\d+): (.+)\n", text)
        if not check(m is not None, f"{page.name} starts with its number and name", text[:60]):
            continue
        n, name = m.groups()
        check(page.name.startswith(f"{int(n):02d}-"), f"{page.name}: its file name starts with its number", n)
        check(f"| {n} | [{name}]({page.name}) |" in index, f"{page.name} is listed in docs/exercises/README.md", name)
        check((n, name) in offered, f"{page.name} is offered in the issue form", f"{n}. {name}")
        commands = exercise_commands(text)
        check(any(c.startswith("mcdonald run ") for c in commands), f"{page.name} shows the command line's way too",
              f"{len(commands)} commands")
        for command in commands:
            words = shlex.split(command)
            module = cli.COMMANDS.get(words[1], (None, None))[1]
            if not check(module is not None, f"{page.name}: `mcdonald {words[1]}` is a command", command[:80]):
                continue
            source = Path(importlib.util.find_spec(module).origin).read_text(encoding="utf-8")
            unknown = [w for w in words[2:] if w.startswith("--") and f'"{w}"' not in source and w not in known]
            check(not unknown, f"{page.name}: `mcdonald {words[1]}` has the options it is shown with",
                  ", ".join(unknown) or command[:80])


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


# ---------------------------------------------------------------- a name that is also a folder's
def test_a_folder_named_like_a_video_is_not_the_video():
    """Every command writes to ./<tag>, and on a Mac's or Windows' disk, where case is not told apart, the `pr44`
    folder `mcdonald look PR44` made is also `PR44`: the next command, `mcdonald mark PR44 ...`, was given the folder
    as its video and stopped ("PR44 is not a video ffmpeg can read: Is a directory"), and so did the exercises'
    second step (found 2026-10-21 on Linux, where the folder had the name's own case). A folder is never the video:
    the name is looked up in the catalog, and a folder that is no video's name is said to be a folder."""
    print("\nclip: a folder named like a video is not the video")
    import os
    import tempfile
    from mcdonald import catalog, clip
    was, here = catalog.active(), os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        try:
            os.chdir(td)
            catalog.use(catalog.ShippedCatalog())
            fetched = []
            for name, folder in (("PR23", "PR23"), ("pr44", "pr44")):    # the name's own case: what a Mac's disk does for either
                Path(folder).mkdir()
                path, tag, rec = clip.resolve(name, fetch=lambda rec, dest: fetched.append(dest) or dest)
                check(rec is not None and path == Path(rec["path"]) and tag == name.lower() and not path.is_dir(),
                      f"`{name}` beside a folder `{folder}` is the catalog's video, not the folder", f"{path} ({tag})")
            Path("a-folder").mkdir()
            try:
                clip.resolve("a-folder")
                said = "it was taken"
            except clip.Stop as ex:
                said = str(ex)
            check("is a folder, not a video" in said, "a folder that is no video's name is said to be a folder", said)
        finally:
            os.chdir(here)
            catalog.use(was)


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
    print("mcDonald UAP Toolkit — reduction self-check")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{'ALL PASS' if not FAIL else str(len(FAIL)) + ' FAILED: ' + ', '.join(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):           # a pipe or a log file on Windows is cp1252, and the checks' names have arrows
        _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
