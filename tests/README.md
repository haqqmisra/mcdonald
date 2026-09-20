# tests

Four suites, answering four different questions.

## `test_measurement.py` and `test_reduction.py` — does this install work?

Portable. Neither needs video data; together they run 100 checks in under a
minute, and they are what to run after installing.

```bash
python3 tests/test_measurement.py        # masks, registration, layers, detection
python3 tests/test_reduction.py          # symbology, kinematics, scale, comotion, report
```

`test_reduction.py` anchors several checks to published values — PR113's
graticule k and omega, PR149's 192–255 kn scale-bar bound, the 8 % small-angle
overstatement the Technical Note quantifies — so a change that would move a
number in a manuscript fails here first. It also pins the behaviours that exist
to stop a wrong number: that a bad track is sigma-clipped, that non-uniform
motion is refused rather than averaged, and that a case report never drops a
NO POWER entry.

Every check builds a scene whose answer is known by construction and asks the
library to recover it: a known rigid shift, two backgrounds moving at
different rates, striated versus isotropic texture, planted repeated frames, a
compact source on a known path, a redaction block that must be masked beside a
dark scene that must not be. It also checks the packaging contract — that a
run never writes into the installed package, that the catalog is genuinely
optional, and that ffmpeg is present.

The two-layer check is the one worth watching. It prints what a single
consensus over both layers *would* have said, which is the wrong number this
whole library exists to avoid.

## `test_golden.py` — do the real clips still give the published numbers?

Needs the video files, which are not distributed with the package. Skips
cleanly and says why when they are absent.

```bash
export MCDONALD_CATALOG=~/research/uap/pursue_index/records.csv
python3 tests/test_golden.py             # ~5 min: a 200-frame window of PR144
python3 tests/test_golden.py --full      # tens of minutes: the whole clip
```

The default run measures frames 300–500 of PR144 and compares against a
baseline recorded on 2026-09-19. `--full` runs the documented whole-clip
command and compares against the published values in `docs/method.md` § 4.

The object track is vendored in `golden/pr144_track.csv`, so only the video
has to be found.

### Changing a baseline

A golden number changes only when the measurement genuinely should have
changed. If one moves, find out why before updating it: these are consensus
medians over dozens of templates, and a broken mask or a mis-set zero-exclusion
zone moves them by tens of pixels per second, not by ones. Record the reason in
the commit message — some of these numbers have been published.


## `test_published.py` — can we still produce every published number?

Walks the quantitative claims of the Technical Note (JAIS 2026-08-I012054) and
the PR144 working notes one at a time. Most need no video — they are the
reduction applied to already-recorded tracks — so it runs in a second.

```bash
python3 tests/test_published.py
python3 tests/test_published.py --tracks /path/to/uap/analysis
```

A failure here means a published number can no longer be produced by the code
that is supposed to produce it. That is a retraction risk, not a test nit.

Two findings it pins deliberately, because both are easy to lose:

- **PR149's "43 frames spanning 3.2 s"** is the exit timestamp, not the
  duration; the tracked interval is 2.70 s (n = 17 → 98). And **"straight to
  2.6 px rms"** is the x component alone — the workup recorded 2.6 px (x) and
  3.4 px (y), so the 2-D scatter is 4.2 px.
- **PR113's 142 px/frame is not regenerable from `pr113_transit.csv`.** That
  file is a per-frame component dump ordered by area with no column saying
  which component is the object, so a blind refit returns 52 px/frame off
  unrelated blobs. The number comes from the object's displacement over
  e048–e051, recorded only in `pr113_track.py`'s docstring. Reproducing it
  needs the frames plus that hand identification.


## `test_gui.py` — does the marking window do what its keys say?

Portable, no video, a few seconds. `MarkSet`, where the marks live, is covered
headless in `test_reduction.py`; this covers the window over it.

```bash
python3 tests/test_gui.py                 # every interactive backend that opens
python3 tests/test_gui.py QtAgg TkAgg     # just these
python3 tests/test_gui.py --on-screen     # on the desktop rather than Xvfb
```

Synthetic mouse and key events go in through `fig.canvas.callbacks`, the
registry real events arrive through, so every handler on the canvas runs —
matplotlib's own included. That matters: the first run found that `s` also
opened matplotlib's save-figure dialog, that `l` put the image on a log axis,
that a click made with the toolbar's zoom tool armed was also a mark, and that
a middle-drag snapped back on every other motion event. Calling the handlers
directly finds none of those.

The clip is synthetic — a compact source on a known path — so two clicks on it
must give back the velocity it was built with, to 1e-6 px/frame.

Each backend runs in its own subprocess under two deadlines. A toolkit that
hangs *before* a window opens is the environment's problem and is skipped with
the reason; a hang *after* is ours, and fails — from outside, that is what a
modal dialog looks like. Where `Xvfb` exists the windows are hosted off screen,
so the suite runs the same on a laptop and on a host with no display.

`TkAgg` needs both `tkinter` and `PIL.ImageTk`, which some distributions package
separately (Fedora: `python3-tkinter` and `python3-pillow-tk`). It is the
default backend on Windows and macOS, so a skip there is worth closing before a
release.
