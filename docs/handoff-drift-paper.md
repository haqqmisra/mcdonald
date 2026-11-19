# Handoff: the drift paper's release, mcDonald 0.5.8 (session "wind-drift finalization", 2026-11-17)

**Jacob, 2026-11-17:** "My first immediate goal is the wind-drift paper. The GP triangulation calculations can serve as
a control. I want to make sure that mcdonald has all features needed to finalize the wind-drift calculations and paper.
If more development is needed, we should prioritize this."

`docs/handoff-v04.md` stays the usual handoff (the GPU session writes it). This file is this strand's record, made one
document on 2026-11-17 by the last integration pass. Its history is below the line at the end, shortened.

## Where things stand

- **Branch `drift-paper`** (worktree `/hugespace/models/mcdonald-drift-paper`) carries `main` 1061757 with everything
  0.5.8 holds for the paper. **Not merged into `main`, not pushed, no version set.** `main` is at 1061757, clean.
- **Every suite passes on the branch's last commit, with the overlay of the data folder** (see "The final holds").
- **One thing in the data folder waits for the merge:** the labelled set's table of record (see "What is left").
- The agents' folders are under `/scratch/mcdonald/drift-paper-2026-11-17/` (arthur's disk, not backed up); the common
  brief with Jacob's decisions word for word is `BRIEF-common.md` there.

## What 0.5.8 holds (the drift paper's part; CHANGELOG "Unreleased" says it for a reader)

| what | where | method |
|---|---|---|
| Cameras on the ground as an input of `drift` of their own: `--rays`, each camera its own time, scatter and pointing error (`--pointing-err`), no video needed | `sightlines.py`, `drift.py` | §66 |
| Planted fliers: `--plant`, the slowest flier T2 would have caught on a case's own geometry and winds, from an aircraft's lines of sight or from cameras' | `fliers.py` | §67 |
| T2 from the lines of sight: the fail rule before the velocity's gate; a model's own wind error 2 m/s (was 3) | `drift.test_wind_track`, `MODEL_WIND_ERR` | §34, §68 |
| T2 from the ranges (the Yemen clip's route): a rule with the model's error in it (`WIND_DIFF_ERR` 4.8 m/s), a fail it lacked, and no longer a strong test | `drift.test_wind`, `drift.strong` | §34, §68 |
| A model's wind against weather balloons, and the rule's scores on stations it was not set on | `tools/wind_model_igra.py`, two golden tables | §68 |
| `flicker`'s control against a beat that is the track's own jitter (`JITTER_KEEP` 0.5); the labelled set's record and the report's weights made again | `flicker.jitter_reading`, `controls_beat.csv` | §69; §43, §44, §47 corrected |
| The band a beat was listened for in, said in words by `flicker`, T3 and the report | `flicker.listened_in`, `drift.beat_band`, `report.Case.beat_band` | §34, §35, §53 |
| T3 says where a beat was seen and given to the track; the several-camera rule does not count such a record | `drift.given_to_track`, `given_said`, `shown_floor` | §34 |
| T3 from several cameras compares another camera's floor as measured, not rounded | `drift.beat_floor` | §34 |

The GPU session's part of 0.5.8 was on `main` before this strand branched (`layers --dense`, the plants through
`batch`, Find sooner): its records are in the CHANGELOG below this block and in `docs/handoff-v04.md`.

## Jacob's fourteen decisions (2026-11-17; each asked as a multiple choice)

| | question | his answer | state |
|---|---|---|---|
| 1 | T2 from the ranges (the Yemen clip's route) | build the drafted rule with the model's error in it, AND stop counting this route's T2 as a strong test | built |
| 2 | `MODEL_WIND_ERR` | 2 m/s (the recommendation was to keep 3) | built |
| 3 | T2 from the lines of sight | the fail rule before the velocity's gate | built |
| 4 | the pointing error in the paper's Galileo runs | 0.7 deg in azimuth, 0.4 in elevation (`--pointing-err 0.7,0.4`); the package's default stays 0.3 and 0.1 | the table is made so |
| 5 | what is a camera in those runs | each ring camera, not each site | the table is made so |
| 6 | the model wind files of section 68 | into the data folder | done (`winds_igra/model/`, 594 files) |
| 7 | the tracker's jitter that `flicker` read as a beat (5 of 119 clouds failed T3) | a jitter control is built for 0.5.8, measured first on the labelled birds | built (§69) |
| 8 | the held pictures on the Galileo clips (98 of 494 heard only to about 5 Hz) | study the cadence first | studied (`cadence/`) |
| 9 | the hold-still rule where the winds disagree | a rule against the winds' middle, measured after 0.5.8; nothing changes now | open (IDEAS FL1) |
| 10 | the band, after the cadence study | for 0.5.8, say the band in words; no number moves | built |
| 11 | `flicker.pictures` asking the object's own frames before it lowers the band | after 0.5.8, measured first | open (IDEAS N16) |
| 12 | the jitter control | as built: the record without IR_HELICOPTER_043's false bird, the weights 37 -> 74 and 33 -> 66, `JITTER_KEEP` 0.5 | built; the table swap waits for the merge |
| 13 | T3 and a beat given to the track | in 0.5.8: T3 says where one was seen, and the several-camera rule skips such a record | built |
| 14 | a misfit gate in `drift` ("no single straight path fits these lines of sight") | after 0.5.8, from a null | open (IDEAS TB1) |

## What each agent measured, and the folder that holds it

Each folder has `notes.md` (the log, job ids, judgement calls) and what is named here.

| agent | what | folder under `/scratch/mcdonald/drift-paper-2026-11-17/` |
|---|---|---|
| cams | `--rays` built and held to the 239 Galileo runs: the same fit to the last bit by `--reference shared`; each camera's own pointing; the stated errors against transponder speeds (two errors hold the truth on 50 % with one shared reference, 66 % at the default, 78 % at 0.7 and 0.4 deg) | `cams/` (`drafts.md`, `runs/`) |
| fliers | `--plant` built; the lanterns' table; 40 Galileo clouds by the workaround; the hold-still rule asked wind by wind (decision 9) | `fliers/` |
| winds | a model's wind against 8,129 balloon flights at 18 stations; `MODEL_WIND_ERR` out of sample; T2 from the ranges scored (the old rule passed a drifter 27 times in 100) and a rule drafted | `winds/` |
| flicker | `flicker` v0.5.7 on all 513 Galileo clips; found the seven cloud beats to be the detector's box jittering; the floor's rounding | `flicker/` (`README.md`, `mcd/`) |
| integrate | merged cams, winds, fliers; built decisions 1-3 and the floor; every moved field of the known answers; the first final suites | `integrate/` (`known/`, `out/`) |
| jitter | the jitter control: three designs measured on 864 measurements before one was built; the labelled set judged again; the 513 clips again (`mcd_jit/`); the fourteen cases before and after (`gate/`) | `jitter/` (`drafts/`, `staged/`, `gate/md_diff.txt`) |
| cadence | the 12 pictures a second is the encoder's group of pictures (every file I P P P P); a fast object's picture is new on every frame, a slow cloud's is not; planted beats of 6-23 Hz found 0 times of 576 | `cadence/README.md` |
| band | the band said in words; `words-for-jacob.md` of its own; the fourteen cases before and after (`gate/cmp_band.md`) | `band/` |
| table | **the tables the paper quotes** (`README.md`, 851 lines: the 239 objects as decided, the rates with errors by observing session, every cloud called not drifting looked at, the clean-cloud rule, the planted fliers through `--rays`); its scripts make every table again | `table/` (`scripts/`, `runs/cam_0.7_0.4__jit/`, `plants/`) |
| finish | decision 13 built and held; the records brought together; the final holds; `words-for-jacob.md` | `finish/` and `words-for-jacob.md` beside the folders |

The Galileo Project's data are theirs and unpublished. Nothing of theirs is in the repository or the data folder: the
rays, the per-object files and every reading that names an object stay in scratch. The repository quotes counts and
medians only.

## The four known answers of `drift`, as 0.5.8 gives them

| known answer | verdict | what moved since 0.5.7 |
|---|---|---|
| the Yemen clip | consistent with wind-borne drift (tentative), by T4a | T2's reading is new and seven fields are added (the shortfall 2.67 m/s against 6.31 allowed); T2 is no longer a strong test, so the reason reads "passed T4a and failed none" where it read "passed T2, T4a" |
| AARO's Puerto Rico lanterns | consistent with wind-borne drift (tentative), by T2 from lines of sight | T2's tolerance 10.5 -> 9.5 m/s; "a model's own error (2)" where "(3)" |
| the Santa Barbara helicopter | not drifting, by T3 | nothing: the file is the same to the byte through every step |
| PR051's second leg | cannot say | the verdict's reason names "T2 from lines of sight"; T3's reading names its band, 1.5 to 12.0 Hz, and why it stops there |

Decision 13 moved none of the four (no golden envelope has a beat given to the track).

## The Galileo table (the paper's control populations; aggregates only)

All 239 objects through `drift --rays`, each ring camera its own, `--pointing-err 0.7,0.4`, T3 on the envelopes made
with the jitter control. Verdicts as drifting (tentative) / cannot say / not drifting: **aircraft 0 / 0 / 80; clouds
44 / 74 / 1; mismatched pairs 11 / 29 / 0.** T2 fails 80 of 80 aircraft. T3 fails no cloud and no aircraft. The one
cloud called not drifting is two things matched as one. The planted fliers on the 27 of 40 sample clouds that pass T2:
a drifter passes 98 in 100; fliers at 15 / 20 / 25 / 30 m/s fail 42 / 82 / 96 / 99 in 100; at 5 and 10 m/s 23 and 2 in
100 pass as drifters. Method sections 66 and 67 have the tables; `table/README.md` has everything behind them.
Made again by the last pass before and after decision 13 was built: the same table, 0 of 239 objects with a field that
differs other than T3's reading and its new fields, and eight readings that now say a beat was set aside.

## The final holds (the last pass, on the branch's last commit, from a snapshot, with the overlay)

All on snapshots of **cae6ac6**, the last commit that changes any code or any word a suite reads (the commit after it
fills this section and nothing else), with `MCDONALD_DATA` set to the overlay that holds the new table of record. Logs
and scripts: `/scratch/mcdonald/drift-paper-2026-11-17/finish/` (`notes.md` has every job).

| what | job | result |
|---|---|---|
| every suite with the goldens, arthur's CPUs (`tools/suites.sbatch golden`) | 6443 | ALL SUITES PASS: 29 suites, 4,328 PASS, 0 FAIL, 1 SKIP. test_golden 266 / 0 / 0, test_gui 797 / 0 / 1 (the Wx backend: no wx module, as always), test_drift 361, test_controls 118, test_reduction 734, test_measurement 711, test_beat 72, test_cli 140, test_gpu 137; the other 20 suites pass with no FAIL and no SKIP |
| the same with the graphics card (`--gres=gpu:1`; RTX 5070 Ti, CuPy 14.2.0, CUDA 13.2) | 6444 | ALL SUITES PASS: the same counts, test_gpu 168 (4,359 PASS, 0 FAIL, 1 SKIP) |
| the exercise pages, a page a job (`tests/test_golden.py --exercises NN`) | 6446 | 01: 4 PASS; 02: 5; 03: 5; 04: 16; no FAIL, no SKIP |
| the fourteen reference case files against `main` 1061757 (31 objects) | 6445, against 5615 | 0 objects whose conclusion, bottom line, answers, grade or reasons but for their numbers moved; 0 differences of a kind not listed in `words-for-jacob.md`; every measured number the same. Fields: the jitter reading added to 28 beats' records, a "no beat" finding grown by its band on 7 objects. Reports: 3 the same to the letter, 28 changed in the weights' sentences (21), the screening sentence (21) and the band's rows (7 objects) |
| `drift`'s four known answers (five files) against the branch before the last pass | 6447, against 6431 | byte-identical |
| the 239 Galileo objects before and after decision 13 was built | 6436, 6437 | no field differs but T3's reading and its new fields; no outcome or verdict moves; 8 readings say a beat was set aside |
| fifteen deliberate breaks of decision 13's code | 6448 | each fails the check meant for it |

Not run: Cannon (its copy of the data folder has the old table), Mac and Windows (they wait for the version commit).
Nothing an earlier agent reported as passing failed at the merge. An earlier run of every suite on the last code
commit but one (d134502, job 6439) gave the same counts.

One thing found on the way and left as it was (IDEAS.md N26): the report's sentence for a rotor's look quotes "6 of 8
helicopters", a count of 2026-10-25 that the record had already left behind.

## Done on 2026-11-17, 21:30, at Jacob's word ("Yes, merge and swap now"; "Version commit + Mac/Windows runs")

- `main` fast-forwarded to this branch (9627524), then the version commit 0.5.8 on it (dated 2026-11-17; if the push
  is on a later day, the date moves in `__init__.py`, CITATION.cff and the CHANGELOG heading, and test_reduction runs
  again).
- The data folder's `controls/svanstrom_tracks.csv` swapped, its README paragraph and both checksum lines (the table
  before it: `/scratch/mcdonald/drift-paper-2026-11-17/coord/svanstrom_tracks.before-2026-11-18.csv`). **A checkout of
  0.5.7 or older now fails 10 checks of test_controls against the data folder**, by design. Cannon's copy of the data
  folder still has the old table and lacks `winds_igra/model/`: sync both before `mcdonald-test` runs there.
- Steps 2, 3, 4 and 7 below are done; 5 is running; 1, 6 and 8 are Jacob's or wait for the release.

## Released as 0.5.8 on 2026-11-17 (Jacob: "go ahead and push and tag 0.5.8")

- **The holds on the version commit 46dd395, all green before the push:** every suite with the goldens on arthur
  against the real data folder with the swapped table, on the CPUs (job 6469: golden 266 / 0 / 0) and on the card (job
  6470: 29 suites, 1 SKIP, the Wx backend; drift 361, controls 118, gui 797); Mac run 124 and Windows run 125. The
  Windows run took about 95 minutes of its job's 120 (test_measurement 1,783 s, test_drift 437 s): trim test_drift's
  slowest command-line runs or raise that limit before the next release of this size.
- **Out:** `main` and tag `v0.5.8` pushed, the GitHub release made from the CHANGELOG entry, the site published, PyPI
  by the tag's workflow. Zenodo's version DOI is 10.5281/zenodo.24329905 (CITATION.cff).
- **Housekeeping done:** the worktrees and branches `dp-cams`, `dp-fliers`, `dp-winds`, `dp-jitter`, `dp-band` and
  `drift-paper` removed (all merged). The scratch folder `/scratch/mcdonald/drift-paper-2026-11-17` stays: it holds the
  paper's tables (`table/README.md`), every agent's record and `words-for-jacob.md`.
- **Still open:** Cannon's copy of the data folder (the labelled set's new table, `winds_igra/model/`) before
  `mcdonald-test` runs there again; the fresh-install check of 0.5.8 from PyPI; and "What comes after 0.5.8", below.
- The sections below this one were written before the release and are kept as the record. Some of their headings and
  the agents' brief say "2026-11-18": all of it was 2026-11-17.

## What is left for the release (all on Jacob's word)

1. **Read `/scratch/mcdonald/drift-paper-2026-11-17/words-for-jacob.md`:** every sentence a person reads differently
   in 0.5.8, old beside new, by where it appears.
2. **Merge into `main`:** `main` has not moved since this branch left it (1061757), so it is a fast-forward:
   `git -C /hugespace/models/mcdonald merge --ff-only drift-paper`. Ask Jacob before merging. No Slurm job may be
   importing the checkout at that moment.
3. **Swap the table in the data folder, at the same moment as the merge.** `main` and any branch without the jitter
   control need the old `controls/svanstrom_tracks.csv`; this branch needs the new one. Until the swap, `test_controls`
   fails 10 checks and `test_reduction` 1 on this branch against the plain data folder, by design.
   - new table: `/scratch/mcdonald/drift-paper-2026-11-17/jitter/staged/d2/svanstrom_tracks.csv` (432 rows; 2 lines
     differ: IR_DRONE_011 and IR_HELICOPTER_043) -> `/models/data/mcdonald/controls/svanstrom_tracks.csv`;
   - its line in `/models/data/mcdonald/SHA256SUMS`; a paragraph in `controls/README.md` ("Judged again on 2026-11-17
     with the reading of the track's own jitter, method section 69"); `staged/d2/rates.json` and `summarise.txt` are
     its rates;
   - Cannon's copy of the data folder has the old table too: copy the new one there before `mcdonald-test` runs on
     Cannon again.
   - Until then: `export MCDONALD_DATA=/scratch/mcdonald/drift-paper-2026-11-17/jitter/staged/data` (the data folder
     as links, with the new table).
4. **The version commit** (the date is the push day): `src/mcdonald/__init__.py` 0.5.7 -> 0.5.8; CHANGELOG's
   "Unreleased" heading -> "0.5.8 (date)"; `CITATION.cff`; the version strings in `README.md` and
   `README-technical.md`. `test_reduction` holds these to one another and says which is off.
5. **Every suite once more on the version commit** (`tools/suites.sbatch golden` on arthur, CPU and card; Cannon after
   its table is swapped), **then Mac and Windows** (push to `macos-ci` and `windows-ci`, watch by sha, read the logs
   from `ci-logs`).
6. **Push and tag `v0.5.8`:** Jacob runs these himself (the classifier refuses a tag and a public push). PyPI and the
   website publish on the tag; the Zenodo DOI follows.
7. **ROADMAP.md's status line** for 0.5.8, and a line in `docs/handoff-v04.md`'s top pointing here.
8. Housekeeping after the release: the worktrees `mcdonald-dp-cams`, `-dp-fliers`, `-dp-winds`, `-dp-jitter`,
   `-dp-band` and their branches are merged and can go; the scratch folder holds the paper's tables and stays.

## The table from the release itself (2026-11-18, a check; nothing built)

The paper's table was made at a50bdc3, before the version commit. On 2026-11-18 the same 239 rays files and envelopes
went through the release (`/scratch/mcdonald/drift-final-2026-11-18/README.md`; scratch only, the rays are the Galileo
Project's):

- **The tag's code (46dd395) under the table's own libraries** (NumPy 2.4.1, SciPy 1.17.1; job 10530): every number
  the same on 239 of 239 objects; only T3's words differ (the band, a beat set aside), as said below.
- **The PyPI install of 0.5.8** (a fresh venv, NumPy 2.5.5, SciPy 1.18.1; job 10528): every count the same (aircraft
  0 / 0 / 80, clouds 44 / 74 / 1, mismatched pairs 11 / 29 / 0), no test's outcome moved. The fitted numbers differ in
  late digits: at most 0.006 m/s in a speed, 0.06 m/s in T2's tolerance and in two errors of the velocity, 0.01 m/s in
  an airspeed needed. So the libraries, not the code, move the late digits (the table agent saw the same between
  arthur and merlin). One cloud sits 0.02 m/s from T2's tolerance and one 0.09; a count could move by one on another
  install, though none did here.
- **The paper's three videos at the tag** (the research repository's `paper_check`, job 10529, against what the paper
  reads, made under 0.4.3): the three verdicts stand. What moved is what "What the paper's session needs" lists, and
  two things more: the lanterns' climb error reads 0.05 m/s where 0.04 (the azimuth reference's error is carried), and
  the case file of the Yemen remains answers "Does anything move along with it?" with Yes (a bright feature 2.1 object
  widths away, beside it) where it answered No. The speed band, zoom, `layers --k 1` and `slew` are unchanged.

- **At the package's default pointing error** (0.3 and 0.1 deg; job 10531), to size what a better pointing model could
  gain: clouds 54 / 61 / 4 where 44 / 74 / 1, aircraft and mismatched pairs the same. Of the 31 clouds whose velocity
  the tighter error fixes, 10 pass T2, 18 are beyond the tolerance but short of a flier and 3 fail. So "drifting" said
  of a cloud tops out near 45 in 100: the rest is the clouds, which lag the wind on some days (section 68's Las Vegas
  soundings), not the pointing.

**Jacob's four decisions, 2026-11-18 (each asked as a multiple choice): the result is final at 0.5.8.**

| | question | his answer |
|---|---|---|
| 15 | the one cloud called not drifting, two things matched as one | left in the table and explained; no misfit gate before the paper (TB1 stays for after) |
| 16 | which planted-flier table the paper quotes | the 27 clouds that pass T2 as decided |
| 17 | the Yemen clip's T2, no longer a strong test | left as it is, with section 68's measured rates; no sourced airspeed band, no plants on that route before the paper (DR10, FL2 stay open) |
| 18 | the Galileo cameras' pointing error | 0.7 and 0.4 deg only; no row at the default, no per-object error before the paper (C3 stays for 0.6) |

**Cannon's copy of the data folder is synced (2026-11-18).** 1,021 files, 355 MB: `winds_igra/model/` (594 files),
the labelled set's new table (the same sum as here), the visible tracks, the case files. All 7,711 lines of
`SHA256SUMS` were checked there in a job on `test`; one fails, `svanstrom2021/README.md`, and it fails here too: the
file was edited on 2026-11-18 for the visible tracks and its line was not made again (Cannon's copy is the same as
this one to the byte), and `svanstrom2021/tracks_visible/` (406 files) has no lines yet. So `mcdonald-test` may run on
Cannon again; the two "still open" notes on Cannon's copy above are done.

## The paper's outputs made again from the release, and its Galileo section written (2026-11-18)

Jacob, 2026-11-18: "write the Galileo section and re-make the outputs under 0.5.8 for the wind-drift paper". Nothing
in this repository's code moved. The record is in the research repository: the paper's `README.md` ("mcDonald 0.5.8
and the Galileo section": every job, what moved, what is open), `analysis/cases/hellfire_yemen/paper_check/README.md`
and `galileo/nevada/paper/` (the Galileo numbers the paper quotes, read from the runs at the tag by `collect.py`).

- **The paper cites 0.5.8.** Every output it reads was made again from a `git archive` of the tag (flicker, drift,
  the band and the other stages on the three videos; the figures), and the text follows them. The three verdicts
  stand. The Yemen verdict now rests on Test 4a alone, as "What the paper's session needs" foretold, and the paper
  says that without the strike's evidence it would be "cannot say".
- **The lanterns' planted fliers in the paper are now `drift --plant`'s** (job 12199: the table of section 67 to the
  digit: a drifter 32 of 32, every flier failing from 25 m/s, one of 32 at 20 m/s, none passing).
- **The Galileo section** quotes the table above (aircraft 0 / 0 / 80, clouds 44 / 74 / 1, mismatched pairs
  11 / 29 / 0) from the run at the tag (job 10530), with a figure of its own, and says in Methods that these objects
  also shaped the rules. The planted fliers on the 27 clouds were made again at the tag (array 12201,
  `/scratch/mcdonald/drift-final-2026-11-18/plants_tag/`; 687 s a cloud on 6 CPUs): on 27 of 27 the table, every
  plant's outcome and its airspeeds needed and tolerance are the same as the plants of 2026-11-17 at a50bdc3, and
  every other field of each file is that of its case at the tag (`plant_cmp.txt` there).
- **The Galileo envelopes held to the release** (`/scratch/mcdonald/drift-final-2026-11-18/env_cmp.txt`): the 513
  envelopes behind the table were made the day before the release, before the band's words were merged into
  `flicker`. A sample of 24 clips (the 8 whose beat went to the track, 8 other cloud clips, 8 aircraft clips) made
  again by the tag's `flicker` (array 12211) gives every number and every exit code the same; only `finding` and
  `said` differ, by the band's clause.
- **Found on the way, for this repository:** `mcdonald stabilize` on the Yemen clip puts 329 of 691 frames on the
  display's drawing where 0.4.0 put 21 (and 11 where 18 in the anchored call), still with no power; nothing was
  looked into. And the queue: low-priority jobs behind a deep queue start only by backfill, which wants a `--mem` and
  a `--time` near what the job uses (the paper's small jobs were planned a day out at 3-4 GB and 40 min, and ran at
  once at 600 MB and 5 min).

## The misfit gate, built on a branch (2026-11-19)

Jacob, 2026-11-19, on the one cloud of 119 called not drifting (two things matched as one): "The method should be as
good as it can ... Let's implement the misfit gate in drift now", on a branch, tested for wind-drift before it is
merged. It is on **branch `misfit`** (worktree `/hugespace/models/mcdonald-misfit`, from this branch at 749dc89), and
its record is that branch's `docs/handoff-misfit.md` and method section 92. In short: the stage asks how far each
camera's pointing would have to be off for one straight path to pass through every line of sight, and refuses T1 and
T2 over 19 times what is taken as known, a threshold from a null of 6,073 transponder-tracked aircraft outside the
paper's sample. On the paper's 239 objects one moves: clouds read 44 / 75 / 0 where 44 / 74 / 1. The release's tag
on that null calls 0 of 6,073 aircraft drifting. **Not merged**: whether it goes to `main` as a 0.5.9 for the paper
or to `dev-0.6`, and at which rate, are his to say. TB1 in "What comes after 0.5.8" below is this.

## What the paper's session needs

The manuscript is Jacob's: the tool's sessions report what the tool shows and give no revision advice.

- **The tables:** `table/README.md` in the scratch folder (section 1 the 239 objects as decided with rates and their
  errors by observing session; section 2 every cloud called not drifting, and the tables over clean clouds only;
  section 3 the planted fliers through `--rays`; section 5 its judgement calls; section 6 three questions it left
  for Jacob: how the paper counts the one mismatched "cloud", which planted-flier table is quoted, and T3's words,
  which decision 13 has answered). The scripts in `table/scripts/` make every table again from a snapshot of the code
  and a folder of envelopes; the exact command for one object is in its section 0.
- **The commit to cite:** the release's tag. The table was made at a50bdc3 and is the same to the byte after the
  jitter control's merge; it was made again before and after decision 13 with the same outcomes (`finish/gal/`). A run
  at the tag will differ from `table/runs/cam_0.7_0.4__jit` only in T3's words (the band, a beat set aside).
- **The paper's three videos, what moved against the version it cites (0.4.3):**
  - *the Yemen clip:* T2 passes by the new rule (2.7 m/s short of the nearest hour and place, 6.3 allowed) and is no
    longer a strong test; the verdict is unchanged and rests on the shed pieces (T4a). A body flying 5 to 10 m/s
    would pass that T2 as well (95 and 83 times in 100 on balloons), which the reading now says.
  - *the Puerto Rico lanterns:* the tolerance is 9.5 m/s (7.2 under 0.4.3, 10.5 under 0.5.7); they need 1.4 to 3.6 m/s
    and pass. The planted-flier figure was made under 0.4.3; its numbers under 0.5.8 are in method section 67 (every
    plant fails from 25 m/s; from 5 to 20 m/s the test cannot say, but for one body of 32 at 20 m/s).
  - *the Santa Barbara helicopter:* nothing moved.
- **The control populations:** the Galileo table above; its rates with errors are in method section 66 ("As decided").
- **What the tests cannot say, measured:** T2 cannot tell a flier under about 15 m/s from a drifter (section 67); T3's
  band stops near 5 Hz on one Galileo clip in five, and 14 of 198 objects were heard no higher by any camera (section
  34); a model's wind is 2.1 m/s from a balloon's at the median (section 68).

## What comes after 0.5.8 (IDEAS.md has each row)

Set by Jacob on 2026-11-17, each to be measured first:
- a hold-still rule against the winds' middle (FL1);
- `flicker.pictures` asking the object's own frames before it lowers the band (N16);
- the jitter reading window by window (N21), and a weaker beat of the object's own under one given to the track (N22);
- a misfit gate in `drift`, from a null (TB1).

Open, waiting for him: which camera a several-camera T3 reading leads with (the first that passes, as now, or the one
that listened furthest); N20 (a camera counts as able to see a beat above its own band); whether a camera that set a
beat aside may take another camera's beat back at all (TB6's judgement); whether the checklist's "No" should stand
where the band stops under most of a wingbeat's range; DR10 (a sourced airspeed band for the Yemen aircraft), DR12
(`tools/shear_igra.py`'s sort and dropped levels), DR13 (`WIND_DIFF_ERR` by separation), N12-N14, N26 (the report's
count of helicopters with a rotor's look, stale since before this release), FL2 (plants on the range route), TB2-TB4 (a camera with one to four readings; cameras of one ring sharing an error; T1's words between
its two thresholds).

---

## History (shortened; the agents' notes have every job)

- **Morning, the regroup** (`/scratch/mcdonald/regroup-2026-11-17`, nothing built). The paper cites 0.4.3 and had no
  text on the Galileo objects; its known-answer table was of 0.5.3-era code. The 239 objects run again at the v0.5.7
  tag by the workaround (one shared azimuth reference): aircraft 0 / 16 / 64, clouds 64 / 49 / 6, mismatched pairs 21
  / 19 / 0. Five items went into ROADMAP's "0.5.8", and Jacob said yes to building 1, 2, 4 and 5 and to measuring
  item 3 first.
- **Four agents** (cams, fliers, winds, flicker) built and measured; Jacob answered decisions 1-6.
- **The integration** merged `dp-cams`, `dp-winds` and `dp-fliers`, wired `--plant` to `--rays`, and built decisions
  1-3 one commit each, each measured before and after. T2 failed all 80 aircraft where it had failed 30 (each site a
  camera, the default pointing error), 2 (0.7 and 0.4 deg) and 54 (v0.5.7). With 2 m/s T2 passed 55 of 119 clouds
  where 68, and 45 where 53 at 0.7 and 0.4 deg. Suites on ce298f0: arthur CPU job 5709, the card job 5710, Cannon job
  61600543, all passing (test_drift 325).
- **Decisions 7-9**, then three more strands. *jitter* (branch `dp-jitter`, merged ef56bd3): suites on e64aa6e, job
  5813, 4,158 checks passing. *cadence* (scratch only): decisions 10 and 11 followed. *band* (branch `dp-band`, merged
  0a91028): suites on cb3bac6, jobs 6416 and 6425 (test_drift 342).
- **The table** (scratch only): jobs 6392 and 6393, and the plants' arrays 6077, 6095, 6061, 6366.
- **Decisions 12-14, and the last pass** (this document's "final holds").
- Deliberate breaks through the day, each failing the check meant for it: 21 (the integration), 3 (the jitter
  control), 21 (the band), 15 (decision 13).
