"""From pixels to what the motion permits — and to what it does not.

The whole reduction is three scalar equations:

    (1)  omega = v_px * f / k          line-of-sight angular rate  [rad/s]
    (2)  omega * R = |v_obj - v_own| * sin(theta)
    (3)  k = f_px * sec^2(alpha),      f_px = (W/2) / tan(FOV/2)

with two more for size and aspect:

    (4)  S = p * R / k                 object size from its angular size
    (5)  tan(theta) = omega * R / |Rdot|

v_px (image-plane rate), f (frame rate) and W (frame width) come out of the
clip. **k, R, Rdot (or theta) and v_own do not.** On most released sensor video
none of the four is recoverable, which is why this module is built to return
bounds and refuse point speeds.

That refusal is the design, not a limitation of the code. A reduction with an
unknown k and an unknown R has a one-parameter family of answers spanning
orders of magnitude, and printing any single member of it — the one where the
range happened to be guessed at 5 km — is how a clip of an unremarkable object
becomes a hypersonic craft in a headline.

Three things follow that are easy to get wrong:

- **theta is not free.** The range changes with time, and theta follows from
  the range rate by (5). Picking theta = 90 deg to "be conservative" is
  choosing the minimum of the family, which is a lower bound and should be
  quoted as one.
- **Relative speed is not object speed.** |v_obj - v_own| already includes the
  platform's own motion: a stationary object seen from a jet has
  |v_obj - v_own| = |v_own|. Everything below about Mach 1 is reachable by an
  object that is not moving at all. That is the GOFAST lesson.
- **k is a function of position in the frame**, not a constant. It grows as
  sec^2(alpha) toward the edges, and an object crossing most of the frame is
  not measured at one scale.

Two routes escape the unknown k entirely, and are worth more than a better
estimate of it:

- **An in-frame object of known size** (scale_bar_speed): an image displacement
  divided by a reference object's image length is a displacement in reference
  lengths. The field of view cancels. Only the *ratio* of ranges survives, and
  that is what such a clip cannot supply — so the result is a bound, tight only
  when the object is at the reference's range.
- **The object's own size** (body_lengths_per_s): v_px / h_px is the object's
  speed in its own body-lengths per second, free of k, of R and of the field of
  view, because numerator and denominator scale alike with range. It is the
  only speed in this module that needs nothing at all.
"""
import math

import numpy as np

A_SOUND = 343.0          # m/s at sea level, for Mach context only
RESOLVED = ("a body length only if the object shows its own shape: "
            "for a point, the size is the blur, not the body")


# ---- the angular scale, with its provenance --------------------------------------------
class AngularScale:
    """k, in pixels per radian, and where it came from.

    Carrying the provenance is the point. A k read off a graticule the sensor
    itself draws is a measurement; a k derived from an assumed field of view is
    an assumption, and anything computed from it inherits that status."""

    def __init__(self, k, source, alpha_deg=0.0, detail=""):
        self.k = None if k is None else float(k)
        self.source = source
        self.alpha_deg = alpha_deg
        self.detail = detail

    @property
    def known(self):
        return self.k is not None

    @classmethod
    def unknown(cls, why="not recoverable from this clip"):
        return cls(None, "unknown", detail=why)

    @classmethod
    def from_graticule(cls, px_per_deg, alpha_deg=0.0):
        """Measured: the sensor draws a scale and it is read directly. No lens
        model, no field of view, no assumption."""
        return cls(px_per_deg * 180.0 / math.pi, "graticule", alpha_deg,
                   f"{px_per_deg:g} px per labelled degree")

    @classmethod
    def from_fov(cls, width_px, fov_deg, alpha_deg=0.0):
        """Assumed: a field of view, through the full sec^2 expression.

        alpha_deg is the object's field angle — its position in the frame, not
        its direction of travel. k grows toward the frame edge."""
        f_px = (width_px / 2.0) / math.tan(math.radians(fov_deg) / 2.0)
        k = f_px / math.cos(math.radians(alpha_deg)) ** 2
        return cls(k, "assumed FOV", alpha_deg,
                   f"FOV {fov_deg:g} deg over {width_px:g} px, at field angle {alpha_deg:g} deg")

    def at(self, alpha_deg):
        """The same optics, re-evaluated at another field angle."""
        if not self.known:
            return self
        k0 = self.k * math.cos(math.radians(self.alpha_deg)) ** 2
        return AngularScale(k0 / math.cos(math.radians(alpha_deg)) ** 2,
                            self.source, alpha_deg, self.detail)

    def __repr__(self):
        return (f"AngularScale(unknown: {self.detail})" if not self.known else
                f"AngularScale(k={self.k:.1f} px/rad, {self.source}: {self.detail})")


def f_px_from_fov(width_px, fov_deg):
    return (width_px / 2.0) / math.tan(math.radians(fov_deg) / 2.0)


def fov_from_k(k, width_px, alpha_deg=0.0, small_angle=False):
    """Inverse of (3): the field of view implied by an angular scale.

    The two models disagree by more than the rounding suggests, so say which
    you used. small_angle=True takes k -> W/FOV, which is the reading meant by
    "extrapolating the graticule across the frame"; the default uses the full
    sec^2 expression. At a targeting pod's wide fields the small-angle form
    overstates k at frame centre by about 8 % (FOV 54 deg), and k itself varies
    by ~34 % between frame centre and corner — which is why a single k for a
    whole transit is usually the weakest step in a reduction.

    PR113's graticule k = 2028 px/rad gives 54.2 deg small-angle, 50.7 deg
    full. Both are that measurement; neither is a field of view the sensor
    reported."""
    if small_angle:
        return math.degrees(width_px / k)
    f_px = k * math.cos(math.radians(alpha_deg)) ** 2
    return math.degrees(2 * math.atan((width_px / 2.0) / f_px))


# ---- image-plane rate ------------------------------------------------------------------
def fit_v_px(track, fps, t0=None, t1=None, n0=None, n1=None, clip_sigma=4.0,
             iters=4, min_points=3):
    """v_px from a track, by robust least squares against **wall-clock time**.

    Three things this does that a plain polyfit does not, each of which cost a
    wrong number once:

    - **Time, not frames.** Many sensor clips repeat ~7 % of their frames and
      catch up with a double step later, so position-against-frame is a
      staircase. The mean rate against wall-clock time is still right; any
      per-frame reading is not.
    - **Sigma-clipping.** A detection file is not a track. Trackers latch onto
      a trailing smear, a terrain false positive or a second source, and a
      single such point drags a least-squares slope a long way. Points more
      than clip_sigma robust deviations off the line are dropped and the fit
      repeated.
    - **A straightness check.** `resid_rms` is returned *and* compared with
      the span. When the residual is a large fraction of the distance covered,
      the motion is not uniform and a single v_px does not describe it —
      `uniform` is then False and the caller must not quote the number.

    n0/n1 window by frame, t0/t1 by time; use them when the object is only in
    shot for part of the file.

    track is {frame: (x, y)} or an (n, 3) array of frame, x, y."""
    if isinstance(track, dict):
        a = np.array([[n, xy[0], xy[1]] for n, xy in sorted(track.items())], float)
    else:
        a = np.asarray(track, float)
    if len(a) < min_points:
        return None
    t_all = (a[:, 0] - 1) / float(fps)
    s = np.isfinite(a[:, 1]) & np.isfinite(a[:, 2])
    if t0 is not None:
        s &= t_all >= t0
    if t1 is not None:
        s &= t_all < t1
    if n0 is not None:
        s &= a[:, 0] >= n0
    if n1 is not None:
        s &= a[:, 0] <= n1
    if s.sum() < min_points:
        return None
    t, x, y = t_all[s], a[s, 1], a[s, 2]
    n_in = int(s.sum())

    keep = np.ones(len(t), bool)
    for _ in range(max(int(iters), 0)):
        if keep.sum() < min_points:
            break
        ok = np.ones(keep.sum(), bool)
        for v in (x[keep], y[keep]):
            r = v - np.polyval(np.polyfit(t[keep], v, 1), t[keep])
            sd = 1.4826 * np.median(np.abs(r - np.median(r)))
            ok &= np.abs(r - np.median(r)) < max(clip_sigma * sd, 2.0)
        if ok.all():
            break
        idx = np.nonzero(keep)[0]
        keep[idx[~ok]] = False
    if keep.sum() < min_points:
        return None

    tk, xk, yk = t[keep], x[keep], y[keep]
    (vx, x0), (vy, y0) = np.polyfit(tk, xk, 1), np.polyfit(tk, yk, 1)
    rx, ry = xk - (vx * tk + x0), yk - (vy * tk + y0)
    resid = float(np.sqrt((rx ** 2 + ry ** 2).mean()))
    span = float(math.hypot(xk[-1] - xk[0], yk[-1] - yk[0]))
    return dict(v_px=float(math.hypot(vx, vy)), vx=float(vx), vy=float(vy),
                direction_deg=float(math.degrees(math.atan2(vx, -vy)) % 360),
                resid_rms=resid, n=int(keep.sum()), n_in=n_in,
                n_clipped=int(n_in - keep.sum()),
                t0=float(tk.min()), t1=float(tk.max()), span_px=span,
                resid_frac=float(resid / span) if span > 0 else None,
                uniform=bool(span > 0 and resid / span < 0.05))


def omega(v_px_per_s, scale):
    """(1): line-of-sight angular rate [rad/s]. None when k is unknown."""
    k = scale.k if isinstance(scale, AngularScale) else scale
    return None if k in (None, 0) else float(v_px_per_s) / float(k)


# ---- the relation, and the fan --------------------------------------------------------
def relative_speed(omega_rad_s, R_m, theta_deg=90.0):
    """(2) solved for |v_obj - v_own| [m/s]. Relative, not object, speed."""
    return float(omega_rad_s) * float(R_m) / math.sin(math.radians(theta_deg))


def aspect_from_range_rate(omega_rad_s, R_m, range_rate_m_s):
    """(5): theta from the range rate, the quantity a sensor could record and
    these releases do not."""
    if range_rate_m_s == 0:
        return 90.0
    return float(math.degrees(math.atan2(omega_rad_s * R_m, abs(range_rate_m_s))))


def fan(omega_rad_s, R_m=None, thetas_deg=(90, 30, 15, 8, 4, 2)):
    """The permitted family: relative speed against range, one line per aspect
    angle. log v = log(omega R) - log(sin theta), so on log-log axes these are
    parallel straight lines — which is what makes the one-sidedness visible.

    theta = 90 deg is a hard LOWER bound: everything below that line is
    excluded, everything above it is permitted."""
    R = np.logspace(0, math.log10(3000), 400) if R_m is None else np.atleast_1d(R_m).astype(float)
    return R, {th: omega_rad_s * R / math.sin(math.radians(th)) for th in thetas_deg}


def object_size(p_px, R_m, scale):
    """(4): physical size from angular size. Small-angle; these span << 1 deg."""
    k = scale.k if isinstance(scale, AngularScale) else scale
    return None if k in (None, 0) else float(p_px) * float(R_m) / float(k)


# ---- the two routes that do not need k -------------------------------------------------
def body_lengths_per_s(v_px_per_s, size_px):
    """The object's speed in its own body-lengths per second.

    Free of k, of R and of the field of view: numerator and denominator scale
    alike with range. The one speed here that assumes nothing -- except that
    `size_px` is the body. For an object too small to show its shape, the size
    the detector or a person gives is the blur of a point, and this is a speed
    in blur widths (PR135: "28.6 body-lengths/s" from a 7.4 px detector size,
    for a group of points). Context: a watercraft tops out near 11 /s, an
    airliner near 3 /s, a rifle bullet near 10^3 /s."""
    return None if not size_px else float(v_px_per_s) / float(size_px)


def scale_bar_speed(v_px_per_s, ref_px, ref_len_m, range_ratio=1.0):
    """Speed from a known-size object sharing the frame. The FOV cancels.

    range_ratio is R_object / R_reference, the one thing such a clip cannot
    supply. At 1.0 this is the speed the object would have *at the reference's
    range*; an object nearer than the reference is slower, one further is
    faster, in proportion. Quote it as a bound and say which."""
    return float(v_px_per_s) / float(ref_px) * float(ref_len_m) * float(range_ratio)


# ---- parallax: the platform's share of a ground-projected speed ------------------------
# An agent's first request after `layers` (PR135, items 1 and 15): the question behind every MQ-9
# "speed" in the release is whether a speed measured along the ground is the object's own, or the
# aircraft's motion seen through an object nearer than the ground. For an object at height h_O seen
# against the ground from h_A, the ground point behind it moves at
#
#     v_G = k v_O - (k - 1) v_A,        k = h_A / (h_A - h_O)
#
# so a stationary object (v_O = 0) half way down (k = 2) has a ground speed equal to the aircraft's.
# The FOV x range ladder answers |v_obj - v_own| across the line of sight; this one answers "which
# heights, for which speeds of its own, give the speed that was reported" -- and needs two numbers
# the video does not hold: the ground speed (a report's, or one measured with a scale on the ground)
# and the aircraft's speed. Its heading and the ground motion's bearing narrow it from a range of k
# to one k for each speed; without them the ladder is the range every direction allows.
KNOTS, MPH, KMH = 0.514444, 0.44704, 1 / 3.6
SPEEDS_OF_ITS_OWN = (0.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0, 100.0)    # m/s: still air, birds, a small drone, ...


def isa_density_ratio(alt_m, dT=0.0):
    """rho / rho_0 in the ISA troposphere, with the temperature dT off standard (K)."""
    T0, L, g, R = 288.15, 0.0065, 9.80665, 287.053
    T = T0 - L * alt_m + dT
    p_ratio = (1 - L * alt_m / T0) ** (g / (R * L))
    return p_ratio * (T0 / T)


def tas_from_ias(ias_m_s, alt_m, dT=0.0):
    """True airspeed from indicated (calibrated, incompressible: good below about 250 kt), ISA."""
    return float(ias_m_s / math.sqrt(isa_density_ratio(alt_m, dT)))


def speed_of(text):
    """(m/s, band (lo, hi) or None, what was read) from '480mph', '215 m/s', '250kt', '400 km/h', or
    '250kias@7000ft' (indicated airspeed at an altitude: the true airspeed in ISA, with the band a
    day 15 C colder or warmer gives). A bare number is m/s. ValueError for anything else."""
    import re
    t = str(text).strip().lower().replace(" ", "")
    m = re.fullmatch(r"([0-9.]+)(kias|kcas)@([0-9.]+)(ft|m)?", t)
    if m:
        ias, alt = float(m.group(1)) * KNOTS, float(m.group(3)) * (0.3048 if m.group(4) != "m" else 1.0)
        tas = tas_from_ias(ias, alt)
        band = (tas_from_ias(ias, alt, -15.0), tas_from_ias(ias, alt, 15.0))
        return tas, band, f"{m.group(1)} kt indicated at {alt:.0f} m: {tas:.1f} m/s true in ISA ({band[0]:.1f}-{band[1]:.1f} at -15 to +15 C)"
    m = re.fullmatch(r"([0-9.]+)(m/s|mps|kt|kts|knots?|mph|km/h|kph|kmh)?", t)
    if not m:
        raise ValueError(f"{text!r}: give a speed as 480mph, 215m/s, 250kt, 400km/h, or 250kias@7000ft")
    unit = m.group(2) or "m/s"
    f = {"m/s": 1.0, "mps": 1.0, "mph": MPH, "km/h": KMH, "kph": KMH, "kmh": KMH}.get(unit, KNOTS)
    v = float(m.group(1)) * f
    return v, None, f"{m.group(1)} {unit} = {v:.1f} m/s"


def parallax_inputs(ground_speed, own_ship):
    """The two strings a person gives -- ground speed 'SPEED[,BEARING]', own ship
    'SPEED[,HEADING[,ALTITUDE]]' (altitude as 7000ft or 2100m; an indicated speed '250kias@7000ft'
    carries its own) -- as dict(v_ground, v_own, own_band, ground_bearing, own_heading, h_own_m, said).
    ValueError with a sentence for anything that cannot be read."""
    import re
    g = [x.strip() for x in str(ground_speed).split(",")]
    o = [x.strip() for x in str(own_ship).split(",")]
    if len(g) > 2 or len(o) > 3:
        raise ValueError("give the ground speed as SPEED[,BEARING] and the aircraft as SPEED[,HEADING[,ALTITUDE]], "
                         "such as 480mph,265 and 180kt,90,7000ft")
    vg, _, said_g = speed_of(g[0])
    vo, band, said_o = speed_of(o[0])
    h = None
    m = re.search(r"@([0-9.]+)(ft|m)?$", o[0].lower())
    if m:
        h = float(m.group(1)) * (0.3048 if m.group(2) != "m" else 1.0)
    if len(o) == 3:
        m = re.fullmatch(r"([0-9.]+)(ft|m)", o[2].lower().replace(" ", ""))
        if not m:
            raise ValueError(f"{o[2]!r}: give the aircraft's altitude as 7000ft or 2100m")
        h = float(m.group(1)) * (0.3048 if m.group(2) == "ft" else 1.0)
    num = lambda t, what: float(t) if t else None
    try:
        gb = num(g[1], "bearing") if len(g) > 1 else None
        oh = num(o[1], "heading") if len(o) > 1 else None
    except ValueError:
        raise ValueError("a bearing or heading is degrees clockwise from north, such as 265")
    return dict(v_ground=vg, v_own=vo, own_band=band, ground_bearing=gb, own_heading=oh, h_own_m=h,
                said=[f"ground speed {said_g}" + (f", toward {gb:g} deg" if gb is not None else ""),
                      f"aircraft {said_o}" + (f", heading {oh:g} deg" if oh is not None else "")
                      + (f", at {h:.0f} m" if len(o) == 3 else "")])


def _unit(bearing_deg):
    b = math.radians(bearing_deg)
    return np.array([math.sin(b), math.cos(b)])                  # east, north


def parallax_ladder(v_ground, v_own, own_heading=None, ground_bearing=None, h_own_m=None, speeds=SPEEDS_OF_ITS_OWN):
    """For each speed of its own the object might have, the k = h_A / (h_A - h_O) that give the ground
    speed seen, and the heights they put it at (h_O / h_A = 1 - 1/k; in metres with h_own_m). Speeds in
    m/s, bearings in degrees clockwise from north.

    Without the two directions: the range of k every direction of the object's own motion allows,
    [(v_G + v_A) / (v_A + v_O), (v_G + v_A) / (v_A - v_O)] (open above when v_O >= v_A), and k >= 1 --
    an object between the aircraft and the ground. With both: v_G and v_A as vectors, and
    k v_O = |v_G + (k - 1) v_A| solved for k, one or two roots. A stationary object then has to move
    along the ground exactly opposite the aircraft's heading, and `stationary_off_deg` says how far
    the ground motion is from that.

    A still object fits exactly only with the ground motion exactly against the heading, which measured
    bearings never are: its row also gives the nearest k (`closest`) and the speed of its own the object
    would still need there -- |v_G| sin(the angle off), the across-track part nothing else explains.

    Returns dict(rows=[dict(v_obj, k (or k_min, k_max), h_ratio (or ranges), h_m)], stationary_off_deg)."""
    rows = []
    vec = own_heading is not None and ground_bearing is not None
    if vec:
        G, A = v_ground * _unit(ground_bearing), v_own * _unit(own_heading)
    for vo in speeds:
        row = dict(v_obj_m_s=vo)
        if vec:
            ks = np.concatenate([np.linspace(1.0, 20.0, 4000), np.geomspace(20.0, 1e4, 2000)[1:]])
            f = np.array([np.hypot(*(G + (k - 1) * A)) - k * vo for k in ks])
            roots = []
            for i in np.nonzero(np.sign(f[:-1]) != np.sign(f[1:]))[0]:
                a, b = ks[i], ks[i + 1]
                for _ in range(50):
                    m = 0.5 * (a + b)
                    fm = np.hypot(*(G + (m - 1) * A)) - m * vo
                    if np.sign(fm) == np.sign(np.hypot(*(G + (a - 1) * A)) - a * vo):
                        a = m
                    else:
                        b = m
                roots.append(0.5 * (a + b))
            if abs(f[0]) < 1e-9:
                roots.insert(0, 1.0)
            if vo == 0.0:                               # |G + (k - 1) A| = 0 touches zero only if G is exactly against A
                u = A / np.hypot(*A)
                kc = 1.0 + max(0.0, -float(G @ u)) / float(np.hypot(*A))
                need = float(np.hypot(*(G + (kc - 1) * A)))
                roots = [kc] if need < 1e-6 * max(v_ground, 1.0) else []
                row["closest"] = dict(k=round(kc, 3), h_ratio=round(1 - 1 / kc, 4), own_speed_needed_m_s=round(need, 2))
            row["k"] = [round(float(k), 3) for k in roots]
            row["h_ratio"] = [round(1 - 1 / k, 4) for k in roots]
            if h_own_m:
                row["h_m"] = [round(h_own_m * (1 - 1 / k)) for k in roots]
        else:
            lo = max(1.0, (v_ground + v_own) / (v_own + vo)) if v_own + vo > 0 else None
            hi = (v_ground + v_own) / (v_own - vo) if v_own > vo else None
            if lo is not None and hi is not None and hi < lo:
                lo = hi = None
            row["k_min"], row["k_max"] = lo, hi
            row["h_ratio_min"] = None if lo is None else round(1 - 1 / lo, 4)
            row["h_ratio_max"] = None if hi is None else round(1 - 1 / hi, 4)
            if h_own_m:
                row["h_m_min"] = None if lo is None else round(h_own_m * (1 - 1 / lo))
                row["h_m_max"] = None if hi is None else round(h_own_m * (1 - 1 / hi))
        rows.append(row)
    off = None
    if vec:
        off = abs((ground_bearing - (own_heading + 180.0) + 180.0) % 360.0 - 180.0)
    return dict(rows=rows, stationary_off_deg=off, vectors=vec)


def ladder_said(p, v_ground, v_own, h_own_m=None):
    """The ladder as lines, for a person."""
    L = [f"parallax: a ground speed of {v_ground:.1f} m/s seen from an aircraft at {v_own:.1f} m/s "
         "(k = h_A / (h_A - h_O); h_O / h_A = 1 - 1/k)"]
    for r in p["rows"]:
        head = f"  {r['v_obj_m_s']:5.1f} m/s of its own: "
        if p["vectors"]:
            if not r["k"] and "closest" in r:
                c = r["closest"]
                L.append(head + f"no height gives it exactly; nearest at k {c['k']:.2f}, h_O/h_A {c['h_ratio']:.3f}, "
                         f"where it would still need {c['own_speed_needed_m_s']:.1f} m/s of its own across")
            elif not r["k"]:
                L.append(head + "no height gives it")
            else:
                L.append(head + "; ".join(f"k {k:.2f}, h_O/h_A {h:.3f}" + (f" ({m} m)" if h_own_m else "")
                                          for k, h, m in zip(r["k"], r["h_ratio"], r.get("h_m", [None] * len(r["k"])))))
        else:
            if r["k_min"] is None:
                L.append(head + "no height gives it")
            elif r["k_max"] is not None and r["k_max"] - r["k_min"] < 0.005:
                L.append(head + f"k {r['k_min']:.2f}: h_O/h_A {r['h_ratio_min']:.3f}" + (f" ({r['h_m_min']} m)" if h_own_m else ""))
            else:
                hi = "or more" if r["k_max"] is None else f"to {r['k_max']:.2f}"
                L.append(head + f"k {r['k_min']:.2f} {hi}: h_O/h_A {r['h_ratio_min']:.3f} to "
                         + ("1 (just under the aircraft)" if r["k_max"] is None else f"{r['h_ratio_max']:.3f}")
                         + (f" ({r['h_m_min']} to {r['h_m_max'] if r['h_m_max'] is not None else round(h_own_m)} m)" if h_own_m else ""))
    if p["vectors"]:
        L.append(f"  a stationary object would move along the ground opposite the aircraft; the ground motion is "
                 f"{p['stationary_off_deg']:.0f} deg from that")
    else:
        L.append("  without the aircraft's heading and the ground motion's bearing, each row is the range every "
                 "direction of the object's own motion allows")
    return L


# ---- putting it together ----------------------------------------------------------------
class Reduction:
    """What this clip's motion permits, and what it is still missing.

    Built to be printed. It states the inputs it has, names the ones it does
    not, and produces a bound rather than a speed whenever anything is absent."""

    def __init__(self, v_px, fps=None, scale=None, R_m=None, range_rate=None,
                 theta_deg=None, v_own=None, size_px=None, ref=None, tag="",
                 fit=None):
        self.tag = tag
        self.fit = fit
        self.v_px = float(v_px)
        self.fps = fps
        self.scale = scale if isinstance(scale, AngularScale) else (
            AngularScale.unknown() if scale is None else AngularScale(scale, "given"))
        self.R_m, self.range_rate, self.v_own = R_m, range_rate, v_own
        self.size_px, self.ref = size_px, ref
        self.omega = omega(self.v_px, self.scale)
        self.theta_deg = theta_deg
        if self.theta_deg is None and self.omega and R_m and range_rate is not None:
            self.theta_deg = aspect_from_range_rate(self.omega, R_m, range_rate)

    @property
    def missing(self):
        m = []
        if not self.scale.known:
            m.append("k (angular scale)")
        if self.R_m is None:
            m.append("R (range)")
        if self.theta_deg is None:
            m.append("theta or Rdot (aspect angle / range rate)")
        if self.v_own is None:
            m.append("v_own (platform velocity)")
        return m

    def speed(self):
        """|v_obj - v_own| in m/s, or None when something needed is missing."""
        if self.omega is None or self.R_m is None:
            return None
        return relative_speed(self.omega, self.R_m, self.theta_deg or 90.0)

    def lower_bound(self):
        """The theta = 90 deg member: the minimum relative speed consistent
        with the measurement, at whatever range is assumed."""
        return None if (self.omega is None or self.R_m is None) else self.omega * self.R_m

    def report(self):
        L = [f"kinematic reduction{': ' + self.tag if self.tag else ''}",
             f"  v_px      {self.v_px:.1f} px/s" + (f"  ({self.v_px / self.fps:.2f} px/frame at {self.fps:g} fps)" if self.fps else ""),
             f"  k         {self.scale.k:.1f} px/rad  [{self.scale.source}: {self.scale.detail}]"
             if self.scale.known else f"  k         UNKNOWN  [{self.scale.detail}]"]
        if self.omega is not None:
            L.append(f"  omega     {self.omega:.4f} rad/s  ({math.degrees(self.omega):.2f} deg/s)")
        else:
            L.append("  omega     UNKNOWN -- without k there is no angular rate, and no speed")

        bl = body_lengths_per_s(self.v_px, self.size_px)
        if bl:
            L.append(f"  v/size    {bl:.1f} body-lengths/s  [needs no k, no R, no FOV; {RESOLVED}]")
        if self.ref:
            v = scale_bar_speed(self.v_px, self.ref["px"], self.ref["len_m"], self.ref.get("range_ratio", 1.0))
            L.append(f"  scale bar {v:.1f} m/s ({v * 1.94384:.0f} kn) at the reference's range "
                     f"[{self.ref.get('what', 'reference')}, {self.ref['len_m']:g} m over {self.ref['px']:g} px; "
                     "FOV cancels, range ratio does not]")

        if self.fit and not self.fit.get("uniform", True):
            L.append(f"  !! NOT UNIFORM: the fit residual is {self.fit['resid_rms']:.0f} px, "
                     f"{self.fit['resid_frac']:.0%} of the {self.fit['span_px']:.0f} px covered. "
                     "The motion is not a straight line at constant rate, so this v_px does not "
                     "describe it and nothing below should be quoted.")
            L.append("     If the camera is moving, the meaningful rate is against the "
                     "background, not the frame: use `mcdonald layers`.")
        if self.missing:
            L.append("  missing:  " + ", ".join(self.missing))
        if self.speed() is not None:
            lb = self.lower_bound()
            L.append(f"  |v_obj - v_own| = {self.speed():.0f} m/s (Mach {self.speed() / A_SOUND:.2f}) "
                     f"at R = {self.R_m:g} m, theta = {self.theta_deg or 90:.0f} deg")
            L.append(f"  lower bound (theta = 90 deg): {lb:.0f} m/s (Mach {lb / A_SOUND:.2f}) at that range")
            L.append("  This is RELATIVE speed. A stationary object seen from a moving platform "
                     "already has |v_obj - v_own| = |v_own|.")
        elif self.omega is not None:
            L.append("  No range, so no speed. At range R the relative speed is at least "
                     f"{self.omega:.4f} * R m/s (theta = 90 deg); scale it up by 1/sin(theta) otherwise.")
        else:
            L.append("  Nothing here converts to m/s. Report v_px and the unknowns, not a speed.")
        return "\n".join(L)

    def __repr__(self):
        return self.report()
