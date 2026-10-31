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
HELD_SPAN_PX = 5.0       # a track that covers less than this, with a residual within its noise, is held, not "not uniform"
HELD_FLOOR_PX = 0.1      # ... the noise taken as at least this: a track written to 0.01 px that never moves has no noise to
                         # measure (the Yemen object read against its reticle, 2026-10-29: "NOT uniform" on a still point)
RESOLVED = ("a body length only if the object shows its own shape: "
            "for a point, the size is the blur, not the body")


# ---- the angular scale, with its provenance --------------------------------------------
class AngularScale:
    """k, in pixels per radian, and where it came from.

    Carrying the provenance is the point. A k read off a graticule the sensor
    itself draws is a measurement; a k derived from an assumed field of view is
    an assumption, and anything computed from it inherits that status. `lens`, where
    one was given (`lens.Lens`: its radial term and focal length), says what the scale
    was read through: k is then the lens's own along the track, not a pinhole's."""

    def __init__(self, k, source, alpha_deg=0.0, detail="", lens=None):
        self.k = None if k is None else float(k)
        self.source = source
        self.alpha_deg = alpha_deg
        self.detail = detail
        self.lens = lens

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
                            self.source, alpha_deg, self.detail, self.lens)

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
      Except where the object hardly moves: a track held at a camera's
      boresight covers a pixel or two, and any residual is a large fraction of
      that. Under HELD_SPAN_PX, a residual within twice the position noise
      (from second differences of consecutive frames, `noise_px`) is the
      noise: the track is `held`, and a rate of about zero describes it (FLIR1's
      locked stretch: 0.65 px over a 2.4 px span was called "not uniform").

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
    fk = a[s, 0][keep]
    ok = (np.diff(fk[:-1]) == 1) & (np.diff(fk[1:]) == 1)
    noise = None
    if ok.sum() >= 3:
        d2 = np.concatenate([(v[2:] - 2 * v[1:-1] + v[:-2])[ok] for v in (xk, yk)])
        noise = float(1.4826 * np.median(np.abs(d2 - np.median(d2))) / math.sqrt(6.0))
    held = bool(span < HELD_SPAN_PX and noise is not None and resid <= max(2.0 * math.sqrt(2.0) * noise, HELD_FLOOR_PX))
    return dict(v_px=float(math.hypot(vx, vy)), vx=float(vx), vy=float(vy),
                direction_deg=float(math.degrees(math.atan2(vx, -vy)) % 360),
                resid_rms=resid, n=int(keep.sum()), n_in=n_in,
                n_clipped=int(n_in - keep.sum()),
                t0=float(tk.min()), t1=float(tk.max()), span_px=span,
                resid_frac=float(resid / span) if span > 0 else None, noise_px=noise, held=held,
                uniform=bool((span > 0 and resid / span < 0.05) or held))


# ---- the speed band: v(t) from the track's own covariance (K1, 2026-10-28) -------------------------
# `fit_v_px` is one line with white jitter about it, and its `uniform` flag is how it notices the line is wrong.
# The kriging survey (2026-10-15/16, §1.1-1.2) fitted every recorded track and found none of 23 is that: the
# scatter about the line is the path bending (0.4-134 px), while the jitter itself -- the nugget, how well the
# detector holds the object -- is 0.1-1.5 px. With the two told apart, the rate at every instant has a band
# up to 13 times tighter than a frame-to-frame difference (median 8), and a track that bends has a speed after
# all: one that changes, described rather than refused.
BAND_MIN = 10            # points a band needs
BAND_NMAX = 450         # the points one fit holds at once (15 s at 30 fps); a longer track is fitted on its middle and read window by window
BAND_DLNL = 10.0         # the log-likelihood gain over a line + white jitter past which the velocity is said to change
BAND_Z = 3.0             # the mean acceleration's sigmas past which the speed is said to have changed over the stretch
BEAT_DLNL = 10.0         # the log-likelihood gain past which a rhythm left in the band is held as a beat beside the wander (M8)
BEAT_CYCLES = 3.0        # and the cycles of it the fitted stretch must hold (a slower rhythm is the wander's own)
HARMONIC_NEAR = 0.15     # a rhythm left within this share of twice the beat's rate is its first harmonic, held beside it


def _band_points(track, fps, t0=None, t1=None, n0=None, n1=None):
    """(frame, t, x, y) of the track inside the window, finite, in order, exact repeats of the previous
    frame dropped (a frame the display did not update is the previous picture again: read as a
    measurement it shrinks the nugget and fakes a velocity step)."""
    if isinstance(track, dict):
        a = np.array([[n, xy[0], xy[1]] for n, xy in sorted(track.items())], float)
    else:
        a = np.asarray(track, float)
    if a.ndim != 2 or len(a) == 0:
        return None
    a = a[np.argsort(a[:, 0])]
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
    a, t = a[s], t_all[s]
    if len(a) < 2:
        return a[:, 0], t, a[:, 1], a[:, 2], 0
    rep = np.r_[False, (np.diff(a[:, 0]) == 1) & (np.diff(a[:, 1]) == 0) & (np.diff(a[:, 2]) == 0)]
    return a[~rep, 0], t[~rep], a[~rep, 1], a[~rep, 2], int(rep.sum())


# ---- jumps named: a glitch, an excursion or a step (E4, 2026-10-29) ----------------------------------------------
# The band dropped a point more than four of its own leave-one-out sigmas off its fit, once: nothing said which kind
# of jump it was, and nothing held how often the clip fires on a clean track (the economics survey, 2026-10-28, §1.2
# and §6.2). Each increment of the track is held instead against its neighbours' scale -- the local median rate
# taken out, a robust scale over a second either side, as Lee & Mykland (2008) hold a price's -- and the threshold is
# drawn on the track's own frames and gaps, not read off the normal table: with a second's window the scale is
# itself uncertain by ~15 %, and the table's familywise 1 % named jumps on 12 of 100 white tracks. A jump found is
# named by the shape it leaves, as X-13ARIMA-SEATS names outliers (Chen & Liu 1993): a *glitch*, one point off and
# back (an additive outlier); an *excursion*, a few points off and back (a temporary change); a *step*, off for good
# (a level shift). The points of a glitch or an excursion are the track's slips, and the band is fitted without
# them; a step is kept and named -- the track moved to something else, a held picture caught up, or the camera's
# field changed, and dropping points cannot undo any of those.
JUMP_ALPHA = 0.01        # the jump test's familywise false alarm: one clean track in a hundred has a jump named
JUMP_DRAWS = 400         # white tracks on the track's own frames and gaps that the threshold is drawn from
JUMP_FLOOR_PX = 0.1      # px a coordinate: the least jitter a jump is held against (a centroid is read to about this; a drawn or interpolated track has none)
JUMP_BACK = 5            # points: a track off for at most this many, and back, made an excursion; off longer, a step
JUMP_SEED = 20261029     # the draws' seed: the same frames give the same threshold every time
GRIDS = (1.0, 0.5, 0.25, 0.2, 0.1, 0.05, 0.02, 0.01)   # px: the grids a track's coordinates may be written on
_JUMP_U = {}             # the thresholds drawn, by the frames' gaps and the window


def _jump_scale(d, g, w):
    """(r, s) for increments d (..., n) over gaps g (n): r each increment's rate less the local median rate (px a
    frame: over a gap of several frames a wandering velocity moves the increment by the gap's length, its rate not),
    s 1.4826 times the median absolute deviation of r -- each over the w increments centred on it, reflected at the
    ends: a robust local scale (a median, where Lee & Mykland's bipower variation would be pulled up by a glitch's two
    large increments side by side)."""
    from numpy.lib.stride_tricks import sliding_window_view
    pad = [(0, 0)] * (d.ndim - 1) + [(w // 2, w // 2)]
    rate = d / g
    r = rate - np.median(sliding_window_view(np.pad(rate, pad, mode="reflect"), w, axis=-1), axis=-1)
    win = sliding_window_view(np.pad(r, pad, mode="reflect"), w, axis=-1)
    s = 1.4826 * np.median(np.abs(win - np.median(win, axis=-1, keepdims=True)), axis=-1)
    return r, s


def _jump_threshold(g, w):
    """The (1 - JUMP_ALPHA) quantile of the largest jump statistic over JUMP_DRAWS tracks of white jitter on these
    gaps, both coordinates (the statistic is scale-free on them, so the draws need no scale)."""
    key = (int(w), np.asarray(g, float).tobytes())
    if key not in _JUMP_U:
        rng = np.random.default_rng(JUMP_SEED)
        n = len(g)
        chunk = max(1, int(1e7 // (2 * n * w)))
        top = []
        for b in range(0, JUMP_DRAWS, chunk):
            z = rng.standard_normal((2, min(chunk, JUMP_DRAWS - b), n + 1))
            r, s = _jump_scale(np.diff(z, axis=-1), g, w)
            top.append(np.hypot(*(r / np.maximum(s, 1e-12))).max(axis=-1))
        _JUMP_U[key] = float(np.quantile(np.concatenate(top), 1.0 - JUMP_ALPHA))
    return _JUMP_U[key]


def grid_of(*vs):
    """The coarsest of GRIDS that every coordinate is written on (px), or 0 where they are not on one."""
    v = np.concatenate([np.asarray(a, float).ravel() for a in vs])
    for q in GRIDS:
        if np.all(np.abs(v / q - np.round(v / q)) < 1e-6):
            return q
    return 0.0


def jumps(frames, x, y, fps):
    """The track's jumps, named (E4): each increment's residual from the local median rate, over the local robust
    scale (at least JUMP_FLOOR_PX of jitter a coordinate, and the rounding of the grid the track is written on: a
    quantised track's scale collapses), both coordinates together, against the threshold drawn on the track's own
    frames and gaps (`_jump_threshold`: a clean track has a jump named one time in a hundred). Each one found is a
    *glitch* where the next increment takes it back, an *excursion* where the track is back within JUMP_BACK points,
    else a *step*; an end point off its neighbours is a glitch (nothing beyond it says otherwise).

    Returns None under BAND_MIN points; else dict(threshold, alpha, window (increments), floor_px, grid_px, flags:
    [dict(kind, frame (the first point off, or the step's), off (the frames of a glitch's or an excursion's points),
    px (the jump's size), L (its statistic))], drop: a bool a point, True for the points of glitches and excursions)."""
    frames, x, y = (np.asarray(v, float) for v in (frames, x, y))
    n = len(frames) - 1                                   # increments
    if n + 1 < BAND_MIN:
        return None
    g = np.diff(frames)
    w = min(2 * max(10, int(round(float(fps)))) + 1, n if n % 2 else n - 1)
    rr, s = _jump_scale(np.stack([np.diff(x), np.diff(y)]), g, w)
    r = rr * g                                            # each residual as the displacement it is, px
    q = grid_of(x, y)
    floor = max(math.sqrt(2.0) * JUMP_FLOOR_PX, q / math.sqrt(6.0))   # an increment's: two points' jitter, or their rounding
    L = np.hypot(*(rr / np.maximum(s, floor)))
    u = _jump_threshold(g, w)
    flags, drop = [], np.zeros(n + 1, bool)
    size = lambda v: float(math.hypot(v[0], v[1]))
    i = 0
    while i < n:
        if L[i] <= u:
            i += 1
            continue
        big = size(r[:, i])
        kind, off, nxt = "step", [], i + 1
        if i == n - 1:
            kind, off = "glitch", [n]                         # the last point off
        elif i > 0 and not drop[i] and size(r[:, i - 1] + r[:, i]) < 0.5 * big <= size(r[:, i - 1]):
            kind, off = "glitch", [i]                         # the way back from a point whose way out fell short of the threshold
        elif size(r[:, i] + r[:, i + 1]) < 0.5 * big:
            kind, off, nxt = "glitch", [i + 1], i + 2         # the next increment takes it back
        else:
            for m in range(2, JUMP_BACK + 1):
                if i + m >= n:
                    break
                if size(r[:, i:i + m + 1].sum(axis=1)) < 0.5 * big:
                    kind, off, nxt = "excursion", list(range(i + 1, i + m + 1)), i + m + 1
                    break
            if kind == "step" and i == 0:
                kind, off = "glitch", [0]                     # the first point off
        drop[off] = True
        flags.append(dict(kind=kind, frame=int(frames[off[0]] if off else frames[i + 1]),
                          off=[int(frames[j]) for j in off], px=round(big, 2), L=round(float(L[i]), 1)))
        i = nxt
    return dict(threshold=u, alpha=JUMP_ALPHA, window=int(w), floor_px=floor, grid_px=q, flags=flags, drop=drop)


def _windows(n, n_max):
    """[(start, stop)] of the windows a series of n points is read in: one where it fits, else windows
    of n_max every n_max / 2 (the last ending at n), each point read from the window whose middle is
    nearest -- a moving neighbourhood, so a long track's local trend is its own."""
    if n <= n_max:
        return [(0, n)]
    step = max(n_max // 2, 1)
    starts = list(range(0, n - n_max + 1, step))
    if starts[-1] != n - n_max:
        starts.append(n - n_max)
    return [(s, s + n_max) for s in starts]


def _read_band(models, tk, xk, yk, tm, dt, n_max):
    """The band read off its fitted models window by window, each window with its own trend: (rate {coordinate: (the
    rate at every point, its sd)}, innov {coordinate: each point's one-step innovation, from the window that reads it},
    ends {coordinate: the average velocity over the stretch and its change, with their errors}, the windows)."""
    from . import kriging as kg
    n = len(tk)
    span = float(tk[-1] - tk[0])
    wins = _windows(n, n_max)
    mids = np.array([(a + b) / 2.0 for a, b in wins])
    owner = np.argmin(np.abs(np.arange(n)[:, None] - mids[None, :]), axis=1)
    rate = {name: (np.empty(n), np.empty(n)) for name in ("x", "y")}
    innov = {name: np.empty(n) for name in ("x", "y")}
    ends, local = {}, {}
    for w, (a, b) in enumerate(wins):
        sel = np.nonzero(owner == w)[0]
        for name, v in (("x", xk), ("y", yk)):
            m = models[name] if len(wins) == 1 else kg.Model(tk[a:b], v[a:b], tm, theta=models[name].theta, dt=dt)
            local[(name, w)] = m
            mu, var = m.predict(tk[sel], "df")
            rate[name][0][sel], rate[name][1][sel] = mu, np.sqrt(var)
            innov[name][sel] = m.innovations()[sel - a]
    for name in ("x", "y"):
        first, last = local[(name, 0)], local[(name, len(wins) - 1)]
        if len(wins) == 1:
            mf, Cf = first.joint([tk[0], tk[-1]], "f")
            mv, Cv = first.joint([tk[0], tk[-1]], "df")
        else:                                                  # far apart: independent
            m0, v0 = first.predict([tk[0]], "f")
            m1, v1 = last.predict([tk[-1]], "f")
            mf, Cf = np.r_[m0, m1], np.diag(np.r_[v0, v1])
            m0, v0 = first.predict([tk[0]], "df")
            m1, v1 = last.predict([tk[-1]], "df")
            mv, Cv = np.r_[m0, m1], np.diag(np.r_[v0, v1])
        ends[name] = dict(vbar=float((mf[1] - mf[0]) / span), vbar_err=float(math.sqrt(max(Cf[0, 0] + Cf[1, 1] - 2 * Cf[0, 1], 0.0)) / span),
                          dv=float(mv[1] - mv[0]), dv_err=float(math.sqrt(max(Cv[0, 0] + Cv[1, 1] - 2 * Cv[0, 1], 0.0))))
    return rate, innov, ends, wins


def _held_better(new, old):
    """Whether a band with M8's beat (`new`, its backtest) is the better held to its track than without (`old`): less left
    in its innovations (Ljung-Box's least p higher) and missing no more often (its Basel zone no worse)."""
    if not new or not old:
        return False
    zone = lambda bt: 0 if bt["zone_p"] < BASEL[0] else 1 if bt["zone_p"] < BASEL[1] else 2
    return min(new["ljung_box_p"]) > min(old["ljung_box_p"]) and zone(new) <= zone(old)


def speed_band(track, fps, t0=None, t1=None, n0=None, n1=None, n_max=BAND_NMAX):
    """The track's rate along it with a band, from its own covariance (`kriging`): each coordinate against
    wall-clock time as a line plus a Matérn-3/2 wander plus a nugget, the three fitted by REML; the rate at
    every kept frame kriged from it with its sd; the average velocity over the stretch, (f(t1) - f(t0)) / T
    on the latent path, with an honest error; the velocity's change over the stretch (the mean acceleration)
    with its sigma; and the evidence that the velocity changes at all, as a log-likelihood ratio against a
    line with white jitter (both REML, the same mean) -- not a refusal. The track's jumps are named first
    (`jumps`: a glitch, an excursion or a step, against a threshold drawn on its own frames), and the points of
    its glitches and excursions -- the linker catching a neighbour or a wing for a frame or a few -- are left
    out of the fit; a step is kept, and named. A track longer than n_max is fitted on its middle n_max points
    and read in windows of n_max (`_windows`).

    Returns None under BAND_MIN points; else a dict of plain values (the `band` the kinematics stage
    records) and `series`, the rate frame by frame (frame, t_s, vx, vy, sd_vx, sd_vy, speed, sd_speed),
    which the stage writes beside the case as a CSV."""
    from . import kriging as kg
    got = _band_points(track, fps, t0, t1, n0, n1)
    if got is None:
        return None
    frames, t, x, y, repeats = got
    n_in = len(t)
    if n_in < BAND_MIN:
        return None
    dt = 1.0 / float(fps)
    jp = jumps(frames, x, y, fps)                          # the slips named, before the fit
    keep = ~jp["drop"] if jp is not None and int((~jp["drop"]).sum()) >= BAND_MIN else np.ones(n_in, bool)
    clipped = int(n_in - keep.sum())
    tk, fk, xk, yk = t[keep], frames[keep], x[keep], y[keep]
    n = len(tk)
    tm = float(tk.mean())
    lo = 0 if n <= n_max else (n - n_max) // 2
    models = {name: kg.Model(tk[lo:lo + n_max], v[lo:lo + n_max], tm, dt=dt)       # the covariance, from the middle (or all)
              for name, v in (("x", xk), ("y", yk))}
    span = float(tk[-1] - tk[0])
    rate, innov, ends, wins = _read_band(models, tk, xk, yk, tm, dt, n_max)
    plain = models                                          # the wander alone: its evidence says whether the velocity changes
    bt = backtest(innov, tk)
    beat = None
    hz = (bt or {}).get("rhythm_hz")
    if hz and hz * min(span, n_max * dt) >= BEAT_CYCLES and hz < 0.5 / dt:
        # a rhythm left in the innovations: the wander and a beat beside it (M8), each coordinate apart where it gains
        tried = {name: kg.Model(tk[lo:lo + n_max], v[lo:lo + n_max], tm, dt=dt, warm=models[name].theta, beat=hz)
                 for name, v in (("x", xk), ("y", yk))}
        gain = {name: (models[name].val - tried[name].val) / 2.0 for name in tried}
        if max(gain.values()) >= BEAT_DLNL:
            trial = {name: tried[name] if gain[name] >= BEAT_DLNL else models[name] for name in models}
            read = _read_band(trial, tk, xk, yk, tm, dt, n_max)
            bt_t = backtest(read[1], tk)
            h = [trial[name].theta[5] for name in trial if len(trial[name].theta) > 3]
            if bt_t and bt_t.get("rhythm_hz") and abs(bt_t["rhythm_hz"] / (2.0 * h[0]) - 1.0) < HARMONIC_NEAR and 2.0 * h[0] < 0.5 / dt:
                # what is left is the beat's first harmonic (a wingbeat's trace is no sine): on the same envelope
                more = {name: kg.Model(tk[lo:lo + n_max], v[lo:lo + n_max], tm, dt=dt, warm=trial[name].theta, beat=trial[name].theta[5],
                                       harmonic=True) for name, v in (("x", xk), ("y", yk)) if len(trial[name].theta) > 3}
                more = {name: m for name, m in more.items() if (trial[name].val - m.val) / 2.0 >= BEAT_DLNL}
                if more:
                    trial2 = {name: more.get(name, trial[name]) for name in trial}
                    read2 = _read_band(trial2, tk, xk, yk, tm, dt, n_max)
                    bt2 = backtest(read2[1], tk)
                    if _held_better(bt2, bt_t):
                        trial, read, bt_t = trial2, read2, bt2
            th = {name: trial[name].theta for name in ("x", "y")}
            kept = _held_better(bt_t, bt)                 # the beat is kept where it leaves less, missing no more often
            beat = dict(kept=kept, hz=[float(th[name][5]) if len(th[name]) > 3 else None for name in th],
                        sill_px=[float(math.sqrt(th[name][3])) if len(th[name]) > 3 else None for name in th],
                        harmonic_px=[float(math.sqrt(th[name][6])) if len(th[name]) > 6 else None for name in th],
                        range_s=[float(th[name][4]) if len(th[name]) > 3 else None for name in th],
                        gain=[float(gain[name]) for name in ("x", "y")], rhythm_hz=float(hz), without=bt,
                        light_with=bt_t["light"] if bt_t else None)
            if kept:
                models = trial
                rate, innov, ends, wins = read
                bt = bt_t
    theta = {name: m.theta for name, m in models.items()}
    vx, sx = rate["x"]
    vy, sy = rate["y"]
    speed = np.hypot(vx, vy)
    with np.errstate(invalid="ignore", divide="ignore"):
        s_speed = np.where(speed > 0, np.sqrt(vx ** 2 * sx ** 2 + vy ** 2 * sy ** 2) / np.where(speed > 0, speed, 1.0),
                           np.sqrt((sx ** 2 + sy ** 2) / 2.0))
    vbx, vby = ends["x"]["vbar"], ends["y"]["vbar"]
    v_mean = float(math.hypot(vbx, vby))
    v_mean_err = (float(math.sqrt(vbx ** 2 * ends["x"]["vbar_err"] ** 2 + vby ** 2 * ends["y"]["vbar_err"] ** 2) / v_mean)
                  if v_mean > 0 else float(math.sqrt((ends["x"]["vbar_err"] ** 2 + ends["y"]["vbar_err"] ** 2) / 2.0)))
    dvx, dvy = ends["x"]["dv"], ends["y"]["dv"]
    dv = float(math.hypot(dvx, dvy))
    dv_err = (float(math.sqrt(dvx ** 2 * ends["x"]["dv_err"] ** 2 + dvy ** 2 * ends["y"]["dv_err"] ** 2) / dv)
              if dv > 0 else float(math.sqrt((ends["x"]["dv_err"] ** 2 + ends["y"]["dv_err"] ** 2) / 2.0)))
    accel, accel_err = dv / span, dv_err / span
    d0, d1 = math.atan2(vx[0], -vy[0]), math.atan2(vx[-1], -vy[-1])
    turn = float(abs((math.degrees(d1 - d0) + 180.0) % 360.0 - 180.0))
    at = lambda i: [float(tk[i]), float(speed[i]), float(s_speed[i])]
    one = np.diff(fk) == 1                                  # what single pairs of consecutive frames read, their scatter
    pairs_sd = (float(math.sqrt((np.var(np.diff(xk)[one]) + np.var(np.diff(yk)[one])) / 2.0)) * float(fps)
                if one.sum() >= 3 else None)
    i_min, i_max = int(np.argmin(speed)), int(np.argmax(speed))
    dlnl = float(sum(m.dlnl for m in plain.values()))
    nug = [float(math.sqrt(theta[name][2])) for name in ("x", "y")]
    loo_z = {name: models[name].loo() for name in models} if len(wins) == 1 else None
    band = dict(
        kernel="a line, a Matérn-3/2 wander and a nugget, fitted by REML; the rate kriged from it" + (
            f" (and a beat near {next(h for h in beat['hz'] if h):.1f} Hz beside the wander, the Matérn times a cosine: the rate is the wander's)"
            if beat and beat["kept"] else ""),
        n=int(n), n_in=int(n_in), repeats_dropped=int(repeats), clipped=int(clipped), t0=float(tk[0]), t1=float(tk[-1]),
        nugget_px=nug, sill_px=[float(math.sqrt(theta[name][0])) for name in ("x", "y")],
        range_s=[float(theta[name][1]) for name in ("x", "y")],
        dlnl=dlnl, constant=bool(dlnl < BAND_DLNL),
        v_mean_px_per_s=v_mean, v_mean_err_px_per_s=v_mean_err, vx_mean=vbx, vy_mean=vby,
        direction_deg=float(math.degrees(math.atan2(vbx, -vby)) % 360),
        v_start=at(0), v_end=at(n - 1), v_min=at(i_min), v_max=at(i_max),
        dv_px_per_s=dv, dv_err_px_per_s=dv_err, dv_xy=[dvx, dvy], dv_err_xy=[ends["x"]["dv_err"], ends["y"]["dv_err"]], turn_deg=turn,
        accel_px_per_s2=accel, accel_err_px_per_s2=accel_err, accel_z=float(accel / accel_err) if accel_err > 0 else None,
        band_err_px_per_s=float(np.median(s_speed)),
        pair_err_px_per_s=float(math.sqrt(nug[0] ** 2 + nug[1] ** 2) * math.sqrt(2.0) * float(fps)),
        pairs_sd_px_per_s=pairs_sd,
        loo_z_sd=[float(np.std(loo_z[name])) for name in ("x", "y")] if loo_z else None,
        loo_beyond_3=[float(np.mean(np.abs(loo_z[name]) > 3)) for name in ("x", "y")] if loo_z else None,
        windows=len(wins), backtest=bt, beat=beat,
        jumps=None if jp is None else dict(threshold=round(jp["threshold"], 2), alpha=jp["alpha"], floor_px=round(jp["floor_px"], 3),
                                           grid_px=jp["grid_px"], flags=jp["flags"]))
    band["change_bound"] = change_bound(band, tk, xk, yk)
    series = dict(frame=fk.astype(int).tolist(), t_s=tk.tolist(), vx=vx.tolist(), vy=vy.tolist(),
                  sd_vx=sx.tolist(), sd_vy=sy.tolist(), speed=speed.tolist(), sd_speed=s_speed.tolist())
    return band, series


# ---- the band held to its own track (E1, 2026-10-29) ----------------------------------------------------------------
# A bank's value-at-risk model states a quantile of tomorrow's loss every day, and its supervisor checks it with no
# truth to hand by counting the days the loss went past it (the economics survey, 2026-10-28, §1.4 and §6.4). The band
# states an error the same way at every point: its one-step innovations (`kriging.Model.innovations`) are N(0, 1),
# each independent of the last, where the band's model is the track's. So the band is held to its own track, with no
# ground truth: how many innovations miss by more than 1.96 (Kupiec 1995; 5 % stated), whether the misses come together
# (Christoffersen 1998), whether a rhythm is left in them (Ljung & Box 1978), whether the jitter changes along the track
# (Engle's ARCH test, 1982), and the tails (Jarque & Bera 1987). The light is the Basel Committee's (1996) for the
# count of misses -- green while that many or fewer would come 95 % of the time from a band that is right, red past
# 99.99 % -- and yellow besides where any of the other four fails: the band is then right on average along the track,
# not frame by frame, and the reason says how.
BACKTEST_MIN = 30        # points the backtest needs (fewer, and its tests have no power)
BACKTEST_Z = 1.959964    # an innovation past this many of its sds is a miss: 5 % of them, where the band is right
BACKTEST_P = 0.01        # a test of the innovations fails under this p, the two coordinates together (each held at half)
BACKTEST_LAGS = 10       # Ljung-Box's lags
ARCH_LAGS = 5            # the ARCH test's lags
BASEL = (0.95, 0.9999)   # the binomial probability of so many misses or fewer past which the light is yellow, then red
TAIL_Z = 4.0             # an innovation past this many sds is counted among the tails
SLOW_HZ = 1.0            # Hz: a rhythm left slower than this is said as something slow, not as a rhythm


def _christoffersen(miss):
    """Christoffersen's (1998) independence test: whether a miss follows a miss more often than it follows a hit (a
    first-order Markov chain against independence), as p."""
    from scipy import stats
    a, b = miss[:-1], miss[1:]
    n = [[int(np.sum(~a & ~b)), int(np.sum(~a & b))], [int(np.sum(a & ~b)), int(np.sum(a & b))]]

    def ll(k0, k1):                      # the log-likelihood of k1 misses in k0 + k1 at their own rate
        t = k0 + k1
        p = k1 / t if t else 0.0
        return (k0 * math.log(1 - p) if 0 < t and p < 1 else 0.0) + (k1 * math.log(p) if p > 0 else 0.0)
    lr = -2.0 * (ll(n[0][0] + n[1][0], n[0][1] + n[1][1]) - ll(*n[0]) - ll(*n[1]))
    return float(stats.chi2.sf(max(lr, 0.0), 1))


def _ljung_box(w, lags):
    from scipy import stats
    w = w - w.mean()
    g0 = float(w @ w)
    n = len(w)
    q = n * (n + 2) * sum((float(w[:-k] @ w[k:]) / g0) ** 2 / (n - k) for k in range(1, lags + 1)) if g0 > 0 else 0.0
    return float(stats.chi2.sf(q, lags))


def _arch(w, lags):
    """Engle's ARCH-LM test: the squared innovations regressed on their own lags, n R^2 against chi-square, as p."""
    from scipy import stats
    e2 = w ** 2
    Y = e2[lags:]
    X = np.c_[np.ones(len(Y)), np.column_stack([e2[lags - k:-k] for k in range(1, lags + 1)])]
    res = Y - X @ np.linalg.lstsq(X, Y, rcond=None)[0]
    tot = float(((Y - Y.mean()) ** 2).sum())
    return float(stats.chi2.sf(len(Y) * (1.0 - float(res @ res) / tot), lags)) if tot > 0 else 1.0


def backtest(innov, t):
    """The band held to its own track: its one-step innovations {coordinate: array} at the times t (s). Returns None
    under BACKTEST_MIN points; else dict(light ("green", "yellow" or "red"), reasons [plain words], n, misses, share
    (of the innovations past +-1.96: 5 % stated), zone_p (the binomial probability of so many misses or fewer, the
    Basel zone's), kupiec_p, and by coordinate christoffersen_p, ljung_box_p, arch_p, jarque_bera_p, sd; tails (past
    TAIL_Z sds), rhythm_hz (the strongest rhythm left, where Ljung-Box fails))."""
    from scipy import stats
    w = {name: np.asarray(v, float) for name, v in innov.items()}
    n = len(t)
    if n < BACKTEST_MIN:
        return None
    N = sum(len(v) for v in w.values())
    miss = {name: np.abs(v) > BACKTEST_Z for name, v in w.items()}
    x = int(sum(int(m.sum()) for m in miss.values()))
    zone_p = float(stats.binom.cdf(x - 1, N, 0.05)) if x > 0 else 0.0
    kupiec_p = float(stats.binomtest(x, N, 0.05).pvalue)
    lags, alags = min(BACKTEST_LAGS, n // 5), min(ARCH_LAGS, n // 10)
    got = {name: dict(christoffersen_p=_christoffersen(miss[name]), ljung_box_p=_ljung_box(v, lags), arch_p=_arch(v, alags),
                      jarque_bera_p=float(stats.jarque_bera(v).pvalue), sd=float(np.std(v)), kurtosis=float(stats.kurtosis(v)))
           for name, v in w.items()}
    low = lambda key: min(g[key] for g in got.values())
    half = BACKTEST_P / len(w)
    tails = int(sum(int(np.sum(np.abs(v) > TAIL_Z)) for v in w.values()))
    rhythm = None
    reasons = []
    light = "red" if zone_p >= BASEL[1] else "yellow" if zone_p >= BASEL[0] else "green"
    if light != "green":
        reasons.append(f"it misses {x} of its {N} one-step predictions ({100 * x / N:.1f} %) where a right band misses 5 %: "
                       "it is too narrow for this track")
    elif kupiec_p < BACKTEST_P:
        reasons.append(f"it misses {x} of its {N} one-step predictions ({100 * x / N:.1f} %) where a right band misses 5 %: "
                       "it is wider than it need be")
    if low("christoffersen_p") < half:
        reasons.append("its misses come together: the band is too narrow in places and too wide in others")
    if low("ljung_box_p") < half:
        name = min(got, key=lambda k: got[k]["ljung_box_p"])
        v = w[name] - w[name].mean()
        dt = float(np.median(np.diff(t))) if n > 1 else 1.0
        power = np.abs(np.fft.rfft(v)) ** 2
        f = np.fft.rfftfreq(len(v), dt)
        rhythm = float(f[int(np.argmax(power[1:])) + 1])
        reasons.append(f"a rhythm is left in it, strongest near {rhythm:.1f} Hz: the track moves in a way its model does not "
                       "hold (a wingbeat, a sway, the camera's shake)" if rhythm >= SLOW_HZ else
                       f"something slow is left in it, strongest near {rhythm:.1f} Hz: a change its wander does not hold "
                       "(the camera's turn, or the object's own)")
    if low("arch_p") < half:
        reasons.append("its jitter changes along the track")
    if low("jarque_bera_p") < half:
        name = min(got, key=lambda k: got[k]["jarque_bera_p"])
        reasons.append("its errors have tails heavier than a normal's" + (f": {tails} past {TAIL_Z:.0f} sds, jumps or slips "
                       "the band kept" if tails else "") if got[name]["kurtosis"] > 0 else
                       "its errors are not shaped as a normal's: lopsided, or with tails lighter than a normal's")
    if light == "green" and reasons:
        light = "yellow"
    return dict(light=light, reasons=reasons, n=int(n), misses=x, share=float(x / N), zone_p=zone_p, kupiec_p=kupiec_p,
                tails=tails, rhythm_hz=rhythm, **{key: [got[name][key] for name in ("x", "y")] for key in
                                                  ("christoffersen_p", "ljung_box_p", "arch_p", "jarque_bera_p", "sd", "kurtosis")})


def backtest_said(bt, beat=None):
    """The backtest (`backtest`) in a sentence: the light, the count of misses against the 5 % stated, the reasons, and
    a beat held beside the wander (M8, `beat`) with what the light was without it."""
    if not bt:
        return None
    head = (f"{bt['light']}: {bt['misses']} of its {2 * bt['n']} one-step predictions missed by more than 1.96 of their "
            f"sds ({100 * bt['share']:.1f} %, 5 % stated)")
    held = ""
    if beat:
        hz = [h for h in beat["hz"] if h]
        what = f"a beat at {hz[0]:.1f} Hz" + (" with its first harmonic" if any(beat.get("harmonic_px") or []) else "")
        held = (f"; a rhythm near {beat['rhythm_hz']:.1f} Hz was left in it, and is held beside the wander as {what} (the "
                f"light without it {beat['without']['light']}; the rate is the wander's)" if beat.get("kept", True) else
                f"; a rhythm near {beat['rhythm_hz']:.1f} Hz is left in it: held beside the wander as {what} it left more in "
                f"the band's errors or missed more often ({beat['light_with']}), so the band keeps its wander alone")
    if bt["light"] == "green":
        return head + ", the misses apart, nothing left in them: its errors are honest frame by frame" + held
    return (head + "; " + "; ".join(bt["reasons"]) + ("" if bt["light"] == "red" else
            " -- its error is right on average along the track, not frame by frame") + held)


def backtest_short(bt):
    """The light and its first reason, short, for the summary's row: "green", "yellow (its misses come together)"."""
    if not bt:
        return None
    return bt["light"] + (f" ({bt['reasons'][0].split(':')[0].split(', strongest')[0].split(' (')[0]})" if bt["reasons"] else "")


# ---- "constant" as an upper bound (E12, 2026-10-29) ----------------------------------------------------------------
# A band that says its speed is constant -- no wander past the jitter, Δln L under BAND_DLNL -- says that no change was
# seen, not that there was none: the likelihood of a wander's variance piles up at exactly zero even where the wander
# is there (Shephard & Harvey 1990, the pile-up problem; the economics survey, §1.6), and the band's change of velocity
# then reads 0 ± nothing. Stock & Watson (1998) answered with an interval found by inverting the test. Here the
# alternative is the plainest one a reader means by "its speed changed": a steady change over the stretch. A free
# quadratic's acceleration, its residual taken as white (as the band found it), has an exact interval, and its far end
# is the largest steady change of speed along the track the band could have missed. Where the band sees a wander but
# its change over the stretch is within BAND_Z of its sigmas, the bound is the larger of its own change's far end and
# the quadratic's.
CHANGE_Z = 1.959964      # the bound's sigmas: the far end of a two-sided 95 % interval


def change_bound(b, t, x, y, z=CHANGE_Z):
    """The largest change of speed along the track the band could have missed (E12), over its stretch: dict(dv_max_px_per_s
    (95 %), dv_px_per_s (the change read along the track), dv_err_px_per_s, span_s, z, by), or None where the band saw the
    change (past BAND_Z of its sigmas). On a constant band, by a free quadratic in each coordinate (its residual white):
    the change 2 c T along the mean direction, its error from the two axes' apart; else the larger of the band's own
    change along the track and the quadratic's, each at its far end (a band's covariance reads a steady change as a
    wander, its rate at the ends drawn toward the line's: on drawn lines with a steady change its own bound held the
    truth 88-90 % of the time alone)."""
    T = float(b["t1"] - b["t0"])
    v = float(b["v_mean_px_per_s"])
    if T <= 0 or not (b["constant"] or (b.get("accel_z") is not None and abs(b["accel_z"]) < BAND_Z)):
        return None
    u = (b["vx_mean"] / v, b["vy_mean"] / v) if v > 0 else None
    along = lambda d, e: ((math.hypot(*d), math.hypot(*e) / math.sqrt(2.0)) if u is None else    # a still object: the velocity's change
                          (d[0] * u[0] + d[1] * u[1], math.hypot(e[0] * u[0], e[1] * u[1])))
    s = np.asarray(t, float) - float(np.mean(t))
    X = np.c_[np.ones(len(s)), s, s ** 2]
    G = np.linalg.inv(X.T @ X)
    dq, eq = [], []
    for c in (x, y):
        coef = G @ (X.T @ np.asarray(c, float))
        r = np.asarray(c, float) - X @ coef
        dq.append(2.0 * float(coef[2]) * T)
        eq.append(2.0 * T * math.sqrt(max(float(r @ r) / max(len(s) - 3, 1) * G[2, 2], 0.0)))
    dv_q, e_q = along(dq, eq)
    if b["constant"]:
        dv, e, by = dv_q, e_q, "a steady change: a free quadratic, its residual white"
    else:
        dv, e = along(b["dv_xy"], b["dv_err_xy"])
        by = "the band's own change and a free quadratic's, the larger"
        if abs(dv_q) + z * e_q > abs(dv) + z * e:
            dv, e = dv_q, e_q
    return dict(dv_max_px_per_s=float(abs(dv) + z * e), dv_px_per_s=float(dv), dv_err_px_per_s=float(e), span_s=T,
                z=float(z), by=by)


def pm(v, e, unit=""):
    """'37.9 ± 0.1', the value written to the error's precision (two figures of the error under 10, one above),
    so that an error never rounds to 0 beside a value written coarser than it."""
    if e is None or not math.isfinite(e) or e <= 0:
        return f"{v:.0f}{unit}"
    d = max(0, 1 - int(math.floor(math.log10(e)))) if e < 10 else 0
    d = min(d, 3)
    return f"{v:.{d}f} ± {e:.{d}f}{unit}"


def band_said(band, fps=None):
    """The speed band in two lines: the average with its error and what the band is worth, and whether
    and how the speed changed. Written from the band's own numbers, so the report cannot disagree with them."""
    b = band
    T = b["t1"] - b["t0"]
    per = f" ({b['v_mean_px_per_s'] / fps:.2f} px/frame)" if fps else ""
    first = (f"{pm(b['v_mean_px_per_s'], b['v_mean_err_px_per_s'])} px/s{per} on average over {T:.2f} s "
             f"({b['n']} points; the detector holds the object to ±{max(b['nugget_px']):.2f} px; "
             + (f"single pairs of frames read the rate ±{b['pairs_sd_px_per_s']:.0f} px/s apart, " if b.get("pairs_sd_px_per_s") else "")
             + f"the band is ±{b['band_err_px_per_s']:.0f})")
    cb = b.get("change_bound")
    if b["constant"]:
        second = (f"constant within its band: a changing velocity gains Δln L = {b['dlnl']:.1f} over a straight line with "
                  f"jitter, under the {BAND_DLNL:.0f} it would take" + (f"; {bound_said(cb)}" if cb else ""))
    else:
        (ts, vs, es), (te, ve, ee) = b["v_start"], b["v_end"]
        (tl, vl, el), (th, vh, eh) = b["v_min"], b["v_max"]
        second = (f"the speed ran from {pm(vs, es)} px/s at {ts:.2f} s to {pm(ve, ee)} at {te:.2f} s "
                  f"(least {pm(vl, el)} at {tl:.2f} s, most {pm(vh, eh)} at {th:.2f} s); its velocity changed by "
                  f"{pm(b['dv_px_per_s'], b['dv_err_px_per_s'])} px/s over the stretch ({b['turn_deg']:.0f}° of direction), "
                  f"a mean acceleration of {pm(b['accel_px_per_s2'], b['accel_err_px_per_s2'])} px/s²"
                  + (f" ({b['accel_z']:.1f} σ)" if b.get("accel_z") is not None else "")
                  + f"; a changing velocity gains Δln L = {b['dlnl']:.0f} over a straight line with jitter"
                  + (f"; within its noise: {bound_said(cb)}" if cb else ""))
    return first, second


def bound_said(cb):
    """E12's bound in words: on a constant band "a steady change of its speed of more than X px/s over the T s would
    have shown (95 %)"; on one whose change is within its noise "its speed along the track changed by less than ..."."""
    x = f"{cb['dv_max_px_per_s']:.{0 if cb['dv_max_px_per_s'] >= 10 else 1}f} px/s over the {cb['span_s']:.1f} s"
    return (f"a steady change of its speed of more than {x} would have shown (95 %)" if cb["by"].startswith("a steady") else
            f"its speed along the track changed by less than {x} (95 %)")


JUMP_WHY = "the track moved to something else, a held picture caught up, or the camera's field changed"


def jumps_said(band, most=4):
    """The jumps the band named (`jumps`) in a sentence: the glitches and excursions left out of its fit as the track's
    slips, and the steps kept, the largest `most` of each with their frames and sizes. None for a band written before
    the test, or too short for it."""
    jp = (band or {}).get("jumps")
    if not jp:
        return None
    test = (f"past {jp['threshold']:.1f} times the local scale, which a clean track on these frames passes "
            f"{100 * (1 - jp['alpha']):.0f} % of the time")
    flags = jp["flags"]
    if not flags:
        return f"none {test}"
    left = sorted((f for f in flags if f["kind"] != "step"), key=lambda f: -f["px"])
    steps = sorted((f for f in flags if f["kind"] == "step"), key=lambda f: -f["px"])
    more = lambda fs: f" and {len(fs) - most} more" if len(fs) > most else ""
    what = lambda f: (f"a glitch at frame {f['frame']}" if f["kind"] == "glitch" else
                      f"an excursion over frames {f['off'][0]}-{f['off'][-1]}") + f" ({f['px']:.1f} px)"
    parts = []
    if left:
        parts.append(", ".join(what(f) for f in left[:most]) + more(left)
                     + f": {sum(len(f['off']) for f in left)} point{'s' if sum(len(f['off']) for f in left) > 1 else ''} "
                     "left out of the band's fit as the track's slips")
    if steps:
        parts.append(f"{'a step' if len(steps) == 1 else f'{len(steps)} steps'} kept ("
                     + ", ".join(f"{f['px']:.1f} px at frame {f['frame']}" for f in steps[:most]) + more(steps)
                     + f"): off its path for good -- {JUMP_WHY}; the band's rate across a step is the step's")
    return f"{len(flags)} {test}: " + "; ".join(parts)


def simulate_track(n, fps, v=(100.0, 0.0), nugget=0.5, sill=5.0, range_s=1.0, accel=(0.0, 0.0), start=(500.0, 500.0),
                   frame0=1, rng=None):
    """A track drawn from a covariance (`kriging.simulate`): n frames at fps, a line at velocity v (px/s) plus a
    Matérn-3/2 wander of the given sill (px) and range (s) plus a nugget (px), and a planted acceleration (px/s²)
    on top. Returns (track {frame: (x, y)}, truth), the truth being the drawn velocity at every frame (frame,
    vx, vy) -- the line's, the acceleration's and the wander's own rate together -- and the average velocity over
    the stretch. The validation set the band is held to (K8): its coverage on tracks that have the fitted
    covariance, its false alarms on tracks that have none, and what it sees of an acceleration planted."""
    from . import kriging as kg
    rng = np.random.default_rng() if rng is None else rng
    t = np.arange(n) / float(fps)
    theta = (float(sill) ** 2, float(range_s), float(nugget) ** 2)
    track, vel = {}, []
    draws = [kg.simulate(t, theta, rng) if sill > 0 else
             (float(nugget) * rng.standard_normal(n), np.zeros(n), np.zeros(n)) for _ in (0, 1)]
    pos = []
    for k in (0, 1):
        y, f, df = draws[k]
        p = start[k] + v[k] * t + 0.5 * accel[k] * t ** 2 + y
        pos.append(p)
        vel.append(v[k] + accel[k] * t + df)
    for i in range(n):
        track[frame0 + i] = (float(pos[0][i]), float(pos[1][i]))
    f0 = [start[k] + draws[k][1][0] for k in (0, 1)]
    f1 = [start[k] + v[k] * t[-1] + 0.5 * accel[k] * t[-1] ** 2 + draws[k][1][-1] for k in (0, 1)]
    vbar = [(f1[k] - f0[k]) / t[-1] for k in (0, 1)]
    truth = dict(frame=(frame0 + np.arange(n)).tolist(), vx=vel[0].tolist(), vy=vel[1].tolist(), vbar=vbar)
    return track, truth


# ---- tau: the time to contact, from looming or the light curve (I6, 2026-10-28) ----------------------------
# A resolved object's angular size s grows as 1/(t_z - t) on a straight approach, so tau = s / s_dot = t_z - t (Lee 1976:
# the quantity animals brake on), with no range and no field of view; an unresolved one's flux goes as 1/R^2, so
# d ln F / dt = -2 Rdot / R once the gain is out. Either gives Rdot / R, the first thing a bearings-only track can
# observe (Nardone & Aidala 1981), and with omega the aspect angle: tan theta = omega R / |Rdot| = omega |tau|.
def looming_fit(t, size, boot=200, seed=0, offset=True):
    """tau from a resolved object's size along the track. Fits s(t) = a / (t_z - t) + c -- the projective test's own law,
    the same t_z, with c the blur's reach: an extent read off the picture is the object's own radius plus the width its
    edge is drawn over, which does not loom (`flicker.extent` reads a disc of radius r with a 1.2-px edge at r + 2.6;
    without it a disc closing at 2.0 s fitted 3.3), held at 0 <= c <= the least size; `offset=False` fits c = 0 -- and,
    for a short arc, the log-linear d ln s / dt beside it. t_z is found on a grid either side of the track, out to FAR
    track lengths, and refined between its neighbours. Returns None under 5 points or with no positive sizes; else
    dict(t_z, t_z_band (16-84 %, a residual bootstrap), tau_last (t_z - t_last: positive closing, negative receding),
    offset (c), dlns_dt, dlns_err, tau_mid (1 / dlns_dt at the arc's middle), tau_mid_err, rms, n)."""
    from scipy.optimize import minimize_scalar
    t, size = np.asarray(t, float), np.asarray(size, float)
    ok = np.isfinite(t) & np.isfinite(size) & (size > 0)
    t, size = t[ok], size[ok]
    if len(t) < 5:
        return None
    span = float(t[-1] - t[0]) or 1.0
    from .projective import FAR
    grid = np.r_[t[0] - span * np.logspace(math.log10(FAR), -2, 80), t[-1] + span * np.logspace(-2, math.log10(FAR), 80)]

    def at(tz, s):
        g = 1.0 / (tz - t)
        if offset:
            A = np.c_[g, np.ones_like(g)]
            (a, c), *_ = np.linalg.lstsq(A, s, rcond=None)
            c = min(max(float(c), 0.0), float(s.min()))
            a = float(g @ (s - c) / (g @ g))
        else:
            a, c = float(g @ s / (g @ g)), 0.0
        return a, c, float(np.sqrt(np.mean((s - a * g - c) ** 2)))

    def fit_at(s):
        rms = [at(tz, s)[2] for tz in grid]
        i = int(np.argmin(rms))
        lo, hi = grid[max(i - 1, 0)], grid[min(i + 1, len(grid) - 1)]
        if i in (79, 80) or lo < t[-1] < hi or lo < t[0] < hi:     # never across the track itself
            lo, hi = (lo, t[0] - 1e-6 * span) if grid[i] < t[0] else (t[-1] + 1e-6 * span, hi)
        tz = grid[i]
        if hi > lo:
            got = minimize_scalar(lambda z: at(z, s)[2], bounds=(lo, hi), method="bounded", options=dict(xatol=1e-4 * span))
            if got.fun <= rms[i]:
                tz = float(got.x)
        a, c, r = at(tz, s)
        return a, float(tz), r, c
    a, tz, rms, c = fit_at(size)
    rng = np.random.default_rng(seed)
    model = a / (tz - t) + c
    r = size - model
    draws = [fit_at(model + rng.choice(r, len(r), replace=True))[1] for _ in range(int(boot))] if boot else []
    band = [float(np.percentile(draws, 16)), float(np.percentile(draws, 84))] if draws else None
    b, cov = np.polyfit(t - t.mean(), np.log(size), 1, cov=True) if len(t) > 2 else ((0.0, 0.0), np.zeros((2, 2)))
    db = float(math.sqrt(max(cov[0, 0], 0.0)))
    return dict(n=int(len(t)), t_z=tz, t_z_band=band, tau_last=tz - float(t[-1]), rms=rms, offset=c,
                dlns_dt=float(b[0]), dlns_err=db,
                tau_mid=float(1.0 / b[0]) if b[0] else None, tau_mid_err=float(db / b[0] ** 2) if b[0] else None)


def tau_from_light_curve(t, flux, flux_bg=None):
    """tau from an unresolved object's brightness: d ln F / dt = -2 Rdot / R = 2 / tau on a straight approach (F ~ 1/R^2,
    the air's own extinction left out), the gain's share taken out where a background aperture's curve is given (its
    d ln F / dt subtracted: a gain change multiplies both). Returns None under 5 points; else dict(dlnF_dt, dlnF_err,
    tau (2 / dlnF_dt: positive closing), tau_err, n). A bird's brightness changes with its aspect and a flame's with
    its burning: this is for a steady source."""
    t, F = np.asarray(t, float), np.asarray(flux, float)
    ok = np.isfinite(t) & np.isfinite(F) & (F > 0)
    if flux_bg is not None:
        B = np.asarray(flux_bg, float)
        ok &= np.isfinite(B) & (B > 0)
    if ok.sum() < 5:
        return None
    tt = t[ok] - t[ok].mean()
    b, cov = np.polyfit(tt, np.log(F[ok]), 1, cov=True)
    db2 = float(max(cov[0, 0], 0.0))
    if flux_bg is not None:
        bb, cb = np.polyfit(tt, np.log(B[ok]), 1, cov=True)
        b = (b[0] - bb[0], b[1])
        db2 += float(max(cb[0, 0], 0.0))
    db = math.sqrt(db2)
    return dict(n=int(ok.sum()), dlnF_dt=float(b[0]), dlnF_err=db, tau=(2.0 / b[0]) if b[0] else None,
                tau_err=(2.0 * db / b[0] ** 2) if b[0] else None)


def aspect_from_tau(omega_rad_s, tau_s):
    """(5) with R out: tan theta = omega R / |Rdot| = omega |tau|. Degrees; None without either."""
    if omega_rad_s is None or tau_s is None:
        return None
    return float(math.degrees(math.atan(abs(float(omega_rad_s)) * abs(float(tau_s)))))


TAU_MIN_PX = 4.0         # px: the object's radius (flicker's `extent`) a size series needs -- a point reads 2-3 px, its blur's
TAU_MIN_POINTS = 10      # sizes (or brightnesses) a tau needs
TAU_Z = 4.0              # the trend in ln size (or ln brightness) must stand this many of its sigmas from none ...
TAU_GROW = 2.0           # ... the size must change by this many px over the stretch (it is read in whole pixels) ...
TAU_LIGHT = 0.1          # ... and the brightness, with the ring's level out, by this much in ln (10 %)
TAU_COVER = 0.6          # the share of the frames its size was tried on that must give one (a size that comes and goes is
                         # its neighbours' or the background's as often as its own: PURSUE PR097's dots, 24-50 of 126)
TAU_ODD = 3.0            # a size this many of the sizes' own MADs (and 1.5 px) off their running median is dropped as a slip
TAU_REL = 0.3            # tau's error must be at most this share of it: a tau the fit cannot place is not measured
TAU_CAP_PX = 80.0        # px: flicker's EXTENT_MAX. An extent read out to it found no edge -- the Yemen object, 22 px long
                         # inside its tracker's gate, read 80 on most frames (2026-10-29): the cap's, not a size


def _trend(t, y):
    """(slope, its sigma, the change it makes over the stretch) of a line through (t, y); the sigma widened for the
    residuals' own correlation from frame to frame (n_eff = n (1 - rho) / (1 + rho), rho their lag-1 correlation): a
    size or a brightness that wanders slowly is not as many independent readings as it has frames."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    tc = t - t.mean()
    b, a = np.polyfit(tc, y, 1)
    r = y - (a + b * tc)
    n = len(t)
    rho = float(np.corrcoef(r[:-1], r[1:])[0, 1]) if n > 3 and np.std(r[:-1]) > 0 and np.std(r[1:]) > 0 else 0.0
    rho = min(max(rho, 0.0), 0.95)
    n_eff = max(n * (1 - rho) / (1 + rho), 3.0)
    s2 = float(np.sum(r ** 2) / max(n - 2, 1))
    err = math.sqrt(s2 / max(float(np.sum(tc ** 2)), 1e-12)) * math.sqrt(n / n_eff)
    return float(b), float(err), float(b * (t[-1] - t[0]))


def tau_of(t, size=None, flux=None, level=None, beats=False):
    """tau -- R / |Rdot|, the time to contact, positive closing -- for one object from what the flicker stage reads on its
    frames: its size (`flicker.extent`, a radius in px; None where not read), its brightness over its ring and the ring's
    own level (`flicker.curves(each=)`), at times t (s). Two routes (method section 33):

    looming, the measurement: a resolved object (median radius at least TAU_MIN_PX) whose size changes along the track --
    its trend in ln size TAU_Z of its sigmas from none (the sigma widened for the sizes' own wander), TAU_GROW px or more
    over the stretch -- and which the looming law s = a / (t_z - t) + c describes as well as a free quadratic does
    (within projective's QUAD_SLACK) with t_z inside FAR track lengths: tau at the last frame, its error from the fit's
    bootstrap. A size that holds says no closing was seen in it, and nothing of how far: its blur's share of it is not
    known, so no bound on tau is drawn from it.

    the light curve, conditional, for an unresolved object only (a resolved one outgrows its aperture): d ln F / dt with
    the ring's level's taken out (`tau_from_light_curve`, at the track's middle), where the object does not beat and its
    brightness changes by TAU_LIGHT in ln or more at TAU_Z: tau = 2 / (d ln F / dt) IF the change is the range's alone --
    a steady source, the air's extinction and the picture's gamma left out (a video's levels compress a brightness change
    by about its gamma, 2.2, so tau from them is long by up to that). Recorded, said with its condition, never the route.

    The sizes are the frames' where one was read (a NaN in `size` is a frame tried with nothing read, None one not
    tried; a size at the extent's cap, TAU_CAP_PX, is one tried with nothing read): at least TAU_COVER of those tried
    must give one, and a size TAU_ODD of the sizes' MADs off their running median is dropped first (the far ring
    reaching a neighbour reads 30-80 px on a 5-px bird).

    Returns dict(route ("looming" or None), tau_s, tau_err_s, closing (True, False, or None), n, tried, dropped,
    median_px, looming, light, why)."""
    t = np.asarray(t, float)
    out = dict(route=None, tau_s=None, tau_err_s=None, closing=None, n=0, tried=0, dropped=0, median_px=None, looming=None,
               light=None, why=None)
    resolved = False
    if size is not None:
        sz = np.array([np.nan if v is None else float(v) for v in size])
        sz[sz >= TAU_CAP_PX] = np.nan                       # read to the cap with no edge: tried, nothing read
        tried = np.array([v is not None for v in size]) & np.isfinite(t)
        ok = tried & np.isfinite(sz) & (sz > 0)
        idx = np.flatnonzero(ok)
        if len(idx) >= 5:                                   # slips off the sizes' own running median
            from scipy.ndimage import median_filter
            med = median_filter(sz[idx], size=9, mode="mirror")     # "nearest" would make a first slip its own median
            dev = np.abs(sz[idx] - med)
            mad = 1.4826 * float(np.median(dev))
            odd = dev > max(TAU_ODD * mad, 1.5)
            ok[idx[odd]] = False
            out["dropped"] = int(odd.sum())
        out["n"], out["tried"] = int(ok.sum()), int(tried.sum())
        if ok.sum() >= TAU_MIN_POINTS:
            out["median_px"] = float(np.median(sz[ok]))
            resolved = out["median_px"] >= TAU_MIN_PX
        if ok.sum() < TAU_MIN_POINTS:
            out["why"] = f"its size was read on {int(ok.sum())} frames, under the {TAU_MIN_POINTS} tau needs"
        elif ok.sum() < TAU_COVER * tried.sum():
            out["why"] = (f"its size was read on {int(ok.sum())} of the {int(tried.sum())} frames it was tried on: one that comes and "
                          "goes is its neighbours' or the background's as often as its own")
        elif not resolved:
            out["why"] = (f"it is {2 * out['median_px']:.0f} px across, under {2 * TAU_MIN_PX:.0f}: its size is its blur's, "
                          "not its distance's")
        else:
            ts, ss = t[ok], sz[ok]
            b, e, _ = _trend(ts, np.log(ss))
            line = np.polyfit(ts, ss, 1)
            grew = float(np.polyval(line, ts[-1]) - np.polyval(line, ts[0]))
            z = abs(b) / e if e > 0 else float("inf")
            out["looming"] = dict(z=z, grew_px=grew, dlns_dt=b, dlns_err=e)
            if z < TAU_Z:
                out["why"] = (f"its size held, {out['median_px']:.1f} px in radius: no trend in it stands out of its own "
                              f"wander ({grew:+.1f} px over the stretch, {z:.1f} sigma), so no closing is seen in it")
            elif abs(grew) < TAU_GROW:
                out["why"] = (f"its size changed by {grew:+.1f} px over the stretch, under the {TAU_GROW:g} px a fit needs "
                              "(it is read in whole pixels)")
            else:
                from .projective import FAR, QUAD_SLACK
                lm = looming_fit(ts, ss)
                span = float(ts[-1] - ts[0]) or 1.0
                quad = float(np.sqrt(np.mean((ss - np.polyval(np.polyfit(ts, ss, 2), ts)) ** 2)))
                far = lm is None or not (-FAR * span * 0.95 < lm["t_z"] - ts[-1] < FAR * span * 0.95)
                if lm is not None:
                    out["looming"] = dict(lm, rms_quad=quad, z=z, grew_px=grew)
                band = (lm or {}).get("t_z_band")
                err = float((band[1] - band[0]) / 2) if band else None
                placed = err is not None and err <= TAU_REL * abs(lm["tau_last"])
                if lm is not None and not far and lm["rms"] <= QUAD_SLACK * max(quad, 0.5) and placed:
                    out.update(route="looming", tau_s=float(lm["tau_last"]), closing=bool(lm["tau_last"] > 0), tau_err_s=err)
                elif lm is not None and not far and lm["rms"] <= QUAD_SLACK * max(quad, 0.5):
                    out["why"] = (f"its size changes as a straight approach draws it, but the fit cannot place when: tau "
                                  f"{lm['tau_last']:.1f} s ± {err if err is not None else float('nan'):.1f}")
                else:
                    out["why"] = ("its size changes, but not as a straight approach draws it: the looming law "
                                  + ("puts the camera's plane too far off" if far else
                                     f"leaves {lm['rms']:.1f} px where a free curve leaves {quad:.1f}"))
    if flux is not None and level is not None and not beats and not resolved:
        F = np.array([np.nan if v is None else float(v) for v in flux])
        L = np.array([np.nan if v is None else float(v) for v in level])
        ok = np.isfinite(t) & np.isfinite(F) & (F > 0) & np.isfinite(L) & (L > 0)
        if ok.sum() >= TAU_MIN_POINTS:
            b, e, d = _trend(t[ok], np.log(F[ok]) - np.log(L[ok]))
            if b and abs(b) >= TAU_Z * e and abs(d) >= TAU_LIGHT:
                lc = tau_from_light_curve(t[ok], F[ok], L[ok])
                out["light"] = (dict(lc, tau=float(lc["tau"]), dlnF_err=e, tau_err=float(2.0 * e / b ** 2), z=float(abs(b) / e),
                                     change=d) if lc and lc.get("tau") else None)
    if out["route"] is None and out["why"] is None:
        out["why"] = "no size was read" if size is None else "no tau"
    return out


# ---- the admissible region in (R, Rdot) (A10, 2026-10-28) ----------------------------------------------------
# The astronomer's frame for a short angles-only track (Milani et al. 2004; Tommei, Milani & Rossi 2007): the track gives
# the angular rate and nothing of the range or its rate, and the physical constraints carve a region in the (R, Rdot)
# plane, which is then sampled. Here the constraints are the bounds the stages give on R (a horizon's or the haze's
# ceiling, the focus's floor, a range given), a speed cap, a size range through S = p R / k, and tau where it is
# measured (Rdot = -R / tau, a line). Sampling the region evenly gives the joint distribution of speed, aspect and
# size that the clip allows under those constraints -- the Technical Note's fan generalised, with its one-sidedness
# visible: the speed across the line of sight, omega R, is the least the speed can be at any R.
V_CAP = 3.0 * A_SOUND    # the default speed cap: nothing that breathes air flies faster


def admissible_region(omega_rad_s, k=None, p_px=None, R_min=None, R_max=None, v_cap=V_CAP, S_min=None, S_max=None,
                      tau_s=None, n=20000, seed=0, R_floor=1.0, rate_max=None):
    """The region of (R, Rdot) the clip allows, and what is drawn from it. R is bounded below by R_min (a stage's floor,
    else R_floor) and by S_min k / p, above by R_max, by S_max k / p and by the speed cap (omega R <= v_cap); at each R,
    |Rdot| <= sqrt(v_cap^2 - (omega R)^2), and with `rate_max` (|Rdot| / R at most that: the depth bound of a track
    that fits constant velocity with no closing seen, `projective.depth_bound`) |Rdot| <= rate_max R, a wedge; with tau,
    Rdot = -R / tau. Returns None where the region is empty (why in `empty`); else dict(R_lo, R_hi, v_cap, bounds
    (which limited it), rate_max, edge: [[R, rdot_max], ...] the region's rim, samples: {speed, theta_deg, size_m}:
    percentiles 5/50/95 of each drawn evenly over the region, speed_min (omega R_lo), speed_max, share_subsonic, n)."""
    om = abs(float(omega_rad_s))
    if om <= 0:
        return dict(empty="no angular rate")
    lo, hi, bounds = float(R_floor), v_cap / om, [("speed cap", "high")]
    if R_min is not None and R_min > lo:
        lo, bounds = float(R_min), bounds + [("range floor", "low")]
    if R_max is not None and R_max < hi:
        hi, bounds = float(R_max), [b for b in bounds if b[1] != "high"] + [("range ceiling", "high")]
    if k and p_px:
        if S_min is not None and S_min * k / p_px > lo:
            lo, bounds = S_min * k / p_px, bounds + [("smallest size", "low")]
        if S_max is not None and S_max * k / p_px < hi:
            hi, bounds = S_max * k / p_px, [b for b in bounds if b[1] != "high"] + [("largest size", "high")]
    if hi <= lo:
        return dict(empty=f"the bounds leave no range: at least {lo:.0f} m and at most {hi:.0f} m")
    rng = np.random.default_rng(seed)
    rim = lambda R: np.minimum(np.sqrt(np.maximum(v_cap ** 2 - (om * R) ** 2, 0.0)), rate_max * R if rate_max else np.inf)
    edge_R = np.geomspace(lo, hi, 120)
    edge = np.c_[edge_R, rim(edge_R)]
    if tau_s:
        R = rng.uniform(lo, hi, int(n))
        Rd = -R / float(tau_s)
        keep = np.abs(Rd) <= rim(R)
        R, Rd = R[keep], Rd[keep]
        if len(R) < 10:
            return dict(empty="tau puts the range rate beyond the speed cap at every allowed range")
    else:
        top = min(v_cap, rate_max * hi) if rate_max else v_cap      # the box the region is drawn evenly from, then cut to it
        R = rng.uniform(lo, hi, int(n) * 2)
        Rd = rng.uniform(-top, top, int(n) * 2)
        keep = np.abs(Rd) <= rim(R)
        R, Rd = R[keep][:int(n)], Rd[keep][:int(n)]
    speed = np.hypot(om * R, Rd)
    theta = np.degrees(np.arctan2(om * R, np.abs(Rd)))
    pc = lambda v: [float(np.percentile(v, q)) for q in (5, 50, 95)]
    # the extent, exactly: the least speed at the nearest range (along Rdot = 0, or on tau's line), the most the cap or
    # where the line or the wedge meets the farthest range
    slope = math.hypot(om, 1.0 / float(tau_s)) if tau_s else math.hypot(om, rate_max) if rate_max else None
    out = dict(R_lo=lo, R_hi=hi, v_cap=float(v_cap), omega=om, bounds=bounds, tau_s=tau_s, rate_max=rate_max, edge=edge.tolist(), n=int(len(R)),
               measure="uniform in R and Rdot", samples=dict(speed=pc(speed), theta_deg=pc(theta)),
               speed_min=lo * slope if tau_s else om * lo, speed_max=float(min(v_cap, hi * slope)) if slope else float(v_cap),
               share_subsonic=float(np.mean(speed < A_SOUND)))
    # the same region under the invariant measure (the pure-mathematics survey's M2, 2026-10-29): the range log-uniform
    # (Jeffreys' dR / R, which no choice of units changes) and the direction isotropic (cos theta uniform, which no
    # choice of axes changes), cut to the region -- beside the uniform draw, so the spread between the two is what a
    # "drawn evenly" number is worth (31 % under the speed of sound or 97 % on the same region)
    Ri = np.exp(rng.uniform(math.log(lo), math.log(hi), int(n) * 2))
    if tau_s:
        Rdi = -Ri / float(tau_s)
    else:
        cmax = rate_max / math.hypot(om, rate_max) if rate_max else 1.0       # |cot theta| <= rate_max / omega, exactly
        ci = rng.uniform(-cmax, cmax, len(Ri))
        Rdi = -om * Ri * ci / np.sqrt(np.maximum(1.0 - ci ** 2, 1e-12))
    ok = np.abs(Rdi) <= rim(Ri)
    Ri, Rdi = Ri[ok][:int(n)], Rdi[ok][:int(n)]
    if len(Ri) >= 10:
        si = np.hypot(om * Ri, Rdi)
        out["invariant"] = dict(measure="the range log-uniform, the direction isotropic", n=int(len(Ri)), speed=pc(si),
                                theta_deg=pc(np.degrees(np.arctan2(om * Ri, np.abs(Rdi)))), share_subsonic=float(np.mean(si < A_SOUND)))
    if k and p_px:
        size = p_px * R / k
        out["samples"]["size_m"] = pc(size)
        out.update(size_min=p_px * lo / k, size_max=p_px * hi / k)
        if out.get("invariant"):
            out["invariant"]["size_m"] = pc(p_px * Ri / k)
    return out


BOUND_WORDS = {"speed cap": "where the speed cap meets ωR", "range floor": "the floor a stage measured",
               "range ceiling": "the ceiling a stage measured", "smallest size": "the smallest size allowed",
               "largest size": "the largest size allowed"}


def admissible_said(reg):
    """The region in a sentence: what the clip allows, under what. None where nothing but the floor of one metre and
    the speed cap bounds it (then the figure says what there is to say: the fan)."""
    if not reg or reg.get("empty"):
        return None
    lows = [BOUND_WORDS[w] for w, side in reg["bounds"] if side == "low"]
    highs = [BOUND_WORDS[w] for w, side in reg["bounds"] if side == "high"]
    if not lows and not reg.get("tau_s") and not reg.get("rate_max") and highs == [BOUND_WORDS["speed cap"]]:
        return None
    sp, th = reg["samples"]["speed"], reg["samples"]["theta_deg"]
    out = (f"with the range at least {reg['R_lo']:,.0f} m ({', '.join(lows) if lows else 'nothing bounds it below'}) and at most "
           f"{reg['R_hi']:,.0f} m ({', '.join(highs)}), under a speed cap of {reg['v_cap']:.0f} m/s, the speed relative to the platform "
           f"is at least {reg['speed_min']:.0f} m/s and at most {reg['speed_max']:.0f}"
           + (f", the size {reg['size_min']:.3g} to {reg['size_max']:.3g} m" if reg.get("size_min") is not None else "")
           + ": that much is the clip's. How the speed spreads between them is a choice of how to draw: evenly in R and Ṙ, "
           f"{sp[0]:.0f}-{sp[2]:.0f} m/s (5-95 %, median {sp[1]:.0f}), {reg['share_subsonic']:.0%} under the speed of sound, the "
           f"aspect angle {th[0]:.0f}-{th[2]:.0f}°")
    iv = reg.get("invariant")
    if iv:
        out += (f"; with the range log-uniform and the direction isotropic (a draw no choice of units or of axes changes), "
                f"{iv['speed'][0]:.0f}-{iv['speed'][2]:.0f} m/s (median {iv['speed'][1]:.0f}), {iv['share_subsonic']:.0%} under it")
    if reg.get("tau_s"):
        out += f"; tau = {reg['tau_s']:.2f} s puts the range rate at -R / tau, one line of the region"
    elif reg.get("rate_max"):
        from .projective import pct
        out += (f"; no closing seen puts the range rate within {pct(reg['rate_max'])} of the range a second, a wedge of the "
                "region (if it flew straight at a steady speed)")
    return out



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
                 fit=None, band=None):
        self.tag = tag
        self.fit = fit
        self.band = band                 # `speed_band`'s, where the track gave one
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
            ratio = self.ref.get("range_ratio")
            v = scale_bar_speed(self.v_px, self.ref["px"], self.ref["len_m"], ratio or 1.0)
            L.append(f"  scale bar {v:.1f} m/s ({v * 1.94384:.0f} kn) at "
                     + (f"{ratio:g} times the reference's range " if ratio else "the reference's range ")
                     + f"[{self.ref.get('what', 'reference')}, {self.ref['len_m']:g} m over {self.ref['px']:g} px; "
                     + ("FOV cancels; R_obj/R_ref given]" if ratio else "FOV cancels, range ratio does not]"))

        if self.band:
            first, second = band_said(self.band, self.fps)
            L.append(f"  band      {first}")
            L.append(f"            {second}")
        if self.fit and not self.fit.get("uniform", True):
            b = self.band
            L.append(f"  !! NOT UNIFORM: the fit residual is {self.fit['resid_rms']:.0f} px, "
                     + (f"{self.fit['resid_frac']:.0%} of the {self.fit['span_px']:.0f} px covered. "
                        if self.fit.get("resid_frac") is not None else "and it ends where it began. ")
                     + "The motion is not a straight line at constant rate, so this v_px does not describe it"
                     + (f": the speed ran from {b['v_min'][1]:.0f} to {b['v_max'][1]:.0f} px/s (the band above), and the "
                        f"numbers below are for its average over the stretch, {pm(b['v_mean_px_per_s'], b['v_mean_err_px_per_s'])} "
                        "px/s, which the speed itself ran either side of."
                        if b and not b["constant"] else " and nothing below should be quoted."))
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
