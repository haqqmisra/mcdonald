"""The standard case report: one clip, every stage, in a fixed shape.

The shape is not arbitrary. It is the structure the hand-written workups
converged on over two dozen clips, and each section earns its place:

    Conclusion         the one sentence a reader takes away, and how firm it is -- tentative,
                       or none -- then what can be said in one paragraph, with the bounds
    What the clip is   container, cadence, geometry, provenance if any
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
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from . import __version__
from .kinematics import A_SOUND


STOPPED_BEFORE = "stopped before "     # a note, then the step that never started: stages.run_case writes it, stopped_in() reads it
# A brightness beat in this band is the rate of a wingbeat -- gulls and crows near 3 Hz, pigeons near 8, small birds
# to the low twenties -- and the conclusion then names a bird as the leading explanation (Jacob, Galileo flyer 2,
# 2026-10-07). Below it a blinking light (an aircraft's strobe, about once a second) beats; above it nothing a camera
# at 60 frames a second resolves. The alternatives are named with it: the flicker stage cannot tell them apart.
WINGBEAT_HZ = (2.0, 25.0)
BIRD = "Beats like a bird"             # the conclusion's label for a beat in that band (Jacob, 2026-10-12): the window draws a bird by it
# A thing of known size in the picture gives the speed across the line of sight at that thing's distance: no faster
# where the object is no farther away. Under the speed of sound, that bound is the finding (JAIS Technical Note, PR149:
# "supersonic relative velocities can be excluded"; Jacob, 2026-10-22, exercise 2): the window draws sound's wavefronts by it
SUBSONIC = "Subsonic motion"
# A field of view (or angle marks) turns pixels into angles, and nothing gives the distance: the size and the speed both
# follow from a distance, so the headline says where a bird, a weather balloon and a fighter jet would be (Jacob,
# 2026-10-22, exercise 3: "This gives a sense of what is learned by obtaining FOV")
INDETERMINATE = "Indeterminate, range needed"
FLAMES = ("sky lantern", "candle flames")   # flicker's bands for a flame (item 11, 2026-10-20): per object, its own phase -- a
                                            # look-alike the members being out of step does not clear, so the bottom line says so

def own_beats(ff):
    """{name: beat} of the flicker stage's fields: the beats that are the object's (or members') own -- none
    unless the stage found a beat, and of a group's members only those whose beat passed the tests
    (`strong`, since 2026-10-09; a case from before has every member's)."""
    if not ff.get("beats"):
        return {}
    strong = ff.get("strong")
    return {n: b for n, b in (ff.get("beat") or {}).items() if strong is None or n in strong}


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
        if v is not None and fps:
            how = (f"fitted to {fit.get('n', '?')} points of the track against wall-clock time"
                   + ("" if kf.get("uniform", True) else "; **the motion is not uniform, so this does not describe it**"))
            rows.append(("pixel velocity", "v_px", f"{v / fps:.1f} px/frame ({v:.0f} px/s)", how))
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
        fov = sf.get("fov_deg")
        rows.append(("horizontal field of view", "FOV", None if fov is None else f"{fov:.1f}°",
                     sf.get("fov_from") or "not in the video: needs a graticule reading or a sourced field of view"))
        rows.append(("angular scale", "k", None if k is None else f"{k:.0f} px/rad ({k * math.pi / 180:.1f} px/deg)",
                     sf.get("k_from") or "needs a graticule, a reference object of known size, or a field of view"))
        rows.append(("angular rate", "ω = v_px f / k", None if om is None else f"{om:.2f} rad/s ({math.degrees(om):.0f}°/s)",
                     "from v_px, f and k" if om is not None else "needs k"))
        p, p_how = self.extent()
        rows.append(("image extent", "p", None if p is None else f"{p:.0f} px", p_how))
        rows.append(("range", "R", None if R is None else f"{R:,.0f} m", "given" if R is not None else "needs a sourced range"))
        rows.append(("aspect angle / range rate", "θ, Ṙ",
                     None if th is None else f"θ = {th:.0f}°" + (f" (Ṙ = {rdot:g} m/s)" if rdot is not None else ""),
                     ("given" if rdot is None else "from Ṙ, ω and R") if th is not None else "needs a range history or a sourced angle"))
        rows.append(("platform velocity", "v_own", None if v_own is None else f"{v_own:.0f} m/s",
                     "given (the aircraft's speed)" if v_own is not None else "needs the aircraft's speed"))
        lb, bar = kf.get("lower_bound_m_per_s"), kf.get("scale_bar_m_per_s")
        if lb is not None:
            rows.append(("transverse relative speed", "ωR = |v_obj − v_own| sin θ", f"{lb:.0f} m/s", "from ω and R"))
        elif bar is not None and kf.get("range_ratio"):
            rows.append(("transverse relative speed", "|v_obj − v_own| sin θ", f"{bar:.0f} m/s",
                         f"from the reference object at R_obj/R_ref = {kf['range_ratio']:g} (given): k cancels"))
        elif bar is not None:
            rows.append(("transverse relative speed", "|v_obj − v_own| sin θ", f"{bar:.0f} m/s × R_obj/R_ref",
                         "from the reference object: k cancels, the range ratio remains; no more than this where R_obj ≤ R_ref"))
        else:
            rows.append(("transverse relative speed", "ωR = |v_obj − v_own| sin θ", None, needs(k=k, R=R)))
        S = p * R / k if (p and R and k) else None
        rows.append(("object size", "S = pR/k", None if S is None else f"{S:.1f} m", "from p, R and k" if S else needs(p=p, R=R, k=k)))
        rel = kf.get("relative_speed_m_per_s") if th is not None else None
        rows.append(("relative speed", "|v_obj − v_own|", None if rel is None else f"{rel:.0f} m/s", 
                     "from ω, R and θ" if rel is not None else needs(k=k, R=R, **{"θ (or Ṙ)": th})))
        rows.append(("object velocity", "v_obj", None, "needs the relative speed, its direction, and v_own as a vector"))
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
            rows.append(("brightness beat", "f_b", f"{beat['hz']:.1f} Hz" + (f" (and {beat['double_hz']:.1f} Hz, its double)" if beat.get("double_hz") else ""),
                         f"the object's own, over frames {beat['first']}–{beat['last']}: clear of the codec's rhythm, not shared by the "
                         "background beside it" + ("" if beat.get("comes_back", True) else
                                                  ". One stretch only: the whole track does not beat, and no window apart from it does")
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
            return tf["object_size_px"], "the spot size the track was followed at"
        return None, "needs a track, or the object's length given"

    def rate(self):
        """(px/s, against what): the object's rate against the background where the layers check measured
        it (its largest motion group), else its rate in the image; (None, None) with no track."""
        lf = self.stages.get("layers", {}).get("fields") or {}
        per = lf.get("px_per_s") or {}
        if lf.get("tracked") and (per.get("all") or {}).get("median"):
            return per["all"]["median"], "against the background"
        v = (self.stages.get("kinematics", {}).get("fields") or {}).get("v_px_per_s")
        return (v, "in the image") if v is not None else (None, None)

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

    def at_each_distance(self):
        """The headline's words where the turn rate is known (a field of view, or angle marks) and the distance is not:
        how fast the object crosses the view and how big it is there, then how far away a bird, a weather balloon and a
        fighter jet of their sizes would be, and how fast they would then cross the line of sight, at least (omega R;
        `figures.BIRDS` and `OBJECTS`, which the size-and-speed figure marks too). An object no wider than a point
        here is no bigger than that in the picture, so each would be at least that far away."""
        from .figures import BIRDS, OBJECTS
        kf = self.stages.get("kinematics", {}).get("fields") or {}
        k = (self.stages.get("scale", {}).get("fields") or {}).get("k_px_per_rad")
        (rate, against), (p, _) = self.rate(), self.extent()
        omega = rate / k if rate is not None and k else kf["omega_rad_per_s"]   # against the background where measured
        two = lambda x: float(f"{x:.2g}")            # the sizes are a kind's, so two figures say all they can
        far = lambda m: f"{two(m / 1000):g} km" if m >= 1000 else f"{two(m):g} m"
        span = lambda a, b: f"{two(a):g}–{two(b):g} m" if b < 1000 else f"{far(a)}–{far(b)}"
        num = lambda v: f"{two(v):,.0f}"
        turn = f"the object moved about {math.degrees(omega):.0f}° a second {against or 'in the image'}"
        if not p or not k:
            return (turn + f": at 100 m away that is at least {num(omega * 100)} m/s across the line of sight, at 1 km "
                    f"{num(omega * 1000)} m/s, and how far away it is decides what it is")
        point = (kf.get("resolution") or {}).get("resolved") is False
        least = "at least " if point else ""
        R = lambda size: size * k / p
        b0, b1 = BIRDS
        said = [f"as a bird ({b0:g}–{b1:g} m) it would be {least}{span(R(b0), R(b1))} away and moving at least "
                f"{num(omega * R(b0))}–{num(omega * R(b1))} m/s across the line of sight"]
        said += [f"as a {name} ({size:g} m), {least}{far(R(size))} away and {num(omega * R(size))} m/s" for name, size in OBJECTS]
        size = f"{p:.0f} pixels" + ("" if point else " across") + f" ({math.degrees(p / k):.2g}°)"
        return (turn + f" and is {'no wider than a point here, ' if point else ''}{size}; what it is depends on how far "
                "away it is: " + "; ".join(said))

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
        day); and "Conclusion" otherwise. Written from the stages' fields, as the bottom line is, which
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
        if speed is not None:
            bits.append(f"the object moved about {speed:.0f} m/s relative to the camera's platform, with the stated range and scale")
        elif bar is not None:                        # at the thing's distance (or the ratio's): no faster where it is nearer
            ratio = kf.get("range_ratio")
            bits.append((f"the object moved about {bar:.0f} m/s across the line of sight, relative to the camera's platform, at "
                         f"{ratio:g} times the distance of the thing of known size (as given)" if ratio else
                         f"the object moved at most about {bar:.0f} m/s across the line of sight, relative to the camera's "
                         "platform, if it is no farther away than the thing of known size")
                        + (f": under the speed of sound (Mach {bar / A_SOUND:.2f})" if bar < A_SOUND else f" (Mach {bar / A_SOUND:.2f})"))
        elif kf.get("omega_rad_per_s") is not None:  # a scale and no distance: what each thing would be, and where
            bits.append(self.at_each_distance())
        elif rate is not None:                       # what is missing is said in the paragraph under it, once
            bits.append(f"the object moved about {rate:.0f} pixels a second {against}, and its real speed and size cannot be "
                        "found from this video alone")
        beats = own_beats(ff)
        hypothesis = False
        # a bird is named only from a beat that comes back -- the whole track beats, or windows apart agree (the headline
        # rule, Jacob, 2026-10-17); a case from before has no such mark, and its beats came back
        winged = lambda bs: [b for b in bs if WINGBEAT_HZ[0] <= b["hz"] <= WINGBEAT_HZ[1]]
        back = [b for b in beats.values() if b.get("comes_back", True)]
        beat = next(iter(winged(back)), None) or next(iter(back), None) or next(iter(beats.values()), None)
        flock = winged(back) if len(beats) > 1 else []
        once = [b for b in winged(beats.values()) if not b.get("comes_back", True)]
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
        elif beat and beat.get("comes_back", True) and WINGBEAT_HZ[0] <= beat["hz"] <= WINGBEAT_HZ[1]:
            hypothesis = True
            bits.insert(0, f"a bird is the leading explanation: its brightness beats at {beat['hz']:.1f} Hz"
                           + (f" (and at {beat['double_hz']:.1f} Hz, its double)" if beat.get("double_hz") else "")
                           + ", the rate of a wingbeat, a rhythm of its own and not the video's (a tumbling body or a blinking "
                           "light would beat too, and nothing here tells them apart)")
        elif once:                                    # at a wingbeat's rate, but in one stretch: too little to name a bird
            b = once[0]
            bits.append(f"its brightness beats at {b['hz']:.1f} Hz for one stretch, frames {b['first']}–{b['last']}, and not "
                        "elsewhere along its track: a rhythm of its own there, but too little to name a bird")
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
        if speed is None and bar is None and kf.get("omega_rad_per_s") is not None:
            return INDETERMINATE, head
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
        if against:
            L.append("The object moves " + ", and ".join(f"{r:.0f} px/s against the {n}" for n, r in against.items())
                     + " (medians over one-second windows of wall-clock time).")
            if len(against) > 1:
                L.append("Those are different numbers because the background is not one "
                         "surface; quoting either as *the* rate would name neither layer.")
        elif lf.get("tracked") and per.get("all"):
            L.append(f"The object moves {per['all']['median']:.0f} px/s against the scene's largest motion group "
                     "(median over one-second windows); the texture classes could not be told apart.")
        elif v is not None and not not_uniform:
            L.append(f"The object moves {v:.0f} px/s in the image.")
        elif v is not None:
            L.append(f"A straight-line fit to the track gives {v:.0f} px/s, but the motion "
                     "is **not uniform** ({}), so that figure does not describe it."
                     .format(kin.get("fit_residual", "large residual")))

        speed = kf.get("relative_speed_m_per_s", self._num(kin.get("speed_m_s")))
        missing = kf.get("missing", kin.get("missing"))
        bar, ref = kf.get("scale_bar_m_per_s"), st("scale", "fields").get("reference") or {}
        if speed is not None:
            L.append(f"With the stated scale and range that is {speed:.0f} m/s "
                     f"relative to the platform — a *relative* speed, which already includes "
                     "the platform's own motion.")
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
                om = r / k if r is not None and k else kf["omega_rad_per_s"]
                L.append(f"With the scale that is {om:.2f} rad/s {against or 'in the image'}, so at a distance of R meters it moves "
                         f"at least {om:.2f} R m/s across the line of sight, relative to the camera's platform"
                         + (f", and is {p:.0f}/{k:.0f} R m across ({p:.0f} px: {how}). " if p and k else
                            "; its size in the picture is not known. ")
                         + "The first line puts a bird, a weather balloon and a fighter jet where their sizes would be; "
                         "a distance from another source would say which, if any, it is.")
            if missing:
                L.append("It does not convert to a physical speed: " +
                         ", ".join(missing) + " " +
                         ("are" if len(missing) > 1 else "is") + " not available from this clip.")

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
                     + (f" (and at {beat['double_hz']:.1f} Hz, its double)" if beat.get("double_hz") else "")
                     + (f" for one stretch, frames {beat['first']}–{beat['last']}" if not beat.get("comes_back", True) else "")
                     + ": the object's own, not the video's.")
        flame = [b for b in beats.values() if any(d.get("source") in FLAMES for d in b.get("lookalike") or [])]
        if flame:                                            # flicker's item 11: a flame is a look-alike the beat cannot clear
            L.append(self.flame_said(flame, len(beats) > 1, st("groups", "fields")))
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

    def markdown(self):
        """The report, most wanted first: the conclusion, or the lack of one (Jacob, 2026-10-07: at the top),
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
        L += ["## Conclusion", "", f"**{label}.** {head}", "", self.bottom_line(), ""]
        L += self._summary()

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
                               notes=self.notes, started=self.started, measured_by=self.measured_by,
                               mcdonald=__version__, python=platform.python_version(),
                               ffmpeg=_ffmpeg_version()),
                          indent=1, default=plain)

    def write(self, prefix):
        open(f"{prefix}_case.md", "w", encoding="utf-8").write(self.markdown())
        open(f"{prefix}_case.json", "w", encoding="utf-8").write(self.json())
        print(f"wrote {prefix}_case.{{md,json}}", file=sys.stderr)
        return f"{prefix}_case.md"
