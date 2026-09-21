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
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import forensics as vf
from .progress import to_stderr
from .report import Found, emit, inputs_of, said_to_stderr

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


def sheet(clip, tracks, out, compare=None, compare_px=15.0, compare_name="the --compare track", every=1, cols=30,
          tile=384, pages=1, dark=False, note="", title=None, procs=10, say=print, progress=None, stop=None):
    """Every frame tiled with the tracked position circled: the check that a track is on
    the object all the way. `tracks` is a list of {frame: (x, y)}, merged with the first
    winning where they overlap, each interpolated only inside itself. Writes
    <out>_all_frames.jpg (or _p1.. with pages), and measures the contrast of whatever is
    under each detected position: a tracked position with no compact source under it is
    in `weak_frames`. The sheet still has to be looked at; nothing here says it was."""
    out = Path(f"{out}_all_frames")
    seen, pos = {}, {}
    for t in tracks:                                       # each track interpolates only inside itself
        t = {n: p for n, p in t.items() if clip.n0 <= n <= clip.n1}
        if not t:
            continue
        ip = vf.interp_track(t)
        for n in range(min(t), max(t) + 1):
            pos.setdefault(n, ip(n))
        for n, p in t.items():
            seen.setdefault(n, p)
            pos[n] = seen[n]
    if not seen:
        raise vf.Stop(f"the track has no position on frames {clip.n0}-{clip.n1}, so there is nothing to circle.",
                      vf.EXIT_NOTHING)
    cmp_ = {"_px": compare_px}
    if compare:
        cmp_.update({n: p for n, p in compare.items() if clip.n0 <= n <= clip.n1})

    frames = list(range(clip.n0, clip.n1 + 1, every))
    tiles = vf.pooled(procs, _tile, frames, _init, (clip.video, clip.dir, clip.n0, clip.n1, pos, set(seen), cmp_, tile, dark),
                      8, progress, stop, "track sheet: making the small pictures")

    con = {n: c for n, _, c in tiles if n in seen}
    weak = sorted(n for n, c in con.items() if c < 25)
    n_cmp = sum(1 for n, q in cmp_.items() if n != "_px" and (n not in pos or np.hypot(q[0] - pos[n][0], q[1] - pos[n][1]) > compare_px))
    fields = dict(frames=len(frames), detected=sum(n in seen for n in frames),
                  interpolated=sum(n in pos and n not in seen for n in frames),
                  outside_every_track=sum(n not in pos for n in frames),
                  contrast_dn=dict(median=float(np.median(list(con.values()))), minimum=float(min(con.values()))) if con else None,
                  weak_frames=weak, compared_away=n_cmp if compare else None, compare_px=compare_px if compare else None)

    tw, th = tiles[0][1].size
    head = 150
    font, small = ImageFont.truetype(FONT, 46), ImageFont.truetype(FONT, 30)
    per = int(np.ceil(len(tiles) / pages / cols)) * cols
    files = []
    for k in range(pages):
        part = tiles[k * per:(k + 1) * per]
        if not part:
            break
        rows = int(np.ceil(len(part) / cols))
        im = Image.new("RGB", (cols * tw, head + rows * th), (18, 18, 18))
        d = ImageDraw.Draw(im)
        d.text((24, 14), (title or clip.video.name) + f"  ({clip.video.name}, {clip.W}x{clip.H}, {clip.fps:g} fps)"
               + (f"   page {k + 1}/{pages}" if pages > 1 else ""), fill=(255, 255, 255), font=font)
        legend = [(GREEN, "detected in this frame"), (ORANGE, "interpolated (not detected in this frame)")]
        if compare:
            legend.append((RED, f"x: {compare_name}, where it is > {compare_px:g} px away"))
        x = 24
        for col, text in legend:
            d.ellipse([x, 84, x + 30, 114], outline=col, width=4)
            d.text((x + 42, 80), text, fill=(230, 230, 230), font=small)
            x += 42 + d.textlength(text, font=small) + 60
        d.text((x, 80), f"frames {part[0][0]}-{part[-1][0]}, every {every}; t = (n - 1)/fps; inset: {CROP}-px crop at the position, x{ZOOM}, "
               "nearest-neighbour.  " + note, fill=(170, 170, 170), font=small)
        for i, (_, t, _) in enumerate(part):
            im.paste(t, ((i % cols) * tw, head + (i // cols) * th))
        name = f"{out}.jpg" if pages == 1 else f"{out}_p{k + 1}.jpg"
        im.save(name, quality=92, subsampling=0, optimize=True)
        files.append(name)
        say(f"wrote {name}  {im.size[0]}x{im.size[1]}  {Path(name).stat().st_size / 1e6:.1f} MB")

    result = dict(sheet=files[0] if len(files) == 1 else ", ".join(files),
                  frames=f"{fields['detected']} detected, {fields['interpolated']} interpolated, "
                         f"{fields['outside_every_track']} outside every track")
    npw = []
    if con:
        result["source under the track"] = (f"median contrast {fields['contrast_dn']['median']:.0f} DN, minimum "
                                            f"{fields['contrast_dn']['minimum']:.0f} DN; below 25 DN in {len(weak)} frames")
    return Found("verify", result, fields, no_power=npw, files=files)


def said(fields):
    """What `mcdonald tracksheet` prints of a sheet, from its fields."""
    L = [f"{fields['frames']} frames: {fields['detected']} detected, {fields['interpolated']} interpolated, "
         f"{fields['outside_every_track']} outside every track"]
    c = fields["contrast_dn"]
    if c:
        L.append(f"contrast of the source under the detected positions: median {c['median']:.0f} DN, "
                 f"minimum {c['minimum']:.0f} DN; below 25 DN in {len(fields['weak_frames'])} frames: {fields['weak_frames'][:40]}")
    if fields["compared_away"] is not None:
        L.append(f"--compare positions more than {fields['compare_px']:g} px away: {fields['compared_away']}")
    return L


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
    ap.add_argument("--json", action="store_true",
                    help="print what the sheet found as JSON on stdout (the envelope every command prints); "
                         "everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        found, clip = _main(args)
    if args.json:
        emit(found.envelope("tracksheet", inputs_of(args), clip, said=lines))
    return 0


def _main(args):
    video, tag, rec = vf.resolve(args.video)
    clip = vf.Clip(video, args.workdir, args.n0, args.n1)
    found = sheet(clip, [vf.read_track(f) for f in args.track], vf.out_prefix(args.out, tag),
                  vf.read_track(args.compare) if args.compare else None, args.compare_px,
                  Path(args.compare).name if args.compare else "", args.every, args.cols, args.tile, args.pages,
                  args.dark, args.note, rec["title"] if rec else None, args.procs, progress=to_stderr())
    print("\n".join(said(found.fields)))
    return found, clip


if __name__ == "__main__":
    raise SystemExit(main())
