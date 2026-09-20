"""`mcdonald <command>` — the command line.

Each subcommand is one question about a clip. They are deliberately separate:
the answers are not a pipeline yet, and a tool that cannot decide something
should say so rather than hand a number to the next stage.
"""
import sys

from . import __version__
from .clip import MissingTool, require_ffmpeg

COMMANDS = {
    "run": ("every stage on one clip, into one case report", "mcdonald.run"),
    "mark": ("find the object and click it on a few frames (opens a window)", "mcdonald.mark"),
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
the measurements mean and how each one fails.
"""


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
        return 2

    try:
        require_ffmpeg()
    except MissingTool as e:
        print(f"mcdonald: {e}", file=sys.stderr)
        return 3

    import importlib
    mod = importlib.import_module(COMMANDS[cmd][1])
    # Each tool parses sys.argv itself, so present it the command's own tail.
    sys.argv = [f"mcdonald {cmd}"] + argv[1:]
    return mod.main() or 0


if __name__ == "__main__":
    sys.exit(main())
