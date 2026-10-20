"""Does `mcdonald slew` read k cos(e) from a slew, and say when it cannot?

Synthetic series only, small and quick: a camera holding the ground while the pointer turns
at a steady rate, then an extra turn that moves the scene; the scene's shifts given as a
`layers` stage gives them (k-frame pairs) and the pointer as `symbology` gives it, on a
coarse grid. c must come back within a few per cent whatever the grid's phase; a window with
no slew, or a pointer whose steps are as large as the slew, must be refused; the forward fit
must be pulled low by the pointer's noise and the reverse not.

    python3 tests/test_slew.py        # or: pytest tests/

No video data needed.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import slew  # noqa: E402

FAIL = []
FPS = 30.0


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def run(c=1500.0, hold=0.33, extra_deg=1.0, slew_t0=5.0, slew_s=2.0, seconds=10.0, step=0.0, phase=0.0, k=5,
        el_share=0.2, gap=None, seed=1, n_boot=200):
    """The stage's fit on one synthetic window: (fit, truth c)."""
    rng = np.random.default_rng(seed)
    n = np.arange(1, int(seconds * FPS) + 1)
    t = (n - 1) / FPS
    extra = extra_deg * np.clip((t - slew_t0) / slew_s, 0, 1)
    theta = 250.0 + hold * t + extra
    X = c * extra + np.cumsum(rng.normal(0, 0.2, len(t)))
    Y = el_share * c * extra
    dx = X[k:] - X[:-k]
    dy = Y[k:] - Y[:-k]
    if gap:
        dx[gap[0]:gap[1]] = np.nan
    thq = (np.round((theta - phase) / step) * step + phase) if step else theta + rng.normal(0, 0.02, len(t))
    frames, Xs, Ys, S, _ = slew.scene_path(n[:len(dx)], dx, dy, k)
    ths = slew.smooth_like_scene(n, thq, k, frames)
    sig, _ = slew.pointer_scatter(thq, 295.0)
    m = np.isfinite(ths) & np.isfinite(Xs)
    return slew.fit_window((frames[m] - 1) / FPS, ths[m], Xs[m], Ys[m], S[m], sig, 1, FPS, n_boot), c


def test_a_clean_slew_is_read():
    print("\nslew: a clean slew over a ground-held hold")
    f, c = run()
    check(not f["no_power"], "it claims", f"{f['no_power']}")
    check(abs(f["c_px_per_deg"] / c - 1) < 0.02, "c within 2 %", f"{f['c_px_per_deg']:.0f} against {c:.0f}")
    check(abs(f["hold_rate_deg_per_s"] - 0.33) < 0.02, "the hold rate comes back", f"{f['hold_rate_deg_per_s']:.3f}")
    check(abs(f["tilt_deg"] - np.degrees(np.arctan(0.2))) < 1.0, "the elevation in step shows as the tilt",
          f"{f['tilt_deg']:.1f} deg")


def test_a_coarse_pointer_is_read_whatever_the_grid_phase():
    print("\nslew: a pointer on a 0.45-deg grid, at every phase of it")
    got = []
    for ph in np.linspace(0, 0.45, 6, endpoint=False):
        f, c = run(step=0.45, phase=ph, extra_deg=2.0, n_boot=100)
        got.append(f["c_px_per_deg"] / c)
        check(f["c_forward_px_per_deg"] < f["c_px_per_deg"], f"phase {ph:.3f}: the forward fit is pulled low",
              f"{f['c_forward_px_per_deg']:.0f} < {f['c_px_per_deg']:.0f}")
    got = np.array(got)
    check(np.abs(got - 1).max() < 0.06, "the reverse fit stays within 6 % at every phase", f"{np.round(got, 3)}")


def test_a_lever_under_half_the_grid_step_is_refused():
    print("\nslew: a 1.5-deg slew read by a pointer on a 1.07-deg grid (synthetic staircases: 15-26 % off here)")
    f, _ = run(step=1.07, extra_deg=1.5, n_boot=100)
    check(any("grid step" in w or "barely shows" in w for w in f["no_power"]), "refused: the slew is small against the grid",
          f"{f['no_power'][:1]}")


def test_no_slew_is_refused():
    print("\nslew: the camera never slews")
    f, _ = run(extra_deg=0.0)
    check(any("did not slew" in w for w in f["no_power"]), "refused: the scene did not move beyond a steady drift",
          f"{f['no_power']}")


def test_a_slew_below_the_pointers_step_is_a_floor_not_a_measurement():
    print("\nslew: an extra turn of a fifth of the pointer's step, at every phase of the grid")
    for ph in np.linspace(0, 0.5, 5, endpoint=False):
        f, c = run(step=0.5, phase=ph, extra_deg=0.1, n_boot=150)
        floor = f.get("c_at_least_px_per_deg")
        check(not f.get("c_px_per_deg") or bool(f["no_power"]), f"phase {ph:.2f}: no measurement claimed",
              f"registered {f['registered']}, {f['no_power'][:1]}")
        check(floor is None or floor <= c, f"phase {ph:.2f}: any floor stays under the truth",
              f"floor {floor} against {c:.0f}")


def test_a_pointer_that_ignores_the_slew_gives_a_floor():
    print("\nslew: a pointer that turns at its hold rate whatever the turret does (a heading reference)")
    # the scene motion of a 1-deg slew at c = 1500, with the pointer blind to it
    rng = np.random.default_rng(3)
    n = np.arange(1, 301)
    t = (n - 1) / FPS
    X = 1500.0 * np.clip((t - 5) / 2, 0, 1) + np.cumsum(rng.normal(0, 0.2, len(t)))
    thq = np.round((250.0 + 0.33 * t) / 0.45) * 0.45
    dx = X[5:] - X[:-5]
    frames, Xs, Ys, S, _ = slew.scene_path(n[:len(dx)], dx, dx * 0, 5)
    ths = slew.smooth_like_scene(n, thq, 5, frames)
    sig, _ = slew.pointer_scatter(thq, 295.0)
    m = np.isfinite(ths) & np.isfinite(Xs)
    f = slew.fit_window((frames[m] - 1) / FPS, ths[m], Xs[m], Ys[m], S[m], sig, 1, FPS, 150)
    check(f["registered"] is False and f.get("c_at_least_px_per_deg"), "not registered: a floor on c",
          f"floor {f.get('c_at_least_px_per_deg')}")
    check(abs(f["hold_rate_deg_per_s"] - 0.33) < 0.03, "the hold rate is still read", f"{f['hold_rate_deg_per_s']:.3f}")


def test_a_broken_chain_keeps_its_stretches_apart():
    print("\nslew: a gap of 1.5 s in the scene's chain during the hold, too long to bridge")
    f, c = run(gap=(30, 75))
    check(not f["no_power"] and abs(f["c_px_per_deg"] / c - 1) < 0.03, "c is read across the two stretches",
          f"{f.get('c_px_per_deg', float('nan')):.0f} against {c:.0f}; {f['no_power']}")


def test_a_short_gap_at_the_slews_start_is_bridged():
    print("\nslew: the pairs at the slew's start missing, as `layers` leaves them")
    f, c = run(gap=(146, 154))
    check(not f["no_power"] and abs(f["c_px_per_deg"] / c - 1) < 0.03, "c is read across the bridge",
          f"{f.get('c_px_per_deg', float('nan')):.0f} against {c:.0f}; {f['no_power']}")


def test_the_chains_kernel_is_the_pointers():
    print("\nslew: the scene chain smooths as its kernel says")
    k = 5
    n = np.arange(1, 101)
    X = np.where(n > 50, 100.0, 0.0)                 # a step
    dx = X[k:] - X[:-k]
    frames, Xs, _, S, _ = slew.scene_path(n[:len(dx)], dx, dx * 0, k)
    d, w = slew.kernel(k)
    main_ = S == np.bincount(S[S >= 0]).argmax()                 # the ends, where under half the pairs span a step, break off
    want = np.array([sum(wi * X[min(max(f + di, 1), 100) - 1] for di, wi in zip(d, w)) for f in frames[main_]])
    got = Xs[main_] - Xs[main_][0] + want[0]
    check(main_.sum() > 80 and np.abs(got - want).max() < 1e-9, "the chained path is the step smoothed by the kernel",
          f"worst {np.abs(got - want).max():.2e} over {main_.sum()} frames")


def test_auto_windows_find_the_slew():
    print("\nslew: a window round each slew")
    t = np.arange(0, 20, 1 / FPS)
    vx = np.where((t > 8) & (t < 11), 300.0, 0.0) + np.where((t > 14) & (t < 16), -200.0, 0.0)
    w = slew.slews(t, vx, FPS)
    check(len(w) == 2 and w[0][0] < 8 and w[0][1] > 11 and w[1][0] < 14 and w[1][1] > 16,
          "one window round each slew, start to stop", f"{[(round(a, 2), round(b, 2)) for a, b in w]}")


def test_a_still_platform_gives_k_from_a_steady_pan():
    print("\nslew: a camera on a still platform panning at one steady rate the whole window")
    rng = np.random.default_rng(5)
    k, c = 5, 1500.0
    n = np.arange(1, 301)
    t = (n - 1) / FPS
    theta = 250.0 + 0.4 * t                                          # the whole turn is the pan's
    thq = np.round(theta / 0.2) * 0.2                                # on a grid, as PURSUE's pointers are
    X = c * 0.4 * t + np.cumsum(rng.normal(0, 0.2, len(t)))
    dx = X[k:] - X[:-k]
    frames, Xs, Ys, S, _ = slew.scene_path(n[:len(dx)], dx, dx * 0, k)
    ths = slew.smooth_like_scene(n, thq, k, frames)
    sig, step = slew.pointer_scatter(thq, 295.0)
    m = np.isfinite(ths) & np.isfinite(Xs)
    still = slew.fit_window((frames[m] - 1) / FPS, ths[m], Xs[m], Ys[m], S[m], sig, 0, FPS, 150, step_deg=step)
    check(not still["no_power"] and abs(still["c_px_per_deg"] / c - 1) < 0.03, "with --still (no hold term) c comes back",
          f"{still.get('c_px_per_deg')} against {c:.0f}; {still['no_power']}")
    moving = slew.fit_window((frames[m] - 1) / FPS, ths[m], Xs[m], Ys[m], S[m], sig, 1, FPS, 150, step_deg=step)
    check(not moving.get("c_px_per_deg") or bool(moving["no_power"]), "with a hold term the steady pan is the hold: no k",
          f"registered {moving['registered']}, {moving['no_power'][:1]}")


def test_the_path_filter_keeps_a_pointer_that_turns_round_and_drops_a_mislock_run():
    print("\nslew: the path filter on a pan that reverses, with a mislocked run in it")
    fps = 30.0
    n = np.arange(1, 331)
    t = (n - 1) / fps
    pan = 53 + 2.6 * np.sin(2 * np.pi * t / 5.0)                   # a broadcast pan reversing every 2.5 s
    theta = (-pan) % 360
    bad = (n >= 140) & (n < 170)                                   # a second of mislocks 1.5 deg off
    theta_read = np.where(bad, theta - 1.5, theta)
    r = np.full(len(n), 295.0)
    keep, _ = slew.clean_pointer(n, r, theta_read, fps)
    # a sine pan of 2.6 deg every 5 s turns at 4 deg/s^2, which over the filter's 3 s a parabola misses by up to
    # ~3 deg: the line judges there and drops readings at the vertices (the real broadcast pan kept 312 of 330)
    check(keep[~bad].mean() > 0.85, "most true readings are kept through the reversals",
          f"{keep[~bad].sum()} of {(~bad).sum()}")
    check(keep[bad].mean() < 0.2, "the mislocked run is dropped", f"{keep[bad].sum()} of {bad.sum()} kept")


def _stretched_clip(td, theta0, par, c=1500.0, hold=0.33, seconds=10.0, k=5, r=300.0, bore=(960.0, 540.0)):
    """A pointer and a scene as `symbology` and `layers` write them, from a picture drawn `par` times wider than
    it was made: the glyph at (bx + par r sin, by - r cos), the scene's shift across times par."""
    import csv
    n = np.arange(1, int(seconds * FPS) + 1)
    t = (n - 1) / FPS
    extra = np.clip((t - 4.0) / 3.0, 0, 1) * 1.5
    th = theta0 + hold * t + extra
    X = par * c * extra                                              # square px times the stretch
    gx, gy = bore[0] + par * r * np.sin(np.radians(th)), bore[1] - r * np.cos(np.radians(th))
    north, layers = Path(td) / "c_north.csv", Path(td) / "c_layers.csv"
    with open(north, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame", "t_s", "glyph_x", "glyph_y", "r_px", "theta_deg", "quality"])
        for i in range(len(n)):                                     # as symbology reads it: about the boresight, in video px
            dx, dy = gx[i] - bore[0], gy[i] - bore[1]
            w.writerow([n[i], t[i], gx[i], gy[i], np.hypot(dx, dy), np.degrees(np.arctan2(dx, -dy)) % 360, 1.0])
    with open(layers, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame", "t_s", f"all_dx{k}", f"all_dy{k}"])
        for i in range(len(n) - k):
            w.writerow([n[i], t[i], X[i + k] - X[i], 0.0])
    return north, layers


def test_a_stretched_picture_is_read_in_square_pixels():
    import tempfile
    print("\nslew: a 4:3 picture drawn full-height in 16:9 (pixels 1.333 times wider than tall)")
    W, H, par = 1920, 1080, 4 / 3
    for theta0, where in ((-5.0, "at the top of its circle"), (85.0, "at its side")):
        with tempfile.TemporaryDirectory() as td:
            north, layers = _stretched_clip(td, theta0, par)
            got = {}
            for a in (1.0, par):
                f = slew.measure(north, layers, W, H, FPS, windows=[(0.0, 9.8)], pixel_aspect=a, n_boot=100).fields
                w = f["windows"][0]
                got[a] = (w.get("c_px_per_deg"), w.get("hold_rate_deg_per_s"), f.get("fov_w_ceiling_deg"))
        c, hold, fov = got[par]
        check(c is not None and abs(c / 1500 - 1) < 0.03 and abs(hold - 0.33) < 0.02,
              f"{where}: with --pixel-aspect 1.333, c and the hold come back", f"c {c}, hold {hold}")
        check(fov is not None and abs(fov / (1440 / 1500) - 1) < 0.03, f"{where}: the field's ceiling is the picture's",
              f"{fov} deg against {1440 / 1500:.3f}")
        c1, hold1, fov1 = got[1.0]
        print(f"        (read as square: c {c1}, hold {hold1}, field {fov1})")


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
