"""One figure style, and the two traps that cost a figure each.

Before this module the per-clip scripts each set their own rcParams (26 of
them), hard-coded their own font path (16), and three copied the same palette
block verbatim. This is that, once.

**Trap 1 — the PIL font.** matplotlib ships its own DejaVu, so matplotlib text
is fine anywhere. PIL does not: it looks for system font files, and on a host
without DejaVu installed `ImageFont.truetype("DejaVuSans.ttf", 40)` does not
raise — it silently falls back to an ~8 px bitmap face that **ignores the size
argument**, and the label comes out unreadably small. `pil_font` resolves a
real file and raises if it cannot, which is the behaviour you want.

**Trap 2 — `bbox_inches="tight"`.** It changes the output size, so a figure
drawn for a column comes out at some other width and every font size in it is
wrong once LaTeX scales it back. Draw at the width the document will print
(`FigureSize`), and crop by measuring label extents instead. `save` refuses
the tight path by default.

**Colour.** The ink tokens are the house style the published figures use:
near-black primary, two greys, one accent. Data normally wears the accent or
plain ink — most figures here are one series, and a family of parallel lines
is better labelled directly than coloured. For the cases that genuinely need
several distinguishable series, SERIES is a validated categorical order
(worst adjacent CVD ΔE 9.1, normal-vision ΔE 19.6 on a light surface). Two
rules come with it: assign slots in fixed order and never cycle, and because
the lighter slots fall below 3:1 against white, **every series carries a
direct label or a legend entry** — colour is never the only cue.
"""
import math
import os
import textwrap
from pathlib import Path

import numpy as np

# ---- tokens ----------------------------------------------------------------------------
SURFACE = "#ffffff"
PRIMARY = "#0b0b0b"      # near-black ink: the data, and headings
SECONDARY = "#52514e"    # axis labels, tick text
MUTED = "#898781"        # axis lines, de-emphasised text
FAINT = "#dedcd6"        # grid
DIM = "#e5e3de"          # filled bands
ACCENT = "#8a5c12"       # the one highlight

# Validated categorical order (light surface). Fixed order, never cycled; a
# ninth series folds into "other" or becomes small multiples.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]

# Verdict colours, reserved. Never reused as a series hue, and always shipped
# with the word as well as the colour.
VERDICT = {"PASS": "#1baf7a", "FLAG": "#e34948",
           "INCONCLUSIVE": "#eda100", "NO POWER": MUTED}


class FigureSize:
    """Widths in inches that documents actually print at.

    Draw at these. A figure drawn at 8 in and then scaled to 4.875 in by
    \\includegraphics has every font in it halved."""
    AIAA_COLUMN = 4.875      # 0.75\textwidth under new-aiaa
    AIAA_FULL = 6.5
    SLIDE = 10.0
    NOTE = 7.4               # the working-note default


# ---- the house style (Jacob, 2026-11-07) ---------------------------------------------------
# After the figures of his 2026 EBM/THAI paper (~/local/archive/published/2026ebmTHAI), with his own changes: a full black
# box with the ticks in on all four sides and no grid; one sans-serif face, tick labels 10 pt, axis labels 11 pt in bold
# (his), titles 12 pt in normal weight and short -- a name, the finding being the caption's; the paper's colours; legends
# inside the axes, borderless on white; no panel letters (his: the text names a panel by its place, "upper left"); and no
# text over a line (his). `setup` sets it before a figure is drawn, `dress` puts the frame on whatever code drew one, and
# `clear` moves text and legends off the lines; `save` does both, so every figure that goes through it is in the style.
BLUE, AMBER, RED, PURPLE, CYAN = "#2166ac", "#e08000", "#d73027", "#8e44ad", "#00cec9"
HOUSE = [BLUE, AMBER, RED, PURPLE, CYAN]   # in this order: a first series blue, a second amber; measured points red
TICK_PT, LABEL_PT, TITLE_PT, LEGEND_PT = 10, 11, 12, 9
HOUSE_RC = {
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans", "Liberation Sans", "Arial"], "font.size": TICK_PT,
    "axes.labelsize": LABEL_PT, "axes.labelweight": "bold", "axes.titlesize": TITLE_PT, "axes.titleweight": "normal",
    "axes.edgecolor": "black", "axes.linewidth": 0.8, "axes.labelcolor": "black", "axes.grid": False,
    "axes.spines.top": True, "axes.spines.right": True, "axes.facecolor": "#ffffff",
    "xtick.direction": "in", "ytick.direction": "in", "xtick.top": True, "ytick.right": True,
    "xtick.labelsize": TICK_PT, "ytick.labelsize": TICK_PT, "xtick.color": "black", "ytick.color": "black",
    "legend.fontsize": LEGEND_PT, "legend.frameon": True, "legend.framealpha": 0.85, "legend.edgecolor": "none",
    "legend.facecolor": "#ffffff", "lines.linewidth": 1.8, "text.color": "#0b0b0b",
    "figure.facecolor": "#ffffff", "savefig.facecolor": "#ffffff", "savefig.dpi": 200,
}
# what `save` could not clear: (path, what), for the tests to hold every figure to the style
CLASHES = []


def setup(size=None, family=None):
    """The house rcParams (HOUSE_RC). Call once, before creating a figure. `size` and `family` are kept for the old
    callers and are not used: one size of type in every figure is the point."""
    import matplotlib
    if not os.environ.get("DISPLAY"):
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from cycler import cycler
    plt.rcParams.update(dict(HOUSE_RC, **{"axes.prop_cycle": cycler(color=HOUSE)}))
    return plt


def dress(fig):
    """The house frame on every axes of `fig`, whatever the code that drew it set: all four sides in black, the ticks in
    on each side (on a twin's side, the twin's), no grid, the tick labels 10 pt, the axis labels 11 pt bold in black,
    the titles 12 pt in normal weight, and each legend borderless on white. Axes drawn with their axis off (a picture)
    are left as they are."""
    axes = [a for a in fig.axes if a.axison]
    for ax in axes:
        if getattr(ax, "_colorbar", None) is not None:          # a colour bar keeps its outline; its ticks go in
            ax.tick_params(which="both", direction="in", colors="black", labelsize=TICK_PT)
            continue
        pos = ax.get_position().bounds
        twins = [b for b in axes if b is not ax and np.allclose(b.get_position().bounds, pos)]
        right_owned = any(b.yaxis.get_label_position() == "right" for b in twins)   # a twinx holds the right side
        top_owned = any(b.xaxis.get_label_position() == "top" for b in twins)
        mine_right = ax.yaxis.get_label_position() == "right" and twins
        mine_top = ax.xaxis.get_label_position() == "top" and twins
        for s in ax.spines.values():
            s.set_visible(True)
            s.set_color("black")
            s.set_linewidth(0.8)
        ax.tick_params(which="both", direction="in", colors="black", labelsize=TICK_PT,
                       left=not mine_right, right=not right_owned, bottom=not mine_top, top=not top_owned)
        ax.grid(False)
        for lab in (ax.xaxis.label, ax.yaxis.label):
            lab.set_fontsize(LABEL_PT)
            lab.set_fontweight("bold")
            lab.set_color("black")
        for t in (ax.title, getattr(ax, "_left_title", None), getattr(ax, "_right_title", None)):
            if t is not None and t.get_text():
                t.set_fontsize(TITLE_PT)
                t.set_fontweight("normal")
    for leg in [a.get_legend() for a in fig.axes] + list(fig.legends):
        if leg is not None:
            leg.set_frame_on(True)
            fr = leg.get_frame()
            fr.set_facecolor(SURFACE)
            fr.set_alpha(0.85)
            fr.set_edgecolor("none")
            for t in leg.get_texts():
                t.set_fontsize(LEGEND_PT)
    return fig


def _lines_px(ax):
    """The axes' lines in display pixels: [polylines, each (n, 2)], [marker points, each (m, 2)], split where a line has a
    gap (a NaN), so that no false segment joins its two sides."""
    from matplotlib.collections import LineCollection
    polys, points = [], []

    def add(xy, line, marks):
        ok = np.isfinite(xy).all(1)
        if marks:
            points.append(xy[ok])
        if line:
            cut = np.flatnonzero(~ok)
            for part in np.split(xy, cut):
                part = part[np.isfinite(part).all(1)]
                if len(part) > 1:
                    polys.append(part)
    for ln in ax.get_lines():
        if not ln.get_visible() or ln.get_alpha() == 0:
            continue
        try:
            xy = ln.get_transform().transform(np.asarray(ln.get_xydata(), float))
        except (ValueError, TypeError):
            continue
        add(xy, ln.get_linestyle() not in ("None", "", " ", "none") and ln.get_linewidth() > 0,
            ln.get_marker() not in (None, "None", "", " ", "none"))
    for c in ax.collections:
        if isinstance(c, LineCollection) and c.get_visible():
            for seg in c.get_segments():
                add(c.get_transform().transform(np.asarray(seg, float)), True, False)
    return polys, points


def _crosses(polys, points, box):
    """Whether any line or marker point touches `box` (x0, y0, x1, y1): a vertex in it, or a segment through it
    (Liang-Barsky, all segments at once)."""
    x0, y0, x1, y1 = box
    for pts in points:
        if len(pts) and ((pts[:, 0] >= x0) & (pts[:, 0] <= x1) & (pts[:, 1] >= y0) & (pts[:, 1] <= y1)).any():
            return True
    for xy in polys:
        if ((xy[:, 0] >= x0) & (xy[:, 0] <= x1) & (xy[:, 1] >= y0) & (xy[:, 1] <= y1)).any():
            return True
        p, d = xy[:-1], np.diff(xy, axis=0)
        lo, hi = np.zeros(len(p)), np.ones(len(p))
        for k, a, b in ((0, x0, x1), (1, y0, y1)):
            dk, pk = d[:, k], p[:, k]
            flat = dk == 0
            with np.errstate(divide="ignore", invalid="ignore"):
                t1, t2 = (a - pk) / dk, (b - pk) / dk
            lo = np.maximum(lo, np.where(flat, -np.inf, np.minimum(t1, t2)))
            hi = np.minimum(hi, np.where(flat, np.inf, np.maximum(t1, t2)))
            lo = np.where(flat & ((pk < a) | (pk > b)), 2.0, lo)
        if (lo <= hi).any():
            return True
    return False


def _box(artist, renderer, pad=1.5):
    b = artist.get_window_extent(renderer)
    return (b.x0 - pad, b.y0 - pad, b.x1 + pad, b.y1 + pad)


def _meet(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _inside(a, outer):
    return a[0] >= outer[0] and a[1] >= outer[1] and a[2] <= outer[2] and a[3] <= outer[3]


def _move(t, dx, dy, ax):
    """Move a text by (dx, dy) display pixels in its own coordinates; False where they cannot be inverted."""
    from matplotlib.text import Annotation
    if isinstance(t, Annotation):
        coords = t.anncoords if isinstance(t.anncoords, str) else None
        x, y = t.xyann
        if coords == "offset points":
            t.xyann = (x + dx * 72.0 / t.figure.dpi, y + dy * 72.0 / t.figure.dpi)
        elif coords == "offset pixels":
            t.xyann = (x + dx, y + dy)
        elif coords in ("data", "axes fraction"):
            tr = ax.transData if coords == "data" else ax.transAxes
            t.xyann = tuple(tr.inverted().transform(tr.transform((x, y)) + (dx, dy)))
        else:
            return False
        return True
    tr = t.get_transform()
    t.set_position(tuple(tr.inverted().transform(tr.transform(t.get_position()) + (dx, dy))))
    return True


def clear(fig, reach=24, step=2):
    """Each legend and text in an axes moved off its lines (Jacob, 2026-11-07: "make sure text does not overlap with
    lines"), and off the other texts there: a legend to the first of matplotlib's nine places inside the axes that is
    clear, a text by the smallest shift within `reach` pixels that lands it clear and inside the axes. The reach is
    small on purpose: a label moved far from what it names (a band's name out of its band, "Mach 1" off its line) says
    something false, so a text with no clear place near it is left and reported, for its figure's layout to fix. Returns what is
    left, [(axes, text, what)], after also reporting text that overlaps text elsewhere in the figure (an axis label over
    a neighbour's numbers) or runs off the figure: those need the layout, not a nudge."""
    from matplotlib.text import Text
    if not hasattr(fig.canvas, "get_renderer"):       # a bare Figure() has no drawing canvas: give it Agg's (audio's figure)
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        FigureCanvasAgg(fig)
    fig.draw_without_rendering()                      # the layout, without the pixels: a full draw doubled each figure's time
    r = fig.canvas.get_renderer()
    left = []
    offsets = sorted(((dx, dy) for dx in range(-reach, reach + 1, step) for dy in range(-reach, reach + 1, step)),
                     key=lambda o: math.hypot(*o))[1:]
    for ax in fig.axes:
        texts = [t for t in ax.texts if t.get_visible() and t.get_text().strip()]
        leg = ax.get_legend()
        if not texts and leg is None:
            continue
        polys, points = _lines_px(ax)
        abox = _box(ax, r, pad=0)
        placed = []
        if leg is not None and leg.get_visible():
            lb = _box(leg, r)
            if _meet(lb, abox) and _crosses(polys, points, lb):
                for loc in ("upper right", "upper left", "lower left", "lower right", "center right", "center left",
                            "upper center", "lower center", "center"):
                    leg.set_loc(loc)
                    lb = _box(leg, r)
                    if _inside(lb, abox) and not _crosses(polys, points, lb) and not any(_meet(lb, _box(t, r)) for t in texts):
                        break
                else:
                    left.append((ax, leg, "the legend crosses a line wherever it goes inside the axes"))
            placed.append(_box(leg, r))
        for t in texts:
            tb = _box(t, r)
            if not _meet(tb, abox):               # outside the axes, where no line is drawn: but not over another, nor off
                fb = _box(fig, r, pad=0)
                if not _inside(tb, (fb[0] - 1, fb[1] - 1, fb[2] + 1, fb[3] + 1)):
                    left.append((ax, t, f"'{t.get_text()[:40]}' runs off the figure"))
                elif any(_meet(tb, p) for p in placed):
                    left.append((ax, t, f"'{t.get_text()[:40]}' overlaps another label beside the plot"))
                placed.append(tb)
                continue
            if not _crosses(polys, points, tb) and not any(_meet(tb, p) for p in placed):
                placed.append(tb)
                continue
            found = moved = False
            for dx, dy in offsets:
                nb = (tb[0] + dx, tb[1] + dy, tb[2] + dx, tb[3] + dy)
                if _inside(nb, abox) and not _crosses(polys, points, nb) and not any(_meet(nb, p) for p in placed):
                    found, moved = True, _move(t, dx, dy, ax)    # moved False where its coordinates cannot be (a mixed pair)
                    if moved:
                        tb = nb
                    break
            if not moved:
                left.append((ax, t, f"'{t.get_text()[:40]}' crosses a line, and its coordinates cannot be moved" if found else
                                    f"'{t.get_text()[:40]}' crosses a line or another label, with no clear place within "
                                    f"{reach} pixels"))
            placed.append(tb)
    # text over text elsewhere in the figure, and text off the figure: for the layout to fix
    fbox = _box(fig, r, pad=0)
    for leg in fig.legends:
        if leg.get_visible() and not _inside(_box(leg, r, pad=0), (fbox[0] - 1, fbox[1] - 1, fbox[2] + 1, fbox[3] + 1)):
            left.append((None, leg, "the legend runs off the figure"))
    labelled = []
    for ax in fig.axes:
        for t in [ax.xaxis.label, ax.yaxis.label, ax.title, getattr(ax, "_left_title", None), getattr(ax, "_right_title", None)]:
            if isinstance(t, Text) and t.get_visible() and t.get_text().strip():
                labelled.append((ax, t, _box(t, r, pad=0)))
    for t in fig.texts:
        if t.get_visible() and t.get_text().strip():
            labelled.append((None, t, _box(t, r, pad=0)))
    ticks = [(ax, _box(lab, r, pad=0)) for ax in fig.axes if ax.axison
             for lab in ax.get_xticklabels() + ax.get_yticklabels() if lab.get_visible() and lab.get_text()]
    for i, (ax, t, b) in enumerate(labelled):
        if not _inside(b, (fbox[0] - 1, fbox[1] - 1, fbox[2] + 1, fbox[3] + 1)):
            left.append((ax, t, f"'{t.get_text()[:40]}' runs off the figure"))
        for ax2, t2, b2 in labelled[i + 1:]:
            if _meet(b, b2):
                left.append((ax, t, f"'{t.get_text()[:30]}' overlaps '{t2.get_text()[:30]}'"))
        for ax2, b2 in ticks:
            if ax2 is not ax and _meet(b, b2):
                left.append((ax, t, f"'{t.get_text()[:30]}' overlaps another plot's numbers"))
                break
    return left


def halo(width=3.4):
    """White stroke behind a label so it survives crossing a line."""
    from matplotlib import patheffects as pe
    return [pe.withStroke(linewidth=width, foreground=SURFACE)]


# ---- fonts for PIL ----------------------------------------------------------------------
_PIL_CANDIDATES = [
    "/usr/share/fonts/liberation-sans-fonts/LiberationSans-{w}.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-{w}.ttf",
    "/usr/share/fonts/TTF/LiberationSans-{w}.ttf",
    "/Library/Fonts/Arial{mac}.ttf",
    "/System/Library/Fonts/Supplemental/Arial{mac}.ttf",     # macOS 10.15 on: /Library/Fonts has no Arial
    "/usr/share/fonts/truetype/dejavu/DejaVuSans{dj}.ttf",
    "{mpl}/fonts/ttf/DejaVuSans{dj}.ttf",                    # matplotlib's own: every platform has one
]


def pil_font(size, bold=False):
    """A real TrueType face at `size`, or an exception.

    Never returns ImageFont.load_default(): that face ignores `size`, so a
    caller asking for 40 px silently gets about 8 and the figure ships
    unreadable. If this raises, install a font rather than catching it."""
    from PIL import ImageFont
    import matplotlib
    w = "Bold" if bold else "Regular"
    for pat in _PIL_CANDIDATES:
        path = pat.format(w=w, mac=" Bold" if bold else "", dj="-Bold" if bold else "", mpl=matplotlib.get_data_path())
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise FileNotFoundError(
        f"no TrueType font found for PIL at size {size}. Tried: "
        + ", ".join(_PIL_CANDIDATES)
        + ". Install Liberation or DejaVu; do not fall back to load_default(), "
          "which ignores the size argument and renders ~8 px.")


def text_extent(draw, xy, text, font, **kw):
    """Measured bounding box of text as it will actually render.

    Measure, never compute from the size: the face may not be the one asked
    for, and glyph metrics are not the point size."""
    return draw.textbbox(xy, text, font=font, **kw)


# ---- saving -------------------------------------------------------------------------------
def save(fig, path, dpi=200, tight=False, quiet=False):
    """Save at the size the figure was drawn, in the house style: `dress` and `clear` first, what `clear` could not fix
    said on stderr and kept in CLASHES (the tests hold every figure to none). `tight=True` must be deliberate."""
    import sys
    dress(fig)
    log = os.environ.get("MCDONALD_FIGURE_CLASHES")     # the test job's log: every process's figures, subprocesses too
    for ax, t, what in clear(fig):
        CLASHES.append((str(path), what))
        print(f"  ! {Path(str(path)).name}: {what}", file=sys.stderr)
        if log:
            with open(log, "a", encoding="utf-8") as fh:
                fh.write(f"{Path(str(path)).name}\t{what}\n")
    if tight:
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
    else:
        fig.savefig(path, dpi=dpi)
    if not quiet:
        print(f"wrote {path}  ({fig.get_size_inches()[0]:.3f} x {fig.get_size_inches()[1]:.3f} in "
              f"at {dpi} dpi{'' if not tight else '; TIGHT -- the printed size is no longer what you drew'})")
    return path



# ---- the recurring figure ------------------------------------------------------------------
def relspeed_fan(omega, ax=None, thetas=(90, 30, 15, 8, 4, 2), R=None,
                 a_sound=343.0, size=FigureSize.NOTE, label_all=True,
                 bands=None, title=None):
    """Relative speed against range, one line per aspect angle.

    The figure that says what a filled contour map cannot: on log-log axes
    log v = log(omega R) - log(sin theta) is a family of parallel straight
    lines, theta = 90 deg is a hard LOWER bound, and everything above it is
    permitted. The constraint is one-sided — the data return an inequality,
    not a value — and a reader can see that here.

    `bands` are (lo, hi, label) spans in m/s for what conventional
    explanations reach. They are bands in RELATIVE speed: a stationary object
    seen from a jet already sits at |v_own|, so a band below Mach 1 is
    reachable by an object that is not moving at all."""
    plt = setup()
    if ax is None:
        fig, ax = plt.subplots(figsize=(size, size * 0.73), dpi=200, layout="constrained")
    else:
        fig = ax.figure
    R = np.logspace(np.log10(2), np.log10(3000), 600) if R is None else np.asarray(R, float)
    ax.set_xscale("log")
    ax.set_yscale("log")
    for lo, hi, lab in (bands or []):
        ax.axhspan(lo, hi, color=AMBER, alpha=0.15, lw=0, zorder=1)
    for th in thetas:                               # each line named at its right end, clear of its neighbours
        v = omega * R / math.sin(math.radians(th))
        lower = th == 90
        if not (label_all or lower):
            continue
        ax.plot(R, v, color=BLUE, lw=2.4 if lower else 1.2, alpha=1.0 if lower else 0.55, zorder=6 if lower else 4,
                solid_capstyle="round")
        ax.annotate(f"{th}°" + (" (least)" if lower else ""), (R[-1] * 1.08, v[-1]), color=BLUE, va="center",
                    fontsize=TICK_PT - 1, weight="bold" if lower else "normal", annotation_clip=False)
    ax.set_xlim(R[0], R[-1] * 4.0)
    ax.set_xlabel("Distance to the object (m)")
    ax.set_ylabel("Speed relative to the camera (m/s)")
    for lo, hi, lab in (bands or []):
        ax.text(R[1], math.sqrt(lo * hi), lab, fontsize=TICK_PT - 2, color=SECONDARY, va="center", ha="left", zorder=8)
    sec = ax.secondary_yaxis("right", functions=(lambda v: v / a_sound, lambda m: m * a_sound))
    sec.set_ylabel("Mach")
    ax.set_title(title or "Speed by aspect angle")
    return fig, ax


# ---- the report's two figures (after the PR144 working note's two panels) -------------------------
OBJECTS = [("weather balloon", 2.0), ("fighter jet", 17.0)]     # m: marked where an object that size would sit
# m, the bands of the other things a witness's video is held against (an agent on IMG_5611, 2026-10-28, and the
# phone-video scope's WP8): a party balloon and a small drone share a band, a cluster of balloons and a tethered
# aerostat sit between the weather balloon and the jet
BANDS = [("party balloon or small drone", 0.3, 1.0), ("balloon cluster", 2.0, 5.0), ("tethered aerostat", 5.0, 20.0)]
# m, across the wings: a sparrow's to a goose's or an eagle's -- the band a bird would sit in. A tester, 2026-10-18: "when the
# analyses says it could be a bird, the plot doesn't show the range for 'Birds'"
BIRDS = (0.2, 2.0)
# deg: the fan drawn when nothing fixes the scale. 0.7 is a targeting pod's narrow field (ATFLIR's NAR: the Navy's FLIR1,
# 2026-10-20), which 3-30 left out by a factor of four
FOVS = (0.7, 3.0, 10.0, 30.0)
A_SOUND = 343.0
# the words on the figures for what the case's fields call things (sciencespeak's mcdonald glossary, the standard since
# 2026-11-07): `Case.rate`'s "in the image", and the admissible region's bounds
AGAINST = {"in the image": "across the picture"}
BOUND_NAMES = {"speed cap": "where the limit is reached", "range floor": "nearest it can be", "range ceiling": "farthest it can be",
               "farthest range given": "farthest given", "smallest size": "smallest size", "largest size": "largest size"}


def track_frame(clip, track, rate, against, extent, path, width=FigureSize.NOTE):
    """A frame from the middle of the track with the object's path over it, a dot each half second
    (or each quarter of a short track) labelled with its time, the rate, and the object enlarged in a
    corner. `rate` is px/s; `against` says against what; `extent` is the object's size in px, or None."""
    plt = setup()
    ns = sorted(track)
    mid = ns[len(ns) // 2]
    img = np.clip(np.asarray(clip.rgb(mid)), 0, 255).astype(np.uint8)
    H, W = img.shape[:2]
    fps = float(clip.fps)
    top = 0.36                                                         # inches above the picture, for its title
    fig = plt.figure(figsize=(width, width * H / W + top))
    ax = fig.add_axes([0, 0, 1, H / W * width / (width * H / W + top)])
    ax.imshow(img, interpolation="lanczos")
    xs, ys = [track[n][0] for n in ns], [track[n][1] for n in ns]
    ax.plot(xs, ys, "-", color=AMBER, lw=1.6)
    span = (ns[-1] - ns[0]) / fps
    step = 0.5 if span >= 1.5 else max(span / 4, 1 / fps)
    t = ns[0] / fps
    dots = []
    while t <= ns[-1] / fps + 1e-9:
        n = min(ns, key=lambda k: abs((k - 1) / fps - t))
        if n not in dots:
            dots.append(n)
            ax.plot(*track[n], "o", ms=6, mfc=AMBER, mec="white", mew=1.0)
        t += step
    ax.set_xticks([]), ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    # what is written on the picture goes where the path is not (Jacob, 2026-11-07: no text over lines): the enlarged
    # object and the rate each to the first corner the path keeps clear of, each time beside its dot on the first side
    # clear of the path, the dots and the times already placed. A path that doubles back can crowd a time out: its dot stays.
    if not hasattr(fig.canvas, "get_renderer"):
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        FigureCanvasAgg(fig)
    fig.draw_without_rendering()
    r = fig.canvas.get_renderer()
    polys, points = _lines_px(ax)
    abox = _box(ax, r, pad=0)
    placed = []

    def free(box):
        return _inside(box, abox) and not _crosses(polys, points, box) and not any(_meet(box, b) for b in placed)

    def crowd(box):                                # how much of the path a box would cover, to choose the least bad
        xy = np.concatenate(polys + points) if polys or points else np.zeros((0, 2))
        return int(((xy[:, 0] >= box[0]) & (xy[:, 0] <= box[2]) & (xy[:, 1] >= box[1]) & (xy[:, 1] <= box[3])).sum())
    x, y = track[mid]
    half = int(max(12, 1.5 * (extent or 9)))
    cx, cy = int(round(x)), int(round(y))
    crop = img[max(cy - half, 0):cy + half + 1, max(cx - half, 0):cx + half + 1]
    if crop.size:
        w_in, h_in = 0.19, 0.19 * W / H
        spots = [[0.79, 0.03, w_in, h_in], [0.79, 0.97 - h_in, w_in, h_in], [0.02, 0.03, w_in, h_in], [0.02, 0.97 - h_in, w_in, h_in]]
        boxes = [ax.transAxes.transform([(b[0], b[1]), (b[0] + b[2], b[1] + b[3])]).ravel() for b in spots]
        boxes = [(b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3) for b in boxes]
        i = next((i for i, b in enumerate(boxes) if free(b)), min(range(4), key=lambda i: crowd(boxes[i])))
        ins = ax.inset_axes(spots[i])
        ins.imshow(crop, interpolation="nearest")
        ins.set_xticks([]), ins.set_yticks([])
        for sp in ins.spines.values():
            sp.set_edgecolor("white")
        ins.text(0.04, 0.04, f"×{w_in * width * 100 / crop.shape[1]:.0f}"
                 + (f": about {extent:.0f} pixels across" if extent else ""), transform=ins.transAxes, color="white", fontsize=7.5)
        placed.append(boxes[i])
    if rate is not None:
        words = f"{rate:.0f} pixels a second ({rate / fps:.1f} a frame)\n{AGAINST.get(against, against)}"
        tried = []
        for fx, fy, ha, va in ((0.02, 0.03, "left", "bottom"), (0.02, 0.97, "left", "top"), (0.98, 0.97, "right", "top"),
                               (0.98, 0.03, "right", "bottom"), (0.5, 0.03, "center", "bottom"), (0.5, 0.97, "center", "top")):
            tx = ax.text(fx, fy, words, transform=ax.transAxes, ha=ha, va=va, color="white", fontsize=9,
                         bbox=dict(boxstyle="round,pad=0.3", fc="black", ec="none", alpha=0.55))
            b = _box(tx, r, pad=3)
            tried.append((tx, b))
            if free(b):
                break
        else:                                      # every place has the path: the one over the least of it, clear of the inset
            ok = [q for q in tried if not any(_meet(q[1], b) for b in placed)] or tried
            tried.sort(key=lambda q: (q not in ok, crowd(q[1])))
        keep = tried[-1] if free(tried[-1][1]) else tried[0]
        for tx, _ in tried:
            if tx is not keep[0]:
                tx.remove()
        placed.append(keep[1])
    from matplotlib import patheffects
    halo_ = [patheffects.withStroke(linewidth=2.2, foreground="black")]
    pt = fig.dpi / 72.0
    sides = [(1, 1), (1, -1), (-1, 1), (-1, -1), (1, 0), (-1, 0), (0, 1), (0, -1)]
    order = [dots[0], dots[-1]] + dots[1:-1] if len(dots) > 1 else dots       # the first and last times first
    for n in order:
        words = f"{(n - 1) / fps:.1f} s" if step >= 0.1 else f"{(n - 1) / fps:.2f} s"
        for d in (6, 10, 16):
            for sx, sy in sides:
                tx = ax.annotate(words, track[n], xytext=(sx * d, sy * d), textcoords="offset points", color="white", fontsize=8,
                                 weight="bold", ha={1: "left", -1: "right", 0: "center"}[sx],
                                 va={1: "bottom", -1: "top", 0: "center"}[sy], path_effects=halo_, annotation_clip=False)
                b = _box(tx, r, pad=2 * pt)
                if free(b):
                    placed.append(b)
                    break
                tx.remove()
            else:
                continue
            break
    fig.text(0.01, 1 - 0.05 / (width * H / W + top), f"The object's path over frames {ns[0]}–{ns[-1]}",
             fontsize=TITLE_PT, va="top")                     # a short title (the house style); the caption says the rest
    save(fig, path, dpi=200)
    plt.close(fig)
    return str(path)


def size_speed(rate, extent, width_px, path, k=None, k_from=None, R_known=None, size=FigureSize.NOTE, fov=None, bird=False,
               R_max=None):
    """Size S = p R / k (left axis) and transverse speed ωR (right axis) against the unknown range R.
    Both are R times the same unknown 1/k, so their ratio is the measured rate over the measured extent
    and one line carries both. With k known (a graticule, or a field of view given) that is one line,
    with where a weather balloon and a fighter jet would sit on it; with k unknown, one line for each of
    four fields of view (`FOVS`, a targeting pod's narrowest among them), k = (W/2)/tan(FOV/2) at the centre of the
    frame. Without an extent, speed only.
    The band of a bird's sizes is drawn with them, in amber where the case `bird`: its brightness
    beats like a bird's (`report.BIRD`). `R_max`, the farthest it can be, greys what lies beyond it.

    It is read by people who need not know what k is (a tester, 2026-10-18: "People may not know what 'k' is
    and they dont have to"): the axes and the lines are named in words and fields of view -- `fov` is the
    field of view a known k stands for, `k_from` where k came from -- and the symbols stay in the report's
    table of variables. In the house style (2026-11-07): the lines in blue, named at their ends; the kinds of object,
    Mach 1 and what was given named in a legend under the plot, so that no text inside it can cross a line."""
    from matplotlib import ticker
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    plt = setup()
    fig, ax = plt.subplots(figsize=(size, size * 0.82), layout="constrained")
    R = np.logspace(2, np.log10(max(3e4, R_max or 0.0)), 300)     # to the farthest it can be, where that is past the usual end
    ratio = rate / extent if extent else None                     # 1/s: speed over size, from the pixels alone
    per = (lambda kk: extent * R / kk) if extent else (lambda kk: rate * R / kk)
    lines = [(k, f"{fov:.2g}° view" if fov else "this video", True)] if k else \
        [((width_px / 2) / math.tan(math.radians(f) / 2), f"{f:g}° view", False) for f in FOVS]     # none is favoured
    keys = []
    if k:                                         # where the one line's scale came from: given, or the angle marks
        how = ("from the angle marks on the display" if str(k_from).startswith("graticule") else "as given")
        keys.append(Line2D([], [], color=BLUE, lw=2.2, label=(f"the line for a {fov:.2g}° view, {how}" if fov else
                                                              f"the line for {k * math.pi / 180:.1f} pixels a degree, {how}")))
    for kk, label, hot in lines:
        y = per(kk)
        ax.plot(R, y, color=BLUE, lw=2.2 if hot else 1.8, zorder=3)
        ax.annotate(label, (R[-1] * 1.08, y[-1]), color=BLUE, fontsize=TICK_PT - 1, va="center", annotation_clip=False,
                    weight="bold" if hot else "normal")
    ax.set_xscale("log"), ax.set_yscale("log")
    ax.set_xlim(R[0], R[-1] * 3.2)
    lo = min(per(kk)[0] for kk, _, _ in lines)
    hi = max(per(kk)[-1] for kk, _, _ in lines)
    if extent:                                                    # the things it is held against, always in sight
        lo, hi = min(lo, BIRDS[0]), max(hi, 1.5 * max([obj for _, obj in OBJECTS] + [top for _, _, top in BANDS]))
    ax.set_ylim(10 ** math.floor(math.log10(lo)), 10 ** math.ceil(math.log10(hi)))
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v / 1000:g} km" if v >= 1000 else f"{v:g} m"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_xlabel("Distance to the object")
    mach = A_SOUND / ratio if extent else A_SOUND                 # Mach 1, in the left axis's units
    ax.axhline(mach, color="black", lw=1.0, ls=":", zorder=1)
    keys.append(Line2D([], [], color="black", lw=1.0, ls=":", label="Mach 1, the speed of sound"))
    if extent:
        ax.set_ylabel("Size of the object (m)")
        sec = ax.secondary_yaxis("right", functions=(lambda s_: s_ * ratio, lambda v: v / ratio))
        sec.set_ylabel("Speed across the line of sight (m/s)")
        sec.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        b0, b1 = BIRDS
        ax.axhspan(b0, b1, color=AMBER, alpha=0.30 if bird else 0.16, lw=0, zorder=0.5)
        keys.append(Patch(color=AMBER, alpha=0.30 if bird else 0.16,
                          label=f"birds, {b0:g}–{b1:g} m" + (" (it beats like a bird)" if bird else "")))
        for (name, lo_, hi_), col, a in zip(BANDS, (CYAN, PURPLE, MUTED), (0.20, 0.13, 0.22)):   # the other bands, faint, a colour each
            ax.axhspan(lo_, hi_, color=col, alpha=a, lw=0, zorder=0.4)
            keys.append(Patch(color=col, alpha=a, label=f"{name}, {lo_:g}–{hi_:g} m"))
        for (name, obj), col in zip(OBJECTS, (RED, "black")):
            ax.axhline(obj, color=col, lw=1.0, ls="--", zorder=1)
            keys.append(Line2D([], [], color=col, lw=1.0, ls="--", label=f"{name}, {obj:g} m"))
            if k:
                r_obj = obj * k / extent
                if R[0] <= r_obj <= R[-1]:
                    ax.plot([r_obj, r_obj], [ax.get_ylim()[0], obj], color=col, lw=0.8, ls=":", zorder=1)
                    ax.plot(r_obj, obj, "o", ms=7, mfc=col, mec=SURFACE, mew=1.2, zorder=4)
        title = "Size and speed against distance"
    else:
        ax.set_ylabel("Speed across the line of sight (m/s)")
        title = "Speed against distance"
    if R_known:
        ax.axvline(R_known, color=AMBER, lw=1.4)
        keys.append(Line2D([], [], color=AMBER, lw=1.4, label=f"{R_known:,.0f} m away (given)"))
    if R_max:
        ax.axvspan(R_max, ax.get_xlim()[1], color=MUTED, alpha=0.18, lw=0, zorder=0.6)
        ax.axvline(R_max, color=AMBER, lw=1.4, ls="--")
        keys.append(Line2D([], [], color=AMBER, lw=1.4, ls="--", label=f"nothing beyond {R_max:,.0f} m (given)"))
    ax.set_title(title)
    fig.legend(handles=keys, loc="outside lower center", ncol=2)
    save(fig, path, dpi=200)
    plt.close(fig)
    return str(path)


def speed_band(path, series, band, fps, pairs=None, width=FigureSize.NOTE):
    """The speed along the track with its band (`kinematics.speed_band`, method section 32): the rate kriged
    from the track's own covariance as a line with its ±1 and ±2 sd, what each pair of consecutive frames
    reads on its own as dots (`pairs`: (t, px/s)), the net speed over the stretch dashed and, where the speed
    changed, the speed along the path dotted (B6: the distance travelled over the time, from paths drawn from the
    band's posterior); under it, the distance along the track those give. In the house style (2026-11-07): short
    titles, the finding in the report's caption and paragraph; the speed blue, the pairs red, the net amber, the
    path purple; room above the data for the legend, so that no text crosses a line."""
    plt = setup()
    t, v, s = (np.asarray(series[k], float) for k in ("t_s", "speed", "sd_speed"))
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(width, width * 0.86), sharex=True, layout="constrained",
                                  gridspec_kw=dict(height_ratios=[1.0, 0.7]))
    ax.fill_between(t, np.maximum(v - 2 * s, 0), v + 2 * s, color=BLUE, alpha=0.13, lw=0, label="±2 standard deviations")
    ax.fill_between(t, np.maximum(v - s, 0), v + s, color=BLUE, alpha=0.26, lw=0, label="±1 standard deviation")
    if pairs is not None and len(pairs[0]):
        ax.plot(pairs[0], pairs[1], ".", color=RED, ms=3.0, alpha=0.75, label="from one pair of frames")
    ax.plot(t, v, "-", color=BLUE, lw=2.0, label="the speed, read from the whole track")
    vm, em = band["v_mean_px_per_s"], band["v_mean_err_px_per_s"]
    vp, ep = band.get("v_path_px_per_s"), band.get("v_path_err_px_per_s")
    changed = vp is not None and not band["constant"]
    ax.axhline(vm, color=AMBER, lw=1.2, ls="--", label=(f"start to finish, {vm:.0f} ± {em:.1f} pixels a second" if changed
                                                        else f"average, {vm:.0f} ± {em:.1f} pixels a second"))
    if changed:
        ax.axhline(vp, color=PURPLE, lw=1.2, ls=":", label=f"along its path, {vp:.0f} ± {ep:.1f} pixels a second")
    data_top = max(float(np.max(v + 2 * s)), float(np.max(pairs[1])) if pairs is not None and len(pairs[0]) else 0.0, vm, vp or 0.0)
    steps = [f for f in ((band.get("jumps") or {}).get("flags") or []) if f["kind"] == "step"]
    for i, f in enumerate(steps):                   # a step the jump test named and the band kept: its rate there is the step's
        ax.vlines((f["frame"] - 1) / float(fps), 0, (data_top or 1.0) * 1.04, color=MUTED, lw=0.8, ls=":",   # up to the data
                  label="a step in the track (kept)" if i == 0 else None)                                  # only: the legend's room
    ax.set_ylim(0, (data_top or 1.0) * 1.62)       # the legend's room above the data
    ax.set_xlim(t[0], t[-1])
    ax.set_ylabel("Speed (pixels a second)")
    ax.set_title("Speed along the track")
    ax.legend(loc="upper center", ncol=2)
    # the time-distance diagram along the track (ROADMAP A13): the distance run, from the kriged speed, against time
    dist = np.r_[0.0, np.cumsum(0.5 * (v[1:] + v[:-1]) * np.diff(t))]
    sd = np.r_[0.0, np.sqrt(np.cumsum((0.5 * (s[1:] + s[:-1]) * np.diff(t)) ** 2))]
    ax2.fill_between(t, dist - 2 * sd, dist + 2 * sd, color=BLUE, alpha=0.13, lw=0)
    if pairs is not None and len(pairs[0]):
        tp = np.asarray(pairs[0], float)
        run = np.cumsum(np.asarray(pairs[1], float) * np.r_[np.diff(tp), np.diff(tp)[-1] if len(tp) > 1 else 0.0])
        ax2.plot(tp, run, ".", color=RED, ms=2.6, alpha=0.75, label="the track's own path, pair by pair")
    ax2.plot(t, dist, "-", color=BLUE, lw=2.0, label="from the speed above")
    ax2.plot([t[0], t[-1]], [0, vm * (t[-1] - t[0])], "--", color=AMBER, lw=1.2,
             label="at the net speed, start to finish" if changed else "at the average speed")
    if changed:
        ax2.plot([t[0], t[-1]], [0, vp * (t[-1] - t[0])], ":", color=PURPLE, lw=1.2, label="at the speed along its path")
    ax2.set_ylim(0, float(np.max(dist + 2 * sd)) * 1.12 or 1.0)
    ax2.set_xlim(t[0], t[-1])
    ax2.set_xlabel("Time in the video (s)")
    ax2.set_ylabel("Distance (pixels)")
    ax2.set_title("Distance along the track")
    ax2.legend(loc="upper left")
    save(fig, path, dpi=200)
    plt.close(fig)
    return str(path)


def admissible(path, reg, k=None, p_px=None, width=FigureSize.NOTE):
    """The admissible region in (R, Rdot) (`kinematics.admissible_region`, method section 33): the range along the
    bottom (log), the range rate up, the region the clip allows shaded, curves of constant speed across it, the
    bounds that cut it named, tau's line where there is one, and the size along the top where k and the extent give
    it. The Technical Note's fan with its one-sidedness visible: along Rdot = 0 the speed is omega R, the least it
    can be at that range. In the house style (2026-11-07): the region blue, each speed named just past its curve's
    end, the bounds and tau's line in a legend under the plot; what the region says is the report's paragraph."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    plt = setup()
    om, v_cap = reg["omega"], reg["v_cap"]
    edge = np.asarray(reg["edge"], float)
    fig, ax = plt.subplots(figsize=(width, width * 0.66), layout="constrained")
    ax.set_xscale("log")
    ax.fill_between(edge[:, 0], -edge[:, 1], edge[:, 1], color=BLUE, alpha=0.16, lw=0)
    keys = [Patch(color=BLUE, alpha=0.16, label="what the video allows")]
    R = np.geomspace(max(reg["R_lo"] / 3, 0.5), reg["R_hi"] * 3, 400)
    speeds = [(v, name) for v, name in ((10, "10 m/s"), (30, "30 m/s"), (100, "100 m/s"), (A_SOUND, "Mach 1"),
                                         (2 * A_SOUND, "Mach 2"), (v_cap, f"the limit, {v_cap:.0f} m/s"))
              if 0.07 * v_cap <= v <= v_cap + 1e-9]       # a curve under 7 % of the height is a sliver on the zero line
    for v, name in speeds:
        rr = R[om * R <= v]
        if len(rr) < 2:
            continue
        rd = np.sqrt(np.maximum(v ** 2 - (om * rr) ** 2, 0.0))
        mach = name.startswith("Mach")
        ax.plot(rr, rd, "--", color="black" if mach else MUTED, lw=1.0 if mach else 0.8)
        ax.plot(rr, -rd, "--", color="black" if mach else MUTED, lw=1.0 if mach else 0.8)
        top = v >= v_cap - 1e-9                        # the limit's line is the plot's top: its name goes under it
        ax.text(R[0] * 1.06, v * (0.97 if top else 1.0) + (-0.02 if top else 0.02) * v_cap, name, fontsize=TICK_PT - 1,
                color="black" if mach else SECONDARY, ha="left", va="top" if top else "bottom")
    for (what, side), ls in zip(reg["bounds"], ("-", "--", "-.", ":")):
        x = reg["R_lo"] if side == "low" else reg["R_hi"]
        ax.axvline(x, color=AMBER, lw=1.4, ls=ls)
        keys.append(Line2D([], [], color=AMBER, lw=1.4, ls=ls, label=BOUND_NAMES.get(what, what)))
    if reg.get("tau_s"):
        rr = edge[:, 0]
        rd = -rr / reg["tau_s"]
        ok = np.abs(rd) <= edge[:, 1]
        ax.plot(rr[ok], rd[ok], "-", color=RED, lw=1.8)
        keys.append(Line2D([], [], color=RED, lw=1.8, label=f"its size says {reg['tau_s']:.2f} s to reach the camera"))
    ax.axhline(0, color=MUTED, lw=0.6)
    ax.set_xlim(R[0], R[-1])
    ax.set_ylim(-1.05 * v_cap, 1.05 * v_cap)
    ax.set_xlabel("Distance to the object (m)")
    ax.set_ylabel("Change of distance (m/s; − is closing)")
    if k and p_px:
        top = ax.secondary_xaxis("top", functions=(lambda r: p_px * r / k, lambda S: S * k / p_px))
        top.set_xlabel("The object's size at that distance (m)")
    ax.set_title("What the video allows" if not (k and p_px) else "")
    fig.legend(handles=keys, loc="outside lower center", ncol=2)
    save(fig, path, dpi=200)
    plt.close(fig)
    return str(path)


def report_figures(case, clip, track, prefix):
    """The report's figures for a case with a track: [paths] -- the track on its frame and the size against
    speed (none without a track, or without a rate), and the beat figure where the flicker stage found a beat
    of the object's own and drew it (`flicker.judge`)."""
    from .report import BIRD
    rate, against = case.rate()
    out = []
    if track and rate is not None:
        extent, _ = case.extent()
        sf = (case.stages.get("scale") or {}).get("fields") or {}
        kf = (case.stages.get("kinematics") or {}).get("fields") or {}
        out = [track_frame(clip, track, rate, against, extent, f"{prefix}_track_frame.png"),
               size_speed(rate, extent, sf.get("fov_px") or clip.W, f"{prefix}_size_speed.png", k=sf.get("k_px_per_rad"),
                          k_from=sf.get("k_from"),
                          R_known=kf.get("range_m"), fov=sf.get("fov_deg"), bird=case.conclusion()[0] == BIRD,
                          R_max=kf.get("range_max_m"))]
    if ((case.stages.get("kinematics") or {}).get("fields") or {}).get("band") and Path(f"{prefix}_speed.png").exists():
        out.append(f"{prefix}_speed.png")                  # the speed along the track with its band (section 32)
    reg = case.admissible()
    if reg and not reg.get("empty"):                      # the admissible region in (R, Rdot) (section 33)
        try:
            sf = (case.stages.get("scale") or {}).get("fields") or {}
            out.append(admissible(f"{prefix}_admissible.png", reg, k=sf.get("k_px_per_rad"), p_px=case.extent()[0]))
        except Exception as e:                            # noqa: BLE001 -- a figure that cannot be drawn is said, the rest stand
            print(f"  ! the admissible region was not drawn: {type(e).__name__}: {e}")
    if ((case.stages.get("flicker") or {}).get("fields") or {}).get("beats") is True and Path(f"{prefix}_beat.png").exists():
        out.append(f"{prefix}_beat.png")
    ff = (case.stages.get("flicker") or {}).get("fields") or {}
    here = [(b["hz"], b["amplitude"]) for b in (ff.get("beat") or {}).values() if b.get("hz") and b.get("amplitude") is not None]
    if here:                                              # the beat against the labelled tracks (S20, 2026-11-07)
        try:
            from .report import BIRD_FLOOR
            out.append(beat_controls(f"{prefix}_controls.png", here, ff.get("rule") or "stage", BIRD_FLOOR))
        except Exception as e:                            # noqa: BLE001 -- a figure that cannot be drawn is said, the rest stand
            print(f"  ! the beat against the labelled tracks was not drawn: {type(e).__name__}: {e}")
    return out


# ---- the beat against the controls (S20) -------------------------------------------------------
def beat_controls(path, here, rule, floor, width=FigureSize.NOTE):
    """The discriminant plot (the ideas bank's S20): every labelled track of thermal video the flicker stage measured a beat
    on (`controls.population`, 400 of 432), its strongest rhythm's rate across and its strength up (a share of its
    brightness, on a log scale), birds blue and the rest amber -- filled where the rhythm was the track's own, open where
    it is only the strongest peak of a track with none -- the band of a wingbeat's rate shaded, the floor a bird is named
    from dashed, and this object's beat (`here`, [(Hz, share)], each member of a group) red. What it shows, beside the
    report's screening words (`controls.screen`): where the object's beat falls among birds and among the rest. What it
    must not be read to show: that the beat tests see wingbeats -- the birds' open dots sit as high as their filled ones,
    because the set's birds are faint and a faint object's brightness wanders more (ranked by this height, a bird
    outranks another track 0.82 of the time over all of them, and 0.88 among tracks with no rhythm of their own at all:
    the diagnostic survey's clinical rebuild). The points are scatter (`clear` keeps text off lines, not off dots), the
    legend below the axes."""
    from . import controls
    plt = setup()
    pop = controls.population(rule, floor)
    top = max([15.0] + [h * 1.1 for h, _ in here])
    fig, ax = plt.subplots(figsize=(width, width * 0.62))
    fig.subplots_adjust(left=0.11, right=0.97, top=0.92, bottom=0.30)
    ax.axvspan(controls.WINGBEAT_HZ[0], min(controls.WINGBEAT_HZ[1], top), color=DIM, zorder=0, lw=0,
               label="a wingbeat's rate")
    for bird, colour, who in ((False, AMBER, "aircraft, drones and helicopters"), (True, BLUE, "birds")):
        own = [(h, a) for b, h, a, k in pop if b == bird and k in controls.OWN]
        rest = [(h, a) for b, h, a, k in pop if b == bird and k not in controls.OWN]
        if rest:
            ax.scatter(*zip(*rest), s=14, facecolors="none", edgecolors=colour, linewidths=0.7, zorder=2,
                       label=f"{who}: strongest peak, no rhythm of its own")
        if own:
            ax.scatter(*zip(*own), s=18, color=colour, edgecolors="none", zorder=3, label=f"{who}: a rhythm of its own")
    ax.axhline(floor, color=PRIMARY, lw=1.0, ls=(0, (4, 3)), zorder=4, label=f"a bird is named above {100 * floor:g} %")
    ax.scatter([h for h, _ in here], [max(a, 2e-3) for _, a in here], s=70, color=RED, edgecolors="black", linewidths=0.8,
               zorder=5, label="this object")
    ax.set_yscale("log")
    ax.set_xlim(0, top)
    ax.set_ylim(2e-3, 1.5)
    ax.set_xlabel("Rate of its strongest rhythm (beats a second)")
    ax.set_ylabel("Strength (share of brightness)")
    ax.set_title("This object's beat among labelled tracks")
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.0))
    save(fig, path, dpi=150, quiet=True)
    plt.close(fig)
    return path


# ---- the beat -----------------------------------------------------------------------------
# In the style of the PR135 paper's Fig. 2 (Scientific Reports: one sans-serif face at one size, sentence-case
# lettering, no line under 1 pt, drawn 6.5 in wide), with amplitudes absolute rather than each spectrum normalised to
# its own peak, so that the controls drawn with it can be seen to be smaller (PR41, 2026-10-10).
BEAT_FS, BEAT_LW, BEAT_SHOW_S = 7.5, 1.0, 4.5
CONTROL = "#b7b5ae"


def beat(path, fps, ns, curves, seg, scale, beats, tracks, bgs, lines=(), trend=15):
    """One row per track with a beat of its own: (left) its brightness deviation over BEAT_SHOW_S s about the
    stretch reported (shaded where that is a window), with the background aperture beside it (in the object's brightness) as
    the control; (right) amplitude spectra over the track's whole span -- the object's and every background
    aperture's -- and, where the beat reported comes from a window, that window's spectrum dashed, so a beat heard
    in one stretch looks like one. The codec's rhythm is marked. `curves` is {name: brightness per frame of ns},
    `seg` {name: (first index, last index + 1)}, `scale` the object's median brightness (the backgrounds are
    measured in it), `beats` flicker's fields["beat"]. In the house style since 2026-11-07 (it had the PR135 paper's own
    look): each row's name and beat as titles over its plots, the shared axis labels the layout's. Returns the path."""
    from matplotlib.lines import Line2D
    from scipy import ndimage
    plt = setup()

    def dev(f, sc=None):
        f = np.asarray(f, float)
        t_ = ndimage.uniform_filter1d(f, trend, mode="nearest")
        return 100 * (f - t_) / (sc if sc else t_)

    def amp(r):
        r = r - r.mean()
        w = np.hanning(len(r))
        Z = 32 * len(r)
        return np.fft.rfftfreq(Z, 1 / fps), 2 * np.abs(np.fft.rfft(r * w, Z)) / w.sum()

    tracks = list(tracks)[:6]
    ns = np.asarray(ns)
    fig = plt.figure(figsize=(FigureSize.AIAA_FULL, 1.1 + 1.6 * len(tracks)), layout="constrained")
    left, right = fig.subfigures(1, 2, width_ratios=[2.35, 1], wspace=0.03)
    axL = left.subplots(len(tracks), 1, squeeze=False)[:, 0]
    axR = right.subplots(len(tracks), 1, squeeze=False, sharex=True)[:, 0]
    for i, name in enumerate(tracks):
        col = HOUSE[i % len(HOUSE)]
        s0, s1 = seg[name]
        n = ns[s0:s1]
        obj = dev(curves[name][s0:s1])
        b = beats[name]
        mid, half = 0.5 * (b["first"] + b["last"]), 0.5 * BEAT_SHOW_S * fps
        lo_, hi_ = max(n[0], mid - half), min(n[-1], mid + half)
        show = (n >= lo_) & (n <= hi_)
        ax = axL[i]
        ax.axhline(0, color=MUTED, lw=0.6, zorder=0)
        if b["source"] != "the whole track":                 # the window the beat was heard in
            ax.axvspan((b["first"] - 1) / fps, (b["last"] - 1) / fps, color=col, alpha=0.12, lw=0, zorder=0)
        if bgs:
            bs0, bs1 = max(s0, seg[bgs[0]][0]), min(s1, seg[bgs[0]][1])
            g, gn = dev(curves[bgs[0]][bs0:bs1], scale), ns[bs0:bs1]
            k = (gn >= lo_) & (gn <= hi_)
            ax.plot((gn[k] - 1) / fps, g[k], color=CONTROL, lw=1.0, zorder=1)
        ax.plot((n[show] - 1) / fps, obj[show], color=col, lw=1.2, marker="o", ms=2.0, zorder=2)
        m = float(np.nanmax(np.abs(obj[show]))) if show.any() else 1.0
        ax.set_ylim(-1.15 * m, 1.15 * m)
        ax.set_xlim((lo_ - 1) / fps - 0.03, (hi_ - 1) / fps + 0.03)
        ax.set_title(name, loc="left")
        sp_ = axR[i]
        for line in lines or ():
            sp_.axvline(line, color=MUTED, lw=1.0, ls=(0, (1, 1.5)), zorder=0)
        for bg in bgs:
            bs0, bs1 = max(s0, seg[bg][0]), min(s1, seg[bg][1])
            if bs1 - bs0 >= 30:
                f, A = amp(dev(curves[bg][bs0:bs1], scale))
                sp_.plot(f, A, color=CONTROL, lw=1.0, zorder=1)
        f, A = amp(obj)
        sp_.plot(f, A, color=col, lw=1.6, zorder=3)
        ymax = A[f > 1.0].max()
        if b["source"] != "the whole track":
            w0, w1 = b["first"] - ns[0], b["last"] - ns[0] + 1
            fw, Aw = amp(dev(curves[name][w0:w1]))
            sp_.plot(fw, Aw, color=col, lw=1.2, ls=(0, (3, 1.8)), zorder=2)
            ymax = max(ymax, Aw[fw > 1.0].max())
        sp_.set_xlim(0, fps / 2)
        sp_.set_ylim(0, 1.15 * ymax)
        sp_.set_title(f"{b['hz']:.2f} Hz" + (f" (double {b['double_hz']:.2f})" if b.get("double_hz") else ""), loc="left",
                      color=col)
        if i < len(tracks) - 1:
            sp_.tick_params(labelbottom=False)
    left.supylabel("Brightness change (%)", fontweight="bold", fontsize=LABEL_PT)
    left.supxlabel("Time in the video (s)", fontweight="bold", fontsize=LABEL_PT)
    right.supylabel("Beat strength (%)", fontweight="bold", fontsize=LABEL_PT)
    right.supxlabel("Beats a second (Hz)", fontweight="bold", fontsize=LABEL_PT)
    handles = [Line2D([], [], color=HOUSE[0], lw=1.2, marker="o", ms=2.0), Line2D([], [], color=CONTROL, lw=1.0)]
    labels = ["The object", "Background beside it"]
    if any(beats[n]["source"] != "the whole track" for n in tracks):
        handles.insert(1, Line2D([], [], color=HOUSE[0], lw=1.2, ls=(0, (3, 1.8))))
        labels.insert(1, "Its beat's stretch (shaded)")
    if lines:
        handles.append(Line2D([], [], color=MUTED, lw=1.0, ls=(0, (1, 1.5))))
        labels.append("Video file's rhythm")
    fig.legend(handles, labels, loc="outside upper center", ncol=2, handlelength=3)
    save(fig, path, dpi=200, quiet=True)
    plt.close(fig)
    return str(path)


def fold(path, rows, fps):
    """One row per track with a beat of its own: its brightness folded on the beat's period, over the
    phase of the beat's cycle, twice over, with the background beside it folded the same way; then the mean picture
    of the object over the bright half of the cycle, over the dim half, their difference (where the brightness that
    beats is: a beat of the object's sits in the aperture, the codec's in blocks, a gain's over the whole scene), and
    the whole frame's difference, small, with the object's place ringed. `rows` is [(name, numbers, (bright, dim,
    difference, scene))], `flicker.fold`'s two returns. In the house style since 2026-11-07: each row's name and beat as
    the title over its first plot, the pictures framed, the shared axis label the layout's. Returns the path."""
    from matplotlib.patches import Circle, Rectangle
    plt = setup()
    rows = list(rows)[:6]
    fig = plt.figure(figsize=(8.0, 1.0 + 1.75 * len(rows)), layout="constrained")
    gs = fig.add_gridspec(len(rows), 6, width_ratios=[1.7, 1, 1, 1, 1, 1.6])
    small = TICK_PT - 2

    def note(a, words):                            # a small plain caption under a picture (an axis label would be bold)
        a.text(0.5, -0.06, words, transform=a.transAxes, ha="center", va="top", fontsize=small, color=SECONDARY)
    for i, (name, num, pics) in enumerate(rows):
        col = HOUSE[i % len(HOUSE)]
        nb = len(num["bins"])
        ph = (np.arange(2 * nb) + 0.5) / nb
        ax = fig.add_subplot(gs[i, 0])
        ax.axhline(0, color=MUTED, lw=0.6, zorder=0)
        y = 100 * np.r_[num["bins"], num["bins"]]
        ax.step(ph, y, where="mid", color=col, lw=1.6, zorder=3)
        ax.plot(ph, y, "o", color=col, ms=3.0, zorder=4)
        if num.get("controls_amplitude") is not None:
            ax.axhspan(-100 * abs(num["controls_amplitude"]), 100 * abs(num["controls_amplitude"]), color=MUTED, alpha=0.18, lw=0, zorder=1)
        m = max(float(np.max(np.abs(y))), 1e-6)
        ax.set_ylim(-1.25 * m, 1.25 * m)
        ax.set_xlim(0, 2)
        ax.set_title(f"{name}, {num['hz']:.2f} Hz", loc="left")
        ax.set_xlabel("Through each beat (cycles)" if i == len(rows) - 1 else "")
        bright, dim, diff, scene = pics[:4]
        cmap = pics[4] if len(pics) > 4 else None
        heads = ("Bright", "Dim", "Difference")
        if bright is not None:
            lo_, hi_ = float(min(bright.min(), dim.min())), float(max(bright.max(), dim.max()))
            d = max(float(np.abs(diff).max()), 1e-6)
            for j, (im, head) in enumerate(zip((bright, dim, diff), heads)):
                a = fig.add_subplot(gs[i, 1 + j])
                if j < 2:
                    a.imshow(im, cmap="gray", vmin=lo_, vmax=hi_, interpolation="nearest")
                else:
                    a.imshow(im, cmap="RdBu_r", vmin=-d, vmax=d, interpolation="nearest")
                S = im.shape[0] // 2
                if num.get("in_aperture_share") is not None:
                    rad = S * np.sqrt(num["area_share"] / np.pi) * np.sqrt(np.pi) if num.get("area_share") else 4.0
                    a.add_patch(Circle((S, S), rad, fill=False, ec=AMBER, lw=1.0, ls=(0, (2, 1.5))))
                a.set_xticks([])
                a.set_yticks([])
                if i == 0:
                    a.set_title(head, fontsize=small + 1)
                if j == 2 and num.get("concentration") is not None:
                    note(a, f"{num['in_aperture_share']:.0%} in ring")
        a = fig.add_subplot(gs[i, 4])                     # the same by phase (flicker.phase_map, item 8)
        if cmap is not None:
            a.imshow(cmap, cmap="viridis", vmin=0, vmax=1, interpolation="nearest")
            S = cmap.shape[0] // 2
            rad = S * np.sqrt(num["area_share"] / np.pi) * np.sqrt(np.pi) if num.get("area_share") else 4.0
            a.add_patch(Circle((S, S), rad, fill=False, ec=AMBER, lw=1.0, ls=(0, (2, 1.5))))
            if num.get("phase_inside") is not None and num.get("phase_outside") is not None:
                note(a, f"in {num['phase_inside']:.2f}, out {num['phase_outside']:.2f}")
        a.set_xticks([])
        a.set_yticks([])
        if i == 0:
            a.set_title("In step", fontsize=small + 1)
        a = fig.add_subplot(gs[i, 5])
        if scene is not None:
            d = max(float(np.abs(scene).max()), 1e-6)
            a.imshow(scene, cmap="RdBu_r", vmin=-d, vmax=d, interpolation="nearest", aspect="equal")
            if num.get("at"):
                x0, y0, hw, hh = num["at"]
                a.add_patch(Rectangle((x0 - hw, y0 - hh), 2 * hw, 2 * hh, fill=False, ec=AMBER, lw=1.0))
            if num.get("scene_rms") is not None:
                note(a, f"elsewhere {num['scene_rms']:.2f} levels")
        a.set_xticks([])
        a.set_yticks([])
        if i == 0:
            a.set_title("Whole picture", fontsize=small + 1)
    fig.supylabel("Brightness change (%)", fontweight="bold", fontsize=LABEL_PT)
    save(fig, path, dpi=200, quiet=True)
    plt.close(fig)
    return str(path)


def noise(path, rows, fps):
    """One row per track with a beat of its own: the background apertures' windows' amplitude spectra as a distribution
    (`flicker.noise_pdf`; McNamara & Buland 2004's probabilistic power spectral density) -- the band up to their median,
    their 90th and their 99th centile at every frequency -- with the object's own median window spectrum over it, its
    beat marked, and the codec's lines. `rows` is [(name, arrays, hz, lines, numbers)], arrays `noise_pdf`'s second
    return. In the house style since 2026-11-07: each row's name, beat and where it stands as its title, a legend for the
    bands. Returns the path."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    plt = setup()
    rows = list(rows)[:6]
    fig, axes = plt.subplots(len(rows), 1, figsize=(FigureSize.AIAA_FULL, 1.0 + 1.6 * len(rows)), squeeze=False,
                             layout="constrained")
    fills = ((FAINT, 1.0, "The background, up to its median"), (DIM, 1.0, "Up to its 90th centile"),
             (SECONDARY, 0.35, "Up to its 99th centile"))
    for i, (name, arr, hz, lines, num) in enumerate(rows):
        ax = axes[i, 0]
        col = HOUSE[i % len(HOUSE)]
        fr = np.asarray(arr["fr"])
        band = (fr >= 1.0) & (fr <= 0.5 * fps)
        x = fr[band]
        floor = 1e-3
        lo = np.full(band.sum(), floor)
        for (c, a, _), key in zip(fills, ("p50", "p90", "p99")):
            hi = 100 * np.maximum(arr[key][band], floor)
            ax.fill_between(x, lo, hi, color=c, alpha=a, lw=0, zorder=1)
            lo = hi
        if arr.get("obj") is not None:
            ax.plot(x, 100 * np.maximum(np.asarray(arr["obj"])[band], floor), color=col, lw=1.5, zorder=4)
        for L in lines or ():
            ax.axvline(L, color=MUTED, lw=1.0, ls=(0, (2, 2)), zorder=2)
        ax.axvline(hz, color=RED, lw=1.2, zorder=3)
        ax.set_yscale("log")
        ax.set_xlim(1.0, 0.5 * fps)
        ax.set_title(f"{name}, {hz:.2f} Hz", loc="left")       # the name on the left, the finding on the right: each short
        if num and num.get("centile") is not None:
            ax.set_title(f"above {num['centile']:.0f} % of {num['windows']} background windows", loc="right")
        ax.set_xlabel("Beats a second (Hz)" if i == len(rows) - 1 else "")
    fig.supylabel("Strength in each window (%)", fontweight="bold", fontsize=LABEL_PT)
    keys = [Patch(color=c, alpha=a, label=lab) for c, a, lab in fills] + \
        [Line2D([], [], color=HOUSE[0], lw=1.5, label="The object"), Line2D([], [], color=RED, lw=1.2, label="Its beat"),
         Line2D([], [], color=MUTED, lw=1.0, ls=(0, (2, 2)), label="The video file's rhythm")]
    fig.legend(handles=keys, loc="outside upper center", ncol=3)
    save(fig, path, dpi=200, quiet=True)
    plt.close(fig)
    return str(path)
