"""Does `mcdonald noise` read the background apertures as the flicker stage read them, and are its centile, its tail and
its false discovery rate what they say? (ROADMAP 0.6 objective 6; IDEAS.md S3, E24, D7; docs/method.md section 63.)

On drawn data only:

- the curves as judged: a drawn group, one member lost against what is behind it on some frames, judged by
  `flicker.judge` (which writes its CSV); `noisemodel.as_judged` reads the CSV back and every curve the stage read gives
  back the stage's own strongest line, frequency and amplitude, to the CSV's rounding;
- the reading: a line planted in grain is the strongest in its half-hertz bin at the amplitude planted, and stands over
  its continuum past the drawn null's 99th centile; grain alone stands under it nearly always;
- the tail: a generalised Pareto's shape and scale come back from drawn excesses; the p-value of a draw from the same
  population is uniform, past the threshold too; a value past the sample's largest still gets a p, smaller than the
  sample can show; the threshold rule picks a stable one;
- the false discovery rate: Benjamini and Hochberg's own example (1995) gives their four; Benjamini-Yekutieli is
  stricter; under the null with signals mixed in, the share of false discoveries stays under q; one test a video;
- the centile: drawn backgrounds in twelve videos, a beat at a known quantile of their population reads back about
  there, its interval holds it, a stratum short of videos says so; a planted beat in a drawn curve, read by `reading`,
  sits where its amplitude sits among the backgrounds;
- the p-values against the model, each background with its own video left out, are uniform;
- the strata: contrast is one, a thin cell falls back by its length first and says which stratum it used, a window's
  reading is held against windows; the cautious p is never under the p past the threshold;
- the command end to end on a drawn batch folder: --read, --build, --model, --fdr, each with its --json envelope;
- and, where the data folder has them, the reference model of record read on PR41's reference case file: its bird's
  centile and its line's p, as recorded (a golden on a real clip).

    python3 tests/test_noise.py        # or: pytest tests/
"""
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import flicker, noisemodel as nm  # noqa: E402

FAIL = []


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def quiet(*a, **k):
    pass


def drawn_group(seed=3, n=240, fps=30.0):
    """Two members and their apertures: member 0 beats at 7 Hz and is lost (its brightness near nothing) on six short
    runs of frames; member 1 is seen from frame 31. The set about the member seen longest and each member's own."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / fps
    m0 = 1000 * (1 + 0.1 * np.sin(2 * np.pi * 7.0 * t)) + rng.normal(0, 6, n)
    for a in (40, 41, 90, 150, 151, 200):
        m0[a] = 3.0
    m1 = list(2500 * (1 + 0.02 * rng.normal(size=n)) + rng.normal(0, 6, n))
    m1[:30] = [None] * 30
    raw = {"member 0": list(m0), "member 1": m1}
    for dx, dy in flicker.BACKGROUND:
        raw[f"background {dx:+d},{dy:+d}"] = list(rng.normal(0, 30, n) + 5 * np.sin(2 * np.pi * 2.2 * t + dx))
        raw[f"background of member 0 {dx + 3:+d},{dy:+d}"] = list(rng.normal(0, 25, n))
        own1 = list(rng.normal(0, 40, n))
        own1[:30] = [None] * 30
        raw[f"background of member 1 {dx:+d},{dy - 3:+d}"] = own1
    fields = dict(frames=n, first=1, last=n, codec=None, aperture_px={"member 0": 4.0, "member 1": 6.0},
                  tracks=["member 0", "member 1"], spans={"member 0": (1, n), "member 1": (31, n)})
    return raw, fields, n, fps


def test_the_curves_as_judged(tmp):
    raw, fields, n, fps = drawn_group()
    ns = list(range(1, n + 1))
    found = flicker.judge({k: list(v) for k, v in raw.items()}, ns, fps, [], dict(fields), "member 0", out=str(tmp / "g"), say=quiet)
    F = found.fields
    ns2, cols = nm.read_csv(tmp / "g_flicker.csv")
    got = nm.as_judged(F, ns2, cols, fps)
    read = {k for k, v in (F.get("curves") or {}).items() if v}
    same = 0
    for c in got:
        p = flicker.peak(c["curve"], fps, [], c["scale"], err=False)
        s = F["curves"][c["name"]]
        same += int(abs(p["hz"] - s["hz"]) < 1e-9 and abs(p["amplitude"] - s["amplitude"]) <= 1e-4 * s["amplitude"])
    check(bool(F.get("lost")) and {c["name"] for c in got} == read and same == len(read),
          "every curve the stage read comes back from its CSV as the stage read it: stretch, lost frames filled, scale",
          f"{same} of {len(read)} the same (lost frames {sum(len(v) for v in (F.get('lost') or {}).values())})")
    kinds = {c["name"]: c for c in got}
    b0 = kinds.get("background of member 0 +3,+25")
    b1 = kinds.get("background of member 1 +0,+22")
    check(b0 is not None and b1 is not None and abs(b0["scale"] - np.median([v for v in raw["member 0"] if v > 100])) < 30
          and b1["frames"][0] == 31 and b1["scale"] != b0["scale"],
          "each member's own apertures in that member's brightness, over that member's frames",
          f"scales {b0 and round(b0['scale'])} and {b1 and round(b1['scale'])}; member 1's from frame {b1 and b1['frames'][0]}")
    row = dict(in_group_set=True, occupied=0.0)
    check(nm.dropped_because(row) == "the set about a group's member seen longest"
          and nm.dropped_because(dict(in_group_set=False, occupied=0.2)) == "something as bright as the object in it"
          and nm.dropped_because(dict(in_group_set=False, occupied=0.05, folder="v", object="object-2"), {("v", "object-2"): True})
          == "another row's track" and nm.dropped_because(dict(in_group_set=False, occupied=0.05, folder="v", object="o")) is None,
          "the rules that drop an aperture: a group's shared set, something bright in it, another row's track")


def test_the_reading():
    fps, n = 30.0, 300
    t = np.arange(n) / fps
    rng = np.random.default_rng(11)
    f = 2000 * (1 + 0.05 * np.sin(2 * np.pi * 7.3 * t)) + rng.normal(0, 20, n)
    r = nm.reading(f, fps)
    j = nm.bin_of(7.3)
    bins = np.array(r["bins"], float)
    check(int(np.nanargmax(bins)) == j and abs(bins[j] - 0.05) < 0.006 and abs(r["hz"] - 7.3) < 0.1,
          "a line planted in grain is the strongest of its half-hertz bin, at its amplitude",
          f"bin {nm.GRID[j]:.1f} Hz: {bins[j]:.4f} against 0.05 planted; peak {r['hz']:.2f} Hz")
    check(r["standing"] > 2 and r["continuum_p"] is not None and r["continuum_p"] < 0.01 and r["windows"].shape[1] == len(nm.GRID),
          "and it stands over its own continuum past the drawn null's 99th centile", f"standing {r['standing']:.2f}")
    st = [nm.reading(2000 + rng.normal(0, 20, n), fps, windows=False)["standing"] for _ in range(60)]
    check(np.mean(np.array(st) >= 1.0) <= 0.05, "grain alone stands under it nearly always",
          f"{np.mean(np.array(st) >= 1.0):.0%} of 60 at 1 or more")
    noise = rng.normal(0, 20, n)
    bg = nm.reading(noise, fps, scale=2000.0, windows=False)
    check(abs(bg["amplitude"] - flicker.peak(noise, fps, (), 2000.0)["amplitude"]) < 1e-12 and bg["amplitude"] < 0.01,
          "a background aperture is read in the object's brightness, as `flicker.peak` reads it", f"{bg['amplitude']:.4f}")


def test_the_tail():
    from scipy import stats
    rng = np.random.default_rng(5)
    x = stats.genpareto.rvs(0.15, scale=1.0, size=3000, random_state=rng)
    xi, sigma = nm.gpd_fit(x)
    check(abs(xi - 0.15) < 0.08 and abs(sigma - 1.0) < 0.12, "a generalised Pareto's shape and scale come back from 3,000 draws",
          f"shape {xi:+.3f} (0.15), scale {sigma:.3f} (1)")
    ref = rng.exponential(1.0, 20000)
    fit = nm.tail_fit(ref, float(np.quantile(ref, 0.95)))
    new = rng.exponential(1.0, 20000)
    p = np.array([nm.tail_p(v, ref, fit) for v in new])
    rates = [(a, float(np.mean(p <= a))) for a in (0.1, 0.01, 0.001)]
    ok = all(abs(r - a) <= 4 * np.sqrt(a * (1 - a) / len(new)) + 0.15 * a for a, r in rates)
    check(ok, "a draw from the same population has a uniform p, past the threshold too",
          ", ".join(f"p <= {a:g}: {r:.4f}" for a, r in rates))
    far = nm.tail_p(ref.max() + 3.0, ref, fit)
    check(0 < far < 1 / (len(ref) + 1), "a value past the sample's largest still has a p, under what the sample alone can show",
          f"{far:.2e} against 1/{len(ref) + 1}")
    stab = nm.stability(ref, B=60)
    th = nm.threshold(stab)
    check(th is not None and abs(th["xi"]) < 0.1, "the stability rule picks a threshold where the shape holds (an exponential: 0)",
          f"the {100 * th['q']:g}th centile, shape {th['xi']:+.3f}")


def test_the_false_discovery_rate():
    p = [0.0001, 0.0004, 0.0019, 0.0095, 0.0201, 0.0278, 0.0298, 0.0344, 0.0459, 0.3240, 0.4262, 0.5719, 0.6528, 0.7590, 1.0]
    f, adj = nm.bh(p, 0.05)
    g, _ = nm.by(p, 0.05)
    check(list(np.flatnonzero(f)) == [0, 1, 2, 3] and list(np.flatnonzero(g)) == [0, 1, 2],
          "Benjamini and Hochberg's own example (1995): four discoveries at 0.05; Benjamini-Yekutieli three",
          f"{int(f.sum())} and {int(g.sum())}")
    rng = np.random.default_rng(2)
    fdp, fdp_by = [], []
    for _ in range(200):
        null = rng.uniform(size=950)
        sig = rng.uniform(0, 1e-4, size=50)
        pp = np.r_[sig, null]
        d, _ = nm.bh(pp, 0.05)
        e, _ = nm.by(pp, 0.05)
        fdp.append(d[50:].sum() / max(1, d.sum()))
        fdp_by.append(e[50:].sum() / max(1, e.sum()))
    check(np.mean(fdp) <= 0.05 and np.mean(fdp_by) <= np.mean(fdp),
          "with 50 signals among 1,000, the share of false discoveries stays under q (Benjamini-Yekutieli under it)",
          f"{np.mean(fdp):.4f} and {np.mean(fdp_by):.4f} at q 0.05")
    v = nm.per_video([0.01, 0.2, 0.5, 0.004, 0.9], ["a", "a", "a", "b", "b"])
    check(abs(v["a"][0] - 0.03) < 1e-12 and v["a"][1] == 3 and abs(v["b"][0] - 0.008) < 1e-12 and v["b"][2] == 3,
          "one test a video: its smallest p times its count", str(v))


def drawn_backgrounds(videos=12, each=20, seed=9, fps=30.0, frames=200, aperture=4.0, contrast=10.0):
    """Background rows as `video_reading` writes them, drawn: each video's grain its own (a scale drawn per video), the
    bins Rayleigh in grey levels a pixel, the power over the continuum exponential."""
    rng = np.random.default_rng(seed)
    rows = []
    for v in range(videos):
        s = rng.uniform(0.5, 1.5)
        for k in range(each):
            g = s * rng.rayleigh(1.0, len(nm.GRID))
            rows.append(dict(folder=f"v{v:02d}", object=f"object-{k // 4 + 1}", row=k, name=f"background {k}", owner="object",
                             fps=fps, frames=frames, aperture_px=aperture, contrast=contrast, bins=list(g / contrast),
                             standing=float(np.sqrt(rng.exponential(0.2))), amplitude=float(g.max() / contrast)))
    return rows


def test_the_centile():
    rows = drawn_backgrounds()
    m = nm.Model(rows)
    rng = np.random.default_rng(1)
    pop = rng.uniform(0.5, 1.5, 200000) * rng.rayleigh(1.0, 200000)      # the population the videos are drawn from
    q90 = float(np.quantile(pop, 0.90))
    j = nm.bin_of(7.2)

    def own_share(g):                                   # each video's share under g, averaged: what `centile` says it is
        return 100 * np.mean([np.mean(m.grey_bins[m.video == v, j] < g) for v in sorted(set(m.video))])
    c = m.centile(7.2, q90 / 10.0, 10.0, 30.0, 200, 4.0)
    check(c["centile"] is not None and abs(c["centile"] - own_share(q90)) < 1e-9 and c["lo"] <= 90 <= c["hi"] and c["videos"] == 12,
          "a beat at the population's 90th centile: each video weighs the same, and the interval over videos holds 90",
          f"{c['centile']:.1f} % ({c['lo']:.1f}-{c['hi']:.1f}), {c['videos']} videos")
    left = m.centile(7.2, q90 / 10.0, 10.0, 30.0, 200, 4.0, leave="v03")
    check(left["videos"] == 11 and left["apertures"] == 220, "its own video's backgrounds left out", f"{left['videos']} videos")
    short = m.centile(7.2, q90 / 50.0, 50.0, 30.0, 200, 4.0)
    check(short["centile"] is None and "videos in its stratum" in (short["why"] or ""),
          "a stratum with no backgrounds (another contrast) gives no centile, and says why", short["why"] or "")
    # a beat planted in a drawn curve, read by the stage's reading, sits where its amplitude sits among the backgrounds
    fps, n = 30.0, 200
    t = np.arange(n) / fps
    f = 3000 * (1 + 0.08 * np.sin(2 * np.pi * 7.2 * t)) + rng.normal(0, 3, n)
    r = nm.reading(f, fps, windows=False)
    contrast = 15.0                                      # its brightness over its ring, a pixel: the drawn backgrounds' class
    c2 = m.centile(r["hz"], r["amplitude"], contrast, fps, n, 4.0)
    gain = float(flicker._gain([7.2], fps)[0])         # the running mean's own transfer at 7.2 Hz (1.09 at 30 fps)
    want = own_share(r["amplitude"] * contrast)
    check(c2["centile"] is not None and abs(c2["centile"] - want) < 1e-9 and abs(r["amplitude"] - 0.08 * gain) < 0.002,
          "a beat planted in a drawn curve is read as the stage reads it (the running mean's gain in it) and sits at that "
          "amplitude's centile", f"{c2['centile'] if c2['centile'] is None else round(c2['centile'], 1)} for the 8.0 % planted, read {100 * r['amplitude']:.2f} % "
          f"(8.0 % times the gain {gain:.3f}), {c2['grey']:.2f} grey levels")


def test_the_strata_and_their_fallback():
    rows = drawn_backgrounds(videos=12, each=12, seed=8, contrast=30.0)
    for r in rows[:72]:                                   # six videos' worth at contrast 50: a thinner cell
        r["contrast"] = 50.0
    m = nm.Model(rows)
    a = m.centile(6.1, 0.05, 30.0, 30.0, 200, 4.0)
    b = m.centile(6.1, 0.05 * 30 / 50, 50.0, 30.0, 200, 4.0)
    check(nm.contrast_class(19.9) == "contrast under 20" and nm.contrast_class(20) == "contrast 20-40"
          and nm.contrast_class(40) == "contrast 40 or more" and a["stratum"].get("contrast") == "contrast 20-40"
          and a["videos"] == 6 and a["centile"] is None,
          "contrast is a stratum, and a stratum of six videos is too few even after the fallback",
          f"{a['stratum']}, {a['videos']} videos: {a['why']}")
    rows2 = drawn_backgrounds(videos=12, each=12, seed=8, contrast=30.0)
    for r in rows2[:72]:
        r["frames"] = 400                                 # six videos long, six short: the length cell is thin, the rest not
    m2 = nm.Model(rows2)
    c = m2.centile(6.1, 0.05, 30.0, 30.0, 200, 4.0)
    check(c["centile"] is not None and "length" not in c["stratum"] and c["videos"] == 12,
          "a cell short of videos falls back by its length first, and says which stratum it used", str(c["stratum"]))
    w = m2.centile(6.1, 0.05, 30.0, 30.0, 200, 4.0, windows=True)
    check(w["centile"] is None and w["windows"] and "videos" in (w["why"] or ""),
          "a window's reading is held against the backgrounds' windows, and with none kept says so", w["why"] or "")


def test_the_cautious_p():
    rows = drawn_backgrounds(videos=15, each=60, seed=6)
    m = nm.Model(rows)
    s, v = m.reference_power()
    st = nm.stability(s, B=40, groups=v)
    th = nm.threshold(st)
    m.fit = nm.tail_fit(s, float(np.quantile(s, th["q"])))
    m.fit["q"] = th["q"]
    m.meta = dict(threshold=th)
    below = float(np.sqrt(np.quantile(s, 0.5)))
    far = float(np.sqrt(s.max() * 3))
    check(m.p_cautious(below) == m.p_value(below) and m.p_cautious(far) >= m.p_value(far) > 0,
          "the cautious p is the p under the threshold, and at least the p past the corpus's largest",
          f"{m.p_value(far):.2e} and {m.p_cautious(far):.2e} at three times the largest power")


def test_the_reference_model_on_a_reference_case(tmp):
    """The golden on a real clip: the reference model in the data folder (made from the catalog run of 2026-11-13/14)
    read on the bird paper's PR41 case file. Skipped where the data folder has neither."""
    import zipfile
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import reference_data
    d = reference_data.root()
    mdir, case = d / "noise", d / "cases" / "pr41.mcdonald"
    if not (mdir / nm.MODEL).exists() or not case.exists():
        print(f"  SKIP  the reference model on PR41's case file: {mdir} or {case} is not here")
        return
    m = nm.open_model(mdir)
    meta = m.meta
    check(meta["kept"] == 2028 and meta["videos"] == 65 and abs(meta["fit"]["xi"] - 0.1065) < 5e-4 and meta["threshold"]["q"] == 0.925,
          "the reference model is the one of record: 2,028 apertures in 65 videos, the tail past the 92.5th centile, shape +0.107",
          f"{meta['kept']}, {meta['videos']}, {meta['fit']['xi']:+.4f}")
    Z = zipfile.ZipFile(case)
    d41 = json.loads(Z.read("case/object-1/pr41_case.json"))
    F, fps = d41["stages"]["flicker"]["fields"], float(d41["clip"]["fps"])
    (tmp / "pr41.csv").write_bytes(Z.read("case/object-1/pr41_flicker.csv"))
    ns, cols = nm.read_csv(tmp / "pr41.csv")
    got = {c["name"]: c for c in nm.as_judged(F, ns, cols, fps)}
    o = got["object"]
    rd = nm.reading(o["curve"], fps, (F.get("codec") or {}).get("lines_hz") or [], F["top_hz"], windows=False)
    b = F["beat"]["object"]
    R = F["aperture_px"]["object"]
    c = m.centile(b["hz"], b["amplitude"], o["level"] / (np.pi * R * R), fps,
                  b["last"] - b["first"] + 1, R, windows=not b["source"].startswith("the whole"), leave="pr41", boot=200)
    p = m.p_value(rd["standing"], leave="pr41")
    check(abs(b["hz"] - 6.43) < 0.01 and c["centile"] is not None and abs(c["centile"] - 97.3) < 0.5 and 3e-8 < p < 2e-7,
          "PR41's bird (6.43 Hz, the paper's rule) sits at the 97th centile of the backgrounds' lines and its line's p is about 1e-7",
          f"{b['hz']:.2f} Hz, {100 * b['amplitude']:.1f} %: centile {c['centile']:.1f} ({c['lo']:.1f}-{c['hi']:.1f}), p {p:.2e}")


def test_the_p_values_with_the_video_left_out():
    rows = drawn_backgrounds(videos=15, each=60, seed=4)
    m = nm.Model(rows)
    s, v = m.reference_power()
    st = nm.stability(s, B=30, groups=v)
    th = nm.threshold(st)
    m.fit = nm.tail_fit(s, float(np.quantile(s, th["q"])))
    m.fit["q"] = th["q"]
    p = np.array([m.p_value(r["standing"], leave=r["folder"]) for r in rows])
    rates = [(a, float(np.mean(p <= a))) for a in (0.2, 0.05, 0.01)]
    check(all(abs(r - a) <= 4 * np.sqrt(a * (1 - a) / len(p)) + 0.2 * a for a, r in rates),
          "each background's p against the others, its own video left out, is uniform",
          ", ".join(f"p <= {a:g}: {r:.3f}" for a, r in rates))


def drawn_batch(tmp, videos=3):
    """A batch folder as `mcdonald batch` leaves one: a video folder each, an object in it with its case file's flicker
    fields and its CSV (judged by `flicker.judge`), and the table's rows."""
    B = tmp / "batch"
    rows = []
    for v in range(videos):
        raw, fields, n, fps = drawn_group(seed=20 + v)
        folder = B / f"vid{v}" / "object-1"
        folder.mkdir(parents=True)
        found = flicker.judge({k: list(x) for k, x in raw.items()}, list(range(1, n + 1)), fps, [], dict(fields), "member 0",
                              out=str(folder / f"vid{v}"), say=quiet)
        case = dict(clip=dict(fps=fps, width=320, height=240), stages=dict(flicker=dict(fields=found.fields, result={})))
        (folder / f"vid{v}_case.json").write_text(json.dumps(case, default=flicker_plain), encoding="utf-8")
        rows.append(dict(id=f"VID{v}", folder=f"vid{v}", object="1", label="No physical conclusion", several="yes", dark="no",
                         same_as=""))
    with open(B / "batch.tsv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(rows[0]), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    return B


def flicker_plain(x):
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, tuple):
        return list(x)
    return str(x)


def test_the_command(tmp):
    B = drawn_batch(tmp)
    R = tmp / "readings"
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parent.parent / "src"))

    def run(*a):
        r = subprocess.run([sys.executable, "-m", "mcdonald.cli", "noise", *a, "--json"], capture_output=True, encoding="utf-8", env=env)
        try:
            return r.returncode, json.loads(r.stdout)
        except ValueError:
            return r.returncode, dict(stdout=r.stdout[-300:], stderr=r.stderr[-600:])
    code, d = run("--read", str(B), "--out", str(R))
    check(code == 0 and d.get("command") == "noise" and d["results"].get("videos") == 3 and len(list(R.glob("*.json.gz"))) == 3,
          "--read reads every video folder of a batch into its own folder, and says so as JSON", str(d.get("results") or d)[:160])
    code, d = run("--build", str(R), "--batch", str(B))
    res = d.get("results") or {}
    check(code == 0 and res.get("kept", 0) > 0 and res.get("dropped", {}).get("the set about a group's member seen longest") == 12
          and (R / nm.MODEL).exists() and (R / nm.BACKGROUNDS).exists(),
          "--build keeps each member's own apertures and drops the group's shared set, and writes the model",
          f"kept {res.get('kept')}, dropped {res.get('dropped')}")
    code, d = run("--model", str(R), "--hz", "7.0", "--share", "0.1", "--contrast", "20", "--frames", "240", "--standing", "3")
    c = (d.get("results") or {}).get("centile") or {}
    check(code == 0 and c.get("centile") is None and "videos" in (c.get("why") or "") and (d["results"].get("p") or 1) < 0.05,
          "--model with three videos gives no centile and says why, and a p from the tail", f"{c.get('why')}; p {d['results'].get('p')}")
    code, d = run("--fdr", str(R))
    res = d.get("results") or {}
    check(code == 0 and res.get("corpus", {}).get("m") == 3 and "0.05" in res.get("corpus", {}),
          "--fdr gives the rate over the batch's rows, three ways", str({k: res.get(k, {}).get("m") for k in ("corpus", "drawn", "stage")}))


def main():
    with tempfile.TemporaryDirectory(prefix="mcdonald-test-noise-") as td:
        tmp = Path(td)
        for name, fn in list(globals().items()):
            if name.startswith("test_") and callable(fn):
                print(name)
                args = fn.__code__.co_varnames[:fn.__code__.co_argcount]
                sub = tmp / name
                sub.mkdir()
                fn(*[dict(tmp=sub)[a] for a in args])
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
