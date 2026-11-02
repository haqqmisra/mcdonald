"""The standard case report: one clip, every stage, in a fixed shape.

The shape is not arbitrary. It is the structure the hand-written workups
converged on over two dozen clips, and each section earns its place:

    Conclusion         the one sentence a reader takes away, and how firm it is -- tentative,
                       or none -- then the checklist: each test as a question in plain words with
                       its answer in a word (Yes, No, Partly, Can't tell, Not yet) and why in a
                       line; and, folded under it, what can be said in one paragraph, with the bounds
    What the clip is   container, cadence, geometry, provenance if any
    The four unknowns  k, R, theta and v_own: constrained, assumed, bounded or missing, by which route, and
                       the released datum that would close each (ROADMAP 0.4, objective 6)
    Measurements       per stage, with the inputs each one needed
    What has no power  the tests this clip cannot decide -- never dropped
    What would close it  the specific missing quantity, named
    Reproduce          the exact commands

"What has no power" and "What would close it" are the two sections that make
the rest trustworthy. A report that lists only what it found reads as a
result; the same report with its blind spots named reads as a measurement.
Most clips in this subject deserve the second.

A `Case` accumulates stage results as they are produced, so a partial run
still writes a coherent report saying which stages ran.
"""
import contextlib
import io
import json
import math
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from . import __version__
from .kinematics import A_SOUND, aspect_from_tau, backtest_short, bound_said, path_said, pm
from .projective import TILT_OWN, TILT_STRAIGHTER, depth_said, held_to, lens_could, lens_said, pct, swings_said, trend_px


STOPPED_BEFORE = "stopped before "     # a note, then the step that never started: stages.run_case writes it, stopped_in() reads it
# A brightness beat in this band is the rate of a wingbeat -- gulls and crows near 3 Hz, pigeons near 8, small birds
# to the low twenties -- and the conclusion then names a bird as the leading explanation (Jacob, Galileo flyer 2,
# 2026-10-07). Below it a blinking light (an aircraft's strobe, about once a second) beats; above it nothing a camera
# at 60 frames a second resolves. The alternatives are named with it: the flicker stage cannot tell them apart.
WINGBEAT_HZ = (2.0, 25.0)
BIRD = "Beats like a bird"             # the conclusion's label for a beat in that band (Jacob, 2026-10-12): the window draws a bird by it
# ... and a bird is named only from a beat at least this share of the object's brightness. Fixed before the test that
# judges it (2026-10-24, Jacob: "go ahead"): on the Svanstrom labelled infrared set (2026-10-19) the calls on birds beat at
# a median 15-18 % and the false calls on aircraft, drones and helicopters at 1.8-2.3 %; 8 %, chosen on the birds and
# airplanes, kept 28-29 of 30-34 bird calls and left 2 of 307 other tracks called; it is held to a set it was not
# chosen on in uap analysis/sweeps/svanstrom/README.md ("The aperture study"). A fainter beat is still said, as one.
BIRD_FLOOR = 0.08
# A thing of known size in the picture gives the speed across the line of sight at that thing's distance: no faster
# where the object is no farther away. Under the speed of sound, that bound is the finding (JAIS Technical Note, PR149:
# "supersonic relative velocities can be excluded"; Jacob, 2026-10-22, exercise 2): the window draws sound's wavefronts by it
SUBSONIC = "Subsonic motion"
# A field of view (or angle marks) turns pixels into angles, and nothing gives the distance: the size and the speed both
# follow from a distance, so the headline says where a bird, a weather balloon and a fighter jet would be (Jacob,
# 2026-10-22, exercise 3: "This gives a sense of what is learned by obtaining FOV")
INDETERMINATE = "Indeterminate, range needed"
# A field of view and a distance give omega R, the speed across the line of sight: the least the speed relative to the
# platform can be. Past the speed of sound that settles it; under it, the motion toward or away from the camera could
# still take it past, until an angle or a range rate is given (Jacob, 2026-10-22, agreed: "those look good to me")
SUPERSONIC = "Supersonic motion"
ANGLE_NEEDED = "Indeterminate, angle needed"
FLAMES = ("sky lantern", "candle flames")   # flicker's bands for a flame (item 11, 2026-10-20): per object, its own phase -- a
                                            # look-alike the members being out of step does not clear, so the bottom line says so
# The four unknowns of the velocity equation (JAIS Technical Note: omega = v_px f / k, omega R = |v_obj - v_own| sin theta),
# and for each the datum a release could give that would close it (ROADMAP 0.4, objective 6: the Note's census of what
# the released videos withhold, made a table of every case, which 1.0 sums over the corpus)
LEDGER_CLOSES = {
    "k": "the sensor's field of view at this zoom -- printed on the display, or the footprint's width with the slant "
         "range on a data bar (FVW / SLR)",
    "R": "the slant range to the object (a laser range, a data bar's SLR with the object at the cross), or its position "
         "from a second sensor",
    "θ": "the object's direction of motion, or its range at two times (a range rate)",
    "v_own": "the platform's ground speed and track, from a data bar or the flight's log",
}

def own_beats(ff):
    """{name: beat} of the flicker stage's fields: the beats that are the object's (or members') own -- none
    unless the stage found a beat, and of a group's members only those whose beat passed the tests
    (`strong`, since 2026-10-09; a case from before has every member's)."""
    if not ff.get("beats"):
        return {}
    strong = ff.get("strong")
    return {n: b for n, b in (ff.get("beat") or {}).items() if strong is None or n in strong}


def bird_beats(ff):
    """{name: beat} of the flicker stage's fields: the beats that would name a bird, by the rule `Case.conclusion` keeps -- a
    beat of its own that comes back, at a wingbeat's rate, at BIRD_FLOOR of the brightness or more. What the sensor's shake
    may make is not asked here: this is what `run` reads the shake for (flicker's item 17)."""
    return {n: b for n, b in own_beats(ff).items() if b.get("comes_back", True) and WINGBEAT_HZ[0] <= b["hz"] <= WINGBEAT_HZ[1]
            and (b.get("amplitude") is None or b["amplitude"] >= BIRD_FLOOR)}


# numbers for the sentences that place a bird, a balloon and a jet: their sizes are a kind's, so two figures say all
# they can ("1.5 km", "3,500 m/s"); and the kind an object is near in size, by the same sizes (`figures.BIRDS`, `OBJECTS`)
def _two(x):
    return float(f"{x:.2g}")


# the fan's one-sidedness given a number, under a stated measure (the pure-mathematics survey's M2, its section 3.2): for
# a direction drawn isotropically cos theta is uniform, so the speed over the speed across the line of sight, 1 / sin
# theta, is more than m with probability 1 - sqrt(1 - 1 / m^2)
ISOTROPIC = ("With its direction drawn isotropically (nothing favouring one), the speed is within 15 % of this half the "
             "time, more than twice it one time in 7.5 and more than ten times it one time in 200")


# what `Case.extent` calls the size a track was followed at: a scale for finding a thing (on a track given with no size, the
# default), not a width measured. Good enough for "about"; a limit is not to be built on it (PR051's drift, `run --track`
# with no size: 9 px, where the thing is 53 wide at half its peak, gave "at most 0.36 m", five times too small).
SPOT_SIZE = "the spot size the track was followed at"

# The checklist under the conclusion (Ravi Kopparapu, 2026-11-01: a report "that even an undergraduate student can
# understand"; Jacob: "a checklist form that lists off each test, in a nicely formatted table, with a simple answer of the
# test result"): each test as a question in plain words, and its answer in one of five words. "Can't tell" is a verdict
# (the package's third rule: a test that cannot decide has not passed), never dropped for a "No".
YES, NO, PARTLY, CANT, NOT_YET = "Yes", "No", "Partly", "Can't tell", "Not yet"
ANSWERS = (YES, NO, PARTLY, CANT, NOT_YET)
CHECKS = {
    "video": "Does the video have repeated frames or sudden changes of brightness?",
    "camera": "Did the camera move while it filmed this?",
    "moves": "Does the object move against the background?",
    "straight": "Does it move in a straight line at a steady speed across the picture?",
    "closing": "Is it coming toward the camera, or going away?",
    "beat": "Does its brightness beat, as a bird's wingbeat would?",
    "lookalike": "Could something other than a bird beat like this?",
    "flash": "Does it flash in a regular train, like an aircraft's light?",
    "single": "Is it a single thing?",
    "with": "Does anything move along with it (a line, a load, a companion)?",
    "through": "Does it move through what is around it, rather than drift with it?",
    "added": "Does it look like something added to the video afterwards?",
    "real": "Can its real speed and size be worked out?",
    "chosen": "Did a person pick out the object by eye?",
    "checked": "Has a person checked that the track stays on the object in every frame?",
}


def plainer(text):
    """A stage's own words with the trade's units and names made plain, for a checklist row's line."""
    for pat, to in ((r"\bclips?\b", "video"), (r"\bpx/s\b", "pixels a second"), (r"\bpx\b", "pixels"), (r"\bfps\b", "frames a second")):
        text = re.sub(pat, to, text)
    return text


def _far(m, two=True):
    r = _two if two else (lambda x: float(f"{x:.3g}"))            # a distance given: three figures of it
    return f"{r(m / 1000):g} km" if m >= 1000 else f"{r(m):g} m"


def _span(a, b):
    return f"{_two(a):g}–{_two(b):g} m" if b < 1000 else f"{_far(a)}–{_far(b)}"


def _num(v):
    return f"{_two(v):,.0f}"


def _deg(rad):
    """A turn rate in the picture as degrees a second: whole degrees from 1° up, two figures under it, so that an
    object the camera held does not "move about 0° a second" (IMG_5611's 0.09°, 2026-11-01)."""
    d = math.degrees(rad)
    return f"{d:.0f}°" if d >= 1 else f"{_two(d):g}°"


def _kinds():
    """Every kind an object is held against, (name, smallest, largest) in order of size: the bird's band, the bands
    (`figures.BANDS`) and the things of one size (`figures.OBJECTS`)."""
    from .figures import BANDS, BIRDS, OBJECTS
    return sorted([("bird", *BIRDS)] + list(BANDS) + [(n, s, s) for n, s in OBJECTS], key=lambda k: (k[1], k[2]))


def _like(size):
    """"about a fighter jet's size", "about a bird's or a weather balloon's size", "smaller than a bird": a kind is
    near where the size is in a bird's band, within a band by a quarter either way, or within 2.5 times a thing's."""
    from .figures import BANDS, BIRDS, OBJECTS
    kinds = ((["a bird's"] if BIRDS[0] <= size <= BIRDS[1] else [])
             + [" or ".join(f"a {w}'s" for w in n.split(" or ")) for n, lo, hi in BANDS if lo / 1.25 <= size <= hi * 1.25]
             + [f"a {n}'s" for n, s in OBJECTS if s / 2.5 <= size <= s * 2.5])
    if kinds:
        return f"about {' or '.join(kinds)} size"
    biggest = max(OBJECTS, key=lambda o: o[1])
    return ("smaller than a bird" if size < BIRDS[0] else f"larger than a {biggest[0]}" if size > biggest[1] * 2.5 else
            "between a " + " and a ".join(n for n, _ in OBJECTS) + " in size")


def clock(seconds):
    """A time in the video as the window's segment step shows it (`mark_qt.clock`): 0:30.00."""
    return f"{int(seconds // 60)}:{seconds % 60:05.2f}"


def written_again(report_md):
    """The report at `report_md` written again from its case file where this version words it otherwise, so that
    the report's page says what the card (read from the case file by this version) says. A tester, 2026-10-18: the
    cards said "A bird is the leading explanation" and the report "doesn't say bird at all" -- most likely a report
    written by a version before 0.2.14, which named no bird, beside cards that read its beat by a later one's rules
    (on 0.2.20 the same segment measured again finds no beat at all). Nothing is measured: `mcdonald report
    CASE.json` does the same. True where the file was written."""
    md = Path(report_md)
    try:
        now = Case.load(md.with_name(md.name[:-len("_case.md")] + "_case.json")).markdown()
        if md.read_text(encoding="utf-8") == now:
            return False
        md.write_text(now, encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return True


def _ffmpeg_version():
    try:
        out = subprocess.run(["ffmpeg", "-version"], capture_output=True, encoding="utf-8", errors="replace").stdout
        return out.splitlines()[0].strip()
    except Exception:
        return "unknown"


def clip_block(clip):
    """The clip, as every envelope and every case gives it: its size, its exact rate, the frames
    worked on, and how it was encoded (`clip.encoding`, with the GOP)."""
    from .clip import encoding
    return dict(width=clip.W, height=clip.H, fps=float(clip.fps), fps_exact=str(clip.info["fps"]),
                fps_note=clip.info.get("fps_note"), n0=clip.n0, n1=clip.n1,
                duration_s=float(clip.info.get("duration") or 0),
                encoding=encoding(str(clip.video), float(clip.fps)) if getattr(clip, "video", None) else None)


def envelope(command, inputs, clip=None, files=(), results=None, no_power=(), needs=(), notes=(), exit_code=0,
             error=None):
    """What `--json` prints, the same shape from every command, so that something
    driving the package reads one structure and not six kinds of prose.

    It is a Case's stage, opened out: what went in, which files were written, what was
    found, and the two lists that make a result a measurement -- what this clip cannot
    decide (`no_power`, as [test, why] pairs, never dropped) and what would close the gap
    (`needs`). `exit` is the process's exit code and `error` the sentence that went with
    it; clip.EXIT_CODES says what the codes mean."""
    c = None if clip is None else dict(video=str(clip.video), **clip_block(clip))
    return dict(command=command, mcdonald=__version__, inputs=inputs, clip=c, files=[str(f) for f in files if f],
                results=results or {}, no_power=[list(x) for x in no_power], needs=list(needs), notes=list(notes),
                exit=exit_code, error=error)


def emit(env):
    """The envelope, alone on stdout. With --json everything said to a person goes to stderr."""
    print(json.dumps(env, indent=1, default=plain))


def inputs_of(args):
    """A command's parsed options as the envelope's `inputs`: what was given, not every default left unset."""
    return {k: v for k, v in vars(args).items() if v not in (None, False) and k != "json"}


@contextlib.contextmanager
def said_to_stderr(on=True):
    """With --json, stdout is for the envelope alone: what the command says to a person
    goes to stderr instead, and is kept, line by line, to go into the envelope as `said`.
    The list this yields is filled when the block ends. With `on` false it does nothing."""
    lines = []
    if not on:
        yield lines
        return

    class Tee(io.TextIOBase):
        def write(self, text):
            sys.stderr.write(text)
            kept.append(text)
            return len(text)

        def flush(self):
            sys.stderr.flush()

    kept = []
    try:
        with contextlib.redirect_stdout(Tee()):
            yield lines
    finally:
        lines[:] = [ln for ln in "".join(kept).splitlines() if ln.strip()]


def plain(v):
    """numpy's numbers and arrays as JSON's; anything else as its string."""
    return v.tolist() if hasattr(v, "tolist") else str(v)


def _double_said(hz, dbl):
    """flicker's words for a beat's double ("its double", or folded through the frame rate), imported where used:
    flicker imports this module."""
    from .flicker import double_said
    return double_said(hz, dbl)


class Found:
    """What one stage found. Every stage function returns one, and nothing in it knows
    who asked: `mcdonald run`, the stage's own command and a window all read the same
    object, so a number cannot differ between them.

        fields    the findings as numbers and plain values, units in the names
                  (`v_px_per_s`). What --json prints and what a test should read.
        result    label -> the line the case report prints. Made from the same
                  values as `fields`, formatted for a reader.
        no_power  [(test, why)]: what this clip cannot decide -- never dropped
        needs     what would close the gap, each a named missing quantity
        files     what the stage wrote
        notes     sentences for the report's "What the clip is"
        carry     what the next stage is handed that is not a finding: a track,
                  an AngularScale, a fit. Never serialised.
    """

    def __init__(self, stage, result=None, fields=None, no_power=(), needs=(), files=(), notes=(), carry=None):
        self.stage = stage
        self.result = dict(result or {})
        self.fields = dict(fields or {})
        self.no_power = [tuple(x) for x in no_power]
        self.needs = list(needs)
        self.files = [str(f) for f in files if f]
        self.notes = list(notes)
        self.carry = carry

    def into(self, case, command=None):
        """Record it as a stage of a case."""
        case.add(self.stage, self.result, command=command, no_power=self.no_power, needs=self.needs,
                 fields=self.fields, files=self.files)
        for n in self.notes:
            case.note(n)
        return self

    def envelope(self, command, inputs, clip=None, said=(), exit_code=0, error=None):
        """The stage's own command's --json: the fields are the results. `said` is what
        the command printed for a person, kept beside them as lines."""
        results = dict(self.fields)
        if said:
            results["said"] = list(said)
        return envelope(command, inputs, clip, self.files, results, self.no_power, self.needs, self.notes,
                        exit_code, error)


class Case:
    """One clip's results, accumulated stage by stage."""

    def __init__(self, tag, video, clip=None, record=None):
        self.tag = tag
        self.video = str(video)
        self.record = record
        self.clip = None if clip is None else clip_block(clip)
        self.segment = None                  # [first, last] frame of the segment the person chose; the clip may be fewer of them
        self.measured_by = __version__       # the version whose stages found what is in it: kept when the case is written again
        self.stages = {}
        self.commands = []
        self.notes = []
        self.identified_by = None            # set when the marks the track came from were not all a hand's
        self.figures = []                    # the summary's two pictures, beside the report
        self.started = datetime.now(timezone.utc).isoformat(timespec="seconds")

    @classmethod
    def load(cls, path):
        """A case read back from the `_case.json` that `write` left, as it was: its stages (results, fields,
        what had no power, what is needed, files), notes, commands and who decided which thing is the
        object. So a case can be amended -- a track sheet looked at afterwards (`stages.confirm_sheet`) --
        and its report written again without measuring anything."""
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        case = cls(d["tag"], d["video"], record=d.get("record"))
        case.clip, case.segment = d.get("clip"), d.get("segment")
        case.measured_by = d.get("measured_by") or d.get("mcdonald")      # a case from before it was kept: the version that wrote it
        case.stages = {n: dict(result=st.get("result") or {}, no_power=[tuple(x) for x in st.get("no_power") or []],
                               needs=list(st.get("needs") or []), fields=dict(st.get("fields") or {}),
                               files=list(st.get("files") or []))
                       for n, st in d.get("stages", {}).items()}
        case.commands, case.notes = list(d.get("commands") or []), list(d.get("notes") or [])
        case.identified_by = d.get("identified_by")
        case.figures = list(d.get("figures") or [])
        if case.identified_by:                          # JSON keeps a dict's keys as strings; the frames are numbers
            case.identified_by["not_by_hand"] = {int(n): h for n, h in case.identified_by.get("not_by_hand", {}).items()}
        case.started = d.get("started", case.started)
        return case

    def add(self, stage, result=None, command=None, no_power=None, needs=None, fields=None, files=None):
        """Record one stage. no_power is a list of (test, why) this clip
        cannot decide; needs is what would close the gap. `result` is what the
        report prints, `fields` the same findings as numbers (see Found)."""
        self.stages[stage] = dict(result=result or {}, no_power=list(no_power or []),
                                  needs=list(needs or []), fields=dict(fields or {}),
                                  files=list(files or []))
        if command:
            self.commands.append(command)
        return self

    def note(self, text):
        self.notes.append(text)
        return self

    def identified(self, not_by_hand, n_marks):
        """Record that which thing is the object was not (only) a person's judgment.
        `not_by_hand` is {frame: MarkSet.how}. The package's founding claim is that no
        detector can say which thing is the object and a person looking can; a report built
        on marks an agent placed, or marks snapped to the detector, says so on its face,
        above the bottom line, because every number below it inherits that judgment."""
        if not_by_hand:
            self.identified_by = dict(marks=n_marks, not_by_hand={int(n): h for n, h in not_by_hand.items()})
        return self

    def _identified(self):
        d = self.identified_by
        if not d:
            return []
        hows = d["not_by_hand"]
        agents = [n for n, h in hows.items() if h.startswith("agent:")]
        proposed = [n for n, h in hows.items() if h.startswith("proposed")]
        typed = [n for n, h in hows.items() if h.startswith("typed:")]
        who = ("an agent, not by a person looking at the frames" if len(agents) == len(hows) else
               "a person, who typed the positions as numbers read off a picture rather than placing them by hand on "
               "the frames" if len(typed) == len(hows) else
               "the detector's proposal, which a person looking at its strip accepted: the suggestion and the positions "
               "are the detector's, the yes was theirs" if len(proposed) == len(hows) else
               "the detector (snapped marks), not by a hand" if not agents and not proposed else
               "an agent or the detector, not by a hand")
        reasons = sorted({h for h in hows.values() if h.startswith("agent:")})
        L = [f"> **Which thing is the object was decided by {who}.** The track was linked from {d['marks']} "
             f"mark{'s' if d['marks'] != 1 else ''}, of which {len(hows)} {'were' if len(hows) != 1 else 'was'} not placed by hand. "
             "Every object measurement below inherits that identification, and no test here checks it: "
             "look at the track strip and the contact strip before quoting any of them."
             + (" The agent's reason: " + "; ".join(f"“{r[len('agent:'):].strip()}”" for r in reasons) + "." if reasons else "")]
        return L + [""]

    def _marks_detail(self):
        """The frame-by-frame record of the marks that were not a hand's: kept, but folded, near the end.
        `<details>` folds it on a page that knows it (GitHub; the window's report page)."""
        d = self.identified_by
        if not d:
            return []
        hows = d["not_by_hand"]
        return ["## Where the marks came from", "",
                f"<details><summary>Frame by frame: {len(hows)} mark{'s' if len(hows) != 1 else ''} not placed by hand</summary>",
                ""] + self._identified() + [f"- frame {n}: {h}" for n, h in sorted(hows.items())] + ["", "</details>", ""]

    # ---- the summary: the Technical Note's variables ----------------------------------
    def summary(self):
        """The variables of the velocity equation (JAIS Technical Note, Eqs. 1-6), most often known first:
        [(name, symbol, value or None, how)]. v_px from the track; FOV, k and omega from a graticule or an
        assumed field of view; p, the image extent; then what a source has to give (R, theta or Rdot, v_own)
        and what follows from them. A value of None is not available from this clip, and `how` says what
        would give it."""
        st = lambda name: self.stages.get(name, {}).get("fields") or {}
        kf, sf, tf = st("kinematics"), st("scale"), st("track")
        c = self.clip or {}
        fps = kf.get("fps") or c.get("fps")
        W = c.get("width")
        v = kf.get("v_px_per_s")
        k = sf.get("k_px_per_rad")
        om = kf.get("omega_rad_per_s")
        R, th, rdot = kf.get("range_m"), kf.get("theta_deg"), kf.get("range_rate_m_per_s")
        par = kf.get("parallax") or {}
        v_own = par.get("v_own")
        res = kf.get("resolution") or {}
        fit = kf.get("fit") or {}
        def needs(**have):
            gone = [n for n, v in have.items() if v is None]
            return "needs " + (", ".join(gone[:-1]) + " and " + gone[-1] if len(gone) > 1 else gone[0]) if gone else ""
        rows = []
        band = kf.get("band") or {}
        if v is not None and fps:
            how = f"fitted to {fit.get('n', '?')} points of the track against wall-clock time"
            if band and not band["constant"]:
                how += (f"; the speed band (the track's own covariance, section 32) says the speed ran from {band['v_min'][1]:.0f} "
                        f"to {band['v_max'][1]:.0f} px/s along the track: {path_said(band)}"
                        + ("" if kf.get("uniform", True) else ": **the motion is not uniform, so this line's rate is neither, and not a rate it held**"))
            elif band:
                how += (f"; constant within its band, ±{band['band_err_px_per_s']:.0f} px/s (the track's own covariance, section 32)"
                        + (f": {bound_said(band['change_bound'])}" if band.get("change_bound") else ""))
            if band.get("backtest"):
                how += f"; held to its own track, the band is {backtest_short(band['backtest'])}"
            elif not kf.get("uniform", True):
                how += "; **the motion is not uniform, so this does not describe it**"
            value = f"{v / fps:.1f} px/frame ({v:.0f} px/s)"
            if band and (kf.get("uniform", True) or band["constant"]):
                value = f"{v / fps:.1f} px/frame ({pm(v, band['v_mean_err_px_per_s'])} px/s)"
            rows.append(("pixel velocity", "v_px", value, how))
        elif self.stopped_in() and "kinematics" not in self.stages and tf:
            rows.append(("pixel velocity", "v_px", None, f"not measured: the measuring was stopped {self.stopped_in()}. "
                                                         "Measure again to get it"))
        else:
            rows.append(("pixel velocity", "v_px", None, "needs a track of the object"))
        lf = st("layers")
        names, per = lf.get("names") or {}, lf.get("px_per_s") or {}
        for part in ("striated", "isotropic"):             # against each layer of the background (the layers check)
            got = per.get(part) if lf.get("tracked") else None
            label = names.get(part, part)
            rows.append((f"pixel velocity against the {part} background" + (f" ({label})" if label != part else ""), f"v_px,{part}",
                         None if not got or not fps else f"{got['median'] / fps:.1f} px/frame ({got['median']:.0f} px/s)",
                         "median of one-second fits against that layer" if got else
                         ("the layers check was not run (Measure → Slow checks)" if "layers" not in self.stages else
                          f"no {part} background measured along the track")))
        # on a stretched picture (section 40) the field is given both ways, k up the picture and across, the stretch itself
        # with where it was read, and the extent in square pixels, between p / a and p; on square pixels nothing here changes
        fov, fov_v, a = sf.get("fov_deg"), sf.get("fov_v_deg"), sf.get("pixel_aspect") or 1.0
        deg = lambda f: f"{f:.1f}°" if f >= 1 else f"{f:.2g}°"
        rows.append(("horizontal field of view", "FOV", None if fov is None else deg(fov) + (f" by {deg(fov_v)} up" if fov_v else ""),
                     sf.get("fov_from") or "not in the video: needs a graticule reading or a sourced field of view"))
        rows.append(("angular scale", "k", None if k is None else f"{k:.0f} px/rad ({k * math.pi / 180:.1f} px/deg"
                     + (f" up the picture, {sf['k_x_px_per_rad'] * math.pi / 180:.1f} across" if sf.get("k_x_px_per_rad") else "") + ")",
                     sf.get("k_from") or "needs a graticule, a reference object of known size, or a field of view"))
        if a != 1.0:
            rows.append(("pixel aspect", "a", f"{a:.4g} wide to tall",
                         f"{sf.get('pixel_aspect_from') or 'given'}: the picture's pixels are drawn {a:.4g} times wider than tall, so k is "
                         "read up the picture and the rate is turned into square pixels along the track before it becomes an angle"))
        if sf.get("lens"):
            rows.append(("the lens's radial term", "k1", f"{sf['lens']['k1']:g}",
                         f"given: x_d = x_u (1 + k1 r²), r in units of the focal length ({sf['lens']['f_px']:.0f} px/rad at the axis)"))
        rows.append(("angular rate", "ω = v_px f / k", None if om is None else f"{om:.2f} rad/s ({math.degrees(om):.0f}°/s)" if om >= 0.01
                     else f"{om:.2g} rad/s ({math.degrees(om):.2g}°/s)",
                     ("from v_px, f and k" if a == 1.0 else
                      f"from v_px in square pixels along the track ({kf.get('v_square_px_per_s') or 0:.0f} px/s), f and k") if om is not None
                     else "needs k"))
        p, p_how = self.extent()
        rows.append(("image extent", "p", None if p is None else f"{p:.0f} px" + (f" ({p / a:.0f}–{p:.0f} square px)" if a != 1.0 else ""), p_how))
        R_ratio, R_by, _ = self.ranged() if R is None else (None, None, False)
        R_max = None if R is not None or R_ratio is not None else kf.get("range_max_m")    # a limit, where nothing gives a value
        rows.append(("range", "R", f"{R:,.0f} m" if R is not None else f"{R_ratio:,.0f} m" if R_ratio is not None else
                     f"at most {R_max:,.0f} m" if R_max else None,
                     "given" if R is not None else R_by if R_ratio is not None else "given: the farthest it can be" if R_max else
                     "needs a sourced range"))
        th_tau = aspect_from_tau(self.omega_last(), self.tau()["tau_s"]) if th is None and self.omega_last() is not None and self.tau() else None
        b, om = self.depth_rate_max(), kf.get("omega_rad_per_s")
        th_low = math.degrees(math.atan(om / b)) if th is None and th_tau is None and b and om is not None else None
        rows.append(("aspect angle / range rate", "θ, Ṙ",
                     (f"θ = {th_tau:.0f}°" if th_tau is not None else f"θ ≥ {th_low:.0f}°" if th_low is not None else None) if th is None else
                     f"θ = {th:.0f}°" + (f" (Ṙ = {rdot:g} m/s)" if rdot is not None else ""),
                     ("given" if rdot is None else "from Ṙ, ω and R") if th is not None else
                     "from τ (its size along the track) and ω at its last frame: tan θ = ω τ, no range" if th_tau is not None else
                     f"no closing seen: |Ṙ / R| under {pct(b)} a second (its speed along the track held), so tan θ > ω / that "
                     "-- if it flew straight at a steady speed, which its track fits" if th_low is not None else
                     "needs a range history, a sourced angle, or τ from a size that grows"))
        rows.append(("platform velocity", "v_own", None if v_own is None else f"{v_own:.0f} m/s",
                     "given (the aircraft's speed)" if v_own is not None else "needs the aircraft's speed"))
        lb, bar = kf.get("lower_bound_m_per_s"), kf.get("scale_bar_m_per_s")
        top = kf.get("upper_bound_m_per_s") if R_max else None
        if lb is not None:
            rows.append(("transverse relative speed", "ωR = |v_obj − v_own| sin θ", f"{lb:.0f} m/s",
                         "from ω and R: the least the speed can be. " + ISOTROPIC))
        elif top is not None:
            fast = kf.get("upper_bound_fastest_m_per_s")
            rows.append(("transverse relative speed", "ωR", f"at most {_two(top):,g} m/s" + (f" ({_two(fast):,g} at its fastest)" if fast else ""),
                         "from ω and the farthest range given: the picture's rate, against the line of sight as the camera held "
                         "it, " + (f"its speed along its path on average, the distance it travelled over the time (at its fastest, "
                                   f"{_two(fast):,g} m/s); " if fast else "") +
                         "less if the object is nearer. Its motion toward or away from the camera is not measured"))
        elif bar is not None and kf.get("range_ratio"):
            rows.append(("transverse relative speed", "|v_obj − v_own| sin θ", f"{bar:.0f} m/s",
                         f"from the reference object at R_obj/R_ref = {kf['range_ratio']:g} (given): k cancels"))
        elif bar is not None:
            rows.append(("transverse relative speed", "|v_obj − v_own| sin θ", f"{bar:.0f} m/s × R_obj/R_ref",
                         "from the reference object: k cancels, the range ratio remains; no more than this where R_obj ≤ R_ref"))
        else:
            rows.append(("transverse relative speed", "ωR = |v_obj − v_own| sin θ", None, needs(k=k, R=R)))
        S = p * R / k if (p and R and k) else None
        ref = sf.get("reference") or {}
        if S is None and p and kf.get("range_ratio") and ref.get("px") and ref.get("length_m"):
            # beside a thing of known length at a known ratio of its distance, k cancels: S = p (R_obj / R_ref) L / l
            S = p * kf["range_ratio"] * ref["length_m"] / ref["px"]
            rows.append(("object size", "S = p (R_obj/R_ref) L / l", f"{S:.1f} m",
                         f"from p and the reference of known length ({ref['length_m']:g} m over {ref['px']:g} px) at the range ratio "
                         f"given ({kf['range_ratio']:g}): k cancels"))
        elif S is None and p and k and R_max and p_how != SPOT_SIZE:
            rows.append(("object size", "S = pR/k", f"at most {_two(p * R_max / k):,g} m", "from p, k and the farthest range given"))
        elif S is None and p and k and R_max:
            rows.append(("object size", "S = pR/k", None, "needs its width in pixels: a limit is not built on the spot size the track "
                                                          "was followed at"))
        else:
            rows.append(("object size", "S = pR/k", None if S is None else f"{S:.1f} m", "from p, R and k" if S else needs(p=p, R=R, k=k)))
        rel = kf.get("relative_speed_m_per_s") if th is not None else None
        rows.append(("relative speed", "|v_obj − v_own|", None if rel is None else f"{rel:.0f} m/s", 
                     "from ω, R and θ" if rel is not None else needs(k=k, R=R, **{"θ (or Ṙ)": th})))
        rows.append(("object velocity", "v_obj", None, "needs the relative speed, its direction, and v_own as a vector"))
        # what survives the missing variables (section 33): facts of the track that need none of the four
        tn, pj, sm = kf.get("turn"), kf.get("projective"), kf.get("smear")
        el = tn.get("ellipse") if tn and tn.get("how") == "ellipse" else None
        if el:                                       # a loop, read whole (section 33, M4): the radius is the turn's own
            rows.append(("turn radius in body widths", "r_turn / D", pm(tn["r_turn_over_D"], el["r_turn_over_D_err"]),
                         f"a loop through {el['arc_deg']:,.0f}°, read as the ellipse a circle draws at any tilt ({el['major_px']:.0f} by "
                         f"{el['minor_px']:.0f} px, its plane {el['tilt_deg']:.0f}° from facing the camera, round at "
                         f"{el['omega_rad_per_s']:.2f} rad/s): {el['speed_widths_per_s']:.1f} body widths a second, "
                         f"{el['accel_widths_per_s2']:.1f} a second² toward its centre, from its width ({tn['width_px']:.1f} px); no range, "
                         "field of view, platform speed or foreshortening needed; a turn, or the camera's own motion"))
        elif tn:
            rows.append(("turn radius in body widths", "r_turn / D",
                         f"about {tn['r_turn_over_D']:,.0f}" if tn["bent"] else f"at least {tn['r_turn_over_D_low']:,.0f} (95 %)"
                         if tn["r_turn_over_D_low"] is not None else "no bend at all",
                         ("a turn" if tn["turned"] else ("a hair off straight: the camera's as easily as the object's" if tn.get("lens")
                                                         else "a hair off straight: the camera's or the lens's as easily as the object's")
                          if tn["bent"] else "did not turn") + f"; from the track's bend ({tn['sagitta_px']:.1f} ± {tn['sagitta_err_px']:.1f} px "
                         f"over {tn['length_px']:.0f}) and its width ({tn['width_px']:.1f} px); no range, field of view or platform speed needed"
                         + ("; the picture's radius: with the turn's plane at random to the line of sight its own is "
                            f"{TILT_OWN[0]:g} to {TILT_OWN[1]:g} times it nine times in ten" if tn["bent"] else
                            f"; a turn whose plane holds the line of sight looks straight ({TILT_STRAIGHTER[0][0]} times tighter for "
                            f"{100 * TILT_STRAIGHTER[0][1]:.0f} % of the ways its plane can lie)")
                         + (swings_said(tn["swings"]) if tn.get("swings") else "")))
        elif kf.get("fit") and not (kf.get("fit") or {}).get("held"):
            rows.append(("turn radius in body widths", "r_turn / D", None, "needs the object's width"))
        if pj:
            if pj["closing"] is not None and pj.get("fits") is False:
                rows.append(("constant velocity, as a pinhole draws it", "1/(t_z − t)", f"describes its trend to {trend_px(pj)} px",
                             f"{'constant velocity' if pj['closing'] else 'constant image speed'} follows the track's trend as a free "
                             f"quadratic does ({pj['rms_quad']:.1f} px rms), but misses it by {pj['misfit']:.0f} times its own jitter "
                             f"({pj['jitter_px']:.2f} px): not a straight line at a steady speed to the jitter -- the camera's motion or "
                             f"the object's own is in it, so no time to the camera's plane; straight to {pj['straight_rms']:.1f} px"
                             + (f"; {depth_said(pj['depth'], trend=True)}" if pj.get("depth") else
                                f"; {pj['depth_none']}" if pj.get("depth_none") else "") + lens_could(pj)))
            elif pj["closing"] is True:
                rows.append(("constant velocity, as a pinhole draws it", "1/(t_z − t)",
                             f"passes: {'closing' if pj['T'] > 0 else 'receding'}, T = {abs(pj['T']):.2f} s"
                             + (f", θ = {pj['psi_deg']:.0f}°" if pj.get("psi_deg") is not None else ""),
                             f"the speed is about R / {abs(pj['T']):.2f} s at the {'last' if pj['T'] > 0 else 'first'} frame, for a range R there; "
                             f"straight to {pj['straight_rms']:.1f} px, {pj['rms']:.1f} px rms against a free quadratic's {pj['rms_quad']:.1f}"
                             + held_to(pj)))
            elif pj["closing"] is False:
                dep = pj.get("depth")
                rows.append(("constant velocity, as a pinhole draws it", "1/(t_z − t)", "passes, no closing seen"
                             + (f": depth changing under {pct(dep['rate_max_per_s'])} a second" if dep else ""),
                             f"straight to {pj['straight_rms']:.1f} px at constant image speed ({pj['rms_const']:.1f} px rms"
                             + held_to(pj) + "): " + (depth_said(dep) if dep else pj.get("depth_none") or "nothing of the range's change")))
            else:
                rows.append(("constant velocity, as a pinhole draws it", "1/(t_z − t)", "fails",
                             f"straight to {pj['straight_rms']:.1f} px; neither constant velocity ({pj['rms']:.1f} px rms) nor constant image "
                             f"speed ({pj['rms_const']:.1f}) describes it as a free quadratic does ({pj['rms_quad']:.1f})" + lens_could(pj)))
            if pj.get("lens"):
                rows[-1] = rows[-1][:3] + (rows[-1][3] + lens_said(pj["lens"]),)
        if sm is not None:
            rows.append(("smear", "Π_s", f"{sm:.2f} widths a frame", "the displacement in one frame over the object's width: above 1 it streaks "
                                                                     "within a frame; above 2 an interlaced source's fields separate"))
        ta, tr = self.tau(), self.tau_reading()
        if ta:
            rows.append(("time to contact", "τ = R / |Ṙ|", f"{pm(abs(ta['tau_s']), ta.get('tau_err_s'))} s, " + ("closing" if ta["tau_s"] > 0 else "receding"),
                         ("from its size along the track, which grows as a straight approach draws it (the looming law, its blur's "
                          f"share taken out), at its last frame; R / |Ṙ| with no range or field of view" if ta.get("from") != "given" else "given")
                         + ("" if self.omega_last() is None else
                            f"; with ω at the last frame, tan θ = ω τ: θ = {aspect_from_tau(self.omega_last(), ta['tau_s']):.0f}°")))
        elif tr:
            lc = tr.get("light") or {}
            rows.append(("time to contact", "τ = R / |Ṙ|", None, (tr.get("why") or "not measured")
                         + (f"; its brightness would give τ = {pm(lc['tau'], lc['tau_err'])} s at the track's middle if the change were "
                            "its range's alone (a steady source; the picture's gamma makes that long by up to 2.2)" if lc.get("tau") else "")))
        ff = st("flicker")
        beats = own_beats(ff)
        beat = next(iter(beats.values()), None)
        if len(beats) > 1:                                 # a group: each member's own beat, out of step with the others
            hz = sorted(b["hz"] for b in beats.values())
            measured = max(len(ff.get("beat") or {}), len(beats))
            rows.append(("brightness beat", "f_b", f"{len(beats)}{'' if measured == len(beats) else f' of {measured}'} members: "
                                                   f"{hz[0]:.1f}–{hz[-1]:.1f} Hz",
                         "each member's own, out of step with the others: a rhythm of the video would beat them as one. "
                         "A wingbeat, a tumbling body and a blinking light all beat"))
        elif beat:
            rows.append(("brightness beat", "f_b", f"{beat['hz']:.1f} Hz" + (f" (and {beat['double_hz']:.1f} Hz, {_double_said(beat['hz'], beat['double_hz'])})" if beat.get("double_hz") else ""),
                         f"the object's own, over frames {beat['first']}–{beat['last']}: clear of the codec's rhythm, not shared by the "
                         "background beside it" + ("" if beat.get("comes_back", True) else
                                                  ". One stretch only: the whole track does not beat, and no window apart from it does")
                         + (f". The whole picture shakes at that rate by {beat['shaken']['px']:.2g} pixels, so the camera may make it"
                            if beat.get("shaken") else "")
                         + ". A wingbeat, a tumbling body and a blinking light all beat"))
        elif ff:
            rows.append(("brightness beat", "f_b", None, ff.get("finding") or next((w for _, w in (self.stages.get("flicker", {}).get("no_power") or [])), "not measured")))
        blinks = ff.get("blink") or {}
        for name, k in blinks.items():                     # a light that flashes in a train, its own (flicker's item 13)
            if not k.get("train") or k.get("shared"):
                continue
            word = {"brightness": "brightness", "white": "hottest pixels" if k.get("black_hot") else "brightest pixels",
                    "red": "reddest pixels"}.get(k.get("best"), "brightness")
            rows.append(("flashing light" + (f" ({name})" if len(blinks) > 1 else ""), "f_light",
                         f"{k['per_minute']:.0f} a minute ({k['hz']:.2f} Hz)",
                         f"a train of {k['flashes']} flashes in its {word}, not shared by the background beside it"
                         + ("; an aircraft's anti-collision light flashes 40–100 a minute" if k.get("rule") == "anti-collision" else
                            "; within the 180 a minute allowed where two anti-collision lights' beams overlap"
                            if k.get("rule") == "overlap" else "")
                         + ("; the beat is the flashes'" if k.get("marked") else "")
                         + ". A glint off something that turns flashes too"))
        return rows

    def extent(self):
        """(p, how): the object's image extent in pixels -- the length given, else its measured width at
        half its peak, else the spot size the track was followed at -- or (None, what would give it)."""
        kf = self.stages.get("kinematics", {}).get("fields") or {}
        tf = self.stages.get("track", {}).get("fields") or {}
        res = kf.get("resolution") or {}
        if kf.get("size_px"):
            return kf["size_px"], "given"
        if res.get("object_fwhm_px"):
            return res["object_fwhm_px"], "measured: the object's width at half its peak"
        if tf.get("object_size_px"):
            return tf["object_size_px"], SPOT_SIZE
        return None, "needs a track, or the object's length given"

    # what the first line and the bottom line say of a rate read over a picture that held still on screen
    HELD_STILL = "the picture behind it held still on screen, so its motion against the background is not measured"

    def behind_held_still(self):
        """Whether the picture behind the object held still on screen while it was measured: the layers step's own
        no-power ("the scene is held still on screen even over 30 frames in 77% of pairs: a background rate there is
        an upper limit, not a measurement"). A camera following the object over a sky with nothing to read, and a
        camera held still over a slow scene, both look so, and the step cannot tell them apart (a pattern on the
        sensor can hold a match at zero). The object's rate against the background is then not measured, whatever
        number the step read of it: what the track gives is its motion in the picture, as the camera held it. IMG_5611
        (2026-11-01): the phone followed the object, which moved 98 px/s against the clouds while the track read 6
        px/s, and the first line said "the object moved about 0° a second in the image"."""
        return any("held still on screen" in str(why) for _, why in (self.stages.get("layers") or {}).get("no_power") or [])

    def held_still_said(self):
        """The bottom line's sentence on it, after a rate read over a picture that held still."""
        return ("The picture behind the object held still on screen while it was tracked, so that is its motion as the "
                "camera held it, not against the background, which is not measured: a camera following the object over "
                "a sky with nothing to read, and a camera held still over a slow scene, both look so, and the layers step "
                "cannot tell them apart (its own line under Measurements).")

    def rate(self):
        """(px/s, against what): the object's rate against the background where the layers check measured
        it (its largest motion group): the median of one-second windows over the whole track, every second once
        (`layers.over_track`), or in a case file written before it, of the windows where the background was read --
        "in the picture, as the camera held it" where that background held still on screen (`behind_held_still`);
        else its rate in the image; (None, None) with no track."""
        lf = self.stages.get("layers", {}).get("fields") or {}
        per = lf.get("px_per_s") or {}
        if lf.get("tracked") and (per.get("all") or {}).get("median"):
            whole = (lf.get("over_track") or {}).get("all")
            return ((whole["median"] if whole else per["all"]["median"]),
                    "in the picture, as the camera held it" if self.behind_held_still() else "against the background")
        v = (self.stages.get("kinematics", {}).get("fields") or {}).get("v_px_per_s")
        return (v, "in the image") if v is not None else (None, None)

    def ranged(self):
        """(R, how, assumed): the object's range where the case gives one -- given; else from a reference of known length
        and the range ratio, with k: the reference is at R_ref = L k / l, the object R_obj / R_ref times as far (ROADMAP
        0.4, objective 5: "the range ratio for a reference object"). The speed across the line of sight from the reference
        needs no k (it cancels); the range does, and is as assumed as k is. (None, None, False) where neither."""
        kf = self.stages.get("kinematics", {}).get("fields") or {}
        sf = self.stages.get("scale", {}).get("fields") or {}
        if kf.get("range_m") is not None:
            return float(kf["range_m"]), "given", False
        ref, ratio, k = sf.get("reference") or {}, kf.get("range_ratio"), sf.get("k_px_per_rad")
        if not (ref.get("px") and ref.get("length_m") and ratio and k):
            return None, None, False
        R_ref = ref["length_m"] * k / ref["px"]
        assumed = "ASSUMED" in (sf.get("k_from") or "")
        return (ratio * R_ref, f"the reference of known length ({ref['length_m']:g} m over {ref['px']:g} px) is at L k / l = "
                               f"{R_ref:,.0f} m, and the object {ratio:g} times as far (the range ratio, given)"
                               + (": as assumed as k is" if assumed else ""), assumed)

    def range_bounds(self):
        """(R_min, R_max, given): the range the stages bound -- a range given (or worked out from a reference and its
        range ratio, `ranged`) is both; else the focus's floor below, the horizon's and the haze's ceilings above and the
        farthest range given (the ledger's rows, as numbers); None where nothing bounds it."""
        st = lambda name: self.stages.get(name, {}).get("fields") or {}
        R = self.ranged()[0]
        if R is not None:
            return float(R), float(R), True
        hz, ha, fo = st("horizon").get("bounds") or {}, st("haze"), st("focus").get("bound") or {}
        top = [v for v in (hz.get("range_max_m"), ha.get("bound_m"), st("kinematics").get("range_max_m")) if v and math.isfinite(v)]
        low = [v for v in (fo.get("floor_m"),) if v and math.isfinite(v)]
        return (max(low) if low else None), (min(top) if top else None), False

    def omega_last(self):
        """The object's angular rate at its last frame, rad/s: the speed band's rate there (`band["v_end"]`) over k. tau is
        read at the last frame, so theta = atan(omega tau) wants omega there too -- on a thing closing on the camera its
        rate in the picture grows, and the track's average would put theta low (a drawn approach: 2° for 6°). None
        without the band or k."""
        kf = self.stages.get("kinematics", {}).get("fields") or {}
        k = (self.stages.get("scale", {}).get("fields") or {}).get("k_px_per_rad")
        band = kf.get("band") or {}
        return band["v_end"][1] * (kf.get("square_per_px") or 1.0) / k if band.get("v_end") and k else None

    def tau_reading(self):
        """The flicker stage's tau reading for the object (`kinematics.tau_of`, method section 33): the track named
        "object", else the first; None where the stage read none."""
        taus = (self.stages.get("flicker", {}).get("fields") or {}).get("tau") or {}
        return taus.get("object") or next(iter(taus.values()), None)

    def tau(self):
        """The object's tau where one is measured: the flicker stage's from its size along the track (route "looming"),
        else a `looming` in the kinematics fields (`kinematics.looming_fit`'s, given by a caller); dict(tau_s (positive
        closing), tau_err_s, from) or None."""
        r = self.tau_reading()
        if r and r.get("route"):
            return {"tau_s": r["tau_s"], "tau_err_s": r.get("tau_err_s"), "from": r["route"]}
        lm = (self.stages.get("kinematics", {}).get("fields") or {}).get("looming") or {}
        if lm.get("tau_last") is not None:
            band = lm.get("t_z_band")
            return {"tau_s": lm["tau_last"], "tau_err_s": (band[1] - band[0]) / 2 if band else None, "from": "given"}
        return None

    def admissible(self):
        """The admissible region in (R, Rdot) (`kinematics.admissible_region`, method section 33) from what the case
        holds: the turn rate (needs k), the range's bounds (`range_bounds`), the extent and k for the size, tau where
        the kinematics stage measured one. None without a turn rate."""
        from .kinematics import admissible_region
        kf = self.stages.get("kinematics", {}).get("fields") or {}
        om = kf.get("omega_rad_per_s")
        if om is None or (kf.get("fit") or {}).get("held"):
            return None
        k = (self.stages.get("scale", {}).get("fields") or {}).get("k_px_per_rad")
        lo, hi, _ = self.range_bounds()
        tau = (self.tau() or {}).get("tau_s")
        if tau is not None and self.omega_last() is not None:      # tau is the last frame's: so is omega, with it
            om = self.omega_last()
        return admissible_region(om, k=k, p_px=self.extent()[0], R_min=lo, R_max=hi, tau_s=tau, rate_max=self.depth_rate_max(),
                                 ceiling="farthest range given" if hi is not None and hi == kf.get("range_max_m") else "range ceiling")

    def depth_rate_max(self):
        """|Rdot / R| at most this, per second, where the track fits constant velocity to its own jitter with no closing
        seen (`projective.depth_bound`, the pure-mathematics survey's M5): its speed along the track held, so its depth
        cannot have changed faster. None where the track does not fit (the bound is then said only as a condition)."""
        pj = (self.stages.get("kinematics", {}).get("fields") or {}).get("projective") or {}
        dep = pj.get("depth")
        return dep["rate_max_per_s"] if dep and pj.get("closing") is False and pj.get("fits") else None

    def survives(self):
        """What survives the missing variables (method section 33), as sentences: the turn, the constant-velocity
        test, the smear, and the admissible region -- from the kinematics stage's fields."""
        from . import projective
        from .kinematics import admissible_said
        kf = self.stages.get("kinematics", {}).get("fields") or {}
        said = projective.said(kf.get("projective"), kf.get("turn"), kf.get("smear"))
        ta, pj = self.tau(), kf.get("projective") or {}
        if ta and ta.get("from") == "looming":
            e = ta.get("tau_err_s")
            when = pm(abs(ta["tau_s"]), e)
            said["time to contact"] = ((f"its size grows as a straight approach draws it: it would reach the camera's plane {when} s "
                                        "after its last frame at this rate (tau, R / |Rdot|)") if ta["tau_s"] > 0 else
                                       f"its size shrinks as a straight retreat draws it: it was at the camera's plane {when} s before "
                                       "its last frame (tau, R / |Rdot|)")
            if pj.get("closing") is True and pj.get("fits") is not False and (pj["T"] > 0) == (ta["tau_s"] > 0):
                lo_hi = [b - pj["t_last"] for b in pj["t_z_band"]] if pj.get("t_z_band") else None
                agree = (abs(abs(pj["T"]) - abs(ta["tau_s"])) <= 2 * math.hypot(e or 0.0, (lo_hi[1] - lo_hi[0]) / 2 if lo_hi else 0.0)
                         if (e or lo_hi) else None)
                said["time to contact"] += (f"; its path, read alone, puts that at {abs(pj['T']):.2f} s"
                                            + ("" if agree is None else ", which agrees" if agree else
                                               ", which does not agree: the two cannot both be a straight line at a steady speed"))
        reg = self.admissible()
        if reg and not reg.get("empty") and admissible_said(reg):
            said["what the clip allows"] = admissible_said(reg)
        return said

    def ledger(self):
        """The four unknowns of the velocity equation -- k, R, theta and v_own -- each a dict(symbol, name, status,
        value, by, closes). `status` is "constrained" (measured, or given from a source), "assumed" (a field of view
        taken without a source, as `scale` says of every --fov), "bounded" (a bound only, from a stage that needs no
        motion: `slew`'s c on k, a ceiling on R from `horizon` or `haze` and a floor from `focus`) or "missing"; `by`
        is the route, and `closes` the datum a release could give that would close it (LEDGER_CLOSES). Written from
        the stages' fields, as the summary is: the stages run on their own reach a case through their --case."""
        st = lambda name: self.stages.get(name, {}).get("fields") or {}
        sf, kf, sl = st("scale"), st("kinematics"), st("slew")
        rows = []

        def row(symbol, name, status, value, by):
            rows.append(dict(symbol=symbol, name=name, status=status, value=value, by=by,
                             closes=None if status == "constrained" else LEDGER_CLOSES[symbol]))
        k, k_from = sf.get("k_px_per_rad"), sf.get("k_from") or ""
        c, floor = sl.get("c_px_per_deg"), sl.get("c_at_least_px_per_deg") if sl.get("floor_stands") else None
        if k:
            row("k", "angular scale", "assumed" if "ASSUMED" in k_from else "constrained",
                f"{k * math.pi / 180:.1f} px/deg" + (f" up the picture, {sf['k_x_px_per_rad'] * math.pi / 180:.1f} across"
                                                     if sf.get("k_x_px_per_rad") else ""), k_from or "given")
        elif sl.get("k_px_per_deg"):
            row("k", "angular scale", "constrained", f"{sl['k_px_per_deg']:.0f} px/deg",
                f"the camera's slew (mcdonald slew), at a depression of {sl['depression_deg']:g}° given")
        elif c or floor:
            row("k", "angular scale", "bounded", f"at least {c or floor:.0f} px/deg",
                "the camera's slew (mcdonald slew): " + ("its scene against its north pointer gives c = k cos(depression)"
                                                          if c else "a floor where the pointer did not register the turn"))
        elif sf.get("reference"):                          # a thing of known length gives a scale at its own distance, not k
            row("k", "angular scale", "missing", None, "no graticule, field of view or slew; the reference of known length "
                                                       "gives the speed across the line of sight without it (k cancels)")
        else:
            row("k", "angular scale", "missing", None, "no graticule, field of view or slew")
        R, R_by, R_assumed = self.ranged()
        ref, ratio = sf.get("reference") or {}, kf.get("range_ratio")
        if R is not None:
            row("R", "range", "assumed" if R_assumed else "constrained", f"{R:,.0f} m", R_by)
        else:
            hz, ha, fo = st("horizon").get("bounds") or {}, st("haze"), st("focus").get("bound") or {}
            top = [(v, why) for v, why in ((hz.get("range_max_m"), "the horizon (mcdonald horizon)"),
                                           (ha.get("bound_m"), f"the haze, to a factor of about {ha.get('factor', 4):g} "
                                                               "(mcdonald haze)"),
                                           (kf.get("range_max_m"), "the farthest range given")) if v and math.isfinite(v)]
            low = [(v, why) for v, why in ((fo.get("floor_m"), "sharp as a point, if focused far (mcdonald focus)"),)
                   if v and math.isfinite(v)]
            said = ([f"at most {_far(min(top)[0], two=False)}" + (f", by {min(top)[1]}" if len(top) + len(low) > 1 else "")]
                    if top else []) + ([f"at least {_far(max(low)[0], two=False)}"
                                        + (f", by {max(low)[1]}" if len(top) + len(low) > 1 else "")] if low else [])
            # a reference of known length is a range of its own, at L k / l: the object's is that times a ratio
            yard = ("" if not (ref.get("px") and ref.get("length_m")) else
                    f"; the reference of known length is at L k / l = {ref['length_m'] * k / ref['px']:,.0f} m, and the object's "
                    "range is that times R_obj / R_ref, not given" if k and not ratio else
                    f"; with k, the reference of known length and the range ratio given ({ratio:g}) would give it: "
                    "R = (R_obj / R_ref) L k / l" if ratio else "")
            if said:
                row("R", "range", "bounded", "; ".join(said),
                    ("; ".join(why for _, why in top + low) if len(top) + len(low) == 1 else "with no motion and no size") + yard)
            else:
                row("R", "range", "missing", None, "not given, and no bound measured" + yard)
        th, rdot = kf.get("theta_deg"), kf.get("range_rate_m_per_s")
        ta, om = self.tau(), self.omega_last()
        if th is not None:
            row("θ", "aspect angle", "constrained", f"{th:.0f}°", "from a range rate, omega and R" if rdot is not None else "given")
        elif ta and om is not None and not (kf.get("fit") or {}).get("held"):
            row("θ", "aspect angle", "constrained", f"{aspect_from_tau(om, ta['tau_s']):.0f}°",
                f"tau ({pm(abs(ta['tau_s']), ta.get('tau_err_s'))} s, from its size along the track) and omega at its last frame: "
                "tan θ = ω τ, no range")
        elif ta:
            row("θ", "aspect angle", "missing", None, f"tau is measured ({pm(abs(ta['tau_s']), ta.get('tau_err_s'))} s, from its size "
                                                       "along the track); with k, omega would give θ = atan(ω τ)")
        elif self.depth_rate_max() is not None and kf.get("omega_rad_per_s") is not None:
            b = self.depth_rate_max()
            row("θ", "aspect angle", "bounded", f"at least {math.degrees(math.atan(kf['omega_rad_per_s'] / b)):.0f}°",
                f"no closing seen: its speed along the track held, so its range changed by less than {pct(b)} of itself a "
                f"second, and tan θ = ω R / |Ṙ| > ω / {b:.3g} -- if it flew straight at a steady speed, which its track fits")
        else:
            dep = (kf.get("projective") or {}).get("depth")
            row("θ", "aspect angle", "missing", None, "not given, and no range history"
                + (f"; if it flew straight at a steady speed its range changed by less than {pct(dep['rate_max_per_s'])} of "
                   "itself a second (its speed along the track), but its track does not fit that to its own jitter"
                   if dep and (kf.get("projective") or {}).get("fits") is False else
                   f"; its range changed by less than {pct(dep['rate_max_per_s'])} of itself a second (its speed along the "
                   "track held); with k, omega would bound θ" if dep else ""))
        v_own = (kf.get("parallax") or {}).get("v_own")
        if v_own is not None:
            row("v_own", "platform speed", "constrained", f"{v_own:.0f} m/s", "given")
        else:
            row("v_own", "platform speed", "missing", None, "not given")
        return rows

    def _ledger(self):
        L = ["## The four unknowns", "", "| unknown | where it stands | value | by | what would close it |",
             "|---|---|---|---|---|"]
        for r in self.ledger():
            L.append(f"| {r['name']}, {r['symbol']} | {r['status']} | {'**' + r['value'] + '**' if r['value'] else '—'} "
                     f"| {r['by']} | {r['closes'] or '—'} |")
        return L + [""]

    def _summary(self):
        c = self.clip or {}
        L = ["## Summary of variables", ""]
        L += ["| variable | symbol | value | how |", "|---|---|---|---|"]
        for name, sym, val, how in self.summary():
            cell = lambda t: t.replace("|", "\\|")      # |v_obj − v_own| is a magnitude, not a column
            L.append(f"| {name} | {cell(sym)} | {'**' + cell(val) + '**' if val else '—'} | {cell(how)} |")
        return L + [""]

    # ---- rendering ------------------------------------------------------------------
    def _provenance(self):
        r = self.record
        if not r:
            return ("No catalog record for this file, so this report says nothing about its "
                    "provenance: who released it, and whether they disclosed any alteration, "
                    "has to be established separately. Pixel tests cannot substitute for that.")
        bits = [f"**{r.get('title', 'record')}**"]
        if r.get("release"):
            bits.append(f"release {r['release']}")
        if r.get("disclosure"):
            bits.append(f"the release states: *{r['disclosure']}*")
        else:
            bits.append("no alteration statement in the release text")
        return " — ".join(bits) + "."

    @staticmethod
    def _num(v):
        """A number out of a stage result, which may hold a formatted string."""
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(str(v).split()[0])
        except (ValueError, IndexError):
            return None

    def segment_said(self, measured=True):
        """The segment of the video the person chose, in the video's time as the segment step shows it and in frames,
        and the frames measured where they were fewer (and `measured`): the part round the object's track (an object is
        measured over the frames it is in and a little either side, `stages.around`). A tester, 2026-10-19: "I don't think
        it mentions the segment chosen by the user" -- the report named only the frames measured. A case written before
        the segment was kept has none: its clip is all it says."""
        c = self.clip or {}
        if not c.get("fps"):
            return ""
        at = lambda n: clock((n - 1) / c["fps"])
        a, b = self.segment or (c["n0"], c["n1"])
        said = f"**Segment:** {at(a)} to {at(b)} of the video, {(b - a + 1) / c['fps']:.1f} s (frames {a}–{b})"
        if measured and (c["n0"], c["n1"]) != (a, b):
            said += f". Measured over {at(c['n0'])} to {at(c['n1'])} (frames {c['n0']}–{c['n1']}), the part of it round the object's track"
        return said + "."

    def older(self):
        """The version that measured this case, where it is not this one; else None. Such a case is read by this
        version's rules: a beat that version's stages found may be named a bird now where its own report did not
        (the bird was first named in 0.2.14), and its stages might not find that beat at all today."""
        return self.measured_by if self.measured_by and self.measured_by != __version__ else None

    def older_said(self):
        return (f"Measured with mcdonald {self.older()}, and read with {__version__}: what that version found, said by "
                "this one's rules. Measure it again to have this version's own numbers.")

    def stopped_in(self):
        """Where the measuring was stopped, if it was -- "during layers", or "before kinematics" when
        it was stopped between two steps -- or None. The steps after it did not run."""
        during = next((name for name, st in self.stages.items()
                       if any("stopped before it finished" in str(why) for _, why in st.get("no_power") or [])), None)
        before = next((n[len(STOPPED_BEFORE):] for n in self.notes if n.startswith(STOPPED_BEFORE)), None)
        return f"during {during}" if during else f"before {before}" if before else None

    def _scaled(self):
        """(omega, k, p, how, held, point) for the two sentences below: the kinematics step's turn rate in the picture
        (the Technical Note's omega = v_px f / k, the number the summary's table holds), the scale, the object's size in
        the picture and where it came from, whether the camera held the object in view (its turning is then the
        camera's, not measured here: the Note's tracked objects), whether the object is no wider than a point, and how much
        wider than tall the picture draws a pixel (1 on square pixels; section 40: the extent p is then in the file's
        pixels, between p / a and p square ones)."""
        kf = self.stages.get("kinematics", {}).get("fields") or {}
        sf = self.stages.get("scale", {}).get("fields") or {}
        p, how = self.extent()
        return (kf.get("omega_rad_per_s"), sf.get("k_px_per_rad"), p, how,
                bool((kf.get("fit") or {}).get("held")), (kf.get("resolution") or {}).get("resolved") is False, sf.get("pixel_aspect") or 1.0)

    def at_each_distance(self):
        """The headline's words where the turn rate is known (a field of view, or angle marks) and the distance is not:
        how fast the object crosses the view and how big it is there, then how far away a bird, a weather balloon and a
        fighter jet of their sizes would be, and how fast they would then cross the line of sight, at least (omega R;
        `figures.BIRDS` and `OBJECTS`, which the size-and-speed figure marks too). An object no wider than a point
        here is no bigger than that in the picture, so each would be at least that far away; one the camera held in
        view has no speed here, only where each would be."""
        from .figures import BIRDS, OBJECTS
        omega, k, p, _, held, point, a = self._scaled()
        still = not held and self.behind_held_still()
        turn = ("the camera kept the object in view, so how fast it crossed the view is the camera's turning, not "
                "measured here" if held else
                f"the object moved about {_deg(omega)} a second in the picture, as the camera held it ({self.HELD_STILL})" if still
                else f"the object moved about {_deg(omega)} a second in the image")
        no_speed = held or still                    # a speed across the line of sight needs the rate against the world
        if not p or not k:
            return turn + ("" if no_speed else f": at 100 m away that is at least {_num(omega * 100)} m/s across the line of "
                           f"sight, at 1 km {_num(omega * 1000)} m/s") + ", and how far away it is decides what it is"
        least = "at least " if point else ""
        # on a stretched picture the extent in the file's pixels is between p / a and p square ones, so each distance is a span
        R, R_far, spread = (lambda size: size * k / p), (lambda size: size * k * a / p), a != 1.0
        said = []
        for i, (name, lo, hi) in enumerate(_kinds()):             # smallest first; the first carries the words the rest shorten
            kind = " or ".join(f"{'an' if w[0] in 'aeiou' else 'a'} {w}" for w in name.split(" or "))
            sizes = f"{lo:g}–{hi:g} m" if hi > lo else f"{lo:g} m"
            far = f"{least}{_span(R(lo), R_far(hi)) if hi > lo or spread else _far(R(lo))} away"
            fast = "" if no_speed else (f"{_num(omega * R(lo))}–{_num(omega * R_far(hi))}" if hi > lo or spread else _num(omega * R(lo))) + " m/s"
            if i == 0:
                said.append(f"as {kind} ({sizes}) it would be {far}" + (f" and moving at least {fast} across the line of sight" if fast else ""))
            else:
                said.append(f"as {kind} ({sizes}), {far}" + (f" and {fast}" if fast else ""))
        size = f"{p:.0f} pixels" + ("" if point else " across") + (f" ({math.degrees(p / k):.2g}°)" if not spread else
                                                                    f" in the file ({math.degrees(p / k / a):.2g}–{math.degrees(p / k):.2g}°: "
                                                                    f"the picture is drawn {a:.4g} times wider than tall)")
        return (turn + f"{'; it' if held else ' and'} is {'no wider than a point here, ' if point else ''}{size}; what it is "
                "depends on how far away it is: " + "; ".join(said))

    def at_the_distance(self):
        """(the headline's words, the least speed, the speed) where a scale and a distance are both given (Jacob,
        2026-10-22: "it is worth thinking about how the headline conclusion should change if both FOV and range are
        provided"): its size at that distance and the kind it is near in size, and omega R -- the speed across the line
        of sight, which is the least the speed as the camera held it can be, its motion toward or away from the
        camera not measured. The speed itself only where an angle is given too (theta, or a range rate). None where
        the case has no turn rate or no distance (one put together by hand, with only a speed)."""
        kf = self.stages.get("kinematics", {}).get("fields") or {}
        omega, k, p, _, held, point, a = self._scaled()
        R, theta = kf.get("range_m"), kf.get("theta_deg")
        if omega is None or R is None:
            return None
        where = f"at the given distance of {_far(R, two=False)}" + (f", moving at {theta:.0f}° to the line of sight" if theta is not None else "")
        size = ""
        if p and k:
            S = p * R / k
            size = (f", it is {'no more than ' if point else ''}about {_two(S):g} m across, {_like(S)}" if a == 1.0 else
                    f", it is {'no more than ' if point else ''}about {_two(S / a):g}–{_two(S):g} m across, {_like(S)}")
        if held:
            return f"{where}{size}; the camera kept it in view, so its speed is not measured here", None, None
        least = kf.get("lower_bound_m_per_s")
        least = omega * R if least is None else least
        full = kf.get("relative_speed_m_per_s") if theta is not None else None
        moving = (f"moving about {_num(full)} m/s as the camera held it (Mach {full / A_SOUND:.2g})" if full is not None else
                  f"moving at least {_num(least)} m/s across the line of sight as the camera held it "
                  f"(Mach {least / A_SOUND:.2g})")
        return f"{where}{size}, and {moving}", least, full

    def at_the_farthest(self):
        """(the headline's words, the most the speed can be) where a scale and a farthest range are given and nothing gives
        the distance (`--range-max`; 2026-10-30, PR051's drift against the ground behind it): `at_the_distance` as a limit --
        its size at that range and omega R there, each the most it can be, for both fall with the range. A speed that
        changed along the track is said twice, on average and at its fastest, for an average is no limit, and the most is
        the fastest. Only the speed across the line of sight is bounded: its motion toward or away from the camera is not, as
        for a thing of known size; and the size only where its width is measured or given, for a spot size is no limit
        (`SPOT_SIZE`). The most is None where the camera held the object in view. None where the case has no turn rate, or
        no farthest range."""
        kf = self.stages.get("kinematics", {}).get("fields") or {}
        omega, k, p, how, *_ = self._scaled()
        R = kf.get("range_max_m")
        if omega is None or R is None or self.ranged()[0] is not None:
            return None
        where = f"no farther than the given {_far(R, two=False)}"
        size = f", it is at most about {_two(p * R / k):g} m across" if p and k and how != SPOT_SIZE else ""
        top, fast = kf.get("upper_bound_m_per_s"), kf.get("upper_bound_fastest_m_per_s")
        if top is None:
            return f"{where}{size}; the camera kept it in view, so its speed is not measured here", None
        most = fast or top
        return (f"{where}{size or ', it is'}{', and' if size else ''} moving at most {_two(top):,g} m/s"
                + (f" on average along its path and {_two(fast):,g} m/s at its fastest" if fast else "")
                + " across the line of sight as the camera held it"
                + (f": under the speed of sound (Mach {most / A_SOUND:.2g})" if most < A_SOUND else f" (Mach {most / A_SOUND:.2g})")), most

    def conclusion(self):
        """(label, headline): the one sentence a reader takes away, and how firm it is. The label is
        "Beats like a bird" where its brightness beats at a wingbeat's rate (or a group's members' do: a flock),
        whether or not the track has been checked by eye (Jacob, 2026-10-12: "Anything with a bird wingbeat
        frequency should be reported as 'Flaps like a bird'", and later that day "Beats like a bird");
        "Tentative conclusion" where the track has not
        been checked by eye (the sheet unconfirmed);
        "No conclusion" where nothing was measured about an object, or the measuring was stopped; "No
        physical conclusion" where the object's motion was measured in the picture but cannot become a
        real speed or size, and no bird is named, whatever else the headline says (2026-10-21); "Subsonic
        motion" where a thing of known size puts the speed across the line of sight under the speed of sound
        and no bird is named (Jacob, 2026-10-22: "Knowing the range ratio provides an upper bound on relative
        velocity"), the banner and the report's note saying whether the track has been checked by eye, as
        for a bird; "Indeterminate, range needed" where a field of view gives the turn rate and nothing gives
        a distance or a size, with what a bird, a balloon and a jet would be (`at_each_distance`, the same
        day); with a distance too (`at_the_distance`), "Supersonic motion" where even the speed across the line
        of sight is past the speed of sound, "Indeterminate, angle needed" where it is under it and no angle is
        given, and "Subsonic motion" or "Supersonic motion" where an angle gives the speed itself; with a farthest
        range (`at_the_farthest`), "Subsonic motion" where the most it can be across the line of sight is under the speed
        of sound, as for a thing of known size, and "Indeterminate, range needed" where it is not, for a limit past the
        speed of sound says nothing of the speed; and "Conclusion" otherwise. Written from the stages' fields, as the bottom line is, which
        has the detail under it (Jacob, 2026-10-07: "the tentative conclusion (or lack thereof) at the top")."""
        from .stages import SHEET_PROVISIONAL
        st = lambda name, part: self.stages.get(name, {}).get(part) or {}
        kf, ff, tf = st("kinematics", "fields"), st("flicker", "fields"), st("tether", "fields")
        integ = st("integrity", "result")
        tentative = SHEET_PROVISIONAL in self.notes
        if self.stopped_in():
            return "No conclusion yet", (f"The measuring was stopped {self.stopped_in()}, so the steps after it did not run. "
                                         "Measure again for the rest.")
        if not self.stages:
            return "No conclusion", "No step produced a result."
        if "track" in self.stages and not self.stages["track"]["result"]:
            return "No conclusion", "No object was tracked, so nothing here measures one: the report describes the video."
        rate, against = self.rate()
        speed = kf.get("relative_speed_m_per_s", self._num((st("kinematics", "result") or {}).get("speed_m_s")))
        bar = kf.get("scale_bar_m_per_s")            # from a thing of known size in the picture: no FOV, no range
        bits = []
        here = self.at_the_distance() if speed is not None else None
        limit = self.at_the_farthest() if speed is None else None
        if here is not None:                         # a scale and a distance: its size there, and the least speed
            bits.append(here[0])
        elif speed is not None:
            bits.append(f"the object moved about {speed:.0f} m/s as the camera held it, with the stated range and scale")
        elif limit is not None:                      # a scale and a farthest range: the most its size and speed can be
            bits.append(limit[0])
        elif bar is not None:                        # at the thing's distance (or the ratio's): no faster where it is nearer
            ratio = kf.get("range_ratio")
            bits.append((f"the object moved about {bar:.0f} m/s across the line of sight as the camera held it, at "
                         f"{ratio:g} times the distance of the thing of known size (as given)" if ratio else
                         f"the object moved at most about {bar:.0f} m/s across the line of sight as the camera held it, "
                         "if it is no farther away than the thing of known size")
                        + (f": under the speed of sound (Mach {bar / A_SOUND:.2f})" if bar < A_SOUND else f" (Mach {bar / A_SOUND:.2f})"))
        elif kf.get("omega_rad_per_s") is not None:  # a scale and no distance: what each thing would be, and where
            bits.append(self.at_each_distance())
        elif rate is not None:                       # what is missing is said in the paragraph under it, once
            bits.append(f"the object moved about {rate:.0f} pixels a second {against}"
                        + (f" ({self.HELD_STILL})" if against == "in the picture, as the camera held it" else "")
                        + ", and its real speed and size cannot be found from this video alone")
        beats = own_beats(ff)
        hypothesis = False
        # a bird is named only from a beat that comes back -- the whole track beats, or windows apart agree (the headline
        # rule, Jacob, 2026-10-17); a case from before has no such mark, and its beats came back
        band = lambda b: WINGBEAT_HZ[0] <= b["hz"] <= WINGBEAT_HZ[1]
        loud = lambda b: b.get("amplitude") is None or b["amplitude"] >= BIRD_FLOOR      # a case from before has it
        winged = lambda bs: [b for b in bs if band(b) and loud(b) and not b.get("shaken")]
        back = [b for b in beats.values() if b.get("comes_back", True)]
        beat = next(iter(winged(back)), None) or next(iter(back), None) or next(iter(beats.values()), None)
        flock = winged(back) if len(beats) > 1 else []
        once = [b for b in beats.values() if band(b) and not b.get("comes_back", True)]
        if len(flock) > 1:
            hypothesis = True
            hz = sorted(b["hz"] for b in flock)
            short = len(ff.get("short") or [])             # members seen too briefly for a beat (PR135's, after the jump)
            measured = max(len(ff.get("beat") or {}), len(beats))     # members measured, whether or not their beat passed
            who = f"its {measured} members" if len(flock) == measured else f"{len(flock)} of its {measured} members"
            bits.insert(0, f"a flock of birds is the leading explanation: {who} each beat at "
                           f"{hz[0]:.1f}–{hz[-1]:.1f} Hz, the rate of a wingbeat, each its own and out of step with the others "
                           "(a rhythm of the video would beat them as one; tumbling bodies or blinking lights would beat too"
                           + (f"; {short} more {'was' if short == 1 else 'were'} seen too briefly to tell" if short else "") + ")")
        elif beat and beat.get("shaken"):             # the camera's own shake sits at it (flicker's item 17; agent aot, 2026-10-31)
            bits.append(f"its brightness beats at {beat['hz']:.1f} Hz, but the whole picture shakes at that rate by "
                        f"{beat['shaken']['px']:.2g} pixels, so the camera may make it, and no bird is named")
        elif beat and beat.get("comes_back", True) and band(beat) and loud(beat):
            hypothesis = True
            bits.insert(0, f"a bird is the leading explanation: its brightness beats at {beat['hz']:.1f} Hz"
                           + (f" (and at {beat['double_hz']:.1f} Hz, {_double_said(beat['hz'], beat['double_hz'])})" if beat.get("double_hz") else "")
                           + ", the rate of a wingbeat, a rhythm of its own and not the video's (a tumbling body or a blinking "
                           "light would beat too, and nothing here tells them apart)")
        elif once:                                    # at a wingbeat's rate, but in one stretch: too little to name a bird
            b = once[0]
            bits.append(f"its brightness beats at {b['hz']:.1f} Hz for one stretch, frames {b['first']}–{b['last']}, and not "
                        "elsewhere along its track: a rhythm of its own there, but too little to name a bird")
        elif beat and band(beat) and not loud(beat):  # a wingbeat's rate, but no stronger than false calls on aircraft beat
            bits.append(f"its brightness beats at {beat['hz']:.1f} Hz, a rhythm of its own and not the video's, but by only "
                        f"{100 * beat['amplitude']:.1f} % of its brightness: under the {100 * BIRD_FLOOR:.0f} % that the false "
                        "calls on known aircraft, drones and helicopters stay under, so too faint to name a bird")
        elif beat and not beat.get("comes_back", True):  # under a wingbeat's rate, and one stretch all the same (a Galileo airliner's 1.7 Hz)
            bits.append(f"its brightness beats at {beat['hz']:.1f} Hz for one stretch, frames {beat['first']}–{beat['last']}, and "
                        "not elsewhere along its track: a rhythm of its own there")
        elif beat:
            bits.append(f"its brightness beats at {beat['hz']:.1f} Hz, a rhythm of its own and not the video's")
        # something that only moves with it is the bottom line's, where it is said how far and at what angle (Jacob,
        # 2026-10-22, PR149's faint dark spot: "leave it out of the headline, it is confusing"); a pendulum is a finding
        if tf.get("companion") and (tf.get("swing") or {}).get("swings"):
            bits.append("something moves with it, swinging like a pendulum")
        if integ.get("object_verdicts"):
            flagged = [k for k, v in integ["object_verdicts"].items() if v == "FLAG"]
            bits.append(f"{len(flagged)} integrity test{'s' if len(flagged) != 1 else ''} flag it ({', '.join(flagged)})" if flagged
                        else "it behaves like imagery from this sensor chain")
        if not bits and tf.get("companion"):         # all there is: said, rather than "nothing was measured"
            bits.append("something moves with it")
        if not bits:
            return "No conclusion", "Nothing was measured about the object."
        head = "; ".join(bits)
        head = head[0].upper() + head[1:] + "."
        if hypothesis:
            return BIRD, head
        # a speed on the screen and no m/s is no physical conclusion, whatever the headline says beside it: a companion,
        # a beat no bird's, integrity's reading (Jacob, 2026-10-21, PR149's "something moves with it" had made it tentative)
        if limit is not None and limit[1] is not None and limit[1] < A_SOUND:   # a limit under it: as a thing of known size's
            return SUBSONIC, head
        if speed is None and bar is None and kf.get("omega_rad_per_s") is not None:
            return INDETERMINATE, head
        if here is not None and here[1] is not None:  # a scale and a distance, and the camera did not hold it
            _, least, full = here
            if full is not None:
                return (SUBSONIC if full < A_SOUND else SUPERSONIC), head
            return (SUPERSONIC if least >= A_SOUND else ANGLE_NEEDED), head
        if speed is None and bar is None and rate is not None:
            return "No physical conclusion", head
        if speed is None and bar is not None and bar < A_SOUND:
            return SUBSONIC, head
        return ("Tentative conclusion" if tentative else "Conclusion"), head

    @staticmethod
    def flame_said(flame, several, gf):
        """The bottom line's sentence for beats inside a flame's band (FLAMES): a sky lantern's flame puffs at 4.7-8.7 Hz,
        a bundle of candles flickers near 10, each with its own phase, so neither the beat nor the members being out of
        step tells a flame from a wingbeat. What can, here, is the group (`groups`' `rigid`): lanterns let go together
        drift on one wind and keep their places; a flock rearranges (PR135's six: 16 px, against 0.1 for a drone show).
        For one object, or a group whose rigidity was not read, the sentence says that nothing here decides it."""
        hz = ", ".join(f"{b['hz']:.1f}" for b in flame)
        s = (f"{'Those beats' if len(flame) > 1 else 'That beat'} ({hz} Hz) {'are' if len(flame) > 1 else 'is'} also where a "
             "flame flickers -- a sky lantern's puffs at 4.7–8.7 Hz, a bundle of candles near 10 -- with a phase of its own, so "
             + ("being out of step does not tell a flame from a wingbeat. " if several else "the beat does not tell a flame from a wingbeat. "))
        rigid = (gf or {}).get("rigid") if (gf or {}).get("several") else None
        if rigid is False:
            return s + "The group does not keep its shape: a flock rearranges, and lanterns drifting on one wind would keep their places."
        if rigid is True:
            return s + "The group keeps its shape, as lanterns drifting on one wind would: a flame is not excluded here."
        return s + ("Whether the group keeps its shape was not read, and nothing else here decides it." if several else
                    "Nothing here decides it for one object: its height, its heat and its drift with the wind would.")

    @staticmethod
    def rotor_said(rotor, several):
        """The bottom line's sentence for a beat with a rotor's look (flicker's item 14): it reaches the background beside
        the object in step, or the light that beats sits off its middle. Said beside the headline, as the flame's is; it
        changes no call, for its thresholds were chosen on the helicopters it was found on."""
        from .flicker import rotor_said as words
        bits = [(name.capitalize() + ": " if several else "") + words(r) for name, r in rotor]
        s = "; ".join(bits)
        return (s[0].upper() + s[1:] + ". In a labelled infrared set, 6 of 8 helicopters whose beat would have named a bird showed "
                "this, and 1 of 50 birds; it is a reading beside the headline, not a test, until it is held to helicopters it was "
                "not chosen on.")

    @staticmethod
    def blink_said(lights, several):
        """The bottom line's sentence for a light that flashes in a train (flicker's item 13): the rate, what flashes at it
        (an aircraft's anti-collision light, 40-100 times a minute; to 180 where two lights' beams overlap), and whether the
        beat is the flashes'. A glint off something that turns flashes too, so the sentence says so; it is a reading
        beside the headline, as the flame's is."""
        bits = []
        for name, k in lights:
            word = {"brightness": "brightness", "white": "hottest pixels" if k.get("black_hot") else "brightest pixels",
                    "red": "reddest pixels"}.get(k.get("best"), "brightness")
            verb = "flashes" if word == "brightness" else "flash"
            bits.append(f"{'Its' if not several else name.capitalize() + chr(39) + 's'} {word} {verb} in a regular train, {k['flashes']} flashes at "
                        f"{k['hz']:.2f} Hz ({k['per_minute']:.0f} a minute)"
                        + (": the rate an aircraft's anti-collision light must flash at (40–100 a minute)" if k.get("rule") == "anti-collision" else
                           ": faster than one anti-collision light may flash, within the 180 a minute allowed where two lights' beams overlap"
                           if k.get("rule") == "overlap" else "")
                        + (f"; its beat keeps {k['beat_kept']:.0%} of its amplitude without the flashes, so the beat is the flashes'"
                           if k.get("marked") else ""))
        return ". ".join(bits) + ". A glint off something that turns flashes too, at the rate it turns."

    def bottom_line(self):
        """Assembled from the stages, and deliberately hedged where it must be.

        Read from the stages' fields, which are numbers; a case put together by hand with
        only `result` strings is still read, through `_num`. A rate is called the object's
        only where a stage measured the object: the look at the background that `run`
        takes without a track (`layers.glance`) is the scene's motion, and an earlier
        version of this paragraph printed it as "The object moves ..."."""
        L = []
        st = lambda name, part: self.stages.get(name, {}).get(part) or {}
        kin, kf = st("kinematics", "result"), st("kinematics", "fields")
        lf = st("layers", "fields")
        com = st("comotion", "result")
        integ = st("integrity", "result")

        if "track" in self.stages and not self.stages["track"]["result"]:
            L.append("No object was tracked, so nothing here measures one: what follows describes the clip.")
        if self.stopped_in():
            L.append(f"**The measuring was stopped {self.stopped_in()}, so the steps after it did not run.** "
                     "Measure again to get the rest.")

        names = lf.get("names") or {}
        per = lf.get("px_per_s") or {}
        against = {names.get(c, c): per[c]["median"] for c in ("striated", "isotropic") if per.get(c)} if lf.get("tracked") else {}
        v = kf.get("v_px_per_s", self._num(kin.get("v_px")))
        not_uniform = (not kf["uniform"]) if "uniform" in kf else str(kin.get("uniform_motion", "")).startswith("NO")
        still = self.behind_held_still()
        if against:
            L.append("The object moves " + ", and ".join(f"{r:.0f} px/s against the {n}" for n, r in against.items())
                     + " (medians over one-second windows of wall-clock time)." + (f" {self.held_still_said()}" if still else ""))
            if len(against) > 1:
                L.append("Those are different numbers because the background is not one "
                         "surface; quoting either as *the* rate would name neither layer.")
        elif lf.get("tracked") and per.get("all"):
            L.append(f"The object moves {per['all']['median']:.0f} px/s against the scene's largest motion group "
                     "(median over one-second windows); the texture classes could not be told apart."
                     + (f" {self.held_still_said()}" if still else ""))
        elif v is not None and not not_uniform:
            band = kf.get("band") or {}
            L.append(f"The object moves {v:.0f} px/s in the image"
                     + (f" (between {band['v_min'][1]:.0f} and {band['v_max'][1]:.0f} px/s along the track: the speed band, "
                        f"from the track's own covariance, is ±{band['band_err_px_per_s']:.0f} px/s)."
                        if band and not band["constant"] else
                        f" (constant within ±{band['band_err_px_per_s']:.0f} px/s, the speed band"
                        + (f"; {bound_said(band['change_bound'])}" if band.get("change_bound") else "") + ")." if band else "."))
        elif v is not None:
            band = kf.get("band") or {}
            if band and not band["constant"]:
                L.append(f"The object's speed in the image changed: from {band['v_start'][1]:.0f} px/s at {band['v_start'][0]:.1f} s "
                         f"to {band['v_end'][1]:.0f} at {band['v_end'][0]:.1f} s (least {band['v_min'][1]:.0f}, most "
                         f"{band['v_max'][1]:.0f}); it ran {path_said(band)}; its velocity changed by "
                         f"{pm(band['dv_px_per_s'], band['dv_err_px_per_s'])} px/s "
                         f"({band['turn_deg']:.0f}° of direction). A straight-line fit's {v:.0f} px/s is **not** a rate it held "
                         "({}).".format(kin.get("fit_residual", "large residual")))
            else:
                L.append(f"A straight-line fit to the track gives {v:.0f} px/s, but the motion "
                         "is **not uniform** ({}), so that figure does not describe it."
                         .format(kin.get("fit_residual", "large residual")))

        speed = kf.get("relative_speed_m_per_s", self._num(kin.get("speed_m_s")))
        missing = kf.get("missing", kin.get("missing"))
        bar, ref = kf.get("scale_bar_m_per_s"), st("scale", "fields").get("reference") or {}
        here = self.at_the_distance() if speed is not None else None
        limit = self.at_the_farthest() if speed is None else None
        if here is not None and here[1] is not None and here[2] is None:   # no angle: omega R is the least it can be
            L.append(f"With the stated scale and range it moves {here[1]:.0f} m/s across the line of sight (Mach "
                     f"{here[1] / A_SOUND:.2f}): the least its speed as the camera held it can be, since its motion "
                     "toward or away from the camera is not measured; an angle or a range rate would give it. It is a "
                     "*relative* speed, which already includes the platform's own motion.")
        elif speed is not None:
            L.append(f"With the stated scale and range that is {speed:.0f} m/s "
                     f"relative to the platform — a *relative* speed, which already includes "
                     "the platform's own motion.")
        if here is not None and max(here[1] or 0, here[2] or 0) >= A_SOUND:
            L.append("Faster than sound relative to the platform is not faster than sound through the air: two aircraft "
                     "meeting head-on can pass it between them.")
        elif limit is not None:                      # the conclusion's words as a limit: what it bounds, and what it does not
            _, k, p, how, *_ = self._scaled()
            R = kf["range_max_m"]
            firm = p and k and how != SPOT_SIZE
            size = f" and is at most {_two(p * R / k):g} m across ({p:.0f} px: {how})" if firm else ""
            fast = kf.get("upper_bound_fastest_m_per_s")
            L.append(("The camera kept it in view, so its speed is not measured here" + (f"; it is at most {_two(p * R / k):g} m "
                      f"across at the farthest range given ({p:.0f} px: {how})." if firm else ".")) if limit[1] is None else
                     f"With the stated scale, and nothing beyond {_far(R, two=False)}, it moves at most "
                     f"{_two(kf['upper_bound_m_per_s']):,g} m/s" + (f" on average along its path and {_two(fast):,g} m/s at its fastest" if fast else "")
                     + f" across the line of sight{size}: " + ("both fall with the range, so a nearer object is slower and smaller. " if firm else
                     "that falls with the range, so a nearer object is slower. ")
                     + "That is an upper bound, and it leaves two things out. Its motion toward or away from the camera is not measured. And the "
                     "rate is the one in the picture, against the line of sight as the camera held it: if the camera was turning to "
                     "hold the ground at that range, this is its speed over the ground only at that range, and a nearer object "
                     "showing the same rate has more of the platform's own speed across the line of sight in it, up to all of it."
                     + ("" if firm or not (p and k) else f" No limit on its size: {p:.0f} px is {how}, not a width measured; its width in "
                        "pixels (--size-px) would give one."))
        elif bar is not None:
            said = f" ({ref['length_m']:g} m over {ref['px']:g} px)" if ref.get("length_m") and ref.get("px") else ""
            L.append(f"With the thing of known size{said} that is {bar:.0f} m/s across the line of sight "
                     + (f"at {kf['range_ratio']:g} times its distance, as given." if kf.get("range_ratio") else
                        "if the object is as far away as that thing: less if it is nearer, more if it is farther. "
                        "No field of view or range is needed for it.")
                     + " It is a *relative* speed, which already includes the platform's own motion.")
            if bar < A_SOUND:                         # the conclusion's "Subsonic motion": the bound, and what it leaves out
                L.append("That is an upper bound, as in the JAIS Technical Note: where the object is no farther away "
                         + (f"than {kf['range_ratio']:g} times that thing's distance" if kf.get("range_ratio") else "than that thing")
                         + f", it moves across the line of sight at no more than Mach {bar / A_SOUND:.2f}, under the speed of "
                         "sound. Its motion toward or away from the camera is not measured.")
        elif v is not None and (missing or kf.get("omega_rad_per_s") is not None):
            if kf.get("omega_rad_per_s") is not None:   # the headline's bird, balloon and jet: what they rest on
                p, how = self.extent()
                k, (r, against) = st("scale", "fields").get("k_px_per_rad"), self.rate()
                sq, a = kf.get("square_per_px") or 1.0, st("scale", "fields").get("pixel_aspect") or 1.0
                om = r * sq / k if r is not None and k else kf["omega_rad_per_s"]
                L.append(f"With the scale that is {om:.2f} rad/s {against or 'in the image'}, so at a distance of R meters it moves "
                         + (f"{om:.2f} R m/s across the line of sight relative to the camera's pointing, which held a still picture "
                            "(its motion against the background is not measured, so this is no floor on its speed)"
                            if self.behind_held_still() else
                            f"at least {om:.2f} R m/s across the line of sight as the camera held it")
                         + (f", and is {p:.0f}/{k:.0f} R m across ({p:.0f} px: {how}). " if p and k and a == 1.0 else
                            f", and is {p / a:.0f}–{p:.0f}/{k:.0f} R m across ({p:.0f} px in the file's pixels: {how}). " if p and k else
                            "; its size in the picture is not known. ")
                         + "The first line puts a bird, a weather balloon and a fighter jet where their sizes would be; "
                         "a distance from another source would say which, if any, it is.")
                if a != 1.0:                            # the stretch, where it came from, and the rate both ways (section 40)
                    fps = kf.get("fps") or (self.clip or {}).get("fps") or 1.0
                    L.append(f"The picture's pixels are drawn {a:.4g} times wider than tall ({st('scale', 'fields').get('pixel_aspect_from') or 'given'}), "
                             f"so the scale is read up the picture ({k * math.pi / 180:.1f} px/deg; {k * a * math.pi / 180:.1f} across), and the "
                             f"track's rate, {v / fps:.1f} px/frame in the file's own pixels, is {(kf.get('v_square_px_per_s') or v * sq) / fps:.1f} "
                             "px/frame in square pixels along its own direction, which is what the scale turns into an angle.")
            if missing:
                L.append("It does not convert to a physical speed: " +
                         ", ".join(missing) + " " +
                         ("are" if len(missing) > 1 else "is") + " not available from this clip.")

        sv = self.survives()
        if sv.get("turn") or sv.get("constant velocity") or sv.get("time to contact") or sv.get("what the clip allows"):
            bits = [sv[k][0].upper() + sv[k][1:] + "." for k in ("turn", "constant velocity", "time to contact", "what the clip allows")
                    if sv.get(k)]
            L.append("Without a range, a field of view or the platform's speed, the track itself says this. " + " ".join(bits))

        ff = st("flicker", "fields")
        beats = own_beats(ff)
        beat = next(iter(beats.values()), None)
        if len(beats) > 1:
            measured = max(len(ff.get("beat") or {}), len(beats))
            who = f"Its {measured}" if measured == len(beats) else f"{len(beats)} of its {measured}"
            L.append(f"{who} members beat at " + ", ".join(f"{b['hz']:.1f}" for b in beats.values())
                     + " Hz, each its own and out of step with the others: a rhythm of the video would beat them as one.")
        elif beat:
            L.append(f"Its brightness beats at {beat['hz']:.1f} Hz"
                     + (f" (and at {beat['double_hz']:.1f} Hz, {_double_said(beat['hz'], beat['double_hz'])})" if beat.get("double_hz") else "")
                     + (f" for one stretch, frames {beat['first']}–{beat['last']}" if not beat.get("comes_back", True) else "")
                     + (f": the whole picture shakes at that rate too, by {beat['shaken']['px']:.2g} pixels, so it may be the camera's."
                        if beat.get("shaken") else ": the object's own, not the video's."))
        flame = [b for b in beats.values() if any(d.get("source") in FLAMES for d in b.get("lookalike") or [])]
        if flame:                                            # flicker's item 11: a flame is a look-alike the beat cannot clear
            L.append(self.flame_said(flame, len(beats) > 1, st("groups", "fields")))
        rotor = [(n, b["rotor"]) for n, b in beats.items() if (b.get("rotor") or {}).get("marked")]
        if rotor:                                            # flicker's item 14: a beat that reaches past the body
            L.append(self.rotor_said(rotor, len(beats) > 1))
        lights = [(n, k) for n, k in (ff.get("blink") or {}).items() if k.get("train") and not k.get("shared")]
        if lights:                                           # flicker's item 13: a light that flashes in a train
            L.append(self.blink_said(lights, len(ff.get("blink") or {}) > 1))

        tf = st("tether", "fields")
        if tf.get("fellow_member"):
            c = tf["fellow_member"]
            L.append(f"The {c['sign']} feature {c['r_over_size']:.1f} object sizes away that moves with it is {c['member']} of "
                     "the group it is in, not something tied to it.")
        if tf.get("companion"):
            c, sw = tf["companion"], tf.get("swing") or {}
            L.append(f"Something moves with it: a {c['sign']} feature {c['r_over_size']:.1f} object sizes away, "
                     f"{c['direction_deg']:+.0f}° from straight down"
                     + (f", swinging with a period of {sw['period_used_s']:.2f} s -- a pendulum of {sw['line_length_m']:.2f} m"
                        + (" (tentative: under two cycles)" if sw.get("tentative") else "") if sw.get("swings")
                        else (", at a steady angle (no swing, so no length)" if sw.get("swings") is False else "")) + ".")

        if com.get("verdict"):
            rel = self._num(com.get("rel_D", 0)) or 0.0
            L.append(f"Against the texture immediately around it the object is "
                     f"**{com['verdict']}** ({rel:.1f} object diameters).")

        if integ.get("object_verdicts"):
            flagged = [k for k, v in integ["object_verdicts"].items() if v == "FLAG"]
            passed = [k for k, v in integ["object_verdicts"].items() if v == "PASS"]
            if flagged:
                L.append(f"Integrity: **{len(flagged)} test{'s' if len(flagged) != 1 else ''} FLAG** ({', '.join(flagged)}).")
            elif passed:
                L.append(f"Integrity: {len(passed)} test{'s pass' if len(passed) != 1 else ' passes'} and none flag; the object "
                         "behaves like imagery from this sensor chain.")
        np_total = sum(len(s["no_power"]) for s in self.stages.values())
        if np_total:
            L.append(f"{np_total} test{'s' if np_total != 1 else ''} had no power on this clip (under Measurements); "
                     "a test that cannot decide has not passed.")
        return " ".join(L) or "No stage produced a result."

    def checklist(self):
        """Each test the report rests on, as a question in plain words (CHECKS), its answer in a word (ANSWERS) and why
        in a line: [dict(key, test, answer, said, stage)], in a fixed order -- the video, the camera, the object's motion,
        its brightness, its company, whether it was added, whether a real speed follows, and the person's part. Read from
        the stages' fields, as the conclusion and the bottom line are, so a case file from before has one too, and the
        window's card reads the same rows. A test whose stage did not run has no row: the table says nothing it did not
        check. A test that could not decide answers "Can't tell" (the package's third rule) -- the camera's row wherever
        the picture behind the object held still on screen, which is the layers step's no-power and not a still camera
        -- and a bend or a change of speed on a camera that moved says so, since the picture's motion is then partly
        the camera's."""
        st = lambda name, part="fields": self.stages.get(name, {}).get(part) or {}
        npw = lambda name: next((w for _, w in (self.stages.get(name, {}).get("no_power") or [])), None)
        rows = []
        add = lambda key, stage, answer, said: rows.append(dict(key=key, test=CHECKS[key], answer=answer, said=said, stage=stage))

        # the video: what the survey found of its frames
        if "survey" in self.stages:
            sv = st("survey")
            rep = int(sv.get("repeated_frames") or 0)
            tr = sv.get("transients") or []
            n_tr = len(tr) if isinstance(tr, (list, tuple)) else int(tr or 0)
            found = ([f"{rep} repeated frame{'s' if rep != 1 else ''}"] if rep else []) + \
                    ([f"{n_tr} sudden change{'s' if n_tr != 1 else ''} of brightness"] if n_tr else [])
            add("video", "survey", YES if found else NO,
                " and ".join(found) + (": a step between two frames is not always a frame's worth of motion" if rep else "")
                if found else "every frame is new, and the brightness holds")

        # the camera: whether the background moved across the screen (the layers check, over about a second). A picture
        # that held still on screen is the step's own no-power, not a still camera: a camera following the object over a
        # sky with nothing to read and a camera held still over a slow scene both hold a match at zero, and the step
        # cannot tell them apart (`behind_held_still`; the first line's "as the camera held it"). So the row answers
        # "Can't tell" there, in the first line's words, and never "No": the step has no reading that says a scene was
        # read and held (0.4.1 answered "No" from the held-still share, on ten of the fourteen reference cases, where
        # its own first line said the camera's motion was not measured; 2026-11-02). The step's rule is its no-power
        # above half the pairs; the share is read too, for a case file written before that no-power had its words.
        hs = st("layers").get("held_still") or {}
        still = hs.get("still_again_share") if hs.get("share_of_pairs") is not None else None
        held = self.behind_held_still() or (still is not None and still > 0.5)
        camera_still, camera_moved = still is not None and still >= 0.9, still is not None and still <= 0.1
        if still is not None:
            longer = hs.get("again_over_frames") or hs.get("over_frames")
            zooms = [z for z in (st("camera").get("zoom_steps") or []) if z.get("applied", True)]
            zoom = ("; the picture zoomed " + {1: "once", 2: "twice"}.get(len(zooms), f"{len(zooms)} times")) if zooms else ""
            both = "a camera following it over an empty sky and a still camera over a slow scene both give"
            if held and camera_still:
                add("camera", "layers", CANT, f"the picture behind the object held still on screen (in {still:.0%} of the frame pairs, even over "
                                              f"{longer} frames), which {both}, so whether the camera moved is not measured" + zoom)
            elif held:
                add("camera", "layers", CANT, f"the picture behind the object held still on screen in {still:.0%} of the frame pairs and moved across "
                                              f"it in the rest; {both} the held pairs, so how much the camera moved is not measured" + zoom)
            elif camera_moved:
                add("camera", "layers", YES, f"the background moved across the picture in {1 - still:.0%} of the frame pairs (over {longer} frames)" + zoom)
            else:
                add("camera", "layers", PARTLY, f"the picture held still in {still:.0%} of the frame pairs over {longer} frames, and moved in the rest" + zoom)
        elif "layers" in self.stages and npw("layers"):
            add("camera", "layers", CANT, "the background could not be followed: too little texture in it, or too few frames")

        # the object's motion
        rate, against = self.rate()
        kf = st("kinematics")
        if rate is not None:
            if against == "in the image" and camera_moved:
                add("moves", "kinematics", CANT, f"it moves about {rate:.0f} pixels a second across the picture, but so did the background, "
                                                 "and its rate against the background was not measured")
            else:
                where = ("against the background" if against == "against the background" else
                         "across the picture, which held still" if camera_still else "across the picture")
                add("moves", "layers" if against == "against the background" else "kinematics", YES if round(rate) else NO,
                    f"about {rate:.0f} pixels a second {where}" if round(rate) else f"under half a pixel a second {where}")
        band, pj, tn = kf.get("band") or {}, kf.get("projective") or {}, kf.get("turn") or {}
        if kf.get("fit"):
            if band.get("constant") is None:
                n = (kf.get("fit") or {}).get("n")
                add("straight", "kinematics", CANT, f"only {n} frames: too few to tell" if n else "too few frames to tell")
            else:
                bends, loops = bool(tn.get("turned")), tn.get("how") == "ellipse"
                path = ("it loops" if loops else "its path bends" if bends else "its path is a hair off straight" if tn.get("bent")
                        else "its path is straight" if tn else "")
                camera = " (the camera moved, so some of this may be its motion)" if camera_moved else ""
                if band["constant"] and not bends and not loops:
                    add("straight", "kinematics", YES, f"its speed held to within ±{band['band_err_px_per_s']:.0f} pixels a second"
                                                       + (f", and {path}" if path else ""))
                elif band["constant"]:
                    add("straight", "kinematics", NO, f"its speed held, but {path}"
                                                      + (f" (a turn of about {tn['r_turn_over_D']:,.0f} body widths)" if bends and not loops else "") + camera)
                else:
                    add("straight", "kinematics", NO, f"its speed ran from {band['v_min'][1]:.0f} to {band['v_max'][1]:.0f} pixels a second"
                                                      + (f", and {path}" if bends or loops else f", though {path}" if path else "") + camera)
        ta, tr = self.tau(), self.tau_reading()
        dep = pj.get("depth")
        if ta:
            t = ta["tau_s"]
            add("closing", "flicker" if ta.get("from") == "looming" else "kinematics", YES,
                f"coming closer: its size grows along the track as a straight approach would; it would reach the camera's distance "
                f"about {abs(t):.1f} s after its last frame" if t > 0 else
                f"going away: its size shrinks along the track as a straight retreat would; it was at the camera's distance about "
                f"{abs(t):.1f} s before its last frame")
        elif pj.get("closing") is True and pj.get("fits"):
            add("closing", "kinematics", YES, f"its path fits a straight approach: it would reach the camera's distance about {abs(pj['T']):.1f} s "
                                              "after its last frame" if pj["T"] > 0 else
                                              f"its path fits a straight retreat: it was at the camera's distance about {abs(pj['T']):.1f} s before its first frame")
        elif dep and pj.get("closing") is False and pj.get("fits"):
            add("closing", "kinematics", NO, f"not by more than {pct(dep['rate_max_per_s'])} of its distance a second, if it flew straight at a steady "
                                             "speed, which its track fits")
        elif tr and tr.get("why"):
            why = tr["why"]
            add("closing", "flicker", CANT, "its size held along the track, so no approach or retreat shows in it" if why.startswith("its size held") else
                                            "its size could not be read on enough frames to say" if "was read on" in why else
                                            "it is too small in the picture for its size to say" if "its size is its blur's" in why else
                                            "its size changed too little along the track to say" if "a fit needs" in why else plainer(why))
        elif pj:
            add("closing", "kinematics", CANT, f"its path fits a straight line at a steady speed only roughly (to {trend_px(pj)} pixels), so "
                                               "its approach cannot be read from it" if pj.get("fits") is False else
                                               "its path does not fit a straight line at a steady speed, so its approach cannot be read from it")

        # its brightness: the beat, what else could beat so, and a train of flashes
        ff = st("flicker")
        if "flicker" in self.stages:
            beats = own_beats(ff)
            in_band = lambda b: WINGBEAT_HZ[0] <= b["hz"] <= WINGBEAT_HZ[1]
            loud = lambda b: b.get("amplitude") is None or b["amplitude"] >= BIRD_FLOOR
            winged = [b for b in beats.values() if in_band(b) and loud(b) and not b.get("shaken") and b.get("comes_back", True)]
            beat = next(iter(winged), None) or next(iter(beats.values()), None)
            own = []                                     # the beats the look-alike row is about: said to be the object's own
            if len(beats) > 1 and len(winged) > 1:
                hz = sorted(b["hz"] for b in winged)
                measured = max(len(ff.get("beat") or {}), len(beats))
                add("beat", "flicker", YES, f"{len(winged)} of its {measured} members each beat at {hz[0]:.1f}–{hz[-1]:.1f} times a second, "
                                            "each its own rhythm and out of step with the others")
                own = winged
            elif beat and beat.get("shaken"):
                add("beat", "flicker", CANT, f"it beats at {beat['hz']:.1f} times a second, but the whole picture shakes at that rate too, "
                                             "so the camera may make it")
            elif beat and beat.get("comes_back", True) and in_band(beat) and loud(beat):
                add("beat", "flicker", YES, f"{beat['hz']:.1f} times a second, the rate of a wingbeat: its own rhythm, not the video's")
                own = [beat]
            elif beat and in_band(beat) and not beat.get("comes_back", True):
                add("beat", "flicker", PARTLY, f"{beat['hz']:.1f} times a second in one stretch only, frames {beat['first']}–{beat['last']}, "
                                               "and not along the rest of its track")
                own = [beat]
            elif beat and in_band(beat):
                add("beat", "flicker", PARTLY, f"{beat['hz']:.1f} times a second, but by only {beat['amplitude']:.0%} of its brightness, under the "
                                               f"{BIRD_FLOOR:.0%} that false alarms on aircraft stay under")
                own = [beat]
            elif beat:
                add("beat", "flicker", NO, f"it beats at {beat['hz']:.1f} times a second, {'slower' if beat['hz'] < WINGBEAT_HZ[0] else 'faster'} "
                                           f"than a wingbeat ({WINGBEAT_HZ[0]:g}–{WINGBEAT_HZ[1]:g} a second)")
            elif ff.get("beats") is False or (ff.get("beat") and not beats):
                add("beat", "flicker", NO, "no rhythm of its own stands out above the background beside it")
            elif npw("flicker"):
                add("beat", "flicker", CANT, plainer(npw("flicker")))
            if own:
                flame = any(d.get("source") in FLAMES for b in own for d in b.get("lookalike") or [])
                rotor = any((b.get("rotor") or {}).get("marked") for b in own)
                add("lookalike", "flicker", YES, "a tumbling body or a blinking light would beat too"
                    + ("; a sky lantern's flame puffs at this rate as well" if flame else "")
                    + ("; the beat reaches past its body, as a rotor's does" if rotor else "") + ": nothing here tells them apart")
            blinks = ff.get("blink") or {}
            if blinks:
                trains = [k for k in blinks.values() if k.get("train") and not k.get("shared")]
                if trains:
                    k = trains[0]
                    add("flash", "flicker", YES, f"{k['flashes']} flashes at {k['per_minute']:.0f} a minute"
                        + (", the rate of an aircraft's anti-collision light" if k.get("rule") == "anti-collision" else
                           ", within what two overlapping anti-collision lights may flash at" if k.get("rule") == "overlap" else "")
                        + "; a glint off something that turns flashes too")
                else:
                    add("flash", "flicker", NO, "no regular train of flashes")

        # its company: a group, a thing tied to it, the texture round it
        gf = st("groups")
        if gf.get("several") is not None:
            if gf["several"]:
                n = gf.get("members_followed") or gf.get("member_tracks")
                add("single", "groups", NO, f"{n} things move together" if n else "several things move together"
                    + (", keeping their places as the parts of one body would" if gf.get("rigid") is True else
                       ", changing places as a flock does" if gf.get("rigid") is False else ""))
            else:
                add("single", "groups", YES, "one point on most frames; nothing moves with it as a group")
        tt = st("tether")
        if tt.get("fellow_member"):
            c = tt["fellow_member"]
            add("with", "tether", YES, f"a {c['sign']} thing {c['r_over_size']:.1f} object widths away: a fellow member of its group, not something tied to it")
        elif tt.get("companion"):
            c, sw = tt["companion"], tt.get("swing") or {}
            period = sw.get("period_used_s") or sw.get("period_s")
            add("with", "tether", YES, f"a {c['sign']} thing {c['r_over_size']:.1f} object widths away moves with it"
                + (f", swinging with a period of {period:.1f} s like a pendulum {sw['line_length_m']:.2f} m long"
                   + (" (tentative: under two cycles)" if sw.get("tentative") else "") if sw.get("swings") and period and sw.get("line_length_m") else
                   ", at a steady angle (no swing)" if sw.get("swings") is False else ""))
        elif tt.get("finding"):
            add("with", "tether", NO, f"nothing within {tt.get('r_max') or 40:.0f} object widths keeps step with it")
        elif "tether" in self.stages and npw("tether"):
            add("with", "tether", CANT, "too few frames of the track to look" if "frames" in npw("tether") else plainer(npw("tether")))
        com = st("comotion", "result")
        if com.get("verdict"):
            v, rel = com["verdict"], self._num(com.get("rel_D", 0)) or 0.0
            if v == "NO POWER":
                add("through", "comotion", CANT, "no frame pair gave both its position and the motion of the texture round it")
            else:
                add("through", "comotion", YES if v == "MOVES THROUGH" else NO if v == "CARRIED" else CANT,
                    f"it moves {rel:.1f} of its own widths relative to the texture round it"
                    + (": within its own width, so carried with it" if v == "CARRIED" else
                       ": through it, not locked to any feature of it" if v == "MOVES THROUGH" else
                       ": more than nothing, but not clearly beyond the texture's own shear"))

        # whether it was added: the integrity tests on the object
        iv = st("integrity", "result").get("object_verdicts") or {}
        if iv:
            flagged = [k for k, v in iv.items() if v == "FLAG"]
            passed = [k for k, v in iv.items() if v == "PASS"]
            if flagged:
                add("added", "integrity", YES, f"{len(flagged)} of the {len(iv)} checks say it behaves like something laid over the picture: "
                                               + ", ".join(flagged))
            elif passed:
                add("added", "integrity", NO, f"{len(passed)} of the {len(iv)} checks could decide on this video, and "
                                              f"{'it passes' if len(passed) == 1 else 'all pass'}; the rest could not")
            else:
                add("added", "integrity", CANT, f"none of the {len(iv)} checks could decide on this video")

        # a real speed: what the four unknowns allow
        if kf.get("fit") or rate is not None:
            speed, lb, bar = kf.get("relative_speed_m_per_s"), kf.get("lower_bound_m_per_s"), kf.get("scale_bar_m_per_s")
            top, om, R = kf.get("upper_bound_m_per_s"), kf.get("omega_rad_per_s"), kf.get("range_m")
            ledger = {r["symbol"]: r for r in self.ledger()}
            guess = " (the field of view is a guess, so this is too)" if (ledger.get("k") or {}).get("status") == "assumed" else ""
            p, k = self.extent()[0], st("scale").get("k_px_per_rad")
            size = f", and about {p * R / k:.1f} m across" if speed is not None and p and k and R else ""
            if speed is not None:
                add("real", "kinematics", YES, f"about {speed:.0f} m/s relative to the camera, with the distance and the scale given" + size + guess)
            elif lb is not None:
                add("real", "kinematics", PARTLY, f"at least {lb:.0f} m/s across the line of sight at the given distance; its motion toward or "
                                                  "away from the camera is not measured" + guess)
            elif bar is not None:
                ratio = kf.get("range_ratio")
                add("real", "kinematics", PARTLY, f"about {bar:.0f} m/s across the line of sight, at {ratio:g} times the distance of the thing of "
                                                  "known size (as given)" if ratio else
                                                  f"at most about {bar:.0f} m/s across the line of sight, if it is no farther away than the thing of known size")
            elif top is not None and kf.get("range_max_m"):
                add("real", "kinematics", PARTLY, f"at most {_two(top):,g} m/s across the line of sight, with nothing beyond "
                                                  f"{_far(kf['range_max_m'], two=False)}" + guess)
            elif om is not None:
                add("real", "kinematics", PARTLY, f"the field of view gives how fast it crosses the view, about {math.degrees(om):.0f}° a second; "
                                                  "the distance to it would give the rest" + guess)
            else:
                need = [w for sym, w in (("k", "the camera's field of view"), ("R", "the distance to the object"))
                        if (ledger.get(sym) or {}).get("status", "missing") in ("missing", "bounded")]
                add("real", "kinematics", NO, "it needs " + " and ".join(need) if need else "the scale and the distance are not known")

        # the person's part: who chose the object, and whether the track was checked
        if "track" in self.stages and self.stages["track"]["result"]:
            d = self.identified_by
            if d:
                hows = list(d["not_by_hand"].values())
                agents = [h for h in hows if h.startswith("agent:")]
                proposed = [h for h in hows if h.startswith("proposed")]
                typed = [h for h in hows if h.startswith("typed:")]
                who = ("an AI agent placed the marks, not a person looking at the frames" if len(agents) == len(hows) else
                       "a person typed the positions as numbers, rather than placing the marks on the frames" if len(typed) == len(hows) else
                       "the computer suggested which thing is the object, and the suggestion was taken" if len(proposed) == len(hows) else
                       "the marks were snapped to what the computer found, not placed by hand" if not agents and not proposed else
                       "an AI agent or the computer placed the marks, not a hand")
                add("chosen", "track", NO, who + "; every measurement of the object rests on that choice")
            else:
                add("chosen", "track", YES, "a person placed the marks on the frames by hand")
        vf = st("verify")
        if "verify" in self.stages and "reviewed" in vf:
            add("checked", "verify", YES if vf["reviewed"] else NOT_YET,
                "the track sheet was looked at, and the ring is on the object in every frame" if vf["reviewed"] else
                "until then, every number about the object is not yet sure: look at the track sheet")
        return rows

    def _checklist(self):
        """The checklist as the report's table, under the conclusion's sentence, with the bottom line's paragraph folded
        under it (Jacob, 2026-11-01: the table "might be more useful ... than the long paragraph at the top"). A case
        with no row -- nothing ran -- has the paragraph as before."""
        rows = self.checklist()
        if not rows:
            return [self.bottom_line(), ""]
        cell = lambda s: str(s).replace("|", "\\|")
        return (["| What was checked | Answer | In short |", "|---|---|---|"]
                + [f"| {cell(r['test'])} | **{r['answer']}** | {cell(r['said'])} |" for r in rows]
                + ["", "<details><summary>The reasoning, in one paragraph</summary>", "", self.bottom_line(), "", "</details>", ""])

    def markdown(self):
        """The report, most wanted first: the conclusion, or the lack of one (Jacob, 2026-10-07: at the top), the
        checklist of the tests with an answer each, the paragraph of reasoning folded under it (2026-11-01),
        the Technical Note's variables and what is missing, the two figures; then, folded, the measurements
        stage by stage (with the record, the notes and what had no power), where the marks came from, and
        the commands."""
        c = self.clip or {}
        L = [f"# {self.tag.upper()}: case report", ""]
        if c:
            L += [self.segment_said(), ""]
            L.append(f"`{self.video.split('/')[-1]}`, {c['width']}x{c['height']}, "
                     f"{c['fps_exact']} fps ({c['fps']:.3f}). Generated by mcdonald {__version__}.")
            L.append("")
        if self.older():
            L += [f"> {self.older_said()}", ""]
        from .stages import SHEET_PROVISIONAL        # the one note that qualifies every number: kept where it is seen
        if SHEET_PROVISIONAL in self.notes:
            L += [f"> {SHEET_PROVISIONAL}", ""]
        label, head = self.conclusion()
        L += ["## Conclusion", "", f"**{label}.** {head}", ""]
        L += self._checklist()
        L += self._summary()
        L += self._ledger()

        needs = [(n, x) for n, st in self.stages.items() for x in st["needs"]]
        L += ["## Missing quantities", ""]
        L += [f"- **{x}** ({n})" for n, x in needs] if needs else ["Nothing outstanding was identified."]
        L.append("")

        pics = [f for f in self.figures if Path(f).exists() or not Path(f).is_absolute()]
        if pics:
            L += ["## Figures", ""]
            for f in pics:
                L += [f"![{Path(f).stem}]({quote(Path(f).name)})", ""]

        L += ["## Measurements", "", "<details><summary>Stage by stage</summary>", ""]
        L += ["### the record", "", "- " + self._provenance()]
        if c:
            L.append(f"- Frame rate is the exact rational {c['fps_exact']}. Where that is not a "
                     "whole number, a rounded 30 drifts a frame every ~33 s.")
            if c.get("fps_note"):
                L.append(f"- The frame rate is not the header's: {c['fps_note']}.")
        L += [f"- {n}" for n in self.notes if n != SHEET_PROVISIONAL and not n.startswith(STOPPED_BEFORE)]
        L.append("")
        for name, st in self.stages.items():
            if not st["result"] and not st["no_power"]:
                continue
            L.append(f"### {name}")
            L.append("")
            for k, v in st["result"].items():
                if isinstance(v, dict):
                    L.append(f"- {k}: " + ", ".join(f"{a} = {b}" for a, b in v.items()))
                elif isinstance(v, list):
                    L.append(f"- {k}: " + ", ".join(str(x) for x in v))
                else:
                    L.append(f"- {k}: {v}")
            L += [f"- no power -- {t}: {w}" for t, w in st["no_power"]]
            L.append("")
            # the pictures the stage wrote, under it: they sit beside the report, so a name is a link any Markdown
            # viewer follows (the window's report page shows them at its width)
            for f in st.get("files") or []:
                if str(f).lower().endswith((".png", ".jpg", ".jpeg")):
                    L += [f"![{name}: {Path(f).name}]({quote(Path(f).name)})", ""]
        L += ["</details>", ""]

        L += self._marks_detail()
        L += ["## Reproduce on command line", "", "<details><summary>The commands</summary>", "", "```bash"]
        L += self.commands or ["# no commands recorded"]
        L += ["```", "", "</details>", ""]
        return "\n".join(L) + "\n"

    def json(self):
        return json.dumps(dict(tag=self.tag, video=self.video, record=self.record, identified_by=self.identified_by,
                               clip=self.clip, segment=self.segment, stages=self.stages, commands=self.commands, figures=self.figures,
                               notes=self.notes, started=self.started, measured_by=self.measured_by, ledger=self.ledger(),
                               mcdonald=__version__, python=platform.python_version(),
                               ffmpeg=_ffmpeg_version()),
                          indent=1, default=plain)

    def write(self, prefix):
        open(f"{prefix}_case.md", "w", encoding="utf-8").write(self.markdown())
        open(f"{prefix}_case.json", "w", encoding="utf-8").write(self.json())
        print(f"wrote {prefix}_case.{{md,json}}", file=sys.stderr)
        return f"{prefix}_case.md"


def into_case(found, case_json, command=None):
    """`--case CASE_JSON` on a stage run on its own (`horizon`, `haze`, `focus`, `slew`): its measurement recorded in a
    case already measured, as if `run` had made it -- findings, what had no power, the command -- and the report written
    again, whose table of the four unknowns then carries the bound. Returns the report's path."""
    case = Case.load(case_json)
    found.into(case, command=command)
    return case.write(str(case_json)[:-len("_case.json")])


def case_option(ap):
    """The --case option the stages that need no `run` share."""
    ap.add_argument("--case", metavar="CASE_JSON", help="a case's _case.json: record this measurement in it and write its "
                    "report again (its table of the four unknowns carries what this finds)")


def command_line():
    """The command as it was typed, for a case's record: `cli` presents each tool its own name and tail."""
    import shlex
    return " ".join([sys.argv[0]] + [shlex.quote(a) for a in sys.argv[1:]])
