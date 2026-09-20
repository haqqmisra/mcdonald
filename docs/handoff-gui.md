# Handoff: the object-marking GUI

> **For what comes next, read `docs/handoff-ui.md`** — the brief for making the
> tool usable from the command line alone and from the window alone, with an
> audit of how far each gets today. This file is the record of how the window
> got here: the decisions, the measurements, and the traps.

Written 2026-09-20 at the end of the session that built `mcdonald mark` 0.2.0,
and brought up to date at the end of the next one, the same day, which settled
§6 and built the Qt window. **Start at §0**; §1–§10 are the original handoff,
annotated where they have been overtaken.
Everything below is verified on this machine unless marked otherwise.

---

## 0. Where things stand (end of the second session, 2026-09-20)

*The link (§0.1) was added later the same day, after Jacob had used the window.
His verdict on the window: "a nice feel". His one complaint: `c` on PR148
ringed a lot of features and not the ship. That is the detector's scale, not
the window — see the first finding in §0.1.*

**§6 is decided: route (b), finder scope.** Jacob chose a PySide6 front end as
an optional extra, with the matplotlib window kept as the fallback.

What now exists:

| | lines | what it is |
|---|---|---|
| `src/mcdonald/mark.py` | ~400 | `MarkSet`, `contact_strip`, the matplotlib `Marker`, and three things both windows share: `save_all()`, `status_line()`, `choose_gui()` |
| `src/mcdonald/mark_qt.py` | ~990 | the Qt window: `QtMarker` over `FrameStore` (decode-ahead cache), `FrameView`, `Timeline`, `Loupe`, `Overview`, undo via `QUndoStack` |
| `src/mcdonald/autolink.py` | ~250 | marks → detector choice → candidates on a process pool → `link_track` → distance from every mark. No Qt. §0.1 |
| `tests/test_gui.py` | ~960 | one list of checks run against both windows through a rig each, a finder section for Qt, and a comparison of the files the two saved |
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
on Xvfb and on the Wayland desktop. **TkAgg passes too, as of later on
2026-09-20**: Jacob installed `python3-pillow-tk` and ran
`python3 tests/test_gui.py TkAgg` — all 47 window checks, so the backend that
Windows and macOS users get by default is no longer unverified. Only WxAgg
still skips (no `wx`), and nothing depends on it.

`mark.main()` was driven whole on PR148: argv → Qt window → two clicks → `q` →
JSON, CSV and contact strip on disk, exit 0.

### 0.1 The link: from the marks to an automatic track (`l`)

`src/mcdonald/autolink.py` (~250 lines, no Qt in it) and the `l` key in the Qt
window. `link_from_marks(clip, marks)` is a generator of `Link`s: static masks →
the detector's scale and polarity chosen from the marks → the detector forward
from the first mark on a process pool → `link_track`, seeded and primed from the
marks → the distance from every hand mark. The window draws the track as it
grows (white; hand marks keep the class colours), boxes its position on each
frame, shows the linked frames on the timeline so gaps read as gaps, and puts
`track_strip` in front of the analyst when it ends. `s` also writes
`<tag>_autotrack.csv` (which `--track` reads) and its strip.

**On the Technical Note's case, PR113, the two documented clicks give back the
published result, in the window:** 21 px dark chosen, frames 408–411 linked,
0.005 px from `tests/golden/pr113_transit_curated.csv`, 1.9 and 0.5 px from the
two hand marks, (−102.8, +97.1) = 141.4 px/frame against the published 142.
48 s (12 masks, ~25 choosing the scale, 8 linking); longest GUI stall 81 ms.
Now pinned in `test_golden.py`.

Four findings came out of building it. All four are in tests.

1. **The scale has to come from the marks, and "the smallest that works" is the
   wrong rule.** At the 9 px default the detector does not see an object much
   larger than 9 px at all, which is what `c` showed on PR148. But choosing the
   smallest scale that puts a candidate within 6 px of the marks fails too: a
   5 px filter fires on the *rim* of an 18 px disc, within tolerance of a mark
   on its centre, and the track then rides the rim 6 px off. `pick_detector`
   climbs instead — on to the next scale while that brings the candidate ≥0.5 px
   closer to the marks. (`forensics.best_scale` still has the old rule.)
2. **`source_candidates`' default `min_resp=35` loses PR113's last frame.** The
   object responds at 44 on frame 408 and 32 on 411. The vendored golden track
   was made at the sweep's threshold of 5. A blind track needs 35, because it
   starts on the strongest candidate; a seeded, gated one chooses by position
   and can listen for weak ones. `frame_candidates(..., min_resp=)` makes the
   difference explicit and `autolink.MIN_RESP = 5`. **The CLI's `--auto-track`
   still cannot do PR113**: it has no way to pass a velocity, and uses 35. The
   route is now mark → `l` → `--track <tag>_autotrack.csv`.
3. **`link_track` starts again on the strongest candidate after `max_gap`
   frames without a link** — by design, and documented, but it means a track
   under the object's name that is on something else. `autolink` stops one
   frame short of that and says "lost". The test shows `link_track` alone
   jumping to a decoy on the same candidates.
4. **`mcdonald integrity --auto-track` was broken**: `import bg_layers`, the
   research repo's name for `layers`. Fixed, and the per-frame detector is now
   one function, `forensics.frame_candidates`, used by `layers`, `integrity`
   and the link.

Costs to know: the detector is O(size²) per pixel — 0.75 s a 1080p frame at
9 px, 4 s at 21, 9 s at 31, 20 s at 45 — so the pool matters, and a link at a
large scale over a long clip is minutes. It is progressive and `l` stops it.
An FFT route through `source_candidates` would fix the scaling, but it changes
the core detector's arithmetic and wants `test_golden` behind it.

The pool is `forkserver` (`spawn` on Windows), never `fork`: the caller is a
GUI with threads. The children import the caller's main module by path, so a
program piped to `python -` cannot start one; `autolink` then runs inline.

Check counts, corrected: the first handoff's 46 / 75 / 33 each counted the
`ALL PASS` line as a check. Counting `  PASS` lines only, the suites now stand
at `test_measurement` 62 (45 before `autolink`'s 17), `test_reduction` 74,
`test_published` 32, `test_gui` 297 with TkAgg running, and `test_golden` has
PR113's two clicks ahead of PR144.

### 0.2 Everything that was on the list (third pass, 2026-09-20)

Jacob, after using `l`: "build all remaining features". All of these are in,
tested, and in the window's key list (`mcdonald mark --help`, `mark_qt.py`).

| | what it is now | where |
|---|---|---|
| link backwards; re-seed after a loss | **every mark is a seed.** Between two marks the track is linked forward from one and backward from the other with the velocity that pair gives; before the first and after the last it runs until lost. A mark placed after a loss resumes the track both ways. `arrivals` says how far each mark's forward link lands from the *next* mark — the check against a mark it was not seeded from | `autolink.assemble`, `_pass` |
| disagreements | where the forward and backward links pick different candidates the frame is **disputed**: the nearer mark's version is kept, the frame is amber on the timeline and its box dashed, and the CSV's `source` column says `disputed` (else `both` / `forward` / `backward`) | `autolink.assemble`, `mark_qt.Box` |
| relinking is cheap | candidates are kept per (frame, size, polarity) for the life of the window, so `l` after one more mark computes new frames only | `link_from_marks(cache=)` |
| `object2` | `l` links `object` and `object #2` together, the class in hand first; each has its box (the second labelled 2), its strip and its `<tag>_autotrack_object2.csv`. A class whose marks are all deleted loses its track on the next `l` | `QtMarker.links` |
| the pipeline takes marks | `layers --marks`, `integrity --marks`, `run --marks`. **On PR113 from the command line: `--auto-track` links 1 of 13 frames, `--marks` links all 4 onto the golden positions** | `autolink.track_from_marks_file` |
| per-mark provenance | `MarkSet.how`: absent for a hand mark, so old files load and a file of hand marks is byte-for-byte what it was. In the JSON (`"how"`), the CSV (`how` column, and a header line counting them), the contact strip ("snapped") and the table | `mark.MarkSet` |
| snapping | shift+click puts the mark on the detector's nearest candidate within 12 px at the scale shown, and records `snapped to the 21 px dark candidate 1.8 px from a click at (x, y)`. No candidate near: nothing placed, and it says so. Nudging a snapped mark makes it a hand's again | `QtMarker._snap` |
| nudge | ctrl+arrows 1 px, ctrl+shift+arrows 0.1 px; a run of nudges is one undo | `_Put.mergeWith` |
| scrubbing | a drag on the timeline goes to the newest frame asked for, not to each in turn | `QtMarker._scrub` |
| extraction | `Clip(..., extract=False)`, `extracted()`, `n_extracted()`, `extract(stop=)`; the Qt window extracts behind a progress bar with a Cancel on it | `clip.Clip`, `mark_qt.extract_with_progress` |
| `forensics.best_scale` | now climbs to the closest candidate, as `pick_detector` does, not the smallest within tolerance | `forensics` |

Verified on real clips, not only synthetic ones:

- **PR113** through the real window again after the rewrite: 21 px dark, 408–411
  on the golden positions, every row `both`, 58 s, longest GUI stall 97 ms.
  `test_golden` pins it.
- **PR144, frames 300–500**, from two marks 160 frames apart (lifted from the
  vendored track): all 201 frames linked at 9 px bright, **median 0.00 px and
  worst 0.2 px from `tests/golden/pr144_track.csv`**, forward and backward links
  agreeing on all 161 frames between the marks, none disputed, 75 s. A third
  mark and `l` again: 0.6 s.
- `test_golden` whole: PR113's two clicks, and PR144's layer rates unchanged
  (599 / 500 / 99 px/s) after the changes to `Clip` and `layers`.

Suites now: `test_measurement` 82 checks (50 s), `test_reduction` 84,
`test_published` 32, `test_gui` 321 with only WxAgg skipping (42 s).

Two things were weighed and **not** done, on purpose:

- **An FFT route through `source_candidates`**, for the O(size²) cost. It
  cannot reproduce the direct correlation's float32 rounding, so peak pixels
  can differ where responses nearly tie, and every published position comes
  through that function. It needs its own session with `test_golden` and
  `test_published` behind it, not a ride along with GUI work.
- **Running the Qt window on Windows and macOS**: nothing here can.

How to try all of it by hand is at the end of §0.

One more behaviour worth knowing: `MarkSet.remove_last` now drops a class when
its last mark goes. It used to leave `{"object2": {}}` behind in memory, which
`to_dict` hid and a reloaded file did not have — found when a test compared
the two.

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

1. ~~`sudo dnf install python3-pillow-tk` and rerun the suite under TkAgg.~~
   **Done 2026-09-20, ALL PASS.**
2. ~~Close the loop in the window: `link_track` from the two marks, drawn over
   the clip.~~ **Done — §0.1.** What follows from it: link backwards as well as
   forwards; re-seed from a later mark after a loss; give `layers` and
   `integrity` a `--marks FILE` so the pipeline can take the velocity and the
   low threshold without going through the window.
3. **Run the Qt window on Windows and macOS** once. The abi3 wheel covers both;
   nothing here has been seen to work there. Still open.
4. ~~Smaller: nudge; coalesce scrubs; extraction with progress; per-mark
   provenance, then snapping.~~ **Done — §0.2**, with linking backwards,
   re-seeding, `object2`, and `--marks` for the pipeline.
5. What is left is no longer GUI work: the detector's cost at large scales
   (§0.2), and using the window on the rest of the corpus to find out what it
   still lacks.

### Trying it by hand

```bash
export MCDONALD_CATALOG=/hugespace/local/research/uap/pursue_index/records.csv
mcdonald mark PR113 --n0 400 --n1 420 --out /tmp/try113
```

1. Go to frame 408 (type it in the frame box, or `.`), click the dark object
   near (1009, 313); go to 411, click it near (702, 604). The dock shows
   v ≈ (−102, +97) px/frame.
2. `l`. About a minute: masks, then the scale (it settles on 21 px dark), then
   the link. Expect "4 of 4 frames linked, 408–411 … within 1.9 px of all 2
   marks; each mark's link arrives within 0.5 px of the next mark; searched
   back to frame 400; searched on to frame 420", the white track, and the strip
   with the same dark blob in all four tiles.
3. `l` again: it finishes in a second or two. Nothing is recomputed.
4. `c`: the rings are now at 21 px dark, and the object is one of them.
   shift+click near it on 409: the mark jumps to the ring's centre and the
   table says `snap`. ctrl+arrows nudge it (and it is `hand` again); ctrl+z.
5. `s`, then look in `/tmp/try113`: `pr113_autotrack.csv` should match
   `tests/golden/pr113_transit_curated.csv` row for row, with a `source`
   column of `both`.
6. `mcdonald layers PR113 --n0 400 --n1 420 --marks /tmp/try113/pr113_marks.json --out /tmp/try113b`
   prints the same four-frame link before it does anything else.

For a loss and a re-seed, and for a disputed frame, PR113 is too short; PR144
(`mcdonald mark PR144 --n0 300 --n1 500`) is the clip to try them on.

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
2. ~~`sudo dnf install python3-pillow-tk`~~ — **done 2026-09-20; TkAgg passes
   `test_gui.py`.** The original note: still needed, and still the most
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
