# Handoff: the object-marking GUI

Written 2026-09-20 at the end of the session that built `mcdonald mark` 0.2.0.
Everything below is verified on this machine unless marked otherwise.

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
| `Marker` (10 methods) | **yes** (2026-09-20) | the matplotlib window: events, zoom, pan, redraw |
| `main()` | no | arg parsing, backend check |

The `Marker` window was driven end to end on 2026-09-20 with synthetic
matplotlib events on a real clip (PR113, frames 404–416), under **QtAgg and
GTK3Agg, identically**: window construction, frame stepping, click → mark
(coordinates round-trip through the axes transform exactly), class switching,
backspace, scroll zoom, view reset, and save of all three outputs. Two
synthetic clicks produced velocity (−102.3, +97.0) px/frame against the
documented (−103, +98). The driver is `gui_test.py`-style and worth
re-creating as a proper test — see §9.

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
3. **`pip install PySide6`** — only if route (b) or (c) is chosen. Verified to
   have a working `cp310-abi3` wheel for Python 3.14.
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
6. **Promote the ad-hoc GUI driver into a real test.** Synthetic
   `MouseEvent`/`KeyEvent` through `fig.canvas` exercised every handler on a
   real clip in about a second; parametrised over whichever interactive
   backends import, it would give the window the same regression cover the
   rest of the package has. Skip cleanly when no interactive backend exists,
   as the other suites do for a missing corpus.

## 10. State at handoff

- `mcdonald` 0.2.0, commit `19be3dc`, pushed, working tree clean.
- Three suites green and portable: `test_measurement` (46 checks),
  `test_reduction` (75), `test_published` (33, no skips) — 154 in about a
  minute, no video data. `test_golden` needs the corpus and passes.
- Research repo `haqqmisra/uapsac` at `7a87b2d`, also clean and pushed.
- `MCDONALD_CATALOG=/hugespace/local/research/uap/pursue_index/records.csv`
  wires the package to the PURSUE corpus for real-clip work.
