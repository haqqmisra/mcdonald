"""`mcdonald run` — one clip through every stage, into one report.

The stages, in the order their dependencies demand:

    0 ingest      what is this file? exact rational fps, container, provenance
    1 survey      cadence (repeats, catch-up steps), transients, symbology map
    2 track       where is the object? (supplied, or attempted)
    3 verify      is the track on the object in EVERY frame?  <- the gate
    4 layers      how does the background move, in how many layers?
    5 scale       what bounds k? graticule, reference object, zoom chain
    6 kinematics  what does the motion permit? bounds, not a speed
    7 integrity   altered? object added? + the synthetic-insert self-test
    8 report      the case report

**Stage 3 is a gate, and it is deliberate.** Nothing downstream of it runs
until a track sheet exists, because every measurement after it inherits the
assumption that the track is on the object. On the clip this toolkit was
developed against, the first automatic tracker spent seven frames locked to a
cloud feature 100 px away and produced a clean, wrong rate. `--i-looked` is
how you assert you have looked at the sheet; there is no flag that skips
making it.

The driver is deliberately thin. Each stage is the same code the standalone
subcommand runs, so a result from `mcdonald run` and one from
`mcdonald layers` are the same number, and a stage that fails or has nothing
to work with is recorded as such rather than crashing the run.
"""
import sys
import traceback

import numpy as np

from . import catalog, forensics as vf
from . import comotion as com
from . import kinematics as kin
from . import scale as sc
from . import symbology as sym
from .report import Case

STAGES = ["ingest", "survey", "track", "verify", "layers", "scale",
          "kinematics", "integrity", "report"]


def _fail(case, name, e, verbose=False):
    if verbose:
        traceback.print_exc()
    case.add(name, no_power=[(name, f"stage raised {type(e).__name__}: {e}")])
    print(f"  ! {name} failed: {type(e).__name__}: {e}", file=sys.stderr)


def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", help="CSV with frame and x/y columns. Without one, the "
                                    "object stages are skipped and say so.")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--out", metavar="DIR", help="case directory (default: ./<tag>)")
    ap.add_argument("--only", help="run only these stages, comma separated")
    ap.add_argument("--skip", help="skip these stages, comma separated")
    ap.add_argument("--i-looked", action="store_true",
                    help="assert you have looked at the track sheet from a previous run. "
                         "Without it the stages that depend on the track being right are "
                         "marked provisional in the report.")
    ap.add_argument("--diameter", type=float, help="object diameter px, for co-motion (D)")
    ap.add_argument("--fov", type=float, help="assumed horizontal field of view, deg")
    ap.add_argument("--graticule", type=float, help="px per labelled degree, if the sensor draws one")
    ap.add_argument("--range", type=float, dest="range_m", help="object range, m, if sourced")
    ap.add_argument("--ref-px", type=float, help="in-frame reference length, px")
    ap.add_argument("--ref-m", type=float, help="in-frame reference true length, m")
    ap.add_argument("--size-px", type=float, help="object size in px, for body-lengths/s")
    ap.add_argument("--mask-rows")
    ap.add_argument("--procs", type=int, default=10)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    only = set(args.only.split(",")) if args.only else set(STAGES)
    skip = set(args.skip.split(",")) if args.skip else set()
    want = [s for s in STAGES if s in only and s not in skip]

    # ---- 0 ingest -------------------------------------------------------------------
    video, tag, rec = vf.resolve(args.video)
    clip = vf.Clip(video, args.workdir, args.n0, args.n1)
    out = vf.out_prefix(args.out, tag)
    cat = catalog.active()
    record = None
    if rec:
        record = dict(title=rec.get("title"), release=rec.get("release"),
                      disclosure=cat.disclosure(rec), catalog=cat.name)
    case = Case(tag, video, clip, record)
    print(f"{video.name}: {clip.W}x{clip.H}, {clip.info['fps']} fps, frames {clip.n0}-{clip.n1}")
    print(f"case directory: {out.parent}")
    case.add("ingest", dict(container=clip.info["format"].get("format_name", "?"),
                            fps_exact=str(clip.info["fps"]),
                            frames=f"{clip.n0}-{clip.n1}"),
             command=f"mcdonald run {args.video}" + (f" --track {args.track}" if args.track else ""))

    masks = vf.static_masks(clip)
    rows = vf.parse_rows(args.mask_rows)
    track = vf.read_track(args.track) if args.track else None

    # ---- 1 survey -------------------------------------------------------------------
    series = None
    if "survey" in want:
        print("[survey] cadence and transients")
        try:
            series = vf.frame_series(clip, masks, procs=args.procs)
            reps = vf.repeats(series)
            trans = vf.transients(series)
            bore = sym.reticle_from_chroma(clip.rgb(clip.n0))
            res = dict(repeated_frames=len(reps), transients=len(trans),
                       masked_blocks=f"{masks['blocks'].mean():.1%}",
                       masked_graphics=f"{masks['graphics'].mean():.1%}",
                       boresight=f"({bore[0]:.1f}, {bore[1]:.1f})" if bore else "not found by chroma")
            npw = []
            if not reps:
                npw.append(("cadence", "no repeated frames, so the cadence test on the object "
                                       "has nothing to work with"))
            if not trans:
                npw.append(("transient", "no contrast transient in the clip"))
            case.add("survey", res, no_power=npw)
            if reps:
                case.note(f"{len(reps)} repeated frames: never quote a per-frame displacement "
                          "on this clip; average over at least a second of wall-clock time.")
            print(f"  repeats {len(reps)}, transients {len(trans)}")
        except Exception as e:
            _fail(case, "survey", e, args.verbose)

    # ---- 2/3 track and the gate -----------------------------------------------------
    if "track" in want:
        if track:
            case.add("track", dict(source=args.track, frames=len(track),
                                   span=f"{min(track)}-{max(track)}"))
            print(f"  track: {len(track)} frames from {args.track}")
        else:
            case.add("track", no_power=[("track", "no track supplied, so every object "
                                                  "measurement is skipped")],
                     needs=["a track: run `mcdonald layers VIDEO --auto-track` or mark the "
                            "object by hand, then pass --track"])
            print("  no track supplied: object stages will be skipped")

    if "verify" in want and track:
        print("[verify] track sheet -- look at it before believing anything below")
        try:
            from . import tracksheet
            argv = sys.argv
            sys.argv = ["tracksheet", str(video), "--track", args.track,
                        "--out", str(out.parent)]
            if args.n0:
                sys.argv += ["--n0", str(args.n0)]
            if args.n1:
                sys.argv += ["--n1", str(args.n1)]
            try:
                tracksheet.main()
            finally:
                sys.argv = argv
            case.add("verify", dict(sheet=f"{out}_all_frames.jpg",
                                    reviewed="yes (--i-looked)" if args.i_looked else "NOT CONFIRMED"),
                     command=f"mcdonald tracksheet {args.video} --track {args.track}",
                     needs=[] if args.i_looked else
                     ["confirmation that the track sheet was examined: every number below "
                      "assumes the track is on the object in every frame"])
            if not args.i_looked:
                case.note("The track sheet was generated but not confirmed as examined, so the "
                          "object measurements below are **provisional**.")
        except Exception as e:
            _fail(case, "verify", e, args.verbose)

    # ---- 4 layers -------------------------------------------------------------------
    lay_rates = {}
    if "layers" in want:
        print("[layers] background, layer by layer")
        try:
            a, b = clip.n0, min(clip.n0 + 5, clip.n1)
            ga, gb = clip.grey(a), clip.grey(b)
            bad_a = vf.frame_mask(clip.rgb(a), masks, rows, a)
            bad_b = vf.frame_mask(clip.rgb(b), masks, rows, b)
            field, still = vf.shift_field_auto(ga, gb, bad_a, bad_b)
            f = vf.good(field)
            lay = vf.layers_of(f) if len(f) else {"groups": 0}
            res = {"motion groups": lay.get("groups", 0)}
            if still:
                res["scene held still"] = ("yes -- zero shift was allowed, so a static "
                                           "pattern could be locking these estimates; read "
                                           "them as 'no more than'")
            for name in ("striated", "isotropic"):
                v = lay.get(name)
                if v is not None:
                    rate = float(np.hypot(*v[0])) * clip.fps / max(b - a, 1)
                    lay_rates[name] = rate
                    res[f"{name} layer"] = f"{rate:.0f} px/s ({v[1]} templates)"
            npw = []
            if lay.get("groups", 0) == 0:
                npw.append(("layers", "no consensus background motion: the scene is held still "
                                      "or has too little texture"))
            if still:
                npw.append(("layers", "the scene is held still on screen, so a background rate "
                                      "here is an upper limit, not a measurement"))
            case.add("layers", res, no_power=npw,
                     command=f"mcdonald layers {args.video}" +
                             (f" --track {args.track}" if args.track else " --auto-track"))
            print(f"  motion groups {lay.get('groups', 0)}; " +
                  ", ".join(f"{k} {v:.0f} px/s" for k, v in lay_rates.items()))
            if len(lay_rates) > 1:
                case.note("More than one background layer: any rate quoted here must name "
                          "which layer it is against.")
        except Exception as e:
            _fail(case, "layers", e, args.verbose)

    # ---- 5 scale --------------------------------------------------------------------
    scale = kin.AngularScale.unknown("no graticule, no reference object, no FOV supplied")
    if "scale" in want:
        print("[scale] what bounds k")
        try:
            res, needs = {}, []
            if args.graticule:
                scale = kin.AngularScale.from_graticule(args.graticule)
                res["k"] = f"{scale.k:.1f} px/rad (graticule, measured)"
            elif args.fov:
                scale = kin.AngularScale.from_fov(clip.W, args.fov)
                res["k"] = f"{scale.k:.1f} px/rad (from an ASSUMED FOV of {args.fov} deg)"
            else:
                needs.append("an angular scale k: a graticule reading, a known-size object in "
                             "frame, or a sourced field of view")
            bb = sym.bracket_box(clip.rgb(clip.n0))
            if bb:
                res["corner brackets"] = (f"{bb[0]:.0f} x {bb[1]:.0f} px -- these mark the NEXT "
                                          "field of view and must not be read as a zoom ratio")
            if args.ref_px and args.ref_m:
                res["reference object"] = f"{args.ref_m:g} m over {args.ref_px:g} px"
            if not args.graticule and not args.fov:
                ladder = sc.fov_ladder(1.0, clip.W, (3, 10, 30, 54))
                res["k if the FOV were"] = ", ".join(
                    f"{r['fov_deg']:g} deg -> {r['k']:.0f}" for r in ladder)
            case.add("scale", res, needs=needs,
                     no_power=[] if scale.known else
                     [("scale", "k is unconstrained, so no pixel rate converts to an angular rate")])
            print(f"  {res.get('k', 'k UNKNOWN')}")
        except Exception as e:
            _fail(case, "scale", e, args.verbose)

    # ---- 6 kinematics ---------------------------------------------------------------
    if "kinematics" in want and track:
        print("[kinematics] what the motion permits")
        try:
            fit = kin.fit_v_px(track, clip.fps)
            if not fit:
                case.add("kinematics", no_power=[("kinematics", "track too short to fit a rate")])
            else:
                ref = None
                if args.ref_px and args.ref_m:
                    ref = dict(px=args.ref_px, len_m=args.ref_m, what="in-frame reference")
                red = kin.Reduction(fit["v_px"], clip.fps, scale, R_m=args.range_m,
                                    size_px=args.size_px, ref=ref, tag=tag, fit=fit)
                res = dict(v_px=f"{fit['v_px']:.1f} px/s",
                           direction=f"{fit['direction_deg']:.0f} deg (clockwise from screen-up)",
                           fit_residual=f"{fit['resid_rms']:.2f} px = {fit['resid_frac']:.1%} of span, "
                                        f"{fit['n']}/{fit['n_in']} points kept",
                           uniform_motion="yes" if fit["uniform"] else
                                          "NO -- v_px does not describe this motion")
                if red.omega is not None:
                    res["omega"] = f"{red.omega:.4f} rad/s"
                if red.speed() is not None:
                    res["relative speed"] = (f"{red.speed():.0f} m/s (Mach {red.speed() / kin.A_SOUND:.2f}) "
                                             "-- RELATIVE, includes the platform's own motion")
                caveat = "" if fit["uniform"] else \
                    "  [NOT QUOTABLE: the underlying fit is not uniform straight-line motion]"
                bl = kin.body_lengths_per_s(fit["v_px"], args.size_px) if args.size_px else None
                if bl:
                    res["body-lengths/s"] = f"{bl:.1f} /s (needs no k, no R, no FOV)" + caveat
                if ref:
                    res["scale-bar speed"] = (
                        f"{kin.scale_bar_speed(fit['v_px'], args.ref_px, args.ref_m):.1f} m/s "
                        "at the reference's range -- a ceiling, not a speed" + caveat)
                if not fit["uniform"]:
                    case.note("The track is not uniform straight-line motion, so every speed "
                              "derived from a single v_px above is marked not quotable. Either "
                              "fit a window in which the motion IS uniform, or measure the rate "
                              "against the background with `mcdonald layers`.")
                case.add("kinematics", res, needs=red.missing,
                         no_power=[] if red.speed() is not None else
                         [("speed", "missing " + ", ".join(red.missing))])
                print("  " + red.report().replace("\n", "\n  "))
                case.note("Reported rates are fitted against wall-clock time, never per-frame "
                          "differences.")
        except Exception as e:
            _fail(case, "kinematics", e, args.verbose)
    elif "kinematics" in want:
        case.add("kinematics", no_power=[("kinematics", "no track, so no image-plane rate")])

    # ---- co-motion (optional, needs D) ----------------------------------------------
    if track and args.diameter:
        print("[comotion] with the texture, or through it?")
        try:
            s = com.series(clip, track, args.diameter, masks=masks, rows=rows, step=2)
            tot = com.integrate(s, args.diameter)
            if tot:
                v, why = com.verdict(tot["rel_D"], tot["rel_D_per_s"])
                case.add("comotion", dict(verdict=v, rel_D=round(tot["rel_D"], 2),
                                          rel_D_per_s=round(tot["rel_D_per_s"], 2),
                                          finding=why, pairs=tot["n"]),
                         command=f"mcdonald comotion {args.video} --track {args.track} "
                                 f"--diameter {args.diameter:g}")
                print(f"  {v}: {tot['rel_D']:.1f} D relative ({tot['rel_D_per_s']:.2f} D/s)")
            else:
                case.add("comotion", no_power=[("comotion", "no pair gave both an object "
                                                            "position and a local flow")])
        except Exception as e:
            _fail(case, "comotion", e, args.verbose)

    # ---- 7 integrity ----------------------------------------------------------------
    if "integrity" in want:
        print("[integrity] altered? object added?  (the long one)")
        try:
            from . import integrity as integ
            argv = sys.argv
            sys.argv = ["integrity", str(video), "--out", str(out.parent)]
            if args.track:
                sys.argv += ["--track", args.track]
            if args.n0:
                sys.argv += ["--n0", str(args.n0)]
            if args.n1:
                sys.argv += ["--n1", str(args.n1)]
            if args.mask_rows:
                sys.argv += ["--mask-rows", args.mask_rows]
            try:
                integ.main()
            finally:
                sys.argv = argv
            import json as _json
            R = _json.load(open(f"{out}_integrity_report.json"))
            verdicts = {k: v["verdict"] for k, v in R.get("object", {}).items()}
            npw = [(k, v["finding"]) for k, v in R.get("object", {}).items()
                   if v["verdict"] in ("NO POWER", "INCONCLUSIVE")]
            case.add("integrity", dict(object_verdicts=verdicts,
                                       report=f"{out}_integrity_report.md"),
                     no_power=npw,
                     command=f"mcdonald integrity {args.video}" +
                             (f" --track {args.track}" if args.track else ""))
        except Exception as e:
            _fail(case, "integrity", e, args.verbose)

    # ---- 8 report -------------------------------------------------------------------
    if "report" in want:
        if lay_rates:
            case.stages.setdefault("layers", {"result": {}, "no_power": [], "needs": []})
            case.stages["layers"]["result"]["rates"] = lay_rates
        path = case.write(str(out))
        print(f"\n{'=' * 70}\n{case.bottom_line()}\n{'=' * 70}\n\nfull report: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
