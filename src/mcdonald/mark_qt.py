"""`mcdonald mark`, the Qt window — for finding the object, not only marking it.

The matplotlib window (`mark.Marker`) is enough when you already know which
twenty frames the object is in. This one is for the clip you have not seen:
scrub the whole of it on a timeline, play it at true speed, open an overview of
every part of it at once, ask the detector which compact sources it sees, and
mark under a loupe. Then press `l` and watch what the linker makes of the marks:
the automatic track is drawn over the clip as it grows, which is where "did it
lock onto the object?" ought to be answered -- in front of the person who knows
which thing the object is, before anything is built on the track.

It is a second shell over the same `MarkSet`. Everything that matters lives
there, both windows save through `mark.save_all`, and tests/test_gui.py runs
one list of checks against both, so the two cannot drift apart unnoticed.

Three things carry over from the matplotlib window on purpose.

- Frames are lossless PNGs named by absolute frame number. There is no video
  element here and there must never be one: playback is those same PNGs shown
  against a clock, so the frame on screen is frame n by construction.
- Coordinates are the package's: pixel centres at integers, as numpy indexes
  them and imshow draws them. A Qt scene would put pixel (0, 0) over [0, 1), so
  the pixmap is offset by half a pixel and scene coordinates *are* image
  coordinates. tests/test_gui.py pins this against the rendered pixels.
- Time is (n - 1) / fps, with fps the exact rational.

Playback. A lossless 1080p frame takes about 50 ms to decode and lasts 33, so
frames are decoded ahead of the cursor on several threads (`FrameStore`). The
clock decides which frame is due; if decoding falls behind, frames are skipped
rather than time stretched, and the status bar says how many.

PySide6 only, which is LGPL. PyQt is GPL or commercial, and importing it here
would choose the package's licence before anyone had decided it.

The keys are rows of `actions.ACTIONS`, and so are the menus: every row is a
QAction with its shortcut, which is how someone with only this window finds out
what it can do. Help -> Keys lists them with the mouse.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
from collections import OrderedDict
from concurrent.futures import CancelledError, ThreadPoolExecutor
from fractions import Fraction
from html import escape
from pathlib import Path

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from . import actions, autolink, catalog
from . import forensics as vf
from .actions import SNAP_PX
from .mark import CLASSES, COLOURS, LINKED, MarkSet, save_all, seed_text, status_line
from .reel import Reel

MASKS = autolink.MASKS                             # one sentence, wherever that wait is met
AUTO = "#f2f0e9"                                  # the automatic track: never a class colour, those are hand marks
DISPUTED = "#eda100"                              # where its forward and backward links disagree

SPEEDS = [Fraction(1, 8), Fraction(1, 4), Fraction(1, 2), Fraction(1), Fraction(2), Fraction(4)]
RGB32 = QtGui.QImage.Format.Format_RGB32


def application():
    """The QApplication, made on first use. Dark, so that the frame is the
    brightest thing on the screen: a white surround costs contrast on exactly
    the frames that matter, a faint object on a night sky."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv[:1])
        app.setApplicationName("mcdonald")
        app.setStyle("Fusion")
        pal, c = QtGui.QPalette(), QtGui.QColor
        for role, col in (("Window", "#1d1d1f"), ("WindowText", "#dddddd"), ("Base", "#141415"),
                          ("AlternateBase", "#1d1d1f"), ("Text", "#dddddd"), ("Button", "#2a2a2d"),
                          ("ButtonText", "#dddddd"), ("ToolTipBase", "#2a2a2d"), ("ToolTipText", "#dddddd"),
                          ("Highlight", "#2a78d6"), ("HighlightedText", "#ffffff"), ("PlaceholderText", "#898781")):
            pal.setColor(getattr(QtGui.QPalette.ColorRole, role), c(col))
        app.setPalette(pal)
        app.setWindowIcon(icon())
        if sys.platform == "win32":             # else the taskbar shows Python's icon, not the window's
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("bmsis.mcdonald")
            except (AttributeError, OSError):
                pass
    return app


def icon():
    """mcdonald's icon (tools/make_icons.py), each size its own drawing: the small ones are
    bolder, as the large one blurs to nothing at 16 pixels."""
    got = QtGui.QIcon()
    for png in sorted((Path(__file__).parent / "icons").glob("mcdonald-[0-9]*.png")):
        got.addFile(str(png))
    return got


def native_keys(keys):
    """A key list as this platform draws it: on macOS Qt's Ctrl is the command key."""
    if sys.platform != "darwin":
        return keys
    return keys.replace("ctrl+", "⌘").replace("shift+", "⇧")


def beside(window):
    """A dialog to be read beside the window, not instead of it. As a tool window it leaves
    the main window's shortcuts working while it has the focus: the track strip says "play
    the clip", and space has to play it without a click on the main window first."""
    d = QtWidgets.QDialog(window)
    d.setWindowFlag(Qt.WindowType.Tool)
    return d


def qimage_from_rgb(a):
    """An H x W x 3 array as a QImage that owns its pixels."""
    a = np.ascontiguousarray(np.asarray(a).astype(np.uint8))
    h, w = a.shape[:2]
    return QtGui.QImage(a.data, w, h, 3 * w, QtGui.QImage.Format.Format_RGB888).convertToFormat(RGB32)


# ---- frames -----------------------------------------------------------------------------
class FrameStore(QtCore.QObject):
    """Decoded frames, a few seconds either side of where you are.

    Decoding runs on a small thread pool and both routes release the GIL, so it
    scales: measured on 1080p lossless PNGs, one thread gives 20 frames/s and
    four give 73. The cache is bounded in bytes, least recently used out first."""
    arrived = QtCore.Signal(int)
    thumb_arrived = QtCore.Signal(int, QtGui.QImage)

    def __init__(self, clip, budget_mb=768, workers=None):
        super().__init__()
        self.clip = clip
        self._on_disk = callable(getattr(clip, "path", None))
        self._pool = ThreadPoolExecutor(workers or max(2, min(6, (os.cpu_count() or 4) - 2)),
                                        thread_name_prefix="mcdonald-decode")
        self._lock = threading.RLock()
        self._have, self._pending = OrderedDict(), {}
        self._bytes, self._budget = 0, budget_mb * 2 ** 20

    def _decode(self, n):
        if self._on_disk:
            img = QtGui.QImage(str(self.clip.path(n)))
            if not img.isNull():
                return img if img.format() == RGB32 else img.convertToFormat(RGB32)
        return qimage_from_rgb(self.clip.rgb(n))

    def get(self, n):
        """Frame n, now: from the cache, from a decode already under way, or decoded here."""
        with self._lock:
            img = self._have.get(n)
            if img is not None:
                self._have.move_to_end(n)
                return img
            fut = self._pending.get(n)
        try:
            img = fut.result() if fut else self._decode(n)
        except CancelledError:
            img = self._decode(n)
        self._keep(n, img)
        return img

    def want(self, ns):
        """Decode these ahead, in this order, and drop queued work nobody wants any more."""
        ns = [n for n in ns if self.clip.n0 <= n <= self.clip.n1]
        with self._lock:
            for n, f in list(self._pending.items()):
                if n not in ns and f.cancel():       # cancelling runs _done here and now, which forgets it
                    self._pending.pop(n, None)
            for n in ns:
                if n not in self._have and n not in self._pending:
                    f = self._pending[n] = self._pool.submit(self._decode, n)
                    f.add_done_callback(lambda f, n=n: self._done(n, f))

    def _done(self, n, f):
        if f.cancelled() or f.exception() is not None:
            with self._lock:
                self._pending.pop(n, None)
            return
        self._keep(n, f.result())
        self.arrived.emit(n)

    def _keep(self, n, img):
        with self._lock:
            self._pending.pop(n, None)
            if n not in self._have:
                self._have[n] = img
                self._bytes += img.sizeInBytes()
            self._have.move_to_end(n)
            while self._bytes > self._budget and len(self._have) > 1:
                _, old = self._have.popitem(last=False)
                self._bytes -= old.sizeInBytes()

    def cached(self):
        with self._lock:
            return sorted(self._have)

    def thumb(self, n, width):
        """Frame n reduced to `width`, off the GUI thread; comes back through thumb_arrived."""
        def job():
            img = self._decode(n).scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)
            self.thumb_arrived.emit(n, img)
        self._pool.submit(job)

    def close(self):
        self._pool.shutdown(wait=False, cancel_futures=True)


# ---- what is drawn over the frame -------------------------------------------------------
class Cross(QtWidgets.QGraphicsItem):
    """A mark: four arms with a gap at the centre, so that it points at the
    object without covering it. Constant size on screen whatever the zoom."""

    def __init__(self, x, y, colour, arms=(4, 14), width=2.0):
        super().__init__()
        self.xy, self._colour, self._arms, self._width = (x, y), QtGui.QColor(colour), arms, width
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setPos(x, y)
        self.setZValue(10)

    def boundingRect(self):
        r = self._arms[1] + 3
        return QtCore.QRectF(-r, -r, 2 * r, 2 * r)

    def paint(self, p, option, widget=None):
        a, b = self._arms
        lines = [QtCore.QLineF(dx * a, dy * a, dx * b, dy * b) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        for pen in (QtGui.QPen(QtGui.QColor(0, 0, 0, 190), self._width + 2.5), QtGui.QPen(self._colour, self._width)):
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawLines(lines)


class Ring(QtWidgets.QGraphicsItem):
    """A detector candidate: a ring and its rank, 1 the strongest."""

    def __init__(self, x, y, rank, strength):
        super().__init__()
        self.xy, self._rank, self.strength = (x, y), rank, strength
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setPos(x, y)
        self.setZValue(5)

    def boundingRect(self):
        return QtCore.QRectF(-14, -14, 60, 30)

    def paint(self, p, option, widget=None):
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        for pen in (QtGui.QPen(QtGui.QColor(0, 0, 0, 170), 3.0), QtGui.QPen(QtGui.QColor("#f2f0e9"), 1.2)):
            p.setPen(pen)
            p.drawEllipse(QtCore.QPointF(0, 0), 11, 11)
        p.setPen(QtGui.QColor("#f2f0e9"))
        p.drawText(QtCore.QPointF(14, 4), str(self._rank))


class Box(QtWidgets.QGraphicsItem):
    """Where the automatic track puts the object on this frame. A box, so that it
    can never be mistaken for a hand mark, and open, so that the object shows."""
    HALF = 15

    def __init__(self, x, y, disputed=False, label=""):
        super().__init__()
        self.xy, self.disputed, self.label = (x, y), disputed, label
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setPos(x, y)
        self.setZValue(8)

    def boundingRect(self):
        h = self.HALF + 3
        return QtCore.QRectF(-h, -h, 2 * h + 14, 2 * h)

    def paint(self, p, option, widget=None):
        h = self.HALF
        front = QtGui.QPen(QtGui.QColor(DISPUTED if self.disputed else AUTO), 1.4,
                           Qt.PenStyle.DashLine if self.disputed else Qt.PenStyle.SolidLine)
        for pen in (QtGui.QPen(QtGui.QColor(0, 0, 0, 190), 3.5), front):
            p.setPen(pen)
            p.drawRect(QtCore.QRectF(-h, -h, 2 * h, 2 * h))
        if self.label:
            p.drawText(QtCore.QPointF(h + 3, -h + 9), self.label)


class FrameView(QtWidgets.QGraphicsView):
    """The frame, with zoom about the cursor and pan. Reports presses in image coordinates."""
    pressed = QtCore.Signal(QtCore.QPointF, bool)             # where, in image coordinates, and whether shift was held
    hovered = QtCore.Signal(QtCore.QPointF)

    def __init__(self, w, h):
        super().__init__()
        self.W, self.H = w, h
        self.image_rect = QtCore.QRectF(-0.5, -0.5, w, h)
        sc = QtWidgets.QGraphicsScene(self)
        self.setScene(sc)
        self.pix = sc.addPixmap(QtGui.QPixmap())
        self.pix.setOffset(-0.5, -0.5)               # pixel centres at integers: see the module docstring
        # room to pan an edge of the frame to the middle of the window
        self.setSceneRect(self.image_rect.adjusted(-w / 2, -h / 2, w / 2, h / 2))
        self.setBackgroundBrush(QtGui.QColor("#0c0c0d"))
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._fitted, self._pan, self._pan_left = True, None, QtCore.QPointF()

    # -- coordinates: through the float transform. mapToScene() takes whole pixels only
    def to_image(self, pos):
        return self.viewportTransform().inverted()[0].map(QtCore.QPointF(pos))

    def to_view(self, x, y):
        return self.viewportTransform().map(QtCore.QPointF(x, y))

    def magnification(self):
        return self.transform().m11()

    def visible(self):
        """(x0, x1, y0, y1) of the view in image coordinates."""
        a, b = self.to_image(QtCore.QPointF(0, 0)), self.to_image(QtCore.QPointF(self.viewport().width(), self.viewport().height()))
        return a.x(), b.x(), a.y(), b.y()

    def fit(self):
        self.fitInView(self.image_rect, Qt.AspectRatioMode.KeepAspectRatio)
        self._fitted = True
        self._resample()

    def zoom_by(self, f, about):
        """Scale by f, keeping the image point under viewport position `about` where it is."""
        f = float(np.clip(self.magnification() * f, 0.05, 64.0)) / self.magnification()
        was = self.to_image(about)
        self.scale(f, f)
        now = self.to_image(about)
        self.translate(now.x() - was.x(), now.y() - was.y())
        self._fitted = False
        self._resample()

    def _resample(self):
        # reduced, a frame is smoothed so that a two-pixel object survives the
        # decimation; enlarged, it is the clip's own pixels, never interpolated
        smooth = self.magnification() < 1.0
        self.pix.setTransformationMode(Qt.TransformationMode.SmoothTransformation if smooth
                                       else Qt.TransformationMode.FastTransformation)

    # -- events
    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self._fitted:
            self.fit()

    def wheelEvent(self, e):
        notches = e.angleDelta().y() / 120.0
        if notches:
            self.zoom_by(1.25 ** notches, e.position())
        e.accept()

    def mousePressEvent(self, e):
        left = e.button() == Qt.MouseButton.LeftButton
        if e.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton) or \
                (left and e.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self._pan, self._pan_left = e.position(), QtCore.QPointF()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif left:
            p = self.to_image(e.position())
            if self.image_rect.contains(p):
                self.pressed.emit(p, bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier))
        e.accept()

    def mouseMoveEvent(self, e):
        if self._pan is not None:
            # scroll bars move in whole pixels; carry the remainder so a slow drag is not lost
            d = e.position() - self._pan + self._pan_left
            dx, dy = int(d.x()), int(d.y())
            self._pan, self._pan_left = e.position(), QtCore.QPointF(d.x() - dx, d.y() - dy)
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
            self._fitted = False
        self.hovered.emit(self.to_image(e.position()))
        e.accept()

    def mouseReleaseEvent(self, e):
        self._pan = None
        self.setCursor(Qt.CursorShape.CrossCursor)
        e.accept()

    def keyPressEvent(self, e):
        e.ignore()                                   # the window owns the keys; a scroll area would eat the arrows


class Timeline(QtWidgets.QWidget):
    """The whole clip as a bar: where you are, where the marks are, what is decoded."""
    scrubbed = QtCore.Signal(int)
    PAD = 10

    def __init__(self, n0, n1, fps):
        super().__init__()
        self.n0, self.n1, self.fps = n0, n1, fps
        self.n, self.marks, self.cached, self.linked, self.disputed = n0, {}, [], [], []
        self.part = None                              # (first, last) of a chosen part, drawn as a band: the range chooser's
        self.setFixedHeight(22 + 4 * len(CLASSES))
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def x_of(self, n):
        span = max(self.n1 - self.n0, 1)
        return self.PAD + (n - self.n0) / span * (self.width() - 2 * self.PAD)

    def n_at(self, x):
        span = max(self.n1 - self.n0, 1)
        f = (x - self.PAD) / max(self.width() - 2 * self.PAD, 1)
        return int(np.clip(round(self.n0 + f * span), self.n0, self.n1))

    def show_state(self, n, marks, cached, linked=(), disputed=()):
        self.n, self.marks, self.cached, self.linked, self.disputed = n, marks, cached, linked, disputed
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QtGui.QColor("#141415"))
        p.fillRect(QtCore.QRectF(self.PAD, 4, w - 2 * self.PAD, h - 8), QtGui.QColor("#232326"))
        px = max((w - 2 * self.PAD) / max(self.n1 - self.n0, 1), 1.0)
        if self.part:
            a, b = self.x_of(self.part[0]), self.x_of(self.part[1])
            p.fillRect(QtCore.QRectF(a, 4, max(b - a, 2.0), h - 8), QtGui.QColor("#2a4a73"))
        for n in self.cached:                        # decoded and ready: what playback can show without waiting
            p.fillRect(QtCore.QRectF(self.x_of(n) - px / 2, h - 7, px, 3), QtGui.QColor("#4a4944"))
        for n in self.linked:                        # where the automatic track has the object: gaps show as gaps
            p.fillRect(QtCore.QRectF(self.x_of(n) - px / 2, 5, px, 4), QtGui.QColor(AUTO))
        for n in self.disputed:                      # and where its two links disagree
            p.fillRect(QtCore.QRectF(self.x_of(n) - max(px, 2) / 2, 4, max(px, 2), 6), QtGui.QColor(DISPUTED))
        for i, c in enumerate(CLASSES):
            for n in self.marks.get(c, {}):
                p.fillRect(QtCore.QRectF(self.x_of(n) - 1.5, 12 + 4 * i, 3, 3.4), QtGui.QColor(COLOURS[i]))
        p.setPen(QtGui.QPen(QtGui.QColor("#f2f0e9"), 1.4))
        x = self.x_of(self.n)
        p.drawLine(QtCore.QPointF(x, 1), QtCore.QPointF(x, h - 1))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.scrubbed.emit(self.n_at(e.position().x()))

    def mouseMoveEvent(self, e):
        n = self.n_at(e.position().x())
        if e.buttons() & Qt.MouseButton.LeftButton:
            self.scrubbed.emit(n)
        QtWidgets.QToolTip.showText(e.globalPosition().toPoint(), f"frame {n}, at {(n - 1) / self.fps:.3f} s", self)


class Loupe(QtWidgets.QLabel):
    """The pixels under the cursor, enlarged and never interpolated, with the
    cursor's own position to a fraction of a pixel."""
    HALF, ZOOM = 10, 10

    def __init__(self):
        super().__init__()
        side = (2 * self.HALF + 1) * self.ZOOM
        self.setFixedSize(side, side)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def look(self, img, x, y, marks):
        r, z = self.HALF, self.ZOOM
        cx, cy = int(round(x)), int(round(y))
        crop = img.copy(cx - r, cy - r, 2 * r + 1, 2 * r + 1).scaled(self.width(), self.height(),
                                                                     Qt.AspectRatioMode.IgnoreAspectRatio,
                                                                     Qt.TransformationMode.FastTransformation)
        p = QtGui.QPainter(crop)

        def at(u, v):                                # image coordinates -> loupe pixels
            return (u - cx + r + 0.5) * z, (v - cy + r + 0.5) * z
        for (mx, my), colour in marks:
            u, v = at(mx, my)
            if 0 <= u <= self.width() and 0 <= v <= self.height():
                p.setPen(QtGui.QPen(QtGui.QColor(colour), 2))
                p.drawLine(QtCore.QPointF(u - 9, v), QtCore.QPointF(u + 9, v))
                p.drawLine(QtCore.QPointF(u, v - 9), QtCore.QPointF(u, v + 9))
        u, v = at(x, y)
        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 150), 1))
        p.drawLine(QtCore.QPointF(u, 0), QtCore.QPointF(u, self.height()))
        p.drawLine(QtCore.QPointF(0, v), QtCore.QPointF(self.width(), v))
        p.end()
        self.setPixmap(QtGui.QPixmap.fromImage(crop))


class TrackStrip(QtWidgets.QLabel):
    """`forensics.track_strip`, the pipeline's own check, with the frame number
    under each tile. Click a tile to go to that frame."""
    chosen = QtCore.Signal(int)

    def __init__(self, path, frames):
        super().__init__()
        strip = QtGui.QPixmap(path)
        self.frames, self.tile = list(frames), strip.width() / max(len(frames), 1)
        sheet = QtGui.QPixmap(strip.width(), strip.height() + 20)
        sheet.fill(QtGui.QColor("#141415"))
        p = QtGui.QPainter(sheet)
        p.drawPixmap(0, 0, strip)
        p.setPen(QtGui.QColor("#dddddd"))
        for i, n in enumerate(self.frames):
            p.drawText(QtCore.QRectF(i * self.tile, strip.height(), self.tile, 20), Qt.AlignmentFlag.AlignCenter, str(n))
        p.end()
        self.setPixmap(sheet)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, e):
        i = int(e.position().x() // self.tile)
        if 0 <= i < len(self.frames):
            self.chosen.emit(self.frames[i])


class Overview(QtWidgets.QDialog):
    """The whole clip at once, as evenly spaced tiles. Click one to go there."""
    chosen = QtCore.Signal(int)
    TILE = 224

    def __init__(self, parent, clip, store, n_tiles=72):
        super().__init__(parent)
        self.setWindowTitle("overview — click a picture to go to its frame")
        self.resize(1180, 720)
        self.frames = [int(n) for n in np.unique(np.linspace(clip.n0, clip.n1, min(n_tiles, clip.n1 - clip.n0 + 1)).round())]
        self.list = QtWidgets.QListWidget()
        self.list.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.list.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.list.setMovement(QtWidgets.QListView.Movement.Static)
        self.list.setIconSize(QtCore.QSize(self.TILE, int(self.TILE * clip.H / clip.W)))
        self.list.setSpacing(6)
        self._row = {}
        blank = QtGui.QPixmap(self.list.iconSize())
        blank.fill(QtGui.QColor("#232326"))
        for n in self.frames:
            it = QtWidgets.QListWidgetItem(QtGui.QIcon(blank), f"{n}    {(n - 1) / clip.fps:.2f} s")
            it.setData(Qt.ItemDataRole.UserRole, n)
            self._row[n] = it
            self.list.addItem(it)
        self.list.itemClicked.connect(lambda it: self.chosen.emit(it.data(Qt.ItemDataRole.UserRole)))
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addWidget(self.list)
        self.filled = 0
        store.thumb_arrived.connect(self._fill)
        for n in self.frames:
            store.thumb(n, self.TILE)

    def _fill(self, n, img):
        it = self._row.get(n)
        if it is not None:
            it.setIcon(QtGui.QIcon(QtGui.QPixmap.fromImage(img)))
            self.filled += 1


# ---- undo -------------------------------------------------------------------------------
class _Put(QtGui.QUndoCommand):
    """Place, move or (with xy None) delete one mark. The MarkSet is what changes;
    this only remembers what was there."""

    def __init__(self, window, cls, n, xy, how=None, nudge=False):
        was = window.ms.marks.get(cls, {}).get(n)
        super().__init__(f"{'delete' if xy is None else 'move' if was else 'place'} {cls} on frame {n}")
        self.w, self.cls, self.n, self.xy, self.how, self.nudge = window, cls, n, xy, how, nudge
        self.was, self.was_how = was, window.ms.how_of(cls, n)

    def _set(self, xy, how):
        if xy is None:
            self.w.ms.remove_last(self.cls, self.n)
        else:
            self.w.ms.add(self.cls, self.n, *xy, how=how)
        self.w.marks_changed()

    def redo(self):
        self._set(self.xy, self.how)

    def undo(self):
        self._set(self.was, self.was_how)

    def id(self):
        return 1 if self.nudge else -1

    def mergeWith(self, other):
        """A run of nudges on one mark is one step to undo, back to where it started."""
        if not (other.nudge and other.cls == self.cls and other.n == self.n):
            return False
        self.xy = other.xy
        return True


# ---- the window -------------------------------------------------------------------------
class QtMarker(QtWidgets.QMainWindow):
    """The Qt front end. Marker-shaped: same constructor, same `n`, `cls`, `ms`,
    `goto`, `finish`, `run`, so `mark.main` and the tests can treat the two alike."""
    candidates_ready = QtCore.Signal(object, object)          # the request key, and the candidates or an Exception
    link_progress = QtCore.Signal(int, object)                # a class and its autolink.Link, from the linking thread
    link_finished = QtCore.Signal()                           # every class has been linked, or it was stopped
    strip_ready = QtCore.Signal(object)                       # [(class, the track strip's path, its frames)]

    def __init__(self, clip, ms, out_prefix, cases=None, workdir=None):
        app = application()                           # before any widget, this one included
        super().__init__()
        self.app = app
        self.clip, self.ms, self.out = clip, ms, out_prefix
        self.cases, self.workdir = cases, workdir     # for File -> Open: where the next clip's case and frames go
        self._closing = False
        self.n, self.cls = clip.n0, 0
        info = getattr(clip, "info", None)
        self.fps = info["fps"] if info else Fraction(clip.fps).limit_denominator(1_001_000)
        self.store = FrameStore(clip)
        self.store.arrived.connect(self._frame_arrived)
        self._img = None
        self._undo = QtGui.QUndoStack(self)
        self._undo.cleanChanged.connect(self._retitle)
        self._show_track = True
        self._overlay = []
        self.saved_strip = None

        self.view = FrameView(clip.W, clip.H)
        self.view.pressed.connect(self._place)
        self.view.hovered.connect(self._hover)
        self._cursor = None

        self.timeline = Timeline(clip.n0, clip.n1, float(self.fps))
        self.timeline.scrubbed.connect(self._scrub)
        # a drag on the timeline asks for a frame at every mouse move, and a frame not yet
        # decoded takes 60 ms: go to the newest request only, when the event queue lets us
        self._scrub_to, self._scrub_timer = None, QtCore.QTimer(self)
        self._scrub_timer.setSingleShot(True)
        self._scrub_timer.setInterval(0)
        self._scrub_timer.timeout.connect(lambda: self.goto(self._scrub_to))

        # playback: the clock says which frame is due; the timer only asks it often
        self._playing, self._speed = False, SPEEDS.index(Fraction(1))
        self._clock, self._play_from, self.shown, self.skipped = QtCore.QElapsedTimer(), self.n, 0, 0
        self._timer = QtCore.QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(4)
        self._timer.timeout.connect(self._tick)

        # the detector, off the GUI thread: a second a frame, and ~20 s once for the static masks
        self._cand_on, self._cand_cache, self._cand_busy, self._masks = False, {}, None, None
        self._cand_wait = QtCore.QTimer(self)
        self._cand_wait.setSingleShot(True)
        self._cand_wait.setInterval(200)
        self._cand_wait.timeout.connect(self._ask_detector)
        self.candidates_ready.connect(self._got_candidates)
        self._masks_lock = threading.Lock()

        # the link: autolink on its own thread (and its own processes), reporting frame by frame.
        # One per class that can be tracked; the candidates are kept, so that linking again
        # after one more mark runs the detector only on frames it has not seen at that scale
        self.links, self._link_marks, self._link_paths, self._link_said = {}, {}, {}, {}
        self._link_thread, self._link_stop, self._link_busy = None, threading.Event(), False
        self._link_cache, self.track_strip, self._snap_wait = {}, None, None
        self._tmp = tempfile.TemporaryDirectory(prefix="mcdonald-")    # the track strips on their way to the screen
        self.link_progress.connect(self._on_link)
        self.link_finished.connect(self._on_link_finished)
        self.strip_ready.connect(self._show_track_strip)

        self.measure_panel = self.report_page = None   # Measure: made when first asked for
        self.find_panel, self._proposal_path = None, None

        self._build()
        self.resize(1500, 920)
        self.goto(self.n)
        self.marks_changed()
        self._undo.setClean()

    # -- layout --------------------------------------------------------------------------
    def _build(self):
        rows = {a.id: a for a in actions.ACTIONS}

        def button(text, act, checkable=False):
            """A button for a row of the table: its help and its key are the tooltip."""
            b = QtWidgets.QToolButton()
            b.setText(text)
            b.setToolTip(f"{rows[act].help} ({actions.spoken(rows[act].keys[0])})")
            b.setCheckable(checkable)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda _=False: self.do(act))
            return b

        bar = QtWidgets.QHBoxLayout()
        bar.setContentsMargins(8, 4, 8, 0)
        for text, act in (("⏮", "first"), ("−10", "back10"), ("−1", "prev")):
            bar.addWidget(button(text, act))
        self.play_button = button("▶", "play")
        bar.addWidget(self.play_button)
        for text, act in (("+1", "next"), ("+10", "on10"), ("⏭", "last")):
            bar.addWidget(button(text, act))
        self.speed_label = QtWidgets.QLabel()
        bar.addWidget(self.speed_label)
        bar.addSpacing(16)
        self.frame_box = QtWidgets.QSpinBox()
        self.frame_box.setRange(self.clip.n0, self.clip.n1)
        self.frame_box.setPrefix("frame ")
        self.frame_box.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.frame_box.setKeyboardTracking(False)
        self.frame_box.valueChanged.connect(self._frame_typed)
        bar.addWidget(self.frame_box)
        bar.addStretch(1)
        self.class_buttons = []
        for i, c in enumerate(CLASSES):
            b = button(f"{i + 1} {c}", f"class_{i + 1}", checkable=True)
            b.setStyleSheet(f"QToolButton {{ color: {COLOURS[i]}; padding: 2px 7px; }} "
                            f"QToolButton:checked {{ background: {COLOURS[i]}; color: #0b0b0b; }}")
            self.class_buttons.append(b)
            bar.addWidget(b)

        mid = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(mid)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(self.view, 1)
        lay.addLayout(bar)
        lay.addWidget(self.timeline)
        self.setCentralWidget(mid)

        # the dock: loupe, what the marks say, the marks themselves, the detector
        side = QtWidgets.QWidget()
        col = QtWidgets.QVBoxLayout(side)
        self.loupe = Loupe()
        col.addWidget(self.loupe, 0, Qt.AlignmentFlag.AlignHCenter)
        self.cursor_label = QtWidgets.QLabel("—")
        col.addWidget(self.cursor_label)
        self.velocity_label = QtWidgets.QLabel()
        self.velocity_label.setWordWrap(True)
        self.velocity_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        col.addWidget(self.velocity_label)
        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["what", "frame", "x", "y", "how"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.cellClicked.connect(self._row_clicked)
        col.addWidget(self.table, 1)
        det = QtWidgets.QHBoxLayout()
        self.cand_box = QtWidgets.QCheckBox(f"show spots ({actions.spoken(rows['candidates'].keys[0])})")
        self.cand_box.setToolTip(rows["candidates"].help)
        self.cand_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cand_box.toggled.connect(self.set_candidates)
        self.size_box = QtWidgets.QSpinBox()
        self.size_box.setRange(3, 60)
        self.size_box.setValue(9)
        self.size_box.setSuffix(" pixels")
        self.size_box.setToolTip("the spot size: how big a spot the computer looks for")
        self.size_box.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.size_box.setKeyboardTracking(False)
        self.size_box.valueChanged.connect(lambda _: (self._candidates_stale(), self.view.setFocus()))
        self.dark_box = QtWidgets.QCheckBox("dark")
        self.dark_box.setToolTip("look for an object that is darker than what is around it, not brighter")
        self.dark_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.dark_box.toggled.connect(lambda _: self._candidates_stale())
        self.auto_box = QtWidgets.QCheckBox("choose for me")
        self.auto_box.setChecked(True)
        self.auto_box.setToolTip("when linking, let the computer choose the spot size, and bright or dark, from your marks")
        self.auto_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for w in (self.cand_box, self.size_box, self.dark_box, self.auto_box):
            det.addWidget(w)
        col.addLayout(det)
        find_row = next(a for a in actions.ACTIONS if a.id == "find")
        self.find_button = QtWidgets.QPushButton(f"find the object ({actions.spoken(find_row.keys[0])})…")
        self.find_button.setToolTip(find_row.help)
        self.find_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.find_button.clicked.connect(lambda _=False: self.do("find"))
        col.addWidget(self.find_button)
        self.link_button = QtWidgets.QPushButton()
        self.link_button.setToolTip("the computer follows the object from your marks, forward and backward from each, and "
                                   "draws the track as it grows")
        self.link_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.link_button.clicked.connect(lambda _=False: self.do("link"))
        self._say_link_button()
        col.addWidget(self.link_button)
        self.link_label = QtWidgets.QLabel("")
        self.link_label.setWordWrap(True)
        self.link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        col.addWidget(self.link_label)
        # what comes after the link, where someone who has only the window will find it
        key = actions.spoken(next(a for a in actions.ACTIONS if a.id == "measure").keys[0])
        self.measure_button = QtWidgets.QPushButton(f"measure this video ({key})…")
        self.measure_button.setToolTip(next(a for a in actions.ACTIONS if a.id == "measure").help)
        self.measure_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.measure_button.clicked.connect(lambda _=False: self.do("measure"))
        col.addWidget(self.measure_button)
        # where 's' writes. It was a flag's default, relative to a working directory that
        # someone who started this from a desktop never chose and cannot see
        self.case_label = QtWidgets.QLabel()
        self.case_label.setWordWrap(True)
        self.case_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.case_label.setStyleSheet("color: #898781;")
        col.addWidget(self.case_label)
        self._say_case()
        dock = QtWidgets.QDockWidget("marks")
        dock.setWidget(side)
        dock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        self.status = QtWidgets.QLabel()
        self.note = QtWidgets.QLabel()
        self.statusBar().addWidget(self.status, 1)
        self.statusBar().addPermanentWidget(self.note)
        self.statusBar().setSizeGripEnabled(False)
        self._build_menus()

    def _build_menus(self):
        """Every row of actions.ACTIONS as a QAction: in a menu, with its shortcut, and its
        help in the status bar while the pointer is on it. There is no keyPressEvent: a key
        that is not in the table does nothing, and one that is cannot go missing from the menus."""
        self._handlers = self.handlers()
        self.acts, menus, classes = {}, {}, QtGui.QActionGroup(self)
        for name in actions.MENUS:
            menus[name] = self.menuBar().addMenu(f"&{name}")
        for a in actions.for_window("qt"):
            if a.menu not in menus:                   # "Edit>Nudge the mark": a submenu, made when first met
                top, sub = a.menu.split(">")
                menus[a.menu] = menus[top].addMenu(sub)
            act = self.acts[a.id] = QtGui.QAction(a.text, self)
            act.setShortcuts([QtGui.QKeySequence(k) for k in a.keys])
            act.setStatusTip(a.help or a.group.help)
            act.setCheckable(a.check)
            # macOS moves an action it takes for Quit or About into the application menu,
            # going by its text. Only the one that is Quit may go
            act.setMenuRole(QtGui.QAction.MenuRole.QuitRole if a.id == "quit" else QtGui.QAction.MenuRole.NoRole)
            if a.id.startswith("class_"):
                classes.addAction(act)
            act.triggered.connect(lambda _=False, i=a.id: self.do(i))
            if a.sep:
                menus[a.menu].addSeparator()
            menus[a.menu].addAction(act)
            self.addAction(act)                       # the window's too, so the shortcut does not depend on the menu bar

    def handlers(self):
        """What each row of actions.ACTIONS is, in this window."""
        h = {"open_clip": self.open_clip, "open_id": self.open_by_id, "open_marks": self.open_marks,
             "save_to": self.save_to, "desktop": self.add_to_desktop,
             "save": self.finish, "quit": self.save_and_quit, "undo": self._undo.undo, "redo": self._undo.redo,
             "delete": self.delete_here, "fit": self.view.fit, "overview": self.open_overview,
             "candidates": lambda: self.set_candidates(not self._cand_on), "other_frames": self.toggle_other_frames,
             "prev": lambda: self.goto(self.n - 1), "next": lambda: self.goto(self.n + 1),
             "back10": lambda: self.goto(self.n - 10), "on10": lambda: self.goto(self.n + 10),
             "first": lambda: self.goto(self.clip.n0), "last": lambda: self.goto(self.clip.n1),
             "prev_marked": lambda: self._marked_neighbour(-1), "next_marked": lambda: self._marked_neighbour(+1),
             "play": self.toggle_play, "slower": lambda: self.change_speed(-1), "faster": lambda: self.change_speed(+1),
             "link": self.toggle_link, "keys": self.show_keys,
             "find": self.find_object,
             "measure": self.measure, "report": self.show_report, "folder": self.open_folder,
             "first_run": self.show_first_run}
        h.update({f"class_{i + 1}": lambda i=i: self.set_class(i) for i in range(len(CLASSES))})
        h.update({act: lambda d=d: self.nudge(*d) for act, d in actions.NUDGES.items()})
        return h

    def do(self, act):
        """One way in for a menu, a shortcut and a button."""
        self._handlers[act]()
        self._sync_actions()

    def _sync_actions(self):
        """The ticks in the menus, from the state they stand for. Qt ticks a checkable action
        when it is triggered, whether or not what it asked for then happened."""
        on = {"candidates": self._cand_on, "other_frames": self._show_track,
              **{f"class_{i + 1}": i == self.cls for i in range(len(CLASSES))}}
        for act, state in on.items():
            self.acts[act].setChecked(bool(state))

    @QtCore.Slot()
    def _retitle(self, *_):
        self.setWindowTitle(f"mcdonald — {self.ms.tag}{'' if self._undo.isClean() else ' *'}")

    # -- where we are ----------------------------------------------------------------------
    def goto(self, n):
        n = int(np.clip(n, self.clip.n0, self.clip.n1))
        forward = n >= self.n
        self.n = n
        self._img = self.store.get(n)
        self.view.pix.setPixmap(QtGui.QPixmap.fromImage(self._img))
        ahead = 32 if self._playing else 8
        step = 1 if forward else -1
        self.store.want([n + step * k for k in range(1, ahead + 1)] + [n - step * k for k in range(1, 5)])
        self.draw()

    def draw(self):
        """Everything that depends on the frame or the marks, redrawn from the MarkSet."""
        sc = self.view.scene()
        for it in self._overlay:
            sc.removeItem(it)
        self._overlay = []
        here = self.ms.marks.get(CLASSES[self.cls], {})
        if self._show_track and len(here) > 1:
            ns = sorted(here)
            path = QtGui.QPainterPath(QtCore.QPointF(*here[ns[0]]))
            for k in ns[1:]:
                path.lineTo(*here[k])
            line = sc.addPath(path, QtGui.QPen(QtGui.QColor(COLOURS[self.cls]), 0, Qt.PenStyle.DotLine))
            line.setZValue(4)
            self._overlay.append(line)
            for k in ns:
                if k != self.n:
                    dot = Cross(*here[k], COLOURS[self.cls], arms=(0, 3), width=1.5)
                    dot.setZValue(4)
                    sc.addItem(dot)
                    self._overlay.append(dot)
        self.crosses = []
        for ci, c in enumerate(CLASSES):
            xy = self.ms.marks.get(c, {}).get(self.n)
            if xy:
                item = Cross(xy[0], xy[1], COLOURS[ci])
                sc.addItem(item)
                self._overlay.append(item)
                self.crosses.append(item)
        self.boxes = {}
        for ci, link in self.links.items():
            if self.n in link.track:
                box = self.boxes[ci] = Box(*link.track[self.n], disputed=link.source.get(self.n) == "disputed",
                                           label="" if ci == 0 else str(ci + 1))
                sc.addItem(box)
                self._overlay.append(box)
        self.box = self.boxes.get(self._link_class())
        self.rings = []
        if self._cand_on and not self._playing:
            got = self._cand_cache.get(self._cand_key())
            if got is None:
                self._cand_wait.start()
            else:
                for rank, (x, y, v) in enumerate(got, 1):
                    ring = Ring(x, y, rank, v)
                    sc.addItem(ring)
                    self._overlay.append(ring)
                    self.rings.append(ring)
        self.status.setText(status_line(self.clip, self.ms, self.n, self.cls))
        self.status.setStyleSheet(f"color: {COLOURS[self.cls]};")
        self.frame_box.blockSignals(True)
        self.frame_box.setValue(self.n)
        self.frame_box.blockSignals(False)
        for i, b in enumerate(self.class_buttons):
            b.setChecked(i == self.cls)
        self._sync_actions()
        self._timeline_state()
        self._look()

    @QtCore.Slot(int)
    def _frame_arrived(self, n):                     # from a decoding thread, queued onto this one
        self._timeline_state()

    def _timeline_state(self):
        link = self.link
        self.timeline.show_state(self.n, self.ms.marks, self.store.cached(),
                                 sorted(link.track) if link is not None else (), link.disputed() if link is not None else ())

    def marks_changed(self):
        """The table and the velocity, which change with the marks and not with the frame."""
        rows = [(c, n, xy) for c in CLASSES for n, xy in sorted(self.ms.marks.get(c, {}).items())]
        self.table.setRowCount(len(rows))
        for r, (c, n, (x, y)) in enumerate(rows):
            how = self.ms.how_of(c, n)
            for k, text in enumerate((c, str(n), f"{x:.2f}", f"{y:.2f}", self.ms.kind(c, n))):
                it = QtWidgets.QTableWidgetItem(text)
                it.setForeground(QtGui.QColor(COLOURS[CLASSES.index(c)]))
                if how:
                    it.setToolTip(how)
                self.table.setItem(r, k, it)
        self._rows = rows
        self._say_link()
        v = self.ms.velocity()
        self.velocity_label.setText(
            "two marks on the object give its speed and direction" if v is None else
            f"moves ({v[0]:+.2f}, {v[1]:+.2f}) pixels each frame (right, down)\n"
            f"speed: {np.hypot(*v) * float(self.fps):.0f} pixels each second, at {float(self.fps):.4g} frames a second\n"
            f"linking starts from (frame, x, y) = {seed_text(self.ms.seed())}")
        self._retitle()
        self.draw()

    def set_class(self, i):
        self.cls = i
        self.draw()

    # -- marks -----------------------------------------------------------------------------
    def _place(self, p, snap=False):
        if snap:
            self._snap(p.x(), p.y())
        else:
            self._undo.push(_Put(self, CLASSES[self.cls], self.n, (p.x(), p.y())))

    def _snap(self, x, y):
        """Put the mark on the detector's nearest candidate, if there is one close by, and
        record that. Asks the detector first if this frame has not been through it."""
        key = self._cand_key()
        if key not in self._cand_cache:
            self._snap_wait = (key, self.cls, x, y)
            self._ask_detector(force=True)
            return
        self._snap_wait = None
        kind = f"{'dark' if key[2] else 'bright'} {key[1]}-pixel"
        near = min(self._cand_cache[key], key=lambda c: np.hypot(c[0] - x, c[1] - y), default=None)
        d = None if near is None else float(np.hypot(near[0] - x, near[1] - y))
        if d is None or d > SNAP_PX:
            self.note.setText(f"No mark was placed: the computer found no {kind} spot within {SNAP_PX:g} pixels of your click"
                              + ("" if d is None else f" (the nearest is {d:.0f} pixels away)")
                              + ". Click without shift to mark by hand, or change the spot size.")
            return
        how = f"snapped to the {key[1]} px {'dark' if key[2] else 'bright'} candidate {d:.1f} px from a click at ({x:.1f}, {y:.1f})"
        self._undo.push(_Put(self, CLASSES[self.cls], self.n, (near[0], near[1]), how=how))      # `how` is the record, in the files' words
        self.note.setText(f"The mark was put on the {kind} spot the computer found, {d:.1f} pixels from your click. "
                          "That place is the computer's, not yours, and the saved files say so.")

    def nudge(self, dx, dy):
        xy = self.ms.marks.get(CLASSES[self.cls], {}).get(self.n)
        if xy is not None:                           # a nudged mark is a hand's again, wherever it came from
            self._undo.push(_Put(self, CLASSES[self.cls], self.n, (xy[0] + dx, xy[1] + dy), nudge=True))

    def _scrub(self, n):
        self._scrub_to = n
        if not self._scrub_timer.isActive():
            self._scrub_timer.start()

    def delete_here(self):
        if self.ms.marks.get(CLASSES[self.cls], {}).get(self.n) is not None:
            self._undo.push(_Put(self, CLASSES[self.cls], self.n, None))

    def _row_clicked(self, row, _col):
        c, n, _ = self._rows[row]
        self.cls = CLASSES.index(c)
        self.goto(n)

    def _marked_neighbour(self, step):
        ns = [n for n in self.ms.frames(CLASSES[self.cls]) if (n - self.n) * step > 0]
        if ns:
            self.goto(min(ns) if step > 0 else max(ns))

    # -- the cursor ------------------------------------------------------------------------
    def _hover(self, p):
        self._cursor = (p.x(), p.y())
        self._look()

    def _look(self):
        if self._cursor is None or self._img is None:
            return
        x, y = self._cursor
        marks = [(self.ms.marks[c][self.n], COLOURS[i]) for i, c in enumerate(CLASSES)
                 if self.n in self.ms.marks.get(c, {})]
        self.loupe.look(self._img, x, y, marks)
        ix, iy = int(round(x)), int(round(y))
        if 0 <= ix < self.clip.W and 0 <= iy < self.clip.H:
            c = self._img.pixelColor(ix, iy)
            self.cursor_label.setText(f"x {x:.1f}   y {y:.1f}     brightness {(c.red() + c.green() + c.blue()) / 3:.0f} of 255"
                                      f"     zoom ×{self.view.magnification():.2g}")

    # -- playback --------------------------------------------------------------------------
    def speed(self):
        return SPEEDS[self._speed]

    def toggle_play(self):
        if self._playing:
            self._playing = False
            self._timer.stop()
        else:
            if self.n >= self.clip.n1:
                self.goto(self.clip.n0)
            self._playing, self._play_from, self.shown, self.skipped = True, self.n, 0, 0
            self._clock.start()
            self._timer.start()
        self.play_button.setText("⏸" if self._playing else "▶")
        self._say_speed()
        self.draw()

    def change_speed(self, step):
        self._speed = int(np.clip(self._speed + step, 0, len(SPEEDS) - 1))
        if self._playing:                            # restart the clock, or the change would apply to time already played
            self._play_from = self.n
            self._clock.start()
        self._say_speed()

    def _say_speed(self):
        s = self.speed()
        text = f"  {s}×" if s != 1 else "  1×"
        if self._playing or self.shown:
            text += f"   {self.shown} shown, {self.skipped} skipped"
        self.speed_label.setText(text)

    def _tick(self):
        due = self._play_from + int(Fraction(self._clock.nsecsElapsed(), 10 ** 9) * self.fps * self.speed())
        if due > self.n:
            due = min(due, self.clip.n1)
            self.skipped += due - self.n - 1         # frames the clock passed while one was decoding
            self.shown += 1
            self.goto(due)
            self._say_speed()
        if self.n >= self.clip.n1:
            self.toggle_play()

    # -- the detector ----------------------------------------------------------------------
    def _cand_key(self):
        return self.n, self.size_box.value(), self.dark_box.isChecked()

    def set_candidates(self, on):
        self._cand_on = bool(on)
        self.cand_box.blockSignals(True)
        self.cand_box.setChecked(self._cand_on)
        self.cand_box.blockSignals(False)
        if not on:
            self.note.setText("")
        self.draw()

    def _candidates_stale(self):
        if self._cand_on:
            self.draw()

    def _ask_detector(self, force=False):
        key = self._cand_key()
        if not (self._cand_on or force) or self._playing or key in self._cand_cache or self._cand_busy is not None:
            return
        self._cand_busy = key
        self.note.setText(MASKS if self._masks is None else f"Looking for spots on frame {key[0]}…")

        def job():
            try:                                     # what the linker would be given on this frame, threshold and all
                out = vf.frame_candidates(self.clip, key[0], self._static_masks(), None, float(key[1]), key[2],
                                          autolink.MIN_RESP)
            except Exception as ex:                  # shown in the window; a dead thread would say nothing
                out = ex
            self.candidates_ready.emit(key, out)
        threading.Thread(target=job, daemon=True, name="mcdonald-detector").start()

    def _static_masks(self):
        """Once per clip, whichever of the detector and the link asks first."""
        with self._masks_lock:
            if self._masks is None:
                self._masks = vf.static_masks(self.clip)
            return self._masks

    @QtCore.Slot(object, object)
    def _got_candidates(self, key, out):
        self._cand_busy = None
        if isinstance(out, Exception):
            self.note.setText(f"Looking for spots did not work: {out}")
            return
        self._cand_cache[key] = out
        self.note.setText(f"{len(out)} spot{'' if len(out) == 1 else 's'} found on frame {key[0]}; number 1 stands out the most. "
                          "The computer finds small spots. You say which one is the object.")
        self.draw()
        if self._snap_wait is not None:              # a shift+click was waiting for this
            wkey, cls, x, y = self._snap_wait
            if wkey == key and wkey == self._cand_key() and cls == self.cls:
                self._snap(x, y)
            elif wkey == self._cand_key():
                self._ask_detector(force=True)
            else:
                self._snap_wait = None

    # -- the link --------------------------------------------------------------------------
    def _link_class(self):
        """The class whose link the timeline and the labels follow: the current one if it
        can be tracked, else the object."""
        return self.cls if CLASSES[self.cls] in LINKED else 0

    @property
    def link(self):
        return self.links.get(self._link_class())

    def linking(self):
        return self._link_busy

    def toggle_link(self):
        if self._link_busy:
            self._link_stop.set()
            return
        order = sorted((ci for ci, c in enumerate(CLASSES) if c in LINKED and self.ms.marks.get(c)),
                       key=lambda ci: ci != self._link_class())
        if not order:
            self.link_label.setText("Mark the object first. Linking starts from a mark, and a second mark gives the "
                                    "speed and direction that a fast object needs.")
            return
        self._link_stop = threading.Event()          # a new one: the last link's thread may still hold the old
        self._link_busy = True
        for ci in [ci for ci in self.links if ci not in order]:      # its marks are gone, so its track goes too
            del self.links[ci]
            self._link_said.pop(ci, None)
            self._draw_link_path(ci)
        for ci in order:
            self._link_marks[ci] = dict(self.ms.marks[CLASSES[ci]])
            self.links.pop(ci, None)
            self._link_said[ci] = ""
            self._draw_link_path(ci)
        auto = self.auto_box.isChecked()
        size, dark = (None, None) if auto else (float(self.size_box.value()), self.dark_box.isChecked())
        building, stop, marks = self._masks is None, self._link_stop, dict(self._link_marks)

        def job():
            done = []
            try:
                if building:
                    self.link_progress.emit(order[0], autolink.Link("masks", MASKS))
                for ci in order:
                    last = None
                    for last in autolink.link_from_marks(self.clip, marks[ci], masks=self._static_masks(), size=size,
                                                         dark=dark, stop=stop.is_set, cache=self._link_cache):
                        self.link_progress.emit(ci, last)
                    if last is not None and last.track:
                        done.append((ci, last))
                    if stop.is_set():
                        break
            except Exception as ex:                  # shown in the window; a dead thread would say nothing
                self.link_progress.emit(order[0], autolink.Link("done", f"Linking did not work: {ex}", done=True))
            self.link_finished.emit()
            strips = []
            try:
                for ci, last in done:                # after 'finished': 'l' pressed meanwhile starts a new link
                    path = os.path.join(self._tmp.name, f"track_strip_{CLASSES[ci]}.png")
                    strips.append((ci, path, vf.track_strip(self.clip, last.track, path)))
            except OSError:                          # the window closed under us and took the directory with it
                return
            if strips and not stop.is_set():
                self.strip_ready.emit(strips)
        self._link_thread = threading.Thread(target=job, daemon=True, name="mcdonald-link")
        self._link_thread.start()
        self._say_link_button()

    def _draw_link_path(self, ci):
        old = self._link_paths.pop(ci, None)
        if old is not None:
            self.view.scene().removeItem(old)
        link = self.links.get(ci)
        if link is not None and len(link.track) > 1:
            ns = sorted(link.track)
            path = QtGui.QPainterPath(QtCore.QPointF(*link.track[ns[0]]))
            for a, b in zip(ns, ns[1:]):             # a gap in the track is a gap in the line, not a chord across it
                (path.lineTo if b == a + 1 else path.moveTo)(*link.track[b])
            self._link_paths[ci] = self.view.scene().addPath(path, QtGui.QPen(QtGui.QColor(AUTO), 0))
            self._link_paths[ci].setZValue(3)

    @QtCore.Slot(int, object)
    def _on_link(self, ci, link):
        if link.track or link.done or ci not in self.links:
            self.links[ci] = link
        if link.size is not None and ci == self._link_class():   # show the choice where the detector's controls are
            for box in (self.size_box, self.dark_box):
                box.blockSignals(True)
            self.size_box.setValue(int(round(link.size)))
            self.dark_box.setChecked(bool(link.dark))
            for box in (self.size_box, self.dark_box):
                box.blockSignals(False)
        self._draw_link_path(ci)
        self._link_said[ci] = link.say
        self._say_link()
        self.draw()

    @QtCore.Slot()
    def _on_link_finished(self):
        self._link_busy = False
        self._say_link_button()

    def _say_link_button(self):
        key = actions.spoken(next(a for a in actions.ACTIONS if a.id == "link").keys[0])
        self.link_button.setText(f"stop linking ({key})" if self._link_busy else f"link from the marks ({key})")

    def _say_link(self):
        lines = []
        for ci in sorted(self._link_said):
            if not self._link_said[ci]:
                continue
            text = (f"{CLASSES[ci]}: " if len(self._link_said) > 1 else "") + self._link_said[ci]
            link = self.links.get(ci)
            if link is not None and link.track and self._link_marks.get(ci) != self.ms.marks.get(CLASSES[ci], {}):
                text += "\nThe marks have changed since this track was made. Press l to link again: only the new frames are worked out."
            lines.append(text)
        self.link_label.setText("\n\n".join(lines))

    @QtCore.Slot(object)
    def _show_track_strip(self, strips):
        """The pipeline's own check, put in front of the person who knows which thing
        the object is. CHECK WHAT IT LOCKED ONTO, as link_track's docstring says."""
        if self.track_strip is not None:
            self.track_strip.close()
        d = self.track_strip = beside(self)
        d.setWindowTitle("the track — is this the object in every picture?")
        lay = QtWidgets.QVBoxLayout(d)
        d.strips, wide, high = {}, 0, 90
        for ci, path, frames in strips:
            strip = d.strips[ci] = TrackStrip(path, frames)
            strip.chosen.connect(lambda n, ci=ci: (self.set_class(ci), self.goto(n)))
            if len(strips) > 1:
                lay.addWidget(QtWidgets.QLabel(CLASSES[ci]))
            area = QtWidgets.QScrollArea()
            area.setWidget(strip)
            lay.addWidget(area)
            wide, high = max(wide, strip.pixmap().width()), high + strip.pixmap().height() + 40
        d.strip = d.strips[min(d.strips)]
        lay.addWidget(QtWidgets.QLabel("Small pictures cut from the video along the track. Click one to go to its frame. "
                                       "Play the video to see if the box stays on the object."))
        d.resize(min(wide + 40, 1500), min(high, 900))
        d.show()

    # -- overview --------------------------------------------------------------------------
    def open_overview(self):
        self.overview = Overview(self, self.clip, self.store)
        self.overview.chosen.connect(self._from_overview)
        self.overview.show()

    def _from_overview(self, n):
        self.overview.close()
        self.goto(n)

    # -- what the rows of the table are, where that is more than a line ------------------------
    def toggle_other_frames(self):
        self._show_track = not self._show_track
        self.draw()

    def save_and_quit(self):
        self.finish(show_strip=False)                # the window is going; the terminal says where the strip is
        self.close()

    def _say_case(self):
        self.case_label.setText(f"saves to {Path(self.out).parent.resolve()}")
        self.case_label.setToolTip("To change it, use File → Save to a different folder")

    def save_to(self, folder=None):
        folder = folder or choose_folder(self, "save this video's files in…", str(Path(self.out).parent))
        if folder:
            self.out = str(Path(folder) / self.ms.tag)
            # remembered for the next video: its folder goes beside this one's, if this is named for the video
            settings().setValue("cases", str(Path(folder).parent if Path(folder).name == self.ms.tag else Path(folder)))
            self._say_case()
            self.finish()

    def open_marks(self, path=None):
        """--load, from the window: continue from a marks file saved earlier."""
        path = path or choose_file(self, "open marks", str(Path(self.out).parent), "Marks (*_marks.json *.json);;All files (*)")
        if not path or not self.settle_unsaved():
            return
        try:
            d = json.loads(Path(path).read_text())
            other = MarkSet(self.ms.tag, self.ms.video, self.ms.fps).load(path)
            if not isinstance(d.get("classes"), dict):
                raise ValueError("it has no 'classes' part")
        except (OSError, ValueError, TypeError, AttributeError, KeyError, IndexError) as ex:
            complain(self, f"{Path(path).name} is not a marks file: {ex}")
            return
        theirs = Path(str(d.get("video") or "")).name
        if theirs and theirs != Path(self.ms.video).name and not confirm(
                self, f"These marks were made on {theirs}, but this video is {Path(self.ms.video).name}. "
                      "A mark is a place on the frames of one video. Do you still want to open them on this one?"):
            return
        self.ms.marks, self.ms.how = other.marks, other.how
        self._undo.clear()
        self._undo.resetClean()                       # they are not what this case directory holds: closing asks
        outside = sum(1 for c in other.marks.values() for n in c if not self.clip.n0 <= n <= self.clip.n1)
        self.marks_changed()
        self.note.setText(f"Opened {other.count()} marks from {Path(path).name}." +
                          (f" {outside} of them are on frames outside {self.clip.n0}–{self.clip.n1}, the part that is open. They are kept."
                           if outside else ""))

    def open_clip(self, video=None):
        """Another clip, in a window of its own that takes this one's place."""
        video = video or choose_video(self)
        if not video or not self.settle_unsaved():
            return
        new = open_session(video, cases=self.cases, workdir=self.workdir, parent=self)
        if new is not None:
            new.show()
            new.view.setFocus()
            self._closing = True                      # the marks were settled above; do not ask twice
            self.close()

    def open_by_id(self):
        key = ask_catalog_id(self)
        if key:
            self.open_clip(key)

    def add_to_desktop(self):
        from . import gui
        try:
            where = gui.desktop_entry()
        except (OSError, RuntimeError) as ex:
            complain(self, str(ex))
            return
        self.note.setText(f"mcdonald is now in the applications menu ({where})")

    # -- finding the object ------------------------------------------------------------------
    def find_object(self):
        """Track -> Find the object: what moves against the background, to say yes or no to (find_qt)."""
        from . import find_qt
        if self.find_panel is None:
            self.find_panel = find_qt.FindPanel(self)
        self.find_panel.refresh()
        self.find_panel.show()
        self.find_panel.raise_()
        if not self.find_panel.running() and not self.find_panel.proposals:
            self.find_panel.start()

    def show_proposal(self, p):
        """Draw a proposal's path and go to where it starts -- or, with None, take the path away."""
        if self._proposal_path is not None:
            self.view.scene().removeItem(self._proposal_path)
            self._proposal_path = None
        if p is None:
            return
        ns = p.frames
        path = QtGui.QPainterPath(QtCore.QPointF(*p.track[ns[0]]))
        for n in ns[1:]:
            path.lineTo(*p.track[n])
        pen = QtGui.QPen(QtGui.QColor("#35e0c8"), 0, Qt.PenStyle.DashLine)
        self._proposal_path = self.view.scene().addPath(path, pen)
        self._proposal_path.setZValue(3)
        self.goto(ns[0])
        self.note.setText(f"The dashed line is one thing the computer found: {p.describe()}. Step through its frames to check it. "
                          "It is not a mark until you choose it.")

    def take_proposal(self, p, how):
        """The person said yes to a proposal: marks of the object along it, as one step to undo,
        each saying that it was proposed; then the link, as after clicks."""
        self.show_proposal(None)
        self.set_class(0)
        self._undo.beginMacro("take a proposal")
        for n, (x, y) in sorted(p.seeds().items()):
            self._undo.push(_Put(self, CLASSES[0], n, (x, y), how=how))
        self._undo.endMacro()
        self.goto(min(p.seeds()))
        self.note.setText(f"{len(p.seeds())} marks were put along its path and saved as proposed. Linking has started from them. "
                          "When it ends, look at the strip, and click the object on any frame where the track is wrong.")
        if not self._link_busy:
            self.do("link")

    # -- the measurements ------------------------------------------------------------------
    def measure(self):
        """Measure -> Measure this clip: the panel that makes a case of it (measure_qt)."""
        from . import measure_qt
        if self.measure_panel is None:
            self.measure_panel = measure_qt.MeasurePanel(self)
        self.measure_panel.refresh()
        self.measure_panel.show()
        self.measure_panel.raise_()
        self.measure_panel.activateWindow()

    def show_report(self):
        from . import measure_qt
        path = Path(f"{self.out}_case.md")
        if not path.exists():
            self.note.setText(f"There is no report for this video yet. Measure → Measure this video makes one ({path.name}).")
            return None
        self.report_page = measure_qt.show_report(self, str(path))
        return self.report_page

    def open_folder(self):
        folder = Path(self.out).parent
        folder.mkdir(parents=True, exist_ok=True)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(folder.resolve())))

    def show_first_run(self):
        """Help -> Getting started: the job in the order it is done, its keys taken from the table."""
        if getattr(self, "first_run_page", None) is not None:
            self.first_run_page.close()
        d = self.first_run_page = beside(self)
        d.setWindowTitle("getting started")
        page = QtWidgets.QTextBrowser()
        bold = lambda text: escape(text).replace("\x02", "<b>").replace("\x03", "</b>")     # escape first: a key may be '<'
        page.setHtml("".join(f"<h3>{i}. {escape(head)}</h3><p>{bold(text)}</p>" for i, (head, text) in
                             enumerate(actions.first_run(lambda k: f"\x02{native_keys(k)}\x03"), 1))
                     + "<p>Every key is in the menus, and under Help → Keys and mouse.</p>")
        lay = QtWidgets.QVBoxLayout(d)
        lay.addWidget(page)
        d.page = page
        d.resize(720, 820)
        d.show()

    def show_keys(self):
        """Help -> Keys: the table, with the mouse, for someone who has only this window."""
        if getattr(self, "keys_page", None) is not None:
            self.keys_page.close()
        d = self.keys_page = beside(self)
        d.setWindowTitle("keys and mouse")
        rows = "".join(f"<tr><td style='padding: 3px 18px 3px 0; white-space: pre;'><b>{escape(native_keys(k))}</b></td>"
                       f"<td style='padding: 3px 0;'>{escape(text)}</td></tr>" for k, text, _ in actions.listing("qt"))
        page = QtWidgets.QTextBrowser()
        page.setHtml(f"<p>Everything here is also in the menus, which show the same keys.</p><table>{rows}</table>")
        lay = QtWidgets.QVBoxLayout(d)
        lay.addWidget(page)
        d.resize(760, 720)
        d.show()

    def _frame_typed(self, n):
        self.goto(n)
        self.view.setFocus()

    # -- saving ----------------------------------------------------------------------------
    def finish(self, show_strip=True):
        try:
            Path(self.out).parent.mkdir(parents=True, exist_ok=True)
            said = save_all(self.clip, self.ms, self.out)
        except OSError as ex:
            complain(self, f"Nothing was saved: {ex}\n\nUse File → Save to a different folder to choose another place.")
            return
        for ci, link in sorted(self.links.items()):
            if link.track:
                how = {n: self.ms.how_of(CLASSES[ci], n) for n in link.marks}
                auto, strip = autolink.save_track(self.clip, link, self.out, CLASSES[ci], how, video=self.ms.video)
                said.append(f"wrote {auto} and {strip}  -- the automatic track of the {CLASSES[ci]}: {link.say}")
        print("\n".join(said))
        self._undo.setClean()
        self.note.setText(said[0])
        strip = f"{self.out}_marks.png"
        if show_strip and os.path.exists(strip) and self.ms.count():
            self._show_strip(strip)

    def _show_strip(self, path):
        """The contact strip, put in front of the person who placed the marks. It is
        the check that a coordinate is where they meant it, so it is not left on disk."""
        if self.saved_strip is not None:
            self.saved_strip.close()
        d = self.saved_strip = beside(self)
        d.setWindowTitle("saved — now look at it")
        lay = QtWidgets.QVBoxLayout(d)
        pic = QtWidgets.QLabel()
        pic.setPixmap(QtGui.QPixmap(path))
        area = QtWidgets.QScrollArea()
        area.setWidget(pic)
        lay.addWidget(area)
        lay.addWidget(QtWidgets.QLabel("Until you have seen a mark drawn on the picture, you are trusting a number. "
                                       "You have not checked it.\n" + path))
        d.resize(min(pic.pixmap().width() + 40, 1400), min(pic.pixmap().height() + 90, 800))
        d.show()

    def unsaved_answer(self):
        """Ask what to do with unsaved marks: 'save', 'discard' or 'cancel'."""
        B = QtWidgets.QMessageBox.StandardButton
        b = QtWidgets.QMessageBox.question(self, "unsaved marks", "Save the marks before closing?",
                                           B.Save | B.Discard | B.Cancel, B.Save)
        return {B.Save: "save", B.Discard: "discard"}.get(b, "cancel")

    def settle_unsaved(self):
        """Before the marks go, by closing or by opening something else: False if the
        person would rather stay."""
        if self._undo.isClean():
            return True
        answer = self.unsaved_answer()
        if answer == "save":
            self.finish(show_strip=False)
        return answer != "cancel"

    def closeEvent(self, e):
        if not (self._closing or self.settle_unsaved()):
            e.ignore()
            return
        self._timer.stop()
        self._link_stop.set()
        if self.measure_panel is not None:           # a sheet waiting for an answer gets "no", and the step under way
            self.measure_panel.close()               # ends and the report of what ran is written before the program does
            if self.measure_panel.running():
                self.note.setText("Stopping the measuring: the step under way ends, and the report of the steps that ran is "
                                  "written, before this window closes…")
                self.measure_panel.wait_for_the_step()
        if self.find_panel is not None:
            self.find_panel.close()
        self.store.close()
        self._tmp.cleanup()
        e.accept()

    def run(self):
        self.show()
        self.view.setFocus()
        self.app.exec()


def extract_with_progress(clip, parent=None, watch=None):
    """Extract the clip's frames behind a progress bar with a Cancel on it. True when
    the frames are there, False if the person thought better of it. `watch` is called
    with the dialog each time it is updated."""
    app = application()
    if clip.extracted():
        return True
    total = clip.n1 - clip.n0 + 1
    box = QtWidgets.QProgressDialog(f"Saving {total} frames of {clip.video.name} as pictures, with nothing lost. "
                                    f"This is done once.\nThey are kept in {clip.dir}", "Cancel", 0, total, parent)
    box.setWindowTitle("mcdonald")
    box.setWindowModality(Qt.WindowModality.ApplicationModal)
    box.setMinimumDuration(0)
    box.setAutoClose(False)
    box.setAutoReset(False)
    box.show()
    stop, result = threading.Event(), {}

    def job():
        try:
            result["ok"] = clip.extract(stop=stop.is_set)
        except Exception as ex:
            result["error"] = ex
    worker = threading.Thread(target=job, daemon=True, name="mcdonald-extract")
    worker.start()
    while worker.is_alive():
        box.setValue(min(clip.n_extracted(), total))
        if watch:
            watch(box)
        app.processEvents()
        if box.wasCanceled():
            stop.set()
        QtCore.QThread.msleep(40)
    box.close()
    if "error" in result:
        raise result["error"]
    return bool(result.get("ok"))


# ---- getting in, and being told, with no terminal ----------------------------------------------
_windows = []                                         # a window that replaced another has nobody else to hold it


def complain(parent, text):
    """What the command line would have printed before stopping, in front of someone who
    has no command line. It is printed as well: a terminal that is there should not be
    left knowing less than the dialog."""
    print(f"mcdonald: {text}", file=sys.stderr)
    application()
    QtWidgets.QMessageBox.critical(parent, "mcdonald", text)


def confirm(parent, text):
    B = QtWidgets.QMessageBox.StandardButton
    return QtWidgets.QMessageBox.question(parent, "mcdonald", text, B.Yes | B.No, B.No) == B.Yes


def settings():
    """What is worth remembering between one start from the desktop and the next: which
    catalog, and where the last clip was. An environment variable always wins over it."""
    return QtCore.QSettings("mcdonald", "mcdonald")


def cases_folder():
    """Where case directories go when nobody said. From a terminal that is the working
    directory; someone who started from the desktop has none they chose, so it is the
    folder they last saved a video's files in (File -> Save to a different folder), and
    before they have, Documents/mcdonald; the window shows where that is."""
    docs = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.DocumentsLocation)
    return (os.environ.get("MCDONALD_CASES", "").strip() or settings().value("cases") or
            str(Path(docs or Path.home()) / "mcdonald"))


def choose_file(parent, title, where, what):
    path, _ = QtWidgets.QFileDialog.getOpenFileName(parent, f"mcdonald — {title}", where, what)
    return path or None


def choose_folder(parent, title, where):
    return QtWidgets.QFileDialog.getExistingDirectory(parent, f"mcdonald — {title}", where) or None


def choose_video(parent=None):
    """A file dialog, for `mcdonald mark` with no clip named, and for File -> Open."""
    application()
    path = choose_file(parent, "choose a video", settings().value("clips") or "",
                       "Video (*.mp4 *.mov *.mkv *.avi *.m4v *.ts *.mpg *.wmv);;All files (*)")
    if path:
        settings().setValue("clips", str(Path(path).parent))
    return path


def use_remembered_catalog():
    """MCDONALD_CATALOG is how a catalog is named, and a person at a window cannot set
    it. Theirs is remembered from the time they chose it."""
    if not os.environ.get("MCDONALD_CATALOG", "").strip():
        path = settings().value("catalog")
        if path and Path(path).exists():
            catalog.use(catalog.PursueCatalog(path))


def ask_catalog_id(parent=None):
    """A record id to open, or None. With no catalog, first the chance to choose one."""
    application()
    if isinstance(catalog.active(), catalog.NullCatalog):
        if not confirm(parent, "No catalog has been chosen yet, so a name such as PR144 cannot be looked up.\n\n"
                               "A catalog is a file called records.csv. It lists videos, and says which video file "
                               "each short name stands for. Do you want to choose one now?"):
            return None
        path = choose_file(parent, "choose the catalog file (records.csv)", "", "Catalog (*.csv);;All files (*)")
        if not path:
            return None
        cat = catalog.PursueCatalog(path)
        if not cat.videos():
            complain(parent, f"{Path(path).name} does not list any videos that mcdonald can read. It needs these "
                             "columns: type, title, release, redacted, blurb, out_path.")
            return None
        catalog.use(cat)
        settings().setValue("catalog", path)
    text, ok = QtWidgets.QInputDialog.getText(parent, "mcdonald — open by catalog name",
                                              f"Name of the video in the {catalog.active().name} catalog (such as PR144, or 06:PR001):")
    return text.strip() or None if ok else None


def choose_start(parent=None):
    """The first thing someone with no terminal sees: what this is, and the two ways to
    name a clip. A clip or a record id to open, or None to leave."""
    application()
    while True:
        d = QtWidgets.QDialog(parent)
        d.setWindowTitle("mcDonald UAP Toolkit")
        lay = QtWidgets.QVBoxLayout(d)
        about = QtWidgets.QLabel("<b>mcdonald</b> measures the kinematics of an unknown object in a single-camera video<br><br>"
                                 "Start by opening a video by filename or by catalog name. (Current catalog includes all "
                                 "PURSUE cases.)")
        about.setWordWrap(True)
        about.setMinimumWidth(460)
        lay.addWidget(about)
        for text, code in (("Open a video…", 2), ("Open by catalog name…", 3), ("Quit", 0)):
            b = QtWidgets.QPushButton(text)
            b.clicked.connect(lambda _=False, code=code: d.done(code))
            lay.addWidget(b)
        code = d.exec()
        if code == 0:
            return None
        got = choose_video(parent) if code == 2 else ask_catalog_id(parent)
        if got:
            return got


def clock(seconds):
    return f"{int(seconds // 60)}:{seconds % 60:05.2f}"


class Screen(QtWidgets.QWidget):
    """A frame of the reel, as large as there is room for and never stretched."""

    def __init__(self, w, h):
        super().__init__()
        self._pix, self._smooth, self._hint = None, True, QtCore.QSize(w, h)
        self.setMinimumSize(480, max(90, int(480 * h / w)))
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def sizeHint(self):
        return self._hint

    def pixmap(self):
        return self._pix

    def show_frame(self, pix, smooth=True):
        self._pix, self._smooth = pix, smooth
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.fillRect(self.rect(), QtGui.QColor("#0c0c0d"))
        if self._pix is not None:
            size = self._pix.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
            p.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, self._smooth)
            p.drawPixmap(QtCore.QRect(QtCore.QPoint((self.width() - size.width()) // 2, (self.height() - size.height()) // 2),
                                      size), self._pix)


class RangeChooser(QtWidgets.QDialog):
    """Which part of the clip to open, found by watching it, and what that part will cost.

    --n0 and --n1 were flags only, and without them the whole clip was extracted: PR148 is
    1793 frames and 1.3 GB, into a temporary directory that on Fedora is memory. Someone
    who has not seen the clip cannot name frame numbers, so this is a player: play it
    forward or backward at the clip's true speed or slower, step a frame or ten, drag the
    bar, and say "the part starts here" and "ends here" at the frame on the screen. Nothing
    is extracted to do it: the frames come from an ffmpeg pipe (`reel.Reel`), with the
    package's frame numbers. The keys for moving about are the main window's, from the
    same rows of `actions.ACTIONS`; there is no menu here, so each button's tip names its
    key and a line under them names the main ones."""
    frame_arrived = QtCore.Signal(int)
    OWN = {"back": ("Shift+Space",), "start": ("[",), "end": ("]",), "part": ("P",)}

    def __init__(self, clip, parent=None, width=960):
        super().__init__(parent)
        self.clip, self.fps = clip, clip.info["fps"]
        self.reel = Reel(clip.video, clip.info, width=width, on_frame=self._tell)
        self.total = total = self.reel.total
        self.n, self.shown = clip.n0, None            # the frame wanted, and the one on the screen
        self._playing, self._speed, self._stop_at = 0, SPEEDS.index(Fraction(1)), None
        self._clock, self._play_from = QtCore.QElapsedTimer(), self.n
        self._timer = QtCore.QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(4)
        self._timer.timeout.connect(self._tick)
        name, fps = clip.video.name, float(self.fps)
        self.setWindowTitle(f"mcdonald — choose the part of {name} to open")
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel(f"{name}: {total} frames, {clock(total / fps)} long, {fps:.4g} frames a second, "
                                       f"{clip.W}×{clip.H}"))
        guide = QtWidgets.QLabel("Play the video and find the part that has the object in it. Set where that part starts "
                                 "and where it ends, then press Open. Only that part is opened, so a short part opens "
                                 "fast and takes little room. But leave a second or two before the object comes and "
                                 "after it goes: the computer needs to see the background without it.")
        guide.setWordWrap(True)
        lay.addWidget(guide)
        self.preview = Screen(self.reel.w, self.reel.h)
        lay.addWidget(self.preview, 1)
        self.bar = Timeline(1, total, fps)
        self.bar.scrubbed.connect(self.goto)
        lay.addWidget(self.bar)

        rows, self.buttons_by_id = {a.id: a for a in actions.ACTIONS}, {}
        moves = {"first": lambda: self.goto(1), "back10": lambda: self.step(-10), "prev": lambda: self.step(-1),
                 "play": lambda: self.toggle_play(+1), "next": lambda: self.step(+1), "on10": lambda: self.step(+10),
                 "last": lambda: self.goto(self.reel.last), "slower": lambda: self.change_speed(-1),
                 "faster": lambda: self.change_speed(+1)}
        own = {"back": (lambda: self.toggle_play(-1), "play backward"),
               "start": (lambda: self.first.setValue(self.on_screen()), "the part starts at the frame on the screen"),
               "end": (lambda: self.last.setValue(self.on_screen()), "the part ends at the frame on the screen"),
               "part": (self.play_part, "play the part you chose, from its start to its end")}

        def button(text, act, kind=QtWidgets.QToolButton):
            """A button and its keys. The tip is the row's help and its first key."""
            do, tip = (moves[act], rows[act].help) if act in moves else own[act]
            keys = rows[act].keys if act in moves else self.OWN[act]
            b = self.buttons_by_id[act] = kind()
            b.setText(text)
            b.setToolTip(f"{tip} ({native_keys(actions.spoken(keys[0]))})")
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            if isinstance(b, QtWidgets.QPushButton):
                b.setAutoDefault(False)
            b.clicked.connect(lambda _=False: do())
            for k in keys:
                QtGui.QShortcut(QtGui.QKeySequence(k), self, activated=do)
            return b

        ctl = QtWidgets.QHBoxLayout()
        for text, act in (("⏮", "first"), ("−10", "back10"), ("−1", "prev"), ("◀", "back"), ("▶", "play"), ("+1", "next"),
                          ("+10", "on10"), ("⏭", "last")):
            ctl.addWidget(button(text, act))
        ctl.addSpacing(16)
        ctl.addWidget(button("slower", "slower"))
        self.speed_label = QtWidgets.QLabel()
        ctl.addWidget(self.speed_label)
        ctl.addWidget(button("faster", "faster"))
        ctl.addSpacing(16)
        self.where = QtWidgets.QLabel()
        ctl.addWidget(self.where, 1)
        lay.addLayout(ctl)
        hint = QtWidgets.QLabel("Keys: space plays and stops · the left and right arrows go one frame · with shift, ten "
                                "frames · [ and ] set the start and the end")
        hint.setStyleSheet("color: #898781;")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        row = QtWidgets.QHBoxLayout()
        self.first, self.last = QtWidgets.QSpinBox(), QtWidgets.QSpinBox()
        for box, n, text, act, tip in ((self.first, clip.n0, "Start here", "start", "the first frame of the part"),
                                       (self.last, clip.n1, "End here", "end", "the last frame of the part")):
            box.setRange(1, total)
            box.setValue(n)
            box.setKeyboardTracking(False)
            box.setToolTip(tip)
            box.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            b = button(text, act, QtWidgets.QPushButton)
            row.addWidget(b)
            row.addWidget(box)
            row.addSpacing(12)
            box.valueChanged.connect(self._changed)
            box.editingFinished.connect(self.preview.setFocus)
        row.addStretch(1)
        row.addWidget(button("Play this part", "part", QtWidgets.QPushButton))
        whole = QtWidgets.QPushButton("The whole video")
        whole.setToolTip("choose all of the video, from its first frame to its last")
        whole.setAutoDefault(False)
        whole.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        whole.clicked.connect(lambda: (self.first.setValue(1), self.last.setValue(total)))
        row.addWidget(whole)
        lay.addLayout(row)
        self.span = QtWidgets.QLabel()
        lay.addWidget(self.span)
        self.cost = QtWidgets.QLabel()
        self.cost.setWordWrap(True)
        lay.addWidget(self.cost)
        B = QtWidgets.QDialogButtonBox.StandardButton
        self.buttons = QtWidgets.QDialogButtonBox(B.Open | B.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        for b in self.buttons.buttons():              # space plays; it must not press whichever of these has the focus
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        lay.addWidget(self.buttons)

        self.frame_arrived.connect(self._arrived)
        room = (parent.screen() if parent is not None else QtGui.QGuiApplication.primaryScreen()).availableGeometry()
        self.resize(self.sizeHint().boundedTo(QtCore.QSize(int(room.width() * 0.92), int(room.height() * 0.92))))
        self.preview.setFocus()
        self._changed()
        self._say_speed()
        self.goto(self.n)

    # -- the part ----------------------------------------------------------------------------
    def chosen(self):
        return self.first.value(), self.last.value()

    def on_screen(self):
        """The frame a person means by "here": the one they can see."""
        return self.shown if self.shown is not None else self.n

    def _changed(self, *_):
        a, b = self.chosen()
        if b < a:                                     # whichever was just moved wins; the other follows it
            (self.last if self.sender() is self.first else self.first).setValue(a if self.sender() is self.first else b)
            return
        fps = self.clip.fps
        self.span.setText(f"Frames {a} to {b}: {b - a + 1} frames, from {clock((a - 1) / fps)} to {clock((b - 1) / fps)}")
        c = self.clip.cost(a, b)
        self.cost.setText(vf.cost_text(c))
        self.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Open).setEnabled(c["bytes"] <= 0.8 * c["free"])
        self.bar.part = (a, b)
        self.bar.update()

    # -- moving about --------------------------------------------------------------------------
    def goto(self, n, direction=+1):
        """Show frame n. A place on the bar is come to from the front, which is quickest; a
        step back says so, and then what is behind it is fetched as well."""
        self.n = int(np.clip(n, 1, self.reel.last))
        self.reel.want(self.n, direction, around=not self._playing)
        if not self._display(self.n):
            self._say_where()

    def step(self, k):
        if self._playing:
            self.pause()
        self.goto(self.on_screen() + k, +1 if k > 0 else -1)

    def _tell(self, n):                               # on the reel's thread
        try:
            self.frame_arrived.emit(n)
        except RuntimeError:                          # the dialog closed while ffmpeg was reading
            pass

    @QtCore.Slot(int)
    def _arrived(self, k):
        """Frame k has been read. If it is the one wanted, show it; if the one wanted is still
        on its way and k is nearer to it than what is on the screen, show that meanwhile --
        which is what is seen while the bar is dragged."""
        if self.shown != self.n and not self._playing and (
                k == self.n or self.shown is None or abs(k - self.n) < abs(self.shown - self.n)):
            self._display(k)
        self.bar.show_state(self.on_screen(), {}, self.reel.cached())

    def _display(self, k):
        data = self.reel.get(k)
        if data is None:
            return False
        img = QtGui.QImage(data, self.reel.w, self.reel.h, 3 * self.reel.w, QtGui.QImage.Format.Format_RGB888)
        self.preview.show_frame(QtGui.QPixmap.fromImage(img), smooth=not self._playing)
        self.shown = k
        self.bar.show_state(k, {}, self.reel.cached())
        self._say_where()
        return True

    def _say_where(self):
        if self.reel.error:
            self.where.setText("This video cannot be shown here. You can still type the first and last frame below.")
            return
        k, fps = self.shown, self.clip.fps
        text = "getting the video ready…" if k is None else \
            f"{'frame' if self.reel.exact else 'about frame'} {k} of {self.reel.last}, at {clock((k - 1) / fps)}"
        if k is not None and k != self.n and not self._playing:
            text += f" — finding frame {self.n}…"
        self.where.setText(text)

    # -- playing -------------------------------------------------------------------------------
    def playing(self):
        return self._playing

    def speed(self):
        return SPEEDS[self._speed]

    def toggle_play(self, direction=+1):
        if self._playing:
            self.pause()
        else:
            self.play(direction)

    def play(self, direction=+1, stop_at=None):
        here = self.on_screen()
        if direction > 0 and here >= (stop_at or self.reel.last):
            here = 1                                  # at the end, play starts again from the beginning
        elif direction < 0 and here <= 1:
            here = self.reel.last
        self._playing, self._stop_at = (1 if direction > 0 else -1), stop_at
        self.goto(here, self._playing)
        self._play_from = here
        self._clock.start()
        self._timer.start()
        self._say_play()

    def play_part(self):
        if self._playing:
            self.pause()
        a, b = self.chosen()
        self.shown = None if self.shown != a else a   # "here" is the start of the part, not where the screen was
        self.n = a
        self.play(+1, stop_at=b)

    def pause(self):
        self._playing, self._stop_at = 0, None
        self._timer.stop()
        self.goto(self.on_screen())                   # stopped: ask for what is round this frame, either way
        if self.preview.pixmap() is not None:
            self.preview.show_frame(self.preview.pixmap(), smooth=True)
        self._say_play()

    def change_speed(self, step):
        self._speed = int(np.clip(self._speed + step, 0, len(SPEEDS) - 1))
        if self._playing:                             # start the clock again, or the change would apply to time already played
            self._play_from = self.on_screen()
            self._clock.start()
        self._say_speed()

    def _say_speed(self):
        self.speed_label.setText(f"speed {self.speed()}×")

    def _say_play(self):
        self.buttons_by_id["play"].setText("⏸" if self._playing > 0 else "▶")
        self.buttons_by_id["back"].setText("⏸" if self._playing < 0 else "◀")

    def _tick(self):
        """The clock says which frame is due. If it is not here yet, show the furthest one
        that is and start the clock again from it: here time is stretched, not skipped,
        because a frame skipped is a frame of the clip nobody looked at."""
        d = self._playing
        end = (self._stop_at or self.reel.last) if d > 0 else 1
        gone = int(Fraction(self._clock.nsecsElapsed(), 10 ** 9) * self.fps * self.speed())
        due = self._play_from + d * gone
        due = min(due, end) if d > 0 else max(due, end)
        here = self.on_screen()
        if due == here and self.shown is not None:
            return
        self.n = due
        self.reel.want(due, d)
        if not self._display(due):
            k = self.reel.nearest(due, *((here + 1, due) if d > 0 else (due, here - 1)))
            if k is not None:
                self._display(k)
            self.n = self._play_from = self.on_screen()
            self._clock.start()
        if self.shown == end:
            self.pause()

    def done(self, r):
        self._timer.stop()
        self.reel.close()
        super().done(r)


LONG = 900                  # frames: a clip longer than this is asked about even when it is all on disk (30 s at 30 a second)


def choose_range(clip, parent=None):
    """(n0, n1) from the person, or None if they thought better of opening it. The part chosen
    last time for this video is where the chooser starts, and is remembered for next time."""
    d = RangeChooser(clip, parent)
    key = f"parts/{clip.video.name}"
    last = remembered_part(clip)
    if last:
        d.first.setValue(last[0])
        d.last.setValue(last[1])
        d.goto(last[0])
    if d.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return None
    got = d.chosen()
    settings().setValue(key, f"{got[0]},{got[1]}")
    return got


def remembered_part(clip):
    """(n0, n1) of the part of this video opened last time, if it is still a part of it."""
    try:
        a, b = (int(v) for v in str(settings().value(f"parts/{clip.video.name}") or "").split(","))
    except ValueError:
        return None
    return (a, b) if 1 <= a <= b <= clip.n1 else None


def open_session(video, n0=None, n1=None, out=None, load=None, workdir=None, cases=None, parent=None):
    """From the name of a clip to a window on it, or None. Everything that can go wrong on
    the way is said in a dialog, in the words the command line uses for it.

    With no range given, the person is asked which part, by watching it, and shown what it
    costs -- where there are frames still to extract, and also where there are none but the
    clip is long. A whole clip that happens to be on disk already costs nothing to open
    and a great deal afterwards: PR113 is 5291 frames, and Measure on all of them is hours.
    `out` is this clip's case directory; `cases` is a folder to make one in, for a start from
    the desktop, where there is no working directory anyone chose."""
    application()
    try:
        path, tag, _ = vf.resolve(video)
        clip = vf.Clip(path, workdir, n0, n1, extract=False)
        if n0 is None and n1 is None and (clip.cost()["missing"] or clip.n1 - clip.n0 + 1 > LONG):
            got = choose_range(clip, parent)
            if got is None:
                return None
            clip = vf.Clip(path, workdir, *got, extract=False)
        if not extract_with_progress(clip, parent):
            return None
    except (SystemExit, vf.NotAVideo, vf.MissingTool) as ex:        # resolve() stops a command line with its message
        complain(parent, str(ex))
        return None
    except (OSError, subprocess.CalledProcessError) as ex:
        complain(parent, f"The frames of {Path(str(video)).name} could not be saved as pictures: {ex}")
        return None
    prefix = vf.case_dir(out or (Path(cases) / tag if cases else None), tag, create=False) / tag
    ms = MarkSet(tag, path, clip.fps, load or f"{prefix}_marks.json")
    w = QtMarker(clip, ms, str(prefix), cases=cases, workdir=workdir)
    _windows[:] = [x for x in _windows if x.isVisible()] + [w]
    return w
