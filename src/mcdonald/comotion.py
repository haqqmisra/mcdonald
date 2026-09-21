"""Does the object move *with* the texture around it, or *through* it?

This is a different question from the one `layers` answers, and the difference
matters. `layers` measures rigid, frame-wide motion: how fast the object moves
against a background that moves as one. Here the background is a *field* — a
cloud deck, a sea surface, a dust layer — whose parts move differently, and the
question is local: relative to the texture immediately surrounding it, is the
object carried along or does it cross?

Why it is worth asking. A co-motion answer needs **no field of view and no
range**. Measured in units of the object's own diameter D, it survives any
scaling of the image, and it distinguishes the two hypotheses that a plain rate
cannot:

    carried along      a balloon, debris, a cloud feature, a lens artefact
                       stuck to the display
    moving through     an object with its own motion relative to the air mass

An object that holds station within a drifting cloud field is doing what a
balloon does. One that covers tens of its own diameters relative to the
surrounding cloud is not.

Method, and the three things that make it honest:

- **The same frame pair for both.** The object's displacement and the local
  flow are measured over identical pairs, so an irregular hold cadence — many
  sensor clips repeat frames and catch up later — cancels exactly instead of
  contaminating one term.
- **An annulus, not the whole frame.** The flow is taken from patches in a ring
  around the object, with a disc about the object excluded so its own pixels
  never enter the background estimate. A cloud field shears across the frame,
  so a frame-wide median is not the flow *where the object is*.
- **A radius sweep.** The annulus is arbitrary, so the result is reported
  across several radii. On PR055 the relative displacement moved only from
  1.87 to 2.15 D as the ring went from 300 px to the whole frame — which is
  what made the conclusion safe to state.

What it cannot do. It says nothing in metres: converting D/s to m/s needs the
object's physical size, which needs its angular size and the range. Those are
the same two unknowns as everywhere else in this toolkit, and a scale-free
answer does not escape them — it sidesteps the question they answer.
"""
import math

import numpy as np

from . import forensics as vf
from .report import Found, emit, inputs_of, said_to_stderr


def patch_flow(ga, gb, bad_a, bad_b, centre=None, exclude_px=0.0, tpl=128,
               stride=96, reach=120, zero=4):
    """Shift of each clean patch from frame a to frame b, with a disc about
    the object excluded.

    Built on the same whole-template ZNCC search the rest of the package uses,
    so the estimator is the validated one — no second registration core to
    keep honest. Returns the rows of forensics.SHIFT_COLS."""
    bad_a, bad_b = bad_a.copy(), bad_b.copy()
    if centre is not None and exclude_px > 0:
        yy, xx = np.mgrid[:ga.shape[0], :ga.shape[1]]
        disc = (xx - centre[0]) ** 2 + (yy - centre[1]) ** 2 <= exclude_px ** 2
        bad_a |= disc
        bad_b |= disc
    return vf.shift_field(ga, gb, bad_a, bad_b, tpl=tpl, stride=stride, reach=reach, zero=zero)


def local_flow(field, centre, r_in, r_out, minn=4):
    """Median shift of the patches whose centres lie in an annulus.

    The annulus is the point: near enough to be the flow where the object is,
    far enough that the object's own pixels and its halo are not in it."""
    if not len(field):
        return None
    g = vf.good(field)
    if not len(g):
        return None
    r = np.hypot(g[:, 1] - centre[0], g[:, 2] - centre[1])
    s = (r >= r_in) & (r <= r_out)
    if s.sum() < minn:
        return None
    return dict(dx=float(np.median(g[s, 3])), dy=float(np.median(g[s, 4])),
                n=int(s.sum()),
                sd=float(np.hypot(g[s, 3].std(), g[s, 4].std())))


def series(clip, track, diameter_px, masks=None, rows=None, baseline=5,
           r_in=None, r_out=None, exclude=None, tpl=128, stride=96, reach=120,
           zero=4, step=1):
    """Per-pair object motion, local flow, and the difference between them.

    track is {frame: (x, y)}; diameter_px sets the unit D. Radii default to
    2.8-6 D about the object, the ring that worked on PR055, with the object
    disc excluded out to 2.8 D."""
    D = float(diameter_px)
    r_in = 2.8 * D if r_in is None else r_in
    r_out = 6.0 * D if r_out is None else r_out
    exclude = 2.8 * D if exclude is None else exclude
    masks = masks or {}
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    out = []
    for a in ns[::step]:
        b = a + baseline
        if b not in track or b > clip.n1:
            continue
        ga, gb = clip.grey(a), clip.grey(b)
        bad_a = vf.frame_mask(clip.rgb(a), masks, rows, a) if masks else np.zeros(ga.shape, bool)
        bad_b = vf.frame_mask(clip.rgb(b), masks, rows, b) if masks else np.zeros(gb.shape, bool)
        f = patch_flow(ga, gb, bad_a, bad_b, track[a], exclude, tpl, stride, reach, zero)
        lf = local_flow(f, track[a], r_in, r_out)
        if lf is None:
            continue
        odx = track[b][0] - track[a][0]
        ody = track[b][1] - track[a][1]
        out.append((a, b, float(clip.t(b) - clip.t(a)), odx, ody,
                    lf["dx"], lf["dy"], odx - lf["dx"], ody - lf["dy"], lf["n"], lf["sd"]))
    return np.array(out, float).reshape(-1, 11)


COLS = "a b dt obj_dx obj_dy flow_dx flow_dy rel_dx rel_dy n_patch flow_sd".split()


def integrate(s, diameter_px, t0=None, t1=None):
    """Cumulative displacement over an interval, in object diameters.

    Summing the per-pair differences, not differencing the endpoints: the
    object may be hidden for part of the interval, and a sum over the pairs
    that were measured is the honest total."""
    if not len(s):
        return None
    D = float(diameter_px)
    sel = np.ones(len(s), bool)
    if t0 is not None:
        sel &= s[:, 0] >= t0
    if t1 is not None:
        sel &= s[:, 0] <= t1
    if sel.sum() < 1:
        return None
    w = s[sel]
    dt = float(w[:, 2].sum())
    obj = np.hypot(w[:, 3].sum(), w[:, 4].sum()) / D
    flow = np.hypot(w[:, 5].sum(), w[:, 6].sum()) / D
    rdx, rdy = float(w[:, 7].sum()), float(w[:, 8].sum())
    rel = math.hypot(rdx, rdy) / D
    return dict(n=int(sel.sum()), frames=(int(w[0, 0]), int(w[-1, 1])), dt=dt,
                obj_D=float(obj), flow_D=float(flow), rel_D=float(rel),
                rel_D_per_s=float(rel / dt) if dt else None,
                rel_dir_deg=float(math.degrees(math.atan2(rdx, -rdy)) % 360),
                flow_dir_deg=float(math.degrees(math.atan2(w[:, 5].sum(), -w[:, 6].sum())) % 360))


def radius_sweep(clip, track, diameter_px, radii=(300, 450, 700, None), **kw):
    """The same measurement at several annulus radii.

    The annulus is a choice, so a conclusion that depends on it is not a
    conclusion. Run this before quoting any co-motion result."""
    D = float(diameter_px)
    out = {}
    for r in radii:
        s = series(clip, track, D, r_in=2.8 * D,
                   r_out=(1e9 if r is None else r), **kw)
        tot = integrate(s, D)
        out[r] = tot
    return out


def verdict(rel_D, rel_D_per_s, flow_sd_D=None):
    """Plain words for the result, with the ambiguous middle named as such."""
    if rel_D is None:
        return "NO POWER", "no frame pair gave both an object position and a local flow"
    if rel_D < 1.0:
        return "CARRIED", (f"moves {rel_D:.2f} D relative to the surrounding texture -- "
                           "within its own width, i.e. consistent with being carried by the field")
    if rel_D < 3.0:
        return "INCONCLUSIVE", (f"{rel_D:.2f} D of relative motion: more than nothing, but not "
                                "clearly beyond the field's own shear. Sweep the radius and "
                                "compare against the patch scatter before calling it")
    return "MOVES THROUGH", (f"covers {rel_D:.1f} D relative to the surrounding texture "
                             f"({rel_D_per_s:.2f} D/s) -- not locked to a feature of the field. "
                             "This is scale-free; it is NOT a statement that the motion is anomalous, "
                             "which needs the object's size and range")


# ---- the stage ------------------------------------------------------------------------
def measure(clip, track, diameter_px, masks=None, rows=None, baseline=5, step=1, r_in=None, r_out=None,
            legs=None, sweep=False, out=None, say=print):
    """The co-motion measurement as a stage: the series, its total in object diameters,
    the verdict in words, and -- asked for -- the same over `legs` ((a, b) frame intervals)
    and across annulus radii. Writes <out>_comotion.csv."""
    D = float(diameter_px)
    fields = dict(diameter_px=D, annulus_px=[r_in or 2.8 * D, r_out or 6 * D], baseline_frames=baseline, step=step,
                  pairs=0, verdict="NO POWER", finding=None, whole=None, legs=[], sweep=None,
                  local_flow_px=None, flow_near_zero_zone=False)
    s = series(clip, track, D, masks=masks, rows=rows, baseline=baseline, r_in=r_in, r_out=r_out, step=step)
    whole = integrate(s, D)
    if not whole:
        v, why = verdict(None, None)
        fields["finding"] = why
        return Found("comotion", fields=fields, no_power=[("comotion", "no pair gave both an object "
                                                                       "position and a local flow")])
    files = []
    if out:
        import csv
        with open(f"{out}_comotion.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(COLS)
            for r in s:
                w.writerow([int(r[0]), int(r[1])] + [round(v, 4) for v in r[2:9]] + [int(r[9]), round(r[10], 3)])
        files.append(f"{out}_comotion.csv")
        say(f"wrote {out}_comotion.csv: {len(s)} pairs")

    flow_px = float(np.median(np.hypot(s[:, 5], s[:, 6])))
    v, why = verdict(whole["rel_D"], whole["rel_D_per_s"])
    fields.update(pairs=len(s), verdict=v, finding=why, whole=whole, local_flow_px=flow_px, flow_near_zero_zone=flow_px < 8,
                  legs=[t for t in (integrate(s, D, a, b) for a, b in (legs or [(None, None)])) if t])
    if sweep:
        fields["sweep"] = {("whole frame" if r is None else f"{r} px"): tot for r, tot in
                           radius_sweep(clip, track, D, masks=masks, rows=rows, baseline=baseline,
                                        step=max(step, 2)).items() if tot}
    result = dict(verdict=v, rel_D=round(whole["rel_D"], 2), rel_D_per_s=round(whole["rel_D_per_s"], 2),
                  finding=why, pairs=whole["n"])
    notes = []
    if fields["flow_near_zero_zone"]:
        notes.append(f"Co-motion: the local flow is only {flow_px:.1f} px over the baseline, close to the zero-shift "
                     "exclusion the registration uses, so the flow term is unreliable; raise the baseline.")
    return Found("comotion", result, fields, files=files, notes=notes)


def said(fields):
    """What `mcdonald comotion` prints of a measurement, from its fields."""
    L = []
    if fields["flow_near_zero_zone"]:
        L.append(f"  NOTE: the local flow is only {fields['local_flow_px']:.1f} px over the baseline, close to the "
                 "zero-shift exclusion the registration uses. Raise --baseline until the field has "
                 "moved well clear of it, or the flow term is unreliable.")
    L += ["\ndirections are clockwise from screen-up (up 0, right 90, down 180); "
          "add a north-pointer reading to get a bearing",
          "\n| interval | dt | object | local field | object - field | dir |", "|---|---|---|---|---|---|"]
    for tot in fields["legs"]:
        L.append(f"| {tot['frames'][0]}-{tot['frames'][1]} | {tot['dt']:.2f} s | {tot['obj_D']:.2f} D | "
                 f"{tot['flow_D']:.2f} D | **{tot['rel_D']:.2f} D -> {tot['rel_D_per_s']:.2f} D/s** | "
                 f"{tot['rel_dir_deg']:.0f} deg |")
    whole = fields["whole"]
    L.append(f"\n{fields['verdict']}: {fields['finding']}.")
    L.append(f"the field itself moves {whole['flow_D']:.2f} D in {whole['dt']:.2f} s, "
             f"toward {whole['flow_dir_deg']:.0f} deg")
    if fields["sweep"] is not None:
        L.append("\nradius sweep (the annulus is a choice; a result that depends on it is not one)")
        for r, tot in fields["sweep"].items():
            L.append(f"  r_out {r:>12}: relative {tot['rel_D']:.2f} D  ({tot['n']} pairs)")
    L.append("\nThis is scale-free and says nothing in metres: D/s becomes m/s only through the "
             "object's physical size, which needs its angular size and the range.")
    return L


# ---- CLI ----------------------------------------------------------------------------
def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", required=True, help="CSV with frame and x/y columns")
    ap.add_argument("--diameter", type=float, required=True,
                    help="object diameter in px -- the unit D everything is reported in")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--baseline", type=int, default=5, help="frames between the pair (default 5)")
    ap.add_argument("--step", type=int, default=1, help="use every step-th pair")
    ap.add_argument("--r-in", type=float, help="inner annulus radius px (default 2.8 D)")
    ap.add_argument("--r-out", type=float, help="outer annulus radius px (default 6 D)")
    ap.add_argument("--legs", help="a:b,... frame intervals to summarise separately")
    ap.add_argument("--sweep", action="store_true", help="repeat at several annulus radii")
    ap.add_argument("--mask-rows")
    ap.add_argument("--out", metavar="DIR", help="case directory for results "
                    "(default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        found, clip = _main(args)
    code = 0 if found.fields["pairs"] else vf.EXIT_NOTHING
    if args.json:
        emit(found.envelope("comotion", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.fields["finding"]))
    return code


def _main(args):
    video, tag, _ = vf.resolve(args.video)
    clip = vf.Clip(video, args.workdir, args.n0, args.n1)
    out = vf.out_prefix(args.out, tag)
    track = vf.read_track(args.track)
    masks = vf.static_masks(clip)
    rows = vf.parse_rows(args.mask_rows)
    D = args.diameter
    print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
    print(f"object diameter D = {D:g} px; annulus {args.r_in or 2.8 * D:.0f}-{args.r_out or 6 * D:.0f} px "
          f"({(args.r_in or 2.8 * D) / D:.1f}-{(args.r_out or 6 * D) / D:.1f} D), baseline {args.baseline} frames")
    legs = None
    if args.legs:
        legs = [tuple(float(x) if x else None for x in p.split(":")) for p in args.legs.split(",")]
    found = measure(clip, track, D, masks, rows, args.baseline, args.step, args.r_in, args.r_out, legs, args.sweep, out)
    if not found.fields["pairs"]:
        print("no pair yielded both an object position and a local flow: NO POWER")
    else:
        print("\n".join(said(found.fields)))
    return found, clip


if __name__ == "__main__":
    raise SystemExit(main())
