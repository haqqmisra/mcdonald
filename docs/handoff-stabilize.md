# Handoff: `mcdonald stabilize` (branch `stabilize`, 2026-10-18)

**What it is.** A new stage for video of a screen filmed by a phone, the fifth tranche's PR117–PR122
(an AC-130's IR display over the Gulf of Oman). It finds one homography a frame from the display's own
drawing, never its picture, and writes the display's video (`<tag>_stable.mkv`, FFV1, frame n = frame n).
Every other command then runs on that video. Method and traps: `docs/method.md` §14 (§13 on the branch; renumbered on the merge,
main's §13 being the bird headline).

**State.**
- Branch `stabilize` from main 76edc50, worktree `/models/mcdonald-stabilize`.
- Not merged, not released. Main had uncommitted 0.3.0 work in `CHANGELOG.md`, `ROADMAP.md`,
  `docs/method.md`, `flicker.py`, `report.py` and two tests when this branched; the branch does not
  touch those files except `docs/method.md`, where it only appends its section (§14 on main).
- **Files.** `src/mcdonald/stabilize.py` (new); `cli.py` (one line); `progress.py` (one line in
  `WORKER_MODULES`); `tests/test_stabilize.py` (new, portable, passes: 0.08 px rms against the truth);
  `tools/stabilize_selftest.py` (new: a simulated phone filming a real clip, the true homography known).

**Validated.**
- PR117: the held boresight against the independent reticle-line fit, 0.26 px rms (1.0 px worst) over
  483 frames.
- PR117: a display ring held out of the template wanders 4.8 px rms, 345 px from the boresight. That is
  the phone lens's distortion, which a homography cannot hold.
- All six Oman clips hold: 500/500, 906/906, 63/84, 370/398, 973/1032 and 789/790 frames, median ECC
  0.72–0.96. The case write-up is the uap repo's `analysis/cases/pr117/README.md`.

**Known failure, open.** A textured scene with a thin overlay can be held instead of the display.
- In the self-test, PR144's clouds were held (about 33 px from the truth), and pass 2 confirmed it
  because its template came from pass 1's frames.
- `drawing_persistence` (the start's template against the end's) does not catch this case: 0.65 there,
  where the threshold is 0.5. It may still catch a scene that leaves the view, but it is uncalibrated.
- Remedies in the stage: `--anchor X0,Y0,X1,Y1@N` and `--drawing chroma`. On PR144 with chroma the
  match is 0.98, but PR144's own drawing is not fixed (its brackets jump at a zoom step and its north
  pointer moves), so it is not a clean test.
- Clean self-tests draw a fixed reticle on the display: `stabilize_selftest.py --overlay` (over PR144's
  clouds) and `--overlay --scene flat` (Oman-like).
- With a fixed Oman-style reticle over PR144's panning clouds (`--overlay`), the stage holds all 150
  frames to the truth: 0.12 px per-frame median near the centre, 0.48 px rms over the view, 8.6 px at
  worst on one or two frames. Persistence is 0.95, and it recovers the planted tremor (8.99 Hz) and
  vibration (7.69 Hz). So the failure needs a drawing that is small and thin next to the scene, as
  PR144's own few orange marks are; a rich scene alone does not cause it.
- Oman-like (`--overlay --scene flat`: a fixed reticle on a featureless field with fixed pattern and
  grain): all 150 frames held, 0.20 px near the centre, 0.31 px rms over the view, 0.5 px worst.
- Ideas not built:
  - an automatic choice of chroma when thin coloured strokes exist;
  - a two-layer test (after holding, look for a rigid set of straight strokes that still moves);
  - a radial distortion term shared by all frames (the PR117 ring's 4.8 px).

**Added 2026-10-18 (second round).** `--to-clip HELD_TRACK.csv`: a track made on the held video, carried
back onto the clip's own pixels through `<tag>_stabilize.csv` (the stage is not run again if that file is
there), with gaps of up to `--fill` frames (default 4) filled on the held video first. Use it so that
`flicker` runs on the clip, whose GOP its codec controls need. Tested: a held point carried back stays on
one display point to 0.10 px.

**The reference frame (fixed 2026-10-18).** The first committed run lost 152 of PR120's 398 frames. The
"sharpest" frame was 263, in the second of visible sea between its mode changes. The coherence weighting
counts long wave crests as lines, so the template began as sea. `sharpest` now passes over frames with more
than `TYPICAL` (1.3) times the clip's median structure. PR120: 388 of 398 held (ECC 0.884, persistence 0.84),
against 370 in the exploratory run. The rule keeps PR117's, PR119's and PR122's reference and moves PR118's and
PR121's.

**Results at 3c058ed** (`/hugespace/local/tmp/oman/runs_v1`; PR118, PR120 and PR121, whose reference moved, in `runs_v2`):

| clip | held | ECC | persistence | note |
|---|---|---|---|---|
| PR117 | 500/500 | 0.927 | 0.86 | held-out ring 1.38 px rms (95 % within 2.2), from 3.8 in the exploratory run |
| PR118 | 906/906 | 0.939 | 0.80 | the display's right edge, seen in frames 25-55, maps to one held x (2311-2313) |
| PR119 | 80/84 | 0.814 | 0.58 | |
| PR120 | 388/398 | 0.884 | 0.84 | after the reference fix |
| PR121 | 973/1032 | 0.950 | 0.88 | |
| PR122 | 789/790 | 0.961 | 0.82 | |

**Not built, and why: the clock (ROADMAP S9).** Tried on the Oman phones, one steady picture rate per clip
leaves 23-114 ms rms against the frames' slot times; nearest-slot padding of a steady rate would leave at
most ±16.7 ms. The phones' low-light rate wandered within each clip. Counting repeats also cannot align
two exports of one recording picture by picture: PR121 against PR122 drifts (correlation 0.39 by
new-frame index, 0.68 by file frame). Until pictures are matched by content, a picture's slot time is the
best estimate of when it was taken; a fitted clock would be worse.

**Before a release.**
1. Results of the two clean self-tests, and a decision on `drawing_persistence`: calibrate it or drop it.
2. README-technical "Use" entry, CHANGELOG, ROADMAP line (after the 0.3.0 work lands, to avoid
   conflicts).
3. The window: a "Hold the screen still" step, with a box for `--anchor` drawn on a frame.
4. Speed: pass 1 is about 0.6 s a frame (sequential). Pass 2 and the video are pooled.
5. A golden: PR117's held boresight against `pr117_jitter.csv` (which would need vendoring into
   `tests/golden/`), or the PR117 frame-2 repeat.

**Found on the way (for the 0.3.0 work).** `flicker` gave PR117 (frames 1–135) no `no_power` entry, yet
its own planted beats were recovered in 0 % of trials up to 20 % (stage rule) and 0–38 % (paper rule).
Its closed form says 37 % is needed. A test that cannot hear a 20 % beat should say so.
