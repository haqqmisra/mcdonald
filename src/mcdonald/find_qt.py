"""Find the object, from the window: `mcdonald.propose`, for someone to say yes or no to.

Track -> Find the object looks for what moves against the background and shows what
it finds as it goes: a row for each thing, best first, with a strip of the clip's own
pixels along it and a line saying what it is like. "This is it" takes one -- marks
are placed along it, recorded as proposed and never as a hand's, and the link starts
from them, as it would from clicks. "Show" goes to it in the main window, with its
path drawn, to look before deciding. None of them is also an answer: close the panel
and click the object, which is what a click was always for.

Nothing is decided here. The order is the detector's guess at what is most like an
object; which thing is the object, or whether any is, is the person's to say, and
the files record that the suggestion was the detector's and the yes was theirs.

`mcdonald look --propose` is the same search from the command line, and draws the
same strips.
"""
import threading
import time

from PySide6 import QtCore, QtGui, QtWidgets

from . import propose
from .mark_qt import ACCENT, MASKS, MUTED, complain, qimage_from_rgb
from .progress import Stopped, clock, left

NEAR = 300                  # frames either side of the one in view, where everything open would take long
STRIP_HEIGHT = 120          # px: each row's pictures, small enough that six fit across the panel under the video
KEEP = 30                   # things kept from a search: the rows shown at first are the best of them, the rest are behind "Show more"
LONG = 900                  # "long": at 0.2 s a frame, three minutes


def close_button(panel, go=None):
    """The ✕ at the right of a panel's heading: it closes the panel, as closing its window did (or does `go`)."""
    b = QtWidgets.QToolButton()
    b.setText("✕")
    b.setAutoRaise(True)
    b.setToolTip("close this")
    b.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
    b.clicked.connect(go or panel.close)
    return b


class FindPanel(QtWidgets.QFrame):
    found = QtCore.Signal(int, int, object)       # frames done, frames in all, [Proposal] best first
    step = QtCore.Signal(str, object, object)
    done = QtCore.Signal(object)                  # None, or the exception that ended it

    def __init__(self, window):
        super().__init__(window)                          # a part of the window, under the video (Jacob, 2026-09-25)
        self.window_, self.proposals, self.rows = window, [], []
        self._all, self._more, self._strips = [], False, {}
        self._stop, self._thread, self._began, self._step = threading.Event(), None, 0.0, (None, None, None)
        self.setWindowTitle(f"Find the object — {window.ms.tag}")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(8)
        head = QtWidgets.QLabel("Which one is the object?")
        font = head.font()
        font.setPointSizeF(font.pointSizeF() * 1.3)
        font.setBold(True)
        head.setFont(font)
        top = QtWidgets.QHBoxLayout()
        top.addWidget(head, 1)
        top.addWidget(close_button(self))
        lay.addLayout(top)
        self.what = QtWidgets.QLabel("The computer lists things that move against the background, the most likely first. "
                                     "Press “This is it” on the object. If none of them is the object, close "
                                     "this (✕) and use “Mark the object by hand” on the right.")
        self.what.setWordWrap(True)
        self.what.setStyleSheet(f"color: {MUTED};")
        lay.addWidget(self.what)
        self.near, self.whole = QtWidgets.QRadioButton(), QtWidgets.QRadioButton()
        for b in (self.near, self.whole):
            lay.addWidget(b)
        row = QtWidgets.QHBoxLayout()
        self.go = QtWidgets.QPushButton("Look again")
        self.go.setToolTip("look again, for instance after choosing other frames above")
        self.go.clicked.connect(self.start)
        self.halt = QtWidgets.QPushButton("Stop")
        self.halt.setToolTip("stop looking; what has been found so far stays on the list")
        self.halt.setEnabled(False)
        self.halt.clicked.connect(self.stop)
        self.elapsed = QtWidgets.QLabel()
        self.elapsed.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        for w_ in (self.go, self.halt):
            w_.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            row.addWidget(w_)
        self.elapsed.setStyleSheet(f"color: {MUTED};")
        row.addWidget(self.elapsed, 1)
        row.addStretch(1)
        lay.addLayout(row)
        self.bar = QtWidgets.QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 1)
        lay.addWidget(self.bar)
        self.halt.hide()                              # Stop is for while it looks; the bar and the time are step 1's,
        self.bar.hide()                               # in the window's side panel (Jacob, 2026-09-25)
        self.elapsed.hide()
        self.now = QtWidgets.QLabel()
        self.now.setWordWrap(True)
        lay.addWidget(self.now)
        self.list = QtWidgets.QVBoxLayout()
        self.more = QtWidgets.QPushButton()
        self.more.setToolTip("show the other things the computer found, which it thinks less likely. In a hard video the object "
                             "may be one of these")
        self.more.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.more.clicked.connect(self.show_more)
        self.more.hide()
        self.list.addWidget(self.more)
        self.list.addStretch(1)
        inner = QtWidgets.QWidget()
        inner.setLayout(self.list)
        area = QtWidgets.QScrollArea()
        area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setWidgetResizable(True)
        area.setWidget(inner)
        lay.addWidget(area, 1)
        self._tick = QtCore.QTimer(self)
        self._tick.setInterval(500)
        self._tick.timeout.connect(self._say_time)
        self.found.connect(self._on_found)
        self.step.connect(self._on_step)
        self.done.connect(self._finished)
        self.refresh()

    # -- which frames ---------------------------------------------------------------------------
    def refresh(self):
        clip, n = self.window_.clip, self.window_.n
        total = clip.n1 - clip.n0 + 1
        a, b = max(clip.n0, n - NEAR), min(clip.n1, n + NEAR)
        self._near = (a, b)
        self.whole.setText(f"all {total} frames that are open, {clip.n0}–{clip.n1}: about {_about(total * 0.2 + 25)}")
        self.near.setText(f"frames {a}–{b}, around the frame you are on: about {_about((b - a + 1) * 0.2 + 25)}")
        long = total > LONG
        self.near.setVisible(long)
        self.whole.setVisible(long)
        if not (self.near.isChecked() or self.whole.isChecked()):
            (self.near if long else self.whole).setChecked(True)

    def frames(self):
        clip = self.window_.clip
        return self._near if self.near.isChecked() and self.near.isVisibleTo(self) else (clip.n0, clip.n1)

    # -- looking ---------------------------------------------------------------------------------
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running():
            return
        w = self.window_
        a, b = self.frames()
        if b - a + 1 < 2 * propose.K + 3:             # each frame is compared with the ones K before and K after it
            self.now.setText(f"This part of the video is too short to look in: it has {b - a + 1} frames. The computer compares each "
                             f"frame with the frames {propose.K} before and {propose.K} after it, so it needs at least "
                             f"{2 * propose.K + 3}, and it does best with a second or two before the object comes and after it "
                             "goes. Use File → Open a video to open a longer part, or click the object on two frames yourself.")
            return
        self._stop.clear()
        self._all, self._more, self._strips = [], False, {}
        self._show([])
        self.go.setEnabled(False)
        self.halt.setEnabled(True)
        self.halt.show()
        self.go.hide()
        self.now.hide()
        self._began = time.monotonic()
        self._on_step(MASKS if w._masks is None else f"starting on frames {a}–{b}…", None, None)
        self._tick.start()

        def tell(signal):
            def emit(*args):
                try:
                    signal.emit(*args)
                except RuntimeError:                  # the panel went while it was looking
                    pass
            return emit

        def job():
            try:
                for done, total, props in propose.search(w.clip, w._static_masks(), a, b, progress=tell(self.step),
                                                         stop=self._stop.is_set, keep=KEEP):
                    tell(self.found)(done, total, props)
                tell(self.done)(None)
            except Stopped:
                tell(self.done)(None)
            except BaseException as ex:               # on the screen, not to a dead thread
                tell(self.done)(ex)
        self._thread = threading.Thread(target=job, daemon=True, name="mcdonald-find")
        self._thread.start()
        w.say_steps()

    def stop(self):
        self._stop.set()
        self.halt.setEnabled(False)

    @QtCore.Slot(str, object, object)
    def _on_step(self, text, done, total):
        self._step = (text, done, total)
        self.bar.setRange(0, int(total) if total else 0)
        if total:
            self.bar.setValue(int(done or 0))
        self._say_time()

    def _say_time(self):
        text, done, total = self._step
        if text is None:
            return
        now = time.monotonic()
        eta = left(done, total, now - self._began) if total else None
        self.now.setText(text + (f" — {done} of {total}" if total else "") + (f", about {clock(eta)} left" if eta is not None else ""))
        self.elapsed.setText(f"{clock(now - self._began)} elapsed")
        self.window_.say_steps()

    @QtCore.Slot(int, int, object)
    def _on_found(self, done, total, props):
        self._all = list(props)
        self._show(self._all if self._more else propose.shortlist(props))
        self.window_.say_steps()

    def show_more(self):
        """The rest of what was found. The rows shown first are the best few; where nothing
        stands out -- PR113, where everything is weak -- the object can be further down."""
        self._more = True
        self._show(self._all)

    @QtCore.Slot(object)
    def _finished(self, ex):
        self._tick.stop()
        self.go.setEnabled(True)
        self.halt.setEnabled(False)
        self.halt.hide()
        self.go.show()
        self.now.show()
        self.bar.setRange(0, 1)
        self.bar.setValue(1)
        self.window_.say_steps()
        self._step = (None, None, None)
        self.elapsed.setText(f"{clock(time.monotonic() - self._began)} in all")
        if isinstance(ex, BaseException):
            self.now.setText("it stopped")
            complain(self, f"Looking for the object stopped because something went wrong: {type(ex).__name__}: {ex}")
            return
        n = len(self.proposals)
        self.now.setText(("Stopped. " if self._stop.is_set() else "") +
                         (f"{n} thing{'s' if n != 1 else ''} found moving against the background." if n else
                          "Nothing here moves against the background in a line for three frames or more. Close this "
                          "window and use “Mark the object by hand” in the main window."))

    def progress(self):
        """(fraction done or None, a line) for step 1's card, where the one bar for this step is
        (Jacob, 2026-09-25: one progress bar a step, on the right)."""
        text, done, total = self._step
        return (done / total if total else None), " · ".join(x for x in (self.now.text(), self.elapsed.text()) if x)

    # -- the list --------------------------------------------------------------------------------
    def _show(self, props):
        self.proposals = list(props)
        for r in self.rows:
            self.list.removeWidget(r)
            r.deleteLater()
        self.rows = []
        for i, p in enumerate(self.proposals, 1):
            r = QtWidgets.QFrame()
            r.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
            v = QtWidgets.QVBoxLayout(r)
            top = QtWidgets.QHBoxLayout()
            text = QtWidgets.QLabel(f"<b>{i}.</b> <span style='background: #2c2c31; border-radius: 3px;'>&nbsp;{p.strength()}"
                                    f"&nbsp;</span> &nbsp;<span style='color: {MUTED}'>{p.describe()}</span>")
            text.setWordWrap(True)
            show = QtWidgets.QPushButton("Show in video")
            show.setToolTip("go to it in the main window, with its path drawn as a dashed line")
            take = QtWidgets.QPushButton("This is it")
            take.setStyleSheet(f"QPushButton {{ background: {ACCENT}; color: #0b1a1c; font-weight: bold; padding: 5px 14px; "
                               "border-radius: 5px; border: none; } QPushButton:hover { background: #7fe3d8; }")
            take.setToolTip("put marks along its path, saved as proposed and never as placed by hand, and start linking from them")
            for b in (show, take):
                b.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
            show.clicked.connect(lambda _=False, k=i - 1: self.show_in_window(k))
            take.clicked.connect(lambda _=False, k=i - 1: self.accept_proposal(k))
            top.addWidget(text, 1)
            top.addWidget(show)
            top.addWidget(take)
            v.addLayout(top)
            key = (p.frames[0], p.frames[-1], len(p.track), round(p.track[p.frames[0]][0]), round(p.track[p.frames[0]][1]))
            if key not in self._strips:               # a strip is six frames read from disk: made once for a thing, not at every refresh
                self._strips[key] = propose.strip(self.window_.clip, p)
            pix, shown = self._strips[key]
            pic = QtWidgets.QLabel()
            pic.setPixmap(QtGui.QPixmap.fromImage(qimage_from_rgb(pix)).scaledToHeight(
                STRIP_HEIGHT, QtCore.Qt.TransformationMode.SmoothTransformation))      # it fits under the video
            pic.setToolTip("frames " + ", ".join(map(str, shown)))
            v.addWidget(pic)
            r.take, r.show_, r.pic = take, show, pic
            self.list.insertWidget(self.list.count() - 2, r)
            self.rows.append(r)
        hidden = len(self._all) - len(self.proposals)
        self.more.setText(f"Show {hidden} more that the computer thinks less likely")
        self.more.setVisible(hidden > 0)

    def show_in_window(self, k):
        p = self.proposals[k]
        self.window_.show_proposal(p)

    def accept_proposal(self, k):
        """The person's yes. The marks are the detector's positions and were its suggestion,
        and say so; the link then runs from them as it does from clicks."""
        if self.running():
            self.stop()
        p, w = self.proposals[k], self.window_
        how = (f"proposed: {k + 1} of {len(self.proposals)} things found moving against the background in frames "
               f"{self.frames()[0]}–{self.frames()[1]} ({p.describe()}); accepted at the window by a person looking at its strip")
        w.take_proposal(p, how)
        self.close()

    def closeEvent(self, e):
        self._stop.set()
        self.window_.show_proposal(None)
        super().closeEvent(e)
        self.window_.work_changed()


def _about(seconds):
    m = max(1, round(seconds / 60))
    return f"{m} minute{'s' if m != 1 else ''}" if seconds >= 50 else "less than a minute"
