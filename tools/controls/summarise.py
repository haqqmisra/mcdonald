"""The infrared set's run, track by track and class by class: the table, the rates of record and their bounds.

    python3 tools/controls/summarise.py RUNS [--out TABLE.csv] [--json RATES.json]

Reads RUNS/<clip>_<object>/{stage,paper}.json.gz (`run_set.py`) and the track index, writes one row per track (TABLE.csv,
default RUNS/../svanstrom_tracks.csv) and prints, rule by rule:

- each track's call as the run of 2026-10-19 read it (`call`, unchanged, so its headline can be rebuilt): **bird** -- the
  object's own beat at 2-25 Hz (report.WINGBEAT_HZ) that comes back (the whole track, or two windows apart); **once** -- in
  one stretch only; **other** -- its own beat outside 2-25 Hz; **none** -- measured, no beat of its own; **refused** -- NO
  POWER;
- and what the report says today (**named**: "Beats like a bird", `report.bird_beats` -- the call above with the beat at
  BIRD_FLOOR of the brightness or more -- and the camera's own shake not at the beat);
- every rate with its exact (Clopper-Pearson) 95 % interval over tracks and a 95 % interval from resampling clips (a
  clip's tracks are not independent: the economics survey's E10), by class and by distance bin;
- the agreement of the two rules on one set of tracks, raw and chance-corrected (Cohen's kappa, the biology survey's X6);
- the beat's amplitude as a separator of the bird calls from the false ones (the area under the ROC curve);
- the same rates by stratum of what a clip offers -- the track's length, the object's size, its contrast, the frame rate
  (STRATA) -- since a pooled rate over easy tracks overstates the test's power on hard ones (spectrum bias), each stratum
  with fewer than STRATUM_MIN tracks given as a count and no rate;
- and how many tracks' saved curves replay to the same call.

`--json` writes the rates of record (`tests/test_controls.py` holds the suite to them). Pure Python over small files:
seconds. `--rejudge` judges every track again from its saved curves with the code as it stands, with no video -- after a
change to the judging (a gate, a floor, a rule), the whole set's rates in some minutes on a few CPUs, through the job
scheduler; the saved curves stay what the photometry made."""
import argparse
import csv
import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))
sys.path.insert(0, str(HERE.parent.parent / "tests"))

import reference_data  # noqa: E402
from mcdonald import report  # noqa: E402

RULES = ("stage", "paper")
CLASSES = ("BIRD", "AIRPLANE", "DRONE", "HELICOPTER")
BINS = ("CLOSE", "MEDIUM", "DISTANT")
CALLS = ("bird", "once", "other", "none", "refused", "error")
BOOT = 10000         # resamplings of clips for a rate's interval
# What a clip offers the test, in strata (the diagnostic-accuracy survey's spectrum bias: a pooled rate over easy controls
# overstates the test's power on harder clips), each read from what the outcome cannot set -- the track's length, the
# label's size, the set's distance bin, the frame rate -- and the object's contrast over its ring (a reading of the pixels,
# not of the beat; never flicker's `needs`, which follows the outcome). Each a dimension: (column, its bins as (label, lo,
# hi), lo <= x < hi; or (label, value, None) for a category). The edges are round numbers near the set's own quartiles,
# set before the rates were read (a judgement call); frame rate has one stratum here, the set's 30 a second.
STRATA = {
    "frames": ("frames_measured", (("60-149 frames", 60, 150), ("150-299 frames", 150, 300), ("300 frames or more", 300, 1e9))),
    "size": ("w_med", (("under 14 px wide", 0, 14), ("14-20 px", 14, 20), ("20 px or more", 20, 1e9))),
    "contrast": ("contrast_gl", (("under 10 grey levels", -1e9, 10), ("10-40 grey levels", 10, 40), ("40 or more", 40, 1e9))),
    "frame rate": ("fps", (("30 a second", 29.0, 31.0), ("60 a second", 59.0, 61.0))),
    "distance": ("distance", (("CLOSE", "CLOSE", None), ("MEDIUM", "MEDIUM", None), ("DISTANT", "DISTANT", None))),
}
STRATUM_MIN = 10     # tracks: a stratum with fewer states no rate, only its count (a judgement call: under ten, the exact
                     # interval of a rate near a half spans more than 60 points)


def offers(saved, name="object"):
    """What a track offers the test, from its saved curves: {frames_measured, fps, contrast_gl (the median brightness over
    the ring a pixel of the aperture, in grey levels), extent_px (the stage's, None for a point)}."""
    import numpy as np
    ff = saved["fields"]
    a, b = ff["spans"][name]
    raw = [v for v in saved["raw"][name][a - saved["ns"][0]:b - saved["ns"][0] + 1] if v is not None]
    ap = (ff.get("aperture_px") or {}).get(name) or 4.0
    return dict(frames_measured=int(b - a + 1), fps=round(float(saved["fps"]), 3),
                contrast_gl=round(float(np.median(raw)) / (np.pi * ap * ap), 2) if raw else None,
                extent_px=(ff.get("extent_px") or {}).get(name))


def stratum(dim, value):
    """The label of the stratum `value` sits in along `dim` (STRATA): "not read" where the track gave no value (a track
    refused before its curves were judged), None where the value is outside every bin."""
    if value in ("", None):
        return "not read"
    for lab, lo, hi in STRATA[dim][1]:
        if hi is None:
            if str(value) == lo:
                return lab
        elif lo <= float(value) < hi:
            return lab
    return None
SEED = 5


def cp(k, n, alpha=0.05):
    """Clopper-Pearson's exact interval for k of n: (lo, hi). With k = 0 the upper limit is 1 - (alpha/2)^(1/n): no false
    alarm in four bounds the rate only under 60 % (the biology survey's B28)."""
    from scipy.stats import beta
    if n == 0:
        return (0.0, 1.0)
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def upper(k, n, conf=0.95):
    """The exact one-sided upper bound on a rate seen k times in n (Clopper-Pearson): zero in n bounds it under
    1 - (1 - conf)^(1/n) -- 1.04 % for none in 286, so no count on about 300 tracks can show "under 1 %"."""
    from scipy.stats import beta
    return 1.0 if k >= n else float(beta.ppf(conf, k + 1, n - k))


def by_clip(rows, hit, runs=BOOT, seed=SEED):
    """The share of rows with `hit`, with a 95 % interval from resampling clips: (share, lo, hi, clips)."""
    g = defaultdict(lambda: [0, 0])
    for r in rows:
        g[r["clip"]][0] += 1
        g[r["clip"]][1] += bool(hit(r))
    a = np.array(list(g.values()), float)
    if not len(a):
        return None, None, None, 0
    rng = np.random.default_rng(seed)
    s = a[rng.integers(0, len(a), (runs, len(a)))]
    share = s[..., 1].sum(1) / s[..., 0].sum(1)
    lo, hi = np.percentile(share, [2.5, 97.5])
    return float(a[:, 1].sum() / a[:, 0].sum()), float(lo), float(hi), len(a)


def kappa(a, b):
    """Cohen's kappa of two raters' labels over the same items: (raw agreement, chance agreement, kappa)."""
    n = len(a)
    if not n:
        return None, None, None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / n ** 2
    return po, pe, (po - pe) / (1 - pe) if pe < 1 else 1.0


def auc(pos, neg):
    """The area under the ROC curve of a score that should be higher on `pos` (Mann-Whitney, ties counted half)."""
    if not pos or not neg:
        return None
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    return float(((pos[:, None] > neg[None, :]).sum() + 0.5 * (pos[:, None] == neg[None, :]).sum()) / (len(pos) * len(neg)))


def call(rec):
    """A measurement's call as the run of 2026-10-19 read it, and the values the table keeps."""
    if rec is None:
        return dict(call="missing")
    if rec.get("error"):
        return dict(call="error", why=rec["error"][:160])
    ff = rec.get("fields") or {}
    beat = (ff.get("beat") or {}).get("object") or {}
    an = (ff.get("analytic") or {}).get("object") or {}
    pic = ff.get("pictures") or {}
    out = dict(hz=beat.get("hz"), hz_err=beat.get("hz_err"), amplitude=beat.get("amplitude"), comes_back=beat.get("comes_back"),
               shaken_px=(beat.get("shaken") or {}).get("px"), needs=an.get("with_floor"), top_hz=pic.get("top_hz"),
               pictures=pic.get("rate"), held=pic.get("held"), cadence=pic.get("cadence"),
               continuum_p=((ff.get("continuum") or {}).get("object") or {}).get("p"),
               train=int(bool(((ff.get("blink") or {}).get("object") or {}).get("train"))),
               named=int(any(not b.get("shaken") for b in report.bird_beats(ff).values())))
    if ff.get("beats") is None:                          # NO POWER, as the run of 2026-10-19 read it
        return dict(out, call="refused", why=str((rec.get("no_power") or [["", ""]])[0][1])[:160])
    strong = ff.get("strong")
    if not (ff.get("beats") and (strong is None or "object" in strong)):
        out["call"] = "none"
    elif not report.WINGBEAT_HZ[0] <= (beat.get("hz") or 0) <= report.WINGBEAT_HZ[1]:
        out["call"] = "other"
    else:
        out["call"] = "bird" if beat.get("comes_back", True) else "once"
    return out


def read(path):
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def rejudged(d):
    """A track's calls judged again from its saved curves with the code as it stands (`run_set.replay`): {rule: call}."""
    from run_set import read_gz, replay
    path = Path(d) / "curves.json.gz"
    if not path.exists():
        return str(d), None
    saved, out = read_gz(path), {}
    for rule in RULES:
        try:
            found = replay(saved, rule)
            out[rule] = call(dict(fields=found.fields, no_power=found.no_power))
        except Exception as e:                  # said in the table, as a measurement's error is
            out[rule] = dict(call="error", why=f"{type(e).__name__}: {e}"[:160])
    return str(d), out


def table(runs, index_rows, again=None):
    """One row per track. `again`, where given, is {folder: {rule: call}} judged again from the saved curves (`rejudged`),
    read in place of the measurement's own."""
    rows = []
    for j in index_rows:
        d = Path(runs) / f"{j['clip']}_{j['object']}"
        row = {k: j[k] for k in ("clip", "object", "cls", "distance", "objects", "labelled", "first", "last", "w_med", "h_med", "dark")}
        rep = {}
        if (d / "replay.json").exists():
            rep = json.loads((d / "replay.json").read_text())
        for rule in RULES:
            c = ((again.get(str(d)) or {}).get(rule) or dict(call="missing")) if again is not None else call(read(d / f"{rule}.json.gz"))
            for k in ("call", "named", "hz", "hz_err", "amplitude", "comes_back", "shaken_px", "needs", "top_hz", "pictures", "held",
                      "cadence", "continuum_p", "train", "why"):
                v = c.get(k)
                row[f"{rule}_{k}"] = "" if v is None else (f"{v:.6g}" if isinstance(v, float) else v)
            row[f"{rule}_replay"] = "" if rule not in rep else int(bool(rep[rule].get("same")))
        got = read(d / "curves.json.gz")
        row.update({k: ("" if v is None else v) for k, v in (offers(got) if got else
                                                             dict(frames_measured=None, fps=None, contrast_gl=None, extent_px=None)).items()})
        row["curves"] = str(d / "curves.json.gz") if (d / "curves.json.gz").exists() else ""
        rows.append(row)
    return rows


def pct(x):
    return "--" if x is None else f"{100 * x:.1f}"


def rates(rows):
    """The rates of record: {rule: {what: {k, n, share, cp: [lo, hi], clips: [lo, hi], n_clips}}}."""
    done = [r for r in rows if r["stage_call"] not in ("missing", "") and r["paper_call"] not in ("missing", "")]
    out = {"tracks": len(done), "of": len(rows)}
    for rule in RULES:
        R = {}
        groups = [(c, [r for r in done if r["cls"] == c]) for c in CLASSES]
        groups += [("non-bird", [r for r in done if r["cls"] != "BIRD"])]
        groups += [(f"{c} {b}", [r for r in done if r["cls"] == c and r["distance"] == b]) for c in CLASSES for b in BINS]
        groups += [(f"non-bird {b}", [r for r in done if r["cls"] != "BIRD" and r["distance"] == b]) for b in BINS]
        for name, g in groups:
            for what, hit in (("bird", lambda r: r[f"{rule}_call"] == "bird"), ("named", lambda r: str(r[f"{rule}_named"]) == "1"),
                              ("refused", lambda r: r[f"{rule}_call"] in ("refused", "error")),
                              ("answered", lambda r: r[f"{rule}_call"] not in ("refused", "error"))):
                k = sum(bool(hit(r)) for r in g)
                s, lo, hi, nc = by_clip(g, hit)
                R[f"{name}: {what}"] = dict(k=k, n=len(g), share=(k / len(g) if g else None), cp=list(cp(k, len(g))),
                                            upper=upper(k, len(g)) if g else None, clips=[lo, hi], n_clips=nc)
        # refusals are not neutral (the diagnostic-accuracy survey, 2026-11-07): how much likelier a refusal is on a bird
        # than on anything else, P(refused | bird) / P(refused | non-bird), with an interval from resampling clips in each
        b = [r for r in done if r["cls"] == "BIRD"]
        nb = [r for r in done if r["cls"] != "BIRD"]
        ref = lambda r: r[f"{rule}_call"] in ("refused", "error")
        if b and nb and sum(map(ref, nb)):
            lr = (sum(map(ref, b)) / len(b)) / (sum(map(ref, nb)) / len(nb))
            rng = np.random.default_rng(SEED)
            gb, gn = defaultdict(list), defaultdict(list)
            for r in b:
                gb[r["clip"]].append(ref(r))
            for r in nb:
                gn[r["clip"]].append(ref(r))
            A = np.array([(len(v), sum(v)) for v in gb.values()], float)
            B = np.array([(len(v), sum(v)) for v in gn.values()], float)
            sa, sb = A[rng.integers(0, len(A), (2000, len(A)))], B[rng.integers(0, len(B), (2000, len(B)))]
            with np.errstate(divide="ignore", invalid="ignore"):
                boot = (sa[..., 1].sum(1) / sa[..., 0].sum(1)) / (sb[..., 1].sum(1) / sb[..., 0].sum(1))
            boot = boot[np.isfinite(boot)]
            R["refusal ratio"] = dict(lr=lr, clips=[float(x) for x in np.percentile(boot, [2.5, 97.5])])
        else:
            R["refusal ratio"] = dict(lr=None, clips=[None, None])
        for name, cls in (("clips with a bird call", None),):
            for c in CLASSES:
                by = defaultdict(list)
                for r in done:
                    if r["cls"] == c:
                        by[r["clip"]].append(r)
                k = sum(any(r[f"{rule}_call"] == "bird" for r in g) for g in by.values())
                kn = sum(any(str(r[f"{rule}_named"]) == "1" for r in g) for g in by.values())
                R[f"{c}: clips with a bird call"] = dict(k=k, n=len(by), cp=list(cp(k, len(by))))
                R[f"{c}: clips named"] = dict(k=kn, n=len(by), cp=list(cp(kn, len(by))))
            by = defaultdict(list)
            for r in done:
                if r["cls"] != "BIRD":
                    by[r["clip"]].append(r)
            k = sum(any(r[f"{rule}_call"] == "bird" for r in g) for g in by.values())
            kn = sum(any(str(r[f"{rule}_named"]) == "1" for r in g) for g in by.values())
            R["non-bird: clips with a bird call"] = dict(k=k, n=len(by), cp=list(cp(k, len(by))))
            R["non-bird: clips named"] = dict(k=kn, n=len(by), cp=list(cp(kn, len(by))))
        calls = [r for r in done if r[f"{rule}_call"] in ("bird", "once") and r[f"{rule}_amplitude"] != ""]   # as on 2026-10-19
        R["amplitude AUC"] = auc([float(r[f"{rule}_amplitude"]) for r in calls if r["cls"] == "BIRD"],
                                 [float(r[f"{rule}_amplitude"]) for r in calls if r["cls"] != "BIRD"])
        has = [r for r in done if r[f"{rule}_amplitude"] != ""]          # every track with a measured amplitude, called or not
        R["amplitude AUC, measured"] = auc([float(r[f"{rule}_amplitude"]) for r in has if r["cls"] == "BIRD"],
                                           [float(r[f"{rule}_amplitude"]) for r in has if r["cls"] != "BIRD"])
        quiet = [r for r in has if r[f"{rule}_call"] == "none"]             # ... and those with no beat of their own at all
        R["amplitude AUC, no beat"] = auc([float(r[f"{rule}_amplitude"]) for r in quiet if r["cls"] == "BIRD"],
                                          [float(r[f"{rule}_amplitude"]) for r in quiet if r["cls"] != "BIRD"])
        R["replayed the same"] = [sum(str(r[f"{rule}_replay"]) == "1" for r in done), sum(r[f"{rule}_replay"] != "" for r in done)]
        out[rule] = R
    # by stratum of what the clip offers: the share of birds named (one minus the miss rate) and of non-birds named (the
    # false-alarm rate), each with its exact interval, or only its count where the stratum holds under STRATUM_MIN tracks
    for rule in RULES:
        S = {}
        for dim, (col, bins) in STRATA.items():
            for lab in [b[0] for b in bins] + ["not read"]:
                for who, sel in (("birds", lambda r: r["cls"] == "BIRD"), ("non-birds", lambda r: r["cls"] != "BIRD")):
                    g = [r for r in done if sel(r) and stratum(dim, r.get(col)) == lab]
                    k = sum(str(r[f"{rule}_named"]) == "1" for r in g)
                    S[f"{dim}: {lab}: {who}"] = dict(k=k, n=len(g), share=(k / len(g) if len(g) >= STRATUM_MIN else None),
                                                      cp=list(cp(k, len(g))) if len(g) >= STRATUM_MIN else None,
                                                      upper=upper(k, len(g)) if len(g) >= STRATUM_MIN else None,
                                                      answered=sum(r[f"{rule}_call"] not in ("refused", "error") for r in g),
                                                      too_few=len(g) < STRATUM_MIN)
        out[rule]["strata"] = S
    # the two rules as two raters on one set of tracks (the biology survey's X6): a bird call or not, as X6 read it, and the
    # five calls; and the report's name today
    for key, lab in (("agreement", lambda r, rule: r[f"{rule}_call"] == "bird"),
                     ("agreement, five calls", lambda r, rule: r[f"{rule}_call"] if r[f"{rule}_call"] in ("bird", "once", "none", "refused")
                      else "other"),
                     ("agreement, named", lambda r, rule: str(r[f"{rule}_named"]) == "1")):
        a_, b_ = [lab(r, "stage") for r in done], [lab(r, "paper") for r in done]
        po, pe, k = kappa(a_, b_)
        both = sum(x is True and y is True for x, y in zip(a_, b_))     # positive agreement, for the yes-or-no readings
        one = sum((x is True) != (y is True) for x, y in zip(a_, b_))
        out[key] = dict(raw=po, chance=pe, kappa=k, positive=(2 * both / (2 * both + one) if both + one else None)
                        if isinstance(a_[0], bool) else None)
    return out


def show(rows, R):
    done = [r for r in rows if r["stage_call"] not in ("missing", "") and r["paper_call"] not in ("missing", "")]
    print(f"{R['tracks']} of {R['of']} tracks measured under both rules\n")
    for rule in RULES:
        print(f"== {rule} rule: calls per track (the 2026-10-19 reading), and 'Beats like a bird' as the report says it today")
        print(f"{'class':<11}{'bin':<9}{'n':>4}" + "".join(f"{c:>8}" for c in CALLS) + f"{'bird %':>8}{'named':>7}{'named %':>9}")
        for cls in CLASSES:
            for b in BINS + ("all",):
                g = [r for r in done if r["cls"] == cls and (b == "all" or r["distance"] == b)]
                if not g:
                    continue
                n = Counter(r[f"{rule}_call"] for r in g)
                nm = sum(str(r[f"{rule}_named"]) == "1" for r in g)
                print(f"{cls:<11}{b:<9}{len(g):>4}" + "".join(f"{n[c]:>8}" for c in CALLS)
                      + f"{100 * n['bird'] / len(g):>7.1f}%{nm:>7}{100 * nm / len(g):>8.1f}%")
        g = [r for r in done if r["cls"] != "BIRD"]
        n = Counter(r[f"{rule}_call"] for r in g)
        nm = sum(str(r[f"{rule}_named"]) == "1" for r in g)
        if g:
            print(f"{'non-bird':<11}{'all':<9}{len(g):>4}" + "".join(f"{n[c]:>8}" for c in CALLS)
                  + f"{100 * n['bird'] / len(g):>7.1f}%{nm:>7}{100 * nm / len(g):>8.1f}%")
        Q = R[rule]
        print("\n  rates of record (exact 95 % over tracks; 95 % resampling clips):")
        for key in ("BIRD: bird", "BIRD: named", "non-bird: bird", "non-bird: named", "AIRPLANE: bird", "DRONE: bird",
                    "HELICOPTER: bird", "AIRPLANE: named", "DRONE: named", "HELICOPTER: named", "non-bird DISTANT: bird",
                    "non-bird DISTANT: named", "BIRD DISTANT: bird", "BIRD DISTANT: named"):
            q = Q.get(key)
            if q and q["n"]:
                print(f"    {key:<26} {q['k']:>3}/{q['n']:<4} {pct(q['share']):>5} %  exact {pct(q['cp'][0])}-{pct(q['cp'][1])}"
                      f"  by clip {pct(q['clips'][0])}-{pct(q['clips'][1])} ({q['n_clips']} clips)")
        print("  coverage, the share answered (not NO POWER), by class -- beside every rate, never pooled over classes alone:")
        for c in CLASSES + ("non-bird",):
            q = Q[f"{c}: answered"]
            print(f"    {c:<11} {q['k']:>3}/{q['n']:<4} {pct(q['share'])} % answered (exact {pct(q['cp'][0])}-{pct(q['cp'][1])})")
        rr = Q["refusal ratio"]
        if rr["lr"] is not None:
            print(f"    a refusal is {rr['lr']:.1f} times as likely on a bird as on anything else (by clip {rr['clips'][0]:.1f}-"
                  f"{rr['clips'][1]:.1f})" + ("; the interval holds 1" if rr["clips"][0] <= 1 <= rr["clips"][1] else ""))
        print("  false alarms, each a point estimate with its exact one-sided 95 % upper bound:")
        for key in ("non-bird: named", "AIRPLANE: named", "DRONE: named", "HELICOPTER: named", "non-bird DISTANT: named"):
            q = Q[key]
            if q["n"]:
                print(f"    {key:<26} {q['k']}/{q['n']} = {pct(q['share'])} %, under {pct(q['upper'])} %")
        for key in ("non-bird: clips with a bird call", "non-bird: clips named"):
            q = Q[key]
            print(f"    {key:<34} {q['k']}/{q['n']}  exact {pct(q['cp'][0])}-{pct(q['cp'][1])}")
        print(f"    among the calls only (bird and once), the beat's amplitude separating birds' calls from false ones: AUC {Q['amplitude AUC'] if Q['amplitude AUC'] is None else round(Q['amplitude AUC'], 3)}")
        print(f"    the same over every track with a measured amplitude: AUC {Q['amplitude AUC, measured']:.3f}; among those with no "
              f"beat of their own: {Q['amplitude AUC, no beat']:.3f} (most of the separation is the birds' faintness, not their beat)")
        print(f"    saved curves replayed to the same call: {Q['replayed the same'][0]} of {Q['replayed the same'][1]}")
        hz = sorted(float(r[f"{rule}_hz"]) for r in done if r["cls"] == "BIRD" and r[f"{rule}_call"] == "bird")
        if hz:
            print(f"    bird tracks called birds beat at {hz[0]:.2f}-{hz[-1]:.2f} Hz, median {hz[len(hz) // 2]:.2f}")
        fa = [(r["clip"], r["object"], round(float(r[f"{rule}_hz"]), 2), round(100 * float(r[f"{rule}_amplitude"]), 1))
              for r in done if r["cls"] != "BIRD" and r[f"{rule}_call"] == "bird"]
        print(f"    non-birds called birds (clip, object, Hz, %): {fa}")
        print("    by what the clip offers -- birds named (one minus the miss rate), non-birds named (the false-alarm rate):")
        for dim, (col, bins) in STRATA.items():
            for lab in [b[0] for b in bins] + ["not read"]:
                if not any(Q["strata"][f"{dim}: {lab}: {who}"]["n"] for who in ("birds", "non-birds")):
                    if lab == "not read":
                        continue
                cells = []
                for who in ("birds", "non-birds"):
                    q = Q["strata"][f"{dim}: {lab}: {who}"]
                    cells.append(f"{who} {q['k']}/{q['n']}" + (" (too few to state a rate)" if q["too_few"] else
                                 f" {pct(q['share'])} % ({pct(q['cp'][0])}-{pct(q['cp'][1])}"
                                 + (f"; under {pct(q['upper'])} %" if who == "non-birds" else "") + ")")
                                 + f", {q['answered']} answered")
                print(f"      {dim:<10} {lab:<22} " + "; ".join(cells))
        top = Counter(r[f"{rule}_top_hz"] for r in done)
        print(f"    the band's top: {dict(top.most_common(4))}\n")
    for key, what in (("agreement", "a bird call or not"), ("agreement, five calls", "bird / once / other / none / refused"),
                      ("agreement, named", "named or not")):
        a = R[key]
        if a["kappa"] is not None:
            print(f"stage against paper ({what}): raw {pct(a['raw'])} %, chance {pct(a['chance'])} %, kappa {a['kappa']:.2f}"
                  + (f", positive agreement {pct(a['positive'])} %" if a.get("positive") is not None else ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("runs")
    ap.add_argument("--index", help="the track index (default: the reference-data folder's svanstrom2021/tracks/index.tsv)")
    ap.add_argument("--out", help="the table (default: RUNS/../svanstrom_tracks.csv)")
    ap.add_argument("--json", help="write the rates of record here")
    ap.add_argument("--rejudge", action="store_true",
                    help="judge every track again from its saved curves with the code as it stands, no video (after a change "
                         "to the judging: a gate, a floor, a rule), and tabulate that")
    ap.add_argument("--procs", type=int, default=1, help="worker processes for --rejudge")
    a = ap.parse_args(argv)
    from run_set import index
    again = None
    if a.rejudge:
        from multiprocessing import Pool
        dirs = [str(Path(a.runs) / f"{j['clip']}_{j['object']}") for j in index(a.index)]
        with Pool(a.procs) as pool:
            again = dict(pool.map(rejudged, dirs, chunksize=4))
    rows = table(a.runs, index(a.index), again)
    out = Path(a.out or Path(a.runs).parent / "svanstrom_tracks.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    R = rates(rows)
    show(rows, R)
    if a.json:
        Path(a.json).write_text(json.dumps(R, indent=1))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
