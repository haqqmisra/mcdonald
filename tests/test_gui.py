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

    def grey(self, n):
        return self.rgb(n).mean(2)

    def __getstate__(self):                      # it goes to the linker's processes; the frames can be made again there
        return {**self.__dict__, "_frames": {}}

    def rgb(self, n):
        if n not in self._frames:
            yy, xx = self._yx
            x, y = self.truth(n)
            g = self._sky + 170 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 2.5 ** 2))
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

    def __init__(self, clip, ms, out):
        self.m = mark.Marker(clip, ms, out)

    def describe(self):
        return f"{type(self.m.fig.canvas).__module__}.{type(self.m.fig.canvas).__name__}"

    def key(self, k):
        """One key press, with the pointer over the middle of the image -- where it
        is when someone is marking, and where matplotlib's own bindings would act."""
        from matplotlib.backend_bases import KeyEvent
        c, box = self.m.fig.canvas, self.m.ax.bbox
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

    def key(self, k, ctrl=False, shift=False):
        from PySide6 import QtCore, QtGui, QtWidgets
        from PySide6.QtCore import Qt
        named = {"left": Qt.Key.Key_Left, "right": Qt.Key.Key_Right, "backspace": Qt.Key.Key_Backspace,
                 "home": Qt.Key.Key_Home, "end": Qt.Key.Key_End, " ": Qt.Key.Key_Space}
        if k in named:
            code, text = named[k], " " if k == " " else ""
        else:
            code, text = Qt.Key(ord(k.upper())), k
            shift = shift or k in "<>"
        mod = Qt.KeyboardModifier.NoModifier
        if ctrl:
            mod, text = mod | Qt.KeyboardModifier.ControlModifier, ""
        if shift:
            mod = mod | Qt.KeyboardModifier.ShiftModifier
        # to the view, which is where the focus sits while marking
        for kind in (QtCore.QEvent.Type.KeyPress, QtCore.QEvent.Type.KeyRelease):
            QtWidgets.QApplication.sendEvent(self.m.view, QtGui.QKeyEvent(kind, code, mod, text))
        self.settle()

    def to_px(self, xy):
        p = self.m.view.to_view(float(xy[0]), float(xy[1]))
        return np.array([p.x(), p.y()])

    def mouse(self, kind, px, button=None, step=0, widget=None):
        from PySide6 import QtCore, QtGui, QtWidgets
        from PySide6.QtCore import Qt
        w = widget or self.m.view.viewport()
        pos = QtCore.QPointF(float(px[0]), float(px[1]))
        glob = QtCore.QPointF(w.mapToGlobal(pos.toPoint()))
        B = {None: Qt.MouseButton.NoButton, 1: Qt.MouseButton.LeftButton, 2: Qt.MouseButton.MiddleButton,
             3: Qt.MouseButton.RightButton}
        none = Qt.KeyboardModifier.NoModifier
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
            check(any("source_candidates(size=" in ln and "seed=" in ln for ln in head) and any("hand mark" in ln for ln in head),
                  "and says how it was made and how far it sits from the hand marks")
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
    check(f"frame {m.clip.n0} / {m.clip.n1}" in rig.status() and "marking: object" in rig.status(),
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
    check(f"frame {n1} / {n1}" in rig.status(), "the status follows")


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
    check("2 marks" in rig.status() and "px/frame" in rig.status(), "the status reports both")

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


# ---------------------------------------------------------------- what only the Qt window has
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
    check(f"x {c.RED[0]:.1f}   y {c.RED[1]:.1f}" in m.cursor_label.text() and "DN 85" in m.cursor_label.text(),
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
    m.auto_box.setChecked(True)
    m.size_box.setValue(31)                      # wrong on purpose: auto has to put it right
    rig.key("l")
    check(m.linking() and "stop" in m.link_button.text(), "'l' starts linking, off the GUI thread")
    done = rig.wait_for(lambda: m.link is not None and m.link.done, 120)
    check(done, "and it finishes", m.link_label.text()[:90] if m.link else "")
    if done:
        L = m.link
        check(L.size is not None and L.size < 31 and m.size_box.value() == int(L.size) and m.dark_box.isChecked() == L.dark,
              "the detector's scale came from the marks, and the controls show the choice", f"{L.size:g} px, dark={L.dark}")
        check(sorted(L.track) == list(range(first, c.n1 + 1)), "every frame from the first mark to the end is linked",
              f"{len(L.track)} frames, {min(L.track)}–{max(L.track)}")
        err = max(np.hypot(x - c.truth(n)[0], y - c.truth(n)[1]) for n, (x, y) in L.track.items())
        check(err < 0.5, "on the object in every one of them", f"worst {err:.2f} px")
        check(set(L.residuals) == {first, second} and L.worst() < 0.5,
              "and held against both hand marks, the second of which it was not seeded from", f"worst {L.worst():.2f} px")
        m.goto(first + 5)
        check(m.box is not None and np.allclose(m.box.xy, L.track[first + 5]), "the window draws the track's position on the frame")
        m.goto(first - 1)
        check(m.box is None, "and nothing where it has none")
        check(m.timeline.linked == sorted(L.track), "the timeline shows which frames are linked")
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
        rig.key("l")
        rig.wait_for(lambda: m.link is not None and m.link.stage == "linking" and m.linking(), 60)
        rig.key("l")
        check(rig.wait_for(lambda: not m.linking(), 30) and m.link.done and "stopped" in m.link.say,
              "'l' while linking stops it, and it says so", m.link.say[-60:])
        rig.key("l")                                 # straight away, while the last link's thread is still making its strip
        again = rig.wait_for(lambda: m.link is not None and m.link.done and "stopped" not in m.link.say, 120)
        check(again and sorted(m.link.track) == list(range(first, c.n1 + 1)),
              "and 'l' once more links to the end again, for the save below")
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


def drive(target):
    """The child: open one window and press everything."""
    qt = target == "PySide6"
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
        drive_zoom_and_pan(rig)
        drive_pixels_are_where_the_coordinates_say(rig)
        if qt:
            drive_the_finder(rig, new_rig)
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
            results = list(pool.map(lambda b: _run_child(b, host), backends))
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
