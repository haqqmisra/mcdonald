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

MENUS = ["File", "Edit", "Mark", "View", "Go", "Track", "Help"]


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


SNAP_PX = 12.0              # how far shift+click reaches for a candidate; the window's, and the help's

_CLASS = Group("1..%d" % len(CLASSES), "mark class: " + ", ".join(CLASSES).replace("object2", "object #2"))
_NUDGE = Group("Ctrl+arrows", "nudge this class's mark on this frame by 1 px; a nudged mark is a hand's again")
_FINE = Group("Ctrl+Shift+arrows", "nudge it by 0.1 px")
_ARROWS = (("left", "Left", -1, 0), ("right", "Right", 1, 0), ("up", "Up", 0, -1), ("down", "Down", 0, 1))
NUDGES = {f"nudge_{name}{'_fine' if fine else ''}": (dx * (0.1 if fine else 1.0), dy * (0.1 if fine else 1.0))
          for fine in (False, True) for name, _, dx, dy in _ARROWS}

ACTIONS = [
    # what the command line does with an argument or a flag, for someone who has no command line
    Action("open_clip", "File", "Open a clip…", ("Ctrl+O",), "open another clip: a video file, and which part of it"),
    Action("open_id", "File", "Open by catalog id…", ("Ctrl+Shift+O",),
           "open a clip by its record id (PR144, 06:PR001), where there is a catalog to look it up in"),
    Action("open_marks", "File", "Open marks…", (), "continue from a _marks.json saved earlier (--load)"),
    Action("save", "File", "Save", ("S", "Ctrl+S"), "save: the marks, the track CSV, and the contact strip to check them by",
           mpl=True, sep=True),
    Action("save_to", "File", "Save to a different folder…", ("Ctrl+Shift+S",),
           "choose the case directory, where everything for this clip is written (--out), and save there"),
    Action("quit", "File", "Save and quit", ("Q", "Ctrl+Q"), "save and quit", mpl=True, sep=True),

    Action("undo", "Edit", "Undo", ("Ctrl+Z",), "undo"),
    Action("redo", "Edit", "Redo", ("Ctrl+Shift+Z", "Ctrl+Y"), "redo"),
    Action("delete", "Edit", "Delete this mark", ("Backspace", "Delete"), "delete this class's mark on this frame",
           mpl=True, sep=True),
    *(Action(f"nudge_{name}{'_fine' if fine else ''}", "Edit>Nudge the mark",
             f"{name.capitalize()} {'0.1' if fine else '1'} px", (("Ctrl+Shift+" if fine else "Ctrl+") + key,),
             "", sep=fine and name == "left", group=_FINE if fine else _NUDGE)
      for fine in (False, True) for name, key, _, _ in _ARROWS),

    *(Action(f"class_{i + 1}", "Mark", c.replace("object2", "object #2"), (str(i + 1),), f"clicks mark the {c}",
             mpl=True, check=True, group=_CLASS) for i, c in enumerate(CLASSES)),

    Action("fit", "View", "Fit the frame to the window", ("R",), "fit the frame to the window", mpl=True),
    Action("overview", "View", "Overview of the whole clip", ("O",), "overview of the whole clip; click a tile to go there"),
    Action("candidates", "View", "Detector candidates", ("C",),
           "detector candidates on this frame (slow the first time: it builds the static masks)", check=True, sep=True),
    Action("other_frames", "View", "This class's marks on the other frames", ("T",),
           "show / hide the marks of this class on the other frames", check=True),

    Action("prev", "Go", "Previous frame", (",", "Left"), "previous frame", mpl=True),
    Action("next", "Go", "Next frame", (".", "Right"), "next frame", mpl=True),
    Action("back10", "Go", "Back 10 frames", ("<", "Shift+Left"), "back 10 frames", mpl=True),
    Action("on10", "Go", "On 10 frames", (">", "Shift+Right"), "on 10 frames", mpl=True),
    Action("first", "Go", "First frame", ("Home",), "first frame", mpl=True),
    Action("last", "Go", "Last frame", ("End",), "last frame", mpl=True),
    Action("prev_marked", "Go", "Previous marked frame", ("[",), "previous frame with a mark of this class", sep=True),
    Action("next_marked", "Go", "Next marked frame", ("]",), "next frame with a mark of this class"),
    Action("play", "Go", "Play / pause", ("Space",), "play / pause, at the clip's true speed", sep=True),
    Action("slower", "Go", "Slower", ("-",), "play slower"),
    Action("faster", "Go", "Faster", ("=", "+"), "play faster"),

    Action("link", "Track", "Link from the marks / stop", ("L",),
           "link: an automatic track through the marks of the object (and of object #2), forward and backward from "
           "each, drawn as it grows; again stops it. The detector's scale is chosen from the marks. Frames where the "
           "forward and backward links disagree are amber: look at those. After a loss, mark the object where it "
           "reappears and link again -- only new frames are computed"),

    Action("keys", "Help", "Keys and mouse", ("F1",), "this list"),
    Action("desktop", "Help", "Add mcdonald to the applications menu", (),
           "add mcdonald to the applications menu, so that it starts from the desktop with no terminal (Linux; "
           "`mcdonald-gui --desktop-entry` does the same)",
           sep=True),
]

GESTURES = [
    Gesture("click", "place a mark of the current class", mpl=True),
    Gesture("shift+click", f"the same, snapped to the detector's nearest candidate (within {SNAP_PX:g} px) at the scale "
                           "shown; the mark records that it was, and is never counted as a hand mark"),
    Gesture("scroll", "zoom about the cursor", mpl=True),
    Gesture("middle-drag", "pan", mpl=True),
    Gesture("right-drag, ctrl+drag", "pan, for a mouse with no middle button"),
]

MPL_NOTE = "The matplotlib window's toolbar zooms and pans too; while one of its tools is armed, clicks do not mark."


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
    L = ["Controls (* the Qt window only)", ""]
    for keys, text, mpl in rows:
        body = textwrap.wrap(text, width - pad - 6, break_on_hyphens=False) or [""]
        L.append(f"  {' ' if mpl else '*'} {keys:<{pad}}{body[0]}")
        L += [" " * (pad + 4) + ln for ln in body[1:]]
    return "\n".join(L + ["", MPL_NOTE, ""])
