"""Does the object look the same from every side? Its brightness, size and shape against its heading.

A sphere, a "ball of light" or an "orb" looks the same whichever way it is going. A body with
wings, or any body longer than it is wide, does not: as it turns it shows the sensor a different
outline, and as it banks into a turn it tilts its planform towards the sensor or away. Its
brightness and size then follow its heading. The test needs no range, no field of view and no
beat, so it is asked of clips where nothing else can be (PURSUE's Gulf of Oman phone captures,
PR121: two contacts looping about the boresight for 11-13 s), and it sees a glider, which the
beat test (`flicker`) cannot.

**What a level glider does, and what a banking one does.** A flat planform held level shows the
same area from every heading at a given depression (the area is that of the plate, times the
sine of the angle it is seen at), so a gliding bird flying level in a straight line is invisible
to a heading test. A flyer that turns on its wings must bank, by phi = atan(V omega / g) for speed
V and turn rate omega, and the bank tilts the planform towards the sensor on one side of the
loop and away on the other: a first-harmonic swing in the brightness of about cot(eps) tan(phi)
at depression eps. With `--depression`, the stage turns its bound on that harmonic into the
largest bank, and so the largest speed, that a winged flyer could have had through the track's
own turn rate (`bank_bound`). Below one full turn the headings are not all seen and it says so.

**How.**
1. Every frame from the track's first mark to its last is measured, marked or not, and no
   frame that repeats the one before (`repeats`): an object that fades at some headings must
   not drop out of the test at exactly those frames.
2. The position, velocity, heading theta (clockwise from up), speed and signed turn rate omega
   of every frame come from a local quadratic in time through the track (+-SMOOTH s).
3. Each frame's flux is the aperture's sum over the annulus' median; with `--still` (a display
   held by `mcdonald stabilize`, or a sensor that stares), the background is first the median
   of the frames within +-HALF with the object masked out, which takes out a fixed pattern
   the object crosses. Size, elongation and the long axis' angle from an elliptical Gaussian.
4. The flux's fractional deviation is modelled as a cubic in time, a quadratic in place and the
   speed, with and without cos/sin theta and cos/sin 2theta. The heading terms' F, and each
   harmonic's amplitude, are judged against TIME SLIDES: the heading and turn-rate series slid
   circularly against the flux by at least MIN_SLIDE s, N_SLIDE times -- the null that keeps
   every series' own autocorrelation. The same for the size. The elongation's alignment with
   the motion, (e - 1) cos 2(alpha - theta), regressed on speed, separates a shape (its value
   at zero speed: + along the motion, - across it, a wingspan seen from above) from smear.
5. Controls, run through every step: a round blob of the object's own fitted size and depth
   planted along the same path moved to empty picture (`offset`); and the same blob with its
   flux modulated by PLANT_M at 2 theta and at theta. The first is the false alarm, the others
   the completeness; where the modulated plant is not found, the stage has no power.

**No power.** Under one full turn (the headings not all seen); a path on which the heading goes with
the place (a clean circle, where the velocity is square to the radius: `entanglement` over
MAX_TANGLE), so that a place effect cannot be told from a heading effect; a time-slide null that
admits a heading effect over NULL_MAX of the flux; the planted modulation not recovered; too few
frames measured. The entanglement is reported either way: a wandering loop has R^2 near 0.96 and
is still told apart, because a few hundred frames carry the rest.
"""
import csv
import math
from pathlib import Path

import numpy as np
from scipy import ndimage, optimize

HALF, SKIP = 45, 3          # --still background: frames either side, and the nearest left out
MASK_R = 2.5                # the object masked out of the --still background to this many apertures
SMOOTH = 0.17               # s: half-width of the local quadratic for position and velocity
MIN_SLIDE = 1.5             # s: the least time slide in the null
N_SLIDE = 1000
PLANT_M = 0.15              # the planted modulation, a share of the flux
FIT_HALF = 13               # px: half-size of the Gaussian fit's cutout
MIN_TURN = 360.0            # deg: under this the headings are not all seen
MIN_FRAMES = 40
MAX_TANGLE = 0.995          # the heading terms' R^2 on the place-and-time model, at most (`entanglement`): a wandering
                           # loop sits at 0.96 and is still told apart (tests/test_aspect.py); a clean circle is 1
NULL_MAX = 0.30             # a test whose time-slide null admits a heading effect this large (95th percentile) has no power
G = 9.81


# ---- reading ---------------------------------------------------------------------------------
def repeats(clip, frames, box):
    """Frames whose box repeats the frame before (a variable-rate camera padded to a constant
    rate): a mean change under 0.15 of the clip's median change in the box."""
    x0, y0, x1, y1 = box
    prev, d = None, {}
    for n in frames:
        g = clip.grey(n)[y0:y1, x0:x1]
        if prev is not None:
            d[n] = float(np.abs(g - prev).mean())
        prev = g
    if not d:
        return set()
    med = float(np.median(list(d.values())))
    return {n for n, v in d.items() if v < 0.15 * med}


def local_quad(t, x, tq, half=SMOOTH):
    """Position and velocity at times tq from samples (t, x): a local quadratic, tricube weights."""
    pos, vel = np.full(len(tq), np.nan), np.full(len(tq), np.nan)
    for i, t0 in enumerate(tq):
        d = t - t0
        m = np.abs(d) < half
        if m.sum() < 4:
            m = np.isin(np.arange(len(t)), np.argsort(np.abs(d))[:5])
        hw = max(half, np.abs(d[m]).max() * 1.01)
        w = np.sqrt((1 - (np.abs(d[m]) / hw) ** 3) ** 3)
        c, *_ = np.linalg.lstsq(np.c_[np.ones(m.sum()), d[m], d[m] ** 2] * w[:, None], x[m] * w, rcond=None)
        pos[i], vel[i] = c[0], c[1]
    return pos, vel


def gauss_fit(cut):
    """Elliptical Gaussian on a cutout of the (positive) signal: amp, x, y, s1 >= s2, angle of s1."""
    h, w = cut.shape
    yy, xx = np.mgrid[:h, :w].astype(float)

    def model(p):
        a, x0, y0, s1, s2, ang, off = p
        c, s = np.cos(ang), np.sin(ang)
        u = (xx - x0) * c + (yy - y0) * s
        v = -(xx - x0) * s + (yy - y0) * c
        return off + a * np.exp(-0.5 * ((u / s1) ** 2 + (v / s2) ** 2))

    p0 = [max(cut.max() - np.median(cut), 1.0), w / 2, h / 2, 3.0, 3.0, 0.0, float(np.median(cut))]
    try:
        r = optimize.least_squares(lambda p: (model(p) - cut).ravel(), p0,
                                   bounds=([0, w / 2 - 6, h / 2 - 6, 0.8, 0.8, -np.pi, -np.inf],
                                           [np.inf, w / 2 + 6, h / 2 + 6, 12, 12, np.pi, np.inf]))
    except (ValueError, np.linalg.LinAlgError):
        return None
    a, x0, y0, s1, s2, ang, _ = r.x
    if s2 > s1:
        s1, s2, ang = s2, s1, ang + np.pi / 2
    return dict(amp=float(a), s1=float(s1), s2=float(s2), ang=float((ang + np.pi / 2) % np.pi - np.pi / 2))


# ---- photometry --------------------------------------------------------------------------------
def photometry(stack, order, pos, r_ap, still, plant=None):
    """Flux and shape on every frame of `order` at `pos` {n: (x, y)} (stack px). stack is the
    object-positive picture (a dark object already turned over). plant {n: (x, y, depth, sigma)}
    adds a Gaussian before anything is measured."""
    idx = {n: i for i, n in enumerate(order)}
    S = stack.copy()
    h, w = S.shape[1:]
    yy, xx = np.mgrid[:h, :w]
    if plant:
        for n, (px, py, depth, sig) in plant.items():
            S[idx[n]] += depth * np.exp(-0.5 * ((xx - px) ** 2 + (yy - py) ** 2) / sig ** 2)
    r_in, r_out = 1.35 * r_ap, 2.0 * r_ap
    masked = None
    if still:
        masked = S.copy()
        for n, (x, y) in pos.items():
            masked[idx[n]][(xx - x) ** 2 + (yy - y) ** 2 < (MASK_R * r_ap) ** 2] = np.nan
    out = {}
    for n, (x, y) in pos.items():
        i = idx[n]
        reach = max(r_out, FIT_HALF + 1)                  # room for the annulus and for the shape's cutout
        x0, x1 = int(max(0, x - reach - 2)), int(min(w, x + reach + 3))
        y0, y1 = int(max(0, y - reach - 2)), int(min(h, y + reach + 3))
        if still:
            nb = [j for j in range(max(0, i - HALF), min(len(order), i + HALF + 1)) if abs(j - i) > SKIP]
            bg = np.nanmedian(masked[nb, y0:y1, x0:x1], 0)
            s = S[i, y0:y1, x0:x1] - bg
        else:
            bg = None
            s = S[i, y0:y1, x0:x1].copy()
        sy, sx = np.mgrid[y0:y1, x0:x1]
        r = np.hypot(sx - x, sy - y)
        ann = np.nanmedian(s[(r >= r_in) & (r < r_out)])
        flux = float(np.nansum(s[r < r_ap] - ann))
        level = float(np.nanmedian((bg if bg is not None else S[i, y0:y1, x0:x1])[(r >= r_in) & (r < r_out)]))
        cx, cy = int(round(x)), int(round(y))
        cut = s[cy - FIT_HALF - y0:cy + FIT_HALF + 1 - y0, cx - FIT_HALF - x0:cx + FIT_HALF + 1 - x0] - ann
        g = gauss_fit(np.nan_to_num(cut)) if cut.shape == (2 * FIT_HALF + 1, 2 * FIT_HALF + 1) else None
        out[n] = dict(flux=flux, level=level, **(g or {}))
    return out


# ---- the model and its null --------------------------------------------------------------------
def design(t, x, y, speed, theta, omega, heading=True, bank=False, extra=None):
    tt = (t - t.mean()) / (np.ptp(t) / 2 or 1)
    xs, ys = (x - x.mean()) / 100.0, (y - y.mean()) / 100.0
    cols = [np.ones_like(t), tt, tt ** 2, tt ** 3, xs, ys, xs * xs, ys * ys, xs * ys, speed / 100.0]
    if extra is not None:
        cols += [(extra - extra.mean()) / (extra.std() or 1)]
    if heading:
        cols += [np.cos(theta), np.sin(theta), np.cos(2 * theta), np.sin(2 * theta)]
    if bank:
        cols += [omega / 5.0]
    return np.c_[tuple(cols)]


def fit_stats(z, t, x, y, speed, theta, omega, extra=None):
    """The heading terms' F (and the turn rate's) over the base model, and each harmonic's amplitude."""
    rss = lambda X: float(((z - X @ np.linalg.lstsq(X, z, rcond=None)[0]) ** 2).sum())
    X0 = design(t, x, y, speed, theta, omega, False, False, extra)
    X1 = design(t, x, y, speed, theta, omega, True, False, extra)
    X2 = design(t, x, y, speed, theta, omega, False, True, extra)
    r0, r1, r2 = rss(X0), rss(X1), rss(X2)
    n = len(z)
    c = np.linalg.lstsq(X1, z, rcond=None)[0]
    return dict(F_heading=((r0 - r1) / 4) / (r1 / max(1, n - X1.shape[1])),
                F_turn=((r0 - r2) / 1) / (r2 / max(1, n - X2.shape[1])),
                amp1=float(np.hypot(c[-4], c[-3])), amp2=float(np.hypot(c[-2], c[-1])),
                phase1_deg=float(np.degrees(np.arctan2(c[-3], c[-4])) % 360),
                phase2_deg=float((np.degrees(np.arctan2(c[-1], c[-2])) / 2) % 180))


def with_null(z, t, x, y, speed, theta, omega, rng, extra=None, n_slide=N_SLIDE):
    """fit_stats with its time-slide p values and the null's 95th percentiles."""
    obs = fit_stats(z, t, x, y, speed, theta, omega, extra)
    dt = float(np.median(np.diff(t)))
    k_min = int(math.ceil(MIN_SLIDE / dt))
    N = len(z)
    if N - 2 * k_min < 5:
        obs.update(p_heading=None, p_amp1=None, p_amp2=None, p_turn=None)
        return obs
    null = [fit_stats(z, t, x, y, np.roll(speed, k), np.roll(theta, k), np.roll(omega, k), extra)
            for k in rng.integers(k_min, N - k_min, n_slide)]
    p = lambda key: float((1 + sum(d[key] >= obs[key] for d in null)) / (1 + len(null)))
    obs.update(p_heading=p("F_heading"), p_amp1=p("amp1"), p_amp2=p("amp2"), p_turn=p("F_turn"),
               null95_amp1=float(np.percentile([d["amp1"] for d in null], 95)),
               null95_amp2=float(np.percentile([d["amp2"] for d in null], 95)))
    return obs


def entanglement(t, x, y, speed, theta, omega):
    """How far the heading terms are already in the place-and-time model: the largest R^2 of a heading
    column regressed on the base columns. On a clean circle the heading is a function of place
    (the velocity is square to the radius) and R^2 is 1: a place effect cannot be told from a
    heading effect, and the stage has no power. A wandering loop keeps them apart."""
    X0 = design(t, x, y, speed, theta, omega, False, False)
    worst = 0.0
    for col in (np.cos(theta), np.sin(theta), np.cos(2 * theta), np.sin(2 * theta)):
        c, *_ = np.linalg.lstsq(X0, col, rcond=None)
        r = col - X0 @ c
        worst = max(worst, 1 - float(r @ r) / float(((col - col.mean()) ** 2).sum() or 1))
    return worst


def bank_bound(amp1_95, depression_deg, omega_median):
    """The largest bank, and the speed it allows through the track's turn rate, that a flat planform
    could have had and stayed under `amp1_95` at the first harmonic: cot(eps) tan(phi) <= amp1_95."""
    eps = math.radians(depression_deg)
    tan_phi = amp1_95 * math.tan(eps)
    phi = math.degrees(math.atan(tan_phi))
    v = G * tan_phi / max(abs(omega_median), 1e-6)
    return dict(depression_deg=depression_deg, bank_max_deg=round(phi, 1), speed_max_m_s=round(v, 2),
                loop_radius_max_m=round(v / max(abs(omega_median), 1e-6), 2))


# ---- the stage ---------------------------------------------------------------------------------
def offset_for(pos, W, H, margin):
    """Where the planted controls go: the track's own path moved by the smallest whole offset that
    keeps it in the picture and clear of the track."""
    xy = np.array(list(pos.values()))
    span = xy.max(0) - xy.min(0)
    for k in (1.3, 1.6, 2.0, 2.5):
        for dx, dy in ((k * span[0] + 3 * margin, 0), (-(k * span[0] + 3 * margin), 0), (0, k * span[1] + 3 * margin),
                       (0, -(k * span[1] + 3 * margin))):
            q = xy + [dx, dy]
            if q[:, 0].min() > margin and q[:, 0].max() < W - margin and q[:, 1].min() > margin and q[:, 1].max() < H - margin:
                return float(dx), float(dy)
    return None


def measure(clip, track, dark=False, still=False, aperture=None, offset=None, depression=None, out=None, seed=1,
            progress=None):
    """The stage. track {frame: (x, y)}: the object's marks or a linked track (gaps allowed)."""
    from .report import Found
    say = progress or (lambda *a, **k: None)
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    n0, n1 = ns[0], ns[-1]
    det = np.array([[n, *track[n]] for n in ns], float)
    xy = det[:, 1:]
    margin = int(aperture * 2.2 + FIT_HALF) if aperture else 40
    if offset is None:
        offset = offset_for({n: track[n] for n in ns}, clip.W, clip.H, margin) or (0.0, 0.0)
    ox, oy = offset
    bx0 = int(max(0, min(xy[:, 0].min(), xy[:, 0].min() + ox) - margin - 8))
    by0 = int(max(0, min(xy[:, 1].min(), xy[:, 1].min() + oy) - margin - 8))
    bx1 = int(min(clip.W, max(xy[:, 0].max(), xy[:, 0].max() + ox) + margin + 8))
    by1 = int(min(clip.H, max(xy[:, 1].max(), xy[:, 1].max() + oy) + margin + 8))
    lo, hi = (max(clip.n0, n0 - 3 * HALF), min(clip.n1, n1 + 3 * HALF)) if still else (n0, n1)
    frames = list(range(lo, hi + 1))
    reps = repeats(clip, frames, (bx0, by0, bx1, by1))
    order = [n for n in frames if n not in reps]
    span = [n for n in order if n0 <= n <= n1]
    stack = np.stack([clip.grey(n)[by0:by1, bx0:bx1] for n in order]).astype(np.float32)
    if dark:
        stack = -stack
    t_det = (det[:, 0] - 1) / clip.fps
    t = (np.array(span) - 1) / clip.fps
    xs, vx = local_quad(t_det, det[:, 1], t)
    ys, vy = local_quad(t_det, det[:, 2], t)
    speed = np.hypot(vx, vy)
    theta = np.arctan2(vx, -vy)
    th_u = np.unwrap(theta)
    omega = np.gradient(th_u, t)
    turned = float(np.degrees(th_u[-1] - th_u[0]))
    pos = {n: (xs[i] - bx0, ys[i] - by0) for i, n in enumerate(span)}
    if aperture is None:                                   # from the object's own fitted size on a few frames
        probe = photometry(stack, order, {n: pos[n] for n in span[:: max(1, len(span) // 25)]}, 8.0, still)
        sig = np.nanmedian([math.sqrt(m["s1"] * m["s2"]) for m in probe.values() if "s1" in m])
        aperture = float(np.clip(2.0 * sig, 4.0, 20.0))
    say(f"aspect: frames {n0}-{n1}, {len(span)} new ({len(ns)} marked), turned {turned:+.0f} deg, aperture {aperture:.1f} px")
    meas = photometry(stack, order, pos, aperture, still)
    flux = np.array([meas[n]["flux"] for n in span])
    good = np.isfinite(flux) & np.array(["s1" in meas[n] for n in span])
    if good.sum() < 8:
        raise ValueError(f"aspect: only {int(good.sum())} of {len(span)} frames could be measured at the track")
    z = flux / np.nanmean(flux[good]) - 1
    args = (t[good], xs[good], ys[good], speed[good], theta[good], omega[good])
    tangled = entanglement(*args)
    rng = np.random.default_rng(seed)
    bright = with_null(z[good], *args, rng)
    level = np.array([meas[n]["level"] for n in span])
    bright_lv = with_null(z[good], *args, np.random.default_rng(seed + 3), extra=level[good])
    s1 = np.array([meas[n].get("s1", np.nan) for n in span])
    s2 = np.array([meas[n].get("s2", np.nan) for n in span])
    ang = np.array([meas[n].get("ang", np.nan) for n in span])
    size = np.sqrt(s1 * s2)
    okz = good & np.isfinite(size) & (s1 < 11.5)
    zs = size / np.nanmean(size[okz]) - 1
    sz = with_null(zs[okz], t[okz], xs[okz], ys[okz], speed[okz], theta[okz], omega[okz], np.random.default_rng(seed + 1))
    align = (s1 / s2 - 1) * np.cos(2 * (np.pi / 2 + ang - theta))
    ca, *_ = np.linalg.lstsq(np.c_[np.ones(okz.sum()), speed[okz] / 100.0], align[okz], rcond=None)
    depth = float(np.nanmedian([meas[n].get("amp", np.nan) for n in span]))
    sigma = float(np.nanmedian(size[okz]))
    ctrl = {}
    ppos = {n: (pos[n][0] + ox, pos[n][1] + oy) for n in span}
    for name, mod in (("round", lambda th: 1.0), ("2theta", lambda th: 1 + PLANT_M * np.cos(2 * (th - math.radians(30)))),
                      ("theta", lambda th: 1 + PLANT_M * np.cos(th - math.radians(60)))):
        plant = {n: (ppos[n][0], ppos[n][1], depth * mod(theta[i]), sigma) for i, n in enumerate(span)}
        m = photometry(stack, order, ppos, aperture, still, plant=plant)
        f = np.array([m[n]["flux"] for n in span])
        g = np.isfinite(f)
        ctrl[name] = with_null(f[g] / np.nanmean(f[g]) - 1, t[g], xs[g], ys[g], speed[g], theta[g], omega[g],
                               np.random.default_rng(seed + 7))
    fields = dict(frames=[n0, n1], new_frames=len(span), marked=len(ns), measured=int(good.sum()), repeats=len(reps),
                  turned_deg=round(turned, 1), turns=round(abs(turned) / 360.0, 2), heading_place_r2=round(tangled, 3),
                  clockwise_share=round(float((omega > 0).mean()), 2),
                  median_speed_px_s=round(float(np.median(speed)), 1),
                  median_turn_rate_deg_s=round(float(np.degrees(np.median(np.abs(omega)))), 1),
                  aperture_px=round(aperture, 1), still=bool(still), offset=[round(ox, 1), round(oy, 1)],
                  flux_noise_per_frame=round(float(np.std(np.diff(z[good])) / math.sqrt(2)), 3),
                  brightness=bright, brightness_with_level=bright_lv, size=sz,
                  elongation=dict(median=round(float(np.nanmedian(s1[okz] / s2[okz])), 3),
                                  align_mean=round(float(np.nanmean(align[okz])), 3),
                                  align_at_zero_speed=round(float(ca[0]), 3), align_per_100px_s=round(float(ca[1]), 3)),
                  controls=dict(depth=depth, sigma=sigma, **ctrl))
    if depression is not None and bright.get("null95_amp1") is not None:
        fields["bank_bound"] = bank_bound(max(bright["amp1"], bright["null95_amp1"]), depression, float(np.median(np.abs(omega))))
    no_power, needs = [], []
    if abs(turned) < MIN_TURN:
        no_power.append(("aspect", f"the track turns through {abs(turned):.0f} deg, under a full turn: its headings are not all seen"))
        needs.append("a longer track, or one that turns")
    if tangled > MAX_TANGLE:
        no_power.append(("aspect", f"on this path the heading goes with the place (R^2 {tangled:.2f}): a place effect cannot be "
                                   "told from a heading effect"))
        needs.append("a path that comes back over the same place at other headings")
    if max(bright.get("null95_amp1") or 0, bright.get("null95_amp2") or 0) > NULL_MAX:
        no_power.append(("aspect", f"the time slides admit a heading effect of {100 * max(bright['null95_amp1'], bright['null95_amp2']):.0f} % "
                                   "of the flux: too noisy, or the heading too tied to the place, to hear one"))
    if good.sum() < MIN_FRAMES:
        no_power.append(("aspect", f"only {int(good.sum())} frames measured"))
    for name in ("2theta", "theta"):
        p = ctrl[name].get("p_heading")
        if p is None or p > 0.05:
            no_power.append(("aspect", f"a {100 * PLANT_M:.0f} % modulation at {name} planted along the path is not recovered"))
    files = []
    if out:
        files = write(out, span, t, xs, ys, speed, theta, omega, flux, z, good, s1, s2, ang)
        try:
            files.append(figure(f"{out}_aspect.png", Path(out).name, t, xs, ys, theta, z, good, zs, okz, fields))
        except Exception as ex:                                   # a figure is never worth the measurement
            say(f"(no figure: {ex})")
    found = Found("aspect", result={"aspect": said(fields)[0]}, fields=fields, no_power=no_power, needs=needs, files=files)
    return found


def write(out, span, t, xs, ys, speed, theta, omega, flux, z, good, s1, s2, ang):
    p = Path(f"{out}_aspect.csv")
    with open(p, "w", newline="", encoding="utf-8") as fh:
        fh.write("# mcdonald aspect: every new frame from the track's first mark to its last; heading clockwise from up\n")
        w = csv.writer(fh)
        w.writerow(["frame", "t_s", "x", "y", "speed_px_s", "heading_deg", "turn_deg_s", "flux", "flux_rel", "s1", "s2",
                    "long_axis_deg", "measured"])
        for i, n in enumerate(span):
            w.writerow([n, f"{t[i]:.4f}", f"{xs[i]:.2f}", f"{ys[i]:.2f}", f"{speed[i]:.1f}", f"{math.degrees(theta[i]) % 360:.1f}",
                        f"{math.degrees(omega[i]):.1f}", f"{flux[i]:.2f}", f"{z[i]:.4f}", f"{s1[i]:.3f}", f"{s2[i]:.3f}",
                        f"{(math.degrees(ang[i]) + 90) % 180:.1f}", int(good[i])])
    return [p]


def figure(path, name, t, x, y, theta, z, sel, zs, okz, f):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)
    a = ax[0]
    sc = a.scatter(x[sel], y[sel], c=z[sel], cmap="coolwarm", s=12, vmin=-0.5, vmax=0.5)
    a.plot(x, y, "-", color="0.7", lw=0.5, zorder=0)
    a.invert_yaxis()
    a.set_aspect("equal")
    a.set_xlabel("x (px)", fontweight="bold")
    a.set_ylabel("y (px)", fontweight="bold")
    a.set_title(f"{name}: Path, Coloured by Brightness", fontweight="bold")
    fig.colorbar(sc, ax=a, fraction=0.046, pad=0.02).set_label("Brightness", fontweight="bold")
    b = f["brightness"]
    hh = np.linspace(0, 360, 361)
    for a, v, m, key, lab in ((ax[1], z, sel, "brightness", "Brightness Deviation"), (ax[2], zs, okz, "size", "Size Deviation")):
        s = f[key]
        a.scatter(np.degrees(theta[m]) % 360, v[m], s=8, color="0.3")
        a.plot(hh, s["amp1"] * np.cos(np.radians(hh - s["phase1_deg"])) + s["amp2"] * np.cos(2 * np.radians(hh - s["phase2_deg"])),
               color="C3", lw=2)
        a.set_xlim(0, 360)
        a.set_xlabel("Heading (deg, Clockwise from Up)", fontweight="bold")
        a.set_ylabel(lab, fontweight="bold")
        p = s.get("p_heading")
        a.set_title(f"{100 * s['amp1']:.1f} % (1st), {100 * s['amp2']:.1f} % (2nd); p = {p if p is None else round(p, 2)}",
                    fontweight="bold", fontsize=10)
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return Path(path)


def said(f):
    b = f["brightness"]
    pct = lambda v: f"{100 * v:.1f} %"
    L = [f"Through {f['turns']:.1f} turns ({f['turned_deg']:+.0f} deg, {100 * f['clockwise_share']:.0f} % of the time clockwise) "
         f"over {f['new_frames']} new frames, the brightness follows the heading by {pct(b['amp1'])} (1st harmonic) and "
         f"{pct(b['amp2'])} (2nd), p = {b.get('p_heading')}; time slides put the 95th percentiles at "
         f"{pct(b.get('null95_amp1', float('nan')))} and {pct(b.get('null95_amp2', float('nan')))}."]
    s, e, c = f["size"], f["elongation"], f["controls"]
    L.append(f"The size follows it by {pct(s['amp1'])} and {pct(s['amp2'])} (p = {s.get('p_heading')}); the long axis lies "
             f"{'along' if e['align_at_zero_speed'] > 0 else 'across'} the motion by {e['align_at_zero_speed']:+.3f} at zero speed "
             f"(smear adds {e['align_per_100px_s']:+.3f} per 100 px/s).")
    L.append(f"Planted along the same path {f['offset']} px away: a round blob shows {pct(c['round']['amp1'])} / "
             f"{pct(c['round']['amp2'])} (p = {c['round'].get('p_heading')}); {100 * PLANT_M:.0f} % at 2theta is read as "
             f"{pct(c['2theta']['amp2'])} (p = {c['2theta'].get('p_heading')}) and at theta as {pct(c['theta']['amp1'])} "
             f"(p = {c['theta'].get('p_heading')}).")
    if "bank_bound" in f:
        bb = f["bank_bound"]
        L.append(f"At a {bb['depression_deg']:g} deg depression a flat planform banking through this track's turns would swing its "
                 f"brightness by cot(eps) tan(bank) at the 1st harmonic: under the bound, the bank is under {bb['bank_max_deg']} deg, "
                 f"so a winged flyer turning on its wings here moved under {bb['speed_max_m_s']} m/s (a loop radius under "
                 f"{bb['loop_radius_max_m']} m). A level glider, or a body that looks the same from every side, is not bounded.")
    return L


def main():
    import argparse
    from . import forensics as vf
    from . import clip as vclip
    from .report import emit, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", required=True, help="CSV with frame and x/y columns: the object's marks or linked track")
    ap.add_argument("--dark", action="store_true", help="the object is darker than what is round it")
    ap.add_argument("--still", action="store_true",
                    help="the background stands still (a display held by `mcdonald stabilize`, a staring sensor): take "
                         "out what is fixed under the object with a running median, the object masked")
    ap.add_argument("--aperture", type=float, help="aperture radius, px (default: twice the object's fitted size)")
    ap.add_argument("--offset", metavar="DX,DY", help="where the planted controls go (default: the nearest clear place)")
    ap.add_argument("--depression", type=float, metavar="DEG",
                    help="the sensor's depression angle, if known: turns the bound into the largest bank and speed")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>; with --n0/--n1, the segment's own folder in it, <tag>/segment-<n0>-<n1>)")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        video, tag, _ = vf.resolve(args.video)
        track = vf.read_track(args.track)
        n0 = args.n0 if args.n0 is not None else max(1, min(track) - (3 * HALF if args.still else 0))
        n1 = args.n1 if args.n1 is not None else max(track) + (3 * HALF if args.still else 0)
        clip = vclip.Clip(video, args.workdir, n0, n1)
        out = vclip.out_prefix(args.out, tag, vclip.named(args.n0, args.n1, clip))
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
        off = tuple(float(v) for v in args.offset.split(",")) if args.offset else None
        found = measure(clip, track, args.dark, args.still, args.aperture, off, args.depression, out, progress=print)
        print("\n".join(said(found.fields)))
        for w in found.no_power:
            print(f"  no power: {w[1]}")
        for f in found.files:
            print(f"  wrote {f}")
    code = vclip.EXIT_NOTHING if found.no_power else 0
    if args.json:
        emit(found.envelope("aspect", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
