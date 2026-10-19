"""The report on paper: one PDF of a case's report, its pictures in it, to keep or to send.

A tester, 2026-10-18: "I couldn't find a button to download the report. It has only two options:
'Open the Folder' or 'Back to the Video'." A report is a Markdown file with its pictures beside
it -- right for the window's page and for GitHub, and no use to someone who wants to send one
file. This makes that file: the report as the window's page shows it, the same words in the same
order with the conclusion first in its band (`dress`, which the page uses too), set for paper --
dark ink on white, every folded part open (paper cannot unfold), each picture no wider than the
text, and a picture taller than a page (a track sheet) cut into page-high strips one under the
other rather than shrunk until nothing in it can be seen.

No interface in it: `mcdonald report CASE.json --pdf` and the report page's "Save as PDF…" are
its two shells. It needs Qt's GUI module, which every install has (PySide6-Essentials); with no
window open it draws offscreen, so a command line on a computer with no screen makes one too.
"""
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from . import __version__

DETAILS = re.compile(r"<details><summary>(.*?)</summary>(.*?)</details>", re.S)
PICTURE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
# the conclusion's band, the tables' rules, and the headings' and links' colour, on paper (the window's are its own)
PAPER = ("#e3eeee", "#c2c2c2", "#1b6b73")
MARGIN_MM = 22           # round the text: what Qt's printing gives a document (2 cm), and the paper's 2 mm it sets where none are
BODY_PT = 9.5
MOST_PAGES = 6           # a picture longer than this many pages (a long track's sheet) is named, not printed;
FINEST = 4.0             # so is one this many times the text's width: the command line's sheet, 30 frames of 384 px across


def application():
    """The Qt application that drawing text needs: the window's where there is one, else one made here,
    offscreen unless the person has said otherwise (a command line wants no window, and on a computer
    with no screen anything else stops the process)."""
    from PySide6 import QtGui
    app = QtGui.QGuiApplication.instance()
    if app is None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QtGui.QGuiApplication([sys.argv[0] if sys.argv and sys.argv[0] else "mcdonald"])
    return app


def dress(doc, size_pt, band, rule, accent):
    """A report's Markdown, already in `doc`, set for reading: room round the headings, which stand out
    (the second level in `accent`), lines not packed tight, the conclusion as a card -- `band` behind its
    lines, under its heading (Jacob, 2026-10-07: first on the page) -- links in `accent`, and tables ruled
    lightly in `rule` and as wide as the text. `size_pt` is the body's size; the headings' go from it.
    The window's report page (`measure_qt.render`) and the PDF (`write`) are dressed by this one function."""
    from PySide6 import QtGui
    block = doc.begin()
    while block.isValid():
        fmt = block.blockFormat()
        level = fmt.headingLevel()
        cur = QtGui.QTextCursor(block)
        if level:
            fmt.setTopMargin({1: 4, 2: 22}.get(level, 14))
            fmt.setBottomMargin(8)
            cur.setBlockFormat(fmt)
            cur.select(QtGui.QTextCursor.SelectionType.BlockUnderCursor)
            ch = QtGui.QTextCharFormat()
            ch.setFontPointSize(size_pt * {1: 1.9, 2: 1.4, 3: 1.15}.get(level, 1.05))
            ch.setFontWeight(QtGui.QFont.Weight.Bold)
            if level == 2:
                ch.setForeground(QtGui.QColor(accent))
            cur.mergeCharFormat(ch)
        else:
            fmt.setNonBreakableLines(False)       # a command in a code block wraps; it was the page's width, and a scrollbar
            if "￼" not in block.text():      # not a picture's line: 135 % of a picture's height is a gap under it
                fmt.setLineHeight(135, QtGui.QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            fmt.setBottomMargin(max(fmt.bottomMargin(), 6))
            cur.setBlockFormat(fmt)
        block = block.next()
    # the conclusion, first on the page (Jacob, 2026-10-07), as a card: a band behind its lines, under its heading
    in_conclusion, first, block = False, True, doc.begin()
    while block.isValid():
        level = block.blockFormat().headingLevel()
        if level:
            in_conclusion, first = level == 2 and block.text().strip() == "Conclusion", True
        elif in_conclusion and block.text().strip():
            fmt = block.blockFormat()
            fmt.setBackground(QtGui.QColor(band))
            fmt.setLeftMargin(14)
            fmt.setRightMargin(14)
            fmt.setTopMargin(10 if first else 0)
            fmt.setBottomMargin(10)
            QtGui.QTextCursor(block).setBlockFormat(fmt)
            first = False
        block = block.next()
    it = doc.begin()                              # links in the accent: Markdown import fixes them in the palette's blue
    while it.isValid():
        frags = it.begin()
        while not frags.atEnd():
            f = frags.fragment()
            if f.charFormat().isAnchor() and not f.charFormat().isImageFormat():
                cur = QtGui.QTextCursor(doc)
                cur.setPosition(f.position())
                cur.setPosition(f.position() + f.length(), QtGui.QTextCursor.MoveMode.KeepAnchor)
                ch = QtGui.QTextCharFormat()
                ch.setForeground(QtGui.QColor(accent))
                cur.mergeCharFormat(ch)
            frags += 1
        it = it.next()
    for frame in doc.rootFrame().childFrames():
        if isinstance(frame, QtGui.QTextTable):
            tf = frame.format()
            tf.setBorder(1)
            tf.setBorderBrush(QtGui.QColor(rule))
            tf.setBorderStyle(QtGui.QTextFrameFormat.BorderStyle.BorderStyle_Solid)
            tf.setCellPadding(6)
            tf.setCellSpacing(0)
            tf.setWidth(QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 100))    # its columns wrap, not the page
            frame.setFormat(tf)


def letter_here():
    """Is paper Letter where this computer is (the United States' measures), not A4?"""
    from PySide6 import QtCore
    return QtCore.QLocale().measurementSystem() == QtCore.QLocale.MeasurementSystem.ImperialUSSystem


def default_name(report_md):
    """Where `write` puts the PDF unless told: beside the report, <tag>_report.pdf."""
    md = Path(report_md)
    return md.with_name(md.name[:-len("_case.md")] + "_report.pdf") if md.name.endswith("_case.md") else md.with_suffix(".pdf")


def write(report_md, pdf=None, letter=None):
    """The report at `report_md` as one PDF, its pictures in it, at `pdf` (default: `default_name`). Returns the
    PDF's path. `letter` is the paper: Letter, or A4 when false; by default what the computer's place uses.
    Raises OSError where the report cannot be read or the PDF cannot be written."""
    from PySide6 import QtCore, QtGui
    application()
    md = Path(report_md)
    folder = md.resolve().parent
    pdf = Path(pdf) if pdf else default_name(md)
    text = md.read_text(encoding="utf-8")
    title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), md.stem)
    letter = letter_here() if letter is None else letter
    size = QtGui.QPageSize(QtGui.QPageSize.PageSizeId.Letter if letter else QtGui.QPageSize.PageSizeId.A4)
    pdf.parent.mkdir(parents=True, exist_ok=True)       # a folder named that is not there yet is made, as `--out` makes one
    pdf.unlink(missing_ok=True)                          # one from before is replaced: a file there afterwards is this one
    writer = QtGui.QPdfWriter(str(pdf))
    writer.setPageSize(size)
    writer.setTitle(title)
    writer.setCreator(f"mcdonald {__version__}")
    # Qt prints a document with 2 cm round the text and its page numbers, inside the paper's own margins, which it
    # makes 2 mm where none are set: so none are, and the text is the page less 22 mm a side
    page = size.size(QtGui.QPageSize.Unit.Millimeter)
    high = 0.92 * (page.height() - 2 * MARGIN_MM) / (page.width() - 2 * MARGIN_MM)     # a page's height over its width, less a line
    doc = QtGui.QTextDocument()
    font = QtGui.QFont(QtGui.QGuiApplication.font())
    font.setPointSizeF(BODY_PT)
    doc.setDefaultFont(font)
    doc.setDocumentMargin(0)
    # every folded part open, under its own line: paper cannot unfold
    text = DETAILS.sub(lambda m: f"*{m.group(1).strip()}*\n\n{m.group(2)}", text)
    # A picture's width is in the pixels of Qt's own screen dots per inch, which printing scales to the paper (96 here,
    # 72 on a Mac): no wider than the text in those. A width as a share of the text's is not kept to when printing.
    screen = QtGui.QGuiApplication.primaryScreen()
    widest = (page.width() - 2 * MARGIN_MM) / 25.4 * (round(screen.logicalDotsPerInchX()) if screen is not None else 100)
    # each picture a resource of the document; one taller than a page in strips a page high, one under the other
    strips = []

    def pictures(m):
        file = folder / unquote(m.group(2))
        reader = QtGui.QImageReader(str(file))
        got = reader.size()
        if not got.isValid() or got.width() < 1:
            return m.group(0)                      # not there: its name says what was meant
        w, h = got.width(), got.height()
        step = max(1, int(w * high))
        if w > FINEST * widest or -(-h // step) > MOST_PAGES:     # a long track's sheet: on paper, nothing in it could be seen
            return (f"*{m.group(1)}: {w} × {h} pixels, too large for paper. It is in the results folder, beside the report: "
                    f"{unquote(m.group(2))}*")
        parts = []
        for y in range(0, h, step):
            strips.append((f"mcdonald-picture-{len(strips)}.png", file, QtCore.QRect(0, y, w, min(step, h - y))))
            parts.append(f"![{m.group(1)}]({strips[-1][0]})")
        return "\n\n".join(parts)
    doc.setMarkdown(PICTURE.sub(pictures, text))
    for key, file, rect in strips:                 # after the Markdown: setting it clears a document's resources
        reader = QtGui.QImageReader(str(file))
        reader.setClipRect(rect)
        doc.addResource(QtGui.QTextDocument.ResourceType.ImageResource, QtCore.QUrl(key), reader.read())
    sizes = {key: (rect.width(), rect.height()) for key, _, rect in strips}
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.charFormat().isImageFormat() and frag.charFormat().toImageFormat().name() in sizes:
                im = frag.charFormat().toImageFormat()
                w, h = sizes[im.name()]
                im.setWidth(min(w, widest))
                im.setHeight(h * min(w, widest) / w)
                cur = QtGui.QTextCursor(doc)
                cur.setPosition(frag.position())
                cur.setPosition(frag.position() + frag.length(), QtGui.QTextCursor.MoveMode.KeepAnchor)
                cur.setCharFormat(im)
            it += 1
        block = block.next()
    dress(doc, BODY_PT, *PAPER)
    doc.print_(writer)
    del writer                                     # the file is finished when the writer goes
    if not pdf.exists() or pdf.stat().st_size == 0:
        raise OSError(f"{pdf} could not be written")
    return pdf
