# Handoff: `drift`'s T4b reads the remains' fall from the speed band (2026-11-02)

Branch `drift-band`, worktree `/hugespace/models/mcdonald-band`, off `main` at 3375cb9 (0.4.0). Uncommitted: the
maintainer reviews, commits, merges and releases. Nothing in the main checkout was touched.

## What changed, and why

Test 4b ("if it was struck, do its remains sink steadily?") fitted the remains' screen-down position as a line and
a quadratic in time, with a moving-block bootstrap error (blocks of 15 frames, 2000 draws), and excluded a falling
wreck of every body smaller than g cos δ / (a + 3σ). On the Yemen known answer that read -0.08 ± 0.06 L/s² and "no
falling wreck of any body smaller than about 75 m".

The 0.4.0 speed band (`kinematics.speed_band`, method §32) on that same remains track finds a correlated wander with a
range of 0.55-0.75 s (sill 4-6 px, nugget 0.31-0.37 px): longer than the bootstrap's 0.5-s blocks, so the bootstrap's
error is too small. The band's change of the screen-down velocity over the 3.5-s stretch is -13.24 ± 11.29 px/s, i.e.
-3.78 ± 3.23 px/s² = -0.17 ± 0.145 L/s² (L = 22.3 px; 2.4 times the bootstrap's error), and its 95 % bound on a steady
change of speed it could have missed (`change_bound`, "the band's own change and a free quadratic's, the larger") is
35.22 px/s over 3.5 s = 10.06 px/s² = 0.451 L/s² either way. With g cos 40.55° = 7.46 m/s² the honest reach is
7.46 / 0.451 = 16.5 m, not 75: a 5-m wreck (1.49 L/s²) is still excluded three times over, a 20-m wreck (0.37) no
longer is. The record of these numbers is the uap repository's `analysis/cases/hellfire_yemen/band/README.md` and
`band.json`; a Slurm probe here (job 19630, `logs/drift_band_probe_19630.out`) reproduced them to the digit before any
code was changed.

The change (`src/mcdonald/drift.py`):

- `fall(track, fps, rng)` keeps everything it returned and every draw from `rng` in the same order (a paper's figure
  script reproduces the bootstrap), and adds, from the track's own band (None where the track has none):
  `band_accel_px_s2` = dv_xy[1] / span (+y down), `band_accel_err_px_s2`, `band_accel_max_px_s2` =
  change_bound.dv_max_px_per_s / span (None where the band saw the change), `band_range_s` and `band_nugget_px` (the
  larger coordinate's), `band_light`. The band draws from its own seeded generator (`JUMP_SEED`), not the stage's.
- `relative(remains, piece, fps, rng)` adds `band_speed_px_s` and `band_speed_err_px_s` from the band on the
  difference track; `test_tracer` records them as `pieces_band_L_per_s` beside `pieces_L_per_s`. T4a's rule and
  bound stay on the lines' rate.
- `test_wreck(accel_L, accel_err_L, delta_deg, min_m=WRECK_MIN_M, band=None, fail_m=WRECK_FAIL_M)`: the reach is
  g cos δ over the band's bound where it gives one (`reach_by` "the band's 95 % bound on a steady change of speed"),
  else over a + 3σ (`reach_by` "a + 3 sigma"). Records `band_accel_L_per_s2`, `band_accel_err`,
  `band_accel_max_L_per_s2`, `reach_by`; the reading gives both accelerations and the bound in plain words.
- `measure` passes the band (the `fall` fields over L[0]) to `test_wreck` and adds `band_range_s`, `band_nugget_px`,
  `band_light` and `bootstrap_block_s` to T4b's record. The command-line table and per-test lines have no new rows;
  the JSON carries the new fields.

## The thresholds, and one decision to review

- **The pass needs a reach of 10 m** (`WRECK_MIN_M`, was 20): the test asks whether the remains sink steadily, and a
  16.5-m reach excludes every drone and every bird there is; at 20 m Yemen would have fallen to "cannot say". The
  maintainer can move it.
- **The fail rule keeps its 20-m constant apart** (`WRECK_FAIL_M`, new: the quadratic's a - 3σ at or above half a
  20-m body's free fall), so it does not move with the pass threshold.
- **The fail rule is now tried before the pass rule** (it was after). With the pass at 10 m, a 20-m body's measured
  fall (a = 0.375 ± 0.05 L/s², reach 14 m) would otherwise have passed as "a steady sink"; tried first it fails, as it
  did at the old threshold. The cost: a well-measured acceleration down between a 20-m and a 40-m body's fall (say
  0.28 ± 0.03 L/s²) now fails where the old order passed it. Yemen, the synthetic sink and the 5-m wreck are the same
  either way. If the old order is preferred, swap the two `if` blocks at the end of `test_wreck` and drop the two
  threshold checks in `test_t4b_...` that pin it (the 20-m body's fall).

## The Yemen known answer, before and after (the stage's own output)

Before (job 19634, `main` at 3375cb9 exported to `/scratch/tmp/drift_band/before`):

    T4b passes: the remains sink at a steady rate, accelerating at -0.08 +- 0.06 lengths/s^2: no falling wreck of any
    body smaller than about 75 m

After (job 19633, this branch; `/scratch/tmp/drift_band/yemen_envelope.json`):

    T4b passes: the remains sink at a steady rate: their acceleration is -0.08 +- 0.06 lengths/s^2 by a quadratic in
    time, and -0.17 +- 0.14 with the track's own wander fitted (a band), which would have shown a steady change of
    more than 0.45 lengths/s^2 either way (95 %): no falling wreck of any body smaller than about 17 m

(16.52 m; the reading rounds to 17.) T4b's JSON: `band_accel_L_per_s2` -0.17, `band_accel_err` 0.145,
`band_accel_max_L_per_s2` 0.451, `reach_by` the band's, `excludes_wrecks_under_m` 17.0, `band_range_s` 0.75,
`band_nugget_px` 0.365, `band_light` green, `bootstrap_block_s` 0.5. T1, T2, T3 and T4a are unchanged to the digit
(every field of their records identical before and after; T4a gains only `pieces_band_L_per_s`), and so are the
verdict, its reason, the depression and the relative line.

T4a's band numbers: `pieces_band_L_per_s` [0.79, 0.62] against the lines' `pieces_L_per_s` [0.82, 0.68] -- in px/s
17.64 ± 0.13 and 13.89 ± 0.15 against the lines' 18.4 and 15.2 (within 4-9 %).

## Tests and docs

- `tests/test_drift.py`: the steady sink still passes and the 5-m wreck still fails, each read with its band (the
  wreck's band sees the change, z = 16, and gives no bound, so its reach is a + 3σ); a drawn track with a slow wander
  (`kinematics.simulate_track(106, 30.0, v=(2.0, 32.0), nugget=0.35, sill=5.0, range_s=0.65, start=(-45.0, 27.0),
  frame0=640, rng=default_rng(1))`) gives a band bound of 8.76 px/s² against a bootstrap error of 1.04 (the band's own
  error 2.63; range 0.64 s against 0.5-s blocks), and `test_wreck` reports the band's reach; the thresholds (15 m
  passes, 8 m cannot say, a 10-m and a 20-m body's measured fall fail); the Hellfire known answers expect the reach
  between 12 and 22 m, the band's -0.17 ± 0.03, the pieces' bands within 10 % of the lines', from the readings and
  by the command line. Puerto Rico and Santa Barbara have no remains: unchanged. `tests/golden/hellfire_drift/` holds
  inputs only, nothing to update.
- `docs/method.md` §34 only (the T4b bullet and the Yemen known-answer paragraph; checked by `git diff` that both
  hunks lie inside the section). `CHANGELOG.md`: a bullet under Unreleased. `tests/README.md`: the T4b checks and the
  known answer's numbers. `README-technical.md` and `cli.py` do not state T4b's rule or the 75 m: untouched.

## The jobs (all through Slurm from the worktree; logs in `logs/`)

| job | what | result |
|---|---|---|
| 19630 | probe: the band on the test tracks before any code change | matches the uap repo's band.json |
| 19631 | `tests/test_drift.py` + `tests/test_reduction.py` (first pass, before the last label edits) | drift 104 PASS, reduction 568 PASS; 0 FAIL, 0 SKIP; both ALL PASS, exit 0 |
| 19632 | `tests/test_golden.py` with `MCDONALD_DATA=/models/data/mcdonald` | 198 PASS, 0 FAIL, 0 SKIP; ALL PASS, exit 0 |
| 19633 / 19634 | the stage on the Yemen inputs, after / before | quoted above |
| 19635 | `tests/test_drift.py` on the final files | 104 PASS, 0 FAIL, ALL PASS (0 skipped) |

## Left for the maintainer

- Review the three decisions above (the 10-m pass, the 20-m fail constant, the fail rule first), commit, merge
  `drift-band`, release (0.4.1 or with whatever else is unreleased).
- The uap repository is read-only for this change: the Yemen case notes and the drift paper quote "about 75 m" for T4b;
  the paper's figure script reproduces the bootstrap's draws, which are unchanged, but its T4b text and the case's
  `*_drift.json` outputs want regenerating with the new reach (16.5 m) once this is merged.
- `_band` runs the speed band on the remains, on each piece (for `pieces_fall_L_per_s`, where only the bootstrap's rate
  is used) and on each difference track: a few seconds each on 100-point tracks. If that ever matters, `fall` could
  take a flag to skip the band for the pieces.

## Merged

Merged into `main` on 2026-11-02 at Jacob's word ("Go ahead and merge drift-band"), under 0.4.1's heading in the
CHANGELOG (0.4.1 was not yet tagged). The research repository's drift paper and Yemen case were re-run on the merged
stage the same day.
