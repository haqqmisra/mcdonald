# tests

Five suites, answering five different questions.

## `test_measurement.py` and `test_reduction.py` — does this install work?

Portable. Neither needs video data; together they run 207 checks in about a
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
NO POWER entry. And whose rate the bottom line says it is: until 2026-09-20
`mcdonald run` printed the sea's screen speed over one frame pair as "The object
moves 340 px/s against the striated" (the object against the sea on those frames
is 599), so a case whose layers stage only looked at the background must not
say "object moves", one that measured the object against each layer must name
the layers, and what `mcdonald layers` prints is checked to be written from the
same fields.

Every check builds a scene whose answer is known by construction and asks the
library to recover it: a known rigid shift, two backgrounds moving at
different rates, striated versus isotropic texture, planted repeated frames, a
compact source on a known path, a redaction block that must be masked beside a
dark scene that must not be. It also checks the packaging contract — that a
run never writes into the installed package, that the catalog is genuinely
optional, and that ffmpeg is present.

`test_measurement.py` also covers `autolink`, the step from hand marks to an
automatic track, on a scene built to be PR113's situation: an object faster
than the linker's gate, larger than the detector's default scale, and weaker
than something else in the frame. Its checks pin findings that are easy to
lose. The detector's scale is *not* the smallest that comes within tolerance of
the marks — a 5 px filter does that on an 18 px disc, on its rim, and the track
then rides the rim — but the one whose candidate sits closest to them. When the
object goes, the link stops; `link_track` alone, on the same candidates, starts
again on the decoy, which the test shows rather than asserts. A mark placed
after a loss is a new seed, linked both ways, and the detector is not run again
on a frame it has seen. And where the forward and backward links disagree the
frames are flagged — that one from candidates written out by hand, so that what
"disputed" means is in the test and not only in the code.

It also opens a clip that ffmpeg draws, without extracting it, stops an
extraction, and lets one finish: what the window's progress bar stands on. And
it watches one without extracting it (`reel.Reel`, what the range chooser
plays): the frames of a seek, of reading on, of 110 steps backward and of the
end of the file are each compared with the extracted frame of the same number.
The drawn clip has a sound track on purpose. It is the sound track that makes
ffmpeg, left to write a constant rate, copy the first frame after a seek and
put every later one a frame out; without sound the check passes with the fix
taken out. A file shorter than its header says is found to be, and one ffmpeg
cannot read is an error said once. And
`mcdonald.propose`, on autolink's scene: the disc that moves is the first
proposal, at its velocity, and the brighter disc that never moves — the
strongest thing in every frame — is not proposed at all; the seeds are places it
was seen, off the frame's edge, and the package's own linker started from them is
on the disc; the gate is generous along a fast track and tight across it; and the
list shown is short where one thing stands out and longer where none does. And
`mcdonald.progress`, which every long loop of the measuring stages goes through:
`pooled` gives what `Pool.map` gives, in order, says how far it has got after
every item and stops at the next when asked; time left is said only once there
is a rate to say it from.

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

It first takes PR113 from the Technical Note's two documented clicks to the
four vendored positions the published 142 px/frame was measured over (about a
minute): the detector chosen from the marks, a 142 px/frame object acquired, and
the track within 0.05 px of `golden/pr113_transit_curated.csv`.

The default run then measures frames 300–500 of PR144 and compares against a
baseline recorded on 2026-09-19. It reads the numbers as fields from
`layers --json`, checks that the prose printed beside them is those fields
rounded, and passes `--fresh`: `layers` keeps its templates beside the frames,
and a run that finds them there takes 25 s and tests no registration at all —
which is what this test had been doing on the machine it was written on. `--full` runs the documented whole-clip
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


## `test_cli.py` — can the whole job be done from the command line alone?

Portable: ffmpeg, no video data, about a minute. The third shell, held to the
windows' standard. It runs `mcdonald <command>` as a subprocess, so the exit
code and a stdout with nothing on it but JSON are the real ones, on
`test_measurement`'s planted clip written out as a lossless (FFV1) video: a disc
on a known path, and a brighter decoy that never moves.

```bash
python3 tests/test_cli.py
```

It does what an agent would — look, ask the detector, place marks with `--set`,
link, read the answer — and holds the command line to this: `look`'s overview
tiles are the frames their labels say (each is compared with the true frame and
its neighbours), and it extracts nothing to make them; the planted object is
among a frame's candidates and is *not* the strongest, which is why choosing is
a judgment and not a sort; a position read off the enlarged view is a position
in the clip, to the pixel centre (one red pixel, as `test_gui.py` asks of the
windows); a mark placed with `--set` is an agent's in the JSON, the CSV, the
automatic track's header and above the case report's bottom line, and never in
`by_hand()`; apart from `how`, the file is the one a window saves from the same
marks; the link follows the object for as long as it is in the frame and has no
concerns, and one made from marks on two different things has some; every
command prints the same envelope, with its numbers as fields (`kinematics
--json` gives the planted rate as `v_px_per_s`, and `run --json` has the same
number to the last digit, because both call one function; `layers` on under a
second of clip says so in `no_power` rather than printing an empty table); and
2, 4 and 5 are exits with a sentence, not tracebacks.

## `test_gui.py` — do the marking windows do what their keys say?

Portable, no video, about three minutes (the Qt window's child measures three
cases). `MarkSet`, where the marks live, is
covered headless in `test_reduction.py`; this covers the two windows over it.

```bash
python3 tests/test_gui.py                 # the Qt window, and every matplotlib backend that opens
python3 tests/test_gui.py PySide6 TkAgg   # just these
python3 tests/test_gui.py --on-screen     # on the desktop rather than Xvfb
```

**One list of checks, two windows.** A small rig per front end turns "press
this key" and "click at these image coordinates" into that toolkit's own
events, and the same checks then run against both: stepping, two clicks →
velocity, classes, zoom about the cursor, pan, save, reload, quit. The harness
then compares the marks files the two windows wrote from the same clicks; they
agree to 1e-13 px. That is what stops two front ends drifting apart.

Events go in where real ones do — `fig.canvas.callbacks` for matplotlib; for Qt,
`QApplication.sendEvent` for the mouse and `QTest.keyClick` for keys, which
passes through the shortcut map as a real key does (every key in the Qt window
is a `QAction`'s shortcut, and an event sent straight to a widget never meets
the map) — never to a handler directly. That matters:
the first run found that in the matplotlib window `s` also opened matplotlib's
save-figure dialog, `l` put the image on a log axis, a click made with the
toolbar's zoom tool armed was also a mark, and a middle-drag snapped back on
every other motion event. Calling the handlers directly finds none of those.

**The table of actions.** Both windows' keys, the Qt window's menus, Help →
Keys and `mcdonald mark --help` are made from `mcdonald/actions.py`. Against
each window: every row has a handler and there are no others; every key of
every row runs that row's handler and only that one (two `QAction`s given the
same shortcut silently cancel each other — the check fails naming both); the
other window's keys do nothing. For the Qt window, every row is in the menu the
table names, with its shortcuts and a line of help; and with Help → Keys in
front, the main window's keys still work, because it and the strips are tool
windows.

**Getting in with no terminal.** `mark_qt.open_session` is the way in for
`mcdonald-gui` and `mcdonald mark` alike, on a clip ffmpeg draws: the range
chooser says what a range costs and where, refuses one that will not fit, and
is a player that extracts nothing: the frame on its screen is compared with the
extracted frame of the same number after a jump, a step, ten steps back, playing
forward (timed against the clip's own speed), playing backward and playing the
chosen part, and the keys are sent by the route a real key takes; only the
chosen range is extracted; a long clip already on disk is asked about all the
same; the case
directory is shown, and not made until something is saved; a missing clip, a
file that is not a video and a failed save are dialogs in the command line's
words; File → Open marks takes a four-line file written by hand, refuses
junk, and questions marks made on another clip; File → Open a clip replaces the
window. The dialogs that would wait for a person are replaced by their
answers; what they lead to is not. `test_the_launcher` checks the gui-script is
declared, that it explains itself with no display rather than letting Qt abort,
and what `--desktop-entry` writes.

**The window proposes the object.** Track → Find the object on the synthetic
clip, which has two things that move: both are listed, the brighter first, each
row a strip with Show and This is it; Show draws the path and places nothing;
This is it places marks that are every one `proposed` and none a hand's, saying
what was proposed and who accepted, as one step to undo; the link starts and is
on the object to 0.1 px by the package's own detector; and a click afterwards is
still a hand's. `test_reduction` pins the report's sentence for such marks, and
`test_cli` that `look --propose` lists the same thing with the command that
takes it, and exits 5 where nothing moves.

**Plain words.** What the window says is written for someone outside the
field, and text drifts back toward the trade's words one tooltip at a time. So
`drive_plain_words` reads the words off the live widgets — the menus and their
lines of help, every label, tip, placeholder and title, both Help pages, the
Find and Measure panels; most of it is made at run time, and a search of the
source finds half — and looks for the trade's: clip, detector, candidate, px,
fps, DN, extract, static masks, velocity, polarity, provisional, case report.
The text it replaced had 95 of them. Two things are let through on purpose: the
report's own headings, which Getting started quotes so that they can be found,
and a mark's record (`how`), which is the files' wording. It also checks that
the four words the window keeps — frame, mark, track, link — are said before
they are used. It needs no word list from outside the repository.

**The measurements, from the window.** Measure → Measure this video is
`stages.run_case`, which `mcdonald run` is a command line over, behind a form.
On `test_cli`'s planted video: the form has a field for every row of
`stages.KNOWN` and `mcdonald run --help` an option for each, in the same words;
a field that is not a number is refused in a dialog; the track sheet is made and
shown, laid out for a screen, and nothing is measured from the track until the
question under it is answered; closing it unanswered is a no, and the report
says provisional; the panel offers the frames round the track where that is
fewer than everything open, and measures the ones it said; each long step says
which stage it is and counts, and the bar counts with it, runs busy where a
step cannot count, and stands still while it is the person's turn; Stop during
`layers` ends it at the next frame pair and the report says that stage was
stopped; the report is shown, not left on a disk. Then `mcdonald run` is run on
the files the window saved, and every stage's fields and the bottom line must
be the same, to the last digit. Help → Getting started is checked to name its
keys from the table.

The clip is synthetic — a compact source on a known path — so two clicks must
give back the velocity it was built with, to 1e-6 px/frame. It also has one red
pixel, which pins the half-pixel convention against the *rendered* window: the
red block on screen has to be centred on the pixel's integer coordinates, in
both toolkits. Qt's scene would otherwise put it half a pixel out.

The Qt window has a section of its own: the timeline, playback against the
clock at 1× and ¼× with every frame accounted for as shown or skipped,
read-ahead, undo and redo, the detector finding the planted source to half a
pixel *without marking anything*, the overview, and the unsaved-marks question
on closing. And the link: `l` chooses the detector from the marks (the controls
are set wrong on purpose first), links every frame onto the planted source,
back from the first mark as well as on from the last, draws it, shows the strip,
says when a moved mark has made it stale, costs nothing the second time, stops
on a second `l`, links a second object alongside the first, draws a disputed
frame as one, and saves `_autotrack.csv` files that say how they were made.
Then the fine work: shift+click snaps to the detector's centroid and the mark
owns up to it, ctrl+arrows nudge and undo as one step, a dozen scrub requests
decode one frame, and extraction runs behind a bar that can be cancelled.

Each window runs in its own subprocess under two deadlines. A toolkit that
hangs *before* a window opens is the environment's problem and is skipped with
the reason; a hang *after* is ours, and fails — from outside, that is what a
modal dialog looks like. Where `Xvfb` exists the windows are hosted off screen,
so the suite runs the same on a laptop and on a host with no display.

`TkAgg` needs both `tkinter` and `PIL.ImageTk`, which some distributions package
separately (Fedora: `python3-tkinter` and `python3-pillow-tk`). It is the
default backend on Windows and macOS, so a skip there is worth closing before a
release.
