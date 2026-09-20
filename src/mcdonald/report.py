"""The standard case report: one clip, every stage, in a fixed shape.

The shape is not arbitrary. It is the structure the hand-written workups
converged on over two dozen clips, and each section earns its place:

    Bottom line        what can be said, in one paragraph, with the bounds
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
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone

from . import __version__


def _ffmpeg_version():
    try:
        out = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout
        return out.splitlines()[0].strip()
    except Exception:
        return "unknown"


def envelope(command, inputs, clip=None, files=(), results=None, no_power=(), needs=(), notes=(), exit_code=0,
             error=None):
    """What `--json` prints, the same shape from every command, so that something
    driving the package reads one structure and not six kinds of prose.

    It is a Case's stage, opened out: what went in, which files were written, what was
    found, and the two lists that make a result a measurement -- what this clip cannot
    decide (`no_power`, as [test, why] pairs, never dropped) and what would close the gap
    (`needs`). `exit` is the process's exit code and `error` the sentence that went with
    it; clip.EXIT_CODES says what the codes mean."""
    c = None if clip is None else dict(video=str(clip.video), width=clip.W, height=clip.H, fps=float(clip.fps),
                                       fps_exact=str(clip.info["fps"]), n0=clip.n0, n1=clip.n1,
                                       duration_s=float(clip.info.get("duration") or 0))
    return dict(command=command, mcdonald=__version__, inputs=inputs, clip=c, files=[str(f) for f in files if f],
                results=results or {}, no_power=[list(x) for x in no_power], needs=list(needs), notes=list(notes),
                exit=exit_code, error=error)


def emit(env):
    """The envelope, alone on stdout. With --json everything said to a person goes to stderr."""
    print(json.dumps(env, indent=1, default=str))


class Case:
    """One clip's results, accumulated stage by stage."""

    def __init__(self, tag, video, clip=None, record=None):
        self.tag = tag
        self.video = str(video)
        self.record = record
        self.clip = None if clip is None else dict(
            width=clip.W, height=clip.H, fps=float(clip.fps),
            fps_exact=str(clip.info["fps"]), n0=clip.n0, n1=clip.n1,
            duration_s=float(clip.info.get("duration") or 0))
        self.stages = {}
        self.commands = []
        self.notes = []
        self.identified_by = None            # set when the marks the track came from were not all a hand's
        self.started = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def add(self, stage, result=None, command=None, no_power=None, needs=None):
        """Record one stage. no_power is a list of (test, why) this clip
        cannot decide; needs is what would close the gap."""
        self.stages[stage] = dict(result=result or {}, no_power=list(no_power or []),
                                  needs=list(needs or []))
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
        who = ("an agent, not by a person looking at the frames" if len(agents) == len(hows) else
               "the detector (snapped marks), not by a hand" if not agents else "an agent or the detector, not by a hand")
        L = [f"> **Which thing is the object was decided by {who}.** The track was linked from {d['marks']} "
             f"mark{'s' if d['marks'] != 1 else ''}, of which {len(hows)} {'were' if len(hows) != 1 else 'was'} not placed by hand. "
             "Every object measurement below inherits that identification, and no test here checks it: "
             "look at the track strip and the contact strip before quoting any of them."]
        L += [f"> - frame {n}: {h}" for n, h in sorted(hows.items())]
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

    def bottom_line(self):
        """Assembled from the stages, and deliberately hedged where it must be."""
        L = []
        kin = self.stages.get("kinematics", {}).get("result", {})
        lay = self.stages.get("layers", {}).get("result", {})
        com = self.stages.get("comotion", {}).get("result", {})
        integ = self.stages.get("integrity", {}).get("result", {})

        if lay.get("rates"):
            parts = [f"{self._num(v):.0f} px/s against the {k}" for k, v in lay["rates"].items()
                     if self._num(v) is not None]
            L.append("The object moves " + ", and ".join(parts) + ".")
            if len(lay["rates"]) > 1:
                L.append("Those are different numbers because the background is not one "
                         "surface; quoting either as *the* rate would name neither layer.")
        elif kin.get("v_px") is not None:
            v = self._num(kin["v_px"])
            not_uniform = str(kin.get("uniform_motion", "")).startswith("NO")
            if v is not None and not not_uniform:
                L.append(f"The object moves {v:.0f} px/s in the image.")
            elif v is not None:
                L.append(f"A straight-line fit to the track gives {v:.0f} px/s, but the motion "
                         "is **not uniform** ({}), so that figure does not describe it."
                         .format(kin.get("fit_residual", "large residual")))

        if self._num(kin.get("speed_m_s")) is not None:
            L.append(f"With the stated scale and range that is {self._num(kin['speed_m_s']):.0f} m/s "
                     f"relative to the platform — a *relative* speed, which already includes "
                     "the platform's own motion.")
        elif kin.get("missing"):
            L.append("It does not convert to a physical speed: " +
                     ", ".join(kin["missing"]) + " " +
                     ("are" if len(kin["missing"]) > 1 else "is") + " not available from this clip.")

        if com.get("verdict"):
            rel = self._num(com.get("rel_D", 0)) or 0.0
            L.append(f"Against the texture immediately around it the object is "
                     f"**{com['verdict']}** ({rel:.1f} object diameters).")

        if integ.get("object_verdicts"):
            flagged = [k for k, v in integ["object_verdicts"].items() if v == "FLAG"]
            passed = [k for k, v in integ["object_verdicts"].items() if v == "PASS"]
            if flagged:
                L.append(f"Integrity: **{len(flagged)} test(s) FLAG** ({', '.join(flagged)}).")
            elif passed:
                L.append(f"Integrity: {len(passed)} test(s) pass and none flag; the object "
                         "behaves like imagery from this sensor chain.")
        np_total = sum(len(s["no_power"]) for s in self.stages.values())
        if np_total:
            L.append(f"{np_total} test(s) had no power on this clip and are listed below; "
                     "a test that cannot decide has not passed.")
        return " ".join(L) or "No stage produced a result."

    def markdown(self):
        c = self.clip or {}
        L = [f"# {self.tag.upper()}: case report", ""]
        if c:
            L.append(f"`{self.video.split('/')[-1]}`, {c['width']}x{c['height']}, "
                     f"{c['fps_exact']} fps ({c['fps']:.3f}), frames {c['n0']}-{c['n1']}. "
                     f"Generated by mcdonald {__version__}; read docs/method.md before quoting it.")
        L += [""] + self._identified() + ["## Bottom line", "", self.bottom_line(), "",
              "## What the clip is", "", "- " + self._provenance()]
        if c:
            L.append(f"- Frame rate is the exact rational {c['fps_exact']}. Where that is not a "
                     "whole number, a rounded 30 drifts a frame every ~33 s.")
        for n in self.notes:
            L.append(f"- {n}")

        L += ["", "## Measurements", ""]
        for name, st in self.stages.items():
            if not st["result"]:
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
            L.append("")

        no_power = [(n, t, w) for n, st in self.stages.items() for t, w in st["no_power"]]
        L += ["## What this clip cannot decide", ""]
        if no_power:
            L.append("| stage | test | why it has no power |")
            L.append("|---|---|---|")
            for n, t, w in no_power:
                L.append(f"| {n} | {t} | {w} |")
        else:
            L.append("Every test attempted returned a verdict.")

        needs = [(n, x) for n, st in self.stages.items() for x in st["needs"]]
        L += ["", "## What would close it", ""]
        if needs:
            for n, x in needs:
                L.append(f"- **{x}** ({n})")
        else:
            L.append("Nothing outstanding was identified.")

        L += ["", "## Reproduce", "", "```bash"]
        L += self.commands or ["# no commands recorded"]
        L += ["```", "",
              f"mcdonald {__version__}, Python {platform.python_version()}, {_ffmpeg_version()}. "
              f"Run started {self.started}.", "",
              "No pixel test excludes a composite made upstream of the symbology by someone who "
              "modelled exposure, shake, gain and parallax. That is a custody question — the "
              "original recording with its metadata, and the mission report."]
        return "\n".join(L) + "\n"

    def json(self):
        return json.dumps(dict(tag=self.tag, video=self.video, record=self.record, identified_by=self.identified_by,
                               clip=self.clip, stages=self.stages, commands=self.commands,
                               notes=self.notes, started=self.started,
                               mcdonald=__version__, python=platform.python_version(),
                               ffmpeg=_ffmpeg_version()),
                          indent=1, default=str)

    def write(self, prefix):
        open(f"{prefix}_case.md", "w").write(self.markdown())
        open(f"{prefix}_case.json", "w").write(self.json())
        print(f"wrote {prefix}_case.{{md,json}}", file=sys.stderr)
        return f"{prefix}_case.md"
