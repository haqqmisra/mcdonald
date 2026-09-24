"""`mcdonald kinematics` — the reduction, from a track and whatever is known.

Deliberately separate from kinematics.py, which stays import-only so the
equations can be used without a command line in the way."""
import argparse

from . import forensics as vf
from . import kinematics as kin
from . import scale as sc
from . import stages
from .report import emit, inputs_of, said_to_stderr


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
    ap.add_argument("--ground-speed", metavar="SPEED[,BEARING]",
                    help="a speed given for the object along the ground (a report's 480mph; or 215m/s, 250kt, 400km/h), "
                         "and the true bearing it moved toward if known: with --own-ship, the parallax ladder -- which "
                         "heights and speeds of its own give it")
    ap.add_argument("--own-ship", metavar="SPEED[,HEADING[,ALT]]",
                    help="the aircraft's speed (180kt; 250kias@7000ft is indicated airspeed at an altitude, turned into true "
                         "airspeed in ISA with the band a day 15 C colder or warmer gives), its heading and its altitude")
    ap.add_argument("--ladder", action="store_true",
                    help="with no k, print what each candidate FOV would imply")
    ap.add_argument("--json", action="store_true",
                    help="print the reduction as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        found = _main(args)
    if args.json:
        emit(found.envelope("kinematics", inputs_of(args), said=lines))
    return 0


def _main(args):
    video, tag, _ = vf.resolve(args.video)
    info = vf.probe(video)
    fps, W = float(info["fps"]), info["width"]
    track = vf.read_track(args.track)

    if args.graticule:
        scale = kin.AngularScale.from_graticule(args.graticule, args.alpha)
    elif args.fov:
        scale = kin.AngularScale.from_fov(W, args.fov, args.alpha)
    else:
        scale = kin.AngularScale.unknown("no graticule and no FOV given")
    ref = dict(px=args.ref_px, len_m=args.ref_m, range_ratio=args.range_ratio,
               what="in-frame reference") if (args.ref_px and args.ref_m) else None
    found = stages.kinematics(track, fps, W, tag, scale, args.t0, args.t1, args.n0, args.n1, args.range_m,
                              args.range_rate, args.theta, args.size_px, ref, ground_speed=args.ground_speed,
                              own_ship=args.own_ship)
    if not found.carry:
        raise vf.Stop("track too short to fit a rate (need at least 3 points in the window)", vf.EXIT_NOTHING)
    fit, red = found.carry["fit"], found.carry["reduction"]

    print(f"{video.name}: {W}x{info['height']}, {info['fps']} fps")
    print(f"track: {fit['n']} points kept of {fit['n_in']} "
          f"({fit['n_clipped']} sigma-clipped as off the line) over "
          f"t = {fit['t0']:.2f}-{fit['t1']:.2f} s, span {fit['span_px']:.0f} px")
    print(f"       residual {fit['resid_rms']:.2f} px = {fit['resid_frac']:.1%} of the span"
          + ("" if fit["uniform"] else "   <-- NOT a uniform straight-line motion"))
    print(f"direction {fit['direction_deg']:.0f} deg (clockwise from screen-up)")
    print()
    print(red.report())
    par = found.fields.get("parallax")
    if par:
        print()
        print("\n".join(stages.parallax(args.ground_speed, args.own_ship)[2]))
    else:
        print(f"\nparallax: {dict(found.no_power).get('parallax', '')}")
    if args.ladder and not scale.known:
        ladder = sc.fov_ladder(fit["v_px"], W, (3, 10, 30, 54))
        found.fields["if_the_fov_were"] = ladder
        print("\nwhat each candidate field of view would imply "
              "(the spread is the point; do not pick one):")
        for r in ladder:
            sp = "  ".join(f"{R / 1000:g} km: {v:6.0f} m/s" for R, v in r["speeds"].items())
            print(f"  FOV {r['fov_deg']:5.1f} deg -> k {r['k']:8.0f} px/rad, "
                  f"omega {r['omega']:.4f} rad/s | {sp}")
    return found


if __name__ == "__main__":
    raise SystemExit(main())
