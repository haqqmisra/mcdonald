"""Does the marking window do what its keys say? Every handler, under every
interactive matplotlib backend this machine can open.

    python3 tests/test_gui.py                 # every backend that imports
    python3 tests/test_gui.py QtAgg TkAgg     # just these
    python3 tests/test_gui.py --on-screen     # on the desktop rather than Xvfb

`MarkSet` is covered headless in test_reduction.py. This is the other half:
the `Marker` window. Synthetic MouseEvent and KeyEvent objects go in through
`fig.canvas.callbacks`, the registry real events arrive through, so every
handler connected to the canvas runs — matplotlib's own included, which is how
this suite found that 's' also opened matplotlib's save-figure dialog and 'l'
put the image on a log axis. Calling `Marker.on_key` directly would have
missed both.

No video. The clip is synthetic, a compact source on a known path, so two
clicks on it must give back the velocity it was built with.

Each backend is driven in its own subprocess under a timeout: a GUI toolkit
that cannot reach a display may hang rather than raise (GTK4Agg did, here),
and two toolkits do not share a process. Where Xvfb exists the windows are
hosted off screen, so nothing flashes on the desktop, a modal dialog cannot
wait on a person, and a host with no display at all runs the same checks. A
backend that cannot open a window is skipped, with the reason. A hang once the
window is up is a failure: from here, that is what a modal dialog looks like.
"""
import contextlib
import io
import json
import math
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import forensics as vf  # noqa: E402
from mcdonald import mark  # noqa: E402

BACKENDS = ["QtAgg", "GTK3Agg", "GTK4Agg", "TkAgg", "WxAgg", "MacOSX"]      # the matplotlib window's
WINDOWS = ["PySide6"] + BACKENDS                                           # and the Qt window
UP = "window up"              # the child says this once a window has opened
SAVED = "saved: "             # and this, with the marks file it wrote, at the end
CANNOT_OPEN = 77              # and exits with this when one cannot
FAIL, SKIP = [], []
ON_SCREEN = False
WANTED = []
# Every deadline times this: a shared CI machine (GitHub's macOS runner) is slower than a desk.
PATIENCE = float(os.environ.get("MCDONALD_TEST_PATIENCE", "1"))


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}", flush=True)
    if not cond:
        FAIL.append(label)
    return cond


# ---------------------------------------------------------------- the clip
class SyntheticClip:
    """What Marker asks of a Clip, with a compact source on a known path.

    Frame numbers are absolute and do not start at 1, as in a real window of
    a real clip, and fps is the NTSC rational rather than 30."""
    W, H = 640, 360
    n0, n1 = 401, 440
    fps = 30000 / 1001
    P0, V = (560.0, 90.0), (-7.25, 3.5)          # position at n0, px/frame
    P2, V2 = (100.0, 320.0), (10.5, -0.5)        # a second, fainter object, never within 70 px of the first
    RED = (40, 300)                              # one red pixel, for the half-pixel check

    def __init__(self):
        rng = np.random.default_rng(113)
        self._yx = np.mgrid[:self.H, :self.W]
        yy, xx = self._yx
        self._sky = 60 + 25 * np.sin(xx / 47.0) * np.cos(yy / 31.0) + rng.normal(0, 3, (self.H, self.W))
        self._frames = {}

    def truth(self, n):
        k = n - self.n0
        return self.P0[0] + self.V[0] * k, self.P0[1] + self.V[1] * k

    def truth2(self, n):
        k = n - self.n0
        return self.P2[0] + self.V2[0] * k, self.P2[1] + self.V2[1] * k

    def grey(self, n):
        return self.rgb(n).mean(2)

    def __getstate__(self):                      # it goes to the linker's processes; the frames can be made again there
        return {**self.__dict__, "_frames": {}}

    def rgb(self, n):
        if n not in self._frames:
            yy, xx = self._yx
            g = self._sky
            for (x, y), amp in ((self.truth(n), 170), (self.truth2(n), 110)):
                g = g + amp * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 2.5 ** 2))
            f = np.repeat(np.clip(g, 0, 255)[..., None], 3, axis=2).astype(np.float32)
            f[self.RED[1], self.RED[0]] = (255, 0, 0)
            self._frames[n] = f
        return self._frames[n]


# ---------------------------------------------------------------- the rigs
# One list of checks, two windows. A rig is what the checks need from a front
# end -- press this key, click at these image coordinates, tell me what is on
# screen -- and each sends real toolkit events to do it: through
# fig.canvas.callbacks for matplotlib, through QApplication.sendEvent for Qt.
# Neither calls a handler. Pixel positions are each toolkit's own (matplotlib's
# origin is bottom left, Qt's top left); the checks never mix them.
class MplRig:
    name, px_tol = "matplotlib", 1e-6            # px_tol: how exactly a view change can be placed, screen px
    window = "mpl"                               # which rows of actions.ACTIONS it has

    def __init__(self, clip, ms, out):
        self.m = mark.Marker(clip, ms, out)

    def describe(self):
        return f"{type(self.m.fig.canvas).__module__}.{type(self.m.fig.canvas).__name__}"

    def key(self, k):
        """One key press, with the pointer over the middle of the image -- where it
        is when someone is marking, and where matplotlib's own bindings would act."""
        from matplotlib.backend_bases import KeyEvent
        c, box = self.m.fig.canvas, self.m.ax.bbox
        k = k.lower()                            # the table says "Ctrl+S" and "Backspace"; matplotlib reports them lower case
        c.callbacks.process("key_press_event", KeyEvent("key_press_event", c, k, box.x0 + box.width / 2,
                                                        box.y0 + box.height / 2))

    def to_px(self, xy):
        self.m.fig.canvas.draw()                 # the transform is final only once the aspect is applied
        return np.asarray(self.m.ax.transData.transform(xy), float)

    def mouse(self, kind, px, button=None, step=0):
        from matplotlib.backend_bases import MouseEvent
        c = self.m.fig.canvas
        c.draw()
        name = {"press": "button_press_event", "release": "button_release_event",
                "move": "motion_notify_event", "scroll": "scroll_event"}[kind]
        c.callbacks.process(name, MouseEvent(name, c, px[0], px[1], button=button, step=step))

    def outside_px(self):
        return np.array([1.0, 1.0])

    def status(self):
        return self.m.ax.get_title(loc="left")

    def drawn(self):
        return [tuple(a.get_xydata()[0]) for a in self.m.overlay]

    def shows(self, n):
        return np.array_equal(np.asarray(self.m.im.get_array()), self.m.clip.rgb(n).astype(np.uint8))

    def view(self):
        (x0, x1), (yb, yt) = self.m.ax.get_xlim(), self.m.ax.get_ylim()
        return x0, x1, yt, yb

    def screen_rgb(self, xy):
        px = self.to_px(xy)
        buf = np.asarray(self.m.fig.canvas.buffer_rgba())
        return tuple(int(v) for v in buf[buf.shape[0] - 1 - int(px[1]), int(px[0]), :3])

    def settle(self, ms=0):
        pass

    def is_open(self):
        import matplotlib.pyplot as plt
        return plt.fignum_exists(self.m.fig.number)

    def close(self):
        import matplotlib.pyplot as plt
        plt.close(self.m.fig)

    def after_save(self):
        pass

    def own_checks(self):
        """What only this window can get wrong."""
        m = self.m
        # matplotlib binds keys of its own to every figure. 's' is its save-figure
        # dialog, 'l' and 'k' put the image on log axes, 'g' draws a grid, and
        # backspace walks its view history -- all keys this window uses or sits beside
        theirs = m.fig.canvas.manager.key_press_handler_id
        if not check(theirs not in m.fig.canvas.callbacks.callbacks.get("key_press_event", {}),
                     "matplotlib's default key bindings are disconnected"):
            # carry on without them, or the 's' further down blocks on a dialog until the timeout
            m.fig.canvas.mpl_disconnect(theirs)
            return
        for k in ("l", "k", "g"):
            self.key(k)
        check(m.ax.get_yscale() == "linear" and m.ax.get_xscale() == "linear",
              "so a stray 'l' or 'k' cannot put the image on a log axis",
              f"x {m.ax.get_xscale()}, y {m.ax.get_yscale()}")
        tb = m.fig.canvas.toolbar
        if tb is not None:
            # with the toolbar's zoom or pan armed, a click belongs to the toolbar. If it
            # also placed a mark, zooming in to look would silently move the object
            before = m.ms.count()
            tb.zoom()
            click(self, m.clip.truth(m.n))
            tb.zoom()
            check(m.ms.count() == before, "a click made while the toolbar's zoom tool is armed is not a mark")


class QtRig:
    name, px_tol = "PySide6", 1.0                # a QGraphicsView scrolls in whole screen pixels
    window = "qt"

    def __init__(self, clip, ms, out):
        from mcdonald import mark_qt
        self.m = mark_qt.QtMarker(clip, ms, out)
        self.m.show()
        self.m.set_advanced(True)                     # the checks drive the steps one at a time; the one button has its own driver
        self._held = None
        self.settle(50)

    def describe(self):
        import PySide6
        from PySide6 import QtCore, QtGui
        return f"PySide6 {PySide6.__version__}, Qt {QtCore.qVersion()}, platform {QtGui.QGuiApplication.platformName()}"

    def settle(self, ms=0):
        # Not QTest.qWait: it holds the GIL for its whole wait, and every worker thread -- the decoder, the
        # link, Find, Measure -- starves under it (a 30 fps player measured at 8 under qWait, 2026-09-26)
        end = time.monotonic() + ms / 1000
        while True:
            self.m.app.processEvents()
            if time.monotonic() >= end:
                break
            time.sleep(0.003)

    def wait_for(self, cond, seconds):
        """Keep the event loop turning until cond() or the deadline; says which."""
        end = time.monotonic() + seconds * PATIENCE
        while not cond() and time.monotonic() < end:
            self.m.app.processEvents()
            time.sleep(0.005)
        return bool(cond())

    def active(self):
        """Would a key pressed now reach the window? It, or a tool window of its, is the active one."""
        from PySide6.QtCore import Qt
        w = self.m.app.activeWindow()
        return w is self.m or (w is not None and w.parentWidget() is self.m and w.windowType() == Qt.WindowType.Tool)

    def key(self, k, ctrl=False, shift=False):
        """One key, by the route a real one takes: the shortcut map, then the widget with
        the focus. Every key this window has is a QAction's shortcut, and a QKeyEvent sent
        straight to a widget never meets the map -- so the keys are only live in the active
        window, as they are for a person. An X server with no window manager activates
        nothing by itself, so the rig asks.

        A synthetic key has no keyboard layout behind it: '<' must arrive as '<', where a
        real one arrives as shift+',' and Qt works out the rest."""
        from PySide6 import QtGui, QtTest, QtWidgets
        if not self.active():
            self.m.activateWindow()
            if not self.wait_for(self.active, 10):          # a slow shared VM (GitHub's Mac) took over 3 s once, and lost the key
                print(f"  (the window is not active after 10 s: the key {k!r} may not reach it)")
        combo = QtGui.QKeySequence(("Ctrl+" if ctrl else "") + ("Shift+" if shift else "") + ("Space" if k == " " else k))[0]
        QtTest.QTest.keyClick(QtWidgets.QApplication.focusWidget() or self.m.view, combo.key(), combo.keyboardModifiers())
        self.settle()

    def to_px(self, xy):
        p = self.m.view.to_view(float(xy[0]), float(xy[1]))
        return np.array([p.x(), p.y()])

    def mouse(self, kind, px, button=None, step=0, widget=None, shift=False):
        from PySide6 import QtCore, QtGui, QtWidgets
        from PySide6.QtCore import Qt
        w = widget or self.m.view.viewport()
        pos = QtCore.QPointF(float(px[0]), float(px[1]))
        glob = QtCore.QPointF(w.mapToGlobal(pos.toPoint()))
        B = {None: Qt.MouseButton.NoButton, 1: Qt.MouseButton.LeftButton, 2: Qt.MouseButton.MiddleButton,
             3: Qt.MouseButton.RightButton}
        none = Qt.KeyboardModifier.ShiftModifier if shift else Qt.KeyboardModifier.NoModifier
        if kind == "scroll":
            ev = QtGui.QWheelEvent(pos, glob, QtCore.QPoint(0, 0), QtCore.QPoint(0, 120 * step),
                                   Qt.MouseButton.NoButton, none, Qt.ScrollPhase.NoScrollPhase, False)
        elif kind == "move":
            ev = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseMove, pos, glob, Qt.MouseButton.NoButton,
                                   B[self._held], none)
        else:
            press = kind == "press"
            self._held = button if press else None
            ev = QtGui.QMouseEvent(QtCore.QEvent.Type.MouseButtonPress if press else QtCore.QEvent.Type.MouseButtonRelease,
                                   pos, glob, B[button], B[button] if press else Qt.MouseButton.NoButton, none)
        QtWidgets.QApplication.sendEvent(w, ev)
        self.settle()

    def outside_px(self):
        c, vp = self.m.clip, self.m.view.viewport()
        for xy in ((-6, c.H / 2), (c.W / 2, -6)):          # fitted, the frame leaves a margin on one axis
            px = self.to_px(xy)
            if 0 <= px[0] < vp.width() and 0 <= px[1] < vp.height():
                return px
        raise AssertionError("the frame fills the viewport; nowhere to click outside it")

    def status(self):
        return self.m.status.text()

    def drawn(self):
        return [item.xy for item in self.m.crosses]

    def shows(self, n):
        """The frame's pixels are what the view shows -- given a moment, on a slow machine, for the draw."""
        from PySide6 import QtGui
        want = self.m.clip.rgb(n).astype(np.uint8)

        def same():
            img = self.m.view.pix.pixmap().toImage().convertToFormat(QtGui.QImage.Format.Format_RGB888)
            a = np.frombuffer(img.constBits(), np.uint8).reshape(img.height(), img.bytesPerLine())
            a = a[:, :3 * img.width()].reshape(img.height(), img.width(), 3)
            return a.shape == want.shape and np.array_equal(a, want)
        return same() or self.wait_for(same, 2)

    def view(self):
        return self.m.view.visible()

    def screen_rgb(self, xy):
        self.settle()
        img = self.m.view.viewport().grab().toImage()
        px = self.to_px(xy) * img.devicePixelRatio()
        c = img.pixelColor(int(px[0]), int(px[1]))
        return c.red(), c.green(), c.blue()

    def is_open(self):
        return self.m.isVisible()

    def close(self):
        self.m.unsaved_answer = lambda: "discard"
        self.m.close()
        self.settle()

    def own_checks(self):
        pass

    def after_save(self):
        auto, m = Path(f"{self.m.out}_autotrack.csv"), self.m
        check(auto.exists() and Path(f"{m.out}_autotrack_strip.png").exists(),
              "and the automatic track, with its strip")
        if auto.exists():
            head = [ln for ln in auto.read_text(encoding="utf-8").splitlines() if ln.startswith("#")]
            check(vf.read_track(auto) == {n: (round(x, 2), round(y, 2)) for n, (x, y) in m.link.track.items()},
                  "which reads back through the package's own reader", f"{len(m.link.track)} frames")
            check(any("source_candidates(size=" in ln and "marks: " in ln for ln in head) and any("hand mark" in ln for ln in head)
                  and any("disputed frames" in ln for ln in head),
                  "and says how it was made, how far it sits from the hand marks, and which frames are in dispute")
        d = self.m.saved_strip
        check(d is not None and d.isVisible(), "and the contact strip is put in front of whoever placed the marks")
        with contextlib.redirect_stdout(io.StringIO()):
            self.key("s")
        check(self.m.saved_strip.isVisible() and not d.isVisible(), "once: saving again replaces it")


def click(rig, xy=None, px=None, button=1):
    px = rig.to_px(xy) if px is None else np.asarray(px, float)
    rig.mouse("press", px, button=button)
    rig.mouse("release", px, button=button)
    return px


# ---------------------------------------------------------------- the checks both windows must pass
def drive_the_window(rig):
    print("\nthe window")
    m = rig.m
    check(m.n == m.clip.n0 and rig.shows(m.clip.n0), "opens on the first frame of the window", f"n={m.n}")
    check(f"frame {m.clip.n0} of {m.clip.n1}" in rig.status() and "marking: object" in rig.status(),
          "and says which frame and which class", repr(rig.status()[:40]))
    if rig.window == "qt":                        # the audit of 2026-09-26: what a modern desktop program does
        room = m.screen().availableGeometry()
        check(m.width() <= max(room.width(), m.minimumSizeHint().width()) and m.height() <= room.height(),
              "the window is no larger than the screen it opens on", f"{m.width()}x{m.height()} on {room.width()}x{room.height()}")
        check(m.dock.titleBarWidget() is not None, "the panel of steps is a panel, with no docked tool window's title bar")
        check(m.loupe.pixmap() is not None and not m.loupe.pixmap().isNull() and "mouse pointer" in m.cursor_label.text(),
              "before the mouse has been over the video, the close-up says what it is for, not an empty black square")
        check(m.note.parentWidget() is m.view and m.note.isHidden(), "a note for the person goes over the foot of the video; there is none yet")
        m.note.setText("a note, said once")
        rig.settle()
        check(m.note.isVisible() and m.note.y() + m.note.height() <= m.view.height() and m.note.text() == "a note, said once",
              "said, it shows there, at the foot", f"y {m.note.y()} h {m.note.height()} in {m.view.height()}")
        m.note.setText("")
        check(m.note.isHidden(), "and an empty note is no note")
    rig.own_checks()


def drive_stepping(rig):
    print("\nframes")
    m, key = rig.m, rig.key
    n0, n1 = m.clip.n0, m.clip.n1
    key(",")
    check(m.n == n0, "cannot step back past the start of the window")
    key(".")
    check(m.n == n0 + 1 and rig.shows(n0 + 1), "'.' is the next frame, and its pixels are on screen")
    key(">")
    check(m.n == n0 + 11 and rig.shows(n0 + 11), "'>' is ten on")
    key("<")
    key(",")
    check(m.n == n0 and rig.shows(n0), "'<' and ',' come back")
    key("right")
    key("right")
    key("left")
    check(m.n == n0 + 1, "the arrow keys step too")
    for _ in range(6):
        key(">")
    check(m.n == n1 and rig.shows(n1), "and cannot run off the end", f"n={m.n}")
    check(f"frame {n1} of {n1}" in rig.status(), "the status follows")


def drive_two_clicks(rig):
    """The point of the tool: two clicks on the object give its velocity."""
    print("\ntwo clicks")
    m = rig.m
    c, ms = m.clip, m.ms
    a, b = c.n0 + 7, c.n0 + 10
    m.goto(a)
    click(rig, c.truth(a))
    got = ms.marks.get("object", {}).get(a)
    check(got is not None and np.allclose(got, c.truth(a), atol=1e-6),
          "a click lands where it was aimed, through the view's transform", f"{got} for {c.truth(a)}")
    check(len(rig.drawn()) == 1 and np.allclose(rig.drawn()[0], c.truth(a), atol=1e-6),
          "and is drawn back at that position")
    m.goto(b)
    check(len(rig.drawn()) == 0, "a mark shows only on its own frame")
    click(rig, c.truth(b))
    v = ms.velocity()
    check(v is not None and np.allclose(v, c.V, atol=1e-6),
          "two clicks recover the velocity the source was built with",
          f"({v[0]:+.3f}, {v[1]:+.3f}) for ({c.V[0]:+.3f}, {c.V[1]:+.3f})" if v else "None")
    check(ms.seed() == (a, *ms.marks["object"][a]), "and the seed is the first of them")
    check("2 marks" in rig.status() and "pixels each frame" in rig.status(), "the status reports both")

    before = ms.count()
    click(rig, px=rig.outside_px())
    check(ms.count() == before, "a click outside the image places nothing")
    click(rig, c.truth(b), button=3)
    check(ms.count() == before, "nor does a right click")
    x, y = c.truth(b)
    click(rig, (x + 2.0, y - 1.0))
    check(ms.count() == before and np.allclose(ms.marks["object"][b], (x + 2.0, y - 1.0), atol=1e-6),
          "a second click on a frame moves the mark rather than adding one")
    click(rig, c.truth(b))


def drive_classes(rig):
    print("\nclasses")
    m = rig.m
    c, ms = m.clip, m.ms
    v, n = ms.velocity(), ms.count()
    rig.key("3")
    check(mark.CLASSES[m.cls] == "boresight" and "marking: boresight" in rig.status(),
          "'3' marks the boresight, and the status says so")
    click(rig, (c.W / 2, c.H / 2))
    check(ms.marks.get("boresight", {}).get(m.n) is not None and ms.count() == n + 1,
          "the click goes to that class")
    check(ms.velocity() == v, "and leaves the object's velocity alone")
    check(len(rig.drawn()) == 2, "both classes are drawn on the frame")
    for k in ("0", "7", "9"):
        rig.key(k)
    check(mark.CLASSES[m.cls] == "boresight", "digits with no class behind them are ignored")
    rig.key("backspace")
    check("boresight" not in ms.to_dict()["classes"] and ms.velocity() == v,
          "backspace deletes this class's mark on this frame, and only that")
    rig.key("1")
    check(mark.CLASSES[m.cls] == "object", "'1' is the object again")


def drive_zoom_and_pan(rig):
    print("\nzoom and pan")
    m, tol = rig.m, rig.px_tol
    c = m.clip
    home = rig.view()
    at = np.array([300.0, 200.0])

    px = rig.to_px(at)
    rig.mouse("scroll", px, step=1)
    span = rig.view()[1] - rig.view()[0]
    check(np.isclose(span, 0.8 * (home[1] - home[0])), "scrolling up zooms in", f"span x{span / (home[1] - home[0]):.2f}")
    check(np.allclose(rig.to_px(at), px, atol=tol), "about the cursor: the pixel under it stays under it",
          f"moved {np.abs(rig.to_px(at) - px).max():.2g} screen px")
    n, want = m.n, (c.truth(m.n)[0] + 1.5, c.truth(m.n)[1] + 1.5)
    click(rig, want)
    check(np.allclose(m.ms.marks["object"][n], want, atol=1e-6), "a click in a zoomed view still lands where it was aimed")
    click(rig, c.truth(n))

    # a drag in several motion events, as a real one arrives. The image has to
    # follow the cursor through all of them, not just the first
    before = m.ms.count()
    p0 = rig.to_px(at)
    rig.mouse("press", p0, button=2)
    for step in ((15, 10), (40, 25), (64, -32)):
        rig.mouse("move", p0 + step)
    moved = rig.to_px(at) - p0
    check(np.allclose(moved, (64, -32), atol=tol), "a middle-button drag carries the image with the cursor",
          f"moved ({moved[0]:+.1f}, {moved[1]:+.1f}) px for a drag of (+64.0, -32.0)")
    rig.mouse("release", p0 + (64, -32), button=2)
    held = rig.view()
    rig.mouse("move", p0)
    check(rig.view() == held, "and lets go on release")
    check(m.ms.count() == before, "a drag places no mark")

    rig.mouse("scroll", rig.to_px(at), step=-1)
    span = rig.view()[1] - rig.view()[0]
    check(np.isclose(span, home[1] - home[0]), "scrolling down zooms back out")
    rig.key("r")
    check(np.allclose(rig.view(), home, atol=1e-6), "'r' restores the view the window opened with",
          f"{tuple(round(float(v), 2) for v in rig.view())}")


def drive_pixels_are_where_the_coordinates_say(rig):
    """The half-pixel question, asked of the rendered window rather than of the code.

    The package's convention is numpy's: pixel [y, x] is centred on (x, y). A
    toolkit that puts pixel (0, 0) over [0, 1) instead is half a pixel out on
    every mark, in both axes, silently. The clip has one red pixel; enlarged,
    the red block on screen has to be centred on its coordinates."""
    print("\nthe convention: pixel centres at integers")
    x, y = rig.m.clip.RED
    for _ in range(12):
        rig.mouse("scroll", rig.to_px((x, y)), step=1)

    def red(dx, dy):
        r, g, b = rig.screen_rgb((x + dx, y + dy))
        return r > 200 and g < 60 and b < 60
    check(red(0, 0), f"the screen is red at ({x}, {y}), the red pixel's coordinates", f"{rig.screen_rgb((x, y))}")
    check(all(red(dx, dy) for dx in (-0.4, 0.4) for dy in (-0.4, 0.4)), "and out to 0.4 px either side of it, both ways")
    check(not any(red(dx, dy) for dx, dy in ((-0.6, 0), (0.6, 0), (0, -0.6), (0, 0.6))),
          "and not at 0.6 px: the block is centred on the integer, not hung from it")
    rig.key("r")


def drive_saving(rig, new_rig):
    print("\nsaving")
    from PIL import Image
    m = rig.m
    c, ms = m.clip, m.ms
    m.goto(c.n0 + 10)                            # wherever the sections above left it: the harness compares files
    rig.key("3")
    click(rig, (c.W / 2, c.H / 2))
    rig.key("1")
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        rig.key("s")
    j, t, p = (Path(f"{m.out}_marks.{e}") for e in ("json", "csv", "png"))
    check(j.exists() and t.exists() and p.exists(), "'s' writes the marks, the track CSV and the contact strip")
    rig.after_save()
    again = mark.MarkSet(ms.tag, ms.video, ms.fps, j)
    check(again.marks == ms.marks, "the JSON reads back as the same marks", f"{again.count()} marks")
    check(vf.read_track(t) == {n: (round(x, 2), round(y, 2)) for n, (x, y) in ms.track().items()},
          "the CSV reads back as the object track through the package's own reader")
    cell = 90 * 3
    check(Image.open(p).size == (ms.count() * cell, cell + 18),
          "the contact strip has a magnified cell for every mark", f"{Image.open(p).size}")
    check("link_track(" in said.getvalue() and f"seed={mark.seed_text(ms.seed())}" in said.getvalue(),
          "and the terminal says what to feed the linker")

    # --load: a saved file continues in a new window
    second = new_rig(again)
    second.m.goto(ms.frames()[0])
    check(len(second.drawn()) == 1 and np.allclose(second.drawn()[0], ms.marks["object"][ms.frames()[0]]),
          "a saved file reopens with its marks drawn")
    second.close()

    j.unlink()
    with contextlib.redirect_stdout(io.StringIO()):
        rig.key("q")
    check(j.exists(), "'q' saves")
    check(not rig.is_open(), "and closes the window")
    return json.loads(j.read_text(encoding="utf-8"))


def drive_every_key(rig):
    """The table against the window. The menus, Help -> Keys and --help are all made from
    actions.ACTIONS, so what is left to go wrong is the window: a row nothing is bound to,
    or a key that reaches the wrong row, or none -- two QActions given the same shortcut
    silently cancel each other."""
    print("\nthe table of actions")
    from mcdonald import actions
    m = rig.m
    rows = actions.for_window(rig.window)
    check(set(m._handlers) == {a.id for a in rows}, "the window has a handler for every row of the table, and no others",
          f"{len(rows)} rows; differing: {sorted(set(m._handlers) ^ {a.id for a in rows}) or 'none'}")
    real, ran, wrong = m._handlers, [], []
    m._handlers = {a.id: (lambda i=a.id: ran.append(i)) for a in rows}
    try:
        for a in rows:
            for k in a.keys:
                ran.clear()
                rig.key(k)
                if ran != [a.id]:
                    wrong.append(f"{k!r} ran {ran or 'nothing'}, not {a.id}")
    finally:
        m._handlers = real
    check(not wrong, f"each of its {sum(len(a.keys) for a in rows)} keys runs its own row, and only that",
          "; ".join(wrong[:4]))
    theirs = [a for a in actions.ACTIONS if a not in rows]
    if theirs:                                   # a key this window does not have must do nothing, not something else
        before = (m.n, m.cls, m.ms.count())
        for a in theirs:
            for k in a.keys:
                rig.key(k)
        check((m.n, m.cls, m.ms.count()) == before and rig.is_open(), "and the other window's keys do nothing here",
              f"{sum(len(a.keys) for a in theirs)} keys")


# ---------------------------------------------------------------- what only the Qt window has
def drive_the_menus(rig):
    """Someone who has only the window finds out what it does from its menus. There was no
    menu bar at all, and 'l', 'o', 'c', 't', '[' and ']' were in a docstring."""
    print("\nfinder: the menus")
    from mcdonald import actions
    from PySide6 import QtGui, QtWidgets
    m = rig.m

    def leaves(menu):
        for act in menu.actions():
            if act.menu() is not None:
                yield from leaves(act.menu())
            elif not act.isSeparator():
                yield act
    found = {act.text(): (top.text().replace("&", ""), act) for top in m.menuBar().actions() for act in leaves(top.menu())}
    rows = actions.for_window("qt")
    check(sorted(found) == sorted(a.text for a in rows), "every row of the table is in a menu, and nothing else is",
          f"{len(found)} entries under {', '.join(t.text().replace('&', '') for t in m.menuBar().actions())}")
    wrong = [a.text for a in rows if a.text in found and
             (found[a.text][0] != a.menu.split(">")[0] or found[a.text][1].shortcuts() != [QtGui.QKeySequence(k) for k in a.keys]
              or not found[a.text][1].statusTip())]
    check(not wrong, "under the menu the table names, showing its keys, with a line of help for the status bar",
          ", ".join(wrong))
    rig.key("3")
    check(m.acts["class_3"].isChecked() and not m.acts["class_1"].isChecked(), "the Mark menu ticks the class being marked")
    rig.key("1")

    n = m.n
    rig.key("F1")
    page = m.keys_page
    text = " ".join(page.findChild(QtWidgets.QTextBrowser).toPlainText().split())
    from mcdonald.mark_qt import native_keys                      # on a Mac the page says ⌘ and ⇧, as the menus do
    missing = [k for k, h, _ in actions.listing("qt") if any(" ".join(t.split()) not in text for t in (native_keys(k), h))]
    check(page.isVisible() and m.stack.currentWidget() is page and not missing,
          "F1 is Help -> Keys, a page over the video: every key and the mouse, with what each does",
          f"{len(actions.listing('qt'))} lines" + (f"; missing {missing[:3]}" if missing else ""))
    rig.key(".")
    check(m.n == n and not m.acts["next"].isEnabled() and m.acts["quit"].isEnabled(),
          "with a page in front the video's own keys are off (a key pressed on a page must not move the video behind it); "
          "quit, open and help stay", f"n {m.n} for {n}")
    rig.key("Escape")
    rig.settle(50)
    check(m.keys_page is None and m.stack.currentWidget() is m.split and not page.isVisible(), "Esc closes the page, and the video is back")
    rig.key(".")
    check(m.n == n + 1, "with its keys")
    rig.key(",")


TRADE_WORDS = (r"\bclips?\b", r"\bdetectors?\b", r"\bcandidates?\b", r"\bpx\b", r"\bfps\b", r"\bDN\b", r"\bextract", r"static masks?",
               r"\bvelocity\b", r"\bpolarity\b", r"\bprovisional\b", r"\bcase (report|folder|directory)\b", r"\bkinematics\b")


def drive_plain_words(rig):
    """What the window says is written for someone outside the field (Jacob, 2026-09-21): a
    video, not a clip; a spot the computer found, not a detector's candidate; pixels, not px.
    Text drifts back toward the trade's words one tooltip at a time, so the words are read
    off the live widgets -- the menus and their lines of help, every label, tip and
    placeholder, the two Help pages, the Find and Measure panels -- and the trade's are
    looked for. Two things are let through: the report's own headings, which Getting
    started quotes so that they can be found, and what a mark's record says (`how`, in the
    table's tips), which is the files' wording and not the window's."""
    print("\nfinder: plain words")
    import re
    from PySide6 import QtGui, QtWidgets
    from mcdonald import actions, find_qt, measure_qt, several_qt
    m = rig.m
    from mcdonald import known_qt
    said, panels = [], [find_qt.FindPanel(m), measure_qt.MeasurePanel(m), several_qt.SeveralPanel(m),
                        known_qt.KnownForm(ruler=lambda done: None), known_qt.KnownForm(ruler=lambda done: None, narrow=True)]
    m.show_keys()
    roots = [m.keys_page]
    m.show_first_run()                                # the Help pages are pages of the window, one in front at a time
    roots += [m.first_run_page, m] + panels
    for root in roots:
        for w in [root] + root.findChildren(QtWidgets.QWidget):
            up, technical = w, False
            while up is not None and not technical:     # Measure's optional fields may use the trade's terms (Jacob, 2026-09-24)
                technical, up = up.objectName() == "technical", up.parentWidget()
            if technical:
                continue
            said += [w.windowTitle() if w.isWindow() else "", w.toolTip(), w.statusTip()]
            if isinstance(w, QtWidgets.QTextBrowser):
                said.append(w.toPlainText())
            elif not isinstance(w, (QtWidgets.QPlainTextEdit, QtWidgets.QAbstractSpinBox)):
                said += [getattr(w, name)() for name in ("text", "placeholderText", "title") if callable(getattr(w, name, None))]
            if isinstance(w, QtWidgets.QAbstractSpinBox):
                said += [w.prefix() if hasattr(w, "prefix") else "", w.suffix() if hasattr(w, "suffix") else ""]
        for act in root.findChildren(QtGui.QAction):
            said += [act.text(), act.statusTip(), act.toolTip()]
    said = [re.sub(r"<[^>]+>", " ", t) for t in said if t and t.strip()]
    quoted = ("What this clip cannot decide",)
    found = sorted({(re.search(pat, t.replace(quoted[0], ""), re.I if pat != r"\bDN\b" else 0).group(0), t[:60]) for t in said for pat in TRADE_WORDS
                    if re.search(pat, t.replace(quoted[0], ""), re.I if pat != r"\bDN\b" else 0)})
    check(len(said) > 150 and not found, "nothing the window says uses the trade's words where plain ones will do",
          f"{len(said)} pieces of text; " + "; ".join(f"{w!r} in {t!r}" for w, t in found[:6]))
    words = " ".join(actions.first_run()[0][1].split())
    check(all(w in words for w in ("frames", "A mark is", "A track is", "To link is")),
          "and the four words it keeps -- frame, mark, track, link -- are said before they are used", words[:70])
    m.first_run_page.close()
    for d in panels:
        d.close()


def drive_the_finder(rig, new_rig):
    """Finding the object in a clip you have not seen: timeline, playback, undo,
    the detector, the overview. None of it may touch what a mark is."""
    from PySide6 import QtCore, QtTest
    from PySide6.QtCore import Qt
    m = rig.m
    c, ms = m.clip, m.ms

    print("\nfinder: getting about")
    tl = m.timeline
    rig.mouse("press", (tl.x_of(c.n0 + 25), tl.height() / 2), button=1, widget=tl)
    rig.mouse("release", (tl.x_of(c.n0 + 25), tl.height() / 2), button=1, widget=tl)
    check(m.n == c.n0 + 25 and rig.shows(c.n0 + 25), "a click on the timeline goes to that frame", f"n={m.n}")
    rig.key("home")
    check(m.n == c.n0, "home is the first frame")
    rig.key("end")
    check(m.n == c.n1, "end is the last")
    marked = ms.frames()
    rig.key("[")
    check(m.n == marked[-1], "'[' goes back to the nearest marked frame", f"n={m.n}, marks on {marked}")
    rig.key("[")
    rig.key("]")
    check(m.n == marked[-1], "and ']' forward again")
    rows = m.table.rowCount()
    check(rows == ms.count(), "the table lists every mark", f"{rows} rows")
    QtTest.QTest.mouseClick(m.table.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                            m.table.visualItemRect(m.table.item(0, 1)).center())
    check(m.n == marked[0], "and clicking a row goes to its frame")
    check(m.view.hasFocus() or not m.table.hasFocus(), "without taking the keyboard away from the frame")

    print("\nfinder: undo")
    m.goto(c.n0 + 20)
    before, clean_title = ms.to_dict(), m.windowTitle()
    click(rig, c.truth(m.n))
    check(" * — " in m.windowTitle() and m.windowTitle().endswith("— mcDonald"), "an unsaved mark shows in the title, which names the video "
          "first and the program after it", repr(m.windowTitle()))
    rig.key("z", ctrl=True)
    check(ms.to_dict() == before and m.windowTitle() == clean_title, "ctrl+z takes it back, and the title with it")
    rig.key("z", ctrl=True, shift=True)
    check(ms.marks["object"].get(m.n) is not None, "ctrl+shift+z puts it back")
    was = ms.marks["object"][m.n]
    click(rig, (was[0] + 3, was[1]))
    rig.key("z", ctrl=True)
    check(ms.marks["object"][m.n] == was, "undoing a move restores the old position, not an empty frame")
    rig.key("backspace")
    rig.key("z", ctrl=True)
    check(ms.marks["object"].get(m.n) == was, "and a deletion can be undone")
    rig.key("backspace")
    check(ms.to_dict() == before, "the marks are back where this section found them")

    print("\nfinder: the loupe")
    rig.mouse("move", rig.to_px(c.RED))
    check(not m.loupe.pixmap().isNull(), "the loupe shows what is under the cursor")
    check(f"x {c.RED[0]:.1f}   y {c.RED[1]:.1f}" in m.cursor_label.text() and "brightness 85 of 255" in m.cursor_label.text(),
          "with its coordinates and its value", repr(m.cursor_label.text()))

    print("\nfinder: playback runs on a clock")
    fps = float(m.fps)
    check(m.fps == Fraction(30000, 1001), "fps is the exact rational", str(m.fps))
    m.goto(c.n0)
    t0 = time.perf_counter()
    rig.key(" ")
    rig.settle(450)
    rig.key(" ")
    due = (time.perf_counter() - t0) * fps
    check(abs((m.n - c.n0) - due) <= 2.5, "in 0.45 s at 1x it advances 0.45 s of frames",
          f"{m.n - c.n0} frames for {due:.1f} due")
    check(m.n - c.n0 == m.shown + m.skipped, "every frame it passed is accounted for, shown or skipped",
          f"{m.shown} shown + {m.skipped} skipped")
    m.goto(c.n0)
    rig.key("-")
    rig.key("-")
    t0 = time.perf_counter()
    rig.key(" ")
    rig.settle(450)
    rig.key(" ")
    due = (time.perf_counter() - t0) * fps / 4
    check(m.speed() == Fraction(1, 4) and abs((m.n - c.n0) - due) <= 1.5, "and a quarter of that at 1/4x",
          f"{m.n - c.n0} frames for {due:.1f} due")
    rig.key("=")
    rig.key("=")
    from PySide6 import QtCore
    m.goto(c.n1 - 3)
    xs = set()
    for n in (c.n0, c.n0 + 1, c.n0 + 8, c.n0 + 10, c.n1 - 11, c.n1):
        m.goto(n)
        rig.settle(30)
        xs.add((m.time_label.width(), m.play_button.mapTo(m, QtCore.QPoint(0, 0)).x()))
    m.goto(c.n1 - 3)
    check(len(xs) == 1, "the time and the buttons beside it stay where they are as the frames go by (they jittered: "
                        "Jacob, PR23)", str(sorted(xs)))
    rig.key(" ")
    check(rig.wait_for(lambda: not m._playing, 3) and m.n == c.n1, "it stops on the last frame")
    m.goto(c.n0)
    check(rig.wait_for(lambda: set(range(c.n0 + 1, c.n0 + 9)) <= set(m.store.cached()), 5),
          "and the frames ahead of the cursor are decoded before they are asked for")

    print("\nfinder: the detector")
    n = c.n0 + 12
    m.goto(n)
    rig.key("c")
    got = rig.wait_for(lambda: bool(m.rings), 60)
    check(got, "'c' shows the detector's candidates, computed off the GUI thread", m.note.text()[:60])
    if got:
        best = m.rings[0]
        d = np.hypot(best.xy[0] - c.truth(n)[0], best.xy[1] - c.truth(n)[1])
        check(d < 0.5, "the strongest is the planted source, to half a pixel", f"{d:.2f} px off")
    check(ms.to_dict() == before, "and showing them marks nothing: which one is the object is the analyst's to say")
    rig.key("c")
    check(not m.rings, "'c' again hides them")

    print("\nfinder: the link, from the marks to an automatic track")
    first, second = ms.frames()[0], ms.frames()[-1]
    everywhere = list(range(c.n0, c.n1 + 1))
    m.auto_box.setChecked(True)
    m.size_box.setValue(31)                      # wrong on purpose: auto has to put it right
    m.goto(first + 5)
    check(m.box is None and m.link is None, "before a link there is no track to draw")
    rig.key("l")
    check(m.linking() and m.link_button.text() == "Stop following", "'l' starts linking, off the GUI thread, and the step's button stops it")
    done = rig.wait_for(lambda: not m.linking() and m.link is not None and m.link.done, 120)
    check(done, "and it finishes", m.link_label.text()[:90] if m.link else "")
    if done:
        L = m.link
        check(L.size is not None and L.size < 31 and m.size_box.value() == int(L.size) and m.dark_box.isChecked() == L.dark,
              "the detector's scale came from the marks, and the controls show the choice", f"{L.size:g} px, dark={L.dark}")
        check(sorted(L.track) == everywhere, "linked back from the first mark to the start, and on from the last to the end",
              f"{len(L.track)} frames, {min(L.track)}–{max(L.track)}; the marks are on {first} and {second}")
        err = max(np.hypot(x - c.truth(n)[0], y - c.truth(n)[1]) for n, (x, y) in L.track.items())
        check(err < 0.5, "on the object in every one of them", f"worst {err:.2f} px")
        check(set(L.residuals) == {first, second} and L.worst() < 0.5 and L.arrivals[second] < 0.5,
              "held against both hand marks, and the link from the first arrives on the second", f"worst {L.worst():.2f} px")
        check(not L.disputed() and all(L.source[n] == "both" for n in range(first, second + 1)),
              "between them the forward and backward links agree on every frame")
        m.goto(first + 5)
        check(m.box is not None and np.allclose(m.box.xy, L.track[first + 5]) and not m.box.disputed,
              "the window draws the track's position on the frame")
        check(m.timeline.linked == sorted(L.track) and m.timeline.disputed == [], "the timeline shows which frames are linked")
        check(ms.to_dict() == before, "none of which has touched the hand marks")
        shown = rig.wait_for(lambda: m.track_strip is not None and m.track_strip.isVisible(), 20)
        check(shown, "the track strip is put in front of whoever made the marks")
        if shown:
            strip = m.track_strip.strip
            rig.mouse("press", (strip.tile * 2.5, 20), button=1, widget=strip)
            check(m.n == strip.frames[2], "and a click on a tile goes to its frame", f"n={m.n}")
            m.track_strip.close()
        here = ms.marks["object"][second]
        m.goto(second)
        click(rig, (here[0] + 4, here[1]))
        check("marks have changed" in m.link_label.text(), "moving a mark says the link is now out of date")
        rig.key("z", ctrl=True)
        check("marks have changed" not in m.link_label.text() and ms.to_dict() == before, "and undoing it takes that back")

        ran = len(m._link_cache)
        t0 = time.perf_counter()
        rig.key("l")
        again = rig.wait_for(lambda: not m.linking() and m.link is not None and m.link.done, 60)
        check(again and len(m._link_cache) == ran and m.link.track == L.track,
              "linking again runs the detector on nothing it has already seen, and gives the same track",
              f"{time.perf_counter() - t0:.1f} s, {ran} frames kept")
        rig.wait_for(lambda: m.track_strip is not None and m.track_strip.isVisible(), 20)
        m.track_strip.close()

        m._link_cache.clear()                        # so that there is something to interrupt
        rig.key("l")
        rig.wait_for(lambda: m.link is not None and m.link.stage == "linking" and m.linking(), 60)
        rig.key("l")
        check(rig.wait_for(lambda: not m.linking(), 30) and m.link.done and m.link.stopped and "stopped" in m.link.say,
              "'l' while linking stops it, and it says so", m.link.say[-40:])

        print("\nfinder: two objects")
        a2, b2 = c.n0 + 3, c.n0 + 30
        rig.key("2")
        for n in (a2, b2):
            m.goto(n)
            click(rig, c.truth2(n))
        rig.key("l")                                 # at once, while the last link's thread may still be finishing
        both = rig.wait_for(lambda: not m.linking() and set(m.links) == {0, 1} and all(k.done for k in m.links.values()), 120)
        check(both, "'l' links the object and object #2 in one go", m.link_label.text()[:70])
        if both:
            L2 = m.links[1]
            err2 = max(np.hypot(x - c.truth2(n)[0], y - c.truth2(n)[1]) for n, (x, y) in L2.track.items())
            check(sorted(L2.track) == everywhere and err2 < 0.5, "object #2's track is on the second source, in every frame",
                  f"worst {err2:.2f} px")
            check(sorted(m.links[0].track) == everywhere and m.link is L2, "the object's is whole again, and the window follows the class in hand")
            m.goto(a2 + 1)
            check(set(m.boxes) == {0, 1} and m.boxes[1].label == "2" and m.boxes[0].label == "",
                  "both are boxed on the frame, and the second says which it is")
            shown = rig.wait_for(lambda: m.track_strip is not None and m.track_strip.isVisible()
                                 and set(m.track_strip.strips) == {0, 1}, 20)
            check(shown, "and each has its strip",
                  "" if shown else f"strip shown: {m.track_strip is not None and m.track_strip.isVisible()}, "
                                   f"strips of {sorted(m.track_strip.strips) if m.track_strip is not None else None}")
            if shown:
                m.track_strip.close()
            with contextlib.redirect_stdout(io.StringIO()):
                rig.key("s")
            auto2 = Path(f"{m.out}_autotrack_object2.csv")
            check(auto2.exists() and vf.read_track(auto2) == {n: (round(x, 2), round(y, 2)) for n, (x, y) in L2.track.items()},
                  "saving writes object #2's track beside the object's")
            m.saved_strip.close()

        print("\nfinder: a disputed frame")
        from mcdonald import autolink
        real = m.links[0]
        n = first + 2
        m.goto(n)
        rig.key("1")
        m._on_link(0, autolink.Link("done", "a link with one frame in dispute", track=dict(real.track),
                                    source={**real.source, n: "disputed"}, marks=dict(real.marks), done=True))
        check(m.box.disputed and m.timeline.disputed == [n], "is drawn as one, on the frame and on the timeline")
        m._on_link(0, real)
        check(not m.box.disputed and m.timeline.disputed == [], "and only while it is")

        print("\nfinder: a follow that finds nothing, from marks Find itself called a line")
        # Jacob on PR43, 2026-09-27: a thing moving 20 px a frame is drawn out along its path; Find sees it by
        # its motion, the follower's spot detector has nothing spot-like to hold, and the person was sent to redo a mark
        from mcdonald import mark
        was = m.ms
        m.ms = mark.MarkSet(was.tag, was.video, was.fps)
        how = ("proposed: 1 of 2 things found moving against the background in frames 1–88 (bright, about 7 pixels wide; "
               "frames 57–74 (seen in 16); moves 17 pixels each frame against the background; more like an edge or a line "
               "than a spot; nothing else moves the same way); accepted at the window by a person looking at its strip")
        m.ms.add("object", c.n0 + 3, 100.0, 100.0, how=how)
        m.ms.add("object", c.n0 + 9, 220.0, 170.0, how=how)
        m._on_link(0, autolink.Link("done", "No spot size from 5 to 71 pixels puts a spot within 6 pixels of the marks. Nothing was linked.", done=True))
        check(m._link_said[0].startswith("What Find found is drawn out into a line, not a spot") and "Nothing was linked" in m._link_said[0],
              "the window says first that the thing is a line the follower cannot hold, then what the follower said", m._link_said[0][:80])
        m.ms.add("object", c.n0 + 5, 150.0, 130.0)                        # one hand mark among them: the person's own, not Find's
        m._on_link(0, autolink.Link("done", "Nothing was linked.", done=True))
        check(m._link_said[0] == "Nothing was linked.", "with a hand mark among them, only what the follower said")
        m.ms = was
        m._on_link(0, real)

        print("\nfinder: snapping, which has to own up")
        n = c.n0 + 16
        m.goto(n)
        x, y = c.truth(n)
        p = rig.to_px((x + 3.0, y - 2.0))
        rig.mouse("press", p, button=1, shift=True)
        rig.mouse("release", p, button=1, shift=True)
        snapped = rig.wait_for(lambda: n in ms.marks["object"], 30)
        check(snapped, "shift+click asks the detector, then places the mark")
        if snapped:
            d = np.hypot(ms.marks["object"][n][0] - x, ms.marks["object"][n][1] - y)
            check(d < 0.3, "on the detector's centroid, not under the cursor", f"{d:.2f} px from the source; the click was 3.6 px off")
            how = ms.how_of("object", n) or ""
            check("snapped to" in how and "3.6 px from a click" in how and n not in ms.by_hand(),
                  "the mark says it was snapped, and from where; it is not counted as a hand mark", how[:60])
            row = [r for r in range(m.table.rowCount()) if m.table.item(r, 1).text() == str(n) and m.table.item(r, 0).text() == "object"]
            check(bool(row) and m.table.item(row[0], 4).text() == "snapped", "and the table shows it")
            rig.key("right", ctrl=True)
            check(ms.how_of("object", n) is None, "nudge it and it is a hand's again")
            rig.key("z", ctrl=True)
            check("snapped to" in (ms.how_of("object", n) or ""), "undo gives it back as it was, provenance and all")
            rig.key("z", ctrl=True)
        sky = rig.to_px((320.0, 40.0))
        rig.mouse("press", sky, button=1, shift=True)
        rig.mouse("release", sky, button=1, shift=True)
        rig.settle(100)
        check(n not in ms.marks["object"] and "No mark was placed" in m.note.text(),
              "shift+click with no candidate near places nothing, and says so", m.note.text()[:60])

        print("\nfinder: nudging")
        m.goto(second)
        was = ms.marks["object"][second]
        for _ in range(3):
            rig.key("right", ctrl=True)
        for _ in range(2):
            rig.key("down", ctrl=True, shift=True)
        now = ms.marks["object"][second]
        check(np.allclose(now, (was[0] + 3.0, was[1] + 0.2)), "ctrl+arrows move the mark a pixel, ctrl+shift a tenth",
              f"({now[0] - was[0]:+.2f}, {now[1] - was[1]:+.2f})")
        rig.key("z", ctrl=True)
        check(ms.marks["object"][second] == was, "and the whole run of nudges is one step to undo")

        print("\nfinder: scrubbing")
        calls = []
        goto = m.goto
        m.goto = lambda n: (calls.append(n), goto(n))[1]
        for n in range(c.n0 + 2, c.n0 + 14):
            m.timeline.scrubbed.emit(n)
        rig.settle(50)
        m.goto = goto
        check(calls == [c.n0 + 13] and m.n == c.n0 + 13, "a dozen requests in one breath decode one frame: the newest",
              f"went to {calls}")

        # leave it as the save below expects: no object #2, and the object linked to the end
        rig.key("2")
        for n in (a2, b2):
            m.goto(n)
            rig.key("backspace")
        rig.key("1")
        rig.key("l")
        tidy = rig.wait_for(lambda: not m.linking() and set(m.links) == {0} and m.links[0].done, 120)
        check(tidy and "object2" not in ms.to_dict()["classes"] and ms.to_dict() == before,
              "with object #2's marks deleted, linking again drops its track; the object's marks are as they were")
        rig.wait_for(lambda: m.track_strip is not None and m.track_strip.isVisible(), 20)
        m.track_strip.close()

    print("\nfinder: the overview")
    rig.key("o")
    ov = m.overview
    check(ov.isVisible() and ov.frames[0] == c.n0 and ov.frames[-1] == c.n1,
          "'o' opens tiles from the first frame to the last", f"{len(ov.frames)} tiles")
    check(rig.wait_for(lambda: ov.filled >= len(ov.frames), 20), "every tile gets its picture")
    target = ov.frames[len(ov.frames) // 2]
    item = ov.list.item(ov.frames.index(target))
    ov.list.scrollToItem(item)
    rig.settle(50)
    QtTest.QTest.mouseClick(ov.list.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                            ov.list.visualItemRect(item).center())
    rig.settle(50)
    check(m.n == target and not ov.isVisible(), "clicking a tile goes to its frame and puts the overview away",
          f"n={m.n} for {target}")

    print("\nfinder: closing with unsaved marks")
    other = new_rig(mark.MarkSet("unsaved", ms.video, ms.fps))
    w = other.m
    click(other, c.truth(w.n))
    asked = []
    w.unsaved_answer = lambda: asked.append(1) or "cancel"
    w.close()
    other.settle()
    check(asked and w.isVisible(), "the window asks first, and 'cancel' keeps it open")
    w.unsaved_answer = lambda: "discard"
    w.close()
    other.settle()
    check(not w.isVisible() and not Path(f"{w.out}_marks.json").exists(), "'discard' closes it and writes nothing")
    check(not Path(w._tmp.name).exists(), "and leaves nothing behind in the temporary directory")


def drive_extraction(td):
    """`mcdonald mark` on a clip it has not seen extracts the frames first. That is
    a minute on a long clip, so it happens behind a progress bar with a way out."""
    print("\nfinder: extracting, where the person can see it")
    from mcdonald import mark_qt
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    video = Path(td) / "drawn.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30000/1001",
                    "-frames:v", "90", "-pix_fmt", "yuv420p", str(video)], check=True)
    clip = vf.Clip(video, f"{td}/frames", extract=False)
    seen = []
    got = mark_qt.extract_with_progress(clip, watch=lambda box: (seen.append(box.value()), box.cancel()))
    check(got is False and not clip.extracted(), "Cancel stops ffmpeg, and the window is told it has no frames",
          f"{clip.n_extracted()} of 90 written before it stopped")
    seen.clear()
    got = mark_qt.extract_with_progress(clip, watch=lambda box: seen.append((box.value(), box.maximum())))
    check(got is True and clip.extracted() and clip.n_extracted() == 90, "left alone it runs to the end", f"{clip.n_extracted()} frames")
    check(bool(seen) and all(total == 90 for _, total in seen) and [v for v, _ in seen] == sorted(v for v, _ in seen),
          "with the bar counting frames as ffmpeg writes them", f"{len(seen)} updates, last at {seen[-1][0] if seen else None}")
    check(mark_qt.extract_with_progress(clip, watch=lambda box: seen.append("again")) is True and "again" not in seen,
          "and a clip already extracted opens without asking")


def drive_the_player(d, truth):
    """The range chooser is a player, because someone who has not seen the clip cannot name
    frame numbers: they have to watch it, go back, and step round the place. `truth` is the
    same clip extracted, which is what says that the frame on the screen is the frame the
    label says it is."""
    from fractions import Fraction
    from PySide6 import QtCore, QtGui, QtTest
    from PySide6.QtCore import Qt

    def on_screen():
        img = d.preview.pixmap().toImage().convertToFormat(QtGui.QImage.Format.Format_RGB888)
        a = np.frombuffer(img.constBits(), np.uint8).reshape(img.height(), img.bytesPerLine())
        a = a[:, :3 * img.width()].reshape(img.height(), img.width(), 3).astype(np.float32)
        err = {n: float(np.abs(truth.rgb(n) - a).mean()) for n in truth.frames()}
        return min(err, key=err.get)

    def key(k, shift=False):
        if d.window().isActiveWindow() is False:
            d.activateWindow()
            QtTest_wait(d.isActiveWindow, 3)
        mod = Qt.KeyboardModifier.ShiftModifier if shift else Qt.KeyboardModifier.NoModifier
        QtTest.QTest.keyClick(QtWidgets.QApplication.focusWidget() or d, k, mod)

    from PySide6 import QtWidgets
    B = QtWidgets.QDialogButtonBox.StandardButton
    check(all(d.buttons.button(b).icon().isNull() for b in (B.Open, B.Cancel))
          and not QtWidgets.QApplication.style().styleHint(QtWidgets.QStyle.StyleHint.SH_DialogButtonBox_ButtonsHaveIcons),
          "its Open and Cancel carry no icons from the desktop theme, and no dialog's buttons will: the window's own style says so")
    check(QtTest_wait(lambda: d.shown == 1, 10) and on_screen() == 1 and "frame 1 of 90" in d.where.text(),
          "it opens on the first frame, and says which frame is on the screen", repr(d.where.text()))
    from PySide6 import QtCore
    x1 = d.buttons_by_id["play"].mapTo(d, QtCore.QPoint(0, 0)).x()
    d.goto(44)
    check(QtTest_wait(lambda: d.shown == 44, 10) and on_screen() == 44, "a place on the bar is gone to, and the picture is that frame's")
    check(d.buttons_by_id["play"].mapTo(d, QtCore.QPoint(0, 0)).x() == x1,
          "and the buttons stay where they were as the frame number grows a digit", f"{x1}")
    d.buttons_by_id["end"].click()
    check(d.chosen() == (20, 44) and d.bar.part == (20, 44), "'End here' ends the part at the frame on the screen, and the bar shows the part")
    key(Qt.Key.Key_Right)
    check(QtTest_wait(lambda: d.shown == 45, 5) and on_screen() == 45, "the right arrow steps one frame on")
    key(Qt.Key.Key_Left, shift=True)
    check(QtTest_wait(lambda: d.shown == 35, 5) and on_screen() == 35, "shift and the left arrow step ten frames back")
    key(Qt.Key.Key_BracketLeft)
    check(d.chosen() == (35, 44), "[ starts the part at the frame on the screen")
    seen = []
    d.frame_arrived.connect(lambda _n: seen.append(d.shown))
    t0 = time.monotonic()
    key(Qt.Key.Key_Space)
    check(d.playing() == 1 and d.buttons_by_id["play"].text() == "⏸", "space plays")
    QtTest_wait(lambda: d.shown >= 65, 10)
    took, first = time.monotonic() - t0, d.shown
    key(Qt.Key.Key_Space)
    check(not d.playing() and 0.7 < took < 2.5 and on_screen() == d.shown,
          "at the clip's own speed, and space stops it on a frame that is the one it says", f"35 to {first} in {took:.2f} s")
    here = d.shown
    key(Qt.Key.Key_Space, shift=True)
    QtTest_wait(lambda: d.shown <= here - 20, 10)
    key(Qt.Key.Key_Space, shift=True)
    check(not d.playing() and d.shown <= here - 20 and on_screen() == d.shown, "shift and space play it backward", f"{here} to {d.shown}")
    d.first.setValue(20)
    d.last.setValue(40)
    key(Qt.Key.Key_P)
    check(d.playing() == 1, "p plays the part that was chosen")
    QtTest_wait(lambda: not d.playing(), 10)
    check(d.shown == 40 and on_screen() == 40, "from its first frame to its last, and stops there", f"stopped on {d.shown}")
    key(Qt.Key.Key_Equal)
    check(d.speed() == 2 and "2×" in d.speed_label.currentText(), "= plays faster, and the speed menu says so", repr(d.speed_label.currentText()))
    key(Qt.Key.Key_Minus)
    d.speed_box.activated.emit(1)
    check(d.speed() == Fraction(1, 4), "and the menu sets it", str(d.speed()))
    d.speed_box.activated.emit(3)
    d.bar.resize(900, d.bar.height())
    x0, x1 = d.bar.x_of(d.chosen()[0]), d.bar.x_of(d.chosen()[1])
    QtTest.QTest.mousePress(d.bar, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(int(x0), 10))
    QtTest.QTest.mouseMove(d.bar, QtCore.QPoint(int(d.bar.x_of(25)), 10))
    QtTest.QTest.mouseRelease(d.bar, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(int(d.bar.x_of(25)), 10))
    check(d.chosen()[0] == 25 and d.first.value() == 25 and d.n == 25, "the part's start is a handle on the bar: dragged, the part "
          "and the picture follow it", f"{d.chosen()}, frame {d.n}")
    QtTest.QTest.mousePress(d.bar, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(int(d.bar.x_of(d.chosen()[1])), 10))
    QtTest.QTest.mouseMove(d.bar, QtCore.QPoint(int(d.bar.x_of(10)), 10))
    QtTest.QTest.mouseRelease(d.bar, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(int(d.bar.x_of(10)), 10))
    check(d.chosen() == (25, 25), "and the end cannot be dragged past the start", str(d.chosen()))
    d.first.setValue(20)
    d.last.setValue(40)
    tips = {k: b.toolTip() for k, b in d.buttons_by_id.items()}
    check(all("(" in t for t in tips.values()) and "space" in tips["play"] and "[" in tips["start"],
          "there is no menu here, so every button's tip names its key", tips["play"])
    tip = next(b for b in d.findChildren(QtWidgets.QToolButton) if b.text() == "Shortcuts").toolTip()
    check(all(k in tip for k in ("space", "shift", "Home", "[ and ]")), "and Shortcuts lists the keys that have no button")
    d.last.setValue(44)


def drive_getting_in(td):
    """Someone with no terminal: no argument to name the clip with, no --n0/--n1, no --out,
    no --load, and nowhere for an error to be printed. mark_qt.open_session is the way in
    for them and for `mcdonald mark` alike. The dialogs that would wait for a person are
    replaced here by their answers; what they lead to is not."""
    print("\nfinder: getting in with no terminal")
    from PySide6 import QtWidgets
    from mcdonald import mark_qt
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    video, cases = Path(td) / "drawn.mp4", Path(td) / "cases"
    said, asked = [], []
    keep = mark_qt.complain, mark_qt.choose_range, mark_qt.confirm
    mark_qt.complain = lambda parent, text: said.append(text)

    # which part, and what it costs
    clip = vf.Clip(video, f"{td}/frames2", extract=False)
    d = mark_qt.RangeChooser(clip)
    d.show()
    check(d.chosen() == (1, 90) and "Needs about" in d.cost.text() and "free" in d.cost.text()
          and "90 of 90 frames still have to be saved" in d.cost.toolTip() and clip.dir.name in d.cost.toolTip(),
          "the range chooser opens on the whole clip and says in a few words what extracting it costs; its tip says where",
          repr(d.cost.text()))
    d.first.setValue(30)
    d.last.setValue(50)
    check("21 of 21 frames" in d.cost.toolTip() and "21 frames" in d.span.text() and "0:00.97" in d.span.text(),
          "a shorter range costs less, and is given in time as well as frames", repr(d.span.text()))
    d.last.setValue(20)
    check(d.chosen() == (20, 20), "the end cannot come before the start: the other follows the one that moved")
    got = QtTest_wait(lambda: d.preview.pixmap() is not None and not d.preview.pixmap().isNull(), 15)
    check(got and clip.n_extracted() == 0, "there is a picture to find the place by, from ffmpeg, without extracting anything",
          f"{clip.n_extracted()} frames extracted")
    drive_the_player(d, vf.Clip(video, f"{td}/frames"))
    real = clip.cost
    clip.cost = lambda a=None, b=None: {**real(a, b), "bytes": 10 ** 15}
    d.first.setValue(21)
    ok = d.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Open)
    check(not ok.isEnabled() and d.cost.text().startswith("Too large") and "more than there is room for" in d.cost.toolTip(),
          "a range that will not fit cannot be opened, and says why", repr(d.cost.text()))
    d.close()
    clip.cost = real

    # the dialogs that wait for an answer, answered as a person would -- no test drove them until 2026-09-23
    from PySide6 import QtCore
    answers, handled = [], []

    def poll():
        m = QtWidgets.QApplication.activeModalWidget()
        if m is not None and m.isVisible() and (not handled or m is not handled[-1] or getattr(m, "_asked_again", False)) and answers:
            handled.append(m)
            answers.pop(0)(m)
        if answers:
            QtCore.QTimer.singleShot(60, poll)

    def answer(*acts):
        answers[:] = list(acts)
        handled.clear()
        QtCore.QTimer.singleShot(60, poll)
    Open = QtWidgets.QDialogButtonBox.StandardButton.Open

    w0 = mark_qt.QtMarker(cases=str(cases))          # the chooser is a page of the window while it asks
    w0.show()

    def on_chooser(fn):
        def poll():
            d = w0.chooser
            if d is not None and w0.stack.currentWidget() is d:
                fn(d)
            else:
                QtCore.QTimer.singleShot(60, poll)
        QtCore.QTimer.singleShot(60, poll)

    def pick(m):
        m.first.setValue(12)
        m.last.setValue(40)
        counted.append((m.count.value(), m.count.specialValueText(), m.count.text()))
        m.count.setValue(3)                           # how many objects they are looking for (Jacob, 2026-10-08)
        m.buttons.button(Open).click()
    counted = []                                      # (`asked` is the way in's, further down)
    mark_qt.settings().remove(f"objects/{clip.video.name}")
    on_chooser(pick)
    got = keep[1](clip, w0)
    check(got == (12, 40) and mark_qt.remembered_part(clip) == (12, 40) and w0.chooser is None and w0.stack.currentWidget() is w0.home,
          "the part chosen on the player's page is what opens, and it is remembered; the page then goes", str(got))
    check(counted == [(0, "I don't know", "I don't know")] and w0.objects_expected == 3 and mark_qt.remembered_objects(clip) == 3,
          "the segment step asks how many objects they are looking for, \"I don't know\" unless they say; a number is the window's "
          "and is remembered for the video", str(counted))
    seen = []
    on_chooser(lambda m: seen.append((m.chosen(), m.count.value())) or m.reject())
    check(keep[1](clip, w0) is None and seen == [((12, 40), 3)],
          "opened again, the player starts on the part chosen last time and the count said then; and Cancel opens nothing", str(seen))
    mark_qt.settings().remove(f"objects/{clip.video.name}")
    w0._closing = True
    from mcdonald import catalog as cat
    was = cat.active()
    cat.use(cat.NullCatalog())
    mark_qt.confirm = keep[2]
    answer(lambda m: m.button(QtWidgets.QMessageBox.StandardButton.No).click())
    w0.home.catalog_button.click()                    # the home page is the start screen (2026-10-08): no dialog before it
    check(w0.clip is None and not answers and w0.stack.currentWidget() is w0.home,
          "the home page: by catalog name with no catalog asks whether to choose one; no opens nothing")

    # the storage folder: on the home page, with a way to change it (Jacob, 2026-09-24)
    home_was = os.environ.get("MCDONALD_HOME")
    mark_qt.settings().setValue("cases", str(Path(td) / "somewhere"))
    before, chose = w0.home.where.text(), mark_qt.choose_folder
    mark_qt.choose_folder = lambda parent, title, where: str(Path(td) / "store")
    w0.home.change.click()
    mark_qt.choose_folder = chose
    shown = w0.home.where.text()
    check(str(Path(td) / "store") not in before and f"saved to {Path(td) / 'store'} (" in shown and " free)" in shown,
          "the home page says where videos and their pictures are kept, and how much room there is; Change… changes it, "
          "and it says so", shown[-120:])
    w0.close()
    check(os.environ.get("MCDONALD_HOME") == str(Path(td) / "store") and mark_qt.settings().value("storage") == str(Path(td) / "store")
          and mark_qt.cases_folder() == str(Path(td) / "store"),
          "it is remembered, everything started from here sees it, and a video's files are saved there too",
          mark_qt.cases_folder())
    mark_qt.settings().remove("storage")

    # a catalog video that is not here yet: asked first, and no is no, without a complaint
    class One(cat.Catalog):
        name = "test"

        def videos(self):
            return [dict(path=str(Path(td) / "store" / "videos" / "far.mp4"), id="PR999", title="DOW-UAP-PR999, far",
                         url=video.resolve().as_uri(), bytes=video.stat().st_size)]
    cat.use(One())
    questions, n = [], len(said)
    mark_qt.confirm = lambda parent, text: questions.append(text) and False
    check(mark_qt.open_session("PR999", cases=str(cases)) is None and len(said) == n and not (Path(td) / "store" / "videos" / "far.mp4").exists(),
          "a catalog video not on this computer is asked about, and no opens nothing and complains of nothing")
    check(questions and "PR999 is not on this computer yet" in questions[0] and "MB" in questions[0] and "free" in questions[0],
          "the question says how large it is, where it will go, and how much room there is", questions[0][:60] if questions else "")
    mark_qt.confirm = lambda parent, text: True
    mark_qt.choose_range = lambda clip, parent=None: (10, 30)
    got = mark_qt.open_session("PR999", cases=str(cases))
    check(got is not None and (Path(td) / "store" / "videos" / "far.mp4").read_bytes() == video.read_bytes()
          and Path(got.clip.dir) == Path(td) / "store" / "frames" / "far",
          "yes downloads it into the storage folder's videos, and its frames go in its frames", str(got.clip.dir) if got else "")
    if got is not None:
        got.close()

    # one whose address does not answer: the complaint is a sentence -- what, from where, why -- not a traceback
    class Gone(One):
        def videos(self):
            return [dict(path=str(Path(td) / "store" / "videos" / "gone.mp4"), id="PR998", title="DOW-UAP-PR998, gone",
                         url="https://127.0.0.1:9/gone.mp4", bytes=1000)]
    cat.use(Gone())
    n = len(said)
    check(mark_qt.open_session("PR998", cases=str(cases)) is None and len(said) == n + 1
          and "PR998 is not on this computer, and could not be downloaded from" in said[-1] and "could not reach" in said[-1]
          and "urlopen error" not in said[-1] and not (Path(td) / "store" / "videos" / "gone.mp4.part").exists(),
          "one whose address does not answer is complained of in a sentence: what, from where, and why",
          said[-1][-150:] if len(said) > n else "no complaint")
    mark_qt.confirm, mark_qt.choose_range = keep[2], keep[1]
    if home_was is None:
        os.environ.pop("MCDONALD_HOME", None)
    else:
        os.environ["MCDONALD_HOME"] = home_was
    cat.use(was)

    # the way in
    mark_qt.choose_range = lambda clip, parent=None: asked.append((clip.n0, clip.n1)) or (10, 30)
    w = mark_qt.open_session(str(video), workdir=f"{td}/frames2", cases=str(cases))
    check(w is not None and asked == [(1, 90)] and (w.clip.n0, w.clip.n1) == (10, 30), "with no range named, the person is asked for one")
    check(w.clip.n_extracted() == 21 and not w.clip.path(9).exists() and not w.clip.path(31).exists(),
          "and only that much is extracted", f"{len(list(Path(w.clip.dir).glob('*.png')))} frames on disk")
    check(Path(w.out) == cases / "drawn" / "drawn" and str((cases / "drawn").resolve()) in w.case_label.text(),   # the label resolves it: Windows' temp is RUNNER~1
          "the case directory is in a folder of cases, and the window says where", repr(w.case_label.text()))
    check(not (cases / "drawn").exists(), "nothing is made on disk until there is something to save")
    w.show()
    w.ms.add("object", 12, 100.0, 50.0)
    with contextlib.redirect_stdout(io.StringIO()):
        w.finish(show_strip=False)
    check((cases / "drawn" / "drawn_marks.json").exists(), "saving makes it")
    had = os.environ.pop("MCDONALD_CASES", None)
    w.save_to(str(Path(td) / "elsewhere" / "drawn"))
    check((Path(td) / "elsewhere" / "drawn" / "drawn_marks.json").exists() and mark_qt.cases_folder() == str(Path(td) / "elsewhere"),
          "saved to another folder, it is where the next video's folder goes, after a restart too", mark_qt.cases_folder())
    mark_qt.settings().remove("cases")
    if had is not None:
        os.environ["MCDONALD_CASES"] = had
    asked.clear()
    again = mark_qt.open_session(str(video), 10, 30, workdir=f"{td}/frames2", cases=str(cases))
    check(again is not None and not asked and again.ms.marks == w.ms.marks,
          "opened again with a range, nobody is asked, and the marks saved in that case come back")
    again.close()
    asked.clear()
    whole = mark_qt.open_session(str(video), workdir=f"{td}/frames", cases=str(cases))
    check(whole is not None and not asked and (whole.clip.n0, whole.clip.n1) == (1, 90),
          "a short clip that is all on disk already opens whole, and nobody is asked")
    whole.close()
    long, mark_qt.LONG = mark_qt.LONG, 50
    mark_qt.choose_range = lambda clip, parent=None: asked.append((clip.n0, clip.n1)) and None
    check(mark_qt.open_session(str(video), workdir=f"{td}/frames", cases=str(cases)) is None and asked == [(1, 90)],
          "a long one is asked about all the same: opening it costs nothing, and measuring all of it costs hours")
    mark_qt.LONG = long

    # what goes wrong, said where they can see it
    check(mark_qt.open_session("/nowhere/no-such-clip.mp4") is None and said and "no such file" in said[-1],
          "a clip that is not there is a dialog, in the command line's words", repr(said[-1][:60]) if said else "")
    check(mark_qt.open_session(str(Path(__file__))) is None and "is not a video ffmpeg can read" in said[-1],
          "and so is a file that is not a video", repr(said[-1][:70]))
    blocked = Path(td) / "a-file-not-a-folder"
    blocked.write_text("", encoding="utf-8")
    n = len(said)
    w.out = str(blocked / "drawn" / "drawn")
    w.finish()
    check(len(said) == n + 1 and "Nothing was saved" in said[-1] and "Save to a different folder" in said[-1],
          "a save that fails says so, and says what to do")

    # --out and --load, from the File menu
    with contextlib.redirect_stdout(io.StringIO()):
        w.save_to(str(Path(td) / "elsewhere"))
    check((Path(td) / "elsewhere" / "drawn_marks.json").exists() and "elsewhere" in w.case_label.text(),
          "File -> Save to a different folder moves the case, saves there, and the window follows")
    by_agent = Path(td) / "agent_marks.json"                  # four lines, whole numbers, as the handoff says one can be written
    by_agent.write_text(json.dumps({"classes": {"object": {"12": [101, 51], "15": [90, 60], "80": [5, 5]}},
                                    "how": {"object": {"12": "agent: candidate 1 of 3 at 9 px"}}}), encoding="utf-8")
    w.open_marks(str(by_agent))
    shown = {w.table.item(r, 1).text(): w.table.item(r, 4).text() for r in range(w.table.rowCount())}
    check(shown == {"12": "agent", "15": "hand", "80": "hand"} and "candidate 1 of 3" in w.table.item(0, 4).toolTip(),
          "a mark an agent placed is shown as an agent's, with its reason, to the person who opens the file", str(shown))
    check(w.ms.marks["object"] == {12: (101.0, 51.0), 15: (90.0, 60.0), 80: (5.0, 5.0)} and "1 of them are on frames outside" in w.note.text(),
          "File -> Open marks continues from a marks file, and says which of its marks this range cannot show", repr(w.note.text()[:60]))
    check(" * — " in w.windowTitle(), "they are not this case's saved marks, so the window counts them unsaved")
    junk = Path(td) / "junk.json"
    junk.write_text("[1, 2, 3]", encoding="utf-8")
    n, before = len(said), dict(w.ms.marks["object"])
    w.unsaved_answer = lambda: "discard"
    w.open_marks(str(junk))
    check(len(said) == n + 1 and "is not a marks file" in said[-1] and w.ms.marks["object"] == before,
          "a file that is not a marks file is refused, and the marks are left alone")
    other = Path(td) / "other_marks.json"
    other.write_text(json.dumps({"video": "/somewhere/another-clip.mp4", "classes": {"object": {"12": [1, 1]}}}), encoding="utf-8")
    put = []
    mark_qt.confirm = lambda parent, text: put.append(text) and False
    w.open_marks(str(other))
    check(len(put) == 1 and "another-clip.mp4" in put[0] and w.ms.marks["object"] == before,
          "marks made on a different clip are questioned before they are opened on this one")

    # another clip, without starting again: into the same window
    second = Path(td) / "second.mp4"
    shutil.copy(video, second)
    mark_qt.choose_range = lambda clip, parent=None: (1, 12)
    w.open_clip(str(second))
    check(w.isVisible() and w.ms.tag == "second" and w.ms.count() == 0 and (w.clip.n0, w.clip.n1) == (1, 12)
          and w.stack.currentWidget() is w.split and "second" in w.windowTitle(),
          "File -> Open a video opens it in the same window, in place, with its own marks")
    check(Path(w.out) == cases / "second" / "second", "and its own case directory, beside the first")
    w.close()
    mark_qt.complain, mark_qt.choose_range, mark_qt.confirm = keep


def drive_the_first_screen_and_memory(td):
    """What a desktop program does now (the audit of 2026-09-26): opens at the size it was closed at, lists
    the videos opened last, takes a video dropped on it, and never waits on the network to draw its
    first screen."""
    print("\nfinder: the first screen, and what is remembered")
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtCore import Qt
    from mcdonald import mark_qt
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    video, cases = Path(td) / "drawn.mp4", Path(td) / "cases"
    keep = mark_qt.choose_range
    mark_qt.choose_range = lambda clip, parent=None: (10, 30)
    w = mark_qt.open_session(str(video), workdir=f"{td}/frames2", cases=str(cases))
    w.show()
    avail = w.screen().availableGeometry()
    want = (min(1040, avail.width() - 40), min(700, avail.height() - 80))     # a size that fits: GitHub's Mac screen is 1024 x 677
    w.resize(*want)
    QtTest_wait(lambda: w.width() == want[0], 3)
    closed = (w.width(), w.height())
    w.close()
    again = mark_qt.open_session(str(video), workdir=f"{td}/frames2", cases=str(cases))
    again.show()
    check((again.width(), again.height()) == closed, "the window opens at the size it was closed at",
          f"{again.width()}x{again.height()}, closed at {closed[0]}x{closed[1]} on a {avail.width()}x{avail.height()} screen")
    again.close()
    recent = mark_qt.recent_videos()
    check(bool(recent) and recent[0][0] == str(video) and recent[0][1] == "drawn.mp4",
          "the video opened last is first on the list of recent ones, by its name", str(recent[:1]))

    # the home page is the start screen (2026-10-08): the recent list, a dropped file, the update check
    w = mark_qt.QtMarker(cases=str(cases), workdir=f"{td}/frames2")
    w.show()
    QtTest_wait(w.isVisible, 5)
    check(w.home.recent_box.isVisible() and w.home.recent_buttons and w.home.recent_buttons[0].text().startswith("drawn.mp4")
          and "frames" in w.home.recent_buttons[0].text() and w.home.open_button.isVisible() and "saved to" in w.home.where.text(),
          "the home page lists the videos opened last, with the frames chosen then, beside the two ways to open one",
          w.home.recent_buttons[0].text() if w.home.recent_buttons else "no recent")
    w.home.recent_buttons[0].click()
    check(w.clip is not None and w.ms.tag == "drawn" and (w.clip.n0, w.clip.n1) == (10, 30),
          "on the home page a recent video is one click, and it opens into the window on the frames chosen last time")
    w.unsaved_answer = lambda: "discard"
    w.unload()
    mime = QtCore.QMimeData()
    mime.setUrls([QtCore.QUrl.fromLocalFile(str(video))])
    pos = QtCore.QPointF(w.width() / 2, w.height() / 2)
    QtWidgets.QApplication.sendEvent(w, QtGui.QDragEnterEvent(pos.toPoint(), Qt.DropAction.CopyAction, mime,
                                                              Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    QtWidgets.QApplication.sendEvent(w, QtGui.QDropEvent(pos, Qt.DropAction.CopyAction, mime,
                                                         Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    check(w.clip is not None and w.ms.tag == "drawn", "a video file dropped on the window is what opens")
    w._closing = True
    w.close()

    class Late:                                   # an update check still on its way when the window comes up
        found, offered = "9.9.9", False

        def __init__(self):
            self.t = time.monotonic()

        def is_alive(self):
            return time.monotonic() - self.t < 0.5
    offered, was = [], mark_qt.offer_update
    mark_qt.offer_update = lambda v: offered.append(v) or True
    w2 = mark_qt.QtMarker(cases=str(cases))
    w2.show()
    t0 = time.monotonic()
    w2.watch_update(Late())
    QtTest_wait(lambda: bool(offered) and not w2.isVisible(), 6)
    mark_qt.offer_update = was
    check(offered == ["9.9.9"] and not w2.isVisible() and time.monotonic() - t0 < 6,
          "the window is up before the update check has answered; the answer is offered when it comes, and yes closes the window",
          f"{offered} after {time.monotonic() - t0:.1f} s")
    w = mark_qt.open_session(str(video), workdir=f"{td}/frames2", cases=str(cases))
    w.show()
    enter = QtGui.QDragEnterEvent(QtCore.QPoint(w.width() // 2, w.height() // 2), Qt.DropAction.CopyAction, mime,
                                  Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    QtWidgets.QApplication.sendEvent(w, enter)
    check(enter.isAccepted(), "the main window takes a dropped video too")
    w.close()
    mark_qt.choose_range = keep


def drive_finding(new_rig):
    """Track -> Find the object: the window proposes, the person says yes or no. The first step
    used to be the person's -- find it, click it -- and their click is now the correction. What
    a proposal may not do is pass for a judgment nobody made: its marks say they were proposed."""
    print("\nfinder: the window proposes the object")
    from PySide6 import QtWidgets
    from mcdonald import find_qt, mark_qt
    rig = new_rig(mark.MarkSet("found", "/nowhere/synthetic.mp4", SyntheticClip.fps))
    m, clip = rig.m, rig.m.clip
    said = []
    keep = mark_qt.complain, find_qt.complain
    mark_qt.complain = find_qt.complain = lambda parent, text: said.append(text)
    check(m.find_button.text() == "Find the object" and "(f)" in m.find_button.toolTip() and m.steps[0].stage == "next",
          "it is the first step, the one to do first, and its button's tip names its key")
    rig.key("F")
    p = m.find_panel
    check(p is not None and p.isVisible() and p.running() and not p.near.isVisible() and p.frames() == (clip.n0, clip.n1),
          "f opens the panel and it starts looking, in everything that is open when that is not long")
    check(p.area.isHidden() and p.looking.isVisible() and "Looking" in p.looking.text() and m.split.sizes()[0] > m.split.sizes()[1],
          "while it looks the panel says so and shows no empty list; the video keeps most of the window", str(m.split.sizes()))
    got = rig.wait_for(lambda: not p.running() and bool(p.proposals) and p.go.isEnabled(), 240)   # the thread has ended, and the panel has heard
    ok = check(got and not said, "it finishes with something on its list", p.now.text()[:80] + ("; " + said[-1][:80] if said else ""))
    check(p.area.isVisible() and m.split.sizes()[1] >= min(p.wanted_height(), 0.44 * m.split.height()) - 20,
          "the list comes with its rows, and the panel takes what they need", f"{m.split.sizes()} for {p.wanted_height()}")
    if not ok:
        m._closing = True
        m.close()
        mark_qt.complain, find_qt.complain = keep
        return
    first = p.proposals[0]
    off = max(np.hypot(first.track[n][0] - clip.truth(n)[0], first.track[n][1] - clip.truth(n)[1]) for n in first.frames)
    second = [q for q in p.proposals if all(np.hypot(q.track[n][0] - clip.truth2(n)[0], q.track[n][1] - clip.truth2(n)[1]) < 3 for n in q.frames)]
    check(off < 3.0 and len(first.track) > 20, "the first row is the brighter of the two things that move, along its path", f"{len(first.track)} frames, worst {off:.1f} px")
    check(bool(second), "and the fainter one is on the list too: which of them is the object is not the detector's to say",
          ", ".join(q.strength() for q in p.proposals))
    row = p.rows[0]
    check(row.pic.pixmap() is not None and not row.pic.pixmap().isNull() and "frames" in row.pic.toolTip()
          and [b.text() for b in row.findChildren(QtWidgets.QPushButton)] == ["Show in video", "This is it"],
          "each row is a strip of the clip's own pixels, with Show in video and This is it")
    check(p.bar.isHidden() and p.halt.isHidden() and "in all" in p.elapsed.text() and "found" in p.now.text()
          and "Mark the object by hand" in p.what.text() and "This is it" in m.steps[0].state.text(),
          "when it ends the bar and Stop go, the time it took is said, the window says what to do if the object is not "
          "there, and the main window's first step says what to do next", m.steps[0].state.text()[:70])
    # Jacob, 2026-09-21: "worked on PR144 but not on PR113". There the object was the eleventh thing on a list that
    # showed eight. The order is better now (test_measurement), and what is further down can be asked for
    import dataclasses
    real = list(p._all)
    p._on_found(0, 0, [first] + [dataclasses.replace(first, score=first.score * f) for f in (0.2, 0.1, 0.05, 0.04, 0.03)])
    check(len(p.rows) == 3 and p.more.isVisibleTo(p) and "3 more" in p.more.text(),
          "the rows shown are the best few, and a button says how many more there are", repr(p.more.text()))
    p.more.click()
    check(len(p.rows) == 6 and not p.more.isVisibleTo(p), "which shows them: in a hard clip the object may be one of those")
    p._more = False
    p._on_found(0, 0, real)
    whole, p.frames = p.frames, lambda: (clip.n0, clip.n0 + 4)
    p.start()
    check(not p.running() and "too short" in p.now.text() and "at least 7" in p.now.text(),
          "a part too short to look in -- someone who opened just the frames the object is in -- is told so, and what to do",
          repr(p.now.text()[:70]))
    p.frames = whole
    row = p.rows[0]
    row.show_.click()
    rig.settle(50)
    check(m.n == first.frames[0] and m._proposal_path is not None and m.ms.count() == 0 and m.note.isHidden(),
          "Show goes to where it starts and draws its path -- and places nothing, and no note covers the video (Jacob on PR43, 2026-09-27)")
    row.take.click()
    rig.settle(50)
    seeds = first.seeds()
    kinds = {n: m.ms.kind("object", n) for n in m.ms.frames("object")}
    check(sorted(kinds) == sorted(seeds) and set(kinds.values()) == {"proposed"} and not m.ms.by_hand() and m._proposal_path is None,
          "This is it places marks along it, every one recorded as proposed and none as a hand's", str(kinds))
    how = m.ms.how_of("object", min(seeds))
    check(how.startswith("proposed: 1 of") and "accepted at the window by a person" in how and first.describe() in how,
          "with what was proposed and who accepted it", how[:90])
    check(not p.isVisible() and (m.linking() or m.links.get(0) is not None), "the panel goes, and the link starts from them as it does from clicks")
    busy = m.linking() and m.steps[1].stage == "busy" and m.steps[1].busy.isVisible() and any(w in m.steps[1].state.text() for w in ("Starting…", "Static masks", "Spot size", "Between marks", "Linking forward", "Linking backward"))
    check(busy or not m.linking(), "and step 2 shows that it is following: a moving bar, and says so", m.steps[1].state.text()[:60])
    bar = mark_qt.Stripes()
    bar.show()
    before = bar._phase
    QtTest_wait(lambda: bar._phase != before, 2)
    check(bar._phase != before, "the bar moves: its stripes run while it is shown (Jacob, 2026-09-25: a still bar did not say so)")
    bar.hide()
    check(not bar._timer.isActive(), "and stop when it is hidden")
    rig.wait_for(lambda: not m.linking() and m.links.get(0) is not None and m.links[0].done, 120)
    link = m.links.get(0)
    worst = max(np.hypot(x - clip.truth(n)[0], y - clip.truth(n)[1]) for n, (x, y) in link.track.items()) if link and link.track else None
    check(worst is not None and worst < 1.0 and len(link.track) >= 30, "and is on the object, measured by the package's own detector",
          f"{len(link.track) if link else 0} frames, worst {worst:.2f} px" if worst is not None else "no link")
    got = rig.wait_for(lambda: m.track_strip is not None and m.track_strip.isVisible(), 20)
    stages = [st.stage for st in m.steps]
    check(got and stages == ["done", "next", "todo"] and m.steps[1].state.text() == "Check the track below the video"
          and m.track_strip.yes.isVisible() and m.track_strip.no.isVisible(),
          "when it ends, the strip asks whether the box is on the object, with a yes and a no; until then Measure waits",
          f"{stages}")
    m.track_strip.no.click()
    check(not m.track_strip.isVisible() and m.hand.isVisible() and m.steps[1].stage == "next" and "goes off" in m.steps[1].state.text()
          and m.steps[2].stage == "todo", "no opens marking by hand and says what to do", m.steps[1].state.text()[:60])
    m.show_hand(False)
    m.check_button.click()
    rig.wait_for(lambda: m.track_strip is not None and m.track_strip.isVisible(), 5)
    m.track_strip.yes.click()
    stages = [st.stage for st in m.steps]
    check(stages == ["done", "done", "next"] and "chosen from what Find showed" in m.steps[0].state.text()
          and m.link_button.text() == "Follow again" and m.hand.isHidden(),
          "the steps move on: found (chosen from Find), followed, and Measure is next; marking by hand stays folded",
          f"{stages}, {m.steps[0].state.text()!r}")
    check(m.steps[1].state.text() == "Track checked: on the object", "and step 2 says so in a few words, without the link's summary",
          repr(m.steps[1].state.text()[:60]))
    shown = {m.table.item(r, 1).text(): m.table.item(r, 4).text() for r in range(m.table.rowCount())}
    check(set(shown.values()) == {"proposed"}, "the table of marks says proposed, where a click says hand", str(shown))
    rig.key("Z", ctrl=True)
    check(m.ms.count() == 0, "taking a proposal is one step to undo")
    click(rig, clip.truth2(m.n))
    check(m.ms.kind("object", m.n) == "hand", "and a click is still a click: the person's correction, recorded as a hand's")
    check(m.hand.isVisible() and m.hand_toggle.isChecked(), "and the first mark by hand opens “Mark the object by hand”, where its table is")
    m._undo.setClean()
    m._closing = True
    m.close()
    mark_qt.complain, find_qt.complain = keep


def drive_measuring(td):
    """The window ended where the measurements began: `layers`, `integrity`, `run` had no
    window of any kind, and a case report was a file on a disk. Measure -> Measure this clip
    is `stages.run_case` -- what `mcdonald run` is a command line over -- with a form in
    place of the options and the track sheet put in front of the person in place of
    --i-looked. Held to what the command line is held to: the same case, from the same marks.

    The clip is test_cli's: the planted disc as a real video, because the stages' processes
    open the clip by its file."""
    print("\nfinder: the measurements, from the window")
    from PySide6 import QtWidgets
    from mcdonald import actions, mark_qt, measure_qt, stages
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_cli import mcdonald as command, planted_video
    home = Path(td) / "measuring"
    home.mkdir()
    truth, video = planted_video(home)
    case, frames = home / "case", home / "frames"
    said = []
    keep = mark_qt.complain, measure_qt.complain
    mark_qt.complain = measure_qt.complain = lambda parent, text: said.append(text)
    w = mark_qt.open_session(str(video), 1, 24, out=str(case), workdir=str(frames))
    w.show()

    w.do("report")
    check(w.report_page is None and "no report for this video" in w.note.text(), "before anything is measured, Show the case report says there is none, and how to make one",
          repr(w.note.text()[:70]))
    w.do("measure")
    p = w.measure_panel
    check(p is not None and p.isVisible() and "no track of the object yet" in p.what.text() and "Follow it" in p.what.text(),
          "Measure opens a panel; with nothing linked it says nothing of an object will be measured, and what to do", repr(p.what.text()[:60]))
    rows = {k.name: k for k in stages.KNOWN}
    check(set(p.fields) == set(rows) and all(p.fields[n].toolTip() == f"{k.help} (command line: {k.flag})" for n, k in rows.items())
          and all(p.fields[n].parentWidget().objectName() == "technical" for n in rows),
          "its form has a field for every row of stages.KNOWN, with the row's help and flag under the pointer, in the part "
          "that may use the trade's terms", f"{len(rows)} rows")
    rc, out, err = command("run", "--help")
    check(rc == 0 and all(k.flag + " " in out and " ".join(k.help.split()[:4]) in " ".join(out.split()) for k in rows.values()),
          "and `mcdonald run --help` has an option for every one of them, in the same words: one table, two shells")
    check(p.slow["layers"].isChecked() and not p.slow["integrity"].isChecked(),
          "of the slow checks, layers is ticked at first and integrity is not (Jacob, 2026-09-25)")
    p.slow["integrity"].setChecked(True)
    check("less than a minute" not in p.cost.text() and "pairs of frames" in p.cost.text() and "integrity" in p.cost.text(),
          "what the two slow stages will take is said before they start", repr(p.cost.text()[:80]))

    for n in (2, 5):
        w.ms.add("object", n, *truth.truth(n))
    w.marks_changed()
    w.do("link")
    QtTest_wait(lambda: not w.linking() and w.links.get(0) is not None and w.links[0].done, 60)
    link = w.links.get(0)
    ok = check(link is not None and len(link.track) >= 10, "two marks and a link, as a person would", link.say if link else "no link")
    if not ok:
        w.close()
        mark_qt.complain, measure_qt.complain = keep
        return
    w.do("measure")
    check("track followed from your marks" in p.what.text() and f"{link.size:g} pixels" in p.fields["size"].placeholderText(),
          "asked again, the panel says which track the case will be made from, and the size the marks chose", repr(p.fields["size"].placeholderText()))

    p.fields["fov"].setText("wide")
    p.start()
    check(not p.running() and said and "wide" in said[-1] and "not a number" in said[-1], "a field that is not a number is refused in a dialog, and nothing starts",
          repr(said[-1]) if said else "")
    p.fields["fov"].setText("")
    # a length measured on the video: the ship in PR149, as the reference object (Jacob, 2026-09-25)
    from PySide6 import QtTest
    from PySide6.QtCore import Qt as _Qt
    p.rulers["ref_px"].click()
    view = w.view
    at = lambda x, y: view.to_view(x, y).toPoint()
    a, b = at(10, 10), at(40, 50)
    QtTest.QTest.mousePress(view.viewport(), _Qt.MouseButton.LeftButton, pos=a)
    QtTest.QTest.mouseMove(view.viewport(), b)
    QtTest.QTest.mouseRelease(view.viewport(), _Qt.MouseButton.LeftButton, pos=b)
    fa, fb = view.to_image(a), view.to_image(b)     # the frame points those whole view pixels are: on a small screen (GitHub's
    expect = math.hypot(fb.x() - fa.x(), fb.y() - fa.y())   # Mac, the video a third the size) not (10, 10) and (40, 50) to the pixel
    got = p.fields["ref_px"].text()
    check(got and abs(float(got) - expect) < 0.1 and not view.ruler and "pixels" in w.note.text(),
          "Measure on the video: a drag along it gives its length in pixels, into the field; the next click is a mark again",
          f"{got!r} for a drag of {expect:.1f}; {w.note.text()[:50]!r}")
    marks = w.ms.count()
    QtTest.QTest.mouseClick(view.viewport(), _Qt.MouseButton.LeftButton, pos=at(12, 12))
    check(w.ms.count() == marks + 1, "and a click after it places a mark, as before")
    w._undo.undo()
    p.fields["ref_px"].setText("")
    view.draw_rule(None, None)
    p.fields["size_px"].setText("21")

    # which frames: someone who opened a whole clip to find a short transit has thousands of frames open
    whole = type("Clip", (), dict(n0=1, n1=5291, fps=30.0))
    check(measure_qt.around({408: 0, 411: 0}, whole) == (348, 471) and measure_qt.around({5: 0, 40: 0}, whole) == (1, 100),
          "the frames worth measuring for a track are the track and two seconds either side, inside what is open")
    check("a group of points" in measure_qt.cost_text(1, 900, ["groups", "flicker"])
          and "a group" not in measure_qt.cost_text(1, 24, ["groups", "flicker"]),
          "and a long stretch says what looking for a group and a beat costs; a short one does not",
          measure_qt.cost_text(1, 900, ["groups", "flicker"]))
    check("hours" in measure_qt.cost_text(1, 5291, ["layers"]) and "min" in measure_qt.cost_text(348, 471, ["layers"]),
          "and the cost is said in hours when it is hours", measure_qt.cost_text(1, 5291, ["layers", "integrity"])[:90])
    check(not p.near.isVisible() and p.frames() == (1, 24), "where that is everything open, there is nothing to choose")
    p.pad_seconds = 0.1                                   # 3 frames either side of the track 1-11, so that this clip has a choice
    p.refresh()
    check(p.near.isVisible() and p.near.isChecked() and p.frames() == (1, 14) and "1–14" in p.near.text() and "all 24 frames" in p.whole.text(),
          "where it is not, the panel offers both and starts on the frames round the track", repr(p.near.text()))
    before = p.cost.text()
    p.whole.setChecked(True)
    check(p.frames() == (1, 24) and p.cost.text() != before, "choosing everything open changes what it says it will cost")
    p.near.setChecked(True)

    for box in p.slow.values():
        box.setChecked(False)
    check("less than a minute" in p.cost.text(), "with the two slow stages unticked the panel says it is quick")

    steps = []
    p.step.connect(lambda text, done, total: steps.append((text, done, total, p.bar.maximum())))
    with contextlib.redirect_stdout(io.StringIO()):
        p.go.click()                                      # the form's own button, not start(): clicked's bool must not reach `ask`
    check(not p.isVisible() and p.running() and w.steps[2].stage == "busy" and w.measure_button.text() == "Stop measuring",
          "once it starts the form goes (Jacob, 2026-09-25): step 3 has the bar, and its button is Stop measuring",
          f"{w.steps[2].stage}, {w.measure_button.text()!r}")
    got = QtTest_wait(lambda: p.sheet_path is not None and p.sheet is not None and p.sheet.isVisible(), 120)
    check(got and Path(p.sheet_path).exists() and p.running() and p.case is None and not (case / "planted_case.md").exists(),
          "the gate: the track sheet is made and shown, and nothing is measured from the track until the person answers",
          Path(p.sheet_path).name if got else "no sheet within 120 s")
    asked = " ".join(x.text() for x in p.sheet.findChildren(QtWidgets.QLabel)) if got else ""
    check("on the object in every frame" in asked, "with the question under it")
    check(p.bar.maximum() == 1 and p.now.text() == "Check track sheet" and "elapsed" in p.elapsed.text(),
          "while it waits for the person the bar is still and the panel says whose turn it is; the clock goes on", repr(p.now.text()[:40]))
    p.answer_sheet(True)
    done = QtTest_wait(lambda: not p.running() and p.case is not None, 180)
    check(done and not said[1:], "answered, it runs to the end", "; ".join(said[1:])[:120] or p.now.text())
    if not done:
        print(p.log.toPlainText()[-1500:])
        w.close()
        mark_qt.complain, measure_qt.complain = keep
        return
    counted = [x for x in steps if x[2]]
    check(counted and all(t.startswith("step ") and " of " in t for t, _, _, _ in counted)
          and any(d == n for _, d, n, _ in counted) and any(m == n for _, _, n, m in counted),
          "is it working, or has it hung? each long step says which stage it is and counts, and the bar counts with it",
          f"{len(counted)} counts over {len({t for t, _, _, _ in counted})} steps, e.g. {counted[-1][0]!r}")
    check(any(n is None and m == 0 for _, _, n, m in steps), "a step that cannot count shows the bar busy, not a bar that does not move")
    check(p.bar.maximum() == 1 and p.bar.value() == 1 and "in all" in p.elapsed.text() and p.now.text() == "done",
          "and at the end it is full, with the time it took", p.elapsed.text())
    check(p.case.clip["n1"] == 14, "the frames measured are the ones the panel said: round the track", f"{p.case.clip['n0']}–{p.case.clip['n1']}")
    md = (case / "planted_case.md").read_text(encoding="utf-8")
    card = w.report_card
    check(p.report is card and card.isVisible() and w.stack.currentWidget() is w.split and card.label.text() == "No physical conclusion"
          and "pixels a second" in card.headline.text() and not card.banner.isVisible() and card.facts.isVisible()
          and card.more_text.isHidden(),
          "and the report is a card in the right column, the video still in sight: the conclusion, the numbers found, More folded")
    card.more.click()
    check(card.more_text.isVisible() and "px/s" in card.more_text.text() and "Missing:" in card.more_text.text(),
          "More opens the bottom line and what is missing")
    card.more.click()
    w.do("report")
    text = w.report_page.page.toPlainText()
    check(w.report_page.isVisible() and w.stack.currentWidget() is w.report_page
          and text.index("Conclusion") < text.index("Summary of variables") < text.index("Missing quantities"),
          "Full report is the whole report, a page over the video, in the report's order")
    p.report = w.report_page                          # the checks below read the page
    from PySide6 import QtCore
    check("reviewed: yes (asked with the sheet on the screen)" in md and "provisional" not in md,
          "the report records that the sheet was examined, and how it knows")
    import re
    from PySide6 import QtCore
    folded = "Stage by stage" in p.report.page.toPlainText() and "_all_frames" not in p.report.page.document().toHtml()
    p.report.page.anchorClicked.emit(QtCore.QUrl("mcdonald:details/0"))        # open Measurements, as a person would
    check(folded and "▾ Stage by stage" in p.report.page.toPlainText(),
          "Measurements is folded at first, and the link under it opens it", p.report.page.toPlainText()[:0])
    pics = re.findall(r'<img[^>]*src="([^"]+)"[^>]*width="([0-9.]+)"', p.report.page.document().toHtml())
    check(pics and all(float(wd) <= measure_qt.PICTURE_WIDTH for _, wd in pics) and any("_all_frames" in src for src, _ in pics),
          "the pictures the steps drew are in the report page, under their step, the track sheet among them, none wider than "
          "the page", f"{len(pics)} pictures: " + ", ".join(src for src, _ in pics[:4]))
    from PySide6 import QtGui
    shown = QtGui.QPixmap(p.sheet_path)
    check(not shown.isNull() and shown.width() <= 1980 and measure_qt.sheet_layout(w.clip)["cols"] == 6,
          "the sheet is laid out for a screen: six tiles across, not the command line's thirty", f"{shown.width()}x{shown.height()}")
    long = type("Clip", (), dict(n0=1, n1=5291, W=1920, H=1080))
    lay = measure_qt.sheet_layout(long)
    check(-(-5291 // lay["cols"]) * round(lay["tile"] * 1080 / 1920) <= 32767,
          "and on a long clip it grows wider rather than taller than a pixmap can be", f"{lay['cols']} across for 5291 frames")
    check("[kinematics]" in p.log.toPlainText() and "v_px" in p.log.toPlainText(), "what the command line prints as it goes is in the panel")
    check("integrity" not in p.case.stages and "layers" not in p.case.stages and "kinematics" in p.case.stages,
          "the stages unticked were left out", ", ".join(p.case.stages))

    # the same case as the command line makes, from the same marks: it is the same function
    other = home / "by-command"
    rc, out, err = command("run", video, "--track", case / "planted_autotrack.csv", "--marks", case / "planted_marks.json", "--n0", 1, "--n1", 14,
                           "--out", other, "--workdir", frames, "--skip", "layers,integrity", "--size-px", 21, "--size", link.size,
                           *(["--dark"] if link.dark else []), "--i-looked", "--json")
    d = json.loads(out) if rc == 0 else None
    mine = {n: st["fields"] for n, st in p.case.stages.items()}
    theirs = (d or {}).get("results", {}).get("fields", {})
    strip = lambda f: json.loads(json.dumps(f, default=lambda v: v.tolist() if hasattr(v, "tolist") else str(v)).replace(str(other), "X").replace(str(case), "X"))
    check(d is not None and strip(mine) == strip(theirs) and mine["kinematics"]["v_px_per_s"] == theirs["kinematics"]["v_px_per_s"],
          "`mcdonald run` on the files the window saved gives the same fields in every stage, to the last digit",
          f"v_px {mine['kinematics']['v_px_per_s']!r}" if d else err[-300:])
    check(d is not None and d["results"]["bottom_line"] == p.case.bottom_line(), "and the same bottom line", p.case.bottom_line()[:90])

    # closing the sheet is "no"
    with contextlib.redirect_stdout(io.StringIO()):
        p.start()
    QtTest_wait(lambda: p.sheet is not None and p.sheet.isVisible(), 120)
    p.sheet.close()
    QtTest_wait(lambda: not p.running() and p.case is not None, 180)
    md = (case / "planted_case.md").read_text(encoding="utf-8")
    check("NOT CONFIRMED" in md and "provisional" in md and "confirmation that the track sheet was examined" in md,
          "a sheet closed without an answer is a no: the report calls the object measurements provisional, and says what would close it")
    shown = QtTest_wait(lambda: p.report is not None and p.report.isVisible() and p.report.looked.isVisible(), 10)
    fields_before = json.loads((case / "planted_case.json").read_text(encoding="utf-8"))["stages"]["kinematics"]["fields"]
    check(shown and p.report is w.report_card and w.report_card.banner.isVisible(),
          "measured again with the sheet closed, the card says the track is not yet checked by eye, with the button")
    if shown:
        w.do("report")                                # the page too, for the checks below: its banner and its text
        p.report = w.report_page
        p.report.looked.click()
    md = (case / "planted_case.md").read_text(encoding="utf-8")
    after = json.loads((case / "planted_case.json").read_text(encoding="utf-8"))["stages"]
    check(shown and "looked at afterwards" in md and "provisional" not in md and "NOT CONFIRMED" not in md
          and after["verify"]["fields"]["reviewed"] is True and after["kinematics"]["fields"] == fields_before
          and not p.report.looked.isVisible() and "Stage by stage" in p.report.page.toPlainText()
          and ("looked at afterwards" in p.report.page.toPlainText()) == (0 in getattr(p.report.page, "opened", set())),
          "looked at later, the sheet is confirmed from the report page: the case is read back and written again, "
          "nothing measured, and the page shows it")

    # stopping
    with contextlib.redirect_stdout(io.StringIO()):
        p.start()
    from PySide6 import QtWidgets as QW
    p.show()
    next(b for b in p.findChildren(QW.QToolButton) if b.text() == "✕").click()
    check(not p.isVisible() and p.running() and not p._stop.is_set(),
          "while it measures the ✕ only puts the panel away: it does not stop (on PR23 it did, and v_px was never measured)")
    w.measure_button.click()                              # step 3's Stop measuring
    check(p._stop.is_set() and not w.measure_button.isEnabled(), "Stop measuring stops it, and says it is stopping",
          repr(w.measure_button.text()))
    QtTest_wait(lambda: p.sheet is not None and p.sheet.isVisible() or not p.running(), 120)
    if p.sheet is not None:
        p.answer_sheet(False)
    QtTest_wait(lambda: not p.running() and p.case is not None, 120)
    check(p.case is not None and "kinematics" not in p.case.stages and "ingest" in p.case.stages and (case / "planted_case.md").exists()
          and "stopped" in p.log.toPlainText(), "Stop leaves the stages not yet run out, and the report is written of the ones that ran",
          ", ".join(p.case.stages) if p.case else "")
    check("The measuring was stopped" in (case / "planted_case.md").read_text(encoding="utf-8"),
          "and the report says where it was stopped, not that the missing numbers need something (PR23: v_px 'needs a track')")

    # and inside a stage: minutes of layers must not have to be waited out
    p.whole.setChecked(True)
    p.slow["layers"].setChecked(True)
    del steps[:]
    with contextlib.redirect_stdout(io.StringIO()):
        p.start()
    QtTest_wait(lambda: p.sheet is not None and p.sheet.isVisible() or not p.running(), 120)
    if p.sheet is not None:
        p.answer_sheet(True)
    in_layers = QtTest_wait(lambda: any(t.endswith("· Layers") and (d or 0) >= 1 for t, d, _, _ in steps) or not p.running(), 180)
    p.close()                                         # as the window does when it closes: the panel goes, and it is waited for
    ended = p.wait_for_the_step(120)
    QtTest_wait(lambda: not p.running() and p.case is not None, 120)
    check(ended and not p.running() and (p.report is None or not p.report.isVisible() or p.report.label.text()),
          "closed while it measures, the panel is waited for: the step ends and the report of what ran is written before the "
          "program may end (it was a daemon thread nothing waited for)")
    p.show()
    last = max((d for t, d, _, _ in steps if t.endswith("· Layers")), default=None)
    total = next((n for t, _, n, _ in steps if t.endswith("· Layers")), None)
    check(in_layers and p.case is not None and last is not None and last < total and "kinematics" not in p.case.stages
          and any("stopped before it finished" in why for _, why in p.case.stages.get("layers", {}).get("no_power", []))
          and "Stopped" in p.now.text(),
          "Stop during layers ends it there -- it does not have to be waited out -- and the report says that stage was stopped",
          f"stopped at pair {last} of {total}")
    p.slow["layers"].setChecked(False)

    if w.report_page is not None:
        w.report_page.close()
    w.do("report")
    check(w.report_page is not None and w.report_page.isVisible(), "Measure -> Show the case report opens it again later")
    row = next(a for a in actions.ACTIONS if a.id == "measure")
    check("track sheet" in row.help and "mcdonald run" in row.help, "and the menu's line of help says what Measure is, and that it asks about the sheet")
    p.close()
    w.measure_button.click()
    check(p.isVisible() and "(m)" in w.measure_button.toolTip(), "there is a button for it, the third step, its tip naming its key: what comes after the link")

    w.do("first_run")
    text = w.first_run_page.page.toPlainText()
    heads = [h for h, _ in actions.first_run()]
    check(w.first_run_page.isVisible() and all(h in text for h in heads) and text.index("Two clicks") < text.index("Link") < text.index("Measure"),
          "Help -> Getting started walks through the job in the order it is done", ", ".join(heads))
    named = {a.id: mark_qt.native_keys(actions.spoken(a.keys[0])) if a.keys else f"{a.menu} -> {a.text}"
             for a in actions.ACTIONS}                # ⌘ on a Mac; a row with no key is named by its menu
    import re
    used = set(re.findall(r"{(\w+)}", " ".join(t for _, t in actions.FIRST_RUN)))
    check(used and used <= set(named) and all(f"Press {named[i]}" in text or named[i] in text for i in used),
          "and every key it names is taken from the table the menus are made from", ", ".join(sorted(used)))
    w._closing = True
    w.close()
    mark_qt.complain, measure_qt.complain = keep


def drive_several(td):
    """More than one object in a video. Jacob, 2026-10-06, after Galileo flyer 1's four things: "Is
    there a way for the GUI to find/follow/measure multiple objects at once?" A report is about one
    object, so several objects are several reports: the rows ticked on Find's list each get a folder
    with their marks, and `several.run_each` -- what `mcdonald run --each` is a command line over --
    follows and measures them in turn. Nobody is asked about a track along the way; each report says
    so until someone has looked. Held to the command line: the same numbers from the same marks."""
    print("\nfinder: more than one object, a report each")
    import re
    from PySide6 import QtWidgets
    from mcdonald import find_qt, mark_qt, several, several_qt
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_cli import mcdonald as command, planted_video
    from test_measurement import TwoPlanted
    home = Path(td) / "several"
    home.mkdir()
    truth, video = planted_video(home, TwoPlanted(n1=24, seen=range(1, 25)), "two")
    case, frames = home / "case", home / "frames"
    said = []
    keep = mark_qt.complain, find_qt.complain, several_qt.complain
    mark_qt.complain = find_qt.complain = several_qt.complain = lambda parent, text: said.append(text)
    w = mark_qt.open_session(str(video), 1, 24, out=str(case), workdir=str(frames))
    w.show()

    def end():
        sp = w.several_panel
        for d in (sp.pages if sp is not None else []):
            d.close()
        w._closing = True
        w.close()
        mark_qt.complain, find_qt.complain, several_qt.complain = keep

    w.do("several")
    check(w.several_panel is not None and not w.several_panel.isVisible() and "no list of objects yet" in w.note.text()
          and not w.several_button.isVisible(),
          "before any object is chosen, Measure → The objects of this video says there is no list, and how to make one", repr(w.note.text()[:60]))
    w.do("find")
    p = w.find_panel
    got = QtTest_wait(lambda: not p.running() and len(p.proposals) >= 2 and p.go.isEnabled(), 240)
    on = lambda q, where: float(np.median([np.hypot(q.track[n][0] - where(n)[0], q.track[n][1] - where(n)[1]) for n in q.frames])) < 5.0
    both = [next((i for i, q in enumerate(p.proposals) if on(q, where)), None) for where in (truth.truth, truth.truth2)]
    ok = check(got and None not in both and both[0] != both[1], "Find lists both of the things that move", f"rows {both} of {len(p.proposals)}")
    if not ok:
        end()
        return
    check(all(not r.tick.isChecked() for r in p.rows) and not p.several_bar.isVisible() and "more than one object" in p.what.text(),
          "each row can be ticked as one of several; none is at first, and the words above the list say what a tick is for")
    p.rows[both[0]].tick.setChecked(True)
    check(p.several_bar.isVisible() and p.several_text.text().startswith("1 ticked"), "a tick brings up the button under the list",
          repr(p.several_text.text()))
    p._show(p.proposals)                              # the list drawn again, as it is each time the search reports: the tick stays
    check(p.rows[both[0]].tick.isChecked(), "a tick outlives the list being drawn again")
    p.rows[both[1]].tick.setChecked(True)
    check(p.several_text.text().startswith("2 ticked") and find_qt.SEVERAL == p.several_go.text(), "two ticked, and it says so",
          repr(p.several_text.text()))
    p.several_go.click()
    sp = w.several_panel
    ok = check(sp is not None and sp.isVisible() and not p.isVisible() and sorted(sp.rows) == [1, 2] and sp.running() and not w.ms.count(),
               "the button puts Find away and opens the list of objects, which starts on the first; the window's own marks are not touched")
    if not ok:
        end()
        return
    ms1 = mark.MarkSet("two", str(video), 30.0).load(case / "object-1" / "two_marks.json")
    obj1 = ms1.marks.get("object", {})
    check(sorted(d.name for d in case.iterdir() if d.is_dir()) == ["object-1", "object-2"] and len(obj1) >= 2
          and {ms1.kind("object", n) for n in obj1} == {"proposed"} and "accepted at the window by a person" in ms1.how_of("object", min(obj1))
          and (case / "object-2" / "two_marks.png").exists(),
          "each ticked row is a folder under the video's, with its marks saved as proposed and the strip that shows them")
    # Stop, at once: the object under way ends where it is, the next is left as it is
    QtTest_wait(lambda: sp._now is not None or not sp.running(), 60)
    sp.halt.click()
    QtTest_wait(lambda: not sp.running(), 240)
    states = {k: re.sub(r"<[^>]+>", "", r.state.text()) for k, r in sp.rows.items()}
    check("Stopped before it was finished" in states[1] and "Not measured yet" in states[2] and sp.go.isVisible() and "(2)" in sp.go.text()
          and not sp.halt.isVisible() and (case / "object-1" / "two_case.md").exists() and not (case / "object-2" / "two_case.md").exists(),
          "Stop ends the step under way: the first object's report covers the steps that ran, the second is left as it is, and "
          "one button offers the rest", f"{states}; {sp.go.text()!r}")
    sp.go.click()
    done = QtTest_wait(lambda: not sp.running() and all(several.measured(r.thing) for r in sp.rows.values()), 900)
    states = {k: re.sub(r"<[^>]+>", "", r.state.text()) for k, r in sp.rows.items()}
    ok = check(done and not said and all("Done: followed on" in x and "has not been looked at yet" in x for x in states.values())
               and all(r.report.isVisible() for r in sp.rows.values()) and "2 of 2 reports are ready" in sp.now.text(),
               "pressed, it follows and measures both to the end, and each row says how far its object was followed",
               f"{states}" + (f"; {said[-1][:80]}" if said else ""))
    if not ok:
        end()
        return
    check(w.steps[0].stage == "done" and "2 objects chosen" in w.steps[0].state.text() and w.steps[2].stage == "done"
          and "2 of 2 reports are ready" in w.steps[2].state.text() and w.several_button.isVisible(),
          "the three steps say how the objects stand, and step 3 has the button that shows them", repr(w.steps[2].state.text()))
    rc, out, err = command("run", video, "--marks", case / "object-1" / "two_marks.json", "--n0", 1, "--n1", 24, "--out", home / "alone",
                           "--workdir", frames, "--skip", "integrity", "--json")
    try:
        one, queued = json.loads(out), json.loads((case / "object-1" / "two_case.json").read_text(encoding="utf-8"))
        same = all(one["results"]["fields"][s] == queued["stages"][s]["fields"] for s in ("kinematics", "layers", "flicker", "groups"))
        v = queued["stages"]["kinematics"]["fields"].get("v_px_per_s")
    except (ValueError, KeyError) as ex:
        same, v = False, repr(ex)
    check(rc == 0 and same, "an object measured from the window's list is that object measured by `mcdonald run --marks`: the same "
                            "numbers, to the digit", f"v = {v} px/s")
    # the list as a page, and a track sheet looked at afterwards
    page = sp.show_list()
    text = page.page.toPlainText() if page is not None else ""
    check("Object 1" in text and "Object 2" in text and text.count("not looked at yet") == 2,
          "Open the list shows one page that lists them, each with its track sheet not yet looked at", text[:60].replace("\n", " "))
    d = sp.open_report(1)
    check(d is not None and d.banner.isVisible(), "an object's report opens as any report does, with the line at its top that "
                                                  "nobody has said its track sheet shows the object")
    d.looked.click()
    QtTest_wait(lambda: "You have looked" in sp.rows[1].state.text(), 10)
    check(not d.banner.isVisible() and "You have looked at its track sheet" in sp.rows[1].state.text()
          and "has not been looked at yet" in sp.rows[2].state.text()
          and (case / "two_objects.md").read_text(encoding="utf-8").count("not looked at yet") == 1,
          "said there, it is said in the report, in that object's row, and in the list on disk")
    # one of them brought into the window, for the work only a hand can do
    sp.rows[2].bring.click()
    obj = w.ms.marks.get("object", {})
    check(Path(w.out).parent == case / "object-2" and len(obj) >= 2 and {w.ms.kind("object", n) for n in obj} == {"proposed"}
          and "Object 2 is open here" in w.note.text(),
          "Open in the window brings an object's marks into the window, which then saves to that object's folder", repr(w.note.text()[:50]))
    QtTest_wait(lambda: not w.linking() and w.links.get(0) is not None and w.links[0].done, 90)
    link = w.links.get(0)
    second = truth.truth if both[0] > both[1] else truth.truth2       # the objects are numbered in the list's order: object 2 is the lower row
    off = max((np.hypot(x - second(n)[0], y - second(n)[1]) for n, (x, y) in link.track.items()), default=99.0) if link else 99.0
    check(link is not None and len(link.track) >= 8 and off < 3.0 and sp.base == case,
          "and follows it there, on that object; the list still belongs to the video's own folder", f"{len(link.track) if link else 0} frames, worst {off:.1f} px")
    texts = []
    for root in (sp, p):
        for x in [root] + root.findChildren(QtWidgets.QWidget):
            texts += [x.toolTip()] + [getattr(x, name)() for name in ("text", "placeholderText") if callable(getattr(x, name, None))]
    texts = [re.sub(r"<[^>]+>", " ", x) for x in texts if x and x.strip()]
    found = sorted({(re.search(pat, x, re.I if pat != r"\bDN\b" else 0).group(0), x[:50]) for x in texts for pat in TRADE_WORDS
                    if re.search(pat, x, re.I if pat != r"\bDN\b" else 0)})
    check(len(texts) > 20 and not found, "and what the list and the ticks say is in plain words, as the rest of the window is",
          f"{len(texts)} pieces of text; " + "; ".join(f"{a!r} in {b!r}" for a, b in found[:4]))
    end()


def drive_one_window(td):
    """One window (Jacob, 2026-10-07: "minimize pop-up windows whenever possible ... keep everything inside
    the main window"). The window opens with nothing in it and the start screen as a small dialog over it; a
    video opens into it in place -- which part of it is asked on a page of the window, the wait for its frames
    is a page too -- and so does the next one; the report, the overview, the strip after a save and Help are
    pages over the video, with the video's own keys off while one is in front; and the only windows of their
    own are the desktop's file dialogs, the alerts and About."""
    print("\nfinder: one window")
    from PySide6 import QtCore, QtWidgets
    from mcdonald import mark_qt
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    video, cases = Path(td) / "drawn.mp4", Path(td) / "cases"
    if not video.exists():                            # drive_extraction draws it first in the suite; alone (tools/drive_one.py), here
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30000/1001",
                        "-frames:v", "90", "-pix_fmt", "yuv420p", str(video)], check=True)
    said, keep = [], mark_qt.complain
    mark_qt.complain = lambda parent, text: said.append(text)
    w = mark_qt.QtMarker(cases=str(cases), workdir=f"{td}/frames3")
    w.show()
    QtTest_wait(w.isVisible, 5)
    check(w.clip is None and w.stack.currentWidget() is w.home and not w.side.isEnabled() and w.windowTitle() == "mcDonald"
          and "Open a video" in w.home.hint.text(),
          "the window opens with nothing in it: a home page, the side panel grey, a line saying what to do")
    live = {i for i, a in w.acts.items() if a.isEnabled()}
    check(live == mark_qt.ANYTIME, "and only the keys that need no video are live", str(sorted(live)))

    home = w.home
    check(home.isVisible() and home.open_button.isVisible() and home.catalog_button.isVisible() and "saved to" in home.where.text()
          and " free)" in home.where.text() and home.change.isVisible() and home.recent_box.isVisible() == bool(home.recent_buttons)
          and not [x for x in QtWidgets.QApplication.topLevelWidgets() if x.isVisible() and x is not w and not isinstance(x, mark_qt.QtMarker)],
          "the home page is the start screen: what this is, the two ways to open a video, where the data goes, the recent "
          "videos when there are any; and no dialog over it (Jacob, 2026-10-08)")
    seen = []

    # a video into it, in place: the segment chosen on a page, the frames saved behind a bar on a page
    busy, was = [], mark_qt.show_busy
    mark_qt.show_busy = lambda parent, box: busy.append((parent is w, box.title_)) or was(parent, box)
    Open = QtWidgets.QDialogButtonBox.StandardButton.Open

    def on_chooser(fn):
        def poll():
            d = w.chooser
            if d is not None and w.stack.currentWidget() is d:
                fn(d)
            else:
                QtCore.QTimer.singleShot(60, poll)
        QtCore.QTimer.singleShot(60, poll)

    def pick(d):
        seen.append(("page", w.acts["play"].isEnabled(), w.acts["quit"].isEnabled(), w.side.isEnabled()))
        d.first.setValue(5)
        d.last.setValue(30)
        d.buttons.button(Open).click()
    del seen[:]
    on_chooser(pick)
    got = mark_qt.open_session(str(video), workdir=f"{td}/frames3", cases=str(cases), window=w)
    mark_qt.show_busy = was
    check(got is w and w.clip is not None and (w.clip.n0, w.clip.n1) == (5, 30) and w.stack.currentWidget() is w.split
          and seen == [("page", False, True, False)] and w.side.isEnabled() and w.windowTitle() == "drawn — mcDonald",
          "the video opens into the same window: which part of it was a page here, with the video's keys off and the side "
          "panel grey, and the window then shows it", f"{seen}")
    check(busy == [(True, "Saving the frames as pictures")] and w.clip.n_extracted() == 26,
          "the frames were saved behind a bar on a page of the window", str(busy))
    # another video: the chooser cancelled leaves the first; chosen, the second takes its place
    second = Path(td) / "second.mp4"
    shutil.copy(video, second)
    seen = []
    on_chooser(lambda d: seen.append((w.clip, w.side.isEnabled(), w.report_card.isVisible()))
               or d.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).click())
    w.open_clip(str(second))
    check(seen == [(None, False, False)] and w.clip is None and w.stack.currentWidget() is w.home and w.chooser is None,
          "File -> Open a video: the one that was open goes first, so the column is reset while the next is chosen "
          "(Jacob, 2026-10-07); cancelled on its page, the window stays empty", str(seen))
    on_chooser(lambda d: (d.first.setValue(1), d.last.setValue(12), d.buttons.button(Open).click()))
    w.open_clip(str(second))
    check(w.ms.tag == "second" and (w.clip.n0, w.clip.n1) == (1, 12) and w.isVisible() and w.stack.currentWidget() is w.split,
          "opened, the second takes the first one's place in the same window")
    tops = [x for x in QtWidgets.QApplication.topLevelWidgets() if x.isVisible() and x.isWindow()]
    others = [x for x in tops if not isinstance(x, mark_qt.QtMarker)]        # the suite's own rig is a main window too
    check(w in tops and not others and not said,
          "through all of that, no window but the main one is open -- nothing was left as a dialog -- and nothing was complained of",
          ", ".join(type(x).__name__ for x in tops) + ("; " + said[-1][:80] if said else ""))
    w._closing = True
    w.close()
    mark_qt.complain = keep


def drive_one_button(td):
    """One press (Jacob, 2026-10-07: "an all-in-one button press option that goes through all steps without
    asking for any confirmations ... Users can choose an 'advanced' mode"). On the planted video: the side
    panel opens simple, with the one button and the three steps hidden; the button finds the object, takes
    the first row of Find's list, follows it and measures it, asking nothing; the marks say the run took them;
    the report opens on a page of the window and says its numbers are not yet sure; Advanced shows the three
    steps, all done. Then: pressed again it measures again, and Stop stops it; and on a part where nothing
    moves it stops with a sentence that points at Advanced."""
    print("\nfinder: one button")
    from mcdonald import actions, find_qt, mark_qt, measure_qt
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_cli import planted_video
    home = Path(td) / "one-button"
    home.mkdir()
    truth, video = planted_video(home)
    case, frames = home / "case", home / "frames"
    said = []
    keep = mark_qt.complain, find_qt.complain, measure_qt.complain
    mark_qt.complain = find_qt.complain = measure_qt.complain = lambda parent, text: said.append(text)
    mark_qt.settings().remove("panel/advanced")      # as a person meets it: the rig's drivers turned Advanced on, and it is remembered
    w = mark_qt.open_session(str(video), 1, 24, out=str(case), workdir=str(frames))
    w.show()
    card = w.auto_card
    check(not w.advanced and w.steps_box.isHidden() and card.isVisible() and card.button.isEnabled()
          and card.button.text() == "Find, follow and measure the object" and "(a)" in card.button.toolTip() and not w.auto.running(),
          "the side panel opens simple: one button, the three steps hidden, its tip naming its key", card.button.text())
    row = next(a for a in actions.ACTIONS if a.id == "auto")
    check(row.menu == "Track" and "Nothing is asked" in row.help and next(a for a in actions.ACTIONS if a.id == "advanced").check,
          "it is a row of the table, in the Track menu with its line of help; Advanced is a row of View, ticked or not")
    card.button.click()
    check(w.auto.running() and w.auto.stage == "find" and card.button.text() == "Stop" and card.busy.isVisible()
          and card.state.isVisible() and "Step" not in card.state.text() and "elapsed" not in card.state.text(),
          "pressed, it is finding the object: a moving bar, a Stop, and the step's own line with no step number and no clock",
          card.state.text()[:60])
    check((w.find_panel is None or not w.find_panel.isVisible()) and w.work.isHidden() and w.note.isHidden() and w.note.quiet,
          "and nothing pops up under or over the video: the list is not a choice to make (Jacob, 2026-10-07)")
    check(card.lights.stages == ["busy", "todo", "todo"] and card.lights.isVisible() and w.advanced_toggle.isHidden() and not w.advanced,
          "the first of three lights under the button is lit as under way, and the Advanced line is no longer offered",
          str(card.lights.stages))
    got = QtTest_wait(lambda: w.auto.stage in ("link", "measure") or not w.auto.running(), 300)
    hows = [w.ms.how_of("object", n) or "" for n in w.ms.frames("object")]
    check(got and w.auto.running() and {w.ms.kind("object", n) for n in w.ms.frames("object")} == {"proposed"}
          and hows and all("one-press run" in h for h in hows),
          "found: the first row of the list is taken, its marks saved as proposed and recorded as the run's, with nobody looking",
          hows[0][:90] if hows else w.auto.why)
    got = QtTest_wait(lambda: w.auto.stage == "measure" or not w.auto.running(), 300)
    link = w.links.get(0)
    worst = max((np.hypot(x - truth.truth(n)[0], y - truth.truth(n)[1]) for n, (x, y) in link.track.items()), default=99.0) \
        if link is not None and link.track else 99.0
    check(got and w.auto.running() and link is not None and len(link.track) >= 8 and worst < 3.0,
          "followed, on the planted object, and measuring without a question",
          f"{len(link.track) if link is not None else 0} frames, worst {worst:.1f} px; {w.auto.why}")
    check(card.lights.stages[2] == "busy" and "elapsed" not in card.state.text() and "left" not in card.state.text(),
          "the third light says which step it is on, and the line has no clock", card.state.text()[:60])
    done = QtTest_wait(lambda: not w.auto.running(), 600)
    mp = w.measure_panel
    ok = check(done and not said and mp is not None and mp.case is not None and (case / "planted_case.md").exists() and w.auto.why == "",
               "it runs to the end, and the report is written", "; ".join(said)[:120] or w.auto.why)
    if not ok:
        w._closing = True
        w.close()
        mark_qt.complain, find_qt.complain, measure_qt.complain = keep
        return
    md = (case / "planted_case.md").read_text(encoding="utf-8")
    check("NOT CONFIRMED" in md and "provisional" in md and mp.sheet is None,
          "nothing was asked: the report says its numbers are not yet sure, as the command line's does without --i-looked")
    d = w.report_card
    check(mp.report is d and d.isVisible() and w.stack.currentWidget() is w.split and d.banner.isVisible() and d.looked.isVisible(),
          "the report is a card in the right column under the button, the video still in sight, with the line that nobody "
          "has checked the track by eye")
    check(d.label.text() == "No physical conclusion" and d.badge.text() == "≈" and "pixels a second" in d.headline.text()
          and d.facts.isVisible() and d.more_text.isHidden() and d.full.isVisible(),
          "a badge and the label, the one sentence, the numbers found, More folded, and the full report a press away",
          d.headline.text()[:80])
    check(card.state.isHidden() and card.button.text() == "Measure again",
          "the one-button card says nothing more: the report's card speaks for itself", card.state.text())
    d.looked.click()
    QtTest_wait(lambda: not d.banner.isVisible(), 10)
    check(not d.banner.isVisible() and "provisional" not in (case / "planted_case.md").read_text(encoding="utf-8"),
          "the sheet looked at afterwards is said on the card, and the report on disk follows")
    d.full.click()
    text = w.report_page.page.toPlainText() if w.report_page is not None else ""
    check(w.report_page is not None and w.report_page.isVisible() and text.index("Conclusion") < text.index("Summary of variables")
          and not w.report_page.banner.isVisible(), "Full report opens the whole report over the video, its conclusion first")
    w.report_page.close()
    check(w.track_strip is None and bool(w._strips) and not w.note.quiet and w.note.isHidden() and w.work.isHidden(),
          "through the run nothing was put under the video -- not the track's check either -- and nothing said over it")
    check(card.lights.stages == ["done", "done", "done"] and all(b.text() == "✓" for b in card.lights.badges),
          "and the three lights are lit as done", str(card.lights.stages))
    w.do("advanced")
    check(w.advanced and w.steps_box.isVisible() and [st.stage for st in w.steps] == ["done", "next", "done"]
          and "chosen from what Find showed" in w.steps[0].state.text() and "Press “Check the track”" in w.steps[1].state.text()
          and w.check_button.isVisible() and w.acts["advanced"].isChecked(),
          "Advanced shows the three steps, and they say what the run did: found from Find's list, the track followed with its "
          "pictures behind Check the track (not asked), measured", str([st.stage for st in w.steps]))
    w.check_button.click()
    check(w.track_strip is not None and w.track_strip.isVisible() and w.steps[1].state.text() == "Check the track below the video",
          "pressed, the pictures along the track come under the video, as after Follow")
    w.track_strip.close()
    w.set_advanced(False)
    # pressed again with a track, it measures again; and Stop stops it
    card.button.click()
    check(w.auto.running() and w.auto.stage == "measure" and card.button.text() == "Stop", "pressed again with a track, it measures again")
    card.button.click()
    QtTest_wait(lambda: not w.auto.running() and not mp.running(), 180)
    check(not w.auto.running() and w.auto.why == "Stopped." and card.state.text() == "Stopped.", "and Stop stops it, and says so",
          card.state.text())
    w._closing = True
    w.close()

    # a part where nothing moves: it stops with a sentence, and points at Advanced
    w2 = mark_qt.open_session(str(video), 13, 24, out=str(home / "still"), workdir=str(frames))
    w2.show()
    w2.auto_card.button.click()
    got = QtTest_wait(lambda: not w2.auto.running(), 300)
    check(got and "Nothing was found" in w2.auto.why and "Advanced" in w2.auto.why and w2.auto_card.state.text() == w2.auto.why
          and not w2.ms.count() and w2.advanced_toggle.isVisible(),
          "where nothing moves, the run stops with a sentence that says so and points at Advanced, whose line is back under the button",
          w2.auto.why[:80])
    w2._closing = True
    w2.close()

    # several things worth following (Galileo flyer 1 has four): each a folder and a report, nothing asked, nothing shown
    from test_measurement import TwoPlanted
    from mcdonald import several
    truth2, video2 = planted_video(home, TwoPlanted(n1=24, seen=range(1, 25)), "two")
    case2, frames2 = home / "two-case", home / "two-frames"
    w3 = mark_qt.open_session(str(video2), 1, 24, out=str(case2), workdir=str(frames2))
    w3.show()
    w3.auto_card.button.click()
    got = QtTest_wait(lambda: w3.auto.stage == "several" or not w3.auto.running(), 300)
    check(got and w3.auto.running() and w3.auto.stage == "several" and not w3.ms.count() and w3.auto_card.lights.stages == ["done", "busy", "busy"]
          and (w3.several_panel is None or not w3.several_panel.isVisible()) and w3.work.isHidden() and not w3.advanced,
          "with two things worth following, the run takes both as a queue of cases, shows nothing, and the lights say so",
          f"{w3.auto.stage}; {w3.auto.why}")
    done = QtTest_wait(lambda: not w3.auto.running(), 900)
    things = several.things(case2)
    check(done and len(things) == 2 and all(t.report is not None for t in things) and w3.auto.why == ""
          and w3.auto_card.lights.stages == ["done", "done", "done"] and w3.auto_card.button.text() == "Measure again",
          "both are followed and measured in turn, each with a report, and the lights are lit", f"{len(things)} objects; {w3.auto.why}")
    ms2 = lambda t: mark.MarkSet("two", str(video2), 30.0).load(t.marks)
    hows = [ms2(t).how_of("object", n) or "" for t in things for n in ms2(t).frames("object")]
    check(hows and all("one-press run" in h for h in hows), "their marks say the run took them, with nobody looking", hows[0][:90] if hows else "")
    check(sorted(w3.object_cards) == [1, 2] and all(c.isVisible() and c.banner.isVisible() and c.label.text() for c in w3.object_cards.values())
          and not w3.report_card.isVisible() and w3.stack.currentWidget() is w3.split,
          "and the column has a report card for each, the track not yet checked by eye on either, the video still in sight",
          str({k: c.label.text() for k, c in w3.object_cards.items()}))
    both = [n for n in range(1, 25) if all(n in t for t in w3.object_tracks.values())]
    w3.goto(both[0] if both else 8)
    check(sorted(w3.object_tracks) == [1, 2] and sorted(w3._object_paths) == [1, 2] and sorted(w3.object_boxes) == [1, 2]
          and {b.label for b in w3.object_boxes.values()} == {"1", "2"} and len({b.colour for b in w3.object_boxes.values()}) == 2,
          "and each object's track is drawn on the video, a line in its own colour and a box with its number on its frames "
          "(Jacob, 2026-10-08: the tracks did not show)", f"frames shared: {both[:3]}")
    c1 = w3.object_cards[1]
    first = c1.first_frame()
    w3.goto(24)
    from PySide6 import QtCore, QtTest
    from PySide6.QtCore import Qt
    QtTest.QTest.mouseClick(c1, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QtCore.QPoint(10, 10))
    check(first is not None and w3.n == first, "a click on an object's card goes to where its track starts", f"{w3.n} for {first}")
    c1.looked.click()
    QtTest_wait(lambda: not c1.banner.isVisible(), 10)
    check(not c1.banner.isVisible() and w3.object_cards[2].banner.isVisible()
          and (case2 / "two_objects.md").read_text(encoding="utf-8").count("not looked at yet") == 1,
          "I looked on one card is that object's sheet looked at: its card, its report and the list on disk say so, the other not")
    w3._closing = True
    w3.close()
    # told how many to look for (the segment step, 2026-10-08): one is the single path, the first row only; three is the queue
    # of what there is, the count held against it in the run's last line
    case5, frames5 = home / "two-case-one", home / "two-frames"
    w5 = mark_qt.open_session(str(video2), 1, 24, out=str(case5), workdir=str(frames5))
    w5.show()
    w5.objects_expected = 1
    w5.auto_card.button.click()
    got = QtTest_wait(lambda: w5.auto.stage in ("link", "measure") or not w5.auto.running(), 300)
    check(got and w5.auto.running() and w5.auto.stage in ("link", "measure") and w5.ms.count() and not several.things(case5),
          "looking for one object, the run takes the first row alone, as a single case, though two things were found",
          f"{w5.auto.stage}; {w5.auto.why}")
    w5.auto.stop()
    QtTest_wait(lambda: not w5.auto.running(), 120)
    w5._closing = True
    w5.close()
    case6 = home / "two-case-three"
    w6 = mark_qt.open_session(str(video2), 1, 24, out=str(case6), workdir=str(frames5))
    w6.show()
    w6.objects_expected = 3
    w6.auto_card.button.click()
    got = QtTest_wait(lambda: w6.auto.stage == "several" or not w6.auto.running(), 300)
    check(got and w6.auto.running() and w6.auto.stage == "several", "looking for three, both things found go to the queue", w6.auto.why)
    done = QtTest_wait(lambda: not w6.auto.running(), 900)
    text = (case6 / "two_objects.md").read_text(encoding="utf-8") if (case6 / "two_objects.md").exists() else ""
    check(done and w6.auto.why == "You looked for 3 objects: 2 were followed; 1 was not found." and w6.auto_card.state.text() == w6.auto.why
          and "**You looked for 3 objects: 2 were followed; 1 was not found.**" in text and len(several.things(case6)) == 2,
          "and at the end the count is held against what was followed, under the button and on the list, with nothing invented",
          w6.auto.why or text[:80])
    w6._closing = True
    w6.close()
    mark_qt.complain, find_qt.complain, measure_qt.complain = keep


def QtTest_wait(cond, seconds):
    from PySide6 import QtWidgets
    end = time.monotonic() + seconds * PATIENCE
    while not cond() and time.monotonic() < end:
        QtWidgets.QApplication.processEvents()        # not QTest.qWait: it holds the GIL, and the threads waited for starve
        time.sleep(0.005)
    return bool(cond())


def drive(target):
    """The child: open one window and press everything."""
    qt = target == "PySide6"
    import atexit
    cfg = tempfile.mkdtemp(prefix="mcdonald-test-config-")     # QSettings: not the person's own, and not left behind
    atexit.register(shutil.rmtree, cfg, ignore_errors=True)
    os.environ["XDG_CONFIG_HOME"] = cfg
    try:
        if qt:
            from mcdonald import mark_qt
            mark_qt.application()
        else:
            import matplotlib
            matplotlib.use(target, force=True)
            import matplotlib.pyplot as plt
            plt.close(plt.figure())
    except Exception as ex:                       # ImportError, or whatever the toolkit raises
        print(f"{type(ex).__name__}: {(str(ex).splitlines() or [''])[0]}")
        return CANNOT_OPEN
    print(UP, flush=True)
    Rig = QtRig if qt else MplRig
    with tempfile.TemporaryDirectory() as td:
        clip = SyntheticClip()
        rig = Rig(clip, mark.MarkSet("synthetic", "/nowhere/synthetic.mp4", clip.fps), f"{td}/synthetic")

        def new_rig(ms):
            return Rig(clip, ms, f"{td}/{ms.tag}")
        print(f"\n== {target}: {rig.describe()}")
        drive_the_window(rig)
        drive_stepping(rig)
        drive_two_clicks(rig)
        drive_classes(rig)
        drive_every_key(rig)
        drive_zoom_and_pan(rig)
        drive_pixels_are_where_the_coordinates_say(rig)
        if qt:
            drive_the_menus(rig)
            drive_plain_words(rig)
            drive_the_finder(rig, new_rig)
            drive_finding(new_rig)
            drive_extraction(td)
            drive_getting_in(td)
            drive_one_window(td)
            drive_the_first_screen_and_memory(td)
            drive_measuring(td)
            drive_several(td)
            drive_one_button(td)
            drive_what_is_known(td)
        saved = drive_saving(rig, new_rig)
        # what the two windows put on disk from the same clicks, for the harness to compare
        print(SAVED + json.dumps(saved, sort_keys=True), flush=True)
    return 1 if FAIL else 0


def drive_what_is_known(td):
    """What the person knows of the video that its pixels cannot say (Jacob, 2026-10-09: "we need to prompt the
    user to ask if any additional quantities are known (FOV, object of known reference size, range to object,
    etc.)"). Asked on the segment step, folded under the count, with a ruler on the player for the thing of known
    size; remembered for the video and taken by the one press, which asks nothing. Asked again on the report card
    where the report could not give a real speed: the speed is then worked out again and nothing measured again --
    what `mcdonald report CASE --range ...` gives on the same case, to the last digit -- and the card says what
    the speed rests on, with a way to change it."""
    print("\nfinder: what is known of the video")
    import re
    from PySide6 import QtCore, QtTest, QtWidgets
    from PySide6.QtCore import Qt
    from mcdonald import find_qt, known_qt, mark_qt, measure_qt
    if shutil.which("ffmpeg") is None:
        print("  SKIP  ffmpeg is not installed")
        return
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_cli import mcdonald as command, planted_video
    home = Path(td) / "what-is-known"
    home.mkdir()
    truth, video = planted_video(home)
    case, frames = home / "case", home / "frames"
    said = []
    keep = mark_qt.complain, find_qt.complain, measure_qt.complain
    mark_qt.complain = find_qt.complain = measure_qt.complain = lambda parent, text: said.append(text)
    for key in ["panel/advanced", f"known/{video.name}"] + [f"known_units/{k}" for k in ("range", "ref", "ground", "own")]:
        mark_qt.settings().remove(key)
    plain = lambda text: not any(re.search(pat, text, re.I if pat != r"\bDN\b" else 0) for pat in TRADE_WORDS)

    # the segment step: folded under the count; a thing of known size needs both its lengths, one measured on the player
    w0 = mark_qt.QtMarker(cases=str(home / "cases"))
    w0.show()
    clip = vf.Clip(video, str(frames), extract=False)
    seen = {}
    Open = QtWidgets.QDialogButtonBox.StandardButton.Open

    def fill(d):
        k = d.known
        seen["folded"] = k.isHidden() and d.known_toggle.text() == d.KNOWN and not d.known_toggle.isChecked()
        d.known_toggle.click()
        seen["units"] = tuple(k.units[n].currentText() for n in ("range_m", "ref_m", "ground_speed", "own_ship"))
        k.edits["fov"].setText("30")
        k.edits["range_m"].setText("5")
        k.edits["ref_m"].setText("60")
        seen["label"] = d.known_toggle.text()
        seen["words"] = all(plain(x.text()) for x in k.findChildren(QtWidgets.QLabel)) and all(
            plain(x.toolTip()) for x in k.findChildren(QtWidgets.QWidget))
        d.buttons.button(Open).click()
        seen["refused"] = (d._done is None, d.known_said.isVisible(), d.known_said.text())
        QtTest_wait(lambda: d.preview.pixmap() is not None, 10)
        k.ruler.click()
        r = d.preview.drawn()
        a, b = r.topLeft() + QtCore.QPoint(40, 50), r.topLeft() + QtCore.QPoint(160, 100)
        QtTest.QTest.mousePress(d.preview, Qt.MouseButton.LeftButton, pos=a)
        QtTest.QTest.mouseMove(d.preview, b)
        QtTest.QTest.mouseRelease(d.preview, Qt.MouseButton.LeftButton, pos=b)
        per = d.preview.pixmap().width() / r.width() * clip.W / d.reel.w
        seen["ruled"] = (float(k.edits["ref_px"].text() or 0), math.hypot(120, 50) * per)
        d.buttons.button(Open).click()

    def poll():
        d = w0.chooser
        if d is not None and w0.stack.currentWidget() is d:
            fill(d)
        else:
            QtCore.QTimer.singleShot(60, poll)
    QtCore.QTimer.singleShot(60, poll)
    got = mark_qt.choose_range(clip, w0)
    rem = known_qt.remembered(clip)
    check(seen.get("folded") and seen["units"] == ("miles", "feet", "miles an hour", "knots") and seen["label"].endswith("— 3 given")
          and seen["words"], "the segment step asks what else is known, folded under the count until opened, in plain words and "
          "the units a person thinks in, and says how many are given", f"{seen.get('units')}; {seen.get('label')!r}")
    check(seen["refused"][0] and seen["refused"][1] and "give both" in seen["refused"][2],
          "a thing of known size without its length on the screen is refused under the form, and nothing opens yet",
          seen["refused"][2])
    check(abs(seen["ruled"][0] - seen["ruled"][1]) < 0.15, "its length on the screen is measured on the player, in the video's "
          "own pixels", f"{seen['ruled'][0]:.1f} for {seen['ruled'][1]:.2f}")
    check(got == (1, 24) and rem == {"fov": 30.0, "range_m": 5 * 1609.344, "ref_m": 60 * 0.3048, "ref_px": seen["ruled"][0]},
          "and what was given is remembered for the video, in meters", str(rem))
    w0._closing = True
    w0.close()

    # the one press takes it, and asks nothing
    w = mark_qt.open_session(str(video), 1, 24, out=str(case), workdir=str(frames))
    w.show()
    check(w.known_values == rem, "the video opens with what is known of it")
    w.auto_card.button.click()
    done = QtTest_wait(lambda: not w.auto.running(), 600)
    mp, d = w.measure_panel, w.report_card
    data = json.loads((case / "planted_case.json").read_text(encoding="utf-8")) if (case / "planted_case.json").exists() else {}
    st = data.get("stages", {})
    ok = check(done and not said and mp is not None and all(st["ingest"]["fields"]["known"].get(n) == v for n, v in rem.items())
               and st["kinematics"]["fields"]["relative_speed_m_per_s"] is not None
               and "ASSUMED field of view of 30" in st["scale"]["fields"]["k_from"]
               and mp.fields["fov"].text() == "30" and mp.fields["range_m"].text() == "8046.72",
               "the one press takes it, asking nothing: the report has the field of view and the range, and a speed; the "
               "Measure form shows them", "; ".join(said)[:120] or w.auto.why)
    if not ok:
        w._closing = True
        w.close()
        mark_qt.complain, find_qt.complain, measure_qt.complain = keep
        return
    check(d.ask.isVisible() and d.ask_text.text().startswith("Worked out from what you gave: the camera sees 30 degrees across, "
                                                             "the object is 5 miles away, a thing 60 feet long is")
          and d.ask_button.text() == "Change" and "m/s" in d.headline.text() and plain(d.ask_text.text()),
          "the card says what the speed rests on, in the units given, with a way to change it", d.ask_text.text()[:110])

    # Change: emptied, worked out again -- the card asks
    d.ask_button.click()
    check(d.known.isVisible() and d.known.edits["fov"].text() == "30" and d.known.edits["range_m"].text() == "5"
          and d.known.units["range_m"].currentText() == "miles" and d.known_buttons.isVisible() and d.ask_button.isHidden(),
          "Change opens the same questions in the card, filled with what the report was worked out with")
    d.known.ruler.click()
    check(w.view.ruler and d.known.ruler.text() == "Measure on the video", "and its ruler is the window's, on the video beside it")
    w.stop_ruler()
    for n in ("range_m", "ref_m", "ref_px"):
        d.known.edits[n].setText("")
    d.work_out.click()
    QtTest_wait(lambda: d.known.isHidden(), 60)
    data = json.loads((case / "planted_case.json").read_text(encoding="utf-8"))
    check(d.known.isHidden() and d.label.text() == "No physical conclusion"
          and d.ask_text.text() == ("Its real speed needs how far away the object is, or the true size of something in the "
                                    "picture. Do you know either?")
          and d.ask_button.text() == "Add what you know" and known_qt.remembered(clip) == {"fov": 30.0}
          and "range_m" not in data["stages"]["ingest"]["fields"]["known"] and mp.fields["range_m"].text() == ""
          and plain(d.ask_text.text()),
          "emptied and worked out again: the speed goes, the card asks for what would give one, and the video's memory and "
          "the Measure form follow", d.ask_text.text()[:100])

    # Add what you know: something that cannot be read is said; 3 kilometers is `report --range 3000`, to the last digit
    d.ask_button.click()
    d.known.edits["own_ship"].setText("fast")
    d.work_out.click()
    check(d.known.isVisible() and d.known_said.isVisible() and "is not a speed" in d.known_said.text(),
          "something that cannot be read is said in the card, and nothing is worked out", d.known_said.text())
    d.known.edits["own_ship"].setText("")
    d.known.units["range_m"].setCurrentText("kilometers")
    d.known.edits["range_m"].setText("3")
    other = home / "by-command"
    shutil.copytree(case, other)
    d.work_out.click()
    QtTest_wait(lambda: d.known.isHidden(), 60)
    mine = json.loads((case / "planted_case.json").read_text(encoding="utf-8"))
    rc, out, err = command("report", other / "planted_case.json", "--range", 3000, "--workdir", frames, "--json")
    theirs = json.loads((other / "planted_case.json").read_text(encoding="utf-8")) if rc == 0 else {"stages": {}}
    check(rc == 0 and all(mine["stages"][n]["fields"] == theirs["stages"].get(n, {}).get("fields") for n in ("scale", "kinematics", "ingest")),
          "Work out the speed is `mcdonald report CASE --range 3000` on the same case, to the last digit: 3 kilometers is "
          "3000 meters", f"{mine['stages']['kinematics']['fields']['relative_speed_m_per_s']!r}" if rc == 0 else err[-200:])
    check("m/s" in d.headline.text() and d.label.text() != "No physical conclusion"
          and d.ask_text.text().startswith("Worked out from what you gave: the camera sees 30 degrees across, the object is 3 "
                                           "kilometers away") and known_qt.remembered(clip) == {"fov": 30.0, "range_m": 3000.0},
          "and the card has the speed, and says what it rests on; the video remembers it for the next run", d.headline.text()[:90])

    # typed in the Measure form, it is kept for the video too
    mp.fields["fov"].setText("12")
    mp.fields["fov"].editingFinished.emit()
    check(known_qt.remembered(clip).get("fov") == 12.0 and w.known_values.get("fov") == 12.0,
          "and a field of view typed in the Measure form is kept for the video as the segment step and the card keep it")
    w._closing = True
    w.close()
    mark_qt.complain, find_qt.complain, measure_qt.complain = keep
    mark_qt.settings().remove(f"known/{video.name}")


# ---------------------------------------------------------------- the harness
def _xvfb():
    """(process, display) for an X server with no screen, or None.

    -displayfd has the server pick a free display itself and write the number
    once it is accepting connections, so there is nothing to race and nothing
    to sleep for -- xvfb-run sleeps three seconds a launch. It is started
    without an auth file, which means any local user could connect to it for
    the few seconds it lives; all they would find is a synthetic clip."""
    if ON_SCREEN or not shutil.which("Xvfb"):
        return None
    r, w = os.pipe()
    x = subprocess.Popen(["Xvfb", "-displayfd", str(w), "-screen", "0", "1600x1200x24", "-nolisten", "tcp"],
                         pass_fds=[w], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(w)
    try:
        num = os.read(r, 32).decode().strip() if select.select([r], [], [], 15)[0] else ""
    finally:
        os.close(r)
    if num.isdigit():
        return x, f":{num}"
    x.kill()
    x.wait()
    return None


def _host(xvfb):
    """Where the windows go: (environment, what to call it), or None."""
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    env.pop("MPLBACKEND", None)
    if xvfb:
        # X11 only. Left to themselves Qt and GTK find the Wayland session and
        # open on the desktop anyway, DISPLAY or no DISPLAY
        env.pop("WAYLAND_DISPLAY", None)
        env.update(DISPLAY=xvfb[1], QT_QPA_PLATFORM="xcb", GDK_BACKEND="x11")
        return env, f"Xvfb {xvfb[1]}, off screen"
    if sys.platform in ("win32", "darwin") or env.get("DISPLAY") or env.get("WAYLAND_DISPLAY"):
        return env, "the desktop"
    return None


def _stop(p):
    """The child and anything it started, gently first."""
    if not hasattr(os, "killpg"):
        p.kill()
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(p.pid, sig)
            p.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            continue
        except ProcessLookupError:
            return


def _run_child(backend, host, open_within=25, finish_within=180):
    """(exit code, output, hung). Two deadlines, because the two hangs mean
    different things: before the window is up it is the toolkit, after it is us.
    The output is read by a thread of this harness's own, not `communicate`: on
    Windows a `communicate` that times out carries none of what the child has
    printed (CPython's `_communicate` there raises `TimeoutExpired` bare), so
    the window's `UP` line could not be seen at the first deadline and every
    child that outlived it was "hung" (run 18 on 0.2.14, 2026-10-09, the
    PySide6 child ended at 75 s with 416 checks passed)."""
    open_within, finish_within = open_within * PATIENCE, finish_within * PATIENCE
    began = time.monotonic()
    p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--drive", backend],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", env=host[0],
                         start_new_session=True)
    lines = []

    def read():
        for line in p.stdout:
            lines.append(line)

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    hung = False
    try:
        p.wait(timeout=open_within)
    except subprocess.TimeoutExpired:
        if UP in "".join(lines):
            try:
                p.wait(timeout=finish_within)
            except subprocess.TimeoutExpired:
                hung = True
        else:
            hung = True
    if hung:
        _stop(p)
    reader.join(15)                   # the pipe closes with the child; a worker it spawned may hold it a moment
    out = "".join(lines)
    if hung:
        out += f"\n(ended by the harness after {time.monotonic() - began:.0f} s)\n"
    return p.returncode, out, hung


def test_help_is_the_table():
    """`mcdonald mark --help` is where an agent, or a person at a terminal, reads the keys."""
    print("\nmark: --help")
    from mcdonald import actions
    argv, sys.argv = sys.argv, ["mcdonald mark", "--help"]
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            mark.main()
    except SystemExit:
        pass
    finally:
        sys.argv = argv
    text = " ".join(out.getvalue().split())
    missing = [k for k, h, _ in actions.listing("qt") if any(" ".join(t.split()) not in text for t in (k, h))]
    check(not missing, "--help lists every key of both windows, from the table the menus are made from",
          f"{len(actions.listing('qt'))} lines" + (f"; missing {missing[:3]}" if missing else ""))
    check("* the Qt window only" in text, "and says which are the Qt window's alone")


def test_the_launcher():
    """`mcdonald-gui`: how someone with no terminal gets in at all. Before it, the only way
    to the window was to type `mcdonald mark`."""
    print("\nmcdonald-gui: the way in with no terminal")
    from mcdonald import gui
    toml = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    check("[project.gui-scripts]" in toml and 'mcdonald-gui = "mcdonald.gui:main"' in toml,
          "the package installs a mcdonald-gui launcher, as a gui-script: no console opens with it")
    from mcdonald import mark_qt
    sizes = sorted(s.width() for s in mark_qt.application().windowIcon().availableSizes())
    check(sizes[:1] == [16] and 512 in sizes, "every window has mcdonald's icon, drawn for each size", str(sizes))
    if sys.platform not in ("win32", "darwin"):
        keep = {k: os.environ.pop(k, None) for k in ("DISPLAY", "WAYLAND_DISPLAY")}
        try:
            why = gui.cannot_open() or ""
        finally:
            os.environ.update({k: v for k, v in keep.items() if v is not None})
        check("PySide6" in why or "no screen" in why, "with no display, or no PySide6, it says so rather than letting Qt abort",
              repr(why[:60]))
        if shutil.which("mcdonald-gui") is None:
            print("  SKIP  mcdonald-gui is not on the PATH (the package is not installed), so there is nothing for a menu entry to start")
            SKIP.append("the desktop entry")
            return
        with tempfile.TemporaryDirectory() as td:
            text = gui.desktop_entry(td).read_text(encoding="utf-8")
            drawn = sorted(int(d.name.split("x")[0]) for d in (Path(td) / "icons" / "hicolor").iterdir()
                           if (d / "apps" / "mcdonald.png").is_file())
        check(f"Exec={shutil.which('mcdonald-gui')} %f" in text and "Terminal=false" in text and "MimeType=video/mp4" in text,
              "--desktop-entry writes an applications-menu entry that starts it, with no terminal, and offers it for videos")
        check("Icon=mcdonald" in text and drawn[:1] == [16] and 256 in drawn,
              "and with its own icon, at each size, in the icon theme", str(drawn))


def test_main_refuses_a_backend_that_cannot_open_a_window():
    """The commonest first experience on Linux. It has to end in instructions."""
    print("\nmark: a backend that cannot open a window")
    import matplotlib
    matplotlib.use("Agg", force=True)
    argv, sys.argv = sys.argv, ["mcdonald mark", "/nowhere/no-such-clip.mp4", "--gui", "mpl"]
    try:
        mark.main()
        msg = ""
    except SystemExit as ex:
        msg = str(ex.code)
    finally:
        sys.argv = argv
    check("non-interactive 'agg'" in msg.lower(), "main() stops, naming the backend it found",
          repr(msg[:60]))
    check("no-such-clip" not in msg, "before it goes looking for the video")
    for fix in ("pip install PySide6", "python3-tkinter python3-pillow-tk", "apt install python3-tk",
                "brew install python-tk"):
        check(fix in msg, f"and offers: {fix}")
    check("ImageTk" in msg, "says why tkinter alone may not be enough")
    check("track CSV" in msg, "and leaves a way through with no window at all")


def test_main_chooses_the_window_it_can_open():
    """--gui auto must never pick Qt where Qt cannot open: without a display Qt
    does not raise, it aborts the process."""
    print("\nmark: which window")
    import importlib.util
    import matplotlib
    matplotlib.use("Agg", force=True)
    have_qt = importlib.util.find_spec("PySide6") is not None
    keep = {k: os.environ.pop(k, None) for k in ("DISPLAY", "WAYLAND_DISPLAY")}
    try:
        if sys.platform not in ("win32", "darwin"):
            try:
                got = mark.choose_gui("auto")
            except SystemExit as ex:
                got = str(ex.code)
            check("non-interactive" in got, "with no display, auto falls through to matplotlib's own refusal, Qt or no Qt")
            try:
                got = mark.choose_gui("qt")
            except SystemExit as ex:
                got = str(ex.code)
            check("--gui qt needs PySide6 and a display" in got, "and --gui qt says what it needs rather than aborting",
                  repr(got[:70]))
        os.environ["DISPLAY"] = ":77"                 # never connected to: choosing is not opening
        if have_qt:
            check(mark.choose_gui("auto") == "qt", "with PySide6 and a display, auto is the Qt window")
        else:
            print("  SKIP  PySide6 is not installed, so there is no Qt window to choose")
            SKIP.append("choosing Qt")
    finally:
        for k, v in keep.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def test_the_window_under_every_backend_that_opens():
    xvfb = _xvfb()
    try:
        host = _host(xvfb)
        if host is None:
            print("\n  SKIP  no display, and no Xvfb to stand in for one")
            SKIP.append("the window (no display)")
            return
        print(f"\nthe window, hosted on {host[1]}")
        backends = WANTED or [b for b in WINDOWS if b != "MacOSX" or sys.platform == "darwin"]
        with ThreadPoolExecutor(len(backends)) as pool:       # the children are the work, not these threads
            # the Qt window's child also measures three cases and runs `mcdonald run` beside them
            results = list(pool.map(lambda b: _run_child(b, host, finish_within=540 if b == "PySide6" else 90), backends))
    finally:
        if xvfb:
            xvfb[0].terminate()
            xvfb[0].wait()
    driven, saved = 0, {}
    for b, (rc, out, hung) in zip(backends, results):
        if UP not in out:
            why = "hung before a window opened" if hung else \
                  next((ln for ln in reversed(out.strip().splitlines()) if ln.strip()), f"exit {rc}")
            print(f"  SKIP  {b}: {why.strip()[:150]}")
            SKIP.append(b)
            continue
        driven += 1
        body = out.split(UP, 1)[1].strip("\n")
        for ln in body.splitlines():
            if ln.startswith(SAVED):
                saved[b] = json.loads(ln[len(SAVED):])
        print("\n".join(ln for ln in body.splitlines() if not ln.startswith(SAVED)))
        failed = [ln.split("FAIL", 1)[1].strip() for ln in body.splitlines() if ln.startswith("  FAIL")]
        FAIL.extend(f"{b}: {f}" for f in failed)
        if hung:
            print(f"  FAIL  {b} hung after the window was up -- a handler is waiting on something "
                  "(a modal dialog?)")
            FAIL.append(f"{b}: hung")
        elif rc != 0 and not failed:
            print(f"  FAIL  {b} exited {rc} without finishing")
            FAIL.append(f"{b}: exit {rc}")
    if not driven:
        print("  no interactive backend could open a window here, so the window itself is untested")
    if "PySide6" in saved and len(saved) > 1:
        # the same clicks at the same image coordinates, through two toolkits and two
        # transforms. What reaches the disk has to be the same file
        print("\nthe two windows, compared")
        other = next(b for b in saved if b != "PySide6")

        def flat(d):
            return {(c, n): xy for c, v in d["classes"].items() for n, xy in v.items()}
        a, b = flat(saved["PySide6"]), flat(saved[other])
        worst = max((abs(a[k][i] - b[k][i]) for k in a if k in b for i in (0, 1)), default=0.0)
        check(a.keys() == b.keys(), f"the Qt window and the matplotlib window ({other}) saved marks on the same frames",
              f"{len(a)} marks")
        check(worst < 1e-6, "at the same coordinates", f"largest difference {worst:.1e} px")


def main():
    global ON_SCREEN, WANTED
    if "--drive" in sys.argv:
        return drive(sys.argv[sys.argv.index("--drive") + 1])
    ON_SCREEN = "--on-screen" in sys.argv
    WANTED = [a for a in sys.argv[1:] if not a.startswith("-")]
    print("McDonald UAP Toolkit — the marking windows")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    if FAIL:
        print(f"\n{len(FAIL)} FAILED: {', '.join(FAIL)}")
        return 1
    print(f"\n{'ALL PASS' if not SKIP else 'ALL PASS (skipped: ' + ', '.join(SKIP) + ')'}")
    return 0


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):           # a pipe or a log file on Windows is cp1252, and the checks' names have arrows
        _s.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
