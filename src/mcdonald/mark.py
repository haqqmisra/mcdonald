"""`mcdonald mark` — click the object on a few frames.

Everything downstream needs to know which thing in the frame is the object,
and nothing in this toolkit can decide that. Two clicks are usually enough:
they give the seed the linker starts from and the velocity it cannot acquire
without (`forensics.velocity_from_marks`), after which the automatic track
covers the rest.

Why a desktop window and not a browser. The hard part of marking is frame
accuracy — being certain that the frame you clicked is the frame ffmpeg calls
n — and in a browser that is genuinely hard: the video element presents
whatever frame contains `currentTime`, seeks land between frames, and the
reported time needs a sub-frame bias to agree with ffmpeg. Here the frames are
already on disk as losslessly extracted PNGs **named by their absolute frame
number**, so "which frame is this" is answered by the filename. The whole
class of error disappears.

The display is matplotlib, which the package already depends on, so marking
adds nothing to install. It needs an interactive backend: Qt, GTK or Tk,
whichever the system has.

    mcdonald mark CLIP.mp4 --n0 400 --n1 420

Controls
    click           place a mark of the current class
    , .             previous / next frame          < >   -/+ 10 frames
    1..6            mark class: object, object #2, boresight, north, reference, horizon
    backspace       delete the last mark on this frame
    scroll          zoom about the cursor          drag   pan
    r               reset the view
    s               save
    q               save and quit

Writes <tag>_marks.json and <tag>_marks.png — the marked frames with the marks
drawn on them, magnified, which is how the coordinates get checked by eye
rather than trusted.
"""
import json
from pathlib import Path

import numpy as np

from . import forensics as vf

CLASSES = ["object", "object2", "boresight", "north", "reference", "horizon"]
COLOURS = ["#eb6834", "#eda100", "#2a78d6", "#1baf7a", "#e87ba4", "#9085e9"]


class MarkSet:
    """The marks, independent of any display.

    Kept separate so the state machine can be tested without a window, and so
    another front end could drive the same file format."""

    def __init__(self, tag, video, fps, path=None):
        self.tag, self.video, self.fps = tag, str(video), float(fps)
        self.marks = {}                      # {class: {frame: (x, y)}}
        self.path = Path(path) if path else None
        if self.path and self.path.exists():
            self.load(self.path)

    def add(self, cls, frame, x, y):
        self.marks.setdefault(cls, {})[int(frame)] = (float(x), float(y))

    def remove_last(self, cls, frame):
        d = self.marks.get(cls, {})
        return d.pop(int(frame), None)

    def frames(self, cls="object"):
        return sorted(self.marks.get(cls, {}))

    def track(self, cls="object"):
        return dict(self.marks.get(cls, {}))

    def velocity(self, cls="object"):
        """px/frame from the marks of one class, or None with fewer than two."""
        return vf.velocity_from_marks(self.marks.get(cls, {}))

    def seed(self, cls="object"):
        f = self.frames(cls)
        return None if not f else (f[0], *self.marks[cls][f[0]])

    def count(self):
        return sum(len(v) for v in self.marks.values())

    def to_dict(self):
        return {"tag": self.tag, "video": self.video, "fps": self.fps,
                "classes": {c: {str(n): list(xy) for n, xy in sorted(d.items())}
                            for c, d in self.marks.items() if d}}

    def save(self, path=None):
        p = Path(path or self.path)
        p.write_text(json.dumps(self.to_dict(), indent=1))
        return p

    def load(self, path):
        d = json.loads(Path(path).read_text())
        self.marks = {c: {int(n): tuple(xy) for n, xy in v.items()}
                      for c, v in d.get("classes", {}).items()}
        return self

    def write_track_csv(self, path, cls="object", note=""):
        """A track CSV the rest of the package reads, with provenance."""
        import csv
        d = self.marks.get(cls, {})
        if not d:
            return None
        with open(path, "w", newline="") as f:
            # comments are written raw, not through the csv writer: a line with
            # a comma in it would otherwise come back quoted, and a quoted
            # "# ..." is no longer a comment to anything else that reads it
            f.write(f"# hand marks ({cls}) on {Path(self.video).name}, "
                    f"placed with `mcdonald mark`\n")
            if note:
                f.write(f"# {note}\n")
            w = csv.writer(f)
            w.writerow(["frame", "t_s", "x_px", "y_px"])
            for n in sorted(d):
                w.writerow([n, round((n - 1) / self.fps, 4), round(d[n][0], 2), round(d[n][1], 2)])
        return path


def contact_strip(clip, ms, out, box=90, zoom=3):
    """The marked frames, magnified, with the marks drawn on them.

    The check that a coordinate is where you meant it. A mark you have not
    seen drawn back onto the pixels is a number you are trusting, not one you
    have verified."""
    from PIL import Image, ImageDraw
    from .figures import pil_font
    items = [(c, n, xy) for c, d in ms.marks.items() for n, xy in sorted(d.items())]
    if not items:
        return None
    cols = min(5, len(items))
    rows = (len(items) + cols - 1) // cols
    cell = box * zoom
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 18)), "#111111")
    dr = ImageDraw.Draw(sheet)
    font = pil_font(13)
    for i, (cls, n, (x, y)) in enumerate(items):
        cx, cy = i % cols * cell, i // cols * (cell + 18)
        x0, y0 = int(round(x)) - box // 2, int(round(y)) - box // 2
        crop = Image.fromarray(clip.rgb(n).astype(np.uint8)).crop((x0, y0, x0 + box, y0 + box))
        sheet.paste(crop.resize((cell, cell), Image.NEAREST), (cx, cy))
        col = COLOURS[CLASSES.index(cls) % len(COLOURS)] if cls in CLASSES else "#ffffff"
        px, py = cx + (x - x0) * zoom, cy + (y - y0) * zoom
        dr.line([(px - 11, py), (px - 3, py)], fill=col, width=2)
        dr.line([(px + 3, py), (px + 11, py)], fill=col, width=2)
        dr.line([(px, py - 11), (px, py - 3)], fill=col, width=2)
        dr.line([(px, py + 3), (px, py + 11)], fill=col, width=2)
        dr.text((cx + 4, cy + cell + 2), f"n={n}  {cls}  ({x:.1f}, {y:.1f})", fill="#dddddd", font=font)
    sheet.save(out)
    return out


# ---- the window -------------------------------------------------------------------------
class Marker:
    """The matplotlib front end. Thin: all state lives in MarkSet."""

    def __init__(self, clip, ms, out_prefix):
        import matplotlib.pyplot as plt
        self.clip, self.ms, self.out = clip, ms, out_prefix
        self.n = clip.n0
        self.cls = 0
        self.plt = plt
        self.fig, self.ax = plt.subplots(figsize=(13, 7.6))
        self.fig.canvas.manager.set_window_title(f"mcdonald mark — {ms.tag}")
        self.im = self.ax.imshow(clip.rgb(self.n).astype(np.uint8), interpolation="nearest")
        self.ax.set_axis_off()
        self.fig.subplots_adjust(0.01, 0.06, 0.99, 0.94)
        self.overlay = []
        self._pan = None
        for ev, fn in (("button_press_event", self.on_click),
                       ("button_release_event", self.on_release),
                       ("motion_notify_event", self.on_motion),
                       ("key_press_event", self.on_key),
                       ("scroll_event", self.on_scroll)):
            self.fig.canvas.mpl_connect(ev, fn)
        self.draw()

    # -- state ---------------------------------------------------------------------------
    def goto(self, n):
        self.n = int(np.clip(n, self.clip.n0, self.clip.n1))
        self.im.set_data(self.clip.rgb(self.n).astype(np.uint8))
        self.draw()

    def draw(self):
        for a in self.overlay:
            a.remove()
        self.overlay = []
        for ci, c in enumerate(CLASSES):
            xy = self.ms.marks.get(c, {}).get(self.n)
            if xy:
                self.overlay += list(self.ax.plot(xy[0], xy[1], "+", ms=16, mew=2,
                                                  color=COLOURS[ci]))
        t = (self.n - 1) / self.clip.fps
        v = self.ms.velocity()
        vtxt = "" if v is None else f"   v = ({v[0]:+.1f}, {v[1]:+.1f}) px/frame"
        self.ax.set_title(
            f"frame {self.n} / {self.clip.n1}    t = {t:.3f} s    "
            f"marking: {CLASSES[self.cls]}    {self.ms.count()} marks{vtxt}",
            fontsize=10, color=COLOURS[self.cls], loc="left")
        self.fig.canvas.draw_idle()

    # -- events --------------------------------------------------------------------------
    def on_click(self, e):
        if e.inaxes is not self.ax or e.xdata is None:
            return
        if e.button == 1:
            self.ms.add(CLASSES[self.cls], self.n, e.xdata, e.ydata)
            self.draw()
        elif e.button == 2:
            self._pan = (e.xdata, e.ydata, self.ax.get_xlim(), self.ax.get_ylim())

    def on_release(self, e):
        self._pan = None

    def on_motion(self, e):
        if self._pan and e.xdata is not None:
            x0, y0, xl, yl = self._pan
            dx, dy = e.xdata - x0, e.ydata - y0
            self.ax.set_xlim(xl[0] - dx, xl[1] - dx)
            self.ax.set_ylim(yl[0] - dy, yl[1] - dy)
            self.fig.canvas.draw_idle()

    def on_scroll(self, e):
        if e.xdata is None:
            return
        f = 0.8 if e.button == "up" else 1.25
        xl, yl = self.ax.get_xlim(), self.ax.get_ylim()
        self.ax.set_xlim(e.xdata + (xl[0] - e.xdata) * f, e.xdata + (xl[1] - e.xdata) * f)
        self.ax.set_ylim(e.ydata + (yl[0] - e.ydata) * f, e.ydata + (yl[1] - e.ydata) * f)
        self.fig.canvas.draw_idle()

    def on_key(self, e):
        k = e.key
        if k in (",", "left"):
            self.goto(self.n - 1)
        elif k in (".", "right"):
            self.goto(self.n + 1)
        elif k == "<":
            self.goto(self.n - 10)
        elif k == ">":
            self.goto(self.n + 10)
        elif k and k.isdigit() and 1 <= int(k) <= len(CLASSES):
            self.cls = int(k) - 1
            self.draw()
        elif k == "backspace":
            self.ms.remove_last(CLASSES[self.cls], self.n)
            self.draw()
        elif k == "r":
            self.ax.set_xlim(0, self.clip.W)
            self.ax.set_ylim(self.clip.H, 0)
            self.fig.canvas.draw_idle()
        elif k in ("s", "q"):
            self.finish()
            if k == "q":
                self.plt.close(self.fig)

    def finish(self):
        p = self.ms.save(f"{self.out}_marks.json")
        print(f"wrote {p}  ({self.ms.count()} marks)")
        csv_path = self.ms.write_track_csv(f"{self.out}_marks.csv")
        if csv_path:
            print(f"wrote {csv_path}")
        try:
            strip = contact_strip(self.clip, self.ms, f"{self.out}_marks.png")
            if strip:
                print(f"wrote {strip}  -- look at it: a mark you have not seen drawn "
                      "back onto the pixels is a number you are trusting, not one you "
                      "have verified")
        except Exception as ex:
            print(f"(contact strip not written: {ex})")
        v = self.ms.velocity()
        if v:
            print(f"velocity from the object marks: ({v[0]:+.1f}, {v[1]:+.1f}) px/frame "
                  f"= {np.hypot(*v) * self.clip.fps:.0f} px/s")
            print(f"  feed it to the linker:  link_track(..., seed={self.ms.seed()}, "
                  f"velocity=({v[0]:.1f}, {v[1]:.1f}))")

    def run(self):
        self.plt.show()


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__[__doc__.index("Controls"):])
    ap.add_argument("video")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--load", help="an existing _marks.json to continue")
    ap.add_argument("--out", metavar="DIR", help="case directory (default: ./<tag>)")
    args = ap.parse_args()

    import matplotlib
    if matplotlib.get_backend().lower() in ("agg", "pdf", "ps", "svg", "template"):
        raise SystemExit(
            f"matplotlib is using the non-interactive '{matplotlib.get_backend()}' backend, "
            "so no window can open. Options:\n"
            "  pip install PySide6                      (any platform; LGPL)\n"
            "  dnf install python3-tkinter python3-pillow-tk     (Fedora/RHEL)\n"
            "  apt install python3-tk                            (Debian/Ubuntu)\n"
            "  brew install python-tk                            (Homebrew Python on macOS)\n"
            "matplotlib's Tk backend needs PIL's ImageTk as well as tkinter, and some "
            "distributions package those separately -- installing tkinter alone is not "
            "always enough.\n"
            "Or mark the object elsewhere and pass the positions as a track CSV: any file "
            "with a frame column and an x/y pair works.")

    video, tag, _ = vf.resolve(args.video)
    clip = vf.Clip(video, args.workdir, args.n0, args.n1)
    out = vf.out_prefix(args.out, tag)
    ms = MarkSet(tag, video, clip.fps, args.load or f"{out}_marks.json")
    print(f"{video.name}: frames {clip.n0}-{clip.n1} at {clip.info['fps']} fps")
    print("click the object; ',' '.' step frames; '1'-'6' pick the class; 's' save; 'q' quit")
    Marker(clip, ms, str(out)).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
