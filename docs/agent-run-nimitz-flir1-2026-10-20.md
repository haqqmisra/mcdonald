# mcdonald 0.3.2 — issues and feature requests from an agent run (Nimitz FLIR1, 2026-10-20)

The Navy's 2004 ATFLIR clip "FLIR1" (not PURSUE; on AARO's imagery page as "Unresolved Case: FLIR
Video", DVIDS 955825). The best copy is the 2007 leak, an MPEG-1 VCD file, 352×240, 29.97 fps
(`https://web.archive.org/web/20070209id_/http://www.vision-unlimited.de/extern/f4.mpg`). Claude Code
ran `mcdonald run` through Slurm on the locked IR stretch (frames 1241–2207) and on the exit
(2185–2250). It ran each on the MPEG-1 file and on a pixel-identical FFV1 copy that has the true rate
in its header. Each run took about 3 min with 4 CPUs and peaked at 1.5 GB. The question behind the run: a published
75.9 g "acceleration" (Knuth, Powell & Reali 2019, *Entropy* 21, 939). It turns out to be the pod
letting go of a target it had been slewing to follow at 0.252 deg/s. So the useful tests were the
camera's own state, which mcdonald does not yet read. Severity: **B** bug, **F** feature, **D** docs.

## Status on branch `flir1` (2026-10-20, later the same day)

- Item 1 (frame rate): **fixed** -- `clip.frame_rate`; tests in `tests/test_camera.py` and the FLIR1 goldens.
- Items 2, 3 (zoom steps; the camera-event gate): **built** as `mcdonald camera` and a `camera` stage of `run`
  (method §18). The zoom is found from the object, and events are given (`--events`). Detecting the overlay's own
  changes (gate, mode, readouts) automatically is not done yet.
- Item 4 (readout tick timing): **built** as `mcdonald readout` (method §19). The values are read by a person (or an
  agent) off its strip.
- Item 5 (the released-track null): **built** into `camera` (`--los-rate`). The assumed field's error is part of the
  comparison: on FLIR1 the fastest stretch is +1.3 sigma with the field's 10 %, and +4.0 with it exact.
- Item 6 (`uniform_motion` on a held object): **fixed** (`held`).
- Items 7-9, later the same day: the ATFLIR's fields placed and followed (`symbology --method atflir`, method §21; the
  values read by a person off its sheet); a 0.7 deg line in the figure and the scale's ladder; integrity's layer order on
  symbology drawn frame by frame (method §23). Item 3's detection: `mcdonald events` (method §20), `camera --events
  auto`. Also `mcdonald versions` (method §22) and a `readout` fix that moves one FLIR1 tick by 40 frames (the slew is
  0.2466 +- 0.0051 deg/s). See `docs/handoff-camera.md`.

## Priorities

1. **B — the frame rate of MPEG-1/2 field-rate streams.** `clip.probe` (`clip.py:165`) takes
   `r_frame_rate`. On this VCD stream that is 60000/1001; `avg_frame_rate` is 30000/1001, and the
   frame count over the duration agrees with 29.97. As a result:
   - every time and px/s is halved: the segment is reported as 0:20.7–0:36.8 instead of
     0:41.4–1:13.6;
   - the codec's anchor rhythm is reported as 19.98 Hz instead of 9.99;
   - **`flicker` gave a different verdict on the same pixels.** On the MPEG-1 file it refused
     ("lost on 108 of 967 frames"). On the FFV1 copy it ran, and found no beat.

   Suggested fix: when `r_frame_rate` is 2 × `avg_frame_rate` (field-rate signalling), or when
   `nb_frames / duration` matches `avg_frame_rate` and not `r_frame_rate`, use `avg_frame_rate`.
   Say so in the record. `audio.py:180` has the same pattern. `reel.py:60` already compares the two.
   A 2-s VCD-style MPEG-1 test clip would hold the fix.
2. **F — a picture zoom inside a track.** The picture zooms ×2 between frames 2234 and 2235 (counted
   from 1). The object's length and its offset from the boresight both double, and the zoom's centre,
   solved from the jump, is the boresight to 0.3 px. The gate follows one frame later and the `2.0`
   readout three frames later. `kinematics` fits one scale through both halves and says only "not
   uniform". Suggested: detect scale steps from the object (its size and offset) and from the
   symbology, report the zoom's frame, ratio and centre, and convert each side with its own k.
3. **F — a camera-event timeline, and a kinematics gate on it.** Events to time:
   - gate collapses and vanishings (the track is let go at 2208 here);
   - gate resizes;
   - picture zooms;
   - mode switches (IR/TV);
   - readout changes.

   A kinematic change point within a few frames of one of these is *an instrument change until
   shown otherwise*. The published fit put the end of its acceleration exactly on the zoom frame.
4. **F — readout tick timing (`slew` for displays without a north pointer).** ATFLIR's pod-azimuth
   readout is in whole degrees. Timing each tick to the frame (two-template change point, dithering
   counted) gave the pod's slew rate as 0.2518 ± 0.0042 deg/s over 8 ticks, with residuals of
   0.09°. The same tool should also say what a readout that holds still cannot rule out. Here it
   could not have changed before the clip ended, whatever the pod did.
5. **F — the "tracker let go" null in `kinematics`.** When an object leaves a field of view it was
   held in, compare its apparent angular rate with the line of sight's rate before the release.
   Reaching that rate and no more is what a camera that stopped following predicts. On FLIR1 the
   fastest stretch is 0.261 ± 0.013 deg/s, against 0.252 before.
6. **D/B — `uniform_motion` on a held object.** On the locked stretch it says "not uniform (0.65 px
   = 27.1 % of span)" when the span is 2.4 px. Compare the residual with the position noise, or
   report "held in the field of view" (the corpus triage's word).
7. **F — the symbology reader for ATFLIR.** Boresight from the frame centre is (176, 120); the
   measured value is (177.5, ~120). There is no north pointer, and it correctly finds none. The
   information is in the text readouts: az/el in whole degrees, zoom, NAR/WFOV, IR/TV, and the
   clock. A template OCR of a fixed font at 352×240 worked here by stretch templates.
8. **D — the size/speed figure.** The default FOV lines are 3°, 10° and 30°. Targeting pods are far
   narrower (ATFLIR NAR is 0.7°, or 0.35° at ×2). Take a sensor-family FOV, or add a 0.7° line.
9. **B (minor) — integrity's symbology mask.** It says "the object never crosses the symbology", but
   the object crosses the moving gate brackets and passes under the `5°` label. The gate is not
   static, so it needs per-frame line masks (vertical runs ≥ 9 rows worked here).

## What worked

- `layers`: no power on empty sky, and it did not lock onto the fixed pattern (the 0.2.x banding
  bug did not come back).
- `groups`: one thing.
- `flicker` on the right frame rate: a correct null (2.76 Hz at 3 %, under the red-noise level).
- `integrity`: correctly said no power on nearly every test, on sky.
- The JSON envelopes and exit codes were clean from Slurm.

## From the paper, for the roadmap

Knuth et al. compare kinematic models by Bayesian evidence (nested sampling, Student-t likelihood).
That is worth having in `kinematics`, with two conditions. First, a posterior-predictive check before
any evidence is reported: their logL was −52,031 over 32 frames, with structured residuals. Second,
the camera's motion must be among the models. They also suggest forward-modelling the pixels with
the exposure, and treating change points as parameters. Both depend on item 3.
