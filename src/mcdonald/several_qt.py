"""More than one object in a video, from the window: a report each, one after another.

Find lists what moves against the background. Where a video has more than one object --
Galileo flyer 1 has four -- the person ticks each of them on Find's list and presses
"Follow and measure the ticked ones". Every ticked thing gets a folder of its own under the
video's results folder, with its marks in it (recorded as proposed, as "This is it" records
them), and `several.run_each` follows and measures them in turn: what `mcdonald run VIDEO
--each DIR` does, with a row for each object in place of the log.

Nobody is asked about a track while it runs, so that it can be left running. Each report
says its numbers are not yet sure, and its page has the button that says the track sheet
has been looked at; the list, here and in `<tag>_objects.md`, says which have been.

The window's own marks, track and report are not touched. An object here is a folder, and
"Open in the window" brings one in for the work only a hand can do: a track that went
wrong, a thing that could not be followed.
"""
import threading
import time
from html import escape
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from . import several
from .find_qt import close_button
from .mark_qt import MUTED, Page, ReadingView, complain, qimage_from_rgb
from .measure_qt import MAIN, heading, muted, render, sheet_layout, show_report
from .progress import clock

PICTURE_HEIGHT = 64         # px: a row's strip of pictures, smaller than in Find's list: it is a reminder here, not the question
WAITING, FOLLOWED = "Waiting for its turn.", "followed on {n} frames, {a}–{b}"


class SeveralPanel(QtWidgets.QFrame):
    said = QtCore.Signal(str)                     # a line for the person, from the measuring thread
    step = QtCore.Signal(str, object, object)     # a long step: its name, and how far it has got of how many, if it can count
    told = QtCore.Signal(object)                  # an object has started, or ended
    done = QtCore.Signal(object)                  # the objects, or the exception that ended it

    def __init__(self, window):
        super().__init__(window)
        self.window_ = w = window
        folder = Path(w.out).parent                   # the video's own results folder, also when the window has gone into an object's
        self.base = folder.parent if several.NAME.match(folder.name) else folder
        self.rows, self.pictures, self.lines = {}, {}, []
        self._stop, self._thread, self._began, self._step, self._now = threading.Event(), None, 0.0, (None, None, None), None
        self._busy = False                            # from Start until the panel has heard that the queue ended
        self.closed, self.pages = False, []
        self.setWindowTitle(f"More than one object — {w.ms.tag}")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(8)
        top = QtWidgets.QHBoxLayout()
        top.addWidget(heading("More than one object"), 1)
        top.addWidget(close_button(self, self.put_away))
        lay.addLayout(top)
        self.what = muted("Each object you ticked is followed and measured in turn, and gets its own report in a folder of its "
                          "own. You can leave it running. Nobody is asked about a track along the way, so each report says its "
                          "numbers are not yet sure: open each report when it is ready, look at its track sheet, and say so there.")
        lay.addWidget(self.what)
        row = QtWidgets.QHBoxLayout()
        self.halt = QtWidgets.QPushButton("Stop")
        self.halt.setToolTip("stop after the step under way. The report of that object says which steps ran, and the objects "
                             "not yet started are left as they are, to be measured later")
        self.halt.clicked.connect(self.stop)
        self.go = QtWidgets.QPushButton("Measure the rest")
        self.go.setToolTip("follow and measure the objects that have no finished report yet")
        self.go.setStyleSheet(MAIN)
        self.go.clicked.connect(self.start)
        self.list_button = QtWidgets.QPushButton("Open the list")
        self.list_button.setToolTip("one page that lists every object of this video: what it was chosen as, how far it was "
                                    "followed, the last line of its report, and whether its track sheet has been looked at")
        self.list_button.clicked.connect(self.show_list)
        self.elapsed = muted()
        self.elapsed.setWordWrap(False)
        for b in (self.halt, self.go, self.list_button):
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            row.addWidget(b)
        row.addWidget(self.elapsed)
        row.addStretch(1)
        lay.addLayout(row)
        self.now = QtWidgets.QLabel()
        self.now.setWordWrap(True)
        lay.addWidget(self.now)
        self.list = QtWidgets.QVBoxLayout()
        self.list.addStretch(1)
        inner = QtWidgets.QWidget()
        inner.setLayout(self.list)
        area = self.area = QtWidgets.QScrollArea()
        area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setWidgetResizable(True)
        area.setWidget(inner)
        lay.addWidget(area, 1)
        self._tick = QtCore.QTimer(self)
        self._tick.setInterval(500)
        self._tick.timeout.connect(self._say_time)
        self.said.connect(self.lines.append)
        self.step.connect(self._on_step)
        self.told.connect(self._on_told)
        self.done.connect(self._finished)
        self.refresh()

    # -- the rows --------------------------------------------------------------------------------
    def _row(self, k):
        """The row of object k, made when first needed: its pictures, what it is, how it stands, and its two buttons."""
        if k in self.rows:
            return self.rows[k]
        r = QtWidgets.QFrame()
        r.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        h = QtWidgets.QHBoxLayout(r)
        r.pic, got = None, self.pictures.get(k)
        if got is not None:                           # Find's strip of it, small: an object of an earlier day has none
            r.pic = QtWidgets.QLabel()
            r.pic.setPixmap(QtGui.QPixmap.fromImage(qimage_from_rgb(got)).scaledToHeight(
                PICTURE_HEIGHT, QtCore.Qt.TransformationMode.SmoothTransformation))
            h.addWidget(r.pic)
        v = QtWidgets.QVBoxLayout()
        r.state = QtWidgets.QLabel()
        r.state.setWordWrap(True)
        r.state.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        r.desc = muted()
        v.addWidget(r.state)
        v.addWidget(r.desc)
        h.addLayout(v, 1)
        r.report = QtWidgets.QPushButton("Open its report")
        r.report.setToolTip("the report of this object. Its track sheet is in it: look at it there, and say so at the top")
        r.report.clicked.connect(lambda _=False, k=k: self.open_report(k))
        r.bring = QtWidgets.QPushButton("Open in the window")
        r.bring.setToolTip("bring this object's marks into the main window, and follow it there, where you can watch the "
                           "track, put it right by hand, and measure it again. Use this if its track went wrong or it could "
                           "not be followed")
        r.bring.clicked.connect(lambda _=False, k=k: self.open_in_window(k))
        for b in (r.report, r.bring):
            b.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            h.addWidget(b)
        self.list.insertWidget(self.list.count() - 1, r)
        self.rows[k] = r
        return r

    def refresh(self):
        """The rows, from what is in the folders: also the objects of an earlier day."""
        measuring = self._now if self.running() else None
        for t in several.things(self.base):
            d = several.row(t)
            r = self._row(t.k)
            r.thing = t
            r.desc.setText(escape(_chosen(d)))
            f = d["followed"]
            if t.k == measuring:
                pass                                  # its line is the step under way
            elif d["error"] and not d["measured"]:
                self._state(t.k, "It could not be measured.", d["error"])
            elif not d["measured"]:
                self._state(t.k, WAITING if self.running() else "Not measured yet.")
            elif d["stopped"]:
                self._state(t.k, "Stopped before it was finished.", "Its report covers the steps that ran.")
            elif not f:
                self._state(t.k, "It could not be followed, so nothing about it was measured.",
                            "Open it in the window to mark it by hand.")
            else:
                self._state(t.k, "Done: " + FOLLOWED.format(n=f["frames"], a=f["first"], b=f["last"]) + ".",
                            "You have looked at its track sheet." if d["track_sheet_looked_at"] else
                            "Its track sheet has not been looked at yet.")
            r.report.setVisible(bool(d["report"]))
            r.bring.setVisible(t.k != measuring)      # not the one under way: the window would follow it where the queue measures it
        waiting = self.waiting()
        self.go.setVisible(bool(waiting) and not self.running())
        self.go.setText(f"Measure the rest ({len(waiting)})" if any(several.measured(r.thing) for r in self.rows.values())
                        else f"Follow and measure ({len(waiting)})")
        self.halt.setVisible(self.running())
        self.list_button.setEnabled(any(self.base.glob(f"*{several.LIST}.md")))

    def _state(self, k, bold, rest=""):
        self.rows[k].state.setText(f"<b>Object {k}.</b> {escape(bold)}" + (f" <span style='color: {MUTED}'>{escape(rest)}</span>" if rest else ""))

    def waiting(self):
        """The objects that have no report measured to its end from their marks."""
        return [r.thing for r in self.rows.values() if not several.measured(r.thing)]

    def wanted_height(self):
        """What the panel needs of the window's height: its words and buttons, and up to four rows."""
        rows = list(self.rows.values())[:4]
        return (self.sizeHint().height() - self.area.sizeHint().height()
                + sum(r.sizeHint().height() + self.list.spacing() for r in rows) + 12)

    # -- taking them from Find's list ------------------------------------------------------------
    def take(self, items):
        """The ticked rows of Find's list: [(row, of how many, Proposal, how its marks are recorded, its strip)].
        Each is given a folder with its marks, and the queue starts."""
        w = self.window_
        try:
            for _, _, p, how, strip in items:
                t = several.place(w.clip, w.ms.tag, self.base, p.seeds(), how, video=w.ms.video, seen=(p.frames[0], p.frames[-1]))
                self.pictures[t.k] = strip
        except OSError as ex:
            complain(self, f"The objects could not be saved: {ex}\n\nUse File → Save to a different folder to choose another place.")
            return
        self.refresh()
        self.window_.fit_work(self)
        self.start()

    # -- following and measuring -----------------------------------------------------------------
    def running(self):
        """Is the queue under way, as the panel knows it: from its start until the panel has heard that it ended
        (the thread is still alive for an instant when its last word arrives, and has gone before some are heard)."""
        return self._busy

    def start(self):
        if self.running():
            return
        w = self.window_
        from . import measure_qt
        if w.measure_panel is None:                   # Measure's form holds what is known of the video and which slow checks
            w.measure_panel = measure_qt.MeasurePanel(w)      # to make: the same for every object of it
            w.measure_panel.hide()
        mp = w.measure_panel
        try:
            kw = mp.known()
        except ValueError as ex:
            complain(self, str(ex))
            return
        skip = [n for n, b in mp.slow.items() if not b.isChecked()]
        self._stop.clear()
        self.lines.clear()
        self._began, self._now = time.monotonic(), None
        self._on_step("Starting…", None, None)
        self._tick.start()

        def tell(signal):
            def emit(*a):
                try:
                    signal.emit(*a)
                except RuntimeError:                  # the panel went while an object was being measured: nobody to tell
                    pass
            return emit

        def job():
            try:
                got = several.run_each(w.ms.video, self.base, clip=w.clip, masks=w._masks, say=tell(self.said),
                                       progress=tell(self.step), stop=self._stop.is_set, told=tell(self.told),
                                       sheet=sheet_layout, skip=skip, **kw)
                tell(self.done)(got)
            except BaseException as ex:               # whatever it is goes on the screen, not to a dead thread
                tell(self.done)(ex)
        self._busy = True
        self.halt.setEnabled(True)
        self._thread = threading.Thread(target=job, daemon=True, name="mcdonald-several")
        self._thread.start()
        self.refresh()
        w.say_steps()

    def stop(self):
        self._stop.set()
        self.halt.setEnabled(False)
        self._on_step("Stopping…", None, None)

    def put_away(self):
        self.hide()
        self.window_.work_changed()

    @QtCore.Slot(object)
    def _on_told(self, t):
        if t.state == "measuring":
            self._now = t.k
            self._state(t.k, "Following it and measuring it…")
        else:
            self._now = None
        self.refresh()
        self.window_.say_steps()

    @QtCore.Slot(str, object, object)
    def _on_step(self, text, done, total):
        self._step = (text, done, total)
        self._say_time()

    def _say_time(self):
        text, done, total = self._step
        if text is None:
            return
        now = time.monotonic()
        line = text[:1].upper() + text[1:] + (f" — {done} of {total}" if total else "")
        self.now.setText(line)                        # a step's count, not the queue's: how long is left is not said
        self.elapsed.setText(f"{clock(now - self._began)} elapsed")
        if self._now in self.rows and " · " in text:
            self._state(self._now, "Now: " + line.split(" · ", 1)[1] + ".")
        self.window_.say_steps()

    def progress(self):
        """(fraction done or None, a line) for step 3's card while the queue runs."""
        text, done, total = self._step
        return (done / total if total else None), " · ".join(x for x in (self.now.text(), self.elapsed.text()) if x)

    @QtCore.Slot(object)
    def _finished(self, got):
        self._tick.stop()
        self._busy, self._step, self._now = False, (None, None, None), None
        self.elapsed.setText(f"{clock(time.monotonic() - self._began)} in all")
        if isinstance(got, BaseException):
            self.now.setText("It stopped.")
            self.refresh()
            self.window_.say_steps()
            complain(self, f"Measuring the objects stopped because something went wrong: {type(got).__name__}: {got}")
            return
        self.refresh()
        n, ready = len(self.rows), sum(1 for r in self.rows.values() if r.thing.report is not None)
        self.now.setText(("Stopped. " if self._stop.is_set() else "") +
                         f"{ready} of {n} report{'s' if n != 1 else ''} {'are' if ready != 1 else 'is'} ready. Open each one, look at "
                         "its track sheet, and say at its top if the ring is on the object in every frame.")
        self.window_.say_steps()

    # -- what is there to open -------------------------------------------------------------------
    def open_report(self, k):
        t = self.rows[k].thing
        if t.report is None:
            return None
        d = show_report(self.window_, str(t.report))
        d.looked.clicked.connect(lambda *_: QtCore.QTimer.singleShot(0, self.refresh))      # said there: its line here follows
        self.pages.append(d)
        return d

    def open_in_window(self, k):
        self.window_.open_object(self.rows[k].thing)

    def show_list(self):
        page = next(iter(sorted(self.base.glob(f"*{several.LIST}.md"))), None)
        if page is None:
            return None
        several.index(self.base)                      # as the folders stand now
        d = show_list(self.window_, page, self.open_report_at)
        self.pages.append(d)
        return d

    def open_report_at(self, path):
        k = next((k for k, r in self.rows.items() if r.thing.report is not None and r.thing.report.resolve() == Path(path).resolve()), None)
        return self.open_report(k) if k is not None else show_report(self.window_, str(path))

    def showEvent(self, e):
        self.closed = False
        self.refresh()
        super().showEvent(e)

    def closeEvent(self, e):
        self.closed = True
        self._stop.set()                              # the step under way ends at its next item, on its own thread
        super().closeEvent(e)
        self.window_.work_changed()

    def wait_for_the_step(self, most=60.0):
        """Before the program ends: the queue, told to stop, given up to `most` seconds to end the step under way
        and write that object's report of the steps that ran. The window keeps answering meanwhile. True if it ended."""
        t = self._thread
        if t is None or not t.is_alive():
            return True
        self._stop.set()
        end = time.monotonic() + most
        while t.is_alive() and time.monotonic() < end:
            QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
            t.join(0.05)
        return not t.is_alive()


def _chosen(d):
    """What an object was chosen as, short enough for a row: Find's own line where it came from Find's list."""
    how = d["chosen_as"]
    if how.startswith("proposed: ") and "(" in how:
        head, rest = how[len("proposed: "):].split(" (", 1)
        return f"Row {head.split(' things')[0]} of what Find showed: " + rest.rsplit(");", 1)[0].split("; moves")[0]
    return how if how == "marked by hand" else how[:160]


def show_list(window, page, open_report):
    """The list of a video's objects (`<tag>_objects.md`), on a page of the window. A report named on
    it opens as a report does here; anything else opens outside."""
    d = Page(window, f"The objects of this video — {window.ms.tag.upper()}")
    d.setWindowTitle(f"The objects of this video — {Path(page).name}")
    lay = d.body
    where = muted(escape(str(Path(page).resolve())))
    where.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    lay.addWidget(where)
    view = ReadingView()
    view.setOpenLinks(False)

    def clicked(url):
        target = (Path(page).resolve().parent / url.toString()).resolve() if url.isRelative() else Path(url.toLocalFile())
        if str(target).endswith("_case.md") and target.exists():
            open_report(target)
        elif url.scheme() == "mcdonald":              # a folded part: there is none on this page
            return
        else:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(target)) if target.exists() else url)
    view.anchorClicked.connect(clicked)
    view.setSearchPaths([str(Path(page).resolve().parent)])
    render(view, str(page))
    lay.addLayout(view.column(), 1)
    d.page = view
    d.take_focus = view.setFocus
    window.show_page(d)
    return d
