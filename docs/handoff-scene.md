# Handoff: the scene under the sensor's pattern (branch `scene`): B3, B4, then every video

Written 2026-11-01 at `ee1f512`, brought up to date the same night after steps 0-5. Sections from "What is known" down are the original audit, kept as written;
where a later result overturned one, the note under "Traps, as they came out" says so.

## Where things stand

- **Branch `scene`, worktree `/hugespace/models/mcdonald-scene`.** Local only. Pushing any branch is public, so ask first. Every push to `main` is a release, so nothing here
  goes to `main` until the maintainer says. Work folder: `/scratch/mcdonald/scene-2026-11-01/` (`env.sh`, `snap*`, one folder a step, `logs`).
- **Done: steps 0-5.** Step 0 reproduced to 0 difference. `scene.py` (B4), `layers.read_scene_under` (B3), `mcdonald scene`, the gate frozen at `bcb9fac`, the census written to
  `~/research/uap/analysis/sweeps/scene_census.{md,tsv}`, not committed there. Method section 38, README-technical, agents.md, CHANGELOG (Unreleased) are written.
- **Not done: step 6 (each consumer), and the window's words in step 7.** Both wait on the maintainer's decisions below. `run` does not ask for the reading, so no report and no window changes.
- **Suites:** all green at `fa633fe`, see the last section.

## What came out

- **The gate** (`scene.judge`; method 38): frozen, z 15.2, 1 reduced px/frame, not on the search's rim, stack against -v 1.4 (coded null's p99 1.38), the two halves' coherence 0.07 (above all 258
  still-camera searches, 0.068). **0 of 326 blocks with no scene read, 95 % bound 0.91 % a block:** 86 still-camera blocks and 240 coded blocks with no scene. 650 real sky blocks: 25 read,
  looked at by eye, 22 plain scenes, at most 3 not plain.
- **Known answers.** PR144 0.6-1.1 % on three blocks, 2.9 % on the fourth. PR41 23 of 23, r 0.97 over +-120 frames. PR088 object 2 r 0.72, 1,005 px/deg, no shift of 48 reaches it. Soccer: every read inside
  what the camera did, about 5 % where the pan is steady, and one of the runs where it reverses inside the block. Planted: real noise 0.5-1 DN, none at 0.25. PR099 object 3: templates 10 of 21 pairs.
- **The census.** 144 videos: 89 with a block read, 36 with half or more; 430 of 1,520 blocks. Open 31 %, held out 23 %. The held-out third was opened once, after the gate's commit, and nothing changed after.

## PR135 is not refused, on purpose

The "Done when" asked for PR135 refused. **It reads 15 of 29 blocks, and the handoff's label was wrong.** It was called empty sky, a coder's artefact. Evidence it is not: the private case notes have an MQ-9 looking
down past an island; the readings run smoothly from the frames where the island visibly leaves at -9.6 px/frame out to -18.5, so -16 is a value it passes through and not a lattice lock; the literal stack at frame 781 is a picture
along v and a smear along -v; the two halves agree (0.12-0.29, against 0.068) on frames 475-1107 and at 1739; and x against the pointer gives 1,462 px/deg, inside the 995-1,723 of the 0.643-deg field at that look-down
and outside the wide field's 178. **The weak part:** the pointer's correlation is only suggestive (r 0.60, 2 of 18 shifts reach it), and blocks 1180-1320 are the least sure (halves 0.02-0.12, neighbouring blocks disagree on v).
Refusing the clip would have taken a rule fitted to it. What the surface is was not decided, and stays the maintainer's word (trap 11). If this holds, PR135's "object against the scene" of 103 px/s is against a scene moving at 200-550 px/s.

## Decisions for the maintainer

The original three stand, and two came with the results. Put together:

1. **The report's words** for a scene read this way, and whether it replaces NO POWER or stands beside it. Recommended: beside it.
2. **Does `slew` take k from it unasked?** Recommended: on request. The soccer check is passed for what a block says, but only 2 blocks are steady enough for a number (about 5 %).
3. **Release.** Both B3 and B4 change the same reports: one release for the pair is simpler.
4. **PR135:** accept that it is not a null. Recommended: yes, with 1180-1320 kept as unsure, and the reference report's rate looked at again.
5. **Should `layers`' third pass stay?** It reads 10 of 21 pairs on PR099 where the block reading reads 7 of 8 blocks, and costs little. Recommended: keep it, as a second witness in the same CSV row.

## Traps, as they came out

- **1-4 closed by design:** a third pass's rows, cache and file are its own. `<tag>_layers.csv` is the same to the byte (test, and compared on real PR099), the cache key did not move, `still_again_share` and NO POWER are what they were. They reopen at step 6, each consumer by name.
- **5 changed:** PR135 is not the null. The coded null of step 3 takes its place, and the odd part's blind spot (it cannot tell a picture along v from one inverted along -v) is met by the two halves.
- **6:** a frozen picture has its own reason. **7:** a second place in S is kept, but PR41's are a tenth of the main peak, stack into a crosshatch and do not last: no parallax. PR099's, near zero, cannot be settled that way. Two layers in one block are rarely resolved.
- **8:** 400 MB a block's worker; 16 MB for the third pass. **9:** the upper band fixes PR144's slow low band; it is not believed under 4 reduced px/frame, where it snaps to a residue about zero. **10:** the floor is in the output. **12:** said in the method.
- **A new one, found on the census:** S steps up on a ring near 1 reduced px/frame, where the first lag drops out. PR123's "reads" held their speed and turned every block. That is the speed rule.
- **A new one:** the third pass must not use `_bad`'s masks: they cost the templates the field needs (36 to 21 on PR099, nothing read).
- **To look at:** PR143, PR26, PR075 and the top of PR133, PR100, PR056, PR052 read 45-60 px/frame, not far under the search's 90. Nobody has looked at them.

## What is known

`layers` matches templates between frames. On 13 of the 14 reference case files it says NO POWER: the scene is held still even over 30 frames.
Microscopy's immobile filter (STICS, Hebert, Costantino & Wiseman 2005), taken one step further to the odd part of the cross-spectrum, shows that
many of those scenes move under the sensor's fixed pattern. Anything that stays put has a real cross-spectrum, however it breathes with the gain;
a shift makes it imaginary.

| clip | `layers` held | reading | how it was checked |
|---|---|---|---|
| PR41 | 98 % | 25.5-31.6 px/frame on the object's frames, 12.6-31.6 over the clip | rebuilt independently; north marker r 0.92 over 23 blocks, null 10-35 against peak 130-320 |
| PR099 object 3 | 93 % | 25.8-29.0, mean 27.3; templates raw 0, block mean out 24.6-28.0 | rebuilt; a 40-lag search reads it on raw frames too (12 of 12), so "raw reads 0" is true of single-lag templates only |
| PR088 object 2 | 99 % | 12-24; follows the pointer, r 0.70, signs 55 of 55 | c bracketed at 652-1,349 px/deg; **a bracket, not a k** |
| PR44, PR079, PR077, PR085 | 52-100 % | 5.5-6.4, 8-13, 4-24, 3-6 | rebuilt; PR085 reads only in its object's window (4 of 7 blocks, 1 of 12 over the clip) |
| PR149 | 53 % | 15-27 past its track, 8 of 8 blocks | the survey called it unread on a short window; the rebuild corrected that |
| PR144 (known answer) | 0 % | within about 1 % of `layers`, but the top peak flips between its two layers | see trap 7 |
| Galileo flyers | still camera | none: 0 of 16, 0 of 24 | must stay none |
| PR135 | 100 % | none, empty sky, **but not clean**: see trap 5 | the hard null |

The smallest form, B3: each pixel's mean over a block taken out, then `layers`' own templates. It recovered 10 of 24 pairs on PR099 object 3, 3 of 24
on PR41, 17 % of pairs on PR44 and PR085 (PR085's y disagrees with the whole-frame reading: 1.5 against 3.0), none on PR079 and PR088 object 2. So B3
helps some clips, and B4 is what opens the others. PR144 does not move under B3 (21.0 against 21.5 px/frame).

## How to work here

- **Everything through Slurm**, niced, `--time` realistic. Load the `slurm` skill first. Heavy stages from a snapshot, never a live tree:
  `/scratch/mcdonald/v04-s13/suites/snap.sh` and `one.sbatch` are the pattern (one job a suite; test_gui 4 CPUs).
- **The editable install is `main`'s.** `python3 -c "import mcdonald"` from this worktree imports `/hugespace/models/mcdonald/src` unless told
  otherwise (checked). Tests insert their own `src`, and `tools/suites.sbatch` sets `PYTHONPATH` from the submit directory, but a script of your own,
  and any `python -m mcdonald.cli` subprocess, needs `export PYTHONPATH=/hugespace/models/mcdonald-scene/src`.
- **`export MCDONALD_DATA=/models/data/mcdonald`** in every script. From a worktree or snapshot, golden and the exercises otherwise skip cases and still
  say ALL PASS. Read the PASS and SKIP counts: golden is 195 PASS, 0 SKIP.
- **Keep `TMPDIR` short** (a long one breaks the forkserver's socket path), and not under `/tmp`, which is RAM.
- Thresholds come from a null with a stated false-alarm rate. A judgement call is flagged as one.

## The prototypes

In `/scratch/mcdonald/bio-survey-2026-11-01/microscopic/scripts/` (paths hard-coded to that folder; a copy is kept with the survey):

| file | what it does |
|---|---|
| `sticslib.py` (227 lines, numpy and scipy) | the whole reading: `frames`, `active_box`, `prep`, `qband`, `rmaps(odd=True)`, `vmap`, `best`, `analyse_block` |
| `cover.py`, `cover.sbatch`, `cover_jobs.txt` | the coverage table: 60-frame blocks, the low band `lo=0.012, hi=0.09`, the stack test. **Run this first** |
| `layers_im.py` | B3: `fr - fr.mean(0) + 128`, then `vf.shift_field_auto` and `vf.layers_of` |
| `stack_check.py` | shift-and-add at +v, -v, 0.8v, 1.2v and the rotations |
| `stics_series.py` | scene velocity against the north pointer |
| `stics_planted.py`, `stics_test.py` | drawn and planted known answers |

Their results are in `microscopic/out/cover` and `out/l3s`. The independent search is `/scratch/mcdonald/bio-survey-2026-11-01/verify-scene/scripts/`
(a different method: shift-and-add energy over 40 lags, +-120 px/frame), with its record in that folder's `notes.md`. Read that record: it holds the
reasoning behind traps 5 and 7.

Settings to carry: a block is 60 frames; `down = ceil(W / 660)`; pass = z >= 15.2 on the 234-block shuffled null and stack +v/-v >= 1.4 and the stack's
peak at v. **The 15.2 comes from that null; the 1.4 is a judgement call.** Sign: v is image motion, +x right, +y down, as `layers`' `all_dx5`. About 15 s a
block on one core.

## The work, in order

**0. Reproduce.** `cover.py` from the snapshot on PR144, PR41 and flyer 1. The numbers must match the table before anything is ported.

**1. B3 in `layers`.** A third pass on pairs the second pass left STILL, skipping UNMOVED pairs: block mean out, templates again. A new `how` value
beside `MOVED, AGAIN, STILL, UNMOVED` (`layers.py:96`). Read traps 1-4 first. Add a check in `test_measurement` beside
`test_held_still_pairs_share_their_second_pass`: a scene behind a pattern that breathes.

**2. B4, the whole-frame reading.** A function or a small module `layers` calls where `still_again_share` > 0.5 (line 628), so its cost falls only on
clips that need it. Port `sticslib`'s reading into the package's style; results through pools stay small. One row a block: start, velocity, z, the null's
z, the stack's ratios, passed or not, and the reason.

**3. Set the gate from nulls.** The rate per block on real coded frames with no scene: still cameras and empty sky. Report the false-alarm rate in the
method section. Replace the 1.4 with a tested number.

**4. Hold it to known answers.**
- Planted textures through the clip's own encoder: read at 1 DN rms (z 39-68), the slow one alone at 0.5 DN, none at 0.25 DN. Say that floor in the report.
- PR144 within about 1 %.
- Pointers: PR41 r 0.92, PR088 object 2 r 0.70, with the circular-shift null.
- **The soccer camera** (`ptzslam_soccer/`, every frame's pan known): the only full known-pan answer, not yet tried with this reading.
- Flyers none. PR135 refused.

**5. Every video.** A Slurm array (`%10`, 1 CPU, about 2500M) over the 29 local PURSUE videos, then the 144 release videos. 12 sampled blocks is about 3
minutes a video; every block of a 5-minute video about 40. The table goes to the private analysis repository, not here: which NO POWER clips get a scene,
at what speeds, by tranche, and which have a pointer for `slew`. This is the first time the reading meets clips it has not been tuned on, so expect to
learn something. Hold out a third of them before looking, as `tools/sweep/holdout.tsv` does.

**6. Downstream, one consumer at a time.** `slew` on PR088 object 2 under its normal refusals; `camera` and E3's index; `over_track`, then the report. M6's
field rotation and `waves` gain a scene on such clips (PR41 is the first case).

**7. Close the branch.** A method section (38, or the next free; renumber at merge), CHANGELOG, README-technical, the window's text in plain words, and all
suites plus golden and the exercises. Do not touch `propose`: it has its own `still_again`, and a change there needs `find_rank --link`.

## Traps, checked against the code

1. **Nothing downstream can see where a shift came from.** `slew.read_layers` (`slew.py:129`) and `camera.read_scene` (`camera.py:722`) read
   `<layer>_dx<k>`, `groups` and the errors. The CSV has no `how` column (`layers.py:541-549`), and `how` lives only in the cached `tpl`. **A reading written to
   those columns goes straight into `slew`, `camera` and the reports with no flag.** Requirement: no consumer takes it by accident. Recommended: a new
   provenance column, with `read_layers` leaving those rows out unless asked, until step 6 turns each consumer on.
2. **`over_frames` will lie.** Line 549 writes `k if how[n] in (MOVED, UNMOVED) else longer`, so a new `how` value is labelled `longer`.
3. **The template cache will serve stale results.** `made_from` (lines 496-502) names what the cache depends on. Add the new pass's settings, or an old
   `bg_layers_*.npz` comes back silently. Note that a fast test may be a cache hit. Adding them moves every cache key; the size-conditional at the end of
   `made_from` shows how to keep older caches valid where the new pass does not apply.
4. **NO POWER rests on `still_again_share`** (`h == STILL`, line 595; the words at line 628). A new `how` value lowers that share, so the warning goes away by
   arithmetic and not by decision, on pairs B3 read and on those it did not. `test_measurement` (lines 134, 138, 217) and the report both hold this. Decide what
   the warning should say when a share of pairs was read this way.
5. **The shuffled null does not hold a coder's artefacts.** On PR135's empty sky the low band gives (0, -16) px/frame at z 27 against a null of 5, with no scene
   to find. The survey's stack test refuses it (+v/-v 1.3), but the rebuild's rule, stack test included, false-read PR135 on 5 of 12 blocks at 6-10 px/frame, mostly
   on the y axis. So **the gate is not settled**, and PR135 is the null to beat in step 3. Flyers do not test this: their +v/-v is 1.00.
6. **A frozen picture breaks a pooled null.** PR113 frames 4431-4551 hold a still: shuffling changes nothing and the pooled maximum goes to 965. Pool only blocks whose
   frames change. Repeated pictures are the same kind of case: skip UNMOVED pairs, and read `repeating` first (`layers.py:216`).
7. **The reading keeps one peak, and scenes have layers.** PR144's top peak flips between its sea and cloud layers, 3.3 px/frame apart: that is the 98 px/s of method §1,
   known since the start, not a new finding. Keep two peaks. Weaker second peaks on PR41 near (0, -5) and PR099 at (5-11, -1), S 50-90, are unexplained: they could be a
   second layer, which would bring layer parallax to NO POWER clips, or symbols, or the coder. Find out which before any word of parallax.
8. **Memory.** B3 as prototyped holds 60 frames of float32 at full size: about 500 MB at 1080p, per worker, on 2.5 GB per CPU. A running mean per shared window, which
   `second_pass` already shares, should do it. Frames do not go through pool pipes ("Pool results must be small"; about 5 MB/s here).
9. **Slow scenes are the weak end.** The block mean takes part of a slow scene with it (PR085). The low band reads 10-12 % slow on PR144's fast first blocks, a bias of the 0.125
   px/frame grid, not chased. Fast textures at 4 DN were misread (z 5-7) while 2 DN read: probably the drawing wrapping inside the block, not run down.
10. **Coded clips lose faint motion.** Below about 1 DN rms the reading says nothing, so "no scene read" means none above that, not none. The report must say the floor, as it
    does for a beat.
11. **"The sea" is a reading of the streaks.** PR41's stack shows long parallel streaks. Report a velocity with its tests, and leave the word to the maintainer.
12. **Stretched pictures.** The reading is in file pixels. PR113 holds two stretches (ROADMAP F rows), and `slew` takes a `pixel_aspect`. Do not read scene speed as angle on a
    stretched clip without it.

## Reports and case files

This is a report-changer. `over_track` measures the object against the scene: PR41's "object against the scene" of 40 px/s is against a scene read as still, so a read scene moves
that line by a factor of about 20, and the report's NO POWER beside it goes. 13 of the 14 reference case files could change. `share rerun --strict` will then differ, and they are remade
only at a release, from the recorded commands (handoff-v04 has the recipe). Until the maintainer has seen the words, keep the reading out of the report and show it in the stage's own
output.

## Decisions for the maintainer

Ask these together, once, when steps 3-5 have numbers, by multiple choice with a recommendation:

1. **The report's words** for a scene read this way, and whether it replaces NO POWER or stands beside it.
2. **Does `slew` take k from it unasked**, or only on request? Recommended: on request until a known-pan check passes on the soccer camera.
3. **Release.** The ROADMAP has B3 in 0.4.x and B4 in 0.5. Both change the same reports, so one release for the pair is simpler.

## Done when

- Step 0 reproduced, and every suite, golden (195+ PASS, 0 SKIP) and the exercises green on the branch.
- PR144's `layers` numbers unchanged, and no clip that reads by templates today moves.
- A false-alarm rate per block stated from real coded frames, with PR135 and the flyers refused.
- Known answers held: planted textures, PR144, the soccer camera, the two pointers.
- No consumer takes a block reading unasked, and a test proves it.
- The census of step 5 in the private repository, its held-out third read once.

## Not on this branch

A small second reading round, a survey and not a build, after step 5: measuring a point spread function from stacked point objects (the body-length envelope has power on only 3 of 46
tracks, and today's plan is V9's slanted edge); flat-field estimation (BaSiC, Peng et al. 2017), which models a pattern that breathes with gain and may help where B3 falls short (PR088 object 2);
and kICS (Kolin, Ronis & Wiseman 2006), which separates blinking from transport. Those citations are from memory and unchecked, and none of the three has been tested. If step 1 stalls on
PR088 object 2, read the flat-field paper sooner.

## Suites at `fa633fe`

From a snapshot, one Slurm job a suite, 0 FAIL in all: measurement 568 (baseline 540, 28 new), reduction 558, camera 151, slew 65, share 25, cli 134 (133, one new), gui 763, golden 195 PASS 0 SKIP,
and aspect, audio, drift, focus, haze, horizon, published, stabilize, streak, sweep, tether, waves, zoom. Exercises: `test_golden --exercises`, job 19602, log in `/scratch/mcdonald/scene-2026-11-01/suites/logs/`
(its first run hit the 1:15 limit of `one.sbatch`; this one has 2:40).
