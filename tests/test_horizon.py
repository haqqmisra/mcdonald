"""Does `mcdonald horizon` find the horizon, set the object against it, and bound its range or height right?

Rendered scenes and closed forms only, small and quick:

- the geometry: the dip from 7,000 ft with and without refraction, the range at which a ray just under the horizon
  meets the sea (the horizon's own distance) and one steeply down (h / sin of the depression, curvature a small part),
  the lowest height of a ray just over the horizon (zero), and a ray's height at its lowest point;
- refraction outside the band (W8): which bound it breaks and by how much, both bounds growing with kappa, and a kappa
  of 1 or more (a duct) refused with its reason by the geometry, the stage (no power) and the command (its error);
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


def test_refraction_outside_the_band():
    """W8 (the air-and-sea survey's finding, rebuilt 2026-11-13 with these functions): refraction outside the band breaks
    one bound each way, and only that way, because the range to the sea and a ray's lowest height both grow with kappa;
    a kappa of 1 or more is a duct, with no horizon, and every function of the geometry refuses it with that reason
    (radius(1.0) divided by zero, and above 1 a range came back negative)."""
    print("\nhorizon: refraction outside the band, and a duct (W8)")

    def rng(d, kap, h=H7000):                      # the sea's range along a ray d deg below the line the camera sees
        return hz.surface_range(h, hz.dip(h, kap) + math.radians(d), kap)

    def low(d, kap, h=H7000):                      # the lowest height of a ray d deg above it
        return hz.lowest_height(h, -hz.dip(h, kap) + math.radians(d), kap)

    top, floor = rng(2.0, hz.KAPPA_HI), low(0.5, hz.KAPPA_LO)
    got = [100 * (rng(2.0, kap) / top - 1) for kap in (0.5, 0.75)] + [100 * (low(0.5, kap) / floor - 1) for kap in (-0.25, -0.5)]
    check(all(abs(g - w) < 0.2 for g, w in zip(got, (6.7, 17.2, -8.6, -15.3))),
          "from 7,000 ft: the sea 2 deg below the line is farther than the band's top at kappa 0.5 and 0.75, and a ray 0.5 "
          "deg above it lower than the band's bottom at -0.25 and -0.5", "  ".join(f"{g:+.1f} %" for g in got)
          + f"  (of {top / 1000:.2f} km and {floor:.0f} m)")
    ks = [-1.0 + 0.02 * i for i in range(100)]     # -1 to 0.98
    rise = all(all(b >= a for a, b in zip(v, v[1:]))
               for h in (10.0, 100.0, H7000, 12000.0) for d in (0.05, 0.5, 2.0, 10.0)
               for v in ([rng(d, kap, h) for kap in ks], [low(d, kap, h) for kap in ks]))
    check(rise, "both grow with kappa from -1 to 0.98, at four heights and four angles: the band's two ends are its corners, "
                "and each bound breaks one way only")
    said = []
    for kap in (1.0, 1.2, 1.5, math.inf, math.nan):
        for fn in (lambda: hz.radius(kap), lambda: hz.dip(H7000, kap), lambda: hz.surface_range(H7000, 0.05, kap),
                   lambda: hz.lowest_height(H7000, -0.01, kap), lambda: hz.height_at(H7000, -0.01, 1e4, kap)):
            try:
                said.append(repr(fn()))
            except ValueError as e:                # a ZeroDivisionError, or a number, fails the check
                said.append(str(e))
    check(all("is a duct" in s for s in said[:15]) and all("must be a number" in s for s in said[15:]),
          "a kappa of 1 or more is refused as a duct by every function of the geometry, and one that is no number as that",
          said[0])
    bad = []
    for band in ((0.0, 1.0), (0.3, 0.1), "wide", (0.0, math.nan)):
        try:
            bad.append(repr(hz.band_of(band)))
        except ValueError as e:
            bad.append(str(e))
    texts = []
    for text in ("0,1.2", "1", "0,0.2,0.4", "warm", ""):
        try:
            texts.append(repr(hz.parse_kappa(text)))
        except ValueError as e:
            texts.append(str(e))
    check("is a duct" in bad[0] and "is above" in bad[1] and "two numbers" in bad[2] and "two numbers" in bad[3]
          and "is a duct" in texts[0] and "is a duct" in texts[1] and all("LOW,HIGH" in t for t in texts[2:])
          and hz.band_of() == (0.0, hz.KAPPA, hz.KAPPA_HI) and hz.band_of((-0.5, 0.75)) == (-0.5, hz.KAPPA, 0.75)
          and hz.band_of(0.5) == (0.5, 0.5, 0.5) and hz.band_of((0.3, 0.5))[1] == 0.4
          and hz.parse_kappa("-0.5,0.25") == (-0.5, 0.25) and hz.parse_kappa("0.17") == (0.17, 0.17),
          "a band is read as LOW,HIGH or one value, its nominal 0.13 where it holds it; one that reaches 1, runs the wrong "
          "way or cannot be read is refused with its reason", " / ".join(bad[:2] + texts[2:3])[:200])
    wide, own = (-0.5, 0.75), hz.bounds(2.0, 0.0, H7000, 0.0, 0.0)
    b = hz.bounds(2.0, 0.0, H7000, 0.0, 0.0, kappa=wide)
    a = hz.bounds(-0.5, 0.0, H7000, 0.0, 0.0, kappa=wide)
    a0 = hz.bounds(-0.5, 0.0, H7000, 0.0, 0.0)
    check(b["range_max_m"] == rng(2.0, 0.75) and b["breaks_if_kappa_above"] == 0.75 and "breaks_if_kappa_below" not in b
          and a["height_min_m"] == low(0.5, -0.5) and a["breaks_if_kappa_below"] == -0.5 and "breaks_if_kappa_above" not in a
          and own["range_max_m"] == top and own["breaks_if_kappa_above"] == hz.KAPPA_HI
          and a0["height_min_m"] == floor and a0["breaks_if_kappa_below"] == 0.0
          and own == hz.bounds(2.0, 0.0, H7000, 0.0, 0.0, kappa=(0.0, hz.KAPPA_HI)),
          "a band given moves each bound to its own end, and says where it breaks: the range above its top, the height "
          "below its bottom; with none given the stage's 0 to 0.25, as before",
          f"at most {b['range_max_m'] / 1000:.2f} km (the stage's band {own['range_max_m'] / 1000:.2f}); at least "
          f"{a['height_min_m']:.0f} m ({a0['height_min_m']:.0f})")


def test_the_command_refuses_a_duct():
    """`--kappa` typed with 1 or more is the command's error, with the reason, before anything is read or measured: exit 2
    (the command line was wrong), and with --json the envelope every command prints."""
    print("\nhorizon: --kappa of 1 or more on the command line")
    import json
    import os
    import shutil
    import subprocess
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent.parent / "src"))
    p = subprocess.run([sys.executable, "-m", "mcdonald.cli", "horizon", "no-such-video.mp4", "--track", "no-such.csv",
                        "--horizon", "1,300,160", "--height", "7000ft", "--fov", "12.8", "--kappa=0,1.2", "--json"],
                       capture_output=True, env=env, encoding="utf-8", errors="replace")
    try:
        d = json.loads(p.stdout)
    except ValueError:
        d = None
    check(p.returncode == 2 and d is not None and d["exit"] == 2 and "--kappa 0,1.2" in (d["error"] or "")
          and "is a duct" in d["error"] and "Traceback" not in p.stderr,
          "refused before the video is looked for: exit 2, the reason on stderr and in the envelope",
          f"exit {p.returncode}; {(d or {}).get('error') or p.stderr[-200:]}")


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
            way = [n for n in f.notes if n.startswith("The horizon's limit on range")]
            check(abs(b["range_max_m"] / 1000 - 42.40) < 0.1 and abs(b["range_nominal_m"] / 1000 - 37.81) < 0.1
                  and f.fields["kappa"] == [0.0, hz.KAPPA, hz.KAPPA_HI] and b["breaks_if_kappa_above"] == hz.KAPPA_HI
                  and len(way) == 1 and "no more than 0.25" in way[0] and "farther than that limit" in way[0]
                  and any("kappa 0.25" in s and "puts the sea farther" in s for s in hz.said(f.fields)),
                  "the bound is what it was before W8 (42.4 km, nominal 37.8), and a note and the command's lines say which "
                  "way refraction breaks it", way and way[0])
            g = hz.measure(clip, track, (1, 300.0, 160.0), H7000, k, 0.10, h_err=30.0, kappa=(0.0, 0.75))
            gb = g.fields["bounds"]
            check(gb["range_max_m"] > 1.1 * b["range_max_m"] and gb["breaks_if_kappa_above"] == 0.75
                  and g.fields["kappa"] == [0.0, hz.KAPPA, 0.75] and g.fields["kappa_from"] == "given"
                  and any("no more than 0.75" in n for n in g.notes) and "at 0.75" in g.result["dip"],
                  "with a wider band given (to kappa 0.75) the range bound is farther, and the words follow the band",
                  f"at most {gb['range_max_m'] / 1000:.2f} km against {b['range_max_m'] / 1000:.2f}")
            for duct in ((0.0, 1.0), (0.0, 1.5), 1.2):
                g = hz.measure(clip, track, (1, 300.0, 160.0), H7000, k, 0.10, h_err=30.0, kappa=duct)
                check(g.fields["bounds"] is None and g.fields["kappa"] is None and len(g.no_power) == 1
                      and "is a duct" in g.no_power[0][1] and "horizon line" in g.result and "range" not in g.result,
                      f"a band that reaches 1 ({duct}): no power with the reason, the line still found, no bound and no failure",
                      g.no_power and g.no_power[0][1])
        elif what == "above":
            check(b and not b["below"] and 0 < b["height_min_m"] < b["height_nominal_m"],
                  f"{-dy:.0f} px above (1.2 deg): a height at least, under the nominal",
                  b and f"{b['height_min_m']:.0f} m (nominal {b['height_nominal_m']:.0f})")
            way = [n for n in f.notes if n.startswith("The horizon's limit on height")]
            g = hz.measure(clip, track, (1, 300.0, 160.0), H7000, k, 0.10, h_err=30.0, kappa=(-0.5, 0.25))
            gb = g.fields["bounds"]
            check(abs(b["height_min_m"] - 1935) < 2 and abs(b["height_nominal_m"] - 2096) < 2
                  and b["breaks_if_kappa_below"] == 0.0 and len(way) == 1 and "0 or more" in way[0]
                  and "lower than that limit" in way[0] and gb["height_min_m"] < b["height_min_m"] - 50
                  and gb["breaks_if_kappa_below"] == -0.5 and any("-0.5 or more" in n for n in g.notes),
                  "the bound is what it was before W8 (1,935 m, nominal 2,096), a note says a sea warmer than the air breaks "
                  "it, and a band given down to kappa -0.5 lowers it", f"{gb['height_min_m']:.0f} m against "
                  f"{b['height_min_m']:.0f}; {way and way[0][:90]}")
        else:
            check(b and b["within_band"] and f.no_power, "on the line: within its band, no bound",
                  f.no_power and f.no_power[0][1])
            check(not any(n.startswith("The horizon's limit on") for n in f.notes), "and no word on a bound that is not given")
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
        ways = [[n for n in c.notes if n.startswith("The horizon's limit on height")] for c in (case, got, gone)]
        check([len(w) for w in ways] == [1, 1, 0] and ways[0] == ways[1],
              "which way refraction breaks the height's bound is among the case's notes, once, and goes with the step",
              ways[0] and ways[0][0][:100])
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
