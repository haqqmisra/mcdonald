"""`mcdonald focus` — sharp means far: a floor on range from the object being as sharp as a point.

  mcdonald focus VIDEO --track CSV (--fov DEG | --graticule PX_DEG) [--band mwir] [--pupil 0.1m] [--json]

A lens focused at distance s draws a point at distance d as a disc of angular diameter D |1/d - 1/s|, D the entrance
pupil's diameter (Pentland's depth from defocus; what a focus puller works by). Focused at infinity the disc is D/d: the
pupil seen from the thing. A thing no wider than the clip's own points (`forensics.point_blur`: the sharpest quarter of
the compact spots in the scene, at half their peak) has a disc no wider than what its width leaves over theirs -- in
quadrature, sqrt(W^2 - b^2) with W its width and b theirs, at least half a blur, the least a measurement of width shows --
so d >= D / that. Turret optics have pupils of centimetres to tens of centimetres; where none is given, the optics
cannot draw a point narrower than their own diffraction, b >= 1.22 lambda / D, so D >= 1.22 lambda / b and
d >= 1.22 lambda / (b x disc), every angle in radians. The band's shortest wavelength is taken (the bound's cautious
end): 3 um for MWIR, 8 for LWIR, 0.4 for visible light and for a band not named.

It is a floor on range from one frame, from neither motion nor a known size, and it needs k (the angles) and focus at
infinity. Where the lens is focused nearer, at s, it is 1 / (1/s + 1/d_inf), and the scene's points are themselves sharp
at their own range, so s is at least as far as they are; the report gives d_inf and says so.

What it assumes, and says on every run: (1) the sensor is focused far -- at infinity, or at the scene's own points.
A camera that refocuses on the tracked thing (an autofocus, a crew focusing on it) makes the object sharp at any range,
and then the bound says nothing; a scene sharp behind the object is the check that it did not. (2) The object's width
is its image's, not its motion's: a smear along the track widens it, and the width across the track is what is used
where the track moves. (3) The blur b is the optics' and the chain's: a codec or a display that blurs everything makes
b wider than the optics', which weakens the bound and does not falsify it.

A thing wider than its points (it may be large, or near and out of focus) is read by its edge instead (`edge_blur`,
from the AARO Middle East Object's case, MEO11): profiles out from its centre, across its motion, each fitted with a
disc of radius rho seen through a Gaussian blur sigma (exact: a noncentral chi-square), its clipped core left out. A
defocus disc of diameter b adds b^2/16 to sigma^2, so b <= 4 sigma assuming nothing of the camera's own blur, or
4 sqrt(sigma^2 - sigma_points^2) assuming it blurs as the scene's points. One trap is closed: a small thing far out of
focus is drawn as a faint disc whose edge is as sharp as the thing is small, so a sharp edge alone says nothing. Its
core is then paler than black by (thing / disc)^2 at least, whatever its own shade, so both bounds are divided by the
square root of the core's depth as a share of the way from the ground beside it to the screen's black (0; one, where
the core reaches it). Only a dark object is read so: nothing is darker than black, but a bright thing may outshine
the whole scene, and a small one far out of focus draws the same sharp-edged disc. With a ground scale s (m/px, `--ground-scale`) and a pupil A, focused on the ground at R:
b = (A / s)(R / r - 1), so r / R >= 1 / (1 + b s / A), with no k and no R.

What it cannot do: work with no points in the scene (a clear sky, open sea): no blur, no bound; or tell a soft-edged
thing (smoke, a puff of dust) from one out of focus: a soft edge bounds nothing, and a sharp one is the result.
"""
import math

import numpy as np

from .report import Found

BANDS = {"visible": 0.4e-6, "nir": 0.7e-6, "swir": 1.0e-6, "mwir": 3.0e-6, "lwir": 8.0e-6}
DEFAULT_LAMBDA = BANDS["visible"]
WIDTH_TOL = 1.15        # the object's width, read this much wider, for what it leaves over the blur
DISC_FLOOR = 0.5        # of a blur: the least defocus disc a width can show (one of half a blur widens a point 12 %)
K_SHARE_ASSUMED = 0.10
EDGE_DIRS = 12          # profiles out from a resolved object's centre, every 30 deg
EDGE_ACROSS = 35.0      # deg: a profile within this of the motion's axis is left out (a smear lengthens it there)
EDGE_STEP = 0.25        # px between samples along a profile
EDGE_MOVING = 0.3       # px a frame: slower, and every direction is used
FWHM_PER_SIGMA = 2.3548
APERTURES = (0.05, 0.10, 0.15, 0.20)    # m: the pupils r/R is given for when none is named
NBOOT = 1000


def disc_max_px(obj_fwhm, blur_fwhm):
    """The widest defocus disc (px) an object of half-maximum width `obj_fwhm` could hide, drawn through a blur of
    `blur_fwhm`: what WIDTH_TOL x its width leaves over the blur in quadrature, at least DISC_FLOOR of a blur."""
    w = max(obj_fwhm, blur_fwhm) * WIDTH_TOL
    return math.sqrt(max(w * w - blur_fwhm * blur_fwhm, (DISC_FLOOR * blur_fwhm) ** 2))


def bound(blur, k, k_share=0.0, band=None, pupil_m=None, focus_m=None, disc=None):
    """The range floor from `blur` (`forensics.point_blur`'s dict), k (px/deg) and its share of error: dict(floor_m --
    focused at infinity --, floor_focused_m -- at `focus_m` if given --, how, disc_px, ...) or dict(floor_m=None, why).
    `disc` (px), the widest defocus disc a resolved object's edge leaves (`edge_disc`), is used in place of the width's."""
    out = dict(floor_m=None, floor_focused_m=None, why=None, disc_px=None, lambda_m=None, pupil_m=pupil_m)
    if blur is None or blur.get("blur_fwhm_px") is None:
        out["why"] = "the blur is not measured: too few points in the scene (a clear sky, open sea)"
        return out
    if blur.get("object_fwhm_px") is None:
        out["why"] = "the object's width is not measured"
        return out
    if blur.get("resolved") is True and disc is None:
        out["why"] = (f"the object is wider than a point ({blur['object_fwhm_px']:.1f} px against "
                      f"{blur['blur_fwhm_px']:.1f}) and its edge is not measured: large, or near and out of focus")
        return out
    if blur.get("resolved") is None and disc is None:
        out["why"] = "the object is clipped on most frames: whether it is wider than a point is not known"
        return out
    if not k:
        out["why"] = "no angular scale: --fov (with --fov-px) or --graticule, or k from `mcdonald slew`"
        return out
    b, w = blur["blur_fwhm_px"], blur["object_fwhm_px"]
    disc = disc_max_px(w, b) if disc is None else max(disc, DISC_FLOOR * b)
    k_lo = k * (1.0 - k_share)                          # the angles at their largest: the bound at its weakest
    rad = lambda px: math.radians(px / k_lo)
    lam = BANDS.get((band or "").lower(), DEFAULT_LAMBDA)
    if pupil_m:
        d = pupil_m / rad(disc)
        how = f"a pupil of {pupil_m * 100:.1f} cm (given) over a disc of at most {disc:.2f} px"
    else:
        d = 1.22 * lam / (rad(b) * rad(disc))
        how = (f"no pupil given: the optics' diffraction at {lam * 1e6:.1f} um ({band or 'no band named, so visible light'})"
               f" puts the pupil at {1.22 * lam / rad(b) * 100:.2f} cm or more, over a disc of at most {disc:.2f} px")
    out.update(floor_m=float(d), disc_px=float(disc), lambda_m=None if pupil_m else lam, how=how,
               blur_rad=rad(b), disc_rad=rad(disc), k_lo=k_lo)
    if focus_m:
        out["floor_focused_m"] = float(1.0 / (1.0 / focus_m + 1.0 / d))
    return out


def disc_profile(t, tc, rho, sigma, bg, depth):
    """A dark disc of radius `rho` seen through a Gaussian blur `sigma`, along a line through its centre (at `tc`): bg less
    depth x the share of the blur's weight that falls inside the disc -- exact, a noncentral chi-square of 2 degrees."""
    from scipy.stats import ncx2
    lam = ((t - tc) / sigma) ** 2
    return bg - depth * ncx2.cdf((rho / sigma) ** 2, 2, np.maximum(lam, 1e-12))


def _axis_off(a, b):
    """How far direction `a` is from the axis through `b` (deg, 0-90)."""
    d = abs((a - b) % 180.0)
    return min(d, 180.0 - d)


def edge_fits(g, x, y, size, dark=True, bad=None, motion_deg=None, black=0.0):
    """One frame's profiles of a resolved object at (x, y), about `size` px across: from its centre (weighted by its
    contrast within 0.6 of its size) out every 360/EDGE_DIRS deg, clockwise from screen-up, leaving out the directions
    within EDGE_ACROSS of `motion_deg` (the axis it moves along) and any that cross `bad`; each fitted with
    `disc_profile`, the samples at or past the clip level left out. [dict(direction_deg, sigma, rho, depth, bg, rms,
    share -- the depth over bg less `black`, the screen's black, capped at 1 --, clipped)]. A bright object is read as
    a dark one in 255 - g (its share then means nothing: see the module's note)."""
    from scipy import ndimage
    from scipy.optimize import curve_fit
    from .forensics import CLIP
    p = np.asarray(g, float) if dark else 255.0 - np.asarray(g, float)
    lo = CLIP[0] if dark else 255.0 - CLIP[1]
    blk = None if black is None else (float(black) if dark else 255.0 - float(black))
    H, W = p.shape
    reach = max(9.0, 1.6 * size)
    R = int(np.ceil(reach)) + 2
    xi, yi = int(round(x)), int(round(y))
    if xi < R or yi < R or xi >= W - R or yi >= H - R:
        return []
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(float)
    rr = np.hypot(xx, yy)
    box = p[yi - R:yi + R + 1, xi - R:xi + R + 1]
    ring = (rr >= reach - 2.5) & (rr <= reach)
    bg0 = float(np.median(box[ring]))
    w = np.clip(bg0 - box, 0, None) * (rr <= max(3.0, 0.6 * size))
    if w.sum() <= 0:
        return []
    cx, cy = xi + (w * xx).sum() / w.sum(), yi + (w * yy).sum() / w.sum()
    t = np.arange(-2.0, reach + 1e-9, EDGE_STEP)
    out = []
    for d in np.arange(0.0, 360.0, 360.0 / EDGE_DIRS):
        if motion_deg is not None and _axis_off(d, motion_deg) < EDGE_ACROSS:
            continue
        a = math.radians(d)
        px, py = cx + t * math.sin(a), cy - t * math.cos(a)
        if bad is not None and bad[np.clip(np.round(py).astype(int), 0, H - 1), np.clip(np.round(px).astype(int), 0, W - 1)].any():
            continue
        v = ndimage.map_coordinates(p, [py, px], order=1)
        keep = v > lo
        if keep.sum() < 8:
            continue
        top = float(np.median(v[-8:]))
        try:
            q, _ = curve_fit(disc_profile, t[keep], v[keep], p0=(0.0, 0.4 * size, 1.2, top, max(top - v.min(), 1.0)),
                             bounds=([-2.0, 0.5, 0.3, 0.0, 0.0], [2.0, reach, reach / 2.0, 300.0, 300.0]), maxfev=20000)
        except (RuntimeError, ValueError):
            continue
        tc, rho, sg, bgf, dep = q
        if sg >= 0.98 * reach / 2.0 or rho >= 0.98 * reach:
            continue                                   # held by the profile's own length: not an edge
        rms = float(np.sqrt(np.mean((v[keep] - disc_profile(t[keep], *q)) ** 2)))
        share = None if blk is None or bgf - blk <= 1.0 else float(min(1.0, dep / (bgf - blk)))
        out.append(dict(direction_deg=float(d), sigma=float(sg), rho=float(rho), depth=float(dep), bg=float(bgf),
                        rms=rms, share=share, clipped=bool((~keep).any())))
    return out


def _motion(track, n, reach=5):
    """The axis the track moves along at frame n (deg clockwise from screen-up), or None where it moves under
    EDGE_MOVING px a frame."""
    a = [m for m in range(n - reach, n) if m in track]
    b = [m for m in range(n + 1, n + reach + 1) if m in track]
    if not a and not b:
        return None
    m0, m1 = (a[0] if a else n), (b[-1] if b else n)
    if m1 == m0:
        return None
    (x0, y0), (x1, y1) = track[m0], track[m1]
    if math.hypot(x1 - x0, y1 - y0) / (m1 - m0) < EDGE_MOVING:
        return None
    return math.degrees(math.atan2(x1 - x0, -(y1 - y0))) % 360.0


def edge_blur(clip, track, masks, rows=None, dark=False, frames=None, seed=5):
    """A resolved object's edge on `frames` of the track's frames, spread over it: each frame's sigma, radius and
    depth share the median of its profiles (`edge_fits`). dict(frames, fits, sigma_px -- the median over frames --,
    sigma_16_84, sigma_95 -- the median's 95th percentile over a bootstrap of the frames --, rho_px, share_16 -- the
    depth share's 16th percentile over frames, the cautious end --, clipped_frames, by_direction, per_frame)."""
    from . import forensics as vf
    from .propose import thing_at
    frames = frames or vf.BLUR_FRAMES
    ns = sorted(n for n in track if getattr(clip, "n0", n) <= n <= getattr(clip, "n1", n))
    if len(ns) > frames:
        ns = [ns[i] for i in np.unique(np.linspace(0, len(ns) - 1, frames).round().astype(int))]
    per, dirs = [], {}
    for n in ns:
        rgb = clip.rgb(n)
        g = vf.grey_of(rgb)
        bad = vf.frame_mask(rgb, masks, rows, n, grow=2)
        ox, oy = track[n]
        _, _, across, _ = thing_at(g, ox, oy, -1 if dark else 1)
        black = 0.0 if dark else 255.0
        fits = edge_fits(g, ox, oy, across, dark, bad, _motion(track, n), black)
        if not fits:
            continue
        for f in fits:
            dirs.setdefault(f["direction_deg"], []).append(f["sigma"])
        sh = [f["share"] for f in fits if f["share"] is not None]
        per.append(dict(frame=n, sigma=float(np.median([f["sigma"] for f in fits])),
                        rho=float(np.median([f["rho"] for f in fits])), share=float(np.median(sh)) if sh else None,
                        profiles=len(fits), clipped=any(f["clipped"] for f in fits), black=black))
    if not per:
        return dict(frames=len(ns), fits=0, sigma_px=None)
    sg = np.array([p["sigma"] for p in per])
    rng = np.random.default_rng(seed)
    boot = np.array([np.median(sg[rng.integers(0, len(sg), len(sg))]) for _ in range(NBOOT)])
    shares = [p["share"] for p in per if p["share"] is not None]
    return dict(frames=len(ns), fits=len(per), sigma_px=float(np.median(sg)),
                sigma_16_84=[float(v) for v in np.percentile(sg, [16, 84])], sigma_95=float(np.percentile(boot, 95)),
                rho_px=float(np.median([p["rho"] for p in per])),
                share_16=float(np.percentile(shares, 16)) if shares else None,
                clipped_frames=int(sum(p["clipped"] for p in per)),
                by_direction={f"{d:.0f}": dict(profiles=len(v), sigma_px=float(np.median(v))) for d, v in sorted(dirs.items())},
                per_frame=per)


def edge_disc(edge, blur_fwhm):
    """The widest defocus disc (px) a resolved object's edge leaves, two ways: assuming nothing of the camera's own
    blur (4 sigma) and assuming it blurs as the scene's points (4 sqrt(sigma^2 - sigma_points^2)), each from sigma's
    95th percentile and divided by the square root of the core's depth share (a small thing far out of focus draws a
    pale disc with a sharp edge), never under half a point."""
    s95, share = edge.get("sigma_95"), edge.get("share_16")
    if s95 is None:
        return None
    f = min(1.0, max(share if share is not None else 1.0, 1e-3))
    s_ref = blur_fwhm / FWHM_PER_SIGMA if blur_fwhm else 0.0
    floor = DISC_FLOOR * blur_fwhm if blur_fwhm else 0.0
    return dict(assuming_nothing=float(max(4.0 * s95 / math.sqrt(f), floor)),
                blur_as_points=float(max(4.0 * math.sqrt(max(s95 ** 2 - s_ref ** 2, 0.0)) / math.sqrt(f), floor)),
                sigma_points=float(s_ref), depth_share=float(f), share_measured=share is not None)


def r_over_R(disc_px, ground_m_per_px, pupils=None):
    """{pupil (m): r/R at least} for a camera focused on the ground at R, its scale `ground_m_per_px` there:
    b = (A / s)(R / r - 1), so r / R >= 1 / (1 + b s / A)."""
    return {A: float(1.0 / (1.0 + disc_px * ground_m_per_px / A)) for A in (pupils or APERTURES)}


def measure(clip, track, k, k_share, band=None, pupil_m=None, focus_m=None, masks=None, rows=None, dark=False,
            k_from="given", ground_m_per_px=None):
    from . import forensics as vf
    if not track:
        return Found("focus", no_power=[("focus", "no track")])
    masks = masks if masks is not None else vf.static_masks(clip)
    blur = vf.point_blur(clip, track, masks, rows, dark)
    edge = disc = None
    res, npw, notes = {}, [], []
    if blur.get("resolved") is True and blur.get("blur_fwhm_px") is not None and not dark:
        npw.append(("focus", f"the object is wider than a point ({blur['object_fwhm_px']:.1f} px against "
                             f"{blur['blur_fwhm_px']:.1f}) and bright: a small bright thing far out of focus draws the "
                             "same sharp-edged disc, so its edge bounds nothing (a dark one is read by its edge: --dark)"))
    elif blur.get("blur_fwhm_px") is not None and dark and (blur.get("resolved") is True or (
            blur.get("resolved") is None and blur.get("object_clipped"))):
        # wider than a point, or clipped at black so that its width is not known: either way its edge is the test
        # (the clipped core is left out of the fit), as on the Middle East Object
        edge = edge_blur(clip, track, masks, rows, dark)
        disc = edge_disc(edge, blur["blur_fwhm_px"])
        if disc:
            res["edge"] = (("wider than a point" if blur.get("resolved") else "clipped at black") +
                           f", its edge blurred {edge['sigma_px']:.2f} px (sigma; 16-84 %: "
                           f"{edge['sigma_16_84'][0]:.2f}-{edge['sigma_16_84'][1]:.2f}, {edge['fits']} frames) against "
                           f"the points' {disc['sigma_points']:.2f}; its core {disc['depth_share']:.0%} of the way to "
                           f"black: a defocus disc of at most {disc['blur_as_points']:.1f} px if the camera blurs as its "
                           f"points, {disc['assuming_nothing']:.1f} px assuming nothing")
            if ground_m_per_px:
                rR = r_over_R(disc["blur_as_points"], ground_m_per_px, [pupil_m] if pupil_m else None)
                rR0 = r_over_R(disc["assuming_nothing"], ground_m_per_px, [pupil_m] if pupil_m else None)
                disc.update(r_over_R=dict(blur_as_points={f"{A * 100:.0f} cm": v for A, v in rR.items()},
                                          assuming_nothing={f"{A * 100:.0f} cm": v for A, v in rR0.items()},
                                          ground_m_per_px=ground_m_per_px))
                res["r/R"] = ("focused on the ground, at least " + ", ".join(
                    f"{rR0[A]:.2f}-{rR[A]:.2f} at a {A * 100:.0f}-cm pupil" for A in rR)
                              + f" (assuming nothing - as the points; ground {ground_m_per_px} m/px)")
            notes.append("A soft edge bounds nothing, and cannot tell a thing out of focus from a soft-edged one (smoke, "
                         "dust). Two biases: the coding softens a moving object more than the still ground (toward "
                         "finding a disc), and turbulence over hot ground blurs the ground's points more than an object "
                         "above it (toward hiding one); the bound assuming nothing is free of both.")
        else:
            npw.append(("focus", "the object is wider than a point and its edge could not be fitted on any frame"))
    b = bound(blur, k, k_share, band, pupil_m, focus_m, disc=disc["blur_as_points"] if disc else None)
    b0 = bound(blur, k, k_share, band, pupil_m, focus_m, disc=disc["assuming_nothing"]) if disc else None
    if blur.get("blur_fwhm_px") is not None:
        res["points"] = (f"a point is {blur['blur_fwhm_px']:.2f} px wide at half its peak ({blur['spots']} spots), the "
                         f"object {blur['object_fwhm_px']:.2f}" if blur.get("object_fwhm_px") is not None else
                         f"a point is {blur['blur_fwhm_px']:.2f} px wide ({blur['spots']} spots); the object not measured")
    if b["floor_m"] is None and disc:
        notes.append(f"No floor on range in metres: {b['why']}.")
    elif b["floor_m"] is None:
        npw.append(("focus", b["why"]))
    else:
        res["range"] = (f"at least {b['floor_m'] / 1000:.2f} km, IF the sensor is focused far: {b['how']}"
                        + (f"; focused at {focus_m / 1000:.1f} km, at least {b['floor_focused_m'] / 1000:.2f} km"
                           if b["floor_focused_m"] else ""))
        notes.append("Assumes the sensor is focused far (at infinity, or at the scene's own points): a camera that "
                     "refocuses on the tracked object makes it sharp at any range. The scene's points are sharp at their "
                     "own range, so the focus is at least that far.")
        if k_from == "assumed":
            notes.append(f"k comes from an assumed field of view: its {k_share:.0%} share of error is in the bound "
                         "(which goes as k squared without a pupil, as k with one).")
    if b0 and b0["floor_m"] is not None:
        res["range"] += f"; {b0['floor_m'] / 1000:.2f} km assuming nothing of the camera's own blur"
    fields = dict(blur=blur, bound=b, k_px_per_deg=k, k_from=k_from, k_share=k_share, band=band)
    if edge is not None:
        fields.update(edge={kk: v for kk, v in edge.items() if kk != "per_frame"}, edge_frames=edge.get("per_frame"),
                      disc=disc, bound_assuming_nothing=b0)
    return Found("focus", res, fields, no_power=npw, notes=notes)


def said(f):
    L = []
    bl, b = f.get("blur") or {}, f.get("bound") or {}
    if bl.get("blur_fwhm_px") is not None:
        L.append(f"a point {bl['blur_fwhm_px']:.2f} px wide at half its peak ({bl['spots']} spots); the object "
                 + (f"{bl['object_fwhm_px']:.2f}" if bl.get("object_fwhm_px") is not None else "not measured")
                 + {True: ", wider than a point", False: ", as sharp as a point", None: ""}[bl.get("resolved")])
    e, dc = f.get("edge") or {}, f.get("disc") or {}
    if dc:
        L.append(f"its edge: sigma {e['sigma_px']:.2f} px ({e['fits']} frames; 95 % at most {e['sigma_95']:.2f}) against "
                 f"the points' {dc['sigma_points']:.2f}, its core {dc['depth_share']:.0%} of the way to black: a defocus "
                 f"disc of at most {dc['blur_as_points']:.1f} px (blurring as the points), {dc['assuming_nothing']:.1f} "
                 "(assuming nothing)")
        rr = dc.get("r_over_R")
        if rr:
            L.append("focused on the ground, r/R at least " + ", ".join(
                f"{rr['assuming_nothing'][A]:.2f}-{rr['blur_as_points'][A]:.2f} at {A}" for A in rr["blur_as_points"]))
    if b.get("floor_m") is not None:
        L.append(f"range at least {b['floor_m'] / 1000:.2f} km if the sensor is focused far ({b['how']})")
    elif b.get("why"):
        L.append(f"no bound: {b['why']}")
    return L


def parse_length(text):
    """'0.1m', '10cm', '100mm', '4in' (or a bare number, metres) -> metres."""
    import re
    t = str(text).strip().lower().replace(" ", "")
    m = re.fullmatch(r"([0-9.]+)(mm|cm|m|in|km)?", t)
    if not m:
        raise ValueError(f"{text!r}: give a length as 0.1m, 10cm, 100mm or 4in")
    return float(m.group(1)) * {"mm": 1e-3, "cm": 1e-2, "m": 1.0, "in": 0.0254, "km": 1e3, None: 1.0}[m.group(2)]


def main():
    from .report import case_option, command_line, into_case
    import argparse
    from . import clip as vclip
    from . import forensics as vf
    from .report import emit, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", required=True, help="CSV with frame and x/y columns: the object")
    ap.add_argument("--fov", type=float, help="the horizontal field of view, deg (an assumption unless a display gives it)")
    ap.add_argument("--fov-px", type=float, help="how many pixels that field spans (default the frame's width)")
    ap.add_argument("--fov-given", action="store_true", help="the field of view is read off the display, not assumed")
    ap.add_argument("--graticule", type=float, help="px per degree, off the camera's own scale")
    ap.add_argument("--k-share", type=float, help="the share by which k may be off (default 0.1 for an assumed field "
                    "of view, 0.01 otherwise)")
    ap.add_argument("--band", choices=sorted(BANDS), help="the sensor's band: its shortest wavelength is used (default: "
                    "visible light, the most cautious)")
    ap.add_argument("--pupil", help="the lens's entrance pupil (aperture) diameter, if a source gives it: 0.1m, 10cm")
    ap.add_argument("--focus", help="the distance the lens is focused at, if known (default infinity): 10km, 5000m")
    ap.add_argument("--dark", action="store_true", help="the object is darker than the scene")
    ap.add_argument("--ground-scale", type=float, metavar="M_PER_PX", help="the ground's metres per pixel beside the "
                    "object (from a ruler in the scene): an object wider than a point then gets r/R, the share of the "
                    "ground's range it is at least at, for the pupil given or 5-20 cm")
    ap.add_argument("--mask-rows", help="y0:y1[:n0:n1],... burned-in captions the static masks miss")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--workdir")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true", help="print the measurement as JSON on stdout")
    case_option(ap)
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        video, tag, _ = vf.resolve(args.video)
        track = vf.read_track(args.track)
        n0, n1 = args.n0 or min(track), args.n1 or max(track)
        clip = vclip.Clip(video, args.workdir, n0, n1)
        track = {n: xy for n, xy in track.items() if clip.n0 <= n <= clip.n1}
        k, k_from = None, "none"
        if args.graticule:
            k, k_from = args.graticule, "graticule"
        elif args.fov:
            k, k_from = (args.fov_px or clip.W) / args.fov, "given" if args.fov_given else "assumed"
        share = args.k_share if args.k_share is not None else (K_SHARE_ASSUMED if k_from == "assumed" else 0.01)
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
        found = measure(clip, track, k, share, args.band, parse_length(args.pupil) if args.pupil else None,
                        parse_length(args.focus) if args.focus else None, rows=vf.parse_rows(args.mask_rows),
                        dark=args.dark, k_from=k_from, ground_m_per_px=args.ground_scale)
        print("\n".join(said(found.fields)))
        for w in found.no_power:
            print(f"no power: {w[1]}")
        if args.case:
            print(f"recorded in {into_case(found, args.case, command_line())}")
    code = vclip.EXIT_NOTHING if found.no_power else 0
    if args.json:
        emit(found.envelope("focus", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
