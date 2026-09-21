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
from html import escape
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from . import stages
from .mark import CLASSES
from .mark_qt import beside, complain

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


def cost_text(clip, chosen):
    """What the slow stages will take on this clip, said before they start."""
    pairs = max(clip.n1 - clip.n0 - 4, 0)
    L = []
    if "layers" in chosen:
        L.append(f"layers: {pairs} frame pairs at about a second each, so about {max(1, round(pairs * 1.7 / 60))} min")
    if "integrity" in chosen:
        L.append("integrity: as long again, and more (about 15 min on a 30 s clip)")
    return "; ".join(L) if L else "Without the two slow stages this takes under a minute."


class MeasurePanel(QtWidgets.QDialog):
    """The form, the button, and what is said while the case is made."""
    said = QtCore.Signal(str)                     # a line for the person, from the measuring thread
    step = QtCore.Signal(str)                     # the name of a long step as it starts
    sheet_made = QtCore.Signal(str)               # the track sheet is on disk: show it, and ask
    done = QtCore.Signal(object)                  # (case, files), or the exception that ended it

    def __init__(self, window):
        super().__init__(window)
        self.window_, self.case, self.files, self.sheet, self.report = window, None, [], None, None
        self.sheet_path, self._answer, self._answered = None, False, threading.Event()
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
        self.halt = QtWidgets.QPushButton("Stop after this stage")
        self.halt.setToolTip("the stage under way finishes; the rest are left out, and the report says which ran")
        self.halt.setEnabled(False)
        self.halt.clicked.connect(self.stop)
        self.now = QtWidgets.QLabel()
        row.addWidget(self.go)
        row.addWidget(self.halt)
        row.addWidget(self.now, 1)
        lay.addLayout(row)

        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont))
        lay.addWidget(self.log, 1)

        self.said.connect(self.log.appendPlainText)
        self.step.connect(self.now.setText)
        self.sheet_made.connect(self._show_sheet)
        self.done.connect(self._finished)
        self.resize(820, 760)
        self.refresh()

    # -- what it will be given ---------------------------------------------------------------
    def refresh(self):
        """Say what the case will be made from: the link of the object, if there is one."""
        w, link = self.window_, self.window_.links.get(0)
        if link is not None and link.track:
            self.what.setText(f"Every stage of a case, on frames {w.clip.n0}–{w.clip.n1} of {Path(str(w.ms.video)).name}, "
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

    def _say_cost(self, *_):
        self.cost.setText(cost_text(self.window_.clip, [n for n, b in self.slow.items() if b.isChecked()]))

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
        self._stop.clear()
        self._answered.clear()
        self.case, self.files, self.sheet_path = None, [], None
        self.log.clear()
        self.go.setEnabled(False)
        self.halt.setEnabled(True)
        self.now.setText("starting…")

        def tell(signal):
            def emit(*a):
                try:
                    signal.emit(*a)
                except RuntimeError:                  # the panel went while a stage was under way: nobody to tell
                    pass
            return emit

        def job():
            try:
                case, _, files = stages.run_case(w.ms.video, out=str(Path(w.out).parent), clip=w.clip, skip=skip,
                                                 i_looked=self._ask, say=tell(self.said), progress=tell(self.step),
                                                 stop=self._stop.is_set, sheet=sheet_layout(w.clip), **kw)
                tell(self.done)((case, files))
            except BaseException as ex:               # a SystemExit too: whatever it is goes on the screen, not to a dead thread
                tell(self.done)(ex)
        self._thread = threading.Thread(target=job, daemon=True, name="mcdonald-measure")
        self._thread.start()

    def stop(self):
        self._stop.set()
        self.now.setText("stopping after this stage…")

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
        self.now.setText("waiting for you: look at the track sheet")
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
        if isinstance(got, BaseException):
            self.now.setText("it stopped")
            complain(self, f"The measurement stopped: {type(got).__name__}: {got}")
            return
        self.case, self.files = got
        self.now.setText("done")
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
