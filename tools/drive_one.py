"""One driver of tests/test_gui.py, alone, with a window of its own: for working on the window.

    python3 tools/drive_one.py drive_several                 # a driver that takes a temporary directory (td)
    python3 tools/drive_one.py drive_finding                 # one that takes new_rig
    python3 tools/drive_one.py drive_the_window --keep       # one that takes rig; keep what it wrote

The whole of test_gui.py takes minutes and two toolkits; while one panel is being built, one driver
in a few seconds is what is wanted. The driver is looked up by name in tests/test_gui.py and given
what its parameters ask for -- `rig` (the Qt rig on the synthetic clip), `new_rig` (a function that
makes one for a MarkSet), `td` (a temporary directory) -- as `drive()` would. QSettings go to a
configuration directory of their own, so the person's are not touched.

With no screen, under a virtual one, and through Slurm on merlin (everything that runs the package
does, since 2026-10-06):

    TMPDIR=/scratch/tmp/mcq1 QT_QPA_PLATFORM=xcb srun -n 1 -c 4 --mem=6G --time=15:00 \\
        xvfb-run -a -s "-screen 0 1600x1200x24" python3 tools/drive_one.py drive_several

Keep TMPDIR short (the pools' sockets), and note the main guard below: Python 3.14's pools are
forkserver processes, and a script without it runs its body a second time in the server.
"""
import inspect
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    name, keep = args[0], "--keep" in sys.argv
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "tests"))
    cfg = tempfile.mkdtemp(prefix="mcdonald-drive-one-cfg-")
    os.environ["XDG_CONFIG_HOME"] = cfg
    import test_gui as t
    from mcdonald import mark, mark_qt
    fn = getattr(t, name, None)
    if fn is None or not name.startswith("drive_"):
        print(f"no driver named {name!r} in tests/test_gui.py; they are: " + ", ".join(sorted(n for n in dir(t) if n.startswith("drive_"))))
        return 2
    mark_qt.application()
    td = tempfile.mkdtemp(prefix="mcdonald-drive-one-")
    clip = t.SyntheticClip()
    rig = None

    def new_rig(ms):
        return t.QtRig(clip, ms, f"{td}/{ms.tag}")
    wanted = []
    for p in inspect.signature(fn).parameters:
        if p == "rig":
            rig = rig or new_rig(mark.MarkSet("synthetic", "/nowhere/synthetic.mp4", clip.fps))
            wanted.append(rig)
        elif p == "new_rig":
            wanted.append(new_rig)
        elif p == "td":
            wanted.append(td)
        else:
            print(f"{name} takes {p!r}, which this script does not know how to give it")
            return 2
    t0 = time.time()
    try:
        fn(*wanted)
    finally:
        print(f"{name}: {time.time() - t0:.0f} s; {'FAIL: ' + ', '.join(t.FAIL) if t.FAIL else 'all checks passed'}")
        if rig is not None and rig.is_open():
            rig.close()
        if keep:
            print(f"kept {td}")
        else:
            shutil.rmtree(td, ignore_errors=True)
        shutil.rmtree(cfg, ignore_errors=True)
    return 1 if t.FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
