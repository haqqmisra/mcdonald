# McDonald UAP Toolkit

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

**Status: alpha (0.2.0).** The full pipeline: eight stages from a file to a
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
   python3 -m pip install "mcdonald[gui] @ git+https://github.com/haqqmisra/mcdonald"
   ```

3. **Check this computer**, which also says what to type next:

   ```bash
   mcdonald setup
   ```

Then `mcdonald-gui` opens the window, and `mcdonald run PR113` does the whole job on the
command line (downloading PR113 the first time).

### Working on the code

```bash
git clone https://github.com/haqqmisra/mcdonald.git
cd mcdonald
python3 -m pip install -e ".[gui]"
```

Verify the install measures correctly before you trust a number from it:

```bash
python3 tests/test_measurement.py    # measurement: masks, registration, layers, detection
python3 tests/test_reduction.py      # reduction: symbology, kinematics, scale, marks, report
python3 tests/test_published.py      # every number in the Technical Note and the PR144 notes
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

- **The Qt window** (`pip install -e ".[gui]"`) is for the clip you have not
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
  list. A proposal's marks are for the linker: `tools/find_rank.py --link`
  holds Find and the link from its marks against every clip with a recorded
  track, and is what to run after any change. About 0.2 s a frame, shown as
  it goes.

  **With no terminal.** `mcdonald-gui` starts the same window the other way
  round: it asks for the clip (a file, or a catalog id: a PURSUE video not on
  the computer yet is downloaded, after asking), asks which part, keeps its
  cases in the storage folder (`Documents/mcdonald/<tag>` until changed on the
  first screen) and shows where, and says what goes
  wrong in a dialog instead of printing it. Everything a flag does is in the
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
  The track sheet is put on the screen first, with the question every number
  after it depends on — is the circle on the object in every frame? — and
  closing it unanswered is a no, which the report records as provisional. The
  case report opens beside the window when it is done, and Measure → Open the
  case folder finds the files. `mcdonald-gui --desktop-entry`, or Help in the
  window, adds it to the applications menu on Linux. It needs the `gui` extra
  installed once; it has not yet been run on macOS or Windows.
- **The matplotlib window** (`--gui mpl`) needs nothing beyond what the package
  already depends on. It steps at about 11 frames/s on 1080p, which is ample
  when you already know which frames to look at.

Both keep every mark in the same `MarkSet`, save through the same function, and
are held to the same checks by `tests/test_gui.py`. In both, a frame is a
lossless PNG named by its frame number; there is no video element to disagree
with ffmpeg about which frame is on screen, playback included.

### The gate

`run` makes a track sheet — every frame tiled with the tracked object circled —
and treats looking at it as a prerequisite, not an option. Without
`--i-looked`, every object measurement in the report is stamped
**provisional**. There is no flag that skips making the sheet.

This is not ceremony. On the clip this toolkit was developed against, the first
automatic tracker spent seven frames locked to a cloud feature 100 px from the
object and produced a clean, plausible, wrong rate. The sheet is how that is
caught, and it takes about ten seconds to look at.

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

**None yet — all rights reserved.** No licence is granted while the toolkit is
in development, which is deliberate: the right licence is easier to choose
once the shape of the thing is settled, and it is far easier to add one later
than to take one back.

One consequence that matters now: a dependency's licence can constrain the
choice later. Anything GPL linked into the package would force the package
GPL. That is why the marking GUI uses **PySide6 (LGPL)** rather than
PyQt (GPL or commercial), and only as an optional extra — see
`docs/handoff-gui.md`.
