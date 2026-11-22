# mcDonald UAP Toolkit: the technical README

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

**Status: alpha (0.5.9).** The full pipeline: eight stages from a file to a
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
(`mcdonald.update`). To ask now, whatever was asked today and whatever turned it off: Help → Check
for updates in the window, and the `version` line of `mcdonald setup` (`--json`: the check named
`version`), which says the newest version and the pip command when there is one (`update.now`).

### What it needs, and how long it takes

- **Python 3.10 or newer, and ffmpeg**, on macOS, Windows or Linux. The window needs a desktop;
  the command line does not.
- **Disk**: each frame worked on is saved once, losslessly: about 0.75 MB a frame at 1920×1080,
  so a 3-second segment is ~70 MB and a whole 3-minute video ~4 GB. Downloaded PURSUE videos are
  2 MB to 3 GB (most under 100 MB). Both go in one folder you choose on the first screen.
- **Memory**: 8 GB is enough for a segment of a few hundred frames; more for whole videos.
- **Time.** mcdonald compares frames pixel by pixel, and some steps are slow. On the machine it
  was built on (a 2012 six-core Xeon workstation, 2 GHz, 32 GB), for a 1080p segment, and on 4 CPUs
  (2 cores) of the workstation it is developed on now (a 48-core Xeon of 2025), for whole videos:

  | step | the 2012 workstation, about | 4 CPUs of the 2025 workstation, about |
  |---|---|---|
  | saving the frames (once) | a few seconds per 100 frames | 1 s per 100 frames |
  | Find the object | 15 s + 0.2 s a frame (a 3-second segment: under a minute) | 0.26 s a frame (0.29 at 1080p, 0.21 at 720p; a 5-minute video: 40 minutes) |
  | Follow it | about ten seconds | 15 s (median; 0.06 s a frame) |
  | Measure, without the two slow checks | under a minute | 50 s (median) |
  | Measure: the *layers* check | about 1.4 s per pair of frames (3 s: ~2 minutes) | 2 minutes (median; 0.5 s a frame; 6.5 minutes or more on a tenth of the tracks) |
  | Measure: the *integrity* check | about 1.5 s per pair of frames + 30 s (3 s: ~3 minutes) | 1.5 minutes (median; 1 minute + 0.15 s a frame) |

  The right-hand column is the record of the first run of `mcdonald batch` over all 144 PURSUE videos (13 and 14
  November 2026, the code of commit abdc399, 4 CPUs a video with other jobs beside them, no graphics card; 620 objects
  followed and measured with every check, those whose clock ran across a pause of the scheduler left out;
  `docs/method.md` §54). There an object takes 4.5 minutes (median; 0.6 to 80, by its track's length and its
  background), and the two slow checks are 80 % of it. A whole video is Find over every frame and then its objects,
  up to twelve: 5 minutes (median) where nothing lasted, 47 where objects were measured; PR149 (52 s, 7 objects) 42
  minutes, PR088 (5 minutes, 12 objects measured of 30) 110, PR098 (18 minutes, 12 of 120) 4 hours. The catalog took
  about 650 CPU-hours. On 8 CPUs a video takes about three quarters as long, so several videos side by side on 4 CPUs each
  get through more than fewer on 8. Since that run the *layers* check takes about half as long on a CPU, and the
  *integrity* check's background is read once, with the same numbers to the bit (the CHANGELOG, 0.5.5 and after); a
  batch job given the graphics card takes both in minutes.

  On four CPUs (a laptop) count on about twice these: a 2-second segment of PR113 measured with
  every check took 8 minutes there. The long steps use every CPU there is, as far as the memory
  free allows (about half a gigabyte a CPU for 1080p video), so a machine with more cores is
  faster -- up to 32: on a 96-thread workstation, whole runs at 8 to 88 worker processes were
  fastest at 32 to 48 and up to 15 % slower at 88, so a computer with more than 32 uses 32
  unless told otherwise (`--cpus N` with a larger N is used as given). To leave some of the computer for other work, `mcdonald --cpus N <command> ...` (or
  `MCDONALD_CPUS=N` in the environment) lets every step use at most N CPU cores, and in the
  window **Edit → Preferences…** (on a Mac, mcDonald → Settings) does the same and is remembered; `--procs N` on a
  command sets one step's worker processes within that.

- **A graphics card (GPU), if there is one.** Never needed. Where the computer has an NVIDIA card and CuPy is
  installed (the window's Preferences has a button for it, **Install the add-on**; from a terminal,
  `mcdonald setup --install-gpu`, or by hand `pip install "mcdonald[gpu]"`; [docs/install.md](docs/install.md)), the
  steps that match one frame
  against another run on it: the *layers* check and the *integrity* check's background passes, which are most of a
  Measure's time. On the workstation mcdonald is now developed on (a 48-core Xeon and an RTX 5070 Ti, November 2026),
  the *layers* check of a 2-second 1080p segment takes 27 s on four CPU cores, 10 s on all 88 threads and 3 s on the
  card; of a 30-second segment, 60 s on all 88 threads and 35 s on the card. A whole `mcdonald run` of a 9-second
  720p segment takes 107 s on eight cores and 71 s with the card. The measurement is the CPU's: the same templates
  and verdicts, the report word for word, and numbers that agree to about one part in a million
  ([docs/method.md](docs/method.md) §52 says what is held, and how). `mcdonald --gpu none` (or `MCDONALD_GPU=none`, or
  Preferences) keeps every step on the CPU, and `--gpu NAME` picks among several cards. Inside a batch job a card is
  used only if the job was given one (for Slurm, `--gres=gpu:1`). `mcdonald setup` says which card is in use, and a
  case's report says when a card took part in it.

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
python3 tests/test_audio.py          # audio: planted propellers, supplies and codec lines; noise gives nothing
python3 tests/test_gpu.py            # a graphics card's arithmetic held to the CPU's (runs with or without a card)
python3 tests/test_plant.py          # planted objects: where the truth table says, the same file twice, marked as a test video
python3 tests/test_noise.py          # the noise model: curves read as the stage read them, the centile, the tail, the FDR
python3 tests/test_rank.py           # the ranking: p-values uniform on drawn classes, every defect rule, NO POWER's reasons
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
mcdonald mark CLIP.mp4 --n0 400 --n1 420    # or a segment of it, saved in a folder of its own: clip/segment-400-420/

# ...and hand those clicks to the pipeline: the track is linked from them
mcdonald layers CLIP.mp4 --marks CLIP/clip_marks.json

# The same with no window, for something that cannot click: see the clip, then say where
mcdonald look CLIP.mp4 --n0 1 --n1 120 --propose          # what moves against the background, best first, as strips
mcdonald look CLIP.mp4                                    # an overview sheet; --n0/--n1 narrow it
mcdonald look CLIP.mp4 --frame 408 --size 21 --dark       # a frame's candidates, ringed, numbered, enlarged
mcdonald mark CLIP.mp4 --n0 400 --n1 420 --no-window --link \
    --set object@408=1010.9,313.0 --set object@411=702.4,604.2 --why "candidate 1 of 6 at 21 px dark; the one that moves"

# Each segment of a video named with --n0/--n1 keeps its results in a folder of its own, ./<tag>/segment-<n0>-<n1>/
# (the whole video's are ./<tag>/; --out names any folder outright). look --propose prints `--segment A-B` on the
# lines that take its rows, so that look, mark and run meet in one folder; this lists them, as the window does
mcdonald segments CLIP.mp4                  # each segment with results: its frames, what its report says, where

# Start a case over: what its results folder holds (the marks, the tracks, the reports, each object's folder) is moved
# into a dated folder inside it, earlier/<date>_<time>/, so the next run starts with nothing saved. Nothing is deleted
# unless --delete is given; the video, its frames and other segments' folders are not touched (the window's Start over)
mcdonald clear CLIP/ --dry-run              # what would be set aside, and what would stay
mcdonald clear CLIP/                        # a results folder; or the video, as every command names its case:
mcdonald clear CLIP.mp4 --n0 400 --n1 420   # ... that segment's folder, clip/segment-400-420/

# What could the search have found? Synthetic objects written into a stretch and encoded again as the video is, with a
# truth table of where each is in every frame, and the same stretch with nothing planted as the control. The result
# is a test video, never footage: its name, its tags and every case made from it say so (docs/method.md section 62)
mcdonald plant CLIP.mp4 --n0 1 --n1 400 --draw 20 --seed 1 --out plants/      # 20 objects drawn over contrast, blur and speed
mcdonald plant --score plants/clip_planted_1_400_s1_truth.json --proposals look.json   # Find's list against the table

# Boresight, north pointer, corner brackets -- the overlay's own readings
mcdonald symbology CLIP.mp4
mcdonald symbology CLIP.mp4 --method hue             # the pointer by its colour alone: warm (orange, red) where a warm glyph
                                                     # shows, else the hue the frames' own glyph has (magenta, cyan); --box
                                                     # Y0,Y1,X0,X1 says where to look in a picture with colour of its own

# v_px -> omega -> what the motion permits (with --ladder when k is unknown); the speed band -- the rate along the
# track with its error from the track's own covariance (<tag>_speed.csv, .png), a changing speed described, not refused;
# a sudden change of velocity beyond the track's own wander, dated with an interval (in `run`, set against the scene the
# layers step measured: the camera's or not; method section 51); and what survives with no range, field of view or
# platform speed: the constant-velocity test, the turn radius in body widths (--size-px), the smear number, and which
# motion models survive as a 90 % model confidence set (a line, constant velocity in projection, a steady turn); beside
# the band, its jitter read with no model (a beat it misses); two readings against a sourced table of known kinds
# (class_envelopes.csv; method section 61): the speed in body lengths a second as a lower bound (--size-px) and the turn
# as a load-factor curve (<tag>_load.png), each NO POWER where the camera moved; and which of the four unknowns would
# settle the most of a stated question about the speed, under two measures
mcdonald kinematics CLIP.mp4 --track track.csv --ladder

# Does the object move WITH the texture around it, or THROUGH it?
mcdonald comotion CLIP.mp4 --track track.csv --diameter 72

# Is the object several points moving together, and do they keep their places? (a formation does, a flock does not)
# With four members or more: do they move as one rigid body, or as several? Each answer may be "cannot say"
mcdonald groups CLIP.mp4 --track track.csv

# Does something hang under the object -- a line, a payload -- and does it swing? (hangs / beside it / nothing tied /
# cannot say, from the line's angle to the picture's vertical; a swing's period T -> metres of line)
mcdonald tether CLIP.mp4 --track track.csv

# Does its brightness beat, and is the beat its own? The bird paper's way: its aperture, its rule, its neighbours avoided
mcdonald flicker CLIP.mp4 --track track.csv
mcdonald flicker CLIP.mp4 --track bird_A.csv --aperture 4,7,10 --beat-rule paper --avoid bird_B.csv,bird_C.csv
# beside the call, and changing none of it (docs/method.md section 59): the beat in the position (does its track carry the
# rhythm of its brightness? --scene-shift takes the camera's motion out), a line in a look-alike band that the strongest
# peak hides, the shape of a beat that sits where the sensor chain can make one, and how much of the band carries a mark
mcdonald flicker CLIP.mp4 --track track.csv --scene-shift --json
# a beat that only follows the track is the track's, not the object's (docs/method.md section 69): the brightness is
# read in a small disc that rides the track, and over an object wider than the disc the track's own jitter becomes a
# beat. A beat that keeps under half its strength once what follows the jitter is out reads "no beat of its own", and
# the result records it (`jittered`, each beat's `jitter`). It can take a beat away and never gives one

# What does the sound track record? The codec, a supply's hum (a clock), a propeller (the platform), and where
# each folds through the frame rate (no track needed; a sound file works with --fps)
mcdonald audio CLIP.mp4

# A screen filmed by a phone: hold the display still, and write the display's own video (frame n = frame n),
# CLIP/clip_stable.mkv, for every other command to run on; --to-clip carries a track made on it back to the clip
mcdonald stabilize CLIP.mp4
mcdonald stabilize CLIP.mp4 --to-clip held_track.csv     # writes CLIP/clip_track_on_clip.csv

# Does it look the same from every side? Its brightness and size against its heading (a sphere's do not follow it);
# no range, field of view or beat needed. --still on a held display, --depression to bound a winged flyer's bank
mcdonald aspect CLIP.mp4 --track track.csv
mcdonald aspect CLIP/clip_stable.mkv --track held_track.csv --still --depression 20

# The sea as a ruler: metres per pixel from the dispersion of its waves (no field of view, no range, no telemetry)
mcdonald waves CLIP.mp4 --n1 120
mcdonald waves CLIP/clip_stable.mkv --n1 120 --held CLIP/clip_stabilize.csv     # on a held display

# k from the camera's own slew: the scene's shift against the north pointer's turn (the pointer on every frame first)
mcdonald symbology CLIP.mp4 --step 1 --method template --tpl-box X0,Y0,X1,Y1 --out CASE
mcdonald layers CLIP.mp4 --out CASE
mcdonald slew CLIP.mp4 --out CASE                    # --window T0:T1 round a slew; --depression D for k itself
mcdonald slew CLIP.mp4 --hold-rate 0.068 --out CASE  # the platform's share of the pointer's turn known (v_perp / R):
                                                     # a steady pan then gives k too
                                                     # every claim's pointer is read as a stale price (its lead-lag behind the
                                                     # scene, the most it owed while it sat still, Dimson's summed slope): one that
                                                     # runs over a second behind the picture is refused by name; a zoom state's
                                                     # windows are combined only where they agree (method 49)
mcdonald slew CLIP.mp4 --platform P.csv --los L.csv --out CASE   # a data bar in place of the pointer: the aircraft's
                                                     # position and the line of sight's ground point at each reading
                                                     # (drift's files); the hold and the depression come with them

# Does the scene move under the sensor's pattern? A reading of whole blocks of 60 frames, with no templates: for a clip `layers`
# says is held still. `layers` runs it on such a clip by itself (--no-scene: not), and its file is its own: no other stage takes a
# rate from it. Where enough blocks read the scene moving, the report says the background moved, not that it held still
mcdonald scene CLIP.mp4 --out CASE                   # every block; --sample 12 for a look at a long clip; --track CSV keeps the object out
mcdonald slew CLIP.mp4 --scene-blocks --out CASE     # k from the slew with the scene from those blocks, only when asked: each zoom state one
                                                     # window, the blocks' agreement with the pointer tested against circular shifts of it
                                                     # (21 blocks or more; the pointer read on every frame, --step 1)

# Where each layer of the background is in the picture, and how its motion changes across one: 128-px templates every
# 16 px on 24 pairs that moved (method 65; best on a graphics card, about a third of a second a 1080p pair). A match counts
# above the peak at which two empty pairs -- the clip's own second frame turned half a turn, and that frame with its detail
# scrambled (or --null-from another video's frame) -- keep 1 % of their templates or fewer. Its files are its own: no other
# stage and no report takes from it
mcdonald layers CLIP.mp4 --dense --out CASE           # --dense-pairs 48 for more; <tag>_dense.csv, _dense_map.csv, _dense.png

# The camera's zoom states: where its field changes in a burst of blank frames, or in a step of the picture with no
# blank (an electronic zoom), and by how much (slew and camera use them)
mcdonald zoom CLIP.mp4 --out CASE                    # each burst a step (x s), no step, or unknown
mcdonald zoom CLIP.mp4 --events CASE/clip_events.csv --out CASE     # and the picture's steps `events` found
mcdonald zoom CLIP.mp4 --rd --out CASE               # each zoom also as a regression discontinuity: the jump from the pairs
                                                     # 3 frames either side with its interval, and placebo cutoffs inside the
                                                     # states (how often a step is found where there is none; method 49)

# What a phone wrote down about its own clip: an iPhone's frame-by-frame record (its LivePhotoInfo track, found by its
# key and read with ffmpeg alone: the zoom, the camera's shift and the exposure on every frame) into CASE/clip_phone.csv,
# and what the file says of the device, the lens, the software and its own history; exit 5 where there is no record
mcdonald phone IMG_0001.MOV --out CASE

# The sea's horizon as a ruler: a thing seen against the sea is nearer than where its line of sight meets it; a thing
# above the horizon is at least as high as its line of sight's lowest point (a point on the horizon, the camera's
# height and k needed; the line is found through the point and followed)
mcdonald horizon CLIP.mp4 --track track.csv --horizon 1,640,212 --height 7000ft --fov 2.1
mcdonald horizon CLIP.mp4 --track track.csv --marks CASE/clip_marks.json --height 2100m --graticule 300 --range 9000
# Each bound holds for air that bends light as the stage assumes (a refraction coefficient, kappa, of 0 to 0.25), and
# says which way it breaks outside that: --kappa=LOW,HIGH gives another band (a sea warmer than the air: below 0;
# warm air over a cold sea: toward 1; 1 or more is a duct, with no horizon, and is refused)
mcdonald horizon CLIP.mp4 --track track.csv --horizon 1,640,212 --height 7000ft --fov 2.1 --kappa=-0.5,0.25

# Sharp means far: an object as sharp as the scene's own points is at least D / (its defocus disc) away, focused far;
# with no pupil given, the optics' diffraction bounds it (the band's shortest wavelength)
mcdonald focus CLIP.mp4 --track track.csv --fov 0.7 --band mwir
mcdonald focus CLIP.mp4 --track track.csv --graticule 900 --pupil 10cm

# The air as a ruler: a dark object's contrast against its sky in daytime haze, in linear light, bounds its range
# (Koschmieder; good to a factor of about four), with the reported visibility or something dark at a known range
mcdonald haze CLIP.mp4 --track track.csv --size 12 --visibility 20km
mcdonald haze CLIP.mp4 --track track.csv --size 12 --reference 1,410,212,3000

# The dash a fast object draws in one frame (PR43's), read along the track on each frame less the median of its
# neighbours 4-6 frames away (where that is quieter round the dash): the dash fitted whole (Vereš et al. 2012's trailed
# point-spread function) for its centre, length, direction, width and flux -- the exposure from its length over the
# speed, the half-peak length beside it; its centres as a track, with the projective test's T on them and on the track's
# points; its flux as a second clock on T, if the object is a steady point -- and a flicker far above the frame rate as
# beads along it (each pixel is 1/speed seconds)
mcdonald streak CLIP.mp4 --track track.csv              # --blur 2 to give the blur rather than read it
mcdonald streak CLIP.mp4 --track track.csv --centres dash_track.csv   # the dash's centres as a track `run --track` reads
mcdonald streak CLIP.mp4 --track track.csv --scene-in   # each frame read as it is, the scene left in

# A number the overlay prints (an angle in whole degrees), timed to the frame: first a strip to read it off, then the
# value on each stretch; its ticks, the rate they make, and whether its holding still can say the camera stopped
mcdonald readout CLIP.mp4 --box X0,Y0,X1,Y1
mcdonald readout CLIP.mp4 --box X0,Y0,X1,Y1 --values "1-256:4,271-706:3,721-961:2"

# What the camera did: a zoom inside the track (from the object's size and its jump about the zoom's centre), the
# rate's steps set beside the camera's events, and -- with a scale and the camera's rate before -- whether a track
# that was let go explains the object's departure (with each rate's error from the departure's own wander beside the
# white one's: z_wander, method section 51)
mcdonald camera CLIP.mp4 --track track.csv --fov 0.7 --fov-px 244 --los-rate 0.247 --events "2208:gate collapses"
mcdonald camera CLIP.mp4 --track track.csv --events auto     # the overlay's own events, found (as `events` finds them)
mcdonald camera CLIP.mp4 --track track.csv --scene CASE/clip_layers.csv --after 4439 --fov 0.08 --pixel-aspect 1.333
                                                               # the ground in the picture as the camera's own record:
                                                               # the track relative to the scene's path, the camera's
                                                               # rate before from the scene's drift (no readout, no k)
mcdonald camera CLIP.mp4 --track track.csv --fov-px 244 --fields "1-2156:0.7,2157-2206:1.5,2208-2216:6"
                                                               # the field across the picture as the display gives it:
                                                               # each change taken out like a zoom, checked on the object
mcdonald camera CLIP.mp4 --track track.csv --zoom CASE/clip_zoom.json   # the zooms `mcdonald zoom` measured in the
                                                               # picture, taken out the same way (read by default where
                                                               # the case has one); its other bursts are camera events
mcdonald camera IMG_0001.MOV --track track.csv --phone         # a phone's own record of its zoom on every frame, checked
                                                               # on the object's size first, and k from its lens and zoom

# The overlay's own events: its text boxes and when each changes (timed to the half frame), clocks, the strokes round
# the object (its gate), the picture's steps and held frames
mcdonald events CLIP.mp4 --track track.csv

# The Navy's ATFLIR display, which draws no north pointer: its fields of text placed and followed, a sheet of each
# field's looks to read, then what they said and the pod's slew from the azimuth's ticks
mcdonald symbology CLIP.mp4 --method atflir
mcdonald symbology CLIP.mp4 --method atflir --read "az:A=-8,B=-7;zoom:A=1,B=2;fov:A=NAR,E=MFOV"
                                            # and the picture's field, frame by frame, in `camera --fields` form
mcdonald symbology CLIP.mp4 --method atflir --clock X0,Y0,X1,Y1 --clock-at 1:5
                                            # each look's reading suggested from the clip's own clock's digits

# Several copies of one clip: which keeps the most, the frames each holds or drops, a relabelled frame rate
mcdonald versions COPY1.mpg COPY2.mp4 COPY3.webm --names 2007,dvids,commons
mcdonald versions BASE.mp4 RENDITION_1080.mp4 --width 1920      # at the smaller copy's full width, not 480

# Did it drift with the wind? Three main tests and a fourth on other evidence, each passes, fails or cannot say, and a
# tentative verdict: its height (T1) and the winds (T2) from the ranges, bearings and heading the display prints, its
# beat (T3, from flicker's envelope); other evidence (T4), where the video holds any: pieces it shed or cloud at its
# depth (T4a), and its remains' fall after a strike (T4b), from tracks held on the display
mcdonald drift CLIP.mp4 --size-px 22,15 --remains remains.csv --pieces a.csv,b.csv --slant slant.csv \
  --horizontal horizontal.csv --own-height own.csv --bearings bearings.csv --heading 145 --winds day.json \
  --airspeed-kn 0,240 --flicker f.json
mcdonald drift CLIP.mp4 --comotion comotion.json --tracer-depth layer --flicker f.json
# ... or T1/T2 from the aircraft's own track, where the display shows its position (lat/lon/alt, heading) and the
# line of sight's ground point but ranges nothing: the rays from a turning aircraft fix the object's path
mcdonald drift CLIP.mp4 --platform platform.csv --los los.csv --winds era5.json --obs-winds obs.csv --ground-m 72 \
  --when 2013-04-27T01:22:47 --flicker f.json
# its errors carry a constant error of the display's own azimuths: --az-ref-err DEG says how well the display's true
# north is known (by default the azimuth error of --los-sigma, 0.3; inf leaves it to the lines of sight themselves)
# ... or T1/T2 from cameras on the ground, each with its own clock: a row a reading (a time, the camera's name, its
# azimuth and elevation), the cameras' places in the rows or in a file of their own. No video is needed. Each camera
# has its own pointing error (--pointing-err AZ,EL, by default the errors of --los-sigma), its own scatter, and one
# camera alone cannot say; the winds' hour is the rays' own unless --when is given
mcdonald drift --rays rays.csv --cameras cameras.csv --winds model.json --ground-m 600 --flicker a.json,b.json
# how slow a flier that wind test would have caught, on this case's own geometry and winds (from an aircraft's lines
# of sight or from cameras'): bodies planted at the fitted place, moving with the air plus 5-50 m/s through it in
# eight directions, each through the same fit and test (minutes; --plant-speeds, --plant-air path|winds,
# --plant-draws, --procs)
mcdonald drift CLIP.mp4 --platform platform.csv --los los.csv --winds era5.json --ground-m 72 \
  --when 2013-04-27T01:22:47 --plant
# T2 is a strong test only from lines of sight. From the ranges it passes where the nearest hour and place given is
# within the fit's errors and a model's own error (4.8 m/s) of the sideways motion, and fails 10 m/s beyond; a slow
# flier passes it nearly as often as a drifter, so there the verdict needs T4a. From lines of sight a model's wind is
# allowed 2 m/s of error, and a body 10 m/s beyond the whole tolerance fails however well its velocity is known
# T3 passes where flicker finds no beat of the object's own, and says what it covered: the band it listened in, why
# where that band was cut short, and any beat that was seen and given to the track (its frequency, its strength, the
# share it kept). With several cameras' envelopes a beat one camera holds must be seen by another that could have
# seen it; a beat a camera gave to its own track is not counted as one
```

`drift` takes no video where its inputs carry their own times (`--rays`, `--flicker`); the inputs timed by a video's
frames need the video or `--fps`, and the command says which.

`stabilize`, `aspect`, `waves`, `slew`, `zoom`, `streak`, `readout`, `events`, `versions` and `drift` are not
stages of `run` yet, and the window has no page for them: so far they are the command line's alone. `horizon`, `haze` and
`focus` are steps of `run` where what each needs is given -- `run --height 7000ft --horizon 1,640,212` (or a horizon
mark in `--marks`), `run --visibility 20km` or `--haze-reference 1,410,212,3000`, `run --band mwir` (with `--pupil`,
`--focus-at`, `--ground-scale`) -- and so of the window's Measure form and its plain questions, each its command's own
call with the command's own k (FOV px / FOV, or the graticule). `camera` is a stage of `run` (after
`kinematics`), without the released-track null, which needs `--los-rate` or `--scene`, and with no events but the zooms it finds;
`run --fields` and `--fov-px` give it the fields a display shows. `run --lens-k1 -0.43` (with `--fov` or `--graticule`) gives
a wide lens's radial term, as a calibration counts it: the track is drawn back through it before the straight-and-steady
test and the turn. `--lens-k2` gives the second radial term where the calibration has one (k2 of
x_d = x_u (1 + k1 r² + k2 r⁴); the Galileo Project's infrared cameras: k1 -0.55, k2 +0.73). `run --pixel-aspect 1.333,symbols` gives the picture's stretch -- how much wider than tall the file draws
a pixel, and after the comma where that was read (`symbols`, `scene`, or your own words) -- so that the angle marks' scale
is read up the picture, the field of view counted in square pixels and the turn rate taken from the track's own direction;
without it a stretched file (PR113: a 720x480 raster shown as 1080p) reads a diagonal rate up to the stretch times too
high. A phone's clip (an iPhone's maker or model tag, or timed-metadata tracks) has its own record read at `run`'s ingest, as
`mcdonald phone` reads it: where the object's size follows the record's zoom (or the zoom cannot be checked), k comes from
the lens's 35-mm tag and the zoom ("the phone's record", to within 10 %; a `--fov` or `--graticule` given wins), the
kinematics stage fits its rate to the track on one scale, and the camera stage takes the zoom on every frame; a record
the pictures disagree with is said so and not used. `run --no-phone` refuses the record. Any other clip is not asked.
`docs/method.md` §14-30, §34, §36, §37, §39, §40, §42 and §45 say how each works and how each fails. `horizon`, `focus`, `haze` and `slew` take `--case CASE/clip_case.json`: the measurement is recorded in a
case `run` made and its report written again, whose table of **the four unknowns** (k, R, θ and v_own: constrained,
assumed, bounded or missing, by which route, and which released datum would close each) then carries the bound. Under that
table the report says which missing unknown is worth asking for first (`kinematics.value_of_information`, §61): the bits
of "is its own speed under 30 m/s?" and "under the speed of sound?" each would settle, under two measures, one ranked
first only where both agree.

`CLIP` is a path to any video file. Results go to a **case directory** —
`--out DIR`, otherwise `./<name>/` under your working directory, and for a
segment named with `--n0/--n1` a folder of its own in it, `./<name>/segment-<n0>-<n1>/`
(as the window keeps each segment's; `mcdonald segments CLIP` lists them). Nothing is
ever written next to the installed code.

**Two ways in, and each does the whole job.** A person with no terminal starts
`mcdonald-gui` (below), marks and links the object, and measures it from the
window's Measure menu, which is `mcdonald run` with a form in place of the
options. An agent with no display uses `look` and `mark --set`: `docs/agents.md`
is PR113 done start to finish that way, to 141.4 px/frame against the published
142. A mark placed with `--set` is recorded
as an agent's, with its `--why`, never counts as a hand mark, and a case report
built on it says so above its bottom line — which thing is the object is a
judgment, and the files say who made it. While the window works, an oval
beside its bar names the command that does the same (`look` while it finds,
`mark` while it follows, each stage's own while it measures), so whatever a
person watched it do can be found on the command line. Under the bar, in place
of a line of text, a row of jewels counts the bars the step goes through -- for
Measure one a stage (`stages.planned`) -- each lit once its bar is over.

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
  it goes. An object that turns is found before the turn and after it, as two
  rows: it is slow where it turns, and a chain does not bend. So the last list
  puts such rows to the link (`propose.joined`, 2026-11-22; docs/method.md
  §110): started from the end of the earlier row with no mark ahead of it,
  does it arrive on the later row's first mark, and from the later back onto
  the earlier's last? Where both do, the list has one row, which says how many
  times the object was found (`pieces` in `--json`) and has marks in each
  stretch. PR169's bird, turning twice in 13.6 s, was three rows and three
  reports; it is one row, and the link from its marks one track over 396 of
  its 408 frames.

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
  simple: one box, **Measure the object**, with one button, **Begin** (`a`;
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
  pressed the Advanced Mode button under it is gone for that video (View →
  Advanced Mode remains). Pressed where results are saved, the button (then **Measure again**) goes on
  from them: it follows what is marked and measures it again, or measures the objects in their folders
  again. Two things start a case over instead (2026-11-22; `mcdonald/clear.py`, method section 111). A quiet
  **Start over** at the foot of the box, there whenever something is saved for the open segment (and
  File → Start this segment over…), asks in the box -- "Start over? …", **Start over** or **Keep them**,
  no dialog -- and on yes sets the saved results aside in `earlier/<date>_<time>/` inside the results
  folder (`clear.set_aside`, which `mcdonald clear` is; nothing is deleted) and puts the video back as
  when first opened: no marks, no track, no objects, no report, the lights off, the button Begin, and one
  line that says where the results went. And the count is not ignored (`auto_qt.AutoRun.outdated`): where
  everything saved was a one-press run's own choice, made for another count of objects than the one said
  now on the segment step, the button says Begin again, and the press starts over by itself and says so
  under the button when it ends.
  What a person chose -- marks by hand, a row said yes to, rows ticked, an agent's marks -- is never set
  aside without the question. What the person knows of the video that its pixels cannot say --
  the horizontal field of view, the distance to the object, a reference of known
  length in the picture (its length in pixels measured on the player), the speeds a
  report gave -- is asked on the segment step too, folded under the count, in the
  units they think in (`known_qt.KnownForm`; remembered for the video, and what
  the Measure form's fields show, so the one press and the queue use it). Where
  a report could not give a real speed, its card asks for the same things ("Add
  what you know") and "Work out the speed" is `stages.add_known` -- what `report
  CASE --fov ...` does, below -- and where it could, the card says what the speed
  rests on, with "Change". What it found and the pictures along its track wait behind
  Advanced Mode's "Show what Find found" and "Check the track". The wait while a
  video's frames are saved, or a video downloads, is a card at the top of the
  right column (`mark_qt.BusyCard`), not a dialog. **Advanced Mode** (View →
  Advanced Mode, or the button under the cards; every window starts without it,
  and a click on the video in Auto Mode is not a mark) puts the three
  steps, find, follow and measure, as buttons of their own, and marking by hand
  in the box's place; the same button, now **Auto Mode**, puts the box back. Everything a flag does is in the
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
  hours of frames open. (The command line says the same on stderr.) A segment chosen
  on the segment step keeps its results in a folder of its own inside the video's,
  `<tag>/segment-<first>-<last>/` (`mcdonald/segments.py`), and File → Another
  segment of this video, or the report page's "Back to the whole video", opens the
  whole video on that step again, with the segments opened before listed, each with
  its report; results from before there were segment folders stay in `<tag>/` and
  are listed as one. Every command does the same with `--n0/--n1` (`clip.named`,
  `clip.out_prefix`), and `mcdonald segments VIDEO` lists them.
  The track sheet is put under the video first, with the question every number
  after it depends on — is the circle on the object in every frame? — and
  closing it unanswered is a no, which the report records as provisional. The
  report then appears as a card in the right column under the one button, the
  video still in sight (`report_qt.ReportCard`; one card per object after a
  queue of several): a badge and the label of its
  conclusion (`report.Case.conclusion`: tentative, none, or firm, in one
  sentence -- a beat at a wingbeat's rate makes a bird the leading explanation),
  then the numbers found as label-and-value rows, "More" for how sure
  the conclusion is (`report.Case.grade`: GRADE's domains, computed), what it rests on, at most four reasons the heaviest first,
  each weighed on the labelled infrared set where it can be (`report.Case.reasons`, `controls`; method section 47), and the bottom
  line's paragraph (which says what a real speed still needs), "I looked" when the track sheet has not been
  checked by eye, and "Full report", the whole report as a page over the video
  (`measure_qt.show_report`), whose "Save as PDF…" writes it as one file with its pictures in it
  (`paper.write`, which `mcdonald report CASE.json --pdf` is too). The report's own checklist -- each test as a question
  in plain words, its answer in a word (Yes, No, Partly, Can't tell, Not yet; integrity's row Consistent or Inconsistent)
  and why in a line (`report.Case.checklist`; a tester's ask, 2026-11-01) -- is in the full report, under the conclusion's
  sentence, with the paragraph of reasoning folded under it, and in `run --json`. It is not on the card: it was from
  2026-11-01, and came off on 2026-11-22 because up to fifteen wrapped rows made the summary too long (the maintainer,
  after PR169). Measure → Open the case folder finds the files. **Measure → The sound
  of this video…** is `mcdonald audio` in the window: a page over the video that says first, in one
  sentence, what the sound holds (an aircraft named by two tones, the power it was recorded on,
  silence), then the picture of the sound and, folded, the command's own words. A video with sound
  also has a "Measure the sound" card in the right column (in colour until the sound is read, then
  ticked and grey), and its sound plays with the picture, in the player and while choosing the
  segment (by ffplay, which comes with ffmpeg; the speaker beside the stop button turns it off). **Edit →
  Preferences…** chooses where it plays -- the system default, or any output ffplay's SDL lists -- with a test
  tone, and chooses the graphics card (GPU) the slow steps run on: the cards mcdonald can compute on (NVIDIA's, through
  CUDA, with CuPy installed), greyed out where there is none, with a line saying why and what would change it. Where
  a card waits for CuPy, the row has a button, **Install the add-on**: pip runs behind a wait's card in the right
  column, the window stays open, and the card computes from the next step (`mcdonald setup --install-gpu` on the
  command line; `mcdonald.addon`). The
  choice is remembered and used from the next step (`mcdonald --gpu` on the command line). Opening another video while one is still on its way in (its
  segment being chosen, its frames saved) stops that one first. `mcdonald setup` (or `mcdonald-gui --desktop-entry`)
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
mcdonald run CLIP.mp4 --each CLIP/ --same 1,2    # objects 1 and 2 are the same object: made one (object 1), then followed and measured
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

**Two found objects that are one** (2026-11-22; `several.join`, method section 112). Find lists what it saw, so one
object seen twice -- 60 frames apart, or with frames between where it was not seen -- is two rows, two folders and
two reports, and `same_things` notices by itself only where two tracks lie on the same pixels. `run --each DIR
--same N,M` is for whoever knows they are one: the marks of both become object N's (the lower number), each mark
still saying what it was recorded as (`how`), the frames it was seen on the first to the last of either, and the
marks file gains a record of who said they are one and when (`joined`: what, of, by, when, which marks came from
which, and `both`, the frames both had marked at different places, where the lower number's mark is kept). Their old
folders are set aside whole in `DIR/earlier/<date>_<time>/` (`clear.aside`), and nothing is deleted or measured; the
queue then follows and measures the one object as any other. Its report says above its conclusion that the objects
were made one, by whom, whose marks it was followed from, and what the track did where one's marks meet the next
one's (`stages.seams`, by the link's own gate): "the track passes through the marks of both", or "The track does not
join them at frame 15", with the frames. The person's word is the authority, as a hand mark is, and what the link
found is not hidden. `--json` has `results.joined`; a group's member, and a group whose members are objects, are
refused with exit 2. In the window the same function is "Same object as…" on an object's card -- one line in the
card, a choice of the other objects, Join them or Cancel, no dialog -- after which the one object is followed and
measured as a press does it and the line under the button says where the old folders went; and at Find's list, with
two or more rows ticked, "They are one object" beside "Follow and measure the ticked ones" takes their marks together
as the window's own object (`QtMarker.take_as_one`), saved as proposed, with the same record.

In the window it is the same function. Each row of Find's list has a tick, "one of several"; with
rows ticked, "Follow and measure the ticked ones" under the list gives each a folder with its marks
(recorded as proposed, as "This is it" records them) and follows and measures them in turn
(`several_qt.SeveralPanel`): a row for each object with how it stands, Stop, "Measure the rest",
each report with the banner that says its track sheet has not been looked at, the list as a page,
and "Open in the window" for the object whose track needs a hand. Measure's form -- what is known
of the video, which slow checks to make -- is used for every one of them. The window's own marks
are not touched: an object in the list is a folder.

### Many videos, with nobody looking (`batch`)

`mcdonald batch` is the queue above with nobody choosing the objects, over a list of videos or the whole catalog
(ROADMAP 0.6; [docs/method.md](docs/method.md) §54 says what its rules are and what a row of its table can be read as):

```bash
mcdonald batch PR113 PR149:1-158 --out runs                # these, one after the other, with every CPU
mcdonald batch --list videos.txt --out runs --pool 4       # four videos side by side, each with a quarter of the CPUs
mcdonald batch --catalog --out runs --slurm --sbatch="--nice=100 -p some_partition"   # job arrays, a size class each
mcdonald batch --catalog --out runs --slurm --card 8 --cpus-per-video 4   # one job given the graphics card, 8 videos at a time
mcdonald batch --out runs --status                         # done, running, stalled, stopped, failed and why; nothing is run
mcdonald batch --out runs                                  # go on: what is done is not done twice
mcdonald batch --out runs --table                          # the table again, from the folders as they are
mcdonald batch --audit runs/pr149/object-1 --wrong none --by "A. Reader"   # a look at an object's audit sheet, recorded
```

One unit of work is one video (`batch.run_unit`; `mcdonald batch --out DIR --unit K` is what a pool's worker and an
array's task both run). In order: is there a picture that changes at all (`batch.picture`: a sound recording released
as a video is a row that says so); the frames, whole and once, in a folder of the unit's own; Find over every frame in
windows of 400 frames overlapping by 30 (`find/wNN.json`); the proposals seen on 40 frames or more, with background
all round, not a scrolling tape, the same object in two windows made one (`batch.long_lived`, `batch.merged`: the beat
sweep's rules, which `tools/sweep/` now calls); the first twelve by Find's score (`--most`) each an `object-N` folder
with marks at Find's seeds, recorded as an agent's with the rule as its reason; `several.run_each` on them, every
stage (`--quick` leaves out `layers` and `integrity`; `--only track,report` stops after the link, `--most 0` after
Find; `--keep N` keeps more of Find's rows a window than 30); the index; each object's audit (59 frames of its track drawn at
random by leverage, `<tag>_audit.png` and `.json`) and `<tag>_refused.png`, samples of what the rules refused; one
shared file, `<tag>_batch.mcdonald`, which `share rerun` measures again to its numbers; the unit's rows; and the
frames removed (`--keep-frames`). `DIR/batch.tsv`, `.json` and `.md` are the table over all of them: a row an object,
and a row for each video with none (nothing that lasted, a picture that does not change, a failure with its error).
A row is a spot that lasted, not an identified object: one object lost and found again is several rows, a group Find
listed as one spot is one row (`several`, `members`), and a spot in view under 40 frames is counted (`brief`,
`brief_spots`, `brief_longest`) and never measured -- PR113's four-frame transit is a count in a row that says
"nothing found".

It is resumable (`batch_plan.json`, a `batch_state.json` and a lock a unit): a unit that is done is left, one killed
half way goes on from the windows and objects it finished, and a unit done by another version or with other options
(`batch.make_of`) is left as it is and said to be so by `--status`, in every row and at the head of `batch.md`.
`--slurm` writes `DIR/batch.sbatch` (no partition, no account: those go through `--sbatch`) and submits one array a
size class (`batch.classes`: time and memory from the video's frames and size, fitted to a pilot on the 2025
workstation), then the table's job after them; `--slurm-print` writes the lines and submits nothing. `--units` and
`--except` take part of a plan (a long video on more CPUs than the rest); `--note` is a line kept with the batch and
printed at the head of its table. An array's task given the graphics card (`--sbatch=--gres=gpu:1`) would hold the
one card, so such tasks run one after another: `--slurm --card N` submits instead one job given the card (N x
`--cpus-per-video` CPUs, the memory of the N largest videos, `batch.card_job`) that runs the videos N side by side
(`--pool N`). Each video's process opens the card for itself and plans its batches on it within its part of the
card's memory (`gpu.part`, told how many share it by `MCDONALD_CARD_SHARED`); each video's log and
`batch_state.json` say what computed it (method §52).

### The corpus's noise (`noise`)

`mcdonald noise` (`mcdonald.noisemodel`; ROADMAP 0.6 objective 6, IDEAS S3, E24, D7; [docs/method.md](docs/method.md)
§63) reads every background aperture of a batch as the flicker stage read it and makes a distribution of them, so that a
beat's strength is a centile of what the sensors do rather than a fixed factor over four apertures:

```bash
mcdonald noise --read runs --out noise/readings [--unit K]          # each video folder's curves, read (a unit a video)
mcdonald noise --build noise/readings --batch runs --out noise/model [--only FILE] [--choose-on FILE]
mcdonald noise --model noise/model --hz 7.1 --share 0.12 --contrast 35 --frames 300 --aperture 6 [--window] [--standing 2.4] [--leave FOLDER]
mcdonald noise --fdr noise/model --readings noise/readings --out noise/model [--q 0.05,0.10]
```

`--read` rebuilds each curve exactly as `flicker.judge` judged it (`noisemodel.as_judged`: the span, the object's lost
frames filled across, each background aperture in its object's brightness; checked against the case's own
`fields.curves`) and reads it with the stage's functions (`flicker.peak`, `flicker.continuum`, the strongest amplitude in
each 0.5-Hz bin from 1.5 Hz, and the same in each 2-s window of `noise_pdf`'s). `--build` drops by stated rules (a
group's shared set, an aperture where something reaches `flicker.DROP` of the object on more than `LOST_MAX` of its
frames, a row followed onto another's track), stratifies by frame rate, contrast, aperture and length (a cell of under
10 videos falls back by length, then aperture), and fits a generalised Pareto past a threshold chosen by a stability
rule to the backgrounds' line power over their own continuum (`standing`², the ratio over the drawn null's 99th
centile). `--model` gives a beat's centile (each video weighing the same, an interval resampling videos) and a line's p
(empirical, past the threshold the Pareto; `p_cautious` with the shape at its interval's top). `--fdr` gives every
object's p (its own video left out) and Benjamini-Hochberg, Benjamini-Yekutieli and one-test-a-video over the batch's
rows, on four p's (the model's, the cautious one, the drawn continuum null over the whole stretch, the stage's own). The
PURSUE pass's model is in the reference-data folder's `noise/`. Readings only: no call and no report sentence reads them.

### A batch's objects against known classes (`rank`)

`mcdonald rank` reads a finished batch and writes a list for a person (ROADMAP 0.6 objective 5; method §64): every
object on the same axes, the record's defects first, then each object held against each labelled control class as a
tail probability within its stratum of quality, with the measure that drove it. It changes no report and names nothing
anomalous.

```bash
mcdonald rank runs                                   # against the data folder's controls/rank_controls.tsv
mcdonald rank runs --controls ctl.tsv --masks        # also find tracks on the overlay or a redaction block (reads the videos)
mcdonald rank runs --apart tools/sweep/holdout.tsv   # count a held-out set apart in the summary
mcdonald rank --records runs/rank/rank_records.json.gz --controls ctl.tsv --out ranked   # again, without reading the batch
```

In order (`mcdonald.rank`): a row followed onto another's track (`same_as`) is folded into it, and a group stays one
object of the kind "group"; the defects (`rank.RULES`: not followed, failed, integrity FLAGs, the overlay's
layer-order FLAG, a track on the static masks of its case's clip for a quarter of its frames or more (`--masks`), a
group read as one blend, `forensics.on_the_sensor`'s test on the object's own track, the report's "does not move against
the background", a track with no compact spot under it on most of its frames, a beat refused for held pictures) are
listed and never ranked; the axes (`rank.AXES`) are "score" (scale-free, measured the same way on the controls: the
strongest line's amplitude and, where it stands above the continuum, its frequency; the brightness's spread; its
frame-to-frame spread over the background apertures'; the size's change where the camera did not zoom; the rate
against the background in widths a second and its spread), "shown" (rates in pixels, the path's shape on the screen,
the line's standing) or "quality" (width, contrast, frames, fps, held share). Each object gets a full-conformal p-value
against each class within its contrast stratum (two, at the controls' median), the score being the largest robust
distance over the axes both have; NO POWER where the class has under 19 objects there, the object lies outside the
class's width, contrast or fps (widened by a tenth), or is a group. The list is ordered by the largest p over the
classes with power. Outputs in `--out` (default `BATCH/rank`): `rank.md` (the page), `rank.tsv` (every object, every
class's p, n, measure and reason, every axis), `rank.json` (the same with the summary, the held-out calibration and
the checks on known objects of other kinds), `rank_records.json.gz` (what was read, to run again in seconds).

The controls' table is made by `tools/rank_controls.py` from known objects put through `mcdonald batch` with the same
code as the corpus (the labelled infrared set's 365 clips, the Galileo flyers, AARO's resolved segments), each batch
object matched to its labelled box.

### Sharing an analysis (`share`)

One file to send someone, so that they go on where you left off (Jacob, 2026-10-15): a zip ending in `.mcdonald`
holding `share.json` -- the video by its catalog name, file name, size and SHA-256; the part to open; the stretches
to look at; the objects' names; and the thread, every note so far with who wrote it, whether a person or an agent,
and when -- with the video's results folder under `case/` (marks with their `how`, tracks, each `object-N`) and
any figures under `attached/`. The video is never in it.

```bash
# an agent's file from tracks alone: each becomes object-N, its track the automatic track, marks every 10 frames
# recorded as an agent's
mcdonald share make PR085 --object "o05=pr085_autotrack.csv" --look "3300-3500:first flapping bout" \
    --note "Beats at 7.37 Hz in bouts; please look at the first bout." --by Claude --agent --attach fig.png
# or from a results folder: the window's (a segment's: ./pr085/segment-2983-3923), with <tag>_marks.json and the object-N folders
mcdonald share make PR085 --case ./pr085/segment-2983-3923 --n0 2983 --n1 3923 --look 3300-3500 --note "..." --by Jacob
mcdonald share show FILE.mcdonald [--json]            # who it is from, the thread, the stretches, the objects
mcdonald share open FILE.mcdonald [--no-window] [--cases DIR] [--json]
mcdonald share rerun FILE.mcdonald [...] [--strict] [--video-dir DIR] [--cases DIR] [--json]   # its numbers again?
```

Opening one unpacks it into `<tag>-from-<who>-<date>` under the results folder -- never over anything there; a
second opening is a second folder -- finds the video (the catalog, then the storage folder's videos and the shared
file's own folder; the window asks where it is if none of those has it), checks its size and SHA-256, and in the
window opens the part with the sender's marks, every object's track and the shared card. Only data and pictures come
out of the zip; a member whose name would land outside the folder (`..`, an absolute path) stops it before anything
is written. An answer -- the card's "Save a file to send back", or `share make --case` on the opened folder --
carries the thread on with the new note last.

Does a shared file give back its own numbers? `mcdonald share rerun FILE.mcdonald` opens it as anyone does,
measures every object again by the command its report records, and holds the new report against the file's, number
for number and sentence for sentence (exit 1 where it does not): a number may differ by one part in a billion, a
file's path is compared by its file name, and every other string has to be the same to the letter. It is the check
every reference case of the data folder is held to (ROADMAP.md, 0.3), and in the window the shared card's **Measure
it again**. Minutes per object; needs the video (beside the file,
in the storage folder, in `$MCDONALD_DATA`, in a `--video-dir`, or by its catalog name). `tools/rerun_cases.py` in
the repository is the same, with the reference-data folder looked in as well.

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
mcdonald report CASE.json --fov 0.08 --range-max 41700   # nothing beyond the ground: the most its speed and size can be
mcdonald report CASE.json --forget range              # that range was wrong
mcdonald report CASE.json --pdf                       # and the report as one PDF, its pictures in it: <tag>_report.pdf
mcdonald report CASE.json --height 2000m --horizon 120,640,388 --visibility 12mi
                                                      # the horizon's and the haze's steps, done on the track followed
```

`report` takes `run`'s options that change nothing but that arithmetic (`--fov`,
`--graticule`, `--lens-k1`, `--lens-k2`, `--pixel-aspect`, `--range`, `--range-max`, `--ref-px`, `--ref-m`, `--range-ratio`,
`--size-px`, `--ground-speed`, `--own-ship`, `--line-of-sight`; `stages.AFTER`): the scale and kinematics steps
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
including any alteration statement, alongside the pixel tests. Its record also
gives the clip's levels: the range the stream declares, what the frame
extraction does to it (a studio-range stream's Y 16-235 is stretched to 0-255
and every code past them cut), the share of pixels outside the nominal range,
and how often the object's own core is past it (docs/method.md §50):

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
button to change it, and in **Edit → Preferences…**. `--workdir DIR` puts one command's frames somewhere else.

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

- **A propeller's blade count from its sound alone.** Four blades at one speed and six at two-thirds of it make the same tones; `audio` reads an airframe only where its propeller's speed is known (in flight, governed) and, for a lone line, only with that airframe's second tone. On the ground the speeds differ, and a phase of flight has to come from elsewhere. Most PURSUE sensor videos carry a silent sound track, which is NO POWER.
- **A phone's own lens and shutter, on a filmed screen.** `stabilize` holds the display with one homography a frame, which is exact for a flat screen seen in perspective; the phone lens's distortion and its rolling shutter (a shear while the hand moves fast) are left in what remains, which it measures and says, and do not come out.
- **A winged flyer that glides level and straight.** A flat planform shows the same area from every heading, so `aspect` cannot tell it from a sphere; only a turn, which banks the wings, gives it away. Under one full turn the headings are not all seen, and it says so.
- **A departure from a camera that stopped following.** When a tracker lets go, the object drifts out of the picture at the rate the camera had been turning; `camera --los-rate` sets the object's departure against a readout's rate, and `camera --scene` against the ground's own drift through the picture where the ground is in it (the track taken relative to the scene; PR051), but on an empty sky nothing shows the camera's turn. A readout that holds still to the end of a clip may hold whatever the camera did (`readout` says when).
- **A field of view from a pointer that does not say what it points at.** `slew` reads k cos(depression) off a slew only if the north pointer is an azimuth dial; a pointer drawing ground north projected into the image is off by a factor up to 1/sin(depression), and one drawn against the platform's heading registers no slew at all. A clip whose pointer registers none of its slews is NO POWER: the field may be that narrow, or the pointer may not follow the turret, and the clip cannot tell which. A pointer drawn on a coarse grid needs a slew that turns it by more than half a step beyond the platform's own share; a pointer that runs a second or more behind the picture (PR051's dial, two seconds) is a stale reading, and its slope is refused.
- **A scale from a narrow swell alone.** At one wavelength the waves' dispersion and the sensor's drift are one number, so `waves` gives a scale from a narrow-band swell only with the drift assumed, and claims one only where its band of scales is bounded, the dispersion beats drift alone, and the same frames shuffled in time score well below. Most PURSUE sea is refused, saying why.
- **A payload too faint for single frames that swings more than its own size.** `tether` finds a line or a payload that moves with the object by stacking the frames on it, with the track run backwards as the control, finds it again on the frames from where the stack put it, and reads a line's length off the swing's period; a payload that smears by its own swing in the stack and is under five times a frame's noise evades both, and needs a search over the pendulum's motion that is not written. A companion must be held in stretches of 45 frames on three tenths of the track, so one that shows only briefly is refused; a second object keeping the first one's pace passes as a companion. The stage's first answer, whether something hangs under the object (hangs, beside it, nothing tied, cannot say), is about the picture: the line from the object to what moves with it, or a line that starts at the object, lies within 18 degrees of the picture's vertical. Nothing in it knows which way is down in the world, a line at a random angle lies that near one time in five (the record gives each line's own chance), and a neighbour that keeps its place under the object passes as well as a load on a line does. Under two cycles the period is tentative, and a period is a swing only where a slow wander of the angle's own size shows one as strong under once in a thousand (measured: 1 in 100 drawn wanders at the worst).
- **A clip below the file's top that has been through a codec.** A core is called clipped where it sits at the picture's ceiling (255 on the extracted frames; Y 255 where the headroom the extraction cuts is read) or has a flat top (five of its 3 x 3 pixels within a code of its top, 50 codes over its surroundings; method §50). A peak a camera cut at 235, or a sensor at its own ceiling, before the encoder is rippled by the codec, and the null finds only 5-21 % of such cores flat; the rest read as peaks. Where that matters -- a width measured on a core cut below 255 -- the clip cannot say it was cut.

## Roadmap

[ROADMAP.md](ROADMAP.md) is the plan to 1.0, rewritten 2026-11-17 at version 0.5.7. A version
names a state to reach: 0.5.8 the wind-drift paper's release, 0.6 known answers at scale (the
Galileo Project's triangulated objects as a standing test, and one route in for new footage of
known objects), 0.7 the catalog object by object and finding without a hand, 0.8 the displays
and the sensor's record, 0.9 the walkthrough, and 1.0 a reproducible case file for every
PURSUE video with the ideas bank closed and the software paper submitted to the Journal of
Open Source Software. It carries the principles, what every release is held to, the working
rules and the decisions. The plan of 2026-10-16, whose objectives the code and the method notes
cite by number, is kept as [docs/history/roadmap-2026-10-16.md](docs/history/roadmap-2026-10-16.md).
CHANGELOG.md is what happened.

Working (0.2): the `run` driver and the case report; background layers; clip
integrity; track verification; symbology (boresight, north pointer, corner
brackets); angular scale (graticule, in-frame reference, zoom chain, the FOV
ladder); the kinematic reduction; object-versus-texture co-motion; groups,
flicker and tether; one window with one button; shared files; one figure style;
a catalog, with the PURSUE videos' list shipped and downloaded on demand.

## Support

**mcdonald** is free and open source. To support its development, you can
[donate to the mcDonald UAP Toolkit](https://www.zeffy.com/en-US/donation-form/project-janus-mcdonald-uap-toolkit)
through Blue Marble Space, a 501(c)(3) nonprofit. Donations are tax-deductible as allowed by law.
Supporters are listed, with thanks, on the [Supporters](https://mcdonald.bluemarblespace.org/supporters/) page.

## License

**BSD 3-Clause** ([LICENSE](LICENSE)), copyright Jacob Haqq Misra, chosen
2026-09-25 when the repository went public: the scientific-Python norm, and
its third clause keeps the author's name off a derived version's promotion
without permission, which matters on this subject.

A dependency's licence could have constrained that choice: anything GPL linked
into the package would have forced the package GPL. That is why the marking GUI
uses **PySide6 (LGPL)** rather than PyQt (GPL or commercial), and only as an
optional extra — see `docs/history/handoff-gui.md`. Keep it that way.
