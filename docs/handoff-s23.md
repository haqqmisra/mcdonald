# Handoff: session 23 (2026-11-13, from 15:05) -- nine strands of the ROADMAP's open items, each on a branch of its own, merged into `s23` as they finish; nothing on `main`, nothing versioned or pushed

**Jacob, 2026-11-13:** "Two other sessions are currently working on GPU development and triangulation/drift/hover
features for mcdonald. In this session, keep going with other outstanding items on the ROADMAP in a logical order,
coordinating with the other sessions as needed. Feel free to spawn agents as needed. Run jobs on /slurm on arthur
and/or merlin, and cannon is also available."

This file is the session's record in the repository; `docs/handoff-v04.md` stays the usual handoff (the GPU session
writes it). The working record, with every agent's id, brief and notes, is `/scratch/mcdonald/s23-2026-11-13/`
(`COORDINATOR.md` first). **This is an interim state, written at 22:00 on 2026-11-13 while eight strands were still
at work**; it is brought current at each merge.

## Where it stands (read this first)

`s23` (worktree `/hugespace/models/mcdonald-s23`) is `main` 5e6c468 plus what is merged below. Each strand is a branch
`s23-<name>` in `/hugespace/models/mcdonald-s23-<name>`, started from `main` 3459561, built by an agent under one
common brief and a brief of its own. **Do not delete those worktrees or the scratch folder until every strand is
merged: several hold work that exists nowhere else.**

| strand | ROADMAP | state at 22:00 | last commit |
|---|---|---|---|
| drift | 0.5.x: `drift`'s report-changers DR2-DR5; PR051 as a known answer (DR1, in part) | **merged into `s23`** (9aea557); every suite passes on the merged tree (Cannon run 20261113-214000-s23-9aea557; no goldens in that run; the branch's own run had them, 234 PASS) | 7d5a17d |
| batch | 0.6 objectives 1 and 2: `mcdonald batch` | built, tested, piloted on 11 videos; **the 144-video run is going** (jobs 1656, 1658-1662; out `batch/catalog/`) | 7c0ab20 |
| hang | 0.5.x, H5: "does something hang under it?" | built; suites pass; second null, goldens, the fourteen cases and method section 55 under way | 5b7895b |
| scene | 0.5.x, GL4 and GL5 (PR058); K10 | GL4 and GL5 built; finishing runs under way; **20 of 31 reference objects change words** | c7a74fb |
| small | W8, the shake test's fields, `_overlay_drawn`, a held-picture cadence, E15 on real clips, a test_cli flake | items 1-2 done and tested; 3-6 built, their nulls and reruns under way | 57f83b0 |
| plant | 0.6 objective 4: planted objects at scale (design and the CPU path) | `mcdonald plant` built; cost and crowding measured; the pilot not yet run | 5ea36da |
| kin | 0.4.x: Av11, Av10, A16, D8 | resumed 21:27 after being held; work in progress | (checkpoint) |
| groups | 0.5.x: M7 with B23, S14, E21 | resumed 21:39; work in progress | (checkpoint) |
| beat | 0.3's leftovers: K2, T2, E11, the band search as a reading | resumed 21:53; work in progress | (checkpoint) |

Method sections reserved: 54 batch, 55 hang, 56 scene, 57 drift (used section 34 instead), 58 small, 59 beat, 60
groups, 61 kin, 62 plant.

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

1. **`s23` into `main`**, when every strand is merged and the merged tree has passed the suites, the goldens and the
   fourteen-case rerun. Not asked yet: nothing but drift is merged.
2. **plant, forks F1-F8** (`plant/notes.md`): what is planted, how it moves, what stands for the clip's own
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
7. **batch**: a row of the corpus table is not an object (one bird in seven pieces on PR088; a flock as one row on
   PR135); a second pass that splits a group into its members; the 40-frame rule, which leaves out PR113's transit
   and PR43's streak; every stage for every object as the default.
8. **The record of the controls**: remade once, after N3's revision and the small strand's cadence rule are both in.
9. **How hard agents may load arthur by day** (asked 16:15; the queue was resumed without an answer, so "as before").

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
  Cannon's `test` partition took minutes.
