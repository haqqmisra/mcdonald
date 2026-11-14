# Handoff: the Galileo Project's known answers, branch `nevada-fixes` (2026-11-13)

**Jacob, 2026-11-13**, after the known-answer study of the Galileo Project's triangulated objects (the uap
repository's `galileo/nevada/README.md`): "Yes, make all fixes to mcdonald." Four report-changers, IDEAS.md N1-N6,
method section 53. Built on `nevada-fixes`, a worktree at `/hugespace/models/mcdonald-nevada`, branched from `main` at
a72784c (0.5.3). Merged into `main` at 3459561 (2026-11-13), N3 revised at 4847926 (`galileo/nevada/n3/` in the uap
repository), and released in 0.5.4 (2026-11-14).

## What was built

| | what | where |
|---|---|---|
| N1 | T2 from the lines of sight allows a model's own error, `MODEL_WIND_ERR` 3 m/s; each wind carries its `source` | `drift.test_wind_track`, `drift.track_winds`; method section 34 |
| N3 | a beat comes back by windows apart only beyond chance (`CHANCE_P` 0.01, binomial on `independent_windows` at `drift_rate`); drift weighs older envelopes from their own windows | `flicker` (pick's `windows_independent`, `windows_chance_p`, `comes_back`), `drift.held_beat`, `report`; method section 13 |
| N4 | T3 from several cameras at once: `--flicker a.json,b.json`, `drift.test_beat_cameras`, `AGREE` 3 | `drift`; method section 34 |
| N5 | no size, kind or distance from the tracker's default spot; the camera stage's length at half the peak in its place; the track stage records `object_size_from` | `report.extent` (`SPOT_DEFAULT`, `SPOT_NOT_MEASURED`, `LENGTH_SIZE`), `stages` |
| N6 | the speed across the line of sight carries the range's and the scale's errors (said in the report); `--lens-k2` | `report`, `lens` (`Lens.k2`, `radial`, `slope`, every function's `k2=0.0`), `stages.through_lens`, `scale`, `run_case`, `KNOWN`, `kinematics_cli`; method sections 37, 53 |

With k2 0, no model wind, a whole-track beat or a size given, every number is as before.

## How it was tested

- `mcdonald-test --golden` on Cannon, snapshot 464e326 (run `20261113-112022-nevada-fixes-464e326-wip`): every suite
  passes, 228 goldens included. `tests/test_drift.py` from the same snapshot on Cannon, with the footage: ALL PASS.
- New tests: `test_drift.test_track_t2_a_models_own_error`, `test_t3_windows_apart_against_chance`,
  `test_t3_two_cameras`; `test_reduction.test_a_spot_size_is_no_size_at_a_given_range`, `test_the_lens_second_term`.
- On the Galileo data (uap `galileo/nevada/README.md`, "After the fixes"): clouds called drifting 23 -> 69 of 119,
  called not drifting 16 -> 4; aircraft unchanged (0 drifting, 54 of 80 not drifting); T3 false beats 14 -> 3 on
  clouds, 2 -> 0 on aircraft. Mismatched cloud pairs (a false low point) now mostly pass as drifters (9 -> 31 of 40):
  drift cannot tell a wrong height, and model winds change too little with height to show it. With k2, the speed's
  median ratio beyond 300 px from the centre goes 1.113 -> 0.966; overall 1.010 -> 0.983, the 90th-percentile error
  about 20 % either way (not the lens).

## For the maintainer to decide

1. **Commit, merge, version.** The branch is uncommitted in its worktree. CHANGELOG has an "Unreleased" entry.
2. **N2, holding still.** T2 never asks whether a body holding still fits as well as a drifter. Wherever the wind is
   weaker than T2's tolerance it does, and a hovering body passes. A test with power would change the Puerto Rico
   lanterns' T2 (their winds spread 6.2 m/s). Not built.
3. **N5's order.** The measured length is used only in place of the tracker's default. It was closer to the Galileo
   aircraft's size than any spot (1.29 times, against 2.80 for the default), and putting it before a spot the marks set
   would move hand-marked reports' sizes (PR113's 21 px). Not done.
4. ~~`test_drift` is in no suite list~~ -- added (Jacob, 2026-11-13) to `tools/suites.sbatch` and both workflows'
   lists (its three command-line clip runs skip without $MCDONALD_DATA, as on GitHub's runners).
5. ~~The window's card does not ask for k2~~ -- added (Jacob, 2026-11-13): `known_qt` asks "and its second bending
   term, if given", either sign, needing the field of view as k1 does.

**Jacob's answers, 2026-11-13:** commit and merge to main, no version yet; the hover test (N2) to be measured on the
known answers before anything is built; N5's order kept as built (the length only in place of the default spot).

**N2 measured (2026-11-13):** IDEAS.md N2 has the numbers. A strict rule costs the Puerto Rico lanterns their pass;
a comparative one (drifting needs less airspeed than holding still, at every wind) keeps it. **Jacob chose the
comparative rule; built 2026-11-13** (`drift.test_wind_track`: `hold_still_m_s`, `drift_beats_hold`;
`test_drift.test_track_t2_holding_still_against_drifting`).

**Merge to main: waiting.** `nevada-fixes` has main's 4ef5f57 merged in (0f61868; all suites pass on Cannon), but the
shared tree at /models/mcdonald holds session 22's uncommitted work in `flicker.py`, which this branch changes too:
git refuses to move main over it, and forcing would lose that work. Once it is committed:
`git -C /models/mcdonald merge nevada-fixes` (a fast-forward if main has not moved again).
