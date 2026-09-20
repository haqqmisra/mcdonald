#!/usr/bin/env python3
"""Every frame of a clip, tiled, with the tracked object circled -- the check that a
track is on the object all the way, and something to hand to a second analyst.

  track_sheet.py VIDEO|ID --track CSV [--track CSV2 ...] [--compare CSV] [options]

Each tile is the whole frame, reduced, with a circle at the tracked position and
an inset of the pixels there at twice native size (nearest-neighbour, so they
are the clip's own pixels; an inset spanning less than 80 DN is stretched
linearly and labelled). The inset sits in the corner farthest from the object.

  green    the object was detected in this frame (any --track file)
  orange   not detected in this frame; the position is interpolated between
           its neighbours (flat calibration frames, the object over bright cloud)
  red x    the position in the --compare track, where it differs by more than
           --compare-px (a second tracker's disagreements, e.g. a mis-link)
  no mark  outside every track

Several --track files are merged (first one wins where they overlap), so a
wide-view track and a post-zoom track can share a sheet. Writes
<tag>_all_frames.jpg into the case directory (--out DIR; default ./<tag>)
(default ./<tag>/<tag>_all_frames.jpg) and prints a per-frame contrast check:
a tracked position with no compact source under it is listed.

  --every K     every K-th frame          --cols N     tiles per row (default 30)
  --tile W      tile width, px            --pages P    split into P images
"""
import argparse
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import forensics as vf

FONT = "/usr/share/fonts/liberation-sans-fonts/LiberationSans-Bold.ttf"   # no DejaVu for PIL on this host
GREEN, ORANGE, RED, GREY = (70, 235, 90), (255, 160, 40), (255, 60, 60), (170, 170, 170)
CROP, ZOOM = 64, 2
_G = {}


def _init(video, workdir, n0, n1, pos, seen, cmp_, tw, dark):
    _G.update(clip=vf.Clip(video, workdir, n0, n1), pos=pos, seen=seen, cmp=cmp_, tw=tw, dark=dark)


def _tile(n):
    clip, tw = _G["clip"], _G["tw"]
    th = int(round(tw * clip.H / clip.W))
    s = tw / clip.W
    full = Image.fromarray(clip.rgb(n).astype(np.uint8))
    tile = full.resize((tw, th), Image.LANCZOS)
    d = ImageDraw.Draw(tile)
    font = ImageFont.truetype(FONT, max(11, tw // 27))
    p = _G["pos"].get(n)
    contrast = np.nan
    if p is not None:
        x, y = p
        col = GREEN if n in _G["seen"] else ORANGE
        r = max(7, tw // 42)
        d.ellipse([x * s - r, y * s - r, x * s + r, y * s + r], outline=col, width=2)
        g = np.pad(clip.grey(n), CROP, mode="edge")
        xi, yi = int(round(x)) + CROP, int(round(y)) + CROP
        sub = g[yi - CROP // 2:yi + CROP // 2, xi - CROP // 2:xi + CROP // 2]
        rr = np.hypot(*np.mgrid[-CROP // 2:CROP // 2, -CROP // 2:CROP // 2])
        core = sub[rr <= 4]
        contrast = float((np.median(sub[rr >= 20]) - core.min()) if _G["dark"] else (core.max() - np.median(sub[rr >= 20])))
        faint = sub.max() - sub.min() < 80                 # a faint source: stretch the inset linearly, and say so
        shown = (sub - sub.min()) / max(sub.max() - sub.min(), 1) * 255 if faint else sub
        ins = Image.fromarray(shown.astype(np.uint8)).resize((CROP * ZOOM, CROP * ZOOM), Image.NEAREST).convert("RGB")
        di = ImageDraw.Draw(ins)
        if faint:
            di.text((5, CROP * ZOOM - font.size - 4), "contrast stretched", fill=col, font=font)
        c = CROP * ZOOM // 2
        di.ellipse([c - 22, c - 22, c + 22, c + 22], outline=col, width=1)
        di.rectangle([0, 0, CROP * ZOOM - 1, CROP * ZOOM - 1], outline=col, width=2)
        corners = [(tw - CROP * ZOOM - 3, th - CROP * ZOOM - 3), (3, th - CROP * ZOOM - 3), (tw - CROP * ZOOM - 3, 3)]
        far = max(corners, key=lambda q: np.hypot(q[0] + CROP - x * s, q[1] + CROP - y * s))
        tile.paste(ins, far)
    q = _G["cmp"].get(n)
    if q is not None and (p is None or np.hypot(q[0] - p[0], q[1] - p[1]) > _G["cmp"]["_px"]):
        a = 6
        d.line([q[0] * s - a, q[1] * s - a, q[0] * s + a, q[1] * s + a], fill=RED, width=2)
        d.line([q[0] * s - a, q[1] * s + a, q[0] * s + a, q[1] * s - a], fill=RED, width=2)
    lab = f"n={n}  t={float(clip.t(n)):.2f}s" + ("" if p is not None else "  no track") + \
          ("  interp." if p is not None and n not in _G["seen"] else "")
    lw, lh = d.textlength(lab, font=font) + 8, font.size + 6
    ly = th - lh if (p is not None and p[0] * s < lw + 16 and p[1] * s < lh + 16) else 0   # never over the object
    d.rectangle([0, ly, lw, ly + lh], fill=(0, 0, 0))
    d.text((4, ly + 2), lab, fill=(255, 255, 80) if p is not None else GREY, font=font)
    return n, tile, contrast


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--track", action="append", required=True)
    ap.add_argument("--compare")
    ap.add_argument("--compare-px", type=float, default=15.0)
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--cols", type=int, default=30)
    ap.add_argument("--tile", type=int, default=384)
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--dark", action="store_true")
    ap.add_argument("--note", default="", help="a line for the header")
    ap.add_argument("--out", metavar="DIR", help="case directory for results "
                    "(default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--procs", type=int, default=10)
    args = ap.parse_args()

    video, tag, rec = vf.resolve(args.video)
    clip = vf.Clip(video, args.workdir, args.n0, args.n1)
    out = Path(f"{vf.out_prefix(args.out, tag)}_all_frames")
    seen, pos = {}, {}
    for f in args.track:                                   # each track interpolates only inside itself
        t = {n: p for n, p in vf.read_track(f).items() if clip.n0 <= n <= clip.n1}
        ip = vf.interp_track(t)
        for n in range(min(t), max(t) + 1):
            pos.setdefault(n, ip(n))
        for n, p in t.items():
            seen.setdefault(n, p)
            pos[n] = seen[n]
    cmp_ = {"_px": args.compare_px}
    if args.compare:
        cmp_.update({n: p for n, p in vf.read_track(args.compare).items() if clip.n0 <= n <= clip.n1})

    frames = list(range(clip.n0, clip.n1 + 1, args.every))
    with Pool(args.procs, _init, (video, clip.dir, clip.n0, clip.n1, pos, set(seen), cmp_, args.tile, args.dark)) as p:
        tiles = p.map(_tile, frames, chunksize=8)

    con = {n: c for n, _, c in tiles if n in seen}
    weak = sorted(n for n, c in con.items() if c < 25)
    n_cmp = sum(1 for n, q in cmp_.items() if n != "_px" and (n not in pos or np.hypot(q[0] - pos[n][0], q[1] - pos[n][1]) > args.compare_px))
    print(f"{len(frames)} frames: {sum(n in seen for n in frames)} detected, {sum(n in pos and n not in seen for n in frames)} interpolated, "
          f"{sum(n not in pos for n in frames)} outside every track")
    print(f"contrast of the source under the detected positions: median {np.median(list(con.values())):.0f} DN, "
          f"minimum {min(con.values()):.0f} DN; below 25 DN in {len(weak)} frames: {weak[:40]}")
    if args.compare:
        print(f"--compare positions more than {args.compare_px:g} px away: {n_cmp}")

    tw, th = tiles[0][1].size
    head = 150
    font, small = ImageFont.truetype(FONT, 46), ImageFont.truetype(FONT, 30)
    per = int(np.ceil(len(tiles) / args.pages / args.cols)) * args.cols
    for k in range(args.pages):
        part = tiles[k * per:(k + 1) * per]
        if not part:
            break
        rows = int(np.ceil(len(part) / args.cols))
        sheet = Image.new("RGB", (args.cols * tw, head + rows * th), (18, 18, 18))
        d = ImageDraw.Draw(sheet)
        title = (rec["title"] if rec else video.name) + f"  ({video.name}, {clip.W}x{clip.H}, {clip.fps:g} fps)"
        d.text((24, 14), title + (f"   page {k + 1}/{args.pages}" if args.pages > 1 else ""), fill=(255, 255, 255), font=font)
        legend = [(GREEN, "detected in this frame"), (ORANGE, "interpolated (not detected in this frame)")]
        if args.compare:
            legend.append((RED, f"x: {Path(args.compare).name}, where it is > {args.compare_px:g} px away"))
        x = 24
        for col, text in legend:
            d.ellipse([x, 84, x + 30, 114], outline=col, width=4)
            d.text((x + 42, 80), text, fill=(230, 230, 230), font=small)
            x += 42 + d.textlength(text, font=small) + 60
        d.text((x, 80), f"frames {part[0][0]}-{part[-1][0]}, every {args.every}; t = (n - 1)/fps; inset: {CROP}-px crop at the position, x{ZOOM}, "
               "nearest-neighbour.  " + args.note, fill=(170, 170, 170), font=small)
        for i, (_, tile, _) in enumerate(part):
            sheet.paste(tile, ((i % args.cols) * tw, head + (i // args.cols) * th))
        name = f"{out}.jpg" if args.pages == 1 else f"{out}_p{k + 1}.jpg"
        sheet.save(name, quality=92, subsampling=0, optimize=True)
        print(f"wrote {name}  {sheet.size[0]}x{sheet.size[1]}  {Path(name).stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
