"""What a person knows of a video that its pixels cannot say, asked in plain words: how wide the camera
sees, how far away the object is, a thing in the picture whose true size they know, the speeds a report
gave.

Jacob, 2026-10-09: "we need to prompt the user to ask if any additional quantities are known (FOV, object
of known reference size, range to object, etc.)". It is asked in two places, and never while the one
press runs: on the segment step, folded under "How many objects are you looking for?", where the one
press takes it from; and on the report card, when the report could not give a real speed -- there the
speed is worked out again in a second or two (`stages.add_known`), and nothing is measured again. Both
are this form. What it holds is remembered for each video and is what the Measure form's fields show (in
meters), so the one press, the queue of several objects and Measure all use it.

The values are `run_case`'s keywords, the rows of `stages.KNOWN` that change only the arithmetic of the
speed (`stages.AFTER`): a range and a length in meters, speeds as `run` reads them ("180kt"). The person
types in the unit they think in -- miles, feet, knots -- chosen beside each one and remembered.
"""
import json
import re
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from .mark_qt import MUTED, muted, settings

# a length's units, in meters; a speed's, as `run` reads them (kinematics.speed_of)
LENGTHS = {"miles": 1609.344, "nautical miles": 1852.0, "kilometers": 1000.0, "feet": 0.3048, "meters": 1.0}
SPEEDS = {"miles an hour": "mph", "knots": "kt", "kilometers an hour": "km/h", "meters a second": "m/s"}
READ_SPEED = re.compile(r"\s*([0-9]*\.?[0-9]+)\s*(m/s|mps|kt|kts|knots?|mph|km/h|kph|kmh)?\s*", re.I)
SPEED_WORD = {"m/s": "meters a second", "mps": "meters a second", "kt": "knots", "kts": "knots", "knot": "knots",
              "knots": "knots", "mph": "miles an hour", "km/h": "kilometers an hour", "kph": "kilometers an hour",
              "kmh": "kilometers an hour"}
# the names this form asks for, of stages.AFTER; the rest (the camera's angle marks, the range ratio, the object's
# length on the screen) are the Measure form's, in the trade's terms
ASKED = ("fov", "range_m", "ref_m", "ref_px", "ground_speed", "own_ship")


def remembered(clip_or_video):
    """What the person said they know of this video, last time: {name: value} of stages.AFTER, or {} (a test's
    drawn frames have no video)."""
    video = getattr(clip_or_video, "video", clip_or_video)
    if video is None:
        return {}
    try:
        got = json.loads(settings().value(f"known/{Path(str(video)).name}") or "{}")
    except (TypeError, ValueError):
        return {}
    from .stages import AFTER
    return {k: v for k, v in got.items() if k in AFTER and v is not None} if isinstance(got, dict) else {}


def remember(clip_or_video, values):
    """`values` over what is remembered for this video: a value of None takes one away. Returns the whole."""
    video = getattr(clip_or_video, "video", clip_or_video)
    now = remembered(video)
    for k, v in values.items():
        if v is None:
            now.pop(k, None)
        else:
            now[k] = v
    if video is not None:
        settings().setValue(f"known/{Path(str(video)).name}", json.dumps(now))
    return now


def number(v):
    """A number as a person would write it back: 5, 2.5, 8046.72."""
    return f"{v:.6g}"


def describe(known):
    """What was given, in the person's words and units, for a line on the report card: "the camera sees 2.5
    degrees across, the object is 5 miles away". Empty when nothing was."""
    unit = lambda key, default: settings().value(f"known_units/{key}") or default
    said = []
    if known.get("fov") is not None:
        said.append(f"the camera sees {number(known['fov'])} degrees across")
    if known.get("graticule") is not None:
        said.append(f"its angle marks are {number(known['graticule'])} pixels a degree apart")
    if known.get("range_m") is not None:
        u = unit("range", "miles")
        said.append(f"the object is {number(known['range_m'] / LENGTHS.get(u, 1.0))} {u if u in LENGTHS else 'meters'} away")
    if known.get("ref_m") is not None and known.get("ref_px") is not None:
        u = unit("ref", "feet")
        said.append(f"a thing {number(known['ref_m'] / LENGTHS.get(u, 1.0))} {u if u in LENGTHS else 'meters'} long is "
                    f"{number(known['ref_px'])} pixels on the screen"
                    + (f", the object {number(known['range_ratio'])} times as far away" if known.get("range_ratio") else ""))
    if known.get("size_px") is not None:
        said.append(f"the object is {number(known['size_px'])} pixels long on the screen")
    for key, what in (("ground_speed", "a report gave the object's speed as"), ("own_ship", "the aircraft flew at")):
        if known.get(key):
            m = READ_SPEED.fullmatch(str(known[key]))
            said.append(f"{what} {m.group(1)} {SPEED_WORD.get((m.group(2) or 'm/s').lower(), 'meters a second')}" if m
                        else f"{what} {known[key]}")
    return ", ".join(said)


class KnownForm(QtWidgets.QWidget):
    """The questions, in plain words, each box with its unit beside it: three lines that read as sentences on
    the segment step ("The camera sees [30] degrees from left to right"), and each question over its box in the
    right column (`narrow`). `values()` is what is typed as run_case's keywords (None for an empty box), or
    ValueError with a sentence to show; `set_values` fills it from them. `ruler(done)` is the host's way to
    measure a length on its picture of the video, `done(pixels)` at the end: the main window's ruler, or the
    segment step's own on its player."""
    changed = QtCore.Signal()

    # what each box holds, said under the pointer
    TIPS = {"fov": "how wide an angle the picture covers, from its left edge to its right, in degrees. A source, or the "
                   "camera's make and zoom, may give it. With how far away the object is, the report gives its speed and size",
            "range_m": "the distance from the camera to the object, if a source gives it. With how wide the camera sees, the "
                       "report gives the object's speed and its size",
            "ref_m": "the true length of a thing in the picture whose size you know, such as a ship or a building. With its "
                     "length on the screen, the report gives the object's speed if it is as far away as that thing",
            "ref_px": "that thing's length on the screen, in pixels: measure it on the video with the button",
            "ground_speed": "a speed a report gave for the object, measured along the ground below it. Used with the "
                            "aircraft's speed",
            "own_ship": "the speed of the aircraft that carried the camera. Used with a speed a report gave for the object"}

    def __init__(self, ruler=None, where="on the video", narrow=False, parent=None):
        super().__init__(parent)
        self._shown = {}                              # name -> (text, unit, value) as set: unchanged text gives back the value
        self.edits, self.units = {}, {}
        self.narrow = narrow                          # in the right column: each question over its box, not beside it
        for name, unit, key, default in (("fov", "degrees", None, None), ("range_m", LENGTHS, "range", "miles"),
                                         ("ref_m", {k: LENGTHS[k] for k in ("feet", "meters")}, "ref", "feet"),
                                         ("ref_px", "pixels", None, None), ("ground_speed", SPEEDS, "ground", "miles an hour"),
                                         ("own_ship", SPEEDS, "own", "knots")):
            self._box(name, unit, key, default)
        self.ruler = None
        if ruler is not None:
            self.ruler = QtWidgets.QPushButton("Measure " + where)
            self.ruler.setToolTip(f"drag along that thing {where}, from one end to the other: its length on the screen goes "
                                  "in the box beside it")
            self.ruler.setAutoDefault(False)
            self.ruler.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.ruler.clicked.connect(lambda _=False: ruler(self._ruled))
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        if narrow:                                    # on the card, the line over the form has just said why
            self._stacked(lay)
        else:
            lay.addWidget(muted("These turn the object's speed on the screen into a real speed. Leave empty what you don't know."))
            self._sentences(lay)
        lay.addWidget(muted("The two speeds are used together: the report then says how much of the object's speed could "
                            "be the aircraft's own motion."))

    # -- building ------------------------------------------------------------------------------
    def _box(self, name, unit, key=None, default=None):
        """Where one thing is typed, and its unit: a word, or a choice of them, remembered."""
        edit = QtWidgets.QLineEdit()
        edit.setToolTip(self.TIPS[name])
        edit.setFixedWidth(84)
        if name not in ("ground_speed", "own_ship"):  # a speed may be typed with its unit, as `run` takes it
            v = QtGui.QDoubleValidator(self)
            v.setBottom(0.0)
            v.setLocale(QtCore.QLocale.c())           # a point is a point: what the command line reads
            edit.setValidator(v)
        edit.textChanged.connect(lambda *_: self.changed.emit())
        self.edits[name] = edit
        if isinstance(unit, dict):
            box = QtWidgets.QComboBox()
            box.addItems(list(unit))
            box.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            box.setToolTip(self.TIPS[name])
            chosen = settings().value(f"known_units/{key}") or default
            box.setCurrentText(chosen if chosen in unit else default)
            box.currentTextChanged.connect(lambda text, key=key: settings().setValue(f"known_units/{key}", text))
            box.currentTextChanged.connect(lambda *_: self.changed.emit())
            self.units[name] = box
        else:
            box = QtWidgets.QLabel(unit)
            box.setStyleSheet(f"color: {MUTED};")
        edit.unit_widget = box

    def _row(self, *parts):
        """One line: words, boxes and their units, in reading order, and the rest of the line empty."""
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)
        for x in parts:
            if isinstance(x, str):
                row.addWidget(QtWidgets.QLabel(x))
            elif isinstance(x, int):
                row.addSpacing(x)
            elif x is not None:
                row.addWidget(x)
                if isinstance(x, QtWidgets.QLineEdit):
                    row.addWidget(x.unit_widget)
        row.addStretch(1)
        return row

    def _sentences(self, lay):
        """On the segment step, wide: three lines that read as sentences, so the player keeps its room."""
        e = self.edits
        for parts in (("The camera sees", e["fov"], "from left to right.", 28, "The object is", e["range_m"], "away."),
                      ("Something in the picture is", e["ref_m"], "long, and", e["ref_px"], "on the screen.", self.ruler),
                      ("A report gave the object's speed as", e["ground_speed"], 28, "and the aircraft's as", e["own_ship"])):
            lay.addLayout(self._row(*parts))

    def _stacked(self, lay):
        """In the right column, narrow: each question over its box."""
        e = self.edits
        for text, name in (("How wide the camera sees, left to right", "fov"), ("How far away the object is", "range_m"),
                           ("How long something in the picture really is", "ref_m"), ("and how long it is on the screen", "ref_px"),
                           ("The object's speed, if a report gave it", "ground_speed"), ("and the aircraft's speed", "own_ship")):
            q = QtWidgets.QLabel(text)
            q.setWordWrap(True)
            q.setToolTip(self.TIPS[name])
            lay.addWidget(q)
            lay.addLayout(self._row(e[name]))
            if name == "ref_px" and self.ruler is not None:
                lay.addLayout(self._row(self.ruler))

    def _ruled(self, px):
        self.edits["ref_px"].setText(f"{px:.1f}")
        self.edits["ref_px"].setFocus()

    # -- what it holds -------------------------------------------------------------------------
    def given(self):
        """How many of its rows have something typed in them."""
        return sum(1 for e in self.edits.values() if e.text().strip())

    def set_values(self, known):
        """Show `known` (run_case's keywords, in meters and as `run` reads speeds) in the units chosen."""
        self._shown = {}
        for name, edit in self.edits.items():
            v, box = known.get(name), self.units.get(name)
            text = ""
            if v is not None and name in ("ground_speed", "own_ship"):
                m = READ_SPEED.fullmatch(str(v))
                if m and box is not None:
                    box.blockSignals(True)
                    box.setCurrentText(SPEED_WORD.get((m.group(2) or "m/s").lower(), "meters a second"))
                    box.blockSignals(False)
                    text = m.group(1)
                else:
                    text = str(v)                     # typed with more in it (a heading, a height): kept as it is
            elif v is not None:
                text = number(float(v) / LENGTHS[box.currentText()]) if box is not None else number(float(v))
            edit.blockSignals(True)
            edit.setText(text)
            edit.blockSignals(False)
            self._shown[name] = (text, box.currentText() if box is not None else None, v)
        self.changed.emit()

    def values(self):
        """{name: value or None} of every row, as run_case takes them. ValueError, with a sentence for the
        person, for something that cannot be read or does not go alone."""
        from . import kinematics as kin
        out = {}
        for name, edit in self.edits.items():
            text, box = edit.text().strip(), self.units.get(name)
            unit = box.currentText() if box is not None else None
            if not text:
                out[name] = None
                continue
            was = self._shown.get(name)
            if was and was[0] == text and was[1] == unit and was[2] is not None:
                out[name] = was[2]                    # as it was given, not as it was rounded for the screen
                continue
            if name in ("ground_speed", "own_ship"):
                if re.fullmatch(r"[0-9]*\.?[0-9]+", text):
                    text = f"{text}{SPEEDS[unit]}"
                try:
                    kin.speed_of(text.split(",")[0])
                except ValueError:
                    raise ValueError(f"“{edit.text().strip()}” is not a speed: type a number, and choose its unit beside it.") from None
                out[name] = text
                continue
            try:
                v = float(text)
            except ValueError:
                raise ValueError(f"“{text}” is not a number.") from None
            if v <= 0:
                raise ValueError("Each of these is more than 0. Leave it empty if you don't know it.")
            if name == "fov" and v >= 180:
                raise ValueError("How wide the camera sees is an angle under 180 degrees.")
            out[name] = v * LENGTHS[unit] if box is not None else v
        if (out["ref_m"] is None) != (out["ref_px"] is None):
            raise ValueError("For the thing of known size, give both: how long it really is, and how long it is on the screen.")
        return out
