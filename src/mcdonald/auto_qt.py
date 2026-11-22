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
one thing there in Auto Mode; Advanced Mode puts the three steps in its place.

Starting over (Jacob, 2026-11-22, after PR169: one bird, followed as three objects, and measured
as three again when he had opened the video anew and said he was looking for 1). Two things, both
on `clear.set_aside`, which moves what a results folder holds into `earlier/<date>_<time>/`
inside it and deletes nothing:

- "Start over", a quiet button at the foot of the card whenever something is saved for the open
  segment. It asks in the card, in one sentence with two buttons, never in a dialog. On yes the
  results are set aside and the video is as when first opened (`QtMarker.begin_again`): no marks,
  no track, no objects, no report, the three lights off, the button Begin. The card then says,
  once, where the results went. File -> Start this segment over… is the same question.
- The count the person gives is not ignored (`AutoRun.outdated`). The press went on from whatever
  the folder held, so three objects from a press that was told nothing were measured again for
  someone who had since said 1. Now, where every saved object was the press's own choice and the
  count said is not the one they were chosen for, the button says Begin again (the card asks
  `outdated` too) and the press starts over by itself, and says so under the button when it ends. What a person chose -- marks by hand, a row said yes to, rows
  ticked, an agent's -- is never set aside without the question: the press goes on from it as
  before, and Start over is theirs to press.
"""
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from . import actions, several
from .mark import CLASSES, MarkSet
from .mark_qt import ACCENT, MUTED, PRIMARY, QUIET, Command, Jewels, Stripes, heading, muted, with_command

AUTO = "Begin"                                    # the card's heading says what (Jacob, 2026-10-21: "the button can say \"Begin\"")
TAKEN = ("taken by the window's one-press run as the first spot on Find's list, with nobody looking: check the track "
         "sheet in the report")
TAKEN_SEVERAL = ("taken by the window's one-press run as one of the spots on Find's list worth following, with nobody "
                 "looking: check the track sheet in its report")
PRESS = "taken by the window's one-press run"     # in both: how a mark's record says the press chose it, not a person
BUSY = "Something is already running. Let it end, or stop it, and press again."
OVER_ASKS = ("Start over? The marks, tracks and reports saved for this segment will be set aside in a folder named "
             "earlier. Nothing is deleted, and the video stays open.")
ASIDE = "The results from before were set aside in {where}, inside the results folder."
NOT_ASIDE = "The results from before could not be set aside, so nothing was changed: {why}"


def aside_said(got):
    """What `clear.set_aside` did, in the card's one sentence: where the results went ("" where there were none)."""
    if not got or not got.get("into"):
        return ""
    return ASIDE.format(where=Path(got["into"]).relative_to(got["folder"]))


def by_the_press(ms):
    """Were all of a MarkSet's marks of the object taken by a one-press run (TAKEN, TAKEN_SEVERAL), none by a person?"""
    obj = ms.marks.get(CLASSES[0], {})
    return bool(obj) and all(PRESS in (ms.how_of(CLASSES[0], n) or "") for n in obj)


class AutoRun(QtCore.QObject):
    """The three steps, pressed in turn, by the window. `stage` is the one under way: "find", "link",
    "measure", or None; `why` is the sentence it ended with, when it ended short."""

    def __init__(self, window):
        super().__init__(window)
        self.w = window
        self.stage, self.why, self.used = None, "", False
        self.aside = ""                               # where a press that started over by itself put the results from before
        window.link_finished.connect(self._linked)

    def reset(self):
        self.stage, self.why, self.used = None, "", False
        self.aside = ""
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
            w.note.setText(BUSY)
            return
        self.why, self.used = "", True
        w.set_advanced(False)                         # the one press is the simple way: the steps' panel is not offered beside it
        w.note.quiet = True                           # nothing over the video while it goes: the card is the one voice
        self._next()

    def _next(self):
        """Whatever is still to do: find, if nothing is marked; follow, if nothing is followed; else measure -- after
        starting over, where what is saved is a press's own work for another count than the one said now (`outdated`)."""
        w = self.w
        self.aside = ""
        if self.outdated():
            if not w.can_start_over():                # the sound being read, or a report's speed worked out: they write there
                self._end(BUSY)
                return
            try:
                got = w.begin_again()                 # the video as when first opened, which resets this run too
            except OSError as ex:
                self._end(NOT_ASIDE.format(why=ex))
                return
            self.used, self.aside = True, aside_said(got)
            w.note.quiet = True
        link = w.links.get(0)
        if not w.ms.marks.get(CLASSES[0]) and several.things(w.several_base()):
            self._several(again=True)                 # the video's objects, each in a folder from a run before: again
        elif not w.ms.marks.get(CLASSES[0]):
            self._find()
        elif not (link is not None and link.track):
            self._link()
        else:
            self._measure()

    def outdated(self):
        """Is what the open segment's folder holds a one-press run's own work, made for another count of objects than
        the person says now? Then the press starts over (`_next`). Jacob, 2026-11-22: "I tried "open a new clip" and
        specifying 1 as the number of objects; but it still found 2" -- the three folders of the press before, measured
        again. The rule, with the cases in the method notes (section 111):

        - *The window's own object* (its marks here, not in an object's folder). A press told 1, or told nothing where
          one row of Find's list was worth following, leaves this; a press told 2 or more never does. So it is
          outdated when 2 or more are looked for now.
        - *Objects in folders of their own* (`several`). Their list records the count it was written for
          (`several.asked_before`). Outdated when that is not the count said now -- none said counts as a count -- or
          when there are more objects, their groups' members apart, than are looked for now: a press told N takes at
          most N rows. (The second half is for lists the press before 2026-11-22 wrote again under a new count.)

        And only where every object there was the press's own choice (`by_the_press`). Marks a person put by hand, a
        row they said yes to, rows they ticked and an agent's marks are theirs: the press goes on from them as it
        always did, whatever the count, and the card's Start over is the way to set them aside."""
        w = self.w
        now = w.objects_expected
        own = w.ms.marks.get(CLASSES[0])
        inside = several.NAME.match(Path(w.out).parent.name)     # the window has gone into one of several objects
        if own and not by_the_press(w.ms):
            return False
        if own and not inside:
            return bool(now) and now > 1
        base = w.several_base()
        found = [t for t in several.things(base) if not t.group]
        try:
            if not found or not all(by_the_press(MarkSet(t.tag, "", 1.0).load(t.marks)) for t in found):
                return False
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return False                              # marks that cannot be read are not known to be the press's
        return several.asked_before(base) != now or (now is not None and len(found) > now)

    def start_over(self):
        """The card's yes to "Start over?": the results set aside, the video as when first opened, and the card
        saying once where they went. Returns what `clear.set_aside` did, or None where it did nothing."""
        w = self.w
        if not w.can_start_over():
            return None
        try:
            got = w.begin_again()
        except OSError as ex:
            self.why = NOT_ASIDE.format(why=ex)
            w.say_steps()
            return None
        self.why = aside_said(got)
        w.say_steps()
        return got

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
            self._end("Nothing was found moving against the background, so there is no object to follow. Press Advanced "
                      "Mode below to look in other frames, or to click the object yourself.")
            return
        # every thing on the list worth following: the first row whatever it is, and any other that is at least fair
        # (Galileo flyer 1 has four things; one report each, as Find's ticks give -- Jacob, 2026-10-07) -- or, where the
        # person said how many they are looking for (the segment step, 2026-10-08), that many of the likeliest, weak
        # ones too, through the queue, which splits a group of points into its members where fewer were found
        asked = w.objects_expected
        from . import propose
        rows = propose.one_press_rows(p.proposals, asked)     # the rule, where a command line can call it too
        if len(rows) > 1 or (asked and asked > 1):
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
        if isinstance(got, BaseException):
            self._end(f"Measuring the objects stopped because something went wrong: {got}")
            return
        asked = self.w.objects_expected                  # the count against what was followed: the queue's last word
        self._end(several.tally(several.things(self.w.several_base()), asked)["sentence"] if asked else "")

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
                      + " Press Advanced Mode below to choose another spot on Find's list, or to click the object yourself.")
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
    the step cards': grey to do, a teal ring while under way, teal with a tick when done. They share the
    card's width, a third each, each in the middle of its third (Jacob, 2026-10-21: "centered and spanning
    the width of the column")."""

    def __init__(self):
        super().__init__()
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 2, 0, 0)
        row.setSpacing(0)
        self.badges, self.labels, self.stages = [], [], ["todo"] * 3
        for i, name in enumerate(("Find", "Follow", "Measure"), 1):
            badge = QtWidgets.QLabel(str(i))
            badge.setFixedSize(22, 22)
            badge.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label = QtWidgets.QLabel(name)
            third = QtWidgets.QHBoxLayout()
            third.setSpacing(6)
            third.addStretch(1)
            third.addWidget(badge)
            third.addWidget(label)
            third.addStretch(1)
            row.addLayout(third, 1)
            self.badges.append(badge)
            self.labels.append(label)
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
    (`QtMarker.say_steps` writes those, then calls `say`). At its foot, when something is saved for the
    open segment, `over`: Start over, quietly; pressed, `ask` takes its place -- the question in one
    sentence, `yes` (Start over) and `keep` (Keep them) -- until one of them is pressed or a step starts."""

    def __init__(self, window):
        super().__init__()
        self.window_ = window
        self.setObjectName("auto")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)
        lay.addWidget(heading("Measure the object", 1.1))
        self.line = muted("Automatically find, follow, and measure the object")         # Jacob's words, 2026-10-21
        lay.addWidget(self.line)
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
        self.command = Command()                      # the step's command, as its card names it
        self.jewels = Jewels()                        # the step's bars, as its card has them, under the bar
        lay.addLayout(with_command(self.busy, self.command, self.jewels))
        self.state = QtWidgets.QLabel()
        self.state.setWordWrap(True)
        self.state.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.state.hide()
        lay.addWidget(self.state)
        # Start over (Jacob, 2026-11-22): quiet, under everything else, and its question here in the card
        over = next(a for a in actions.ACTIONS if a.id == "start_over")
        self.over = QtWidgets.QPushButton("Start over")
        self.over.setStyleSheet(QUIET)
        self.over.setToolTip(over.help)
        self.over.clicked.connect(lambda _=False: window.do("start_over"))
        self.over_row = QtWidgets.QWidget()           # a widget, hidden whole: an empty row of buttons would keep its room
        foot = QtWidgets.QHBoxLayout(self.over_row)
        foot.setContentsMargins(0, 0, 0, 0)
        foot.addWidget(self.over)
        foot.addStretch(1)
        lay.addWidget(self.over_row)
        self.over_row.hide()
        self.ask = QtWidgets.QFrame()
        self.ask.setObjectName("over")
        self.ask.setStyleSheet("QFrame#over { background: #3a2f16; border: 1px solid #8a6a1f; border-radius: 6px; }")
        al = QtWidgets.QVBoxLayout(self.ask)
        al.setContentsMargins(8, 6, 8, 8)
        al.setSpacing(6)
        self.ask_text = QtWidgets.QLabel(OVER_ASKS)
        self.ask_text.setWordWrap(True)
        al.addWidget(self.ask_text)
        answers = QtWidgets.QHBoxLayout()
        answers.addStretch(1)
        self.keep = QtWidgets.QPushButton("Keep them")
        self.keep.setStyleSheet(QUIET)
        self.keep.setToolTip("change nothing: the results stay where they are")
        self.keep.clicked.connect(lambda _=False: self.keep_them())
        self.yes = QtWidgets.QPushButton("Start over")
        self.yes.setStyleSheet(PRIMARY)
        self.yes.setToolTip("set the results aside in the folder named earlier, and begin again with nothing saved")
        self.yes.clicked.connect(lambda _=False: self.start_over())
        for b in (self.over, self.keep, self.yes):
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            b.setAutoDefault(False)
        answers.addWidget(self.keep)
        answers.addWidget(self.yes)
        al.addLayout(answers)
        lay.addWidget(self.ask)
        self.ask.hide()
        self._was_advanced = False                    # the question was asked from Advanced Mode: Keep them goes back to it
        self._now = None
        self._frame(True)

    def ask_over(self):
        """Start over, asked for (the quiet button, or File -> Start this segment over…): the question, here. From
        Advanced Mode the card comes back to ask it, and Keep them puts the three steps back."""
        w = self.window_
        self._was_advanced = bool(w.advanced)
        w.set_advanced(False)
        self.ask.show()
        self.say()
        w.panel_area.ensureWidgetVisible(self.ask)

    def keep_them(self):
        """No: nothing changes, and the card is as it was."""
        self.ask.hide()
        if self._was_advanced:
            self.window_.set_advanced(True)
        self.say()

    def start_over(self):
        """Yes (`AutoRun.start_over`): the card then says where the results went."""
        self.ask.hide()
        self.window_.auto.start_over()

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
        objects = len(sp.rows) if queue else 0
        if loaded and not queue and not running and not w.ms.marks.get(CLASSES[0]):
            # ... or their folders are here from an earlier day, and the queue's panel is not made until it is asked for:
            # the card said Begin over their report cards, with its lights off, and the press measured them again
            # (PR169 opened again, 2026-11-22). They are found, and measured, whoever looks
            found = several.things(w.several_base())
            queue, objects, ready = bool(found), len(found), sum(1 for t in found if t.report is not None)
        if queue and ready:
            report = True
        # what is saved is the press's own, for another count than the one said now (`AutoRun.outdated`): the press
        # will set it aside and begin, so the button says Begin, in colour, with the lights off -- not Measure again
        stale = loaded and not running and not a.busy_elsewhere() and a.outdated()
        if running:
            k = a.step_number()
            st = w.steps[k - 1]
            # no line under the bar (Jacob, 2026-10-20: "remove the descriptive text below the progress bar"): the lights
            # under the button say which step it is, and the step's jewels how many bars it has and how many are over
            text = ""
            self.busy.set_fraction(st.busy.fraction if st.busy.isVisibleTo(st) else None)
            self.busy.show()
            self.command.say(st.command.text())
            self.jewels.set(st.jewels.names, st.jewels.done)
            self.jewels.setVisible(st.jewels.isVisibleTo(st))
            self.button.setText("Stop")
            self.button.setEnabled(True)
        else:
            self.busy.hide()
            self.command.say(None)
            self.jewels.hide()
            self.button.setText("Measure again" if report and not stale else AUTO)
            self.button.setEnabled(loaded and not a.busy_elsewhere())
            # a report is the card under this one; it speaks for itself. A press that started over says where the
            # results from before went, after whatever it ended with
            text = " ".join(x for x in (a.why, a.aside) if x) if loaded else ""
        self.state.setText(text)
        self.state.setVisible(bool(text))
        self.state.setStyleSheet("" if running or not text else f"color: {MUTED};")
        # Start over: there whenever something is saved for the segment and the press is not running; greyed while
        # another step runs. Its question goes when anything starts, or when nothing is left to start over from
        free = loaded and w.can_start_over()
        there = free or (loaded and not running and w.saved_before())
        if not free:
            self.ask.hide()
        self.over_row.setVisible(there and self.ask.isHidden())
        self.over.setEnabled(free)
        if hasattr(w, "acts"):
            w.acts["start_over"].setEnabled(free)
        self._frame(loaded and not running and (stale or not report))
        # the three lights: what is done, and which step is under way
        link = w.links.get(0) if loaded else None
        if stale:
            stages = ["todo"] * 3
        elif queue:                                   # the objects: found; followed and measured in turn, as one step each
            stages = ["done", "done" if ready else "todo", "done" if ready == objects else "todo"]
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
        # "Once the 1-button mode is chosen, Advanced should no longer be an option"); View -> Advanced Mode stays, for
        # later, and once in it, Auto Mode is offered to come back. It is back when the run ended short -- nothing found,
        # nothing followed, stopped -- because its sentence then points at it ("Press Advanced Mode below"), and the
        # simple way has nothing more to offer (2026-10-09)
        w.mode_button.setVisible(w.advanced or not a.used or bool(a.why))
        if hasattr(w, "acts"):
            w.acts["advanced"].setEnabled(not running)
