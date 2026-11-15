"""`mcdonald noise` -- what the sensors' own backgrounds do, over a whole pass: the corpus noise model, its tail, and a
false discovery rate over the pass's objects (ROADMAP.md 0.6, objective 6; IDEAS.md S3, E24, D7; docs/method.md
section 63).

The flicker stage holds an object's beat against the four background apertures beside it, read as if each were the
object (`flicker.controls_judged`). Four curves say little about how strong a line noise alone makes: a fixed factor
(`flicker.ABOVE`, three times the background's strongest) stands in for a distribution nobody had measured. A batch
over the whole catalog (`mcdonald batch`, method section 54) leaves every background aperture's curve on disk, in each
object's `<tag>_flicker.csv`. This module reads them all, as the stage read them, with the stage's own functions:

1. **The curves as judged** (`as_judged`): each curve over the stretch the stage judged it on, the object's lost frames
   filled across as the stage filled them, each background aperture in its object's brightness (`flicker.judge`'s
   `use`, `seg` and `scale`), checked against the case's own reading of every aperture (`flicker.peak`, kept in
   `fields["curves"]`).
2. **The readings** (`reading`): the strongest line and its amplitude as a share of the brightness (`flicker.peak`),
   the line over its own continuum (`flicker.continuum`: the ratio, its drawn null's 99th centile and p), the strongest
   line in each half-hertz bin of the band over the whole stretch, and the same in 2-s windows along it (the windows of
   `flicker.noise_pdf`).
3. **The model** (`build`, `Model`): every usable background aperture of the pass, by stratum (`stratum_of`), with
   the rules that drop an aperture written down (`dropped_because`).
4. **A reading for any object** (`Model.centile`): its beat's amplitude as a centile of the backgrounds' at its
   frequency, in its stratum, its own video's backgrounds left out, with an interval from resampling videos (E10).
5. **The tail** (`tail_fit`, `Model.p_value`): past a high threshold of the backgrounds' standing over their own
   continuum, a generalised Pareto fitted to the excesses (peaks over a threshold; E24), so that a line stronger than
   any background the pass holds still gets a p-value, with the limit of how far it can be trusted.
6. **The false discovery rate** (`bh`, `by`, `per_video`): Benjamini-Hochberg and Benjamini-Yekutieli over the pass's
   objects, and the same over videos, each video's smallest p corrected for its count.

These are readings and tools. No call of the stage, and no sentence of a report, reads them.
"""
import argparse
import csv
import gzip
import json
import math
import sys
from pathlib import Path

import numpy as np

from . import flicker

GRID_STEP = 0.5          # Hz: the bins a curve's strongest line is read in, from flicker.LOW up
GRID_TOP = 30.0          # Hz: the last bin ends here (a 60-a-second video's band ends at 28.5 Hz)
GRID = np.arange(flicker.LOW, GRID_TOP, GRID_STEP)       # each bin's lower edge
GRID_MID = GRID + GRID_STEP / 2


def bins_of(fr, A, fps):
    """The strongest amplitude in each GRID bin of an amplitude spectrum (fr, A), up to the stage's band's end (0.95 of
    the Nyquist frequency); NaN past it."""
    out = np.full(len(GRID), np.nan)
    hi = 0.95 * fps / 2
    for j, lo in enumerate(GRID):
        m = (fr >= lo) & (fr < lo + GRID_STEP) & (fr <= hi)
        if m.any():
            out[j] = float(A[m].max())
    return out


def read_csv(path):
    """A `<tag>_flicker.csv`: (frame numbers, {column: [value or None per frame]}), columns in the file's order."""
    with open(path, newline="", encoding="utf-8") as fh:
        rd = csv.reader(fh)
        head = next(rd)
        rows = list(rd)
    ns = [int(r[0]) for r in rows]
    cols = {}
    for j, h in enumerate(head[2:], start=2):
        cols[h] = [None if r[j] in ("", "nan") else float(r[j]) for r in rows]
    return ns, cols


def is_background(name):
    return name.startswith("background") and not name.startswith("background light")


def as_judged(fields, ns, cols, fps):
    """The curves as `flicker.judge` read them for their spectra, from a case's flicker fields and its CSV: [{name, kind
    ("object" or "background"), owner (the track a background aperture goes with), frames (first, last), curve (as
    `use` had it over `seg`), scale (the brightness a background aperture is measured in; None for an object), level
    (an object's median brightness)}], every curve the stage read (`per[name]` not None) and only those.

    The stage's own steps, in its order (`_judge`'s `beats_pass`): each curve over its own stretch; where a track was
    lost against what is behind it, its stretch trimmed to the frames either side and the lost frames filled across in
    its curve and in every background aperture that goes with it, which goes no further than it does; where its lost
    frames were the troughs of its own beat (`lost_at_beat`), its stretch is the one recorded and nothing is filled.
    Which frames were lost is read from the fields (`lost`, `lost_at_beat`), not judged again from the CSV's rounded
    values. A track lost on more than LOST_MAX of its frames has no curve of its own; its background apertures are still
    read, in the brightness of the first track read, as the stage read them."""
    names = list(fields.get("tracks") or [])
    spans = {k: tuple(v) for k, v in (fields.get("spans") or {}).items()}
    if not names or not spans:
        return []
    first = max(spans, key=lambda n: spans[n][1] - spans[n][0])
    lo = ns[0]
    raw = {k: list(v) for k, v in cols.items() if k in names or is_background(k)}
    owner = {k: (flicker.owner(k, names) or first) for k in raw if is_background(k)}
    for k in raw:                                          # the stage's first step: each curve over its own track's span
        a, b = spans.get(owner.get(k, k), (lo, lo - 1))    # (a CSV has it already; saved curves do not)
        raw[k] = [v if a <= n <= b else None for v, n in zip(raw[k], ns)]
    seg = {}
    for k, f in raw.items():
        idx = [i for i, v in enumerate(f) if v is not None]
        if idx:
            seg[k] = (idx[0], idx[-1] + 1)
    use = dict(raw)
    too_lost = set()
    lost = fields.get("lost") or {}
    at_beat = fields.get("lost_at_beat") or {}
    for name in names:
        if name not in seg:
            continue
        s0, s1 = seg[name]
        own = raw[name][s0:s1]
        if any(v is None for v in own) or np.median(own) <= 0:
            continue
        mine = [k for k in raw if is_background(k) and owner[k] == name]
        if name in at_beat:
            a, b = at_beat[name]["first"] - lo, at_beat[name]["last"] - lo + 1
            seg[name] = (a, b)
            for m in mine:
                if m in seg:
                    seg[m] = (max(seg[m][0], a), min(seg[m][1], b))
            continue
        if name not in lost:
            continue
        bad = np.isin(np.asarray(ns[s0:s1]), np.asarray(lost[name], int))
        if not bad.any():
            continue
        a, b = 0, len(own)
        while a < b and bad[a]:
            a += 1
        while b > a and bad[b - 1]:
            b -= 1
        gone = [s0 + k for k in range(a, b) if bad[k]]
        if bad.sum() > flicker.LOST_MAX * len(own):
            too_lost.add(name)
        if b <= a:
            del seg[name]
            continue
        seg[name] = (s0 + a, s0 + b)
        for m in [name] + mine:
            if m not in seg:
                continue
            f = list(use[m])
            if m != name:
                seg[m] = (max(seg[m][0], seg[name][0]), min(seg[m][1], seg[name][1]))
            m0, m1 = seg[m]
            if m1 <= m0:
                continue
            part = f[m0:m1]
            if gone and not any(v is None for v in part):
                mask = np.isin(np.arange(m0, m1), gone)
                f[m0:m1] = flicker.filled(part, mask).tolist()
            use[m] = f
    out, level, scale = [], {}, None
    for name, f in use.items():
        bg = is_background(name)
        s = seg.get(name)
        if not s or s[1] <= s[0]:
            continue
        own = f[s[0]:s[1]]
        ok = [v for v in own if v is not None]
        mine_owner = flicker.owner(name, names) if bg else None
        sc = level.get(mine_owner) if bg and mine_owner else scale
        if (len(ok) < len(own) or len(own) < flicker.MIN_FRAMES or (not bg and np.median(ok) <= 0) or (bg and not sc)
                or name in too_lost):
            continue
        if not bg:
            level[name] = float(np.median(ok))
            scale = level[name] if scale is None else scale
        out.append(dict(name=name, kind="background" if bg else "object", owner=owner.get(name) if bg else name,
                        frames=(int(ns[s[0]]), int(ns[s[1] - 1])), curve=np.asarray(own, float), scale=sc if bg else None,
                        level=None if bg else level[name]))
    return out


def window_bins(r, fps):
    """The strongest amplitude in each GRID bin of every window of the deviation curve `r`, the windows those of
    `flicker.noise_pdf` (WINDOW_S long, PPSD_HOP of a window apart, Hann): an array windows x bins, empty for a curve
    shorter than one window."""
    n = len(r)
    W = max(flicker.MIN_FRAMES, int(round(flicker.WINDOW_S * fps)))
    if n < W:
        return np.zeros((0, len(GRID)))
    step = max(1, int(round(flicker.PPSD_HOP * W)))
    w = np.hanning(W)
    fr = np.fft.rfftfreq(flicker.PAD * W, 1 / fps)
    rows = []
    for s in range(0, n - W + 1, step):
        x = r[s:s + W]
        A = 2 * np.abs(np.fft.rfft((x - x.mean()) * w, flicker.PAD * W)) / w.sum()
        rows.append(bins_of(fr, A, fps))
    return np.asarray(rows)


def reading(f, fps, lines=(), top=None, scale=None, windows=True):
    """The stage's spectral reading of one curve (an object's, or a background aperture's in the object's brightness
    `scale`), with the stage's own functions: {hz, amplitude, stands, edge, codec (the codec line it is at, or None) --
    `flicker.peak`; ratio, needed95, needed99, continuum_p, continuum_hz -- `flicker.continuum` up to `top`; standing
    (the ratio over its drawn null's 99th centile: 1 is the 1 % line, whatever the curve's length and continuum); bins
    (the strongest amplitude in each GRID bin over the whole stretch); windows (the same in each 2-s window), frames}."""
    f = np.asarray(f, float)
    r = flicker.deviation(f, fps, scale)
    pk = flicker.peak(f, fps, lines, scale, err=False)
    top = top or flicker.TOP * fps / 2
    cn = flicker.continuum(r, fps, top=top)
    fr, F, band, wsum, rms = flicker._spec(r, fps)
    A = 2 * np.abs(F) / wsum
    out = dict(hz=pk["hz"], amplitude=pk["amplitude"], stands=pk["stands"], edge=bool(pk["edge"]),
               codec=pk["at_the_codec_line_hz"], rms=rms, ratio=cn["ratio"], needed95=cn["needed95"], needed99=cn["needed99"],
               continuum_p=cn["p"], continuum_hz=cn["hz"],
               standing=(cn["ratio"] / cn["needed99"]) if cn["ratio"] is not None and cn["needed99"] else None,
               bins=bins_of(fr, A, fps), frames=len(f), top=float(top))
    if windows:
        out["windows"] = window_bins(r, fps)
    return out


def offset_px(name, fields):
    """How far a background aperture sits from the middle of the track it goes with, in px: an aperture of a member's own
    is named by its offset; the four about the track seen longest are named by BACKGROUND's directions and sit at
    `fields["background_px"]` (or at `fields["background_offsets"]` where they were moved clear of other tracks)."""
    tail = name.rsplit(" ", 1)[-1]
    try:
        dx, dy = (float(v) for v in tail.split(","))
    except ValueError:
        return None
    if name.startswith("background of "):
        return float(math.hypot(dx, dy))
    moved = fields.get("background_offsets")
    if moved:
        return float(np.median([math.hypot(a, b) for a, b in moved]))
    return float(fields.get("background_px") or 25)


def video_reading(folder, row_of=None, windows=True, say=print):
    """Every curve of one video's objects (a batch's video folder, read only), read as the stage read it: a list of rows,
    each a curve -- an object's (or a member's) or a background aperture's -- with its object's facts and its `reading`,
    and {row index: window bins} beside it. `row_of` gives the batch table's row of each object folder (its label,
    whether it is a group), where known."""
    from . import report
    folder = Path(folder)
    rows, wins = [], {}
    for ob in sorted(folder.glob("object-*"), key=lambda p: int(p.name.split("-")[1]) if p.name.split("-")[1].isdigit() else 0):
        cases, csvs = sorted(ob.glob("*_case.json")), sorted(ob.glob("*_flicker.csv"))
        if not cases or not csvs:
            continue
        d = json.loads(cases[0].read_text(encoding="utf-8"))
        fl = (d.get("stages") or {}).get("flicker") or {}
        F = fl.get("fields") or {}
        if not F.get("curves"):
            continue
        fps = float((d.get("clip") or {}).get("fps") or 0)
        lines = ((F.get("codec") or {}).get("lines_hz")) or []
        top = F.get("top_hz") or flicker.TOP * fps / 2
        ns, cols = read_csv(csvs[0])
        grey = not any(v for k, c in cols.items() if k.endswith(" red") for v in c if v is not None)
        tb = (row_of or {}).get(ob.name) or {}
        named = {n for n, b in report.bird_beats(F).items() if not b.get("shaken")}
        pic = F.get("pictures") or {}
        base = dict(folder=folder.name, object=ob.name, video=tb.get("id"), label=tb.get("label"),
                    several=tb.get("several"), fps=fps, width=(d.get("clip") or {}).get("width"),
                    height=(d.get("clip") or {}).get("height"), grey=grey, held=pic.get("held"), cadence=pic.get("cadence"),
                    lines=lines, top=float(top), rule=F.get("rule"), dark=bool(tb.get("dark") in ("yes", "True", True)))
        got = as_judged(F, ns, cols, fps)
        levels = {c["name"]: c["level"] for c in got if c["kind"] == "object"}
        ap = F.get("aperture_px") or {}
        for c in got:
            own = c["owner"]
            R = float(ap.get(own) or flicker.APERTURE) if isinstance(ap, dict) else float(ap or flicker.APERTURE)
            lev = levels.get(own)
            rd = reading(c["curve"], fps, lines, top, c["scale"], windows=windows)
            w = rd.pop("windows", None)
            row = dict(base, name=c["name"], kind=c["kind"], owner=own, first=c["frames"][0], last=c["frames"][1],
                       aperture_px=R, level=lev, contrast=(lev / (math.pi * R * R)) if lev else None, **rd)
            row["bins"] = [None if not np.isfinite(v) else float(v) for v in rd["bins"]]
            if c["kind"] == "background":
                f, sc = c["curve"], c["scale"]
                row.update(scale=sc, offset_px=offset_px(c["name"], F), median_share=float(np.median(f) / sc),
                           occupied=float(np.mean(f >= flicker.DROP * sc)),
                           stage_hz=(F["curves"].get(c["name"]) or {}).get("hz"),
                           stage_amplitude=(F["curves"].get(c["name"]) or {}).get("amplitude"),
                           in_group_set=bool(len(F.get("tracks") or []) > 1 and not c["name"].startswith("background of ")))
            else:
                b = (F.get("beat") or {}).get(c["name"]) or {}
                cn = (F.get("continuum") or {}).get(c["name"]) or {}
                row.update(stage_hz=(F["curves"].get(c["name"]) or {}).get("hz"),
                           stage_amplitude=(F["curves"].get(c["name"]) or {}).get("amplitude"),
                           beat_hz=b.get("hz"), beat_amplitude=b.get("amplitude"), beat_source=b.get("source"),
                           beat_first=b.get("first"), beat_last=b.get("last"), comes_back=b.get("comes_back"),
                           whole_passes=b.get("whole_passes"), own=c["name"] in (F.get("strong") or []),
                           named=c["name"] in named, shaken=bool(b.get("shaken")),
                           reported_continuum_p=cn.get("p"), reported_ratio=cn.get("ratio"), reported_needed99=cn.get("needed99"),
                           reported_frames=cn.get("frames"))
            if w is not None and len(w):
                wins[len(rows)] = w
            rows.append(row)
    return rows, wins


def _plain(x):
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, (np.floating,)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, float):
        return None if not math.isfinite(x) else x
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def table_rows(batch_dir):
    """{video folder: {object folder: the batch table's row}} from a batch's `batch.tsv`."""
    out = {}
    p = Path(batch_dir) / "batch.tsv"
    if not p.exists():
        return out
    with open(p, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            if r.get("object"):
                out.setdefault(r["folder"], {})[f"object-{r['object']}"] = r
    return out


def read_unit(batch_dir, folder, out_dir, windows=True, say=print):
    """One video's readings, written to OUT_DIR/<folder>.json.gz (the rows) and <folder>_windows.npz (window bins by row);
    nothing is written in the batch's folder. Returns the number of rows."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, wins = video_reading(Path(batch_dir) / folder, table_rows(batch_dir).get(folder), windows=windows, say=say)
    tmp = out_dir / f".{folder}.json.gz.part"
    with gzip.open(tmp, "wt", encoding="utf-8") as fh:
        json.dump(_plain(rows), fh)
    if wins:
        np.savez_compressed(out_dir / f"{folder}_windows.npz", **{f"r{k}": v.astype(np.float32) for k, v in wins.items()})
    tmp.rename(out_dir / f"{folder}.json.gz")
    return len(rows)


# ---- the model --------------------------------------------------------------------------------------------------------
def load(readings_dir, with_windows=False):
    """Every row `read_unit` wrote into `readings_dir`: (rows, windows by (folder, row index) or None)."""
    rows, wins = [], {} if with_windows else None
    for p in sorted(Path(readings_dir).glob("*.json.gz")):
        if p.name.startswith("noise_"):                 # the model's own files, where it was written beside them
            continue
        folder = p.name[:-len(".json.gz")]
        got = json.load(gzip.open(p, "rt", encoding="utf-8"))
        for i, r in enumerate(got):
            r["row"] = i
        rows += got
        if with_windows:
            w = Path(readings_dir) / f"{folder}_windows.npz"
            if w.exists():
                z = np.load(w)
                for k in z.files:
                    wins[(folder, int(k[1:]))] = z[k]
    return rows, wins


def dropped_because(r, same_as=None):
    """Why a background aperture's curve is not a sample of the background, or None. Each rule is written down and uses
    the stage's own numbers; none is a look at the curve's spectrum:

    - "the set about a group's member seen longest": in a group (more than one track) the four apertures about the
      member seen longest are placed without regard to its fellows (a batch gives the stage no tracks to avoid), so they
      can sit on members; each member's own four are placed clear of every fellow (`flicker.clear_offsets`) and are kept.
    - "something as bright as the object in it": the aperture's own brightness reaches flicker.DROP of the object's (the
      share under which the stage calls the object lost against what is behind it) on more than flicker.LOST_MAX of its
      frames (the share past which the stage looks for no beat) -- another object, the object's own glare, a bright
      part of the scene passing.
    - "another row's track": the object's row was followed onto another row's track (`same_as`, method section 54), so
      its apertures are that row's again, frame for frame.
    """
    if r.get("in_group_set"):
        return "the set about a group's member seen longest"
    if (r.get("occupied") or 0.0) > flicker.LOST_MAX:
        return "something as bright as the object in it"
    if same_as and same_as.get((r["folder"], r["object"])):
        return "another row's track"
    return None


# ---- the tail: peaks over a threshold (E24) --------------------------------------------------------------------------
def gpd_fit(x):
    """A generalised Pareto fitted by maximum likelihood to the excesses `x` (all > 0): (shape xi, scale sigma), with the
    shape held to -0.5..1 (past -0.5 the likelihood's regularity fails; past 1 there is no mean). scipy's own fit, its
    location held at nought."""
    from scipy import stats
    x = np.asarray(x, float)
    if len(x) < 10:
        return None
    xi, _, sigma = stats.genpareto.fit(x, floc=0.0)
    return float(min(max(xi, -0.5), 1.0)), float(sigma)


def gpd_sf(x, xi, sigma):
    """The generalised Pareto's survival function at excess `x`."""
    x = np.asarray(x, float)
    if abs(xi) < 1e-9:
        return np.exp(-x / sigma)
    z = 1 + xi * x / sigma
    return np.where(z > 0, np.power(np.maximum(z, 1e-300), -1 / xi), 0.0)


def tail_fit(sample, u):
    """Peaks over the threshold `u`: {u, n (the sample), above (how many exceed u), xi, sigma, largest} -- the excesses'
    generalised Pareto -- or None where fewer than 10 exceed it."""
    s = np.asarray(sample, float)
    s = s[np.isfinite(s)]
    ex = s[s > u] - u
    got = gpd_fit(ex)
    if got is None:
        return None
    return dict(u=float(u), n=int(len(s)), above=int(len(ex)), xi=got[0], sigma=got[1], largest=float(s.max()))


def tail_p(value, sample, fit):
    """The chance a sample's member stands at `value` or over: the empirical share (k + 1) / (n + 1) at or under the
    threshold, and past it the threshold's own share times the fitted Pareto's survival -- so that a value past the
    sample's largest still has a p, from the fit."""
    s = np.asarray(sample, float)
    s = s[np.isfinite(s)]
    n = len(s)
    if value is None or not np.isfinite(value) or n == 0:
        return None
    if fit is None or value <= fit["u"]:
        return float((np.sum(s >= value) + 1) / (n + 1))
    return float((fit["above"] / n) * gpd_sf(value - fit["u"], fit["xi"], fit["sigma"]))


def stability(sample, quantiles=(0.80, 0.85, 0.90, 0.925, 0.95, 0.96, 0.97, 0.975, 0.98, 0.985, 0.99), B=200, seed=0, groups=None):
    """The threshold's stability plot in numbers: at each candidate threshold (a quantile of the sample), the fitted shape
    xi and the modified scale sigma - xi u (both constant above the threshold where a Pareto holds), each with a 95 %
    interval from resampling -- the sample's `groups` (its videos) where given, else its members. [{q, u, above, xi, xi_lo,
    xi_hi, sigma_star, ss_lo, ss_hi}]."""
    s = np.asarray(sample, float)
    ok = np.isfinite(s)
    s = s[ok]
    g = None if groups is None else np.asarray(groups)[ok]
    rng = np.random.default_rng(seed)
    keys = None if g is None else np.unique(g)
    idx = None if g is None else {k: np.flatnonzero(g == k) for k in keys}
    out = []
    for qq in quantiles:
        u = float(np.quantile(s, qq))
        f = tail_fit(s, u)
        if f is None:
            continue
        xs, ss = [], []
        for _ in range(B):
            if keys is None:
                t = s[rng.integers(0, len(s), len(s))]
            else:
                t = s[np.concatenate([idx[k] for k in keys[rng.integers(0, len(keys), len(keys))]])]
            ff = tail_fit(t, u)
            if ff is not None:
                xs.append(ff["xi"])
                ss.append(ff["sigma"] - ff["xi"] * u)
        out.append(dict(q=qq, u=u, above=f["above"], xi=f["xi"], xi_lo=float(np.percentile(xs, 2.5)) if xs else None,
                        xi_hi=float(np.percentile(xs, 97.5)) if xs else None, sigma_star=f["sigma"] - f["xi"] * u,
                        ss_lo=float(np.percentile(ss, 2.5)) if ss else None, ss_hi=float(np.percentile(ss, 97.5)) if ss else None))
    return out


# ---- the false discovery rate over the pass (D7) ---------------------------------------------------------------------
def bh(p, q):
    """Benjamini-Hochberg (1995): which of the p-values `p` are discoveries at false discovery rate `q` (a boolean array),
    and the adjusted p-values (q-values). None counts as 1."""
    p = np.array([1.0 if v is None or not np.isfinite(v) else float(v) for v in p])
    m = len(p)
    if m == 0:
        return np.zeros(0, bool), np.zeros(0)
    o = np.argsort(p, kind="stable")
    ranked = p[o] * m / np.arange(1, m + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(m)
    out[o] = np.minimum(adj, 1.0)
    return out <= q, out


def by(p, q):
    """Benjamini-Yekutieli (2001): Benjamini-Hochberg at q / c(m), c(m) = 1 + 1/2 + ... + 1/m, which holds the false
    discovery rate under any dependence among the tests (the objects of one video share its frames and its noise)."""
    m = len([v for v in p])
    c = float(np.sum(1.0 / np.arange(1, m + 1))) if m else 1.0
    found, adj = bh(p, q / c)
    return found, np.minimum(adj * c, 1.0)


def per_video(p, video):
    """One test a video: its smallest p, corrected for how many objects it had (Bonferroni: m times the smallest, at most
    1, which holds whatever their dependence). Returns ({video: (p, m, index of the smallest)})."""
    out = {}
    for i, (v, x) in enumerate(zip(video, p)):
        x = 1.0 if x is None or not np.isfinite(x) else float(x)
        best = out.get(v)
        if best is None:
            out[v] = [x, 1, i]
        else:
            best[1] += 1
            if x < best[0]:
                best[0], best[2] = x, i
    return {v: (min(1.0, b[0] * b[1]), b[1], b[2]) for v, b in out.items()}


# ---- strata and the reading for an object ----------------------------------------------------------------------------
LENGTHS = ((60, 150, "60-149 frames"), (150, 300, "150-299 frames"), (300, None, "300 frames or more"))   # the controls
#   harness's edges (method section 44), fixed before the corpus was read
APERTURES = ((None, 4.01, "4-px disc"), (4.01, 6.01, "6-px capped disc"), (6.01, None, "wider disc"))      # the stage's
#   own three kinds of aperture (`flicker.sized`): APERTURE for a point, POINT_DISC for a capped one, larger for a wide thing
CONTRASTS = ((None, 20.0, "contrast under 20"), (20.0, 40.0, "contrast 20-40"), (40.0, None, "contrast 40 or more"))
#   grey levels a pixel of the aperture over the ring: the controls harness's top edge (40), and 20 between, round numbers
#   fixed on the 66 videos outside the held-out third (2026-11-15), where even in grey levels the backgrounds of objects
#   under 20 run at 0.43 at the median against 1.0 from 45 up: a faint object is found only where the scene is quiet
FALLBACK = (("rate", "contrast", "aperture", "length"), ("rate", "contrast", "aperture"), ("rate", "contrast"))
#   the strata a reading is held in, in turn, until one has STRATUM_MIN_VIDEOS videos: the factors dropped in the order of
#   their measured effect on the backgrounds' median in grey levels, smallest first (length 1.25 times, aperture 1.6,
#   contrast 2.3; the frame rate is kept: 96 % of the objects are at about 30 a second)
STRATUM_MIN_VIDEOS = 10  # a stratum of fewer videos than this gives its count and no centile (a judgement, as the
#   controls harness's STRATUM_MIN of ten tracks is): the backgrounds of one video are one draw of a sensor and a scene
BOOT = 1000              # resamples of the reference videos for a centile's interval (E10)


def rate_class(fps):
    """The frame rate's stratum: "about 30 a second" (29-31; 96 % of the pass's objects), else "another rate"."""
    return "about 30 a second" if fps and 29.0 <= fps <= 31.0 else "another rate"


def length_class(frames):
    for lo, hi, name in LENGTHS:
        if frames >= lo and (hi is None or frames < hi):
            return name
    return "under 60 frames"


def aperture_class(r):
    for lo, hi, name in APERTURES:
        if (lo is None or r > lo) and (hi is None or r <= hi):
            return name
    return APERTURES[-1][2]


def contrast_class(c):
    for lo, hi, name in CONTRASTS:
        if c is not None and (lo is None or c >= lo) and (hi is None or c < hi):
            return name
    return "contrast unknown"


def grey(amplitude, contrast):
    """A line's amplitude in grey levels a pixel of the aperture: its share of the object's brightness times the
    object's contrast (its brightness over the ring, a pixel). A background aperture's share is of its object's
    brightness, so this takes the object's brightness out: what the scene and the sensor make, in their own units."""
    if amplitude is None or contrast is None:
        return None
    return float(amplitude) * float(contrast)


def bin_of(hz):
    """The GRID bin a frequency falls in, or None outside the grid."""
    if hz is None or hz < GRID[0] or hz >= GRID[-1] + GRID_STEP:
        return None
    return int((hz - GRID[0]) // GRID_STEP)


class Model:
    """The corpus noise model: the usable background apertures of a pass (`build`), and the readings it gives. `bg` is a
    list of background rows (`video_reading`'s, with `video` set), `wins` their window bins by (folder, row) where kept."""

    def __init__(self, bg, wins=None, fit=None, meta=None):
        self.bg = bg
        self.wins = wins or {}
        self.meta = meta or {}
        self.video = np.array([r["folder"] for r in bg])
        self.rate = np.array([rate_class(r["fps"]) for r in bg])
        self.length = np.array([length_class(r["frames"]) for r in bg])
        self.aperture = np.array([aperture_class(r["aperture_px"]) for r in bg])
        self.contrast = np.array([contrast_class(r.get("contrast")) for r in bg])
        G = np.array([[np.nan if v is None else v for v in r["bins"]] for r in bg]) if bg else np.zeros((0, len(GRID)))
        con = np.array([r["contrast"] or np.nan for r in bg])
        self.grey_bins = G * con[:, None]
        st = np.array([np.nan if r.get("standing") is None else r["standing"] for r in bg])
        self.power = st ** 2
        self.fit = fit

    # -- which backgrounds a reading is held against
    def cell(self, fps, frames, aperture_px, contrast, keys=FALLBACK[0], windows=False, leave=None):
        """The mask of backgrounds in an object's stratum on the factors `keys` -- its frame rate's class, its contrast's,
        its aperture's and its length's (never for a window's reading: every window is WINDOW_S long) -- its own video's
        left out (`leave`)."""
        m = np.ones(len(self.bg), bool)
        if "rate" in keys:
            m &= self.rate == rate_class(fps)
        if "contrast" in keys:
            m &= self.contrast == contrast_class(contrast)
        if "aperture" in keys:
            m &= self.aperture == aperture_class(aperture_px)
        if "length" in keys and not windows:
            m &= self.length == length_class(frames)
        if leave is not None:
            m &= self.video != leave
        return m

    def centile(self, hz, amplitude, contrast, fps, frames, aperture_px, windows=False, leave=None, boot=BOOT, seed=0):
        """An object's beat as a centile of the backgrounds' at its frequency in its stratum (S3): {centile, lo, hi (95 %
        over resamples of the reference videos), grey (the beat in grey levels a pixel), level50, level90, level99 (the
        backgrounds' centiles at that bin, grey levels a pixel), apertures, videos, stratum, why (where no centile)}.
        Each video weighs the same: the centile is the mean over the reference videos of the share of each one's
        backgrounds (or their windows) under the beat, so a video with a hundred apertures counts as one with four.
        `windows`: the beat was read in a 2-s window, so it is held against the backgrounds' windows."""
        full = dict(rate=rate_class(fps), contrast=contrast_class(contrast), aperture=aperture_class(aperture_px),
                    length=None if windows else length_class(frames))
        g = grey(amplitude, contrast)
        j = bin_of(hz)
        out = dict(centile=None, lo=None, hi=None, grey=g, level50=None, level90=None, level99=None, apertures=0, videos=0,
                   stratum=None, windows=bool(windows), bin_hz=None if j is None else [float(GRID[j]), float(GRID[j] + GRID_STEP)],
                   why=None)
        if g is None or j is None:
            out["why"] = "no beat to place, or its frequency is off the grid"
            return out
        for keys in FALLBACK:
            if windows and "length" in keys and tuple(k for k in keys if k != "length") in FALLBACK:
                continue                                     # a window has no length class: the next is the same cell
            m = self.cell(fps, frames, aperture_px, contrast, keys, windows, leave)
            vals = {}
            for i in np.flatnonzero(m):
                r = self.bg[i]
                if windows:
                    w = self.wins.get((r["folder"], r["row"]))
                    if w is None or not len(w):
                        continue
                    x = np.asarray(w)[:, j] * (r["contrast"] or np.nan)
                else:
                    x = np.array([self.grey_bins[i, j]])
                x = x[np.isfinite(x)]
                if len(x):
                    vals.setdefault(r["folder"], []).append(x)
            vals = {v: np.concatenate(x) for v, x in vals.items()}
            out.update(apertures=int(m.sum()), videos=len(vals), stratum={k: full[k] for k in keys if full.get(k) is not None})
            if len(vals) >= STRATUM_MIN_VIDEOS:
                break
        if len(vals) < STRATUM_MIN_VIDEOS:
            out["why"] = f"{len(vals)} videos in its stratum, under the {STRATUM_MIN_VIDEOS} a centile needs"
            return out
        keys = sorted(vals)
        under = np.array([np.mean(vals[k] < g) for k in keys])
        out["centile"] = float(100 * under.mean())
        allv = np.concatenate([vals[k] for k in keys])
        wts = np.concatenate([np.full(len(vals[k]), 1.0 / len(vals[k])) for k in keys])
        o = np.argsort(allv)
        cw = np.cumsum(wts[o]) / wts.sum()
        for p, key in ((0.5, "level50"), (0.9, "level90"), (0.99, "level99")):
            out[key] = float(allv[o][min(len(o) - 1, int(np.searchsorted(cw, p)))])
        rng = np.random.default_rng(seed)
        bs = under[rng.integers(0, len(keys), (boot, len(keys)))].mean(axis=1)
        out["lo"], out["hi"] = float(100 * np.percentile(bs, 2.5)), float(100 * np.percentile(bs, 97.5))
        return out

    # -- the p of a line, past the corpus's largest by the fitted tail (E24)
    def reference_power(self, leave=None):
        m = np.isfinite(self.power)
        if leave is not None:
            m &= self.video != leave
        return self.power[m], self.video[m]

    def p_cautious(self, standing, leave=None):
        """`p_value` with the tail's shape at the upper end of its 95 % interval over videos (the threshold's row of the
        stability plot) and its modified scale held: the heaviest tail the backgrounds allow, so the largest p they allow
        past their largest. Where it and `p_value` part by more than ten times, the tail is extrapolated past what it can
        be trusted for. Equal to `p_value` at or under the threshold."""
        th = (self.meta or {}).get("threshold")
        if standing is None or not np.isfinite(standing) or not th or th.get("xi_hi") is None or self.fit is None:
            return self.p_value(standing, leave)
        s, _ = self.reference_power(leave)
        u = float(np.quantile(s, self.fit["q"]))
        f = tail_fit(s, u)
        if f is None:
            return self.p_value(standing, leave)
        xi = max(f["xi"], th["xi_hi"])
        sigma = (f["sigma"] - f["xi"] * u) + xi * u
        return tail_p(standing ** 2, s, dict(f, xi=xi, sigma=max(sigma, 1e-9)))

    def p_value(self, standing, leave=None, fit=None):
        """The chance a background aperture's line stands as high over its own continuum as this one (`standing`, the
        ratio over its drawn null's 99th centile), squared to a power: the backgrounds' own share at or under the tail's
        threshold, the fitted Pareto past it (`tail_p`). `leave` a video whose backgrounds are left out (an object's
        own); the fit is then made again without them, at the same quantile."""
        if standing is None or not np.isfinite(standing):
            return None
        s, _ = self.reference_power(leave)
        f = fit
        if f is None and self.fit is not None:
            f = self.fit if leave is None else tail_fit(s, float(np.quantile(s, self.fit["q"])))
            if f is not None and "q" not in f:
                f["q"] = self.fit["q"]
        return tail_p(standing ** 2, s, f)


# ---- building the model from a pass's readings -----------------------------------------------------------------------
QUANTILES = (0.80, 0.85, 0.90, 0.925, 0.95, 0.96, 0.97, 0.975, 0.98, 0.985, 0.99)   # the thresholds the stability plot tries


def threshold(stab):
    """The tail's threshold from its stability plot, by a rule and not by eye: the lowest candidate whose fitted shape
    is inside the 95 % interval of the shape at every higher candidate, and whose interval holds every higher candidate's
    point (where a Pareto holds above u, the shape is the same above it; Coles 2001, section 4.3.4). The highest
    candidate where none is."""
    for i, s in enumerate(stab):
        rest = stab[i + 1:]
        if all(r["xi_lo"] is not None and r["xi_lo"] <= s["xi"] <= r["xi_hi"] for r in rest) and \
                all(s["xi_lo"] <= r["xi"] <= s["xi_hi"] for r in rest):
            return s
    return stab[-1] if stab else None


def same_as_of(batch_dir):
    """{(video folder, object folder): True} for the batch table's rows followed onto another row's track."""
    return {(f, o): bool(r.get("same_as")) for f, objs in table_rows(batch_dir).items() for o, r in objs.items()}


def usable(rows, batch_dir):
    """(kept background rows, {reason: count}) by `dropped_because`."""
    sa = same_as_of(batch_dir)
    kept, why = [], {}
    for r in rows:
        if r["kind"] != "background":
            continue
        w = dropped_because(r, sa)
        if w is None:
            kept.append(r)
        else:
            why[w] = why.get(w, 0) + 1
    return kept, why


def build(readings_dir, batch_dir, choose_on=None, only=None, seed=0):
    """The model from a pass's readings: the usable backgrounds (of the videos in `only`, all where None), the tail's
    threshold chosen by `threshold` on the backgrounds of the videos in `choose_on` (all where None) and the Pareto
    fitted at that quantile to all the model's backgrounds. Returns (Model, rows of every curve)."""
    rows, wins = load(readings_dir, with_windows=True)
    kept, why = usable(rows, batch_dir)
    if only is not None:
        kept = [r for r in kept if r["folder"] in only]
    m = Model(kept, wins)
    pick = np.isfinite(m.power) if choose_on is None else np.isfinite(m.power) & np.isin(m.video, list(choose_on))
    stab = stability(m.power[pick], QUANTILES, groups=m.video[pick], seed=seed)
    th = threshold(stab)
    s, _ = m.reference_power()
    fit = tail_fit(s, float(np.quantile(s, th["q"]))) if th else None
    if fit is not None:
        fit["q"] = th["q"]
    m.fit = fit
    m.meta = dict(curves=len(rows), backgrounds=sum(1 for r in rows if r["kind"] == "background"), kept=len(kept),
                  dropped=why, videos=len(set(m.video)), stability=stab, threshold=th,
                  chosen_on=None if choose_on is None else sorted(choose_on), only=None if only is None else sorted(only), fit=fit)
    return m, rows


def pass_pvalues(model, rows, floor_runs=flicker.CONTINUUM_RUNS, centiles=True):
    """Every object's (member's) p of a line over the pass, three ways: `p_corpus` (`Model.p_value`, its own video's
    backgrounds left out), `p_drawn` (the drawn continuum null over its whole stretch, `reading`'s), and `p_stage` (the
    stage's own continuum p, over the stretch it reported the beat from); a drawn null's p of nought is taken as
    1 / (runs + 1), the least its runs can say. [{folder, object, name, label, video, named, own, ...}]."""
    least = 1.0 / (floor_runs + 1)
    out = []
    for r in rows:
        if r["kind"] != "object":
            continue
        pc = model.p_value(r.get("standing"), leave=r["folder"])
        pk = model.p_cautious(r.get("standing"), leave=r["folder"])
        pd = r.get("continuum_p")
        ps = r.get("reported_continuum_p")
        c = None
        if centiles and r.get("beat_hz") is not None and r.get("beat_amplitude") is not None:
            win = bool(r.get("beat_source")) and not str(r["beat_source"]).startswith("the whole")
            n = (r["beat_last"] - r["beat_first"] + 1) if r.get("beat_first") is not None else r.get("frames")
            c = model.centile(r["beat_hz"], r["beat_amplitude"], r.get("contrast"), r.get("fps"), n, r.get("aperture_px"),
                              windows=win, leave=r["folder"], boot=200)
        out.append(dict(folder=r["folder"], object=r["object"], name=r["name"], video=r.get("video"), label=r.get("label"),
                        named=bool(r.get("named")), own=bool(r.get("own")), comes_back=r.get("comes_back"),
                        whole_passes=r.get("whole_passes"), hz=r.get("hz"), amplitude=r.get("amplitude"),
                        standing=r.get("standing"), frames=r.get("frames"), contrast=r.get("contrast"),
                        aperture_px=r.get("aperture_px"), beat_hz=r.get("beat_hz"), beat_amplitude=r.get("beat_amplitude"),
                        beat_source=r.get("beat_source"), centile=c, p_corpus=pc, p_cautious=pk,
                        p_drawn=None if pd is None else max(pd, least), p_stage=None if ps is None else max(ps, least)))
    return out


def by_row(pv, key):
    """Each row of the table (a video's object: one curve, or a group's members) its p: the members' smallest, times
    how many members have one (Bonferroni, whatever their dependence). {(folder, object): (p, members, best member)}."""
    got = {}
    for r in pv:
        x = r.get(key)
        if x is None:
            continue
        k = (r["folder"], r["object"])
        got.setdefault(k, []).append((x, r["name"]))
    return {k: (min(1.0, min(v)[0] * len(v)), len(v), min(v)[1]) for k, v in got.items()}


def fdr_over(pv, key, qs=(0.05, 0.10), only=None):
    """The false discovery rate over the pass's rows on the p `key`: {m, q: {bh: [rows], by: [rows], video: [videos]}},
    each row (folder, object), over the rows with a p (`only`: a set of video folders to keep)."""
    rows = by_row(pv, key)
    if only is not None:
        rows = {k: v for k, v in rows.items() if k[0] in only}
    keys = sorted(rows)
    p = [rows[k][0] for k in keys]
    out = dict(m=len(keys), videos=len({k[0] for k in keys}), p={f"{k[0]}/{k[1]}": rows[k][0] for k in keys})
    vids = per_video(p, [k[0] for k in keys])
    vk = sorted(vids)
    for q in qs:
        fb, _ = bh(p, q)
        fy, _ = by(p, q)
        fv, _ = bh([vids[v][0] for v in vk], q)
        out[str(q)] = dict(bh=[f"{keys[i][0]}/{keys[i][1]}" for i in np.flatnonzero(fb)],
                           by=[f"{keys[i][0]}/{keys[i][1]}" for i in np.flatnonzero(fy)],
                           video=[f"{v} ({keys[vids[v][2]][1]})" for v, ok in zip(vk, fv) if ok])
    return out


# ---- the model's files -----------------------------------------------------------------------------------------------
MODEL = "noise_model.json"             # the strata's levels by frequency, the tail's fit and its stability, the counts
BACKGROUNDS = "noise_backgrounds.json.gz"  # every usable background aperture's reading (what a centile is read against)
WINDOWS = "noise_windows.npz"          # their 2-s windows' bins
KEEP = ("folder", "object", "row", "name", "owner", "video", "fps", "frames", "aperture_px", "contrast", "hz",
        "amplitude", "standing", "ratio", "needed99", "continuum_p", "bins", "grey", "held", "dark", "lines", "top")


def levels(model, ps=(0.5, 0.9, 0.99)):
    """The backgrounds' centiles at every bin in every stratum a reading can be held in (FALLBACK's: the four factors,
    then without the length, then the frame rate and contrast alone), in grey levels a pixel, each video weighing the
    same: [{rate, contrast, aperture, length, apertures, videos, p: {50: [...], 90: [...], 99: [...]}}], `p` None for a
    stratum of under STRATUM_MIN_VIDEOS videos (the figure, and the table a report would read)."""
    out = []
    names = dict(rate=sorted(set(model.rate)), contrast=[n for *_, n in CONTRASTS], aperture=[n for *_, n in APERTURES],
                 length=[n for *_, n in LENGTHS])
    arrays = dict(rate=model.rate, contrast=model.contrast, aperture=model.aperture, length=model.length)
    import itertools
    for keys in FALLBACK:
        for combo in itertools.product(*[names[k] for k in keys]):
            m = np.ones(len(model.bg), bool)
            for k, v in zip(keys, combo):
                m &= arrays[k] == v
            vids = sorted(set(model.video[m]))
            row = dict(rate=None, contrast=None, aperture=None, length=None, apertures=int(m.sum()), videos=len(vids), p=None)
            row.update(dict(zip(keys, combo)))
            if len(vids) >= STRATUM_MIN_VIDEOS:
                G = model.grey_bins[m]
                vv = model.video[m]
                cnt = {v: np.sum(vv == v) for v in vids}
                w = np.array([1.0 / cnt[v] for v in vv])
                cols = {}
                for p in ps:
                    vals = []
                    for jj in range(len(GRID)):
                        x = G[:, jj]
                        ok = np.isfinite(x)
                        if len(set(vv[ok])) < STRATUM_MIN_VIDEOS:
                            vals.append(None)
                            continue
                        o = np.argsort(x[ok])
                        cw = np.cumsum(w[ok][o]) / w[ok].sum()
                        vals.append(float(x[ok][o][min(len(o) - 1, int(np.searchsorted(cw, p)))]))
                    cols[str(int(round(100 * p)))] = vals
                row["p"] = cols
            out.append(row)
    return out


def save(model, out_dir):
    """The model into `out_dir`: MODEL, BACKGROUNDS and WINDOWS. Returns the paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    bg = [{k: r.get(k) for k in KEEP} for r in model.bg]
    for b, r in zip(bg, model.bg):
        b["grey"] = grey(r.get("amplitude"), r.get("contrast"))
    with gzip.open(out / BACKGROUNDS, "wt", encoding="utf-8") as fh:
        json.dump(_plain(bg), fh)
    keys = {}
    for i, r in enumerate(model.bg):
        w = model.wins.get((r["folder"], r["row"]))
        if w is not None and len(w):
            keys[f"{r['folder']}|{r['row']}"] = np.asarray(w, np.float32)
    np.savez_compressed(out / WINDOWS, **keys)
    meta = dict(model.meta, grid_hz=[float(g) for g in GRID], grid_step_hz=GRID_STEP, levels=levels(model),
                strata=dict(rate=["about 30 a second", "another rate"], length=[n for *_, n in LENGTHS],
                            aperture=[n for *_, n in APERTURES], min_videos=STRATUM_MIN_VIDEOS),
                units=dict(levels="grey levels a pixel of the aperture: a line's amplitude as a share of the object's "
                                  "brightness times the object's contrast", power="(ratio / needed99) squared"))
    (out / MODEL).write_text(json.dumps(_plain(meta), indent=1), encoding="utf-8")
    return [out / MODEL, out / BACKGROUNDS, out / WINDOWS]


def open_model(model_dir):
    """A Model from the files `save` wrote."""
    d = Path(model_dir)
    meta = json.loads((d / MODEL).read_text(encoding="utf-8"))
    bg = json.load(gzip.open(d / BACKGROUNDS, "rt", encoding="utf-8"))
    wins = {}
    if (d / WINDOWS).exists():
        z = np.load(d / WINDOWS)
        for k in z.files:
            f, row = k.rsplit("|", 1)
            wins[(f, int(row))] = z[k]
    return Model(bg, wins, fit=meta.get("fit"), meta=meta)


def figure(model, path, points=()):
    """Strength against frequency, by stratum (the house style, `figures.save`): one panel for each class of contrast at
    about 30 frames a second, and in it, for each kind of aperture, the backgrounds' median (dashed) and 99th centile
    (solid) at every bin, over every length of track, in grey levels a pixel, each video weighing the same. `points`,
    [(contrast class, hz, grey)], are beats drawn over them in red (the pass's named birds). Returns the path, or None
    where no stratum has STRATUM_MIN_VIDEOS videos."""
    from matplotlib.lines import Line2D
    from . import figures
    plt = figures.setup()
    lev = [l for l in levels(model) if l["rate"] == "about 30 a second" and l["length"] is None and l["aperture"] and l["p"]]
    kinds = [n for *_, n in CONTRASTS if any(l["contrast"] == n for l in lev)]
    if not kinds:                                          # no stratum has STRATUM_MIN_VIDEOS videos: nothing to draw
        return None
    fig, axes = plt.subplots(len(kinds), 1, figsize=(figures.FigureSize.AIAA_FULL, 1.6 + 2.0 * len(kinds)), squeeze=False,
                             layout="constrained", sharex=True)
    colour = dict(zip([n for *_, n in APERTURES], (figures.BLUE, figures.AMBER, figures.PURPLE)))
    for ax, kind in zip(axes[:, 0], kinds):
        here = [l for l in lev if l["contrast"] == kind]
        for l in here:
            for key, lw, ls in (("50", 1.0, (0, (3, 2))), ("99", 1.8, "-")):
                y = np.array([np.nan if v is None else v for v in l["p"][key]])
                ax.plot(GRID_MID, y, color=colour[l["aperture"]], lw=lw, ls=ls)
        pts = [(h, g) for k, h, g in points if k == kind and g]
        if pts:
            ax.plot([q[0] for q in pts], [q[1] for q in pts], "o", color=figures.RED, ms=3.5, zorder=5)
        ax.set_yscale("log")
        lo, hi = ax.get_ylim()                             # from the decade under the lowest line, so the medians' level
        least = min(np.nanmin(np.asarray(g.get_ydata(), float)) for g in ax.get_lines())     # has a labelled tick under
        ax.set_ylim(min(lo, 10.0 ** np.floor(np.log10(least))), hi)                          # it in every panel
        ax.set_xlim(flicker.LOW, 15.0)
        vids = ", ".join(f"{l['aperture'].split(' ')[0]} {l['videos']}" for l in here)
        ax.set_title(f"{kind[0].upper() + kind[1:]} grey levels", loc="left")
        ax.set_title(f"videos: {vids}", loc="right")
    axes[-1, 0].set_xlabel("Beats a second (Hz)")
    fig.supylabel("Strength (grey levels a pixel)", fontweight="bold", fontsize=figures.LABEL_PT)
    keys = [Line2D([], [], color=colour[n], lw=1.8, label=n[0].upper() + n[1:]) for *_, n in APERTURES] + \
        [Line2D([], [], color="black", lw=1.0, ls=(0, (3, 2)), label="The backgrounds' median"),
         Line2D([], [], color="black", lw=1.8, label="Their 99th centile"),
         Line2D([], [], color=figures.RED, marker="o", ls="", ms=3.5, label="Beats named a bird")]
    fig.legend(handles=keys, loc="outside upper center", ncol=2)
    figures.save(fig, path, dpi=200, quiet=True)
    plt.close(fig)
    return str(path)


# ---- the command -----------------------------------------------------------------------------------------------------
def folders_with_curves(batch_dir):
    """The video folders of a batch that hold at least one object's flicker curves, in order."""
    return sorted({p.parent.parent.name for p in Path(batch_dir).glob("*/object-*/*_flicker.csv")})


def main(argv=None):
    from .clip import Stop
    from .report import emit, envelope, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(
        prog="mcdonald noise",
        description="What the background beside every object of a batch does. It builds a corpus noise model, places a "
                    "beat's strength as a centile of it, and gives a p-value past its largest. It also gives the false "
                    "discovery rate over the batch's objects. These are readings only: no call of the flicker stage reads them.")
    ap.add_argument("--read", metavar="BATCH", help="read every video folder of a `mcdonald batch` folder (read only) into --out")
    ap.add_argument("--unit", type=int, help="with --read: only the K-th video folder that has curves (0-based), for a job array")
    ap.add_argument("--build", metavar="DIR", help="make the model from the readings in DIR (needs --batch for its table); "
                                                   "written into --out, else DIR")
    ap.add_argument("--batch", metavar="BATCH", help="the batch folder the readings came from (its table says which rows "
                                                     "were followed onto another row's track)")
    ap.add_argument("--choose-on", metavar="FILE", help="with --build: video folders, one a line, the tail's threshold is "
                                                         "chosen on (the rest are not looked at for it)")
    ap.add_argument("--only", metavar="FILE", help="with --build: video folders, one a line, whose background apertures "
                                                    "make the model (the others' are left for checking it)")
    ap.add_argument("--model", metavar="DIR", help="a model's folder (what --build wrote): read a beat against it")
    ap.add_argument("--hz", type=float, help="with --model: the beat's frequency")
    ap.add_argument("--share", type=float, help="with --model: the beat's strength as a share of the brightness (0.12 is 12 %%)")
    ap.add_argument("--contrast", type=float, help="with --model: the object's brightness over its ring, grey levels a pixel")
    ap.add_argument("--frames", type=int, help="with --model: the frames the beat was read over")
    ap.add_argument("--fps", type=float, default=30.0, help="with --model: frames a second (default 30)")
    ap.add_argument("--aperture", type=float, default=flicker.APERTURE, help="with --model: the aperture's radius in pixels (default 4)")
    ap.add_argument("--window", action="store_true", help="with --model: the beat was read in a 2-s window, not over the whole track")
    ap.add_argument("--standing", type=float, help="with --model: the line's ratio over its own continuum divided by the "
                                                   "drawn null's 99th centile (`flicker.continuum`): its p from the tail")
    ap.add_argument("--leave", metavar="FOLDER", help="with --model: a video folder whose backgrounds are left out (the object's own)")
    ap.add_argument("--fdr", metavar="DIR", help="the false discovery rate over the batch's objects, from the model in DIR "
                                                  "and the readings it was built from (--readings, else DIR's own)")
    ap.add_argument("--readings", metavar="DIR", help="with --fdr: the readings folder")
    ap.add_argument("--q", default="0.05,0.10", help="with --fdr: the rates, comma-separated (default 0.05,0.10)")
    ap.add_argument("--out", metavar="DIR", help="where --read and --build write")
    ap.add_argument("--json", action="store_true", help="print the result as JSON on stdout")
    args = ap.parse_args(argv)
    inputs = inputs_of(args)
    files, res = [], {}
    with said_to_stderr(args.json) as lines:
        if args.read:
            if not args.out:
                raise Stop("--read needs --out, the folder the readings go to", 2)
            todo = folders_with_curves(args.read)
            if args.unit is not None:
                if not 0 <= args.unit < len(todo):
                    raise Stop(f"--unit {args.unit}: the batch has {len(todo)} video folders with curves", 2)
                todo = [todo[args.unit]]
            n = 0
            for f in todo:
                k = read_unit(args.read, f, args.out)
                n += k
                print(f"{f}: {k} curves read")
                files.append(str(Path(args.out) / f"{f}.json.gz"))
            res = dict(videos=len(todo), curves=n)
        elif args.build:
            if not args.batch:
                raise Stop("--build needs --batch, the batch folder the readings came from", 2)
            choose = None
            if args.choose_on:
                choose = {l.strip() for l in Path(args.choose_on).read_text(encoding="utf-8").splitlines() if l.strip()}
            only = None
            if args.only:
                only = {l.strip() for l in Path(args.only).read_text(encoding="utf-8").splitlines() if l.strip()}
            m, rows = build(args.build, args.batch, choose, only)
            files = [str(p) for p in save(m, args.out or args.build)]
            pts = [(contrast_class(r.get("contrast")), r["beat_hz"], grey(r.get("beat_amplitude"), r.get("contrast")))
                   for r in rows if r["kind"] == "object" and r.get("named") and r.get("beat_hz")]
            fig = figure(m, Path(args.out or args.build) / "noise_strength.png", pts)
            if fig:
                files.append(fig)
            else:
                print(f"no figure: no stratum has the {STRATUM_MIN_VIDEOS} videos a level needs")
            th, fit = m.meta["threshold"], m.fit
            print(f"{m.meta['kept']} background apertures kept of {m.meta['backgrounds']}, in {m.meta['videos']} videos; "
                  + "; ".join(f"{v} dropped: {k}" for k, v in m.meta["dropped"].items()))
            if fit:
                print(f"the tail: past the {100 * th['q']:g}th centile of the power over the continuum ({fit['u']:.3f}), "
                      f"{fit['above']} of {fit['n']}, a generalised Pareto of shape {fit['xi']:+.3f} and scale {fit['sigma']:.3f}; "
                      f"the largest {fit['largest']:.3f}")
            res = {k: m.meta[k] for k in ("curves", "backgrounds", "kept", "dropped", "videos", "threshold", "fit")}
        elif args.model:
            m = open_model(args.model)
            if args.hz is None or args.share is None or args.contrast is None or (args.frames is None and not args.window):
                raise Stop("--model needs --hz, --share, --contrast and --frames (or --window)", 2)
            c = m.centile(args.hz, args.share, args.contrast, args.fps, args.frames or 0, args.aperture, windows=args.window,
                          leave=args.leave)
            res = dict(centile=c)
            if c["centile"] is not None:
                print(f"a beat of {100 * args.share:.1f} % at {args.hz:.2f} Hz ({c['grey']:.2f} grey levels a pixel) is "
                      f"stronger than {c['centile']:.1f} % of the background lines at that frequency "
                      f"({c['lo']:.1f}-{c['hi']:.1f} %, from {c['videos']} videos)")
            else:
                print(f"no centile: {c['why']}")
            if args.standing is not None:
                res["p"] = m.p_value(args.standing, leave=args.leave)
                res["p_cautious"] = m.p_cautious(args.standing, leave=args.leave)
                past = bool(m.fit and args.standing ** 2 > m.fit["largest"])
                print(f"its line stands {args.standing:.2f} times as high over its own continuum as the drawn noise's 1 % line: "
                      f"p {res['p']:.2g} against the backgrounds")
                if past:
                    print(f"that is past the strongest background line, so the p comes from the fitted tail; the heaviest "
                          f"tail the backgrounds allow gives p {res['p_cautious']:.2g}")
        elif args.fdr:
            m = open_model(args.fdr)
            rows, _ = load(args.readings or args.fdr)
            pv = pass_pvalues(m, rows)
            qs = tuple(float(x) for x in args.q.split(","))
            res = dict(objects=len(pv), corpus=fdr_over(pv, "p_corpus", qs), cautious=fdr_over(pv, "p_cautious", qs),
                       drawn=fdr_over(pv, "p_drawn", qs), stage=fdr_over(pv, "p_stage", qs))
            if args.out:
                Path(args.out).mkdir(parents=True, exist_ok=True)
                t = Path(args.out) / "noise_pass.tsv"
                cols = ["folder", "object", "name", "video", "label", "named", "own", "comes_back", "whole_passes", "beat_hz",
                        "beat_amplitude", "beat_source", "contrast", "aperture_px", "frames", "standing", "centile", "centile_lo",
                        "centile_hi", "centile_stratum", "p_corpus", "p_cautious", "p_drawn", "p_stage"]
                with open(t, "w", newline="", encoding="utf-8") as fh:
                    w = csv.writer(fh, delimiter="\t")
                    w.writerow(cols)
                    for r in pv:
                        c = r.get("centile") or {}
                        r2 = dict(r, centile=c.get("centile"), centile_lo=c.get("lo"), centile_hi=c.get("hi"),
                                  centile_stratum="; ".join(f"{v}" for v in (c.get("stratum") or {}).values())
                                  + (" (2-s windows)" if c.get("windows") else ""))
                        w.writerow(["" if r2.get(k) is None else r2.get(k) for k in cols])
                files.append(str(t))
            for key in ("corpus", "cautious", "drawn", "stage"):
                r = res[key]
                print(f"{key}: {r['m']} rows of {r['videos']} videos; " + "; ".join(
                    f"q {q:g}: {len(r[str(q)]['bh'])} by Benjamini-Hochberg, {len(r[str(q)]['by'])} by Benjamini-Yekutieli, "
                    f"{len(r[str(q)]['video'])} videos" for q in qs))
        else:
            raise Stop("say what to do: --read BATCH, --build DIR, --model DIR or --fdr DIR (see --help)", 2)
    if args.json:
        emit(envelope("noise", inputs, None, files, dict(res, said=lines)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
