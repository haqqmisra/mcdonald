"""`mcdonald report` -- a case's report, from the case file, without measuring anything again.

    mcdonald report pr144/pr144_case.json               # write pr144_case.md again from the case file
    mcdonald report pr144/pr144_case.json --i-looked    # the track sheet has now been looked at: say so

A case measured before its track sheet was looked at says that every object measurement in it
is provisional. Looking at the sheet afterwards does not change a number, only whether the
numbers can be trusted, so the case is read back from its `_case.json`, the track sheet is
recorded as looked at, and the report is written again. The window's report page has the same
thing as a button."""
import argparse
import shlex
import sys
from pathlib import Path

from . import clip as vf
from .report import Case, emit, envelope


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__[__doc__.index("    mcdonald report"):])
    ap.add_argument("case", help="a <tag>_case.json that `mcdonald run` (or the window's Measure) wrote")
    ap.add_argument("--i-looked", action="store_true",
                    help="you have looked at the case's track sheet (<tag>_all_frames.jpg), and the track is on the "
                         "object in every frame: the report stops calling the object measurements provisional")
    ap.add_argument("--json", action="store_true", help="print the case as JSON on stdout, in the envelope every command prints")
    args = ap.parse_args()
    path = Path(args.case)
    if not path.name.endswith("_case.json") or not path.exists():
        raise vf.Stop(f"{args.case}: give the <tag>_case.json a run wrote", vf.EXIT_INPUT)
    say = (lambda *a: print(*a, file=sys.stderr)) if args.json else print
    if args.i_looked:
        from .stages import confirm_sheet
        try:
            case, md = confirm_sheet(path, "looked at afterwards, and said so with --i-looked",
                                     command=f"mcdonald report {shlex.quote(str(path))} --i-looked")
        except ValueError as e:
            raise vf.Stop(str(e), vf.EXIT_NOTHING)
        say(f"the track sheet is recorded as looked at; wrote {md}")
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
