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

3. **A flame in the bottom line** (`report.FLAMES`, `Case.flame_said`): a beat inside the lantern's or the candles'
   band gets a sentence in the report's bottom line -- a flame keeps its own phase, so neither the beat nor members
   out of step clear it -- and `groups`' rigidity beside it where it was read (keeps its shape: a flame is not
   excluded; rearranges: as a flock does). The report did not read `groups` before. The headline is not touched.
4. **`flicker --scene-shift`** (`scene_shift`, `lk_shift`): the scene's own motion at each of the objects' own beats,
   off by default (it reads the stretch twice more, on the stage's pool). Every frame registered against the mean
   frame (frame to frame where it pans), tracks and graphics masked, 0.05 px planted at the beat as its test, the
   object's own centroid beside it (`curves` now collects each track's centroid, `moves`, from the same reading of the
   frame). Synthetic: a 0.3-px jitter read 0.300 px; still 0.0002 px, the plant back at 0.998; a flat sky not read.
   PURSUE (on the case files' tracks and apertures): PR077 o1 0.0002 px (plant 0.98, own 0.18 px), PR135 A 0.0015
   (1.05, 0.37), PR41 0.0004 (1.14, 0.75) -- the uap prototype's numbers again.

All are readings. No call, gate or headline changes.

**Tried and dropped: `pictures()` by the object's motion.** Scored against known answers (method §18's table), the
whole frame reads PURSUE's PR149, PR44 and PR135 to their truth; every rule that cut the Svanström false holds lost
PR149's real ones, and held frames' spacing does not separate them. Reverted; the misreads are in `pictures`'
docstring. A chain-specific fix (the codec's skip blocks, or a known-answer clip per chain) would be the next try.

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

## Decided (Jacob, 2026-10-20)

1. **The reference case files** will not rerun `--strict` once this merges (the new fields are differences to
   `rerun`): fine for now -- the reference cases keep improving on the way to 1.0.
2. **An amplitude floor on the bird headline** (the Svanström set: 8 % separated true from false calls, AUC 0.96):
   not now; the bird paper waits for its reviews. Not built.
3. **The lantern band marks most bird beats**: keep it. Not needed for the paper now, but it is a look-alike mcdonald
   must note and handle -- a flame is per-object and has its own phase, so the members-apart argument does not touch
   it; what can is in "Next" (groups' rigidity on night clips, and the rest of objective 4).

## Next, in the order the 2026-10-19 analyses put them

1. **The 10-Hz morphology tests** (objective 4's last item): the beat's depth along the track, its wander, the
   fixed-core width, for the two Table 1 objects near 10 Hz (PR077, PR088's object 2).
2. **A background-crossing check**: the Svanström helicopter false call (21 % at 2.1 Hz) was a fence line passing
   behind it, which apertures 25 px away do not see.
3. **The controls harness (0.5)** -- tractable on the new workstation (Jacob, 2026-10-20): the Svanström labels as tracks in the data folder (the uap repository's
   `analysis/sweeps/svanstrom/svanstrom_mcos.py` reads the MATLAB groundTruth with scipy alone; copy, do not point),
   and a suite that holds the bird test's call rates on it.

## Traps paid for

- An unbounded peak search in each half (the padded spectrum's maximum within 0.6 Hz) has no power: the planted clocks
  scatter to 0.3-0.6 Hz, far over the bound. The survey's bounded least-squares refinement is what makes D2 work.
- Plant the clock with the record's own amplitude envelope, piece by piece: a whole-record amplitude on a beat that
  wanders is small, and the clocks then drown in noise (PR088's object 2 read p 0.98 that way).
- At exactly 30 fps, 50-Hz mains, a lamp on it, and 400/800-Hz power all fold to 10.000 Hz; a beat there that holds
  steady (PR077: halves 9.907 and 9.896 Hz, p 0.90) is not cleared by steadiness.
