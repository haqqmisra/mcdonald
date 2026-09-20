"""`mcdonald kinematics` — the reduction, from a track and whatever is known.

Deliberately separate from kinematics.py, which stays import-only so the
equations can be used without a command line in the way."""
import argparse

from . import forensics as vf
from . import kinematics as kin
from . import scale as sc


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", required=True, help="CSV with frame and x/y columns")
    ap.add_argument("--t0", type=float, help="fit window start, s")
    ap.add_argument("--t1", type=float, help="fit window end, s")
    ap.add_argument("--n0", type=int, help="fit window start frame")
    ap.add_argument("--n1", type=int, help="fit window end frame")
    ap.add_argument("--fov", type=float, help="assumed horizontal FOV, deg (an ASSUMPTION)")
    ap.add_argument("--graticule", type=float, help="px per labelled degree (a MEASUREMENT)")
    ap.add_argument("--alpha", type=float, default=0.0, help="object's field angle, deg")
    ap.add_argument("--range", type=float, dest="range_m", help="range to the object, m")
    ap.add_argument("--range-rate", type=float, help="range rate, m/s, if a sensor reported one")
    ap.add_argument("--theta", type=float, help="aspect angle, deg (default 90 = lower bound)")
    ap.add_argument("--size-px", type=float, help="object size px, for body-lengths/s")
    ap.add_argument("--ref-px", type=float, help="in-frame reference length, px")
    ap.add_argument("--ref-m", type=float, help="in-frame reference true length, m")
    ap.add_argument("--range-ratio", type=float, default=1.0,
                    help="R_object / R_reference (default 1 = the object is at the reference's range)")
    ap.add_argument("--ladder", action="store_true",
                    help="with no k, print what each candidate FOV would imply")
    args = ap.parse_args()

    video, tag, _ = vf.resolve(args.video)
    info = vf.probe(video)
    fps, W = float(info["fps"]), info["width"]
    track = vf.read_track(args.track)
    fit = kin.fit_v_px(track, fps, args.t0, args.t1, args.n0, args.n1)
    if not fit:
        raise SystemExit("track too short to fit a rate (need at least 3 points in the window)")

    if args.graticule:
        scale = kin.AngularScale.from_graticule(args.graticule, args.alpha)
    elif args.fov:
        scale = kin.AngularScale.from_fov(W, args.fov, args.alpha)
    else:
        scale = kin.AngularScale.unknown("no graticule and no FOV given")

    ref = dict(px=args.ref_px, len_m=args.ref_m, range_ratio=args.range_ratio,
               what="in-frame reference") if (args.ref_px and args.ref_m) else None
    red = kin.Reduction(fit["v_px"], fps, scale, R_m=args.range_m,
                        range_rate=args.range_rate, theta_deg=args.theta,
                        size_px=args.size_px, ref=ref, tag=tag, fit=fit)

    print(f"{video.name}: {W}x{info['height']}, {info['fps']} fps")
    print(f"track: {fit['n']} points kept of {fit['n_in']} "
          f"({fit['n_clipped']} sigma-clipped as off the line) over "
          f"t = {fit['t0']:.2f}-{fit['t1']:.2f} s, span {fit['span_px']:.0f} px")
    print(f"       residual {fit['resid_rms']:.2f} px = {fit['resid_frac']:.1%} of the span"
          + ("" if fit["uniform"] else "   <-- NOT a uniform straight-line motion"))
    print(f"direction {fit['direction_deg']:.0f} deg (clockwise from screen-up)")
    print()
    print(red.report())
    if args.ladder and not scale.known:
        print("\nwhat each candidate field of view would imply "
              "(the spread is the point; do not pick one):")
        for r in sc.fov_ladder(fit["v_px"], W, (3, 10, 30, 54)):
            sp = "  ".join(f"{R / 1000:g} km: {v:6.0f} m/s" for R, v in r["speeds"].items())
            print(f"  FOV {r['fov_deg']:5.1f} deg -> k {r['k']:8.0f} px/rad, "
                  f"omega {r['omega']:.4f} rad/s | {sp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
