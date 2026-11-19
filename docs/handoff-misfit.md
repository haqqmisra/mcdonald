# Handoff: the misfit gate in `drift` (branch `misfit`, 2026-11-19)

**Jacob, 2026-11-19:** "The method should be as good as it can. mcDonald needs to be the premier tool for UAP video
analysis. Let's implement the misfit gate in drift now ... The work can be done on a branch and tested for wind-drift
before being merged, as other agents are doing other development now."

It began with his question about the drift paper's Fig. 7: is the one cloud called not drifting a false positive, or
a cloud faster than the wind? It is two things matched as one (method section 92 has the reading), and nothing in
0.5.8 refuses a path its rays do not follow (IDEAS.md TB1, his decision 14 of 2026-11-17: after 0.5.8, from a null).

## Where things stand

- **Branch `misfit`** (worktree `/hugespace/models/mcdonald-misfit`), from `main` 749dc89 (0.5.8 and its handoff
  commits). **Not merged, not pushed, no version set.** `main` and `dev-0.6` are not touched.
- **Built:** `sightlines.asked` and `sightlines.misfit` (the reading), `sightlines.MISFIT` = 19 and `ASKED_MIN` = 9,
  the refusal in `drift.unfixed`, the words (`sightlines.no_one_path`, a line in `sightlines.said`), the test
  `test_cameras_the_misfit_gate`, method section 92, the CHANGELOG's "Unreleased (branch `misfit`)", IDEAS.md TB1.
- **The strand's folder:** `/scratch/mcdonald/misfit-2026-11-19/` (arthur, not backed up): `NOTES.md` (the log),
  `explore/` (what was tried first), `null/` (the list of the null and how its rays were made), `made/` (the made
  mismatches), `scripts/` (`threshold.py` makes every number of section 92's null again from the summaries),
  `cannon/` (the job scripts and the fetched summaries). On Cannon:
  `GalileoProject/jacob/nevada/misfit_null/` (rays, runs, logs; the lines of sight are in netscratch and temporary).
  The Galileo Project's data are theirs: nothing of it is in the repository, which quotes counts and percentiles.

## What the gate is, in four lines

One straight path is fitted to every camera's lines of sight. The gate fits them again with each camera's pointing
free to be off, held to what is taken as known of it, and reads the largest offset asked in units of what is known.
One body asks about what the cameras have (1.9 times at the median for 6,073 known aircraft); two things matched as
one ask tens of times (29, 41 and 58 for the three known). Over 19 times, T1 and T2 cannot say, and say why.

## What it does to the drift paper's table (the paper cites 0.5.8, which has no gate)

| | 0.5.8 | branch `misfit` |
|---|---|---|
| aircraft (80) | 0 / 0 / 80 | 0 / 0 / 80 |
| clouds (119) | 44 / 74 / 1 | 44 / 75 / 0 |
| mismatched pairs (40) | 11 / 29 / 0 | 11 / 29 / 0 |

One object moves, the cloud of two things, from not drifting to cannot say; the other 238 files are the tag's but
for the new fields. The planted fliers do not move (four clouds made again). If the paper is to quote the gate, it
needs a release that carries it (0.5.9), the table's one cell, and the sentences on that cloud (Results, the
Discussion's "one of 119", Fig. 7's caption and its top bar, Methods): the paper's session's work, on his word.

## For Jacob to decide

1. **Merge, and where:** into `main` as a 0.5.9 for the paper, or into `dev-0.6` for 0.6. It is a report-changer on
   one known object. Nothing else waits on it.
2. **The rate** (section 92, judgement 1): one single body in a thousand by the null's own law (`MISFIT` 19, as
   built); or one in 200 (13) or one in 100 (11), which refuse more made mismatches (two clouds: 65 % at 13 where
   51 %) and more real aircraft (0.5 % and 1 %). The paper's 239 objects come out the same from 9.5 to 29.
3. **A name is not a known answer** (found on the way): 1,276 of the 7,423 named aircraft outside the paper's sample
   have no transponder track, and the stage calls 59 of them drifting, at clouds' speeds. The paper's 80 aircraft all
   have a track, so its table stands; the note to the Galileo team could say it.
4. **The route from an aircraft's own track has no misfit gate**: its one azimuth reference is read poorly by the
   rays, and no null is to hand. Open (IDEAS.md TB1's row says so).

## The holds

[filled at the end of the pass]
