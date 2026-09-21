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

    Action("measure", "Measure", "Measure this clip…", ("M",),
           "measure: every stage of a case on this clip, with the track linked from the marks, into one report -- what "
           "`mcdonald run` does. It makes the track sheet first and asks whether the track is on the object in every "
           "frame, because every number after it assumes so"),
    Action("report", "Measure", "Show the case report", ("Ctrl+R",),
           "the case report of this clip, once there is one: what was measured, what this clip cannot decide, and "
           "what would close it"),
    Action("folder", "Measure", "Open the case folder", (),
           "the folder everything for this clip is written to, in the file manager", sep=True),

    Action("first_run", "Help", "Getting started", (), "the job in the order it is done: find it, two clicks, link, look, "
           "save, measure, read the report"),
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

# Help -> Getting started: the job, in the order it is done, for someone who has only the window.
# A key is named by its row -- {link} -- so the page cannot come to say a key the menus do not.
FIRST_RUN = [
    ("Find when",
     "Open the overview ({overview}): the whole clip as tiles. Click the tile where something is, and the window goes "
     "there. {play} plays the clip at its true speed, {prev} and {next} step a frame, and the timeline under the frame "
     "can be dragged."),
    ("Find where",
     "Scroll to zoom about the cursor; the loupe shows the pixels under it. If you cannot tell which blob is the thing, "
     "{candidates} rings what the detector sees on this frame. It is slow the first time, once per clip."),
    ("Two clicks",
     "Click the object. Go on a few frames and click it again. One mark says which thing; two give its velocity, which "
     "a fast object needs. This is the one judgment the package cannot make for you: no detector can say which thing in "
     "the frame is the object, and someone looking can. {delete} removes a mark, {undo} undoes."),
    ("Link",
     "Press {link}: an automatic track is linked through your marks, forward and backward from each, and drawn as it "
     "grows. Frames "
     "where the two directions disagree are amber: look at those. If it loses the object, mark it where it reappears "
     "and link again -- only the new frames are computed."),
    ("Look at the strip",
     "When the link ends, a strip of the tracked positions opens by itself. Every tile should show the same thing. A "
     "track that sits on a cloud feature for a few frames gives a clean, wrong rate, and nothing but looking finds it."),
    ("Save",
     "Press {save} to save the marks, the track and a contact strip -- every mark drawn back onto the pixels -- and to be shown "
     "the strip. A mark you have not seen drawn back is a number you are trusting, not one you have verified. The "
     "window says which folder it saves to, at the bottom of the panel on the right."),
    ("Measure",
     "Press {measure} to make a case of the clip: how the background moves and the object against each layer of it, what the "
     "motion permits, whether the object behaves as imagery or as something laid over it. It shows you the track sheet "
     "first and asks whether the circle is on the object in every frame; say no if you cannot tell. Fill in only what "
     "you know -- a field of view, a range -- and leave the rest empty."),
    ("Read the report",
     "It opens when the measuring ends, and {report} opens it again. Read \"What this clip cannot decide\" before the "
     "bottom line: a test that could not decide has not passed. \"What would close it\" names what is missing."),
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
    L = ["Controls (* the Qt window only)", ""]
    for keys, text, mpl in rows:
        body = textwrap.wrap(text, width - pad - 6, break_on_hyphens=False) or [""]
        L.append(f"  {' ' if mpl else '*'} {keys:<{pad}}{body[0]}")
        L += [" " * (pad + 4) + ln for ln in body[1:]]
    return "\n".join(L + ["", MPL_NOTE, ""])
