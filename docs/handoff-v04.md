# Handoff: ROADMAP 0.4 -- session 8 (2026-10-29) on top, sessions 7 (2026-10-28/29), 6, 5, 4, 3, 2 (2026-10-28) and 1 (2026-10-27) below as the record

## Session 8 (2026-10-29): the ledger finished in the window and in `run`; PR43's dash read through its own blur; Jacob's answers built; focus a step

Jacob: "see docs/handoff-v04.md and remember to use /slurm". Session 7's item 1 waits on Jacob's word (below, still
open), so this session took **item 2, the ledger finished** -- the report card, the bounds in `run`, R from a range
ratio -- and **the streak half of item 5** (PR43's dash with the clip's own blur). On main, **committed locally, not
pushed** (nothing pushed or released until 0.4.0); no version bumped; CHANGELOG's Unreleased has four new items.

**Built in a worktree**, `/hugespace/models/mcdonald-s9` (branch `v04-s9` off e670858), fast-forwarded into main at the
end and removed: Jacob's `orbs_propose` array (`metallic_orbs/jobs/propose_array.sbatch`, 41 tasks) runs `mcdonald look`
from this checkout, a task starting every few minutes. The card and the range ratio (report.py, report_qt.py and their
tests) were edited on main's checkout before I saw the array -- whole-file edits, each complete and checked; everything
after went to the worktree. Scratch: `/scratch/mcdonald/v04-s9/` (`look/` the cards drawn off screen, `scripts/`
`card_look.py`, `one_drive.py` (one of test_gui's drives alone), `pr43_blur.py`; `runs/` PR43's readings; `logs/`;
`suites/` the job script and logs; the snapshots removed).

### What was built

| what | where | tested by |
|---|---|---|
| **the four unknowns on the card**: Scale, Range, Aspect and Camera's speed on every card with a speed in the picture -- the value (", assumed" on a guessed field of view), a bound ("2.5 km to 57 km", "at most 1.2 km"), or "not known" written quietly (muted, not bold); the tooltip the ledger's route and "What would give it: ..." | `report_qt.facts`, `unknown`, `_bound`, `UNKNOWNS`, `NOT_KNOWN` | test_gui (one-press drive: 3 checks) |
| **R from a range ratio**: a reference of known length is at L k / l, the object R_obj / R_ref times as far; in the summary's range row, the ledger (as assumed as k is: "assumed" on a guessed FOV), the admissible region's bounds; beside the reference the size needs no k (S = p (R_obj/R_ref) L / l); without the ratio or without k, the range row says what the reference would give | `Case.ranged`, `range_bounds`, `ledger`, `summary` | test_reduction (the four unknowns: 3 new checks) |
| k's row no longer suggests a reference gives k ("no graticule, field of view or slew"; with a reference: "gives the speed across the line of sight without it (k cancels)") -- PR149's card said "no graticule, reference, ..." with a reference given | `Case.ledger` | test_reduction |
| **`horizon` and `haze` as steps of `run`** (and so of the window's Measure form): `--height` + a point (`--horizon N,X,Y`, or the first horizon mark in `--marks`) runs horizon; `--visibility` or `--haze-reference N,X,Y,M` runs haze; each its command's own call with its command's own k ((FOV px) / FOV, or the graticule -- not the case's pinhole k, so the numbers are the command's), the command recorded, the bound into the ledger and the admissible region; planned (a jewel each) only where what it needs is given; a height with no point is NO POWER saying so; what cannot go together refused before anything is measured | `stages.KNOWN` (4 rows), `OPTIONAL`, `ORDER`, `planned(**known)`, `check_known`, `horizon_point`, `haze_reference`, `run_case`; `haze.parse_visibility`; `measure_qt.STAGE_WORDS`, the plan; `COMMAND` | test_horizon (`test_a_step_of_run`, 6 checks on a rendered sea clip through `run_case`); test_reduction (planned); test_gui (the form's rows, `run --help`) |
| **`streak` takes the blur back exactly** (`motion_px`: the inverse of a box's half-peak width through a Gaussian blur) instead of subtracting it whole, and **reads the blur off the scene's points** by default (`scene_blur` = `forensics.point_blur`; `--blur` gives it; 2 px, said, with too few points) | `streak.motion_px`, `scene_blur`, `BLUR_ASSUMED`, `main` | test_streak (the old exposure 0.462 -> 0.500; 3 new checks) |

**The choice made for item 2 ("a page or `run` stages for the bounds"): `run` stages fed by known quantities** -- the
pattern Jacob set for what is known (2026-10-09: asked before the one press or after it, never during; new knowns go in `stages.KNOWN`), with no new
page or pop-up, the one press asking nothing; the window reaches them through the Measure form's technical fields and a
horizon mark. Jacob's word may move it. **`focus` is not a step**: branch `metallic-orbs` (06cc313, not in main) is
reworking it (a dark edge read with no points, `--ground-scale`); wire it after that merges, the same way (a `--band`
or `--pupil` row). **`slew` is not a step** (it needs a pointer read every frame and the scene's chain; `--case`
remains its route).

**The card, drawn off screen** (`look/pr43_fov.png`, PR113, PR149 from session 7's unpacked case files, 0.3.0's): PR43
at 65.6°: Scale "1490 px/rad, assumed", Range / Aspect / Camera's speed "not known" (muted) between the found rows;
PR113: Scale "2028 px/rad" (graticule); PR149: all four not known, its speed across from the ship. The words were mine
("not known", "assumed", "What would give it"); Jacob chose others the same day (below).

### PR43's dash through its own blur (session 7's item 5, the streak half)

`forensics.point_blur` on PR43's frames 50-75 (its case file's track): **3.6 px** at half the peak, from 43 compact
spots on 12 frames (4 on the sensor left out). Reading the dash at 3.6 px showed the subtraction was wrong, not only the
blur: a box of motion drawn through a Gaussian is the box's length at half its peak once it is a couple of blurs long,
so "the length less a blur" read every dash short -- test_streak's own half-frame shutter at 0.46, a 20-px/frame dash
through 3.5 px at 0.34. With `motion_px`: **PR43's exposure 15.6 ms, 0.47 of a frame, at its blur; 14.7 ms at 2 px**
(11.5 before) -- the median of the frames' ratios; the medians' ratio gives 12 ms (the centroid's jitter, the speed
band's 5.7-px nugget, spreads the frames' speeds: a kriged speed per frame would be the better divisor, not done). At
3.6 px the dash (7.0 px) is under three blurs: **no light curve, so session 2's "no beads at 134 Hz" made at 2 px does
not stand.** ROADMAP row 757 and method §30 say so.

**Item 5's other half, `horizon` on PR149's ship, cannot be done**: PR149 looks about 29° down at the ship (the uap
case note, `pr149_transit.md`), no horizon in the frame, and the platform's altitude is not known (1-5 km). A sea
horizon with a known height and range is still wanted (AARO's or the Galileo clips).

### Tests at the end

From a snapshot of the worktree's tracked files (`git ls-files -z | xargs -0 cp --parents`), one Slurm job a suite
(`suites/one.sbatch`, niced 100, 4 CPUs for gui/golden/measurement/camera, 2 for the rest), `MCDONALD_DATA` set,
`TMPDIR` `/scratch/tmp/s9`; logs in `/scratch/mcdonald/v04-s9/suites/logs/`: **all 20 pass** -- measurement 491, reduction 432 (429 + the range ratio's 3), gui 750 (747 + the card's four unknowns' 3; the WxAgg backend skipped as before), camera 134, cli 126, **golden 140 PASS, 0 SKIP**, slew 59, audio 54, published 32, zoom 31, share 25, tether 24, horizon 23 (17 + `test_a_step_of_run`'s 6), waves 14, stabilize 13, aspect 10, focus 10, sweep 10, haze 9, streak 5. The streak fix came after that snapshot: from a second one, streak 8 (5 + the blur's 3), reduction 432, cli 126, horizon 23 and haze 9 again (the `_2` logs).

**After Jacob's answers** (the second commit, from a third snapshot; logs `r2_*`, and `r3_*` for the suites the Help
text, README and CHANGELOG reach, run again from the last snapshot): **all 20 pass** -- gui 753 (750 + the horizon's
click and the card's questions: 3), reduction 433 (+ no bend at all), horizon 24 (+ given afterwards), golden 140 PASS
0 SKIP, measurement 491, cli 126, the rest as above.

**A slip**: one `python3 -c` spot check of `motion_px` (six numbers, about a second) ran on the desktop, not through
Slurm; everything else went through srun/sbatch. Jacob's own jobs (`orbs_firstlook`, `orbs_propose`, `math_*`) ran
alongside, untouched.

**Left behind:** nothing in `/tmp`; `/scratch/tmp/s9` removed; the snapshots and PR43's extracted frames (`v04-s9/frames/`) removed; `/scratch/mcdonald/v04-s9/` kept (732 KB: the looks, scripts, runs and logs); the frame cache `~/Documents/mcdonald/frames` untouched; the worktree `mcdonald-s9` and its branch removed after the fast-forward (the second round's worktree `mcdonald-s9b` likewise). Jacob's other worktrees (`drift`, `rotor-note`, `fold-double`, `metallic-orbs`, `v04-window`) untouched.

### Jacob's answers (2026-10-29, the same session, by multiple choice), and what was built from them

| asked | his answer | built |
|---|---|---|
| how the window reaches the horizon and haze bounds | **also in the plain form** ("Do you know anything else about this video?", segment step and report card), not only Advanced Mode's Measure form | `known_qt.KnownForm`: "How high was the camera over the sea?" (meters / feet), "Where is the sea's horizon?" (a click on the video: `start_point` on the main view, `Screen.start_point` on the segment step's player; the frame on the screen and the point, or a drag's middle; Clear), "How far could you see that day?" (kilometers / miles; `--visibility` takes `mi`); height and horizon go together; kept for the video (`remembered`: AFTER + LATER) and shown in the Measure form; the one press uses them; on the card "Work out the speed" does the two steps on the track already followed (`stages.LATER`, `add_known` via `horizon_step` / `haze_step`, the same calls `run_case` makes; `mcdonald report CASE --height --horizon --visibility`) |
| the ledger's status words | **keep** (constrained / assumed / bounded / missing, the headers) | nothing to change |
| the card's words for the four unknowns | **"unknown" / "To find it: ..." / ", a guess"** | `report_qt.NOT_KNOWN`, `unknown` |
| card "coming closer" against report "closing on the camera" | **the card uses the report's words** | "fits, closing on the camera" / "fits, receding"; "Time to the camera" "... s ago, receding"; Help's "Read the report" says so |

The three new questions sit **after** the existing ones, under a line "These say how far away the object can be, with
no speed at all: over the sea, or in the haze of a day." -- his preview drew them first, as a sketch; the card opens on
"Its real speed needs ...", so the speed's questions lead. A word from him moves them. Found on the way: a drawn track
with no bend at all left the turn's 95 % bound empty and **`projective.said` raised** (the kinematics stage failed
quietly in `run`, loudly in `add_known`): now "no bend at all: it did not turn" (test_reduction).

### Focus as a step, after `metallic-orbs` was merged (the same day; Jacob's two answers)

Jacob merged `metallic-orbs` (7359594) and chose, by multiple choice: **the camera's band starts the focus step** (not
every case with a scale -- its floor rests on "focused far"), and **the plain form asks it too**. Built: KNOWN rows
`band`, `pupil`, `focus_at` (`--focus-at`, the command's `--focus`), `ground_scale`; `stages.OPTIONAL["focus"]`,
`focus_step` (the command's own call and k, the object's polarity and the mask rows), in `run_case` after the haze and
in `add_known` (LATER); `NOTES_OF` tells each step's notes apart (horizon's and focus's both begin "k comes from an
assumed field of view"); `check_known` refuses an unknown band, an unreadable pupil or focus distance, and the pupil,
focus distance or ground scale without a band; the jewel "How far away it is at least, from how sharp it is beside
the scene's own points"; the plain form's "What kind of camera was it?" (don't know / daylight / near infrared /
short-wave infrared / heat (mid-wave) / heat (long-wave) -- his list, with short-wave infrared added since the band
exists; described on the card as "a heat (mid-wave) camera"). Tests: test_horizon (the step's numbers are the
command's; given afterwards and forgotten; the refusals), test_reduction (the plan), test_gui (the card's question
against `mcdonald report CASE --band mwir`). **All 20 suites pass** from a snapshot of it (logs `r5_*`): gui 753 (1 skip,
WxAgg), reduction 436, horizon 25, focus 19 (the merged branch's), golden 140 PASS 0 SKIP, measurement 491, cli 126, the
rest as above.

### Open, in the order I would take them

1. Jacob's look at the plain form's four new questions in the window (their place, the click on the horizon, the
   camera's list).
2. A real clip with a known range for each bound: a sea horizon with the camera's height, a daytime EO clip for the
   haze, and the focus (the Galileo aircraft with ADS-B would serve the focus and tau both).
3. `share rerun --strict` on the 14 case files and the recipe's remake for 0.4.0 (every report changes: the band, the
   survivors, tau, now the card's rows and the ledger's range from a ratio where a case has one).
4. tau on real objects (session 7's item 4): the Galileo aircraft when the ADS-B data comes.
5. `streak`'s speed per frame from the speed band rather than the centroid's differences (PR43's 12-16 ms spread).
6. The sweep's open items (session 2's item 3); the parallax ladder when Long's revision is in (PR043 on hold).
7. `camera --scene` into `run` and the window; Find/Follow on a saturated bloom; `slew` on a dial that stalls; session
   4's item 6; session 7's item 9 (the residual bootstraps a quarter narrow, `projective.turn` past a quarter turn).

---

## Session 7 (2026-10-28/29, overnight): the window's plain words for the band and the survivors; tau from a stage

Jacob: "see docs/handoff-v04.md and remember to use /slurm". Took session 6's open list in its order: **item 1 (the
window) and item 2 (tau from a stage)**. On main, **committed locally, not pushed** (e78e092 the window; the tau
commit after it; nothing pushed or released until 0.4.0). No version bumped; CHANGELOG's Unreleased has two new items.
Everything that ran the package went through Slurm (srun for the looks, sbatch for the controls and the suites). This
session's scratch is `/scratch/mcdonald/v04-s8/` (`cases/` the reference case files unpacked, `pr43_fov`, `pr144_now`,
`pr135_now` with their speed step done again by this code; `look/` the card drawn off screen before and after;
`scripts/` the looks, the rendered approach `looming_clip.py`, the drawn sweeps `wander3.py`/`.jsonl`; `controls/` the
tau control over the 31 objects -- `objects.json`, `one.py`, `array.sbatch`, `out1/` the first rules, `out2/` the
second, `out/` the final; `suites/` one.sbatch and the logs; `snap*/` the snapshots the jobs ran from).

### Item 1: the window, in plain words (e78e092)

The card cut every value at its first bracket, so the band's "± e" and its range never reached it, and the three rows
of section 33 showed under the report's own names ("Constant velocity, as a pinhole draws it": "passes: closing, T =
0.91 s, θ = 39°"). Now `report_qt.facts` gives the rows, each with the summary's `how` as its tooltip:

| row | values | from |
|---|---|---|
| Along the track (under the speed) | "steady, ±e px/frame" / "A to B px/frame" (the least to the most) | `kin.band_said` in the tip; PR43 at 65.6°: 11.6 to 31.4 |
| Turn | "did not turn" / "a hair off straight" / "its path bends, radius N widths" | the image path: camera or lens can bend it, said in the tip and the report |
| Straight and steady | "fits, coming closer" / "fits, going away" / "fits, no closing seen" / "does not fit" | `projective` |
| Moves in a frame | "2.5 of its widths" | the smear |
| Time to the camera (item 2) | "in 2.0 s" / "7.3 s ago, going away" | `Case.tau()` |

The value column takes the room the labels leave (a short value no longer wraps in three lines). Help -> Getting
started's "Read the report" says what the rows are; the speed step's jewel says it measures them. **My words, not
Jacob's**: the card says "coming closer" where the report says "closing on the camera"; the report keeps session 6's
wording ("the track itself says this", "a hair off straight", "did not turn", "closing on the camera") -- **still
awaiting Jacob's word**, as session 6 asked.

### Item 2: tau from a stage (method §33, "From a stage")

| what | where | tested by |
|---|---|---|
| the size (`extent`, every frame up to EACH_MAX 300) and the ring's median level (`flicker.level`) read with the brightness; NaN where tried and nothing read; "object size"/"object level" in `<tag>_flicker.csv` | `flicker.curves(each=)`, `_apertures`, `judge(each=)` | test_measurement (the columns) |
| `tau_of`: the looming law **with the blur's offset** (s = a/(t_z - t) + c; without c a rendered disc closing at 2.0 s read 3.3), t_z refined between grid points (the bootstrap band had collapsed on the grid); the rules TAU_MIN_PX 4, TAU_COVER 0.6, TAU_ODD 3 MAD slips (mirror-padded: "nearest" made a first slip its own median), TAU_Z 4 (sigma widened by the lag-1 n_eff), TAU_GROW 2 px, QUAD_SLACK, FAR, TAU_REL 0.3; no bound from a size that holds (the blur's share is unknown: the bound I first drew said "at least 12 s" of a thing 2-6 s out) | `kinematics.tau_of`, `_trend`, `looming_fit(offset=True)` | test_reduction (8 checks) |
| the light curve, conditional: unresolved, not beating, 10 % at TAU_Z, gain out by the ring's level; said as "would give tau = x s at the track's middle if the change were its range's alone" (gamma: long by up to 2.2) -- never the route | `tau_of` | test_reduction, test_measurement |
| the stage's `tau` field (a track each) and its result line; a group member carries its own. **No NO POWER for tau**: I first listed one wherever no track had a size, and two of test_measurement's checks showed what it does -- the flicker stage's NO POWER list is the beat's (callers read "nothing refused" from it, the CLI's error is its first entry), and most objects are points, so every flicker stage and every report's count would carry it; the summary's row says why instead | `flicker.tau_reading`, `tau_said`, `of_member` | test_measurement |
| into the case: the summary row "time to contact"; θ from τ and **ω at the last frame** (the band's v_end / k -- the track's average put a drawn approach at 2° for 6°) in the summary and the ledger (constrained); τ's line in the admissible region (with ω at the last frame); the bottom line's sentence beside the path's own T ("which agrees" / "does not agree") | `Case.tau`, `tau_reading`, `omega_last`, `ledger`, `admissible`, `survives` | test_measurement (rendered: 1.95 ± 0.13 s for 2.03, θ 6° for 6.1°; receding -7.27 ± 0.19 for -6.97; held: none, the row saying why; a point: light only, 3.83 s for 4.02) |

**Calibration.** Drawn (`scripts/wander3.py`, 4 s at 30 fps, rounded sizes): looming at tau 2 s found 40/40 (median
1.97, pulls sd 1.25: the band is a quarter narrow); at tau 6 or 16 s never (grows under 2 px -- the size route reaches
a thing that closes in about the track's own length); a wandering size passes 1/100 (0.3-s memory), 2/100 (1 s; 3 of
the test's 40), 8/100 (drifting as slowly as the record is long -- no size rule tells that from an approach, hence the
path's T beside it). **The 31 objects of the 14 reference case files** (`controls/`): with z 3 and no coverage or
slip rules 7 claimed a tau (PR097's four dots sized on 20-50 of 126 frames at 7-55 px; PR149; PR135 object 2; PR44 at
-22 s); with the final rules **none**: 10 never sized (or on under ten frames), 9 sized on too few of the frames tried,
12 hold (PR44's bird at 3.1 sigma). Every recorded object in the set is a point or a small blob whose size the far ring
reads unsteadily: the size route has not yet been seen to work on a real video -- the Galileo aircraft with ADS-B are
where it can be.

### Tests at the end

From a snapshot of the working tree with every tracked file (`git ls-files -z | xargs -0 cp --parents`; a first
snapshot of `src tests pyproject.toml` alone failed test_cli's readme and test_reduction's exercises checks for want of
the READMEs and docs/), one Slurm job a suite (`suites/one.sbatch`, niced 100), `MCDONALD_DATA` set, `TMPDIR`
`/scratch/tmp/s8`; logs in `/scratch/mcdonald/v04-s8/suites/logs/`: **all 20 pass** -- measurement 491 (483 + tau's 8),
reduction 429 (422 + tau's 7), gui 747 (the WxAgg backend skipped as before; the card's 3 checks were added in e78e092,
job 13028: 748 -- the count differs by grep, not by a check), camera 134, cli 126, golden **140 PASS, 0 SKIP**, slew 59,
audio 54, published 32, zoom 31, share 25, tether 24, horizon 17, waves 14, stabilize 13, aspect 10, focus 10, sweep 10,
haze 9, streak 5. The round before it (with tau's NO POWER) failed two of test_measurement's checks -- the reason it
was taken out. Jacob's own jobs (`orbs_test_*`, `pr062_*`, `econ_smoke`) ran alongside, untouched.

**Left behind:** nothing in `/tmp`; `/scratch/tmp/s8` emptied; the extracted frames (`v04-s8/frames/`) removed;
`/scratch/mcdonald/v04-s8/` kept (the cases, looks, scripts, controls and logs; the snapshots removed); the frame cache
`~/Documents/mcdonald/frames` untouched (the controls extracted into their own folders and removed them).

### Open, in the order I would take them

1. **Jacob's word on the wording** (session 6's and mine): the report's "the track itself says this", "a hair off
   straight", "did not turn", "closing on the camera"; the card's "Along the track", "Straight and steady" ("fits,
   coming closer"), "Turn" ("its path bends, radius N widths"), "Moves in a frame", "Time to the camera" ("in 2.0 s").
2. The ledger, finished (session 3's item 2): the report card, a page or `run` stages for the bounds, R from a range
   ratio; Jacob's word on the ledger's wording -- no answer yet. (θ from τ is in the ledger now.)
3. `share rerun --strict` on the 14 case files and the recipe's remake for 0.4.0 (every report changes: the band, the
   survivors, now the flicker stage's tau, its CSV columns and the "time to contact" row).
4. tau on real objects: the Galileo aircraft when the ADS-B data comes; before that, any PURSUE clip where something
   visibly closes (none of the 14 case files' objects does). The per-frame `extent` is the weak part: its far ring
   reaches neighbours and bands (see the controls) -- a size read off the object's own stamp, like `stacked_extent`'s
   `local`, may hold better and is the thing to try first if the aircraft fail.
5. The new bounds on real clips (session 2's item 4): PR149's ship for `horizon`, PR43's dash for `streak`.
6. The sweep's open items (session 2's item 3).
7. The parallax ladder's nearest height when Long's revision is in; PR043 on hold.
8. `camera --scene` into `run` and the window; `Find`/`Follow` on a saturated bloom; `slew` on a dial that stalls;
   session 4's item 6.
9. Noted: the residual bootstrap of `looming_fit` (and the projective test's) ignores the residuals' correlation, so
   the band is about a quarter narrow on drawn series; `projective.turn` on an arc of more than a quarter turn reads the
   radius short (a drawn 286° arc: 14 widths for 25) -- the sagitta formula is for a small bend; session 6's item 9.

---

## Session 6 (2026-10-28, late night): the speed band (objective 4) and what survives the missing variables (objective 3)

Jacob: "see docs/handoff-v04.md". Took session 5's open list in its order: **item 1, both objectives, without ADS-B**
-- objective 4 first (K1, K8), then objective 3's parts that need no range. On main, **committed locally, not pushed**
(4526270 the work, then the test fix below; nothing pushed or released until 0.4.0). No version bumped; CHANGELOG's
Unreleased has two new items. This session's scratch is `/scratch/mcdonald/v04-s7/` (`logs/` the reduction suite's
runs as the work went, `suites/` the one-job-a-suite script `one.sbatch` and `logs/` of the snapshot runs, `cases/` the
band over every object of the 14 case files and the golden tracks (`band_cases.py`, `band_table.md`), `try/` the PR055,
PR23 and PR43 figures looked at, `snap/` the snapshot the suites ran from).

### Objective 4: the speed band (K1, K8; method §32)

| what | where | tested by |
|---|---|---|
| **universal kriging in a few functions**: a linear mean, a Matérn-3/2 wander, a nugget; REML (three starts on a 60-evaluation budget, the best run to convergence; a warm restart), Dubrule's closed-form leave-one-out, predictions of the latent path and its rate with the mean's own uncertainty, joint covariances, a draw of the wander and its rate together | `kriging.py` (new; numpy + scipy, dense) | the band's tests |
| **`kinematics.speed_band`**: each coordinate against wall-clock time (exact repeats dropped first; a point 4 of its own LOO sigmas off dropped once; over 450 points fitted on the middle and read in windows of 450): the rate at every kept frame with its sd; the average velocity over the stretch, (f(t1) - f(t0)) / T on the latent path, with its honest error; the velocity's change as a vector, its magnitude, turn and mean acceleration with its sigma; Δln L over a line with white jitter (`constant` under BAND_DLNL 10); the nugget and what one pair of frames reads against it; `series` frame by frame | `kinematics` (`BAND_*`, `band_said`, `pm` -- every value to its error's precision, `simulate_track`) | `test_reduction`: three tests, 41 checks |
| the stage records `band`, says it in two result lines (`speed band`, `speed change`), writes `<tag>_speed.csv` and `<tag>_speed.png` (the rate with ±1/±2 sd, each pair's reading, the average; **the time-distance diagram as the lower panel**, A13); a not-uniform track is described, not refused (the note, the caveat on body lengths and the scale bar, the Reduction's print); `uniform` and `v_px` unchanged | `stages.kinematics(out=)`, `_speed_files`; `figures.speed_band`; `report_figures` | the same; `test_cli` 66 as before |
| the report: the pixel-velocity row carries the average's error and the band's range ("the speed ran from A to B px/s along the track, V ± e on average"); the bottom line says "The object's speed in the image changed: from ... to ... (least, most), V ± e on average; its velocity changed by ... (turn)" where not uniform, "(constant within ±x px/s)" or "(between a and b along the track)" where it is | `report.summary`, `bottom_line` | `test_the_speed_band_in_the_stage_and_the_report` |
| `mcdonald kinematics --out DIR` (its files; default ./<tag> as every command) | `kinematics_cli` | `test_cli` (`--out` given, so the planted clip's folder no longer lands in the cwd: the fix after the snapshot) |

**Held (K8).** Sixteen tracks drawn from the covariance (`simulate_track`: the wander and its rate drawn together, a
velocity and an acceleration on top): the ±2 sd band holds the drawn rate 94 % of the time, z sd 1.05, the average's
z sd 1.03; sixteen lines with jitter: constant within the band 16 of 16, the velocity never said to have changed, the
nugget 0.50 for 0.5 planted; a planted 200 px/s² seen 8 of 8 at 3 sigma or more, read 197. Over 30 draws at five
(theta, T) combinations the coverage was 0.938-0.967 (`cover.py`, run on the desktop by mistake before the Slurm rule
was recalled -- nothing of it kept). On the recorded tracks: the nugget is the survey's (PR055 0.59 px for 0.50, PR071
0.21 for 0.33 with 5 slips clipped, PR144 0.75 for 0.80, PR23 0.61 for 0.65, the balloon 0.45 for 0.44), the band
2.5-9x tighter than the scatter of single pairs; PR43's streak (test_golden) 12-31 px/frame along the track against the
Note's 7-33, the velocity's change 3.1 sigma over 0.83 s; flyer 5 holds to 0.08 px and speeds up 104-174 px/s.

**The band over the 14 case files' 22 objects and the golden tracks** (`cases/band_table.md`, one Slurm job): every
track but PR113's four points has a band; nuggets 0.01-0.84 px on the spot-filter tracks, 2.5-3.0 on PR141's two (IR,
76 points), 5.7 on PR43's streak; **every one of them wanders** (Δln L 56-3,816: none is a line with white jitter, as
the survey found); the line's `uniform` is True on 10 of 45 while the band says the speed varied by 2-10x along most
of them. The line's v_px and the band's average differ most where the track curves (PR144's golden 29 vs 42 px/s;
PR071 2.2 vs 7.3; PR051's release 19 vs 133). PR051's release track: pairs every second frame, so no pair scatter;
the dash's jump gives a nugget of 1.6 px in y and a band of ±150. **`share rerun --strict` was not run**: the reports
of every case change (new rows, the band's words, a new figure), so the strict comparison will list differences until
the case files are remade for 0.4.0, as the recipe says they are at a release ([[reference-case-files-recipe]]).

**Two things the band says that the words had to learn.** (1) The mean acceleration is a vector's change: PR055's
sphere runs 68 -> 80 px/s in speed but its velocity changed by 144 px/s (152° of direction), so the words say "its
velocity changed by ... (so many degrees of direction)" and not "accelerated". (2) The band can be as wide as a pair's
jitter where the wander's range is short (PR071's hand track, 0.6 s: ±13 against ±12): the rate itself changes faster
than one pair can tell, and the honest comparison is against the pair readings' scatter (`pairs_sd_px_per_s`), not the
nugget alone -- the first wording claimed "tighter than one pair" and was wrong on PR071.

### Objective 3 without ADS-B: what survives the missing variables (method §33)

| what | where | tested by |
|---|---|---|
| **the projective constant-velocity test**: a straight image track whose distance from its vanishing point goes as 1/(t_z - t); five parameters (the line, the vanishing point on it, a scale, t_z) by a grid in t_z either side of the track (to 20 track lengths) and least squares; held against constant image speed (4) and a free quadratic (6); passes closing/receding with t_z's residual-bootstrap band, T = t_z - t_last, v ≈ R / T (exact with k and the frame's centre, the secants' ratio), with k the aspect angle ψ from the vanishing point; passes with no closing seen; fails | `projective.fit` (new module), `FAR`, `CLOSING_GAIN`, `QUAD_SLACK` | `test_reduction` (a drawn pinhole track closing: t_z 2.5 found, ψ within 1°, v/R within 10 %; far: no closing; curved: fails); `test_golden` PR43 |
| **the turn radius in body widths**: the sagitta across the principal line, Π_L = 8 D s / L²; did not turn (s within 3 sigma: the radius at least L² / 8 D s_95), a hair off straight (Π_L < HAIR 0.01), a turn; the scale from the kinematic notes (quadcopter 15, pigeon 33, airliner 60, fighter 47-121) | `projective.turn`, `smear`, `said` | a drawn arc of 500 px by a 10-px object -> 48 (50); a straight track -> at least 8,590 |
| **tau** from looming (s = a / (t_z - t), the same grid and bootstrap; d ln s/dt beside it) and from a light curve with the gain taken out by a background aperture; θ = atan(ω τ) | `kinematics.looming_fit`, `tau_from_light_curve`, `aspect_from_tau` | a rendered disc growing as 1/(t_z - t) read by `flicker.extent` in whole pixels (t_z 3.96 for 4.0); a 1/R² light curve under a sinusoidal gain (tau 2.98 for 3.02); without the background the gain leaks in |
| **the admissible region in (R, Rdot)**: the stages' range bounds (a range given; else focus's floor, horizon's and haze's ceilings), a speed cap V_CAP (Mach 3), the size through k and the extent, tau's line; drawn evenly for the 5-95 % of speed, aspect and size, the share under Mach 1, the least (ωR at the floor) and the most | `kinematics.admissible_region`, `admissible_said`, `BOUND_WORDS`; `Case.range_bounds`, `Case.admissible`, `Case.survives`; `figures.admissible`; `<tag>_admissible.png` among the report's figures wherever ω is known | analytic checks (the rim is the cap, a size ceiling cuts R, tau makes it one line, crossed bounds empty); the figures test now expects three where k is known |
| the stage records `projective`, `turn`, `smear`, `width_px` (the size given, else the blur's width, else the spot size the track was followed at: `extent_px`, passed by `run` and `add_known`; `height` for the frame's centre); nothing for a held track; NO POWER "turn" with no width; the summary's rows ("turn radius in body widths", "constant velocity, as a pinhole draws it", "smear"); the bottom line's paragraph "Without a range, a field of view or the platform's speed, the track itself says this. ..." with the region's sentence only where a stage bounds the range | `stages.kinematics(height=, extent_px=)`, `report.summary`, `bottom_line`, `kinematics_cli` | `test_what_survives_reaches_the_stage_and_the_report` |

**PR43 on its case file's 25-point track** (the research repository's note did it on its own 18 detections,
2026-08-05): straight to 1.5 px rms, t_z 3.38 s (3.33-3.45) against the note's 3.34, T 0.91 s against 0.80, the
vanishing point (483, 488) inside the frame against (573, 545), ψ 35° at a 65.6° field read linearly (39° with the
pinhole k `AngularScale.from_fov` gives: 1,489 px/rad) against the note's 33.8; the turn 4.0 ± 0.4 px over 505 px, about
1,870 body widths (the note: > 1,936): a hair off straight -- the first wording called it "a turn, so not inertial
motion" at 9 sigma, which is right arithmetic and wrong words for 4 px on a streak's centroid; the smear 4.75 widths
a frame. The bottom line's paragraph for it is in `try/` (run with an assumed 65.6° field).

**Not built, said in §33:** edge-crossing fits (A16: the frames at the edge); the parallax number (`comotion`'s and
`layers`' to give: valid only over a world-fixed textured background); tau is not fed by any stage (no per-frame size
or brightness series is recorded -- the flicker stage's extent is one number a track), so it reaches a report only
where a caller computes it, and its validation on real objects waits for the Galileo ADS-B data.

### Tests at the end

From a `git archive` snapshot of 4526270 (`/scratch/mcdonald/v04-s7/snap`), one Slurm job a suite (`suites/one.sbatch`),
`MCDONALD_DATA` set, `TMPDIR` on `/scratch/tmp/s7`; logs in `/scratch/mcdonald/v04-s7/suites/logs/`: all 20 pass --
measurement 483, reduction 422 (350 + the band's 41 + what survives' 31), gui 744 (1 skip, the WxAgg backend), camera
134, cli 126, slew 59, audio 54, published 32, zoom 31, share 25, tether 24, horizon 17, waves 14, stabilize 13,
aspect 10, focus 10, sweep 10, haze 9, streak 5, and **golden 133 PASS, 0 SKIP** -- the same 133 as session 5, because
`test_pr43_speed_band` was not yet in `main`'s explicit list (test_golden runs a list, not every `test_`): listed
after the snapshot, it passes 7 of 7 run alone from the checkout (`suites/logs/pr43_band2_*.out`: 11.6-31.4 px/frame
against the Note's 7-33, 3.1 sigma, t_z 3.38 s (3.30-3.44), T 0.91 s, psi 35.0°, vp (483, 488), 1,871 body widths),
and the golden suite from the checkout with it listed is **140 PASS, 0 SKIP** (`suites/logs/ck_test_golden_*.out`, 30b028e). `test_cli` ran again from the checkout after
its `--out` fix (126 PASS: the planted clip's `kinematics` run no longer leaves `planted/` in the cwd). Jacob's own
jobs (`pr062_firstlook`, `pr063_firstlook`, the `propose` arrays, `orbs_test_focus`) ran alongside, untouched; the
golden rerun was submitted niced behind them.

**Left behind:** nothing in `/tmp`; `/scratch/tmp/s7` empty (the suites cleaned up); `/scratch/mcdonald/v04-s7/`
kept (14 MB: the logs, the band table, the three cases' figures in `try/`; the snapshot removed -- it is 4526270); the
frame cache `~/Documents/mcdonald/frames` as session 5 left it (145 folders; nothing extracted this session: every run
was on tracks); the Slurm queue has only Jacob's own jobs. A coverage script ran on the desktop once by mistake
(`tmp/cover.py` in the job's folder, 4 min): everything after it went through srun/sbatch.

### Open, in the order I would take them

1. **The window** (the two audiences): the report card shows the summary's values, so the band's "± e" and "ran from A
   to B" reach it through the pixel-velocity row, and the full report page has the new rows, paragraph and figures; but
   nothing in the window names the speed band or the constant-velocity test in plain words (`window-text-in-plain-words`),
   and the Measure panel's jewels know nothing of them (they are the kinematics stage's, so no new jewel). Jacob's word
   on the wording: "the track itself says this", "a hair off straight", "did not turn", "closing on the camera".
2. **tau from a stage**: a per-frame size series (the `extent` the flicker stage reads on EXTENT_FRAMES frames, read on
   every frame along the track) and the object's and background apertures' curves (`<tag>_flicker.csv` has them) given
   to `looming_fit` / `tau_from_light_curve`, into the kinematics fields (`looming`), the ledger's θ row ("bounded by
   tau": I6) and the admissible region's line. Held on a rendered approaching object through the whole chain. Then the
   Galileo aircraft when the ADS-B data comes (session 5's note on what is on the drive).
3. The ledger, finished (session 3's item 2): the report card, a page or `run` stages for the bounds, R from a range
   ratio; Jacob's word on the wording -- no answer yet.
4. `share rerun --strict` on the 14 case files and the recipe's remake for 0.4.0 (above: every report changes).
5. The new bounds on real clips (session 2's item 4): PR149's ship for `horizon`, PR43's dash for `streak`.
6. The sweep's open items (session 2's item 3).
7. The parallax ladder's nearest height when Long's revision is in; PR043 on hold.
8. `camera --scene` into `run` and the window; `Find`/`Follow` on a saturated bloom (session 5's item 6); `slew` on a
   dial that stalls (session 5's item 7); session 4's item 6.
9. Noted: the projective test's residual bootstrap is along the line only (the across-line error of the line's angle
   is second order); the admissible region's "drawn evenly" is uniform in area, said in the words -- a log-uniform
   prior in R would be the scale-free alternative; `BAND_NMAX` 450 fits the covariance on a long track's middle only.

---

## Session 5 (2026-10-28, night): the released-track null on PR051, against the scene -- and the 9 % shortfall read

Jacob: "see docs/handoff-v04.md". Took session 4's open list in its order: **item 1, both halves**. The released-track
null on PR051 is built (`camera --scene`) and a golden check; the 9 % shortfall of the scene's chain against the data
bar is read (below: it sits between the bar's target grid and everything in the picture, which agrees with itself).
On main, **committed locally, not pushed** (abb8523 the work; nothing pushed or released until 0.4.0). No version
bumped; CHANGELOG's Unreleased has the item. This session's scratch is `/scratch/mcdonald/v04-s6/` (`mov_frames/` the
leak's frames 900-1279 and `look/` the sheets they were read from, `centroid_track.py` the track's maker, `runs/`
the upload's `layers`, the linker, the camera stage, `slew/` and `north/`, `shortfall.py` and `scene_look.py` the
readings, `logs/`, `suites/logs/`, `tests/`, `snap/` the snapshot the suites ran from).

### The null, in the form the clip allows

The MTS-B draws no azimuth readout a `readout` could time, and its north pointer lags in steps (session 2). But the
ground is in the picture, and the ground is the camera's own record: while a camera holds a drifting object the
ground slides through the picture at the object's rate against it, the other way; let go, the object keeps its motion
and crosses the ground at that rate. So `camera --scene LAYERS_CSV` (method §20, the bullet "Against the scene")
takes the track relative to the scene's path (`slew.scene_path` of a `layers` CSV over the same frames, one stretch
at a time), fits the rate steps on that, and reads the camera's rate before the release as the scene's drift over the
frames it held the object (`camera_before`), and after it too; the comparison needs no readout and no scale (one k on
both sides). Added with it: every stretch after the release compared and the first named beside the fastest; the
departure as a whole (`departure`: a line from the release to the track's end or its first jump of more than twice
the object's width) said first, since a jittery centroid cuts a track into many short stretches (PR051's: thirty) and
the null is about the departure, not its pieces; the direction each stretch takes against the one the release would
send it (only where the scene drifted at 2 px/s or more, `BEFORE_MIN`); `--pixel-aspect` (square pixels first).
The FLIR1 readout form and its fields are unchanged (its golden as before).

### What PR051 says (the numbers are in method §20, the test and the commit)

- **Which copy, which frames.** The research repository's case note (`analysis/cases/pr051/pr051_untracked.md`
  §48.3) rules: measure on Corbell's upload, not the Sitrec `.mov` (whose re-export wanders by up to 10 px and
  overstates scene motion). Upload frame = 2 x leak frame + 2140; every frame is doubled and the odd frames carry
  the pictures (checked: even n is a copy of n - 1). The event: the gate holds the object solid to 4437, blinks from
  4438 (the display's own lock-lost flag, the note's §48.1), the object walks out of it from ~4440, the gate goes out
  and the mode drops `RPOINT` for `RATE` at 4546, the dash at 4553-4567, the operator's slew from 4605. Frames
  4200-4700 are in the cache `~/Documents/mcdonald/frames/yt_nKtJslcHlCQ_1080p60_h264/` now, beside 181-860.
- **The scene.** `layers --n0 4201 --n1 4661 --k 2 --step 2 --max-shift 60` with 13 boxes (the data bar's blocks, the
  heading tape, the N, the reticle, the gate, the object's drift path and the dash's corridor; in `runs/up_layers.sbatch`
  and the golden test): held still over 2 frames in 99 % of pairs and still over 60 too; the chain whole 4201-4603
  at 0.3 square px/s before the release and 0.6 after; the operator's slew at 4605-4633 (no consensus) and the two
  big steps at 4637 and 4651. The note's "tracker chasing, unresolved" over the leak's 1105-1169 is nothing: the
  ground held.
- **The track.** `tests/golden/pr051_release_track.csv`, a thresholded intensity-weighted centroid as the note
  measured the released copy (`centroid_track.py`; the overlay, the reticle's arms and the gate's corners blanked;
  a 180-px window that follows, 1240 x 220 along the row for the dash), odd frames 4201-4549 and 4553-4567, the
  header saying so. mcdonald's own linker (`mark --set object@4301=905,545 --set object@4521=768,352 --no-window
  --link`, bright spots 71 px wide) agrees over the drift to a median 0.0 px, MAD 0.5, but does not hold the bloom
  inside the gate's brackets (lost before 4421) nor the dash: a track to keep in mind when Find/Follow meet a
  saturated bloom in a bracket.
- **The result** (`camera --track ... --scene ... --after 4439 --fov 0.080 --pixel-aspect 1.33333 --size 71`; 0.080
  deg = FVW 58.5 m at 22.5 NM across the 4:3 sensor's 1440 square px, k 18000): the camera was not turning against
  the ground while it held the object (0.3 +- 0.0 square px/s); the departure as a whole, 4439-4549 to the dash's jump
  at 4553, crosses the ground at **0.0079 +- 0.0002 deg/s** (143 square px/s, heading 328 deg, up and to the left),
  +43 sigma; the dash's centroid 4561-4567 at 0.11 +- 0.014 deg/s after a jump of 475 px; after the release the scene
  drifts 0.6 px/s. **The release explains neither the drift nor the dash.** Not said by the tool: the range (SLR is the
  ground's), so no speed -- at the ground's 41.7 km the drift would be 5.8 m/s across the line of sight (the note's
  "8 knots" from the released copy's slower read).
- Golden: `test_pr051_released_track_against_the_scene` (8 checks, ~3 min: `layers` then the stage from the cache).

### The 9 % shortfall, read (`shortfall.py`; session 4's chain `v04-s5/runs/s5_pr051`, session 2's `truth.npz`)

The chain over 5.0-13.5 s is 0.913 of the bar's expected path at a pixel aspect of 4/3 (0.932 over 5.0-9.5), and by
thirds 0.94, 0.90, 0.89: it falls further behind along the window. Three readings:

1. **Not the timing.** The bar's path read at t +- 0.25 or 0.5 s moves the ratio by under 2 % (0.896-0.913); the
   picture's frames shifted by a quarter second either way, 0.887-0.920. A steady rate does not care where the clock
   sits.
2. **The aspect, in part.** At 1.30 (what the pointer-convention fit preferred for this framing, gain held at 1) the
   ratio is 0.936; at 1.25, 0.974. Two to three points of the nine.
3. **The picture agrees with itself; the bar does not agree with the picture.** The pointer (the a1b and a1 series,
   square px at 4/3) turns at 0.260 deg/s over 4.5-14 s against the bar's azimuth rate (ACFT to TGT A) of 0.273:
   0.953 of it (0.977 at an aspect of 1.30). The scene over the pointer with the hold out -- `slew`'s own quantity --
   gives **c = 2160 px/deg at 4/3 and 2140 at 1.30, against the truth 2230: 3-4 % under**; the scene over the bar's
   azimuth gives 2020 (9 % under). So the pointer and the scene say the line of sight turned 0.253-0.260 deg/s and
   the bar's grid says 0.273: the TGT A solution marches 5-9 % faster across the line of sight than the sensor's own
   azimuth as drawn and than the ground in the picture (the same solution that coasts stale in the 4X stretch, the
   note's §46.1). What is left over after the aspect is the bar's, not the chain's, and the data bar's expected path
   should be quoted as "the bar's grid" with that caveat; the golden check's 10 % / 15 % tolerances stand.

`slew --hold-rate 0.074` on the whole chain (`runs/slew.sbatch`): with the pointer read every second frame (the a1b/a1
series, `--step 2`) and the chain at k 2, the pointer smoothed with the chain's kernel never covers 0.6 of it
(`MIN_COVER`: half, every frame) and every window has 0 samples -- the series must be read every frame for a k-2
chain. A `symbology --method template --step 1` over 271-841 was run (`runs/north/`) and `slew` tried again on it:
with the hold given, **7-14 s claims c = 2843 px/deg (16-84 % 1969-2855; the forward fit 2112; the truth 2230
inside the band, the point a quarter high) with the pointer's rate and the scene's at r 0.05** -- the lag: the dial's
turn over the window is the slew's, its rate is not; 4.5-14 and 5-13.5 s are refused (the slopes 38-45 % apart, the
bootstrap +-29-32 %); without the hold every window is NO POWER (c at least 324-362). The rates gate (r 0.5, method
§17) would refuse 7-14 s, and I tried applying it with the hold given too -- but a steady pan, which `--hold-rate` is
for, has no rates to correlate, and `test_slew`'s "the hold given: c comes back" fails under it (c None against 2200):
reverted, nothing committed of it, noted in method §17 as known and open. The pointer read every frame at `--min-ncc
0.5` solves 515 of 571 (411 kept by `clean_pointer`; at the default 0.7, 126). So PR051 still gives no k from its
slew, and the reason is now exact: a dial that stalls beyond its grid. The test to add is for that stall.

### Tests at the end

From a `git archive` snapshot of abb8523 (`/scratch/mcdonald/v04-s6/snap`), one Slurm job a suite, `MCDONALD_DATA`
set, `TMPDIR` on `/scratch/tmp/s6`; logs in `/scratch/mcdonald/v04-s6/suites/logs/`: all 20 pass -- measurement 483,
reduction 350, gui 744 (1 skip, the WxAgg backend), camera 134 (103 + the scene test's 31), cli 126, camera's golden
below, slew 59, audio 54, published 32, zoom 31, share 25, tether 24, horizon 17, waves 14, stabilize 13, aspect 10,
focus 10, sweep 10, haze 9, streak 5, and **golden 133 PASS, 0 SKIP** (125 + PR051's released track's 8). The
`slew` gate that was tried and reverted (above) never entered the snapshot; `test_slew` on the checkout with it
failed one check, without it the suite is the snapshot's.

**Left behind:** nothing in `/tmp`; the suites' temporary folders on `/scratch/tmp/s6` removed; `/scratch/mcdonald/
v04-s6/` kept (the snapshot removed -- it is abb8523); the frame cache has the upload's 4200-4700 now; the Slurm queue
is empty of mine.

### Open, in the order Jacob chose (2026-10-28, after session 5)

Jacob, 2026-10-28: 0.4.0 is about half way, the k half done and objective 3 untouched. **Next: objectives 3 and 4**
("what survives the missing variables" and "a speed with a band for every track"), in a new session, starting now
without ADS-B: **he has asked the Galileo Project for the ADS-B data and does not have it yet**, so the validation of
tau and the aspect on Galileo aircraft is the last step, slotted in when it arrives. **PR043 and the parallax ladder's
fix are on hold until N. Long has finished revising his homography** (the row stays "to do, for 0.4.0").

1. **Objective 4 first, then 3 -- my suggested order, since 4 is self-contained and 3's figure wants its band**
   (Jacob's words were "3 and 4"; a word from him reorders it).
   - **The speed band (K1; ROADMAP row 762):** v(t) with a band from the track's own covariance -- a Matérn-3/2 kernel
     with a nugget for the centroid's jitter, fitted by REML, the instantaneous velocity kriged from it; the average
     speed's honest error; acceleration as a likelihood ratio, not a refusal; non-uniform motion described, not
     averaged. The survey that tested it on the recorded tracks is `~/research/uap/analysis/methods/
     kriging_methods_survey.md` ("The answer, first", §1.1-1.2, §3.1, §6 Ranked ports; its scripts and results in
     `kriging_survey/` beside it): the kriged velocity up to 13x tighter than frame differences (median 8x; under 3x
     on PR23 and two others), the nugget 0.1-1.5 px, the hole effect of a wingbeat in the position (§1.5). K9's pair
     errors are the weights. Where: `kinematics` (`fit_v_px` is already universal kriging with a pure nugget) and
     `report`; scipy is enough (PyKrige is in the user site, not a dependency). Tracks to hold it on: `tests/golden/
     *_track.csv`, the 14 reference case files in `/models/data/mcdonald/cases/` (22 objects).
   - **Planted tracks with the measured covariance (K8; row 763):** conditional simulation as the validation -- the
     band's coverage on tracks drawn from the fitted covariance, with and without a planted acceleration; the
     likelihood ratio's false-alarm rate from them. In `tests/`.
   - **Objective 3 without ADS-B** (rows 758-761, 765; I6 at 767): (a) the dimensionless numbers as report facts --
     the turn radius in body widths (the track's curvature over the object's width, no range; neither PR43's nor
     PR113's object turned), the smear number (`streak`), the obliquity from the vanishing point, the parallax number
     (`comotion`); (b) the projective constant-velocity test (a straight image track whose distance from the vanishing
     point goes as 1/(t_z - t)); (c) the admissible region in (R, Rdot) with the speed and size distributions it
     implies, the Technical Note's fan as the standard figure of a case, fed by the bounds the four commands and the
     ledger already give; (d) edge-crossing fits and the time-distance diagram; (e) tau from looming (angular size over
     its rate) or the light curve (d ln F/dt = -2 Rdot/R, the gain out), theta = atan(omega tau), built and held on
     drawn scenes (a rendered approaching object) and on any reference case that looms -- **its validation on Galileo
     aircraft waits for the ADS-B data**.
   - What is on the drive for the aircraft when the data comes: the Dalek clips in `/models/data/galileo_project/
     IR-Dalek-Hideout/` (153 clips, 33 GB; the five bird flyers were cut from them) and `IR-Dalek-Sphere/` (2); the
     0.5 controls name "the Galileo airliners" among 21 infrared aircraft with known answers (`~/research/uap/galileo/`
     has the bird work's scripts, no README) -- find which clips hold them and match the ADS-B (range, speed, heading,
     altitude against the camera's clock); no ADS-B file is on the machine today.
2. **The ledger, finished** (session 3's item 2): the window's report card, a page or `run` stages for the bounds, R
   from a range ratio, theta bounded by tau (I6); Jacob's word on the wording (session 2) -- no answer yet.
3. The new bounds on real clips (session 2's item 4): PR149's ship for `horizon`, PR43's dash for `streak`.
4. The sweep's open items (session 2's item 3): the small zoom ratios and PR101's claim, before either is quoted.
5. The speed band (K1, K8); the parallax ladder's nearest height when Long's revision is in.
6. `camera --scene` into `run` (a case whose `layers` CSV is there, with `--after` as a known quantity) and the window
   -- the two audiences; and `Find`/`Follow` on a saturated bloom inside a bracket (above).
7. **`slew` on a dial that stalls** (above): a test for a pointer that holds still beyond its grid's step and catches
   up, so a known-hold claim from the totals is refused where the rates do not follow -- without gating a steady pan.
8. Noted, not done: session 4's item 6 (a sharp template wrong by a bump, `still_score` unused, the vote's cluster
   tolerance); a `layers` pair held still is zero in the path, so the capture's jitter stays in a track (method §20,
   how it fails).

---

## Session 4 (2026-10-28, evening): PR051's 10-13 s read and fixed -- the chain whole over 4.5-13.5 s

Jacob: "see: docs/handoff-v04.md". Took session 3's open list in its order: **item 1, PR051's 10-13 s, read and
fixed**; the released-track null (its second half) not started. On main, **committed locally, not pushed** (82f6c13;
nothing pushed or released until 0.4.0). No version bumped; CHANGELOG's Unreleased has four new items. This session's
scratch is `/scratch/mcdonald/v04-s5/` (`none_probe.py` with its five readings in `logs/`, `masked_probe.py`,
`mask_diag.py`, `own_shift_chain.py`, `compare.py`, `cmp_pr135.py`, `runs/` PR051 and PR135 with the new code
(`s5a_*` a first try before `moved` counted the templates placed), `look/` crops, `suites/logs/`, `tests/`).

### What the no-consensus pairs' fields said

Thirty pairs over 9.4-13.3 s had no consensus (24 held and measured again over 60, 6 moved). Their fields
(`none_probe.py fields`, `masked_probe.py`, `vote`; the probe reads the frame cache `~/Documents/mcdonald/frames`)
were three things, none of them K9's, and a fourth turned up on the way:

1. **The masks took half the picture.** With `layers`' own masks each pair kept 14-29 templates of the 66-85 the
   boxes alone leave, the sharp ones first. The static mask (18.6 %) was all chroma -- the static-and-sharp share is
   0.000 on this clip -- and each frame's own chroma mask added the rest (48 % of frame 603 masked). The upload's
   bright terrain (grey over 120, a fifth of the frame) carries a colour tint of 46-54 DN in 60-84 % of its pixels:
   18.7 % of the frame cast, just under the fifth that calls a clip colour. Interlace was ruled out (`comb`: the odd
   and even lines of every frame agree within 0.2 px).
2. **The holds jitter.** A repeated capture reads 0.5-1.9 px from the last (a hold's own field: 74-80 of ~80
   templates in one group), and `AT_ZERO` 0.5 sent eleven of them to a second pass over 60 frames, where a scene
   moving 600 px has no match.
3. **The big steps have no sharp templates.** Catch-ups of 70-140 px along the streaks (603, 611, 621, 639, 653 and
   their like) leave 0-2 templates sure both ways and 60+ sure only across; the zero-allowed fallback then found a
   false near-zero group (3-5 sharp at zero plus the streaks' self-match, 16 of 79 members) and the pair was "held".
   The ridge templates' own argmaxes cluster: the largest cluster 26 against the next 13 (603), 22 against 9 (611),
   28 against 9 (639), 32 against 10 (653) -- leads of 2.0-3.4 sigma of a split vote -- within 1-4 px of the sharp
   templates where there are any, and the mean correlation map over all templates (`global`) agrees to within its
   own 10-px breadth.
4. **Zero allowed on a moving streaky pair blends.** A same-position ZNCC of 0.9 or more (the old "held still")
   holds through a 15-35 px step along the streaks, and the zero-allowed field then splits between the streaks'
   self-match at zero and the step: the sure route blended them (615-617: a group of 7.1 px, n 67, for a step of
   18; 629: 4.1 px) and the vote would have picked zero (629: 49 against 29). Only the zero-left-out field is clean
   there (18.08, n 56), and on a true hold that field keeps 0-6 templates (the peaks sit on the zone's rim).

### What was built (82f6c13)

| what | where | tested by |
|---|---|---|
| **a tint is not symbology**: `tinted` where most of the brightest fifth of the sampled frames carries a cast; no chroma mask then, static-and-sharp kept; the flag travels with the masks to every worker | `forensics.static_masks` (`TINT_FIFTH`, `TINT_SHARE`), `frame_mask`; the slimmed mask dicts in `layers`, `integrity`, `autolink`, `groups`, `static_pattern`; method §3 | `test_measurement` (`test_a_redaction_block...`: a tinted drawn picture with a white glyph, a green gate on the same picture) |
| **both fields from one search**, the zero-left-out one read first wherever a fifth of the templates placed are sure or it has a consensus (`moved`); `second_pass` the same in one round; `still_score` no longer consulted (kept, unused) | `forensics.shift_field(zeros=)`, `_peak`, `moved`, `shift_field_auto`; `layers._again_part`, `second_pass`, `_window` | the held-still tests as before; PR135 to the bit |
| **the vote along the streaks** where fewer than three templates are sure both ways: the largest cluster of every template's shift, leading the next cluster a ridge's length away by `VOTE_LEAD` 2 sigmas; ridge members carry along-information equal to the cluster's scatter (>= `VOTE_FLOOR_PX`), the group's error along floored at it | `forensics.consensus`, `_vote`, `_ridge_axes`; method §31 | `test_measurement` K9 test (drawn streaks with no sharp patch: +/-1.0 along; split 13 px: none) |
| **a hold unmoved inside the zero zone** (`AT_ZERO` 4 px) with nearly every template in one group (`REPEAT_SHARE` 0.8) | `layers.repeating` | the repeat test (1.5-px holds unmoved; 8 of 38 at zero not) |
| the golden check through 13.5 s: `layers` 301-811, nearly every pair measured, 5.0-9.5 s within 10 %, 5.0-13.5 s within 15 % | `tests/test_golden.py` (`test_pr051_scene_path_against_the_data_bar`, ~6 min now) | golden |

**What changed on real clips:** PR135 150-305's layers CSV is the same to the bit (151 pairs, errors 0.007 px).
PR051 (`--k 2 --step 2`, the boxes; `runs/s5_pr051`, `compare.py`): every pair over 4.5-13.5 s has a consensus
(49 % steps, 67 % unmoved, 2 steps bridged where 126 were; `held still ... 69 %` in the stage's line), the new
run's steps within 1 px of the probe's readings pair by pair, and the chain whole in one stretch over 4.5-13.5 s --
at **0.93 of the data bar over 5.0-9.5 s and 0.91 through 13.5 s** (`own_shift_chain.py`: with the unmoved pairs at
their own shift instead of zero, 0.94 and 0.89-0.92: the holds' creep, median +0.2 px, is 1 % of it). Session 3's
0.94-0.95 over 5.0-9.5 s was a broken chain bridged at its neighbours' rate, which over-counts inside a hold (the
`s5a` run, bridged 46, read 1.03 over the whole). **The shortfall is now steady, not lost steps**, and its cause is
open: the bar's half-second readings scatter from 0.57 to 1.43 of the chain (digits read by eye), the line of sight
is taken at a fixed 7 deg true, and the first half second (4.5-5.0 s) has 17 px of motion in the picture against
242 in the bar -- the picture against the data bar's own timing (the overlay's clock and the imagery may not be
synchronous in this upload). To look at: the ACFT/TGT readings against the pointer's own azimuth, and the bar's
expected path with the timing shifted by a hold.

**Tests at the end** (d4a14c8 -- 82f6c13 the work, c610121 and d4a14c8 two test fixes found by the suites: a hand-made
masks dict without `tinted` crashed `autolink`'s workers, the PR051 check had counted every frame row as a pair, and
the K9 test's drawn streaks gave 2 sure templates in the full suite's RNG order where the sure route needs 3 -- they
are drawn from a generator of their own now, seed 2, 5 sure). From a `git archive` snapshot, one Slurm job a suite,
`MCDONALD_DATA` set; logs in `/scratch/mcdonald/v04-s5/suites/logs/` (`test_measurement3.out` the final measurement
run, `golden_pr051.out` the PR051 check rerun alone after the fix): all 20 pass -- measurement 483 (477 + the tint's
3, the holds' 2, the vote's 1), reduction 350, gui 744 (1 skip, the WxAgg backend), cli 126, camera 114, slew 59,
audio 54, published 32, zoom 31, share 25, tether 24, horizon 17, waves 14, stabilize 13, aspect 10, focus 10,
sweep 10, haze 9, streak 5, and **golden 125 PASS, 0 SKIP** (118 + PR051's scene path's 7: nearly every pair
measured, both windows whole, 0.932 and 0.913 of the bar, the path's error +/-5 and +/-10 square px).

**Left behind:** nothing in `/tmp`; the suites' temporary folders on `/scratch/tmp/s5` removed; `/scratch/mcdonald/
v04-s5/` kept (the probes and their readings, the runs, the logs; the snapshot removed -- it is d4a14c8); the frame
caches as session 3 left them, plus the new `layers` cache in `v04-s3/pr051_wd` (`bg_layers_k2_s2_271_841_fc8902e095.npz`,
the new rules' key). The Slurm queue is empty of mine.

### Open, in the order I would take them

1. **The released-track null on PR051** (session 1's item 3): the scene through the leak's breaklock, now that the
   chain holds through catch-up steps of any size. And the 9 % shortfall above, read against the bar's timing
   before `slew --hold-rate` is tried again on 7-14 s (the pointer's lag, session 2, stands).
2. **The ledger, finished** (session 3's item 2): the window's report card, a page or `run` stages for the bounds, R
   from a range ratio, theta bounded by tau (I6); Jacob's word on the wording (session 2) -- no answer yet.
3. The sweep's open items (session 2's item 3).
4. The new bounds on real clips (session 2's item 4).
5. The speed band (K1, K8), objectives 3 and 5, the parallax ladder's nearest height (session 2's item 5).
6. Noted, not done: a sharp template wrong by a bump on its ridge (§31); `still_score` unused; the vote's cluster
   tolerance (6 px) against a 13-px period leaves votes between modes in no cluster -- fine while the lead is
   measured, a thing to know if a clip's period is nearer 12.

---

## Session 3 (2026-10-28, afternoon): K9 built, PR051's scene path a golden check

Jacob: "see docs/handoff-v04.md". Took session 2's open list in its order: **item 1, K9, is built and checked**, and
PR051's scene path against the data bar is a golden check. On main, **committed locally, not pushed** (nothing pushed
or released until 0.4.0). No version bumped; CHANGELOG's Unreleased has the item. This session's scratch is
`/scratch/mcdonald/v04-s4/` (`probe/` the peak probe and its three readings, `runs/` PR051 and PR135 with the new code,
`suites/`, `tests/`); `/scratch` is the new drive (session 2's note holds: every older path is gone).

### What was done

| what | where | tested by |
|---|---|---|
| **each template's own error** from its peak's curvature (`SHIFT_COLS` + `wxx wyy wxy ridge`): the least-squares covariance 2(1-pk)/N K^-1, scaled 3.5x in sigma (drawn textures) with a 0.02-px floor, kept as the information matrix | `forensics.peak_information`, `PEAK_ERR_SCALE`, `PEAK_FLOOR_PX`; method §31 | `test_measurement` (`test_each_template_weighed_by_its_own_error`, 8 checks) |
| **a template sure only across its ridge**: runner-up within `good`'s gap -> information across the line to it alone, `ridge` = the runner-up's distance; `ridged` picks them; in `consensus` they are members across their ridge (within the tolerance) and along it within ridge + tolerance, count towards the 8, fix nothing along; 3 sure both ways needed; a shift unconstrained along some line is none | `forensics.ridged`, `consensus(w=, ridge=)`, `layers_of` | the same test (36 of 40 drawn-streak templates ridged, 4 sure: found; no sharp patch: none) |
| **the weighted shift**: GLS over the group by each member's information, scaled to the members' pull (>= 1), Huber 2.5; the covariance | `forensics.weighted_shift` | the same (rigid +/-0.004 px; half the templates 1.5 px off: +/-0.12) |
| the pair's error in the layers CSV (`err_x_px`, `err_y_px`), `shift_error_px` in the fields and `said`; an unmoved pair keeps its own field's covariance; the cache key has the rule | `layers.measure` | end to end in the same test |
| the chain weighs each step's pairs by their errors and carries the path's own (6th value with `err=`); `read_layers(errors=True)`; each slew window's `scene_path_err_px` | `slew.read_layers`, `scene_path`, `series`, `measure` | the same test's chain check; `test_slew` 59 |
| `comotion.local_flow`: the annulus's weighted mean where within 3 px of the median, `err` beside `sd` | `comotion.local_flow` | -- (no golden; the median kept where they disagree) |
| **PR051's scene path against the data bar**, 5.0-9.5 s: one stretch, 1740 against 1848 square px (x0.942), the path's own error +/-7 | `tests/test_golden.py` (`test_pr051_scene_path_against_the_data_bar`, ~3 min: `layers` 301-571 `--k 2 --step 2` with the 13 boxes, chained in square px against TGT A's motion across the line of sight computed from `pr051_databar_track.csv` in the test) | golden |
| the second pass's L-frame shifts scaled consistently (information by (L/k)^2, the ridge by k/L) | `forensics.scaled_shifts`; `layers._again`, `second_pass` | `test_measurement`'s held-still tests as before |

**The probe that fixed the numbers** (`/scratch/mcdonald/v04-s4/probe/peak_probe.py`, `probe_*.out`): on drawn
textures with white noise in both frames the curvature's least-squares error understates the residual by 3.5 in sigma
at every noise level (band-passed pixels are not independent), and the parabola alone is 0.02 px at zero noise; on
PR135's held pairs (a real scene) the templates scatter nine times the prediction (0.05-0.16 px over 5 frames), hence
the group's pull scaling; on PR051's pairs 55 of 69 templates have their runner-up at (+/-13, 0) -- 13 px along the
streaks, just outside the 12-px zone -- at the peak's own height, their dx scattering 96-110 where the sharp ones
(gap 0.08-0.16) agree within a pixel: that is what "counted across its streaks" means in numbers.

**What changed on real clips:** PR135 150-305's layers CSV differs by at most 0.02 px a pair (members up by 1-4 where
ridge templates joined, errors 0.007 px); PR144's goldens are as they were; PR051 (`--k 2 --step 2`, the boxes): 37 % of
pairs with a consensus (12 % before), 53 % of pairs unmoved between catch-ups (16 %: more pairs reach a consensus, so
more windows qualify as repeating), the whole scene 520 px/s median in 186 windows (344 in 42), the chain in one
stretch over 5.0-9.5 s at 95 % of the bar (`compare.py` in `v04-s4/`), then at half the bar's rate over 10-13 s.

**Tests at the end** (f7f7fad, from a `git archive` snapshot, one Slurm job a suite, `MCDONALD_DATA` set; logs in
`/scratch/mcdonald/v04-s4/suites/logs/final/`): all 20 pass -- measurement 477 (469 + the new test's 8), reduction
350, gui 744 (1 skip, the WxAgg backend), cli 126, camera 114, slew 59, audio 54, published 32, zoom 31, share 25,
tether 24, horizon 17, waves 14, stabilize 13, aspect 10, focus 10, sweep 10, haze 9, streak 5, and **golden 121
PASS, 0 SKIP** (118 + PR051's scene path's 3; peak 3.9 GB at 4 CPUs). The same three suites passed on the checkout
before the commit (golden 118 then, before the new test was added).

**Left behind:** nothing in `/tmp`; the suites' temporary folders on `/scratch/tmp` removed; `/scratch/mcdonald/v04-s4/`
kept (the probe, the runs, the logs; the snapshot removed -- it is f7f7fad); the frame caches as session 3 left them
(`v04-s3/pr051_wd`, `v04-s3/pr135_frames`, `~/Documents/mcdonald/frames`). The Slurm queue has only Jacob's own
arrays (`regime`, `orb_sweep`), untouched.

### Open, in the order I would take them

1. **PR051's 10-13 s.** Every other catch-up step there has no consensus at all (`over_frames` 60 in the CSV: held
   over 2, measured again over 60, none) -- `v04-s4/runs/k9_pr051/` has the CSV, the cache
   `/scratch/mcdonald/v04-s3/pr051_wd/bg_layers_k2_s2_271_841_*.npz` the templates: read those pairs' fields (the
   probe's `show_pair` does it). Then the released-track null (session 1's item 3), which needs the scene through the
   breaklock.
2. **The ledger, finished** (session 2's item 2): the window's report card, a page or `run` stages for the bounds, R
   from a range ratio, θ bounded by τ (I6); Jacob's word on the wording (session 2, below) -- no answer yet.
3. The sweep's open items (session 2's item 3).
4. The new bounds on real clips (session 2's item 4).
5. The speed band (K1, K8) -- K9's pair errors are the weights it wanted; then objectives 3 and 5; the parallax
   ladder's nearest height (session 2's item 5).
6. A sharp template wrong by a bump on its ridge (PR051 439-441: two of the 13 "good" read 77 and 89 against 108)
   is caught only by the group's tolerance and the Huber weight, not by its own error; fine for now, noted in §31.

---

## Session 2 (2026-10-28): where things stand

Jacob: "Keep going with the next 0.4.0 session handoff". Worked from session 1's "Open" list, in its order. On main,
**committed locally, not pushed** (Jacob, 2026-10-27: nothing pushed or released until 0.4.0): fd88370 (the code and
its docs) and the handoff commit after it. No version bumped; CHANGELOG's Unreleased has the new items.

**First, before anything else: `/scratch` is a new, empty drive.** The 3.6-TB scratch disk was taken out on
2026-10-27 (its `/etc/fstab` line is marked `#REMOVED-2026-10-27#`) and a 1.8-TB one mounted at `/scratch` on
2026-10-28, empty. **Every `/scratch/...` path in session 1 below, in the older handoffs and in the memory notes is
gone**: session 1's PR051 runs and its 12 hand-drawn overlay boxes (`/scratch/mcdonald/pr051-2026-10-27/`), its suite
logs (`v04-dev/`), the sweep's list and results (`pointer-sweep-2026-10-27/`, `out_v04/summary.md`), and older
recipes (the reference case files' `cases-2026-10-16/18`, the flicker controls, the censuses). What survived is on
`/hugespace` (the slew chains in `/hugespace/local/tmp/slew/`, the frame cache `~/Documents/mcdonald/frames`) and in
`/models/data/mcdonald`. This session's work is in `/scratch/mcdonald/v04-s2/` on the new drive: `diag/` (PR051's
scripts and readings), `seq*/` (frame sequences, symlinks), `sweep/` (the re-run), `suites/` (the test logs).

### What was done

| what | where | tested by |
|---|---|---|
| PR051's pointer and picture, frame by frame, against the data bar read every 0.5 s (below) | `/models/data/mcdonald/pr051/pr051_databar_track.csv` (README, SHA256SUMS); scripts in `/scratch/mcdonald/v04-s2/diag/` | -- (a finding; no code changed) |
| **the four unknowns** on every report (objective 6, first form): k, R, θ, v_own -- constrained, assumed, bounded or missing, the route, and the datum that would close each; in the JSON as `ledger` | `report.Case.ledger`, `_ledger`, `LEDGER_CLOSES` | `test_reduction` (`test_the_four_unknowns_say_where_each_stands`) |
| `--case CASE_JSON` on `horizon`, `haze`, `focus`, `slew`: the measurement recorded in a case `run` made, its report written again with the bound in the table | `report.into_case`, `case_option`, `command_line` | `test_reduction` (the round trip through a written case) |
| PR43's streak read (item 4) | `/scratch/mcdonald/v04-s2/pr43/` | -- (a reading) |
| the pointer sweep re-run with session 1's code (item 2; its results had gone with `/scratch`) | `/scratch/mcdonald/v04-s2/sweep/` (`list.tsv` rebuilt from the uap `clips.csv`), copied to `/hugespace/local/tmp/slew/sweep/pass5/`; pass 5 written into the uap `analysis/corpus/pointer_sweep/README.md` (uap 336273c, those two files only) | the same counts as session 1 to the burst: 95 measured steps of 573, the x2.00 / x5.9 ladder, PR27 267 -> 517 and PR057a 276 -> 584 (both agreeing with their imaged x2), PR134 205, PR101 141 |

**Tests at the end** (fd88370, from a `git archive` snapshot, one Slurm job a suite, `MCDONALD_DATA` set; logs in `/scratch/mcdonald/v04-s2/suites/logs/`): all 20 pass -- measurement 461, reduction 350, gui 744 (1 skip, the WxAgg backend), cli 126, camera 114, slew 59, audio 54, published 32, zoom 31, share 25, tether 24, horizon 17, waves 14, stabilize 13, aspect 10, focus 10, sweep 10, haze 9, streak 5, and **golden 118 PASS, 0 SKIP** (peak 4.3 GB at 4 CPUs, 19 min).

**Left behind:** nothing in `/tmp`; the suites' temporary folders on `/scratch/tmp` removed; `/scratch/mcdonald/v04-s2/` (39 MB) kept; the frame cache `~/Documents/mcdonald/frames` as session 1 left it (the upload's frames 181-860; every run of this session read it or used its own work directory). The Slurm queue is empty.

### PR051: why its slew gives no k, read against the data bar

Session 1 left PR051's NAR stretch at NO POWER with the pointer's rate and the scene's anti-correlated, and asked
first for "the pointer's own steps against the picture's jumps, frame by frame". Done, on the cached frames 181-860
of Corbell's upload (`diag/framewise.py`, `jumps.py`, `isox.py`, `truth.py`, `rebuild.py`), and then against the data
bar itself: the aircraft's position (ACFT, 0.1") and TGT A's grid (MGRS, 1 m) read every 0.5 s over 3-14 s give the
line of sight's true azimuth (grid convergence -1.11°) and the scene's expected path (TGT A's motion across the line
of sight over FVW, times 1440 square px).

- **The picture repeats and catches up.** Every frame is doubled (59.94 over 29.97), and beyond that the content is
  often the same picture again with new capture noise (a zero shift to 0.05 px), then moves on by 10-110 px; at other
  times it moves a few pixels every unique frame. The whole capture also jitters by a few pixels a line (analog
  timebase), overlay and all.
- **The pointer is a dial drawn in steps that lags.** Over 4.5-14 s the bar's azimuth turns 2.55° and the pointer
  2.23°; the pointer holds still for up to 2 s while the azimuth moves 0.6°, then catches up in 0.2-0.5° steps
  (one step of the display's grid is about 0.35-0.4° at its radius in the 4:3 picture). Against the bar it is off by
  0.17° rms, 0.11° rebuilt straight between its steps: a stall is not a grid, so no rebuild recovers it. Its mean
  rate is right (0.25-0.26°/s against the bar's 0.26), as the 80-s convention check found (gain 0.965).
- **So `slew`'s NO POWER is right, and the anti-correlation is the lag**: the scene moves on (the bar says 445 square
  px/s; the aircraft gives the hold, 0.074°/s, near session 1's 0.068) while the pointer sits still, then the pointer
  jumps while the scene does not. Over NAR's 11 s the pointer's swing beyond a steady rate is about one of its steps.
- **The scene can be measured, and `layers` does not yet.** With zero shift allowed on unique pairs, `shift_field`'s
  striated templates (the terrain is streaks) measure each step (frames 439-441: 108 px, 9 templates agreeing, against
  phase correlation's 110 and TGT A's 99 -- and the picture by eye). But where a step has no consensus (22 of 329
  unique pairs, most in 9.5-11 s), bridging at the neighbours' velocity loses the jump, and the path came to 2,793
  of the bar's 4,145 square px over 4.5-14 s (83 % of the bar where it measured). `layers` itself, on a sequence of
  the content changes alone, still called 81 % of pairs held still.
- What it does not give: c from the totals with the hold given came out 1,600-1,900 px/deg against the truth 2,230,
  and frame by frame 1,000-1,600 -- neither a measurement; no claim was made.

The data-bar track is now reference data, the known answer for any scene measurement on this stretch (its expected
path is 445 square px/s over 4.5-14 s) and for the pointer's path.

### The four unknowns (objective 6), as built

`Case.ledger()` writes from the stages' fields, as `summary()` does: k from `scale` (constrained, or "assumed" where
`scale` says ASSUMED -- every `--fov` without `--fields`), else from `slew` (constrained with a depression given;
bounded by c; bounded by a floor only where `floor_stands`); R given, else bounded by `horizon`'s `range_max_m`,
`haze`'s `bound_m` (to its factor of four) and `focus`'s `floor_m`; θ given or from a range rate; v_own given (the
parallax inputs). The markdown's "## The four unknowns" sits after "## Summary of variables" and before "## Missing
quantities"; the window's report page shows the full report, so it reaches the window too, but the report card
(`report_qt._fill`) shows only the summary's values, and the four bound commands have no page in the window: both are
open (two audiences).

### Later the same day: repeated frames in `layers` (Jacob's decision)

Jacob, 2026-10-28, on my recommendation (tell repeats from a slow scene before measuring a held pair again; a census of
repeated frames first, as `integrity` takes one): **"Go with your recommendation on repeated frames in layers."** Built
on a branch in a worktree (`v04-repeats`, b8b54f1, fast-forwarded into main after the suites), because the probes ran from
the main checkout. What it became, and why not the census first:

- **A per-pair sub-pixel test cannot be the rule.** A one-step Lucas-Kanade shift, tile by tile
  (`/scratch/mcdonald/v04-s3/lk_probe.py`, `lk_probe.txt`), reads PR051's true holds at 0.04-0.09 px (z 2-5) and PR135's
  island, which moved 1.6 px in those 5 frames, at 0.04-0.07 (z 2-4): its fixed pattern swallows the drift. And
  `forensics.repeats` finds exact copies only; PR051's holds are new captures of the same picture, noise in every pixel.
- **The order of the pairs can.** `layers.repeating`: in a window where the held pairs and the catch-ups (12 px or more
  over k frames) alternate four times or more, with under a third of the pairs in between, a held pair whose own field
  (zero allowed) agrees on zero is UNMOVED -- zero, not measured again. With it, `held_but_moved`: a pair called held
  whose own field agrees on more than 5 px moved and keeps that (a streaky scene moving along its streaks keeps its
  same-place correlation high; PR051's 439-441 step was found, 108 px, and thrown away).
- **Checked**: `test_measurement`'s new test (drawn sequences; end to end on a lossless repeating picture: 204 px of 210,
  312 without the rule); PR135 150-305's layers CSV byte-identical before and after; PR051's NAR stretch with whole-frame
  pairs (`--k 2 --step 2 --max-shift 100`): a consensus in 12 % of pairs (5 % before), 16 % unmoved, the chain whole over
  5-7 s at 71 % of the data bar's motion, then broken again (runs in `/scratch/mcdonald/v04-s3/runs/`, `compare.py`).
- **What PR051 now waits on is templates, not repeats**: on its streaky terrain most pairs have 4-8 good templates, under
  the 8 a consensus needs (my scratch run that tracked the bar asked for 4). The floor protects every clip and was not
  lowered; K9 -- each template weighed by its own error, a striated one counted across its streaks -- is the way.
  So the golden check of PR051's scene path against the data bar waits for K9.
- **Tests** (b8b54f1 from a snapshot, one Slurm job a suite, logs `/scratch/mcdonald/v04-s3/suites/logs/`): all 20 pass,
  measurement 469 (461 + the new test's 8), golden 118 PASS 0 SKIP, the rest as in the morning.

**The ledger's words, put to Jacob the same day** (he asked which to look at): the status words (constrained / assumed
/ bounded / missing -- "constrained" covers measured and given; "known" is the plain alternative), the column headers
("where it stands", "by", "what would close it"), the "what would close it" texts (FVW / SLR, "range rate", "track" --
the most technical; the window shows the full report), the section's title and place (after the summary of variables),
and the bounded rows (a slew's c as "at least ... px/deg"; two range bounds in one cell). No answer yet.

### Open, in the order I would take them

1. **K9**, layers' per-template error from its peak's curvature (`shift_field` already computes kxx, kyy, kxy and keeps
   only their ratio and axis): a 2x2 covariance a template, a weighted consensus, a pair's error in the CSV, weights in
   `slew`. PR051 is now the reason in numbers: its pairs have 4-8 good templates, mostly striated, under the
   consensus's 8; then PR051's scene path against `pr051_databar_track.csv` as a golden check (it needs no pointer).
2. **The ledger, finished**: the window (the report card; a page for the bounds or `run` stages for them), R from a
   range ratio, θ bounded by τ (I6) when it comes; and Jacob's word on its wording (above).
3. The sweep's open items (session 1's item 2; pass 5 is now written): look at the scatter of small ratios (x1.09-1.78: PR49's x1.735 then x0.529 a second apart, PR108's three within five seconds, PR116, PR091, PR054, PR27's x0.852 at 127.7 s -- some may be a continuous zoom) and at PR101's claim (141 +- 17) before quoting it; and the hint in pass 5 that PR27's wide field at x11.8 (0.61 deg) is 5 % from PR051's NAR (0.6427 deg) -- a shared ladder would put a field on every clip that zooms to or from a state of it.
4. The new bounds on real clips (session 1's item 4): `streak` on PR43 with the clip's own blur (`forensics.point_blur`,
   as `focus` measures it), `horizon` on a sea horizon of known height and range, `focus` and `haze` on a daytime clip
   with a known range.
5. The speed band (K1, K8), then objectives 3 and 5.
   Also for 0.4.0: the parallax ladder's nearest height for a still object (ROADMAP's ideas bank, the last 0.4 row,
   from Long's homography draft): `kinematics.parallax_ladder` reports k v_O as the object's own speed and picks k
   by it (PR043: 922 m/s printed where 31.5 is needed); the row has the fix and the test's known answer.
6. The released-track null on PR051 (session 1's item 3): it needs the scene measured through the leak's breaklock,
   which waits on K9 first.

---

# Session 1 (2026-10-27), the record -- finishing k, PR051 as a known answer, the range bounds without motion

Jacob asked (2026-10-27): "Let's do all of the above for the 0.4 release. Let's first focus on everything needed for 3
finish k and evaluate on PR051. 5 is also important. Go ahead with the first session, prompt when needed, and then work
until we need to handoff to another session. Submit jobs through /slurm". "Above" is the path to 0.4 given that morning
(the order: 1 layers' per-template error K9; 2 the unknowns ledger as a skeleton; 3 finish k -- PR051, the pointer sweep
re-run, camera and zoom reading each other; 4 the speed band, kriging K1 with planted tracks K8; 5 the range bounds
without motion -- horizon, haze, focus, the streak; 6 then objectives 3 and 5, the admissible region and tau/aspect on
Galileo aircraft with ADS-B, and more kinds of known quantity). This session did 3 and 5; 1, 2, 4 and 6 are next.

Decision asked and given: **`integrity` switches its zoom across transients to `zoom_fit`** ("Switch to zoom_fit").

## Where the work is

Built in a worktree (`/hugespace/models/mcdonald-v04`, branch `v04-k` off main at e60238f), because Slurm jobs import
the main checkout's code at each start and a half-finished edit there would have broken them (it nearly did: see "What
went wrong"). At the end it was committed and **main fast-forwarded to it, locally; the worktree and the branch were
removed. Not pushed, no version bumped** (CHANGELOG has an Unreleased section). **Jacob, 2026-10-27: "just commit, we'll
hold on pushing until 0.4.0"** -- the 0.4 sessions commit to main locally and nothing is pushed or released until 0.4.0. Scratch job scripts under `/scratch/mcdonald/pr051-2026-10-27/` and `/scratch/mcdonald/v04-dev/` still name
the worktree's `src`: point them at the main checkout to run them again.

**Tests at the end (2026-10-27, the final code):** every suite one job each (`/scratch/mcdonald/v04-dev/suites/`): the
17 of `tools/suites.sbatch` passed mid-session, and the ones touched after (measurement 461, reduction 344, cli 126,
zoom 31, camera 114, slew 59, horizon 17, focus 10, haze 9, streak 5) passed again on the final code, with **golden 118
PASS, 0 SKIP** (PR051's zoom among them). `tools/zoom_check.py`: all passed (PR27's and PR057a's steps and slews,
Puerto Rico's three switches, the 142.6-s one now a step confirmed by two pairs; PR27's traps unknown).

## What was built (each with its tests; method sections in `docs/method.md`)

| what | where | tested by |
|---|---|---|
| a zoom with no blank: the scan's own steps of level or contrast (`events.picture_steps`, shared with `events`) and `zoom --events CSV`, fitted as bursts; a measured one a boundary (`kind` "picture"), the rest kept in `picture_steps` | `zoom.picture_candidates`, `plan`, `measure`; method §17 | `test_zoom` (end to end through `zoom.measure` from rendered frames); PR051's leak x0.498 vs the data bar's x1/1.999 |
| the zoom fit's window variance in float64; a window with no detail no match | `forensics._zoom_score`, `ZOOM_FLAT` | `test_zoom` (a frame flat in part; fails on the old code: ZNCC 10.46, a false x0.136) |
| a marginal fit confirmed by pairs 1-3 frames out (two passing on their own, within 3 %) | `zoom.marginal`, `zoom.confirm` | `test_zoom` (the rule, with fit_all stood in for); `tools/zoom_check.py`: Puerto Rico 142.6 s now a step |
| a strong fit (ZNCC >= 0.5 and twice its rival's) leads whatever the prominences | `forensics.ZOOM_STRONG`, `ZOOM_ZNCC_LEAD`, `zoom_fit_scenes` | PR144's x5.8 (see below); `zoom_check` |
| `integrity` across transients through `zoom.fit_all` + `zoom.confirm` (Jacob's decision) | `integrity.transient_zooms` | PR144: step x5.804 (ZNCC 0.87), its second transient no step x0.995 (/scratch/mcdonald/v04-dev/pr144_izoom3_*.out) |
| `camera --zoom` and `run`'s camera stage reading `<tag>_zoom.json`: imaged steps taken out of the track, checked on the object; other bursts camera events | `camera.imaged_steps`, `first_new`, `burst_events`; `stages` camera | `test_camera` (`test_zoom_from_the_picture`) |
| `slew`: one row a state (a "no step" join had counted windows twice); the figure a row for the clip, then a row a state; a state under 0.5 s no longer crashes `slews` | `slew.measure`, `figure`, `slews` | `test_slew` (the figure's height; five frames); PR27 unchanged (267 -> 517, x1.932 vs x2.000) |
| `mcdonald horizon` | `horizon.py`, method §27 | `test_horizon` |
| `mcdonald focus` | `focus.py`, method §28 | `test_focus` |
| `mcdonald haze` | `haze.py`, method §29 | `test_haze` |
| `mcdonald streak` | `streak.py`, method §30 | `test_streak` |
| the pointer sweep tool | `tools/pointer_sweep.py`, `tools/pointer_sweep.sbatch` | PR27 through it: 267 -> 517 px/deg, x1.932 vs x2.000, agree |

README-technical lists the four new commands and `zoom --events`, `camera --zoom`; tests/README.md the four new
suites; `tools/suites.sbatch` runs them; ROADMAP's ideas-bank rows for these are updated; CHANGELOG has an Unreleased
section.

## PR051 (the user's ask): what it gives, and where

Reference data (`/models/data/mcdonald/pr051/`, README, SHA256SUMS): Corbell's upload and Sitrec's .mov (watermarked:
a local reference, not to be redistributed, as `ptzslam_soccer/` is), the released copy in `pursue/`, and three
readings tables. The known answers, read off the data bar by eye:

- **The first framing of the upload (t 3-35 s) has three fields**: NAR to 14.0 s, FVW / SLR = **0.6427 deg +- 0.15 %**
  (649-657 m at 31.23-31.64 NM); ULTN from 14.25 s, 0.3212 deg (x2.001); 2X of ULTN from 17.0 s, 0.1610 (x1.995). In
  NAR, k = 1440 / 0.6427 = **2240 px/deg** in square pixels (the 4:3 sensor stretched to 1920), and the depression
  5.1-5.4 deg (HAT 17,072 ft over SLR), so **c = k cos e = 2230 +- 10 px/deg** is what `slew` should read there.
- **The leak's electronic zoom out at its frames 1331-1341** (2X -> ULTN, no blank, FVW 119 -> 238-239 m): `mcdonald zoom`
  measures **x0.498 = 1/2.008 against x1/1.999**, the first real known answer for a zoom with no blank.
- The upload's NAR -> ULTN switch at 13.85-14.21 s (with a blank) comes out unknown (x0.99 at ZNCC 0.15: streaky
  terrain sweeping during the blank); its ULTN -> 2X at 16.9 s is not found (neither level nor contrast steps).

What it took to get `slew` going on it (each a trap worth knowing):

1. **The overlay is not masked by itself.** The analog capture jitters the whole picture, so no pixel holds within 2
   grey levels (`static_masks` finds 0 %), and the clip reads as colour, so the colour route is off too. Unmasked,
   `layers` read the scene held still in 88 % of pairs. Boxed by hand (12 boxes; `/scratch/mcdonald/pr051-2026-10-27/
   run_nar2.sbatch` has them), it moves: 401 px/s median in the upload's pixels.
2. **The content jumps.** Beyond the regular doubling (59.94 over 29.97), the scene moves in jumps every few unique
   frames, so most 2-frame pairs fall inside a hold. `layers --k 2` left `slew` 20-23 samples (it needs 30). `--k 8
   --max-shift 25` (a 200-px search over 4 unique frames, about one jump cycle) is the run in `nar3/`.
3. **The pointer is mislocated at 4-6 s** (over bright ground: radius 315 +- 19 px); from 7 s it holds (310.5 +- 0.3).

**The result: NO POWER, a floor c >= 1087 px/deg**, which the truth (2230) clears -- the stage refuses correctly, as it
did on Puerto Rico, but PR051 does not yet give k from its slew. Why: even at `--k 8`, 72 % of pairs are "held still"
and left out (in this upload a held pair is real: the content did not update), so the scene chains whole only over
5.1-8.3 s, and the pointer is clean only from 7 s. The pointer's rate does change (-0.13, +0.43, +0.24 deg/s over 7-9,
9-11.3, 11.3-14.2 s, square pixels), so there is lever once the scene chains over 7-14 s. Built for it: **`slew
--hold-rate`** (the platform's share known: here about +0.068 deg/s in the pointer's sense, from the aircraft's 70.9
m/s across the line of sight at 58.1 km, read off ACFT at 5 and 10 s -- blurry digits, good to ~10 %). Runs and logs:
`/scratch/mcdonald/pr051-2026-10-27/` (`nar/` unmasked, `nar2/` boxed at k 2, `nar3/` boxed at k 8, `nar3/held/` with
the hold given; `zoom_v04/` the zoom runs; `look/` the crops the data bar was read from).

**Tried at the end: the held pairs as real zeros** (`nar3/zeroheld/`: the 487 pairs `layers` read still over 8 frames
and could not re-measure over 60 set to 0, a scratch edit of the CSV). The scene then chains unbroken over 7-14.2 s
(421 samples). With the hold fitted: no registration, a floor of 270. With `--hold-rate 0.068`: **c 549 px/deg
(16-84 % 183-538), refused** -- forward and reverse 71 % apart, the bootstrap +-32 % -- against the truth 2230; and the
pointer's rate and the scene's *anti*-correlate (r -0.52, best at +6 frames). So the pointer and the picture do not move
together frame by frame in this edit of the footage: whether the upload's frames were re-timed (its slowed passages
elsewhere), the overlay drawn on a cadence of its own, or the jumps sit in the picture alone, is the first thing to look
at -- the pointer's own steps against the picture's jumps, frame by frame. No false claim was made at any point.

**Next for PR051's k**: a sequence of the upload's content changes alone (drop every frame whose picture, the overlay
masked, is within noise of the one before), each frame timed at its first appearance; `symbology` and `layers --k 1`
on it, the CSVs' `t_s` from that timing; then `slew --window 7:14.2 --hold-rate 0.068 --pixel-aspect 1.3333` and
without the hold. The ACFT position should be read more carefully (every second over 5-14 s) for the hold.

## The pointer sweep

`tools/pointer_sweep.py` over the 127 sensor clips of the uap repository's `analysis/corpus/pointer_sweep/clips.csv`
(list at `/scratch/mcdonald/pointer-sweep-2026-10-27/list.tsv`: zoom on every clip, slew on the 17 whose pointer and
scene chains exist under `/hugespace/local/tmp/slew/`). A first pass with main's code was stopped at 56 clips when the
float64 bug turned up (its results are in `out/`, made with the bug). **Re-run with the v04 code** (job 12274, all 127
clips, `out_v04/`, `summary.md` and `summary.json` there; `python3 tools/pointer_sweep.py collect <out>` remakes them):

- **573 bursts: 95 measured steps, 56 no step, 422 unknown.** All 95 steps are at blank bursts; no step of the picture
  with no blank was measured anywhere in PURSUE (they come out no step or not measured).
- **The ladder: the MTS-B steps by x2 and by x5.9.** Folded so a zoom in and out count alike: x2.003 (45 steps, 1.87-2.06),
  x5.89 (18, 5.76-6.32), x2.33 (9, 2.19-2.36), x3.13 (3), x7.5 (2), and a scatter of ones and twos between x1.09 and x1.76
  that should be looked at before anything is said of them. PR051's data bar says why x2: its 2X and 4X are electronic,
  and NAR -> ULTN is x2.00 too.
- **slew's claims, by state:** PR27 267 +- 3 -> 517 +- 50 across x2.003 (c x1.932, agree), PR057a 276 +- 18 -> 584 +- 26
  across x2.001 (x2.119, agree), PR134 205 +- 11, PR101 141 +- 17. PR076's claim of the first pass (no rate correlation)
  is refused now. PR101 was "not trusted" in the uap sweep note (2.6 scatters, rates at r 0.51-0.55): look at its window
  before quoting it.
- Not yet written into the uap repository's `analysis/corpus/pointer_sweep/README.md` (pass 5): that repository had
  another session's uncommitted work in it at the end of this one, and was left alone.

## What went wrong, so it is not done again

- **Editing the main checkout under running Slurm jobs.** The sweep's array tasks and the PR051 job import
  `/hugespace/models/mcdonald/src` at each start; a half-written `zoom.py` (a constant not yet defined) sat there for a
  minute. Work moved to the worktree and main was restored at once; no task was seen to fail of it (PR40's crash was a
  real `slews` bug). Develop in a worktree whenever jobs run from a checkout.
- **A forkserver pool needs the main guard** in a scratch script (the PR144 check failed once for it), as the memory
  says.
- **Test scenes that are wrong, not the code**: a view that jumped 600 px at the zoom; a star on the object; an
  expectation of 0.22 for BT.709's 128 (it is 0.26). Each time the test was fixed, not the code -- check which.

## Open, in the order I would take them

1. PR051's k from its slew: the content-change sequence above; if it registers, a golden check (`tests/test_golden.py`:
   the NAR window's c against 2230 +- 10 %). PR051's zoom answer (x0.498 against x1/1.999) wants a golden check now:
   `zoom.measure` on the .mov, the step at frames 1331-1341.
2. Write the sweep's pass 5 into the uap repository's `analysis/corpus/pointer_sweep/README.md` (above; the numbers are
   in `out_v04/summary.md`), look at the scatter of small ratios (x1.09-1.76) and at PR101's claim, and put a field on
   every clip that zooms to or from the x2 / x5.9 ladder's states from PR27's wide 267 px/deg.
3. The released-track null on PR051 (ROADMAP row): the breaklock at the released copy's frames 4601-4605 (the leak's
   ~1150-1205); the camera's rate before needs the scene registered while the gate tracked (the leak, masked as above).
4. The new bounds on real clips: `horizon` (a sea horizon, a known height and a surface target at a known range -- PR149's
   ship if its altitude can be had), `focus` and `haze` (a daytime EO clip with a known range: AARO's resolved cases),
   `streak` on PR43 (its track from `/models/data/mcdonald/cases/pr43.mcdonald`).
5. Then the session plan's 1, 2, 4: layers' per-template error (K9), the unknowns ledger on every report (objective 6),
   the speed band (K1, K8).
6. Not done: the defocus disc's flat-topped profile as the near-thing test (`focus` says so); `zoom` seeing FLIR1's
   no-blank zoom (its sky steps nothing; `camera` covers it).
