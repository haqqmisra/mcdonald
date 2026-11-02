# Handoff: flicker's false "bird" call on PR23 (2026-10-09)

**Status (2026-10-09, night): fixed.** PR23 has no beat now, and its report leads with "No physical
conclusion" (242 pixels a second) instead of "a bird". The flicker stage holds a beat against two more
things that faked one -- frames where the object is lost against what is behind it, and the curve's own
slow change -- plus a band-edge rule and a fixed double. Every bird control keeps its beat; none of the
things that are not birds has one. **Released as 0.2.15 at Jacob's word** (asked at the commit: "Commit locally",
then "Release 0.2.15"): the fix `3c459a0`, the release `429c95f`, tagged `v0.2.15`, on PyPI at 21:26:50 UTC. Jacob, after running
PR23 in the window: "PR23 looks good now!"
The original brief this session started from is kept below, under "As found".

## What was done

All in `src/mcdonald/flicker.py` unless said; the module docstring has the reasons, items 4 and 5.

1. **Lost against what is behind it** (`lost`, `filled`; `DROP`, `LOST_MAX`). A frame where the object's
   brightness over the ring falls under a quarter of its own level -- the running upper quartile over 2 s,
   which a gap of up to 1.5 s does not pull down (a running median over a second is pulled down by any gap
   over half a second and finds none of it) -- or to nothing or less, is lost. Lost frames at the ends are
   trimmed; between them they are filled across from the frames either side, in the object's curve and in
   the background apertures that go with it; no 2-s window holding one is used; lost on more than a tenth of
   its frames, no beat is looked for (no power, said). Listed in `fields.lost`, in the finding and in a note.
   The CSV keeps what was measured. PR23: frames 3 (its first, trimmed), 131-136 and 138.
2. **Its own slow change** (`drift`, `_fit`, `_units`, `_steps`; `RUNS`, `BEYOND`, `CLIP`). The strongest
   beat must stand over the wander (a random walk) and jitter (white grain) that best account for the curve's
   own spectrum -- Whittle's fit, by reweighted least squares, with frequencies standing 10 times over the fit
   left out of it (a peak's) -- further than 99 in 100 of 1,000 curves made of that wander and jitter stand
   over theirs, each read the same way (its own wander and jitter fitted: a parametric bootstrap, one seed, so
   a curve gives one answer). `curves.*.over_drift` and `drift_needed`, and the same in each window. Two
   cheaper ways were tried and dropped, on random walks of 60-400 frames at 30 and 60 fps: wander read off
   the frame-to-frame steps (a strong beat is in those steps too: flyer 5's beat, read as wander, hid its own
   3.9 Hz half; and 2-9% of random walks passed for 1%), and a fit with the strongest peak's lobe left out
   (8-10% of random walks passed, with tails to 9 times the threshold, because the drift's own peak is then
   left out of the fit of the drift). The one kept: 1.0, 1.0, 0.3, 1.3 and 2.0% of 300 random walks pass at
   the 1% setting (60 frames at 30 fps, 120 at 60, with and without grain; pure grain 2.0%) -- measured on the
   prototype that became `drift`, the same steps; on the code as committed, test_measurement's 40 random walks
   of 120 frames: 1 passes.
3. **The band's edge** (`peak` returns `edge`). A strongest within its lobe of the band's first frequency
   with more power below it (or of the last, with more above) is the flank or a side lobe of something slower
   and no beat: WA9ONY-5's 1.53 Hz, PR144's late windows at 1.50 Hz, a planted 0.8-Hz swing's side lobe at
   1.60 Hz.
4. **The double** (`harmonics`). The other peak must be a local maximum in the band, further from the
   strongest than its lobe (2 resolutions), and stand 6 times over the drift fitted with its own frequencies
   left out (a fit with them in let flyer 5's real half prop up the drift it was held against: 4 times over it,
   30 over one without). Before, every 2-s window with a beat under 2.5 Hz found its "half" on its own flank and
   named fundamentals under 1.5 Hz (PR23's `hz_range` was 0.92-0.98 Hz).
5. **The beat reported passed.** The whole track passes where its strongest is 3 times the background's, over
   its drift and not the band's edge; the reported beat is the clearest passing window where it is clearer
   than the whole track *or the whole track does not pass* (PR23 had reported the whole track's 2.13 Hz, which
   had not passed, because three windows over the roof had). `fields.strong` names the tracks whose beat
   passed; `of_member` and the report (`report.own_beats`) count only those: "5 of its 6 members" in the
   conclusion, the summary and the bottom line where one did not pass.
6. **The running mean is the paper's 0.5 s at any frame rate** (`DETREND_S`, `trend_frames`): 15 frames at
   30 fps as before, 30 at 60 where it was 15 -- the paper's Galileo analysis uses 30 (`GWIN`), and at 15 the
   drift's peak sat at 4 Hz, on flyers 1, 4 and 5's fundamentals.

The shared and codec tests are asked as before (at the whole track's strongest, of every object with a beat):
a window's beat does not escape the background's veto. That was tried and undone the same evening -- PR144
went from "shared" to "a beat at 1.50 Hz" from five late windows.

## The controls, before (0.2.14) and after

Curves read once from the video with the committed source, then judged again with each change (`flicker.judge`,
the stage from the curves on, split out of `measure` for it); the after also measured again end to end, from the
video, and the same to the digit. All in `/scratch/mcdonald/flicker-controls-2026-10-09/`: `before/` and `after/`
(each control's `_flicker.csv` and fields), the two logs, `controls.py` (what each control is: the paper's tracks,
the vendored golden tracks, PR23's run's track; dark for the balloon, PR055 and PR071) and `judge_saved.py` (the
stage again on saved curves, no video read: `PYTHONPATH=src python3 judge_saved.py before`). The frames were
deleted (1.1 GB).

| control | before | after |
|---|---|---|
| PR23, frames 1-208 (the one press's track) | beats 2.13 Hz, 15.5% -- "a bird" | no beat: 3.31 Hz, 5.3% against the background's 6.0%; frames 3, 131-136, 138 left out |
| WA9ONY-5, pico balloon (dark) | beats 1.53 Hz (the band's edge), "316%", from 5 windows | no power: lost on 35 of 130 frames |
| PR055, sphere among clouds (dark) | no beat | no power: lost in the clouds on 92 of its 233 frames |
| PR071 (dark) | null: shared with the background | no beat; frames 397-414 left out |
| PR144, frames 300-500 | null: shared at 2.01 Hz | null: shared |
| PR135 A-F, each alone | 7.84 / codec (7.38) / 8.02 / 7.11 / shared (7.65) / shared (7.60) | the same |
| PR135, the six as one group | beats, all six | beats, all six `strong` (paper 7.85, 7.38, 7.85, 7.11, 7.64, 7.60) |
| flyer 1 | 3.35 Hz | 3.35 Hz (paper 3.36) |
| flyer 2 | 4.25 Hz, 15 of 15 windows | 4.25 Hz, 14 of 15 (paper 4.49 over the whole track) |
| flyer 3 | 10.04 Hz | 10.03 Hz (paper 10.04); its fade at the end left out |
| flyer 4 | 4.22 / 8.44 Hz, 13 of 18 windows | 4.19 / 8.38 Hz, 3 of 18 (paper 3.85 / 7.69) |
| flyer 5 | 3.92 / 7.84 Hz | 3.92 / 7.84 Hz (paper 3.90 / 7.80) |

PR23's report, its case worked out again with the new stage: "**No physical conclusion.** The object moved
about 242 pixels a second against the background, and its real speed and size cannot be found from this video
alone." The summary's beat row: "no beat reaches 3 times what the background beside it does (6.0% ...) in 204
frames (6.8 s, resolution 0.15 Hz); frames 131–136 and 138, where it was lost against what is behind it, are left
out".

## Checked

Everything through Slurm, niced.
- The brief's numbers, reproduced on the saved curve: as run 2.13 Hz 15.5%, the dip filled 3.31 Hz 5.3%, frames
  5-94 2.21 Hz 8.7%, 140-204 3.55 Hz 8.6% (the brief has 3.52); 2,000 random walks of 204 frames through the stage's
  steps peak at 1.5-2.5 Hz 67% of the time, 57% with white grain as large as a step, 32% with twice that (the brief:
  64%); every window's `fundamental_hz` was half its `hz`.
- The drift test's calibration, 300 random walks per line (above); and the controls' table, judged again after
  each change and then measured end to end from the video (jobs 2164/2167 before, 2191 after).
- The new tests on the committed source fail where they should: the planted dip is "a beat at 2.10 Hz" there, and
  the 2.4-Hz beat's windows name fundamentals of 1.19-1.20 Hz.
- PR23's saved case with the stage judged again: the conclusion above.
- All suites and golden on this tree (job 2192, `tools/suites.sbatch golden`, 4 CPUs): measurement 246,
  reduction 195, published 32, tether 24, cli 105, gui 575 (WxAgg skipped), golden 38 (none skipped:
  `MCDONALD_FOOTAGE` set for the balloon) -- ALL SUITES PASS.
- Not run: `tools/find_rank.py` (nothing that finds or links changed).
- **Jacob ran PR23 in the window afterwards, on the released code: "PR23 looks good now!"** (2026-10-09, night).
- Left on disk: the suites' frame cache (`MCDONALD_HOME=/scratch/tmp/mcdonald-suites`) has golden's new clips' frames
  now -- PR23, PR135 1240-1389, flyers 1-4, the balloon, about 770 MB on /scratch (a disk, 3.4 TB free) -- so the next
  golden run reads no video; the controls' frames (1.1 GB) were deleted; nothing of this session in /tmp.

## Decisions of mine, for Jacob's word

- *The thresholds*: lost under a quarter of its level; no beat past a tenth of its frames lost; the drift test
  at 99 in 100; a half or double at 6 times its drift. Each calibrated or checked as above; each one number.
- *The running mean at 60 fps* is 30 frames now (the paper's 0.5 s), where it was 15. Flyers 1-5 moved by
  0.03 Hz at most.
- *PR055 says "no power"* (lost in the clouds) where it said "no beat". Both mean no bird; the new one says why.
- *A limit, said*: the drift is a random walk and white grain. A brightness that changes smoothly with a
  timescale of its own (a slowly tumbling irregular body, scintillation) is neither, and a bump it makes near
  2 Hz could pass for a beat; the apertures beside the object catch it only where the scene does it too.
- *Not done*: "which frames drive a passing window" (the brief's fix 1, last sentence). The lost frames are
  listed, and a beat carried by a few frames is broad, not a peak, so the drift test refuses it; a per-window
  leave-out test was not written.

## The release (2026-10-09, night)

Main pushed with everything since 0.2.14 (six commits: the design review's fixes, what is known of the video,
this fix, the release); then `v0.2.15`, which `publish.yml` uploaded (run 12: the wheel at 21:26:49 UTC).
Checked from a fresh venv (`/scratch/mcdonald/venv-0.2.15`, Python 3.14): `pip install mcdonald==0.2.15` gives
0.2.15, released 2026-10-09, with the new flicker stage in it (the running mean 30 frames at 60 fps, `drift`), and
`mcdonald setup --offline --no-desktop` says "Ready.". On the release tree (job 2195): reduction 195 and cli 105,
all pass; the six suites and golden had passed on the fix (job 2192), and the release is strings. The Mac and
Windows runners on `429c95f` (runs 21 and 22): the Mac passed all six suites (measurement 246, reduction 195,
published 21, tether 24, cli 102, gui 520) and its Homebrew install; Windows failed one check of test_cli, "nothing
else in the case changed; it keeps what it was told, and the command is in Reproduce" -- not the flicker change but
this afternoon's what-is-known check (`e45293b`, the first commits the runners had not seen): `mcdonald report`
writes the Reproduce line with `shlex.quote`, as every Reproduce line is, and the runner's temp path
(`C:\Users\RUNNER~1\...`) comes out quoted where the check expected it bare. The test was fixed (`0a8ca4c`; the
package is unchanged -- the tests are not in the wheel -- so no version) and both runners run again on it: Windows (run 23) and the Mac (run 24) pass all six suites -- measurement 246, reduction 195, published 21, tether 24, cli 102, gui 470 there and 520 here -- and the Mac's Homebrew install says "Ready." with the window up.
Testers on 0.2.14 are offered 0.2.15 at their next start.

## Left

- His word on the decisions above.
- Flyers 2 and 4 report a window's frequency (4.25, 4.19 Hz) where the paper's whole track gives 4.49 and
  3.85: unchanged by this, and worth a look against the paper's own windows.

## As found (the brief this session started from)

### What happened

`mcdonald` 0.2.14, GUI one-press run on PR23 (`DOD_111688809.mp4`, R01, Iraq, Dec 2022, 30 fps,
frames 1–208). Output is in `/scratch/mcdonald/pr23/` (`pr23_case.json`, `pr23_case.md`, `pr23_flicker.csv`).

The report's conclusion:

> **Tentative conclusion.** A bird is the leading explanation: its brightness beats at 2.1 Hz ...

This call is wrong. The flicker result for the object was 2.13 Hz, 15.5% amplitude, 16x its band,
half-power 1.51–2.29 Hz. The background apertures peaked at 6.2, 7.3, 11.4 and 2.6 Hz, so the run
counted the beat as the object's own.

### Why it's wrong

#### 1. One contrast dropout carries the whole beat

The object crosses a large hot (white) rooftop at **frames 131–138**. Its ring-subtracted brightness
falls from about 4,800 to about 0 and goes negative (−1054, −82, −330, 345, 189, 100, then 4688, 910).
In crops the spot disappears against the roof and comes back past it. This is the background, not the object.

Check: interpolate the object curve across frames 131–138, plus the edge frames ≤4 and ≥205, using
the same 15-frame detrend, Hann window and 16× pad:

| curve | peak | amplitude |
|---|---|---|
| as run | 2.13 Hz | 15.5% |
| dropout interpolated | 3.31 Hz | 5.3% |
| frames 5–94 only | 2.21 Hz | 8.7% |
| frames 140–204 only | 3.52 Hz | 8.6% |

5% at 2–4 Hz is the grain level: planted constant-brightness dots encoded like PR135 beat 5–7% there
(see the `ABOVE` comment in `flicker.py`). Of the 22 sliding windows, only three pass (frames 94–153,
101–160 and 108–167), and all three span the dip, at 41–52% amplitude.

**The background-aperture control can't catch this.** The hot roof lies on the object's path, not at
±25 px beside it. Any clip where the object crosses a high-contrast background will do the same, and
look-down urban and coastline clips are the main risk.

#### 2. The detrend makes a ~2 Hz peak out of slow drift

Subtracting a `DETREND = 15`-frame running mean at 30 fps acts as a high-pass filter near 2 Hz.
When slow drift (red noise) goes through it, the spectrum peaks just above the cut-off.
Null test: 2,000 random walks of 204 samples with white noise added, through the same processing
(`LOW = 1.5`). Peak-frequency percentiles were 1.61 / 2.26 / 3.09 Hz (10th/50th/90th), and
**64% peak in 1.5–2.5 Hz.**

`report.WINGBEAT_HZ = (2.0, 25.0)` starts inside this artefact band.

#### 3. The "double" reading doesn't help

If 2.1 Hz were a second harmonic, the flap would be about 1 Hz. That fits only the largest birds, and
it's also about an aircraft strobe's rate. Separately, every window in `fields.windows.object` reports
`fundamental_hz = hz/2` and `double_hz = hz`, even where no half-frequency peak was checked (e.g.
frames 3–62: `hz` 2.47, `fundamental_hz` 1.23). Check whether this is always filled in. If it is, the
report could name a "double" that was never tested.

### Suggested fixes (as written then; what was done, and what was not, is above)

1. **Dropout / occlusion mask in `flicker`.** Flag frames where the object's ring-subtracted
   brightness collapses (e.g. below some fraction of its running median, or ≤ 0). Report them, and
   leave them out of the spectrum or fill them by interpolation. If more than N% of frames, or a
   contiguous run, are masked, say there is no power. Also report which frames drive a passing window.
2. **Red-noise null for the beat.** Test the peak against random walks fitted to the object curve's
   own low-frequency power (or phase-randomised surrogates), as well as against the background
   apertures. Or raise `WINGBEAT_HZ[0]`, or the effective low limit, above the detrend's artefact
   band, which depends on `DETREND` and fps.
3. **Gate the conclusion.** In `report.py`, don't name "a bird is the leading explanation" from a
   whole-track beat unless at least one sliding window passes away from any masked frames, or most
   windows agree on the frequency.
4. **Golden test.** Add PR23 as a negative golden: expected result is no beat, or a beat flagged as
   dropout-driven. It sits next to PR135, which should still beat at 7.1–7.9 Hz.
5. Check the `fundamental_hz` / `double_hz` filling (point 3 above).

### What PR23 does show (unchanged)

A single airborne object (it crosses over rooftops) moving in a straight line at a steady
247 px/s (248 against the striated layer, 244 against the isotropic) for about 7 s. Direction 62°
from screen-up. The north pointer was solved on 70/70 frames, so D18's "flying west to east" is
checkable. There is no angular scale, so there is no speed or size. It stays INDETERMINATE in
`video_adjudication.csv`.
