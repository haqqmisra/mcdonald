"""Does the camera stage find a zoom inside a track and the rate's steps at the camera's events; does
`readout` time a readout's ticks to the frame; does the frame rate of a field-rate MPEG come out right?

Synthetic scenes only, small and quick, each built so the answer is known:

- the frame rate: an MPEG-1 file drawn at 30000/1001 says 60000/1001 in its header (the field rate), and
  must be read as 30000/1001, with a note; a lossless copy carrying 30000/1001 must read the same, with none;
- an elongated object drifting left, the picture zooming x2 about a point near its centre: the step's
  frame, ratio and centre must come back, and the track taken back to one scale must be one straight line;
- an object that only grows (it comes nearer), and one whose size steps where it sits at the zoom's
  centre, and one whose size steps with a jump that no zoom about the frame's middle makes: no zoom, a
  zoom it cannot place, and a step that is not called a zoom;
- a rate that steps once: one breakpoint, at the step, and at the camera's event if one is given there;
  a steady rate over several noise draws: no breakpoint;
- the released-track null on stretches faster and no faster than the camera had been turning;
- a readout drawn with ticks at known frames, one of them dithering: each tick to the frame, the rate,
  and that a readout holding still to the end at that rate cannot say whether the camera stopped;
- a track held at the boresight: held, not "not uniform".

    python3 tests/test_camera.py        # or: pytest tests/

No video data needed (the frame-rate check draws two short clips with ffmpeg).
"""
import math
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import camera, clip as vclip, kinematics as kin, readout  # noqa: E402

FAIL = []
FPS = 30000 / 1001
W, H = 352, 240


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


class Frames:
    """What the stages read of a clip: grey frames by number, the window, the size and the rate."""

    def __init__(self, frames, fps=FPS):
        self._f = frames
        self.n0, self.n1 = min(frames), max(frames)
        self.H, self.W = next(iter(frames.values())).shape
        self.fps = fps

    def grey(self, n):
        return self._f[n]


def blob(x, y, sx, sy, amp=120.0):
    yy, xx = np.mgrid[:H, :W]
    return amp * np.exp(-0.5 * (((xx - x) / sx) ** 2 + ((yy - y) / sy) ** 2))


def zoom_scene(n_frames=40, at=21, ratio=2.0, centre=(176.0, 120.0), start=(168.0, 118.0), v=(-1.5, 0.0),
               sx=2.5, sy=1.0, grow=None, seed=1, noise=2.0):
    """An object on a dark sky, moving at v px/frame in the first zoom's pixels; from frame `at` the picture is
    magnified `ratio` times about `centre`. Returns (Frames, {frame: true displayed position})."""
    rng = np.random.default_rng(seed)
    frames, truth = {}, {}
    c = np.array(centre)
    for n in range(1, n_frames + 1):
        p = np.array(start) + (n - 1) * np.array(v)
        z = ratio if n >= at else 1.0
        g = 1.0 if grow is None else grow(n)
        q = c + z * (p - c)
        frames[n] = 30.0 + blob(q[0], q[1], sx * z * g, sy * z * g) + rng.normal(0, noise, (H, W))
        truth[n] = (float(q[0]), float(q[1]))
    return Frames(frames), truth


def track_of(frames, truth, seed=2, sd=0.3):
    rng = np.random.default_rng(seed)
    return {n: (x + rng.normal(0, sd), y + rng.normal(0, sd)) for n, (x, y) in truth.items()}


def test_frame_rate():
    print("\nthe frame rate of an MPEG-1 file whose header gives the field rate")
    with tempfile.TemporaryDirectory() as td:
        mpg, mkv = f"{td}/vcd.mpg", f"{td}/copy.mkv"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=352x240:rate=30000/1001",
                        "-t", "1", "-c:v", "mpeg1video", mpg], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-r", "30000/1001", "-i", mpg, "-c:v", "ffv1", mkv], check=True)
        i, j = vclip.probe(mpg), vclip.probe(mkv)
        hdr = i["stream"]["r_frame_rate"]
        check(hdr == "60000/1001", "the drawn MPEG-1's header says the field rate", hdr)
        check(i["fps"] == Fraction(30000, 1001), "it is read as 30000/1001", str(i["fps"]))
        check(bool(i["fps_note"]) and "field rate" in i["fps_note"], "and the record says why", str(i["fps_note"]))
        check(j["fps"] == Fraction(30000, 1001) and j["fps_note"] is None, "the lossless copy reads the same, with no note",
              f"{j['fps']} {j['fps_note']}")
        from mcdonald import audio
        check(audio.probe(mpg)["fps"] == Fraction(30000, 1001), "the audio stage folds through the same rate")
        c = vclip.Clip(mpg, f"{td}/frames", extract=False)
        check(abs(c.fps - 30000 / 1001) < 1e-9 and c.n1 <= 33,
              "a Clip counts its frames at that rate, not twice as many", f"{c.fps:.4f} fps, last frame {c.n1} of 30")
    s = {"r_frame_rate": "30/1", "avg_frame_rate": "28543/1000"}
    check(vclip.frame_rate(s) == (Fraction(30), None), "a variable-rate phone file keeps its r_frame_rate")


def test_shape():
    print("\nthe object's image: its length along its long axis")
    f = 30.0 + blob(150.0, 100.0, 4.0, 1.5)
    s = camera.shape(f, 150.0, 100.0, size=9.0)
    want = 2.355 * 4.0
    check(abs(s["length_px"] / want - 1) < 0.15, "length within 15 % of the Gaussian's FWHM",
          f"{s['length_px']:.2f} against {want:.2f}")
    along = min(s["angle_deg"] % 180, 180 - s["angle_deg"] % 180) < 5
    check(s["width_px"] < s["length_px"] / 2 and along, "long axis along the frame's x",
          f"angle {s['angle_deg']:.1f} deg, width {s['width_px']:.2f}")


def test_zoom_found_and_placed():
    print("\na x2 zoom inside the track, about a point near the frame's centre")
    fr, truth = zoom_scene()
    trk = track_of(fr, truth)
    shp = camera.shapes(fr, trk)
    st = camera.zoom_steps(trk, shp, W, H)
    check(len(st) == 1, "one zoom step", f"{len(st)}")
    if not st:
        return
    s = st[0]
    check(s["frame"] == 21, "at the frame the picture changed", f"{s['frame']}")
    check(abs(s["ratio"] / 2.0 - 1) < 0.08, "ratio within 8 % of 2", f"{s['ratio']:.3f}")
    check(s["centre"] is not None and math.hypot(s["centre"][0] - 176, s["centre"][1] - 120) < 2.0,
          "centre within 2 px of where it zoomed about", f"{s['centre']}")
    check(s["confirmed_by_offset"], "confirmed by the offset's jump")
    one = camera.to_one_scale(trk, st, W, H)
    seg, sig = camera.rate_steps(one, FPS)
    check(all(abs(x["v_px_per_s"] / (1.5 * FPS) - 1) < 0.08 for x in seg),
          "taken back to one scale, the rate is the same either side of the zoom",
          ", ".join(f"{x['frames']} {x['v_px_per_s']:.1f}" for x in seg) + f" against {1.5 * FPS:.1f} px/s")
    jump = max(abs(one[21][0] - (one[20][0] - 1.5)), abs(one[21][1] - one[20][1]))
    check(jump < 1.5, "and the zoom's jump is gone to under 1.5 px", f"{jump:.2f} px")
    raw, _ = camera.rate_steps(trk, FPS)
    after = [x for x in raw if x["frames"][0] >= 21]
    check(len(raw) >= 2 and after and abs(after[0]["v_px_per_s"] / (3.0 * FPS) - 1) < 0.08,
          "left in its own pixels, the rate after the zoom is twice the rate before",
          ", ".join(f"{x['frames']} {x['v_px_per_s']:.1f}" for x in raw))


def test_not_zooms():
    print("\nwhat is not a zoom, or not one that can be placed")
    fr, truth = zoom_scene(ratio=1.0, grow=lambda n: 1.0 + 0.6 * (n - 1) / 39)
    trk = track_of(fr, truth)
    check(camera.zoom_steps(trk, camera.shapes(fr, trk), W, H) == [], "an object that grows by 60 % over 40 frames: none")
    fr, truth = zoom_scene(start=(176.0, 120.0), v=(0.0, 0.0))
    trk = track_of(fr, truth)
    st = camera.zoom_steps(trk, camera.shapes(fr, trk), W, H)
    check(len(st) == 1 and st[0]["centre"] is None and not st[0]["confirmed_by_offset"],
          "a zoom on an object at its centre: a step, but its centre cannot be placed",
          f"{[(s['frame'], round(s['ratio'], 2), s['centre']) for s in st]}")
    fr, truth = zoom_scene(ratio=1.0, start=(120.0, 118.0), v=(0.0, 0.0), grow=lambda n: 1.7 if n >= 21 else 1.0)
    truth = {n: ((x - 9.0, y) if n >= 21 else (x, y)) for n, (x, y) in truth.items()}
    frs = {}
    for n in fr._f:
        x, y = truth[n]
        g = 1.7 if n >= 21 else 1.0
        frs[n] = 30.0 + blob(x, y, 2.5 * g, 1.0 * g) + np.random.default_rng(n).normal(0, 2.0, (H, W))
    fr = Frames(frs)
    trk = track_of(fr, truth)
    st = camera.zoom_steps(trk, camera.shapes(fr, trk), W, H)
    check(len(st) == 1 and not st[0]["confirmed_by_offset"],
          "a size step with a jump that no zoom about the middle makes: not confirmed as a zoom",
          f"{[(s['frame'], round(s['ratio'], 2), s['centre'], s['confirmed_by_offset']) for s in st]}")


def piecewise(v1=1.0, v2=3.0, n1=20, n2=20, sd=0.3, seed=1):
    rng = np.random.default_rng(seed)
    trk, x = {}, 100.0
    for n in range(1, n1 + n2 + 1):
        x += v1 if n <= n1 else v2
        trk[n] = (x + rng.normal(0, sd), 120.0 + rng.normal(0, sd))
    return trk


def test_rate_steps():
    print("\nthe rate's steps, and the camera's events")
    seg, sig = camera.rate_steps(piecewise(), FPS)
    check(len(seg) == 2, "a rate that steps once: two stretches", f"{len(seg)}")
    check(len(seg) == 2 and abs(seg[1]["frames"][0] - 21) <= 1, "the step at frame 21, to a frame",
          f"{[s['frames'] for s in seg]}")
    b = camera.at_events(seg, [(22, "a readout changes")])
    check(len(b) == 1 and b[0]["at_event"] and b[0]["frames_from_event"] == seg[1]["frames"][0] - 22,
          "set beside an event a frame away: at the camera's event")
    b = camera.at_events(seg, [(35, "a readout changes")])
    check(len(b) == 1 and not b[0]["at_event"], "and not beside one fourteen frames away")
    false = [len(camera.rate_steps(piecewise(v2=1.0, seed=s), FPS)[0]) for s in range(1, 9)]
    check(all(n == 1 for n in false), "a steady rate, eight noise draws: no breakpoint", f"{false}")
    long_trk = piecewise(v1=0.5, v2=2.0, n1=1500, n2=1500, sd=0.4)
    seg, _ = camera.rate_steps(long_trk, FPS)
    check(len(seg) == 2 and abs(seg[1]["frames"][0] - 1501) <= 3, "3000 frames: one step, found (the pruned search)",
          f"{[s['frames'] for s in seg]}")


def test_released():
    print("\nthe released-track null")
    st = [dict(frames=[1, 20], n=20, deg_per_s=0.0, err_deg_per_s=0.001),
          dict(frames=[30, 35], n=6, deg_per_s=0.261, err_deg_per_s=0.013),
          dict(frames=[36, 43], n=8, deg_per_s=0.152, err_deg_per_s=0.018)]
    r = camera.released(st, 0.252, 0.004)
    check(r["within_camera_rate"] and r["fastest"]["frames"] == [30, 35],
          "0.261 +- 0.013 against a camera that turned at 0.252: no faster than a release shows", f"z {r['z']:+.2f}")
    st[1]["deg_per_s"] = 0.5
    r = camera.released(st, 0.252, 0.004)
    check(not r["within_camera_rate"], "0.5: faster than the camera had been turning", f"z {r['z']:+.1f}")
    check(camera.released(st, 0.252, 0.004, after=40)["fastest"]["frames"] == [36, 43],
          "--after leaves out the stretches that end before it")


def readout_scene(values, fps=FPS, seed=3, dither=()):
    """A box with a number drawn in it: values[n] on frame n, and on the frames in `dither` the next value
    instead every other frame. Returns a Frames of a 40 x 24 picture."""
    from PIL import Image, ImageDraw
    from mcdonald.figures import pil_font
    rng = np.random.default_rng(seed)
    f = pil_font(14, bold=True)
    frames = {}
    for n, v in values.items():
        shown = v + (1 if (n in dither and n % 2) else 0)
        im = Image.new("L", (40, 24), 20)
        ImageDraw.Draw(im).text((8, 3), f"{shown:g}", fill=200, font=f)
        frames[n] = np.asarray(im, float) + rng.normal(0, 8, (24, 40))
    return Frames(frames, fps)


def test_readout_ticks():
    print("\na readout's ticks, to the frame")
    edges = [1, 61, 121, 181, 241]               # value 3 from frame 1, 4 from 61, 5 from 121, 6 from 181, to 300
    vals = {n: 3 + sum(n >= e for e in edges[1:]) for n in range(1, 301)}
    clip = readout_scene(vals, dither=set(range(177, 186)))
    stretches = [(5, 55, 3.0), (65, 115, 4.0), (125, 170, 5.0), (190, 235, 6.0), (245, 300, 7.0)]
    tk = readout.ticks(clip, (0, 0, 40, 24), stretches)
    got = [t["tick_frame"] for t in tk]
    check(all(abs(g - (e - 0.5)) <= 1.0 for g, e in zip(got[:2], edges[1:3])), "clean ticks to a frame",
          f"{got[:2]} against {[e - 0.5 for e in edges[1:3]]}")
    check(abs(got[2] - 180.5) <= 4 and tk[2]["dither_frames"] >= 5, "the dithered tick in the dither, its dither counted",
          f"{got[2]:.1f}, dither {tk[2]['dither_frames']}")
    r = readout.rate(tk, FPS, last_frame=330)
    want = 1.0 / (60 / FPS)
    check(r["rate_per_s"] is not None and abs(r["rate_per_s"] / want - 1) < 0.03, "the rate within 3 %",
          f"{r['rate_per_s']:.4f} against {want:.4f}")
    check(r["holds_to_end"] is False, "the readout ticks again before the end: its hold is not to the end")
    r = readout.rate(tk, FPS, last_frame=280)
    check(r["holds_to_end"] is True, "cut off before the next tick was due: holding still cannot say the camera stopped",
          f"next due at {r['next_tick_due_frame']:.0f}")
    back = readout.rate([dict(t, **{"from": t["to"], "to": t["from"]}) if i == 1 else t for i, t in enumerate(tk)], FPS)
    check(back["ticks_used"] < len(tk), "a run that goes back is not fitted through", f"{back['ticks_used']} of {len(tk)}")
    check(readout.parse_values("1-56:4, 61-115:3") == [(1, 56, 4.0), (61, 115, 3.0)], "values as typed")


def test_held():
    print("\na track held at the boresight")
    rng = np.random.default_rng(5)
    trk = {n: (177.3 + rng.normal(0, 0.45), 118.0 + rng.normal(0, 0.45)) for n in range(1, 120)}
    f = kin.fit_v_px(trk, FPS)
    check(f["held"] and f["uniform"], "held, and a rate of about zero describes it",
          f"span {f['span_px']:.1f} px, residual {f['resid_rms']:.2f}, noise {f['noise_px']:.2f}")
    trk = {n: (100 + 0.5 * n + 0.02 * n * n, 120.0 + rng.normal(0, 0.3)) for n in range(1, 60)}
    f = kin.fit_v_px(trk, FPS)
    check(not f["held"] and not f["uniform"], "a curving transit is neither", f"span {f['span_px']:.0f} px")


def test_commands():
    print("\nthe commands")
    from mcdonald import cli
    check("camera" in cli.COMMANDS and "readout" in cli.COMMANDS, "camera and readout are commands")
    from mcdonald import stages
    check("camera" in stages.STAGES and stages.STAGES.index("camera") == stages.STAGES.index("kinematics") + 1,
          "camera is a stage of run, after kinematics")


def main():
    test_frame_rate()
    test_shape()
    test_zoom_found_and_placed()
    test_not_zooms()
    test_rate_steps()
    test_released()
    test_readout_ticks()
    test_held()
    test_commands()
    if FAIL:
        print(f"\n{len(FAIL)} FAILED: {', '.join(FAIL)}")
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
