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
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
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
        self._held = None
        self.settle(50)

    def describe(self):
        import PySide6
        from PySide6 import QtCore, QtGui
        return f"PySide6 {PySide6.__version__}, Qt {QtCore.qVersion()}, platform {QtGui.QGuiApplication.platformName()}"

    def settle(self, ms=0):
        from PySide6 import QtTest
        if ms:
            QtTest.QTest.qWait(ms)
        self.m.app.processEvents()

    def wait_for(self, cond, seconds):
        """Keep the event loop turning until cond() or the deadline; says which."""
        from PySide6 import QtTest
        end = time.monotonic() + seconds
        while not cond() and time.monotonic() < end:
            QtTest.QTest.qWait(10)
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
            self.wait_for(self.active, 3)
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
        from PySide6 import QtGui
        img = self.m.view.pix.pixmap().toImage().convertToFormat(QtGui.QImage.Format.Format_RGB888)
        a = np.frombuffer(img.constBits(), np.uint8).reshape(img.height(), img.bytesPerLine())
        a = a[:, :3 * img.width()].reshape(img.height(), img.width(), 3)
        return np.array_equal(a, self.m.clip.rgb(n).astype(np.uint8))

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
            head = [ln for ln in auto.read_text().splitlines() if ln.startswith("#")]
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
    return json.loads(j.read_text())


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
    missing = [k for k, h, _ in actions.listing("qt") if any(" ".join(t.split()) not in text for t in (k, h))]
    check(page.isVisible() and not missing, "F1 is Help -> Keys: every key and the mouse, with what each does",
          f"{len(actions.listing('qt'))} lines" + (f"; missing {missing[:3]}" if missing else ""))
    page.activateWindow()
    rig.wait_for(lambda: m.app.activeWindow() is page, 3)
    rig.key(".")
    check(m.app.activeWindow() is page and m.n == n + 1, "and with that page in front the window's keys still work: "
          "it is a tool window, as the strips are", f"active: {type(m.app.activeWindow()).__name__}")
    rig.key(",")
    page.close()


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
    from mcdonald import actions, find_qt, measure_qt
    m = rig.m
    m.show_keys()
    m.show_first_run()
    roots = [m, m.keys_page, m.first_run_page, find_qt.FindPanel(m), measure_qt.MeasurePanel(m)]
    said = []
    for root in roots:
        for w in [root] + root.findChildren(QtWidgets.QWidget):
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
    for d in roots[1:]:
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
    check(m.windowTitle().endswith("*"), "an unsaved mark shows in the title", repr(m.windowTitle()))
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
    m.goto(c.n1 - 3)
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
    check(m.linking() and "stop" in m.link_button.text(), "'l' starts linking, off the GUI thread")
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
            check(shown, "and each has its strip")
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
    from PySide6 import QtGui, QtTest
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
    check(QtTest_wait(lambda: d.shown == 1, 10) and on_screen() == 1 and "frame 1 of 90" in d.where.text(),
          "it opens on the first frame, and says which frame is on the screen", repr(d.where.text()))
    d.goto(44)
    check(QtTest_wait(lambda: d.shown == 44, 10) and on_screen() == 44, "a place on the bar is gone to, and the picture is that frame's")
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
    d.buttons_by_id["faster"].click()
    check("2×" in d.speed_label.text(), "faster and slower change the speed, and the label says it", repr(d.speed_label.text()))
    d.buttons_by_id["slower"].click()
    tips = {k: b.toolTip() for k, b in d.buttons_by_id.items()}
    check(all("(" in t for t in tips.values()) and "space" in tips["play"] and "[" in tips["start"],
          "there is no menu here, so every button's tip names its key", tips["play"])
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
    check(d.chosen() == (1, 90) and "90 of 90 frames still have to be saved" in d.cost.text() and clip.dir.name in d.cost.text(),
          "the range chooser opens on the whole clip and says what extracting it costs, and where", repr(d.cost.text()[:75]))
    d.first.setValue(30)
    d.last.setValue(50)
    check("21 of 21 frames" in d.cost.text() and "21 frames" in d.span.text() and "0:00.97" in d.span.text(),
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
    check(not ok.isEnabled() and "more than there is room for" in d.cost.text(), "a range that will not fit cannot be opened, and says why")
    d.close()

    # the way in
    mark_qt.choose_range = lambda clip, parent=None: asked.append((clip.n0, clip.n1)) or (10, 30)
    w = mark_qt.open_session(str(video), workdir=f"{td}/frames2", cases=str(cases))
    check(w is not None and asked == [(1, 90)] and (w.clip.n0, w.clip.n1) == (10, 30), "with no range named, the person is asked for one")
    check(w.clip.n_extracted() == 21 and not w.clip.path(9).exists() and not w.clip.path(31).exists(),
          "and only that much is extracted", f"{len(list(Path(w.clip.dir).glob('*.png')))} frames on disk")
    check(Path(w.out) == cases / "drawn" / "drawn" and str(cases / "drawn") in w.case_label.text(),
          "the case directory is in a folder of cases, and the window says where", repr(w.case_label.text()))
    check(not (cases / "drawn").exists(), "nothing is made on disk until there is something to save")
    w.show()
    w.ms.add("object", 12, 100.0, 50.0)
    with contextlib.redirect_stdout(io.StringIO()):
        w.finish(show_strip=False)
    check((cases / "drawn" / "drawn_marks.json").exists(), "saving makes it")
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
    blocked.write_text("")
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
                                    "how": {"object": {"12": "agent: candidate 1 of 3 at 9 px"}}}))
    w.open_marks(str(by_agent))
    shown = {w.table.item(r, 1).text(): w.table.item(r, 4).text() for r in range(w.table.rowCount())}
    check(shown == {"12": "agent", "15": "hand", "80": "hand"} and "candidate 1 of 3" in w.table.item(0, 4).toolTip(),
          "a mark an agent placed is shown as an agent's, with its reason, to the person who opens the file", str(shown))
    check(w.ms.marks["object"] == {12: (101.0, 51.0), 15: (90.0, 60.0), 80: (5.0, 5.0)} and "1 of them are on frames outside" in w.note.text(),
          "File -> Open marks continues from a marks file, and says which of its marks this range cannot show", repr(w.note.text()[:60]))
    check(w.windowTitle().endswith("*"), "they are not this case's saved marks, so the window counts them unsaved")
    junk = Path(td) / "junk.json"
    junk.write_text("[1, 2, 3]")
    n, before = len(said), dict(w.ms.marks["object"])
    w.unsaved_answer = lambda: "discard"
    w.open_marks(str(junk))
    check(len(said) == n + 1 and "is not a marks file" in said[-1] and w.ms.marks["object"] == before,
          "a file that is not a marks file is refused, and the marks are left alone")
    other = Path(td) / "other_marks.json"
    other.write_text(json.dumps({"video": "/somewhere/another-clip.mp4", "classes": {"object": {"12": [1, 1]}}}))
    put = []
    mark_qt.confirm = lambda parent, text: put.append(text) and False
    w.open_marks(str(other))
    check(len(put) == 1 and "another-clip.mp4" in put[0] and w.ms.marks["object"] == before,
          "marks made on a different clip are questioned before they are opened on this one")

    # another clip, without starting again
    second = Path(td) / "second.mp4"
    shutil.copy(video, second)
    mark_qt.choose_range = lambda clip, parent=None: (1, 12)
    w.open_clip(str(second))
    new = mark_qt._windows[-1]
    check(new is not w and new.isVisible() and not w.isVisible() and new.ms.tag == "second" and new.ms.count() == 0,
          "File -> Open a clip opens it in this window's place, with its own marks")
    check(Path(new.out) == cases / "second" / "second", "and its own case directory, beside the first")
    new.close()
    mark_qt.complain, mark_qt.choose_range, mark_qt.confirm = keep


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
    check("(f)" in m.find_button.text(), "there is a button for it above the link's, naming its key")
    rig.key("F")
    p = m.find_panel
    check(p is not None and p.isVisible() and p.running() and not p.near.isVisible() and p.frames() == (clip.n0, clip.n1),
          "f opens the panel and it starts looking, in everything that is open when that is not long")
    got = rig.wait_for(lambda: not p.running() and bool(p.proposals) and p.go.isEnabled(), 240)   # the thread has ended, and the panel has heard
    ok = check(got and not said, "it finishes with something on its list", p.now.text()[:80] + ("; " + said[-1][:80] if said else ""))
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
          and [b.text() for b in row.findChildren(QtWidgets.QPushButton)] == ["Show", "This is it"],
          "each row is a strip of the clip's own pixels, with Show and This is it")
    check(p.bar.maximum() == 1 and p.bar.value() == 1 and "in all" in p.elapsed.text() and "click it on two frames" in p.now.text(),
          "when it ends the bar is full, the time it took is said, and what to do if the object is not there")
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
    check(m.n == first.frames[0] and m._proposal_path is not None and m.ms.count() == 0 and "not a mark until you choose it" in m.note.text(),
          "Show goes to where it starts and draws its path -- and places nothing")
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
    rig.wait_for(lambda: not m.linking() and m.links.get(0) is not None and m.links[0].done, 120)
    link = m.links.get(0)
    worst = max(np.hypot(x - clip.truth(n)[0], y - clip.truth(n)[1]) for n, (x, y) in link.track.items()) if link and link.track else None
    check(worst is not None and worst < 1.0 and len(link.track) >= 30, "and is on the object, measured by the package's own detector",
          f"{len(link.track) if link else 0} frames, worst {worst:.2f} px" if worst is not None else "no link")
    shown = {m.table.item(r, 1).text(): m.table.item(r, 4).text() for r in range(m.table.rowCount())}
    check(set(shown.values()) == {"proposed"}, "the table of marks says proposed, where a click says hand", str(shown))
    rig.key("Z", ctrl=True)
    check(m.ms.count() == 0, "taking a proposal is one step to undo")
    click(rig, clip.truth2(m.n))
    check(m.ms.kind("object", m.n) == "hand", "and a click is still a click: the person's correction, recorded as a hand's")
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
    check(p is not None and p.isVisible() and "no track of the object yet" in p.what.text() and "to link" in p.what.text(),
          "Measure opens a panel; with nothing linked it says nothing of an object will be measured, and what to do", repr(p.what.text()[:60]))
    rows = {k.name: k for k in stages.KNOWN}
    check(set(p.fields) == set(rows) and all(p.fields[n].toolTip() == k.help for n, k in rows.items()),
          "its form has a field for every row of stages.KNOWN, with the row's help under the pointer", f"{len(rows)} rows")
    rc, out, err = command("run", "--help")
    check(rc == 0 and all(k.flag + " " in out and " ".join(k.help.split()[:4]) in " ".join(out.split()) for k in rows.values()),
          "and `mcdonald run --help` has an option for every one of them, in the same words: one table, two shells")
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
    check("track linked from your marks" in p.what.text() and f"{link.size:g} pixels" in p.fields["size"].placeholderText(),
          "asked again, the panel says which track the case will be made from, and the size the marks chose", repr(p.fields["size"].placeholderText()))

    p.fields["fov"].setText("wide")
    p.start()
    check(not p.running() and said and "wide" in said[-1] and "not a number" in said[-1], "a field that is not a number is refused in a dialog, and nothing starts",
          repr(said[-1]) if said else "")
    p.fields["fov"].setText("")
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
        p.start()
    got = QtTest_wait(lambda: p.sheet_path is not None and p.sheet is not None and p.sheet.isVisible(), 120)
    check(got and Path(p.sheet_path).exists() and p.running() and p.case is None and not (case / "planted_case.md").exists(),
          "the gate: the track sheet is made and shown, and nothing is measured from the track until the person answers",
          Path(p.sheet_path).name if got else "no sheet within 120 s")
    asked = " ".join(x.text() for x in p.sheet.findChildren(QtWidgets.QLabel)) if got else ""
    check("on the object in every frame" in asked, "with the question under it")
    check(p.bar.maximum() == 1 and "waiting for you" in p.now.text() and "since it started" in p.elapsed.text(),
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
    md = (case / "planted_case.md").read_text()
    check(p.report is not None and p.report.isVisible() and "Bottom line" in p.report.page.toPlainText()
          and "What this clip cannot decide" in p.report.page.toPlainText(), "and the case report is put in front of the person, not left on a disk")
    check("reviewed: yes (asked with the sheet on the screen)" in md and "provisional" not in md,
          "the report records that the sheet was examined, and how it knows")
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
    md = (case / "planted_case.md").read_text()
    check("NOT CONFIRMED" in md and "provisional" in md and "confirmation that the track sheet was examined" in md,
          "a sheet closed without an answer is a no: the report calls the object measurements provisional, and says what would close it")

    # stopping
    with contextlib.redirect_stdout(io.StringIO()):
        p.start()
    p.stop()
    QtTest_wait(lambda: p.sheet is not None and p.sheet.isVisible() or not p.running(), 120)
    if p.sheet is not None:
        p.answer_sheet(False)
    QtTest_wait(lambda: not p.running() and p.case is not None, 120)
    check(p.case is not None and "kinematics" not in p.case.stages and "ingest" in p.case.stages and (case / "planted_case.md").exists()
          and "stopped" in p.log.toPlainText(), "Stop leaves the stages not yet run out, and the report is written of the ones that ran",
          ", ".join(p.case.stages) if p.case else "")

    # and inside a stage: minutes of layers must not have to be waited out
    p.whole.setChecked(True)
    p.slow["layers"].setChecked(True)
    del steps[:]
    with contextlib.redirect_stdout(io.StringIO()):
        p.start()
    QtTest_wait(lambda: p.sheet is not None and p.sheet.isVisible() or not p.running(), 120)
    if p.sheet is not None:
        p.answer_sheet(True)
    in_layers = QtTest_wait(lambda: any("layers: comparing pairs of frames" in t and (d or 0) >= 1 for t, d, _, _ in steps) or not p.running(), 180)
    p.stop()
    QtTest_wait(lambda: not p.running() and p.case is not None, 120)
    last = max((d for t, d, _, _ in steps if "layers: comparing pairs of frames" in t), default=None)
    total = next((n for t, _, n, _ in steps if "layers: comparing pairs of frames" in t), None)
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
    check(p.isVisible() and "(m)" in w.measure_button.text(), "there is a button for it under the link's, naming its key: what comes after the link")

    w.do("first_run")
    text = w.first_run_page.page.toPlainText()
    heads = [h for h, _ in actions.first_run()]
    check(w.first_run_page.isVisible() and all(h in text for h in heads) and text.index("Two clicks") < text.index("Link") < text.index("Measure"),
          "Help -> Getting started walks through the job in the order it is done", ", ".join(heads))
    named = {a.id: actions.spoken(a.keys[0]) for a in actions.ACTIONS if a.keys}
    import re
    used = set(re.findall(r"{(\w+)}", " ".join(t for _, t in actions.FIRST_RUN)))
    check(used and used <= set(named) and all(f"Press {named[i]}" in text or named[i] in text for i in used),
          "and every key it names is taken from the table the menus are made from", ", ".join(sorted(used)))
    w._closing = True
    w.close()
    mark_qt.complain, measure_qt.complain = keep


def QtTest_wait(cond, seconds):
    from PySide6 import QtTest
    end = time.monotonic() + seconds
    while not cond() and time.monotonic() < end:
        QtTest.QTest.qWait(10)
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
            drive_measuring(td)
        saved = drive_saving(rig, new_rig)
        # what the two windows put on disk from the same clicks, for the harness to compare
        print(SAVED + json.dumps(saved, sort_keys=True), flush=True)
    return 1 if FAIL else 0


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


def _run_child(backend, host, open_within=25, finish_within=90):
    """(exit code, output, hung). Two deadlines, because the two hangs mean
    different things: before the window is up it is the toolkit, after it is us."""
    p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--drive", backend],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=host[0],
                         start_new_session=True)
    try:
        out, _ = p.communicate(timeout=open_within)
        return p.returncode, out, False
    except subprocess.TimeoutExpired as ex:
        so_far = ex.output or b""
        so_far = so_far.decode(errors="replace") if isinstance(so_far, bytes) else so_far
    if UP in so_far:
        try:
            out, _ = p.communicate(timeout=finish_within)
            return p.returncode, out, False
        except subprocess.TimeoutExpired:
            pass
    _stop(p)
    out, _ = p.communicate()
    return p.returncode, out, True


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
    toml = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text()
    check("[project.gui-scripts]" in toml and 'mcdonald-gui = "mcdonald.gui:main"' in toml,
          "the package installs a mcdonald-gui launcher, as a gui-script: no console opens with it")
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
            text = gui.desktop_entry(td).read_text()
        check(f"Exec={shutil.which('mcdonald-gui')} %f" in text and "Terminal=false" in text and "MimeType=video/mp4" in text,
              "--desktop-entry writes an applications-menu entry that starts it, with no terminal, and offers it for videos")


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
            results = list(pool.map(lambda b: _run_child(b, host, finish_within=420 if b == "PySide6" else 90), backends))
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
    sys.exit(main())
