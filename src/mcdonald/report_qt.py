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

Where the report could not give a real speed, the card asks for what would give one (Jacob,
2026-10-09: "prompt the user to ask if any additional quantities are known (FOV, object of known
reference size, range to object, etc.)"): how wide the camera sees, how far away the object is, a
thing of known size in the picture. "Add what you know" opens the segment step's form in the card
(`known_qt.KnownForm`), and "Work out the speed" is `stages.add_known`, what `mcdonald report CASE
--fov ...` does: the speed worked out again from the case's track, nothing measured again. Where it
could, the card says what the speed rests on, with a way to change it.
"""
import re
import threading
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from . import known_qt, stages
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


class Box(QtWidgets.QFrame):
    """A frame that keeps its clicks: one inside the card's form must not take the video to the track's start."""

    def mousePressEvent(self, e):
        e.accept()


class ReportCard(QtWidgets.QFrame):
    """The report's card. `refresh` reads the case again when its file has changed; `looked` is the
    button that says the track sheet has been looked at; `full` opens the whole report as a page;
    `ask` is the box that asks what else is known of the video, and `known` its form."""
    worked = QtCore.Signal(object)                    # add_known's answer, from its thread: (case, md), or what went wrong

    def __init__(self, window, thing=None):
        super().__init__()
        self.window_, self.thing, self.case, self.md, self._seen = window, thing, None, None, None
        self.setObjectName("report")
        self.setStyleSheet("QFrame#report { border: 1px solid #34343a; border-radius: 8px; }")
        self.setToolTip("click to go to the frame where its track starts")
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
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
        # what else is known of the video: asked for where the report could not give a real speed, and said where it
        # could -- what the speed rests on is a thing given, not measured (2026-10-09)
        self.ask = Box()
        self.ask.setObjectName("ask")
        self.ask.setStyleSheet("QFrame#ask { background: #16262a; border: 1px solid #2c5a5e; border-radius: 6px; }")
        self.ask.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
        al = QtWidgets.QVBoxLayout(self.ask)
        al.setContentsMargins(8, 6, 8, 8)
        al.setSpacing(6)
        top = QtWidgets.QHBoxLayout()
        self.ask_text = QtWidgets.QLabel()
        self.ask_text.setWordWrap(True)
        top.addWidget(self.ask_text, 1)
        self.ask_button = QtWidgets.QPushButton("Add what you know")
        self.ask_button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.ask_button.setAutoDefault(False)
        self.ask_button.clicked.connect(lambda _=False: self.open_known())
        top.addWidget(self.ask_button, 0, QtCore.Qt.AlignmentFlag.AlignTop)
        al.addLayout(top)
        self.known = known_qt.KnownForm(ruler=window.start_ruler, narrow=True)
        al.addWidget(self.known)
        self.known_said = QtWidgets.QLabel()
        self.known_said.setWordWrap(True)
        al.addWidget(self.known_said)
        self.known_buttons = QtWidgets.QWidget()
        kb = QtWidgets.QHBoxLayout(self.known_buttons)
        kb.setContentsMargins(0, 0, 0, 0)
        kb.addStretch(1)
        self.cancel_known = QtWidgets.QPushButton("Cancel")
        self.cancel_known.setStyleSheet(QUIET)
        self.cancel_known.clicked.connect(lambda _=False: self.close_known())
        self.work_out = QtWidgets.QPushButton("Work out the speed")
        self.work_out.setStyleSheet(PRIMARY)
        self.work_out.setToolTip("the speed is worked out again with what you gave, from the track already followed: "
                                 "nothing is measured again, and it takes a second or two")
        self.work_out.clicked.connect(lambda _=False: self.work_it_out())
        for b in (self.cancel_known, self.work_out):
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            b.setAutoDefault(False)
            kb.addWidget(b)
        al.addWidget(self.known_buttons)
        self.close_known()
        lay.addWidget(self.ask)
        self.worked.connect(self._worked)
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
        said = self.asking(case)
        self.ask.setVisible(said is not None)
        if said is not None and self.known.isHidden():    # not while the form is open: what it says is the person's
            self.ask_text.setText(said[0])
            self.ask_button.setText(said[1])
            self.ask_button.setStyleSheet(PRIMARY if said[2] else QUIET)

    # -- what else is known of the video ------------------------------------------------------------
    @staticmethod
    def asking(case):
        """(what the box says, its button, whether it asks) for a case with a rate to turn into a speed; None for
        one without (no track, or no fit to it)."""
        kf = case.stages.get("kinematics", {}).get("fields") or {}
        if not kf.get("fit"):
            return None
        if kf.get("relative_speed_m_per_s") is None and kf.get("scale_bar_m_per_s") is None:
            k = (case.stages.get("scale", {}).get("fields") or {}).get("k_px_per_rad")
            r = kf.get("range_m")
            need = ("how far away the object is" if k is not None and r is None else
                    "how wide the camera sees" if k is None and r is not None else
                    "how wide the camera sees and how far away the object is")
            one = k is not None or r is not None
            return (f"Its real speed needs {need}, or the true size of something in the picture. Do you know "
                    f"{'either' if one else 'any of these'}?", "Add what you know", True)
        said = known_qt.describe(stages.known_of(case))
        return (f"Worked out from what you gave: {said}." if said else "Worked out from what was given."), "Change", False

    def open_known(self):
        """The form, in the card, filled with what this report was worked out with."""
        if self.case is None:
            return
        self.known.set_values(stages.known_of(self.case))
        for x in (self.known, self.known_buttons):
            x.show()
        self.ask_button.hide()
        self.known_said.hide()
        self.work_out.setEnabled(True)

    def close_known(self):
        for x in (self.known, self.known_buttons, self.known_said):
            x.hide()
        self.ask_button.show()

    def _say(self, text, warn=False):
        self.known_said.setText(text)
        self.known_said.setStyleSheet("color: #e8a23a;" if warn else f"color: {MUTED};")
        self.known_said.show()

    def work_it_out(self):
        """What was typed, as `stages.add_known` takes it -- only what changed -- on a thread of its own; the card
        is read again when it is done, and the window keeps what was given for the video."""
        if self.case is None or self.md is None:
            return
        try:
            values = self.known.values()
        except ValueError as e:
            self._say(str(e), warn=True)
            return
        was = stages.known_of(self.case)
        change = {n: v for n, v in values.items() if v != was.get(n) and not (v is None and n not in was)}
        if not change:
            self.close_known()
            return
        w = self.window_
        js = str(self.md)[:-len("_case.md")] + "_case.json"
        c = self.case.clip or {}
        same = w.clip is not None and (c.get("n0"), c.get("n1")) == (w.clip.n0, w.clip.n1)
        workdir, masks = (str(w.clip.dir) if w.clip is not None else None), (w._masks if same else None)
        self.work_out.setEnabled(False)
        self._say("Working it out…")
        self._change = change

        def job():
            try:
                got = stages.add_known(js, workdir=workdir, masks=masks, **change)
            except BaseException as e:                # whatever it is goes on the card, not to a dead thread
                got = e
            try:
                self.worked.emit(got)
            except RuntimeError:                       # the card went meanwhile
                pass
        threading.Thread(target=job, daemon=True, name="mcdonald-known").start()

    @QtCore.Slot(object)
    def _worked(self, got):
        if isinstance(got, BaseException):
            self.work_out.setEnabled(True)
            self._say(f"It could not be worked out: {got}", warn=True)
            return
        _, md = got
        self.window_.set_known(self._change)          # kept for the video: the next run starts from it
        from . import several
        several.listed(str(md)[:-len("_case.md")] + "_case.json")     # one of several objects: its line in their list too
        self.close_known()
        self.refresh(force=True)
        page = getattr(self.window_, "report_page", None)
        if page is not None and page.isVisible():
            from .measure_qt import render
            render(page.page, self.md)
        self.window_.say_steps()

    def first_frame(self):
        """The first frame of the track the report is about, if it has one."""
        tf = (self.case.stages.get("track") or {}).get("fields") or {} if self.case is not None else {}
        return tf.get("first")

    def mousePressEvent(self, e):
        """A click on the card: the video goes to where its track starts, with the track drawn there."""
        n = self.first_frame()
        if n is not None and self.window_.clip is not None:
            self.window_.show_video()
            self.window_.goto(int(n))
        super().mousePressEvent(e)

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
