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
import threading
import time
from html import escape
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from . import forensics as vf
from . import stages
from .mark import CLASSES
from .mark_qt import beside, complain
from .progress import clock, left

ASK = ("Is the circle on the object in every frame?\n"
       "Every number measured from this track assumes it is. A track that sits on a cloud feature for seven "
       "frames gives a clean, wrong rate.")


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
        L.append(f"layers: {pairs} frame pairs at about a second each, so about {_about(pairs * 1.7)}")
    if "integrity" in chosen:
        L.append(f"integrity: more again, about {_about(pairs * 2.6 + 90)}")
    return "; ".join(L) if L else "Without the two slow stages this takes under a minute."


def _about(seconds):
    return f"{max(1, round(seconds / 60))} min" if seconds < 5400 else f"{seconds / 3600:.1f} hours"


class MeasurePanel(QtWidgets.QDialog):
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
        self._stop, self._thread = threading.Event(), None
        self.setWindowTitle(f"measure — {window.ms.tag}")
        lay = QtWidgets.QVBoxLayout(self)

        self.what = QtWidgets.QLabel()
        self.what.setWordWrap(True)
        lay.addWidget(self.what)

        box = QtWidgets.QGroupBox("What you know about this clip. Leave empty what you do not: the report says what is "
                                  "missing, and what would close it.")
        form = QtWidgets.QFormLayout(box)
        self.fields = {}
        for k in stages.KNOWN:
            edit = QtWidgets.QLineEdit()
            edit.setToolTip(k.help)
            edit.setPlaceholderText(k.help if k.kind is str else k.unit)
            if k.kind is float:
                v = QtGui.QDoubleValidator(self)
                v.setLocale(QtCore.QLocale.c())       # a point is a point: what the command line reads
                edit.setValidator(v)
            self.fields[k.name] = edit
            form.addRow(k.label + (f"  [{k.unit}]" if k.unit else ""), edit)
        lay.addWidget(box)

        self.near = QtWidgets.QRadioButton()
        self.whole = QtWidgets.QRadioButton()
        for b in (self.near, self.whole):
            b.toggled.connect(self._say_cost)
            lay.addWidget(b)

        self.slow = {}
        for name, why in stages.SLOW.items():
            self.slow[name] = QtWidgets.QCheckBox(f"{name}: {why}")
            self.slow[name].setChecked(True)
            self.slow[name].toggled.connect(self._say_cost)
            lay.addWidget(self.slow[name])
        self.cost = QtWidgets.QLabel()
        self.cost.setWordWrap(True)
        lay.addWidget(self.cost)

        row = QtWidgets.QHBoxLayout()
        self.go = QtWidgets.QPushButton("Measure")
        self.go.setDefault(True)
        self.go.clicked.connect(self.start)
        self.halt = QtWidgets.QPushButton("Stop")
        self.halt.setToolTip("the step under way ends where it is; the stages not yet run are left out, and the report "
                             "is written of the ones that ran")
        self.halt.setEnabled(False)
        self.halt.clicked.connect(self.stop)
        self.elapsed = QtWidgets.QLabel()
        self.elapsed.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self.go)
        row.addWidget(self.halt)
        row.addWidget(self.elapsed, 1)
        lay.addLayout(row)
        # Is it working, or has it hung? The bar is the answer: it counts where the step can count
        # (frame pairs, tiles), runs to and fro where it cannot, and the clock beside it never stops.
        self.bar = QtWidgets.QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 1)
        self.bar.setValue(0)
        lay.addWidget(self.bar)
        self.now = QtWidgets.QLabel()
        self.now.setWordWrap(True)
        lay.addWidget(self.now)
        self._began = self._step_began = 0.0
        self._step = (None, None, None)
        self._tick = QtCore.QTimer(self)
        self._tick.setInterval(500)
        self._tick.timeout.connect(self._say_time)

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont))
        lay.addWidget(self.log, 1)

        self.said.connect(self.log.appendPlainText)
        self.step.connect(self._on_step)
        self.sheet_made.connect(self._show_sheet)
        self.done.connect(self._finished)
        self.resize(820, 860)
        self.refresh()

    # -- what it will be given ---------------------------------------------------------------
    def refresh(self):
        """Say what the case will be made from: the link of the object, if there is one."""
        w, link = self.window_, self.window_.links.get(0)
        n_open = w.clip.n1 - w.clip.n0 + 1
        self.whole.setText(f"all {n_open} frames that are open, {w.clip.n0}–{w.clip.n1}")
        tracked = link is not None and bool(link.track)
        a, b = around(link.track, w.clip, self.pad_seconds) if tracked else (w.clip.n0, w.clip.n1)
        self.near.setVisible(tracked and (a, b) != (w.clip.n0, w.clip.n1))
        self.whole.setVisible(self.near.isVisibleTo(self))
        if self.near.isVisibleTo(self):
            self.near.setText(f"frames {a}–{b}: the track, {min(link.track)}–{max(link.track)}, and {self.pad_seconds:g} s "
                              f"either side ({b - a + 1} frames)")
            if not (self.near.isChecked() or self.whole.isChecked()) or self._range_for != (a, b):
                self.near.setChecked(True)            # the object's rates come from the frames it is in
        else:
            self.whole.setChecked(True)
        self._range_for = (a, b)
        if tracked:
            self.what.setText(f"Every stage of a case of {Path(str(w.ms.video)).name}, "
                              f"with the track linked from your marks ({link.say}). The marks and the track are saved "
                              f"first. Everything is written to {Path(w.out).parent.resolve()}.")
            size = self.fields["size"]
            if not size.text():
                size.setPlaceholderText(f"{link.size:g} px, {'dark' if link.dark else 'bright'}: what the marks chose")
        else:
            key = "l"
            self.what.setText(f"There is no track of the object yet, so this will describe the clip and measure nothing "
                              f"of an object. To measure the object: mark it on two frames, press {key} to link, look "
                              f"at the strip, and come back. Everything is written to {Path(w.out).parent.resolve()}.")
        self._say_cost()

    def frames(self):
        """(first, last) of what will be measured: round the track, or everything open."""
        w = self.window_
        return self._range_for if self.near.isChecked() and self._range_for else (w.clip.n0, w.clip.n1)

    def _say_cost(self, *_):
        if not hasattr(self, "cost"):                 # a radio button toggled while the panel is still being built
            return
        self.cost.setText(cost_text(*self.frames(), [n for n, b in self.slow.items() if b.isChecked()]))

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
                raise ValueError("The layers' names are given as striated=sea,isotropic=cloud tops.") from None
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

    def stop(self):
        self._stop.set()
        self.halt.setEnabled(False)
        self._on_step("stopping: the step under way ends at its next item…", None, None)

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
            self.elapsed.setText(f"{clock(now - self._began)} since it started")

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
        self.said.emit("the track sheet: " + ("examined, and the track is on the object in every frame" if looked else
                                              "not confirmed, so the object measurements are provisional"))

    @QtCore.Slot(str)
    def _show_sheet(self, path):
        self.sheet_path = path
        self._step = ("waiting for you: look at the track sheet, and answer the question under it", None, None)
        self.bar.setRange(0, 1)                       # not busy: it is the person's turn, and the bar should not say otherwise
        self.bar.setValue(0)
        self._say_time()
        d = self.sheet = beside(self.window_)
        d.setWindowTitle("the track sheet — look at it before believing anything measured from the track")
        lay = QtWidgets.QVBoxLayout(d)
        pic, shown = QtWidgets.QLabel(), QtGui.QPixmap(path)
        if shown.isNull():                            # too large for a pixmap, or not written: say so, never an empty box
            pic.setText("The sheet could not be shown here. It is in the case folder (Measure -> Open the case folder): "
                        "open it there, and then answer.")
        else:
            pic.setPixmap(shown)
        area = QtWidgets.QScrollArea()
        area.setWidget(pic)
        lay.addWidget(area, 1)
        lay.addWidget(QtWidgets.QLabel(ASK + "\n" + path))
        row = QtWidgets.QHBoxLayout()
        yes = QtWidgets.QPushButton("Yes: it is on the object in every frame")
        no = QtWidgets.QPushButton("No, or I cannot tell")
        yes.clicked.connect(lambda: self.answer_sheet(True))
        no.clicked.connect(lambda: self.answer_sheet(False))
        row.addStretch(1)
        row.addWidget(no)
        row.addWidget(yes)
        lay.addLayout(row)
        d.finished.connect(lambda *_: self._answered.is_set() or self.answer_sheet(False))
        d.resize(min(shown.width() + 60, 1980) if not shown.isNull() else 900, 900)
        d.show()

    @QtCore.Slot(object)
    def _finished(self, got):
        self.go.setEnabled(True)
        self.halt.setEnabled(False)
        self._tick.stop()
        took = clock(time.monotonic() - self._began)
        self.bar.setRange(0, 1)
        self.bar.setValue(0 if isinstance(got, BaseException) else 1)
        self.elapsed.setText(f"{took} in all")
        self._step = (None, None, None)
        if isinstance(got, BaseException):
            self.now.setText("it stopped")
            complain(self, f"The measurement stopped: {type(got).__name__}: {got}")
            return
        self.case, self.files = got
        self.now.setText("stopped: the report is of the stages that ran" if self._stop.is_set() else "done")
        report = next((f for f in self.files if str(f).endswith("_case.md")), None)
        if report and Path(report).exists():
            self.report = show_report(self.window_, report)

    def closeEvent(self, e):
        self._stop.set()                              # the stage under way finishes on its own thread; nothing waits for it
        if not self._answered.is_set():
            self.answer_sheet(False)
        super().closeEvent(e)


def show_report(window, path):
    """A case report, to be read beside the window: the file `mcdonald run` writes, shown."""
    d = beside(window)
    d.setWindowTitle(f"case report — {Path(path).name}")
    lay = QtWidgets.QVBoxLayout(d)
    page = QtWidgets.QTextBrowser()
    page.setOpenExternalLinks(True)
    page.setMarkdown(Path(path).read_text())
    lay.addWidget(page, 1)
    row = QtWidgets.QHBoxLayout()
    where = QtWidgets.QLabel(f"<span>{escape(str(Path(path).resolve()))}</span>")
    where.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    folder = QtWidgets.QPushButton("Open the folder")
    folder.setToolTip("the case directory, in the file manager: the report, the sheets, the CSVs and the figures")
    folder.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(Path(path).resolve().parent))))
    row.addWidget(where, 1)
    row.addWidget(folder)
    lay.addLayout(row)
    d.page = page
    d.resize(900, 900)
    d.show()
    return d
