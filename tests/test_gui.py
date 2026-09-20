"""Does the marking window do what its keys say? Every handler, under every
interactive matplotlib backend this machine can open.

    python3 tests/test_gui.py                 # every backend that imports
    python3 tests/test_gui.py QtAgg TkAgg     # just these
    python3 tests/test_gui.py --on-screen     # on the desktop rather than Xvfb

`MarkSet` is covered headless in test_reduction.py. This is the other half:
the `Marker` window. Synthetic MouseEvent and KeyEvent objects go in through
`fig.canvas.callbacks`, the registry real events arrive through, so every
handler connected to the canvas runs — matplotlib's own included, which is how
this suite found that 's' also opened matplotlib's save-figure dialog and 'l'
put the image on a log axis. Calling `Marker.on_key` directly would have
missed both.

No video. The clip is synthetic, a compact source on a known path, so two
clicks on it must give back the velocity it was built with.

Each backend is driven in its own subprocess under a timeout: a GUI toolkit
that cannot reach a display may hang rather than raise (GTK4Agg did, here),
and two toolkits do not share a process. Where Xvfb exists the windows are
hosted off screen, so nothing flashes on the desktop, a modal dialog cannot
wait on a person, and a host with no display at all runs the same checks. A
backend that cannot open a window is skipped, with the reason. A hang once the
window is up is a failure: from here, that is what a modal dialog looks like.
"""
import contextlib
import io
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import forensics as vf  # noqa: E402
from mcdonald import mark  # noqa: E402

BACKENDS = ["QtAgg", "GTK3Agg", "GTK4Agg", "TkAgg", "WxAgg", "MacOSX"]
UP = "window up"              # the child says this once a figure has opened
CANNOT_OPEN = 77              # and exits with this when one cannot
FAIL, SKIP = [], []
ON_SCREEN = False
WANTED = []


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}", flush=True)
    if not cond:
        FAIL.append(label)
    return cond


# ---------------------------------------------------------------- the clip
class SyntheticClip:
    """What Marker asks of a Clip, with a compact source on a known path.

    Frame numbers are absolute and do not start at 1, as in a real window of
    a real clip, and fps is the NTSC rational rather than 30."""
    W, H = 640, 360
    n0, n1 = 401, 440
    fps = 30000 / 1001
    P0, V = (560.0, 90.0), (-7.25, 3.5)          # position at n0, px/frame

    def __init__(self):
        rng = np.random.default_rng(113)
        self._yx = np.mgrid[:self.H, :self.W]
        yy, xx = self._yx
        self._sky = 60 + 25 * np.sin(xx / 47.0) * np.cos(yy / 31.0) + rng.normal(0, 3, (self.H, self.W))
        self._frames = {}

    def truth(self, n):
        k = n - self.n0
        return self.P0[0] + self.V[0] * k, self.P0[1] + self.V[1] * k

    def rgb(self, n):
        if n not in self._frames:
            yy, xx = self._yx
            x, y = self.truth(n)
            g = self._sky + 170 * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 2.5 ** 2))
            self._frames[n] = np.repeat(np.clip(g, 0, 255)[..., None], 3, axis=2).astype(np.float32)
        return self._frames[n]


# ---------------------------------------------------------------- events
def key(m, k):
    """One key press, with the pointer over the middle of the image -- where it
    is when someone is marking, and where matplotlib's own bindings would act."""
    from matplotlib.backend_bases import KeyEvent
    c = m.fig.canvas
    x, y = m.ax.bbox.x0 + m.ax.bbox.width / 2, m.ax.bbox.y0 + m.ax.bbox.height / 2
    c.callbacks.process("key_press_event", KeyEvent("key_press_event", c, k, x, y))


def mouse(m, name, xy=None, px=None, **kw):
    """One mouse event at data coordinates xy, or at display pixel px."""
    from matplotlib.backend_bases import MouseEvent
    c = m.fig.canvas
    c.draw()                  # the transform is final only once the aspect is applied
    if px is None:
        px = m.ax.transData.transform(xy)
    c.callbacks.process(name, MouseEvent(name, c, px[0], px[1], **kw))
    return np.asarray(px, float)


def click(m, xy=None, px=None, button=1):
    at = mouse(m, "button_press_event", xy, px, button=button)
    mouse(m, "button_release_event", px=at, button=button)
    return at


def shows(m, n):
    return np.array_equal(np.asarray(m.im.get_array()), m.clip.rgb(n).astype(np.uint8))


# ---------------------------------------------------------------- the drive
def drive_the_window_opens_and_owns_its_keys(m):
    print("\nthe window")
    check(m.n == m.clip.n0 and shows(m, m.clip.n0), "opens on the first frame of the window",
          f"n={m.n}")
    title = m.ax.get_title(loc="left")
    check(f"frame {m.clip.n0} / {m.clip.n1}" in title and "marking: object" in title,
          "and the title says which frame and which class", repr(title[:40]))
    # matplotlib binds keys of its own to every figure. 's' is its save-figure
    # dialog, 'l' and 'k' put the image on log axes, 'g' draws a grid, and
    # backspace walks its view history -- all keys this window uses or sits beside
    theirs = m.fig.canvas.manager.key_press_handler_id
    if not check(theirs not in m.fig.canvas.callbacks.callbacks.get("key_press_event", {}),
                 "matplotlib's default key bindings are disconnected"):
        # carry on without them, or the 's' further down blocks on a dialog until the timeout
        m.fig.canvas.mpl_disconnect(theirs)
        return
    for k in ("l", "k", "g"):
        key(m, k)
    check(m.ax.get_yscale() == "linear" and m.ax.get_xscale() == "linear",
          "so a stray 'l' or 'k' cannot put the image on a log axis",
          f"x {m.ax.get_xscale()}, y {m.ax.get_yscale()}")


def drive_stepping(m):
    print("\nframes")
    n0, n1 = m.clip.n0, m.clip.n1
    key(m, ",")
    check(m.n == n0, "cannot step back past the start of the window")
    key(m, ".")
    check(m.n == n0 + 1 and shows(m, n0 + 1), "'.' is the next frame, and its pixels are on screen")
    key(m, ">")
    check(m.n == n0 + 11 and shows(m, n0 + 11), "'>' is ten on")
    key(m, "<")
    key(m, ",")
    check(m.n == n0 and shows(m, n0), "'<' and ',' come back")
    key(m, "right")
    key(m, "right")
    key(m, "left")
    check(m.n == n0 + 1, "the arrow keys step too")
    for _ in range(6):
        key(m, ">")
    check(m.n == n1 and shows(m, n1), "and cannot run off the end", f"n={m.n}")
    check(f"frame {n1} / {n1}" in m.ax.get_title(loc="left"), "the title follows")


def drive_two_clicks(m):
    """The point of the tool: two clicks on the object give its velocity."""
    print("\ntwo clicks")
    c, ms = m.clip, m.ms
    a, b = c.n0 + 7, c.n0 + 10
    m.goto(a)
    click(m, c.truth(a))
    got = ms.marks.get("object", {}).get(a)
    check(got is not None and np.allclose(got, c.truth(a), atol=1e-6),
          "a click lands where it was aimed, through the axes transform",
          f"{got} for {c.truth(a)}")
    check(len(m.overlay) == 1 and np.allclose(m.overlay[0].get_xydata()[0], c.truth(a), atol=1e-6),
          "and is drawn back at that position")
    m.goto(b)
    check(len(m.overlay) == 0, "a mark shows only on its own frame")
    click(m, c.truth(b))
    v = ms.velocity()
    check(v is not None and np.allclose(v, c.V, atol=1e-6),
          "two clicks recover the velocity the source was built with",
          f"({v[0]:+.3f}, {v[1]:+.3f}) for ({c.V[0]:+.3f}, {c.V[1]:+.3f})" if v else "None")
    check(ms.seed() == (a, *ms.marks["object"][a]), "and the seed is the first of them")
    check("2 marks" in m.ax.get_title(loc="left") and "px/frame" in m.ax.get_title(loc="left"),
          "the title reports both")

    before = ms.count()
    click(m, px=(1, 1))
    check(ms.count() == before, "a click outside the image places nothing")
    click(m, c.truth(b), button=3)
    check(ms.count() == before, "nor does a right click")
    x, y = c.truth(b)
    click(m, (x + 2.0, y - 1.0))
    check(ms.count() == before and np.allclose(ms.marks["object"][b], (x + 2.0, y - 1.0), atol=1e-6),
          "a second click on a frame moves the mark rather than adding one")
    click(m, c.truth(b))

    tb = m.fig.canvas.toolbar
    if tb is not None:
        # with the toolbar's zoom or pan armed, a click belongs to the toolbar. If it
        # also placed a mark, zooming in to look would silently move the object
        tb.zoom()
        m.goto(b + 1)
        click(m, c.truth(b + 1))
        tb.zoom()
        check(ms.count() == before and (b + 1) not in ms.marks["object"],
              "a click made while the toolbar's zoom tool is armed is not a mark")
        m.goto(b)


def drive_classes(m):
    print("\nclasses")
    c, ms = m.clip, m.ms
    v, n = ms.velocity(), ms.count()
    key(m, "3")
    check(mark.CLASSES[m.cls] == "boresight" and "marking: boresight" in m.ax.get_title(loc="left"),
          "'3' marks the boresight, and the title says so")
    click(m, (c.W / 2, c.H / 2))
    check(ms.marks.get("boresight", {}).get(m.n) is not None and ms.count() == n + 1,
          "the click goes to that class")
    check(ms.velocity() == v, "and leaves the object's velocity alone")
    check(len(m.overlay) == 2, "both classes are drawn on the frame")
    for k in ("0", "7", "9"):
        key(m, k)
    check(mark.CLASSES[m.cls] == "boresight", "digits with no class behind them are ignored")
    key(m, "backspace")
    check("boresight" not in ms.to_dict()["classes"] and ms.velocity() == v,
          "backspace deletes this class's mark on this frame, and only that")
    key(m, "1")
    check(mark.CLASSES[m.cls] == "object", "'1' is the object again")


def drive_zoom_and_pan(m):
    print("\nzoom and pan")
    ax, c = m.ax, m.clip
    m.fig.canvas.draw()
    home = (ax.get_xlim(), ax.get_ylim())
    at = np.array([300.0, 200.0])

    px = mouse(m, "scroll_event", at, step=1)
    span = ax.get_xlim()[1] - ax.get_xlim()[0]
    check(np.isclose(span, 0.8 * (home[0][1] - home[0][0])), "scrolling up zooms in", f"span x{span / (home[0][1] - home[0][0]):.2f}")
    m.fig.canvas.draw()
    check(np.allclose(ax.transData.transform(at), px, atol=1e-6),
          "about the cursor: the pixel under it stays under it")
    n, want = m.n, (c.truth(m.n)[0] + 1.5, c.truth(m.n)[1] + 1.5)
    click(m, want)
    check(np.allclose(m.ms.marks["object"][n], want, atol=1e-6),
          "a click in a zoomed view still lands where it was aimed")
    click(m, c.truth(n))

    # a drag in several motion events, as a real one arrives. The image has to
    # follow the cursor through all of them, not just the first
    m.fig.canvas.draw()
    before = m.ms.count()
    p0 = mouse(m, "button_press_event", at, button=2)
    for step in ((15, 10), (40, 25), (64, -32)):
        mouse(m, "motion_notify_event", px=p0 + step)
    m.fig.canvas.draw()
    moved = ax.transData.transform(at) - p0
    check(np.allclose(moved, (64, -32), atol=1e-6), "a middle-button drag carries the image with the cursor",
          f"moved ({moved[0]:+.1f}, {moved[1]:+.1f}) px for a drag of (+64.0, -32.0)")
    mouse(m, "button_release_event", px=p0 + (64, -32), button=2)
    lims = (ax.get_xlim(), ax.get_ylim())
    mouse(m, "motion_notify_event", px=p0)
    check((ax.get_xlim(), ax.get_ylim()) == lims, "and lets go on release")
    check(m.ms.count() == before, "a drag places no mark")

    mouse(m, "scroll_event", at, step=-1)
    span = ax.get_xlim()[1] - ax.get_xlim()[0]
    check(np.isclose(span, home[0][1] - home[0][0]), "scrolling down zooms back out")
    key(m, "r")
    check(np.allclose((ax.get_xlim(), ax.get_ylim()), home), "'r' restores the view the window opened with",
          f"x {ax.get_xlim()}, y {ax.get_ylim()}")


def drive_saving(m, td):
    print("\nsaving")
    import matplotlib.pyplot as plt
    from PIL import Image
    c, ms = m.clip, m.ms
    key(m, "3")
    click(m, (c.W / 2, c.H / 2))
    key(m, "1")
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        key(m, "s")
    j, t, p = (Path(f"{m.out}_marks.{e}") for e in ("json", "csv", "png"))
    check(j.exists() and t.exists() and p.exists(), "'s' writes the marks, the track CSV and the contact strip")
    again = mark.MarkSet(ms.tag, ms.video, ms.fps, j)
    check(again.marks == ms.marks, "the JSON reads back as the same marks", f"{again.count()} marks")
    check(vf.read_track(t) == {n: (round(x, 2), round(y, 2)) for n, (x, y) in ms.track().items()},
          "the CSV reads back as the object track through the package's own reader")
    cell = 90 * 3
    check(Image.open(p).size == (ms.count() * cell, cell + 18),
          "the contact strip has a magnified cell for every mark", f"{Image.open(p).size}")
    check("link_track(" in said.getvalue() and f"seed={ms.seed()}" in said.getvalue(),
          "and the terminal says what to feed the linker")

    # --load: a saved file continues in a new window
    m2 = mark.Marker(c, again, m.out)
    m2.goto(ms.frames()[0])
    check(len(m2.overlay) == 1 and np.allclose(m2.overlay[0].get_xydata()[0], ms.marks["object"][ms.frames()[0]]),
          "a saved file reopens with its marks drawn")
    plt.close(m2.fig)

    j.unlink()
    num = m.fig.number
    with contextlib.redirect_stdout(io.StringIO()):
        key(m, "q")
    check(j.exists(), "'q' saves")
    check(not plt.fignum_exists(num), "and closes the window")


def drive(backend):
    """The child: open a window under one backend and press everything."""
    import matplotlib
    try:
        matplotlib.use(backend, force=True)
        import matplotlib.pyplot as plt
        plt.close(plt.figure())
    except Exception as ex:                       # ImportError, or whatever the toolkit raises
        print(f"{type(ex).__name__}: {(str(ex).splitlines() or [''])[0]}")
        return CANNOT_OPEN
    print(UP, flush=True)
    with tempfile.TemporaryDirectory() as td:
        clip = SyntheticClip()
        m = mark.Marker(clip, mark.MarkSet("synthetic", "/nowhere/synthetic.mp4", clip.fps), f"{td}/synthetic")
        print(f"\n== {backend}: {type(m.fig.canvas).__module__}.{type(m.fig.canvas).__name__}, "
              f"matplotlib {matplotlib.__version__}")
        drive_the_window_opens_and_owns_its_keys(m)
        drive_stepping(m)
        drive_two_clicks(m)
        drive_classes(m)
        drive_zoom_and_pan(m)
        drive_saving(m, td)
    return 1 if FAIL else 0


# ---------------------------------------------------------------- the harness
def _xvfb():
    """(process, display) for an X server with no screen, or None.

    -displayfd has the server pick a free display itself and write the number
    once it is accepting connections, so there is nothing to race and nothing
    to sleep for -- xvfb-run sleeps three seconds a launch. It is started
    without an auth file, which means any local user could connect to it for
    the few seconds it lives; all they would find is a synthetic clip."""
    if ON_SCREEN or not shutil.which("Xvfb"):
        return None
    r, w = os.pipe()
    x = subprocess.Popen(["Xvfb", "-displayfd", str(w), "-screen", "0", "1600x1200x24", "-nolisten", "tcp"],
                         pass_fds=[w], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(w)
    try:
        num = os.read(r, 32).decode().strip() if select.select([r], [], [], 15)[0] else ""
    finally:
        os.close(r)
    if num.isdigit():
        return x, f":{num}"
    x.kill()
    x.wait()
    return None


def _host(xvfb):
    """Where the windows go: (environment, what to call it), or None."""
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    env.pop("MPLBACKEND", None)
    if xvfb:
        # X11 only. Left to themselves Qt and GTK find the Wayland session and
        # open on the desktop anyway, DISPLAY or no DISPLAY
        env.pop("WAYLAND_DISPLAY", None)
        env.update(DISPLAY=xvfb[1], QT_QPA_PLATFORM="xcb", GDK_BACKEND="x11")
        return env, f"Xvfb {xvfb[1]}, off screen"
    if sys.platform in ("win32", "darwin") or env.get("DISPLAY") or env.get("WAYLAND_DISPLAY"):
        return env, "the desktop"
    return None


def _stop(p):
    """The child and anything it started, gently first."""
    if not hasattr(os, "killpg"):
        p.kill()
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(p.pid, sig)
            p.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            continue
        except ProcessLookupError:
            return


def _run_child(backend, host, open_within=25, finish_within=90):
    """(exit code, output, hung). Two deadlines, because the two hangs mean
    different things: before the window is up it is the toolkit, after it is us."""
    p = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--drive", backend],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=host[0],
                         start_new_session=True)
    try:
        out, _ = p.communicate(timeout=open_within)
        return p.returncode, out, False
    except subprocess.TimeoutExpired as ex:
        so_far = ex.output or b""
        so_far = so_far.decode(errors="replace") if isinstance(so_far, bytes) else so_far
    if UP in so_far:
        try:
            out, _ = p.communicate(timeout=finish_within)
            return p.returncode, out, False
        except subprocess.TimeoutExpired:
            pass
    _stop(p)
    out, _ = p.communicate()
    return p.returncode, out, True


def test_main_refuses_a_backend_that_cannot_open_a_window():
    """The commonest first experience on Linux. It has to end in instructions."""
    print("\nmark: a backend that cannot open a window")
    import matplotlib
    matplotlib.use("Agg", force=True)
    argv, sys.argv = sys.argv, ["mcdonald mark", "/nowhere/no-such-clip.mp4"]
    try:
        mark.main()
        msg = ""
    except SystemExit as ex:
        msg = str(ex.code)
    finally:
        sys.argv = argv
    check("non-interactive 'agg'" in msg.lower(), "main() stops, naming the backend it found",
          repr(msg[:60]))
    check("no-such-clip" not in msg, "before it goes looking for the video")
    for fix in ("pip install PySide6", "python3-tkinter python3-pillow-tk", "apt install python3-tk",
                "brew install python-tk"):
        check(fix in msg, f"and offers: {fix}")
    check("ImageTk" in msg, "says why tkinter alone may not be enough")
    check("track CSV" in msg, "and leaves a way through with no window at all")


def test_the_window_under_every_backend_that_opens():
    xvfb = _xvfb()
    try:
        host = _host(xvfb)
        if host is None:
            print("\n  SKIP  no display, and no Xvfb to stand in for one")
            SKIP.append("the window (no display)")
            return
        print(f"\nthe window, hosted on {host[1]}")
        backends = WANTED or [b for b in BACKENDS if b != "MacOSX" or sys.platform == "darwin"]
        with ThreadPoolExecutor(len(backends)) as pool:       # the children are the work, not these threads
            results = list(pool.map(lambda b: _run_child(b, host), backends))
    finally:
        if xvfb:
            xvfb[0].terminate()
            xvfb[0].wait()
    driven = 0
    for b, (rc, out, hung) in zip(backends, results):
        if UP not in out:
            why = "hung before a window opened" if hung else \
                  next((ln for ln in reversed(out.strip().splitlines()) if ln.strip()), f"exit {rc}")
            print(f"  SKIP  {b}: {why.strip()[:150]}")
            SKIP.append(b)
            continue
        driven += 1
        body = out.split(UP, 1)[1].strip("\n")
        print(body)
        failed = [ln.split("FAIL", 1)[1].strip() for ln in body.splitlines() if ln.startswith("  FAIL")]
        FAIL.extend(f"{b}: {f}" for f in failed)
        if hung:
            print(f"  FAIL  {b} hung after the window was up -- a handler is waiting on something "
                  "(a modal dialog?)")
            FAIL.append(f"{b}: hung")
        elif rc != 0 and not failed:
            print(f"  FAIL  {b} exited {rc} without finishing")
            FAIL.append(f"{b}: exit {rc}")
    if not driven:
        print("  no interactive backend could open a window here, so the window itself is untested")


def main():
    global ON_SCREEN, WANTED
    if "--drive" in sys.argv:
        return drive(sys.argv[sys.argv.index("--drive") + 1])
    ON_SCREEN = "--on-screen" in sys.argv
    WANTED = [a for a in sys.argv[1:] if not a.startswith("-")]
    print("McDonald UAP Toolkit — the marking window")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    if FAIL:
        print(f"\n{len(FAIL)} FAILED: {', '.join(FAIL)}")
        return 1
    print(f"\n{'ALL PASS' if not SKIP else 'ALL PASS (skipped: ' + ', '.join(SKIP) + ')'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
