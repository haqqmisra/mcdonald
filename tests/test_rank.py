"""Does `mcdonald rank` give honest tail probabilities, and does it take the record's defects out first?

Drawn populations, no video (docs/method.md section 64):

- **calibrated**: objects drawn like a class get p-values uniform against it (the share at or under 0.05 and 0.10 within
  a binomial band of the level, and a Kolmogorov-Smirnov test that does not refuse uniform); the held-out calibration of
  drawn controls (several to a video, each held out with its video) is uniform too;
- **power and the measure that drove it**: an object drawn far out on one axis gets the smallest p-value the class's size
  allows, 1/(n+1), and that axis, with the right sign, is named as what drove it (Av14);
- **NO POWER is an answer** (E5): a class with fewer than 19 objects of the object's width, an object outside a class's
  range of contrast or frame rate, an object with no width, and a group get no p-value and a reason, never a number;
- **missing is missing**: an axis the object lacks is not scored, and one too few of a class have is let go;
- **rows to objects**: a row on another's track is folded into it; the defects (no track, a failed stage, integrity's
  failure, the overlay, a blend, a scene feature, a track not held on its spot, held pictures) each fire on their own
  drawn record and not on a clean one, and a defect is never ranked;
- **the corpus summary**: Benjamini-Hochberg and Benjamini-Yekutieli on worked examples; the bootstrap over videos is
  reproducible and its interval holds the share;
- **matching known objects**: a track on a labelled box is matched, one beside it is not, and of two pieces on one
  known object the longer stands for it;
- **the command**, end to end on drawn records and a drawn controls' table: the table, the page and the envelope are
  written, and no word of them names an object anomalous.

    python3 tests/test_rank.py        # or: pytest tests/
"""
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import rank  # noqa: E402

FAIL = []


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def band(n, a, z=3.5):
    """A binomial band round the level a for n draws: (low, high) shares."""
    s = math.sqrt(a * (1 - a) / n)
    return a - z * s, a + z * s


# ---- drawn objects -----------------------------------------------------------------------------------------------------
CLASSES = {  # each class's middle on the scored axes (lognormal where the axis is logged)
    "alpha": dict(beat_amp=0.02, beat_hz=3.0, light_var=0.05, light_over_bg=2.0, size_trend=0.0, rate_scene_w=5.0, speed_spread=0.3),
    "beta": dict(beat_amp=0.08, beat_hz=8.0, light_var=0.20, light_over_bg=6.0, size_trend=0.2, rate_scene_w=20.0, speed_spread=0.6),
}


def drawn_axes(rng, cls, size=6.0, contrast=40.0, fps=30.0, missing=()):
    m = CLASSES[cls]
    ax = dict.fromkeys(rank.AXIS)
    for k, v in m.items():
        if k in missing:
            continue
        ax[k] = float(v * math.exp(rng.normal(0, 0.35))) if rank.AXIS[k][4] == "log" else float(v + rng.normal(0, 0.8 if k == "beat_hz" else 0.1))
    ax.update(size_px=size, contrast=contrast, fps=fps, frames=200.0, held=0.0)
    return ax


def drawn_controls(rng, per_class=80, per_video=3, contrasts=(20.0, 40.0, 80.0, 160.0)):
    out = []
    for cls in CLASSES:
        for i in range(per_class):
            out.append(dict(source="drawn", **{"class": cls}, scored=True, video=f"{cls}-v{i // per_video}", key=f"{cls}#{i}",
                            truth="", on=0, shared=0, defect="",
                            axes=drawn_axes(rng, cls, size=float(rng.uniform(3, 9)), contrast=contrasts[i % len(contrasts)])))
    return out


def drawn_record(rng, cls="alpha", unit="v1", k=1, **kw):
    """A batch record as `rank.extract` writes it, with the fields the axes and the rules read."""
    ax = drawn_axes(rng, cls)
    row = dict(id=unit.upper(), unit=unit, folder=unit, file=f"{unit}.mp4", object=k, object_state="measured", release="01", fps="30",
               followed_frames=200, size_px=5.0, same_as=None, several="no", label="No physical conclusion", grade="Low",
               rate_is="against the background", rate_px_per_s=ax["rate_scene_w"] * 6.0, checklist=dict(camera="Yes"))
    row.update(kw.pop("row", {}))
    r = dict(row=row, case=f"/nowhere/{unit}/object-{k}/x_case.json", folder=f"/nowhere/{unit}/object-{k}", no_power={},
             clip=dict(fps=30.0), integrity={"cadence": "PASS"},
             verify=dict(frames=200, detected=190, weak=0, contrast=40.0),
             layers=dict(all=dict(median=ax["rate_scene_w"] * 6.0, p16=ax["rate_scene_w"] * 6.0 * (1 - ax["speed_spread"] / 2),
                                  p84=ax["rate_scene_w"] * 6.0 * (1 + ax["speed_spread"] / 2)), shift_err=[0.03, 0.03], shift_over=5),
             kinematics=dict(v=30.0, noise=0.5, width=6.0, sagitta=2.0, length=100.0, resid_frac=0.05),
             camera=dict(size_ratio=math.exp(ax["size_trend"])), groups=dict(several=False, points=1, on_sensor=0),
             track=dict(n=200, fixed_share=0.05),
             flicker=dict(extent=6.0, held=0.0, amp=ax["beat_amp"], hz=ax["beat_hz"], stands=3.0, cont_p=0.01, blend=False),
             curves=dict(light_var=ax["light_var"], light_over_bg=ax["light_over_bg"], light_fast=0.01))
    for k_, v in kw.items():
        r[k_] = v
    return r


# ---- the tests ---------------------------------------------------------------------------------------------------------
def test_uniform_against_its_own_class():
    rng = np.random.default_rng(11)            # a new class each time: a p-value is uniform over the class and the object
    ps = [rank.against(drawn_axes(rng, "alpha"), [drawn_axes(rng, "alpha") for _ in range(60)])["p"] for _ in range(600)]
    a = np.array(ps)
    for t in (0.05, 0.10, 0.20):
        lo, hi = band(len(a), t)
        check(lo <= np.mean(a <= t) <= hi, f"objects drawn like the class: {np.mean(a <= t):.3f} at or under {t}", f"band {lo:.3f}-{hi:.3f}")
    u = rank.uniformity(ps)
    check(u["ks_p"] > 0.001, "and their p-values are not refused as uniform (Kolmogorov-Smirnov)", f"D = {u['ks']:.3f}, p = {u['ks_p']:.3g}")
    check(min(ps) >= 1 / 61 - 1e-12, "no p-value is under 1/(n+1)", f"{min(ps):.4f}")
    mem = [drawn_axes(rng, "alpha") for _ in range(60)]


def test_far_out_on_one_axis():
    rng = np.random.default_rng(12)
    mem = [drawn_axes(rng, "alpha") for _ in range(40)]
    x = drawn_axes(rng, "alpha")
    x["light_over_bg"] = 2.0 * 50
    r = rank.against(x, mem)
    check(abs(r["p"] - 1 / 41) < 1e-12, "an object far out gets the smallest p-value the class allows, 1/(n+1)", f"p = {r['p']:.4f}")
    check(r["axis"] == "light_over_bg" and r["z"] > 0, "and the axis it is far out on drove it, above the class's middle",
          f"{r['axis']}, z = {r['z']:.1f}")
    check(r["axis_p"] <= 1 / 41 + 1e-12, "that axis alone gives it the same tail", f"{r['axis_p']:.4f}")
    x["light_over_bg"] = 2.0 / 50
    r = rank.against(x, mem)
    check(r["axis"] == "light_over_bg" and r["z"] < 0, "far below drives it too, with the sign below", f"z = {r['z']:.1f}")
    check("below" in rank.drove(r), "and the list says below", rank.drove(r))


def test_missing_is_missing():
    rng = np.random.default_rng(13)
    mem = [drawn_axes(rng, "alpha") for _ in range(40)]
    x = drawn_axes(rng, "alpha", missing=("beat_amp", "beat_hz"))
    r = rank.against(x, mem)
    check(r["p"] is not None and "beat_amp" not in r["axes"], "an axis the object lacks is not scored", ",".join(r["axes"]))
    mem2 = [dict(m, rate_scene_w=None) if i % 3 else m for i, m in enumerate(mem)]
    r = rank.against(drawn_axes(rng, "alpha"), mem2)
    check(r["p"] is not None and "rate_scene_w" not in r["axes"] and r["n"] == 40,
          "an axis too few of the class have is let go, and every member counts on the rest", f"n = {r['n']}, axes {','.join(r['axes'])}")
    none = dict.fromkeys(rank.AXIS)
    check(rank.against(none, mem)["p"] is None, "an object with no scored measurement has no p-value")
    check(rank.axes_of(dict(row=dict(object=1), case=None))["beat_amp"] is None, "a record with no case has no measurements, not zeros")
    rec = drawn_record(rng)
    rec["flicker"]["cont_p"] = 0.6
    a = rank.axes_of(rec)
    check(a["beat_hz"] is None and a["beat_amp"] is not None, "a line that does not stand above the slow wander has no frequency, but its amplitude")
    rec["camera"]["zooms"] = 2
    check(rank.axes_of(rec)["size_trend"] is None, "the size's change is not read across a zoom of the camera")


def test_no_power_is_an_answer():
    rng = np.random.default_rng(14)
    ctl = drawn_controls(rng, per_class=30)
    edges = rank.strata_edges(ctl)
    med = float(np.median([c["axes"]["contrast"] for c in ctl]))
    check(edges == [med], "the strata are cut at the controls' own median contrast", f"{edges} against {med}")
    ps = rank.pvalues(drawn_axes(rng, "alpha", contrast=40.0), ctl, ["alpha", "beta"], edges)
    check(all(r["p"] is None and "under the 19" in r["why"] for r in ps.values()),
          "a class with fewer than 19 objects of the object's contrast has no power, and says so", ps["alpha"].get("why", ""))
    ctl = drawn_controls(rng, per_class=150)
    edges = rank.strata_edges(ctl)
    check(rank.pvalues(drawn_axes(rng, "alpha", contrast=40.0), ctl, ["alpha"], edges)["alpha"]["p"] is not None,
          "with enough of the class at its contrast, it has a p-value")
    r = rank.pvalues(drawn_axes(rng, "alpha", contrast=4000.0), ctl, ["alpha"], edges)["alpha"]
    check(r["p"] is None and "outside the class's range" in r["why"] and "contrast" in r["why"],
          "an object outside a class's range of contrast has no power from it (E5)", r.get("why", ""))
    r = rank.pvalues(drawn_axes(rng, "alpha", contrast=40.0, fps=60.0), ctl, ["alpha"], edges)["alpha"]
    check(r["p"] is None and "fps" in r["why"], "nor outside its frame rates", r.get("why", ""))
    r = rank.pvalues(drawn_axes(rng, "alpha", contrast=40.0, size=60.0), ctl, ["alpha"], edges)["alpha"]
    check(r["p"] is None and "size_px" in r["why"], "nor wider than any of the class", r.get("why", ""))
    ax = drawn_axes(rng, "alpha")
    ax["contrast"] = None
    r = rank.pvalues(ax, ctl, ["alpha"], edges)["alpha"]
    check(r["p"] is None and "no stratum" in r["why"], "an object with no contrast has no stratum, and no power", r.get("why", ""))
    p, c, k = rank.least_unlike(dict(a=dict(p=None, why="x"), b=dict(p=None, why="y")))
    check(p is None and k == 0, "with no class that could tell there is no largest p-value")
    p, c, k = rank.least_unlike(dict(a=dict(p=0.02, score=5.0), b=dict(p=0.3, score=2.0), c=dict(p=None)))
    check(p == 0.3 and c == "b" and k == 2, "the class least unlike is the one with the largest p-value", f"{c} {p}")


def test_calibration_held_out():
    rng = np.random.default_rng(15)
    ctl = drawn_controls(rng, per_class=150, per_video=3)
    edges = rank.strata_edges(ctl)
    cal = rank.calibrate(ctl, ["alpha", "beta"], edges)
    for c in ("alpha", "beta"):
        u = rank.uniformity(cal["own"][c])
        lo, hi = band(u["n"], 0.10)
        check(u["n"] == 150 and lo <= u["le_0.10"] <= hi, f"held out with its video, class {c}'s p-values hold the level",
              f"{u['le_0.10']:.3f} at or under 0.10 of {u['n']}")
    x = rank.uniformity(cal["cross"]["alpha"]["beta"])
    check(x["le_0.05"] > 0.8, "and drawn classes that differ are told apart", f"{x['le_0.05']:.2f} of alpha unlike beta at 0.05")


def test_objects_and_defects():
    rng = np.random.default_rng(16)
    a = drawn_record(rng, unit="v1", k=1)
    b = drawn_record(rng, unit="v1", k=2, row=dict(same_as=1))
    c = drawn_record(rng, unit="v1", k=3, row=dict(several="yes"))
    kept = rank.objects([a, b, c])
    check([r["key"] for r in kept] == ["v1#1", "v1#3"] and a["also"] == ["v1#2"], "a row on another's track is folded into it",
          str([r["key"] for r in kept]))
    check(kept[1]["kind"] == "group" and kept[0]["kind"] == "single", "a group stays one object of the kind group")
    check(rank.defects(drawn_record(rng)) == [], "a clean record has no defect")
    rec = drawn_record(rng, track=dict(n=200, fixed_share=0.8), row=dict(checklist=dict(camera="Can't tell")))
    check("sensor" not in [k for k, _ in rank.defects(rec)], "a spot still on a picture not seen to move is not called the sensor's")
    cases = {
        "not followed": dict(row=dict(object_state="not followed")),
        "failed": dict(row=dict(object_state="failed", error="boom")),
        "added": dict(integrity={"cadence": "FLAG"}),
        "overlay": dict(integrity={"layer order: symbology": "FLAG"}),
        "blend": dict(flicker=dict(blend=True)),
        "scene": dict(row=dict(checklist=dict(camera="Yes", moves="No"))),
        "sensor": dict(track=dict(n=200, fixed_share=0.8)),
        "lost": dict(verify=dict(frames=200, detected=150, weak=90, contrast=40.0)),
        "masked": dict(masks=dict(share=0.4, frames=200)),
        "held": dict(no_power={"flicker": [["beat", "the pictures are held: too few new pictures"]]}),
    }
    for rule, kw in cases.items():
        rec = drawn_record(rng, **{k: v for k, v in kw.items() if k != "row"}, row=kw.get("row", {}))
        d = [k for k, _ in rank.defects(rec)]
        check(rule in d, f"the rule '{rule}' fires on its own drawn record", ",".join(d))
    rec = drawn_record(rng, looked=dict(reason="the overlay's N", by="an agent"))
    d = rank.defects(rec)
    check([k for k, _ in d] == ["looked"] and "the overlay's N" in d[0][1], "a recorded look sets an object aside with its reason")
    rec = drawn_record(rng, verify=dict(frames=400, detected=150, weak=10, contrast=40.0))
    check("lost" not in [k for k, _ in rank.defects(rec)], "a short track in a padded clip is not called lost: only frames with no spot under it count")
    ctl = drawn_controls(rng, per_class=150)
    recs = [drawn_record(rng, unit=f"v{i}", k=1) for i in range(20)] + [drawn_record(rng, unit="vx", k=1, integrity={"cadence": "FLAG"})]
    res = rank.rank(recs, ctl)
    bad = [o for o in res["objects"] if o["defects"]]
    check(len(bad) == 1 and "rank" not in bad[0] and "ps" not in bad[0], "a defect is listed and never ranked")


def test_corpus_summary():
    ps = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216]
    check(rank.bh(ps, 0.05) == [0, 1], "Benjamini-Hochberg on a worked example", str(rank.bh(ps, 0.05)))
    check(rank.by(ps, 0.05) == [0], "Benjamini-Yekutieli, stricter, on the same", str(rank.by(ps, 0.05)))
    check(rank.bh([0.5] * 5, 0.05) == [] and rank.bh([], 0.05) == [], "and nothing where nothing is small")
    groups = [[0.01, 0.5], [0.2], [0.03, 0.04, 0.9], [0.6]]
    a, b = rank.boot_share(groups, 0.05, seed=3), rank.boot_share(groups, 0.05, seed=3)
    check(a == b and a["k"] == 3 and a["n"] == 7, "the bootstrap over videos is the same twice with one seed", f"{a['k']} of {a['n']}")
    check(a["lo"] <= a["share"] <= a["hi"], "and its interval holds the share", f"{a['lo']:.2f}-{a['hi']:.2f}")


def test_match_known_objects():
    rng = np.random.default_rng(17)
    truth = dict(video="CLIP_1", name="CLIP_1_o0", cls="bird", track={n: (100.0 + n, 50.0, 3.0, 3.0) for n in range(1, 101)})
    on, far, piece = (drawn_record(rng, unit="clip-1", k=k, row=dict(id="CLIP_1")) for k in (1, 2, 3))
    on["_track"] = {n: (100.0 + n + 1.0, 50.5) for n in range(1, 101)}
    far["_track"] = {n: (100.0 + n + 30.0, 50.0) for n in range(1, 101)}
    piece["_track"] = {n: (100.0 + n, 50.0) for n in range(1, 40)}
    m, left = rank.match([on, far, piece], [truth])
    check(len(m) == 1 and m[0][1] is on, "a track on the labelled box is matched, and the longer of two pieces stands for it",
          str([x[1]["key"] if "key" in x[1] else x[1]["row"]["object"] for x in m]))
    check(far in left and piece in left, "a track beside it is not matched")


def test_a_track_on_the_overlay(tmp):
    """A drawn video (a texture drifting 3 px a frame, a white bracket and a black block that stay put, encoded without
    loss): a track on the bracket for half its frames, then on the moving scene, is on the masks for about half; one
    on the scene alone for none; one on the block for all."""
    import shutil
    import subprocess
    if not shutil.which("ffmpeg"):
        print("  SKIP  a track on the overlay: no ffmpeg")
        return
    rng = np.random.default_rng(19)
    W, H, N = 160, 120, 60
    big = np.clip(100 + 30 * rng.standard_normal((H, W + 3 * N)), 0, 255)
    from scipy import ndimage
    big = ndimage.gaussian_filter(big, 1.0) * 1.6 - 60
    frames = []
    for n in range(N):
        f = big[:, 3 * n:3 * n + W].copy()
        f[20:23, 30:45] = 255
        f[20:35, 30:33] = 255                       # a bracket, burned in
        f[70:115, 100:150] = 0                      # a redaction block
        frames.append(np.clip(f, 0, 255).astype(np.uint8))
    video = tmp / "drawn.mkv"
    p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                        "-c:v", "ffv1", "-pix_fmt", "gray", str(video)], input=b"".join(f.tobytes() for f in frames))
    if p.returncode:
        print("  SKIP  a track on the overlay: this ffmpeg cannot write ffv1")
        return
    recs = []
    for name, path in (("half", {n: (31.0, 21.0) if n <= 30 else (60.0 + n, 50.0) for n in range(1, N + 1)}),
                       ("scene", {n: (60.0 + n / 2, 50.0) for n in range(1, N + 1)}),
                       ("block", {n: (120.0, 90.0) for n in range(1, N + 1)})):
        d = tmp / name
        d.mkdir()
        (d / "x_case.json").write_text("{}")
        (d / "x_autotrack.csv").write_text("frame,x,y\n" + "".join(f"{n},{x},{y}\n" for n, (x, y) in path.items()))
        recs.append(dict(row=dict(object=1), case=str(d / "x_case.json"), clip=dict(n0=1, n1=N, width=W, height=H), name=name))
    rank.masks_of_video(video, recs, tmp / "frames")
    sh = {r["name"]: (r.get("masks") or {}).get("share") for r in recs}
    check(sh["half"] is not None and 0.4 <= sh["half"] <= 0.6, "a track on a burned-in bracket for half its frames is on the masks for about half",
          f"{sh['half']}")
    check(sh["scene"] == 0.0, "a track on the moving scene is on no mask", f"{sh['scene']}")
    check(sh["block"] == 1.0, "a track on a redaction block is on it throughout", f"{sh['block']}")
    check("masked" in [k for k, _ in rank.defects(dict(drawn_record(rng), masks=recs[0]["masks"]))],
          "and the rule takes the half-on track out as a defect")


def test_the_command(tmp):
    rng = np.random.default_rng(18)
    ctl = drawn_controls(rng, per_class=150)
    rank.write_controls(tmp / "ctl.tsv", ctl)
    back = rank.read_controls(tmp / "ctl.tsv")
    check(len(back) == len(ctl) and back[0]["axes"]["beat_amp"] == float(f"{ctl[0]['axes']['beat_amp']:.6g}"),
          "the controls' table reads back as written")
    recs = [drawn_record(rng, cls="alpha" if i % 2 else "beta", unit=f"v{i}", k=1) for i in range(30)]
    far = drawn_record(rng, unit="vfar", k=1)
    far["curves"]["light_over_bg"] = 500.0
    far["flicker"]["amp"] = 0.9
    recs.append(far)
    recs.append(drawn_record(rng, unit="vbad", k=1, integrity={"layer order: symbology": "FLAG"}))
    rank.write_json(tmp / "rec.json.gz", dict(head={}, records=recs))
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        (tmp / "apart.tsv").write_text("id\tfile\trole\nX\tvfar.mp4\theld out\nY\tv1.mp4\topen\n")
        code = rank.main(["--records", str(tmp / "rec.json.gz"), "--controls", str(tmp / "ctl.tsv"), "--out", str(tmp / "out"),
                          "--apart", str(tmp / "apart.tsv"), "--json"])
    env = json.loads(buf.getvalue())
    check(code == 0 and env["command"] == "rank" and env["results"]["top"], "the command writes its envelope", f"exit {code}")
    check(env["results"]["top"][0]["key"] == "vfar#1", "the object drawn far out heads the list", env["results"]["top"][0]["key"])
    check(env["results"]["summary"]["defects"] == {"overlay": 1}, "the defect is counted by its rule", str(env["results"]["summary"]["defects"]))
    ap = env["results"]["summary"].get("apart") or {}
    check(ap.get("videos") == 1 and ap.get("le_0.05") == 1, "a list given with --apart is counted apart", str(ap))
    files = [tmp / "out" / f for f in ("rank.md", "rank.tsv", "rank.json")]
    check(all(f.exists() for f in files), "the page, the table and the JSON are written")
    text = " ".join(f.read_text(encoding="utf-8").lower() for f in files[:2]) + json.dumps(env).lower()
    check("anomal" not in text, "no word of them names an object anomalous")
    md = files[0].read_text(encoding="utf-8")
    check("can't tell" in md and "Benjamini-Hochberg" in md, "the page says what could not tell, and the correction for many objects")
    check(all(w in rank.RULE_WORDS for w in rank.RULES), "every rule has its words for the page")


def main():
    with tempfile.TemporaryDirectory(prefix="mcdonald-test-rank-") as td:
        for name, fn in list(globals().items()):
            if name.startswith("test_") and callable(fn):
                print(name)
                args = fn.__code__.co_varnames[:fn.__code__.co_argcount]
                d = Path(td) / name
                d.mkdir()
                fn(*[dict(tmp=d)[a] for a in args])
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
