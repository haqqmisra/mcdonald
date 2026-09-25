"""`mcdonald-gui` — the window, for someone who has no terminal.

`mcdonald mark` assumes a command line: the clip is an argument, the frame
range and the case directory are flags, and whatever goes wrong is printed.
This is the same window started the other way. It asks for the clip, asks
which part of it and says what that will cost, keeps its cases in a folder the
person can see, and says what goes wrong in a dialog. It is a gui-script, so on
a desktop it opens no console, and `--desktop-entry` (or Help, in the window)
puts it in the applications menu on Linux.

    mcdonald-gui                      # ask for a clip
    mcdonald-gui CLIP.mp4             # what a file manager's "Open with" does
    mcdonald-gui --desktop-entry      # add it to the applications menu, and stop

Nothing is imported from Qt until it is known that Qt is there and has a
display to open on: without one Qt does not raise, it aborts the process.
"""
import os
import shutil
import sys
from pathlib import Path

ICONS = Path(__file__).with_name("icons")
INSTALL = "pip install --upgrade mcdonald        (or: pip install PySide6-Essentials)"


def tell(text):
    """Say something to a person before there is a Qt to say it with: on stderr, and in
    a Tk message box if there is a Tk, since a gui-script may have no stderr anyone sees."""
    print(f"mcdonald-gui: {text}", file=sys.stderr)
    try:
        import tkinter
        from tkinter import messagebox
        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("mcdonald", text)
        root.destroy()
    except Exception:                                 # no Tk, or no display for it either
        pass


def cannot_open():
    """Why the Qt window cannot open here, or None if it can."""
    import importlib.util
    if importlib.util.find_spec("PySide6") is None:
        return f"The window needs PySide6, which is not installed.\n\n    {INSTALL}"
    if sys.platform not in ("win32", "darwin") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return ("There is no screen to open a window on (neither DISPLAY nor WAYLAND_DISPLAY is set). "
                "All that the window does can also be done from a command line: see `mcdonald --help`.")
    return None


def desktop_entry(where=None):
    """Write mcdonald.desktop, so that the window starts from the applications menu and a
    video's "Open with". Returns the file. Linux (freedesktop) only: macOS and Windows
    have no equivalent that a Python package can write into place."""
    if sys.platform in ("win32", "darwin"):
        raise RuntimeError("Only a Linux desktop has this kind of applications menu. On this computer, start it as `mcdonald-gui`.")
    exe = shutil.which("mcdonald-gui") or str(Path(sys.argv[0]).resolve())
    if Path(exe).name != "mcdonald-gui":
        raise RuntimeError("mcdonald-gui was not found (it is not on the PATH), so a menu entry would have nothing to start. "
                           f"Install mcdonald first:  {INSTALL}")
    base = Path(where) if where else Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "applications"
    base.mkdir(parents=True, exist_ok=True)
    # The icon, at each size drawn for it, in the hicolor theme beside the entry (in `where`
    # itself, for a test), so that a menu shows the drawing made for its size.
    theme = (base.parent if where is None else base) / "icons" / "hicolor"
    for png in ICONS.glob("mcdonald-[0-9]*.png"):
        s = png.stem.split("-")[1]
        (theme / f"{s}x{s}" / "apps").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(png, theme / f"{s}x{s}" / "apps" / "mcdonald.png")
    path = base / "mcdonald.desktop"
    path.write_text("[Desktop Entry]\nType=Application\nName=mcdonald\n"
                    "GenericName=Video measurement\n"
                    "Comment=Find and mark an object in a video, let the computer follow it, and measure how it moves\n"
                    f"Exec={exe} %f\nIcon=mcdonald\nTerminal=false\n"
                    "Categories=Science;AudioVideo;Video;\n"
                    "MimeType=video/mp4;video/quicktime;video/x-matroska;video/x-msvideo;video/mpeg;video/mp2t;\n")
    return path


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="mcdonald-gui", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", nargs="?", help="a clip or a catalog id; asked for if left out")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--out", metavar="DIR", help="this clip's case directory (default: <cases folder>/<tag>)")
    ap.add_argument("--workdir")
    ap.add_argument("--desktop-entry", action="store_true", help="add mcdonald to the applications menu (Linux), and stop")
    args = ap.parse_args(argv)

    if args.desktop_entry:
        try:
            print(f"wrote {desktop_entry()}")
            return 0
        except (OSError, RuntimeError) as ex:
            print(f"mcdonald-gui: {ex}", file=sys.stderr)
            return 1

    why = cannot_open()
    if why:
        tell(why)
        return 3
    from . import update
    check = update.Check()                            # asked of GitHub while Qt starts
    from . import mark_qt
    from .clip import MissingTool, require_ffmpeg
    mark_qt.application()
    try:
        require_ffmpeg()
    except MissingTool as ex:
        mark_qt.complain(None, str(ex))
        return 3
    if mark_qt.offer_update(check.result(3)):
        return 0                                      # closed, for the helper to update it and open it again
    mark_qt.use_remembered_catalog()
    mark_qt.use_remembered_storage()

    video = args.video
    while True:
        if video is None:
            video = mark_qt.choose_start()
            if video is None:
                return 0
        w = mark_qt.open_session(video, args.n0, args.n1, args.out, workdir=args.workdir, cases=mark_qt.cases_folder())
        if w is not None:
            w.run()
            return 0
        video = None                                  # it did not open, and they have been told why: ask again


if __name__ == "__main__":
    sys.exit(main())
