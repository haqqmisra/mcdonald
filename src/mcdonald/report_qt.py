"""The report in the right column, under the one button: what a reader takes away, in a card.

Jacob, 2026-10-07: "The report should open in the right-hand column, underneath the 'Measure the
Object' box, so that the video is still visible in the main window. ... Imagine how the Apple
developers would choose to present content, using minimal words and even icons." So: a small
caption, a badge and the label (a tick for a conclusion, a question mark for a tentative one,
a dash for none), the one sentence, a line with a button when nobody has checked the track by
eye, the numbers that were found as label-and-value rows, "More" for the bottom line's
paragraph and what is missing, and two quiet buttons: the full report (`measure_qt.show_report`,
a page over the video) and the folder.

Nothing is measured or decided here. The card reads the case back from its `_case.json`
(`report.Case.load`), the file `mcdonald run` writes, and shows what `Case.conclusion`,
`Case.summary` and `Case.bottom_line` say; "I looked at the track sheet" is `stages.confirm_sheet`,
the same amendment the report page's banner and `mcdonald report --i-looked` make.
"""
import re
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from . import stages
from .mark_qt import ACCENT, MUTED, PRIMARY, QUIET, folding_button, heading, muted
from .report import Case

# the label of a conclusion: its glyph and colour, as a badge
LOOK = {"Conclusion": ("✓", ACCENT), "Tentative conclusion": ("?", "#e8a23a"), "No physical conclusion": ("≈", "#898781"),
        "No conclusion": ("–", "#898781"), "No conclusion yet": ("…", "#898781")}
# the summary's rows, in the fewest words
SHORT = {"pixel velocity": "Speed, in the picture", "horizontal field of view": "Field of view", "angular scale": "Scale",
         "angular rate": "Turn rate", "image extent": "Size, in the picture", "range": "Range",
         "aspect angle / range rate": "Aspect", "platform velocity": "Camera's speed",
         "transverse relative speed": "Relative speed, across", "object size": "Size", "relative speed": "Relative speed",
         "object velocity": "Velocity", "brightness beat": "Beat"}


def short(name):
    m = re.match(r"pixel velocity against the \w+ background(?: \((.+)\))?", name)
    if m:
        return "Against the " + (m.group(1) or name.split("against the ")[1].split(" background")[0])
    return SHORT.get(name, name[:1].upper() + name[1:])


class ReportCard(QtWidgets.QFrame):
    """The report's card. `refresh` reads the case again when its file has changed; `looked` is the
    button that says the track sheet has been looked at; `full` opens the whole report as a page."""

    def __init__(self, window, thing=None):
        super().__init__()
        self.window_, self.thing, self.case, self.md, self._seen = window, thing, None, None, None
        self.setObjectName("report")
        self.setStyleSheet("QFrame#report { border: 1px solid #34343a; border-radius: 8px; }")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)
        caption = muted("REPORT" if thing is None else f"OBJECT {thing.k}  ·  REPORT")
        caption.setStyleSheet(f"color: {MUTED}; font-size: 10px; letter-spacing: 1px;")
        lay.addWidget(caption)
        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)
        self.badge = QtWidgets.QLabel()
        self.badge.setFixedSize(22, 22)
        self.badge.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self.badge, 0, QtCore.Qt.AlignmentFlag.AlignTop)
        self.label = heading("", 1.1)
        self.label.setWordWrap(True)
        top.addWidget(self.label, 1)
        lay.addLayout(top)
        self.headline = QtWidgets.QLabel()
        self.headline.setWordWrap(True)
        self.headline.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.headline)
        # the track not yet checked by eye: one line, and the button that says it has been
        self.banner = QtWidgets.QFrame()
        self.banner.setObjectName("unchecked")
        self.banner.setStyleSheet("QFrame#unchecked { background: #3a2f16; border: 1px solid #8a6a1f; border-radius: 6px; }")
        row = QtWidgets.QHBoxLayout(self.banner)
        row.setContentsMargins(8, 5, 6, 5)
        note = QtWidgets.QLabel("⚠  Track not yet checked by eye")
        note.setToolTip("the numbers for the object are not yet sure: nobody has said that the track sheet shows the object in "
                        "every frame. The sheet is in the full report")
        row.addWidget(note, 1)
        self.looked = QtWidgets.QPushButton("I looked")
        self.looked.setToolTip("the track sheet shows the object ringed on every frame. If you have looked at it, and the ring is "
                               "on the object in every frame, say so here: the report stops calling the numbers not yet sure. "
                               "Nothing is measured again")
        self.looked.setStyleSheet(PRIMARY)
        self.looked.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.looked.setAutoDefault(False)
        self.looked.clicked.connect(self.confirm)
        row.addWidget(self.looked)
        lay.addWidget(self.banner)
        # what was found, as rows: the trade's units are the report's own words (the plain-words test skips "technical")
        self.facts = QtWidgets.QWidget()
        self.facts.setObjectName("technical")
        self.grid = QtWidgets.QGridLayout(self.facts)
        self.grid.setContentsMargins(0, 2, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(3)
        self.grid.setColumnStretch(0, 1)
        lay.addWidget(self.facts)
        # More: the bottom line's paragraph, and what is missing
        self.more_text = muted()
        self.more_text.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.more = folding_button("More", self.more_text)
        lay.addWidget(self.more)
        lay.addWidget(self.more_text)
        buttons = QtWidgets.QHBoxLayout()
        self.full = QtWidgets.QPushButton("Full report")
        self.full.setToolTip("the whole report, over the video: the numbers, what is missing, the pictures, every step")
        self.full.clicked.connect(self.open_full)
        self.folder = QtWidgets.QPushButton("Folder")
        self.folder.setToolTip("open the folder with the report, the sheets, the tables of numbers and the pictures")
        self.folder.clicked.connect(self.open_folder)
        for b in (self.full, self.folder):
            b.setStyleSheet(QUIET)
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            b.setAutoDefault(False)
            buttons.addWidget(b)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        self.hide()

    def path(self):
        """The case's report, if there is one: the object's, or the window's own."""
        w = self.window_
        if w.clip is None:
            return None
        if self.thing is not None:
            md = self.thing.report
            return md if md is not None and md.exists() and self.thing.case_json.exists() else None
        md, js = Path(f"{w.out}_case.md"), Path(f"{w.out}_case.json")
        return md if md.exists() and js.exists() else None

    def open_full(self):
        """The whole report as a page over the video."""
        if self.thing is None:
            self.window_.do("report")
        elif self.md is not None:
            from .measure_qt import show_report
            d = show_report(self.window_, str(self.md))
            d.looked.clicked.connect(lambda *_: self.refresh(force=True))

    def open_folder(self):
        if self.thing is None:
            self.window_.do("folder")
        elif self.md is not None:
            from PySide6 import QtGui
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(self.md.resolve().parent)))

    def refresh(self, force=False):
        """Shown, from the case's file, whenever there is a report for this video; read again when the file
        has changed (or `force`), and only then: this is called at every step's progress."""
        md = self.path()
        if md is None:
            self.hide()
            self._seen = None
            return
        js = Path(str(md)[:-len("_case.md")] + "_case.json")
        key = (str(js), js.stat().st_mtime_ns)
        if key == self._seen and not force:
            self.show()
            return
        try:
            case = Case.load(js)
        except (OSError, ValueError, KeyError, TypeError):
            self.hide()
            return
        self._seen, self.case, self.md = key, case, md
        self._fill(case)
        self.show()

    def _fill(self, case):
        label, head = case.conclusion()
        glyph, colour = LOOK.get(label, ("–", MUTED))
        self.badge.setText(glyph)
        self.badge.setStyleSheet(f"border-radius: 11px; font-weight: bold; background: {colour}; color: #0b1a1c;")
        self.label.setText(label)
        self.headline.setText(head)
        self.banner.setVisible(stages.SHEET_PROVISIONAL in case.notes)
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        rows = []
        tf = case.stages.get("track", {}).get("fields") or {}
        if tf.get("frames"):
            rows.append(("Followed", f"{tf['frames']} frames, {tf.get('first')}–{tf.get('last')}"))
        rows += [(short(name), val.split(" (")[0]) for name, _, val, _ in case.summary() if val]    # the rest is in the full report
        for r, (k, v) in enumerate(rows):
            key = muted(k)
            key.setWordWrap(False)
            value = QtWidgets.QLabel(v)
            value.setStyleSheet("font-weight: bold;")
            value.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop)
            value.setWordWrap(True)
            value.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
            self.grid.addWidget(key, r, 0)
            self.grid.addWidget(value, r, 1)
        self.facts.setVisible(bool(rows))
        needs = [x for st in case.stages.values() for x in st.get("needs") or []]
        self.more_text.setText(case.bottom_line() + ("\n\nMissing: " + "; ".join(needs) + "." if needs else ""))

    def confirm(self):
        """The track sheet looked at afterwards: the case amended (`stages.confirm_sheet`), the card read again,
        and the report page too if it is open."""
        if self.md is None:
            return
        js = str(self.md)[:-len("_case.md")] + "_case.json"
        try:
            stages.confirm_sheet(js, "looked at afterwards, and said so in the window")
        except (OSError, ValueError) as e:
            from .mark_qt import complain
            complain(self, f"The report could not be changed: {e}")
            return
        from . import several
        several.listed(js)                            # one of several objects: its line in their list too
        self.refresh(force=True)
        page = getattr(self.window_, "report_page", None)
        if page is not None and page.isVisible():
            from .measure_qt import render
            render(page.page, self.md)
            page.banner.setVisible(False)
        self.window_.say_steps()
