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
    check(all(v[0] <= 0.25 and v[1] <= 1.0 for v in worst.values()),
          "after the encoder each object is where the truth table has it: within 0.25 px at the median, 1 px at the most", said)
    check(all(0.75 <= v[2] <= 1.15 for v in worst.values()),
          "its contrast survives the encoder: 0.75 to 1.15 of what was asked, at the median", said)
    check(all(0.75 <= v[3] <= 1.25 for v in worst.values()),
          "and its width: 0.75 to 1.25 of the sigma asked (the half-peak core's second moment)", said)
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


def test_one_seed_one_file(tmp, made):
    again = plant.make(tmp / "drawn.mp4", 1, N, PLANTS, tmp / "again", "drawn", seed=1, look=False)
    check(sha(again["planted"]) == sha(made["planted"]) and sha(again["none"]) == sha(made["none"]),
          "two runs with one seed give the same planted video and the same control, byte for byte")
    check(Path(again["truth"]).read_text() == Path(made["truth"]).read_text(), "and the same truth table")
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
