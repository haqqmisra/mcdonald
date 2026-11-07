"""`mcdonald horizon` — what the horizon says about range and height, with no motion and no known size.

  mcdonald horizon VIDEO --track CSV --horizon N,X,Y --height 7000ft (--fov DEG | --graticule PX_DEG) [--json]

Over the sea the visible horizon lies below the camera's level by the **dip**, the angle a ray from height h makes
grazing the curved surface: cos(dip) = R' / (R' + h), about sqrt(2 h / R'), with R' the Earth's radius as refraction
bends the ray -- R / (1 - kappa), kappa 0.13 in a standard atmosphere, 0 with none, a quarter or more over a cold
sea. A thing in the picture is a measured angle above or below that line (its pixels across the line over k, the
pixels a degree). Two bounds follow, each needing k and h, which the report gives as what they are (measured,
given, or assumed):

- **Below the horizon, seen against the sea**: the line of sight meets the sea at a range d_s, where depression
  dip + delta reaches the surface, and the thing is in front of the sea it is seen against: its range is at most
  d_s. From 7,000 ft a thing a degree below the horizon is within 57 km, three degrees below within 29 km (the
  horizon itself is 177 km off): close under the horizon the bound is weak, and it tightens fast below it. It is an
  upper bound on range from one frame, and with the track's rate an upper bound on its transverse speed.
- **Above the horizon**: the line of sight never meets the sea, and its lowest point over the surface -- where the
  ray passes closest to the Earth's centre -- is how low the thing can be, at any range: it is at least that high.
  At a range known from elsewhere, its height.

The horizon line is found in the picture, not assumed level: from a point a person put on it (a `horizon` mark, or
`--horizon N,X,Y`), the strongest straight step in brightness from top to bottom within REACH px of that point and
TILT_DEG of level (`fit_line`: the vertical derivative's mean along each candidate line, its peak refined to a
fraction of a pixel), then followed from frame to frame along the track, each frame searched about the last one's
line. The distance across the line is measured in square pixels (`--pixel-aspect`).

The band is the conservative corner of everything that is not known exactly: the line's and the object's place
(each frame's scatter, at least a pixel), k's share (10 % for an assumed field of view), h's, and kappa from 0 to
KAPPA_HI. A range bound takes the largest range in that box, a height bound the lowest height.

What it assumes, and says on every run: (1) the line is the sea's horizon -- not a haze top (which lies above it in
a hazy sky), a coastline or the top of a cloud deck (nearer, and at a height of its own); over land a skyline is
terrain at a range of its own, and neither bound holds; (2) for the range bound, the thing is seen against the sea
itself and not against something nearer standing up from it (a ship, a cloud); (3) h is the camera's height above
the sea; (4) k is the picture's scale across the line, in square pixels.

What it cannot do: say anything of a thing within the band of the line (the line's own scatter, or the error of k
times the angle); tell a sea horizon from a haze line; or use a land horizon.
"""
import csv
import math
from pathlib import Path

import numpy as np
from scipy import ndimage

from .report import Found

R_EARTH = 6_371_000.0   # m, the mean radius
KAPPA = 0.13            # refraction's share of the Earth's curvature in a standard atmosphere
KAPPA_HI = 0.25         # the band's other end: a cold sea bends rays more (ducting can exceed it; it is said so)
REACH = 12.0            # px either side of the given point (or the last frame's line) searched for the line
TILT_DEG = 10.0         # the line's tilt from the image's level searched, deg either side
TILT_STEP = 0.25        # deg
SIGMA = 1.5             # px: the vertical derivative's smoothing
PROMINENCE = 10.0       # the line's step over its surface (MADs of its tilt's lines over the frame, 6 px or more
                        # off it); a frame of noise, its best line chosen from the whole search, reaches 5
LINE_PX = 1.0           # px: the line's place is good to no better than this, whatever its fit says
OBJECT_PX = 1.0         # px: and the object's
K_SHARE_ASSUMED = 0.10  # an assumed field of view's share of error


# ---- the geometry -------------------------------------------------------------------------
def radius(kappa=KAPPA):
    """The Earth's radius as a ray refracted by kappa sees it."""
    return R_EARTH / (1.0 - kappa)


def dip(h, kappa=KAPPA):
    """The visible horizon's angle below the camera's level, rad, from height h (m)."""
    Rp = radius(kappa)
    return math.acos(Rp / (Rp + max(h, 0.0)))


def surface_range(h, depression, kappa=KAPPA):
    """How far a ray from height h (m), `depression` rad below level, goes before it meets the surface (m); inf for
    one that never does (above the horizon)."""
    Rp = radius(kappa)
    a = Rp + h
    s = math.sin(depression)
    disc = a * a * s * s - (2.0 * Rp * h + h * h)
    if depression <= 0 or disc < 0:
        return math.inf
    return a * s - math.sqrt(disc)


def lowest_height(h, elevation, kappa=KAPPA):
    """The least height over the surface (m) a ray from height h at `elevation` rad (negative below level) reaches
    anywhere along it: at the camera itself for a ray at or above level, else where it passes closest to the
    Earth's centre (the ray must clear the surface: elevation above minus the dip)."""
    Rp = radius(kappa)
    if elevation >= 0:
        return h
    return (Rp + h) * math.cos(elevation) - Rp


def height_at(h, elevation, r, kappa=KAPPA):
    """A ray's height over the surface (m) at range r (m) along it."""
    Rp = radius(kappa)
    a = Rp + h
    return math.sqrt(a * a + r * r + 2.0 * a * r * math.sin(elevation)) - Rp


# ---- the line ---------------------------------------------------------------------------
def fit_line(grey, x, y, mask=None, reach=REACH, tilt=TILT_DEG, slope0=0.0):
    """The horizon near (x, y) in one frame: dict(y0 -- the line's height at x --, slope -- dy/dx --, score, prominence,
    sign -- +1 where the frame is brighter below the line --, cols -- the columns it was measured over), or None.

    Each candidate line through (x, y + o), o within `reach`, tilted by up to `tilt` deg from `slope0` (the last
    frame's), is scored by the vertical derivative of the frame (a Gaussian's, SIGMA px) averaged along it over the
    columns the overlay leaves clear; the best by its size, its offset refined by a parabola. A line is one whose
    score stands PROMINENCE MADs over the lines of its tilt across the whole frame's height, 6 px or more off it (the
    surface its peak stands on: the other tilts' lines near it score nearly as well, and the soft edge's own shoulders
    fill a surface taken only within the search)."""
    g = np.asarray(grey, np.float32)
    H, W = g.shape
    dy = ndimage.gaussian_filter(g, SIGMA, order=(1, 0))
    if mask is not None:
        dy = np.where(mask, np.nan, dy)
    cols = np.arange(0, W, 2, dtype=np.float32)
    offs = np.arange(-reach, reach + 0.25, 0.5, dtype=np.float32)
    angs = np.arange(-tilt, tilt + 1e-6, TILT_STEP)
    best, scores = None, []
    for ang in angs:
        sl = slope0 + math.tan(math.radians(ang))
        yy = (y + offs[:, None] + sl * (cols[None, :] - x)).astype(np.float32)
        ok = (yy >= 0) & (yy <= H - 1)
        v = ndimage.map_coordinates(np.nan_to_num(dy, nan=0.0), [np.clip(yy, 0, H - 1), np.broadcast_to(cols, yy.shape)],
                                    order=1, mode="nearest")
        if mask is not None:
            m = ndimage.map_coordinates(np.isnan(dy).astype(np.float32), [np.clip(yy, 0, H - 1),
                                                                          np.broadcast_to(cols, yy.shape)], order=0)
            ok &= m < 0.5
        n = ok.sum(1)
        s = np.where(n >= 0.3 * len(cols), (v * ok).sum(1) / np.maximum(n, 1), 0.0)
        scores.append(s)
        i = int(np.argmax(np.abs(s)))
        if best is None or abs(s[i]) > abs(best[2]):
            best = (ang, i, float(s[i]), sl, s)
    ang, i, sc, sl, s = best
    # the surface the peak stands on: the best tilt's lines over the whole frame's height, 6 px or more off it
    ys = np.arange(1.0, H - 1.0, 1.0, dtype=np.float32) - (y - 0.0)
    yy = (y + ys[:, None] + sl * (cols[None, :] - x)).astype(np.float32)
    ok = (yy >= 0) & (yy <= H - 1)
    v = ndimage.map_coordinates(np.nan_to_num(dy, nan=0.0), [np.clip(yy, 0, H - 1), np.broadcast_to(cols, yy.shape)],
                                order=1, mode="nearest")
    if mask is not None:
        m = ndimage.map_coordinates(np.isnan(dy).astype(np.float32), [np.clip(yy, 0, H - 1),
                                                                      np.broadcast_to(cols, yy.shape)], order=0)
        ok &= m < 0.5
    n = ok.sum(1)
    prof = np.where(n >= 0.3 * len(cols), (v * ok).sum(1) / np.maximum(n, 1), np.nan)
    rest = np.abs(prof[(np.abs(ys - offs[i]) > 6.0) & np.isfinite(prof)])
    if len(rest) < 8:
        return None
    med = float(np.median(rest))
    mad = 1.4826 * float(np.median(np.abs(rest - med))) + 1e-9
    prom = (abs(sc) - med) / mad
    if prom < PROMINENCE:
        return None
    o = float(offs[i])
    if 0 < i < len(offs) - 1:
        a, b, c = abs(s[i - 1]), abs(s[i]), abs(s[i + 1])
        den = a - 2 * b + c
        if den < 0:
            o += 0.5 * 0.5 * (a - c) / den
    return dict(y0=float(y + o), x0=float(x), slope=float(sl), score=float(sc), prominence=float(prom),
                sign=int(np.sign(sc)))


def follow(frames_grey, start, mask=None):
    """The line on each of `frames_grey` ({frame: grey}, in order), each searched about the last one's: {frame: line}
    for the frames where one stands. `start` is (frame, x, y): a point on the line in one of them."""
    n0, x, y = start
    order = sorted(frames_grey)
    out = {}
    first = min(order, key=lambda n: abs(n - n0))
    i0 = order.index(first)
    for seq in (order[i0:], order[i0::-1]):
        cx, cy, sl = x, y, 0.0
        for n in seq:
            ln = fit_line(frames_grey[n], cx, cy, mask, slope0=sl, tilt=TILT_DEG if n == first else 2.0)
            if ln is None:
                continue
            out[n] = ln
            cx, cy, sl = ln["x0"], ln["y0"], ln["slope"]
    return out


def across(line, x, y, pixel_aspect=1.0):
    """The signed distance of (x, y) from the line, square px, positive below it."""
    a = pixel_aspect
    sl = line["slope"] * a                      # the slope in square pixels: x is divided by a
    yl = line["y0"] + line["slope"] * (x - line["x0"])
    return (y - yl) / math.sqrt(1.0 + sl * sl)


# ---- the bounds -------------------------------------------------------------------------
def bounds(delta_deg, delta_err_deg, h, h_err, k_share, range_m=None):
    """From the angle below (+) or above (-) the horizon line and its error, h and its error, and k's share of error:
    dict(below, range_max_m, range_nominal_m, height_min_m, height_nominal_m, height_at_range_m, ...), each bound the
    conservative corner of the box (the angle +- its error, scaled by 1 -+ k's share; h +- its error; kappa 0 to
    KAPPA_HI)."""
    corners = []
    for dd in (-1, 1):
        for kk in (-1, 1):
            for hh in (-1, 1):
                for kap in (0.0, KAPPA, KAPPA_HI):
                    d = (delta_deg + dd * delta_err_deg) * (1 + kk * k_share)
                    corners.append((math.radians(d), max(h + hh * h_err, 0.0), kap))
    nominal = (math.radians(delta_deg), h, KAPPA)
    out = dict(below=bool(delta_deg > 0), delta_deg=delta_deg, delta_err_deg=delta_err_deg)
    if delta_deg > 0:
        rs = [surface_range(hh, dip(hh, kap) + d, kap) for d, hh, kap in corners]
        out.update(range_max_m=max(rs), range_nominal_m=surface_range(h, dip(h, KAPPA) + nominal[0], KAPPA),
                   horizon_m=math.sqrt(2 * h * radius(KAPPA)),
                   within_band=bool(not math.isfinite(max(rs))))
    else:
        zs = [lowest_height(hh, -dip(hh, kap) - d, kap) if -dip(hh, kap) - d > -dip(hh, kap) else -math.inf
              for d, hh, kap in corners]
        out.update(height_min_m=min(zs), height_nominal_m=lowest_height(h, -dip(h, KAPPA) - nominal[0], KAPPA),
                   within_band=bool(not math.isfinite(min(zs))))
        if range_m:
            hs = [height_at(hh, -dip(hh, kap) - d, range_m, kap) for d, hh, kap in corners]
            out.update(height_at_range_m=[min(hs), max(hs)],
                       height_at_range_nominal_m=height_at(h, -dip(h, KAPPA) - nominal[0], range_m, KAPPA))
    return out


def measure(clip, track, start, h, k, k_share, h_err=0.0, pixel_aspect=1.0, line=None, range_m=None, mask=None,
            out=None, name="clip", k_from="given"):
    """The stage: the line on every tracked frame (followed from `start`, or `line` given as (x0, y0, x1, y1) for a
    camera that holds still), the object's angle from it, and the bounds on the median frame's angle. A Found."""
    res, npw, needs, notes = {}, [], [], []
    if not track:
        return Found("horizon", no_power=[("horizon", "no track: nothing to set against the horizon")])
    if line is not None:
        x0, y0, x1, y1 = line
        fixed = dict(y0=float(y0), x0=float(x0), slope=float((y1 - y0) / (x1 - x0)) if x1 != x0 else 0.0,
                     score=None, prominence=None, sign=0)
        lines = {n: fixed for n in track}
        found_how = f"given: ({x0:g}, {y0:g}) to ({x1:g}, {y1:g})"
    else:
        lines = follow({n: clip.grey(n) for n in sorted(track)}, start, mask)
        found_how = f"found from the point ({start[1]:g}, {start[2]:g}) on frame {start[0]}"
    rows = []
    for n in sorted(track):
        ln = lines.get(n)
        if ln is None:
            continue
        x, y = track[n]
        rows.append(dict(frame=n, x=x, y=y, line_y=ln["y0"] + ln["slope"] * (x - ln["x0"]),
                         tilt_deg=math.degrees(math.atan(ln["slope"] * pixel_aspect)),
                         across_px=across(ln, x, y, pixel_aspect), prominence=ln.get("prominence")))
    fields = dict(frames=len(track), frames_with_line=len(rows), line_from=found_how, k_px_per_deg=k, k_from=k_from,
                  k_share=k_share, height_m=h, height_err_m=h_err, kappa=[0.0, KAPPA, KAPPA_HI], pixel_aspect=pixel_aspect,
                  rows=rows, bounds=None)
    if not rows:
        npw.append(("horizon", f"no horizon line stood out ({PROMINENCE:g} MADs over the other candidates) near "
                               f"the point given, on any tracked frame"))
        return Found("horizon", res, fields, no_power=npw)
    a = np.array([r["across_px"] for r in rows])
    med = float(np.median(a))
    scatter = 1.4826 * float(np.median(np.abs(a - med))) if len(a) > 2 else 0.0
    err_px = math.hypot(max(scatter, LINE_PX), OBJECT_PX)
    fields.update(across_px=med, across_scatter_px=scatter, across_err_px=err_px)
    res["horizon line"] = (f"{found_how}; on {len(rows)} of {len(track)} tracked frames, tilted "
                           f"{np.median([r['tilt_deg'] for r in rows]):+.2f} deg")
    res["the object"] = (f"{abs(med):.1f} px {'below' if med > 0 else 'above'} the line (median; frame-to-frame scatter "
                         f"{scatter:.1f} px)")
    if not k:
        npw.append(("horizon", "no angular scale: --fov (with --fov-px) or --graticule, or k from `mcdonald slew`"))
    if h is None:
        npw.append(("horizon", "the camera's height over the sea is not given: --height (7000ft, 2100m)"))
    if npw:
        return Found("horizon", res, fields, no_power=npw, needs=needs)
    d = med / k
    b = bounds(d, err_px / k, h, h_err, k_share, range_m)
    fields["bounds"] = b
    dp = math.degrees(dip(h, KAPPA))
    res["dip"] = f"the sea's horizon {dp:.3f} deg below level from {h:.0f} m (kappa {KAPPA:g}; {math.degrees(dip(h, 0)):.3f} " \
                 f"with no refraction, {math.degrees(dip(h, KAPPA_HI)):.3f} at {KAPPA_HI:g})"
    if b["within_band"]:
        npw.append(("horizon", f"the object is {abs(d):.3f} +- {err_px / k:.3f} deg from the line: within its band, so "
                               "neither below nor above it for certain"))
    elif b["below"]:
        res["range"] = (f"at most {b['range_max_m'] / 1000:.2f} km (nominal {b['range_nominal_m'] / 1000:.2f} km): "
                        f"{d:.3f} +- {err_px / k:.3f} deg below the horizon, IF it is seen against the sea there")
    else:
        res["height"] = (f"at least {b['height_min_m']:.0f} m over the sea at any range (nominal "
                         f"{b['height_nominal_m']:.0f} m): {-d:.3f} +- {err_px / k:.3f} deg above the horizon")
        if range_m:
            lo, hi = b["height_at_range_m"]
            res["height at the range given"] = f"{lo:.0f}-{hi:.0f} m at {range_m / 1000:.2f} km"
    notes.append("Assumes the line is the sea's horizon: not a haze top, a coastline, a cloud deck or a skyline over "
                 "land; h is the camera's height over the sea; k is the scale across the line, in square pixels.")
    if k_from == "assumed":
        notes.append(f"k comes from an assumed field of view: its {k_share:.0%} share of error is in the band.")
    files = []
    if out:
        files = write(out, name, rows, fields)
    return Found("horizon", res, fields, no_power=npw, needs=needs, notes=notes, files=files)


def write(out, name, rows, fields):
    p = Path(f"{out}_horizon.csv")
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["frame", "x", "y", "line_y", "tilt_deg", "across_px"])
        for r in rows:
            w.writerow([r["frame"], f"{r['x']:.2f}", f"{r['y']:.2f}", f"{r['line_y']:.2f}", f"{r['tilt_deg']:.3f}",
                        f"{r['across_px']:.2f}"])
    files = [str(p)]
    try:
        files.append(figure(f"{out}_horizon.png", name, rows, fields))
    except Exception:                                 # a figure is never worth the measurement
        pass
    return files


def figure(path, name, rows, fields):
    from .figures import PRIMARY, setup, save
    plt = setup(9)
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 3.6), constrained_layout=True)
    fr = [r["frame"] for r in rows]
    a.plot(fr, [r["across_px"] for r in rows], ".", ms=3, color="C0")
    a.axhline(0, color=PRIMARY, lw=0.8)
    a.set_xlabel("Frame", fontweight="bold")
    a.set_ylabel("Below the horizon (pixels)", fontweight="bold")
    b.plot(fr, [r["tilt_deg"] for r in rows], ".", ms=3, color="C1")
    b.set_xlabel("Frame", fontweight="bold")
    b.set_ylabel("Tilt of the horizon (degrees)", fontweight="bold")
    bd = fields.get("bounds") or {}
    title = (f"the object is at most {bd['range_max_m'] / 1000:.2f} km away" if bd.get("range_max_m") and math.isfinite(bd["range_max_m"])
             else f"the camera is at least {bd['height_min_m']:.0f} m up" if bd.get("height_min_m") is not None
             and math.isfinite(bd["height_min_m"]) else "no limit on the distance")
    fig.suptitle(f"{name}: the sea's horizon -- {title}", fontweight="bold")
    save(fig, path, dpi=110)
    plt.close(fig)
    return path


def said(f):
    L = []
    if f.get("rows"):
        L.append(f"the line: {f['line_from']}; on {f['frames_with_line']} of {f['frames']} tracked frames")
        if f.get("across_px") is not None:
            L.append(f"the object {abs(f['across_px']):.1f} +- {f['across_err_px']:.1f} px "
                     f"{'below' if f['across_px'] > 0 else 'above'} the line")
    b = f.get("bounds")
    if b:
        if b["within_band"]:
            L.append("within the line's band: no bound")
        elif b["below"]:
            L.append(f"range at most {b['range_max_m'] / 1000:.2f} km (nominal {b['range_nominal_m'] / 1000:.2f}; the "
                     f"horizon itself {b['horizon_m'] / 1000:.1f} km off)")
        else:
            L.append(f"height at least {b['height_min_m']:.0f} m over the sea at any range (nominal "
                     f"{b['height_nominal_m']:.0f})")
            if b.get("height_at_range_m"):
                L.append(f"at the range given: {b['height_at_range_m'][0]:.0f}-{b['height_at_range_m'][1]:.0f} m")
    return L


def parse_height(text):
    """'7000ft' or '2100m' (or a bare number, metres) -> metres."""
    import re
    t = str(text).strip().lower().replace(" ", "")
    m = re.fullmatch(r"([0-9.]+)(ft|m)?", t)
    if not m:
        raise ValueError(f"{text!r}: give a height as 7000ft or 2100m")
    return float(m.group(1)) * (0.3048 if m.group(2) == "ft" else 1.0)


def main():
    from .report import case_option, command_line, into_case
    import argparse
    from . import clip as vclip
    from . import forensics as vf
    from .report import emit, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", required=True, help="CSV with frame and x/y columns: the object")
    ap.add_argument("--horizon", metavar="N,X,Y", help="a point on the horizon in frame N, px; the line is found "
                    "through it and followed along the track")
    ap.add_argument("--marks", metavar="JSON", help="a `mcdonald mark` file: its first `horizon` mark is the point")
    ap.add_argument("--line", metavar="X0,Y0,X1,Y1", help="the horizon as a line, px, for a camera that holds still "
                    "(in place of finding it)")
    ap.add_argument("--height", help="the camera's height over the sea: 7000ft or 2100m")
    ap.add_argument("--height-err", help="its error, in the same form (default 0)")
    ap.add_argument("--fov", type=float, help="the horizontal field of view, deg (an assumption unless a display gives it)")
    ap.add_argument("--fov-px", type=float, help="how many pixels that field spans (default the frame's width)")
    ap.add_argument("--fov-given", action="store_true", help="the field of view is read off the display, not assumed")
    ap.add_argument("--graticule", type=float, help="px per degree, off the camera's own scale")
    ap.add_argument("--k-share", type=float, help=f"the share by which k may be off (default {K_SHARE_ASSUMED:g} for an "
                    "assumed field of view, 0.01 for one given or a graticule)")
    ap.add_argument("--pixel-aspect", type=float, default=1.0, help="how much wider the video draws a pixel than it is "
                    "tall (a 4:3 picture shown full-height in 16:9: 1.333)")
    ap.add_argument("--range", type=float, metavar="M", help="the range to the object from elsewhere, m: its height there")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--workdir")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true", help="print the measurement as JSON on stdout")
    case_option(ap)
    args = ap.parse_args()
    if not (args.horizon or args.marks or args.line):
        ap.error("say where the horizon is: --horizon N,X,Y, --marks JSON (a horizon mark), or --line X0,Y0,X1,Y1")
    with said_to_stderr(args.json) as lines:
        video, tag, _ = vf.resolve(args.video)
        track = vf.read_track(args.track)
        n0, n1 = args.n0 or min(track), args.n1 or max(track)
        clip = vclip.Clip(video, args.workdir, n0, n1)
        out = vclip.out_prefix(args.out, tag, vclip.named(args.n0, args.n1, clip))
        track = {n: xy for n, xy in track.items() if clip.n0 <= n <= clip.n1}
        start = None
        if args.horizon:
            n, x, y = (float(v) for v in args.horizon.split(","))
            start = (int(n), x, y)
        elif args.marks:
            from .mark import MarkSet
            hm = MarkSet("", "", 0).load(args.marks).marks.get("horizon", {})
            if not hm:
                raise SystemExit(f"{args.marks} has no horizon mark")
            n = min(hm)
            start = (n, *hm[n])
        line = tuple(float(v) for v in args.line.split(",")) if args.line else None
        W = clip.W / args.pixel_aspect
        k, k_from = None, None
        if args.graticule:
            k, k_from = args.graticule, "graticule"
        elif args.fov:
            k, k_from = (args.fov_px / args.pixel_aspect if args.fov_px else W) / args.fov, "given" if args.fov_given else "assumed"
        share = args.k_share if args.k_share is not None else (K_SHARE_ASSUMED if k_from == "assumed" else 0.01)
        h = parse_height(args.height) if args.height else None
        he = parse_height(args.height_err) if args.height_err else 0.0
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
        masks = vf.static_masks(clip) if line is None else None
        mask = None if masks is None else (masks["blocks"] | masks["graphics"])
        found = measure(clip, track, start, h, k, share, he, args.pixel_aspect, line, args.range, mask, out, tag,
                        k_from or "none")
        print("\n".join(said(found.fields)))
        for w in found.no_power:
            print(f"no power: {w[1]}")
        for f in found.files:
            print(f"wrote {f}")
        if args.case:
            print(f"recorded in {into_case(found, args.case, command_line())}")
    code = vclip.EXIT_NOTHING if found.no_power and not found.fields.get("bounds") else 0
    if args.json:
        emit(found.envelope("horizon", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
