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
    version       this one against the newest, asked now (the forced update check)

and ends with what to type next: the two interfaces, and a prompt for an AI agent. On a Linux
desktop it also puts mcdonald in the applications menu (Jacob, 2026-09-25: setup does it, not a
Help item), unless `--no-desktop`; `--offline` leaves out the download check and the version's;
`--json` prints the checks as one object.
Exit 0 when what the command line needs is there (ffmpeg, Python), 3 when it is not.

`mcdonald setup --install-gpu` does one thing instead, and none of the above: it installs the add-on
for an NVIDIA graphics card (`mcdonald.addon`), as the window's Preferences does with a button.
"""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import textwrap

from . import __version__, catalog, storage
from .clip import EXIT_MISSING


RULE = "-" * 66
# What comes after "Ready.", in Jacob's words (2026-09-25); paragraphs wrap to 80 columns.
_NEXT = [
    "The mcdonald graphical interface is designed to prompt human users through the steps of analysis. "
    "To start the graphical interface:",
    "  mcdonald-gui",
    "The command-line interface is designed for developers, advanced users, and AI agents. To start the "
    "command-line interface and see a summary of options:",
    "  mcdonald",
    "You can invoke an AI agent to assist at any point in the analysis, whether before or after a human has "
    "looked at the video. Here is a sample prompt that you can pass to your favorite command-line AI model:",
    "  Please use the mcdonald toolkit to analyze the PR144 video released under PURSUE. Run mcdonald readme "
    "to get started.",
]
NEXT = (RULE + "\n\n"
        + "\n\n".join(textwrap.fill(t.lstrip(), 80, initial_indent=" " * (len(t) - len(t.lstrip())),
                                     subsequent_indent=" " * (len(t) - len(t.lstrip()))) for t in _NEXT)
        + "\n\n" + RULE + "\nCopyright (c) 2026 Jacob Haqq Misra. Released under the BSD 3-Clause License.")


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
        first = subprocess.run(["ffmpeg", "-version"], capture_output=True, encoding="utf-8", errors="replace").stdout.split("\n")[0]
        out.append(("ffmpeg", True, " ".join(first.split()[:3]) + f" ({shutil.which('ffmpeg')})", ""))

    try:
        import PySide6                                # noqa: F401 -- only whether it is there
        from PySide6 import __version__ as qt
        screen = _system() != "linux" or bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        out.append(("the window", True if screen else None, f"PySide6 {qt}" + ("" if screen else "; no screen here (no DISPLAY)"),
                    "" if screen else "the window needs a desktop; the command line works without one"))
    except ImportError:
        out.append(("the window", None, "PySide6 is not installed",
                    "for the window: pip install --upgrade mcdonald (or pip install PySide6-Essentials)"))

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

    out.append(("graphics card",) + _graphics_card())

    cat = catalog.active()
    n = len(cat.videos())
    out.append(("catalog", True, f"{cat.label}, {n} videos" if n else "none (MCDONALD_CATALOG=none): give videos by their path", ""))

    if offline:
        out.append(("downloads", None, "not checked (--offline)", ""))
        out.append(("version", None, f"{__version__}; the newest not asked (--offline)", ""))
    else:
        recs = [r for r in catalog.ShippedCatalog().videos() if r.get("url")]
        url = min(recs, key=lambda r: r["bytes"])["url"] if recs else None
        out.append(("downloads",) + _can_download(url))
        out.append(("version",) + _newest())
    return out


def _graphics_card():
    """(ok, found, what to do) for the graphics card: never needed (None unless one is in use), so that a computer
    with none passes. Says which card computes, or which is here and what it would take to use it."""
    from . import gpu
    c = gpu.card()
    if c is not None:
        return True, f"{c.name} ({c.library}): the steps that can use it do", ""
    if gpu.asked() == gpu.NONE:
        return None, "not used: the CPU only was chosen (--gpu none, MCDONALD_GPU or Preferences)", ""
    cards = gpu.found()
    ours = gpu.usable(cards)
    if ours and not gpu.installed():
        from . import addon, update
        o = addon.offer(cards)
        found = f"{ours[0]['name']}, not used: the add-on for graphics cards (CuPy) is not installed"
        if o["cannot"]:
            return None, found, f"it cannot be installed from here. {o['cannot']}"
        return None, found, f"to install it: mcdonald setup --install-gpu (by hand: {update.said(o['command'])})"
    if ours:
        return None, f"{ours[0]['name']}, not used: {gpu.why()}", ""
    if cards:
        return None, (f"{', '.join(c['name'] for c in cards)}: not one mcdonald can compute on "
                      "(it uses NVIDIA cards, through CUDA)"), "nothing to do: every step runs on the CPU"
    return None, "none found", "nothing to do: every step runs on the CPU"


def install_gpu(as_json=False):
    """`mcdonald setup --install-gpu`: the add-on for graphics cards, installed (`addon.install`) and tried
    (`addon.use_now`), for an agent or a person at a terminal; the window's Preferences does the same with a button.
    What pip prints goes to stderr. Exit 0 when the card computes, or CuPy was here already; 3 when there is nothing
    to install it for, or it could not be installed, or the card does not answer."""
    from . import addon, gpu, update
    say = lambda *a: print(*a, file=sys.stderr, flush=True)

    def end(ok, **more):
        if as_json:
            print(json.dumps(dict(command="setup", mcdonald=__version__, install_gpu=dict(ok=ok, **more)), indent=1))
        return 0 if ok else EXIT_MISSING
    say(f"mcdonald {__version__}: the add-on for graphics cards\n")
    if gpu.installed():
        c, found = gpu.card(), _graphics_card()[1]
        say(f"  already installed (CuPy). graphics card: {found}")
        return end(True, installed=False, card=f"{c.name} ({c.library})" if c is not None else None, found=found)
    cards = gpu.found()
    o = addon.offer(cards)
    if o is None:
        why = (f"{', '.join(c['name'] for c in cards)}: not one mcdonald can compute on (it uses NVIDIA cards, through CUDA)"
               if cards else "no graphics card was found")
        say(f"  nothing to install it for: {why}. Every step runs on the CPU.")
        return end(False, installed=False, why=why)
    cuda = f"its driver runs CUDA {o['cuda'][0]}.{o['cuda'][1]}" if o["cuda"] else "its driver did not say which CUDA it runs"
    say(f"  {o['card']}: {cuda}")
    if o["cannot"]:
        say(f"  not installed. {o['cannot']}")
        return end(False, installed=False, card=o["card"], why=o["cannot"])
    say(f"  installing {' '.join(o['requires'])}: CuPy with CUDA {addon.CUDA[o['extra']]}'s libraries, about "
        f"{o['download_mb'] / 1000:.1f} GB to download and {o['disk_mb'] / 1000:.1f} GB on disk\n")
    r = addon.install(o["extra"], said=lambda line: say(f"    {line}"))
    if not r["ok"]:
        say(f"\nmcdonald: the add-on was not installed. {r['why']}\n  by hand: {update.said(r['command'])}")
        return end(False, installed=False, card=o["card"], why=r["why"], pip=r["pip"], command=r["command"])
    card, why, again = addon.use_now()
    took = f"{r['seconds'] / 60:.1f} min, {r['mb']:,.0f} MB downloaded"
    if again:                                         # pip chose a folder this process was not reading: the next one does
        say(f"\n  installed ({took}). `mcdonald setup` says, from its next run on, whether the card is in use")
        return end(True, installed=True, card=None, seconds=round(r["seconds"], 1), mb=round(r["mb"], 1))
    if card is None:
        say(f"\n  installed ({took}), but the card is not in use: {why}")
        return end(False, installed=True, card=None, why=why, seconds=round(r["seconds"], 1), mb=round(r["mb"], 1))
    say(f"\n  installed ({took}). graphics card: {card}: the steps that can use it do")
    return end(True, installed=True, card=card, seconds=round(r["seconds"], 1), mb=round(r["mb"], 1))


def _newest():
    """(ok, found, what to do) for this version against the newest, asked now (`update.now`): setup is where a
    person on the command line asks whether a newer mcdonald is out (Jacob, 2026-10-22)."""
    from . import update
    what, v = update.now()
    if what == "newest":
        return True, f"{__version__}, the newest", ""
    if what == "newer":
        return None, f"{__version__}; {v} is out", f"to update: {update.said(update.command())}"
    if what == "by hand":
        return None, f"{__version__}, a copy pip did not install (PyPI has {v})", "update it where it came from"
    return None, f"{__version__}; could not ask which is the newest", "check the internet connection"


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
        if storage.is_certificate_error(e):
            return False, "certificate not trusted", storage.certificate_fix()
        why = getattr(e, "reason", e)
        return False, f"could not reach DVIDS: {why}", "check the internet connection; videos given by their path still work"
    except OSError as e:
        return False, f"could not reach DVIDS: {e}", "check the internet connection; videos given by their path still work"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mcdonald setup", description=__doc__.split("\n\n")[0])
    ap.add_argument("--no-desktop", action="store_true", help="do not add mcdonald to the applications menu (Linux)")
    ap.add_argument("--desktop", action="store_true", help=argparse.SUPPRESS)     # what 0.2.1-0.2.5 asked for: now what it does anyway
    ap.add_argument("--offline", action="store_true", help="leave out the download check, and asking whether a newer mcdonald is out")
    ap.add_argument("--json", action="store_true", help="the checks as one JSON object on stdout")
    ap.add_argument("--install-gpu", action="store_true",
                    help="install the add-on for an NVIDIA graphics card (CuPy, 1 to 2 GB from PyPI) into this Python, and "
                         "nothing else of setup: the build for this computer's driver, with nothing already installed "
                         "replaced. What the window's Preferences does with its Install button")
    args = ap.parse_args(argv)
    if args.install_gpu:
        return install_gpu(args.json)

    got = checks(args.offline)
    desktop = None
    if _system() == "linux" and not args.no_desktop:  # macOS and Windows have no menu a package can write into
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            try:
                from .gui import desktop_entry
                desktop = f"added: {desktop_entry()}"
            except (OSError, RuntimeError) as e:
                desktop = f"not added: {e}"
        else:
            desktop = "not added: no desktop here (run mcdonald setup again from one to add it)"
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
    print("Ready.\n")
    print(NEXT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
