"""The background's motion as a dense field: where each layer of it is in the picture, and how the motion changes
across a layer (IDEAS.md A14; docs/method.md section 65). Asked for with `mcdonald layers --dense`.

`layers` reads the background with 128-px templates every 96 px: on a 1080p frame about 80 of them, enough for one
consensus or two. The same templates every 16 px are about 36 times as many, and on a graphics card a pair of them
costs a third of a second (about 45 cores' worth). That many readings say where in the picture each layer is, and
how the motion changes across one layer: a surface whose range changes across the picture (the sea toward its
horizon) moves faster where it is near.

The design is Jacob's (2026-11-16), from the measurements of 2026-11-15 (method section 65 has them):
- *What for, first:* the background's layers, and the parallax between and within them. Not the ring about a small
  object (no template large enough to be trusted fits there), nor a scene behind a sensor's pattern (no setting read
  it better than chance).
- *Templates:* 128 px every 16 px. Smaller templates match an empty pair too often under the keep rule.
- *Which matches count:* the keep rule of `forensics.good` (a peak of 0.5, 0.05 above the runner-up), and each clip
  held against two empty pairs -- its own second frame turned half a turn, and a frame of another clip -- with the
  peak floor raised until neither keeps more than NULL_SHARE of its templates.

A pair is read only where `layers` found its scene moving with a consensus; the field reaches MARGIN px past the
fastest motion `layers` saw in it. Nothing here changes any other number `layers` gives: the dense field has its own
cache, its own files (<tag>_dense.csv, <tag>_dense_map.csv, <tag>_dense.png) and its own entry in the fields.
"""
import csv
import hashlib
import math
from pathlib import Path

import numpy as np
from scipy import ndimage

from . import forensics as vf
from . import gpu
from . import layers

TEMPLATE, STRIDE = 128, 16
PAIRS = layers.PAIRS_DENSE   # pairs read, spread evenly over the pairs `layers` found moving with a consensus (24)
MARGIN = 24                # px: how far past the pair's fastest group (`layers`') the search reaches
NULL_SHARE = 0.01          # the most of an empty pair's templates a match rule may keep
FLOORS = tuple(round(0.50 + 0.01 * i, 2) for i in range(50))      # the peak floors tried, lowest first: 0.50 to 0.99
TOL = (6.0, 2.5)           # px over k frames: how near a row's shift must be to its layer's motion (`layers_of`'s)
# A layer needs as many rows as cover the area of the 8 templates a consensus of `layers` needs: at a stride of 16 px
# a picture holds (96 / 16)^2 = 36 rows where `layers` places one, so 288. A group of a few dozen rows is the size of
# one or two of today's templates (on PR144 a group of 31 rows near zero was the only false layer in 25 settings).
MIN_ROWS = int(8 * (layers.TEMPLATES[1] / STRIDE) ** 2)
# Neighbouring rows share most of their pixels: a 128-px template moved 16 px keeps seven-eighths of them. So the rows'
# scatter overstates how many independent readings there are by about (TEMPLATE / STRIDE)^2, and an error from the
# scatter is too small by about TEMPLATE / STRIDE: it is multiplied by that. Even so a pair's error is a floor: on PR144
# the readings of pairs 10 frames apart differ by 1.5 to 3.4 times it (method section 65). So the clip's own numbers take
# their errors from the pairs' scatter about their median (`summary`), which does not depend on this.
OVERLAP = TEMPLATE / STRIDE
ROUNDS = 6                 # a layer's rows found again about its fitted motion at most this many times
SEED = 6514                # the random phases' seed, with the pair's first frame: one pair, one empty frame


def read(clip, masks, rows, trk, how, lay, k, reach, made_from, n=PAIRS, null_from=None, procs=None, fresh=False,
         say=print, progress=None, stop=None):
    """The dense field of up to `n` pairs, its two empty pairs each, and the floor they set: (fields, per-pair records,
    kept rows with their layer). `how` and `lay` are `layers.measure`'s: how each pair was measured, and its layers;
    `made_from` names what `layers`' templates were measured from, `reach` its search. `null_from`: a video whose middle
    frame is the empty pair's other clip; without it, frame b with its phases drawn at random (`scrambled`)."""
    moving = sorted(a for a, l in lay.items() if how.get(a) == layers.MOVED and l.get("all") is not None)
    if not moving:
        return dict(template=TEMPLATE, stride=STRIDE, pairs=0, why="no pair of frames moved with a consensus: there is "
                    "no motion of the background to map"), [], np.zeros((0, len(MAP_COLS)))
    picked = [moving[i] for i in np.unique(np.linspace(0, len(moving) - 1, min(n, len(moving))).round().astype(int))]
    jobs = [(a, _reach(lay[a], reach)) for a in picked]
    other, other_is = (_other_frame(null_from, clip.H, clip.W) if null_from else (None, "frame b with its phases drawn at random"))
    key = repr((made_from, "dense", TEMPLATE, STRIDE, MARGIN, jobs, other_is, SEED, vf.PK_GAP))
    cache = clip.dir / f"bg_dense_k{k}_{clip.n0}_{clip.n1}_{hashlib.sha1(key.encode()).hexdigest()[:10]}.npz"
    if cache.exists() and not fresh:
        with np.load(cache) as z:              # closed at once: Windows cannot delete a folder holding an open .npz
            got = [(int(a), int(r), z[f"real_{a}"], z[f"turned_{a}"], z[f"other_{a}"]) for a, r in z["jobs"]]
        if "graphics card" in made_from:
            gpu.took_part(gpu.card())
        say(f"the dense field from {cache} (measured earlier; --fresh measures it again)")
    else:
        args = (other, clip.video, clip.dir, clip.n0, clip.n1, masks, rows, trk, k, reach, 9.0, False, None, layers.TEMPLATES)
        got = vf.pooled_or_on_card(layers._G, layers._read, [m for a, _ in jobs for m in (a, a + k)], procs, _pair, jobs,
                                   _init, args, 1, progress, stop, "Layers, dense", pixels=clip.W * clip.H)
        layers._G.pop("other", None)
        np.savez_compressed(cache, jobs=np.array([(a, r) for a, r, *_ in got], np.int64),
                            **{f"{name}_{a}": x for a, _, *fields in got for name, x in zip(("real", "turned", "other"), fields)})
    turned = np.vstack([t for _, _, _, t, _ in got])
    others = np.vstack([o for _, _, _, _, o in got])
    floor, at = floor_of(turned, others)
    fields = dict(template=TEMPLATE, stride=STRIDE, pairs=len(got), floor=floor, null_share=NULL_SHARE,
                  empty_pairs=dict(half_turn=at[0], other_clip=at[1], other_clip_is=other_is,
                                   templates=[int(len(turned)), int(len(others))]))
    if floor is None:
        fields["why"] = (f"the empty pairs keep more than {NULL_SHARE:.0%} of their templates at every peak floor up to "
                         f"{FLOORS[-1]}: no match of this clip's dense field can be told from chance")
        return fields, [], np.zeros((0, len(MAP_COLS)))
    records, kept_rows = [], []
    for a, r, real, _, _ in got:
        rec, mapped = pair_layers(real, floor)
        rec.update(a=a, t_s=round(float(clip.t(a)), 4), reach=r, today=int(lay[a]["n_good"]))
        records.append(rec)
        kept_rows.append(mapped)
    fields.update(summary(records, clip.fps / k, clip.H))
    return fields, records, np.vstack(kept_rows) if kept_rows else np.zeros((0, len(MAP_COLS)))


def _reach(l, reach):
    """A pair's search: MARGIN px past the faster of its groups (`layers_of`'s first, and its second where there is
    one), and never past `layers`' own."""
    first = float(np.hypot(*l["all"][0]))
    return int(min(reach, math.ceil(first + l.get("group_gap", 0.0) + MARGIN)))


def _init(other, *args):
    layers._init(*args)
    layers._G["other"] = other


def _pair(job):
    """One pair's dense field, and its two empty pairs: (a, reach, rows of SHIFT_COLS, then of each empty pair its
    templates' peak and runner-up). The empty pairs are matched with the same templates, masks and reach as the pair."""
    a, reach = job
    k = layers._G["k"]
    ga, ba = layers._bad(a)
    gb, bb = layers._bad(a + k)
    match = lambda g, b: vf.shift_field(ga, g, ba, b, a=a, tpl=TEMPLATE, stride=STRIDE, reach=reach)
    real = match(gb, bb)
    turned = match(np.ascontiguousarray(gb[::-1, ::-1]), np.ascontiguousarray(bb[::-1, ::-1]))
    other = layers._G.get("other")
    og, ob = other if other is not None else scrambled(gb, bb, a)
    return a, reach, real, turned[:, 5:7].copy(), match(og, ob)[:, 5:7].copy()


def scrambled(g, bad, seed):
    """Frame g with its phases drawn at random: the same power at every scale of detail and in every direction, and
    nothing in it where it was. The empty pair's second frame where no other clip is named: a scene with this clip's
    texture that is not this clip's scene, and none of its sensor's fixed pattern in place. Masked pixels are set to the
    rest's median first, so that a black bar or a caption does not lend the frame its own power; the mask is kept."""
    g = np.asarray(g, np.float64)
    clear = ~np.asarray(bad, bool)
    h = np.where(clear, g, float(np.median(g[clear])) if clear.any() else float(g.mean()))
    mean = float(h.mean())
    power = np.abs(np.fft.rfft2(h - mean))
    noise = np.fft.rfft2(np.random.default_rng([SEED, int(seed)]).standard_normal(h.shape))
    out = np.fft.irfft2(power * noise / np.maximum(np.abs(noise), 1e-300), s=h.shape) + mean
    return out.astype(np.float32), np.asarray(bad, bool)


def _other_frame(video, H, W):
    """((grey, mask), what it is) of another clip for the empty pair: its middle frame, masked as its own symbology is
    (`static_masks` over the 90 frames about it), cut to H x W about its middle, or set in the middle of an H x W
    frame masked where it does not reach."""
    from .clip import Clip
    video = Path(video)
    whole = Clip(video, extract=False)
    mid = max(1, whole.total // 2)
    c = Clip(video, None, max(1, mid - 45), min(whole.total, mid + 45))
    rgb = c.rgb(mid)
    g, m = vf.grey_of(rgb).astype(np.float32), vf.frame_mask(rgb, vf.static_masks(c), None, mid)
    out_g, out_m = np.full((H, W), float(np.median(g)), np.float32), np.ones((H, W), bool)
    h, w = min(H, c.H), min(W, c.W)
    sy, sx, ty, tx = (c.H - h) // 2, (c.W - w) // 2, (H - h) // 2, (W - w) // 2
    out_g[ty:ty + h, tx:tx + w] = g[sy:sy + h, sx:sx + w]
    out_m[ty:ty + h, tx:tx + w] = m[sy:sy + h, sx:sx + w]
    return (out_g, out_m), f"frame {mid} of {video.name}"


def kept_at(peaks, floor):
    """Of rows of (peak, runner-up), those the keep rule takes with its peak floor at `floor`."""
    peaks = np.asarray(peaks, float).reshape(-1, 2)
    return (peaks[:, 0] >= floor) & (peaks[:, 0] - peaks[:, 1] >= vf.PK_GAP)


def floor_of(*empty):
    """The lowest peak floor of FLOORS at which none of the `empty` pairs' templates (rows of peak and runner-up, a
    clip's pairs together) are kept more often than NULL_SHARE: (floor, [each one's share kept there]); (None, [each
    one's share at the highest floor]) where there is no such floor. An empty pair with no templates keeps none."""
    share = lambda p, f: float(kept_at(p, f).mean()) if len(p) else 0.0
    for f in FLOORS:
        at = [share(p, f) for p in empty]
        if max(at) <= NULL_SHARE:
            return f, at
    return None, [share(p, FLOORS[-1]) for p in empty]


MAP_COLS = "a x y dx dy pk layer".split()


def pair_layers(real, floor):
    """One pair's kept rows sorted into layers: the record of it (see `RECORD`) and its rows of MAP_COLS (layer 1 the
    larger, 2 the second, 0 neither). A layer is the largest group of rows whose shifts follow one motion that changes
    evenly across the picture (an affine field): seeded by `forensics.consensus`, then its rows found again about the
    fitted motion until they stop changing (`grow`). A second layer is sought among the rest, and is one only where
    MIN_ROWS follow it and its motion is 2 TOL[0] px or more from the first's where it is. Where there are two, each
    layer's motion is fitted again on its rows whose templates reach no row of the other layer (`inside`): a template
    that straddles the line between them reads a blend, and on a drawn shear beside a second layer those rows pulled the
    change across the first layer 3.5 % low."""
    keep = kept_at(real[:, 5:7], floor)
    f = real[keep]
    xy, v = f[:, 1:3], f[:, 3:5]
    label = np.zeros(len(f), int)
    rec = dict(placed=int(len(real)), kept=int(len(f)))
    first = grow(xy, v, f[:, 10:13] if f.shape[1] >= len(vf.SHIFT_COLS) else None, np.ones(len(f), bool))
    if first is not None:
        label[first["rows"]] = 1
        rest = label == 0
        second = grow(xy, v, f[:, 10:13] if f.shape[1] >= len(vf.SHIFT_COLS) else None, rest)
        if second is not None:
            at = xy[second["rows"]].mean(0)
            apart = float(np.hypot(*(motion_at(second, at) - motion_at(first, at))))
            if apart >= 2 * TOL[0]:
                label[second["rows"]] = 2
                first, second = (_inside(xy, v, label, lab, fitted) for lab, fitted in ((1, first), (2, second)))
                at = xy[label == 2].mean(0)
                apart = float(np.hypot(*(motion_at(second, at) - motion_at(first, at))))
                rec["second"] = dict(_layer_record(second), apart=apart, where=_where(xy[label == 2]))
        rec["first"] = dict(_layer_record(first), where=_where(xy[label == 1]))
        if "second" in rec:
            rec["neighbours"] = neighbours(xy, label)
    mapped = np.column_stack([f[:, 0:6], label]) if len(f) else np.zeros((0, len(MAP_COLS)))
    return rec, mapped


def _inside(xy, v, label, lab, fitted):
    """Layer `lab`'s motion fitted again on its rows whose templates reach no row of another layer: no such row within
    half a template, across or down (`fit`'s dict; the layer's own fit where under MIN_ROWS are left)."""
    ix = np.round(xy / STRIDE).astype(np.int64)
    ix -= ix.min(0)
    grid = np.zeros(tuple(ix.max(0)[::-1] + 1), bool)
    other = (label > 0) & (label != lab)
    grid[ix[other, 1], ix[other, 0]] = True
    reach = int(TEMPLATE // 2 // STRIDE)
    near = ndimage.binary_dilation(grid, np.ones((2 * reach + 1, 2 * reach + 1), bool)) if other.any() else grid
    keep = (label == lab) & ~near[ix[:, 1], ix[:, 0]]
    if keep.sum() < MIN_ROWS:
        return fitted
    refit = fit(xy[keep], v[keep])
    refit["rows"] = fitted["rows"]
    return refit


def grow(xy, v, w, among):
    """The largest group among the rows `among` whose shifts `v` follow one affine motion within TOL, as a dict (`fit`'s,
    with "rows": a boolean over all rows), or None where it has under MIN_ROWS."""
    idx = np.flatnonzero(among)
    if len(idx) < MIN_ROWS:
        return None
    c = vf.consensus(v[idx], TOL[0], TOL[1], MIN_ROWS, w=None if w is None else w[idx])
    if c is None:
        return None
    rows = np.zeros(len(v), bool)
    rows[idx[c[2]]] = True
    fitted = None
    for _ in range(ROUNDS):
        if rows.sum() < MIN_ROWS:
            return None
        fitted = fit(xy[rows], v[rows])
        near = np.abs(v - motion_at(fitted, xy))
        now = among & (near[:, 0] < TOL[0]) & (near[:, 1] < TOL[1])
        if np.array_equal(now, rows):
            break
        rows = now
    if rows.sum() < MIN_ROWS:
        return None
    fitted = fit(xy[rows], v[rows])
    fitted["rows"] = rows
    return fitted


def fit(xy, v):
    """The affine motion of rows at `xy` (template centres) with shifts `v`, by least squares about their centre: the
    shift there (px over k frames), its change across the picture (`grad`, px per 100 px: [[d dx/dx, d dx/dy], [d dy/dx,
    d dy/dy]]) and each number's error, from the rows' scatter about the fit times OVERLAP (neighbouring rows share most
    of their pixels)."""
    centre = xy.mean(0)
    X = np.column_stack([np.ones(len(xy)), (xy - centre) / 100.0])
    coef, *_ = np.linalg.lstsq(X, v, rcond=None)                   # 3 x 2: rows (shift, per 100 px in x, in y)
    res = v - X @ coef
    dof = max(len(xy) - 3, 1)
    inv = np.linalg.pinv(X.T @ X)
    err = np.sqrt(np.outer(np.diag(inv), (res ** 2).sum(0) / dof)) * OVERLAP        # 3 x 2, as coef
    return dict(centre=centre, shift=coef[0], grad=coef[1:].T, shift_err=err[0], grad_err=err[1:].T,
                scatter=np.sqrt((res ** 2).sum(0) / dof), n=int(len(xy)))


def motion_at(fitted, xy):
    """A fitted layer's shift at the places `xy` (one place, or rows of them)."""
    xy = np.asarray(xy, float)
    return fitted["shift"] + ((xy - fitted["centre"]) / 100.0) @ fitted["grad"].T


def parts(grad, err):
    """A layer's change of motion across the picture (`fit`'s grad and its errors) in the four parts it is made of
    (Koenderink and van Doorn 1976): spreading (the divergence: a zoom, or a surface coming nearer), turning (the curl:
    a roll of the camera), and stretching (the deformation's size and the direction of its axis: what a surface whose
    range changes across the picture gives as the camera moves past it). Each with its error, by the errors of the four
    numbers as independent."""
    (xx, xy), (yx, yy) = grad
    (exx, exy), (eyx, eyy) = err
    a, b = xx - yy, xy + yx
    stretch = float(np.hypot(a, b))
    e_stretch = float(np.sqrt((a * a * (exx ** 2 + eyy ** 2) + b * b * (exy ** 2 + eyx ** 2)) / max(stretch ** 2, 1e-24)))
    return dict(spread=float(xx + yy), spread_err=float(np.hypot(exx, eyy)), turn=float(yx - xy),
                turn_err=float(np.hypot(eyx, exy)), stretch=stretch, stretch_err=e_stretch,
                stretch_axis_deg=float(np.degrees(0.5 * np.arctan2(b, a))))


def _layer_record(fitted):
    return dict(rows=int(fitted["rows"].sum()), fitted_on=fitted["n"], shift=[float(x) for x in fitted["shift"]], shift_err=[float(x) for x in fitted["shift_err"]],
                grad=[[float(x) for x in r] for r in fitted["grad"]], grad_err=[[float(x) for x in r] for r in fitted["grad_err"]],
                centre=[float(x) for x in fitted["centre"]], **parts(fitted["grad"], fitted["grad_err"]))


def _where(xy):
    """Where a layer's rows are: the quartiles and the median of their x and of their y (template centres, px)."""
    q = np.percentile(xy, [25, 50, 75], axis=0)
    return dict(x=[float(v) for v in q[:, 0]], y=[float(v) for v in q[:, 1]])


def neighbours(xy, label):
    """Of the rows next to each other on the grid (STRIDE apart across or down), both in a layer, the share in the same
    one, and the share chance gives (each layer's share of those rows, squared, summed): (same, by chance). A map of
    two layers in two parts of the picture is near 1 against well under it."""
    ix = np.round(xy / STRIDE).astype(np.int64)
    at = {(int(x), int(y)): int(l) for (x, y), l in zip(ix, label) if l}
    same = total = 0
    for (x, y), l in at.items():
        for q in ((x + 1, y), (x, y + 1)):
            m = at.get(q)
            if m:
                total += 1
                same += m == l
    n = np.bincount(label[label > 0], minlength=3)[1:]
    chance = float((n ** 2).sum() / max(n.sum(), 1) ** 2)
    return dict(same=same / total if total else None, chance=chance, pairs=total)


def summary(records, per_s, H):
    """The clip's dense field in a few numbers, from its pairs' records; speeds in px/s (`per_s` = fps / k)."""
    read = [r for r in records if "first" in r]
    two = [r for r in read if "second" in r]
    out = dict(pairs_read=len(read), rows_kept=dict(median=_med([r["kept"] for r in records]),
                                                    today_median=_med([r["today"] for r in records])),
               two_layers=None, change_across=None)
    if two:
        # Which layer has more rows can change from pair to pair as the picture moves (PR144: the sea for most of the
        # window, the cloud tops at its end); which moves faster on the screen does not while the parallax keeps its
        # sign. So a pair's two layers are told apart by their speed, and where each lies is said of the faster and the
        # slower.
        speed = lambda x: float(np.hypot(*x["shift"]))
        fast = [max((r["first"], r["second"]), key=speed) for r in two]
        slow = [min((r["first"], r["second"]), key=speed) for r in two]
        share = lambda xs: [_med([x["where"]["y"][i] / H for x in xs]) for i in range(3)]
        out["two_layers"] = dict(pairs=len(two), share_of_pairs=len(two) / max(len(read), 1),
                                 apart_px_per_s=_med([r["second"]["apart"] * per_s for r in two]),
                                 smaller_rows=_med([r["second"]["rows"] for r in two]),
                                 faster_y_share=share(fast), slower_y_share=share(slow),
                                 neighbours_same=_med([r["neighbours"]["same"] for r in two if r["neighbours"]["same"] is not None]),
                                 neighbours_by_chance=_med([r["neighbours"]["chance"] for r in two]))
    if read:
        out["change_across"] = dict(units="px/s per 100 px", pairs=len(read))
        for p in ("spread", "turn", "stretch"):
            v = np.array([r["first"][p] for r in read]) * per_s
            e = np.array([r["first"][f"{p}_err"] for r in read]) * per_s
            out["change_across"][p] = dict(median=float(np.median(v)), error=median_error(v), p16=float(np.percentile(v, 16)),
                                           p84=float(np.percentile(v, 84)), pair_error_median=float(np.median(e)))
    return out


def median_error(v):
    """The error of the median of `v` from their own scatter: the median absolute deviation as a sigma (x 1.4826), and
    the median's (x 1.2533 / sqrt(n)); None under three values. Pairs spread over a clip are read on different frames, so
    their scatter holds whatever moves a pair's reading, which a pair's own error does not."""
    v = np.asarray(v, float)
    if len(v) < 3:
        return None
    return float(1.2533 * 1.4826 * np.median(np.abs(v - np.median(v))) / np.sqrt(len(v)))


def _med(x):
    x = [v for v in x if v is not None]
    return float(np.median(x)) if x else None


RECORD = ("a t_s reach placed kept today first_rows first_dx first_dy spread spread_err turn turn_err stretch stretch_err "
          "stretch_axis_deg first_y25 first_y50 first_y75 second_rows second_dx second_dy apart second_y25 second_y50 second_y75 "
          "neighbours_same neighbours_chance").split()


def write(out, records, mapped, k):
    """<out>_dense.csv (a row a pair: RECORD, shifts over k frames, changes in px over k frames per 100 px) and
    <out>_dense_map.csv (a row a kept template: MAP_COLS). The paths written."""
    with open(f"{out}_dense.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow([c.replace("dx", f"dx{k}").replace("dy", f"dy{k}") for c in RECORD])
        for r in records:
            f, s = r.get("first"), r.get("second")
            row = [r["a"], r["t_s"], r["reach"], r["placed"], r["kept"], r["today"]]
            row += ([f["rows"], round(f["shift"][0], 3), round(f["shift"][1], 3)]
                    + [round(f[p], 4) for p in ("spread", "spread_err", "turn", "turn_err", "stretch", "stretch_err")]
                    + [round(f["stretch_axis_deg"], 1)] + [round(v) for v in f["where"]["y"]] if f else [""] * 13)
            row += ([s["rows"], round(s["shift"][0], 3), round(s["shift"][1], 3), round(s["apart"], 2)]
                    + [round(v) for v in s["where"]["y"]] if s else [""] * 7)
            n = r.get("neighbours")
            row += [round(n["same"], 4) if n and n["same"] is not None else "", round(n["chance"], 4) if n else ""]
            wr.writerow(row)
    with open(f"{out}_dense_map.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["frame", "x_px", "y_px", f"dx{k}", f"dy{k}", "peak", "layer"])
        for a, x, y, dx, dy, pk, lab in mapped:
            wr.writerow([int(a), round(x, 1), round(y, 1), round(dx, 3), round(dy, 3), round(pk, 4), int(lab)])
    return [f"{out}_dense.csv", f"{out}_dense_map.csv"]


def figure(path, clip, records, mapped, k, say=print):
    """Where each layer is, on the pair with the most rows in a second layer (else the most kept): its first frame in
    grey, each kept template's centre a square in its layer's colour; beside it, the larger layer's speed down the
    picture, row by row, and its fitted change over the middle 90 % of its rows. In the house style (figures.setup)."""
    if not len(mapped):
        return None
    import matplotlib
    matplotlib.use("Agg")
    from . import figures
    plt = figures.setup()
    best = max(records, key=lambda r: (r.get("second", {}).get("rows", 0), r["kept"]))
    a = best["a"]
    m = mapped[mapped[:, 0] == a]
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True, gridspec_kw=dict(width_ratios=[1.9, 1]))
    g = clip.grey(a)
    lo, hi = np.percentile(g, [1, 99.5])
    ax.imshow(g, cmap="gray", vmin=lo, vmax=hi, extent=(0, clip.W, clip.H, 0))
    for lab, col, name in ((0, figures.MUTED, "in neither layer"), (1, figures.BLUE, "larger layer"), (2, figures.AMBER, "smaller layer")):
        s = m[m[:, 6] == lab]
        if len(s):
            ax.scatter(s[:, 1], s[:, 2], s=5, marker="s", color=col, alpha=0.8, linewidths=0, label=name)
    ax.set_xlim(0, clip.W)
    ax.set_ylim(clip.H, 0)
    ax.set_title(f"Where each layer is, frame {a}")
    ax.set_xlabel("Across the picture (px)")
    ax.set_ylabel("Down the picture (px)")
    ax.legend(loc="lower right", markerscale=3, framealpha=0.9)
    one = m[m[:, 6] == 1]
    per_s = clip.fps / k
    if len(one):
        speed = np.hypot(one[:, 3], one[:, 4]) * per_s
        bx.scatter(one[:, 2], speed, s=4, color=figures.BLUE, alpha=0.35, linewidths=0)
        f = best["first"]
        ys = np.linspace(*np.percentile(one[:, 2], [5, 95]), 50)        # where most of the layer's rows are
        xs = np.full_like(ys, f["centre"][0])
        fitted = motion_at(dict(shift=np.array(f["shift"]), grad=np.array(f["grad"]), centre=np.array(f["centre"])),
                           np.column_stack([xs, ys]))
        bx.plot(ys, np.hypot(*fitted.T) * per_s, color=figures.PRIMARY, lw=2)
    bx.set_title("Larger layer's speed down the picture")
    bx.set_xlabel("Down the picture (px)")
    bx.set_ylabel("Speed (pixels a second)")
    figures.save(fig, path, dpi=200, quiet=True)
    plt.close(fig)
    say(f"wrote {path}")
    return str(path)


def said(d):
    """What `mcdonald layers --dense` prints of the dense field, from its fields."""
    L = [f"dense field: {d['template']}-px templates every {d['stride']} px, {d['pairs']} pairs"]
    if d.get("why"):
        return L + ["  " + d["why"]]
    e = d["empty_pairs"]
    L.append(f"  a match counts at a peak of {d['floor']:.2f} or more, where the empty pairs (frame b turned half a turn; "
             f"{e['other_clip_is']}) keep {e['half_turn']:.1%} and {e['other_clip']:.1%} of their templates")
    r = d["rows_kept"]
    if r["median"] is not None:
        L.append(f"  matches kept a pair: median {r['median']:.0f} (the 128-px templates every 96 px: {r['today_median']:.0f}); "
                 f"a background layer read in {d['pairs_read']} of {d['pairs']} pairs")
    s = d.get("two_layers")
    if s:
        f, w = s["faster_y_share"], s["slower_y_share"]
        L.append(f"  two layers in {s['pairs']} of {d['pairs_read']} pairs, {s['apart_px_per_s']:.0f} px/s apart (median): the "
                 f"faster on the screen centred {f[1]:.0%} of the way down the picture (half its matches from {f[0]:.0%} to "
                 f"{f[2]:.0%}), the slower centred {w[1]:.0%} ({w[0]:.0%} to {w[2]:.0%})")
        if s["neighbours_same"] is not None:
            L.append(f"  neighbouring matches in the same layer {s['neighbours_same']:.1%} of the time (by chance "
                     f"{s['neighbours_by_chance']:.0%}): each layer lies in a part of the picture of its own")
    elif d["pairs_read"]:
        L.append("  one layer: no second group of matches large enough to be a layer")
    c = d.get("change_across")
    if c:
        words = dict(spread="spreads (a zoom, or a surface coming nearer)", turn="turns (a roll of the camera)",
                     stretch="stretches (a surface whose range changes across the picture)")
        L.append(f"  across the larger layer, how its motion changes, in px/s per 100 px (the median of {c['pairs']} pairs, its "
                 "error from their scatter, and the middle two-thirds of the pairs):")
        for p in ("spread", "turn", "stretch"):
            q = c[p]
            err = f"+/-{q['error']:5.2f}" if q["error"] is not None else "        "
            L.append(f"    {words[p]:58s} {q['median']:+7.2f} {err}   {q['p16']:+7.2f} to {q['p84']:+7.2f}")
    return L


def described(d):
    """The dense field in one line for the stage's result (Found.result), or None where it read nothing."""
    if not d or d.get("why") or not d.get("pairs_read"):
        return d.get("why") if d else None
    s = d.get("two_layers")
    c = d.get("change_across") or {}
    parts_said = [f"{name} {c[p]['median']:+.1f}" + (f" +/- {c[p]['error']:.1f}" if c[p]["error"] is not None else "")
                  for p, name in (("spread", "spreads"), ("turn", "turns"), ("stretch", "stretches")) if c.get(p)]
    return (f"{d['rows_kept']['median']:.0f} matches a pair at a peak of {d['floor']:.2f} or more (empty pairs under "
            f"{d['null_share']:.0%}); "
            + (f"two layers in {s['pairs']} of {d['pairs_read']} pairs, {s['apart_px_per_s']:.0f} px/s apart, the faster on the "
               f"screen centred {s['faster_y_share'][1]:.0%} of the way down and the slower {s['slower_y_share'][1]:.0%}"
               if s else "one layer")
            + (f"; across the larger layer its motion {', '.join(parts_said)} px/s per 100 px" if parts_said else ""))


