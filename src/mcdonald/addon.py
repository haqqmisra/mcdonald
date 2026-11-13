"""The add-on for graphics cards, put in place for the person: which one this computer takes, and pip run for it.

The slow steps run on an NVIDIA card through CuPy (`mcdonald.gpu`), which is not installed with mcdonald: it is the
extra `mcdonald[gpu]` (CuPy with CUDA 12's libraries) or `mcdonald[gpu-cuda13]` (CUDA 13's). A person at the window
has no terminal to type that in, so Preferences has a button for it, and the command line has
`mcdonald setup --install-gpu` for an agent (IDEAS.md G5, 2026-11-13). Both call `install`, and both read what there
is to install from `offer`. The rules, each with its reason:

- *pip never touches mcdonald.* It is given the add-on's own requirement ("cupy-cuda13x[ctk]>=14"), never
  "mcdonald[gpu]": a working copy (`pip install -e`) or a copy from GitHub stays what it is. The requirement is
  written here (`REQUIRES`) and not read from the installed package's record, because a working copy's record is as
  old as the day it was installed: the maintainer's own said 0.5.2 and had no `gpu` extra on the day this was
  written. test_reduction holds `REQUIRES` to pyproject.toml.
- *Nothing already installed is replaced*, which is why the window can stay open. `update` has to close the window
  first, because pip replaces the running mcdonald and Windows locks the files of a running program. The add-on only
  adds packages, and pip is held to that: it is given a constraints file that pins every package here at the version
  it has (`pinned`). If the add-on wants another version of one of them (NumPy 1, where CuPy needs 2), pip stops
  before it changes anything, and the person is told. Nothing else that shares this Python is disturbed either.
- *Which of the two* (`which`): CUDA 13's, where the driver runs CUDA 13 and every card here is one CUDA 13's
  libraries still run (compute capability 7.5 and up: the GTX 1600 and RTX 2000 series on); else CUDA 12's, which
  runs on today's cards too. The driver alone does not say: NVIDIA's 580 drivers report CUDA 13 on a GTX 1080, which
  CUDA 13's libraries dropped. A driver older than CUDA 12 takes neither, and that is said before anything is
  downloaded.
- *Wheels only* (`--only-binary`): a build from source needs a compiler and an hour, which a person at a window has
  not got. *Nothing kept* (`--no-cache-dir`): pip's own copy of the download would be another 1 to 2 GB in a hidden
  folder. *Never asks* (`--no-input`, no stdin): there is nobody at a terminal to answer.
- *Used at once* (`use_now`): CuPy is found without importing it (`gpu.installed`), so once Python's import caches
  are told to look again the same process has it, and `gpu.card()` opens the card. Where pip put it in a folder this
  process does not read (a user folder made by this very install), the person is told to open mcDonald again.
- *A failure is said in plain words* (`explain`): no network, no room, no build for this Python, a package that would
  have to be replaced; then what pip said, and the command to type by hand.

Tried for real on the development workstation (2026-11-13: Linux, Python 3.14, an RTX 5070 Ti on a driver that runs
CUDA 13.5, a fresh venv with mcdonald installed from a copy of the source, not editable). `mcdonald setup
--install-gpu` chose CUDA 13's add-on, downloaded 1,353 MB in eleven files and had the card compute in the same
process after 22 s; the venv grew by 1.9 GB. CUDA 12's, asked for by name, was 1,823 MB, 34 s and 2.8 GB, and the
card computed with it too. That was on a fast line (60 MB a second): at 50 megabits a second the downloads are about
4 and 5 minutes. `DOWNLOAD_MB` and `DISK_MB` are those numbers, and the window's words are made from them.
"""
import importlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import threading
import time
from pathlib import Path

from . import gpu, update

# What each extra installs: pyproject.toml's [project.optional-dependencies], word for word (test_reduction)
REQUIRES = {"gpu": ["cupy-cuda12x[ctk]>=14"], "gpu-cuda13": ["cupy-cuda13x[ctk]>=14"]}
CUDA = {"gpu": 12, "gpu-cuda13": 13}                # the CUDA whose libraries each brings
OLDEST = (12, 0)                # a driver must run at least this CUDA for either
STILL_RUN = (7, 5)              # the compute capability from which CUDA 13's libraries run a card (Turing)
DOWNLOAD_MB = {"gpu": 1820, "gpu-cuda13": 1350}     # what pip downloads: PyPI's wheels for Linux, measured 2026-11-13 (those
DISK_MB = {"gpu": 2800, "gpu-cuda13": 1900}         # for Windows add up to 1,727 and 1,303 MB), and what they take unpacked
PIP = None                      # a test's stand-in for [python, "-m", "pip"]
TAIL = 12                       # lines of what pip said that a failure keeps


def which(seen):
    """(the extra this computer takes, "") or (None, why neither, in sentences the window can show): from what the
    driver says (`gpu.cuda()`). With no answer from the driver it is CUDA 12's, which every card the add-on runs on
    can use."""
    driver, cards = (seen or {}).get("driver"), (seen or {}).get("cards") or []
    if driver is not None and tuple(driver) < OLDEST:
        return None, (f"The card's driver is too old for it. The driver runs version {driver[0]}.{driver[1]} of CUDA, "
                      f"NVIDIA's software for computing on a card, and the add-on needs version {OLDEST[0]} or newer. "
                      "Install a newer driver from NVIDIA, then try again.")
    if driver is not None and tuple(driver) >= (13, 0) and cards and min(map(tuple, cards)) >= STILL_RUN:
        return "gpu-cuda13", ""
    return "gpu", ""


def command(extra, python=None):
    """The pip command that installs the add-on, for a person to type: with the window closed it may replace what it
    needs to."""
    return [python or sys.executable, "-m", "pip", "install", *REQUIRES[extra]]


def offer(cards=None, seen=None):
    """What there is to install on this computer, or None where there is nothing to offer: no NVIDIA card with CUDA
    (`gpu.usable`), or CuPy is here already. {"card": its name, "extra", "requires", "cuda": the driver's (13, 5) or
    None, "download_mb", "disk_mb", "command": to type by hand, "cannot": "" or why it cannot be installed from here,
    in sentences the window can show}.
    `cards` is `gpu.found()`'s list and `seen` is `gpu.cuda()`'s answer, where the caller has them already."""
    ours = gpu.usable(gpu.found() if cards is None else cards)
    if not ours or gpu.installed():
        return None
    seen = gpu.cuda() if seen is None else seen
    extra, cannot = which(seen)
    extra, numpy = extra or "gpu", _numpy()
    if not cannot and PIP is None and importlib.util.find_spec("pip") is None:
        cannot = "This Python has no pip, the program that installs packages."
    elif not cannot and numpy and numpy[0] < 2:
        cannot = (f"The add-on needs NumPy 2, and this Python has NumPy {'.'.join(map(str, numpy))}, which cannot be "
                  f"replaced while mcDonald runs. Close mcDonald and type in a terminal: {update.said(command(extra))}")
    return dict(card=ours[0]["name"], extra=extra, requires=list(REQUIRES[extra]), cuda=(seen or {}).get("driver"),
                download_mb=DOWNLOAD_MB[extra], disk_mb=DISK_MB[extra], command=command(extra), cannot=cannot)


def _numpy():
    try:
        import numpy
        return tuple(int(n) for n in re.findall(r"\d+", numpy.__version__)[:3])
    except Exception:
        return None


def pinned():
    """Every package installed here at the version it has, as the lines of a pip constraints file: with it pip can
    add packages and replace none. A package found twice counts as the first, which is the one Python imports. One
    whose name or version pip would not read in such a file is left out: a line pip refuses stops the whole install."""
    from importlib.metadata import distributions
    try:
        from packaging.version import Version         # pip's own reading of a version; here with matplotlib
    except ImportError:
        Version = None
    seen, lines = set(), []
    for d in distributions():
        try:
            name, version = str(d.metadata["Name"] or ""), str(d.version or "")
            if Version is not None:
                Version(version)
        except Exception:
            continue
        key = re.sub(r"[-_.]+", "-", name).lower()
        if key and key not in seen and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) \
                and re.fullmatch(r"[0-9][0-9A-Za-z.!+_-]*", version):
            seen.add(key)
            lines.append(f"{name}=={version}")
    return sorted(lines, key=str.lower)


def room(extra, where=None, temp=None):
    """"" where the disk has room for the add-on, else a sentence saying how much it needs and how much is free: the
    unpacked packages where this Python keeps its packages (`where`), and the download in the temporary folder
    (`temp`) until it is unpacked. A disk that fills half-way leaves half an add-on."""
    where = Path(where or sysconfig.get_paths()["purelib"])
    temp = Path(temp or tempfile.gettempdir())
    while not where.exists() and where != where.parent:
        where = where.parent
    try:
        same = os.stat(where).st_dev == os.stat(temp).st_dev
        need = [(where, DISK_MB[extra] + (DOWNLOAD_MB[extra] if same else 0))] + ([] if same else [(temp, DOWNLOAD_MB[extra])])
        for folder, mb in need:
            free = shutil.disk_usage(folder).free / 1e6
            if free < mb:
                return (f"The add-on needs about {mb / 1000:.1f} GB of free disk space in {folder}, and "
                        f"{free / 1000:.1f} GB are free there.")
    except OSError:
        pass
    return ""


def install(extra, progress=None, said=None, stop=None):
    """Install the add-on `extra` ("gpu" or "gpu-cuda13") into this Python with pip, in a process of its own, and wait
    for it. `progress(state)` is called as it goes, from this thread: state is {"phase": "looking" (pip asks what is
    needed), "downloading" or "installing" (unpacking: from here on it is not stopped), "mb": downloaded so far, "of":
    the add-on's size, never under `mb`, "file": the part on its way}. `said(line)` gets each line pip prints but its
    counts. `stop` is a threading.Event: once set, pip is ended if it is still downloading, and nothing is installed.

    Returns {"ok", "stopped", "code": pip's exit code or None, "why": "" or a plain sentence saying what went wrong,
    "pip": the last lines pip said (its errors, where it named them), "command": to type by hand, "seconds", "mb":
    downloaded}. It does not say whether the card answers: `use_now` does."""
    t0 = time.monotonic()
    result = dict(ok=False, stopped=False, code=None, why="", pip=[], command=command(extra), seconds=0.0, mb=0.0)
    short = room(extra)
    if short:
        return dict(result, why=short)
    state = dict(phase="looking", mb=0.0, of=float(DOWNLOAD_MB[extra]), file="")
    before, lines = 0, []                             # bytes of the files already here; what pip said
    folder = Path(tempfile.mkdtemp(prefix="mcdonald-addon-"))
    try:
        (folder / "installed.txt").write_text("\n".join(pinned()) + "\n", encoding="utf-8")
        cmd = [*(PIP or [sys.executable, "-m", "pip"]), "install", "--no-input", "--disable-pip-version-check",
               "--only-binary=:all:", "--no-cache-dir", "--progress-bar", "raw" if _counts() else "off",
               "--constraint", str(folder / "installed.txt"), *REQUIRES[extra]]
        if said:
            said(update.said(cmd))
        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    encoding="utf-8", errors="replace", creationflags=gpu.NO_WINDOW,
                                    env=dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8"))
        except OSError as e:
            return dict(result, why="pip could not be started.", pip=[str(e)], seconds=time.monotonic() - t0)

        def watch():                                  # Stop, while it downloads: once pip unpacks, it is left to finish
            while proc.poll() is None:
                time.sleep(0.2)
                if stop is not None and stop.is_set() and state["phase"] != "installing":
                    result["stopped"] = True
                    proc.terminate()
                    return
        threading.Thread(target=watch, daemon=True, name="mcdonald-addon-stop").start()

        here = 0                                      # bytes of the file on its way
        for line in proc.stdout:
            line = line.rstrip()
            m = re.match(r"Progress (\d+) of (\d+)", line)
            if m:
                here = int(m.group(1))
            else:
                m = re.match(r"\s*Downloading (\S+)", line)
                if m or line.startswith("Installing collected packages"):
                    before, here = before + here, 0   # the file before this one is all here
                if m and not m.group(1).endswith(".metadata"):      # a part itself, not the note of what it needs
                    state.update(phase="downloading", file=m.group(1))
                elif not m and line.startswith("Installing collected packages"):
                    state.update(phase="installing", file="")
                if line.strip():
                    lines.append(line)
                    if said:
                        said(line)
            state["mb"] = (before + here) / 1e6
            state["of"] = max(state["of"], state["mb"])
            if progress:
                progress(dict(state))
        code = proc.wait()
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    errors = [ln for ln in lines if ln.startswith("ERROR")]
    result.update(code=code, pip=(errors or lines)[-TAIL:], seconds=time.monotonic() - t0, mb=state["mb"],
                  ok=code == 0 and not result["stopped"])
    if result["stopped"]:
        result["why"] = "It was stopped before anything was installed."
    elif code != 0:
        result["why"] = explain(lines, extra)
    return result


def _counts():
    """Whether this pip prints its downloads as counts a program can read (`--progress-bar raw`, pip 24.1 on)."""
    if PIP is not None:
        return True
    try:
        from importlib.metadata import version
        return update.key(version("pip"))[:2] >= (24, 1)
    except Exception:
        return False


# What pip prints when it cannot reach the index at all: no network, no name service, a proxy, a certificate
_NO_NETWORK = re.compile(r"NewConnectionError|NameResolutionError|name resolution|Name or service not known|getaddrinfo failed|"
                         r"Network is unreachable|Connection refused|ConnectTimeoutError|ReadTimeoutError|ProxyError|"
                         r"SSLError|CERTIFICATE_VERIFY_FAILED|connection broken|Connection reset|timed out", re.I)


def explain(lines, extra="gpu"):
    """One plain sentence for why pip failed, from what it printed (`lines`)."""
    text = "\n".join(lines)
    if re.search(r"No space left on device|Errno 28\b|not enough (free )?space", text, re.I):
        return f"The disk filled up. The add-on needs about {(DOWNLOAD_MB[extra] + DISK_MB[extra]) / 1000:.0f} GB of free space."
    if "externally-managed-environment" in text:
        return "This Python is looked after by the operating system, which does not let pip add packages to it."
    if re.search(r"Permission denied|Errno 13\b|Access is denied", text, re.I):
        return "pip is not allowed to write in the folder where this Python keeps its packages."
    if "(constraint)" in text or "ResolutionImpossible" in text or "conflicting dependencies" in text:
        return ("The add-on needs another version of a package that is installed here, and mcDonald replaces nothing "
                "that is installed.")
    if _NO_NETWORK.search(text):
        return ("pip could not reach the Python Package Index (pypi.org), where the add-on is kept. "
                "Check the internet connection, then try again.")
    if "No matching distribution found" in text or "Could not find a version" in text:
        return (f"The add-on has no build for this Python ({sys.version_info[0]}.{sys.version_info[1]}) on this kind of "
                "computer yet.")
    return "pip could not install the add-on."


def use_now():
    """After `install`: (the card in use, as `gpu.computed_on` names one, or None; "" or why none is in use; whether
    mcDonald has to be opened again first). Python is told to look for new packages, the card is asked for again
    (`gpu.forget`), and one sum is computed on it (`gpu.card`), which takes some seconds the first time. Not for the
    window's own thread."""
    importlib.invalidate_caches()
    if not gpu.installed():
        return None, "pip put the add-on where this mcDonald does not read until it is opened again", True
    gpu.forget()
    c = gpu.card()
    if c is not None:
        return f"{c.name} ({c.library})", "", False
    return None, gpu.why(), False
