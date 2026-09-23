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
