"""`mcdonald <command>` — the command line.

Each subcommand is one question about a clip. They are deliberately separate:
the answers are not a pipeline yet, and a tool that cannot decide something
should say so rather than hand a number to the next stage.
"""
import sys

from . import __version__
from .clip import EXIT_CODES, EXIT_INPUT, EXIT_MISSING, EXIT_USAGE, MissingTool, NotAVideo, Stop, require_ffmpeg

COMMANDS = {
    "setup": ("run once after installing: is everything here, and what next?", "mcdonald.setup_cli"),
    "readme": ("print the technical README (for AI agents): every command, and how each step works", "mcdonald.readme_cli"),
    "run": ("every stage on one clip, into one case report", "mcdonald.run"),
    "look": ("see the clip with no window: an overview, a frame's candidates, a place enlarged", "mcdonald.look"),
    "mark": ("say which thing is the object: in a window, or with --set and no window", "mcdonald.mark"),
    "layers": ("how does the background move, and in how many layers?", "mcdonald.layers"),
    "integrity": ("has the clip been altered, was the object added?", "mcdonald.integrity"),
    "tracksheet": ("every frame tiled, with the tracked object circled", "mcdonald.tracksheet"),
    "symbology": ("boresight, north pointer, corner brackets -- the overlay's own readings", "mcdonald.symbology"),
    "comotion": ("does the object move WITH the texture around it, or THROUGH it?", "mcdonald.comotion"),
    "groups": ("is the object several points, and do they keep their places?", "mcdonald.groups"),
    "flicker": ("does its brightness beat -- and is the beat the object's, or the video's?", "mcdonald.flicker"),
    "kinematics": ("v_px -> omega -> what the motion permits (bounds, not a speed)", "mcdonald.kinematics_cli"),
    "report": ("a case's report again, from its _case.json: --i-looked once the track sheet is looked at", "mcdonald.case_cli"),
}

USAGE = f"""mcdonald {__version__} — measurement tools for single-sensor video of unidentified objects

For the graphical interface, type `mcdonald-gui`: it walks you through each
step of the analysis.

usage: mcdonald <command> [options] VIDEO

commands:
""" + "".join(f"  {n:<12} {d}\n" for n, (d, _) in COMMANDS.items()) + """
VIDEO is a path to any video file, or a PURSUE record id such as PR113 (the
video is downloaded the first time); MCDONALD_CATALOG names another catalog.
New here? `mcdonald setup` checks this computer and says what to do next.

Results go to a case directory: --out DIR, else ./<tag>.
`mcdonald <command> --help` for a command's options; `mcdonald readme` for all
of it; `mcdonald readme method` for what the measurements mean and how each one
fails; `mcdonald readme agents` for doing the whole job from here with no window.

Every command takes --json: one object on stdout (command, inputs, clip, files,
results, no_power, needs, exit, error), and everything else on stderr. `results`
holds the command's findings as fields -- numbers, not sentences -- and what it
printed for a person beside them as `said`.

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

    if cmd == "setup":                                    # it says what is missing, ffmpeg included: nothing is required first
        from . import setup_cli
        return setup_cli.main(argv[1:])
    if cmd == "readme":                                   # nor to read the documents
        from . import readme_cli
        return readme_cli.main(argv[1:])

    import importlib
    from . import update
    check = update.Check()                                # asked of GitHub while the command runs; said after it
    mod = importlib.import_module(COMMANDS[cmd][1])
    # Each tool parses sys.argv itself, so present it the command's own tail.
    sys.argv = [f"mcdonald {cmd}"] + argv[1:]
    code, error = _run(mod)
    if error and "--json" in argv[1:]:                    # it stopped before it could print its envelope
        from .report import emit, envelope
        emit(envelope(cmd, {"argv": argv[1:]}, exit_code=code, error=error))
    update.tell_cli(check)
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


if __name__ == "__main__":
    sys.exit(main())
