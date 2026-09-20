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

```bash
git clone https://github.com/haqqmisra/mcdonald.git
cd mcdonald
python3 -m pip install -e .            # everything but the Qt window
python3 -m pip install -e ".[gui]"     # and the Qt window for `mcdonald mark` (PySide6, LGPL; ~240 MB)
```

Python ≥ 3.10, plus **ffmpeg and ffprobe on your PATH** — the toolkit reads
video through them and cannot install them for you:

```bash
sudo dnf install ffmpeg      # Fedora / RHEL
sudo apt install ffmpeg      # Debian / Ubuntu
brew install ffmpeg          # macOS
```

Then verify the install measures correctly before you trust a number from it:

```bash
python3 tests/test_measurement.py    # measurement: masks, registration, layers, detection
python3 tests/test_reduction.py      # reduction: symbology, kinematics, scale, marks, report
python3 tests/test_published.py      # every number in the Technical Note and the PR144 notes
```

Together those are 136 checks against cases whose answers are known by
construction — a known rigid shift, two backgrounds moving at different rates,
planted repeated frames, an object on a known path, the published PR113
reduction, the PR149 scale-bar bound — confirming the library recovers each
one. They need no video data, take under a minute, and each should end
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
```

That walks the clip through ingest → survey → track → **verify** → layers →
scale → kinematics → integrity → report, and writes `<tag>_case.md` and
`.json`. A stage that has nothing to work with says so and the run continues;
nothing is silently skipped.

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

  Then **`l` links**: an automatic track forward from the first mark, drawn over
  the clip as it grows, with the linked frames shown on the timeline and the
  track strip put in front of you at the end. The detector's scale and polarity
  are chosen from the marks, the track is held against every hand mark, and it
  stops when it loses the object rather than starting again on the brightest
  thing in the frame. `s` then also writes `<tag>_autotrack.csv`, which the
  other commands take as `--track`. On PR113 the two documented clicks choose
  21 px dark, link frames 408–411 onto the vendored positions to 0.005 px, and
  give back 141.4 px/frame against the published 142 — in the window, in under
  a minute. The same step without a window is `mcdonald.autolink`.
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

### Provenance, optionally

The tools run on any file and say nothing about where it came from. If you have
a catalog of releases, point the toolkit at it and the integrity report will
quote the releasing body's own words — including any alteration statement —
alongside the pixel tests:

```bash
export MCDONALD_CATALOG=/path/to/pursue_index/records.csv
mcdonald integrity PR144            # record ids resolve once a catalog is set
```

One backend ships, for the U.S. DoW PURSUE releases (war.gov/UFO) via a local
mirror's `records.csv`. Writing another is a subclass with one method; see
`src/mcdonald/catalog.py`. With no catalog, the report states plainly that it
knows nothing about provenance rather than defaulting to someone else's.

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
style; an optional catalog.

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
