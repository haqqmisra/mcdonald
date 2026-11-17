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

## Still to do after the agents report

- Merge `dp-cams`, `dp-fliers`, `dp-winds` into `drift-paper`; wire `--plant` to the fixed-camera input; CHANGELOG,
  IDEAS.md, a pointer from method section 34 to sections 66-68.
- The Galileo table once more on the merged tree, through the new input, with item 5's envelopes: the table the
  paper quotes. Its driver must not live only in the private repository.
- Every suite with the goldens (arthur; Cannon if its login is open), Mac and Windows runs before a tag.
- Item 3's choice, and every judgement call the agents name, to Jacob as multiple choices.
- 0.5.8's version commit, push and tag are Jacob's word, after the GPU session's work is on `main`.
- The paper itself (re-run of its three videos at 0.5.8, the Galileo section, the planted-flier figure) is the paper
  session's; manuscripts are Jacob's.
