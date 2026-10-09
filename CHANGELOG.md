# Changelog

Every version that went out, newest first. The version is written in one place,
`src/mcdonald/__init__.py`; each release from 0.2.4 on is a git tag and is on PyPI.

## Unreleased

- `tests/test_tether.py` runs with the other portable suites: in `tools/suites.sbatch`, on the
  Mac and Windows runners, and in the READMEs' install checks. Nothing measured changes.

## 0.2.14 (2026-10-08)

- One window: pages over the video in place of pop-up windows (the start screen is the one
  dialog, and the home page); one button that finds the object, follows it and measures it,
  with Advanced revealing the three steps; the report leads with its conclusion.
- More than one object in a video: ticks on Find's rows, or `run --each DIR` on folders
  `object-1`, `object-2` …; a case and a report for each, one list of them, and every track
  drawn on the video in its own colour.
- How many objects are looked for: the segment step asks, and `run --each --objects N` holds the
  count against what was followed; a group of points is split into its members, each followed
  over its own frames, and a flock of birds is named in the report.
- `mcdonald tether`: is something tied to the object, and does it swing? A pendulum period
  becomes metres of line; a stage of `run`.
- The window's look audited: one accent colour, one button style, a column to read in.

## 0.2.13 (2026-10-05)

- Find sees the slow crawlers in a still scene: a still-scene pass in `look --propose`.

## 0.2.12 (2026-09-29)

- The beat (a periodic brightness or size change) is measured in windows along the track,
  named by its fundamental, and shown in the report.

## 0.2.11 (2026-09-27)

- The link follows an object by its motion when no spot size holds it (PR43's streak links).
- The link's gate at the marks grows with the spot size.
- Registration: the ZNCC variance is computed in float64, and the second pass runs once a
  window, not once a pair.
- Ready for Windows: every file UTF-8, a download that cannot start says why, and a Windows CI job.
- Help -> About and the README say where to donate (Project Janus at Blue Marble Space).

## 0.2.10 (2026-09-26)

- Six speedups that give the same numbers: Follow 74 s -> 8 s, Measure a quarter shorter, the
  window's start halved.
- The window fits the screen and remembers its size, shows notes as a toast, lists recent
  videos and takes dropped files, and never waits on the network.

## 0.2.9 (2026-09-26)

- Step 2's track-check lines, shortened.

## 0.2.8 (2026-09-26)

- Progress lines name every step in one to three words.
- Open by catalog name: the question on two lines, with the three ways to write a name.

## 0.2.7 (2026-09-25)

- The applications-menu entry starts this install's window, not the first one on the PATH.

## 0.2.6 (2026-09-25)

- `mcdonald setup` adds the window to the applications menu.

## 0.2.5 (2026-09-25)

- `pip install mcdonald` gives the window too: PySide6 is a dependency.

## 0.2.4 (2026-09-25)

- First release on PyPI: `pip install mcdonald`, no git needed. The repository went public.

## 0.2.3 (2026-09-25)

- Help -> About: version, release date, what it is, the quote, the license.

## 0.2.2 (2026-09-25)

- mcdonald updates itself: the window asks, the command line prints the command.

## 0.2.1 (2026-09-25)

- The version goes up with every change sent out, written in one place.

## 0.2.0 (2026-09-20 to 2026-09-24)

- The reduction: symbology, kinematics, scale, co-motion, figures, and the `mcdonald run`
  driver from a video to a case report.
- `tests/test_published.py` walks every published number it can reproduce.
- The marking window (`mcdonald mark`, `mcdonald-gui`): find the object, mark it, link a track,
  play the clip, measure from the window, with progress and Stop on every long step.
- The command line does the whole marking job with no window: `look`, `mark --set`, `--json`
  everywhere, exit codes.

## 0.1.0 (2026-09-19)

- The measurement nucleus as an installable package: background layers, clip integrity, the
  track sheet, and the catalog adapter.
