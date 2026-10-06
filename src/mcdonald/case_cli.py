"""`mcdonald report` -- a case's report, from the case file, without measuring anything again.

    mcdonald report pr144/pr144_case.json               # write pr144_case.md again from the case file
    mcdonald report pr144/pr144_case.json --i-looked    # the track sheet has now been looked at: say so
    mcdonald report flyer1 --index                      # a video's several objects (`run --each`): their list again

A case measured before its track sheet was looked at says that every object measurement in it
is provisional. Looking at the sheet afterwards does not change a number, only whether the
numbers can be trusted, so the case is read back from its `_case.json`, the track sheet is
recorded as looked at, and the report is written again. The window's report page has the same
thing as a button. A case that is one of a video's several objects (`mcdonald run --each DIR`) has
its line in DIR's list brought up to date as well; `--index` writes that list again from the folders."""
import argparse
import shlex
import sys
from pathlib import Path

from . import clip as vf
from .report import Case, emit, envelope


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
    ap.add_argument("--json", action="store_true", help="print the case as JSON on stdout, in the envelope every command prints")
    args = ap.parse_args()
    path = Path(args.case)
    say = (lambda *a: print(*a, file=sys.stderr)) if args.json else print
    if args.index:
        from . import several
        if args.i_looked:
            ap.error("--i-looked is said of one case, not of a list: give that object's <tag>_case.json")
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
    else:
        case = Case.load(path)
        md = case.write(str(path)[:-len("_case.json")])
    say(case.bottom_line())
    if args.json:
        emit(envelope("report", {"case": str(path), "i_looked": args.i_looked}, None, [md, str(path)],
                      {"bottom_line": case.bottom_line(), "identified_by": case.identified_by,
                       "stages": {n: st["result"] for n, st in case.stages.items()},
                       "fields": {n: st["fields"] for n, st in case.stages.items()}},
                      [(f"{n}: {t}", w) for n, st in case.stages.items() for t, w in st["no_power"]],
                      [f"{x} ({n})" for n, st in case.stages.items() for x in st["needs"]], case.notes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
