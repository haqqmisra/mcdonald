# McDonald UAP Toolkit: the technical README

**For AI agents and technical users**: every command, how each step works, what the tests hold it to,
and why. For installing it and using the window, [README.md](README.md) is shorter.

Measurement tools for single-sensor video of unidentified objects.

Point it at a clip and it will tell you how the background moves and in how many
layers, whether the clip behaves like the output of one sensor chain, whether
the object in it behaves like imagery or like something laid over imagery, and
whether your track is actually on the object in every frame.

It will also, frequently, tell you that a question cannot be answered from the
clip you have. That is the intended behaviour, not a shortfall. Most released
sensor video does not contain enough information to state a speed, and a tool
that always returns a number is worse than useless on this subject.

> Named for James E. McDonald, who argued that the subject deserved ordinary
> scientific instruments rather than either credulity or dismissal.

**Status: alpha (0.2.14).** The full pipeline: eight stages from a file to a
case report, plus each stage as its own command. See [Roadmap](#roadmap) for
what is still missing.

---

## Install

Three steps, the same on macOS, Windows and Linux ([docs/install.md](docs/install.md) goes
through each one slowly, for each system):

1. **ffmpeg**, which mcdonald reads video with: `brew install ffmpeg` (macOS),
   `winget install Gyan.FFmpeg` (Windows), `sudo dnf install ffmpeg` or `sudo apt install ffmpeg` (Linux).
2. **mcdonald**, with its window (Python 3.10 or newer):

   ```bash
   python3 -m pip install mcdonald
   ```

3. **Check this computer**, which also says what to type next:

   ```bash
   mcdonald setup
   ```

Then `mcdonald-gui` opens the window, and `mcdonald run PR149` does the whole job on the
command line (downloading PR149 the first time).

**Updates.** A copy installed this way asks PyPI, at most once a day, what the newest version
is (one small request; no account). If it is newer, the window asks whether to update: on a yes
it closes, pip installs the new version, and it opens again. The command line never stops to
ask; it prints one line on stderr (stdout stays JSON) with the pip command. A copy installed
from GitHub (`pip install "mcdonald[gui] @ git+https://github.com/haqqmisra/mcdonald"`, as
before 0.2.4) asks GitHub's main instead and updates from there; a working copy
(`pip install -e`) is never checked, and `MCDONALD_NO_UPDATE_CHECK=1` turns it off
(`mcdonald.update`).

### What it needs, and how long it takes

- **Python 3.10 or newer, and ffmpeg**, on macOS, Windows or Linux. The window needs a desktop;
  the command line does not.
- **Disk**: each frame worked on is saved once, losslessly: about 0.75 MB a frame at 1920×1080,
  so a 3-second segment is ~70 MB and a whole 3-minute video ~4 GB. Downloaded PURSUE videos are
  2 MB to 3 GB (most under 100 MB). Both go in one folder you choose on the first screen.
- **Memory**: 8 GB is enough for a segment of a few hundred frames; more for whole videos.
- **Time.** mcdonald compares frames pixel by pixel, and some steps are slow. On the machine it
  was built on (a 2012 six-core Xeon workstation, 2 GHz, 32 GB), for a 1080p segment:

  | step | about |
  |---|---|
  | saving the frames (once) | a few seconds per 100 frames |
  | Find the object | 15 s + 0.2 s a frame (a 3-second segment: under a minute) |
  | Follow it | about ten seconds |
  | Measure, without the two slow checks | under a minute |
  | Measure: the *layers* check | about 1.4 s per pair of frames (3 s: ~2 minutes) |
  | Measure: the *integrity* check | about 1.5 s per pair of frames + 30 s (3 s: ~3 minutes) |

  On four CPUs (a laptop) count on about twice these: a 2-second segment of PR113 measured with
  every check took 8 minutes there.

  So **open only the part of the video with the object in it**, plus a second or two either side:
  the window asks which part, and says what it will cost before it starts. A whole 3-minute video
  measured with every check is hours. Each step shows its progress, and can be stopped.

### Working on the code

```bash
git clone https://github.com/haqqmisra/mcdonald.git
cd mcdonald
python3 -m pip install -e .
```

Verify the install measures correctly before you trust a number from it:

```bash
python3 tests/test_measurement.py    # measurement: masks, registration, layers, detection
python3 tests/test_reduction.py      # reduction: symbology, kinematics, scale, marks, report
python3 tests/test_published.py      # every number in the Technical Note and the PR144 notes
python3 tests/test_tether.py         # tether: a hanging thing's swing, its period, its line
```

Together those are the checks against cases whose answers are known by
construction — a known rigid shift, two backgrounds moving at different rates,
planted repeated frames, an object on a known path, the published PR113
reduction, the PR149 scale-bar bound — confirming the library recovers each
one. They need no video data, take a few minutes, and each should end
`ALL PASS`.

`test_published.py` adds 32 more, walking the Technical Note's and the PR144
notes' quantitative claims one at a time, so a change that would move a number
in a manuscript fails here first. `tests/test_golden.py` goes further and
re-measures real clips, but needs the video files; it skips cleanly and says
so when they are absent.

`python3 tests/test_gui.py` presses every key and button of both `mcdonald mark`
windows — the Qt one, and the matplotlib one under each interactive backend the
machine can open — runs the same checks against each, and compares the files
they save. It skips what cannot open here and says why, which also makes it the
quickest way to find out whether `mcdonald mark` will open a window at all.

## Use

Everything at once, into one report:

```bash
mcdonald run CLIP.mp4 --track track.csv
mcdonald run CLIP.mp4 --marks CLIP/clip_marks.json    # or from two clicks: the track is linked first
mcdonald run CLIP.mp4 --each CLIP/                    # more than one object: a case for each, in turn (below)
```

That walks the clip through ingest → survey → track → **verify** → layers →
scale → kinematics → integrity → report, and writes `<tag>_case.md` and
`.json`. A stage that has nothing to work with says so and the run continues;
nothing is silently skipped. Each stage is the function the stage's own command
calls (`mcdonald.stages`), so a number in the case report is the number
`mcdonald layers` or `mcdonald kinematics` would give. With a track, the layers
stage is the whole measurement — the object against each background layer, about
a second per frame pair — and `--skip layers,integrity` is the quick run.

Or one question at a time:

```bash
# How does the background move -- and is it one background?
mcdonald layers CLIP.mp4 --auto-track --validate

# Has the clip been altered? Was the object added?
mcdonald integrity CLIP.mp4 --track track.csv

# Is my track on the object in every frame?
mcdonald tracksheet CLIP.mp4 --track track.csv

# Find the object and click it on a couple of frames (opens a window)
mcdonald mark CLIP.mp4                      # the whole clip
mcdonald mark CLIP.mp4 --n0 400 --n1 420    # or a window of it

# ...and hand those clicks to the pipeline: the track is linked from them
mcdonald layers CLIP.mp4 --marks CLIP/clip_marks.json

# The same with no window, for something that cannot click: see the clip, then say where
mcdonald look CLIP.mp4 --n0 1 --n1 120 --propose          # what moves against the background, best first, as strips
mcdonald look CLIP.mp4                                    # an overview sheet; --n0/--n1 narrow it
mcdonald look CLIP.mp4 --frame 408 --size 21 --dark       # a frame's candidates, ringed, numbered, enlarged
mcdonald mark CLIP.mp4 --n0 400 --n1 420 --no-window --link \
    --set object@408=1010.9,313.0 --set object@411=702.4,604.2 --why "candidate 1 of 6 at 21 px dark; the one that moves"

# Boresight, north pointer, corner brackets -- the overlay's own readings
mcdonald symbology CLIP.mp4

# v_px -> omega -> what the motion permits (with --ladder when k is unknown)
mcdonald kinematics CLIP.mp4 --track track.csv --ladder

# Does the object move WITH the texture around it, or THROUGH it?
mcdonald comotion CLIP.mp4 --track track.csv --diameter 72

# Is something tied to the object -- a line, a payload -- and does it swing? (T -> metres of line)
mcdonald tether CLIP.mp4 --track track.csv
```

`CLIP` is a path to any video file. Results go to a **case directory** —
`--out DIR`, otherwise `./<name>/` under your working directory. Nothing is ever
written next to the installed code.

**Two ways in, and each does the whole job.** A person with no terminal starts
`mcdonald-gui` (below), marks and links the object, and measures it from the
window's Measure menu, which is `mcdonald run` with a form in place of the
options. An agent with no display uses `look` and `mark --set`: `docs/agents.md`
is PR113 done start to finish that way, to 141.4 px/frame against the published
142. A mark placed with `--set` is recorded
as an agent's, with its `--why`, never counts as a hand mark, and a case report
built on it says so above its bottom line — which thing is the object is a
judgment, and the files say who made it.

Every command takes `--json`: one object alone on stdout — `command`, `inputs`,
`clip`, `files`, `results`, `no_power`, `needs`, `notes`, `exit`, `error` — and
everything meant for a person on stderr. Every command has its results as
fields — numbers with the unit in the name, never a sentence to parse — and what
it printed for a person beside them as `results.said`, written *from* those
fields. Each measuring command is a command line over one function, and `run`
calls the same ones (`mcdonald.stages`), so a number in a case report is the
number the stage's own command gives: `tests/test_cli.py` holds them equal to
the last digit, and `tests/test_gui.py` does the same for the window. Exit
codes tell an expected failure from a bug: 0 done, 1 a traceback (a bug), 2 the
command line was wrong, 3 the machine lacks ffmpeg or a window, 4 the input is
not there or is not a video, 5 nothing to work on (no marks; the link acquired
nothing). `mcdonald --help` lists them.

A track CSV needs a frame column (`frame`, `n` or `frame_n`) and an x/y column
pair in video pixels (`x_px,y_px` or `x,y`). `--auto-track` will attempt one for
you, but **look at the track sheet before building anything on it**: on the clip
this toolkit was developed against, the first automatic tracker spent seven
frames locked to a cloud feature 100 px from the object.

Long clips: `--n0/--n1` take a frame window and keep the absolute numbering.
Frames are extracted losslessly and are ~2 MB each, so point `--workdir`
somewhere with room if `/tmp` is small or a tmpfs.

### Marking the object

Nothing here can decide which thing in the frame is the object, and it does
not pretend to. `mcdonald mark` opens a window on the extracted frames; two
clicks give the linker its seed and the velocity it cannot acquire on its own,
after which the automatic track covers the rest. It writes a marks JSON, a
track CSV the other commands read, and a magnified contact strip with the
marks drawn back onto the pixels — which is how a coordinate gets checked
rather than trusted.

On DOW-UAP-PR113 that is the entire human input: two clicks reproduce the
published 142 px/frame.

There are two windows over the same marks, and `--gui auto` (the default) takes
the first that will open.

- **The Qt window** (`pip install -e .`) is for the clip you have not
  seen. A timeline over the whole clip, playback at true speed — it holds
  30 frames/s on lossless 1080p, skipping frames rather than stretching time if
  it ever cannot, and saying how many — an overview of the clip as tiles (`o`),
  the detector's candidates drawn on the frame (`c`), a loupe under the cursor,
  and undo. The candidates are there to be looked at, not trusted: on PR148 the
  detector ranks the reticle's corner marks alongside the ship.

  Then **`l` links**: an automatic track through the marks, drawn over the clip
  as it grows, with the linked frames shown on the timeline and the track strip
  put in front of you at the end. The detector's scale and polarity are chosen
  from the marks. Every mark is a seed: between two marks the track is linked
  forward from one and backward from the other, and a frame where the two
  disagree is drawn amber rather than settled quietly; before the first mark
  and after the last it runs until the object is lost, and stops there rather
  than starting again on the brightest thing in the frame. So after a loss,
  mark the object where it reappears and press `l` again — the detector's work
  is kept, and only new frames are computed. `object` and `object #2` are
  linked together. `s` then also writes `<tag>_autotrack.csv`, which the other
  commands take as `--track`. On PR113 the two documented clicks choose 21 px
  dark, link frames 408–411 onto the vendored positions to 0.005 px, and give
  back 141.4 px/frame against the published 142 — in the window, in about a
  minute. The same step without a window is `mcdonald.autolink`, and
  `layers`, `integrity` and `run` take a marks file directly as `--marks`:
  from the command line that is the only way to track an object too fast for
  `--auto-track`, which links 1 of PR113's frames where `--marks` links all 4.

  For placing a mark finely: `ctrl`+arrows nudge it a pixel (`ctrl+shift`, a
  tenth), and `shift`+click snaps it to the detector's nearest candidate. A
  snapped mark says so, in the window, the JSON, the CSV and the contact strip:
  it agrees with the detector because it *is* the detector's, so it must never
  be mistaken for an independent hand mark.

  A clip it has not seen is extracted first, behind a progress bar with a
  Cancel on it. Where `--n0/--n1` do not say which part, it asks, and what it
  asks with is a player: play the clip forward or backward at its true speed or
  slower, step a frame or ten, drag the bar, press "Start here" and "End here"
  at the frame on the screen, and read what that part will cost before anything
  is extracted. Nothing is extracted to watch it: the frames come from an ffmpeg
  pipe (`mcdonald/reel.py`) under the numbers extraction will give them. A long
  clip is asked about even when it is all on disk already, because opening the
  whole of it costs nothing and measuring the whole of it costs hours.

  **It can look first.** Track → Find the object (`f`; `mcdonald look --propose`
  from a command line) looks for what moves against the background — a double
  difference on the registered background, compact residual peaks, chains at
  constant velocity, marked down where several things go the same way at once,
  which is a layer or a scale that scrolls, and where the frame itself shows an
  edge or a stroke and not a spot with background all round it — and lists what
  it finds, best first, each as a strip of the clip's own pixels. It shows the
  best few and says how many more it kept (`--more`). "This is it" places marks
  along one and links from them; a click is then the correction rather than the
  first step. It proposes and does not decide: no detector can say which thing
  is the object, so a mark taken from a proposal is recorded as `proposed`,
  never counts as a hand mark, and a report built on it says the suggestion was
  the detector's and the yes a person's. Against every clip with a recorded
  track: on PR149 the contact is the one strong proposal (0.4 px from the hand
  workup; taken and linked, 20.1 px/frame for the published 20.2); on PR144,
  where the sensor follows the object and only the background moves, on PR142
  and on PR148, likewise, the second row scoring a fiftieth of the first; on
  PR113, a four-frame transit past a scrolling heading tape under a pan, it is
  first by a narrow margin, and weak — it was sixth to eleventh until the frame
  was asked whether each thing is a spot — and taken, links to the vendored
  track exactly; on PR055 at its true size, a black disc 24 px across that
  moves 1.5 px a frame, it is first and strong, and its marks are on the disc's
  centre and not on its rim, because a proposal's positions are the thing's
  own (`propose.thing_at`) and not the residual's — the ×3 copy of the same
  scene, a 72 px disc, still cancels in the double difference and is not on the
  list. Where the scene holds still, or nearly, each frame is also compared with
  the frames half a second either side (`propose.still_peaks`, 2026-09-29): a
  thing that crawls at a quarter of a pixel a frame -- a bird far off at 60
  frames a second -- has not moved its own width in the four frames the double
  difference spans, and leaves nothing in it but the odd flap; by half a second
  it has moved clear of itself. On Galileo flyer 1 (a still sky, 60 fps, four
  things in it) Find listed the paper's bird only as two three-frame fragments
  scored nothing, and a second bird along the top edge not at all; now the
  paper's bird is first and strong for its whole 18 s (1.3 px from the paper's
  track), a spot crossing at 4 px a frame second, the edge bird third and fair,
  and a streak that crosses the frame in eight frames fourth, weak, behind
  "Show more". A proposal's marks are for the linker: `tools/find_rank.py --link`
  holds Find and the link from its marks against every clip with a recorded
  track (the two Galileo flyers among them), and is what to run after any
  change. About 0.2 s a frame, twice that where the scene holds still, shown as
  it goes.

  **With no terminal.** `mcdonald-gui` starts the same window the other way
  round: it opens on its home page -- what this is, the two ways to name a
  clip (a file, or a catalog id: a PURSUE video not on the computer yet is
  downloaded, after asking), the videos opened last, where the data goes --
  asks which part, keeps its cases in the storage folder
  (`Documents/mcdonald/<tag>` until changed on the home page) and shows where,
  and says what goes wrong in a dialog instead of printing it. It is one window (2026-10-07): which part of the video to open,
  the wait for its frames, the report, the overview, the strip after a save and
  the Help pages are pages inside it, over the video, with a way back
  (`mark_qt.Page`), and the track sheet's question is a panel under the video;
  the video's own keys are off while a page is in front. Only the desktop's file
  dialogs, the alerts and About are windows of their own. The side panel opens
  simple: one button, **Find, follow and measure the object** (`a`;
  `auto_qt.AutoRun`), which presses the three steps in turn with nothing asked
  and nothing popping up -- the first row of Find's list taken as the object,
  or every row at least fair when there are several (then a queue of cases,
  `several.run_each`, a folder and a report each; the list is not shown: it
  would look like a choice to make), or, where the person said on the segment
  step how many objects they are looking for, that many of the likeliest rows
  (the queue then holds the count against what was followed, and splits a
  group of points into its members where fewer were found), the marks recorded as the run's, the
  track's check not put under the video, no note over it, the report saying its
  numbers are not yet sure until someone looks at the sheet and says so -- and
  stops with a sentence where a step gives it nothing to go on. Three lights under the button -- Find,
  Follow, Measure -- are lit as each is done, and once the button has been
  pressed the Advanced line under it is gone for that video (View → Advanced
  remains). What the person knows of the video that its pixels cannot say --
  how wide the camera sees, how far away the object is, a thing of known size in
  the picture (its length on the screen measured on the player), the speeds a
  report gave -- is asked on the segment step too, folded under the count, in the
  units they think in (`known_qt.KnownForm`; remembered for the video, and what
  the Measure form's fields show, so the one press and the queue use it). Where
  a report could not give a real speed, its card asks for the same things ("Add
  what you know") and "Work out the speed" is `stages.add_known` -- what `report
  CASE --fov ...` does, below -- and where it could, the card says what the speed
  rests on, with "Change". What it found and the pictures along its track wait behind
  Advanced's "Show what Find found" and "Check the track". The wait while a
  video's frames are saved, or a video downloads, is a card at the top of the
  right column (`mark_qt.BusyCard`), not a dialog. **Advanced** (View → Advanced, or the
  line under the button; remembered) shows the three steps, find, follow and
  measure, as buttons of their own, and marking by hand. Everything a flag does is in the
  File menu — Open a video, Open by catalog name, Open marks (`--load`), Save to
  a different folder (`--out`) — and every key is in the menus and under Help →
  Keys and mouse, which are made from one table (`mcdonald/actions.py`) together
  with `mcdonald mark --help`. What the window says is written in plain words,
  for someone outside the field: a video, not a clip; a spot the computer found,
  not a detector's candidate; "frame", "mark", "track" and "link" are the four
  words of the trade it keeps, and Help → Getting started says what each means
  first. (The case report and the lines each stage prints are the measurement's
  own words, and are not part of that yet.) **Measure → Measure this video** is the rest of the
  job: it saves the marks and the link, asks what you know that the pixels cannot
  say (the form is made from the rows `mcdonald run`'s options are made from),
  says what the slow stages will cost, and makes the case on a thread of its own.
  While it runs there is a bar that counts where the step can count (frame
  pairs, tiles) and runs to and fro where it cannot, the stage it is on, the time
  gone and the time left in the step, and a Stop that ends the step under way;
  and it measures the frames round the track unless asked for everything that is
  open, because someone who opened a whole clip to find a four-frame transit has
  hours of frames open. (The command line says the same on stderr.)
  The track sheet is put under the video first, with the question every number
  after it depends on — is the circle on the object in every frame? — and
  closing it unanswered is a no, which the report records as provisional. The
  report then appears as a card in the right column under the one button, the
  video still in sight (`report_qt.ReportCard`; one card per object after a
  queue of several): a badge and the label of its
  conclusion (`report.Case.conclusion`: tentative, none, or firm, in one
  sentence -- a beat at a wingbeat's rate makes a bird the leading explanation),
  the numbers found as label-and-value rows, "More" for the bottom line's
  paragraph and what is missing, "I looked" when the track sheet has not been
  checked by eye, and "Full report", the whole report as a page over the video
  (`measure_qt.show_report`); Measure → Open the case folder finds the files. `mcdonald setup` (or `mcdonald-gui --desktop-entry`)
  adds it to the applications menu on Linux. It needs the `gui` extra
  installed once. On macOS every suite passes on GitHub's runner
  (`.github/workflows/platforms.yml`, run by hand or by `git push -f origin HEAD:macos-ci`);
  it has not yet been run on Windows.
- **The matplotlib window** (`--gui mpl`) needs nothing beyond what the package
  already depends on. It steps at about 11 frames/s on 1080p, which is ample
  when you already know which frames to look at.

Both keep every mark in the same `MarkSet`, save through the same function, and
are held to the same checks by `tests/test_gui.py`. In both, a frame is a
lossless PNG named by its frame number; there is no video element to disagree
with ffmpeg about which frame is on screen, playback included.

### More than one object in a video

A case is one video, one object, and one report whose bottom line is about that object; every
measuring step takes one track. A video with several things in it -- Galileo flyer 1 has two
birds, a streak and a spot -- is several cases, each in a folder of its own:

```bash
mcdonald mark CLIP.mp4 --no-window --set object@813=116,70 --set object@911=137,101 --why "…" --out CLIP/object-1
mcdonald mark CLIP.mp4 --no-window --set object@1658=307,71 --set object@1703=379,231 --why "…" --out CLIP/object-2
mcdonald run CLIP.mp4 --each CLIP/          # every object-N under it: linked, measured over the frames it is in
mcdonald run CLIP.mp4 --each CLIP/ --objects 6   # looking for six: the list says how many were followed, and a group's members become objects
mcdonald report CLIP/object-1/clip_case.json --i-looked     # once its track sheet has been looked at
mcdonald report CLIP/object-1/clip_case.json --fov 2.5 --range 9000   # known afterwards: the speed worked out again
mcdonald report CLIP/ --index               # the list again, from the folders
```

`run --each` (`several.run_each`) makes a case of each `object-N` folder in turn -- `stages.run_case`
over the frames its marks are on and two seconds either side, so an object measured this way is the
object measured alone with `run --marks … --n0 … --n1 …`, to the digit -- and writes
`CLIP/<tag>_objects.md` and `.json`: what each was chosen as, how far it was followed, its report's
bottom line, and whether its track sheet has been looked at. Nobody is asked about a sheet while the
queue runs, so every report is provisional until `report … --i-looked` says otherwise, which brings
the list up to date too. One that has a report from the same marks is not measured again (`--again`
does). With `--objects N` -- how many the person is looking for -- the list's first line holds the
count against what was followed ("You looked for 6 objects: 6 were followed, 6 of them the members of
2 groups (objects 1, 2)"), and where fewer things were found than N and one of them is a group of
points (`groups`: several, members followed), its members seen on 60 frames or more become objects of
their own, measured after the rest (`several.split_group`): each a folder with the member's positions
as its track (written, not linked again, so it cannot wander to the bird beside it), marks every ten
frames for the record, and `<tag>_group.json` naming the group; the member's case skips the groups
stage, takes its flicker stage from the group's (`flicker.of_member`: measured with its fellows, the
beat its own where it is out of step with one of them -- alone, three of PR135's six birds are vetoed
by the codec's line or the bird beside them), and the tether stage names a fellow member found moving
with it rather than calling it something tied to the object. The group's own case stays, its report
the flock's. The background step is measured for each object on its own: its templates are made with the
object's track in hand.

In the window it is the same function. Each row of Find's list has a tick, "one of several"; with
rows ticked, "Follow and measure the ticked ones" under the list gives each a folder with its marks
(recorded as proposed, as "This is it" records them) and follows and measures them in turn
(`several_qt.SeveralPanel`): a row for each object with how it stands, Stop, "Measure the rest",
each report with the banner that says its track sheet has not been looked at, the list as a page,
and "Open in the window" for the object whose track needs a hand. Measure's form -- what is known
of the video, which slow checks to make -- is used for every one of them. The window's own marks
are not touched: an object in the list is a folder.

### The gate

`run` makes a track sheet — every frame tiled with the tracked object circled —
and treats looking at it as a prerequisite, not an option. Without
`--i-looked`, every object measurement in the report is stamped
**provisional**. There is no flag that skips making the sheet.

This is not ceremony. On the clip this toolkit was developed against, the first
automatic tracker spent seven frames locked to a cloud feature 100 px from the
object and produced a clean, plausible, wrong rate. The sheet is how that is
caught, and it takes about ten seconds to look at.

### What is known afterwards

A field of view, a range or a thing of known size learned after a case was
measured changes only the arithmetic from the track's rate in pixels to a speed,
so the case need not be measured again:

```bash
mcdonald report CASE.json --fov 2.5 --range 9000      # the speed worked out again with them
mcdonald report CASE.json --ref-px 228 --ref-m 18     # a thing of known size: no FOV, no range needed
mcdonald report CASE.json --forget range              # that range was wrong
```

`report` takes `run`'s options that change nothing but that arithmetic (`--fov`,
`--graticule`, `--range`, `--ref-px`, `--ref-m`, `--range-ratio`, `--size-px`,
`--ground-speed`, `--own-ship`; `stages.AFTER`): the scale and kinematics steps
are done again from the case's track, on the frames it was measured on
(`--workdir`), with what the case already knew and these over it, the figures
drawn again, and nothing else touched. The numbers are the ones `run` gives when
it is told the same from the start (test_cli holds the two to the last digit).
A case keeps what it was told in its ingest step's `known`; the rest of `run`'s
options change what other steps look at, and are refused here.

### Reading the results

`docs/method.md` is the method note: what each measurement means, how each one
fails, and the traps the library is built around. Read it before quoting a
number. The short version of the three that matter most:

1. **Never quote a rate "against the background" without naming the layer.** Sea
   and cloud tops moved 98 px/s apart on the clip this came from; a single
   consensus returns a blend and names neither.
2. **Pixels per second become metres per second only through an angular scale
   *k* and a range *R*.** Neither is usually recoverable from a clip. A speed
   quoted without both sourced is not a measurement.
3. **NO POWER is a verdict.** A clip that cannot decide a test has not passed
   it, and those tests are reported, never dropped.

### Provenance, and the PURSUE videos

The tools run on any file. The package also carries the list of the U.S. DoW
PURSUE release's videos (war.gov/UFO), so a record id works with nothing set up:
the first time a video is named, it is downloaded from DVIDS into the storage
folder (below), and the integrity report quotes the releasing body's own words,
including any alteration statement, alongside the pixel tests:

```bash
mcdonald integrity PR144            # downloads PR144 the first time (31 MB)
```

A mirror of your own, or a catalog of another release, is named instead with
`MCDONALD_CATALOG` (`none` for no catalog at all):

```bash
export MCDONALD_CATALOG=/path/to/pursue_index/records.csv
```

Writing another backend is a subclass with one method; see
`src/mcdonald/catalog.py`. A clip that is not in the catalog gets "no record
for this file": nothing is borrowed from someone else's release.

### Where the large files go

Downloaded videos and each video's frames (a lossless 1080p frame is most of a
megabyte, so a whole clip is gigabytes) go in one storage folder:
`Documents/mcdonald` unless `MCDONALD_HOME` says otherwise, with `videos/` and
`frames/` inside it. In the window it is shown on the first screen, with a
button to change it. `--workdir DIR` puts one command's frames somewhere else.

This matters more than it looks. On a disclosed digital recreation, every pixel
test returned NO POWER or INCONCLUSIVE — **the record identified the clip, not
the pixels.** Custody and disclosure are not things pixel forensics can replace.

## What it cannot do

`integrity` shows whether a clip and the object in it behave like the output of
one sensor chain. It catches an object pasted, AI-inserted or animated onto
footage that already existed. **It cannot exclude a composite made upstream of
the symbology by someone who modelled exposure, shake, gain and parallax.**
Nothing in the pixels can; that is a custody question — the original recording
with its metadata, and the mission report. Say so whenever you quote a result.

The synthetic-insert self-test is what gives a PASS its meaning: the tool
animates a fake object over the same frames and runs the same tests on it. If
the fake passes too, that test has no discriminating power on your clip,
whatever its verdict says. Note the honest limit: no clip with a *known real*
insert was available to validate against, so the synthetic stands in for one,
and it models a naive overlay rather than a match-moved physical composite.

- **A payload too faint for single frames that swings more than its own size.** `tether` finds a line or a payload that moves with the object by stacking the frames on it, with the track run backwards as the control, and reads a line's length off the swing's period; a payload that smears by its own swing in the stack and cannot be seen on single frames evades both, and needs a search over the pendulum's motion that is not written. Under two cycles the period is tentative.

## Roadmap

Working (0.2): the `run` driver and the case report; background layers; clip
integrity; track verification; symbology (boresight, north pointer, corner
brackets); angular scale (graticule, in-frame reference, zoom chain, the FOV
ladder); the kinematic reduction; object-versus-texture co-motion; one figure
style; a catalog, with the PURSUE videos' list shipped and downloaded on demand.

Next: automatic tracking good enough to trust without hand marks (the current
`--auto-track` needs its sheet checked every time); the mode annunciator and
the data bar; batch mode over a whole catalog; the dimensionless-number
reduction.

## License

**BSD 3-Clause** ([LICENSE](LICENSE)), copyright Jacob Haqq Misra, chosen
2026-09-25 when the repository went public: the scientific-Python norm, and
its third clause keeps the author's name off a derived version's promotion
without permission, which matters on this subject.

A dependency's licence could have constrained that choice: anything GPL linked
into the package would have forced the package GPL. That is why the marking GUI
uses **PySide6 (LGPL)** rather than PyQt (GPL or commercial), and only as an
optional extra — see `docs/handoff-gui.md`. Keep it that way.
