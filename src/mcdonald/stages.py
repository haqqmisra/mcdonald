"""The stages of a case, as functions with no interface in them.

`mcdonald run` is a command line over `run_case`, and so is whatever else wants
a whole case: a window's Measure menu calls the same function with a `say` that
writes to a pane instead of a terminal. Nothing here parses arguments, swaps
`sys.argv`, prints, or exits.

Every stage is a function that returns a `report.Found` -- fields, the lines the
report prints, what the clip cannot decide, what would close the gap, the files
written. The three that had no module of their own are here (`survey`, `scale`,
`kinematics`); the others are where their measurement is:

    verify      tracksheet.sheet
    layers      layers.glance (one frame pair; `run`'s look at the background)
                layers.measure (every pair, the object against each layer: minutes)
    comotion    comotion.measure
    integrity   integrity.examine
    symbology   symbology.measure

and each of those modules' own commands is a command line over the same
function, so a number from `mcdonald run` and one from the stage's own command
are the same number because they are the same call.

**Stage 3 is a gate, and it is deliberate** (see `run`'s docstring): a track
sheet is made before anything is measured from the track, and nothing here can
say the sheet was looked at. `i_looked` is how a caller asserts it.
"""
import math
import shlex
import statistics
import traceback
from pathlib import Path
from typing import NamedTuple

import numpy as np

from . import catalog, forensics as vf
from . import kinematics as kin
from . import lens
from . import scale as sc
from . import symbology as sym
from .progress import Stopped
from .report import STOPPED_BEFORE, Case, Found

STAGES = ["ingest", "survey", "symbology", "track", "verify", "layers", "scale",
          "kinematics", "camera", "groups", "flicker", "tether", "integrity", "report"]


class Known(NamedTuple):
    """Something a person may know about a clip that the pixels cannot say. One row is an
    option of `mcdonald run`, a field of the window's Measure form and a keyword of
    `run_case`: written down once, as the windows' actions are, so that the command line
    and the form cannot come to describe the same quantity differently -- or one of them
    come to lack it."""
    name: str               # run_case's keyword
    flag: str               # what the command line calls it
    kind: type              # float or str
    label: str              # what the form calls it
    help: str               # one line: --help, and the form's tooltip
    unit: str = ""
    term: str = ""          # the form's label in the trade's words and symbols (Jacob, 2026-09-24: technical terms are fine there)


KNOWN = [
    Known("fov", "--fov", float, "horizontal field of view (FOV)",
          "how wide the camera's view is from left to right, in degrees, if you have to guess it. The report says that "
          "it is a guess", "degrees", term="FOV, horizontal (deg) → k"),
    Known("fov_px", "--fov-px", float, "how many pixels that view spans",
          "how many pixels from left to right the camera's view spans, where the picture is a box inside the frame "
          "with words round it (an ATFLIR's is 244 of its 352). Left empty, it is the frame's width", "pixels",
          term="FOV extent, horizontal (px)"),
    Known("fields", "--fields", str, "horizontal field of view, stretch by stretch",
          "if the camera's view changes while the object is followed and the display says how: each stretch of frames, "
          "counted from 1, and how wide the view is there in degrees, such as 1-2156:0.7,2157-2206:1.5,2207-2290:6. Each "
          "change is taken out of the track as a zoom, and checked on the object's size where it can be. In place of the "
          "horizontal field of view", term="FOV by stretch (first-last:deg, …)"),
    Known("range_m", "--range", float, "distance to the object",
          "the distance to the object, in meters, if a source gives it", "meters", term="range R (m)"),
    # a limit where --range is a value (2026-10-30, PR051's drift: the ground behind it is as far as it can be, and a data
    # bar's slant range says how far that is): the same arithmetic, read as "at most"
    Known("range_max_m", "--range-max", float, "the farthest the object can be",
          "the farthest the object can be, in meters, if a source gives a limit and not its distance: the ground behind it, "
          "where the camera looks down (a data bar's slant range). The speed across the line of sight and the size are then "
          "given as the most they can be. In place of the distance to the object", "meters", term="farthest range R_max (m)"),
    Known("ref_px", "--ref-px", float, "a reference in the picture: its length in pixels on the screen",
          "the length in pixels on the screen of a reference object in the picture, one whose physical length you know", "pixels", term="reference object extent l_px (px)"),
    Known("ref_m", "--ref-m", float, "and its physical length", "the physical length of that reference, in meters", "meters", term="reference object length L (m)"),
    Known("range_ratio", "--range-ratio", float, "distance to the object, compared with that reference's",
          "how many times farther away the object is than the reference object of known size: 2 if twice as far, 0.5 if half "
          "as far. Left empty, the two are taken to be at the same distance, and the speed from the reference is "
          "said to be at the reference's range", "times", term="range ratio R_obj / R_ref"),
    Known("graticule", "--graticule", float, "the camera's angle marks",
          "if the camera draws marks with angles written on them: how many pixels lie between marks one degree apart. "
          "This measures how much angle one pixel covers", "pixels for each degree", term="graticule scale (px/deg) → k"),
    Known("lens_k1", "--lens-k1", float, "how much the lens bends straight lines",
          "how much the lens bends straight lines near the picture's edge, if a calibration of the camera gives it: the k1 of "
          "x_d = x_u (1 + k1 r²), with r the distance from the frame's centre in units of the lens's focal length (as "
          "calibration tools count it, OpenCV's among them), such as -0.43. Below 0 for a wide lens, which bows lines outward. "
          "Needs the horizontal field of view or the angle marks, for one focal length (not with the fields stretch by "
          "stretch). The path is drawn back through the lens before it is tested for a straight line at a steady speed", "k1",
          term="lens radial term k1 (x_d = x_u (1 + k1 r²), r in focal lengths) → k, straight and steady"),
    # the picture's stretch (2026-11-02, the surveys' F1/B8: PR113's file holds a 720x480 raster stretched to 1080p, and one k
    # read its diagonal transit as 121 deg/s for about 103). The number, and after a comma where it was read; method section 40
    Known("pixel_aspect", "--pixel-aspect", str, "how much wider than tall the video draws a pixel",
          "how much wider than tall the video draws each pixel, if the picture was stretched to fill the frame (a 4:3 "
          "picture shown full-height in 16:9 is 1.333); and, after a comma, where the number was read: symbols (a circle or "
          "ladder the display draws), scene (the picture under a roll of the camera), or your own words, such as "
          "1.333,symbols. The angle marks' scale is then read up the picture, the field of view counted in square pixels, "
          "and the turn rate from the track's own direction", "times wider than tall[,where it was read]",
          term="pixel aspect a = width / height [,symbols | scene | words]"),
    Known("names", "--names", str, "what the two parts of the background are",
          "what the background is made of in this video, written as striated=sea,isotropic=cloud tops. Striated means a "
          "background with lines or streaks in it, like waves on the sea; isotropic means one that looks the same in "
          "every direction, like cloud tops. The report then calls the two parts by these names", term="background layer names (striated=…,isotropic=…)"),
    Known("dark_below", "--dark-below", float, "the streaked part of the background is darker than",
          "count a piece of background as streaked only if it is darker than this brightness, from 0 to 255 (open sea in "
          "a white-hot heat camera is dark)", "brightness, 0 to 255", term="striated layer threshold (DN, 0–255)"),
    Known("mask_rows", "--mask-rows", str, "rows of the picture that hold words laid over it",
          "rows that hold words laid over the picture, if the computer misses them: first row:last row, and if they "
          "are there on only some frames then :first frame:last frame as well, with commas between, such as 1000:1080 or "
          "0:40:1:300", term="symbology mask rows (row0:row1[:n0:n1])"),
    Known("size", "--size", float, "how wide the object is",
          "how wide the object is on the screen, in pixels, for the steps that look at its pixels. Left empty, it is the "
          "spot size chosen from your marks (or 9)", "pixels", term="detector spot size (px)"),
    Known("diameter", "--diameter", float, "how wide the object is, to measure co-motion",
          "how wide the object is on the screen, in pixels. With this, one more thing is measured: does the object move "
          "along with the background around it, or through it? That is called co-motion, and it is counted in object "
          "widths. Left empty, co-motion is not measured", "pixels", term="object diameter D for co-motion (px)"),
    Known("aperture", "--aperture", str, "the disc its brightness is measured in",
          "a fixed disc for the brightness beat, in pixels: its radius, and if wanted the ring its background is taken "
          "from and how far away the apertures beside it sit -- R, or R,R1,R2, or R,R1,R2,BG, such as 8 or 8,11,16. Left "
          "empty, the disc follows the object's size", "pixels", term="photometry aperture r[,annulus r1,r2[,background offset]] (px)"),
    Known("beat_rule", "--beat-rule", str, "how a beat in its brightness is judged",
          "stage, the default: a beat must be three times what the background beside it does anywhere, and stand over the "
          "curve's own slow wander. paper: the bird paper's tests -- the curve's own continuum, the background at the beat's "
          "own frequency, and constant dots planted and encoded like the video -- for an object someone has looked at",
          term="flicker rule (stage | paper)"),
    Known("size_px", "--size-px", float, "how long the object is, for speed in body lengths",
          "how long the object is on the screen, in pixels, to give its speed in body lengths each second", "pixels", term="image extent p, for body lengths/s (px)"),
    Known("ground_speed", "--ground-speed", str, "a speed given for the object along the ground",
          "a speed someone gave for the object, measured along the ground below it (a report's \"480 mph\"), such as "
          "480mph or 215m/s; and, if known, the direction it went, in degrees from north: 480mph,265. With the "
          "aircraft's speed, it says which heights and speeds of the object's own give it -- how much of it may be "
          "the aircraft's own motion", "speed[,direction]", term="ground speed v_ground [,bearing°]"),
    Known("own_ship", "--own-ship", str, "how fast the aircraft with the camera flew",
          "how fast the aircraft carrying the camera flew, such as 180kt, or 250kias@7000ft for the speed its "
          "instruments show at a height; and, if known, its heading and height: 180kt,90,7000ft; and how fast it "
          "climbed (+) or descended (-), such as -500fpm or -2.5m/s: 180kt,90,7000ft,-500fpm, which needs the line of "
          "sight below", "speed[,heading[,height[,climb]]]",
          term="own-ship speed v_own [,heading°[,altitude[,climb]]]"),
    Known("line_of_sight", "--line-of-sight", str, "where the camera looked",
          "where the camera looked, for an aircraft that climbed or descended: the bearing it looked toward, in degrees "
          "from north (minus the angle of a north pointer on the display), and how far below the horizontal, such as "
          "270,17.9. A climb moves the ground under a nearer thing as a speed of the aircraft's own along the line of "
          "sight would", "bearing,depression", term="line of sight bearing°,depression° (for the climb)"),
    # the range and height with no motion and no known size (ROADMAP 0.4, objective 2): `mcdonald horizon` and `mcdonald
    # haze` as steps of `run`, each where what it needs is given -- so the window's Measure form reaches them too, and
    # their bounds reach the four unknowns (2026-10-29)
    Known("height", "--height", str, "how high the camera was over the sea",
          "how high the camera was over the sea, such as 7000ft or 2100m. With a point on the sea's horizon (a horizon "
          "mark, or the next row), the horizon step says how far away an object below the horizon can be at most, or how high "
          "an object above it is at least", "7000ft or 2100m", term="camera height over the sea h (7000ft | 2100m) → horizon"),
    Known("horizon", "--horizon", str, "a point on the sea's horizon",
          "a point on the sea's horizon, for the horizon step: the frame, then x and y in pixels, such as 120,640,388. Left "
          "empty, the first horizon mark is taken", "frame,x,y", term="point on the sea's horizon N,X,Y (px)"),
    Known("visibility", "--visibility", str, "how far one could see that day",
          "how far one could see that day, from a weather report, such as 20km. A dark object that looks pale with haze is "
          "far away, so this gives the farthest it can be, to a factor of about four", "20km",
          term="meteorological visibility V (20km) → haze"),
    Known("haze_reference", "--haze-reference", str, "something dark at a known distance",
          "something dark in the picture at a known distance, to measure the haze by in place of the visibility: the frame, "
          "x and y in pixels, and its distance in meters, such as 120,400,300,5000", "frame,x,y,meters",
          term="dark reference for the haze N,X,Y,R (px, m)"),
    # sharp means far (`mcdonald focus`), started by the camera's band (Jacob, 2026-10-29: so nobody gets a floor resting on
    # "focused far" they did not ask for); the rest of its options with it
    Known("band", "--band", str, "what kind of camera it was",
          "what kind of camera it was: visible (daylight), nir, swir, mwir or lwir (the kinds of infrared; mwir and lwir are "
          "heat cameras). With a field of view, the focus step says how far away the object is at least, if the camera "
          "was focused far away and not on it", "visible, nir, swir, mwir or lwir", term="sensor band (visible|nir|swir|mwir|lwir) → focus"),
    Known("pupil", "--pupil", str, "how wide the camera's lens opening is",
          "how wide the lens's opening (its entrance pupil) is, if a source gives it, such as 10cm or 0.1m: for the focus step",
          "10cm or 0.1m", term="entrance pupil D (10cm | 0.1m)"),
    Known("focus_at", "--focus-at", str, "how far away the lens was focused",
          "how far away the lens was focused, if known, such as 10km: for the focus step (left empty, far away)", "10km",
          term="focus distance s (10km)"),
    Known("ground_scale", "--ground-scale", float, "the ground's meters for each pixel beside the object",
          "the ground's meters for each pixel beside the object, from a ruler in the scene: for the focus step, an object "
          "wider than a point then gets how far it is as a share of the ground's distance", "meters for each pixel",
          term="ground scale (m/px), for r/R"),
]
SLOW = {"layers": "how the object moves against each part of the background. About a second for every pair of frames",
        "integrity": "has the video been changed, and was the object added later? The slow one: it more than doubles the time"}


SHEET_NEEDED = ("confirmation that the track sheet was examined: every number below "
                "assumes the track is on the object in every frame")
SHEET_PROVISIONAL = ("Nobody has yet confirmed the track sheet, the page that shows the object ringed in each frame, so the "
                     "measurements of the object below are **provisional**.")
# the same note as the case files written before 2026-11-07 keep it: read back as the note above (`report.Case.load`)
SHEET_PROVISIONAL_BEFORE = ("The track sheet was generated but not confirmed as examined, so the "
                            "object measurements below are **provisional**.")


def around(frames, clip, seconds=2.0):
    """The frames worth measuring for a thing seen on `frames` (a track, or the frames of its marks):
    those, and `seconds` either side of them, inside what `clip` holds. Someone who opened a whole
    clip to find a four-frame transit has 5291 frames open, and measuring all of them is hours:
    the object's rates come from the frames it is in, and the background's need a second or two
    round them. The window's Measure and a queue of several objects (`several.run_each`) use the
    one rule."""
    pad = int(round(seconds * clip.fps))
    return max(clip.n0, min(frames) - pad), min(clip.n1, max(frames) + pad)


def confirm_sheet(case_json, how, command=None):
    """A case whose track sheet was not confirmed, confirmed afterwards: the case read back from its
    `_case.json` (`report.Case.load`), the verify stage amended -- reviewed, and how -- the need and the
    note that made every object measurement provisional taken out, and both files written again.
    Nothing is measured again: whether the track is on the object changes whether its numbers can be
    trusted, not what they are. Returns (the case, the report's path); ValueError if the case has no
    track sheet."""
    from .report import Case
    case = Case.load(case_json)
    v = case.stages.get("verify")
    if not v or "reviewed" not in v["fields"]:
        raise ValueError(f"{case_json}: this case has no track sheet to confirm (it was measured without a track)")
    v["fields"]["reviewed"] = True
    v["result"]["reviewed"] = f"yes ({how})"
    v["needs"] = [x for x in v["needs"] if x != SHEET_NEEDED]
    case.notes = [x for x in case.notes if x != SHEET_PROVISIONAL]
    if command:
        case.commands.append(command)
    prefix = str(case_json)[:-len("_case.json")]
    return case, case.write(prefix)


# What a person may know that changes nothing but the arithmetic from the track's rate in pixels to a speed: the
# scale and kinematics stages. These can be given to a case already measured (`add_known`, `mcdonald report CASE
# --fov ...`, the report card's "Add what you know"); the rest of KNOWN changes what other stages look at, and needs
# the case measured again.
AFTER = ("fov", "fov_px", "graticule", "lens_k1", "pixel_aspect", "range_m", "range_max_m", "ref_px", "ref_m", "range_ratio", "size_px", "ground_speed", "own_ship",
         "line_of_sight")
# What a person may know that gives a step reading only the frames along the track already followed -- the horizon's,
# the haze's -- and so can be given afterwards too (Jacob, 2026-10-29: asked in the plain form, on the segment step and
# the report card): `add_known` does those steps again on the case's track, as `run_case` does them
LATER = ("height", "horizon", "visibility", "haze_reference", "band", "pupil", "focus_at", "ground_scale")
# each of those steps' notes, told apart: done again (`add_known`), its old ones go and the others' stay
NOTES_OF = dict(
    horizon=lambda n: n.startswith("Assumes the line is the sea's horizon") or (
        n.startswith("k comes from an assumed field of view") and n.endswith("is in the band.")),
    haze=lambda n: n.startswith("Assumes a daytime visible-light picture"),
    focus=lambda n: n.startswith(("Assumes the sensor is focused far", "A soft edge bounds nothing", "No floor on range in metres"))
    or (n.startswith("k comes from an assumed field of view") and "k squared" in n))
# the stages in the order run_case adds them (co-motion, which is asked for by its D, after tether)
# The stages run only where something they need is given, whatever `only` says, and by which of KNOWN's names: co-motion
# by its D; the horizon by the camera's height (and a point on the horizon, typed or a horizon mark); the haze by the
# visibility or a dark reference; the focus by the camera's band
OPTIONAL = dict(comotion=("diameter",), horizon=("height",), haze=("visibility", "haze_reference"), focus=("band",))
ORDER = STAGES[:STAGES.index("integrity")] + list(OPTIONAL) + STAGES[STAGES.index("integrity"):]
# The command that does each stage on its own (`mcdonald <command>`), as the stage's `command` in the case says where
# it has one: the window names it in an oval beside the bar while the stage runs (Jacob, 2026-10-19). The stages with no
# command of their own are `run`'s; the track is linked from marks as `mark --link` links it, and scale's k is
# `kinematics`' --fov and --graticule.
COMMAND = dict(ingest="run", survey="run", symbology="symbology", track="mark", verify="tracksheet", layers="layers",
               scale="kinematics", kinematics="kinematics", camera="camera", groups="groups", flicker="flicker", tether="tether",
               comotion="comotion", horizon="horizon", haze="haze", focus="focus", integrity="integrity", report="report")


def asked_for(only=None, skip=None):
    """The stages asked for, of STAGES, in its order: `only` (all, if not given) less `skip`."""
    return [s for s in STAGES if s in (set(only) if only else set(STAGES)) and s not in set(skip or ())]


def planned(only=None, skip=None, **known):
    """The stages run_case will go through for these keywords, in the order it goes through them (ORDER): those
    asked for, and each of OPTIONAL where what it needs is in `known` (co-motion where a D is given) -- for a window to
    say how many bars there are before the first begins (Jacob, 2026-10-20: a jewel under the bar for each). A stage
    that needs a track is in it; with none it is over at once."""
    asked = asked_for(only, skip)
    return [s for s in ORDER if s in asked or (s in OPTIONAL and any(known.get(n) for n in OPTIONAL[s])
                                               and s not in set(skip or ()))]


def known_of(case):
    """What was known of the video when `case` was measured, as run_case's keywords: what its ingest stage keeps
    (`known`, as given), or, for a case written before it kept them (2026-10-09), read back off the command it
    records, where each was typed with six figures."""
    f = (case.stages.get("ingest") or {}).get("fields") or {}
    if "known" in f:
        return dict(f["known"])
    run = next((c for c in case.commands if c.startswith("mcdonald run ")), None)
    if run is None:
        return {}
    words, out = shlex.split(run), {}
    for k in KNOWN:
        if k.flag in words[:-1]:
            try:
                out[k.name] = k.kind(words[words.index(k.flag) + 1])
            except ValueError:
                pass
    return out


def _track_of(case, case_json):
    """The case's track file: where the track stage says it was read from, or beside the case."""
    source = ((case.stages.get("track") or {}).get("fields") or {}).get("source")
    if not source:
        return None
    for p in (Path(source), Path(case_json).parent / Path(source).name,
              Path(str(case_json)[:-len("_case.json")] + "_autotrack.csv")):
        if p.exists():
            return p
    raise ValueError(f"{case_json}: its track, {source}, is not there any more")


# where a picture's stretch was read, as `--pixel-aspect A,FROM` names it: the words the report says (section 40). A number
# with no words is "given"; any other words are kept as the person's own
ASPECT_FROM = {"symbols": "read from the display's symbols", "scene": "read from the scene"}


def parse_pixel_aspect(text):
    """`--pixel-aspect` as given -- 1.333, or 1.333,symbols / 1.333,scene / 1.333,any words of your own -- as (a, where it
    came from): a the width of a pixel over its height, and the words "given", "given, read from the display's symbols",
    "given, read from the scene", or "given: <the words>". None for nothing given; ValueError for one that cannot be
    read, or that is not a positive number."""
    if text is None or text == "":
        return None
    if isinstance(text, (int, float)):
        a, words = float(text), ""
    else:
        a, _, words = str(text).partition(",")
        try:
            a = float(a)
        except ValueError:
            raise ValueError(f"--pixel-aspect {text}: write how much wider than tall a pixel is drawn, such as 1.333, and "
                             "after a comma where it was read (symbols, scene, or your own words)") from None
    if not math.isfinite(a) or a <= 0:
        raise ValueError(f"--pixel-aspect {text}: the width of a pixel over its height is a positive number")
    words = words.strip(" ,\t")
    return a, ("given" if not words else f"given, {ASPECT_FROM[words.lower()]}" if words.lower() in ASPECT_FROM else f"given: {words}")


def aspect_of(pixel_aspect):
    """(a, where it came from) of `--pixel-aspect` as given, or (1.0, "") for none."""
    got = parse_pixel_aspect(pixel_aspect)
    return got if got else (1.0, "")


def parse_fields(fields):
    """`--fields` as given (`1-2156:0.7,2157-2206:1.5`, or the list it reads as) -> [(first, last, deg)] in frame
    order. ValueError for one that cannot be read, overlaps, or gives a field that is not a positive angle."""
    if not fields:
        return None
    if isinstance(fields, str):
        from .readout import parse_values
        try:
            fields = parse_values(fields)
        except ValueError as e:
            raise ValueError(f"--fields {fields}: {e}" if "overlap" in str(e) else
                             f"--fields {fields}: write each stretch as FIRST-LAST:DEG, with commas between") from None
    out = sorted((int(a), int(b), float(d)) for a, b, d in fields)
    if any(d <= 0 or a > b for a, b, d in out):
        raise ValueError(f"--fields: every stretch runs forward and has a field of more than 0 deg ({out})")
    return out


def check_known(**known):
    """What run_case cannot be told together, said before anything is measured: the command line's error and the
    window's are the same sentence. ValueError."""
    if known.get("fields"):
        parse_fields(known["fields"])
        if known.get("fov") or known.get("graticule"):
            raise ValueError("--fields gives the camera's field and its changes: leave out --fov and --graticule")
    if known.get("range_max_m") is not None:
        if known["range_max_m"] <= 0:
            raise ValueError("--range-max: the farthest the object can be is more than 0 meters")
        if known.get("range_m") is not None:
            raise ValueError("--range gives the object's distance and --range-max the farthest it can be: give one of them")
    if known.get("pixel_aspect") is not None:
        parse_pixel_aspect(known["pixel_aspect"])
        if known.get("lens_k1"):
            raise ValueError("--lens-k1 is counted in square pixels, and a stretched picture (--pixel-aspect) is not drawn back "
                             "through the lens yet: give one of them")
    if known.get("lens_k1"):
        if known.get("fields"):
            raise ValueError("--lens-k1 is the lens at one focal length, and --fields says it changes: leave one out")
        if not known.get("fov") and not known.get("graticule"):
            raise ValueError("--lens-k1 is counted in the lens's focal length: give the field of view (--fov) or the angle "
                             "marks (--graticule) too")
        if known.get("fov") and not known.get("graticule"):
            lens.focal_px(known["lens_k1"], known["fov"], 1.0)     # refuses a field past the model's fold
    from .horizon import parse_height
    if known.get("height"):
        parse_height(known["height"])
    if known.get("horizon"):
        if not known.get("height"):
            raise ValueError("--horizon is for the horizon step, which needs the camera's height over the sea too: --height")
        horizon_point(known["horizon"])
    if known.get("visibility"):
        from .haze import parse_visibility
        parse_visibility(known["visibility"])
    if known.get("haze_reference"):
        if known.get("visibility"):
            raise ValueError("--visibility and --haze-reference both measure the haze: give one of them")
        haze_reference(known["haze_reference"])
    from .focus import BANDS, parse_length
    if known.get("band") and known["band"] not in BANDS:
        raise ValueError(f"--band {known['band']}: the camera's band is one of {', '.join(BANDS)}")
    for name, flag in (("pupil", "--pupil"), ("focus_at", "--focus-at")):
        if known.get(name):
            try:
                parse_length(known[name])
            except ValueError:
                raise ValueError(f"{flag} {known[name]}: give a length such as 10cm, 0.1m or 10km") from None
    extra = [f for n, f in (("pupil", "--pupil"), ("focus_at", "--focus-at"), ("ground_scale", "--ground-scale")) if known.get(n)]
    if extra and not known.get("band"):
        raise ValueError(f"{', '.join(extra)} {'is' if len(extra) == 1 else 'are'} for the focus step, which the camera's band "
                         "starts: --band too")


def horizon_point(text, marks=None):
    """(frame, x, y) of a point on the sea's horizon: as typed (`--horizon N,X,Y`), else the first frame's horizon mark in
    `marks` (a _marks.json), as `mcdonald horizon --marks` takes it; None where neither. ValueError for one that cannot
    be read."""
    if text:
        try:
            n, x, y = (float(v) for v in str(text).split(","))
        except ValueError:
            raise ValueError(f"--horizon {text}: write the point as FRAME,X,Y, such as 120,640,388") from None
        return int(n), x, y
    if marks:
        from .mark import MarkSet
        hm = MarkSet("", "", 0).load(marks).marks.get("horizon", {})
        if hm:
            n = min(hm)
            return (n, *hm[n])
    return None


def haze_reference(text):
    """`--haze-reference N,X,Y,RANGE` -> (frame, x, y, meters). ValueError for one that cannot be read."""
    try:
        n, x, y, r = (float(v) for v in str(text).split(","))
    except ValueError:
        raise ValueError(f"--haze-reference {text}: write it as FRAME,X,Y,METERS, such as 120,400,300,5000") from None
    if r <= 0:
        raise ValueError(f"--haze-reference {text}: its distance is more than 0 meters")
    return int(n), x, y, r


def horizon_step(clip, trk, height, horizon, marks, masks, prefix, tag, fov=None, fov_px=None, fields=None, graticule=None,
                 range_m=None, pixel_aspect=None, say=lambda *a: None):
    """`mcdonald horizon`'s own call on a case's track: (the Found, the flags of its command after --track). Its own k --
    across the frame, (FOV px) / FOV, or the graticule's, not the case's pinhole k -- so that the number here and the
    command's are the same number; the point on the horizon typed (`--horizon`) or a horizon mark in `marks`; NO POWER
    where there is neither. `pixel_aspect` (as `run` is given it) is the command's own `--pixel-aspect`: its k in square
    pixels, the frame's width over the stretch."""
    from . import horizon as hz
    hk = hk_from = None
    a = aspect_of(pixel_aspect)[0]
    fv = fov or field_of(fields, trk)
    if graticule:
        hk, hk_from = float(graticule), "graticule"
    elif fv:
        hk, hk_from = (fov_px or clip.W) / a / fv, "assumed"
    start = horizon_point(horizon, marks)
    if start is None:
        f = Found("horizon", no_power=[("horizon", "no point on the sea's horizon: give one (--horizon FRAME,X,Y) or put a "
                                                   "horizon mark on it")])
    else:
        share = hz.K_SHARE_ASSUMED if hk_from == "assumed" else 0.01
        f = hz.measure(clip, trk, start, hz.parse_height(height), hk, share, pixel_aspect=a, range_m=range_m,
                       mask=masks["blocks"] | masks["graphics"], out=prefix, name=tag, k_from=hk_from or "none")
    say("  " + "\n  ".join(hz.said(f.fields) + [w for _, w in f.no_power]))
    return f, ((_flags(horizon=",".join(f"{v:g}" for v in start)) if start else "") + _flags(height=height)
               + (_flags(fov=fv, fov_px=fov_px) if hk_from == "assumed" else _flags(graticule=graticule)) + _flags(range=range_m)
               + _flags(pixel_aspect=a if a != 1.0 else None))


def haze_step(clip, trk, size, visibility, reference, masks, say=lambda *a: None):
    """`mcdonald haze`'s own call on a case's track at the object's spot size: (the Found, the flags of its command after
    --track)."""
    from . import haze
    f = haze.measure(clip, trk, size, haze.parse_visibility(visibility) if visibility else None,
                     haze_reference(reference) if reference else None, masks)
    say("  " + "\n  ".join(haze.said(f.fields) + [w for _, w in f.no_power]))
    return f, _flags(size=size, visibility=visibility, reference=reference)


def focus_step(clip, trk, band, masks, rows=None, dark=False, pupil=None, focus_at=None, ground_scale=None, fov=None,
               fov_px=None, fields=None, graticule=None, pixel_aspect=None, say=lambda *a: None):
    """`mcdonald focus`'s own call on a case's track, with its command's own k (as `horizon_step`): (the Found, the flags
    of its command after --track). With a stretched picture (`pixel_aspect`) k is the scale up the picture, in square
    pixels; the command has no such flag, so its own call keeps a field of view across the frame's pixels."""
    from . import focus
    fv = fov or field_of(fields, trk)
    a = aspect_of(pixel_aspect)[0]
    k, k_from = ((float(graticule), "graticule") if graticule else ((fov_px or clip.W) / a / fv, "assumed") if fv else (None, "none"))
    share = focus.K_SHARE_ASSUMED if k_from == "assumed" else 0.01
    f = focus.measure(clip, trk, k, share, band, focus.parse_length(pupil) if pupil else None,
                      focus.parse_length(focus_at) if focus_at else None, masks=masks, rows=rows, dark=dark, k_from=k_from,
                      ground_m_per_px=ground_scale)
    say("  " + "\n  ".join(focus.said(f.fields) + [w for _, w in f.no_power]))
    return f, ((_flags(fov=fv, fov_px=fov_px) if k_from == "assumed" else _flags(graticule=graticule))
               + _flags(band=band, pupil=pupil, focus=focus_at, dark=bool(dark), ground_scale=ground_scale))


def field_of(fields, track):
    """The field the fields give at the track's first frame inside them: the scale stage's field of view, an
    assumption as any given field is. None where there is no track or no stretch holds it."""
    from .camera import field_at
    fields = parse_fields(fields)
    if not fields or not track:
        return None
    inside = [n for n in sorted(track) if field_at(n, fields) is not None]
    return field_at(inside[0], fields) if inside else None


def add_known(case_json, workdir=None, masks=None, command=None, say=lambda *a: None, **known):
    """A case worked out again with more known of the video -- the horizontal field of view, the distance to
    the object, a reference of known length in the picture, the speeds a report gave -- and nothing measured again.
    These change only the arithmetic from the track's rate in pixels to a speed, so the scale and kinematics
    stages are done again from the case's track, on the frames it was measured on (in `workdir`, extracted
    there if they are not), with what the case was measured with and `known` over it: a value of None takes
    one away. The report's figures are drawn again (the size and speed against range carries k and R) and both
    files are written. The numbers are the ones `run_case` gives when it is told the same from the start.

    Jacob, 2026-10-09: "prompt the user to ask if any additional quantities are known (FOV, object of known
    reference size, range to object, etc.)" -- asked before the one press (the segment step) and after it (the
    report card), and the after is this. `masks` is the clip's static masks, for a caller that has them: needed
    only for the blur of a point, where a size is given and the case has not measured it, and for the horizon and
    haze steps. Those (LATER: the camera's height and a point on the horizon, the visibility or a dark reference)
    read the frames along the case's track, and are done again here where they are known -- the calls `run_case`
    makes -- or taken out where they are forgotten. Returns (the case, the report's path); ValueError for a case with
    no track, or for a name in neither AFTER nor LATER."""
    from .report import Case
    bad = [n for n in known if n not in AFTER + LATER]
    if bad:
        flags = {k.name: k.flag for k in KNOWN}
        raise ValueError(f"{', '.join(flags.get(n, n) for n in bad)} changes more than the arithmetic of the speed: measure "
                         "the case again with it (mcdonald run)")
    case = Case.load(case_json)
    trk_file = _track_of(case, case_json)
    if trk_file is None or not case.clip:
        raise ValueError(f"{case_json}: this case was measured without a track, so there is no speed to work out")
    now = known_of(case)
    for n, v in known.items():
        if v is None:
            now.pop(n, None)
        else:
            now[n] = v
    check_known(**now)
    get = now.get
    trk = vf.read_track(trk_file)
    clip = vf.Clip(case.video, workdir, case.clip["n0"], case.clip["n1"])
    prefix = str(case_json)[:-len("_case.json")]

    fov = get("fov") or field_of(get("fields"), trk)
    f = scale(clip, get("graticule"), fov, get("ref_px"), get("ref_m"), fov_px=get("fov_px"),
              from_fields=bool(get("fields")), lens_k1=get("lens_k1"), track=trk, pixel_aspect=get("pixel_aspect")).into(case)
    say(f"  {f.result.get('k', 'k UNKNOWN')}")
    if (case.stages.get("camera") or {}).get("fields", {}).get("stretches") is not None:
        # the camera stage's rates in degrees are the same arithmetic: in the new scale, nothing in pixels changes
        from . import camera
        camera.rescale(case.stages["camera"]["fields"], clip.W, fov, get("fov_px"), get("graticule"), bool(get("fields")),
                       pixel_aspect=aspect_of(get("pixel_aspect"))[0])
    ref = dict(px=get("ref_px"), len_m=get("ref_m"), what="in-frame reference",
               **({"range_ratio": get("range_ratio")} if get("range_ratio") else {})) if get("ref_px") and get("ref_m") else None
    tf = case.stages["track"]["fields"]
    blur = None
    if get("size_px"):                                 # the blur of a point does not depend on the size: measured once
        blur = ((case.stages.get("kinematics") or {}).get("fields") or {}).get("resolution")
        if not blur:
            blur = vf.point_blur(clip, trk, masks if masks is not None else vf.static_masks(clip),
                                 vf.parse_rows(get("mask_rows")), bool(tf.get("object_is_dark")))
    k = kinematics(trk, clip.fps, clip.W, case.tag, f.carry, range_m=get("range_m"), size_px=get("size_px"), ref=ref,
                   blur=blur, ground_speed=get("ground_speed"), own_ship=get("own_ship"), line_of_sight=get("line_of_sight"),
                   out=prefix, height=clip.H,
                   extent_px=tf.get("object_size_px"), range_max=get("range_max_m"),
                   layers=(case.stages.get("layers") or {}).get("fields"))
    if k.carry:
        say("  " + k.carry["reduction"].report().replace("\n", "\n  "))
    # its notes where the stage's were, the old ones out: the report reads as if it had been told from the start
    at = next((i for i, n in enumerate(case.notes) if n.startswith(KIN_NOTES)), len(case.notes))
    case.notes = [n for n in case.notes if not n.startswith(KIN_NOTES)]
    case.add("kinematics", k.result, no_power=k.no_power, needs=k.needs, fields=k.fields, files=k.files)
    case.notes[at:at] = k.notes
    # the horizon, the haze and the focus, where they are known now: done again on the track (a new k or range changes
    # the horizon's and the focus's), or taken out where they are not
    marks = Path(f"{prefix}_marks.json")
    marks = str(marks) if marks.exists() else None
    if (get("height") or get("visibility") or get("haze_reference") or get("band")) and masks is None:
        masks = vf.static_masks(clip)
    for name, on in (("horizon", bool(get("height"))), ("haze", bool(get("visibility") or get("haze_reference"))),
                     ("focus", bool(get("band")))):
        case.notes = [n for n in case.notes if not NOTES_OF[name](n)]
        if not on:
            case.stages.pop(name, None)
            continue
        say(f"[{name}] on the track already followed")
        if name == "horizon":
            f, cmd = horizon_step(clip, trk, get("height"), get("horizon"), marks, masks, prefix, case.tag, fov=get("fov"),
                                  fov_px=get("fov_px"), fields=get("fields"), graticule=get("graticule"), range_m=get("range_m"),
                                  pixel_aspect=get("pixel_aspect"), say=say)
        elif name == "haze":
            f, cmd = haze_step(clip, trk, float(tf.get("object_size_px") or 9.0), get("visibility"), get("haze_reference"), masks,
                               say=say)
        else:
            f, cmd = focus_step(clip, trk, get("band"), masks, vf.parse_rows(get("mask_rows")), bool(tf.get("object_is_dark")),
                                pupil=get("pupil"), focus_at=get("focus_at"), ground_scale=get("ground_scale"), fov=get("fov"),
                                fov_px=get("fov_px"), fields=get("fields"), graticule=get("graticule"),
                                pixel_aspect=get("pixel_aspect"), say=say)
        f.into(case, command=f"mcdonald {name} {shlex.quote(str(case.video))}" + _flags(track=str(trk_file)) + cmd
                             + _flags(n0=case.clip["n0"], n1=case.clip["n1"]))
    case.stages = {n: case.stages[n] for n in sorted(case.stages, key=lambda n: ORDER.index(n) if n in ORDER else len(ORDER))}
    if "ingest" in case.stages:
        case.stages["ingest"]["fields"]["known"] = now
    try:
        from . import figures
        case.figures = figures.report_figures(case, clip, trk, prefix)
    except Exception as e:                           # as run_case: a figure that cannot be drawn is said, the report still written
        say(f"  ! the report's figures were not drawn: {type(e).__name__}: {e}")
    if command is None:
        flags = {k.name: k.flag for k in KNOWN}
        typed = lambda v: f"{v:.15g}" if isinstance(v, float) else str(v)
        gone = [flags[n][2:] for n, v in known.items() if v is None]
        command = (f"mcdonald report {shlex.quote(str(case_json))}"
                   + "".join(f" {flags[n]} {shlex.quote(typed(v))}" for n, v in known.items() if v is not None)
                   + (f" --forget {','.join(gone)}" if gone else ""))
    case.commands.append(command)
    return case, case.write(prefix)


# ---- the stages that had no module of their own ---------------------------------------
def survey(clip, masks, procs=None, progress=None, stop=None):
    """Cadence and transients: repeated frames, contrast transients, how much of the
    frame is masked, and the boresight if the reticle is coloured."""
    series = vf.frame_series(clip, masks, procs, progress, stop)
    reps = vf.repeats(series)
    trans = vf.transients(series)
    bore = sym.reticle_from_chroma(clip.rgb(clip.n0))
    fields = dict(repeated_frames=len(reps), transients=[list(t) for t in trans],
                  masked_share=dict(blocks=float(masks["blocks"].mean()), graphics=float(masks["graphics"].mean())),
                  boresight=None if not bore else dict(x=float(bore[0]), y=float(bore[1]), how="coloured reticle"))
    res = dict(repeated_frames=len(reps), transients=len(trans),
               masked_blocks=f"{masks['blocks'].mean():.1%}",
               masked_graphics=f"{masks['graphics'].mean():.1%}",
               boresight=f"({bore[0]:.1f}, {bore[1]:.1f})" if bore else "not found by chroma")
    npw, notes = [], []
    if not reps:
        npw.append(("cadence", "no repeated frames, so the cadence test on the object "
                               "has nothing to work with"))
    if not trans:
        npw.append(("transient", "no contrast transient in the clip"))
    if reps:
        notes.append(f"{len(reps)} repeated frames: never quote a per-frame displacement "
                     "on this clip; average over at least a second of wall-clock time.")
    return Found("survey", res, fields, no_power=npw, notes=notes, carry=series)


def through_lens(k, k1, width, height, track=None, fov=None, across=None, graticule=None):
    """An AngularScale read through a lens of radial term `k1`: its `lens` the focal length (the graticule's k, which a
    graticule reads at the axis; else the field of view's through the lens, `lens.focal_px`), its k the lens's own scale
    along `track`, or the axis's with no track. `k` unknown, or no k1: `k` as it is."""
    if not k1 or not k.known:
        return k
    f = float(k.k) if graticule else lens.focal_px(k1, fov, across or width)
    here = lens.along(track, k1, f, (width / 2.0, height / 2.0)) if track else f
    return kin.AngularScale(here, k.source, k.alpha_deg, f"{k.detail}; through a lens of k1 {k1:g}", lens.Lens(float(k1), f),
                            k.aspect, k.aspect_from)


def scale(clip, graticule=None, fov=None, ref_px=None, ref_m=None, alpha=0.0, fov_px=None, from_fields=False, lens_k1=None,
          track=None, pixel_aspect=None):
    """What bounds k, the angular scale: a graticule reading (a measurement), a field of
    view (an assumption, and said to be one), or nothing. The AngularScale is in `carry`.
    The field of view spans `fov_px` (the picture's box, where it is inside the frame;
    the frame's width by default); `from_fields`: it is the one the display gives at the
    track's first frame (`--fields`). With `lens_k1` (`lens`) the scale is read through
    the lens: the focal length at its axis, and k the lens's own along `track`, the scale
    that turns the track's rate into an angle. With `pixel_aspect` (`--pixel-aspect` as
    given: the width of a pixel over its height, and where it was read; section 40) k is
    the scale up the picture, in square pixels -- the graticule's, read up the picture, or
    the field of view over the frame's width in square pixels (W / a) -- and the fields
    carry the stretch, the scale across (`k_x_px_per_rad` = a k) and the field of view up
    the picture too (`fov_v_deg`)."""
    k = kin.AngularScale.unknown("no graticule, no reference object, no FOV supplied")
    res, fields, needs = {}, dict(k_px_per_rad=None, k_from=None), []
    a, a_from = aspect_of(pixel_aspect)
    square = clip.W / a                                   # the frame's width in square pixels
    up = " up the picture" if a != 1.0 else ""
    if graticule:
        k = kin.AngularScale.from_graticule(graticule, alpha, a, a_from)
        res["k"] = f"{k.k:.1f} px/rad (graticule, measured" + (f"{up}; {k.k_x:.1f} across" if a != 1.0 else "") + ")"
        fields.update(k_px_per_rad=float(k.k), k_from="graticule, measured" + (", read" + up if a != 1.0 else ""),
                      fov_deg=math.degrees(square / k.k),
                      fov_from="k extrapolated linearly across the frame" + (f"'s {square:.0f} square pixels" if a != 1.0 else ""))
        if a != 1.0:
            fields["fov_v_deg"] = math.degrees(clip.H / k.k)
    elif fov:
        across = fov_px or clip.W
        k = kin.AngularScale.from_fov(across / a, fov, alpha, a, a_from)
        over = (f" over {across:g} px" if fov_px else "") + (f" ({across / a:.0f} square pixels)" if a != 1.0 else "")
        res["k"] = (f"{k.k:.1f} px/rad (from an ASSUMED FOV of {fov:g} deg{over}"
                    + (", the display's field at the track's first frame" if from_fields else "") + (f"; {k.k_x:.1f} across" if a != 1.0 else "") + ")")
        fields.update(k_px_per_rad=float(k.k), k_from=f"an ASSUMED field of view of {fov:g} deg{over}"
                      + (" (the fields given, at the track's first frame)" if from_fields else ""),
                      fov_deg=float(fov), fov_px=float(across),
                      fov_from="the display's field at the track's first frame (--fields)" if from_fields else "assumed, as given")
        if a != 1.0:
            fields["fov_v_deg"] = kin.fov_from_k(k.k, clip.H, alpha)
    else:
        needs.append("an angular scale k: a graticule reading, a known-size object in "
                     "frame, or a sourced field of view")
    if a != 1.0:                                          # the stretch itself, and where it came from: the report says both
        fields.update(pixel_aspect=a, pixel_aspect_from=a_from, k_x_px_per_rad=float(k.k * a) if k.known else None)
        res["pixel aspect"] = (f"the pixels are drawn {a:.4g} times wider than tall ({a_from}): k is read up the picture, "
                               f"the scale across is {a:.4g} k, and a rate is turned into square pixels along its own direction")
    k = through_lens(k, lens_k1, clip.W, clip.H, track, fov, fov_px, graticule)
    if k.lens:
        where = "along the track" if track else "at the lens's axis, with no track to read it along"
        said = f"through a lens of k1 {k.lens.k1:g}: {k.lens.f:.1f} px/rad at its axis, {k.k:.1f} {where}"
        res["k"] = f"{k.k:.1f} px/rad {res['k'].split(' px/rad ', 1)[1]}, {said}"
        fields.update(k_px_per_rad=float(k.k), k_from=f"{fields['k_from']}, {said}", lens=dict(k1=k.lens.k1, f_px=k.lens.f))
        if graticule:                                  # the frame's real width: the graticule's angle is the axis's
            half = lens.undistort([[clip.W, clip.H / 2.0]], k.lens.k1, k.lens.f, (clip.W / 2.0, clip.H / 2.0))[0, 0] - clip.W / 2.0
            if np.isfinite(half):
                fields.update(fov_deg=2.0 * math.degrees(math.atan(half / k.lens.f)), fov_from="the graticule's scale, through the lens")
    bb = sym.bracket_box(clip.rgb(clip.n0))
    if bb:
        res["corner brackets"] = (f"{bb[0]:.0f} x {bb[1]:.0f} px -- these mark the NEXT "
                                  "field of view and must not be read as a zoom ratio")
        fields["corner_brackets"] = dict(width_px=float(bb[0]), height_px=float(bb[1]))
    if ref_px and ref_m:
        res["reference object"] = f"{ref_m:g} m over {ref_px:g} px"
        fields["reference"] = dict(px=ref_px, length_m=ref_m)
    if fov_px:                                         # the box the field spans: the ladder's and the figure's too
        fields["fov_px"] = float(fov_px)
    if not graticule and not fov:
        ladder = sc.fov_ladder(1.0, fov_px or clip.W, sc.FOV_LADDER)
        res["k if the FOV were"] = ", ".join(f"{r['fov_deg']:g} deg -> {r['k']:.0f}" for r in ladder)
        fields["k_if_the_fov_were"] = {f"{r['fov_deg']:g} deg": float(r["k"]) for r in ladder}
    return Found("scale", res, fields, needs=needs, carry=k,
                 no_power=[] if k.known else
                 [("scale", "k is unconstrained, so no pixel rate converts to an angular rate")])


# how each of the kinematics stage's notes begins: a case worked out again (`add_known`) takes the old ones out by these
KIN_NOTES = ("The track is not uniform straight-line motion", "Reported rates are fitted against wall-clock time",
             "Parallax ladder -- ", "The speed in body lengths divides by")


def platform_of(own_ship=None, layers=None):
    """Whether the camera moved while the object was tracked, for the speed in body lengths (B7, 2026-11-02): dict(moving,
    why), `moving` True where the aircraft's own speed is given (`own_ship`) or the layers step saw the background move
    across the picture (its `held_still`: still again in under half the frame pairs), None where the picture behind the
    object held still on screen -- a camera held still over a slow scene and a camera following the object over a sky
    with nothing to read both look so, and the step cannot tell them apart (`report.Case.behind_held_still`), so the
    rate is the object's as the camera held it -- and False where nothing says the camera moved (no layers step: the row
    then stands on its words). The rate over the size is v_own sin(phi) / D for a thing still in the air, so on a moving
    platform the row is NO POWER unless the rate is against a scene at the object's own depth, which no step here
    measures."""
    if own_ship:
        try:
            v = kin.speed_of(str(own_ship).split(",")[0])[0]
        except ValueError:
            v = None
        if v:
            return dict(moving=True, why=f"the camera flew at {v:.0f} m/s (--own-ship): a thing still in the air crosses the picture "
                                         f"at that speed over its range, and over its own size that is {v:.0f} m/s over its length "
                                         f"-- a 1-m thing scores {v:.0f} lengths a second standing still")
    hs = (layers or {}).get("held_still") or {}
    still = hs.get("still_again_share") if hs.get("share_of_pairs") is not None else None
    if still is None:
        return dict(moving=False, why=None)
    if still > 0.5:
        return dict(moving=None, why=f"the picture behind it held still on screen ({still:.0%} of the frame pairs), so the rate is its "
                                     "motion as the camera held it: a camera following the object over a sky with nothing to read "
                                     "looks so, and the step cannot tell it from a camera held still")
    return dict(moving=True, why=f"the background moved across the picture in {1 - still:.0%} of the frame pairs (the layers step): "
                                 "the camera turned or moved, and the rate over the size holds the camera's motion")


def kinematics(track, fps, width, tag="", scale=None, t0=None, t1=None, n0=None, n1=None, range_m=None,
               range_rate=None, theta_deg=None, size_px=None, ref=None, blur=None, ground_speed=None, own_ship=None,
               out=None, height=None, extent_px=None, range_max=None, line_of_sight=None, layers=None):
    """What the motion permits: v_px fitted against wall-clock time, and whatever the scale,
    a range and a reference allow beyond it -- bounds, not a speed. `ref` is
    dict(px, len_m[, range_ratio, what]). `blur` is forensics.point_blur's measure of how
    wide a point and the object are drawn, where there were frames to measure it on: a
    speed in body lengths of an object no wider than a point is NO POWER. `ground_speed` and
    `own_ship` are the parallax ladder's two strings (`kin.parallax_inputs`): without both it
    is NO POWER, saying which is missing. `layers` is the layers step's fields where it ran: with `own_ship` it says
    whether the camera moved (`platform_of`), and a speed in body lengths on a moving camera is NO POWER, for the
    rate over the size then holds the camera's motion (v_own / D for a thing standing still). The fit and the
    Reduction are in `carry`. `range_max` is the farthest the
    object can be, where `range_m` is where it is: the speed across the line of sight is then the most it can be,
    `upper_bound_m_per_s`, with `upper_bound_fastest_m_per_s` at the fastest it ran where its speed changed, and
    `relative_speed_m_per_s` stays None, for the speed is not known.

    The speed band (`kin.speed_band`, method section 32) is fitted beside the line: the rate along the
    track with its error from the track's own covariance, its net velocity over the stretch with an honest
    error, and whether the velocity changed -- as evidence, not a refusal. With `out` (a path prefix)
    the rate frame by frame goes to `<out>_speed.csv` and its figure to `<out>_speed.png`.

    What survives the missing variables (`projective`, method section 33) is read beside them: the projective
    constant-velocity test (with `height` the frame's centre is known, and with a scale the aspect angle under
    the hypothesis; the model it chooses held to the band's nugget, the track's own jitter), the turn radius in body widths and the smear number -- the last two from the object's width
    across its travel: `size_px` given, else the blur's measured width, else `extent_px` (the spot size the track
    was followed at). A track the camera held in view has none of them: its motion is the camera's.

    Where the scale was read through a lens (`scale.lens`, with `height`) the projective test and the turn take the
    track drawn back through it (`lens.drawn`), a pinhole's, which is all they know how to read: the width in the
    track's new pixels, the depth bound's band read off the drawn track, its jitter the picture's carried through the lens
    (`lens.carried`). The rate, the speed band
    and the smear stay the picture's, in the pixels a person can count; k is the lens's along the track. With no lens
    given, a track that misses the test is asked whether a lens alone could account for it (`lens.could_be`, kept as the
    test's `lens_could`, said by `projective.lens_could`)."""
    from . import projective
    par, par_npw, par_said = parallax(ground_speed, own_ship, line_of_sight)
    fit = kin.fit_v_px(track, fps, t0, t1, n0, n1) if track else None
    if not fit:
        why = "no track, so no image-plane rate" if not track else "track too short to fit a rate"
        return Found("kinematics", fields=dict(fit=None, parallax=par), no_power=[("kinematics", why)] + par_npw,
                     notes=["Parallax ladder -- " + "; ".join(x.strip() for x in par_said)] if par else ())
    if scale is None:
        scale = kin.AngularScale.unknown("no graticule and no FOV given")
    band, series, band_why = None, None, None
    try:
        got = kin.speed_band(track, fps, t0, t1, n0, n1)
    except Exception as e:                       # noqa: BLE001 -- a covariance that will not fit is said; the line's rate stands
        got, band_why = None, f"the band could not be fitted ({type(e).__name__}: {e})"
    if got:
        band, series = got
    elif band_why is None:
        band_why = f"fewer than {kin.BAND_MIN} points in the window once repeated frames are dropped"
    red = kin.Reduction(fit["v_px"], fps, scale, R_m=range_m, range_rate=range_rate, theta_deg=theta_deg,
                        size_px=size_px, ref=ref, tag=tag, fit=fit, band=band, R_max=range_max,
                        v_top=kin.fastest_rate(track, fps, fit, band, t0, t1, n0, n1) if range_max is not None else None)
    D, D_from = ((size_px, "given") if size_px else ((blur or {}).get("object_fwhm_px"), "measured: the object's width at half its peak")
                 if (blur or {}).get("object_fwhm_px") else (extent_px, "the spot size the track was followed at"))
    proj = turn = smear = proj_why = None
    if not fit.get("held"):
        centre = (width / 2.0, height / 2.0) if height else None
        through = scale.lens if height else None        # the track as a pinhole would have drawn it; none is the track itself
        line = lens.drawn(track, through.k1, through.f, centre) if through else track
        try:
            yard = (lens.carried(projective.band_of(line, fps, t0, t1, n0, n1), band, track, through.k1, through.f, centre)
                    if through else band or {})             # the band's nugget is the track's own jitter
            proj = projective.fit(line, fps, k=through.f if through else scale.k if scale.known else None, centre=centre,
                                  t0=t0, t1=t1, n0=n0, n1=n1, band=yard)
        except Exception as e:                   # noqa: BLE001 -- a fit that will not converge is said, not fatal
            proj, proj_why = None, f"{type(e).__name__}: {e}"
        turn = (projective.turn(line, fps, D * (lens.grown(track, line) if through else 1.0), t0=t0, t1=t1, n0=n0, n1=n1)
                if D else None)
        if through:
            drew = dict(k1=through.k1, f_px=through.f, moved_px=lens.moved(track, line))
            proj = proj and dict(proj, lens=drew)
            turn = turn and dict(turn, lens=drew)
        elif proj and height and proj.get("fits") is False:     # no lens given, and a miss: could one alone be all of it?
            proj = dict(proj, lens_could=lens.could_be(track, fps, width, height, proj, t0, t1, n0, n1))
        smear = projective.smear(fit["v_px"], fps, D) if D else None
    speed = red.speed()
    bl = kin.body_lengths_per_s(fit["v_px"], size_px) if size_px else None
    platform = platform_of(own_ship, layers) if bl else None
    bar = kin.scale_bar_speed(fit["v_px"], ref["px"], ref["len_m"], ref.get("range_ratio", 1.0)) if ref else None
    fields = dict(v_px_per_s=fit["v_px"], direction_deg=fit["direction_deg"], uniform=fit["uniform"], fit=fit,
                  omega_rad_per_s=red.omega, relative_speed_m_per_s=speed,
                  mach=None if speed is None else speed / kin.A_SOUND,
                  lower_bound_m_per_s=red.lower_bound(), upper_bound_m_per_s=None if fit.get("held") else red.upper_bound(),
                  upper_bound_fastest_m_per_s=None if fit.get("held") else red.fastest_bound(),
                  body_lengths_per_s=bl, platform=platform, scale_bar_m_per_s=bar,
                  range_ratio=ref.get("range_ratio") if ref else None,
                  quotable=fit["uniform"], missing=red.missing, resolution=blur, parallax=par,
                  range_m=range_m, range_max_m=range_max, range_rate_m_per_s=range_rate, theta_deg=red.theta_deg, size_px=size_px, fps=float(fps),
                  band=band, projective=proj, turn=turn, smear=smear, width_px=dict(px=D, how=D_from) if D else None)
    if scale.stretched:                                   # the rate in square pixels along the track, and what it was worth (section 40)
        fields.update(pixel_aspect=scale.aspect, square_per_px=red.along, v_square_px_per_s=fit["v_px"] * red.along)
    res = dict(v_px=f"{fit['v_px']:.1f} px/s" + (f" in the file's pixels; {fit['v_px'] * red.along:.1f} square px/s along the track "
                                               f"(the pixels are drawn {scale.aspect:.4g} times wider than tall)" if scale.stretched else ""),
               direction=f"{fit['direction_deg']:.0f} deg (clockwise from screen-up)",
               fit_residual=(f"{fit['resid_rms']:.2f} px = {fit['resid_frac']:.1%} of span, " if fit.get("resid_frac") is not None else
                             "the track does not move, ")      # a drawn track exactly still: no span to share the residual by
                            + f"{fit['n']}/{fit['n_in']} points kept",
               uniform_motion=(f"held in the field of view: it covers {fit['span_px']:.1f} px in all, and the residual is "
                               f"within the position noise ({fit['noise_px']:.2f} px a coordinate)") if fit.get("held") else
                              "yes" if fit["uniform"] else "NO -- v_px does not describe this motion")
    files, npw = [], []
    res.update(projective.said(proj, turn, smear))
    if proj_why:
        npw.append(("constant velocity", f"the projective fit failed: {proj_why}"))
    if not fit.get("held") and D is None:
        npw.append(("turn", "the turn radius in body widths and the smear need the object's width: give its size (--size-px)"))
    if band:
        res["speed band"], res["speed change"] = kin.band_said(band, fps)
        if kin.jumps_said(band):
            res["jumps"] = kin.jumps_said(band)
        if band.get("backtest"):
            res["band backtest"] = kin.backtest_said(band["backtest"], band.get("beat"))
        if not band["constant"] and not fit["uniform"]:
            res["uniform_motion"] += f": the speed ran from {band['v_min'][1]:.0f} to {band['v_max'][1]:.0f} px/s (the speed band)"
        if out and series:
            files += _speed_files(out, track, fps, band, series)
    else:
        npw.append(("speed band", band_why))
    if red.omega is not None:
        res["omega"] = f"{red.omega:.4f} rad/s" + (" (from the rate in square pixels along the track over k, the scale up the picture)"
                                                   if scale.stretched else "")
    if speed is not None:
        res["relative speed"] = (f"{speed:.0f} m/s (Mach {speed / kin.A_SOUND:.2f}) "
                                 "-- RELATIVE, includes the platform's own motion")
    elif fields["upper_bound_m_per_s"] is not None:
        top, fast = fields["upper_bound_m_per_s"], fields["upper_bound_fastest_m_per_s"]
        res["speed at most"] = (f"{top:.1f} m/s across the line of sight" + (f" on average, {fast:.1f} m/s at its fastest" if fast else "")
                                + f" (Mach {(fast or top) / kin.A_SOUND:.2f}) at the farthest range given, {range_max:g} m -- a "
                                "ceiling, not a speed")
    caveat = "" if fit["uniform"] else (
        f"  [the line's rate over a changing speed: it ran from {band['v_min'][1]:.0f} to {band['v_max'][1]:.0f} px/s (the speed band)]"
        if band and not band["constant"] else
        "  [NOT QUOTABLE: the underlying fit is not uniform straight-line motion]")
    if bl:
        res["body-lengths/s"] = (f"{bl:.1f} /s (needs no k, no R, no FOV, and is the object's own only where the camera does not move "
                                 f"through the air; {kin.RESOLVED})" + caveat)
        if platform["moving"] is not False:
            npw.append(("body lengths", platform["why"] + ": the speed in body lengths is not the object's own"
                        + (" here" if platform["moving"] else " unless the camera held still")))
    if ref and ref.get("range_ratio"):
        res["scale-bar speed"] = (f"{bar:.1f} m/s at {ref['range_ratio']:g} times the reference's range (the range ratio given)" + caveat)
    elif ref:
        res["scale-bar speed"] = (f"{bar:.1f} m/s "
                                  "at the reference's range -- a ceiling, not a speed" + caveat)
    notes = []
    if not fit["uniform"] and band and not band["constant"]:
        notes.append("The track is not uniform straight-line motion: the speed ran from "
                     f"{band['v_min'][1]:.0f} to {band['v_max'][1]:.0f} px/s (the speed band, in the figure beside the "
                     f"report), so every speed derived from a single v_px above is the line's rate over a changing speed; "
                     f"the track ran {kin.path_said(band)}. "
                     "If the camera moved, measure the rate against the background with `mcdonald layers`.")
    elif not fit["uniform"]:
        notes.append("The track is not uniform straight-line motion, so every speed "
                     "derived from a single v_px above is marked not quotable. Either "
                     "fit a window in which the motion IS uniform, or measure the rate "
                     "against the background with `mcdonald layers`.")
    notes.append("Reported rates are fitted against wall-clock time, never per-frame "
                 "differences.")
    npw += [] if speed is not None else [("speed", "missing " + ", ".join(red.missing))]
    npw += par_npw
    if par:
        still = par["rows"][0]
        k = still.get("k") if par["vectors"] else ([still["k_min"]] if still["k_min"] is not None else [])
        c = still.get("closest") if not k else None
        n = 3 if par.get("look_deg") is not None else 2         # what was given: the ground speed, the aircraft, the line of sight
        res["parallax"] = ("; ".join(par_said[:n]) + ": "
                           + ("a still object would be at h_O/h_A " + ", ".join(f"{1 - 1 / x:.3f}" for x in k) if k else
                              "no height holds a still object, and the least it needs of its own is "
                              f"{c['own_speed_needed_m_s']:.1f} m/s, " + (f"at h_O/h_A {c['h_ratio']:.3f}"
                              + (f" ({c['h_m']} m)" if c.get("h_m") is not None else "") if c["k"] is not None else
                              "approached just under the aircraft") if c else "no height holds a still object")
                           + " (the ladder is in the notes)")
        notes.append("Parallax ladder -- " + "; ".join(x.strip() for x in par_said[n:]))
    if bl:
        b, o = (blur or {}).get("blur_fwhm_px"), (blur or {}).get("object_fwhm_px")
        if b is not None and o is not None:
            res["resolution"] = (f"the object {o:.1f} px wide at half its peak, a point {b:.1f} px (the sharpest "
                                 f"spots on {blur['frames']} frames): " + ("resolved" if blur["resolved"] else "NOT resolved"))
        if blur and blur["resolved"] is False:
            npw.append(("body lengths", f"the object is {o:.1f} px wide at half its peak and a point on this clip "
                                        f"{b:.1f} px, so it is not resolved: the size given ({size_px:g} px) is the "
                                        "blur's, and the speed in body lengths is a speed in blur widths, not the body's"))
        elif blur and blur["resolved"]:
            notes.append(f"The speed in body lengths divides by the size given ({size_px:g} px). The object is "
                         f"resolved -- {o:.1f} px wide at half its peak, where a point on this clip is {b:.1f} -- so "
                         "it shows its own shape; that the size given is its length is the giver's.")
        else:
            why = ("fewer than %d compact spots to measure a point on" % vf.BLUR_SPOTS if blur and b is None else
                   "the object is clipped at white or black, so its width follows its brightness, and it is not "
                   f"{vf.CLIPPED_RESOLVED:g} times as wide as a point, past what clipping can make of one"
                   if blur and blur.get("object_clipped") else
                   "the object could not be fitted" if blur else "there were no frames to measure it on")
            notes.append(f"The speed in body lengths divides by the size given ({size_px:g} px). It is the object's "
                         "own length only if the object is resolved -- larger than the blur a point makes on this "
                         f"clip, which was not measured ({why}). For an unresolved point, or a group of them, it is "
                         "a speed in blur widths and says nothing about the body.")
    return Found("kinematics", res, fields, needs=red.missing, notes=notes, carry=dict(fit=fit, reduction=red, series=series),
                 no_power=npw, files=files)


def _speed_files(out, track, fps, band, series):
    """`<out>_speed.csv`, the rate frame by frame with its sd, and `<out>_speed.png`, the figure: [paths]."""
    import csv
    csv_path = f"{out}_speed.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        f.write(f"# the speed along the track with its band (mcdonald kinematics; docs/method.md section 32): {band['kernel']}; "
                f"nugget {band['nugget_px'][0]:.3f}/{band['nugget_px'][1]:.3f} px, sill {band['sill_px'][0]:.2f}/{band['sill_px'][1]:.2f} px, "
                f"range {band['range_s'][0]:.3f}/{band['range_s'][1]:.3f} s (x/y); {band['n']} of {band['n_in']} points "
                f"({band['repeats_dropped']} repeated frames dropped first, {band['clipped']} left out as the track's slips, "
                f"{sum(f['kind'] == 'step' for f in (band.get('jumps') or {}).get('flags', []))} steps kept)"
                + (f"; held to its own track, the band is {band['backtest']['light']}" if band.get("backtest") else "")
                + "; rates in px/s against wall-clock time\n")
        w = csv.writer(f)
        w.writerow(["frame", "t_s", "vx_px_per_s", "vy_px_per_s", "sd_vx", "sd_vy", "speed_px_per_s", "sd_speed"])
        for row in zip(series["frame"], series["t_s"], series["vx"], series["vy"], series["sd_vx"], series["sd_vy"],
                       series["speed"], series["sd_speed"]):
            w.writerow([row[0], f"{row[1]:.4f}"] + [f"{v:.3f}" for v in row[2:]])
    files = [csv_path]
    try:
        from . import figures
        ns = sorted(n for n in track if all(np.isfinite(track[n])))
        a = np.array([[n, *track[n]] for n in ns], float) if ns else np.zeros((0, 3))
        d = np.diff(a, axis=0) if len(a) > 1 else np.zeros((0, 3))
        one = (d[:, 0] >= 1) & (d[:, 0] <= 5)                 # consecutive points of the track, a few frames apart at most
        pairs = ((a[:-1, 0][one] + d[one, 0] / 2.0 - 1.0) / float(fps), np.hypot(d[one, 1], d[one, 2]) / d[one, 0] * float(fps))
        files.append(figures.speed_band(f"{out}_speed.png", series, band, fps, pairs=pairs))
    except Exception as e:                       # noqa: BLE001 -- a figure that cannot be drawn is not a finding lost
        print(f"  ! the speed figure was not drawn: {type(e).__name__}: {e}")
    return files


def parallax(ground_speed=None, own_ship=None, line_of_sight=None):
    """(fields, no_power, lines) of the parallax ladder (`kin.parallax_ladder`) from the two strings, and the line
    of sight that an aircraft's climb needs. Without both speeds: no fields, and a NO POWER line naming what is
    missing -- the video holds neither."""
    if not ground_speed or not own_ship:
        missing = [w for w, v in (("a speed along the ground (--ground-speed: a report's, or one measured with a scale "
                                   "on the ground)", ground_speed), ("the aircraft's own speed (--own-ship)", own_ship)) if not v]
        return None, [("parallax", "how much of a ground speed is the aircraft's own motion needs "
                                   + " and ".join(missing) + ", which the video does not hold")], []
    try:
        p = kin.parallax_inputs(ground_speed, own_ship, line_of_sight)
    except ValueError as e:
        return None, [("parallax", str(e))], []
    tilt = dict(climb=p["climb_m_s"], look=p["look_deg"], depression=p["depression_deg"])
    lad = kin.parallax_ladder(p["v_ground"], p["v_own"], p["own_heading"], p["ground_bearing"], p["h_own_m"], **tilt)
    lines = p["said"] + kin.ladder_said(lad, p["v_ground"], p["v_own"], p["h_own_m"])
    if p["own_band"]:
        lo = kin.parallax_ladder(p["v_ground"], p["own_band"][1], p["own_heading"], p["ground_bearing"], p["h_own_m"], **tilt)
        hi = kin.parallax_ladder(p["v_ground"], p["own_band"][0], p["own_heading"], p["ground_bearing"], p["h_own_m"], **tilt)
        lad["with_the_air_15C_colder_and_warmer"] = dict(v_own=list(p["own_band"]), warmer=lo["rows"], colder=hi["rows"])
    return dict(p, **lad), [], lines


# ---- a whole case ----------------------------------------------------------------------
def fellow_member(companion, track, members, tol_px=4.0, tol_deg=20.0):
    """The member of `members` ({name: {frame: (x, y)}}) that sits where the tether stage's `companion`
    (`r_px`, `direction_deg`: 0 straight down the image, + right) was found beside `track`, or None.
    PR135, 2026-10-08: on a flock the "bright feature that moves with the object" 29 px away was the
    next bird. Held to the median offset over the frames both have: within `tol_px` or 30% in distance,
    and `tol_deg` in direction."""
    if not companion or not members:
        return None
    best = None
    for name, t in members.items():
        both = [n for n in track if n in t]
        if len(both) < 5:
            continue
        dx = statistics.median(t[n][0] - track[n][0] for n in both)
        dy = statistics.median(t[n][1] - track[n][1] for n in both)
        r, ang = math.hypot(dx, dy), math.degrees(math.atan2(dx, dy))
        dr = abs(r - companion["r_px"])
        da = abs((ang - companion["direction_deg"] + 180) % 360 - 180)
        if dr <= max(tol_px, 0.3 * companion["r_px"]) and da <= tol_deg and (best is None or dr < best[0]):
            best = (dr, name)
    return best[1] if best else None


def _flags(**kw):
    """Options as they would be typed, for the report's Reproduce section."""
    typed = lambda v: f"{v:g}" if isinstance(v, float) else str(v)       # 100, as it was typed, not 100.0
    return "".join(f" --{k.replace('_', '-')}" + ("" if v is True else f" {shlex.quote(typed(v))}")
                   for k, v in kw.items() if v is not None and v is not False and v != "")


def run_case(video, track=None, marks=None, workdir=None, n0=None, n1=None, out=None, only=None, skip=None,
             i_looked=False, size=None, dark=None, diameter=None, fov=None, fov_px=None, fields=None, graticule=None, range_m=None,
             range_max_m=None, ref_px=None, ref_m=None, range_ratio=None, size_px=None, mask_rows=None, names=None, dark_below=None, ground_speed=None,
             own_ship=None, line_of_sight=None, aperture=None, beat_rule=None, avoid=None, procs=None, black_hot=False, height=None, horizon=None,
             visibility=None, haze_reference=None, band=None, pupil=None, focus_at=None, ground_scale=None, lens_k1=None, pixel_aspect=None,
             verbose=False, clip=None, say=print, progress=None, stop=None, sheet=None, masks=None,
             flicker_of=None, siblings=None, segment=None, started=None):
    """One clip through every stage, into one Case. Returns (case, clip, files written).

    `segment` is (first, last) of the frames the person chose to open, where the clip measured
    is fewer of them -- the frames round one object's track -- so that the report can say both;
    by default the clip is the segment.

    A member of a group followed on its own (`several.split_group`) comes with `flicker_of`,
    (the group's case json, its member name): its flicker stage is read from the group's,
    where it was measured with its fellows (`flicker.of_member`); and `siblings`, the other
    members' tracks {name: {frame: (x, y)}}, so that the tether stage can tell a fellow
    member from something tied to the object.

    `video` is a path or a record id; `track` a CSV's path, or `marks` a _marks.json to
    link one from. `only` and `skip` are stage names. `size` and `dark` describe the
    object to the stages that look at its pixels (the sheet, integrity); linked from
    marks, the link's own are used unless given. `names` ("striated=sea,isotropic=cloud
    tops") and `dark_below` are `layers`' own. `clip` is an already opened Clip of the
    same video and window, for a caller that has one. `say` is given every line meant
    for a person; `progress(text, done, total)` is told each long step as it starts
    and how far it has got, where it can count (see `mcdonald.progress`); and `stop`
    is asked between the items of a step and before each stage: the step under way
    ends, the rest are left out, and the report is still written, of the stages that
    ran. `i_looked` may be a function: it is called with
    the track sheet's path once the sheet exists, and what it returns is the answer --
    how a window asks the person in front of it. `sheet` is the track sheet's layout
    (`cols`, `tile`), for a caller that will show it on a screen rather than leave it
    to an image viewer; what the sheet measures does not depend on it. `masks` is the
    clip's static masks for a caller that has made them (the window has, for Find and
    Follow): made here when not given, once, and handed to every stage that needs them.
    A stage that raises is recorded as having no power, and the case goes on. `started(name)`
    is told each stage's name as it begins, and again as its progress does (`COMMAND` has the
    command that does it alone), for a window to say which is running -- a stage with nothing
    to count, such as groups on an object wider than a point, is over at once and records its
    command all the same.

    With a track the layers stage is the whole measurement (`layers.measure`: every
    frame pair, the object against each layer, about a second a pair); without one it
    is `layers.glance`, a look at the background over one pair."""
    chosen = asked_for(only, skip)

    class Want:
        """The stages asked for -- until `stop` says to stop, after which none is: the
        stage under way finishes, the rest are left out, and the report says which ran.
        Asked at each stage's start; a yes is the stage beginning, and `started` is told."""
        stopped = noted = False

        def __contains__(self, name):
            if not self.stopped and stop is not None and stop():
                self.stopped = True
                say("stopped: the remaining stages were not run")
            asked = name in chosen or (name in OPTIONAL and name not in set(skip or ()))   # asked for by what they need
            if self.stopped and asked and name != "report" and not self.noted:
                self.noted = True                          # the first one left out, for the report to say where it stopped
                case.note(STOPPED_BEFORE + name)
            run = asked and (not self.stopped or name == "report")
            if run and started is not None:
                started(name)
            return run

    want = Want()
    video_arg = str(video)
    video, tag, rec = vf.resolve(video_arg)
    clip = clip or vf.Clip(video, workdir, n0, n1)
    prefix = vf.out_prefix(out, tag, vf.named(n0, n1, clip))      # a segment named, with no --out: its own folder
    files = []
    window = _flags(n0=n0, n1=n1)
    given = dict(size=size, dark=dark)
    # what the person said they know, as given: kept in the case, so that something known later can be added to it
    # (`add_known`) without losing what was known before
    check_known(fov=fov, graticule=graticule, fields=fields, height=height, horizon=horizon, visibility=visibility,
                haze_reference=haze_reference, band=band, pupil=pupil, focus_at=focus_at, ground_scale=ground_scale,
                range_m=range_m, range_max_m=range_max_m, lens_k1=lens_k1, pixel_aspect=pixel_aspect)
    aspect = aspect_of(pixel_aspect)[0]                   # the number alone, for the stages whose own commands take it as one
    if fields and not isinstance(fields, str):         # as it would be typed: the case keeps it, and its commands say it
        fields = ",".join(f"{a}-{b}:{d:g}" for a, b, d in parse_fields(fields))
    known = {k: v for k, v in dict(fov=fov, fov_px=fov_px, fields=fields, range_m=range_m, range_max_m=range_max_m, ref_px=ref_px, ref_m=ref_m,
                                   range_ratio=range_ratio,
                                   graticule=graticule, names=names, dark_below=dark_below, mask_rows=mask_rows, size=size,
                                   diameter=diameter, size_px=size_px, ground_speed=ground_speed, own_ship=own_ship,
                                   line_of_sight=line_of_sight,
                                   aperture=aperture, beat_rule=beat_rule, black_hot=black_hot or None, height=height, horizon=horizon,
                                   visibility=visibility, haze_reference=haze_reference, band=band, pupil=pupil, focus_at=focus_at,
                                   ground_scale=ground_scale, lens_k1=lens_k1, pixel_aspect=pixel_aspect).items()
             if v is not None}

    def at(name):
        """`progress` for one stage: its steps, under the stage's name and place in the case."""
        if started is not None:
            started(name)
        if progress is None:
            return None
        place = f"step {chosen.index(name) + 1} of {len(chosen)} · " if name in chosen else ""
        return lambda text, done=None, total=None: progress(f"{place}{text}", done, total)

    def tell(name, text):
        """A step that cannot count: say that it has started."""
        p = at(name)
        if p is not None:
            p(text)

    def failed(name, e):
        if isinstance(e, Stopped):                         # asked for, not a failure: say so and leave the rest out
            want.stopped = True
            case.add(name, no_power=[(name, "stopped before it finished, so it found nothing")])
            say(f"  stopped during {name}: the remaining stages were not run")
            return
        if verbose:
            say(traceback.format_exc())
        case.add(name, no_power=[(name, f"stage raised {type(e).__name__}: {e}")])
        say(f"  ! {name} failed: {type(e).__name__}: {e}")

    # ---- 0 ingest -------------------------------------------------------------------
    cat = catalog.active()
    record = None
    if rec:
        record = dict(title=rec.get("title"), release=rec.get("release"),
                      disclosure=cat.disclosure(rec), catalog=cat.name)
    case = Case(tag, video, clip, record)
    case.segment = [int(segment[0]), int(segment[1])] if segment else [clip.n0, clip.n1]
    say(f"{video.name}: {clip.W}x{clip.H}, {clip.info['fps']} fps, frames {clip.n0}-{clip.n1}")
    say(f"case directory: {prefix.parent}")
    ingest = dict(container=clip.info["format"].get("format_name", "?"), fps_exact=str(clip.info["fps"]),
                  frames=f"{clip.n0}-{clip.n1}")
    if clip.info.get("fps_note"):
        ingest["fps_note"] = clip.info["fps_note"]
    g = (case.clip.get("encoding") or {}).get("gop")
    if g and g["anchor_period"]:
        i_frames = f"an I frame every {g['i_period']:g}" if g["i_period"] else f"one I frame in the first {g['frames_read']}"
        rhythm = ", ".join(f"{h:g}" for h in g["lines_hz"])
        ingest["gop"] = (f"{g['types'][:12]}...: {i_frames}, an anchor every {g['anchor_period']:g}"
                         + (f" (the codec's rhythm: {rhythm} Hz)" if g["lines_hz"] else ""))
    case.add("ingest", ingest, fields=dict(ingest, n0=clip.n0, n1=clip.n1, width=clip.W, height=clip.H, known=known),
             command=f"mcdonald run {shlex.quote(video_arg)}" + _flags(track=track, marks=marks) + window
                     + _flags(mask_rows=mask_rows, names=names, dark_below=dark_below, diameter=diameter, fov=fov,
                              fov_px=fov_px, fields=fields,
                              graticule=graticule, range=range_m, range_max=range_max_m, ref_px=ref_px, ref_m=ref_m,
                              range_ratio=range_ratio, size_px=size_px,
                              ground_speed=ground_speed, own_ship=own_ship, line_of_sight=line_of_sight, aperture=aperture,
                              beat_rule=beat_rule,
                              height=height, horizon=horizon, visibility=visibility, haze_reference=haze_reference,
                              band=band, pupil=pupil, focus_at=focus_at, ground_scale=ground_scale, lens_k1=lens_k1,
                              pixel_aspect=pixel_aspect,            # as given, with where it was read: the Reproduce line carries it (2026-11-02)
                              avoid=avoid if isinstance(avoid, str) else None,
                              only=",".join(only) if only else None, skip=",".join(skip) if skip else None,
                              i_looked=i_looked is True, **given))

    masks = masks if masks is not None else vf.static_masks(clip, progress=at("ingest"))
    rows = vf.parse_rows(mask_rows)
    trk = None
    if marks:
        from . import autolink
        from .mark import MarkSet
        if track and (size is None or dark is None):       # the link is already made: its size and polarity are still what the marks
            got = autolink.detector_of(track)              # said, and a dark object measured as bright reads nothing it should
            got = got or autolink.detector_at_marks(clip, marks, masks, rows, procs=procs)
            if got:
                size = got[0] if size is None else size
                dark = got[1] if dark is None else dark
                say(f"  from the marks: {'dark' if dark else 'bright'} spots {size:g} pixels wide")
            else:
                say("  ! the marks say nothing of the object's polarity (no spot at them): measured as bright unless --dark is given")
        if not track:                                      # with both, the track is the link someone already made of them
            say("[track] from the hand marks")
            tell("track", "Linking")
            link = autolink.link_from_marks_file(clip, marks, prefix, masks=masks, say=say, procs=procs)
            if link is not None and link.track:
                track = f"{prefix}_autotrack.csv"          # every stage below takes it as it would any other track
                files += [track, f"{prefix}_autotrack_strip.png"]
                size = link.size if size is None else size     # what the marks said the object is: the stages that
                dark = link.dark if dark is None else dark     # look at its pixels must look for that, not a default
        ms = MarkSet(tag, video, clip.fps).load(marks)
        case.identified(ms.not_by_hand(), len(ms.marks.get("object", {})))
    if track:
        trk = vf.read_track(track)
    size, dark = (9.0 if size is None else float(size)), bool(dark)

    # ---- 1 survey -------------------------------------------------------------------
    series = None                                          # the frame series, for integrity to take rather than make again
    if "survey" in want:
        say("[survey] cadence and transients")
        try:
            f = survey(clip, masks, procs, at("survey"), stop).into(case)
            series = f.carry
            say(f"  repeats {f.fields['repeated_frames']}, transients {len(f.fields['transients'])}")
        except Exception as e:
            failed("survey", e)

    # ---- 1b the overlay ---------------------------------------------------------------
    # The north pointer, the boresight and the corner brackets: `mcdonald symbology`, which was not a stage of a
    # case until 2026-09-23, so no report had a pointer reading in it. Its automatic method gives up after 20
    # frames on a pointer it cannot see, and lists the glyphs a template could follow for someone to choose from.
    if "symbology" in want:
        say("[symbology] the overlay: boresight, north pointer, corner brackets")
        try:
            from . import symbology
            f = symbology.measure(clip, step=3, out=prefix, say=lambda line: None, progress=at("symbology"), stop=stop,
                                  procs=procs, masks=masks)
            f.into(case, command=f"mcdonald symbology {shlex.quote(video_arg)}" + window)
            files += f.files
            rot = f.fields["rotation"][0] if f.fields["rotation"] else None
            say(f"  {f.result.get('north pointer', 'no north pointer read')}"
                + (f"; turning {rot['dtheta_dt']:+.3f} deg/s" if rot else ""))
        except Exception as e:
            failed("symbology", e)

    # ---- 2/3 track and the gate -----------------------------------------------------
    if "track" in want:
        if trk:
            case.add("track", dict(source=track, frames=len(trk), span=f"{min(trk)}-{max(trk)}"),
                     fields=dict(source=str(track), frames=len(trk), first=min(trk), last=max(trk),
                                 object_size_px=size, object_is_dark=dark))
            say(f"  track: {len(trk)} frames from {track}")
        else:
            case.add("track", no_power=[("track", "no track supplied, so every object "
                                                  "measurement is skipped")],
                     needs=["a track: mark the object on two frames with `mcdonald mark` and pass the file as "
                            "--marks, or run `mcdonald layers VIDEO --auto-track` and pass its --track"])
            say("  no track supplied: object stages will be skipped")

    if "verify" in want and trk:
        say("[verify] track sheet -- look at it before believing anything below")
        try:
            from . import tracksheet
            # a window lays the sheet out for its screen; the command line pages it so that each page can be checked
            # on one screen (an agent on IMG_5611, 2026-10-28: "an 11520 x 4254 JPEG can't be checked on one screen")
            layout = sheet or tracksheet.paged(clip.n1 - clip.n0 + 1)
            f = tracksheet.sheet(clip, [trk], prefix, dark=dark, title=rec["title"] if rec else None, procs=procs,
                                 say=say, progress=at("verify"), stop=stop, **layout)
            how = "--i-looked"
            if callable(i_looked):                         # a window shows the sheet and asks; a command line was told
                i_looked, how = bool(i_looked(f.files[0])), "asked with the sheet on the screen"
            pages = [p for p in f.files if str(p).endswith(".jpg")]
            f.result = dict(sheet=(pages[0] if len(pages) <= 1 else
                                   f"{len(pages)} pages, {Path(pages[0]).name} to {Path(pages[-1]).name}, each to be looked at"),
                            reviewed=f"yes ({how})" if i_looked else "NOT CONFIRMED")
            f.fields["reviewed"] = bool(i_looked)
            f.fields["pages"] = len(pages)
            if not i_looked:
                f.needs.append(SHEET_NEEDED)
                f.notes.append(SHEET_PROVISIONAL)
            f.into(case, command=f"mcdonald tracksheet {shlex.quote(video_arg)}"
                   + _flags(track=track, dark=dark, **({} if sheet else layout)) + window)
            files += f.files
        except (Exception, SystemExit) as e:
            failed("verify", e)

    # ---- 4 layers -------------------------------------------------------------------
    if "layers" in want:
        say("[layers] background, layer by layer")
        try:
            from . import layers
            if trk:
                f = layers.measure(clip, masks, rows, trk, names=dict(p.split("=") for p in names.split(",")) if names else None,
                                   dark_below=dark_below, out=prefix, procs=procs, say=say, progress=at("layers"), stop=stop, scene=True)
                say("  " + "\n  ".join(layers.said(f.fields)))
            else:
                tell("layers", "Layers glance")
                f = layers.glance(clip, masks, rows)
                say(f"  motion groups {f.fields['motion_groups']}; " +
                    ", ".join(f"{k} {v:.0f} px/s on screen" for k, v in f.fields["screen_px_per_s"].items())
                    + " (one frame pair; with a track, the object is measured against each layer)")
            f.into(case, command=f"mcdonald layers {shlex.quote(video_arg)}" + _flags(track=track) + window
                   + _flags(mask_rows=mask_rows, names=names, dark_below=dark_below))
            files += f.files
        except Exception as e:
            failed("layers", e)

    # ---- 5 scale --------------------------------------------------------------------
    k = None
    if "scale" in want:
        say("[scale] what bounds k")
        try:
            f = scale(clip, graticule, fov or field_of(fields, trk), ref_px, ref_m, fov_px=fov_px,
                      from_fields=bool(fields), lens_k1=lens_k1, track=trk, pixel_aspect=pixel_aspect).into(case)
            k = f.carry
            say(f"  {f.result.get('k', 'k UNKNOWN')}")
        except Exception as e:
            failed("scale", e)
    if k is None:
        k = kin.AngularScale.unknown("no graticule, no reference object, no FOV supplied")

    # ---- 6 kinematics ---------------------------------------------------------------
    if "kinematics" in want:
        if trk:
            say("[kinematics] what the motion permits")
        try:
            ref = dict(px=ref_px, len_m=ref_m, what="in-frame reference", **({"range_ratio": range_ratio} if range_ratio else {})) \
                if ref_px and ref_m else None
            blur = None
            if trk and size_px:
                tell("kinematics", "Blur width")
                blur = vf.point_blur(clip, trk, masks, rows, dark)
                say(f"  a point {blur['blur_fwhm_px'] or float('nan'):.1f} px wide at half its peak "
                    f"({blur['spots']} spots), the object {blur['object_fwhm_px'] or float('nan'):.1f}: "
                    + {True: "resolved", False: "NOT resolved", None: "not measured"}[blur["resolved"]])
            f = kinematics(trk, clip.fps, clip.W, tag, k, range_m=range_m, size_px=size_px, ref=ref, blur=blur,
                           ground_speed=ground_speed, own_ship=own_ship, line_of_sight=line_of_sight, out=prefix, height=clip.H,
                           extent_px=(case.stages.get("track", {}).get("fields") or {}).get("object_size_px"),
                           range_max=range_max_m, layers=(case.stages.get("layers") or {}).get("fields"))
            if f.carry:
                say("  " + f.carry["reduction"].report().replace("\n", "\n  "))
            f.into(case)
            files += f.files
        except Exception as e:
            failed("kinematics", e)

    # ---- camera -----------------------------------------------------------------------
    # What the camera did while the object was tracked: a zoom inside the track (found from the object's size and
    # its jump about the zoom's centre), and the rate's steps set beside the camera's events. A stage since
    # 2026-10-20 (the Navy's FLIR1: its picture zooms x2 three frames before its readout says so, and a published
    # fit ended an acceleration on that frame). The released-track null needs the camera's rate before: `mcdonald
    # camera --los-rate`.
    if trk and "camera" in want:
        say("[camera] a zoom inside the track, and the rate's steps at the camera's own events")
        try:
            from . import camera
            tell("camera", "Zoom steps and rate steps")
            zoom_found = None
            if not fields:                       # `mcdonald zoom`'s states, the segment's or the whole video's, where made
                here = Path(f"{prefix}_zoom.json")
                whole = here.parent.parent / here.name if here.parent.name.startswith("segment-") else None
                zj = here if here.exists() else whole if whole and whole.exists() else None
                if zj:
                    from . import zoom as zm
                    zoom_found = zm.read(zj)
                    say(f"  the zoom states from {zj}")
            f = camera.measure(clip, trk, size=size, dark=dark, fov=fov, fov_px=fov_px, graticule=graticule, out=prefix, tag=tag,
                               fields=parse_fields(fields), zoom=zoom_found, pixel_aspect=aspect)
            say("  " + "\n  ".join(camera.said(f.fields, brief=True)) if f.fields else "  " + f.no_power[0][1])
            f.into(case, command=f"mcdonald camera {shlex.quote(video_arg)}" + _flags(track=track, size=size if size != 9.0 else None,
                                                                                     dark=dark, fov=fov, fov_px=fov_px,
                                                                                     fields=fields, graticule=graticule,
                                                                                     pixel_aspect=aspect if aspect != 1.0 else None)
                   + window)
            files += f.files
        except Exception as e:
            failed("camera", e)

    # ---- groups ---------------------------------------------------------------------
    members = None
    if trk and "groups" in want:
        say("[groups] one object, or several points -- and do they keep their places?")
        try:
            from . import groups
            if size > groups.POINT_SIZE:
                f = Found("groups", dict(finding=f"the object was looked for as a spot {size:g} px wide, larger than a "
                                                 "point: whether it is several points is asked only of point-sized ones"),
                          dict(several=None, rigid=None, skipped_because_size_px=size))
            else:
                f = groups.measure(clip, trk, masks, rows, dark=dark, out=prefix, say=say, progress=at("groups"), stop=stop,
                                   procs=procs)
                say(f"  {f.result.get('points', '')}; {f.fields.get('finding', '')}")
                members = f.carry
            f.into(case, command=f"mcdonald groups {shlex.quote(video_arg)}" + _flags(track=track, dark=dark) + window
                   + _flags(mask_rows=mask_rows))
            files += f.files
        except Exception as e:
            failed("groups", e)

    # ---- flicker --------------------------------------------------------------------
    if trk and "flicker" in want:
        say("[flicker] does its brightness beat -- and is the beat its own?")
        try:
            from . import flicker
            if flicker_of:                                  # a member of a group: measured with its fellows, in the group's case
                group_json, name = flicker_of
                group = Case.load(group_json)
                where = Path(group_json).parent.name
                f = flicker.of_member((group.stages.get("flicker") or {}).get("fields") or {}, name, where, trk)
                cmd = ((group.stages.get("flicker") or {}).get("command")
                       or f"mcdonald flicker {shlex.quote(video_arg)} --members {where}/{tag}_members.csv")
            else:
                tracks = {f"member {i}": t for i, t in members.items()} if members else {"object": trk}
                f = flicker.measure(clip, tracks, dark=dark, out=prefix, say=say, progress=at("flicker"), stop=stop,
                                    procs=procs, aperture=aperture, rule=beat_rule, scene="bird",
                                    avoid=flicker.read_avoid(avoid) if isinstance(avoid, str) else avoid, black_hot=black_hot)
                cmd = (f"mcdonald flicker {shlex.quote(video_arg)}"
                       + (_flags(members=f"{prefix}_members.csv") if members else _flags(track=track, dark=dark))
                       + _flags(aperture=aperture, beat_rule=beat_rule, avoid=avoid if isinstance(avoid, str) else None,
                                black_hot=black_hot) + window)
            if f.fields.get("finding"):
                say(f"  {f.fields['finding']}")
            f.into(case, command=cmd)
            files += f.files
        except Exception as e:
            failed("flicker", e)

    # ---- tether ---------------------------------------------------------------------
    # Is something tied to the object -- a line, a payload -- and does it swing? A stage since 2026-10-07; the
    # object's size is read off the stack unless someone gave it (or the marks' link did).
    if trk and "tether" in want:
        say("[tether] is something tied to the object -- a line, a payload -- and does it swing?")
        try:
            from . import tether
            tsize = None if (given["size"] is None and not marks) else size
            f = tether.measure(clip, trk, masks, rows, size=tsize, out=prefix, say=say, progress=at("tether"), stop=stop,
                               procs=procs)
            fellows = siblings or ({f"member {i}": t for i, t in members.items()} if members else {})
            who = fellow_member(f.fields.get("companion"), trk, fellows) if fellows else None
            if who:                                         # the thing moving with it is a member of the group it is in
                c = f.fields["companion"]
                f.fields["fellow_member"] = dict(c, member=who)
                f.fields["companion"] = None
                f.fields["finding"] = f.result["finding"] = (
                    f"the {c['sign']} feature {c['r_px']:.0f} px ({c['r_over_size']:.1f} object sizes) away that moves with the "
                    f"object is {who} of the group it is in, not something tied to it")
            say(f"  {f.fields.get('finding', '')}")
            f.into(case, command=f"mcdonald tether {shlex.quote(video_arg)}" + _flags(track=track, size=tsize) + window
                   + _flags(mask_rows=mask_rows))
            files += f.files
        except Exception as e:
            failed("tether", e)

    # ---- co-motion (optional, needs D) ----------------------------------------------
    if trk and diameter and "comotion" in want:
        say("[comotion] with the texture, or through it?")
        try:
            from . import comotion as com
            f = com.measure(clip, trk, diameter, masks=masks, rows=rows, step=2, out=prefix, say=say,
                            progress=at("comotion"), stop=stop)
            f.into(case, command=f"mcdonald comotion {shlex.quote(video_arg)}" + _flags(track=track, diameter=diameter, step=2)
                   + window + _flags(mask_rows=mask_rows))
            files += f.files
            if f.fields["pairs"]:
                w = f.fields["whole"]
                say(f"  {f.fields['verdict']}: {w['rel_D']:.1f} D relative ({w['rel_D_per_s']:.2f} D/s)")
        except Exception as e:
            failed("comotion", e)

    # ---- the range and height with no motion (optional: each where what it needs is given) ---------------------
    # `mcdonald horizon` and `mcdonald haze` as steps of a case (2026-10-29; ROADMAP 0.4, objectives 2 and 6): their
    # bounds reach the four unknowns and the admissible region as they did through their --case (`horizon_step`,
    # `haze_step`: the same calls `add_known` makes when they are given afterwards)
    if trk and height and "horizon" in want:
        say("[horizon] how far below the sea's horizon, or how high above it")
        try:
            tell("horizon", "The sea's horizon")
            f, cmd = horizon_step(clip, trk, height, horizon, marks, masks, prefix, tag, fov=fov, fov_px=fov_px, fields=fields,
                                  graticule=graticule, range_m=range_m, pixel_aspect=pixel_aspect, say=say)
            f.into(case, command=f"mcdonald horizon {shlex.quote(video_arg)}" + _flags(track=track) + cmd + window)
            files += f.files
        except Exception as e:
            failed("horizon", e)
    if trk and (visibility or haze_reference) and "haze" in want:
        say("[haze] how far a dark object can be, from how pale the haze makes it")
        try:
            tell("haze", "Contrast against the sky")
            f, cmd = haze_step(clip, trk, size, visibility, haze_reference, masks, say=say)
            f.into(case, command=f"mcdonald haze {shlex.quote(video_arg)}" + _flags(track=track) + cmd + window)
            files += f.files
        except Exception as e:
            failed("haze", e)
    if trk and band and "focus" in want:
        say("[focus] how far away it is at least, from how sharp it is against the scene's own points")
        try:
            tell("focus", "How sharp the points are")
            f, cmd = focus_step(clip, trk, band, masks, rows, dark, pupil=pupil, focus_at=focus_at, ground_scale=ground_scale,
                                fov=fov, fov_px=fov_px, fields=fields, graticule=graticule, pixel_aspect=pixel_aspect, say=say)
            f.into(case, command=f"mcdonald focus {shlex.quote(video_arg)}" + _flags(track=track) + cmd + window
                   + _flags(mask_rows=mask_rows))
            files += f.files
        except Exception as e:
            failed("focus", e)

    # ---- 7 integrity ----------------------------------------------------------------
    if "integrity" in want:
        say("[integrity] altered? object added?  (the long one)")
        try:
            from . import integrity as integ
            f = integ.examine(clip, rec, trk, size=size, dark=dark, rows=rows, out=prefix, tag=tag, procs=procs,
                              say=say, progress=at("integrity"), stop=stop, masks=masks, series=series)
            f.into(case, command=f"mcdonald integrity {shlex.quote(video_arg)}"
                   + _flags(track=track, size=size if trk and size != 9.0 else None, dark=bool(trk) and dark) + window
                   + _flags(mask_rows=mask_rows))
            files += f.files
        except (Exception, SystemExit) as e:
            failed("integrity", e)

    # ---- 8 report -------------------------------------------------------------------
    if "report" in want:
        tell("report", "Report")
        try:
            from . import figures
            case.figures = figures.report_figures(case, clip, trk, prefix)
            files += case.figures
        except Exception as e:                       # a figure that cannot be drawn is said, and the report still written
            say(f"  ! the report's figures were not drawn: {type(e).__name__}: {e}")
        path = case.write(str(prefix))
        files += [path, f"{prefix}_case.json"]
        label, head = case.conclusion()
        say(f"\n{'=' * 70}\n{label}. {head}\n\n{case.bottom_line()}\n{'=' * 70}\n\nfull report: {path}")
    return case, clip, files
