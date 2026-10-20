# Handoff: the beat's controls (branch `beat-controls`, worktree `/models/mcdonald-beat-controls`)

Started 2026-10-20 from main at 35fde2c, at Jacob's word ("start on the mcdonald improvements on a branch"), after two
analyses in the uap repository on 2026-10-19: the chain-rate table for the bird paper (every Table 1 beat against the
rhythms of the sensor chain and the sky) and the bird test on the Svanström et al. 2021 labelled infrared set (432
tracks of birds, airplanes, drones and helicopters). ROADMAP 0.3 objective 4 and 0.5's controls. Not merged.

## What is on the branch

1. **Look-alikes that are bands** (`flicker.LOOKALIKE_BANDS`, `fold_band`; item 11 of flicker's docstring). Beside the
   exact lines (50, 100, 60, 120, 400, 800 Hz; fps/3-6; held pictures; the clip's own sound):
   - the 400-Hz power as aircraft sound records it, 398.41-401.27 Hz (8.41-11.27 Hz at 30 fps, 8.80-11.66 at 29.97),
     and a lamp on it at twice that;
   - a bundle of candles near 10 Hz and a sky lantern's puffing at 4.7-8.7 Hz (not folded; each flame its own phase);
   - a rotor's (10-30 Hz, and doubled for an odd blade count), a turboprop's (50-150), a multirotor's (150-300)
     blade-pass and a cryocooler's drive (40-80): these fold over the whole band at video rates (`covers`), so they
     mark nothing and the notes say once that frequency excludes none of them.
   A beat inside a band is marked as a line is ("marked, not refused"); the finding says "inside the band of ...".
   The mechanical bands are nominal (the infrared survey's, not measured); the flames and the buses are sourced.
2. **Steady as a clock, or not** (`flicker.steadiness`; item 12; the information-theory survey's D2). Over the whole
   stretch the object was followed over (not the beat's own stretch, which is one 2-s window where that is clearer --
   PR135's C-F, which the first golden run found "too short to split"), each piece searched about the beat: two halves (4-s pieces past 8 s), each fitted by least squares (sinusoid + quadratic,
   frequency on a grid within 0.6 Hz or 10 % and refined within half a resolution), compared in their Cramér-Rao
   bounds; 200 steady beats planted at the frequency with each piece's own amplitude in the pieces' residuals (0.5-s
   blocks) read the same way; p, and `wanders` = p < 0.01. In `fields["steadiness"]`, the text report, and the
   look-alike note's "a supply holds its frequency, a wingbeat's wanders" sentence, which until now had no control.
   A stretch under 2 x MIN_FRAMES is not read (NO POWER). About 1.2 s a beat (vectorised normal equations).

Both are readings. No call, gate or headline changes.

## Tests

- `test_measurement`: `test_look_alikes_that_are_bands_and_those_that_cover_the_band` (the folds, the covering bands,
  marks at 8.5 / 3.5 / 10.59 Hz, a planted 6-Hz beat marked with the lantern band and the note said once);
  `test_steadiness_tells_a_clock_from_a_beat_that_wanders` (12 planted steady beats: at most 1 called wandering;
  8 that step 7.4 -> 7.8 Hz between halves: 7 or more called; 100 frames not read; a 20-s stretch in five pieces;
  the stage carries it). **One existing check changed premise:** the look-alike test's beat "clear of them all" was
  8.5 Hz, which is now inside the lantern's and the heard bus's bands; it is 3.5 Hz now (the comment says why).
- `test_golden` (PR135's flock): every member's steadiness read; and at least three of the six wander beyond a clock.
  The second is an expectation written before the run (the case files gave p 0.005-0.035 one member at a time, with
  the paper's aperture; the golden test measures the six together in the default aperture).

## For Jacob to decide

1. **The reference case files will not rerun `--strict` to their numbers** once this merges: `share rerun` compares
   every stage's fields, and `steadiness` and the new look-alike rows are fields the files do not have. Either remake
   the files at the release (they are made by `tools/rerun_cases.py`' route), or teach `rerun` to list fields the old
   case lacks as additions, not differences. Nothing here does either.
2. **The bird headline's amplitude floor.** On the Svanström set the beat's amplitude separates true from false bird
   calls (AUC 0.96): birds' called beats a median 15-18 % of their brightness, false calls 1.8-2.3 %; an 8 % floor set
   on birds and airplanes left 2 of 307 non-bird tracks called, the held-out drones and helicopters included. It was
   chosen after seeing the data. Not on this branch: it changes the headline, which is your rule (2026-10-17). If you
   want it, the honest route is to fix the number now and run it once on sets it has not seen (AARO's resolved cases,
   the Galileo flyers and Sphere footage).
3. **The lantern band marks most bird beats** (4.7-8.7 Hz holds PR135's six, PR41, PR085, PR097, PR099, PR141). That
   is true -- a flame is a per-object, own-phase look-alike the members-apart argument does not touch -- but it puts a
   look-alike sentence into most bird findings. Keep it, or list it in the table without marking.

## Next, in the order the 2026-10-19 analyses put them

1. **`pictures()` misreads two chains** that give a fresh picture every frame (Galileo Sphere; Svanström, ~24.7/s with
   ~18 % "held" on IR_BIRD_040): the whole-frame thumbnails see the encoder skipping a static sky. Read held pictures
   from blocks that change (or the object's own region), and check PR44 (truly 14.9/s), PR141 (23.8), PR097 o8 and
   PR27 do not move. It moves `top_hz`, so it is a golden-number change and wants its own commit.
2. **The scene's own motion at the beat** (a cooler's or gimbal's jitter): Lucas-Kanade of each band-passed frame
   against the stretch's mean frame (frame to frame where the scene pans), with a planted sinusoidal shift as its
   test -- prototyped in the uap repository (`analysis/tools/pr135_chain_jitter.py`: a 0.05-px plant recovered at
   0.79-1.23 on all 27 Table 1 objects; no Table 1 beat is a jitter). Phase correlation was tried first and locked onto
   the IR fixed pattern. Costs a decode of the stretch, so an option or its own command, not every run.
3. **A background-crossing check**: the Svanström helicopter false call (21 % at 2.1 Hz) was a fence line passing
   behind it, which apertures 25 px away do not see.
4. **The controls harness (0.5)**: the Svanström labels as tracks in the data folder (the uap repository's
   `analysis/sweeps/svanstrom/svanstrom_mcos.py` reads the MATLAB groundTruth with scipy alone; copy, do not point),
   and a suite that holds the bird test's call rates on it.

## Traps paid for

- An unbounded peak search in each half (the padded spectrum's maximum within 0.6 Hz) has no power: the planted clocks
  scatter to 0.3-0.6 Hz, far over the bound. The survey's bounded least-squares refinement is what makes D2 work.
- Plant the clock with the record's own amplitude envelope, piece by piece: a whole-record amplitude on a beat that
  wanders is small, and the clocks then drown in noise (PR088's object 2 read p 0.98 that way).
- At exactly 30 fps, 50-Hz mains, a lamp on it, and 400/800-Hz power all fold to 10.000 Hz; a beat there that holds
  steady (PR077: halves 9.907 and 9.896 Hz, p 0.90) is not cleared by steadiness.
