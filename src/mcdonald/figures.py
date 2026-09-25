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


# ---- the report's two figures (after the PR144 working note's two panels) -------------------------
OBJECTS = [("weather balloon", 2.0), ("fighter jet", 17.0)]     # m: marked where an object that size would sit
FOVS = (3.0, 10.0, 30.0)                                         # deg: the fan drawn when nothing fixes the scale
A_SOUND = 343.0


def track_frame(clip, track, rate, against, extent, path, width=FigureSize.NOTE):
    """A frame from the middle of the track with the object's path over it, a dot each half second
    (or each quarter of a short track) labelled with its time, the rate, and the object enlarged in a
    corner. `rate` is px/s; `against` says against what; `extent` is the object's size in px, or None."""
    plt = setup(9)
    ns = sorted(track)
    mid = ns[len(ns) // 2]
    img = np.clip(np.asarray(clip.rgb(mid)), 0, 255).astype(np.uint8)
    H, W = img.shape[:2]
    fps = float(clip.fps)
    top = 0.3                                                          # inches above the picture, for its title
    fig = plt.figure(figsize=(width, width * H / W + top))
    ax = fig.add_axes([0, 0, 1, H / W * width / (width * H / W + top)])
    ax.imshow(img, interpolation="lanczos")
    xs, ys = [track[n][0] for n in ns], [track[n][1] for n in ns]
    ax.plot(xs, ys, "-", color=SERIES[1], lw=1.6)
    span = (ns[-1] - ns[0]) / fps
    step = 0.5 if span >= 1.5 else max(span / 4, 1 / fps)
    t = ns[0] / fps
    shown = set()
    while t <= ns[-1] / fps + 1e-9:
        n = min(ns, key=lambda k: abs((k - 1) / fps - t))
        if n not in shown:
            shown.add(n)
            x, y = track[n]
            ax.plot(x, y, "o", ms=6, mfc=SERIES[1], mec="white", mew=1.0)
            ax.text(x + 0.012 * W, y - 0.012 * H, f"{(n - 1) / fps:.1f} s" if step >= 0.1 else f"{(n - 1) / fps:.2f} s",
                    color="white", fontsize=8, weight="bold", path_effects=None)
        t += step
    if rate is not None:
        xe, ye = track[ns[-1]]
        ax.text(min(xe + 0.02 * W, 0.72 * W), min(ye + 0.04 * H, 0.9 * H),
                f"{rate:.0f} px/s ({rate / fps:.1f} px/frame)\n{against}", color="white", fontsize=9, va="top",
                bbox=dict(boxstyle="round,pad=0.3", fc="black", ec="none", alpha=0.55))
    x, y = track[mid]
    half = int(max(12, 1.5 * (extent or 9)))
    cx, cy = int(round(x)), int(round(y))
    crop = img[max(cy - half, 0):cy + half + 1, max(cx - half, 0):cx + half + 1]
    if crop.size:
        ins = ax.inset_axes([0.79, 0.03, 0.19, 0.19 * W / H])
        ins.imshow(crop, interpolation="nearest")
        ins.set_xticks([]), ins.set_yticks([])
        for sp in ins.spines.values():
            sp.set_edgecolor("white")
        ins.text(0.04, 0.04, f"×{ins.get_position().width * fig.get_size_inches()[0] * 100 / crop.shape[1]:.0f}"
                 + (f": ≈{extent:.0f} px across" if extent else ""), transform=ins.transAxes, color="white", fontsize=7.5)
    ax.set_xticks([]), ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.text(0.01, 1 - 0.04 / (width * H / W + top), f"Frame {mid} (t = {(mid - 1) / fps:.2f} s), with the object's path over frames {ns[0]}–{ns[-1]}",
             fontsize=10, weight="bold", va="top")
    save(fig, path, dpi=150)
    plt.close(fig)
    return str(path)


def size_speed(rate, extent, width_px, path, k=None, k_from=None, R_known=None, size=FigureSize.NOTE):
    """Size S = p R / k (left axis) and transverse speed ωR (right axis) against the unknown range R.
    Both are R times the same unknown 1/k, so their ratio is the measured rate over the measured extent
    and one line carries both. With k known (a graticule, or a field of view given) that is one line,
    with where a weather balloon and a fighter jet would sit on it; with k unknown, one line for each of
    three fields of view, k = (W/2)/tan(FOV/2) at the centre of the frame. Without an extent, speed only."""
    from matplotlib import ticker
    plt = setup(9)
    fig, ax = plt.subplots(figsize=(size, size * 0.62))
    fig.subplots_adjust(left=0.11, right=0.83 if extent else 0.8, top=0.86, bottom=0.14)
    R = np.logspace(2, np.log10(3e4), 300)
    ratio = rate / extent if extent else None                     # 1/s: speed over size, from the pixels alone
    per = (lambda kk: extent * R / kk) if extent else (lambda kk: rate * R / kk)
    lines = [(k, k_from or "given", True)] if k else \
        [((width_px / 2) / math.tan(math.radians(f) / 2), f"FOV {f:g}°", False) for f in FOVS]     # none is favoured
    for kk, label, hot in lines:
        y = per(kk)
        ax.plot(R, y, color=SERIES[0] if hot else SECONDARY, lw=2.3 if hot else 1.6,
                zorder=3 if hot else 2)
        ax.annotate(label if not k else f"k = {k:.0f}", (R[-1] * 1.05, y[-1]), color=PRIMARY if hot else SECONDARY,
                    fontsize=8.3, va="center", annotation_clip=False, weight="bold" if hot else "normal")
    ax.set_xscale("log"), ax.set_yscale("log")
    ax.set_xlim(R[0], R[-1] * 2.4)
    lo = min(per(kk)[0] for kk, _, _ in lines)
    hi = max(per(kk)[-1] for kk, _, _ in lines)
    ax.set_ylim(10 ** math.floor(math.log10(lo)), 10 ** math.ceil(math.log10(hi)))
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v / 1000:g} km" if v >= 1000 else f"{v:g} m"))
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_xlabel("range to the object  R")
    mach = A_SOUND / ratio if extent else A_SOUND                 # Mach 1, in the left axis's units
    ax.axhline(mach, color=SECONDARY, lw=0.8, ls="--")
    ax.text(R[-1] * 0.9, mach * 0.84, "Mach 1", fontsize=8, color=SECONDARY, ha="right", va="top")    # right, under the line: the object labels are on the left, over theirs
    if extent:
        ax.set_ylabel("size  S = p R / k  [m]")
        sec = ax.secondary_yaxis("right", functions=(lambda s_: s_ * ratio, lambda v: v / ratio))
        sec.set_ylabel("transverse speed  ωR  [m/s]")
        sec.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        for name, obj in OBJECTS:
            ax.axhline(obj, color=FAINT, lw=0.9, zorder=1)
            ax.text(R[0] * 1.1, obj * 1.12, f"{name}, ~{obj:g} m", fontsize=8, color=SECONDARY)
            if k:
                r_obj = obj * k / extent
                if R[0] <= r_obj <= R[-1]:
                    ax.plot([r_obj, r_obj], [ax.get_ylim()[0], obj], color=FAINT, lw=0.9, zorder=1)
                    ax.plot(r_obj, obj, "o", ms=7, mfc=SERIES[0], mec=SURFACE, mew=1.2, zorder=4)
        title = "Size (left) and speed (right) against range"
    else:
        ax.set_ylabel("transverse speed  ωR  [m/s]")
        title = "Speed against range (no image extent, so no size)"
    if R_known:
        ax.axvline(R_known, color=SERIES[1], lw=1.2)
        ax.text(R_known * 1.05, ax.get_ylim()[0] * 1.3, f"R = {R_known:,.0f} m (given)", color=SERIES[1], fontsize=8)
    ax.set_title(title, loc="left", fontsize=10, weight="bold", pad=20)
    ax.text(0, 1.015, f"k = {k:.0f} px/rad, from {k_from}" if k else "k is unknown, so one line for each field of view",
            transform=ax.transAxes, fontsize=8, color=SECONDARY, va="bottom")
    save(fig, path, dpi=150)
    plt.close(fig)
    return str(path)


def report_figures(case, clip, track, prefix):
    """The report's two figures for a case with a track: [paths] (none without one, or without a rate)."""
    rate, against = case.rate()
    if not track or rate is None:
        return []
    extent, _ = case.extent()
    sf = (case.stages.get("scale") or {}).get("fields") or {}
    kf = (case.stages.get("kinematics") or {}).get("fields") or {}
    out = [track_frame(clip, track, rate, against, extent, f"{prefix}_track_frame.png"),
           size_speed(rate, extent, clip.W, f"{prefix}_size_speed.png", k=sf.get("k_px_per_rad"), k_from=sf.get("k_from"),
                      R_known=kf.get("range_m"))]
    return out
