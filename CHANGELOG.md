# Changelog

Every version that went out, newest first. The version is written in one place,
`src/mcdonald/__init__.py`; each release from 0.2.4 on is a git tag and is on PyPI.

## Unreleased

**`share rerun` holds every sentence to the letter** (IDEAS.md G6, found 2026-11-12, fixed 2026-11-13). A rerun is
made in another folder, so a string that is a file's path is compared by its file name. Until now any two strings
that both held a slash were taken for paths: "median 103 px/s (...)" and "median 250 px/s (...)" were the same
wherever the words after "px/s" were. Now only a path is compared that way (`rerun.is_path`: an absolute path, or a
string with no space in it and a file's ending); a rate, a ratio and a sentence are compared whole. A path written
on Windows is read by its file name on any system.

What the old rule hid, measured on the fourteen reference case files rerun on the workstation (31 objects; the
files were made on another CPU, so their numbers differ in the last digits there, as the benchmark of 2026-11-12
found): 21 sentences on 11 objects, each a printed number that moved by one in its last digit ("29.3" and "29.4
px/s"). Fifteen repeat a number field that differs too, so the old check already said so. Six do not: `integrity`'s
shake test prints both axes' slopes and keeps only the stronger axis's numbers, so PR135's "-646.24" against
"-646.25" was held by nothing. No object's verdict changes: each of the 31 already differed in a number field.
Two reruns of all 31 on the same computer, a day and five commits apart and in different folders, differ in nothing
under the new rule (test_share; test_gpu's check of the card's tolerance now has a slash in its sentence).

**No more than 32 worker processes unless asked** (the maintainer, 2026-11-13: "is there an optimal number of CPUs
for mcDonald GUI to use? Right now the default is the system maximum"). Measured on the 96-thread workstation: whole
`mcdonald run`s of PR149 (158 frames, 1080p), PR135's object 2 (270 frames, 720p) and PR088's object 2 (3,678
frames) at 8 to 88 workers, with the graphics card and without, were fastest at 32 to 48 workers and up to 15 %
slower at 64 and 88. Under 32, a worker for each hardware thread stays the default: in a job of 4 or 8 whole cores,
two workers a core beat one a core by 5 to 20 %. So nothing changes on a computer with 32 CPUs or fewer. A larger
number from `--cpus`, `MCDONALD_CPUS`, Preferences or `--procs` is used as given. The answers are the same at any
count (`progress.MOST_WORKERS`, `default_workers`; Preferences says the default; test_measurement, test_gui).

**Four corrections from the Galileo Project's triangulated objects** (branch nevada-fixes, 2026-11-13).
The Galileo Project's three infrared camera sites near Las Vegas triangulate what they see together, so its objects
have known ranges, heights and speeds: aircraft with known tracks (ADS-B) and clouds moving with the wind. Run as known
answers (method section 53; the uap repository's `galileo/nevada/README.md`), they found four things the reports said
that the measurements do not support (IDEAS.md N1-N6). Each changes what some reports say; no measurement changes.

- **Drift's T2 allows a model's own error** (N1; `drift.MODEL_WIND_ERR`, 3 m/s). Clouds need 3-4 m/s through the air
  against Open-Meteo's winds, more than the winds' hour-to-hour spread, so T2 said "cannot say" for most of them. With
  the allowance it passes 80-94 % of clouds and none of 44 aircraft. Only model winds carry it (each wind now says its
  `source`). The reading says what it costs: with a model's winds, a body flying a few metres a second through the air
  is not told from a drifter. The Puerto Rico lanterns still pass.
- **A beat comes back by windows apart only beyond chance** (N3; `flicker.CHANCE_P`, `windows_chance`). On a long track
  two passing windows apart are what chance gives: 14 of 16 beats on clouds and aircraft were. Such a beat is now held to
  the one-stretch rule, and `drift` weighs envelopes made before this from their own windows. **T3 with two cameras**
  (N4; `--flicker a.json,b.json`): a beat that one camera sees and another, watching at the same time and able to see a
  third of it, does not, is the first camera's view, and T3 passes on it.
- **No size from the default spot** (N5; `report.extent`). With a track file and no size, the report turned the
  tracker's default 9-pixel spot into metres and kinds of object ("an A320 at 8.0 km: about 98 m across"). It now uses
  the camera stage's length at half the object's peak, measured on every tracked frame (the A320: 45 m, its projected
  length 36 m), and says the size is not measured where only that default is known. A spot the marks or `--size` set
  is read as before. Reports made from a track file with no marks and no size change their size, their kinds and their
  distances; the rest do not (the track stage now records `object_size_from`; older cases are read as before).
- **The speed's errors, and the lens's second term** (N6). "The least its speed can be" carries the range's and the
  scale's errors: on aircraft it came within 5 % half the time and 20 % nine times in ten, and the report now says so.
  `--lens-k2` (`run`, `report`, `kinematics`; `lens.Lens.k2`) takes a calibration's second radial term: the Galileo
  lenses' k2 +0.73 had left rates near the frame's edge 12 % high. With no k2 every number is as before. The window's
  card asks for it beside k1 ("and its second bending term, if given").

For whoever runs the tests: `tests/test_drift.py` is now in `tools/suites.sbatch` and both workflows' lists; it was in
none.

## 0.5.3 (2026-11-12)

**The slow steps can run on a graphics card** (ROADMAP 0.6, objective 3; built 2026-11-12, the day the development
workstation had one). Never required: with no card, or without the add-on, every step runs on the CPU as before, and
the CPU's arithmetic is the reference.

- **`layers` and `integrity`'s background passes on an NVIDIA card** (`mcdonald.gpu`, `forensics._shift_field_on`).
  The card matches all of a pair's templates in one batch, threads read the frames ahead of it, and one process does
  the pass. On the workstation (a 48-core Xeon 678X and an RTX 5070 Ti) the *layers* check of PR113's frames 380-440
  takes 26.6 s on four CPU cores, 10.0 s on all 88 threads and 2.8 s on the card; of frames 1-900, 60 s on 88 threads
  and 35 s on the card. A whole `mcdonald run` of PR135 object 2 (270 frames) takes 107 s on eight cores and 71 s with
  the card.
- **The measurement is the CPU's.** The band-pass on the card is the CPU's to the last bit. The same templates keep
  their rows; each shift is within a hundredth of its own error; a pair's agreed shift within 0.0001 px on PR113. On
  PR135's whole case 26 of 4,040 values differ at all, the farthest by 1.3 parts in 100,000; no sentence, count or
  verdict differs, and the seven tables are byte for byte the same. `docs/method.md` §52 has the tables and the reason
  it is not "to the last bit" (single-precision correlations by another transform in another order).
- **Install**: `pip install "mcdonald[gpu]"` (CuPy with CUDA 12's libraries from PyPI: any NVIDIA card from the GTX
  900 series on, with only its driver installed), or `mcdonald[gpu-cuda13]`; `docs/install.md` has a section. Linux
  and Windows. A Mac's card, an AMD or an Intel one is named and said not to be used yet.
- **The choice**: `mcdonald --gpu NAME|NUMBER|none` (before or after the command), `MCDONALD_GPU`, and **Edit →
  Preferences…**, whose graphics card row is now live: it offers the cards mcdonald can compute on, says what runs on
  the card, and where CuPy is missing says how to install it. `mcdonald setup` has a "graphics card" line. Inside a
  batch job a card is used only if the job was given one (Slurm's `--gres=gpu:1`), as CPUs are counted by the
  allocation and not the machine.
- **A card is used only where a stage says so** (`gpu.on`), for the whole of a pass, never wherever one is to hand:
  a stage's numbers do not depend on whether it ran in one process or on a pool. A pool's workers never compute on
  the card. A card out of memory is sent half as much at once; one that stops is said once on stderr and the CPUs take
  the pairs left. One thread of its own talks to the card and never ends, because CuPy's FFT plans run Python's cycle
  collector in the thread that lets them go, and the window allows the collector in its own thread only.
- **A case says what computed it** (`computed_on` in `_case.json`, a line under the report's heading when a card took
  part, and a note in a command's `--json`). `mcdonald share rerun` measures a case again by the arithmetic it was measured by: a case the CPU measured,
  which is every case until now, on the CPU also where there is a card, held to one part in a billion as before; a
  case a card took part in is held to the card's agreement, one part in 10,000, and the comparison says so.
- **Held by** `tests/test_gpu.py` (new; in `tools/suites.sbatch` and both workflows): the card's code against the
  CPU's on drawn scenes, with NumPy standing in for the card where there is none (GitHub's runners), and on the real
  card where the job has one. `sbatch --gres=gpu:1 tools/suites.sbatch golden` runs every suite with the card's
  arithmetic wherever a stage has it.
- Also there and held, not yet used by a stage: the spot detector's response on the card
  (`forensics._spot_response_on`). Find and Follow still run on pools of CPUs.

Also in 0.5.3 (2026-11-10, a2bf7ed): the noise figure's legend is in two columns, not three; with conda-forge's
matplotlib and FreeType it ran off `one_noise.png` and `beat_noise.png`. For whoever runs the tests:
`tests/test_measurement.py` and `tests/test_reduction.py` take `--part K/N`, so the two long suites can run side by
side in parts.

## 0.5.2 (2026-11-10; on main that day, no tag of its own: on PyPI with 0.5.3)

A correctness patch for `mcdonald tether`: four defects found on 2026-11-09/10 by running the released stage on AARO's
known cases, on the reference case files and on three PURSUE clips with something under the object (IDEAS.md, H1-H4;
the maintainer, 2026-11-10: "0.5.2 goes ahead as a correctness patch for `tether`"). Two released reference reports
carried a pendulum that was noise.

- **The follower no longer leaves the companion, and a pendulum is no longer read off one that did** (H1;
  `tether.Follower`, `merge_ways`, `followed_how`, `judge`). After each frame the stage moved its gate to whatever it
  had last found, the strongest feature in a gate a quarter of the separation wide, and a candidate that passed the
  stack's tests and moved "smoothly" became the companion whatever its angle did. On PR105 the follower went with the
  scene, 14 to 1,290 px from the object, and the stage reported "steady to +-18.8 deg". On PR077 object 1 it went round
  the object through 320 degrees ("like a pendulum 9.71 m long (tentative)"), on PR135 object 2 through 150 ("2.52 m"):
  both are birds of the bird paper's Table 1, and both sentences were in their reference reports. PR149's record held
  `swings: true`, 0.159 m, beside "nothing tied to the object". Now a candidate is found again on the frames from where
  the stack put it: the strongest compact feature within 12 px of the stack's offset starts a stretch, the nearest to
  where it was last seen continues it, it may swing to 0.75 of its distance from the stack's offset and no farther, and
  it is counted on the frames that show it. The frames are gone through in order and in reverse and the two put
  together, so a companion is held from before it first passes the stack's offset, and past a stronger spot of the
  scene going by. `fields.swing` is the companion's alone: null where nothing is tied. PR105 reads "a bright feature
  moves with the object 26 px away at +0 deg from straight down ... re-found on 46% of the frames to 0.4 px;
  the companion's angle does not swing: steady to +-4.9 deg over 36.0 s".
- **A swing's period is held against a slow wander** (H2; `tether.wander_null`, `WANDER_P`). An angle that only
  wanders shows a cycle or two in a short window most of the time, and the two-cycle rule alone read "2.0 m" off
  AARO's known balloon PR-004 from two 6-7-s windows. The angle's strongest Lomb-Scargle power is now ranked among
  2,000 Ornstein-Uhlenbeck series of its own variance and correlation, drawn at the same sampling, and a swing is
  claimed only where under 1 in 1,000 is as strong. That threshold was measured, not assumed: on 57 kinds of drawn
  wander, 31,867 series (`tools/tether_wander_rate.py`), the two-cycle rule alone calls a swing in up to 78 % (29 % at
  the median); with the null at p <= 0.01 the whole rule still calls one in up to 3.3 %; at p <= 0.001 in 1 in 100 at
  the worst (0 to 1.0 % by kind), while a pendulum four times the wander's size is found in 84 to 100 % of series. The
  one known swing, WA9ONY-5's payload, passes (none of 2,000; 2.58 +- 0.02 s, 1.66 +- 0.03 m, tentative as before); PR-004 keeps its
  companion on all eight of its tracks and has no pendulum on any. A period the null refuses is in the record as
  `period_refused_s`, and the finding says how often a wander shows one as strong.
- **The companion gate is set against a null** (H3; `tools/tether_null.py`). 11 of 45 AARO tracks got a "companion" 112 to
  760 px away, scene or symbology, and PR29 "a pendulum of 0.65 +- 0.01 m" from a feature 277 px away on 8 % of frames:
  any strong feature the follower could follow "smoothly" was kept, and smooth was a share of the separation. Each of
  80 recorded tracks, 19,941 frames (AARO's 45, 29 of the reference objects, the stage's goldens, PR105, PR28, PR29) was
  run again on two tracks that nothing in the picture keeps step with: itself backwards in time, and itself shifted by
  half its length. The released stage, by its own command on those null tracks, names a false companion on 38 of the 154
  it runs on (a quarter) and reads a pendulum off 13 of them; the gate as now set names one on 2 of the 160 (1.3 %; 0.2
  to 4.4 %), with every known
  companion kept (WA9ONY-5's payload, PR071's string, PR105's lower point, PR-004 on its eight tracks). What it took: a
  feature re-found on a frame is 5 times the frame's noise, not 2.5 (within 12 px of a place a 2.5-sigma feature is there
  by chance on a quarter of frames); a companion is **held**, in stretches of 45 frames or more on 0.3 of the frames
  (counting every frame seen instead: 28 of the 160); and it makes under half of the scene's motion against the object
  and of the screen's (without that test: 30), the places regressed and not the steps, which share the track's own
  error. The control's 0.6 was held to the same null and stays. On the real tracks: of AARO's eleven far "companions"
  three are left, a feature on the horizon that keeps the distant object's pace (PR-010, in two windows) and features
  on the picture's straight borders, which the object moves along (PR-009); the method says why the tests here cannot
  refuse them. Of the twelve companions in the reference reports the neighbours in a flock stay (PR097, PR135), and the
  dark features hugging PR077 object 1, PR085 and PR44, at the inner edge of the ring where a sharpening ring puts its
  dark side, are companions no longer; PR097's objects 7 and 8 gain one each, a dark feature 14 px straight under the
  object on seven frames in ten, where a smear down the sensor's column would be.
- **Of several features that move with the object, the nearest is the companion reported**, among those held about as
  well (to a tenth of the frames). A swinging payload leaves several points of its arc on the stack, and each leads to
  the same payload; a neighbour 40 object sizes off is not what is tied to it.
- **"Nothing tied to the object" says where it looked** (H4). PR28's stem hangs straight under the head, inside the
  ring the stage searches. The finding now reads "nothing tied to the object between 18 and 540 px of it (1.3 to 40
  object sizes); nearer than 18 px is the object's own picture, and was not searched", the record carries `searched_px`,
  and the checklist's row says "nothing between 18 and 540 pixels from it keeps step with it; closer in was not
  searched". Finding a line that starts at the object is not in this release (IDEAS.md, H5).
- **The report follows the stage** in the three places it prints a swing (the headline's "swinging like a pendulum", the
  paragraph, the checklist's "with" row): a period the wander null refused is a pendulum in none of them ("Its angle
  drifts back and forth, but no more regularly than a slow random drift would. So no swing is claimed, and there is no
  length to read."; "with no regular swing"), and a companion seen on some of the frames says on how many. A report made
  before reads as it did.
- **`mcdonald tether` exits 5 again where the object moves under 20 px on the screen** and nothing can be told from the
  overlay: the test had kept the title's old wording since 0.5.0's sweep of "thing", and the command exited 0.
- **An object given as under 5 px no longer ends the stage.** Its stack reaches 42 object sizes, under the 200 px the
  object's size and extent were read over, and both readers raised (`run` recorded the stage as no power). Found on the
  null tracks of PR097 object 6, 4 px.
- **Tests.** `tests/test_tether.py`, 45 checks (24 before): a drawn wander the two-cycle rule calls a 2.12-m
  pendulum, refused, and a pendulum under the same wander, kept; a companion above the object, whose angle sits at +-180;
  the object's, the scene's and the screen's motion told apart, with the track's own error on both; a stack narrower than
  200 px read; and three drawn
  clips: a companion past a stronger spot going by 9 px away and right over it, a pendulum followed along its swing, and
  nothing tied, with no swing in the record and the ring that was searched. `tests/test_golden.py`: PR-004 (its rows 4
  and 8: the companion, no pendulum), PR105 (never more than a few px from where it hangs), PR077 object 1 and PR135
  object 2 (no pendulum), PR149, PR29 and PR28 (nothing tied, nothing in the record, the ring said), beside PR071,
  PR055 and WA9ONY-5 as before; their small tracks are in `tests/golden/`. `tests/test_reduction.py` holds the report's
  words. `docs/method.md` section 6 has the null, the rates, the controls' table and how the stage still fails;
  `tools/tether_null.py` and `tools/tether_wander_rate.py` rebuild its numbers, from `tether_null/` in the
  reference-data folder. `docs/tether-validation.md` shows the stage's own figure of each of its three clips.
- **The window's suite no longer skips the window in a job sent from the desktop.** `tests/test_gui.py` hosts the
  windows on an Xvfb of its own, and handed that child the desktop session's `XAUTHORITY`: another server's cookie file,
  with which Qt could not open there. The window went untested, and the suite and `tools/suites.sbatch` still said all
  passed (33 checks and 6 skips where there are 769). The variable is left out for the Xvfb child now.
- **For someone reading the JSON**: `companion` and each of `candidates[]` gain `followed_on`, `held_on`, `stretches`,
  `followed_jitter_px`, `scene_share`, `scene_moved_px`, `screen_share`, `screen_moved_px` and the reason a candidate is
  not the object's (`scene`, `screen`, `seldom`, `jumps`); `swing` gains `wander` and `period_refused_s` and loses
  `with_the_object` and `object_against_scene_px`, which the candidate's shares replace; `_tether_candidates.csv` has the
  new columns after the old ones, and `_tether_companion.csv` lists the frames the companion was seen on.

## 0.5.1 (2026-11-09)

Two things the JAIS Technical Note's reproducibility package found (2026-11-09; Jacob: the paper will be mcdonald's
first citation, "worth a little more development").

- **A pass from the marks holds its line over a gap** (`autolink._link_held`, `HOLD_MAX`). From two marks alone on
  PR149, frames 17 and 96, the link lost the contact for 20-odd frames where it crosses the ship, and `link_track`,
  made for a tracker that learns the velocity as it goes, opened its gate 12 px a frame meanwhile: forward it took the
  hull's lower edge 141 px from where the object should have been, and backward a crane 166 px off, then rode the crane
  to the first mark, because a spot that stays put on the screen is one step from the prediction on every frame once it
  has been taken (21 of 65 linked frames on the object, a curved track at 437-376 px/s). Now a pass whose velocity the
  marks give predicts at that velocity over a gap, never looks more than 60 px from where the object should be however
  long it has gone unseen, and takes the marks' velocity again after the gap, not the jump's; frame to frame it is
  link_track as before. From the same two marks the link holds its gap and arrives 0.1 px from the mark on 96: 40
  frames, 604 px/s, straight to 10 px rms, the paper's track. From eleven marks, and on PR113, nothing changes. The
  concerns say it: "the object was not seen there, and the link takes no spot more than 60 px from where the object
  should be". Drawn in test_measurement: an object unseen for 23 frames past a row of brighter spots, which the linker
  before took on 36 frames.
- **`share rerun` compares measurements, not the review state** (`rerun.review_state`). The two archived case files gave
  back every number and still "did not rerun": the file says a person looked at the track sheet (`--i-looked`), a run
  made again cannot, and the comparison counted that and the note it removes as four differences. The review state is now
  taken out of both reports before they are compared and said beside the result ("the review state is not compared. The
  file says its track sheet was looked at ... A run made again cannot say that"), in `review_state` of each object's
  result with `--json`; any other difference still fails the file. test_share holds both.

## 0.5.0 (2026-11-08)

The controls: ROADMAP 0.5.0's cut (the controls harness, the bird floor set from a null, AARO's resolved cases run
blind, the checklist's rows, reason codes and a grade, levels), the 0.4.x additions built beside it, and everything the
package says to people in sciencespeak and every figure in Jacob's house style.

- **Everything mcdonald says to people is written to one standard, sciencespeak** (Jacob, 2026-11-07: "make /sciencespeak
  the new standard to replace /simplespeak"; a tester's ask of 2026-11-01 for a report "that even an undergraduate student
  can understand"). Its reader is the educated non-specialist -- "the typical Scientific American reader", "an
  undergraduate level of scientific understanding" -- and its targets were measured on Scientific American and Quanta
  prose: about 20 words a sentence or fewer, none over 40, the field's own terms defined where they first appear, the
  trade's words and symbols (px, rms, theta, v_own) kept to tables and the command line.
- **The report's headline and its paragraph** (`Case.conclusion`, `Case.bottom_line`) are short sentences, one finding
  each: PR135's paragraph went from 38 words a sentence, the longest 124, to 17, the longest 34, with the same facts. The
  labels (Beats like a bird, Subsonic motion and the rest) are unchanged. The plain sentences for the turn, the
  straight-line test, the time to the camera and what the video allows are the report's own (`Case.track_said`); the
  kinematics stage keeps its technical ones for the command line and the folded Measurements. Two faults went with the
  rewrite: the headline said "it behaves like imagery from this sensor chain" wherever no integrity check flagged it, even
  where none could decide (PR135: none of eight), and now says nothing of integrity there; and a rate read over a
  background that held still on screen was said against that background in one sentence and not measured in the next.
  "The thing of known size" is a reference object of known size; a companion is a feature; a slow turn keeps two figures
  ("0.0073 × R", not "0.00").
- **Each of the report's figures has a caption** saying what to look at, and the provisional note at the top says what the
  track sheet is. Case files written before keep their note and read as before.
- **The window's text** follows it too: the help pages split into short sentences, and the object, a spot (what the computer
  found) or a feature is named, never a thing; test_gui holds the window to it (no "thing", no sentence over 40 words).
  The command line's output and help, the list of several objects and the stages' findings say it the same way, and
  Find's saved row text says "spots found" (older case files read as before).
  "Velocity" and "provisional" are no longer banned words. The card's More holds the reasoning alone: it says what a real
  speed still needs, in plain words, where a list in the stages' symbols used to follow it.
- **The docs** (README, the website's pages, the four exercise pages) are rewritten to it, the exercises' quoted first
  lines with them. The technical README and the method stay as they were, at Jacob's word.
- **The words on the figures** -- axis labels, legends and titles -- follow it: the quantity in words and its unit, what
  each line is, the finding. Colours and layout wait for Jacob's house style.
- **Every figure is in Jacob's house style** (2026-11-07, after the figures of his 2026 EBM/THAI paper, with his
  changes): a full black box with the ticks in on all four sides and no grid; tick labels 10 pt, axis labels 11 pt in
  bold, titles 12 pt and short (a name; the finding is the report's caption); the paper's colours -- blue first, amber
  second, red for measured points; legends inside the plot, borderless on white, or under it; no panel letters; and no
  text over a line. `figures.setup` sets it, `figures.dress` puts the frame on any figure, `figures.clear` moves a legend
  or a label off the lines (a label by at most 24 pixels, so that it stays by what it names) and reports what it cannot,
  and `figures.save` runs both. The report's figures were redrawn to it (the speed, the size and speed against distance,
  what the video allows, the track, the beat, the fold, the noise), the beat figure leaving the PR135 paper's own look,
  and the eleven stages' figures with them. The track figure now writes each time beside its dot on a side the path
  leaves clear, and leaves out a time where the path doubles back so tightly that none is clear (its dot stays); the
  enlarged object and the rate go to corners the path keeps clear of. The members figure names its members in a key, the
  aspect figure gives its changes in per cent, the waves figure names its band of scales, and the layers figure counts
  groups in whole numbers and shows both of two equal background lines. The suites fail on any figure with text over a line, over other text or off
  the figure (`MCDONALD_FIGURE_CLASHES`, set by `tools/suites.sbatch`), and test_reduction holds the report's figures to
  the box, the ticks, bold labels and short titles.

**ROADMAP 0.5.0's cut, built (session 18, 2026-11-07; method sections 43-47 and 50).**

- **The controls harness** (I1, T9, B28, B17; method §44). The Svanström et al. (2021) labelled infrared set, read from its
  MATLAB `groundTruth` objects with scipy alone (`tools/controls/svanstrom_labels.py`), is in the data folder as 432 tracks
  of 60 frames or more (125 birds, 82 airplanes, 168 drones, 57 helicopters); `tools/controls/run_set.py` runs `flicker` on
  all of them as `mcdonald run` would, under both rules, as a Slurm array, saving everything the judging was given so that
  the set is judged again with no video after any change to a gate (`summarise.py --rejudge`). The run of 2026-10-19 is
  rebuilt to the digit where nothing changed, and every call that moved since is a named release. At the 7 % floor the
  report names 30 of the 125 bird tracks and 3 of the 307 others (1.0 %, one-sided 95 % bound 2.5 %) under the stage's
  rule, 27 and 2 (bound 2.0 %) under the paper's; the rates are given by class, by distance, track length, size, contrast
  and frame rate, with the share answered beside each (helicopters 81 %, drones 96 %), and a stratum with under ten tracks
  states none. `tests/test_controls.py`, a new suite, judges 27 controls again from saved curves in minutes -- birds near
  and far, the Galileo flyers, PR135's flock, a drone, an airplane and a helicopter of the set, the balloon, PR23, PR055,
  PR071, the two strobe helicopters, a bird the test does not hear, a refusal -- each with the exact bound its outcome
  gives, and holds the false alarms of record as they are: DRONE_059 (a 10.00-Hz beat at a third of the frame rate, from
  held pictures the cadence test misses by 0.843 against 0.85) and HELICOPTER_024 (7.8 %) and _043 (21 %). Which golden
  checks are controls and which regressions is listed (B28: 20 and 18), the held-out third's ledger of looks is
  `tools/sweep/looks.tsv` (B17; its agreement 6.8 % against 6.3 %, -8.0 to +10.6 points, `tools/sweep/agreement.py`), and
  the exotica list says what the harness lacks. The set's labels were made differently by class (birds' and airplanes'
  boxes run on straight lines between key frames on 86-95 % of frames, drones' and helicopters' on 5 %).
- **The bird floor is set from a null, at a stated rate** (B24, E9, E19; method §43). It is **7 %** where 8 % had been
  chosen by eye: the smallest floor at which no more than 1 in 100 known aircraft, drones and helicopters of the labelled set
  are named a bird (the median over 2,000 resamples of their clips, by a rule written down before the set was measured
  again). The headline and the checklist say the measured rate -- "About 1 in 100 of them reach 7 %" -- where they said false
  alarms "stay under 8 %", which beats at 15 and 21 % did not. At one object in twelve a bird, a false bird now costs
  1.1-1.5 missed ones. Tested once, frozen, on the visible-band clips: 2 of 190 non-birds named, not shown above 1 in 100.
  `tools/sweep/floor.py` (set, test, challenger, strata) and `tools/sweep/pbo.py` (the probability of backtest overfitting,
  0.45-0.47 for the floor's exact value; a floor beats none out of sample on every half). The amplitude alone, at the same
  rate, does as well on this set, which lacks what the beat's tests are for. No reference case's call moves.
- **AARO's resolved cases, run blind** (method §46). The 14 known answers and 2 weak ones, run through the one press with
  only what each video and its public description give, the label held against AARO's by a rule fixed before the runs.
  Coverage 0 of 14 (exact 95 % interval 0-23 %): every one of the 54 objects says "No physical conclusion", since no
  description gives a field of view, a distance or a reference size. No disagreement and no false bird (the beat test had
  power on 9 of the 12 non-bird cases); on the two flocks the one press found no wingbeat on the one point it followed,
  where AARO cites one. The protocol was blind in its inputs, not in its operator, and says so. The 17 case files are in the
  data folder's `aaro/blind/`; `tools/aaro_blind.py` scores and reruns them; `test_golden.py --aaro` holds the scorecard.
- **The checklist says only what its tests decided** (the diagnostic-accuracy survey of 2026-11-07, Dx1 and Dx7; method
  §47). The beat row's "No" mixed a track that could have shown a bird's beat with one too noisy to (on the labelled set
  such a "No" was about three times as common on birds); it is "Can't tell" wherever a beat strong enough to name a bird
  would not have been found three times in four, and so is a refusal that had a measured peak. `run --track` no longer
  says "a person placed the marks by hand" whatever made the track: the track stage records who placed it, and the row
  says "Can't tell" where nothing does. `run --i-looked` is said as what it is. Integrity's row answers "Consistent" or
  "Inconsistent" with the camera's own picture, never a bare No: its checks have never been tried on a real insert. The
  track sheet carries the release's id, not its title (22 of PURSUE's 144 titles describe the object). On the 31
  reference objects: 29 chosen rows to Can't tell, 6 beat rows to Can't tell, 3 integrity rows to Consistent; no label,
  headline or number moves.
- **Reason codes and a grade beside the conclusion** (E7, S17, S20; method §47). At most four reasons, the heaviest first,
  each weighed on the labelled set where it can be (a bird named at the 7 % floor is 25 times as common on birds, 33 under
  the paper's rule); the beat's tests read one curve and count once; what no control population weighs says so. Beside it a
  grade from four of GRADE's domains, each computed -- risk of bias, inconsistency, indirectness, imprecision -- High,
  Moderate, Low or Very low (not GEIPAN's letters), in the report, the card's More, the lists of objects and the JSON; every
  reference object grades Low or Very low until its track sheet is looked at. A figure sets the case's beat against every
  labelled track's (`<case>_controls.png`), with "consistent with the birds", "not screened out" or "screened out" and its
  bound, and a caption saying that much of the gap is the set's birds being faint. The set's table ships with the package
  (`controls_beat.csv`).
- **"Clipped" is a flat top, and the clip's levels are a fact of the clip** (V1; method §50). A core is clipped where its
  top sits at the picture's ceiling or is flat (five of its 3 x 3 pixels within a code of the top, 50 codes over its
  surroundings), not where it reaches grey 250: 0.03 % of unclipped peaks drawn through x264 are called clipped, 89 % of
  peaks cut at 255 are caught (5-21 % of those cut below it before the encoder, which the technical README says).
  `Clip.luma`/`Clip.headroom` read the file's own luma with the headroom the extraction cuts; integrity's record and every
  envelope give the clip's levels. PR144's halo test goes from NO POWER to INCONCLUSIVE; no checklist row or conclusion
  moves. The blur test keeps the extracted frames: with the headroom a flock's other birds come in as the scene's points.

**0.4.x additions (session 18; method sections 42, 45, 48, 49 and 51).**

- **A phone's own record of its clip** (the phone scope's WP1 and WP4; method §42). `mcdonald phone VIDEO` reads an
  iPhone's `LivePhotoInfo` timed-metadata track with ffmpeg alone (found by its key, not a stream number) into
  `<tag>_phone.csv`, with what the file says of the device, lens, software and history. `run` reads it for a phone's clip
  only: the record is first checked on the clip's own pictures (where its zoom moves, the object's size must follow), a
  record that disagrees is said so and not used, and otherwise k comes from the lens and the zoom ("the phone's record", to
  within 10 %), the ledger's k is constrained rather than assumed, and the camera stage takes the zoom on every frame
  (`camera --phone`; `run --no-phone` refuses it). No reference case moves.
- **`mcdonald streak` reads the dash better** (F11, F12, F41, F51; method §45). Each frame is read less the median of its
  registered neighbours where that is quieter round the dash, and the dash is fitted whole -- the trailed point-spread
  function of Vereš et al. (2012) -- for its centre, length, direction, width and flux: 0.82 px rms on 609 drawn dashes
  where the half-peak length read 3.82. On PR43 the exposure reads 20.3 ms (was 16.3), its centres give T 0.72 ± 0.03 s
  against the track's 0.76, and its flux as a clock 0.39 s; the case file's track stays the measurement of record.
- **Which motion models survive, the jitter read without a model, and a traffic light for the suites** (E22, E6, E20;
  method §48). The model confidence set of a line, constant velocity in projection and a turn; where the track wanders about
  the best of them (44 of 45 recorded tracks) the paragraph says the set ranks the predictions and names no motion, since a
  straight track with a wander keeps the line only 63-95 % of the time at a stated 90 %; PR43 keeps the straight flight
  alone. The band's jitter from second differences beside its fitted nugget flags a beat the nugget took in (0.5 % of tracks
  with no beat flagged, 1 % stated). Forty checks on drawn data in the suites pass, warn or fail by a binomial zone, as the
  Basel Committee reads a bank's exceptions. A group member's position noise is read from its second differences too
  (the air-and-sea survey's W-TU11): rigid groups drifting across the picture had read "neither" or "shuffling".
- **Non-uniform motion dated, and set against the scene** (E2, E3, B16; method §51). A sudden change of velocity beyond the
  track's own wander is dated with an interval (a sup-Wald scan, its null drawn from the track's own covariance: 1.45 % at a
  stated 5 %) and set against the scene's change at the same moment: the camera's, not the camera's, partly, or can't tell.
  13 of the 31 reference objects gain a dated change: PR144's at 23.27 s is the camera's; on the other twelve the picture
  behind held still, so the report says it cannot tell. PR135's six change together at 44.556 s with no more spread than at
  ordinary moments.
- **The routes to k, held to finance's tools** (E14-E17; method §49). `slew` reads each claim's pointer as a stale price:
  its lead-lag behind the picture (Hoffmann, Rosenbaum & Yoshida on the pointer's own updates), the most turn it owed
  while it sat still, and Dimson's slope summed over a lead and a lag. A pointer further behind than the bootstrap's
  one-second blocks, or behind at all where Dimson's slope does not bear the claim out, is refused by name: PR051's dial,
  about two seconds behind, whose 7-14 s had claimed 2843 px/deg for a truth of 2230, and PR057a's 24.4-32.4 s window; a
  stall is said beside the claim and refuses nothing. Drawn with no lag, none of 248 claims was refused. A zoom state's
  windows, and a case's routes to k, are combined only where a chi-square says they agree (each slew window's error
  scaled by 1.5, read off the null); where they disagree the report says which and does not combine. `zoom --rd`
  measures a zoom as a regression discontinuity with placebo cutoffs; `scale.ladder` pools a sensor's zoom steps (the
  pointer sweep's 95: x1.9998 ± 0.3 %, x5.916 ± 0.5 %). No reference case's k or speed moves.
- **`python3 -m mcdonald`** runs the command line, as the console script does.

## 0.4.3 (2026-11-07)

Pushed on 2026-11-07 with 0.4.2 and 0.4.1 under it, which were cut on 2026-11-02 and 2026-11-01 and never pushed on their own: one
tag, `v0.4.3`, carries the three entries, and a `pip install --upgrade` from 0.4.0 gets all of it.

The scene under the sensor's pattern, from branch `scene` (the biology survey's B3 and B4, 2026-11-01; the maintainer's four decisions of 2026-11-02: the reading beside NO POWER, not in its place; `slew` takes it only on request; PR135 is not a null; one release for the pair). On 13 of the 14 reference case files `layers` says NO POWER -- the scene held still even over 30 frames -- and seven of them have a scene moving under the sensor's fixed pattern, which this release reads. The reference case files are remade after it (their layers stage gains `scene` and the line; no number of theirs changes from this release).


- **`mcdonald scene`: does the scene move under the sensor's pattern?** (method §41; the biology survey's B3 and B4.) A reading of whole
  blocks of 60 frames, with no templates, for the clips `layers` holds still. 0 of 326 blocks with no scene read (95 % bound 0.91 % a block);
  PR144 within about 1 % of its layers; PR41 and PR088 object 2 follow their pointers. `layers` runs it on a clip left still in over half its
  pairs, into `<tag>_scene.csv` and a `scene` field of its own, with each pixel's block mean taken out for a third pass of its templates.
  `<tag>_layers.csv` is the same to the byte, and `camera` and the rate against the background do not read it.
- **The report says it beside NO POWER** (the maintainer's choice, 2026-11-02): `run` asks `layers` for the reading, and where a block was read
  the layers stage has one more line, beside its NO POWER, not in its place.
- **`slew --scene-blocks` judges the blocks by a rule of their own** (`slew.fit_blocks`, method §41; 2026-11-02). `slew`'s fit is in places,
  with a check that the pointer's rate follows the scene's frame by frame, which a velocity held over 60 frames cannot pass: on the real clips it
  refused every window. With the scene from blocks each zoom state is now one window judged in rates -- each block's velocity against the
  pointer's rate over the same frames, the hold an offset, c the inverse slope with the pointer as the noisy side -- and the blocks' agreement
  with the pointer is tested against circular shifts of the pointer's block rates at a level of 1 in 20, which takes 21 blocks (42 s); fewer
  refuse by name, and so does a pointer the blocks do not follow. The claim then passes `slew`'s own checks (the pointer's lever, the
  bootstrap's width over the blocks, a hold allowed to drift, the tilt). Measured against drawn pointers with no relation to the blocks:
  on PR088 object 2's real blocks the shift test alone 4.5 % and a claim 0.6 %; on PR41's, whose velocity trends over the clip, the test
  alone 6.5-17.6 % and a claim 0-1 %; on a drawn scene of one slow swing the test alone 10-12 % and a claim 1.6-2.1 % -- the shift test
  holds its level on a series without a trend and is no guard on one with, where the hold's steadiness and the bootstrap's width hold the
  claim to about 1 in 100. Followed at a known c, the real blocks give it back within 2 % (median), nine in ten within 3-4 %. PR088 object 2 gives k cos(e) = 1,491 px/deg (16-84 % 1,284-1,802) from 51 blocks
  with no shift reaching their agreement (1,018 with no hold fitted; the survey's bracket was 652-1,349); PR135 refuses (11 blocks, and no
  agreement); PR41's case segment refuses (6 blocks); its whole clip's 33 blocks agree with the pointer (r 0.79, no shift reaching it) at 1,640 px/deg (16-84 % 1,422-1,996)
  and are refused because a hold allowed to drift moves c by 31 %: PR41's velocity trends over the clip, and a drifting hold cannot be told from it. A block over which the pointer turned unevenly
  (a pan reversing inside it, more than 3 scatters off a line) is left out and counted: the soccer camera's three readable blocks each hold a
  reversal and would read c two to five times wrong.

## 0.4.2 (2026-11-02; pushed with 0.4.3 on 2026-11-07, no tag of its own)

A correctness release, with nothing new in it (the review of 2026-11-02; ROADMAP decision 11). The biology and the single-camera
surveys of 2026-11-01 held the toolkit to known truth -- curves drawn under the null, dots planted in real frames and found by the
detector, aircraft of known range, a reference clip's own raster -- and found stated rates that are not what the code does, and
one reference case misread. Each item below says what the code said, what it did, and what it says now; every number that moves in
a reference case file is named, and the fourteen case files are remade once after 0.4.3.

- **The continuum null reads its noise curves as it reads the curve** (`flicker.continuum`, `_over_powerlaw`, `_gain`;
  `docs/method.md` §10, §39; the evolutionary biology survey's D1 and its check, 2026-11-01). The paper's null holds a
  peak against noise curves shaped to the curve's own continuum, but the curve has been through the stage's 0.5-s running
  mean -- a filter, 0.7 at 1.5 Hz and 1.2 at 3 -- and has its own peak left out of its own power-law fit, and the noise
  curves had neither: with the null true the stated 1 % ran at 5-7 % (drawn curves through the stage's own path, 90-600
  frames, white to 1/f and a random walk with grain), and 6 of the reference case files' 112 background apertures passed it,
  four of them at 2.25-2.5 Hz where the filter peaks. Now the power law is fitted with the filter's gain divided out, the
  noise curves are drawn from it and taken through the same running mean, and each is fitted with its own strongest left
  out: 0.8-1.4 % on white, pink and 1/f curves, about 2 % on a random walk with grain (the drift test's own kind of curve,
  and its trap: said in the docstring and §39), and 2 of the 112 background apertures, neither of them noise (a
  neighbour's beat in each). Every object's ratio is unchanged; its `p` and 99 % level move (about 5.2 on 150 frames, where
  it was 4.2), so every reference case file's continuum row moves, and five of the 28 reference lines, at ratios 4.8-5.7,
  are no longer lines at 0.01: PR077 object 2 (p 0.001 -> 0.025), PR097 objects 3 and 4 (0.000 -> 0.014 and 0.011), PR099
  object 2 (0.004 -> 0.022) and PR141's infrared object (0.008 -> 0.024); PR097 object 8 (0.003 -> 0.008) keeps its line.
  Under the paper's rule, which the case files use, PR097 object 4, PR099 object 2 and PR141's infrared object lose the
  beat and the headline ("Beats like a bird" -> "No physical conclusion"); PR077 object 2 keeps its bird from its clearest
  2-s window (10.3 Hz, two windows apart agree) where the whole track no longer passes; and PR097 object 3 goes from Partly
  (7.7 % over the whole track, under the 8 % floor) to a bird at 6.5 Hz from its clearest window, as the stage's rule
  already had it. At the remake of the case files with 0.4.3 (2026-11-02) a sixth line moved that the reading of the 28 lines had
  not named: PR097 object 7's whole-track 6.63 Hz no longer passes, its clearest window's 4.84 Hz stands 4.3 times over the
  continuum (a chance of 0.059 where 0.0042 is needed), and under the paper's rule it too loses the beat and the headline; so
  four of Table 1's lines lose "Beats like a bird" in the remade set and one gains it (the files' README has the table). Under the stage's rule, whose whole-track test is the drift test, nothing moves; the one-stretch rule
  (§13) is stricter by it. `CONTINUUM_P` stays 0.01 and now means it. Tests: `tests/test_measurement.py` (the continuum
  test's red curves now go through `deviation`, as every curve the stage hands the null has).
- **The drift test's words say its measured rate** (`flicker.DRIFT_RATE`, `drift_rate_said`; the module's item 5,
  `drift`; `docs/method.md` §39; the genetic survey's null census and its check, 2026-11-01). The stage's whole-track
  rule keeps a beat only where it stands over its own slow wander further than 99 in 100 drawn curves of that wander and
  jitter do -- and on empty apertures in real frames, paths that follow nothing through 116 release videos judged as an
  object is (3,092 apertures of 150 frames), 8.7 % pass that line: 9.3 % of those whose strongest lies under 4.5 Hz, 4.3 %
  of the rest; the check's 286 apertures in 13 PURSUE videos, 7.3 %. Not the null's reading (curves drawn from an
  aperture's own fit pass 1.3 %) but the curve model's shape: a real curve carries a hump at 1.5-4.5 Hz, scene texture
  swept through the aperture, that a random walk and white grain do not draw, and each aperture's hump is its own. An AR(1)-coloured jitter chosen per curve was tried and refused (5.9 % against 7.3 % on the check's 286 apertures; §39).
  The whole stage rule, ABOVE beside it, passes 0.36 % of them (every one at 1.5-2.8 Hz) against the 0.15 % stated from its
  background apertures. The test is unchanged; wherever its line is printed -- the stage's line for each curve, the
  finding of a beat the rule kept -- the measured rate for the beat's band stands beside it, and the docstrings and the
  method that said "1 in 100" say what is measured. No reference case's call moves; their flicker findings gain the clause.
- **The picture's stretch is a known: `--pixel-aspect A[,FROM]` on `run`, `kinematics` and `report CASE`** (`stages.KNOWN`,
  `kinematics.AngularScale.aspect`, `kinematics.square_along`; `docs/method.md` §40; the single-camera survey's F1 and the
  biology survey's B8, 2026-11-01). A file whose raster was stretched to fill the frame has two scales, and one k on it read a
  rate across the picture as the stretch times what it is: PR113's file holds a 720x480 tape picture shown as 1920x1080, the
  Technical Note's 35.4 px/deg was read up the ladder, and the object crosses the frame diagonally, so `run --graticule 35.4`
  printed 121°/s and a field of 54° where the picture supports about 103°/s and about 40° by 30°. The stretch -- how much
  wider than tall the file draws a pixel, and after a comma where it was read (`symbols`, `scene`, or one's own words) --
  now makes k the scale up the picture in square pixels (the angle marks' scale as read; a field of view over W / a), the scale
  across a k, the field of view both ways, and the turn rate from the track's own direction, hypot(v_x / a, v_y) / k; a width in
  the file's pixels is between p / a and p square ones, so the first line's distances for a bird, a balloon and a jet span both;
  the rate in the file's own pixels stays beside it (PR113's 142 px/frame is that number). The report's summary, ledger and
  bottom line and the window's card say the stretch and its source. Nothing moves on square pixels: a drawn 45° track on a
  picture stretched by 4/3 comes back at its rate exactly, one k reads it 1.18 times high, and a = 1 leaves every field
  as it was. The camera stage, which took a pixel aspect of its own, is handed `run`'s; the horizon step's k is in square
  pixels; the lens's term and a stretch together are refused. **Nothing measures the stretch yet**: the surveys read PR113's
  twice -- the display's rotating ladder draws 1.753 wide to tall (322 frames, 95 % 1.751-1.755) at 36.25 px/deg up the
  picture, and the scene under a real roll 1.29 (15 pairs, 95 % 1.24-1.38; known stretches come back within 2 %), the 4/3 of
  a 4:3 picture in 16:9 -- two stretches of two things, rebuilt to the digit this session; a reader held to a null for each
  route is an open row. Exercise 3 (`docs/exercises/03-pr113.md`) now gives the marks' scale and the stretch
  (`report CASE --graticule 36.25 --pixel-aspect "1.333,a 4:3 tape shown in 16:9"`) and quotes what the report then says;
  `tests/test_golden.py --exercises 03` runs one page. Tests: `test_the_pictures_stretch_known` (test_reduction),
  `drive_known_afterwards` (test_cli).
- **The speed band held to planted truth: the detector's memory is not the object's path** (`kinematics.MEMORY_FRAMES`,
  `_read_band`; `docs/method.md` §32 "The detector's memory"; the biology survey's B2 and the single-camera survey's F9,
  2026-11-01). Straight dots of known speed planted in real decoded frames of six PURSUE clips, encoded with each clip's own
  settings and found by the toolkit's centroid (111 tracks, 222 velocity components) showed the band's net velocity holding
  the truth within its stated ±1.96 errors 68 % of the time, where white jitter of the same size gave 96 % and the same
  errors shuffled in time 97 %: the detector's error has a memory of about two frames (lag-1 autocorrelation 0.38 -- the
  picture's blocks drag a centroid), REML gives it to the Matérn as a wander of 1-9 frames' range, and the net velocity,
  read on the latent path, then counts it as the object's own and states an error from the nugget alone; the wander's
  likelihood gain called 88 % of those straight dots "not constant". A coordinate whose fitted range is under
  MEMORY_FRAMES (10, and the wander's sill no larger than MEMORY_SILL_PX, 1.25 px) is now read as the line's: the GLS slope under the fitted covariance with the larger of its error
  and the ends', at every frame and in the net velocity; its change of velocity nil, so E12's bound speaks for it; its
  wander no evidence that the velocity changes (`dlnl_path`). On the planted dots held apart (PR077, PR055) the coverage
  is 94.3 % (calibration clips 93.2 %, all 93.6), and 9 % of the straight dots are "not constant". On 19 Galileo aircraft against
  ADS-B (33,609 frames at 60 fps, the truth in pixels with the lens inside it) the band's rate frame by frame held the
  truth 63.5 % of the time before and 95.4 % after (held-out aircraft 96.4 %): the shortfall was in bands under 0.15 px/s, where the model's smoothness and not the data set the width, so the band states no rate at a frame finer than RATE_FLOOR, 1/60 px a frame, added in quadrature (1 px/s at 60 fps: a floor, not a factor); on the planted dots at 30 fps the floor costs a little width (99.8 % frame by frame; 96.9 % without it, 97.7 before the change). The recorded tracks' wanders have
  ranges of 12 frames and up, so no reference case's band moves: the fields `memory`, `dlnl_path` and `rate_floor_px_per_s` are new, the per-frame sds carry the floor (visible only where a band was under 0.5 px/s wide at 30 fps: none of the 30 recorded), nothing else in them changes; the golden FLIR1 exit and fields tracks' y (the 2007 MPEG's field alternation, ranges of 5 frames with sills about 1 px) are read as the picture's, and PR051's drift (a 6-frame memory with a 14.6-px sill: the pointer stepping as a held picture catches up) is not, by the sill guard. Tests: `tests/test_reduction.py` (a drawn short-memory wander read as the line's and constant, its
  velocity held; a wander of the path's length untouched; K8, E1, E12 as before).
- **The speed along the path beside the net speed** (`kinematics.speed_band`'s `v_path_px_per_s`, `v_fast_px_per_s` with
  their errors, `path_said`; `report_qt.path`; `figures.speed_band`; `docs/method.md` §32, §36; the biology survey's T3).
  The report's "on average over the stretch" was the net displacement over the time, which on a path that doubles back
  is far under the speed along it (PR41: 0.8 against 40 px/s; over 1.5 times apart on 25 of 44 recorded tracks). From
  200 paths drawn from the band's posterior (seeded; the continuous-time speed of Noonan et al. 2019) the band now gives
  the speed along the path, the distance travelled over the time, with its error, and the fastest; where the speed
  changed, the stage's line, the summary's speed row, the bottom line, the window's card ("Along its path") and the
  figure name both speeds, "along its path" and "start to finish". `Reduction.upper_bound` takes the path speed where the
  speed changed (it took the net: PR077's object 1 ran near 150 px/s along a path whose net was 5.7); no reference case
  carries `--range-max`, so no reference bound moves; the farthest-range test's PR051 drift bound goes from 5.7 to 9.9 m/s on average (its path is 1.73 times its line start to finish), its fastest 32 m/s as before (`tests/test_reduction.py`, re-pinned with the reason). On drawn tracks the path speed's 95 % holds the drawn path's speed about nine times in ten
  and reads 1.00 of it (0.994 at the median of 24); the drawn fastest reads 1.025 times the kriged mean's fastest at the median on the 45 recorded tracks (1.069 at most), nearer the truth, which the kriged mean's reads low; on the planted straight dots the path speed reads 1.0000 of the truth and its 95 % holds it 94.9 %.
- **The speed in body lengths is not free of the camera's own motion** (`stages.platform_of`, `stages.kinematics(layers=)`;
  `kinematics.body_lengths_per_s`; `docs/method.md` §5; the biology survey's Part 3 §1). The row was said to need no k, no
  R and no field of view, which holds for the object's own motion; the image rate also holds the platform's, and a thing
  still in the air seen from a camera moving at v_own crosses at v_own sin φ / R over a size D / R, so the row reads
  v_own sin φ / D for it: a 1-m thing seen from an aircraft at 100 m/s scores up to 100 lengths a second standing still
  (PR135's "28.6 body-lengths/s" is 212 px/s over 7.4 px, the 212 px/s the paper reads as the aircraft's). The row now
  says it is the object's own only where the camera does not move through the air, and is NO POWER with the arithmetic
  where the camera's speed is given (`--own-ship`), where the layers step saw the background move across the picture, and
  where the picture behind the object held still on screen (a camera following it looks so, and the step cannot tell);
  the number stays in the fields with `platform` beside it. No reference case gives a size, so none changes.
- **`drift`'s refusal from the aircraft's own track reads the rays, not where the fit landed; too few readings and a
  model wind above its levels say so** (`drift.unfixed`, `path_off_line`, `range_bound`, `model_test`, `boot_kept`,
  `track_winds`; `docs/method.md` §34; the single-camera survey's F4, F5 and F6, 2026-11-01, fixed 2026-11-02). T1
  and T2 from `--platform --los` refused a path only where two bootstrap errors of its velocity were over 5 m/s, and on
  a cost flat along range -- a straight-flying aircraft -- that reads where the 28 starts landed: a landing beside the
  aircraft at 1-2 % of the true range gives a velocity nearly the aircraft's own with a small error in m/s, since the
  error scales with the range found, and it passed on 2 of 196 drawn straight flights at the default sigma (1.0 %) and
  2 of 30 at a tighter one (6.7 %), T2 then calling a body drifting with the wind a flier. Two gates now come before
  any number of the fit (Park et al. 2015, Result 2; Nardone, Lindgren & Gong 1984): the aircraft's path must leave a
  straight line at a steady velocity, in the fit's own coordinates, by more than twice its readings' a priori error
  (10 m; a straight flight's own rounding at an arcsecond leaves under 10 m, the path gate), and the Cramér-Rao bound
  on the logarithm of the range at the fit must be under 1 (the range known to better than a factor e). With them no
  drawn straight flight passes (NNN of NNN, the same trials; the rounding null and the turns in the session's notes);
  T1 and T2 read "cannot say" with the reason, and the old 5-m/s rule stays behind them as the rule that T2 cannot
  tell a drifter from a slow flier. An F test of an accelerating path over the straight one is reported (`model_p`)
  and not yet a refusal: Puerto Rico's lanterns give p = 0.054. The stage admitted 6 readings while its bootstrap
  fitted only resamples with 8 distinct ones, which 6 or 7 never give, and crashed on the empty sample (IndexError);
  8 readings kept 4.8 of 2,000. The least number of readings is now computed from the resamples kept (9: the first to
  keep the 20 the 5th and 95th percentiles need; `READINGS_MIN`, `BOOT_MIN`), fewer read "cannot say" saying how many
  are needed and why, and `fit_track` on fewer gives the covariance's errors instead of an error. A model wind file
  counted at any height (a file with only a 100-m level counted at 3,960 m, and T2 passed or failed on it); it now
  counts within its levels and, held beyond them, only within a factor of 4 of the object's height above the model's
  own ground, as an observed level does, the note naming the heights it covers, and T2 with no wind at the object's
  height says which files fall short. The known answers do not move: Puerto Rico's path leaves a line by 855 m, its
  bound is 0.0025, all 2,000 resamples are fitted, the same 14 winds count and T1, T2 pass as before; Yemen and Santa
  Barbara do not use the track route. Tests: `tests/test_drift.py` (a straight flight fixes nothing whatever the fit's
  error says, the survey's own phantom trial, the rounding null, a 30° turn; 5-8 readings; a 100-m file at 400 and
  3,960 m).
- **The checklist's camera row says Can't tell where the picture held still on screen** (`report.Case.checklist`;
  `docs/method.md` §38). It answered "Did the camera move while it filmed this?" with No wherever the layers step found
  the picture held still in nine of ten frame pairs, and Partly down to one in ten. That held-still share is the step's
  own no-power, not a still camera: a camera following the object over a sky with nothing to read and a camera held
  still over a slow scene both hold a match at zero, and the step cannot tell them apart -- which is why 0.4.1's first
  line says such an object moved "as the camera held it" and that its motion against the background is not measured.
  The row now agrees with that line: Can't tell, with why ("the picture behind the object held still on screen, which a
  camera following it over an empty sky and a still camera over a slow scene both give, so whether the camera moved is
  not measured"; where some pairs moved, how many), wherever the step's no-power holds (above half the pairs); Yes where
  the background moved across the picture; Partly where it held in half the pairs or fewer. It never answers No, since
  the step has no reading that tells a scene that held from a following camera over nothing. On the reference case files
  the row moves on 25 of 31 objects in ten of the fourteen files (PR135's six birds among them, from No; PR44 and PR097's
  flock from Partly); PR144, PR149 and PR43 keep Yes, PR113 Partly. No number changes.

**ROADMAP:** no row of its own (a 0.4.1 defect found 2026-11-02); if the coordinator wants one: "done 0.4.2".

**Decisions for Jacob.**
1. The new words on the card's camera row (above). My recommendation: as written; they repeat the first line's reason.
2. The "moves" row still answers **Yes** to "Does the object move against the background?" with "about 103 pixels a
   second across the picture, which held still" where the camera's row now says Can't tell. The number is the object's
   motion in the picture, as the camera held it, and the first line says its motion against the background is not
   measured. Candidates: (a) leave it (0.4.1's choice, the pin says so); (b) Yes with "across the picture, as the camera
   held it" (the first line's words); (c) Can't tell, "it moves about 103 pixels a second across the picture, but the
   picture behind it held still on screen, so its motion against the background is not measured" (the same shape as the
   camera-moved case). I recommend (c) for consistency with the question asked, but did not build it: it changes PR135's
   answer on a row the brief did not name, and the words are Jacob's.
- **`mcdonald streak` no longer calls a flicker inside the frame; it reports the beads as a reading and says why**
  (`streak.measure`, `NOISE_ALONE`, `STEADY_PASS`; `docs/method.md` §30; the single-camera survey's D4 of 2026-11-01,
  F2). The stage searched a fast object's dash for beads -- a flicker far above the frame rate -- and called the peak of
  the dash line's power over the lines beside it a flicker under a false alarm of 1e-3. Measured on steady dashes drawn
  with no flicker, that test passed 7-9 % with no codec and, through x264, 29-52 % on real PURSUE frames and 80-98 % on
  a flat sky (CRF 18-28; the survey's 7.5 %, 28-47 % and 77-100 %): a codec flattens the lines beside a dash to nothing
  and textures the dash, so a steady dash reaches any ratio a flicker does (13 to 1,500 times through CRF 23). The
  brief's remedies were built and measured: the spectra are now summed in hertz, each dash's by its own speed, which is
  right and stays; the band's top moved off the blur's roll-off changed nothing (the passes follow the edge); and a null
  drawn in the clip -- eight steady dashes beside the object through the clip's own encoder -- left 91-97 % of steady
  dashes passing on a flat sky, because a second encode of decoded frames at the first stream's bit rate runs at a far
  lower quantizer and draws clean dashes (the first encoder's operating point is not in its output). So the report now
  gives the beads' spacing, rate and power over the lines beside them with the chance noise alone would give it, says
  that is a reading and not a flicker found, and says under no power that a flicker inside the frame is not decided,
  with the measured shares. PR43: at its scene's blur no light curve and no beads read, before and after; at an assumed
  2 px "none" before (2.6 times, 0.08) and "nothing stands out" after, the same numbers. Tests: `tests/test_streak.py`
  (steady dashes through x264 reach the old test's 1e-3 on most and the stage calls none; the blink is read at its rate).

## 0.4.1 (2026-11-01; pushed with 0.4.3 on 2026-11-07, no tag of its own)

A checklist of the tests under the conclusion, the parallax ladder's still row after N. Long's revision, and a phone's video running with the report saying whose motion a rate is. The last is from a witness's iPhone clip filmed from a fishing boat (Rhode Island Sound, 2026-06-12: the uap repository's `analysis/methods/mcdonald_phone_video_scope.md`, its WP0, WP3's report line and WP8), and an agent's tester feedback on it of 2026-10-28; and `drift`'s Test 4b with its error and reach from the track's own speed band (merged from `drift-band`, 2026-11-02).

- **`drift`'s T4b reads the remains' fall from the track's own speed band** (`drift.fall`, `drift.test_wreck`;
  `docs/method.md` §34; from the Yemen case's band study, 2026-11-02). The remains' screen-down acceleration was a
  quadratic in time with a moving-block bootstrap error (blocks of 15 frames), and the reach -- the size under which a
  falling wreck of every body is excluded -- g cos δ over a + 3σ. The 0.4.0 speed band on the Yemen remains found a
  wander with a range of 0.55-0.75 s, longer than the 0.5-s blocks, so the bootstrap's error was too small: the band
  reads -0.17 ± 0.14 L/s² down the screen against the quadratic's -0.08 ± 0.06 (2.4 times the error), and its 95 %
  bound on a steady change of speed it could have missed, 0.45 L/s² either way, puts the honest reach at 16.5 m
  ("about 17 m"), not 75. `fall` now returns the band's acceleration, its sigma, that bound, the wander's range, the
  nugget and the backtest's light beside the bootstrap's numbers (the bootstrap's draws are unchanged, so a figure
  script that reproduces them still does); `test_wreck` takes the band and sets the reach by its bound where it gives
  one (`reach_by`), by a + 3σ where the band saw the change or the track has none, and its reading gives both
  accelerations and the bound in plain words. The pass threshold is 10 m (`WRECK_MIN_M`, was 20): the test asks
  whether the remains sink steadily, and a 16-m reach excludes every drone and every bird there is; the fail rule keeps
  its 20-m constant apart (`WRECK_FAIL_M`: the remains accelerate down at half a 20-m body's fall or more, three errors
  clear) and is tried first, so that a measured fall is never called a steady sink (a 20-m body's fall measured to
  0.05 L/s² reaches 14 m and would otherwise pass). T4a reads the pieces' speeds against the remains from the
  difference tracks' bands too (`pieces_band_L_per_s`: 0.79 and 0.62 L/s on Yemen against the lines' 0.82 and 0.68);
  its rule stays on the lines'. The Yemen known answer: T1, T2, T3 and T4a unchanged to the digit, every test passing,
  T4b now "no falling wreck of any body smaller than about 17 m"; the synthetic 5-m wreck still fails and the steady
  sink passes. Tests: `tests/test_drift.py` (a drawn track with a slow wander, whose band's bound outreaches three of
  the bootstrap's errors; the thresholds; the known answers' new numbers).

- **The checklist under the conclusion** (`report.Case.checklist`; a tester's ask, 2026-11-01: a report "that even an
  undergraduate student can understand"). Under the conclusion's sentence the report now has a table of the tests it
  rests on, each a question in plain words -- did the camera move, does the object move against the background, does it
  fly straight at a steady speed, is it coming closer, does its brightness beat as a wingbeat would, could something else
  beat like that, does it flash like an aircraft's light, is it one thing, does anything move with it, was it added to the
  video, can a real speed be worked out, did a person pick it out and check the track -- answered in a word (Yes, No,
  Partly, Can't tell, Not yet) with why in a line. A test that could not decide answers "Can't tell", never "No"; a row's
  stage that did not run has no row; a bend or a change of speed seen on a camera that moved says so. The paragraph of
  reasoning is folded under the table (on the page, in the PDF and on GitHub), not gone. The window's report card has the
  same rows, the answer in a word and why in the tooltip, above the numbers; `mcdonald run --json` carries them as
  `results.checklist`. The rows are read from the stages' fields, so a case file from an earlier version gets its
  checklist when its report is opened or written again.
- **The parallax ladder's still row gives the least speed an object needs of its own** (`kinematics.parallax_ladder`,
  `closest`; `--ground-speed` with `--own-ship`). With the aircraft's heading and the ground motion's bearing, a still
  object fits only where the ground motion runs exactly against the heading; where it does not, the row gave the k that
  made |v_G + (k - 1) v_A| smallest and that number as the speed still needed, which is k times a speed: on PR043 with
  N. Long's homography (ground point 2350 m/s toward 69.6 deg, aircraft 76.4 m/s on 272.7 deg at 1611 m) it printed
  922.9 m/s. It now gives the least |v_G + (k - 1) v_A| / k and where: 29.1 m/s of its own, 1564 m up. Where the ground
  moves the aircraft's way and faster than it (PR023 on the same table), there is no nearest height: the speed needed
  falls toward the aircraft's own the nearer its height, and the line says so. The ladder's other rows were right and
  agree with Long's revised paper (2026-11-01): 30 m/s at 1559-1568 m, Mach 1 at 1338 m, Mach 5 at 432 m, where his
  figure has a bird above 1560 m, 1340 m and 434 m. No reference case file carries a ladder, so none changes.
- **The parallax ladder takes the aircraft's climb** (`--own-ship SPEED,HEADING,ALTITUDE,CLIMB` with the new
  `--line-of-sight BEARING,DEPRESSION`, on `run`, `kinematics`, `report CASE` and the Measure form). A ray through a
  thing at a fixed height sweeps the ground as the aircraft climbs or descends, as if the aircraft moved
  climb / tan(depression) faster along the line of sight; the ladder now takes the aircraft's speed with that added,
  says so, and says why where it cannot (no line of sight, or no directions). A still thing simulated under PR043's
  descending camera is found still and at its height within 2 m, where the level ladder put it 53 m too low looking
  ahead or made it move 12.7 m/s looking aside. On PR043 itself, with Long's descent (5.01 m/s), his slant range for
  the depression (17.9 deg) and the video's own north pointer for the bearing (270 deg), the least speed of its own is
  24.0 m/s at 1573 m, where his figure's curve ends at 23.5 m/s at 1570 m and the level ladder stops at 29.1; and his
  cut-off's speed (658.5 m/s) comes at 1133 m, where his text has 1132 (level: 1126).
- **A clip coded on its side opens upright** (`clip.probe`, `clip.rotation`, `clip.turned_on_its_side`). A phone held
  upright codes its frames on their side and writes a display matrix beside them; ffmpeg turns them as it decodes, but
  `probe` took the coded size, so W and H were each other's: `layers`, `tether` and `symbology` broke on the shapes,
  the track sheet was laid out on its side with its ring in the sea, and `--fov` was spread over 1920 px in place of
  1080 -- a silent 1.78x in every angle. The size is now the decoded frames' (a swap within a degree of 90 or 270, as
  ffmpeg's autorotate transposes), with `coded_width`, `coded_height` and `rotation` kept for the record; the player
  and the window follow. The test draws the same frames upright and on their side, both ways round, with the matrix
  set on a stream copy (`-display_rotation`; a re-encode drops it), and holds the frames, the linked track, the
  player's pipe and a click in the window to the upright twin.
- **`integrity` reads a stream with no codec name** (an iPhone's `mebx` timed-metadata tracks, a timecode track):
  `container_report` names it by its tag and records the rotation and the coded size. It crashed on it, and under
  `run` every iPhone clip lost the integrity test as "no power".
- **A rate over a picture that held still is the camera's hold** (`report.Case.behind_held_still`). Where the layers
  step says the scene held still on screen -- its own no-power: a camera following the object over a sky with nothing
  to read, and a camera held still over a slow scene, both look so, and the step cannot tell them apart -- the first
  line said "the object moved about 0° a second in the image" and "against the background", while the object moved
  98 px/s against the clouds. It now gives the rate in the picture as the camera held it, says that its motion
  against the background is not measured, builds no speed across the line of sight on it, and gives a rate under a
  degree to its figures (`_deg`); the bottom line says the same of the layers' number. Ten of the fourteen reference
  cases carry that no-power: their first lines change in wording and in no number, and the PR44 and PR135 exercise
  pages quote the new clause.
- **`run` pages its track sheet** (`tracksheet.paged`): ten columns and at most eight rows a page, so each page can be
  checked on one screen at full size ("an 11520 x 4254 JPEG can't be checked on one screen"); the verify step names
  the pages and its Reproduce line carries `--cols 10 --pages N`. The command line's own `tracksheet` keeps its
  30-column sheet and the window its own layout.
- **`symbology` asks first whether there is any overlay**: with the survey's static masks under 0.1 % of the picture
  drawn (`OVERLAY_MIN`; a burned-in display is a few percent) it says "no overlay" as no power and reads no frame for
  a pointer, where it had fitted one 646 px from the boresight to whatever was warm; the command samples a dozen
  frames to ask.
- **The other things a size is held against** (`figures.BANDS`): a party balloon or a small drone (0.3-1 m), a
  balloon cluster (2-5 m) and a tethered aerostat (5-20 m), in size order between the bird's band, the weather
  balloon and the fighter jet, in the headline's "what it is depends on how far away it is", in the kind a measured
  size is near, and on the size-and-speed figure. PR113's exercise line changes by those clauses.
- **`audio --platform aircraft|boat|car|hand`**: on a boat or in a car a steady series is read first as the platform's
  own engine, a four-stroke's firing rate cylinders x rpm / 120 (`engine_speeds`: 33.76 Hz is 4 cylinders at 1013
  rpm, 6 at 675, 8 at 506), a 400-Hz supply as an inverter's or a generator's, which is no clock, and no airframe is
  matched on its blade-pass alone; an airframe's second tone names it whatever the platform. The default is an
  aircraft for a catalog record and otherwise not given, when both readings are named. A boat's diesel had been read
  as "a propeller" and its supply as "an aircraft's 400-Hz power" with "tape-transport sidebands".
- **`docs/agents.md` says how to write what was found**: in the words of the person who asked for a report an
  undergraduate could read, the short answer first and every symbol said in words.

## 0.4.0 (2026-11-01)

ROADMAP 0.4, the first session (2026-10-27): finishing k from the camera's own motion, PR051 as a known answer, and
four bounds on range or the exposure that need no motion.

- **`zoom` finds a zoom with no blank over streaming ground** (method §17; from PR062 in the metallic-orb class study,
  2026-10-28). Frames where the whole picture changes at once (1.8 times the usual change or more,
  `zoom.change_spikes`) are candidates beside the level's and contrast's steps; the number fitted grows with the clip
  (24, or 12 a minute); and frames given with `--events` are always fitted (they went through the same cut by size). On
  PR062 the first pass missed all three zooms in, and its chain put two minutes at twice the field; now all six are
  found with nothing given.
- **`symbology` fits the circle the pointer draws** (method, `mcdonald symbology`; from PR062, 2026-10-28). An MTS-B's
  "N" need not circle the reticle: PR062's circles a point 8.6 px off it, and the stage called its frames mislocated
  and read its angles 3 degrees off. Where the glyph sweeps 60 degrees or more its circle is fitted, glyphs off it
  dropped, and the angles read about its centre; `--pointer-centre X,Y` carries a centre to a clip of the same display
  whose pointer sweeps too little.
- **`focus` reads a dark object's edge** (method §28, the ideas bank's MEO11 and the near-thing test of V5; from the
  metallic-orb class study, 2026-10-28). A dark object wider than its points, or clipped at black, was refused ("its
  sharpness bounds nothing"); its edge is now fitted with an exact blurred disc, across its motion, the clipped core
  left out, and bounds the defocus disc two ways (assuming nothing of the camera's blur; assuming the points'), each
  divided by the square root of how far its core reaches toward black, so that a small thing far out of focus -- a
  faint disc with a sharp edge -- cannot pass as in focus. `--ground-scale M_PER_PX` gives r/R >= 1 / (1 + b s / A)
  with no k. A bright object wider than a point still gets no bound, and says why. Checked on rendered frames and on
  the Middle East Object's stare (sigma 1.27 px against the hand fit's 1.30-1.42). With no points in the scene (ground
  streaming past smears them all) the edge is read all the same and the bound assuming nothing given.
- **A zoom with no blank** (`mcdonald zoom`; `docs/method.md` §17). An electronic zoom, and the ATFLIR's, steps the
  picture's level or contrast instead of blanking it: those steps (`events.picture_steps`, now shared with `mcdonald
  events`, and `zoom --events CSV`) are fitted as a burst is, and one the fit measures is a boundary of the zoom states
  (`kind` "picture"); one it does not is kept apart, the scale taken to hold across it. PR051's leak (an MTS-B going
  from 2X to ULTN with no blank) measures x0.498 against its data bar's x1/1.999.
- **A zoom fit's window variance in float64** (`forensics._zoom_score`). Over a frame flat in part (a title card, a
  black bar) the float32 sums left rounding in place of the variance: a card "matched" a scene at ZNCC 1551 on PR051's
  upload, and a replay came out a step of x4.165. A window with no fine detail is now no match.
- **A marginal zoom fit confirmed by pairs further out** (`zoom.confirm`). A fit that lacks only its lead over the best
  scale a quarter or more away is fitted again from the pairs 1-3 frames further out, and is a step where two of them
  pass every rule on their own, within 3 % of it and of each other. AARO's Puerto Rico switch at 142.6 s (x1/3 by its
  readout) is now a step; PR27's 89-s haze, which fits x3.127 from every pair to the digit, stays unknown.
- **A strong zoom fit leads a weak rival** (`forensics.ZOOM_STRONG`, `ZOOM_ZNCC_LEAD`): a fit at ZNCC 0.5 or more leads
  a rival that matches at under half its ZNCC, whatever their prominences (PR144's x5.8 at 0.85 against x2.8 at 0.35).
- **`integrity` fits the zoom across each transient with `zoom_fit`** (the maintainer's decision, 2026-10-27), as
  `mcdonald zoom` fits a burst, in place of `zoom_ratio`, which looked within 60 px of the boresight and read x1.0 at
  every switch of the Puerto Rico clip. Its report and record now say step x s, no change of scale, or not measured and
  why: integrity's records change, the reference case files' among them when they are next remade.
- **`camera` reads `zoom`** (`camera --zoom JSON`, and `run`'s camera stage where a `<tag>_zoom.json` is in the case's
  folder or the whole video's): the steps the picture measured inside a track are taken out of it at the imagery's
  ratio and checked on the object's size; bursts with no measured step are the camera's events.
- **`slew --hold-rate`**: the platform's share of the pointer's turn, known from its own motion (a ground point's
  bearing rate, v_perp / R), taken out of the pointer, so a steady pan gives k on a moving platform too (it is otherwise
  the hold's twin). PR051's NAR stretch, whose k the data bar gives (2230 px/deg), still gives only a floor (1087): its
  scene moves in jumps and most pairs are held.
- **`slew`**: one row a zoom state where a "no step" burst joins two stretches (their windows had been counted twice),
  its figure one row a state under a row for the clip (PR27's was 64 inches tall), and a zoom state shorter than half
  a second no longer stops it (PR40's, five frames).
- **`mcdonald horizon`** (§27): the sea's horizon as a ruler. From a point on the horizon the line is found and followed
  along the track; with k and the camera's height, a thing seen against the sea below it is nearer than where its line
  of sight meets the sea, and a thing above it at least as high as that line's lowest point, each at the conservative
  corner of its band (refraction 0 to 0.25 among it).
- **`mcdonald focus`** (§28): sharp means far. An object as sharp as the scene's own points, with the sensor focused far,
  is at least D / (the defocus disc it could hide) away; with no pupil given, the optics' diffraction bounds D.
- **`mcdonald haze`** (§29): the air as a ruler. A dark object's contrast against its sky, in linear light (BT.709),
  bounds its range with the reported visibility or something dark at a known range in the frame (Koschmieder; good to
  a factor of about four, as Hartmann found).
- **`mcdonald streak`** (§30): the dash a fast object draws in one frame, read along the track: the exposure, and a
  flicker far above the frame rate as beads along the dash, tested as an F ratio against the lines beside it.
- **The four unknowns** (the second session, 2026-10-28; ROADMAP 0.4, objective 6, as a first form): every report has a
  table, after the summary of variables, of k, R, θ and v_own -- constrained, assumed (a field of view with no source),
  bounded or missing, by which route, and the datum a release could give that would close each -- in its JSON too
  (`ledger`). `horizon`, `focus`, `haze` and `slew` take `--case CASE_JSON`, which records their measurement in a case
  and writes its report again: a ceiling on R from the horizon or the haze, a floor from focus, slew's c (a floor on k).
- **`layers`: a picture that repeats and catches up** (the maintainer's choice, 2026-10-28; `docs/method.md` §3). A
  pair held still inside a hold of a repeated picture was measured again over a second and took the second's mean
  rate, counting the catch-up steps twice; where a window's held pairs and catch-ups alternate (four switches or more,
  catch-ups 12 px or more over k frames), a held pair whose own field agrees on zero is unmoved: zero, not measured
  again (`layers.repeating`, how `UNMOVED`, `held_still.unmoved_share`). And a pair called held whose own field, zero
  allowed, agrees on a shift past the zero zone keeps it (`held_but_moved`): a streaky scene moving along its streaks
  keeps its same-place correlation high. PR135's island is the same to the byte; on PR051's upload (`--k 2 --step 2`)
  12 % of pairs reach a consensus (5 % before), the rest short of templates. `layers`' cached templates are measured
  again once (the cache's name has the rule in it).
- **A tinted grey picture is not masked by its tint** (the fourth session, 2026-10-28; `forensics.static_masks`:
  `tinted`, `TINT_FIFTH`, `TINT_SHARE`; method §3). A colour cast that follows the picture's own brightness (most of
  the brightest fifth of the sampled frames carries it) is the picture's tint, not coloured symbology, and neither
  the static chroma mask nor each frame's own takes it; the static-and-sharp mask for white symbology stays. PR051's
  upload: 46-54 DN of chroma on the terrain's bright band, 18.7 % of the frame, under the fifth that calls a clip
  colour; the masks had taken half the picture and `layers` kept 29 templates of 85 a pair.
- **The field with zero left out is read first, from the one search** (the fourth session; `forensics.shift_field`
  `zeros=`, `shift_field_auto`, `moved`; `layers.second_pass`). A same-position ZNCC of 0.9 or more no longer says
  "held still" by itself: on terrain streaked along its own motion that score stays above 0.9 through a step of 15-35
  px, and the field read with zero allowed split between the streaks matched on themselves at zero and the step (a
  group of 7 px for a step of 18, or zero winning). Both fields come from one correlation now, and the one with zero
  left out is taken wherever a fifth of its templates are sure or it has a consensus; a held picture keeps a handful
  of templates there (the peaks sit on the zone's rim) and falls back to zero allowed as before.
- **The vote along the streaks** (the fourth session; `forensics.consensus`, `VOTE_LEAD`, `VOTE_FLOOR_PX`; method
  §31). Where a pair has fewer than three templates sure both ways, every template's peak is a vote for a place --
  the ridge templates at their own place along their streaks -- and the largest cluster is the group where it leads
  every other cluster a ridge's length away by two sigmas of a split vote; its error along the ridge is at least the
  votes' own scatter. PR051's catch-up steps of 70-140 px (0-2 sharp templates, 63 ridged) lead by 2.0-3.4 sigma; a
  hold read with zero left out forms no cluster; drawn streaks vote as one, and a vote split 13 px apart is none.
  With the three together every pair of PR051's 4.5-13.5 s has a consensus (two steps bridged where 126 were) and
  the chain runs whole at 0.91-0.93 of the data bar's path (`test_golden` now holds it through 13.5 s); PR135's
  layers are the same to the bit.
- **A hold is unmoved inside the zero zone, with nearly every template agreeing** (the fourth session;
  `layers.AT_ZERO` 4 px, `REPEAT_SHARE` 0.8). A repeated capture of one picture lands 0.3-1.9 px from the last
  (PR051), and at 0.5 px half of its holds were measured again over a second and lost; a catch-up whose match
  failed is matched at zero by a few templates only (16 of 79) and is not a hold.
- **Each template's own error, and a template sure only across its streaks** (the third session, 2026-10-28; ROADMAP
  0.4's K9; `docs/method.md` §31). Every template of `forensics.shift_field` carries the error its correlation peak
  gives (the peak's curvature, calibrated on drawn textures, 3.5 times the least-squares value in sigma with a 0.02-px
  floor), kept as its information matrix; one whose runner-up is within the gap of its peak is sure only across the line
  to it, and in a pair's consensus counts as a member across its ridge while fixing nothing along it. The consensus is
  the group's mean weighed by each member's information, scaled down to the members' own scatter and robust to one far
  out, with a covariance: `layers` writes each pair's sigma to its CSV (`err_x_px`, `err_y_px`) and reports the
  pairs' median (`shift_error_px`); `slew`'s chain weighs each step's pairs by it and carries the path's own error
  (`scene_path_err_px` in each window); `comotion`'s annulus takes the same mean. A pair needs eight members as
  before, three of them sure both ways. `layers`' cached templates are measured again once.
- **`tools/pointer_sweep.py`** (and `.sbatch`): the k-from-slew sweep with zoom states over any list of clips, in place
  of the research repository's `pointer_slew_states.py`, with a summary of the measured steps, the states and the
  c-ratio checks.
- Reference data: `pursue/DOD_111719715.mp4` (PR051) and `pr051/` (its two unredacted copies, watermarked, a local
  reference not to be redistributed, and the data bar read by eye).
- Tests: `test_horizon`, `test_focus`, `test_haze` and `test_streak`, new; `test_zoom` (a zoom with no blank end to end,
  a frame flat in part, the confirmation rule), `test_camera` (the picture's zoom in a track) and `test_slew` (the
  figure, a five-frame state) added to.
- **The released-track null against the scene** (`camera --scene LAYERS_CSV`, `--pixel-aspect`; the fifth session,
  2026-10-28; `docs/method.md` §20). Where no readout gives the camera's rate but the ground is in the picture, the
  track is taken relative to the scene's path (a `layers` CSV over the same frames), the camera's rate before the
  release is the scene's drift through the picture while it held the object, and the comparison needs no readout and
  no scale. The null now compares every stretch after the release, names the first, and reads the departure as a
  whole (a line from the release to the track's end or its first jump of more than twice the object's width), and
  says whether the camera moved at all after it let go. PR051 (the MTS-B's "instant acceleration", a golden check):
  the ground held still while the gate held the object, the object then crossed the ground at 0.0079 deg/s for 1.8 s
  and became a dash at 0.11 deg/s with the camera unmoved at either, so the release explains neither.

- **The speed band** (the sixth session, 2026-10-28; ROADMAP 0.4, K1 and K8; `docs/method.md` §32). The rate along
  the track with an error from the track's own covariance (`kriging.py`: a line, a Matérn-3/2 wander and a nugget,
  fitted by REML; `kinematics.speed_band`): the average velocity over the stretch with an honest error, the rate at
  every frame with its band, the velocity's change over the stretch as a number with its sigma, and whether the
  velocity changes at all as a likelihood ratio against a line with white jitter. A track that is not uniform is
  described -- the speed ran from so much to so much, this on average -- instead of refused; the line's rate and its
  `uniform` flag are unchanged. The nugget says how well the detector holds the object (0.1-1.5 px on the recorded
  tracks), and the band is tighter than the scatter of single pairs of frames by two to nine times. The rate frame by frame is written
  to `<tag>_speed.csv` with its figure `<tag>_speed.png` among the report's; `mcdonald kinematics` takes `--out`.
  Held on tracks drawn from the fitted covariance (`kinematics.simulate_track`): the band's coverage, no false
  alarm on a line with jitter, a planted acceleration seen; and on the vendored recorded tracks against the kriging
  survey's anchor, PR43's streak among them (12 to 31 px/frame where the Note reads 7 to 33).

- **What survives the missing variables** (the same session; ROADMAP 0.4, objective 3; `docs/method.md` §33). Facts of
  the track that need no range, field of view or platform speed, in the summary's rows and a paragraph of the bottom
  line: the projective constant-velocity test (`projective.fit`: a straight image track whose distance from its
  vanishing point goes as 1/(t_z - t) -- passes closing or receding with the time to go T and the speed R / T, passes
  with no closing seen, or fails; with k the aspect angle at the last frame; PR43 passes, T = 0.91 s, 35° at a 65.6°
  field), the turn radius in body widths (`projective.turn`: did not turn, a hair off straight, or a turn, on the scale
  of a quadcopter's 15, a pigeon's 33, an airliner's 60; PR43 about 1,900), the smear number, tau from looming or the
  light curve with the aspect angle from it (`kinematics.looming_fit`, `tau_from_light_curve`, `aspect_from_tau`; held
  on rendered scenes, not yet fed by a stage), the admissible region in (R, Rdot) (`kinematics.admissible_region`,
  `Case.admissible`, `<tag>_admissible.png`: the ranges the stages bound, a speed cap, the size through k, tau's line,
  sampled evenly for the speed, aspect and size the clip allows), and the time-distance diagram as the speed figure's
  lower panel.

- **The two in the window, in plain words** (the seventh session, 2026-10-28). The report's card has a row under the
  speed, "Along the track": steady within its band, or the least to the most it ran at (PR43: 11.6 to 31.4 px/frame).
  The rows of what survives the missing variables say it plainly: Turn (did not turn, a hair off straight, or its path
  bends with the radius in widths), Straight and steady (fits, coming closer or going away; fits, no closing seen; or
  does not fit), Moves in a frame (in its own widths). Every row of the card shows how it was found when the pointer
  is held over it, and a short value no longer wraps. Help -> Getting started says what the three rows are, and the
  Measure panel's jewel for the speed step says it measures them.

- **tau from a stage** (the same session; ROADMAP 0.4, I6; `docs/method.md` §33). The flicker stage reads the
  object's size and the level of the ring about it on every frame beside its brightness (`<tag>_flicker.csv`: "object
  size", "object level") and gives them to `kinematics.tau_of`: the time to contact from a size that grows (or shrinks)
  as a straight approach draws it -- the looming law with the blur's reach as an offset (without it a disc closing at
  2.0 s read 3.3), the size read on most of the frames it was tried on, slips to a neighbour dropped, a trend four of
  its sigmas from none (widened for the size's own wander), tau placed to 30 %. Into the case: a summary row, the
  aspect angle from tau and the rate at the last frame (the ledger's theta constrained with no range), tau's line
  through the admissible region, the bottom line's sentence beside the path's own crossing time, and the card's "Time
  to the camera". A point's light curve, with the gain taken out by its ring, is said only as what it would give if
  the change were the range's. Held on rendered approaches through the stage (closing 1.95 ± 0.13 s for 2.03, the
  aspect 6° for 6.1°; receding; a size that holds; a point) and on the 31 objects of the reference case files, none of
  which claims a tau. `looming_fit` fits the offset by default (`offset=False` for the plain law) and refines t_z
  between its grid points.
- **The four unknowns on the report's card** (the eighth session, 2026-10-29; ROADMAP 0.4, objective 6). On every card
  with a speed in the picture, Scale, Range, Aspect and Camera's speed are shown whether or not they were found: the
  value (with ", assumed" where it rests on a guessed field of view), a bound ("2.5 km to 57 km", "at most 1.2 km"), or
  "not known", written quietly; the pointer over each says how it was found, or why not, and what would give it -- the
  report's table of the four unknowns, in the card.
- **The range from a reference's range ratio** (the same session; ROADMAP 0.4, objective 5). A thing of known length
  in the picture is a range of its own, L k / l; with k and the range ratio given, the object's range is that times
  the ratio (`Case.ranged`): in the summary, the four unknowns (as assumed as k is) and the admissible region's
  bounds. Beside such a reference the object's size needs no k (S = p (R_obj / R_ref) L / l). Without the ratio, or
  without k, the range's row says what the reference would give; k's row no longer suggests a reference gives k.
- **`horizon` and `haze` are steps of `run`** (the same session; ROADMAP 0.4, objectives 2 and 6). `run --height
  7000ft` with a point on the sea's horizon (`--horizon FRAME,X,Y`, or a horizon mark in the marks) does `mcdonald
  horizon`; `run --visibility 20km` or `--haze-reference FRAME,X,Y,METERS` does `mcdonald haze` -- each its command's
  own call with its command's own k, the command recorded, the bound in the four unknowns and the admissible region.
  The window's Measure form has the four rows ("Provide additional information about this video"), and a jewel for
  each step that will run. Neither runs, nor is planned, without what it needs (as co-motion without its D).
  `focus` is not a step yet: it is being reworked on another branch.
- **Asked in plain words too: the camera's height, the sea's horizon, how far one could see** (the same session, Jacob's
  choice). "Do you know anything else about this video?" -- on the segment step and in the report card -- asks "How high
  was the camera over the sea?" (meters or feet), "Where is the sea's horizon?" (a click on the video: the frame on the
  screen and the point, on either player) and "How far could you see that day?" (kilometers or miles). The one press
  uses them; on the card, "Work out the speed" does the horizon's and the haze's steps on the track already followed
  (`stages.LATER`, `add_known`; `mcdonald report CASE --height 2000m --horizon N,X,Y --visibility 12mi`), to the
  numbers `run` gives. Kept for the video, and shown in the Measure form. `--visibility` takes miles (`12mi`).
- **`focus` is a step of `run` too, started by the camera's band** (the same session, Jacob's choice, after the
  `metallic-orbs` branch with focus's edge reading was merged). `run --band visible|nir|swir|mwir|lwir` (with
  `--pupil`, `--focus-at`, `--ground-scale`) does `mcdonald focus` on the track -- its own call, its own k, the
  object's polarity -- and its floor is the range's among the four unknowns. Not on every case with a scale: the floor
  rests on the camera being focused far, and only the band says someone is thinking about the optics. The plain form
  asks it too: "What kind of camera was it?" (daylight, near infrared, short-wave infrared, heat (mid-wave), heat
  (long-wave)); on the card, and with `mcdonald report CASE --band`, it is done on the track already followed.
- **The card's words, as Jacob chose them** (the same session): the four unknowns say "unknown" (not "not known"), "To
  find it: ..." under the pointer, and ", a guess" for a field of view given without a source; the straight-line row
  says "fits, closing on the camera" or "fits, receding", the report's own words (and "Time to the camera", "... s
  ago, receding"). The report's table of the four unknowns keeps its words.
- **A track with no bend at all is said, not a crash** (the same session; `projective.said`, the summary's turn row). A
  drawn track dead straight left the turn's 95 % bound empty, and the kinematics stage raised on it: now "no bend at
  all: it did not turn".
- **`streak` reads the exposure through the blur exactly, and the blur off the scene** (the same session; `docs/method.md`
  §30). A dash's length at half its peak is the motion during the exposure once the dash is a couple of blurs long (its
  ends are the motion's), not the motion and a blur: subtracting the blur whole read every dash short (a half-frame
  shutter as 0.46 of a frame at 51 px a frame, 0.34 at 20 px through a 3.5-px blur). `streak.motion_px` takes the blur
  back exactly. The blur is read off the scene's compact points by default (`forensics.point_blur`, as `focus` reads it;
  `--blur` gives it; 2 px, said, where the scene has too few). PR43: its points read 3.6 px; its dash 15.6 ms, 0.47 of a
  frame (11.5 before), and under three of its blurs, so no light curve -- the "no beads" read at 2 px does not stand.
- **The projective test is held to the track's own jitter** (the ninth session, 2026-10-29; ROADMAP 0.4, objective 3, the
  pure-mathematics survey's M1; `docs/method.md` §33). Its three models were compared only with one another, which says
  which is least wrong, not whether any is right: PR077's object, looping through 705° in ten seconds, passed "no closing
  seen", and PR135's members, carrying the camera's slew, passed "receding" ("fits, receding" on the card). The model
  chosen is now held to the track's own jitter (the larger of the speed band's nugget and the nugget of its covariance
  fitted to the model's residual) and fits only within four times it; otherwise the track "describes its trend to N
  px" (the card: "roughly, to within N pixels", in Jacob's words), and no time to the camera's plane, speed over range or aspect is given. Of the 25
  recorded tracks that passed, 24 now describe their trend (4.6 to 234 times their jitter); PR43 fits (1.0). On drawn
  tracks at constant velocity the check calls at most 5 % of them trend-only, none with white jitter. Every report
  with a passing track changes.
- **"No closing seen" is a bound** (the same session; the survey's M5; §33). The speed band's change of speed along the
  track bounds how fast the depth could have changed under the projective model: "if it flew straight at a steady
  speed, its depth changed by less than X % a second ... at least T s from the camera's plane", in place of "the track
  says nothing of how its range changed" (`projective.depth_bound`; its error floored by a free quadratic's, since a band
  that fits no wander reads the velocity as unchanging to within nothing). On a track that fits it bounds the ledger's
  θ with k and cuts the admissible region to a wedge (`admissible_region(rate_max=)`); on one that describes its trend it
  is said as a condition. PR23's object: under 1.6 % a second; PR149's contact: under 4.6 %. The band records its change
  of velocity by axis (`dv_xy`, `dv_err_xy`).
- **t_z's error is the track's own covariance's** (the eleventh session, 2026-10-30; the survey's M5, its other half;
  §33). Where the projective test fits, t_z's band came from a residual bootstrap, which resamples the points as if
  each were drawn alone: on drawn approaches whose centroid drifts for a few frames its 16-84 % held the truth 39 % of
  the time and its 2.5-97.5 % 70 %. Now the residual's covariance (a line, a Matérn wander and a nugget, REML, as the
  speed band fits a track) is carried through the fit's least squares (`projective.tz_err`, the sandwich; new field
  `t_z_err`, the band t_z within one of it): 68-76 % and 91-98 % on every drawn case. The depth bound's own route (the
  band's change of velocity through v_end / v_start = ((T + L) / T)²) was tried and is six times too wide for t_z.
  PR43: T = 0.91 ± 0.10 s (0.72-1.10 at 95 %), where the bootstrap gave about 0.07 a side.
- **A turn past 150° is read whole, as an ellipse; a shorter one says its tilt** (the same session; the survey's M4;
  §33). A body going round a circle draws, at any range, field of view and tilt, the affine image of uniform circular
  motion: an ellipse whose semi-major axis is the circle's radius unforeshortened. `projective.turn` read every turn by
  its sagitta, a formula for a small bend, which put a drawn 286° turn of 25 body widths at 12 and a whole circle at
  thousands. Past 150° (the phase swept and the path's own heading; it goes round, not back and forth; it describes
  the track better than a free quadratic) the turn is now the ellipse's (`projective.ellipse`): the radius in body
  widths with its error, the tilt of its plane, the turn rate, and the speed and the acceleration toward the centre in
  body widths -- 25.0 for 25 at every tilt from 180° up. PR077's object, looping through 585° at 1.0 rad/s, was "a hair
  off straight, about 117 widths"; it is now a loop of 23.5 widths, its plane 84° from facing the camera (or the
  camera's own motion). Under 150° the sagitta's radius is said as the picture's, the turn's own 0.12 to 6.6 times it
  nine times in ten, and "did not turn" says how a turn hides (its plane holding the line of sight: ten times tighter
  for 4 % of orientations, forty for 1 %). The card's row for a loop says "it loops, radius N widths"
  (Jacob's words, 2026-10-30).
- **The admissible region's extent is the clip's; a spread is a draw's** (the same session; the survey's M2; §33). The
  same region was 31 % or 97 % under the speed of sound by how "drawn evenly" is read (Bertrand's paradox). Its sentence
  now gives the extent first and exactly (the least and the most speed, the size from the range's ends), "that much is
  the clip's", then the spread drawn evenly in R and Ṙ (as before) and beside it with the range log-uniform and the
  direction isotropic, the draw no choice of units or axes changes (`admissible_region`'s `invariant`); the figure's
  caption the same. The transverse-speed row adds the isotropic odds: within 15 % of ωR half the time, more than twice
  it one time in 7.5, more than ten times one time in 200.
- **Held pictures tested, not counted** (the eleventh session, 2026-10-29; the survey's M3, brought forward from 0.8;
  `flicker.cadence`, method §35). A tenth of the frames repeating no longer lowers the beat band's top by itself; only a
  cadence does -- a slower source on the frame grid, its held frames a balanced word (at every window length from 2 to
  12 frames, 0.85 or more of the windows within one held frame of the word's share, and above 200 random words of its
  share and length), and not a word the GOP's places foretell better with its I frames fresh (the encoder's). The
  source's rate comes from the slope, its period from the slope's continued fraction. Holds in runs or at random are
  missing samples: the top stays the frame grid's, and they go to Lomb-Scargle as missing, as before. On the census of
  the data folder, 3 of PURSUE's 214 ten-second windows that lowered the band are cadences (PR055's sphere at 16 pictures
  a second, PR051 at 9.9), none of Galileo's 25, 51 of the 70 in PR051's YouTube copy (a 29.97 source doubled), and the
  Svanström helicopters' 25 on 30. On the reference case files the top goes back to the grid's 12 Hz for PR44 (from
  5.96), PR141's two objects (9.5), PR149 (9.3: its "no beat" now covers 0-12 Hz) and PR097's object 8 (10.7); the
  Galileo flyers' to 24 Hz. The stage says how the pictures are held, and the look-alike table lists a cadence only.

- **`mcdonald drift`: did it drift with the wind?** (`docs/method.md` §34; merged from `drift` 2026-10-29, Jacob's choice for 0.4.0, so
  that the drift paper's cited version is installable). Three main tests and a fourth on other
  evidence, each `passes` (consistent with drifting), `fails` (not drifting) or `cannot say` with its reason, and a
  tentative verdict. T1, the display's ranges give its height and climb; T2, a straight line in space from the ranges
  and the north pointer's bearings, against archived model winds and the aircraft's heading; T3, `flicker`'s beat.
  T4, other evidence, runs whichever of its parts the inputs allow: T4a, pieces it shed (or cloud at its own depth,
  from `comotion`'s envelope), bound its airspeed in its own lengths a second; T4b, the remains' fall excludes a heavy
  wreck. The verdict is "consistent with wind-borne drift (tentative)" when T2 or T4a (a tracer at its own depth)
  passes and none fails, "not drifting" when any fails, else "cannot say". T3 fails only on a beat that holds across
  the video (`flicker`'s `comes_back`); a beat in one stretch is not counted and T3 passes on the whole stretch (AARO's
  Puerto Rico lanterns: one window of 109; until 2026-10-22 it could not say), while a hovering rotorcraft's steady
  beat still decides (the Santa Barbara hoist, 2026-10-21). A T3 pass is no longer called "a weak pass" (it is still
  never a strong test). It names no object. Writes `<out>_drift.json`, T4's parts under it (`parts`).
  - The main tests first (2026-10-28, Jacob): few videos show a strike or anything shed, while the height, the winds
    and the beat run on any intact display. The tracer and the remains, T1 and T2 until then, became T4's parts T4a and
    T4b, and the height, the winds and the beat (T3-T5) became T1-T3. The rules, the numbers and the verdicts are
    unchanged (the work runs in the same order, so the bootstrap draws the same numbers).
  - T1/T2 from the aircraft's own track (`--platform`, `--los`, `--obs-winds`, `--ground-m`, `--when`; 2026-10-21):
    where the display shows the aircraft's position and the line of sight's ground point but no range, the rays from
    a turning aircraft are fitted with a straight, steady path (WGS84, bootstrap errors), its climb is T1, and T2
    compares its velocity over the ground with every wind at its height (model files, now with the archive's 10- and
    100-m levels too; observed winds; the aircraft's own wind from its turn), passing within the winds' spread, failing
    10 m/s beyond it, and saying it cannot when a straight-flying aircraft cannot range what it sees.
  - An outline test (the object's fill against a fixed-wing planform; `--outline-*`, `--psf`, `--dark`) was dropped the
    same day as weak: it could only exclude a fixed wing, passed the hovering Huey, and could not say on the lanterns.
    The beat, which was T6, became T5 (and T3 on 2026-10-28).
  - Every test's question is put so that a drifting body answers yes (2026-10-22, after the drift paper): the remains'
    test asks "do its remains sink steadily?" (was "did anything heavy fall?") and the beat "is its brightness free of
    a beat at a wingbeat's or a rotor's rate?" (was whether it beats). T4's own question is "does other evidence in the
    video, where there is any, agree with drift?". The rules and outcomes are unchanged.
  - Known answers: the Hellfire/Yemen clip (`$MCDONALD_DATA/hellfire_yemen/`, its readings vendored in
    `tests/golden/hellfire_drift/`): every test passes, tentative drift. AARO's Puerto Rico lanterns, a known drifter
    (`$MCDONALD_DATA/aaro/videos/`, readings in `tests/golden/puerto_rico_drift/`): 7.4 m/s toward 240°, 181 m above
    the field, T1 and T2 pass from the aircraft's track, T3 passes (a beat in one window of 109, not counted), T4
    cannot say (nothing shed or struck), tentative drift. Santa Barbara's UH-1H Huey, a helicopter known to have hovered
    in calm air (`$MCDONALD_DATA/santa_barbara_2018/`, inputs in `tests/golden/santa_barbara_drift/`): T1, T2 and T4
    cannot say (no range or line of sight reaches it, nothing shed or struck), T3 fails on its main rotor's 10.645 Hz
    held across the stretch: not drifting. PR055: it moves through the cloud it is in at 1.3-3.7 of its diameters a
    second, the cloud places it only within the layer (T4a): cannot say.
  - Tests: `tests/test_drift.py` (synthetic scenes for each test and the verdict; the three known answers from their
    inputs, and by the command line on their clips when `$MCDONALD_DATA` holds them).
- **Jumps named in the speed band** (the eleventh session, 2026-10-29; ROADMAP 0.4, the economics survey's E4;
  `docs/method.md` §32). The band dropped a point four of its own leave-one-out sigmas off its fit, once: nothing said
  which kind of jump it was, nothing held how often it fired on a clean track, and a track past 450 points was never
  cleaned. Each increment's rate is now held against its neighbours' robust scale (Lee & Mykland's test, both
  coordinates together, floored at 0.1 px of jitter and at a grid's rounding), against a threshold drawn on the track's
  own frames and gaps (a clean track has a jump named one time in a hundred: 0-1.5 % on nine kinds of drawn track), and
  each jump found is named as X-13 names outliers: a glitch or an excursion -- left out of the fit as the track's slips
  -- or a step, kept and named (`kinematics.jumps`, `jumps_said`; the band's `jumps`; the stage's "jumps" line, the CSV's
  header, the steps marked on the speed figure). On the recorded tracks 25 of 45 have a jump named and 12 lose points:
  PR149's two glitches (12 and 9 px) had held its band to a tenth-of-a-second wander, and with them out its change of
  speed is seen (25 ± 4 px/s, 5.6 sigma) and its depth bound tightens from 4.6 % to 0.62 % a second; no projective
  verdict moves (PR43 still fits at 1.0).
- **The speed band held to its own track, with a light** (the same session; the economics survey's E1; §32). The band
  states an error at every point, as a bank's value-at-risk model does, and is now checked as a supervisor checks the
  bank's, with no truth to hand: its one-step innovations (`kriging.Model.innovations`, the residual whitened by the
  fitted covariance) counted past ±1.96 (Kupiec), their misses tested for clustering (Christoffersen), what is left in
  them (Ljung-Box, ARCH) and the tails (Jarque-Bera). A light -- green, yellow or red, the Basel zones on the count of
  misses, yellow besides where another test fails -- and its reasons in plain words (`kinematics.backtest`,
  `backtest_said`, `backtest_short`; the band's `backtest`; the stage's "band backtest" line, the light in the
  summary's speed row and the speed CSV's header). Green 97-98 % of the time on tracks drawn from the band's own
  covariance. On the recorded tracks 4 of 44 are green, 38 yellow (a rhythm or something slow left on 56 of 88
  coordinates, the misses together on 17), 2 red (PR088's object 2 and the golden PR144, whose middle-fitted
  covariance is too narrow at their ends): the band is right on average along most of them, not frame by frame.
- **A beat held as covariance** (the same session; the pure-mathematics survey's M8; §32). Where the backtest finds a
  rhythm left, the band is fitted again with a beat beside its wander, the Matérn-3/2 times cos 2πfτ (a covariance by
  Schur's product theorem; with its first harmonic where that is what is then left: `kriging.beat32`, `covariance`,
  `Model(beat=, harmonic=)`), and keeps it where its backtest is the better for it; the rate, the average and the
  change are the wander's. On drawn tracks with a 4-Hz beat the band alone is yellow every time and with the beat held
  green 37 times in 40 (at 8 Hz, 40 of 40). On the recorded tracks a beat is kept on 19 (3.1-13 Hz; PR135's six at
  7.2-8.0), Ljung-Box failing on 37 coordinates in place of 56; PR135's members stay yellow, with something slow left
  (the camera's turn at 44.5 s), and flyer 1's beat is tried and left (with it the band missed more often).
- **"Constant" is an upper bound** (the same session; the economics survey's E12; §32). A band that says its speed is
  constant says that no change was seen (the pile-up problem: its change read 0 ± nothing); it now gives the largest
  steady change of speed it could have missed, from a free quadratic's exact interval -- "a steady change of its speed
  of more than X px/s over the T s would have shown (95 %)" -- and where it sees a wander but no change over the
  stretch, the larger of its own change's far end and the quadratic's (`kinematics.change_bound`, `bound_said`; the
  band's `change_bound`; the band's line, the summary's speed row, the bottom line). On drawn lines with a steady
  change too small to show, the bound holds it 96-98 % of the time (and the wandering band's 196 times in 197). No
  recorded band says constant; 11 recorded tracks whose change is within its noise get the bound. The window's card
  says a constant band as "steady: changed by at most N px/frame" (Jacob's words, 2026-10-30).
- **`slew` takes a data bar in place of the pointer** (the eleventh session, 2026-10-29; ROADMAP 0.4, objectives 1 and
  5: k held against a real clip of known range; `docs/method.md` §17). `slew --platform CSV --los CSV` -- the files
  `mcdonald drift` reads, the aircraft's position and the line of sight's ground point at each reading the display
  prints -- gives the line of sight's azimuth (drawn straight between readings), the platform's share of its turn frame
  by frame (the ground the boresight was on, seen from where the aircraft has got to) and the depression, so no hold is
  fitted and a turret following something round an orbit gives k. On AARO's Puerto Rico clip, where the north arrow
  had been refused (six times low under a steady hold), it gives 1720-1773 px/deg over 82-100, 82-107 and 82-117 s
  against the case's 1657 +- 79 (within 1.5 of its sigmas; the case's own number was pulled about 3 % low by
  regressing the scene on the bar's 29-m grain, and taken the other way gives 1696-1727), and 1844 over 100-117 s,
  where the ground point jumps from the hills to the sea and the hold's range is not the picture's. A golden check
  (`test_puerto_rico_k_from_the_data_bar`) runs on the vendored readings and scene shifts.
- **tau held against the Puerto Rico lanterns' known range** (the same session; §33). Over 1640-2231 the range opens
  2131 -> 2567 m (tau about -97 s): the size route reads the lanterns resolved and shrinking at -0.0127 +- 0.0066 a
  second against the range's -0.0103 and, at 1.9 sigma, claims no closing -- right; the light route (not tried on a
  resolved object) does not follow the range, because the lanterns' own light changed more than their range did, and
  its gate claims nothing; without the ring's level taken out it would have read a false approach at +85 s. Golden
  check `test_puerto_rico_lanterns_tau_against_their_range` on the stage's vendored curves.
- **A track that never moves is held, and `kinematics` says so** (the same session; a bug the Yemen clip exposed). The
  object the MQ-9 holds on its reticle, read against the reticle, is one point to 0.01 px: its second differences had
  no noise to measure, so the held test (a residual within twice the noise) failed and the track was "NOT uniform", and
  `mcdonald kinematics` then crashed printing the residual as a share of a span of 0. The noise is now taken as at
  least a tenth of a pixel (`kinematics.HELD_FLOOR_PX`), so such a track is held -- no projective test, no depth bound:
  its motion is the camera's -- and the command prints "the track does not move".
- **A size read out to the extent's cap is no size** (the same session; `kinematics.TAU_CAP_PX`; a bug the Yemen clip
  exposed). Inside the MQ-9's tracker gate the object's radial profile never fell to a tenth of its height, so
  `flicker.extent` returned its cap, 80 px, on most frames, and tau's row said "its size held, 80.0 px in radius" of a
  thing 22 x 10 px. A size at the cap is now a frame tried with nothing read; an object so read is not resolved, and its
  light curve is tried. On the recorded objects of the 0.4 controls no verdict changes (where an 80 appeared it was
  already dropped as a slip).
- **The projective test and the depth bound held against the Yemen clip's laser** (the same session; §33). The MQ-9
  flew straight and level, so the object's line of sight -- the north pointer's azimuth and the depression from the
  laser's slant range, drawn by a camera that does not turn -- is the test's premise: it fits, closing, with T = 80.7 s
  (16-84 % 75.9-87.2) against the laser's 92.6 (13 % short, outside its band), and the depth bound, |Zdot/Z| <= 2.1 % a
  second, holds the laser's 1.08. Golden check `test_yemen_line_of_sight_against_the_laser` on the drift stage's
  vendored readings.
- **`focus` held against a real known range** (the same session; §28). On the Puerto Rico lanterns (2.1-2.6 km, the
  ground point 3.6-3.9 km) the dark edge, read with the ground's scale from `slew --platform --los`'s k, bounds r/R at
  0.11-0.34 for a 5-20 cm pupil against the truth's 0.59-0.66: it holds, loosely; with the ground streaming past, no
  point is sharp and no floor in metres is given, as it should not be.
- **The Santa Barbara Huey against its known range** (the same session; §33). Its rotor disc, drawn by the frames'
  spread, gives k = 86-99 px/deg at the hoist site's 297 m (+-7 %), the known-size route the drift paper's Huey lacked;
  the size route cannot size a body past flicker's 80-px extent and claims nothing, and `focus` finds no sharp point in
  the night's hillside: neither says anything false, and neither reaches the orbit's slow closing (tau 170-190 s).
- **The rate against the background is the whole track's** (the twelfth session, 2026-10-30; §1). The report's "moved
  about N pixels a second against the background" was the median of `layers`' one-second windows, which exist only
  where the background was read: PR44's exercise went from 22 to 28 when 82f6c13 read other stretches of a still
  background, the bird flying 20-40 px/s along them. The windows now cover the whole track, every second once
  (`layers.over_track`: each pair against a running median of the layer's readings, carried across the frames where it
  was not read) -- 32.3 and 32.6 on the two builds; PR44's page quotes 33. Not a net rate (25.7 and 26.0 there): on
  PR135, whose relative motion turns back with the camera, it fell from 99 to 8 px/s on a member whose every second
  read about a hundred; PR135, read along its whole track, is unchanged. The windows of the background's own readings
  stay in the layers line; a case file written before keeps their median. A report moves where the background was
  read on only part of the track.
- **The card's Turn row for a loop, and a steady speed's bound** (the same session; Jacob's words, 2026-10-30). A turn
  read whole as an ellipse says "it loops, radius N widths" (a bend read by its sagitta keeps "its path bends"); a band
  whose speed held steady says "steady: changed by at most N px/frame", from E12's bound, where it said "steady, ±N".
- **A beat in one stretch, against its own continuum** (session 13; Jacob's answer for 0.4.0). A beat from one 2-s window
  with no window apart agreeing now stands only where it is a line against the continuum of that stretch, as seldom as
  1 in 100 over all the stretches its track offered (`flicker.once_held`, `ONCE_P`, method section 13); otherwise it is no
  beat of its own, the finding says why, and tau's light route runs. It held to a null: 0.8 % of 11,400 drawn tracks with
  no line keep a false beat, against 15.8 % before. Four airliners that "beat" 1.7-4.9 Hz in one window at a track's
  end no longer do. And one stretch under a wingbeat's rate now says so, where it read "a rhythm of its own and not the
  video's". A report moves where its only beat was one stretch: PR088's object 1 and PR097's object 8 by the default rule,
  and no reference case file.
- **Each member of a group against its own background** (session 13; exercise 4's bisect). A member's whole track and
  windows are held to four apertures of its own, clear of its fellows, over its own frames and in its own brightness, not
  to the one set about the member seen longest: a link's tail on one bird had changed another's call. Reads about three
  times the apertures on a group. A lone object is measured exactly as before.
- **`--range-max`: the farthest the object can be, a limit where `--range` is a value** (method §36; PR051's release
  written up, 2026-10-30). A row of `stages.KNOWN` (`run`, `report CASE`, `kinematics`, the Measure form; "nothing beyond"
  in the plain form): the speed across the line of sight and the size at that range, each as the most it can be, R
  `bounded` in the ledger and the admissible region stopped there; a track whose speed changed is said on average and at
  its fastest, and the size is a limit only from a width given or measured, not a spot size. The report calls it a speed
  against the line of sight as the camera held it, for a camera that holds the ground is turning, and over the ground a
  nearer object has the aircraft's speed in it (PR051's drift: at most 5.7 m/s on that line at the ground's 41.7 km, and
  over the ground 5.8 m/s there and more if nearer). Nothing changes unless it is given, but for one thing found on the
  way: a field of view under a degree and a turn rate under 0.01 rad/s keep their figures in the summary, where 0.08 deg
  read 0.1° and PR051's drift 0.00 rad/s.
- **`BALANCED` calibrated, and a word's balance no longer jumps at an exact fraction** (the thirteenth session, 2026-10-30;
  `flicker.balance`, method §35). The line of 0.85 was a judgement; it is now the least line that holds false alarms to 5
  % at every share and length the stage hears a beat on, on random words and on words held in runs or by GOP place,
  gates together: 4.75 % at 60 frames (0.84 gives 7.1 %), 1.7 at 90, 0.7 at 120, none of 2,000 from 300. The number stays;
  the second gate is the line's help at short words of few holds and adds nothing else, and §35 says what no line
  covers (an encoder holding nearly every P frame of a short GOP, rate control at a near steady cost, a slower source with
  scattered timing) and which real words sit either side of it. The reading itself changes: "within one of a L" left a
  word with a whole a L the single count, so 10 pictures a second on 30 read 0.78 at a share of exactly 2/3 and 0.90
  one frame off it. It now reads the two whole counts about a L. On the census DOD_110982722's cadence windows go from
  40 to 63 of 98 and PR34's from 34 to 35 of 35, and nothing else is called a cadence; a word with no whole a L reads as
  before. No reference case's band top or call moves; PR149's least balance reads 0.64, not 0.51, and the random words'
  low end rises, so that 51 census words change how they are said ("at random", "in runs", "more evenly").
- **The Puerto Rico lanterns over their range's doubling** (session 13, no change to a stage). Followed frame by frame over 54.7-117.8 s,
  the range 2131 -> 4474 m, where the case's tracker stopped at 74 s. They do not fade: the lantern switches, by over x4 within half a
  second on 15 % of frames, is not to be seen for 5.1 s at 4.2 km, and comes back black. The stage says nothing false on it. Over the
  whole lever the size route claims receding, tau -113 +- 31 s against the range's -111, good to a factor of two by neighbouring
  windows. The light's bright state follows the range, R^-1.8 in a 22-px disc; its median does not, and its tau runs -53 to -147 s with
  the aperture for -77. In windows of 3-5 s a switch can pass the light's gate as a false closing; from 10 s none does. Method section
  33; golden check `test_puerto_rico_lanterns_over_the_doubling`, on 42 KB of the stage's curves. Method section 17: the ground point's
  jump is not shown to cause `slew`'s 1844 px/deg over 100-117 s (the range drawn straight through it leaves 1800-1896).
- **The size's trend, not only its steps** (the thirteenth session, 2026-10-30; §20). The camera stage said "the
  object's size holds steady" of any track with no step, though the size of fifteen closing airliners grew threefold.
  "zoom steps" now says "none: no step in the object's size", and a new "size trend" row (`camera.size_trend`, also in
  the stage's fields and the command's output) says whether it grows, shrinks, holds within 25 %, or goes up and down: six stretches
  of the track all in order, and its first and last thirds 25 % apart. Of drawn sizes that hold, at most 0.25 % pass with
  no memory and 1.0 % with a memory a tenth of the track's length. A line through the sizes passed 12-14 % at 4 sigma.
  None of the fourteen reference cases has a camera stage, so none changes.
- **The depth bound from the mean taken geometrically, held to the truth** (the same session; §33). `projective.depth_read`,
  which `depth_bound` now wraps; `fit`'s `depth_none`. The mean speed is the ends' geometric mean under the model, so
  every change of speed has its bound, past twice the mean too, but that exact form alone held the truth only 61 % of the
  time at r 2.4 and 27 % at 3.6: the band's end rates lag a steep curve, and the old split had hidden it by overshooting. A tenth of the
  change joins its error, and a bound is refused, with the reason said, past four times the mean speed, where the ends'
  geometric mean is over 1.75 times from the mean speed, or on a closing trend whose own change of speed lies outside the
  band's. PR097 objects 1, 2 and 6 lose their bounds (their ends are 2-2.5 times the mean: 15.9, 10.0 and 38 % a second before);
  flyer 3 tightens from 9.0 to 7.9 %; PR077's object 2 gains one, 13 %; PR149 and PR23 are unmoved.

- **The lens's radial term as a known, `--lens-k1`** (method §37; session 13, from the Galileo aircraft). A known of `run`,
  `report` (given afterwards, `--forget lens-k1`), `kinematics`, Measure's form and the plain questions, kept in the case:
  the k1 of x_d = x_u (1 + k1 r²), r in focal lengths, as a calibration gives it, with the field of view or angle marks
  that give f (through the lens: 50.2° over 640 px at -0.43 is 754 px/rad, not a pinhole's 683). The track is drawn back
  before the projective test and the turn, at their input, so `projective.fit` is unchanged; k becomes the lens's own
  scale along the track (1.000-1.008 of the true one on 19 known-range tracks, where a pinhole's was 0.91-1.01). A lens
  under the jitter passes a pinhole's test at the wrong time (T 19 % short, drawn), which only the known lens shows. With
  none given, a miss that a lens alone accounts for, better than a free quadratic, says so: 98 % of a lens's misses and
  1.4 % of real curves', drawn, and none of the 44 recorded tracks that miss. M1's null holds with k1 in and out (at most
  4.8 % on its 32 cases, 400 draws); off the axis it failed, 10.2 %, until the jitter was read in the picture and carried
  through the lens (at most 4.3 %).
- **A loop is read only past the track's own wander** (Jacob's "revisit", 2026-10-31; §33). The turn's gates (150°, a
  rms 0.8 of a free quadratic's, a minor axis three white errors from nothing) held lines, curves and sways, but on a
  null of drawn tracks with no turn in them read a wander in two coordinates as a loop up to 67 % of the time, a
  camera's pans 47 %, and a sway with a wander on it 85 %; each recorded "loop" drawn again from its own covariance passed
  them up to half the time. No threshold on those numbers mends it. `projective.against_wander` asks the track directly: the
  likelihood gain of the ellipse beside a wander over a wander alone, at least 40, and the minor axis three errors from
  nothing under the covariance left: at most 5.1 % on wander and 6.0 % on a sway, the worst case of each at 1000 and
  200 draws. The radius's error is the same covariance's with the rate let go (white at a fixed rate it held the truth within one
  error 4-29 % of the time; now 50-81 %): flyer 4's 27.4 ± 0.4 widths is ± 15. A track an ellipse follows but which fails
  these keeps its sagitta and says it swings about, no loop claimed (`swings_said`); the card says "it swings about, N widths
  either side". **Reports move:** of the old loops PR097 object 3 stays; PR077 object 1, PR41, PR085, PR088 object 1, PR097
  objects 1, 2 and 4, PR099 object 3 and PR135 objects 1 and 4 swing about, as do FLIR1's exit and Svanström V030.
- **t_z's error from the whole stretch, with two ranges of wander** (the same day; §33). It was read on the middle 450
  points, 7.5 s of a 20-s track at 60 fps, and on 54 stretches of airliners' approaches of known range held the truth
  within one error 4 % of the time (median 14 errors off, the 20-85 of session 11). Read over the whole stretch, the model's own
  columns as its mean, a short wander beside one held at the stretch's length (`projective.two_ranges`), it holds 43 %,
  67 % at 1.96 errors and 80 % at three, its median 8 % of T where T's true error is 10 %, and on drawn tracks with memory it
  is better than it was everywhere. The rest is model error the fit takes up and no residual shows: a steady change of speed
  of a share ε a second moves T by ε T² / 2, so the sentence now says what 1 % a second would do (`speed_moves`). Yemen's miss
  was the old bootstrap's: 80.7 ± 55 s holds the laser's 92.6. **Reports move:** PR43's T 0.91 s, 16-84 % 0.81-1.01, becomes
  0.43-1.39, nearly all of it its last point (0.76 ± 0.04 s without frame 75).
- **`run --marks M --track T` keeps the marks' polarity** (session 13; agent aot). A link chooses a spot size and polarity, and with both given no link ran, so a dark object was measured as bright, silently. They now come from the track's own header where it is a link's, and otherwise from the marks by the link's own sweep; `--dark` and `--size` still win. No reference case gives both.
- **The camera's shake stops a bird** (session 13; agent aot). Five of Amazon's labelled aircraft were named birds, beating on a
  camera shaking 0.4-1.1 px at 3.5 Hz. `run` and the window now read the whole picture's shift wherever a beat would name a bird,
  and name none where the shift has a line at the beat (15 times its neighbours) and the beat is no bigger than a shake that size
  can make (5 of the brightness a pixel, or less). The rule fires on all five, and on none of 37 recorded birds or 36 labelled
  ones. "Stands 10 times over the band" is gone: it fired on every recorded bird under 4.3 Hz, the shake's spectrum being red.
  A bird's case takes minutes longer (72 to 421 s on 421 frames at 1080p, one CPU) and gains a note. No headline moves on a
  reference case file. `flicker --scene-shift` gives the same reading.
- **The link no longer steps backward on a fast thing** (`autolink.went_back`; method, "A thing drawn out along its path"). PR43's
  link took frame 75, a faint blob 9 px behind frame 74's position after the dash had left the picture: one point of 25, which
  set the track's jitter at 8 px and made T 0.91 ± 0.48 s. On a thing expected to move 4 of its widths or more, a peak half a
  width or more behind its last position is now not the thing; PR43 links 24 frames, 50-74, T 0.76 s. From 1,414 drawn dashes: a
  real step refused on 0.28 % of tracks (under 0.63 % at 95 %), 1 frame of 1,719 lost on dashes that really brake or turn. It
  catches the clear case: of planted residues, mostly among real steps, it refuses 4 %. PR43 is the one real track that takes
  this way; ten others forced through it lost no recorded point. PR43's reference case keeps frame 75 until its rerun.
- **A speed from a range is said as the camera held it** (Jacob, 2026-10-31). "relative to the camera's platform" was false on any camera that
  turns, as the number comes from the rate in the picture: `--range`'s five sentences and the bottom line now say "as the camera held it", as
  `--range-max` does. Exercise 2's page moves with them.
- **Exercise 4's page moved to what the tool says** (Jacob, 2026-10-31): five birds and one it will not name. Object 4's old "Beats like a bird"
  leaned on a fellow bird's background apertures; on its own it beats for one stretch. Objects 2, 5 and 6 move in their rates, object 1 to "2 of its 3
  members".
- **A command mcdonald prints quotes its video's path**: `look`'s line to take a row, `segments`' line to open one, and `slew`'s two steps. A path with a
  space broke them anywhere, and on Windows the test's own reading of the line lost the backslashes (found by the first Windows run since 0.3.9).

## 0.3.10 (2026-10-27)

A tester's three, and four stages that failed on a clip with little left to see.

From a tester's run on a Mac (Ravi Kopparapu, 2026-10-26): a ruler that can be seen, a way back to the whole video,
and a folder for each segment, listed with its report -- in the window and on the command line.

- **The ruler is yellow on a dark edge.** "Measure on the video" drew a thin teal line that blended into a building
  against the sky, and the tester did not see that anything had been measured. It is now a yellow line on a dark
  edge, with a bar across each end and its length in pixels on a dark label, and it stays after the drag to show
  what was measured: on the video (`FrameView.drawForeground`) and on the segment step's player (`Screen`), drawn
  by one function (`mark_qt.paint_rule`). A length can be measured from the report card while the report's page
  is open: the video comes to the front first.
- **Two ways back from the report.** The report page's "Back to the video" went to the segment, with no way to the
  rest of the video short of closing it and opening it again. It now has **Back to the segment** and **Back to the
  whole video**; the second, also File → Another segment of this video, opens the whole video on the segment step
  to choose another segment (`QtMarker.whole_video`). Cancelled there, the segment that was open comes back.
- **A folder for each segment.** A segment of a video -- chosen on the window's segment step, or named with
  `--n0/--n1` to any command -- keeps its results in a folder of its own in the video's,
  `<tag>/segment-<first>-<last>/` (objects' folders inside it, as before), so measuring a second segment no longer
  writes over the first one's report (`mcdonald/segments.py`, `clip.named`, `clip.out_prefix`). The whole video's
  results stay in `<tag>/`, and so do results already there for the segment they hold; nothing is moved. `--out`
  still names any folder outright. The window's segment step lists the segments opened before, each with its
  report's label, **Open** and **Report**; **`mcdonald segments VIDEO`** (`--json`) lists them on the command line,
  downloading nothing. **`mark --segment A-B`** puts marks in a segment's folder without changing the frames the
  link searches, and `look --propose --n0 A --n1 B` prints it on the lines that take its rows, so that look, mark
  and run meet in one folder. The exercise pages' paths follow (`pr44/segment-7980-8400/pr44_case.md`); they need
  this version.
- **The segment step's card stays inside its column.** "Do you know anything else about this video? (optional)" was
  one line, and with something given "— 1 given" was added to it: wider than the right column, it pushed the card
  past the column's edge. The question and "(optional)" are now two lines, and the count replaces "(optional)"; "How
  many objects are you looking for?" wraps beside its box. The card's narrowest is 328 px, from 389.

Four stages read a clip that leaves little to see -- AARO's "Middle East Object": a 560-px strip between blurred panels,
crossed by a reticle, boxes and a horizon line, the object in view in stretches (`docs/method.md` §26).

- **`layers` takes 64-px templates where too few 128-px ones fit.** Under 16 clean, textured 128-px templates on a
  typical frame (a consensus needs 8), the matcher read every slew "held still" (92 % of the clip's pairs). With 64-px
  templates the object reads 393 px/s against the ground, against a hand chain's ~400. `fields["templates"]` says which
  were used; a clip where 16 or more fit is measured as before (`layers.template_size`).
- **A link does not take a spot that stays put on the screen.** The reticle's bar, which the object crossed hidden, and
  the north pointer's "N", which it passed slowly, each held a link for 12-40 frames. A place where a spot is found on a
  quarter of the frames is left out, unless a mark is on it: an object the sensor follows stays put itself, with its
  marks on it (`autolink.Places`).
- **A track out of view is measured over its longest stretch.** `flicker` held a track's position across gaps where the
  camera had lost the object, read the ground there as the object "lost", and looked for no beat. Gaps over 0.5 s now cut
  the track, and the longest stretch is measured (`flicker.stretches`, `fields["stretches"]`; said in the case's notes).
- **A warm pointer taller than an "N", in a box.** `--method hue --box` takes a glyph up to 60 px where a box is given
  (the MTS-B's red triangle is 36-42 px); with none, 30 as before. Where chroma's radius wanders in a colour picture, the
  no-power entry says to use it.

## 0.3.9 (2026-10-25)

Faint, small and smeared points are measured in apertures that fit them, a bird is named only from a beat strong
enough to tell it from a close helicopter, a beat with a rotor's look is said, and a beat whose double folds
through the frame rate is named by its own frequency.

- **An object's size where its frames disagree.** A faint, smeared point over a banded sea (PURSUE PR089's bird C
  after a sensor blank) gave a size on only some of its frames, some of them 43-66 px, and got a 58-px aperture on
  a dot 5-9 px across, so nothing could be measured. Where the frames disagree, the size is now read once off the
  median of the object's stamps along the track, turned to its travel and read on the half ahead of it; where they
  agree, nothing changes, and a picture too small for any stamp keeps the point's aperture (`flicker.sizes`,
  `stacked_extent`; `fields["extent_read"]`). C: 48 -> 8 px.
- **A small disc for a point-like thing.** For a thing under 10 px across, the disc is capped at 6 px and stays on
  the smoothed track, while the ring and the background apertures stay clear of the whole thing (`POINT_DISC`,
  `POINT_EXTENT`). On 38 birds with known beats, 19 are now named, against 15; on the Svanström et al. 2021 infrared
  set, false bird calls fall from 12 to 2 of 307 tracks (uap `analysis/sweeps/svanstrom/README.md`).
- **A bird is named only from a beat of 8 % or more.** A fainter beat at a wingbeat's rate is said as "too faint to
  name a bird" (`report.BIRD_FLOOR`): the close helicopters that the small disc made beat were all under it.
- **A rotor's look, said beside the headline.** A beat in step with the background beside the object, or one sitting
  off its middle, is marked (flicker item 14, `beat[..]["rotor"]`) and said in the bottom line. It changes no call:
  6 of 8 helicopter calls in the infrared set looked like this, against 1 of 50 birds, and the thresholds were chosen
  on those calls.
- **A beat whose double folds is named by its fundamental.** Re-measured with the small disc, PR089's bird C beat at
  10.50 Hz, but its double, at 21 Hz, folds through 30 frames a second to 9.0 Hz. That double stood taller than the
  beat, and the stage named 8.99 Hz. A strongest line with a peak of its own at (fps - f)/2 is now read as that beat's
  folded double: the fundamental is reported, and the double is named "folded through the frame rate"
  (`flicker.harmonics`; `test_measurement`).
- The website, mcdonald.bluemarblespace.org, is built and published with every version tag.

## 0.3.8 (2026-10-22)

PR135 downloads again, and the nine other videos DVIDS re-wrapped since the list inside the package was written.

- **PR135 downloads again, and nine others.** On a laptop with 0.3.7, opening PR135 by its name ended in "could not be
  downloaded ... 22771452 of 22766393 bytes arrived": DVIDS had re-wrapped ten of release 06's videos (PR133, PR135,
  PR140, PR143, PR144, PR148, PR150, PR151, PR159, LLE-UAP-PR001) since the shipped list was written, each 4-7 kB
  larger, and the download held a file to the list's size. Every frame and the sound are the same as before, bit for
  bit (`ffmpeg -f framemd5`). The download now takes the length DVIDS says it is sending as whole, and the list's
  only when DVIDS gives none; the ten sizes are brought up to date. A web page sent in place of the video (a network
  that wants you to sign in first) is refused with a sentence that says so (`storage.download`; `test_measurement`).

## 0.3.7 (2026-10-22)

What the report says once you add what you know -- "Subsonic motion" from a thing of known size, "Indeterminate,
range needed" from a field of view, "Supersonic motion" or "Indeterminate, angle needed" with a distance too --
and the form's questions in plain technical words; Help → Check for updates; Auto Mode at every start.

- **"Subsonic motion": what a thing of known size tells you.** A thing of known size in the picture (a ship, given with
  `--ref-px` and `--ref-m`, or "Add what you know" on the card) gives the speed across the line of sight at that thing's
  distance, and no more where the object is no farther away: the upper bound of the JAIS Technical Note. Where that
  bound is under the speed of sound, the report's label is now "Subsonic motion" in place of "Conclusion" or
  "Tentative conclusion", with a speed dial for its badge on the card, and its sentence gives the bound and its Mach
  number: PR149 with a 175 m ship, "at most about 115 m/s across the line of sight ... under the speed of sound (Mach
  0.33)". The bottom line says the same, and that motion toward or away from the camera is not measured. A bird is
  still named first; a track not yet checked by eye is still said on the card and at the top of the report; a bound at
  or over the speed of sound keeps the label it had. Exercise 2 quotes the new first line (`report.SUBSONIC`;
  `test_reduction`, `test_gui`).
- **"Indeterminate, range needed", with a bird, a balloon and a jet placed.** Given a field of view (or angle marks)
  and no distance, the report's label was "No physical conclusion", as if the field of view had taught nothing.
  Now it is "Indeterminate, range needed" (a ↔ on the card), and its first line says how fast the object turns
  across the view, how big it is there, and how far away a bird (0.2–2 m), a weather balloon (2 m) and a fighter
  jet (17 m) of their sizes would be, with the least speed across the line of sight each would then have -- the
  sizes the size-and-speed figure marks. PR113 at 54°: a balloon 180 m away at 410 m/s, a jet 1.5 km away at 3,500
  m/s. An object no wider than a point is put at least that far away (`report.INDETERMINATE`,
  `Case.at_each_distance`; `test_reduction`, `test_cli`, `test_gui`). Exercise 3 quotes it.
- **With a field of view and a distance: "Supersonic motion", "Indeterminate, angle needed" or "Subsonic motion".**
  The first line said "the object moved about N m/s relative to the camera's platform" where N was omega R, the
  speed across the line of sight: the least the speed can be, its motion toward or away from the camera not
  measured. Now it says "at least", gives the object's size at that distance and the kind it is near in size, and
  the label follows the least speed: past the speed of sound, "Supersonic motion" (a dial past the limit; the
  paragraph under it says that two aircraft meeting head-on can pass it between them); under it, "Indeterminate,
  angle needed" (an angle on the card); where a case carries an angle or a range rate, the speed itself,
  "Subsonic motion" or "Supersonic motion" (`run`, `report` and the window do not ask for an angle yet). PR113 at 54° and 3 km: "about 33 m across, about a fighter jet's size, and moving at least
  6,800 m/s across the line of sight". An object the camera held in view gets its size and no speed
  (`Case.at_the_distance`; `test_reduction`, `test_gui`). Exercise 3 suggests trying a distance.
- **"Something moves with it" is no longer in the first line.** A thing found moving with the object -- PR149's faint
  dark spot, 17 object sizes behind it, found at the least strength the tether step allows -- is said in the
  paragraph under it (More, on the card), with how far away it is and at what angle; in the first line it read as a
  finding and confused. One that swings like a pendulum, the thing that step is for, stays in the first line.
  Exercises 1, 2 and 4 quote the shorter lines (`test_reduction`).
- **The questions of "Add what you know" in plain technical words.** "Horizontal field of view (FOV)", "Distance
  to the object", "Physical length of a reference in the picture" and "and its length in pixels on the screen"
  (they were "How wide the camera sees, left to right", "How far away the object is", "How long something in the
  picture really is" and "and how long it is on the screen"); the card's question, its line of what was given,
  the form's tips and messages, Help, `--help` and the Measure form's names follow. The segment step keeps its
  three sentences, which the longer words would push past a small screen.
- **Metric units first in "Add what you know".** The form on the segment step and on the report card starts in
  kilometers, meters and meters a second (it started in miles, feet, miles an hour and knots); a unit a person picks
  is still remembered (`known_qt.UNITS`; `test_gui`). Exercise 2 no longer asks you to change feet to meters.
- **"Measure the sound" quieter than "Measure the object".** Still in colour while the sound is to be measured, but
  as a second thing to do: a dim teal frame and an outlined button, where the main card has the filled one
  (`mark_qt.SECONDARY`, `DIM_ACCENT`; `test_gui`). Measured, it still turns grey with a tick.
- **Check for updates, at any time.** Help → Check for updates in the window asks now whether a newer mcDonald is
  out, whatever was asked earlier that day and even after "Don't ask again", and offers it as the start does; it says
  so when this is the newest, when the internet could not be reached (with the pip command), and when the copy was not
  installed by pip. On the command line, `mcdonald setup` has a `version` line that asks the same thing (`--offline`
  leaves it out). Both READMEs say so (`update.now`; `test_cli`, `test_gui`).
- **Every window starts in Auto Mode, and only you turn Advanced Mode on.** Advanced Mode was remembered from one start to
  the next, and the window turned it on by itself: a click on the video (which put a mark there), opening a video whose
  marks were put by hand, or taking Find's ticked rows. Now each window opens in Auto Mode; Advanced Mode comes on when
  you press Advanced Mode (or View → Advanced Mode), and with the two buttons that ask for work by hand (No on the
  track's pictures, and the queue's Open in the window). In Auto Mode a click on the video is not a mark: a line over the
  video says how to turn on Advanced Mode (`test_gui`).

## 0.3.6 (2026-10-22)

A fourth exercise, and one thing followed twice counted once.

- **Fixed: one thing followed twice was counted twice.** PR135 looked for as six objects: Find listed the flock as two
  groups and a third row seen on 3 frames; followed, that row was one of the second group's birds, and the list said "7
  were followed ... 1 more than you looked for". Two tracks on the same pixels (within 2 px) on 10 frames or more, and
  on half or more of the frames both were followed on, are now one thing, counted once: "You looked for 6 objects: 6
  were followed, 6 of them the members of 2 groups (objects 1, 2); object 3 followed the same thing as object 8." The
  list's row for it says so (`same_as` in `run --each --json`, `tally.same`); the window shows no card or track of its
  own for it, and the queue panel says "The same thing as object 8." Its report stays in its folder. A group and its own
  members are not compared, and one on a group's track and a member's is named as the member (one point). Among the earlier several-object runs this also counts PR44's bird, listed as two rows on
  2026-10-19, once (`several.same_things`; `test_reduction`, `test_gui`).
- **Exercise 4, "Six at once" (PR135)** (`docs/exercises/04-pr135.md`): type 6 on the segment step, and the one press
  takes the flock apart into its six birds, each with a report of its own (6.9 to 7.9 Hz), beside the two flocks'.
  `test_golden --exercises` takes a page of several objects: a `mark` line a row, each with its own `--out`, and `run
  --each`, each object's report and the list's first line held to the page.

## 0.3.5 (2026-10-22)

The window from Jacob's testing, three exercises that need this version, and two fixes.

- **The exercises are Birdwatching (PR44), A ship for a ruler (PR149) and A known field of view (PR113).** PR23's
  is gone. PR149 gives the ship in the picture as a thing of known size (920 px, 175 m: about 115 m/s across the
  line of sight at the ship's distance), PR113 a field of view (54 degrees: a turn rate of 2.27 rad/s, and the
  speed at each distance on the report's figure), each in the window (Add what you know) and on the command line
  (`report --ref-px --ref-m`, `report --fov`). `test_golden --exercises` runs a page's `report` step too and
  holds its report's opening to the page. Each page needs 0.3.5: the window's **Begin**, and PR149's first label.
- **The window, from Jacob's testing (2026-10-21).** The one-press box says "Automatically find, follow, and measure
  the object" over a button that says **Begin**, and its three lights (Find, Follow, Measure) share the box's width.
  **Advanced Mode** (the button under the boxes, or View → Advanced Mode) puts the three steps in the box's place, and
  the same button, now **Auto Mode**, puts the box back; it was a line that unfolded the steps under the box. Find's
  step had its number half way across its box (its empty row for a second button could not grow, so the box gave the
  width to the number); it now lines up with Follow and Measure. The command's oval beside a working bar is as wide
  as the longest command's name, so the bar keeps its width from one step to the next, and the jewels sit in the
  middle under the bar. The frames' wait says "Saving N frames from NAME" and nothing else (where they are kept is
  in its tooltip), and the right column keeps the side panel's width while that card is alone in it.
- `waves`: the default patches fit inside a picture smaller than one 384-px patch and its margins. A 640x328 copy (the
  Burlison MQ-9 clip) got one patch starting above its top edge, cut to a crop that was not square, and every run
  stopped at `assert H == W`. Such a picture is now tiled with the largest square that fits (232 px there). So are
  the Nimitz FLIR1 copies (352x240 and 352x264), which stopped the same way. A picture at least 480 px on its short side
  is tiled as before (`test_waves.py`). Of the 116 videos in the data folder, one more is tiled differently: PR35
  (800x444) gets two 348-px patches inside the margin, where it had one of 384 px that reached into it.
- **Fixed: a speed on the screen was labelled a conclusion.** With pixels a second and no meters a second, and no bird,
  the report's label is "No physical conclusion" whatever else its first line says. Something said beside the speed --
  "something moves with it", integrity's "it behaves like imagery from this sensor chain", a beat that names no bird
  -- had made it "Tentative conclusion" (or "Conclusion" once the track sheet was looked at). Exercise 2 showed it:
  PR149 before the ship is given (the page now quotes the new label). PR113, PR144 and PR43's reference cases read
  that way too. Of 257 saved cases read again, 34 change label, all to "No physical conclusion"; none with meters a
  second or a bird changes (`test_reduction`).

## 0.3.4 (2026-10-21)

A fix for testers on a Mac or Windows, and a new first exercise.

- **Fixed: a folder named like a video was taken for the video.** Every command writes its results to `./<tag>`,
  and on a Mac's or Windows' disk, where case is not told apart, the `pr44` folder `mcdonald look PR44` made is also
  `PR44`. The next command (`mcdonald mark PR44 ...`) stopped with "PR44 is not a video ffmpeg can read: Is a
  directory", and so did the second step of both exercises. A folder is never the video now: the name is looked up in
  the catalog, and a folder that is no video's name is said to be one (`clip.resolve`; `test_reduction`).
- **Exercise 1 is "Birdwatching" (PR44)** (`docs/exercises/01-pr44.md`): 14 seconds of a video opened by name, the
  one press, and "Beats like a bird" at 3.1 Hz, with what the report's beat figure shows. PR23 is exercise 2, "A spot
  over a town". The README links the first; both need 0.3.4 for their command-line steps on a Mac or Windows.

## 0.3.3 (2026-10-21)

Commands that read the camera and its display -- `slew` (k from the camera's own slew), `zoom`, `camera` (also a
stage of `run`), `readout`, `events`, `versions` and `symbology --method atflir` -- a light that flashes in a train
and the look-alike bands in `flicker`, jewels under the window's bars, and exercises for testers.

- **`flicker`: a light that flashes in a train** (item 13; `docs/method.md` §19; merged from `blinks` 2026-10-21). An aircraft's
  anti-collision light flashes 40-100 times a minute, and a train of short flashes is a comb whose harmonics fill the
  beat band.
  - On every frame each tracked thing's 3 brightest and 3 reddest pixels are read beside its sum (`lights`), in a disc
    that covers its whole silhouette (`reach`). A helicopter's dark body hides a light from the sum.
  - In each curve the flashes are found (`flashes`; timed by their centroid), their times folded at 0.6-3 Hz by Z^2
    against random sets, and the lowest near-strongest rate taken (`blinks`).
  - Controls sit beside the object twice its light disc away. A beat that keeps under half its amplitude without the
    flashes is marked "anti-collision light" (`blink_reading`, `deflash`).
  - Writes `fields["blink"]`, `fields["light_reach_px"]`, a note, and a sentence in the report's bottom line. No call
    changes.
  - Known answers: of 837 labelled Svanström tracks, exactly the two helicopters with lights seen (V_054 white
    1.00 Hz, V_030 red 0.75 Hz) and none of the other 835.
  - Tests: `test_measurement` (planted trains, random flashes, a sinusoid, a flat-topped flash, a dark body with a red
    or white light, the bottom line) and `test_golden` (V_054 and V_030; tracks vendored in `tests/golden/`).
  - Which controls were read is kept (`controls_read`, of `controls_n`), and the note counts only those: controls off
    the frame are not quiet ones. The light curves are written to `<out>_flicker.csv` ("<name> white", "<name> red").
    (Branch `blinks2`, 2026-10-21.)
  - `--black-hot` (`flicker`, `run`): on a black-hot thermal display a light, which is hot, is dark. Item 13 then reads
    the darkest pixels, and the sum's sign follows. Kept among the case's known options. Tested on a black-hot
    `_Flasher`: a train with the option, none without. (Branch `blinks2`, 2026-10-21.)
  - The summary has a "flashing light" row for an object's own train, rate a minute first. The window's report card
    shows it as "Light" (Jacob, 2026-10-21). (Branch `blinks2`.)
- **A clip's window is extracted only when every frame of it is on disk** (`Clip.extracted`). It checked the first and
  last frames only, so two windows of one clip extracted apart left a third's ends there and a gap between them, read
  as lost frames (V_BIRD_020 in the Svanström sweep, 2026-10-20). Branch `blinks2`, 2026-10-21.
- **`mcdonald slew`: k from the camera's own slew** (ROADMAP V2, `docs/method.md` §17). The scene's horizontal shift
  (`layers`) regressed on the north pointer's turn (`symbology`) over a slew, with the platform's share of the turn (the
  hold) as a term in time, gives k cos(depression): a floor on k and a ceiling on the field of view, or the field itself
  with `--depression`. Fitted the reverse way round (the pointer is the noisy one); three outcomes (registered, a floor,
  against); a floor stands only where another slew of the same clip registers. Validated on series
  (`tests/test_slew.py`) and on rendered pans (`tools/slew_selftest.py`, five variants). PR148: NO POWER.
- `symbology --search DX,UP,DOWN`: how far the template looks from the glyph's first place (default unchanged).
- `slew --pixel-aspect`: a picture drawn wider than it was made (a 4:3 sensor shown full-height in 16:9, 1.333) is read
  in square pixels. The pointer's convention tested on PR051: the line of sight's azimuth, unit gain to 3.5 %.
- `slew --still`: a still platform (no hold term), where a steady pan gives k. `layers --mask-box X0,Y0,X1,Y1[:N0:N1]`:
  graphics drawn in place mid-picture masked by boxes, not whole rows (`forensics.parse_boxes`). The known answer
  from AARO's Puerto Rico 2013 video: k from its display's target track, and the stage's correct refusal of it.
- `slew` measured against real footage with a known answer: a broadcast camera (PTZ-SLAM's soccer sequence, per-frame
  pan/tilt/focal), c 73 px/deg against 72.0 (`tools/slew_ptz_check.py`). The pointer's path filter follows a camera
  that turns round (a consensus parabola where the line misses) and still drops a run of mislocks.
- **`mcdonald zoom`: the camera's zoom states** (`docs/method.md` §17, "Zoom states"; `docs/history/handoff-zoom-slew.md`).
  The bursts of blank or flash frames the MQ-9's MTS-B changes its field in, found from a 192-px pass over the clip
  (contrast collapse, or a jump of the level with the contrast intact), merged under a second apart, and each fitted
  from the last good frame before it to the first settled one after: `forensics.zoom_fit`, the later frame shrunk by s
  and found anywhere in the earlier, the overlay filled and zeroed, each side's fixed pattern taken out. Each burst is
  a step (x s), no step, or unknown. The scale is the one whose peak stands highest over its own correlation surface
  (in robust SDs), not the highest ZNCC, which the smallest templates win on repeating texture; it is a number only at
  8 MADs or more, leading every scale a quarter or more away (and x1) by x1.25, off the grid's edge, and "no step" only
  with the fixed pattern taken out. PR27 x2.000 at 82 s (its 89-s and 134-s traps unknown), PR057a x2.001 at 32.8 s,
  AARO's Puerto Rico x4.966 and x3.096 where its readout says 5 and 3 (`tools/zoom_check.py`). `scale.zoom_chain` now
  calls `zoom_fit` (it unpacked a tuple as a dict).
- **`slew` across a zoom.** Automatic windows are found within each zoom state and cut at every burst; claims and
  floors are compared within a state only (a floor in one state no longer refuses a claim in another); across a
  measured step the ratio of the states' c is checked against the imagery's; a window given across a step is
  refused; one line per state. `--zoom JSON` reads `mcdonald zoom`'s file, `--no-zoom` keeps the old behaviour, and by
  default the states are found on the spot. Two more checks from the PR27/PR057a/PR076 sweep: a claim whose pointer
  rate and scene rate correlate under r 0.5 at every lag within 6 frames is refused (PR076's 46-s window, r 0.24),
  and the lag is fitted and c's shift for a frame either way reported (PR27: -2 frames, 1.1 %).
- `symbology`: its caveat now says what the pointer is taken to be -- the line of sight's azimuth, a dial -- as `slew`'s
  "assumes" does; it said "north as projected into the image", which PR051, AARO's Puerto Rico clip and PR27/PR057a
  showed wrong for the MTS-B and the WESCAM.
- **The window: jewels under the bar.** Under each step's moving bar -- Find, Follow, Measure, and the one-press card --
  a row of round jewels, one for each bar the step goes through before the next can begin, takes the place of the line
  that said what it was doing: lit when that bar is over, a ring on the one under way, dark for those to come; the
  tooltip names each in plain words. Find has the picture's still parts (where they are not made yet) and the search;
  Follow those, the spot size and the following, each now a bar of its own from empty; Measure a jewel for each stage
  it goes through (`stages.planned`); a queue of several objects a jewel for each object. The line is kept for when the
  step is not busy ("Check track sheet", "The report is ready"). The bar itself is fatter, as tall as the command's
  oval beside it (it was 8 pixels), and says in its middle how far it has got, in per cent, once that is known.
- Donations go to mcdonald's own form at Blue Marble Space (`zeffy.com/.../project-janus-mcdonald-uap-toolkit`), in
  Help -> About, both READMEs and `.github/FUNDING.yml`: "you can donate to the mcDonald UAP Toolkit through Blue
  Marble Space". About no longer links the GitHub page.
- **Exercises for testers** (`docs/exercises/`): short exercises on the PURSUE videos, each with the steps in the
  window and on the command line and the answer to expect, so a tester can check their own work. The first is PR23,
  "Your first video": open it by name, the one press, and a report that says "No physical conclusion" at about 242
  pixels a second. Results come back through an issue form (`.github/ISSUE_TEMPLATE/exercise-result.yml`), and the
  README links both. `test_golden --exercises` (and `--full`) runs each page's command-line steps as written and holds
  the report to the page's quote, word for word; `test_reduction` holds every page to the list, the form and the
  commands that exist.

Merged from the branch `flir1` on 2026-10-21 (`docs/history/handoff-camera.md`), built on 2026-10-20 from the Navy's 2004 FLIR1
as a test of the toolkit (`docs/history/agent-run-nimitz-flir1-2026-10-20.md`):

- **The frame rate of a field-rate MPEG (a bug).** `clip.probe` took ffprobe's `r_frame_rate`, which on MPEG-1/2
  streams that signal the field rate (VCD, DVD) is twice the frame rate: the 2007 FLIR1 copy was read at 59.94, every
  time and rate on it halved, and `flicker` gave a different verdict on the same pixels as a copy that carried the rate.
  `clip.frame_rate` takes `avg_frame_rate` where `r_frame_rate` is twice it, and says so (`fps_note`, in the record and
  the report); `audio` folds through the same rate. No reference clip changes (125 scanned).
- **`mcdonald camera`, and a `camera` stage of `run`** (`docs/method.md` §20): a zoom inside the track found from the
  object's size and its jump about the zoom's centre (FLIR1: x2 at frame 2235, three frames before its readout); the
  track in one scale; its rate's steps (optimal partitioning, Schwarz criterion) set beside the camera's events (the
  zoom steps and `--events`); and with a scale and `--los-rate` the released-track null: is the object's departure
  faster than the camera had been turning, with the assumed field's error in the comparison.
- **`mcdonald readout`** (`docs/method.md` §21): a readout's ticks timed to the frame from the values a person reads off
  a strip; the rate they make; and whether its holding still to the end can say the camera stopped (FLIR1's azimuth:
  0.2466 +- 0.0051 deg/s over 8 ticks; its last value holds to the end, where the next tick was not due).
- `kinematics`: a track that covers under 5 px with a residual within its noise is `held` (a rate of about zero
  describes it), not "not uniform" -- FLIR1's locked stretch was called non-uniform for 0.65 px over a 2.4 px span.
- Tests: `tests/test_camera.py` (synthetic, in `tools/suites.sbatch`); FLIR1 goldens in `tests/test_golden.py`, on the
  reference data's new `nimitz_flir1/` (the 2007 copy, its lossless FFV1 copy, DVIDS's official file); vendored
  `tests/golden/flir1_exit_track.csv` and `flir1_az_stretches.csv`.

Later the same day, on the same branch (the handoff's "Open" list, and its choices tried on the PURSUE reference cases):

- **`camera`: only a zoom its position confirms is taken out of the track.** On the reference cases the stage "found"
  zooms in five of PR135's six birds (a half-maximum blob that takes in a neighbour or a wing for a few frames) and in
  PR43's streak, and took them out of the tracks: one stretch came out at 386 +- 183 px/s. A step's two sides must now
  hold frame by frame, and only a step its offset confirms, or one whose ratio is given, is applied; the rest are
  reported as the object's own size steps, with why (`why_not`, `width_ratio`). On 22 reference objects none is applied;
  FLIR1's zoom still is.
- `camera`: each breakpoint says whether the track jumps there (`jump_px`, `jump_sigma`): a tracker on another feature,
  a frame dropped, a cut -- not a rate of the object's. In `run`'s report more than 6 stretches are summed up (each is in
  the camera CSV), and a stage with no camera event known says so. `camera --events auto` takes the overlay's events.
- **`mcdonald events`** (`docs/method.md` §22): the overlay's own events found from its pixels -- text boxes and each
  one's changes timed to the half frame with their dithering, clocks, the strokes round the object (its gate), the
  picture's level and contrast steps, held frames, contrast collapses. On FLIR1 the box found for the azimuth times 12
  of the 13 hand-read ticks to the same half frame, and the zoom readout's 1.0 -> 2.0 at 2238.
- **`symbology --method atflir`** (`mcdonald.atflir`, `docs/method.md` §23): the Navy's ATFLIR display, which draws no
  pointer, read as fields (azimuth, elevation, zoom, field of view, camera) placed by the picture's box; each field's
  looks, stretches and changes; a sheet to read the looks off; and with `--read` each field's values and the azimuth's
  slew rate.
- **`mcdonald versions`** (`docs/method.md` §24): several copies of one clip -- their containers, detail kept, blocks the
  encoder held, held frames (the recording's, held in all; each copy's own), the lag between them and where it steps (a
  frame repeated or dropped), a relabelled frame rate, and the best source. FLIR1: the 2007 copy (the official copies
  keep 0.65 of its detail, hold 20-36 % of their blocks from frame to frame against its 7 %, and repeat a frame at
  985 and 1986).
- **`readout` timed a tick 40 frames late (a bug).** Its templates compared the grey, so the sky brightening behind
  FLIR1's azimuth at frame 1486 moved the 1 L -> 2 L tick from 1437 (where a strip shows it) to 1477.5. They now compare
  the text's strokes (`forensics.strokes`). FLIR1's slew is 0.2466 +- 0.0051 deg/s (was 0.2518 +- 0.0042), and its exit's
  fastest stretch +1.5 sigma over it with the field's 10 % (+4.3 exact; was +1.3 and +4.0). The FLIR1 goldens hold the
  new numbers.
- **`integrity` sees symbology drawn frame by frame** (`docs/method.md` §25): a gate that moves and text drawn for a
  stretch, which no whole-clip mask holds (FLIR1: "never crosses the symbology" while the object crossed the gate's
  bars and passed under the `5°`). Decided only where object and symbology are on opposite sides of the picture's level;
  otherwise the crossing is reported with no power. Where nothing is crossed the words are as before.
- **A Clip whose header gives no frame count** counts its video packets (MKV, WebM, MPEG program streams), not the
  container's duration, which its sound may outlast (FLIR1: 2294 from the duration, 2290 packets, 2289 frames). Where
  an extraction to the end finds the clip shorter, the window ends there and that is kept beside the frames
  (`last_frame.json`), so the window is no longer extracted again on every run.
- The size/speed figure and the scale stage's ladder add a 0.7 deg field of view: a targeting pod's narrow field (ATFLIR
  NAR), which 3-30 deg left out by a factor of four.
- `share rerun --strict` on the reference files now differs by additions only (the camera stage, `kinematics`' `held`
  and `noise_px`, the ladder's 0.7 deg row, and a camera "no power" in the bottom line's count where a track is under 8
  frames): no number of theirs changes (PR113, PR149, PR144, PR43, PR41; 2026-10-20).

Later again (the second handoff's "Open" list, 2026-10-20 evening):

- **`camera --fields`: the field of view as the display gives it** (`docs/method.md` §20). FLIR1's zoom readout says 2.0
  over 2158-2209 (from 1) while the pod went from NAR x2 (0.35 deg) to MFOV x2 (1.5 deg), then WFOV (6 deg) and back to
  NAR x1 before its exit: a change of x4.3 that its readout does not show and its object, at the copy's blur, cannot.
  `--fields FIRST-LAST:DEG,...` takes each change out of the track as a zoom, about `--centre`, sets it among the
  camera's events, and checks it on the object's size: confirms, contradicts, or no power (under 1.5 blurs, `--blur`).
  On FLIR1 2070-2250 the three x2 zooms are confirmed, the changes of field no power; the released-track null is as
  before.
- **`symbology --method atflir` reads the field's mnemonic** (`--read "fov:A=NAR,E=MFOV"`) and, with the zoom read, gives
  the picture's field frame by frame in `camera --fields` form (`ATFLIR_FIELDS`); a change of the mnemonic's look is
  flagged as a change of scale. It had timed FLIR1's (2167, 2220) before anyone read them.
- **Suggested readings from the clip's own clock** (`mcdonald.glyphs`, `symbology --method atflir --clock X0,Y0,X1,Y1
  --clock-at FRAME:DIGIT`): the clock's last digit, once a person says what it reads on one frame, gives ten templates
  in the display's own font; each look of each field is matched glyph by glyph, and its likeliest digits are printed
  beside it on the sheet. Suggestions, never readings: `?` where no digit matches well.
- **`versions --width`**: the copies compared at up to the smallest one's full width (default 480 as before). At 480 a
  1280-px base and its 1920 x 1080 rendition look alike; at 1280 the rendition, taken back down, keeps 0.73 of PR135's
  base's fine detail.

Later that night (the third handoff's "Open" list, `docs/history/handoff-camera.md`):

- **`run --fields` and `--fov-px`**, rows of what a person may know (`stages.KNOWN`), so the window's Measure form has
  them too: the display's fields reach a case's camera stage as `camera --fields` takes them, and the scale stage's k is
  over `--fov-px`, the picture's box where it is narrower than the frame. `run --fov 0.7` on FLIR1 had put the 0.7 deg
  across all 352 px of the frame, not the 244 of its picture. With `--fov-px` and no field, the scale stage's ladder and
  the size/speed figure's lines span the box. `--fov-px` can be given afterwards (`report CASE --fov-px`).
- **A field of view given to a case afterwards moved its speeds but not its camera stage's degrees (a bug).**
  `add_known` worked out the scale and kinematics again and left the camera stage's rates in the old scale, or in none;
  they are now worked out again with them (`camera.rescale`, arithmetic on its stretches).
- **`events` found no text drawn against a black border (a bug).** It looked for text everywhere but `static_masks`'
  blocks, the dark grown by 8 px against a redaction's codec ringing, which took in FLIR1's field of view (`NAR`, under
  the picture's top edge) and all of GIMBAL's top line, its azimuth among it, on a sky black above the clouds. It now
  looks everywhere but the dark itself and a ring round it, with the lines along the dark taken out, and takes a word
  the copy has blurred into one band as text (`events.text_strokes`, `_band`). The other readers of the blocks are
  unchanged. On PR27 and PR144 the boxes found are the same as before.
- **`events` reads each cell's noise again from its quiet frames**, those more than 6 from a change found: a readout
  that ticks every 20 frames had raised even the lower part of its distribution, and its ticks of one or two segments
  did not stand out. GIMBAL's azimuth, under `symbology --method atflir`: 12 of 13 ticks within a frame, none false (was
  9); GOFAST's change where no tick is goes. Its cost: PR27's one box of scene gives 40 changes over 600 frames (was 19).
- **Letters for the suggested readings** (`symbology --method atflir --letters BOX=TEXT`, and the words given in `--read`
  for the field of view and the camera): templates from text a person has read once, cut at the display's pitch where
  the blur joined its glyphs, and each field read by the ATFLIR's grammar (`atflir.GRAMMAR`: the azimuth's digits and
  then L or R). Letters matched beside the digits everywhere outscore them on true digits, so they are not. FLIR1's
  azimuth side is suggested right on 10 of 11 hand-read stretches (`?` on the other, none wrong), and its digit on 10
  (was 8; glyphs the blur joined are now cut at the pitch). The mnemonic is not read: `NAR` comes out `N??`.
- Tests: `test_camera` (a whole case drawn and run with `--fields`; text against a border and a redaction box on a
  moving scene; letters from fixed text and a joined word); goldens: FLIR1's mnemonic box, its azimuth's side, GIMBAL's
  ticks read off every frame (they had been read off every tenth).
- `versions`: frames held in every copy are "the recording's, or those of a copy every one of these was made from":
  DVIDS's renditions of one upload all carry its encoder's holds (PR149's every 4-5 frames).
- Tests: `test_camera` 90 checks (was 68): a zoom then a change of field the object cannot show; a field the picture
  did not follow, contradicted; an ATFLIR display whose mnemonic and zoom change; a clock and a readout in one font.
  Goldens: FLIR1's fields; FLIR1's clock as templates (the azimuth's digit suggested right on 8 of 11 stretches);
  `atflir` on GIMBAL and GOFAST against hand-read ticks (GIMBAL's azimuth 9 of 13, GOFAST's 5 of 6 and its elevation 3
  of 3, held at what it does now).

Merged from the branch `beat-controls` on 2026-10-20 (`docs/history/handoff-beat-controls.md`), readings in `flicker` and the report for
ROADMAP 0.3 objective 4 (`docs/method.md` §18). None changes a call, a gate or a headline:

- **Look-alikes that are bands** (`LOOKALIKE_BANDS`, `fold_band`): an aircraft's 400-Hz power as recorded aircraft
  sound has it (398.41-401.27 Hz: 8.41-11.27 Hz at 30 fps), a lamp on it, a bundle of candles near 10 Hz, a sky
  lantern's 4.7-8.7 Hz; rotors, propellers, multirotors and a cryocooler's drive, which fold over the whole band at
  video rates, are listed and mark nothing, and the notes say once that frequency excludes none of them. A beat inside
  a band is marked with it ("inside the band of ..."). **More beats now carry a look-alike mark**: most bird beats sit
  inside the lantern's band, and PR077 and PR088's object 2 inside the heard bus's.
- **Steadiness against a clock** (`steadiness`; the information-theory survey's D2): the pieces of the stretch an
  object was followed over, fitted by least squares and compared in their Cramér-Rao bounds, against 200 steady beats
  planted at its frequency in its own noise; `fields["steadiness"]`, the text report and the look-alike note. About
  1.2 s a beat.
- **A flame in the bottom line** (`report.flame_said`): where a beat is inside a flame's band, the report's bottom line
  says a flame flickers there with its own phase, so neither the beat nor members out of step tell it from a wingbeat,
  and which way the group's rigidity (`groups`) points -- lanterns on one wind keep their places, a flock rearranges.
  The headline is not touched.
- **`flicker --scene-shift`**: the scene's own motion at each beat (a cooler's or a gimbal's jitter), every frame
  registered by Lucas-Kanade against the stretch's mean frame (frame to frame where it pans), with 0.05 px planted at
  the beat as its test and the object's own centroid beside it. Synthetic: a 0.3-px jitter read 0.300 px, a still scene
  0.0002 with the plant back at 0.998. PURSUE: PR077, PR135 A and PR41 0.0002-0.0015 px, plants back at 0.98-1.14,
  their own centroids 0.18-0.75 px: no jitter at their beats. Off by default: it reads the stretch twice more.
- `pictures()`: an attempt to read held pictures by the object's own motion (the Svanström and Sphere chains, which it
  misreads) lost PURSUE's real holds and was dropped; the rule is as it was, its misreads in its docstring (method §18).
- A test's premise changed: `test_measurement`'s beat "clear of every look-alike" was 8.5 Hz, which is now inside two
  bands; it is 3.5 Hz.
- Case files made before this will not `share rerun --strict` to their numbers once it merges: the new fields are
  differences to `rerun`. See the handoff.

## 0.3.2 (2026-10-19)

**Known issue, on Windows only** -- as this went out, the Windows runner failed two of the window's checks of
opening another video while the last is on its way in. Found the same night to be the test's, not the window's:
there the next video opened and stayed, as it should, but the runner had saved all of the first video's frames in
a second, before the stop came, which the check did not allow for, and the next check then found nothing to stop.
The test was fixed after the release (tests are not in the package); nothing in 0.3.2 changes.

Four things in the window (Jacob, 2026-10-19):

- **Where the sound plays**, in Edit → Preferences…: "Play the sound on" lists System default and then each output
  ffplay can play to, by the names its SDL gives them, with "Play a test sound" (a short tone there, and the page says
  whether it played). Remembered. SDL opens the output named in `SDL_AUDIO_DEVICE_NAME`, by its own name to the letter,
  so the names come from the SDL library ffplay is linked against (asked in a process of its own), and where SDL is
  built into ffplay -- the Windows builds -- from the sound endpoints' names in the registry; on a Mac where the library
  is not found, from system_profiler. One the player refuses (unplugged since, or named otherwise) is played around:
  the sound starts again on the system default. One chosen that is not connected now stays the choice, and the page
  says so. Checked in two containers with two pretend outputs: Ubuntu 24.04 (SDL2 2.30) and Fedora 44 (sdl2-compat
  2.32 over SDL3 3.4), each output reached and an unknown name played around.
- **The graphics card (GPU)**, in Preferences too: the cards that can compute -- dedicated ones first, named as sold
  -- and "None: the CPU only"; greyed out where there is none, saying so, and naming a card that is there but cannot
  compute. A card can compute where Vulkan lists it as a GPU (Linux, Windows), where it is NVIDIA's with CUDA's
  library, or where Metal runs on it (macOS). A server's management chip, a virtual machine's screen and a card on
  Windows' basic driver are not counted at all. On merlin the FirePro 2270 (TeraScale 2, on the radeon driver) is
  found and not offered: the only Vulkan device there is llvmpipe, the CPU. Nothing uses a graphics card yet: the
  choice is remembered for when something does (`gpu.py`).
- **A control that cannot be used is grey.** The window's palette gave every state the same colours, so a disabled
  menu entry (Undo with nothing to undo), drop-down or button without its own style looked like one that could be
  used; they now take the grey the quiet buttons already used when disabled.
- **Opening another video while one is on its way in stops that one first.** File → Open, a drop or a recent video
  while the last one's segment was being chosen, or its frames saved, opened the new one inside the old one's wait --
  and the old one then came back over it once its own wait was over. Now the old one's question is answered no, or its
  wait cancelled, and the new one opens once it has gone. The window is also drawn empty, saying what it is opening,
  before the next file is looked at: the old video's last frame stayed on the screen until the next page was drawn.

**The command beside the bar** (Jacob, 2026-10-19: "when the progress bar is working, I'd also like a colored oval
box to display the CLI command being invoked; not the full command, just the first word after mcdonald"). Wherever the
window shows a moving bar, an indigo oval to its left names the command that does the same from a terminal: `look`
while Find looks, `mark` while it follows, and while it measures the stage under way's own command (`tracksheet`,
`layers`, `groups`, `flicker`, `tether`, `integrity`...; `run` for the parts that have none) -- on the three steps, the
one-press card and the queue of several objects alike; `mark` while a video is downloaded or its frames saved, `audio`
while its sound is read, `share` while a shared folder is measured again. The window calls the code those commands
call, not the commands, so the oval is the name to look up. `stages.COMMAND` holds a command for each stage, and
`run_case(started=)` says which stage has begun.

Three new commands, merged from their branches on 2026-10-19 (command line only so far; no page in the window yet;
README-technical has an example of each and what each cannot do):

- **`mcdonald stabilize`** holds a screen filmed by a phone still: one homography a frame from the display's own
  drawing, and the display's video written out (frame n = frame n) for every other command to run on. `--to-clip`
  carries a track made on that video back onto the clip. The fifth tranche's six Oman clips hold. `docs/method.md` §14.
- **`mcdonald aspect`** asks whether an object looks the same from every side: does its brightness or size follow its
  heading? A sphere's do not. It needs no range, field of view or beat. `docs/method.md` §15.
- **`mcdonald waves`** reads the sea as a ruler: metres per pixel from the dispersion of the waves a clip shows, with
  no field of view, range or telemetry, along the line of sight unless the depression is given. PR149 passes; most
  PURSUE sea is refused, saying why. `docs/method.md` §16.

## 0.3.1 (2026-10-19)

From a tester's runs on a Mac with 0.2.20 (PR44, opened at 30-56 s; 2026-10-18 and 19):

- **The report can be saved as one file.** "Save as PDF…" at the top of the report's page in the window (and of the
  list of a video's objects) writes the whole report as a PDF with its pictures in it, where the person says; before,
  the page had only "Open the folder" and "Back to the video". `mcdonald report CASE.json --pdf [FILE]` writes the
  same file (`<tag>_report.pdf` beside the case unless a file is named; with `--index`, the list's). The PDF is the
  page's words in the page's order, set for paper by the same function the page uses (`paper.dress`): every folded
  part open, each picture no wider than the text, a long picture in page-high strips, and a track sheet too large for
  paper named, not printed. Letter or A4 by where the computer is.
- **The report says the segment chosen**, at its top, in the video's time as the segment step shows it ("Segment:
  0:30.00 to 0:56.00 of the video, 26.0 s (frames 901–1681)"), and the frames measured where they are fewer: an object
  is measured over the frames round its track. The case file keeps it (`segment`, outside what `share rerun`
  compares); the list of several objects says it too.
- **A report and its card say the same.** The tester's cards said "A bird is the leading explanation" and the report
  "doesn't say bird at all". A card reads its case file by the running version's rules; the report is the file written
  when the case was measured, and a report from before 0.2.14 names no bird (the same segment measured again on 0.2.20
  finds no beat at all, so most likely those cases were older). The report's page now writes the report again from its
  case file wherever this version would word it otherwise (`report.written_again`, what `mcdonald report CASE.json`
  does), and a case keeps the version that measured it (`measured_by`): the report and the card say "Measured with
  mcdonald X, and read with Y ... Measure it again to have this version's own numbers" where they differ.
- **The list of several objects leads each object with its report's conclusion**, where a bird is named; it showed
  only the bottom line, which never names one.
- **The size-and-speed figure has the birds on it, and no k.** A band for a bird's size (about 0.2-2 m across the
  wings) is drawn with the weather balloon and the fighter jet, and in the accent, said as the object's own, where its
  brightness beats like a bird's. The axes are named in words -- size, speed across the line of sight, distance to the
  object -- and a known scale is named by its field of view: the equations with k and ωR are gone from it (they stay
  in the report's table of variables).

## 0.3.0 (2026-10-19)

ROADMAP.md's 0.3, "the beat, held to account; the reference cases as files", as the maintainer scoped it on 2026-10-17:
the goldens green; the flicker gates decided by evidence; a case file for every video of the two papers that reruns to
its numbers; the beat sweep reproducible from the repository's tools; and every frequency with its error. The roadmap
itself is new (`ROADMAP.md`, 2026-10-16): one theme a minor version to 1.0. What 0.3 leaves for 0.3.x: the sky's rhythms
in the look-alike table, the beat in the position, the report's grade and checklist, and levels.

### The beat, held to account

- **Every frequency has its error, and the codec's mark and the members' independence are held to it**, not to the
  resolution (ROADMAP 0.3, objective 2; the information-theory survey's D1 and D6; docs/method.md section 12). Until now
  a peak within 1/T of a codec line was "at the codec's line": 0.5 Hz on a 2-s window, so on the 93 of 112 sensor videos
  whose codec puts a line at 7.49-7.5 Hz no window passed from 7.0 to 8.0 Hz, the middle of the bird band, and the
  planted beats were moved off the line, so their completeness never showed it.
  - `flicker.hz_error`: a block bootstrap in the curve's own residual (200 resamplings in 0.5-s blocks), never under the
    Cramer-Rao bound or the spectrum's own step. Planted in grain, the truth falls within three errors 97-100 % of the
    time above the detection threshold. Every object's peak, window, pair and reported beat carries `hz_err`, and
    `mcdonald flicker` and the finding print it ("7.39 ± 0.02 Hz").
  - The codec's mark (`at_line`): within 3 errors of the line, which has no width of its own. A rhythm on the line is
    marked every time; a strong beat 0.25 Hz beside it in a 2-s window, 0-7 % of the time (100 % before). The rhythms
    locked to every k-th frame in the look-alike table are held to the same error; a supply's, a heard and a held
    picture's rhythm keep the resolution. The one-bit reading and the multitaper's lines use the same mark.
  - Members apart (`common`): by more than 3 of their combined errors over all the pairs judged at once (Sidak: 3.75
    for fifteen pairs), or out of step, as before. Each pair says `apart_z`, `z_needed` and its resolution.
  - `flicker.sliced` (with the slower nulls): beats of 10 and 20 % planted 0.1-0.4 Hz either side of each codec line
    in a 2-s window of each background aperture, and 1 Hz off it as the control, with what the old mark recovers
    beside it (`by_resolution`). `flicker.analytic` (D6): the amplitude a beat needs, in closed form from the noise,
    the frames and the band's look-elsewhere, beside the planted beats (`injection.analytic`, `slice.analytic`) and
    each object (`fields["analytic"]`), with how long a clip must be for a beat of 5, 10 and 20 %.
  - Windows record what the old mark said of them (`codec_by_resolution_hz`, `passes_by_resolution`), and each beat
    how many windows passed by it (`windows_passing_by_resolution`).
  - Moved numbers. PR135 (the golden): the whole-track frequencies are unchanged and now carry errors of 0.02-0.11 Hz
    against a resolution of 0.20. The windows that pass went from 0 to 9, 3, 9 and 7 of 14 for A, B, E and F (the
    four within half a hertz of the line) and from 4 to 14 and 10 for C and D. Where a window is clearer than the whole
    track the stage reports it, so E is reported at 7.90 ± 0.07 Hz (its whole track 7.69 ± 0.03, the paper's 7.64), C
    at 8.02, D 7.09, F 7.74. The golden now holds the paper's whole-track rates to the stage's whole-track peaks (all
    within 0.06 Hz). B's one-bit reading is clear of the line; F's still is not. One pair went the other way: D-F, 0.475
    Hz apart, 3.5 of their errors, under 3.75, and 38 degrees in phase, is no longer apart by frequency (the flock is
    still theirs). The saved-curve controls give the same calls as before: the Galileo birds and PR135 beat; PR23,
    PR055, PR071, WA9ONY-5 and PR144 do not. On real data the mark cuts both ways: strong beats beside the line are
    freed, weak ones whose frequency is poorly known are held (PR073 o00's 8-Hz windows, ±0.24 Hz).
  - The codec slice's worklist (D3), through the new mark, the continuum null and the encoding control: by the stage's
    rule none of its ten objects is called -- the mark was not what refused them, their windows fail the background's
    floor; by the paper's rule seven are (PR085 o04/o08/o11, PR098 o06/o08/o58), candidates for a look.
- **The flicker gates decided, and the bird headline held to a beat that comes back** (the maintainer, 2026-10-17:
  ROADMAP.md's decision 6, on a gate study of 760 saved curve sets with the held-out third left out; docs/method.md
  sections 7, 8 and 13). `GATE_ASTRO` and `GATE_SEIS` stay off and their tests stay reported readings: the
  astronomer's gate lost 4 of 27 known birds' beats and none of the 3 false alarms among 2,887 background apertures
  judged as the object, the seismologist's lost 3 birds to remove 2 of them, and alone each passes 58 % of those
  apertures. The report now names a bird (or a flock) only from a beat that **comes back** -- the whole track beats,
  or two passing windows that do not overlap agree within 0.5 Hz (`flicker.apart_windows`; each beat's `whole_passes`,
  `windows_apart`, `comes_back`). A beat in one stretch is said as one, in the conclusion, the summary and the bottom
  line, and the flicker finding adds "that is one stretch". On the same curve sets the rule keeps 25 of the 27 birds'
  headlines (it loses PR085's and PR088's Table 1 bout-flappers, which the paper's rule calls over the whole track)
  and drops 17 of the pass's 46 one-stretch calls. A case from before the rule has no mark and reads as before. Run
  once, after the decisions, on the held-out third (441 objects in 29 videos, never tuned on): the stage calls 27 (6.1
  %, against 6.4 % on the tuning set); their background apertures pass as the object 3 times in 1,657 (0.18 %, against
  0.10 %), and neither gate would have removed one; the headline rule keeps 7 of the 27 and drops 20 one-stretch
  calls, 15 of them in LLE-PR002, a phone video the whole-video pass had marked as likely noise.
- **The held-out third** (the ideas bank's D5): `tools/sweep/holdout.py` drew 42 of the sweep's 126 videos on
  2026-10-17, by release, with a hash anyone can repeat (`tools/sweep/holdout.tsv`), before any of the gate work; the
  videos the gate work needs by name (goldens, controls, reference cases, the codec slice's worklist, the headline
  rule's two examples) were not eligible.
- **The bird paper's method, in the flicker stage** (the maintainer, 2026-10-16: "It is fine to use the paper's aperture
  and nulls"; docs/method.md section 10). The reference case files measured with the toolkit's own defaults called 11
  of the 19 Table 1 objects beside PR135's six at the paper's frequency and refused 8, which the paper had measured its
  own way. Each piece of that way is now the stage's:
  - `--aperture R[,R1,R2[,BG]]` (`flicker.fixed`; a row of the known-quantities table, so `run`, `flicker` and the
    Measure form all have it): a disc of the object's own size and its ring, never re-centred, in place of the aperture
    that follows the object's size -- where a flock's members fly close, that one takes in its neighbours.
  - The continuum null (`flicker.continuum`, `fields["continuum"]`, printed by `mcdonald flicker`): the peak against a
    power law fitted to the curve's own spectrum, against 2,000 noise curves of that continuum; its original code
    reproduces the review that judged Table 1 exactly, and the port agrees with it on every verdict.
  - The planted-dot encoding control (`mcdonald.planted`, new; `fields["encoding"]`): constant dots like the object,
    planted in the clip's own frames and grain, encoded with libx264 like the clip (on one thread, so that it gives one
    answer) and measured as it is; the encoder makes a beat only where the dots carry a line at it and the beat is under
    three times that line. It decides where one object's beat sits at the codec's rhythm, which the stage had left
    undecided ("nothing tells the two apart"): measured alone, PR135's B (7.38 Hz against the codec's 7.49) is its own,
    the dots reaching 0.4 % there against its 22.5 %. About 20 s, in that case only; without libx264 it says so and
    decides nothing.
  - `--avoid TRACK.csv[,...]` (`flicker.clear_offsets`): the background apertures keep clear of the other tracked
    things in the frame; measured one by one, PR135's E and F had theirs on neighbouring birds. Only when asked, so
    that an object in a queue still gives what it gives alone.
  - `--beat-rule stage|paper` (`flicker.RULE`, per measurement): how a whole curve's beat is judged (`whole_passes`).
    `paper` is the paper's: the continuum null, the background apertures' amplitude at the beat's own frequency, and the
    encoding control; the 2-s windows keep the stage's tests under both. **The stage's rule stays the default, decided
    by the controls** (1,201 saved curve sets): the background apertures judged as the object pass 0.15 % of 4,700
    times by the stage's rule and 2.0 % by the paper's. The paper's rule is for an object someone has looked at, as the
    paper used it.
  `mcdonald run` records `--aperture`, `--beat-rule` and `--avoid` in its command, so a case reruns as it was made.
- **The astronomer's tests** (from the astronomy methods survey, its ports 1-4; module docstring item 7), each in the
  fields, printed by `mcdonald flicker` and said in the notes where it disagrees with a beat the stage called:
  - `fields["astro"][track]["lombscargle"]`: the strongest beat again by the generalised Lomb-Scargle periodogram
    (VanderPlas 2018; astropy's exact method's numbers) over the frames that are samples -- a held picture or a frame
    the object was lost on is a missing sample -- with Baluev's (2008) false-alarm probability over the band, and the
    sampling's own rhythms read off its spectral window.
  - `["scramble"]`: the curve's strongest held against 200 copies of itself scrambled in 0.25-s chunks (Thompson et al.
    2018; Theiler et al. 1992), said above 4 Hz, where the scrambling does not also destroy the slow wander.
  - `["common_mode"]` and `["pixel_phase"]`: the frame's own level and contrast and the background apertures' common
    mode (SysRem, Tamuz et al. 2005), and where within its pixel the object sits, regressed out of the object's curve,
    with its beat before and after.
  - `fields["controls"]` and `["false_alarm"]`: every background aperture put through the object's own tests as if it
    were the object, so what passes is a false alarm by construction; `["injection"]`: beats planted in them at 2, 5,
    10 and 20 % across the band, the completeness. With the slower nulls, which `mcdonald flicker` runs unless told
    `--no-nulls` (`mcdonald run` does not: the method note had said it did).
  - `fields["fold"]` and `<case>_fold.png`: the frames folded on the beat into a bright and a dim half (epoch folding;
    Kepler's difference image), their difference saying where in the picture the brightness that beats is.
- **The seismologist's tests** (from the seismology methods survey, its ports 1, 3, 4, 6, 8 and 11; item 8), likewise
  reported: the multitaper spectrum with the harmonic F-test at the beat, over the stretch and in 2-s windows
  (`fields["seis"][track]["line"]`, `["line_windows"]`: a wingbeat's wandering rate is no stationary line over a whole
  track, and is one within 2 s); the coherence with each background aperture and the frame's level and contrast
  (`["coherence"]`); the noise as a distribution and the centile the object's windows sit at (`["noise"]`,
  `<case>_noise.png`); the Sompi method's lines, a frequency and a decay from a few cycles (`["sompi"]`), which also
  reads a track of 20-59 frames too short for the stage (`fields["short_record"]`); the comb and the glide of the
  fundamental (`["comb"]`, `["glide"]`); members' phases held together, with the array F-statistic
  (`fields["in_step"]`); the fold by phase (`phase_inside`, `phase_outside`); and the one-bit reading (`["onebit"]`).
- **The look-alikes** (the SETI methods survey's first port; docs/method.md section 9): a lamp on 50-Hz mains, an
  aircraft's lights on its 400-Hz power and a video at 30 frames a second fold to 10 Hz (9.19-10.39 at 29.97), where
  small birds beat. `flicker.lookalikes` is the table for a clip -- the supplies and their lamps folded through the
  frame rate (`flicker.alias`), a rhythm locked to every third to sixth frame, the held pictures' cadence, and the
  rhythms its own sound carries (`audio.heard`) -- in `fields["lookalikes"]`; a beat at one is marked with it, not
  refused, and the finding and the notes say what tells a supply's line from a wingbeat.
- **Frames lost at the troughs of the object's own beat are kept**, where they are its troughs (the maintainer,
  2026-10-15; PR097's dark dots, beating at 25-60 % of their brightness, fall under a quarter of their level at every
  trough, and the guard built for PR23's hot roof refused the clearest of them). In two halves, calibrated on the 142
  objects of the whole-video pass that the stage had refused for lost frames: troughs are suspected from six short runs
  or more in the lower half of the curve's own strongest beat (`flicker.lost_at_beat`, `LOST_RUNS` 6), and kept for good
  only where the beat the stage then finds is theirs, within 1 Hz of their frequency or its double
  (`flicker.at_the_troughs`); for every other track the frames are lost, as before. PR097's dots keep their beats
  (6.94, 6.69 and 2.34 Hz); PR23's roof crossing and the WA9ONY-5 balloon say what they said before.

### The reference cases, and reproducing them

- **`mcdonald share rerun FILE.mcdonald`** (`mcdonald.rerun`): every object of a shared file measured again by the very
  command its report records -- the same marks or track, frames, known quantities, polarity, aperture, beat rule, the
  other objects kept clear of, skipped stages -- into a fresh folder, and the new report held against the file's,
  number for number (paths by their file name; a float within one part in a billion); exit 1 where it does not rerun,
  and with `--strict` a report that tracked nothing does not count. The check every reference case is held to, so that
  anyone who installed the package can reproduce a case; `tools/rerun_cases.py` in the repository is the same, looking
  in the reference-data folder too. In the window, a shared file with measured objects has **Measure it again** on its
  card: the objects measured in a thread behind a wait's card, and the card then says whether the numbers come back the
  same.
- **The reference case files** (ROADMAP 0.3, objective 8): a `.mcdonald` file in the reference-data folder's `cases/`
  for each of the 14 videos the two papers rest on -- PR113, PR149, PR43 and PR144 (the Technical Note), PR135 and the
  nine other bird videos of the Scientific Reports Table 1 -- measured the paper's way and made with this release; each
  reruns to its numbers under `mcdonald share rerun --strict` (the folder's README has the table against the papers).
  The reference-data folder holds the nine other Table 1 videos (PR41, PR44, PR077, PR079, PR085, PR088, PR097, PR099,
  PR141) for them.

### The beat sweep, from the repository's tools

- **`tools/sweep/`** (ROADMAP 0.3, objective 9): `sweep.sh WORK` runs the whole-video beat pass through Slurm from
  nothing but the package and the videos. `windows.py` finds each video by the release's file name in the package's
  catalog (downloading it into the storage folder the first time) and cuts it into windows of 400 frames overlapping by
  30; every frame is extracted once (`extract.sbatch`); Find runs over every window (`propose.sbatch`); each video's
  proposals become objects, each linked from Find's own marks and put through the flicker stage (`post.sbatch`,
  `post.py`, `collect.py`); `summary.py` writes the candidates and the strict list, leaving the held-out third out
  until told `--held-out`; `review.sbatch` measures the strict list again by the paper's rule; `cadcheck.py` asks
  whether the encoder or the cadence makes a beat. Run on PR23 and PR073, it cuts the pass's own windows and finds its
  objects exactly.

### The sound: `mcdonald audio`

- **`mcdonald audio VIDEO`** (`mcdonald.audio`; the aviation survey's Av3, brought forward from 0.8 at the maintainer's
  word; docs/method.md section 11): what a video's sound track records, read as an accident investigator reads a
  cockpit recording -- the codec's frame products (named first: they look like machinery), the video's frame comb and
  field rate, an aircraft's 400-Hz power or the mains as a clock on the playback speed (read at full resolution from
  up to three 30-s pieces, a line on two combs counting for neither, every bus said against 400 and 400/1.001),
  sidebands and a tape's wow, any other harmonic series as something turning steadily, and, against a small table of
  airframes whose propellers' speed in flight is sourced (the T56 C-130, the C-130J, the H-60), the airframe, named only
  with its second tone at a measured ratio: an MQ-9 heard from the ground puts its blade-pass over a T56's. Silence is
  NO POWER (exit 5). On PURSUE: PR117-PR119, phone captures of an AC-130's display, are a T56 gunship in flight (67.76
  Hz, second tone at 8.129x), not the AC-130J of AARO's description; PR106/PR107 carry the bus at 399.66/399.74 Hz;
  PR113 carries the NTSC field rate (59.944 Hz) and the mains (60.011 Hz) apart. Planted in 35 real tracks (3,150
  runs): found at +18 dB 76-92 %, at +24 dB 79-97 %; no airframe ever read as another; decoys read as an airframe in 4
  of 1,260 runs. Every heard rhythm is folded through the frame rate into flicker's look-alike table: PR117's propeller
  sits at 7.75 Hz, where birds beat.
- `--flyover LO-HI [--rest HZ] [--temp-c C]` (`audio.flyover`, `audio.pass_of`): a source passing the microphone, its
  speed and closest range from the Doppler curve of its tones (Ferguson 1992). Against ADS-B on AeroSonicDB (148
  fixed-wing propeller passes): 75 pass its own checks, and their closest range over their altitude is 0.92 (16-84 %
  0.66-1.19).
- In the window: **Measure → The sound of this video…**, a page that leads with one plain sentence, the picture of the
  sound (saved in the results folder) and, folded, the command's own words and **A source passing the microphone**
  (the flyover, worked out in a thread, `mcdonald audio --flyover`'s answer to the letter); a **Measure the sound** card
  in the right column when the video has sound, teal until measured, then ticked and grey; and the sound played with
  the picture (ffplay, which comes with ffmpeg) in the player and while choosing the segment, from the frame on the
  screen and at the player's speed, its speaker beside the stop button.

### The window

- Measure's optional part offers to keep the apertures beside the object clear of the other objects followed in the
  video (the command line's `--avoid`), shown only where there are others and not ticked unless asked. With
  **Measure it again** and the flyover above, what this release added to the commands the window does too.

### Tests and CI

- The no-video suites run on GitHub's Linux runners on every push to main and every pull request
  (`.github/workflows/suites.yml`), and on demand on Mac and Windows: nine suites, as `tools/suites.sbatch` runs them,
  with `test_audio` (it had never run there) and the new `test_sweep`. On this release's tree, through Slurm:
  measurement 389, reduction 201, published 32, tether 24, audio 54, cli 105, share 25, sweep 10, gui 653 checks, and
  golden 70 on the real clips; and the Mac and Windows runners before the tag.

## 0.2.20 (2026-10-15)

- A crash in the window on a Mac, from 0.2.19: Measure stopped the program right after the track sheet's question
  (on GitHub's Mac runner in three runs of three; 0.2.18 and 0.2.17 passed). Python's cycle collector runs in
  whichever thread is allocating, and it freed a closed Preferences page -- 0.2.19's page referred back to itself --
  in Measure's thread; a Qt widget destroyed outside the thread that made it is a crash. The page no longer refers
  back to itself, and while there is a window the collector runs only in the window's thread, from a timer, as
  pyqtgraph does (`mark_qt.Collector`): any other widget caught in such a cycle is now freed safely too. Tests:
  `drive_collector` (no collection outside the window's thread through the whole drive; 76 on 0.2.19) and a check
  in `drive_preferences` that the page is freed when it closes.
  The Windows runner, which had crashed at the same place now and then since 0.2.15, passed three runs of three.
- A shared file's stretch, played from its card, stops on its last frame even when the window was held up while it
  played; it went past it (the Mac runner: frames 3-9 stopped on 10), since the player's catching up stopped only
  at the end of the part. Tests: in `drive_sharing`, the window held up on purpose (stopped on 21 before).

## 0.2.19 (2026-10-15)

- The file dialogs open where the person last looked (Jacob, 2026-10-15: "when I open a shared file (or video), can
  the file chooser remember where I last looked?"): **File → Open a shared file…** starts in the folder the last
  shared file came from, **File → Open marks…** in the last marks folder, and the video dialogs (File → Open, and
  "where is this video on this computer?" when a shared file's video is not found) in the folder the last video was
  chosen from, as File → Open already did. A remembered folder that is no longer there is ignored. Tests:
  `drive_remembered_folders` in test_gui.
- Boxes in the right column are only as tall as what they hold (Jacob, 2026-10-15: "Only make the box as tall as
  needed for the content. General design principle for mcDonald"): the "Saving the frames as pictures" and
  "Downloading" cards filled the column's whole height while a video opened, and in a tall window the three steps of
  Advanced grew with the spare room (175 pixels for 120). Opened, "Mark the object by hand" still lets its table of
  marks take the room. Tests: `drive_boxes_fit` and a check in `drive_one_window` in test_gui (`too_tall`, which
  every framed card of the column is held to).
- **Edit → Preferences…** (Ctrl+,) in place of the Preferences menu (Jacob, 2026-10-15); on a Mac, Qt puts it in
  the application menu as mcDonald → Settings, where a Mac's own programs keep it. The page has a section for each
  setting, for more to be added: **where data is saved** (the folder, the room there, and Change…, as on the first
  screen; it says that nothing already saved is moved) and **CPU cores**, as before. Its way back, and Help's
  pages', says "Back" rather than "Back to the video" when no video is open. Tests: `drive_preferences` in test_gui.
- A video downloaded and then saved as pictures shows the two waits one under the other, as the steps they are
  (Jacob, 2026-10-15): once the download is done its card stays, quiet -- grey, a tick, "Downloaded PR113", where
  the video is kept -- and the frames' card comes under it; both go when the frames are saved, or at once if the
  person stops (no segment chosen, Cancel, an error). Tests: in `drive_getting_in` in test_gui.

## 0.2.18 (2026-10-15)

- One file to send someone so that they go on where you left off (Jacob, 2026-10-15): **File → Share for review…**
  writes `<tag>_<who>_<date>.mcdonald` -- the video's results (marks still saying who placed them, tracks, every
  object's folder), the part to open, the stretches to look at, and a thread of notes, each with who wrote it and
  whether a person or an agent did. The video is not in it: it is named by catalog name, file name, size and
  SHA-256, and found (or downloaded) on the other computer, which says whether it is the same file. **File → Open a
  shared file…**, a drop, the first screen's third button, or `mcdonald mark FILE` opens it into a folder of its own,
  with the part, the marks, every object's track, and a card in the right column: the thread (newest first), a
  button per stretch that plays it and stops at its end, the attached figures, and a box whose button saves the
  answer as a file to send back. `mcdonald share make|show|open` does the same from the command line, `--object
  LABEL=TRACK.csv` for an agent with tracks alone. Unpacking takes only data and pictures and refuses a name that
  would land outside its folder. Tests: `tests/test_share.py` (16), and `drive_sharing` in test_gui (8).

## 0.2.17 (2026-10-12)

- The window: no right column until a video is open, so "Measure the object" is not on the home page. Choosing
  the segment, the player is on the left and what is asked -- the segment, how many objects, what else is known,
  the space it needs, Open -- is a card on the right, "Select the video segment".
- A brightness beat at a wingbeat's rate (one bird, or a flock) is labelled "Beats like a bird" in place of
  "Tentative conclusion": in the report, the command line's summary and --json, and the window's card, where its
  badge is a drawn bird.
- A most for the CPU cores: `mcdonald --cpus N`, and Preferences -> CPU cores in the window, remembered. Every
  stage's workers stay within it.
- Fixed: the flicker stage heard a video's hold cadence as a beat. PR34 is 10 pictures a second shown at 30 fps,
  each picture held three frames; the stage reported "a beat at 5.02 Hz (and at 10.03, its double), 31% of its
  brightness, 6 of 8 windows" -- the cadence and its half -- "clear of the codec's rhythm", as the codec check
  looks only at the encoder's anchor frames. The stage now finds the held frames from the frames it already reads
  (`pictures`: a frame is held where it differs from the one before by under 0.2 of the typical change between
  pictures, the 80th percentile -- held frames differ by the encoder's noise, 0.01-0.05 grey levels on PR34, and can
  be most of them), carries the picture rate, and hears a beat only below 0.8 of that rate's Nyquist frequency
  (PR34: 10.2 pictures a second, beats heard up to 4.1 Hz; no beat). `fields["pictures"]` = {rate, held, top_hz};
  the finding says when a strongest peak is above it. PR44 (15 pictures a second) keeps its 3.06 Hz.
- Fixed: a beat heard near the Nyquist frequency. PR27 passed six 2-s windows at 13.5 Hz, 0.9 of the 15-Hz limit,
  on frame-to-frame noise with no rhythm in the curve. A beat -- of the whole track or of a window -- now passes only
  up to 0.8 of the Nyquist frequency (12 Hz at 30 fps; `TOP`), and windows carry `above_top`. PR27: no beat.
  PR41 (6.43 Hz), PR099 (4.90 Hz), PR44 (3.06 Hz) and PR088 (10.3 Hz) are unchanged.
- Not done, and why: a check of the brightness folded on the frame number (a pattern of the recording chain repeats
  with the frame count) was tried for PR088 and withdrawn -- a real beat whose period is near a whole number of
  frames folds just as strongly (a pure 10.28-Hz sine over PR088's 74 frames: 1.32 of its std; PR088: 1.01).

## 0.2.16 (2026-10-10)

- Every CPU: a worker for each CPU this process may use (a batch job's allocation), as far as free memory
  allows (about 100 MiB and 200 bytes a pixel each), where every stage used 10; --procs on groups, flicker,
  tether and symbology too. groups, flicker and symbology's pointer reading now read their frames on a pool,
  tether's on threads, and the static masks on threads. Nothing measured changes: the same numbers to the
  bit on any number of workers.
- New: every case the flicker stage flags with a beat of its own comes with `<case>_beat.png`
  (`figures.beat`), in the style of the PR135 paper's Fig. 2: for each track that beats, its
  brightness deviation over 4.5 s about the stretch reported, beside the background aperture as the
  control, and amplitude spectra over the whole track -- the object's, every background aperture's,
  the codec's rhythm marked, and, where the beat reported comes from a 2-s window, that window's
  spectrum dashed and the window shaded, so a beat heard in one stretch looks like one (PR094's
  4.97 Hz does; PR41's 6.44 Hz stands in the whole track too). Listed in the stage's files, so the
  report shows it under flicker, and among the report's figures. Nothing measured changes.
- Fixed: the flicker stage's aperture was 4 px with its ring at 7-10 px whatever the object's size, so on
  things 15-100 px across the ring lay on the thing, its brightness over the ring came out near nothing,
  and the stage called something anyone could see "lost" and looked for no beat (PR056, PR086, PR116,
  PR47; PR052). The object's extent is now read off its own frames -- its radial profile, a median on
  each ring so that roofs and wave crests beside it do not count -- and a thing wider than the 4-px
  aperture is measured whole: an aperture 1.2 times its extent, a ring and background apertures beyond
  it, re-centred each frame on its own centroid. A point keeps the 4-px aperture, ring and background
  apertures exactly (PR23, PR135's six, Galileo's flyers: unchanged). `fields` carry `extent_px`,
  `aperture_px`, `ring_px` per track, `background_px` and `recentred`; a note says when it happened.
  PR086, PR056, PR116 and PR47 are now tested (no beat of their own); PR41 keeps its 6.43 Hz, measured
  at 12 % of its brightness where the point aperture read 3 %.

## 0.2.15 (2026-10-09)

- Fixed: the flicker stage called PR23 "a bird" from a beat at 2.1 Hz that was one dip -- the
  object lost against a hot roof for seven frames -- read through the running mean, which makes a
  peak near 2 Hz of any slow change. Frames where the object is lost against what is behind it are
  now left out (and listed); a beat must stand over the curve's own slow wander and jitter, fitted
  to its spectrum (one in a hundred curves that only wander pass); a strongest that is only the
  band's edge is no beat; a fundamental is named only from a peak of its own; and the beat reported
  is one that passed. The running mean is the paper's 0.5 s at any frame rate (15 frames at 30 fps
  as before; 30 at 60, where it was 15). Held against PR135's six birds and the five Galileo flyers
  (all keep their beats) and PR23, a pico balloon, PR055 and PR071 (none has one).
- `tests/test_tether.py` runs with the other portable suites: in `tools/suites.sbatch`, on the
  Mac and Windows runners, and in the READMEs' install checks. Nothing measured changes.
- Fixed: the Measure form's own button never asked the track-sheet question (every report made
  through Advanced → Measure → Measure was provisional since 0.2.14); the Advanced line comes back
  under the one button when its run ends short, where its sentence points at it.
- The window's look, reviewed before more testers: dialog buttons without the desktop theme's icons,
  the program named mcDonald in every title, the Mark menu in sentence case, one accent for the
  chosen segment and a proposed path, the frame said once on the control bar, the wait card
  counting frames.
- What is known of the video is asked for: on the segment step, folded under the count ("Do you
  know anything else about this video?": how wide the camera sees, how far away the object is, a
  thing of known size measured on the player, the speeds a report gave), remembered for the video
  and used by the one press; and on the report card when the report could not give a real speed
  ("Add what you know", then "Work out the speed", nothing measured again). On the command line,
  `mcdonald report CASE --fov ... --range ...` (and `--forget`) does the same; the numbers are
  `run`'s when told the same from the start. A case keeps what it was told (`known`).
- A speed from a thing of known size is now the report's conclusion and is in its bottom line,
  where both had said that nothing converts to a speed.

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
