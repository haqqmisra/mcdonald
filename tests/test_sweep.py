"""The beat sweep's tools (tools/sweep/; ROADMAP.md 0.3, objective 9): the parts of the whole-video pass that decide
something, held with no video.

    python3 tests/test_sweep.py

- the windows a video is cut into: the pass's own (PR073's eight, the last ending on the last frame);
- Find's proposals made objects: one seen in two windows is one, a dark and a bright one never are, two apart are two;
- the strict list: passing windows that come back apart at one frequency, or a whole track over its drift at 5 %;
- the held-out third: drawn again from its seed, it is the committed table, and the summary leaves it out until told.

Portable: Python and numpy only.
"""
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools" / "sweep"))
sys.path.insert(0, str(HERE.parent / "src"))

FAIL = []


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAIL.append(label)


@contextlib.contextmanager
def inside(folder):
    """In `folder`, and back where it was whatever happens: Windows will not remove a folder that is the working one."""
    here = os.getcwd()
    os.chdir(folder)
    try:
        yield
    finally:
        os.chdir(here)


def test_windows():
    print("\nthe windows a video is cut into")
    from windows import cut
    pr073 = [(1, 400), (371, 770), (741, 1140), (1111, 1510), (1481, 1880), (1851, 2250), (2221, 2620), (2591, 2657)]
    check(cut(2657, 400, 30) == pr073, "PR073's 2,657 frames: the whole-video pass's own eight windows", str(cut(2657, 400, 30)[-2:]))
    check(cut(322, 400, 30) == [(1, 322)], "a video shorter than a window is one window", str(cut(322, 400, 30)))
    w = cut(770, 400, 30)
    check(w[-1][1] == 770 and all(b - a + 1 <= 400 for a, b in w) and all(w[i + 1][0] <= w[i][1] - 29 for i in range(len(w) - 1)),
          "every window at most 400 frames, each overlapping the next by 30 or more, the last ending on the last frame", str(w))


def proposal(rank, frames, xy, dark=False, seen=None, strength="strong"):
    return dict(rank=rank, strength=strength, seen_in=seen or len(frames), background_all_round=0.9, scrolling_tape=False, dark=dark,
                track={str(n): [xy[0] + n, xy[1]] for n in frames}, against_background_px_per_frame=1.0,
                mark_at={str(frames[0]): [xy[0] + frames[0], xy[1]]})


def test_collect():
    print("\nFind's proposals made objects")
    import collect
    with tempfile.TemporaryDirectory(prefix="mcdonald-sweep-test-") as td, inside(td):
        Path("prop/PRX").mkdir(parents=True)
        w0 = [proposal(1, range(1, 61), (100, 200)), proposal(2, range(1, 61), (100, 200), dark=True),
              proposal(3, range(10, 30), (500, 500)), proposal(4, range(1, 61), (300, 300), strength="none")]
        w1 = [proposal(1, range(50, 120), (102, 201)), proposal(2, range(50, 120), (700, 100))]
        Path("prop/PRX/w00.json").write_text(json.dumps({"results": {"proposals": w0}}), encoding="utf-8")
        Path("prop/PRX/w01.json").write_text(json.dumps({"results": {"proposals": w1}}), encoding="utf-8")
        props = collect.proposals("PRX")
        check(len(props) == 4 and all(p["seen"] >= collect.SEEN for p in props),
              "kept: those seen on 40 frames or more, rated; not one seen on 20, nor one Find did not rate", str(len(props)))
        objs = collect.merged(props)
        firsts = sorted((o["a"], o["b"], o["dark"]) for o in objs)
        check(len(objs) == 3 and (1, 119, False) in firsts and (1, 60, True) in firsts and (50, 119, False) in firsts,
              "the bright one seen in both windows is one object; the dark one beside it is another; one far off is a third", str(firsts))
        collect.main(["PRX"])
        rows = Path("objects/PRX.tsv").read_text(encoding="utf-8").splitlines()
        check(len(rows) == 3 and rows[0].startswith("o00\tw") and rows[0].split("\t")[-1].count(":") >= 1,
              "objects/ID.tsv: a row an object, in order of first frame, with every window it was seen in", rows[0][:60])


def test_summary():
    print("\nthe strict list, and the held-out third")
    import summary
    from holdout import held_out, main as holdout_main
    win = lambda a, b, hz: dict(first=a, last=b, hz=hz, passes=True)
    check(summary.apart([win(1, 60, 7.0), win(61, 120, 7.2)])[0] == 2 and summary.apart([win(1, 60, 7.0), win(30, 90, 7.1)])[0] == 1
          and summary.apart([win(1, 60, 7.0), win(61, 120, 8.0)])[0] == 1,
          "two passing windows count as a beat come back only apart, and within half a hertz of each other")
    check(holdout_main([]) == 0 and len(held_out()) == 42, "the held-out third, drawn again from its seed, is the committed table: 42 videos")
    gone = sorted(held_out())[0]
    with tempfile.TemporaryDirectory(prefix="mcdonald-sweep-test-") as td, inside(td):
        for pid, obj, beats, wins, over, amp in (("PRIN", "o00", True, [(1, 60, 7.0), (61, 120, 7.1)], 1.0, 0.03),
                                                 ("PRIN", "o01", True, [(1, 60, 7.0)], 20.0, 0.08),
                                                 ("PRIN", "o02", True, [(1, 60, 7.0)], 20.0, 0.03),
                                                 (gone, "o00", True, [(1, 60, 7.0), (61, 120, 7.1)], 1.0, 0.03)):
            Path(f"beat/{pid}").mkdir(parents=True, exist_ok=True)
            r = dict(first=1, last=120, frames=120, beats=beats, finding="",
                     curves={"object": dict(hz=7.0, hz_err=0.02, amplitude=amp, over_drift=over, drift_needed=8.0)},
                     beat={"object": dict(hz=7.0, windows_passing=len(wins), windows=8)},
                     windows={"object": [win(*w) for w in wins]})
            Path(f"beat/{pid}/{obj}_flicker.json").write_text(json.dumps({"results": r}), encoding="utf-8")
        rows, left = summary.rows(held_out())
        strict = {(r["id"], r["obj"]) for r in rows if r["strict"]}
        check(strict == {("PRIN", "o00"), ("PRIN", "o01")} and left == 1,
              "strict: two windows apart at one frequency (o00), or the whole track over its drift at 8 % (o01) -- not at 3 % (o02); "
              "and the held-out video left out, and counted", f"{sorted(strict)}, {left} left out")
        rows, left = summary.rows(())
        check(left == 0 and (gone, "o00") in {(r["id"], r["obj"]) for r in rows if r["strict"]}, "told the gates are frozen, it is counted in")


def test_floor():
    print("\nthe bird floor from a null, its challenger, and the probability it is overfit (floor.py, pbo.py)")
    import random
    import floor
    import pbo
    check(floor.smallest_floor([0.2, 0.15, 0.07, 0.05, 0.02, None], 300, 0.01) == 0.051
          and floor.smallest_floor([0.2, 0.15], 300, 0.01) == 0.0,
          "the smallest floor that names no more than 1 % of 300: just over the fourth strongest (3 may pass); none needed for two")
    row = lambda clip, cls, call, amp, shaken="": {"clip": clip, "cls": cls, "stage_call": call, "stage_amplitude": amp,
                                                   "stage_hz": 7.0, "stage_shaken_px": shaken}
    check(floor.named(row("a", "BIRD", "bird", "0.09"), "stage", 0.08) and not floor.named(row("a", "BIRD", "bird", "0.07"), "stage", 0.08)
          and not floor.named(row("a", "BIRD", "bird", "0.5", "0.6"), "stage", 0.08)
          and floor.named(row("a", "BIRD", "bird", ""), "stage", 0.5) and not floor.named(row("a", "BIRD", "once", "0.5"), "stage", 0.0),
          "named: a beat that comes back at the floor or over, not where the camera's shake sits at it; a case with no amplitude as before")
    lo, hi = floor.exact(0, 307)
    lo2, hi2 = floor.exact(2, 307)
    check(lo == 0 and abs(hi - 0.01194) < 2e-4 and abs(lo2 - 0.00079) < 1e-4 and abs(hi2 - 0.02334) < 3e-4,
          "Clopper-Pearson: 0 of 307 under 1.2 %; 2 of 307 within 0.08-2.3 %", f"{hi:.5f} {lo2:.5f} {hi2:.5f}")
    check(floor.binom_upper(307, 0.01) == 6, "at a rate of 1 % on 307 tracks, a one-sided test at 5 % allows up to 6")
    check(abs(floor.upper(0, 286) - 0.0104) < 2e-4 and abs(floor.upper(2, 307) - 0.0205) < 5e-4,
          "the one-sided 95 % bound: none in 286 is 1.04 %, so about 300 tracks cannot show under 1 %; 2 in 307 is about 2 %",
          f"{floor.upper(0, 286):.4f}, {floor.upper(2, 307):.4f}")
    _, _, stage = floor.operating_point(0.24, 0.039)
    _, _, floored = floor.operating_point(0.23, 0.0065)
    check(abs(stage - 0.33) < 0.02 and abs(floored - 1.5) < 0.05,
          "the operating point (B24): the stage's rule prices a false bird at a third of a missed one, the 8 % floor at 1.5",
          f"{stage:.3f}, {floored:.3f}")
    rng = random.Random(7)
    rows = [row(f"n{i}", "DRONE", "bird" if i < 12 else "none", f"{0.002 * (i + 1):.3f}") for i in range(300)]
    rows += [row(f"b{i}", "BIRD", "bird" if i < 30 else "none", f"{rng.uniform(0.05, 0.3):.3f}") for i in range(100)]
    f, per = floor.set_floor(rows, boot=200, say=lambda *a: None)
    k = sum(floor.named(r, "stage", f) for r in rows if not floor.bird(r))
    check(per["stage"]["plain"] == 0.019 and 0.015 <= per["stage"]["median"] <= 0.023 and f in (0.02, 0.025) and k <= 3,
          "set from the null: twelve false calls at 0.2-2.4 % of 300, so the floor lands over the fourth strongest and names at most 3",
          f"{f}, {per['stage']}, {k}")
    check(floor.stratum({"labelled": "120"}, "labelled", (150, 300, float("inf")), "stage") == "0-150"
          and floor.stratum({"labelled": "400"}, "labelled", (150, 300, float("inf")), "stage") == "300 or more"
          and floor.stratum({"w_med": ""}, "w_med", (5, 10, float("inf")), "stage") == "(not measured)"
          and floor.stratum({"distance": "CLOSE"}, "distance", None, "stage") == "CLOSE",
          "the strata a frozen floor's rates are described by: track length, size, the set's own bins")
    rows = []
    for c in range(64):
        cls = "BIRD" if c % 2 else "DRONE"
        for t in range(3):
            rows += [dict(config="perfect", clip=f"c{c}", cls=cls, named=int(cls == "BIRD"))]
            rows += [dict(config=f"coin {j}", clip=f"c{c}", cls=cls, named=int(rng.random() < 0.5)) for j in range(9)]
    configs, table = pbo.table_long(rows, 8)
    p, logits, chosen, _ = pbo.cscv(pbo.counts(table, 8), 8)
    check(p == 0 and all(configs[j] == "perfect" for j in chosen),
          "CSCV: a rule right on every clip is chosen on every half and never overfit", f"{p}")
    configs, table = pbo.table_long([r for r in rows if r["config"] != "perfect"], 8)
    p, _, _, _ = pbo.cscv(pbo.counts(table, 8), 8)
    check(0.25 < p < 0.85, "CSCV: among coins, the best in sample is no better than the median out of sample about half the time",
          f"{p:.2f}")


def main():
    print("mcDonald UAP Toolkit -- the beat sweep's tools")
    for fn in (test_windows, test_collect, test_summary, test_floor):
        fn()
    print(f"\n{'ALL PASS' if not FAIL else str(len(FAIL)) + ' FAILED: ' + ', '.join(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
