"""Does a shared case file give back its own numbers?  The check ROADMAP.md's 0.3 asks of every reference case.

    python3 tools/rerun_cases.py FILE.mcdonald [FILE ...] [--cases DIR] [--procs N] [--strict] [--json]

`mcdonald share rerun` with the reference-data folder looked in for the video as well (its pursue/ and footage/;
tests/reference_data.py finds it). Everything else -- the unpacking, the command each report records, the comparison
number for number, --strict -- is the package's (`mcdonald.rerun`), so that anyone who installed it can do the same:
`mcdonald share rerun FILE.mcdonald`. Exit code 1 if any file does not rerun to its numbers.

Takes minutes per object: the Technical Note's cases 3-11 min with integrity, the bird videos' stretches longer. Run it
through the job scheduler on a shared machine."""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE.parent / "tests"))

from mcdonald import rerun  # noqa: E402
from mcdonald.rerun import compare_cases, recorded_run, rerun_args  # noqa: E402,F401 -- as before, for scripts that import them
import reference_data  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="+", help="shared case files (.mcdonald)")
    ap.add_argument("--cases", help="where to unpack and rerun (default: a temporary folder, removed after)")
    ap.add_argument("--procs", type=int, help="worker processes for the stages")
    ap.add_argument("--strict", action="store_true", help="an object whose report tracked nothing counts as not rerunning")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    a = ap.parse_args(argv)
    say = (lambda *x: print(*x, file=sys.stderr, flush=True)) if a.json else (lambda *x: print(*x, flush=True))
    results, ok = rerun.rerun_files(a.files, a.cases, procs=a.procs, strict=a.strict, say=say,
                                    also=[reference_data.root() / "pursue", reference_data.footage()])
    if a.json:
        print(json.dumps(results, indent=1, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
