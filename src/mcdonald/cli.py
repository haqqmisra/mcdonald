"""`mcdonald <command>` — the command line.

Each subcommand is one question about a clip. They are deliberately separate:
the answers are not a pipeline yet, and a tool that cannot decide something
should say so rather than hand a number to the next stage.
"""
import sys

from . import __version__
from .clip import EXIT_CODES, EXIT_INPUT, EXIT_MISSING, EXIT_USAGE, MissingTool, NotAVideo, Stop, require_ffmpeg

COMMANDS = {
    "run": ("every stage on one clip, into one case report", "mcdonald.run"),
    "look": ("see the clip with no window: an overview, a frame's candidates, a place enlarged", "mcdonald.look"),
    "mark": ("say which thing is the object: in a window, or with --set and no window", "mcdonald.mark"),
    "layers": ("how does the background move, and in how many layers?", "mcdonald.layers"),
    "integrity": ("has the clip been altered, was the object added?", "mcdonald.integrity"),
    "tracksheet": ("every frame tiled, with the tracked object circled", "mcdonald.tracksheet"),
    "symbology": ("boresight, north pointer, corner brackets -- the overlay's own readings", "mcdonald.symbology"),
    "comotion": ("does the object move WITH the texture around it, or THROUGH it?", "mcdonald.comotion"),
    "kinematics": ("v_px -> omega -> what the motion permits (bounds, not a speed)", "mcdonald.kinematics_cli"),
}

USAGE = f"""mcdonald {__version__} — measurement tools for single-sensor video of unidentified objects

usage: mcdonald <command> [options] VIDEO

commands:
""" + "".join(f"  {n:<12} {d}\n" for n, (d, _) in COMMANDS.items()) + """
VIDEO is a path to any video file, or a record id (PR144, 06:PR001) when a
catalog is configured via MCDONALD_CATALOG.

Results go to a case directory: --out DIR, else ./<tag>.
`mcdonald <command> --help` for a command's options; docs/method.md for what
the measurements mean and how each one fails; docs/agents.md for doing the
whole job from here with no window. `mcdonald-gui` is the window with no
command line.

Every command takes --json: one object on stdout (command, inputs, clip, files,
results, no_power, needs, exit, error), and everything else on stderr.

""" + EXIT_CODES


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE, end="")
        return 0
    if argv[0] in ("-V", "--version"):
        print(__version__)
        return 0

    cmd = argv[0]
    if cmd not in COMMANDS:
        print(f"mcdonald: unknown command {cmd!r}\n", file=sys.stderr)
        print(USAGE, end="", file=sys.stderr)
        return EXIT_USAGE

    import importlib
    mod = importlib.import_module(COMMANDS[cmd][1])
    # Each tool parses sys.argv itself, so present it the command's own tail.
    sys.argv = [f"mcdonald {cmd}"] + argv[1:]
    own_json = getattr(mod, "PRINTS_JSON", False)         # it makes its own envelope, with results as fields
    if "--json" in argv[1:] and not own_json:
        return _enveloped(cmd, mod, argv[1:])
    code, error = _run(mod)
    if error and own_json and "--json" in argv[1:]:        # it stopped before it could print one
        from .report import emit, envelope
        emit(envelope(cmd, {"argv": argv[1:]}, exit_code=code, error=error))
    return code


def _run(mod):
    """(exit code, the sentence that went with it). An expected failure is a sentence and
    a code from clip.EXIT_CODES; anything else is a bug, and is left to raise."""
    try:
        require_ffmpeg()
        return (mod.main() or 0), None
    except MissingTool as e:
        code, error = EXIT_MISSING, str(e)
    except Stop as e:
        code, error = e.exit_code, str(e)
    except (NotAVideo, FileNotFoundError) as e:
        code, error = EXIT_INPUT, str(e)
    except SystemExit as e:                               # argparse's (a number), or a module's own message
        if not isinstance(e.code, str):
            return (e.code or 0), None
        code, error = (EXIT_MISSING if "window" in e.code or "display" in e.code else EXIT_INPUT), e.code
    print(f"mcdonald: {error}", file=sys.stderr)
    return code, error


def _enveloped(cmd, mod, args):
    """--json for a command that prints prose: the same envelope, with what it said as
    lines and the files it wrote found by looking. Its numbers are still in the prose --
    `look`, `mark` and `run` have them as fields -- but what ran, what it wrote, whether it
    worked and why not are the same from every command."""
    import contextlib
    import io
    import time
    from pathlib import Path
    from .report import emit, envelope
    sys.argv = [a for a in sys.argv if a != "--json"]
    said, began = io.StringIO(), time.time() - 1
    with contextlib.redirect_stdout(said):
        code, error = _run(mod)
    sys.stderr.write(said.getvalue())
    lines = [ln for ln in said.getvalue().splitlines() if ln.strip()]
    named = {w.strip(".,;:()'\"") for ln in lines for w in ln.split()}
    files = sorted(str(p) for p in {Path(w) for w in named if "/" in w or "." in w}
                   if p.is_file() and p.stat().st_mtime >= began)
    results = {"said": lines}
    for f in files:                                       # a report the command wrote as JSON is its results
        if f.endswith(".json"):
            import json
            try:
                results[Path(f).name] = json.loads(Path(f).read_text())
            except ValueError:
                pass
    emit(envelope(cmd, {"argv": args}, files=files, results=results, exit_code=code, error=error))
    return code


if __name__ == "__main__":
    sys.exit(main())
