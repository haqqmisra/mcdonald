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
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from . import forensics as vf

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
    clip = _G["clip"]
    rgb = clip.rgb(n)
    bad = vf.frame_mask(rgb, _G["masks"], _G["rows"], n, grow=6)
    m = int(1.5 * _G["size"])
    bad[:m, :] = bad[-m:, :] = True
    bad[:, :m] = bad[:, -m:] = True
    return n, vf.source_candidates(rgb.mean(2), bad, _G["size"], _G["dark"])


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


def figure(out, clip, names, w, par, groups):
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
    print(f"wrote {out}")


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
    ap.add_argument("--mask-rows", help="y0:y1[:n0:n1],... burned-in captions the static masks miss")
    ap.add_argument("--dark-below", type=float, help="striated templates must be darker than this (open sea in white-hot IR)")
    ap.add_argument("--names", default="striated=striated layer,isotropic=isotropic layer",
                    help="e.g. striated=sea,isotropic=cloud tops")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--composite", type=int)
    ap.add_argument("--out", metavar="DIR", help="case directory for results "
                    "(default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--procs", type=int, default=10)
    args = ap.parse_args()

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
    if args.auto_track:
        _init(video, clip.dir, clip.n0, clip.n1, masks, rows, None, args.k, reach, args.size, args.dark)
        with Pool(args.procs, _init, (video, clip.dir, clip.n0, clip.n1, masks, rows, None, args.k, reach, args.size, args.dark)) as p:
            cands = dict(p.map(_cands, clip.frames(), chunksize=4))
        seed = tuple(float(v) for v in args.seed.split(",")) if args.seed else None
        trk = vf.link_track(cands, clip.n0, clip.n1, (int(seed[0]), seed[1], seed[2]) if seed else None)
        strip = Path(f"{out}_track_strip.png")
        shown = vf.track_strip(clip, trk, strip)
        print(f"auto-track: {len(trk)} of {clip.n1 - clip.n0 + 1} frames. CHECK {strip} (frames {shown[0]}..{shown[-1]}) "
              "before trusting it.")
    if trk:
        trk = {n: p for n, p in trk.items() if clip.n0 <= n <= clip.n1}

    cache = clip.dir / f"bg_layers_k{args.k}_s{args.step}_{clip.n0}_{clip.n1}_{int(bool(trk))}.npz"
    if cache.exists():
        tpl = np.load(cache)["tpl"]
    else:
        with Pool(args.procs, _init, (video, clip.dir, clip.n0, clip.n1, masks, rows, trk, args.k, reach, args.size, args.dark)) as p:
            tpl = np.vstack(p.map(_pair, range(clip.n0, clip.n1 - args.k + 1, args.step), chunksize=2))
        np.savez_compressed(cache, tpl=tpl)

    lay = {int(a): vf.layers_of(tpl[tpl[:, 0] == a], dark_below=args.dark_below) for a in np.unique(tpl[:, 0])}
    with open(f"{out}_layers.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["frame", "t_s", "x_px", "y_px"] + [f"{c}_{q}" for c in ("striated", "isotropic", "all")
                                                       for q in (f"dx{args.k}", f"dy{args.k}", "tpl")] + ["groups", "inliers"])
        for n in clip.frames():
            row = [n, round(float(clip.t(n)), 4)] + ([round(v, 2) for v in trk[n]] if trk and n in trk else ["", ""])
            for c in ("striated", "isotropic", "all"):
                v = lay.get(n, {}).get(c)
                row += [round(v[0][0], 2), round(v[0][1], 2), v[1]] if v else ["", "", ""]
            wr.writerow(row + ([lay[n]["groups"], round(lay[n]["inliers"], 3)] if n in lay else ["", ""]))
    print(f"wrote {out}_layers.csv")

    fk = clip.fps / args.k
    half = int(round(clip.fps / 2))
    need = int(0.8 * 2 * half / args.step)
    win = lambda s: vf.windowed(s, clip.n0, clip.n1, args.k, half, need) if s else {}
    vel = {c: {a: l[c][0] * fk for a, l in lay.items() if l[c]} for c in ("striated", "isotropic", "all")}
    par = win({a: vel["isotropic"][a] - vel["striated"][a] for a in set(vel["striated"]) & set(vel["isotropic"])})
    if trk:
        rel = {c: {a: (np.array(trk[a + args.k]) - np.array(trk[a])) * fk - v for a, v in vel[c].items()
                   if a in trk and a + args.k in trk} for c in vel}
    else:
        rel = vel
    w = {c: win(rel[c]) for c in rel}

    def describe(label, d):
        v = np.array([np.hypot(*p) for p in d.values()])
        if len(v):
            print(f"  {label:44s} median {np.median(v):5.0f}  16-84 %: {np.percentile(v, 16):5.0f}-{np.percentile(v, 84):5.0f}"
                  f"  range {v.min():5.0f}-{v.max():5.0f} px/s  ({len(v)} windows)")

    print("object's rate against" if trk else "screen speed of")
    for c in ("striated", "isotropic", "all"):
        describe(f"the {names.get(c, 'whole scene (largest group)')}", w[c])
    if par:
        print("layer against layer")
        describe(f"the {names['isotropic']} against the {names['striated']}", par)
        both = sorted(set(w["striated"]) & set(par)) if trk else []
        if both:
            rat = [np.hypot(*w["striated"][n]) / max(np.hypot(*par[n]), 1e-6) for n in both]
            ang = [np.degrees(np.arctan2(w["striated"][n][1], w["striated"][n][0]) - np.arctan2(par[n][1], par[n][0])) for n in both]
            ang = (np.array(ang) + 180) % 360 - 180
            print(f"  object-vs-{names['striated']} over {names['isotropic']}-vs-{names['striated']}: ratio "
                  f"{np.median(rat):.1f} ({np.percentile(rat, 16):.1f}-{np.percentile(rat, 84):.1f}), directions "
                  f"{np.median(ang):+.0f} deg apart. A stationary object gives parallel motion at a constant ratio.")
    g = np.array([l["groups"] for l in lay.values()])
    two = np.array([l.get("group_gap", 0) for l in lay.values() if l["groups"] == 2]) * fk
    print(f"motion groups: two in {np.mean(g == 2):.1%} of pairs" + (f", {np.median(two):.0f} px/s apart (median)" if len(two) >= 5 else "")
          + f"; templates inside a group: {np.median([l['inliers'] for l in lay.values()]):.0%} (rigid scenes are near 100 %)")
    if args.composite:
        fa = args.composite
        ga, ba = clip.grey(fa), vf.frame_mask(clip.rgb(fa), masks, rows, fa)
        gb, bb = clip.grey(fa + args.k), vf.frame_mask(clip.rgb(fa + args.k), masks, rows, fa + args.k)
        composite(clip, fa, args.k, vf.layers_of(vf.shift_field(ga, gb, ba, bb, reach=reach), dark_below=args.dark_below),
                  Path(f"{out}_composite_{fa}.png"))
    figure(Path(f"{out}_layers.png"), clip, names, w, par, {a: l["groups"] for a, l in lay.items()})


if __name__ == "__main__":
    main()
