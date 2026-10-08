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

It is quiet while it goes (Jacob, 2026-10-07: "we do not need the 'Which one is the object?' or
other inset frames popping up. Otherwise the user will be confused and think they need to make
a choice"): Find's list is not shown, the track's check is not put under the video, and no note
is said over it. The card says which step it is on; the video shows the marks and the track as
they come; the report is the one thing that opens. What the run left behind is there for
Advanced afterwards: "Show what Find found", and "Check the track" with the pictures along it.

Nothing is decided here that the steps do not decide, and the files say what was decided by
whom: the marks are the detector's proposal, taken by this run and not by a person looking,
and the record says so.

`AutoCard` is the button and how the job stands under it, at the top of the side panel: the
one thing there unless Advanced is on.
"""
import re
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from . import actions, several
from .mark import CLASSES
from .mark_qt import ACCENT, MUTED, PRIMARY, QUIET, Stripes, heading, muted

AUTO = "Find, follow and measure the object"
STEP_WORDS = {1: "finding the object", 2: "following it", 3: "measuring"}
TAKEN = ("taken by the window's one-press run as the first thing on Find's list, with nobody looking: check the track "
         "sheet in the report")
TAKEN_SEVERAL = ("taken by the window's one-press run as one of the things on Find's list worth following, with nobody "
                 "looking: check the track sheet in its report")


class AutoRun(QtCore.QObject):
    """The three steps, pressed in turn, by the window. `stage` is the one under way: "find", "link",
    "measure", or None; `why` is the sentence it ended with, when it ended short."""

    def __init__(self, window):
        super().__init__(window)
        self.w = window
        self.stage, self.why, self.used = None, "", False
        window.link_finished.connect(self._linked)

    def reset(self):
        self.stage, self.why, self.used = None, "", False
        self.w.note.quiet = False

    def running(self):
        return self.stage is not None

    def step_number(self):
        return {"find": 1, "link": 2, "measure": 3, "several": 3}.get(self.stage, 0)

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
        self.why, self.used = "", True
        w.set_advanced(False)                         # the one press is the simple way: the steps' panel is not offered beside it
        w.note.quiet = True                           # nothing over the video while it goes: the card is the one voice
        self._next()

    def _next(self):
        """Whatever is still to do: find, if nothing is marked; follow, if nothing is followed; else measure."""
        w = self.w
        link = w.links.get(0)
        if not w.ms.marks.get(CLASSES[0]) and several.things(w.several_base()):
            self._several(again=True)                 # the video's objects, each in a folder from a run before: again
        elif not w.ms.marks.get(CLASSES[0]):
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
        self.stage = "find"                           # the list is not shown: it would look like a choice to make
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
        # every thing on the list worth following: the first row whatever it is, and any other that is at least fair
        # (Galileo flyer 1 has four things; one report each, as Find's ticks give -- Jacob, 2026-10-07)
        rows = [i for i, q in enumerate(p.proposals) if i == 0 or q.strength() != "weak"]
        if len(rows) > 1:
            self._several(rows=rows)
            return
        self.stage = "link"
        p.accept_proposal(0, TAKEN)                   # marks along the best row, saved as proposed; the link starts; the list goes
        w.say_steps()

    # -- several things: a queue of cases, each with a report, nothing asked and nothing shown --------------
    def _several(self, rows=None, again=False):
        """Rows of Find's list as objects of their own, followed and measured in turn (`several_qt`, quiet); or,
        with `again`, the objects already in the video's folders measured again."""
        w = self.w
        from . import several_qt
        if w.several_panel is None:
            w.several_panel = several_qt.SeveralPanel(w)
        sp = w.several_panel
        if not getattr(sp, "_auto_hooked", False):
            sp.done.connect(self._several_done)
            sp._auto_hooked = True
        self.stage = "several"
        if rows is not None:
            w.find_panel.take_rows(rows, TAKEN_SEVERAL, quiet=True)
        else:
            sp.refresh()
            sp.start(again=again)
        if not sp.running():
            self._end("The objects could not be followed and measured.")
        w.say_steps()

    @QtCore.Slot(object)
    def _several_done(self, got):
        if self.stage != "several":
            return
        self._end(f"Measuring the objects stopped because something went wrong: {got}" if isinstance(got, BaseException) else "")

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
        elif self.stage == "several" and w.several_panel is not None and w.several_panel.running():
            w.several_panel.stop()
        self._end("Stopped.")

    def _end(self, why):
        self.stage, self.why = None, why or ""
        self.w.note.quiet = False
        self.w.say_steps()


class StepLights(QtWidgets.QWidget):
    """Three lights under the one button -- Find, Follow, Measure -- lit as each step is done (Jacob,
    2026-10-07: "It helps the user understand that steps are being completed"). Each is a badge like
    the step cards': grey to do, a teal ring while under way, teal with a tick when done."""

    def __init__(self):
        super().__init__()
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 2, 0, 0)
        row.setSpacing(6)
        self.badges, self.labels, self.stages = [], [], ["todo"] * 3
        for i, name in enumerate(("Find", "Follow", "Measure"), 1):
            badge = QtWidgets.QLabel(str(i))
            badge.setFixedSize(22, 22)
            badge.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label = QtWidgets.QLabel(name)
            row.addWidget(badge)
            row.addWidget(label)
            if i < 3:
                row.addSpacing(10)
            self.badges.append(badge)
            self.labels.append(label)
        row.addStretch(1)
        self.set(self.stages)

    def set(self, stages):
        """`stages`: "todo", "busy" or "done" for each of the three."""
        self.stages = list(stages)
        for i, (badge, label, stage) in enumerate(zip(self.badges, self.labels, stages), 1):
            done, busy = stage == "done", stage == "busy"
            badge.setText("✓" if done else str(i))
            badge.setStyleSheet("border-radius: 11px; font-weight: bold; "
                                + (f"background: {ACCENT}; color: #0b1a1c;" if done else
                                   f"border: 2px solid {ACCENT}; color: {ACCENT}; background: transparent;" if busy else
                                   "background: #34343a; color: #b8b6ae;"))
            label.setStyleSheet("font-weight: bold;" if busy else "" if done else f"color: {MUTED};")


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
        lay.addWidget(muted("Finds what moves against the background, takes the most likely thing as the object, follows it, "
                            "works out how it moved, and writes a report. Nothing is asked on the way. Afterwards, check the "
                            "track sheet in the report."))
        self.button = QtWidgets.QPushButton(AUTO)
        row = next(a for a in actions.ACTIONS if a.id == "auto")
        self.button.setToolTip(f"{row.help} ({actions.spoken(row.keys[0])})")
        self.button.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.button.setAutoDefault(False)
        self.button.setMinimumHeight(36)
        self.button.clicked.connect(lambda _=False: window.do("auto"))
        lay.addWidget(self.button)
        self.lights = StepLights()
        lay.addWidget(self.lights)
        self.busy = Stripes()
        self.busy.hide()
        lay.addWidget(self.busy)
        self.state = QtWidgets.QLabel()
        self.state.setWordWrap(True)
        self.state.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.state.hide()
        lay.addWidget(self.state)
        self._now = None
        self._frame(True)

    def _frame(self, now):
        """Drawn as the thing to do next (the step cards' teal), or quietly."""
        if now == self._now:
            return
        self._now = now
        self.setStyleSheet(f"QFrame#auto {{ border: 1px solid {ACCENT if now else '#34343a'}; border-radius: 8px; "
                           f"background: {'#16262a' if now else 'transparent'}; }}")
        self.button.setStyleSheet(PRIMARY if now else QUIET)

    def say(self):
        w = self.window_
        a = w.auto
        loaded = w.clip is not None
        report = loaded and Path(f"{w.out}_case.md").exists()
        running = loaded and a.running()
        sp = w.several_panel
        queue = loaded and sp is not None and bool(sp.rows) and not w.ms.marks.get(CLASSES[0])     # several objects, a report each
        ready = sum(1 for r in sp.rows.values() if r.thing.report is not None) if queue else 0
        if queue and ready:
            report = True
        if running:
            k = a.step_number()
            st = w.steps[k - 1]
            # the step's own line, without the clock (Jacob, 2026-10-07: no elapsed and no time left here) and without
            # "Step k of 3": the lights under the button say which step it is
            line = " · ".join(part for part in st.state.text().split(" · ") if "elapsed" not in part)
            line = re.sub(r", about [\d:]+ left( in this step)?", "", line).strip()
            text = line or f"{STEP_WORDS[k][:1].upper()}{STEP_WORDS[k][1:]}…"
            self.busy.set_fraction(st.busy.fraction if st.busy.isVisibleTo(st) else None)
            self.busy.show()
            self.button.setText("Stop")
            self.button.setEnabled(True)
        else:
            self.busy.hide()
            self.button.setText("Measure again" if report else AUTO)
            self.button.setEnabled(loaded and not a.busy_elsewhere())
            text = a.why if loaded else ""                # a report is the card under this one; it speaks for itself
        self.state.setText(text)
        self.state.setVisible(bool(text))
        self.state.setStyleSheet("" if running or not a.why else f"color: {MUTED};")
        self._frame(loaded and not running and not report)
        # the three lights: what is done, and which step is under way
        link = w.links.get(0) if loaded else None
        if queue:                                     # the objects: found; followed and measured in turn, as one step each
            stages = ["done", "done" if ready else "todo", "done" if ready == len(sp.rows) else "todo"]
            if running and a.stage == "several":
                stages[1:] = ["busy", "busy"]
        else:
            stages = ["done" if loaded and w.ms.marks.get(CLASSES[0]) else "todo",
                      "done" if link is not None and link.track and not w.linking() else "todo",
                      "done" if report else "todo"]
            if running:
                stages[a.step_number() - 1] = "busy"
        self.lights.set(stages)
        # once the button has been pressed for this video, the steps' panel is not offered beside it (Jacob, 2026-10-07:
        # "Once the 1-button mode is chosen, Advanced should no longer be an option"); View -> Advanced stays, for later
        w.advanced_toggle.setVisible(not a.used)
        if hasattr(w, "acts"):
            w.acts["advanced"].setEnabled(not running)
