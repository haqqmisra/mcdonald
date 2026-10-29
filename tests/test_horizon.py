"""Does `mcdonald horizon` find the horizon, set the object against it, and bound its range or height right?

Rendered scenes and closed forms only, small and quick:

- the geometry: the dip from 7,000 ft with and without refraction, the range at which a ray just under the horizon
  meets the sea (the horizon's own distance) and one steeply down (h / sin of the depression, curvature a small part),
  the lowest height of a ray just over the horizon (zero), and a ray's height at its lowest point;
- a sea under a sky, the horizon tilted 1.5 deg, the point given 5 px off it: the line to a fraction of a pixel and
  its tilt to a tenth of a degree; followed over 40 frames while it drifts down and turns, under an overlay;
- an object below the line and one above it: the range bound and the height bound, each the conservative corner of
  its band; an object on the line, within its band: no bound;
- a frame with no horizon in it: none found.

    python3 tests/test_horizon.py        # or: pytest tests/

No video data needed.
"""
import math
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import horizon as hz  # noqa: E402

FAIL = []
W, H = 640, 360
H7000 = 7000 * 0.3048


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


class Frames:
    def __init__(self, frames):
        self._f = frames
        self.n0, self.n1 = min(frames), max(frames)
        self.H, self.W = next(iter(frames.values())).shape

    def grey(self, n):
        return self._f[n]


SEA = ndimage.gaussian_filter(np.random.default_rng(3).normal(size=(H * 2, W * 2)).astype(np.float32), (1.0, 6.0))
SEA = 14 * SEA / SEA.std()


def scene(y_mid, tilt_deg, seed=0, sky=150.0, sea=95.0, overlay=True):
    """A sky over a sea with waves, the horizon crossing the middle column at y_mid, tilted tilt_deg (down to the
    right), a soft edge of a pixel and a half; noise of 2 grey levels; and, where asked, white text and a reticle."""
    yy, xx = np.mgrid[:H, :W].astype(np.float32)
    line = y_mid + math.tan(math.radians(tilt_deg)) * (xx - W / 2)
    t = 1.0 / (1.0 + np.exp(np.clip(-(yy - line) / 0.8, -50, 50)))
    waves = SEA[(yy.astype(int) + 7 * seed) % (2 * H), xx.astype(int)]
    g = sky * (1 - t) + (sea + waves) * t + np.random.default_rng(seed).normal(0, 2.0, (H, W))
    if overlay:
        g[20:28, 30:200] = 250.0
        g[H // 2 - 1:H // 2 + 2, W // 2 - 40:W // 2 + 40] = 250.0
        g[H // 2 - 40:H // 2 + 40, W // 2 - 1:W // 2 + 2] = 250.0
    return g.astype(np.float32)


OVERLAY = np.zeros((H, W), bool)
OVERLAY[18:30, 28:202] = True
OVERLAY[H // 2 - 3:H // 2 + 4, W // 2 - 42:W // 2 + 42] = True
OVERLAY[H // 2 - 42:H // 2 + 42, W // 2 - 3:W // 2 + 4] = True


def test_geometry():
    print("\nhorizon: the geometry against closed forms, from 7,000 ft")
    d0, d1 = math.degrees(hz.dip(H7000, 0.0)), math.degrees(hz.dip(H7000))
    check(abs(d0 - math.degrees(math.sqrt(2 * H7000 / hz.R_EARTH))) < 0.003, "the dip with no refraction, sqrt(2h/R)",
          f"{d0:.4f} deg")
    check(abs(d1 / d0 - math.sqrt(1 - hz.KAPPA)) < 0.002, "refraction lowers it by sqrt(1 - kappa)", f"{d1:.4f} deg")
    r_h = math.sqrt(2 * H7000 * hz.radius())
    r = hz.surface_range(H7000, hz.dip(H7000) + 1e-6)
    check(abs(r / r_h - 1) < 0.02, "a ray just under the horizon meets the sea at the horizon's distance",
          f"{r / 1000:.1f} km against {r_h / 1000:.1f}")
    r = hz.surface_range(H7000, math.radians(30))
    check(abs(r / (H7000 / math.sin(math.radians(30))) - 1) < 0.005, "steeply down, h / sin(depression)", f"{r:.0f} m")
    check(hz.surface_range(H7000, hz.dip(H7000) - 1e-4) == math.inf, "just over the horizon: it never meets the sea")
    z = hz.lowest_height(H7000, -hz.dip(H7000) + 1e-9)
    check(abs(z) < 1.0, "the lowest height of a ray grazing the horizon: zero", f"{z:.2f} m")
    e = -hz.dip(H7000) + math.radians(0.5)
    rs = -(hz.radius() + H7000) * math.sin(e)
    check(abs(hz.height_at(H7000, e, rs) - hz.lowest_height(H7000, e)) < 0.5,
          "a ray's height at its closest approach is its lowest", f"{hz.lowest_height(H7000, e):.0f} m at {rs / 1000:.0f} km")


def test_the_line_is_found_and_followed():
    print("\nhorizon: a sea under a sky, tilted 1.5 deg, the point given 5 px off it")
    g = scene(170.0, 1.5)
    ln = hz.fit_line(g, 100.0, 170.0 + math.tan(math.radians(1.5)) * (100 - W / 2) - 5.0)
    check(ln is not None, "a line stands out")
    if ln is None:
        return
    y_at = ln["y0"] + ln["slope"] * (W / 2 - ln["x0"])
    check(abs(y_at - 170.0) < 0.4, "its height at the middle column to 0.4 px", f"{y_at:.2f} against 170.00")
    check(abs(math.degrees(math.atan(ln["slope"])) - 1.5) < 0.1, "its tilt to 0.1 deg",
          f"{math.degrees(math.atan(ln['slope'])):.2f} against 1.50")
    frames = {n: scene(150.0 + 1.2 * n, 1.5 - 0.02 * n, seed=n) for n in range(1, 41)}
    lines = hz.follow(frames, (1, 320.0, 151.0), OVERLAY)      # the overlay masked, as the command masks it
    errs = [abs(lines[n]["y0"] + lines[n]["slope"] * (W / 2 - lines[n]["x0"]) - (150.0 + 1.2 * n)) for n in lines]
    check(len(lines) == 40 and max(errs) < 0.5, "followed over 40 frames as it drifts 48 px and turns 0.8 deg",
          f"{len(lines)} frames, worst {max(errs):.2f} px")
    check(hz.fit_line(np.random.default_rng(9).normal(120, 3, (H, W)).astype(np.float32), 320.0, 180.0) is None,
          "a frame with no horizon: none")


def test_bounds_below_above_and_on_the_line():
    print("\nhorizon: an object below the line, one above it, one on it; from 7,000 ft, k 50 px/deg (a 12.8-deg field)")
    k = W / 12.8
    frames = {n: scene(160.0, 0.0, seed=n) for n in range(1, 21)}
    clip = Frames(frames)
    for dy, what in ((100.0, "below"), (-60.0, "above"), (0.5, "on")):
        track = {n: (300.0 + 2 * n, 160.0 + dy) for n in frames}
        f = hz.measure(clip, track, (1, 300.0, 160.0), H7000, k, 0.10, h_err=30.0)
        b = f.fields["bounds"]
        d = dy / k
        if what == "below":
            want = max(hz.surface_range(h, hz.dip(h, kap) + math.radians(dd * (1 + s)), kap)
                       for h in (H7000 - 30, H7000 + 30) for kap in (0.0, hz.KAPPA, hz.KAPPA_HI)
                       for dd in (d - 1.42 / k, d + 1.42 / k) for s in (-0.1, 0.1))
            check(b and b["below"] and abs(b["range_max_m"] / want - 1) < 0.03,
                  f"{dy:.0f} px below (2 deg): the range at most the band's farthest", b and f"{b['range_max_m'] / 1000:.2f} km "
                  f"against {want / 1000:.2f}; nominal {b['range_nominal_m'] / 1000:.2f}")
            check("range" in f.result and "IF it is seen against the sea" in f.result["range"], "said with its condition",
                  f.result.get("range", ""))
        elif what == "above":
            check(b and not b["below"] and 0 < b["height_min_m"] < b["height_nominal_m"],
                  f"{-dy:.0f} px above (1.2 deg): a height at least, under the nominal",
                  b and f"{b['height_min_m']:.0f} m (nominal {b['height_nominal_m']:.0f})")
        else:
            check(b and b["within_band"] and f.no_power, "on the line: within its band, no bound",
                  f.no_power and f.no_power[0][1])
    f = hz.measure(clip, {1: (300.0, 260.0)}, (1, 300.0, 160.0), None, k, 0.1)
    check(f.no_power and "height" in f.no_power[0][1], "no height given: no power, and it says what is missing",
          f.no_power and f.no_power[0][1])


def test_a_step_of_run():
    """The horizon and the haze as steps of `mcdonald run` (2026-10-29: the window's Measure form reaches them, and their
    bounds the four unknowns): with the camera's height and a point on the horizon -- typed, or a horizon mark -- and with a
    visibility, run_case does each as its own command does, the same call and the same numbers; the commands are recorded;
    neither is planned without what it needs; what cannot go together is refused before anything is measured."""
    print("\nhorizon and haze: steps of run")
    import shutil
    import subprocess
    import tempfile
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    from mcdonald import forensics as vf
    from mcdonald import haze, stages
    from mcdonald.mark import MarkSet
    n = 20
    track = {i: (300.0 + 2 * i, 100.0) for i in range(1, n + 1)}     # a dark thing 60 px above the horizon, against the sky
    yy, xx = np.mgrid[:H, :W]
    only = ["ingest", "track", "scale", "kinematics", "report"]
    with tempfile.TemporaryDirectory() as td:
        mkv = Path(td) / "sea.mkv"
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", "30",
                              "-i", "-", "-c:v", "ffv1", "-pix_fmt", "gray", str(mkv)], stdin=subprocess.PIPE)
        for i in range(1, n + 1):
            g = scene(160.0, 0.0, seed=i, overlay=False)
            g[np.hypot(xx - track[i][0], yy - track[i][1]) <= 4] = 60.0
            p.stdin.write(np.clip(g, 0, 255).astype(np.uint8).tobytes())
        p.stdin.close()
        p.wait()
        csv = Path(td) / "t.csv"
        csv.write_text("frame,x,y\n" + "".join(f"{i},{x},{y}\n" for i, (x, y) in track.items()), encoding="utf-8")
        case, clip, _ = stages.run_case(str(mkv), track=str(csv), workdir=f"{td}/frames", out=f"{td}/case", only=only, fov=12.8,
                                        height="7000ft", horizon="1,300,160", visibility="20km", band="visible",
                                        say=lambda *a: None)
        hf, zf = (case.stages.get(s, {}).get("fields") or {} for s in ("horizon", "haze"))
        masks = vf.static_masks(clip)
        own_h = hz.measure(clip, vf.read_track(csv), (1, 300.0, 160.0), H7000, W / 12.8, hz.K_SHARE_ASSUMED,
                           mask=masks["blocks"] | masks["graphics"], k_from="assumed").fields
        own_z = haze.measure(clip, vf.read_track(csv), 9.0, 20000.0, None, masks).fields
        from mcdonald import focus
        own_f = focus.measure(clip, vf.read_track(csv), W / 12.8, focus.K_SHARE_ASSUMED, "visible", masks=masks, rows=[],
                              k_from="assumed")
        b = hf.get("bounds") or {}
        check(b and not b["below"] and b["height_min_m"] == (own_h.get("bounds") or {}).get("height_min_m") and b["height_min_m"] > 0
              and zf.get("bound_m") and zf["bound_m"] == own_z["bound_m"],
              "a height and a point on the horizon, and a visibility: each step's numbers are its own command's",
              f"at least {b.get('height_min_m', 0):.0f} m over the sea; within {(zf.get('bound_m') or 0) / 1000:.2f} km")
        led = {r["symbol"]: r for r in case.ledger()}
        cmd = {s: next((c for c in case.commands if c.startswith(f"mcdonald {s} ")), "") for s in ("horizon", "haze", "focus")}
        ff = (case.stages.get("focus") or {}).get("fields")
        check(ff is not None and ff == own_f.fields and "--fov 12.8 --band visible" in cmd["focus"]
              and (case.stages["focus"]["no_power"] == own_f.no_power),
              "with the camera's band the focus step runs too (Jacob, 2026-10-29: the band starts it), its command's own "
              "call and numbers, its command recorded", cmd["focus"][-60:])
        known = stages.known_of(case)
        check(led["R"]["status"] == "bounded" and "by the haze" not in led["R"]["value"] and "haze" in led["R"]["by"]
              and "--horizon 1,300,160 --height 7000ft --fov 12.8" in cmd["horizon"] and "--visibility 20km" in cmd["haze"]
              and (known.get("height"), known.get("horizon"), known.get("visibility")) == ("7000ft", "1,300,160", "20km"),
              "the haze's ceiling is the range's bound among the four unknowns; each step's command is recorded, and what "
              "was known kept", f"{led['R']['value']} ({led['R']['by'][:40]}); {cmd['horizon'][-50:]}")
        # given afterwards (`add_known`, the report card's form, `mcdonald report CASE --height ...`): the same numbers
        later, _, _ = stages.run_case(str(mkv), track=str(csv), workdir=f"{td}/frames", out=f"{td}/later", clip=clip, only=only,
                                      fov=12.8, say=lambda *a: None)
        js = f"{td}/later/sea_case.json"
        got, _ = stages.add_known(js, workdir=f"{td}/frames", height="7000ft", horizon="1,300,160", visibility="20km",
                                  band="visible")
        same = all(got.stages[s]["fields"] == case.stages[s]["fields"] for s in ("horizon", "haze", "focus"))
        gone, _ = stages.add_known(js, workdir=f"{td}/frames", height=None, horizon=None, band=None)
        check("horizon" not in later.stages and same and "haze" in gone.stages and "horizon" not in gone.stages
              and "focus" not in gone.stages and sum(stages.NOTES_OF["haze"](n) for n in gone.notes) == 1
              and not any(stages.NOTES_OF["focus"](n) or stages.NOTES_OF["horizon"](n) for n in gone.notes)
              and {"height", "horizon"}.isdisjoint(stages.known_of(gone)),
              "given afterwards, the three steps are done on the track already followed, to the same numbers; forgotten, the "
              "horizon's and the focus's go with their notes and the haze's stays, its note once", f"same {same}; {sorted(gone.stages)}")
        ms = MarkSet("sea", str(mkv), 30.0)
        ms.add("horizon", 3, 310.0, 161.0)
        ms.save(f"{td}/sea_marks.json")
        check(stages.horizon_point(None, f"{td}/sea_marks.json") == (3, 310.0, 161.0) and stages.horizon_point(None) is None,
              "with no point typed, the first horizon mark is the point (as `mcdonald horizon --marks` takes it)")
        bare, _, _ = stages.run_case(str(mkv), track=str(csv), workdir=f"{td}/frames", out=f"{td}/bare", clip=clip,
                                     only=["ingest", "track", "report"], height="2100m", say=lambda *a: None)
        npw = (bare.stages.get("horizon") or {}).get("no_power") or [("", "")]
        check("no point on the sea's horizon" in npw[0][1] and "haze" not in bare.stages,
              "a height with no point on the horizon is said to want one; no visibility, no haze step", npw[0][1])
    plain = stages.planned(only=only)
    check("horizon" not in plain and "haze" not in plain
          and stages.planned(only=only, height="7000ft", visibility="20km") == ["ingest", "track", "scale", "kinematics",
                                                                               "horizon", "haze", "report"]
          and stages.planned(only=only, haze_reference="1,2,3,4000")[-2] == "haze"
          and stages.planned(only=only, visibility="20km", band="lwir")[-3:] == ["haze", "focus", "report"],
          "planned only where what each needs is given, in run_case's order", ", ".join(stages.planned(only=only, height="1m")))
    said = []
    for bad in (dict(horizon="1,300,160"), dict(height="tall"), dict(height="7000ft", horizon="300,160"),
                dict(visibility="20km", haze_reference="1,2,3,4000"), dict(haze_reference="1,2,3"), dict(visibility="far"),
                dict(band="xray"), dict(pupil="10cm"), dict(band="mwir", pupil="wide")):
        try:
            stages.check_known(**bad)
            said.append(None)
        except ValueError as e:
            said.append(str(e))
    check(all(said) and "--height" in said[0] and "one of them" in said[3] and "one of visible" in said[6]
          and "--band too" in said[7],
          "a point with no height, a height or a point or a reference that cannot be read, and two measures of the haze "
          "are refused before anything is measured", " / ".join(str(x) for x in said)[:160])


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
