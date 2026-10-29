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
  and a free quadratic in each coordinate (six: no physics). Where it fits -- as well as the quadratic with one
  parameter fewer, and better than constant speed -- the track is consistent with constant velocity, and the time
  to go T = t_z - t_last is the speed in units of the range: v ≈ R / T at the last frame, within a few per cent
  for any field under about 50° (the secants of the vanishing point's and the object's angles off boresight nearly
  cancel; with k given, exactly). With k the aspect angle at the last frame is the angle between the object and the
  vanishing point (`psi_deg`; the kinematic notes' identity Π_θ = tan ψ). PR43 passes it: straight to 1.4 px rms,
  T = 0.80 s, the vanishing point inside the frame.
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


def fit(track, fps, k=None, centre=None, t0=None, t1=None, n0=None, n1=None, boot=BOOT, seed=0):
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
    `beta_vp_deg`, the vanishing point's angle off boresight."""
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
    # the band of t_z: a residual bootstrap of the 1-D fit along the line
    band = None
    if closing and boot:
        rng = np.random.default_rng(seed)
        r = s - (s_vp + a / (tz - t))
        draws = []
        for _ in range(int(boot)):
            sb = (s_vp + a / (tz - t)) + rng.choice(r, len(r), replace=True)
            draws.append(_fit_along(sb, t, span)[2])
        band = [float(np.percentile(draws, 16)), float(np.percentile(draws, 84))]
    out = dict(n=int(len(t)), t_first=float(t[0]), t_last=float(t[-1]), **straight, vp=[vx, vy], t_z=tz, t_z_band=band,
               T=T, rms=rms, rms_const=rms_const, rms_quad=rms_quad, closing=closing,
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
            L["turn"] = (f"{bend} (within its noise), so the turn radius is at least {turn_['r_turn_over_D_low']:,.0f} body widths "
                     f"(95 %): it did not turn, with no range, field of view or platform speed ({scale})")
    if proj:
        if proj["closing"] is True:
            band = (f" (16-84 % {proj['t_z_band'][0] - proj['t_last']:.2f} to {proj['t_z_band'][1] - proj['t_last']:.2f} s)"
                    if proj.get("t_z_band") else "")
            where = ("closing on the camera: it would cross the camera's plane " + f"{proj['T']:.2f} s after its last frame{band}"
                     if proj["T"] > 0 else f"receding: it crossed the camera's plane {-proj['T']:.2f} s before its first frame{band}")
            L["constant velocity"] = (f"the track is straight to {proj['straight_rms']:.1f} px and its distance from the vanishing "
                     f"point ({proj['vp'][0]:.0f}, {proj['vp'][1]:.0f}) goes as 1/(t_z - t), {proj['rms']:.1f} px rms against a free "
                     f"quadratic's {proj['rms_quad']:.1f} and constant image speed's {proj['rms_const']:.1f}: consistent with constant "
                     f"velocity, {where}; its speed is then about {proj['v_over_R']:.2f} times its range at the last frame, per second"
                     + (f", at {proj['psi_deg']:.0f}° to the line of sight" if proj.get("psi_deg") is not None else ""))
        elif proj["closing"] is False:
            L["constant velocity"] = (f"the track is straight to {proj['straight_rms']:.1f} px and constant image speed fits it "
                     f"({proj['rms_const']:.1f} px rms): consistent with constant velocity across the line of sight, no closing seen, "
                     "so the track says nothing of how its range changed")
        else:
            L["constant velocity"] = (f"the track is straight to {proj['straight_rms']:.1f} px (at most {proj['straight_max']:.1f}); "
                     f"neither constant velocity ({proj['rms']:.1f} px rms) nor constant image speed ({proj['rms_const']:.1f}) describes "
                     f"it as a free quadratic does ({proj['rms_quad']:.1f}): not a straight line at constant velocity, or the camera moved")
    return L
