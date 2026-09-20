"""Can the package reproduce every published number?

The Technical Note (JAIS 2026-08-I012054) and the PR144 working notes are the
results this toolkit exists to have produced. This suite walks their
quantitative claims one at a time and checks the package returns each.

Unlike test_golden.py, most checks here need no video: they are the reduction
applied to tracks and measurements that are already recorded. Those that do
need imagery are marked and skip cleanly.

    python3 tests/test_published.py
    python3 tests/test_published.py --tracks /path/to/uap/analysis

A failure here means a published number can no longer be produced by the code
that is supposed to produce it. That is a retraction risk, not a test nit.
"""
import argparse
import csv
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from mcdonald import kinematics as kin  # noqa: E402

FAIL, SKIP = [], []
A_SOUND = 343.0


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def close(a, b, tol):
    return a is not None and abs(a - b) <= tol


def read_track(path, xc="x_px", yc="y_px", fc="frame"):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                rows.append([float(str(r[fc]).lstrip("e")), float(r[xc]), float(r[yc])])
            except (ValueError, KeyError, TypeError):
                continue
    return np.array(rows, float).reshape(-1, 3)


# ---------------------------------------------------------------- PR113
def pr113(tracks):
    """Technical Note Sec. 5 (DOW-UAP-PR113)."""
    print("\nTechnical Note, PR113 — the graticule case")
    W, FPS, V_PX_FR, P_PX = 1920.0, 30.0, 142.0, 25.0

    k = kin.AngularScale.from_graticule(35.4)
    check(close(k.k, 2.03e3, 5), 'k = 35.4 px/deg = "2.03e3 px/rad"',
          f"{k.k:.1f} px/rad")
    check(close(kin.fov_from_k(k.k, W, small_angle=True), 54, 0.5),
          'FOV ~54 deg "with a linear extrapolation across the frame"',
          f"{kin.fov_from_k(k.k, W, small_angle=True):.1f} deg")
    om = kin.omega(V_PX_FR * FPS, k)
    check(close(om, 2.10, 0.01), "omega ~2.10 rad/s", f"{om:.3f}")
    check(close(math.degrees(om), 120, 1.0), "= ~120 deg/s", f"{math.degrees(om):.1f}")
    check(close(V_PX_FR * FPS / W, 2.2, 0.05), "v_px ~2.2 frame-widths per second",
          f"{V_PX_FR * FPS / W:.2f}")
    s = kin.object_size(P_PX, 3000.0, k)
    check(close(s, 37, 1.0), '~25 px is "a ~37 m craft at 3 km"', f"{s:.1f} m")

    # theta = 90 is the lower bound, and the fan is one-sided
    R, fanv = kin.fan(om, thetas_deg=(90, 30, 2))
    check(all((fanv[90] <= fanv[30] + 1e-9).all() and (fanv[30] <= fanv[2] + 1e-9).all()
              for _ in [0]), "theta = 90 deg is a hard lower bound at every range")
    i = int(np.argmin(np.abs(R - 300)))
    check(fanv[90][i] / A_SOUND > 1.0,
          '"supersonic beyond a few hundred meters for every aspect angle"',
          f"Mach {fanv[90][i] / A_SOUND:.1f} at R = {R[i]:.0f} m, theta = 90")

    # The published rate comes from the object's per-frame displacement over
    # e048-e051, recorded in pr113_track.py's docstring as (-103, +98) px/frame.
    check(close(math.hypot(103, 98), V_PX_FR, 0.3),
          "the documented (-103, +98) px/frame step is the published 142",
          f"{math.hypot(103, 98):.1f} px/frame")

    # It is NOT refittable from the committed CSV, and that is worth asserting
    # rather than glossing: pr113_transit.csv is a per-frame *component dump*
    # ordered by area, with no column saying which component is the object, so
    # x1/y1 jump between unrelated blobs (1009,313 -> 917,411 -> 118,899).
    # Regenerating the headline number needs the frames plus the hand
    # identification. Flagged as a provenance gap, not a pass.
    t = tracks / "pr113_transit.csv" if tracks else None
    if t and t.exists():
        a = read_track(t, "x1", "y1")
        f = kin.fit_v_px(a, FPS) if len(a) >= 3 else None
        got = f["v_px"] / FPS if f else None
        check(got is not None and abs(got - V_PX_FR) > 50,
              "a blind refit from pr113_transit.csv does NOT give 142 -- as expected",
              f"{got:.1f} px/frame; the CSV does not identify the object component, "
              "so the transit is not recoverable from it alone")
        SKIP.append("PR113 v_px is not regenerable from the committed CSV "
                    "(needs frames + the e048-e051 hand identification)")
    else:
        print("  SKIP  the PR113 CSV check (no --tracks)")
        SKIP.append("PR113 CSV")


# ---------------------------------------------------------------- PR149
def pr149(tracks):
    """Technical Note Sec. 6 (DOW-UAP-PR149)."""
    print("\nTechnical Note, PR149 — the scale-bar case")
    FPS, L_PX, V_LO, V_HI = 30.0, 920.0, 604.5, 633.7

    lo, hi = V_LO / L_PX, V_HI / L_PX
    check(close(lo, 0.657, 0.002) and close(hi, 0.689, 0.002),
          "0.657-0.689 ship-lengths per second", f"{lo:.3f}-{hi:.3f}")
    check(1 / hi < 1.6 and 1 / lo < 1.6, "crosses the whole hull in under 1.6 s",
          f"{1 / hi:.2f}-{1 / lo:.2f} s")

    v150 = kin.scale_bar_speed(V_LO, L_PX, 150.0)
    v200 = kin.scale_bar_speed(V_LO, L_PX, 200.0)
    check(close(v150, 99, 1) and close(v200, 132, 1),
          "upper bound 99-132 m/s for a 150-200 m Handymax",
          f"{v150:.0f}-{v200:.0f} m/s")
    check(close(v150 / A_SOUND, 0.3, 0.02) and close(v200 / A_SOUND, 0.4, 0.02),
          "= ~0.3-0.4 Mach", f"{v150 / A_SOUND:.2f}-{v200 / A_SOUND:.2f}")
    check(v200 / A_SOUND < 1.0, '"supersonic relative velocities can be excluded"')

    # the size/speed pairs: both follow from one range ratio
    h_px = 4.18                                  # object vertical FWHM, pr149_ship.py
    for want_v, want_s, loa in ((12.0, 0.08, 150.0), (22.5, 0.15, 200.0)):
        rr = want_v / kin.scale_bar_speed(V_LO, L_PX, loa)
        size = h_px / L_PX * loa * rr
        check(close(size, want_s, 0.012),
              f'"a {want_s} m body at {want_v} m/s"',
              f"{size:.3f} m at range ratio {rr:.3f}")

    t = tracks / "pr149_transit.csv" if tracks else None
    if t and t.exists():
        a = read_track(t)
        f = kin.fit_v_px(a, FPS)
        check(close(f["v_px"] / FPS, 20.2, 0.6), "v_px = 20.2 px/frame, refit from the track",
              f"{f['v_px'] / FPS:.2f} px/frame")
        check(close(f["n"], 43, 3), "tracked over 43 frames", f"{f['n']} kept of {f['n_in']}")

        # The workup records n = 17 -> n = 98, i.e. exits at t = 3.23 s after a
        # 2.70 s track. The Note's "43 frames spanning 3.2 s" reads the exit
        # timestamp as the duration; the tracked interval is 2.70 s.
        check(close(f["t1"], 3.23, 0.05), "exits at t = 3.23 s", f"{f['t1']:.2f} s")
        check(close(f["t1"] - f["t0"], 2.70, 0.05),
              "the tracked interval is 2.70 s, not 3.2 s",
              f"{f['t1'] - f['t0']:.2f} s -- the Note quotes the exit time as the span")

        # The workup records 2.6 px (x) and 3.4 px (y) separately; the Note
        # quotes the x component alone. The 2D scatter is hypot(2.6, 3.4).
        a2 = a[np.argsort(a[:, 0])]
        tt = (a2[:, 0] - 1) / FPS
        rx = a2[:, 1] - np.polyval(np.polyfit(tt, a2[:, 1], 1), tt)
        ry = a2[:, 2] - np.polyval(np.polyfit(tt, a2[:, 2], 1), tt)
        check(close(float(np.sqrt((rx ** 2).mean())), 2.6, 0.15), "straight to 2.6 px rms in x",
              f"{np.sqrt((rx ** 2).mean()):.2f} px")
        check(close(float(np.sqrt((ry ** 2).mean())), 3.4, 0.15), "and 3.4 px rms in y",
              f"{np.sqrt((ry ** 2).mean()):.2f} px")
        check(close(f["resid_rms"], math.hypot(2.6, 3.4), 0.15),
              "the 2D residual is their quadrature sum",
              f"{f['resid_rms']:.2f} px -- the Note quotes the x component alone")
        check(f["uniform"], "and the motion is uniform, so v_px describes it",
              f"residual {f['resid_frac']:.1%} of span")
    else:
        print("  SKIP  the PR149 track checks (no --tracks)")
        SKIP.append("PR149 track")


# ---------------------------------------------------------------- PR144
def pr144(tracks):
    """pr144_velocity_size.md and pr144_integrity.md."""
    print("\nPR144 working notes — layers, zoom, integrity")
    print("  (layer rates are checked against the clip by tests/test_golden.py:")
    print("   object vs sea 648, vs cloud tops 510, cloud vs sea 98, ratio 6.2)")

    # the zoom, and why the brackets must not be used for it
    check(abs(5.9 / 2.97 - 2.0) < 0.02,
          "the bracket reading (x2.97) and the fitted zoom (x5.9) differ by ~2x",
          "which is why zoom is fitted from imagery, never read off the box")
    # FOV cap: a x5.9 zoom from a wide field bounds the narrow one
    check(close(kin.fov_from_k(kin.AngularScale.from_fov(1920, 9.0).k, 1920), 9.0, 0.01),
          "FOV <-> k round-trips at the ~9 deg cap")

    t = tracks / "pr144_layers.csv" if tracks else None
    if t and t.exists():
        a = read_track(t)
        f = kin.fit_v_px(a, 30.0)
        check(not f["uniform"],
              "a frame-coordinate fit to PR144 is correctly refused as non-uniform",
              f"residual {f['resid_frac']:.0%} of span -- its rate belongs to `layers`, "
              "because the object is held in the FOV while the camera pans")
    else:
        print("  SKIP  the PR144 non-uniform check (no --tracks)")
        SKIP.append("PR144 non-uniform")

    north = tracks / "pr144_north.csv" if tracks else None
    if north and north.exists():
        r = [float(x["r_px"]) for x in csv.DictReader(open(north)) if x["r_px"]]
        check(close(float(np.mean(r)), 310.9, 0.5) and float(np.std(r)) < 1.5,
              "north pointer radius 310.9 +/- 0.9 px (reproduced by `mcdonald symbology`)",
              f"{np.mean(r):.1f} +/- {np.std(r):.1f} px over {len(r)} frames")
    else:
        print("  SKIP  the PR144 pointer check (no --tracks)")
        SKIP.append("PR144 pointer")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tracks", type=Path,
                    default=Path("/hugespace/local/research/uap/analysis"),
                    help="directory holding the recorded per-clip CSVs")
    args = ap.parse_args()
    tracks = args.tracks if args.tracks and args.tracks.exists() else None
    print("McDonald UAP Toolkit — published-results check")
    print(f"tracks: {tracks or 'not available (reduction-only checks will run)'}")
    pr113(tracks)
    pr149(tracks)
    pr144(tracks)
    if FAIL:
        print(f"\n{len(FAIL)} FAILED: {', '.join(FAIL)}")
        return 1
    print(f"\n{'ALL PASS' if not SKIP else 'ALL PASS (skipped: ' + ', '.join(SKIP) + ')'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
