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
import shlex
import traceback
from typing import NamedTuple

from . import catalog, forensics as vf
from . import kinematics as kin
from . import scale as sc
from . import symbology as sym
from .report import Case, Found

STAGES = ["ingest", "survey", "track", "verify", "layers", "scale",
          "kinematics", "integrity", "report"]


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


KNOWN = [
    Known("names", "--names", str, "what the two background layers are",
          "what the striated and the isotropic texture are in this scene, e.g. striated=sea,isotropic=cloud tops; "
          "the report names the layers by it"),
    Known("dark_below", "--dark-below", float, "the striated layer is darker than",
          "striated templates must be darker than this (open sea in white-hot IR)", "DN"),
    Known("mask_rows", "--mask-rows", str, "rows holding a burned-in caption",
          "y0:y1[:n0:n1],... burned-in captions the static masks miss"),
    Known("size", "--size", float, "the object's diameter",
          "the object's diameter px, for the stages that look at its pixels (default 9; linked from marks, "
          "the scale the marks chose)", "px"),
    Known("diameter", "--diameter", float, "the object's diameter, for co-motion",
          "object diameter px, the unit D of co-motion: does it move with the texture around it, or through it? "
          "Left out, co-motion is not measured", "px"),
    Known("size_px", "--size-px", float, "the object's length, for body-lengths a second",
          "object size in px, for body-lengths/s", "px"),
    Known("graticule", "--graticule", float, "the sensor's graticule",
          "px per labelled degree, if the sensor draws one: a measurement of the angular scale", "px/deg"),
    Known("fov", "--fov", float, "horizontal field of view",
          "assumed horizontal field of view, deg: an ASSUMPTION, and the report says so", "deg"),
    Known("range_m", "--range", float, "range to the object", "object range, m, if sourced", "m"),
    Known("ref_px", "--ref-px", float, "a reference object in frame: its length on screen",
          "in-frame reference length, px", "px"),
    Known("ref_m", "--ref-m", float, "and its true length", "in-frame reference true length, m", "m"),
]
SLOW = {"layers": "the object against each background layer: about a second for every frame pair",
        "integrity": "has the clip been altered, was the object added? The long one: as long again, and more"}


# ---- the stages that had no module of their own ---------------------------------------
def survey(clip, masks, procs=10):
    """Cadence and transients: repeated frames, contrast transients, how much of the
    frame is masked, and the boresight if the reticle is coloured."""
    series = vf.frame_series(clip, masks, procs=procs)
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


def scale(clip, graticule=None, fov=None, ref_px=None, ref_m=None, alpha=0.0):
    """What bounds k, the angular scale: a graticule reading (a measurement), a field of
    view (an assumption, and said to be one), or nothing. The AngularScale is in `carry`."""
    k = kin.AngularScale.unknown("no graticule, no reference object, no FOV supplied")
    res, fields, needs = {}, dict(k_px_per_rad=None, k_from=None), []
    if graticule:
        k = kin.AngularScale.from_graticule(graticule, alpha)
        res["k"] = f"{k.k:.1f} px/rad (graticule, measured)"
        fields.update(k_px_per_rad=float(k.k), k_from="graticule, measured")
    elif fov:
        k = kin.AngularScale.from_fov(clip.W, fov, alpha)
        res["k"] = f"{k.k:.1f} px/rad (from an ASSUMED FOV of {fov} deg)"
        fields.update(k_px_per_rad=float(k.k), k_from=f"an ASSUMED field of view of {fov:g} deg")
    else:
        needs.append("an angular scale k: a graticule reading, a known-size object in "
                     "frame, or a sourced field of view")
    bb = sym.bracket_box(clip.rgb(clip.n0))
    if bb:
        res["corner brackets"] = (f"{bb[0]:.0f} x {bb[1]:.0f} px -- these mark the NEXT "
                                  "field of view and must not be read as a zoom ratio")
        fields["corner_brackets"] = dict(width_px=float(bb[0]), height_px=float(bb[1]))
    if ref_px and ref_m:
        res["reference object"] = f"{ref_m:g} m over {ref_px:g} px"
        fields["reference"] = dict(px=ref_px, length_m=ref_m)
    if not graticule and not fov:
        ladder = sc.fov_ladder(1.0, clip.W, (3, 10, 30, 54))
        res["k if the FOV were"] = ", ".join(f"{r['fov_deg']:g} deg -> {r['k']:.0f}" for r in ladder)
        fields["k_if_the_fov_were"] = {f"{r['fov_deg']:g} deg": float(r["k"]) for r in ladder}
    return Found("scale", res, fields, needs=needs, carry=k,
                 no_power=[] if k.known else
                 [("scale", "k is unconstrained, so no pixel rate converts to an angular rate")])


def kinematics(track, fps, width, tag="", scale=None, t0=None, t1=None, n0=None, n1=None, range_m=None,
               range_rate=None, theta_deg=None, size_px=None, ref=None):
    """What the motion permits: v_px fitted against wall-clock time, and whatever the scale,
    a range and a reference allow beyond it -- bounds, not a speed. `ref` is
    dict(px, len_m[, range_ratio, what]). The fit and the Reduction are in `carry`."""
    fit = kin.fit_v_px(track, fps, t0, t1, n0, n1) if track else None
    if not fit:
        why = "no track, so no image-plane rate" if not track else "track too short to fit a rate"
        return Found("kinematics", fields=dict(fit=None), no_power=[("kinematics", why)])
    if scale is None:
        scale = kin.AngularScale.unknown("no graticule and no FOV given")
    red = kin.Reduction(fit["v_px"], fps, scale, R_m=range_m, range_rate=range_rate, theta_deg=theta_deg,
                        size_px=size_px, ref=ref, tag=tag, fit=fit)
    speed = red.speed()
    bl = kin.body_lengths_per_s(fit["v_px"], size_px) if size_px else None
    bar = kin.scale_bar_speed(fit["v_px"], ref["px"], ref["len_m"], ref.get("range_ratio", 1.0)) if ref else None
    fields = dict(v_px_per_s=fit["v_px"], direction_deg=fit["direction_deg"], uniform=fit["uniform"], fit=fit,
                  omega_rad_per_s=red.omega, relative_speed_m_per_s=speed,
                  mach=None if speed is None else speed / kin.A_SOUND,
                  lower_bound_m_per_s=red.lower_bound(), body_lengths_per_s=bl, scale_bar_m_per_s=bar,
                  quotable=fit["uniform"], missing=red.missing)
    res = dict(v_px=f"{fit['v_px']:.1f} px/s",
               direction=f"{fit['direction_deg']:.0f} deg (clockwise from screen-up)",
               fit_residual=f"{fit['resid_rms']:.2f} px = {fit['resid_frac']:.1%} of span, "
                            f"{fit['n']}/{fit['n_in']} points kept",
               uniform_motion="yes" if fit["uniform"] else
                              "NO -- v_px does not describe this motion")
    if red.omega is not None:
        res["omega"] = f"{red.omega:.4f} rad/s"
    if speed is not None:
        res["relative speed"] = (f"{speed:.0f} m/s (Mach {speed / kin.A_SOUND:.2f}) "
                                 "-- RELATIVE, includes the platform's own motion")
    caveat = "" if fit["uniform"] else \
        "  [NOT QUOTABLE: the underlying fit is not uniform straight-line motion]"
    if bl:
        res["body-lengths/s"] = f"{bl:.1f} /s (needs no k, no R, no FOV)" + caveat
    if ref:
        res["scale-bar speed"] = (f"{bar:.1f} m/s "
                                  "at the reference's range -- a ceiling, not a speed" + caveat)
    notes = []
    if not fit["uniform"]:
        notes.append("The track is not uniform straight-line motion, so every speed "
                     "derived from a single v_px above is marked not quotable. Either "
                     "fit a window in which the motion IS uniform, or measure the rate "
                     "against the background with `mcdonald layers`.")
    notes.append("Reported rates are fitted against wall-clock time, never per-frame "
                 "differences.")
    return Found("kinematics", res, fields, needs=red.missing, notes=notes, carry=dict(fit=fit, reduction=red),
                 no_power=[] if speed is not None else [("speed", "missing " + ", ".join(red.missing))])


# ---- a whole case ----------------------------------------------------------------------
def _flags(**kw):
    """Options as they would be typed, for the report's Reproduce section."""
    typed = lambda v: f"{v:g}" if isinstance(v, float) else str(v)       # 100, as it was typed, not 100.0
    return "".join(f" --{k.replace('_', '-')}" + ("" if v is True else f" {shlex.quote(typed(v))}")
                   for k, v in kw.items() if v is not None and v is not False and v != "")


def run_case(video, track=None, marks=None, workdir=None, n0=None, n1=None, out=None, only=None, skip=None,
             i_looked=False, size=None, dark=None, diameter=None, fov=None, graticule=None, range_m=None,
             ref_px=None, ref_m=None, size_px=None, mask_rows=None, names=None, dark_below=None, procs=10,
             verbose=False, clip=None, say=print, progress=None, stop=None, sheet=None):
    """One clip through every stage, into one Case. Returns (case, clip, files written).

    `video` is a path or a record id; `track` a CSV's path, or `marks` a _marks.json to
    link one from. `only` and `skip` are stage names. `size` and `dark` describe the
    object to the stages that look at its pixels (the sheet, integrity); linked from
    marks, the link's own are used unless given. `names` ("striated=sea,isotropic=cloud
    tops") and `dark_below` are `layers`' own. `clip` is an already opened Clip of the
    same video and window, for a caller that has one. `say` is given every line meant
    for a person, `progress` the name of each long step as it starts, and `stop` is
    asked before each stage whether to leave the rest out (the report is still
    written, of the stages that ran). `i_looked` may be a function: it is called with
    the track sheet's path once the sheet exists, and what it returns is the answer --
    how a window asks the person in front of it. `sheet` is the track sheet's layout
    (`cols`, `tile`), for a caller that will show it on a screen rather than leave it
    to an image viewer; what the sheet measures does not depend on it. A stage that
    raises is recorded as having no power, and the case goes on.

    With a track the layers stage is the whole measurement (`layers.measure`: every
    frame pair, the object against each layer, about a second a pair); without one it
    is `layers.glance`, a look at the background over one pair."""
    chosen = [s for s in STAGES if s in (set(only) if only else set(STAGES)) and s not in set(skip or ())]

    class Want:
        """The stages asked for -- until `stop` says to stop, after which none is: the
        stage under way finishes, the rest are left out, and the report says which ran."""
        stopped = False

        def __contains__(self, name):
            if not self.stopped and stop is not None and stop():
                self.stopped = True
                say("stopped: the remaining stages were not run")
            asked = name in chosen or (name == "comotion" and name not in set(skip or ()))   # co-motion is asked for by its D
            return asked and (not self.stopped or name == "report")

    want = Want()
    video_arg = str(video)
    video, tag, rec = vf.resolve(video_arg)
    clip = clip or vf.Clip(video, workdir, n0, n1)
    prefix = vf.out_prefix(out, tag)
    files = []
    window = _flags(n0=n0, n1=n1)
    given = dict(size=size, dark=dark)

    def failed(name, e):
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
    say(f"{video.name}: {clip.W}x{clip.H}, {clip.info['fps']} fps, frames {clip.n0}-{clip.n1}")
    say(f"case directory: {prefix.parent}")
    ingest = dict(container=clip.info["format"].get("format_name", "?"), fps_exact=str(clip.info["fps"]),
                  frames=f"{clip.n0}-{clip.n1}")
    case.add("ingest", ingest, fields=dict(ingest, n0=clip.n0, n1=clip.n1, width=clip.W, height=clip.H),
             command=f"mcdonald run {shlex.quote(video_arg)}" + _flags(track=track, marks=marks) + window
                     + _flags(mask_rows=mask_rows, names=names, dark_below=dark_below, diameter=diameter, fov=fov,
                              graticule=graticule, range=range_m, ref_px=ref_px, ref_m=ref_m, size_px=size_px,
                              only=",".join(only) if only else None, skip=",".join(skip) if skip else None,
                              i_looked=i_looked is True, **given))

    masks = vf.static_masks(clip)
    rows = vf.parse_rows(mask_rows)
    trk = None
    if marks:
        from .mark import MarkSet
        if not track:                                      # with both, the track is the link someone already made of them
            from . import autolink
            say("[track] from the hand marks")
            link = autolink.link_from_marks_file(clip, marks, prefix, masks=masks, say=say)
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
    if "survey" in want:
        say("[survey] cadence and transients")
        try:
            f = survey(clip, masks, procs).into(case)
            say(f"  repeats {f.fields['repeated_frames']}, transients {len(f.fields['transients'])}")
        except Exception as e:
            failed("survey", e)

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
            f = tracksheet.sheet(clip, [trk], prefix, dark=dark, title=rec["title"] if rec else None, procs=procs,
                                 say=say, **(sheet or {}))
            how = "--i-looked"
            if callable(i_looked):                         # a window shows the sheet and asks; a command line was told
                i_looked, how = bool(i_looked(f.files[0])), "asked with the sheet on the screen"
            f.result = dict(sheet=f"{prefix}_all_frames.jpg", reviewed=f"yes ({how})" if i_looked else "NOT CONFIRMED")
            f.fields["reviewed"] = bool(i_looked)
            if not i_looked:
                f.needs.append("confirmation that the track sheet was examined: every number below "
                               "assumes the track is on the object in every frame")
                f.notes.append("The track sheet was generated but not confirmed as examined, so the "
                               "object measurements below are **provisional**.")
            f.into(case, command=f"mcdonald tracksheet {shlex.quote(video_arg)}" + _flags(track=track, dark=dark) + window)
            files += f.files
        except (Exception, SystemExit) as e:
            failed("verify", e)

    # ---- 4 layers -------------------------------------------------------------------
    if "layers" in want:
        say("[layers] background, layer by layer")
        try:
            from . import layers
            if trk:
                if progress:
                    progress(f"layers: {clip.n1 - clip.n0 - 4} frame pairs, about a second each")
                f = layers.measure(clip, masks, rows, trk, names=dict(p.split("=") for p in names.split(",")) if names else None,
                                   dark_below=dark_below, out=prefix, procs=procs, say=say)
                say("  " + "\n  ".join(layers.said(f.fields)))
            else:
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
            f = scale(clip, graticule, fov, ref_px, ref_m).into(case)
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
            ref = dict(px=ref_px, len_m=ref_m, what="in-frame reference") if ref_px and ref_m else None
            f = kinematics(trk, clip.fps, clip.W, tag, k, range_m=range_m, size_px=size_px, ref=ref)
            if f.carry:
                say("  " + f.carry["reduction"].report().replace("\n", "\n  "))
            f.into(case)
        except Exception as e:
            failed("kinematics", e)

    # ---- co-motion (optional, needs D) ----------------------------------------------
    if trk and diameter and "comotion" in want:
        say("[comotion] with the texture, or through it?")
        try:
            from . import comotion as com
            f = com.measure(clip, trk, diameter, masks=masks, rows=rows, step=2, out=prefix, say=say)
            f.into(case, command=f"mcdonald comotion {shlex.quote(video_arg)}" + _flags(track=track, diameter=diameter, step=2)
                   + window + _flags(mask_rows=mask_rows))
            files += f.files
            if f.fields["pairs"]:
                w = f.fields["whole"]
                say(f"  {f.fields['verdict']}: {w['rel_D']:.1f} D relative ({w['rel_D_per_s']:.2f} D/s)")
        except Exception as e:
            failed("comotion", e)

    # ---- 7 integrity ----------------------------------------------------------------
    if "integrity" in want:
        say("[integrity] altered? object added?  (the long one)")
        try:
            from . import integrity as integ
            f = integ.examine(clip, rec, trk, size=size, dark=dark, rows=rows, out=prefix, tag=tag, procs=procs,
                              say=say, progress=progress)
            f.into(case, command=f"mcdonald integrity {shlex.quote(video_arg)}"
                   + _flags(track=track, size=size if trk and size != 9.0 else None, dark=bool(trk) and dark) + window
                   + _flags(mask_rows=mask_rows))
            files += f.files
        except (Exception, SystemExit) as e:
            failed("integrity", e)

    # ---- 8 report -------------------------------------------------------------------
    if "report" in want:
        path = case.write(str(prefix))
        files += [path, f"{prefix}_case.json"]
        say(f"\n{'=' * 70}\n{case.bottom_line()}\n{'=' * 70}\n\nfull report: {path}")
    return case, clip, files
