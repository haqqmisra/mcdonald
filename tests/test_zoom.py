"""Does the zoom fit find a step of scale across a blank, and say "unknown" where it cannot?

Rendered scenes only, small and quick: one textured ground seen at two magnifications, the later frame's view moved
on by hundreds of pixels (AARO's Puerto Rico clip moved 300-400 px during each blank), under an overlay drawn the way
the MTS-B draws it -- a cyan reticle and glyph, black redaction boxes, white text -- and, where asked, a sensor's fixed
pattern (a vignette ring and column stripes) that does not move with the scene. Each trap of docs/history/handoff-zoom-slew.md is
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
    # a frame flat over part of it (a title card's, a black bar's): the window's variance there is rounding in float32,
    # and it made the card "match" at ZNCC 1551 on PR051's upload (2026-10-27)
    def part_flat(m, cx, cy, cols=True, level=128.0, seed=0):
        g, _ = render(m, cx, cy, seed=seed)
        g = g.copy()
        if cols:
            g[:, W // 3:] = level
        else:
            g[H // 2:, :] = level
        return overlay(g)
    for a, b, want, what in ((render(1.0, 900, 900), part_flat(2.0, 950, 920), 2.0, "x2 to a frame two-thirds flat"),
                             (part_flat(1.0, 900, 900, cols=False, level=40.0), render(3.0, 950, 920, seed=1), 3.0,
                              "x3 from a frame half flat")):
        r = vf.zoom_fit_frames(a, b)
        z = [v[0] for v in r["scores"].values()] + [r["zncc"], r["zncc_at_1"]]
        check(max(abs(v) for v in z) <= 1.0 + 1e-6 and (r["verdict"] == "unknown" or (
            r["verdict"] == "step" and abs(r["s"] / want - 1) < 0.02)),
            f"{what}: every ZNCC within 1, and the right step or unknown",
            f"{r['verdict']} x{r['s']:.3f} ZNCC {r['zncc']:.2f}, the largest on the grid {max(z):.2f}")


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


def test_a_marginal_fit_needs_two_pairs_further_out_that_pass_on_their_own():
    print("\nzoom: a fit that fails only its lead, fitted again from the pairs 1-3 frames further out")
    base = dict(verdict="unknown", s=0.323, zncc=0.22, zncc_at_1=0.05, prominence=10.7, prominence_at_1=3.0,
                prominence_off=9.4, at_edge=False, centre=[0.0, 0.0], fixed_share=[0.2, 0.3],
                why="x0.32 does not lead the best scale a quarter or more from it")
    todo = [dict(frames=[100, 103], kind="blank", before=97, after=110, fixed_before=None, fixed_after=None)]
    real = zoom.fit_all

    def with_pairs(results):
        zoom.fit_all = lambda video, extra, *a, **k: [dict(base, **r) for r in results[:len(extra)]]
        try:
            return zoom.confirm("v", todo, [dict(base)], n_last=500)[0]
        finally:
            zoom.fit_all = real

    step = dict(verdict="step", why="")
    r = with_pairs([dict(step, s=0.328), dict(verdict="unknown", s=0.324), dict(step, s=0.327)])
    check(r["verdict"] == "step" and r["confirmed_by"] == [1, 3] and abs(r["s"] - 0.327) < 0.002,
          "two of three pass on their own and agree (Puerto Rico's 142.6 s): a step", f"{r['verdict']} x{r['s']:.4f} {r['why']}")
    r = with_pairs([dict(verdict="unknown", s=3.127)] * 3)
    check(r["verdict"] == "unknown" and len(r["confirm"]) == 3, "the same scale three times, none passing (PR27's 89-s "
          "haze): unknown", r["why"])
    r = with_pairs([dict(step, s=0.328), dict(verdict="unknown", s=0.33), dict(verdict="unknown", s=0.33)])
    check(r["verdict"] == "unknown", "one pair alone: unknown", r["why"])
    r = with_pairs([dict(step, s=0.328), dict(step, s=0.36), dict(verdict="unknown", s=0.33)])
    check(r["verdict"] == "unknown", "two steps that disagree by 10 %: unknown", r["why"])
    low = dict(base, prominence=7.0)
    check(not zoom.marginal(low) and not zoom.marginal(dict(base, at_edge=True)) and not zoom.marginal(dict(base, zncc=0.1)),
          "a fit under the prominence or ZNCC floor, or on the grid's edge, is not tried again")


class Rendered:
    """A clip whose frames are all saved, as `zoom.fit_all` and `zoom.overlay_masks` read one: frame n rendered on
    demand by `frame_of(n)` (grey, colour cast), the cast drawn cyan."""

    class _There:
        def exists(self):
            return True

    def __init__(self, frame_of):
        self.frame_of = frame_of

    def path(self, n):
        return self._There()

    def rgb(self, n):
        g, col = self.frame_of(int(n))
        a = np.repeat(g[..., None], 3, axis=2)
        a[..., 0] = np.where(col, g - 60, g)
        return a


def test_a_zoom_with_no_blank_is_fitted_and_a_gain_step_is_not_a_boundary():
    print("\nzoom: x2 between two frames with no blank (FLIR1's ATFLIR at 2235; an electronic zoom), then a gain step "
          "with the optics as they were")
    s = series_with_bursts([], n=400)
    s[200:, 2] = 14.0                                     # from frame 201 the picture's contrast steps down
    s[200, 1] = 12.0
    s[300:, 3] = 118.0                                    # and from frame 301 its level steps up
    s[300, 1] = 15.0
    c = zoom.picture_candidates(s, FPS, [])
    check(c == [(201, 201), (301, 301)], "both found as steps of the picture with no blank", f"{c}")
    check(zoom.bursts(s, FPS) == [], "and neither is a burst")

    def frame_of(n):
        m = 1.0 if n < 201 else 2.0
        g, col = render(m, 700 + 2.0 * n, 900 - 0.6 * n, seed=n)     # the view drifts 2 px a frame over the ground
        if n >= 301:
            g = np.where(col | (g <= 0) | (g >= 255), g, np.clip(g + 18, 9, 246)).astype(np.float32)
        return g, col

    f = zoom.measure("rendered", W, H, FPS, series=s, clip=Rendered(frame_of)).fields
    rows = {r["frames"][0]: r for r in f["picture_steps"]}
    z = rows.get(201)
    check(z is not None and z["verdict"] == "step" and abs(z["s"] / 2 - 1) < 0.02, "the zoom: a step of x2.00 within 2 %",
          z and f"{z['verdict']} x{z.get('fitted_s') or 0:.3f} {z['why']}")
    gain = rows.get(301)
    check(gain is not None and gain["verdict"] != "step", "the gain step: no step of scale",
          gain and f"{gain['verdict']} {gain['why']}")
    check([r["frames"][0] for r in f["bursts"]] == [201] and f["bursts"][0]["kind"] == "picture",
          "only the zoom is a boundary", f"{[(r['frames'], r['kind'], r['verdict']) for r in f['bursts']]}")
    check(len(f["states"]) == 2 and abs(f["states"][1]["magnification"] - 2) < 0.04 and f["states"][1]["chain"] == 0,
          "two states on one chain, the second x2", f"{[(x['frames'], x['magnification'], x['chain']) for x in f['states']]}")
    said = "\n".join(zoom.said(f))
    check("no blank" in said and "not a zoom" in said, "the report says which steps had no blank, and which were no zoom")


def test_the_zoom_as_a_regression_discontinuity():
    print("\nzoom: the jump at a burst from the pairs either side, and placebo cutoffs where nothing happened (E15)")
    rng = np.random.default_rng(3)
    pairs = [(i, j, 2.0 * np.exp(0.002 * i + 0.003 * j + rng.normal(0, 0.002))) for i in range(4) for j in range(4)]
    r = zoom.rd_fit(pairs)
    check(r and abs(r["S"] / 2 - 1) < 0.005 and r["interval"][0] <= 2.0 <= r["interval"][1] and zoom.rd_step(r),
          "a step of x2 with the scene's scale drifting either side: x2.00 within 0.5 %, its interval holding it",
          r and f"x{r['S']:.4f}, {r['interval'][0]:.4f}-{r['interval'][1]:.4f}")
    flat = zoom.rd_fit([(i, j, np.exp(rng.normal(0, 0.004))) for i in range(4) for j in range(4)])
    check(flat and zoom.rd_step(flat) is False, "no step: the interval inside the no-step band", flat and f"{flat['interval']}")
    check(zoom.rd_fit(pairs[:4]) is None, "too few pairs: no estimate")

    def frame_of(n):
        m = 1.0 if n <= 70 else 2.0
        return render(m * (1 + 0.001 * n), 700 + 2.0 * n, 900 - 0.6 * n, fixed=0.5, seed=n)

    todo = [dict(frames=[71, 72], kind="blank", before=70, after=73, fixed_before=list(range(40, 71, 3)),
                 fixed_after=list(range(73, 104, 3)))]
    rows = [dict(frames=[71, 72], verdict="step", s=2.0)]
    states = zoom.states_of(rows, 140, FPS)
    d = zoom.rd("rendered", todo, rows, states, 140, FPS, clip=Rendered(frame_of), h=2, k=2)
    b = d["bursts"][0]["rd"]
    check(b and abs(b["S"] / (2 * 1.073 / 1.070) - 1) < 0.02 and d["bursts"][0]["rd_step"],
          "rendered: the burst's jump from 9 pairs either side, within 2 %", b and f"x{b['S']:.4f} {b['interval']}")
    check(d["placebos_judged"] >= 1 and d["placebo_steps"] == 0, "rendered: the placebo cutoffs inside the states find no step",
          f"{d['placebo_steps']} of {d['placebos_judged']}: {[q['rd'] and round(q['rd']['S'], 4) for q in d['placebos']]}")
    check(any("placebo" in x for x in zoom.rd_said(d)), "and the stage says the placebo rate")


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
