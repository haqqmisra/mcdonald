#!/usr/bin/env python3
"""How does the background of a clip move -- and is it one background?

  bg_layers.py VIDEO|ID [--track CSV | --auto-track] [options]

Measures the scene's screen motion with whole-template matching over a k-frame
baseline (forensics.shift_field), separately for striated texture (open sea)
and isotropic texture (cloud, land), and reports
  - each layer's screen velocity, and the rate of one layer against the other
    (layer parallax: own-ship motion seen against two ranges);
  - how many motion groups the templates fall into, whatever their texture;
  - with a track, the object's rate against EACH layer in 1-s windows of
    wall-clock time. "Against the background" is only one number when there is
    one layer. On PR144 there were two, 98 px/s apart, and a single-consensus
    tracker had blended them into a rate against neither.

Writes <tag>_layers.csv and <tag>_layers.png into the case directory
(--out DIR; default ./<tag>).

  --validate      check the ruler first: recover known synthetic shifts of real
                  frames (bias), and compare 2k-frame shifts with the sum of two
                  k-frame shifts (chain consistency)
  --composite N   red/cyan composites of frames N and N+k aligned on each
                  layer's shift; the other layer shows colour fringes

VIDEO is a path or a record id (PR144, DOW-UAP-PR144, 06:PR001). Frames are
ffmpeg's, 1-based. A full-rate run is ~1 s per frame pair on 10 cores.
"""
import argparse
import csv
import hashlib
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from . import forensics as vf
from .report import Found, emit, inputs_of, said_to_stderr

_G = {}


def _init(video, workdir, n0, n1, masks, rows, trk, k, reach, size, dark):
    masks = {key: v for key, v in masks.items() if key in ("blocks", "graphics", "colour")}
    _G.update(clip=vf.Clip(video, workdir, n0, n1), masks=masks, rows=rows, k=k, reach=reach,
              pos=vf.interp_track(trk) if trk else None, size=size, dark=dark)


def _bad(n):
    clip = _G["clip"]
    rgb = clip.rgb(n)
    bad = vf.frame_mask(rgb, _G["masks"], _G["rows"], n)
    if _G["pos"]:
        cx, cy = _G["pos"](n)
        yy, xx = np.ogrid[:clip.H, :clip.W]
        bad = bad | ((xx - cx) ** 2 + (yy - cy) ** 2 < 28 ** 2)
    return rgb.mean(2), bad


def _pair(a):
    ga, ba = _bad(a)
    gb, bb = _bad(a + _G["k"])
    return vf.shift_field_auto(ga, gb, ba, bb, a=a, reach=_G["reach"])[0]


def _cands(n):
    return n, vf.frame_candidates(_G["clip"], n, _G["masks"], _G["rows"], _G["size"], _G["dark"])


def validate(clip, masks, rows, k, reach):
    """The ruler, on this clip's own texture."""
    ns = np.linspace(clip.n0 + 5, clip.n1 - 2 * k - 5, 6).astype(int)
    print("known shifts of real frames (truth -> recovered consensus):")
    for n in ns[::2]:
        g = clip.grey(int(n))
        bad = vf.frame_mask(clip.rgb(int(n)), masks, rows, int(n))
        for dx, dy in ((-20, -8), (37, 11), (-96, 40)):
            gb = ndimage.shift(g, (dy, dx), order=0, mode="nearest")
            bb = ndimage.shift(bad.astype(float), (dy, dx), order=0, mode="constant", cval=1) > 0
            f = vf.good(vf.shift_field(g, gb, bad, bb, stride=192, reach=reach))
            c = vf.consensus(f[:, 3:5])
            got = "none" if c is None else f"({c[0][0]:+.2f},{c[0][1]:+.2f}) from {c[1]} templates"
            print(f"  n = {n}: ({dx:+d},{dy:+d}) -> {got}")
    print(f"chain consistency: the {2 * k}-frame shift against the sum of two {k}-frame shifts:")
    for n in ns:
        n = int(n)
        fr = {m: (clip.grey(m), vf.frame_mask(clip.rgb(m), masks, rows, m)) for m in (n, n + k, n + 2 * k)}
        sh = {}
        for a, b in ((n, n + k), (n + k, n + 2 * k), (n, n + 2 * k)):
            f = vf.shift_field(fr[a][0], fr[b][0], fr[a][1], fr[b][1], stride=144, reach=reach * (b - a) // k)
            sh[(a, b)] = vf.layers_of(f)
        for name in ("striated", "isotropic"):
            p = [sh[q][name] for q in ((n, n + k), (n + k, n + 2 * k), (n, n + 2 * k))]
            if all(p):
                s, d = p[0][0] + p[1][0], p[2][0]
                print(f"  n = {n} {name:9s}: sum ({s[0]:+7.1f},{s[1]:+6.1f})  direct ({d[0]:+7.1f},{d[1]:+6.1f})  "
                      f"difference {np.hypot(*(d - s)):.1f} px ({100 * np.hypot(*(d - s)) / max(np.hypot(*d), 1):.1f} %)")


def composite(clip, n, k, lay, out):
    ga, gb = clip.grey(n), clip.grey(n + k)
    lo, hi = np.percentile(ga, [1, 99.5])
    st = lambda g: ((g - lo) / max(hi - lo, 1) * 255).clip(0, 255)
    tiles = []
    for name in ("striated", "isotropic"):
        if lay.get(name):
            dx, dy = lay[name][0]
            bs = ndimage.shift(gb, (-dy, -dx), order=1, mode="constant")
            tiles.append(np.stack([st(ga), st(bs), st(bs)], -1).astype(np.uint8))
            print(f"composite: frame {n} (red) against {n + k} shifted by the {name} layer ({dx:+.1f},{dy:+.1f})")
    if tiles:
        Image.fromarray(np.vstack(tiles)).save(out)
        print(f"wrote {out}  (grey = aligned; colour fringes = the other layer)")


def figure(out, clip, names, w, par, groups, say=print):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
    INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": GRID,
                         "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
                         "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF})
    ns = np.arange(clip.n0, clip.n1 + 1)
    ser = lambda d: np.array([np.hypot(*d[n]) if n in d else np.nan for n in ns])
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(10, 6.2), sharex=True,
                                 gridspec_kw=dict(height_ratios=[3, 1], hspace=0.18, left=0.08, right=0.8, top=0.88, bottom=0.09))
    what = "the object's rate against each background layer" if w["striated"] or w["isotropic"] or w["all"] else "screen speed of each background layer"
    fig.text(0.08, 0.955, f"{out.name.upper().split('_')[0]}: {what}", fontsize=12.5, weight="bold", va="center")
    fig.text(0.08, 0.915, "1-s windows against wall-clock time; layers classed by the anisotropy of their texture.",
             fontsize=9, color=INK2, va="center")
    for a_ in (ax, bx):
        a_.grid(axis="y", color=GRID, lw=0.8)
        a_.set_axisbelow(True)
        a_.tick_params(length=0)
        for s in ("top", "right", "left"):
            a_.spines[s].set_visible(False)
    for key, col in (("striated", BLUE), ("isotropic", ORANGE)):
        if w[key]:
            v = ser(w[key])
            ax.plot(clip.t(ns), v, color=col, lw=2, solid_capstyle="round", label=f"against the {names[key]}")
            i = np.nonzero(np.isfinite(v))[0][-1]
            ax.annotate(f"against the\n{names[key]}", (clip.t(ns[i]), v[i]), xytext=(8, 0), textcoords="offset points",
                        fontsize=8.8, va="center", annotation_clip=False)
    if not (w["striated"] and w["isotropic"]) and w["all"]:
        ax.plot(clip.t(ns), ser(w["all"]), color=INK2, lw=1.6, label="against all templates")
    ax.set_ylabel("rate  [px/s]")
    ax.legend(loc="upper left", frameon=False, fontsize=8.8, ncol=3, handlelength=1.6, borderaxespad=0.0)
    if par:
        bx.plot(clip.t(ns), ser(par), color=AQUA, lw=2, solid_capstyle="round")
        bx.set_title(f"The {names['isotropic']} against the {names['striated']} (both in frame)", loc="left",
                     fontsize=9.6, weight="bold", pad=5)
    else:
        bx.plot(clip.t(ns), [groups.get(n, np.nan) for n in ns], color=INK2, lw=1.2)
        bx.set_title("Motion groups among the templates", loc="left", fontsize=9.6, weight="bold", pad=5)
    bx.set_ylim(bottom=0)
    bx.set_ylabel("rate  [px/s]" if par else "groups")
    bx.set_xlabel("time in the clip  [s]")
    fig.savefig(out, dpi=140)
    say(f"wrote {out}")


def auto_track(clip, masks, rows=None, size=9.0, dark=False, seed=None, out=None, procs=10, say=print):
    """Track a compact source with no marks to go on: the detector on every frame, linked
    from `seed` (n, x, y) or from the strongest. Writes <out>_track_strip.png, which has
    to be looked at before the track is believed. `layers` and `integrity` both offer it."""
    args = (clip.video, clip.dir, clip.n0, clip.n1, masks, rows, None, 5, 0, size, dark)
    with Pool(procs, _init, args) as p:
        cands = dict(p.map(_cands, clip.frames(), chunksize=4))
    trk = vf.link_track(cands, clip.n0, clip.n1, (int(seed[0]), seed[1], seed[2]) if seed else None)
    strip = Path(f"{out}_track_strip.png")
    shown = vf.track_strip(clip, trk, strip)
    say(f"auto-track: {len(trk)} of {clip.n1 - clip.n0 + 1} frames. CHECK {strip} (frames {shown[0]}..{shown[-1]}) "
        "before trusting it.")
    return trk


def _spread(d):
    """Median, the 16-84 % interval and the range of a set of windowed rates, px/s."""
    v = np.array([np.hypot(*p) for p in d.values()])
    if not len(v):
        return None
    return dict(median=float(np.median(v)), p16=float(np.percentile(v, 16)), p84=float(np.percentile(v, 84)),
                min=float(v.min()), max=float(v.max()), windows=len(v))


def glance(clip, masks, rows=None):
    """One frame pair at the start of the window: how many motion groups, and how fast
    each texture class crosses the screen. Seconds, where `measure` is minutes -- and a
    look, not a measurement: one pair, no windows, and nothing about the object."""
    a, b = clip.n0, min(clip.n0 + 5, clip.n1)
    ga, gb = clip.grey(a), clip.grey(b)
    bad_a = vf.frame_mask(clip.rgb(a), masks, rows, a)
    bad_b = vf.frame_mask(clip.rgb(b), masks, rows, b)
    field, still = vf.shift_field_auto(ga, gb, bad_a, bad_b)
    f = vf.good(field)
    lay = vf.layers_of(f) if len(f) else {"groups": 0}
    groups = lay.get("groups", 0)
    res = {"motion groups": groups}
    fields = dict(pair=[a, b], motion_groups=groups, scene_held_still=bool(still), screen_px_per_s={}, templates={})
    if still:
        res["scene held still"] = ("yes -- zero shift was allowed, so a static "
                                   "pattern could be locking these estimates; read "
                                   "them as 'no more than'")
    for name in ("striated", "isotropic"):
        v = lay.get(name)
        if v is not None:
            rate = float(np.hypot(*v[0])) * clip.fps / max(b - a, 1)
            fields["screen_px_per_s"][name], fields["templates"][name] = rate, int(v[1])
            res[f"{name} layer"] = f"{rate:.0f} px/s ({v[1]} templates)"
    npw, notes = [], []
    if groups == 0:
        npw.append(("layers", "no consensus background motion: the scene is held still "
                              "or has too little texture"))
    if still:
        npw.append(("layers", "the scene is held still on screen, so a background rate "
                              "here is an upper limit, not a measurement"))
    if len(fields["screen_px_per_s"]) > 1:
        notes.append("More than one background layer: any rate quoted here must name "
                     "which layer it is against.")
    return Found("layers", res, fields, no_power=npw, notes=notes)


def measure(clip, masks, rows=None, track=None, k=5, step=1, max_shift=45.0, names=None, dark_below=None,
            out=None, procs=10, fresh=False, say=print):
    """Every frame pair of the window: each layer's screen velocity, the rate of one layer
    against the other, and with a track the object's rate against EACH layer, in 1-s
    windows of wall-clock time. Writes <out>_layers.csv and <out>_layers.png.

    The findings come back as numbers (Found.fields); what `mcdonald layers` prints is
    written from them by `said`, so the prose and the fields cannot disagree. The
    templates are cached in the clip's work directory; `fresh` measures them again."""
    names = dict(names or {})
    names.setdefault("striated", "striated layer")
    names.setdefault("isotropic", "isotropic layer")
    reach = int(max_shift * k + 20)
    trk = {n: p for n, p in track.items() if clip.n0 <= n <= clip.n1} if track else None

    # The templates are minutes of work and are kept beside the frames. What they depend on is in the
    # name: until 2026-09-20 the track was there only as "is there one", and --mask-rows and --max-shift
    # not at all, so a second run with a different track or caption mask silently reused the first's.
    made_from = repr((reach, rows, sorted((n, round(x, 2), round(y, 2)) for n, (x, y) in trk.items()) if trk else None))
    cache = clip.dir / (f"bg_layers_k{k}_s{step}_{clip.n0}_{clip.n1}_"
                        f"{hashlib.sha1(made_from.encode()).hexdigest()[:10]}.npz")
    if cache.exists() and not fresh:
        tpl = np.load(cache)["tpl"]
        say(f"templates from {cache} (measured earlier with the same frames, track and masks; --fresh measures again)")
    else:
        with Pool(procs, _init, (clip.video, clip.dir, clip.n0, clip.n1, masks, rows, trk, k, reach, 9.0, False)) as p:
            tpl = np.vstack(p.map(_pair, range(clip.n0, clip.n1 - k + 1, step), chunksize=2))
        np.savez_compressed(cache, tpl=tpl)

    lay = {int(a): vf.layers_of(tpl[tpl[:, 0] == a], dark_below=dark_below) for a in np.unique(tpl[:, 0])}
    files = []
    if out:
        with open(f"{out}_layers.csv", "w", newline="") as f:
            wr = csv.writer(f)
            wr.writerow(["frame", "t_s", "x_px", "y_px"] + [f"{c}_{q}" for c in ("striated", "isotropic", "all")
                                                           for q in (f"dx{k}", f"dy{k}", "tpl")] + ["groups", "inliers"])
            for n in clip.frames():
                row = [n, round(float(clip.t(n)), 4)] + ([round(v, 2) for v in trk[n]] if trk and n in trk else ["", ""])
                for c in ("striated", "isotropic", "all"):
                    v = lay.get(n, {}).get(c)
                    row += [round(v[0][0], 2), round(v[0][1], 2), v[1]] if v else ["", "", ""]
                wr.writerow(row + ([lay[n]["groups"], round(lay[n]["inliers"], 3)] if n in lay else ["", ""]))
        files.append(f"{out}_layers.csv")
        say(f"wrote {out}_layers.csv")

    fk = clip.fps / k
    half = int(round(clip.fps / 2))
    need = int(0.8 * 2 * half / step)
    win = lambda s: vf.windowed(s, clip.n0, clip.n1, k, half, need) if s else {}
    vel = {c: {a: l[c][0] * fk for a, l in lay.items() if l[c]} for c in ("striated", "isotropic", "all")}
    par = win({a: vel["isotropic"][a] - vel["striated"][a] for a in set(vel["striated"]) & set(vel["isotropic"])})
    if trk:
        rel = {c: {a: (np.array(trk[a + k]) - np.array(trk[a])) * fk - v for a, v in vel[c].items()
                   if a in trk and a + k in trk} for c in vel}
    else:
        rel = vel
    w = {c: win(rel[c]) for c in rel}

    fields = dict(of="the object's rate against each layer" if trk else "each layer's screen speed",
                  tracked=bool(trk), k=k, step=step, names=names,
                  px_per_s={c: _spread(w[c]) for c in ("striated", "isotropic", "all")},
                  layer_against_layer=_spread(par) if par else None, object_over_parallax=None)
    both = sorted(set(w["striated"]) & set(par)) if trk and par else []
    if both:
        rat = [np.hypot(*w["striated"][n]) / max(np.hypot(*par[n]), 1e-6) for n in both]
        ang = [np.degrees(np.arctan2(w["striated"][n][1], w["striated"][n][0]) - np.arctan2(par[n][1], par[n][0])) for n in both]
        ang = (np.array(ang) + 180) % 360 - 180
        fields["object_over_parallax"] = dict(ratio=float(np.median(rat)), ratio_p16=float(np.percentile(rat, 16)),
                                              ratio_p84=float(np.percentile(rat, 84)),
                                              directions_apart_deg=float(np.median(ang)))
    g = np.array([l["groups"] for l in lay.values()])
    two = np.array([l.get("group_gap", 0) for l in lay.values() if l["groups"] == 2]) * fk
    fields["motion_groups"] = dict(two_in_share_of_pairs=float(np.mean(g == 2)),
                                   apart_px_per_s=float(np.median(two)) if len(two) >= 5 else None,
                                   inside_a_group_share=float(np.median([l["inliers"] for l in lay.values()])))

    result, npw, notes = {}, [], []
    for c in ("striated", "isotropic", "all"):
        s = fields["px_per_s"][c]
        if s:
            result[("object against the " if trk else "screen speed of the ") + names.get(c, "whole scene (largest group)")] = (
                f"median {s['median']:.0f} px/s (16-84 %: {s['p16']:.0f}-{s['p84']:.0f}; {s['windows']} one-second windows)")
    if fields["layer_against_layer"]:
        s = fields["layer_against_layer"]
        result[f"the {names['isotropic']} against the {names['striated']}"] = (
            f"median {s['median']:.0f} px/s (16-84 %: {s['p16']:.0f}-{s['p84']:.0f})")
        notes.append("More than one background layer: any rate quoted here must name "
                     "which layer it is against.")
    if not any(fields["px_per_s"].values()):
        npw.append(("layers", "no one-second window had enough frame pairs with a consensus background motion: "
                              "the scene is held still, has too little texture, or the window is under a second"))
    if out:
        figure(Path(f"{out}_layers.png"), clip, names, w, par, {a: l["groups"] for a, l in lay.items()}, say=say)
        files.append(f"{out}_layers.png")
    return Found("layers", result, fields, no_power=npw, notes=notes, files=files, carry=dict(reach=reach))


def said(fields):
    """What `mcdonald layers` prints of a measurement, line by line, from its fields."""
    names, L = fields["names"], []

    def describe(label, s):
        if s:
            L.append(f"  {label:44s} median {s['median']:5.0f}  16-84 %: {s['p16']:5.0f}-{s['p84']:5.0f}"
                     f"  range {s['min']:5.0f}-{s['max']:5.0f} px/s  ({s['windows']} windows)")

    L.append("object's rate against" if fields["tracked"] else "screen speed of")
    for c in ("striated", "isotropic", "all"):
        describe(f"the {names.get(c, 'whole scene (largest group)')}", fields["px_per_s"][c])
    if fields["layer_against_layer"]:
        L.append("layer against layer")
        describe(f"the {names['isotropic']} against the {names['striated']}", fields["layer_against_layer"])
        r = fields["object_over_parallax"]
        if r:
            L.append(f"  object-vs-{names['striated']} over {names['isotropic']}-vs-{names['striated']}: ratio "
                     f"{r['ratio']:.1f} ({r['ratio_p16']:.1f}-{r['ratio_p84']:.1f}), directions "
                     f"{r['directions_apart_deg']:+.0f} deg apart. A stationary object gives parallel motion at a constant ratio.")
    m = fields["motion_groups"]
    L.append(f"motion groups: two in {m['two_in_share_of_pairs']:.1%} of pairs"
             + (f", {m['apart_px_per_s']:.0f} px/s apart (median)" if m["apart_px_per_s"] is not None else "")
             + f"; templates inside a group: {m['inside_a_group_share']:.0%} (rigid scenes are near 100 %)")
    return L


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--k", type=int, default=5, help="baseline, frames")
    ap.add_argument("--step", type=int, default=1, help="measure every step-th pair")
    ap.add_argument("--max-shift", type=float, default=45, help="fastest scene motion to look for, px/frame")
    ap.add_argument("--track", help="CSV with frame and x/y columns")
    ap.add_argument("--auto-track", action="store_true", help="track a compact source (check the strip it writes)")
    ap.add_argument("--size", type=float, default=9.0, help="source diameter for --auto-track, px")
    ap.add_argument("--dark", action="store_true", help="the source is darker than the scene")
    ap.add_argument("--seed", help="n,x,y: where the source is in frame n")
    ap.add_argument("--marks", metavar="JSON",
                    help="a _marks.json from `mcdonald mark`: link the track from the hand marks, which give it the "
                    "detector's scale, its polarity and the velocity. The way to track an object too fast "
                    "for --auto-track to acquire")
    ap.add_argument("--mask-rows", help="y0:y1[:n0:n1],... burned-in captions the static masks miss")
    ap.add_argument("--dark-below", type=float, help="striated templates must be darker than this (open sea in white-hot IR)")
    ap.add_argument("--names", default="striated=striated layer,isotropic=isotropic layer",
                    help="e.g. striated=sea,isotropic=cloud tops")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--composite", type=int)
    ap.add_argument("--out", metavar="DIR", help="case directory for results "
                    "(default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--procs", type=int, default=10)
    ap.add_argument("--fresh", action="store_true",
                    help="measure again: do not reuse the templates an earlier run left in the work directory")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        found, clip = _main(args)
    if args.json:
        emit(found.envelope("layers", inputs_of(args), clip, said=lines))
    return 0


def _main(args):
    video, tag, _ = vf.resolve(args.video)
    clip = vf.Clip(video, args.workdir, args.n0, args.n1)
    out = vf.out_prefix(args.out, tag)
    names = dict(p.split("=") for p in args.names.split(","))
    rows = vf.parse_rows(args.mask_rows)
    masks = vf.static_masks(clip)
    reach = int(args.max_shift * args.k + 20)
    print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}; "
          f"masked: blocks {masks['blocks'].mean():.1%}, graphics {masks['graphics'].mean():.1%}")
    if args.validate:
        validate(clip, masks, rows, args.k, reach)

    trk = vf.read_track(args.track) if args.track else None
    if args.marks and not trk:
        from . import autolink
        trk = autolink.track_from_marks_file(clip, args.marks, out, masks=masks, rows=rows, procs=args.procs)
    elif args.auto_track:
        seed = tuple(float(v) for v in args.seed.split(",")) if args.seed else None
        trk = auto_track(clip, masks, rows, args.size, args.dark, seed, out, args.procs)

    found = measure(clip, masks, rows, trk, k=args.k, step=args.step, max_shift=args.max_shift, names=names,
                    dark_below=args.dark_below, out=out, procs=args.procs, fresh=args.fresh)
    print("\n".join(said(found.fields)))
    if args.composite:
        fa = args.composite
        ga, ba = clip.grey(fa), vf.frame_mask(clip.rgb(fa), masks, rows, fa)
        gb, bb = clip.grey(fa + args.k), vf.frame_mask(clip.rgb(fa + args.k), masks, rows, fa + args.k)
        name = Path(f"{out}_composite_{fa}.png")
        composite(clip, fa, args.k, vf.layers_of(vf.shift_field(ga, gb, ba, bb, reach=reach), dark_below=args.dark_below), name)
        if name.exists():
            found.files.append(str(name))
    return found, clip


if __name__ == "__main__":
    raise SystemExit(main())
