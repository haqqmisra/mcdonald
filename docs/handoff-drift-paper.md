# Handoff: the drift paper's release, 0.5.8 (session "wind-drift finalization", from 2026-11-17)

**Jacob, 2026-11-17:** "My first immediate goal is the wind-drift paper. The GP triangulation calculations can serve as
a control. I want to make sure that mcdonald has all features needed to finalize the wind-drift calculations and paper.
If more development is needed, we should prioritize this." And, on the regroup's four questions: build items 1, 2, 4
and 5 ("Yes"); item 3, measure first, then he decides ("Yes" to the recommendation); 0.5.8 "once the current GPU
session finishes, then that is enough for the release"; the ROADMAP rewrite, "Take it". "Feel free to spawn as many
agents as needed... Use arthur, merlin, and cannon as needed, through /slurm."

`docs/handoff-v04.md` stays the usual handoff (the GPU session writes it). This file is this strand's record.

## What the regroup found (2026-11-17, nothing built)

The paper (the PURSUE analyses' drift manuscript) cites 0.4.3 and has no text on the Galileo Project's triangulated
objects. Their known-answer table in the paper's brief was made with 0.5.3-era code. Run again at the v0.5.7 tag
(`/scratch/mcdonald/regroup-2026-11-17`, its README; job 3684; T3 on the old flicker envelopes):

| group | n | drifting (tentative) | cannot say | not drifting |
|---|---|---|---|---|
| ADS-B aircraft below 3 km | 60 | 0 | 9 | 51 |
| ADS-B aircraft above 8 km | 20 | 0 | 7 | 13 |
| clouds, three sites | 59 | 37 | 21 | 1 |
| clouds, two sites | 60 | 27 | 28 | 5 |
| mismatched low pairs | 40 | 21 | 19 | 0 |

The slowest aircraft whose velocity is fixed needs 53 m/s through the air. 108 of the 119 clouds are from nine days of
late May 2026.

## The five items (ROADMAP.md, "0.5.8")

| | item | who | branch / folder |
|---|---|---|---|
| 1 | fixed cameras as an input of `drift` of their own (no placeholder video, each camera its own pointing reference) | agent "cams" | `dp-cams`, `/hugespace/models/mcdonald-dp-cams`; method section 66 |
| 2 | planted fliers in the package (`--plant`): the slowest flier T2 would have caught on a case's own geometry and winds | agent "fliers" | `dp-fliers`, `/hugespace/models/mcdonald-dp-fliers`; section 67 |
| 3 | T2 from the ranges (the Yemen clip's own route) has no model-error term and no measured rate: **measured, not built; Jacob decides** | agent "winds", Part B | `dp-winds`, `/hugespace/models/mcdonald-dp-winds`; section 68 |
| 4 | `MODEL_WIND_ERR` (3 m/s) held on days it was not set on, and against weather balloons elsewhere | agent "winds", Part A | the same |
| 5 | `flicker` made again at v0.5.7 on every camera's clip, and the Galileo table with it | agent "flicker" | no branch; `/scratch/mcdonald/drift-paper-2026-11-17/flicker` |

The agents' common brief is `/scratch/mcdonald/drift-paper-2026-11-17/BRIEF-common.md`; each keeps `notes.md` in its
folder there, with its drafts for CHANGELOG and IDEAS.md. The coordinator merges the branches into `drift-paper`
(worktree `/hugespace/models/mcdonald-drift-paper`), applies those drafts, runs every suite, and then asks Jacob.

## The GPU session's part is in (2026-11-17)

Its message that day: all its code for 0.5.8 is on local `main`, 725df75 (not pushed, not versioned): the planted
objects through `batch` merged at Jacob's word (5827c89; every suite on Cannon and arthur on the merge candidate), the
CHANGELOG and IDEAS records, and one bullet of ROADMAP.md. Nothing more of its goes onto `main` before the release.
So 0.5.8 waits only on this strand. `drift-paper` carries `main` 725df75.

## Still to do after the agents report (as written that morning; what became of each is in the evening's section below)

- Merge `dp-cams`, `dp-fliers`, `dp-winds` into `drift-paper`; wire `--plant` to the fixed-camera input; CHANGELOG,
  IDEAS.md, a pointer from method section 34 to sections 66-68.
- The Galileo table once more on the merged tree, through the new input, with item 5's envelopes: the table the
  paper quotes. Its driver must not live only in the private repository.
- Every suite with the goldens (arthur; Cannon if its login is open), Mac and Windows runs before a tag.
- Item 3's choice, and every judgement call the agents name, to Jacob as multiple choices.
- 0.5.8's version commit, push and tag are Jacob's word, after the GPU session's work is on `main`.
- The paper itself (re-run of its three videos at 0.5.8, the Galileo section, the planted-flier figure) is the paper
  session's; manuscripts are Jacob's.

## 2026-11-17, evening: the four agents reported, Jacob decided, and the branches were integrated

### Jacob's decisions (asked as multiple choices; the common brief's last section has them word for word)

| | question | his answer | state |
|---|---|---|---|
| 1 | T2 from the ranges (the Yemen clip's route) | build the drafted rule with the model's error in it, AND stop counting this route's T2 as a strong test | built (commit "drift T2 from the ranges ...") |
| 2 | `MODEL_WIND_ERR` | lower to 2 m/s (the recommendation was to keep 3) | built |
| 3 | T2 from the lines of sight | the fail rule before the velocity's gate | built |
| 4 | the pointing error in the paper's Galileo runs | 0.7 deg in azimuth, 0.4 in elevation (`--pointing-err 0.7,0.4`); the package's default stays 0.3 and 0.1 | for the table's agent |
| 5 | what is a camera in those runs | each ring camera, not each site | for the table's agent |
| 6 | the model wind files of section 68 | into the data folder | done by the coordinator (`winds_igra/model/`, 594 files) |
| 7 | the tracker's jitter that `flicker` reads as a beat (5 of 119 clouds) | a jitter control IS built for 0.5.8 | a new strand, branch `dp-jitter`, method section 69; it touches `flicker.py`, not `drift.py` |
| 8 | the held pictures on the Galileo clips (98 of 494 heard only to about 5 Hz) | studied first | a "cadence" strand, scratch only, section 70 if it earns one; section 53's sentence is left as it is until then; T3 saying the band it covered stays unbuilt |
| 9 | the hold-still rule where the winds disagree | a rule against the winds' middle is measured after 0.5.8; nothing changes now | IDEAS.md FL1 |

### What the integration did (agent "integrate", on `drift-paper` itself; nothing merged into main, nothing pushed)

In order, each its own commit, each measured before and after (the agent's notes:
`/scratch/mcdonald/drift-paper-2026-11-17/integrate/notes.md`, with every job id and every moved field):

1. **`dp-fliers` merged** (the planted fliers, section 67), and `--plant` wired to the cameras' input: it ran on
   `--rays` at the first try and is held there by a drawn test that catches the rays handed to every fit. One change
   to `fliers`: the case planted again must also have the case's tolerance (a fit not handed the cameras' pointing
   error passed the old check).
2. **The fail rule before the velocity's gate** (decision 3). T2 fails all 80 Galileo aircraft, where it failed 30
   (each site a camera, the default pointing error), 2 (0.7 and 0.4 deg) and 54 (one shared reference, v0.5.7's
   numbers). Three of 119 clouds fail too, at 19-122 m/s over the ground. No known answer's file moves.
3. **`MODEL_WIND_ERR` 3 -> 2 m/s** (decision 2). T2 passes 55 of the 119 clouds where it passed 68 (default
   pointing), 45 where 53 (0.7 and 0.4), 52 where 64 (v0.5.7's); of the 40 mismatched pairs 11, 11 and 13 where 20,
   20 and 21. The Puerto Rico lanterns' tolerance 10.5 -> 9.5 m/s and "(3)" -> "(2)" in the reading; outcome unmoved.
4. **T2 from the ranges** (decision 1): `drift.test_wind` is section 68's draft A with `WIND_DIFF_ERR` 4.8 m/s, a
   fail 10 m/s beyond, and `drift.strong` counts T2 only from lines of sight. Scored by `tools/wind_model_igra.py` on
   the stations the allowance was not set on: drifters pass 96.8 %, bodies at 5/10/25/50 m/s pass 94.8/82.9/29.8/13.8
   and fail 0/0/22.7/72.2 % (three cells x 24 h; the draft's 96.9; 95/84/30/14; 22/72, and why they differ by up to a
   point is in section 68's "Decided"). The Yemen clip: T2 passes (2.67 m/s against 6.31), the verdict is unchanged
   and rests on T4a ("passed T4a and failed none"); PR051's verdict reason changes its words.
5. **T3 from several cameras** compares another camera's floor unrounded (the flicker agent's finding). T3 of the 239
   Galileo objects, made again from the new envelopes before and after: see the notes.
6. **The records:** CHANGELOG "Unreleased" (one entry for the strand), IDEAS.md rows C1-C5, FL1-FL5, DR7-DR14, N8-N15
   with what became of each, README-technical and tests/README, method sections 34 (the rules as built), 67 (the
   lanterns' table made again at 2 m/s) and 68 ("Decided 2026-11-17").

The four known answers after all of it: the Yemen clip, consistent with wind-borne drift (tentative), as before, by
T4a; the Puerto Rico lanterns, the same, by T2 from lines of sight; the Santa Barbara helicopter, not drifting (its
file the same to the byte through every step); PR051's second leg, cannot say.

### The suites, on the integration's last code commit (ce298f0; the two commits after it change words in docs only)

Every suite with the goldens, each from a snapshot of that commit, `MCDONALD_DATA` exported:

| where | job | result |
|---|---|---|
| arthur, CPU (`tools/suites.sbatch golden`) | 5709 | ALL SUITES PASS: test_golden 266 PASS / 0 FAIL / 0 SKIP, test_gui 797 / 0 / 1 (the Wx backend, as always), test_drift 325 / 0 / 0, test_measurement 704, test_reduction 732, test_cli 140, test_gpu 137, the other 22 suites all PASS with no FAIL and no SKIP |
| arthur, the graphics card (`--gres=gpu:1`) | 5710 | ALL SUITES PASS: the same counts, test_gpu 168 |
| Cannon (`mcdonald-test --golden`, run 20261117-144352-drift-paper-ce298f0) | 61600543 | ALL SUITES PASS: test_golden 266 / 0 / 0, test_drift 325 / 0 / 0, test_gui 695 / 0 / 4 and test_cli 137 (Cannon's usual counts: no installed menu entry, no GTK or Wx there), test_measurement 702, test_reduction 732 |

test_drift takes about four and a half minutes on four CPUs of arthur (it took five before, with 293 checks of
today's 325): its stage runs take 60 or 200 resamples where no check turns on the count. Under two minutes would mean
dropping one of the command-line runs that keep the stage's 2,000 resamples (the lanterns' planted fliers alone are
a minute), which was not done.

Deliberate breaks: 21, of the plants on cameras, the three rules, the soundings tool and T3's floor; each fails the
check meant for it (one did not at first, and a check was added for it).

### Still to do

- **The Galileo table for the paper** (another agent, scratch folder `table/`): the 239 objects through `--rays`
  with `--pointing-err 0.7,0.4`, each ring camera a camera of its own, the envelopes `flicker` made at v0.5.7 (or
  with the jitter control once `dp-jitter` is in), on the rules as built. Its driver must not live only in the
  private repository. Expected from the recomputation above (each site a camera, T3 as recorded then): aircraft T2
  fails 80 of 80; clouds T2 passes about 45 of 119.
- **The 40 clouds with `--plant`** were measured before these rules and through one shared reference: section 67
  says so above its table. To be made again through `--rays` (10-12 min a cloud on 6 CPUs).
- **`dp-jitter`** (section 69) and the **cadence** study (section 70, if any) are other strands; `flicker.py` is
  theirs this week. When `dp-jitter` merges, the IDEAS row N8 and the CHANGELOG want its line.
- **Section 53**: its sentence on held pictures waits for the cadence study (IDEAS N10). Its counts of T3 are the
  0.5.2 envelopes'; with `flicker` 0.5.7 T3 fails on 5 of 119 clouds and no aircraft (the flicker agent's README).
- **Open, for Jacob** (IDEAS.md): FL1 (hold-still against the winds' middle, after 0.5.8), DR10 (a sourced airspeed
  band for the Yemen aircraft), DR12 (`tools/shear_igra.py`'s sort and its dropped levels: the shear law's constants
  may move), DR13 (`WIND_DIFF_ERR` by separation), N12, N13, N14 (T3's quoted window; cameras that overlap in part; a
  one-camera run's 2,000 resamples on a refused path), FL2 (plants on the range route).
- Every suite on Mac and Windows before a tag; 0.5.8's version commit, push and tag are Jacob's word.
- The paper itself (its three videos again at 0.5.8, the Galileo section, the planted-flier figure) is the paper
  session's; manuscripts are Jacob's. What moves for it: the Yemen clip's T2 is no longer a strong test and its
  verdict rests on the shed pieces; the lanterns' tolerance is 9.5 m/s; the planted-flier figure's numbers are in
  section 67.
