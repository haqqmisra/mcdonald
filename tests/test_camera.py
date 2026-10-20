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


def test_frame_count():
    """A file whose header gives no frame count (MPEG program streams, MKV): the count is not the container's duration,
    which its sound may outlast (FLIR1's 2007 copy: 2294 from the duration, 2290 packets, 2289 frames)."""
    print("\nthe frame count of a file whose header gives none")
    with tempfile.TemporaryDirectory() as td:
        mpg = f"{td}/program.mpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=352x240:rate=30000/1001",
                        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-map", "0:v", "-map", "1:a",
                        "-frames:v", "30", "-t", "1", "-c:v", "mpeg1video", "-c:a", "mp2", "-f", "mpeg", mpg], check=True)
        i = vclip.probe(mpg)
        check(i["nb_frames"] == 0 and i["frames_from"] == "packets" and 30 <= i["frames"] <= 32,
              "no count in its header: its video packets are counted", f"{i['frames']} from {i['frames_from']}")
        mkv = f"{td}/copy.mkv"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mpg, "-map", "0:v", "-c:v", "ffv1", mkv], check=True)
        j = vclip.probe(mkv)
        check(j["frames_from"] == "packets" and j["frames"] == 30, "an MKV's packets are its frames", f"{j['frames']}")
        # a count three frames long, as the duration of a file whose sound outlasts its picture gives
        real = vclip.frame_count
        vclip.frame_count = lambda *a: (33, "duration")
        try:
            c = vclip.Clip(mkv, f"{td}/frames")
            check(c.n1 == 30 and c.total == 30 and c.extracted(), "a window to the end ends on the last frame ffmpeg gives",
                  f"last {c.n1} of a count of 33")
            again = vclip.Clip(mkv, f"{td}/frames", extract=False)
            check(again.n1 == 30 and again.extracted(),
                  "the next Clip of it starts from that end, and finds its window on disk", f"last {again.n1}")
            part = vclip.Clip(mkv, f"{td}/frames", 5, 12)
            check((part.n0, part.n1) == (5, 12), "a window inside the clip is left as it was given", f"{part.n0}-{part.n1}")
        finally:
            vclip.frame_count = real


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
    check(len(st) == 1 and not st[0]["applied"] and camera.to_one_scale(trk, st, W, H) == trk
          and camera.scale_at(30, st) == 1.0, "and not taken out of the track: the object's own size step, said to be",
          f"{st[0]['why_not'] if st else ''}")
    st = camera.zoom_steps(trk, camera.shapes(fr, trk), W, H, ratios=[1.7])
    check(len(st) == 1 and st[0]["applied"] and st[0]["ratio_from"] == "given",
          "the same step with its ratio given (the sensor says it zoomed): taken as the zoom")
    # PR135's birds (2026-10-20): the half-maximum blob takes in a neighbour or a wing for two to four frames, then
    # lets it go -- the median of four frames held, so 0.3.2's branch called five of six birds' tracks zooms
    rng = np.random.default_rng(5)
    flip = [1.0] * 12 + [2.3, 2.3, 1.0, 2.3, 2.2, 2.3, 2.4, 1.0, 1.0, 1.0, 2.2, 2.3, 2.3, 2.2, 1.0, 2.3, 2.2] + [1.0] * 11
    frs, truth = {}, {}
    for n in range(1, len(flip) + 1):
        x, y = 140.0 - 1.2 * n, 100.0
        frs[n] = 30.0 + blob(x, y, 2.5 * flip[n - 1], 1.4 * (1 + 0.4 * (flip[n - 1] > 1))) + rng.normal(0, 2.0, (H, W))
        truth[n] = (x, y)
    fr = Frames(frs)
    trk = track_of(fr, truth)
    st = camera.zoom_steps(trk, camera.shapes(fr, trk), W, H)
    check(st == [], "a blob whose size flips back and forth for a few frames at a time: no step",
          f"{[(s['frame'], round(s['ratio'], 2)) for s in st]}")


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
    seg, _ = camera.rate_steps(piecewise(), FPS)
    b = camera.at_events(seg, [])
    check(len(b) == 1 and not b[0]["jump"], "a rate that steps is continuous: no jump where it does",
          f"{b[0]['jump_px']:.2f} px" if b else "")
    glitch = piecewise(v2=1.0)
    for n in range(21, 26):                          # a tracker on another feature 6 px off, for five frames
        glitch[n] = (glitch[n][0], glitch[n][1] + 6.0)
    seg, _ = camera.rate_steps(glitch, FPS)
    b = camera.at_events(seg, [])
    check(sum(x["jump"] for x in b) == 2 and len(seg) == 3,
          "five frames on another feature 6 px away: two jumps, out and back, and not two rate steps",
          f"{[(x['frame'], round(x['jump_px'] or 0, 1), x['jump']) for x in b]}")
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


SEG = {"a": (0, 0, 1, 0), "b": (1, 0, 1, 1), "c": (1, 1, 1, 2), "d": (0, 2, 1, 2), "e": (0, 1, 0, 2), "f": (0, 0, 0, 1),
       "g": (0, 1, 1, 1)}
DIGIT = {0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgedc", 7: "abc", 8: "abcdefg", 9: "abcdfg"}


def digits(text, x0, y0, w=4, h=4):
    """A mask of seven-segment digits drawn one pixel wide, each w x 2h, a gap of 3 between them."""
    m = np.zeros((H, W), bool)
    for k, ch in enumerate(text):
        for s in DIGIT[int(ch)]:
            a, b, c, d = SEG[s]
            xa, xb = sorted((x0 + k * (w + 3) + a * w, x0 + k * (w + 3) + c * w))
            ya, yb = sorted((y0 + b * h, y0 + d * h))
            m[ya:yb + 1, xa:xb + 1] = True
    return m


def overlay_scene(n_frames=180, seed=11):
    """FLIR1's kinds of events, drawn at 352 x 240 on a dark sky (40 DN) with white symbology (200): a two-digit readout
    that ticks 13 -> 14 at frame 31 and 14 -> 15 at 71, then dithers between 15 and 16 over 110-116 and settles on 16; a
    clock whose last digit ticks every 30 frames (16, 46, 76, ...); a gate's two bars beside the object that vanish at frame 91; the
    picture's level stepping from 40 to 70 at 130 (a gain step); frames 150-152 held on 149; and a crosshair that never
    moves. Returns (a clip of them, the object's track)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[:H, :W]
    cross = ((np.abs(yy - 200) <= 0) & (np.abs(xx - 60) <= 14)) | ((np.abs(xx - 60) <= 0) & (np.abs(yy - 200) <= 14))
    frames, track = {}, {}
    for n in range(1, n_frames + 1):
        if 150 <= n <= 152:
            frames[n] = frames[149]
            track[n] = track[149]
            continue
        x, y = 176.0 + 0.1 * n, 120.0
        bg = 40.0 if n < 130 else 70.0
        f = bg + rng.normal(0, 3.0, (H, W)) + blob(x, y, 2.0, 2.0, amp=90.0)
        value = 13 if n < 31 else 14 if n < 71 else 15 if n < 110 else (15 + (n % 2) if n <= 116 else 16)
        ov = cross | digits(f"{value:02d}", 160, 20) | digits(f"{(n + 14) // 30 % 10}0", 250, 200)
        if n < 91:
            ov |= ((xx == int(round(x - 9))) | (xx == int(round(x + 9)))) & (np.abs(yy - y) <= 8)
        f[ov] = 200.0
        frames[n] = f
        track[n] = (x, y)

    class Clip(Frames):
        def frames(self):
            return range(self.n0, self.n1 + 1)

        def rgb(self, n):
            return np.repeat(self.grey(n)[:, :, None], 3, 2).astype(np.float32)
    return Clip(frames), track


def test_overlay_events():
    """`mcdonald events` (2026-10-20): the overlay's own events found from its pixels, which `camera --events` was given
    by hand. Each kind drawn where it is known."""
    print("\nthe overlay's own events, found")
    from mcdonald import events
    clip, track = overlay_scene()
    f = events.find(clip, track, size=4.0).fields
    near = lambda frames, at, tol=2: any(abs(x - at) <= tol for x in frames)
    boxes = f["boxes"]
    read = [b for b in boxes if b["box"][1] <= 20 <= b["box"][3] and b["box"][0] <= 160 <= b["box"][2]]
    clock = [b for b in boxes if b["box"][1] <= 200 <= b["box"][3] and b["box"][0] <= 252 <= b["box"][2]]
    check(len(read) == 1 and len(clock) == 1, "the readout and the clock are found as boxes of text, the crosshair is not",
          f"{[b['name'] for b in boxes]}")
    if read:
        tk = [t["frame"] for t in read[0]["ticks"] if not t["with_picture"]]
        check(near(tk, 31) and near(tk, 71) and near(tk, 113, 5), "the readout's ticks at 31 and 71, and its dither as one",
              f"{tk}")
        d = [t for t in read[0]["ticks"] if 105 <= t["frame"] <= 120]
        check(len(d) == 1 and d[0]["dither_frames"] >= 4, "the dither over 110-116 is one tick, with its frames counted",
              f"{[(t['frame'], t['dither_frames']) for t in d]}")
    if clock:
        ck = clock[0]["clock"]
        check(ck is not None and abs(ck["period_frames"] - 30.0) < 0.5 and not ck["early_late"],
              "the clock is a clock, ticking every 30 frames, none early or late",
              f"{ck and round(ck['period_frames'], 2)}")
    gate = [g["frame"] for g in f["gate"] if "vanishes" in g["what"]]
    check(near(gate, 91), "the gate round the object vanishes at 91", f"{[(g['frame'], g['what']) for g in f['gate']]}")
    check(near([s["frame"] for s in f["picture"] if s["what_key"] == "level"], 130),
          "the picture's level steps at 130", f"{[(s['frame'], s['what']) for s in f['picture']]}")
    check(any(a <= 150 and b >= 152 for a, b in f["held"]), "frames 150-152 held", f"{f['held']}")
    ev = [e[0] for e in events.as_camera_events(f)]
    check(near(ev, 31) and not near(ev, 46, 1) and not near(ev, 76, 1),
          "camera's events: the readout's ticks, the gate's and the picture's, and not the clock's", f"{ev}")


def atflir_scene(n_frames=160, seed=12):
    """An ATFLIR display drawn at FLIR1's size: a black surround, the picture at 52-296 by 14-229 (a noisy sky), and
    white text at the fields' places -- the azimuth reading 4, 5, 6, 7 (stepping at frames 41, 81, 121), the
    elevation 5 and the zoom 10. Returns a clip of it."""
    rng = np.random.default_rng(seed)
    frames = {}
    for n in range(1, n_frames + 1):
        f = np.zeros((H, W))
        f[14:229, 52:296] = 45.0 + rng.normal(0, 3.0, (215, 244))
        az = 4 + (n - 1) // 40
        f[digits(f"0{az}", 165, 24)] = 190.0                 # under the field of view's and the camera's row
        f[digits("05", 70, 110)] = 190.0
        f[digits("10", 88, 24)] = 190.0
        frames[n] = f

    class Clip(Frames):
        info = {"stream": {"sample_aspect_ratio": "200:219"}}      # FLIR1's VCD pixels, a little taller than wide

        def frames(self):
            return range(self.n0, self.n1 + 1)

        def rgb(self, n):
            return np.repeat(self.grey(n)[:, :, None], 3, 2).astype(np.float32)
    return Clip(frames)


def test_atflir():
    """`symbology --method atflir` (2026-10-20): the picture's box, the fields at their places, the azimuth's changes
    timed, and with its looks read, the slew rate its ticks make (1 deg every 40 frames: 0.75 deg/s at 30)."""
    print("\nthe ATFLIR's fields of text")
    from mcdonald import atflir
    clip = atflir_scene()
    box = atflir.picture_box(clip)
    check(box is not None and all(abs(a - b) <= 2 for a, b in zip(box, (52, 14, 296, 229))),
          "the picture's box, inside the black surround", f"{box}")
    f = atflir.measure(clip)
    fl = f.fields["fields"]
    check({"az", "el", "zoom"} <= set(fl) and "fov" not in fl and "mode" not in fl,
          "the azimuth, elevation and zoom placed; the empty fields left out", f"{sorted(fl)}")
    if "az" in fl:
        ch = [c["frame"] for c in fl["az"]["changes"]]
        check(fl["az"]["looks"] == 4 and all(any(abs(c - t) <= 1 for c in ch) for t in (40.5, 80.5, 120.5)),
              "the azimuth's four looks and its three changes, to the frame", f"{fl['az']['looks']} looks, {ch}")
        check(fl["el"]["looks"] == 1 and fl["zoom"]["looks"] == 1, "the elevation and the zoom hold one look each")
        r = atflir.measure(clip, read=atflir.parse_read("az:A=4,B=5,C=6,D=7")).fields["fields"]["az"].get("rate")
        check(r is not None and abs(r["rate_per_s"] - 0.75) < 0.03 and r["ticks_used"] == 3,
              "read, its ticks give the slew: 0.75 deg/s", f"{r and round(r['rate_per_s'], 3)}")


def test_versions():
    """`mcdonald versions` (2026-10-20): two copies of one drawn clip -- the first lossless at 30000/1001, with three
    frames held in the recording itself; the second re-encoded poorly, relabelled to 30 a second, with a frame repeated
    near 60 and one dropped near 180. (A blocky encode, MPEG-4 at a coarse quantiser, adds edges of its own and shows as
    much fine detail as the lossless copy: the test's poor copy is an H.264, whose deblocking smooths, as FLIR1's
    official copies are.)"""
    print("\nseveral copies of one clip")
    from mcdonald import versions
    from scipy import ndimage
    rng = np.random.default_rng(4)
    w, h, n = 160, 120, 240
    tex = ndimage.gaussian_filter(rng.normal(0, 1, (h, w + n)), 1.2) * 60
    src = []
    for k in range(n):
        f = np.clip(100 + 15 * rng.normal() + tex[:, k:k + w], 0, 255).astype(np.uint8)
        src.append(src[-1] if 100 <= k <= 102 else f)
    copy = src[:61] + [src[60]] + src[61:179] + src[180:]          # frame 61 again; frame 180 gone
    with tempfile.TemporaryDirectory() as td:
        a, b = f"{td}/a.mkv", f"{td}/b.mp4"
        for path, frames, rate, codec in ((a, src, "30000/1001", ["-c:v", "ffv1"]),
                                          (b, copy, "30", ["-c:v", "libx264", "-crf", "38"])):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r", rate,
                            "-i", "-", *codec, "-pix_fmt", "yuv420p", path], input=np.stack(frames).tobytes(), check=True)
        f = versions.compare([a, b], ["first", "second"])
    c0, c1 = f.fields["copies"]
    check(c0["fps"] == "30000/1001" and c1["fps"] == "30" and any("relabelled" in x for x in f.notes),
          "the second copy's 30 for the same frames: relabelled, not resampled", f"{c0['fps']} {c1['fps']}")
    steps = c1["lag_steps"]
    check(len(steps) == 2 and steps[0]["by"] == 1 and abs(steps[0]["near"] - 61) <= 30 and steps[1]["by"] == -1
          and abs(steps[1]["near"] - 180) <= 30, "a frame repeated near 61 and one dropped near 180, from the lag's steps",
          f"{steps}")
    check(any(101 <= x <= 103 for x in f.fields["held_in_every_copy"]), "the frames held in both are the recording's",
          f"{f.fields['held_in_every_copy']}")
    check(f.fields["best"] == "first" and c1["detail_share"] < 0.9, "the lossless copy is the best source",
          f"second keeps {c1['detail_share']:.2f}")


def test_commands():
    print("\nthe commands")
    from mcdonald import cli
    check("camera" in cli.COMMANDS and "readout" in cli.COMMANDS, "camera and readout are commands")
    check("events" in cli.COMMANDS and "versions" in cli.COMMANDS, "events and versions are commands")
    from mcdonald import stages
    check("camera" in stages.STAGES and stages.STAGES.index("camera") == stages.STAGES.index("kinematics") + 1,
          "camera is a stage of run, after kinematics")


def main():
    test_frame_rate()
    test_frame_count()
    test_shape()
    test_zoom_found_and_placed()
    test_not_zooms()
    test_rate_steps()
    test_released()
    test_readout_ticks()
    test_held()
    test_overlay_events()
    test_atflir()
    test_versions()
    test_commands()
    if FAIL:
        print(f"\n{len(FAIL)} FAILED: {', '.join(FAIL)}")
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
