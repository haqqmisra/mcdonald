# Handoff: branch `flir1` -- the frame rate of a field-rate MPEG, `mcdonald camera`, `mcdonald readout` (2026-10-20)

Built in one day at Jacob's request ("proceed with all work on mcDonald in a branch") after the Navy's 2004 FLIR1
was run through 0.3.2 as a test (`docs/agent-run-nimitz-flir1-2026-10-20.md`). Worktree `/models/mcdonald-flir1`,
branch `flir1` off main at 171e0c0. **Not merged.**

## What is on the branch

| what | where | tested by |
|---|---|---|
| the frame rate: `avg_frame_rate` where `r_frame_rate` is twice it (MPEG-1/2 field-rate headers), with `fps_note` in the record, the ingest stage and the report; `audio` folds through it too | `clip.frame_rate`, `clip.probe`, `audio.probe`, `report.clip_block`, `stages` ingest | `test_camera` (an MPEG-1 drawn with ffmpeg, and its FFV1 copy); FLIR1 golden. 125 reference clips scanned: none changes |
| `mcdonald camera`: zoom steps from the object (size + its jump about the zoom's centre), the track in one scale, the rate's steps (optimal partitioning, PELT, Schwarz) set beside the camera's events, the released-track null | `camera.py`, method §18; a `camera` stage of `run` after `kinematics` (no `--los-rate` there) | `test_camera` (synthetic zooms, non-zooms, rate steps, the null); FLIR1 golden |
| `mcdonald readout`: a strip to read a readout off, then its ticks timed to the frame, the rate, and whether holding still to the end can say the camera stopped | `readout.py`, method §19 | `test_camera` (drawn digits, one dithering tick); FLIR1 golden |
| `kinematics.fit_v_px`: `held` (span under 5 px, residual within twice the noise) is uniform; the stage says "held in the field of view" | `kinematics.py`, `stages.kinematics` | `test_camera` |

The FLIR1 numbers the goldens hold:
- **the frame rate:** 30000/1001;
- **the zoom:** frame 2235 (counted from 1). The size gives ×1.91, the offset ×2.08, and with ×2 given the centre
  is (178.1, 122.1);
- **a rate step at the zoom;**
- **the fastest stretch:** 0.293 deg/s, z +1.3 with the field's 10 % (+4.0 exact);
- **the readout:** −0.2518 ± 0.0042 deg/s over 8 ticks, holding to the end, with the next tick due at frame 2318.

The reference data are in `nimitz_flir1/` of the data folder. The vendored files are
`tests/golden/flir1_exit_track.csv` and `flir1_az_stretches.csv`.

## Tests (2026-10-20, Slurm job 7958, and 8156 for test_gui)

All suites pass on the branch: measurement 392, reduction 212, published 32, tether 24, audio 54, cli 109, share 25,
sweep 10, stabilize 13, aspect 10, waves 8, slew 35, **camera 40**, gui 698 (1 skip), and golden 79 (the FLIR1 checks
among them). In job 7958, test_gui failed one check, "measure it again". Its subprocess imported the installed
package (main's, without the camera stage), not the worktree's. `tools/suites.sbatch` now puts this checkout's
`src` on `PYTHONPATH`, and with it the check passes (job 8156).

## Choices to look at before merging

- **`camera` as a stage of `run`.** It adds a stage to every case report: zoom steps (usually "none") and the rate
  steps of the track. The rate steps are new output on every clip, and on long tracks the partition finds the
  slow wander of the tracker. NOISE_FLOOR = 0.25 px keeps a held object in one stretch on FLIR1. It has not been
  run on the PURSUE reference cases, so look at a few reports before keeping it in `run`.
- **The noise floor (0.25 px), the 4-frame shortest stretch, the 3-frame "at an event" distance and ZOOM_MIN 1.35**
  are judgments, set on FLIR1 and the synthetic scenes.
- **`--scale-err` 10 % for an assumed field.** On FLIR1 it decides the verdict: +1.3 σ with it, +4.0 without. Both are
  printed. A sourced field's error should be given.
- **`held`** changes `uniform` only for tracks under 5 px. No golden or test changed. Run the full golden suite
  (`sbatch tools/suites.sbatch golden`) before merging.

## Open

- Detect the overlay's own events automatically: a gate collapsing or resizing, a mode switch, a readout changing.
  These are given by hand now (`--events`). Glyph templates per box, from `readout`, are the start.
- An ATFLIR symbology reader (az/el, zoom, NAR/WFOV, IR/TV, the clock) as a `symbology` method.
- The size/speed figure's FOV lines (3/10/30°) miss targeting pods: ATFLIR NAR is 0.7°.
- `integrity`'s symbology mask misses the moving gate and the text the object passes.
- A Clip whose header has no frame count takes it from the duration. That is the container's, audio included, so
  FLIR1 counts 2294 where it has 2289, and the window to the end is never fully on disk.
- Versions of a clip as a provenance input (frozen frames, detail kept). FLIR1's official copy was the worst of three.
