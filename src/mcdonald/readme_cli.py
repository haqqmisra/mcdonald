"""`mcdonald readme` -- the documents, from the install itself.

Jacob, 2026-09-25: an AI agent told to use mcdonald should find everything it needs in
what was installed, not on GitHub. So the technical README and the documents it names are
copied into the package when it is built (setup.py), and this prints them:

    mcdonald readme            README-technical.md: every command, how each step works
    mcdonald readme method     docs/method.md: what each measurement means, how each fails
    mcdonald readme agents     docs/agents.md: the whole job from the command line, no window
    mcdonald readme install    docs/install.md: installing, step by step

An editable install (a clone, `pip install -e`) has no copies: it reads the repository's.
"""
import argparse
import sys
from pathlib import Path

DOCS = {"technical": "README-technical.md", "method": "method.md", "agents": "agents.md", "install": "install.md"}
REPO = {"technical": "README-technical.md", "method": "docs/method.md", "agents": "docs/agents.md",
        "install": "docs/install.md"}


def path(name):
    """Where the document is: the package's copy, else the repository's (an editable install)."""
    shipped = Path(__file__).parent / "docs" / DOCS[name]
    if shipped.is_file():
        return shipped
    return Path(__file__).resolve().parents[2] / REPO[name]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mcdonald readme", description=__doc__.split("\n\n")[0])
    ap.add_argument("name", nargs="?", default="technical", choices=list(DOCS),
                    help="which document (default: technical, the README for AI agents and technical users)")
    args = ap.parse_args(argv)
    p = path(args.name)
    if not p.is_file():
        print(f"mcdonald readme: {DOCS[args.name]} is not in this install", file=sys.stderr)
        return 4
    text = p.read_text(encoding="utf-8")
    if args.name == "technical":
        text = ("(Printed by `mcdonald readme`. The documents it names print with `mcdonald readme method`, "
                "`mcdonald readme agents` and `mcdonald readme install`.)\n\n" + text)
    try:
        sys.stdout.reconfigure(encoding="utf-8")      # a pipe on Windows is cp1252, and the text has → and —
    except (AttributeError, ValueError):
        pass
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
