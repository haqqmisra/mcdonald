# Handoff: the misfit gate in `drift` (branch `misfit`, 2026-11-19)

**Jacob, 2026-11-19:** "The method should be as good as it can. mcDonald needs to be the premier tool for UAP video
analysis. Let's implement the misfit gate in drift now ... The work can be done on a branch and tested for wind-drift
before being merged, as other agents are doing other development now."

It began with his question about the drift paper's Fig. 7: is the one cloud called not drifting a false positive, or
a cloud faster than the wind? It is two things matched as one (method section 92 has the reading), and nothing in
0.5.8 refuses a path its rays do not follow (IDEAS.md TB1, his decision 14 of 2026-11-17: after 0.5.8, from a null).

## Where things stand

- **Merged into `main` on 2026-11-19** at Jacob's word ("Great! The false positive is gone. Yes, merge into main and
  update the paper"), merge commit 168b831, and versioned **0.5.9** in the commit after it. The rate is as built (19).
  **Released as 0.5.9 the same evening** (Jacob: "go ahead and release"): Mac run 126 and Windows run 127 green on
  c28fda4, then `main` pushed (450268e), the tag `v0.5.9` on the version commit c28fda4, the GitHub release from the
  CHANGELOG entry, PyPI by the tag's workflow (publish run 39), the site (run 31). Zenodo's version DOI is
  10.5281/zenodo.24381952 (CITATION.cff).
  `dev-0.6` is not touched: it will meet `drift.py`, `sightlines.py`, `tests/test_drift.py` and method section 92 when
  it next takes `main`. The branch was made from `main` 749dc89 (0.5.8 and its handoff commits).
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

1. **Merge, and where:** DECIDED 2026-11-19: into `main`, as 0.5.9, and the paper updated.
2. **The rate** (section 92, judgement 1): one single body in a thousand by the null's own law (`MISFIT` 19, as
   built, and as merged on his "The false positive is gone"); one in 200 (13) or one in 100 (11) would refuse more
   made mismatches (two clouds: 57 to 67 % at 12 to 15 where 51 %) and more real aircraft (0.5 % and 1 %). The
   paper's 239 objects come out the same from 9.5 to 29. Open only if he wants another rate.
2a. **The release:** DONE 2026-11-19 on his "go ahead and release" (above).
3. **A name is not a known answer** (found on the way): 1,276 of the 7,423 named aircraft outside the paper's sample
   have no transponder track, and the stage calls 59 of them drifting, at clouds' speeds. The paper's 80 aircraft all
   have a track, so its table stands; the note to the Galileo team could say it.
4. **The route from an aircraft's own track has no misfit gate**: its one azimuth reference is read poorly by the
   rays, and no null is to hand. Open (IDEAS.md TB1's row says so).

## The holds (2026-11-19; Cannon's `test` partition, since arthur's queue was full of the dev session's jobs)

| what | job | result |
|---|---|---|
| the paper's 239 objects, the tag and the branch side by side (the same rays and envelopes) | 62110903, 62116215 | the branch's file is the tag's on 238 of 239, the new fields apart; the cloud of two things: not drifting -> cannot say. The tag on Cannon gives the tag on arthur's every verdict and outcome (239 of 239) |
| the null, 7,425 objects (6,073 known aircraft, 1,276 with a name only, 74 tracked but over 1.5 km off, 2 looked at), the tag and the branch | 62116259, 62116228 | the tag: 0 of 6,073 known aircraft drifting, 6,069 not drifting, 4 cannot say; the branch refuses 12 (0.20 %), 11 of them not drifting at the tag; no outcome moves but by the gate, in any group |
| made mismatches, 600 (branch, `MISFIT` then 15; read at 19 from their misfits) | 62112053 | refused: cloud with aircraft 142 of 150, aircraft with cloud 141, two aircraft 139, two clouds 76 |
| the planted fliers on four sample clouds through the branch | 62116263 | the tag's tables; 0 of 1,152 plants differ |
| every suite on the branch (`mcdonald-test`) | 62112145 (the first build), 62124433 (the final words) | ALL SUITES PASS both times; test_drift 373 (361 + the gate's 12), test_gui 695 + 4 skips (Cannon's usual) |
| every suite with the footage test (`mcdonald-test --golden`) on f42c321 | 62116780 | every suite passes but test_golden, 265 PASS and 1 FAIL: the count of reference case files (17 objects where 18), because Cannon's copy of the data folder had 14 case files and not `pr089.mcdonald`, installed on arthur on 2026-11-18 after the copy was synced. Not the gate's. The file was copied to Cannon afterwards and the run made again on the gate's commit fbfae51 (job 62129715): ALL SUITES PASS, test_golden 266 / 0 / 0, test_drift 373, test_gui 695 + 4 skips |
| eight deliberate breaks of the gate's code against its test | 62116341 | each fails it (1 to 5 checks); the code as it is passes |

The breaks: the gate never shuts; `unfixed` does not read it; the offsets read as zero; the offsets held ten thousand
times tighter; a camera of any number of readings asked; the gate always shuts; an unknown pointing asked all the
same; cameras that share a reference given the gate.

**On the version commit c28fda4 (0.5.9), 2026-11-19, from a `git archive` in `/scratch/mcdonald/release-0.5.9/`:**

| what | job | result |
|---|---|---|
| the paper's 239 objects on arthur (py314), against the tag's run there | array 15327 | 238 files the tag's but for the gate's fields and the printed lines; the cloud of two things: not drifting -> cannot say. Clouds 44 / 75 / 0, aircraft 0 / 0 / 80, pairs 11 / 29 / 0 |
| the planted fliers on all 27 sample clouds that pass T2 | array 15337 | the tag's table on 27 of 27; 0 of 7,776 plants differ; every other field the tag's |
| the drift paper's three videos and the other stages it names | 15328, 15351, 15353 | the three drift files the paper reads: every field the same; the lanterns' planted fliers the same; the other stages' files the same, versions and paths apart |
| every suite with the footage test on arthur (`tools/suites.sbatch golden`, from the snapshot) | 15336 | ALL SUITES PASS: test_golden 266 / 0 / 0, test_drift 373, test_reduction 734, test_gui 797 and 1 skip (a window opened) |
| every suite with the footage test on Cannon (`mcdonald-test --golden`) | 62164646 | ALL SUITES PASS: test_golden 266 / 0 / 0, test_drift 373, test_reduction 734 (it holds the version, the date, CITATION.cff and the CHANGELOG's entry) |
| the null's 7,425 objects through 0.5.9 on Cannon | 62164770 | the 6,073 known aircraft: 0 drifting, 15 cannot say, 6,058 not drifting; 12 refused; the misfit's median 1.91, 99th percentile 10.1, 99.5th 12.4. Verdict, T1, T2, the gate and the misfit itself are the branch's run's on 7,425 of 7,425 |

| Mac and Windows (`platforms.yml`, pushed to `macos-ci` and `windows-ci`) | runs 126, 127 | both green: every suite passes on each (`ci-logs`, `logs/126-c28fda4`, `logs/127-c28fda4`); the Mac's runner was slow that hour (47 min where 35 at 0.5.8), Windows took 64 min of its 120 |
| a fresh install of 0.5.9 from PyPI into an empty venv, on merlin (Python 3.12, no AVX2) | 16865 | `mcdonald --version` 0.5.9, `sightlines.MISFIT` 19.0, `setup --no-desktop` and `drift --help` run |

Not run: merlin. The suites on arthur's card (job 16193) were queued behind the dev session's jobs and had not started
when the release went out; the gate touches no code that the card runs.

## How the null was made (to make it again, or larger)

1. The list: `null/null_list.tsv` and `null_list2.tsv` in the strand's folder (the catalog's named aircraft outside
   the paper's sample; the rule is in `NOTES.md`).
2. Lines of sight on Cannon: the research repository's `galileo/nevada/los.py` by `cannon/los_null.sbatch` (16 CPUs,
   3 min a thousand objects), then `null/rays_from_los.py` (the paper's selection of rays; it gives the table's 239
   rays files row for row).
3. The stage on Cannon: `cannon/null_drift.sbatch SNAP LIST RAYS OUT` (48 CPUs: 1,000 objects in 14 min), then
   `summarise.py`; fetch `OUT.summary.json`.
4. `scripts/threshold.py` (the null's percentiles, its law, the made mismatches) and `scripts/final.py` (the tag
   against the branch).
