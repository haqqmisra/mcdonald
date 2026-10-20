# Handoff: branch `flir1` -- the frame rate of a field-rate MPEG, `camera`, `readout`, `events`, the ATFLIR's fields, `versions` (2026-10-20)

Built in one day at Jacob's request ("proceed with all work on mcDonald in a branch") after the Navy's 2004 FLIR1
was run through 0.3.2 as a test (`docs/agent-run-nimitz-flir1-2026-10-20.md`), then, the same day, the first handoff's
"Open" list worked through and its "Choices" tried on the PURSUE reference cases. Worktree `/models/mcdonald-flir1`,
branch `flir1` off main at 171e0c0. **Not merged.**

## What is on the branch

| what | where | tested by |
|---|---|---|
| the frame rate: `avg_frame_rate` where `r_frame_rate` is twice it (MPEG-1/2 field-rate headers), with `fps_note` in the record, the ingest stage and the report; `audio` folds through it too | `clip.frame_rate`, `clip.probe`, `audio.probe`, `report.clip_block`, `stages` ingest | `test_camera` (an MPEG-1 drawn with ffmpeg, and its FFV1 copy); FLIR1 golden. 125 reference clips scanned: none changes |
| the frame count of a file whose header gives none: its video packets counted (not the container's duration, which sound outlasts); a window to the end that comes out shorter ends there, kept in `last_frame.json` beside the frames | `clip.frame_count`, `Clip._ended_early`, `reel` | `test_camera` (an MKV, an MPEG program stream, a count three frames long); FLIR1 ends at 2289 (was 2294 from the duration) |
| `mcdonald camera`: zoom steps from the object, applied only where its offset confirms them (or a ratio is given); the object's own size steps reported with why; the rate's steps (PELT, Schwarz) with a jump test at each break; set beside the camera's events, given or `--events auto`; the released-track null | `camera.py`, method §18; a `camera` stage of `run` after `kinematics`, its report summed up past 6 stretches | `test_camera`; FLIR1 golden |
| `mcdonald readout`: a strip to read a readout off, its ticks timed to the frame on the text's strokes, the rate, and whether holding still to the end can say the camera stopped | `readout.py`, method §19 | `test_camera`; FLIR1 golden (1 L -> 2 L at 1437.5) |
| `mcdonald events`: the overlay's text boxes and each one's changes (to the half frame, dithers counted), clocks, the strokes round the object, the picture's steps, held frames, contrast collapses | `events.py`, method §20; `camera --events auto` | `test_camera` (a drawn readout, clock, gate, gain step, held frames); FLIR1 golden |
| `symbology --method atflir`: the ATFLIR's fields (azimuth, elevation, zoom, field of view, camera) placed from its picture's box, each one's looks and changes, a sheet to read them off, and with `--read` their values and the azimuth's slew | `atflir.py`, `symbology._atflir`, method §21 | tried on FLIR1, GOFAST, GIMBAL (below); no test yet |
| `mcdonald versions`: copies of one clip -- detail, blocks held, held frames (the recording's and each copy's), the lag and its steps, a relabelled rate, the best source | `versions.py`, method §22 | `test_camera` (two drawn copies); FLIR1 golden (the 2007 copy against DVIDS's) |
| `integrity`'s layer order on symbology drawn frame by frame (a moving gate, text held for a stretch), decided only where object and symbology are on opposite sides of the picture's level | `integrity._overlay_drawn`, `forensics.ridges/strokes/overlay_level`, method §23 | `test_measurement` (five drawn cases); FLIR1's exit |
| `kinematics.fit_v_px`: `held` (span under 5 px, residual within twice the noise) is uniform | `kinematics.py`, `stages.kinematics` | `test_camera` |
| the size/speed figure and the scale stage's ladder add 0.7 deg (a targeting pod's narrow field) | `figures.FOVS`, `scale.FOV_LADDER` | `test_reduction` |

The FLIR1 numbers the goldens hold:
- **the frame rate:** 30000/1001;
- **the zoom:** frame 2235 (counted from 1). The size gives ×1.91, the offset ×2.08, and with ×2 given the centre
  is (178.1, 122.1);
- **a rate step at the zoom;**
- **the readout:** −0.2466 ± 0.0051 deg/s over 8 ticks (was −0.2518 ± 0.0042: see below), holding to the end, with
  the next tick due at frame 2296;
- **the fastest stretch:** 0.293 deg/s, z +1.5 with the field's 10 % (+4.3 exact; was +1.3 and +4.0);
- **events:** the azimuth's 13 ticks from the box found, 12 to the frame; the zoom readout at 2237.5; held 529-534 and
  1233-1236;
- **versions:** the 2007 copy best; DVIDS's keeps 0.65 of its detail, holds 24 % of its blocks (7 %), and repeats a
  frame at 985 and at 1986.

## Two findings to carry to the uap repository's FLIR1 case note

These change numbers in `analysis/cases/nimitz_flir1/README.md` (not edited here: it is the analysis repo's).

1. **One azimuth tick was timed 40 frames late.** The readout reads `1° L` to frame 1436 and `2° L` from 1438 (strip
   of every other frame, 1426-1498). `readout` put the tick at 1477.5 because it compared grey crops and the sky
   behind the readout brightens at 1486. On strokes it is 1437.5. The pod's slew becomes **0.2466 ± 0.0051 deg/s**
   (was 0.252 ± 0.004), its residuals 0.115 deg; the exit's fastest stretch +1.5 σ with the field's 10 %, +4.3 exact;
   the next tick due at 2296, still after the clip's end (2289). Nothing in the conclusion changes; the numbers do.
2. **The zoom readout toggles more than the note says, and at least some toggles are real zooms.** It reads 2.0 over
   441-1276, 2086-2142 and 2158-2210, and 1.0 between (a strip of every 4th frame, 2140-2244). The note treats the
   picture as at 1.0 until 2235. On the locked track (`camera.shapes`, Slurm 8318): over 2070-2085 (1.0) the held
   object is 8.3 px long and 2.1 wide; over 2087-2141 (2.0) 15.6 and 4.1 (×1.9 both); over 2144-2156 (1.0) 8.9 and
   2.0 -- and `zoom_steps` confirms the step at 2140 by its offset about the frame's centre. So those are the
   picture's zooms. Over 2158-2207 (2.0 again) the object is 5.4 px long and 3.2 wide, with its peak down from ~105
   to 80 as the sky brightens (the picture's level steps at 2162): either the picture did not zoom with its readout,
   or the object's half-maximum image shrank with the gain. That is NOT settled. Over the exit the rates are
   unaffected (the locked stretch is ~0; 2230-2234 is at the 1.0 the readout shows), but the note's (e), the object's
   angular size "growing from 0.013° to 0.020° at the release", assumes 1.0 before the release.

## Choices tried on the PURSUE reference cases (2026-10-20)

`mcdonald camera` on 22 objects of the 14 reference case files, each on its own track as `run` calls the stage (Slurm
8186, then 8220 after the fixes), and `share rerun --strict` on PR113, PR149, PR144, PR43 and PR41 (8272):

- **Zoom steps.** Before the fixes, five of PR135's six birds, PR077, PR097's object 3 and PR43's streak "zoomed", and
  the false zooms were taken out of the tracks (one stretch: 386 ± 183 px/s). Now a step's sides must hold frame by
  frame and only a confirmed step is applied: none of the 22 is, nine are reported as the objects' own size steps (none
  about the frame's centre, none with a jump), and FLIR1's still is. **Recommendation: keep.**
- **The rate steps.** 4-42 stretches an object; a panning camera's smooth rate is cut into many, and with no camera
  event known none of them means anything by itself. `run`'s report now sums them up past 6 (each is in the CSV) and
  says no event was known. **Recommendation: keep `camera` in `run`** -- it is cheap (it reads the frames once), it is
  where a zoom inside a track is caught, and its size steps flag a blob that takes in its neighbours (PR135) -- but it
  is Jacob's call; dropping it is one line in `stages.STAGES`.
- **`share rerun --strict` now differs by additions only**: the camera stage; `kinematics`' `held` and `noise_px`; the
  ladder's 0.7 deg row; and, where a track is under 8 frames (PR113), a camera "no power" that raises the bottom line's
  count by one. No number of theirs changes. The reference case files will need making again after the merge, or
  strict reruns told to allow additions (Jacob's call). PR41 (a bird, 54 min) the same: its beat unchanged. (Those
  reruns saw integrity's no-crossing line reworded; it is back to its old words since.)
- **The noise floor (0.25 px), the 4-frame stretch, EVENT_NEAR 3, ZOOM_MIN 1.35, OUTLIER_MAX 0.30, JUMP_SIGMA 5** are
  judgments, set on FLIR1, the synthetic scenes and the reference cases above.
- **`--scale-err` 10 % for an assumed field.** On FLIR1 it decides the verdict (+1.5 σ with it, +4.3 without); both are
  printed.
- **`events`' thresholds** (6-frame windows; 8 sigmas of each cell's noise, read from the lower part of its
  distribution; TOGETHER 3 boxes; WITH_PICTURE 2 frames) were set on FLIR1 (against its 13 hand-read ticks) and GIMBAL
  (9 of its 13 ticks in 300 frames; the whole-series median found 6). `tests/test_camera.py` holds a drawn scene. A
  PURSUE display (MTS-B) should be scored before relying on them there.

## Tests (2026-10-20, Slurm job 8332, `sbatch tools/suites.sbatch golden`)

All suites pass on the branch: measurement 398, reduction 212, published 32, tether 24, audio 54, cli 109, share 25,
sweep 10, stabilize 13, aspect 10, waves 8, slew 35, **camera 68**, gui 698 (1 skip), and golden 87 (the FLIR1 checks
among them: frame rate, zoom and release, the readout's ticks, the overlay's events, two copies). The earlier run of the
day (job 7958, then 8156 for test_gui) was 40 in camera and 79 in golden.

## Open

- **Whether FLIR1's picture zoomed at 2158** with its readout (finding 2): the zooms at 2087 and 2143 are in the
  object's size; the one at 2158 is not, while the gain changes. The gate's size in pixels (a pod's gate scales with
  the picture: it doubled at 2235) is the next test; a scale fit on the scene (`forensics.zoom_ratio`) needs texture
  FLIR1's sky barely has. If the picture did zoom, the case note's angular sizes before the release are halved.
- **Values are read by a person.** `atflir` and `events` time every change but read no digit. Glyph templates could
  be built from a clip's own clock (its seconds digit cycles through 0-9 with known values) and offered as
  suggestions, beside the sheet, never instead of it.
- **`atflir` has no test.** Its layout is from three clips; the 2004 software puts the zoom elsewhere. A drawn ATFLIR
  frame in `test_camera`, and GOFAST/GIMBAL as goldens (they are in the data folder's `aaro/`), would hold it.
- **`events` in `run`.** Not a stage: on PURSUE overlays (MTS-B) whose readouts change constantly, every rate step
  would fall near some event. `camera --events auto` only, where a person chose it.
- **The released-track null on another clip.** Only FLIR1 has it (GIMBAL and GOFAST are ATFLIR too, with the
  azimuth readable; neither has a clean release).
- Versions of PURSUE clips: AARO's 1920x1080 renditions against DVIDS's base files, for the videos the papers rest on.
