"""What the marking windows do, written down once.

Every action either window offers -- its keys, what a menu calls it, one line
of help -- is a row of `ACTIONS`. The Qt window's menus and shortcuts, its
Help -> Keys page, the matplotlib window's key handler and the epilog of
`mcdonald mark --help` are all made from these rows, so a key cannot be bound
in one place and described differently in another. Before this table the list
existed three times by hand, and the person at the window could read none of
them: they were in two docstrings and a `keyPressEvent`.

No toolkit is imported here. A window binds a row to something it can do by
the row's id (`handlers()` in each), and tests/test_gui.py presses every key
of every row at each window and checks that the row's handler ran, and only
that one.

Keys are spelled as Qt's portable key sequences are ("Ctrl+Shift+Z",
"Backspace", ","), since that is also what a menu shows; `mpl_key` gives the
name matplotlib reports for the same key. On macOS Qt reads "Ctrl" as the
command key and draws it as one, which is what a person there expects.
"""
import textwrap
from typing import NamedTuple

from .mark import CLASSES

MENUS = ["File", "Edit", "Mark", "View", "Go", "Track", "Measure", "Help"]


class Group(NamedTuple):
    """Rows that a list of keys shows as one line: the six classes, the four arrows."""
    keys: str
    help: str


class Action(NamedTuple):
    id: str                 # what a window's handlers are keyed by
    menu: str               # one of MENUS; "Edit>Nudge the mark" is a submenu
    text: str               # what the menu calls it
    keys: tuple             # the first is the one a menu shows
    help: str               # one line: the status bar under a menu, Help -> Keys, --help
    mpl: bool = False       # the matplotlib window has it too
    check: bool = False     # a state that is on or off, shown ticked
    sep: bool = False       # a separator above it in the menu
    group: Group = None


class Gesture(NamedTuple):
    """The mouse. Listed with the keys, bound by the windows themselves."""
    keys: str
    help: str
    mpl: bool = False


SNAP_PX = 12.0              # how far shift+click reaches for a spot; the window's, and the help's

# Everything below that a person reads is written in plain words (docs/handoff-ui.md, "The player,
# and plain words", has the vocabulary; tests/test_gui.py's drive_plain_words holds it): a video, not a clip; a spot the computer found, not a detector's candidate; a kind of
# mark, not a class. "frame", "mark", "track" and "link" are the four words of the trade that are
# kept, and Help -> Getting started says what each means before it uses them.
_WHAT = {"object": "the object", "object2": "a second object",
         "boresight": "the boresight: the cross that shows where the camera points",
         "north": "the north arrow, if the screen shows one",
         "reference": "a thing whose true size you know",
         "horizon": "the horizon: the line between sky and ground"}
_CLASS = Group("1..%d" % len(CLASSES), "choose what your clicks mark: " + ", ".join(CLASSES).replace("object2", "object #2"))
_NUDGE = Group("Ctrl+arrows", "move this mark by 1 pixel; a mark you move this way counts as placed by hand")
_FINE = Group("Ctrl+Shift+arrows", "move it by a tenth of a pixel")
_ARROWS = (("left", "Left", -1, 0), ("right", "Right", 1, 0), ("up", "Up", 0, -1), ("down", "Down", 0, 1))
NUDGES = {f"nudge_{name}{'_fine' if fine else ''}": (dx * (0.1 if fine else 1.0), dy * (0.1 if fine else 1.0))
          for fine in (False, True) for name, _, dx, dy in _ARROWS}

ACTIONS = [
    # what the command line does with an argument or a flag, for someone who has no command line
    Action("open_clip", "File", "Open a video…", ("Ctrl+O",), "open another video: choose the file, then the segment of it to open"),
    Action("open_id", "File", "Open by catalog name…", ("Ctrl+Shift+O",),
           "open a video by its short name in a catalog, such as PR113 or PR144. A catalog is a list of videos that "
           "says which file each name stands for"),
    Action("open_marks", "File", "Open marks…", (), "go on from marks you saved before: a file whose name ends in _marks.json"),
    Action("save", "File", "Save", ("S", "Ctrl+S"),
           "save your marks, the track, and a strip of small pictures that shows each mark on its frame, so you can check them",
           mpl=True, sep=True),
    Action("save_to", "File", "Save to a different folder…", ("Ctrl+Shift+S",),
           "choose the folder where everything for this video is saved, and save there"),
    Action("quit", "File", "Save and quit", ("Q", "Ctrl+Q"), "save and close the window", mpl=True, sep=True),

    Action("undo", "Edit", "Undo", ("Ctrl+Z",), "undo your last change to the marks"),
    Action("redo", "Edit", "Redo", ("Ctrl+Shift+Z", "Ctrl+Y"), "do again what you just undid"),
    Action("delete", "Edit", "Delete this mark", ("Backspace", "Delete"), "delete the mark of this kind on this frame",
           mpl=True, sep=True),
    *(Action(f"nudge_{name}{'_fine' if fine else ''}", "Edit>Move the mark a little",
             f"{name.capitalize()} {'0.1' if fine else '1'} pixel", (("Ctrl+Shift+" if fine else "Ctrl+") + key,),
             "", sep=fine and name == "left", group=_FINE if fine else _NUDGE)
      for fine in (False, True) for name, key, _, _ in _ARROWS),

    *(Action(f"class_{i + 1}", "Mark", c.replace("object2", "object #2"), (str(i + 1),), f"your clicks mark {_WHAT[c]}",
             mpl=True, check=True, group=_CLASS) for i, c in enumerate(CLASSES)),

    Action("fit", "View", "Fit the frame to the window", ("R",), "show the whole frame, as large as the window allows", mpl=True),
    Action("overview", "View", "Overview of the whole video", ("O",),
           "overview: small pictures from the whole video; click one to go there"),
    Action("candidates", "View", "Show spots the computer finds", ("C",),
           "put a ring on each small bright or dark spot the computer finds on this frame. The first time is slow: it "
           "first works out which parts of the picture never change", check=True, sep=True),
    Action("other_frames", "View", "Marks of this kind on the other frames", ("T",),
           "show or hide the marks of this kind that are on the other frames", check=True),

    Action("prev", "Go", "Back one frame", (",", "Left"), "go back one frame", mpl=True),
    Action("next", "Go", "On one frame", (".", "Right"), "go on one frame", mpl=True),
    Action("back10", "Go", "Back 10 frames", ("<", "Shift+Left"), "go back 10 frames", mpl=True),
    Action("on10", "Go", "On 10 frames", (">", "Shift+Right"), "go on 10 frames", mpl=True),
    Action("first", "Go", "First frame", ("Home",), "go to the first frame", mpl=True),
    Action("last", "Go", "Last frame", ("End",), "go to the last frame", mpl=True),
    Action("prev_marked", "Go", "Back to a marked frame", ("[",), "go back to the nearest frame that has a mark of this kind",
           sep=True),
    Action("next_marked", "Go", "On to a marked frame", ("]",), "go on to the nearest frame that has a mark of this kind"),
    Action("play", "Go", "Play or stop", ("Space",), "play the video at its true speed, or stop it", sep=True),
    Action("slower", "Go", "Slower", ("-",), "play slower"),
    Action("faster", "Go", "Faster", ("=", "+"), "play faster"),

    Action("find", "Track", "Find the object…", ("F",),
           "find: the computer looks for things that move against the background and lists them, the most likely first, "
           "each as a strip of small pictures cut from the video. If the object is on the list, choose it: marks are put "
           "along its path, saved as proposed and never as placed by hand, and linking starts. If it is not there, click "
           "the object yourself. The computer only offers; you say which thing is the object"),
    Action("link", "Track", "Link from the marks, or stop", ("L",),
           "link: the computer follows the object from your marks, forward and backward from each, and draws the track as "
           "it grows. Press again to stop. It chooses the size of spot to look for from your marks. Frames where forward "
           "and backward do not agree are shown in orange: look at those. If it loses the object, mark the object where "
           "you see it again and link again -- only the new frames are worked out"),

    Action("measure", "Measure", "Measure this video…", ("M",),
           "measure: run every measuring step on this video, with the track linked from your marks, and write one report "
           "-- what `mcdonald run` does. It shows you the track sheet first and asks if the track is on the object in "
           "every frame, because every number after that needs it to be"),
    Action("report", "Measure", "Show the report", ("Ctrl+R",),
           "the report for this video, once there is one: what was measured, what this video cannot tell us, and what "
           "would settle it"),
    Action("folder", "Measure", "Open the results folder", (),
           "open the folder where everything for this video is saved", sep=True),

    Action("first_run", "Help", "Getting started", (), "the job, step by step: find the object, click it twice, link, look, "
           "save, measure, read the report"),
    Action("keys", "Help", "Keys and mouse", ("F1",), "this list"),
    Action("desktop", "Help", "Add mcdonald to the applications menu", (),
           "add mcdonald to the applications menu, so that you can start it from the desktop with no command line (Linux "
           "only; `mcdonald-gui --desktop-entry` does the same)",
           sep=True),
]

GESTURES = [
    Gesture("click", "place a mark of the kind you chose", mpl=True),
    Gesture("shift+click", f"the same, but the mark goes on the nearest spot the computer found (within {SNAP_PX:g} pixels) "
                           "at the spot size shown. The mark is saved as snapped, and never counts as placed by hand"),
    Gesture("scroll", "zoom in or out around the mouse pointer", mpl=True),
    Gesture("middle-drag", "move the picture", mpl=True),
    Gesture("right-drag, ctrl+drag", "move the picture, for a mouse with no middle button"),
]

MPL_NOTE = ("The matplotlib window's toolbar can zoom and move the picture too. While one of its tools is on, clicks do "
            "not place marks.")

# Help -> Getting started: the job, in the order it is done, for someone who has only the window.
# A key is named by its row -- {link} -- so the page cannot come to say a key the menus do not.
FIRST_RUN = [
    ("Four words",
     "A video is a row of still pictures, called frames. A mark is a click that says: on this frame, the object is here. "
     "A track is the place of the object on every frame. To link is to let the computer follow the object from your "
     "marks, and so make a track."),
    ("Let the computer look first",
     "Press {find}. The computer looks for things that move against the background and lists them, the most likely "
     "first. Each is shown as a strip of small pictures cut from the video. If the object is on the list, press This is it "
     "next to it, and go on to Look at the strip, below. The computer only offers. Other things move too, such as "
     "numbers that slide across the screen. If the object is faint, is seen for only a moment, or is one of many "
     "moving things, it may not be on the list at all. Then find it yourself:"),
    ("Find when",
     "Open the overview ({overview}): small pictures from the whole video. Click the one where you see something, and "
     "the window goes there. {play} plays the video at its true speed. {prev} and {next} go back or on one frame. You "
     "can also drag the bar under the picture."),
    ("Find where",
     "Scroll to zoom in around the mouse pointer. The close-up at the top right shows the pixels under the pointer. If "
     "you cannot tell which spot is the object, {candidates} puts a ring on each spot the computer finds on this frame. "
     "The first time is slow, once for each video."),
    ("Two clicks",
     "Click the object. Go on a few frames and click it again. One mark says which thing it is. Two marks also give its "
     "speed and direction, which a fast object needs. This is the one thing the computer cannot do for you: it cannot "
     "know which thing in the picture is the object, and a person who looks can. {delete} takes a mark away, and {undo} "
     "undoes your last change."),
    ("Link",
     "Press {link}. The computer follows the object from your marks, forward and backward from each one, and draws the "
     "track as it grows. Frames where forward and backward do not agree are shown in orange: look at those. If it "
     "loses the object, mark the object where you see it again and link again. Only the new frames are worked out."),
    ("Look at the strip",
     "When linking ends, a strip of small pictures opens, one for each place on the track. Every picture should show "
     "the same thing. A track that sits on a bit of cloud for a few frames gives a clean but wrong speed, and only "
     "looking can catch that."),
    ("Save",
     "Press {save} to save the marks, the track, and a strip that shows every mark drawn on its frame. The strip is then "
     "shown to you. Until you have seen a mark drawn on the picture, you are trusting a number; you have not checked "
     "it. The window says which folder it saves to, at the bottom right."),
    ("Measure",
     "Press {measure} to measure the video: how the background moves, how the object moves against each part of the "
     "background, what that motion allows, and whether the object acts like part of the picture or like something "
     "laid over it. First you are shown the track sheet, one small picture for every frame, and asked if the circle is "
     "on the object in every one. Say no if you cannot tell. Fill in only what you know, such as how wide the camera "
     "sees or how far away the object was, and leave the rest empty."),
    ("Read the report",
     "The report opens when measuring ends, and {report} opens it again. Read the part called \"What this clip cannot "
     "decide\" before the last line of the report: a test that could not decide has not passed. The part called \"What "
     "would close it\" names what is missing."),
]


def first_run(key=str):
    """FIRST_RUN with each {row id} replaced by that row's key as the menus show it;
    `key` dresses a key for the page it is going onto."""
    keys = {a.id: key(spoken(a.keys[0]) if a.keys else f"{a.menu} -> {a.text}") for a in ACTIONS}
    return [(head, text.format(**keys)) for head, text in FIRST_RUN]


def for_window(window):
    """The rows a window has: 'qt' has them all, 'mpl' those marked."""
    return [a for a in ACTIONS if window == "qt" or a.mpl]


def mpl_key(key):
    """What matplotlib calls a key: 'Ctrl+S' is 'ctrl+s', 'Backspace' 'backspace'."""
    return key.lower()


def spoken(key):
    """A key as a person reads it: 'S' in a list of keys would be read as shift+s."""
    return key.lower()


def listing(window="qt"):
    """[(keys, help, the matplotlib window has it)], one entry per line of a key
    list: the mouse first, then the rows in menu order, a group once."""
    out, seen = [(g.keys, g.help, g.mpl) for g in GESTURES if window == "qt" or g.mpl], set()
    for a in for_window(window):
        if a.group is None:                          # a row with no key is found in its menu
            out.append(("  ".join(spoken(k) for k in a.keys) or f"{a.menu} menu", a.help, a.mpl))
        elif a.group not in seen:
            seen.add(a.group)
            out.append((spoken(a.group.keys), a.group.help, a.mpl))
    return out


def controls(width=100):
    """The key list as text, for `mcdonald mark --help`."""
    rows = listing("qt")
    pad = max(len(k) for k, _, _ in rows) + 2
    L = ["Keys and mouse (* the Qt window only)", ""]
    for keys, text, mpl in rows:
        body = textwrap.wrap(text, width - pad - 6, break_on_hyphens=False) or [""]
        L.append(f"  {' ' if mpl else '*'} {keys:<{pad}}{body[0]}")
        L += [" " * (pad + 4) + ln for ln in body[1:]]
    return "\n".join(L + ["", MPL_NOTE, ""])
