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

What it cannot do: bound the range of a thing wider than its points (it may be large, or near and out of focus: the
disc's own shape, flat-topped where a point is not, is the test for the second, and is not made here yet); or work
with no points in the scene (a clear sky, open sea): no blur, no bound.
"""
import math

from .report import Found

BANDS = {"visible": 0.4e-6, "nir": 0.7e-6, "swir": 1.0e-6, "mwir": 3.0e-6, "lwir": 8.0e-6}
DEFAULT_LAMBDA = BANDS["visible"]
WIDTH_TOL = 1.15        # the object's width, read this much wider, for what it leaves over the blur
DISC_FLOOR = 0.5        # of a blur: the least defocus disc a width can show (one of half a blur widens a point 12 %)
K_SHARE_ASSUMED = 0.10


def disc_max_px(obj_fwhm, blur_fwhm):
    """The widest defocus disc (px) an object of half-maximum width `obj_fwhm` could hide, drawn through a blur of
    `blur_fwhm`: what WIDTH_TOL x its width leaves over the blur in quadrature, at least DISC_FLOOR of a blur."""
    w = max(obj_fwhm, blur_fwhm) * WIDTH_TOL
    return math.sqrt(max(w * w - blur_fwhm * blur_fwhm, (DISC_FLOOR * blur_fwhm) ** 2))


def bound(blur, k, k_share=0.0, band=None, pupil_m=None, focus_m=None):
    """The range floor from `blur` (`forensics.point_blur`'s dict), k (px/deg) and its share of error: dict(floor_m --
    focused at infinity --, floor_focused_m -- at `focus_m` if given --, how, disc_px, ...) or dict(floor_m=None, why)."""
    out = dict(floor_m=None, floor_focused_m=None, why=None, disc_px=None, lambda_m=None, pupil_m=pupil_m)
    if blur is None or blur.get("blur_fwhm_px") is None:
        out["why"] = "the blur is not measured: too few points in the scene (a clear sky, open sea)"
        return out
    if blur.get("object_fwhm_px") is None:
        out["why"] = "the object's width is not measured"
        return out
    if blur.get("resolved") is True:
        out["why"] = (f"the object is wider than a point ({blur['object_fwhm_px']:.1f} px against "
                      f"{blur['blur_fwhm_px']:.1f}): large, or near and out of focus, and its sharpness bounds nothing")
        return out
    if blur.get("resolved") is None:
        out["why"] = "the object is clipped on most frames: whether it is wider than a point is not known"
        return out
    if not k:
        out["why"] = "no angular scale: --fov (with --fov-px) or --graticule, or k from `mcdonald slew`"
        return out
    b, w = blur["blur_fwhm_px"], blur["object_fwhm_px"]
    disc = disc_max_px(w, b)
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


def measure(clip, track, k, k_share, band=None, pupil_m=None, focus_m=None, masks=None, rows=None, dark=False,
            k_from="given"):
    from . import forensics as vf
    if not track:
        return Found("focus", no_power=[("focus", "no track")])
    masks = masks if masks is not None else vf.static_masks(clip)
    blur = vf.point_blur(clip, track, masks, rows, dark)
    b = bound(blur, k, k_share, band, pupil_m, focus_m)
    res, npw, notes = {}, [], []
    if blur.get("blur_fwhm_px") is not None:
        res["points"] = (f"a point is {blur['blur_fwhm_px']:.2f} px wide at half its peak ({blur['spots']} spots), the "
                         f"object {blur['object_fwhm_px']:.2f}" if blur.get("object_fwhm_px") is not None else
                         f"a point is {blur['blur_fwhm_px']:.2f} px wide ({blur['spots']} spots); the object not measured")
    if b["floor_m"] is None:
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
    fields = dict(blur=blur, bound=b, k_px_per_deg=k, k_from=k_from, k_share=k_share, band=band)
    return Found("focus", res, fields, no_power=npw, notes=notes)


def said(f):
    L = []
    bl, b = f.get("blur") or {}, f.get("bound") or {}
    if bl.get("blur_fwhm_px") is not None:
        L.append(f"a point {bl['blur_fwhm_px']:.2f} px wide at half its peak ({bl['spots']} spots); the object "
                 + (f"{bl['object_fwhm_px']:.2f}" if bl.get("object_fwhm_px") is not None else "not measured")
                 + {True: ", wider than a point", False: ", as sharp as a point", None: ""}[bl.get("resolved")])
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
    ap.add_argument("--mask-rows", help="y0:y1[:n0:n1],... burned-in captions the static masks miss")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--workdir")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true", help="print the measurement as JSON on stdout")
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
                        dark=args.dark, k_from=k_from)
        print("\n".join(said(found.fields)))
        for w in found.no_power:
            print(f"no power: {w[1]}")
    code = vclip.EXIT_NOTHING if found.no_power else 0
    if args.json:
        emit(found.envelope("focus", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
