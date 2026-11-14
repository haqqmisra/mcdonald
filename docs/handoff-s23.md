# Handoff: session 23 (2026-11-13, from 15:05) -- nine strands of the ROADMAP's open items, each on a branch of its own, merged into `s23` as they finish; nothing on `main`, nothing versioned or pushed

**Jacob, 2026-11-13:** "Two other sessions are currently working on GPU development and triangulation/drift/hover
features for mcdonald. In this session, keep going with other outstanding items on the ROADMAP in a logical order,
coordinating with the other sessions as needed. Feel free to spawn agents as needed. Run jobs on /slurm on arthur
and/or merlin, and cannon is also available."

This file is the session's record in the repository; `docs/handoff-v04.md` stays the usual handoff (the GPU session
writes it). The working record, with every agent's id, brief and notes, is `/scratch/mcdonald/s23-2026-11-13/`
(`COORDINATOR.md` first). **State at 18:15 on 2026-11-14: all nine strands merged and tested; at Jacob's word ("Merge
all now, local") `main` is fast-forwarded to `s23` (fe96011, not pushed, still 0.5.5) and the data folder's
controls table swapped; the 144-video catalog run nearly done.** The session ran on Fable until the usage limit stopped every agent twice (16:19
and ~23:45 on 11-13), and on Opus 5.5 from 07:26 on 11-14 at Jacob's word; each agent resumed from its own
transcript. arthur was shut down for its fans (11-13 20:35, 11-14 ~13:00) and the queue paused twice.

## Where it stands (read this first)

`s23` (worktree `/hugespace/models/mcdonald-s23`, 15c4587) is **`main` as it stands (0.5.5 and the GPU session's
rounds through 6263ce0) plus the nine strands and one fix** below. Nothing of it is on `main`, nothing versioned or
pushed. **Every suite and every golden passes on it, on CPUs and with the card** (arthur runs 20261114-170237 and
-170248-s23-15c4587: test_golden 266 PASS, 0 FAIL, 0 SKIP; test_gpu 153 on the card; test_gui 791 + 1 skip earlier),
**except ten checks of test_controls**, which compare against the data folder's table of record: the small strand
remade the record in the code; the table is swapped with the merge into `main` (it is shared with `main` and the other
sessions; the strand's `holds/rejudge/SWAP.md` has the three commands). Against the new table test_controls passes
whole, 118 of 118 (job 2278).

**The fourteen reference case files measured again on the full tree** (gate `final1` against `gate/ref-4847926`, main
4847926's CPU reference; `coord/gate_diff_final1.txt`): **0 conclusions differ**; 22 bottom lines grow, every old
sentence kept; the numbers that move are exactly the scene strand's (PR41's pointer read on 259 frames instead of 134,
-0.413 to -0.409 deg/s; PR113's held share 48 to 46 %; PR088 object 2's 0.9924 to 0.9897); words change by the scene
strand (the background) and the hang strand (tether's sentences on 30 objects); the rest are additions (kin, beat,
small, hang). After main's later rounds (`final2`, c649965): 0 differences from `final1` at one part in a billion.

| strand | ROADMAP | merged as |
|---|---|---|
| drift | 0.5.x: `drift`'s report-changers DR2-DR5; PR051 as a known answer (DR1, in part) | 9aea557 |
| groups | 0.5.x: M7 with B23, S14, E21 | f25311f |
| kin | 0.4.x: Av11, Av10, A16 (set aside), D8 | 7037f60 |
| plant | 0.6 objective 4: planted objects (design, CPU path, pilot) | 1c933da |
| scene | 0.5.x: GL4 and GL5 (PR058); K10 not merged -- **a report-changer** | 5fc8cbf |
| batch | 0.6 objectives 1 and 2: `mcdonald batch` (the catalog's table and page to come) | 742108e |
| (fix) | `integrity` near the picture's edge (found by the catalog run) | 5c19921 |
| beat | 0.3's leftovers: K2, T2, E11, the band search, as readings | fb5ef54 |
| small | W8, shake fields, `_overlay_drawn`, the cadence rule, E15, test_cli; the controls' record remade | fcac2f5 |
| hang | 0.5.x, H5: "does something hang under it?" -- **a report-changer** (tether's words) | 51f4006 |

Method sections: 54 batch, 55 hang, 56 scene (used 1, 41 and its own), 57 drift (used 34), 58 small (used the stages'
own), 59 beat, 60 groups, 61 kin, 62 plant. **Do not delete the `mcdonald-s23-*` worktrees or the scratch folder until
`s23` is on `main`.**

## What is merged on `s23`

**drift** (merge 9aea557; the agent's CHANGELOG entry is under Unreleased). The own-track errors from the rays' own
scatter where they fit better than the errors given (DR3); the heading box tested against the aircraft's positions,
and a constant error of the display's azimuth reference carried (DR2); the wind's change with height from 8,125
radiosonde soundings, so one wind far from the object's height no longer decides T2 (DR4); pieces leaving at a
flier's rate fail with no depression given, and T3 quotes the track's own floor (DR5). Known answers against `main`
3459561: the Yemen video and the Santa Barbara hoist, no difference; the Puerto Rico lanterns keep every outcome and
their verdict, and three quoted numbers move (T1 -0.60 +- 0.04 to +- 0.05 m/s; T2's "two errors of the fit" 1.0 to
1.3; its tolerance 10.18 to 10.50 m/s). PR051's second leg is a golden of the own-track route, from readings an
agent made and no person has checked. Not built: the reader for the data bar, the two-leg fit, W7. The data folder
gained `winds_igra/` (41 MB; Cannon's copy of the folder lacks it).

**groups** (merge f25311f). Two calibrated readings beside the unchanged `rigid` call: `one_body` (one rigid body or
several, from what is left off the best rank-3 fit of the centred positions) and `places` (the members keep their
places or wander, from every separation over the group's size). "Moved" only where the wander keeps going (KPSS
against a block bootstrap of the series itself), stands over a line drawn on rigid groups carrying the detector's
real errors, and is over a pixel; NO POWER under four members or 60 shared frames. On drawn nulls 0 of 32,640 false
"wander" and 0 of 32,640 false "several"; PR135's six read several and wander, the drone show's 20 groups of six one
body that keeps its places. No reference report changes (no case holds a group).

**kin** (merge 7037f60). Av11: the speed in body lengths a second, a lower bound, against a 33-row class table in
which every number carries its source (`class_envelopes.csv`, `envelopes.py`); on 209 Galileo aircraft a median 0.72
of the truth, above it in 1 %. Av10: a turn's rate against each class's sourced limit load. A16: tried and set aside
(a crossing reads the blurred image). D8: which missing unknown would settle the most of two questions about the
speed. All 31 reference objects are NO POWER for Av11 and Av10; additions only on the fourteen cases (each report
gains about 22 lines, "Which missing quantity to ask for first"). New suite `test_unknowns`.

**plant** (merge 1c933da). `mcdonald plant`: synthetic objects written into a clip's frames and encoded again with
the clip's own settings, a control stretch beside it, a truth table, the planted video marked as a test article
everywhere. The pilot (50 stretches, 2,748 points): Find lists 56 % (52-60) of constant points, 11 % under 15 DN to
100 % over 120 DN; flock members 37 %, formation members 25 %; 5 of 2,748 paths "found" where nothing was planted.
On the labelled set a copy written whole is listed 74 % against its object's 80 %. About 13 CPU-s a planted point,
Find 41 % of it, so the plants do not need Find on the card. Found: Find folds a dark point into a bright one
crossing within 30 px (PL2). New suite `test_plant`. No reference report changes.

**scene** (merge 5fc8cbf). GL4: on PR058 there was no lock -- templates matched well along the sea's streaks but did
not agree, and "nothing found" was written as "held still". `layers.LOST` (such a pair is not counted as held; 0 of
5,213 held pairs on five still cameras) and `layers.scene_state` (where `scene`'s blocks read the background moving
beyond 1 in 100 by chance, the report says so). GL5: `symbology --method hue` reads PR058's magenta pointer (613 of
615 frames) and five more pointer clips. **A report-changer**: words on 17 reference objects, a sentence on 8 more;
PR113's held share 48 to 46 %, PR088 object 2's 0.9924 to 0.9897, PR41's pointer -0.413 to -0.409 deg/s; no rate
moves; exercise pages 01 and 04 quote the new first lines. The side-by-side table is in `scene/notes.md`. K10 not
merged.

**0.5.4** (merge 417c2b4): released by the Triangulation session from 4847926 on 2026-11-14 (N3 revised,
test_controls in the suite lists, the GPU session's work). The four strands' CHANGELOG entries, which the merge put
under "## 0.5.4", were moved back under "## Unreleased".

**batch** (merge 742108e). `mcdonald batch`: a unit is one video (frames once, Find over windows of 400, spots seen
on 40 frames or more made objects, the first 12 measured through `run --each`), a folder per video with a
`.mcdonald` file and an audit sheet per object (E8), and over the corpus `batch.tsv`/`batch.json`/`batch.md`;
`--pool` here or `--slurm` (arrays by size class, no site names), `--status`, `--table`, resumable, depths for the
plants. Its gate: 0 differences. **The catalog run** (all 144 videos, from a snapshot, started 11-13 22:36): stopped
and resumed on purpose, through two pauses and two shutdowns; 88 done at 14:00 on 11-14, none failed but the
integrity cases below; done about late evening. Rows are not objects (PR088's one bird in seven rows; PR135's flock
as two group rows, both named a bird); PR113's transit and PR43's streak are counted as "seen too briefly".

**The `integrity` fix** (5c19921, found by the catalog run, diagnosed by the batch agent): the self-test failed on 6
of 321 cases (objects 21 and 71 px wide near an edge), because three windows grow with the object while their
margins were fixed. Only cases that raised change. A drawn test sorts last in test_measurement.

**beat** (merge fb5ef54). Four readings beside the beat, none of which changes a call: the beat in the position
(K2, `beatpos`), a line in each look-alike band against the background's own search (`beatlines`), a beat's depth
and width on a look-alike near 10 Hz (T2, `beatshape`), and the look-alike mark's base rate (E11: 69.5 % of the
bird band at 30 frames a second). test_controls gives main's lines exactly; 0 of 432 labelled rows move; on the
fourteen cases additions only (21 bottom lines grow; the E11 clause in 17). Where a reading disagrees with the call
(PR089 object 3, PR085's GL6 lead, PR077, flyer 3, a helicopter control, PR097 object 4, PR099 object 3), the
strand's notes list each.

**small** (merge fcac2f5). `horizon` refuses a duct (kappa of 1 or more: NO POWER) and says which way refraction
breaks each bound; the shake test's both axes as fields; PR-016's false "possibly added" (the birds' dark rings read
as a drawn line; the labelled set flags 0 of 431 before and after); a held-picture cadence read in blocks of 60
frames (IR_DRONE_059 and IR_DRONE_098 lose their 10-Hz "bird" calls; no named bird lost); the zoom's discontinuity on
five real clips (placebos 0 of 46 call a step, but its interval measures real drift); test_cli's failure message. And
the controls' record remade in the code (RECORD; the data folder's table at the merge into `main`: the strand's
`holds/rejudge/SWAP.md` has the three commands).

**main's later rounds** (194f9cf, ace76de): the GPU session's speed-ups after 0.5.4, the same numbers sooner (`layers`
on the CPU in about half the time with 4395ed8). The scene strand's `lost_pairs` and main's `_by_pair` both rewrote
one line of `layers.measure`; the merge keeps both.

**hang** (merge 51f4006). `tether` answers "does something hang under the object?" on every object: hangs, beside
it, nothing tied, cannot say. "Hangs" is a line within 18 degrees of the picture's vertical (a random line lies that
close one time in five; the smallest round value that keeps AARO's known balloon PR-004). Null: 0 of 160 null tracks,
2 of 68 objects with nothing known under them (PR097 objects 7 and 8, a neighbour flying under the bird: the false
alarm of record), 9 of 9 known answers. PR105, PR28's stem and PR071 hang; PR29 nothing tied. Run once on 434 tracks
it had not seen: 2 hang (a ground band keeping pace). The scene's roll is now read from the shifts across the scene's
motion (a similarity fit gave PR105's clouds a 34-degree roll). Nothing in the headline.

## Found on the way

- **`tests/test_controls.py` is in no suite list and fails on `main`.** At 0.5.3 (a72784c): 117 PASS, 1 FAIL (0.5.2's
  four tether goldens are unclassified). Since a49d5b6 (the Galileo fixes; N3's rule for a beat that comes back): 107
  PASS, 11 FAIL: two bird controls lose their beat, four rows of the labelled set's table move (9 of 432 rows
  judged again, every one `comes_back` True to False; named birds 30 to 28 of 125). Found by the small strand,
  bisected by the coordinator (jobs 1496, 1497) and again by the GPU session. **Jacob decided the same evening:
  revise N3, measured first, and add test_controls to every suite list**; the Triangulation session is doing both on
  branch `n3-revise` (its 4847926, reported 22:00: each window's chance from the clip's own background apertures put
  through the object's windows, floored at 0.02; all 30 named birds of the record kept, one row of 432 different
  from the record, the Galileo clouds' false beats 14 to 5 and the aircraft's 3 to 0; test_controls 118 PASS, 0 FAIL
  on its tree; to be merged to `main` when its goldens pass). `test_breaks` and `test_phone` are in no list either, and `mcdonald-test`'s lanes (the
  `harvard` skill) lack `test_drift`, and will lack `test_controls`, `test_batch` and `test_plant`.
- **PR051, `test_pr051_released_track_against_the_scene`.** The drift and scene strands each measured it: while the
  gate held the object in the ULTN hold the scene streamed behind it at 0.78-0.97 of the rate the data bar gives; in
  the 4X hold the rate (210-230 px a picture) is beyond either stage's search, so nothing can be said, and the
  check's "the camera was not turning against the ground" is not supported. Neither strand edited the check.
- **After a reboot Slurm kept the suspended jobs as lost, still marked SUSPENDED**, holding 88 GB in its books until
  Jacob ran `requeue-lost-jobs.sh`; they then ran again from their start.

## For Jacob to decide (collected as the strands report; each strand's notes have the full lists)

1. ~~`s23` into `main`~~: **done** at Jacob's word, 11-14 ~18:00 (main fe96011, local); the controls' table swapped in
   the data folder (all 7,110 checksums pass; test_controls 118 of 118 on main, job 2446). Still his: the push and a
   version, after reading the changed sentences (scene's table, hang's words, beat's, kin's, groups'). Cannon's copy
   of the data folder is synced by the Triangulation session when the FASRC login is reopened.
2. **plant, forks F1-F10** (`plant/notes.md`; F9: completeness against the contrast after the encoder; F10: the
   planted rate beside the labelled table) and **the full run** (500 points a video on 144 videos, about 320 CPU-hours,
   a night on arthur, as batch units once batch is merged): what is planted, how it moves, what stands for the clip's own
   settings, what counts as found, how much of the chain, how many and where, a burned-in label, where results
   live. The pilot runs on the agent's recommendations; nothing larger starts without a word.
3. **drift**: the azimuth reference's default error (none; 0.3 deg as built; left to the rays, which makes the
   lanterns' verdict "cannot say"); what happens to the PR051 scene check; whether PR051 may be named in method
   section 34 yet; whether the checkpoint commits are squashed.
4. **scene**: whether the report takes the blocks' rate where `layers` holds a zero and `scene` reads the
   background moving (as built the rate stays "as the camera held it" and only the words change); the changed
   sentences on 20 of 31 reference objects; exercise pages 1 and 4, whose quoted first lines change; the first
   line's words where the background may move faster than the search (PR051's 4X hold).
5. **hang**: ten decisions in `hang/for-jacob.md` (the 18-degree gate, "hangs" kept out of the headline, PR097's
   two birds as the false alarms of record) and every new sentence in `hang/words-for-jacob.md`.
6. **small**: the horizon's band of kappa stays 0-0.25; the cadence rule's blocks of 60 frames and "more than
   half"; `_overlay_drawn`'s two thresholds; whether other integrity tests' printed numbers become fields too.
7. **kin**: a known quantity "the camera stood still" (the only way Av11 and Av10 speak inside `run`); D8's table only
   where some unknown is bounded; the class table's stated rules; whether "too long for the limit" changes a verdict.
8. **groups**: which reading the report's group sentences follow (`places` recommended; IDEAS RG3); nine sentence forms.
9. **batch**: a row of the corpus table is not an object (one bird in seven pieces on PR088; a flock as one row on
   PR135); a second pass that splits a group into its members; the 40-frame rule, which leaves out PR113's transit
   and PR43's streak; every stage for every object as the default.
10. **beat**: the new bottom-line sentences and the E11 clause (it changes a sentence released reports already
    carry: 17 findings); ten judgement calls in `beat/notes.md`; what to make of the readings that disagree with the
    call (PR089 object 3, PR085's GL6 lead).
11. **small, more**: N7's held frames left out of the Lomb-Scargle reading (a loss of power); whether E15's interval
    caveat belongs in the stage's own words.
12. **The record of the controls**: remade on s23 (small's 8e8fa62); the data folder's table swapped with s23's merge.
13. **Sizing the next catalog run**: the slow objects were the queue's pauses and `layers`' first pass, not the third
    (the GPU session's measurement); a batch job given the card, or 4395ed8's halving on the CPU, is the lever.
14. **How hard agents may load arthur by day** (asked 2026-11-13 16:15; never answered, so "as before").

## How it ran (for next time)

- Nine agents at once, with two other busy sessions, reached the account's usage limit about 45 minutes after
  launch (16:19). Jacob restored usage at 19:29; agents were resumed in stages. At 20:20 arthur and merlin were shut
  down for a hardware check, and resumed again at 21:20. **An agent stopped by a limit or a reboot resumes from its
  own transcript** (a message to its id); what made that safe was a checkpoint commit and a current notes file
  before each stop.
- Date an agent's stop from its files and jobs, not from when the notice arrives; run `date` before writing a time.
- A paused queue tightens "everything through Slurm": one agent ran a numpy job by hand during Jacob's pause for a
  fan diagnosis, and it had to be reported to him.
- The fourteen-case gate (`/scratch/mcdonald/s23-2026-11-13/gate/`) asked 8 GB a task, eleven at once, which is all
  of arthur's job memory; from measured peaks (PR088 4.9 GB) it asks 6 now.
- With the catalog run and nine strands' jobs, a 48-CPU niced suites job did not start on arthur; the same tree on
  Cannon's `test` partition took minutes (golden in 36 min).
- The usage limit stopped every agent a second time (~23:45); on 2026-11-14 Jacob switched the session to Opus 5.5 and
  the agents resumed under it from their transcripts. Commits from then on carry Opus 5.5's line.
- Merging a released `main` moves an "Unreleased" heading's entries under the new version's heading: move them back.
- Every strand that adds a test function to `test_golden.py` needs its line in `test_controls.GOLDEN_KINDS`.
- A shutdown leaves Slurm's running jobs marked RUNNING as ghosts holding the CPUs until `requeue-lost-jobs.sh`; the
  Cannon login dies with arthur's reboot (only Jacob reopens it), so test on arthur (`mcdonald-test --on arthur`) then.
- A wall-clock time across a queue pause includes the pause (a suspended job's clock runs): the catalog's slowest
  "objects" were the pause.
