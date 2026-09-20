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

Controls
    click           place a mark of the current class
    , .  or arrows  previous / next frame          < >  or shift+arrows   -/+ 10 frames
    space           play / pause                   - =   slower / faster
    home end        first / last frame             [ ]   previous / next marked frame
    1..6            mark class: object, object #2, boresight, north, reference, horizon
    backspace       delete this class's mark on this frame
    ctrl+z          undo                           ctrl+shift+z   redo
    scroll          zoom about the cursor          middle-, right- or ctrl-drag   pan
    r               fit the frame to the window
    c               detector candidates on this frame (slow the first time: it builds the static masks)
    l               link: an automatic track forward from this class's first mark, drawn as it
                    grows; l again stops it. The detector's scale is chosen from the marks
    t               show / hide the marks of this class on the other frames
    o               overview of the whole clip; click a tile to go there
    s               save                           q   save and quit
"""
import os
import sys
import tempfile
import threading
from collections import OrderedDict
from concurrent.futures import CancelledError, ThreadPoolExecutor
from fractions import Fraction

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from . import autolink
from . import forensics as vf
from .mark import CLASSES, COLOURS, save_all, seed_text, status_line

AUTO = "#f2f0e9"                                  # the automatic track: never a class colour, those are hand marks

SPEEDS = [Fraction(1, 8), Fraction(1, 4), Fraction(1, 2), Fraction(1), Fraction(2), Fraction(4)]
RGB32 = QtGui.QImage.Format.Format_RGB32


def application():
    """The QApplication, made on first use. Dark, so that the frame is the
    brightest thing on the screen: a white surround costs contrast on exactly
    the frames that matter, a faint object on a night sky."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv[:1])
        app.setApplicationName("mcdonald mark")
        app.setStyle("Fusion")
        pal, c = QtGui.QPalette(), QtGui.QColor
        for role, col in (("Window", "#1d1d1f"), ("WindowText", "#dddddd"), ("Base", "#141415"),
                          ("AlternateBase", "#1d1d1f"), ("Text", "#dddddd"), ("Button", "#2a2a2d"),
                          ("ButtonText", "#dddddd"), ("ToolTipBase", "#2a2a2d"), ("ToolTipText", "#dddddd"),
                          ("Highlight", "#2a78d6"), ("HighlightedText", "#ffffff"), ("PlaceholderText", "#898781")):
            pal.setColor(getattr(QtGui.QPalette.ColorRole, role), c(col))
        app.setPalette(pal)
    return app


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

    def __init__(self, x, y):
        super().__init__()
        self.xy = (x, y)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setPos(x, y)
        self.setZValue(8)

    def boundingRect(self):
        h = self.HALF + 3
        return QtCore.QRectF(-h, -h, 2 * h, 2 * h)

    def paint(self, p, option, widget=None):
        h = self.HALF
        for pen in (QtGui.QPen(QtGui.QColor(0, 0, 0, 190), 3.5), QtGui.QPen(QtGui.QColor(AUTO), 1.4)):
            p.setPen(pen)
            p.drawRect(QtCore.QRectF(-h, -h, 2 * h, 2 * h))


class FrameView(QtWidgets.QGraphicsView):
    """The frame, with zoom about the cursor and pan. Reports presses in image coordinates."""
    pressed = QtCore.Signal(QtCore.QPointF)
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
                self.pressed.emit(p)
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
        self.n, self.marks, self.cached, self.linked = n0, {}, [], []
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

    def show_state(self, n, marks, cached, linked=()):
        self.n, self.marks, self.cached, self.linked = n, marks, cached, linked
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QtGui.QColor("#141415"))
        p.fillRect(QtCore.QRectF(self.PAD, 4, w - 2 * self.PAD, h - 8), QtGui.QColor("#232326"))
        px = max((w - 2 * self.PAD) / max(self.n1 - self.n0, 1), 1.0)
        for n in self.cached:                        # decoded and ready: what playback can show without waiting
            p.fillRect(QtCore.QRectF(self.x_of(n) - px / 2, h - 7, px, 3), QtGui.QColor("#4a4944"))
        for n in self.linked:                        # where the automatic track has the object: gaps show as gaps
            p.fillRect(QtCore.QRectF(self.x_of(n) - px / 2, 5, px, 4), QtGui.QColor(AUTO))
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
        QtWidgets.QToolTip.showText(e.globalPosition().toPoint(), f"frame {n}   t = {(n - 1) / self.fps:.3f} s", self)


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
        self.setWindowTitle("overview — click a frame to go there")
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

    def __init__(self, window, cls, n, xy):
        was = window.ms.marks.get(cls, {}).get(n)
        super().__init__(f"{'delete' if xy is None else 'move' if was else 'place'} {cls} on frame {n}")
        self.w, self.cls, self.n, self.xy, self.was = window, cls, n, xy, was

    def _set(self, xy):
        if xy is None:
            self.w.ms.remove_last(self.cls, self.n)
        else:
            self.w.ms.add(self.cls, self.n, *xy)
        self.w.marks_changed()

    def redo(self):
        self._set(self.xy)

    def undo(self):
        self._set(self.was)


# ---- the window -------------------------------------------------------------------------
class QtMarker(QtWidgets.QMainWindow):
    """The Qt front end. Marker-shaped: same constructor, same `n`, `cls`, `ms`,
    `goto`, `finish`, `run`, so `mark.main` and the tests can treat the two alike."""
    candidates_ready = QtCore.Signal(object, object)          # the request key, and the candidates or an Exception
    link_progress = QtCore.Signal(object)                     # an autolink.Link, from the linking thread
    strip_ready = QtCore.Signal(str, object)                  # the track strip's path and its frames

    def __init__(self, clip, ms, out_prefix):
        app = application()                           # before any widget, this one included
        super().__init__()
        self.app = app
        self.clip, self.ms, self.out = clip, ms, out_prefix
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
        self.timeline.scrubbed.connect(self.goto)

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

        # the link: autolink on its own thread (and its own processes), reporting frame by frame
        self.link, self._link_marks, self._link_cls = None, None, 0
        self._link_thread, self._link_stop = None, threading.Event()
        self._link_path, self.track_strip, self._link_said = None, None, ""
        self.link_progress.connect(self._on_link)
        self.strip_ready.connect(self._show_track_strip)

        self._build()
        self.resize(1500, 920)
        self.goto(self.n)
        self.marks_changed()
        self._undo.setClean()

    # -- layout --------------------------------------------------------------------------
    def _build(self):
        def button(text, tip, fn, checkable=False):
            b = QtWidgets.QToolButton()
            b.setText(text)
            b.setToolTip(tip)
            b.setCheckable(checkable)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(fn)
            return b

        bar = QtWidgets.QHBoxLayout()
        bar.setContentsMargins(8, 4, 8, 0)
        for text, tip, fn in (("⏮", "first frame (home)", lambda: self.goto(self.clip.n0)),
                              ("−10", "back ten (<)", lambda: self.goto(self.n - 10)),
                              ("−1", "back one (,)", lambda: self.goto(self.n - 1))):
            bar.addWidget(button(text, tip, fn))
        self.play_button = button("▶", "play / pause (space)", self.toggle_play)
        bar.addWidget(self.play_button)
        for text, tip, fn in (("+1", "on one (.)", lambda: self.goto(self.n + 1)),
                              ("+10", "on ten (>)", lambda: self.goto(self.n + 10)),
                              ("⏭", "last frame (end)", lambda: self.goto(self.clip.n1))):
            bar.addWidget(button(text, tip, fn))
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
            b = button(f"{i + 1} {c}", f"mark the {c} ({i + 1})", lambda _=False, i=i: self.set_class(i), checkable=True)
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
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["class", "frame", "x", "y"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.cellClicked.connect(self._row_clicked)
        col.addWidget(self.table, 1)
        det = QtWidgets.QHBoxLayout()
        self.cand_box = QtWidgets.QCheckBox("candidates (c)")
        self.cand_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cand_box.toggled.connect(self.set_candidates)
        self.size_box = QtWidgets.QSpinBox()
        self.size_box.setRange(3, 60)
        self.size_box.setValue(9)
        self.size_box.setSuffix(" px")
        self.size_box.setToolTip("the size of source to look for")
        self.size_box.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.size_box.valueChanged.connect(lambda _: self._candidates_stale())
        self.dark_box = QtWidgets.QCheckBox("dark")
        self.dark_box.setToolTip("look for an object darker than its surroundings")
        self.dark_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.dark_box.toggled.connect(lambda _: self._candidates_stale())
        self.auto_box = QtWidgets.QCheckBox("auto")
        self.auto_box.setChecked(True)
        self.auto_box.setToolTip("when linking, choose the detector's scale and polarity from the marks: "
                                 "the smallest scale that puts a candidate on them")
        self.auto_box.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for w in (self.cand_box, self.size_box, self.dark_box, self.auto_box):
            det.addWidget(w)
        col.addLayout(det)
        self.link_button = QtWidgets.QPushButton("link from the marks (l)")
        self.link_button.setToolTip("an automatic track forward from this class's first mark, drawn as it grows")
        self.link_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.link_button.clicked.connect(self.toggle_link)
        col.addWidget(self.link_button)
        self.link_label = QtWidgets.QLabel("")
        self.link_label.setWordWrap(True)
        self.link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        col.addWidget(self.link_label)
        dock = QtWidgets.QDockWidget("marks")
        dock.setWidget(side)
        dock.setFeatures(QtWidgets.QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

        self.status = QtWidgets.QLabel()
        self.note = QtWidgets.QLabel()
        self.statusBar().addWidget(self.status, 1)
        self.statusBar().addPermanentWidget(self.note)
        self.statusBar().setSizeGripEnabled(False)

    @QtCore.Slot()
    def _retitle(self, *_):
        self.setWindowTitle(f"mcdonald mark — {self.ms.tag}{'' if self._undo.isClean() else ' *'}")

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
        self.box = None
        if self.link is not None and self.n in self.link.track:
            self.box = Box(*self.link.track[self.n])
            sc.addItem(self.box)
            self._overlay.append(self.box)
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
        self._timeline_state()
        self._look()

    @QtCore.Slot(int)
    def _frame_arrived(self, n):                     # from a decoding thread, queued onto this one
        self._timeline_state()

    def _timeline_state(self):
        self.timeline.show_state(self.n, self.ms.marks, self.store.cached(),
                                 sorted(self.link.track) if self.link is not None else ())

    def marks_changed(self):
        """The table and the velocity, which change with the marks and not with the frame."""
        rows = [(c, n, xy) for c in CLASSES for n, xy in sorted(self.ms.marks.get(c, {}).items())]
        self.table.setRowCount(len(rows))
        for r, (c, n, (x, y)) in enumerate(rows):
            for k, text in enumerate((c, str(n), f"{x:.2f}", f"{y:.2f}")):
                it = QtWidgets.QTableWidgetItem(text)
                it.setForeground(QtGui.QColor(COLOURS[CLASSES.index(c)]))
                self.table.setItem(r, k, it)
        self._rows = rows
        self._say_link()
        v = self.ms.velocity()
        self.velocity_label.setText(
            "two marks on the object give its velocity" if v is None else
            f"v = ({v[0]:+.2f}, {v[1]:+.2f}) px/frame\n"
            f"  = {np.hypot(*v) * float(self.fps):.0f} px/s at {self.fps} fps\nseed = {seed_text(self.ms.seed())}")
        self._retitle()
        self.draw()

    def set_class(self, i):
        self.cls = i
        self.draw()

    # -- marks -----------------------------------------------------------------------------
    def _place(self, p):
        self._undo.push(_Put(self, CLASSES[self.cls], self.n, (p.x(), p.y())))

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
            self.cursor_label.setText(f"x {x:.1f}   y {y:.1f}     DN {(c.red() + c.green() + c.blue()) / 3:.0f}"
                                      f"     ×{self.view.magnification():.2g}")

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

    def _ask_detector(self):
        key = self._cand_key()
        if not self._cand_on or self._playing or key in self._cand_cache or self._cand_busy is not None:
            return
        self._cand_busy = key
        self.note.setText("detector: building the static masks, once per clip…" if self._masks is None
                          else f"detector: frame {key[0]}…")

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
            self.note.setText(f"detector failed: {out}")
            return
        self._cand_cache[key] = out
        self.note.setText(f"detector: {len(out)} candidate{'' if len(out) == 1 else 's'} on frame {key[0]}, strongest first. "
                          "It finds compact sources; which one is the object is yours to say.")
        self.draw()

    # -- the link --------------------------------------------------------------------------
    def linking(self):
        """True until the link has said it is done. (Its thread lives a moment longer,
        making the strip; 'l' in that moment starts a new link rather than being lost.)"""
        return self._link_thread is not None and self._link_thread.is_alive() and not (self.link and self.link.done)

    def toggle_link(self):
        if self.linking():
            self._link_stop.set()
            return
        marks = dict(self.ms.marks.get(CLASSES[self.cls], {}))
        if not marks:
            self.link_label.setText(f"Mark the {CLASSES[self.cls]} first: the first mark is where the link starts, "
                                    "and a second gives it the velocity a fast object needs.")
            return
        self._link_stop = threading.Event()          # a new one: the last link's thread may still hold the old
        self._link_marks, self._link_cls, self.link = marks, self.cls, None
        if self._link_path is not None:
            self.view.scene().removeItem(self._link_path)
            self._link_path = None
        size, dark = (None, None) if self.auto_box.isChecked() else (float(self.size_box.value()), self.dark_box.isChecked())
        building, stop = self._masks is None, self._link_stop

        def job():
            try:
                if building:
                    self.link_progress.emit(autolink.Link("masks", "building the static masks, once per clip…"))
                last = None
                for last in autolink.link_from_marks(self.clip, marks, masks=self._static_masks(), size=size, dark=dark,
                                                     stop=stop.is_set):
                    self.link_progress.emit(last)
                if last is not None and last.track:
                    path = os.path.join(tempfile.mkdtemp(prefix="mcdonald-"), "track_strip.png")
                    self.strip_ready.emit(path, vf.track_strip(self.clip, last.track, path))
            except Exception as ex:                  # shown in the window; a dead thread would say nothing
                self.link_progress.emit(autolink.Link("done", f"the link failed: {ex}", done=True))
        self._link_thread = threading.Thread(target=job, daemon=True, name="mcdonald-link")
        self._link_thread.start()
        self.link_button.setText("stop linking (l)")

    @QtCore.Slot(object)
    def _on_link(self, link):
        if link.track or link.done or self.link is None:
            self.link = link
        if link.size is not None:                    # show the choice where the detector's controls are; 'c' then uses it
            for box in (self.size_box, self.dark_box):
                box.blockSignals(True)
            self.size_box.setValue(int(round(link.size)))
            self.dark_box.setChecked(bool(link.dark))
            for box in (self.size_box, self.dark_box):
                box.blockSignals(False)
        if link.done:
            self.link_button.setText("link from the marks (l)")
        if self._link_path is not None:
            self.view.scene().removeItem(self._link_path)
            self._link_path = None
        if len(self.link.track) > 1:
            ns = sorted(self.link.track)
            path = QtGui.QPainterPath(QtCore.QPointF(*self.link.track[ns[0]]))
            for k in ns[1:]:
                path.lineTo(*self.link.track[k])
            self._link_path = self.view.scene().addPath(path, QtGui.QPen(QtGui.QColor(AUTO), 0))
            self._link_path.setZValue(3)
        self._say_link(link.say)
        self.draw()

    def _say_link(self, say=None):
        if say is not None:
            self._link_said = say
        text = self._link_said
        if self.link is not None and self.link.track and \
                self._link_marks != self.ms.marks.get(CLASSES[self._link_cls], {}):
            text += "\nThe marks have changed since this was linked; l links again."
        self.link_label.setText(text)

    @QtCore.Slot(str, object)
    def _show_track_strip(self, path, frames):
        """The pipeline's own check, put in front of the person who knows which thing
        the object is. CHECK WHAT IT LOCKED ONTO, as link_track's docstring says."""
        if self.track_strip is not None:
            self.track_strip.close()
        d = self.track_strip = QtWidgets.QDialog(self)
        d.setWindowTitle("the automatic track — is this the object, all the way?")
        lay = QtWidgets.QVBoxLayout(d)
        d.strip = TrackStrip(path, frames)
        d.strip.chosen.connect(self.goto)
        area = QtWidgets.QScrollArea()
        area.setWidget(d.strip)
        lay.addWidget(area)
        lay.addWidget(QtWidgets.QLabel("Crops along the track, the clip's own pixels. Click one to go to its frame; "
                                       "play the clip to watch the box ride the object, or not."))
        d.resize(min(d.strip.pixmap().width() + 40, 1500), d.strip.pixmap().height() + 90)
        d.show()

    # -- overview --------------------------------------------------------------------------
    def open_overview(self):
        self.overview = Overview(self, self.clip, self.store)
        self.overview.chosen.connect(self._from_overview)
        self.overview.show()

    def _from_overview(self, n):
        self.overview.close()
        self.goto(n)

    # -- keys ------------------------------------------------------------------------------
    def keyPressEvent(self, e):
        k, text, mod = e.key(), e.text(), e.modifiers()
        ctrl, shift = bool(mod & Qt.KeyboardModifier.ControlModifier), bool(mod & Qt.KeyboardModifier.ShiftModifier)
        if ctrl:
            if k == Qt.Key.Key_Z:
                (self._undo.redo if shift else self._undo.undo)()
            elif k == Qt.Key.Key_Y:
                self._undo.redo()
            elif k == Qt.Key.Key_S:
                self.finish()
            return
        if text == "," or (k == Qt.Key.Key_Left and not shift):
            self.goto(self.n - 1)
        elif text == "." or (k == Qt.Key.Key_Right and not shift):
            self.goto(self.n + 1)
        elif text == "<" or k == Qt.Key.Key_Left:
            self.goto(self.n - 10)
        elif text == ">" or k == Qt.Key.Key_Right:
            self.goto(self.n + 10)
        elif k == Qt.Key.Key_Home:
            self.goto(self.clip.n0)
        elif k == Qt.Key.Key_End:
            self.goto(self.clip.n1)
        elif text == "[":
            self._marked_neighbour(-1)
        elif text == "]":
            self._marked_neighbour(+1)
        elif k == Qt.Key.Key_Space:
            self.toggle_play()
        elif text == "-":
            self.change_speed(-1)
        elif text in ("=", "+"):
            self.change_speed(+1)
        elif text.isdigit() and 1 <= int(text) <= len(CLASSES):
            self.set_class(int(text) - 1)
        elif k in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.delete_here()
        elif text == "r":
            self.view.fit()
        elif text == "c":
            self.set_candidates(not self._cand_on)
        elif text == "l":
            self.toggle_link()
        elif text == "t":
            self._show_track = not self._show_track
            self.draw()
        elif text == "o":
            self.open_overview()
        elif text == "s":
            self.finish()
        elif text == "q":
            self.finish(show_strip=False)            # the window is going; the terminal says where the strip is
            self.close()
        else:
            super().keyPressEvent(e)

    def _frame_typed(self, n):
        self.goto(n)
        self.view.setFocus()

    # -- saving ----------------------------------------------------------------------------
    def finish(self, show_strip=True):
        said = save_all(self.clip, self.ms, self.out)
        if self.link is not None and self.link.track:
            auto = autolink.write_track_csv(f"{self.out}_autotrack.csv", self.link, self.ms.video, self.clip.fps)
            vf.track_strip(self.clip, self.link.track, f"{self.out}_autotrack_strip.png")
            said.append(f"wrote {auto} and {self.out}_autotrack_strip.png  -- the automatic track: {self.link.say}")
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
        d = self.saved_strip = QtWidgets.QDialog(self)
        d.setWindowTitle("saved — now look at it")
        lay = QtWidgets.QVBoxLayout(d)
        pic = QtWidgets.QLabel()
        pic.setPixmap(QtGui.QPixmap(path))
        area = QtWidgets.QScrollArea()
        area.setWidget(pic)
        lay.addWidget(area)
        lay.addWidget(QtWidgets.QLabel("A mark you have not seen drawn back onto the pixels is a number you are "
                                       "trusting, not one you have verified.\n" + path))
        d.resize(min(pic.pixmap().width() + 40, 1400), min(pic.pixmap().height() + 90, 800))
        d.show()

    def unsaved_answer(self):
        """Ask what to do with unsaved marks: 'save', 'discard' or 'cancel'."""
        B = QtWidgets.QMessageBox.StandardButton
        b = QtWidgets.QMessageBox.question(self, "unsaved marks", "Save the marks before closing?",
                                           B.Save | B.Discard | B.Cancel, B.Save)
        return {B.Save: "save", B.Discard: "discard"}.get(b, "cancel")

    def closeEvent(self, e):
        if not self._undo.isClean():
            answer = self.unsaved_answer()
            if answer == "cancel":
                e.ignore()
                return
            if answer == "save":
                self.finish()
        self._timer.stop()
        self._link_stop.set()
        self.store.close()
        e.accept()

    def run(self):
        self.show()
        self.view.setFocus()
        self.app.exec()


def choose_video():
    """A file dialog, for `mcdonald mark` with no clip named."""
    application()
    path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "mcdonald mark — choose a clip", "",
                                                    "Video (*.mp4 *.mov *.mkv *.avi *.m4v *.ts *.mpg *.wmv);;All files (*)")
    return path or None
