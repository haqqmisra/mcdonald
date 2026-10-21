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


# ---- zoom states ------------------------------------------------------------------------
def _two_field_clip(td, c=(500.0, 1000.0), burst=(571, 583), seconds=40.0, k=5, hold=0.2, seed=4, blind=False):
    """A pointer and a scene as `symbology` and `layers` write them, over a clip whose field changes at a burst of
    blank frames (`burst`): c px/deg before it and after it, a 2-deg slew in each state (6-8 s and 27-29 s) over a
    steady hold, no pair measured across the burst. `blind`: the pointer does not turn with the second slew (north
    against the platform's heading), so the second state gives a floor."""
    import csv
    rng = np.random.default_rng(seed)
    n = np.arange(1, int(seconds * FPS) + 1)
    t = (n - 1) / FPS
    extra = 2.0 * np.clip((t - 6) / 2, 0, 1) + 2.0 * np.clip((t - 27) / 2, 0, 1)
    seen = 2.0 * np.clip((t - 6) / 2, 0, 1) + (0.0 if blind else 2.0) * np.clip((t - 27) / 2, 0, 1)
    th = 250.0 + hold * t + seen + rng.normal(0, 0.02, len(t))
    cc = np.where(n < burst[0], c[0], c[1])
    X = np.cumsum(np.r_[0.0, np.diff(extra) * cc[1:]]) + np.cumsum(rng.normal(0, 0.2, len(t)))
    north, layers = Path(td) / "z_north.csv", Path(td) / "z_layers.csv"
    with open(north, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame", "t_s", "glyph_x", "glyph_y", "r_px", "theta_deg", "quality"])
        for i in range(len(n)):
            w.writerow([n[i], t[i], 960 + 300 * np.sin(np.radians(th[i])), 540 - 300 * np.cos(np.radians(th[i])), 300.0,
                        th[i] % 360, 1.0])
    with open(layers, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frame", "t_s", f"all_dx{k}", f"all_dy{k}"])
        for i in range(len(n) - k):
            inside = n[i] + k >= burst[0] and n[i] <= burst[1]
            w.writerow([n[i], t[i], "" if inside else X[i + k] - X[i], "" if inside else 0.0])
    return north, layers, len(n)


def _zoom(n_last, verdict="step", s=2.0, burst=(571, 583)):
    from mcdonald import zoom
    rows = [dict(frames=list(burst), t_s=[(burst[0] - 1) / FPS, (burst[1] - 1) / FPS], verdict=verdict,
                 s=s if verdict == "step" else None, zncc=0.6, zncc_at_1=0.1, why="" if verdict != "unknown" else "test")]
    return dict(bursts=rows, states=zoom.states_of(rows, n_last, FPS))


def test_windows_are_cut_at_a_zoom_and_compared_within_their_state():
    import tempfile
    print("\nslew: a clip whose field halves at 19 s, a slew either side (c 500 then 1000)")
    with tempfile.TemporaryDirectory() as td:
        north, layers, N = _two_field_clip(td)
        f = slew.measure(north, layers, 1920, 1080, FPS, zoom=_zoom(N), n_boot=100).fields
        one = slew.measure(north, layers, 1920, 1080, FPS, zoom=None, n_boot=100).fields
    st = {r["state"]: r for r in f["states"]}
    check(len(f["windows"]) == 2 and [w["state"] for w in f["windows"]] == [0, 1], "one window in each state",
          f"{[(w['window'], w['state']) for w in f['windows']]}")
    check(st[0]["c_px_per_deg"] and abs(st[0]["c_px_per_deg"] / 500 - 1) < 0.03, "state 0: c 500",
          f"{st[0]['c_px_per_deg']}")
    check(st[1]["c_px_per_deg"] and abs(st[1]["c_px_per_deg"] / 1000 - 1) < 0.03, "state 1: c 1000",
          f"{st[1]['c_px_per_deg']}")
    chk = f["zoom_checks"][0] if f["zoom_checks"] else {}
    check(chk.get("agree") is True and abs(chk["c_ratio"] / 2 - 1) < 0.04, "the ratio of c across the step is the imagery's x2",
          f"{chk}")
    check(f["c_spread"] is None, "no state holds two fields", f"{f['c_spread']}")
    print(f"        (taken as one field, --no-zoom: c {one['c_px_per_deg']:.0f}, the windows apart x{one['c_spread']:.2f})")
    check(one["c_spread"] and one["c_spread"] > 1.8, "taken as one field, the two claims disagree by the zoom",
          f"x{one['c_spread']}")


def test_a_zoom_the_slew_does_not_bear_out_is_said():
    import tempfile
    print("\nslew: the same clip, the imagery's zoom given as x1.5 where the field halved")
    with tempfile.TemporaryDirectory() as td:
        north, layers, N = _two_field_clip(td)
        found = slew.measure(north, layers, 1920, 1080, FPS, zoom=_zoom(N, s=1.5), n_boot=100)
    chk = found.fields["zoom_checks"][0]
    check(chk["agree"] is False, "the check fails", f"c x{chk['c_ratio']:.3f} against x{chk['imaged_ratio']:.3f}")
    check(any("imagery's zoom" in w[1] for w in found.no_power), "and the stage says so", f"{found.no_power}")


def test_an_unknown_burst_compares_nothing():
    import tempfile
    print("\nslew: the burst's zoom not measured")
    with tempfile.TemporaryDirectory() as td:
        north, layers, N = _two_field_clip(td)
        found = slew.measure(north, layers, 1920, 1080, FPS, zoom=_zoom(N, verdict="unknown"), n_boot=100)
    f = found.fields
    check([r["chain"] for r in f["states"]] == [0, 1], "the states are on different chains", f"{f['states']}")
    check(f["zoom_checks"] and f["zoom_checks"][0]["compared"] is False, "their c's are not compared", f"{f['zoom_checks']}")
    check(not any("disagree" in w[1] for w in found.no_power), "and nothing is refused for their differing",
          f"{found.no_power}")


def test_a_floor_in_one_state_does_not_refuse_a_claim_in_another():
    import tempfile
    print("\nslew: the pointer blind to the second slew, after a burst whose zoom was not measured")
    with tempfile.TemporaryDirectory() as td:
        north, layers, N = _two_field_clip(td, blind=True)
        found = slew.measure(north, layers, 1920, 1080, FPS, zoom=_zoom(N, verdict="unknown"), n_boot=100)
        old = slew.measure(north, layers, 1920, 1080, FPS, zoom=None, n_boot=100)
    f = found.fields
    st = {r["state"]: r for r in f["states"]}
    print(f"        (state 1: c {st[1]['c_px_per_deg']}, floor {st[1]['c_at_least_px_per_deg']})")
    check(st[0]["c_px_per_deg"] and abs(st[0]["c_px_per_deg"] / 500 - 1) < 0.03, "state 0's claim stands",
          f"{st[0]['c_px_per_deg']}; {found.no_power}")
    check(st[1]["c_at_least_px_per_deg"] is not None, "state 1 gives a floor", f"{st[1]['c_at_least_px_per_deg']}")
    check(not any("disagree" in w[1] for w in found.no_power), "no window of another state refuses it", f"{found.no_power}")
    print(f"        (taken as one field: {[w[1][:90] for w in old.no_power]})")


def test_a_window_given_across_a_step_is_refused():
    import tempfile
    print("\nslew: a window given by hand across the zoom")
    with tempfile.TemporaryDirectory() as td:
        north, layers, N = _two_field_clip(td)
        f = slew.measure(north, layers, 1920, 1080, FPS, windows=[(3.0, 32.0)], zoom=_zoom(N), n_boot=100).fields
    w = f["windows"][0]
    check(any("spans the burst" in x for x in w["no_power"]), "refused: it spans the step", f"{w['no_power'][:2]}")


def test_the_rates_find_a_lagging_pointer_and_a_turn_that_does_not_follow():
    print("\nslew: the pointer's rate against the scene's: a pointer drawn a frame late, and one that only curves slowly")
    rng = np.random.default_rng(8)
    n = np.arange(1, 301)
    t = (n - 1) / FPS
    extra = 1.5 * np.clip((t - 4) / 2, 0, 1)
    X = 1500.0 * extra + np.cumsum(rng.normal(0, 0.2, len(t)))
    late = 250.0 + 0.3 * t + np.r_[extra[0], extra[:-1]]           # the turn drawn one frame after the scene's
    seg = np.zeros(len(t), int)
    r = slew.rate_lag(t, late, X, seg, FPS)
    check(r["best_lag_frames"] == 1 and r["rate_r"] > 0.95, "a pointer drawn a frame late: best lag +1, r near 1",
          f"lag {r['best_lag_frames']}, r {r['rate_r']:.3f}, c at -1/0/+1 "
          f"{[round(r['c_at_lag'][L]) for L in (-1, 0, 1)]}")
    # PR076's case: the pointer only holds and curves slowly; the scene curves the same way (so a fit finds a c), but
    # moves on its own by more, every few seconds
    slow = 250.0 + 0.3 * t + 0.5 * ((t - 5) / 5) ** 2
    X2 = 750 * ((t - 5) / 5) ** 2 + 200 * np.sin(2 * np.pi * t / 3) + 150 * np.sin(2 * np.pi * t / 2.2)
    r = slew.rate_lag(t, slow, X2, seg, FPS)
    check(r["rate_r"] < slew.MIN_RATE_R, "a turn that curves slowly under a scene that wiggles: r under the bar",
          f"r {r['rate_r']:.2f}")


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
