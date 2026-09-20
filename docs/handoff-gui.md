# Handoff: the object-marking GUI

Written 2026-09-20 at the end of the session that built `mcdonald mark` 0.2.0,
and brought up to date at the end of the next one, the same day, which settled
§6 and built the Qt window. **Start at §0**; §1–§10 are the original handoff,
annotated where they have been overtaken.
Everything below is verified on this machine unless marked otherwise.

---

## 0. Where things stand (end of the second session, 2026-09-20)

**§6 is decided: route (b), finder scope.** Jacob chose a PySide6 front end as
an optional extra, with the matplotlib window kept as the fallback.

What now exists:

| | lines | what it is |
|---|---|---|
| `src/mcdonald/mark.py` | ~400 | `MarkSet`, `contact_strip`, the matplotlib `Marker`, and three things both windows share: `save_all()`, `status_line()`, `choose_gui()` |
| `src/mcdonald/mark_qt.py` | ~990 | the Qt window: `QtMarker` over `FrameStore` (decode-ahead cache), `FrameView`, `Timeline`, `Loupe`, `Overview`, undo via `QUndoStack` |
| `tests/test_gui.py` | ~900 | one list of checks run against both windows through a rig each, a finder section for Qt, and a comparison of the files the two saved |
| `pyproject.toml` | | `gui = ["PySide6-Essentials>=6.6"]` |

`mcdonald mark CLIP` opens the Qt window when PySide6 imports and there is a
display, else the matplotlib one (`--gui auto|qt|mpl`). With no clip named, the
Qt window asks for one.

Measured on PR148 (1908×1028, lossless PNG, 0.8 MB/frame), this machine:

| | matplotlib window | Qt window |
|---|---|---|
| one frame step | ~90 ms (24 decode + 58 Agg render) | **5 ms** with read-ahead; 59 ms to a frame not yet decoded |
| playback at 1× | n/a (~11 frames/s) | **120 of 120 frames in 4.00 s, 0 skipped**, from a cold cache |
| playback at 2× | n/a | 179 of 180 in 3.00 s, 0 skipped |
| overview, 72 tiles | n/a | 1.8 s |
| detector candidates | n/a | 19 s the first time (static masks, once per clip), then 1.4 s a frame; GUI never stalled more than 50 ms |

Decoding is the bottleneck and it scales: one thread 20 frames/s, four 73,
eight 110 (`QImage(path)`; PIL is ~20 % slower and scales the same).

`test_gui`: 231 checks, ~15 s — 11 on `main()`, 77 on the Qt window, 47 per
matplotlib backend, 2 comparing the saved files (they agree to 6e-14 px). Green
on Xvfb and on the Wayland desktop. TkAgg and WxAgg still skip.

`mark.main()` was driven whole on PR148: argv → Qt window → two clicks → `q` →
JSON, CSV and contact strip on disk, exit 0.

### New traps, paid for in this session

- **`QTest.qWait()` holds the GIL.** A Python worker thread starves while the
  GUI thread sits in it: the detector "never returned" in 90 s under a
  `qWait(100)` loop and took 19 s under `app.exec()`. The window is fine; the
  measuring script was not. In tests, wait in `qWait(10)` slices with Python in
  between (`QtRig.wait_for`), or use a real event loop.
- **`Future.cancel()` runs the done-callbacks there and then**, in the caller.
  `FrameStore.want()` died with a `KeyError` on the second scrub because the
  callback had already forgotten the future.
- **Qt does not raise without a display; it aborts the process.** So
  `choose_gui()` looks for `DISPLAY`/`WAYLAND_DISPLAY` before it picks Qt.
- **A Qt scene puts pixel (0, 0) over [0, 1); the package puts its centre at
  (0, 0).** `FrameView` offsets the pixmap by (−0.5, −0.5) so scene coordinates
  are image coordinates. The red-pixel check in `test_gui.py` pins this against
  rendered pixels in both windows. Do not "simplify" the offset away.
- **`QGraphicsView.mapToScene()` takes whole pixels.** Marks go through
  `viewportTransform().inverted()` instead, which is exact to ~1e-13 px. The
  view still *scrolls* in whole screen pixels, so zoom-about-cursor and pan are
  good to 1 screen px, not 1e-6 (`QtRig.px_tol`).
- **A check printed inside `redirect_stdout` is a check nobody sees.** Redirect
  the key press, not the assertions after it.
- **`Clip(video)` with no `--n0/--n1` extracts the whole clip**, and that is now
  the Qt default: PR148 is 1793 frames, ~1.4 GB under `/tmp/mcdonald`. `main()`
  says so before it starts. Extraction still blocks in the terminal.

### What the detector overlay showed, worth keeping in mind

On PR148 frame 300 the detector's 25 strongest "compact sources" include the
reticle's four corner marks and the boresight ticks, ranked among the pieces of
the ship. That is §1's argument on real pixels, and it is why the overlay marks
nothing and the status line says the choice is the analyst's. It is also why
**snap-to-candidate was left out**: a snapped mark is not a hand mark, and
`MarkSet` has nowhere to record the difference. Add provenance per mark first.

### Next, in order of value

1. **`sudo dnf install python3-pillow-tk`** (§7.2) and rerun
   `python3 tests/test_gui.py TkAgg`. Still the default backend on Windows and
   macOS, still untested here.
2. **Close the loop in the window**: run `link_track` from the two marks and
   draw the automatic track over the clip, so "did it lock onto the object?" is
   answered where the marks were made. The candidates are already computed off
   the GUI thread; this needs them for a range of frames, and a progress bar.
3. **Run the Qt window on Windows and macOS** once. The abi3 wheel covers both;
   nothing here has been seen to work there.
4. Smaller: nudge the current mark with ctrl+arrows; coalesce timeline scrubs so
   a drag decodes only the newest frame; extract in a thread with progress
   rather than blocking the terminal; per-mark provenance, then snapping.

---

## 1. Why this tool exists, in one paragraph

Nothing in the toolkit can decide **which thing in the frame is the object**,
and it does not pretend to. Every measurement downstream inherits that
decision. Two clicks are enough to supply it: the first is the linker's seed,
the pair gives the velocity the linker cannot acquire on its own, and the
automatic track covers the rest. On DOW-UAP-PR113 two clicks reproduce the
published 142 px/frame. So the GUI is not a convenience — it is the interface
to the one input the package genuinely requires from a human.

The strongest argument for making it good: on PR117 the most trackable feature
in the frame was a blemish stuck to the display, the first analysis tracked it,
and it drew exactly the wrong conclusion. No detector prevents that. Looking
does.

## 2. What exists now

`src/mcdonald/mark.py`, 317 lines, shipped and working. Run it with
`mcdonald mark CLIP.mp4 --n0 400 --n1 420`.

Deliberately split in two:

| | tested? | what it is |
|---|---|---|
| `MarkSet` (12 methods) | **yes**, headless | all the state: marks by class and frame, `velocity()`, `seed()`, JSON save/load, `write_track_csv()` |
| `contact_strip()` | manually | the verification artifact: marked frames magnified with the marks drawn back on |
| `Marker` (10 methods) | **yes**, `tests/test_gui.py` | the matplotlib window: events, zoom, pan, redraw |
| `main()` | the backend check only | arg parsing, backend check |

The `Marker` window was driven end to end on 2026-09-20 with synthetic
matplotlib events on a real clip (PR113, frames 404–416), under **QtAgg and
GTK3Agg, identically**: window construction, frame stepping, click → mark
(coordinates round-trip through the axes transform exactly), class switching,
backspace, scroll zoom, view reset, and save of all three outputs. Two
synthetic clicks produced velocity (−102.3, +97.0) px/frame against the
documented (−103, +98). The driver is `gui_test.py`-style and worth
re-creating as a proper test — see §9.

**Update, later on 2026-09-20: that is now `tests/test_gui.py`, and writing it
found four defects the hand-driven pass had missed**, all fixed in `mark.py`:

1. matplotlib's default key bindings were still connected. `s` saved the marks
   *and* opened matplotlib's modal save-figure dialog; `l`/`k` put the image on
   log axes; `g` drew a grid; backspace also walked the view history.
2. A click made while the toolbar's zoom or pan tool was armed was also a mark
   — so zooming in for a closer look could silently move the object.
3. Middle-drag pan snapped back on every other motion event (`xdata` was read
   through limits the drag had already moved). A drag of (+64, −32) px moved
   the image (+39, −47).
4. `r` reset to (0, W) × (H, 0), half a pixel off the view the window opens
   with.

The lesson for whatever front end comes next: send events through the canvas's
callback registry, not to the handlers. Calling `Marker.on_key` directly finds
none of 1–2, because the collision is with a handler that is not ours.

**That split is the thing to preserve.** All state lives in `MarkSet`, the
window is a thin shell over it, and that is why the whole workflow is testable
without a display — which is how it was verified here (`tests/test_reduction.py`,
`test_marks_carry_everything_the_linker_needs` and
`test_marks_round_trip_and_read_back_as_a_track`). Whatever toolkit replaces
matplotlib, keep `MarkSet` and swap only `Marker`.

Outputs, all three written on save:
- `<tag>_marks.json` — the marks, by class
- `<tag>_marks.csv` — a track CSV the other commands read, with a `#` provenance header
- `<tag>_marks.png` — the contact strip

## 3. Verified environment facts

Checked on this host (Fedora 44, Python 3.14.7), because two common
assumptions turned out to be false:

| | result |
|---|---|
| `tkinter` | **installed 2026-09-20** (Tk 9.0, `python3-tkinter`) |
| `PIL.ImageTk` | **still missing** — needs `python3-pillow-tk`, which Fedora packages separately from `python3-pillow`. Note the repo has 12.1.0 while the installed pillow is 12.3.0, so dnf may want to adjust versions |
| matplotlib `TkAgg` | **still fails**: `ImportError: cannot import name 'ImageTk'`. **Installing tkinter alone was not enough** |
| matplotlib `QtAgg` | **works**, full GUI path verified (PyQt5 5.15.12 present) |
| matplotlib `GTK3Agg` | **works**, full GUI path verified |
| matplotlib `GTK4Agg` | **works** under `test_gui.py`, both on Xvfb and on the Wayland desktop — the one hang was in an ad-hoc probe and has not recurred |
| `PyQt5` | present — but **GPL or commercial** |
| `PySide6` | not installed; wheel `pyside6-6.11.2-cp310-abi3` downloads fine for Python 3.14. **LGPL** |
| `PySide2`, `PyQt6`, `wxPython` | absent |
| `DISPLAY` | `:0` is set; probing GTK4Agg once hung, so probe backends in a subprocess with a timeout |

## 4. The licensing point, which decides the toolkit choice

The package carries **no licence at present** (2026-09-20: the MIT file was
removed, to be decided once the toolkit is finished). That makes this question
*more* pressing, not less: **a dependency's licence constrains which licences
the package can later adopt.** Anything GPL linked in would force the package
GPL and take a permissive release off the table before the choice is made.

**PyQt5/PyQt6 are GPL or paid commercial.** **PySide6 is LGPL**, fine for
dynamic linking, and is the official Qt binding. Building the GUI on PyQt now
would quietly pre-decide the licence later.

If the GUI moves to Qt, it moves to **PySide6**, not PyQt. (matplotlib itself
will happily *use* whichever binding is installed; this is about what the
package tells people to install.)

## 5. Cross-platform position

Current design adds **nothing to install**: matplotlib is already a hard
dependency, and `mark.py` uses only its event system. What varies is whether
the user has a working interactive backend:

| platform | out of the box | if not |
|---|---|---|
| Windows | Tk ships with python.org Python → works | — |
| macOS | Tk ships with python.org Python → works. Homebrew Python often needs `brew install python-tk` | as noted |
| Linux | **usually not** — distro Pythons split tkinter out, and Fedora splits `PIL.ImageTk` out again | `dnf install python3-tkinter python3-pillow-tk` / `apt install python3-tk`, or `pip install PySide6` |
| conda | Tk present → works | — |

`main()` already detects a non-interactive backend and exits with an
actionable message naming the three fixes, rather than failing obscurely.

**So the zero-install path already covers Windows, macOS and conda.** Linux
users need one or two packages — and the Fedora case shows the trap: matplotlib's
Tk backend needs **both** `tkinter` and `PIL.ImageTk`, and a distribution may
package them separately, so "install tkinter" is not reliable advice. The
backend-check message in `mark.py:main()` now spells out all four routes and
says so.

**TkAgg remains unverified here**, which matters because it is the default on
Windows and macOS. Either `python3-pillow-tk` gets installed, or that path
ships untested — worth resolving before release, not before the next session.

## 6. The decision to make first

**Decided 2026-09-20: (b), finder scope — see §0.** One number the argument
below lacked: the matplotlib window was measured at ~90 ms a frame step on
1080p (11 frames/s, the same under QtAgg and GTK3Agg), so "sluggish" means no
playback, not unusable. The extra is `PySide6-Essentials`, not `PySide6`: the
meta-package adds ~350 MB of Addons (WebEngine, 3D, Multimedia) for nothing.

Three routes, in increasing cost:

**(a) Keep matplotlib, polish it.** Zero new dependencies, already works,
already tested headless. Ceiling: matplotlib's event loop is not a UI
framework — no proper widgets, no file dialog, no undo stack, keyboard
handling is quirky, and redraw on a 1920×1080 frame is sluggish at speed.
Good enough for "click two frames"; poor for "scrub 800 frames looking for the
object."

**(b) PySide6 as an optional extra**: `pip install "mcdonald[gui]"`, with the
matplotlib path as the fallback when it is absent. Real widgets, real
performance, proper zoom/pan, LGPL, one pip install on all three platforms
(abi3 wheel, works on 3.14). Cost: ~100 MB, and two front ends to keep
behaving identically.

**(c) Qt only.** Simplest code, heaviest install, and it breaks the "adds
nothing to install" property that currently makes the package easy to hand to
a colleague.

**Recommendation: (b), structured so (a) remains the fallback.** `MarkSet`
already makes this cheap — one more `Marker`-shaped class, same file format,
same tests.

Worth settling before writing code: is the tool for *marking two frames*
(current scope, matplotlib is ample) or for *finding the object in a clip you
have not seen* — scrubbing, contact-sheet navigation, candidate overlays,
playback? The second is a real application and argues for Qt.

## 7. What to ask Jacob to install

He has offered. In priority order:

1. ~~`python3-tkinter`~~ — **done 2026-09-20**, Tk 9.0.
2. **`sudo dnf install python3-pillow-tk`** — still needed, and still the most
   valuable. tkinter alone did not make TkAgg work: matplotlib's Tk backend
   also imports `PIL.ImageTk`, which Fedora ships in this separate package.
   Until it is in, the backend most Windows and macOS users get by default
   cannot be tested on this machine. (Version wrinkle: the repo has
   pillow-tk 12.1.0 against an installed pillow 12.3.0; dnf may want to move
   one of them.)
3. ~~`pip install PySide6`~~ — **done 2026-09-20, as
   `pip install --user PySide6-Essentials`**: 6.11.2, Qt 6.11.2, 236 MB on
   disk, xcb and wayland platforms both verified. Side effect worth knowing:
   matplotlib's `QtAgg` now binds to PySide6 rather than PyQt5 for *every*
   matplotlib program on this account (it prefers Qt 6). The marking suite
   passes under it. `pip uninstall PySide6-Essentials shiboken6` undoes it.
4. Nothing else. `xvfb` is already used elsewhere in the project and can host
   a headless smoke test of a real window if wanted.

## 8. Traps already paid for — do not rediscover these

- **Frame accuracy is already solved, by construction.** The browser annotator
  in the research repo (`analysis/tools/annotator.py`, 442 lines + 29 KB of
  HTML) is mostly machinery for one problem: being certain the frame you
  clicked is the frame ffmpeg calls *n*. `requestVideoFrameCallback`,
  seeks landing between frames, a quarter-frame bias to reconcile the two.
  **None of that applies here.** `Clip` extracts losslessly to PNGs named by
  absolute frame number, so "which frame is this" is answered by the filename.
  Do not reintroduce a video element.
- **fps is an exact rational.** 92 of 96 corpus clips are 30000/1001, not 30.
  Take it from `clip.info["fps"]` (a `Fraction`); never round, never read it
  from a catalog column.
- **The contact strip is not decoration.** A mark nobody has seen drawn back
  onto the pixels is a number being trusted, not verified. Keep it, and keep
  it magnified.
- **PIL fonts**: use `figures.pil_font()`. Hard-coding a DejaVu path on a host
  without DejaVu does not raise — it silently returns an ~8 px bitmap face
  that ignores the size argument.
- **Probe GUI backends in a subprocess with a timeout.** One probe hung here.

## 9. First moves for the new session

1. Read `src/mcdonald/mark.py` and run
   `python3 tests/test_reduction.py` (the two `mark` tests).
2. Settle §6 — scope first, then toolkit.
3. Ask for the installs in §7.
4. If Qt: add `[project.optional-dependencies] gui = ["PySide6>=6.6"]`, write
   `QtMarker` against the existing `MarkSet`, and have `main()` prefer it when
   importable and fall back to `Marker` otherwise.
5. Keep `MarkSet` the single source of truth, and keep the headless tests
   passing — they are what makes any of this verifiable without a screen.
6. ~~Promote the ad-hoc GUI driver into a real test.~~ **Done 2026-09-20:
   `tests/test_gui.py`**, 8 checks on `main()` and 44 per backend, about 7 s
   for Qt + GTK3 + GTK4 in parallel. See §2 for what it found. The original
   note: Synthetic
   `MouseEvent`/`KeyEvent` through `fig.canvas` exercised every handler on a
   real clip in about a second; parametrised over whichever interactive
   backends import, it would give the window the same regression cover the
   rest of the package has. Skip cleanly when no interactive backend exists,
   as the other suites do for a missing corpus.

## 10. State at handoff

*(Overtaken: see §0 for the state at the end of the second session. What
follows is the state at the first handoff.)*

- `mcdonald` 0.2.0, commit `19be3dc`, pushed, working tree clean.
- Three suites green and portable: `test_measurement` (46 checks),
  `test_reduction` (75), `test_published` (33, no skips) — 154 in about a
  minute, no video data. `test_golden` needs the corpus and passes.
- Research repo `haqqmisra/uapsac` at `7a87b2d`, also clean and pushed.
- `MCDONALD_CATALOG=/hugespace/local/research/uap/pursue_index/records.csv`
  wires the package to the PURSUE corpus for real-clip work.
