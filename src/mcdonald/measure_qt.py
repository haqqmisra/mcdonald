"""The measurements, from the window: `mcdonald run` for someone who has no terminal.

The window used to end where the measurements began. Measure -> Measure this clip
saves the marks and the link, asks what the person knows that the pixels cannot
say, and hands both to `stages.run_case` -- the function `mcdonald run` is a
command line over -- on a thread of its own. What comes back is put in front of
them: the track sheet first, with the question the command line asks as
`--i-looked`, and at the end the case report.

Nothing is measured here. The form is made from `stages.KNOWN`, the rows
`mcdonald run`'s options are made from, so the two cannot come to differ; what is
said while it runs is what the command line prints; and the report is the file
`run` writes, shown. A number in it is the number the command line gives because
it is the same call (tests/test_gui.py holds the two to that).

The gate is kept. `run_case` makes the track sheet before anything is measured
from the track and then asks `i_looked`; here that is a question on the screen,
under the sheet, and the measuring thread waits for the answer. Closing the
sheet, or the panel, is "no": the report then calls the object measurements
provisional, as it does for a command line that was not told `--i-looked`.
"""
import re
import threading
import time
from html import escape
from pathlib import Path
from urllib.parse import unquote

from PySide6 import QtCore, QtGui, QtWidgets

from . import forensics as vf
from . import stages
from .mark import CLASSES
from .mark_qt import ACCENT, MUTED, beside, complain
from .progress import clock, left

ASK = ("Is the circle on the object in every frame?\n"
       "Every number measured from this track needs that to be true. A track that sits on a bit of cloud for seven "
       "frames gives a clean but wrong speed.")
MAIN = (f"QPushButton {{ background: {ACCENT}; color: #0b1a1c; font-weight: bold; padding: 7px 16px; border-radius: 5px; "
        "border: none; } QPushButton:hover { background: #7fe3d8; } QPushButton:disabled { background: #2d4a4a; color: #7a8a8a; }")


RULED = ("ref_px", "size_px", "diameter")     # the optional fields that are a length on the screen: a ruler beside each


def heading(text, scale=1.3):
    label = QtWidgets.QLabel(text)
    font = label.font()
    font.setPointSizeF(font.pointSizeF() * scale)
    font.setBold(True)
    label.setFont(font)
    return label


def muted(text=""):
    label = QtWidgets.QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(f"color: {MUTED};")
    return label


def card(title):
    """A titled box of related choices, drawn quietly."""
    box = QtWidgets.QGroupBox(title)
    box.setStyleSheet("QGroupBox { border: 1px solid #34343a; border-radius: 8px; margin-top: 14px; padding: 10px 10px 6px 10px; "
                      "font-weight: bold; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }")
    return box


def folding(text, body, open_=False):
    """A button with an arrow that shows and hides `body`."""
    b = QtWidgets.QToolButton()
    b.setText(text)
    b.setCheckable(True)
    b.setAutoRaise(True)
    b.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    b.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

    def show(on):
        b.setArrowType(QtCore.Qt.ArrowType.DownArrow if on else QtCore.Qt.ArrowType.RightArrow)
        body.setVisible(on)
    b.toggled.connect(show)
    b.setChecked(open_)
    show(open_)
    return b


def sheet_layout(clip, tile=320, tallest=30000):
    """The track sheet's layout for a screen. The command line's is 30 tiles across, a
    picture for an image viewer to zoom into; in a window that is one row to be scrolled
    sideways. Six across fits a screen and scrolls down -- and more on a long clip, because
    a pixmap taller than 32767 px cannot be shown at all."""
    th = int(round(tile * clip.H / clip.W))
    n = clip.n1 - clip.n0 + 1
    return dict(tile=tile, cols=max(6, -(-n * th // tallest)))


def around(track, clip, seconds=2.0):
    """The frames worth measuring for a track: the track, and `seconds` either side of it,
    inside what is open. Someone who opened a whole clip to find a four-frame transit has
    5291 frames open, and measuring all of them is hours: the object's rates come from the
    frames it is in, and the background's need a second or two round them."""
    pad = int(round(seconds * clip.fps))
    return max(clip.n0, min(track) - pad), min(clip.n1, max(track) + pad)


def cost_text(n0, n1, chosen):
    """What the slow stages will take on these frames, said before they start."""
    pairs = max(n1 - n0 - 4, 0)
    L = []
    if "layers" in chosen:
        L.append(f"layers: {pairs} pairs of frames at about a second each, so about {_about(pairs * 1.7)}")
    if "integrity" in chosen:
        L.append(f"integrity: longer still, about {_about(pairs * 2.6 + 90)}")
    rest = (n1 - n0 + 1) * 0.4                      # groups and flicker, about 0.4 s a frame between them (PR135)
    if rest > 60 and ("groups" in chosen or "flicker" in chosen):
        L.append(f"looking for a group of points and for a beat in the brightness: about {_about(rest)}")
    return "; ".join(L) if L else "Without the two slow steps this takes less than a minute."


def _about(seconds):
    m = max(1, round(seconds / 60))
    return f"{m} minute{'s' if m != 1 else ''}" if seconds < 5400 else f"{seconds / 3600:.1f} hours"


# Slow checks left unticked until someone ticks them: integrity more than doubles the time, and is a
# question about the video rather than the object's motion (Jacob, 2026-09-25).
OFF_AT_FIRST = {"integrity"}


class MeasurePanel(QtWidgets.QFrame):
    """The form, the button, and what is said while the case is made."""
    said = QtCore.Signal(str)                     # a line for the person, from the measuring thread
    step = QtCore.Signal(str, object, object)     # a long step: its name, and how far it has got of how many, if it can count
    sheet_made = QtCore.Signal(str)               # the track sheet is on disk: show it, and ask
    done = QtCore.Signal(object)                  # (case, files), or the exception that ended it

    def __init__(self, window):
        super().__init__(window)
        self.window_, self.case, self.files, self.sheet, self.report = window, None, [], None, None
        self.sheet_path, self._answer, self._answered = None, False, threading.Event()
        self._range_for, self.pad_seconds = None, 2.0
        self._stop, self._thread, self.closed = threading.Event(), None, False
        self.setWindowTitle(f"Measure — {window.ms.tag}")
        outer = QtWidgets.QVBoxLayout(self)          # a part of the window, under the video (Jacob, 2026-09-25):
        outer.setContentsMargins(0, 0, 0, 0)         # the heading and the button stay, what is between them scrolls
        top = QtWidgets.QHBoxLayout()
        top.addWidget(heading("Measure the object"), 1)
        from .find_qt import close_button
        # While it measures, the ✕ only puts the panel away: closing it stopped the measuring, and on PR23
        # a report came out with no pixel velocity because of it (Jacob, 2026-09-25). Stop is step 3's button.
        top.addWidget(close_button(self, lambda: self.put_away() if self.running() else self.close()))
        outer.addLayout(top)
        body = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(body)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(10)
        area = QtWidgets.QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setWidget(body)
        outer.addWidget(area, 1)
        self.body_area = area
        self.what = muted()
        lay.addWidget(self.what)

        frames = card("Frames to measure")
        fl = QtWidgets.QVBoxLayout(frames)
        self.near = QtWidgets.QRadioButton()
        self.whole = QtWidgets.QRadioButton()
        for b in (self.near, self.whole):
            b.toggled.connect(self._say_cost)
            fl.addWidget(b)
        self.frames_box = frames
        lay.addWidget(frames)

        slow = card("Slow checks")
        sl = QtWidgets.QVBoxLayout(slow)
        self.slow = {}
        for name, why in stages.SLOW.items():
            self.slow[name] = QtWidgets.QCheckBox(f"{name}: {why}")
            self.slow[name].setChecked(name not in OFF_AT_FIRST)
            self.slow[name].toggled.connect(self._say_cost)
            sl.addWidget(self.slow[name])
        self.cost = muted()
        sl.addWidget(self.cost)
        lay.addWidget(slow)

        known = QtWidgets.QWidget()
        known.setObjectName("technical")              # the trade's terms are fine here (Jacob, 2026-09-24): the plain-words test skips it
        kl = QtWidgets.QVBoxLayout(known)
        kl.setContentsMargins(18, 0, 0, 0)
        kl.addWidget(muted("Leave empty what you do not know."))
        form = QtWidgets.QFormLayout()
        self.fields, self.rulers = {}, {}
        for k in stages.KNOWN:
            edit = QtWidgets.QLineEdit()
            edit.setToolTip(f"{k.help} (command line: {k.flag})")
            edit.setPlaceholderText(k.help if k.kind is str else k.unit)
            if k.kind is float:
                v = QtGui.QDoubleValidator(self)
                v.setLocale(QtCore.QLocale.c())       # a point is a point: what the command line reads
                edit.setValidator(v)
            edit.textChanged.connect(self._say_known)
            self.fields[k.name] = edit
            label = k.term or (k.label + (f"  ({k.unit})" if k.unit else ""))
            if k.name in RULED:                           # a length on the screen: measured on the video, not guessed
                row = QtWidgets.QHBoxLayout()
                row.addWidget(edit, 1)
                ruler = QtWidgets.QPushButton("Measure on the video")
                ruler.setToolTip("drag along it on the video, from one end to the other; the length in pixels goes here")
                ruler.setAutoDefault(False)
                ruler.clicked.connect(lambda _=False, e=edit: self.window_.start_ruler(lambda px, e=e: self._ruled(e, px)))
                row.addWidget(ruler)
                self.rulers[k.name] = ruler
                form.addRow(label, row)
            else:
                form.addRow(label, edit)
        kl.addLayout(form)
        self.known_toggle = folding("Provide additional information about this video (optional)", known)
        lay.addWidget(self.known_toggle)
        lay.addWidget(known)

        # while it runs: where it has got to. Is it working, or has it hung? The bar is the answer: it
        # counts where the step can count (frame pairs, tiles), runs to and fro where it cannot, and the
        # clock beside it never stops
        self.bar = QtWidgets.QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(8)
        self.bar.setRange(0, 1)
        self.bar.setValue(0)
        lay.addWidget(self.bar)
        self.now = QtWidgets.QLabel()
        self.now.setWordWrap(True)
        lay.addWidget(self.now)
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont))
        self.log.setMinimumHeight(160)
        self.log_toggle = folding("Show details", self.log)
        lay.addWidget(self.log_toggle)
        lay.addWidget(self.log, 1)
        self.bar.hide()
        self.now.hide()
        self.log_toggle.hide()
        lay.addStretch(0)

        row = QtWidgets.QHBoxLayout()
        self.elapsed = muted()
        self.elapsed.hide()                           # step 3 says it, on the right
        row.addWidget(self.elapsed, 1)
        row.addStretch(1)
        self.halt = QtWidgets.QPushButton("Stop")
        self.halt.setToolTip("the step that is running stops where it is. The steps not yet run are left out, and the "
                             "report covers the steps that ran")
        self.halt.setEnabled(False)
        self.halt.hide()
        self.halt.clicked.connect(self.stop)
        self.open_report = QtWidgets.QPushButton("Open the report")
        self.open_report.clicked.connect(lambda: self.window_.do("report"))
        self.open_report.hide()
        self.go = QtWidgets.QPushButton("Measure")
        self.go.setStyleSheet(MAIN)
        self.go.clicked.connect(self.start)
        for b in (self.halt, self.open_report, self.go):
            row.addWidget(b)
        outer.addLayout(row)
        self._began = self._step_began = 0.0
        self._step = (None, None, None)
        self._tick = QtCore.QTimer(self)
        self._tick.setInterval(500)
        self._tick.timeout.connect(self._say_time)

        self.said.connect(self.log.appendPlainText)
        self.step.connect(self._on_step)
        self.sheet_made.connect(self._show_sheet)
        self.done.connect(self._finished)
        self.refresh()

    def _ruled(self, edit, px):
        """A length measured on the video, into its field, which is brought into view."""
        edit.setText(f"{px:.1f}")
        self.known_toggle.setChecked(True)
        self.body_area.ensureWidgetVisible(edit)
        edit.setFocus()

    def _say_known(self, *_):
        n = sum(1 for e in self.fields.values() if e.text().strip())
        self.known_toggle.setText("Provide additional information about this video (optional)" + (f" — {n} given" if n else ""))

    # -- what it will be given ---------------------------------------------------------------
    def refresh(self):
        """Say what the case will be made from: the link of the object, if there is one."""
        w, link = self.window_, self.window_.links.get(0)
        n_open = w.clip.n1 - w.clip.n0 + 1
        self.whole.setText(f"all {n_open} frames that are open, {w.clip.n0}–{w.clip.n1}")
        tracked = link is not None and bool(link.track)
        a, b = around(link.track, w.clip, self.pad_seconds) if tracked else (w.clip.n0, w.clip.n1)
        choice = tracked and (a, b) != (w.clip.n0, w.clip.n1)
        for x in (self.near, self.whole, self.frames_box):
            x.setVisible(choice)
        if choice:
            self.near.setText(f"frames {a}–{b}: the track, {min(link.track)}–{max(link.track)}, and {self.pad_seconds:g} "
                              f"seconds before and after it ({b - a + 1} frames)")
            if not (self.near.isChecked() or self.whole.isChecked()) or self._range_for != (a, b):
                self.near.setChecked(True)            # the object's rates come from the frames it is in
        else:
            self.whole.setChecked(True)
        self._range_for = (a, b)
        if tracked:
            self.what.setText(f"Works out how the object moved along the track followed from your marks (frames "
                              f"{min(link.track)}–{max(link.track)}), and writes a report. Your marks and the track are "
                              f"saved first, with everything else, in {Path(w.out).parent.resolve()}.")
            self.what.setToolTip(link.say)
            size = self.fields["size"]
            if not size.text():
                size.setPlaceholderText(f"{link.size:g} pixels, {'dark' if link.dark else 'bright'}: chosen from your marks")
        else:
            self.what.setText(f"There is no track of the object yet, so this will describe the video but measure nothing "
                              f"about an object. To measure the object, do steps 1 and 2 first (Find the object, Follow "
                              f"it), and come back. Everything is saved in {Path(w.out).parent.resolve()}.")
        self._say_cost()

    def frames(self):
        """(first, last) of what will be measured: round the track, or everything open."""
        w = self.window_
        return self._range_for if self.near.isChecked() and self._range_for else (w.clip.n0, w.clip.n1)

    def _say_cost(self, *_):
        if not hasattr(self, "cost"):                 # a radio button toggled while the panel is still being built
            return
        self.cost.setText(cost_text(*self.frames(), [n for n, b in self.slow.items() if b.isChecked()] + ["groups", "flicker"]))

    def known(self):
        """The form as run_case's keywords; an empty field is a thing not known. Raises
        ValueError naming the field that cannot be read."""
        out = {}
        for k in stages.KNOWN:
            text = self.fields[k.name].text().strip()
            if not text:
                continue
            try:
                out[k.name] = k.kind(text)
            except ValueError:
                raise ValueError(f"“{text}” is not a number ({k.label}).") from None
        if "names" in out:
            try:
                dict(p.split("=") for p in out["names"].split(","))
            except ValueError:
                raise ValueError("Give the names of the two background parts like this: striated=sea,isotropic=cloud tops") from None
        return out

    # -- running it ---------------------------------------------------------------------------
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running():
            return
        w = self.window_
        if w.linking():                               # a track still growing is not the track the report should cite
            complain(self, "The link is still running. Let it end, or stop it, and then measure.")
            return
        try:
            kw = self.known()
        except ValueError as ex:
            complain(self, str(ex))
            return
        w.finish(show_strip=False)                    # the marks and the link, on disk: the report cites those files
        link = w.links.get(0)
        marks = f"{w.out}_marks.json"
        if link is not None and link.track:
            kw.update(track=f"{w.out}_autotrack.csv", marks=marks, dark=link.dark)
            kw.setdefault("size", link.size)
        elif w.ms.marks.get(CLASSES[0]) and Path(marks).exists():
            kw.update(marks=marks)                    # marked but not linked: run_case links, as `run --marks` does
        skip = [n for n, b in self.slow.items() if not b.isChecked()]
        a, b = self.frames()
        clip = w.clip
        if (a, b) != (clip.n0, clip.n1):              # the same frames on disk, fewer of them: nothing is extracted
            clip = vf.Clip(w.ms.video, clip.dir, a, b)
        self._stop.clear()
        self._answered.clear()
        self.case, self.files, self.sheet_path = None, [], None
        self.log.clear()
        self.go.setEnabled(False)
        self.halt.setEnabled(True)
        for x in (self.halt, self.log_toggle):       # the bar and where it has got to are step 3's, on the right
            x.show()
        self.open_report.hide()
        self._began = self._step_began = time.monotonic()
        self._on_step(f"starting on frames {a}–{b}…", None, None)
        self._tick.start()

        def tell(signal):
            def emit(*a):
                try:
                    signal.emit(*a)
                except RuntimeError:                  # the panel went while a stage was under way: nobody to tell
                    pass
            return emit

        def job():
            try:
                case, _, files = stages.run_case(w.ms.video, out=str(Path(w.out).parent), clip=clip, skip=skip,
                                                 i_looked=self._ask, say=tell(self.said), progress=tell(self.step),
                                                 stop=self._stop.is_set, sheet=sheet_layout(clip), **kw)
                tell(self.done)((case, files))
            except BaseException as ex:               # a SystemExit too: whatever it is goes on the screen, not to a dead thread
                tell(self.done)(ex)
        self._thread = threading.Thread(target=job, daemon=True, name="mcdonald-measure")
        self._thread.start()
        # The form has done its work: step 3 on the right has the bar, and its button stops it; the menu's
        # Measure brings the panel back, with its details (Jacob, 2026-09-25). Put away, not closed.
        self.hide()
        self.window_.work_changed()
        self.window_.say_steps()

    def put_away(self):
        self.hide()
        self.window_.work_changed()

    def stop(self):
        self._stop.set()
        self.halt.setEnabled(False)
        self._on_step("Stopping. The step that is running ends at its next frame…", None, None)

    @QtCore.Slot(str, object, object)
    def _on_step(self, text, done, total):
        """A step has started, or got further. With a count the bar counts; without, it
        runs to and fro -- busy, and not pretending to know how far."""
        if text != self._step[0]:
            self._step_began = time.monotonic()
        self._step = (text, done, total)
        if total:
            self.bar.setRange(0, int(total))
            self.bar.setValue(int(done or 0))
        else:
            self.bar.setRange(0, 0)
        self._say_time()
        self.window_.say_steps()

    def _say_time(self):
        text, done, total = self._step
        if text is None:
            return
        now = time.monotonic()
        line = text
        if total:
            line += f" — {done} of {total}"
            eta = left(done, total, now - self._step_began)
            if eta is not None:
                line += f", about {clock(eta)} left in this step"
        self.now.setText(line)
        if self.running() or self._tick.isActive():
            self.elapsed.setText(f"{clock(now - self._began)} elapsed")
        self.window_.say_steps()

    def progress(self):
        """(fraction done or None, a line) for step 3's card, where the one bar for this step is
        (Jacob, 2026-09-25: one progress bar a step, on the right)."""
        text, done, total = self._step
        if self.sheet_path and not self._answered.is_set():
            return None, "Waiting for you: look at the track sheet, and answer its question."
        return (done / total if total else None), " · ".join(x for x in (self.now.text(), self.elapsed.text()) if x)

    def _ask(self, sheet):
        """On the measuring thread: put the sheet in front of the person, and wait."""
        self._answer = False
        self._answered.clear()
        try:
            self.sheet_made.emit(str(sheet))
        except RuntimeError:                          # the panel has gone: nobody looked
            return False
        self._answered.wait()
        return self._answer

    def answer_sheet(self, looked):
        """The person's answer under the sheet -- and what closing it, or the panel, gives: no."""
        self._answer = bool(looked)
        self._answered.set()
        if self.sheet is not None:
            sheet, self.sheet = self.sheet, None
            sheet.close()
        self.said.emit("the track sheet: " + ("you looked, and the track is on the object in every frame" if looked else
                                              "not checked, so the numbers for the object are not yet sure"))

    @QtCore.Slot(str)
    def _show_sheet(self, path):
        self.sheet_path = path
        self._step = ("waiting for you: look at the track sheet, and answer the question under it", None, None)
        self.bar.setRange(0, 1)                       # not busy: it is the person's turn, and the bar should not say otherwise
        self.bar.setValue(0)
        self._say_time()
        d = self.sheet = beside(self.window_)
        d.setWindowTitle(f"Check the track sheet — {self.window_.ms.tag}")
        lay = QtWidgets.QVBoxLayout(d)
        lay.addWidget(heading(ASK.split("\n", 1)[0]))
        pic, shown = QtWidgets.QLabel(), QtGui.QPixmap(path)
        if shown.isNull():                            # too large for a pixmap, or not written: say so, never an empty box
            pic.setText("The sheet could not be shown here. It is in the results folder (Measure → Open the results "
                        "folder). Open it there, and then answer.")
        else:
            pic.setPixmap(shown)
        area = QtWidgets.QScrollArea()
        area.setWidget(pic)
        lay.addWidget(area, 1)
        row = QtWidgets.QHBoxLayout()
        where = muted(path)
        where.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        row.addWidget(where, 1)
        yes = QtWidgets.QPushButton("Yes, on the object in every frame")
        yes.setStyleSheet(MAIN)
        no = QtWidgets.QPushButton("No, or I cannot tell")
        yes.clicked.connect(lambda: self.answer_sheet(True))
        no.clicked.connect(lambda: self.answer_sheet(False))
        row.addWidget(no)
        row.addWidget(yes)
        lay.addLayout(row)
        d.finished.connect(lambda *_: self._answered.is_set() or self.answer_sheet(False))
        d.resize(min(shown.width() + 60, 1980) if not shown.isNull() else 900, 900)
        d.show()

    @QtCore.Slot(object)
    def _finished(self, got):
        self.go.setEnabled(True)
        self.go.setText("Measure again")
        self.halt.setEnabled(False)
        self.halt.hide()
        self._tick.stop()
        took = clock(time.monotonic() - self._began)
        self.bar.setRange(0, 1)
        self.bar.setValue(0 if isinstance(got, BaseException) else 1)
        self.elapsed.setText(f"{took} in all")
        self._step = (None, None, None)
        if isinstance(got, BaseException):
            self.now.setText("it stopped")
            complain(self, f"Measuring stopped because something went wrong: {type(got).__name__}: {got}")
            return
        self.case, self.files = got
        self.now.setText("Stopped. The report covers the steps that ran." if self._stop.is_set() else "done")
        report = next((f for f in self.files if str(f).endswith("_case.md")), None)
        self.open_report.setVisible(bool(report and Path(report).exists()))
        self.window_.say_steps()
        if report and Path(report).exists() and not self.closed:     # not for a panel that was closed while it measured
            self.report = show_report(self.window_, report)

    def showEvent(self, e):
        self.closed = False
        super().showEvent(e)

    def closeEvent(self, e):
        self.closed = True                            # put away for Find is not closed: only this is
        self._stop.set()                              # the stage under way ends at its next item, on its own thread
        if not self._answered.is_set():
            self.answer_sheet(False)
        super().closeEvent(e)
        self.window_.work_changed()

    def wait_for_the_step(self, most=60.0):
        """Before the program ends: the measuring thread, told to stop, given up to `most` seconds to end
        the step under way and write the report of the steps that ran. Until 2026-09-23 nothing waited
        for it -- it was a daemon thread, and the window closing ended the program under it, part way
        through writing a file. The window keeps answering meanwhile. True if it ended."""
        t = getattr(self, "_thread", None)
        if t is None or not t.is_alive():
            return True
        self._stop.set()
        end = time.monotonic() + most
        while t.is_alive() and time.monotonic() < end:
            QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
            t.join(0.05)
        return not t.is_alive()


PICTURE_WIDTH = 820      # pixels: a picture in the report page is shown no wider than this, and clicked open whole


def fit_pictures(page, folder, width=PICTURE_WIDTH):
    """Every picture in the page shown at most `width` wide, its shape kept, and linked to its file. The
    track sheet is thousands of pixels across; shown at its own size it would be the whole page, to be
    scrolled sideways. The pictures were files behind "Open the folder" until 2026-09-23, which someone
    who cannot open a folder of pictures with confidence never saw. Returns how many there were."""
    doc, n = page.document(), 0
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            fmt = frag.charFormat()
            if fmt.isImageFormat():
                im = fmt.toImageFormat()
                file = Path(folder) / unquote(im.name())               # the report names it as a link, quoted
                size = QtGui.QImageReader(str(file)).size()
                if size.isValid() and size.width() > 0:
                    w = min(width, size.width())
                    im.setWidth(w)
                    im.setHeight(size.height() * w / size.width())
                    im.setAnchor(True)
                    im.setAnchorHref(QtCore.QUrl.fromLocalFile(str(file)).toString())
                    cur = QtGui.QTextCursor(doc)
                    cur.setPosition(frag.position())
                    cur.setPosition(frag.position() + frag.length(), QtGui.QTextCursor.MoveMode.KeepAnchor)
                    cur.setCharFormat(im)
                n += 1
            it += 1
        block = block.next()
    return n


def sheet_unconfirmed(report_md):
    """Does this report's case have a track sheet nobody has said they looked at?"""
    js = Path(str(report_md)[:-len("_case.md")] + "_case.json")
    try:
        import json
        v = json.loads(js.read_text()).get("stages", {}).get("verify")
    except (OSError, ValueError):
        return False
    return bool(v) and v.get("fields", {}).get("reviewed") is False


DETAILS = re.compile(r"<details><summary>(.*?)</summary>(.*?)</details>", re.S)


def render(page, report_md):
    """The report's Markdown on the page, set for reading: room round the text, headings that
    stand out, lines not packed tight, tables ruled lightly, the pictures fitted. A folded
    part (`<details>`, the marks frame by frame) is a link that opens and closes it."""
    opened = getattr(page, "opened", set())             # which of the folded parts are open, by their order
    count = iter(range(1000))

    def fold(m):
        i = next(count)
        return f"[{'▾' if i in opened else '▸'} {m.group(1)}](mcdonald:details/{i})\n" + (m.group(2) if i in opened else "")
    text = DETAILS.sub(fold, Path(report_md).read_text())
    page.setMarkdown(text)
    page.setWordWrapMode(QtGui.QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)     # a long path breaks too
    doc = page.document()
    doc.setDocumentMargin(28)
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
            ch.setFontPointSize(page.font().pointSizeF() * {1: 1.9, 2: 1.4, 3: 1.15}.get(level, 1.05))
            ch.setFontWeight(QtGui.QFont.Weight.Bold)
            if level == 2:
                ch.setForeground(QtGui.QColor(ACCENT))
            cur.mergeCharFormat(ch)
        else:
            fmt.setNonBreakableLines(False)       # a command in a code block wraps; it was the page's width, and a scrollbar
            if "\ufffc" not in block.text():      # not a picture's line: 135 % of a picture's height is a gap under it
                fmt.setLineHeight(135, QtGui.QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            fmt.setBottomMargin(max(fmt.bottomMargin(), 6))
            cur.setBlockFormat(fmt)
        block = block.next()
    it = doc.begin()                              # links in the icon's teal: Markdown import fixes them in the palette's blue
    while it.isValid():
        frags = it.begin()
        while not frags.atEnd():
            f = frags.fragment()
            if f.charFormat().isAnchor() and not f.charFormat().isImageFormat():
                cur = QtGui.QTextCursor(doc)
                cur.setPosition(f.position())
                cur.setPosition(f.position() + f.length(), QtGui.QTextCursor.MoveMode.KeepAnchor)
                ch = QtGui.QTextCharFormat()
                ch.setForeground(QtGui.QColor(ACCENT))
                cur.mergeCharFormat(ch)
            frags += 1
        it = it.next()
    for frame in doc.rootFrame().childFrames():
        if isinstance(frame, QtGui.QTextTable):
            tf = frame.format()
            tf.setBorder(1)
            tf.setBorderBrush(QtGui.QColor("#3a3a40"))
            tf.setBorderStyle(QtGui.QTextFrameFormat.BorderStyle.BorderStyle_Solid)
            tf.setCellPadding(6)
            tf.setCellSpacing(0)
            tf.setWidth(QtGui.QTextLength(QtGui.QTextLength.Type.PercentageLength, 100))    # its columns wrap, not the page
            frame.setFormat(tf)
    fit_pictures(page, Path(report_md).resolve().parent)


def _confirm(d, report_md):
    """The banner's button: the track sheet looked at afterwards (`stages.confirm_sheet`), and the page shown again."""
    try:
        stages.confirm_sheet(str(report_md)[:-len("_case.md")] + "_case.json", "looked at afterwards, and said so in the window")
    except (OSError, ValueError) as e:
        complain(d, f"The report could not be changed: {e}")
        return
    render(d.page, report_md)
    d.banner.setVisible(False)


def show_report(window, path):
    """A case report, to be read beside the window: the file `mcdonald run` writes, shown."""
    d = beside(window)
    d.setWindowTitle(f"Report — {Path(path).name}")
    lay = QtWidgets.QVBoxLayout(d)
    lay.setSpacing(8)
    top = QtWidgets.QHBoxLayout()
    names = QtWidgets.QVBoxLayout()
    names.setSpacing(0)
    names.addWidget(heading(f"Report — {window.ms.tag.upper()}", 1.4))
    where = muted(escape(str(Path(path).resolve())))
    where.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    names.addWidget(where)
    top.addLayout(names, 1)
    folder = QtWidgets.QPushButton("Open the folder")
    folder.setToolTip("open the results folder: the report, the sheets, the tables of numbers and the pictures")
    folder.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(Path(path).resolve().parent))))
    top.addWidget(folder, 0, QtCore.Qt.AlignmentFlag.AlignTop)
    lay.addLayout(top)
    # a track sheet nobody has said they looked at: said at the top, where it cannot be missed, with its answer beside it
    banner = QtWidgets.QFrame()
    banner.setObjectName("banner")
    banner.setStyleSheet("QFrame#banner { background: #3a2f16; border: 1px solid #8a6a1f; border-radius: 6px; }")
    bl = QtWidgets.QHBoxLayout(banner)
    bl.setContentsMargins(12, 8, 8, 8)
    note = QtWidgets.QLabel("The numbers for the object are not yet sure: nobody has said that the track sheet shows the "
                            "object in every frame.")
    note.setWordWrap(True)
    bl.addWidget(note, 1)
    looked = QtWidgets.QPushButton("I have looked at the track sheet now")
    looked.setToolTip("the track sheet shows the object ringed on every frame. If you have looked at it since, and the ring is "
                      "on the object in every frame, say so here: the report stops calling the numbers for the object not yet "
                      "sure. Nothing is measured again")
    looked.setStyleSheet(MAIN)
    looked.clicked.connect(lambda: _confirm(d, path))
    bl.addWidget(looked)
    banner.setVisible(sheet_unconfirmed(path))
    lay.addWidget(banner)
    page = QtWidgets.QTextBrowser()
    page.setOpenLinks(False)                      # a link, or a picture clicked, opens outside the page, which stays the report
    def clicked(url):
        if url.scheme() == "mcdonald":                # the folded part: open or close it where it is
            at = page.verticalScrollBar().value()
            i = int(url.path().rsplit("/", 1)[-1] or 0)
            page.opened = getattr(page, "opened", set()) ^ {i}
            render(page, path)
            page.verticalScrollBar().setValue(at)
        else:
            QtGui.QDesktopServices.openUrl(url)
    page.anchorClicked.connect(clicked)
    page.setSearchPaths([str(Path(path).resolve().parent)])      # the report names its pictures; they sit beside it
    page.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    pal = page.palette()
    pal.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor(ACCENT))    # the default blue is not read on a dark page
    page.setPalette(pal)
    render(page, path)
    lay.addWidget(page, 1)
    d.page, d.looked, d.banner = page, looked, banner
    d.resize(960, 920)
    d.show()
    return d
