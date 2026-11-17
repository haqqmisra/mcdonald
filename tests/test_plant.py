"""Does `mcdonald plant` write what its truth table says, and write it the same way twice?

A drawn video (a textured scene that drifts under a still redaction block, with grain, through libx264) has objects
planted in it by the command's own function. Then:

- each object is where the truth table says after the encoder, to a stated tolerance, and its contrast and width
  survive to stated tolerances (read on the planted file less the control: the same frames with nothing planted);
- two runs with one seed give the same file, byte for byte, and another seed gives another;
- with nothing planted the tool changes nothing but the encoding: its file is the control's, byte for byte, and
  the control is the drawn video to within what an encoder does;
- nothing is written under the overlay; an object too bright for the picture clips, and the table says so;
- the scene's own motion is read as the frames go by, an object planted "with the scene" moves as it does, and
  every object's speed is given against the scene as well as on the screen;
- a planted file says what it is (its name, its container's comment, `clip.planted` in every envelope, the
  report's first lines) and is refused beside its video and in the storage and reference-data folders;
- the lights are what they are called (a beat at its frequency, a strobe's short pulses, a twinkle's spread);
- an object drawn is the same whatever is drawn after it, and the draws keep apart and take turns;
- the score against a truth table: a row on a planted path is that object, found; a row elsewhere is another;
- and end to end: Find lists the planted objects that move against the scene, on their paths; it does not list the
  one planted with the scene; and in the control it lists none of them.

    python3 tests/test_plant.py        # or: pytest tests/

No video data needed. It needs an ffmpeg with libx264 and says so where there is none.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import plant, planted  # noqa: E402

FAIL = []
W, H, N, FPS = 320, 240, 72, 30
BLOCK = (slice(20, 70), slice(200, 300))          # a redaction block: rows, columns
DRIFT = -2.0                                      # px a frame: how the drawn scene moves on the screen (x)


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def skip(label, why):
    print(f"  SKIP  {label}: {why}")


def drawn_video(path, seed=0):
    """The drawn video: a smooth texture drifting DRIFT px a frame (to the left) under a black block that stays put,
    grain of 1.2 grey levels, through libx264 with B frames at 700 kb/s."""
    rng = np.random.default_rng(seed)
    big = ndimage.gaussian_filter(rng.normal(0, 1, (H + 40, W + 4 * N + 40)), 6)
    fine = ndimage.gaussian_filter(rng.normal(0, 1, big.shape), 1.0)
    # 12 grey levels of broad texture and 4 of fine: well under the objects planted, and sharp enough that one bright
    # point is not the sharpest thing in the picture (it would pull the registration of the whole scene toward itself)
    big = 110 + 12 * big / big.std() + 4 * fine / fine.std()
    frames = []
    for n in range(N):
        g = ndimage.shift(big, (0, DRIFT * n), order=1, mode="nearest")[20:20 + H, 20 + 2 * N:20 + 2 * N + W]
        g = g + rng.normal(0, 1.2, (H, W))
        g[BLOCK] = 0
        frames.append(np.clip(g, 0, 255).astype(np.uint8))
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
                        "-framerate", str(FPS), "-i", "-", "-c:v", "libx264", "-threads", "1", "-pix_fmt", "yuv420p", "-g", "24",
                        "-bf", "2", "-b:v", "700k", str(path)], input=b"".join(f.tobytes() for f in frames), capture_output=True)
    assert r.returncode == 0, r.stderr.decode()
    return path


def luma(path):
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vf", "extractplanes=y", "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8)
    return a[:(len(a) // (W * H)) * W * H].reshape(-1, H, W).astype(np.float32)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def point(ident, x, y, vx=0.0, vy=0.0, contrast=60.0, sigma=1.5, dark=False, **more):
    return dict(id=ident, kind="dot", shape="point", sigma=sigma, contrast=contrast, dark=dark, light=dict(kind="constant"),
                path=dict(kind="line", x=x, y=y, vx=vx, vy=vy), **more)


PLANTS = [point(1, 60.0, 120.0, 1.5, 0.4, contrast=60.0, sigma=1.5),
          point(2, 150.3, 180.6, 1.0, -0.3, contrast=80.0, sigma=2.5),
          point(3, 90.0, 195.0, 0.5, -0.2, contrast=50.0, sigma=2.0, dark=True),       # 30 px or more from the others, always
          point(4, 170.0, 45.0, 0.9, 0.0, contrast=80.0, sigma=1.5),            # goes behind the block: hidden there
          point(5, 40.0, 40.0, 0.2, 0.3, contrast=400.0, sigma=2.0),            # too bright for the picture: clips
          dict(id=6, kind="scene", shape="point", sigma=2.0, contrast=60.0, dark=False, light=dict(kind="constant"),
               path=dict(kind="scene", x=280.0, y=110.0), first=5, last=65)]   # a feature of the scene: it moves as the scene does


# ---- the tests ---------------------------------------------------------------------------------------
def test_planted_as_the_truth_table_says(tmp, made):
    t = made["truth_data"]
    A, B = luma(made["planted"]), luma(made["none"])
    check(len(A) == N and len(B) == N and t["stretch"]["frames"] == N, "the planted video and the control have the stretch's frames",
          f"{len(A)}, {len(B)} of {N}")
    k = t["levels"]["codes_per_dn"]
    yy, xx = np.mgrid[-9:10, -9:10]
    by = {p["id"]: p for p in t["plants"]}
    worst = {}
    for i in (1, 2, 3):
        p = by[i]
        off, peak, wid = [], [], []
        for n, (x, y) in ((int(n), xy) for n, xy in p["track"].items()):
            xi, yi = int(round(x)), int(round(y))
            d = (A[n - 1] - B[n - 1])[yi - 9:yi + 10, xi - 9:xi + 10] * (-1.0 if p["dark"] else 1.0)
            q = np.clip(d, 0, None)
            q = np.where(q > 0.2 * q.max(), q, 0)
            cx, cy = (xx * q).sum() / q.sum() + xi, (yy * q).sum() / q.sum() + yi
            off.append(np.hypot(cx - x, cy - y))
            peak.append(d.max())
            wid.append(np.sqrt((((xx + xi - cx) ** 2 + (yy + yi - cy) ** 2) * q).sum() / q.sum() / 2))
        worst[i] = (float(np.median(off)), float(np.max(off)), float(np.median(peak)) / (p["contrast"] * k), float(np.median(wid)) / p["sigma"])
    said = "; ".join(f"object {i}: {v[0]:.2f} px (most {v[1]:.2f}), contrast x{v[2]:.2f}, width x{v[3]:.2f}" for i, v in worst.items())
    # the most on any one frame is the encoder's: an object's centroid on a frame of quantised blocks moves by about a pixel
    # (1.00 px on arthur's libx264, 1.03 on the macOS runner's, 2026-11-14), so 1.5 px holds across encoder builds; the
    # median, which is what a measurement reads, stays held to a quarter of a pixel
    check(all(v[0] <= 0.25 and v[1] <= 1.5 for v in worst.values()),
          "after the encoder each object is where the truth table has it: within 0.25 px at the median, 1.5 px at the most", said)
    check(all(0.75 <= v[2] <= 1.15 for v in worst.values()),
          "its contrast survives the encoder: 0.75 to 1.15 of what was asked, at the median", said)
    check(all(0.75 <= v[3] <= 1.25 for v in worst.values()),
          "and its width: 0.75 to 1.25 of the sigma asked (the half-peak core's second moment)", said)
    check(all(0.75 <= by[i]["contrast_after"] / by[i]["contrast_written"] <= 1.15 for i in (1, 2, 3))
          and all(abs(by[i]["contrast_after"] - worst[i][2] * by[i]["contrast"]) <= 0.12 * by[i]["contrast"] for i in (1, 2, 3)),
          "the table also gives each object's contrast after the encoder (the planted video less the control): here 0.75 to "
          "1.15 of what was written, and the same as this test reads",
          str([(by[i]["contrast_written"], by[i]["contrast_after"]) for i in (1, 2, 3)]))
    check(all(0.9 <= by[i]["contrast_written"] / by[i]["contrast"] <= 1.0 for i in (1, 2, 3)),
          "the table's contrast as written (the most a pixel was changed by) is 0.9 to 1 of the contrast asked where nothing cut it",
          str([(by[i]["contrast"], by[i]["contrast_written"]) for i in (1, 2, 3)]))


def test_under_the_overlay_and_past_the_ceiling(tmp, made):
    t = made["truth_data"]
    by = {p["id"]: p for p in t["plants"]}
    rows = [json.loads(json.dumps(r)) for r in csv_rows(made["table"])]
    mine = [r for r in rows if r["id"] == "4"]
    hidden = [r for r in mine if float(r["hidden"]) > 0.99]
    A, B = luma(made["planted"]), luma(made["none"])
    block = np.zeros((H, W), bool)
    block[BLOCK] = True
    inside = ndimage.binary_erosion(block, iterations=6)
    changed = float(np.abs(A - B)[:, inside].max())
    seen = [r for r in mine if float(r["hidden"]) < 0.01]
    check(t["overlay"]["share"] > 0.05 and len(hidden) >= 20 and len(seen) >= 15 and by[4]["frames_hidden"] >= 20,
          "an object that goes behind the redaction block is hidden there and seen before it, and the table says on which frames",
          f"overlay {t['overlay']['share']:.2f} of the frame, {len(seen)} frames in the open, {len(hidden)} wholly hidden")
    check(changed <= 3.0, "and nothing is written into the block", f"the most a pixel inside it differs from the control: {changed:.0f} codes")
    lv = t["levels"]
    top = [float(A[int(n) - 1][int(round(xy[1])), int(round(xy[0]))]) for n, xy in by[5]["track"].items()]
    check(by[5]["frames_clipped"] >= 0.9 * by[5]["frames_on"] and by[5]["contrast_written"] < 0.6 * by[5]["contrast"]
          and abs(float(np.median(top)) - lv["ceiling"]) <= 6,
          "an object brighter than the picture can hold is cut at the picture's ceiling: a flat top there after the encoder, "
          "and the table says so",
          f"asked {by[5]['contrast']:g} DN, written {by[5]['contrast_written']:g}; ceiling {lv['ceiling']}, its middle in the planted "
          f"video {np.median(top):.0f} at the median (the encoder rings to {A.max():.0f} beside it)")
    check(lv["codes_per_dn"] < 1 and lv["floor"] <= 16 and lv["ceiling"] >= 235,
          "the levels are the stretch's own: a studio-range picture, a contrast in grey levels divided into codes", str(lv))


def csv_rows(path):
    import csv
    return list(csv.DictReader(ln for ln in open(path, encoding="utf-8") if not ln.startswith("#")))


def test_the_scene_and_what_moves_with_it(tmp, made):
    t = made["truth_data"]
    by = {p["id"]: p for p in t["plants"]}
    sc = t["scene"]
    check(abs(sc["speed_px_per_frame"] - abs(DRIFT)) <= 0.15 and sc["held_still"] < 0.1,
          "the scene's own motion is read as the frames go by: the drawn drift, to 0.15 px a frame",
          f"{sc['speed_px_per_frame']} px a frame for {abs(DRIFT)} drawn")
    tr = {int(n): xy for n, xy in by[6]["track"].items()}
    a, b = min(tr), max(tr)
    moved = (tr[b][0] - tr[a][0], tr[b][1] - tr[a][1])
    steps = np.diff([tr[n][0] for n in sorted(tr)])
    check(abs(moved[0] - DRIFT * (b - a)) <= 1.0 and abs(moved[1]) <= 1.0 and by[6]["speed_against_scene"] <= 0.1
          and float(np.std(steps)) <= 0.1,
          "an object planted with the scene moves as the scene does: within 1 px of the drawn drift over its life, its "
          "steps scattered under 0.1 px, and still against it",
          f"moved {moved[0]:.2f}, {moved[1]:.2f} px in {b - a} frames for {DRIFT * (b - a):.0f}, 0; steps scattered {np.std(steps):.3f} px; "
          f"{by[6]['speed_against_scene']} px a frame against the scene")
    want = {1: np.hypot(1.5 - DRIFT, 0.4), 2: np.hypot(1.0 - DRIFT, 0.3), 3: np.hypot(0.5 - DRIFT, 0.2)}
    check(all(abs(by[i]["speed_against_scene"] - v) <= 0.2 for i, v in want.items()) and abs(by[1]["speed_px_per_frame"] - np.hypot(1.5, 0.4)) < 0.01,
          "every object's speed is given on the screen and against the scene",
          "; ".join(f"object {i}: {by[i]['speed_px_per_frame']} on the screen, {by[i]['speed_against_scene']} against the scene ({v:.2f} drawn)" for i, v in want.items()))


def test_a_faint_object_at_a_low_bit_rate_is_mostly_the_encoders(tmp):
    """The same faint point through the drawn video's own 700 kb/s and through a tenth of it: the table's contrast after
    the encoder says what is left, which the contrast written cannot."""
    faint = [point(1, 70.0, 150.0, 1.0, 0.2, contrast=20.0, sigma=1.5)]
    low = tmp / "low.mp4"
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(tmp / "drawn.mp4"), "-c:v", "libx264", "-threads", "1",
                        "-pix_fmt", "yuv420p", "-g", "24", "-bf", "2", "-b:v", "60k", str(low)], capture_output=True)
    assert r.returncode == 0, r.stderr.decode()
    a = plant.make(tmp / "drawn.mp4", 1, N, faint, tmp / "faint", "drawn", seed=1, look=False)["truth_data"]["plants"][0]
    b = plant.make(low, 1, N, faint, tmp / "faint-low", "low", seed=1, look=False)["truth_data"]["plants"][0]
    check(abs(a["contrast_written"] - b["contrast_written"]) <= 1.5 and a["contrast_after"] >= 0.6 * a["contrast_written"]
          and b["contrast_after"] <= 0.6 * a["contrast_after"],
          "a 20-level point written the same into both: most of it is left at the video's bit rate, under 0.6 of that at a tenth of it",
          f"written {a['contrast_written']} and {b['contrast_written']} DN; after the encoder {a['contrast_after']} and {b['contrast_after']}")


def test_one_seed_one_file(tmp, made):
    again = plant.make(tmp / "drawn.mp4", 1, N, PLANTS, tmp / "again", "drawn", seed=1, look=False)
    check(sha(again["planted"]) == sha(made["planted"]) and sha(again["none"]) == sha(made["none"]),
          "two runs with one seed give the same planted video and the same control, byte for byte")
    check(Path(again["truth"]).read_text() == Path(made["truth"]).read_text(), "and the same truth table")
    build = made["truth_data"]["settings"].get("encoder_build") or ""
    check(build.startswith("x264 - core "), "the truth table names the encoder build that wrote the file (one seed, one file holds "
          "for one build: two builds of libx264 write different files)", build)
    a = plant.make(tmp / "drawn.mp4", 1, N, None, tmp / "s1", "drawn", seed=1, drawn=dict(k=4, life=30, at_once=2), look=False)
    b = plant.make(tmp / "drawn.mp4", 1, N, None, tmp / "s1b", "drawn", seed=1, drawn=dict(k=4, life=30, at_once=2), look=False)
    c = plant.make(tmp / "drawn.mp4", 1, N, None, tmp / "s2", "drawn", seed=2, drawn=dict(k=4, life=30, at_once=2), look=False)
    check(sha(a["planted"]) == sha(b["planted"]) and sha(a["planted"]) != sha(c["planted"]),
          "a draw with one seed is one video; another seed is another")
    check(len(a["truth_data"]["plants"]) == 4 and Path(a["planted"]).name == "drawn_planted_1_72_s1.mp4",
          "the draw plants what was asked, in a file named for what it is", Path(a["planted"]).name)


def test_nothing_planted_changes_nothing_but_the_encoding(tmp, made):
    zero = plant.make(tmp / "drawn.mp4", 1, N, [], tmp / "zero", "drawn", seed=1, look=False)
    check(sha(zero["planted"]) == sha(zero["none"]) == sha(made["none"]),
          "with nothing planted the tool's video is the control, byte for byte")
    src, ctl = luma(tmp / "drawn.mp4"), luma(zero["none"])
    err = np.abs(src - ctl)
    mse = float(((src - ctl) ** 2).mean())
    psnr = 10 * np.log10(255.0 ** 2 / max(mse, 1e-9))
    check(psnr >= 38.0 and float(err.mean()) <= 2.0, "and the control is the drawn video to within what an encoder does",
          f"PSNR {psnr:.1f} dB, a pixel differs by {err.mean():.2f} codes on average")
    st = zero["truth_data"]["settings"]
    check(st["types_made"][0] == "I" and all(st["types_made"][i] == "I" for i in st["i_frames"]) and st["bframes"] == 2
          and 0.6 <= st["bit_rate_made"] / st["bit_rate"] <= 1.4,
          "encoded as the video is: an I frame wherever the video has one, its B frames, near its bit rate over the stretch",
          f"I at {st['i_frames']}, {st['bframes']} B frames, {st['bit_rate_made'] / 1e3:.0f} kb/s for {st['bit_rate'] / 1e3:.0f}; "
          f"{100 * st['types_same']:.0f} % of picture types the same")


def test_a_planted_file_says_what_it_is(tmp, made):
    from mcdonald import forensics as vf
    from mcdonald.clip import probe
    from mcdonald.report import clip_block
    art = plant.test_article(probe(made["planted"]))
    none = plant.test_article(probe(made["none"]))
    check(art is not None and art["planted"] == len(PLANTS) and art["comment"].startswith("mcdonald plant: a test video, not footage"),
          "the planted file's container says what it is and how many objects are in it", str(art))
    check(none is not None and none["planted"] == 0 and plant.test_article(probe(tmp / "drawn.mp4")) is None,
          "the control says it holds none; any other video says nothing")
    block = clip_block(vf.Clip(made["planted"], tmp / "frames", 1, 4, extract=False))
    plain = clip_block(vf.Clip(tmp / "drawn.mp4", tmp / "frames0", 1, 4, extract=False))
    check(block.get("planted", {}).get("planted") == len(PLANTS) and "planted" not in plain,
          "every envelope and every case made from it carries clip.planted; a video that is not one has no such field")
    from mcdonald.report import Case
    case = Case("drawn_planted", made["planted"], vf.Clip(made["planted"], tmp / "frames", 1, 4, extract=False))
    md = case.markdown()
    check("This is a test video, not footage" in md.split("## Conclusion")[0],
          "a report made from it says so above its conclusion", md.split("## Conclusion")[0][-260:].replace("\n", " "))
    check("test video" not in Case("drawn", tmp / "drawn.mp4", vf.Clip(tmp / "drawn.mp4", tmp / "frames0", 1, 4, extract=False)).markdown(),
          "and any other report does not")


def test_never_where_it_could_pass_for_footage(tmp, made):
    from mcdonald import storage
    old = {k: os.environ.get(k) for k in ("MCDONALD_DATA", "MCDONALD_HOME")}
    os.environ["MCDONALD_DATA"], os.environ["MCDONALD_HOME"] = str(tmp / "data"), str(tmp / "home")
    try:
        why = [plant.refused(tmp, tmp / "drawn.mp4"), plant.refused(storage.videos(), tmp / "drawn.mp4"),
               plant.refused(tmp / "data" / "pursue", tmp / "drawn.mp4"), plant.refused(tmp / "elsewhere", tmp / "drawn.mp4")]
        check(all(why[:3]) and why[3] is None,
              "a planted video is refused beside its video, in the storage folder's videos and in the reference-data folder", str(why))
        try:
            plant.make(tmp / "drawn.mp4", 1, N, [], tmp, "drawn")
            ok = False
        except SystemExit as e:
            ok = "test article" in str(e)
        check(ok, "and the command stops with the reason")
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_the_lights():
    rng = np.random.default_rng(3)
    n, fps = 600, 30.0
    spec = lambda m: np.abs(np.fft.rfft((m - m.mean()) * np.hanning(len(m))))
    fr = np.fft.rfftfreq(n, 1 / fps)
    b = plant.light(dict(kind="beat", hz=6.2, depth=0.3), n, fps, rng)
    check(abs(fr[np.argmax(spec(b))] - 6.2) <= 0.1 and abs(b.mean() - 1) < 0.01 and abs((b.max() - b.min()) / 2 - 0.3) < 0.01,
          "a beat is at its frequency and its depth, about a mean of 1", f"{fr[np.argmax(spec(b))]:.2f} Hz, depth {(b.max() - b.min()) / 2:.3f}")
    w = plant.light(dict(kind="wander", hz=6.2, depth=0.3, hz_sd=0.5), n, fps, rng)
    sb, sw = spec(b), spec(w)
    check(abs(fr[np.argmax(sw)] - 6.2) <= 1.0 and sw.max() < 0.8 * sb.max(),
          "a wandering beat is near its frequency and spread over more of the spectrum than a steady one",
          f"peak at {fr[np.argmax(sw)]:.2f} Hz, {sw.max() / sb.max():.2f} of the steady beat's height")
    tw = plant.light(dict(kind="twinkle", index=0.3, corner_hz=3.0), 6000, fps, rng)
    check(abs(tw.mean() - 1) < 0.05 and 0.15 <= tw.std() / tw.mean() <= 0.33 and tw.min() > 0,
          "a twinkle's brightness is always positive, about 1, and spread by about its index (less the frames' own averaging)",
          f"mean {tw.mean():.3f}, sd over mean {tw.std() / tw.mean():.3f}")
    s = plant.light(dict(kind="strobe", hz=1.5, duty=0.05, depth=4.0, phase=0.0), n, fps, rng)
    on = s > 1.5
    near = min(fr[1:][np.argmax(spec(s)[1:])] % 1.5, 1.5 - fr[1:][np.argmax(spec(s)[1:])] % 1.5)
    check(0.02 <= on.mean() <= 0.12 and near < 0.11 and s.min() >= 1.0 and 2.0 < s.max() <= 5.0,
          "a strobe is short pulses at its rate over a steady light, never over the steady light plus its depth",
          f"on {100 * on.mean():.0f} % of frames, most {s.max():.2f}, strongest line {fr[1:][np.argmax(spec(s)[1:])]:.2f} Hz")
    check(np.all(plant.light(dict(kind="constant"), 50, fps, rng) == 1.0), "a constant light is constant")


def test_a_draw_is_the_same_whatever_follows(tmp):
    a, _ = plant.draw(4, 640, 480, 300, 30.0, seed=7, kinds=("dot", "bird"), life=60, at_once=2)
    b, _ = plant.draw(8, 640, 480, 300, 30.0, seed=7, kinds=("dot", "bird"), life=60, at_once=2)
    check(json.dumps(a, default=plant._plain) == json.dumps(b[:4], default=plant._plain),
          "the first four objects of a draw of eight are the draw of four: an object does not depend on what follows it")
    real = [(p, plant.realise(p, 300, 30.0, 640, 480, 7)) for p in b]
    alive = np.zeros(301, int)
    close = np.inf
    for i, (p, r) in enumerate(real):
        alive[p["first"]:p["last"] + 1] += 1
        for q, s in real[i + 1:]:
            lo, hi = max(p["first"], q["first"]), min(p["last"], q["last"])
            if lo <= hi:
                d = np.hypot(r["x"][lo - p["first"]:hi - p["first"] + 1] - s["x"][lo - q["first"]:hi - q["first"] + 1],
                             r["y"][lo - p["first"]:hi - p["first"] + 1] - s["y"][lo - q["first"]:hi - q["first"] + 1])
                close = min(close, float(d.min()))
    check(alive.max() <= 2 and close >= plant.APART, "at most two in the frame at once, as asked, and never nearer than the least distance",
          f"most at once {alive.max()}, nearest {close:.0f} px")
    g, _ = plant.draw(2, 640, 480, 120, 30.0, seed=3, kinds=("flock", "formation"), life=100, at_once=2)
    flock = [p for p in g if p.get("grouped") == "flock"]
    form = [p for p in g if p.get("grouped") == "formation"]
    hz = [p["light"]["hz"] for p in flock]
    rf = [plant.realise(p, 120, 30.0, 640, 480, 3) for p in form]
    sep = np.hypot(rf[0]["x"] - rf[1]["x"], rf[0]["y"] - rf[1]["y"])
    rk = [plant.realise(p, 120, 30.0, 640, 480, 3) for p in flock]
    sepk = np.hypot(rk[0]["x"] - rk[1]["x"], rk[0]["y"] - rk[1]["y"])
    check(len(flock) >= 3 and len(form) >= 3 and len(set(hz)) == len(hz) and np.ptp(sep) < 1e-6 and np.ptp(sepk) > 0.5,
          "a flock is three or more birds, each with its own beat, that change their places; a formation keeps its places",
          f"{len(flock)} and {len(form)} members; a formation pair's separation moves {np.ptp(sep):.2g} px, a flock pair's {np.ptp(sepk):.1f}")
    sc, _ = plant.draw(4, 640, 480, 200, 30.0, seed=5, kinds=("twinkle", "scene", "dot", "still"), life=80, at_once=2)
    check([p["path"]["kind"] for p in sc] == ["scene", "scene", "line", "still"] and sc[0]["light"]["kind"] == "twinkle",
          "objects that go with the scene are drawn by where they start (their paths are made as the frames are read)",
          str([(p["kind"], p["path"]["kind"]) for p in sc]))
    try:
        plant.draw(9, 640, 480, 100, 30.0, life=60, at_once=2)
        fits = True
    except ValueError as e:
        fits = "do not fit" not in str(e)
    check(not fits, "more objects than the stretch has room for is refused, with how many would fit")


def test_the_score_against_the_truth(tmp, made):
    t = made["truth_data"]
    by = {p["id"]: p for p in t["plants"]}
    on2 = {n: [xy[0] + 3.0, xy[1] - 2.0] for n, xy in list(by[2]["track"].items())[5:40]}
    off = {str(n): [20.0 + n, 220.0] for n in range(10, 40)}
    props = [dict(track=off, dark=False, size_px=5.0, score=9.0, strength="fair", frames=[10, 39]),
             dict(track=on2, dark=False, size_px=6.0, score=4.0, strength="fair", frames=[6, 40], points=1)]
    res = plant.recovered(t, props)
    r2 = next(r for r in res["plants"] if r["id"] == 2)
    check(res["found"] == 1 and r2["found"] and r2["rank"] == 2 and r2["rank_alone"] == 2 and abs(r2["px"] - 3.6) < 0.2 and r2["polarity"] is True,
          "a row on a planted path is that object, found at its place on the list", str({k: r2[k] for k in ("rank", "px", "shared")}))
    check(len(res["others"]) == 1 and res["others"][0]["rank"] == 1 and sum(r["found"] for r in res["plants"]) == 1,
          "a row on no planted path is another row, and the objects with no row are not found")
    two = plant.recovered(t, [dict(track=by[1]["track"], dark=False, size_px=5.0, score=9.0, strength="fair"), props[0],
                              dict(track=by[2]["track"], dark=False, size_px=5.0, score=3.0, strength="weak")])
    got = {r["id"]: r for r in two["plants"]}
    check(got[2]["rank"] == 3 and got[2]["rank_alone"] == 2 and got[1]["rank_alone"] == 1,
          "an object's place with the other planted objects' rows set aside: third on the list, second among what is not planted")
    lo, hi = plant.wilson(0, 20)
    lo2, hi2 = plant.wilson(18, 20)
    check(lo == 0.0 and 0.15 < hi < 0.17 and 0.69 < lo2 < 0.70 and 0.97 < hi2 < 0.98 and plant.wilson(0, 0) == (None, None),
          "the interval on a share is Wilson's: 0 of 20 is under 16 %, 18 of 20 is 70 to 97 %", f"{hi:.3f}; {lo2:.3f}-{hi2:.3f}")
    tab = plant.tabulate(res["plants"], by=("dark",))
    check([(c["dark"], c["n"], c["found"]) for c in tab] == [(False, 5, 1), (True, 1, 0)], "and the cells count what was planted and found", str(tab))


def test_the_command(tmp, made):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent.parent / "src"))
    r = subprocess.run([sys.executable, "-m", "mcdonald.cli", "plant", str(tmp / "drawn.mp4"), "--n0", "1", "--n1", str(N), "--draw", "3",
                        "--life", "30", "--at-once", "2", "--contrast", "60", "--seed", "5", "--out", str(tmp / "cli"), "--json"],
                       capture_output=True, encoding="utf-8", env=env)
    try:
        d = json.loads(r.stdout)
    except ValueError:
        d = {}
    res = d.get("results") or {}
    check(r.returncode == 0 and d.get("command") == "plant" and len(res.get("plants") or []) == 3 and len(d.get("files") or []) == 5
          and all(Path(f).exists() for f in d["files"]) and any(f.endswith("_truth.png") for f in d["files"]),
          "`mcdonald plant --draw 3 --json`: the envelope, three objects, the five files it wrote", (r.stderr or "")[-300:])
    check(all("track" not in p for p in res.get("plants") or [{}]) and any("test video, not footage" in s for s in res.get("said") or []),
          "the envelope has each object's fields (the frame-by-frame table is in the truth file) and says it is a test video")
    props = tmp / "props.json"
    t = made["truth_data"]
    by = {p["id"]: p for p in t["plants"]}
    props.write_text(json.dumps(dict(results=dict(proposals=[dict(track=by[1]["track"], dark=False, size_px=5.0, score=12.0, strength="strong")]))))
    r = subprocess.run([sys.executable, "-m", "mcdonald.cli", "plant", "--score", made["truth"], "--proposals", str(props), "--json"],
                       capture_output=True, encoding="utf-8", env=env)
    try:
        s = json.loads(r.stdout).get("results") or {}
    except ValueError:
        s = {}
    check(r.returncode == 0 and s.get("found") == 1 and s.get("planted") == len(PLANTS),
          "`mcdonald plant --score TRUTH --proposals JSON`: Find's list held against the table", (r.stderr or "")[-300:])
    r = subprocess.run([sys.executable, "-m", "mcdonald.cli", "plant", str(tmp / "drawn.mp4"), "--json"], capture_output=True, encoding="utf-8", env=env)
    check(r.returncode == 2 and "say what to plant" in (r.stderr or ""), "with nothing to plant named, it says what to give and exits 2",
          (r.stderr or "")[-200:])


def test_find_lists_a_planted_object_and_not_in_the_control(tmp, made):
    from mcdonald import forensics as vf
    from mcdonald import propose
    t = made["truth_data"]
    rows = {}
    for name in ("planted", "none"):
        clip = vf.Clip(made[name], tmp / f"find-{name}", 1, N)
        props = propose.find(clip, vf.static_masks(clip), procs=2, keep=60)
        rows[name] = [p.to_dict() for p in props]
    res, ctl = plant.recovered(t, rows["planted"]), plant.recovered(t, rows["none"])
    got = {r["id"]: r for r in res["plants"]}
    check(got[1]["found"] and got[2]["found"] and got[3]["found"] and max(got[i]["rank"] for i in (1, 2, 3)) <= 6,
          "Find lists the planted objects that move against the scene on their paths, among its first rows",
          "; ".join(f"object {i}: " + (f"row {got[i]['rank']} ({got[i]['strength']}), {got[i]['px']} px" if got[i]["found"] else "not found") for i in (1, 2, 3)))
    check(not got[6]["found"], "and not the one planted with the scene: it does not move against the background",
          f"object 6: {'row ' + str(got[6]['rank']) if got[6]['found'] else 'not on the list'}")
    check(ctl["found"] == 0, "in the control, where they were not planted, none of their paths is on the list",
          f"{ctl['found']} of {ctl['planted']} 'found' in the control's {ctl['rows']} rows")


def test_many_frames_read_back(tmp):
    """The frames the encoder's contrast and the picture of the objects are read from: 300 asked of a 300-frame video
    come back, each the frame asked for. One `select` for all of them came back empty past about 100 (2026-11-16)."""
    v = tmp / "long.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=64x48:rate=30:duration=10",
                    "-c:v", "libx264", "-threads", "1", "-pix_fmt", "yuv420p", str(v)], check=True)
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(v), "-vf", "extractplanes=y", "-f", "rawvideo",
                        "-pix_fmt", "gray", "-"], capture_output=True, check=True)
    every = np.frombuffer(r.stdout, np.uint8).reshape(-1, 48, 64)
    got = plant._luma_frames(v, range(1, 301), 64, 48)
    check(len(every) == 300 and sorted(got) == list(range(1, 301)) and all(np.array_equal(got[n], every[n - 1]) for n in got),
          "300 frames asked of a 300-frame video come back, each the frame asked for", f"{len(got)} of 300")
    some = plant._luma_frames(v, [7, 150, 299, 7], 64, 48)
    check(sorted(some) == [7, 150, 299] and all(np.array_equal(some[n], every[n - 1]) for n in some), "and a few, once each")


def _row(rank, track, seen=None, round_=0.9, score=5.0):
    """One of Find's rows as a batch's window keeps it (`Proposal.to_dict`, with its rank)."""
    return dict(rank=rank, strength="strong" if score >= 10 else "fair" if score >= 4 else "weak", score=score,
                seen_in=seen or len(track), background_all_round=round_, scrolling_tape=False, dark=False, size_px=6.0,
                says="drawn", against_background_px_per_frame=1.0, track={str(n): list(xy) for n, xy in track.items()},
                mark_at={str(n): list(xy) for n, xy in list(track.items())[::20]}, frames=[min(track), max(track)])


def test_what_the_batch_takes():
    """`recovered_batch` on a batch's unit made here: a window of six rows, five planted paths."""
    line = lambda x0, y0, a=1, b=100: {n: (x0 + 1.0 * (n - a), y0) for n in range(a, b + 1)}
    paths = {i: line(*xy) for i, xy in {1: (100, 100), 2: (100, 200), 3: (100, 300, 20), 4: (400, 100), 5: (400, 300)}.items()}
    truth = dict(plants=[dict(id=i, kind="dot", contrast=60.0, track={str(n): list(xy) for n, xy in t.items()}, frames_on=len(t))
                         for i, t in paths.items()])
    off = {n: (x + 10.0, y) for n, (x, y) in paths[5].items()}
    rows = [_row(1, {n: xy for n, xy in paths[1].items() if n <= 60}, score=12.0),          # object 1: found, followed
            _row(2, {n: xy for n, xy in paths[5].items() if n <= 60}, score=11.0),          # object 5: found; its link 10 px off
            _row(3, line(700, 500, 1, 60)),                                                  # on no planted path: another object
            _row(4, {n: xy for n, xy in paths[2].items() if n <= 30}),                       # object 2: seen on 30 frames
            _row(5, {n: (80.0 + n, 300.0) for n in range(10, 60)})]                         # object 3 (from frame 20), and
    # from 10 frames before it began: three planted rows above it
    unit = dict(keep=400, windows=[dict(name="w00", n0=1, n1=100, rows=rows)],
                objects=[dict(object=1, windows=["w00:1"]), dict(object=2, windows=["w00:2"]), dict(object=3, windows=["w00:3"]),
                         dict(object=None, windows=["w00:5"])],
                followed={1: dict(paths[1]), 2: off, 3: line(700, 500, 1, 60)})
    on = plant.on_rows(truth, unit)
    check(on == {("w00", 1): [1], ("w00", 2): [5], ("w00", 4): [2], ("w00", 5): [3]}, "which of Find's rows are planted objects", str(on))
    res = plant.recovered_batch(truth, unit, keep=30, on=on)
    got = {r["id"]: r for r in res["plants"]}
    check(got[1]["object"] and got[1]["followed"] and got[1]["measured"] == 1 and got[1]["covered"] == 1.0 and got[1]["rank"] == 1,
          "a planted object whose row lasts and whose link stays on it is an object of the batch, and followed", str(got[1]))
    check(got[5]["object"] and not got[5]["followed"] and got[5]["covered"] == 0.0,
          "one whose link lies 10 px off it is an object, and not followed", str({k: got[5][k] for k in ("object", "covered", "followed")}))
    check(got[2]["listed"] and not got[2]["object"] and got[2]["why"] == "brief" and got[2]["seen"] == 30,
          "one whose row lasts 30 frames is listed, and no object: the rule's 40 frames", str({k: got[2][k] for k in ("why", "seen")}))
    check(got[3]["object"] and got[3]["rank"] == 2 and got[3]["measured"] is None and not got[3]["followed"],
          "a row fifth on the list with three planted rows above it stands second alone; its object, past the run's cap, is not followed",
          str({k: got[3][k] for k in ("rank", "measured", "followed")}))
    check(not got[4]["listed"] and not got[4]["object"] and got[4]["why"] == "not listed" and got[4]["rank"] is None,
          "one with no row is not listed")
    check(len(res["others"]) == 1 and res["others"][0]["first"] == 1 and res["others"][0]["last"] == 60,
          "the row on no planted path is the one other object the rule makes", str([(o["first"], o["last"]) for o in res["others"]]))
    from mcdonald import batch
    check(plant.recovered_batch(truth, unit, on=on)["keep"] == batch.KEEP,
          "asked at no setting, the rule is the batch's own: its 30 rows a window, not the 400 the planted run kept")
    at = lambda **kw: {r["id"]: r for r in plant.recovered_batch(truth, unit, on=on, **kw)["plants"]}
    check(at(keep=2)[3]["kept"] and at(keep=1)[3]["why"] == "past the rows kept" and not at(keep=1)[3]["object"],
          "with a window keeping two rows it is kept, with one it is past them")
    check(at(seen=20)[2]["object"] and at(seen=20)[2]["why"] is None and not at(seen=20)[2]["followed"],
          "asked at 20 frames the rule takes the 30-frame row; the run made no object of it, so it has no link")
    check(at(round_=0.95)[1]["why"] == "edge", "asked with more background round it than the row has, the rule calls it an edge")
    tab = plant.tables(res["plants"])
    k = {c["cell"]: c for c in tab["kind"]}["dot"]
    check(k["n"] == 5 and k["listed"]["k"] == 4 and k["object"]["k"] == 3 and k["followed"]["k"] == 1
          and tab["why"] == [dict(cell="brief", n=1), dict(cell="not listed", n=1)],
          "the table counts each level over what was planted, and why the rest were not taken", str(k))
    check(plant.cell(14.9, plant.CELLS["contrast_written"]) == "0-15" and plant.cell(160, plant.CELLS["contrast_written"]) == "over 120"
          and plant.cell(None, plant.CELLS["frames"]) is None, "the cells' edges: a cell is [low, high), the last open")
    check(plant.control_name(dict(files=dict(none=None)), "pr113_planted_301_1300_s7.mp4") == "pr113_planted_301_1300_none.mp4"
          and plant.control_name(dict(files=dict(none="x_none.mp4")), "y_s1.mp4") == "x_none.mp4",
          "a planted file's control: the truth table's, or the one another seed of the stretch wrote")


def _env(tmp):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent.parent / "src"), MCDONALD_HOME=str(tmp / "home"), MCDONALD_GPU="none")
    for k in ("MCDONALD_CATALOG", "MCDONALD_CASES", "MCDONALD_DATA", "MCDONALD_CPUS", "SLURM_JOB_ID", "SLURM_ARRAY_JOB_ID"):
        env.pop(k, None)
    return env


def test_through_the_batch(tmp, made):
    """The drawn planted video and its control through `mcdonald batch` as the plants at scale go (`--only track,report`,
    `--keep`; the control `--most 0`), then `mcdonald plant --table`."""
    run = lambda *a: subprocess.run([sys.executable, "-m", "mcdonald.cli", *map(str, a)], capture_output=True, encoding="utf-8",
                                    errors="replace", env=_env(tmp))
    r1 = run("batch", made["planted"], "--out", tmp / "bp", "--only", "track,report", "--keep", "60", "--most", "10")
    r2 = run("batch", made["none"], tmp / "drawn.mp4", "--out", tmp / "bc", "--most", "0", "--keep", "60")
    check(r1.returncode == 0 and r2.returncode == 0, "the planted video and its control go through `mcdonald batch`",
          (r1.stderr or "")[-300:] + (r2.stderr or "")[-300:])
    r = run("plant", "--table", tmp / "bp", "--control", tmp / "bc", "--json")
    try:
        d = json.loads(r.stdout)
    except ValueError:
        d = {}
    res = d.get("results") or {}
    check(r.returncode == 0 and len(d.get("files") or []) == 3 and all(Path(f).exists() for f in d.get("files") or ["-"]),
          "`mcdonald plant --table BATCH --control BATCH`: the table, as .md, .tsv and .json", (r.stderr or "")[-300:])
    rows = {}
    for f in d.get("files") or []:
        if f.endswith(".tsv"):
            import csv
            rows = {int(x["id"]): x for x in csv.DictReader(open(f, encoding="utf-8"), delimiter="\t")}
    moving = [rows.get(i, {}) for i in (1, 2, 3)]
    check(len(rows) == len(PLANTS) and all(x.get("object") == "True" and x.get("followed") == "True" for x in moving),
          "the three planted objects that move against the scene are objects of the batch, and followed",
          "; ".join(f"{i}: {x.get('object')}/{x.get('followed')} ({x.get('why')}, seen {x.get('seen')})" for i, x in zip((1, 2, 3), moving)))
    check(rows.get(6, {}).get("object") == "False", "the one planted with the scene is not", str({k: rows.get(6, {}).get(k) for k in ("listed", "why")}))
    u = (res.get("units") or [{}])[0]
    check(u.get("control") == Path(made["none"]).name and u.get("chance_object") == 0 and u.get("planted") == len(PLANTS),
          "its control is found by name, and no planted path is an object there", str({k: u.get(k) for k in ("control", "chance_listed", "chance_object", "control_objects")}))
    check(u.get("original_objects") == 0 and u.get("original_in_control") == 0 and u.get("control_in_original") == 0,
          "and the stretch of the video itself, run beside the controls (here the whole drawn video), is found by its frames: "
          "nothing in it lasts, as in the control", str({k: u.get(k) for k in ("original_objects", "original_in_control", "control_in_original")}))
    md = Path(next((f for f in d.get("files") or [] if f.endswith(".md")), tmp / "none.md"))
    check(md.exists() and "## drawn" in md.read_text() and "Where nothing was planted" in md.read_text(),
          "the table has a section for the video, with what the control gave")


def main():
    if not planted.has_x264():
        skip("every check", "this ffmpeg has no libx264 encoder, which the planted video is encoded with")
        print("\nall passed (skipped)")
        return 0
    with tempfile.TemporaryDirectory(prefix="mcdonald-test-plant-") as td:
        tmp = Path(td)
        drawn_video(tmp / "drawn.mp4")
        made = plant.make(tmp / "drawn.mp4", 1, N, PLANTS, tmp / "made", "drawn", seed=1)
        check(bool(made["sheets"]) and all(Path(f).exists() for f in made["sheets"]), "the picture of the planted objects is written")
        for name, fn in list(globals().items()):
            if name.startswith("test_") and callable(fn):
                print(name)
                args = fn.__code__.co_varnames[:fn.__code__.co_argcount]
                fn(*[dict(tmp=tmp, made=made)[a] for a in args])
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
