"""Reading the burned-in overlay: boresight, north pointer, corner brackets.

The overlay is the only instrument whose readings survive redaction on most
released clips. Range, altitude and pointing angles are usually blacked out or
never present, but the reticle and the north pointer are drawn in the open, and
both carry measurable information:

- the **boresight** (reticle intersection) is the origin every other screen
  measurement should be referenced to, and on a hand-held or re-photographed
  capture it is the only way to separate camera shake from object motion;
- the **north pointer** gives the sensor's azimuth. It is drawn at a radius
  that is fixed within a clip to a few tenths of a percent, so its *angle* is a
  real per-frame reading and its rotation rate is the line-of-sight azimuth
  rate. Pointing is therefore **not** withheld on clips that draw it, whatever
  a redaction tag says;
- the **corner brackets** mark the *next* narrower field of view, not the
  current one and not a fixed angle. They are read here only for the box they
  describe, which can identify a crop (PR149's bracket box is exactly half of
  1920x1080, which is how its 1028-row release was shown to be a crop of a
  1080-line original). Never derive a zoom ratio from them: use
  forensics.zoom_ratio, which fits it from the imagery.

Three detection routes, because the overlays differ:

    chroma      coloured symbology (PR149 magenta, PR144 orange): segment by
                saturation, then identify glyphs by shape and position.
    template    monochrome symbology (PR148 white-on-black): NCC of the first
                frame's glyph *gradient magnitude*, searched independently
                every frame. Gradient, because the sea brightness behind the
                glyph changes; independently, because a frame-to-frame walk
                drifts off as the codec redraws the strokes.
    lines       the reticle as lines rather than as glyphs (PR117): a
                Radon-style search scoring each candidate line by the white
                top-hat it sums. This is the route to use when the reticle is
                a periodic tick train -- phase correlation aliases onto the
                tick spacing and returns nonsense, and NCC of a large patch
                saturates.

Angle convention throughout: **theta is clockwise from screen-up**, measured
about the boresight, so theta = -azimuth. A pointer rotating with
d(theta)/dt > 0 means the platform is moving toward image-RIGHT across the
line of sight, and a stationary object nearer than the background then drifts
image-LEFT against it.

Two caveats that belong with every number this module produces:
- The pointer gives true north *as projected into the image*. Turning an
  image-plane direction into a ground bearing also needs the depression angle,
  because the down-range axis is compressed by sin(depression). At ~30 deg
  that is a few degrees, not tens, but it is not zero.
- Reading the rotation as azimuth change assumes the image roll is constant
  and the aim point is ground-fixed over the segment. Check that against the
  background flow before relying on the sign.
"""
import numpy as np
from scipy import ndimage

from . import forensics as vf


# ---- glyphs -------------------------------------------------------------------------
def chroma_glyphs(rgb, chroma=40, min_area=12, max_side=60):
    """Coloured overlay glyphs: connected components of saturated pixels.

    max_side drops the redaction blocks, which are large; min_area drops codec
    speckle. Returns dicts with area, centroid, width and height."""
    sat = rgb.max(2).astype(int) - rgb.min(2).astype(int)
    lab, _ = ndimage.label(sat > chroma, structure=np.ones((3, 3)))
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        if sl is None:
            continue
        m = lab[sl] == i
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if int(m.sum()) < min_area or h > max_side or w > max_side:
            continue
        ys, xs = np.nonzero(m)
        out.append(dict(area=int(m.sum()), cx=float(xs.mean() + sl[1].start),
                        cy=float(ys.mean() + sl[0].start), w=w, h=h))
    return out


def hue_glyphs(rgb, box=None, chroma=70, warm=60, min_h=10, max_h=30, min_w=8,
               max_w=30, min_area=20):
    """A single warm-coloured glyph (PR144's orange "N") inside a search box.

    Returns its bounding-box centre, which for an "N" is a better centre than
    the centroid: the diagonal stroke biases the mean toward one side."""
    y0, y1, x0, x1 = box or (0, rgb.shape[0], 0, rgb.shape[1])
    sub = rgb[y0:y1, x0:x1].astype(int)
    m = ((sub.max(2) - sub.min(2)) > chroma) & (sub[..., 0] > sub[..., 2] + warm)
    lab, _ = ndimage.label(ndimage.binary_closing(m, iterations=1))
    best = None
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        a = int((lab[sl] == i).sum())
        if min_h <= h <= max_h and min_w <= w <= max_w and a >= min_area \
                and (best is None or a > best[2]):
            best = ((sl[1].start + sl[1].stop - 1) / 2 + x0,
                    (sl[0].start + sl[0].stop - 1) / 2 + y0, a)
    return None if best is None else (best[0], best[1])


# ---- boresight ----------------------------------------------------------------------
def reticle_from_chroma(rgb, glyphs=None):
    """Boresight as the mean of the four coloured ticks nearest frame centre."""
    g = glyphs if glyphs is not None else chroma_glyphs(rgb)
    if len(g) < 4:
        return None
    cx0, cy0 = rgb.shape[1] / 2, rgb.shape[0] / 2
    g = sorted(g, key=lambda d: np.hypot(d["cx"] - cx0, d["cy"] - cy0))[:4]
    return float(np.mean([t["cx"] for t in g])), float(np.mean([t["cy"] for t in g]))


def tophat(g, size=9):
    """Keeps the thin bright strokes of a reticle, drops the soft scene."""
    return np.maximum(g - ndimage.grey_opening(g, size=(size, size)), 0)


def _parabola(m, o, p):
    d = m - 2 * o + p
    return 0.0 if abs(d) < 1e-9 else float(np.clip((m - p) / (2 * d), -1, 1))


def fit_line(g, intercepts, slopes, samples, vertical):
    """Best (intercept, slope) by summing the top-hat along each candidate line.

    vertical=True fits x = a + b*y over the y samples, else y = c + d*x.
    Sub-pixel on the intercept only: that is what the boresight needs, and the
    slope grid is already finer than the fit is stable to."""
    H, W = g.shape
    P = np.rint(intercepts[:, None, None] + slopes[None, :, None] * samples[None, None, :])
    P = P.astype(np.int32)
    T = np.broadcast_to(samples[None, None, :], P.shape)
    if vertical:
        score = (g[T, np.clip(P, 0, W - 1)] * ((P >= 0) & (P < W))).sum(2)
    else:
        score = (g[np.clip(P, 0, H - 1), T] * ((P >= 0) & (P < H))).sum(2)
    i, j = np.unravel_index(np.argmax(score), score.shape)
    di = _parabola(score[i - 1, j], score[i, j], score[i + 1, j]) if 0 < i < len(intercepts) - 1 else 0.0
    return float(intercepts[i] + di * (intercepts[1] - intercepts[0])), float(slopes[j]), float(score[i, j])


def boresight_from_lines(g, v_intercept, h_intercept, ys=None, xs=None,
                         v_slope=(-0.10, 0.10), h_slope=(-0.03, 0.15), refine=True):
    """Reticle intersection by fitting the two lines. No accumulation, so no
    drift: every frame is solved independently and absolutely.

    v_intercept/h_intercept are (lo, hi) search ranges for x at y=0 and y at
    x=0. ys/xs sample along each line and should skip the region where the
    other line and the object cross it."""
    H, W = g.shape
    ys = np.arange(0, H, 3) if ys is None else ys
    xs = np.arange(0, W, 3) if xs is None else xs
    t = tophat(g)
    a, b, s1 = fit_line(t, np.arange(*v_intercept, 1.0), np.arange(*v_slope, 0.004), ys, True)
    c, d, s2 = fit_line(t, np.arange(*h_intercept, 1.0), np.arange(*h_slope, 0.004), xs, False)
    if refine:
        a, b, s1 = fit_line(t, np.arange(a - 3, a + 3, 0.25),
                            np.arange(b - 0.004, b + 0.004, 0.0005), ys, True)
        c, d, s2 = fit_line(t, np.arange(c - 3, c + 3, 0.25),
                            np.arange(d - 0.004, d + 0.004, 0.0005), xs, False)
    y = (c + d * a) / (1 - d * b)
    return (a + b * y, y), (a, b, c, d), (s1, s2)


# ---- the north pointer --------------------------------------------------------------
def bearing(px, py, bore):
    """(radius, theta) of a point about the boresight; theta clockwise from up."""
    dx, dy = px - bore[0], py - bore[1]
    return float(np.hypot(dx, dy)), float(np.degrees(np.arctan2(dx, -dy)) % 360.0)


def north_from_chroma(rgb, bore=None, r_frac=(0.20, 0.36)):
    """The "N" as the odd glyph out in an annulus about the boresight.

    The four corner brackets also sit in that annulus, but they come as a
    symmetric set of four; the pointer does not, which is what distinguishes
    it without hard-coding any coordinate."""
    g = chroma_glyphs(rgb)
    if len(g) < 5:
        return None
    bore = bore or reticle_from_chroma(rgb, g)
    if bore is None:
        return None
    cx0, cy0 = rgb.shape[1] / 2, rgb.shape[0] / 2
    rest = sorted(g, key=lambda d: np.hypot(d["cx"] - cx0, d["cy"] - cy0))[4:]
    best = None
    for d in rest:
        r = np.hypot(d["cx"] - bore[0], d["cy"] - bore[1])
        if not (r_frac[0] * rgb.shape[0] <= r <= r_frac[1] * rgb.shape[0]):
            continue
        mirrored = any(abs((o["cx"] - bore[0]) + (d["cx"] - bore[0])) < 12
                       and abs(abs(o["cy"] - bore[1]) - abs(d["cy"] - bore[1])) < 12
                       for o in rest if o is not d)
        if mirrored:
            continue
        if best is None or d["area"] > best["area"]:
            best = d
    if best is None:
        return None
    r, th = bearing(best["cx"], best["cy"], bore)
    return dict(x=best["cx"], y=best["cy"], r_px=r, theta_deg=th, bore=bore, quality=1.0)


def _grad(a, sigma=0.8):
    a = ndimage.gaussian_filter(a, sigma)
    return np.hypot(ndimage.sobel(a, 0), ndimage.sobel(a, 1))


def make_glyph_template(grey, box):
    """Gradient-magnitude template of the glyph in (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    t = _grad(grey)[y0:y1, x0:x1]
    return t - t.mean()


def north_from_template(grey, tpl, box, bore, search=(20, 45, 19), min_ncc=0.7):
    """Locate the glyph by NCC of gradient magnitude, searched from its
    original box every frame -- never chained, so nothing accumulates.

    search is (dx, up, down) in pixels. min_ncc guards the failure that costs
    a wrong reading: over bright texture the match wanders and still returns a
    position, so a low peak must be reported as unsolved, not as a number."""
    x0, y0, x1, y1 = box
    h, w = tpl.shape
    G = _grad(grey)
    sx, su, sd = search
    best = (-2.0, 0, 0)
    tn = float(np.sqrt((tpl * tpl).sum()))
    for dy in range(-su, sd + 1):
        for dx in range(-sx, sx + 1):
            b = G[y0 + dy:y0 + dy + h, x0 + dx:x0 + dx + w]
            if b.shape != tpl.shape:
                continue
            b = b - b.mean()
            den = tn * float(np.sqrt((b * b).sum()))
            c = float((tpl * b).sum() / den) if den > 0 else -2.0
            if c > best[0]:
                best = (c, dx, dy)
    c, dx, dy = best
    gx, gy = (x0 + x1 - 1) / 2 + dx, (y0 + y1 - 1) / 2 + dy
    r, th = bearing(gx, gy, bore)
    return dict(x=gx, y=gy, r_px=r, theta_deg=th, bore=bore, quality=c) if c >= min_ncc else None


def north_series(clip, frames, bore, method="chroma", box=None, tpl_box=None, **kw):
    """(frame, t, x, y, r_px, theta_deg, quality) over `frames`, unsolved dropped.

    Every frame is solved independently, so a gap is a gap and not a drift."""
    rows, tpl = [], None
    if method == "template":
        if tpl_box is None:
            raise ValueError("method='template' needs tpl_box=(x0,y0,x1,y1) of the glyph")
        tpl = make_glyph_template(clip.grey(clip.n0), tpl_box)
    for n in frames:
        if method == "chroma":
            s = north_from_chroma(clip.rgb(n), bore, **kw)
        elif method == "hue":
            p = hue_glyphs(clip.rgb(n), box=box, **kw)
            if p is None:
                s = None
            else:
                r, th = bearing(p[0], p[1], bore)
                s = dict(x=p[0], y=p[1], r_px=r, theta_deg=th, bore=bore, quality=1.0)
        elif method == "template":
            s = north_from_template(clip.grey(n), tpl, tpl_box, bore, **kw)
        else:
            raise ValueError(f"unknown method {method!r}")
        if s:
            rows.append((n, float(clip.t(n)), s["x"], s["y"], s["r_px"], s["theta_deg"], s["quality"]))
    return np.array(rows, float).reshape(-1, 7)


def unwrap_theta(theta):
    """Angles in degrees, unwrapped, so a fit across the 0/360 seam is sane."""
    return np.degrees(np.unwrap(np.radians(np.asarray(theta, float))))


def rotation_rate(series, t0=None, t1=None):
    """d(theta)/dt in deg/s over a time window, with the radius as a check.

    The radius is the check that matters: the pointer is drawn at a fixed
    radius, so a radius that wanders means the glyph was mislocated and the
    angle cannot be trusted either."""
    if len(series) < 3:
        return None
    t, r, th = series[:, 1], series[:, 4], unwrap_theta(series[:, 5])
    s = np.ones(len(t), bool)
    if t0 is not None:
        s &= t >= t0
    if t1 is not None:
        s &= t < t1
    if s.sum() < 3:
        return None
    slope, intercept = np.polyfit(t[s], th[s], 1)
    resid = th[s] - (slope * t[s] + intercept)
    return dict(dtheta_dt=float(slope), theta_mean=float(th[s].mean()),
                r_mean=float(r[s].mean()), r_sd=float(r[s].std()),
                r_frac_sd=float(r[s].std() / max(r[s].mean(), 1e-9)),
                resid_rms=float(np.sqrt((resid ** 2).mean())), n=int(s.sum()),
                t0=float(t[s].min()), t1=float(t[s].max()))


def cross_los_sense(dtheta_dt):
    """What the pointer's rotation says about the platform's motion.

    theta = -azimuth, so a pointer turning clockwise on screen means the
    line-of-sight azimuth is decreasing. Returns the direction the platform
    moves across the line of sight, and the direction parallax would push a
    stationary object nearer than the background."""
    if abs(dtheta_dt) < 1e-3:
        return dict(platform=None, parallax=None,
                    note="no measurable rotation: the sense is undetermined, not zero")
    right = dtheta_dt > 0
    return dict(platform="image-right" if right else "image-left",
                parallax="image-left" if right else "image-right",
                note="a stationary object nearer than the background drifts opposite "
                     "to the platform's cross-LOS motion")


def true_bearing(screen_dir_deg, theta_north_deg):
    """A screen direction turned into a compass bearing, using the pointer.

    Both angles are in the package convention (clockwise from screen-up), and
    the pointer shows where north lies in the image, so the bearing is simply
    the difference. This is the payoff of using one convention everywhere: a
    motion direction measured by `kinematics` or `comotion` can be compared
    directly with a pointer reading.

    Still an image-plane bearing. A ground bearing needs the depression angle
    as well, because the down-range axis is compressed by sin(depression)."""
    return float((screen_dir_deg - theta_north_deg) % 360.0)


# ---- corner brackets ----------------------------------------------------------------
def bracket_box(rgb, bore=None, area=(150, 400), tol=0.06):
    """The box the four L-glyphs mark, centroid to centroid, as (w, h).

    This is the NEXT field of view, not the current one. Its use is geometric:
    a box that is an exact fraction of a standard raster identifies a crop
    (PR149's is 959 x 540, half of 1920 x 1080, so its 1028-row release is a
    crop of a 1080-line original).

    The four are found as a *symmetric set*: four glyphs sharing the same
    |dx| and |dy| about the boresight, one per quadrant. Anything weaker
    invents boxes -- the north pointer is glyph-sized too, and sits nearer the
    boresight than the brackets do, so "the nearest in each quadrant" picks it
    up and returns a box that was never drawn."""
    g = chroma_glyphs(rgb)
    bore = bore or reticle_from_chroma(rgb, g) or (rgb.shape[1] / 2, rgb.shape[0] / 2)
    cand = [d for d in g if area[0] < d["area"] < area[1]]
    if len(cand) < 4:
        return None
    for d in cand:
        d["adx"], d["ady"] = abs(d["cx"] - bore[0]), abs(d["cy"] - bore[1])
    best = None
    for seed in cand:
        if seed["adx"] < 1 or seed["ady"] < 1:
            continue
        near = [d for d in cand
                if abs(d["adx"] - seed["adx"]) <= tol * seed["adx"]
                and abs(d["ady"] - seed["ady"]) <= tol * seed["ady"]]
        quad = {}
        for d in near:
            quad.setdefault((d["cx"] > bore[0], d["cy"] > bore[1]), d)
        if len(quad) == 4 and (best is None or seed["adx"] > best[0]["adx"]):
            best = (seed, quad)
    if best is None:
        return None
    quad = best[1]
    w = float(np.mean([d["adx"] for d in quad.values()])) * 2
    h = float(np.mean([d["ady"] for d in quad.values()])) * 2
    return (w, h)


# ---- CLI ----------------------------------------------------------------------------
def main():
    import argparse
    import csv

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--step", type=int, default=3, help="measure every step-th frame")
    ap.add_argument("--method", default="auto", choices=["auto", "chroma", "hue", "template"])
    ap.add_argument("--bore", help="x,y of the boresight (default: frame centre, or the "
                                   "coloured reticle when one is found)")
    ap.add_argument("--box", help="y0,y1,x0,x1 to search for a warm-coloured glyph (hue)")
    ap.add_argument("--tpl-box", help="x0,y0,x1,y1 of the glyph in the first frame (template)")
    ap.add_argument("--min-ncc", type=float, default=0.7)
    ap.add_argument("--windows", help="t0:t1,... time windows to fit the rotation over")
    ap.add_argument("--out", metavar="DIR", help="case directory for results "
                    "(default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    args = ap.parse_args()

    video, tag, _ = vf.resolve(args.video)
    clip = vf.Clip(video, args.workdir, args.n0, args.n1)
    out = vf.out_prefix(args.out, tag)
    frames = list(range(clip.n0, clip.n1 + 1, args.step))
    print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")

    first = clip.rgb(clip.n0)
    bore = tuple(float(v) for v in args.bore.split(",")) if args.bore else reticle_from_chroma(first)
    how = "coloured reticle" if bore and not args.bore else ("given" if args.bore else "frame centre")
    if bore is None:
        bore = (clip.W / 2.0, clip.H / 2.0)
    print(f"boresight: ({bore[0]:.1f}, {bore[1]:.1f})  [{how}]")

    method = args.method
    if method == "auto":
        method = "chroma" if north_from_chroma(first, bore) else ("template" if args.tpl_box else "hue")
        print(f"method: {method} (auto)")

    kw = {}
    if method == "hue":
        kw["box"] = tuple(int(v) for v in args.box.split(",")) if args.box else None
    if method == "template":
        kw["min_ncc"] = args.min_ncc
    series = north_series(clip, frames, bore, method=method,
                          tpl_box=tuple(int(v) for v in args.tpl_box.split(",")) if args.tpl_box else None,
                          **kw)

    if not len(series):
        print("no frames solved: the pointer was not found. Try --method, --box or --tpl-box.")
        return 1

    with open(f"{out}_north.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame", "t_s", "glyph_x", "glyph_y", "r_px", "theta_deg", "quality"])
        for r in series:
            w.writerow([int(r[0]), round(r[1], 4), round(r[2], 2), round(r[3], 2),
                        round(r[4], 2), round(r[5], 3), round(r[6], 3)])
    print(f"wrote {out}_north.csv: {len(series)}/{len(frames)} frames solved")

    whole = rotation_rate(series)
    print(f"radius {whole['r_mean']:.2f} +/- {whole['r_sd']:.2f} px "
          f"({whole['r_frac_sd']:.2%} of it) -- the check that the glyph was found, "
          "not the scene")
    if whole["r_frac_sd"] > 0.02:
        print("  WARNING: the radius is not fixed. The pointer is drawn at a constant "
              "radius, so this means mislocated frames; the angles are unreliable.")

    windows = [(None, None)]
    if args.windows:
        windows = [tuple(float(x) if x else None for x in w.split(":")) for w in args.windows.split(",")]
    print("rotation of the pointer (theta clockwise from screen-up, = -azimuth)")
    for t0, t1 in windows:
        rr = rotation_rate(series, t0, t1)
        if not rr:
            continue
        lab = f"t {rr['t0']:6.2f}-{rr['t1']:6.2f} s"
        print(f"  {lab}: theta {rr['theta_mean']:8.2f} deg, d(theta)/dt = "
              f"{rr['dtheta_dt']:+.3f} deg/s  (n={rr['n']}, residual {rr['resid_rms']:.2f} deg)")
        s = cross_los_sense(rr["dtheta_dt"])
        if s["platform"]:
            print(f"    -> platform moves {s['platform']} across the LOS; "
                  f"a stationary object nearer than the background drifts {s['parallax']}")
        else:
            print(f"    -> {s['note']}")

    bb = bracket_box(first, bore)
    if bb:
        print(f"corner brackets: box {bb[0]:.0f} x {bb[1]:.0f} px "
              f"({bb[0] / clip.W:.3f} x {bb[1] / clip.H:.3f} of the frame). "
              "These mark the NEXT field of view -- do not read a zoom ratio off them.")
    print("\nThe pointer gives north as projected into the image; a ground bearing also "
          "needs the depression angle. Reading its rotation as azimuth change assumes "
          "constant image roll and a ground-fixed aim point -- check the background flow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
