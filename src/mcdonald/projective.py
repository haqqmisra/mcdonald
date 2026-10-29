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
  vanishing point (`psi_deg`; the kinematic notes' identity Π_θ = tan ψ). PR43 passes it: straight to 1.4 px rms,
  T = 0.80 s, the vanishing point inside the frame, at its jitter. Where it gives no time -- no closing
  seen, or the trend only -- the band's change of speed along the track still bounds how fast the depth changed
  under the model (`depth_bound`: |Zdot / Z| = 1 / |T|, the survey's M5), "the track says nothing of how its range
  changed" made a number.
- **The turn number** (`turn`): the track's sagitta against its length and the object's width, Π_L = 8 D s / L².
  A straight 3-D line at constant velocity projects to a straight image line at any range, so image curvature is
  not inertial by construction, and r_turn / D = 1 / Π_L is the turn radius in body widths -- the one kinematic
  statement that survives every missing calibration. Neither PR43's nor PR113's object turned: r_turn > 1,900 and
  > 380 body widths. Traps: D must be the object's width across its travel (a streak's length overstates it); a
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
BOOT = 200           # bootstrap draws for t_z's band
CLOSING_GAIN = 0.8   # the projective fit's rms must be under this share of constant image speed's to say it closes
QUAD_SLACK = 1.25    # and no more than this times the free quadratic's: it describes the track as the quadratic does
NUGGETS = 4.0        # and the model chosen fits only with its rms within this many times the track's own jitter; else it describes the trend
JITTER_FLOOR = 0.1   # px a coordinate: the least jitter a track is held to (a drawn or interpolated track has none; a centroid is read to about this)
DEPTH_Z = 1.959964   # the depth bound's sigmas: two-sided 95 %


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


def _T_from(v, dv, L):
    """T = t_z - t_last from the speed along the line at the stretch's two ends, v -/+ dv/2, over its length L: under
    the projective model v_end / v_start = ((T + L) / T)^2. Positive closing, negative receding, inf for no change;
    None where an end's speed is not positive (the change is too big to read this way)."""
    v0, v1 = v - dv / 2.0, v + dv / 2.0
    if v0 <= 0 or v1 <= 0:
        return None
    r = math.sqrt(v1 / v0)
    return math.inf if r == 1 else L / (r - 1.0)


def depth_bound(band, z=DEPTH_Z, floor=0.0):
    """"No closing seen" as a bound (the pure-mathematics survey's M5, 2026-10-29). Under the projective model the
    speed along the line goes as a / (t_z - t)^2, so over the band's stretch of length L, ending at the last frame,
    v_end / v_start = ((T + L) / T)^2, T = t_z - t_last, and 1 / |T| = |Zdot / Z| there: how fast the depth changed,
    as a share of itself a second. The band's change of velocity along the track (its kriged rate at the two ends,
    with the error the track's own covariance gives, so a wandering track widens it; at least `floor`, px/s, the error
    a free quadratic's curvature has, since a band whose REML finds no wander reads the velocity as unchanging to
    within nothing) within +-z sigmas bounds |T| from below on either side. Returns dict(rate_max_per_s,
    T_closing_min_s, T_receding_min_s (inf where that side is not reached), dv_px_per_s (along the track),
    dv_err_px_per_s, v_px_per_s, span_s, z), or None where the band has no change of velocity by axis or the change
    and its error reach the speed itself (the bound says nothing then)."""
    if not band or band.get("dv_xy") is None or not band.get("v_mean_px_per_s"):
        return None
    v, L = float(band["v_mean_px_per_s"]), float(band["t1"] - band["t0"])
    if L <= 0:
        return None
    ux, uy = band["vx_mean"] / v, band["vy_mean"] / v
    dv = band["dv_xy"][0] * ux + band["dv_xy"][1] * uy
    e = max(math.hypot(band["dv_err_xy"][0] * ux, band["dv_err_xy"][1] * uy), float(floor))
    lo, hi = dv - z * e, dv + z * e
    close = _T_from(v, hi, L) if hi > 0 else math.inf
    recede = _T_from(v, lo, L) if lo < 0 else -math.inf
    if close is None or recede is None:
        return None
    close, recede = abs(close), abs(recede)
    return dict(rate_max_per_s=max(1.0 / close, 1.0 / recede), T_closing_min_s=close, T_receding_min_s=recede,
                dv_px_per_s=float(dv), dv_err_px_per_s=float(e), v_px_per_s=v, span_s=L, z=float(z))


def fit(track, fps, k=None, centre=None, t0=None, t1=None, n0=None, n1=None, boot=BOOT, seed=0, band=None):
    """The projective constant-velocity test on a track. Returns None under 6 points; else a dict:

    `straight_rms`, `straight_max` (px): how straight the image track is, off its principal line;
    `vp` (x, y): the vanishing point; `t_z` (s), `t_z_band` (16-84 %, a residual bootstrap), `T` = t_z - t_last
    (the time to go; negative where the object recedes from a crossing in the past); `rms`, `rms_const`, `rms_quad`
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
    None, and None where no jitter is known. `depth`: `depth_bound` of the band where the model is chosen and gives no
    time to the camera's plane (no closing seen, or the trend only) -- how fast its depth could have changed, if it
    flew straight at a steady speed."""
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
    s_vp, a, tz, _ = _fit_along(s, t, span)
    ang = math.atan2(u[1], u[0])
    vp0 = c + u * s_vp
    theta0 = [vp0[0], vp0[1], ang, a, tz]

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
    # the band of t_z: a residual bootstrap of the 1-D fit along the line (none where the model describes only the trend)
    tz_band = None
    if closing and fits is not False and boot:
        rng = np.random.default_rng(seed)
        r = s - (s_vp + a / (tz - t))
        draws = []
        for _ in range(int(boot)):
            sb = (s_vp + a / (tz - t)) + rng.choice(r, len(r), replace=True)
            draws.append(_fit_along(sb, t, span)[2])
        tz_band = [float(np.percentile(draws, 16)), float(np.percentile(draws, 84))]
    # the change of speed along the line a free quadratic reads, its error if its residual were white: the depth bound's
    # floor, where the band's REML puts the wander at nothing and so the velocity's change at nothing to within nothing
    X = np.c_[np.ones(len(t)), t - t.mean(), (t - t.mean()) ** 2]
    coef, *_ = np.linalg.lstsq(X, s, rcond=None)
    res = s - X @ coef
    var = float(res @ res) / max(len(t) - 3, 1)
    dv_floor = 2.0 * span * math.sqrt(max(var * np.linalg.inv(X.T @ X)[2, 2], 0.0))
    out = dict(n=int(len(t)), t_first=float(t[0]), t_last=float(t[-1]), **straight, vp=[vx, vy], t_z=tz, t_z_band=tz_band,
               T=T, rms=rms, rms_const=rms_const, rms_quad=rms_quad, closing=closing, jitter_px=yard, jitter_from=jitter_from,
               misfit=misfit, fits=fits,
               depth=depth_bound(band, floor=dv_floor) if closing is False or (closing and fits is False) else None,
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


def turn(track, fps, width_px, t0=None, t1=None, n0=None, n1=None):
    """The turn number: the track's sagitta across its principal line (a quadratic across, s the sagitta of the
    arc over the whole length L), Π_L = 8 D s / L², and the turn radius in body widths r_turn / D = L² / (8 D s).
    Returns None under 5 points or with no width; else dict(sagitta_px, sagitta_err_px, length_px, pi_L,
    r_turn_over_D, r_turn_over_D_low (the 95 % lower bound: the sagitta at its 95 % upper), turned (the sagitta
    three sigmas from zero), n)."""
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
    return dict(n=int(len(s)), sagitta_px=sag, sagitta_err_px=sag_err, length_px=L, width_px=float(width_px), pi_L=pi_L,
                r_turn_over_D=(1.0 / pi_L) if pi_L > 0 else None,
                r_turn_over_D_low=L ** 2 / (8.0 * width_px * sag95) if sag95 > 0 else None,
                bent=bent, turned=bool(bent and pi_L >= HAIR), residual_rms_px=float(math.sqrt(var)))


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
        if turn_["turned"]:
            L["turn"] = (f"{bend}, a turn radius of about {turn_['r_turn_over_D']:.0f} body widths (Π_L = {turn_['pi_L']:.2g}; {scale}): "
                     "a straight line at constant velocity draws a straight track at any range, so this is a turn, or a camera that "
                     "moved sideways, or the lens")
        elif turn_["bent"]:
            L["turn"] = (f"{bend}, a turn radius of about {turn_['r_turn_over_D']:,.0f} body widths (Π_L = {turn_['pi_L']:.2g}): a hair "
                     f"off straight, as easily the camera's or the lens's as the object's; nothing that manoeuvres flies that straight ({scale})")
        else:
            low = turn_["r_turn_over_D_low"]               # None on a track with no bend at all (a drawn one): no bound to give
            L["turn"] = ((f"{bend} (within its noise), so the turn radius is at least {low:,.0f} body widths (95 %)" if low is not None
                          else f"{bend}: no bend at all")
                         + f": it did not turn, with no range, field of view or platform speed ({scale})")
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
                     + (f"; {depth_said(proj['depth'], trend=True)}" if proj.get("depth") else ""))
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
                     "seen, " + (f"and {depth_said(proj['depth'])}" if proj.get("depth") else
                                 "so the track says nothing of how its range changed") + loose)
        else:
            L["constant velocity"] = (f"the track is straight to {proj['straight_rms']:.1f} px (at most {proj['straight_max']:.1f}); "
                     f"neither constant velocity ({proj['rms']:.1f} px rms) nor constant image speed ({proj['rms_const']:.1f}) describes "
                     f"it as a free quadratic does ({proj['rms_quad']:.1f}): not a straight line at constant velocity, or the camera moved")
    return L
