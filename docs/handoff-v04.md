# Handoff: ROADMAP 0.4, session 1 (2026-10-27) -- finishing k, PR051 as a known answer, the range bounds without motion

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
removed. Not pushed, no version bumped** (CHANGELOG has an Unreleased section): Jacob's call when 0.4's first release
goes out. Scratch job scripts under `/scratch/mcdonald/pr051-2026-10-27/` and `/scratch/mcdonald/v04-dev/` still name
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
