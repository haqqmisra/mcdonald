"""What survives the missing variables: the tests a track passes or fails with no range, no field of view and no
platform speed (ROADMAP 0.4, objective 3; the kinematic notes of 2026-08-05/06).

The Technical Note's four unknowns -- the field of view, the range, the aspect angle and the platform's own
motion -- enter the observables as multiplicative scale factors: the field of view turns pixels into angles, the
range turns angles into metres. So ratios of image quantities with equal powers of each cancel them exactly, and
what is left is the part of kinematics that survives the missing calibration. Three of it here, each a fact of the
track rather than of a guess:

- **The projective constant-velocity test** (`fit`). For a pinhole camera an object moving in a straight line at
  constant velocity draws a straight line in the picture, and its distance from that line's vanishing point goes as
  1/(t_z - t), t_z the instant it crosses the camera's plane -- at any range, any field of view, any speed. Both
  halves are falsifiable on the track alone. The model has five parameters (the line, the vanishing point on it, a
  scale and t_z); it is held against constant image speed (four: motion across the line of sight at a fixed range)
  and a free quadratic in each coordinate (six: no physics). Those three are compared only with one another, which
  says which is least wrong, not whether any is right; so the one chosen is then held to the track's own jitter (the
  larger of the speed band's nugget and the nugget of its covariance fitted to the model's residual), and it *fits*
  only within NUGGETS times it -- otherwise it describes the track's trend, and the rest of the track is something
  else's: the camera's motion, or the object's own. Of the 25 recorded tracks the three models passed, 24 miss the
  one chosen by 4.6 to 234 times their jitter (the pure-mathematics survey, 2026-10-29, M1: PR077's object loops
  through 705° and passed "no closing seen"; PR135's members passed "receding").
  Where it fits -- as well as the quadratic with one parameter fewer, better than constant speed, and to the
  jitter -- the track is consistent with constant velocity, and the time
  to go T = t_z - t_last is the speed in units of the range: v ≈ R / T at the last frame, within a few per cent
  for any field under about 50° (the secants of the vanishing point's and the object's angles off boresight nearly
  cancel; with k given, exactly). With k the aspect angle at the last frame is the angle between the object and the
  vanishing point (`psi_deg`; the kinematic notes' identity Π_θ = tan ψ). t_z's error is the track's own covariance
  carried through the fit (`tz_err`, the survey's M5). PR43 passes it: straight to 1.5 px rms, T = 0.91 ± 0.10 s on its
  case file's track, the vanishing point inside the frame, at its jitter. Where it gives no time -- no closing
  seen, or the trend only -- the band's change of speed along the track still bounds how fast the depth changed
  under the model (`depth_bound`: |Zdot / Z| = 1 / |T|, the survey's M5), "the track says nothing of how its range
  changed" made a number.
- **The turn number** (`turn`): the track's sagitta against its length and the object's width, Π_L = 8 D s / L².
  A straight 3-D line at constant velocity projects to a straight image line at any range, so image curvature is
  not inertial by construction, and r_turn / D = 1 / Π_L is the turn radius in body widths -- the one kinematic
  statement that survives every missing calibration. Neither PR43's nor PR113's object turned: r_turn > 1,900 and
  > 380 body widths. That radius is the picture's: the tilt of the turn's plane makes it 0.15 to 8.5 times the turn's
  own, nine times in ten, and the words say so. Past 150° of turn the track is read whole (`ellipse`, the survey's
  M4): the affine image of uniform circular motion is an ellipse whose semi-major axis is the radius unforeshortened,
  so r_turn / D, the tilt, the rate, and the speed and acceleration in body widths come exact. Traps: D must be the object's width across its travel (a streak's length overstates it); a
  camera that translates puts parallax into the track (a pan does not: a rotation keeps straight lines straight);
  lens distortion curves everything near the frame's edge.
- **The smear number** (`smear`): the image displacement per frame over the object's width. A property of the
  observation, not the object: above 1 the object streaks within one frame; above 2 an interlaced source's two
  fields separate and masquerade as two objects (PR113's retracted "formation").

Each returns plain values the kinematics stage records and the report prints as facts.
"""
import math

import numpy as np
from scipy import optimize

FAR = 20.0           # t_z beyond this many track lengths from the track: no closing seen, the fit is constant speed's
HAIR = 0.01          # Π_L under this (a turn radius over 100 body widths) is a hair off straight: the camera's or the lens's as easily as the object's
# the turn radius in body widths that known things fly (the kinematic notes, from v^2 / (a D)): the scale the number is read on
TURNS_OF = [("a quadcopter at 2 g", 15), ("a pigeon's 2-g turn", 33), ("an airliner at 1.5 g", 60), ("a fighter at 9 g", 47)]
CLOSING_GAIN = 0.8   # the projective fit's rms must be under this share of constant image speed's to say it closes
QUAD_SLACK = 1.25    # and no more than this times the free quadratic's: it describes the track as the quadratic does
NUGGETS = 4.0        # and the model chosen fits only with its rms within this many times the track's own jitter; else it describes the trend
JITTER_FLOOR = 0.1   # px a coordinate: the least jitter a track is held to (a drawn or interpolated track has none; a centroid is read to about this)
DEPTH_Z = 1.959964   # the depth bound's sigmas: two-sided 95 %
DEPTH_SHARE = 0.10   # the share of the change of speed added to its error: the band's end rates lag a steep curve (see `depth_read`)
DEPTH_X = 4.0        # no bound where the change of speed, with its error, passes this many times the mean speed
DEPTH_G = 1.75       # nor where the ends' geometric mean is further than this factor from the mean speed, as the model has them equal
ARC_DEG = 150.0      # a turn is read as an ellipse once it sweeps this much, its fitted path's heading too; under it, by its sagitta
LOOP_GAIN = 0.8      # and only where the ellipse describes the track this much better than a free quadratic does (rms)
W_TURNS = 3.0        # the ellipse's scan of the turn rate reaches this many turns a second (or 0.8 of the frame rate's Nyquist)
# a turn's tilt (the pure-mathematics survey, §1.3, §6.5): the picture's radius of curvature over the turn's own is
# (sin²φ + cos²i cos²φ)^1.5 / |cos i| at the circle's phase φ, i the tilt of its plane -- 0.152 to 8.50 (5-95 %, median
# 1.02) with the plane's normal isotropic (cos i uniform) and the phase uniform, so the turn's own radius is 0.118 to
# 6.57 times the picture's; a turn looks ten times straighter than it is for 4.25 % of the ways its plane can lie and
# forty times for 1.06 % (a 4000 x 4000 grid; test_reduction recomputes them on a coarser one)
TILT_OWN = (0.118, 6.57)
TILT_STRAIGHTER = ((10, 0.0425), (40, 0.0106))


def _points(track, fps, t0=None, t1=None, n0=None, n1=None):
    if isinstance(track, dict):
        a = np.array([[n, xy[0], xy[1]] for n, xy in sorted(track.items())], float)
    else:
        a = np.asarray(track, float)
    a = a[np.isfinite(a[:, 1]) & np.isfinite(a[:, 2])]
    t = (a[:, 0] - 1) / float(fps)
    s = np.ones(len(a), bool)
    if t0 is not None:
        s &= t >= t0
    if t1 is not None:
        s &= t < t1
    if n0 is not None:
        s &= a[:, 0] >= n0
    if n1 is not None:
        s &= a[:, 0] <= n1
    return a[s, 0], t[s], a[s, 1:3]


def line_of(p):
    """(centre, unit direction u, unit normal w) of the straight line through the points, by their principal axis."""
    c = p.mean(axis=0)
    q = p - c
    _, _, vt = np.linalg.svd(q, full_matrices=False)
    u = vt[0]
    if len(p) > 1 and np.dot(q[-1] - q[0], u) < 0:
        u = -u                                            # pointing the way the object went
    return c, u, np.array([-u[1], u[0]])


def _model(theta, t):
    """Image positions under the projective constant-velocity model: theta = (vx, vy, ang, a, tz)."""
    vx, vy, ang, a, tz = theta
    u = np.array([math.cos(ang), math.sin(ang)])
    d = a / (tz - t)
    return np.c_[vx + u[0] * d, vy + u[1] * d]


def _fit_along(s, t, span):
    """s(t) = s_vp + a / (t_z - t) on the line: t_z by a grid either side of the track (sixty points a side, a
    thirteenth apart in log), (s_vp, a) linear at each, then the best refined in t_z. Returns (s_vp, a, t_z, rms)."""
    best = None
    T = span or 1.0
    grid = np.r_[t[-1] + T * np.logspace(-2, math.log10(FAR), 60), t[0] - T * np.logspace(-2, math.log10(FAR), 60)]

    def at(tz):
        X = np.c_[np.ones(len(t)), 1.0 / (tz - t)]
        coef = np.linalg.lstsq(X, s, rcond=None)[0]
        r = s - X @ coef
        return float(coef[0]), float(coef[1]), float(tz), float(np.sqrt(np.mean(r ** 2)))
    for tz in grid:
        got = at(tz)
        if best is None or got[3] < best[3]:
            best = got
    tz = best[2]
    side = 1.0 if tz > t[-1] else -1.0                      # the crossing is after the track, or before it
    lo, hi = (t[-1] + 1e-3 * T, tz + 0.5 * abs(tz - t[-1])) if side > 0 else (tz - 0.5 * abs(t[0] - tz), t[0] - 1e-3 * T)
    res = optimize.minimize_scalar(lambda z: at(z)[3], bounds=(min(lo, hi), max(lo, hi)), method="bounded",
                                   options=dict(xatol=1e-4 * T))
    got = at(float(res.x))
    return got if got[3] <= best[3] else best


def band_of(track, fps, t0=None, t1=None, n0=None, n1=None):
    """The track's speed band (`kinematics.speed_band`: a line, a Matérn wander and a nugget fitted to the track by
    REML), whose nugget is the track's own jitter and whose change of speed bounds how its depth changed; {} where it
    is not fitted (under its BAND_MIN points, or a covariance that will not fit)."""
    from . import kinematics as kin
    try:
        got = kin.speed_band(track, fps, t0, t1, n0, n1)
    except Exception:                            # noqa: BLE001 -- the test is then relative only, and says so
        got = None
    return got[0] if got else {}


def residual_jitter(frames, t, p, r, fps):
    """The jitter left in a model's residual r (n x 2) of the track's points p, (sx, sy) px: the nugget of the band's
    covariance (a line, a Matérn wander and a nugget, REML: `kriging.Model`) fitted to the residual of the model
    chosen rather than to the track, so that a steep trend cannot take a share of it -- the band's own fit of a drawn object closing on the
    camera half a second after its last frame read its nugget at 0.7 of the jitter drawn, chasing the curve with a
    short wander. Exact repeats of the previous frame's point are dropped, as the band drops them; a longer track is read on
    its middle BAND_NMAX points. None under BAND_MIN points, or where the covariance will not fit."""
    from . import kinematics as kin, kriging as kg
    keep = np.r_[True, ~((np.diff(frames) == 1) & np.all(np.diff(p, axis=0) == 0, axis=1))]
    t, r = t[keep], r[keep]
    if len(t) < kin.BAND_MIN:
        return None
    if len(t) > kin.BAND_NMAX:
        a = (len(t) - kin.BAND_NMAX) // 2
        t, r = t[a:a + kin.BAND_NMAX], r[a:a + kin.BAND_NMAX]
    try:
        return tuple(float(math.sqrt(kg.Model(t, r[:, j], float(t.mean()), dt=1.0 / float(fps)).theta[2])) for j in (0, 1))
    except Exception:                            # noqa: BLE001 -- the band's nugget stands in, and the record says so
        return None


def tz_err(t, s, s_vp, a, tz, fps):
    """t_z's standard error, s, under the track's own covariance (the pure-mathematics survey's M5, its other half;
    2026-10-29/30). The fit along the line, s(t) = s_vp + a / (t_z - t), is least squares; the covariance of its
    residual -- a line, a Matérn wander and a nugget, fitted by REML as the speed band fits the track (`kriging.Model`;
    on the middle BAND_NMAX points of a longer track) -- is carried through it by the sandwich (J'J)^-1 J'ΣJ (J'J)^-1,
    J the fit's derivatives in (s_vp, a, t_z). With white residuals it is plain least squares' error, which the residual
    bootstrap it replaces also gave; where the residual has memory (a centroid that drifts for a few frames) the
    bootstrap, which resamples the points as if each were drawn alone, ran narrow -- on drawn approaches with AR(1)
    jitter at φ 0.6 its 16-84 % held the truth 39 % of the time and its 2.5-97.5 % 70 %; this holds it 68 and 91 %.
    The band's own change of velocity, the depth bound's route (`depth_bound`), was tried first and is no error for t_z:
    its end rates are the wander's, free of the model, so t_z's interval through v_end / v_start = ((T + L) / T)^2 came
    out six times too wide (it held the truth every time at one sigma) and, centred on the band's change, biased long
    (PR43: 2.2 s for the fit's 0.91). None under 6 points, or where the covariance will not fit."""
    from . import kinematics as kin, kriging as kg
    if len(t) < 6:
        return None
    J = np.c_[np.ones(len(t)), 1.0 / (tz - t), a / (tz - t) ** 2]
    r = s - (s_vp + a / (tz - t))
    a0 = (len(t) - kin.BAND_NMAX) // 2 if len(t) > kin.BAND_NMAX else 0
    sl = slice(a0, a0 + kin.BAND_NMAX)
    try:
        s2, ell, tau2 = kg.Model(t[sl], r[sl], float(t[sl].mean()), dt=1.0 / float(fps)).theta
        A = np.linalg.inv(J.T @ J)
    except Exception:                            # noqa: BLE001 -- no band is then given, as under six points
        return None
    S = kg.matern32(t[:, None] - t[None, :], s2, ell) + tau2 * np.eye(len(t))
    v = float((A @ J.T @ S @ J @ A)[2, 2])
    return math.sqrt(v) if v > 0 and math.isfinite(v) else None


def _T_from(v, dv, L):
    """T = t_z - t_last from the stretch's mean speed along the line, v, and the change of speed over it, dv, over its
    length L. Under the projective model the speed at the two ends is a / (T + L)^2 and a / T^2, and the mean speed, the
    stretch's chord over its length (the band's, its latent path's), a / (T (T + L)): exactly their geometric mean, so
    with r = (T + L) / T the ends are v / r and v r and r - 1 / r = dv / v. Positive closing (r > 1), negative receding,
    inf for no change. Every dv has its r: past twice the mean speed the split v -/+ dv / 2 this replaced went through
    zero, though nothing in the model stops there (r = 3.6 is a speed that grows 13x)."""
    x = dv / v
    r = x / 2.0 + math.sqrt(1.0 + x * x / 4.0)
    return math.inf if r == 1 else L / (r - 1.0)


def depth_read(band, z=DEPTH_Z, floor=0.0, t_z=None):
    """"No closing seen" as a bound (the pure-mathematics survey's M5, 2026-10-29): (the bound, None), (None, why there is
    none, in words), or (None, None) where the band has no change of velocity by axis. Under the projective model the
    speed along the line goes as a / (t_z - t)^2, so over the band's stretch of length L, ending at the last frame, the
    mean speed and the change of speed give T = t_z - t_last (`_T_from`), and 1 / |T| = |Zdot / Z| there: how fast the
    depth changed, as a share of itself a second. The band's change of velocity along the track (its kriged rate at the
    two ends, with the error the track's own covariance gives, so a wandering track widens it; at least `floor`, px/s, the
    error a free quadratic's curvature has, since a band whose REML finds no wander reads the velocity as unchanging to
    within nothing) within +-z sigmas bounds |T| from below on either side.

    Those end rates run short of a steep curve, as a smoothed rate at the end of its data does: drawn, the band's change
    read 0.92 of the truth at r = (T + L) / T = 1.2-1.5, 0.84 at 3.6, 0.72 at 6, with an error of 4-9 %. The split of the
    mean that `_T_from` replaced hid this by overshooting. So DEPTH_SHARE of the change joins the error, and the bound
    held the truth 95-99.7 % of the time from r = 0.4 to 3.6 at a nominal 95 % (it was 61 % at r 2.4, 27 % at 3.6). Three things
    give none. Past DEPTH_X times the mean speed no error is known to reach the truth (at r = 6 the bound held it one
    time in two). The model has the ends' geometric mean equal to the mean speed exactly, so a track whose ends are
    further from it than DEPTH_G (99 % of drawn straight flights lie within it at each r from 0.4 to 3.6) has ends that are not a straight
    flight's: a track looping over a short chord; PR077's reads 28 times it. And a bound of a closing trend is of that trend,
    so its change of speed must be the one that trend draws: `t_z`, its crossing, must give a change inside the band's.
    Fifteen airliners closing on a camera followed a T of 10-14 s, within 22 % of the truth, while the link hopping on
    their grown images read their change of speed anywhere from -3.1 to +5.2 times the mean, and without this seven of
    ten bounds missed the truth, by up to fifty times; with it, three stayed, and all held. Constant image speed is held to no
    change this way: a change it cannot see is what the bound is for (drawn at r 1.04, the band reads it and the test does not).

    The bound: dict(rate_max_per_s, T_closing_min_s, T_receding_min_s (inf where that side is not reached), dv_px_per_s
    (along the track), dv_err_px_per_s, v_px_per_s, span_s, z)."""
    if not band or band.get("dv_xy") is None or not band.get("v_mean_px_per_s"):
        return None, None
    v, L = float(band["v_mean_px_per_s"]), float(band["t1"] - band["t0"])
    if L <= 0:
        return None, None
    ux, uy = band["vx_mean"] / v, band["vy_mean"] / v
    dv = band["dv_xy"][0] * ux + band["dv_xy"][1] * uy
    e = math.hypot(max(math.hypot(band["dv_err_xy"][0] * ux, band["dv_err_xy"][1] * uy), float(floor)), DEPTH_SHARE * dv)
    lo, hi = dv - z * e, dv + z * e
    ends = [(band.get(end) or (None, None))[1] for end in ("v_start", "v_end")]
    if all(ends) and not 1.0 / DEPTH_G <= math.sqrt(ends[0] * ends[1]) / v <= DEPTH_G:
        return None, (f"no bound on how fast its depth changed: its speed at the two ends ({ends[0]:.0f} and {ends[1]:.0f} px/s) is not "
                      f"what a straight flight at a steady speed draws about its mean ({v:.0f} px/s), so they are the track's wander's")
    if max(abs(lo), abs(hi)) > DEPTH_X * v:
        return None, (f"no bound on how fast its depth changed: its speed along the track changed by {dv:+.0f} ± {e:.0f} px/s on a mean "
                      f"of {v:.0f}, more than {DEPTH_X:g} times over, and the speed at a track's ends is not read that well")
    if t_z is not None:
        r = (t_z - band["t0"]) / (t_z - band["t1"])
        drawn = v * (r - 1.0 / r)
        if not lo <= drawn <= hi:
            return None, (f"no bound on how fast its depth changed: its speed along the track changed by {dv:+.0f} ± {e:.0f} px/s where the "
                          f"trend it follows changes by {drawn:+.0f}, so its two ends are not that trend's")
    close, recede = abs(_T_from(v, hi, L)) if hi > 0 else math.inf, abs(_T_from(v, lo, L)) if lo < 0 else math.inf
    return dict(rate_max_per_s=max(1.0 / close, 1.0 / recede), T_closing_min_s=close, T_receding_min_s=recede,
                dv_px_per_s=float(dv), dv_err_px_per_s=float(e), v_px_per_s=v, span_s=L, z=float(z)), None


def depth_bound(band, z=DEPTH_Z, floor=0.0):
    """The bound of `depth_read`, or None."""
    return depth_read(band, z, floor)[0]


def fit(track, fps, k=None, centre=None, t0=None, t1=None, n0=None, n1=None, boot=True, band=None):
    """The projective constant-velocity test on a track. Returns None under 6 points; else a dict:

    `straight_rms`, `straight_max` (px): how straight the image track is, off its principal line;
    `vp` (x, y): the vanishing point; `t_z` (s), `t_z_err` (s: its error under the track's own covariance, `tz_err`)
    and `t_z_band` (16-84 %, t_z within one of it; both left out with `boot` false, the name of the residual bootstrap
    they replaced), `T` = t_z - t_last (the time to go; negative where the object recedes from a crossing in the
    past); `rms`, `rms_const`, `rms_quad`
    (px): this model's residual against constant image speed's and a free quadratic's; `closing`: True where the
    model describes the track (within QUAD_SLACK of the quadratic) and beats constant speed by CLOSING_GAIN, False
    where constant speed fits as well (no closing seen: t_z is beyond FAR track lengths, and the track says nothing
    of the range's change), None where neither describes it (the track is not straight, or not constant velocity);
    `v_over_R` (per s): the speed at the last frame in units of its range, R / T, exact with `k` and `centre`
    (`sec` the correction applied), within a few per cent without; with `k`: `psi_deg`, the angle between the
    object at its last frame and the vanishing point, which under the hypothesis is the aspect angle there, and
    `beta_vp_deg`, the vanishing point's angle off boresight.

    The absolute check: the track's own position noise is read twice -- the nugget of the band's covariance fitted to
    the chosen model's residual (`residual_jitter`), and the nugget of `band`, the track's speed band over the same
    stretch (`kinematics.speed_band`'s first value; fitted here, `band_of`, when None; {} where there is none) -- and
    the larger taken (`jitter_from` names it): the band's own fit reads it low on a steep trend, which its wander
    chases, and the residual's on a short track whose jitter has a frame or two of memory (drawn constant-velocity
    tracks, 400 a case: at NUGGETS 4 neither reading alone holds every case to 5 % false alarms, the larger does).
    `jitter_px` is the rms a point is off by that noise alone (both coordinates, each at least JITTER_FLOOR), `misfit`
    the chosen model's rms over it (the projective model's where `closing` is True, constant speed's where False), and
    `fits` True within NUGGETS, False beyond it (the model describes the track's trend only) or where `closing` is
    None, and None where no jitter is known. `depth`: `depth_read`'s bound of the band where the model is chosen and gives
    no time to the camera's plane (no closing seen, or the trend only) -- how fast its depth could have changed, if it
    flew straight at a steady speed; `depth_none`, why there is none, in words, where the band was read and gave none."""
    frames, t, p = _points(track, fps, t0, t1, n0, n1)
    if len(t) < 6:
        return None
    c, u, w = line_of(p)
    q = p - c
    s, across = q @ u, q @ w
    span = float(t[-1] - t[0])
    straight = dict(straight_rms=float(np.sqrt(np.mean(across ** 2))), straight_max=float(np.abs(across).max()))
    # the three models
    cs = np.polyfit(t, s, 1)
    rms_const = float(np.sqrt(np.mean((s - np.polyval(cs, t)) ** 2 + across ** 2)))
    qx, qy = np.polyfit(t, p[:, 0], 2), np.polyfit(t, p[:, 1], 2)
    rms_quad = float(np.sqrt(np.mean((p[:, 0] - np.polyval(qx, t)) ** 2 + (p[:, 1] - np.polyval(qy, t)) ** 2)))
    s_vp, a_line, tz_line, _ = _fit_along(s, t, span)
    ang = math.atan2(u[1], u[0])
    vp0 = c + u * s_vp
    theta0 = [vp0[0], vp0[1], ang, a_line, tz_line]

    def resid(theta):
        return (_model(theta, t) - p).ravel()
    sol = optimize.least_squares(resid, theta0, method="lm", max_nfev=2000)
    theta = sol.x
    rms = float(np.sqrt(np.mean(sol.fun ** 2) * 2))      # per point, both coordinates
    vx, vy, ang, a, tz = (float(v) for v in theta)
    T = tz - float(t[-1])
    far = abs(tz - float(t[-1])) > FAR * span and abs(tz - float(t[0])) > FAR * span
    if far or rms >= CLOSING_GAIN * rms_const:
        closing = False if rms_const <= QUAD_SLACK * rms_quad or far else None
    else:
        closing = True if rms <= QUAD_SLACK * rms_quad else None
    # the absolute check: the model chosen, held to the track's own jitter
    if band is None:
        band = band_of(track, fps, t0, t1, n0, n1)
    resid = ((p - _model(theta, t)) if closing else np.c_[s - np.polyval(cs, t), across]) if closing is not None else None
    # the larger of two readings of the jitter: each reads it low on a track the other reads well (drawn, 2026-10-29)
    yards = {name: math.hypot(*(max(float(j), JITTER_FLOOR) for j in got)) for name, got in
             (("the model's residual", residual_jitter(frames, t, p, resid, fps) if resid is not None else None),
              ("the speed band's nugget", (band or {}).get("nugget_px"))) if got}
    jitter_from = max(yards, key=yards.get) if yards else None
    yard = yards.get(jitter_from)
    chosen = rms if closing is True else rms_const if closing is False else None
    misfit = chosen / yard if chosen is not None and yard else None
    fits = False if closing is None else None if misfit is None else bool(misfit <= NUGGETS)
    # t_z's error: the fit along the line, its residual's own covariance carried through it (none where the model
    # describes only the trend, which gives no t_z)
    tz_sd = tz_err(t, s, s_vp, a_line, tz_line, fps) if closing and fits is not False and boot else None
    tz_band = [tz - tz_sd, tz + tz_sd] if tz_sd else None
    # the change of speed along the line a free quadratic reads, its error if its residual were white: the depth bound's
    # floor, where the band's REML puts the wander at nothing and so the velocity's change at nothing to within nothing
    X = np.c_[np.ones(len(t)), t - t.mean(), (t - t.mean()) ** 2]
    coef, *_ = np.linalg.lstsq(X, s, rcond=None)
    res = s - X @ coef
    var = float(res @ res) / max(len(t) - 3, 1)
    dv_floor = 2.0 * span * math.sqrt(max(var * np.linalg.inv(X.T @ X)[2, 2], 0.0))
    depth, depth_none = (depth_read(band, floor=dv_floor, t_z=tz if closing else None)
                         if closing is False or (closing and fits is False) else (None, None))
    out = dict(n=int(len(t)), t_first=float(t[0]), t_last=float(t[-1]), **straight, vp=[vx, vy], t_z=tz, t_z_err=tz_sd, t_z_band=tz_band,
               T=T, rms=rms, rms_const=rms_const, rms_quad=rms_quad, closing=closing, jitter_px=yard, jitter_from=jitter_from,
               misfit=misfit, fits=fits,
               depth=depth, depth_none=depth_none,
               direction_deg=float(math.degrees(math.atan2(math.cos(ang) * np.sign(a), -math.sin(ang) * np.sign(a))) % 360))
    if closing:
        sec = 1.0
        if k and centre is not None:
            cx, cy = centre
            beta_vp = math.atan(math.hypot(vx - cx, vy - cy) / k)
            beta_obj = math.atan(math.hypot(p[-1, 0] - cx, p[-1, 1] - cy) / k)
            sec = (1.0 / math.cos(beta_vp)) * math.cos(beta_obj)
            # the angle between the object's ray and the vanishing point's: the aspect angle under the hypothesis
            ray = lambda x, y: np.array([(x - cx) / k, (y - cy) / k, 1.0]) / math.hypot((x - cx) / k, (y - cy) / k, 1.0)
            cosang = float(np.clip(np.dot(ray(vx, vy), ray(p[-1, 0], p[-1, 1])), -1.0, 1.0))
            psi = math.degrees(math.acos(cosang))
            out.update(beta_vp_deg=math.degrees(beta_vp), psi_deg=psi if T > 0 else 180.0 - psi)
        out.update(v_over_R=abs(sec / T) if T != 0 else None, sec=sec)
    return out


def _ellipse_at(t, p, w):
    X = np.c_[np.ones(len(t)), t, np.cos(w * t), np.sin(w * t)]
    coef, *_ = np.linalg.lstsq(X, p, rcond=None)
    return coef, float(np.sqrt(np.mean(np.sum((p - X @ coef) ** 2, axis=1)))), X


def ellipse(t, p, fps):
    """The turn read whole (the pure-mathematics survey's M4, 2026-10-29/30): a body going round a circle at a steady
    rate ω, seen by an affine camera at any range, field of view and tilt of the circle's plane, draws x(t) = c + u t +
    a cos ωt + b sin ωt -- the affine image of uniform circular motion, u letting the circle drift with the air (a
    thermalling bird draws a trochoid). ω by a scan (600 rates, log-spaced from an eighth of a turn over the track to
    W_TURNS a second, or 0.8 of the frame rate's Nyquist, the best refined by golden section); the rest is linear.
    The singular values of [a b] are the ellipse's semi-axes (Rytz's construction, by linear algebra): the major is the
    circle's radius unforeshortened -- the diameter parallel to the picture keeps its length -- and the minor over the
    major is |cos i|, i the tilt of its plane from facing the camera (the elementary half of Pohlke's theorem); ω is the
    same in every view. Returns None under 8 points; else dict(omega_rad_per_s, arc_deg (the phase swept over the
    track), heading_deg (how far the fitted path's own heading swings: a drift faster than the circle draws a wave, not
    a loop), major_px, major_err_px (at the fitted ω, its residual taken as white), minor_px, cos_i, tilt_deg,
    drift_px_per_s, rms_px)."""
    if len(t) < 8:
        return None
    t = np.asarray(t, float) - float(np.mean(t))
    span = float(t[-1] - t[0])
    w_lo, w_hi = math.pi / (4.0 * span) if span > 0 else 0.0, min(2.0 * math.pi * W_TURNS, 0.8 * math.pi * float(fps))
    if span <= 0 or w_hi <= w_lo:
        return None
    w = min(np.exp(np.linspace(math.log(w_lo), math.log(w_hi), 600)), key=lambda g: _ellipse_at(t, p, g)[1])
    lo, hi = w / 1.02, w * 1.02
    for _ in range(40):                                  # golden section on the bracket
        m1, m2 = lo + 0.382 * (hi - lo), lo + 0.618 * (hi - lo)
        if _ellipse_at(t, p, m1)[1] < _ellipse_at(t, p, m2)[1]:
            hi = m2
        else:
            lo = m1
    w = 0.5 * (lo + hi)
    coef, rms, X = _ellipse_at(t, p, w)
    sv = np.linalg.svd(coef[2:4].T, compute_uv=False)   # [a b], a coordinate a row
    var = float(np.sum((p - X @ coef) ** 2)) / max(2 * len(t) - 9, 1)
    cov = np.linalg.inv(X.T @ X)
    tt = np.linspace(t[0], t[-1], 4 * len(t))            # the fitted path's own velocity, four times as fine as the points
    v = coef[1][None, :] + w * (np.cos(w * tt)[:, None] * coef[3][None, :] - np.sin(w * tt)[:, None] * coef[2][None, :])
    ci = float(sv[1] / sv[0]) if sv[0] > 0 else 1.0
    return dict(omega_rad_per_s=float(w), arc_deg=float(math.degrees(w * span)),
                heading_deg=float(math.degrees(np.ptp(np.unwrap(np.arctan2(v[:, 1], v[:, 0]))))),
                major_px=float(sv[0]), major_err_px=float(math.sqrt(var * max(cov[2, 2], cov[3, 3]))), minor_px=float(sv[1]),
                cos_i=ci, tilt_deg=float(math.degrees(math.acos(min(ci, 1.0)))), drift_px_per_s=float(math.hypot(*coef[1])), rms_px=rms)


def turn(track, fps, width_px, t0=None, t1=None, n0=None, n1=None):
    """The turn in body widths, read two ways by how far the track turned.

    Past ARC_DEG of turn -- the phase the ellipse sweeps and its fitted path's own heading both that far (a drift
    faster than the circle draws a wave, whose heading never swings so far; the scan's least rate, an eighth of a turn,
    is where a short arc's ellipse goes when nothing fixes it), its minor axis three of its errors from nothing (it goes
    round, not back and forth along a line, which a turn seen edge-on and a sway draw alike), and the ellipse
    describing the track LOOP_GAIN better than a free quadratic does -- it is read whole (`ellipse`, the survey's
    M4): r_turn / D the ellipse's
    semi-major axis over the width, exact at any tilt, with the tilt, the turn rate ω, and the speed and the
    acceleration toward the centre in body widths, ω r / D and ω² r / D -- none of them foreshortened. A sagitta
    formula is for a small bend: on a drawn turn of 25 widths it read 12 over 286° and thousands over a whole circle,
    where the ellipse reads 25.0 at every tilt (the survey's §6.2).

    Under it, the turn number: the track's sagitta across its principal line (a quadratic across, s the sagitta of the
    arc over the whole length L), Π_L = 8 D s / L², and the turn radius in body widths r_turn / D = L² / (8 D s) -- the
    picture's, which the tilt of the turn's plane makes 0.15 to 8.5 times the turn's own (TILT_OWN; a short arc does
    not fix a circle, so no ellipse is read there).

    Returns None under 5 points or with no width; else dict(how ("ellipse" or "sagitta"), sagitta_px, sagitta_err_px,
    length_px, pi_L, r_turn_over_D, r_turn_over_D_low (the 95 % lower bound: the sagitta at its 95 % upper, or the
    ellipse's axis at its), sagitta_r_over_D (what the sagitta reads, whichever is used), bent (the sagitta three sigmas
    from zero, or a loop), turned (bent, and Π_L at least HAIR, or a loop), rms_quad_px (a free quadratic's in each
    coordinate against time), n, ellipse (`ellipse`'s dict where it is used, with r_turn_over_D_err,
    speed_widths_per_s and accel_widths_per_s2; else None))."""
    if not width_px or width_px <= 0:
        return None
    frames, t, p = _points(track, fps, t0, t1, n0, n1)
    if len(t) < 5:
        return None
    c, u, w = line_of(p)
    q = p - c
    s, across = q @ u, q @ w
    L = float(s.max() - s.min())
    if L <= 0:
        return None
    X = np.c_[np.ones(len(s)), s, s ** 2]
    coef, *_ = np.linalg.lstsq(X, across, rcond=None)
    r = across - X @ coef
    dof = max(len(s) - 3, 1)
    var = float(r @ r) / dof
    cov = var * np.linalg.inv(X.T @ X)
    sag = abs(float(coef[2])) * (L / 2.0) ** 2
    sag_err = float(math.sqrt(max(cov[2, 2], 0.0))) * (L / 2.0) ** 2
    sag95 = sag + 1.645 * sag_err
    pi_L = 8.0 * width_px * sag / L ** 2
    bent = bool(sag_err > 0 and sag > 3.0 * sag_err)
    D = float(width_px)
    tc = t - t.mean()
    rms_quad = float(np.sqrt(np.mean(sum((p[:, j] - np.polyval(np.polyfit(tc, p[:, j], 2), tc)) ** 2 for j in (0, 1)))))
    out = dict(how="sagitta", n=int(len(s)), sagitta_px=sag, sagitta_err_px=sag_err, length_px=L, width_px=D, pi_L=pi_L,
               r_turn_over_D=(1.0 / pi_L) if pi_L > 0 else None,
               r_turn_over_D_low=L ** 2 / (8.0 * D * sag95) if sag95 > 0 else None,
               bent=bent, turned=bool(bent and pi_L >= HAIR), residual_rms_px=float(math.sqrt(var)), rms_quad_px=rms_quad,
               ellipse=None)
    out["sagitta_r_over_D"] = out["r_turn_over_D"]
    e = ellipse(t, p, fps)
    if (e and min(e["arc_deg"], e["heading_deg"]) >= ARC_DEG and e["rms_px"] <= LOOP_GAIN * rms_quad
            and e["minor_px"] > 3.0 * e["major_err_px"]):
        rD, om = e["major_px"] / D, e["omega_rad_per_s"]
        e.update(r_turn_over_D_err=e["major_err_px"] / D, speed_widths_per_s=om * rD, accel_widths_per_s2=om * om * rD)
        out.update(how="ellipse", ellipse=e, r_turn_over_D=rD, pi_L=1.0 / rD,
                   r_turn_over_D_low=max(e["major_px"] - 1.645 * e["major_err_px"], 0.0) / D, bent=True, turned=True)
    return out


def smear(v_px_per_s, fps, width_px):
    """The smear number: the displacement in one frame over the object's width across its travel. None without a width."""
    if not width_px or width_px <= 0 or v_px_per_s is None:
        return None
    return float(v_px_per_s) / float(fps) / float(width_px)


def pct(share):
    """A share a second as the depth bound writes it: '1.0 %', '0.45 %', '12 %'."""
    p = 100.0 * share
    return f"{p:.0f} %" if p >= 10 else f"{p:.1f} %" if p >= 1 else f"{p:.2g} %"


def depth_said(d, trend=False):
    """The depth bound (`depth_bound`) in words: under the hypothesis, said as one -- of the flight, or of the track's
    trend where the model follows only that."""
    sides = [f"{d['T_closing_min_s']:,.0f} s from the camera's plane if closing" if math.isfinite(d["T_closing_min_s"]) else None,
             f"{d['T_receding_min_s']:,.0f} s if receding" if math.isfinite(d["T_receding_min_s"]) else None]
    sides = [x for x in sides if x]
    return (f"if {'its trend is a straight flight' if trend else 'it flew straight'} at a steady speed, its depth changed by less "
            f"than {pct(d['rate_max_per_s'])} a second (its speed along the track changed by {d['dv_px_per_s']:+.0f} ± "
            f"{d['dv_err_px_per_s']:.0f} px/s over {d['span_s']:.1f} s)" + (f": it was at least {' and '.join(sides)}" if sides else ""))


def trend_px(proj):
    """The rms of the model the test chose, as "describes its trend to N px" writes it: whole pixels from 10 up."""
    r = proj["rms"] if proj["closing"] else proj["rms_const"]
    return f"{r:.0f}" if r >= 10 else f"{r:.1f}"


def held_to(proj):
    """", N times the track's own jitter (J px)" where the model chosen fits it; "" where no jitter was known, or the
    case was written before the check."""
    return (f", {proj['misfit']:.1f} times the track's own jitter ({proj['jitter_px']:.2f} px)"
            if proj.get("fits") and proj.get("misfit") is not None else "")


def tilt_said(r):
    """A turn read from a short arc, its tilt's band in words: the picture's radius r (in body widths) and the turn's
    own, nine times in ten with its plane at random to the line of sight (TILT_OWN)."""
    return (f"that radius is the picture's: with its plane at random to the line of sight, the turn's own radius is "
            f"{TILT_OWN[0] * r:,.0f} to {TILT_OWN[1] * r:,.0f} body widths nine times in ten")


def straight_said():
    """'Did not turn', with the one way a turn hides: its plane holding the line of sight (TILT_STRAIGHTER)."""
    (m1, p1), (m2, p2) = TILT_STRAIGHTER
    return (f"unless its plane held the line of sight, which draws a turn straight: one {m1} times tighter looks this "
            f"straight for {100 * p1:.0f} % of the ways its plane can lie, {m2} times tighter for {100 * p2:.0f} %")


def lens_said(drew):
    """"; drawn back through the lens ..." at the end of a reading made on a track a lens given was taken out of."""
    return f"; on the track drawn back through the lens first (k1 {drew['k1']:g}, which moved it by up to {drew['moved_px']:.1f} px)"


def lens_could(proj):
    """"; or the lens bent it ..." at the end of a miss where a lens alone accounts for it (`lens.could_be`, which the stage
    keeps as `lens_could`) better than a free quadratic of as many parameters does: the shape a lens gives a track, which
    real curves do not take; "" otherwise."""
    got = proj.get("lens_could")
    if not got or not got["fits"] or got["rms_px"] >= proj["rms_quad"]:
        return ""
    return (f"; or a lens bent it: one that moves the frame's corner {100 * abs(got['corner']):.0f} % "
            f"{'in' if got['corner'] < 0 else 'out'} accounts for the whole miss ({got['rms_px']:.1f} px rms, against the free "
            f"quadratic's {proj['rms_quad']:.1f}), so if the lens's k1 is known, give it")


def said(proj=None, turn_=None, smear_=None):
    """The three as sentences, written from their own numbers: {"smear": ..., "turn": ..., "constant velocity": ...}."""
    L = {}
    if smear_ is not None:
        L["smear"] = (f"{smear_:.2f}: the object moves {smear_:.2f} of its own width in one frame"
                 + (" -- it streaks within a frame" if smear_ > 1 else "")
                 + ("; an interlaced source's two fields would separate into two objects" if smear_ > 2 else ""))
    if turn_:
        scale = "; ".join(f"{what} {n}" for what, n in TURNS_OF)
        bend = f"the track bends by {turn_['sagitta_px']:.1f} ± {turn_['sagitta_err_px']:.1f} px over {turn_['length_px']:.0f} px"
        taken = turn_.get("lens")                          # drawn back through a lens given: its bend is out of the track
        e = turn_.get("ellipse") if turn_.get("how") == "ellipse" else None
        if e:
            from .kinematics import pm
            span = e["arc_deg"] / math.degrees(e["omega_rad_per_s"])
            L["turn"] = (f"the track loops: an ellipse {e['major_px']:.0f} by {e['minor_px']:.0f} px, drifting {e['drift_px_per_s']:.0f} px/s, "
                         f"goes round at {e['omega_rad_per_s']:.2f} rad/s ({e['arc_deg']:,.0f}° in {span:.1f} s), {e['rms_px']:.1f} px rms against a "
                         f"free quadratic's {turn_['rms_quad_px']:.1f}: a turn of radius {pm(turn_['r_turn_over_D'], e['r_turn_over_D_err'])} "
                         f"body widths, its plane {e['tilt_deg']:.0f}° from facing the camera, at {e['speed_widths_per_s']:.1f} body widths a "
                         f"second and {e['accel_widths_per_s2']:.1f} a second² toward its centre -- read whole, so with no range, field of "
                         f"view or foreshortening: a circle's image keeps its radius at any tilt ({scale}); a turn, or the camera's own "
                         "motion while it followed the object")
        elif turn_["turned"]:
            L["turn"] = (f"{bend}, a turn radius of about {turn_['r_turn_over_D']:.0f} body widths (Π_L = {turn_['pi_L']:.2g}; {scale}) -- "
                     f"{tilt_said(turn_['r_turn_over_D'])}: a straight line at constant velocity draws a straight track at any range, "
                     "so this is a turn, or a camera that moved sideways" + ("" if taken else ", or the lens"))
        elif turn_["bent"]:
            L["turn"] = (f"{bend}, a turn radius of about {turn_['r_turn_over_D']:,.0f} body widths (Π_L = {turn_['pi_L']:.2g}): a hair "
                     f"off straight, as easily the camera's{'' if taken else ' or the lens' + chr(39) + 's'} as the object's; nothing that manoeuvres flies that straight ({scale}) "
                     f"-- {tilt_said(turn_['r_turn_over_D'])}")
        else:
            low = turn_["r_turn_over_D_low"]               # None on a track with no bend at all (a drawn one): no bound to give
            L["turn"] = ((f"{bend} (within its noise), so the turn radius is at least {low:,.0f} body widths (95 %)" if low is not None
                          else f"{bend}: no bend at all")
                         + f": it did not turn, with no range, field of view or platform speed ({scale}) -- {straight_said()}")
    if proj:
        fits, misfit, held = proj.get("fits"), proj.get("misfit"), held_to(proj)
        loose = ("; not held to the track's own jitter, which could not be fitted" if fits is None and "fits" in proj
                 and proj["closing"] is not None else "")      # a case written before the check has no "fits": nothing said of it
        if proj["closing"] is not None and fits is False:
            model = (f"constant velocity ({proj['rms']:.1f} px rms)" if proj["closing"] else
                     f"constant image speed ({proj['rms_const']:.1f} px rms)")
            L["constant velocity"] = (f"the track is straight to {proj['straight_rms']:.1f} px, and {model} describes its trend as a "
                     f"free quadratic does ({proj['rms_quad']:.1f}), but misses the track by {misfit:.0f} times its own jitter "
                     f"({proj['jitter_px']:.2f} px): not a straight line at a steady speed to the jitter -- the camera's motion, or the "
                     "object's own, is in it -- so it gives no time to the camera's plane"
                     + (f"; {depth_said(proj['depth'], trend=True)}" if proj.get("depth") else
                        f"; {proj['depth_none']}" if proj.get("depth_none") else "") + lens_could(proj))
        elif proj["closing"] is True:
            band = (f" (16-84 % {proj['t_z_band'][0] - proj['t_last']:.2f} to {proj['t_z_band'][1] - proj['t_last']:.2f} s)"
                    if proj.get("t_z_band") else "")
            where = ("closing on the camera: it would cross the camera's plane " + f"{proj['T']:.2f} s after its last frame{band}"
                     if proj["T"] > 0 else f"receding: it crossed the camera's plane {-proj['T']:.2f} s before its first frame{band}")
            L["constant velocity"] = (f"the track is straight to {proj['straight_rms']:.1f} px and its distance from the vanishing "
                     f"point ({proj['vp'][0]:.0f}, {proj['vp'][1]:.0f}) goes as 1/(t_z - t), {proj['rms']:.1f} px rms{held} against a free "
                     f"quadratic's {proj['rms_quad']:.1f} and constant image speed's {proj['rms_const']:.1f}: consistent with constant "
                     f"velocity, {where}; its speed is then about {proj['v_over_R']:.2f} times its range at the last frame, per second"
                     + (f", at {proj['psi_deg']:.0f}° to the line of sight" if proj.get("psi_deg") is not None else "") + loose)
        elif proj["closing"] is False:
            L["constant velocity"] = (f"the track is straight to {proj['straight_rms']:.1f} px and constant image speed fits it "
                     f"({proj['rms_const']:.1f} px rms{held}): consistent with constant velocity across the line of sight, no closing "
                     "seen, " + (f"and {depth_said(proj['depth'])}" if proj.get("depth") else f"and {proj['depth_none']}" if
                                 proj.get("depth_none") else "so the track says nothing of how its range changed") + loose)
        else:
            L["constant velocity"] = (f"the track is straight to {proj['straight_rms']:.1f} px (at most {proj['straight_max']:.1f}); "
                     f"neither constant velocity ({proj['rms']:.1f} px rms) nor constant image speed ({proj['rms_const']:.1f}) describes "
                     f"it as a free quadratic does ({proj['rms_quad']:.1f}): not a straight line at constant velocity, or the camera moved"
                     + lens_could(proj))
    for name, got in (("constant velocity", proj), ("turn", turn_)):
        if name in L and (got or {}).get("lens"):
            L[name] += lens_said(got["lens"])
    return L
