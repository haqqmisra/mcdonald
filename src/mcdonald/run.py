"""`mcdonald run` — one clip through every stage, into one report.

The stages, in the order their dependencies demand:

    0 ingest      what is this file? exact rational fps, container, provenance
    1 survey      cadence (repeats, catch-up steps), transients, symbology map
    2 track       where is the object? (supplied, or attempted)
    3 verify      is the track on the object in EVERY frame?  <- the gate
    4 layers      how does the background move, in how many layers?
    5 scale       what bounds k? graticule, reference object, zoom chain
    6 kinematics  what does the motion permit? bounds, not a speed
    7 integrity   altered? object added? + the synthetic-insert self-test
    8 report      the case report

**Stage 3 is a gate, and it is deliberate.** Nothing downstream of it runs
until a track sheet exists, because every measurement after it inherits the
assumption that the track is on the object. On the clip this toolkit was
developed against, the first automatic tracker spent seven frames locked to a
cloud feature 100 px away and produced a clean, wrong rate. `--i-looked` is
how you assert you have looked at the sheet; there is no flag that skips
making it.

The driver is thin: this file is a command line and nothing else. The case is
made by `stages.run_case`, which has no interface in it, and each stage is the
same function the stage's own command calls -- so a result from `mcdonald run`
and one from `mcdonald layers` are the same number, and a stage that fails or
has nothing to work with is recorded as such rather than crashing the run.

**More than one object in a video is more than one case.** `--each DIR` takes a
folder that holds one folder for each object (`object-1`, `object-2` ...), each
with that object's marks, and makes a case of every one in turn, over the frames
it is in (`several.run_each`); `DIR/<tag>_objects.md` lists them. It is what the
window's "Follow and measure the ticked ones" does with the rows chosen in Find.
"""
from .progress import PROCS_HELP, to_stderr
from .report import emit, envelope, inputs_of, said_to_stderr
from .stages import KNOWN, STAGES, run_case


def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", help="CSV with frame and x/y columns. Without one, the "
                                    "object stages are skipped and say so.")
    ap.add_argument("--marks", metavar="JSON",
                    help="a _marks.json from `mcdonald mark`, instead of --track: the track is linked from the "
                         "hand marks first, and written to the case directory as <tag>_autotrack.csv")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--out", metavar="DIR", help="case directory (default: ./<tag>)")
    ap.add_argument("--each", metavar="DIR",
                    help="more than one object in this video: DIR holds a folder for each (object-1, object-2 ...), each with "
                         "the marks of one object (`mcdonald mark VIDEO --set ... --out DIR/object-1`). Every one is linked "
                         "and measured in turn, over the frames it is in and two seconds either side, into its own folder, "
                         "and DIR/<tag>_objects.md lists them. Instead of --track, --marks and --out; no track sheet is "
                         "asked about, so each report is provisional until `mcdonald report ... --i-looked`")
    ap.add_argument("--again", action="store_true",
                    help="with --each: measure every object again, also one that has a report from the same marks")
    ap.add_argument("--objects", type=int, metavar="N",
                    help="with --each: how many objects you are looking for. The list says how many were followed against "
                         "it, and where fewer things were found than N and one is a group of points, its members (each seen "
                         "on 60 frames or more) are made objects of their own and measured after the rest")
    ap.add_argument("--only", help="run only these stages, comma separated")
    ap.add_argument("--skip", help="skip these stages, comma separated")
    ap.add_argument("--i-looked", action="store_true",
                    help="assert you have looked at the track sheet from a previous run. "
                         "Without it the stages that depend on the track being right are "
                         "marked provisional in the report.")
    ap.add_argument("--dark", action="store_true", default=None,
                    help="the object is darker than the scene (with --marks, the polarity the marks chose)")
    for k in KNOWN:                                   # what a person may know: the window's Measure form is made of the same rows
        ap.add_argument(k.flag, dest=k.name, type=k.kind, help=k.help)
    ap.add_argument("--procs", type=int, default=None, help=PROCS_HELP)
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--json", action="store_true",
                    help="print the case as JSON on stdout (what <tag>_case.json holds, in the envelope every "
                         "command prints); everything else goes to stderr")
    args = ap.parse_args()
    unknown = [x for x in (args.only or "").split(",") + (args.skip or "").split(",") if x and x not in STAGES]
    if unknown:
        ap.error(f"no such stage: {', '.join(unknown)} (the stages are {', '.join(STAGES)})")
    kw = {k: v for k, v in vars(args).items() if k not in ("json", "only", "skip", "each", "again", "objects")}
    if args.each:
        return each(ap, args, kw)
    if args.again:
        ap.error("--again goes with --each")
    if args.objects is not None:
        ap.error("--objects goes with --each: how many objects to look for in the folder of them")
    with said_to_stderr(args.json):
        case, clip, files = run_case(only=args.only.split(",") if args.only else None,
                                     skip=args.skip.split(",") if args.skip else None, progress=to_stderr(), **kw)
    if args.json:
        no_power = [(f"{n}: {t}", w) for n, st in case.stages.items() for t, w in st["no_power"]]
        needs = [f"{x} ({n})" for n, st in case.stages.items() for x in st["needs"]]
        emit(envelope("run", inputs_of(args), clip, files,
                      {"bottom_line": case.bottom_line(), "conclusion": dict(zip(("label", "headline"), case.conclusion())),
                       "identified_by": case.identified_by,
                       "stages": {n: st["result"] for n, st in case.stages.items()},
                       "fields": {n: st["fields"] for n, st in case.stages.items()}}, no_power, needs, case.notes))
    return 0


def each(ap, args, kw):
    """`run --each DIR`: a case for each object under DIR, in turn, and the list of them."""
    from . import several
    given = [f"--{k.replace('_', '-')}" for k in ("track", "marks", "out", "i_looked") if kw.pop(k)]
    if given:
        ap.error(f"{', '.join(given)} cannot go with --each: each object's marks and results are in its own folder under "
                 "the one given, and nobody is asked about a track sheet")
    if args.objects is not None and args.objects < 1:
        ap.error("--objects N: N is how many objects you are looking for, 1 or more")
    with said_to_stderr(args.json):
        things = several.run_each(kw.pop("video"), args.each, again=args.again, progress=to_stderr(), objects=args.objects,
                                  only=args.only.split(",") if args.only else None,
                                  skip=args.skip.split(",") if args.skip else None, **kw)
        page, rows = several.index(args.each, objects=args.objects)
        done = [t for t in things if t.state == "done"]
        count = several.tally(things, args.objects or several.asked_before(args.each))
        print(f"{len(done)} of {len(things)} object{'s' if len(things) != 1 else ''} measured; the list is {page}"
              + (f"\n{count['sentence']}" if count["sentence"] else ""))
    if args.json:
        cases = [(t.k, t.case) for t in things if t.case is not None]
        emit(envelope("run", inputs_of(args), None, [str(page), str(page)[:-3] + ".json"] + [str(f) for t in things for f in t.files],
                      {"objects": rows, "list": str(page), "asked": count["asked"], "tally": count,
                       "states": {f"object-{t.k}": t.state for t in things}},
                      [(f"object {k}: {n}: {test}", why) for k, c in cases for n, st in c.stages.items() for test, why in st["no_power"]],
                      [f"object {k}: {x} ({n})" for k, c in cases for n, st in c.stages.items() for x in st["needs"]],
                      [f"object {t.k}: {t.error}" for t in things if t.error]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
