# Handoff: a light that flashes in a train (`flicker` item 13) -- merged, and what is left

**Status (2026-10-21).** Built on branch `blinks` 2026-10-20 and merged to main 2026-10-21 at Jacob's word ("merge to
main, remove the branch and worktree, but do not release yet"). The merge commit is db942e8, made on top of `zoom`'s merge and its ROADMAP follow-up (af49ab3).
All 15 suites and golden passed on the merged tree (Slurm job 8699). The branch and its worktree
(`/models/mcdonald-blinks`) are gone. **Not pushed and not released:** a push is a release here, and the release is
Jacob's word. This page is for the session that takes up the open items (section "Open, in order").

## The question, and the answer so far

A UAPSAC council member asked (2026-10-20, relayed by Jacob): helicopters have blinking lights with well-known
properties; could a rotor's beat and a light's flicker show as two peaks in one amplitude spectrum? The PURSUE analysis
answered first, in the uap repository (`/hugespace/local/research/uap`):

- `analysis/methods/helicopter_lights.md` is the write-up.
- `analysis/sweeps/svanstrom/heli_lights.py` and `analysis/tools/heli_lights_figure.py` are the measurement and the
  figure, in the bird paper's Supplementary layout.
- `analysis/sweeps/svanstrom/heli_lights_fig.png` is the figure: one helicopter (V_HELICOPTER_054), its white light, its
  red light and its rotor.

The answer:

- **In visible video, yes.** The light is not a peak but a comb, at the flash rate and every multiple of it. An
  anti-collision light flashes 40-100 times a minute (14 CFR 25/27/29.1401(c)), to 180 where two beams overlap. The
  rotor is a separate line, folded by the frame rate.
- **The two live in different pixels.** On a resolved helicopter the light is in the brightest or reddest few pixels,
  the rotor in the blade pixels. For an unresolved point they add into one curve.
- **In thermal video, no light shows.** An LED gives off almost no heat, and a lamp's light leaves through a cover
  opaque to thermal infrared. Of the PURSUE ledger's 112 sensor clips, 106 are thermal.
- **Jacob, 2026-10-20:** "a handy tool, as we want to be robust to all single-camera videos, not just PURSUE. And we
  don't know what will come in future tranches." So visible-band look-alikes matter even though PURSUE is mostly
  infrared.

## What is in mcdonald now

`docs/method.md` §19 is the full account; `flicker`'s docstring item 13 is the short one.

- **`lights`, `reach`, `light_reach`.** On every frame, each tracked thing's 3 brightest pixels and 3 reddest
  (R - max(G, B)) are read, each over a ring's median.
  - They are read in `_apertures`, from the same reading of the frame as the sum, so the frame is decoded once.
  - The disc covers the thing's whole silhouette (`reach`: the patch 4 robust sigmas off the sky joined to its middle).
    `extent` cannot serve: it is the core, and a tail light sits far outside it.
  - The controls are the same readings at four places, at least twice that disc away, named "background light dx,dy"
    (`curves(lit=, litring=)`). Their place is `max(off, 2 * r_out + 6)` px from the object.
- **`flashes`, `blinks`.**
  - A flash is a run over a 2-s running median: above 2.5 robust sigmas throughout, reaching 5. Runs closer than
    0.15 s are one flash; a light's curve has a floor of 1 grey level of scatter. Each flash is timed by its run's
    centroid.
  - The flash times are folded by Z^2 with 4 harmonics at 0.6-3 Hz, against 2,000 sets of random times.
  - A train is at least 4 flashes at p < 0.01, and its rate is the lowest within 0.8 of the strongest fold
    (BLINK_FUND). `rule` is "anti-collision" (40-100 a minute, 5 % either side), "overlap" (to 180) or None.
- **`deflash`, `blink_reading`, `said_blink`.**
  - `measure` calls `blink_reading` after `judge`. It reads all three curves for each track, then the controls; a
    control train within 5 % of the object's rate marks the object's as `shared`.
  - Where the object has its own train and a beat, the beat is read again without the flashes. If it keeps under half
    its amplitude, it is marked as the look-alike "anti-collision light".
  - Output: `fields["blink"]`, `fields["light_reach_px"]`, and a note.
- **`report.Case.blink_said`.** A sentence in the bottom line. No call, gate or headline changes.
- **Tests.**
  - `test_measurement.test_a_light_that_flashes_in_a_train`: 11 checks on planted curves, random flashes, a sinusoid,
    a flat-topped flash, and `_Flasher`, a dark body carrying a red or white light, plus the bottom line.
  - `test_golden.test_svanstrom_helicopter_lights`: 5 checks on V_054 and V_030, their tracks vendored in
    `tests/golden/svanstrom_v0{54,30}_track.csv`.
  - All suites and golden passed on the branch (Slurm job 8577), and again on the merged tree with `zoom` (job 8699).

## The known-answer run

Every labelled track of Svanström et al. 2021 (`/models/data/mcdonald/svanstrom2021`) went through the branch's
`flicker`: 837 tracks, 405 visible and 432 infrared, of birds, drones, airplanes and helicopters.

| | tracks | trains |
|---|---|---|
| visible helicopters | 70 | **2** |
| everything else | 767 | 0 |

- **V_HELICOPTER_054:** white light, 4 flashes, 1.00 Hz, p 0.003.
- **V_HELICOPTER_030:** red light, 6 flashes, 0.75 Hz, p 0.0005.
- None in any infrared track, and none among 251 birds.

**Where it lives.**
- Working files: `/scratch/mcdonald/blinks-sweep-2026-10-20/`. Per-track JSON in `out/`, `blinks_summary.csv`, the code
  snapshot `mcd_src/`, and the frames under `home/` (MCDONALD_HOME).
- The driver and array script are kept in the uap repository: `analysis/sweeps/svanstrom/blinks_run_track.py`,
  `blinks_sweep.sbatch`, and the summary script `blinks_sweep_summary.py`.
- The visible tracks are written by `heli_lights.py tracks OUT AIRPLANE BIRD DRONE HELICOPTER`. It reads the one
  structured label row, in V_AIRPLANE_002.

## Rules for the next session

- **Everything through Slurm**, small checks included (Jacob, 2026-10-20: "be sure to run jobs on slurm"). Read the
  `slurm` skill.
  - Memory, not CPUs, is what usually blocks: jobs share about 50 GB, so ask for a measured peak.
  - Sweeps go in at `--nice=5000`, throttled to `%10`.
  - The suites: `sbatch tools/suites.sbatch golden`.
- **Point MCDONALD_HOME at scratch for any sweep.** Otherwise hundreds of clips' frames land in Jacob's
  `~/Documents/mcdonald/frames`.
- **mcdonald work goes on a branch in a worktree** (`git worktree add /models/mcdonald-<name> -b <name> main`). Run the
  suites there, and merge only at Jacob's word. Other sessions use main's working tree: on 2026-10-21 it held another
  session's uncommitted `waves` fix (CHANGELOG.md, waves.py, test_waves.py). This merge carried it across with
  `--autostash`; do not commit, reset or discard it.
- **Never push or release** without Jacob's word.

## Open, in order

1. **PURSUE's visible clips and the bird paper's beats, for the record.** Expected: no trains. Each is a sentence for
   `helicopter_lights.md` and the ledger, and for the bird paper's revision ("no Table 1 beat is a light's harmonic").
   - PR49: night EO, aircraft navigation lights. The whole-video pass's tracks are
     `/scratch/mcdonald/sweep/whole/cases/PR49/obj/o*/pr49_autotrack.csv`; the 10 objects o01-o06 and o08-o11 are over
     100 frames. The clip is `data/release_01/videos/DOD_111689168.mp4`, 30/1 fps.
   - PR106: `/scratch/mcdonald/sweep/cases/pr106/pr106_autotrack.csv` (85 frames, under the 2 s that `blinks` needs:
     expect "not read"). The clip is `data/release_04/videos/DOD_111830034.mp4`.
   - Table 1's beats: 10 videos and 25 objects. The configs, with tracks, frames and apertures, are
     `analysis/cases/review/*_final.json`; the chain-rate table is `analysis/cases/pr135/pr135_chain_rates.md`. These
     are thermal, so the brightness curve is the one that matters.
   - Run `mcdonald flicker VIDEO --track T [--dark] --n0 --n1 --json`, or `blinks_run_track.py`, under Slurm.
2. **A visible known answer for an airplane and a drone, at night above all.** The Svanström set has none with a light
   caught. The 180-a-minute overlap rule and the band's upper half have no real positive yet.
   - Best source: footage Jacob or a colleague takes of aircraft near an airport at night, with ADS-B for the type. Ask
     first.
   - Others to look for: Galileo Project visible cameras, if any (`/models/data/galileo_project`); public-domain DVIDS
     night footage of aircraft; Amazon's AOT airborne set (aviation survey Av8; daytime, lights unlikely).
   - Done when at least one airplane and one drone train is found at a rate their lights are known to have, with no
     new false trains on the Svanström set.
3. **Mid-wave infrared.** Most PURSUE pods are mid-wave, and nothing here has a mid-wave known answer.
   - AARO's resolved aircraft videos are in `/models/data/mcdonald/aaro/videos/`, listed in `resolved_cases.csv`:
     "Western United States" (`DOD_109670991.mp4`, commercial aircraft up to 300 nmi), "Atmospheric Wakes"
     (`DOD_109584436.mp4`) and PR-007 (`DOD_111311861.mp4`, aircraft-like, 6 s).
   - They need tracks (`mcdonald look --propose`, then `mark --set` with `--why`).
   - Expected: no train at those ranges. Any train is a positive worth a figure.
   - The Galileo Sphere airliners A1-A12 (long-wave, night; uap `galileo/sphere/cases/A*`) are a further negative.
4. **Synchronised lights across a group.** Wind-farm obstruction lights (FAA L-864) flash 20-40 times a minute
   (0.33-0.67 Hz), every turbine within 0.05 s of the others (uap `analysis/methods/aviation_methods_survey.md` §7,
   Av12). PR48 and PR058 are offshore wind farms seen from above in infrared.
   - First, look whether the lights show in infrared at all.
   - If they do, build two things. A second band under BLINK_BAND (0.3-0.6 Hz needs about 12 s for 4 flashes). And a
     group reading through `--members`: each member's flash times, and whether they are in step (Z^2 of all members'
     times together against members slid apart in time).
   - A formation of drones with synchronised strobes would answer the same way.
5. **Smaller things.**
   - **The frame store.** `Clip.extracted()` (clip.py) checks only the window's first and last frames. Several objects
     of one clip, with overlapping windows, can leave a gap, which is then read as missing frames. V_BIRD_020_o2 failed
     on f00249 this way: frames 240-249 were missing between two partial extractions. Clearing the folder and running
     again fixed it. Count the window's frames (`n_extracted`) instead, and give a sweep's array tasks a frame store
     each or one clip per task.
   - **Record how many controls were read**, not only those that flashed. V_030's controls may all have left the
     frame: its light disc is large, and the controls sit twice it out.
   - **Put the light curves in `<out>_flicker.csv`** (columns "<name> white", "<name> red") for figures. Check first
     that `share rerun` and the reference cases do not choke on new columns.
   - **Check the window** (`report_qt`, the case page) shows the blink note and the bottom-line sentence.
6. **Release** when Jacob says: version bump in `src/mcdonald/__init__.py`, move CHANGELOG's Unreleased entries under
   the version, tag, PyPI.

## Traps paid for

- **The fold's strongest is a harmonic.** Flashes in step at 1/P are in step at k/P, as tightly: a planted 1.00-Hz
  train read 3.00 until the lowest near-strongest rate was taken.
- **`extent` is the core's.** The first sweep found no trains at all: V_054's extent is 8.5 px, its lights 14-35 px out.
- **A merge window longer than the gap between flashes.** At 0.35 s, a 2.5-Hz train merged into one flash.
- **A robust scatter of zero.** A grey frame's red excess is exactly 0 between flashes, so every flash was infinite.
- **The highest frame of a flat-topped flash.** A rotating beacon's flash is flat on top. Timed by its highest frame,
  V_030 folded at p 0.026; by its centroid, 0.001.
- **A driver without `if __name__ == "__main__"`.** mcdonald's pools re-import the main module.
