"""`mcdonald look` — see the clip, with no window.

The Qt window has three ways of finding the object: an overview of the whole
clip as tiles, the detector's candidates drawn on a frame, and a loupe under
the cursor. All three lived inside the window, so something driving the package
from a command line -- an agent with no display, which can open an image file
but cannot click -- could not see the clip at all. These are the same three, as
files.

    mcdonald look CLIP                          # the overview: evenly spaced frames, tiled and labelled
    mcdonald look CLIP --n0 380 --n1 440        # the same, of part of it
    mcdonald look CLIP --frame 408              # one frame, the detector's candidates ringed and numbered,
                                                #   and each candidate enlarged on a sheet beside it
    mcdonald look CLIP --frame 408 --size 21 --dark
    mcdonald look CLIP --frame 408 --at 1009,313    # the loupe: that place enlarged, with a scale to read from
    mcdonald look CLIP --n0 1 --n1 120 --propose    # what moves against the background, best first: each a strip
                                                #   of the clip's own pixels, and the marks that would take it
    mcdonald look CLIP --n0 1 --n1 120 --propose --more   # every thing that was kept, not only the best few

--propose is the window's Track -> Find the object (mcdonald.propose): the things
that move against the background, as a short list for someone to choose from, or
to reject. It extracts the frames it searches, so give it --n0/--n1 on a long clip.
It orders a list; it does not say which thing is the object.

Every form takes --json, which prints what was written and, for --frame, the
candidates as numbers. The candidates are there to be looked at, not trusted:
the detector finds compact sources, and which of them is the object -- or
whether none is -- is the judgment of whoever is looking. If that is an agent,
the marks it goes on to place with `mcdonald mark --set` say so.

Coordinates. The frame is written at its own size with nothing added round it,
so a position in the file is a position in the clip: pixel centres at integers,
as everywhere in the package. The enlarged views keep to that -- pixel (x, y)
fills a block that is *centred* on (x, y), and the ticks are drawn at pixel
centres -- which tests/test_measurement.py pins with a red pixel, as
tests/test_gui.py does for the windows.

The overview does not extract the clip. Its frames come from one pass of ffmpeg
that keeps only the frames asked for, selected by number, so they are the
frames they say they are; a whole 1080p clip would otherwise be a gigabyte of
PNGs to look at forty of them.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import autolink
from . import forensics as vf
from .figures import pil_font
from .mark import CLASSES, COLOURS, MarkSet
from .report import emit, envelope

RING = "#35e0c8"                                   # not a class colour: a candidate is nobody's mark
INK, PAPER = "#f2f0e9", "#111111"


# ---- the overview -----------------------------------------------------------------------
def overview_frames(n0, n1, tiles):
    return [int(n) for n in np.unique(np.linspace(n0, n1, min(tiles, n1 - n0 + 1)).round())]


def thumbnails(clip, frames, width):
    """{frame: PIL image} at `width` px. From the extracted frames where they are all on
    disk already; else one pass of ffmpeg selecting exactly these frame numbers."""
    h = int(round(width * clip.H / clip.W / 2)) * 2
    if all(clip.path(n).exists() for n in frames):
        return {n: Image.fromarray(clip.rgb(n).astype(np.uint8)).resize((width, h), Image.LANCZOS) for n in frames}
    with tempfile.TemporaryDirectory(prefix="mcdonald-look-") as td:
        sel = "+".join(f"eq(n,{n - 1})" for n in frames)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip.video), "-vf", f"select='{sel}',scale={width}:{h}",
                        "-vsync", "0", "-frames:v", str(len(frames)), f"{td}/%05d.png"], check=True)
        got = sorted(Path(td).glob("*.png"))
        return {n: Image.open(p).convert("RGB").copy() for n, p in zip(frames, got)}


def overview(clip, out, tiles=40, width=384, cols=8):
    """Evenly spaced frames of the clip's window as one sheet, each labelled with its
    frame number and time. Returns the frames shown."""
    frames = overview_frames(clip.n0, clip.n1, tiles)
    thumbs = thumbnails(clip, frames, width)
    frames = [n for n in frames if n in thumbs]
    cols = min(cols, len(frames))
    rows = (len(frames) + cols - 1) // cols
    th, bar, font = next(iter(thumbs.values())).size[1], 26, pil_font(18)
    sheet = Image.new("RGB", (cols * width, rows * (th + bar)), PAPER)
    dr = ImageDraw.Draw(sheet)
    for i, n in enumerate(frames):
        x, y = i % cols * width, i // cols * (th + bar)
        sheet.paste(thumbs[n], (x, y))
        dr.text((x + 6, y + th + 3), f"frame {n}    {(n - 1) / clip.fps:.2f} s", fill=INK, font=font)
    sheet.save(out)
    return frames


# ---- one frame --------------------------------------------------------------------------
def _cross(dr, x, y, colour, arms=(4, 14), width=2):
    a, b = arms
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        dr.line([(x + a * dx, y + a * dy), (x + b * dx, y + b * dy)], fill=colour, width=width)


def _ticks(dr, x0, y0, w, h, to_px, step, font, every=1):
    """A scale along the top and left edges, in the clip's coordinates, inside the image."""
    for v in range(int(np.ceil(x0 / step)) * step, int(x0 + w) + 1, step):
        px = to_px(v, y0)[0]
        dr.line([(px, 0), (px, 9)], fill=INK, width=1)
        if (v // step) % every == 0:
            dr.text((px + 3, 1), str(v), fill=INK, font=font, stroke_width=2, stroke_fill="#000000")
    for v in range(int(np.ceil(y0 / step)) * step, int(y0 + h) + 1, step):
        py = to_px(x0, v)[1]
        dr.line([(0, py), (9, py)], fill=INK, width=1)
        if (v // step) % every == 0 and py > 16:
            dr.text((12, py - 9), str(v), fill=INK, font=font, stroke_width=2, stroke_fill="#000000")


def marks_on(ms, n):
    return [(c, ms.marks[c][n], COLOURS[CLASSES.index(c) % len(COLOURS)] if c in CLASSES else "#ffffff")
            for c in ms.marks if n in ms.marks[c]] if ms else []


def frame_view(clip, n, cands, out, ms=None):
    """Frame n at its own size -- a position in this file is a position in the clip -- with
    the candidates ringed and numbered strongest first, any marks drawn, and a scale."""
    img = Image.fromarray(clip.rgb(n).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    font, small = pil_font(20, bold=True), pil_font(14)
    _ticks(dr, 0, 0, clip.W, clip.H, lambda x, y: (x, y), 100, small, every=2)
    for rank, (x, y, _) in enumerate(cands, 1):
        r = 16
        dr.ellipse([x - r, y - r, x + r, y + r], outline=RING, width=2)
        dr.text((x + r + 3, y - r - 6), str(rank), fill=RING, font=font, stroke_width=2, stroke_fill="#000000")
    for _, (x, y), colour in marks_on(ms, n):
        _cross(dr, x, y, colour)
    img.save(out)
    return out


def crop_view(clip, n, x, y, out=None, box=96, zoom=6, cands=(), ms=None, label=None):
    """The loupe: `box` px of frame n about (x, y), enlarged `zoom` times without
    interpolation, with a scale in the clip's coordinates. Returns the image.

    Pixel (i, j) becomes the block [zoom*(i-x0), zoom*(i-x0+1)), whose middle is where
    anything *at* (i, j) is drawn: a position p maps to (p - x0 + 0.5) * zoom - 0.5."""
    x0, y0 = int(round(x)) - box // 2, int(round(y)) - box // 2
    rgb = np.pad(clip.rgb(n).astype(np.uint8), ((box, box), (box, box), (0, 0)), mode="constant")
    tile = Image.fromarray(rgb[y0 + box:y0 + 2 * box, x0 + box:x0 + 2 * box]).resize((box * zoom, box * zoom), Image.NEAREST)
    dr = ImageDraw.Draw(tile)

    def to_px(u, v):
        return (u - x0 + 0.5) * zoom - 0.5, (v - y0 + 0.5) * zoom - 0.5
    _ticks(dr, x0, y0, box - 1, box - 1, to_px, 10, pil_font(13), every=2)
    for rank, (cx, cy, _) in enumerate(cands, 1):
        if x0 <= cx < x0 + box and y0 <= cy < y0 + box:
            px, py = to_px(cx, cy)
            dr.ellipse([px - 5 * zoom, py - 5 * zoom, px + 5 * zoom, py + 5 * zoom], outline=RING, width=2)
            dr.text((px + 5 * zoom + 3, py - 5 * zoom - 4), str(rank), fill=RING, font=pil_font(18, bold=True),
                    stroke_width=2, stroke_fill="#000000")
    for _, (mx, my), colour in marks_on(ms, n):
        if x0 <= mx < x0 + box and y0 <= my < y0 + box:
            _cross(dr, *to_px(mx, my), colour, arms=(2 * zoom, 5 * zoom))
    if label is None:                                # the place asked about, unless this is a candidate's tile
        _cross(dr, *to_px(x, y), INK, arms=(zoom, 3 * zoom), width=1)
    if out:
        tile.save(out)
    return tile


def candidate_sheet(clip, n, cands, out, box=64, zoom=4, cols=5, ms=None):
    """Every candidate enlarged, in the detector's order, captioned with its number,
    position and response: what "which of these is the object?" is answered from."""
    if not cands:
        return None
    cell, bar, font = box * zoom, 24, pil_font(16)
    cols = min(cols, len(cands))
    rows = (len(cands) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + bar)), PAPER)
    dr = ImageDraw.Draw(sheet)
    for i, (x, y, v) in enumerate(cands):
        cx, cy = i % cols * cell, i // cols * (cell + bar)
        sheet.paste(crop_view(clip, n, x, y, box=box, zoom=zoom, cands=cands, ms=ms, label=i + 1), (cx, cy))
        dr.text((cx + 5, cy + cell + 3), f"#{i + 1}   ({x:.1f}, {y:.1f})   response {v:.0f}", fill=INK, font=font)
    sheet.save(out)
    return out


def look_at_frame(clip, n, out_prefix, size=9.0, dark=False, at=None, masks=None, ms=None, rows=None):
    """Everything `--frame` writes. Returns (files, results)."""
    masks = vf.static_masks(clip) if masks is None else masks
    cands = vf.frame_candidates(clip, n, masks, rows, float(size), bool(dark), autolink.MIN_RESP)
    stem = f"{out_prefix}_look_f{n:05d}_{size:g}px{'_dark' if dark else ''}"
    files = [frame_view(clip, n, cands, f"{stem}.png", ms),
             candidate_sheet(clip, n, cands, f"{stem}_candidates.png", ms=ms)]
    if at:
        crop_view(clip, n, at[0], at[1], f"{out_prefix}_look_f{n:05d}_at_{at[0]:g}_{at[1]:g}.png", cands=cands, ms=ms)
        files.append(f"{out_prefix}_look_f{n:05d}_at_{at[0]:g}_{at[1]:g}.png")
    results = {"frame": n, "t_s": round((n - 1) / clip.fps, 4),
               "detector": {"size_px": float(size), "dark": bool(dark), "min_resp": autolink.MIN_RESP,
                            "static_masks_from_frames": [clip.n0, clip.n1]},
               "candidates": [{"rank": i, "x": round(x, 2), "y": round(y, 2), "response": round(v, 1)}
                              for i, (x, y, v) in enumerate(cands, 1)],
               "marks_on_this_frame": {c: list(xy) for c, xy, _ in marks_on(ms, n)}}
    return [f for f in files if f], results


# ---- the command ------------------------------------------------------------------------
def proposal_sheet(clip, props, out):
    """One row for each proposal: its number, what it is like, and its strip."""
    from . import propose
    font = pil_font(15)
    rows = [propose.strip(clip, p) for p in props]
    w = max(r[0].shape[1] for r in rows)
    sheet = Image.new("RGB", (w, sum(r[0].shape[0] + 44 for r in rows)), PAPER)
    dr, y = ImageDraw.Draw(sheet), 0
    for i, (p, (pix, shown)) in enumerate(zip(props, rows), 1):
        dr.text((6, y + 3), f"{i}.  {p.strength()} ({p.score:.1f})   {p.describe()}"[:int(w / 7.4)], fill=INK, font=font)
        dr.text((6, y + 23), "frames " + ", ".join(map(str, shown)), fill=RING, font=font)
        sheet.paste(Image.fromarray(pix), (0, y + 44))
        y += pix.shape[0] + 44
    sheet.save(out)
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__[__doc__.index("    mcdonald look CLIP "):])
    ap.add_argument("video")
    ap.add_argument("--frame", type=int, metavar="N", help="look at this frame: candidates ringed, and each enlarged")
    ap.add_argument("--at", metavar="X,Y", help="with --frame: also enlarge this place")
    ap.add_argument("--propose", action="store_true",
                    help="find what moves against the background in --n0..--n1, best first: a sheet of strips, and with "
                         "--json the marks that would take each. It proposes; which one is the object is yours to say")
    ap.add_argument("--more", action="store_true",
                    help="with --propose: list every thing that was kept (up to 30), not only the best few -- the window's "
                         "\"Show more\". In a hard clip, where every row says weak, the object may be further down")
    ap.add_argument("--procs", type=int, default=10)
    ap.add_argument("--size", type=float, default=9.0, help="the size of source the detector looks for, px (default 9)")
    ap.add_argument("--dark", action="store_true", help="look for an object darker than its surroundings")
    ap.add_argument("--n0", type=int, help="first frame: of the overview, or of the frames the static masks are made from")
    ap.add_argument("--n1", type=int)
    ap.add_argument("--tiles", type=int, default=40, help="how many frames the overview shows (default 40)")
    ap.add_argument("--marks", metavar="JSON", help="draw these marks too (default: the case directory's, if there are any)")
    ap.add_argument("--mask-rows")
    ap.add_argument("--workdir")
    ap.add_argument("--out", metavar="DIR", help="case directory (default: ./<tag>)")
    ap.add_argument("--json", action="store_true", help="print what was written, and the candidates, as JSON on stdout")
    args = ap.parse_args()
    say = (lambda *a: print(*a, file=sys.stderr)) if args.json else print

    video, tag, _ = vf.resolve(args.video)
    out = vf.out_prefix(args.out, tag)
    inputs = {k: v for k, v in vars(args).items() if v not in (None, False) and k != "json"}
    if args.propose:
        from . import propose
        from .progress import to_stderr
        clip = vf.Clip(video, args.workdir, args.n0, args.n1, extract=False)
        say(vf.cost_text(clip.cost()))
        clip.extract()
        progress = to_stderr()
        props = propose.find(clip, vf.static_masks(clip, progress=progress), procs=args.procs, progress=progress, keep=30)
        kept, props = len(props), props if args.more else propose.shortlist(props)
        if not props:
            text = (f"nothing in frames {clip.n0}-{clip.n1} moves against the background in a line for three frames or more: "
                    "look with --frame, and mark it with `mcdonald mark --set`")
            if args.json:
                emit(envelope("look", inputs, clip, [], {"proposals": []}, no_power=[("proposals", text)], exit_code=vf.EXIT_NOTHING, error=text))
            raise vf.Stop(text, vf.EXIT_NOTHING) if not args.json else SystemExit(vf.EXIT_NOTHING)
        path = proposal_sheet(clip, props, f"{out}_look_proposals_{clip.n0}_{clip.n1}.png")
        say(f"{len(props)} thing{'s' if len(props) != 1 else ''} that move against the background in frames {clip.n0}-{clip.n1}, best first:")
        for i, p in enumerate(props, 1):
            say(f"  {i}. {p.strength():6s} {p.score:5.1f}   {p.describe()}")
        if kept > len(props):
            say(f"  ({kept - len(props)} more were kept and scored lower: --more lists them)")
        say(f"wrote {path}  -- look at it. This orders a list; it does not say which thing is the object, or that any is.")
        say("to take one:  " + propose.accept_command(args.video, props[0], 1, len(props)))
        if args.json:
            emit(envelope("look", inputs, clip, [path],
                          {"proposals": [dict(p.to_dict(), rank=i, to_accept=propose.accept_command(args.video, p, i, len(props)))
                                         for i, p in enumerate(props, 1)]},
                          needs=[f"a look at {path}: the list is what moves against the background, ordered by how much like an "
                                 "object it moves. Which one is the object, or whether none is, is the judgment of whoever is "
                                 "looking, and the marks that record it say whose it was"],
                          notes=["The positions are centroids of a smoothed residual, good to a few pixels: they are for seeding "
                                 "the link, which measures the track with the package's own detector. A weak proposal is often "
                                 "symbology that moves, or terrain under a pan."]))
        return 0
    if args.frame is None:
        clip = vf.Clip(video, args.workdir, args.n0, args.n1, extract=False)
        path = f"{out}_look_overview_{clip.n0}_{clip.n1}.png"
        frames = overview(clip, path, args.tiles)
        say(f"{video.name}: {clip.W}x{clip.H}, {clip.info['fps']} fps, frames {clip.n0}-{clip.n1}")
        say(f"wrote {path}  -- {len(frames)} frames, {frames[0]} to {frames[-1]}. Narrow it with --n0/--n1; "
            "look at one frame with --frame N")
        if args.json:
            emit(envelope("look", inputs, clip, [path], {"frames_shown": frames,
                                                         "frames_in_clip": clip.info["nb_frames"] or clip.n1}))
        return 0

    # one frame. The static masks need the scene to move under the symbology, so they are
    # made from a window of frames about this one unless --n0/--n1 say which
    total = vf.Clip(video, args.workdir, extract=False).n1
    if not 1 <= args.frame <= total:
        raise vf.Stop(f"--frame {args.frame}: {video.name} has frames 1-{total}")
    n0 = args.n0 or max(1, args.frame - 30)
    n1 = args.n1 or min(total, args.frame + 30)
    if not n0 <= args.frame <= n1:
        raise vf.Stop(f"--frame {args.frame} is outside --n0/--n1 ({n0}-{n1})", vf.EXIT_USAGE)
    clip = vf.Clip(video, args.workdir, n0, n1, extract=False)
    say(vf.cost_text(clip.cost()))
    clip.extract()
    at = None
    if args.at:
        try:
            at = tuple(float(v) for v in args.at.split(","))
            assert len(at) == 2
        except (ValueError, AssertionError):
            raise vf.Stop(f"--at {args.at}: give it as X,Y in pixels, e.g. --at 1009,313", vf.EXIT_USAGE)
    marks = args.marks or f"{out}_marks.json"
    ms = MarkSet(tag, video, clip.fps).load(marks) if Path(marks).exists() else None
    files, results = look_at_frame(clip, args.frame, out, args.size, args.dark, at, ms=ms, rows=vf.parse_rows(args.mask_rows))
    c = results["candidates"]
    say(f"frame {args.frame}: {len(c)} candidate{'' if len(c) == 1 else 's'} at {args.size:g} px "
        f"{'dark' if args.dark else 'bright'}, strongest first")
    for k in c:
        say(f"  #{k['rank']:<3} ({k['x']:7.1f}, {k['y']:7.1f})   response {k['response']:.0f}")
    say("The detector finds compact sources; which one is the object, if any, is yours to say. "
        "An object much larger or smaller than --size is missed outright: try 5, 9, 15, 21, 31, 45, and --dark.")
    for f in files:
        say(f"wrote {f}")
    if args.json:
        emit(envelope("look", inputs, clip, files, results,
                      no_power=[] if c else [("candidates", f"nothing compact at {args.size:g} px "
                                                            f"{'dark' if args.dark else 'bright'} on this frame")]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
