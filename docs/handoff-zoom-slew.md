# Handoff: zoom states in `slew`, and a scene zoom fit that works on PURSUE (2026-10-20; built 2026-10-21, merged to main, unreleased)

Jacob asked (2026-10-20): "On zoom: can we add a feature in mcDonald to detect zoom?" It was proposed for a fresh
session, on its own branch off main. Do not push or release (Jacob's standing instruction). Run the suites and any
heavy runs through Slurm (`tools/suites.sbatch`; nice ≥ 5000 for sweeps).

## Why

The k-from-slew sweep of PURSUE (uap repo, `analysis/corpus/pointer_sweep/README.md`) found that the MQ-9 clips change
zoom during short bursts of blank or flash frames, and every clip tried has them. PR27 has four in 297 s; PR067 has
nine. `slew` does not know. On PR27 this cost three things:

- **Mixed claims.** Automatic windows across the 82-s step fitted one c to two fields, and some still passed every
  check.
- **A false refusal.** The whole clip was refused because "the windows disagree": three windows measure 268 px/deg
  and one, two zoom steps later, gives a floor of 1238.
- **A missed check.** The ratio of c across a step is a measurement of the zoom. The imagery measures it too.
  Comparing the two is the best internal check the method has, and it is free.

The sweep worked around this with `analysis/tools/pointer_slew_states.py` (uap repo), which cuts the automatic windows
at blank bursts, and `pr27_zoomcheck.py`, which fits the scale by hand. Both belong in mcdonald.

## What exists already

- **On main:**
  - `forensics.transients(series, frac=0.35, max_len=40)`: runs of contrast collapse.
  - `forensics.zoom_ratio(clip, n_before, n_after, masks, boresight)`: the later frame shrunk by s and matched within
    ±60 px of the boresight, s from 1 to 9.
  - `scale.zoom_chain(clip, transients, masks, boresight)`: `zoom_ratio` at each transient.
- **On branch `flir1`** (another session's work, not merged; see `docs/handoff-camera.md` there):
  - `camera.zoom_steps`: zoom from a tracked object's size and offset.
  - `events.find`: the picture's steps, held runs and transients.

Design so that both merge. `events` already reads transients, so do not fork that logic.

## What failed, and must not fail again

1. **±60 px about the boresight.** On AARO's Puerto Rico clip the ground moved 300–400 px during each ~15-frame blank.
   `zoom_ratio` read ×1.0 at every switch (ZNCC 0.27–0.62). Search the whole earlier frame.
2. **An unmasked overlay.** A first hand fit on PR27 matched the static symbology (reticle, cyan "N", corner brackets,
   black redaction boxes). It read ×1.00 at ZNCC 0.75 even against a blank white frame. Mask coloured pixels and held
   black or white pixels, dilate the mask, fill it with the local median, high-pass the frame, then **zero the filled
   pixels**, so they match nothing. Static masks are not enough here: in a stare the whole scene is static.
3. **Frames inside the transition.** The gain settles about ten frames after the burst (Puerto Rico). PR27's 58-s
   step has a vignetted mid-zoom frame. Take the last good frame before the burst and the first settled frame after
   it: frame-to-frame difference back under a threshold for three frames running (Puerto Rico's `pr_zoom.py`
   `blank_edges`).
4. **The edge of the grid.** PR27's 89-s step has featureless haze with a static vignette ring behind it. It fitted
   ×6.00 at ZNCC 0.25, exactly at the grid's edge. A ratio at the edge of the grid, or with ZNCC under about 0.4, is
   "not measured", never a number.
5. **×1.00 on a featureless scene is not "no zoom".** PR27's 134-s burst fitted ×0.98–1.00 at ZNCC 0.45 (the same at
   ×1). It is a zoom: AARO's description says "zoomed 2:15", and the vignette ring gives way to a central glow. The fit
   matched the detector's fixed pattern and the vignette's edge, which do not move with the scene. Remove the fixed
   pattern (subtract a temporal median over a held stretch) before fitting, and require the ZNCC at s to beat the
   ZNCC at 1 by a margin before calling either a step or no step. A burst with no trusted fit is an "unknown"
   boundary: never assume a step, and never assume none.
6. **One change of optics can be several bursts.** PR27 at 82 s is grey, then white, then grey within 0.5 s. Merge
   bursts under about a second apart.

## Proposed design

- **`forensics.zoom_fit(clip, before, after, ...)`**: the whole-picture scale search. Overlay filled and zeroed,
  high-passed ZNCC, s on a log grid from 1/8 to 8, and a refinement. Returns s, ZNCC at s, ZNCC at 1, and whether s
  is at the grid's edge. Keep `zoom_ratio` for its callers, or make it call this with a narrow search.
- **Zoom states**, used by `slew`:
  1. read the clip's contrast series (or `layers`' chain breaks) and find the transients;
  2. merge the close ones;
  3. fit each with `zoom_fit`;
  4. call each a step (s and its ZNCC), not a step (s ≈ 1), or unknown.
- **`slew`**:
  - cut automatic windows at every transient (pad about 12 frames);
  - group the windows by state, and compare claims only within a state;
  - across a measured step, report the ratio of the states' c against the imaged s. That is a pass or fail check.
  - a floor in one state must not refuse a claim in another. Across an "unknown" step, say so; do not compare.
  - the report has one line per state.
- **Optional:** a `mcdonald zoom VIDEO` command that prints the states, for use outside `slew`.

## Known answers to test against

| clip | step | expected |
|---|---|---|
| PR27 (`uap/data/release_01/videos/DOD_111688825.mp4`) | 82.0–82.3 s | ×1.98–2.00 (ZNCC 0.49–0.52 vs 0.10–0.14 at ×1); slew c 268 → ~515–530 |
| PR27 | 134 s burst | a zoom per AARO ("zoomed 2:15"), ratio unknown; a naive fit says ×1.00, which must come out "unknown" |
| PR27 | 58 s | zoom-out about ×4–5 (rough: mid-transition frame) |
| PR27 | 89 s | unmeasurable (featureless haze): must come out "unknown" |
| PR057a (`uap/data/release_02/videos/DOD_111719752.mp4`) | 32.8 s | ×2.00 (ZNCC 0.78–0.83); slew c ~250–263 → 570 |
| AARO Puerto Rico (`/models/data/mcdonald/aaro/videos/DOD_110692805-1920x1080-9000k.mp4`) | 20.5, 118.1, 142.6 s | ×5.05, ×3.05, ×1/3.10 (readout 5, 3, 1/3) |
| FLIR1 (on `flir1`) | frame 2235 | ×2 (the object's size ×1.91, its offset ×2.08) |

The PR27 pointer and layers CSVs for the whole clip, and its extracted frames, are in `/hugespace/local/tmp/slew/pr27_all/`
and `/hugespace/local/tmp/slew/frames/PR27/`. PR057a's are in `/hugespace/local/tmp/slew/sweep/chain/PR057a/` and
`/hugespace/local/tmp/slew/frames/PR057a/`. They are scratch: copy what a test needs into `tests/golden/` or
`/models/data/mcdonald`, never point at the uap repo. For a unit test, a rendered scene with a scale step inside a
blank burst, under a drawn overlay, is cheap and decisive.

## Related, not zoom: the one-frame alignment

`analysis/tools/slew_lag.py` (uap repo) cross-correlates the pointer's rate with the scene's. On PR27's main slew it
peaks at −1 frame (r 0.9813 against 0.9799 at 0), which is probably the half-pair offset of `layers`' k = 2 shifts.
That moves c by 1 % there (267 to 264). On PR057a's 2.7-s slew it moves c by 5 % (250 to 263), and ±2 frames span
226–280. At −1 frame, all three wide-state windows on the two clips agree at 263–264. While in `slew`, fit the lag
(or at least report how far c moves for ±1 frame), and check that the scene path's frame time and the pointer's
are aligned as `kernel(k)`/`smooth_like_scene` intend.

## Related, not zoom: two more gaps the sweep found in `slew`

- **A claim with no rate correlation.** PR076 (uap: `analysis/corpus/pointer_sweep/README.md`, pass 3) passed every
  check at 122.9–169.2 s (c 526, 16–84 % 504–542, 9.7 scatters). But the pointer's rate and the scene's correlate at
  r = 0.24 at every lag. The c came from slow curvature over 46 s, which a drifting hold mimics. A check on the rates
  (r below about 0.5: refuse, the turn does not follow the scene) would have caught it. PR27's main slew is at r 0.98
  and PR057a's at 0.90–0.99.
- **Stale wording in `symbology`.** Its report still says "The pointer gives north as projected into the image ...
  Reading its rotation as azimuth change assumes ...". PR051 (MTS-B), AARO's Puerto Rico (WESCAM) and now PR27/PR057a
  show it is the line of sight's azimuth (a dial). The caveat should follow `slew`'s "assumes" line instead.

## Status (2026-10-21): built on branch `zoom`, merged to main the same day; not pushed, not released

Built in worktree `/hugespace/models/mcdonald-zoom` (branch `zoom` off main 5dd4fdc; both removed after the merge). Method: `docs/method.md` §17, "Zoom
states". What was built, against the design above:

- `forensics.zoom_fit(clip, before, after, masks, fixed_before, fixed_after)` and `zoom_fit_frames` (frames as
  arrays): the whole-picture search, the overlay filled and zeroed (`zoom_mask`, `zoom_fill`, `zoom_detail`), each
  side's fixed pattern taken out (`zoom_fixed`, `zoom_clean`), a log grid 1/8-8 on halved frames and a fine one at full
  size. `zoom_ratio` is kept for `integrity`; `scale.zoom_chain` now calls `zoom_fit` (it unpacked a tuple as a dict).
- `mcdonald zoom` (`src/mcdonald/zoom.py`): the 192-px scan, bursts (contrast collapse or a level jump; merged under
  1 s), settled edges (change and level drift), the clip's static overlay from 40 frames, the fits, and the states and
  chains. Writes `<tag>_zoom.json`.
- `slew`: `--zoom JSON` / `--no-zoom` (default: read `<out>/<tag>_zoom.json` or make it); windows found per state and
  cut at every burst (PAD 12 frames, pieces >= 3 s); a hand window across a step or an unknown burst refused; claims
  and floors per state; the c-ratio check across measured steps (and claim-vs-floor through a step); one line per
  state; the rate-correlation refusal (r < 0.5 at every lag within 6 frames); the lag fitted and c's shift for +-1
  frame reported.
- `symbology`'s stale "north as projected into the image" caveat replaced by `slew`'s "assumes" wording.

Two things the handoff did not foresee, both now rules:

1. **Shrink, then high-pass.** High-passing each frame and then shrinking the narrower kept only detail under 2 px of
   the wider frame at x5: Puerto Rico's 20.5-s switch read ZNCC 0.25 that way, 0.62 the right way.
2. **Choose the scale by prominence, not ZNCC.** The best chance ZNCC grows as the template shrinks, so the grid's far
   end wins on repeating detail (Puerto Rico's sea: x8 at 0.48 where the truth, x3.05, scores 0.44). The peak's height
   over its correlation surface in robust SDs found all three measured switches. A verdict needs >= 8 MADs, a x1.25
   lead over the best scale a quarter or more away (and over x1, for a step), ZNCC >= 0.15, not on the grid's edge;
   "no step" also needs the fixed pattern taken out both sides. The handoff's "ZNCC under about 0.4 is not measured"
   is replaced by these (Puerto Rico's 118-s step is right at ZNCC 0.39).

Known answers (`tools/zoom_check.py`, reference data, 14 min on 4 CPUs through Slurm):

| clip | burst | got | expected |
|---|---|---|---|
| PR27 | 82 s | step x2.000 | x1.98-2.00 |
| PR27 | 89 s, 134 s | unknown, unknown | unknown |
| PR27 | 58 s | unknown | "x4-5 out, rough": not measured |
| PR057a | 32.8 s | step x2.001 | x2.00 |
| Puerto Rico | 20.5, 118.1 s | steps x4.966, x3.096 | readout x5, x3 (hand x5.05, x3.05) |
| Puerto Rico | 142.6 s | unknown (fits x1/3.096 but leads the next scale by only x1.14) | readout x1/3 |
| `slew` PR27 | 82 s | 267 -> 517 px/deg, x1.932: agrees | ~268 -> 515-530 |
| `slew` PR057a | 32.8 s | 276 -> 584, x2.119: agrees | ~250-263 -> 570 |

FLIR1's frame-2235 zoom (on `flir1`) has no blank: the scan's contrast stays at 17-20 through it and the change from
frame to frame is at most 6.6, so `mcdonald zoom` does not see it (a zoom with no blank is outside what it looks for);
`camera.zoom_steps` covers it from the object. Its six blank bursts (17.6-74 s) are all unknown: a featureless sky,
the fixed pattern 82-87 % of the detail at four of them.

Reference data added (`/models/data/mcdonald`, README and SHA256SUMS updated): `pursue/DOD_111688825.mp4` (PR27),
`pursue/DOD_111719752.mp4` (PR057a), and `slew/` (their north and layers CSVs from the uap pointer sweep).

**Open.**
1. Merge with `flir1`: both add to `forensics.py` (different places), `cli.py`, `symbology.py` (different hunks),
   `scale.py` (flir1 changes `fov_ladder`, this changes `zoom_chain` and the docstring), `tools/suites.sbatch` (both add
   a suite: one line) and `docs/method.md` (flir1 numbers its new sections 18-23 after main's 17; this adds a part of
   17, so main's 18 stays 18). `events.find` reads `forensics.transients` as before; `zoom.bursts` adds the level jumps.
   The design is for `events` to report the picture's steps and `zoom` to fit them: if `events` grows a burst list,
   `zoom.plan` could take it.
2. `integrity` still fits zooms with `zoom_ratio` (+-60 px, no prominence). Switching it to `zoom_fit` changes its
   report's numbers, so it waits for a decision.
3. The prominence rule leaves correct-but-marginal fits unknown (Puerto Rico 142.6 s). A second, independent pair of
   frames either side (a frame or two further out) agreeing on s would be a way to trust such a fit without lowering
   the bar for traps.
4. The pointer sweep in the uap repository can now be rerun with `slew --zoom` in place of `pointer_slew_states.py`.
5. `slew`'s figure is one row per window (64 inches tall on PR27); a per-state summary figure would read better.
