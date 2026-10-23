"""Draw mcdonald's icon at every size a desktop asks for, and the logo with its name.

The icon is a video's frame (the four corners), an object in it, ringed as the window rings
the one being followed, and the places it was in earlier pictures: what mcdonald does, find
the object and follow it from picture to picture. Night-sky blue, as the window is dark.
Two drawings, both in `src/mcdonald/icons/`, are the originals and are edited by hand:

    mcdonald.svg        48 px and up
    mcdonald-small.svg  32 px and down: thicker corners, a solid object, two earlier places

This draws from them the PNGs (16-512), mcdonald.ico (Windows) and mcdonald.icns (macOS),
and `docs/logo-dark.svg` / `docs/logo-light.svg` (the icon and "mcDonald / UAP TOOLKIT",
for dark and light pages) with a PNG of each, and `docs/logo-stacked-*` (the words under the
icon instead of beside it). The words are outlines, so the logo looks the
same without the font; the font is Adwaita Sans (Inter; SIL Open Font License), which is
needed only to run this.

    python3 tools/make_icons.py
"""
import io
import re
from pathlib import Path

from PIL import Image
from PySide6 import QtCore, QtGui, QtSvg

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "src" / "mcdonald" / "icons"
DOCS = ROOT / "docs"
SIZES = (16, 24, 32, 48, 64, 128, 256, 512)
SMALL = 32
FONT = "Adwaita Sans"
INK = {"dark": ("#e8eef6", "#4fd1c5"), "light": ("#0a1830", "#1f8f86")}


def render(svg, w, h=None):
    """An SVG drawn at w x h, as a Pillow image."""
    h = h or w
    img = QtGui.QImage(w, h, QtGui.QImage.Format.Format_ARGB32)
    img.fill(0)
    p = QtGui.QPainter(img)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode())).render(p)
    p.end()
    buf = QtCore.QBuffer()
    buf.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")


def outline(text, size, weight, spacing=0.0):
    """Text as an SVG path (shaped and kerned by Qt), and its ink's box (baseline at y 0)."""
    f = QtGui.QFont(FONT)
    f.setPixelSize(size)
    f.setWeight(QtGui.QFont.Weight(weight))
    if spacing:
        f.setLetterSpacing(QtGui.QFont.SpacingType.AbsoluteSpacing, spacing)
    if QtGui.QFontInfo(f).family() != FONT:
        raise SystemExit(f"the font {FONT!r} is not installed")
    path = QtGui.QPainterPath()
    path.addText(0, 0, f, text)
    d, i, n = [], 0, path.elementCount()
    E = QtGui.QPainterPath.ElementType
    while i < n:
        e = path.elementAt(i)
        if e.type == E.MoveToElement:
            d.append(f"M{e.x:.2f} {e.y:.2f}")
        elif e.type == E.LineToElement:
            d.append(f"L{e.x:.2f} {e.y:.2f}")
        else:                                   # a cubic: this element and the two data after it
            c2, end = path.elementAt(i + 1), path.elementAt(i + 2)
            d.append(f"C{e.x:.2f} {e.y:.2f} {c2.x:.2f} {c2.y:.2f} {end.x:.2f} {end.y:.2f}")
            i += 2
        i += 1
    return " ".join(d), path.boundingRect()


def icon_inner():
    """The 256-px icon's drawing, without its <svg> wrapper."""
    icon = (ICONS / "mcdonald.svg").read_text()
    return re.sub(r"^<svg[^>]*>|</svg>\s*$", "", icon.strip(), flags=re.S)


def logo(theme):
    """The icon, and beside it mcDonald over UAP TOOLKIT."""
    ink, accent = INK[theme]
    name, nr = outline("mcDonald", 132, 700)
    sub, sr = outline("UAP TOOLKIT", 44, 600, spacing=9)
    x, W = 300, 300 + max(nr.right(), sr.right()) + 8
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} 256" width="{W:.0f}" height="256">\n'
            f'  <title>mcDonald UAP Toolkit</title>\n  <g>{icon_inner()}</g>\n'
            f'  <path transform="translate({x} 142)" fill="{ink}" d="{name}"/>\n'
            f'  <path transform="translate({x + 4} 212)" fill="{accent}" d="{sub}"/>\n</svg>\n'), W, 256


def stacked(theme, pad=8):
    """The icon, and under it mcDonald over UAP TOOLKIT, each centred; the words smaller than
    beside it (104 px, not 132), so the name is about twice the icon's width."""
    ink, accent = INK[theme]
    name, nr = outline("mcDonald", 104, 700)
    sub, sr = outline("UAP TOOLKIT", 35, 600, spacing=7)
    W = max(256, nr.width(), sr.width()) + 2 * pad
    name_y = 256 + 32 - nr.top()                # baselines: 32 px under the icon, 30 between
    sub_y = name_y + 30 - sr.top()
    H = sub_y + sr.bottom() + pad
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" width="{W:.0f}" height="{H:.0f}">\n'
            f'  <title>mcDonald UAP Toolkit</title>\n  <g transform="translate({(W - 256) / 2:.2f} 0)">{icon_inner()}</g>\n'
            f'  <path transform="translate({(W - nr.width()) / 2 - nr.left():.2f} {name_y:.2f})" fill="{ink}" d="{name}"/>\n'
            f'  <path transform="translate({(W - sr.width()) / 2 - sr.left():.2f} {sub_y:.2f})" fill="{accent}" d="{sub}"/>\n'
            f'</svg>\n'), W, H


def main():
    QtGui.QGuiApplication.instance() or QtGui.QGuiApplication(["make_icons", "-platform", "offscreen"])
    big, small = (ICONS / "mcdonald.svg").read_text(), (ICONS / "mcdonald-small.svg").read_text()
    imgs = {s: render(small if s <= SMALL else big, s) for s in SIZES}
    for s, img in imgs.items():
        img.save(ICONS / f"mcdonald-{s}.png", optimize=True)
    imgs[256].save(ICONS / "mcdonald.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)],
                   append_images=[imgs[s] for s in (16, 24, 32, 48, 64, 128)])
    imgs[512].save(ICONS / "mcdonald.icns", append_images=[imgs[s] for s in (16, 32, 64, 128, 256)])
    for theme in INK:
        for stem, draw in (("logo", logo), ("logo-stacked", stacked)):
            svg, W, H = draw(theme)
            (DOCS / f"{stem}-{theme}.svg").write_text(svg)
            render(svg, round(W), round(H)).save(DOCS / f"{stem}-{theme}.png", optimize=True)
    print(f"wrote {len(SIZES)} PNGs, mcdonald.ico and mcdonald.icns in {ICONS.relative_to(ROOT)}, "
          f"and the logo in {DOCS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
