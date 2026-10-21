"""Does the zoom fit find a step of scale across a blank, and say "unknown" where it cannot?

Rendered scenes only, small and quick: one textured ground seen at two magnifications, the later frame's view moved
on by hundreds of pixels (AARO's Puerto Rico clip moved 300-400 px during each blank), under an overlay drawn the way
the MTS-B draws it -- a cyan reticle and glyph, black redaction boxes, white text -- and, where asked, a sensor's fixed
pattern (a vignette ring and column stripes) that does not move with the scene. Each trap of handoff-zoom-slew.md is
a check: the overlay must not match itself at x1, a blank frame must not fit, a scale on the grid's edge is no number,
and a featureless scene behind a fixed pattern must come out "unknown", never "no step".

    python3 tests/test_zoom.py        # or: pytest tests/

No video data needed.
"""
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import forensics as vf  # noqa: E402
from mcdonald import zoom  # noqa: E402

FAIL = []
W, H = 640, 360
FPS = 30.0


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def texture(size=1800, seed=7):
    """Ground with detail at every scale from 1 px to 40 (each band's amplitude growing with its size), mean 110."""
    rng = np.random.default_rng(seed)
    t = np.zeros((size, size), np.float32)
    for s, a in ((1.0, 5), (2.5, 8), (6, 12), (15, 16), (40, 20)):
        n = ndimage.gaussian_filter(rng.normal(size=(size, size)).astype(np.float32), s)
        t += a * n / n.std()
    return t


TEX = texture()
YY, XX = np.mgrid[:H, :W].astype(np.float32)
R = np.hypot(XX - W / 2, YY - H / 2) / (H / 2)
RING = (0.35 * np.exp(-((R - 0.95) / 0.08) ** 2)).astype(np.float32)      # a vignette's bright ring
STRIPES = np.random.default_rng(11).normal(0, 3.0, W).astype(np.float32)[None, :] * np.ones((H, 1), np.float32)


def render(m, cx, cy, amp=1.0, fixed=0.0, seed=0):
    """The ground at magnification m about texture point (cx, cy), its detail scaled by `amp`, plus `fixed` times the
    sensor's pattern, plus a grey level of noise. Returns (grey, colour cast) with the overlay drawn."""
    x = cx + (XX - W / 2) / m
    y = cy + (YY - H / 2) / m
    g = 110 + amp * ndimage.map_coordinates(TEX, [y, x], order=1, mode="reflect")
    g = g + fixed * (60 * RING + STRIPES) + np.random.default_rng(seed).normal(0, 1.0, g.shape)
    return overlay(np.clip(g, 9, 246).astype(np.float32))


def overlay(g):
    """The MTS-B's overlay on a frame: a cyan reticle and a cyan glyph (grey 170, a colour cast), two black boxes and
    a white line of text, all at fixed places."""
    g = g.copy()
    col = np.zeros(g.shape, bool)
    cx, cy = W // 2, H // 2
    for a, b in ((slice(cy - 1, cy + 2), slice(cx - 60, cx - 12)), (slice(cy - 1, cy + 2), slice(cx + 12, cx + 60)),
                 (slice(cy - 60, cy - 12), slice(cx - 1, cx + 2)), (slice(cy + 12, cy + 60), slice(cx - 1, cx + 2)),
                 (slice(40, 58), slice(500, 512)), (slice(40, 43), slice(500, 520)), (slice(55, 58), slice(508, 520))):
        g[a, b] = 170.0
        col[a, b] = True
    g[290:340, 30:200] = 0.0
    g[20:60, 560:630] = 0.0
    g[330:338, 250:420] = 255.0
    return g, col


def blank(level, seed=5):
    g = np.full((H, W), float(level), np.float32) + np.random.default_rng(seed).normal(0, 1.0, (H, W)).astype(np.float32)
    return overlay(g)


def fixed_of(m, cx, cy, amp=1.0, fixed=1.0, n=10):
    """A stretch's fixed pattern from n frames of the same optics, the view drifting 25 px a frame."""
    sc, ms = [], []
    for i in range(n):
        g, col = render(m, cx + 25 * i / m, cy - 12 * i / m, amp, fixed, seed=100 + i)
        mk = vf.zoom_mask(g, col)
        sc.append(vf.zoom_scene(g, mk))
        ms.append(mk)
    return vf.zoom_fixed(sc, ms)


def fit(before, after, **kw):
    r = vf.zoom_fit_frames(before, after, **kw)
    r.pop("scores")
    return r


def test_a_step_of_two_under_the_overlay_with_the_view_moved_on():
    print("\nzoom: x2 across a blank, the view moved 160 px across and 90 down meanwhile, under the overlay")
    r = fit(render(1.0, 900, 900), render(2.0, 1060, 990, seed=1))
    check(r["verdict"] == "step", "a step", f"{r['verdict']} {r['why']}")
    check(abs(r["s"] / 2.0 - 1) < 0.02, "x2.00 within 2 %", f"x{r['s']:.3f}, ZNCC {r['zncc']:.2f} (at x1 {r['zncc_at_1']:.2f}); {r['prominence']:.1f} MADs (x1 {r['prominence_at_1']:.1f})")
    check(abs(r["centre"][0] - (W / 2 + 160)) < 8 and abs(r["centre"][1] - (H / 2 + 90)) < 8,
          "the narrower frame's middle lands where the view moved to", f"{np.round(r['centre'], 1)}")


def test_a_zoom_out_by_three():
    print("\nzoom: out by 3 (the later frame the wider), the view moved 300 px")
    r = fit(render(3.0, 900, 900), render(1.0, 1000, 900, seed=1))
    check(r["verdict"] == "step" and abs(r["s"] * 3.0 - 1) < 0.02, "x1/3 within 2 %",
          f"{r['verdict']} x{r['s']:.4f} = 1/{1 / r['s']:.3f}, ZNCC {r['zncc']:.2f}")


def test_no_step_when_the_optics_held():
    print("\nzoom: the same field either side (a gain reset), the view moved 130 px across and 40 up (a fifth of the "
          "picture's width, as on AARO's Puerto Rico clip)")
    b, a = (1.5, 900, 900), (1.5, 900 + 130 / 1.5, 900 - 40 / 1.5)
    r = fit(render(*b), render(*a, seed=1), fixed_before=fixed_of(*b), fixed_after=fixed_of(*a))
    check(r["verdict"] == "no step", "no step", f"{r['verdict']} x{r['s']:.3f} {r['why']}")
    check(abs(r["s"] - 1) < 0.01, "x1.00 within 1 %", f"x{r['s']:.4f}, ZNCC {r['zncc']:.2f}, {r['prominence']:.1f} MADs against {r['prominence_off']:.1f} off it")
    r = fit(render(*b), render(*a, seed=1))
    check(r["verdict"] == "unknown", "without a stretch to take the fixed pattern out, x1 is not an answer",
          f"{r['verdict']}: {r['why']}")


def test_the_overlay_does_not_match_itself():
    print("\nzoom: a scene against a blank white frame, and two blank grey frames, both under the same overlay")
    r = fit(render(1.0, 900, 900), blank(240))
    check(r["verdict"] == "unknown", "scene against white: unknown", f"{r['verdict']} x{r['s']:.2f} ZNCC {r['zncc']:.2f}")
    r = fit(blank(120), blank(125, seed=6))
    check(r["verdict"] == "unknown", "overlay alone: unknown, not x1", f"{r['verdict']} x{r['s']:.2f} ZNCC {r['zncc']:.2f}")


def test_featureless_haze_behind_a_fixed_pattern_is_unknown():
    print("\nzoom: x2 over haze (a twentieth of the ground's detail) behind a vignette ring and column stripes")
    b, a = render(1.0, 900, 900, amp=0.05, fixed=1.0), render(2.0, 1000, 950, amp=0.05, fixed=1.0, seed=1)
    naive = fit(b, a)
    print(f"        (the pattern left in: x{naive['s']:.2f} at ZNCC {naive['zncc']:.2f} -- the trap, called "
          f"{naive['verdict']} for want of a stretch to take the pattern out)")
    check(naive["verdict"] != "no step", "the pattern left in: not called \"no step\"", naive["verdict"])
    r = fit(b, a, fixed_before=fixed_of(1.0, 900, 900, 0.05), fixed_after=fixed_of(2.0, 1000, 950, 0.05))
    check(r["verdict"] == "unknown", "the pattern taken out: unknown, never \"no step\"",
          f"{r['verdict']} x{r['s']:.2f} ZNCC {r['zncc']:.2f} (fixed share {np.round(r['fixed_share'], 2)}); {r['why']}")


def test_a_fixed_pattern_over_a_good_scene_does_no_harm():
    print("\nzoom: x2 over a textured ground with the same fixed pattern, taken out")
    r = fit(render(1.0, 900, 900, fixed=1.0), render(2.0, 1000, 950, fixed=1.0, seed=1),
            fixed_before=fixed_of(1.0, 900, 900), fixed_after=fixed_of(2.0, 1000, 950))
    check(r["verdict"] == "step" and abs(r["s"] / 2 - 1) < 0.02, "x2.00 within 2 %",
          f"{r['verdict']} x{r['s']:.3f} ZNCC {r['zncc']:.2f} (fixed share {np.round(r['fixed_share'], 2)})")


def test_a_scale_past_the_grid_is_not_a_number():
    print("\nzoom: x10 (past the grid's x8)")
    r = fit(render(1.0, 900, 900), render(10.0, 920, 910, seed=1))
    check(r["verdict"] == "unknown", "unknown", f"{r['verdict']} x{r['s']:.2f} ZNCC {r['zncc']:.2f}; {r['why']}")


def series_with_bursts(bursts, n=900, settle=8):
    """A scan's columns (frame, change, contrast, level): contrast 20 and change 1.5 between bursts; contrast 2 in a
    burst; for `settle` frames after one, the level climbing back (change 6 falling to 1.5)."""
    rows = []
    for f in range(1, n + 1):
        d, sd = 1.5, 20.0
        for a, b in bursts:
            if a <= f <= b:
                d, sd = 25.0, 2.0
            elif b < f <= b + settle:
                d = 1.5 + 6.0 * (b + settle + 1 - f) / settle
        rows.append((f, d, sd, 100.0))
    return np.array(rows, float)


def test_bursts_close_together_are_one_change_and_edges_wait_for_the_gain():
    print("\nzoom: three bursts within half a second, then one alone; the gain settling over 8 frames after each")
    s = series_with_bursts([(300, 303), (308, 309), (313, 316), (600, 610)])
    b = zoom.bursts(s, FPS)
    check(b == [(300, 316), (600, 610)], "merged into one, the lone one kept", f"{b}")
    before, after, q = zoom.edges(s, 300, 316, FPS)
    check(before is not None and before <= 297, "the last good frame is before the burst", f"{before}")
    check(after is not None and 316 + 8 - 2 <= after <= 316 + 12, "the first settled frame waits for the gain",
          f"{after} (the gain settles by {316 + 8})")


def test_a_blank_that_keeps_its_contrast_is_found_by_its_level():
    print("\nzoom: three dark frames with their contrast intact, then one white (AARO's Puerto Rico switches)")
    s = series_with_bursts([], n=600)
    s[300:303, 3] = 20.0                                 # frames 301-303 dark: the level drops 80, the contrast stays
    s[300, 1], s[303, 1] = 120.0, 120.0
    s[303, 3], s[303, 2], s[304, 1] = 200.0, 2.0, 100.0  # frame 304 white and flat
    s[304, 3] = 100.0
    b = zoom.bursts(s, FPS)
    check(b == [(301, 305)], "one burst from the first dark frame to the last jump", f"{b}")


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
