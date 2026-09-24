"""Draw mcdonald's icon at every size a desktop asks for, and the logo with its name.

The icon is a video's frame (the four corners), an object in it, ringed as the window rings
the one being followed, and the places it was in earlier pictures: what mcdonald does, find
the object and follow it from picture to picture. Night-sky blue, as the window is dark.
Two drawings, both in `src/mcdonald/icons/`, are the originals and are edited by hand:

    mcdonald.svg        48 px and up
    mcdonald-small.svg  32 px and down: thicker corners, a solid object, two earlier places

This draws from them the PNGs (16-512), mcdonald.ico (Windows) and mcdonald.icns (macOS),
and `docs/logo-dark.svg` / `docs/logo-light.svg` (the icon and "mcDonald / UAP TOOLKIT",
for dark and light pages) with a PNG of each. The words are outlines, so the logo looks the
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
    """Text as an SVG path (shaped and kerned by Qt), and its width and cap height."""
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
    r = path.boundingRect()
    return " ".join(d), r.right(), -r.top()


def logo(theme):
    """The icon, and beside it mcDonald over UAP TOOLKIT."""
    ink, accent = INK[theme]
    icon = (ICONS / "mcdonald.svg").read_text()
    inner = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", icon.strip(), flags=re.S)
    name, name_w, name_h = outline("mcDonald", 132, 700)
    sub, sub_w, _ = outline("UAP TOOLKIT", 44, 600, spacing=9)
    x, W = 300, 300 + max(name_w, sub_w) + 8
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} 256" width="{W:.0f}" height="256">\n'
            f'  <title>mcDonald UAP Toolkit</title>\n  <g>{inner}</g>\n'
            f'  <path transform="translate({x} 142)" fill="{ink}" d="{name}"/>\n'
            f'  <path transform="translate({x + 4} 212)" fill="{accent}" d="{sub}"/>\n</svg>\n'), W


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
        svg, W = logo(theme)
        (DOCS / f"logo-{theme}.svg").write_text(svg)
        render(svg, round(W), 256).save(DOCS / f"logo-{theme}.png", optimize=True)
    print(f"wrote {len(SIZES)} PNGs, mcdonald.ico and mcdonald.icns in {ICONS.relative_to(ROOT)}, "
          f"and the logo in {DOCS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
