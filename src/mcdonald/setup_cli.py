"""`mcdonald setup` -- run once after `pip install`: is everything here, and what next?

pip cannot print anything after it installs a package, so this is what the install
instructions send people to next (Jacob, 2026-09-24). It checks what mcdonald needs and
says, for this computer, how to get what is missing:

    Python        3.10 or newer
    ffmpeg        and ffprobe, on the PATH
    the window    PySide6 (the `gui` extra), and a screen to draw on
    storage       the folder videos and their frames go in, and the room there
    catalog       the PURSUE list, or the one MCDONALD_CATALOG names
    downloads     one small request to DVIDS: the network, and on a Mac, Python's certificates

and ends with what to type next, and where the short README is. `--desktop` also adds mcdonald to the applications menu
(Linux); `--offline` leaves out the download check; `--json` prints the checks as one object.
Exit 0 when what the command line needs is there (ffmpeg, Python), 3 when it is not.
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys

from . import __version__, catalog, storage
from .clip import EXIT_MISSING

REPO = "git+https://github.com/haqqmisra/mcdonald"
README = "https://github.com/haqqmisra/mcdonald#readme"          # the short one, for a person


def _system():
    return {"darwin": "mac", "win32": "windows"}.get(sys.platform, "linux")


def _ffmpeg_help():
    return {"mac": "install it with Homebrew: `brew install ffmpeg` (Homebrew itself: https://brew.sh)",
            "windows": "install it with `winget install Gyan.FFmpeg`, then open a new terminal so the PATH is read again",
            "linux": "install it with your package manager: `sudo dnf install ffmpeg` (Fedora, with RPM Fusion) or "
                     "`sudo apt install ffmpeg` (Debian, Ubuntu)"}[_system()]


def checks(offline=False):
    """[(name, ok, what it found, what to do)]; ok is True, False, or None (not needed for the command line)."""
    out = []
    v = sys.version_info
    out.append(("Python", v >= (3, 10), f"{platform.python_version()} ({sys.executable})",
                "" if v >= (3, 10) else "mcdonald needs Python 3.10 or newer"))

    missing = [t for t in ("ffmpeg", "ffprobe") if shutil.which(t) is None]
    if missing:
        out.append(("ffmpeg", False, f"{' and '.join(missing)} not found on the PATH", _ffmpeg_help()))
    else:
        first = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
        out.append(("ffmpeg", True, " ".join(first.split()[:3]) + f" ({shutil.which('ffmpeg')})", ""))

    try:
        import PySide6                                # noqa: F401 -- only whether it is there
        from PySide6 import __version__ as qt
        screen = _system() != "linux" or bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        out.append(("the window", True if screen else None, f"PySide6 {qt}" + ("" if screen else "; no screen here (no DISPLAY)"),
                    "" if screen else "the window needs a desktop; the command line works without one"))
    except ImportError:
        out.append(("the window", None, "PySide6 is not installed",
                    f"for the window, install the gui extra: pip install \"mcdonald[gui] @ {REPO}\""))

    home = storage.home()
    probe = home
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        free = shutil.disk_usage(probe).free
        writable = os.access(probe, os.W_OK)
    except OSError:
        free, writable = 0, False
    out.append(("storage", writable, f"{home} ({free / 1e9:.0f} GB free)" + ("" if home.exists() else "; made when first used"),
                "" if writable else f"{probe} cannot be written to: set MCDONALD_HOME to a folder that can"))

    cat = catalog.active()
    n = len(cat.videos())
    out.append(("catalog", True, f"{cat.label}, {n} videos" if n else "none (MCDONALD_CATALOG=none): give videos by their path", ""))

    if offline:
        out.append(("downloads", None, "not checked (--offline)", ""))
    else:
        recs = [r for r in catalog.ShippedCatalog().videos() if r.get("url")]
        url = min(recs, key=lambda r: r["bytes"])["url"] if recs else None
        out.append(("downloads",) + _can_download(url))
    return out


def _can_download(url):
    """(ok, found, what to do) for one HEAD request to DVIDS."""
    if not url:
        return None, "no address to try", ""
    import ssl
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD", headers={"User-Agent": "mcdonald"}),
                                    timeout=20) as r:
            return True, f"DVIDS answered ({r.status})", ""
    except (ssl.SSLError, urllib.error.URLError) as e:
        why = getattr(e, "reason", e)
        if isinstance(why, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(why):
            fix = ("Python cannot check the website's certificate. With Python from python.org on a Mac, run "
                   "\"Install Certificates.command\" once (in Applications → Python 3.x), then try again"
                   if _system() == "mac" else "Python cannot check the website's certificate: `pip install --upgrade certifi`")
            return False, "certificate not trusted", fix
        return False, f"could not reach DVIDS: {why}", "check the internet connection; videos given by their path still work"
    except OSError as e:
        return False, f"could not reach DVIDS: {e}", "check the internet connection; videos given by their path still work"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mcdonald setup", description=__doc__.split("\n\n")[0])
    ap.add_argument("--desktop", action="store_true", help="also add mcdonald to the applications menu (Linux)")
    ap.add_argument("--offline", action="store_true", help="leave out the download check")
    ap.add_argument("--json", action="store_true", help="the checks as one JSON object on stdout")
    args = ap.parse_args(argv)

    got = checks(args.offline)
    desktop = None
    if args.desktop:
        try:
            from .gui import desktop_entry
            desktop = f"added: {desktop_entry()}"
        except (OSError, RuntimeError) as e:
            desktop = f"not added: {e}"
    needed = all(ok for name, ok, _, _ in got if name in ("Python", "ffmpeg"))

    if args.json:
        print(json.dumps(dict(command="setup", mcdonald=__version__, ready=needed, desktop=desktop,
                              checks=[dict(name=n, ok=ok, found=f, fix=x) for n, ok, f, x in got]), indent=1))
        return 0 if needed else EXIT_MISSING

    mark = {True: "ok  ", False: "NO  ", None: "--  "}
    print(f"mcdonald {__version__}: checking this computer\n")
    for name, ok, found, fix in got:
        print(f"  {mark[ok]}{name:<11} {found}")
        if fix:
            print(f"      {'':<11} → {fix}")
    if desktop:
        print(f"\n  applications menu: {desktop}")
    print()
    if not needed:
        print("Fix what says NO above, then run `mcdonald setup` again.")
        return EXIT_MISSING
    window = next(ok for n, ok, _, _ in got if n == "the window")
    print("Ready. Next:")
    if window:
        print("  mcdonald-gui                 the window: open a video, find the object, follow it, measure")
        if _system() == "linux" and not args.desktop:
            print("  mcdonald setup --desktop     add it to the applications menu")
    print("  mcdonald run PR149           the whole job on the command line (downloads PR149 the first time)")
    print("  mcdonald --help              every command")
    print(f"\nHow to use it, in short:  {README}")
    print("All of it, for technical users and AI agents:  mcdonald readme")
    return 0


if __name__ == "__main__":
    sys.exit(main())
