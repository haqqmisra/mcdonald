"""Is there a newer mcdonald, and putting it in place.

Someone who installed with the README's command (pip from GitHub) gets nothing new
until they run pip again, and has no way to know when to. So at a start, mcdonald
asks GitHub what version main is -- one small file, no account, no API -- at most
once a day, and only for an install that came from there: a working copy
(`pip install -e`) or a CI build from a checkout is left alone. main moves only
when a release is ready, and the version goes up with each one, so a higher
number on main is a release this computer does not have.

The window asks, and on a yes closes and hands the update to a small helper
process: on Windows the running mcdonald-gui.exe is locked, and pip cannot
replace it while the window is open. The helper waits for the window to close,
runs pip, and opens the window again. The command line never stops to ask
(an agent could not answer): it says so in one line on stderr, once a day.

MCDONALD_NO_UPDATE_CHECK=1 turns all of it off, as "Don't ask again" does.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from . import __version__

REPO = "https://github.com/haqqmisra/mcdonald"
LATEST = "https://raw.githubusercontent.com/haqqmisra/mcdonald/main/src/mcdonald/__init__.py"
SOURCE = f"mcdonald[gui] @ git+{REPO}"
OFF = "MCDONALD_NO_UPDATE_CHECK"
DAY = 24 * 3600
STATE = None                                          # a test's own state file; else state_file()


def key(version):
    return tuple(int(n) for n in re.findall(r"\d+", version))


def command(python=None):
    """The pip command that updates this install, for a person to type or the helper to run."""
    return [python or sys.executable, "-m", "pip", "install", "--upgrade", SOURCE]


def said(cmd):
    return " ".join(f'"{a}"' if " " in a else a for a in cmd)


def installed_from_github():
    """Was this copy installed by pip from the GitHub repository (not a working copy,
    not a checkout)? pip writes where it came from in direct_url.json (PEP 610)."""
    try:
        from importlib.metadata import distribution
        came = json.loads(distribution("mcdonald").read_text("direct_url.json") or "{}")
    except Exception:
        return False
    return "vcs_info" in came and "haqqmisra/mcdonald" in came.get("url", "")


def state_file():
    if STATE:
        return Path(STATE)
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "mcdonald" / "update.json"


def state():
    try:
        return json.loads(state_file().read_text())
    except Exception:
        return {}


def remember(**kw):
    try:
        s = state()
        s.update(kw)
        state_file().parent.mkdir(parents=True, exist_ok=True)
        state_file().write_text(json.dumps(s))
    except OSError:
        pass


def recently(what, now=None):
    return (time.time() if now is None else now) - state().get(what, 0) < DAY


def latest(timeout=3):
    """The version on main, or None if it could not be read (no network, slow, moved)."""
    try:
        with urllib.request.urlopen(LATEST, timeout=timeout) as r:
            m = re.search(r'^__version__ = "([^"]+)"', r.read().decode("utf-8", "replace"), re.M)
        return m.group(1) if m else None
    except Exception:
        return None


def newer(timeout=3, now=None):
    """A version newer than this one, or None. GitHub is asked at most once a day; in
    between, what it said last is used."""
    if os.environ.get(OFF) or not installed_from_github() or state().get("never"):
        return None
    if recently("checked", now):
        v = state().get("latest")
    else:
        v = latest(timeout)
        remember(checked=time.time() if now is None else now, **({"latest": v} if v else {}))
    return v if v and key(v) > key(__version__) else None


class Check(threading.Thread):
    """newer(), started now and read later, so that a start does not wait on the network."""

    def __init__(self):
        super().__init__(daemon=True)
        self.found = None
        self.start()

    def run(self):
        self.found = newer()

    def result(self, wait=0):
        self.join(wait)
        return self.found


def tell_cli(check):
    """The command line's one line, on stderr and once a day: stdout may be JSON for an agent."""
    v = check.result(0.2)
    if v and not recently("told"):
        remember(told=time.time())
        print(f"mcdonald: version {v} is out (this is {__version__}). To update:\n    {said(command())}",
              file=sys.stderr)


# The helper runs on its own, with only the standard library, after the window has
# closed: nothing of mcdonald is imported, because pip is about to replace it.
HELPER = r'''
import json, os, subprocess, sys, time, threading
pid, log, again = int(sys.argv[1]), sys.argv[2], json.loads(sys.argv[3])
cmd = sys.argv[4:]
hidden = {"creationflags": 0x08000000} if sys.platform == "win32" else {}      # CREATE_NO_WINDOW

def wait_for(pid, most=600):
    if sys.platform == "win32":
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x00100000, False, pid)                               # SYNCHRONIZE
        if h:
            k.WaitForSingleObject(h, most * 1000)
            k.CloseHandle(h)
        time.sleep(2)                                 # the .exe launcher that started it ends just after
        return
    end = time.time() + most
    while time.time() < end:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.3)

result = {}
def update():
    wait_for(pid)
    with open(log, "w") as f:
        f.write(" ".join(cmd) + "\n\n")
        f.flush()
        try:
            result["code"] = subprocess.call(cmd, stdout=f, stderr=subprocess.STDOUT, **hidden)
        except OSError as ex:
            f.write(str(ex) + "\n")
            result["code"] = -1

t = None
try:                                                  # a small window saying what is happening, if there is a Tk
    import tkinter
    root = tkinter.Tk()
    root.title("mcdonald")
    tkinter.Label(root, text="Updating mcdonald. It will open again when it is done.\n"
                             "This can take a minute or two.", padx=24, pady=20).pack()
    t = threading.Thread(target=update, daemon=True)
    t.start()
    def poll():
        root.destroy() if not t.is_alive() else root.after(300, poll)
    root.after(300, poll)
    root.mainloop()
    t.join()
except Exception:
    if t is None:
        update()
    else:
        t.join()

if result.get("code") == 0:
    subprocess.Popen(again, start_new_session=sys.platform != "win32", **hidden)
    import shutil
    shutil.rmtree(os.path.dirname(log), ignore_errors=True)       # this script too: it has been read
else:
    try:
        tail = open(log).read().strip().splitlines()[-12:]
    except OSError:
        tail = []
    text = ("The update did not work. What pip said is in\n" + log + "\n\n" + "\n".join(tail) +
            "\n\nTo try it by hand, in a terminal:\n" + " ".join(a if " " not in a else '"' + a + '"' for a in cmd))
    sys.stderr.write(text + "\n")
    try:
        import tkinter
        from tkinter import messagebox
        r = tkinter.Tk()
        r.withdraw()
        messagebox.showerror("mcdonald", text)
        r.destroy()
    except Exception:
        pass
'''


def start(cmd=None, again=None, pid=None, python=None):
    """Hand the update to the helper, which waits for process `pid` (this one) to end,
    runs `cmd` (pip), and on success starts `again` (the window). Returns the log's path."""
    python = python or sys.executable
    d = Path(tempfile.mkdtemp(prefix="mcdonald-update-"))
    (d / "helper.py").write_text(HELPER)
    log = d / "pip.txt"
    again = again or [python, "-m", "mcdonald.gui"]
    args = [python, str(d / "helper.py"), str(pid or os.getpid()), str(log), json.dumps(again)] + (cmd or command(python))
    if sys.platform == "win32":
        subprocess.Popen(args, creationflags=0x00000008 | 0x00000200 | 0x08000000,   # detached, own group, no window
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(args, start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return log
