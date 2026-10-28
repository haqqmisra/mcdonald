# Handoff: ROADMAP 0.4 -- session 3 (2026-10-28, afternoon) on top, session 2 (2026-10-28) and session 1 (2026-10-27) below as the record

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
