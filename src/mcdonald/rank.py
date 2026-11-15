"""`mcdonald rank` -- every object of a batch on the same axes; the record's defects first; then each object held against
each labelled control class, as a tail probability within its stratum of quality. A list for a person, never a verdict.

ROADMAP.md 0.6, objective 5 ("Anomaly ranking over the pass"), as the ideas bank sharpens it: P9, anomaly ranking as
model criticism -- a tail probability under each control population, never a score for "anomaly"; Av14, the ranking
says which measure flagged each object; D9, conformal p-values per control class within strata of release and quality,
since unsupervised scores track data quality. docs/method.md section 64 is the method; tests/test_rank.py holds it on
drawn populations.

    mcdonald rank BATCH_DIR --out DIR                       # the defects, the axes and the list
    mcdonald rank BATCH_DIR --controls CONTROLS.tsv --out DIR
    mcdonald rank BATCH_DIR --out DIR --json                # the envelope: the tally, the list's head, the files

Why a module of its own, and not part of `batch`: `batch` makes a corpus and `rank` reads one. The ranking needs a
finished table and the controls' table, and nothing in a batch's units depends on it, so it sits apart, as `several`
sits apart from `run`; batch.py's unit runner and scheduler are left as they are. The name is the command's.

**The order, which is the point (D9).**

1. *Rows to objects* (`objects`). A batch row is a spot that lasted, not an object. A row followed onto another row's
   track (`same_as`: `several.same_things`, the package's rule, two tracks within 2 px on half their shared frames) is
   folded into the row it is counted through. A group (`groups` found several points moving together) is one row
   whose members were measured inside it; it stays one object of the kind "group".
2. *Defects first* (`defects`): a row with no track, a stage that failed, an object the integrity tests find unlike the
   camera's own picture or part of the overlay, a track that lies on the display's overlay or a redaction block (the
   package's static masks, with `--masks`), a group whose brightness was read as one blend, a spot that is part of the
   scene or fixed on the sensor, a track with no compact spot under it on most of its frames, a beat refused for held
   pictures. Each by a test the package already has, with the line stated in `RULES`. A defect is listed with its
   reason and never ranked.
3. *The axes* (`AXES`): every measurement every object has, in fixed units; missing is missing, never zero. The axes
   that depend on the sensor's angular scale or on the camera's motion (rates in pixels, the path on the screen) are
   shown and kept out of the class score; the score uses the scale-free ones the controls measure the same way.
4. *Model criticism* (`pvalues`). For each control class (the labelled infrared set's birds, drones, airplanes and
   helicopters; whatever else the controls table holds), a conformal p-value: the share of that class's objects in the
   object's quality stratum (`stratum`) whose score is at least the object's, the score being the largest robust
   distance from the class's middle over the axes both have (`score`). The axis that gave the largest distance is the
   measure that drove it (Av14). A class with fewer than `MIN_CLASS` objects in the stratum, or an object outside the
   class's range of quality, has NO POWER (E5): no p-value, and the reason why.
5. *The list* (`ranked`): the objects that are not defects, by the largest p-value over the classes that had power (the
   class the object is least unlike); ties by how far outside that class it lies. Beside it the corpus summary: how many
   objects are unlike every class with power at a stated level, after Benjamini-Hochberg and Benjamini-Yekutieli over
   the objects, and the share with an interval from a bootstrap over videos (E10: one video's objects are not
   independent).

Nothing here is named anomalous. A small p-value says "unlike these labelled tracks, by this measure", never "unlike
birds": a control class's population is not the sky's.
"""
import argparse
import csv
import gzip
import json
import math
import sys
from pathlib import Path

import numpy as np

from . import __version__

FORMAT = "mcdonald-rank/1"
MIN_CLASS = 19          # a class's objects in a stratum for a p-value of 0.05 to be possible at all: 1/(n+1) <= 0.05
LEVEL = 0.05            # the level the corpus summary counts at (and 0.10 beside it)
MAD_K = 1.4826          # a normal's standard deviation from its median absolute deviation
MASKED_SHARE = 0.25     # a track on the static masks (overlay, redaction) on this share of its frames or more is a defect
                        # (RULES' "masked"; judgement, stated: a track that slides onto a symbol for a quarter of its
                        # frames carries the symbol's steady brightness into every axis read over the track)
WEAK_SHARE = 0.5        # a track with no compact spot under it on more than this share of its frames is a defect
                        # (RULES' "lost"; the track sheet's own test of a frame; the half is judgement, stated)
BOOT = 2000             # draws of the bootstrap over videos
LINE_P = 0.05           # a line's frequency is an axis only where flicker's continuum null gives it p at most this


# ---- small readers ---------------------------------------------------------------------------------------------------
def read_json(path):
    path = Path(path)
    if not path.exists():
        return None
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    tmp = path.with_name(path.name + ".part")
    with opener(tmp, "wt", encoding="utf-8") as f:
        json.dump(obj, f, indent=None if path.suffix == ".gz" else 1, default=_plain)
    tmp.replace(path)


def _plain(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, Path):
        return str(x)
    raise TypeError(type(x))


def g(d, *path, default=None):
    """d[path[0]][path[1]]..., or `default` where any step is missing."""
    for p in path:
        if isinstance(d, dict) and p in d:
            d = d[p]
        elif isinstance(d, list) and isinstance(p, int) and -len(d) <= p < len(d):
            d = d[p]
        else:
            return default
    return d


def num(x):
    """A finite float, or None."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def mad(a):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    if a.size < 3:
        return None
    return float(MAD_K * np.median(np.abs(a - np.median(a))))


# ---- 1. reading a batch: a record for each row with an object ----------------------------------------------------------
def batch_rows(folder):
    """(the table's head, its rows that are objects) from a batch folder's `batch.json`."""
    folder = Path(folder)
    t = read_json(folder / "batch.json")
    if t is None:
        raise FileNotFoundError(f"{folder}: no batch.json (write it with `mcdonald batch --out {folder} --table`)")
    head = {k: v for k, v in t.items() if k != "rows"}
    return head, [r for r in t.get("rows") or [] if r.get("object") not in (None, "")]


def case_json(folder, row):
    d = Path(folder) / (row.get("object_folder") or f"{row['folder']}/object-{row['object']}")
    return next(iter(sorted(d.glob("*_case.json"))), None), d


def curve_stats(csv_path):
    """What the object's brightness curve and its background apertures say, from `<tag>_flicker.csv`: the object's
    robust spread over its median brightness (`light_var`), its frame-to-frame spread over its median (`light_fast`),
    and that frame-to-frame spread over the background apertures' own (`light_over_bg`). The object's column is
    `object`; a group's members are `member N` columns, and the one with most readings stands for it."""
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(ln for ln in f if not ln.startswith("#")))
    except OSError:
        return {}
    if len(rows) < 4:
        return {}
    head, body = rows[0], rows[1:]
    col = lambda i: np.array([num(r[i]) if i < len(r) and r[i] != "" else np.nan for r in body], float)
    fr = col(head.index("frame")) if "frame" in head else np.arange(len(body), dtype=float)
    cand = [i for i, h in enumerate(head) if h == "object"] or \
           [i for i, h in enumerate(head) if h.startswith("member ") and " " not in h[7:]]
    if not cand:
        return {}
    obj_i = max(cand, key=lambda i: np.isfinite(col(i)).sum())
    o = col(obj_i)
    bgs = [col(i) for i, h in enumerate(head) if h.startswith("background ") and "light" not in h]

    def fast(a):                                   # the spread of a step between consecutive frames, both read
        ok = np.isfinite(a[1:]) & np.isfinite(a[:-1]) & (np.diff(fr) == 1)
        d = (a[1:] - a[:-1])[ok]
        m = mad(d)
        return None if m is None else m / math.sqrt(2)

    ok = np.isfinite(o)
    out = dict(curve_frames=int(ok.sum()), curve_lost=float(1 - ok.mean()) if len(o) else None)
    if ok.sum() < 20:
        return out
    med = float(np.median(o[ok]))
    of = fast(o)
    bf = [x for x in (fast(b) for b in bgs) if x]
    out.update(light_median=med,
               light_var=(mad(o) / abs(med)) if med and mad(o) is not None else None,
               light_fast=(of / abs(med)) if med and of is not None else None,
               light_over_bg=(of / float(np.median(bf))) if of is not None and bf and np.median(bf) > 0 else None,
               bg_apertures=len(bf))
    return out


def _strongest(beats, continuum):
    """The object's strongest line (`flicker`'s `beat` field keeps it whether or not it is called a beat): the
    object's own where there is one, else the member whose line stands highest over its slow wander."""
    if not beats:
        return None, None
    if "object" in beats:
        return beats["object"], (continuum or {}).get("object")
    k = max(beats, key=lambda k: num(g(continuum, k, "ratio")) or num(g(beats, k, "stands")) or 0)
    return beats[k], (continuum or {}).get(k)


def extract(row, folder):
    """One row's record: the batch row's own columns, and from its case the fields the axes and the defects read.
    Kept small and flat, so that the axes, the rules and the ranking can be made again in seconds from the records."""
    js, d = case_json(folder, row)
    rec = dict(row=row, folder=str(d), case=str(js) if js else None, video=None)
    if js is None:
        return rec
    try:
        c = read_json(js)
    except (OSError, ValueError) as e:
        rec["read_error"] = f"{type(e).__name__}: {e}"
        return rec
    S = c.get("stages") or {}
    st = lambda n: g(S, n, "fields") or {}
    npw = {n: [list(x) for x in (s.get("no_power") or [])] for n, s in S.items() if s.get("no_power")}
    sv, vr, ly, kn, cm, gr, fl, te = (st(n) for n in ("survey", "verify", "layers", "kinematics", "camera", "groups",
                                                        "flicker", "tether"))
    line, cont = _strongest(fl.get("beat"), fl.get("continuum"))
    clip = c.get("clip") or {}
    rec.update(
        video=c.get("video"), stages=sorted(S), no_power=npw,
        clip=dict(width=clip.get("width"), height=clip.get("height"), fps=num(clip.get("fps")), n0=clip.get("n0"),
                  n1=clip.get("n1"), bit_rate=num(g(clip, "encoding", "bit_rate"))),
        survey=dict(repeated=sv.get("repeated_frames"),
                    transients=len(sv["transients"]) if isinstance(sv.get("transients"), list) else sv.get("transients"),
                    graphics=num(g(sv, "masked_share", "graphics"))),
        verify=dict(frames=vr.get("frames"), detected=vr.get("detected"), interpolated=vr.get("interpolated"),
                    outside=vr.get("outside_every_track"), contrast=num(g(vr, "contrast_dn", "median")),
                    weak=len(vr["weak_frames"]) if isinstance(vr.get("weak_frames"), list) else vr.get("weak_frames"),
                    contrast_min=num(g(vr, "contrast_dn", "minimum"))),
        integrity=g(S, "integrity", "result", "object_verdicts") or {},
        layers=dict(all=g(ly, "over_track", "all"), all_any=g(ly, "px_per_s", "all"), held=ly.get("held_still"),
                    shift_err=g(ly, "shift_error_px", "median"), shift_over=g(ly, "shift_error_px", "over_frames"),
                    scene_speed=num(g(ly, "scene", "speed_px_frame", "median")),
                    scene_read=g(ly, "scene", "read")),
        kinematics=dict(v=num(kn.get("v_px_per_s")), resid_frac=num(g(kn, "fit", "resid_frac")),
                        span=num(g(kn, "fit", "span_px")), noise=num(g(kn, "fit", "noise_px")),
                        sagitta=num(g(kn, "turn", "sagitta_px")), length=num(g(kn, "turn", "length_px")),
                        bent=g(kn, "turn", "bent"), turned=g(kn, "turn", "turned"),
                        r_turn=num(g(kn, "turn", "r_turn_over_D")), breaks=g(kn, "breaks", "found"),
                        width=num(g(kn, "width_px", "px")), smear=num(kn.get("smear")),
                        body_lengths=num(kn.get("body_lengths_per_s"))),
        camera=dict(size_kind=g(cm, "size_trend", "kind"), size_ratio=num(g(cm, "size_trend", "ratio")),
                    zooms=len([z for z in cm.get("zoom_steps") or [] if z.get("applied", True)]),
                    jumps=len([b for b in cm.get("breaks") or [] if b.get("jump")]),
                    events=len(cm.get("events") or [])),
        groups=dict(several=gr.get("several"), points=num(g(gr, "points_per_frame", "median")),
                    members=gr.get("members_followed"), on_sensor=gr.get("on_the_sensor"), rigid=gr.get("rigid"),
                    finding=gr.get("finding")),
        flicker=dict(frames=fl.get("frames"), extent=num(g(fl, "extent_px", "object")),
                     held=num(g(fl, "pictures", "held")), top_hz=num(fl.get("top_hz")),
                     blend="object" in (fl.get("beat") or {}) and bool(gr.get("several")),
                     members=sorted(k for k in (fl.get("beat") or {}) if k != "object"),
                     hz=num((line or {}).get("hz")), amp=num((line or {}).get("amplitude")),
                     stands=num((cont or {}).get("ratio")), needed95=num((cont or {}).get("needed95")),
                     cont_p=num((cont or {}).get("p")), comes_back=(line or {}).get("comes_back"),
                     rotor=num(g(line, "rotor", "coherence")), lookalike=len((line or {}).get("lookalike") or []),
                     train=bool(g(fl, "blink", "object", "curves", "brightness", "train"))),
        tether=dict(companion=bool(te.get("companion")), finding=te.get("finding")),
    )
    tag = js.name[:-len("_case.json")]
    rec["curves"] = curve_stats(js.with_name(f"{tag}_flicker.csv"))
    rec["track"] = track_stats(js.with_name(f"{tag}_autotrack.csv"))
    return rec


def track_stats(path):
    """The followed track's frames and the share of them within 1 px of its median position on the screen
    (`forensics.on_the_sensor`'s test of a spot fixed on the sensor, turned on the object's own track)."""
    from .forensics import read_track
    try:
        t = read_track(path) if Path(path).exists() else {}
    except (OSError, ValueError, KeyError, StopIteration):
        t = {}
    if not t:
        return {}
    xy = np.array(list(t.values()), float)
    m = np.median(xy, axis=0)
    return dict(n=len(t), first=min(t), last=max(t), fixed_share=float(np.mean(np.hypot(*(xy - m).T) <= 1.0)))


def records(folder, say=None):
    """Every object row of a batch folder as a record (`extract`), in the table's order."""
    head, rows = batch_rows(folder)
    out = []
    for i, r in enumerate(rows):
        out.append(extract(r, folder))
        if say and (i + 1) % 100 == 0:
            say(f"  read {i + 1} of {len(rows)} objects")
    return head, out


class _Grabbed:
    """What `forensics.static_masks` reads of a clip -- its window, its size and `rgb(n)` -- for frames grabbed in one
    pass of ffmpeg, through the package's own way to a picture (`clip.every_frame`, PNG, `clip._load`), so that the
    masks are made from the same levels as in the case."""

    def __init__(self, n0, n1, W, H, paths):
        self.n0, self.n1, self.W, self.H, self.paths = n0, n1, W, H, paths

    def rgb(self, n):
        from .clip import _load
        return _load(str(self.paths[int(n)]))


def _even(n0, n1, n_sample):
    """About `n_sample` frames of n0..n1 on an exact step, so that static_masks' own linspace over them gives them back."""
    k = max(1, (n1 - n0) // (n_sample - 1))
    m = min(n_sample, (n1 - n0) // k + 1)
    return n0, k, m


def masks_of_video(video, recs, workdir, n_sample=40):
    """For each record of one video, the share of its track's frames on the static masks of its case's clip (the
    graphics, burned-in symbology, or the blocks, redaction): sets rec["masks"] = dict(share, frames, graphics, blocks).
    Each case's clip is sampled on an exact step (about 40 frames, evenly spaced, as static_masks takes them), and every
    case of the video is read in one pass of ffmpeg, a short select expression a case (a sum of a hundred terms or more
    is refused by ffmpeg's parser)."""
    import subprocess
    from .clip import every_frame
    from .forensics import static_masks
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    want, terms = set(), []
    for r in recs:
        n0, n1 = g(r, "clip", "n0"), g(r, "clip", "n1")
        if n0 and n1 and n1 > n0:
            a, k, m = _even(int(n0), int(n1), n_sample)
            r["_ns"] = [a + k * i for i in range(m)]
            want.update(r["_ns"])
            terms.append(f"between(n,{a - 1},{a - 1 + k * (m - 1)})*not(mod(n-{a - 1},{k}))")
    if not want:
        return
    ns = sorted(want)
    paths = {}
    sub = workdir / "g"
    sub.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", "select='" + "+".join(terms) + "'", *every_frame(),
                    str(sub / "g%05d.png")], check=True)
    got = sorted(sub.glob("g*.png"))
    if len(got) != len(ns):                                   # a frame past the video's end: keep only what is sure
        got = got[:min(len(got), len(ns))]
    paths.update({n: p for n, p in zip(ns, got)})
    for r in recs:
        if not r.get("_ns"):
            continue
        ok = [n for n in r.pop("_ns") if n in paths]
        if len(ok) < 3:
            continue
        W, H = g(r, "clip", "width"), g(r, "clip", "height")
        m = static_masks(_Grabbed(min(ok), max(ok), W, H, paths), n_sample=len(ok))
        gr, bl = m["graphics"], m["blocks"]
        tk = track_of(r)
        on_g = on_b = on = n = 0
        for x, y in tk.values():
            xi, yi = int(round(x)), int(round(y))
            if 0 <= yi < gr.shape[0] and 0 <= xi < gr.shape[1]:
                n += 1
                a, b = bool(gr[yi, xi]), bool(bl[yi, xi])
                on_g, on_b, on = on_g + a, on_b + b, on + (a or b)
        r["masks"] = dict(share=on / n if n else None, frames=n, graphics=on_g, blocks=on_b,
                          graphics_share=float(gr.mean()), blocks_share=float(bl.mean()), sampled=len(ok))
    for p in workdir.rglob("g*.png"):
        p.unlink()


def add_masks(recs, workdir, say=None):
    """`masks_of_video` for every video of the records (by the case's video file)."""
    by = {}
    for r in recs:
        if r.get("video") and r.get("case") and "masks" not in r:
            by.setdefault(r["video"], []).append(r)
    for i, (v, rs) in enumerate(sorted(by.items()), 1):
        if say:
            say(f"  the static masks of {Path(v).name} ({i} of {len(by)}, {len(rs)} objects)")
        try:
            masks_of_video(v, rs, Path(workdir) / f"v{i:04d}")
        except Exception as e:                                # noqa: BLE001 -- a video that cannot be read is said
            for r in rs:
                r["masks"] = dict(share=None, error=f"{type(e).__name__}: {e}")


# ---- 2. rows to objects ----------------------------------------------------------------------------------------------
def key_of(rec):
    r = rec["row"]
    return f"{r.get('unit') or r.get('folder')}#{r['object']}"


def objects(recs):
    """Rows to objects: a row followed onto another row's track (`same_as`, `several.same_things`) is folded into the
    row it is counted through, and lists it under `also`; every other row is an object. A group stays one object of
    the kind "group", its members measured inside its case. Returns the kept records, each with `key`, `kind` and
    `also`, in the table's order."""
    by = {key_of(r): r for r in recs}
    kept = []
    for r in recs:
        r["key"] = key_of(r)
        r.setdefault("also", [])
    for r in recs:
        s = r["row"].get("same_as")
        if s not in (None, ""):
            host = by.get(f"{r['row'].get('unit') or r['row'].get('folder')}#{s}")
            if host is not None and host is not r:
                host["also"].append(r["key"])
                r["folded_into"] = host["key"]
                continue
        kept.append(r)
    for r in kept:
        r["kind"] = kind_of(r)
    return kept


def kind_of(rec):
    """"group" where `groups` found several points moving together (the row's `several`), else "single"."""
    sev = rec["row"].get("several")
    return "group" if (sev is True or str(sev).lower() == "yes" or g(rec, "groups", "several") is True) else "single"


# ---- 3. the defects, before any ranking ------------------------------------------------------------------------------
RULES = {
    "not followed": "the link found no track from Find's marks, so nothing was measured (the report says \"No conclusion\")",
    "failed": "a stage stopped with an error, or the report could not be read",
    "added": "an integrity test flagged it: the object does not behave like the rest of the camera's picture "
             "(integrity's own verdict, FLAG on any test but the overlay's; the report's row \"added\" says Inconsistent)",
    "overlay": "integrity's layer-order test on the display's overlay flagged it: the object behaves like part of the "
               "overlay, not of the camera's picture",
    "masked": f"the track lies on the display's overlay or a redaction block (the package's static masks of its case's "
              f"clip, forensics.static_masks) on {MASKED_SHARE:.0%} of its frames or more",
    "blend": "a group whose brightness was read in one aperture over several points: its brightness is a blend",
    "sensor": "the object's own track sits within 1 px of one place on half its frames or more while the background "
              "moves across the picture: the package's test of a spot fixed on the sensor (forensics.on_the_sensor), "
              "which a camera locked on the object to within a pixel would also pass",
    "scene": "the report's own test says it does not move against the background (its rate there rounds to zero): "
             "a feature of the scene",
    "lost": f"the track sheet finds no compact spot under the track on over {WEAK_SHARE:.0%} of its frames "
            "(contrast under 25 grey levels): the track is not held on a spot",
    "held": "the brightness test refused because the pictures are held (too few new pictures to read a beat)",
    "looked": "someone looked at the track strip and found a record, not an object (--looked: the reason and who looked)",
}


RULE_WORDS = {  # each rule for the page a person reads (sciencespeak); RULES is the table's and the method's
    "not followed": "the computer could not follow it from the spots it found, so nothing was measured",
    "failed": "a step of the measurement stopped with an error",
    "added": "an integrity test found that it does not behave like the rest of the camera's picture",
    "overlay": "an integrity test found that it behaves like part of the overlay, the symbols and text drawn on the picture",
    "masked": "its track lies on the overlay or on a blacked-out block for a quarter of its frames or more",
    "blend": "a group whose brightness was read as one, so that its brightness mixes several objects",
    "sensor": "it stays within a pixel of one place on the screen for half its frames while the background moves",
    "scene": "it does not move against the background, so it is a feature of the scene",
    "lost": "on over half its frames, no clear spot lies under its track",
    "held": "the video repeats its pictures too often for a rhythm in its brightness to be read",
    "looked": "someone looked at its track and found a record, not an object, for the reason the table gives",
}


def defects(rec):
    """[(rule, why)] for one object's record, in RULES' order; empty where the record shows none. A look recorded with
    `--looked` comes last: the package's own tests are said first."""
    row, out = rec["row"], []
    if rec.get("looked"):
        lk = rec["looked"]
        found = defects({k: v for k, v in rec.items() if k != "looked"})
        return found + [("looked", f"a look by {lk.get('by') or 'someone'}: {lk.get('reason')}")]
    st = row.get("object_state")
    if st not in (None, "", "measured"):
        if st == "not followed":
            return [("not followed", RULES["not followed"])]
        return [("failed", f"{RULES['failed']} ({st}{': ' + str(row.get('error')) if row.get('error') else ''})")]
    if rec.get("case") is None or rec.get("read_error"):
        return [("failed", f"{RULES['failed']} ({rec.get('read_error') or 'no case file'})")]
    iv = rec.get("integrity") or {}
    flagged = lambda v: str(v).upper() in ("FLAG", "FAIL")
    if flagged(iv.get("layer order: symbology")):
        out.append(("overlay", RULES["overlay"]))
    ms = g(rec, "masks", "share")
    if ms is not None and ms >= MASKED_SHARE:
        out.append(("masked", f"{RULES['masked']} ({ms:.0%} of {g(rec, 'masks', 'frames')})"))
    bad = [k for k, v in iv.items() if flagged(v) and k != "layer order: symbology"]
    if bad:
        out.append(("added", f"{RULES['added']}: {', '.join(bad)}"))
    if g(rec, "flicker", "blend"):
        out.append(("blend", RULES["blend"]))
    if _on_sensor(rec):
        out.append(("sensor", f"{RULES['sensor']} ({g(rec, 'track', 'fixed_share'):.0%} of its frames)"))
    if (row.get("checklist") or {}).get("moves") == "No":
        out.append(("scene", RULES["scene"]))
    det, weak = g(rec, "verify", "detected"), g(rec, "verify", "weak")
    if det and weak is not None and weak > WEAK_SHARE * det:
        out.append(("lost", f"{RULES['lost']} ({weak} of {det})"))
    if any("held" in str(w).lower() or "pictures" in str(w).lower() for _, w in (rec.get("no_power") or {}).get("flicker", [])):
        out.append(("held", RULES["held"]))
    return out


def _on_sensor(rec):
    """`forensics.on_the_sensor`'s rule on the object's own track: within 1 px of one place on FIXED (half) of its
    frames or more. Only where the report's camera row says the background moved: where the scene held still its own
    points stay put too, and nothing here tells them apart (the rule's own caveat)."""
    from .forensics import FIXED
    if (rec["row"].get("checklist") or {}).get("camera") != "Yes":
        return False
    share = g(rec, "track", "fixed_share")
    return share is not None and share >= FIXED


# ---- 4. the axes -----------------------------------------------------------------------------------------------------
# (name, kind, unit, what it is, transform). kind: "score" enters the class score; "shown" is in the table but depends
# on the sensor's angular scale or on the camera's motion; "quality" makes the strata and E5's range.
AXES = [
    ("beat_amp", "score", "share of brightness", "the strongest line's amplitude in the brightness (flicker)", "log"),
    ("beat_hz", "score", "Hz", "the strongest line's frequency, where the line stands above the brightness's slow wander "
                               "(flicker's continuum null, p at most 0.05): a line that does not has no frequency of its own", "lin"),
    ("light_var", "score", "share of brightness", "the brightness's robust spread over its median", "log"),
    ("light_over_bg", "score", "times", "the brightness's frame-to-frame spread over the background apertures'", "log"),
    ("size_trend", "score", "ln ratio", "the size's change along the track, last over first (camera); missing where the "
                                        "camera found a zoom step inside the track, since a slow zoom stays in it", "lin"),
    ("rate_scene_w", "score", "widths a second", "the rate against the background in object widths a second", "log"),
    ("speed_spread", "score", "share", "the spread of the per-second rate against the background over its median", "log"),
    ("beat_stands", "shown", "times", "the strongest line over the brightness's slow wander (flicker's continuum)", "log"),
    ("light_fast", "shown", "share of brightness", "the brightness's frame-to-frame spread over its median", "log"),
    ("rate_scene", "shown", "px/s", "the rate against the background (layers)", "log"),
    ("rate_screen", "shown", "px/s", "the rate across the picture (kinematics)", "log"),
    ("rate_screen_w", "shown", "widths a second", "the rate across the picture in object widths a second", "log"),
    ("bend", "shown", "share", "how far the path bends: its sagitta over its length, on the screen", "log"),
    ("misfit", "shown", "share", "a straight line's miss over the track's span, on the screen", "log"),
    ("breaks", "shown", "0 or 1", "a sudden change of velocity found along the track (kinematics' break test)", "lin"),
    ("zooms", "shown", "count", "the camera's zoom steps inside the track (camera)", "lin"),
    ("held_still", "shown", "share", "the share of frame pairs in which the picture behind the object held still (layers)", "lin"),
    ("size_px", "quality", "px", "the object's width (flicker's extent, else the spot size followed)", "log"),
    ("contrast", "quality", "grey levels", "the object's contrast against its surround (verify)", "log"),
    ("frames", "quality", "frames", "frames followed", "log"),
    ("fps", "quality", "frames a second", "the video's frame rate", "lin"),
    ("held", "quality", "share", "the share of held pictures in the stretch (flicker)", "lin"),
]
AXIS = {a[0]: a for a in AXES}
SCORE = [a[0] for a in AXES if a[1] == "score"]
FLOOR = dict(beat_amp=1e-4, light_var=1e-4, light_over_bg=1e-3, rate_scene_w=1e-3, speed_spread=1e-3, beat_stands=1e-2,
             light_fast=1e-4, rate_scene=1e-2, rate_screen=1e-2, rate_screen_w=1e-3, bend=1e-4, misfit=1e-4,
             size_px=1.0, contrast=0.1, frames=1.0)


def axes_of(rec):
    """{axis: value or None} for one record (`AXES`). Missing is None, never zero."""
    row = rec["row"]
    a = dict.fromkeys(AXIS)
    if rec.get("case") is None:
        return a
    fl, kn, cu = rec.get("flicker") or {}, rec.get("kinematics") or {}, rec.get("curves") or {}
    size = fl.get("extent") or kn.get("width") or num(row.get("size_px"))
    against = row.get("rate_is") == "against the background"
    rate = num(row.get("rate_px_per_s"))
    la = g(rec, "layers", "all") or {}
    ratio = g(rec, "camera", "size_ratio")
    a.update(
        beat_amp=fl.get("amp"), beat_stands=fl.get("stands"),
        beat_hz=fl.get("hz") if fl.get("cont_p") is not None and fl["cont_p"] <= LINE_P else None,
        light_var=cu.get("light_var"), light_fast=cu.get("light_fast"), light_over_bg=cu.get("light_over_bg"),
        size_trend=math.log(ratio) if ratio and ratio > 0 and not g(rec, "camera", "zooms") else None,
        rate_scene=rate if against else None,
        rate_scene_w=(rate / size) if against and rate is not None and size else None,
        speed_spread=((num(la.get("p84")) - num(la.get("p16"))) / num(la.get("median")))
        if against and la and num(la.get("median")) and num(la.get("p84")) is not None and num(la.get("p16")) is not None else None,
        rate_screen=kn.get("v"), rate_screen_w=(kn["v"] / size) if kn.get("v") is not None and size else None,
        bend=(kn["sagitta"] / kn["length"]) if kn.get("sagitta") is not None and kn.get("length") else None,
        misfit=kn.get("resid_frac"),
        breaks=None if kn.get("breaks") is None else float(bool(kn["breaks"])),
        zooms=float(g(rec, "camera", "zooms")) if g(rec, "camera", "zooms") is not None else None,
        held_still=num(g(rec, "layers", "held", "share_of_pairs")),
        size_px=size, contrast=g(rec, "verify", "contrast"),
        frames=num(row.get("followed_frames")) or g(rec, "verify", "frames"),
        fps=g(rec, "clip", "fps") or num(row.get("fps")), held=fl.get("held"),
    )
    return {k: (None if v is None or (isinstance(v, float) and not math.isfinite(v)) else v) for k, v in a.items()}


def tr(name, v):
    """An axis's value on the scale its distances are measured on (`AXES`' transform)."""
    if v is None:
        return np.nan
    if AXIS[name][4] == "log":
        return math.log10(max(float(v), FLOOR.get(name, 1e-6)))
    return float(v)


# ---- 5. strata of quality --------------------------------------------------------------------------------------------
# D9: unsupervised scores track the record's quality, so an object is held against a class's objects of its own
# quality only (Mondrian conformal). The strata are the object's contrast against its surround (grey levels), cut
# at the scored controls' own median: on the controls the brightness axes fall with contrast (Spearman -0.27 to
# -0.44) more than with width, as the noise strand found for a line's amplitude across the corpus. Two strata, not
# three: with three, the helicopters (30 found) have under 19 in a stratum. E5's range (`RANGE`) then asks that the
# object's width, contrast and frame rate lie inside the class's in that stratum. Measured 2026-11-15 against the
# alternatives (width in two or three, no strata): docs/method.md section 64.
STRATUM = "contrast"    # the quality axis the strata are cut on ...
BINS = 2                # ... into this many, at the scored controls' own quantiles
RANGE = ("size_px", "contrast", "fps")
RANGE_MARGIN = 0.10     # E5's range is the class's, widened by a tenth at each end, so that 29.97 frames a second is
                        # inside a class filmed at 30 and 24 is not (judgement, stated: a decision for the maintainer)


def strata_edges(controls, axis=None, bins=None):
    axis, bins = axis or STRATUM, bins or BINS
    v = np.array([c["axes"].get(axis) for c in controls if c["axes"].get(axis)], float)
    if v.size < bins * MIN_CLASS or bins < 2:
        return []
    return sorted({float(x) for x in np.quantile(v, [i / bins for i in range(1, bins)])})


def stratum(axes, edges, axis=None):
    v = axes.get(axis or STRATUM)
    if v is None:
        return None
    return int(sum(v > e for e in edges))


STRATUM_WORDS = {"size_px": ("width unknown", "px wide"), "contrast": ("contrast unknown", "grey levels of contrast")}


def stratum_words(s, edges, axis=None):
    unknown, unit = STRATUM_WORDS.get(axis or STRATUM, ("unknown", ""))
    if s is None:
        return unknown
    lo = edges[s - 1] if s > 0 else None
    hi = edges[s] if s < len(edges) else None
    return (f"{lo:.3g} to {hi:.3g} {unit}" if lo is not None and hi is not None else
            f"up to {hi:.3g} {unit}" if hi is not None else f"over {lo:.3g} {unit}" if lo is not None else "any")


# ---- 6. conformal p-values against each class ------------------------------------------------------------------------
def _scale(col):
    m = np.median(col)
    s = MAD_K * np.median(np.abs(col - m))
    if not s > 0:
        s = float(np.std(col))
    return float(m), float(s if s > 0 else 1.0)


def score(x, members, axes):
    """The conformal score of `x` among `members` (rows of transformed values over `axes`, all finite): for the bag of
    members and x together, each one's largest robust distance |value - median| / (1.4826 MAD) over the axes, the
    median and spread taken over the whole bag, so the score treats x and the members alike (full conformal).
    Returns (x's score, the members' scores, x's distance on each axis, each axis's distances in the bag)."""
    bag = np.vstack([members, x[None, :]])
    Z = np.empty_like(bag)
    for j in range(bag.shape[1]):
        m, s = _scale(bag[:, j])
        Z[:, j] = (bag[:, j] - m) / s
    S = np.max(np.abs(Z), axis=1)
    return float(S[-1]), S[:-1], Z[-1], Z


def pvalue(x, members, axes, names=None):
    """The conformal p-value of x against members over `axes` (both finite on all of them), with the measure that
    drove it: dict(p, n, score, axis, z, axis_p, axes). p = (members scoring at least x's, plus x) / (n + 1), so it is
    never under 1/(n+1), and for an x drawn like the members it is uniform (ties counted against x: conservative)."""
    n = len(members)
    s, S, zx, Z = score(x, members, axes)
    p = (int(np.sum(S >= s - 1e-12)) + 1) / (n + 1)
    j = int(np.argmax(np.abs(zx)))
    ap = (int(np.sum(np.abs(Z[:-1, j]) >= abs(zx[j]) - 1e-12)) + 1) / (n + 1)
    nm = names or axes
    return dict(p=p, n=n, score=s, axis=nm[j], z=float(zx[j]), axis_p=ap, axes=list(nm))


def against(ax, members_axes, used=SCORE):
    """The p-value of an object (its axes, raw) against one class's objects in its stratum (their axes, raw), over the
    score axes both have: the axes the object has, and the members that have every one of them. Where fewer than
    MIN_CLASS members have them all, the axis that the fewest members have is let go, one at a time; the p-value is
    never made from fewer. Returns the pvalue dict, or dict(p=None, why=...)."""
    use = [k for k in used if ax.get(k) is not None]
    if not use:
        return dict(p=None, why="none of the scored measurements was made on the object")
    while use:
        mem = [m for m in members_axes if all(m.get(k) is not None for k in use)]
        if len(mem) >= MIN_CLASS:
            x = np.array([tr(k, ax[k]) for k in use])
            M = np.array([[tr(k, m[k]) for k in use] for m in mem])
            return pvalue(x, M, use)
        have = {k: sum(m.get(k) is not None for m in members_axes) for k in use}
        use.remove(min(use, key=lambda k: (have[k], -use.index(k))))
    return dict(p=None, why=f"fewer than {MIN_CLASS} of the class's objects in its stratum share a measurement with it")


def class_members(controls, cls, s, edges, leave=None):
    """The class's control objects in stratum `s` (none of `leave`, a video's name, so a held-out control is never
    compared with its own video's objects)."""
    return [c for c in controls if c["class"] == cls and stratum(c["axes"], edges) == s and (leave is None or c["video"] != leave)]


def in_range(ax, members):
    """E5: the axes of RANGE on which the object lies outside every member's value (the class's range there)."""
    out = []
    for k in RANGE:
        v = ax.get(k)
        vals = [m["axes"][k] for m in members if m["axes"].get(k) is not None]
        if v is not None and vals and not (min(vals) * (1 - RANGE_MARGIN) <= v <= max(vals) * (1 + RANGE_MARGIN)):
            out.append(f"{k} {v:.3g} outside the class's {min(vals):.3g}-{max(vals):.3g}")
    return out


def pvalues(ax, controls, classes, edges, leave=None):
    """{class: result} for one object's axes: the conformal p-value against each class within the object's stratum, or
    NO POWER with the reason (no width; too few of the class in the stratum; outside its range; no shared measurement)."""
    s = stratum(ax, edges)
    out = {}
    for cls in classes:
        if s is None:
            out[cls] = dict(p=None, why=f"{stratum_words(None, edges)}: the object has no stratum")
            continue
        mem = class_members(controls, cls, s, edges, leave)
        if len(mem) < MIN_CLASS:
            out[cls] = dict(p=None, why=f"{len(mem)} of the class's objects are {stratum_words(s, edges)}, under the {MIN_CLASS} a p-value of 0.05 needs")
            continue
        rng = in_range(ax, mem)
        if rng:
            out[cls] = dict(p=None, why="outside the class's range: " + "; ".join(rng))
            continue
        out[cls] = against(ax, [m["axes"] for m in mem])
    return out


def least_unlike(ps):
    """(the largest p over the classes with power, its class, how many classes had power). An object is unlike every
    class with power at level a when this p is at most a: if it belongs to any one of them, that class's p is valid,
    so the largest is too (the intersection-union rule)."""
    have = {c: r for c, r in ps.items() if r.get("p") is not None}
    if not have:
        return None, None, 0
    c = max(have, key=lambda c: (have[c]["p"], -have[c]["score"]))
    return have[c]["p"], c, len(have)


# ---- 7. calibration on held-out controls -----------------------------------------------------------------------------
def calibrate(controls, classes, edges):
    """Each control object against its own class with its own video's objects held out (so neither it nor its
    neighbours are in the reference), and against every other class: the held-out p-values against its own class
    should be uniform. Returns dict(own={class: [p...]}, cross={class: {other: [p...]}}, power={class: n with power})."""
    own = {c: [] for c in classes}
    cross = {c: {o: [] for o in classes if o != c} for c in classes}
    for c in controls:
        ps = pvalues(c["axes"], controls, classes, edges, leave=c["video"])
        if c["class"] in own and ps[c["class"]].get("p") is not None:
            own[c["class"]].append(ps[c["class"]]["p"])
        for o in cross.get(c["class"], {}):
            if ps[o].get("p") is not None:
                cross[c["class"]][o].append(ps[o]["p"])
    return dict(own=own, cross=cross)


def uniformity(ps):
    """How far held-out p-values are from uniform: n, the shares at or under 0.05, 0.10, 0.20, 0.50, and the largest
    gap between the share at or under p and p itself, read at the p-values that occur (a conformal p-value is a step
    of 1/(n+1), and at its own steps a valid one has P(p <= t) = t; between them the gap is the step's, not an error),
    with the Kolmogorov distribution's chance of a gap that large (scipy's kstwobign, conservative for steps)."""
    ps = sorted(p for p in ps if p is not None)
    if not ps:
        return dict(n=0)
    from scipy import stats
    a = np.array(ps)
    t = np.unique(a)
    F = np.searchsorted(a, t, side="right") / len(a)
    d = float(np.max(np.abs(F - t)))
    return dict(n=len(a), **{f"le_{x:.2f}": float(np.mean(a <= x)) for x in (0.05, 0.10, 0.20, 0.50)},
                ks=d, ks_p=float(stats.kstwobign.sf(d * math.sqrt(len(a)))))


# ---- 8. the list and the corpus summary ------------------------------------------------------------------------------
def bh(ps, q):
    """Benjamini-Hochberg: the indices rejected at false discovery rate q."""
    ps = np.asarray(ps, float)
    m = len(ps)
    if not m:
        return []
    o = np.argsort(ps)
    ok = ps[o] <= q * np.arange(1, m + 1) / m
    k = int(np.max(np.nonzero(ok)[0])) + 1 if ok.any() else 0
    return sorted(int(i) for i in o[:k])


def by(ps, q):
    """Benjamini-Yekutieli: Benjamini-Hochberg at q / (1 + 1/2 + ... + 1/m), valid under any dependence."""
    m = len(ps)
    return bh(ps, q / sum(1.0 / i for i in range(1, m + 1))) if m else []


def boot_share(groups, level, draws=BOOT, seed=0):
    """The share of objects with p at most `level`, and its 95 % interval from a bootstrap over videos: `groups` is
    [[p of each object of one video]...], resampled whole (E10)."""
    groups = [g_ for g_ in groups if g_]
    n = sum(len(g_) for g_ in groups)
    if not n:
        return dict(n=0)
    k = sum(sum(p <= level for p in g_) for g_ in groups)
    rng = np.random.default_rng(seed)
    tot = np.array([len(g_) for g_ in groups])
    hit = np.array([sum(p <= level for p in g_) for g_ in groups])
    sh = []
    for _ in range(draws):
        i = rng.integers(0, len(groups), len(groups))
        sh.append(hit[i].sum() / max(tot[i].sum(), 1))
    lo, hi = np.quantile(sh, [0.025, 0.975])
    return dict(n=n, k=int(k), share=k / n, lo=float(lo), hi=float(hi), videos=len(groups))


def video_of(rec):
    r = rec["row"]
    return r.get("id") or r.get("unit") or r.get("folder")


def rank(recs, controls, classes=None, edges=None):
    """The whole reading: rows to objects, the defects, the axes, each object's p-values, the order. Returns
    dict(objects=[...], defects=Counter-like dict, edges, classes)."""
    objs = objects(recs)
    classes = classes or sorted({c["class"] for c in controls if c.get("scored", True)})
    edges = strata_edges([c for c in controls if c["class"] in classes]) if edges is None else edges
    scored_ctl = [c for c in controls if c["class"] in classes]
    out = []
    for r in objs:
        d = defects(r)
        ax = axes_of(r)
        o = dict(key=r["key"], video=video_of(r), file=r["row"].get("file"), release=r["row"].get("release"), object=r["row"].get("object"),
                 kind=r.get("kind"), also=r.get("also", []), defects=d, axes=ax, stratum=stratum(ax, edges),
                 label=r["row"].get("label"), grade=r["row"].get("grade"), folder=r.get("folder"),
                 no_power={k: len(v) for k, v in (r.get("no_power") or {}).items()})
        if not d:
            if o["kind"] == "group":
                o["ps"] = {c: dict(p=None, why="a group of several points: the control classes are single objects (E5)") for c in classes}
            else:
                o["ps"] = pvalues(ax, scored_ctl, classes, edges)
            o["p_max"], o["nearest"], o["classes_with_power"] = least_unlike(o["ps"])
        out.append(o)
    live = [o for o in out if not o["defects"] and o.get("p_max") is not None]
    live.sort(key=lambda o: (o["p_max"], -(o["ps"][o["nearest"]]["score"])))
    for i, o in enumerate(live, 1):
        o["rank"] = i
    return dict(objects=out, classes=classes, edges=edges)


def read_looked(path):
    """{key: dict(reason, by)} from a TSV with columns key, reason, by: what a look at each track strip found."""
    with open(path, newline="", encoding="utf-8") as f:
        return {r["key"]: dict(reason=r.get("reason") or "", by=r.get("by") or "")
                for r in csv.DictReader((ln for ln in f if not ln.startswith("#")), delimiter="\t") if r.get("key")}


def read_apart(path):
    """The video files of a list to be reported apart: a TSV with a `file` column; where it has a `role` column too (as
    tools/sweep/holdout.tsv), only the rows whose role is "held out"."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader((ln for ln in f if not ln.startswith("#")), delimiter="\t"))
    return {r["file"] for r in rows if r.get("file") and ("role" not in r or (r.get("role") or "").strip() == "held out")}


def summary(result, levels=(0.05, 0.10), apart=None):
    """The corpus summary: the defects by rule; the objects with power; at each level, how many are unlike every class
    with power, raw, after Benjamini-Hochberg and after Benjamini-Yekutieli over those objects, and the raw share with
    its interval from a bootstrap over videos; the same by stratum and by release (D9)."""
    objs = result["objects"]
    dfx = {}
    for o in objs:
        for k, _ in o["defects"][:1]:
            dfx[k] = dfx.get(k, 0) + 1
    live = [o for o in objs if not o["defects"]]
    pw = [o for o in live if o.get("p_max") is not None]
    ps = [o["p_max"] for o in pw]
    out = dict(rows_folded=sum(len(o["also"]) for o in objs), objects=len(objs), defects=dfx,
               defect_objects=sum(1 for o in objs if o["defects"]), ranked=len(pw),
               groups=sum(1 for o in live if o["kind"] == "group"),
               no_power=sum(1 for o in live if o.get("p_max") is None), levels={})
    by_video = {}
    for o in pw:
        by_video.setdefault(o["video"], []).append(o["p_max"])
    for a in levels:
        out["levels"][f"{a:.2f}"] = dict(raw=sum(p <= a for p in ps), bh=[pw[i]["key"] for i in bh(ps, a)],
                                          by=[pw[i]["key"] for i in by(ps, a)], share=boot_share(list(by_video.values()), a))
    strata = {}
    for o in pw:
        s = strata.setdefault(str(o["stratum"]), dict(n=0, le05=0))
        s["n"] += 1
        s["le05"] += o["p_max"] <= 0.05
    rel, grade = {}, {}
    for o in pw:
        for d_, k in ((rel, str(o["release"])), (grade, str(o["grade"]))):
            s = d_.setdefault(k, dict(n=0, le05=0))
            s["n"] += 1
            s["le05"] += o["p_max"] <= 0.05
    out.update(by_stratum=strata, by_release=rel, by_grade=grade)
    if apart:
        for name, sel in (("apart", lambda o: o.get("file") in apart), ("rest", lambda o: o.get("file") not in apart)):
            os_ = [o for o in pw if sel(o)]
            out[name] = dict(videos=len({o["video"] for o in os_}), ranked=len(os_),
                             **{f"le_{a:.2f}": sum(o["p_max"] <= a for o in os_) for a in levels})
    return out


# ---- 9. the controls: known objects through the same batch, matched to their truth -----------------------------------
SAME_PX = 2.0           # several.SAME_PX: two tracks this close on a frame are on one thing there
SAME_FRAMES = 10        # several.SAME_FRAMES


def track_of(rec):
    """{frame: (x, y)} of a record's followed track (its `_autotrack.csv`), or {}."""
    from .forensics import read_track
    if not rec.get("case"):
        return {}
    js = Path(rec["case"])
    p = js.with_name(js.name[:-len("_case.json")] + "_autotrack.csv")
    try:
        return read_track(p) if p.exists() else {}
    except (OSError, ValueError, KeyError, StopIteration):
        return {}


def on_truth(track, truth, pad=SAME_PX):
    """(frames the track lies on the truth's box, frames both have): on a frame, within the box's half-size plus
    `pad` of its centre on each axis. A truth frame is (x, y) or (x, y, half-width, half-height)."""
    shared = [n for n in track if n in truth]
    on = 0
    for n in shared:
        t = truth[n]
        hw, hh = (t[2], t[3]) if len(t) >= 4 else (0.0, 0.0)
        on += abs(track[n][0] - t[0]) <= hw + pad and abs(track[n][1] - t[1]) <= hh + pad
    return on, len(shared)


def match(recs, truths, pad=SAME_PX, frames=SAME_FRAMES):
    """Each known object (`truths`: [dict(video, name, cls, track)], `video` the batch's unit `id`) and the batch
    object that lies on it, by several.same_things' rule turned on a labelled box: on SAME_FRAMES frames or more and on
    half or more of the frames both have, within the box plus SAME_PX. Where several batch objects lie on one known
    object, the one on it longest stands for it (the others are pieces of it, as `same_as` folds them); a batch object
    is given to one known object at most. Returns [(truth, rec, on, shared)] for the matched, and the unmatched recs."""
    by_video = {}
    for r in recs:
        by_video.setdefault(r["row"].get("id"), []).append(r)
    cand = []
    for t in truths:
        for r in by_video.get(t["video"], []):
            tk = r.get("_track")
            if tk is None:
                tk = r["_track"] = track_of(r)
            on, sh = on_truth(tk, t["track"], pad)
            if on >= frames and 2 * on >= sh:
                cand.append((on, t, r, sh))
    cand.sort(key=lambda c: -c[0])
    used_t, used_r, out = set(), set(), []
    for on, t, r, sh in cand:
        if id(t) in used_t or id(r) in used_r:
            continue
        used_t.add(id(t))
        used_r.add(id(r))
        out.append((t, r, on, sh))
    for r in recs:
        r.pop("_track", None)
    return out, [r for r in recs if id(r) not in used_r]


CONTROL_COLUMNS = ["source", "class", "scored", "video", "key", "truth", "on", "shared", "kind", "defect"] + [a[0] for a in AXES]


def control_rows(matched, source, scored=True):
    """The controls table's rows for matched known objects: their class, where they came from, their defect (the first,
    if any: a control that is a defect is kept in the table and left out of its class) and their axes."""
    out = []
    for t, r, on, sh in matched:
        d = defects(r)
        out.append(dict(source=source, **{"class": t["cls"]}, scored=bool(scored), video=t["video"], key=key_of(r),
                        truth=t["name"], on=on, shared=sh, kind=kind_of(r), defect=d[0][0] if d else "", axes=axes_of(r)))
    return out


def write_controls(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(CONTROL_COLUMNS)
        for c in rows:
            w.writerow([c["source"], c["class"], int(c["scored"]), c["video"], c["key"], c["truth"], c["on"], c["shared"],
                        c.get("kind", "single"), c["defect"]] + [_cell(c["axes"].get(a[0])) for a in AXES])


def _cell(v):
    return "" if v is None else (f"{v:.6g}" if isinstance(v, float) else str(v))


def read_controls(path):
    """The controls table (`write_controls`): [dict(source, class, scored, video, key, truth, on, shared, defect,
    axes)]; a control with a defect is kept, marked, and left out of `usable`."""
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader((ln for ln in f if not ln.startswith("#")), delimiter="\t"):
            out.append(dict(source=r["source"], **{"class": r["class"]}, scored=r["scored"] in ("1", "True", "true"),
                            video=r["video"], key=r["key"], truth=r["truth"], on=int(r["on"] or 0), shared=int(r["shared"] or 0),
                            kind=r.get("kind") or "single", defect=r["defect"], axes={a[0]: num(r.get(a[0])) for a in AXES}))
    return out


def usable(controls):
    """The controls a class is made of: no defect, and single objects (a group's measurements are a group's)."""
    return [c for c in controls if not c["defect"] and c.get("kind", "single") == "single"]


def default_controls():
    """The reference controls table, if the data folder has it: $MCDONALD_DATA/controls/rank_controls.tsv."""
    import os
    d = os.environ.get("MCDONALD_DATA", "").strip()
    p = Path(d) / "controls" / "rank_controls.tsv" if d else None
    return p if p and p.exists() else None


def checks(controls, classes, edges):
    """Known objects outside the scored classes (AARO's resolved cases, the Galileo flyers): each against the scored
    classes, as a corpus object would be. How often a known, ordinary object comes out unlike every class is the
    list's false-alarm rate on objects the classes do not cover."""
    ref = [c for c in usable(controls) if c["scored"] and c["class"] in classes]
    out = []
    for c in usable(controls):
        if c["scored"]:
            continue
        ps = pvalues(c["axes"], ref, classes, edges)
        p, near, k = least_unlike(ps)
        out.append(dict(key=c["key"], source=c["source"], cls=c["class"], video=c["video"], p_max=p, nearest=near,
                        classes_with_power=k, ps=ps))
    return out


# ---- 10. writing the list --------------------------------------------------------------------------------------------
WORDS = dict(  # each axis in words, for the list's "measure" column (sciencespeak)
    beat_amp="the strength of its brightness's strongest rhythm", beat_hz="the frequency of that rhythm",
    light_var="how much its brightness varies", light_over_bg="how much faster its brightness varies than the sky beside it",
    size_trend="how its size changes along the track", rate_scene_w="its speed against the background, in its own widths",
    speed_spread="how much that speed varies from second to second")


def drove(r):
    """The measure that drove one class's p-value, in words: which, and above or below the class's middle."""
    if r.get("p") is None:
        return ""
    return f"{WORDS.get(r['axis'], r['axis'])}, {abs(r['z']):.1f} spreads {'above' if r['z'] > 0 else 'below'} the class's middle"


def list_rows(result):
    cls = result["classes"]
    head = ["rank", "key", "video", "release", "object", "kind", "also", "defect", "defect_why", "stratum", "label", "grade",
            "p_least_unlike", "least_unlike", "classes_with_power"]
    for c in cls:
        head += [f"p_{c}", f"n_{c}", f"measure_{c}", f"z_{c}", f"no_power_{c}"]
    head += [a[0] for a in AXES]
    rows = []
    order = sorted(result["objects"], key=lambda o: (o.get("rank") or 10 ** 9, o["key"]))
    for o in order:
        d = o["defects"]
        r = [o.get("rank") or "", o["key"], o["video"], o["release"] or "", o["object"], o["kind"], ",".join(o["also"]),
             d[0][0] if d else "", d[0][1] if d else "", "" if o["stratum"] is None else o["stratum"], o["label"] or "",
             o["grade"] or "", _cell(o.get("p_max")), o.get("nearest") or "", o.get("classes_with_power", "")]
        for c in cls:
            x = (o.get("ps") or {}).get(c) or {}
            r += [_cell(x.get("p")), x.get("n", ""), x.get("axis", ""), _cell(x.get("z")), x.get("why", "")]
        r += [_cell(o["axes"].get(a[0])) for a in AXES]
        rows.append(r)
    return head, rows


def write_tsv(path, head, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(head)
        w.writerows(rows)


def _pct(x):
    return f"{100 * x:.0f} %"


def markdown(result, summ, calib, chk, top=20, note=None):
    """The list as a page for a person (sciencespeak): what it is, the defects, the classes checked, the batch as a
    whole, and the first `top` objects of the list."""
    cls, edges = result["classes"], result["edges"]
    L = ["# Objects of a batch, held against known classes", ""]
    if note:
        L += [note, ""]
    L += ["This list orders the objects of a batch by how unlike they are to tracks of known objects. A track is the "
          "object's position in each frame, joined up. The list is for a person to look through, not a finding. A place "
          "near the top says that an object differs from the labelled tracks it was held against, by one measurement. It "
          "does not say what the object is, and it never says that an object is unexplained.", "",
          "## How to read it", "",
          "Each known class is a set of labelled tracks of one kind of object. Every object is held against each class on "
          "the same measurements, made by the same version of the toolkit. Its p-value against a class is a share of that "
          "class's tracks: those that lie at least as far from the class's middle as the object does. A p-value of 0.01 means that "
          "only 1 in 100 of the class's tracks lie that far out. A class's tracks are not the sky's birds or drones, so a "
          "small p-value says \"unlike these tracks\", and no more.", "",
          "An object is compared only with tracks of about its own contrast, because a faint spot measures differently from "
          "a clear one. A class may have too few such tracks, or none as wide, as faint or at that frame rate. Then the "
          "class can't tell, and the list says so.", "",
          "The list is ordered by the largest of an object's p-values: the class it is least unlike. The measure column "
          "names the measurement that set it apart from that class, and in which direction. A spread is the class's "
          "typical distance from its middle.", "",
          "## Rows that are not objects, and records with defects", ""]
    L += [f"The batch's table has {summ['objects'] + summ['rows_folded']} rows. {summ['rows_folded']} of them are the "
          f"same object as another row, followed onto its track, and are counted through that row. That leaves "
          f"{summ['objects']} objects.", "",
          f"{summ['defect_objects']} of those have a defect of the record, found before any ranking. They are listed and "
          "never ranked:", ""]
    L += [f"- {v}: {RULE_WORDS[k]}" for k, v in sorted(summ["defects"].items(), key=lambda kv: -kv[1])]
    L += ["", f"{summ['groups']} more are groups of several points moving together. The known classes are single "
          "objects, so no class can tell for a group.",
          f"Of the rest, {summ['ranked']} objects have a p-value against at least one class, and "
          f"{summ['no_power'] - summ['groups']} have none, for the reasons in the table's columns.", ""]
    L += ["## The known classes, checked", "",
          "Each labelled track was held out in turn, with every other track of its video, and held against its own class. "
          "If the p-values are right, about 5 % of them fall at or under 0.05, and 10 % at or under 0.10.", "",
          "| class | tracks held out | at or under 0.05 | at or under 0.10 | at or under 0.50 |", "|---|---:|---:|---:|---:|"]
    for c in cls:
        u = uniformity(calib["own"].get(c, []))
        if u.get("n"):
            L.append(f"| {c} | {u['n']} | {_pct(u['le_0.05'])} | {_pct(u['le_0.10'])} | {_pct(u['le_0.50'])} |")
    L += ["", "How often a track of one class comes out unlike another class at 0.05 says how well the measurements tell "
          "the classes apart:", "", "| track's class | " + " | ".join(f"unlike {c}" for c in cls) + " |",
          "|---|" + "---:|" * len(cls)]
    for c in cls:
        cells = []
        for o in cls:
            ps = calib["own"].get(c, []) if o == c else calib["cross"].get(c, {}).get(o, [])
            cells.append(f"{_pct(np.mean(np.array(ps) <= 0.05))} of {len(ps)}" if ps else "no power")
        L.append(f"| {c} | " + " | ".join(cells) + " |")
    if chk:
        w = [x for x in chk if x["p_max"] is not None]
        hit = [x for x in w if x["p_max"] <= 0.05]
        L += ["", f"Known objects of other kinds were held against the same classes: {len(chk)} objects from "
              + ", ".join(sorted({x['source'] for x in chk})) + f". {len(w)} had a p-value against at least one class, and "
              f"{len(hit)} of them came out unlike every class at 0.05. That is how often an ordinary object of a kind the "
              "classes do not hold reaches the top of the list.", ""]
        for x in hit:
            L.append(f"- {x['cls']} ({x['source']}, {x['key']}): least unlike {x['nearest']}, p = {x['p_max']:.3f}")
    L += ["", "## The batch as a whole", ""]
    for a, v in summ["levels"].items():
        s = v["share"]
        L.append(f"- At {a}: {v['raw']} of {summ['ranked']} objects are unlike every class that could tell"
                 + (f" ({_pct(s['share'])}; {_pct(s['lo'])} to {_pct(s['hi'])} when whole videos are drawn again at random)" if s.get("n") else "")
                 + f". Allowing for the number of objects tested, {len(v['bh'])} remain by the Benjamini-Hochberg rule. "
                 f"The Benjamini-Yekutieli rule allows for any dependence between the objects, and {len(v['by'])} remain by it.")
    if summ.get("apart"):
        a, b = summ["apart"], summ["rest"]
        L += ["", f"Counted apart, the videos of the list given with `--apart` ({a['videos']} videos): {a['le_0.05']} of "
              f"{a['ranked']} objects unlike every class at 0.05. The rest ({b['videos']} videos): {b['le_0.05']} of {b['ranked']}."]
    L += ["", "By the object's contrast, the count unlike every class at 0.05 (an excess among the faint would be the "
          "record's quality, not the objects):", "", "| contrast | objects | at or under 0.05 |", "|---|---:|---:|"]
    for s, v in sorted(summ["by_stratum"].items()):
        L.append(f"| {stratum_words(int(s), edges) if s not in ('None',) else 'unknown'} | {v['n']} | {v['le05']} |")
    L += ["", "| how sure the report is | objects | at or under 0.05 |", "|---|---:|---:|"]
    L += [f"| {k} | {v['n']} | {v['le05']} |" for k, v in sorted(summ["by_grade"].items())]
    L += ["", "| release | objects | at or under 0.05 |", "|---|---:|---:|"]
    L += [f"| {r} | {v['n']} | {v['le05']} |" for r, v in sorted(summ["by_release"].items())]
    L += ["", f"## The list: the first {top}", "",
          "| rank | video | object | least unlike | p-value | classes that could tell | measure | how sure |",
          "|---:|---|---:|---|---:|---:|---|---|"]
    live = sorted([o for o in result["objects"] if o.get("rank")], key=lambda o: o["rank"])
    for o in live[:top]:
        r = o["ps"][o["nearest"]]
        L.append(f"| {o['rank']} | {o['video']} | {o['object']} | {o['nearest']} | {o['p_max']:.3f} | "
                 f"{o['classes_with_power']} of {len(cls)} | {drove(r)} | {o['grade'] or ''} |")
    L += ["", "The whole list, every object's p-value against every class, the reason where a class could not tell, and "
          "every measurement, is in `rank.tsv` beside this page.", ""]
    return "\n".join(L)


# ---- 11. the command line --------------------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="mcdonald rank", formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Order the objects of a batch by how unlike they are to tracks of known objects. Rows that are the same "
                    "object are counted once, and objects with a defect of the record are listed first and never ranked. "
                    "Every other object gets a p-value against each known class: the share of that class's tracks, of "
                    "about its own contrast, at least as far from the class's middle. The list is for a person to look "
                    "through. It changes no report, and it never calls an object unexplained.",
        epilog="examples:\n"
               "  mcdonald rank runs                         the batch in runs/, against the reference controls\n"
               "  mcdonald rank runs --controls ctl.tsv --out ranked\n"
               "  mcdonald rank runs --json                  one JSON object on stdout\n\n"
               "The controls' table is the data folder's controls/rank_controls.tsv unless --controls names another.\n"
               "docs/method.md section 64 says how the p-values are made and how they fail.")
    ap.add_argument("batch", nargs="?", help="a batch folder: the --out of `mcdonald batch`, with its batch.json")
    ap.add_argument("--controls", metavar="TSV", help="the known objects' table (default: the data folder's controls/rank_controls.tsv)")
    ap.add_argument("--out", metavar="DIR", help="where the list goes (default: BATCH/rank)")
    ap.add_argument("--records", metavar="FILE", help="the objects as read before (rank_records.json.gz), instead of reading the batch again")
    ap.add_argument("--masks", action="store_true",
                    help="also find each track on the display's overlay or a redaction block (reads 40 frames of each case "
                         "from its video: slower, and needs the videos)")
    ap.add_argument("--looked", metavar="TSV", help="what a look at track strips found: a table of key, reason, by; each "
                                                    "object named is set aside as a record, not an object, with the reason")
    ap.add_argument("--apart", metavar="TSV", help="videos to count apart in the summary (a list with a `file` column, such as a "
                                                   "held-out set)")
    ap.add_argument("--top", type=int, default=20, metavar="N", help="objects on the page's list (default 20; the table has all)")
    ap.add_argument("--json", action="store_true", help="print one JSON object on stdout; everything else goes to stderr")
    args = ap.parse_args(argv)
    say = (lambda *a: print(*a, file=sys.stderr)) if args.json else print
    from .report import emit, envelope
    if not args.batch and not args.records:
        ap.error("name a batch folder, or give --records FILE")
    out = Path(args.out) if args.out else Path(args.batch) / "rank"
    out.mkdir(parents=True, exist_ok=True)
    if args.records:
        R = read_json(args.records)
        head, recs = R["head"], R["records"]
    else:
        say(f"reading the objects of {args.batch}")
        head, recs = records(args.batch, say=say)
    if args.masks:
        import tempfile
        with tempfile.TemporaryDirectory(prefix="rank-masks-") as td:
            add_masks(recs, td, say=say)
    if args.masks or not args.records:
        write_json(out / "rank_records.json.gz", dict(head=head, records=recs))
    if args.looked:
        lk = read_looked(args.looked)
        for r in recs:
            if key_of(r) in lk:
                r["looked"] = lk[key_of(r)]
    ctl_path = Path(args.controls) if args.controls else default_controls()
    controls = read_controls(ctl_path) if ctl_path else []
    if not controls:
        say("no controls' table: the defects and the measurements only, with no p-values (NO POWER)")
    good = usable(controls)
    classes = sorted({c["class"] for c in good if c["scored"]})
    edges = strata_edges([c for c in good if c["scored"]])
    result = rank(recs, [c for c in good if c["scored"]], classes, edges)
    summ = summary(result, apart=read_apart(args.apart) if args.apart else None)
    calib = calibrate([c for c in good if c["scored"]], classes, edges) if classes else dict(own={}, cross={})
    chk = checks(controls, classes, edges) if classes else []
    note = (f"Made by mcdonald {__version__} from {args.batch or args.records}; the batch's own note: "
            f"{(g(head, 'options', 'note') or 'none').rstrip('.')}. Controls: {ctl_path or 'none'}.")
    th, tr_ = list_rows(result)
    write_tsv(out / "rank.tsv", th, tr_)
    (out / "rank.md").write_text(markdown(result, summ, calib, chk, args.top, note), encoding="utf-8")
    cal = {c: uniformity(v) for c, v in calib["own"].items()}
    js = dict(format=FORMAT, mcdonald=__version__, batch=str(args.batch or ""), controls=str(ctl_path or ""),
              classes=classes, edges=edges, summary=summ, calibration=cal,
              cross={c: {o: uniformity(v) for o, v in d.items()} for c, d in calib["cross"].items()},
              checks=chk, objects=result["objects"])
    write_json(out / "rank.json", js)
    files = [out / "rank.md", out / "rank.tsv", out / "rank.json"]
    lv = summ["levels"].get("0.05", {})
    say(f"{summ['objects']} objects ({summ['rows_folded']} rows folded in); {summ['defect_objects']} with a defect; "
        f"{summ['ranked']} ranked; at 0.05, {lv.get('raw', 0)} unlike every class that could tell "
        f"({len(lv.get('bh', []))} after Benjamini-Hochberg)")
    say(f"the list: {files[0]} (and rank.tsv, rank.json)")
    if args.json:
        live = sorted([o for o in result["objects"] if o.get("rank")], key=lambda o: o["rank"])
        emit(envelope("rank", dict(batch=args.batch, controls=str(ctl_path or ""), records=args.records), None, files,
                      dict(summary=summ, calibration=cal, classes=classes, edges=edges,
                           top=[dict(rank=o["rank"], key=o["key"], video=o["video"], object=o["object"], p=o["p_max"],
                                     least_unlike=o["nearest"], measure=o["ps"][o["nearest"]].get("axis"),
                                     z=o["ps"][o["nearest"]].get("z"), grade=o["grade"]) for o in live[:args.top]]),
                      no_power=[] if controls else [("rank", "no controls' table: no p-values")],
                      notes=["A list for a person, not a verdict: a small p-value says the object is unlike these labelled "
                             "tracks by one measurement, never what it is."]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
