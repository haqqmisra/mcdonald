"""`mcdonald report` -- a case's report, from the case file, without measuring anything again.

    mcdonald report pr144/pr144_case.json               # write pr144_case.md again from the case file
    mcdonald report pr144/pr144_case.json --i-looked    # the track sheet has now been looked at: say so
    mcdonald report pr23/pr23_case.json --fov 2.5 --range 9000   # known now: the speed worked out again
    mcdonald report pr23/pr23_case.json --forget range  # that range was wrong: worked out again without it
    mcdonald report flyer1 --index                      # a video's several objects (`run --each`): their list again

A case measured before its track sheet was looked at says that every object measurement in it
is provisional. Looking at the sheet afterwards does not change a number, only whether the
numbers can be trusted, so the case is read back from its `_case.json`, the track sheet is
recorded as looked at, and the report is written again. The window's report page has the same
thing as a button. A case that is one of a video's several objects (`mcdonald run --each DIR`) has
its line in DIR's list brought up to date as well; `--index` writes that list again from the folders.

Something learned about the video after it was measured -- the field of view, the range, a thing
of known size in the picture, the speeds a report gave -- changes only the arithmetic from the
track's rate in pixels to a speed. Given here (the options are `run`'s, in the same units), the
scale and kinematics stages are worked out again from the case's track, on the frames it was
measured on, with what the case already knew and these over it; nothing else is measured again,
and the numbers are the ones `run` gives when it is told the same from the start. The window's
report card asks for the same things ("Add what you know")."""
import argparse
import shlex
import sys
from pathlib import Path

from . import clip as vf
from .report import Case, emit, envelope, said_to_stderr
from .stages import AFTER, KNOWN


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__[__doc__.index("    mcdonald report"):])
    ap.add_argument("case", help="a <tag>_case.json that `mcdonald run` (or the window's Measure) wrote; with --index, the "
                                 "folder that holds a video's object-1, object-2 ... folders")
    ap.add_argument("--index", action="store_true",
                    help="the argument is a folder of several objects' cases (`mcdonald run --each DIR`): write its list, "
                         "<tag>_objects.md and .json, again from what is in the folders")
    ap.add_argument("--i-looked", action="store_true",
                    help="you have looked at the case's track sheet (<tag>_all_frames.jpg), and the track is on the "
                         "object in every frame: the report stops calling the object measurements provisional")
    after = [k for k in KNOWN if k.name in AFTER]     # what can be known after the measuring: the rows of `run` that only reckon
    for k in after:
        ap.add_argument(k.flag, dest=k.name, type=k.kind, help=k.help + " (as for `run`). The speed is worked out again with it")
    ap.add_argument("--forget", metavar="NAMES",
                    help="what the case was told that is not known after all, by the options' names, comma separated (such as "
                         "range,fov): the speed is worked out again without them")
    ap.add_argument("--workdir", help="where the case's frames are, or are to be put, for working the speed out again "
                                      "(as for `run`)")
    ap.add_argument("--json", action="store_true", help="print the case as JSON on stdout, in the envelope every command prints")
    args = ap.parse_args()
    path = Path(args.case)
    say = (lambda *a: print(*a, file=sys.stderr)) if args.json else print
    flag_of = {k.flag[2:]: k.name for k in after}
    known = {k.name: getattr(args, k.name) for k in after if getattr(args, k.name) is not None}
    for word in [w.strip() for w in (args.forget or "").split(",") if w.strip()]:
        if word not in flag_of:
            ap.error(f"--forget {word}: name one of {', '.join(flag_of)}")
        if flag_of[word] in known:
            ap.error(f"--forget {word} and --{word} at once: say which")
        known[flag_of[word]] = None
    if args.index:
        from . import several
        if args.i_looked or known:
            ap.error("--i-looked and what is known are said of one case, not of a list: give that object's <tag>_case.json")
        page, rows = several.index(path) if path.is_dir() else (None, [])
        if page is None:
            raise vf.Stop(f"{args.case}: no folder object-1, object-2 ... with an object's marks in it", vf.EXIT_NOTHING)
        say(f"wrote {page}: {len(rows)} object{'s' if len(rows) != 1 else ''}, {sum(1 for r in rows if r['measured'])} measured")
        if args.json:
            emit(envelope("report", {"case": str(path), "index": True}, None, [str(page), str(page)[:-3] + ".json"],
                          {"objects": rows, "list": str(page)}))
        return 0
    if not path.name.endswith("_case.json") or not path.exists():
        raise vf.Stop(f"{args.case}: give the <tag>_case.json a run wrote", vf.EXIT_INPUT)
    if known:
        from .stages import add_known
        typed = lambda v: f"{v:.15g}" if isinstance(v, float) else str(v)
        cmd = (f"mcdonald report {shlex.quote(str(path))}"
               + "".join(f" {k.flag} {shlex.quote(typed(known[k.name]))}" for k in after if known.get(k.name) is not None)
               + (f" --forget {args.forget}" if args.forget else ""))
        try:
            with said_to_stderr(args.json):           # the figures say where they went: with --json, stdout is the envelope's
                case, md = add_known(path, workdir=args.workdir, command=cmd, say=say, **known)
        except ValueError as e:
            raise vf.Stop(str(e), vf.EXIT_NOTHING)
        say(f"the speed is worked out again with what is known now; wrote {md}")
        if not args.i_looked:
            from . import several
            page = several.listed(path)
            if page:
                say(f"and its line in the list of this video's objects: {page}")
    if args.i_looked:
        from .stages import confirm_sheet
        try:
            case, md = confirm_sheet(path, "looked at afterwards, and said so with --i-looked",
                                     command=f"mcdonald report {shlex.quote(str(path))} --i-looked")
        except ValueError as e:
            raise vf.Stop(str(e), vf.EXIT_NOTHING)
        say(f"the track sheet is recorded as looked at; wrote {md}")
        from . import several
        page = several.listed(path)
        if page:
            say(f"and its line in the list of this video's objects: {page}")
    elif not known:
        case = Case.load(path)
        md = case.write(str(path)[:-len("_case.json")])
    say(case.bottom_line())
    if args.json:
        emit(envelope("report", {"case": str(path), "i_looked": args.i_looked, "known": known}, None, [md, str(path)],
                      {"bottom_line": case.bottom_line(), "conclusion": dict(zip(("label", "headline"), case.conclusion())),
                       "identified_by": case.identified_by,
                       "stages": {n: st["result"] for n, st in case.stages.items()},
                       "fields": {n: st["fields"] for n, st in case.stages.items()}},
                      [(f"{n}: {t}", w) for n, st in case.stages.items() for t, w in st["no_power"]],
                      [f"{x} ({n})" for n, st in case.stages.items() for x in st["needs"]], case.notes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
