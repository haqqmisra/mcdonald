"""Do the real clips still give the published numbers?

test_measurement.py proves the library measures synthetic scenes correctly.
This proves it has not drifted on the clips whose results have been published
or circulated — the ones where a changed number would mean a retraction.

It needs the video files, which are not distributed with the package (the
PURSUE corpus is ~22 GB and is a mirror of war.gov/UFO). Point the toolkit at
a catalog and the test finds them:

    export MCDONALD_CATALOG=~/research/uap/pursue_index/records.csv
    python3 tests/test_golden.py

Without one, it skips and says so. The object track it needs is vendored in
tests/golden/, so only the video has to be found.

Two levels:
  (default)  a 200-frame window of PR144 -- about 5 minutes, catches any
             regression in masks, registration, layer classes or consensus.
             It passes --fresh: `layers` keeps its templates beside the frames,
             and until 2026-09-20 this test found the ones an earlier run had
             left there and took 25 s: the masks, the layer classes and the
             consensus were tested, and the registration not at all.
  --full     the documented whole-clip commands against the published values
             in docs/method.md -- tens of minutes.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))

from mcdonald import catalog  # noqa: E402

FAIL, SKIP = [], []

# Frames 300-500 of PR144, measured 2026-09-19 with the command in run_window().
# Tolerances are wider than any float or thread-ordering difference and far
# tighter than any real regression: these are consensus medians over dozens of
# templates, and a broken mask or a mis-set zero zone moves them by tens.
WINDOW_BASELINE = {
    "object vs sea": (599, 4),
    "object vs cloud tops": (500, 4),
    "cloud tops vs sea": (99, 3),
    "ratio": (6.0, 0.4),
    "group gap": (97, 5),
}

# The whole-clip results in docs/method.md, section 4. Checked only with --full.
PUBLISHED = {
    "object vs sea": (648, 12),
    "object vs cloud tops": (510, 12),
    "cloud tops vs sea": (98, 4),
    "ratio": (6.2, 0.5),
}


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def parse(out):
    """The numbers a reader would take off the tool's own summary."""
    got = {}
    for label, key in (("the sea", "object vs sea"),
                       ("the cloud tops", "object vs cloud tops"),
                       ("the cloud tops against the sea", "cloud tops vs sea")):
        m = re.search(rf"^\s+{re.escape(label)}\s+median\s+(-?\d+)", out, re.M)
        if m:
            got[key] = float(m.group(1))
    m = re.search(r"ratio ([\d.]+)", out)
    if m:
        got["ratio"] = float(m.group(1))
    m = re.search(r"two in [\d.]+% of pairs, (\d+) px/s apart", out)
    if m:
        got["group gap"] = float(m.group(1))
    return got


def fields(out, what):
    """The same numbers as `layers --json` has them: fields, not sentences. And what it
    printed for a person, read the way `parse` reads it, has to be those fields rounded."""
    r = json.loads(out)["results"]
    med = lambda s: None if not s else s["median"]
    got = {"object vs sea": med(r["px_per_s"]["striated"]), "object vs cloud tops": med(r["px_per_s"]["isotropic"]),
           "cloud tops vs sea": med(r["layer_against_layer"]), "ratio": (r["object_over_parallax"] or {}).get("ratio"),
           "group gap": r["motion_groups"]["apart_px_per_s"]}
    got = {k: v for k, v in got.items() if v is not None}
    read = parse("\n".join(r["said"]))
    check(set(read) == set(got) and all(abs(read[k] - got[k]) <= (0.051 if k == "ratio" else 0.51) for k in got),
          f"{what}: what it prints for a person is its fields, rounded", ", ".join(f"{k} {read.get(k)} / {got[k]:.2f}" for k in got))
    return got


def have_clip(record_id):
    cat = catalog.active()
    if isinstance(cat, catalog.NullCatalog):
        return None, "no catalog configured (set MCDONALD_CATALOG)"
    hits = cat.by_id(record_id)
    if not hits:
        return None, f"{record_id} not in the {cat.name} catalog"
    p = Path(hits[0].get("path", ""))
    return (p, None) if p.exists() else (None, f"{record_id} is in the catalog but {p} is missing")


def run(args, workdir):
    r = subprocess.run([sys.executable, "-m", "mcdonald.cli"] + args,
                       capture_output=True, text=True, cwd=workdir,
                       env={**os.environ, "PYTHONPATH": str(HERE.parent / "src")})
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-2000:], file=sys.stderr)
        raise SystemExit(f"mcdonald {' '.join(args)} exited {r.returncode}")
    return r.stdout


def compare(got, expected, what):
    for key, (want, tol) in expected.items():
        if key not in got:
            check(False, f"{what}: {key}", "not present in the tool's output")
            continue
        check(abs(got[key] - want) <= tol, f"{what}: {key}",
              f"{got[key]:g} (expected {want:g} +/- {tol:g})")


def test_pr113_two_clicks():
    """Technical Note Sec. 5. Two clicks are the whole human input: the link has to
    choose the detector from them, follow a 142 px/frame object that the blind
    tracker cannot acquire, and land on the four positions the published rate
    was measured over."""
    print("\nPR113, frames 400-420 -- from two clicks to the published track")
    video, why = have_clip("PR113")
    if not video:
        print(f"  SKIP  {why}")
        SKIP.append("PR113 two clicks")
        return
    import numpy as np
    from mcdonald import autolink, forensics as vf
    clip = vf.Clip(video, None, 400, 420)
    marks = {408: (1009.0, 313.0), 411: (702.0, 604.0)}          # the identification in pr113_track.py's docstring
    L = list(autolink.link_from_marks(clip, marks))[-1]
    check(L.size == 21.0 and L.dark is True, "PR113: the detector chosen from the marks is 21 px, dark",
          f"{L.size:g} px, dark={L.dark}")
    gold = vf.read_track(HERE / "golden" / "pr113_transit_curated.csv")
    check(sorted(L.track) == sorted(gold), "PR113: linked on the four frames of the transit, and no others",
          f"{sorted(L.track)}")
    worst = max((float(np.hypot(L.track[n][0] - x, L.track[n][1] - y)) for n, (x, y) in gold.items() if n in L.track),
                default=float("inf"))
    check(worst <= 0.05, "PR113: at the vendored positions", f"worst {worst:.3f} px")
    check(L.worst() is not None and L.worst() <= 3.0, "PR113: and within a click's error of both hand marks",
          ", ".join(f"{n}: {d:.1f} px" for n, d in L.residuals.items()))
    if len(L.track) > 1:
        v = vf.velocity_from_marks({n: L.track[n] for n in (min(L.track), max(L.track))})
        check(abs(float(np.hypot(*v)) - 142.0) <= 1.0, "PR113: the automatic track gives back the published 142 px/frame",
              f"({v[0]:+.1f}, {v[1]:+.1f}) = {np.hypot(*v):.1f}")


def test_pr43_streak_by_motion():
    """PR43 (Jacob, 2026-09-27): a small bright thing crossing about 20 px a frame over ground, drawn out into a
    dash by the exposure. Find's first proposal is it; no spot size holds its marks (the nearest spot 61 px
    away); the link follows its motion instead, from the two marks Find placed, and lands on the dash on
    every frame it is in, 50-75, within 1.4 px of both marks."""
    print("\nPR43, frames 1-88 -- a streak followed by its motion from Find's two marks")
    video, why = have_clip("PR43")
    if not video:
        print(f"  SKIP  {why}")
        SKIP.append("PR43 streak")
        return
    import numpy as np
    from mcdonald import autolink, forensics as vf
    clip = vf.Clip(video, None, 1, 88)
    marks = {57: (1039.0, 836.0), 71: (1301.8, 1000.8)}            # Find's marks on its first proposal, as Jacob's save has them
    steps = list(autolink.link_from_marks(clip, marks))
    L = steps[-1]
    check(L.done and L.track and set(L.source.values()) == {"motion"} and any(s.stage == "motion" for s in steps),
          "PR43: no spot size holds the marks, and the link follows the motion instead", L.say[:80])
    check(L.track and 49 <= min(L.track) <= 52 and 74 <= max(L.track) <= 77 and len(L.track) >= 23,
          "PR43: on the frames the thing is in, 50-75", f"{len(L.track)} frames {min(L.track) if L.track else '-'}–{max(L.track) if L.track else '-'}")
    at65 = L.track.get(65)
    check(at65 is not None and np.hypot(at65[0] - 1158.2, at65[1] - 913.5) <= 4.0, "PR43: on the dash at frame 65, to 4 px",
          f"{at65}")
    check(L.worst() is not None and L.worst() <= 3.0 and L.dark is False, "PR43: within 3 px of both marks, bright",
          ", ".join(f"{n}: {d:.1f} px" for n, d in L.residuals.items()))
    if L.track and 57 in L.track and 71 in L.track:
        v = vf.velocity_from_marks({57: L.track[57], 71: L.track[71]})
        check(abs(float(np.hypot(*v)) - 22.0) <= 2.5, "PR43: about 22 px a frame between the two marks (660 px/s)",
              f"({v[0]:+.1f}, {v[1]:+.1f}) = {np.hypot(*v):.1f} px/frame")


FLYER5 = Path("/home/jacob/research/uap/zenodo_pr135/galileo_dalek_clips")


def test_flyer5_wingbeat():
    """Galileo Project Dalek flyer 5 (Jacob's bird control, 2026-09-29): the paper measured its wingbeat at
    3.90 Hz with the double at 7.80, over source frames 52322-52456. The stage, on the paper's own track,
    finds the beat in a window over the flapping and names the fundamental."""
    print("\nflyer 5 (Galileo Dalek) -- the paper's wingbeat, 3.90 / 7.80 Hz")
    video = next(iter(FLYER5.glob("flyer5_*.mp4")), None)
    track_csv = FLYER5 / "flyer5_paper_track.csv"
    if video is None or not track_csv.exists():
        print("  SKIP  the Galileo clips are not on this computer")
        SKIP.append("flyer 5")
        return
    import csv
    from mcdonald import flicker, forensics as vf
    track = {int(r["frame"]) - 51720: (float(r["x"]), float(r["y"])) for r in csv.DictReader(open(track_csv, encoding="utf-8"))}
    clip = vf.Clip(video, None, min(track), max(track))
    found = flicker.measure(clip, {"object": track}, say=lambda *a: None)
    f = found.fields
    b = (f.get("beat") or {}).get("object")
    check(f["beats"] is True and b is not None, "flyer 5: its brightness beats, the object's own",
          str(f.get("finding") or found.no_power)[:120] + f"; trimmed {f.get('trimmed')}")
    check(b is not None and abs(b["hz"] - 3.90) <= 0.2 and b["double_hz"] is not None and abs(b["double_hz"] - 7.80) <= 0.4,
          "flyer 5: 3.9 Hz and its double 7.8, as the paper has them", f"{b['hz']:.2f} Hz, double {b['double_hz']}" if b else "")


def test_pr144_window():
    """PR144 is the clip every one of these routines was derived from, and the
    one whose published rate was wrong before layers were separated."""
    print("\nPR144, frames 300-500 -- layer separation")
    video, why = have_clip("PR144")
    if not video:
        print(f"  SKIP  {why}")
        SKIP.append("PR144 window")
        return
    with tempfile.TemporaryDirectory() as td:
        out = run(["layers", str(video),
                   "--track", str(HERE / "golden" / "pr144_track.csv"),
                   "--names", "striated=sea,isotropic=cloud tops",
                   "--dark-below", "100", "--mask-rows", "985:1080:1:165",
                   "--n0", "300", "--n1", "500", "--out", td, "--fresh", "--json"], td)
    got = fields(out, "PR144/300-500")
    compare(got, WINDOW_BASELINE, "PR144/300-500")
    check(got.get("object vs sea", 0) - got.get("object vs cloud tops", 0) > 50,
          "PR144/300-500: the two layers are still distinguishable",
          "a single blended rate would be the regression this test exists to catch")


def test_pr144_full():
    """The published whole-clip numbers (docs/method.md section 4)."""
    print("\nPR144, whole clip -- the published values")
    video, why = have_clip("PR144")
    if not video:
        print(f"  SKIP  {why}")
        SKIP.append("PR144 full")
        return
    with tempfile.TemporaryDirectory() as td:
        out = run(["layers", str(video),
                   "--track", str(HERE / "golden" / "pr144_track.csv"),
                   "--names", "striated=sea,isotropic=cloud tops",
                   "--dark-below", "100", "--mask-rows", "985:1080:1:165",
                   "--out", td, "--fresh", "--json"], td)
    compare(fields(out, "PR144/full"), PUBLISHED, "PR144/full")


def main():
    full = "--full" in sys.argv
    print("McDonald UAP Toolkit — golden check against real clips")
    print(f"catalog: {catalog.active().name}")
    test_pr113_two_clicks()
    test_pr144_window()
    test_pr43_streak_by_motion()
    test_flyer5_wingbeat()
    if full:
        test_pr144_full()
    else:
        print("\n(--full also checks the whole-clip published values; tens of minutes)")

    if FAIL:
        print(f"\n{len(FAIL)} FAILED: {', '.join(FAIL)}")
        return 1
    print(f"\n{'ALL PASS' if not SKIP else 'ALL PASS (skipped: ' + ', '.join(SKIP) + ')'}")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):           # a pipe or a log file on Windows is cp1252, and the checks' names have arrows
        _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
