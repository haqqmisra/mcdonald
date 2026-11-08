"""Does `breaks` date a change of velocity beyond the track's wander, and set it against the scene (method section 51)?

Drawn tracks only. A wander with no break is named a break about one time in twenty, the level the scan states; a change of
60 px/s at 5 s on 300 frames at 30 fps (the economics survey's planted row: a wander whose velocity sd is 8.7 px/s) is
found, its date inside the 95 % interval; nothing is looked for in the first and last 15 %. The scene frame by frame from
overlapping five-frame shifts keeps a held picture on the clock (a frame that did not move, then the catch-up), which a
five-frame average never shows. The event study: a change the scene made too is the camera's; one the scene did not make
is not; a scene held still on screen is no power. Six members with one change each share a date, sharper than each alone (Bai, Lumsdaine & Stock), and a common change adds no spread. The kinematics stage records it and the
report's paragraph says it, in sentences under 40 words.

    python3 tests/test_breaks.py        # or: pytest tests/

No video data needed.
"""
import math
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import breaks, kriging as kg  # noqa: E402

FAIL = []
FPS = 30.0
THETA = (25.0, 1.0, 0.16)            # a 5-px wander over about a second and a 0.4-px nugget: the survey's drawn rows


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def drawn(n=300, dv=(0.0, 0.0), at=5.0, seed=0, theta=THETA, v=(20.0, -5.0)):
    """(t, x, y): a line at v px/s, the wander and the nugget of `theta`, and a change of velocity dv px/s at `at` s."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / FPS
    x = v[0] * t + kg.simulate(t, theta, rng)[0] + dv[0] * np.maximum(t - at, 0.0)
    y = v[1] * t + kg.simulate(t, theta, rng)[0] + dv[1] * np.maximum(t - at, 0.0)
    return t, x, y


def test_the_scan():
    print("\nthe scan: a change of velocity beyond the wander")
    named = sum(breaks.scan(*drawn(seed=s), [THETA, THETA], seed=s)["p"] < breaks.ALPHA for s in range(20))
    check(named <= 3, "a wander with no break: named on at most 3 of 20 drawn tracks (5 % stated)", f"{named} of 20")
    t, x, y = drawn(dv=(60.0, 0.0), seed=3)
    s = breaks.scan(t, x, y, [THETA, THETA])
    check(s["p"] < 0.01 and s["interval_s"][0] <= 5.0 <= s["interval_s"][1] and abs(s["dv_xy"][0] - 60.0) < 30.0,
          "60 px/s at 5 s: found, the date inside its 95 % interval, the change about its size",
          f"p {s['p']:.4f}, {s['t_s']:.2f} s in {s['interval_s'][0]:.2f}-{s['interval_s'][1]:.2f}, {s['dv_xy'][0]:+.0f} px/s")
    n = len(t)
    check(abs(s["looked_s"][0] - t[math.ceil(0.15 * n)]) < 1e-9 and abs(s["looked_s"][1] - t[int(0.85 * n) - 1]) < 1e-9,
          "nothing looked for in the first and last 15 %", f"{s['looked_s']}")
    t, x, y = drawn(dv=(60.0, 0.0), at=0.3, seed=3)
    e = breaks.scan(t, x, y, [THETA, THETA])
    check(not (e["looked_s"][0] <= 0.3 <= e["looked_s"][1]), "a change in the first 15 %: outside the stretch looked in (no power there)",
          f"looked {e['looked_s'][0]:.2f}-{e['looked_s'][1]:.2f} s")
    check(breaks.scan(t[:30], x[:30], y[:30], [THETA, THETA]) is None, f"under {breaks.BREAK_MIN} points: no scan")
    a = breaks.scan(*drawn(dv=(60.0, 0.0), seed=3), [THETA, THETA])
    check(a == s, "the same track gives the same p and interval twice (the draws are seeded)")


def held_scene(n=120, v=-21.0, hold=60, k=5):
    """A scene moving v px a frame with the picture held at frame `hold` and caught up at the next: its path, and the
    k-frame shifts a `layers` CSV gives of it, (frames, dx, dy)."""
    step = np.full(n + k, v)
    step[hold] = 0.0
    step[hold + 1] = 2 * v
    S = np.r_[0.0, np.cumsum(step)]
    fr = np.arange(1, n + 1)
    dx = np.array([S[a - 1 + k] - S[a - 1] for a in fr])
    return S, fr, dx, np.zeros(n)


def test_the_scene_frame_by_frame():
    print("\nthe scene frame by frame from overlapping five-frame shifts")
    S, fr, dx, dy = held_scene()
    sc = breaks.scene_path(fr, dx, dy, 5)
    st = np.diff(sc["X"])
    check(abs(st[60]) < 2.0 and abs(st[61] + 42.0) < 2.0 and abs(st[10:40].mean() + 21.0) < 0.05,
          "a held picture comes out as a frame that did not move, then the catch-up, and a second's mean rate is exact",
          f"steps {st[59]:.1f}, {st[60]:.1f}, {st[61]:.1f}, {st[62]:.1f} px; a second's mean {st[10:40].mean():.3f}")
    avg = dx / 5.0
    check(np.abs(avg).min() > 15.0, "the five-frame average never shows the held frame (the hold and its catch-up cancel in "
          "every window that holds both)", f"its least step {np.abs(avg).min():.1f} px")
    check(sc["covered"].all() and len(sc["frames"]) == len(fr) + 5, "every step covered, every frame placed")
    check(breaks.scene_path(fr[:5], dx[:5], dy[:5], 5) is None, "under ten measured pairs: no path")


def event(scene_dv, object_dv, held=None, seed=4, n=240, at=4.0):
    """The event study on a drawn object over a drawn scene: the scene moving -30 px/s, changing by scene_dv at `at` s;
    the object the scene's motion plus its own (+15 px/s, changing by object_dv) plus a wander. Returns against_scene's."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / FPS
    fr = np.arange(1, n + 1)
    Sx = -30.0 * t + scene_dv[0] * np.maximum(t - at, 0.0)
    Sy = scene_dv[1] * np.maximum(t - at, 0.0)
    th = (4.0, 1.5, 0.09)
    x = Sx + 15.0 * t + object_dv[0] * np.maximum(t - at, 0.0) + kg.simulate(t, th, rng)[0]
    y = Sy + object_dv[1] * np.maximum(t - at, 0.0) + kg.simulate(t, th, rng)[0]
    k = 5
    ff = fr[:-k]
    dx = Sx[k:] - Sx[:-k] + rng.normal(0, 0.1, n - k)
    dy = Sy[k:] - Sy[:-k] + rng.normal(0, 0.1, n - k)
    sc = breaks.scene_path(ff, dx, dy, k)
    brk = dict(frame=int(round(at * FPS)) + 1, t_s=at)
    return breaks.against_scene(brk, fr, t, x, y, [th, th], sc, FPS, held_share=held)


def test_against_the_scene():
    print("\nthe event study: the object's change set against the scene's")
    r = event((-60.0, 10.0), (0.0, 0.0))
    check(r["power"] and r["verdict"] == "the camera's",
          "the scene changed and the object with it: the camera's",
          f"object {r['object'][0]:+.0f}, scene {r['scene'][0]:+.0f}, abnormal {r['abnormal'][0]:+.1f} ± {r['abnormal_err'][0]:.1f} px/s")
    r = event((0.0, 0.0), (-60.0, 10.0))
    check(r["power"] and r["verdict"] == "not the camera's",
          "the object changed and the scene did not: not the camera's",
          f"object {r['object'][0]:+.0f}, scene {r['scene'][0]:+.1f}, abnormal {r['abnormal'][0]:+.1f} ± {r['abnormal_err'][0]:.1f} px/s")
    r = event((-60.0, 0.0), (-60.0, 0.0))
    check(r["power"] and r["verdict"] == "partly the camera's" and 0.3 < r["share"] < 0.7,
          "both changed the same way: partly the camera's, about half of it",
          f"share {r['share']:.2f} ± {r['share_err']:.2f}")
    r = event((-60.0, 10.0), (0.0, 0.0), held=0.9)
    check(not r["power"] and "held still on screen" in r["why"], "a scene held still on screen: no power", r.get("why", ""))
    check(not breaks.against_scene(dict(frame=121, t_s=4.0), [], [], [], [], None, None, FPS)["power"],
          "no scene measured: no power")


def test_a_group():
    print("\na group: a change common to its members, and the spread at it")
    members, alone = [], []
    for s in range(6):
        t, x, y = drawn(n=300, dv=(25.0, 0.0), at=5.0, seed=10 + s)
        members.append((t, x, y, [THETA, THETA]))
        alone.append(breaks.scan(t, x, y, [THETA, THETA], seed=s)["p"])
    c = breaks.common(members, FPS, draws=1000)
    check(c["found"] and c["interval_s"][0] <= 5.0 <= c["interval_s"][1],
          "six members with one change each: a common date, inside its interval",
          f"p {c['p']:.4f} at {c['t_s']:.2f} s ({c['interval_s'][0]:.2f}-{c['interval_s'][1]:.2f}); alone p "
          + ", ".join(f"{p:.3f}" for p in alone))
    d = breaks.dispersion(members, c["t_s"], FPS)
    check(d is not None and not d["extra_spread"] and d["common_px_per_s"] > d["placebo_common_median"],
          "the same change for all: a common change larger than on ordinary dates, no extra spread",
          f"common {d['common_px_per_s']:.0f} px/s (placebo median {d['placebo_common_median']:.0f}), spread at the "
          f"{100 * d['spread_centile']:.0f}th centile" if d else "none")
    from mcdonald import kinematics as kin
    objs = []
    for i, (t, x, y, _) in enumerate(members[:3]):
        trk = {j + 1: (float(a), float(b)) for j, (a, b) in enumerate(zip(x + 300, y + 200))}
        objs.append((i + 1, trk, kin.speed_band(trk, FPS)[0]))
    late = {j + 400: xy for j, xy in objs[0][1].items()}            # a fourth, followed over other frames
    objs.append((4, late, kin.speed_band(late, FPS)[0]))
    got = breaks.together(objs, FPS)
    said = " ".join(breaks.together_said(got[0], [False, False, False])) if got else ""
    check(len(got) == 1 and got[0]["objects"] == [1, 2, 3] and got[0]["common"]["found"]
          and "Objects 1, 2 and 3 change their velocity together" in said and "No one of them" in said,
          "the objects' page: the three followed over the same frames tested together, the fourth left out", said[:200])


def test_the_stage_and_the_report():
    print("\nthe kinematics stage records it, and the report says it")
    from mcdonald import stages
    from mcdonald.report import Case
    t, x, y = drawn(n=300, dv=(60.0, 0.0), seed=3)
    trk = {i + 1: (float(a), float(b)) for i, (a, b) in enumerate(zip(x + 400, y + 300))}
    with tempfile.TemporaryDirectory() as td:
        k = stages.kinematics(trk, FPS, 1280, "drawn", None, out=f"{td}/drawn")
    b = k.fields.get("breaks")
    check(b is not None and b["found"] and b["frames_interval"][0] <= 151 <= b["frames_interval"][1]
          and "velocity break" in k.result and b["scene"]["power"] is False,
          "the stage: the change found and dated, the scene not measured (no layers step)", k.result.get("velocity break", "")[:160])
    case = Case("drawn", "drawn.mp4")
    case.add("kinematics", k.result, fields=k.fields, no_power=k.no_power)
    S = case.breaks_said()
    check(len(S) == 3 and S[0].startswith("Its velocity changed suddenly at") and "not measured" in S[2],
          "the paragraph: when, how rare, and that the background was not measured", " ".join(S))
    case.stages["kinematics"]["fields"]["breaks"] = dict(b, scene=dict(power=True, verdict="the camera's"))
    case.add("camera", {}, fields=dict(events=[dict(frame=b["frames_interval"][0], what="the picture zooms x2.00")]))
    S = case.breaks_said()
    check(any("so the change is the camera's." in s for s in S) and "the picture zooms x2.00" in S[-1],
          "a scene that changed with it, and a camera event inside the interval, are said", " ".join(S[2:]))
    long = [s for s in S if len(s.split()) > 40]
    check(not long and not any(" thing" in s for s in S), "every sentence under 40 words, and no 'thing'", f"{long}")
    k0 = drawn(n=300, seed=1)
    trk0 = {i + 1: (float(a), float(b)) for i, (a, b) in enumerate(zip(k0[1] + 400, k0[2] + 300))}
    case0 = Case("drawn", "drawn.mp4")
    f0 = stages.kinematics(trk0, FPS, 1280, "drawn", None)
    case0.add("kinematics", f0.result, fields=f0.fields)
    check(case0.breaks_said() == [] or f0.fields["breaks"]["found"], "no change found: the paragraph says nothing of it",
          f"p {f0.fields['breaks']['p']:.3f}")


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
