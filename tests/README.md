# tests

Seven suites, answering six different questions.

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

## `test_audio.py` — does the sound track still say what it records?

Portable, under a minute. `mcdonald audio` reads a sound track the way an accident investigator reads a cockpit
recording. Its 24 checks plant what is known and ask for it back: a four-bladed propeller at 67.75 Hz with the T56's
second tone at 8.13x (PR117's case), a six-bladed one heard as a single line and read as the C-130J only with its
second tone, the codec's frame products named as the codec and never as a propeller, the mains and the 400-Hz bus as
clocks, a series that wanders called neither. The false-alarm check: twenty records of noise alone give no tone at all.
And the command end to end, on a drawn clip with a propeller's sound and one whose sound is silence (NO POWER, exit 5).
The real sound tracks are in `test_golden.py` (`test_audio_cases`).

## `test_stabilize.py`, `test_aspect.py`, `test_waves.py` — the three stages merged on 2026-10-19

Portable, each made of clips or seas drawn here, with the answer known by construction (merged from their branches;
the method is `docs/method.md` §14-16):

- **`test_stabilize.py`**: a small display filmed through a known homography per frame. The display has a reticle and
  a ring, the detector's fixed pattern and fresh grain; the hand wanders, rolls, changes distance and keystones, and
  a frame is now and then repeated. The stage's answer, carried back through the truth, must be one fixed map for
  every frame. Then: a held track is carried back onto the clip; a native recording is left alone; black inside the
  picture is drawing, and a pillarbox is not.
- **`test_aspect.py`**: a dark blob looping on a grainy field. With a steady brightness it must not be called; with
  its brightness following its heading by 25 % it must be. A track that never turns, and a clean circle, must say
  they have no power.
- **`test_waves.py`**: synthetic seas. A wind sea at a known scale must come back within a quarter, on one second
  (the stepped-phase fit) and on four seconds seen obliquely (the shell, along the waves). A narrow swell, and the same
  frames shuffled in time, must be refused. About 4 minutes on two CPUs.

```bash
python3 tests/test_stabilize.py; python3 tests/test_aspect.py; python3 tests/test_waves.py
```

## `test_slew.py` — does a slew give k cos(depression), and say when it cannot? (merged 2026-10-20)

Portable, seconds; synthetic series only (the method is `docs/method.md` §17). A camera holds the ground while the
pointer turns at a steady rate, then slews: c must come back within 2 %, with the hold rate and the elevation's tilt;
a pointer on a 0.45-deg grid within 6 % at every phase of the grid, the forward fit pulled low and the reverse not; a
slew under the grid step, a pointer blind to the slew and no slew at all give no k (a floor or nothing); a gap too long
to bridge is two stretches, one at the slew's start is bridged. The rendered end-to-end check is a tool, not a suite:
`tools/slew_selftest.py` (a video through `symbology`, `layers` and `slew`, about 4 minutes on four CPUs), and the
real-footage known answer is `tools/slew_ptz_check.py` (a broadcast camera with per-frame pan/tilt/focal; needs the
reference data's `ptzslam_soccer/`).

Since 2026-10-20 it also holds the zoom states (`docs/method.md` §17, "Zoom states"): a clip whose field halves at a
burst of blank frames, a slew either side. The automatic windows fall one in each state, c comes back in each (500 and
1000), and their ratio is checked against the imagery's x2; given as x1.5 the check fails and the stage says so;
across an unknown burst the states are on different chains and nothing is compared; a floor from a pointer blind to
the second slew does not refuse the first state's claim (taken as one field it does); a window given by hand across
the step is refused. And the rates: a pointer drawn a frame late is found at a lag of +1, and a pointer that only
curves slowly under a scene that moves on its own (PR076's case) correlates under 0.5.

```bash
python3 tests/test_slew.py
```

## `test_zoom.py` — does the zoom fit find a step across a blank, and say "unknown" where it cannot? (2026-10-20)

Portable, about 20 seconds; rendered scenes only. One textured ground seen at two magnifications, the later view
moved on by up to a fifth of the picture, under the MTS-B's overlay drawn in (a cyan reticle and glyph, black boxes,
white text), with and without a sensor's fixed pattern (a vignette ring and column stripes). x2 and x1/3 must come
back within 2 % and the narrower frame's middle where the view moved to; the same field either side must be "no step"
-- and "unknown" without a stretch to take the fixed pattern out. Each trap of `docs/handoff-zoom-slew.md` is a check:
a scene against a blank white frame and two blank frames under the overlay are "unknown", not x1; haze behind a fixed
pattern is "unknown" (with the pattern left in it fits x1 at a high ZNCC); x10 is past the grid and "unknown". The
bursts: three within half a second are one, the first settled frame waits for the gain, and a blank that keeps its
contrast (AARO's Puerto Rico switches) is found by its level. The real clips are `tools/zoom_check.py`.

```bash
python3 tests/test_zoom.py
```

## `test_camera.py` — the camera's zoom, its events, a track let go; a readout's ticks; a field-rate MPEG (2026-10-20, merged from `flir1` 2026-10-21)

Portable, seconds; synthetic scenes (the methods are `docs/method.md` §20-21). An MPEG-1 drawn at 30000/1001, whose
header gives the field rate, must read as 30000/1001 with a note, the same as a lossless copy that carries the rate. An
object drifting while the picture zooms x2 about a point near the middle: the step's frame, its ratio within 8 % and
its centre within 2 px, and the track in one scale at one rate either side; an object that only grows, one at the
zoom's centre, and a size step with a jump no zoom about the middle makes: no zoom, a zoom with no centre, and one not
confirmed. A rate that steps once: one breakpoint, to a frame, at an event a frame away and not at one fourteen away;
eight steady draws: none; 3000 frames: one, found by the pruned search. The released-track null both ways. A readout
drawn with ticks at known frames, one dithering: each to a frame, the rate within 3 %, and a hold cut before the next
tick was due. A track held at the boresight: held, not "not uniform". Since 2026-10-20 (night): a whole case drawn
and run with `--fields` and `--fov-px` (the camera's and the scale's k from them; a field of view given afterwards
moving the camera's degrees; `--fields` with `--fov` refused); a display's black border with a readout drawn right
under its top edge, inside the blocks the masks make, found and timed all the same, and a redaction box on a moving
scene that makes no box of text; letters from fixed text (`HELP`, and `CAFE` drawn with its glyphs touching, cut at
the pitch) and a readout's side read as one where the grammar puts a letter (37L, 38L, 39H). The real clip's checks are
FLIR1's in `test_golden.py`, and GIMBAL's and GOFAST's under `atflir`.

```bash
python3 tests/test_camera.py
```

## `test_tether.py` — does a hanging thing's swing still give its line?

Portable, seconds. `mcdonald tether` asks whether something is tied to the
object and swings; a pendulum's period read off the video gives its line in
metres with no range and no field of view (`docs/method.md` § 6). Its 24 checks
are built the same way as the two above, with the answer known by construction:
a period becomes the line it was made from; a planted companion is told from the
frame's edges and from the scene; the overlay's strokes are masked and a dark
line is not; repeated frames stay out of the series; and a window under two
cycles is said to be tentative. It runs with the suites here
(`tools/suites.sbatch`) and on the Mac and Windows runners.

```bash
python3 tests/test_tether.py
```

What it does to real clips is `test_golden.py`'s three tether cases (PR071's
steady string, nothing tied on PR055, the swing on WA9ONY-5) and the table in
`docs/tether-validation.md`.

## `test_golden.py` — do the real clips still give the published numbers?

Needs the video files, which are too large for the repository. They live in
the **reference-data folder**: `$MCDONALD_DATA`, or `data/mcdonald` beside the
repository when that is unset (`/models/data/mcdonald` on merlin). Its
`README.md` lists every file and where it came from; `tests/reference_data.py`
is the one place the tests and `tools/find_rank.py` look for it. A PURSUE clip
that is not there is looked for where the active catalog keeps it (the folder
`mcdonald` downloads into). A case whose video is nowhere skips, and says why.

```bash
python3 tests/test_golden.py             # ~5 min: a 200-frame window of PR144
python3 tests/test_golden.py --full      # tens of minutes: the whole clip, and the exercises
python3 tests/test_golden.py --exercises # the default run and the exercises (PR44, PR149, PR113: ~40 min more)
```

`--exercises` runs each page of `docs/exercises` as a tester would on the command
line: the page's `look` and `run` lines as written (with `--json`), and between
them the line `look` prints to take its first row, which must be the line the page
shows. The report must start as the page quotes it, word for word. The video is
placed in a storage folder of the test's own, so nothing is downloaded. Testers
check their own work against these pages, so a change that moves an answer fails
here, and the page changes with it. That every page is listed, offered in the
issue form and shows only real commands and options is `test_reduction`'s.

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

The flicker stage is held to its controls, both ways: the birds keep their beats
-- PR135's six on the paper's tracks as one flock, each within a quarter of a
hertz of the paper's (7.85, 7.38, 7.85, 7.11, 7.64, 7.60), and Galileo's five
flyers within half a hertz of the paper's (flyer 5 as 3.9 Hz with its double
7.8) -- and the things that are not birds have none: PR23 on the track the
window's one press followed (`golden/pr23_object_track.csv`; it crosses a hot
roof at frames 131-138, and was once "a bird" at 2.1 Hz), and the WA9ONY-5
balloon. The flyers' clips are in the reference-data folder's `galileo/`
(`MCDONALD_GALILEO` names another folder), the balloon's in `footage/`
(`MCDONALD_FOOTAGE`); their tracks, `galileo_clips.csv` and PR135's
`pr135_tracks.csv` are in `golden/`.

And two helicopters whose lights flash (`flicker`'s item 13, method §19).
Svanström V_HELICOPTER_054's white light is a train at 1.00 Hz in its
brightest pixels, and its dark body hides it from the aperture's sum.
V_HELICOPTER_030's red light is a train at 0.74 Hz in its reddest pixels.
Neither is shared by the background beside it. The clips are in the
reference-data folder's `svanstrom2021/`, their labelled tracks in `golden/`.

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
python3 tests/test_published.py --tracks DIR   # recorded tracks from another folder
```

The recorded tracks it reduces are vendored in `golden/`.

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

**More than one object** (`test_several_objects_are_a_case_each`, 2026-10-06): on a
second drawn video with two discs (`TwoPlanted`), each disc's marks in a folder of
its own and `run --each` on the folder above them: a case of each, in turn, into
its own folder; one page that lists them with each track sheet not yet looked
at; an object measured in the queue has the same fields, to the digit, as that
object measured alone with `run --marks` over the same frames; `report
--i-looked` on one case brings its line on the page up to date; a second `--each`
measures nothing again; `--each` with `--marks` is refused with exit 2, and a
folder with no object in it is exit 5 with what to put there. Since 2026-10-08,
`--objects 3` on the second run: the list's first line holds the count against
what was followed ("You looked for 3 objects: 2 were followed; 1 was not
found"), `report --index` remembers it, and `--objects` without `--each` is
refused with exit 2.

**Known afterwards** (`drive_known_afterwards`, 2026-10-09): on the case measured
from the agent's marks, `report --fov 30 --range 8046.72` works the speed out
again, and its scale and kinematics fields, its conclusion, and the report from
the conclusion through what is missing are those of `run` told the same from the
start, to the last digit; nothing else in the case changes, it keeps what it was
told (`known`), and the command is in Reproduce; `--forget range` takes the range
and the speed away and keeps the field of view; giving and forgetting one thing
at once, or `--diameter` (which changes more than the speed), is exit 2; and
`report --help` lists every option that can be given afterwards.

## `test_share.py` — does one file to send someone open where its sender left off?

Portable, needs ffmpeg and no video data (test_cli's drawn clip); 25 checks in about three
minutes. A shared file (`share.py`, 0.2.18) is held to what it promises: what goes in comes
out (the marks, each still saying who placed it, the tracks, every object's folder, the files
sent with it, the stretches to look at and the thread of notes, oldest first); the video is
named by its file's name, size and SHA-256 and found again, never carried, and a different
file of the same name is said to be different; opening never writes over anything and refuses
a name that would land outside its folder; an answer carries the thread on; an agent's file
made from tracks alone says it is an agent's; and `share make`, `share show` and `share open
--no-window` each work with `--json`. Since 2026-10-16 it also holds the comparison that
`tools/rerun_cases.py` makes between a case file's report and a fresh measurement of it:
the same numbers made another day, by another version, in another folder, differ in nothing;
a number that moved, a test that lost its NO POWER, or a path to a different file is a
difference, named by where. Since 2026-10-17 that comparison is the package's (`mcdonald.rerun`)
and an installed command, `mcdonald share rerun FILE`: a case measured on the drawn clip, shared,
reruns to its numbers with exit 0, and the same file with one number in its report changed
does not (exit 1, the difference named).

## `test_sweep.py` — does the beat sweep's pass still decide as it did?

Portable, Python and numpy only; 10 checks in a second. The parts of `tools/sweep/` (ROADMAP.md
0.3, objective 9: the whole-video beat pass as scripts anyone with the videos can run) that
decide something: the windows a video is cut into (PR073's eight, as the pass cut them); Find's
proposals made objects (one seen in two windows is one, a dark and a bright one never are); the
strict list (windows that come back apart at one frequency, or a whole track over its drift at
5 %); and the held-out third, drawn again from its seed and left out of the summary until the
gates are frozen.

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
front -- a page over the video, since 2026-10-07 -- the video's own keys are
off, and Esc brings the video and its keys back.

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
junk, and questions marks made on another clip; File → Open a video opens the
next video in the same window, in place. The dialogs that would wait for a
person are replaced by their answers; what they lead to is not.
`test_the_launcher` checks the gui-script is declared, that it explains itself
with no display rather than letting Qt abort, and what `--desktop-entry` writes.

**One window** (`drive_one_window`, 2026-10-07). The window opens with nothing
in it and the start screen as a small dialog over it, which put away leaves
the window empty and whose Quit is leaving; a video opens into it in place,
which part of it asked on a page of the window with the video's keys off, the
frames saved behind a bar on another page; a second video takes the first's
place, or leaves it when its page is cancelled; and through all of it the
window is the only window on the screen.

**One button** (`drive_one_button`). On the planted video the side panel opens
simple, with the one button and the three steps hidden; pressed, it finds the
object, takes the first row of Find's list (the marks say the run took them,
nobody looking), follows it onto the planted path and measures it asking
nothing, with nothing put under or said over the video on the way -- not the
list, not the track's check, not a note; the report opens on a page of the
window, its conclusion first, with the line that nobody has looked at the
track sheet; Advanced shows the three steps, step 2 with the track's pictures
behind "Check the track"; pressed again it measures again, and Stop stops it;
and on a part where nothing moves it stops with a sentence that points at
Advanced.

**What is known of the video** (`drive_what_is_known`, 2026-10-09). The segment
step asks, folded under the count until opened, in plain words and the units a
person thinks in (miles, feet, knots); a thing of known size without its length
on the screen is refused under the form, and that length is measured on the
player in the video's own pixels; what was given is remembered for the video in
meters. The one press takes it and asks nothing: the report has the field of
view, the range and a speed, and the Measure form shows them. The report card
says what the speed rests on, with Change; emptied and worked out again, the
speed goes and the card asks for what would give one, the video's memory and
the Measure form following; something that cannot be read is said in the card;
and "Work out the speed" with 3 kilometers is `mcdonald report CASE --range 3000`
on a copy of the same case, to the last digit.

**The window proposes the object.** Track → Find the object on the synthetic
clip, which has two things that move: both are listed, the brighter first, each
row a strip with Show and This is it; Show draws the path and places nothing;
This is it places marks that are every one `proposed` and none a hand's, saying
what was proposed and who accepted, as one step to undo; the link starts and is
on the object to 0.1 px by the package's own detector; and a click afterwards is
still a hand's. `test_reduction` pins the report's sentence for such marks, and
`test_cli` that `look --propose` lists the same thing with the command that
takes it, and exits 5 where nothing moves.

**A spot, or an edge or a stroke?** (`test_measurement`, with the proposer's
other checks.) Find put PR113's object eleventh, behind the edges of redaction
blocks, the rim of the picture and the strokes of a scrolling heading tape —
compact peaks in the residual, and none a compact thing in the frame.
`propose.all_round` is checked on drawn shapes whose answer is known: a disc is
1.00, an edge and a corner 0.00, a thin bar straight or slanted under 0.3, a
centroid a few pixels off still finds the disc, and the wrong polarity finds
nothing; and the score puts a spot seen in four frames before an edge seen in
nine, and leaves the edge on the list. What it does to real clips is not a unit
test: it is the table at the top of `docs/handoff-ui.md`, six clips with recorded
tracks, to be run again after any change to `propose.py`. `test_gui` checks that
the Find panel says how many more things it kept and shows them when asked, and
that a part too short to look in is said to be; `test_cli`, that `look --propose
--more` lists them and `--json` carries `background_all_round`.

**Marks the linker can use.** (`test_measurement`, the same function.) Find
"worked" on PR055 and the link from its marks found nothing: a disc slower than
its own width is a rim in the residual, so the marks were a radius off the
centre. `SlowDisc` is that situation drawn — 24 px across, 1.5 px a frame — and
the checks are that the residual's peaks are 12 px off while the proposal is
within 1.3, that it reports the thing's own width and calls it a spot, that the
link from its marks is on the disc at a fitting spot size, and that marks on
the rim get nothing or a small spot riding the rim; `thing_at`, asked at the rim
of discs 8 to 72 px across, answers with the centre and the width. Then the
three ways a proposal's track was found to go wrong on real clips, each from
hand-made points: a point where the thing has faded is left out (PR055, into a
dark gap between clouds); a later piece is joined on only if it is like the
thing (the gap itself, 104 px, was); what runs *beside* a thing lends it no
frames (PR142's faint copy, 20 px behind); a long track that winds keeps its
points, and a stray one goes without taking its neighbours. The linker, for its
part, now says *which* mark has no spot near it and what to do. And pools are
no larger than the CPUs the process may use (`progress.cpus`): in a two-CPU
Slurm job a pool asked for six has two. What all this does to real clips is
`tools/find_rank.py --link` — the place of the recorded object on the list and
the link from its marks, for every clip with a recorded track — which is a
benchmark, not a test, because the tracks are not in the repository.

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

**More than one object, from the window** (`drive_several`, 2026-10-06): on the
two-disc video, Find lists both; each row has a tick, a tick brings up the one
button under the list and outlives the list being drawn again; the button puts
Find away and opens the list of objects, each a folder with its marks saved as
proposed, and the window's own marks untouched; Stop ends the step under way,
leaves the next object as it is, and offers the rest; "Measure the rest" takes
both to the end, the rows say how far each was followed, the step cards say how
the objects stand; an object measured from the window's list has the same
fields as `mcdonald run --marks` on its folder; the page lists them; a report
opens with the banner that nobody has looked at its track sheet, and pressing
it is said in the report, in the row and on the page; "Open in the window"
brings an object's marks in, moves the folder the window saves to, and follows
that object there; and what the list and the ticks say is in plain words.

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

## `golden/` — what is vendored, and from where

Every table a test or `tools/find_rank.py` reads is here, so nothing outside the
repository is needed except the footage (above). The tracks were recorded in the
PURSUE case analyses and are frozen copies; change one only with a reason in the
commit message.

| File | What | Read by |
|---|---|---|
| `pr113_transit_curated.csv`, `pr113_transit.csv` | PR113 transit: the four curated positions; the raw detections | golden, published, find_rank |
| `pr144_track.csv` | PR144 object track with per-layer background shifts (the layers run) | golden, published, find_rank |
| `pr144_north.csv` | PR144 north-pointer angle per frame | published |
| `pr149_transit.csv`, `pr142_transit.csv`, `pr148_transit.csv` | the R05/R06 transits | published, find_rank |
| `pr055_track.csv`, `pr055_sphere_track.csv` | PR055 sphere track (whole clip; the tether window) | find_rank, golden |
| `pr071_object_track.csv`, `pr23_object_track.csv`, `wa9ony5_balloon_track.csv` | tether and no-beat cases | golden |
| `pr135_tracks.csv` | the PR135 paper's tracks of the six birds A–F | golden |
| `flyer1_paper_track.csv` … `flyer5_paper_track.csv`, `galileo_clips.csv` | the paper's Galileo flyer tracks and clip table (Zenodo DOI 10.5281/zenodo.23021686) | golden, find_rank |
| `svanstrom_v054_track.csv`, `svanstrom_v030_track.csv` | Svanström et al. 2021 visible helicopters V_HELICOPTER_054 and _030, their labelled boxes (the uap repository's `heli_lights.py tracks`) | golden (`flicker` item 13: their lights' trains) |

