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

There are two windows over the same marks, and `--gui auto` takes the first
that will open.

- The Qt window (`mark_qt.QtMarker`; `pip install PySide6-Essentials`, or the
  package's `gui` extra) is for finding the object in a clip you have not seen:
  a timeline over the whole clip, playback at true speed, an overview, detector
  candidates, a loupe, undo -- and `l`, which links an automatic track from the
  marks (`autolink`) and draws it over the clip, so that whether it locked onto
  the object is settled where the marks were made. Run it with no clip named
  and it asks for one.
- The matplotlib window (`Marker`, below) needs nothing the package does not
  already depend on, only an interactive backend -- Qt, GTK or Tk, whichever
  the system has. It is enough when you know which frames to look at.

All state lives in `MarkSet`, both save through `save_all`, and
tests/test_gui.py runs the same checks against each.

    mcdonald mark CLIP.mp4                        # the whole clip, in the Qt window if there is one
    mcdonald mark CLIP.mp4 --n0 400 --n1 420      # a window of it
    mcdonald mark CLIP.mp4 --gui mpl              # the matplotlib window regardless

And with no window at all, for something that cannot click -- an agent that has
found the object with `mcdonald look`:

    mcdonald mark CLIP.mp4 --n0 400 --n1 420 --no-window --link --json \\
        --set object@408=1010.9,313.0 --set object@411=702.4,604.2 \\
        --why "candidate 1 of 6 at 21 px dark on 408 and 411: the only compact dark source that moves"

which writes what the window's `s` writes, and with --link the automatic track
too. A mark placed this way is recorded as an agent's (`MarkSet.how`), with the
reason given, and never counts as a hand mark: which thing is the object is a
judgment, and the files say who made it.

The keys, for both windows, are rows of `actions.ACTIONS`: `mcdonald mark --help`
prints them, and the Qt window has them under Help.

Writes <tag>_marks.json and <tag>_marks.png — the marked frames with the marks
drawn on them, magnified, which is how the coordinates get checked by eye
rather than trusted.
"""
import json
from pathlib import Path

import numpy as np

from . import forensics as vf

CLASSES = ["object", "object2", "boresight", "north", "reference", "horizon"]
LINKED = ("object", "object2")                    # the classes that are things in the scene, and so can be tracked
COLOURS = ["#eb6834", "#eda100", "#2a78d6", "#1baf7a", "#e87ba4", "#9085e9"]


class MarkSet:
    """The marks, independent of any display.

    Kept separate so the state machine can be tested without a window, and so
    another front end could drive the same file format.

    A mark is where a hand put it unless `how` says otherwise. There are two
    other ways in. Snapping to the detector's centroid ("snapped to ..."): such
    a mark agrees with the detector because it *is* the detector, so it cannot
    be used to check one. And `mcdonald mark --set` ("agent: ..."), which is
    how something with no window places a mark: the package's founding claim is
    that no detector can say which thing is the object and a person looking
    can, so when an agent made that judgment the record has to say it did, and
    why. Neither may ever pass for a hand mark. `how` travels with the mark
    into the JSON, the CSV, the contact strip, the automatic track's header and
    the case report. Placing a mark by hand on the same frame clears it."""

    def __init__(self, tag, video, fps, path=None):
        self.tag, self.video, self.fps = tag, str(video), float(fps)
        self.marks = {}                      # {class: {frame: (x, y)}}
        self.how = {}                        # {class: {frame: str}}, only for marks that are not plain hand marks
        self.path = Path(path) if path else None
        if self.path and self.path.exists():
            self.load(self.path)

    def add(self, cls, frame, x, y, how=None):
        self.marks.setdefault(cls, {})[int(frame)] = (float(x), float(y))
        if how:
            self.how.setdefault(cls, {})[int(frame)] = str(how)
        else:
            self.how.get(cls, {}).pop(int(frame), None)

    def remove_last(self, cls, frame):
        d = self.marks.get(cls, {})
        self.how.get(cls, {}).pop(int(frame), None)
        was = d.pop(int(frame), None)
        if not d:                            # a class with no marks is no class: what is saved and what is held agree
            self.marks.pop(cls, None)
        return was

    def how_of(self, cls, frame):
        """None for a hand mark, else what was done to it."""
        return self.how.get(cls, {}).get(int(frame))

    def kind(self, cls, frame):
        """'hand', 'snapped' or 'agent': `how`, in a word, for a table or a caption."""
        how = self.how_of(cls, frame)
        return "hand" if not how else "agent" if how.startswith("agent:") else "snapped" if how.startswith("snapped") else "other"

    def not_by_hand(self, cls="object"):
        """{frame: how} for the marks of a class that no hand placed."""
        return {n: self.how_of(cls, n) for n in self.marks.get(cls, {}) if self.how_of(cls, n)}

    def by_hand(self, cls="object"):
        """The marks of a class a hand placed: the only ones fit to check a detector against."""
        return {n: xy for n, xy in self.marks.get(cls, {}).items() if not self.how_of(cls, n)}

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
        d = {"tag": self.tag, "video": self.video, "fps": self.fps,
             "classes": {c: {str(n): list(xy) for n, xy in sorted(d.items())}
                         for c, d in self.marks.items() if d}}
        how = {c: {str(n): h for n, h in sorted(v.items())} for c, v in self.how.items() if v}
        if how:                              # absent when every mark is a hand mark, so old readers see an old file
            d["how"] = how
        return d

    def save(self, path=None):
        p = Path(path or self.path)
        p.write_text(json.dumps(self.to_dict(), indent=1))
        return p

    def load(self, path):
        d = json.loads(Path(path).read_text())
        self.marks = {c: {int(n): (float(xy[0]), float(xy[1])) for n, xy in v.items()}
                      for c, v in d.get("classes", {}).items()}
        self.how = {c: {int(n): h for n, h in v.items() if int(n) in self.marks.get(c, {})}
                    for c, v in d.get("how", {}).items()}
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
            f.write(f"# {'marks' if self.not_by_hand(cls) else 'hand marks'} ({cls}) on {Path(self.video).name}, "
                    f"placed with `mcdonald mark`\n")
            kinds = [self.kind(cls, n) for n in d if self.how_of(cls, n)]
            if kinds:
                f.write(f"# {len(kinds)} of {len(d)} are NOT hand positions: see the `how` column."
                        + (" A snapped mark agrees with the detector because it is the detector's." if "snapped" in kinds else "")
                        + (" An agent's mark is an agent's judgment of which thing is the object, not a person's."
                           if "agent" in kinds else "") + "\n")
            if note:
                f.write(f"# {note}\n")
            w = csv.writer(f)
            w.writerow(["frame", "t_s", "x_px", "y_px", "how"])
            for n in sorted(d):
                w.writerow([n, round((n - 1) / self.fps, 4), round(d[n][0], 2), round(d[n][1], 2),
                            self.how_of(cls, n) or "hand"])
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
        dr.text((cx + 4, cy + cell + 2), f"n={n}  {cls}  ({x:.1f}, {y:.1f}){'  ' + ms.kind(cls, n) if ms.how_of(cls, n) else ''}",
                fill="#dddddd", font=font)
    sheet.save(out)
    return out


def save_all(clip, ms, out_prefix):
    """Write the marks, the track CSV and the contact strip; return what to tell
    the user, line by line.

    Both front ends save through here, so that what lands on disk cannot depend
    on which window placed the marks."""
    said = [f"wrote {ms.save(f'{out_prefix}_marks.json')}  ({ms.count()} marks)"]
    csv_path = ms.write_track_csv(f"{out_prefix}_marks.csv")
    if csv_path:
        said.append(f"wrote {csv_path}")
    try:
        strip = contact_strip(clip, ms, f"{out_prefix}_marks.png")
        if strip:
            said.append(f"wrote {strip}  -- look at it: a mark you have not seen drawn "
                        "back onto the pixels is a number you are trusting, not one you "
                        "have verified")
    except Exception as ex:
        said.append(f"(contact strip not written: {ex})")
    v = ms.velocity()
    if v:
        said.append(f"velocity from the object marks: ({v[0]:+.1f}, {v[1]:+.1f}) px/frame "
                    f"= {np.hypot(*v) * clip.fps:.0f} px/s")
        said.append(f"  feed it to the linker:  link_track(..., seed={seed_text(ms.seed())}, "
                    f"velocity=({v[0]:.1f}, {v[1]:.1f}))")
    return said


def apply_sets(ms, clip, sets, unsets, why=None):
    """--set CLASS@FRAME=X,Y and --unset CLASS@FRAME, applied to a MarkSet. Returns the
    (class, frame) pairs that were set. `clip` is the whole clip: a mark has to be on it."""
    from .clip import EXIT_USAGE, Stop
    how = "agent: " + (why.strip() if why and why.strip() else "placed with --set; no reason was given")
    done = []
    for spec in sets:
        try:
            where, xy = spec.split("=")
            cls, n = where.split("@")
            n, (x, y) = int(n), (float(v) for v in xy.split(","))
        except ValueError:
            raise Stop(f"--set {spec}: give it as CLASS@FRAME=X,Y, e.g. object@408=1009,313", EXIT_USAGE)
        if cls not in CLASSES:
            raise Stop(f"--set {spec}: no class {cls!r}; the classes are {', '.join(CLASSES)}", EXIT_USAGE)
        if not (1 <= n <= clip.n1 and -0.5 <= x <= clip.W - 0.5 and -0.5 <= y <= clip.H - 0.5):
            raise Stop(f"--set {spec}: the clip has frames 1-{clip.n1} of {clip.W}x{clip.H} px, and that is not on it", EXIT_USAGE)
        ms.add(cls, n, x, y, how=how)
        done.append((cls, n))
    for spec in unsets:
        try:
            cls, n = spec.split("@")
            ms.remove_last(cls, int(n))
        except ValueError:
            raise Stop(f"--unset {spec}: give it as CLASS@FRAME, e.g. object@408", EXIT_USAGE)
    return done


def headless(args):
    """`mcdonald mark --no-window`: what the window's 's' does, and with --link its 'l',
    for something that cannot click. Same MarkSet, same save_all, same autolink, same files."""
    import sys
    from . import autolink
    from .clip import EXIT_NOTHING, EXIT_USAGE, Stop
    from .report import emit, envelope
    say = (lambda *a: print(*a, file=sys.stderr)) if args.json else print
    if args.video is None:
        raise Stop("name a clip", EXIT_USAGE)
    video, tag, _ = vf.resolve(args.video)
    whole = vf.Clip(video, args.workdir, extract=False)
    out = vf.out_prefix(args.out, tag)
    ms = MarkSet(tag, video, whole.fps, args.load or f"{out}_marks.json")
    placed = apply_sets(ms, whole, args.set, args.unset, args.why)
    if not ms.count():
        raise Stop("there are no marks: place one with --set CLASS@FRAME=X,Y (`mcdonald look` is how to find where)", EXIT_NOTHING)

    # the frames to work on. The contact strip needs the marked ones; the link searches
    # all of them, back from the first mark and on from the last, so it is worth saying
    marked = sorted(n for d in ms.marks.values() for n in d)
    n0 = args.n0 or max(1, marked[0] - 30)
    n1 = args.n1 or min(whole.n1, marked[-1] + 30)
    notes = []
    if args.n0 is None or args.n1 is None:
        notes.append(f"no --n0/--n1, so frames {n0}-{n1} were used: 30 either side of the marks. "
                     "A link stops at the ends of that range whether or not the object does.")
    clip = vf.Clip(video, args.workdir, n0, n1, extract=False)
    say(vf.cost_text(clip.cost()))
    clip.extract()
    outside = [n for n in marked if not n0 <= n <= n1]
    if outside:
        raise Stop(f"the marks on frames {', '.join(map(str, outside))} are outside --n0/--n1 ({n0}-{n1})", EXIT_USAGE)
    if placed and not (args.why or "").strip():
        notes.append("no --why: the record says an agent placed these marks, and not what it chose or why.")

    said = save_all(clip, ms, out)
    files = [f"{out}_marks.json"] + [f"{out}_marks.{e}" for e in ("csv", "png") if Path(f"{out}_marks.{e}").exists()]
    v = ms.velocity()
    results = {"marks": {c: {str(n): {"x": xy[0], "y": xy[1], "placed_by": ms.kind(c, n), "how": ms.how_of(c, n)}
                             for n, xy in sorted(d.items())} for c, d in ms.marks.items()},
               "placed_now": [f"{c}@{n}" for c, n in placed],
               "velocity_px_per_frame": None if v is None else [round(float(v[0]), 3), round(float(v[1]), 3)],
               "speed_px_per_frame": None if v is None else round(float(np.hypot(*v)), 2)}
    no_power, needs, code, error = [], [], 0, None
    if v is None:
        no_power.append(("velocity", "fewer than two marks on the object: one mark is a seed, a second gives the "
                                     "velocity a fast object cannot be linked without"))
    if args.link:
        results["link"] = {}
        for cls in LINKED:
            marks = {n: xy for n, xy in ms.marks.get(cls, {}).items()}
            if not marks:
                continue
            say(f"linking the {cls} from {len(marks)} mark{'s' if len(marks) != 1 else ''}")
            link = autolink.track_from_marks(clip, marks, say=lambda line: say(f"  {line}"))
            results["link"][cls] = link.to_dict()
            if link.track:
                path, strip = autolink.save_track(clip, link, out, cls, how=ms.not_by_hand(cls), video=ms.video)
                files += [path, strip]
                said.append(f"wrote {path} and {strip}  -- the automatic track of the {cls}: {link.say}")
                needs.append(f"a look at {strip}: nothing here can know whether the marks were on the object, "
                             "and everything measured from this track assumes it")
            else:
                no_power.append((f"link ({cls})", link.say))
        if not results["link"]:
            code, error = EXIT_NOTHING, f"--link: there are no marks of {' or '.join(LINKED)} to link from"
        elif not any(k["frames_linked"] for k in results["link"].values()):
            code, error = EXIT_NOTHING, "--link: nothing was linked; see no_power for what the linker said"
    agents = sum(1 for c in ms.marks for n in ms.marks[c] if ms.kind(c, n) == "agent")
    if agents:
        notes.append(f"{agents} of {ms.count()} marks were placed by an agent, not by a person looking at the frame. "
                     "The marks file, the CSVs and any report made from them say so.")
    for line in said + notes:
        say(line)
    if error:
        say(f"mcdonald: {error}")
    if args.json:
        inputs = {k: v for k, v in vars(args).items() if v not in (None, False, []) and k not in ("json", "gui")}
        emit(envelope("mark", inputs, clip, files, results, no_power, needs, notes, code, error))
    return code


def seed_text(seed):
    """(n, x, y) for people: a position that has been through a view transform
    and back carries 1e-13 px of noise, which is not worth fourteen digits."""
    return None if seed is None else f"({seed[0]}, {round(seed[1], 2):g}, {round(seed[2], 2):g})"


def status_line(clip, ms, n, cls):
    """What the window says about where you are. Shared, so the two front ends agree."""
    v = ms.velocity()
    vtxt = "" if v is None else f"   v = ({v[0]:+.1f}, {v[1]:+.1f}) px/frame"
    return (f"frame {n} / {clip.n1}    t = {(n - 1) / clip.fps:.3f} s    "
            f"marking: {CLASSES[cls]}    {ms.count()} marks{vtxt}")


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
        self._home = (self.ax.get_xlim(), self.ax.get_ylim())
        self.overlay = []
        self._pan = None
        from . import actions                # here, not at the top: actions needs this module's CLASSES
        self._handlers = self.handlers()
        self._keys = {actions.mpl_key(k): a.id for a in actions.for_window("mpl") for k in a.keys}
        # matplotlib binds keys of its own to every figure, and they collide with
        # these: 's' would also open its save-figure dialog, 'l' and 'k' put the
        # image on log axes, backspace walks its view history
        self.fig.canvas.mpl_disconnect(self.fig.canvas.manager.key_press_handler_id)
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
        self.ax.set_title(status_line(self.clip, self.ms, self.n, self.cls),
                          fontsize=10, color=COLOURS[self.cls], loc="left")
        self.fig.canvas.draw_idle()

    # -- events --------------------------------------------------------------------------
    def on_click(self, e):
        if e.inaxes is not self.ax or e.xdata is None:
            return
        # while the toolbar's zoom or pan is armed the click is the toolbar's; if it
        # were a mark as well, zooming in for a closer look would move the object
        if getattr(self.fig.canvas.toolbar, "mode", ""):
            return
        if e.button == 1:
            self.ms.add(CLASSES[self.cls], self.n, e.xdata, e.ydata)
            self.draw()
        elif e.button == 2:
            # the transform as it is now, frozen. xdata on the motion events that
            # follow is read through limits the drag has already moved, and
            # differencing that against the press makes the view snap back
            inv = self.ax.transData.inverted().frozen()
            self._pan = (inv, inv.transform((e.x, e.y)), self.ax.get_xlim(), self.ax.get_ylim())

    def on_release(self, e):
        self._pan = None

    def on_motion(self, e):
        if self._pan:
            inv, p0, xl, yl = self._pan
            dx, dy = inv.transform((e.x, e.y)) - p0
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
        act = self._keys.get(e.key)
        if act:
            self._handlers[act]()

    def handlers(self):
        """What each row of actions.ACTIONS is, in this window."""
        h = {"save": self.finish, "quit": self.save_and_quit, "delete": self.delete_here, "fit": self.fit,
             "prev": lambda: self.goto(self.n - 1), "next": lambda: self.goto(self.n + 1),
             "back10": lambda: self.goto(self.n - 10), "on10": lambda: self.goto(self.n + 10),
             "first": lambda: self.goto(self.clip.n0), "last": lambda: self.goto(self.clip.n1)}
        h.update({f"class_{i + 1}": lambda i=i: self.set_class(i) for i in range(len(CLASSES))})
        return h

    def set_class(self, i):
        self.cls = i
        self.draw()

    def delete_here(self):
        self.ms.remove_last(CLASSES[self.cls], self.n)
        self.draw()

    def fit(self):
        self.ax.set_xlim(self._home[0])
        self.ax.set_ylim(self._home[1])
        self.fig.canvas.draw_idle()

    def save_and_quit(self):
        self.finish()
        self.plt.close(self.fig)

    def finish(self):
        print("\n".join(save_all(self.clip, self.ms, self.out)))

    def run(self):
        self.plt.show()


def choose_gui(want="auto"):
    """'qt' or 'mpl', or SystemExit with what to install.

    Qt is preferred when PySide6 imports and there is a display to open it on.
    The display is checked here because Qt does not raise without one: it
    aborts the process."""
    import os
    import sys
    if want in ("auto", "qt"):
        try:
            import PySide6.QtWidgets  # noqa: F401
            have_qt = True
        except ImportError:
            have_qt = False
        seen = sys.platform in ("win32", "darwin") or os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        if have_qt and seen:
            return "qt"
        if want == "qt":
            raise SystemExit("--gui qt needs PySide6 and a display: " +
                             ("no DISPLAY or WAYLAND_DISPLAY is set." if have_qt else
                              "pip install PySide6-Essentials   (any platform; LGPL)"))
    import matplotlib
    if matplotlib.get_backend().lower() in ("agg", "pdf", "ps", "svg", "template"):
        raise SystemExit(
            f"matplotlib is using the non-interactive '{matplotlib.get_backend()}' backend, "
            "so no window can open. Options:\n"
            "  pip install PySide6-Essentials                    (any platform; LGPL; and the better window)\n"
            "  dnf install python3-tkinter python3-pillow-tk     (Fedora/RHEL)\n"
            "  apt install python3-tk                            (Debian/Ubuntu)\n"
            "  brew install python-tk                            (Homebrew Python on macOS)\n"
            "matplotlib's Tk backend needs PIL's ImageTk as well as tkinter, and some "
            "distributions package those separately -- installing tkinter alone is not "
            "always enough.\n"
            "Or mark the object elsewhere and pass the positions as a track CSV: any file "
            "with a frame column and an x/y pair works.")
    return "mpl"


def main():
    import argparse
    from . import actions
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=actions.controls() + "\n" + __doc__[__doc__.index("Writes <tag>_marks.json"):])
    ap.add_argument("video", nargs="?", help="a clip or a catalog id; the Qt window asks if it is left out")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--load", help="an existing _marks.json to continue")
    ap.add_argument("--out", metavar="DIR", help="case directory (default: ./<tag>)")
    ap.add_argument("--gui", choices=("auto", "qt", "mpl"), default="auto",
                    help="which window: qt (needs PySide6), mpl (matplotlib), or auto, the first that will open")
    ap.add_argument("--set", action="append", default=[], metavar="CLASS@FRAME=X,Y",
                    help="place a mark with no click, e.g. object@408=1009,313 (repeatable). It is recorded as an agent's")
    ap.add_argument("--unset", action="append", default=[], metavar="CLASS@FRAME", help="remove a mark (repeatable)")
    ap.add_argument("--why", help="with --set: what was chosen and why, recorded with each mark "
                                  '("candidate 2 of 9 at 21 px dark; the only one that moves")')
    ap.add_argument("--no-window", action="store_true",
                    help="open nothing: apply --set/--unset, save, and with --link write the automatic track")
    ap.add_argument("--link", action="store_true", help="with --no-window: link an automatic track from the marks")
    ap.add_argument("--json", action="store_true", help="with --no-window: print what was written and found as JSON on stdout")
    args = ap.parse_args()

    if args.no_window:
        return headless(args)
    if args.link or args.json:
        ap.error("--link and --json go with --no-window; in a window, 'l' links and 's' saves")
    if args.set or args.unset:                        # placed first, then the window opens on them to be looked at
        video, tag, _ = vf.resolve(args.video or ap.error("--set needs a clip"))
        total = vf.Clip(video, args.workdir, extract=False)
        out = vf.out_prefix(args.out, tag)
        ms = MarkSet(tag, video, total.fps, args.load or f"{out}_marks.json")
        apply_sets(ms, total, args.set, args.unset, args.why)
        args.load = str(ms.save(f"{out}_marks.json"))

    gui = choose_gui(args.gui)
    if gui == "qt":
        # one way in for this command and for `mcdonald-gui`: mark_qt.open_session asks which
        # part of the clip where --n0/--n1 do not say, and extracts behind a progress bar
        from . import mark_qt
        if args.video is None:
            args.video = mark_qt.choose_video()
            if args.video is None:
                return 1
        video, _, _ = vf.resolve(args.video)          # here, so that a name that resolves to nothing is said in the terminal
        w = mark_qt.open_session(video, args.n0, args.n1, args.out, args.load, args.workdir)
        if w is None:
            print("nothing was opened")
            return 1
        print(f"{video.name}: frames {w.clip.n0}-{w.clip.n1} at {w.clip.info['fps']} fps")
        print("click the object on two frames, then 'l' links an automatic track from them; space plays; "
              "'o' is an overview; 'c' asks the detector; 's' save; 'q' quit. Help -> Keys lists the rest")
        w.run()
        return 0
    if args.video is None:
        ap.error("name a clip (only the Qt window can ask for one)")

    video, tag, _ = vf.resolve(args.video)
    if args.n0 is None and args.n1 is None:
        print(f"{video.name}: opening the whole clip. Frames are extracted losslessly the first time, "
              "which takes a while on a long clip; --n0/--n1 open a window of it.")
    clip = vf.Clip(video, args.workdir, args.n0, args.n1, extract=False)
    print(vf.cost_text(clip.cost()))
    clip.extract()
    out = vf.out_prefix(args.out, tag)
    ms = MarkSet(tag, video, clip.fps, args.load or f"{out}_marks.json")
    print(f"{video.name}: frames {clip.n0}-{clip.n1} at {clip.info['fps']} fps")
    print("click the object; ',' '.' step frames; '1'-'6' pick the class; 's' save; 'q' quit")
    Marker(clip, ms, str(out)).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
