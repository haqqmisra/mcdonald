"""One press for the whole job: find the object, follow it, measure it, write the report.

Jacob, 2026-10-07: "Users should begin with an all-in-one button press option that goes
through all steps without asking for any confirmations. In many cases, the mcdonald high
ranking choices are correct." `AutoRun` is that press. It is the three steps of the side
panel pressed in turn, with the same code behind each: Find (`find_qt`) on everything that
is open, the first row of its list taken as the object -- marks along its path, recorded as
proposed, as "This is it" records them -- the link from those marks (Follow), and Measure
(`measure_qt`) with nothing asked: the track sheet's question is not put, so the report says
its numbers are not yet sure until someone looks at the sheet and says so on the report's
page, as the reports of a queue of several objects do. The report then opens. Where a step
gives it nothing to go on -- nothing found, nothing followed -- it stops with a sentence that
says so and points at Advanced: the three steps one at a time, and marking by hand.

Nothing is decided here that the steps do not decide, and the files say what was decided by
whom: the marks are the detector's proposal, taken by this run and not by a person looking,
and the record says so.

`AutoCard` is the button and how the job stands under it, at the top of the side panel: the
one thing there unless Advanced is on.
"""
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from . import actions
from .mark import CLASSES
from .mark_qt import ACCENT, MUTED, Stripes, heading, muted

AUTO = "Find, follow and measure the object"
STEP_WORDS = {1: "finding the object", 2: "following it", 3: "measuring"}
TAKEN = ("taken by the window's one-press run as the first thing on Find's list, with nobody looking: check the track "
         "sheet in the report")


class AutoRun(QtCore.QObject):
    """The three steps, pressed in turn, by the window. `stage` is the one under way: "find", "link",
    "measure", or None; `why` is the sentence it ended with, when it ended short."""

    def __init__(self, window):
        super().__init__(window)
        self.w = window
        self.stage, self.why = None, ""
        window.link_finished.connect(self._linked)

    def reset(self):
        self.stage, self.why = None, ""

    def running(self):
        return self.stage is not None

    def step_number(self):
        return {"find": 1, "link": 2, "measure": 3}.get(self.stage, 0)

    def busy_elsewhere(self):
        """Is a step under way that this run did not start?"""
        w = self.w
        return (w.linking() or (w.find_panel is not None and w.find_panel.running())
                or (w.measure_panel is not None and w.measure_panel.running())
                or (w.several_panel is not None and w.several_panel.running()))

    def toggle(self):
        """The one button, or its key: start, or stop what it started."""
        if self.running():
            self.stop()
        else:
            self.start()

    def start(self):
        w = self.w
        if w.clip is None or self.running():
            return
        if self.busy_elsewhere():
            w.note.setText("Something is already running. Let it end, or stop it, and press again.")
            return
        self.why = ""
        self._next()

    def _next(self):
        """Whatever is still to do: find, if nothing is marked; follow, if nothing is followed; else measure."""
        w = self.w
        link = w.links.get(0)
        if not w.ms.marks.get(CLASSES[0]):
            self._find()
        elif not (link is not None and link.track):
            self._link()
        else:
            self._measure()

    # -- 1 find ----------------------------------------------------------------------------------
    def _find(self):
        w = self.w
        from . import find_qt
        if w.find_panel is None:
            w.find_panel = find_qt.FindPanel(w)
        p = w.find_panel
        if not getattr(p, "_auto_hooked", False):
            p.done.connect(self._found)
            p._auto_hooked = True
        p.refresh()
        p.whole.setChecked(True)                      # everything that is open: the segment is the person's choice already
        self.stage = "find"
        w.show_work(p)                                # what it finds is listed as it goes, for the person to see
        if p.running():
            pass
        elif p.proposals:                             # a list from before: that is what there is to choose from
            self._found(None)
        else:
            p.start()
            if not p.running() and not p.proposals:   # it would not start (a part too short to look in): the panel said why
                self._end(p.now.text())
        w.say_steps()

    @QtCore.Slot(object)
    def _found(self, ex):
        if self.stage != "find":
            return
        w, p = self.w, self.w.find_panel
        if w.ms.marks.get(CLASSES[0]):                # the person chose one meanwhile: the link is theirs, follow it
            self.stage = "link"
            if not w.linking():
                self._linked()
            return
        if isinstance(ex, BaseException):
            self._end(f"Looking for the object stopped because something went wrong: {ex}")
            return
        if not p.proposals:
            self._end("Nothing was found moving against the background, so there is no object to follow. Turn on Advanced "
                      "below to look in other frames, or to click the object yourself.")
            return
        self.stage = "link"
        p.accept_proposal(0, TAKEN)                   # marks along the best row, saved as proposed; the link starts; the list goes
        w.say_steps()

    # -- 2 follow --------------------------------------------------------------------------------
    def _link(self):
        self.stage = "link"
        self.w.do("link")
        if not self.w.linking():                      # it would not start (no mark it can follow): step 2 said why
            self._linked()

    @QtCore.Slot()
    def _linked(self):
        if self.stage != "link":
            return
        w = self.w
        link = w.links.get(0)
        if not (link is not None and link.track):
            said = w.link_label.text().split("\n")[0]
            self._end("The object could not be followed from the marks" + (f": {said}" if said else ".")
                      + " Turn on Advanced below to choose another thing on Find's list, or to click the object yourself.")
            return
        self._measure()

    # -- 3 measure -------------------------------------------------------------------------------
    def _measure(self):
        w = self.w
        from . import measure_qt
        if w.measure_panel is None:
            w.measure_panel = measure_qt.MeasurePanel(w)
        mp = w.measure_panel
        if not getattr(mp, "_auto_hooked", False):
            mp.done.connect(self._measured)
            mp._auto_hooked = True
        mp.refresh()
        self.stage = "measure"
        mp.start(ask=False)                           # nothing asked: the report says its numbers are not yet sure
        if not mp.running():
            self._end("Measuring did not start.")

    @QtCore.Slot(object)
    def _measured(self, got):
        if self.stage != "measure":
            return
        self._end(f"Measuring stopped because something went wrong: {got}" if isinstance(got, BaseException) else "")

    # -- stopping, ending ------------------------------------------------------------------------
    def stop(self):
        w = self.w
        if self.stage == "find" and w.find_panel is not None:
            w.find_panel.stop()
        elif self.stage == "link" and w.linking():
            w._link_stop.set()
        elif self.stage == "measure" and w.measure_panel is not None and w.measure_panel.running():
            w.measure_panel.stop()
        self._end("Stopped.")

    def _end(self, why):
        self.stage, self.why = None, why or ""
        self.w.say_steps()


class AutoCard(QtWidgets.QFrame):
    """The one button, and how the job stands under it. Its state is read off the three step cards
    (`QtMarker.say_steps` writes those, then calls `say`)."""

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.setObjectName("auto")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)
        lay.addWidget(heading("Measure the object", 1.1))
        lay.addWidget(muted("The computer looks for what moves against the background, takes the most likely thing as the "
                            "object, follows it, works out how it moved, and writes a report. Nothing is asked on the way. "
                            "When the report opens, look at its track sheet, and say at the top whether the ring is on the "
                            "object in every frame."))
        self.button = QtWidgets.QPushButton(AUTO)
        row = next(a for a in actions.ACTIONS if a.id == "auto")
        self.button.setToolTip(f"{row.help} ({actions.spoken(row.keys[0])})")
        self.button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.button.setAutoDefault(False)
        self.button.setMinimumHeight(36)
        self.button.clicked.connect(lambda _=False: window.do("auto"))
        lay.addWidget(self.button)
        self.busy = Stripes()
        self.busy.hide()
        lay.addWidget(self.busy)
        self.state = QtWidgets.QLabel()
        self.state.setWordWrap(True)
        self.state.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.state.hide()
        lay.addWidget(self.state)
        row = QtWidgets.QHBoxLayout()
        self.report_button = QtWidgets.QPushButton("Open the report")
        self.report_button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.report_button.setAutoDefault(False)
        self.report_button.clicked.connect(lambda _=False: window.do("report"))
        self.report_button.hide()
        row.addWidget(self.report_button)
        row.addStretch(1)
        lay.addLayout(row)
        self._now = None
        self._frame(True)

    def _frame(self, now):
        """Drawn as the thing to do next (the step cards' teal), or quietly."""
        if now == self._now:
            return
        self._now = now
        self.setStyleSheet(f"QFrame#auto {{ border: 1px solid {ACCENT if now else '#34343a'}; border-radius: 8px; "
                           f"background: {'#16262a' if now else 'transparent'}; }}")
        self.button.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: #0b1a1c; font-weight: bold; padding: 6px 12px; "
            f"border-radius: 5px; border: none; }} QPushButton:hover {{ background: #7fe3d8; }} "
            f"QPushButton:disabled {{ background: #2d4a4a; color: #7a8a8a; }}" if now else
            "QPushButton { padding: 6px 12px; } QPushButton:disabled { color: #6b6a66; }")

    def say(self):
        w = self.window_
        a = w.auto
        loaded = w.clip is not None
        report = loaded and Path(f"{w.out}_case.md").exists()
        running = loaded and a.running()
        if running:
            k = a.step_number()
            st = w.steps[k - 1]
            line = st.state.text()
            text = f"Step {k} of 3, {STEP_WORDS[k]}" + (f": {line[:1].lower() + line[1:]}" if line else "…")   # "…: step 2 of 12 · Survey"
            self.busy.set_fraction(st.busy.fraction if st.busy.isVisibleTo(st) else None)
            self.busy.show()
            self.button.setText("Stop")
            self.button.setEnabled(True)
        else:
            self.busy.hide()
            self.button.setText("Measure again" if report else AUTO)
            self.button.setEnabled(loaded and not a.busy_elsewhere())
            text = (a.why or ("The report is ready." if report else "")) if loaded else ""
        self.state.setText(text)
        self.state.setVisible(bool(text))
        self.state.setStyleSheet("" if running or report or not a.why else f"color: {MUTED};")
        self.report_button.setVisible(bool(report) and not running)
        self._frame(loaded and not running and not report)
