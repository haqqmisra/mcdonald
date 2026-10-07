"""Checks for `mcdonald tether`: a hanging point's period gives its line, a planted
companion is told from the frame and the scene, the overlay's strokes are masked and a
dark line is not, repeated frames stay out of the series, and a short window is
tentative. Portable: no video data.

    python3 tests/test_tether.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from mcdonald import tether  # noqa: E402

RNG = np.random.default_rng(20261006)
FAIL = []


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def pendulum_series(L_m, fps=29.97, seconds=12.0, amp_deg=12.0, sep_px=160.0, noise_px=1.0, drift=(0.3, 0.1)):
    """A track and a companion hanging sep_px below it, swinging as a pendulum of L_m metres."""
    T = 2 * np.pi * np.sqrt(L_m / tether.G)
    track, comp = {}, {}
    for n in range(1, int(seconds * fps) + 1):
        t = (n - 1) / fps
        x, y = 600 + drift[0] * n, 300 + drift[1] * n
        a = np.radians(amp_deg) * np.sin(2 * np.pi * t / T + 0.4)
        track[n] = (x, y)
        comp[n] = (x + sep_px * np.sin(a) + RNG.normal(0, noise_px), y + sep_px * np.cos(a) + RNG.normal(0, noise_px), -30.0)
    return track, comp, T


def test_a_swinging_point_gives_its_line():
    """T = 2 pi sqrt(L/g): a 1.5 m pendulum seen for 12 s comes back as 1.5 m, claimed, with an error."""
    print("a swinging point gives its line")
    track, comp, T = pendulum_series(1.5)
    sw = tether.swing(track, comp, 29.97)
    check(sw["swings"] is True and sw["tentative"] is False, "the swing is seen and claimed", f"power {sw['power']:.2f}, {sw['cycles']:.1f} cycles")
    check(abs(sw["period_used_s"] - T) < 0.05 * T, "its period is the pendulum's", f"{sw['period_used_s']:.3f} s vs {T:.3f}")
    check(abs(sw["line_length_m"] - 1.5) < 0.15, "and L = g T^2 / 4 pi^2 is the line", f"{sw['line_length_m']:.2f} m")
    check(sw.get("period_err_s") is not None and sw["period_err_s"] < 0.1, "with a bootstrap error on the period",
          f"{sw.get('period_err_s')}")
    check(sw.get("line_length_err_m") is not None and abs(sw["line_length_m"] - 1.5) < 3 * sw["line_length_err_m"] + 0.05,
          "and the line within its error", f"{sw['line_length_m']:.2f} +- {sw.get('line_length_err_m')}")
    check(abs(sw["amplitude_deg"] - 12.0) < 2.0, "with its amplitude", f"{sw['amplitude_deg']:.1f} deg")
    check(sw["smooth"], "the companion moves smoothly frame to frame", f"{100 * sw['step_over_separation']:.1f}% of its separation")


def test_a_steady_line_gives_no_length():
    """A line held at a fixed angle by drag (PR071) has no period, and no length is claimed."""
    print("a steady line gives no length")
    track, comp, _ = pendulum_series(1.5, amp_deg=0.0, noise_px=1.5)
    sw = tether.swing(track, comp, 29.97)
    check(sw["swings"] is False and sw["line_length_m"] is None, "no swing, no length", sw["finding"])


def test_too_few_cycles_are_not_a_period():
    """A 30 m line swings every 11 s: 12 s of it is one cycle, and no period is claimed;
    20 s is 1.8 cycles, a tentative one; 40 s is claimed."""
    print("too few cycles are not a period")
    track, comp, T = pendulum_series(30.0, seconds=12.0)
    sw = tether.swing(track, comp, 29.97)
    check(sw["swings"] is False, "one cycle of an 11 s swing is not a period", sw["finding"])
    track, comp, T = pendulum_series(30.0, seconds=20.0)
    sw = tether.swing(track, comp, 29.97)
    check(sw["swings"] is True and sw["tentative"] is True and abs(sw["line_length_m"] - 30.0) < 4.0,
          "1.8 cycles of it is a tentative period", f"{sw.get('line_length_m')} m, tentative {sw.get('tentative')}")
    track, comp, T = pendulum_series(30.0, seconds=40.0)
    sw = tether.swing(track, comp, 29.97)
    check(sw["swings"] is True and sw["tentative"] is False and abs(sw["line_length_m"] - 30.0) < 3.0, "40 s of it is claimed",
          f"{sw.get('line_length_m')} m")


def test_repeated_frames_are_left_out():
    """A hold-and-jump clip repeats frames: the repeated ones are dropped from the series and
    the period is still the pendulum's."""
    print("repeated frames are left out")
    track, comp, T = pendulum_series(1.5)
    reps = [n for n in sorted(comp) if n % 3 == 0]
    for n in reps:                                   # the repeat carries its predecessor's content
        comp[n] = comp[n - 1]
    sw = tether.swing(track, comp, 29.97, repeats=reps)
    check(sw["repeated_frames_dropped"] == len(reps), "the repeats are counted out", f"{sw['repeated_frames_dropped']} of {len(reps)}")
    check(sw["swings"] and abs(sw["period_used_s"] - T) < 0.05 * T, "and the period survives", f"{sw['period_used_s']:.3f} s vs {T:.3f}")


def planted_stack(R=300, size=16.0, companion=(-20, 120), depth=-25.0, noise=1.0):
    """An object stack: a dark disc at the centre, cloud-like texture smeared into streaks along x,
    a compact dark companion at `companion`; and its reversed-track control, where the companion
    is smeared instead. (mean, count, control)."""
    from scipy.ndimage import gaussian_filter
    S = 2 * R + 1
    yy, xx = np.mgrid[0:S, 0:S]
    base = 130 + gaussian_filter(RNG.normal(0, 1, (S, S)), (6, 40)) * 60       # streaks along x: the scene smeared
    m = base + RNG.normal(0, noise, (S, S))
    m[np.hypot(xx - R, yy - R) <= size / 2] -= 90
    bump = depth * np.exp(-0.5 * (((xx - R - companion[0]) ** 2 + (yy - R - companion[1]) ** 2) / 1.5 ** 2))
    cnt = np.full((S, S), 90.0)
    mc = base + RNG.normal(0, noise, (S, S))
    mc[np.hypot(xx - R, yy - R) <= size / 2] -= 90
    for dx in range(-40, 41, 2):                      # on the reversed track the companion is spread along the object's path
        mc += (depth / 41) * np.exp(-0.5 * (((xx - R - companion[0] - dx) ** 2 + (yy - R - companion[1]) ** 2) / 1.5 ** 2))
    return m + bump, cnt, mc


def test_a_companion_is_told_from_the_control():
    """A compact feature on the object stack that the reversed-track stack does not show."""
    print("a companion is told from the control")
    m, cnt, mc = planted_stack()
    cands, sig = tether.candidates(m, cnt, mc, 16.0, 300, 1.2, 15.0, top=40)
    hit = [c for c in cands if abs(c["dx_px"] + 20) <= 3 and abs(c["dy_px"] - 120) <= 3]
    check(bool(hit), "the planted companion is a candidate", f"{len(cands)} candidates, noise {sig:.2f} DN")
    if hit:
        c = hit[0]
        check(c["sign"] == "dark" and c["not_on_control"], "dark, and not on the reversed track",
              f"z {c['z']:.1f} on the object, {c['z_control']:.1f} on the control")
        check(abs(c["direction_deg"] - np.degrees(np.arctan2(-20, 120))) < 2, "at its direction from straight down",
              f"{c['direction_deg']:+.1f} deg")
    others = [c for c in cands if c not in hit and c["not_on_control"]]
    check(len(others) <= 2, "the smeared scene is mostly as sharp on the control", f"{len(others)} other features pass it")


def test_the_object_size_is_read_off_the_stack():
    print("the object's size is read off the stack")
    m, cnt, _ = planted_stack(size=24.0)
    est = tether.object_size(m, cnt, 300)
    check(est is not None and abs(est - 24.0) < 4.0, "a 24 px disc", f"{est:.1f} px")


def test_the_objects_own_glints_are_inside_its_extent():
    """A crumpled balloon's glints lie outside its half-max width; the extent reaches them, and
    the search starts beyond."""
    print("the object's own glints are inside its extent")
    m, cnt, _ = planted_stack(size=16.0)
    R = 300
    yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]]
    rr = np.hypot(xx - R, yy - R)
    m[(rr > 8) & (rr <= 26)] -= 20                 # the body's dim outer facets, below half the core's contrast
    for dx, dy in ((22, 4), (-19, -9), (6, 24)):   # and glints on them
        m[R + dy - 1:R + dy + 2, R + dx - 1:R + dx + 2] += 60
    size = tether.object_size(m, cnt, R)
    ext = tether.object_extent(m, cnt, R, size)
    check(size is not None and size < 22, "the half-max width is the core's", f"{size:.1f} px")
    check(24 <= ext <= 32, "the extent reaches the facets and the glints", f"{ext:.1f} px")


def test_the_overlays_strokes_are_masked_and_a_dark_line_is_not():
    """A reticle's bright arm and a gate's box are masked; a dark string, a bright blob and the
    scene are not."""
    print("the overlay's strokes are masked, a dark line is not")
    g = 170 + RNG.normal(0, 2, (300, 300))
    g[150, 40:120] = 240                              # a horizontal arm, 1 px
    g[60:140, 200:204] = 235                          # a vertical gate edge, 4 px wide
    g[180:260, 100] = 110                             # a dark string
    yy, xx = np.mgrid[0:300, 0:300]
    g[np.hypot(xx - 250, yy - 250) <= 8] = 250        # a bright blob 16 px across
    m = tether.stroke_mask(g)
    check(m[150, 80] and m[100, 202], "the arm and the gate edge are masked")
    check(not m[220, 100], "the dark string is not")
    check(not m[250, 250], "nor a bright blob wider than a stroke")
    check(m.mean() < 0.05, "and little else is", f"{100 * m.mean():.1f}% of the frame")


def main():
    for t in (test_a_swinging_point_gives_its_line, test_a_steady_line_gives_no_length,
              test_too_few_cycles_are_not_a_period, test_repeated_frames_are_left_out,
              test_a_companion_is_told_from_the_control, test_the_object_size_is_read_off_the_stack,
              test_the_objects_own_glints_are_inside_its_extent, test_the_overlays_strokes_are_masked_and_a_dark_line_is_not):
        t()
    print(f"\n{'OK' if not FAIL else 'FAILED'}: {len(FAIL)} failing check(s)" + ("" if not FAIL else "\n  " + "\n  ".join(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
