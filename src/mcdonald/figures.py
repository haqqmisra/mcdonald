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


def setup(size=10, family=("DejaVu Sans", "Liberation Sans", "Arial")):
    """House rcParams. Call once, before creating a figure."""
    import matplotlib
    if not os.environ.get("DISPLAY"):
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": list(family), "font.size": size,
        "axes.edgecolor": MUTED, "axes.linewidth": 0.8, "axes.labelcolor": PRIMARY,
        "axes.facecolor": SURFACE, "figure.facecolor": SURFACE,
        "text.color": PRIMARY, "xtick.color": SECONDARY, "ytick.color": SECONDARY,
        "grid.color": FAINT, "grid.linewidth": 0.6,
        "legend.frameon": False, "savefig.facecolor": SURFACE,
    })
    return plt


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
    "/usr/share/fonts/truetype/dejavu/DejaVuSans{dj}.ttf",
]


def pil_font(size, bold=False):
    """A real TrueType face at `size`, or an exception.

    Never returns ImageFont.load_default(): that face ignores `size`, so a
    caller asking for 40 px silently gets about 8 and the figure ships
    unreadable. If this raises, install a font rather than catching it."""
    from PIL import ImageFont
    w = "Bold" if bold else "Regular"
    for pat in _PIL_CANDIDATES:
        path = pat.format(w=w, mac="Bold" if bold else "", dj="-Bold" if bold else "")
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
def save(fig, path, dpi=200, tight=False):
    """Save at the size the figure was drawn. `tight=True` must be deliberate."""
    if tight:
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
    else:
        fig.savefig(path, dpi=dpi)
    print(f"wrote {path}  ({fig.get_size_inches()[0]:.3f} x {fig.get_size_inches()[1]:.3f} in "
          f"at {dpi} dpi{'' if not tight else '; TIGHT -- the printed size is no longer what you drew'})")
    return path



def _label_lines(ax, R, lines, label_all=True):
    """Direct labels along a fan of parallel lines, rotated to each line's
    screen angle and spread so they cannot collide.

    Rotation has to come from the axes transform, not the data: on log-log
    axes the screen slope depends on the figure's aspect and the decade
    ranges, so a rotation computed from the numbers alone is wrong."""
    ax.figure.canvas.draw()
    n = len(lines)
    for i, (th, v, lower) in enumerate(lines):
        if not (label_all or lower):
            continue
        # spread the anchors across the x range, widest-angle line leftmost
        frac = 0.16 + 0.68 * (i / max(n - 1, 1))
        j = int(np.clip(len(R) * frac, 2, len(R) - 3))
        p0 = ax.transData.transform((np.log10(R[j - 2]), np.log10(v[j - 2])))
        p1 = ax.transData.transform((np.log10(R[j + 2]), np.log10(v[j + 2])))
        if ax.get_xscale() == "log":
            p0 = ax.transData.transform((R[j - 2], v[j - 2]))
            p1 = ax.transData.transform((R[j + 2], v[j + 2]))
        rot = math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
        ax.text(R[j], v[j], f"θ = {th}°" + ("  (lower bound)" if lower else ""),
                fontsize=8.5, color=PRIMARY if lower else SECONDARY,
                rotation=rot, rotation_mode="anchor",
                ha="center", va="bottom", zorder=7, path_effects=halo())


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
        fig, ax = plt.subplots(figsize=(size, size * 0.73), dpi=200)
    else:
        fig = ax.figure
    R = np.logspace(np.log10(2), np.log10(3000), 600) if R is None else np.asarray(R, float)

    ax.set_xscale("log")
    ax.set_yscale("log")
    for lo, hi, lab in (bands or []):
        ax.axhspan(lo, hi, color=DIM, zorder=1)

    lines = []
    for th in thetas:
        v = omega * R / math.sin(math.radians(th))
        lower = th == 90
        ax.plot(R, v, color=PRIMARY if lower else MUTED,
                lw=2.4 if lower else 1.2, zorder=6 if lower else 4,
                solid_capstyle="round")
        lines.append((th, v, lower))
    _label_lines(ax, R, lines, label_all)

    ax.set_xlabel("range to the object  R  [m]")
    ax.set_ylabel("relative speed  |v$_{obj}$ − v$_{own}$|  [m s$^{-1}$]")
    ax.grid(True, which="both", lw=0.6, color=FAINT, zorder=0)
    ax.set_axisbelow(True)
    for lo, hi, lab in (bands or []):
        # at the left edge, on the band's own midline, so two adjacent bands
        # cannot print their labels on top of each other
        ax.text(R[1], math.sqrt(lo * hi), lab, fontsize=8, color=SECONDARY,
                va="center", ha="left", zorder=8, path_effects=halo())
    sec = ax.secondary_yaxis("right", functions=(lambda v: v / a_sound, lambda m: m * a_sound))
    sec.set_ylabel("Mach")
    if title:
        ax.set_title(title, loc="left", color=PRIMARY, fontsize=11, pad=10)
    ax.text(0.5, -0.17, "Relative speed, not object speed: a stationary object seen from a "
            "moving platform already sits at |v$_{own}$|.",
            transform=ax.transAxes, ha="center", fontsize=8, color=MUTED)
    fig.tight_layout()
    return fig, ax
