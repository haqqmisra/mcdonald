#!/usr/bin/env python3
"""The zoom states and `slew` across a zoom, on the real clips whose answers are known (docs/method.md §17, "Zoom
states"; docs/handoff-zoom-slew.md).

- PR27 (MQ-9 MTS-B, 297 s): x2.00 at the 82-s burst (a hand fit read x1.98-2.00); the 89-s burst (featureless haze,
  a naive fit x6.00 on the grid's edge) and the 134-s burst (AARO: "zoomed 2:15"; a naive fit x1.00 on the fixed
  pattern) must come out "unknown"; the 58-s burst (the camera turns while it zooms out) must not be "no step".
  `slew` across the 82-s step: c ~268 before, ~515-530 after, and their ratio must agree with the imagery's.
- PR057a (MTS-B, 71 s): x2.00 at 32.8 s; `slew` ~250-263 before it and ~570 after.
- AARO's Puerto Rico clip (WESCAM, 2013): its display's IR readout goes 135 -> 675 -> 2024 -> 675 at 20.5, 118.1 and
  142.6 s (ratios 5, 3, 1/3; a hand fit of the imagery read x5.05, x3.05, x1/3.10), and the ground moves 300-400 px
  during each blank. The first two must be steps within 4 % of the readout; the third, whose peak barely leads the
  next scale's (as PR27's 89-s trap's does), a step at the right scale or unknown.

The footage is the reference data's ($MCDONALD_DATA: pursue/, aaro/videos/), and so are the pointer and scene series
`slew` reads (slew/). About ten minutes on four CPUs; through the queue:

    mkdir -p logs && sbatch -n 1 -c 4 --mem=3G --time=00:40:00 -o logs/%x_%j.out -J zoom_check \\
        --wrap "python3 -u tools/zoom_check.py --out /scratch/zoom_check"
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from mcdonald import slew, zoom  # noqa: E402
from mcdonald.clip import Clip  # noqa: E402
import reference_data  # noqa: E402

FAIL = []


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}", flush=True)
    if not cond:
        FAIL.append(label)
    return cond


def burst_at(f, t):
    """The burst whose span (padded by a second) holds t s."""
    return next((r for r in f["bursts"] if r["t_s"][0] - 1.0 <= t <= r["t_s"][1] + 1.0), None)


def states(video, out, tag):
    clip = Clip(video, None, extract=False)
    f = zoom.measure(video, clip.W, clip.H, clip.fps, clip=clip, out=out / tag).fields
    print("\n".join("    " + x for x in zoom.said(f)), flush=True)
    return f, clip


def step(f, t, want, tol, label):
    r = burst_at(f, t)
    ok = r is not None and r["verdict"] == "step" and abs(r["s"] / want - 1) <= tol
    check(ok, label, "no burst there" if r is None else f"{r['verdict']} x{r.get('fitted_s') or 0:.3f} (ZNCC "
          f"{r.get('zncc') or 0:.2f}; {r.get('prominence') or 0:.1f} MADs, at x1 {r.get('prominence_at_1') or 0:.1f}, "
          f"a quarter off {r.get('prominence_off') or 0:.1f}) {r['why']}")


def unknown(f, t, label):
    r = burst_at(f, t)
    check(r is not None and r["verdict"] == "unknown", label,
          "no burst there" if r is None else f"{r['verdict']}: {r['why'] or 'x%.3f' % r['s']}")


def right_or_unknown(f, t, want, tol, label):
    """A step at the right scale, or unknown -- never a wrong number, and never "no step"."""
    r = burst_at(f, t)
    ok = r is not None and (r["verdict"] == "unknown" or (r["verdict"] == "step" and abs(r["s"] / want - 1) <= tol))
    check(ok, label, "no burst there" if r is None else f"{r['verdict']} (fitted x{r.get('fitted_s') or 0:.4f} = "
          f"1/{1 / (r.get('fitted_s') or 1):.3f}; {r.get('prominence') or 0:.1f} MADs, a quarter off "
          f"{r.get('prominence_off') or 0:.1f}) {r['why']}")


def slew_check(video, data, tag, zf, clip, out, before, after, label):
    """`slew` with the zoom states: the claims of the state holding `before` (t, lo, hi) and of the one holding
    `after`, and the ratio check between them."""
    f = slew.measure(data / f"{tag}_north.csv", data / f"{tag}_layers.csv", clip.W, clip.H, clip.fps, zoom=zf,
                     out=str(out / tag), name=tag).fields
    for line in slew.said(f):
        if line.startswith(("state", "states", "zoom", "k cos")):
            print("    " + line, flush=True)
    st = lambda t: next((r for r in f["states"] if r["t_s"][0] <= t <= r["t_s"][1]), None)
    a, b = st(before[0]), st(after[0])
    for r, (t, lo, hi), which in ((a, before, "before"), (b, after, "after")):
        c = r and r["c_px_per_deg"]
        check(bool(c) and lo <= c <= hi, f"{label}: c {which} the step in {lo}-{hi} px/deg",
              f"state {r and r['state']}: {c and round(c)}")
    chk = next((x for x in f["zoom_checks"] if a and b and x["states"] == [a["state"], b["state"]]), None)
    check(chk is not None and chk.get("agree") is True, f"{label}: the ratio of c agrees with the imagery's zoom",
          f"{chk}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default="zoom_check", help="where the states, slews and figures go")
    ap.add_argument("--only", choices=["pr27", "pr057a", "aaro"], action="append")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = reference_data.root()
    only = set(a.only or ["pr27", "pr057a", "aaro"])

    if "pr27" in only:
        print("\nPR27 (MTS-B): the zoom states", flush=True)
        v = data / "pursue" / "DOD_111688825.mp4"
        f, clip = states(v, out, "pr27")
        step(f, 82.1, 2.0, 0.02, "82 s: x2.00 within 2 %")
        unknown(f, 89.4, "89 s (featureless haze): unknown, never a number")
        unknown(f, 134.0, "134 s (a zoom per AARO, x1.00 on the fixed pattern): unknown")
        r = burst_at(f, 58.4)
        check(r is not None and r["verdict"] != "no step", "58 s (the camera turns as it zooms out): not \"no step\"",
              r and r["verdict"])
        slew_check(v, data / "slew", "pr27", f, clip, out, (70.0, 255, 280), (85.0, 480, 560), "PR27")

    if "pr057a" in only:
        print("\nPR057a (MTS-B): the zoom states", flush=True)
        v = data / "pursue" / "DOD_111719752.mp4"
        f, clip = states(v, out, "pr057a")
        step(f, 32.9, 2.0, 0.02, "32.8 s: x2.00 within 2 %")
        slew_check(v, data / "slew", "pr057a", f, clip, out, (25.0, 235, 280), (40.0, 520, 600), "PR057a")

    if "aaro" in only:
        print("\nAARO Puerto Rico 2013 (WESCAM): the zoom states against the IR readout", flush=True)
        v = data / "aaro" / "videos" / "DOD_110692805-1920x1080-9000k.mp4"
        f, _ = states(v, out, "aaro_pr")
        # the readout's ratios; a hand fit of the imagery (uap analysis/cases/aaro_puerto_rico) read x5.05, x3.05, x1/3.10
        step(f, 20.5, 5.0, 0.04, "20.5 s, the readout 135 -> 675: x5 within 4 %")
        step(f, 118.1, 3.0, 0.04, "118.1 s, the readout 675 -> 2024: x3 within 4 %")
        right_or_unknown(f, 142.6, 1 / 3, 0.04, "142.6 s, the readout 2024 -> 675: x1/3 within 4 %, or unknown (its peak "
                                                "barely leads the next scale's: never a wrong number)")
        for r in f["bursts"]:
            if r["t_s"][0] > 150 and r["verdict"] == "step":
                print(f"    note: {r['t_s'][0]:.1f} s fitted a step of x{r['s']:.3f} (the hand fit could not confirm the "
                      "late switches)")

    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
