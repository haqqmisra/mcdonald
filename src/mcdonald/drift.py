"""Did the object drift with the wind?  Three main tests, a fourth on other evidence, and a tentative verdict.

A balloon, a cloud of debris or a bit of film moves with the air: its speed through the air is nearly nothing, whatever
its speed over the ground. A drone, an aircraft or a bird moves through the air at an airspeed set by what keeps it up.
A single camera rarely shows either speed directly, but several things it can show bear on the difference, and this
stage puts each one as a test with a stated outcome -- `passes` (consistent with drifting), `fails` (not drifting), or
`cannot say` -- and never more than the evidence holds. Every question is put so that a drifting body answers yes.

The three main tests need only what a sensor's display shows (its ranges, or the aircraft's own position and its line
of sight) and the object's brightness, so they can run on any video whose display is intact:

    T1 height    Does it hold its height, or rise as a balloon does?  From the ranges on the display: the slant range S
                 and its horizontal part G give the height difference sqrt(S^2 - G^2). A floater holds its height, a
                 sounding balloon rises at about 5 m/s (both wind-borne); vertical speeds beyond a balloon's fail.
    T2 winds     Does its motion relative to the aircraft fit the winds? An aircraft flies through the air along its
                 heading, so for a body drifting with the wind the relative motion's part across that heading is the
                 difference between the winds at the two heights, whatever the airspeed; its part along the heading
                 then gives the airspeed the aircraft would need. Needs the ranges, the north pointer's bearings, the
                 aircraft's heading and archived model winds. A drone adds its own airspeed, and the airspeeds that
                 would need are reported for each speed asked.
    T3 beat      Is its brightness free of a beat at a wingbeat's or a rotor's rate? Read from `mcdonald flicker`: a
                 beat of its own that holds across the video (the whole track beats, or it comes back in stretches
                 apart, flicker's headline rule) fails; a beat in one stretch of many is not counted, since a flame or
                 chance can make one, and the test passes on the whole stretch; no beat passes, with the smallest beat
                 the clip could have shown. A pass here is never a strong test (the verdict needs T2 or T4a).

Where the display shows the aircraft's own position and its line of sight's ground point rather than ranges to the
object, T1 and T2 run from the aircraft's own track instead (`--platform`, `--los`).

The fourth test weighs evidence that only some videos hold -- something the object sheds, cloud at its depth, a strike
-- and runs whichever of its parts the inputs allow. It fails when a part fails, passes when a part passes and none
fails, and cannot say otherwise:

    T4 other     Does other evidence in the video, where there is any, agree with drift? Its parts:
    T4a tracer   Does the object move with something that moves with the air at its own depth? Light pieces it sheds
                 stop in the air within about a second, so a body flying at airspeed V leaves them behind, and across a
                 line of sight depressed by delta at least V sin(delta) of that shows. Measured in the object's own
                 length L on the screen, the pieces' speed against it bounds its airspeed in its own lengths per second,
                 with no field of view, range or wind. Fixed-wing drones cruise at two to tens of their wingspans per
                 second and birds at four or more; a bound under two passes. Cloud is a tracer only where it is shown
                 at the object's depth (cloud passing in front of it); even then it places the object only within the
                 layer, so a relative motion through it cannot be told from a depth offset, and that says so.
    T4b remains  If it was struck, do its remains sink steadily? Any powered drone carries dense parts that fall with
                 gravity's acceleration once it breaks up; on the screen a fall accelerates at g cos(delta)/L_true in
                 lengths per second squared. The remains' acceleration is read two ways: by a quadratic in time with
                 a moving-block bootstrap error, and from the track's own speed band (its wander fitted as a
                 covariance, `kinematics.speed_band`), whose wander can outlast the bootstrap's blocks. The band's
                 bound on a steady change of speed it could have missed (95 %, either way) sets the reach: a falling
                 wreck of every body smaller than g cos(delta) over that bound is excluded (over a + 3 sigma where
                 the band gives no bound). Passes at 10 m or more, since every drone and every bird is smaller.

Until 2026-10-28 the tracer and the remains were T1 and T2, and the height, the winds and the beat T3, T4 and T5. They
were put last because few videos show a strike or anything shed, while the other three run on any intact display
(Jacob).

The verdict is `consistent with wind-borne drift (tentative)` when a strong test (T2, or T4a with a tracer at the
object's own depth) passes and none fails; `not drifting` when any test fails; otherwise `cannot say`. A beat decides
only when it holds across the video: a rotorcraft hovering in calm air has no airspeed, so only its rotor's steady beat
tells it from a drifter, while a lantern's flame, or chance over many windows, can make one stretch beat. Each test runs
only on the inputs it needs and says what it lacks otherwise.

What it cannot do: name the object. A drifting object can be a balloon, a bag, a cloud of chaff or a leaf; T1 narrows
the class, nothing here identifies it. Nor are its tests stronger than their inputs: the ranges, the bearings and
the heading come from the display, read by `readout`, `symbology` or by eye, and the stage checks only that they hang
together (the straight-line fit's residuals).
"""
import csv
import json
import math
from pathlib import Path

import numpy as np

from .progress import to_stderr
from .report import Found, emit, inputs_of, said_to_stderr

G = 9.81
KN = 0.514444
NM = 1852.0
FLY_MIN = 2.0           # lengths/s: the slowest a powered fixed-wing flier cruises for its size (the largest drones
                        # make about two to three wingspans a second); birds fly at four or more
BIRD_MIN = 4.0
ASCENT = 5.0            # m/s, a sounding balloon's climb
VERTICAL_MAX = 8.0      # m/s: faster than any balloon rises or sinks
WRECK_MIN_M = 10.0      # T4b passes when it excludes a falling wreck of every body up to this size: every drone and every
                        # bird is smaller (20 m until 2026-11-02, when the band's honest bound put the Yemen remains at 17 m)
WRECK_FAIL_M = 20.0     # T4b fails when the remains accelerate down at half of this size's free fall or more (the old pass
                        # size, kept apart so that the fail rule does not move with the pass threshold)
T_LAYER = 280.0         # K: the mean temperature of a missing pressure level's layer, for its height
BLOCK, NBOOT = 15, 2000
PASS, FAIL, CANNOT = "passes", "fails", "cannot say"
STRONG = ("T2", "T4a")  # the tests that bear on the airspeed itself (T4a only with a tracer at its depth)


# ---- reading ---------------------------------------------------------------------------
def read_rows(path):
    """The rows of a CSV, `#` lines skipped, as dicts."""
    with open(path, newline="", encoding="utf-8") as f:
        lines = [ln for ln in f if ln.strip() and not ln.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def read_track(path):
    from .forensics import read_track as rt
    return rt(path)


def read_series(path, value=("value_m", "value", "m"), err=("frame_err",), default_err=1.0):
    """frame, value[, error] rows -> arrays (frame, value, error); the error column is the first of `err` present."""
    rows = read_rows(path)
    vk = next(k for k in value if k in rows[0])
    ek = next((k for k in err if k in rows[0]), None)
    f = np.array([float(r["frame"]) for r in rows])
    v = np.array([float(r[vk]) for r in rows])
    e = np.array([float(r[ek]) if ek and r.get(ek) not in (None, "") else default_err for r in rows])
    return f, v, e


def _blocks(n, rng, block=BLOCK):
    block = max(2, min(block, n // 4))
    idx = np.concatenate([np.arange(s, s + block) for s in rng.integers(0, n - block + 1, n // block + 1)])
    return idx[:n]


def boot_fit(t, v, deg, fn, rng, nboot=NBOOT):
    """fn(polyfit) and its moving-block bootstrap error over the residuals (correlated wander counted)."""
    c = np.polyfit(t, v, deg)
    res = v - np.polyval(c, t)
    out = [fn(np.polyfit(t, np.polyval(c, t) + res[_blocks(len(v), rng)], deg)) for _ in range(nboot)]
    return float(fn(c)), float(np.std(out))


# ---- T4a and T4b, other evidence: the pieces and the remains -----------------------------------
def _band(track, fps):
    """The track's speed band (`kinematics.speed_band`: a line, a Matérn-3/2 wander and a nugget fitted by REML), or
    None under its minimum points. It draws no random numbers of its own from the stage's generator, so the bootstrap's
    draws beside it are unchanged."""
    from .kinematics import speed_band
    got = speed_band(track, fps)
    return got[0] if got else None


def relative(remains, piece, fps, rng):
    """The piece's velocity against the remains, px/s, from a straight line in time to their difference (a moving-block
    bootstrap error), and the difference track's average speed from its own speed band (`_band`; None where the track
    has no band)."""
    common = sorted(set(remains) & set(piece))
    if len(common) < 10:
        return None
    t = (np.array(common, float) - common[0]) / fps
    dx = np.array([piece[n][0] - remains[n][0] for n in common])
    dy = np.array([piece[n][1] - remains[n][1] for n in common])
    vx, ex = boot_fit(t, dx, 1, lambda c: c[0], rng)
    vy, ey = boot_fit(t, dy, 1, lambda c: c[0], rng)
    sp = math.hypot(vx, vy)
    b = _band({int(n): (float(x), float(y)) for n, x, y in zip(common, dx, dy)}, fps)
    return dict(frames=[int(common[0]), int(common[-1])], vx_px_s=vx, vy_px_s=vy, speed_px_s=sp,
                speed_err_px_s=math.hypot(vx * ex, vy * ey) / sp if sp > 0 else math.hypot(ex, ey),
                band_speed_px_s=b["v_mean_px_per_s"] if b else None,
                band_speed_err_px_s=b["v_mean_err_px_per_s"] if b else None)


def fall(track, fps, rng):
    """Screen-down rate (px/s) and acceleration (px/s^2) of a track, with moving-block bootstrap errors (BLOCK frames
    a block); and the acceleration again from the track's own speed band (`_band`), whose fitted wander can outlast the
    bootstrap's blocks -- the band's error is then the honest one (on the Yemen remains the wander's range is 0.55-0.75 s
    against 0.5-s blocks, and the band's error 2.4 times the bootstrap's). The band's fields, None where the track has
    no band: `band_accel_px_s2`, the change of the screen-down velocity over the stretch divided by its span (+y down),
    and `band_accel_err_px_s2` its sigma; `band_accel_max_px_s2`, the largest steady change of speed along the track the
    band could have missed (95 %, either sign; `kinematics.change_bound`), None where the band saw the change;
    `band_range_s` and `band_nugget_px`, the wander's range and the nugget, each the larger of the two coordinates';
    `band_light`, the backtest's light."""
    fr = np.array(sorted(track), float)
    t = (fr - fr[0]) / fps
    y = np.array([track[int(n)][1] for n in fr])
    v, ve = boot_fit(t, y, 1, lambda c: c[0], rng)
    a, ae = boot_fit(t, y, 2, lambda c: 2 * c[0], rng)
    out = dict(frames=[int(fr[0]), int(fr[-1])], rate_px_s=v, rate_err=ve, accel_px_s2=a, accel_err=ae)
    b = _band(track, fps)
    span = float(b["t1"] - b["t0"]) if b else 0.0
    if not b or span <= 0:
        return dict(out, band_accel_px_s2=None, band_accel_err_px_s2=None, band_accel_max_px_s2=None, band_range_s=None,
                    band_nugget_px=None, band_light=None)
    cb = b.get("change_bound")
    return dict(out, band_accel_px_s2=float(b["dv_xy"][1]) / span, band_accel_err_px_s2=float(b["dv_err_xy"][1]) / span,
                band_accel_max_px_s2=float(cb["dv_max_px_per_s"]) / span if cb else None,
                band_range_s=float(max(b["range_s"])), band_nugget_px=float(max(b["nugget_px"])),
                band_light=(b.get("backtest") or {}).get("light"))


def test_tracer(L, rels, delta_deg, depth="same", comotion=None):
    """T4a, other evidence: a tracer. `L` = (the object's length on the screen, the smallest it appears) in px; `rels`
    the pieces' speeds against the remains (`relative`); or `comotion`, the envelope of `mcdonald comotion` (motion
    against the cloud field in D/s)."""
    out = dict(test="T4a", question="does it move with something that moves with the air at its own depth?")
    if comotion is not None:
        r = comotion.get("results", comotion)
        legs = r.get("legs") or ([r["whole"]] if r.get("whole") else [])
        rates = [lg["rel_D_per_s"] for lg in legs if lg]
        out.update(tracer="cloud", tracer_depth=depth, rel_D_per_s=[round(x, 2) for x in rates],
                   comotion_verdict=r.get("verdict"))
        if not rates:
            return dict(out, outcome=CANNOT, reading="no relative motion against the cloud was measured")
        if depth != "same" and depth != "layer":
            return dict(out, outcome=CANNOT, reading="nothing shows the cloud at the object's depth (no cloud passes in "
                                                     "front of it), so the cloud is not a tracer of its air")
        if r.get("verdict") == "CARRIED":
            return dict(out, outcome=PASS, reading="it moves with the cloud around it, within its own width")
        return dict(out, outcome=CANNOT, reading=(
            f"it moves through the cloud at {min(rates):.1f}-{max(rates):.1f} of its own diameters per second; the cloud "
            "passing in front places it only within the layer, and a depth offset inside it, wind shear or vertical "
            "motion can give that much without any airspeed"))
    rels = [r for r in rels if r]
    if not rels:
        return dict(out, outcome=CANNOT, reading="no pieces tracked with the remains")
    Lj, Ls = L
    s_hi = max(r["speed_px_s"] for r in rels) / Ls          # in the smallest length: the rate kindest to a flier
    s_lo = max(r["speed_px_s"] for r in rels) / Lj
    out.update(tracer="pieces it shed", tracer_depth="same", pieces=len(rels),
               pieces_L_per_s=[round(r["speed_px_s"] / Lj, 2) for r in rels],
               pieces_band_L_per_s=[round(r["band_speed_px_s"] / Lj, 2) if r.get("band_speed_px_s") is not None else None
                                    for r in rels],                # the same from each difference track's own band
               fastest_L_per_s=[round(s_lo, 2), round(s_hi, 2)])
    if delta_deg is None:
        return dict(out, outcome=CANNOT, reading="the depression of the line of sight is not known, so flight along it "
                                                 "could hide an airspeed")
    sd = math.sin(math.radians(delta_deg))
    bound = s_hi / sd
    out.update(depression_deg=delta_deg, airspeed_bound_L_per_s=round(bound, 2),
               a_flier_at_2_needs_L_per_s=round(FLY_MIN * sd, 2), a_bird_needs_L_per_s=round(BIRD_MIN * sd, 2))
    if bound < FLY_MIN:
        return dict(out, outcome=PASS, reading=(
            f"the pieces move away from the remains at no more than {s_hi:.2f} of the object's lengths per second, so it "
            f"moved through the air at less than {bound:.2f} of its own lengths per second: slower than any powered "
            f"flier or bird cruises for its size ({FLY_MIN:g} or more)"))
    if s_lo >= FLY_MIN:
        return dict(out, outcome=FAIL, reading=f"the pieces leave it at {s_lo:.2f} lengths per second or more: it flies "
                                               "through the air")
    return dict(out, outcome=CANNOT, reading=f"its airspeed is bounded only at {bound:.2f} lengths per second, within "
                                             "a slow flier's")


def test_wreck(accel_L, accel_err_L, delta_deg, min_m=WRECK_MIN_M, band=None, fail_m=WRECK_FAIL_M):
    """T4b, other evidence: the remains. `accel_L`, `accel_err_L`: the remains' screen-down acceleration in the object's
    length per second squared by a quadratic in time, with its bootstrap error. `band`: the same from the track's own
    speed band (`fall`), dict(accel_L, accel_err_L, accel_max_L) in L/s^2 -- the band's change of the screen-down velocity
    over the stretch divided by its span, its sigma, and the largest steady change of speed the band could have missed
    (95 %, either sign; None where the band saw the change) -- or None. On the screen a body of true length L_true falls
    at g cos(delta) / L_true, so the reach, the size under which a falling wreck of every body is excluded, is g cos(delta)
    over the band's bound where it gives one (`reach_by` "the band's 95 % bound on a steady change of speed"; the band's
    wander can outlast the bootstrap's blocks, and the bootstrap's error is then too small -- 2.4 times on the Yemen
    remains), else over a + 3 sigma (`reach_by` "a + 3 sigma"). Passes when the reach is `min_m` (WRECK_MIN_M, 10 m) or
    more: every drone and every bird is smaller. Fails when the quadratic's a - 3 sigma is at or above half the free
    fall of a `fail_m` (WRECK_FAIL_M, 20 m) body, a constant of its own so that it does not move with the pass
    threshold; cannot say between. Until 2026-11-02 the pass needed 20 m and the reach was a + 3 sigma alone, which put
    the Yemen remains at 75 m where the band's bound puts them at 16.5 ("about 17 m"). The fail rule is tried first
    (until then the pass was), so that a measured acceleration down is never read as a steady sink: with the pass at
    10 m a 20-m body's fall, measured to 0.05 L/s^2, reaches 14 m and would otherwise pass."""
    out = dict(test="T4b", question="if it was struck, do its remains sink steadily?")
    if accel_L is None:
        return dict(out, outcome=CANNOT, reading="no remains tracked after a strike")
    if delta_deg is None:
        return dict(out, outcome=CANNOT, reading="the depression is not known: a fall straight along the line of sight "
                                                 "would not show")
    gc = G * math.cos(math.radians(delta_deg))
    up = accel_L + 3 * accel_err_L
    b = band or {}
    a_max = b.get("accel_max_L")
    if a_max is not None and a_max > 0:
        excluded_m, by = gc / a_max, "the band's 95 % bound on a steady change of speed"
    else:
        excluded_m, by = (gc / up if up > 0 else float("inf")), "a + 3 sigma"
    out.update(accel_L_per_s2=round(accel_L, 3), accel_err=round(accel_err_L, 3),
               band_accel_L_per_s2=round(b["accel_L"], 3) if b.get("accel_L") is not None else None,
               band_accel_err=round(b["accel_err_L"], 3) if b.get("accel_err_L") is not None else None,
               band_accel_max_L_per_s2=round(a_max, 3) if a_max is not None else None, reach_by=by,
               free_fall_L_per_s2={f"{m:g} m": round(gc / m, 2) for m in (1, 5, 20)},
               excludes_wrecks_under_m=round(excluded_m, 0) if math.isfinite(excluded_m) else None)
    fit = f"their acceleration is {accel_L:+.2f} +- {accel_err_L:.2f} lengths/s^2 by a quadratic in time"
    if b.get("accel_L") is not None:
        fit += f", and {b['accel_L']:+.2f} +- {b['accel_err_L']:.2f} with the track's own wander fitted (a band)"
        if a_max is not None:
            fit += f", which would have shown a steady change of more than {a_max:.2f} lengths/s^2 either way (95 %)"
    reach = f"about {excluded_m:.0f} m" if math.isfinite(excluded_m) else "any size"
    if accel_L - 3 * accel_err_L >= 0.5 * gc / fail_m:          # tried first: a measured fall is never a steady sink
        return dict(out, outcome=FAIL, reading=f"the remains accelerate down at {accel_L:.2f} lengths/s^2, as a heavy "
                                               "body falls")
    if excluded_m >= min_m:
        return dict(out, outcome=PASS, reading=(
            f"the remains sink at a steady rate: {fit}: no falling wreck of any body smaller than {reach}"))
    return dict(out, outcome=CANNOT, reading=f"it excludes a falling wreck only below {excluded_m:.0f} m ({fit})")


def test_other(parts):
    """T4, other evidence: what only some videos hold, its parts the tracer (T4a) and the remains of a strike (T4b). It
    fails when a part fails, passes when a part passes and none fails, and cannot say otherwise. Whether it bears on the
    airspeed (a strong test for the verdict) is its tracer part's to say."""
    out = dict(test="T4", question="does other evidence in the video, where there is any, agree with drift?",
               parts=list(parts))
    ids = lambda ps: " and ".join(p["test"] for p in ps)                          # noqa: E731
    fails = [p for p in parts if p["outcome"] == FAIL]
    if fails:
        return dict(out, outcome=FAIL, reading=f"{ids(fails)} fail{'s' if len(fails) == 1 else ''}")
    passes = [p for p in parts if p["outcome"] == PASS]
    if passes:
        return dict(out, outcome=PASS, reading=f"{ids(passes)} pass{'es' if len(passes) == 1 else ''}, none fails")
    told = "; ".join(f"{p['test']}: {p['reading']}" for p in parts)
    return dict(out, outcome=CANNOT, reading=f"no part decided ({told})")


# ---- T1 and T2: the ranges ------------------------------------------------------------------
def _line(t, y, e):
    A = np.vstack([t, np.ones_like(t)]).T
    W = np.diag(1.0 / e ** 2)
    cov = np.linalg.inv(A.T @ W @ A)
    c = cov @ A.T @ W @ y
    r = y - A @ c
    dof = max(1, len(y) - 2)
    chi2 = float(r @ W @ r) / dof
    return float(c[0]), float(np.sqrt(cov[0, 0] * max(1.0, chi2))), chi2, float(np.sqrt(np.mean(r ** 2)))


def height_steps(slant, horiz, fps):
    """The height difference sqrt(S^2 - G^2) at each horizontal-range reading, S interpolated between its own readings
    by a quadratic in time; `slant`/`horiz` = (frames, metres, frame errors)."""
    fs, S, es = slant
    fg, Gm, eg = horiz
    cS = np.polyfit(fs, S, 2)
    rms = float(np.sqrt(np.mean((S - np.polyval(cS, fs)) ** 2)))
    Sg = np.polyval(cS, fg)
    dh = np.sqrt(np.maximum(Sg ** 2 - Gm ** 2, 0))
    # its error: the horizontal reading's timing (+- its frame error) carried through the slant range's change
    lo = np.sqrt(np.maximum(np.polyval(cS, fg - eg) ** 2 - Gm ** 2, 0))
    hi = np.sqrt(np.maximum(np.polyval(cS, fg + eg) ** 2 - Gm ** 2, 0))
    e = np.maximum(np.abs(lo - hi) / 2, 1.0)
    return fg, dh, e, Sg, rms


def test_vertical(slant, horiz, own=None, fps=30.0):
    """T1. `own` = (frames, metres) of the aircraft's own height (sea readings), optional."""
    out = dict(test="T1", question="does it hold its height, or rise as a balloon does?")
    if slant is None or horiz is None or len(horiz[0]) < 3 or len(slant[0]) < 3:
        return dict(out, outcome=CANNOT, reading="no ranges on the display (three or more of each are needed)"), None
    fg, dh, e, Sg, rms = height_steps(slant, horiz, fps)
    t = (fg - fg[0]) / fps
    s_dh, e_dh, chi_dh, rms_dh = _line(t, dh, e)
    own_s, own_e = 0.0, 0.0
    if own is not None and len(own[0]) >= 3:
        to = (own[0] - own[0][0]) / fps
        own_s, own_e, _, _ = _line(to, own[1], own[2])
    climb = own_s - s_dh
    err = math.hypot(own_e, e_dh)
    delta = math.degrees(math.asin(min(1.0, dh[-1] / Sg[-1])))
    out.update(height_below_m=round(float(dh.mean()), 1), height_rms_m=round(rms_dh, 1), span_s=round(float(t[-1]), 1),
               climb_m_s=round(climb, 2), climb_err_m_s=round(err, 2), depression_deg=round(delta, 2),
               aircraft_climb_m_s=round(own_s, 2) if own is not None else None,
               steps=[[int(f), round(float(h), 1), round(float(x), 1)] for f, h, x in zip(fg, dh, e)])
    if abs(climb) - 2 * err > VERTICAL_MAX:
        return dict(out, outcome=FAIL, reading=f"it climbs or dives at {climb:+.1f} +- {err:.1f} m/s, faster than a "
                                               "balloon"), delta
    if abs(climb) <= 2 * err + 1.0:
        excl = (ASCENT - climb) / err if err > 0 else float("inf")
        return dict(out, outcome=PASS, reading=(
            f"it holds its height: {climb:+.1f} +- {err:.1f} m/s, the height difference steady to {rms_dh:.1f} m rms "
            f"over {t[-1]:.1f} s; a sounding balloon's {ASCENT:g} m/s climb is {excl:.0f} errors away")), delta
    return dict(out, outcome=PASS, reading=f"it climbs at {climb:+.1f} +- {err:.1f} m/s, as a sounding balloon does"), delta


def fit_line(slant, horiz, bearings, fps, rng, t0=None):
    """A straight line in space, r(t) = r0 + v t (east, north, up; the object relative to the aircraft), fitted to the
    slant ranges (|r|), the horizontal ranges (|r_h|) and the bearings (degrees true), each timed to the frame. Errors
    from the fit's covariance scaled by its reduced chi-square, checked by a bootstrap over the readings."""
    from scipy.optimize import least_squares
    fs, S, es = slant
    fg, Gm, eg = horiz
    fb, B, eb = bearings
    t0 = fs[0] if t0 is None else t0
    rate_s = abs(np.polyfit(fs / fps, S, 1)[0])
    rate_g = abs(np.polyfit(fg / fps, Gm, 1)[0])
    Sd = [((f - t0) / fps, s, max(e, 1.0) / fps * max(rate_s, 1.0)) for f, s, e in zip(fs, S, es)]
    Gd = [((f - t0) / fps, g, max(e, 1.0) / fps * max(rate_g, 1.0)) for f, g, e in zip(fg, Gm, eg)]
    Bd = [((f - t0) / fps, b, max(e, 0.02)) for f, b, e in zip(fb, B, eb)]

    def resid(p, Sd, Gd, Bd):
        x0, y0, z0, vx, vy, vz = p
        o = []
        for t, v, e in Sd:
            o.append((math.sqrt((x0 + vx * t) ** 2 + (y0 + vy * t) ** 2 + (z0 + vz * t) ** 2) - v) / e)
        for t, v, e in Gd:
            o.append((math.hypot(x0 + vx * t, y0 + vy * t) - v) / e)
        for t, v, e in Bd:
            b = math.degrees(math.atan2(x0 + vx * t, y0 + vy * t)) % 360
            o.append(((b - v + 180) % 360 - 180) / e)
        return np.array(o)

    b0 = math.radians(Bd[0][1])
    g0, dh0 = Gd[0][1], math.sqrt(max(Sd[0][1] ** 2 - Gd[0][1] ** 2, 1.0))
    p0 = [g0 * math.sin(b0), g0 * math.cos(b0), -dh0, 0.0, 0.0, 0.0]
    xs = [1000, 1000, 1000, 10, 10, 1]
    fit = least_squares(resid, p0, args=(Sd, Gd, Bd), x_scale=xs)
    dof = len(fit.fun) - 6
    chi2 = float(np.sum(fit.fun ** 2))
    cov = np.linalg.inv(fit.jac.T @ fit.jac) * max(1.0, chi2 / dof)
    err = np.sqrt(np.diag(cov))
    boots = []
    for _ in range(300):
        pick = lambda L: [L[i] for i in rng.integers(0, len(L), len(L))]
        try:
            boots.append(least_squares(resid, fit.x, args=(pick(Sd), pick(Gd), pick(Bd)), x_scale=xs).x)
        except Exception:
            pass
    boots = np.array(boots)
    p = fit.x
    sp = math.hypot(p[3], p[4])
    return dict(t0_frame=float(t0), r0_m=p[:3].tolist(), v_m_s=p[3:].tolist(), v_err_m_s=err[3:].tolist(),
                speed_m_s=sp, toward_deg=math.degrees(math.atan2(p[3], p[4])) % 360,
                speed_err_m_s=float(max(np.hypot(boots[:, 3], boots[:, 4]).std(), 0.0)) if len(boots) else None,
                toward_err_deg=float(np.degrees(np.arctan2(boots[:, 3], boots[:, 4])).std()) if len(boots) else None,
                chi2_dof=chi2 / dof,
                range_rms_m=float(np.sqrt(np.mean(np.concatenate([fit.fun[:len(Sd)] * [s[2] for s in Sd],
                                                                  fit.fun[len(Sd):len(Sd) + len(Gd)] * [g[2] for g in Gd]]) ** 2))))


def _uv(speed_kn, from_deg):
    s = np.asarray(speed_kn, float) * KN
    a = np.radians(np.asarray(from_deg, float))
    return np.stack([-s * np.sin(a), -s * np.cos(a)], -1)


def hourly_levels(d):
    """Each hour of an Open-Meteo archive file as (time, heights above the sea, winds east/north in m/s), lowest first.
    Pressure levels (hourly wind_speed_<P>hPa in kn, wind_direction_<P>hPa) stand at geopotential_height_<P>hPa where
    given; a level without a height is placed from the nearest level that has one by the hypsometric equation for a
    layer at T_LAYER. Height levels (wind_speed_<N>m: N metres above the model's ground, as the archive gives 10 and
    100 m for years without pressure levels) stand at the file's `elevation` plus N. A level whose wind is missing that
    hour is left out."""
    h = d["hourly"]
    plev = sorted({int(k.split("_")[-1][:-3]) for k in h if k.startswith("wind_speed_") and k.endswith("hPa")})
    hlev = sorted({int(k[11:-1]) for k in h if k.startswith("wind_speed_") and k.endswith("m") and k[11:-1].isdigit()})
    z = {}
    for lv in plev:
        k = f"geopotential_height_{lv}hPa"
        if k in h and all(x is not None for x in h[k]):
            z[lv] = np.asarray(h[k], float)
    for lv in plev:
        if lv not in z and z:
            ref = min(z, key=lambda q: abs(q - lv))
            z[lv] = z[ref] - 287.05 * T_LAYER / 9.80665 * math.log(lv / ref)
    plev = [lv for lv in plev if lv in z]
    ground = float(d.get("elevation") or 0.0)
    out = []
    for i, t in enumerate(h["time"]):
        zs, us = [], []
        for lv in plev:
            s, a = h[f"wind_speed_{lv}hPa"][i], h[f"wind_direction_{lv}hPa"][i]
            if s is not None and a is not None:
                zs.append(z[lv][i])
                us.append(_uv(s, a))
        for lv in hlev:
            s, a = h[f"wind_speed_{lv}m"][i], h.get(f"wind_direction_{lv}m", [None] * (i + 1))[i]
            if s is not None and a is not None:
                zs.append(ground + lv)
                us.append(_uv(s, a))
        if zs:
            order = np.argsort(zs)
            out.append((t, np.asarray(zs, float)[order], np.asarray(us, float)[order]))
    return out


def _at(zs, us, m):
    return np.array([np.interp(m, zs, us[:, 0]), np.interp(m, zs, us[:, 1])])


def wind_samples(paths, obj_m, air_m):
    """Hourly winds at the object's and the aircraft's heights from Open-Meteo archive files (`hourly_levels`),
    interpolated in height between the levels and held beyond them."""
    out = []
    for p in paths:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        for t, zs, us in hourly_levels(d):
            out.append(dict(file=Path(p).stem, time=t, w_obj=_at(zs, us, obj_m), w_air=_at(zs, us, air_m)))
    return out


def test_wind(line, heading_deg, winds, speeds=(10.0, 25.0, 50.0), air_min_kn=None, air_max_kn=None):
    """T2. `line` from fit_line; `winds` from wind_samples."""
    out = dict(test="T2", question="does its motion relative to the aircraft fit the winds?")
    if line is None:
        return dict(out, outcome=CANNOT, reading="no ranges and bearings to fit the relative motion")
    hd = math.radians(heading_deg)
    h_hat = np.array([math.sin(hd), math.cos(hd)])
    p_hat = np.array([-math.cos(hd), math.sin(hd)])           # left of the heading
    v = np.array(line["v_m_s"][:2])
    v_left = float(v @ p_hat)
    out.update(relative_m_s=round(line["speed_m_s"], 2), relative_toward_deg=round(line["toward_deg"], 1),
               heading_deg=heading_deg, sideways_right_kn=round(-v_left / KN, 1), range_rms_m=round(line["range_rms_m"], 1))
    if not winds:
        return dict(out, outcome=CANNOT, reading="no archived winds given")
    dw_left = np.array([float((s["w_obj"] - s["w_air"]) @ p_hat) for s in winds])
    A = np.array([s["w_obj"] - s["w_air"] - v for s in winds])
    air = A @ h_hat / KN
    slip = A @ p_hat / KN
    out.update(wind_difference_right_kn=[round(float(-dw_left.max() / KN), 1), round(float(-dw_left.min() / KN), 1)],
               airspeed_kn=[round(float(air.min()), 1), round(float(air.max()), 1)],
               shortfall_kn=[round(float(np.abs(slip).min()), 1), round(float(np.abs(slip).max()), 1)],
               samples=len(winds),
               needs_kn=[[round(float(a), 1), round(float(s), 1)] for a, s in zip(air, slip)])   # along, left of the heading
    phi = np.radians(np.arange(0.0, 360.0, 0.1))
    ring = np.stack([np.sin(phi), np.cos(phi)], 1)
    drones = {}
    for V in speeds:
        hi, lo = [], []
        for a in A:
            P = V * ring + a[None, :]
            c = P @ p_hat
            for i in np.nonzero(np.sign(c[:-1]) != np.sign(c[1:]))[0]:
                u = float(P[i] @ h_hat) / KN
                (hi if float(ring[i] @ h_hat) > 0 else lo).append(u)
        drones[f"{V:g} m/s"] = dict(flying_its_way_kn=[round(min(hi), 1), round(max(hi), 1)] if hi else None,
                                    flying_toward_it_kn=[round(min(lo), 1), round(max(lo), 1)] if lo else None)
    out["drones"] = drones
    same_side = bool(np.all(np.sign(dw_left) == np.sign(v_left))) and abs(v_left) > 0
    in_range = (air_max_kn is None or air.max() <= air_max_kn) and (air_min_kn is None or air.min() >= air_min_kn)
    out.update(same_side=same_side)
    if same_side and in_range:
        return dict(out, outcome=PASS, reading=(
            f"a body drifting with the winds needs the aircraft at {air.min():.0f}-{air.max():.0f} kn through the air, and "
            f"the winds' difference across its heading ({-dw_left.max() / KN:.0f}-{-dw_left.min() / KN:.0f} kn) lies the same "
            f"way as the measured {-v_left / KN:.0f} kn, {np.abs(slip).min():.0f}-{np.abs(slip).max():.0f} kn short"))
    if not same_side:
        return dict(out, outcome=CANNOT, reading="the winds' difference across the heading does not lie the way the motion "
                                                 "does")
    return dict(out, outcome=CANNOT, reading=f"a drifting body needs an airspeed of {air.min():.0f}-{air.max():.0f} kn, "
                                             "outside the aircraft's range")


# ---- T1 and T2 from the aircraft's own track: the lines of sight ----------------------------
# Where a display shows the aircraft's own position (a WESCAM-style ACFT block) rather than ranges to the object, each
# reading is a ray from the aircraft through the object. If the aircraft turns, the rays cross, and a straight path at a
# steady velocity fitted to them gives the object's height and its velocity over the ground; a drifter's is the wind's
# at its height. A straight-flying aircraft cannot fix the range: any path scaled along the rays fits as well (the
# bearings-only problem), and the bootstrap says so. AARO's Puerto Rico lanterns (2026-10-21) are the known answer.
WGS_A, WGS_E2 = 6378137.0, 6.69437999014e-3
FLIER_MIN = 10.0        # m/s: T2 here fails only when the airspeed it needs is this much beyond the winds and the fit
VELOCITY_FIX = 5.0      # m/s: two errors of the fitted velocity over this, and the turn did not fix it
NEAR_LEVEL = 4.0        # a single observed level within this factor of the object's height (above the ground) counts
TURN_MIN = 30.0         # deg of heading change before the aircraft's own wind can be told from its airspeed


def ecef(lat, lon, h):
    la, lo = np.radians(lat), np.radians(lon)
    n = WGS_A / np.sqrt(1 - WGS_E2 * np.sin(la) ** 2)
    return np.stack([(n + h) * np.cos(la) * np.cos(lo), (n + h) * np.cos(la) * np.sin(lo),
                     (n * (1 - WGS_E2) + h) * np.sin(la)], -1)


def enu_rows(lat, lon):
    """The local east, north and up unit vectors in ECEF, as the rows of a matrix."""
    la, lo = math.radians(lat), math.radians(lon)
    return np.array([[-math.sin(lo), math.cos(lo), 0.0],
                     [-math.sin(la) * math.cos(lo), -math.sin(la) * math.sin(lo), math.cos(la)],
                     [math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)]])


class Plane:
    """A map about (lat0, lon0): east and north in metres along the ellipsoid's radii of curvature there."""

    def __init__(self, lat0, lon0):
        s = math.sin(math.radians(lat0))
        self.lat0, self.lon0 = lat0, lon0
        self.m = WGS_A * (1 - WGS_E2) / (1 - WGS_E2 * s * s) ** 1.5 * math.pi / 180       # m per degree north
        self.n = WGS_A / math.sqrt(1 - WGS_E2 * s * s) * math.cos(math.radians(lat0)) * math.pi / 180

    def xy(self, lat, lon):
        return (np.asarray(lon) - self.lon0) * self.n, (np.asarray(lat) - self.lat0) * self.m

    def latlon(self, e, n):
        return self.lat0 + np.asarray(n) / self.m, self.lon0 + np.asarray(e) / self.n


def _num(r, *keys):
    for k in keys:
        if r.get(k) not in (None, ""):
            return float(r[k])
    return None


def read_platform(path):
    """frame, lat, lon (decimal degrees, west and south negative), alt_m (or alt_ft) above the sea[, heading_deg]."""
    out = {}
    for r in read_rows(path):
        alt = _num(r, "alt_m")
        if alt is None:
            alt = _num(r, "alt_ft") * 0.3048
        out[int(float(r.get("frame") or r.get("n")))] = (float(r["lat"]), float(r["lon"]), alt,
                                                         _num(r, "heading_deg", "heading"))
    return out


def read_los(path):
    """frame and the line of sight: az_deg, dep_deg (true azimuth, depression below the horizontal), or the ground
    point the display prints, tgt_lat, tgt_lon, tgt_elev_m (or tgt_elev_ft); optionally off_right_deg, off_down_deg,
    the object's offset from the boresight."""
    out = {}
    for r in read_rows(path):
        el = _num(r, "tgt_elev_m")
        if el is None and _num(r, "tgt_elev_ft") is not None:
            el = _num(r, "tgt_elev_ft") * 0.3048
        out[int(float(r.get("frame") or r.get("n")))] = dict(
            az=_num(r, "az_deg"), dep=_num(r, "dep_deg"), tgt=(float(r["tgt_lat"]), float(r["tgt_lon"]), el)
            if r.get("tgt_lat") not in (None, "") else None,
            off=(_num(r, "off_right_deg") or 0.0, _num(r, "off_down_deg") or 0.0))
    return out


def rays(platform, los, fps):
    """The readings both files give: times (s), the aircraft's ECEF positions, and each line of sight as an azimuth
    and a depression at the aircraft, turned onto the object by its offset where given."""
    frames = sorted(set(platform) & set(los))
    t, A, az, dep, P = [], [], [], [], []
    for f in frames:
        lat, lon, alt, _ = platform[f]
        L = los[f]
        if L["tgt"] is not None:
            d = enu_rows(lat, lon) @ (ecef(*L["tgt"]) - ecef(lat, lon, alt))
            a = math.degrees(math.atan2(d[0], d[1])) % 360
            e = math.degrees(math.atan2(-d[2], math.hypot(d[0], d[1])))
        else:
            a, e = L["az"], L["dep"]
        e += L["off"][1]
        a += L["off"][0] / max(math.cos(math.radians(e)), 1e-6)
        t.append((f - 1) / fps)
        A.append(ecef(lat, lon, alt))
        az.append(a)
        dep.append(e)
        P.append((lat, lon, alt))
    return dict(frames=np.array(frames), t=np.array(t), A=np.array(A), az=np.array(az), dep=np.array(dep),
                platform=np.array(P), rot=np.array([enu_rows(la, lo) for la, lo, _ in P]))


def _path_points(p, t, tm, plane):
    lat, lon = plane.latlon(p[0] + p[3] * (t - tm), p[1] + p[4] * (t - tm))
    return ecef(lat, lon, p[2] + p[5] * (t - tm))


def _path_angles(p, R, plane, tm):
    """Azimuth and depression at each aircraft of the path's point at that time, and the range."""
    X = _path_points(p, R["t"], tm, plane) - R["A"]
    d = np.einsum("nij,nj->ni", R["rot"], X)
    return (np.degrees(np.arctan2(d[:, 0], d[:, 1])) % 360, np.degrees(np.arctan2(-d[:, 2], np.hypot(d[:, 0], d[:, 1]))),
            np.linalg.norm(X, axis=1))


def _fit_track(R, sig, plane, start=None):
    from scipy.optimize import least_squares
    tm = float(R["t"].mean())

    def res(p):
        a, e, _ = _path_angles(p, R, plane, tm)
        return np.r_[((a - R["az"] + 180) % 360 - 180) * np.cos(np.radians(R["dep"])) / sig[0], (e - R["dep"]) / sig[1]]

    if start is None:
        i = len(R["t"]) // 2
        lat, lon, alt = R["platform"][i]
        u = enu_rows(lat, lon).T @ np.array([math.sin(math.radians(R["az"][i])) * math.cos(math.radians(R["dep"][i])),
                                             math.cos(math.radians(R["az"][i])) * math.cos(math.radians(R["dep"][i])),
                                             -math.sin(math.radians(R["dep"][i]))])
        starts = []
        for rng_m in np.geomspace(300.0, 3e5, 28):
            x = R["A"][i] + rng_m * u
            la, lo, h = _geodetic(x)
            e0, n0 = plane.xy(la, lo)
            starts.append(np.array([e0, n0, h, 0.0, 0.0, 0.0]))
    else:
        starts = [np.asarray(start, float)]
    best = None
    for q0 in starts:
        try:
            f = least_squares(res, q0, x_scale=[1000, 1000, 100, 10, 10, 1])
        except ValueError:
            continue
        if best is None or f.cost < best.cost:
            best = f
    return best, tm


def _geodetic(x):
    """ECEF to latitude, longitude, height (Bowring, one step: ample at aircraft heights)."""
    b = WGS_A * math.sqrt(1 - WGS_E2)
    ep2 = (WGS_A ** 2 - b ** 2) / b ** 2
    p = math.hypot(x[0], x[1])
    th = math.atan2(x[2] * WGS_A, p * b)
    la = math.atan2(x[2] + ep2 * b * math.sin(th) ** 3, p - WGS_E2 * WGS_A * math.cos(th) ** 3)
    n = WGS_A / math.sqrt(1 - WGS_E2 * math.sin(la) ** 2)
    return math.degrees(la), math.degrees(math.atan2(x[1], x[0])), p / math.cos(la) - n


def fit_track(R, sig=(0.3, 0.1), ground_m=None, rng=None, nboot=2000):
    """The object's straight, steady path through the rays `R` (from `rays`): east, north and height at the readings'
    mean time on a map about the aircraft's mean position, and their rates; least squares in angle (azimuth weighted by
    the cosine of the depression; `sig`, deg, a priori), errors scaled by the reduced chi-square, and a bootstrap over
    the readings started from the solution."""
    rng = rng or np.random.default_rng(20261021)
    lat0, lon0 = float(np.mean(R["platform"][:, 0])), float(np.mean(R["platform"][:, 1]))
    plane = Plane(lat0, lon0)
    fit, tm = _fit_track(R, sig, plane)
    if fit is None:
        return None
    p = fit.x
    dof = max(1, len(fit.fun) - 6)
    chi2 = float(np.sum(fit.fun ** 2)) / dof
    try:
        err = np.sqrt(np.diag(np.linalg.inv(fit.jac.T @ fit.jac)) * max(1.0, chi2))
    except np.linalg.LinAlgError:
        err = np.full(6, np.inf)
    boots = []
    n = len(R["t"])
    for _ in range(nboot):
        i = np.sort(rng.integers(0, n, n))
        if len(set(i.tolist())) < 8:
            continue
        S = {k: (v[i] if isinstance(v, np.ndarray) and len(v) == n else v) for k, v in R.items()}
        q = p.copy()
        q[:3] += p[3:] * (S["t"].mean() - tm)
        f, _ = _fit_track(S, sig, plane, start=q)
        if f is not None:
            boots.append(f.x)
    B = np.array(boots)
    sp = math.hypot(p[3], p[4])
    tw = math.degrees(math.atan2(p[3], p[4])) % 360
    btw = (np.degrees(np.arctan2(B[:, 3], B[:, 4])) - tw + 180) % 360 - 180 + tw
    a, e, rr = _path_angles(p, R, plane, tm)
    lat, lon = plane.latlon(p[0], p[1])
    sd_v = float(np.hypot(np.hypot(B[:, 3], B[:, 4]).std(), sp * math.radians(btw.std())))
    turn = np.unwrap(np.radians(R["az"]))
    return dict(frames=[int(R["frames"][0]), int(R["frames"][-1])], mean_time_s=tm, lat=float(lat), lon=float(lon),
                height_m=float(p[2]), height_err_m=float(max(err[2], B[:, 2].std())),
                above_ground_m=float(p[2] - ground_m) if ground_m is not None else None,
                v_m_s=[float(p[3]), float(p[4])], speed_m_s=sp, toward_deg=tw,
                speed_sd_m_s=float(np.hypot(B[:, 3], B[:, 4]).std()), toward_sd_deg=float(btw.std()),
                velocity_err_m_s=max(sd_v, float(math.hypot(err[3], err[4]))),
                speed_p05_p95=[float(x) for x in np.percentile(np.hypot(B[:, 3], B[:, 4]), [5, 95])],
                climb_m_s=float(p[5]), climb_err_m_s=float(max(err[5], B[:, 5].std())), chi2_dof=chi2,
                rms_az_deg=float(np.sqrt(np.mean(((a - R["az"] + 180) % 360 - 180) ** 2))),
                rms_dep_deg=float(np.sqrt(np.mean((e - R["dep"]) ** 2))), range_m=[float(rr.min()), float(rr.max())],
                depression_deg=float(np.mean(e)), los_turn_deg=float(np.degrees(turn.max() - turn.min())),
                readings=n, boots=len(B), params=p.tolist(), map_origin=[lat0, lon0])


def aircraft_wind(platform, fps, pos_err_m=10.0):
    """The wind at the aircraft's own height from its turn: its positions are a start, plus the wind times the time,
    plus its airspeed along its heading integrated (the heading interpolated between readings in 0.1-s steps); least
    squares at `pos_err_m` a position. None unless the headings are given and turn by TURN_MIN or more."""
    from scipy.optimize import least_squares
    fr = sorted(f for f in platform if platform[f][3] is not None)
    if len(fr) < 6:
        return None
    t = (np.array(fr, float) - 1) / fps
    h = np.unwrap(np.radians([platform[f][3] for f in fr]))
    if math.degrees(h.max() - h.min()) < TURN_MIN:
        return None
    plane = Plane(float(np.mean([platform[f][0] for f in fr])), float(np.mean([platform[f][1] for f in fr])))
    E, N = plane.xy(np.array([platform[f][0] for f in fr]), np.array([platform[f][1] for f in fr]))
    tt = np.arange(t[0], t[-1] + 1e-9, 0.1)
    hh = np.interp(tt, t, h)
    s = np.interp(t, tt, np.concatenate([[0.0], np.cumsum(0.5 * (np.sin(hh[1:]) + np.sin(hh[:-1])) * 0.1)]))
    c = np.interp(t, tt, np.concatenate([[0.0], np.cumsum(0.5 * (np.cos(hh[1:]) + np.cos(hh[:-1])) * 0.1)]))

    def res(q):
        return np.r_[(q[0] + q[2] * (t - t[0]) + q[4] * s - E) / pos_err_m,
                     (q[1] + q[3] * (t - t[0]) + q[4] * c - N) / pos_err_m]

    f = least_squares(res, [E[0], N[0], 0.0, 0.0, 60.0])
    chi2 = 2 * f.cost / max(1, len(f.fun) - 5)
    err = np.sqrt(np.diag(np.linalg.inv(f.jac.T @ f.jac)) * max(1.0, chi2))
    alt = np.array([platform[f_][2] for f_ in fr])
    return dict(w=np.array(f.x[2:4]), err_m_s=float(math.hypot(err[2], err[3])), airspeed_m_s=float(f.x[4]),
                height_m=float(alt.mean()), heights_m=[float(alt.min()), float(alt.max())],
                heading_turn_deg=float(math.degrees(h.max() - h.min())), chi2_dof=float(chi2))


def _from(w):
    return (math.degrees(math.atan2(w[0], w[1])) + 180) % 360


def track_winds(height_m, ground_m=None, model=(), when=None, observed=None, own=None):
    """Every wind of the evidence at the object's height (above the sea), each a dict: label, w (east, north, m/s),
    counts (whether it bears on the object's own height), note.
    - Model files (`hourly_levels`), interpolated in height and held beyond their levels; only the hours within one of
      `when` (an ISO time) if given. They count.
    - Observed winds (rows: source, height_m above the sea, from_deg, speed_m_s): a source whose levels bracket the
      object's height is interpolated there (in the logarithm of the height above `ground_m` where given) and counts;
      a source that does not is read at its nearest level, which counts only within NEAR_LEVEL of the object's height
      (above the ground where given).
    - The aircraft's own wind (`aircraft_wind`), likewise; and where it blows above the object and an observed source
      only below, the two are interpolated between (the measured profile), which counts."""
    from datetime import datetime, timedelta
    g = ground_m if ground_m is not None else 0.0
    hz = lambda z: max(float(z) - g, 1.0)                                     # noqa: E731
    out = []
    for path in model:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        for t, zs, us in hourly_levels(d):
            if when:
                dt = abs(datetime.fromisoformat(t) - datetime.fromisoformat(when))
                if dt > timedelta(hours=1):
                    continue
            out.append(dict(label=f"{Path(path).stem} {t}", w=_at(zs, us, height_m), counts=True,
                            note=f"model, levels {zs.min():.0f}-{zs.max():.0f} m"))
    srcs = {}
    for r in observed or []:
        srcs.setdefault(r["source"], []).append((float(r["height_m"]), _uv(float(r["speed_m_s"]) / KN, float(r["from_deg"]))))
    below = {}
    for s, lv in srcs.items():
        lv.sort(key=lambda x: x[0])
        zs = np.array([x[0] for x in lv])
        us = np.array([x[1] for x in lv])
        if zs[0] <= height_m <= zs[-1] and len(zs) > 1:
            lz = np.log([hz(z) for z in zs]) if ground_m is not None else zs
            w = _at(lz, us, math.log(hz(height_m)) if ground_m is not None else height_m)
            out.append(dict(label=s, w=w, counts=True, note=f"observed, interpolated between {zs[0]:.0f}-{zs[-1]:.0f} m"))
            continue
        k = int(np.argmin(np.abs(zs - height_m)))
        ratio = max(hz(zs[k]), hz(height_m)) / min(hz(zs[k]), hz(height_m))
        out.append(dict(label=s, w=us[k], counts=ratio <= NEAR_LEVEL,
                        note=f"observed at {zs[k]:.0f} m, {ratio:.1f} times the object's height"))
        if zs[-1] < height_m:
            below[s] = (zs[-1], us[-1])
    if own is not None:
        ratio = max(hz(own["height_m"]), hz(height_m)) / min(hz(own["height_m"]), hz(height_m))
        out.append(dict(label="the aircraft's own", w=own["w"], counts=ratio <= NEAR_LEVEL,
                        note=f"from its turn, {own['heights_m'][0]:.0f}-{own['heights_m'][1]:.0f} m, {ratio:.1f} times "
                             "the object's height"))
        if own["height_m"] > height_m:
            for s, (z, w) in below.items():
                f = (math.log(hz(height_m)) - math.log(hz(z))) / (math.log(hz(own["height_m"])) - math.log(hz(z)))
                out.append(dict(label=f"between {s} and the aircraft's own", w=w + f * (own["w"] - w), counts=True,
                                note="measured profile, interpolated in the logarithm of height"))
    return out


def test_vertical_track(path):
    """T1 from the fitted path's climb; the same rule as from the ranges."""
    out = dict(test="T1", question="does it hold its height, or rise as a balloon does?", source="lines of sight")
    if path is None:
        return dict(out, outcome=CANNOT, reading="no lines of sight to fit")
    climb, err = path["climb_m_s"], path["climb_err_m_s"]
    out.update(climb_m_s=round(climb, 2), climb_err_m_s=round(err, 2), height_m=round(path["height_m"], 0),
               above_ground_m=round(path["above_ground_m"], 0) if path["above_ground_m"] is not None else None,
               depression_deg=round(path["depression_deg"], 2))
    if not math.isfinite(err) or 2 * err > VERTICAL_MAX:
        return dict(out, outcome=CANNOT, reading=f"the lines of sight do not fix its climb ({climb:+.1f} +- {err:.1f} m/s)")
    if abs(climb) - 2 * err > VERTICAL_MAX:
        return dict(out, outcome=FAIL, reading=f"it climbs or dives at {climb:+.1f} +- {err:.1f} m/s, faster than a balloon")
    if abs(climb) <= 2 * err + 1.0:
        return dict(out, outcome=PASS, reading=f"it holds its height: {climb:+.2f} +- {err:.2f} m/s")
    return dict(out, outcome=PASS, reading=f"it climbs or sinks at {climb:+.1f} +- {err:.1f} m/s, no faster than a balloon")


def test_wind_track(path, winds):
    """T2 from the aircraft's own track: a drifter moves over the ground at the wind's velocity at its height, so the
    airspeed it would need against each wind that counts is |V - W|. Passes when every one is within the winds' own
    spread plus two errors of the fitted velocity; fails when even the smallest is FLIER_MIN or more beyond them;
    cannot say when the lines of sight do not fix the velocity (two errors over VELOCITY_FIX) or between."""
    out = dict(test="T2", question="does its motion over the ground fit the winds at its height?", source="lines of sight")
    if path is None:
        return dict(out, outcome=CANNOT, reading="no lines of sight to fit")
    V = np.array(path["v_m_s"])
    ev = path["velocity_err_m_s"]
    out.update(speed_m_s=round(path["speed_m_s"], 2), toward_deg=round(path["toward_deg"], 1),
               velocity_err_m_s=round(ev, 2), los_turn_deg=round(path["los_turn_deg"], 1))
    if not math.isfinite(ev) or 2 * ev > VELOCITY_FIX:
        return dict(out, outcome=CANNOT, reading=(
            f"the lines of sight do not fix its velocity ({path['speed_m_s']:.1f} m/s, two errors {2 * ev:.1f}): the "
            f"line of sight turned {path['los_turn_deg']:.0f} deg; a straight-flying aircraft cannot range what it sees"))
    rows = []
    for w in winds:
        need = V - w["w"]
        rows.append(dict(wind=w["label"], counts=w["counts"], note=w["note"], speed_m_s=round(float(np.hypot(*w["w"])), 2),
                         from_deg=round(_from(w["w"]), 1), needs_m_s=round(float(np.hypot(*need)), 2),
                         direction_diff_deg=round((path["toward_deg"] - (_from(w["w"]) + 180) + 180) % 360 - 180, 1)))
    out["winds"] = rows
    W = np.array([w["w"] for w in winds if w["counts"]])
    if not len(W):
        return dict(out, outcome=CANNOT, reading="no wind at its height given")
    need = [r["needs_m_s"] for r in rows if r["counts"]]
    spread = max(0.25, float(np.max(np.linalg.norm(W[:, None] - W[None], axis=-1))))
    out.update(needs_m_s=[round(min(need), 2), round(max(need), 2)], winds_spread_m_s=round(spread, 2),
               winds_counted=len(need))
    if max(need) <= spread + 2 * ev:
        return dict(out, outcome=PASS, reading=(
            f"it moved over the ground at {path['speed_m_s']:.1f} m/s toward {path['toward_deg']:.0f} deg; the {len(need)} "
            f"winds at its height leave it {min(need):.1f}-{max(need):.1f} m/s through the air, within their own spread "
            f"({spread:.1f} m/s) and two errors of the fit ({2 * ev:.1f})"))
    if min(need) - spread - 2 * ev >= FLIER_MIN:
        return dict(out, outcome=FAIL, reading=(
            f"it moved over the ground at {path['speed_m_s']:.0f} m/s toward {path['toward_deg']:.0f} deg; even the "
            f"nearest wind at its height leaves it {min(need):.0f} m/s through the air, {min(need) - spread - 2 * ev:.0f} "
            "beyond the winds' spread and the fit's errors: it flies"))
    return dict(out, outcome=CANNOT, reading=(
        f"the winds at its height leave it {min(need):.1f}-{max(need):.1f} m/s through the air, beyond their spread "
        f"({spread:.1f}) but not by a flier's {FLIER_MIN:g} m/s"))


# ---- T3: the beat -------------------------------------------------------------------------------
def held_beat(r):
    """Whether the flicker envelope's beat holds across the video: the whole track beats, or it comes back in windows
    apart (flicker's headline rule, `comes_back`). An envelope without it: not where its finding says the beat is one
    stretch."""
    for b in (r.get("beat") or {}).values():
        if isinstance(b, dict) and "comes_back" in b:
            return bool(b["comes_back"]), b
    return "that is one stretch" not in (r.get("finding") or ""), None


def test_beat(env):
    """T3, from the envelope `mcdonald flicker --json` printed. A beat fails only where it holds across the video
    (`held_beat`): a rotorcraft hovering in calm air has no airspeed, and only its rotor's steady beat tells it from a
    drifter (the Santa Barbara hoist, 2026-10-21). A beat in one stretch of many is not counted, since a lantern's or a
    candle's flame, or chance over many windows, can make one, and the test passes on the whole stretch (AARO's Puerto
    Rico lanterns: 3.0 Hz in one 2-s window of 109, the background's own windows beating in 2 of 436; until 2026-10-22
    such a beat could not say)."""
    out = dict(test="T3", question="is its brightness free of a beat at a wingbeat's or a rotor's rate?")
    if env is None:
        return dict(out, outcome=CANNOT, reading="no `mcdonald flicker` result given")
    r = env.get("results", env)
    beats = r.get("beats")
    floor = None
    inj = r.get("injection") or {}
    if isinstance(inj, dict) and isinstance(inj.get("analytic"), dict):
        floor = inj["analytic"].get("with_floor")
    if floor is None and r.get("noise_floor"):          # no injection run: the rule's own threshold
        from .flicker import ABOVE
        floor = ABOVE * float(r["noise_floor"])
    out.update(beats=beats, finding=r.get("finding"), smallest_beat_seen=round(floor, 2) if floor else None)
    seen = f"; only a beat over {100 * floor:.0f}% of its brightness would have shown" if floor else ""
    if beats is True:
        held, b = held_beat(r)
        if b is not None:
            out.update(whole_track_beats=b.get("whole_passes"), windows_passing=b.get("windows_passing"),
                       windows=b.get("windows"), windows_apart=b.get("windows_apart"))
        out["held"] = held
        if held:
            return dict(out, outcome=FAIL, reading=f"its brightness beats across the video: {r.get('finding')}")
        where = (f" ({b['windows_passing']} of {b['windows']} windows)" if b and b.get("windows") else "")
        return dict(out, outcome=PASS, reading=(
            f"no beat across the video: a beat in one stretch only{where} is not counted, since a flame or chance over "
            f"many windows can make one{seen} ({r.get('finding')})"))
    if beats is False:
        return dict(out, outcome=PASS, reading=f"no beat of its own{seen}")
    return dict(out, outcome=CANNOT, reading="the flicker test had no power on this clip")


# ---- the verdict --------------------------------------------------------------------------------
def flat(tests):
    """The tests in order, each followed by its parts (T4's T4a and T4b)."""
    for t in tests:
        yield t
        yield from t.get("parts", ())


def verdict(tests):
    """A strong test passing and none failing: tentative drift. Any failure: not drifting. (T3 fails only on a beat
    that holds across the video, `test_beat`.) A test with parts (T4) is judged by them: a failing part is named, and
    a passing tracer part (T4a) is the strong test."""
    fails = [t for t in flat(tests) if t["outcome"] == FAIL and not t.get("parts")]
    if fails:
        return "not drifting", "; ".join(f"{t['test']}: {t['reading']}" for t in fails)
    strong = [t for t in flat(tests) if t["test"] in STRONG and t["outcome"] == PASS
              and t.get("tracer_depth", "same") == "same"]
    if strong:
        return ("consistent with wind-borne drift (tentative)",
                "passed " + ", ".join(t["test"] for t in strong) + " and failed none; it names no object")
    return "cannot say", "no strong test (T2, or T4a with a tracer at the object's depth) passed"


def measure(fps, L=None, remains=None, pieces=(), delta_deg=None, comotion=None, tracer_depth="same",
            slant=None, horiz=None, own=None, bearings=None, heading_deg=None, winds=(), speeds=(10.0, 25.0, 50.0),
            air_min_kn=None, air_max_kn=None, flicker=None, seed=20261021,
            out=None, say=print, platform=None, los=None, los_sigma=(0.3, 0.1), observed_winds=None, ground_m=None,
            when=None):
    """Every test the inputs allow, and the verdict. Returns a Found with fields `tests` and `verdict`. T1 and T2 come
    from the ranges (slant, horiz, own, bearings, heading_deg) or, given `platform` and `los` (`read_platform`,
    `read_los`), from the aircraft's own track and the lines of sight."""
    rng = np.random.default_rng(seed)
    track = None
    # T1 first: the ranges, or the lines of sight, give the depression the others use
    if platform is not None and los is not None:
        R = rays(platform, los, fps)
        track = fit_track(R, los_sigma, ground_m, rng) if len(R["t"]) >= 6 else None
        t1 = test_vertical_track(track)
        delta_r = track["depression_deg"] if track else None
    else:
        t1, delta_r = test_vertical(slant, horiz, own, fps)
    if delta_deg is None and delta_r is not None:
        delta_deg = delta_r
    # T4's parts before T2's fit, as when they were T1 and T2, so the random generator is drawn in the same order
    rels, accel, band, f = [], None, None, None
    if remains is not None:
        rels = [relative(remains, p, fps, rng) for p in pieces]
        f = fall(remains, fps, rng)
        if L:
            accel = (f["accel_px_s2"] / L[0], f["accel_err"] / L[0])
            if f["band_accel_px_s2"] is not None:            # the remains' own band, in the object's length
                band = dict(accel_L=f["band_accel_px_s2"] / L[0], accel_err_L=f["band_accel_err_px_s2"] / L[0],
                            accel_max_L=f["band_accel_max_px_s2"] / L[0] if f["band_accel_max_px_s2"] is not None else None)
    t4a = test_tracer(L or (1.0, 1.0), rels, delta_deg, tracer_depth, comotion)
    if remains is not None and L:
        t4a["pieces_fall_L_per_s"] = [round(fall(p, fps, rng)["rate_px_s"] / L[0], 2) for p in pieces]
    t4b = test_wreck(*(accel or (None, None)), delta_deg, band=band)
    if f is not None and f["band_range_s"] is not None:
        t4b.update(band_range_s=round(f["band_range_s"], 2), band_nugget_px=round(f["band_nugget_px"], 3),
                   band_light=f["band_light"], bootstrap_block_s=round(BLOCK / fps, 2))
    line = None
    if platform is not None and los is not None:                    # T2 from the aircraft's own track
        own_w = aircraft_wind(platform, fps)
        tw = test_wind_track(track, track_winds(track["height_m"], ground_m, winds, when, observed_winds, own_w)
                             if track else [])
        if own_w:
            tw["aircraft_wind"] = dict(from_deg=round(_from(own_w["w"]), 1), speed_m_s=round(float(np.hypot(*own_w["w"])), 2),
                                       err_m_s=round(own_w["err_m_s"], 2), airspeed_kn=round(own_w["airspeed_m_s"] / KN, 1),
                                       heights_m=own_w["heights_m"], heading_turn_deg=round(own_w["heading_turn_deg"], 0))
    else:                                                           # T2 from the ranges
        if slant is not None and horiz is not None and bearings is not None:
            line = fit_line(slant, horiz, bearings, fps, rng)
        if line is not None and heading_deg is not None and winds and own is not None:
            air_m = float(np.mean(own[1]))
            obj_m = air_m - float(t1.get("height_below_m") or 0)
            tw = test_wind(line, heading_deg, wind_samples(winds, obj_m, air_m), speeds, air_min_kn, air_max_kn)
            tw.update(object_height_m=round(obj_m, 0), aircraft_height_m=round(air_m, 0))
        elif line is not None:
            tw = dict(test="T2", question="does its motion relative to the aircraft fit the winds?", outcome=CANNOT,
                      reading="it needs the aircraft's heading, its height (sea readings) and archived winds as well")
        else:
            tw = test_wind(None, 0.0, [])
    tests = [t1, tw, test_beat(flicker), test_other([t4a, t4b])]
    v, why = verdict(tests)
    fields = dict(tests=tests, verdict=v, why=why, depression_deg=delta_deg)
    if track is not None:
        fields["ground_path"] = track
    if line is not None:
        fields["relative_line"] = {k: line[k] for k in ("speed_m_s", "speed_err_m_s", "toward_deg", "toward_err_deg",
                                                       "v_m_s", "v_err_m_s", "r0_m", "t0_frame", "chi2_dof",
                                                       "range_rms_m")}
    files = []
    if out:
        p = Path(f"{out}_drift.json")
        p.write_text(json.dumps(fields, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)),
                     encoding="utf-8")
        files.append(str(p))
    result = {t["test"]: f"{t['outcome']}: {t['reading']}" for t in flat(tests)}
    result["verdict"] = f"{v}: {why}"
    no_power = [(t["test"], t["reading"]) for t in tests if t["outcome"] == CANNOT]
    return Found("drift", result, fields, no_power=no_power, files=files)


def said(fields):
    L = ["\n| test | question | outcome |", "|---|---|---|"]
    for t in flat(fields["tests"]):
        L.append(f"| {t['test']} | {t['question']} | **{t['outcome']}** |")
    L.append("")
    for t in flat(fields["tests"]):
        L.append(f"{t['test']} {t['outcome']}: {t['reading']}")
    g = fields.get("ground_path")
    if g:
        above = f", {g['above_ground_m']:.0f} m above the ground" if g.get("above_ground_m") is not None else ""
        L.append(f"\nthe path from {g['readings']} lines of sight (the line of sight turned {g['los_turn_deg']:.0f} deg): "
                 f"{g['speed_m_s']:.2f} m/s toward {g['toward_deg']:.1f} deg (two errors {2 * g['velocity_err_m_s']:.2f}), "
                 f"climb {g['climb_m_s']:+.2f} +- {g['climb_err_m_s']:.2f} m/s, {g['height_m']:.0f} m above the sea{above}; "
                 f"reduced chi-square {g['chi2_dof']:.2f}, rms {g['rms_az_deg']:.2f} deg azimuth, {g['rms_dep_deg']:.2f} "
                 f"depression; {g['range_m'][0] / 1e3:.1f}-{g['range_m'][1] / 1e3:.1f} km away")
    L.append(f"\nVERDICT: {fields['verdict']} -- {fields['why']}")
    return L


# ---- CLI ---------------------------------------------------------------------------------------
def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--size-px", help="the object's length on the screen, px; two values (just before, smallest) "
                                      "give the range of L")
    ap.add_argument("--depression", type=float, help="the line of sight's depression, deg (from the ranges if given)")
    ap.add_argument("--remains", help="T4 (other evidence): track of the remains after a strike (frame,x,y; positions "
                                      "held on the display)")
    ap.add_argument("--pieces", help="T4a: tracks of pieces it shed, comma-separated, in the remains' frame")
    ap.add_argument("--comotion", help="T4a: the --json envelope of `mcdonald comotion` (motion against the cloud "
                                       "field)")
    ap.add_argument("--tracer-depth", choices=["same", "layer", "unknown"], default="same",
                    help="where the tracer is: shed by the object (same), the cloud it was seen inside (layer), unknown")
    ap.add_argument("--slant", help="T1/T2: slant range readings (frame,value_m[,frame_err])")
    ap.add_argument("--horizontal", help="T1/T2: horizontal range readings (frame,value_m[,frame_err])")
    ap.add_argument("--own-height", help="T1: the aircraft's height above the sea (frame,value_m)")
    ap.add_argument("--bearings", help="T2: the line of sight's true bearing (frame,value[,frame_err]) from the pointer")
    ap.add_argument("--heading", type=float, help="T2: the aircraft's true heading, deg")
    ap.add_argument("--winds", help="T2: Open-Meteo archive JSON files, comma-separated")
    ap.add_argument("--speeds", default="10,25,50", help="T2: drone airspeeds to test, m/s")
    ap.add_argument("--airspeed-kn", help="T2: the aircraft's airspeed range, min,max kn")
    ap.add_argument("--platform", help="T1/T2 from the aircraft's own track: its position per reading (frame,lat,lon,"
                                       "alt_m[,heading_deg]; decimal degrees, west and south negative)")
    ap.add_argument("--los", help="T1/T2 from the aircraft's own track: the line of sight per reading (frame,az_deg,"
                                  "dep_deg, or frame,tgt_lat,tgt_lon,tgt_elev_m the ground point the display prints; "
                                  "optionally off_right_deg,off_down_deg, the object off the boresight)")
    ap.add_argument("--los-sigma", default="0.3,0.1", help="the lines of sight's errors a priori, azimuth,depression deg")
    ap.add_argument("--obs-winds", help="T2 from the track: observed winds (source,height_m above the sea,from_deg,"
                                        "speed_m_s), e.g. a METAR, a sounding")
    ap.add_argument("--ground-m", type=float, help="the ground's height above the sea under the object, m")
    ap.add_argument("--when", help="the time of the clip (ISO, UTC): the model winds' hours within one of it")
    ap.add_argument("--flicker", help="T3: the --json envelope of `mcdonald flicker` on the object")
    ap.add_argument("--fps", type=float, help="frames per second (default: the video's)")
    ap.add_argument("--out", metavar="PREFIX", help="write <PREFIX>_drift.json")
    ap.add_argument("--json", action="store_true", help="print the envelope as JSON on stdout")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        found = _main(args)
    if args.json:
        emit(found.envelope("drift", inputs_of(args), None, said=lines))
    return 0


def _series(path, value=("value_m", "value", "m")):
    return read_series(path, value) if path else None


def _main(args):
    from .forensics import resolve
    video, tag, _ = resolve(args.video)
    args.video = str(video)
    fps = args.fps
    if fps is None:
        from .clip import probe
        fps = float(probe(video)["fps"])
    L = None
    if args.size_px:
        v = [float(x) for x in args.size_px.split(",")]
        L = (v[0], min(v))
    remains = read_track(args.remains) if args.remains else None
    pieces = [read_track(p) for p in args.pieces.split(",")] if args.pieces else []
    comot = json.loads(Path(args.comotion).read_text(encoding="utf-8")) if args.comotion else None
    bearings = read_series(args.bearings, ("value", "bearing_deg", "value_deg"), ("err_deg", "err"), 0.1) \
        if args.bearings else None
    winds = args.winds.split(",") if args.winds else []
    amin = amax = None
    if args.airspeed_kn:
        amin, amax = (float(x) for x in args.airspeed_kn.split(","))
    if bool(args.platform) != bool(args.los):
        raise SystemExit("--platform and --los go together")
    if args.platform and (args.slant or args.horizontal):
        raise SystemExit("T1/T2 come from the ranges or from the aircraft's own track, not both")
    observed = read_rows(args.obs_winds) if args.obs_winds else None
    own = read_series(args.own_height, ("value_m", "value"), ("err_m", "err"), 10.0) if args.own_height else None
    found = measure(fps, L, remains, pieces, args.depression, comot, args.tracer_depth, _series(args.slant),
                    _series(args.horizontal), own, bearings, args.heading, winds,
                    tuple(float(x) for x in args.speeds.split(",")), amin, amax,
                    json.loads(Path(args.flicker).read_text(encoding="utf-8")) if args.flicker else None, out=args.out,
                    platform=read_platform(args.platform) if args.platform else None,
                    los=read_los(args.los) if args.los else None,
                    los_sigma=tuple(float(x) for x in args.los_sigma.split(",")), observed_winds=observed,
                    ground_m=args.ground_m, when=args.when)
    print("\n".join(said(found.fields)))
    return found


if __name__ == "__main__":
    raise SystemExit(main())
