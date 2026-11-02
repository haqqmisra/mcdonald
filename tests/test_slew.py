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
    try:                                                 # a zoom state shorter than the smoothing (PR40's, 2026-10-27)
        w = slew.slews(t[:5], np.array([0.0, 300.0, np.nan, 300.0, 0.0]), FPS)
        check(w == [], "a state of five frames: no slew, and no error", f"{w}")
    except Exception as e:
        check(False, "a state of five frames: no slew, and no error", repr(e))


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


def test_the_scene_from_blocks_only_when_asked():
    """`slew --scene-blocks` (2026-11-02, the maintainer's choice: on request, not unasked): a clip `layers` holds still is read by
    `mcdonald scene` in blocks of 60 frames, and those blocks, written as a `layers` CSV, give `slew` its scene. A block's velocity is
    held over its frames; a block that did not pass leaves a gap. With a pointer turning steadily and no hold, c comes back."""
    import csv
    import tempfile
    from mcdonald import scene
    print("\nslew: the scene from the block reading, when asked")
    c, rate = 1200.0, 0.6                                       # px/deg; deg/s
    with tempfile.TemporaryDirectory() as td:
        n = np.arange(1, 241)
        t = (n - 1) / FPS
        th = 10.0 + rate * t
        north = Path(td) / "b_north.csv"
        with open(north, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["frame", "t_s", "glyph_x", "glyph_y", "r_px", "theta_deg", "quality"])
            for i in range(len(n)):
                w.writerow([n[i], t[i], 960 + 300 * np.sin(np.radians(th[i])), 540 - 300 * np.cos(np.radians(th[i])), 300.0, th[i] % 360, 1.0])
        v = c * rate / FPS                                       # the scene's px/frame: the pointer turning one way moves it image-right
        blocks = [dict(start=1 + 60 * i, frames=60, vx=v, vy=0.0, down=3, changing=1.0, z=60.0, gain=4.0, gain_back=1.0, hold=0.3) for i in range(4)]
        blocks[2].update(z=5.0)                                 # one block that did not pass: a gap
        sc_csv, lay = Path(td) / "b_scene.csv", Path(td) / "b_scene_as_layers.csv"
        scene.write_csv(sc_csv, blocks)
        pairs = scene.as_layers(sc_csv, FPS, lay)
        fr, _, dx, dy, k, _ = slew.read_layers(lay)
        gap = (fr >= 121) & (fr < 181)
        inside = (fr < 116) & np.isfinite(dx)
        check(pairs == 3 * 55 and np.all(np.isnan(dx[gap])) and inside.sum() == 110 and np.allclose(dx[inside], v * 5, atol=0.01),
              "the blocks that passed become pairs at their velocity over 5 frames, inside each block; the one that did not is a gap",
              f"{pairs} pairs; a pair across two blocks' edge is left for slew to bridge")
        f = slew.measure(north, lay, 1920, 1080, FPS, windows=[(0.0, 3.8)], degree=0, n_boot=100).fields
        got = f["windows"][0].get("c_px_per_deg")
        check(got is not None and abs(got / c - 1) < 0.03, "and slew reads c from them as a chain", f"c {got} against {c}")
        passed = [dict(start=b["start"], frames=b["frames"], vx=b["best_vx_px_frame"], vy=b["best_vy_px_frame"]) for b in scene.read_csv(sc_csv) if b["passed"]]
        f = slew.measure(north, lay, 1920, 1080, FPS, degree=0, n_boot=100, blocks=passed).fields
        w = f["windows"][0]
        check(f["scene_from"] == "blocks" and w.get("from_blocks") and w["n"] == 3 and w.get("c_px_per_deg") is not None
              and abs(w["c_px_per_deg"] / c - 1) < 0.03 and f["c_px_per_deg"] is not None,
              "given the blocks themselves, the window is the whole state and the blocks' rule reads c from the three that passed",
              f"c {w.get('c_px_per_deg')} from {w['n']} blocks; {w['no_power']}")
        said = "\n".join(slew.said(f))
        check("blocks: 3 passed" in said and "3 blocks" in said, "and the stage says it in blocks", said.splitlines()[-6][:100])


def _drawn_blocks(n_blocks=30, c=1500.0, hold=0.2, step=0.18, follow=True, wander="smooth", v0=-20.0, amp=8.0, period_s=40.0, B=60,
                  solved=0.5, seed=0, trend_pointer=0.0):
    """Blocks of a scene whose velocity wanders, and a pointer that follows them at c under a hold (deg/s) -- or turns on its own, a
    wander of the same spectrum -- quantised to a grid of `step` deg with `solved` of its frames read. (rows for fit_blocks, sigma, step)."""
    rng = np.random.default_rng(seed)
    N = n_blocks * B
    t = np.arange(N) / FPS
    if wander == "ramp":
        v = v0 + amp * (t - t.mean()) / t.std()
    else:
        v = v0 + amp * np.sin(2 * np.pi * t / period_s + rng.uniform(0, 2 * np.pi))
    if follow:
        rate = hold / FPS + v / c
    else:
        rho = np.exp(-1 / (period_s / 4 * FPS))
        w, x = np.zeros(N), 0.0
        for i in range(N):
            x = rho * x + np.sqrt(1 - rho * rho) * rng.standard_normal()
            w[i] = x
        rate = hold / FPS + (amp / c) * w + trend_pointer * (t - t.mean()) / FPS
    theta = 100.0 + np.cumsum(rate)
    thq = np.round(theta / step) * step if step else theta
    keep = rng.uniform(size=N) < solved
    frames = np.arange(1, N + 1)[keep]
    sigma, st = slew.pointer_scatter(thq[keep], 300.0)
    blocks = [dict(start=1 + i * B, frames=B, vx=float(v[i * B:(i + 1) * B].mean()), vy=0.1 * float(v[i * B:(i + 1) * B].mean() - v0))
              for i in range(n_blocks)]
    return slew.block_rates(blocks, frames, thq[keep], sigma), sigma, st


def test_the_blocks_rule_reads_c_where_the_blocks_and_the_pointer_agree():
    """The block rule (method 41, 2026-11-02): a scene read 60 frames at a time, each block's velocity set against the pointer's rate
    over the same frames, in rates (the hold an offset, no stretches), the agreement tested against circular shifts of the pointer."""
    print("\nslew: the scene from blocks, the blocks' own rule")
    rows, sigma, st = _drawn_blocks()
    f = slew.fit_blocks(rows, sigma, 1, FPS, n_boot=200, step_deg=st)
    check(f["registered"] and not f["no_power"], "30 blocks following a pointer on a 0.18-deg grid with half its frames read: a claim",
          f"{f['no_power']}")
    check(abs(f["c_px_per_deg"] / 1500 - 1) < 0.08 and f["c_p16_p84"][0] < 1500 < f["c_p16_p84"][1] * 1.05, "c within 8 %, the truth near its 16-84 %",
          f"c {f['c_px_per_deg']:.0f}, 16-84 % {f['c_p16_p84'][0]:.0f}-{f['c_p16_p84'][1]:.0f}")
    check(f["shift_p"] <= slew.SHIFT_ALPHA and f["shift_reaching"] == 0, "no circular shift of the pointer reaches the true alignment's r",
          f"r {f['shift_r']:.2f}, the largest shift {f['shift_null_max']:.2f}")
    check(abs(f["hold_rate_deg_per_s"] - 0.2) < 0.05, "the hold comes back as the offset", f"{f['hold_rate_deg_per_s']:.3f} deg/s against 0.2")
    rows, sigma, st = _drawn_blocks(n_blocks=12)
    f = slew.fit_blocks(rows, sigma, 1, FPS, n_boot=200, step_deg=st)
    check(f["registered"] is False and f["no_power"] and "cannot show" in f["no_power"][0], "12 blocks, however well they follow: refused by name",
          f"{f['no_power'][0][:90]}")
    rows, sigma, st = _drawn_blocks(follow=False, seed=3)
    f = slew.fit_blocks(rows, sigma, 1, FPS, n_boot=200, step_deg=st)
    check(not f["registered"] and f.get("c_px_per_deg") is None, "a pointer wandering on its own: no c", f"{f['no_power'][:1]}")
    rows, sigma, st = _drawn_blocks(follow=False, wander="ramp", trend_pointer=1.0)
    f = slew.fit_blocks(rows, sigma, 1, FPS, n_boot=200, step_deg=st)
    check(bool(f["no_power"]) and f.get("degree_shift", 0) > slew.MAX_DEGREE_SHIFT,
          "a scene that ramps under a pointer that ramps on its own: the shifts cannot tell, the hold's steadiness refuses",
          f"r {f.get('shift_r', float('nan')):.2f}, c {f.get('c_px_per_deg')}, with a hold in t it moves {f.get('degree_shift', 0):.0%}")
    rows, sigma, st = _drawn_blocks(n_blocks=5, hold=0.0, step=0.0, solved=1.0)
    f = slew.fit_blocks(rows, sigma, 0, FPS, n_boot=200, step_deg=st)
    check(f["registered"] and not f["no_power"] and abs(f["c_px_per_deg"] / 1500 - 1) < 0.03,
          "a still platform (no hold, degree 0): five blocks with an exact pointer give c, no shift test needed",
          f"c {f.get('c_px_per_deg')}")
    uneven = [dict(r, resid_scatters=5.0) for r in rows[:3]] + rows[3:]
    f = slew.fit_blocks(uneven, sigma, 0, FPS, n_boot=200, step_deg=st)
    check(f["n"] == 2 and f["blocks_uneven"] == 3 and "unevenly" in f["no_power"][0], "a block where the pointer turned unevenly is left out, and said",
          f"{f['no_power'][0][:100]}")


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


def test_a_known_hold_lets_a_steady_pan_give_k():
    """PR051's NAR stretch (2026-10-27): the scene sweeps at a steady rate and the pointer turns at a steady rate on a
    moving platform, so the pan is the hold's twin and only a floor comes back; with the platform's share given
    (`--hold-rate`, from its velocity across the line of sight over the range) the pan is the lever."""
    import csv
    import tempfile
    print("\nslew: a steady pan of 0.15 deg/s on a platform whose own share is -0.07 deg/s, c 2200")
    rng = np.random.default_rng(9)
    k, c, hold, pan = 8, 2200.0, -0.07, 0.15
    n = np.arange(1, 601)
    t = (n - 1) / FPS
    th = 250.0 + (hold + pan) * t + rng.normal(0, 0.03, len(t))
    X = c * pan * t + np.cumsum(rng.normal(0, 0.3, len(t)))
    with tempfile.TemporaryDirectory() as td:
        north, layers = Path(td) / "h_north.csv", Path(td) / "h_layers.csv"
        with open(north, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["frame", "t_s", "glyph_x", "glyph_y", "r_px", "theta_deg", "quality"])
            for i in range(len(n)):
                w.writerow([n[i], t[i], 960 + 300 * np.sin(np.radians(th[i])), 540 - 300 * np.cos(np.radians(th[i])),
                            300.0, th[i] % 360, 1.0])
        with open(layers, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["frame", "t_s", f"all_dx{k}", f"all_dy{k}"])
            for i in range(len(n) - k):
                w.writerow([n[i], t[i], X[i + k] - X[i], 0.0])
        win = [(1.0, 18.0)]
        free = slew.measure(north, layers, 1920, 1080, FPS, win, n_boot=100).fields
        given = slew.measure(north, layers, 1920, 1080, FPS, win, n_boot=100, hold_rate=hold).fields
    check(not free["c_px_per_deg"], "the hold fitted: the steady pan is the hold's twin, no k",
          f"{free['c_px_per_deg']}, floor {free['c_at_least_px_per_deg']}")
    check(given["c_px_per_deg"] and abs(given["c_px_per_deg"] / c - 1) < 0.05, "the hold given: c comes back",
          f"{given['c_px_per_deg']} against {c:.0f}")
    check(any("--hold-rate" in a for a in given["assumes"]), "and the report says the hold was given")


def _bar_clip(td, k_deg=1650.0, seconds=60.0, every=75, kk=5, seed=3):
    """AARO's Puerto Rico geometry drawn (2026-10-29): an aircraft orbiting at 3 km and 100 m/s, 600 m up, its turret
    following a thing that drifts 7 m/s at 250 m; the display prints the aircraft's position and the line of sight's
    ground point every `every` frames, rounded to an arc-second, and the scene moves by the line of sight's turn against
    the ground, k cos(e) px a degree across and k a degree down. Writes the drift stage's platform and los files and a
    `layers` file; returns their paths and the median depression."""
    import csv
    rng = np.random.default_rng(seed)
    n = np.arange(1, int(seconds * FPS) + 2)
    t = (n - 1) / FPS
    w = 100.0 / 3000.0
    A = np.c_[3000 * np.cos(w * t + 0.3), 3000 * np.sin(w * t + 0.3), np.full(len(t), 600.0)]
    O = np.c_[300 - 6.4 * t, -200 - 3.6 * t, 250 - 0.6 * t]
    G = A + (A[:, 2] / (A[:, 2] - O[:, 2]))[:, None] * (O - A)      # where the line of sight meets the ground
    bearing = lambda v: np.degrees(np.arctan2(v[:, 0], v[:, 1]))
    dep = lambda v: np.degrees(np.arctan2(-v[:, 2], np.hypot(v[:, 0], v[:, 1])))
    wrap = lambda a: (a + 180) % 360 - 180
    e = dep(G - A)
    dpsi = wrap(bearing(G[1:] - A[1:]) - bearing(G[:-1] - A[1:]))    # the line of sight's turn against the ground
    ddep = dep(G[1:] - A[1:]) - dep(G[:-1] - A[1:])
    X = np.r_[0.0, np.cumsum(-k_deg * np.cos(np.radians(e[1:])) * dpsi)] + np.cumsum(rng.normal(0, 0.2, len(t)))
    Y = np.r_[0.0, np.cumsum(-k_deg * ddep)]
    lat0, lon0 = 18.5, -67.13
    m_lat = 111132.954 - 559.822 * np.cos(2 * np.radians(lat0))
    m_lon = 111412.84 * np.cos(np.radians(lat0)) - 93.5 * np.cos(3 * np.radians(lat0))
    sec = lambda v: np.round(v * 3600) / 3600                          # printed to an arc-second
    plat, los, lay = Path(td) / "platform.csv", Path(td) / "los.csv", Path(td) / "b_layers.csv"
    with open(plat, "w", newline="") as fp, open(los, "w", newline="") as fl:
        wp, wl = csv.writer(fp), csv.writer(fl)
        fp.write("# drawn: an orbit at 3 km\n")
        wp.writerow(["frame", "lat", "lon", "alt_m"])
        wl.writerow(["frame", "tgt_lat", "tgt_lon", "tgt_elev_m"])
        for i in range(0, len(n), every):
            wp.writerow([n[i], sec(lat0 + A[i, 1] / m_lat), sec(lon0 + A[i, 0] / m_lon), A[i, 2]])
            wl.writerow([n[i], sec(lat0 + G[i, 1] / m_lat), sec(lon0 + G[i, 0] / m_lon), 0.0])
    with open(lay, "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["frame", "t_s", f"all_dx{kk}", f"all_dy{kk}"])
        for i in range(len(n) - kk):
            wr.writerow([n[i], t[i], X[i + kk] - X[i], Y[i + kk] - Y[i]])
    return plat, los, lay, float(np.median(e))


def test_a_data_bar_in_place_of_the_pointer_gives_k_round_an_orbit():
    """AARO's Puerto Rico clip (2026-10-29): the display prints the aircraft's position and the line of sight's ground
    point, not a pointer the stage can read, and the aircraft orbits while the turret follows the lanterns, so a hold
    fitted as a steady rate cannot be the platform's share (the north arrow read 6 times low and was refused). From the
    bar the share is known frame by frame -- the ground the boresight was on, seen from where the aircraft has got to --
    and so is the depression: k comes back from a steady follow round the orbit."""
    import tempfile
    print("\nslew: a data bar (the aircraft's position and the ground point every 2.5 s, to an arc-second) round an orbit")
    with tempfile.TemporaryDirectory() as td:
        plat, los, lay, e = _bar_clip(td)
        bar = slew.bar_series(plat, los)
        f = slew.measure(None, lay, 1920, 1080, FPS, [(3.0, 57.0)], n_boot=100, bar=bar).fields
    w = f["windows"][0]
    check(bar["hold"] is not None and abs(bar["grain_m"] - 29.3) < 1.5, "the bar gives the hold, and its grain is an arc-second",
          f"grain {bar['grain_m']:.1f} m")
    check(f["k_px_per_deg"] is not None and abs(f["k_px_per_deg"] / 1650 - 1) < 0.04, "k comes back within 4 %",
          f"{f['k_px_per_deg']} against 1650; c {f['c_px_per_deg']}, {w['no_power']}")
    check(f["depression_from"] and "data bar" in f["depression_from"] and abs(f["depression_deg"] - e) < 0.5,
          "the depression is the bar's", f"{f['depression_deg']:.2f} against {e:.2f}")
    check(f["assumes"][0] == slew.BAR_GIVEN and f["degree"] == 0, "no hold fitted, and the report says the bar gave it")
    check(f["pointer"]["bar"] and "pointer convention" not in str(slew.said(f)), "said as the bar, not as a pointer",
          slew.said(f)[0][:90])
    import csv
    with tempfile.TemporaryDirectory() as td:            # the same bar with only the azimuth and depression printed
        plat, los, lay, e = _bar_clip(td)
        rows = list(csv.DictReader(open(los)))
        fr, A, G, az, dep = slew.read_bar(plat, los)
        with open(los, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["frame", "az_deg", "dep_deg"])
            for i, r in enumerate(rows):
                w.writerow([r["frame"], round(float(az[i]), 1), round(float(dep[i]), 1)])
        bar2 = slew.bar_series(plat, los)
        f2 = slew.measure(None, lay, 1920, 1080, FPS, [(3.0, 57.0)], n_boot=100, bar=bar2).fields
    check(bar2["hold"] is None and abs(bar2["step_deg"] - 0.1) < 1e-6 and f2["degree"] == 1 and f2["assumes"][0] == slew.BAR_AZIMUTH,
          "with only the azimuth printed (to 0.1 deg) the bar is a pointer, and the hold is fitted",
          f"step {bar2['step_deg']}, degree {f2['degree']}")


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
        found = slew.measure(north, layers, 1920, 1080, FPS, zoom=_zoom(N), n_boot=100, out=str(Path(td) / "c"))
        f = found.fields
        one = slew.measure(north, layers, 1920, 1080, FPS, zoom=None, n_boot=100).fields
        png = [x for x in found.files if str(x).endswith(".png")]
        try:
            from PIL import Image
            h = Image.open(png[0]).size[1] if png else 0
        except ImportError:
            h = None
        check(h is None or abs(h / (110 * 2.9 * 3) - 1) < 0.15, "the figure: the clip, then a row for each state",
              f"{h} px tall, against {110 * 2.9 * 3:.0f} for three rows")
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
