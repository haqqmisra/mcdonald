"""Checks for `mcdonald tether`: a hanging point's period gives its line, a planted
companion is told from the frame and the scene, the overlay's strokes are masked and a
dark line is not, repeated frames stay out of the series, and a short window is
tentative; a slow wander is not a swing; and, on drawn clips, a companion is re-found
where it hangs past a stronger spot going by, a pendulum is followed along its swing,
and nothing tied leaves no swing in the record. Portable: no video data.

    python3 tests/test_tether.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from mcdonald import tether  # noqa: E402

RNG = np.random.default_rng(20261006)
FAIL = []
WANDER_SEED = 2          # the drawn wander of test_a_slow_wander_is_not_a_swing: the cycles rule alone reads 2.12 m off it


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


def test_a_small_stack_is_read_too():
    """0.5.2. An object given as under 5 px makes a stack narrower than the 200 px the size and the extent were read
    over (the stack reaches 42 object sizes), and both raised: the stage ended as "no power" on a marked object that
    small. Found on the null tracks of PR097 object 6, 4 px."""
    print("a stack narrower than 200 px is read, not refused")
    m, cnt, _ = planted_stack(R=150, size=12.0, companion=(-10, 60))
    size = tether.object_size(m, cnt, 150)
    ext = tether.object_extent(m, cnt, 150, size or 12.0)
    check(size is not None and abs(size - 12.0) < 4.0 and 4.0 <= ext <= 12.0, "its size and its extent are read", f"{size} px, reaching {ext:.1f} px")


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


def wander_series(seed, seconds=10.0, tau=1.0, sd_deg=5.0, fps=30.0, sep_px=100.0, noise_deg=0.3, swing=None):
    """A track and a companion sep_px below it whose angle wanders slowly: an Ornstein-Uhlenbeck series of sd_deg and
    correlation time tau (s), with reading noise on it; `swing` (amplitude in degrees, period in s) puts a pendulum on top."""
    rng = np.random.default_rng(seed)
    n = int(seconds * fps)
    a = np.exp(-1 / (fps * tau))
    e = rng.standard_normal(n)
    y = np.empty(n)
    y[0] = e[0]
    for q in range(1, n):
        y[q] = a * y[q - 1] + np.sqrt(1 - a * a) * e[q]
    ang = sd_deg * y + noise_deg * rng.standard_normal(n)
    if swing:
        ang = ang + swing[0] * np.sin(2 * np.pi * np.arange(n) / fps / swing[1] + 0.7)
    track = {i + 1: (600.0, 300.0) for i in range(n)}
    comp = {i + 1: (600 + sep_px * np.sin(np.radians(v)), 300 + sep_px * np.cos(np.radians(v)), -30.0) for i, v in enumerate(ang)}
    return track, comp


def test_a_slow_wander_is_not_a_swing():
    """0.5.2 (H2). An angle that only wanders shows a cycle or two in a short window most of the time, and the cycles
    rule alone read a pendulum off it: 2.0 m on AARO's known balloon PR-004, 9.71 m and 2.52 m on two birds of the
    released reference reports. The wander null refuses it; a pendulum under the same wander is kept."""
    print("a slow wander is not a swing")
    track, comp = wander_series(WANDER_SEED)
    keep, tether.WANDER_P = tether.WANDER_P, 2.0                 # the cycles rule alone, as 0.5.1 had it
    old = tether.swing(track, comp, 30.0)
    tether.WANDER_P = keep
    check(old["swings"] is True, "the cycles rule alone calls this wander a pendulum",
          f"{old.get('period_used_s', 0):.2f} s over {old.get('cycles', 0):.1f} cycles, {old.get('line_length_m', 0):.2f} m")
    sw = tether.swing(track, comp, 30.0)
    w = sw.get("wander") or {}
    check(sw["swings"] is False and sw["line_length_m"] is None and w.get("p", 0) > tether.WANDER_P,
          "the wander null refuses it: no swing, no length", f"p = {w.get('p')}: {sw['finding'][:120]}")
    check(sw.get("period_refused_s") and "period_used_s" not in sw and "slow wander" in sw["finding"],
          "and the record says which period was refused, and why")
    track, comp = wander_series(WANDER_SEED, sd_deg=2.0, swing=(8.0, 3.2))
    sw = tether.swing(track, comp, 30.0)
    check(sw["swings"] is True and abs(sw["period_used_s"] - 3.2) < 0.16 and sw["wander"]["p"] <= tether.WANDER_P,
          "a pendulum under the same wander is kept, at its period", f"{sw.get('period_used_s')} s, p = {(sw.get('wander') or {}).get('p')}")


def test_a_companion_above_the_object_does_not_wrap():
    """A companion straight above the object sits at +-180 degrees: its angle is read about its mean direction."""
    print("a companion straight above the object")
    track, comp, T = pendulum_series(1.5)
    up = {n: (2 * track[n][0] - x, 2 * track[n][1] - y, c) for n, (x, y, c) in comp.items()}
    sw = tether.swing(track, up, 29.97)
    check(sw["swings"] is True and abs(sw["period_used_s"] - T) < 0.05 * T and sw["angle_sd_deg"] < 15,
          "its swing is read as the same pendulum's", f"{sw.get('period_used_s')} s, angle sd {sw['angle_sd_deg']:.1f} deg")


def test_followed_how_tells_the_object_from_the_scene_and_the_screen():
    """What is tied to the object makes none of the scene's motion against it; a piece of the scene makes all of it;
    what stays put on the screen makes all of the screen's. Places are regressed, not steps: a tied companion read
    with the track's own error against a scene that hardly moves is still tied."""
    print("re-found, a feature is the object's, the scene's or the screen's")
    rng = np.random.default_rng(3)
    ns = list(range(1, 201))
    track = {n: (300 + 0.8 * n + rng.normal(0, 0.3), 200 + 0.2 * n + rng.normal(0, 0.3)) for n in ns}
    true = {n: (300 + 0.8 * n, 200 + 0.2 * n) for n in ns}
    bg = {n: (1.5 * (n - 1), 0.0) for n in ns}                       # the scene slides 1.5 px a frame on the screen
    runs = {n: 1 for n in ns}
    tied = {n: (true[n][0] + 5 + rng.normal(0, 0.2), true[n][1] + 40 + rng.normal(0, 0.2)) for n in ns}
    scene = {n: (420 + 1.5 * (n - 1) + rng.normal(0, 0.2), 260 + rng.normal(0, 0.2)) for n in ns}
    screen = {n: (500 + rng.normal(0, 0.2), 300 + rng.normal(0, 0.2)) for n in ns}
    a, b, c = (tether.followed_how(ns, g, runs, track, bg) for g in (tied, scene, screen))
    check(abs(a["scene_share"]) < 0.05 and abs(a["screen_share"]) < 0.05 and a["followed_jitter_px"] < 0.6,
          "tied to the object: none of the scene's motion, none of the screen's", f"{a['scene_share']:+.2f}, {a['screen_share']:+.2f}")
    check(abs(b["scene_share"] - 1) < 0.05 and b["scene_moved_px"] > 100, "a piece of the scene: all of the scene's",
          f"{b['scene_share']:+.2f} over {b['scene_moved_px']:.0f} px")
    check(abs(c["screen_share"] - 1) < 0.05 and c["screen_moved_px"] > 100, "a mark on the screen: all of the screen's",
          f"{c['screen_share']:+.2f} over {c['screen_moved_px']:.0f} px")
    slow = {n: (0.8 * (n - 1) + 0.02 * n, 0.2 * (n - 1)) for n in ns}  # a scene that moves with the object, 4 px in all
    d = tether.followed_how(ns, tied, runs, track, slow)
    check(d["scene_moved_px"] < tether.STILL and abs(d["screen_share"]) < 0.05,
          "against a scene that hardly moves the question has no power, and is not answered 'scene'",
          f"the scene moved {d['scene_moved_px']:.0f} px; share {d['scene_share']:+.2f}")
    half = dict(list(tied.items())[::2])
    e = tether.followed_how(ns, half, runs, track, bg, repeats=ns[1::2])
    check(abs(e["followed_on"] - 1.0) < 1e-9 and e["followed_frames"] == 100, "repeated frames are left out of the count",
          f"{e['followed_on']:.2f} of the frames that are not repeats")


class Drawn:
    """A clip of drawn grey frames, as the stage reads one."""

    def __init__(self, frames, fps=30.0):
        self.frames, self.fps = frames, fps
        self.n0, self.n1 = min(frames), max(frames)
        self.H, self.W = next(iter(frames.values())).shape

    def rgb(self, n):
        g = self.frames[n]
        return np.dstack([g, g, g])

    def masks(self):
        z = np.zeros((self.H, self.W), bool)
        return dict(blocks=z, graphics=z.copy(), colour=True)


def drawn(seed=5, n=150, W=480, H=360, hang=(4.0, 40.0), swing_deg=0.0, period_s=2.0, passer=None, companion=True, fps=30.0):
    """(clip, track): the object, a bright blob moving 0.9, 0.25 px a frame across a textured scene that slides 1.5 px
    a frame under it; a dark dot `hang` px from the object, swinging `swing_deg` about that direction every `period_s`;
    and `passer`, (how close in px, on which frame): a darker dot fixed in the scene that passes that close to where
    the dot hangs."""
    from scipy.ndimage import gaussian_filter
    rng = np.random.default_rng(seed)
    big = gaussian_filter(rng.normal(0, 1, (H + 40, W + 2 * n + 80)), 2.5) * 55
    yy, xx = np.mgrid[0:H, 0:W]
    frames, track = {}, {}
    r0, a0 = np.hypot(*hang), np.arctan2(hang[0], hang[1])
    for i in range(n):
        sx = int(round(1.5 * i))
        g = 130 + big[20:20 + H, 40 + 2 * n - sx:40 + 2 * n - sx + W].copy()
        ox, oy = 150 + 0.9 * i, 120 + 0.25 * i
        g += 95 * np.exp(-0.5 * ((xx - ox) ** 2 + (yy - oy) ** 2) / 3.0 ** 2)
        if companion:
            a = a0 + np.radians(swing_deg * np.sin(2 * np.pi * i / (period_s * fps) + 0.6))
            g -= 70 * np.exp(-0.5 * ((xx - ox - r0 * np.sin(a)) ** 2 + (yy - oy - r0 * np.cos(a)) ** 2) / 1.6 ** 2)
        if passer:                                   # fixed in the scene: against the object it moves 0.6, -0.25 px a frame
            miss, at = passer
            px, py = ox + hang[0] + 0.6 * (i - at) - miss * 0.385, oy + hang[1] - 0.25 * (i - at) - miss * 0.923
            g -= 110 * np.exp(-0.5 * ((xx - px) ** 2 + (yy - py) ** 2) / 1.6 ** 2)
        g += rng.normal(0, 1.5, g.shape)
        frames[i + 1] = np.clip(np.rint(g), 0, 255).astype(np.uint8)
        track[i + 1] = (ox + rng.normal(0, 0.15), oy + rng.normal(0, 0.15))
    return Drawn(frames, fps), track


def _stage(**kw):
    clip, track = drawn(**kw)
    return tether.measure(clip, track, masks=clip.masks(), say=lambda line: None, procs=0).fields, track


def test_a_spot_passing_by_does_not_take_the_follower():
    """0.5.2 (H1). 0.5.1's follower moved its gate to whatever it last found, and took the strongest feature in it: a
    stronger spot of the scene passing the companion carried it off (PR105: 14 to 1,290 px from the object), and the
    swing was read off that. Now the companion is re-found from the stack's offset, the nearest to where it was, and
    never past its leash; where a spot passes right over it, the pass made in reverse has it on the other side."""
    print("a stronger spot passing the companion does not take the follower")
    for name, passer in (("9 px from it", (9.0, 75)), ("right over it", (0.0, 75))):
        f, track = _stage(passer=passer)
        c, sw = f["companion"], f["swing"]
        ok = c is not None and abs(c["dx_px"] - 4) <= 2 and abs(c["dy_px"] - 40) <= 2
        check(ok and c["followed_on"] > 0.95 and c["followed_jitter_px"] < 1.0 and abs(c["scene_share"]) < 0.1,
              f"a darker spot passing {name}: the companion is re-found on nearly every frame, where it hangs",
              "" if c is None else f"on {100 * c['followed_on']:.0f}% to {c['followed_jitter_px']:.2f} px, {c['scene_share']:+.2f} of the scene's motion")
        check(sw is not None and sw["swings"] is False and sw["separation_range_px"][1] < 46 and sw["angle_sd_deg"] < 3,
              f"a darker spot passing {name}: it is never followed away, and its angle holds",
              "" if sw is None else f"{sw['separation_range_px'][0]:.0f}-{sw['separation_range_px'][1]:.0f} px from the object, +-{sw['angle_sd_deg']:.1f} deg")


def test_a_drawn_pendulum_is_followed_and_read():
    """A dot swinging 12 degrees every 2 s under the object smears on the stack, and is at the stack's offset on half
    the frames: re-found from there along its swing, it is seen on all of them, and gives its period."""
    print("a drawn pendulum is followed along its swing")
    f, track = _stage(swing_deg=12.0, n=180)
    c, sw = f["companion"], f["swing"]
    check(c is not None and c["followed_on"] > 0.95 and (c["seen_on_frames"] or 0) < 0.8,
          "seen on every frame along its swing, though on fewer at the stack's own offset",
          "" if c is None else f"re-found on {100 * c['followed_on']:.0f}%, at the offset on {100 * (c['seen_on_frames'] or 0):.0f}%")
    check(sw is not None and sw["swings"] is True and abs(sw["period_used_s"] - 2.0) < 0.06 and sw["wander"]["p"] <= tether.WANDER_P,
          "and its period is the pendulum's, past the wander null", "" if sw is None else f"{sw.get('period_used_s')} s, p = {(sw.get('wander') or {}).get('p')}")
    # The same stage with its frames read, weighed and measured on threads (2026-11-13: each frame's own arithmetic in
    # the thread that read it, the two stacks beside each other, the background's steps beside the pass): every
    # number of the record, to the last bit, is what one thread gives.
    import json
    clip, track = drawn(swing_deg=12.0, n=180)
    on_threads = tether.measure(clip, track, masks=clip.masks(), say=lambda line: None, procs=4).fields
    same = json.dumps(on_threads, sort_keys=True, default=repr) == json.dumps(f, sort_keys=True, default=repr)
    check(same, "read and measured on four threads, the record is the same to the last bit as in one",
          "" if same else str([k for k in f if repr(f[k]) != repr(on_threads.get(k))][:6]))
    seen = []
    frames = tether.Frames(clip, clip.masks(), track, 60, cache=False, procs=4)
    got = list(frames.each(sorted(track)[:40], also=lambda n, g, bad: (seen.append(n), float(g.sum()))[1]))
    one = [(n, *frames(n)) for n in sorted(track)[:40]]
    check([q[0] for q in got] == sorted(track)[:40] and all(np.array_equal(a_[1], b_[1]) and np.array_equal(a_[2], b_[2])
                                                           and a_[3] == float(b_[1].sum()) for a_, b_ in zip(got, one))
          and sorted(seen) == sorted(track)[:40],
          "`Frames.each` gives the frames in order with what `also` made of each, whichever thread read it",
          f"{len(got)} frames, {len(seen)} computed")


def test_nothing_tied_leaves_no_swing_and_says_where_it_looked():
    """0.5.2 (H1, H4). Where nothing is tied the record holds no swing (0.5.1 kept a refused candidate's: PR149's said
    `swings: true`, 0.159 m, beside "nothing tied"), and the finding says the ring it was said of, in pixels: nearer
    in is the object's own picture, and was not searched."""
    print("nothing tied: no swing in the record, and the ring that was searched")
    for name, kw in (("an empty scene", dict(companion=False)), ("a spot of the scene passing the place", dict(companion=False, passer=(0.0, 75)))):
        f, track = _stage(**kw)
        a, b = f["searched_px"]
        check(f["companion"] is None and f["swing"] is None, f"{name}: no companion, and no swing in the record", f["finding"][:100])
        check(f"between {a:.0f} and {b:.0f} px of it" in f["finding"] and f"nearer than {a:.0f} px" in f["finding"] and 10 < a < 40 < b,
              f"{name}: the finding says the ring it searched", f"{a:.0f} to {b:.0f} px")


def main():
    for t in (test_a_swinging_point_gives_its_line, test_a_steady_line_gives_no_length,
              test_too_few_cycles_are_not_a_period, test_repeated_frames_are_left_out,
              test_a_slow_wander_is_not_a_swing, test_a_companion_above_the_object_does_not_wrap,
              test_a_companion_is_told_from_the_control, test_the_object_size_is_read_off_the_stack,
              test_a_small_stack_is_read_too,
              test_the_objects_own_glints_are_inside_its_extent, test_the_overlays_strokes_are_masked_and_a_dark_line_is_not,
              test_followed_how_tells_the_object_from_the_scene_and_the_screen,
              test_a_spot_passing_by_does_not_take_the_follower, test_a_drawn_pendulum_is_followed_and_read,
              test_nothing_tied_leaves_no_swing_and_says_where_it_looked):
        t()
    print(f"\n{'OK' if not FAIL else 'FAILED'}: {len(FAIL)} failing check(s)" + ("" if not FAIL else "\n  " + "\n  ".join(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
