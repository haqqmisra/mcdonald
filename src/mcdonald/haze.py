"""`mcdonald haze` — the air as a ruler: a dark object pale with haze is far, a strongly dark one near.

  mcdonald haze VIDEO --track CSV (--visibility 20km | --reference N,X,Y,RANGE) [--json]

Koschmieder (1924): a dark object's contrast against the horizon sky behind it falls with range as e^(-sigma d), the
extinction coefficient sigma set by the air (3.912 / V for a meteorological visibility V: the range at which a black
object's contrast falls to 2 %). Painters since Leonardo made distance that way; William K. Hartmann used it on the 1950
McMinnville photographs for the Condon study (Case 46), calibrating sigma on distant hills and checking it on a barn and
a house at known distance, right to a factor of about four. Its intrinsic contrast cannot be darker than black
(C_0 >= -1), so a dark object's apparent contrast |C| <= e^(-sigma d), and **d <= -ln|C| / sigma**: the paler it
looks, the farther it may be; it needs no k and no motion.

C is measured in linear light: the object's darkest core (the median of its darkest pixels) against the sky round it (an
annulus 2-4 times its size out, the object and the overlay left out), both taken back through the BT.709 transfer
function -- video is gamma-encoded, and a grey of 128 is about a quarter of white's light, not half -- on every tracked frame;
the bound is the frame with the palest object's (the cautious end), and the median is reported beside it. sigma is
given (`--visibility`) or calibrated in the same frame on something dark at a known range (`--reference N,X,Y,RANGE`:
its own contrast taken as black's, which makes sigma the smallest it can be, and the bound the largest).

What it assumes, and says on every run: (1) a daytime picture in visible light whose levels follow BT.709 (an
automatic gain multiplies both object and sky, and cancels in C; a tone curve that is not BT.709's -- a camera's log
curve, a display's contrast stretch -- does not); (2) the sky behind the object is the horizon sky that the haze
lights, at the object's elevation; (3) the haze is uniform between camera and object (a layer of it nearer than the
object, or a clearer path above it, moves the bound either way); (4) the object is darker than its sky and no darker
than black (a dark object: a bright one's intrinsic contrast has no ceiling, and gives no bound). In infrared the
object's contrast is a temperature's, not a reflectance's, and there is no bound.

Its error is honestly a factor of about four (Hartmann's check); the report says so, and gives the bound as that.
"""
import math

import numpy as np

from .report import Found

KOSCHMIEDER = 3.912     # -ln(0.02): sigma = this / the visibility
CORE = 0.25             # the darkest share of the object's disc taken as its core
ANNULUS = (2.0, 4.0)    # the sky's ring, in object sizes from its centre
FACTOR = 4.0            # Hartmann's check on objects at known distance: right to about this factor


def linear(v):
    """Video levels (0-255, BT.709) as linear light (0-1)."""
    x = np.clip(np.asarray(v, float) / 255.0, 0.0, 1.0)
    return np.where(x < 0.081, x / 4.5, ((x + 0.099) / 1.099) ** (1 / 0.45))


def contrast(grey, x, y, size, mask=None):
    """(C, core, sky): the object's core against its sky in linear light, C = (core - sky) / sky, or None where the sky
    has too few pixels."""
    g = np.asarray(grey, float)
    H, W = g.shape
    r_obj = max(size / 2.0, 1.5)
    y0, y1 = int(max(0, y - ANNULUS[1] * size - 2)), int(min(H, y + ANNULUS[1] * size + 3))
    x0, x1 = int(max(0, x - ANNULUS[1] * size - 2)), int(min(W, x + ANNULUS[1] * size + 3))
    yy, xx = np.mgrid[y0:y1, x0:x1]
    rr = np.hypot(xx - x, yy - y)
    patch = linear(g[y0:y1, x0:x1])
    ok = np.ones_like(rr, bool) if mask is None else ~mask[y0:y1, x0:x1]
    disc = (rr <= r_obj) & ok
    ring = (rr >= ANNULUS[0] * size) & (rr <= ANNULUS[1] * size) & ok
    if disc.sum() < 3 or ring.sum() < 20:
        return None
    v = np.sort(patch[disc])
    core = float(np.median(v[:max(1, int(math.ceil(CORE * len(v))))]))
    sky = float(np.median(patch[ring]))
    if sky <= 1e-4:
        return None
    return (core - sky) / sky, core, sky


def bound(c, sigma):
    """d_max (m) from a dark object's contrast c (< 0) and sigma (1/m); None for c >= 0 (no bound)."""
    if c is None or c >= 0 or sigma is None or sigma <= 0:
        return None
    return -math.log(min(abs(c), 1.0)) / sigma


def measure(clip, track, size, visibility_m=None, reference=None, masks=None):
    """The stage: C on every tracked frame, sigma from the visibility or the reference, and the bound. A Found."""
    res, npw, notes = {}, [], []
    mask = None if masks is None else (masks["blocks"] | masks["graphics"])
    rows = []
    for n in sorted(track):
        x, y = track[n]
        c = contrast(clip.grey(n), x, y, size, mask)
        if c is not None:
            rows.append(dict(frame=n, c=c[0], core=c[1], sky=c[2]))
    sigma, sigma_from = None, None
    if visibility_m:
        sigma, sigma_from = KOSCHMIEDER / visibility_m, f"a visibility of {visibility_m / 1000:g} km given"
    elif reference:
        n, x, y, r_ref = reference
        cr = contrast(clip.grey(int(n)), x, y, size, mask)
        if cr is None or cr[0] >= 0:
            npw.append(("haze", "the reference is not darker than its sky: it calibrates nothing"))
        else:
            sigma = -math.log(min(abs(cr[0]), 1.0)) / r_ref
            sigma_from = (f"the reference at {r_ref / 1000:g} km (frame {int(n)}, contrast {cr[0]:+.3f}, taken as black's, "
                          f"so sigma is the smallest it can be)")
    fields = dict(rows=rows, sigma_per_m=sigma, sigma_from=sigma_from, size_px=size, bound_m=None, factor=FACTOR)
    if not rows:
        npw.append(("haze", "no tracked frame had sky enough round the object to measure its contrast"))
        return Found("haze", res, fields, no_power=npw)
    cs = np.array([r["c"] for r in rows])
    pale = float(cs.max())
    fields.update(contrast_median=float(np.median(cs)), contrast_palest=pale)
    res["contrast"] = (f"the object's core {np.median(cs):+.3f} of its sky's light (median of {len(rows)} frames; the "
                       f"palest {pale:+.3f}), in linear light")
    if pale >= 0:
        npw.append(("haze", f"the object is not darker than its sky on every frame (the palest {pale:+.3f}): a bright "
                            "object's intrinsic contrast has no ceiling, so haze bounds nothing"))
    elif sigma is None and not npw:
        npw.append(("haze", "no extinction: give --visibility (the reported visibility) or --reference N,X,Y,RANGE "
                            "(something dark at a known range in the frame)"))
    if not npw:
        d = bound(pale, sigma)
        fields.update(bound_m=d, bound_median_m=bound(float(np.median(cs)), sigma))
        res["range"] = (f"at most {d / 1000:.2f} km (from the palest frame; the median frame's {fields['bound_median_m'] / 1000:.2f}) "
                        f"with sigma {sigma * 1000:.3f}/km from {sigma_from} -- good to a factor of about {FACTOR:g} "
                        "(Hartmann's check on objects at known distance), IF the picture's levels are BT.709's, the haze "
                        "is even along the path and the sky behind is the horizon sky")
        notes.append("Assumes a daytime visible-light picture whose levels follow BT.709, haze even between camera and "
                     "object, and a sky behind it lit by the same haze; a dark object. In infrared there is no bound.")
    return Found("haze", res, fields, no_power=npw, notes=notes)


def parse_visibility(text):
    """'20km', '12mi', '12000m', '40000ft' (or a bare number, metres) -> metres. ValueError for one that cannot be read."""
    from .horizon import parse_height
    t = str(text).strip().lower().replace(" ", "")
    try:
        v = (float(t[:-2]) * 1000 if t.endswith("km") else float(t[:-2]) * 1609.344 if t.endswith("mi") else
             parse_height(t))
    except ValueError:
        raise ValueError(f"{text!r}: give a visibility as 20km or 12000m") from None
    if v <= 0:
        raise ValueError(f"{text!r}: a visibility is more than 0")
    return v


def said(f):
    L = []
    if f.get("contrast_median") is not None:
        L.append(f"the object's contrast {f['contrast_median']:+.3f} (median), {f['contrast_palest']:+.3f} at its palest")
    if f.get("bound_m"):
        L.append(f"range at most {f['bound_m'] / 1000:.2f} km, to a factor of about {f['factor']:g} ({f['sigma_from']})")
    return L


def main():
    from .report import case_option, command_line, into_case
    import argparse
    from . import clip as vclip
    from . import forensics as vf
    from .report import emit, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", required=True, help="CSV with frame and x/y columns: the object")
    ap.add_argument("--size", type=float, default=9.0, help="how wide the object is on the screen, px (default 9)")
    ap.add_argument("--visibility", help="the meteorological visibility, if a report gives it: 20km, 12mi, 12000m")
    ap.add_argument("--reference", metavar="N,X,Y,RANGE", help="something dark at a known range in frame N, at (X, Y), its "
                    "range in metres: it calibrates the air in the same frame")
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
        vis = parse_visibility(args.visibility) if args.visibility else None
        ref = tuple(float(v) for v in args.reference.split(",")) if args.reference else None
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
        found = measure(clip, track, args.size, vis, ref, vf.static_masks(clip))
        print("\n".join(said(found.fields)))
        for w in found.no_power:
            print(f"no power: {w[1]}")
        if args.case:
            print(f"recorded in {into_case(found, args.case, command_line())}")
    code = vclip.EXIT_NOTHING if found.no_power else 0
    if args.json:
        emit(found.envelope("haze", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
