# Changelog

Every version that went out, newest first. The version is written in one place,
`src/mcdonald/__init__.py`; each release from 0.2.4 on is a git tag and is on PyPI.

## Unreleased (not released)

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
- **`mcdonald zoom`: the camera's zoom states** (`docs/method.md` §17, "Zoom states"; `docs/handoff-zoom-slew.md`).
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

Merged from the branch `flir1` on 2026-10-21 (`docs/handoff-camera.md`), built on 2026-10-20 from the Navy's 2004 FLIR1
as a test of the toolkit (`docs/agent-run-nimitz-flir1-2026-10-20.md`):

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

Later that night (the third handoff's "Open" list, `docs/handoff-camera.md`):

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

Merged from the branch `beat-controls` on 2026-10-20 (`docs/handoff-beat-controls.md`), readings in `flicker` and the report for
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
