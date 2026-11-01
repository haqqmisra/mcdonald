# Handoff: the phone-video scope -- session 1 (2026-11-01): WP0, WP3's report line and WP8 built; 0.4.1 held for Jacob's word

The scope is the uap repository's `analysis/methods/mcdonald_phone_video_scope.md` (Jacob's decisions of 2026-11-01:
WP0, WP8 and WP3's report line as 0.4.1; WP1 and WP4 as 0.4.2; WP2 and WP3 as a theme ahead of 0.5; no track log, no
filming). The case is IMG_5611, a witness's iPhone clip from a fishing boat on Rhode Island Sound (2026-06-12), in the
uap repository's `analysis/cases/rhode_island_sound_2026/` (the clip itself in `data/external/case_sullivan/`, not for
sharing without the witness's yes). What was found on it before any of this is that folder's `README.md`; what the
package could not do is its `mcdonald_feedback_triage.md`.

## Where it stands

Two branches, built in worktrees so that no Slurm job imported a half-written tree (main moved under them the same
day, b4d88b9, another session's ROADMAP rows: **merge, do not rebase**):

- **`phone`** (`/hugespace/models/mcdonald-phone`, fd01dc4): WP0 and WP3's line. `clip.probe` gives the size of the
  frames ffmpeg decodes, turned by the container's display rotation (`rotation`, `turned_on_its_side`: a swap within a
  degree of 90 or 270, as ffmpeg's autorotate transposes), keeping `coded_width`, `coded_height` and `rotation`;
  `integrity.container_report` names a codec-less stream by its tag. `report.Case.behind_held_still` keys on the
  layers step's own no-power ("held still on screen") and the first line, the headline's speeds and the bottom line
  follow; `_deg` gives a rate under a degree to its figures. PR44's and PR135's exercise pages quote the new clause.
- **`phone-wp8`** (`/hugespace/models/mcdonald-wp8`, 22a86e3 and the 0.4.1 bump after it): WP8's four, and WP7's short
  part. `tracksheet.paged` and the verify step; `symbology.measure(masks=)` with `OVERLAY_MIN`; `figures.BANDS` in
  the headline, `_like` and the figure; `audio --platform` with `SUPPLY`, `TURNING`, `engine_speeds`; a section in
  `docs/agents.md`. PR113's exercise page changes by the bands' clauses.

**The version is 0.4.1, dated 2026-11-01, on `phone-wp8`** (`__init__`, CITATION.cff, both READMEs' status lines, the
CHANGELOG's entry; `test_reduction` holds the five together). CITATION.cff's version DOI is still v0.4.0's until the
release mints the next.

## What the fixture proved, and the traps

- A phone's rotation cannot be made by re-encoding: `ffmpeg -display_rotation 90 -i frames.png ... out.mov` applies
  the turn and writes an upright file with no flag. Set it on a stream copy (`-display_rotation 90 -i coded.mov -c
  copy`), which writes the matrix; a `-timecode` track beside it is a data stream with no codec name, the shape of an
  iPhone's `mebx` tracks. Both signs (`90` and `-90`) decode to the upright twin pixel for pixel, each from the coded
  frames turned the other way.
- Of 923 local videos only IMG_5611 carries a rotation flag or a `mebx` track (the scope's control table): uploads
  and releases strip them, so the drawn twins are the test, and the phone clip the only known answer.
- Ten of the fourteen reference cases carry the layers held-still no-power, so their first lines changed in
  wording. `share rerun` renders both the stored and the fresh case with the current code, so the reference
  `.mcdonald` files need no remake for a wording change; the exercise pages, quoted word for word, do.
- A track-length rule for "held in view" (so that the first line could say "as the camera held it" only for an
  object the camera followed) was tried and dropped: nothing in a case's fields separates a phone following the
  object over a blank sky from a sensor staring at a slow scene while the object drifts across, and a threshold at
  half the picture's side split PR135's flock between two wordings. One wording for every held-still case, naming
  both readings.
- The sheet spreads its tiles evenly over the pages (`per = ceil(n / pages / cols) * cols`), so two pages of 100
  frames are 50 and 50, not 80 and 20; the rule that matters is rows a page.

## Runs (Slurm, from each worktree)

- `phone`: `tools/suites.sbatch` 17896 and `tests/test_golden.py --exercises` 17897, with the clip's own check
  17898 (`analysis/cases/rhode_island_sound_2026/jobs/wp0_check.sbatch`). Results below, as they came in.
- `phone-wp8`: the new checks alone (17902: overlay gate and paging, with test_cli 133), test_audio (17903),
  test_reduction 563 and test_published (17904), and after the bump test_reduction, test_cli and test_published (17905).

### Results

- **`phone`** (fd01dc4, then 10d5b12): suites 17896, every suite green but one check of test_measurement, which was
  order-dependent -- the new clip test drew from the suite's shared random generator, and the tests run in name order,
  so the repeated-frame check later in the suite saw other noise (it passes alone on both trees); fixed in 10d5b12 by
  giving the test its own generator. gui 767 with the four portrait checks. Golden with the exercises 17897: **225
  PASS, 0 FAIL, 0 SKIP** in 1:39:45, every exercise page's quoted line matched, PR44's and PR135's with the new
  clause. The clip, 17898 (`wp0_check.sbatch`): run, layers, tether, symbology, integrity and look all exit 0; the
  header reads 1080x1920; `--fov 15` gives 4102 px/rad (71.6 px/deg); integrity records rotation 270 and the coded
  1920x1080 with an aac and five `mebx` streams; the first line reads "The object moved about 0.091° a second in the
  picture, as the camera held it (the picture behind it held still on screen, so its motion against the background is
  not measured) and is 21 pixels across (0.29°); …"; `run` peaked at 3.6 GB.
- **The merged tree** (`phone-wp8`, 8050f8a; 4718767 with main's ROADMAP commit): suites 17918 **ALL SUITES PASS** --
  measurement 552, reduction 563, published 32, tether 24, audio 62, cli 133, share 25, sweep 10, stabilize 13,
  aspect 10, waves 14, slew 65, zoom 31, horizon 25, focus 19, haze 9, streak 8, camera 151, gui 767 (1 SKIP, WxAgg
  not installed, as always). Golden with the exercises 17923: **225 PASS, 0 FAIL, 0 SKIP** in 1:34:36, PR113's page with the bands' clauses. The clip's WP8 stages, 17924:
  `symbology` says "no overlay: 0.00% of the picture stays drawn across the clip" and reads no frame (exit 5, no
  power); `audio --platform boat` reads the 33.76-Hz series first as the boat's own engine ("4 cylinders at 1013 rpm,
  6 cylinders at 675 rpm, 8 cylinders at 506 rpm") and the 405.17-Hz supply as "on a boat: an inverter's or a
  generator's", no clock; with no platform both readings are named.

## Left for Jacob

1. Merge `phone-wp8` into main: `git merge phone-wp8` (`phone` is behind it; the branch already holds main's
   ee1f512, so it is a fast-forward unless main moves again). Not done from this session because the main checkout
   held another session's uncommitted edits to CHANGELOG.md and README-technical.md, which this branch changes too,
   and merging would have run over that session's tree. The merged tree was verified as above, so no run is owed
   after the merge unless main moves in `src/` or `tests/` first.
2. The public step, as for 0.4.0 and refused to the session by the classifier: set the date in `__init__`,
   CITATION.cff and the CHANGELOG to the push day; `git tag -a v0.4.1`; push main and the tag; `gh release create
   v0.4.1`; the Zenodo version DOI into CITATION.cff.
3. Whether the fourteen reference case files are remade for the wording (decision 7's rule: additions and wording
   until 1.0 need no remake; the reruns pass as they are).

## Next, by the scope

- **0.4.2, WP1 and WP4:** `phone.py` reading the iPhone's `LivePhotoInfo` track with ffmpeg alone (`-map 0:4 -c copy
  -f data`: 872 records of 144 bytes; field 8 the zoom, fields 4-5 the camera shift), `<tag>_phone.csv`, the
  provenance flags, `scale` taking k from lens and zoom as "the phone's record", and `camera` taking the zoom curve.
  Each clip checks itself (the zoom field against the picture's scale, r 0.997 here); no public footage carries the
  track.
- **Then WP2 and WP3 proper:** the sky as a background (all pairs at each gap, the broad gradient out) and a held
  object found as one thing -- the case's 98 px/s against the clouds from `mcdonald run` alone.
