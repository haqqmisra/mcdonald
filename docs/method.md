# Video-forensics toolkit — background layers and clip integrity (method note)

Two questions come up on almost every PURSUE sensor clip, and both were first
answered by hand on DOW-UAP-PR144 (the `pr144_velocity_size` and
`pr144_integrity` workups). The tools below are those workups made independent
of the clip, and are the measurement core of this package.

| question | tool | needs |
|---|---|---|
| Everything below, in order, into one report | `mcdonald run` | the clip; a track for the object stages |
| How fast does the object move **against the background**, and is there one background? | `mcdonald layers` | the clip; a track for the object's rate |
| Does the scene move **under the sensor's pattern**, where `layers` holds it still? | `mcdonald scene` (`layers` runs it on such a clip by itself) | the clip |
| Has the clip been **altered**? Was the **object added**? | `mcdonald integrity` | the clip; a track for the object tests |
| Is the track on the object in **every frame**? | `mcdonald tracksheet` | the clip and the track(s) |
| Where is the boresight, and what is the sensor's azimuth? | `mcdonald symbology` | the clip |
| What does the motion permit in m/s -- and what is missing? | `mcdonald kinematics` | a track; k and R if they exist |
| Does the object move WITH the texture around it or THROUGH it? | `mcdonald comotion` | the clip, a track, the object's diameter |
| How many pixels is a degree, from the camera's own slew? | `mcdonald slew` | the pointer (`symbology`) and the scene (`layers`) |
| Where does the camera's field change, and by how much? | `mcdonald zoom` | the clip |
| shared routines | `mcdonald.forensics`, `.kinematics`, `.scale`, `.figures` | — |

```bash
# VIDEO is a path or a record id: PR144, DOW-UAP-PR144, 06:PR001
mcdonald layers PR144 --auto-track --validate --composite 800 \
        --names "striated=sea,isotropic=cloud tops" --dark-below 100 --mask-rows 985:1080:1:165
mcdonald integrity PR144 --track pr144/pr144_layers.csv --mask-rows 985:1080:1:165
mcdonald integrity FBI-UAP-PR005          # no track: record, container and scene only
mcdonald tracksheet PR144 --track pr144/pr144_layers.csv \
        --track pr144_wide_track.csv --compare pr144_track.csv   # every frame, object circled
```

`VIDEO` is a path to any video file, or a record id when a catalog is
configured (see the README). Frames are extracted losslessly to `--workdir`
(default under the system temp directory) with ffmpeg's 1-based numbering; `--n0/--n1` take a window of a long
clip and keep the absolute numbers. A full-rate run costs about a second per
frame pair on ten cores.

## 1. `mcdonald layers` — the background, layer by layer

**Why it exists.** On PR144 a single "rate against the background" (540 px/s)
turned out to be a blend: the sea and the cloud tops were moving 98 px/s apart,
and a consensus over patches followed whichever layer had more patches in each
frame pair. The object moved ≈ 650 px/s against the sea and ≈ 510 px/s against
the cloud. Layers at different ranges never move together when the platform
moves, so **name the layer whenever you quote a rate**.

**What it does.**
1. Masks what is not scene: redaction blocks (large, static, dark), symbology
   of any colour (coloured, or static and sharp), caption rows you name, and a
   disc about the tracked object.
2. Finds where each 128-px template of frame *a* sits in frame *a + k*
   (default k = 5) by zero-mean normalised cross-correlation over a wide
   search window.
3. Classes templates by the **anisotropy of the correlation peak**: striated
   texture (open sea: a peak 10–50× flatter along the wave crests) and
   isotropic texture (cloud, land). Each class gets its own consensus shift.
   It also counts motion groups regardless of texture, which flags two layers
   of the same texture.
4. Reports each layer's screen velocity, layer against layer (the parallax of
   own-ship motion seen against two ranges), and, with a track, the object's
   rate against each layer in 1-s windows of wall-clock time.
5. With a track, the object's rate against each layer in 1-s windows over
   the whole track, every second once (`over_track`): each k-frame pair of
   the track against the layer's velocity at that pair -- a running median of
   its readings over ±half a second, carried across the frames where it was
   not read. Its median is the report's rate against the background. The
   windows of the layer's own readings exist only where the background was
   read, and their median moved when a change read other stretches: PR44's
   bird, flying 20-40 px/s along a still background, was 21.8 px/s at
   f7f7fad and 28.0 at 82f6c13; over the whole track it is 32.3 and 32.6
   (session 12, 2026-10-30; its exercise page quotes 33). Not the net rate
   over the track (25.7 and 26.0 on PR44, the picture's line fit 25.3): PR135's
   relative motion turns back with the camera, and a net rate fell from 99 to
   8 px/s on a member whose every second read about a hundred. PR135, read
   along its whole track, is unchanged.

**Check the ruler first (`--validate`).** It shifts real frames by known
amounts and recovers them (bias), and compares 2k-frame shifts with the sum of
two k-frame shifts (chain consistency). On PR144: exact recovery, 0.2–0.6 %
chain error. `--composite N` writes red/cyan overlays of frames N and N + k
aligned on each layer; the other layer shows colour fringes, which is the
quickest way to convince yourself, or a council, that two layers are real.

**Reading the result.**
- The farther layer is the better stand-in for a fixed background, but it is
  not fixed either: if layer-against-layer is all own-ship parallax, the far
  layer itself moves at (layer rate) × f/(1 − f), f being the range ratio.
- For a **stationary** object the ratio (object vs far layer)/(near layer vs
  far layer) is free of the field of view and of the platform's speed, and
  the two motions are parallel. With heights above the surface,
  h_obj/(H − h_obj) = ratio × h_near/(H − h_near). PR144: ratio 6.6, 8° apart.
- Striated texture measures the component along the striations poorly
  (aperture problem). Trust the across-crest component and the consensus of
  many templates, not single templates. Since K9 (§31) each template carries
  its own error, and one as well matched a step along its streaks counts
  across them only.

**A pair whose templates do not agree is not held still (added 2026-11-13; IDEAS.md GL4).** A pair whose
templates, zero shift left out, reach no consensus is measured again over a second, and where that finds no motion
either it was "held still even over a second". PR058 showed what else ends there: a sea streaked along its own motion,
crossing the picture at 20 px a frame behind an object the sensor follows. Half its pairs (924 of 1,845) were held
still, in runs of two or three between pairs that read 110 px, and the report said the picture behind the object held
still beside a rate of 588 px/s that was against a moving sea. In such a pair nearly every template is matched
well (a peak near 0.9) 94-115 px along the streaks, the sea's own shift. But each is sure only across its streaks,
their places scatter along them by more than the 6 px a consensus allows, and the second pass looks over 30 frames,
where the sea has gone 600 px, far past its 245-px search: "nothing found" was written down as "still". Nothing in
such a pair sits at zero: with zero allowed, 1-9 of its 36-42 templates do.

So a pair is held where its templates match at no shift, not where they fail to agree on one. Each pair the first pass
calls held keeps its own field in numbers (`layers.own_field`, in the cache beside the templates: the cache's key
moved): the templates placed, those matched well (a peak of 0.5 or more, `forensics.PK_MIN`), and how many of those lie
more than 5 px along their own median shift, on its side of zero (5 px: the most a held pair's shift is kept at). A
pair left STILL by both passes with more than half its templates there, of 8 or more placed (`LOST_AWAY`, `LOST_FEW`),
is LOST: the scene moved and the pair was not read. It has no shift in `<tag>_layers.csv` (a row of blanks, as any pair
with no consensus), it is not counted as held (`held_still.not_read_share`, only where there are such pairs), and a
rate is carried across it as across any unread pair. One side of zero, because a still scene of long streaks, or
stripes on the sensor, scatters its matches along the streaks either side of zero, and neither side is a majority (a
drawn field in `tests/test_measurement.py`: 36 of 40 templates past 5 px, 19 on the median's side).

*The null.* The five Galileo still cameras, every pair (5,213 left STILL, 8 templates or more): the share is 0.037
in the median, 0.075 at the 99th centile and **0.102 at the most; none reaches a half** (under 0.06 % a pair at 95 %).
PR058's 930 STILL pairs: 0.73 in the median, 0.87 at the 90th centile; 834 are LOST (726 at a cut of 0.6). On the 31
objects of the 14 reference case files (11,948 STILL pairs): **11 are LOST**, ten on PR088 object 2 (their templates
87 px along, where its blocks read 11-33 px a frame: the scene) and one of PR113's 56 (0.507: not looked at). A scene
that moves under a pattern fixed on the sensor reaches 0.2-0.4 (PR077, PR079, PR097, PR099, PR41, PR44): some templates
see the scene, the pattern holds the rest, and its pairs stay STILL, for the blocks to read (§41). The half is "most of
its templates", the level a choice; the null says how far a held pair stays under it.

*PR058 after it.* Held still in 5 % of pairs, not read in 45 %, no NO POWER; over the whole track 620 px/s against
the background (16-84 %: 547-654; it was 588, 353-642, with the false zeros in), the layer read on 51 % of it, and
the report's first line is "The object moved about 620 pixels a second against the background." A golden holds ten
seconds of it (`tests/test_golden.py`: 37 % of pairs not read, none still, the sea at 578 px/s). *Drawn*
(`tests/test_measurement.py`): a sea of streaks 250 px long, smeared along its motion, crossing 20 px a frame under
noise nearly as strong as its texture. The first pass loses 34 of 65 pairs, every one with all its templates matched
well on one side, at 100 px in the median; without the rule 40 % of pairs are still over a second, with it none are
and 40 % are not read. A rigid drawn sea with little noise is read on every pair, and still streaks keep a share of
0.03 at the most. *What it is not.* It
does not read those pairs: the scatter along the streaks is the measurement's limit there (a consensus with a wider
reach along a ridge would, and would change every clip's numbers: not done). A pair the second pass read (AGAIN), or
one between a repeating picture's catch-ups (UNMOVED), keeps its reading. And a scene too fast for the search (over
`--max-shift`, 45 px a frame) leaves no well matched template anywhere: such a pair is STILL, as it was.

## 2. `mcdonald integrity` — altered? added?

**What it can and cannot show.** It shows whether the clip and the object
behave like the output of one sensor chain. It catches an object pasted,
AI-inserted or animated onto footage that already existed. It cannot exclude
a composite made upstream of the symbology by someone who modelled exposure,
shake, gain and parallax. Nothing in the pixels can; that is a custody
question (original recording with metadata, mission report). Say so whenever
the result is quoted.

**The record.** The release's own words come first: 15 of the 144 videos carry
"digitally altered before being reported" or "digital recreation", and one
states that nothing was altered. The container is reported too, but a release
transcode (AWS Elemental, fresh creation date) says nothing about the source.

**Is this a sensor's output?** Generated video carries no sensor chain. The
tool looks for repeated frames and their catch-up double steps; contrast
transients (flat fields, gain resets, zoom blanks) and the zoom ratio across
them; a static detector pattern (split-half between alternate blocks of frames
in which the scene sweeps the detector); and rigid scene motion in one or two
groups.

**Was the object added?** Each test asks whether the object behaves as imagery
or as something laid over it.

| test | imagery | an overlay | loses power when |
|---|---|---|---|
| cadence | frozen on repeated frames, doubled on catch-up steps | moves through repeats | the clip has no repeats |
| transient | attenuated with the scene; symbology is not | full strength | no transient inside the track |
| layer order | symbology keeps its colour over it; it enters from under a block or at the frame edge | paints over the symbology; appears in the open | it never crosses symbology |
| smear | stretched along its screen velocity ∝ screen speed | same shape at every speed | speed spans < 6 px/frame; very short exposures |
| shake | screen acceleration follows the background's with unit slope | follows its own smooth path | steady camera; slow or textureless background |
| halo | sharpening ring deepens with its amplitude | fixed ring | always saturated; no ring |
| static pattern | detector pattern continues under its footprint | a hole in the pattern | the pattern is weak where the object goes |

Verdicts are PASS, FLAG, INCONCLUSIVE and NO POWER. **Report NO POWER tests;
do not drop them.** A clip that cannot decide a test has not passed it.

**The self-test is what gives a PASS its meaning.** By default the tool
animates a synthetic disc on a smooth path over the same frames (on top of the
symbology, full strength through transients, moving through repeats, never
smeared, fixed ring, its surroundings regenerated smooth as generative fill
would leave them, and routed through the measurable part of the detector's
static pattern when there is one) and runs the same tests on it. The insert should fail
where the real object passes. If it passes too, that test has no
discriminating power on this clip, whatever its verdict says.

**Two readings that need care.**
- *Shake.* Both accelerations carry measurement noise, so neither regression
  slope is 1 even when the truth is. With similar noise in both, unit slope
  gives slopes of r and 1/r; check that they straddle 1. The verdict is the
  axis of the larger sigma (`best`, `r`, `sigma`). Every number the sentence
  prints is a field as well (since 2026-11-13): `r_x`, `sigma_x`, `slope_x`
  (the object's acceleration fitted on the background's), `slope_inverse_x`
  (one over the background's fitted on the object's; `null` where the
  sentence says inf, r within 0.05 of zero), the same four for y, and
  `frames`, the N; the made-up disc's shake test keeps them too
  (`selftest.shake`). The inverse slope at r near zero is a quotient by
  almost nothing: on PR135's objects 1, 2 and 4 it printed "-646.24" on one
  computer and "-646.25" on another, with no field to hold the sentence to.
  A trap that stays: a case made on one CPU and rerun on another can still
  differ there by more than the one part in a billion a rerun allows; now a
  number says by how much, where before only a sentence differed.
- *Smear.* No smear is INCONCLUSIVE, not a FLAG: a millisecond exposure shows
  none either. Smear that scales with speed is the informative outcome.

## 3. Traps built into the library (each cost a wrong number once)

- **Zero-shift lock.** Sensor fixed-pattern noise, codec blocking and
  symbology all correlate at zero shift. The library excludes a zone about
  zero and **drops peaks on the rim of that zone**, which are not verified
  maxima (they showed up as layers pinned at ±5.49 px).
- **A scene held still on screen** is the opposite case: its true peak lies
  inside the excluded zone, and what remains are chance peaks hundreds of
  pixels away. `shift_field_auto` checks the same-position correlation first
  and allows zero shift when the scene has not moved. It says so, because a
  static pattern can then lock the estimate.
- **A picture that repeats and catches up** (2026-10-28, PR051's upload): the
  same picture again, with new capture noise, for a few frames, then a step of
  tens of pixels. A pair inside a hold is held still, and measured again over
  a second (as a slow scene must be, PR135's island) it took the second's
  mean rate, so the catch-ups were counted twice. A one-step sub-pixel test
  cannot tell the two apart (a fixed pattern swallows a slow drift: PR135's
  1.6 px over 5 frames read 0.04-0.07, PR051's holds 0.04-0.09); the order of
  the pairs can. Where a window's held pairs and catch-ups (12 px or more
  over k frames) alternate at least four times, with under a third of its
  pairs in between, a held pair whose own field agrees on zero is
  **unmoved**: zero, not measured again (`layers.repeating`, how `UNMOVED`).
  A slow scene has no catch-ups, a slew starting or stopping switches once,
  and a catch-up whose match failed does not agree on zero: all three are
  measured again as before. On a drawn picture held 8 frames, then 30 px on,
  the chain came to 204 px of 210 with the rule and 312 without it.
- **Window bias.** Same-position windowed cross-correlation under-reads a
  20-px shift by 1–3 % per pair (overlap taper). Whole-template search has no
  taper.
- **Cadence.** Many clips repeat ~7 % of their frames and catch up with a
  double step a few frames later. Rates are means over ≥ 1 s of wall-clock
  time, never per-frame differences.
- **Halo swallowed by the block mask.** Masking every pixel below 10 DN as
  redaction takes the dark sharpening halo of a bright object over a dark sea
  with it, and the tracker loses the object. Blocks are large, static and
  black (0–1 DN); a night sky is merely dark.
- **Symbology comes in every colour and opacity.** Coloured symbology is found
  by chroma, but only in a grey clip: in a colour clip the colour is the
  scene. White symbology is static and sharp, but so is scenery when the
  camera holds still. Dark, semi-transparent symbology (PR148's reticle)
  varies by 3–6 DN as the sea passes under it, so a variance test misses it.
  What works: the temporal median of frames in which the scene sweeps smooths
  the scene away, and whatever is still sharp in it is symbology
  (`refine_graphics`).
- **A tinted grey picture is not in colour, and its tint is not symbology.**
  PR051's upload (2026-10-28) carries 46–54 DN of chroma on the terrain's
  bright band — a colour balance off somewhere in its analog chain or its
  re-encoding — on 18.7 % of the frame, just under the fifth that calls a
  clip colour. The chroma masks (the static one, and each frame's own) then
  took half the picture, and the sharp parts first: `layers` kept 29
  templates of 85 a pair, and lost most of the catch-up steps of §31. The
  cast of a tint follows the picture's own brightness, so most of the
  brightest fifth of the sampled frames carries it (`static_masks`:
  `tinted`, `TINT_FIFTH`, `TINT_SHARE`); symbology in colour is a few per
  cent of the frame and cannot be. A tinted clip keeps its static-and-sharp
  mask for white symbology and is not masked by chroma at all.
- **A "static detector pattern" that is really the scene.** The temporal mean
  of high-passed frames keeps whatever does not move. Use only frames in which
  the scene sweeps the detector (≥ 3 px/frame). Split the frames by alternate
  25-frame blocks, not odd/even: a striated sea moving along its striations
  leaks into odd and even frames alike (PR148: split-half r fell from 0.99 to
  0.41 with both fixes). For the test under the object, take the pattern from
  the other half of the clip.
- **Corner brackets.** They mark the *next narrower* field of view. They are
  not a fixed angle and do not grow by the zoom ratio. The zoom is fitted from
  the imagery (PR144: ×5.9, where the brackets had been read as ×2.97): by
  `zoom_ratio()` until 2026-10-27 (a small template, a wide search and a gentle
  high-pass, because sea texture decorrelates in ~0.3 s), by `zoom_fit()` since
  (§17's zoom states).
- **"Flat field" frames are not always a shutter.** On PR144 they kept the
  scene at 1/13–1/24 of its contrast; measure before calling them blank.
- **Verify what the tracker locked onto.** `--auto-track` writes a strip of
  crops along the track, and `mcdonald tracksheet` tiles every frame with the
  position circled and the pixels there inset. Look at them. On PR144 the first tracker spent seven
  frames on a cloud feature 100 px from the object, and a noisy detector zone
  can out-score the object in a matched filter (the linker picks by position,
  so keep many candidates).
- **A thing drawn out along its path.** A small thing crossing 20 px a frame is
  smeared into a dash by the exposure (PR43); the motion proposer sees it, and no
  spot filter does -- nor a line-shaped one, among the ground's own lines: only its
  motion separates it from the ground. The linker then follows the marks' motion,
  frame less the median of its registered neighbours, and says so ("followed by
  its motion, not as a spot"). Its speed across the frame need not be uniform,
  and the report says when the fit is not. The search round each prediction runs back
  past the last position, as it must (a repeated frame stands still), so a peak behind
  a fast thing can be taken: PR43's frame 75, a faint blob 9 px behind frame 74's
  position after the dash had left the picture, the one point that set that track's
  jitter at 8 px and its T at 0.91 s. On a thing expected to move 4 of its own widths or
  more, a peak half a width or more behind its last position is now not the thing
  (`autolink.went_back`). Both numbers come from 1,414 drawn dashes followed with the rule
  off: a real step is refused on 0.28 % of tracks, under 0.63 % at 95 %, and on dashes that
  really brake or turn at PR43's scale it costs 1 frame of 1,719. It catches the clear case
  only: of residues planted behind a last dash, mostly at 2.6 widths and 0.3 behind and so
  among real steps, it refuses 4 %, and a false point ahead of the last position it does not
  look at. Of real tracks PR43 is the only one that reaches this way by itself; ten others
  forced through it from marks on them lost no recorded point.
- **Curated partial tracks.** "First / last seen in the open" is
  INCONCLUSIVE by design when the track covers only part of the object's time
  on screen. Look at the frames before and after.
- **Save the check.** An "independent check" done in a throwaway heredoc once
  agreed with a wrong number and could not be audited afterwards.

## 4. Validation of the generic tools (2026-09-19)

| clip | why | `mcdonald layers` | `mcdonald integrity` |
|---|---|---|---|
| **PR144** (the hand workup the tools came from; bright 9-px object, orange symbology, sea + cloud) | must reproduce `pr144_velocity_size.md` and `pr144_integrity.md` | object vs sea **648** px/s (605–689), vs cloud tops **510** (497–536), cloud vs sea **98** (94–101), ratio 6.2, 8° apart; hand: 648 / 510 / 98 / 6.6 / 8°. Known shifts recovered exactly; chain error 0.2–0.6 %. Texture-blind check: two motion groups in 35 % of pairs, 97 px/s apart | cadence, transient, layer order ×2, smear (0.48 × speed, r = +0.98), shake (y: r = +0.35, 7.5σ, N = 409), halo: **PASS**; static pattern: NO POWER. Zoom ×5.8 (ZNCC 0.92), no repointing; second transient ×1.00, scene swept 282 px. **Synthetic insert: FLAG** on cadence (2.7 px across repeats), transient (kept 0.51 against the scene's 0.06) and static pattern (0.07 against 0.94 DN² beside it, 141 frames); INCONCLUSIVE on smear (0.02 × speed) and shake (r ≤ +0.12) |
| **PR148** (never seen by these tools; **dark** 7-px object, dark semi-transparent symbology, 1908×1028, sea held still for 11 s, then a slew) | generality | object vs sea **199** px/s (190–211); hand: 209.8 px/s at t = 5–11 s. One layer, as expected | cadence **PASS** (0.000 px across 17 repeats; insert 6.7 px, FLAG). Everything else NO POWER or INCONCLUSIVE, and said so: no transient, never crosses symbology, a curated partial track, scattered smear (r = +0.10), only 48 frames for shake because the scene is still half the time |
| **FBI-UAP-PR005** (disclosed digital recreation; colour, 0.8 Mb/s) | what the scene tests make of generated video | — | the disclosure is quoted. Scene still in 97 % of pairs, 41 repeats with no catch-up steps, no transients, no static pattern measurable. **A still animation gives the pixel tests nothing to work with; here the record identifies it, not the pixels** |

What the validation does not show: a clip in which a real insert was caught.
The corpus has none that is known. The synthetic insert stands in for it, and
it models a naive overlay plus a regenerated surround, not a match-moved,
physically modelled composite.


## 5. The reduction (added 0.2)

### `mcdonald symbology` — the overlay is an instrument

Three quantities are drawn in the open on clips whose telemetry is redacted.

**The boresight** is the origin every other screen measurement should be
referenced to. Three routes, because the overlays differ: the coloured ticks
nearest frame centre (chroma); a gradient-magnitude template matched
independently every frame (monochrome overlays — never chain frame to frame,
the codec redraws the strokes and a walk drifts off); or, when the reticle is
a periodic tick train, a Radon-style line fit. **Phase correlation fails on a
tick train** — it aliases onto the tick spacing and returns nonsense — and NCC
of a large patch saturates. The line fit is absolute per frame, so nothing
accumulates.

**The north pointer** gives the sensor azimuth. It is drawn at a radius fixed
within a clip to a few tenths of a percent, which is both what makes the angle
trustworthy and the check on it: *a radius that wanders means the glyph was
mislocated, and the angles are then worthless.* The tool prints the radius
scatter for exactly that reason and warns above 2 %.

**Not always about the boresight (added 2026-10-28).** On PR062 (MTS-B,
2021/04/12) the cyan "N" sweeps 136° and its radius about the reticle ran
from 206 to 191 px as it turned: the stage called the frames mislocated, and
the angles were up to 3° off. The glyph had been found every time; it circles
(644.7, 366.0), 8.6 px from the reticle, at 199.9 px with a residual of
0.58 px. Where the glyph sweeps 60° or more (the span holding 96 % of the
glyphs), the circle it draws is fitted (`symbology.pointer_centre`: a robust
least-squares circle, glyphs over 4 px off it dropped as mislocated), and if
its centre is over 1.5 px from the boresight with a residual under 1.5 px the
angles and radii are read about it, and the report says so. A clip of the same
display whose pointer sweeps too little to fit (PR063, 25°) takes the centre
with `--pointer-centre X,Y`. Rendered (`tests/test_reduction.py`): a circle
8.6 px off the boresight, 0.3 px of scatter and one glyph in twenty
mislocated, found to a fifth of a pixel; a sweep of 25° fits nothing.

**The pointer's colour, and a reticle that shows three of its four ticks (added 2026-11-13; IDEAS.md GL5).**
PR058 draws a magenta "N", plain to the eye, that `--method hue` read on no frame and `auto` never reached. Two causes,
both seen on the pixels. (1) `hue_glyphs` kept pixels with red over blue by 60 levels, PR144's orange; a magenta glyph
has as much blue as red (R 182, G 108, B 169), and of the 64-120 of its pixels saturated enough, none passed, on any
frame. Not its saturation after the codec (a chroma of 71-91 against the 70 asked), not its size (14 x 16 px). The hue
method now reads the colour off the frames where no warm glyph shows on any of 20 frames spread over the clip
(`glyph_hue`): the largest glyph-sized patch of saturated colour in each, the hue most of them share (within 30 deg,
on half the frames or more), and glyphs within 30 deg of it (`HUE_WIDTH`: PR058's "N" keeps nine in ten of its pixels
within 9 deg of its own hue, the worst of 565 frames 23, and the hue itself moves 298-319 deg from frame to frame).
A warm glyph is read as before, to the byte (PR144, PR057a). (2) The boresight was the mean of the four coloured
glyphs nearest the middle of the picture, taken to be the reticle's ticks. PR058's reticle shows two to four of its
four (of 615 frames: one on 1, two on 99, three on 251, four on 264; the upright ticks are 2 px wide and their colour,
kept at half the picture's resolution, does not always survive), and the fourth nearest glyph is then the pointer
itself, 195 px out: a boresight at (650.6, 306.8) for (640.5, 359.5), about which the pointer's turn would have read
39 % fast, and a chroma method that had taken the pointer for a tick and had none left to find. Now: where some of the
four nearest lie beyond a fifth of the frame's height from the middle (`RETICLE_WITHIN`, the inner edge of the ring
the pointer is looked for in) and the two or three that do not are ticks of one reticle by themselves (`_crossing`:
each wider than tall beside the crossing or taller than wide above or below it, the ticks of one bar on its line and
an opposite pair's midpoint on the other bar's tick, within 0.6 % of the frame's height), those are the ticks and
the boresight is where they cross; anywhere else the four nearest stand, as before. The tolerances are the
drawing's, not levels from a null.

*PR058, frames 10506-12350, every third* (`mcdonald symbology`, as `run` asks it): boresight (640.5, 359.5); by chroma
613 of 615 frames, radius 195.16 +- 0.55 px (0.28 %), **+0.200 deg/s**, residual 0.22 deg; by hue 565 of 615, the hue
found at 304 deg, radius 195.08 +- 0.70, +0.199 deg/s. Two frames read by eye in the session that found it gave
0.19 deg/s, and a note of 2026-10-14 0.17 over 88 s. *Held on the pointer clips* (the first 3,000 frames of the long
ones, every third, old code and new): PR43, PR48, PR149 and PR27 the same to the byte by chroma, PR144 and PR057a by
hue; every frame chroma read before is read at the same place, and one or two more a clip are read where a tick was
missing (PR144 277 -> 279 of 279, PR057a 658 -> 660, PR060 999 -> 1,000, PR061 976 -> 977). The reference case PR41
had its pointer on half its frames for PR058's reason: 134 -> 259 of 266, -0.413 -> -0.409 deg/s. And hue reads five
pointers it read on no frame, agreeing with chroma where chroma's radius holds: PR43 (cyan, hue 179: 306.32 px against
306.27), PR48 (magenta, 301: -0.1422 deg/s against -0.1428), PR27 (178: +0.3169 against +0.3157), and PR060 and PR061
(182, 188: radius +- 1.10 and +- 0.59 px, +0.61 and +0.83 deg/s, where chroma's radius wanders 4-19 % and the stage
says its angles are unreliable). Drawn (`tests/test_reduction.py`): PR058's display through the codec, a magenta "N" of
10 x 12 to 20 x 24 px on a dark and a bright scene, found by its own hue to a pixel and by the warm test on no frame;
a reticle of three ticks to half a pixel where the mean of the four nearest is 36 px off. *What it is not.* PR149's
magenta "N" is still read by chroma alone (hue: no frame, before and after; not looked into). **PR141's "pointer" is
no pointer** (found here, not fixed): the chroma method's glyphs sit at four fixed places 240-278 px from the
boresight, and the circle fit of 2026-10-28 draws a circle 75-94 px off it through them, dropping over half the
glyphs; its released reports give -9.9 and -5.0 deg/s for two objects on the same frames, and so does this code
(a first cut of the reticle rule moved them; the one built does not). Both are fictitious; a fit that drops most of
its glyphs wants refusing, with a null (IDEAS.md GL8).

Pointing is therefore **not withheld** on any clip that draws a pointer,
whatever a redaction tag says. Measured radii: PR144 310.9 ± 0.9 px, PR148
295.3 ± 0.6, PR149 291.5 ± 0.7 — 0.2–0.3 % each.

Sign convention, and what it buys: **theta is clockwise from screen-up**, so
theta = −azimuth. `d(theta)/dt > 0` means the platform moves toward
image-right across the line of sight, and a stationary object nearer than the
background then drifts image-left. Motion directions from `kinematics` and
`comotion` use the same convention, so `symbology.true_bearing` differences
them into a bearing. It is still an image-plane bearing: a ground bearing also
needs the depression angle, because the down-range axis is compressed by
sin(depression).

**The corner brackets** are read only for the box they mark. PR149's is
959 × 540 px, exactly half of 1920 × 1080, which is how its 1028-row release
was identified as a crop of a 1080-line original. The detector requires a
genuinely symmetric set of four about the boresight; without that test the
north pointer (glyph-sized, and *nearer* the boresight than the brackets) gets
picked up and a box that was never drawn comes out.

### `mcdonald kinematics` — bounds, not speeds

Three scalar equations:

    omega = v_px f / k        omega R = |v_obj - v_own| sin(theta)
    k = f_px sec^2(alpha),    f_px = (W/2) / tan(FOV/2)

v_px, f and W come from the clip. **k, R, Rdot and v_own do not**, and the
module refuses to produce a speed while any is missing — it names them
instead. `--ladder` prints what each candidate field of view would imply;
across 3–54° the answer spans a factor of ~65, which is the argument for not
picking one.

Three traps it enforces:

- **A detection file is not a track.** The fit is sigma-clipped. On PR142's
  raw file — which contains a frame-period echo train and terrain false
  positives — clipping alone recovers the published 560.9 px/s by dropping 34
  of 131 rows. Without it: 273 px/s, wrong by a factor of two.
- **Motion that is not uniform has no single v_px.** `resid_rms` is compared
  with the distance covered, and above 5 % the reduction marks itself NOT
  UNIFORM and refuses to let derived speeds pass quietly. PR144 fails this at
  19 % — correctly, because its object is held in the field of view while the
  camera pans, so its meaningful rate is against the *background*, which is
  what `layers` measures.
- **Rates are fitted against wall-clock time**, never per-frame differences.
  With a repeat every seventh frame, 13 % of per-frame readings say the object
  is stationary and 13 % say it is moving at twice its rate; the fit against
  time is unaffected.

Two routes escape k entirely and are worth more than a better guess at it. An
**in-frame object of known size**: the field of view cancels and only the
*ratio of ranges* survives, which the clip cannot supply — so the result is a
ceiling (PR149: 192–255 kn on a 150–200 m hull). And the object's **own
size**: v_px / h_px is its speed in body-lengths per second, free of k, R and
FOV together, because numerator and denominator scale alike with range — but
not of the camera's own motion (B7, 2026-11-02): a thing still in the air at
range R, seen from a camera moving at v_own, crosses the picture at
v_own sin φ / R while its size is D / R, so the row reads v_own sin φ / D for it,
and a 1-m thing seen from an aircraft at 100 m/s scores up to 100 lengths a
second standing still (PR135's "28.6 body-lengths/s" is 212 px/s over 7.4 px,
the 212 px/s that `parallax` and the paper read as the aircraft's). It is the
object's own speed only where the camera does not move through the air, or
the rate is against a scene at the object's own depth; the row says so, and
is NO POWER where the camera's speed is given or the layers step saw the
background move, and where the picture behind the object held still on screen
(a camera following it looks so: `stages.platform_of`).

### `mcdonald comotion` — with the field, or through it?

A different question from `layers`. There the background moves as one; here it
is a *field* — cloud, sea, dust — whose parts move differently, and the
question is local: relative to the texture immediately around it, is the
object carried or does it cross? A balloon holds station in a drifting cloud
field. An object covering tens of its own diameters relative to that field
does not.

The answer needs **no field of view and no range**, being in units of the
object's diameter D. Three things make it honest: object and field are
measured over *the same frame pairs*, so an irregular hold cadence cancels;
the field comes from an *annulus* around the object with a disc about it
excluded, because a cloud field shears across the frame; and the annulus
radius is *swept*, because it is an arbitrary choice and a result that depends
on it is not a result. The annulus's flow is its patches' mean weighed by
each patch's own error (§31), where that lands within 3 px of their median,
with the error beside it (`err` in `local_flow`'s result).

Validated on PR055 (a sphere over Afghanistan, in and out of cloud): 18.1 D of
relative motion in 7.33 s against a hand workup's ~20 D in 7.7 s, leg rates
3.55 vs 3.41 D/s. Same verdict, MOVES THROUGH.

One caution the tool prints for itself: the registration excludes a zone about
zero shift, so if the field has moved only a few pixels over the chosen
baseline the flow term is unreliable. Raise the baseline until it has moved
clear.

### The gate

`run` builds a track sheet and treats examining it as a prerequisite. Without
`--i-looked` every object measurement is stamped provisional. There is no flag
that skips building it. On PR144 the first automatic tracker spent seven
frames on a cloud feature 100 px from the object and returned a clean, wrong
rate; the sheet is how that is caught.

## 6. `mcdonald tether` — a hanging point is a clock (added 2026-10-07; the follower, its gate and the swing's null set again in 0.5.2, 2026-11-10)

A sounding balloon carries its radiosonde 25–55 m below it; a hobby balloon a few grams
a metre or two below; the Lake Huron object of 2023-02-12 (PR071) had, in the pilots'
words, "strings hanging off". A hanging point is a pendulum, and its period is set by
gravity and the line alone: T = 2π√(L/g). Read T off the video in seconds and L is in
metres with no range and no field of view — the balloon analogue of PR135's wingbeat,
and the one signature in the sky that nothing but a tethered payload has.

**Does anything move with the object?** Every frame, overlay masked, shifted so the
tracked position lands at the centre, and averaged. A feature tied to the object adds up
at its offset; the scene and the overlay smear by however far the object moved on the
screen. A candidate is a compact feature of that stack, 5 times its noise, in the ring
from the object's own footprint (its extent plus 12 px, or 1.2 object sizes) out to 40
object sizes. Three tests then say what it is (`tether.judge`):

1. *The control.* The same frames stacked on the track run backwards in time have the
   same set of positions and the wrong one each frame. A feature tied to the object
   smears there; whatever only looked sharp because the object hardly moved stays
   sharp. On PR055 the two residual peaks of the first stack reappeared in the control
   identically — they were the frame's edges. The control shows at most 0.6 of the
   candidate's strength.
2. *Frame by frame.* The candidate is found again on the frames themselves
   (`tether.Follower`). A stretch starts where the stack put the candidate: at the
   strongest compact feature of its polarity within 12 px of the stack's offset, 5 times
   the frame's own noise and at least half as strong as the stack's feature. After that
   the feature nearest to where it was last seen is taken, within 12 px of it, and never
   farther from the stack's offset than 0.75 of the candidate's distance from the object
   (its leash) nor nearer the object than the ring's inner edge. Unseen for 5 frames, the
   stretch ends and the next starts at the stack's offset again. The frames are gone
   through twice, in order and in reverse, each a follower of its own; where the two hold
   different features the one followed for longer is kept and, where both were followed
   about as long, the one nearer the stack's offset. A companion is **held**: it lies in
   stretches of 45 frames or more on at least 0.3 of the track's frames (on a track
   shorter than 45 frames, in a stretch nearly as long as the track), along a path
   smooth to 1.5 px (how far each place lies from the line between its neighbours: a
   swing's motion drops out, noise does not).
3. *With the object, the scene or the screen.* The re-found place against the object is
   regressed on the scene's place against the object (the background's own shift, by
   phase correlation) and on the screen's, each stretch about its own mean. A feature
   tied to the object makes none of either motion; a piece of cloud drifting past makes
   all of the scene's; a mark the display or the sensor leaves makes all of the
   screen's. Half or more of either, where it moved 20 px or more, and the candidate is
   not the object's. Places are regressed and not the steps between frames: a step of
   the companion against the object and a step of the scene against the object carry
   the same error of the track, which alone made a drawn companion, tied exactly, 0.7
   of a scene that hardly moved.

The overlay's thin bright strokes (reticle arms, a tracking gate's box, brackets) are
masked before any of this, by a morphological opening: a tracking gate *is* tied to the
object — by the tracker, late — and its edges passed every test on PR071 until they
were masked.

**Does it swing?** Asked of the companion alone, on the frames that show it. Its
separation vector from the object gives the swing angle, which needs no scale and
survives any camera motion short of a roll. Repeated frames are left out. A
Lomb–Scargle periodogram starts it, but the estimator is a sinusoid with a drift fitted
to the angle: on a window of a few cycles a periodogram's peak slides up to whatever cap
the window sets, and a peak at the longest period asked is never a period. The period's
error is a block bootstrap of the fit's residuals (they are correlated frame to frame;
single draws would say the period is known to a thousandth). A swing is claimed from 2
cycles of the window and reported as tentative from 1.5 — and only where the period
beats a slow wander (`tether.wander_null`, below).

**Validation** (`docs/tether-validation.md`, with the stage's own figure of each):
- WA9ONY-5, a 13 g pico payload under a mylar balloon, 2021-07-13, filmed at 1080p30
  for 4.3 s of free flight; the builder's own assembly video says "a little over one
  metre of cable" to the balloon. The payload is re-found on all 130 frames, in one
  stretch, to 0.4 px. The swing: 2.58 ± 0.02 s, amplitude 12.8°, 1.7 cycles (tentative) →
  1.66 ± 0.03 m; no drawn wander of 2,000 is as strong. The pivot of a balloon's pendulum is
  the balloon's centre, not its neck (its inertia is mostly the air it displaces), so the
  pendulum is the line plus the balloon's radius plus the payload's own offset ≈ 1.5 m.
  Consistent; the error quoted is statistical, and the 1.7 cycles are why it is
  tentative.
- PR071: a dark line 1.6 object sizes below the object, 14° left of
  straight down, re-found on 92 % of the frames to 0.5 px; over 7.9 s it holds
  −14 ± 3.6°. No swing, so no length: a line held by drag, or stiff.
- PR055: the stack's features are cloud streaks; re-found, they make 0.84 to 0.94 of
  the clouds' motion against the sphere. Nothing tied.

### What 0.5.2 changed, and what it was set from (2026-11-10)

Session 19 ran the stage as released (0.5.1) on AARO's known cases, on the reference case
files and on three PURSUE clips with something under the object, and found four
defects (IDEAS.md, H1–H4). Two of them had put a pendulum that was noise into released
reference reports.

- **H1, the follower left the companion.** After each frame the gate moved to whatever
  it had last found, the strongest feature in a gate a quarter of the separation wide;
  a candidate that passed the stack's tests and moved "smoothly" became the companion
  whatever its angle did; and a refused candidate's swing stayed in the record. On
  PR105 the follower went with the scene, 14 to 1,290 px from the object, and reported
  "steady to ±18.8°". On PR077 object 1 it went round the object through 320° ("a
  pendulum of 9.71 m", tentative), on PR135 object 2 through 150° ("2.52 m"): both are
  birds of the bird paper's Table 1, and both sentences were in their reference
  reports. PR149's record held `swings: true`, 0.159 m, beside "nothing tied to the
  object". The follower above replaces it: it starts where the stack put the candidate,
  cannot leave its leash, counts the companion only where it is seen, and the swing is
  asked of the companion alone.
- **H2, a period with no null.** An angle that only wanders shows a cycle or two in a
  short window most of the time. The wander null: the angle is put in 60 bins of its
  span (wider where a bin would hold under 3.5 samples; medians), a line is taken out,
  and its strongest Lomb–Scargle power between 4 bins and two thirds of the span is
  ranked among the same statistic on 2,000 Ornstein–Uhlenbeck series of the same
  variance and the same correlation between neighbouring bins, drawn at the same bin
  times. **Its rate was measured before it was stated**, on drawn wanders
  (`tools/tether_wander_rate.py`: 57 kinds, 31,867 series —
  correlation times of 0.1 to 3 s over 4.3, 10 and 32 s at 30 frames a second, with and
  without reading noise, seen on every frame or on 40 % of them in stretches, random
  walks, and two wanders at once). The cycles rule alone calls a swing in 0 to 78 % of
  them (29 % at the median; over a tenth in 43 of the 57 kinds). With the null beside it
  at p ≤ 0.01, the proposal, the whole rule still calls one in up to 3.3 % (above 1 % in
  20 kinds): the p is not exact, because the wander's correlation is read off the series
  itself and only series the cycles rule has already picked are asked. At **p ≤ 0.001**
  (`WANDER_P`: at most 2 of the 2,000 draws as strong) the whole rule calls a swing in
  **1 in 100 drawn wanders at the worst** (0 to 1.0 % by kind, 41 of the 31,867 in all).
  That is the threshold. What it costs: a pendulum four times the wander's size is
  still found in 84 to 100 % of drawn series, one twice its size in 2 to 75 %, one of
  the wander's own size in 0 to 11 %. A series too sparse to read the wander's
  correlation (273 of the 9,407 periods the cycles rule called) is refused, and the
  finding says so.
- **H3, companions that were scene or symbology.** 11 of 45 AARO tracks got a
  "companion" 112 to 760 px away, and PR29 "a pendulum of 0.65 ± 0.01 m" from a feature
  277 px away on 8 % of frames. They came in by a rule that kept any strong feature the
  follower could follow "smoothly", and smoothness was a share of the separation: far
  out, a jump of tens of px passed. **The gate was set against a null**
  (`tools/tether_null.py`): each of 80 recorded tracks, 19,941 frames — AARO's 45,
  29 of the 31 reference objects (PR113's track of 4 frames and PR43's of 24 are under
  the 30 the null asks), WA9ONY-5, PR071, PR055, PR105, PR28 and PR29 — run again on
  two tracks that nothing in the picture keeps step with, its own track run backwards
  in time and its own track shifted by half its length, with the same ring searched.
  A feature a null track "finds" that is the real object, or what the real track's own
  run followed with it, is not counted (52 of the features the null tracks followed).
  The known companions are WA9ONY-5's payload, PR071's string, PR105's lower point and
  PR-004's on each of its eight tracks. The released stage on the same null is the
  first row:

  | the gate | real tracks given a companion (of 80) | known companions kept (of 11) | null tracks given a false companion (of 160) |
  |---|---|---|---|
  | the released stage, 0.5.1, by its own command on the same null tracks | | | 38 of the 154 it runs on, a pendulum read off 13 of them (on six, PR097's objects of 4 px, it ends with an error: the stack is narrower than 200 px) |
  | 0.5.2 as set: the control at 0.6; a sighting 5 times the frame's noise; held in stretches of 45 frames on 0.3 of the frames; smooth to 1.5 px; under 0.5 of the scene's and of the screen's motion | 26 | 11 | **2** (both on tracks run backwards) |
  | every frame seen counted, not the held ones | 39 | 11 | 28 |
  | no test against the scene or the screen | 34 | 11 | 30 |
  | no smooth path asked | 26 | 11 | 3 |
  | no control | 29 | 11 | 14 |
  | the control at 0.3 or 0.45 | 24 | 11 | 2 |
  | the control at 0.8 | 27 | 11 | 3 |
  | held on 0.2, 0.25 of the frames | 26 | 11 | 5, 3 |
  | held on 0.4, 0.5 of the frames | 23, 21 | 10, 9 | 1, 1 |
  | smooth to 1, 2.5 px | 26 | 11 | 2, 3 |
  | the scene test at 0.3, 0.7 | 25, 26 | 11 | 2, 5 |

  2 of 160 is 1.3 % (0.2 to 4.4 %, exact 95 % interval), and both are things that
  do keep pace with the null track for a third of it or more: on PR135 object 6 run
  backwards another bird of the flock, 132 px away, held on 0.36 of the frames; on
  AARO's PR-009 row 4 run backwards three dark features 345 to 429 px away. What the
  null taught: a re-found feature is 5 times the frame's noise, not 2.5 (within 12 px
  of a place a 2.5-sigma feature is there by chance on a quarter of frames; on an
  earlier pass of this null over its first 33 tracks, with the follower's bar at 2.5,
  the followers of the null were made of them, 3 to 4 times the noise at the median,
  and 29 of 66 null tracks passed with every frame counted; every known companion is
  16 to 111 times the noise at its median); a companion is **held**, in stretches of 45
  frames (noise and texture come and go: counted frame by frame, 28 null tracks pass
  even at 5 times the noise); and half the scene's motion, the old test's own line
  between "nearer the object's motion" and "nearer the scene's", is where the scene test
  sits (the known companions make −0.05 to 0.26 of it, the scene's features 0.7 and
  more). The control's share stays at 0.6: at 0.3 the null's count does not change,
  and the two features that keep pace with AARO's PR-010 (below) go, which nothing
  here shows to be false. No rule here is a distance in object sizes: a sounding
  balloon's train hangs 10–35 diameters down, and an unresolved object's size is the
  point-spread pattern (H6).
- **H4, "nothing tied to the object" with no word of where.** PR28's stem hangs
  straight under the head, inside the inner radius (the object's extent plus 12 px) and
  the stroke mask. The finding and the checklist's row now say the ring that was
  searched, in pixels, and that nearer in was not (`searched_px`). Finding a line that
  starts at the object is H5's work, not done here (done since: section 55).

**The controls, before and after** (the stage's own words; `tests/test_golden.py` holds each):

| case | 0.5.1 said | 0.5.2 says |
|---|---|---|
| WA9ONY-5, the one known swing | swings, 2.59 ± 0.02 s, 1.66 m (tentative) | the payload re-found on all 130 frames in one stretch; swings, 2.58 ± 0.02 s, 1.66 ± 0.03 m (tentative); no wander of 2,000 as strong |
| AARO PR-004, a known balloon (the blind run's eight tracks, 4 to 11 s each) | a companion 28.6–32.8 px away on all eight; "a pendulum of 1.95 m" on row 4, "2.00 m" on row 8, a tentative 5.88 m on row 3 | the companion on all eight (28.6–32.8 px, held on 0.46 to 1.00 of the frames, to 0.4–0.6 px); no pendulum on any: rows 4 and 8 read p = 0.21 and 0.22, row 3 p = 0.002 (1.5 cycles of 5.0 s), the other five are steady to ±1.6–4.2° |
| PR105, frames 1075–2155 | a bright companion 28 px straight down, then a follower 14 to 1,290 px away: "steady to ±18.8°" | the companion 26 px straight down, re-found on 46 % of the frames (held on 0.34), 26.3 px from the object at the median and never past its leash; steady to ±4.9° over 36 s, no period |
| PR077 object 1, a bird | "a pendulum of 9.71 m" (tentative) | nothing tied between 15 and 280 px; the dark features 15 px out, at the ring's inner edge, are there on 4–7 % of frames |
| PR135 object 2, a bird | "2.52 m" (tentative) | the next bird of the flock, 30 px away, held on 0.77 of the frames; no swing (its angle spreads over ±16° with under 1.5 cycles of anything in 3.8 s) |
| PR149 | nothing tied, with `swings: true`, 0.159 m in the record | nothing tied between 14 and 480 px; no swing in the record |
| PR29 | a "companion" 277 px away on 8 % of frames, "a pendulum of 0.65 ± 0.01 m" | nothing tied between 23 and 780 px |
| PR28 | "nothing tied to the object" | nothing tied between 18 and 540 px; nearer than 18 px, where the stem is, was not searched |
| PR071, the string | a dark line 1.6 sizes below; −18 ± 5° over 7.9 s, no swing | the same line 1.6 sizes below, re-found on 92 % of the frames; −14 ± 3.6° over 7.9 s, no swing |
| PR055, the null | nothing tied: followed, the features went with the clouds | nothing tied between 29 and 960 px: re-found, the features make 0.84 to 0.94 of the clouds' motion |

**How it fails.** A payload too faint for single frames (under 5 times a frame's
noise) evades the follower, and one that swings more than its own size smears in the
stack besides; that needs a search over the pendulum's own motion (period, amplitude,
phase), not written. A companion seen in stretches shorter than 45 frames, or held on
under 0.3 of the frames, is refused as "not held for long": PR105's lower point, which
brightens and fades by itself, is held on 0.34 of its frames, not far above the line.
What keeps the object's pace across the screen for another reason passes as a companion,
and is reported with its numbers, not hidden. Three kinds were met on these tracks. A
neighbour in a flock (PR135's six birds, PR097's: `run` names it a fellow member where
the neighbour was followed too). The far scene, where the background's shift is read
off a nearer layer: on AARO's PR-010 a dark feature on the horizon, 618 px from the
object in one window and 448 px in another, keeps the pace of the distant object while
the sea in front does not (0.08 and 0.20 of "the scene's" motion). And a straight edge
the object moves along: on AARO's PR-009 the features lie on the picture's upper and
lower borders, which stay as sharp along themselves however the object moves beside
them, and a follower on an edge can slide along it (0.41 of the screen's motion and
0.46 of the scene's, under the half that would refuse it; features of the same kind
are one of the null's two false companions). These three tracks are what is left of
the eleven far "companions" 0.5.1 gave AARO's. The sensor's own picture can follow the object
too: under PR097's objects 7 and 8 a dark feature sits 14 px straight down, on 71 and
72 % of frames, where a smear down the sensor's column would be; it is just outside
the ring's inner edge and passes. A stronger spot of the scene passing right over the
companion carries one pass of the follower with it to the end of the leash; the pass
made in reverse holds the companion on that side, unless a second spot does the same
from the other. Where the picture is held three or four frames at a time (PR29) the
cadence check of `stack_both` does not see the repeats (it asks each frame against the
median of the last ten, most of which are repeats); the follower's scatter leaves out
places read off a held picture, and the count of repeated frames is short. A thin
*bright* line on the object is masked with the overlay's strokes (`--no-stroke-mask`).
A line that starts at the object is inside the ring searched (section 55 reads the
object's own picture for one). A line held at a steady angle gives no length. And the wander null's 1 in 100 is its rate on drawn wanders; on
the one known balloon whose payload shows (AARO's PR-004, eight windows of 4 to 11 s)
the nearest miss was p = 0.002 on one window, a period of 5.0 s over 1.5 cycles that
the clip's 32 s do not hold (p = 0.55).

## 7. The astronomer's tests in `mcdonald flicker` (added 2026-10-15)

The flicker stage's own tests were each worked out on one clip that fooled it (the docstring's items 1-6). Astronomy
has named statistics for the same questions, with known null distributions, and a survey of the astronomy
literature (a working note kept with the PURSUE analyses, not part of this package) ranked the four that fit the
stage. They are now computed beside the
stage's tests on every run and reported with them. They do not decide: `flicker.GATE_ASTRO`, which would make the
first two decide, stays off by decision (2026-10-17). Judged on 760 saved curve sets with the held-out third left out,
it lost 4 of 27 known birds' beats and none of the 3 false alarms among 2,887 background apertures judged as the object;
alone, its tests pass 58 % of those apertures, because Baluev's probability assumes white noise and these backgrounds
are red. A gate worth having would hold the peak against the curve's own continuum, as the scrambled copies do.

| what is asked | the stage's own test | the astronomer's | where |
|---|---|---|---|
| is the peak more than chance? | ABOVE x the background apertures' strongest; the drift null | Lomb-Scargle peak with Baluev's false-alarm probability; chunk-scrambled copies of the curve | `astro[track].lombscargle`, `.scramble` |
| is the rhythm the video's? | the codec's lines from the GOP; the picture rate from held frames | the spectral window of the frames that are samples (held or lost frames are *missing samples*) | `.lombscargle.window_lines_hz` |
| is it the camera's gain, or the display's? | a background aperture beating at the object's frequency (`shared`) | the frame's own level and contrast (the tracked things masked out), then the background apertures' common mode, regressed out of the object's curve (SysRem/TFA) | `.common_mode` |
| is it the pixel phase? | the disc aperture's sub-pixel weights (trap 1) | the pixel phase regressed out (Spitzer's decorrelation) | `.pixel_phase` |
| how often does noise alone pass? | -- | every background aperture through the object's own tests (the Robovetter's principle) | `controls`, `false_alarm` |
| what would the stage miss? | -- | beats planted in the background apertures and recovered (injection-recovery) | `injection` |
| where in the picture is the beat? | -- | the frames folded on the beat: bright half less dim half (epoch folding; Kepler's difference image) | `fold`, `<case>_fold.png` |

Each is computed over the stretch the beat is reported from (`astro[track].frames`: a window where the beat was heard in one, else the whole track), so that a beat heard in two seconds of flapping is not held against the whole track's quiet.

Reading them. A beat the stage calls the object's own should have a false-alarm probability well under `FAP_MAX`
(0.01), a scramble `p` under `P_MAX` where the scramble can speak (above 1/`SCRAMBLE_S` = 4 Hz), a common mode that
accounts for little of its curve and leaves its amplitude, no background aperture passing the tests itself, and a
fold whose difference picture is concentrated in the aperture at the object (`concentration` well over 1, `offset_px`
within a pixel or two) while the rest of the frame changes little (`scene_rms` at the grain). Where one disagrees, the
notes say which, and the report carries the note. `injection.complete_from` is the amplitude the stage is complete
from on this clip's own grain: a corpus count of beats is a count only above it.

What the scramble cannot say: anything under 1/`SCRAMBLE_S`. Scrambling in chunks destroys the slow wander along
with every rhythm, so at low frequencies the copies are quieter than the curve and a slow wander would pass; the
drift test (item 5) is the null there. What the common mode cannot say: it is the background apertures' first two
components, and a beat that is only in the object's pixels loses about 2/n of its variance to chance alignment
and no more; a mode that accounts for half the curve is a gain, a display, or a rhythm of the frames.

The slower nulls -- the background apertures through every window, and the planting -- are run by the command
(`mcdonald flicker`, `--no-nulls` to skip them: about as long again as the stage's own windows) and left out of
`measure()` unless asked (`nulls=True`). `mcdonald run` and the window's Measure do not run them (this said they did
until 2026-10-16; they never have).

## 8. The seismologist's tests in `mcdonald flicker` (added 2026-10-15)

Seismology is the science of one sensor listening to a continuous noisy record of a source it cannot control, and its
literature, surveyed in a companion working note (not part of this package), adds the tests below to the astronomer's of §7.
Six of its ports are in the stage, computed beside the stage's own tests on every run and reported with them. They do
not decide: `flicker.GATE_SEIS`, which would make the line test decide, stays off by decision (2026-10-17). On the same
760 curve sets it lost 3 of 27 known birds' beats to remove 2 of the 3 false alarms, within their noise; alone it passes
58 % of the background apertures, since a line in any one of up to 47 windows of 2 s lets a track through.

| what is asked | the stage's own test | the seismologist's | where |
|---|---|---|---|
| is there a line here, past chance? | ABOVE x the background apertures' strongest; the drift null | the multitaper harmonic F-test (Thomson 1982): the chance of one stationary sinusoid at the beat against a continuum smooth over the tapers' bandwidth -- over the stretch (a wingbeat wanders: no stationary line over a whole track) and in 2-s windows along it, which decide | `seis[track].line`, `.line_windows` |
| does the background, or the camera, beat with it? | `shared` (a background aperture at the object's frequency, half as strong) | the magnitude-squared coherence at the beat with each background aperture and with the frame's own level and contrast, against the level chance clears; the phase with its error (Thomson & Chave 1991; InSight's comodulation) | `.coherence` |
| how loud is the noise *at this frequency*, as a distribution? | the median of four apertures' strongest peaks | every background window's spectrum as a probability density (McNamara & Buland 2004); the centile the object's windows sit at | `.noise`, `<case>_noise.png` |
| a frequency from a few cycles? | nothing under 60 frames | the Sompi method (Hori et al. 1989): the roots of an autoregressive model that hold still across its orders, a frequency and a decay each | `.sompi`; `short_record` for tracks of 20-59 frames |
| fundamental or double? | `HALF`: a peak at half the strongest, half as strong | the lines read as a comb, the fundamental whose multiples hold them (harmonic tremor, Hotovec et al. 2013) | `.comb` |
| does the rate change along the track? | windows of 2 s, the clearest reported | the fundamental followed in 1-s windows over the whole track, with its double; a line through it | `.glide` |
| do the members beat as one? | `common`: pairs by their cross-spectrum's phase, APART_DEG | all of them at once: the phase coherence of a phase-weighted stack against time-slid copies, and the array F-statistic (Blandford 1974) | `in_step` |
| where in the picture is the beat? | -- (§7's fold, by amplitude) | the same by phase: each pixel's coherence with the aperture's curve | `fold.phase_inside / phase_outside`, a column of `<case>_fold.png` |
| is it a few frames, or the waveform? | `lost` (a drop under DROP) | the strongest again with every sample its sign alone (Bensen et al. 2007) | `.onebit` |

Reading them. A beat the stage calls the object's own should have a line at its beat under `MT_P` (0.01) in most of
the 2-s windows along its stretch (over the whole stretch it need not: the F-test asks for *one stationary sinusoid*,
and a bird's rate wanders -- on PR135 none of the six is a stationary line over 150 frames and every one is in its
windows; a line that *is* stationary over a whole track is a hum, a display's refresh or a codec's rhythm, and the
stage lists those for the band), a coherence with the frame's level and contrast and with every background aperture under the level chance
clears, its windows' amplitude at the beat above the background windows' 99th centile, a Sompi line at the same
frequency holding still across the orders, a comb whose fundamental is the stage's (where there are two lines), a one-bit
reading at the same frequency, and -- for a point -- a phase coherence within the aperture well above that outside it.
Where one disagrees, the notes say which, and the report carries the note. For a group, `in_step` past chance on both
counts where the stage's pairs said "independent" is the disagreement to look at: a rhythm of the video makes members
coherent. The glide is a measurement, not a test: a wingbeat's rate changes along a track (flyer 5's settles over its
approach), and the double moving at twice the fundamental says the two lines are one comb.

What the line test cannot say: in a 2-s window its bandwidth is 2.5 Hz, so there it tells a line from none and not the
fundamental from the double; the comb, read from the clearest window's lines, does that where the double is under the
top of the band (PR135's doubles are not). What Sompi cannot say: a decay from a short noisy
record reads too fast (a planted Q of 60 on 40 frames reads about 45), and a root holds still in anything periodic,
which is why its line must also stand over what the lines leave of the record. What the short-record reading is: a
reading. Nothing holds it against the background beside the object, and the report does not count it as a beat.

The tether's swing by Sompi (its period with its damping), semblance for the velocity search, the Z-detector for a
still scene and the corpus noise models from the whole-video pass are the survey's next items.


## 9. The look-alikes in `mcdonald flicker` (added 2026-10-16)

From the SETI methods survey (its first port, the first item of ROADMAP.md's 0.3): the rhythms that are not the
object's but can beat at a bird's rate once folded through the frame rate. A lamp on 50-Hz mains flickers at
100 Hz; an aircraft's lights on its 400-Hz power at 400 or 800 Hz; a video at 30 frames a second folds every one of
them to 10 Hz, and at 29.97 to 9.19-10.39 Hz -- where small birds beat, and where two objects of the bird paper's
Table 1 sit (PR077 at 9.93 Hz, PR088 at 10.2-11.0). A rhythm locked to every third, fourth, fifth or sixth frame
(a codec's anchors, a 3:2 pulldown, a display's refresh filmed by a phone) and the cadence of held pictures are of
the same kind.

`flicker.lookalikes(fps, pictures)` is the table for a clip -- each entry where it sits in the band, what makes it
and the frequency it came from (`fields["lookalikes"]`; `mcdonald flicker` prints it). `flicker.alias(hz, fps)` is
the fold: |hz - round(hz / fps) fps|, into 0 .. fps/2. A beat within its own resolution of an entry is marked with
it (`beat[..]["lookalike"]`, and `double_lookalike` for the double), as a beat at the codec's line is marked -- but
**marked, not refused**: a bird can beat at 10 Hz. The finding and the notes say so, and say what tells the two
apart: a supply's line holds its frequency to the supply's own steadiness, a wingbeat's wanders -- across the 2-s
windows that beat (`hz_range`) and over the whole stretch, where the seismologist's F-test (§8) finds no stationary
line in a wingbeat and finds one in a hum. The morphology tests the survey names for the two 10-Hz objects (the
beat's depth along the track, its wander against a supply's, the fixed-core width) are analysis for the paper's
revision, not a stage.

What it is not: a decision. A beat at a look-alike with no wander, a stationary line over the whole track and a
footprint (§7's fold) that is not the object's is a supply's; one that wanders is not; the report leaves that to
the reader, with the numbers beside it.

The bands (an aircraft's bus as recorded, flames, rotors, propellers, a cooler's drive) and the steadiness of a beat
against planted clocks, added 2026-10-20, are §18.

## 10. The bird paper's method in `mcdonald flicker` (added 2026-10-16)

The bird paper measured PR135's six points, and every object of its Table 1, in its own way; its numbers are the
reference cases of ROADMAP.md's 0.3. Four of its pieces are now the stage's, each an option, so that a case can be
measured the paper's way and the result checked against the paper (the reference-data folder's `cases/`):

| the paper | the stage | option |
|---|---|---|
| a disc of the object's own size, 2.5 to 12 px, its background the median of a ring outside it, never re-centred, on the smoothed track | `fixed`: the stage's 8x8 sub-pixel photometry in that disc and ring, the background apertures beyond it | `--aperture R[,R1,R2[,BG]]` (default: the aperture that follows the object's size) |
| the continuum null: the peak against a power law fitted to the curve's own amplitude spectrum, ±0.5 Hz of it left out, held against 2,000 noise curves of that continuum read at their strongest anywhere in the band | `continuum`, over the stretch each beat is reported from, in `fields["continuum"]` | always reported |
| constant dots like the object, planted in the clip's own frames and grain, encoded like it (its GOP, B frames and bit rate) and measured as the object is | `planted.dots` and `planted.at_beat`, in `fields["encoding"]` | where one object beats at the codec's rhythm; with the paper's rule; with the slower nulls |
| the six measured together, each apart from its neighbours | `clear_offsets`: background apertures placed clear of the other tracked things in the frame | `--avoid TRACK.csv[,...]` |

**The continuum null** reproduces the review that judged Table 1. On the whole-video pass's saved curves of the
objects that review quoted, its original code gives exactly the review's numbers (PR41 15.1 against a 99 % level of
4.4; PR085 12.2 against 4.5; PR102 3.4 against 4.5, p 0.36, not a line), and the port, which reads the stage's own
deviation curve (one running mean; the review's script took two), agrees on every verdict, to the hundredth of a hertz,
with ratios within a fifth. On noise with a power-law spectrum and no line, not taken through the running mean, it
passed about once in a hundred; but a curve the stage hands it has been through the running mean, and until 0.4.2 its
noise curves had not, nor was each noise curve's own peak left out of its own fit as the curve's is: with the null true
the stated 1 % ran at about 5 % (§39). Since 0.4.2 the noise curves are read exactly as the curve is, and the 1 % is
1 % on white, pink and 1/f curves, about 2 % on a random walk with grain; the 99 % level is about 5.2 where it was 4.2-4.4,
and five of the 28 reference lines, at ratios 4.8-5.7, are no longer lines at 0.01 (§39 names them). What it still cannot see is a slow
change steeper than the curve's continuum, which the running mean turns into a bump near 1/DETREND_S: that is the drift
test's trap, and the reason the stage's own rule keeps the drift test.

**The encoding control** answers what the codec check cannot. The codec check says a beat sits at the encoder's
rhythm (PR135: a P frame every fourth frame, 7.49 Hz); the planted dots say whether the encoder makes a beat that
strong there. Measured alone, PR135's B beats at 7.38 Hz, inside the codec's line, and the stage had said nothing tells
the two apart; the dots encoded like the clip reach 0.4 % there against B's 22.5 %, sixty times less, and B's beat is
its own. The control asks one thing, whether the encoder makes a rhythm at the beat. Where the encoded dots carry a line
there -- the encoder's own, faint (PR097: 1.3 % at 7.4 Hz, where the object beats at 15.6 %) -- the beat must be three
times it (`planted.ABOVE`). Where they have none, what they reach at the beat is the noise of their record and the
encoder makes no rhythm there: PR085's 7.37 Hz is 2.9 times the dots' noise, which the review that judged Table 1 accepted
for that reason. Whether the object beats at all is the continuum null's and the background's to say. Without libx264 in
ffmpeg the control says so and decides nothing. The encoder runs on one thread, so that the control gives one answer: on
several, with a target bit rate, libx264 is not bit-exact from one run to the next, and a case file's rerun moved only in
the control's numbers until it did.

**The other tracked things.** Measured one by one, PR135's E and F had background apertures 25 px out that sat on
neighbouring birds beating at their rates, and the stage said the background shared their beats. Told where the other
objects are, the stage keeps the four default apertures where they stay clear on every frame, and otherwise takes four
of sixteen directions, at least 60° apart, farther out if need be; the fields and the notes say where. It is not done
unless asked, so that an object measured in a queue still gives what it gives alone.

**The rule, decided by the controls.** `--beat-rule paper` judges a whole curve by the continuum null under 0.01 and
its amplitude three times the background apertures' at its own frequency, and asks the encoding control of one object's
own beat; the 2-s windows keep the stage's tests, as the paper's candidates did. On 1,201 saved curve sets
(2026-10-16) -- 39 of birds, 5 of things that are not, and the whole-video pass's 1,157 objects -- the two rules agree
on the non-birds (no beat under either), the paper's calls 29 of the 39 birds against the stage's 26, and on the pass
111 objects (9.6 %) against 76 (6.6 %), 27 of its 38 extra at 1.5-3.5 Hz, where the running mean makes bumps. The
background apertures judged as if each were the object, which hold no signal by construction, pass 7 times in 4,700
by the stage's rule (0.15 %; 95 %: 0.07-0.31 %) and 93 times by the paper's (2.0 %; 1.6-2.4 %). So the stage's rule
stays the default, for a video nobody has looked at, and the paper's is for an object someone has -- the use the paper
made of it, on candidates the stage had found. Under it, at 2-3 Hz read the drift test beside the call: it is reported.

## 11. `mcdonald audio` -- what the sound track records (added 2026-10-16)

From the aviation methods survey: an accident investigator reads a cockpit recording's spectrum for the engines,
propellers and rotors that were turning (the NTSB's "Sound Spectrum Study"); forensic audio reads the mains hum as a
clock. Of the 150 PURSUE release files, 122 carry sound tracks that are digital silence and 27 carry sound; read the
same way, the 11 DoW videos among them give the codec's frames, two supplies and a propeller.

**What it measures.** The first audio stream, mono at 16 kHz, in 4-s Hann windows 2 s apart (a record shorter than
two windows as three half-length ones). A bin's *excess* is its level over the running median of the 25 Hz either
side. A **line** is a peak 12 dB over that median, 20-4,000 Hz, at the same frequency (0.6 Hz) in at least half the
windows; its spread across windows says whether it is steady. The lines are then explained, in order:
- *the codec's frames*: AAC works in frames of 1,024 samples, MP3 in 1,152, so near-silence carries lines at
  multiples of 46.875 Hz (48 kHz) or 43.07 Hz (44.1 kHz). A family needs three members, two of them low multiples, and
  does not reuse a stronger family's lines (a 16-kHz family's multiples are a 48-kHz family's). A family at a rate the
  file is not at is an earlier encode. PR39: five AAC lines at 48 kHz. Two encodes also *mix*: lines at
  a x 46.875 -+ b x 43.07 Hz (a <= 8, b <= 2) with the earlier encode's own b x 43.07 heard. PR36 and PR39 carry
  86.13, 101.37, 133.01, 148.24 and 179.88 Hz (187.5 - 86.13 = 101.37): encoded at 44.1 kHz, then at 48.
- *the video's frame rate*: PR113's NTSC tape buzzes at 29.97 Hz. The family needs the frame rate itself: 2x and
  6x 29.97 are where 60-Hz hum sits (the Gemini 7 audio).
- *an aircraft's 400-Hz power* (MIL-STD-704 allows 393-407 Hz in steady state) and *the mains* (50 or 60 Hz, a grid
  strays at most about 0.2 %): a harmonic series on a fundamental in range, its members steady to 0.15 %. Each is a
  clock: the clip plays at the fundamental over the supply's range of real speed. PR106 and PR107: the bus at
  399.66 and 399.74 Hz; PR113: 59.98-Hz mains. PR107's lines near 100, 200 and 300 Hz wander by tenths of a hertz and
  are neither.
- *sidebands*: two lines symmetric (0.15 Hz) about a supply's harmonic, 0.5-20 Hz from it, are the hum modulated --
  a tape transport's flutter -- not two machines. The Apollo 14 debriefing tapes (NASA-UAP-D026, D027) carry
  60.15 -+ 7.53 Hz; the upper sideband, 67.7 Hz, sits on a T56's blade-pass, and before this rule a weak tone near
  550 Hz completed a false "T56 C-130". Sidebands are claimed before any airframe is looked for.
- *hum through a transport*: a strong line within 1 % of 50 or 60 Hz that wanders (the Gemini 7 audio, the Apollo 16
  debriefings, the 1952 Ruppelt lecture, PR160: +-0.1 to 0.44 Hz) is mains hum carried through a tape or disc
  transport's wow: ground power, but no clock.
- *a harmonic series*, any other: something turning steadily -- a propeller, rotor, fan or pump. With odd harmonics
  only it is a square or switched electrical waveform instead (PR111: 243.78 Hz and x3 ... x15, a cockpit tone or an
  inverter), and gets no propeller reading. A steady series 1-6 % from 50 or 60 Hz is offered as mains retimed, with
  the speed it would mean (the Apollo 12 medical debriefing, D008: 58.07 Hz, 0.968 of real speed). As a propeller it
  allows every (blades, rpm) with blades x rpm / 60 = F; **the series alone cannot say which** (four blades at R and
  six at 2R/3 sound the same). It is read as an airframe only against `PROPELLERS`, airframes whose propellers'
  speed in flight is sourced and whose sound in flight was measured: the T56 C-130 (four blades, about 1,020 rpm:
  68 Hz) and the C-130J (six blades, 1,020 rpm: 102 Hz). A series within 1.5 % of a blade-pass matches; a lone line
  (harmonics too weak for a series: an AC-130J in flight) only within 0.75 % and with the airframe's second tone.
- *the second tone*: each airframe also carries a steady tone at a fixed ratio to its blade-pass in flight --
  8.13 x on the T56 (553 Hz at 68), 5.39 x on the C-130J (550 Hz at 102), measured on DVIDS cabin audio. It is looked
  for in every window at 8 dB, where it should be. PURSUE's PR117-PR119 (phone captures of an AC-130's display over
  the Gulf of Oman, 2021) hum at 67.76 Hz with their tone at 550.8 Hz, 8.129 x: a T56 gunship in flight, not the
  AC-130J of AARO's description.
- *where each folds*: every heard rhythm folded through the frame rate (`flicker.alias`) into the beat band, in
  `flicker.lookalikes`' form; `flicker` adds them to its table when the clip has sound (`audio.heard`). PR117's
  67.75 Hz at 30 frames a second is 7.75 Hz, where birds beat. (Until 2026-11-13 `flicker` did not: its judging asked
  for the sound by a name it did not have, and the error was taken for a clip with no sound, so no report before
  that day marks a beat with a heard rhythm. Of the reference-data folder's 145 videos the sound of eight carries
  one in the beat band: PR106, PR107, PR111, PR113's per-file copy, PR117, PR118, PR119 and NASA-UAP-D008's tape.)

**What it cannot do, and the traps.** On the ground a propeller turns slower -- C-130Js loading and taxiing hummed at
65.75-75 Hz -- so a match says "in flight" and the report says that a phase of flight decides; the T56 match on
PR117 rests on D101's failed recorder (a live capture, so in flight). The codec's families look like machinery and
are named first. A phone's own processing changes levels, not frequencies; an absent line is weak evidence. And
silence is NO POWER, not "nothing heard".

**In the window.** Measure → The sound of this video… (`sound_qt`) reads the open video's whole sound track, up to
15 minutes, in a thread behind a wait's card at the top of the right column, then shows a page over the video. One
plain sentence comes first (`audio.plainly`, written from the same fields as the finding): the aircraft, named only
with its second tone; recorded on an aircraft; recorded or copied on the ground; copied through a tape machine;
something turning; silent; or no steady tone. A sentence follows for each thing heard. Then comes the figure, which
marks the second tone that named an airframe and is saved as `<tag>_audio.png` in the results folder (where
`mcdonald audio VIDEO --out DIR` saves it). The command's own words are folded at the foot. The reading is kept for
the video, so a second look opens at once. The page says what the tool reads, so it shares the tool's limits.

The window's players also play the sound (`speaker.py`, `mark_qt.SoundControl`):
- ffplay plays it, from the frame on the screen, at the player's speed with the pitch kept (atempo).
- The speaker beside the stop button shows once the video is known to have sound (`speaker.sound_of`: no track,
  digital silence, or sound).
- The main player skips late frames, so its picture keeps time with the sound. The segment chooser waits for them, so
  its sound starts once the picture moves and is started again when the two are more than 0.3 s apart.
- A video with sound also has a "Measure the sound" card in the right column, teal until the sound is read, then
  ticked and grey.
- Where it plays is chosen in Edit → Preferences… (2026-10-19): the system default, or an output by the name ffplay's
  SDL gives it (`speaker.outputs`), passed in `SDL_AUDIO_DEVICE_NAME`. SDL plays nothing for a name it does not know,
  so one ffplay refuses is played around, on the system default, for the rest of the session (`speaker.refused`).

**Tested.** `tests/test_audio.py` (54 checks, portable):
- a four-bladed propeller with its second tone, and a six-bladed one heard alone, with and without it;
- a lone line 1.2 % off;
- the codec's frames, at the file's rate and at another;
- the mains and the bus as clocks; a wandering series;
- noise alone (20 records of 20 s: no tones); a 2.8-s record; the fold;
- the six traps the corpus pass found (sidebands, a wandering hum, odd harmonics, two encodes, retimed mains, the
  frame rate's harmonics without it);
- the field rate against the mains (with and without video), two supplies and the pull-down, a bus on the field comb;
- a pass's speed and range (held, free, and the approach alone, wandering);
- what the window says (plainly, without the trade's words);
- the command end to end, with silence as exit 5.

`test_gui.py`'s `drive_sound` (31 checks) drives, on a drawn propeller and a silent video:
- the window's page;
- the card;
- the sound played with the picture, in both players. A stand-in for ffplay writes down what it was asked to play.

`test_golden.py`'s `test_audio_cases` (25 checks):
- PR117-PR119, PR106, PR107;
- PR113: its mains at 60.011, apart from its field rate; its bus only possible;
- AARO's FLIR video: its field rate, its bus at 399.095, the off-grid 60.32-Hz hum;
- PR39;
- six DVIDS C-130 cabin tracks of known type and phase of flight, and a UH-60 cabin;
- the Apollo 14 tape and an MQ-9 heard from the ground, as negative controls (`aircraft_audio/`).

`test_flyover_cases` (4 checks): two DVIDS C-130H passes with 68.06 Hz held, and two AeroSonicDB Dash 8-300 passes
against their ADS-B altitudes.

**More airframes, and what a blade-pass alone is worth** (added the same evening).
- *The H-60* joins the table. On five DVIDS UH-60 clips the main rotor's blade-pass is 17.20-17.28 Hz (258 rpm, four
  blades, as sourced) and the tail rotor's 79.2-79.7 Hz, so the ratio is 4.605-4.614. The tail rotor is its second
  tone. The band now starts at 12 Hz so the main rotor is heard. Its 4th harmonic, 68.8-69.1 Hz, sits near a T56's
  68 Hz. Read from inside the cabin it is identified; from outside, Doppler makes its lines wander.
- *The MQ-9* is not in the table: its propeller speed is unsourced. Heard from
  the ground in the pattern (DVIDS 776121), its blade-pass sweeps 67-76 Hz with Doppler, straight over a T56's 68.
  Its second tone sits at an integer 9.00x, and a ratio of two engine-locked tones is a quantity Doppler cannot
  move. Hence **a blade-pass identifies nothing by itself**: a series or a lone line is read as an airframe only
  when that airframe's second tone is heard. Otherwise it "matches, not identified".
- *Jets* put no steady engine tone in the band. What an F/A-18 recording holds is its 400-Hz bus: AARO's 2004 Navy
  FLIR video and PURSUE's PR106/PR107/PR111. Gimbal and Go Fast hold crew voice and no steady tone. (The FLIR video was
  first read here as a bus "under a ground copy's 59.94-Hz mains". Withdrawn: the acoustics survey of the same day,
  fitting harmonic by harmonic over the whole record, finds its 59.94-Hz line at twice its 29.97-Hz frame line and
  nothing at 60.00 -- the NTSC field rate's sync buzz, not mains -- and two supplies, 399.1 and 401.3 Hz. The clocks
  are now read at full resolution: below.)

**Rules tightened by AARO's videos and the planted tones.**
- A supply counts one line a harmonic, and needs a member at k <= 3 and two at k <= 10. Puerto Rico's "50.43-Hz mains"
  sat at x5, 15, 22, 30, 33, and PR-017's "400-Hz bus" was one line counted twice.
- The second tone must agree with the ratio to within 0.15 %, be heard in at least two windows (three for its
  spread to count), and hold its frequency to within 0.15 %. Measured second tones agree to within 0.05 % and
  spread 0.02-0.11 %; noise peaks in the old +-0.4 % band reached the old share on short records.
- Sidebands are looked for about every hum fundamental, not only the mains family's, with the mirror line found
  among the weaker peaks too.
- A series is steady when its lowest member is, and at least half of its members are (a rotor's high harmonics
  drift).
- A peak is a local maximum within +-0.5 Hz (a Hann window's main lobe). At +-0.75 Hz, PR36's codec line at 101.37 Hz
  hid a tone at 102.3.

**Completeness and false alarms, from planted tones** (`analysis/tools/audio_plants.py` in the PURSUE analysis). Each
airframe's signature, and two decoys, were planted in the 35 real sound tracks with sound (27 PURSUE, 8 AARO). The
first 120 s of each were used, at 3-24 dB over the track's own local noise, with the frequency jittered +-0.4 % and
three draws a strength (3,150 runs).
- Found at +12 / +18 / +24 dB: T56 23 / 76 / 79 %, C-130J 41 / 90 / 94 %, H-60 25 / 92 / 97 %. Nothing at 9 dB or
  below.
- **No planted airframe was ever read as another** (0 of 945).
- Of the decoys, an MQ-9-like series (9.00x) was read as a T56 in 4 of 630 runs. Each was a coincidence with a real
  tone the track already held at 8.13x the decoy's blade-pass (PR072 holds one at 554.5 Hz), which is the method's
  residual risk. Mains sidebands with an 8.13x tone on the upper one were never read as an airframe (0 of 630;
  planted about the track's own hum, as a recording's sidebands are).
- What misses: a track's own harmonic family can absorb a planted series (the Mercury tapes' 22.75-Hz family holds
  68.25 as its 3rd), and a planted 68 Hz on the Apollo 14 tapes lands on their 67.7-Hz sideband and is held back.

**The clocks at full resolution** (the acoustics survey's Ac1 and Ac2, `analysis/methods/acoustics_methods_survey.md`
in the PURSUE analysis). A 4-s window's bins are 0.25 Hz wide, and three kinds of line sit closer than that.
- *The NTSC field rate is not the mains.* An NTSC chain leaks its vertical sync into the sound at the field rate,
  60/1.001 = 59.94 Hz, with a comb of harmonics. 59.94 is 0.06 Hz from 60-Hz mains. The frame family is now fitted from
  the video's own k = 1 line, trying the tag and its NTSC twin (30 and 30/1.001), and claimed to 4.2 kHz before the
  mains. The mains is never taken from that comb. With no video to tell, mains at 59.94 says it may be the field rate.
  - AARO's 2004 FLIR video: its 59.94-Hz line is 2 x its 29.967-Hz frame line, harmonics to the 39th.
  - PR113: the field rate at 59.944 beside mains at 60.011; the old 59.988 was their blend.
- *A line on two combs counts for neither.* 3 x 400/1.001 = 20 x 59.94, so where the field comb is heard a bus's 3rd,
  6th and 9th harmonics are its lines too. A bus that stands only with them is `bus_possible`, not a bus (PR113).
- *The clocks again, in 30-s pieces.* After the 4-s pass, each clock is re-read from up to three 30-s pieces of the
  record (resolution 0.033 Hz), its harmonics' frequencies divided by k and grouped. A supply counts where most pieces
  find it. Longer pieces smear a supply's own wander: Puerto Rico's bus drifts 0.035 Hz in two minutes. This splits
  what one 4-s line held: two 400-Hz supplies (PR107: 399.817 and 399.597; PR111: 399.604 and 399.829) and the field
  rate beside the mains.
- *400/1.001.* Every bus is given against 400 Hz and against 400/1.001 = 399.600, the NTSC pull-down. PR106, PR107's
  second supply, PR111 and PR113's possible bus all sit within 30 ppm of it. Either the supply runs there, or the
  sound is 0.1 % slow; the file has no second clock to say which.
- *Mains off any grid.* Grids hold well within 0.08 % (US interconnections count excursions of 36-90 mHz as events).
  Mains further off is said to be a local supply (a generator, an inverter, a ship's 60-Hz service power, which may
  run within +-3 %) or a copy retimed by that much. FLIR's odd-harmonic hum at 60.32 Hz (x1-x15, odd) is one. The
  supply tolerance tightened from 0.12 % to 0.05 % with this: it was wide only to hold the blends now split.

**A source passing the microphone: speed and closest range** (`mcdonald audio VIDEO --flyover LO-HI [--rest HZ]`;
the survey's Ac8). Ferguson's (1992, JASA 92:1403) single-microphone method:
- A tone of rest frequency f0 from a source passing at constant speed v, closest at range r0, is heard at
  f0 / (1 + (v/c) s/R) at the time its sound arrives.
- The sweeping tone in [LO, HI] is followed by continuity, its harmonics guided by it, and the curve fitted robustly.
  Every harmonic is then re-tracked about the fitted curve and refitted.
- `--rest` holds f0 when the source is known (an identified airframe's blade-pass in flight). Without it, f0 trades
  against v and r0 over a partial pass. The `profile` gives v and r0 at each f0 that fits as well.
- It needs a microphone that does not ride with the source. A cabin's own propellers have no Doppler, and a governed
  propeller keeps its speed at every airspeed and height. So no PURSUE sound track (cabin, onboard channel, ground
  tapes) can give its platform's speed or height this way.
- On DVIDS 752745, two Connecticut ANG C-130Hs (2020) flying over a camera with 68.06 Hz held, three passes give 212,
  213 and 244 kn at closest ranges of 291-465 m. Free, the rest tone comes out 65-79 Hz, the trade the profile reports.
- **Against ADS-B.** AeroSonicDB (Downward & Nordby 2023; `$MCDONALD_DATA/aerosonicdb/`) has 148 fixed-wing
  propeller passes near Adelaide Airport, each recording triggered and labelled by the aircraft's ADS-B. The rest
  tone was free, and the closest range compared with the ADS-B altitude at the recording's start.
  - The fit's own checks keep 75 passes: closest point inside the span heard, residual under 1 Hz, speed 80-300 kn.
  - For those, closest range / altitude has a median of 0.92 and a 16-84 % range of 0.66-1.19 (a descending approach
    sits a little under its starting altitude).
  - So one pass gives its closest range to about +-25 %. The formal errors, about 1 %, understate it.
  - The Dash 8-300s' tone comes out at 60.6 Hz, pass after pass.
  - The follower must ride over 0.3-s fades near the closest point (the ground reflection's nulls). The free fit must
    start from the curve's asymptotes, not from an f0 scan's lowest residual: along the trade the residual is nearly
    flat.

**The corpus.** All 149 PURSUE video and audio records (`analysis/tools/audio_corpus.py` in the PURSUE analysis):
122 sound tracks are digital silence and 27 carry sound. Of the 27, three name an airframe (PR117-PR119, the T56
gunship), three carry an aircraft's 400-Hz power (PR106, PR107, PR111), two are double encodes (PR36, PR39), PR113 is a
tape dub with mains, the bus and its NTSC clock, and the NASA, Ruppelt and IIR records are ground recordings: mains
hum (four as clocks, five through a transport), sidebands, and one possibly retimed transfer (D008).

## 12. Frequencies with their errors, and the codec's slice, in `mcdonald flicker` (added 2026-10-17)

From the information-theory survey (its D1 and D6; ROADMAP.md 0.3, objective 2). Until now `flicker` compared
frequencies at the resolution 1/T: a peak within 1/T of a codec line was "at the codec's line", and two members were
apart only past 1/T over their common frames. The resolution says when two sinusoids in one curve can be told apart. It
is not how well one sinusoid's frequency is known, which is finer by about the root of the frames times the
signal-to-noise (Rife & Boorstyn 1974). On a 2-s window 1/T is 0.5 Hz, and 93 of the 112 sensor videos have an anchor
every fourth frame, a line at 7.49-7.5 Hz: their windows passed nothing from 7.0 to 8.0 Hz, the middle of the bird band.
In the whole-video pass, no object whose windows read 7.0-7.5 Hz had a window passing (0 of 20), against 12 of 27 at
6.0-6.5 Hz, and PR085's bird was refused there and found again by hand. The planted beats were moved off the line, so
the completeness never showed it.

**The error** (`flicker.hz_error`). The sinusoid at the peak and a constant are fitted by least squares. The residual
is resampled in 0.5-s blocks end to end around the curve (a circular block bootstrap, which keeps the residual's colour)
and added back to the fit, 200 times. Each copy's peak is read as the stage reads one, within its own lobe, and the error
is the spread of those peaks. It is never under the Cramer-Rao bound for one sinusoid of the fitted amplitude in white
noise of the residual's variance, nor under the padded spectrum's step over √12, since the frequency is read off that
grid. Every object's peak, every window, every pair and every reported beat carries it (`hz_err`), and `mcdonald
flicker` prints it.

Planted in white grain, it is honest above the detection threshold. Over 200 draws at 60, 136 and 300 frames, with a
signal-to-noise of 1-2 a frame, the truth lies within two errors 90-98 % of the time and within three 97-100 %. Below
the threshold the strongest peak of the band is often the noise's, somewhere else (40-70 % of draws at 0.3 a frame).
Such a peak passes none of the stage's other tests, and its error says nothing of where the planted beat was. On PR135's
members over 4.5 s the errors are 0.02-0.11 Hz against a resolution of 0.20. The members whose rates wander most have the
largest, because a steady sinusoid cannot absorb a wander and the residual keeps it.

**The codec's mark** (`flicker.at_line`). A peak is at a codec line where it lies within three of its own errors of it.
The line has no width: it is locked to the frame count, so the codec's own rhythm is read there to within the reading's
error. Planted on the line, a rhythm is marked every time. A strong beat a quarter of a hertz beside it, in a 2-s window
with a signal-to-noise of 4 a frame, is marked 0-7 % of the time, against 100 % by the resolution; a weak one (1 a
frame) still 25-85 %, as its error is large. The rhythms locked to every k-th frame in the look-alike table (section 9)
are held to the same error. A supply's line, a heard rhythm and the cadence of held pictures keep the resolution, as
each has a width of its own. The one-bit reading and the multitaper's lines (section 8) are marked the same way.

**Members apart** (`flicker.common`). Two members are apart where their frequencies differ by more than three of their
combined errors (`apart_z`), over all the pairs judged at once (Sidak: 3.0 for one pair, 3.75 for PR135's fifteen), so
that a rhythm of the video read in fifteen pairs seems apart no oftener than in one. The phase test is as it was.

**The slice, planted** (`flicker.sliced`, with the slower nulls, which `mcdonald flicker` runs unless told `--no-nulls`).
Beats of 10 and 20 % of the object's brightness are planted 0.1, 0.25 and 0.4 Hz either side of each codec line, in a
2-s window of each background aperture, and 1 Hz off it as the control. Each is put through a window's tests, and
`by_resolution` is what the old mark recovers of the same beats. On grain (the planted-signal test), at 20 % everything
a quarter of a hertz or more off the line is recovered, as the control is; by the resolution, nothing within half a hertz.

**In closed form** (`flicker.analytic`, D6). The amplitude a beat needs to be heard three times in four follows from
the noise, the frames and the band's look-elsewhere: the error exponent of the test between noise and noise with a
sinusoid in it (Stein's lemma; Cover & Thomas 2006, 11.8), with the Hann window's quadrature variance 2σ²Σw²/(Σw)² and
the drift test's nominal 1 in 100 over the band (what its line is worth on real empty apertures is §39's). With the
background apertures' own flicker it is ABOVE times that, where that
is larger. It sits beside the planted beats (`injection.analytic`, `slice.analytic`) as their check, and beside each
object (`fields["analytic"]`), with how long a clip must be for a beat of 5, 10 or 20 %. On the test's synthetic grain
the planted beats are complete from 10 %, where the closed form says 5.5 %: within the factor of two that the planted
amplitudes' steps (2, 5, 10, 20 %) leave. On PR135's members a beat needs 7-10 % of the brightness in their own noise,
and one of 10 % needs 2.5-6.4 s.

**What moved.** PR135: the whole-track frequencies are unchanged, and the paper's to 0.06 Hz. The windows that pass went
from 0 to 9, 3, 9 and 7 of 14 for A, B, E and F (the four within half a hertz of the 7.49-Hz line), and from 4 to 14 and
10 for C and D. Where a window is clearer than the whole track the stage reports it, so E is reported at 7.90 ± 0.07 Hz
(whole track 7.69 ± 0.03), C at 8.02, D 7.09, F 7.74. B's one-bit reading (7.405 ± 0.016 Hz) is no longer at the codec
line; F's (7.68 ± 0.07) still is. One pair moved the other way: D and F, 0.475 Hz apart over 4.5 s, past the resolution
but 3.5 of their wandering errors, under 3.75, and 38 degrees in phase, are no longer apart by frequency. The flock is
still the members' own. On the saved control curves the calls are the same as before: the five Galileo birds and PR135
beat; PR23, PR055, PR071, the WA9ONY-5 balloon and PR144 do not.

**Traps.** The error is of a frequency averaged over the stretch. A rate that wanders has no single true value, and the
bootstrap's spread includes the wander, as it should when the question is whether two readings over the same frames
differ. Below the threshold outliers dominate, and neither the bootstrap nor the bound sees them: the error is honest only
for a peak that stands. The bootstrap needs the residual's colour kept (blocks of 0.5 s). And a frequency read off a grid
needs the grid's step in its error, or a rhythm locked to the frames misses its own line by half a step.

## 13. The bird headline: a beat that comes back (added 2026-10-17)

The report names a bird as the leading explanation where the flicker stage finds a beat of the object's own at a
wingbeat's rate. Since 2026-10-17 (Jacob's decision 6 of ROADMAP.md, on the evidence below) it does so only where the
beat **comes back**: the whole track beats, or two passing 2-s windows that do not overlap agree within 0.5 Hz
(`flicker.apart_windows`; each beat's `whole_passes`, `windows_apart` and `comes_back`). A beat heard in one stretch
is still the object's own and still reported -- "it beats at 7.1 Hz for one stretch, frames a-b" -- but it names no
bird. One stretch is the weakest evidence the stage gives: a track has dozens of windows, each held to its tests at 1
in 100, and the cases that showed it were one stretch each (PR094's step and three dips; PR052, digitally altered).

On the 760 saved curve sets of the gate study (the held-out third left out), the stage calls 27 of the 39 known
birds; the rule keeps the headline for 25 -- 24 by the whole track, 1 by windows apart -- and loses two bout-flappers
that beat in one stretch only, PR085's and PR088's Table 1 birds (the paper's rule, with its continuum null, calls
both over the whole track, and their case files are made by it). Of the whole-video pass's 716 objects the stage calls
46; the rule keeps 29 and drops 17 one-stretch calls, among them PR052's two, PR073 o00 (rejected by eye in the review)
and blends of PR097's flock. The non-birds get no headline either way. A case made before the rule has no mark, and
its beats are read as coming back.

**A beat in one stretch, against its own continuum (added 2026-10-30).** "It is the object's own" was still said of one
window out of a hundred. Four of fifteen airliner arrivals in a Galileo Project camera beat at 1.7-4.9 Hz in one 2-s
window of their last seconds, where a 4-px aperture sits on a grown aircraft whose track hops between its hot parts:
the curve there drops once (the 1.7 Hz) or flips between two levels (the rest), and is no rhythm. The stage's tests are
held to a nominal 1 in 100 for each window (on real empty apertures the drift test's line passes 7-9 in 100, §39), and a
window that is the track's best of many has passed them by being the best. So a
beat that does not come back now stands only where it is a line against the continuum of its own stretch
(`flicker.continuum`, the paper's null), with the look elsewhere in the answer: the chance p must satisfy
1 - (1 - p)^L <= `ONCE_P` = 0.01, L being the stretches its track offered (`looks_of`: the windows read, an eighth apart,
over 8). Otherwise it is no beat of its own, the finding says why, and the light route to tau is open again
(`flicker.once_held`, `fields["unheld"]`). A beat that comes back is not asked: section 7's and 8's gates stay off.

**Windows apart, against chance (added 2026-11-13; IDEAS.md N3).** Two passing windows apart were the rule's second
road, and on a long track chance takes it. A track of a minute holds about 30 windows that do not overlap, each passing
the drift test's line 4-9 times in 100 on real empty apertures (§39). So two or three of them pass by chance alone. On the
Galileo Project's clouds and aircraft (the uap repository's `galileo/nevada/README.md`), 14 of the 16 beats T3 failed
came back this way, in as many windows as chance gives: 2 of 50, 2 of 41, 5 of 32. A beat now comes back by windows
apart only where that many passing is rarer than 1 in 100 by chance (`CHANCE_P`). The chance is binomial: `k` windows
apart of the `n` its track holds without overlap (`independent_windows`), each at the drift test's measured false rate
for its frequency (`drift_rate`, from `DRIFT_RATE`). That rate is generous to chance, since a window must pass more than
the drift test, and chance's windows would also have to agree in frequency. A real beat that returns along its track is
far beyond it: 12 of 40 windows give 1.9 in 10,000. Each beat records `windows_independent` and `windows_chance_p`, and
the finding says when windows apart were no more than chance. A whole track that beats is not asked. A beat that fails
this falls to the one-stretch rule above.

**Chance from the clip's own background (revised 2026-11-13, IDEAS.md N3).** The drift test's rate is a census over 116
release videos (§39). A clip whose background is clean passes far less often than that, and on a short track the census's
9 % makes two windows apart of five no more than chance (7 %). The labelled set lost two of the record's 30 named birds
this way (§44): IR_BIRD_017 and IR_BIRD_041 under the stage's rule, IR_BIRD_017 and IR_BIRD_038's object 1 under the
paper's. So where the windows decide (two or more apart, and the whole track does not beat), each background aperture
beside the object is put through the object's own windows over the object's stretch, held against the other apertures
and measured in the object's brightness, as the controls are (`background_windows`). Each window's chance of passing is
then the share of those windows that pass, and at least `CHANCE_FLOOR`, 2 in 100 (`windows_chance`'s `rate`). With fewer
than two apertures to read, it is the census's rate, as before. Each beat records `background_windows` (passing, of all)
and `windows_chance_rate`, and the finding says both where they ruled a beat out. The extra windows are read only where
they decide, so a run takes no longer elsewhere.

It was measured before it was built (the uap repository's `galileo/nevada/n3/`). The labelled set's 432 tracks were
judged again from their saved curves under both rules, once for each candidate rule. Every named bird of the record
comes back: 30 under the stage's rule, 27 under the paper's. Every call is the record's but one: IR_BIRD_035's object
0, refused in the record, now has no beat of its own, since its background's windows pass 6 % of the time and its two
windows apart of three are what that gives. The record's three false alarms come back with the birds (DRONE_059,
HELICOPTER_043, HELICOPTER_024); the census's rate had dropped HELICOPTER_043 along with the two birds. Background
apertures judged as objects come back by windows 2 times in 1,562. On the Galileo Project's objects (§53), T3's false
beats from every camera fall from 14 of 119 clouds and 3 of 80 aircraft (two windows apart, the rule before) to 5 and
0 (the census's rate gave 3 and 0). Three of the five clouds beat over the whole track. The other two beat in 10 and 11
windows of more than 160 while their skies' windows pass none: a cloud's own texture flickers more than the clear sky
beside it, which no background aperture can measure. The floor was set on these numbers. At 3 in 100 one of those two
clouds also drops, but two windows apart of five, a short bird's track (IR_BIRD_017), would sit at 0.85 % against the
1 % line; at 2 in 100 it sits at 0.38 %. Making chance's windows also agree in frequency (each 1-Hz band's own share of
passing background windows, summed over the band) changed only one helicopter, under the paper's rule, and was not built.

The rate is stated and then held to a null. Drawn with no line, in 100 cells at 30 and 60 frames a second: coloured noise,
bursts of it, hops, steps, and a level that flips. Of 11,400 tracks 1,800 (15.8 %) come out as one stretch, and 93 keep
it (0.82 % of the tracks, 5.2 % of the calls; the worst family, stationary noise with the object three to five times the
background, 2.8 % of its tracks). Without the look elsewhere, the continuum under 0.01 keeps 13.7 % of the calls;
with the line test beside it as an alternative, 34 %: the selected window has already passed for a tall peak, so the two
are not independent checks of it. A line of 3 % in 3 s, in the same noise, kept all 46 of its one-stretch calls, and 91 %
of the non-overlapping windows of beats that do come back would stand alone. On the Svanström labelled tracks the
one-stretch calls kept are 12 of 44 non-birds and 5 of 11 birds, so the rule takes out more of what is false than of what
is true, but it does not sort them: a label says a bird was there, not that it flapped, and the amplitude floor is what
tells a bird. Lomb-Scargle and the line test do not decide: the first assumes white noise and fails real birds (FAP
0.2-0.8), and the second, as an alternative beside the continuum with the same look elsewhere, lets 14 % of the calls
through against 5 %.

What it costs, under the default rule and aperture: of six reference birds that beat in one stretch, PR085, PR097's objects
4 and 7 and PR135's object 5 stay; PR088's object 1 (chance 0.0085, needed 0.0022) and PR097's object 8 (0.086, 0.0042)
lose the sentence. Neither named a bird, and their case files, by the paper's rule, beat over the whole track.

**Each member against its own apertures (added 2026-10-30).** One set of background apertures went with the member seen
longest, and every member's test was read against it, in the brightness of whichever member was listed first. So a
member's call hung on its fellows' tracks. Exercise 4's object 4 kept its bird while a fellow was followed from frame 1240,
and lost it when a link's tail started that fellow at 1259: the longest became the bird itself, the apertures moved to its
own side, and the floor rose from 2.7 % to 4.7 %, its curve not changing by a digit. Each member of a group now has four
apertures of its own, clear of its fellows (`clear_offsets`), read over its own frames in its own brightness
(`flicker.owner`, `fields["background_of"]`, `fields["floors"]`), and its whole track, its windows and whether the
background shares its beat are held to those alone. The set about the member seen longest stays for the readings. Object 4
fails either way now: 12.05 % against three times 4.8 %. Its earlier pass was on a fellow's apertures.

## 14. `mcdonald stabilize` -- a screen filmed by a phone (added 2026-10-18)

Twelve of the sixteen videos of the fifth tranche are a phone held up to a sensor's display (PURSUE PR117-PR122: an
AC-130's infrared display over the Gulf of Oman, 2021). The video's frame is then the phone's, not the sensor's: a
thing the sensor holds dead centre wanders over the video with the hand, every rate read off the raw pixels measures
the hand, and every geometric argument from "it moves with the overlay" is void, because the phone moves the overlay
and the picture together. Three trackers drifted 120-371 px off PR117's hand marks for that reason, and its first
analysis read a constant-offset blemish as the object and, later, read jumps of the hand as several objects marked in
turn. The stage maps every frame back onto the display and writes the display's own video, on which everything else
then runs.

**The model.** A flat screen seen by a pinhole camera is a plane in perspective: one homography per frame maps the whole
screen (pan, tilt, roll, distance, keystone). The phone lens's distortion and its rolling shutter are not in it and are
measured as a residual, not hidden.

**What is matched.** The display's *drawing*, never its picture: the scene moves on the display whenever the sensor
slews, and a match on it would cancel the motion that is wanted. The drawing is found as structure that is thin and
straight: the band-passed magnitude |G(1) - G(4)| weighted by the structure tensor's coherence over 8 px (a reticle arm
or a box edge keeps its direction over that, grain, sea and most cloud texture do not); letterbox and pillarbox bands
and the frame's outermost 6 px are left out (PR117 has a one-pixel green edge column that is fixed to the video), but
black inside the picture is kept (a redaction box's edges are the best anchors there are). A coloured drawing can be
matched on its colour alone (`--drawing chroma`), which leaves a grey scene out entirely.

**How.** Pass 1 aligns every frame, outward from the sharpest, each from its neighbour's answer, to a template that
starts as the reference frame's structure and grows as the hand shows more of the screen (half resolution, stopping at
the quarter-resolution level). The template proper is then the median, over up to 80 aligned frames spread across the
clip, of their structure on the canvas: what is fixed to the display survives a median; the scene, the objects, the
grain and whatever is fixed to the phone do not. Pass 2 aligns every frame to that one template, independently, so
nothing is chained in the answer and nothing drifts. Both passes are the enhanced correlation coefficient (Evangelidis
& Psarakis 2008) by Gauss-Newton on the eight homography parameters, over the template's strong pixels (at most 30,000
a level), coarse to fine on four levels with fewer parameters at the coarse ones, after a whole-pixel shift search at
the coarsest. A frame repeated by a variable-rate phone padded to a constant rate takes its twin's answer; a frame the
match cannot hold (score under 0.35, or a jump no hand makes in a frame) is flagged lost and interpolated.

**What it reports.** Each frame's homography and what it says of the hand (the display centre's place, scale, roll,
keystone); the repeated frames and the camera's true picture rate (PR118, PR121 and PR122: one frame in four repeats,
about 22.5 pictures a second, not 30); the hand's motion spectrum, slow drift and the fast part above 2 Hz apart (a
held phone's tremor is 8-12 Hz; an airframe's vibration folds in at its own rate -- PR117's T56 propeller at 67.75 Hz
lands at 7.75 Hz at 30 frames a second, inside the bird band), so that a brightness beat at a rate the hand or the
airframe also shows is suspect first; and whether the drawing held at the clip's start is the drawing held at its end
(`drawing_persistence`, below). `--hold-out X,Y,R@N` leaves a small display-fixed feature out of the template and follows
it afterwards in the held video: its wander is the stage's error there.

**Validation (PR117).** The held video's boresight, against the independent Radon fit of the reticle lines
(pr117_jitter.csv, which was validated against five hand-marked boresights to 2.7-5.5 px), agrees to 0.26 px rms,
1.0 px at worst, over 483 new frames. The ring that sits 345 px off the boresight, held out of the template, wanders
4.8 px rms (95 % within 8.5 px) in the held video: slowly (lag-1 autocorrelation 0.9) and in step with where the hand
holds the screen in the phone's frame (r = 0.75 with the hand's x), which is the phone lens's distortion, which one
homography cannot hold. On PR117 the hand's fast shake is 0.3 px between 4 and 15 Hz with no line at 7.75 Hz.

**The trap: holding the scene.** When the sensor's scene is richer than the display's drawing, both layers move in the
phone's video and both are candidates. In the synthetic self-test (`tools/stabilize_selftest.py`: PR144, a native clip
with a thin orange reticle over textured cloud, filmed by a simulated hand with a tremor, a vibration, repeated frames
and an H.264 encode, the true homography of every frame known), pass 1 followed the clouds, the median template built
from those frames was cloud, and pass 2 agreed with it: 148 of 150 frames "aligned", 33 px rms from the truth. A
self-consistent wrong answer. The stage now asks of every run whether the drawing it held is the same at the clip's
start and end (the median aligned structure of the first third of the frames against the last third, on the
template's pixels): the display's drawing is the same picture all clip long, the scene that was held at the start has
left by the end. Under 0.5 it says so, as a `no_power`, and asks for `--anchor X0,Y0,X1,Y1@N` (match only a box of frame
N round the drawing) or, for a coloured drawing, `--drawing chroma`. A sensor that never slews makes the two layers one,
and then holding either is right. **The check is weak:** it read 0.65 on the failed run, because over 5 s the clouds
stayed in view. What decides the failure is how much drawing there is, not how rich the scene is: with a fixed
Oman-style reticle drawn on the same panning clouds (`stabilize_selftest.py --overlay`), all 150 frames are held to the
truth, 0.12 px per-frame median near the centre and 0.48 px rms over the view, with the planted tremor (8.99 Hz) and
vibration (7.69 Hz) recovered from the hand's spectrum. PR144's own drawing is a few small orange marks, its corner
brackets jump at a zoom step, and its north pointer moves; `--drawing chroma` matches them at 0.98 but they are not a
fixed drawing to test against. The portable test (`tests/test_stabilize.py`, a 480 x 320 reticle on a grainy display)
holds to 0.08 px rms, and an Oman-like 1080p self-test (`--overlay --scene flat`: fixed pattern, grain, H.264, repeated
frames) to 0.20 px near the centre and 0.31 px rms over the view.

**What it writes.** `<tag>_stabilize.csv` (each frame's homography from the held video's pixels to the clip's, and the
derived motion), `<tag>_stable.mkv` (FFV1, lossless, every frame of the clip so that frame n is frame n, the canvas the
reference view extended where the hand showed more), `<tag>_stabilize.png`, and with `--track` the track carried onto
the held video. A measurement that needs the clip's own pixels -- `flicker`, whose codec controls need the clip's GOP --
runs on the clip with a track carried back through the homographies.

**Traps.**
- *A filmed display's "grain" may be the sensor's fixed pattern.* On PR118 it correlates with itself at zero shift
  (ZNCC 0.8-0.9) across 160 frames: it is fixed on the display, not sea. It cannot measure the sensor's slew, and an
  object crossing it reads it as brightness noise; on the held video a running median takes it out like a flat field.
- *Repeated frames are not motion.* A variable-rate phone padded to 30 frames a second repeats a frame where it took
  none; two marks a frame apart that agree to a pixel may be one picture twice (PR117's frames 1 and 2).
- *Two exports of one recording are not two captures.* PR122 is PR121 from 8.07 s on, exported separately: the hand's
  path agrees to 3-4 px over 460 frames, and the repeated frames fall in different places, so each export's frame times
  are good to about 1/60 s.
- *Where the canvas sits is not held to the last digit of another arithmetic* (measured 2026-11-14; IDEAS.md G7). The
  template keeps at most 30,000 points a level by a fixed draw over the count of its strong pixels (`Template`), so
  one pixel more or less among them redraws every point. On the `--overlay` self-test, pass 1's answers moved by 1e-6
  px (what another arithmetic's rounding does) moved the final homographies by 0.46 px at the frame's corners (1.5 px
  at worst), while the frames' agreement through the true homographies stayed 0.03 px rms: the held video is as still,
  its canvas placed a little differently. Compare two runs by how still each holds the display, not by the last
  digits of `H`. On one computer a run repeats itself (0 and 8 workers: 1.4e-8 px apart).

## 15. `mcdonald aspect` -- does it look the same from every side? (added 2026-10-18)

From the gliding-birds theory (ROADMAP 0.5, "slow modulation of brightness, size and elongation at the roll and heading
periods"), built for the Gulf of Oman phone captures (PURSUE PR117-PR122, D101's "cold orbs"), where the beat test
had little or no power and no range or field of view exists. A sphere looks the same whichever way it goes; a body
with wings does not, above all when it banks. The stage asks whether an object's brightness and size follow its
heading, with no range, field of view or beat.

**The physics it rests on.** A flat planform held level presents the area A sin(eps) at depression eps from every
heading, so a level glider in a straight line is invisible to a heading test. A flyer that turns on its wings banks by
phi = atan(V omega / g); the bank tilts the planform towards the sensor on one side of a loop and away on the other, a
first-harmonic swing in brightness of about cot(eps) tan(phi). Bounded by the test, tan(phi) <= A1 tan(eps), and the
speed through the track's own turn rate by V <= g tan(phi) / omega (`bank_bound`, with `--depression`). A
self-luminous or sun-lit body has more terms; the bound is for a thermal planform of uniform temperature.

**How** (the module's docstring has the steps). Every new frame between the track's first mark and its last is
measured, marked or not. The heading comes from a local quadratic through the track. The flux, and an elliptical
Gaussian's size and long axis, are measured against an annulus, or, with `--still`, first against a running median of
the frames with the object masked. The flux's fractional deviation is fitted with time, place and speed terms, with and
without the heading's first and second harmonics. The heading terms are judged against 1000 time slides of the heading
series against the flux; a slide keeps every series' own autocorrelation, and keeps the place effect with the flux. A
round blob of the object's own size and depth, planted along the same path moved to clear picture, is the false
alarm; the same blob modulated by 15 % at theta and at 2 theta is the completeness.

**The trap: heading and place.** On a clean circle the heading is a function of place (the velocity is square to the
radius), so a place effect and a heading effect are the same columns, and least squares returns amplitudes of
hundreds of per cent. The stage reports the heading terms' R^2 on the place-and-time model (`heading_place_r2`). It has
no power when that is above 0.995, or when the time slides admit an effect over 30 %. Wandering loops (synthetic,
R^2 0.96) are still told apart: a round blob is not called (p 0.37) and a 25 % effect is read as 25.2 % (p 0.001).

**PR121 (the case).** Two contacts loop about the boresight of the held display (`mcdonald stabilize`), through 3.5
and 3.7 turns in 13 and 11 s. Their brightness follows the heading by 2.7/2.5 % and 4.7/3.6 % (1st/2nd harmonic),
p 0.83 and 0.46, with time-slide 95th percentiles of 7-8 %; the planted 15 % modulations are read as 11-17 %. Size does
not follow the heading. The elongation lies along the motion and vanishes at zero speed: smear. If those loops are the
contacts' own turns, a winged flyer turning on its wings is excluded (at eps = 45 deg its bank is under about 5 deg,
its speed under about 0.4 m/s); a level glider is not tested, and loops made by the sensor's tracker are not the
object's turns at all.

## 16. `mcdonald waves` -- the sea as a ruler (added 2026-10-19)

**What it answers.** Where a clip shows the sea, what is one pixel in metres? Deep-water gravity waves obey
omega^2 = g |K|: a wave's speed fixes its length in metres. The sea's texture, as a sum of Fourier components in
rad per pixel, each turning its phase at a measurable rate in rad per second, obeys that relation for exactly one
image scale, and the fit of that scale needs no field of view, no range and no telemetry. The sensor's or
platform's motion puts one drift U (px/s) on every component, which the fit carries; an oblique view foreshortens
the along-sight axis, so the scale is m_x across and m_y = q m_x along, with q = 1 / sin(depression) for a flat sea
(1 at nadir, never under). The idea has a precedent -- Spencer, Shah & Guha (IEEE Trans. Image Processing 15, 2006)
fitted the deep-water parabola to the per-frequency phase rates of uncalibrated nadir water video and got the scale to
about 10 % with a static camera and twenty dominant wave periods -- and the joint fit of scale, foreshortening and
drift for an oblique, moving, uncalibrated thermal camera is what is new here (the literature report of 2026-10-19 in
the uap repository, `reports/Ocean wave dispersion as image scale.md`, has the lineage and the cost functions).

**What a component does.** With the frame s(x, t) and its 2-D Fourier transform F(k, t), a wave travelling along
+k puts the phase -(Omega(K) + k.U) t on F(k, t), and a wave travelling along -k, which the same bin holds as the
conjugate, +Omega(K) - k.U, with K = (k_x / m_x, k_y / m_y) and Omega = sqrt(g |K|). Each bin's spectrum in time
may hold energy at two places, nu_+- = -+Omega - k.U, split by 2 Omega: the split measures the dispersion whatever
the drift, and along one branch the shape of nu(k), sqrt(k) for dispersion against k for drift, tells the scale from
the drift. At one wavelength the two are one number: a fractional scale error is exactly a drift of that share of the
group velocity along the waves. A narrow swell therefore gives a scale only with the drift assumed, and the fit must
see a span of |k| (the radar practice: Young, Rosenthal & Ziemer 1985; Senet, Seemann & Ziemer 2001; the normalised
scalar product of Serafino, Lugni & Soldovieri 2010).

**How.**
1. Square patches of sea, read straight from the video as 8-bit grey; frames that repeat the one before are dropped
   and the rest carry their true times (a hold-and-jump cadence is read at the times it was shot).
2. `detrended`: the mean frame is taken out of every pixel and, when the record is at least twice `DETREND_S` (4 s),
   a running mean that long. What does not propagate -- a fixed pattern, thermal streaks, a slow level change, the
   texture's own skew that a median frame leaves -- sits at zero rate, and a bin that holds it beside a wave reads
   a rate between the two. This was the first thing that broke the fits on PR148: a line at zero rate through every
   |k| (`tools/waves_kw.py` draws the (|k|, rate) periodogram along the texture's dominant direction, with a known
   scale's curve over it; look at it before fitting anything).
3. `bins_of`: a Hanning taper, the 2-D spectra, and the bins kept: within the wavelength band (`LAM_MIN` 6 px to a
   third of the patch), the top quarter of each of 12 log-annuli of |k| by mean amplitude, so every wavelength the
   band holds is represented. Each bin's weight is a gate on its amplitude against twice the quietest annulus'
   floor, 1 / (1 + (2 n / a)^4), so a bin well above the floor counts once however bright.
4. Two estimators, kept because they fail differently.
   - `fit_rates` (`phase_rates`): each bin's rate as the circular mean of its frame-to-frame phase steps, fitted
     to r(k) = -(s Omega(K; m, q) + k.U) on a grid of theta0 (the side s), m and q, U linear in every cell, then
     polished; weights the gate times the coherence. It is sharp on a record of one second, where a periodogram
     would be 6 rad/s wide, but it assumes one wave per bin: bins holding waves both ways, or a wave beside
     something that stands still, read a blend (on PR148 it read 60 % of the periodogram's peak).
   - `fit_shell` (`periodogram`, `shell_score`): each bin's periodogram at the frames' true times, scaled so a lone
     steady tone is 1 at its peak, masked within one resolution element of zero rate and beyond `CODEC_FRAC` (0.45)
     of the Nyquist rate (the codec's 7.5-Hz cadence on a 30-fps PURSUE clip), and read at the better of the two
     branches; the weighted mean over bins, each bin weighted further by how tonal it is (its peak share: a bin
     with no steady wave has no say). A grid over m and q with a drift box, then q and U polished at every m so the
     profile over m and the best agree, then a polish of all four. Times need not be uniform. It sees both
     branches and resolves a sea with waves both ways, but its resolution is the record's length: it needs the
     dispersion to spread the lit bins over at least `MIN_RESOLVE` (one) resolution element, which a one-second
     record does not give.
5. What is reported: m_x, q, U, the scale along the dominant direction of the weight (`m_along`, `theta_deg`) with
   its band (the profile over m with q held at the fit's, read along that direction), the share on the shell against
   a drift alone (Omega = 0) and against the same frames shuffled in time, the |k| span that carried the weight
   (10th to 90th percentile), the dispersion's spread over the lit bins against the resolution, the share of bins lit
   both ways, and the drift fitted in each quadrant of the patch (`drift_by_quadrant`).

**Why the scale along the waves, not m_x.** Thermal texture is the along-sight slope: a facet tilted towards the
sensor reflects a different sky and shows a different emissivity, while a slope across the sight does neither to
first order. The waves the picture shows are therefore the along-look ones (the dominant direction of the weight was
81-91 degrees from the x axis on every PR148 and PR149 patch), and along one direction only the scale along it is
fixed: m_x and q trade along a ridge, and a fit with q free runs q to the grid's edge. With the depression known
(PR149: 26-32 degrees from the ship's proportions, q 1.9-2.3) `--q` holds it and m_x follows; otherwise the stage
reports m_along and says q is not fixed.

**No power.** The record cannot resolve the dispersion (`resolution`); the share on the shell under `MIN_SHARE` (0.15:
a real thermal sea reaches 0.2-0.35, a synthetic one 0.8); a drift alone within `MIN_OVER_DRIFT` of it; the shuffled
frames within `MIN_GAP` of it; the |k| span under `MIN_SPAN` (2); the band of scales at the grid's edge or wider than
`MAX_BAND` (4); the quadrants' drifts apart by more than `MAX_DRIFT_SPREAD` of the drift (a platform's parallax: use
smaller patches). For the rates fit also: explained under 0.8, a drift alone leaving under twice its residual
(`MIN_DRIFT_RATIO`), and a record of `PEAK_SPAN_S` (3 s) or more, which is the shell's.

**Validated (2026-10-19).** Synthetic seas (`waves.synth`: linear deep-water waves on a periodic world grid, a wind
sea, a swell or both, imaged at m_x, q with uniform, affine or rotating drift, perspective, a radiance not linear in
slope, noise, repeated frames and jittered times; `tools/waves_ladder.py`, 22 rungs on Slurm): on clean one-second
wind seas the rates fit reads 0.97-1.1x the truth and refuses a 100 px/s drift (aliased), a drift gradient, a
ten-second swell and a sea running both ways; it is hurt by jittered frame times (0.6x), a 0.6 radiance nonlinearity
(0.75x) and H.264 at 630 kb/s (1.3x). The shell fit reads 1.0-1.1x along the waves at 4 and 10 s. `tests/test_waves.py`.
On PR149 (hull 920 px: 0.163-0.228 m/px at the ship's rows, q 1.9-2.3) with q held at 2.1, the three patches clear of
the ship's wake read 0.218, 0.222 and 0.260 m/px against about 0.21-0.22 expected at their range, bands 0.18-0.35,
shuffled 0.02 against 0.30-0.33 on the shell; the patches in the wake's path read 1.5-2x high. With q free the same
patches give m_x 0.16-0.22 with q 2.8-3.5 and m_along 0.46-0.64 (bands x2-3 wide) against 0.41-0.46. On PR148 (vessel
218 px = 30-60 m: 0.14-0.28 m/px) three of five patches read 0.19-0.23. PR120's one second of sea (held display video)
is refused by every rule: too short for the shell, and the stepped phase explains 0.3-0.8 of the rates.

**Traps.** Frame-to-frame phase correlation cannot register a dispersive texture (the correlation peak was 0.06 on
PR149): `hold_sea`, an affine registration, is kept but off, and made things worse wherever it ran; a drift field has
to come from per-quadrant dispersion fits. A harmonic travels at its parent's speed and reads the scale low by its
order. A patch must hold several wavelengths of the longest wave used (the band's top is a third of the patch), and
the span in |k| matters more than the record's length. The scale holds at the sea's distance and only while the zoom
holds: on a clip that switches sensor modes it does not carry across the switch.

## 17. `mcdonald slew` -- k from the camera's own slew (added 2026-10-19)

**What it answers.** How many pixels is a degree? k is the binding unknown of every speed (`scale.py`), and its other
routes are a graticule (rare), a known-size object (a ratio, not a k), a zoom chain (needs one field from elsewhere)
and an assumed field. During a slew the scene moves on the screen by the camera's rotation, and on clips that draw a
north pointer the rotation is drawn too: `symbology` reads the pointer's angle theta every frame (clockwise from
screen-up, = -azimuth), `layers` measures the scene's shift. Regressed one on the other, the scene's horizontal shift
has slope **c = k cos(e)** px per degree of the pointer, with e the line of sight's depression. It is the matchmove
with survey data -- a nodal solve (Hartley 1997; de Agapito, Hayman & Reid 2001) with the angles read off the screen
-- and on a narrow turret field, where the frames' own homographies are nearly translations and constrain nothing,
the pointer is what makes it possible (`analysis/methods/visual_arts_methods_survey.md` §5.2 in the uap repository).

```bash
mcdonald symbology CLIP.mp4 --step 1 --method template --tpl-box X0,Y0,X1,Y1 --out CASE   # the pointer, every frame
mcdonald layers CLIP.mp4 --out CASE                                                       # the scene's shifts
mcdonald slew CLIP.mp4 --out CASE [--window T0:T1] [--depression D]
```

**The model.** X(t) = a_s + c theta(t) + b t. The b term is the platform: a camera that holds the ground still (PR148,
PR149) turns the pointer at the rate the aircraft's motion across the line of sight asks for while the scene stays
put, so a window where the pointer turns at one steady rate cannot separate c from b. The lever is the part of theta
a steady rate does not explain: the slew's start and stop. a_s is one offset per unbroken stretch of the scene's chain.

**How.**
1. The pointer: `symbology --method template --step 1` (`--min-ncc` and the new `--search` where the glyph is hard
   to hold). Readings off the clip's radius by more than three robust scatters or 3 px are dropped, and so are
   readings more than 3.5 px along the arc off the repeated-median line through those within 1.5 s: the pointer is a
   gimbal's angle and cannot jump and come back, and a template matched at a low score locks onto a stroke of the
   glyph (PR148 at NCC 0.55-0.65 read 0.9-1.4 deg low for a second at a time). A run of such readings longer than
   half the window outvotes the line, so the filter is a guard, not a cure. The pointer is drawn on a grid -- PR148's
   "N" moves in 3.25-px steps across -- so its angle is a staircase; the stage measures the step (the median jump
   between readings that moved) and takes a reading's scatter as the step over sqrt(12).
2. The scene: `layers`' k-frame shifts of the largest motion group, chained into a path. A frame step is the mean
   of the pairs spanning it (a triangular kernel, which the pointer is then smoothed with too, so the two agree).
   `layers` leaves out shifts within 4 px of zero over k frames and measures a held scene again over a second, so
   a scene moving 1-4 px in five frames -- a slew easing in or out -- has no consensus at all; runs of up to 2k such
   steps are **bridged** at the velocity drawn across them (the synthetic pan broke into 24 stretches exactly there
   before the bridge, and those steps are the lever). A longer gap ends the stretch: its frames have no place on
   any stretch, and the next begins where the steps are measured again. A window whose chain comes in pieces under
   a second long on average is refused (each piece's offset is free). With the largest group (`--layer all`), a
   window where over a fifth of the pairs hold two motion groups is refused too: the largest group switches between
   layers that move at different rates (PR144's sea and cloud tops, 97 px/s apart), and the chain mixes them.
   Graphics drawn in place mid-picture -- a tape, an arrow, a reticle -- hold `layers`' pairs at zero shift unless
   masked: `layers --mask-box X0,Y0,X1,Y1[:N0:N1]` (repeat) takes them out without the rows round them.
3. Windows: given (`--window T0:T1`), or one round each slew the scene shows, from 3 s before it starts to 3 s
   after it stops. A whole slew, not its start and its stop apart: half a slew in a window looks to the steady-hold
   check like a hold that changes (the rendered pan read 554 and 480 px/deg in windows round its start and its stop,
   each moved 34 % by a quadratic hold, and 484-524 in one round all of it). Different slews are kept apart.
4. The fit, **the reverse way round**: theta on X and t, c = 1 / beta. The pointer is the noisy one and the scene's
   chain is not, so noise in theta does not bias beta; the forward fit (X on theta and t) is pulled low by
   1 - 1 / (1 + (scatter / lever)^2) and is reported beside it, and the truth lies between the two. A block
   bootstrap (1-s blocks) gives beta's interval.
5. Three outcomes. **Registered** (beta's 95 % interval above zero): c with its 16-84 % interval, refused where the
   pointer's turn beyond the hold is under 1.5 scatters or under 0.55 of its grid step, the forward and reverse
   slopes are more than 35 % apart, the interval is wider than +-25 %, or a quadratic hold moves c by more than
   15 %. **Not registered** (the interval holds zero): a floor, c >= 1 / B with B the interval's larger side, and
   only for a slew within 20 deg of the horizontal (a slew mostly in elevation can reach the pointer through a
   tilted image or a projected north). **Against** the scene: the pointer is not reading the turret's azimuth with
   this sign.
6. The scale: c is k cos(e), so k >= c and **W / c is a ceiling on the field of view**, reached only at a horizontal
   look -- the direction a ceiling on a speed needs. With `--depression` the field itself.

**What it assumes, and says on every run.** (1) The pointer is an azimuth dial (theta = -az): **tested on PR051**
(below). If it draws ground
north projected into the image, its rate is the azimuth's times sin(e) / (sin^2(e) cos^2(b) + sin^2(b)), b the bearing
of north from the line of sight, and c is off by that factor; if it draws north against the platform's heading, it
turns with the platform and not the turret and registers no slew at any k. (2) The image is level, so a turn in
azimuth moves the scene across it; the theta-driven motion's direction is fitted too, and beyond 20 deg off the
horizontal c is reported as a bracket between the horizontal slope and the whole one. (3) The hold is steady over
the window. (4) Square pixels, or `--pixel-aspect` (a 4:3 picture shown full-height in 16:9 is 1.333): the
glyph's place and the scene's shift are taken back to square pixels, and k is given in them. Near the top or bottom of
its circle the pointer moves sideways and its angle is stretched with the picture; near the sides c is stretched by the
square of it.

**The pointer's convention, tested on PR051 (2026-10-20).** PR051's MTS-B display draws the pointer beside the
aircraft's heading, the sensor's azimuth relative to the nose and `TGT A`'s `BRG` (the bearing of the line of sight's
ground point; heading + relative azimuth = BRG on every reading). Read by eye every 2 s over the original stretch (39
readings, two framings: the aircraft turns 126 -> 44 deg and then 298 -> 231 while BRG runs 9 -> 1 and then 1 -> 15, the
second in the opposite sense to the heading) against the pointer read by `symbology` on every second frame: theta =
c + 0.965 (+-0.021) (-BRG) + 0.000 (+-0.004) (-heading), rms 0.48 deg, in square pixels. The pointer is the line of
sight's azimuth with unit gain to 3.5 %; north against the heading has no share, and ground north projected into the
image (depression 5-7 deg) misses by 13-15 deg rms. In the upload's own pixels the gain is 1.276 +- 0.028: Corbell's
upload shows the 4:3 sensor full-height and stretched to 16:9 (with the gain held at 1 the stretch fits at 1.30-1.35),
which is what `--pixel-aspect` is for. The k half of the test is not possible on PR051: its line of sight sweeps the
terrain (BRG turns 0.3 deg/s against a 0.08 deg/s ground hold) at a field of 0.08 deg, and the faint RS-170 ground does
not register. The uap repository's `analysis/cases/pr051/pr051_pointer_convention.md` has the readings and the fit.

**PR051's k, the known answer (2026-10-27).** Corbell's upload of PR051 (`/models/data/mcdonald/pr051/`) shows the
data bar the release redacts, and in its first framing the field is NAR to 14.0 s: FVW / SLR = 0.6427 deg +- 0.15 % over
5-13.9 s, so k = 1440 / 0.6427 = 2240 px/deg in square pixels and c = k cos e = **2230 +- 10 px/deg** at its 5.1-5.4-deg
depression; then ULTN (x2.001) and 2X of it (x1.995). The line of sight sweeps the terrain (the scene at 400-460 px/s in
the upload's pixels) while the pointer turns at -0.13, +0.43 and +0.24 deg/s over 7-9, 9-11.3 and 11.3-14.2 s. Three
things stood in the way. (1) The overlay is not masked by itself: the analog capture jitters the whole picture, so no
pixel holds within 2 grey levels, and the clip reads as colour; unmasked, `layers` read the scene still in 88 % of
pairs. Twelve boxes by hand (`layers --mask-box`) fix it. (2) The scene moves in jumps a few unique frames apart, so
most pairs fall inside a hold: at `--k 2` 90 % of pairs, at `--k 8` 72 %, are "held still" and left out, and the chain
breaks; only 5.1-8.3 s chains whole. (3) The pointer is mislocated at 4-6 s, over bright ground. On what is left `slew`
gives **NO POWER and a floor, c >= 1087 px/deg**, which the truth (2230) clears. With the platform's share of the turn
known from the data bar (the aircraft about 70.9 m/s across a line of sight at 58.1 km: a ground point's bearing turns at
-0.070 deg/s, the pointer's hold +0.068), `slew --hold-rate` (below) needs the scene chained over 7-14 s, which the
held pairs prevent. Taken as real zeros (a scratch edit), they chain it, and with the hold given the stage measures 549
px/deg and refuses it (forward and reverse 71 % apart, the bootstrap +-32 %), the pointer's rate and the scene's
anti-correlated (r -0.52): in this edit of the footage the pointer and the picture do not move together frame by frame.
Why, read against the data bar itself (2026-10-28: the aircraft's position and TGT A's grid every 0.5 s over 3-14 s,
`/models/data/mcdonald/pr051/pr051_databar_track.csv`, the line of sight's true azimuth from one to the other): the
pointer is a dial drawn in 0.2-0.5-deg steps that sits still for up to 2 s while the azimuth moves 0.6 deg, then catches
up -- off by 0.17 deg rms, 0.11 drawn straight between its steps -- so over NAR's 11 s its swing beyond a steady rate is
about one of its steps, and NO POWER is right; the anti-correlation is that lag. Its mean rate is right (0.25-0.26 deg/s
against the bar's 0.26; the hold 0.074). The scene moves on at the bar's 445 square px/s, in a picture that repeats and
catches up (§3); each step measures (frames 439-441: 108 px against TGT A's 99), but `layers` called most pairs held, and
on its streaky terrain most pairs have fewer than the 8 good templates a consensus needs: with pairs of whole frames
(`--k 2 --step 2`) and the repeats taken as unmoved, 12 % of pairs reached a consensus and the chain held 5-7 s at 71 % of
the bar's motion. With each template weighed by its own error and the streak-bound ones counted across their streaks
(K9, §31, 2026-10-28) 37 % of pairs reach one, and the chain holds in one stretch over 5.0-9.5 s at 94-95 % of the
bar's path (1740-1764 against 1848 square px, the window alone or inside the whole stretch; the path's own error +/-7)
-- the golden check `test_pr051_scene_path_against_the_data_bar` -- then breaks at 9.5-10 s and runs at half the bar's
rate over 10-13 s, where every other catch-up step still finds no consensus at all (held, then measured again over a
second with none). The data-bar track is the known answer for any scene measurement here.

**A hold given (`--hold-rate`, added 2026-10-27).** On a moving platform a steady pan is the hold's twin: the fit takes
the whole turn as the platform's and gives a floor. Where the platform's share is known from its own motion (a ground
point's bearing rate, v_perp / R), it is taken out of the pointer and the fit has no hold term, as with `--still`
(whose hold is zero), so a steady pan gives k. The rate-correlation refusal (PR076's) then does not apply: it guards
against a fitted hold that drifts, and a steady pan's rates have nothing to share. Synthetic (`tests/test_slew.py`): a
steady pan of 0.15 deg/s on a platform turning the pointer -0.07 deg/s gives no k with the hold fitted and 2199 px/deg
against 2200 with it given.

**PR144 (2026-10-20): NO POWER.** The orange pointer is read on all 837 frames (radius 310.95 +- 0.92 px; steps of
0.18 deg) and turns from 176.8 to 170.8 deg, steadily but for a 0.7-deg bump at 14-16 s; the camera pans after the
contact the whole time, mostly in elevation (306 px rms down against 232 across beyond the hold). The largest group
mixes sea and cloud tops (two groups in 32 % of pairs); the sea alone reads 2872 px/deg (16-84 % 2341-4246) with the
forward fit at 836, refused; the cloud tops' slews are mostly vertical. The zoom check (k before and after the x5.9
step) needs a slew in the wide view, which lasts 2.5 s and has none.

**The known answer: AARO's Puerto Rico 2013 video (2026-10-20).** Its WESCAM-style display gives the line of
sight's true azimuth and slant range, and the latitude and longitude of its ground point, every frame. The ground
left behind when that point moves gives k with no pointer and no field-of-view table: the scene moves across by
-k (dG . right) / R. Over t = 82-117 s (`IR 675`, the target read by eye every 2.5 s, the scene matched with the
display's fixed graphics masked by hand -- `layers`' whole-row masks left the tape, the arrow and the reticle to pin
60 % of its pairs at zero), **k = 1657 +- 79 px/deg** in square pixels (a field 1.10 deg across), so k cos(e) = 1640
at the 7.9-deg depression. Its north arrow, which rotates in place and is read by a reader of its own, is the line
of sight's azimuth at slope 1.0013 +- 0.0039 over 286 deg -- the second sensor family after PR051's MTS-B -- in square
pixels: this upload draws its pixels 0.875 as wide as tall (`--pixel-aspect 0.875`), from the arrow's span against
its angle. On it the stage **refuses, correctly**: with a steady hold it reads 255-294 px/deg, six times low, and
refuses it (forward 56-61 % apart; a quadratic hold moves it 82-92 %: the aircraft orbits, so its share of the turn
is not steady); with a quadratic hold the slew is not registered and the floor is 390, consistent with 1640. The
camera follows the lanterns at a nearly steady rate (the scene drifts ~700 px/s, +-20 %), and the method needs a
change of slew rate against a steady hold, which no clip tried so far (PR148, PR144, PR051, this) has. The uap
repository's `analysis/cases/aaro_puerto_rico/README.md` has the readings, the readers and the fits.

**A data bar in place of the pointer (`--platform`, `--los`; added 2026-10-29).** Where the display prints the
aircraft's position and the line of sight's ground point -- the files `mcdonald drift --platform --los` reads (frame,
lat, lon, alt_m; frame, tgt_lat, tgt_lon, tgt_elev_m) -- they are the pointer: the line of sight's azimuth at each
reading, drawn straight between readings, and with it the platform's share of the turn, frame by frame: the bearing of
the ground the boresight was on, seen from where the aircraft has got to, less its bearing from where it was
(`bar_series`). What is left is the line of sight's turn against the ground, which is what the scene shows, so no hold
is fitted (an orbit's share is no longer a steady rate to be fitted), and the depression is the bar's own (the median
over the windows). A reading's scatter is the positions' grain -- the least step between two of them, an arc-second
(29 m) on this display -- over the median range, and the bootstrap draws blocks two readings long, since the frames
between two readings are one reading's worth. With only the azimuth and depression (frame, az_deg, dep_deg) the bar is
a pointer and the hold is fitted as before. Drawn (`tests/test_slew.py`): an orbit at 3 km and 100 m/s, a turret
following a thing that drifts, the bar every 2.5 s to an arc-second: k 1655 px/deg for 1650.

*Held against the Puerto Rico clip* (2026-10-29; `layers --k 5 --max-shift 30` over frames 2440-3530 with the six boxes
above, 1069 of 1086 pairs reaching a consensus; the bar's 39 readings as vendored for the drift stage): **k = 1720
px/deg over 82-100 s, 1727 over 82-107 s and 1773 over 82-117 s** at the bar's depression (8.2-8.5 deg), against the
case's 1657 +- 79: +0.8, +0.9 and +1.5 of its sigmas. The case's number regressed the scene's shift on the bar's
(through the origin, interval by interval), and the bar is the noisy one there -- the ground point printed to 29 m on
moves of 50-120 m between readings -- so it is pulled low, as the forward fit is here; the same intervals on the same
scene chain taken the other way round, or as the whole shift over the whole turn, give 1690-1696 (82-100 s) and
1718-1727 (82-107 and 82-117 s), and the stage agrees with those to 1-3 %. Its own 16-84 % band is narrower (+-1-2 %)
than the spread between windows: **over 100-117 s it reads 1844**, +7 % on the earlier windows, and over 107-117 s
1615, -6 %. The ground point jumps 0.3 NM from the hills to the sea at 107-109.5 s, 381 m of it along the line of sight
and the range 9.7 %, and the hold is taken at that range, but the jump is not shown to be the cause (2026-10-30): the
range drawn straight through it, on both sides, leaves 100-117 s at 1800-1896. Short windows differ this much with no jump
in them: 82-91 s and 91-100 s read c 1678 and 1837, and a reading's bearing is good to about 0.14 deg against a net turn
of 0.8 deg between readings, so a window is only as good as its length against the bar's grain. A warning on the
jump was tried and left out: it would fire (the step in the range times the hold over the net turn reads 0.14-0.19 on
windows holding the jump, at most 0.083 on the others, 0.096 at 1 in 1000 on bars drawn with the arc-second's grain), but it
would name a cause not shown, and imply that the windows it passes are good. A hold term in time moves c by 13-26 % on
every window: the lever is the steady follow itself, so k is only as good as the bar's hold. The golden check
`test_puerto_rico_k_from_the_data_bar` runs the stage on the vendored readings (`tests/golden/puerto_rico_drift/`) and
scene shifts (`tests/golden/puerto_rico_scene_layers.csv`).

**A still platform (`--still`, 2026-10-20).** On the ground, a ship at anchor or an aerostat the platform adds
nothing to the pointer's turn, so the hold term is dropped (degree 0) and the whole turn is the slew's: then a steady
pan gives k, which on a moving platform is the hold's twin and gives nothing. The rendered pan (`slew_selftest.py
--hold-rate 0 --pan 0.4 --still`) reads 511 px/deg against 519.6 (16-84 % 503-544); the same pan on a platform turning
the pointer 0.33 deg/s, fitted with a hold, is refused ("did not slew beyond a steady drift"), as it must be. Where the
method works, then: a still platform (any pan); a moving one in steady straight flight with a slew that starts, stops
or changes rate inside the window; never an orbit, whose share of the turn keeps changing.

**The real known answer: a broadcast camera (2026-10-20).** PTZ-SLAM's soccer sequence (Lu, Chen & Little, BMVC
2019; reference data `ptzslam_soccer/`) gives every frame's pan, tilt and focal length for 330 frames of a broadcast
camera on a fixed base -- a still platform, real compression, players moving through the scene. With the pointer
taken from the ground truth's pan (the only part not read off the picture), `layers` with the score banner
box-masked, and the window where the zoom holds within +-3 % while the pan reverses three times (t 1.0-6.5 s):
**c = 73 px/deg (16-84 % 73-74) against f pi/180 cos(tilt) = 72.0** (68.9-73.3 over the window), +1.4 %, with the
exact pointer and on a 0.25-deg grid, with `--still` and with a hold fitted (the reversals are the lever either
way); the field's ceiling 17.5 deg against the true 17.6. The automatic window gives the same. At the wide end
(t 9-11 s, a 1.1-deg pan) `--still` reads 37 against 33.3 (outside its interval: the pan is a tenth of a degree's
annotation error from 1.1 deg) and the fitted hold refuses; through the zoom-out the scene's chain breaks (a zoom's
radial flow has no one shift), as it should. `tools/slew_ptz_check.py` reruns it. This is the method's first
measurement of k on real footage against a known answer; the PURSUE and AARO clips refused because their
platforms' share of the turn could not be separated, not because the method failed where it could be.

**The path filter turns round with the camera.** The broadcast pan reverses at up to ~4 deg/s^2, and a line through
three seconds of pointer readings left out 48 of the 330 true ones at the reversals. Where the line misses more
than a tenth of its window and a parabola fitted by consensus (RANSAC over triples, `robust_curve`) explains 95 %,
the parabola judges: 312 of 330 kept, c unchanged. A window holding a run of mislocks reaches 95 % with neither and
stays with the line, which drops the run (a parabola alone kept 22 of a synthetic 30).

**A floor stands only beside a registered slew.** A pointer blind to the turret yields a floor at any k:
`tools/slew_selftest.py --pointer heading` gives a floor of 1355 px/deg against a true 520. So a clip on which the
pointer registers no slew at all is NO POWER for k -- "either the field is that narrow or the pointer does not follow
the turret, and this clip cannot tell which" -- and a floor is reported as a result only when another window of the
same clip registers a slew and passes every check.

**Validated (2026-10-19).** Series (`tests/test_slew.py`): a clean slew within 2 %, the hold rate and the elevation's
tilt recovered; a pointer on a 0.45-deg grid within 6 % at six phases of the grid while the forward fit reads 5-7 %
low; a gap of 1.5 s kept as two stretches and a gap at the slew's start bridged, both within 3 %; no slew refused; a
slew of a fifth of the grid step and a pointer blind to the slew give floors, never a k; a 1.5-deg slew on a 1.07-deg
grid refused. On synthetic staircases (eight phases of the grid each) c came back within 9 % at a lever of 0.55 of
the grid step, 6 % at 0.7, 1.5 % at 1, and 15-26 % off under 0.45: the rule, and the grid share reported with every
c (about 0.025 / L^2 at a lever of L steps), come from these. Rendered pans (`tools/slew_selftest.py`: a rigid
textured scene held by a ground-stabilised camera while the pointer turns at 0.33 deg/s, then a 2-deg slew with the
elevation in step, the "N" drawn on a 1.6-px grid at 0.28 H from the reticle, one frame in nine repeated, H.264; run
through `symbology`, `layers` and `slew` as a user would), k cos(e) = 519.6 px/deg: read as 484 (16-84 % 459-585; 524
in a window 1.2 s longer, so the window moves it by about as much as its interval); with the elevation moving as much
as the azimuth (49 deg off the horizontal) 485, the bracket flagged; a 0.5-deg slew not registered (NO POWER, a
conditional floor of 336); a pointer blind to the slew NO POWER (a conditional floor of 1355); the grid at 3.2 px
(steps of 1.07 deg) refused at 0.45 of a step, where it read 452. A scan of a time lag between the pointer and the
picture finds the rendered pan's at 0 to 0.1 s with a sharp minimum; it is a check not yet in the stage.

**PR148, the first real clip: NO POWER** (case note `analysis/cases/pr148/pr148_slew.md` in the uap repository). The
pointer is read on 754 frames at NCC >= 0.7 (radius 295.1 +/- 0.7 px), on 1628 at 0.55 after the path filter; it moves
in steps of 0.24-0.28 deg. The scene: held 0-11 s, 2200 px across in 11-18 s, about 1000 across and 3000 up over
20-46 s, held 46-60 s; the pointer is a smooth arc from 249.4 deg up to 258.1 and back, its hold going from +0.33 to
-0.48 deg/s over the minute. The first slew registers, with the right sign, in both readings (c 1123 and 1789 px/deg,
16-84 % 908-1917 and 1236-3216) and is refused by every check: the forward fit reads 270 and 627, a quadratic hold
moves c by 42 %, and the glyph is unreadable for the two seconds before the slew starts (9.2-11.3 s: the "N" is
smeared into another shape, the codec's work on the moving sea behind it). The later slews are mostly in elevation
or not registered. If c were 1100-1800 px/deg, the vessel's 218 px (a 30-60 m hull, seen broadside at a level look)
would put it 9-28 km away, and the hold of 0.33 deg/s would mean 50-160 m/s across the line of sight (75-120 for a
45-m hull): a plausible aircraft, which makes it a consistency check and not a measurement.

### Zoom states: `mcdonald zoom`, and `slew` across a zoom (added 2026-10-20)

**Why.** The pointer sweep of PURSUE (2026-10-20, in the uap repository) found that the MQ-9's MTS-B changes its field
during short bursts of blank or flash frames, and every clip tried has them: PR27 four in 297 s, PR067 nine. `slew` did
not know. On PR27 automatic windows across the 82-s step fitted one c to two fields, and some passed every check; the
whole clip was refused because "the windows disagree" (three windows at 268 px/deg, and a floor of 1238 two steps
later); and the best internal check the method has went unused: across a step the ratio of c is a measurement of the
zoom, and so is the picture.

```bash
mcdonald zoom CLIP.mp4 --out CASE          # the bursts, each a step (x s), no step, or unknown; writes CASE/<tag>_zoom.json
mcdonald slew CLIP.mp4 --out CASE          # reads that file (or makes it), cuts its windows at every burst
mcdonald slew CLIP.mp4 --out CASE --no-zoom   # as before: the clip taken as one field
```

**The bursts.** A pass over the whole clip at 192 px wide (`zoom.scan`, half a minute for PR27's 8920 frames): each
frame's contrast, mean level and change from the last, over the middle of the picture, leaving out pixels with a
colour cast and pixels black or white (a redaction box on a blank white frame is contrast otherwise). A burst is a run
of contrast collapse (`forensics.transients`) or a frame whose level jumps 20 grey levels while its change is five
times the usual there: AARO's Puerto Rico clip goes dark for three frames at each switch with its contrast intact
(15 against the usual 20-29), and only the white frame after them collapses. Bursts under a second apart are one
change of the optics (PR27 at 82 s is grey, white, grey within half a second).

**The frames either side** (`zoom.edges`). The last good frame before the burst and the first settled frame after it:
the frame's change into it and on to the next two, and the drift of its mean level over them, within twice the
clip's usual there (the larger of the medians over 2 s before and over 1-3 s after, since a zoom in doubles the
scene's motion in pixels), and its contrast not collapsed. The level is the gain: on the Puerto Rico clip it climbs 2
grey levels a frame for ten frames after each blank, while the ground's own motion makes the change from frame to
frame as large as that anyway; the change alone took a frame one after the blank, mid-climb.

**The fit** (`forensics.zoom_fit`, `zoom_fit_frames`). The later frame shrunk by s and found anywhere in the earlier
(s > 1, zoomed in), or the earlier shrunk by 1/s and found in the later; s on a log grid from 1/8 to 8 in steps of 6 %
on frames halved, then 0.5 % steps at full size about the best, and a parabola. The narrower frame is shrunk first
and then high-passed (a Gaussian of 10 px at 1080 rows) in the wider frame's pixels, so both hold the same band of
scales: the other way round, x5 kept only detail under 2 px of the wider frame (Puerto Rico's 20.5-s switch: ZNCC
0.25 that way, 0.62 this way). Each trap the handoff listed is a rule:

1. *The whole picture is searched* (the template is the middle half of the shrunk frame at x1, more as s grows): on
   the Puerto Rico clip the ground moved 300-400 px during each blank, and `zoom_ratio`, which looks within 60 px of the
   boresight, read x1.0 at every switch.
2. *The overlay matches nothing.* Pixels with a colour cast, pixels black or white in both frames (boxes, white text),
   and the clip's static overlay (`forensics.static_masks` on 40 frames spread over the clip: the Puerto Rico display
   draws grey and white text and tapes over a light scene) are dilated, filled with the picture round them (a
   normalised convolution), and set to zero after the high-pass; a placement with under 60 % picture under it scores
   nothing. Unmasked, PR27's overlay fitted x1.00 at ZNCC 0.75 against a blank white frame. Only black and white are
   taken as held between the two frames: in a stare the whole scene is held.
3. *The sensor's fixed pattern is taken out.* Twelve frames over up to 8 s of each side's optics give the median of
   their fine detail, which keeps what does not move with the scene (the detector's pattern, the vignette's ring); it
   is scaled to each frame by least squares and subtracted. Where it explains over 70 % of a frame's detail, the
   frame is mostly the sensor's (or its scene held still) and the burst is unknown.
4. *The scale is chosen by the peak's prominence, not its ZNCC.* The best ZNCC grows as the template shrinks, so on a
   scene whose detail repeats the grid's far end wins: Puerto Rico's sea read x8 at ZNCC 0.48 where the truth is x3.05
   at 0.44. The prominence -- the peak over its correlation surface's median, in robust standard deviations (1.4826
   MAD) -- counts a peak against the noise of its own template's size, and chose all three of that clip's measured
   switches (16, 12 and 10 MADs, against at most 9 at any other scale).
5. *A fit is a number only when it earns it:* the most prominent scale not on the grid's last step either end, at least
   8 MADs, leading the most prominent scale a quarter or more away from it by x1.25 (and x1 by as much, for a step),
   at a ZNCC of 0.15 or more. "No step" (within 8 % of x1) needs the fixed pattern taken out on both sides too: the
   pattern matches itself at x1 and nowhere else. Anything else is "unknown" -- never a step, and never none.

**The states.** The stretches between bursts; a "no step" burst joins its neighbours into one state. Each state's
magnification is the product of the measured steps since the last unknown burst (its chain), so states on one chain
have a known ratio of fields and states on different chains have none.

**In `slew`.** Automatic windows are found within each state (the threshold is the state's own largest rate, so a
narrow state's fast pixels do not hide a wide state's slew) and cut at every burst with 12 frames clear either side,
pieces under 3 s dropped. A window given by hand across a step or an unknown burst is refused. Claims are combined
and compared within a state only: a floor in one state never refuses a claim in another. Across a measured step on
one chain, the ratio of the two states' c is set against the imagery's s, and must agree within twice their combined
error or 5 % (a different depression either side moves cos e too, which the message says); a claim in one state and a
floor in another are checked the same way, the claim carried through the zoom. The report has a line per state, and
the top-level c is the best-measured state's.

**Two more checks in `slew`, from the same sweep.**
- *The rates must follow each other.* PR076 passed every check at 122.9-169.2 s (c 526) while the pointer's rate and
  the scene's correlated at r 0.24 at every lag: the c came from slow curvature over 46 s, which a drifting hold
  mimics. A claim now needs the two rates, each smoothed over 0.2 s, to correlate at r 0.5 or more at their best lag
  within +-6 frames. Not with the hold given (`--hold-rate`): a steady pan, which that is for, has no rates to
  correlate. Known and open (2026-10-28): PR051's pointer is a dial drawn in steps that stalls up to 0.6 deg behind
  the azimuth and catches up, so over 7-14 s its turn is the slew's but its rate is not (r 0.05 at every lag), and
  with the hold given c came from the totals, 2843 px/deg (16-84 % 1969-2855, the forward fit 2112) for a truth of
  2230: inside the band, a quarter high at the point. A test for a dial that stalls beyond its grid is what would
  refuse it; the rates gate cannot be applied to a known hold blindly.
- *The lag is fitted and reported.* c refitted with the pointer moved a frame either way, and at the best lag. On
  PR27's main slew the rates peak at -2 frames (r 0.996; 0.995 at 0) and a frame moves c by 1.1 %; a negative lag is
  the pointer drawn before the picture it is laid over reaches the screen.

**Validated.** Rendered (`tests/test_zoom.py`): x2 under the overlay with the view moved 160 px, x1.996 (ZNCC 0.94,
33.9 MADs; x1 3.4), and the narrower frame's middle where the view moved to; x1/3 as 1/2.983 (ZNCC 0.91); no step
with the view moved a fifth of the picture (51 MADs against 4.4 a quarter off), and unknown without a stretch to take
the fixed pattern out; the overlay alone, a blank white frame and x10 all unknown; haze behind a fixed pattern
unknown (the pattern left in, x1.00 at ZNCC 0.87: the trap); x2 behind the same pattern over a textured ground,
x1.996. Series (`tests/test_slew.py`): the windows fall one in each state and c comes back in each (499 and 1003),
their ratio x2.012 against the imagery's x2; given as x1.5 the check fails; taken as one field, the same clip's two
claims disagree by x2.01. Real clips (`tools/zoom_check.py`, the reference data's footage and series; Slurm, 14 min on
four CPUs):

| clip | burst | the imagery | known | |
|---|---|---|---|---|
| PR27 | 82 s | **x2.000** (ZNCC 0.72; 33.8 MADs, x1 11.8, a quarter off 14.2) | x1.98-2.00 by hand | step |
| PR27 | 89 s | x3.13 at 10.2 MADs, the next a quarter off 8.8 | featureless haze | unknown |
| PR27 | 134 s | 5.8 MADs | AARO: "zoomed 2:15"; x1.00 on the fixed pattern by hand | unknown |
| PR27 | 58 s | -- | the camera turns as it zooms out | unknown |
| PR057a | 32.8 s | **x2.001** (ZNCC 0.86; 42.1 MADs, x1 5.2) | x2.00 by hand | step |
| Puerto Rico | 20.5 s | **x4.966** (ZNCC 0.62; 17.0 MADs, x1 4.2, a quarter off 9.6) | readout x5; hand x5.05 | step |
| Puerto Rico | 118.1 s | **x3.096** (ZNCC 0.39; 11.3 MADs, a quarter off 8.7) | readout x3; hand x3.05 | step |
| Puerto Rico | 142.6 s | x1/3.096 at 10.7 MADs, the next a quarter off 9.4 | readout x1/3; hand x1/3.10 | unknown |

Puerto Rico's 142.6-s fit is the right number, but its peak leads the next scale's by x1.14, as the haze trap's at 89 s
on PR27 does (x1.16): the rule cannot tell them apart, and calls both unknown. Its later switches (155-212 s, the
aircraft 5-8 NM out over a flat sea) all lead by x1.04-1.14 and are unknown too; a hand fit could not confirm them
either. PR27's four single-frame jumps of the level after 134 s, while the object is tracked, are fitted too: one
no step (152.7 s), three unknown. `slew` across the steps: **PR27 267 px/deg before 82 s and 517 after, x1.932 against the imagery's x2.000**
(they agree within the 19 % their errors allow); **PR057a 276 and 584, x2.119 against x2.001** (within 16 %). The
same clips' other states give floors or nothing, each on its own chain.

**A zoom with no blank (added 2026-10-27).** An electronic zoom changes the scale between two frames with no blank
or flash; what it may step is the picture's level or its contrast. The scan's own
level and contrast are read for such steps (`events.picture_steps`, the rule `mcdonald events` uses, shared since; and
`zoom --events` takes an `events` run's), each placed on the frame of the largest change from the one before within
the 8 frames its medians are taken over (a clean step ties them, and the first tie is 3 frames early), and fitted
across as a burst is. One whose fit measures a step is a boundary like a burst (`kind` "picture" against "blank"); one
that does not is kept apart, in `picture_steps`, with its verdict, and the scale is taken to hold across it: a gain
reset or a switch of camera steps the picture too, and an unknown there is no reason to doubt the scale either side,
as a blank burst's is. At most 24 are fitted, the largest first (since 2026-10-28: 24 or 12 a minute, below). Rendered (`tests/test_zoom.py`): a x2 between two
frames, found from the contrast's step and fitted end to end through `zoom.measure` from rendered frames, is a boundary
of x2.00, and a gain step beside it no boundary. **The real known answer: PR051's leak** (Sitrec's copy of Corbell's
upload, `/models/data/mcdonald/pr051/`): its MTS-B display goes from 2X to ULTN at frames 1331-1341 with the picture
brightening for a few frames and no blank, and its data bar's FVW from 119 to 238-239 m at a slant range that holds
(22.91-22.93 NM), x1/1.999. `mcdonald zoom` finds it as a step of the picture and measures **x0.498 = 1/2.008**, 0.4 %
from the data bar. FLIR1's ATFLIR zoom at frame 2235, which has no blank either, is not found this way: over its sky
the scan's level and contrast do not step, and its six blank bursts are all unknown, the fixed pattern 85-88 % of
the detail at four of them; `camera` finds that zoom from the object's size and offset (§20).

**A zoom over streaming ground, and a long clip (added 2026-10-28, from the metallic-orb class study).** PR062 (MTS-B,
EO, 4.8 min) zooms six times with no blank. The first pass found the three zooms out (754, 7444, 7664) and none of the
three in, so its chain put 123-248 s at x0.5 when the field is back at the narrowest, and the last state at x0.12 for
x0.25. Two causes. (1) Over ground that streams past at 20-40 px a frame the level steps all the time: `picture_steps`
gives 613 steps on PR062, and only the 24 largest were fitted; two of the zooms (1985: level 117 -> 85; 3694: 80 ->
95) were 25th and later, and frames given with `--events` went through the same cut. (2) The zoom in at 1564 moves
the level by 5 grey levels and steps nothing. What every one of them does is change the whole picture in one frame:
the scan's change from the frame before is 1.96-13 times the usual there (the 61-frame median), against about 1 for a
frame of ordinary streaming ground. So: frames at 1.8 times the usual or more are candidates too (`zoom.change_spikes`;
a run of them, a cut or a flicker of the gain, is one candidate at its largest), ranked with the level's steps (a spike
of 1.8 as a step of 44 %); the number fitted is 24 or 12 a minute of clip, whichever is more; and every frame given
with `--events` is fitted whatever its size. On PR062 all six are then found with nothing given: x0.501, x2.002,
x0.499, x1.996, x0.501, x0.492, the states narrow, x0.50, narrow, x0.50, narrow, x0.50, x0.25. The cost is time: 40
candidates fitted, 12 min against 7.5.

**A frame flat over part of it (fixed 2026-10-27).** The fit's window variance was summed in the frame's own float32,
and over a flat stretch -- a title card, a black bar, an edited compilation's frames -- the sums nearly cancel and
leave rounding in place of the variance: on Corbell's upload of PR051 a card "matched" a scene at ZNCC 1551, and a
replay's burst came out a STEP of x4.165. The variance is now summed in float64 and a window whose fine detail has an
rms under 0.05 grey levels (`forensics.ZOOM_FLAT`) is no match, as flat sky was made no match in `shift_field` in
September. A rendered frame two-thirds flat read x0.136 at ZNCC 10.46 before and the true x1.994 at 0.47 after
(`tests/test_zoom.py`, which fails on the old code).

**What it cannot do.** See a continuous zoom, or an electronic one that steps neither the level nor the contrast
(PR051's ULTN to 2X at 16.9 s in Corbell's upload is not found); measure a step over a scene with no detail of its own
(haze, a clear sky, a flat sea far off), where the fixed pattern is all there is; tell a correct fit whose peak barely
leads from a trap (both are unknown); or fit a step across a blank while streaky terrain sweeps under it (PR051's NAR to
ULTN at 13.9 s, x2 by its data bar: unknown, the best fit x0.99 at ZNCC 0.15). A cut in an edited compilation is a burst
too: fitted, and unknown if the views do not overlap. `scale.zoom_chain` calls `zoom_fit`, and since 2026-10-27 so does
`integrity` across each contrast transient (`integrity.transient_zooms`, the maintainer's decision: its report and record
say step x s, no change of scale, or not measured and why), in place of `forensics.zoom_ratio`, which looks within 60 px
of the boresight and read x1.0 at every switch of the Puerto Rico clip. Integrity's records change with it, the
reference case files' among them when they are next remade (Decisions, item 9).

**`camera` reads `zoom` (added 2026-10-27).** `mcdonald camera --zoom JSON` (and `run`'s camera stage, where a
`<tag>_zoom.json` is in the case's folder or, for a segment, the whole video's) takes the steps the picture measured
inside the track out of it at the imagery's ratio and checks each on the object's size, as it checks a display's change
of field (§20, `camera.imaged_steps`); the bursts with no measured step are the camera's events ("blank frames A-B, a
zoom not measured"), so a rate step there is the camera's until shown otherwise. With `--fields` the display's scale is
used instead. `slew` keeps one row a zoom state where a "no step" burst joins two stretches into one (it had counted the
state's windows twice), and its figure is one row a state under a row for the clip (PR27's was 64 inches tall).

## 18. Look-alike bands and steadiness against a clock, in `mcdonald flicker` (added 2026-10-20)

Two readings for objective 4 of the 0.3 roadmap, from two analyses kept with the PURSUE work (2026-10-19): a table of
every beat the bird paper's Table 1 rests on against the rhythms a sensor chain and the sky can make, and the bird
test run on a labelled infrared set of birds, airplanes, drones and helicopters (Svanström et al. 2021). Neither
decides anything: they mark and they report, beside §9's lines.

**Bands, not lines** (`flicker.LOOKALIKE_BANDS`, `fold_band`). §9's table holds exact lines; some look-alikes are
bands. An aircraft's 400-Hz power is not 400.000 Hz in the sound recorded on aircraft: PURSUE's buses sit at 399.60
and 399.82 Hz, AARO's FLIR video at 399.10 (and 401.27), a CBP aircraft at 398.41 -- folded at 30 frames a second,
8.41-11.27 Hz, which holds PR077 (9.92) and PR088's object 2 (10.59) though neither is within its resolution of
400.000's 10.00; a lamp on that power folds from twice it. Flames are bands too, and not folded: a bundle of candles
flickers near 10 Hz (Kitahata et al. 2009; Chen et al. 2019, 9.9 Hz), a pool fire puffs at about 1.5 D^-1/2 Hz, so a
sky lantern's 3-10-cm fuel cell puffs at 4.7-8.7 Hz (Cetegen & Ahmed 1993) -- each flame with its own phase, which
the members-apart argument does not touch. A rotor's (10-30 Hz, doubled for an odd blade count), a turboprop's
(50-150) and a multirotor's (150-300) blade-pass and a cooled sensor's cryocooler drive (40-80) are nominal (the
infrared survey's, from patents and recollection) and, folded at video rates, cover the whole band: such a band
(`covers`, WHOLE_BAND of LOW .. top or more) marks nothing, and the notes say once that frequency excludes none of
them. `fold_band(lo, hi, fps)` cuts a band where the fold turns, at each multiple of fps/2, folds the pieces and
merges them. A beat inside any piece of a band, within its resolution of the edges, is marked with it -- "inside
the band of ..." in the finding -- marked, not refused, as with a line.

**Steadiness against a clock** (`flicker.steadiness`; the information-theory survey's D2). §9 has always said what
tells a supply's line from a wingbeat -- a supply holds its frequency, a wingbeat's wanders -- with nothing to hold the
wander against. Now, over the whole stretch the object was followed over:

- it is cut in two halves, or in pieces of 4 s past 8 s;
- each piece is fitted by least squares with a sinusoid and a quadratic, its frequency taken on a grid of 0.05/T
  within 0.6 Hz or 10 % of the beat (the larger) and refined within half a resolution of the best (`_piece_fit`),
  with its Cramér-Rao bound in the residual's own level near the beat;
- the pieces are compared in units of their bounds: z = |f1 - f2| / sqrt(c1^2 + c2^2) for halves, a weighted
  chi-square about their mean for more (`_split`);
- STEADY_RUNS = 200 steady beats are planted -- at the beat's frequency, each piece with its own fitted amplitude, a
  random phase -- in the pieces' residuals resampled in blocks of 0.5 s, and read the same way; p is the share that
  come apart as far, with the beat counted among them (so never under 1/201), and it `wanders` where p < 0.01.

A rhythm locked to the frames does not wander; nor does a supply (the buses above hold to +-0.01 Hz within a clip in
the census) or a cooler's drive. A wingbeat does: the Galileo birds and PR135's six move 2-5 % between halves of
4.5 s. Two traps were paid for. An unbounded peak search in each half (the padded spectrum's highest point within
0.6 Hz) gives no power at all: the planted clocks scatter to 0.3-0.6 Hz, far over the bound. And a clock planted with
the whole record's amplitude, on a beat that comes and goes, is buried in its own noise (the survey's trap): each
piece is planted with its own. Planted in grain over 150 frames at 29.97 (100 clocks each), 12 steady beats gave p 0.01-1.0 (the test allows one
in 12 to be called wandering), and 8 that step from 7.4 to 7.8 Hz between the halves all came out at the floor.
On PR135's six (the golden suite, the paper's tracks, frames 1240-1389): p 0.005 for D, E and F, 0.015-0.025 for A, B
and C, wandering 1.3-4.9 % between halves.

What it is not: a gate, or a way to tell a bird from a governed rotor -- a fold keeps a rotor's 1 % in hertz, and a
helicopter's blade-pass wanders about as much as a wingbeat does once folded (the Galileo Sphere footage). Where each
half would be under MIN_FRAMES it is not read (`power` false, `why` says so). It costs about 1.2 s a beat.

**A flame in the bottom line** (`report.FLAMES`, `Case.flame_said`). A beat marked with a flame's band -- the sky
lantern's or the candles' -- is the one look-alike that neither the beat nor its members being out of step can clear:
a flame is the object's own and keeps its own phase. The report's bottom line says so wherever a beat is marked with
one, and says which way the group's rigidity points where `groups` read it: lanterns let go together drift on one wind
and keep their places; a flock rearranges (the Galileo Sphere run: a drone show held its members to 0.1 px, PR135's
six to 16). For one object, or a group whose rigidity was not read, it says that nothing here decides it. The
headline is not touched.

**The scene's own motion at the beat** (`flicker --scene-shift`, `scene_shift`). A cryocooler's drive or a gimbal's
servo moves the whole picture, the object with it, and turns into brightness through the aperture and the pixel grid;
its folded band covers the whole band (above), so only the picture's own motion can speak to it. With
`--scene-shift`, for each of the objects' own beats:

- the stretch is read twice more: once for its mean frame and the pixels that never change (the burned-in graphics),
  once to register each frame;
- every track is masked to SHIFT_MASK, and the graphics are masked;
- each band-passed frame is registered by one translation of the whole picture, by least squares on the image
  gradient (`lk_shift`, Lucas-Kanade, iterated with a Fourier warp) -- against the mean frame where the scene holds
  still, which also takes out an infrared sensor's fixed pattern, or against the frame before, the shifts summed,
  where the scene pans (over SHIFT_PAN a frame, from a probe of 20 pairs);
- the shift's amplitude at the beat and how it stands over the band are read; the same is read with SHIFT_PLANT =
  0.05 px planted at that beat in every frame, and its recovery is the reading's sensitivity;
- the object's own centroid at the beat is read beside it (`curves`' `moves`).

The scene "moves at the beat" where its shift has a line there and the beat is of a size a shake like that can make (see
below); a scene without the detail to register (SHIFT_TEXTURE) is not read: that is "cannot tell", not "clear". Phase correlation was tried first, in the PURSUE analyses, and dropped: its peak
locked onto PR135's fixed pattern at zero shift and pulls a sub-pixel shift toward whole pixels. The fixed pattern
does not move with a real jitter and pulls this reading toward nothing by its share of the picture's detail, which is
not measured; the planted test moves the scene and the pattern together, so its recovery is an upper bound. On a
synthetic scene jittered 0.3 px at a 6-Hz beat it reads 0.300 px; held still, 0.0002 px, its planted 0.05 px coming
back at 0.998; on a featureless sky it is not read.

**The camera's shake stops a bird (added 2026-10-31).** Five of Amazon's labelled aircraft were named birds, their beats at
3.50-3.67 Hz on a camera shaking 0.37-1.12 px there, whole tracks of it. Their background apertures shake with them, so no
test above can see it. `run` and the window now read the shift wherever a beat would name a bird (`measure(scene="bird")`,
`report.bird_beats`), and the report names no bird where the shift has a line at the beat and the beat is no bigger than a
shake that size can make (`beat[..]["shaken"]`).

The first form could not be used. "Stands 10 times over the band" fired on PR44, PR079, PR088's object 1, PR097's object 8 and
the five Galileo flyers, at 0.0004-0.0038 px: the shake's spectrum is red, and 7-57 % of all frequencies under 5 Hz (29 % at the
median) stand that high wherever a beat is. So the line is now read against its neighbours within 1.5 Hz: SHIFT_LOCAL 15, which paths drawn with
no line reach about once in 200 (0.47-0.52 % of 18,000 draws, white to red). And the size is read against the beat:
SHIFT_PER_PX 5, the beat's share of the brightness over the shake's px.

| | objects | fired | line over neighbours | brightness per px |
|---|---|---|---|---|
| AOT aircraft named birds | 5 | 5 | 30-2423 | 0.14-1.7 |
| Svanström aircraft, drones with a call | 15 | 2 (AIRPLANE_064, named a bird; HELICOPTER_054 o0, not) | 60, 29 | 3.4, 0.15 |
| recorded birds (case files, PR135's six, the flyers) | 37 | 0 | under 7, but flyers 2, 3, 4: 16-66 | 36 and up |
| Svanström labelled birds with a call | 36 | 0 | under 14 | nearest 0.67 at 13.5 |

The two groups are eleven times apart in brightness per px among recorded birds. Where the bound sits between 3.4 and 36 is
judgement inside what the null allows, and five of the six aircraft that set the low side share one data set and one kind of
shake. The labelled bird nearest the rule, IR_BIRD_012 o0, has a line 13.5 times its neighbours at 3.87 Hz, under 15, on a
camera moving 1.6 px at 1.9 Hz. Drawn at random frequencies, the rule fires on none of 14,800 draws on the PURSUE and Galileo
cameras, 1.6 % of 20,400 on Svanström's moving platform and 14 % of 2,000 on the shaking AOT cameras: a beat that lands on a
real line cannot be told from it, so on such a camera a real bird can lose its name, and the report says why.

Coherence of the brightness with the shake does not decide: it clears its level on only two of the five AOT aircraft (a beat
carried by bursts weighs against it), and short tracks have too few looks. The object's own response to a shifted aperture
predicts only 10-14 % of the two AOT beats it was read on, so a shake's size is held to the beat as a ratio, not as a
prediction. What makes these beats from a shake that small is not worked out.

Flyers 2, 3 and 4 keep a small line in the shift at their beats (0.001-0.004 px, 16-66 times its neighbours). It does not move
with a larger mask (30, 60, 120 px), and it is no shake of the sensor: the right half of the picture reads it ten times the
left, and the left at another phase. What makes it was not found. The rule leaves them alone by their size.

No usable scene (SHIFT_TEXTURE) is "cannot tell": the headline stands and the note says the shake was not read. Reading a
bird costs, on one CPU: 421 frames at 1080p 72 to 421 s, 488 at 1080p 50 to 331 s, 413 at 720p 52 to 220 s, 925 at 640 x 512 84
to 149 s, and PR135's six together 101 to 346 s. The planted test is read on 120 frames.

**Tried and dropped: held pictures by the object's motion.** `pictures` reads held pictures off the whole frame's
thumbnails, and misreads two chains outside PURSUE: an encoder that skips a still sky (IPPP, the Svanström set, a
fresh picture every frame) makes fresh pictures look held, and one that re-encodes held pictures afresh (the Galileo
Sphere chain) makes them look new. Read against known answers (2026-10-20):

| clip (held, by hand) | the whole frame (kept) | the object's motion | frame and motion | frame and brightness |
|---|---|---|---|---|
| Svanström bird (0) | 0.175 | 0.224 | 0.036 | 0.084 |
| Svanström airplane (0) | 0.100 | 0.533 | 0.073 | 0.087 |
| Sphere airliner (0.59) | 0.498 | 0.285 | 0.230 | 0.056 |
| PR149 (0.22) | 0.222 | 0.000 | 0.000 | 0.025 |
| PR44 (0.50) | 0.503 | 0.527 | 0.503 | 0.493 |
| PR135 (0) | 0.000 | 0.007 | 0.000 | 0.000 |

The whole frame reads PURSUE's three to their truth; every rule that cut the Svanström false holds lost PR149's real
ones (a contact at 21 px a frame leaves its centroid's reach on a held frame, and the centroid falls back to the
moving track), and the spacing of the held frames does not tell them apart either (PR149 and the Svanström bird both
0.58 in their two commonest intervals). Kept as it was; the misreads are written into `pictures`' docstring. What the
spacing could not tell, the order of the held frames does (section 35): neither chain's holds are a cadence, so since
2026-10-29 neither misread moves the band's top.

## 19. A light that flashes in a train, in `mcdonald flicker` (added 2026-10-20)

A council member's question (UAPSAC, 2026-10-20): helicopters carry flashing lights with known properties, so could a
rotor's beat and a light's flicker show as two peaks in one brightness spectrum? The PURSUE analysis that answered it
(the uap repository's `analysis/methods/helicopter_lights.md`) found that in visible video they do, and that the light
is not a peak but a comb. This is that analysis built into the stage, as item 13 of `flicker`'s docstring. It reports;
it changes no call, gate or headline.

**The rule.** An aircraft's anti-collision light must flash 40-100 times a minute, 0.67-1.67 Hz (14 CFR 25.1401(c),
27.1401(c), 29.1401(c)); where two lights' beams overlap, up to 180 a minute, 3 Hz. A rotorcraft's must be aviation
red (27.1401(d)); many aircraft add white strobes. A train of flashes 0.1-0.3 s long is a comb in the spectrum: lines
at the rate and every multiple of it, under an envelope set by the flash's length. Its fundamental sits under the band
a beat is looked for in (LOW = 1.5 Hz) and its harmonics fill that band. Read by its tallest tooth, a light is a "beat"
at 1.5-3 Hz.

**Three curves, not one** (`lights`, `reach`). The aperture's sum is what a beat is read from. On a thing wider than a
light, the sum is the thing's: a helicopter's dark body swamps a light of a few pixels, and V_HELICOPTER_054's white
light is absent from its sum. So on every frame, from the same reading of the frame, each tracked thing also gets the
mean of its 3 brightest pixels and of its 3 reddest (R - max(G, B)), each over the median of a ring. These pixels are
looked for in a disc that covers the thing's whole silhouette. `reach` is the farthest pixel of the patch standing 4
robust sigmas off the sky and joined to the thing's middle, a median over 20 frames. `extent` cannot serve here: it is
the core's, and V_054's core is 8.5 px in radius while its lights sit 14-35 px out on the tail boom. A patch that runs
on to the edge of the 80-px search disc is clutter joined to the thing, and the disc falls back to the ring. A grey
video's reddest pixels are all 0 and are not read.

**Flashes** (`flashes`). Each curve is taken against a 2-s running median (a median, so a short flash stands on the
level between flashes). A flash is a run over 2.5 robust sigmas that reaches 5, clear of 0.4 s at either end. Runs
closer than 0.15 s are one flash; that is under the 0.23-s gap of the fastest train looked for. A light's curve is held
to a scatter of at least one grey level. A flash's time is its run's brightness-weighted centroid, not its highest
frame. A rotating beacon's flash has a flat top, which puts the highest frame anywhere along it: on V_030, p was 0.026
by the highest frame and 0.001 by the centroid.

**The train** (`blinks`). The flash times are folded at every rate from 0.6 to 3 Hz on a grid of 0.05/T, by Z^2 with
4 harmonics (Buccheri et al. 1983). The strongest fold is held against 2,000 sets of as many times at random over the
same span, read the same way; p is the share that fold as tightly at any rate there. A train is at least 4 flashes at
p < 0.01. Flashes in step at 1/P are in step at 2/P and 3/P as well, and as tightly, so the train's rate is the lowest
whose fold is within 0.8 of the strongest. Without that rule the test's planted 1.00-Hz train read 3.00. The rate is
then refined by a straight line through the flash times against their cycle numbers, so a missed flash keeps its
cycle, and its error comes from the line's residuals. `rule` says where the rate falls: "anti-collision" for 40-100
a minute (5 % either side), "overlap" up to 180.

**The controls, and the beat** (`blink_reading`). The same three curves are read at four places beside the object, at
least twice its light disc away. A train there within 5 % of the object's rate is the scene's, and the object's is
`shared`. Where the object has its own train and a beat, the beat is read again with the flashes taken out
(`deflash`: each run filled straight across). A beat that keeps under half its amplitude is the flashes' (a comb's
tooth, and its harmonic is named). It is marked as a look-alike, "anti-collision light", marked, not refused. The
notes say the train, the rule, the controls and the beat; the report's bottom line says the rate, and that a glint
off something that turns flashes too. A control off the frame, or on it for under 2 s, says nothing, so the record
keeps which controls were read (`controls_read`, of `controls_n`) and the note counts only those: a light disc as wide
as V_030's puts its controls twice it out, where they can all leave the frame. The light curves are written beside the
brightness in `<out>_flicker.csv`, as "<name> white" and "<name> red" (the red only for a colour video), the object's
and its controls'.

**A black-hot display** (`--black-hot`, 2026-10-21). A light is hot. On a visible picture and a white-hot thermal
display a hot thing is bright, but many pods show their picture black-hot, where it is dark. AARO's Atmospheric Wakes
airliner is dark on a light sky. There, "the brightest pixels" are the coldest, and the sum of a dark object, read the
other way up so that a light is up, turns a hot light down. With `black_hot` the light's curve is the 3 darkest pixels,
how far under the ring's median (still keyed "white" in the records, "hot" in the CSV and "the hottest pixels" in the
note), and the sum's sign follows. The test: `_Flasher` drawn black-hot, a dark light on a dark body. It is a train
with `black_hot` and none without. The run that found the need turned the picture over from outside (the uap
repository's `analysis/sweeps/blinks/blinks_track.py --hot-dark`). Nothing yet reads a display's polarity from the
clip; it is given.

**In the report.** The bottom line has a sentence for an object's own train. The summary has a row for it, "flashing
light", rate a minute first, which the window's report card shows as "Light".

**Known answers** (2026-10-20, every labelled track of Svanström et al. 2021: 837 tracks, visible and
infrared, of birds, drones, airplanes and helicopters):

| | tracks | a train of its own | shared with the background |
|---|---|---|---|
| visible, helicopters | 70 | **2** | 0 |
| visible, airplanes / drones / birds | 82 / 127 / 126 | 0 / 0 / 0 | 0 |
| infrared, helicopters / airplanes / drones / birds | 57 / 82 / 168 / 125 | 0 | 0 |

- **V_HELICOPTER_054**: a white light, 4 flashes at 1.00 Hz (60 a minute), p 0.003, read in the brightest pixels. Its
  sum has none: 4 flashes there at p 0.61.
- **V_HELICOPTER_030**: a red light, 6 flashes at 0.75 Hz (45 a minute), p 0.0005, read in the reddest pixels.
- Both beats (2.4 and 2.5 Hz) keep 79 % and 94 % of their amplitude without the flashes, so they are not the lights'.
- These are the two the uap analysis found by eye and by its own reading, and no others.
- In the analysis, V_054 also carries a red light (3 flashes before it is too far to see, under the 4 a train needs
  here) and its rotor at 13.7 Hz in the blade pixels.
- No thermal track flashes. An LED gives off almost no heat, and a lamp's light leaves through a cover opaque to
  thermal infrared; so in thermal video the test is expected to find nothing. Mid-wave sensors, which most PURSUE pods
  are, have no known answer here.

**What it is not.** It is not a gate, and it does not identify an aircraft. A glint off a tumbling or turning body is
a train too, at its turning rate. Daylight hides most lights (2 of 70 helicopters here). Military aircraft fly dark or
with lights only near-infrared goggles see, and a short exposure misses a xenon strobe's millisecond flash, so no train
is weak evidence. A train is strong evidence of a light; a bird does not carry one.

## 20. `mcdonald camera` -- what the camera did while it watched (added 2026-10-20)

**What it answers.** Two things the camera does change the object's motion in the picture without the object doing
anything: it zooms, and it stops following. Both were behind a published 75.9 g (Knuth, Powell & Reali 2019, *Entropy*
21, 939, §2.4.3) on the Navy's 2004 FLIR1, whose fit held the pod's line of sight still and ended its acceleration on
the picture's zoom frame (case note `analysis/cases/nimitz_flir1/README.md` in the uap repository).

```bash
mcdonald camera CLIP.mp4 --track track.csv                                   # zoom steps, rate steps
mcdonald camera CLIP.mp4 --track track.csv --fov 0.7 --fov-px 244 \
    --los-rate 0.2466 --los-err 0.0051 --after 2207 --zoom-ratio 2 \
    --events "2208:the gate collapses,2238:the 2.0 readout"                  # and the released-track null
mcdonald camera CLIP.mp4 --track track.csv --events auto                    # the overlay's events found (section 22)
mcdonald camera CLIP.mp4 --track track.csv --fov-px 244 --centre 177.5,121 \
    --fields "2045-2084:0.7,2085-2139:0.35,...,2158-2207:1.5,2209-2217:6,2218-2234:0.7,2235-2290:0.35"
                                                                             # the fields the display gives (below)
```

**How it works.**

- *The object's image* on each tracked frame (`shape`): the window's median taken off, the part above half its peak
  joined to the brightest pixel near the track, and its second moments -- its length along and across its long axis
  as the full width at half maximum of the Gaussian with those moments there (a 2-D Gaussian cut at half its peak keeps
  sqrt(1 - ln 2) = 0.554 of its sigma).
- *A zoom step* (`zoom_steps`): the median log length over four frames after a frame against four before, each side
  steady, no gap; the frame is the best split of the frames round it. Its centre comes from the track's straight lines
  either side, carried to the step: a zoom by r about c puts p_a - c = r (p_b - c). A zoom is about the optical axis,
  so `confirmed_by_offset` needs the centre within 5 % of the frame's larger side of its middle. A change of the
  object's own size gives a centre anywhere. An object at the centre gives no jump, and then no centre.
- *Which steps are zooms.* Each side of a step must hold frame by frame (no frame more than 0.30 in log size from its
  side's median), not only in its median: a half-maximum blob that takes in a neighbour or a wing for two to four
  frames and lets it go flips back. Only a step its offset confirms, or one whose ratio is given (`--zoom-ratio`), is
  *applied*: taken out of the track and set among the camera's events. The others are reported as the object's own
  size steps, with why (`why_not`): its jump puts the centre far from the frame's; or its position holds where a zoom
  about the frame's centre would have moved it N px; or it sits at the centre, where its position cannot say. The width
  is measured too (`width_ratio`): an electronic zoom, as the ATFLIR's x2 is, scales it with the length (FLIR1: 1.85
  against 1.91); an optical one leaves an unresolved object's width at the blur's.
- *The size's trend* (`size_trend`; added 2026-10-30). A step is not the only way a size changes: fifteen airliners closing
  on a camera grew threefold with no step, and the stage said their size held steady. Its length in the first frame's
  scale (zooms taken out) is read as the medians of the first and last thirds of the frames, and of six stretches of
  the track. It *grows* or *shrinks* where the six are all in order and the thirds are 25 % apart, the share this stage
  already calls a size held; within 25 % it holds; apart but out of order it goes up and down, and the stretches are
  given. All six in order is 2 chances in 720 for a size that holds, whatever its noise's shape. Drawn sizes that hold,
  wander and read noise together, 12 to 3,000 frames, pass at most 0.25 % of the time with no memory, 1.0 % with a memory
  a tenth of the track's length and 1.9 % with a fifth: the rate is held at a tenth, a judgement, because a slower wander
  is a change of size through the track, which is what the row says. A line fitted through the sizes could not be held
  to a rate: read noise on a wander hides the wander's memory from a lag-one correlation, and 12-14 % of drawn sizes
  passed at 4 sigma at any length. The row does not say which of the object's range, its aspect, its light or a slow zoom
  of the picture did it. Recorded: the 15 arrivals grow (x2.8-3.5) and V054 shrinks (x0.25); PR144's 11.6, 8.6, 65, 22,
  26, 77 px and PR43's 5.4, 4.4, 5.5, 10.1, 19.1, 10.7 go up and down.
- *The ratio.* The size's ratio runs low where the chain after the zoom blurs by a fixed amount (FLIR1: x1.91 for an
  ATFLIR's x2). So the offset's ratio about the frame's middle is given too (x2.08). `--zoom-ratio` takes the sensor's
  own, where it prints one.
- *Rate steps* (`rate_steps`): the track taken back to the first frame's scale, then straight lines between
  breakpoints, as few as the noise allows. That is the Schwarz criterion over both coordinates, optimal partitioning
  with PELT's pruning, and stretches of 4 frames or more. The noise comes from second differences, at least 0.25 px. A
  stretch's error is from the larger of that and its own residuals.
- Each breakpoint is set beside the camera's events: the zoom steps, and `--events`, a person's (a readout's change, a
  gate's collapse) or, with `--events auto`, those `mcdonald events` finds in the overlay over 300 frames either side
  of the track (section 22). A breakpoint within 3 frames of one is the camera's until shown otherwise.
- *Jumps.* At each breakpoint the two lines either side, carried to the half frame between, part by `jump_px`. An
  object's position does not jump, so one over 5 errors and 2 px is the track's or the picture's (a tracker on another
  feature, a frame dropped or repeated, a cut, a zoom not taken out), and the stretch it starts is no rate of the
  object's. FLIR1's at 2243 (3.9 px) is where the object passes under the `5°` readout and its centroid is pulled.
- *Changes of field* (`--fields`, `field_steps`). A zoom readout is not the whole scale. A pod with several fields
  changes scale when it changes field: the ATFLIR's NAR (0.7 deg across its picture), MFOV (3) and WFOV (6), each
  but WFOV with a x2, so NAR x2 to MFOV x2 is x4.3 and NAR x2 to WFOV x17. FLIR1's readout says `2.0` over 2158-2209
  (from 1) while the pod is in MFOV x2, and the handoff's question, "did the picture zoom at 2158 with its readout",
  was that (uap `analysis/cases/nimitz_flir1/README.md`, "The fields of view over the last 5 s"). `--fields` gives the
  field across `--fov-px`, stretch by stretch, as the display gives it (`symbology --method atflir` turns its readings
  into this form). Each change is taken out of the track as a zoom is, about `--centre` (the boresight; the frame's
  centre where not given), and set among the camera's events. The object's size checks it on the 4 tracked frames
  nearest either side: *confirms* (its size ratio within 25 % of the field's), *contradicts* (it holds within 25 %
  across a change of x1.5 or more that it would show, or it is resolved where the field puts it at the blur), *no
  power* (tracked on fewer than 2 frames a side, or the field leaves it under 1.5 blurs long on the smaller side --
  the blur then sets its size; `--blur`, default 4 px up to 576 rows), or *unclear*. Changes with fewer than two
  tracked frames between them are checked as one. The angular scale is the first field's, an assumption (the fields
  are the maker's numbers).
- *From a whole case* (`run --fields`, `--fov-px`; 2026-10-20, night). Both are rows of what a person may know
  (`stages.KNOWN`), so `run`, the window's Measure form and `run_case` take them in the same words, the case keeps
  them (its ingest's `known`, its commands) and `share rerun` repeats them. The camera stage takes the fields as
  `camera --fields` does; the scale stage's k is over `--fov-px` (the picture's box, where it is narrower than the
  frame: an ATFLIR's 244 of 352) at the field the fields give at the track's first frame. `--fields` goes without
  `--fov` and `--graticule`, which say the scale another way. Given without a field, `--fov-px` is what the scale
  stage's ladder and the size/speed figure's lines span. `--fov-px` can be given afterwards (`mcdonald report CASE
  --fov-px 244`), and a field of view given afterwards now moves the camera stage's degrees too (`camera.rescale`,
  arithmetic on its stretches): until then `add_known` worked out the scale and kinematics again and left the camera's
  rates in the old scale, or in none.
- *The released-track null* (`released`). A camera that held the object turned at its bearing rate. Once it stops
  following, the object crosses the picture at that rate and no faster. The fastest stretch after `--after` is set
  against `--los-rate` (from `mcdonald readout`). The assumed field's error (`--scale-err`, 10 % with `--fov`)
  scales the object's rates and not the camera's, so it is in the comparison; `z_without_scale` is the comparison
  with the scale taken as exact.
- *Against the scene* (`--scene LAYERS_CSV`, 2026-10-28; `--pixel-aspect` where the pixels are not square). Where no
  readout gives the camera's rate but the ground is in the picture, the scene is the camera's own record. The track
  is taken relative to the scene's path (`slew.scene_path` of a `layers` CSV over the same frames: the chain of the
  pairs' shifts, one stretch at a time), so its rate steps are the object's against the ground, with the camera's
  motion -- before and after the release -- out of them. The camera's rate before is the scene's drift through the
  picture over the frames it held the object (`camera_before`: a line through the path from the track's first frame to
  `--after`, its error the larger of the line's own and the path's), and the comparison then needs no readout and no
  scale: both rates go through one k. A camera that held a drifting object turned against the ground at the object's
  own rate across it, and the ground slid through the picture at that rate the other way; let go, the object keeps its
  motion and crosses the ground at that rate, in the direction the ground had been sliding from (`direction_off_deg`,
  given where the scene drifted at 2 px/s or more and clearly). Beside the fastest stretch the null compares every
  stretch after the release and names the first, and -- a track cut into short stretches by its own jitter has one
  departure all the same -- the departure as a whole (`departure`: a line through the track from the release to its
  end, or to the first jump of more than twice the object's width, a dash or another feature). The scene's drift after
  the release is reported too: whether the camera moved at all once it let go.

**What it found on FLIR1** (the 2007 copy; tests in `tests/test_golden.py`):
- The zoom is at frame 2235 (counted from 1), three frames before the `2.0` readout. The size gives x1.91 and the
  offset x2.08; with x2, the zoom's centre is (178.1, 122.1), against the held object's x of 177.3.
- Once taken to one scale, the rate's steps are 0.004 deg/s while locked, then 0.126 → 0.293 → 0.088 → 0.109 deg/s.
  The steps at 2235 and 2239 are at the zoom and one frame after the readout.
- The fastest stretch, the four frames after the zoom, is 0.293 +- 0.010 deg/s against the 0.247 +- 0.005 the pod
  had been turning (section 21; 0.252 +- 0.004 before one of its ticks was timed again). That is +1.5 sigma with the
  assumed 0.7 deg field's 10 %, and +4.3 with the field exact. Within what a camera that stopped following shows, if
  the field is no better known than that.
- With `--events auto` the step at 2239 falls on the zoom readout's change found at 2238, the event given by hand.
- With the fields the display gives over 2070-2250 (2026-10-20, golden `test_flir1_fields`): the x2 zooms at 2085,
  2140 and 2235 are confirmed by the object's size (x1.79, x0.56, x1.91); NAR -> MFOV x2 at 2156-2158 and the WFOV
  interlude 2209-2218 are *no power* (the object would be 4.3 and 3.6 px long, at the copy's 4-px blur); the
  released-track null is unchanged, 0.293 deg/s at +1.5 sigma (+4.3 exact). Over the MFOV stretch, taken to the first
  field's pixels, the track's wander while the tracker re-centres after the switch (2172-2194) comes out as rate steps
  at no camera event; they are the tracker's, not the object's.

**On the PURSUE reference cases** (2026-10-20, Slurm job 8220; 22 objects of the 14 reference case files, each on its
own track, as `run` calls the stage). No zoom step was applied on any: nine of the objects showed size steps (PR135's
birds, PR077, PR097's object 5, PR141's), none about the frame's centre and none with a jump, so all were reported as
the objects' own. Before the steps had to hold frame by frame and be confirmed to be applied, five of PR135's six birds
"zoomed", and the false zooms, taken out of their tracks, made one stretch 386 +- 183 px/s. The rate steps are 4 to 42
stretches an object: a rate that changes smoothly, as a panning camera's does, is cut into many, and with no camera
event known none of their steps means anything by itself. So in `run`'s report the stage sums up a list of more than 6
stretches (each is in the camera CSV), and says that no event was known to set them beside.

**What it found on PR051** (2026-10-28; the MTS-B's "instant acceleration", Corbell's upload of the unredacted footage,
reference data `pr051/`; golden `test_pr051_released_track_against_the_scene`). The one PURSUE clip whose camera lets an
object go with the ground in the picture. Over 70-74 s of the upload (frames 4201-4437, at 4X: 0.080 deg across the 4:3
sensor's 1440 square px, FVW 58.5 m at 22.5 NM) the gate holds the object at one place in the picture, and `layers`
(every frame doubled, so pairs of the odd frames; the overlay boxed by hand) reads the ground held still too: 0.3 square
px/s, 1.5e-5 deg/s. The camera was not turning against the ground to hold it, so a camera that stopped following would
show the object going nowhere. From the frame the gate starts blinking (4439, the display's own flag that the track is
lost) the object walks out of the gate and crosses the ground at 0.0079 +- 0.0002 deg/s (142 square px/s, heading 325
deg: up and to the left) for 1.8 s, 43 sigma faster than the camera had been turning, and at 4553 becomes a dash 475 px
to the right whose centroid then moves at 0.11 +- 0.01 deg/s. Through the drift and the dash the scene drifts 0.6 px/s:
the camera did not move at either. So the release explains neither the drift nor the dash; both are in the picture's
content, the object's or the display's, which a capture of a display cannot separate (the research repository's case
note `analysis/cases/pr051/`). What it does not say: the object's range (the data bar's SLR is the ground's), so not its
speed; at the ground's 41.7 km the drift would be 5.8 m/s across the line of sight.

**How it fails, and what it cannot do.**
- It cannot tell a camera that stopped from one that slowed, or a crew slewing by hand from a tracker coasting.
- It cannot read the camera's turn off an empty sky.
- With `--scene`, a pair `layers` reads as held still is zero in the path, so the capture's own jitter (PR051's: a few
  pixels, the overlay and all) stays in the track and not in the scene, and a saturated bloom's centroid is cut into
  many short stretches, each a jump at its start by the jump rule. The departure as a whole is the line to read there.
- It cannot say anything about the object's motion along the line of sight. The image's size changes as the range
  does, but by far less than a pixel over the second or so these steps take (FLIR1: 0.03 px for the published
  "67 g away"), so a radial acceleration is not given.
- A gain step can make a small hot object look larger. It is kept out by the centre's test, not by the size.
- The noise floor and the 4-frame stretch are choices. A stretch of 4 frames is 0.13 s.
- A zoom with the object at the frame's centre is not applied unless its ratio is given: its position cannot confirm
  it, and a sudden change of the object's own size looks the same.
- Tests: `tests/test_camera.py` (synthetic, seconds) and the FLIR1 goldens.

## 21. `mcdonald readout` -- a number the overlay prints, timed to the frame (added 2026-10-20)

**What it answers.** How fast the camera turned, from a readout that prints its angle in whole steps. The tick from v
to v + 1 is where the true value crosses v + 1/2. So a tick timed to the frame is a reading good to a frame's
duration, and a straight line through a steady turn's ticks gives its rate far more finely than the step. And the
converse: what a readout that holds still cannot rule out.

```bash
mcdonald readout CLIP.mp4 --box 163,21,179,34                     # a strip of the box every 15 frames, to read
mcdonald readout CLIP.mp4 --box 163,21,179,34 --values "1-256:4,271-706:3,...,2206-2289:-8"
```

**How it works.**
- Reading the digits is the person's (or the agent's, recorded as such). The strip shows the box every `--every`
  frames, and `--values` gives each stretch's value, with frames well inside each.
- Each stretch's template is the mean of its frames' strokes (`forensics.strokes`: a top-hat on the text's side,
  which takes away the scene's shading behind the text), zero-mean and unit-variance, so the gain does not matter. The
  frames from one stretch's middle to the next's go each to the nearer template. On the grey itself FLIR1's tick from
  1 L to 2 L came out at 1477.5; a strip of every other frame shows it at 1437. The sky behind the readout brightens at
  1486, so the 2 L template, made mostly of later frames, was unlike the dark-sky frames between, and they went to
  1 L. On the strokes it is 1437.5, with no frame read the other way.
- The tick is the change point with the fewest frames on the wrong side. The frames that dither between the two
  values are counted, and a dithering tick's crossing is the middle of its dither.
- The rate is a straight line through the crossings of the longest run that steps one way by one step at a time. A
  run that goes back is reported, not fitted.
- After the last tick: when the next was due at that rate; whether the readout's hold runs to the end before it was
  due (`holds_to_end`); and the fastest rate the hold allows.

**On FLIR1.**
- The pod's azimuth gives 0.2466 +- 0.0051 deg/s over 8 ticks in 28 s, with residuals of 0.115 deg (the readout
  shows whole degrees). Before frame 1400 it goes 1 R, 1 L, 0, 1 L; that run is reported, not fitted. (Timed on the
  grey, with the 1 L -> 2 L tick 40 frames late, it was 0.2518 +- 0.0042.)
- The last tick, 7 → 8 L, dithers. At the rate before, the next was due at frame 2296, and the clip ends at 2289. So
  "8° L" from 2210 to the end cannot say whether the pod stopped, and the published analysis took the readout's
  holding still as the pod's.
- `mcdonald events` (section 22), with no values given, times 12 of these 13 ticks to the same half frame.

**How it fails.**
- A template needs a stretch of each value long enough to make one. A readout that changes every few frames is out
  of its reach.
- A glyph that the codec smears into its neighbour's shape reads as the neighbour (FLIR1's first tick: 30 frames
  read the other way).
- The rate assumes the turn was steady over the run. Its residuals say how far it was not.

## 22. `mcdonald events` -- the overlay's own events, found (added 2026-10-20)

**What it answers.** When did the camera do something, as its own overlay shows it? A readout changing, a clock
ticking, the gate round the object collapsing or growing, the whole picture stepping. A step in an object's rate at one
of these is the camera's until shown otherwise (section 20), and on FLIR1 every step of the published "acceleration"
fell on one. They were given by hand (`camera --events`); here they are found.

```bash
mcdonald events CLIP.mp4                                   # text boxes found, their changes, the picture's steps
mcdonald events CLIP.mp4 --track track.csv                 # and the strokes round the object (its gate)
mcdonald events CLIP.mp4 --box "az:163,21,179,34"          # a box given
mcdonald camera CLIP.mp4 --track track.csv --events auto   # the rate's steps set beside them
```

**How it works.**
- *Text boxes.* In a sample of 41 frames, the overlay's strokes (`forensics.strokes`: the grey less its opening by a
  square a stroke's width wide, on the symbology's side), where they stand in a quarter of the frames or more, joined
  along a line only (a label written down the side is not joined to the readout beside it) into boxes 2-9 % of the
  frame's height, two separate strokes or more, and not a reticle's bar. With a track, boxes the object passes are left
  out: they are its gate and what it crosses.
- *Where text is looked for* (`text_strokes`, 2026-10-20, night). Everywhere but the dark that holds in nearly every
  frame (`static_masks`' `blocks_raw`: a redaction, a display's black surround, a sky black above the clouds) and a
  ring of 1 px at 240 rows round it, and with the straight lines three glyphs long or more that run along that dark for
  most of their length taken out whole (a picture's border, a box drawn round a word). Until then it was everywhere
  but `blocks`, the dark grown by 8 px against a redaction's codec ringing, and that took in text drawn against a
  border: FLIR1's field of view, `NAR`, under the picture's top edge, and all of GIMBAL's top line, its azimuth among
  it, because the sky above its clouds is black on 95 % of frames. A word the copy has blurred into one band, a glyph
  high and two or more wide, is text too (`_band`): at 352 x 240 the top-hat's opening is taller than FLIR1's glyphs,
  and `NAR` is one stroke filling 0.74 of its box. On the redacted PURSUE clips tried, PR27 (frames 1-600) and PR144
  (1-300), the boxes found and their events are the same as before; taking the lines out everywhere instead made six
  false boxes on PR27, pieces of its breakwater and of the frame's edge.
- *A box's changes.* Each box's strokes on every frame, kept shrunk to at most 600 pixels as bytes. At each frame the
  mean of the 6 frames before against the 6 from it, per glyph-sized cell (`two_window`); each cell's difference, as
  log(D + its 20th percentile), in sigmas of its noise -- read from the lower part of its distribution, so that a
  readout that ticks every 20 frames is judged against its quiet frames -- and the largest cell's (`change_score`). A
  change is a peak of 8 sigmas or more. Then each cell's noise is read once more from its quiet frames alone, those more
  than 6 frames from a change the first pass found (2026-10-20, night): GIMBAL's azimuth ticks every 20 frames and keeps
  the windows' difference up on some 12 of every 20, so even the lower part of its distribution was partly the
  changes', and the ticks of one or two segments (53 -> 52, 46 -> 45, 43 -> 42) did not stand out of it. Stretches between changes are one look only where they differ by under a
  quarter of the smallest change: a look never stands for two values, though one value may have two looks. Each change is then timed frame by
  frame against the looks either side, as `readout` times a tick: the half frame with the fewest frames on the wrong
  side, and the dithering counted.
- *What a change is.* One within 2 frames of a step of the whole picture is the picture's; one in 3 boxes or more at
  once is the overlay's as a whole; a box whose changes are mostly long back-and-forth runs (median dither over 7
  frames) has something moving in it and is not a readout; a box that changes steadily once a second is a clock, whose
  ticks are no camera event but a second ruler (frames held or dropped come early or late).
- *The gate.* With a track, the strokes in a ring round the object, from just outside it to three times its size or
  8 % of the frame's height: how many pixels, and their rms distance. A step by 1.6 or more, held 4 frames either side:
  vanishes, appears, thins, thickens, draws in, spreads out.
- *The picture.* The middle's level and contrast (away from the boxes and the masks), a step of 6 MADs of their
  frame-to-frame changes held 8 frames either side; contrast collapses (`forensics.transients`); runs of held frames.

**On FLIR1** (the 2007 copy, all 2289 frames, 20 s):
- The box found for the pod's azimuth (`top centre (165,22)-(198,33)`, the value and its L/R) times 12 of the 13
  ticks read by hand to the same half frame -- 256.5, 705.5, 963.5, 1149.5, 1335.5, 1437.5, ..., 2187.5 -- and the 13th,
  1 R to 1 L, within 4 frames. Its other changes are real too: over 383-413 the readout shows another value
  and comes back. Given the hand-read box (the digit only), 12 of 13 (the letter's change is outside it).
- The field of view's mnemonic under the picture's top edge is a box since 2026-10-20 (night), changing at 2166.5 as
  it goes from NAR to MFOV; so are the readouts along the picture's bottom edge (the altitude's among them).
- On GIMBAL, whose azimuth ticks every 20 frames (54 L to 41 L over its first 300), the box found takes in the L
  (it stopped short of it inside the old 8-px margin) and gives 9 of the 13 ticks within 2 frames and no change where
  none is (10 such changes before); `symbology --method atflir`, which reads its fields by layout, gives 12 of 13 within
  a frame since the noise is read from the quiet frames (9 before). The ticks are the frames that hold a field of each
  value, read off every frame: 23, 41, 65, 89, 107, 131, ... 275. (They had been read off a strip of every tenth frame
  as 25, 45, 65, 88, ..., and four were missed at 2 frames' tolerance against those.)
- The zoom readout's 1.0 -> 2.0 at 2238, three frames after the picture zooms; the held frames 529-534, 1233-1236 (the
  switch from the television camera to the infrared) and 1296-1298; the picture's level stepping as the sky darkens at
  the release (2216).
- With the exit's track, the strokes round the object thin at 2209 (the gate collapses) and at 2226 (the new gate
  shrinks).
- Over the exit's own 66 frames the zoom readout's change did not stand out of its box's noise (the release is among
  them), so `camera --events auto` looks over 300 frames either side.

**How it fails.**
- A box's noise is judged on its own frames: a short window, or one full of other changes, hides a small change.
- A change of a single segment on a 1080 rendition of a standard-definition display does not stand out of its cell:
  GOFAST's 38 -> 39 (an 8 to a 9) and GIMBAL's 49 -> 48. A cell half a glyph high, a statistic over segment-sized
  strips of the two windows' difference, and keeping 16 times the pixels of each box (`KEEP_PX` 9600) each found none
  of them (2026-10-20). The digits' strokes are blurred over 5-6 px of the rendition, and a segment's change is a few
  percent of its cell's grain.
- A change of one letter in a box whose looks are otherwise alike is timed less well (FLIR1's R to L, 3 frames).
- It finds text by strokes on the symbology's side: symbology drawn in the scene's own grey on a busy scene is missed.
- It cannot say why the overlay changed: a tracker that let go and an operator who switched it off draw the same
  collapse.
- Tests: `tests/test_camera.py` (a drawn readout that ticks and dithers, a clock, a gate that vanishes, a gain step,
  held frames) and the FLIR1 goldens.

## 23. `mcdonald symbology --method atflir` -- the ATFLIR's fields of text (added 2026-10-20)

**What it answers.** Where the Navy's ATFLIR prints its pointing and its state, and what each field said frame by
frame. The ATFLIR draws no north pointer, so `symbology`'s other methods find nothing on it: its pointing is in its
text -- the pod's azimuth (`8° L`), its elevation (`-5°`), the zoom (`Z 2.0`; on the 2004 software `1.0` beside a
`ZOOM` written down the left), the field of view (`NAR`), the camera (`IR`, `TV`).

```bash
mcdonald symbology CLIP.mp4 --method atflir                                        # the fields, their looks, a sheet
mcdonald symbology CLIP.mp4 --method atflir --read "az:A=4,B=3,C=4;zoom:A=1,B=2"   # what each look says
mcdonald symbology CLIP.mp4 --method atflir --read "...;fov:A=NAR,E=MFOV"          # and the picture's field, frame by frame
mcdonald symbology CLIP.mp4 --method atflir --clock X0,Y0,X1,Y1 --clock-at 1:7     # each look's reading suggested
mcdonald symbology CLIP.mp4 --method atflir --clock ... --clock-at 1:5 --read "fov:A=NAR" \
    --letters "198,15,226,24=RTCL;58,23,82,32=OPR"                                  # and letters, from fixed text
```

**How it works.**
- *The picture's box*: the columns and rows of a sample's median that are not the display's black surround in most of
  the frame -- lit, or changing from frame to frame (GIMBAL's dark sky at the top of its picture is barely above the
  surround's black, but it is noisy where a digital surround is not).
- *The fields*: each at its place as a share of the picture's box, the same on FLIR1 (2004, 352 x 240) and GIMBAL and
  GOFAST (2015, 1920 x 1080 renditions of a standard-definition display). The zoom has two places, and the one with
  text in it is taken.
- *Each field through the clip* as `events` follows a box (section 22): its looks, the stretches it holds each, its
  changes to the half frame. Two stretches either side of a change are never one look.
- *Reading*: a sheet (`<tag>_atflir_looks.png`) with each field's looks lettered A, B, C ..., each from the middle of
  its first stretch, with its frames. A person gives what each says (`--read`; signed, right of the nose +). With
  that, each field is a timeline (`<tag>_atflir.csv`), and the azimuth's stretches go to `readout`, whose ticks and
  rate are given as `readout` gives them (section 21).
- *The picture's field.* The field-of-view mnemonic is read as a word (`fov:A=NAR,B=MFOV`) and the zoom as a number.
  With both, the field across the picture is a timeline too, in degrees (`ATFLIR_FIELDS`: NAR 0.7, MFOV 3, WFOV 6,
  halved at x2: Metabunk's reading of Navy documents, so the maker's numbers and an assumption here), given in the form
  `mcdonald camera --fields` takes (section 20). The zoom readout is not the scale by itself: FLIR1 reads `2.0` while
  the pod goes from NAR x2 to MFOV x2, a change of x4.3. A change of the mnemonic's look is flagged as a change of
  scale. The symbology follows the picture by 1-3 frames (FLIR1's zooms; 9 at its switch to MFOV, across broken
  frames), so each change is checked on the picture before it is given to `camera`.
- *Suggested readings* (`--clock`, `mcdonald.glyphs`). The display's clock gives the digits of its own font. Its
  seconds' last digit runs through 0-9 every ten seconds; once a person says what it reads on one frame
  (`--clock-at FRAME:DIGIT`), its ticks (timed as `events` times a readout's, with a straight line through them so that a
  tick the changes miss still counts) say which digit each frame shows, and the frames of each digit, away from its
  ticks, average to a template. Each look of each field is then read glyph by glyph against the ten templates
  (normalised correlation, slid 2 px either way): the best digit where it scores 0.55 or more and leads the next by 0.04,
  `?` otherwise (signs, degree marks and letters are not among the templates). The suggestion is printed beside the
  look on the sheet and kept in the fields (`suggested`). It is never taken as a reading: a person reads each look,
  and a reading that disagrees with a confident suggestion is worth a second look. A misread anchor shifts every
  suggestion by the same digit, which the sheet shows at once.
  - *How the clock's ticks are found.* The last digit's mean change from frame to frame, folded at the clip's second
    (a median over every second, against flashes and weak ticks), over periods within 1 % of it and every half-frame
    phase, then refined by a straight line through the largest change near each folded tick. The folded change
    must stand 1.8 times the box's usual change. FLIR1's clock folds at 29.977 frames (the clip's 29.970), contrast 2.7.
  - *Glyphs.* The digits are split where a column dips under 0.6 of the peaks either side, as well as at empty
    columns, because a VCD copy joins its glyphs. A slot over 1.6 glyphs wide is cut at the pitch into as many as
    its width holds (`glyphs.pitch_cut`: the text's extent in equal steps, each cut at a column that dips there, under
    0.8 of those round it, or where the step falls), a slot far fainter than the others (under 0.4 of their median
    peak) is residue, and rows lit across 80 % of a box (a border) are left out. Templates and glyphs are cropped to
    their strokes, the ten templates with one common crop. A glyph shorter than 0.7 of the digits' height (a degree
    mark, a point) is `?`.
  - *Letters* (`--letters`, 2026-10-20, night). The ATFLIR's letters are not among its clock's digits: an azimuth's
    `L` or `R`, the field of view's `NAR`. They are taken, as the digits are, from text a person has read once: the
    words given for the field of view's and the camera's looks (`--read "fov:A=NAR"`), and boxes of text that does
    not change, with what each says (`--letters "X0,Y0,X1,Y1=RTCL;..."`, optionally `@FIRST-LAST`). Each box's glyphs
    are paired with its characters left to right; where the blur has joined them (FLIR1's `NAR` dips nowhere under
    0.85 of its peak between letters) the text is cut at the display's fixed pitch into as many cells as it has
    characters. A box whose text is too long for it to cut is refused, and said so. Letters cut from text that holds
    still are sharper than the clock's digits and outscore them on true digits: matched among all the glyphs, FLIR1's
    azimuth read `O` for its 0, 2, 3 and 6, and its digits fell from 8 right of 11 to 1. So each field is read by the
    display's grammar (`atflir.GRAMMAR`): the azimuth among the digits and its last glyph among L and R; the elevation
    and the zoom among the digits; the field of view and the camera among the letters, at the letters' pitch.
  - *On FLIR1* (golden `test_flir1_glyphs`): ten templates from the bottom line's clock, `4135` on frame 1. The
    azimuth's digit is suggested right on 10 of 11 stretches read by hand, wrong on none, `?` on 1 (before glyphs were
    cut at the pitch: 8 right, a 0 as a 1, two `?`). With letters from `RTCL`, `OPR`, `DCLTR` and `LTD/R`, its side
    is suggested right on 10 of 11 and wrong on none (with the digits alone it came out as an 8, a 1 or `?`); over
    1151-1331 the glyph comes out shorter than 0.7 of the digits' height and is `?`. Through `atflir`, with `NAR` read
    off its sheet as well, 22 of the azimuth's looks get a side and none the wrong one. The field of view's own looks
    read poorly: `NAR` as `N??` (its three letters match one another within the 0.04 margin at this blur), and MFOV
    as `N???`, its `M` being no letter given -- the nearest stands in, as a letter did for a digit before. A person
    reads the mnemonic. The clock's 8 and 9 correlate at 0.94 on this copy.

**On the three ATFLIR clips** (2026-10-20):
- FLIR1 (2007 copy, all frames): every field placed. The azimuth's looks read 4 R, 3 R, 4 R again over 383-412, 3 R,
  2 R, 1 R, 1 L, 0, 1 L, ... 8 L; the elevation 6° then 5° from 537; the zoom readout 1.0, 2.0 over 441-1276, 1.0, 2.0
  over 2086-2142, 1.0, 2.0 over 2158-2210, 1.0, and 2.0 from 2238 (the exit's zoom). At 2087 and 2143 the held
  object's size doubles and halves with it. Over 2158-2210 it does not: the mnemonic's look changes at 2167 and back at
  2220, and it reads MFOV, then WFOV (2209-2217), then NAR -- the pod changed field, x4.3 coarser than NAR x2, and the
  object is at the blur there (section 20). This stage had timed both changes; nobody read that line of its sheet
  until the zoom at 2158 was questioned.
- GOFAST (frames 1-300, golden `test_atflir_navy`): the azimuth 35° L to 41° L, the elevation -22° to -25°, `Z 1.0`,
  `NAR`, `IR`. The elevation's 3 ticks to the frame; the azimuth's 5 of 6. Its 38 -> 39 at 151.5, a change of one
  segment (an 8 to a 9) on a 1080 rendition of a standard-definition display, does not stand out of its cell, and the
  two values are one look (section 22). The change it found at 190.5, where no tick is (the sea moving behind the
  text), is gone since the noise is read from the quiet frames.
- GIMBAL (frames 1-300, the same golden): the azimuth 54° L to 41° L, 13 ticks at the frames that hold a field of
  each value, read off every frame (23, 41, 65, ..., 275); 12 of them found within a frame and none where no tick is,
  since the noise is read from the quiet frames (9 before, against ticks first read off a strip of every tenth
  frame). The one missed, 49 -> 48 at 131, is a single segment.

**How it fails.**
- The layout is from three clips. Another display (another pod, another software load) prints elsewhere: `mcdonald
  events` finds its text without a layout.
- A field the copy has blurred past telling its looks apart gives one look.
- The values are a person's. A look letter stands for what the person reads on its exemplar; two values a stroke apart
  that the copy blurs alike would be one look, unless a change was found between them.
- An azimuth is the pod's, relative to the aircraft's nose: it says nothing of where the object is without the
  aircraft's heading.

## 24. `mcdonald versions` -- several copies of one clip (added 2026-10-20)

**What it answers.** Which copy of a clip keeps the most of the recording, and where the copies differ in their
frames. A released clip is a copy of a copy, each re-encoded, and a track or a flicker measured on a poor copy
measures its encoder.

```bash
mcdonald versions f4_2007_archive.mpg DOD_110872545.mp4 aaro_1080.mp4 commons.webm --names 2007,dvids,aaro1080,commons
```

**How it works.**
- Each copy's container: codec, size, frame rate as an exact fraction, frame count, bit rate.
- Its frames decoded to one raster, the smallest copy's (at most 480 wide), so that no copy is credited with detail an
  upscale invented, and streamed: per frame, the middle's mean level, its mean |change| from the frame before, its fine
  detail (the rms of a Laplacian) and the share of its 8 x 8 blocks that did not change by 0.25 DN (the encoder held
  them).
- *Lag and drift.* The shift that best lines up each copy's frame-to-frame changes of level with the first copy's,
  over the whole clip and again in windows of 300 frames: a copy that drops or repeats a frame shifts there.
- *Held frames.* Frames that change under a fifth of their neighbours' change and under 0.35 DN. Mapped onto the
  first copy's frames with the window's lag, those held in every copy are the recording's -- or those of a copy all of
  them were made from: DVIDS's renditions of one upload all carry its encoder's holds (PR149's every 4-5 frames, the
  anchor period of its GOP), where FLIR1's 2007 and 2020 copies came down separate lines. Those held in one copy only
  are its encoder's.
- *Detail kept*: each copy's median, against the best copy's. The best source: the most detail, the fewest held frames
  of its own.
- A copy whose header gives another frame rate for the same frames was relabelled, not resampled.

**On FLIR1's four copies** (2026-10-20, 36 s):

| copy | container | frames | detail | blocks held | held frames (own) | lag |
|---|---|---|---|---|---|---|
| 2007 leak | MPEG-1 352x240, 30000/1001, 1150 kb/s | 2289 | 1.00 | 7 % | 13 (2) | -- |
| DVIDS (= AARO's, the 2020 master) | H.264 352x264, 30, 309 kb/s | 2287 | 0.65 | 24 % | 35 (24) | 0, +1 from 985, +2 from 1986 |
| AARO 1920x1080 rendition | H.264, 30 | 2287 | 0.68 | 36 % | 24 (13) | as DVIDS |
| Wikimedia Commons | VP9 352x264, 30, 524 kb/s | 2288 | 0.65 | 20 % | 33 (22) | one more |

- The 2007 copy is the best source: the most detail, and its encoder held 7 % of its blocks from frame to frame against
  20-36 % in the official copies.
- The official copies were relabelled from 29.97 to 30 frames a second without being resampled. Each repeats a frame
  at 985 and again at 1986 (their lag steps 0 -> +1 -> +2, each step placed to the frame between the windows either
  side; DVIDS holds a frame of its own at 986), and ends four
  frames before the 2007 copy.
- Held in every copy, so the recording's: 530-532, 1052, 1233-1236 (the switch from the television camera to the
  infrared), 1297-1298 and 1300.
- The AARO rendition is an upscale of the same 352x264 file: at the common raster it keeps no more than the DVIDS file.

**How it fails.**
- Detail is the picture's high-frequency energy. A blocky encode (MPEG-4 part 2 at a coarse quantiser) adds edges of
  its own and can show as much as a lossless copy; read it with the blocks held, and look at the copies.
- Copies cut to different parts of the recording, with no overlap, cannot be lined up.
- When every copy is a re-encode of one lost file it says which keeps most, not which is nearest the recording.
- A clip whose level barely changes from frame to frame (an empty sky, held still) gives the lag little to hold on to;
  its `r` says so.
- At the default 480-px raster, fine detail a wider copy keeps is averaged away. `--width` compares at up to the smallest
  copy's full width (never wider, so no upscale is credited): PR135's 1280 x 720 base and its 1920 x 1080 rendition are
  alike at 480 (the rendition 1.0, the base 0.96) and the base keeps the more at 1280 (the rendition, taken back down,
  0.73 of it).

## 25. `mcdonald integrity` -- symbology drawn frame by frame (added 2026-10-20)

The layer-order test asks whether the object is under the symbology it crosses (section 2). Its mask is made from the
whole clip: what is drawn in one place throughout. A tracking gate moves with the object, and a readout changes value,
so neither is in it, and on FLIR1 the test said "the object never crosses the symbology" while the object crossed the
gate's bars and passed under the `5°` readout. Now the frame's own strokes are looked at too (`forensics.ridges`, a
contrast test on the symbology's side), and the static test's words are kept where nothing is crossed.

- *Lines drawn frame by frame* (a gate's bars, a readout's strokes): strokes near the object, less its own body (its
  half-maximum blob, opened so that a thin bar touching it comes away), joined where they lie on one line, and taken
  where the line comes in on one side of the object and leaves on the other, past its own image. Over the object's
  middle: the share of the line's pixels nearer the line's own level (read clear of the object) than the object's --
  on top, near 1 (PASS over 0.6); under, near 0 (FLAG under 0.3).
- *Text drawn for a stretch*: the frames either side, their quarter on the far side of the object's level (their
  median holds a small moving object's faint trail, a stroke too), hold the text without the object. A text pixel the
  object covers is set beside its mirror through the object's centre, which is not text: the share of the way each
  moved toward the object's level, so that the reading is the object's own coverage whatever its size -- near 0 under
  the text (PASS under 0.4), near 1 over it (FLAG over 0.7).
- *Only where they can decide.* Both decide only where the object and the symbology lie on opposite sides of the
  picture's level (a dark object, white symbology). On the same side -- a white-hot object and white symbology, as on
  FLIR1 -- a thin stroke over the object and one under it look alike once the display's chain has blurred it (FLIR1's
  VCD copy spreads its gate's 2-px bars to 4 px, and they take the object's light either way), so the crossing is
  reported and decides nothing. Each needs 3 frames.
- The symbology's level (`forensics.overlay_level`) is its static pixels' where they are 0.2 % of the frame or more;
  else the reference frame's sharp pixels on the side most of them are (FLIR1's static mask is 35 px of the picture's
  dark rim: no pixel there holds within 2 DN over 66 noisy frames).
- On FLIR1's exit (2185-2250): "passes symbology drawn for a stretch (text) in 4 frames, on the same side of the
  picture's level as the object: that decides nothing" -- the `5°`, after the zoom. Drawn tests in
  `tests/test_measurement.py`: a gate on top of a dark object (PASS, 1.00), under it (FLAG, 0.25), white bars over a
  white object (no power), a readout drawn for 20 frames over a dark object (PASS, 0.00) and under it (FLAG, 0.98).

**What is drawn is thin, what is drawn for a stretch stays, and a scene held still decides no text (added 2026-11-13).** AARO's PR-016 is a row of birds,
and the test flagged the one it followed as possibly added, on both counts: "crosses lines drawn frame by frame ... in
13 frames; over the object's middle 0.00 of their pixels keep the line's own level (76 DN, the object 255)" and "passes
symbology drawn for a stretch (text) in 11 frames; its pixels move 1.02 as far toward the object's level". Reproduced on
frames 467-690 of DOD_111415209.mp4 with the blind run's track, and looked at frame by frame. The clip's symbology is
read as dark (its mask holds no static pixel; the reference frame's sharp pixels are dark). The birds are saturated
points 15-20 px apart, each ringed dark by the sensor's edge enhancement, and:

- *The line* is the rings, joined along the row into one net of dark strokes: a rail under the points, a rung between
  each two, an arc over the bird. On the 13 frames it is 78-90 px long and 26-33 px across (6.2-8.3 px rms), 550-960
  pixels, its axis within 5 px of the bird's centre. A group was "a straight stroke" where it was three times as long
  as wide, however wide. Now a group taken for a line must also be no wider across its own axis, rms, than `LINE_THIN`
  (0.5) of a stroke's width (`forensics.stroke_step`: 3 px to 576 rows, 4 to 800, 5 above; what `ridges` itself takes a
  stroke to be): 1.5 px at 240-576 rows, 2.5 px at 1080. A stroke w px wide reads w / sqrt(12) (0.9 px for FLIR1's bars
  spread to 4 px at 480 rows), and two pieces joined 2 px off each other's line 1 px more.
- *The text* is the row sliding along itself, about 2 px a frame here: the window's far quarter (the 25th percentile
  over 17 frames, meant to be the picture without the object) is dark wherever a dark gap passed on a quarter of the
  frames, and those places read as strokes held for the stretch. Now the text's pixels at the object must be nearer
  the text's level than the object's on `TEXT_HELD` (0.75) or more of the window's frames that the object is clear of
  (1.5 sizes away): text held for a stretch is there on all of them, a passing gap on some.
- *A scene held still.* Where more than 30 % of the frame never changes (`static_masks`' `still_scene`, the clip
  where that function already says "static and sharp is the scene, not graphics" and leaves such pixels out of its
  own mask), the text reading decides nothing: "passes symbology drawn for a stretch (text) in N frames, in a picture
  whose scene holds still on screen, where a stroke of the scene and text drawn for a stretch look alike: that
  decides nothing" (`TEXT_STILL`; `still_frames`). Over PR-016's frames 560-690 the hold alone left 7 of 25 readings
  held as text is (0.98), and flagged; and PR47's bird (below) flagged with the hold alone.

What is set aside is in the fields beside what is kept (`wide_frames`, `wide_width_px`; `passing_frames`,
`passing_held`; and `moving_width_px`, `text_held` for the readings taken).

*The null* (2026-11-13, again with the still-scene rule on 2026-11-14; `_overlay_drawn` with the three rules off and on, on objects nothing was drawn over, each with its
clip's static masks: the labelled infrared set's 431 tracks that give a polarity, PR-016's bird, PR135's six flock
members, PR47's bird in a row of three, PR098's three points in a line; and FLIR1's exit, whose gate is drawn).

| objects | flagged before | flagged now | what else |
|---|---|---|---|
| the labelled set, 431 tracks (357 with a scene held still) | 0 | 0 | 2 PASS (moving lines) and 21 crossings that decide nothing, before; 2 and 20 now |
| PR-016's bird | FLAG twice (lines, text) | none | all 13 nets set aside; the text reading decides nothing (a scene held still) |
| PR47's bird | FLAG (text, 14 readings, 0.91) | none | the text reading decides nothing (a scene held still) |
| PR098's three points | 0 | 0 | one "decides nothing" (same side) |
| PR135's six | 0 | 0 | nothing crossed |
| FLIR1's exit | - | - | its crossing kept: 4 frames of text, same side, decides nothing |

So on the labelled set the test flags nothing either way: a false-flag rate under 0.7 % (0 of 431; exact, one-sided
95 %). The rate that matters is on rows of ringed points, and there are three such clips in hand: PR-016's and PR47's
flags are gone, and PR098's never was. Three is no rate.


*The line's width.* The 560 groups that ran through an object on the labelled set (strokes of its scenes: nothing is
drawn there) read 0.27 of a stroke's width at the median (quartiles 0.18-0.32), 89 % of them 0.5 or less. PR-016's 13
nets read 1.23-1.66. `LINE_THIN` 0.5 is the least that keeps a stroke as wide as `ridges` allows (0.29) with two pieces
joined off each other's line; anything from 0.4 to 1.2 gives the same verdicts here. On the labelled set it sets aside
60 of 560 groups, on 3 tracks, and moves one verdict: a crossing that decided nothing, gone.

*The text's hold is judgement, and half a remedy alone.* The shares the null read: PR-016's passing gaps 0.00-0.60 (10
readings) and two at 0.98 and 1.00; PR47's 0.33-0.68 (3) and eleven at 0.75-1.00; the drawn readout 0.97 on the six readings kept, with five set aside within 8 frames of
its first and last frames, where the window reaches past it. No line
divides them: `TEXT_HELD` 0.75 takes out what is plainly passing and no drawn text, and PR47's readings are held as
text is. PR47's clip holds its scene still on screen, with dark strokes in it that the mask does not know (14,272
static pixels, the coloured symbology alone): a stroke of the scene and a stroke of the symbology look the same
there, and the bird passes in front of one (read so; not looked at frame by frame). Hence the third rule. **Its cost**:
in a clip whose scene holds still, a paste under drawn text is no longer caught by this reading, which says it cannot
decide; the moving-line reading and the static symbology's still decide there. On the labelled set 357 of 432 tracks
are such clips, and the rule changed no verdict of theirs. What would decide text in them is the scene's own motion
over the window (a stroke of the scene moves with it; drawn text does not), which this test is not handed.

*How it fails.* (0) In a clip whose scene holds still, text drawn for a stretch decides nothing (above). (1) A drawn line wider than half a stroke's width for its picture's height is set aside: a bar drawn
6 px wide at 1080 rows, or one blurred to that; `ridges` would mostly not have found it either (a stroke is "no wider
than about" its step). (2) Text shown for under three quarters of the 17-frame window (under about 13 frames, 0.4 s) is
not read near its start and end, and a readout that changes digit every few frames may never be. (3) Neither gate
knows a ring from a line that happens to be thin: a single bright point's own ring is an arc, not a straight stroke
through it, and was never taken; two points exactly either side of a third give a rung on each side, which `_collinear`
joins only if each is itself a straight stroke along the row (they lie across it).

## 26. A clip with little left to see: AARO's "Middle East Object" (added 2026-10-26)

AARO's MQ-9 clip that its director showed the Senate Armed Services Committee on 19 April 2023 (DVIDS 880273,
`DOD_109584445.mp4`; the workup is the research repository's `analysis/cases/aaro_middle_east_object/`) leaves a strip
about 560 px wide clear between blurred panels. A reticle, grey boxes, a green horizon line and the north pointer's
red triangle and "N" are drawn over it. The camera loses the object and finds it again, so the object is in view in
stretches. Four stages failed on it, each for a reason that was not this clip's alone.

- *`layers`: too few templates fit.* Of the 128-px templates (stride 96), 4 to 7 on a typical frame fit clear of the
  graphics with texture to match on (band-passed grey's std of 1 DN or more; the blurred panels give 0.3-0.7). That is
  fewer than the 8 a consensus needs, and every pair through every slew was read as "held still", 92 % of them. Where
  the median of nine sampled frames is under `layers.FEW_TEMPLATES` (16), `layers` now takes 64-px templates (stride
  48, 32 on the second pass) and says so (`fields["templates"]`; `layers.template_size`). On this clip the object then
  reads 393 px/s against the ground (16-84 %: 380-399, 52 one-second windows), against a hand chain's ~400; "held
  still" falls to 17 % of pairs, the stare it really is. A clip where 16 or more fit is measured as before, and its
  cached templates still hold.
- *`autolink`: a spot that stays put.* Crossing the reticle at 15 px a frame and hidden under it for a few frames, the
  object was traded for the bar's end at (636, 325). Each frame there halved the velocity, the next prediction fell on
  the bar again, and the link held it for 40 frames. Later, followed by the camera at under 2 px a frame, it took the
  "N" for 12. A place where every spot as strong as the object (not only the 25 a link keeps: the "N" was a spot on
  429 of 538 frames and among the 25 strongest on 97) falls, within a 3-px cell and the eight round it, on a quarter
  or more of the frames linked is a spot that stays put (`autolink.Places`). It and the cells beside it are no
  candidates, unless a mark lies within 6 px of it. An object the sensor follows to within a pixel stays put itself
  (PR135's tracking segment), and its marks are on it. Where more than 0.2 % of the screen's cells would stay put (a
  busy texture held still), none is said to. On this clip: 0 frames on the reticle or the "N", against 51 and 12,
  and the frames more than 10 px off a hand-checked track fall from 38 to 13. The link also found the object on
  frames the hand track had missed: past the "N", and over a rooftop.
- *`flicker`: out of view is not lost.* A track's span ran from its first frame to its last, with its positions held
  across the gaps where the camera had lost the object. The aperture then sat on bare ground, and 175 of 530 frames
  read as lost against what was behind it, over the 10 % past which no beat is looked for. A track with no position for
  over `flicker.GAP_S` (0.5 s) is now measured over its longest stretch in view (`flicker.stretches`;
  `fields["stretches"]`), and the case's notes name the stretches. On this clip: 338-434, no beat of its own.
- *`symbology`: a pointer in a colour picture.* The chroma method looks for the "odd glyph out" in a ring 0.20-0.36 of
  the picture's height about the boresight. In an EO picture with colour of its own, roofs and ground pass for glyphs,
  and this pointer sits at 0.40 of the height: radius 203 +/- 34 px, mislocated. The no-power entry now names the way
  round it: `--method hue --box` for a warm pointer, `--method template --tpl-box` for any other. `hue_glyphs` takes a
  glyph up to 60 px tall and wide where a box is given (30 where not, as before): the red triangle is 36-42 by 26-30
  px. With a box round it, all 180 frames solved, radius 290.87 +/- 0.84 px, the pointer turning +0.036 deg/s.

Drawn tests in `tests/test_measurement.py`: a textured strip crossed by lines between flat panels takes 64-px
templates and its shift comes back; a picture textured all over keeps 128. Candidates by hand: an object hidden under
a spot on its path is not traded for it, and one that stays put with marks on it is linked on every frame. A track
with a 19-frame gap is measured over its longest stretch, and its beat is found there. A 40-px warm triangle is found
in a box and not without one.

## 27. `mcdonald horizon` -- the sea's horizon as a ruler (added 2026-10-27)

**What it answers.** How far can a thing seen against the sea be, and how high must a thing above the horizon be --
with no motion, no known size, and no range? ROADMAP 0.4's objective 2 (the ideas bank's V12, from the visual-arts
survey's single-view metrology).

**The geometry.** From height h the visible sea horizon lies the **dip** below level: cos(dip) = R'/(R' + h), about
sqrt(2h/R'), with R' the Earth's radius as a refracted ray sees it, R/(1 - kappa): kappa 0.13 in a standard atmosphere,
0 with none, 0.25 over a cold sea (and more where a duct forms, which the band does not cover). From 7,000 ft the dip is
1.48 deg with no refraction and 1.38 with it, and the horizon is 177 km off. A thing delta below the horizon line is
on a ray of depression dip + delta, which meets the sea at d_s (`horizon.surface_range`, a sphere's chord); a thing seen
against the sea is in front of it, so **its range is at most d_s**: from 7,000 ft, 57 km a degree below, 29 km three
degrees below (close under the horizon the bound is weak, and it tightens fast below it). A thing above the horizon line
is on a ray that never meets the sea, and **it is at least as high as that ray's lowest point** (where it passes closest
to the Earth's centre, `horizon.lowest_height`) at any range; at a range known from elsewhere, its height
(`height_at`).

**The line.** Found in the picture, not assumed level: from a point a person put on it (`--horizon N,X,Y`, or a
`horizon` mark in a `mcdonald mark` file), the strongest straight step in brightness from top to bottom within 12 px of
it and 10 deg of level (`horizon.fit_line`: the vertical derivative of a Gaussian of 1.5 px, averaged along each
candidate line over the columns the overlay leaves clear, its peak refined by a parabola), then followed from frame to
frame along the track, each frame searched within 2 deg of the last one's tilt (`follow`). A line is one whose step
stands 10 MADs over the lines of its tilt across the whole frame's height, 6 px or more off it: a frame of noise, its
best line chosen from the whole search, reaches 4.6-6.2; a rendered sea under a sky 37, and a faint one (a step of 5
grey levels) 22. `--line X0,Y0,X1,Y1` gives it for a camera that holds still. The object's angle from the line is its
distance across it in square pixels (`--pixel-aspect`) over k.

**The band.** Each bound is the conservative corner of the box of what is not known exactly: the line's and the
object's place (the frame-to-frame scatter of the object's distance from the line, at least a pixel, and a pixel for
the object), k's share (10 % for an assumed field of view, `--k-share`), h's error (`--height-err`), and kappa from 0 to
0.25 (`--kappa=LOW,HIGH` gives another band; `fields.kappa` is the band used, low, nominal and high). A range bound
takes the farthest range in the box, a height bound the lowest height. A thing whose band reaches the line is neither
below nor above it, and gets no bound.

**Refraction outside the band, and a duct (W8, added 2026-11-13).** The real air does not keep to 0-0.25. For sight
lines near the surface the effective kappa "varies from moderate negative values (on sunny days) to values considerably
larger than 1 (at night, or for sight-lines over cold water)" (A. T. Young, "Dip of the Horizon", San Diego State
University's pages on atmospheric refraction), and the dip depends almost wholly on the air's temperature at the camera
against that at the horizon (Young and Kattawar 1998, Applied Optics 37, 3785). So no band both covers the air and
leaves a bound, and the stage says instead which way each bound breaks. Both quantities grow with kappa, at every
height and angle (held from kappa -1 to 0.98 in `tests/test_horizon.py`), so each bound breaks one way only:

- *The range's "at most" is too short where the air bends light more than the band's top* (warm air over a cold sea;
  at its limit a duct). The dip shrinks and the sea lies farther along the same ray. From 7,000 ft, 2 deg below the
  line: 38.8 km at kappa 0.25, 41.4 at 0.5 (+7 %), 45.5 at 0.75 (+17 %), 57.0 at 0.99 (+47 %). A sea warmer than the
  air only shortens it (35.4 km at -0.25), and the bound holds.
- *The height's "at least" is too high where kappa is below the band's bottom* (a sea warmer than the air: light bends
  away from the sea, the dip grows -- 1.82 deg at kappa -0.5 against 1.48 at 0 -- and a ray a given angle over the line
  starts steeper and runs lower). From 7,000 ft, 0.5 deg above the line: 1,196 m at kappa 0, 1,093 at -0.25 (-9 %),
  1,013 at -0.5 (-15 %); 1.2 deg above, -4 and -8 %. Stronger bending only raises it, and the bound holds.

Every run that gives a bound says this: `fields.bounds.breaks_if_kappa_above` (a range bound: the band's top) or
`breaks_if_kappa_below` (a height bound: its bottom), a line under the bound in what the command prints, and a note in
the case ("The horizon's limit on range assumes the air bends light toward the sea by no more than 0.25 of the Earth's
curvature ... the object can be farther than that limit."). Someone who knows the air gives the band:
`--kappa=-0.5,0.25` lowers a height bound to what a warm sea allows (1.2 deg above from 7,000 ft, k 50 px/deg: at least
1,742 m against 1,935), `--kappa=0,0.75` lengthens a range bound (2 deg below: 50.3 km against 42.4). The words follow
the band given.

*A duct.* At kappa 1 a level ray follows the Earth's curve, and above 1 it is bent back down: R' = R/(1 - kappa) is
infinite or negative and there is no horizon. Before 2026-11-13 `radius(1.0)` divided by zero, and above 1 `dip` failed
inside `acos` while `surface_range` handed back a negative range (-3,374 km for a ray 3 deg down at kappa 1.2). Now
`radius`, which every
function of the geometry calls, refuses a kappa of 1 or more with the reason; the stage gives NO POWER for a band that
reaches 1 (the line is still found and the object set against it; no bound), and the command exits 2 with the reason
for a `--kappa` typed so, before it looks for the video. None of this was reachable with the stage's own band.

*Traps.* (1) The constant-kappa Earth is a model of the whole path. A surface or evaporation duct fills the lowest
tens of metres to about 300 m, not the 2 km under an aircraft, so from height the effective kappa moves far less than
near the surface, and from a ship's deck or a low drone far more; the stage's band does not know the camera's height.
(2) The band 0-0.25 is the stage's choice (a standard atmosphere and a cold sea), not a measured range of the air:
the notes say what it assumes, not that the air obeyed. (3) `run` and the window's form take no band: they use the
stage's, and a wider one reaches a case only through `mcdonald horizon ... --kappa=... --case CASE_JSON`.

**What it assumes, and says on every run.** (1) The line is the sea's horizon: not a haze top (which lies above it), a
coastline or a cloud deck (nearer, and at heights of their own), nor a skyline over land, which is terrain at a range of
its own and gives neither bound. (2) For the range bound, the thing is seen against the sea itself and not against
something nearer standing up from it. (3) h is the camera's height over the sea. (4) k is the scale across the line.

**Validated.** Closed forms and rendered scenes (`tests/test_horizon.py`, seconds): the dip with and without refraction
against sqrt(2h/R) and its sqrt(1 - kappa); a ray just under the horizon meets the sea at the horizon's distance, one
steeply down at h / sin(depression); a ray's lowest height is zero when it grazes the horizon. A sea under a sky with
the horizon tilted 1.5 deg, the point given 5 px off it: the line to 0.07 px and its tilt to 0.01 deg; followed over 40
frames while it drifts 48 px and turns 0.8 deg, under an overlay, within 0.5 px on every frame. An object 2 deg below
the line from 7,000 ft at k 50 px/deg: at most 42.4 km (nominal 37.8); 1.2 deg above: at least 1,935 m (nominal 2,096).
Refraction (W8): the four shares above (+6.7, +17.2, -8.6, -15.3 %); both bounds growing with kappa; a kappa of 1, 1.2,
1.5 or infinity refused as a duct by all five functions of the geometry, by the stage (no power, the line still found)
and by the command (exit 2, the reason in the `--json` envelope); a band given moving each bound to its own end; and
the two published bounds unchanged with no band given.
**Not yet on a real clip with a known answer**: one needs a sea horizon, the camera's height and a surface target at a
known range. PR43 shows a horizon, over land; PR149's ship and sea are the nearest candidate if its altitude can be had.

**What it cannot do.** Say anything of a thing within the line's band; tell a sea horizon from a haze line; or use a
land horizon.

**A step of `run`** (since 2026-10-29): where `run` (or the window's Measure form) is given the camera's height
(`--height`) and a point on the horizon (`--horizon FRAME,X,Y`, or the first horizon mark in `--marks`), it does this
command's own call -- with the command's own k, (FOV px) / FOV across the frame or the graticule's, not the case's
pinhole k, so that the two give the same number -- records the command, and a range bound is the range's ceiling among
the four unknowns and in the admissible region (`stages.OPTIONAL`). A height with no point is said to want one. Given
after the case was measured (the report card's form, `mcdonald report CASE --height ... --horizon ...`; `stages.LATER`),
the same call is made on the track already followed, and forgotten, the step is taken out.

## 28. `mcdonald focus` -- sharp means far (added 2026-10-27)

**What it answers.** Is the object far enough to be as sharp as the scene's own points -- a floor on range from one
frame, from neither motion nor a known size (the ideas bank's V5; the visual-arts survey's §1.1, after the insect
note's near-lens test).

**The method.** A lens focused at distance s draws a point at distance d as a disc of angular diameter D |1/d - 1/s|,
D the entrance pupil (Pentland's depth from defocus). Focused at infinity it is D/d. The clip's point spread b is
`forensics.point_blur`'s (the sharpest quarter of the scene's compact spots, at half their peak, defects and clipped
spots left out), and the object's width W is measured the same way. An object no wider than RESOLVED (1.5) points can
hide a disc no wider than what 1.15 W leaves over b in quadrature, and never less than half a blur (a disc of half a
blur widens a point by 12 %, about the least a width shows): disc <= max(sqrt((1.15 W)^2 - b^2), b/2). Then
**d >= D / disc**. Where no pupil is given (`--pupil`), the optics cannot draw a point narrower than their own
diffraction, b >= 1.22 lambda / D, so D >= 1.22 lambda / b and **d >= 1.22 lambda / (b x disc)**, every angle in
radians at k's low end (k x (1 - its share): the bound goes as k^2 without a pupil and as k with one). The band's
shortest wavelength is taken: 3 um for MWIR, 8 for LWIR, 0.4 um for visible light and for a band not named. Focused at
s instead, the floor is 1/(1/s + 1/d_inf) (`--focus`); the scene's points are sharp at their own range, so s is at
least as far as they are.

**An example.** At k 900 px/deg (0.7 deg over 640 px) with a 2-px blur, an MWIR object as sharp as a point is at least
4.1 km off through diffraction alone (`tests/test_focus.py`, worked by hand), 4.3 km with a 10-cm pupil.

**What it assumes, and says on every run.** (1) The sensor is focused far, at infinity or at the scene's own points: a
camera that refocuses on the tracked object makes it sharp at any range, and then the bound says nothing; a scene sharp
behind the object is the check. (2) The width is the object's image's, not its smear's. (3) The blur b is the optics'
and the chain's: a codec or a display that blurs everything makes b wider, which weakens the bound and does not falsify
it.

**Validated.** Rendered frames (`tests/test_focus.py`): thirty points 2 px wide on a noisy ground give the blur at
1.99 px; an object drawn as one more point is "as sharp as a point" (2.01 px) and gets the floor worked by hand; a
flat-topped disc 9 px across (a near thing out of focus) gets none, its width said; a clip with no points has no blur
and no bound. The floor in metres has not yet met a real clip with a known answer (the one tried, AARO's Puerto Rico
lanterns, has no sharp point in its streaming scene and gives none); the edge's r/R has, below.

**Wider than a point, or clipped: the edge (MEO11, added 2026-10-28).** A dark object wider than its points, or one
whose core clips at black so that a Gaussian cannot say how wide it is, is read by its edge (`focus.edge_blur`): on
12 frames, profiles out from its centre every 30 deg, those within 35 deg of the axis it moves along left out (a smear
lengthens it there), each fitted with a disc of radius rho seen through a Gaussian sigma (exact: a noncentral
chi-square of two degrees), the samples at or past the clip left out. A defocus disc of diameter b adds b^2/16 to
sigma^2. So **b <= 4 sigma** assuming nothing of the camera's own blur, and **b <= 4 sqrt(sigma^2 - sigma_points^2)**
assuming it blurs as the scene's points do, sigma at the 95th percentile of a bootstrap of its per-frame medians.
**The trap it closes:** a small thing far out of focus is drawn as a faint disc whose edge is as sharp as the thing is
small (the disc of the defocus convolved with the thing's own), so a sharp edge alone says nothing. Its core is then
paler than black by at least (thing / disc)^2 whatever its own shade, so both bounds are divided by the square root of
the core's depth as a share of the way from the ground beside it to the screen's black (0, the cautious choice; one,
where the core reaches it), at that share's 16th percentile over frames. Only a dark object is read so: nothing is
darker than black, but a bright thing may outshine the whole scene, and a small one far out of focus draws the same
sharp-edged disc, so a bright object wider than a point still gets no bound. The disc then goes through the floor
above in place of the width's (with k), and with a ground scale s (m/px, `--ground-scale`) and a pupil A, focused on
the ground at R, b = (A / s)(R / r - 1) gives **r / R >= 1 / (1 + b s / A)** with no k and no R (for the pupil
given, else 5, 10, 15 and 20 cm).

*Validated* on rendered frames (`tests/test_focus.py`): a black disc 14 px across in focus leaves a disc under 3 px
(edge sigma 0.99 against the points' 0.85); one 6 px across whose core clips is read by its edge; 14 px out of focus
by 8 gives bounds of 9.6 and 10.2 px; and a 4-px thing out of focus by 12 -- a disc 12 px across with an edge sigma of
only 1.49 -- is held off by its pale core (11 % of the way to black): bounds 15.9 and 18.8 px. *Known answer*: the
AARO Middle East Object's stare (210-259), measured by hand against a person on the road (sigma 1.30-1.42 px against
1.45; r/R >= 0.17-0.19 at a 10-cm pupil assuming nothing, 0.32 assuming the person's blur): `focus` reads sigma 1.27
(95 %: 1.36), its core 96 % of the way to black, r/R >= 0.18 assuming nothing and 0.35 as the points. **The "as the
points" column is only as good as the points**: there the scene's sharpest compact spots are 4.7 px wide (sigma 2.0),
blurrier than the person (1.45), so that column is the more optimistic; the column assuming nothing is the one to
quote. Two biases are said on every run: coding softens a moving object more than the still ground (toward finding a
disc), and turbulence over hot ground blurs the ground's points more than an object above it (toward hiding one); the
bound assuming nothing is free of both.

*Held against a real known range* (2026-10-29). AARO's Puerto Rico lanterns, dark on the black-hot display, over
1640-2231 (their range 2131-2567 m from their path, the ground point's 3558-3924 m from the data bar, so r/R 0.59-0.66):
the ground streams at ~20 px a frame and no point in it is sharp, so no floor in metres; their edge reads sigma 2.19 px
(95 %: 2.40), the core 85 % of the way to black, a disc of at most 10.4 px assuming nothing, and with the ground's
scale beside them (0.037 m/px: the ground point's range over k from `slew --platform --los`, 1727 px/deg) **r/R >= 0.11,
0.21, 0.28 and 0.34 at a pupil of 5, 10, 15 and 20 cm, against the truth's 0.59-0.66**: it holds at every pupil, two to
five times short of the truth -- a floor, as it should be, and a loose one.

*With no points in the scene.* Where the ground streams past at tens of pixels a frame every point is smeared and
`point_blur` finds none (PR062's narrowest field); a dark object is then read by its edge all the same, and only the
bound assuming nothing is given (no floor in metres, which needs the blur). The camera's own blur can still be had from
ground edges that run along the streaming direction, where smear does not reach: done by hand on PR062
(`analysis/tools/orb_edge_reference.py` in the PURSUE repository; to come into `focus`). There the ball's edge softens
from sigma 5.4 to 2.8 px over three minutes as it recedes, while the ground's edges hold at 2.3-2.4: a defocus disc
collapsing faster than the body shrinks (sigma over radius 0.41 -> 0.26), which a fuzzy body seen farther away does
not do. And a defocus disc over the object's own image is (A / D)(1 - r / s), so **D <= A x image / disc** with no
range and no k (PR062 at 8-12 s: D <= 1.4-1.7 A). Also to come into `focus`.

**A step of `run`** (since 2026-10-29): the camera's band (`--band`; in the window's plain form "What kind of camera was
it?") starts it -- Jacob's choice, so that no report carries a floor resting on "focused far" that nobody asked for --
with `--pupil`, `--focus-at` and `--ground-scale` beside it. It is this command's own call with the command's own k
((FOV px) / FOV, or the graticule's), the object's polarity and the mask rows the case has; its floor is the range's
among the four unknowns and in the admissible region (`stages.OPTIONAL`, `focus_step`). Given afterwards (the report
card's form, `mcdonald report CASE --band ...`; `stages.LATER`), the same call on the track already followed.

**What it cannot do.** Bound a bright object wider than its points; tell a soft-edged thing (smoke, a puff of dust)
from one out of focus from one frame (a soft edge bounds nothing; a sharp one is the result; the change of softness
against size as the object's distance changes can); or find the camera's blur in a scene with no points and no
edges.

## 29. `mcdonald haze` -- the air as a ruler (added 2026-10-27)

**What it answers.** How far can a dark object be, from how pale the haze has made it -- no k, no motion (the ideas
bank's V15; the visual-arts survey's §6.1).

**The method.** Koschmieder (1924): a dark object's contrast against the horizon sky behind it falls with range as
e^(-sigma d), sigma = 3.912 / V for a meteorological visibility V. Its own contrast cannot be darker than black
(C_0 >= -1), so its apparent contrast |C| <= e^(-sigma d) and **d <= -ln|C| / sigma**. William K. Hartmann used this on
the 1950 McMinnville photographs for the Condon study (Case 46): sigma calibrated on distant hills (0.289 km^-1),
checked on a barn and a house at known distance, right to a factor of about four -- the honest size of its error,
which the report gives with the bound. C is measured in **linear light**: the object's darkest quarter of its disc
against the median of a ring 2-4 of its sizes out (the overlay left out), both taken back through BT.709's transfer
function (a grey of 128 is about a quarter of white's light, not half; an automatic gain multiplies both and cancels).
The bound is the palest frame's, the median frame's beside it. sigma is the visibility's (`--visibility`), or calibrated
in the frame on something dark at a known range (`--reference N,X,Y,RANGE`), whose own contrast is taken as black's:
the smallest sigma it can be, so the largest bound.

**What it assumes, and says on every run.** A daytime visible-light picture whose levels follow BT.709 (a camera's log
curve or a display's contrast stretch does not); the sky behind the object is the horizon sky the haze lights; the haze
is even between camera and object; the object is darker than its sky. A bright object's intrinsic contrast has no
ceiling and gives no bound. In infrared the contrast is a temperature's, and there is no bound.

**Validated.** Rendered frames through BT.709 (`tests/test_haze.py`): a black object 5 km off in 20-km visibility is
bounded at 4.96 km; one with half its sky's light at 8.44 km (beyond its range, as a bound must be; Koschmieder's
8.54); a bright one not at all; a black reference at 3 km gives sigma back to 0.5 %. **Not yet on a real clip with a
known answer**: the PURSUE clips are nearly all infrared; AARO's daytime EO clips and Hartmann's own case are where to
try it.

**A step of `run`** (since 2026-10-29): where `run` (or the window's Measure form) is given `--visibility` or
`--haze-reference`, it does this command's own call on the case's track at its spot size, records the command, and the
bound is the range's ceiling among the four unknowns and in the admissible region (`stages.OPTIONAL`). Given afterwards
(the report card's form, `mcdonald report CASE --visibility ...`), the same call on the track already followed.

## 30. `mcdonald streak` -- the dash as a light curve inside the frame (added 2026-10-27)

**What it answers.** What does a dash -- a fast object smeared across one exposure, as PR43's is -- say about the
shutter and about the object's light between frames (the ideas bank's V14; the visual-arts survey's §2.2, after the
insect note's "rods")?

**The method.** Read along the track's own direction through the track's place in each frame (0.5-px steps, averaged a
pixel either side, less the mean of the same line 6 px and a blur to each side), the dash is the object's brightness
over the exposure laid out in space, one pixel being 1/speed seconds (at 900 px/s, 1.1 ms). **The exposure** is the
dash's length at half its peak -- on the profile smoothed over three blurs, so that beads deep enough to dip under half
do not end it, and as it is for a dash shorter than the smoothing -- taken back through the blur, over the speed; times
the frame rate, the shutter's share of the frame. Taken back exactly (`streak.motion_px`, since 2026-10-29): a box of
motion drawn through a Gaussian blur is the box's length at half its peak once it is a couple of blurs long (its
half-peak ends are the box's), and the blur's width only where it is short; until then the blur was subtracted whole,
which read a half-frame shutter as 0.46 of a frame at 51 px a frame through a 2-px blur and 0.34 at 20 px through 3.5.
The blur is the picture's own, read off the scene's compact points (`forensics.point_blur`, as `focus` reads it;
`--blur` to give it, 2 px where the scene has too few points). **A flicker** leaves beads spaced by its period times the speed. Inside each dash
(a blur trimmed from each end, a straight line taken out) the power at each frequency is summed over every dash, and set
against the same from a null line -- the two side lines' difference, scaled to the dash line's noise (the dash line
less the sides' mean carries 1.5 times one line's noise variance, the difference 2 times). Since 2026-11-02 the sum is
on a frequency axis in hertz, each dash's spectrum read at its own speed (a flicker is so many hertz; dashes of
different speeds put it at different spacings, and a sum in cycles a pixel smeared it). The largest ratio within the
band (two or more cycles in the dash, beads at least two blurs apart) is reported with the chance an F ratio with 2N
degrees of freedom on each side for N dashes gives it from noise alone, times the frequencies looked at -- **as a
reading, not a verdict**: until 0.4.2 the stage called a flicker under 1e-3, and that chance is not the test's false
alarm (below), so the stage now reports the beads' spacing, rate and power over the lines beside them and says, as no
power, that a flicker inside the frame is not decided.

**Why no verdict** (the single-camera survey's D4, 2026-11-01, rebuilt and taken further 2026-11-02; the scripts and
runs in `/scratch/mcdonald/c042-2026-11-02/small/`). Steady dashes drawn with no flicker -- 12-24 frames at 30-70 px a
frame on a 1280x720 picture, blur 1.8-3.5 px, peak 25-150 DN, a track's dashes one test -- passed the F test at 1e-3
as follows (the survey's own counts in brackets):

| sky | no codec | x264 CRF 18 | CRF 23 | CRF 28 |
|---|---|---|---|---|
| flat, noise 0.7-4 DN | 3/45, 7 % [3/44] | 36/45, 80 % [34/44] | 44/45, 98 % [44/44] | 43/44, 98 % [44/44] |
| real PURSUE frames | 4/45, 9 % [3/36] | 13/45, 29 % [10/36] | 22/45, 49 % [13/35] | 23/44, 52 % [16/34] |

A codec flattens the smooth lines beside a dash to nothing and textures the dash itself, so the ratio of the one to the
other climbs toward the top of the band (every pass sat at 2.0-2.1 blurs' spacing, the band's edge) and reaches any
value a flicker does: steady dashes through CRF 23 read 13 to 1,500 times the power beside them. Two remedies were
built and measured. **The band's top moved off the blur's roll-off**, from two blurs to three: the passes moved to the
new edge (3.0-3.1 blurs) and the rates did not change (flat sky through CRF 23 and 28: 91 and 97 %; real frames 22-35
%), while dashes under about eight blurs long lost their band altogether; the top stays at two. **The null drawn in the
clip**: eight steady dashes of the object's own brightness, length and direction on paths beside its own, in the clip's
frames, through libx264 at the clip's bit rate (the flicker stage's encoding control), read the same way, and the
object's ratio tested over theirs. On a flat sky through CRF 18 that brought 80 % to 0-3 %; through CRF 23 and 28 it
left 91-97 %, and on real frames 22-36 %, because the control is a second-generation encode: the decoded frames have
lost the noise the first encoder spent its bits on, so at the same bit rate the second runs at a far lower quantizer and
draws clean dashes (their ratios 0.1-5 where the object's read 13-470). The first encoder's operating point is not in
the stream's bit rate, and a faithful control needs it (the quantizer, or the frames before the encode: the planting
tool of ROADMAP 0.6). A planted 150-Hz flicker at 60 % depth is read on every track (46/46 with no codec, 46/46
through CRF 23, 40/40 with speeds +-30 %, 38/42 on real frames) -- the reading has power; what it lacks is a null.
**What it assumes, and says on every run.** The object moves straight during one exposure at the track's speed; the
dash is the object's (a camera turning during the exposure smears the scene too); the beads are the object's light and
not the scene behind it, which the side lines take out.

**Validated.** Rendered frames, a point drawn step by step while a 180-degree shutter is open (`tests/test_streak.py`):
steady at 51 px a frame, the exposure 0.50 of a frame and nothing standing out among its beads (2.3 times the power
beside the dashes, a 0.33 chance from noise alone); blinking at 300 Hz, beads every 4.7 px read, 329 Hz at 312 times
the power beside the dashes (a 4e-27 chance from noise alone) -- a reading, said not decided; eight steady dashes
through libx264 at CRF 28, a reading each and no verdict, the blink through the same codec read at 305 Hz; at 2 px a
frame, no dash long enough; at 20 px a frame through a 3.5-px blur read off 24 points of the scene, 0.52 at the blur
read and at 2 px alike; at 10 px a frame, a dash under twice the blur, 0.52. **PR43** (its case file's track, frames 50-75, 2026-10-29): its points read a blur of 3.6 px (43 spots on 12
frames); the dash, 6.5-7.0 px at 18.5 px a frame, gives 15.6 ms (0.47 of a frame) at that blur and 14.7 ms at 2 px --
the median of the frames' own ratios; the ratio of the medians is 12 ms -- the centroid's jitter (the speed band's
nugget, 5.7 px) spreads the frames' speeds. Under three of its own blurs, it has no light curve: the bead search made at
an assumed 2 px (none, false alarm 5.8e-3) does not stand. On the case file's track of 2026-11-01 (frames 50-74, 40
spots, blur 3.6 px, 16.3 ms, 0.49 of a frame) the same: no light curve, and the eight dashes long enough to read leave
no room for two cycles of beads two blurs apart, which the stage now says; at 2 px, 11 dashes read, "none" before
0.4.2 (beads every 4.1 px, 136 Hz, 2.6 times the power beside the dashes, a 0.078 chance from noise alone, summed in
cycles a pixel) and since 0.4.2 "nothing stands out" (every 4.1 px, 196 Hz, 3.8 times, a 0.007 chance, summed in hertz
-- its speed runs from 7 to 33 px a frame along the track, so the two sums differ, and the peak sits at the band's
top edge as a codec's does): a reading either way, and no flicker.

**What it cannot do.** Read a dash under three blurs long, beads under two blurs apart, or a flicker slower than two
cycles over the dash; or tell beads from a codec's texture, so it calls no flicker inside the frame.

## 31. Each template's own error, and a template sure only across its streaks (K9, added 2026-10-28)

**What it answers.** How sure is one template of where it was found, and how sure is a pair's shift? Until now a
template was good or not (`forensics.good`: a peak of 0.5 or more, 0.05 above its runner-up), a pair's shift was the
median of the largest group of good templates agreeing within 6 px across and 2.5 down, and the count of eight was
the only guard. The ROADMAP's K9: the regression's weights (§17's slew, the speed band's K1) need a pair's error, and
a scene streaked across the picture leaves few templates good at all -- PR051's terrain (§17), where of a pair's 69
templates 55 have their runner-up 13 px along the streaks at the peak's own height, and the eight a consensus needs
were not there in most pairs.

**The error from the peak.** The ZNCC's negative Hessian at the peak, K (px^-2, from the 3x3 neighbourhood's second
differences, which `shift_field` already took the anisotropy from), is the structure tensor of the normalised patches
over their N pixels, and their residual variance at the match is 2 (1 - pk): the least-squares covariance of the
shift is 2 (1 - pk) / N * K^-1. On drawn textures with white noise in both frames (`/scratch/mcdonald/v04-s4/probe/`,
isotropic and striated, noise 0-20 DN on a texture of 40-70) the residuals come out 3.5 times that in sigma at every
noise level -- the band-pass correlates the pixels -- and 0.02 px at zero noise, the parabola's own error: the
covariance is scaled by 3.5^2 and 0.02^2 added (`PEAK_ERR_SCALE`, `PEAK_FLOOR_PX`), and the drawn residuals then
pull at about 1 (`tests/test_measurement.py`: the Mahalanobis residual's median 0.75 against 1.39 expected). On a
real scene they do not: PR135 150-305's held pairs scatter nine times what their peaks say (0.05-0.16 px over five
frames against 0.008-0.017 predicted; the island drifting behind the pattern, the pattern's own jitter), so a
group's information is scaled down to its members' own scatter (below), and a pair's error is never less than they
support. Each row keeps the information matrix W = C^-1 (`wxx`, `wyy`, `wxy` in `SHIFT_COLS`), not C: a ridge has
none along it.

**A template sure only across.** A template whose runner-up (outside the 25-px zone about the peak) is within the
gap of 0.05 of it is as well matched there as at its peak: along the line to the runner-up it says nothing, across
that line what its curvature says. `peak_information` keeps its information across alone and its `ridge`, the
runner-up's distance; `ridged` picks such rows out as `good` picks the sure ones. In a pair's consensus they are
members where they agree with the group across their ridge within the tolerance and along it within the ridge's
reach plus the tolerance (13 + 6 px on PR051), and they count towards the eight; they fix nothing along their
ridge, so the group also needs three templates sure both ways, and a shift the group leaves unconstrained along some
line (its sigma over the tolerance) is none. On the drawn streaks (sigma 40 px along, three sharp patches): 36 of 40
templates sure only across, four sure both ways, no consensus by the old rule; with the ridges counted the group is
found, the shift right to 0.03 px and its error ten times larger along the streaks than across; with no sharp patch,
none. The held-still rule is untouched (`shift_field_auto` judges by the good templates, as before).

**The weighted shift** (`forensics.weighted_shift`). Generalised least squares over the group, each member by its
own W; the pulls (each member's residual along its own axes over its sigma) give a scale, their robust spread where
over 1, by which every W is divided; a member further out than 2.5 sigma is weighed down to there; and the group's
covariance is the inverse of the summed information. On a rigid drawn scene a pair is +/-0.004 px; with half its
templates 1.5 px off (inside the 6-px tolerance) +/-0.12, the scatter's 0.75 / sqrt(40). `layers_of` returns each
class's (shift, members, covariance); `layers` writes the largest group's sigma to the CSV (`err_x_px`, `err_y_px`,
over k frames) and reports the pairs' median and 84th percentile (`shift_error_px`); a pair unmoved between a
repeating picture's catch-ups keeps its own field's covariance. `slew.read_layers(errors=True)` reads them,
`slew.scene_path(err=...)` weighs each step's pairs by their inverse variances and carries the path's own error
along each stretch (each pair's whole shift enters the path once over its k steps, so the steps' errors are summed as
the pairs', not independently), and `slew`'s window result has `scene_path_err_px`, the chain's error across the
window. The fit itself is unchanged: the pointer's scatter (0.1-0.2 deg, hundreds of px at any c) is the noise, the
chain's error of a few px is not. `comotion`'s annulus takes the same weighted mean where it lands within 3 px of
the patches' median.

**Checked.** `tests/test_measurement.py` (drawn: the pull, the rigid and the loosened pair, the streaks with and
without sharp patches, the weighted chain, end to end through `layers` and the CSV); PR135 150-305 before and after
to 0.02 px a pair (members up by one to four, the errors 0.007 px); PR144's goldens as they were; and PR051 (§17): 37
% of pairs with a consensus against 12 %, half the templates counted across their ridge, the pairs' errors 0.18 px
median and 0.8 at the 84th percentile over two frames, the chain over 5.0-9.5 s at 94-95 % of the data bar's path,
now a golden check. **Not yet:** a sharp template wrong by a bump on its ridge is caught only by the group's
tolerance and the Huber weight, not by its own error.

**PR051's 10-13 s, read (the fourth session, 2026-10-28).** Every other catch-up step there had no consensus at all.
Their fields showed three things, none of them K9's. (1) The masks: the upload's bright terrain carries a colour
tint (46-54 DN of chroma) on 18.7 % of the frame, under the fifth that calls a clip colour, so the chroma masks
took half the picture and the sharp parts first -- `layers` kept 29 templates of 85 a pair (§3, the tint). (2) The
holds: a repeated capture of one picture lands 0.3-1.9 px from the last (the capture's jitter), and the unmoved
rule's 0.5 px sent half of them to a second pass over a second, where a scene that moves 600 px has no match: a hold
is now unmoved inside the zero zone (4 px) with nearly every template in the one group (`layers.AT_ZERO`,
`REPEAT_SHARE`); a catch-up along the streaks whose match failed is matched at zero by a few templates (603-605: 16
of 79) and is not one. (3) The big steps: catch-ups of 70-140 px along the streaks leave 0-2 templates sure both
ways, under the three a group needs, while 60 or more are sure only across -- and along their ridge each one's peak
is a vote for a place (its match is ambiguous by the streaks' own 13-px period), the true shift the one place they
vote for together. `consensus` takes that vote where the sure templates are fewer than three (`_vote`): the largest
cluster of all the templates' shifts is the group where it leads every other cluster a ridge's length or more away
by `VOTE_LEAD` = 2 sigmas of a split vote (n1 - n2 over sqrt(n1 + n2)); the ridge members then carry information
along their ridge equal to the cluster's own scatter (at least `VOTE_FLOOR_PX`), and the group's error along is
floored at that scatter -- a vote is good to its resolution, not to its count. On those pairs the lead is 2.0-3.4
sigma (26 votes against 13; 32 against 10) and the vote lands within 1-4 px of the sharp templates where there are
any (603-605: 85.1 against 89, 89); on drawn streaks it is unanimous (+/-1.0 px along, the floor); split 13 px apart
between two halves of a scene it is none. And (4), found on the way: a same-position ZNCC of 0.9 or more no longer
says "held still" on its own -- on terrain streaked along its motion it stays above 0.9 through a step of 15-35 px,
and the field read with zero allowed splits between the streaks matched on themselves at zero and the step (a group
of 7 px for a step of 18). `shift_field` now gives the field with zero left out and the one with it allowed from the
one search (`zeros=`), and `shift_field_auto` reads the first wherever a fifth of the templates placed are sure of
their match or it has a consensus (`moved`); a picture truly held keeps a handful of templates there (the peaks sit
on the zone's rim and are dropped) and falls back to zero allowed as before.

**Checked.** `test_measurement`: the tint and the gate, the holds inside the zone and the minority zero, the vote
on drawn streaks and the split vote; PR135 150-305 the same to the bit; and PR051 (`--k 2 --step 2`, the boxes):
every pair over 4.5-13.5 s has a consensus (49 % of pairs a step, 67 % unmoved, 2 steps bridged where 126 were),
and the chain runs whole over 4.5-13.5 s at 0.93 of the data bar's path over 5.0-9.5 s and 0.91 through 13.5 s --
a steady shortfall where the broken chain, bridged at its neighbours' rate, had read 0.95. The holds' own shifts
(median +0.2 px) are 1 % of it; the rest is open: the bar's reading by eye, the 7-deg azimuth taken for the line of
sight, or the picture's timing against the data bar's text. The golden check holds 5.0-9.5 s to 10 % and 5.0-13.5 s
to 15 %.

## 32. The speed band: the rate along the track from its own covariance (K1, K8; added 2026-10-28)

**What it answers.** How fast was the object going at each moment, and how sure is that? `fit_v_px` (§5) fits one
line through the track and reads one rate off it; where the residual is more than 5 % of the distance covered it says
"not uniform" and every speed that rests on that rate is refused. That is right as far as it goes -- a line does not
describe a bend -- but most recorded tracks bend, and a report often turns on whether the speed changed. The kriging
survey (uap `analysis/methods/kriging_methods_survey.md`, 2026-10-15/16, §1.1-1.2) fitted every recorded track and
found none of 23 is a line with white jitter: the scatter about the line is the path bending (0.4-134 px rms), while
the jitter itself -- how well the detector holds the object from one frame to the next -- is 0.1-1.5 px. With the two
told apart, the rate at each instant has an error up to 13 times smaller than a frame-to-frame difference (median 8),
and a track that bends has a speed after all: one that changes, described instead of refused.

**The model** (`kriging.py`; `kinematics.speed_band`). Each coordinate of the track against wall-clock time is
universal kriging: a line (intercept and slope) plus a correlated wander plus independent jitter,

    x(t) = b0 + b1 (t - tm) + f(t) + e,    f ~ GP(0, k),    e ~ N(0, tau^2),

with k the Matérn-3/2 covariance, s^2 (1 + c|r|) exp(-c|r|), c = sqrt(3) / ell -- a process that is once
differentiable, so its rate f'(t) exists and has a band of its own (a Gaussian kernel would make that band
overconfident: Stein 1999). The three numbers of the covariance -- the sill s, the range ell and the nugget tau -- are
fitted by REML (the mean's parameters are not charged to the noise), searched in logs from three starts (the range at
a tenth, a third and a thirtieth of the stretch), the best of them run to convergence. Frames that repeat the one
before exactly are dropped first (the picture did not update; read as a measurement, a held frame shrinks the nugget
and fakes a velocity step: the "time, not frames" lesson of §5). Then the track's jumps are named, and the points of
its glitches and excursions -- the linker on a neighbour or a wing for a frame or a few -- are left out of the fit
(*Jumps named*, below). A track longer than 450 points is fitted on its middle 450 and read in windows of 450,
each with a trend of its own (a moving neighbourhood: a long track's local trend is its own).

**What it reads.** From the fitted model, each with an error that includes the mean's own uncertainty:

- *the rate at every kept frame*, v(t) = b1 + f'(t), kriged from the derivative covariance (Rasmussen & Williams
  2006 §9.4); the speed |v| and its sd by the delta rule, x and y being fitted apart;
- *the net velocity over the stretch*, (f(t1) - f(t0)) / T on the latent path -- the displacement over the time,
  the nugget out -- with its honest standard error from the joint posterior of the two ends. Against the line's
  white-noise error this is 0.03-0.8 times as large on curving tracks (the line charges the bend to noise) and up
  to 1.5 times larger where a straight track has a correlated wobble: the white assumption is wrong both ways. Until
  0.4.2 the report called this "on average", which it is only on a track that holds its line: it is the speed from
  start to finish, and on a path that doubles back it is far under the speed along the path (below);
- *the speed along the path*, and *the fastest* (B6, added 2026-11-02; the biology survey's T3, from ecology's
  continuous-time speed and distance, Noonan et al. 2019): from each window's joint posterior of the rate at the
  points it reads, 200 paths are drawn (`PATH_DRAWS`, seeded, so the same track gives the same band twice; independent
  between windows, as the ends are read), the speed along each is its distance over the time (the trapezoid over the
  kept points) and its fastest its largest speed; the mean and sd over the draws are `v_path_px_per_s` and
  `v_fast_px_per_s` with their errors. On the 44 recorded tracks the net speed and the path speed differ by more than
  1.5 times on 25, by 49 times on PR41 (0.8 against 40 px/s): most of a held object's path is the operator's
  correcting, so this is not the object's speed, it is what the picture's rate was. The kriged mean's fastest
  (`v_max`) reads 0.72-0.99 of the truth on drawn tracks (the mean path is smoother than the path) and its band covers
  79-92 %; the drawn fastest reads 1.00 and covers 91-94 %. The report names the two speeds where the speed changed
  ("along its path", "start to finish"), the window's card the same, and the farthest-range bound (§36) rests on the
  path speed, no longer on the net;
- *the velocity's change over the stretch*, v(t1) - v(t0) as a vector, its magnitude and its turn of direction,
  and the mean acceleration it is over T, with its sigma from the same joint posterior -- a number, not a second
  difference of noisy positions, which is the operation that amplifies jitter most;
- *whether the velocity changes at all*, as a likelihood ratio: the REML log-likelihood of the fitted covariance
  against a line with white jitter (the same mean; `kriging.white` is the closed form), summed over x and y. Under
  BAND_DLNL (10) the rate is constant within its band; the recorded tracks give 56-5,400;
- *the nugget*, "how well the detector holds this object", and what it means: from the jitter alone one pair of
  frames reads the rate to about tau sqrt(2) f (±30 px/s on PR055's sphere at 0.6 px), and the readings of single
  pairs scatter by that and by the rate's own changes; the band is the kriged rate's own sd (±3 on the sphere).
  Where the wander's range is short (PR071's hand track, 0.6 s) the band can be as wide as a pair's jitter: the
  rate itself changes faster than one pair can tell, and the band says so.

**The detector's memory** (`MEMORY_FRAMES`; B2 and F9, added 2026-11-02, from the biology survey's T4 and verify-band
and the single-camera survey's Part 7 §1.4). Held to planted truth -- straight dots of known speed added to real
decoded frames of six PURSUE clips, encoded with the clip's own settings, decoded and found by the toolkit's centroid
(111 tracks, 222 velocity components) -- the net velocity's stated ±1.96 errors held the truth 68 % of the time, where
white jitter of the same size gave 96 % and the same errors shuffled in time 97 %. The detector's error has a memory:
its lag-1 autocorrelation is 0.38, lag-2 0.21, lag-5 0.03 (the picture's blocks drag a centroid a frame or two), and
REML gives it to the Matérn as a wander with a range of 1.0-9.1 frames (80 % of the coordinates; median 2.3) and a
sill of a tenth to a third of a pixel. Read on the latent path, the net velocity then counts the detector's error at
the two ends as the object's own and states an error from the nugget alone; and the wander's log-likelihood gain
calls 87 % of those straight dots "not constant". On 19 Galileo aircraft against ADS-B (33,609 frames at 60 fps, the
truth in pixels with the lens inside it) the band's rate frame by frame held the truth 64 % of the time, the
shortfall all in its narrowest bands (sd under 0.15 px/s: 45 %; over 0.6: 93 %). The rule: a coordinate whose fitted
range is under MEMORY_FRAMES wanders with the detector's memory, not the object's, and the band there is the line's --
the slope under the fitted covariance (generalised least squares, the mean the REML fit already carries) with the
larger of its error and the ends', at every point and in the net velocity; its change of velocity over the stretch is
nil (E12's bound then speaks for it) and its wander is no evidence that the velocity changes (`dlnl_path`, the
verdict's). MEMORY_FRAMES is 10, between the two nulls (the planted dots' ranges have their 90th percentile at 9.1
frames, the recorded tracks' least is 12.3: a judgement call, flagged): at 10 the net velocity's stated error holds the
planted truth 92.5 % of the time on the four clips the number was read on and 93.2 % on the two held apart (65.8 and
70.5 % before), the rate frame by frame 96.8 and 94.8 % with its sd 0.012 px/s in place of 2.7, and 11 % of the straight
dots are "not constant". The recorded tracks' wanders have ranges of 12 frames and up (0.4-78 s), so no reference case's
band moves. On the aircraft the rate frame by frame is a second matter: there the wander's range is the whole track's
(a trend held as a wander) and the band's width at a frame is set by the model's smoothness, 0.05-0.15 px/s, not by the
data; the truth's own error and the terms the band does not hold (the lens's scale wandering along the track, the link
hopping between an aircraft's hot parts) are larger. So the band states no rate at a frame finer than RATE_FLOOR, 1/60 px
a frame (1 px/s at 60 fps), added in quadrature: 95.4 % on ten calibration aircraft, 96.4 % on the nine held out, where a
factor on the width would not do (F9: "a floor, not a factor"); on the planted dots at 30 fps it costs nothing but a
little width (97.7 % before it). The floor is not on the net velocity, which the planted dots show known to 0.013 px/s
over a track.

**Jumps named** (`kinematics.jumps`; E4, added 2026-10-29, from the economics survey's §1.2 and §6.2). Before the fit
every increment of the track is held against its neighbours, as Lee and Mykland (2008) hold a price's: its rate (the
increment over its gap in frames) less the median rate over a second either side, over 1.4826 times the median
absolute deviation of those residual rates over the same second, both coordinates together (the length of the vector
of the two). A median, where finance's bipower variation would be pulled up by a glitch's two large increments side by
side; a rate, because over a gap of several frames a wandering velocity moves an increment by the gap's length (held
as displacements, two thirds of drawn tracks with random gaps had a jump named). The scale is floored at the least
jitter a centroid is read to, 0.1 px a coordinate (as the projective test's is, §33), and at the rounding of a grid
the track is written on: a track interpolated and written to hundredths of a pixel has a scale that collapses (the
survey's Svanström V054 scored 9.4 on its 0.1-px kinks). The threshold is not the normal table's: with a second's
window the scale is itself uncertain by about 15 %, and the table's familywise 1 % named jumps on 12 of 100 white
tracks (the survey's first take). It is drawn instead: the 99th percentile of the largest statistic over 400 tracks
of white jitter on the track's own frames and gaps (seeded, so the same frames give the same threshold every time:
5.6 times the scale for 300 consecutive frames, 5.8 for 40, 8.4 for PR149's 41 points with their gaps). A jump past
it is named by the shape it leaves, as X-13ARIMA-SEATS names outliers (Fox 1972; Chen & Liu 1993): a **glitch** where
the next increment takes it back (one point off: an additive outlier), an **excursion** where the track is back within
five points (a temporary change), else a **step** (a level shift); an end point off its neighbour is a glitch, nothing
beyond it saying otherwise. The points of glitches and excursions are the track's slips, and the band is fitted
without them. A step is kept and named, since dropping points cannot undo it: the track moved to something else, a
held picture caught up, or the camera's field changed (FLIR1's 27-px step at its field change, frame 2235), or the
object or the camera moved faster than its neighbours' scale (PR071's swing, most of PR051's release's 24). The band's
rate across a step is the step's, and the speed figure marks each one. This replaces the one-pass clip of a point
four of its own leave-one-out sigmas off the fit, which named nothing, whose false alarms nobody held, and which a
track past 450 points never had.

Held to (drawn tracks, 200 a row; `tests/test_reduction.py`): on clean tracks -- white jitter, a wander, a large
nugget, a fast wander, jitter with memory (AR(1) at 0.6 and 0.9), 40 points, random gaps, a track written on a
0.1-px grid with 0.05 px of jitter -- a jump is named on 0 to 1.5 % of them. With 0.4 px of jitter and a wander, a
planted 4-px glitch is found 85 % of the time and named a glitch every time but twice; a three-point excursion of 4
px is found 78 % of the time and named an excursion 85 % of those (else a step: its points kept); a 4-px step is
found 79 % of the time, a 3-px step 24 %, a 1.5-px one 2 % (the survey's second take, each coordinate apart and no
floor: 38 % at 3 px); a 2-px glitch, under four of an increment's sds, passes 91 % of the time. Of the 45 recorded
tracks with a band (the 14 reference case files' objects and the golden tracks) 25 have a jump named (the survey's
take, each coordinate apart and no floor: 32 of 44). On 13 they are steps only, kept, so those bands do not move. On
12 glitches or excursions are left out: from PR135's member 6 (one point) and PR149 (its glitches at frames 36 and 76,
12 and 9 px: with them out the x-wander's range goes from 0.1 s, a band chasing two slips, to 4.3 s, the nugget from
0.31 to 0.61 px, and the change of velocity over the stretch from 73 ± 43 to 25 ± 4 px/s, seen at 5.6 sigma) to the
golden PR144's 41 points (its zoom's and its slews' excursions: the nugget from 0.75 to 0.51 px). Where the clip had
dropped a step's neighbours the band now carries the step, and its nugget rises (FLIR1's exit 1.3 to 2.4 px, PR071
0.21 to 0.40). None of the bands says constant, before or after; the change over the stretch is now seen (three
sigma) on PR149 and PR051's release and no longer on Svanström V030; and no projective verdict moves (PR43 fits at
1.0 times its jitter, as before; FLIR1's exit still describes its trend, at 4.3).

**Held to its own track** (`kinematics.backtest`; E1, added 2026-10-29, from the economics survey's §1.4 and §6.4). A
band states an error at every point, as a bank's value-at-risk model states a quantile of tomorrow's loss, and it can be
checked the way a supervisor checks the bank's, with no truth to hand. Its one-step innovations -- each coordinate's
GLS residual whitened by the Cholesky factor of its fitted covariance, in time order (`kriging.Model.innovations`; the
prediction-error decomposition, Harvey 1989): each point's error predicting it from the points before it, over that
prediction's own sd -- are independent N(0, 1) where the band's model is the track's (on a long track, each point's
from the window that reads it). On them: the share past ±1.96 against the 5 % stated (Kupiec 1995), whether a miss
follows a miss more often than a hit (Christoffersen 1998), whether a rhythm is left (Ljung & Box 1978, ten lags),
whether the jitter changes along the track (Engle's ARCH test, 1982, five lags), and the tails (Jarque & Bera 1987).
The light is the Basel Committee's (1996) for the count of misses, at 95 % where theirs is at 99 %: green while that
many misses or fewer would come 95 % of the time from a band that is right, yellow to 99.99 %, red past it (the band
is too narrow for the track); and yellow besides where any of the other four fails at p < 0.01 (each coordinate at
half of it) -- the band is then right on average along the track, not frame by frame. The reasons are said in words:
too narrow (or wider than it need be); its misses come together; a rhythm left in it, at the innovations' strongest
frequency (a wingbeat, a sway, the camera's shake), or something slow under 1 Hz (the camera's turn, or the object's
own); its jitter changes along the track; tails heavier than a normal's (those past four sds counted: jumps or slips
the band kept), or a shape that is not a normal's (lopsided, or with lighter tails). Under 30
points there is no backtest. The light and its reasons are the stage's "band backtest" line, the light is in the
summary's speed row and the speed CSV's header.

On drawn tracks with the band's own covariance (100 a row) the light is green 97 % of the time at 60 and 120 points
and 98 % at 300; 93 % on lines with white jitter (Ljung-Box's own false alarms). Tracks that break the model are
caught: heavy tails (Student's t with three degrees of freedom) are yellow 72 % of the time, a jitter that grows
threefold along the track 75 %, a beat in the position (0.8 px at 4 Hz) 100 %; jitter with a frame's memory (AR(1) at
0.6) only 20 % at 150 points, where the tests have little power against it. On the recorded tracks (44 with 30
points or more; every point, a long track's from the window that reads it) 7.0 % of the 27,894 one-step predictions
miss, where the survey found 4.87 % on the middle windows alone: PR088's object 2 misses 11.9 % over its 3,422 points
(a covariance fitted on two minutes' middle 15 seconds is too narrow at its ends) and the golden PR144 8.3 %, the
two red. Of the rest, 4 are green (PR141's two, PR144's case track, PR149) and 38 yellow: a rhythm or something slow
left on 56 of the 88 coordinates (Ljung-Box), the misses together on 17, the jitter changing on 35, the tails on 44 --
the band is right on average along most recorded tracks, and not frame by frame.

**A beat held as covariance** (`kriging.beat32`; M8, added 2026-10-29, from the pure-mathematics survey's §4.1). The
Matérn-3/2 cannot hold a wingbeat: it is a smooth wander with no preferred rate, so a beat goes partly into its
nugget and partly into a short wander, and what is left is a rhythm in the innovations. Where Ljung-Box finds one (at
f, the innovations' strongest frequency, at least three cycles of it in the fitted stretch) the band is fitted again
with a beat beside the wander: the Matérn-3/2 times cos 2πfτ, a covariance by Schur's product theorem (the product of
two covariances is one) whose spectrum is the Matérn's moved to ±f (Bochner) -- the quasi-periodic kernel astronomy
fits to a star's rotation. Its sill, envelope and rate are fitted by REML with the wander's three, each coordinate
apart, the rate within a quarter of f and the envelope at least two periods long (a shorter one is a broad bump in
the spectrum, not a beat), and kept on a coordinate where it gains 10 in log-likelihood; where what is then left is
the beat's first harmonic, that is held too, on the same envelope (a wingbeat's trace is no sine: Galileo flyer 5's
light curve beat at 3.9 and 7.8 Hz). The beat is noise to the band's rate: the rate, the average velocity and its
change are the wander's, kriged with the beat in the covariance of the data but not in the cross-covariance with the
wander, and the evidence that the velocity changes (`dlnl`) is still the wander's alone. The band keeps the beat only
where its backtest is the better for it -- less left in the innovations (Ljung-Box's least p higher) and missing no
more often (its Basel zone no worse) -- and the backtest's line says what was tried either way. On drawn tracks with a
beat of 0.8 px at 4 Hz in the position (40 draws) the band alone was yellow every time, a rhythm near 4 Hz its
reason; with the beat held it is green 37 times, and at 8 Hz over 300 points 40 of 40. On jitter with a frame's
memory (AR(1) at 0.6, 60 draws) a beat is held three times, near 5 Hz: a spectrum that falls with frequency can lend
a broad beat its gain, which the two-period envelope makes rarer; it changes nothing of the rate. On the recorded
tracks a beat is tried on 22 and kept on 19, at 3.1 to 13 Hz: PR135's six at 7.2 to 8.0 Hz (the paper's flock, its
wingbeat), PR097's objects 1, 3, 4, 5, 7 and 8, PR099's 1 and 2, PR41, PR44, PR23, PR088's object 2 and Galileo flyer
3; Ljung-Box fails on 37 coordinates in place of 56. It turns one green (PR097's object 3) and none of the birds:
PR135's members' Ljung-Box p rise from 1e-27 to 1e-52 to 1e-2 to 1e-10, and what is left in five of them is slow, the
camera's turn at 44.5 s (the survey's common break, E2's, not a beat's); flyer 3's innovations are clean of it and it
is yellow for its tails. It is tried and left on flyer 1 (with it the band misses 7.3 % and is red, alone 7.0 %: a bird
that flaps and glides over 14 s, whose beat fitted in the middle window is not the beat at its ends), flyer 2 (even
with its first harmonic, more was left) and the golden PR144.

**"Constant" as an upper bound** (`kinematics.change_bound`; E12, added 2026-10-29, from the economics survey's §1.6).
Under BAND_DLNL the band says its speed is constant, which says that no change was seen, not that there was none: the
likelihood of a wander's variance piles up at exactly zero even where the wander is there (Shephard & Harvey 1990, the
pile-up problem), and the band's change of velocity then reads 0 ± nothing (the depth bound met it, §33: 0 ± 0.0006
px/s). Stock and Watson (1998) answered with an interval found by inverting the test. Here the alternative is the
plainest one a reader means by "its speed changed": a steady change over the stretch. A free quadratic in each
coordinate, its residual taken as white (as the band found it), reads that change along the mean direction, 2cT, with
an exact interval, and the interval's far end is the largest steady change of speed the band could have missed: "a
steady change of its speed of more than X px/s over the T s would have shown (95 %)", in the band's line, the
summary's speed row and the bottom line; the window's card says it as "steady: changed by at most N px/frame"
(Jacob's words, 2026-10-30). Where the band sees a wander but its change of velocity over the stretch is
within BAND_Z (3) of its sigmas, the bound is the larger of its own change's far end along the track and the
quadratic's: "its speed along the track changed by less than X px/s over the T s (95 %)". Where the change is seen
there is no bound to give. Held to (drawn lines, 60 a row, half a pixel of jitter): with a steady change too small to
show -- 0.8 and 1.6 px/s over 4 s, 2 and 4 over 2 s, 0.5 over 10 s -- the band says constant on 59, 28, 60, 43 and 8
of the 60, and its bound holds the change on 58 of 59, 27 of 28, 58 of 60, 41 of 43 and 7 of 8; with no change at all
the bound is 0.8 px/s over 4 s at 120 points and 2.2 over 2 s at 60. Where the band saw a wander and no change, its
own bound alone held a steady change 88-90 % of the time (a covariance reads a steady change as a wander, its rate at
the ends drawn toward the line's), and the larger of the two 196 times in 197. The bound is of a steady change: a
wander too small to see (0.2 px over a second) moves the speed at the two ends by more than it on 4 of 56 constant
tracks, and a small wander under a steady change makes the quadratic's white error optimistic (it held 22 of 26). No
recorded track's band says constant; on 11 the change over the stretch is within its noise and is now bounded (PR088's
object 1, PR097's objects 1-3, PR099's 1, PR141's 2, PR071, PR23, FLIR1's exit and fields, Svanström V030).

**What the report does with it.** The line's rate v_px and its `uniform` flag are unchanged (the Technical Note's
quantity, and PR142's lesson). Beside them the band: on a uniform track the row's rate carries the average's error
and the band's range along the track; on one that is not uniform the bottom line says the speed changed, from how
much to how much, its average over the stretch and the velocity's change, and the speeds derived from the line's
rate are marked an average over a changing speed rather than unquotable. The rate frame by frame goes to
`<tag>_speed.csv` and its figure (the rate with ±1 and ±2 sd, each pair of frames' own reading as a dot, the average
dashed) to `<tag>_speed.png`, among the report's figures. A track with fewer than ten points once repeats are gone
has no band: NO POWER, the line's rate standing.

**Held to (K8: `kinematics.simulate_track`, `kriging.simulate`; `tests/test_reduction.py`).** Tracks drawn from the
covariance -- the correlated part and its rate drawn together from their joint covariance, the nugget added, a
velocity and an acceleration put on top -- are the validation set, the unconditional simulation of geostatistics
(Journel 1974). On sixteen such tracks the ±2 sd band holds the drawn rate 94 % of the time and the average speed's
z-scores have unit spread; on sixteen lines with jitter and no wander the velocity is constant within its band every
time and never said to have changed; a planted 200 px/s² is seen every time at three sigma or more and read near
its value. On the vendored recorded tracks the nugget comes out near the survey's (PR055 0.46 px with three glitches out,
PR144 0.51, PR23 0.65, the balloon 0.46, PR071 0.40 with its swing kept) and the band is tighter than the scatter of single
pairs of frames by the survey's ratios (2.5-9 times). PR43's streak (`tests/test_golden.py`), which the Note reads as a rate rising from about 7 to 33
px/frame, comes out 12 to 31 px/frame along the track with the velocity's change at 3 sigma over 0.8 s: described,
where `fit_v_px` could only refuse. Galileo flyer 5's paper track holds to 0.08 px and speeds up from 104 to 174
px/s along it.

**What it does not do.** The band is conditional on the covariance model: a bird that turns is smooth in one
stretch and not in the next, and the moving windows are the only concession to that (survey §4). An image-plane
rate is still an image-plane rate: the reduction's refusals (§5) stand, and a speed in the image that changed is
not an acceleration of the object until the camera's motion (§20) and the range are known. Acceleration as a
function of time wants a twice-differentiable covariance (Matérn-5/2) and is not read; the mean acceleration over
the stretch is.

## 33. What survives the missing variables (objective 3, added 2026-10-28)

**What it answers.** With no range, no field of view and no platform speed, what does a track still say? The Technical
Note's four unknowns enter the observables as multiplicative scale factors -- the field of view turns pixels into
angles, the range turns angles into metres -- so ratios of image quantities with equal powers of each cancel them
exactly. What is left is the part of kinematics that survives the missing calibration (the kinematic notes of
2026-08-05/06 in the research repository, parked then as a paper figure, right here as a report fact). Four things,
each from the kinematics stage's fields, in the summary's rows and in a paragraph of the bottom line that begins
"Without a range, a field of view or the platform's speed, the track itself says this."

**The projective constant-velocity test** (`projective.fit`). For a pinhole camera an object moving in a straight
line at constant velocity draws a straight line in the picture, and its distance from that line's vanishing point
goes as 1/(t_z - t), t_z the instant it crosses the camera's plane (with X(t) = X0 + V t and Z0 + Vz t = -Vz (t_z - t),
the image point less the vanishing point is a fixed vector over (t_z - t)) -- at any range, any field of view, any
speed. Both halves are falsifiable on the track alone. The model has five parameters: the line (two), the vanishing
point on it, a scale and t_z. It is fitted by least squares from a grid in t_z either side of the track (twenty track
lengths out at most), and held against two others: constant image speed (four parameters: motion across the line of
sight at a fixed range) and a free quadratic in each coordinate (six: no physics). Compared only with one another
the three say which is least wrong, not whether any is right, so the one chosen is then **held to the track's own
jitter** (added 2026-10-29, the pure-mathematics survey's M1). The jitter is read twice, as the nugget of the speed
band's covariance (section 32: a line, a Matérn wander and a nugget, REML) fitted to the track and fitted to the
chosen model's residual, and the larger taken; sqrt(sx² + sy²), each at least 0.1 px (a drawn or interpolated track
has none), is then the rms a point is off by the centroid's noise alone, and the model fits only with its rms within
NUGGETS = 4 times it. The verdict:

- *passes, closing or receding*: the model's rms is within a quarter of the quadratic's (it describes the track as
  well with one parameter fewer), under 0.8 of constant speed's, and within four times the track's jitter. Then t_z
  has an error from the track's own covariance (below; its band, 16-84 %, is t_z within one of it), T = t_z - t_last
  is the time to go, and the speed at the last frame is R / T for
  a range R there: the vanishing point's and the object's angles off boresight enter as a ratio of secants that is
  within a few per cent of one for any field under about 50°, and exactly known with k. With k the angle between the
  object's ray at its last frame and the vanishing point's is the aspect angle under the hypothesis (the notes'
  identity Π_θ = tan ψ). PR43 passes: straight to 1.5 px rms, t_z 3.38 ± 0.48 s on its case file's 25-point
  track, T = 0.91 s (0.72-1.10 at 95 %), the vanishing point at (483, 488) inside the frame, ψ = 35° at a 65.6°
  field, at its jitter (1.0 times it: the streak's centroid is noisy, 8 px) -- the research
  repository's note found 3.34 s, 0.80 s, (573, 545) and 33.8° on its own 18 detections.
- *passes, no closing seen*: constant image speed fits as well, or t_z is beyond twenty track lengths, and to within
  four times the jitter: a straight track at constant velocity whose range hardly changed -- and how fast it could
  have changed is bounded (below).
- *describes its trend*: the models pass it against one another, but the one chosen misses the track by more than
  four times its jitter: the track's trend is a straight flight at a steady speed (closing, receding or across), and
  the rest is something else's -- the camera's motion, or the object's own. No t_z, T, speed over range or aspect is
  given; the summary's row is "describes its trend to N px" (the window's card: "roughly, to within N pixels",
  Jacob's words, 2026-10-29). Of the 25 recorded
  tracks the models passed (the 14 case files' objects and the golden tracks), 24 are here, 4.6 to 234 times their
  jitter: PR077's object, which loops through 705° in ten seconds and had passed "no closing seen"; PR135's members 5
  and 6, which carry the camera's slew and had passed "receding"; PR051's release, PR071, the FLIR1 tracks, the Galileo
  flyer 3, PR097's four, PR23, PR149 and the Svanström clips. Even a free quadratic misses most of them by as much: their
  wander is the camera's, or the object's, on scales from half a second up (PR071 18 px at a range of 0.6 s, PR23 5-7
  px at 0.3-0.7 s). PR43 alone fits; the nearest of the rest is FLIR1's exit, 4.6 times its jitter.
- *fails*: neither describes it as the quadratic does -- not a straight line at constant velocity, or the camera
  moved (a pan keeps straight lines straight; a camera that translates does not).

Why the larger of two readings, and why four: the check's own false alarms on drawn pinhole tracks at constant
velocity (2026-10-29; 400 draws a case, 15-60 points, an object closing on the camera half a second after its last
frame and one far off whose range hardly changes, the jitter half a pixel, white or AR(1) with a frame's memory or
more, φ 0.3, 0.6, 0.9). Each reading alone reads the jitter low somewhere. The band's own fit of the track chases a
steep trend with a short wander, and its nugget takes a share of it: on the closing object over 60 points, 80 % of
the tracks with φ 0.6 were past three jitters (40 % past four). The fit to the model's residual reads low on a short
track whose jitter has memory: 12-14 % past three at φ 0.6. The larger of the two holds every case to 5 % past four
(the closing object over 60 points at φ 0.6 and 0.9: 5.0 and 4.0 %, at three 12 and 52 %; the far one over 15 points
at φ 0.6: 3.0 %), at most 1 % past five, and none at all with white jitter. The far object's 30- and 60-point cases
were cut by the jobs' time limit. That errs toward "describes its trend", which withholds a time to the camera's plane
and claims nothing; the recorded tracks sit far from the line either way (PR43 at 1.0, the rest from 4.6 up). Jitter
with a third of a second's memory is a wander at the scale of a short track, and the check cannot tell them apart.
The honest form would count a wander shorter than the track as noise: a GLS fit of the projective curve under the
band's covariance with its range held short of the track's span (the survey's §1.1), not built.

**t_z's error, where the track fits** (`projective.tz_err`; added 2026-10-30, the survey's M5, its other half; the
covariance as it stands 2026-10-31). The fit along the line, s(t) = s_vp + a / (t_z - t), is least squares. Its error is
the track's own covariance carried through it by the sandwich (J'J)⁻¹ J'ΣJ (J'J)⁻¹, J the fit's derivatives in (s_vp, a,
t_z). With white residuals that is plain least squares' error; where the residual has memory -- a centroid that drifts
for a few frames -- it widens, as the residual bootstrap it replaced did not (it resampled the points as if each were
drawn alone). The band given is t_z within one error either side (16-84 %), centred on the fit's t_z; T's, and the speed
over range's, follow from it.

Σ is the nugget, a short wander of free range under a tenth of the stretch, and a long wander held at the stretch's own
length, their sizes by REML with J as the mean, on every k-th point to 150 (`two_ranges`). Each part answers something
measured. Its first form (a line, one wander of free range and a nugget, fitted on the middle 450 points) was fair on
drawn tracks, and on the real ones it failed by 20 to 85 errors. Fifteen airliners' approaches of known range (ADS-B,
truth Z / -Zdot at the stretch's last frame, seven stretches each; those that close and fit are 54) show why:

| error | truth within 1 / 1.96 / 3 errors | median errors off | median error / T |
|---|---|---|---|
| the first form | 4 / 6 / 15 % | 14.2 | 0.006 |
| one wander of free range, over the whole stretch | 28 / 48 / 56 % | 2.4 | 0.038 |
| the same, the fit's 2-D sandwich | 29 / 45 / 53 % (12 approaches) | 2.8 | 0.050 |
| the same under GLS | 13 / 24 / 39 % (12 approaches) | 4.5 | 0.029 |
| long wander held at the stretch, no short one | 61 / 80 / 89 % | 0.89 | 0.099 |
| both, the short under L / 6, **L / 10**, L / 20 | 39 / 65 / 80, **43 / 67 / 80**, 44 / 69 / 83 % | 1.28, **1.21**, 1.09 | 0.081, 0.081, 0.082 |

At 60 fps the middle 450 points are 7.5 s of a 20-s stretch: a long wander is a line there, and the error came out 5 to 100 times
small. Read over the whole stretch it still misses, because REML's free range flips between a short and a long reading on
like stretches (0.08 s or 5 s), and because the mean must be the model's own columns: the fit has already taken their share of
the wander out of the residual. A long wander alone holds most of the truth because it counts short memory
as long, and that is its cost on drawn tracks: 3.7 times too wide at 30 points and φ 0.6, 27 times at Yemen's geometry and φ 0.9. A
short range of its own mends that. GLS moves T by under 0.01 s and holds no more of the truth, and with the range held the
2-D sandwich and the 1-D agree (57 / 83 / 93 % against 61 / 80 / 89 %), so the cheaper 1-D stays. On drawn tracks whose t_z is known (100
draws a case, 15 to 60 points at half a pixel, PR43's own fitted model at its 8-px jitter, and 1200 and 460 points at an
airliner's and at Yemen's geometry at 0.15 px; the truth within ±1 / ±1.96 errors):

| case | the first form | now | now, median error over the true scatter |
|---|---|---|---|
| closing, 30 points, T 1.5 s, white / φ 0.6 / φ 0.9 | 78 / 98, 60 / 91, 37 / 72 % | 85 / 98, 71 / 94, 64 / 83 % | 1.29, 1.15, 0.85 |
| 15 points, T 2.0 s, white / φ 0.6 / φ 0.9 | 74 / 92, 50 / 72, 56 / 79 % | 78 / 94, 65 / 82, 70 / 84 % | 1.12, 0.82, 0.85 |
| 60 points, T 1.8 s, white / φ 0.6 / φ 0.9 | 71 / 97, 56 / 86, 48 / 70 % | 78 / 98, 73 / 91, 69 / 85 % | 1.12, 0.95, 1.08 |
| 60 points, T 3.0 s, white / φ 0.6 / φ 0.9 | 72 / 98, 63 / 94, 40 / 76 % | 81 / 98, 83 / 99, 63 / 87 % | 1.34, 1.40, 0.88 |
| receding, 30 points, white / φ 0.6 / φ 0.9 | 71 / 97, 59 / 88, 45 / 77 % | 80 / 97, 79 / 93, 59 / 84 % | 1.25, 1.02, 0.97 |
| PR43's model, white / φ 0.3 / φ 0.6 | 69 / 97, 60 / 88, 56 / 89 % | 75 / 97, 68 / 91, 67 / 94 % | 1.22, 0.98, 0.85 |
| 1200 points, T 24 s, white / φ 0.9 | 75 / 98, 58 / 83 % | 83 / 100, 78 / 97 % | 0.91, 0.57 |
| 460 points, T 90 s, white / φ 0.9 | 69 / 96, 49 / 87 % | 76 / 98, 70 / 94 % | 1.09, 1.09 |

(The bootstrap before the first form held 39 / 70 % at 30 points and φ 0.6.)

**What the band does not hold.** On the real approaches it is still about twice too narrow, and no residual can show why: T
far beyond the track rests on the picture's acceleration, T = 2 v / (dv/dt), so whatever else bends the speed in the
picture is taken up by the three numbers and leaves nothing behind. A steady change of the object's own speed by a share ε a
second moves T by ε T² / 2 (drawn: 0.87 s at T 24 for 0.875, 0.21 at T 12 for 0.22, 13.5 at T 90 for 12.2), and with white
jitter the band stays about a sixteenth of that; a lens's barrel and a camera's slow pan do the same. An airliner on
approach slows by 0.2-0.6 % a second; the test's T off the noise-free truth pixel of one of them, over two thirds of its approach,
is 21 % long, with a residual of 0.38 px at a measured 0.41. So the band is the track's own scatter, if its speed held,
and the sentence says the rest as a number: "(16-84 % a to b s), which a speed changing by 1 % a second of its own would
move by X s". On those stretches T itself was within 10 % of the truth (median; 31 % at the 84th percentile).

The depth bound's own route was tried first and is no error for t_z: the band's change of velocity along the track
through v_end / v_start = ((T + L) / T)² gave intervals six times too wide (they held the truth every time at one
sigma), because the band's end rates are its wander's, free of the model, and centred on the band's change rather
than the fit's they ran long (PR43: 2.2 s for the fit's 0.91; at one sigma they held the truth 28-57 % of the time).
The Yemen line of sight, whose bootstrap band of 75.9-87.2 s missed the laser's 92.6, is 80.7 ± 55 s: it holds it, and says
T is five times the track. PR43: T = 0.91 ± 0.48 s (16-84 % 0.43-1.39; the first form 0.81-1.01). Nearly all of that is its
last point: without frame 75, which agent dive43 found to be false, T = 0.76 ± 0.04 s.

**How fast its depth could have changed, where no time is given** (`projective.depth_read`; added 2026-10-29, the
survey's M5). Under the projective model the speed along the line goes as a / (t_z - t)², so over a stretch of length
L ending at the last frame the two ends' speeds are a / (T + L)² and a / T², T = t_z - t_last, and the mean speed, the
chord over its length, is a / (T (T + L)): exactly their geometric mean. With r = (T + L) / T the ends are v̄ / r and v̄ r,
so r - 1/r = Δv / v̄, every change of speed has its r, and 1/|T| = |r - 1| / L = |Ż/Z| there: how fast the depth changed,
as a share of itself a second. The speed band's change of velocity along the track (the kriged rate at the stretch's
two ends, its error the track's own covariance's taken along the track, so a wandering track widens it), within ±1.96
of its sigmas, bounds |T| from below on both sides: "if it flew straight at a steady speed, its depth changed by less
than X % a second ... it was at least T₁ s from the camera's plane if closing and T₂ s if receding", in place of "the
track says nothing of how its range changed" -- Ṙ/R, the first thing bearings-only analysis says is observable (Nardone
& Aidala 1981), bounded instead of missing. The error is floored by a free quadratic's along the line (its curvature's
error with its residual taken as white): where the band's REML fits the wander to nothing, the latent path's velocity
cannot change, and the band read a drawn object's change as 0 ± 0.0006 px/s and the bound as fifty times too tight
(it missed the truth 6 times in 40; with the floor, none).

*The bound until 2026-10-30* split the mean arithmetically, v̄ ∓ Δv / 2, and gave nothing past Δv = 2 v̄, which a closing
object passes. The exact form above was the obvious repair, and it failed: on 26,353 drawn tracks it held the truth
86 % of the time at r 1.5, 61 % at 2.4, 27 % at 3.6 and 2 % at 6, at a nominal 95 %. The band's change runs short of a steep
curve, as a smoothed rate does at the end of its data (0.92 of the truth at r 1.2-1.5, 0.84 at 3.6, 0.72 at 6, with an
error of 4-9 %), and the arithmetic split had hidden that by overshooting. So a tenth of the change joins its error
(DEPTH_SHARE), and three things give none, with the reason in the report: *past four times the mean speed* (DEPTH_X; at r
6 the bound held the truth one time in two); *ends that are no straight flight's* (DEPTH_G: the model has their
geometric mean equal to the mean speed, and 99 % of drawn flights lie within 1.75 times it at each r from 0.4 to 3.6; a track looping
over a short chord does not, PR077's object 1 reading 28 times it); and, on a closing trend, *a change of speed that trend
does not draw*: the bound is of that trend, so the change its t_z gives must lie inside the band's. Constant image
speed is held to no such change, since a change it cannot see is what the bound is for. As built, on 4,320 drawn tracks of
1 to 6.8 s, white and with memory, the bound was given on 91-99 % of them from r 0.4 to 3.6 and held the truth 95-99.7 % of
those times, at a nominal 95 %; at r 0.2, 6 and 10 none is given. The four drawn approaches and retreats of 2026-10-29, |Ż/Z| from
0.0004 to 0.02 a second, 40 draws each, went from 40, 40, 38 and 36 held to 40, 40, 39 and 38.

The last gate came from fifteen airliners closing on a camera, of known range: with the first two gates alone ten of their
whole tracks kept a bound and seven missed the truth, by up to fifty times, the link hopping on their grown images and
the band's ends reading the change anywhere from -3.1 to +5.2 times the mean, while the fit's own T stayed within 22 % of
the truth. With it three bounds stay on the whole tracks, 9.1-10.2 % a second against 9.0-9.3, and four on their first two
thirds, 5.6-6.8 against 4.2-4.8; every one holds. A crossing aircraft read as constant image speed still misses, 0.06
against 0.27 on its first two thirds, as it did before these changes; on another crossing the same miss closed with
the lens's bend taken out of the track.

Given where the model is chosen and no time is given: on a track that fits ("passes, no closing seen") the bound is a
fact under the hypothesis, the ledger's θ row is bounded with k (tan θ = ω R / |Ṙ| > ω / b: at least atan(ω / b)) and the
admissible region a wedge, |Ṙ| <= b R; on a track that describes its trend it is said as a condition of the trend ("if
its trend is a straight flight at a steady speed ..."), and nothing else uses it. PR23's object: under 1.5 % a second over
its 6.8 s (−1 ± 24 px/s on 248), at least 68 s from the camera's plane closing and 73 receding; PR149's contact: under
0.62 % over 2.7 s (−7 ± 7 on 607), at least 456 s closing and 162 receding -- both tracks describe their trend (6.8 and
6.4 times their jitter), so both bounds are conditions. PR149's was 4.6 % (−72 ± 45) until its two glitches were named
and left out of its band (§32, *Jumps named*, 2026-10-29): the band had chased them with a wander a tenth of a second
long, and its change of speed with it. The survey's own table had 1.0 and 4.5 %, the change's error taken along the
change rather than along the track.

**The turn radius in body widths** (`projective.turn`). The track's sagitta s across its principal line (a
quadratic across the line over its length L, the sagitta of that arc) against its length and the object's width D
across its travel: Π_L = 8 D s / L², and r_turn / D = 1 / Π_L. A straight 3-D line at constant velocity projects to
a straight image line at any range, so image curvature is not inertial by construction, and the number survives
every missing calibration. The width is the size given, else the blur's measured width at half peak, else the spot
size the track was followed at; a streak's length would overstate it. Three verdicts: *did not turn* (the sagitta
within three of its sigmas of zero: the radius is at least L² / (8 D s_95), s_95 the sagitta's 95 % upper); *a hair
off straight* (a bend three sigmas from zero but Π_L under 0.01, a radius over 100 body widths: as easily the
camera's or the lens's as the object's); *a turn* (Π_L of 0.01 or more). The scale it is read on, from v² / (a D): a
quadcopter at 2 g turns in 15 body widths, a pigeon's 2-g turn 33, an airliner at 1.5 g 60, a fighter at 9 g about
47-121. PR43's case track bends 4.0 ± 0.4 px over 505 px: about 1,900 body widths, a hair off straight; the note's
18 detections gave > 1,936 and PR113's four > 377. Neither manoeuvred, with no range, field of view or platform
speed.

*The tilt* (added 2026-10-30, the survey's M4 and §6.5). The radius the sagitta reads is the picture's. A circle of
radius r whose plane is tilted by i draws an ellipse, and the picture's radius of curvature at the circle's phase φ is
r (sin²φ + cos²i cos²φ)^1.5 / |cos i| -- anywhere from r cos²i to r / |cos i|: a turn whose plane holds the line of
sight looks straight. With the plane's normal isotropic and the phase uniform the picture's radius is 0.15 to 8.5
times the turn's own (5-95 %, median 1.02; a 4000 x 4000 grid, recomputed by test_reduction), so the words say the
number with its band: "a turn radius of about N body widths ... -- that radius is the picture's: with its plane at
random to the line of sight, the turn's own radius is 0.12 N to 6.6 N body widths nine times in ten". The picture shows a turn ten times
straighter than it is for 4.2 % of the ways its plane can lie and forty times for 1.1 %, so "did not turn" says so:
"... unless its plane held the line of sight, which draws a turn straight: one 10 times tighter looks this straight
for 4 % of the ways its plane can lie, 40 times tighter for 1 %". PR43's "at least 1,900 widths" survives it: a 9-g
fighter's turn (47 widths) would look forty times straighter for about 1 % of orientations.

*Past 150°, the turn read whole* (`projective.ellipse`; added 2026-10-30, the survey's M4). A body going round a
circle at a steady rate ω, seen by an affine camera at any range, field of view and tilt, draws x(t) = c + u t +
a cos ωt + b sin ωt, the affine image of uniform circular motion (u lets the circle drift with the air: a thermalling
bird draws a trochoid). Two classical facts make it a measurement with no calibration: the image of a circle under a
parallel projection is an ellipse whose semi-major axis is the circle's radius unforeshortened (the diameter parallel
to the picture keeps its length), its minor over its major |cos i| (the elementary half of Pohlke's theorem; the axes
are the singular values of [a b], Rytz's construction done by linear algebra); and ω is the same in every view. So
r / D, the tilt, ω, the speed ω r / D in body widths a second and the acceleration toward the centre ω² r / D in body
widths a second² come with no range, no field of view and -- unlike every other speed in the toolkit -- no
foreshortening. Given ω the model is linear, so ω is a scan (600 rates from an eighth of a turn over the track to
three turns a second, or 0.8 of the frame rate's Nyquist, refined by golden section). The sagitta is a formula for a
small bend: on the survey's drawn turns of 25 body widths it read 12 over 286° untilted, 2,500 at 70° of tilt, and
6,500-58,000 over a whole circle, where the ellipse reads 25.0 at every tilt with cos i to two decimals. Under about
45° the ellipse is not identified (a short arc does not fix a circle), and at 90° it is unbiased but wide (19-46
widths, 16-84 %). So `turn` reads the ellipse only past ARC_DEG = 150° -- the phase it sweeps and the fitted path's
own heading both that far (a circle drifting faster than it goes round draws a wave, not a loop, and its heading never
swings so far; a flat ellipse's heading flips at its ends however little of it is swept, and on the recorded tracks
the phase alone kept out four such readings of 600-2,000 widths) -- and only where it describes the track LOOP_GAIN =
0.8 better than a free quadratic does and passes the two tests of *the ellipse against the track's own wander*, below;
otherwise the sagitta with its tilt's band. The words: "the track loops: an ellipse A by B px,
drifting U px/s, goes round at ω rad/s (N° in T s), E px rms against a free quadratic's Q: a turn of radius r ± e
body widths, its plane i° from facing the camera, at V body widths a second and A a second² toward its centre -- read
whole, so with no range, field of view or foreshortening: a circle's image keeps its radius at any tilt; a turn, or
the camera's own motion while it followed the object". The card's row says "it loops, radius N widths" (Jacob's
words, 2026-10-30; a turn read by its sagitta stays "its path bends, radius N widths"). The ellipse is not held to the track's own jitter, as the projective test now is (above): on a camera that
slews in loops it reads the loop the slew drew.

*The ellipse against the track's own wander* (`projective.against_wander`; added 2026-10-31, Jacob's "revisit" of the
judgement above). The first gates were 150°, a rms 0.8 of a free quadratic's and a minor axis 3 white errors from
nothing. Held to a null they do not hold. Drawn tracks with no turn in them (100 draws a case, 15-900 points at half a
pixel of jitter, turned at random): straight lines, curves and sways along a line are read as loops at most 4 % of the
time, as they were built to be; but a Matérn wander in two coordinates at up to a quarter of the track's length 67 %
at worst (32 % of 1680 cases over 5 %), and a camera's pans 47 %. Every recorded track wanders. No threshold on those
three numbers mends it: a rms gate that holds wander to 4 % (0.2) passes no recorded track, and 720° of arc leaves 22 %.
Each recorded track drawn again from its own covariance, no loop in it, passes those gates up to half the time (PR088
object 1 50.5 %, PR085 45.5 %, PR41 43.5 %, PR099 object 3 30.5 %). So the track is asked directly. For x
and y each, by `kriging.fit` on every k-th point to LOOP_NMAX = 150: a line and a wander, against a line, a wander and
the ellipse at the rate the scan found, and LR, -2 log their likelihood ratio, added over x and y. The wander takes up
what is wander in both, which is why one threshold does for any size and range of it. And the minor axis is held to
its error under the covariance that leaves, not a white one: a sway along one line with a wander on it passed the white
gate 52 % of the time, 85 % at worst. **LOOP_LR = 40, LOOP_MINOR = 3**, from a null of 36 wanders (ranges half the track
to twice it, the nearest the limit, 1000 draws each) and 48 sways with a wander on them (200 draws each): the worst
wander is then read as a loop 5.1 % of the time and the worst sway 6.0 %, against M1's 5 %; on the wider second null
(226 cases, 100 draws each) lines and pans 0, sways along a line at most 1 %, and of 160 wanders three over 5 %, the
worst 7 %, which is what 100 draws of a 5 % rate give. Neither test does it alone: LR 40 by itself leaves wander 10.8 %
and passes 90 % of the sways with a wander on them. LOOP_GAIN no longer carries any rate: 0.5 or 0.8 change nothing beside
LR, and it stays only to spare the fit on the many tracks an ellipse does not describe. Two rates at once, one in each
coordinate, are real motion rather than wander, and over a cycle or so they do go round (ratio 1.3: 70-83 % read as loops
up to two cycles; 1.6: 74 and 38 % up to one; from 2.1 almost none, and none past two cycles at 1.6): that is the sentence's
"or the camera's own motion".

True turns (20 draws a case, 120 and 300 points, tilts 0-70°) are read at least 90 % of the time past 210° with wander up
to 5 % of r, and past 360° at 15 %; the radius is then within 20 % nineteen times in twenty past 150° at a jitter of r /
300, 240° at r / 30, 300° at 5 % wander and 360° at 15 %. So 150° stays the floor, from the drawn arcs' own accuracy
at their cleanest (135°: nine in ten), and the error says the rest: it is now the covariance's, the turn rate let go
as well (nine numbers, x and y sharing it). The white error at a fixed rate held the truth within one of it 4-29 % of
the time on those turns; this one 81 % with no wander, 50 % with (2 errors: 98 and 78 %). Flyer 4's 27.4 widths, ±0.4
before, is ±15: 156° of arc does not fix a circle whatever the jitter. The GLS axes are no better than the plain ones, so
the value stays the plain fit's.

Where the ellipse describes the track and is refused, the track swings about more than a bend does and no loop can be
claimed. The sagitta's numbers stand, and `turn` keeps the ellipse as `swings`, so the words go on: "; it swings about
more than a bend does (an ellipse A by B px at ω rad/s follows it, N° in T s, E px rms), but no loop is claimed: its own
wander draws an ellipse as good too often to claim one, and it cannot be told from going back and forth along a line,
which a turn seen edge-on, a sway and a camera's swing draw alike" (the half that applies); the card says "it swings
about, N widths either side".

On the recorded tracks (at the 9-px spot) two are loops: **PR097 object 3** (LR 45.9, minor axis 3.15 errors, 2.07 ±
0.30 widths at 1.7 rad/s) and **Galileo flyer 4** (53.2, 3.85, 27 ± 15 widths, the one still camera). Past the gain but
not the minor axis: PR097's objects 1, 2 and 4 (40.8-44.6; 2.998, 2.1 and 2.9 errors, the same swing of the camera as object
3's, the threshold passing through them). Under the gain, swinging about: PR077 object 1 (39.1, and 0.66 errors: its 212 x
23 px ellipse is a back and forth), PR41 (34.9), PR135 objects 4 and 1 (26.4, 21.8), PR088 object 1 (21.5), PR085 (-2.5),
PR099 object 3 (-13), and FLIR1's exit (30.2) and Svanström V030 (11.0). PR43 stays a hair off straight.

**The smear number** (`projective.smear`): the displacement in one frame over the object's width. A property of the
observation, not the object: above 1 the object streaks within one frame; above 2 an interlaced source's two fields
separate and masquerade as two objects (PR113's retracted "formation"). PR43: 4.75 widths a frame.

**tau, and the aspect angle without a range** (`kinematics.looming_fit`, `tau_of`, `tau_from_light_curve`,
`aspect_from_tau`; `flicker.tau_reading`; I6). A resolved object's angular size grows as 1/(t_z - t) on a straight
approach, so tau = s / s_dot = t_z - t (Lee 1976: the quantity animals brake on), with no range and no field of view --
the projective test's own law. An unresolved source's flux goes as 1 / R², so d ln F / dt = -2 Rdot / R = 2 / tau once
the gain is out. Either gives Rdot / R, the first thing a bearings-only track can observe (Nardone & Aidala 1981), and
with omega the aspect angle: tan theta = omega R / |Rdot| = omega |tau|, R cancelling -- an instant's identity, so
omega is the rate at the same frame as tau (the speed band's at the last frame over k: on a thing closing on the camera
its rate grows, and the track's average put a drawn approach at 2° for 6°).

*From a stage* (2026-10-29). The flicker stage, which reads every frame along the track already, reads with its
brightness the object's size (`flicker.extent`, on every frame up to EACH_MAX 300, evenly spread beyond) and its
ring's median level (`flicker.level`, the scene beside it, which a camera's gain multiplies as it does the object),
writes them to `<tag>_flicker.csv` as "object size" and "object level", and gives them to `kinematics.tau_of`, whose
answer is the stage's field `tau` (one a track; a group's member carries its own into its case) and its result line.
The size route is the measurement, and its rules came from the drawn series and the recorded controls below:

- the size is a radius read in whole pixels with the blur's reach on top -- a disc of radius r with a 1.2-px edge reads
  r + 2.6 -- so the law fitted is s = a / (t_z - t) + c, c between 0 and the least size (without c a disc closing at
  2.0 s fitted 3.3); t_z on the grid either side of the track, refined between its neighbours, its band a residual
  bootstrap (16-84 %);
- the object resolved (a median radius of TAU_MIN_PX 4 px: a point reads 2-3, its blur's), its size read on at least
  TAU_COVER 0.6 of the frames it was tried on, sizes TAU_ODD 3 MADs (and 1.5 px) off their running median dropped as
  slips (the far ring reaching a neighbour reads 30-80 px on a 5-px bird);
- a trend in ln size TAU_Z 4 of its sigmas from none, the sigma widened for the sizes' own wander (n_eff from their
  lag-1 correlation), a change of TAU_GROW 2 px or more over the stretch, the law describing it as well as a free
  quadratic (QUAD_SLACK), t_z inside FAR track lengths, and tau's error at most TAU_REL 0.3 of it.

Drawn series (4 s at 30 frames a second, sizes rounded): a size closing at tau 2.0 s is found 40 of 40 times, median
1.97 s, its band about a quarter too narrow (pulls sd 1.25, 90 % within two of its errors); one closing at 6 or 16 s
grows under 2 px and is found never -- the size route reaches a thing that closes in about the track's own length or
less, and big enough to have a size. A size that wanders with no approach passes 1 in 100 with a 0.3-s memory, 2 in
100 with a 1-s memory (3 of the test's 40), and 8 in 100 when it drifts as slowly as the record is long: no rule on
the size alone tells that drift from an approach, which is why the case says the path's own crossing time beside it.
Rendered through the stage (`test_measurement`, a disc on a straight line through a pinhole under a gain): closing,
1.95 ± 0.13 s for 2.03, the aspect angle 6° for 6.1°; going away, -7.27 ± 0.19 s for -6.97; a size that holds, none.
**The recorded controls** -- the 31 objects of the 14 reference case files, none of them chosen as an approach: with
the first rules (z 3, no coverage or slip rule) 7 of 31 claimed a tau (PR097's four dots, sized on 20-50 of 126
frames between 7 and 55 px; PR149's contact; a bird of PR135's flock; PR44's bird at -22 s); with the rules above none
does: 10 are never sized (or on under ten frames), 9 are sized on too few of the frames they were tried on, and 12
hold -- PR44's bird among them, its shrink at 3.1 sigma.

Into the case: the summary's row "time to contact" (tau, closing or receding, at the last frame; else what stopped it),
the aspect angle from tau where k is known (the summary's theta row, the ledger's theta *constrained* -- tan theta =
omega tau is the Technical Note's equation (5) with R out, |Rdot| so an acute angle, the row saying which way), tau's
line through the admissible region, and the bottom line's sentence beside the projective test's T where both are
read: "its path, read alone, puts that at T s, which agrees" (or does not: the two cannot both be a straight line at a
steady speed). A resolved size that holds says no closing was seen and nothing of how far -- its blur's share of it is
not known, so no bound on tau is drawn from it. Where there is no tau the summary's row says why (a point; sized on
too few frames; a size that holds) -- not a NO POWER of the flicker stage, whose list is the beat's: most objects are
points, and every flicker stage and every report's count would carry it. The window's card says "Time to the camera:
in 2.0 s".

*The light curve, conditional.* For an unresolved object that does not beat: d ln F / dt with the ring's level's
taken out, read where the brightness changes by TAU_LIGHT 10 % or more at TAU_Z, as "its brightness would give tau = x s
at the track's middle if the change were its range's alone" -- recorded and said, never the route: a turn, a glint or
a flame changes a brightness too, the air's extinction is left out, and a video's levels compress a brightness change by
about its gamma (2.2), so tau from them is long by up to that. A resolved object outgrows its aperture and has none.
Held on a point under a gain (3.83 s for 4.02 at the middle). None of the 31 controls gives one at four sigma; PR43's
streak gave 1.0 s at three under the first rules (its middle, where its path's T puts about 1.3).

The validation on real objects -- Galileo aircraft whose ranges ADS-B gives -- waits for that data; the drift paper's
three clips stand in meanwhile (below).

*Held against real clips of known range* (2026-10-29; the drift paper's three videos, whose ranges their displays
give). **AARO's Puerto Rico lanterns** (`DOD_110692805`, IR 675): their path from 39 lines of sight (the uap case's
fit: 7.3 m/s toward 240 deg, sinking 0.6 m/s, 181 m over the field) against the aircraft's printed positions puts them
2130 m off at 54.5 s and 4474 m at 117 s, R / |Rdot| 65-115 s while the range opens. Over 1640-2231 (54.7-74.4 s, the
stretch the case's tracker held them; R 2131 -> 2567 m), `flicker --dark` on that track reads them resolved (a median
radius of 9.0 px) and their size shrinking at d ln s / dt = -0.0127 +- 0.0066 a second, against the range's -0.0103:
the right sign and size at 1.9 sigma, so "its size held ... no closing is seen in it" -- right, and as the drawn series
say, the size route reaches a thing that closes in about the track's own length, not one at 97 s on a 20-s track. The
light route is not tried on a resolved object; run on the stage's own curves by itself it fails here as the condition
says it may: with the ring's level out the brightness rises, d ln F / dt = +0.0054 +- 0.0080 against the range's
-0.0206 (3.3 of its sigmas off, the wrong sign; the gate claims nothing at 0.7 sigma), because the lanterns' own light
changed more than their range did (F R² over the level rose by 0.50 in ln over the 19 s) and the display's gain stepped
between thirds of the stretch. Without the level taken out the same curve reads tau = +85 s, closing -- a false
approach the level's control is there to stop. Golden check `test_puerto_rico_lanterns_tau_against_their_range`, on the
stage's curves (`tests/golden/puerto_rico_lantern_curves.csv`).

*Over the range's doubling* (2026-10-30; frames 1641-3530, 54.7-117.8 s, R 2131 -> 4474 m, one zoom state). The case's tracker
lets them go at 2211, and the reason given, that they fade, does not hold: **the lantern switches.** Followed by a link over
the frames' dark spots, with the ground's shift voted by the spots themselves (a phase correlation locks on the lantern in
a picture the camera follows) and checked by eye every 10 frames, by the case's track (522 frames, median 0.3 px) and by Find
(five of its proposals), it is as deep and as black at 101 s, 3.8 km, as at 73 s, 2.5 km. In a 12-px disc clear of the reticle's
ticks its brightness changes by over x2 within a third of a second on a fifth of the frames, and by over x4 within half a second
on 15 %, against at most 6 % from the range; black over 2798-3060, faint over 3069-3130, and from about 3270 to 3423, 5.1 s, nothing
can be seen, then it returns, black by 3476 at 4.4 km. Shift-and-stack over a grid of rates, which needs no position, reads 18-41 on it
in known blocks and at most 2.7 over 3270-3360 against a null of 1.3-1.9: if it is there, under about a tenth of its black state.
Those frames are left out, not read as a flux: the carry across them on the ground's shift misses by 16-87 px held out. Follow on
twelve marks links 632 of 1256 frames, 91 % of those within 20 px of this track, says where it fails to reach a mark, and draws
nothing across the dark stretch. The stage cuts the track where it is out of view for over half a second and measures the
longest piece, 1641-2597: "its size held", rightly, and no light, since the object is resolved. It said nothing false.

Off the stage, over the whole lever (`tau_of` on the tracked frames):

| reading | gives | the range's |
|---|---|---|
| the size route | receding, tau -113 +- 31 s, t_z 4.8 s; s = 10403 / R + 4.9 px | -111 s, t_z 6.9 s |
| the same, 60-s windows a second apart | -110, -195, -119, -137 s | -109 s |
| the light, the stage's 6-px disc | d ln F / dt -0.0136 +- 0.0034, tau -147 +- 36 s | -0.0259, -77 s |
| 12, 16, 22 px, all tracked frames | tau -90 +- 17, -73 +- 9, -62 +- 6 s | |
| 12, 16, 22 px, clear of the ticks | tau -84 +- 20, -62 +- 9, -53 +- 6 s | |
| the 90 % envelope in 4-s bins, 12, 16, 22 px | p = -1.24 +- 0.30, -1.65 +- 0.34, -1.82 +- 0.21 in F ~ R^p | -2 |
| the same less the noise off the lantern | -1.67 +- 0.45, -1.85 +- 0.66, -2.49 +- 0.90 | |
| the median | -1.35 +- 0.54, -2.18 +- 0.60, -3.01 +- 0.80 | |

Three things follow. The size route, which could not tell at x1.2, makes a true claim at x2.1, but on the whole lever only, and
its value is good to a factor of two, not to the 2 % of the first line. The light's sign is right over any long stretch and its
size is not: the aperture moves it x2.4, since the core is clipped at black and a small disc reads the blob and not its light,
and `_trend`'s error is too small for a curve that moves in steps, -53 +- 6 s missing by four of its sigmas. And the range and the
flame each hold on their own scale: the bright state follows the range, F R^2 at 22 px flat within 14 % in ln while the flux falls
x0.28 (off the lantern a disc that wide can read nearly as much in a bin, so -2 is allowed, not pinned down), while the
median falls faster, more of the time spent off, and each moment is the flame's. Run through sliding windows the light's gate
lets the switches through in short ones: of 420 windows of 3 or 5 s over four apertures, 44 claim and 16 of those say closing,
tau 2-9 s at 4-9 sigma, of a thing receding (+2.4 s at 4.9 sigma in the stage's own disc). In the 580 windows of 10-45 s none does,
but the claim's size is 0.13-0.27 of the truth at 10 s, 0.31-0.76 at 20 s and reaches about 1 only at 45 s. The reading says a flame
can do this, and is tried only on a point, so none of it reaches this clip's report; on a point it would be the sentence to
read. The size route in 177 windows of 10-60 s never says closing, and claims only from 30 s. Golden check
`test_puerto_rico_lanterns_over_the_doubling`, on the curves (`tests/golden/puerto_rico_lantern_curves_long.csv`).

**The Yemen clip's object** (the MQ-9's laser: the slant range 6843 -> 5917 m over frames 117-555, R / |Rdot| about
100 s; the relative motion a straight line at a steady 100.6 m/s). Its own track is held on the reticle, so the stage
reads no projective test and no depth bound from it -- rightly: its motion is the camera's. (Read against the reticle
it is one point to 0.01 px, and `fit_v_px` had called it "not uniform", having no noise to measure: the held test's
noise is now floored at a tenth of a pixel, `HELD_FLOOR_PX`.) The size route claims no looming, which is right too (the
size would grow 17 % in 16 s), but for a reason it should not have given: inside the tracker's gate the object's
profile never falls to a tenth of its height, and the extent ran out to its cap, 80 px, on most frames -- "its size
held, 80 px in radius" of a thing 22 x 10 px. A size at the cap is now no size (`TAU_CAP_PX`); the rest read 70-79 px,
the gate's, and the size "comes and goes" (121 of 235 frames over 336-596). Its brightness over the ring's level, run
by itself through the light route (the stage tries it only on a point), rises +0.063 +- 0.034 a second over 336-565
against the range's +0.020 (within its error, 1.8 sigma from none: no claim), and +0.092 +- 0.030 over 336-596, as the
missile comes into the ring (570-596): there it would say tau = 22 s against the laser's 102, and stops short of
claiming it only at 3.0 sigma.

*The projective test on the line of sight* (`projective.fit`, `depth_bound`). The MQ-9 flew straight and level at a
steady speed, so in a frame that does not turn the object's line of sight is what the test assumes. Drawn from the
display alone -- the azimuth off the north pointer every 5 frames over 130-590 (+-0.05 deg), the depression off the
slant range (S² a quadratic through its 0.1-NM steps, exact for a straight line at a steady velocity) over the height
below the aircraft (3793 m) -- by a camera looking along the middle line of sight, the test **fits, closing**, at 2.2
times its jitter, with **T = 80.7 s (16-84 % 75.9-87.2) against the laser's 92.6 s** at the last frame (Z / |Zdot| along
that axis from the case's straight line): the verdict and the sign right, T 13 % short and outside its band, which (a
residual bootstrap) ignores the residuals' correlation, as the drawn series found. T rests on a few tenths of a degree
of elevation: with the slant drawn as a straight line through its steps (30 m off at the ends, 0.2 deg), T is 63.6 s.
With the drawing camera's k (20 px/deg, its axis the frame's centre) the aspect under the hypothesis is 53 deg against
the line's 57 (the velocity against the line back to the aircraft at the last frame), and v/R 0.0182 a second against
0.0172.
The depth bound on the same track (the band's change of velocity, M5) is |Zdot / Z| <= 2.1 % a second against the
laser's 1.08: it holds, twice wide. Golden check `test_yemen_line_of_sight_against_the_laser`, on the drift stage's
vendored readings (`tests/golden/hellfire_drift/`).

**The Santa Barbara Huey** (the 2018 hoist; the OH-58A's printed positions at 13250, 13390 and 13530
against the stored hoist site, the rotor hub 12-31 m over it: 290-304 m off falling to 274-290 m, closing at 1.6 m/s,
tau +170 to +190 s, its size growing 5 % over the 9.3 s). The size route cannot size it: the saturated cabin and engine,
their bloom and the rotor's ring reach past flicker's 80-px cap, and the extent reads 71-80 px where it reads at all
(79 of 194 frames at the cap) -- it claims nothing, rightly, though the reason it gives ("comes and goes") is not the
reason. A 5 % growth in 9.3 s is beyond the route anyway. Its known size gives k instead: the rotor disc (14.63 m, a
UH-1H's 48 ft), which no single frame shows, is the ring the frames' spread draws about the core over 25-51 frames,
243-280 px across (an ellipse through its outer edge; 270 by eye), its axes' ratio a level disc seen 38-59 deg down
(the geometry: 50 deg) -- k = p R / S = 86-99 px/deg at 297 m (`scale.k_from_reference`'s), a field of 19-22 deg, +-7 %, the
disc's edge the larger share. `focus` with that k finds one spot in the night's hillside and no blur, so NO POWER; the
Huey, bright and wider than a point, would get no bound in any case.

**The admissible region in (R, Rdot)** (`kinematics.admissible_region`, `Case.admissible`, `figures.admissible`; A10).
The astronomer's frame for a short angles-only track (Milani et al. 2004; Tommei, Milani & Rossi 2007): the track
gives the angular rate and nothing of the range or its rate, and the physical constraints carve a region in the
(R, Rdot) plane, which is then sampled. Here the constraints are the bounds the stages give on R (a range given, or
worked out from a reference of known length and its range ratio with k, `Case.ranged`: the reference at L k / l, the
object R_obj / R_ref times as far; else the focus's floor below, the horizon's and the haze's ceilings above -- the
ledger's rows as numbers), a speed
cap (V_CAP, three times the speed of sound: nothing that breathes air flies faster), a size range through
S = p R / k where k and the extent are known, and tau where it is measured (Rdot = -R / tau, one line of the plane).
At each allowed R, |Rdot| <= sqrt(v_cap² - (omega R)²). The region is drawn evenly (uniform in area, as the
space-surveillance practice samples it; with tau, along its line) and the draws give the 5-95 % of the speed
relative to the platform, the aspect angle and the size, the share under the speed of sound, and the least and the
most the speed can be: omega R at the floor (the Technical Note's one-sided bound, along Rdot = 0) and the cap. The
figure (`<tag>_admissible.png`, among the report's where omega is known) has the range along the bottom, the range
rate up, the region shaded, curves of constant speed across it, the bounds that cut it named, tau's line, and the
size along the top. The words say under what: "with the range between a and b (which bound) and a speed cap of c,
the speed is at least ... and at most ...; drawn evenly over that region it runs ..., so much of it under the speed
of sound". A case whose k is unknown has no omega and no region: the size-and-speed figure's ladder of fields stands
for it. A track the camera held in view has none of this: its motion is the camera's.

**The time-distance diagram** (A13) is the lower panel of the speed band's figure (section 32): the distance run
along the track from the kriged rate against time, its band, the straight line at the average speed, and the track's
own path pair by pair.

**Not built:** edge-crossing fits (A16: the time an object takes to cross the frame's edge, times its angular rate,
against its angular size -- a glint appears at once, a body takes p / v_px to enter) need the frames at the edge and
a track that reaches it; and the parallax number (|v_obj - v_bg| / |v_bg| at the object's position: valid only over
a world-fixed textured background, 22 of 96 PURSUE clips) is `comotion`'s and `layers`' to give, not the track's.

## 34. `mcdonald drift` -- did it drift with the wind? (added 2026-10-21)

**What it answers.** Whether the object moved with the air, as a balloon, a cloud of debris or a bit of film does, or
through it, as a drone, an aircraft or a bird does. Its speed over the ground says nothing of this; its speed through
the air (its airspeed) does, and a single camera rarely shows that directly. Several things a clip can show bear on it,
and each is put as a test with a stated outcome: `passes` (consistent with drifting), `fails` (not drifting) or `cannot
say`, with the reason. Three main tests need only the display's readings and the object's brightness, so they run on any
video whose display is intact; a fourth weighs other evidence that only some videos hold (something shed, cloud at the
object's depth, a strike). A test runs only on the inputs it needs, and says what it lacks otherwise.

```bash
mcdonald drift CLIP.mp4 --size-px 22.3,14.6 --remains remains.csv --pieces piece_A.csv,piece_B.csv \
  --slant slant.csv --horizontal horizontal.csv --own-height own_height.csv --bearings bearings.csv --heading 144.9 \
  --winds hist_1.json,hist_2.json --airspeed-kn 0,240 --flicker flicker_envelope.json
mcdonald drift CLIP.mp4 --comotion comotion_envelope.json --tracer-depth layer --flicker flicker_envelope.json
mcdonald drift CLIP.mp4 --platform platform.csv --los los.csv --winds era5_1.json,era5_2.json --obs-winds obs.csv \
  --ground-m 72 --when 2013-04-27T01:22:47 --flicker flicker_envelope.json
```

**The tests.** Every question is put so that a drifting body answers yes (since 2026-10-22, after the drift paper:
the remains' test asked "did anything heavy fall?" and the beat's whether the brightness beats). The three main tests
come first, the fourth last. Until 2026-10-28 the tracer and the remains were T1 and T2, and the height, the winds and
the beat T3, T4 and T5; they were put last because few videos show a strike or anything shed, while the other three
run on any intact display (Jacob). L is the object's length on the screen in pixels; δ is the line of sight's
depression below the horizontal.
- *T1, the height.* Does it hold its height, or rise as a sounding balloon does (about 5 m/s)? From the ranges the
  display prints: the slant range S, fitted by a quadratic in time, at each step of the horizontal range G gives the
  height difference sqrt(S^2 - G^2); its error is the step's timing (one frame) carried through S's change. Against the
  aircraft's own height (sea readings), a straight line in time gives the object's vertical speed. Both a floater and a
  sounding balloon pass; faster than 8 m/s (beyond any balloon) by two errors fails. It also gives δ, which T4's parts
  then use.
- *T2, the winds.* Does its motion relative to the aircraft fit the winds? The ranges and the north pointer's bearings
  give a straight line in space (east, north, up; least squares on all three kinds of reading, the bootstrap over
  them). An aircraft flies through the air along its heading, so for a body drifting with the wind the motion's part
  across the heading is the difference between the winds at the object's height and at the aircraft's, whatever the
  airspeed; its part along the heading then gives the airspeed the aircraft would need. With archived model winds
  (Open-Meteo hourly pressure levels; a level with no height placed by the hypsometric equation at 280 K): passes when
  the winds' difference lies the way the motion does and the airspeed it needs is the aircraft's (`--airspeed-kn`).
  A drone adds its own airspeed; the aircraft airspeeds each drone speed (`--speeds`, m/s) would need are listed. It
  never fails: a mismatch can be the winds' error as well as an airspeed.
- *T1 and T2 from the aircraft's own track* (`--platform`, `--los`; added 2026-10-21). Many displays (a WESCAM-style
  ACFT block) show the aircraft's own position, altitude and heading, and range only the ground: the line of sight's
  ground point and the terrain's height there, the laser off. Each reading is then a ray from the aircraft through
  the object, given as an azimuth and a depression or as that ground point, and turned onto the object by its offset
  from the boresight where known. If the aircraft turns, the rays cross, and a straight path at a steady velocity
  (east and north on a map about the aircraft's mean position, height above the sea, and their rates; points on the
  WGS84 ellipsoid, so a path 100 km off keeps its curvature) fitted to them in angle gives the object's height, its
  climb (T1, the same rule as from the ranges) and its velocity over the ground. Errors: the covariance scaled by the
  reduced chi-square, and a bootstrap over the readings started from the solution; the larger is used. A drifter moves
  over the ground at the wind's velocity at its height, so against each wind the airspeed it would need is
  |V - W|, with no aircraft airspeed or heading in it. The winds: model files (Open-Meteo, pressure levels or the
  archive's 10- and 100-m levels over the model's ground, interpolated in height and held beyond their levels; only
  the hours within one of `--when`); observed winds (`--obs-winds`: source, height above the sea, from, speed), a
  source that brackets the object's height interpolated in the logarithm of the height above `--ground-m`, one that
  does not read at its nearest level and counted only within a factor of 4 of the object's height; and the aircraft's
  own wind, fitted from its positions and headings through a turn of 30° or more (its positions are a start plus the
  wind times the time plus its airspeed along its heading), with the profile between it and an observed level below
  the object. A model file counts within its levels, and beyond them, held at its nearest level, only within a factor
  of 4 of the object's height above the model's own ground, as an observed level does (until 2026-11-02 a model wind
  counted at any height: a file with only a 100-m level counted at 3,960 m, and T2 passed or failed on it). T2 passes
  when every wind that counts leaves it within their own spread plus two errors of the fitted velocity, plus the
  largest of the counted winds' own errors (a model's, or two errors of the aircraft's own wind) and the wind's own
  change over the height between the object and the nearest level a wind was read at (both since 2026-11-13, below);
  fails when even the smallest is 10 m/s or more beyond that (it flies); and cannot say between, when two errors of
  the velocity exceed 5 m/s (T2 cannot then tell a drifter from a slow flier), or when no wind was read near enough
  to its height.
- *A model's own error* (`MODEL_WIND_ERR`, 3 m/s; 2026-11-13). The spread of a model's hours says how much its wind
  changes from hour to hour, not how far it misses the air's own motion. The Galileo Project's three camera sites near
  Las Vegas triangulate clouds 2-5 km up, so their motion over the ground is known (the uap repository's
  `galileo/nevada/README.md`). Against Open-Meteo's hourly winds, those clouds need 3-4 m/s through the air (median;
  90th percentile 5-9), more than the hours' spread of about 1-2 m/s. On the spread alone T2 passed 36-54 % of them.
  With 3 m/s added it passes 80-94 %, and none of 44 aircraft with known tracks (ADS-B). The price is said in the
  reading: with a model's winds, a body flying a few metres a second through the air is not told from a drifter.
  Observed winds (a sounding, a weather report, the aircraft's own) keep the rule before, since nothing here has
  measured their error. Two things the clouds also showed: on windy days clouds lag the wind (0.6-0.7 of its speed,
  as standing wave clouds do), so a cloud is not always a drifter.
- *Drifting against holding still* (2026-11-13, IDEAS.md N2). A body holding still over the ground needs the wind's own
  speed through the air. Wherever the wind is weaker than T2's tolerance, that fit as well, and a hovering body passed
  as a drifter. T2 now passes only where every airspeed drifting needs is under the weakest counted wind's speed, so
  drifting fits better than holding still at every wind; otherwise it cannot say, and the reading says why. Measured on
  the Galileo clouds' T2 passes before it was built: this rule keeps 62 of 69 and 20 of 31 false low points (two
  different clouds matched; a stricter rule, every wind over the tolerance, keeps 45 and 2). The Puerto Rico lanterns
  keep their pass: they need 1.4-3.6 m/s through the air, and holding still would need 4.5-9.5. A drifter in a light
  wind still passes where it needs far less than the wind (0.1-0.5 m/s in a 3-m/s wind, in the tests).
- *Whether the rays fix a path at all* (`drift.unfixed`; 2026-11-02, after the single-camera survey's Part 5). The
  bearings-only problem: from an aircraft flying straight, any path scaled along the rays fits as well, so only a turn
  ranges what it sees (Nardone & Aidala 1981; Fogel & Gavish 1988; Park et al. 2015, Result 2). Until 2026-11-02 the
  stage read this from the fit's velocity error alone, and that reads where the fit landed, not what the rays hold:
  the cost is flat along range, the 28 starts land anywhere on it, and a landing at 1-2 % of the true range gives a
  velocity nearly the aircraft's own with a small error in m/s, since the error scales with the range found -- a
  phantom flying beside the aircraft, which passed on 2 of 196 drawn straight flights at the default sigma and 2 of
  30 at a tighter one, T2 then calling a body drifting with the wind a flier (4 of 4). Two gates now come before any
  number of the fit is trusted, and T1 and T2 cannot say with the reason where either shuts: the aircraft's own path
  must leave a straight line at a steady velocity, in the fit's own coordinates, by more than twice its readings'
  a priori error (10 m: an arcsecond is 30 m) -- the part of the camera's path that the object's model cannot copy
  is all that ranges it, and a straight flight's own rounding leaves under that (the path gate; Park's Result 2(i) as
  a test; the factor 2 is a judgement set over that null) -- and the Cramér-Rao bound on the logarithm of the range
  at the fit (Nardone, Lindgren & Gong 1984, evaluated at the data's own fit: the gradient of ln R in the six
  parameters through the fit's covariance) must be under 1, the range known to better than a factor e. On the
  survey's drawn flights, the same fits read both ways: 4 of 320 straight flights passed as phantoms before and 0
  after, and 2 of 30 at the tighter sigma before and 0 after; the bound alone would have let 48 of the 320 through
  (it takes the aircraft's path as exact, and a straight flight over the ellipsoid leaves 0.6-1.2 m off a map-straight
  line), the path gate none, while a straight flight whose positions are rounded to an arcsecond and a foot leaves
  7.9-12.6 m, under the 20-m gate; the 16 of 80 turning flights the old rule passed are exactly the 16 the stage
  speaks on now. On Puerto Rico's real turn the path leaves a line by 855 m, the bound is 0.0025, and nothing changes. A third gate is reported and not
  yet a refusal: an F test of the same rays fitted with a steady acceleration over the straight fit (`model_p`; an
  object that rounds a corner gives a small bound on a wrong fit, the survey's R7), whose rate on a real drifter is
  not calibrated (Puerto Rico's lanterns give p = 0.054). The fit also needs enough readings for its bootstrap: a
  resample of the readings is fitted only where it holds 8 distinct ones, so 6 and 7 readings keep none of the 2,000
  (the stage admitted 6 and crashed on them until 2026-11-02), 8 keep 4.8 on average and 9 keep 69; the bootstrap's
  errors (its 5th and 95th percentiles among them) are read from 20 resamples at the least, so the stage needs 9
  readings (`READINGS_MIN`, computed from the two by `boot_kept`) and says so below that.
- *Whose errors the path carries* (`drift.own_scatter`; 2026-11-13, IDEAS.md DR3). The fit weighs each ray by the errors
  given for it (`--los-sigma`, 0.3° in azimuth and 0.1° in depression by default), and its covariance was scaled up by
  the rays' misfit and never down. A display that prints its ground point to a metre was then judged at the default:
  PR051's 23 rays (a reading by an agent, not yet checked by a person) scatter by 0.017° and 0.003° about their path,
  a reduced chi-square of 0.0024, and the climb read +0.08 +- 2.74 m/s where the rays' own scatter gives 0.16. The rule
  now has three cases. Rays that fit worse than the errors given scale them up, as before. Rays that fit as well as the
  errors given allow leave them standing, as before: under them the fit's summed squares are chi-square on 2n - 6
  degrees of freedom, and the errors given stand unless the sum lies in the lowest 1 % of that distribution (`OWN_P`;
  the Puerto Rico lanterns' lies at 9 %, so their errors do not move). Rays that fit better than that reject the errors
  given, and the rays' own scatter takes their place: the azimuths' mean square about the fit and the depressions',
  each its own (over n - 3), widened by Student's t at 95 % for the fit's degrees of freedom over the normal's 1.96,
  since a scatter estimated from few rays is itself uncertain (1.11 at 9 rays, 1.03 at 23). The path is not fitted
  again; its covariance is read with the new errors (the sandwich form), so no fitted number moves, only the errors
  and the range's bound. The scatter is never read as under a hundredth of the errors given (`OWN_LEAST`, a guard for
  rays that were drawn or copied, a judgement) nor over them. The bootstrap over the readings is unchanged, and the
  larger of the two errors is reported as before. On 400 drawn orbits whose rays scatter by a sixth of the errors given,
  two such errors hold the true east and north velocity and the true climb 94.5, 95.3 and 94.5 times in 100; with the
  errors given equal to the scatter drawn, 95.5, 96.0 and 95.0, and the rule then takes the rays' own scatter on 7 of
  the 400 (its level is 4). What it does not see: an error the
  rays share. Readings that were smoothed or interpolated scatter less than they err, and a constant error of the
  display's own angles moves every ray alike (the next point).
- *The display's azimuth reference* (`drift.az_reference`, `--az-ref-err`; 2026-11-13, IDEAS.md DR2). Every ray's azimuth
  rests on one reference, the display's own true north: an inertial heading, or a ground point the display worked
  out with one. An error in it turns every ray about its own aircraft position by the same angle. The rays' scatter
  cannot show that, and the fitted path moves with it: by 1.41 m/s of velocity and 0.08 m/s of climb for one degree on
  the Puerto Rico turn, three times the velocity error the scatter gives; by 3.7-4.5 m/s on PR051's. So the same rays
  are fitted once more with a seventh parameter, one constant added to every azimuth, and that fit's covariance gives
  how each of the six moves for a degree (`az_reference_pull_m_s`, `az_reference_pull_climb_m_s`) and what the rays
  themselves read the reference as (`az_reference_fitted_deg`, `az_reference_err_deg`: -2.6 +- 1.3 deg on Puerto Rico,
  -1.6 +- 0.7 on PR051's two legs, +0.3 +- 2.7 on its second leg alone). The path stays the six-parameter fit, which
  takes the reference as right, and the error of doing so is added in quadrature to the errors from the rays'
  scatter: the pull times how well the reference is taken as known beforehand. **That number is a judgement, not a
  measurement: nothing here has measured a display's reference.** By default it is the azimuth error given for the
  rays (`--los-sigma`, 0.3°), taken to hold for the part all rays share as for each ray's own reading;
  `--az-ref-err` gives another, and `inf` leaves it to the rays (their own reading and its error, in quadrature). The
  rays' reading is reported and never used to tighten a reference taken as known, since the path was not fitted with
  it: a path drawn with every azimuth a degree off and read with the reference known to a degree missed the truth by
  2.5 such tightened errors, and is held by the untightened ones (in the tests). On Puerto Rico the default moves T2's
  "two errors of the fit" from 1.0 to 1.3 m/s and T1's error from 0.04 to 0.05 m/s; left to the rays alone, two errors
  are 8.2 m/s and T2 cannot say. Where the rays' scatter alone would fix the velocity and the reference leaves it open,
  T2's reading names the reference. Not carried: a constant error in depression, and errors that run on from reading
  to reading (the residuals' lag-1 correlation is +0.07 and +0.51 on Puerto Rico's azimuths and depressions).
- *The heading box and the direction of flight* (`drift.aircraft_wind`; 2026-11-13, IDEAS.md DR2). The aircraft's own wind
  comes from its positions and its heading box through a turn, and took the box as the direction of flight. On
  PR051's upload that fails: the second leg misfits by 17 m where its positions scatter by 3, and the two legs
  share one wind to 3.7 m only with the aircraft 14.2 +- 0.3° right of its box (52 m without; what the 14° is stays
  open). The box alone gives 21.6 m/s from 211°, the positions 11.2 from 266°, and T2 failed or passed on that
  alone. So the positions are fitted again with one constant added to every heading, and the constant is taken where
  two things hold. An F test of the second fit over the first passes at 1 % (`HEADING_P`). And the constant exceeds
  half a step of the heading box by two of its errors: a box that prints whole degrees cannot say where in the degree
  the heading is, and with fine positions that rounding alone passes the F test (28 % of drawn turns at a tenth of
  an arcsecond, 12 % overall). The rule's false-alarm rate, measured: of 720 drawn turns of 40-157° with the box true,
  positions rounded to 1, 0.36 and 0.1 arcseconds and the heading to a degree, it takes an offset on 2 (0.3 %; 95 %
  upper bound 0.9 %). Its power on the same turns: an offset of 1° is taken on 65 of 200, 2° on 150, 5° on 197,
  14.2° on 200. Where an offset is taken, the wind, the airspeed and their errors are the second fit's. Where none
  is, the wind is the first fit's, as before, and its error is the larger of the two fits' with what an offset
  inside the box's own step would do. Both fits' errors use the position error given (10 m) and are scaled up by a
  misfit, never down: a rounded heading leaves errors that run on from reading to reading, and the positions' own
  scatter understated them (two such errors held the true wind 74-87 times in 100 on drawn turns of 157°; with the
  error given, 99-100). The wind's error now enters T2: the tolerance takes the largest of the counted winds' own
  errors, a model's 3 m/s or two errors of the aircraft's own wind. And a turn too short to tell the wind from the
  offset and the airspeed gives no wind that counts: two errors over 5 m/s (`VELOCITY_FIX`), which a 41° turn of ten
  readings does not meet and PR051's 52° turn of 23 readings just does (4.4). The Puerto Rico turn asks for no offset
  (-0.23 +- 0.15°, p 0.12): its wind is 9.51 m/s from 70.6° as before, its error 0.55 where it was 0.25. What this
  costs, on drawn orbits with the aircraft's own wind the only one, 60 draws each: with the box 14.2° off, the old rule
  failed 60 of 60 drifters and the new one passes 60 of 60; with the box true and a 157° turn nothing changes (drifters
  pass, 25 m/s through the air fails, 5 and 10 m/s cannot say); on a 60° turn a body flying 5 m/s through the air
  now passes 55 of 60 where 3 did, because the wind from so short a turn is known to about 2.4 m/s once the offset is
  open. T2 never told 5 m/s from drift where the winds were that uncertain; now it says how uncertain they are.
- *A wind read far from the object's height* (`drift.wind_change`, `SHEAR_AT_KM`, `SHEAR_POWER`; 2026-11-13, IDEAS.md
  DR4). One wind alone has no spread, so T2 held it at the spread's floor, 0.25 m/s, and took it as the wind at the
  object's height wherever it counted: within a factor of 4 in height. On PR051 the aircraft's own wind, read 1,422 m
  above the object, decided a fail. How much the wind changes with height is measured on radiosondes: 8,125 soundings
  of 18 IGRA v2 stations at 00 and 12 UTC, January to early November 2026 (the data folder's `winds_igra/`;
  `tools/shear_igra.py`; the table of percentiles is `tests/golden/shear_soundings.csv`). The vector change of the wind
  between two levels of one sounding grows as a power of their height difference dz: nine times in ten it is under
  10.3 (dz / 1 km)^0.57 m/s. That is 2.8 m/s over 100 m, 6.1 over 400 and 12.6 over 1,422. The law was set on the
  even-numbered stations and held on the odd ones: 0.89 of their pairs and 0.88 of their soundings (one pair each) lie
  under it, 0.86-0.93 by height difference from 50 m to 6.4 km. It is one law for every height and place, which it is
  not quite: by height band the constant runs from 8.6 (3-8 km above the ground) to 12.0 (8-16 km) and the power from
  0.46 to 0.60; by station the 90th percentile at 1.2 km runs from 7 m/s (tropical coasts) to 14 (mountains, desert
  coasts); it is 11.0 from November to April and 8.3 from May to October. Each wind now carries how far in height it
  was read from the object (`level_gap_m`: none where it was interpolated to the object's height), and T2 adds the
  wind's change over the smallest such gap among the counted winds to its tolerance. Where that change is over 5 m/s
  (`VELOCITY_FIX`: a gap over about 280 m), no wind was read near enough to tell a drifter from a slow flier: T2 cannot
  pass, and says so; it still fails a body 10 m/s or more beyond the whole tolerance. With a second wind at the
  object's height nothing is added: the winds' own spread says how they differ. What the rule did to true drifters,
  counted on the odd-numbered stations' soundings with the fitted velocity taken as exact: given one wind 1,422 m from
  the drifter's height, the old rule failed 18.7 % of them and passed 0.2 %; at 800 m it failed 10.8 %, at 400 m 4.1 %.
  The new rule fails 0.6 % at 1,422 m and 0.2 % at 400 m and passes none there; at 100 m it passes 89 % (9 % before)
  and at 200 m 80 %. The Puerto Rico lanterns have a sounding and a measured profile at their height, so nothing is
  added and nothing moves; PR051's one wind is 1.4 km off, and T2 cannot say.
- *T3, the beat.* Is its brightness free of a beat at a wingbeat's or a rotor's rate? From `mcdonald flicker`: a beat
  of its own that holds across the video fails (a wingbeat or a rotor). "Holds" is flicker's headline rule (§13,
  `comes_back`): the whole track beats, or passing windows that do not overlap agree, more of them than chance gives
  (§13; since 2026-11-13, and an envelope made before then is weighed against chance here, from its own windows). A beat
  in one stretch of many is not counted, since a lantern's or a candle's flame, or chance over many windows, can make
  one, and the test passes on the whole stretch (until 2026-10-22 it could not say); an envelope without the record is
  read from its finding ("that is one stretch"). *Two cameras* (`--flicker a.json,b.json`, `test_beat_cameras`;
  2026-11-13, IDEAS.md N4): a beat of the object's own shows from every side. Where one camera's beat holds, another
  camera watching at the same time keeps the failure if it sees the beat too (within 0.5 Hz, at a third of its strength
  or more), or if it could not have seen a beat a third as strong. Where it could have and does not, the beat is the first
  camera's view, and T3 passes on it. On the Galileo clouds, Hideout's 7 % beat at 1.94 Hz went where Sphere, able to see
  1 %, saw none; a 5 % beat at 2.44 Hz stayed, the other camera seeing 0.8 % where only 2 % would have shown. The
  envelopes must be of the same moments; nothing here can check it. No beat passes, with the smallest beat the clip could have shown. That is the injections' floor
  where `mcdonald flicker` ran them. A result out of `mcdonald run` or a case file has none, and there it is the track's
  own closed-form floor (§13, `flicker.analytic`'s `with_floor`: what a beat needs in the track's own noise and over the
  background's flicker), which the stage records for every object and the report's beat row already reads (2026-11-13,
  IDEAS.md DR5). Until then the rule's own threshold was quoted there, three times the background's beat, which says
  nothing of the track's noise: on 18 of the 28 reference objects the track's own floor is higher, by up to 17 times
  (PR088 object 2: 2 % quoted, 36 % in truth), and PR097 object 4 read "only a beat over 2 % would have shown" beside
  an 8.7 % peak that did not show. Only the sentence moves, no outcome; the rule's threshold stays the last resort.
- *T4, other evidence.* Does other evidence in the video, where there is any, agree with drift? Few videos show a strike
  or anything shed, so this test runs only on whichever of its parts the inputs allow. It fails when a part fails,
  passes when a part passes and none fails, and cannot say otherwise; only its tracer part bears on the airspeed.
  - *T4a, a tracer.* Does it move with something that moves with the air at its own depth? Light pieces it sheds stop in
    the air within about a second, so a flier at airspeed V leaves them behind at V sin δ on the screen. The pieces'
    speed against the remains, in L per second (a straight line in time to their difference, its error from a
    moving-block bootstrap), divided by sin δ bounds the airspeed in the object's own lengths per second, with no field
    of view, range or wind. Fixed-wing drones cruise at two or more of their lengths a second, birds at four or more: a
    bound under 2 passes; pieces leaving at 2 L/s or more fail, with or without δ: what shows across the line of
    sight is the least the airspeed can be, and flight along it only adds (2026-11-13, IDEAS.md DR5; until then a
    missing δ was asked for first and such pieces could not say). L is taken at its smallest (the rate kindest to a
    flier). Cloud is a tracer too (`--comotion`, the envelope of `mcdonald comotion`), but only where it is shown at the
    object's depth: cloud passing in front of the object places it within the layer (`--tracer-depth layer`), not at a
    cloud feature's depth, and a relative motion through it can then come from a depth offset inside the layer, from
    wind shear or from vertical motion; it cannot say.
  - *T4b, the remains.* If it was struck, do its remains sink steadily? A powered drone carries dense parts that fall
    with gravity's acceleration once it breaks up, and on the screen a body of true length L_true falls at g cos δ /
    L_true in L per second squared. The remains' screen-down acceleration is read two ways: by a quadratic in time
    with a moving-block bootstrap error (blocks of 15 frames), and from the track's own speed band (§32,
    `kinematics.speed_band`: a line, a Matérn-3/2 wander and a nugget fitted by REML) as the change of the
    screen-down velocity over the stretch divided by its span, with its sigma. A track's wander can outlast the
    bootstrap's blocks -- the Yemen remains wander with a range of 0.55-0.75 s against 0.5-s blocks -- and the
    bootstrap's error is then too small (2.4 times there), so the reach, the size under which a falling wreck of every
    body is excluded, is g cos δ over the band's 95 % bound on a steady change of speed it could have missed (§32,
    `change_bound`; either sign), and over a + 3σ only where the band gives no bound (it saw the change) or the track
    has none (`reach_by` says which). Fails when the quadratic's a - 3σ is at or above half the free fall of a 20-m
    body (`WRECK_FAIL_M`; tried first, so that a measured acceleration down is never read as a steady sink); else
    passes when the reach is 10 m or more (`WRECK_MIN_M`: every drone and every bird is smaller); else cannot say.
    Until 2026-11-02 the reach was a + 3σ alone and the pass needed 20 m; the band's bound put the Yemen remains at
    16.5 m, which excludes every drone and bird there is but would not have met 20, so the pass threshold moved (the
    maintainer may move it again). The pieces' speeds against the remains (T4a) are read from the difference tracks'
    own bands as well (`pieces_band_L_per_s`), beside the lines'; T4a's rule and bound stay on the lines' (on Yemen
    the two agree within 5-9 %).

**The verdict.** `consistent with wind-borne drift (tentative)` when a strong test -- T2, or T4a with a tracer at the
object's own depth -- passes and none fails; `not drifting` when any test fails; otherwise `cannot say`. A beat counts
as a failure only where it holds across the video (T3, above). The two controls of 2026-10-21 set that rule:
- On AARO's Puerto Rico lanterns, a known drifter, `flicker` found 3.0 Hz in one 2-s window of 109, while the
  background's own windows beat in 2 of 436. Counted, it would have called them "not drifting".
- A rotorcraft hovering in calm air (the Santa Barbara hoist) has no airspeed. Kinematically it is a drifter, and only
  its rotor's steady beat tells it apart. So a held beat must still decide, against any strong pass. (A brief rule of
  the same afternoon, that the beat test's fail alone never overturned a strong pass, would have called it drift.) Tentative,
because each strong test rests on inputs read off the display (ranges, bearings, heading) and on model winds, which the
stage checks only for consistency (the straight line's residuals). It names no object: a balloon, a bag, a cloud of
chaff and a leaf all drift. T1 narrows the class; nothing here identifies it.

**A test dropped (2026-10-21).** The first version had six tests; the fifth asked whether the object's outline was a
winged aircraft's (its half-contrast fill against a fixed-wing planform drawn at its length, seen from δ and blurred as
the copy blurs). It was dropped the same day as weak: it could only exclude a fixed wing, it
passed the hovering Huey (which has none), it could not say on the Puerto Rico lanterns seen 7° from above (a wing
nearly edge-on is as compact as a ball), and it leaned on a copy's blur and sharpening. The beat, which was T6, became
T5 (and T3 on 2026-10-28). The six-test version is kept, uncommitted, in the uap repository's
`manuscript/hellfire_yemen/archive/mcdonald_drift_with_outline_test_2026-10-21.tar.gz`.

**Known answers.**
- *Hellfire/Yemen* (an MQ-9's clip of an object struck by a Hellfire, 30 Oct 2024; `$MCDONALD_DATA/hellfire_yemen/`,
  its readings in `tests/golden/hellfire_drift/`): every test passes. T1: it holds its height (-0.9 +- 1.1 m/s) 3,793 m
  below the aircraft, at δ = 40.55 deg. T2: a 100.5 +- 0.6 m/s motion relative to the aircraft, 23 kn of it to the right
  of the heading; the winds' difference lies the same way (5-18 kn) and needs the aircraft at 179-191 kn through the
  air. T3: no beat over 41 % of its brightness. T4, since it was struck: T4a, two pieces leave the remains at 0.68-0.82
  L/s (at most 1.26 in its smallest length), which bounds its airspeed under 1.93 of its lengths a second (the
  difference tracks' own bands: 0.79 and 0.62 L/s against the lines' 0.82 and 0.68); T4b, the remains sink at a
  steady rate: -0.08 +- 0.06 L/s^2 by the quadratic in time, and -0.17 +- 0.14 with the track's own wander fitted (a
  band; its wander's range 0.75 s against the bootstrap's 0.5-s blocks, so the band's error is the honest one, 2.4
  times the bootstrap's), which would have shown a steady change of more than 0.45 L/s^2 either way (95 %): no
  falling wreck of any body under about 17 m (16.5; a 5-m wreck's 1.49 L/s^2 is excluded three times over; a 20-m wreck's
  0.37 is not; until 2026-11-02 the reach was 75 m, by a + 3σ alone). Verdict: consistent with wind-borne drift
  (tentative).
- *AARO's Puerto Rico lanterns* (2013, a CBP aircraft's infrared turret; AARO's case resolution of 20 March 2025: two
  sky lanterns drifting at the wind's speed; `$MCDONALD_DATA/aaro/videos/DOD_110692805-1920x1080-9000k.mp4`, its
  readings in `tests/golden/puerto_rico_drift/`): the known drifter. The laser is off, so T1/T2 come from the aircraft's
  own track: 39 readings over t 22-117 s, the aircraft turning 157° round the lanterns, the line of sight 191°. They
  moved at 7.37 m/s toward 240° (two errors 0.9), sinking 0.60 +- 0.04 m/s, 181 m above the airfield (reduced
  chi-square 0.79). The aircraft's own wind is 9.5 m/s from 071° at 514-776 m; the airport's METAR 060° at 9-10 kt;
  every wind that counts (ERA5 in five cells, the San Juan sounding, the aircraft's own, the profile between) leaves
  them 1.4-3.6 m/s through the air, within the winds' 6.2-m/s spread: T1 and T2 pass. T3 passes on the whole stretch:
  `flicker` found 3.0 Hz in one 2-s window of 109 (the background's own windows beat in 2 of 436), a beat in one stretch,
  which is not counted. Nothing was shed or struck, so T4 cannot say. Verdict: consistent with wind-borne drift
  (tentative). Had that beat counted, it would have been "not drifting": the control's lesson, and the reason for T3's
  rule.
- *Santa Barbara County's UH-1H Huey* (12 Aug 2018: a sheriff's OH-58A's white-hot turret, circling while the Huey
  hovered over a ridge in calm air to hoist two hikers; its pilot's upload, YouTube 7N8_g3pCK2o, in
  `$MCDONALD_DATA/santa_barbara_2018/`, its inputs in `tests/golden/santa_barbara_drift/`): the known flier, and the
  hardest kind, since hovering in calm air it has no airspeed. The turret held a stored ground point, the hoist site,
  and the display shows no range and no field of view, so nothing reaches the Huey, and nothing was shed or struck:
  T1, T2 and T4 cannot say (had T1 and T2 run, a hover in calm air would pass them). T3 fails: `flicker` finds
  10.645 +- 0.007 Hz, 5 %
  of its brightness, over the whole stretch (frames 13250-13530, a disc of 90 px, ring 100-130, background apertures
  320 px away) and in windows apart, the blade-pass of its two-bladed main rotor (its double folds to 8.68 Hz).
  Verdict: not drifting, the right answer, which only a held beat could give.
- *PR051's second leg, a second display for the route from the aircraft's own track* (IDEAS.md DR1; 2026-11-13;
  `tests/golden/pr051_drift/`, held in test_drift and test_golden). **Its inputs were read off the data bar of the
  unredacted upload by an agent and have not been checked by a person**; a second agent checked seven of the 23
  frames (the whole seconds, the height and the grid's hundreds of metres agree; the ranges recomputed from the
  readings match the ranges the bar prints to 1-12 m). It is kept as a test of the route's arithmetic on a real
  display, not as a finding about the object, and no verdict is drawn from it. The route takes the bar's TGT A as the
  boresight's ground point while the gate holds the object, so the scene must stream behind the object. On the ULTN
  part of the hold (39-58.5 s; 13 readings) `mcdonald scene` reads that stream at 0.8-0.97 of the rate TGT A's
  motion gives, on the upload, on a 29.97 copy of it and on the released copy, with a control at 0.88 where the scene
  is known; on the 4X part (60-73.5 s; 10 readings) no reading of the picture has power, and the bar alone carries
  them. What the stage says of the 23 rays: 9.4 m/s toward 103° at 4,298 m above the sea, 11.0-11.7 km from the
  aircraft; their own scatter (0.018° and 0.004°) in place of the errors given; T1 passes (+0.08 +- 0.19 m/s); the
  aircraft flew 14.7 +- 1.3° right of its heading box, and its wind is 11.2 m/s from 266°; T2 cannot say, since that
  wind, the only one, was read 1.4 km above the object; T3 passes on the 4 s of the hold it was given. Verdict:
  cannot say. Three of this stage's rules were found on it (the errors, the heading box, the far wind).
- *PR055* (a dark sphere seen passing into cloud): `comotion` on the zoomed frames, pairs of 6 frames, finds it moving
  through the cloud field at 1.31 and 3.66 of its diameters a second on its two visible legs (15.0 D in 5.6 s; 15.0-15.7 D
  for every ring from 450 px out), and turning about 110 deg against a steady flow. The cloud places it only within the
  layer, so T4a, and with it T4, cannot say; no ranges are shown, so T1 and T2 cannot run; T3 passes (no beat over
  23 %).
  Verdict: cannot say.

**How it fails.**
- Its strong tests are only as good as the display's readings: a range read off by a step, a bearing off the pointer,
  a heading. The stage times each reading to the frame and checks that they hang together; it cannot see a wrong one
  that agrees with the rest.
- T4a's bound uses the smallest L, and a piece that is not light (a fragment with its own momentum) leaves at more than
  the air does: the bound is then too high, never too low.
- T2 compares with model winds, hourly and tens of kilometres apart; a local wind they miss is not seen.
- No test sees vertical drift directly except T1, and T1 needs the ranges or the aircraft's own track. A clip without
  ranges, the aircraft's position through a turn, a heading or a shed tracer is "cannot say" at best, whatever it shows.
- From the aircraft's own track, the rays rest on the display's position block and its ground point, each rounded (1
  arcsecond, about 30 m; Puerto Rico's fit, 0.26° rms in azimuth); an altitude that is a GPS height above the
  ellipsoid rather than above the sea moves the height, not the velocity. Its power is set by the winds' own
  disagreement. On the Puerto Rico geometry and winds (objects planted in the lanterns' own air, seen from the real
  aircraft positions with the real fit's ray errors, eight directions each; the uap repository's
  `pr_drift_planted.py`): a flier at 25 m/s or more through the air fails in every direction, at 20 m/s in 5 of 8,
  at 10-15 m/s it cannot say, and at 5 m/s, slower than the winds' 6-m/s spread, 2 of 8 pass. A bird's 10-15 m/s is
  not told from drift there.
- A flame beats: a sky lantern's 3-10-cm fuel cell puffs at 4.7-8.7 Hz (`flicker`'s look-alike band). A flame that
  burns steadily through the video would hold its beat, and T3 would then fail a drifter.
- A rotorcraft hovering in calm air has no airspeed, so T1, T2 and T4 cannot tell it from a drifter. Only T3 can, and
  only where
  its rotor's beat shows; a rotor hidden from the camera, or a multirotor's blade-pass folded out of the band, leaves
  it "consistent with drift".

## 35. Held pictures tested, not counted, in `mcdonald flicker` (M3, added 2026-10-29)

**What it answers.** Where a video's frames repeat, is it on a slower clock -- so that a beat is heard only up to that
clock's Nyquist frequency -- or are the repeats missing samples on the frame grid's clock? Until 2026-10-29
`flicker.pictures` took every video that repeats a tenth of its frames for the first, and lowered the band's top to TOP
of the picture rate's Nyquist frequency (PR34, 2026-10-11: 10 pictures a second shown at 30 "beat" at 5.02 Hz, its hold
cadence's half). The pure-mathematics survey's census of every video in the data folder (2026-10-29, kept with the
PURSUE analyses) found the rule right where it was made and wrong nearly everywhere else: 211 of the 214 ten-second
PURSUE windows it lowered hold no cadence, and the Galileo flyers' 45-78 % holds are the HEVC encoder's.

**The word.** Each pair of frames is a letter: 1 where the frame repeats the one before (its thumbnail changes by under
HELD of the typical change, as before), 0 where it is new. A source of f_s pictures a second on a frame grid of f > f_s
-- a rate conversion, or a sensor whose pictures land on the container's frames -- repeats a frame wherever
floor(n f_s / f) does not advance. Its word is a mechanical word of slope a = 1 - f_s / f (Christoffel 1873; Morse &
Hedlund 1940; Lothaire 2002, ch. 2): balanced -- any two windows of one length hold within one held frame of each other
-- and its running count of held frames stays inside a strip less than one frame wide about the line a n. An encoder
that skips a still sky, a capture that drops frames under load, a link that stalls, hold frames where it happens to,
and their count wanders off any line as a random walk does.

**The test** (`flicker.cadence`, on the frames the stage reads -- the track's own):

1. *Balance* (`balance`, `least_balance`). At each window length L from 2 to 12 frames, the share of the windows that
   hold one of the two whole counts about a L (a the word's own share): its floor and ceiling, and where a L is itself
   whole, it and whichever neighbour more windows hold; the least of the eleven. A mechanical word gives 1; a misread
   frame spoils only the L windows over it (a frame in a hundred misread: about 0.9); a pattern locked to a GOP of five
   is balanced only at multiples of five, which the short lengths catch. A word is a cadence where its least balance is
   BALANCED (0.85) or more and above the 99th percentile of 200 random words of its share and length (`random_balance`,
   seeded, so that a case reruns to its numbers: a short word can be balanced by chance). Under their 1st percentile
   its holds come in runs; between, at random; above it but short of 0.85, "more evenly than at random". The line and
   the second gate are calibrated below. (Until 2026-10-30 a window had to be strictly within one of a L, which left a
   word with a whole a L the single count: 10 pictures a second on 30 read 0.78 where a window's share was exactly 2/3 and
   0.90 one frame off it. A word with no whole a L reads as it did.)
2. *The GOP* (`places`), for a balanced word only. An encoder's holds keep to its group of pictures: it skips blocks
   only on the frames it predicts, never on an I frame (Galileo flyer 5: 1 % of its I frames held, then 35, 49, 65 and
   78 % at the four P places). A source's land where its clock puts them. Each frame's picture type over the stretch
   is read (`clip.picture_types`, only here), the places (frames since the last I frame) with PLACE_MIN = 20 frames or
   more are read, and the word is the encoder's where under ENCODER_I = 5 % of its I frames are held and the places'
   own majority foretells it with fewer misses than the cadence does at its best -- the mechanical word of its slope,
   or of a convergent of it, at its best phase. That is a GOP whose length varies, its holds following the I frames
   where no one slope does. In a regular GOP the two cannot be told apart: a balanced word that repeats is a mechanical
   one, whoever made it, so an encoder holding every P frame of a still sky and a source cadence in step with the GOP,
   its I frames on the new pictures (PR051's YouTube copy, a 29.97 source doubled: held at odd places, fresh at even),
   are foretold as well by a cadence of the GOP's own period. Both are kept cadences -- the side PR34's trap is on.
   Given only its own slope, the cadence lost to the places on drawn words of 3,000 frames with a frame in a hundred
   misread -- a doubled source (955 misses against 21: the slope read 0.5015, not 0.5, drifts out of phase) and 10 on
   30 in a GOP of 15 (1,288 against 36), PR34's own case -- which is why its convergents are tried too.
3. *The rate* (`slope`, `every`). The narrowest strip's slope gives the source's rate, f (1 - a); the continued
   fraction of a gives the cadence's period, the first convergent p/q within 1/n of it with q at most CADENCE_Q = 60
   (1/5 is 23.976 on 29.97, a 2:3 pulldown's frame form; 2/3 is PR34's 10 on 30; 25 on 29.97 is 199/1200, periodic only
   over 40 s). It is named ("p of every q frames repeat") only for a word mechanical to the frame, its strip under one
   frame wide: a misread frame moves the slope by more than the 1/n a period is read to.

Only a cadence sets `pictures.rate` to the source's and `top_hz` to TOP of its Nyquist frequency, and only then does the
look-alike table (section 9) list the pictures' cadence and its double. Every other hold leaves the top at the frame
grid's, and the held frames stay in `held_k`, missing samples to the Lomb-Scargle periodogram (section 7), as they
always were. `pictures.holds` says which ("cadence", "encoder", "runs", "random", "uneven", "untested", "none"), and so
does the stage: "the video holds pictures at random (22% of frames repeat the one before), not in a cadence: they are
missing samples, not a slower clock, and a beat is heard up to 12.0 Hz".

**Drawn words** (`test_measurement`): 300 frames at 30 a second. 25 pictures a second, one frame held in six, is a
cadence, 1 of every 6, its top 10 Hz, and stays one with a frame in a hundred misread (least balance 0.96); as many
held at random (0.62, random words 0.42-0.71) or in runs (0.22, under their 1st percentile) are not, and keep 12 Hz.
Every P frame held and every I frame new, in a GOP of 8-12 frames, is balanced (0.94) and the encoder's (the places
miss no frame, the best cadence 69); in a GOP of 5 frames, five P frames new, it is a cadence (both miss five). A point
beating 30 % at 10.8 Hz with a sixth of its frames held at random is heard at 10.8 Hz (the rule before put the top at
10.0 Hz and heard nothing); held one in six, the top is 10.0 Hz and it is not.

**The census** (2026-10-29/30, the survey's change series of every video, read again by `flicker.cadence` in windows of
300 frames, half overlapping, as the survey read them; the Svanström set clip by clip):

| group | windows | held 10 % or more (lowered before) | a cadence (lowered now) |
|---|---|---|---|
| PURSUE (28 videos) | 694 | 214 | 3: PR055, 16.0 and 15.7 pictures a second where its sphere is; PR051, 9.9 |
| AARO (34) | 1,028 | 339 | 63, all in "Middle East 2023" (DOD_110982722), 9.5-10.5 a second |
| Galileo (5) | 33 | 25 | 0 |
| PR051's two copies | 79 | 70 | 51, the YouTube copy's, 28-30 a second |
| FLIR1's copies, Santa Barbara, Hellfire, the balloon | 169 | 19 | 0 |
| Svanström (clips) | 650 | 227 | 10: V_HELICOPTER_020-024 at 24.7-25.2, five more at 19.7-20.6 |

The place test vetoes none of them. PR34 itself, the clip TOP's held-picture rule was made on (not in the data
folder then; read for this check), is a cadence in all 35 of its windows, at 9.85-10.37 pictures a second. (Counts on
the reading of 2026-10-30; before it DOD_110982722 had 40 and PR34 34 of 35, the rest of the table as it stands.) On the
flicker stretches of the reference case files, five objects of four files
had the band cut and now do not: PR44 5.96 Hz to 12.0 ("more evenly than at random": least balance 0.78, random words
0.31-0.56), PR097's object 8 10.74 to 12.0 (in runs), PR141's two objects 9.52 and 9.45 to 12.0 (at random) and PR149
9.33 to 12.0 (at random); the other 26 hold under a tenth. The stage on those five, on the case's own command
before and after: every call, frequency, error and finding the same (PR44 3.059 Hz, PR141's infrared copy 8.29, PR097's
object 8 2.28; PR141's visible copy and PR149 no beat); what moves with the band is the look-alike table and the
numbers read over it -- the continuum null's (PR141's visible copy: p 0.65 to 0.23, still no beat), the scramble's,
the false-alarm probability's, the planted dots'. Of the controls, PR055's sphere keeps its lowered top (a
cadence of 16.0 pictures a second, 6.4 Hz), and the Galileo flyers' go to the grid's 24 Hz (flyer 1 from 8.6, flyer 4
from 9.5, flyer 5 from 16.5).

**The line, from a null** (2026-10-30). BALANCED began as the survey's line by judgement, in the census's gap. It is set
now as NUGGETS was (section 33): the least line that holds false alarms to 5 % at every share and length, on words
with no slower clock of their own. 60 frames is the shortest length that matters, as a shorter stretch hears no beat
(MIN_FRAMES). Fourteen shares from 0.1 to 0.8 by nine lengths from 30 to 3,000 frames, 2,000 words a cell (40,000 at the
worst cells), each word tested as the stage tests it (none under HELD_MIN):

- *Random*: each frame held at the word's share.
- *In runs*: a stall, a still scene the encoder skips, a capture dropping frames: held and fresh runs geometric, the held
  runs of mean 2, 3, 5 or 10 frames.
- *By GOP place*: how real encoders hold. Never the I frame; each P frame by the chance of its place; GOPs of 5-30 frames,
  regular or varying by 30 %; the chance flat over the places, rising with the place, or a B pyramid (B frames four times
  as often as P), its top under 0.9; and the Galileo flyers' four tables as measured on the census (flyer 5: 0, 35, 42, 54,
  75 %; flyer 1: 0, 17, 55, 90, 97 %). PURSUE's and AARO's GOPs of 60 are near flat by place at 0.1-0.6, close to random.

| frames | random | in runs | by GOP place | flyers' tables | all, at 0.85 | all, at 0.84 |
|---|---|---|---|---|---|---|
| 60 | 0.1 | 4.75 | 3.1 | 0.15 | **4.75** | 7.1 |
| 90 | 0.05 | 1.7 | 1.05 | 0 | 1.7 | 2.4 |
| 120 | 0.06 | 0.7 | 0.3 | 0 | 0.7 | 1.2 |
| 180 | 0 | 0.12 | 0.11 | 0 | 0.12 | 0.28 |
| 300 and up | 0 | 0 | 0 | 0 | none of 2,000 in any cell | 0.05 |

Each figure is the percentage past both gates at the worst share, before the GOP's places. The worst cell is in the runs
family, held runs of mean two with one fresh frame between (a share of 2/3), and it sets the line: 0.85 holds 5 %, and
0.84 does not. So the survey's number stands, now with a rate: at most 5 % at 60 frames, 1.7 % at 90, 0.7 % at 120, and
from 300 frames none drawn. Past 180 frames these families no longer press on the line; what does there is below.

*What the second gate adds.* On random words the first gate alone lets through 10 % at 30 frames, 2.1 % at 60, 0.27 % at
90, 0.24 % at 120 and none from 180, the worst of them at shares near 0.1. With the second gate that is at most 0.75 %,
0.1 %, 0.05 %, 0.06 % and none, at any share. Of the random words past the line it stops 92 % at 60 frames, 80 % at 90
and half at 120. Of the words held in runs past the line it stops 32 % at 60 frames, 14 % at 90 and 11 % at 120, of those
held by GOP place 19 %, 6 % and 1 %, and from 180 frames next to nothing of either (6 of 4,695 by place at 180 frames,
none from 300), as a held word stands above random words of its share once there are windows enough. So it does its
work under 120 frames, and it is the only stop at shares near 0.1 and 0.9, where its value passes the line at lengths up
to 300 frames. At shares 0.2-0.8 its value reaches 0.87 at 60 frames, 0.79 at 90 and 0.68 at 300. Its cost: where its value is
1.0 not even a mechanical word can pass (60 frames at a share of 0.1 or from 0.85; 90 frames to 0.11 or from 0.89), and such
a word is too short to tell. Alone it passes 0.4-1.8 % of random words, its 1 % read off 200 words. The GOP's places take
off little more: 1-3 % of the by-place words past both gates, 28 % where the GOP varies and the chance is flat.

*What the rate does not cover.* Three kinds of word lie outside it, and no line can put them inside.

- An encoder holding 0.9 or more of a short regular GOP's P frames: its word approaches a mechanical word of the GOP's
  period. In a GOP of 5, past both gates: at a chance of 0.9, 5 % at 60 frames, 0.7 % at 120, none at 300; at 0.95, 31 %,
  16 %, 7 %; at 0.97, 59 %, 48 %, 44 %; at 0.99, 92 %, 94 %, 99 %. Of those past both, the places veto 10-21 % at 0.97 from
  120 frames in a GOP of 5, and about half in a GOP of 8. It is real: flyer 3's frames 901-1123, every fifth frame new,
  read 0.841.
- Rate control, a leaky buffer of 2 or 6 mean frames, drained at the budget that gives the share, each coded frame's cost
  lognormal of spread sigma (with and without a scene's memory), a frame that would overflow skipped. Its holds are
  even with no clock, and as sigma goes to 0 it is a mechanical word. From sigma 0.8: at most 1.6 %. At 0.5: at most 1.9 %
  to a share of 0.6, then up to 15 % at 0.67-0.8 (under 4 % from 300 frames). At 0.3: up to 9 % to a share of 0.4, and 4-77
  % from 0.5. Frame to frame, the P frames of eight videos here spread 0.1-0.6 in log size and the B frames of six
  0.6-1.3, read off release copies, so this only roughly places a capture's own encoder. At high shares the word is
  hardly a false alarm: an encoder affording one frame in four at a near steady cost is a slower source, and the
  lowered top is true of it.
- A slower source with scattered timing, which is the same question. Pictures landing off the clock by a scatter sd read
  0.85, at 300 frames, at a little over 0.7 frames at a share of 2/3, 0.55 at 1/2, 0.33 at 1/3 and 0.25 at 1/4: the line
  takes a scatter of about a fifth to a quarter of the spacing between pictures as still a clock. DOD_110982722's windows
  past the line (0.85-0.93, three frames apart) are inside it; PR44 (0.72-0.83, two frames apart, the same kind of word:
  pictures a frame off) is outside it, at 0.6 frames or more. Where a slower source stops being a clock is a choice, and
  the line makes it there. A clock that wanders slowly stays balanced (0.1 frames a picture reads 0.89-0.99), as the test
  reads windows of 12 frames at most: over 300 frames no one mechanical word foretells PR34.

*The other side.* A mechanical word at a random phase, each frame misread at random, at 300 frames and the worst share
(1/6): 95 % pass with a frame in a hundred misread, 63 % with two, 27 % with three. At 0.88 the first two would be 82 % and
37 %, at 0.90 77 % and 29 %, so that a higher line pays for its rate here. The new reading raised words at exact fractions,
with one in a hundred misread, from 94-96 % to 99-100 % at shares 1/3, 1/2 and 2/3. All of PR34's windows pass (0.90-0.97),
all of V_HELICOPTER_020-024 (0.91-1.00), PR055's sphere (0.89 on its track), and 51 of the 70 windows of PR051's YouTube
copy (0.88 and up). What real words do near the line, cadences and not:

| least balance | word | what it is |
|---|---|---|
| 0.833 | IR_DRONE_059 | a cadence, 20 on 30: one mechanical word foretells it. Missed |
| 0.841 | flyer 3, frames 901-1123 | the encoder's, every P frame held. Stopped |
| 0.849 | DOD_111985820, frames 151-451 | share 0.11, a hold every 9-10 frames, spread 2-19: a capture dropping frames, by its look. Stopped |
| 0.855, 0.856 | V_DRONE_008, IR_DRONE_151 | cadences, 20 on 30. Called |
| 0.874 | PR055's sphere, frames 1201-1418 | a cadence. Called |

So no line separates the real words perfectly, and 0.85 falls in a narrow gap between them (0.849 to 0.855). IR_DRONE_098
(0.76) and IR_AIRPLANE_003 (0.71) are missed too, though one mechanical word foretells most of each. Tried and not used:
each of 711 real words with no known clock fitted by a Markov chain of order 1-4 and drawn again. Order 1 passes 0.003 %,
and orders 2-4 pass 0.5-1.2 % at 0.85, but the rate comes from a few dozen words: chains fallen into a loop on a rare
context, and Svanström clips near 20 on 30 that may be cadences themselves. It could not tell, and sets nothing. The best
mechanical word's share of frames missed was tried as a label free of the balance; it finds fixed clocks, but PR34
reads 0.5 and flyer 3 0.1.

**What it cannot tell.** A word that a cadence and the GOP's places explain equally well -- an encoder holding every P
frame of a short GOP, or a source cadence in step with it, its I frames fresh -- is taken for a cadence. A source whose
pictures land on the grid unevenly (PR44: most pictures shown two frames, some one or three, about 15 a second) is not
a cadence: its top is the grid's, and its held frames are missing samples. The test is over the whole stretch the
stage reads, so a stretch whose source changes its rate partway is not balanced and keeps the grid's top.
`integrity`'s cadence test (an object frozen on a repeated frame, doubled on the catch-up) and `layers`' repeating
windows (a pair between catch-up steps not measured again) read repeats wherever they fall and set no rate; they are
unchanged.

**A cadence broken by a burst (IDEAS.md Dx6; added 2026-11-13).** The balance is read over the whole word, and a burst
of holds inside a cadence spoils every window over it. IR_DRONE_059 of the labelled set is a 20-a-second source on a
30-a-second grid: its word is `010010...` through 316 pairs of frames, but for 18 frames of extra holds from its 65th
frame and two holds misread. It read 0.843 against the line's 0.85 ("more evenly than at random"), kept the grid's 12
Hz, and its holds' own rhythm, 10.00 Hz = a third of the frame rate at 15 % of its brightness, was named a bird's beat:
the set's false alarm of record. The same source runs through the set: IR_BIRD_043 (0.98), IR_DRONE_151 (0.90) and
IR_AIRPLANE_030 (0.86) pass the line whole; IR_BIRD_032 (0.83), IR_DRONE_098 (0.78, the same false beat at 9.99 Hz, 4.8
%, under the floor), IR_HELICOPTER_044 (0.69) and _048 (0.59) are the same cadence, more broken.

A word short of the line that holds three blocks or more is now read again block by block (`flicker.cadence_blocks`):
blocks of 60 frames or a little more, as many whole ones as the word holds with every frame in one, each read as a word
is (least balance 0.85 or more, above the 99th percentile of random words of its share and length, a tenth of its
frames held). Where more than half the blocks are a cadence the word is one (`pictures.holds` "cadence"), the source's
rate from the median of those blocks' slopes, the band's top lowered as for any cadence; `pictures.blocks` says how
many of how many, with each block's balance. Its period is not named (the word is not mechanical to the frame), and the
GOP's places are asked as before. Sixty frames is the shortest stretch a beat is heard on and the shortest the line was
set on. "More than half" is a choice: the band is lowered for the whole track, so most of the track has to be on the
slower clock (the least count that chance allows would be two blocks of five). Both are judgement in what they ask;
what they cost is measured:

*The null* (2026-11-13; the families the line was set on, drawn again: random words; held in runs of mean 2, 3, 5 and
10 frames; held by place in GOPs of 5, 12 and 30 frames, regular and varying, the chance flat, rising or a B pyramid;
the Galileo flyers' two tables; fifteen shares from 0.1 to 0.8, eight lengths from 180 to 3,000 frames, 2,000 words a
cell, each read as the stage reads it, before the GOP's places). The share of words called a cadence by the blocks
where the whole word is not one, at the worst cell:

| frames | random | in runs | by GOP place | flyers' tables | by the whole word (the rule before) |
|---|---|---|---|---|---|
| 180 | 0 | 0.10 % | 0.05 % | 0 | 0 |
| 240 | 0 | 0 | 0 | 0 | 0 |
| 300 | 0 | 0.05 % | 0.05 % | 0 | 0 |
| 450 and up | 0 | 0 | 0 | 0 | 0 |

Seven words of 4.24 million, in six cells of 2,216. At 180 frames: two of 2,000 held in runs of mean two at a share of
0.65 (M3's own worst cell), and one of 2,000 in each of three cells (runs of mean three at 0.75; a GOP of 5, flat, and
a GOP of 12, a pyramid, at 0.70). At 300 frames: one of 2,000, twice. (A first draw of the 180-frame cells, cut short by
a shutdown, had three of 2,000 in the runs-of-three cell, 0.15 %, and one word in 2,000 past the whole word's line.)
A single block is a cadence in at most 2.3 % of them (runs of mean two; 1.9 % by GOP place, 0.1 % at random): under
the line's 5 %, and the word needs more than half its blocks. So the block reading adds at most 0.15 % to the false
alarms at 180 frames and nothing found from 450, where the rate the line was set to is 5 %.

*The other side: a cadence broken* (200 words a cell: a mechanical word at a random phase, with a burst of extra holds
at a random place, frames misread at random, or both). The share called a cadence, by the whole word (the rule
before) / now, %:

| source on a 30-a-second grid | frames | intact | a burst of 20 | a burst of 60 | 20, and 1 % misread | 20, and 2 % misread | 2 % misread |
|---|---|---|---|---|---|---|---|
| 20 on 30 (one in three held) | 180 | 100 / 100 | 0 / 81 | 0 / 8 | 0 / 58 | 0 / 45 | 79 / 85 |
|  | 300 | 100 / 100 | 0 / 100 | 0 / 100 | 0 / 87 | 0 / 60 | 85 / 90 |
|  | 3000 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 |
| 25 on 30 (one in six) | 180 | 100 / 100 | 0 / 78 | 0 / 2 | 0 / 54 | 0 / 35 | 66 / 80 |
|  | 300 | 100 / 100 | 0 / 100 | 0 / 100 | 0 / 76 | 0 / 49 | 59 / 74 |
|  | 3000 | 100 / 100 | 100 / 100 | 0 / 100 | 94 / 100 | 8 / 92 | 73 / 96 |
| 10 on 30 (two in three) | 180 | 100 / 100 | 33 / 95 | 0 / 28 | 9 / 70 | 2 / 48 | 78 / 88 |
|  | 300 | 100 / 100 | 100 / 100 | 0 / 100 | 56 / 95 | 16 / 67 | 87 / 94 |
|  | 3000 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 |

A single burst of 20 or 60 held frames in 300, the drone's own kind, was never a cadence by the whole word and now is
every time; at 180 frames a burst takes one of three blocks and the reading needs the other two, so a burst of 60
(a whole block and part of another) leaves it at 2-28 %. Over 3,000 frames the whole word mostly carried the burst
already. Frames misread at random are helped less (2 % misread at 300 frames: 59-87 % to 74-94 %), as a misread frame
spoils every block it falls in alike.

*On the saved words* (the 432 labelled tracks, the 27 controls, the 31 reference objects: 170 with a tenth of their
frames held). Four change, one track twice: IR_DRONE_059 (4 of its 5 blocks; the control `sv_drone_059` is the same
track), IR_BIRD_032 (3 of 4) and IR_DRONE_098 (3 of 5), each at 20.0-20.2 pictures a second, the top 8.0-8.1 Hz. The
nearest that stay: PR44's reference object (2 of 5: a bird at 3.06 Hz whose frames repeat one in two, never quite in
step; the scatter case above), IR_HELICOPTER_044 and IR_AIRPLANE_069 (2 of 5), IR_DRONE_023 (1 of 5). The Galileo
flyers have no block that is one (0 of 15, 0 of 6). With blocks of 90 frames the drone is a cadence in 2 of 3 and
IR_DRONE_098 in none of 3; with 120, neither.

*On the labelled set, judged again from its saved curves* (`tools/controls/summarise.py --rejudge`, which reads the
held word again since 2026-11-13: `run_set.pictures_again`), against main 4847926 judged again the same day (the
revision of "a beat that comes back" in it, and none of this): 3 of 432 rows move, under both rules. IR_DRONE_059: a
bird, named, 10.000 Hz at 15.4 % becomes no beat (the continuum null's p 0 to 0.84). IR_DRONE_098: a bird's call at
9.988 Hz, 4.8 %, not named, becomes no beat. IR_BIRD_032, a bird named at 2.04 Hz, 11.5 %, keeps its call and its name
with the top at 8 Hz (its continuum p 0.0015 to 0.003). In the rates of section 44: non-birds called a bird 18 to 16 of
307 under the stage's rule and 25 to 23 under the paper's, drones 3 to 1 and 7 to 5 of 168; non-birds named 3 to 2 of
307 (the stage's rule; drones 1 to 0, distant non-birds 1 to 0 of 100). Birds called (31 and 30 of 125) and named (30
and 27) are as they were: no bird of the record loses a call or a name.

*How it fails.* (1) A clip cut from two sources, most of it at the slower one, has its top lowered through the faster
part too. (2) A word broken in more than half its blocks stays "uneven" and keeps the grid's band: IR_HELICOPTER_044
and _048 are 20-a-second sources read so, and a rhythm at a third of the frame rate could still be heard on them (none
is: 2.2 and 4.8 Hz, no beat). (3) Under 180 frames there are too few blocks, and the whole word's balance decides as
before. (4) What the line does not cover (above) it does not cover block by block either: an encoder holding 0.9 or
more of a short GOP's P frames passes block after block.

**What is said of frames that are nearly the same (IDEAS.md N7; 2026-11-13).** `pictures` compares whole frames. An
encoder that copies a still sky leaves most of a frame the same as the one before while the object's own picture is
new: the documented misread, 0.10-0.18 of frames on the Svanström set and far more on the Galileo cameras' HEVC. On the
flyers, the frames read as held are not held where the bird is. Flyer 4: 60 % of frames read as held; on them the box
about the bird changes by 7.1 grey levels (7.2 on the others) and its centroid steps 1.77 px (1.76), never under 0.38.
Flyer 5: 31 %; 12.5 grey levels (15.0) and 2.35 px (2.53), never under 1.6. Flyer 1, a slow bird (0.3 px a frame): 64 %;
1.25 grey levels (3.2), and on 15 % of those frames its box hardly changes. The whole frame's change on them is
0.05-0.06 grey levels against 0.2-1.0. No number is wrong for it: holds outside a cadence leave the band at the frame
rate's. The stage's line was: it said "the video holds pictures in runs (64% of frames repeat the one before), not in a
cadence: they are missing samples, not a slower clock". It now says what was measured and the two things that make
it: "64% of frames are nearly the same as the one before, more evenly than at random, not in a cadence. A held picture
does that. So does compression that copies a still scene from frame to frame, while the object's own picture is new.
Either way the video's clock is its frame rate, and a beat is heard up to 24.0 Hz". A trap that stays: those frames
are still left out of the Lomb-Scargle periodogram beside the stage's own tests (`held_k`), so on such a chain that
reading works with a third of the object's samples: a loss of power there, not an error, and not changed here.

## 36. A farthest range: `--range-max` (added 2026-10-30)

`--range` takes a value, and what a display often gives is a limit: a camera that looks down has the ground behind
whatever it sees, and a data bar's slant range says how far that is. `--range-max` is that limit, in meters: a row of
`stages.KNOWN`, so `run`, `report CASE`, `kinematics` and the Measure form all have it, and it can be given afterwards;
in the plain form, on the segment step and the report card, "Or, if you know only a limit: nothing beyond". It takes the
paths `--range` takes, and every number comes out as the most it can be: `upper_bound_m_per_s`, omega R at that range;
the size p R / k; R in the ledger `bounded`, beside the horizon's and the haze's ceilings (the nearest of them wins;
`Case.range_bounds`), so the admissible region stops there (§33, "the farthest range given") and the figure of size and
speed greys what lies beyond. Nothing changes unless it is given, and it cannot be given with `--range`.

A spot size is no limit on a size: the size is said as a limit only from a width given (`--size-px`) or measured, for the
size a track was followed at is a scale for finding it, and on a track given with no size it is the default, 9 px (PR051's
drift, 53 px wide at half its peak, would have read "at most 0.36 m"). The speed's limit stands without it.

An average is no limit on a speed that changed, so a track that changed its speed is said twice, on average along its
path (the line's rate or the band's speed along the path, the larger; until 0.4.2 the band's net velocity, which is a
displacement over the time and no limit on a path that doubles back: PR077's object 1 ran near 150 px/s along a path
whose net was 5.7, §32) and at its fastest (`upper_bound_fastest_m_per_s`, the band's fastest, §32; on a track too short for a band that is not
uniform, its largest step between frames, `kinematics.fastest_rate`). The label goes by the fastest: under the speed of
sound "Subsonic motion", as for a thing of known size, whose limit is the same arithmetic; at or past it "Indeterminate,
range needed", for a limit past the speed of sound says nothing of the speed. There is no route from a limit to
"Supersonic motion".

**What it is a limit on.** omega here is the rate in the picture (`omega = v_px f / k`). That is the turn of the line of
sight only for a camera that is not turning. A camera that holds the ground from a moving aircraft is turning at
V / R_g (V the aircraft's speed across the ray, R_g the ground's range), and the rate in the picture, against the ground
point G on the same ray, is

    w = (v - V) / R + V / R_g,    so    v(R) = w R + V (1 - R / R_g),

for each of the two directions across the ray, v the object's velocity across it over the ground. Three things follow.
(1) w R, the number `--range-max` limits, is the object's speed against the line of sight as it was held, at its own
range; it is the speed over the ground at R = R_g, and at nearer ranges the speed over the ground has (1 - R / R_g) of
the aircraft's in it, up to all of it. So over the ground the limit is a limit only at the ground: where V and w point the
same way, w R_g is the *least* the speed over the ground across the ray can be, not the most. (2) Relative to the
aircraft the speed across the ray is (w - V / R_g) R: it does fall with the range, and its limit is |w R_g - V|, not
w R_g. (3) Between two stretches under the same hold the V term cancels, so a *change* of rate, as at a release, is a change
of velocity across the ray in every frame: Delta v = Delta w R, and that is limited by Delta w R_g whatever V was.
The report says so in a sentence ("against the line of sight as the camera held it"), and does not call the limit a speed
relative to the platform.

**On PR051** (the upload, the 4X field of §20; `camera --scene` and `tests/test_reduction.py`). SLR, 22.45-22.61 NM, is
the boresight's ray on the terrain model (the laser safed), so 41.7 km is the farthest anything seen against that ground
can be. In square pixels, k 18000 px/deg:

| stretch | rate | at 41.7 km |
|---|---|---|
| held, 4201-4437 (3.9 s), the object against the ground | 2.7 square px/s, 0.00015 deg/s | 0.11 m/s |
| the drift, 4439-4549 (1.8 s), the line | 142 square px/s, 0.0079 deg/s | **5.7 m/s** |
| the drift at its fastest, a step the band read | 788 square px/s | 32 m/s |
| the dash's centroid, 4553-4567, its line | 1213 square px/s, 0.067 deg/s | 49 m/s |
| its fastest stretch, 4561-4567 | 1990 square px/s, 0.11 deg/s | 80 m/s |
| its fastest step, 4563-4565 | 2990 square px/s | 121 m/s |
| the last of the drift to the dash's end, 4549-4567 (0.30 s) | 2540 square px/s | 103 m/s |
| the jump, 4549-4553 (two pictures) | 7390 square px/s | 299 m/s, if a jump is a motion |

All under the speed of sound at the ground's range, and the drift's and the dash's rates are not one number each: the
drift goes in five steps (4447, 4505, 4507, 4517, 4545), and the dash's centroid is the centroid of a streak 30-80 px long.
Over the drift the object is 53 upload px wide at half its peak, about 46 square (`forensics.point_blur`; a point on this
clip is 6.2 px, so it is resolved, none of the fits clipped), 82 in the drift's first half and 33 in its second: at most
1.9 m across at the ground's range, 2.9 m and 1.1 m by halves. Read in the upload's own pixels with the width's scale on
both axes the drift is 4.8 m/s: the upload stretches the 4:3 sensor to 16:9, so a pixel up the picture is a third wider
in angle than one across it, and most of the drift is up the picture. The camera holds the ground while the aircraft
crosses the ray at about 54 m/s (0.074 deg/s; the data bar's ACFT, read by eye, 60.7 m/s on 256 deg, the ray on 013), so by (1) above the drift's speed over the ground is 5.8 m/s if the object is
at the ground and more if it is nearer (30 m/s at 20 km, 48 at 5 km; the aircraft's motion and the drift both go left), and by (2)
its speed relative to the aircraft is at most about 52 m/s; by (3) what 5.7 m/s does limit in every frame is how much the
object's velocity across the ray changed when it left the held line. A thing at rest in the air between the camera and the
ground would drift to the right, at 57 square px/s at 40 km; the drift goes up and to the left, and while the gate held,
the object kept to the ground to 2.7 square px/s for 3.9 s, which for a thing at rest puts it within about 100 m of the
ground along the ray.

**How it fails.** It is a limit only where the limit is one: "the ground behind it" fails for a thing seen against the
sky, or above the horizon. The rate is the picture's; a camera that turned against the scene needs `camera --scene` or
`layers` first. On a stretched copy give `run --pixel-aspect` (§40; `camera`, `slew` and `horizon` took it before `run` did), or
a thing moving up the picture reads up to a quarter low. An extent that is a bloom's is a
limit on the bloom. Motion along the line of sight is not bounded at all, here as for a thing of known size.
Tests: `test_a_farthest_range_is_a_limit_through_the_paths_a_range_takes`, `test_pr051_s_drift_and_dash_against_the_ground_as_the_farthest_range`
(test_reduction), `drive_known_afterwards` (test_cli: `report --range-max` is `run --range-max` to the last digit, `--forget
range-max`), `drive_what_is_known` (test_gui: the form, refused with a distance, kept for the video).

## 37. The lens's radial term: `--lens-k1` (added 2026-10-30)

**What it answers.** The projective test (§33) and the turn number are a pinhole's: a straight line at a steady speed is
straight and steady in the picture only if the lens draws straight lines straight. A wide lens does not. Held to a fixed
50° thermal camera watching airliners whose range is known (session 11, private), a path known to be straight and steady
missed by 1.4-1.8 px on approaches and 1.5-6 px on crossings when drawn through the camera's fitted barrel, and fitted
exactly through a pinhole, while the report could only say "the camera's motion, or the object's own". This section gives
the lens to the test where it is known, and asks of a miss where it is not whether a lens alone would account for it.

**The second term** (`--lens-k2`, added 2026-11-13; IDEAS.md N6). Where a calibration has it, x_d - c = (x_u - c)
(1 + k1 r² + k2 r⁴), counted as k1 is. The Galileo Project's ring cameras have k1 -0.51 to -0.58 and k2 +0.5 to +0.95.
Read through k1 alone, a rate near their frame's edge came out 12 % high against the aircraft's triangulated speeds
(more than 300 pixels from the centre; section 53), and a drawn crossing 14-21° off the axis is 4.0 % off in scale; with
k2 it is right to 0.02 %. The fold is where 1 + 3 k1 r² + 5 k2 r⁴ first reaches 0: a second term of the other sign, as
these lenses have, may keep the lens from folding at all. With k2 0 every number is the one-term lens's, to the last bit.
Everything below is written for k1 alone, and holds for both terms with `lens.radial` and `lens.slope` in place of the
brackets.

**The model** (`lens.py`). One radial term, the first of the usual calibration (Brown's; OpenCV's k1):

    x_d - c = (x_u - c) (1 + k1 r²),    r = |x_u - c| / f

x_u is where a pinhole of focal length f (pixels per radian at the axis) draws the point, x_d where the lens does, c the
frame's centre, and r the tangent of the angle off the axis. **k1 is counted in focal lengths**, so a calibration's k1 is
entered as it is; below 0 a barrel, above a pincushion. That makes k1 need f: a graticule gives f directly, and a field
of view F across W pixels gives it *through the lens*, W/2 = f t (1 + k1 t²), t = tan(F/2), because F is the real angle to
the frame's edge. 50.2° over 640 px through k1 -0.43 is 754 px/rad, where the camera's fit found 750-757; a pinhole says
683. One k1 is one focal length, so `--lens-k1` is refused with `--fields`, and with neither `--fov` nor `--graticule`.
The one-term model folds back at r² = 1 / (3 |k1|); a field of view past that is refused, and a point past what the lens
can reach is left out of the track as a lost point would be. The centre is the frame's: an offset axis is not modelled.

**What is drawn through it.** `undistort` is the exact inverse, so the track is drawn back to where a pinhole would have
put it (`lens.drawn`) at the *input* of `projective.fit` and `projective.turn`, which are the same functions with and
without a lens, and with k = f so the aspect angle and the secants are exact. The width for the turn is multiplied by
how much the track grew (`lens.grown`). The rate, the speed band and the smear stay the picture's, in pixels a person can
count on the video. **k changes meaning a little:** with a lens it is the lens's own scale along the track (`lens.along`,
the track's length in the picture over the angle the line of sight swept, on the means of twenty stretches, since frame
to frame the steps of a slow track are mostly jitter, which goes every way and mixes the scale across a radius with the
scale around it: that read 3-5 % low on the airliners), and f is kept beside it (`scale.fields.lens`). So every use of k
downstream has the local scale. On the 15 approaches k was 1.000-1.002 of the true scale along the track and on the 4
controls 1.002-1.008, where the pinhole's 683 px/rad was 0.908 and 0.93-1.01. The camera, horizon and focus steps keep
their own k, a pinhole's over the frame: a report through a lens can show two scales some 5-10 % apart.

**What a known lens changes.** Drawn: an approach whose bend sits under the jitter *passes* through a pinhole, at the wrong
time (T 23.85 s of 29.48 drawn, k1 -0.43, 0.15 px jitter), and through the lens gives 29.52: no verdict shows that 19 %.
Crossings near the frame's top edge fail through a pinhole (3.6-4.9 px rms, a free quadratic 0.5-1.25) and fit drawn back.
Held to the known ranges (the camera's own k1, -0.42 to -0.45): of the four controls, one that failed now fits, no closing
seen, 2.2 jitters (0.45 px rms; it had failed at 1.35); a crossing through the frame's centre goes from 6.6 to 0.7 px and
still fails, as does one that really turns gently, 7.2 to 2.2 px; a 2-s track fits either way. **All 15 approaches still
miss** (7-16 jitters; median rms 2.5 to 2.2 px, better on 10 of 15), rightly: they were slowing, by 1.0-1.8 px over the
track, and a real link wanders on a grown aircraft. T, which the report withholds on a miss, rises 2-4 % through the lens, so its
ratio to the truth goes from a median of 1.02 to 1.06: the pinhole's nearer number was the lens's bias cancelling the
slowing. A k1 wrong by 0.02 moves the misfit by at most 0.3.

**M1's null, with the lens in and out** (session 9's drawn tracks, §33: all 32 cases, 400 draws each, on the same seeds and
noise; 32,000 fits). Through a pinhole at most 4.8 % past NUGGETS, as before (`fit` is unchanged). Through k1 -0.43 and drawn
back, at most 4.8 % as well, but that says little of a lens, because M1's far path stays within 0.1 of the axis (its
misfits move by at most 0.23). So sixteen more cases, the far path 0.45 off the axis, near a wide frame's corner, and there
drawn back **the null failed: 10.2 %** (60 points, φ 0.9), 5.6-6.0 % at φ 0.6 at every length, where the same path through a
pinhole gives 4.8 % and 2.8-3.8 %. The excess is the lens's. Drawn back the jitter is stretched, across a radius by 1 / (1
+ 3 k1 r²) and around it by 1 / (1 + k1 r²), so that one coordinate holds most of it, and a low reading of that
coordinate's nugget has no other beside it to pool with. The jitter lives in the picture, the same each way, so
`lens.carried` reads it there, both coordinates pooled, carries it by the stretch's mean over the track, and gives that
to `projective.fit` as its band's nugget, of which the test takes the larger as ever. On the ten off-axis cases that were
near or past the line, 400 draws each, it comes to at most 4.3 % (the same draws: φ 0.3 at most 2.5 %, φ 0.6 4.3 %, 3.5 %, 1.8 %,
0.2 %, φ 0.9 4.0 %); the other six were at most 1.5 % before it, and a larger yard can only lower them. The first 32 cases
were not rerun with it, for the same reason.

**With no lens given: could one alone be all of a miss?** A miss is asked (`lens.could_be`): the track is drawn back through
every radial term the model allows, as k1 / f², which needs no focal length (`REACH`: the frame's corner at the fold, -33 %
for a barrel; a pincushion is held to the same k1 / f² by judgement), the model fitted on the drawn track and drawn
forward again so that the miss is read in the picture where the jitter is, and where the best comes within NUGGETS of the
jitter the test itself is run on that drawn track. On its own that does not tell a lens from a curve: real curves are
rescued too (62 of 693 misses, below). What does is **the shape**: the lens's term must also beat a free quadratic, which has
as many parameters. A lens's bend is cubic along the track and tied to where the track is in the frame; a real curve is
what a quadratic is good at. The words ("or a lens bent it: one that moves the frame's corner N % in accounts for the
whole miss") need both (`projective.lens_could`). Drawn, tracks 100-400 points long at random places, 80 px or longer, 0.1-0.5
px jitter, of those that missed:

| drawn | missed | rescued | and beats the quadratic: the words |
|---|---|---|---|
| straight and steady through k1 -0.43 | 94 | 94 | 91 |
| through k1 -0.20 | 32 | 32 | 32 |
| steady push along the path, 0.1-2 m/s² | 17 | 4 | 0 |
| a steady turn of 3-90° | 283 | 24 | 3 |
| a sway across the track, 1-8 px | 245 | 13 | 0 |
| a smooth wander of 1-6 px | 148 | 21 | 7 |

So the words are said of 98 % of a lens's misses (123 of 126; 93-99 %, 95 % interval) and 1.4 % of real curves' (10 of 693;
0.8-2.6 %), the worst kind, wander, 4.7 % (2.3-9.4 %). Most straight steady tracks through a barrel do not miss at all: at
k1 -0.20 one in ten, so the words are rare where they are right. **On the 44 recorded tracks that miss, no lens in reach
rescues one**: the words appear on no reference report. Of the known-range tracks they are said of the crossing through
the frame's centre, at -22 % (the lens is -20 %), and of none of the approaches, where a lens is only part of it, nor of the
two other controls, one of which fits through the true lens: a test of a lens *alone* can only say that much.

## 38. The checklist under the conclusion (added 2026-11-01)

A tester asked for a report "that even an undergraduate student can understand", and the maintainer for "a checklist
form that lists off each test, in a nicely formatted table, with a simple answer of the test result" in place of the long
paragraph at the top. Measured first: PR135's conclusion and its paragraph were 85 % at the plain-words tier 3 of the
simplespeak skill and 93 % at its school-leaver's tier 4, so the words were mostly fine; the sentences ran 40 words on
average, the longest 143. A reader was being asked to hold every number and its caveat in one sentence.

**What the report now has** (`report.Case.checklist`, `CHECKS`, `ANSWERS`). Under the conclusion's sentence, a table of
three columns: what was checked, the answer, and why in a line. Each row is one test, asked as a question in plain words
and answered in one of five words:

| answer | means |
|---|---|
| Yes / No | the test decided |
| Partly | the test decided part of what was asked: a beat in one stretch only, or too faint to name a bird; a speed bounded but not found |
| Can't tell | the test could not decide on this video. A verdict, never dropped for a "No" (the package's third rule: a test that cannot decide has not passed) |
| Not yet | the person's part is still to do: the track sheet not looked at |
| Consistent / Inconsistent | integrity's row only (2026-11-07, section 47): agreement with the camera's own picture, from checks never tried on a real insert |

The rows, in a fixed order, and what each reads:

| row | reads | Yes | No | Can't tell / Partly |
|---|---|---|---|---|
| repeated frames or sudden changes of brightness | `survey` | so many of each | every frame new | -- |
| did the camera move | `layers`' held-still share over about a second (`still_again_share`) and its no-power where the picture held still on screen (`Case.behind_held_still`) | the background moved across the picture (10 % or less of the pairs held) | never: a picture that held still on screen is the step's no-power, not a still camera (0.4.1 answered No there; 0.4.2 does not) | Can't tell wherever the picture behind the object held still on screen -- the step's no-power, above half the pairs: a camera following the object over an empty sky and a still camera over a slow scene both give it, and the step cannot tell them apart -- with the share that moved where there is one; Partly: held in half the pairs or fewer, moved in the rest |
| does the object move against the background | `Case.rate` | the rate, against the background or across a picture that held still | under half a pixel a second | Can't tell where the rate is the picture's and the camera moved: the rate against the background was not measured |
| straight at a steady speed | the speed band's `constant`, the turn's `turned`, the loop | the band held, the path straight | the speed's range along the track and the bend; "(the camera moved, so some of this may be its motion)" where it did | Can't tell under the frames a band needs |
| coming toward the camera | tau from its size (section 33), the projective fit, the depth bound, the size's trend | its size grows or its path fits an approach, with the time to the camera's distance | the depth bound, under the hypothesis | Can't tell where its size held, could not be read, or its path fits only roughly |
| beats as a wingbeat would | `flicker`'s beats, by the headline's rule (section 13), and its power (`analytic`) | the rate, the object's own; a flock's members each their own | no rhythm of its own on a track that could have shown a bird's (`Case.beat_power` at most BIRD_FLOOR, section 47); or a beat outside the wingbeat band, said | Can't tell where the picture shakes at that rate, where the track is too noisy to show a bird's beat, or where the stage refused, a peak measured or not (section 47); Partly in one stretch, or under BIRD_FLOOR |
| could something other than a bird beat like this | the look-alikes (section 9) | always, where a beat is the object's own: a tumbling body, a blinking light; a flame's band or a rotor's look where marked | -- | -- |
| flashes in a train | `flicker`'s blink (section 19) | the flashes a minute and the rule they meet | no train | -- |
| a single thing | `groups` | one point on most frames | so many things moving together, keeping their places or changing them | -- |
| anything moving with it | `tether` (section 6) | the companion, its distance in object widths, its swing or its steady angle; a fellow member | nothing within the ring | Can't tell under the frames it needs |
| moves through what is round it | `comotion` | MOVES THROUGH | CARRIED | INCONCLUSIVE, NO POWER |
| consistent with the camera's own picture | `integrity`'s object tests (section 2) | Consistent: the checks that could decide pass, the rest said | Inconsistent: checks that flag it, named | Can't tell where none could decide; each decided answer says no check has been tested on a real insert (section 47) |
| a real speed and size | the four unknowns (ROADMAP 0.4 objective 6) | the speed and size, "a guess" where k is | what it needs: the field of view, the distance | Partly: a bound from a thing of known size or a farthest range, a least speed at a given distance, or a turn rate with no distance |
| a person picked out the object | `identified_by`, the track stage's `placed_by` (section 47) | marks placed by hand, or a track file that says it was linked from them | an agent's, typed, the computer's suggestion taken, or snapped marks, or a track file that says so: "every measurement of the object rests on that choice" | Can't tell where the track file says nothing of who placed it (`run --track`) |
| a person checked the track | `verify`'s `reviewed`, and how (its result's "yes (how)") | the sheet looked at, and when: shown before anything was measured, after the report, or said with `run --i-looked` before this run drew its sheet (section 47) | -- | Not yet |

A row whose stage did not run has no row: the table says nothing it did not check. The camera's row agrees with the
first line (2026-11-02): where that line says the object moved "as the camera held it", the row says whether the camera
moved is not measured, in the same words, and not "No" -- on ten of the fourteen reference case files, PR135's six birds
among them, 0.4.1 had answered No from the held-still share, which is the step's own no-power. The paragraph that was at the top
is folded under the table (`<details>`: a link on the window's report page, a fold on GitHub, expanded in the PDF), not
gone; the conclusion's sentence stays first, so the exercise pages, which quote it, stand. The window's report card has
the same rows above its numbers, the answer in a word and why in the tooltip; `mcdonald run --json` carries them as
`results.checklist`. The rows are read from the stages' fields, as the conclusion and the bottom line are, so a case file
from an earlier version gets its checklist when its report is opened or written again. Measured: the rows' own words are
97 % at tier 4, 12 words a sentence; test_gui holds them to the window's plain words (no px, clip, velocity, provisional).
What the checklist is not: a grade (S17), reason codes ranked by their weight (E7), or Louange's items (F56); the first
two are section 47.

## 39. Two nulls read as the data is, and the rate each really holds (B1, B5; added 2026-11-02)

The 0.4.2 rule (Jacob, 2026-10-30): every rate a report states is the rate measured on a null, and where the stated and the
measured disagree, the words say the measured one. The biology survey (2026-11-01) found two of the flicker stage's rates
that were not what the code did, each confirmed by an independent check; both were rebuilt here before anything changed.

**The continuum null, read as the curve is (B1; `flicker.continuum`).** The paper's null (§10) holds a peak against noise
curves shaped to the curve's own power-law continuum. The curve it is handed has been through `deviation`, a running mean
over 0.5 s, which is a filter (`flicker._gain`: 0.70 at 1.5 Hz, 1.0 at 2, 1.22 at 3, 0.87 at 5, ripples of a tenth beyond);
and its own strongest is left out of its own power-law fit. The noise curves had been through neither: drawn from a power
law fitted to the filtered spectrum and never filtered, and every one fitted on the curve's mask, its own peak in its fit.
So the null was quieter at 2-3 Hz than the data, and more permissive everywhere. Measured with the null true, curves drawn
through the stage's own path (a brightness curve, `deviation`, `continuum`; 1,000 curves a cell, 1,000 noise curves each;
`scripts/c1_null.py` of the 0.4.2 notes), the share under 0.01, before -> after:

| curves with no line | 90 frames | 150 | 300 | 600 |
|---|---|---|---|---|
| white | 5.4 -> 0.8 % | 5.2 -> 1.2 % | 6.2 -> 1.2 % | -- |
| pink (f^-0.5) | 5.0 -> 1.1 % | 4.9 -> 1.2 % | 5.7 -> 1.4 % | 6.9 -> 1.0 % |
| red (1/f) | 3.4 -> 0.8 % | 3.6 -> 1.0 % | 4.9 -> 1.3 % | -- |
| a random walk with grain | -- | 6.1 -> 2.1 % | 6.4 -> 1.8 % | 7.1 -> 1.7 % |

Now the power law is fitted with the filter's gain divided out, the noise curves are drawn from it and taken through the
same running mean, and each is fitted with its own strongest left out (by one least-squares pass with a mask a row, so it
stays vectorised). On real curves with nothing in them -- the reference case files' background apertures, 112 of them --
the share under 0.01 goes from 6 (5.4 %; 14 under 0.05) to 2 (1.8 %; 6 under 0.05, and neither of the two is noise: a
neighbour's beat in each), and noise of each one's own continuum through the running mean from 5.1 % (13.4 % under 0.05)
to 0.6 % (5.1 % under 0.05). The 99 % level on a 150-frame curve is about 5.2 where it was 4.2. `CONTINUUM_P` stays 0.01;
it now means 0.01 on white, pink and 1/f curves, and about 2 % on a random walk with grain, the one kind of curve
steeper below LOW than any
power law fitted in the band -- the drift test's trap, which the stage's own rule keeps the drift test for. The
observed statistic -- the ratio at the curve's strongest over its own power law -- is unchanged, so every reference
object's ratio stands; its `p` and `needed99` move, in every case file's continuum row. Of the 28 reference lines
(Table 1 and PR135, every object with a continuum row, read over the stretch that row records, `scripts/c1_real.py`),
20 stay under 0.01 and five leave it: PR077 object 2 (ratio 4.90 at 10.08 Hz, p 0.001 -> 0.025), PR097 objects 3 and 4
(5.34 and 5.67 at 6.9 Hz, 0.000 -> 0.014 and 0.011), PR099 object 2 (4.81 at 6.74 Hz, 0.004 -> 0.022) and PR141's infrared
object (4.88 at 8.31 Hz, 0.008 -> 0.024); PR097 object 8 (5.52 at 2.28 Hz), which the survey's check had leaving, stays
at 0.008 over its recorded stretch. What that does to each headline, under the paper's rule the case files use and under the
stage's, is in the 0.4.2 notes and the CHANGELOG; the stage's whole-track rule does not use this null, and the one-stretch
rule (§13) is stricter by it, not looser.

**The drift test's real rate (B5; `flicker.drift`, `DRIFT_RATE`).** The stage's whole-track rule keeps a beat only where
it stands over its own slow wander further than 99 in 100 curves drawn of the wander and jitter fitted to its spectrum.
That rate holds on drawn curves. On empty apertures in real frames it does not: the genetic survey's null census (paths
that follow nothing through 116 release videos, three stretches of 150 frames each, two paths a stretch at 0-3 px a frame,
four apertures beside each, all judged by `whole_passes` as an object is; 3,092 apertures) and the check's own harness on
13 PURSUE videos (286 apertures; both rebuilt from their saved rows, `scripts/` of the notes):

| empty apertures, by where the strongest lies | n | pass the drift line | pass the whole stage rule |
|---|---|---|---|
| 1.5-4.5 Hz | 2,723 | 252, 9.3 % | 11, 0.40 % (all at 1.5-2.8 Hz) |
| 4.5 Hz and up | 369 | 16, 4.3 % | 0 (under 1 %) |
| all, the census | 3,092 | 268, 8.7 % (by tranche 4.7-13.0 %) | 11, 0.36 % (stated: 0.15 %) |
| all, the check (13 PURSUE videos) | 286 | 21, 7.3 % | 2 |

The cause is the curve model's shape, not how the null is read: curves drawn from an aperture's own fitted wander and
jitter pass 1.3 %, where a real curve's power runs 1.4-1.5 times the fit at 1.5-4.5 Hz and 0.8 above 9 Hz -- a hump of
scene texture swept through the aperture (apertures moving 0.7 px a frame or more pass 13 %, slow ones 3-5 %), and each
aperture's hump is its own (dividing by the mean misfit learned on the other videos leaves 6.3 %). A small change to the
model was tried before the words were settled (the 0.4.2 notes, `scripts/c5_drift.py`): the jitter given a colour, an
AR(1) grain whose memory is chosen for each curve from 0, 0.2, 0.4 and 0.6 by Whittle's likelihood, the null drawn with
it and each drawn curve read the same way. On the check's 286 empty apertures it passes 17 (5.9 %) against the stage's
21 (7.3 %); the memory lands on the grid's top for a third of them, and the hump is not one shape. Not built: it does
not bring the rate near the stated one, and moving the line to the empties' own 1 % instead (2.8 times `needed`) keeps
14 of the 25 recorded beats, the survey's third refused correction.

So the test stays as it is, a reading with its measured rate written beside it. `DRIFT_RATE` holds the two rates by band,
`drift_rate_said` puts them wherever the line is printed -- the stage's line for each curve, and the finding of a beat the
stage's rule kept ("it stands 8.0 times over its own slow wander, where 8.3 is the line (empty apertures in real frames
pass that line 4 % of the time from 4.5 Hz up)") -- and the words that said "1 in 100" of this test now say what is
measured. The whole rule's 0.36 % against its stated 0.15 % (95 %: 0.07-0.31) is said with it. Not measured: the rate on
2-s windows (the census judged 150-frame stretches), and the rate on an aperture holding a bright thing rather than
nothing (an empty aperture's false rate may not carry over to one).

## 40. The picture's stretch: `--pixel-aspect` on `run` (added 2026-11-02)

**What it answers.** A file whose raster was stretched to fill the frame has two scales, and one k on it reads a
rate across the picture as the stretch times what it is. PR113's file is one: a 720x480 raster shown as 1920x1080 (the
ghost grid of an earlier encode at 9.01 px up and 10.67 across, 4 x 1080/480 and 4 x 1920/720; the method's sound
section already calls it an NTSC tape). The Technical Note's 35.4 px/deg was read up the ladder, and the object crosses
the frame diagonally (-103, +97 px a frame), so `run --graticule 35.4` printed 121 deg/s and a field of 54 deg, where
the picture supports about 103 deg/s and 39 by 30 deg (the single-camera survey's Part 7 §1.1 and its rebuild's rows D8
and S3, the biology survey's Part 5 §2 and its Part 7 row "PR113's aspect", 2026-11-01; measured twice, and again here).
The standards put pixel aspect in the first look at any file (OSAC 2022-S-0031 §6.1.3.1; SWGDE 19-V-003 §6). `camera`,
`slew` and `horizon` took one (§17, §20, §27); `run`, which is every report's path, did not, and its docstring said "no
assumption". This section gives it to `run`, `kinematics` and `report CASE`.

**The model.** a is the width of a pixel over its height as the file draws it (4/3 for a 4:3 picture shown full-height
in 16:9). Square pixels are x / a across and y up, so k, px/rad, is **the scale up the picture**, in square pixels, and the
scale across is k_x = a k. A graticule read up the picture is k as it stands; a field of view F across the frame spans
W / a square pixels, k = (W / 2a) / tan(F / 2) (`--fov-px` over a likewise). A rate (v_x, v_y) in the file's pixels is
hypot(v_x / a, v_y) in square ones along the track's own direction (`kinematics.square_along`), so

    omega = sqrt((v_x / k_x)^2 + (v_y / k)^2) = hypot(v_x / a, v_y) / k,

not v / k: 1 up the picture, 1 / a across, and in between on a diagonal. The field of view is W / (a k) across, as the
graticule's field was extrapolated before (small-angle), by H / k up; from a field given, the vertical one is through the
full expression. A width p in the file's pixels is between p / a and p square pixels (across, or up), so its angle lies
between p / (a k) and p / k, and the first line's distances for a bird, a balloon and a jet span both readings. The rate
in the file's own pixels stays beside it everywhere (the speed row, `v_px_per_s`; the Technical Note's 142 px/frame is that
number). The speed band, the straight-and-steady test, the turn in widths and the smear stay in the file's pixels: a
straight line at a steady speed is one under an affine stretch, and the aspect angle under the hypothesis and the widths
are approximate by up to a (open). The camera stage puts its track in square pixels first, as `camera --pixel-aspect`
did; the horizon step's k is in square pixels; the lens's term and a stretch together are refused (the track is not
drawn back through the lens in square pixels yet). On square pixels nothing moves: a = 1 gives the same fields, word for
word, and a case with no stretch gets no new row.

**Where the number comes from.** `--pixel-aspect A[,FROM]`: the number, and after a comma where it was read --
`symbols` (a circle or ladder the display draws), `scene` (the picture under a roll), or words of one's own -- recorded
as "given", "given, read from the display's symbols", "given, read from the scene", or "given: <the words>"
(`stages.parse_pixel_aspect`). The report's summary, its ledger (k up the picture and across), its bottom line and the
window's card ("Pixels, wide to tall") say the stretch and its source. **Nothing measures it yet.** Three routes exist,
and each was measured on PR113 by the surveys and rebuilt here (`/scratch/mcdonald/c042-2026-11-02/aspect/runs/rebuild`,
the rebuild's own scripts on its extracted frames):

| route | what it measures | PR113 | held to |
|---|---|---|---|
| the file's own raster: the ghost grid of an earlier encode (biology Part 5 §2) | an upscale, and the earlier raster's size; the stretch only with the picture's shape (a 720x480 raster is 4:3, or 16:9 anamorphic) | 720x480 under 1080p; a 4:3 picture filling 1,880 of 1,920 columns predicts 1.31-1.33 | drawn upscales, exact; a false-alarm rate of 9 % for a lone grid match; no ghost does not mean native |
| the scene under a roll: each pair warped by S R S⁻¹ over a trial a, the fixed pattern removed, the a of the best correlation | the scene's picture, free of ground foreshortening at first order | **1.29** (15 pairs of the real fast roll, frames 384-416; 95 % 1.24-1.38; range 1.16-1.45; correlation prefers 1.35 to 1.75 in 15 of 15; a drifts +0.06 over 50 deg of roll) | the same roll resampled across by 0.8 gives 1.028 (1.032 expected), by 0.5704 gives 0.723 (0.736); needs a real roll: 6 of 7 other clips had no power, and the gate is pairs for ≥ 3 × against |
| the symbols: the rotating ladder's rung-to-rung lag traces an ellipse with the roll (a S across, S up) | the symbol generator's drawing | **1.753** (322 frames, 95 % 1.751-1.755; a free conic 1.754, tilt under 0.4 deg); the ring 1.728 (58 frames); **S = 181.25 px per 5-deg rung, 36.25 px/deg** (95 % 36.22-36.28; the two surveys read 36.47-36.5, 0.7 % apart, cause not found) | the lattice resampled by 0.8 gives 1.403 (1.402 expected) |

So the symbols and the scene are two stretches of two things: the display draws its ladder 1.75 wide to tall, and the
picture under it is stretched about 1.3, the 4/3 of its raster. The object is in the scene, and its stretch is the
scene's. Why the two differ (a symbol generator built for another raster; ground-slope shear is not excluded) is open.

**PR113, read with it.** The rebuild's three steps of the transit in the file's pixels, (-93.17, +97.73), (-111.9,
+100.52), (-103.39, +92.97), at 36.25 px/deg up the picture: 124.1 square px a frame and **102.7 deg/s** at a = 1.333,
125.7 and 104.0 at 1.29, 113.5 and 93.9 at the symbols' 1.753, and 141.5 and 119.9 with one k at the Note's 35.4 (the
scatter of the three steps: 5 deg/s, a standard error of 2.9, so about ±6 at 95 % by a normal approximation; the Note's
142 px/frame stands as the rate in the file's pixels; the stage's line through the four points gives 142.3 px/frame and
103.2 deg/s at 1.333, 104.5 at 1.29, 94.3 at 1.753, 117.8 with one k at 36.25). The field over the frame's 1,920 columns:
39.7 by 29.8 deg at 1.333, 41.1 by 29.8 at 1.29, 30.2 by 29.8 at 1.753, where the report printed 54 across (over the
picture's 1,880 lit columns, the surveys' 38.9, 40.2 and 29.6). The condition is that the ladder's vertical scale is the scene's,
which the survey held only to about ±15 % (the ladder against the scene over the upright first pass: slope 0.88, total
least squares 1.16, r 0.78, n 37): that, not the steps' scatter, is the rate's error. Exercise 3 (`docs/exercises/03-pr113.md`)
now gives the marks' scale and the stretch, `report CASE --graticule 36.25 --pixel-aspect 1.333,...`, and quotes what
the report then says; the reference case file is remade by the maintainer.

**Held to drawn clips** (`test_the_pictures_stretch_known`, test_reduction): a track at 45 deg in square pixels drawn on
a picture stretched by 4/3 comes back at its rate exactly, where one k reads it 1.18 times high; a = 1, or none, leaves
the scale and kinematics steps unchanged field for field; the field of view and k both ways; the report's rows and
words; PR113's steps through the stage. `report --pixel-aspect` afterwards is `run --pixel-aspect` from the start to the
last digit, and `--forget pixel-aspect` takes it away (`drive_known_afterwards`, test_cli). The exercise page's answers
are held by `test_golden --exercises 03`.

**How it fails.** The number is given, not measured: a wrong a moves the rate by up to a, and the words say only where
the person read it. Which axis a width was measured along is not known, so sizes are spans. A case given a stretch
afterwards keeps its camera step's rates in the pixels they were measured in, and that step's k says so. A reader for
each route, each held to a null (the ghost grid's false alarms, the scene's gate on pairs that turn, a display's drawn
circle), is the open row: on this corpus the grid is on 13 of 29 PURSUE videos and tells an upscale, not by itself a
stretch.

## 41. The scene under the sensor's pattern: `mcdonald scene` (B3, B4; added 2026-11-01)

**What it answers.** `layers` matches templates, and a pattern fixed on the sensor matches best at no shift at all. On 13 of the 14
reference cases that is its NO POWER: the scene is held still even over 30 frames. This section asks whether those scenes are still, or
only held. It reads a block of 60 frames at once, with no templates, in the way microscopy tells what moves from what stays (the immobile
filter of spatio-temporal image correlation, Hebert, Costantino & Wiseman 2005).

**The reading** (`scene.py`). Each frame's mean out, then each pixel's mean over the block: a pattern that stays put goes, and so does a
symbol. What still flickers hard is masked, and the tracked object's place. Frames are box-reduced to 660 px wide or under. Their Fourier
transforms are kept in a low band (periods of 11-83 reduced px), the coder's 8- and 16-px lattice notched out; only those coefficients are
kept, 6 % of them, the same maps to rounding. For each lag the cross-spectrum
of the frames with the frames that lag later is whitened, and its **odd part** kept: anything that stays put, however it breathes with the
gain, has a real cross-spectrum, and only a shift makes it imaginary. S(v) reads those maps along the straight line through (v lag). Its
highest place is the reading. v is image motion in px/frame of the file, +x right, +y down, as `layers`' shifts.

The low band finds a scene and reads it coarsely: 11 % slow on one of PR144's blocks. So the band above it (periods of 4-11 reduced px), an
independent set of coefficients, reads it again near that place. On a scene at least 4 reduced px/frame fast, within half its speed of the
low band's reading, the upper band's velocity is the one given. Nearer zero it is not believed: it keeps a residue of what stayed put about
zero, and PR085's 5.5 px/frame snapped to 0.9.

**The gate** (`scene.judge`), each number from a null, the first reason that fails given in the row:

| test | threshold | where it comes from |
|---|---|---|
| the picture changes | half the frames | a frozen picture has nothing to read (PR113 4431-4551) |
| z, the peak over S's own spread | 15.2 | the largest of the survey's 234 shuffled blocks |
| speed | 1 reduced px/frame | under it the first lag drops out of S and S steps up on a ring. 9 of the coded null's 13 strongest blocks sit at 0.78-0.97, and PR123's "reads" held their speed and turned every block |
| not on the search's rim | 2 steps inside it | PR112 at exactly 90 px/frame is a limit, not a measurement |
| the stack along v over along -v | 1.4 | about the 99th percentile of the coded null (1.38). The survey's 1.4 was a judgement call; on the still cameras the same ratio is 1.09 at most |
| the picture lasts | 0.07 | above all 258 searches on the still cameras (0.068) |

The last is the block's first half and last half, each added up along the velocity near v the stack likes best, two sets of frames with none
in common and up to 59 apart, and how well the two pictures agree. The search matters: 1 px/frame off, frames 30 apart are 30 px out, and a
real PR144 block read coarsely scores 0.005 at its own v. Known scenes score a median of 0.27 (5 % under 0.09).

**The false-alarm rate.** Real coded frames with no scene: **0 of 326 blocks read, 95 % upper bound 0.91 % a block.** 86 are the five Galileo
still cameras, every block (z 7.7 at most). 240 are six clips' own still pictures, symbols and vignette and stripes included, with their own
frame-to-frame scatter, wandering blotches of 0.5-4 DN that change without travelling, and a gain that breathes, coded by x264 at the clip's
rate and GOP (z 15.6 at most, one block, refused by its stack). Across 650 real clips of sky from a panning camera (Svanström et al. 2020),
25 blocks read. Looked at, each frame beside its stack along v and -v: 22 are plain scenes, clouds and treelines and coasts, and at most 3
are not plain (a smooth banded sky, or the aircraft itself, which no track kept out on that run). That is at most 0.5 % on real sky.

**Known answers.**

| | result |
|---|---|
| PR144 against its own layers | within 0.6, 0.8 and 1.1 % of the striated layer on three blocks, 2.9 % of the isotropic on the fourth |
| PR41 against its north marker | 23 of 23 blocks read. r 0.97 with the marker's rate over +-120 frames, 0.94 over +-90 (circular-shift null at most 0.65); 1,923 px/deg |
| PR088 object 2 against its pointer | 49 blocks. r 0.72, no shift of 48 reaches it (null at most 0.63); 1,005 px/deg, inside the survey's bracket of 652-1,349 |
| PR099 object 3 | 7 of 8 blocks read, 25.1-29.9 px/frame; with the block's mean out, `layers`' own templates read 10 of 21 pairs at 23.9-29.6 |
| The soccer camera (every frame's pan known) | every read block, 11 of 11 and 15 of 15 at 30 frames, lies inside what the camera did in that block. Where the pan held steady the error is about 5 %. Where it reversed inside the block the reading is one of the runs, not the mean: 41 % of frames within 15 % of it |
| Planted textures, the clip's own encoder | real still-camera frames at their own 2 Mb/s: read at 0.5 DN rms at 4 and 12 px/frame, 1 DN at 25, none at 0.25. On PR135's still picture at 2.9 Mb/s, read at 0.25. Nothing read at 0 DN (0 of 18). The upper band can move a right reading by about 6 % |

**What it is not.** It reads the steadiest velocity in a block, not its mean, so a block across a reversal says one side of it. Slower than 1
reduced px/frame it says nothing; `layers`' second pass is the tool there. Below about 1 DN rms on real noise a coded clip loses faint motion, so
unread means none above that, not none. A velocity is what was measured: what the moving thing is, sea or cloud, is not. It is in file pixels:
on a stretched clip it is not an angle without the stretch. The weaker places in S are mostly not layers: PR41's are a tenth of its main peak
and stack into a regular crosshatch, the coder's, and their pictures do not last. PR099's, near zero, cannot be settled that way. No word of
parallax comes from them. PR144's two layers are found by the top place flipping between blocks; both are rarely resolved in one block.

**PR135 is not empty sky.** The survey and its rebuild called this clip's stretch after the island empty, a coder's artefact the gate had to
refuse. But the sensor is an MQ-9's, looking down past an island (the private case notes put the look-down at 30-60° in the 0.643-deg field), and
what is under it is left unnamed here. 15 of its 29 blocks read, in one smooth run from the frames where the island
leaves the picture at -9.6 px/frame to -18.5, and on past a reversal to +7. The stack along v at frame 781 comes up as a picture, curved ridges,
and along -v as a smear. Against its pointer the x motion gives 1,462 px/deg, inside the 995-1,723 the 0.643-deg field and that look-down allow,
and outside the wide field's 178; the pointer's own correlation is only suggestive (r 0.60 over 180 frames, 2 of 18 shifts reach it). The weakest
blocks, 1180-1320 (stack gain 1.6-2.1), are the least sure. So a reference report's rate against a scene read as still (103 px/s) is against a
scene moving at 200-550 px/s. The report is not changed here.

**Kept apart from everything else.** The third pass and the block reading have their own rows, their own cache and their own file,
`<tag>_scene.csv`, one row a block. `<tag>_layers.csv` is the same to the byte with or without them (a test holds this, and on PR099 it was
compared on the real clip), so `slew`, `camera` and the report cannot take a block reading by accident; the templates' cache key did not
move, so every earlier cache holds. `mcdonald layers` runs it on a clip left still in over half its pairs (the line NO POWER is drawn on);
`mcdonald run` asks for it too, and the stage then says, beside its NO POWER, that the scene was read and how fast (the maintainer's choice: beside it, not in its place).
The rate against the background is still `layers`' own. `slew --scene-blocks` takes the scene from the blocks, only when asked, and judges it by the
rule below. About 7 s a block on one core, 400 MB.

**Where the blocks say the scene moved, the report does not say it held still (added 2026-11-13; IDEAS.md GL4).**
The blocks' line stood beside `layers`' NO POWER, and the NO POWER was worded "the scene is held still on screen". The
report took those words for its first line ("The picture behind it held still on screen"), its bottom line and its
checklist, on clips where the line beside them read the scene crossing the picture at 20 px a frame. One function now
says what the scene did for every reader of "held still" (`layers.scene_state`): *read*, the templates followed it
(left STILL on half the pairs or fewer); *under*, they did not and the blocks say it moved; *held*, they did not and
nothing says it moved. The rule for *under* is a count against the gate's own false-alarm bound: a block with no
scene is read under 0.91 % of the time, so a clip with no moving scene has one block read of one, two of 2 to 16,
three of 17 to 48 or four of 49 to 91 under 1 time in 100 (`layers.blocks_needed`; blocks taken to read falsely one by
one, not together), and that many read is the scene moving. The 1 in 100 is a choice of level. How much of the track
the blocks stand for is said too: *most* of it where half the blocks asked were read and the templates were left
still on nine pairs in ten, else "for at least part of the track".

Under: the first line reads "The object moved about 27 pixels a second in the picture, as the camera held it. The
background behind it moved across the picture at about 805 pixels a second. A pattern fixed on the camera's sensor hid
that motion from the match between frames, so the object's motion against the background is not measured." (PR41);
the checklist's camera row answers Yes where it answered Can't tell, and the row of the object's motion Can't tell
where it answered Yes ("across the picture, which held still"); the speed in body lengths takes the camera as moving;
the event study (§51) has no frame-by-frame scene and says so without calling it still. **The rate does not change**:
it is still the object's motion as the camera held it, and nothing is built on it. Taking the rate against the blocks'
velocity is the maintainer's decision of 2026-11-02 (beside, not in its place) and stays his: what it would give is in
the session's notes (PR41 830 px/s for 27, PR099 object 3 801 for 38, PR088 object 2 659 for 73), with the one check
that bears on it: where the templates' own read pairs fall inside read blocks they agree with the block's velocity
to 0.97-1.03 in speed and under a degree in direction (48 pairs on those three objects). Held: the words are what they
were, with one sentence more under them, "A background that crosses the picture faster than the search can follow
looks the same too": neither search sees a scene past its reach (the templates' `--max-shift`, 45 px a frame; the
blocks' 30 reduced px a frame), and "held still" was never a finding there.

*On the 31 objects of the reference case files* (each measured again by its recorded command, before and after): 25
carry the NO POWER. On **17 the blocks say the scene moved** and the words change: PR077 objects 1 and 2 (4 of 6 and 3
of 4 blocks, 11-26 px a frame), PR079 (6 of 8, 8-13), PR085 (12 of 17, 2-6), PR088 objects 1 and 2 (7 of 7 and 51 of
61, 8-33), PR099 objects 1-3 (4 of 6, 2 of 3, 11 of 13; 5-30), PR135's six (3 of 4, 15-21), PR41 (13 of 13, 25-31)
and PR44 (3 of 3, 6). "For at least part of the track" on three of them, where the templates were left still on under
nine pairs in ten: PR077 object 1 (85 %), PR099 object 2 (70 %), and PR44 (52 %), whose camera pans for six seconds of
fourteen. On 8 they do not: PR097's six with the NO POWER (no block read) and PR141's two (one block of three, none of
three) -- held, as before, with the one sentence more under the held words. No rate moves on any of the 31.

**The blocks' rule in `slew`** (`slew.fit_blocks`, 2026-11-02). `slew`'s own fit is in places: the scene's path chained from pairs, the pointer's
angle, a hold, an offset per stretch, and a check that the two rates follow each other frame by frame (§17). A scene read 60 frames at a time
cannot pass that check -- a velocity held over 60 frames has no frame-by-frame rate to follow -- and its path has no lever inside a block. So
with `--scene-blocks` each window is judged in rates instead. The slew's model differentiated is  rate = h + v_x / c:  a block gives one
velocity, the pointer one rate over the same frames (a line through its readings there), h is the hold and there is no offset per stretch,
so the chain's pieces do not enter. The pointer's rate is the noisy one (a glyph on a grid turning a step or two in a block), so it is
regressed on the blocks' velocities and c is the inverse slope, as the place fit regresses theta on X. The lever is the spread of the
blocks' velocities over the window; a steady pan under a hold has none, as before. Each zoom state is one window (a slew cut into pieces of a
few blocks each would have no blocks to test), `--window` still cuts where it is told, and a block over which the pointer's readings sit more
than 3 scatters (rms) off a line -- a pan reversing inside it, as the soccer camera's does -- is left out and counted. The 3 is a judgement call:
steady blocks of the real clips sit 0.6-2.6 scatters off their line (PR41's 2.6 where the pointer is read on half the frames), the soccer
camera's reversal blocks 2.1-4.3, and the two overlap; 3 keeps every steady real block, sets aside the sharpest reversal, and the verdicts on
PR41 and PR088 are the same at 2, 2.5, 3 and with no cut, while a kept reversal block reads c two to five times wrong.

Three outcomes a window, as in §17. REGISTERED: beta's bootstrap over the blocks is above zero, and the blocks' agreement with the pointer is
rarer than 1 in 20 of the circular shifts of the pointer's block rates by 1..n-1 blocks -- a null that keeps each series' own smoothness,
so two slow trends agree no better than their shifts do. With n - 1 shifts that takes 21 blocks (42 s at 30 fps): a window with fewer says so
and claims nothing, and a case that is part of a clip is told to read the whole clip's blocks. With no hold fitted (`--still`, `--hold-rate`,
a data bar's ground point) the shift test is not asked, as the place fit skips its rate test there: a steady pan's rates have nothing to share.
NOT registered: a floor from beta's interval where the pointer does not register the blocks' motion, and nothing where the shifts could do it.
AGAINST: beta below zero. A claim must then pass the place fit's own checks with the same constants: the pointer's turn a block beyond its
mean against its scatter and its step, the bootstrap's half-width (25 %), a hold allowed to drift linearly moving c by under 15 %, and the
motion's tilt. The forward slope is reported beside the reverse and refuses nothing: with the pointer's rate quantised over 60 frames the
two are always far apart, the noise is almost all the pointer's, and the blocks' own error (about 5 % of a velocity on the soccer camera)
attenuates the reverse slope by about 3 % at PR41's spread.

The shift test alone does not catch two trends: a scene ramping under a pointer ramping on its own gives r 0.997 and no shift reaches it;
the hold's steadiness refuses it (c moves 97 % with a term in t).

**False alarms, measured.** PR088 object 2's 51 real blocks against 12,000 drawn pointers with no relation to them (the pointer's rate an
AR(1) wander of 0.002 or 0.006 deg/frame rms, the real pointers' own spread, with a correlation time of a quarter of 10, 40 or 120 s, a hold of
-0.3 deg/s, a 0.18- or 0.29-deg grid, half the frames solved; 1,000 draws a configuration): the shift test alone passes **4.5 %** (3.5-6.3 % by
configuration), the test with the bootstrap 3.9 %, and **a claim -- every check passed -- 0.6 %** (0-1.5 %). A drawn scene of one slow swing (a
sinusoid of 40 s over 21 or 30 blocks) against a drawn pointer wandering on its own: the shift test alone **10.5-12 %** -- a circular shift breaks
a smooth series at the wrap, so the true alignment's r is more extreme than its shifts' on a series of one or two slow swings -- registered 9-10 %,
**a claim 1.6-2.1 %**, the hold's steadiness refusing most. So the test's own level is 1 in 20 and holds on real blocks; on a scene of one slow
swing it alone lets through 1 in 9, and the claim rests on the other checks too (1 in 50-60). PR41's 43 real blocks, whose velocity trends
from -10 to -31 px/frame over the clip, against the same drawn pointers: the shift test alone **6.5-17.6 %**, rising with the pointer's
correlation time (a trend against a slow wander), **a claim 0-1.0 %**. A drawn AR(1) walk of 21, 30 and 60 blocks: the test alone 10, 7.6 and
4.2 %, a claim 0.9-1.3 %. Two ramps: the test passes every draw and the hold's steadiness refuses every one. **So the shift test holds its level
on a series without a trend and is no guard on one with: the claim's measured rate, 0-1.5 % on real blocks and 0.9-2.1 % on drawn ones, rests
on the hold's steadiness and the bootstrap's width as much as on the shifts.**

**Recovery.** The same real blocks followed by a drawn pointer at a known c (1,900 px/deg on a 0.18-deg grid with a hold of 0.05 deg/s; 1,000
on 0.29 deg with -0.3; 1,500 with none; half the frames solved; 300 draws each): claimed 97-100 % of the time, c's median error within 2 %, nine
in ten within 3-4 %; the 16-84 % interval holds the truth 47-86 % of the time (68 % would be right: the bootstrap over blocks is a little
narrow where the blocks' velocities trend). Drawn scenes of 21-60 blocks: nine in ten within 4-14 %, the interval holding 50-81 %.

**The real clips**, every-frame pointers. PR088 object 2 (5240-8917): 51 blocks passed, 51 with the pointer; zoom state 11 is one window of 51
and **claims k cos(e) = 1,491 px/deg, 16-84 % 1,284-1,802**, r 0.66 with 0 of 50 shifts reaching it (the largest 0.52), hold -0.21 deg/s, c
moving 9 % with a drifting hold, the motion +6 deg off the horizontal; field at most 0.858 x 0.483 deg. With no hold the same blocks give 1,018,
the survey's 1,005 (its bracket 652-1,349 was the forward and reverse slopes with no hold): the hold is what moves c, and the rule fits one as the
place fit does on a moving platform. PR135 (1-1560): 13 blocks, its first state 11 of them, **refused by name**, and the agreement is nil anyway
(r 0.07, 6 of 10 shifts reach it; the motion -73 deg off the horizontal). PR41's case segment: 8 blocks with the pointer, **refused by name**;
its whole clip (120-2835): 33 blocks with the pointer, all of them **agreeing with the pointer** (r 0.78, 0 of 32 shifts reaching it, the largest 0.62) at
**1,640 px/deg** (16-84 % 1,422-1,996; 1,781 from the 29 steadiest-read blocks, the place fit's 1,784) and **refused for the hold's steadiness**:
a drifting hold moves c by 31 %, since PR41's velocity trends from -10 to -31 px/frame over the clip and a drifting hold cannot be told from it
there. With no hold the same blocks give about 1,940.

**The soccer camera** (`--still`, the pan known on every frame). Its 330 frames give five blocks end to end and the reading passes three, every
one across a reversal of the pan; their readings sit 2.1-4.3 scatters off a line, the rule sets the sharpest aside and refuses the two left
by name (under three), with the exact pointer and with one on a 0.25-deg grid; kept, all three give 107 px/deg and are refused by the
bootstrap's width. Kept, they would have given 149, 90 and 167 px/deg against a truth of 69, 72 and 35: a block's velocity is
one side of the reversal and the pointer's rate the mean. So the camera checks the reading's velocity (above) and the rule's refusal of a reversal,
and cannot exercise the shift test (three blocks of the 21 it needs); no known-pan footage long enough for the rule is at hand.

## 42. A phone's own record: `mcdonald phone` (the phone scope's WP1 and WP4; added 2026-11-07)

**What it answers.** An iPhone writes, beside its picture, a frame-by-frame record of its own camera: QuickTime timed
metadata (`mebx` tracks, Core Media metadata, a sample a frame), one of them keyed `com.apple.quicktime.live-photo-info`.
The file's one lens number, its 35-mm equivalent focal length, is a single value for the whole clip; the record has the
zoom on every frame. On the clip that called for this -- a witness's, which cannot be shared, so no number from it is
given here -- the tag fitted the record's lowest zoom while the clip sat well above that on most of its frames: a reader
who took the tag at face value was out by the ratio in every angle, and dips in the object's height over the horizon
were the zoom, not the object. Uploads and releases strip the track (of the data folder's videos none carries one), so
**each clip checks itself**, and the suite's clip is drawn (`tests/test_phone.py`).

**Reading it with ffmpeg alone.** The track is found by its key, not by a stream's number: the moov box is walked
(`phone.tracks`: each trak's id from its `tkhd`, its handler, its sample description's four letters, and for a `mebx`
description the `keys` box, whose children are boxes typed by their local key id, each holding a `keyd` with the key's
namespace and name), and the trak whose table names the key is matched to ffprobe's stream by its track id
(`phone.stream_of`). The samples come out with `ffmpeg -map 0:<n> -c copy -f data -`, cut by ffprobe's packet sizes; each
sample is items of [4-byte length][4-byte local key id][value], big-endian heads as every QuickTime box. ExifTool unpacks
the first 80 bytes of the value as 27 little-endian fields (`VfVVf6c4lCCcclf4Vvv`, its QuickTime module's
`live-photo-info`); the reader here gives ExifTool's 27 numbers, to rounding, on every frame of the one clip. A value
shorter than 80 bytes, or one that reads a zoom outside 0.5-30, an exposure of a second or more, or a NaN in the fields
used, is an unknown layout: NO POWER, never a guess (`phone.unpack`). The illuminance track
(`com.apple.quicktime.scene-illuminance`) is a big-endian uint32 in thousandths of a lux. A record's time is its packet's,
and its frame the one shown then (frames counted from 1, as they are extracted).

**What the fields mean** (Apple documents none of them; read on the one clip against its own pictures): field 1 the
exposure time; fields 4 and 5 the camera's shift since the first frame, in the coded picture's pixels at the zoom of the
moment, along its long and short sides, the content moving the other way (with ffmpeg's display rotation of 270, a
quarter turn clockwise, the clouds moved +field 5 across and -field 4 up and down; `phone.upright` turns the other
rotations by the same rule, unchecked);
fields 6 and 7 a shift of the frame's own; field 8 the video zoom factor of the camera the phone presents -- on a
two-camera iPhone 2.0 is the main lens at the "1x" its screen shows -- which the object's height over the horizon followed
through the clip's zoom slips at a slope near 1 and r near 1 (the scope's own check, rebuilt). Two fields are not
understood.

**k from the lens and the zoom** (`phone.k_at`). The 35-mm equivalent is the lens's angle across the picture's
diagonal, as on a 36 x 24 mm frame 43.27 mm across (CIPA DC-008). Read at the record's lowest zoom z_min, at frame n

    f(n) = f35 * z(n) / z_min,    k(n) = f(n) * hypot(W, H) / 43.27 mm,

px/rad. The share it may be off by is the larger of the width's reading's difference (f spread over the long side as over
36 mm: 4.7 % more on a 16:9 picture) and **K_SHARE 0.10** (a stabiliser's crop narrows the field the tag was written for;
a judgement). On the one clip this k agreed, within that share, with two measurements free of the tag -- the picture's
keystone as the phone turned, and the object's path fitted with k free -- and both refused the tag at the clip's usual
zoom. **The rule that the tag is the lens at the lowest zoom rests on that one clip**; the provenance flag says so in
words wherever the record's zoom moves. `scale` takes this k at the track's first frame where no graticule or field of view
is given, sourced as "the phone's record ... to within 10 %", and the ledger's k is then constrained by it, not assumed. A
field of view given wins, and the record's k is kept in the scale stage's fields (`phone_k`) so that a case worked out
again (`report CASE`) gives it back.

**The zoom inside the track** (`camera.record_steps`, `record_check`). The record's zoom becomes a zoom step at every
tracked frame whose zoom differs from the one before, about the frame's centre (a phone's zoom crops about the middle of
its sensor), and `to_one_scale` puts the track -- and `size_trend` the object's size -- on the scale of its first frame.
The kinematics stage fits its rate to that track (`stages.PHONE_NOTE` says so); the camera stage's rates are in it, and
the start and end of each stretch where the record's zoom moves are the camera's events. **The check comes first:** over
the tracked frames within RECORD_PAD (8) of each stretch where the record's zoom moves, the object's log length against
the record's log zoom, each stretch's own means out (so that the object's slow change of size between stretches does not
count): the slope, 1 where the picture follows the record, with its error from the residuals with their lag-one memory
counted (variance times (1 + rho) / (1 - rho) for a smooth zoom), and r. It **agrees** where the slope is within
SLOPE_TOL (0.25) of 1 and known to better than that (1.96 errors inside the margin); **disagrees** where the slope's
interval (1.96 errors either side) lies wholly outside 1 +- SLOPE_TOL -- the record is then said so, as no power for the
phone's record, and used for nothing (not k, not the zoom); and is **no power** where the zoom moves by less than x1.10
over the tracked frames, fewer than 12 of them have a size, the object at the lowest zoom (its median length there) is
under 1.5 blurs long (the blur then sets its size), or neither verdict is reached. A half-maximum size runs a little under a slope of 1 (a blur adds in quadrature: a 20-px image under
4 px of blur reads 0.96); what the check is for is a record that is not this clip's zoom -- a field read in another
phone's layout, a record shifted in time against its pictures -- whose slope is near 0 or anywhere. **SLOPE_TOL is a
judgement, not a threshold from a null**: one clip carries the track. **Its rates on drawn sizes** (72 configurations of
400 draws: an 80-frame clip with one zoom slip and a 400-frame clip with two, the object 10, 20 or 40 px through a 4-px blur,
log-size noise AR(1) of sd 0.02-0.20 and memory 0-0.8, a slow drift of the object's own size): a right record is refused
in at most 3.8 % of draws in 70 configurations (0-1 % in most), 5.8 and 7.2 % in the two noisiest on the short clip (sd
0.20 with memory 0.8), so the interval is about as stated; a wrong record -- 25 frames late, or moving while the sizes
hold -- is never let through as agreeing (0.0 % everywhere) and is refused in at least half the draws in 70 of the 72
configurations. Where the check cannot decide (the object under the blur at the lowest zoom, or sizes too unsteady), **a
record is used, and said to be unchecked**. Under the first rule tried (refused only where the slope's interval was
narrower than the margin) a record 25 frames late mostly came out no power: its misfit is structured, its residuals'
memory reaches the 0.95 cap, and the inflated error read as unsteadiness. On drawn
sizes (the suite): sizes following the
record with 3 % noise agree, sizes held while the record says x1.5 disagree, a record 25 frames late disagrees, a
record whose zoom holds is no power, sizes with 60 % noise are no power, a 3-px object is no power; on the drawn clip
the right record agrees and puts a blob still in the sky still on one scale, and a record whose zoom moves the other way
(another layout's field) disagrees and is not used.

**Provenance** (`phone.provenance`): the maker, the model, the software, the lens and the 35-mm tag from the container's
own `mdta` keys (an iPhone keeps the lens and the tag in the video track's `meta`, which ffprobe does not show), the two
creation times, the codec and any encoder that wrote the file again. Flags, each a thing to know about the file and not
a verdict on the clip: the container's creation time more than two minutes from the phone's own (a copy written later, a
share or an export, which can keep the record); H.264 from an iPhone (which records HEVC unless set to "Most
Compatible"); a software tag that is not a system version; an encoder's own tag (Lavf, Lavc, HandBrake); an iPhone's
file with no record; the 35-mm tag against the record's zoom.

**What a case gets, and what it does not.** `run` reads the record at ingest only for a phone's clip (an iPhone's maker or
model tag, or a `mebx` track: `phone.is_phones`); any other clip is not asked, and its case's fields, words and numbers are
as they were -- of the data folder's 193 videos none has either (one, an editor's export, carries other
`com.apple.quicktime` tags, a title and an author, and is not asked), so none of the fourteen reference cases moves. `--no-phone` refuses it (the ingest says "not read:
refused"). `mcdonald phone VIDEO` reads it alone into `<tag>_phone.csv` (frame, time, zoom, the shifts along the coded
sides and as the content moves upright, the exposure, the light, the 27 fields), exit 5 with no record; `camera --phone`
takes it into the camera stage. **Not done:** fields 4-5 checked against the picture's own shift (the scope's "slope about
1" on the shake) -- `layers` holds a smooth sky still, so there is no picture shift to hold them to, and the sky as a
background (WP2) is the route; another phone's layout; the 56 bytes after the 80; a zoom read from the horizon or the sky
on a clip with no record (WP4's larger part).

## 43. The bird floor set from a null, and held to a set it was not set on (B24, E9, E19; added 2026-11-07)

**What it is.** `report.BIRD_FLOOR` is the share of the object's brightness its beat must reach before the conclusion
names a bird. Section 13's headline rule asks the beat to be the object's own, to come back, to lie at a wingbeat's rate
(2-25 Hz) and not to be the camera's shake (item 17); the floor is the last condition. It was first set by eye on
2026-10-19. On the Svanström labelled infrared set the calls on birds beat at a median 15-18 % of their brightness and
the false calls on aircraft, drones and helicopters at 1.8-2.3 % (AUC 0.96), and 8 %, chosen on the birds and airplanes,
left 2 of 307 non-bird tracks called. Chosen after seeing the data, it was a candidate. Here it is set by a rule written
down before the data were measured again (the session's notes, 2026-11-07), and tested once on a set it had not met.

**The rule** (`tools/sweep/floor.py set`). The null is a labelled set's non-bird tracks, each measured by `mcdonald
flicker` on its label boxes as a track (`--no-nulls`, as `run` measures; `--scene-shift`, so that the shake is read at
every beat of the object's own and not only at those a floor would let through). A track is named a bird under a floor
where `Case.conclusion` would name one. The false-alarm rate at a floor is the share of all non-bird tracks named,
refused ones in the denominator. The stated rate is **alpha = 1 %** (`report.BIRD_FLOOR_RATE`), the level of every null
the package states (CONTINUUM_P, ONCE_P, FAP_MAX); the level is a policy, the maintainer's to change. For each beat rule
the floor is the median, over 2,000 resamples of the null's clips with replacement (a clip's tracks together, since a
clip's objects are not independent), of the smallest floor on a 0.1 % grid at which no more than alpha of the resample's
tracks are named. BIRD_FLOOR is the larger rule's, rounded up to the next 0.5 %.

**The set it is set on.** Svanström et al. (2021), the infrared clips: 432 tracks of 60 frames or more in 365 clips (125
birds; 82 airplanes, 168 drones and 57 helicopters, 307 non-birds in 286 clips), the 2026-10-19 conventions, measured on
d46d3a8 (`flicker` as 0.4.3 released it) by this session for the 67 tracks with a bird call in any of eight earlier runs
(0.3.1's two rules, the aperture study's six apertures), and for all 432 by the controls harness's run of the same
commit (the 67 measured by both agree on all 134 calls). The 2026-10-19 numbers rebuilt first, from that run's own
table: the amplitude's AUC, bird over non-bird among every bird or one-stretch call, 0.959 (stage) and 0.962 (paper),
and 2 of 307 non-bird tracks named at 8 % under either rule -- reproduced. On 0.4.3 the AUC is 0.935 and 0.960 (0.919
and 0.956 among the calls that come back). Before any floor the stage's rule calls 16 non-bird tracks a bird (12 on
0.3.1), not counting two the shake gate stops (item 17; one is AIRPLANE_064, which the 8 % floor had kept, 8.03 Hz at
14.9 %): the capped disc (2026-10-24) adds the close helicopters 024 (7.8 %) and 027 (3.6 %); and three drones now beat
at 10.0 Hz, a third of the frame rate (`fps/3`, marked as a look-alike), 059 at 15.4 % among them -- the band's top on
this chain is 12 Hz since the held-picture test (section 35), where 0.3.1 had misread the chain and cut it at 9.9. The
paper's rule calls 23 (24). Bird tracks called: 31 and 30 of 125 (30 and 34; the continuum's correction, section 39,
takes out four).

**The floor.** The stage's rule gives 7.0 % (5-95 % over the resamples 4.7-15.4 %), the paper's 5.1 % (3.1-7.9 %):
**BIRD_FLOOR = 7 %**. At it the stage's rule names 3 of the 307 non-bird tracks (1.0 %; 0.0-2.3 % by clip; the exact
one-sided 95 % bound 2.5 %): helicopter 043 (21 %, a fence line and poles passing behind it), drone 059 (15 % at 10.0
Hz) and helicopter 024 (7.8 %); the paper's names 2 (0.7 %; bound 2.0 %). The false beats are as they are: by the
stage's rule the 16 non-bird calls before any floor beat at 21.0, 15.4, 7.8, 6.97, 6.1, 5.0, 4.8, 4.6, 4.3, 4.1, 3.9,
3.6, 3.1, 2.5, 2.1 and 1.6 % of their brightness, so no floor separates them from the birds cleanly; the 8 % chosen by
eye had been said as a line false alarms "stay under", which two of them do not. The rate is a point estimate with its
bound, and the report says "about 1 in 100", never "under": with none in 286 the bound is still 1.04 %, so no set of
about 300 tracks can show a rate under 1 %. To show it -- false alarms at or under alpha with probability 1 - delta --
the floor would be an order statistic of the non-bird scores (the Neyman-Pearson umbrella; Tong, Feng & Li 2018), which
here would sit over the strongest false call, 21 %, and name 15 and 13 of the 125 birds where 7 % names 30 and 27; the
maintainer's choice, not taken. The 8 % chosen by eye names 2 and 1 non-bird tracks and 29 and 26 birds. (The floor was
first set at 6.5 % with 173 tracks not yet measured counted as not named, none having a bird call in eight earlier runs;
two drones at 10.0 Hz among them did call, and the rule on the complete set gives 7 %. It was re-set before any unseen
track was read.) The labels say a bird is there, not that it flapped, so 24 % of bird tracks named is a floor on the
test's sensitivity to flapping birds, not its measure. Rates by what a clip offers (`floor.py strata`; a description,
never an input): the stage's misses run 56 % at medium range, 72 % close and 91 % distant; 62-80 % across track lengths;
and the test answers at all on 88 % of bird tracks, 97 % of airplanes, 96 % of drones and 81 % of helicopters -- a NO
POWER is not shown to carry the class (refused birds over refused non-birds 1.9, by clip 0.8-3.9, and about 1.2-1.4
within strata of contrast; the diagnostic-accuracy survey), but helicopters are refused far more often. Every clip here
runs at 30 frames a second.

**The cost of a false bird (B24).** A receiver sets its criterion by the odds and the costs (Wiley 2006): with
equal-variance normal evidence, the likelihood ratio at the criterion, beta = exp(d' c), equals (1 - pi) / pi times
C(false alarm) / C(miss) where the criterion is best. In this tool "bird" closes a case: a false bird explains something
away, a missed one leaves it on the list, so a false bird should cost more than a missed one. Read off the set at one
object in twelve a bird, the beat's tests alone price a false bird at 0.27 (stage) and 0.20 (paper) of a missed one --
the wrong way round; the floor at 1 in 100 at 1.08 and 1.46, and the old 8 % at 1.5 and 2.6. At one object in three a
bird the floor's prices are 6.0 and 8.0. The rate, not the floor, is the lever: a stricter rate prices a false bird
higher, and needs a larger null to be set on (1 in 200 needs some 600 non-bird tracks). The base rate of birds among the
objects a camera records is not known; one video in twelve is an anchor, not a measurement.

**How overfit the choice is (E9; `tools/sweep/pbo.py`).** Combinatorially symmetric cross-validation (Bailey, Borwein,
López de Prado & Zhu 2017): the clips in 16 blocks (whole clips, dealt round within the birds and within the rest after
a seeded shuffle), and all 12,870 ways of taking half of them. On each half a floor is chosen -- by the floor's own rule
at 1 %, or by the largest U = TPR - 11 FPR (a false and a missed bird priced alike at one object in twelve a bird) --
and ranked by U among the 41 candidates, 0-20 % by 0.5 %, on the other half. PBO is the share of halves where the choice
ranks at or under the median out of sample. On the set here, chosen by the floor's own rule the floor's PBO is 0.45
(stage) and 0.47 (paper), the choices running 5.0-15.5 % and 4.5-8.0 % across halves; chosen by the best U, 0.35 and
0.37 (0.12-0.38 and 0.14-0.48 at w 5.5 and 16.5). So the set does not pin the floor's exact value within about 5-15 %:
chosen on half the clips, it is close to the median candidate on the other half. What it does pin is that a floor helps:
on every one of the halves the floor chosen beats no floor out of sample (U by +0.42 and +0.68 at the median). On
0.3.1's table the same runs give 0.54 and 0.50, and 0.40 and 0.36. For `flicker.POINT_DISC` (the capped disc of
2026-10-24) the tool was run on the data the cap was chosen on, the aperture study's tables (mcdonald 0.3.x, the floor
at 8 %): among the three apertures tried on both the labelled set and the 38 known-beat birds (no cap, the 6-px cap, a
fixed 4-px disc) PBO is 0.25, the cap chosen on most halves; among the seven tried on the 38 known-beat birds alone
(fixed discs of 3, 4, 4 with a wider ring, 5 and 6 px, the cap, and no cap; their 15 videos in 8 blocks) it is 0.71 --
the cap's lead over the discs of 4-6 px whose ring clears the bird (23 of 38 against 21) is noise, while the cap's lead
over no cap carries over. A disc's candidates need `flicker` run at each size; the tool takes any gate's candidates as a
table (`pbo.py configs`).

**The challenger (E19; `floor.py challenger`).** The simplest rule that could do the floor's job is the amplitude alone:
the strongest beat the stage reports, in the wingbeat band, with none of its tests (whether it is the object's own,
whether it comes back, the shake), its threshold set by the same rule at the same 1 % (15.0 % by the stage's
measurement, 11.4 % by the paper's). It names 3 of 307 non-bird tracks under each, and 27 and 37 of the 125 birds, where
the gate names 30 and 27. The gate's margin, in birds named at the same rate: **+2.4 points under the stage's rule (by
clip -4.8 to +10.1) and -8.0 under the paper's (-14.8 to -0.8)**; on 0.3.1's table, against the 8 % floor, -8.0 and
-3.2. On this set the beat's tests do not beat the amplitude alone: on 0.3.1's table, of the 14 birds the amplitude
alone added, 9 had beats the tests did not hold to be the object's own and 5 came back in one stretch only. The set does
not hold what the tests were built for -- a codec's rhythm, a beat the background shares, the camera's shake; its camera
tracks its target against clean sky -- and their worth was shown on PURSUE's background apertures (0.15 % / 0.36 %
pass). A challenger held on a null with those in it is what would settle whether they earn their place here.

**The test on a set it had not met.** Once, with the floor frozen, on two sets the floor and these gates had not met.
The Svanström set's visible-band clips (640 by 512, colour, the same platform; their bird calls never tabulated before),
measured by the stage's rule in a seeded random order with the non-birds first: by the time of the look 190 of the 279
non-bird tracks were measured, and 2 are named a bird (1.1 %; the one-sided 95 % bound 3.3 %), drone 009 (9.9 Hz, 16 %)
and airplane 017 (5.0 Hz, 7.5 %), against at most 4 that a rate of 1 in 100 allows on 190 at the 5 % level: not shown
above the stated rate -- a weak test at this size, which a detector at 2 % would pass two times in three. With no floor,
7. The visible birds were not reached, so the floor's cost there is not measured. And AARO's resolved cases, as run
blind in the same session (10 cases, 16 objects): none has a beat of its own, so the floor decides nothing there; the
two bird cases are stopped by the beat's own tests. The 10-Hz drones of the infrared set have company in the visible
(drone 009, and 007 at 10.3 Hz under the floor): a third of the frame rate, which the held-picture test (section 35)
reads as uneven holds rather than a cadence (drone 059's balance 0.84 against the 0.85 it needs), so the band's top
stays at 12 Hz.

**The held-out third** was not looked at. Its look was spent on 2026-10-18 (ffa9f3f), before this floor, the capped
disc, the continuum's correction, the one-stretch rule and the shake gate; the ledger of looks (`tools/sweep/looks.tsv`)
records it spent for them and owes them a set none has met. The visible-band clips and AARO's resolved cases are that
set here.

**As a diagnostic-accuracy study** (the items of STARD 2015). Fixed in advance, in the session's notes before the set
was measured again: the rule, the sets it is set on and tested on, the pass test, the CSCV design and the challenger.
Judged: the rate (1 in 100, a policy), the 0.5 % rounding, and three amendments written before the data they concern
were read -- tracks not yet measured counted as not named (dropped when the set was complete, which moved the floor from
6.5 to 7 %), the visible set by the stage's rule only, and the time of the look. What the reader knew: the infrared
set's calls of 2026-10-19 and 2026-10-24 (the floor's first choice was made on them, so it is the setting set, never a
test); the visible set's bird calls had never been tabulated; AARO's cases were run blind by another agent. Sample: 432
infrared tracks in 365 clips; 190 visible non-bird tracks at the look. Flow, by the stage's rule at 7 %: airplanes 82,
answered 80, named 0; birds 125, answered 110, named 30; drones 168, answered 162, named 1; helicopters 57, answered 46,
named 2. The nulls, the planted beats and this labelled set are the bird call's validity as applied (PCAST 2016; Federal
Rule of Evidence 702(d)): what it does on footage like the case's, not on footage in general. The controls harness keeps
the QUADAS-2 table and the bird call's validation file; this section does not repeat them.

**What it moves.** Of the 31 reference objects (the 14 case files, measured by the paper's rule), none changes its call:
every one named a bird beats at 10.3 % of its brightness or more (PR097 object 3 the faintest), and the one beat of its
own under 8 % that comes back, PR085's (7.37 Hz, 5.0 %), stays under 7 %, "too faint to name a bird"; only the words
that say so change ("about 1 in 100 of them reach 7 %"). By the stage's rule -- each of the 28 objects with a beat
measured again with its case file's track, frames, aperture and avoided tracks -- none moves either: every one it names
beats at 10.3 % or more, and the beats it does not hold to be the object's own (PR085 at 13.5 %, PR088 object 1, PR097
objects 2 and 4, PR099 object 2, PR141's two copies) name nothing under either floor. PR41's bird (11.6 % in its 12-px
disc by the paper's rule) was not measured again by the stage's rule in the session (its run outlasted its slot); the
paper's rule keeps it a bird at either floor. (The two rules differ, as before this change, on PR088 object 1, which the
paper's names and the stage's does not, and PR097 object 7, the reverse.)

**What no floor near it stops** (the air-and-sea survey of 2026-11-07, its W3, rebuilt through `flicker`'s own judging;
stated here as an open limit, not built). Atmospheric twinkle -- log-normal scintillation with a Kolmogorov corner -- planted
in the light curves of 18 real non-flapping tracks of the labelled set was named a bird in 18 of 540 draws (3.3 %, 2.1-5.2 %),
every one at 2.1-4.4 Hz and at a strength sigma_I of 0.25 or more, with beats of 8.8-30 % that a floor near 7-8 % does not
reach; the unplanted templates gave none, planted wingbeats came back 33 of 36. The continuum null (§39) refuses 17 of the 18
(at a cost of 5 of the set's 31 named birds and none of the reference beats), and the steadiness test reads twinkle as a
clock. The rate is before the encoder: the twinkle was planted in curves, not in frames through the clip's codec. Strong
twinkle is mostly refused as NO POWER with "lost against what is behind it", which is the wrong reason for it (Jacob's
words to set: the survey's W5). Only a compact source twinkles (about sqrt(lambda L) or smaller: 0.14-0.45 m in the long-wave
infrared at 2-20 km), so the aircraft controls are nulls for it, and a hot engine seen in the mid-wave infrared is not.

## 44. The controls harness: one of everything, and the rates it stands for (I1, T9, B28, B17; added 2026-11-07)

**What it answers.** A control says what the stage did on one thing. What that says of the stage's rates depends on how many
such things were tried, and on whether what each is was known from outside the tool. The harness keeps the two apart: a
sample of one of everything, judged again after every change in a minute or two (`tests/test_controls.py`, a regression),
and the labelled infrared set's whole run, a tool that runs through the job scheduler, where the rates come from
(`tools/controls/`). It lifts the hold of 2026-10-20 ("the harness waits for the new workstation") for the sample on the
present machine; the whole set stays a scheduled run.

**The labelled set as tracks** (`tools/controls/svanstrom_labels.py`). Svanström et al. (2021) keep a box on every frame of
their 365 thermal clips as MATLAB `groundTruth` objects (MCOS class instances), which `scipy.io.loadmat` does not decode.
The object is a MAT stream of its own inside the file's `__function_workspace__`; given a header, scipy's own version-5
reader reads it, and its FileWrapper cell array holds `LabelData`, a row a frame. The boxes of the clip's own class become
tracks: the centre (x + w/2 - 1.5, y + h/2 - 1.5) in the package's pixels (on 48 sampled tracks the contrast centroid sat
0.5-2 px from it on 46), frames 1-based (row i is frame i + 1: written 0-based, a frame early, the 2026-10-19 run had put a
periodic centring error into the aperture of every track whose labels follow the platform's 2-3 Hz wobble), several boxes in
a frame linked by nearest neighbour within 25 px and 15 frames. The polarity is read from the pixels, never the class. 446
objects, **432 tracks** of 60 frames or more (125 birds, 82 airplanes, 168 drones, 57 helicopters), written once to the
reference-data folder's `svanstrom2021/tracks/` -- the same 432, frame for frame and polarity for polarity, as the PURSUE
analysis's conversion of 2026-10-19. The camera follows its target on a pan-and-tilt platform, so the object stays near the
middle and the scene moves behind it; the pictures change on every frame.

**The whole-set run** (`run_set.py`, `svanstrom.sbatch`, `summarise.py`). Every track through `flicker.measure` as `mcdonald
run` puts an object through it -- the aperture following its size, the clip's other tracks avoided, the scene's own motion
read at a beat that would name a bird -- under the stage's rule and the paper's; nothing tuned per clip. A call is read two
ways: as the run of 2026-10-19 read it (**bird**: the object's own beat at 2-25 Hz that comes back), and as the report says
it today (**named**, "Beats like a bird": the same at BIRD_FLOOR, 7 % of the brightness since the floor's merge (section 43;
8 % when the set was run), or more, and the camera's shake not at the beat -- the two tracks with a beat between 7 and 8 %,
IR_BIRD_065 and HELICOPTER_024, measured again at 7 % so that their shake was read: neither shaken). Every rate with its
exact (Clopper-Pearson) 95 % interval over tracks and a 95 % interval from resampling clips, since a clip's tracks are not
independent (E10):

| tracks | the stage's rule: a bird call (2026-10-19's reading) | named today | the paper's rule: a bird call | named today |
|---|---|---|---|---|
| birds (125) | 31 of 125 (24.8 %; 17.5-33.3, by clip 16.7-33.3) | 30 of 125 (24.0 %; 16.8-32.5, by clip 15.8-32.5) | 30 of 125 (24.0 %; 16.8-32.5, by clip 16.1-32.4) | 27 of 125 (21.6 %; 14.7-29.8, by clip 13.8-29.8) |
| airplanes (82) | 7 of 82 (8.5 %; 3.5-16.8, by clip 3.3-15.0) | 0 of 82 (0.0 %; 0.0-4.4, by clip 0.0-0.0) | 11 of 82 (13.4 %; 6.9-22.7, by clip 6.3-21.0) | 0 of 82 (0.0 %; 0.0-4.4, by clip 0.0-0.0) |
| drones (168) | 1 of 168 (0.6 %; 0.0-3.3, by clip 0.0-1.8) | 0 of 168 (0.0 %; 0.0-2.2, by clip 0.0-0.0) | 5 of 168 (3.0 %; 1.0-6.8, by clip 0.6-5.9) | 0 of 168 (0.0 %; 0.0-2.2, by clip 0.0-0.0) |
| helicopters (57) | 8 of 57 (14.0 %; 6.3-25.8, by clip 3.6-25.0) | 2 of 57 (3.5 %; 0.4-12.1, by clip 0.0-8.9) | 7 of 57 (12.3 %; 5.1-23.7, by clip 3.6-23.3) | 2 of 57 (3.5 %; 0.4-12.1, by clip 0.0-8.9) |
| all non-birds (307) | 16 of 307 (5.2 %; 3.0-8.3, by clip 2.6-8.1) | 2 of 307 (0.7 %; 0.1-2.3, by clip 0.0-1.7) | 23 of 307 (7.5 %; 4.8-11.0, by clip 4.6-10.9) | 2 of 307 (0.7 %; 0.1-2.3, by clip 0.0-1.7) |
| distant birds | 5 of 57 (8.8 %; 2.9-19.3, by clip 1.8-16.9) | 5 of 57 (8.8 %; 2.9-19.3, by clip 1.8-16.9) | 6 of 57 (10.5 %; 4.0-21.5, by clip 3.4-19.4) | 6 of 57 (10.5 %; 4.0-21.5, by clip 3.4-19.4) |
| distant non-birds | 1 of 100 (1.0 %; 0.0-5.4, by clip 0.0-3.0) | 0 of 100 (0.0 %; 0.0-3.6, by clip 0.0-0.0) | 3 of 100 (3.0 %; 0.6-8.5, by clip 0.0-7.0) | 0 of 100 (0.0 %; 0.0-3.6, by clip 0.0-0.0) |

Coverage -- the share answered, not NO POWER -- is not the same for every class, so it stands beside every rate: under the
stage's rule birds 111 of 125 (89 %), airplanes 80 of 82, drones 162 of 168, helicopters 46 of 57 (81 %), 399 of 432 in all
(92 %). A refusal is 1.8 times as likely on a bird as on anything else, but by clip 0.7-3.8 (2.0 and 0.9-4.0 under the
paper's rule): the interval holds 1, and the diagnostic-accuracy survey (2026-11-07) finds the objects' contrast accounts
for it, so a NO POWER is not shown to carry class information. Each false-alarm rate is a point estimate with its exact
one-sided 95 % upper bound: named non-birds 2 of 307, 0.7 %, under 2.0 %, under either rule. None
in 286 would bound the rate only under 1.04 %, so no count on a set this size can show "under 1 %". Among the answered
non-birds, 2 of 288. The two named are HELICOPTER_024 (3.53 Hz, 7.8 %, both; over the floor since it went to 7 %) and
HELICOPTER_043 (2.09 Hz, 21 %, both); of the 32 tracks the report names a bird under the stage's rule, 2 are not birds.
Until 2026-11-13 there was a third, DRONE_059 (10.0 Hz, 15 %, stage only): its held frames' own rhythm, above the band's
top since its cadence is read in blocks (section 35). Read as a test, a name is 37 times likelier on a bird track than on
any other (24.0 % against 0.65 %; 33 under the paper's rule, 21.6 % against 0.65 %). By clip, 2 of 286 non-bird clips are
named, under either rule.
Among the tracks already called (bird or once), the beat's amplitude separates the calls on birds from those on everything
else with an AUC of 0.95 (stage) and 0.96 (paper) -- the 2026-10-19 figure's definition. Over every track with a measured
amplitude (400) it is 0.90 and 0.91, and among the tracks with no beat of their own still 0.88 and 0.89: most of the
separation is the birds' faintness, not their beat (the diagnostic-accuracy survey reads 0.82 over all 432). The two rules
as two raters on one set of tracks (the biology survey's X6): a bird call or not, raw agreement 97.2 %, chance 79.5 %, kappa
0.86, positive agreement 88.0 % (44 called by both, 3 by the stage's rule alone, 9 by the paper's); by class, kappa 0.94 on
birds, 0.75 airplanes, 0.33 drones (1 called by both, 4 by the paper's rule alone), 0.92 helicopters; named or not, 98.8 %,
86.9 %, 0.91, positive agreement 91.8 %.

**Flow, and how the set was read (STARD 2015; QUADAS-2).** From the labels to the calls, under the stage's rule (the
paper's in brackets where it differs):

| | birds | airplanes | drones | helicopters |
|---|---|---|---|---|
| labelled objects of the clip's class (446, in 365 clips) | 137 | 84 | 168 | 57 |
| shorter than 60 frames: listed, no track | 12 | 2 | 0 | 0 |
| tracks measured (432) | 125 | 82 | 168 | 57 |
| refused, NO POWER | 15 [17] | 2 | 6 [7] | 11 |
| answered | 110 [108] | 80 | 162 [161] | 46 |
| named "Beats like a bird" (at 7 %) | 30 [27] | 0 | 1 [0] | 2 |

| QUADAS-2 domain | how this set stands |
|---|---|
| selection | every labelled object of 60 frames or more, none chosen; the set's own clips (a pan-and-tilt tracking camera, ground-based, 30 frames a second, 320x256) -- not PURSUE's airborne turrets: applicability, not bias |
| the test | run blind to the label: `flicker` sees a track and the pixels, never the class; the polarity read from the pixels; nothing tuned per clip. Fixed before the run: every gate and constant of 0.4.3. BIRD_FLOOR's 7 % was set afterwards on this very set, by the floor's null (section 43): for the floor this set is the setting set, not a test -- its tests are section 43's unseen sets. Judged, and flagged: STRATUM_MIN, the strata's edges, the sample's picks |
| the reference standard | the set's own labels (a box on every frame, by its authors): a class, not a behaviour -- a bird's label does not say it flapped; some clips labelled between key frames |
| flow and timing | all 432 tracks under both rules, no track lost (the replays 864 of 864); refusals reported by class, never dropped |

The sample size was not chosen: it is the set. With 307 non-bird tracks, no count can show a false-alarm rate under 1 % at
95 % (none in 307 would bound it under 0.97 %; 3 bound it under 2.5 %, 2 under 2.0 %), and 125 bird tracks put an exact
interval of about 15 points on the share named.

**Validity as applied** (PCAST 2016; Federal Rule of Evidence 702(d)). The rates above say how the method does on such
clips; whether it was applied reliably to *this* clip is a different question, and the stage answers it per clip: the
planted beats and the planted-dot encoding control (what this clip's own noise and encoder can make and hide), the
aperture that follows this object's size, the background apertures beside it, and the nulls -- the drift test, the
continuum null, the one-stretch rule -- each read on this clip's own curves. They are the method's validity as applied, and
the report carries them with the call.

**The 2026-10-19 headline, rebuilt, and what 0.4.3 changes.** The reading of 2026-10-19 on today's code, against that day's
(0.3.1): birds 31 of 125 (24.8 %) against 30 (24 %) under the stage's rule, 30 (24.0 %) against 34 (27 %) under the paper's;
non-birds 18 of 307 (5.9 %) against 12 (3.9 %), 25 (8.1 %) against 24 (7.8 %); airplanes 7 and 11 against 7 and 12, drones 3
and 7 against 0 and 6, helicopters 8 and 7 against 5 and 6; the amplitude's AUC 0.94-0.96 against 0.96. Of 432 tracks, 64
calls move under the stage's rule and 74 under the paper's; where a bird call stands on both days its frequency is the same
to the digit (42 of 42, stage). Each move has its cause in the measurement's own fields:
- **A beat in one stretch, against its own continuum** (item 15, 2026-10-31): 42 "once" calls and 8 "other" calls become no
  beat of its own under the stage's rule (36 and 12 under the paper's) -- the largest change, and none of them was a bird
  call.
- **The continuum null read as the curve is** (B1, 0.4.2; section 39): under the paper's rule 8 bird calls become no beat,
  four by the null alone (IR_BIRD_006, 072 o1, IR_DRONE_026, 033; p now 0.021-0.088) and four with the one-stretch rule
  (IR_BIRD_024 o1, 074, IR_DRONE_057, IR_AIRPLANE_063).
- **The band's top at 12 Hz** (M3, 2026-10-29; section 35): `flicker.pictures` no longer reads this chain as about 24.7
  pictures a second (429 of 432 tracks now have the frame grid's 12 Hz; three read a cadence near 8 Hz), so beats between
  9.9 and 12 Hz are heard. Three drones beat at 10.0 Hz, a third of the frame rate: DRONE_023 and 098 at 5 %, under the
  floor, and **DRONE_059 at 15 %, named "Beats like a bird" under the stage's rule** (5 % under the paper's), a new false
  alarm of 0.4.3. A third of DRONE_059's frames are held (a 20-a-second source in a 30-a-second file, perhaps), and the
  held-pictures test misses the cadence by a hair (the word's balance 0.84 against BALANCED's 0.85), so the band stays at 12
  Hz and the holds' own rhythm at fps/3 is heard as the object's; 50-Hz mains fold to the same 10 Hz. The suite held it as
  a false alarm of record, with that cause, until 2026-11-13: a word short of the line is read in blocks since (section
  35), DRONE_059's and DRONE_098's are cadences in most of theirs, the band's top is 8 Hz and both calls are gone; DRONE_023
  (its holds in runs: one block of five) keeps its 5 % under the floor.
- **The capped point disc** (2026-10-24): helicopters 024 and 027 at 3.5-3.9 Hz (7.8 % and 3.6 %), as the aperture study
  predicted (helicopters 5 -> 9 there); 027 under the floor, and 024 over it since the floor went to 7 %: named under both
  rules, its shake read and not at the beat.
- **The camera's shake at the beat** (item 17, 2026-10-31): AIRPLANE_064's 8.03-Hz beat at 15 % -- the false alarm of record
  the 8 % floor kept on 2026-10-24 -- is still called, and no longer named: the whole picture moves 0.04 px at that
  frequency, 60 times its neighbours.
- **BIRD_FLOOR** (7 % since the floor's merge, section 43; 8 % when the set was run) names 30 of the 31 bird calls on birds
  under the stage's rule (IR_BIRD_053 at 6.2 % falls under it; 065 at 7.5 % is named, its shake read at 7 % and not at the
  beat) and 27 of 30 under the paper's (042, 053, 068 at 5.4-6.7 %). Of the 18 non-bird calls under the stage's rule, 14
  fall under the floor, one is the shake's and three are named; of the paper's 25, 22 fall under it, one is the shake's and
  two are named.

**By what a clip offers** (the diagnostic-accuracy survey's spectrum bias: a pooled rate over easy tracks overstates the
test's power on hard ones). The same rates in strata read from what the outcome cannot set -- the track's length, the
label's size, the set's distance bin, the frame rate -- and the object's contrast over its ring (a reading of its pixels,
never flicker's `needs`, which follows the outcome); exact 95 % intervals; a stratum of under ten tracks (STRATUM_MIN, a
judgement call) gives its count and no rate. The edges are round numbers near the set's quartiles, fixed before these were
read:

| stratum | birds named, stage | non-birds named, stage | birds named, paper | non-birds named, paper |
|---|---|---|---|---|
| frames: 60-149 frames | 9 of 43 (21 %; 10-36) | 0 of 17 (0 %; 0-20) | 8 of 43 (19 %; 8-33) | 0 of 17 (0 %; 0-20) |
| frames: 150-299 frames | 8 of 22 (36 %; 17-59) | 0 of 11 (0 %; 0-28) | 8 of 22 (36 %; 17-59) | 0 of 11 (0 %; 0-28) |
| frames: 300 frames or more | 13 of 60 (22 %; 12-34) | 2 of 279 (1 %; 0-3) | 11 of 60 (18 %; 10-30) | 2 of 279 (1 %; 0-3) |
| size: under 14 px wide | 11 of 48 (23 %; 12-37) | 0 of 66 (0 %; 0-5) | 10 of 48 (21 %; 10-35) | 0 of 66 (0 %; 0-5) |
| size: 14-20 px | 15 of 66 (23 %; 13-35) | 0 of 118 (0 %; 0-3) | 13 of 66 (20 %; 11-31) | 0 of 118 (0 %; 0-3) |
| size: 20 px or more | 4 of 11 (36 %; 11-69) | 2 of 123 (2 %; 0-6) | 4 of 11 (36 %; 11-69) | 2 of 123 (2 %; 0-6) |
| contrast: under 10 grey levels | 5 of 39 (13 %; 4-27) | 0 of 31 (0 %; 0-11) | 6 of 39 (15 %; 6-31) | 0 of 31 (0 %; 0-11) |
| contrast: 10-40 grey levels | 17 of 53 (32 %; 20-46) | 0 of 84 (0 %; 0-4) | 14 of 53 (26 %; 15-40) | 0 of 84 (0 %; 0-4) |
| contrast: 40 or more | 8 of 33 (24 %; 11-42) | 2 of 192 (1 %; 0-4) | 7 of 33 (21 %; 9-39) | 2 of 192 (1 %; 0-4) |
| frame rate: 30 a second | 30 of 125 (24 %; 17-32) | 2 of 307 (1 %; 0-2) | 27 of 125 (22 %; 15-30) | 2 of 307 (1 %; 0-2) |
| distance: CLOSE | 8 of 29 (28 %; 13-47) | 1 of 61 (2 %; 0-9) | 8 of 29 (28 %; 13-47) | 1 of 61 (2 %; 0-9) |
| distance: MEDIUM | 17 of 39 (44 %; 28-60) | 1 of 146 (1 %; 0-4) | 13 of 39 (33 %; 19-50) | 1 of 146 (1 %; 0-4) |
| distance: DISTANT | 5 of 57 (9 %; 3-19) | 0 of 100 (0 %; 0-4) | 6 of 57 (11 %; 4-22) | 0 of 100 (0 %; 0-4) |

The set holds no track at 60 frames a second, so no rate of it speaks for the Galileo flyers, which sit there; and the
non-birds are nearly all long tracks (279 of 307 at 300 frames or more), so their false-alarm rate on short tracks rests on
17 and 11 tracks. Distant birds are named 9-11 % of the time, against 28-44 % close and medium: the distance bin, which the
outcome cannot set, carries most of the spread. PURSUE's objects are mostly short, faint and small: the pooled rates
overstate what the test hears there.

**The saved curves** (`run_set.Capture`, `replay`). What `flicker.judge` is given -- the curves of the object, its four
background apertures and its lights, its size and ring level on each frame, its smoothed track, the fields measured before
the judging (the codec's lines, the pictures' reading, the spans) and the planted dots of the encoding control where they
were made -- is kept, 10-40 kB a track, and judged again with no video. On the whole set, all 864 judgings (432 tracks, two
rules) replay to the call, the frequency and the amplitude their measurement gave. Two readings need the frames and are not
replayed: the astronomer's fold (it changes no call) and the scene's own motion at a beat (`shaken`, which keeps a bird from
being named), carried over from the measurement to a beat the replay finds at the same frequency. The curves are what the
photometry made, so a change to the photometry -- the aperture, the track's smoothing, the lights -- leaves them stale: then
the whole set and the sample are made again (`tools/controls/README.md`), and the rates of record move with the table, each
said.

**The sample** (`tests/golden/controls.csv`; the curves in the reference-data folder's `controls/curves/`). Twenty-seven
controls, each of a kind that says what it must give, under both rules:

| kind | what it holds | controls |
|---|---|---|
| bird | its own beat at a wingbeat's rate (whether the report names a bird, the record holds) | the labelled set's distant, medium and close birds; Galileo flyers 1-5 |
| flock | every member beats, each its own | PR135's six (frames 1240-1389) |
| non-bird | never "Beats like a bird" | the labelled set's distant and close drone, distant and medium airplane, distant and close helicopter, and AIRPLANE_064 (named on 2026-10-19 from an 8-Hz beat at 15 %; the camera's shake at the beat, item 17, has kept it from being named since 2026-10-31); the WA9ONY-5 balloon; PR23, PR055, PR071; and DRONE_059, a false alarm of record until 2026-11-13 (a 20-a-second source's held frames heard at a third of the frame rate; a cadence in most of its blocks since, section 35) |
| strobe | a light's flash train (item 13) | Svanström V_HELICOPTER_054 and _030 |
| false alarm | held as the record has it, with its cause: non-birds the report names a bird on the whole set | HELICOPTER_043 (a 2.09-Hz beat at 21 % under both rules: a fence line and poles passing behind it, which background apertures 25 px away do not see), HELICOPTER_024 (3.53 Hz at 7.8 %: named since the floor went to 7 %) |
| miss | measured, and no bird named | a distant bird with no beat where one would show (gliding, most likely) |
| no power | NO POWER | a distant dark bird the stage cannot decide on |

Each is also held, rule by rule, to the outcome the manifest records (its call, its train, its beat's frequency to a
thousandth of a hertz). After a change to the judging -- a gate, a floor, a rule -- `save_controls.py --record` judges the
saved curves again and writes the record anew, so the manifest's diff is what moved; `summarise.py --rejudge` does the same
for all 432 tracks of the set from their saved curves (the reference-data folder's `controls/set/`), with no video. The
false alarms of record are held as they are: a change that removes one is an improvement to be looked at and written down,
not a silent pass. The sample's labelled-set tracks were chosen knowing their outcomes, a distant one of each class among
them (the bin nearest PURSUE's), and each must give its own row of the whole-set table.

**The exact bound beside each control (B28).** For k events in n trials the exact 95 % interval is Clopper-Pearson's; with
none, its upper end is 1 - 0.025^(1/n). One silent negative control bounds the false-alarm rate only under 97.5 %; the four
of `test_golden` (PR23, the balloon, PR055, PR071) under 60 %, and three of them are not known non-birds from outside the
tool at all. So the goldens and the sample are regressions: they find a change. The rate is the whole set's: 2 of 307
non-bird tracks named, under 2.0 % (one-sided 95 %), under either rule. The suite prints the bound beside
each control and holds the rates of record (RECORD) to the table, a regression on the table with the rate from the set.

**Controls and regressions (B28).** A control has its answer from outside the tool: a label, a data bar, a laser, a header,
a filmed launch, a documented hand measurement. A regression holds the tool to what it said before. Of `test_golden`'s 38
checks, 20 are controls (PR113's two documented clicks, the WA9ONY-5 balloon, the audio cases, PR051's and Puerto Rico's
data bars, the Yemen laser, FLIR1's header and readouts, the ATFLIR displays, the strobe helicopters, the known cadences)
and 18 regressions (PR144's window and whole clip, PR43's link and band, the checklist on the case files, the birds' bands,
the projective test, the Galileo flyers and PR135's flock -- known birds by the beat the gates were tuned on --, PR23,
PR071, PR055, PR051's released-track null, FLIR1's glyphs, PR43's dash fitted whole (§45), the AARO
scorecard (§46: the labels are the tool's; AARO's answers are scored beside them), and the exercises). All four exercise answers follow the tool:
PR149's ship and PR113's field of view are from outside, the answers are the tool's. `test_controls` fails on a golden check
or an exercise page that is in neither list.

**The held-out third (B17).** It was drawn on 2026-10-17 and run once, on ffa9f3f (2026-10-18): 27 of 441 objects beat (6.1
%) against 6.4 % on the tuning set. Read again as B17 asks (the biology survey, 2026-11-01, on the census table's calls; no
new look at the videos): held out 6.8 % (30 of 439 objects in 29 videos; 0.9-16.5 % by video), tuning 6.3 % (45 of 715 in
58; 2.7-11.5 %), **a difference of -8.0 to +10.6 points** by video -- a difference under about 8 points could not have shown
-- and 2.1 % held out without LLE-PR002, which holds most of the held-out calls. `tools/sweep/looks.tsv` is the ledger of
looks (date, commit, gates, set, who, what was seen), with the draw, the look of 2026-10-18, its reading of 2026-11-01 and
the scene gate's look of 2026-11-02; `tools/sweep/agreement.py` states a look's agreement as a difference with a by-video
interval. The gates changed since ffa9f3f -- BIRD_FLOOR, the capped point disc, the shake gate, a stretch's own continuum,
the continuum null's correction -- have not met the held-out third, and it is spent for them: they are owed a set none of
them has met (AARO's resolved cases, the drone-show clips), entered as `owed`.

**The exotica list (T9).** After Breakthrough Listen's Exotica catalog (Lacki et al. 2021: prototypes, superlatives,
anomalies, controls), the suite prints one of everything the harness should hold. Held, with saved curves: a flapping bird
on a still camera, a flock, the labelled set's birds near and distant, a bird the test does not hear, a drone, an airplane
and a helicopter near and distant, an anti-collision strobe, a propeller's folded line (a candidate), held pictures' rhythm
heard as a beat, a background crossing, a helicopter's own modulation over the floor, a balloon, an object lost against a
hot roof, two unidentified objects, a track with NO POWER. Held elsewhere, with no saved beat curve yet: a codec's cadence,
sky lanterns, a hovering helicopter's rotor. Missing: a balloon with its payload resolved in the thermal infrared, flares,
an insect near the lens, a bird known to glide, a drone's light at night, a visible-band airplane at night with ADS-B,
airborne helicopters and aircraft from the flyers' cameras, a wind farm's lights, a satellite or star, sea glint and a
ship's lights, the sensor's own defects as curves.

**What it does not do.** It does not run the whole set after every change: that is the scheduled tool, about an hour and a
half six abreast (two CPUs a track, about a minute a track for both rules). The sample was chosen knowing each track's
outcome, so it bounds nothing; it holds the stage to what it did. The camera's shake is read, as `run` reads it, only at a
beat that would name a bird when the track was measured: judged again under a lower floor, a beat between the two floors has
no shake reading, and wants measuring again (done for the 7 % floor: IR_BIRD_065 and HELICOPTER_024, both rules). The labels
were made differently by class (the air-and-sea survey, 2026-11-07): the median share of a track's frames on an exact
straight line while the object moves -- key frames with straight lines between -- is 86 % on birds, 95 % on airplanes, 5 %
on drones and 5 % on helicopters. So on bird and airplane tracks the aperture follows a straight line between key frames,
not the object; within each class no bias in these rates was found, but any difference between birds and drones in centring
or jitter may be the labels'. A bird's label says a bird is there, not that it flapped: gulls glide, so the share of bird
tracks called is a floor on the test's sensitivity to flapping birds, not a measure of it.

## 45. The dash read better: the scene taken out, and the dash fitted whole (F11, F12, F41, F51; added 2026-11-07)

**What it answers.** `streak` (section 30) read a dash along one line of pixels on the frame as it is, and took its length at
half its peak through a blur borrowed from the scene's points. The single-camera survey of 2026-11-01 (its Part 9 §1.1-1.2,
1.6, and the rebuild's M2) found two better readings, both from other fields: read the frame less its neighbours, as
`autolink.follow_by_motion` already does (Kotera et al. 2019's background), and fit the dash whole, the trailed
point-spread function astronomy uses for a moving object on a fixed exposure (Vereš et al. 2012). This section is those two,
rebuilt, built, and held to drawn dashes and to PR43.

**The scene taken out** (`streak.Scene`, `quieter`). Each frame less the median of its six neighbours 4-6 frames away, each
brought onto it by one shift where that fits better than none (`propose.onto`). 4-6 frames, not `follow_by_motion`'s 1-2: a
long dash's nearest neighbours lie beside it, and the median would take part of it out. A frame is read on that picture
where it is quieter round the dash than the frame itself with a plane taken out (each picture's rms over the patch the fit
reads, with the dash's possible place left out); else on the frame, and the stage says on which frames, as no power. That is
no tuned threshold, only the choice of the picture with less else in it. It cannot tell a flat sky (where either reads as
well) from a ground that changed in a way one shift does not bring back (where neither does): both leave the frame as it is.

**The dash fitted whole** (`streak.fit_dash`, `trail`). The model is a Gaussian of width sigma drawn evenly along a segment of
length L through (cx, cy) at angle phi -- 0.5 [erf((u + L/2) / sqrt(2) sigma) - erf((u - L/2) / sqrt(2) sigma)] exp(-w^2 / 2
sigma^2), u along the segment and w across it -- times an amplitude, over a plane, fitted by least squares to every pixel of a
patch round the track's point 0.6 steps, three blurs and 5 px in radius (the part inside the picture at its edge). The
amplitude and the plane are solved exactly at each step (they enter linearly); the centre, length, direction and width are
searched from the track's point and direction, the half-peak length and the scene's blur, and from half and one and a half
times that length. Its integral, the flux, is the amplitude times L sqrt(2 pi) sigma, exactly, at any length. The fit
**holds** on a frame where its amplitude stands `FIT_Z` of its own errors from none (the least-squares error from the fit's
residual) and its length is within the frame's step, 1.2 steps + 3 px (`FIT_CAP`: a dash cannot outrun the step, and one that
seems to has taken in the next dash's ghost, a neighbour or the plane's edge). **No length is read under `FIT_MIN_PX`, 4 px**:
there every reader reads 2-4 px long and a round spot is not told from a short dash (the survey's 3,072 drawn dashes).

Where it holds on three frames or more with a length, the **exposure** is the median of the fitted length over the track's
speed, said with the half-peak reading beside it (which `streak` reported until now; its fields stay as `half_peak`), and the
share's first and last thirds of the frames are said, since PR43's runs from 0.37 to 0.78 (F27). Its **centres** are the
dash's own track points: `--centres` writes them as a track (the fit's centre where it holds, the track's point elsewhere, a
source column and the header naming which frames), and the stage gives the projective test's T (section 33) on that track and
on the track's own points, with each one's jitter. Its **flux** is a second clock on T, for a steady point closing straight at
a steady speed: the flux goes as 1/R^2 and R as (t_z - t), so the root of the flux as a / (t_z - t), the looming law with no
offset (`kinematics.looming_fit`), and T = t_z less the track's last frame, its 16-84 % band from the fit's bootstrap. It is
read only where the flux changes by `kinematics.TAU_LIGHT` in ln over the stretch at `TAU_Z` sigmas (the trend's sigma
widened for the fluxes' own wander, as the light-curve route of section 33), on 10 frames or more, and where the law describes
the root of the flux as well as a free quadratic does. It is said with what it assumes -- a steady point, the exposure and the
gain held, the picture's gamma left out (a video's levels compress a change of brightness by up to 2.2, and the clock reads
long by up to that) -- and beside it what the clip shows of two of them: the dash's share of the step at the start and the
end, and the scene's level round the dash.

**The survey's numbers rebuilt first** (`/scratch/mcdonald/s18-2026-11-07/streak/`, notes.md). The rebuild's own M2 script on
its own draws (seed 3) and on fresh ones (seed 11), about 187 dashes a family each: the shipped half-peak reading on the
frame against the same less the neighbours' median, all families 5.36 and 3.99 px rms against 2.14 and 2.28 (the survey's
5.03 against 2.08); cloud 7.0-7.4 against 0.8-0.9 (8 times), real PURSUE frames 5.3-11.4 against 2.0-3.6 (2.6-3.2), a flat
sky no change. On PR43 (its case file's track, the survey's own): the motion's scatter about a line in speed 6.39 px on the
frame and 1.93 less its neighbours on the 20 frames the survey's cut keeps (amplitude 15 DN or more and the length within
the cap: frames 50, 52, 58 and 71 out), the survey's 6.4 and 1.9 -- **but on all 24 frames 5.97 and 6.86**: three frames
read long once the scene is out, so the gain rests on a cut, which here is `FIT_Z` and `FIT_CAP` in place of a level in DN.
The fit's centres about a quartic 1.89 px against the track's 3.34, and its width 2.7 px against the scene's points' 3.6, as
the survey had them. **The flux clock does not reproduce as the survey stated it**: its "T = 0.63 s at the last frame" is
2 over the slope of ln flux on time (3.0-3.2 /s), which is tau at the stretch's middle, not at its last frame; fitted as
1/R^2 with its own t_z the flux gives **0.37 s at the last frame (16-84 % 0.32-0.43)**, where the track's projective T is
0.76 s -- at the middle the track says about 1.1 s against the flux's 0.66. The two clocks differ by about two times
either way.

**Drawn dashes** (M2's seven families by its own drawing, 609 dashes, 87 a family; the fit on the picture `quieter` picks):

| family | half-peak, frame | half-peak, less neighbours | fit, frame | fit, less neighbours | fit, picked | ratio |
|---|---|---|---|---|---|---|
| Gaussian spot | 0.50 | 1.17 | 0.17 | 0.20 | 0.17 | 2.9 |
| Moffat wings | 0.84 | 0.89 | 0.19 | 0.28 | 0.19 | 4.5 |
| a defocus disc | 0.72 | 0.54 | 0.19 | 0.19 | 0.19 | 3.8 |
| brightness ramped ±50 % | 4.68 | 5.11 | 1.00 | 1.06 | 1.00 | 4.7 |
| speed changing by a third | 1.63 | 1.64 | 0.21 | 0.23 | 0.21 | 7.7 |
| cloud of 10-40 % of the dash | 7.76 | 0.91 | 13.73 | 0.20 | 0.25 | 31 |
| real PURSUE frames (no shift) | 4.00 | 0.88 | 15.71 | 1.85 | 1.87 | 2.1 |
| all | 3.82 | 2.17 | 7.89 | 0.83 | 0.82 | 4.7 |

(rms px of the motion; "ratio" the half-peak on the frame over the fit on the picture picked). The fit is ahead in every
family, 2.1-31 times, its width 3.43 px against 3.23 drawn, its centre 0.07 px off (median); `quieter` took the frame less
its neighbours on 99 % of cloud and 93 % of real frames and on none of the flat ones. **A fit on a textured frame left as it
is reads the ground with the dash** (13.7 and 15.7 px rms, worse than the half-peak): the scene must come out for the fit
to help, and where no shift brings it back the stage says the scene was left in but does not refuse the fit.

**FIT_Z from a null.** The same fit started at three places a frame with no object (a dash's patch drawn from the same
lengths, a random direction), on the picture the stage reads there: on the six noise-only families, 1,562 places, z
reached at most 5.0 (99th percentile 4.5), so at 6 none holds (under 0.2 % at 95 %). On real PURSUE frames taken out with
no shift (the rebuild's stacks, 260 places), 40 % reach 6 and 25 % hold with the cap; with the neighbours brought on by
a shift, as the stage does (335 places), 36 % and 21 %: what a real scene leaves behind fits as a dash. So the fit's holding
is a guard against noise, not against the scene, and the fit is only ever started where the track says the object is. Of 112
dashes drawn on those registered frames the fit held on 110, two of them more than 5 px off (one ran onto a feature beside
the dash: 23.6 px read 45.6, its centre 21 px off); the median error was 0.13 px against the half-peak's 0.46 on the frame.

**Rendered frames** (`tests/test_streak.py`): a dash at 20 px a frame on a textured ground held still and moving 3 px a
frame, read half a frame on all 16 frames less their neighbours where the frame as it is spread 0.18-0.19 about it; a ground
new every frame left in and said; the dash fitted whole at 30 px a frame, its last frame's patch cut by the picture's edge,
half a frame, 2.0 px wide, its axis 0.02° off and its centres within 0.04 px; and a steady point closing straight on a
pinhole camera (its distance from the vanishing point as 1/(t_z - t), its flux as 1/(t_z - t)^2, T 0.6 s): the centres'
projective T 0.59 s and the flux's 0.60.

**PR43** (its case file's track, frames 50-74; `mcdonald streak` with the blur read off 40 of the scene's points, 3.6 px;
2026-11-07, test_golden's run on the final code). The scene came out on all 24 frames, the neighbours brought on by a shift
where that fitted better than none. The fit holds on 23 of 24 frames; frame 52's ran 40 px against a step of 12 (the cap).
Its width is 2.7 px at half its peak, against the scene's points' 3.6: the dash is drawn sharper than the scene's compact
spots, which are not points. **The exposure moves from 16.3 ms (0.49 of a frame, the half-peak length on the frame) to 20.3
ms (0.61, the fit's, a median over 21 frames)**; the half-peak length on the frames less their neighbours reads 15.2 ms
(0.45). The share runs from 0.50 on the first third of the frames to 0.72 on the last (F27: no one shutter). **The dash's
centres** give the
projective test's T 0.72 ± 0.03 s at a jitter of 2.8 px, the track's points 0.76 ± 0.04 at 2.9: the survey's 1.9 against
3.3 px (rms about a quartic) needs its cut, which dropped frames 58 and 71 -- on the stage's own rule frame 58's fit runs
20.5 px at a step of 18.5, within the cap, with its centre 10.5 px off the path (rms about a quartic on the 23 frames 2.99
against the track's 3.40; without 58 and 71, 1.96 against 2.91). Whether the chain's ghost a step behind each dash (the
survey's §1.6) draws it there is not shown. **The flux clock:** the flux grows 11 times over the stretch while the scene's
level round the dash falls 21 %, and the root of the flux as 1/(t_z - t) gives **T 0.39 s (16-84 % 0.33-0.47)** against the track's 0.76: short of it, its 84th
percentile under it. It rests on its last frames: with frame 74 read on the frame as it is (at the picture's edge) it gave
0.49 s (0.40-0.65). Read as clocks, the two do not show a steady point closing at a steady speed together; which condition
fails -- a source that brightens, the exposure (the share above), the gamma (which would make the flux's T shorter still) --
the clip does not say. With the scene left in (`--scene-in`) the fit holds on 21 frames, its centres jitter 4.5 px, and no
change in the flux stands out of its wander (3.5 sigma): no clock.

**What it cannot do.** Tell a flat sky from a ground no shift brings back (both are read as they are, and the fit then reads
that ground too); refuse a fit on such a ground; tell a dash from a copy of the last one left by the chain where the two
nearly touch; read a length under 4 px; or say which of its conditions a flux clock that disagrees with the track has broken.
`streak` is a command of its own, not a stage of `run`: no case report changes, and the case track stays the measurement of
record.

## 46. Known answers: AARO's resolved cases run blind (ROADMAP 0.5.0; added 2026-11-07)

**What it asks.** The All-domain Anomaly Resolution Office (AARO) has published videos with a stated resolution: birds,
balloons, sky lanterns, aircraft. Run through `mcdonald run` with only what a person holding the video and its public
description would have, does the report's conclusion agree with AARO's? Where it does not, which side's evidence is
stronger? The manifest is the data folder's `aaro/resolved_cases.csv` (checked by hand against AARO's case-resolution
reports): 14 videos with a known answer, 2 weak ones (closed as not anomalous, or not anomalous and unidentified), PR-003
held out (AARO's table says resolved, its own page unresolved), 14 unresolved, and two with no video.

**The protocol** (fixed before the first run; the runs' commands are in each case file).

- *Inputs.* The video, and the facts of its public description (AARO's imagery page, the text DVIDS carries): the
  sensor, the platform, the place and the year, the length, and a count of objects where the description's account of
  the sighting gives one (Puerto Rico 2, "splitting into two objects"; Al Taqaddum, Mt. Etna, the Middle East red
  balloon and Go Fast 1). Never AARO's assessment, its case-resolution analyses, or the manifest's answer columns. No
  description states a field of view or a distance, so none is given.
- *Blind in its inputs, not in its operator.* One agent did everything: it chose the segments, ran the commands,
  judged which object each run followed, and later read AARO's answers. Before the first run it had read the data
  folder's README, which lists each case's class, and the imagery page, whose titles carry the resolution ("Resolved as
  Birds", "Resolved as a Balloon"); it read the manifest's answer columns, the case-resolution reports and the earlier
  analyses only after every run had finished. What it knew could enter at three places: the segment of a long video, the
  judgement that a run followed the description's object, and a second run's marks (none was needed). Each rule was
  written down before it was used and each choice recorded with its reason, but the choices were made by someone who
  knew the answer. Linear sequential unmasking (Dror and Kukucka 2021) would split the work: a case manager who cleans
  the inputs, and an operator who never saw AARO's classes, choosing the segments and judging the followed object with
  the label hidden, a first impression recorded before any second mark. That was not done here and cannot be done
  after the fact. With every label "No physical conclusion" (below) it could not have moved a label; it matters most for
  the two bird cases, where a different segment is where a wingbeat would be seen or not.
- *The first run is the one press* (`auto_qt.AutoRun`), from the command line: `look --propose` over the segment (Find);
  the rows the one press takes -- the N likeliest where a count is given, otherwise row 1 and every row that is not
  weak -- each made an object folder by `mark --no-window --set` at the row's seeds; then `run --each`, which follows and
  measures each object over its marked frames and 2 s either side. The marks are recorded as an agent's, with the row
  and the rule as the reason; no track sheet is confirmed, so every report is provisional.
- *Segments.* A video of 35 s or less is opened whole; a longer one on 20 s (200 frames for Mt. Etna's 10 frames a
  second) chosen from a 40-tile overview of the whole video, where the description's object is in view and the picture
  steady, or where the description points (Puerto Rico's "splitting").
- *A second run* where the one press followed something other than the description's object: marks placed by eye on
  that object (the one at or nearest the boresight, which the camera holds, or the one the description names), read
  off enlargements, not copied from a detector, then `run --each` the same way. Both runs are reported: the first also
  measures Find.
- *The quick pass.* Every run skips `layers` and `integrity` (`--skip layers,integrity`), which with no scale or
  distance do not enter the conclusion's label (`Case.conclusion` reads the kinematics' rate and scale, the flicker beat
  and any given range or reference object; integrity adds a sentence, layers says whether the rate is against the
  background). Together they are most of a run's time, about 3 s a frame pair an object on three CPUs; with them the
  sixteen runs would not have finished in the session. What the skip costs: the checklist's camera and integrity rows.

**The rule, fixed before the runs** (`tools/aaro_blind.py`, `verdict`). AARO's resolutions say what the object is and
that it showed no anomalous performance. The report's label speaks to the second, and for a bird to the first. So
"Beats like a bird" agrees with birds and disagrees with any other class; "Subsonic motion" agrees with any prosaic
class; "Supersonic motion" disagrees; every other label is the report declining (**no power**). An agreement is
**informative** where the label names AARO's class (a bird's beat on birds), and only **consistent** where no prosaic
answer could have failed it ("Subsonic motion" beside a balloon): without the distinction, a tool with no identifying
power could agree on every case. A run's outcome counts only its objects on the description's object; a run with none
is **Find failed** (or, for a second run, the marks failed). A case is scored by its second run where it has one, else
its first. No power and Find failed are outcomes of their own, never folded into agree or disagree, which misstates
accuracy (Shinkins et al. 2013). The numbers of record, over the 14 known answers and each with its exact
(Clopper-Pearson) 95 % interval: **coverage**, the share the report answered (agreed or disagreed); **accuracy** on the
answered ones; agreement over all, informative and consistent apart. The 2 weak cases are read beside them. Fourteen
is a small set, and resolved cases are the ones easy enough to resolve: the agreement here is an upper bound for
unresolved footage (partial verification bias, Begg and Greenes 1983).

**Flow** (after STARD 2015). AARO's imagery and case-resolution pages: 34 videos. The manifest's cases with a stated
resolution and a video: 14 known answers (15 videos: the Atmospheric Wakes case has two sensors), 2 weak ones, and
PR-003, held out and not run; 2 resolved cases have no video and 14 videos are unresolved (0.6's catalog runs). Run: 17
videos, 16 cases, each once by the one press (no case called for a second run: every run followed the description's
object, judged from Find's strips before the answers were read). Find's rows taken: 54 objects (49 in the 14 known
cases), 51 of them on the description's object and 3 beside it (PR-004's rows 7 and 8, a faint spot riding just above the
bright point; the Middle East Object's row 4, a bright point among the overlay's marks). Answered: 0 objects; refused
(no power): 54. Scored: 14 cases, 0 answered, 14 refused, 0 Find failed. The sample is 14 by what AARO has published;
at n = 14 even 14 agreements of 14 would bound accuracy only above 77 % (the exact lower limit).

**The scorecard of record** (`tests/golden/aaro_blind.json`; `tools/aaro_blind.py --markdown` prints it, and the data
folder's `aaro/blind/README.md` has it case by case):

| | count | exact 95 % interval |
|---|---|---|
| known answers | 14 | |
| agree, informative | 0 | 0-23 % |
| agree, consistent | 0 | |
| disagree | 0 | |
| no power (the report declines) | 14 | |
| Find failed | 0 | |
| coverage (answered) | 0 of 14 | 0-23 % |
| accuracy on the answered | none answered | -- |
| the 2 weak cases | no power, both | |

Every one of the 54 objects' conclusions is "No physical conclusion": "The object moved about N pixels a second across
the picture. Its real speed and size cannot be found from this video alone." That is right as far as it goes. No
description gives a field of view, a distance or a reference object of known size, so no label can turn a rate in
pixels into a speed; and no label names a class except a bird's beat, which nothing here showed.

**Reading the refusals.** With no disagreement there is nothing to read for which side's evidence is stronger. The
refusals are read instead, by Dror and Scurich's (2020) convention: an inconclusive counts as an error only where the
evidence was enough to decide. Counting every refusal as an error, the worst case, is 14 of 14.

- *The twelve non-bird cases.* Every label they could reach needs a scale or a distance that neither the video's
  description nor the run's inputs gave. AARO resolved them with what the runs did not have: the aerostat's position
  (Al Taqaddum), a 3-D model fitted to the cloud deck and the wind (Mt. Etna), the aircraft's track and an STK
  reconstruction (Puerto Rico), the F/A-18F's speed and the winds aloft over every heading (Go Fast), air-traffic data
  (Western United States, the Wakes), the recorded wind (the European balloons, the red balloon). The refusals are not
  errors by the convention. Several displays carry what would have turned them -- Go Fast's ATFLIR prints a slant range
  (4.4 to 3.3 nmi), Puerto Rico's turret a slant range, an azimuth and the aircraft's position -- but no field of view
  in degrees, which `report CASE --fov ... --range ...` would also need.
- *What the refusals say that agrees with AARO.* No non-bird case was called a bird. On 9 of the 12 the beat test had
  power on the description's object (35 objects) and found no beat of its own; on Mt. Etna, Puerto Rico and Go Fast the
  tracks were 13 to 40 frames and the test could not decide. Mt. Etna is the case where AARO's partners first read a
  steady flicker as a bird's and AARO then put it down to turbulence and contrast stretching; the one press followed the
  object for 13 frames there, too few to test either way. A rate of false birds of 0 in 9 cases is bounded only below
  34 % at this size.
- *The two bird cases.* PR-016 and PR-002 are where the convention may count a refusal as an error: AARO's description
  of PR-016 cites "pulsating infrared return at a frequency consistent with wing beats", which is the beat test's own
  evidence. The one press followed one small point of each flock (PR-016 after the camera's field widens at 4.5 s;
  PR-002 after its gain change) and found no beat of its own: 3.77 Hz at 10 %, 3.7 times over the brightness's slow
  wander where 7.5 is needed; 6.00 Hz at 12 %, 6.1 times where 9.6 is needed. A probe outside the protocol and not
  scored ran the same one press where each flock is plainest (PR-016's first 4.5 s, before its field widens; PR-002's
  first 10 s, before its gain change). It did no better: on PR-016 Find's eight rows were all weak and its first a fast
  streak seen on six frames, followed for 77; on PR-002 a point of the line followed for 223 frames. The beat test
  refused both, as NO POWER: PR-016's point is "not brighter than the ring about it on every frame", and PR-002's "is
  lost against what is behind it on 40 of its 266 frames". So whether these clips hold a wingbeat the test can find is
  still open. The one press does not settle it: in a tight line of points 11 px apart, Find picks up one point at a
  time and the beat test's background ring takes in the neighbours. The test that would settle it is one bird marked
  by hand and measured the bird paper's way (`--aperture`, `--avoid` on its neighbours).
- *Western United States and twinkle.* Airliners up to 300 nmi away in infrared are compact sources, and a compact
  source twinkles. Object 2's flicker refused as "lost against what is behind it on 19 of its 145 frames", the refusal
  strong twinkle draws, which is the wrong reason for twinkle. Twinkle, and the blur it drives, is a rival to AARO's
  "shape changes from sensor vibration and autofocus" that nobody has measured on this clip.

**From resolved to unresolved footage.** The resolved cases are those easy enough to resolve (partial verification bias,
Begg and Greenes 1983). The odds of being right on unresolved footage are the resolved odds divided by a factor psi,
exactly; psi cannot be estimated here, and the assumption that it is near 1 is an assumption. Here there is no
accuracy to carry over: what carries is the coverage, which is no better on footage harder to resolve.

**AARO's answers are an imperfect reference.** Ten of the cases carry likelihood words. By ICD 203's ranges the chance
that at least one of them is mislabelled is 27-65 %, and AARO pairs "high confidence" with "almost certainly", which ICD
203 keeps apart. A disagreement here would have been read as a disagreement, not as the tool's error.

**Find, measured by the first runs.** On PR-004, PR-005, PR-006, PR-009 and PR-010 one bright point the camera follows
came back as five to eight rows, the same object in successive stretches, and the one press's rule (row 1 and every row
not weak) made each a case of its own: 37 reports for 5 objects. `several`'s same-object rule joins tracks that share
frames, and these do not.

**Integrity on a known flock, by a slip.** PR-016's run ran `integrity` too (its skip was lost to `sbatch --export`
splitting the value at its comma). Its "layer order: symbology" check flags the bird it followed as possibly laid over
the picture: it "crosses lines drawn frame by frame" in 13 frames, and over the object's middle none of their pixels keep
the line's level (76 DN, the object 255). The bird is one of a row of bright points 11 px apart, each ringed dark by the
sensor's edge enhancement; the dark rings between points in a row make the dark ridge through the object that the check
reads as a drawn line. That reading is not yet checked frame by frame, and nothing here changes the check.

## 47. What the conclusion rests on, how sure it is, and the beat against labelled tracks (E7, S17, S20; added 2026-11-07)

The checklist (section 38) answers each test in a word. It does not say which answers the conclusion rests on, how much
each weighs, or how sure the conclusion is. Jacob's diagnostic-accuracy survey (2026-11-07; its three rebuilds, `verify/`)
measured the beat test against the labelled infrared set as a diagnostic test, and found the checklist's own words wrong
in four places. This section is the fixes, then the three additions. Every number here was rebuilt from the controls
harness's whole table (432 tracks, 365 clips, 0.4.3; session 18's `harness`) before anything was built
(`reasons/scripts/rebuild.py` of the session's notes).

**The control population** (`controls.py`, `controls_beat.csv`). The harness's table, cut to what the report reads, ships
with the package (54 kB): each labelled track's clip and class, what it offers (frames, frame rate, contrast), and under
each rule its call, beat, amplitude, whether the beat comes back, the shake, and `needs` (`flicker.analytic`'s
`with_floor`). `python3 -m mcdonald.controls $MCDONALD_DATA/controls/svanstrom_tracks.csv` remakes it after the harness
measures the set again; test_reduction holds it to the data folder's table. `controls.kind` answers the checklist's beat
row for a track of the set by the report's own rule, `controls.weigh` gives the likelihood ratio of an answer --
P(answer | bird) / P(answer | not a bird), over tracks -- with a 95 % interval from 2,000 resamples of clips (birds and
the rest apart, numpy's generator seeded 7, all at once: 20 ms a kind; the table below is the rebuild's own draw, whose
intervals differ from the package's in their second figure), at the report's BIRD_FLOOR as it stands, under the rule the case was measured by. An answer
fewer than ten tracks gave carries no ratio (the harness's STRATUM_MIN, a judgement call); one whose interval holds 1
carries no weight.

| the beat row's answer | stage, 8 % | paper, 8 % | stage, 7 % |
|---|---|---|---|
| Yes, a bird named | 35.6 (12.2-inf; 29/125 v 2/307) | 63.9 (16.9-inf; 26 v 1) | 24.6 (9.9-inf; 30 v 3) |
| Partly, too faint | 0.33 (0-1.09; 2 v 15) | 0.43 (0.08-1.09) | 0.18 (0-0.74) |
| Partly, one stretch | 0 v 5: no power | 1 v 3: no power | 0 v 5 |
| No (with power at the floor) | 0.42 (0.31-0.55; 42 v 246) | 0.43 (0.32-0.56) | 0.37 (0.27-0.51) |
| Can't tell, too noisy for a bird's beat (was No) | 4.48 (2.58-8.18; 31 v 17) | 4.62 (2.63-8.57) | 4.42 (2.71-7.84) |
| No, a rhythm outside a wingbeat's rate | 6 v 2: no power | 3 v 2 | 6 v 2 |
| Can't tell, refused | 1.94 (0.81-3.75; 15 v 19) | 2.09 (0.96-3.80) | 1.94 |
| Can't tell, the shake | 0 v 1: no power | 0 v 1 | 0 v 1 |

*Since the record was made again (2026-11-13/14: N3's revision and the held pictures' cadence read in blocks; method
sections 13, 35 and 44)* the package's own table gives, at the same seed: a bird named 71.2 (19.3-inf; 29 v **1**) under
the stage's rule at 8 %, 63.9 under the paper's (unchanged: it had 1 already), 36.8 (13.2-inf; 30 v 2) under the stage's
at 7 %; too noisy for a bird's beat 4.62 (2.68-8.51; 32 v 17), 4.77, 4.54; a refusal 1.81, 1.96, 1.81. The one non-bird
named fewer is IR_DRONE_059, whose 10-Hz beat was its source's held pictures. On the fourteen reference case files the
quoted weight of a named bird is unchanged ("about 33 times", the rule they were measured by), and the noisy track's moves
from 4.5 to 4.7 times on five objects and 4.4 to 4.5 on one.

**Four fixes to the checklist** (`Case.checklist`, `Case.placed`, `Case.beat_power`; `stages.track_placed`).

1. *The beat row's "No" held two answers.* The flicker stage sets `beats` False whenever nothing passes, whatever the
   track's power; the report never read `analytic`. A track whose noise needs a 12 % beat to find one three times in four
   answered "No" as a track that could hear a 2 % one. Now "No" only where `beat_power` (the least `with_floor` over the
   objects measured, or the white-noise amplitude where there is no background) is at most BIRD_FLOOR -- where a beat
   strong enough to name a bird would have been found -- and "Can't tell" above it, with the amplitude it would need. The
   rule is the stage's own power at the floor the report already names a bird from; no threshold was chosen. On the set,
   the old "No" put 31 bird and 17 other tracks without that power beside 42 and 246 with it; by clip, 22 of 293 "No"
   clips had no track that could have heard the floor, 45 % of them birds against 22 % of all clips, LR 3.0 (1.35-6.7)
   -- the diagnostic survey's FX4, rebuilt to the digit. Such a "No" pointed toward a bird; the one left points away
   (0.42). The amplitude follows the object's own residual after one sinusoid, so a real beat that wanders raises it
   (x1.5-3 when planted, the survey's claim 4; with every `needs` divided by 1.9 the clip-level ratio is 1.8, 0.34-9.7):
   the new "Can't tell" is right either way, and it carries no weight in the reasons below.
   And a refusal (`beats` None: the background beats with it, the codec's line, members in step) with a peak measured on
   the way answered "No", because the no-power branch came after it: 2 tracks of the set under the stage's rule, 5 under
   the paper's (none of the reference objects). It is "Can't tell" now, in the stage's words.
2. *Who chose the object.* `run --track` alone records nothing of who made the track, and the row answered "a person placed
   the marks on the frames by hand" there -- on 29 of the 31 reference objects, each measured on a paper's track whose own
   marks files say "agent: from the paper's track". Now the track stage records `placed_by` and `placed_said`: from the
   marks where there are marks, and for a track file given alone from its own first lines (`stages.track_placed`: a link
   from hand marks or a marks file's hand marks is a hand's; marks that say they are not, or `share make`'s agent's track,
   are not; a file that says nothing is not known). The row is Yes, No or "Can't tell" ("the track was read from a file,
   X, that does not say who or what placed its points") accordingly; a case from before is read from its run command
   (`--marks` with every mark a hand's is a hand's; `--track` alone is not known).
3. *What was looked at.* `run --i-looked` asserts a look before this run draws its sheet (the flag's own help: "the track
   sheet from a previous run"). The verify stage's result records how ("yes (--i-looked)"), and the row now says it: "a person said with
   --i-looked, before this run drew its track sheet, that they had looked at the sheet: the look was at an earlier run's
   sheet, not this one"; the window's question and the later confirmation each have their own words.
4. *Integrity's row* (the survey's Dx7, read in the code and confirmed here). Its checks have never been tried on a real
   insert -- section 2's validation says so: the corpus holds no known one, and a synthetic disc stands in -- and one false
   flag is known (AARO's PR-016: a line of birds whose dark rings `_overlay_drawn` reads as a drawn line; session 18's
   `aaro`, open). A "No" from its passes said more than that. The row's question is now "Is it consistent with the
   camera's own picture, rather than added afterwards?", answered Consistent, Inconsistent or Can't tell, each decided
   answer with "no check has been tested on a real insert" (and, where layer order flags, its known false flag).

Also: `run`'s track sheet carries the release's id at its head, not its title (`stages.run_case`): 22 of PURSUE's 144 titles
describe the object as an observer saw it ("Spherical", "TIC TAC", "fast moving"; the survey's FX7, by hand), and the
person judging the sheet should not read that first. `mcdonald tracksheet`'s own command keeps the title.

**What the conclusion rests on** (E7; `Case.reasons`). At most four reasons under the conclusion, the heaviest first --
the rule a US lender follows when it declines (Regulation B's statement of principal reasons; four in the model forms).
The reason the label stands on comes first: the beat for "Beats like a bird", the speed or what it lacks for the speed
labels and "No physical conclusion". Then the weighed reasons, by the weight that survives their interval (|ln| of the end
nearer 1), then the unweighed in the checklist's order. A weight is a likelihood ratio wherever a control population gives
one -- today the beat alone -- said as "about 25 times as common on birds as on aircraft, drones and helicopters (at least
9.6 times, at 95 % confidence)" (a bird named under the stage's rule at §43's 7 % floor; 33 under the paper's, at least 12;
at 0.4.3's 8 % it was 36 and 64); a speed that follows from what was given is a bound ("as sure as those inputs"); the
look-alikes, integrity and a flash train have no control population and say so, carrying no weight. **The beat counts
once.** The stage's readings of it -- the whole track, the windows, the continuum, the background, the paper's rule --
read one curve and pass together: on the 288 answered non-birds, 1 passes all five where independence predicts 0.0034 %,
with phi 0.7-0.9 between the stage, the paper's rule, comes-back and the continuum (the clinical rebuild, DXC7). Counted as
separate support they would multiply one finding's weight. A test that could not decide carries no weight even where
the set's mix gives its answer one (a track too noisy to show a bird's beat was 4.5 times as common on birds, because the
set's birds are faint: said, and weighed at nothing). A one-stretch beat had a ratio of 0.57 for a bird on 0.3.1 (not
evidence for one) and on 0.4.3 the category holds 4-5 tracks: no power.

**How sure** (S17; `Case.grade`). Four of GRADE's domains (Guyatt et al. 2008, BMJ 336:924), each computed from the case,
never given by the analyst, start the conclusion at the top level and take it down one for a serious concern, two for a
very serious one: *risk of bias* (the track sheet not looked at; the object picked by an agent or the computer, or by
nobody recorded, which no longer counts once the sheet has been looked at; integrity inconsistent -- one serious, two or
more very serious: no person's eye recorded at all); *inconsistency* (a named beat the whole track's test does not find,
only its windows; under half of a flock's measured members beating; integrity's checks both passing and flagging);
*indirectness* (for a bird named, the clip outside the labelled set's population, `controls.inside`: not 30 frames a
second, a track under 150 frames -- the set's 17 non-bird tracks there bound a false-alarm rate only under 16 %, DXC5 --
or a flock, where the set's tracks are single; for a speed label, a field of view that is a guess); *imprecision* (a named
beat whose amplitude less twice its own error, sigma sqrt(3/n) from the closed form, falls under BIRD_FLOOR; a speed
whose band, twice its spread along the track, reaches the speed of sound anywhere from 295 m/s at 11 km to 343 at sea
level). The proposed levels are GRADE's: High, Moderate, Low, Very low -- not A-D, which GEIPAN uses for identified to
unexplained (F56); the names are the maintainer's to choose. "Under half the members" and "under 150 frames" are judgement
calls. The grade is said where the label is said: under the conclusion's sentence ("How sure: low. Nobody has said they
looked at the track sheet and who picked the object is not recorded."), in the window card's More, on each object's line
of `several`'s list, and as `grade` in `run --json` and `report --json`.

**The beat against labelled tracks** (S20; `figures.beat_controls`, `controls.screen`). Every track of the set the stage
measured a beat on, its strongest rhythm's rate against its strength on a log scale, birds blue and the rest amber, filled
where the rhythm was the track's own and open where it is only the strongest peak, the wingbeat band shaded, the floor
dashed, the object red (`<case>_controls.png`, in the report's figures wherever the flicker stage measured a peak). Under
it, the words that rest on it: of the labelled tracks with a rhythm of their own at a wingbeat's rate (31 birds, 23
others under the stage's rule), how many beat at least as strongly; "consistent with the birds" where at least one in
twenty of theirs does (a judgement call); the others "not screened out" where any of theirs does, and "screened out" only
where none of the 288 the test could judge does, with the exact one-sided bound that leaves (under 1.04 %). What the plot
must not be read as: evidence that the tests hear wingbeats. Ranked by this strength a bird outranks another track with
an AUC of 0.935 (stage; 31 v 23) and 0.960 (paper; 31 v 28) among tracks with a bird or one-stretch call -- the floor's
own question; 0.816 / 0.824 over all 432 tracks with the raw strongest amplitude wherever one was read; and **0.884 /
0.894 among tracks with no rhythm of their own at all** (73 v 263). Most of the separation is that the set's birds are
faint (contrast median 19 grey levels a pixel against 56), so their brightness wanders more, beat or no beat; the
caption says so.

**Reference objects that move** (the 14 case files read again by this code; not remade). Who chose the object: 29 of the
31 Yes -> Can't tell (each measured on a paper's track given with `--track`); PR113 and PR43 stay No. The beat: six No ->
Can't tell, too noisy to show a bird's beat at 8 % and at §43's 7 % -- PR097 objects 4 and 7 (needing 8.4 and 10.8 %), PR099 object 2
(16.7 %), PR141 objects 1 and 2 (24.3, 17.2 %), PR144 (13.5 %); PR097 object 2 (4.3 %) stays No. Integrity: PR113, PR144 and
PR149 No -> Consistent. No label, headline, number or bottom line moves. Every object grades Low or Very low: none has had its
track sheet looked at, and 29 do not record who placed their track (risk of bias, very serious); looking at the sheet raises each by two levels.

## 48. Three ports from finance: the jitter read without a model, which motion models survive, and the traffic light for the suites (E6, E22, E20; added 2026-11-07)

The economics survey (2026-10-28) read a track as a price series sampled fast with noise on every reading. Three of its ports are
here: a check on the band's nugget that needs no model (E6, its §1.1 and §6.1), the set of motion models a track cannot tell apart
(E22, §1.7), and the suites' checks on drawn data read by a binomial zone (E20, §5.5).

### 48.1 The jitter read without a model (E6; `kinematics.model_free`)

**What it answers.** The band's nugget is REML's, inside its model of a line, a Matérn-3/2 wander and white jitter (§32). Where the
model is wrong -- a wingbeat in the track, which the wander cannot follow -- the nugget takes the misfit in as jitter, and the band's
error and every test held to the nugget (M1's "fits", §33) take it in with it. Finance reads the same noise with no model: bid-ask
bounce makes successive price changes negatively correlated, and Roll (1984) read the spread from that covariance. On first
differences a wandering velocity makes the covariance positive (Roll's "wrong sign": 80 of 88 recorded axes), so the reading is moved
one difference up. White jitter of variance s² gives the second differences Δ²x a lag-1 autocovariance γ₁ = -4 s² and an
autocorrelation ρ₁ = -2/3 exactly; a once-differentiable wander gives them the second differences of an integrated Brownian motion,
ρ₁ = +1/4, and little variance at the frame scale (on the K8 track about 1 % of the jitter's). So √(-γ₁/4) is a nugget read without a
model, and ρ₁ well above what the model draws says the path bends at the frame scale.

**The reading.** On runs of consecutive frames only (a gap breaks a second difference), over the band's own window and its kept
points (the jumps it names dropped, the middle BAND_NMAX), against the band's wander-only model (before M8's beat): γ₁ and ρ₁ of the
second differences, read the economics survey's way (`second_differences`, its `model_free`), at least FREE_MIN = 20 side-by-side pairs.

**The flag, from a null.** The survey's line, ρ₁ above -0.40, was set by eye. Here the band's own fitted covariance (the line, the
wander and the nugget, no beat) is drawn FREE_DRAWS = 1000 times on the track's own times and gaps -- its Cholesky factor times
standard normals; a second difference takes the line out -- and each draw read the same way. A coordinate's p is the share of draws
whose ρ₁ reaches the track's, (1 + k) / (1 + 1000); the track is flagged where either coordinate's p is under FREE_ALPHA / 2 = 0.005,
so a track with no beat is flagged about one time in a hundred whatever its wander and jitter: a parametric bootstrap. The ratio of the
two nuggets is quoted with the central 99 % the same draws give it (each draw's read nugget over the nugget drawn), and REML's nugget
"agrees" where the ratio sits inside.

**The null, measured** (REML refitted on every draw, the band's window; 2026-11-07): tracks drawn with no beat --

| drawn | flagged | the ratio outside its quoted 99 % |
|---|---|---|
| the K8 track (a 5-px wander over 1 s, 0.5-px jitter), 150 points | 1 of 300 | 1 |
| the same, 300 points | 3 of 200 | 0 |
| white jitter alone, 150 points | 4 of 300 | 1 |
| a fast wander (2 px over 0.2 s), a small nugget (0.1 px), the detector's memory (B2's dots) | 0 of 600 | 0 |
| a 60-fps flyer-like track | 1 of 200 | 0 |
| each of the 40 recorded tracks' own fitted covariance on its own times, 25 draws each | 5 of 1,000 (PR135's six: 0 of 150) | 1 |
| **all** | **14 of 2,600: 0.54 %** (0-1.5 % by family) | 3 (0.1 %) |

So the flag's false alarm is half the 1 % its threshold states, and the words give the measured one (FREE_FALSE): "tracks drawn with
no beat are flagged 0.5 % of the time, 1 % at most". The ratio's quoted range is wide: REML's nugget and the one read without a model
read the same jitter, so their ratio scatters less than the read nugget over the true one, which is what the range is drawn as; it is
quoted as what the model draws, not as a test. **Power** on the K8 track (0.5-px jitter): a 6-Hz beat of 0.8 px is flagged 99 times in
100, of 0.4 px 27, of 0.2 px 5; of 0.4 px at 10 Hz, 3.

**What it does and does not flag.** A beat that REML's nugget took in is flagged: PR135's six. A beat that REML's wander took -- a short
range and a small sill that follow the beat -- is not, because the model then draws the same curvature: a drawn 0.8-px 6-Hz beat read
ρ₁ -0.16 against its model's -0.14, and Galileo flyers 2, 4 and 5 (the survey's -0.40 line would have flagged them) have models that
draw +0.13, -0.20 and -0.23 themselves. That beat is the backtest's to find (E1's rhythm left, M8's beat held). So the words never say
"no beat": unflagged, the band's wander and jitter draw what the track does at the frame scale.

**On the recorded tracks** (the survey's 46, read from today's case files and golden tracks, 2026-11-07). The survey's numbers first, its
own estimator on every point: the ratio's median **0.80** (IQR 0.63-0.92, 77 axes, 95 % within a factor of two), PR144 1.00 / 0.93,
PR135's members **0.39-0.73**, Roll's form the wrong sign on 80 of 88 axes -- as the survey had them. On the band's window the median
is 0.80 (IQR 0.61-0.91, 80 axes) and **20 of the 39 tracks read are flagged**: all six PR135 members (p 0.001 on both axes, ρ₁ -0.17 to
-0.39 where their models draw -0.60 to -0.65), PR097's objects 1, 3, 4, 5 and 8, PR099's three, PR41, PR077's object 1, PR085, PR071
and flyers 1 and 3. PR144 is not (1.00 / 0.93 inside 0.70-1.29, ρ₁ -0.64 / -0.64 against -0.62 / -0.65), nor PR141's two, PR079,
PR088's two, FLIR1, the balloon or PR23. Frames that are not consecutive give no reading (PR44, PR149, PR055's sphere, PR051's release).

### 48.2 Which motion models survive, as a computed set (E22; `projective.confidence_set`)

**What it answers.** `projective.fit` and `projective.turn` (§33) ask one model at a time and compare models in pairs, each pair by
its own rule: constant velocity against constant image speed against a free quadratic, a bend against none. Forecasters ask which of
several models the data cannot tell apart with one statistic: the model confidence set of Hansen, Lunde & Nason (2011), the models not
rejected at a level on their out-of-sample losses, with the losses' dependence held by a block bootstrap. It shrinks as the data gain
power and keeps every model where they have none, so it says NO POWER on its own.

**The models.** Three, each two-dimensional, fitted by least squares: a line at a steady image velocity (four numbers: motion across
the line of sight at a fixed range); constant velocity in projection, a straight image line whose distance from its vanishing point
goes as 1/(t_z - t) (five: §33's model); and a steady turn, a circle drawn at a steady image speed (five: a start, a velocity and the
rate it turns, x = x₀ + S v_x - C v_y, y = y₀ + C v_x + S v_y with S = sin(ωτ)/ω and C = (1 - cos ωτ)/ω). Given its one nonlinear
number (t_z, ω) each is linear, so that number is the best of a log grid of MODELS_GRID = 120 values a side (a 6 % step), refined
between its neighbours: t_z after the forecast or before the first point fitted, out to FAR spans; ω up to two turns over the points
fitted. The projective model holds the line as t_z goes far, the turn as ω goes to nothing; on a straight steady track all three hold
the truth.

**The losses.** One-step forecasts: at each of up to MODELS_ORIGINS = 150 origins, spread from the first fifth of the track (ten
points at least) to its end, each model is fitted to the points before and asked for the next one; the loss is the squared distance.
A misspecified model's forecast misses by its misfit at the end of the window, so the losses carry the comparison; a flexible model's
estimation noise is charged to it out of sample, which is the set's own penalty for a parameter.

**The set.** Hansen, Lunde & Nason's elimination rule T_max: each model's loss less the mean of those left, studentised by a
stationary bootstrap of the origins (Politis & Romano 1994; MODELS_BOOT = 2000 resamples), the worst model out while the test
rejects; a model's MCS p-value is the largest p of the tests up to its leaving, and the set at α = 0.10 the models whose p is at least
0.10. The losses run together where the track wanders, so the bootstrap's mean block is the track's own memory: MODELS_DECAY = 2.74
times the range of the wander left about the model that forecasts best (a line, a Matérn-3/2 wander and a nugget fitted to that
model's residual over the whole track by REML, on every k-th point to 150; the range where its wander gains Δln L ≥ 10, else none),
2.74 ranges being where a Matérn-3/2's correlation falls to 5 %; at least one origin, at most a third of them.

**The null: the true model's coverage at 90 %** (60 drawn tracks a cell, 150 points at 30 fps, about 300 px long; a line at 60 px/s, a
straight flight closing or receding with 2.5 s to the camera's plane, a 90° steady turn; 2026-11-07):

| drawn | white jitter (0.3 px) | a 1-px wander over 1 s | K8's 5 px over 1 s | PR144-like, 1.4 px over 1.9 s | bird-like, 2 px over 0.4 s |
|---|---|---|---|---|---|
| a line: kept / set size 1, 2, 3 | 60 / 26, 34, 0 | 52 / 8, 37, 15 | 38 / 10, 12, 38 | 44 / 15, 33, 12 | 57 / 2, 10, 48 |
| closing: kept / alone | 60 / 60 | 60 / 60 | 60 / 60 | 60 / 60 | 60 / 60 |
| receding: kept / alone | 60 / 60 | 60 / 60 | 60 / 60 | 60 / 60 | 60 / 60 |
| a steady turn: kept / alone | 60 / 60 | 60 / 60 | 60 / 60 | 60 / 60 | 60 / 60 |

Where the track is one of the three under white jitter, and for every closing, receding and turning track under every wander tried,
the true model is kept every time, and alone where it is not the line. A straight line with a wander on it stays in the set only 63-95 %
of the time, not 90 %: none of the three is then the path, and a model that bends forecasts a wander better than the line does. So the
set ranks forecasts, and names a motion only where nothing wanders about the best model. That is the rule the words follow: where the
wander left about the best model gains Δln L ≥ 10 (`range_s` > 0), the paragraph says which model "predicts it best" and that the track
"also wanders about it, so this ranks the predictions and does not name the motion"; otherwise the line's leaving names the motion,
and where the line stays, the models that left "predict it worse" -- each holds the line, so none is ruled out as a motion. A set of all
three says the track cannot tell them apart.

**Against M1 on the recorded tracks** (the 31 objects of the 14 case files over the stretch their kinematics stage read, and the golden
tracks; 45 sets, PR113's four points none). M1's projective test describes the trend only on 44 of them and fits PR43, whose set is the
projective model alone (MCS p 0.005 for the line and the turn): the two agree that it closes. On the 44 the set keeps all three nine
times (PR088's two objects, the golden PR144, PR071, PR23, FLIR1's two tracks, PR051, Svanström V054) and leaves the line out on the
other 35 (the projective model alone 12 times, PR135's objects 1-3 among them; the turn alone 8 times; both 15 times). Where M1 chose a
model for the trend, the set keeps it 16 times of 24. But every one of the 44 wanders about its best model, so on each the set ranks the
forecasts and names no motion, as the null requires -- the same verdict as M1's "describes its trend", reached another way.

### 48.3 The traffic light for checks on drawn data (E20; `tests/traffic.py`)

**What it answers.** A check that counts an event over random draws -- a band's misses, a test's false alarms, a planted
signal found -- and holds the count to one threshold flaps: a change that only reorders the draws, another machine's rounding,
or a stated rate that is right puts the count across the line by chance. The Basel Committee (1996) reads a value-at-risk
model's exceptions by their binomial distribution at the stated rate: green while that many or fewer come 95 % of the time
from a model that is right, yellow past that, red past 99.99 % (250 days at 1 %: green 0-4, yellow 5-9, red from 10). The
suites do the same. A check states its rate and its draws; a count in the green passes, one in the yellow prints a `WARN` line
and does not fail, and a red fails. A count at or under the expected one is always green: with few draws at a small rate, none
at all is already likelier than 95 %. A two-sided check (a coverage too wide as well as too narrow) holds the count from both
sides. The draws must be independent: whole tracks or curves, not the frames of one track, whose errors run together -- so
K8's coverage of the rate at every frame, 3,840 frame-coordinates from 16 tracks, is counted at each track's middle frame,
x and y apart, 32 draws at 4.55 %.

**Where it is used.** Every check on drawn data that counts an event against a rate: K8 (coverage, the path speed and the
fastest, the memory rule, constant and not), E4's clean and gridded tracks, E1's lights, E12's bound, M5's t_z and depth
bounds, M4's loops, tau's wandering sizes, E6's flag (test_reduction); the continuum null, the steadiness and train tests,
the frequency's error, the codec's line, the held words of M3, the drift test, sompi on grain (test_measurement); the size
trend and the rate's steps (test_camera); noise records (test_audio). Each states its rate, from its own measurement where
one exists and as a flagged judgement where none does. Spreads and medians, counts over the frames of one clip, a module's
own Monte Carlo p, and maxima over draws are left as they were.

## 49. The pointer as a stale price, one k from the routes that agree, the zoom as a discontinuity and its ladder pooled (E14-E17; added 2026-11-07)

**What it answers.** Two questions the economics survey of 2026-10-28 (§1.5 and §3.4 there, in the uap repository) put to the
routes to k. Is the slope `slew` reads off a pointer the pointer's, or its lag's? PR051's MTS-B dial sits still for up to 2 s
while the azimuth moves 0.6 deg and then catches up (§17), and with the hold given its 7-14 s claimed c = 2843 px/deg for a
truth of 2230. And where a case has two routes to k -- a graticule and a slew, the windows of one zoom state -- do they agree,
and what is the one k they make? Finance met the first as the stale price and the second as forecast combination.

**The stale price (E14).** A thinly traded stock's last price is old, so its return looks unrelated to the market's today and
related tomorrow; betas from short intervals are biased (Scholes & Williams 1977; Epps 1979). A pointer drawn on a grid "sits
still and jumps", and a dial that stalls is a stale price exactly. Every window `slew` claims from (not a data bar's, not the
blocks') is read four ways beside its level fit (`slew.stale_check`, `stale_into`):

1. *The pointer's own clock.* Its updates are the readings where it moved half a grid step or more from the last update
   (`pointer_updates`): the stale price's trades.
2. *The lead-lag* of Hoffmann, Rosenbaum & Yoshida (2013), built on Hayashi & Yoshida's (2005) sums over overlapping intervals:
   the pointer's increment over each interval between two updates against the scene's increment over the same interval
   shifted by l frames, summed, for |l| up to 2 s; the lag is the shift where the contrast peaks (`lead_lag`; l > 0, the
   pointer after the picture). With a hold fitted both increments lose their window's mean rate first; with a hold given
   the pointer's loses the hold, and a steady pan is timed by the scene's own unevenness.
3. *The stall*: over each interval between updates, the turn the pointer owed the scene while it sat still -- the scene's
   move over c and the hold's share -- in steps of its own grid (`stall`). A dial on its grid moves before it owes much more
   than a step.
4. *Dimson's (1979) summed slope*: the pointer's turn over a block regressed on the scene's move over the block before, the
   block and the block after (overlapping blocks of 0.5 s at least, a hold where one is fitted); the three slopes summed are
   the pointer's turn per pixel of scene whatever its lag within a block, and its 95 % interval comes from a bootstrap over
   1-s blocks (`dimson`).

The lag and the stall are judged against the window's own null: pointers drawn with no lag on the window's own scene path at
the fit's c and hold, on the pointer's grid at a random phase with its scatter, on the frames the pointer was read, 100 of them
through the same estimators. A lag is real where 5 % or fewer of them reach it, as far from zero and gaining as much over zero
lag (`STALE_ALPHA`); a stall is beyond its grid where 5 % or fewer owe as much. **A real lag refuses the claim by name where it
lasts longer than the bootstrap's blocks** (`BLOCK_S`, 1 s): c's interval draws 1-s blocks as if the pointer's errors forget
themselves within one, and a pointer that runs further behind carries them across blocks, so the interval does not hold. A
real lag shorter than that refuses only where Dimson's 95 % does not hold the level fit's c; otherwise it is said. A lag is
never taken out of c: on the real pointers that agree with their zooms the lead-lag peaks broadly over a few frames, and c
moved by it would carry that noise where the level fit had survived. **A stall beyond its grid is said beside the claim and
refuses nothing**: its null rests on the window's own fitted c and hold, and on slews drawn with no lag it came out beyond the
null and over a block in 15 of 60 synthetic windows and 11 of 188 drawn on PR27's and PR057a's real scene paths -- a slow hold
fitted a little off makes a long still stretch look owed.

**Measured** (`stale_null.py`, 2026-11-07, job 21205; synthetic slews with a hold, a 1-3-deg slew and a 0.2-0.45-deg grid, and
pointers drawn on the real scene paths of PR27's and PR057a's ten claim windows, at their c and hold). Drawn with no lag, **no
claim of 248 was refused** (60 synthetic, 188 on real paths), though the lead-lag was called real in 12 synthetic and 11 real
ones (shorter than a block, Dimson holding c). Drawn 0.2 s late: refused 24 of 239 (0 of 60 synthetic); 0.5 s late: 108 of
216 (10 of 60 synthetic, where c was off by 11 % at the median); a dial stalling for two steps: 2 of 214; for three steps
shown 10 frames late: 36 of 202. So the refusal is a strict one: it catches a pointer that runs a block or more behind, and
half of those half a block behind on real scene paths, and leaves most shorter lags, which move c by 1-3 % (synthetic, 0.2 s),
to the level fit. (The null then drew the pointer with its grid alone; since then it carries the readings' own scatter too,
which a pointer read with noise and no grid needs -- the test suite's steady pan read a false -38-frame lag without it -- and
which can only widen the null.)

**On the clips** (job 21206). PR051's upload, the three windows of session 6 with the hold given: **refused by name**, the
pointer +118, +100 and +120 frames (1.67-2.00 s) behind the picture (r 0.61 against 0.33 at zero lag over 7-14 s), Dimson's
slope over 2-s blocks 2010 px/deg (95 % 1580-2860) beside the level fit's 2843 and the truth's 2230; the stall said beside it
(still 1.53 s, 1.6 steps). PR27's three claims and PR057a's three that passed before pass, their lead-lags -7 to +7 frames;
PR057a's 24.4-32.4 s (c 303) is **refused**: +21 frames (0.70 s) behind at r 0.38 against 0.27, and Dimson's slope over 21-
frame blocks has no positive value. Its state then rests on 20.4-28.4 s alone (c 256), and the zoom check across 32.8 s reads
x2.285 against the imagery's x2.001, inside the 20 % the windows' errors allow (worked by hand from the windows' own numbers). Of the other pointer clips with series: PR43
has no slew; PR48's 91-99 s is refused (-34 frames, 1.13 s); PR144's and PR148's windows were refused before by other checks
and now also say their lag (+60 frames) or stall (3.9 s). PR060, PR061 and PR149 have no pointer series.

The null drawn on the grid is clean, and real pointers beat it. PR27's and PR057a's slews, whose c's agree with their zooms
(§17), owe 1.2-2.5 steps at a fast slew where a pointer drawn on its grid owes at most 1.0-1.6 in 19 draws of 20, and their
lead-lags of -13 to +21 frames are real against it nearly every time -- a display that draws its glyph a few frames off the
picture -- but they last 0.13-0.77 s. PR051's dial owes 1.6 steps for 1.5 s and runs 118 frames (2.0 s) behind the picture.

**One k from the routes that agree (E17).** Bates & Granger (1969) combined forecasts with weights inverse to their error
variances; the forecast combination puzzle (Smith & Wallis 2009) is that weights estimated from the data often do worse than
equal ones. Here the weights are each route's stated error, and nothing is combined before a test that the routes agree,
since combining two that disagree hides a mistake in one (`scale.route`, `scale.combine`, `combined_said`). In log k: the
measurements with a stated error, one of each group that shares an input (the most precise), are set against their weighted
mean, chi^2 on n - 1 degrees of freedom; they agree where its chance is AGREE_ALPHA (0.05) or more, and the combined k is the
mean with error 1 / sqrt(sum w). The stated rate holds only where the errors are what they say: on 600 synthetic slew windows
with one c, each window's 16-84 % half-width covered the truth 76 % of the time, but ln(c / c_true) over it had sd 1.36 (MAD
0.72) -- right in the middle, light in the tails -- and at a stated 5 % pairs, threes and fours of windows were called in
disagreement 7, 13 and 16 % of the time. With each window's half-width times 1.5 (`slew.SLEW_ERR_SCALE`) the rates are 4.3, 6.5
and 5.3 % (x1.3: 5.3, 9.5, 8.0 %), and `slew` tests its windows so; the state's c and its error are as before. The price is power: two
windows 10 % apart are told apart 43 % of the time at x1.5 (67 % unscaled), 25 % apart 84 % (93 %). Where they disagree nothing is combined and every pair further apart than the two-sided 0.05
allows is named. A measurement whose error is not stated (a graticule as given today) is tested against each that states one
with its own error taken as none -- the strictest the test can be -- and never weighed in. A floor (a slew's c = k cos e with
the depression unknown, or a floor where the pointer did not register the turn) must be cleared: a measured k below it by more
than the one-sided 0.05 allows is a disagreement. A prior (a field of view assumed, or given stretch by stretch) is set against
the result and below a floor is said to be contradicted; it never enters the combination.

Where it is used. (1) In `slew`, each zoom state's windows: each claim's c with its bootstrap's 16-84 % half-width, windows
that overlap in time sharing their frames (only the more precise of two enters); a state whose windows disagree has no c and
says so by name (before, their inverse-variance mean was taken whatever their spread, and `c_spread` reported it). (2) In the
report's table of the four unknowns, k's row: where a case has two routes or more (`Case.k_routes`: the scale stage's
graticule or field of view, the slew recorded with `--case`, a reference of known length at a range given), the row adds what
the test says. The row's value stays the route the speeds were worked out from: the test says whether the others bear it out.
Across zoom states the slew's c's are compared through the imagery's zoom as before (§17), not combined: `zoom`'s ratio states
no error yet (E15 would give it one).

**The zoom as a regression discontinuity (E15; `zoom --rd [H]`).** `forensics.zoom_fit` measures a zoom from one frame either
side of the burst; `zoom.confirm` already refits a marginal one from pairs further out. A regression discontinuity estimates
a jump at a known cutoff by local polynomials either side (Imbens & Kalyanaraman 2012; Calonico, Cattaneo & Titiunik 2014),
and here the cutoff is the burst and the outcome the scale between a frame before it and a frame after it. The pairs (before
- i, after + j), i and j from 0 to H (3 by default: 16 pairs), are each fitted as the burst's own pair is, with the same fixed
patterns taken out; ln s_ij = ln S + b i + c j by least squares, the slopes the scene's own drift of scale (a camera closing on
the ground), and the jump S at i = j = 0 (`rd_fit`). Beside it the same with i^2 and j^2: the interval is that fit's, bias-
corrected by the higher order as Calonico, Cattaneo & Titiunik's robust interval is, its error from a jackknife that leaves out
each frame in turn (the pairs share their frames, so they are not independent), at 95 % on t. It calls a step where the
interval clears x1 and the no-step band (x1.08) too (`rd_step`). **Placebo cutoffs** (`placebo_items`): the same estimator at
10 cutoffs inside the states, at least 12 + H frames from any burst, each with its own state's fixed pattern either side; the
share of them that call a step is how often the fit finds a step where there is none, on this clip, and the stage says it.
Only when asked; a run without `--rd` is as before. H = 3 is a judgement call: within three frames a turret's scale drifts a
few parts in a thousand, so the local line is nearly flat and the quadratic is the check on it (the quadratic is used where
each side has four frames or more, so its jackknife can leave one out; with fewer the line alone). Rendered (`tests/
test_zoom.py`): x2 with the scale drifting 0.1 % a frame, H 2, read as x2.0045 (95 % 1.990-2.019) against 2.0056; two placebo
cutoffs x0.9987 and x1.0014, no step. **On real clips** (2026-11-13; `mcdonald zoom --rd` on PR057a, PR144, PR27, PR105 and AARO's Puerto Rico clip, each
1920 x 1080, H 3, ten placebos; 40 to 68 minutes a clip on two CPUs, 1.9 GB; the runs of 2026-11-07 had not finished in
their hour, each pair then rebuilding both stretches' fixed patterns, which `zoom.fit_all` now builds once a stretch).

| clip | the step | the burst's own pair | the jump, 95 % | the known ratio |
|---|---|---|---|---|
| PR057a, 32.8 s | x2 (the ladder's rung x1.9998) | x2.000 | x2.0004, 1.9924-2.0085 | held |
| PR27, 82 s | x2 | x2.003 | x2.0025, 1.9954-2.0092 | held |
| PR105, 94.6 s | x2 | x2.002 | x2.0008, 1.9933-2.0091 | held |
| PR105, 125.7 s | x0.5 | x0.500 | x0.5005, 0.4924-0.5071 | held |
| PR144, 2.5 s | x5.884 by hand (the rung x5.916 +- 0.5 %) | x5.810 | x5.8608, 5.7738-5.8969 | holds the hand's; the rung's centre is 0.3 % over its top |
| PR057a, 53.8 s | the x5.9 rung | x5.855 | x4.92 (the quadratic's x5.80), 3.55-9.46 | held, by an interval a factor of 2.7 wide: its pairs disagree |
| Puerto Rico, 20.5 s | the display's 135 to 675: x5.000 | x4.966 | x4.9149, 4.8932-4.9694 | not held: 0.6 % over its top |
| Puerto Rico, 118.1 s | 675 to 2024: x2.9985 | x3.096 | x3.1270, 2.7795-3.4387 | held |
| Puerto Rico, 142.6 s | x0.3335 | x0.327 | x0.3260, 0.3200-0.3300 | not held: 1.1 % over its top |

The four steps of the x2 rung (PR105's x0.5 its return) are each read to about 0.4 %, and every interval holds the ratio. The Puerto Rico display
prints its focal lengths as whole numbers, and the imagery's own scale differs from their ratios by 1 to 3 % by three
routes (a hand fit, the burst's pair, this); the interval is the imagery's, and is narrower than that difference.

*Placebos.* Of 50 cutoffs inside the states 48 gave an estimate, and **none called a step** (0 of 9, 10, 10, 9 and 10):
the rate a step is found where there is none is under 6.1 % (exact, one-sided 95 %). **The interval alone is not a test
of "nothing happened"**: 7 of the 48 did not hold x1 (15 %, where 5 % is its level), six of them on PR105 (x1.003 to
x1.006, each to a part in a thousand). A placebo's jump is the scale between two frames next to each other, and where
the scene's own scale drifts, a camera closing or a slow zoom, that is one frame's drift and not nothing. The estimate
is right about the picture. What keeps it from being called a step is the no-step band (x1.08), not the interval, so
"no step" from this reading means "under 8 %", not "none".

*A defect found there, and fixed* (`zoom.rd_trusts`). On nine bursts the stage itself calls unknown the regression
said "a step": it took a pair's scale wherever the fit gave a number off the grid's edge with a ZNCC of 0.15, and never
asked the pair's own verdict (its peak's prominence, its lead over the rival scale). PR27's burst at 89 s, featureless
haze, the trap section 17 names, read "x3.1271, 95 % x3.1271-x3.1271" from 15 pairs all stuck on one value of the grid.
Now a pair's scale is taken only where its own fit is a step or no step, and pairs that all give one value are no
estimate.

*The five clips again, with the fix* (2026-11-14; 43-82 minutes a clip). The pairs of the nine bursts the stage
calls unknown are now too few to trust, but for one: Puerto Rico at 185.6 s, where 12 of the 16 pairs are trusted on
their own and agree, x2.9551 (2.9430-2.9672), though the burst's own pair is not (a step `zoom.confirm` would accept
by its own rule, two pairs further out passing). The known steps:

| clip | the step | before the fix | with it |
|---|---|---|---|
| PR057a, 32.8 s | x2 | x2.0004, 1.9924-2.0085 | the same |
| PR057a, 53.8 s | the x5.9 rung | x4.92, 3.55-9.46, "a step" | x5.61 from 11 pairs, 0.97-32.4: **not a step at that level** |
| PR27, 74.3 s (a picture step) | its pair's x1.205 | x0.859, 0.134-7.73 | x1.2039, 1.1552-1.2546, a step |
| PR27, 82 s | x2 | x2.0025, 1.9954-2.0092 | the same |
| PR27, 127.7 s (a picture step) | its pair's x0.852 | x0.8583, 0.7499-0.9926 | x0.8534, 0.8250-0.8828, a step |
| PR105, 94.6 s | x2 | x2.0008, 1.9933-2.0091 | the same |
| PR105, 125.7 s | x0.5 | x0.5005, 0.4924-0.5071 | x0.4996, 0.4984-0.5009 |
| PR144, 2.5 s | x5.884 by hand | x5.8608, 5.7738-5.8969 | the same |
| Puerto Rico, 20.5 s | x5.000 (the display) | x4.9149, 4.8932-4.9694 | the same: not held |
| Puerto Rico, 118.1 s | x2.9985 | x3.1270, 2.7795-3.4387 | **too few pairs trusted** |
| Puerto Rico, 142.6 s | x0.3335 | x0.3260, 0.3200-0.3300 | x0.3308, 0.2999-0.3648: held |

Taking only the pairs whose own fit is trusted narrows the intervals where the pairs agree (PR27's two picture steps,
PR105's x0.5) and widens or removes them where few do (PR057a's x5.9 rung, Puerto Rico's x3). Two known steps are lost
to the reading that way, and none is read wrong. The placebos: 46 judged of 50, **none a step** (under 6.3 %, exact,
one-sided 95 %); the same 7 intervals exclude x1, six of them PR105's drift, so the finding above stands unchanged.
What `--rd` adds, then: an interval on a step that the pairs agree on, and a way to see that they do not. The
single burst's pair (`zoom.fit_all`, `zoom.confirm`) stays the reading the states are built from.

**The zoom ladder pooled (E16; `scale.ladder`, `credible`, `carry`).** International price comparison fits log price = country
effect + product effect over rarely observed pairs (Summers 1973), and finance shrinks a stock's noisy beta towards the cross
section (Vasicek 1973; Blume 1975), as insurers' credibility does (Buhlmann 1967). A sensor's zoom changes its field by a few
fixed ratios, so every step measured in any clip is a reading of its rung. `ladder` groups steps by |ln s| (a new rung past a
gap of 3 %) and pools each rung, its error the standard error of its steps and, where the steps state their own errors
(`zoom --rd`'s), tau, the spread beyond them; `credible` shrinks one clip's step towards its rung by Z = tau^2 / (tau^2 +
err^2); `carry` takes a k through pooled rungs, the error each rung's pooled one, not a single step's. Read off the pointer
sweep's 95 measured steps (pass 5; 42 of the 127 clips, every PURSUE sensor together): **x1.9998 (+-0.28 % in ln; one step's
spread 1.9 %; 45 steps in 26 clips) and x5.916 (+-0.51 %; spread 2.2 %; 18 in 10)**, then x2.303 (9 in 6), x3.141 (3) and x1.089
(3). A single measured step is good to about 2 %, the x2 rung pooled to 0.3 %. What it does not give is a k on a clip that
measured none: `carry` makes a prior, and k carried between clips also carries their depressions (c = k cos e) and their
videos' scalings, which need not be the same, so the ladder is not a report's row.

## 50. The picture's levels: clipped as a flat top, and the headroom the extraction cuts (V1; added 2026-11-07)

**What it answers.** Video stores brightness (Y, luma) in studio range: black at 16, white at 235 (BT.601, BT.709), the
codes past them headroom ("superblacks", "superwhites"). Every frame here is extracted by ffmpeg as RGB, and its
conversion stretches 16-235 to 0-255 unless the stream says it is full range: every Y above 235 becomes 255, every Y
below 16 becomes 0. A core that is not clipped in the file is clipped in the frames the package measures. Until 0.4.4,
`forensics.spot_fwhm` called a core clipped where it reached grey 250 (`CLIP`), which after the stretch is Y 231, and
`integrity.t_halo` called one saturated past grey 245. This section reads the levels as a fact of the clip, calls a core
clipped where it has a flat top, and reads that top on the file's own luma.

**The survey's check, rebuilt** (the visual-arts survey, section 3.1, 2026-10-15/16; rebuilt 2026-11-07 with a script
of its own). On PR135 (1280x720 yuv420p, tagged `tv`): on neutral pixels the extracted grey is 1.1618 Y - 18.83 (the
stretch's 255/219 = 1.1644 and -18.63), and Y 235, 236, 240 and 250 all become 255. The six birds' cores (within 4 px of
`tests/golden/pr135_tracks.csv`) pass 235 on 121-139 of their 153-162 frames, peak at a median Y of 239 and at most
248-254, and are never flat at 255; in the extracted frames the core is at 255 on 129-145 frames. Clipping Y at 235
costs flicker's aperture a median 0.14-0.17 % of a bird's flux (at most 0.9 % on a frame) and its relative modulation
under 0.3 %: the photometry and the beats stand. What the cut changes is the clipped call.

**The levels as a fact of the clip** (`clip.declared_levels`, `forensics.clip_levels`). What the stream declares
(ffprobe's `color_range`, the matrix, the transfer, the pixel format): studio where it says `tv`, "unsaid" where a YUV
stream says nothing (ffmpeg then takes it as studio, as on 101 of the 149 PURSUE videos), full where it says `pc` or is
`yuvj` or `gray` (checked on ffmpeg 8.1: a gray stream's 236 is extracted as 236, a tagged-tv yuv420p stream's as 255).
What its pixels use, read on the luma plane as the file has it (`extractplanes=y`, nothing converted) on 60 frames over
the window: the lowest and highest code, the share below 16 and above 235 and at 0 and 255, in the whole frame and in
the scene with the symbology and blocks left out. And with a track, the object's core (within 4 px): on how many frames
it is past the nominal range on its own side, its median and its extreme code, and on how many the extraction cuts it.
Every command's envelope carries the declared part (`clip.encoding.levels`); `integrity`'s record carries the whole, and
its report says it in a line under the record.

**The picture with its headroom** (`Clip.luma`, `Clip.headroom`, `forensics.picture`). The luma planes are extracted
beside the frames (`<frames>/luma/`, 8-bit grey PNG) the first time a test of levels asks for one, a second decode of
the window. `headroom(n)` is the luma in the extracted frames' scale -- Y 16 at 0, 235 at 255, a code 255/219 wide -- so
that every fixed level in the package means the same on it while what the stretch cut survives, from -18.6 (Y 0) to 278.3
(Y 255). Where the extraction stretches nothing (a full-range, grey or RGB stream) it is the extracted grey. For a grey
picture, most sensor video, it equals the extracted grey wherever that is not cut (to the stretch's rounding); for a
coloured one it weighs the channels as luma does, not equally. Only 8-bit luma is read; a 10-bit stream's headroom is not,
and the record says so.

**Clipped as a flat top** (`forensics.flat_top`). A core (a spot's 3 x 3, the halo's r <= 0.28 of the object's size) is
clipped where its top is at the picture's own ceiling -- a code there means "this or more" -- or where it is flat:
FLAT_K = 5 of its pixels within FLAT_TOL = 1 code of its top, the top FLAT_AMP = 50 codes over the spot's level, at
whatever level the chain cut it (235 where a camera cut its studio range, a sensor's own ceiling). A dark core, the same
at the floor. A top of one or two pixels below the ceiling is a peak: a clip that leaves so few at its level has cost the
width little.

The three numbers are set on a null (`tools/flat_top_null.py`, two seeds): 207,360 Gaussian points (sigma 0.7-3 px, a
random sub-pixel centre every frame, a level of 30-140 codes with noise of 1, 2 or 4) drawn as 8-bit luma, through
libx264 at CRF 14, 20, 26 and 32, decoded and read as raw Y. Half are unclipped (peaks under 250); half are cut before
the encoder at 180, 235 or 255, their peaks 1.05-3 times the ceiling.

| rule (3 x 3 core) | unclipped called clipped | worst cell (width x CRF) | cut at 255 called | cut at 180 or 235 called |
|---|---|---|---|---|
| tol 1, k 3, no amplitude | 12 % | 37 % | 91 % | 28-33 % |
| tol 0, k 4, amplitude 50 | 0.10 % | 0.5 % | 88 % | 2-10 % |
| tol 1, k 4, amplitude 50 | 0.55 % | 4.7 % | 90 % | 8-31 % |
| **tol 1, k 5, amplitude 50** | **0.03 % (30 of 103,680)** | **0.3 %** | **89 % (73 % at CRF 32, 98 % at CRF 14)** | **5-21 %** |
| tol 2, k 5, amplitude 50 | 0.16 % | 1.4 % | 90 % | 9-41 % |

Without the amplitude no rule is clean: a faint wide peak is flat at the pixel scale by itself (of the peaks 8-20 codes
over their level, 47 % have three of their 3 x 3 pixels within a code of the top; of those 3 px wide, 24-37 %). The rule
chosen is the one with under 0.1 % false over all and under 0.5 % in every cell that keeps the most power below the top;
the two limits are a judgement, stated as one. Its weakness is stated with it: a codec ripples a plateau it is given,
and a core cut below 255 before the encoder is seen flat 5-21 % of the time. A width measured on such a core cannot be
known to be cut.

**Where it reaches a verdict.** `point_blur` (the blur of a point and whether the object is wider: the speed in body
lengths, `focus`, `streak`'s blur) calls its spots clipped by the flat top, for the scene's spots and the object alike,
on the extracted frames by default (`BLUR_HEADROOM`), on the picture with its headroom when asked (`headroom=True`). Its
result says which (`picture`) and the object's median top in it (`object_top`). `integrity.t_halo` reads its cores on the
picture with its headroom and calls them saturated by the flat top; its synthetic insert is drawn on the same picture.
`focus` still leaves pixels past `CLIP` out of an edge's profile, per pixel. Nothing else changes: flicker's photometry,
the detector, the links and the layers read the extracted frames as before.

**What moves, and why `point_blur` does not read the headroom by default** (2026-11-07). On PR135's six birds
(`tests/golden/pr135_tracks.csv`, 12 frames each):

| bird | grey 250, extracted (before): blur (spots) / clipped / resolved | flat top, extracted (default): blur / clipped / resolved | flat top, headroom: blur / clipped / resolved |
|---|---|---|---|
| A | -- (7) / 11 of 11 / None | 2.40 (12) / 8 of 11 / None | 4.31 (33) / 0 of 11 / False |
| B | -- (2) / 3 of 6 / None | -- (3) / 3 of 6 / None | 4.49 (38) / 0 of 6 / False |
| C | -- (5) / 5 of 5 / None | -- (7) / 5 of 5 / None | 4.54 (35) / 0 of 5 / False |
| D | 2.43 (9) / 9 of 9 / None | 2.52 (13) / 8 of 9 / None | 4.28 (37) / 1 of 9 / False |
| E | -- (7) / 8 of 8 / None | 2.54 (17) / 8 of 8 / None | 4.18 (37) / 0 of 8 / False |
| F | -- (7) / 9 of 9 / None | 2.52 (13) / 8 of 9 / None | 4.04 (41) / 0 of 9 / False |

The birds' own widths (4.4-5.6 px) are the same to 0.01 px on both pictures: the cut leaves one or two pixels at the top
and costs the fit nothing. With the headroom they are not clipped, as the file says -- but nor are the flock's other
birds, which the blur takes as the scene's points. On frame 1330 (bird A's twelve frames, every spot listed both ways)
the headroom picture takes 8 spots, 5 of them on the other birds' tracks (within 4 px), 4.1-4.9 px wide, against 1.8-2.7
px for the rest; the extracted frames take 4, 2 of them birds not cut at 255 on that frame. On frame 1260 neither takes
a bird. So the headroom turns "not measured" into "not resolved" against a blur that is the flock's own width. On the
extracted frames the cut kept the other birds out, as clipped, and left the blur to the scene's few true spots. Which of
a scene's spots are points is the open question here, not the levels, and a verdict should not move on it: `point_blur`
reads the extracted frames unless asked, and its six calls on PR135 are what they were (None). With the default the flat
top changes them only in which spots count: the blur is now measured on four of the six (12-17 spots), and the birds
stay clipped at the extraction's 255.

The halo, on every reference object with an integrity stage: PR135's six read on 148-150 frames (were 0-7) and stay NO
POWER, "no sharpening ring to speak of" (the ring is not darker than the sky); PR149 39 frames (4 before; 40 needed) and
PR43 16 (6) stay NO POWER; PR113 (dark) is unchanged; **PR144 goes from NO POWER to INCONCLUSIVE**: its core is past 235 on
55 of 60 frames in the file but never at the top (median Y 240, at most 252), and on 93 frames it shows a real ring (0.145 of
the amplitude) that does not deepen with it (r = -0.34). INCONCLUSIVE is not a PASS: no checklist row and no conclusion
moves. `streak`'s blur on PR43 (method section 30) reads 3.63 px from 40 spots on either picture.

Flicker on the picture with its headroom (a measurement only): every bird of PR135 beats on both, five of the six within
2 % of their amplitude and 0.03 Hz; D's reported beat moves from its clearest window (7.09 Hz) to the whole track (7.12 Hz,
which is its whole-track curve on the extracted frames too). The cut is 0.15 % of their light, as the survey said.

## 51. Non-uniform motion dated, and set against the scene (E2, E3, B16; added 2026-11-07)

**What it answers.** The speed band (§32) says whether a track's velocity changes and by how much over the stretch; it does
not say *when*, nor whether a change is more than the wander every recorded track has. `camera.rate_steps` (§20) cuts a track
into straight lines with a penalty computed from white jitter, so on a wandering track it finds a step wherever the wander
bends: 1,267 stretches on the 44 recorded tracks, 12-16 on each of PR135's 150-frame members, about one a wingbeat wiggle (the
economics survey, uap `analysis/methods/economics_finance_methods_survey.md`, 2026-10-28, §1.3, §2.1, §2.4, §6.3, §6.5). This
section dates a change the wander cannot explain, with an interval on its date, and asks whether the scene changed with it --
the camera's, or not -- as an event study sets a stock against its market.

**The scan** (`breaks.scan`, `breaks.of_track`). Each coordinate is the band's own model -- a line, the fitted Matérn wander
(and the beat beside it, M8, where the band keeps one), the nugget -- with a hinge (t - τ)+ added to the mean: a change of
velocity at τ. Its GLS Wald statistic under the fitted covariance, x and y summed, is maximised over τ inside the stretch with
15 % trimmed from each end (Andrews 1993: nothing can be said there, and the ends are said to be NO POWER). The null is drawn,
not read from a table (Andrews' critical values assume white errors): 400 tracks with the band's covariance and no break,
whitened (each draw is then standard normal, so it costs one projection), the sup taken the same way on each; p is the share at
or above the track's own. The size and direction of the change are the hinge's two coefficients at the date. The interval on
the date is the same bootstrap with the break in: the track's own change at its own date added to every draw (by linearity,
the numerator moves by δ times the whitened hinges' Gram column), the date found again on each, the middle 95 % (Bai 1997's
interval in its simulated form). The points are the band's (repeats dropped, glitches and excursions left out); a track
longer than the band's 450-point window is scanned in the band's windows and each p multiplied by their number (Bonferroni). A
break is named at p < 0.05 (`ALPHA`; a judgement call on the level, the survey's).

**Its false-alarm rate, measured** (`calib.py` in the session's scratch, Slurm 20156). On tracks drawn with each of the 44 recorded tracks' own fitted
covariances (the band's numbers, the beat included where it is kept) on their own first 450 kept frames, with no break, each
put through the whole pipeline -- the band fitted again, then the scan: 16 of 1,100 named, **1.45 %** (95 %: 0.8-2.4 %) at the
stated 5 % (0.36 % under p 0.01, 4.0 % under 0.10). With a change of four prior velocity sds
planted at a random date in the middle 60 %: 650 of 660 found, the date inside the interval on 647 of them -- at that size the
date is found to the frame. On the survey's drawn rows (300 frames, a 5-px Matérn wander of 1 s and a 0.4-px nugget): clean 0 of 40 named,
30 px/s 20 of 40, 60 px/s 40 of 40 (the survey: 1, 17, 40). The fixed-covariance null is conservative where the wander has
taken in part of a break (refitting under the alternative is ~300 fits a track: not done).

**On the recorded tracks** (the survey's functions rebuilt on d46d3a8, Slurm 20111/20128): 20 of 44 have a break at p < 0.05
(the survey 22; two more at 0.052), where `rate_steps` cuts the same tracks into 1,267 stretches. PR144's object 1 at 23.27 s
(29 px/s, p 0.005), PR099 object 3 at 210.0 s, PR088 object 2 at 237.6 s, PR41 at 84.2 s, the balloon at 88.8 s.

**The scene frame by frame** (`breaks.scene_path`). `layers` writes the scene's shift over k = 5 frames at every frame. The
per-frame position S solves S[a + k] - S[a] = dx[a] by least squares with a light penalty (0.01) on S's second differences and
S at the first frame 0, banded -- Denton's (1971) benchmarking turned round, the per-frame series from overlapping sums. A held
picture comes out as a frame that did not move and the catch-up after it, on the video's clock, where a five-frame average
never shows it: the hold and its catch-up cancel in every window that holds both, and the two windows that hold one read a few
pixels off (PR144's hold at frame 732: 0.1 px, then -42 px, against -21 a frame around it, the survey's reading; the average
had made it a 3-px excursion that the step scan called a break at 24.3 s). The frame-to-frame steps are not exact: a pattern
of period k, which no k-frame shift can see, is set by the penalty alone, and beside a hold it rings by about 0.9 px a frame
(a drawn scene at -21 px a frame held once: -21.9, -20.2, -21.0, -21.0, -21.0 repeating). A second's mean rate holds it out
exactly (-21.000), and that is all the event study reads.

**Against the scene** (`breaks.against_scene`). For a turning camera the market model is exact: a rotation moves every point
of the picture by the same pixels, so β = 1 and the object's abnormal change is its own less the scene's. The object's change
is the difference of two straight lines a second long either side of the date, two frames left out; its error is from the
track's own fitted covariance over both windows (the two lines' weights through it: their errors are not independent where
the wander is longer than a second). The scene's change is the difference of its mean per-frame rates over the same frames,
each with a Newey-West error. Two tests at 5 %: is the abnormal change there (both coordinates, χ² on 2), and did the scene
change the way the object did (its change along the object's, one-sided past 1.96 σ)? The scene changed that way and nothing
is left over: **the camera's**; something is left over and the scene did not change that way: **not the camera's**; both:
**partly the camera's**; neither: **undecidable** (a second either side does not hold enough to say). Where `layers` holds
the scene still on screen even over a second in more than half of its pairs (its own NO POWER, `layers.SCENE_SHARE`), there is
no market: NO POWER, never a zero. The event date is chosen where the object's break is largest, so the abnormal change's
test measures attribution given a break, not whether there is one; the scan does that.

On the reference case files (0.4.3's): PR144's break at 23.27 s (95 %: 23.23-23.94 s) -- the object -41.2 ± 17.5 px/s in x,
the scene -53.9 ± 22.7, the abnormal +12.6 ± 28.7: the scene's change along the object's is 1.3 ± 0.5 of it, so **the
camera's** (the survey: +12.5 ± 20.4, the camera's slew). Twelve more objects of the case files have a break -- PR135's
objects 1-4 at 44.51-44.58 s, PR097's 4 and 8, PR077's 1, PR088's 1 and 2, PR099's 3, PR41 and PR44 -- and on every one the
scene is NO POWER. The scene is NO POWER on every other case file's
objects except PR149's and PR097's objects 6 and 7 (held still in 0-38 % of pairs), none of which has a break.

**The match rule.** A camera event inside the break's date interval, or within the camera stage's own 3 frames of it (`EVENT_NEAR`:
a date found to the frame is matched as a rate step is) -- a zoom, a change of field, an event given (`camera`, §20) -- makes the
break the camera's until shown otherwise; the report names it (`breaks.matched`). Where the interval is two frames or fewer the
report says the date "to within a frame or two".

**A group** (`breaks.common`, `breaks.dispersion`, `breaks.together`). A break common to several objects of one video (Bai,
Lumsdaine & Stock 1998): their Wald statistics summed at a shared date on the frame grid they all cover (15 % trimmed), the
null drawn for each from its own covariance independently (2,000 draws). The objects' page (`several.index`, "Together") tests
each set of objects followed over the same frames. With the survey's functions (the Matérn alone): PR135's six share one at
44.556 s (97.3 against a null 95th centile of 34.0, p 0.0005), PR097's objects 1-4 one at 126.19 s (42.9 against 26.4, p 0.0005)
though none of them was significant alone. With the bands' own covariances (the beat held where the band keeps it), as the
objects' page reads them: PR135's six at 44.55 s, to the frame (95.5 against 34.7, none of 2,000 draws), PR097's 1-4 at 126.16 s
(126.12-126.19), its object 4 now significant alone (p 0.022); PR097's 6-7, PR099's 1-2 and PR141's 1-2 share none. Then
event-induced dispersion (Boehmer, Musumeci & Poulsen 1991), read across members: a camera's slew adds one velocity to every
member, so their changes at the event are no more spread than on placebo dates (every 0.1 s, at least 1 s away); spread past
the placebo dates' 95th centile is extra. PR135: a common change of 193.5 px/s, twice the placebo dates' largest (95th centile
96), its spread at their 17th centile -- what a gimbal slew adds to everything in the picture, or a turn the six made together,
which the pixels cannot tell apart (the pointer's turn, uap `cases/pr135/pr135_pointer_slew.md`, agrees in sign and date).
PR097's four: 50.2 px/s, ordinary for them (placebo median 48), spread at the 70th centile (at 126.16 s: 50.9, the 64th). The common test assumes the members'
noise independent; a shared camera jitter correlates it and makes the joint test too liberal -- plausible on a still-scene
clip, not on a moving one.

**B16, the released-track null's error** (`camera.wander_errors`). `camera.released` (§20) takes a stretch's rate error from
its residuals as if white. On tracks drawn with a recorded track's own wander at exactly the camera's rate (the biology survey,
Part 5 §4, 2026-11-01), the fastest stretch beat the camera's rate 97 % of the time and the whole departure 74 % (29 tracks; rebuilt on 38: 96.8 %
and 69.1 %), on white jitter 2 % (2.6 %). The departure's own covariance is now fitted as
the band fits a track's, and every line's slope gets its error under it (c'Kc), the larger of that and the white one kept as
`err_wander_px_per_s`; `released` reports `z_wander` and `within_wander` beside its verdict, which stays the white one's (the
choice of verdict is the maintainer's). Measured again with it: (being measured; the session's notes).
PR051's departure, 157.5 ± 3.7 px/s by `departure` and 153.9 ± 1.0 by the speed band, keeps its error, the white one being the
larger: its wander's range, 0.10-0.18 s, is far shorter than the 1.8-s departure, so its 43 sigma stands.

**What it is not.** One break per window: a track that changes twice is dated at its larger change (Bai & Perron's several
breaks are not ported). A velocity change only; a step in position is §32's jumps. The event study's windows are a second;
a break within a second of the track's end has under 8 points on one side: no power. The scene is `layers`' largest motion group
(else the streaked or the evenly textured layer): on a clip with two layers the abnormal change is against that one.

## 52. Computing on a graphics card: the same measurement, and how it is held (ROADMAP 0.6, objective 3; added 2026-11-12)

**What it answers.** Whether a number depends on what computed it. Since 2026-11-12 the steps that match one frame
against another can run on a graphics card (`mcdonald.gpu`): `layers`' two rounds and `integrity`'s background passes.
A card is never required. The CPU's arithmetic is the reference, its code was not touched, and the card's version of a
routine stands beside it and is held to it. This section says what "held" means, to what tolerance, and why it is not
"to the last bit".

**The rules** (`gpu.py`'s docstring has each with its reason).

- *Which cards.* The card's arithmetic is CuPy's, which answers to NumPy's and SciPy's names and runs on NVIDIA cards
  through CUDA, on Linux and Windows (`pip install "mcdonald[gpu]"`). A Mac's card, an AMD or an Intel one is found,
  named, and said not to be used yet.
- *The choice.* `MCDONALD_GPU`, which `mcdonald --gpu X` and Preferences set: unset is the first card, `none` the CPU
  only, otherwise a card's name or number.
- *A batch job's allocation, not the machine*, as `progress.cpus` has it for CPUs. Inside a Slurm job a card is used
  only where the job was given one (`--gres=gpu:1`).
- *One process computes on it.* A pool's workers never do: each would hold its own state on the card, a few hundred MB,
  and they would take turns. A stage with a card version runs its pass in one process, with the frames read ahead by
  threads (`progress.Ahead`).
- *A stage says so.* A routine with a card version runs on the card only inside `with gpu.on(card):`, which a stage
  enters for the whole of a pass. Anywhere else it is the CPU's arithmetic, card or no card. On the first run on a card
  the routines used it wherever one was to hand, and `groups` took its spots from the card in one process and from
  the CPU on its pool: the suite that holds stages to "the same on a pool as in one process, to the bit" failed, and
  the rule was made.
- *A failure is not a crash.* A card out of memory is sent half as much at once. A card that refuses anything else is
  said once on stderr and given up; the pairs not yet done go to a pool of CPUs.
- *One thread talks to the card, and it never ends.* CuPy keeps its FFT plans in a cache of each thread's own, and
  that cache runs Python's cycle collector when it is cleared and when its thread ends. The window runs the collector
  in its own thread and nowhere else, because a widget freed in Measure's thread is a crash, and the window's suite
  caught the card's first version collecting in Measure's thread 19 times. Every routine on a card is now handed to
  one thread that is never joined (`Card.run`), and the plans are let go one by one, which collects nothing. What is
  left: a card truly out of memory makes CuPy's allocator run the collector once in that thread before it gives up,
  and batches are planned on half the free memory so that it does not come to that.

**The band-pass is the CPU's to the last bit.** CuPy's Gaussian filter sums a single-precision frame in single
precision. Over the 97 taps of the 12-px Gaussian that is 1.4e-4 of a grey level from SciPy's (PR113's frame 380),
because SciPy sums each line in double and keeps the result in the frame's precision. `forensics._gaussian_on` does
SciPy's own arithmetic on the card: along each axis in turn, the sums in double, the result in single. On that frame 0
of 2,073,600 pixels differ. Everything read from a filtered frame therefore starts equal.

**The shift field is the same search, arranged for a card** (`forensics._shift_field_on`). The CPU takes one template at
a time: its region of the second frame, cut where the frame ends, a correlation by FFT, then the peak. The card takes
a pair's templates in one batch:

- every template's region is the same size, min(template + 2 x reach, the frame), slid to stay inside the frame where
  the template is near an edge. It holds every placement the CPU tries. The placements farther than `reach` from the
  template's own place, which the CPU's region does not have, are set to -1 as masked ones are, so a peak on the rim of
  what the CPU searched has a -1 beside it and is dropped, as a peak on the border of the CPU's map is;
- regions that coincide are transformed once: two templates near the same edge, or every template where the reach is
  larger than the frame (`integrity`'s whole-frame search);
- the correlation is circular over the region's own size (625 x 625 for the usual 618-px region, against the CPU's
  750 x 750 padded by the template): the placements wanted are the ones that do not wrap;
- each placement's normalisation and mask count come from the whole frame's summed-area tables in double, as on the
  CPU, made once a frame;
- the card finds each map's peak, its 3 x 3 neighbourhood and its runner-up; the rest of the peak's reading (the
  parabola, the curvatures, each template's own error and ridge, section 31) is `forensics._peak_read`, one function
  that both ways call. Which templates are clear of the masks, and each one's mean level, are worked out on the CPU
  from the same arrays, so they are the same to the bit.

The correlations are single precision on both, by different transforms of different sizes in a different order, so the
maps differ by a few 1e-7. A sharp peak turns that into a few 1e-6 px. A peak nearly flat along a streak (open sea)
turns it into as much as 2e-3 px along the streak, where the template's own error is a thousand times larger and its
information next to nothing. Measured on PR113 (1920 x 1080; pairs from 380, 395, 410 and 425; both zones):

| search | templates a pair | rows kept | a template's shift, worst | in its own error | a pair's agreed shift, worst | one CPU thread | the card |
|---|---|---|---|---|---|---|---|
| the usual (128 px, stride 96, reach 245) | 59-76 | the same | 2.0e-3 px | 3.7e-4 | 9.8e-6 px | 0.77 s | 0.027 s |
| the second pass's (stride 48) | 243-313 | the same | 2.0e-3 px | 5.6e-4 | 2.6e-5 px | 2.4 s | 0.078 s |
| the whole frame (stride 144, reach 1225) | 26-36 | the same | 4.6e-4 px | 2.3e-4 | 9.0e-6 px | 1.8 s | 0.055 s |
| 64-px templates (stride 48) | 344-422 | the same | 1.6e-3 px | 5.1e-4 | 6.4e-5 px | 2.8 s | 0.096 s |

The card's code run by NumPy and SciPy on the CPU (`gpu.stand_in`) differs from the CPU's own by as much: 2.7e-3 px on
a template, 1.2e-4 px on an agreed shift. So the difference is the arrangement's rounding, not the card's.

**The spot detector** (`forensics._spot_response_on`) is by FFT at every size on the card, in double throughout, which
is what the direct sum is: on PR113's frame 380 it is the direct sum to 2e-13 of a grey level before it is kept in the
frame's precision, at 5, 9 and 21 px. The CPU makes the direct sum under 9 px and a single-precision FFT from there,
which is 2e-5 from it. No stage enters a card's pass for the spot detector yet (Find and Follow run on pools); the
routine is there and held.

**The stages, measured both ways** (the development workstation, 2026-11-12: a 48-core Xeon 678X, 88 threads for
jobs, and an RTX 5070 Ti; CuPy 14.2.0 on CUDA 13).

| what | on CPUs | on the card | what differs |
|---|---|---|---|
| `layers`, PR113 frames 380-440 (56 pairs) | 26.6 s on 4, 10.0 s on 88 | 2.8 s | none of the table's 519 cells |
| `layers`, PR113 frames 1-900 (895 pairs) | 60.4 s on 88 | 34.7 s (8 CPUs reading) | 11 of 11,400 cells, each by 0.01 px, its last digit; the three median rates the same to 0.001 px/s |
| `integrity`'s three frame-pair passes, PR113 380-440 | 11.5 s on 8 | 3.0 s | none of the report's 137 values |
| a whole `mcdonald run`, PR135 object 2 (270 frames, 1280 x 720) | 106.5 s on 8 | 70.5 s (`layers` 36 s to 8 s, `integrity`'s passes 14 s to 6 s) | 26 of the case's 4,040 values; no sentence, count or verdict; the seven tables byte for byte the same |

On PR135 the rates agree to nine digits (107.81341642 against 107.81341640 px/s). The farthest apart is the median of
the pairs' own shift errors, 0.00216469 against 0.00216467 px: 1.3 parts in 100,000.

**What that agreement means for a report, measured again on 2026-11-14** (main c1716d3, with every pass the card has by
then: `layers`' three passes, `integrity`'s, `flicker`'s camera shake, `tether`'s stroke mask). The fourteen reference
cases, 31 objects, each measured on arthur's CPUs and on its card from the same code (`rerun_cases.py`, the card's run
with rerun's CPU-for-a-CPU-case rule lifted): 25 objects have a field more than one part in 10,000 apart, and 11 print
a different number in a sentence or a table. None differs in a word: no verdict, no checklist answer, no count of
tests. The numbers that move are those read from many pairs' decisions, each made against a threshold -- held still or
not, a template kept or dropped -- where a pair near the threshold falls one way on the card and the other on the CPU:
`layers`' shares of held-still pairs (PR41 96 % against 98 %), its speeds against a layer (PR097 object 7 14 against
13 px/s, PR41 50 against 48, PR099 object 3 41 against 43), the medians of `layer_against_layer`, `flicker`'s
position-beat fits (a wander of 153.36 against 153.42 px) and the shake test's slopes (-646.25 against -646.23). On a
nearly still scene the shift is larger: in `mcdonald batch`'s PR49 frames 2680-2930, object 1 (IDEAS.md G9), the
object against the whole scene is 22 px/s (16-84 %: 11-49) on the CPU and 15 (10-44) on the card, and the
conclusion's rate 7 against 10 px/s. Each lies inside the other's spread, and each side repeats itself to the bit (the
card alone or in a pool of eight; the CPU on 4 or 8 workers). So the card's arithmetic agrees with the CPU's to about
a part in a million; a report built on it agrees in every word and in most numbers, and in a third of the objects a
number read from threshold decisions moves by about its own last digit, once by a third of itself. Files and
comparison: `/scratch/mcdonald/s24-gpu-2026-11-14/coord/cases/` (`cardcpu.txt`).

**A case says what computed it** (`report.Case.computed_on`, `gpu.computed_on`). `mcdonald share rerun` holds a case
file to one part in a billion, which the card's agreement is not. So a case keeps the card that took part in it (None
where the CPU measured alone), and its report says so in a line under the heading. `rerun` measures a case again by
the arithmetic it was measured by: a case the CPU measured, which is every case from before this, is measured on the
CPU also on a computer with a card, and held to one in a billion as ever. A case a card took part in is held to the
card's agreement, one part in 10,000 (`rerun.CARD_REL`, eight times the farthest seen), and the comparison says so. The
reference case files are the CPU's.

**How it is held.** `tests/test_gpu.py` runs the card's code against the CPU's on drawn scenes: with NumPy standing in
for the card wherever the suite runs (GitHub's runners have no card), and on the real card where the process has one.
It holds the same templates keeping their rows, each shift within 0.01 px and a hundredth of its own error, a pair's
agreed shift within 0.001 px, the band-pass to the bit, the spot detector's response to 1e-4 of a grey level with the
same spots in the same order, and `layers` and `integrity` whole on two drawn clips. `sbatch --gres=gpu:1
tools/suites.sbatch golden` runs every suite with the card's arithmetic wherever a stage has it, which is how the
goldens are held on both.

**Two more passes, 2026-11-13.** `flicker`'s camera-shake pass (`scene_shift`: every frame registered against the
stretch's mean frame, or the frame before where the scene pans, by least squares on the gradient with three Fourier
warps) and the third pass of `layers` (a block's mean taken out, its pairs matched again). The registration is
`flicker._lk_shift_on`: the masked sums are made in double over the whole frame with the mask as a factor, where the
CPU sums the masked pixels in single precision. On PR088's frames (1280 x 720) a frame takes 2.5 ms on the card
against 69 ms on one CPU core, and the two shifts lie 6e-8 px apart; on PR149's (1920 x 1028) 5.7 against 198 ms, and
5e-7 px. The third pass sums a block's sixty frames on the card in double, in the frames' order, as the CPU does.
`tests/test_gpu.py` holds both on drawn clips: the shake at the beat within 0.0001 px and the same verdict, the scene's
velocity under the pattern within 0.01 px a frame with the same blocks and pairs read.

**The card's own code for the matches (G3, 2026-11-13).** The batch above makes each template's map of matches and
goes over the maps about a dozen times in double. On a real card the matches are now read by two small kernels of
the card's own (`forensics._peaks_fused`, `_FUSED_SOURCE`) that never make the maps: one thread a row of a map reads
the correlation, divides by the normalisation, leaves out what the masks, the reach, the zone and the peak's square
leave out, and keeps the row's best match and where it is. The arithmetic of a match is the batch's own (one
multiplication and one division in double, compiled with nothing fused), and a tie goes to the first placement, so
the six arrays that come back are the batch's to the last bit: 4,105 template rows over 60 pairs of PR088, PR149 and
PR113, and every case of the suite's drawn pairs. A pair takes about a fifth less: 11.2 ms against 14.1 on PR088
(1280 x 720), 29.0 against 35.6 on PR149, 24.4 against 29.9 on PR113 (frames in memory, `shift_field_auto`). Not the
half first estimated: of what is left of a 1080p pair about half is the card's (the transforms, the filters, the
kernels), a quarter is each peak read on the CPU in Python by the one function both ways call (`_peak_read`), and the
rest is the frames sent up and each template's mean. NumPy cannot stand in for the card's own code, so the stand-in
runs the batch as before, and so does a card that will not take the code (said once; the card stays in use).
`forensics.FUSED = False` is the way back.

**The peaks read at once (2026-11-13, the same evening).** On the card's path every peak of a pair is now read in one
piece of NumPy (`forensics._peak_read_many`) and no longer one at a time by `_peak_read`, which stays the CPU's way
and the reference. The batch does `_peak_read`'s arithmetic in its order with the same LAPACK routines a matrix at a
time, and its numbers are `_peak_read`'s to the last bit wherever it was tried: 4,000 drawn peaks of every kind
(sharp, flat along an axis, tied with a neighbour, a runner-up as high as the peak) and every row of 6,694 on real
frames of PR088, PR149 and PR113 on the card. The suite holds it to a part in a billion, so that another computer's
linear algebra library may differ in a last digit without failing. Together with the card's own code a pair takes
8.6 ms where it took 14.1 on PR088 (1280 x 720), 25.0 where 35.6 on PR149 (1920 x 1028), 19.5 where 29.9 on PR113,
and 71.7 where 125.4 with the second pass's dense templates: 30 to 43 % less. `forensics.BATCH_READ = False` is the
way back.

**What it is not.** Not every step: Find, Follow, `stabilize`, `groups` and `tether` are the CPU's, on pools or on
threads, as before. For Find and Follow the reason is measured (2026-11-13): the spot detector's response takes 3 to
4 ms a frame on the card against 35 to 85 on a CPU core, but on a busy frame two thirds of the time is the picking
of the spots and their centroids (100 to 260 ms for the 500 to 8,800 spots of a frame of sea), which one process
beside the card would do more slowly than a pool of eight does; and the card's list is not the CPU's list. Of 240
frame readings on four clips (475,530 spots) 201 gave the same spots, 41 of them in the same order, and 78 spots
were in one list only, where a response a few 1e-5 of a grey level apart ties two neighbours or parts them. For
`stabilize` too (2026-11-14, IDEAS.md G7): its second pass on the card is the CPU's to 2e-6 px at the frame's corners
and about as fast as a pool of 32 workers (22-28 ms a 1080p frame in batches of 40, against 40 ms a frame for the
pool); the passes the card would shorten (the first pass and the median template, two thirds of a run, in one
process) feed the template's draw of its points, which a millionth of a pixel redraws (section 14's last trap), so
they could be held to the CPU's only to a pixel or two. Not every card: NVIDIA's only. Not a
different measurement: nothing here adds a number a CPU does not give. And not as fast as it could be: the card's
batch is bound by the memory it moves, about ten passes over a pair's maps in double, and the peak's reading and
the frames' decoding are still the CPU's, in Python. On the workstation the card does `layers` in a little over half
the time all 88 threads do; on four cores, in a ninth.

**Several processes on one card (2026-11-14).** `mcdonald batch --pool N` in a job given the card runs N videos,
each a process that opens the card for itself (`--slurm --card N` submits such a job; an array's tasks given the one
card would hold it in turn). Measured on eight parts of 1080p PURSUE videos (106-376 frames each) whose objects were
among the catalog run's slowest in `layers`, every stage, one job of 32 CPUs on the workstation:

| the eight videos | wall | the videos' own times, summed | CPUs busy | the card busy | its memory at most |
|---|---:|---:|---:|---:|---:|
| on the card, one after another (32 CPUs each) | 1,297 s | 1,296 s | 6 of 32 | 25 % of the time | 9.6 GB |
| on the card, 4 at a time (8 CPUs each) | 476 s | 1,470 s | 12 of 32 | 53 % | 10.9 GB |
| on the card, 8 at a time (4 CPUs each) | 447 s | 1,933 s | (not read) | 48 % | 15.5 GB |
| CPUs alone, 8 at a time (4 CPUs each) | 961 s | 4,535 s | 16 of 32 | | |

Every case of the pools is the same to the bit as the same video measured alone on the card: 10 cases, every field and
every table beside them. A process's arithmetic does not depend on what else is on the card, only on how it batches,
and its batches change nothing (`test_the_cards_batches_change_nothing`). With the card a video in its measuring keeps
two to four CPUs busy whatever it is given, so a card's job wants many videos with few CPUs each, and they share the
card's memory. Each process planned its batches on half of what was free when it asked, so the first to ask took up to
8.3 GB and the eight together 15.5 GB of the 15.9. Since then each plans within its part (`gpu.part`: 0.9 of the card
less 300 MB a process for what CUDA itself holds, 230-270 MB measured, divided among them; 1.5 GB each of eight), told
how many share it by `MCDONALD_CARD_SHARED`, which the pool sets. A batch takes what is left of the part, never more
than half of what is free on the card. Back to back in one job each (2508, 2527), eight at a time: without parts 430
and 391 s, the card's memory at most 14.3 and 13.8 GB, `layers` 238 and 250 s over the ten objects; with parts 404 s,
5.9 GB and 270 s where a batch took half of what was left (its batches small), 405 s, 8.8 GB and 256 s where it takes
all (as built). Every case of every pool, parts or none, is the same to the bit as alone. No process ran short of
memory in any run, also with 6 GB of the card held by another program, where without parts the card filled to 97 %:
planning on half of what is free adapts by itself. The parts are for the desktop the card also draws, which is why one
process plans on half (SHARE).

## 53. Known answers from three cameras: the Galileo Project's triangulated objects (added 2026-11-13)

**What it is.** The Galileo Project runs three sites of infrared cameras near Las Vegas, 2 and 10 km apart. Its pipeline
matches what two or three sites see at the same moment and finds where the object is: its range, its height and its
velocity, from the crossing lines of sight. That turns the sites' video into known answers for mcDonald, which sees one
camera at a time. The data, the samples and every number below are in the uap repository's `galileo/nevada/README.md`:
40,785 objects over 42 days of 2026, of which 13,697 are aircraft with known tracks (ADS-B) and about 3,000 are clouds
moving with the wind. The lines of sight were rebuilt from each camera's own detections with the project's calibration,
and they triangulate to the pipeline's positions within 0.5 %.

**What it found** (IDEAS.md N1-N7), each built into this version:
- *Drift, T2* (section 34). Clouds 2-5 km up need 3-4 m/s through the air against a model's winds, more than the
  winds' hour-to-hour spread. T2 now allows a model's own error, 3 m/s (`MODEL_WIND_ERR`). With lines of sight from two
  or three sites, `drift` finds the clouds' height to 0.3-2.5 % and their speed to 0.1 m/s; from one camera it says it
  cannot range them, every time, as it should. No aircraft was called a drifter.
- *Drift, T3* (sections 13 and 34). The rule for a beat that comes back took two windows apart on any track. On a long
  track chance gives two: 14 of the 16 beats on clouds and aircraft were no more than chance. Windows apart now count
  only beyond chance (chance from the clip's own background windows since the revision, §13), and a beat seen from
  two cameras at once is held to the second camera too.
- *Size* (`report.extent`). With a track file and no size, the report turned the tracker's default 9-pixel spot into
  metres. In place of that default it now uses the object's length at half its peak brightness, measured on every
  tracked frame by the camera stage, and never turns the default into a size. A spot the marks or `--size` set is what
  someone said the object is, and is read as before. On 170 clips of aircraft of known size, set against the larger of their
  span and length across the line of sight: the spot read 2.80 times their size (0.57-5.6, ten to ninety in a hundred),
  the length 1.29 times (0.94-1.67), the width at half the peak 0.72 times (0.42-0.99). The length and the width bracket
  the true size in 74 % of clips. In infrared the bright parts of an aircraft are smaller than the aircraft: a width that
  matches the camera's blur is not an upper limit on its size.
- *Speed* (`kinematics`, the report's words). The speed across the line of sight, at the given range, matched the
  aircraft's to a median of 1.00. It came within 5 % half the time and within 20 % nine times in ten, and above the truth
  in 30 % of clips: "the least its speed can be" is so only up to the errors of the range and the scale, and the report
  now says so. Near the frame's edge it read 12 % high through k1 alone; `--lens-k2` (section 37) takes the rest of the lens.
- *Pictures* (`flicker.pictures`). It reads 70 % of a Dalek clip's frames as held. The object's own steps show a fresh
  picture every frame: the encoder copies a still sky. The band stays at the frame rate, so no number changes.

**What it could not do.** No bird was triangulated by the pipeline: a bird near one site is under a pixel at another,
2 km away. A search of the second site's detections found two candidates seen from both sites, too briefly to hear a
wingbeat. A search of its pixels cannot work on these files: the encoder copies a still sky unchanged, and a far bird
would be half a grey level.

## 54. Every frame of every video: the batch, what a row of its table is, and the audit's draw (ROADMAP 0.6, objective 1; E8; added 2026-11-13)

**What it is.** `mcdonald batch` (`mcdonald.batch`) runs a list of videos, or the whole catalog, with nobody at the
window: Find on every frame, each lasting spot followed and measured by `stages.run_case`, a report each, a folder a
video, one table over them all. It is the beat sweep of October (`tools/sweep/`, 126 videos, each object measured by
`flicker` alone) as one command with the whole of `mcdonald run` behind each object. It measures nothing of its own:
Find is section 3's, the link section 2's, every stage its own section's. What is its own, and what this section is
for, is four rules -- what a unit of work is, how a video is cut, which of Find's proposals become objects and in what
order, and when a video is not searched at all -- and the audit's draw. Each rule is given with where its numbers came
from, because none of the first three has a null yet.

**The unit is one video.** A video owns its frames from extraction to removal. The frames of a video are extracted
whole and once, into a folder of the unit's own, before any window is searched: windows that overlap and extract at
the same time leave gaps that `Clip.extracted()` did not see until 2026-10-20 (the sweep's trap), and an extraction
decodes from the video's first frame, so forty windows extracted one by one decode a long video forty times. The frames
are removed when the unit is done, so the disk a batch holds at once is that of the videos running at once (about 0.8 MB a
frame at 1920 x 1080: 7.5 GB for a five-minute video). The folder is named for the batch as well as the unit: in the pilot two
batches shared one, and the first to finish removed the frames under the other.
One process runs one unit (`mcdonald batch --out DIR --unit K`), whether a scheduler's array task starts it, a pool on
this computer, or a plain loop; a unit's own pools take the CPUs that process was given (`progress.cpus`), so N units
side by side never ask for more than the machine has.

**How a video is cut, and which proposals are objects** (`cut`, `long_lived`, `merged`, `ordered`; the sweep's
`windows.py` and `collect.py`, moved into the package, which the sweep's scripts now call). Find searches windows of
400 frames that overlap by 30 (`propose.find`, 30 proposals kept a window, as `look --propose --more`), each with
static masks made from its own frames. A proposal is an object where Find saw it on 40 frames or more, with background
all round it on 0.3 of them or more (a spot, not an edge or a stroke), and not as one of a row of marks that slide
together (a scrolling tape). Two proposals are one object where they share 5 frames or more, have one polarity and
lie under 15 px apart on the frames they share (the median); the one seen longest leads. The objects are then put in
order of Find's own score, the best an object had in any window, highest first (ties: seen on more frames, then
earlier), and the first twelve (`--most`) are measured; the rest are listed in the video's `<tag>_batch.json` with why
not. How deep a unit goes is an option, and part of its make: every stage by default; `--quick` without `layers` and
`integrity`; `--only track,report` to the link and no further (each object followed, nothing measured); `--most 0` to
Find alone (the objects listed, none followed). `--keep` keeps more of Find's rows a window than the 30 a person is
shown, for a planted object low on the list. **These numbers are the sweep's, and are judgement with a record, not thresholds from a null**: they found the bird
paper's Table 1 on the sweep's 126 videos, and nothing says what they miss. Completeness -- the share of planted objects
the whole chain finds, per video -- is objective 4 of ROADMAP 0.6 and is not measured here.

What the rule cannot find, by construction:

- *An object in view for fewer than 40 frames.* PR113's transit is four frames and PR43's streak 26: Find proposed
  both, the rule refused both for that alone, and each video is a row "nothing found". So that a short transit is
  counted and not silence, every row carries its video's `brief` (proposals seen on fewer than 40 frames),
  `brief_spots` (those refused for that alone) and `brief_longest`, and `batch.md` has the count a video. A short
  event needs a person or an agent at `look --propose` (section 3), where every row is shown.
- *An object Find cannot see*: one held still on a still scene, or one fainter than Find's floor (section 3's limits).
- *An object in view for 40 to 48 frames across a cut.* With an overlap of 30, an object seen on exactly 40 frames is
  whole in no window when it begins on 9 of every 370 frames (2.4 %); from 49 frames on it is always whole in one.
  `--overlap 40` closes the gap and moves every window off the sweep's.
- *The thirteenth object.* A sea of glitter gives dozens of lasting spots. They are counted and listed (`found`,
  against `measured`), and `<tag>_refused.png` shows a sample; raising `--most` measures them.

Each object's marks are Find's own seeds (`Proposal.seeds`), from every window the object was seen in, so that no
stretch between two marks is long; the sweep marked from the first window only and let the link run on. They are
recorded as an agent's, with the row, the rule and "with nobody looking" as the reason (`batch.HOW`), never as
proposed-and-accepted: nobody accepted them. The report built on them says on its face that an agent, not a person
looking at the frames, decided which spot is the object, and that its numbers are provisional.

**A video that is not searched** (`picture`). A sound recording released as a video is one caption card for
minutes. Before any frame is extracted the picture is read at moments spread evenly over the video (one every 10 s, at
least 40 and at most 600, each a seek), and each is held against the first: the difference, smoothed with a Gaussian
of 2 px, at the point where it is largest. Where that never reaches 4.0 grey levels the video is a row that says so
and nothing more is done. The level and the smoothing are not the batch's: they are the floor and the sigma
`propose.peaks` holds a residual's peak to before it is a candidate, so a picture under them holds nothing Find could
propose at those moments (tests/test_batch.py holds the two pairs of numbers together). The first version of this
test was the frame's mean difference against the level of a repeated frame (0.35 grey levels, `forensics.repeats`),
and it was wrong: a 5-px disc crossing a still sky moves the mean by 0.2 and was called a still picture, which is the
case Find's still pass exists for. It is a strict guard, against a picture that truly never changes, and it spares
little: **of the 144 PURSUE videos none lies under it.** The one sound recording on a single card (NASA-UAP-D3A)
differs from its first moment by 5.8 grey levels at some point, so it was searched: 11,137 frames, no proposal, 21
minutes. The next lowest videos change by 34, 47 and 51, and the median video by 214. A level that also spared D3A
would be the batch's own judgement, and was not set. What the check cannot see is a change shorter than the gap
between two moments, which the row states.

**Resumable, and never mixed.** The plan (`batch_plan.json`) lists the units; a unit's folder holds its state
(`batch_state.json`) and, while it runs, a lock whose time a thread keeps fresh. A lock is dead when its time is ten
minutes old, or when it was made on this computer by a process that no longer runs. Every file a later step reads is
written under another name and renamed. A unit that is done is not done again. One killed half way goes on from the
windows already searched and the objects already measured (`several.measured`: a report from the same marks, measured
to its end); an object half measured is removed and measured again from its marks. A unit's state records its *make*:
the package's version, the options that reach the measuring (`--window`, `--overlap`, `--most`, the stages left out,
the audit's draws) and the rules' own numbers. A unit done by another make is left as it is and counted apart: by
`--status`, in every row (`mcdonald`, `make`), and in `batch.md`'s first lines. `--again` does it again and moves the
old folder aside.

**What a row of the table is, and is not.** A row is one spot that Find saw on 40 frames or more, followed from Find's
marks and measured, with nobody looking. Read it so:

- It is not an identified object. It may be a wave, a rock, a symbol the masks missed, the edge of a redaction block
  that Find's all-round test let through. The counts of labels over the table are counts of reports, not of objects
  in the sky.
- Two rows can be one object, and seven can. Followed twice from two of Find's rows, the second says so (`same_as`,
  section 9's rule). Lost and found again, it is a row each time: two proposals are joined only where they share 5
  frames. In the pilot PR088's seven rows named a bird are one bird of the bird paper's Table 1 in seven pieces, each
  on its recorded track to under a pixel.
- A row can be several objects. Where Find lists a group of points as one spot, the row is the group, measured member
  by member (section 9), and its label is the group's; `several` and `members` say so. PR135's flock is two such rows
  over the frames of the paper's six, each "Beats like a bird". The members become objects of their own only where a
  count is given (`run --each --objects N`), which a batch has none of.
- "Nothing found" means Find proposed nothing that lasted, by the rule above. It does not mean the video is empty.
- A label is the report's, by the stage's own rules and the toolkit's defaults: the stage's beat rule, no aperture
  chosen, no other object kept clear of. The reference case files of the two papers were measured the papers' way
  (the paper's beat rule, its aperture), so a bird of Table 1 can be a row here with another label: PR088's second
  bird is found and followed on its recorded track, measures 3.41 Hz where the paper has 3.52, and is not named.
- Every row is provisional (section 1's gate): `sheet_looked` and the audit's columns say what a person has looked at.
- `no_power` counts are over objects measured; a video with nothing found adds none.

**The audit's draw** (E8; `leverage`, `audit_draw`, `audit_sheet`, `audit_record`). A track sheet of a 3,000-frame
track is forty pages, and "I looked" says nothing of how much was looked at. For each measured object the batch draws
59 frames of its track at random, with replacement, by a generator seeded from the video's file name, the object's
folder and its track's span (so nobody chose them, and anyone can draw them again). A frame's chance is half its
leverage on a straight-line fit of position against time, 1/N + (t - mean)^2 / sum: half the weight is even over the
frames and half grows toward the ends, which move a fitted rate most. `<tag>_audit.png` shows each drawn frame's own
pixels round the track's position, ringed and numbered, and `<tag>_audit.json` holds the draw and, once
`mcdonald batch --audit FOLDER --wrong ...` records a look, who looked, which were wrong, and the bound: the exact
binomial upper limit at 95 % on the share of the track's *weight* that lies on wrong frames (Clopper and Pearson
1934). With none wrong of 59 it is 1 - 0.05^(1/59) = 4.95 %; 58 draws do not reach 5 %. With even weights the bound
would be on the share of frames; with these it is on the share of what the rate rests on. A track of 59 frames or
fewer is shown whole, and its wrong share is then known, not bounded. **The weights are a judgement**: they are right
where the answer is a rate fitted to the whole track, and no better than even weights where it is a beat, to which
every frame counts alike. What an audit does not check: that the spot is an object worth a report (the track sheet
and the strip are for that), or the frames the track does not have. `<tag>_refused.png` is the other half of E8:
up to five proposals, drawn at random by the same seed, of each kind the rules refused -- seen too briefly, an edge
or a line, a scrolling tape, past the cap -- each as Find's own strip.

**How it fails, and its traps.**

- A unit's cost is two parts. Find takes 0.11 to 0.22 s a frame on 8 CPUs of the 2025 workstation, 720p and 1080p
  alike, so a five-minute video is 25 minutes before anything is measured. An object then takes 0.6 to 9 minutes
  (2.8 on average over the pilot's first 21), by the length of its track, and 71 to 81 % of that is `layers` and
  `integrity`, which `--quick` leaves out. Half the CPUs take 1.3 to 1.4 times as long for a whole unit, so several
  units side by side on 4 CPUs each do about 1.5 times the work of half as many on 8.
- Find's proposals are per window; an object that Find drops for a window and finds again later is two objects unless
  their tracks overlap by 5 frames.
- The order is Find's score, which "orders a list for a person" and is "not a probability" (section 3). Past the cap
  the batch trusts it.
- A case file larger than a shared file may be (200 MB) leaves out its track sheets' pages, then every picture, and
  says so in its note and its manifest (`left_out`); it still measures again to its numbers, which need none of them.
- The table is only as current as the folders: `--table` reads them again (a sheet looked at, an audit recorded).
- A scheduler's time limit ends a unit like any kill: the next submission takes it up, but nothing resubmits by
  itself. The size classes' limits and memory (`resources`, `classes`) are fitted to the pilot on one workstation
  (eleven videos; a unit's processes held 1.7 to 4.1 GB), and will be wrong elsewhere by the ratio of the machines.
- A scheduler's own count of a job's memory reads up to the job's limit whatever the unit needs, because it counts the
  frames the system keeps to hand. Size by the unit's `peak_rss_mb`, which counts each process's fair share.

**The first run over the catalog** (2026-11-13/14; all 144 PURSUE videos; the code of commit abdc399, before the CPU
speed-ups of 0.5.5 and after; 4 CPUs a video, 8 for NASA-UAP-D024; arthur, no graphics card; stopped on purpose once
and by two power-downs, and taken up each time from where each video was). Every video is a row or more; none failed.

- 99 videos have objects measured; 45 have nothing that lasted 40 frames (35 of them have spots refused for that
  alone, 5 have no proposal at all). 68,508 proposals in all; 22,744 were refused only for lasting under 40 frames
  (the longest such in a video is 35 frames, the median), in 134 videos. 1,715 spots lasted; 786 were measured (the
  cap of twelve reached in 44 videos), 88 of them not followed (the link found no track from Find's marks), 90
  followed onto the track of another of their video (`same_as`), 100 measured as groups of points.
- The labels: 659 "No physical conclusion", 88 "No conclusion" (not followed), 39 "Beats like a bird", in 14
  videos. Grades: 667 Low, 31 Very low. Every report is provisional: no track sheet has been looked at.
- Against the October pass (the research record of the whole-video beat pass, 121 videos in both): **the same 1,576
  objects, video by video**. The rules moved into the package give the pass's list again.
- Against the reference case files (31 objects of the two papers): 22 have a batch object on their track; 7 more
  are lasting spots past the cap of twelve (PR097's objects 5-8, PR099's object 1, PR141's two); 2 were refused as
  brief (PR113's four-frame transit, PR43's 26-frame streak). Of the 20 objects the papers name birds, 16 are
  followed and 9 named a bird by the toolkit's default rule; the others are measured by the papers' own rule and
  aperture in their files, which the batch does not use.
- The held-out third (42 videos): 248 objects with a row, 1 named a bird (grade Very low); on the other 102 videos
  538 objects and 38 named a bird. Entered in `tools/sweep/looks.tsv`; nothing was tuned on it.
- The `integrity` stage raised on 12 objects of 9 videos, every one 21 px wide or more: its self-test drew its
  synthetic object, or read a window, off the picture (section 54's run found it; fixed after the run, 5c19921).
  Those objects' integrity tests are NO POWER in the table.
- Cost: 153 unit-hours of wall time (151 with the scheduler's pauses taken out), about 650 CPU-hours; Find 78 of
  them, measuring 76. A unit held 0.5 to 4.3 GB (each process's fair share); two videos ran out of 3,000 MB on group
  objects of thousands of followed points (PR063, LLE-PR002) and were measured with 12 GB: a unit's memory depends on
  its objects, which the size classes, fitted to the frame's size, do not see.

## 55. Does something hang under it? `mcdonald tether`'s first outcome (IDEAS.md H5; added 2026-11-13)

**What it is.** Section 6's stage finds what moves with an object and asks whether it swings. Most of what moves
with an object does not swing in the seconds a clip gives, and the stage then had nothing more to say: of AARO's
known balloon PR-004, whose load shows on every track of it, of PR105's three points in a line, of PR28's stem. Decision
5 of the roadmap, as amended on 2026-11-10: a single point has no range-free sign of a balloon (W9), but an object with
something under it has a test, whether it hangs. This is that test. The stage now ends in one of four answers on
every object (`fields.hangs`, `fields.hang`):

- **hangs**: something that moves with the object keeps to a line under it or over it, near the picture's vertical;
- **beside it**: something moves with the object, and its line is not near the vertical (a neighbour in a flock, a
  feature level with it);
- **nothing tied**: nothing moves with it in the ring that was searched, and no line starts at the object;
- **cannot say**: the test has no power on this clip, and why.

It is a statement about the picture. Nothing in the stage knows which way is down in the world: no horizon and no
pointer is read, and an airborne camera's picture can lie at any angle to gravity. So the record says which
vertical every angle is from (`hang.vertical`: "the picture's"), and the report says "straight down the picture",
never "straight down". And it names a class, a body with something on a line under it (a balloon and its load, a
parachute, a sling load under a helicopter), not a balloon. It says nothing of drift.

**What is measured.**

1. *The companion*, exactly as section 6 finds it: the stack, the control, the follower and its gate are unchanged,
   and so is the pendulum's reading.
2. *The line from the object to it* (`tether.line_of`). On each frame that shows the companion, the angle of the
   line from the picture's vertical, whichever end is up: the track can sit on either end of a pair (on PR-004 it sits
   on the lower one on six tracks and on the upper on two). `off_vertical_deg` is the median of that over the frames,
   0 to 90; `spread_deg` its spread by MAD; `within` the share of the frames inside the gate; `length_px` and
   `length_spread` the line's length and how far it strays; `above` whether the companion is over the object.
3. *The companion's place against the object's own picture* (`tether.against_own_picture`). Two points too small to
   resolve are the same point-spread pattern (H6), so the patch of 17 x 17 px about the object, slid over the frame
   about the companion (3 px either way), finds it to a fraction of a pixel, with neither the track's error nor either
   centroid's in the answer. Where the two pictures agree (ZNCC 0.8 or more) on half the frames that show the
   companion, the line is read from those places (`read_against`: "the object's own picture"); where they do not (a
   dark load under a bright balloon), from the follower's own. `same_picture_on` is the share of the frames on which
   they agree. Where it is high, neither end of the pair has a size or a shape of its own to read.
4. *The scene's own turn and scale, beside the line* (`tether.scene_step`, `scene_over`). A line under an object
   turns with the picture when the camera rolls, and grows with it when it zooms. Each frame at half size, its slow
   part taken out, is cut into patches of 64 px; each patch gives its shift from the frame before by phase
   correlation; a similarity (shift, scale, turn) is fitted to the shifts with weights that fall off past 2.5 times
   their typical miss, patches near the object left out. `line.scene.roll_deg` is the range of the summed turn over
   the line's frames, `scale` the range of the summed scale, `read_on` the share of the steps that could be read.
   A step of the zoom between two frames is not such a step: `mcdonald zoom` dates those (section 17), and a track
   that runs across one should be cut there.
5. *A line that starts at the object* (`tether.around`, `at_object`; A19's azimuthal residual). 0.5.2 said the ring
   it searched and that nearer in was not: PR28's stem hangs straight under the head, inside it. The object's own
   picture is now read on rings about it, from where that picture ends (the rings' medians fallen to a quarter of its
   contrast, and two px on) out to 6 px past the ring's inner edge, in 72 directions. On every ring the median over
   the directions and the first harmonic are taken out: what is the same all round the object, and what a centre a
   fraction of a pixel off or a lopsided point-spread pattern puts on one side of every ring. What is left is put in
   units of the ring's own scatter, since the rings nearest a bright object are the noisy ones, and averaged over the
   rings: a profile over direction, one a frame. The frames' mean profile has a strongest direction. It is a line
   that starts at the object where it stands `AT_STRENGTH` times over the mean profile's scatter in the directions
   away from it (`strength`), is on one side (`mirror`: under `AT_MIRROR` of it in the opposite direction; a body
   longer than it is wide, a wing either side, a smear of motion are as strong on both), shows on single frames
   (`seen_on`: 5 times that frame's own scatter over direction, on `AT_SEEN` of the frames) and does not show as
   often at a right angle to it (`beside_on`). The line's angle on each frame that shows it is the peak's, to a
   fraction of the 5 degrees between directions. A bright line under a bright object makes, with the object, a run
   long enough for the stroke mask to take it for the overlay's (PR28's stem is masked on 442 of 1,025 frames): for
   this reading alone, strokes that lie wholly within its reach are taken back (`Frames.unstroked`).

**The rule** (`tether.hang_of`, a function of the record alone).

- The companion's line answers first. It **hangs** where the line lies within 18 degrees of the picture's vertical at
  the median of the frames that show it (`VERTICAL`), and is **beside it** where it does not.
- A line that starts at the object is asked one thing, whether it points down the picture or up it: within the same
  18 degrees, something **hangs**. Out to one side it makes no outcome: 8 of the 80 recorded objects have a one-sided
  picture, every one of them 66 to 87 degrees from the vertical, and each is a neighbour of a tight flock inside the
  ring or the object's own shape, which for an unresolved object is its point-spread pattern (H6). The finding says
  it ("the object's own picture reaches farther on one side").
- Neither: **nothing tied**.
- **Cannot say**: the object moved under 20 px on the screen, or the companion under 20 px against the scene and the
  screen (the stage's two standing "no power" cases); the line shows on fewer than 20 frames; the picture itself
  turned by more than 18 degrees over the line's frames, or over the whole track with nothing found (what hangs
  would have turned with the picture and smeared on the stack: on a drawn clip that rolls 24 degrees a dot under the
  object is not found at all); or the stack was too small to search.
- In `run`, a companion that is a member of the object's group, followed in its own right, is **beside it** whatever
  its line (`hang.of`: "fellow member"): the stage's standing call that a fellow member is not something tied to it.

**Where the numbers come from.**

- *18 degrees is a stated rate on an exact null.* A line that has nothing to do with the vertical lies within 18 of the
  90 degrees a line can lie from it one time in five. Measured: of the 1,526 features the 0.5.2 null followed on tracks
  that nothing keeps step with, 22.1 % lie within 18 degrees (and 10.4 % within 9). One in five is the smallest
  round rate that keeps the known balloon: PR-004's line lies 11.9 to 14.6 degrees off on its eight tracks, where a
  chance line is 13 to 16 % of the time. So the direction of one line is a weak witness, and the record says how weak
  for each line (`line.chance`: PR105's 2 degrees, one time in 45; PR-004's 13 degrees, one time in 7). What makes the
  answer worth having is that a companion must be there first; the rates that matter are counted below.
- *No gate on the line's length or on its spread.* WA9ONY-5's line changes length by 30 % in four seconds (the balloon
  is climbing away from the camera) and swings 13 degrees either side; a rigid neighbour is steadier than any hanging
  load. Both are reported. No rule is a distance in object sizes (H3, H6).
- *The line at the object* takes the companion gate's own numbers for the same ideas: 5 times the scatter
  (`Z_MIN`), at most 0.6 of it where it should not be (`CONTROL`, here the opposite direction), there on 0.3 of the
  frames (`FOLLOWED`), a sighting 5 times the frame's own scatter (`SIGHT`). They were not set again; they are held to
  the null below, and the table shows how the counts move with each. One number is judgement: a line is refused where
  a right angle to it shows on more than half as many frames (`AT_BESIDE`), which no object of the null needs with
  the strokes masked and which refuses PR071's tracking gate when they are not (seen on 30 % of frames, and on 32 %
  at a right angle).
- *20 frames*: the stage's `MIN_SWING_FRAMES`.

**Held to the null** (`tools/tether_null.py stage`, then `hang`; the records are in the reference-data folder,
`tether_null/hang/`). The stage itself, as `mcdonald tether` runs it, on each of the 82 recorded tracks of section 6's
null (AARO's 45, the 31 reference objects, WA9ONY-5, PR071, PR055, PR105, PR28, PR29) and on two null tracks of each,
its own run backwards and its own shifted by half its length, with the same ring searched. A null track's companion
that is the real object, or what the real track's own run followed with it, is not counted.

| asked of | hangs | beside it | nothing tied | cannot say |
|---|---|---|---|---|
| 160 tracks nothing keeps step with | **0** (0 to 2.3 %, exact 95 % interval) | 7 | 153 | 0 |
| 68 recorded objects with nothing known under them | **2** (2.9 %; 0.4 to 10 %) | 13 | 53 | 0 |
| 9 known answers (WA9ONY-5; PR-004's eight tracks) | **9** | 0 | 0 | 0 |
| 4 candidates | PR105, PR28, PR071 | | PR29 | |

The two of the second row are one thing seen twice, PR097's objects 7 and 8 (one flier in two stretches of the clip): a
dark compact blob 14 px straight under the tracked one, 1.9 and 2.2 degrees off the vertical, on seven frames in ten.
Looked at frame by frame it is one of a tight group of dark blobs that keep their places for nine seconds (object 6,
in the same seconds, has one 10 px under it and one 17 px to its right): by the picture a neighbour flying in line,
which this geometry cannot tell from a load. It stands as the test's false alarm of record. The 13 "beside it" are
neighbours in flocks (PR135's six, PR097's) and the far features of section 6's "How it fails". On pairs of separately
recorded objects, read as a companion's line is (`tests/test_tether.py` holds PR135's): of 24 pairs in six clips one
lies within 18 degrees of the vertical (PR097's objects 2 and 3, 7 px apart, 8 degrees), none of PR135's fifteen
within 38.

How the counts move with each number (the same records, the rule changed; `hang --scan`):

| the rule | null tracks that hang (of 160) | nothing known, hang (of 68) | known answers that hang (of 9) | candidates that hang |
|---|---|---|---|---|
| as set: 18 degrees | 0 | 2 | 9 | PR105, PR28, PR071 |
| 6, 9 degrees | 0 | 2 | 0 | PR105, PR28 |
| 12 degrees | 0 | 2 | 3 | PR105, PR28 |
| 15, 20, 25, 30 degrees | 0 | 2 | 9 | PR105, PR28, PR071 |
| 45 degrees | 1 | 4 | 9 | PR105, PR28, PR071 |
| a line at the object from 3 to 10 times the scatter; opposite share 0.2 to any; right-angle share 0.25 to any | 0 | 2 | 9 | the same |
| a line at the object on 0.1 of the frames | 0 | 3 | 9 | the same |
| ... on 0.2, 0.4, 0.5 of the frames | 0 | 2 | 9 | the same |
| no line at the object looked for | 0 | 2 | 9 | PR105, PR071 |

So the null holds the gate anywhere from 15 to 30 degrees, and the four numbers of the line at the object anywhere
in their ranges but one (on 0.1 of the frames a third object passes: AARO's `dod_111311872` object 8, a line at -5
degrees on 15 % of its frames). The 18 is the stated rate's, not the null's.

The stage's own run also rebuilds a number of section 6, and it is not the same: on the 160 null tracks it names a
companion that is neither the real object nor its companion on 7 (4.4 %; 1.8 to 8.8 %), where section 6's replay of
saved chains counts 2. The replay follows 30 candidates a track, chosen by how often they are seen; the stage follows
the 60 strongest that the control does not show. All seven are beside the object, 33 to 83 degrees off the vertical:
four far features on AARO's PR-009 and PR-010 clips, three other birds of PR135's flock.

**Run once on tracks the rule had not seen** (the labelled infrared set of section 44, every one of its 432 tracks:
airplanes, birds, drones, helicopters; and two more of the repository's vendored tracks, PR23's object and the
helicopter of section 34's Santa Barbara hoist), read once after the rule was set and not changed after. Of the 432
labelled tracks, **2 hang** (0.5 %; 0.06 to 1.7 %), 12 are beside it, 348 have nothing tied and 70 are "cannot say"
(44 objects that hardly move on the screen, as the platform follows them, and 26 stacks too small to search: the
frames are 320 by 256). Both that hang were looked at, and both are the ground: a bird (IR_BIRD_076, its second
object) whose companion is a feature of the bright ground band 178 px under it, its angle drifting from 12 to 20
degrees; and a helicopter (IR_HELICOPTER_002) whose companion is one ground feature after another, its angle
sweeping in a sawtooth from +15 to -30 degrees (12 degrees of spread). Both passed the companion gate as section 6's
far scene does. PR23's object and the Santa Barbara Huey: nothing tied.

| unseen tracks | hangs | beside it | nothing tied | cannot say |
|---|---|---|---|---|
| airplanes (82) | 0 | 1 | 64 | 17 |
| birds (125) | 1 | 9 | 99 | 16 |
| drones (168) | 0 | 0 | 149 | 19 |
| helicopters (57) | 1 | 2 | 36 | 18 |
| PR23, the Santa Barbara Huey | 0 | 0 | 2 | 0 |

**The known answers and the candidates, as the stage says them** (`tests/test_golden.py` holds each):

| case | the answer | the line |
|---|---|---|
| WA9ONY-5, a 13 g load a metre under a pico balloon | hangs | 9.4 degrees off at the median of 130 frames, within the gate on all of them while it swings 13 degrees either side; read from the follower's places (a dark load is not the balloon's picture); the picture did not turn |
| AARO's PR-004, "almost certainly a balloon", eight tracks | hangs on all eight | 11.9 to 14.6 degrees off (a chance line is that near 13 to 16 % of the time), over the object on six tracks and under it on two; read against the object's own picture, which the companion matches on 62 to 99 % of frames; spread 1.2 to 2.4 degrees; length 28 to 32 px, steady to 2 to 4 % |
| PR105, frames 1075-2155 | hangs | the lower point: 2.0 degrees off at the median of 494 frames (a chance line is that near one time in 45), spread 3.0 degrees, length 26.3 px steady to 8 %; the picture turned 1.0 degree in 36 s while its clouds streamed past; the middle point, 15 px out and inside the ring, is a line that starts at the object straight down on 54 % of frames |
| PR28, frames 620-1650 | hangs: a line that starts at the object | straight down, 0.9 degrees off at the median of 788 frames, spread 1.3 degrees; 17 times the other directions' scatter, 0.08 of it opposite, on 88 % of single frames and at a right angle on none |
| PR071, the Lake Huron object's string | hangs | 14.9 degrees off (the gate is 18), spread 2.6 degrees, within the gate on 90 % of 207 frames |
| PR29 | nothing tied | a line under the head at +5 degrees, 9.7 times the scatter, but on 15 % of the 43 frames that could be read (93 linked, the tracking gate's strokes across the rest): too few |
| PR135 object 2, a bird | beside it | the next bird of the flock, 48 degrees off |
| PR077 object 1, PR149, PR055 | nothing tied | |

**How it fails.**

- *The picture's vertical is not the world's.* PR-004's pair lies 13 degrees off on every track, and nothing says
  whether that is the camera's tilt or the load's. A camera rolled by more than 18 degrees turns a hanging line into
  "beside it"; where the vertical is known some other way (a horizon, a pointer), the angle is in the record to be
  set against it.
- *One line's direction is one number.* A line with no tie to the vertical passes one time in five, and the report
  says each line's own chance. The answer leans on a companion being there at all: 7 of 160 null tracks get one by
  the stage's own run, none of them near the vertical.
- *A feature of the far scene that keeps the object's pace passes*, where it lies under the object (two of the 432
  unseen tracks, the ground band under a bird and under a helicopter). Its angle drifts or sweeps; nothing here gates
  on that (IDEAS.md H12).
- *A neighbour that keeps its place under the object passes* (PR097's objects 7 and 8). `run` calls a companion a
  fellow member, and so beside it, only where that neighbour was followed as a member of the group.
- *The picture's own turn* is read off the scene, and needs a scene: under 12 patches of texture (an empty sky, a
  small frame) it is not read, the picture's vertical is taken as it stands, and the words say so. It is read from
  the part of the shifts across the scene's motion alone. A similarity fitted to the whole shift reads a scene with
  depth sliding past as a small turn on every frame, and the sum is large: PR105's clouds, level in the picture
  throughout, summed to a roll of 34 degrees and a scale of 1.17 over 36 s that way (session 19's own saved series
  sums to the same). A turn about a point far from the picture's middle, and a lens's distortion under a pan, are
  not modelled.
- *A step of the zoom inside the track* doubles the line's length and smears the stack; the stage does not cut the
  track there.
- *A line that starts at the object* is found on rings about the track's own place: a thin bright line longer than
  the reading's reach is still the stroke mask's (`--no-stroke-mask`); a tracking gate's strokes across the object
  leave too few frames to read (PR29); a neighbour inside the ring, or the object's own long shape, shows as a
  one-sided picture and makes no outcome. There is no known answer for a stem: PR28 and PR29 are candidates by
  AARO's description and their mission reports, and the reading's numbers are the companion gate's, held to the null
  and to drawn clips only.
- *What the companion's gate refuses is not here either* (section 6): a load too faint for single frames, one seen on
  under 0.3 of the frames, one that swings by more than its leash.

## 59. Four readings beside the beat: the position, a band's own line, a beat's shape, the mark's base rate (K2, T2, E11, the row "uap PR089"; added 2026-11-13)

**What they are.** Four readings of `mcdonald flicker` that stand beside its call and change none of it (ROADMAP.md 0.3,
objectives 4 and 5, re-homed to 0.4.x; IDEAS.md K2, T2, E11 and the row "uap PR089, 2026-10-23"). The bird headline and
the gates are decision 6 of the roadmap (sections 7, 8 and 13); a reading here may disagree with the call, and then says
so beside it. How that is held: `tests/test_beat.py` measures three drawn clips with the readings and with them taken
out, and every field, note and result line the stage had is the same (E11's clause is the one thing said inside a
sentence the stage had); the controls harness's 118 check lines are, in full, main's; and the fourteen reference case
files measured again differ from main's by additions (the list is in the session's notes).

### 59.1 The beat in the position (K2; `beatpos`, `flicker.measure`)

**What it answers.** Every beat the stage reports is read from brightness, and a camera's gain, a display or a lamp can
make a brightness beat. A bird's body rises and falls with each stroke and its wings move its light about, so its
position carries the beat too; and a background-subtracted, light-weighted centroid does not move when every pixel is
multiplied by a gain. Geostatistics calls the mark a periodic part leaves in a variogram the hole effect (Journel &
Huijbregts 1978): the variogram dips at the period. The kriging survey (2026-10-16, its section 1.5) read it on the five
Galileo flyers' tracks.

**The series.** The object's own centroid on every frame, as the stage reads it for `scene_shift` (`flicker.centred`:
the contrast over the ring's median within the aperture, as weights, twice), not the track it was given: a hand track,
a label's box or a link's output need not hold a rhythm, and on the flyers the paper's tracks sit 0.8-2.4 px from the
centroid (a steady offset). A frame whose picture the video holds is a missing sample only where the centroid also stood
still on it (`still_held`: it moved less than REPEAT_SHARE = 0.25 of its typical step on the fresh frames, or less than
REPEAT_PX = 0.02). An encoder that skips a still sky "holds" 45-78 % of the flyers' frames by their thumbnails, and the
bird moves on nearly all of them; on a picture truly held the step is a twentieth of a fresh frame's or less (PR44,
PR055, the labelled set's 20-a-second clips: 0.01-0.13 px against 0.3-4.9), and not nought, because the aperture it is
read in has moved on with the track.

**The reading** (`beatpos.reading`). The series less its running mean over 0.5 s (`flicker.DETREND_S`), in stretches of
SEG_S = 4 s, half overlapping (a wingbeat wanders 2-5 % over 4.5 s, section 18: over a longer stretch its line smears).
Each coordinate is fitted once, on the track's middle FIT_MAX = 300 points, by universal kriging (section 32: a line, a
Matérn-3/2 wander and a nugget by REML; M8's cosine left out), and DRAWS = 1,000 tracks are drawn from that covariance on
the track's own frames and gaps, three stretches at a time. Each stretch's Hann-windowed spectrum, a coordinate, is
divided by the draws' mean spectrum there (what the track's own wander and jitter make at that frequency through the
same running mean), the two coordinates added, and the sum divided by its own median over the band: the fitted model
gives the continuum's shape and the stretch gives its level, so a jitter that changes along a track does not pass for a
rhythm. The stretches are averaged. The strongest frequency of the average between LOW and the band's top is the
track's periodic part; its chance p is the share of the draws, read the same way, whose strongest anywhere in the band
stands as high (the band is paid for), and it is a rhythm where p < ALPHA = 0.01. Its frequency has an error
(`flicker.hz_error`, section 12, on the coordinate that carries more of it, over the stretch where it stands highest),
its amplitude is the root of the stretches' mean squared amplitude a coordinate, and `needed_px` is the smallest rhythm
that would have shown three times in four (below). Not white noise: surrogates of white jitter find rhythms everywhere
(sections 39 and 48.1 paid for that).

**At the brightness beat** (`at_beat`). Where the stage has a beat for the object, the same average is read within one
resolution of the beat (or three of its errors, if more), of its double and of its half -- a wing's brightness changes
twice a stroke where its body rises once -- a frequency given beforehand each, the chance the least of the three times
the number tried. `agrees`: a rhythm there, the two frequencies within Z_AGREE = 3 of their combined errors.

**Periodogram or hole: measured both.** The variogram's hole (`hole=True`: how deep the variogram of each stretch dips
at each lag against half of it, standardized by the same draws) was held to the same tracks. On recorded objects with
no wingbeat it called a rhythm on 5 of AARO's 42 and on 4 of 5 others (WA9ONY-5's balloon, PR055's sphere, PR28, PR105)
where the periodogram called 0 and 1; of wobbles planted in the 83 recorded tracks it found 9, 10, 13, 21 and 34 % at
0.05, 0.1, 0.2, 0.4 and 0.8 px where the periodogram found 2, 10, 32, 48 and 72 %. A short-lag variogram follows the
detector's memory (section 32), which a Matérn and a nugget do not draw. So the periodogram is the reading; the hole is
an option of `reading`, not in the stage's output.

**Whose motion** (`beatpos.of_stage`; the stage's `position_beat[name]`). A track in the picture is the object's motion
less the camera's, and a camera that shakes puts its shake in every track: on the labelled infrared set, whose camera
follows its target on a pan-and-tilt platform, a rhythm is found as the picture has it on 39 % of the birds, 52 % of the
airplanes, 43 % of the drones and 83 % of the helicopters, and on 17-57 % of the background features followed beside
them, at 8.2-8.3, 6.1, 4.0-4.2 and 3.6-3.9 Hz again and again; at a frequency drawn at random, 15-35 %. So `how` says
how the camera's motion stood:

- **"scene"**: the track less the registered scene's path (`scene_shift`'s, which `measure` hands on; read where a beat
  would name a bird, as `run` asks it, or with `--scene-shift`, which now registers the scene for the position even
  where no beat of its own asks for it);
- **"members"**: in a group, the track less the mean position of the other members in view on 80 % of its frames
  (OTHERS_COVER), which moves with the camera;
- **"picture"**: the track as the picture has it. The rhythm is then given with `own` None, and the words say that the
  camera's own motion was not taken out and what would show it.

`own` is True where a rhythm stands with the camera's motion out, False where none does, None where nothing can say.

**The codec's rhythm is in a position too.** Where an encoder holds part of the picture on its predicted frames, a
centroid stops and starts at the codec's rate: Galileo flyer 1 (0.3 px a frame) stands still on 11-19 % of the frames at
four of the five places of its GOP and never at the fifth, and its strongest rhythm is 11.97 ± 0.04 Hz, a fifth of the
frame rate, 9.6 times its neighbours against its wingbeat's 6.9. `codec_lines` takes the anchors' lines from `clip.gop`
and the I frames' own rate with its multiples where that is LOW or more. A peak within `flicker.Z_LINE` of its own
frequency error of a line is the codec's, said apart (`codec`), and the next strongest beyond CLEAR_RES resolutions is
the track's. A mask a resolution either side of each line was tried first and dropped: about PR135's 7.49 Hz it hid three
of the six wingbeats. The reading at the brightness beat is held to the brightness's own error, the smaller: a beat the
stage has told from the codec's line is not put back on it by the position's wider error.

**Held pictures keep a cadence, and there the reading is not made.** A video made from a slower source holds pictures
by a rule: 20 pictures a second on a grid of 30 holds every third (the labelled set's drones, PR44, PR055). Left out
as missing samples, the held frames still leave a rhythm. The fresh pictures run on the source's clock, so each shows
the scene a part of a frame off its own frame's time, by turns, and a steady motion read at the frames' times steps at
the cadence: a sixtieth of a second, 0.45 px at 27 px a second. IR_DRONE_059, whose brightness "beat" at 10 Hz is that
cadence's (section 47's false alarm), showed 0.34 px at 10.00 Hz in its position, and the reading as first built called
it the object's own. The samples' own spectral window finds the rule (`sampling_lines`: a line where the window, under
a Hann taper, stands at WINDOW_LINE = 0.01 or more and WINDOW_CHANCE = 20 times what the same number of frames missing
at random gives; one frame held in three gives 0.25 at a third of the frame rate, one in five 0.06 at a fifth and at
two fifths, one in ten 0.012). Two remedies were built and measured before the present one. Calling the window's lines
the video's, as the codec's are, left the step's sidebands (0.11 px at 10.16 Hz on the drone). Taking a cosine and a
sine out at each line in every 4-s piece before the fit, and leaving out 1 Hz either side, was held to the null of
background features followed on such clips, each against its fellows: a rhythm on 7 of 14 of the flyers' features and
on 32 of 68 of the labelled set's, against 11 of 194 on full sets of frames. So where the rule is found the reading has
NO POWER and says so (`sampling_lines_hz`, and `why`: "the video holds its pictures at a steady rate ..."). That gives
up PR44, a bird whose position carried its 3.06-Hz beat at 3.09 ± 0.02 Hz by 0.91 px when it was read; a reading that
is wrong half the time on what holds still is not one to keep for the sake of one that came out right. The running
mean is taken with the gaps filled across in a straight line (`_against_trend`), so that a window's mean sits at its
middle whatever is missing from it. And a stretch is read only where 70 % of its frames have a position (COVER):
between 40 and 70 %, with no rule found, the same null gave a rhythm on 4 features of 20. The bars WINDOW_LINE and
WINDOW_CHANCE are judgement, set where a cadence of one frame in ten still shows and 60 frames missing at random from
300 do not (`test_beat`); COVER is from that null.

**What else moves a centroid: a brightness over an uneven background.** Gain-proof is not lamp-proof. The centroid
weighs the object's light and what is behind it together, so a brightness that beats over an uneven background leans
the centroid toward the background as it dims: a rhythm in the position, at the beat, with no motion at all. On 576
drawn scenes of a point whose brightness beats by 20 % over a textured background, with no motion of its own
(`lever_null`), the centroid's rhythm per unit of brightness change -- the lever, px -- had its median at 0.10, 0.22,
0.38 and 0.68 and its 99th centile at 0.46, 0.93, 1.69 and 2.60 for a background contrast of 0.05, 0.12, 0.25 and 0.5 of
the object's peak. The recorded birds' levers are 0.5-3.6 px. So size alone does not tell them apart, and where a rhythm
is found at the beat the stage reads its lever (`at_beat["without_brightness"]["px_per_brightness"]`: the position's
amplitude over the brightness's at that frequency) and holds it to the object's own background: `background_level`, the
root mean square of its background apertures' brightness over its own median brightness (0.02-0.15 on the flyers and
the reference birds). On the drawn scenes the lever over that level has its median at 0.65, its 90th centile at 2.4, its
99th at 5.2 and its most at 6.6 (1.9 to 6.4 at the 99th by the scene's kind: least where the background slides fast under
the object, most where it holds still). LEVER_K = 5.2 times the level is `reach_px`, what such a background gives 99
times in 100; `beyond_background` says whether the rhythm is more, and `own` is None where it is not. By it PR135's six
(levers 2.5-3.6 against a reach of 0.4-0.8) and flyers 2, 4 and 5 (1.3-2.6 against 0.1-0.2) are beyond their backgrounds;
flyer 1 (0.76 against 0.67) barely, and flyer 3 (0.52 against 0.59) not: on those two the reading cannot say the rhythm is
more than their backgrounds could make. Beside it each stretch's
position is regressed on the brightness at no lag and what is left read again (`share`, `p`, `line`): that takes out a
lean that keeps its direction (a neighbour's light, a scene that rides with the object), and not one whose direction
changes as the background slides under the object, which is why the lever is the one held to a null.

**The null, and the rate it really holds.** On tracks drawn with no rhythm (`test_beat`: a wander and jitter, jitter
with a frame's memory, a fast wander; 36 tracks) none is given one. On recorded objects with no wingbeat, as the picture
has it: of AARO's 40 with the power to say, 1 (3.1 Hz; 2.5 %, exact 95 % 0.1-13 %); PR23, 0; of WA9ONY-5's balloon,
PR071, PR28 and PR105, one, PR105's upper point (2.7 Hz at 2.2 px over 28 stretches: a real swing, or the camera's);
PR055's sphere is not read (held pictures). At a frequency drawn at random: 0 of 40, 0, 1 of 4 (PR105 again). With the
camera's motion out, by the members' route: each background feature of those clips (bright patches away from every
track, each followed by the same centroid) against the mean of the others followed with it, 197 with the power to say
-- a rhythm with no frequency given on 12 (6.1 %, exact 95 % 3.2-10.4 %: AARO 8 of 86, the flyers 0 of 12, PR23 1 of 8,
the others 2 of 21, the reference clips 1 of 70), and at a frequency drawn at random on 7 (3.6 %; exact 95 %
1.4-7.2 %). So the stated 1 in 100 is the drawn tracks'; on these cameras' real backgrounds a rhythm is found at a
frequency given beforehand about 4 times in 100 and with none given about 6, because a real feature's jitter is not a
Matérn's and a nugget's (section 39 met the same on brightness). On the labelled set's clips (320 x 256, a scene that
slides several pixels a frame behind a followed target) the same null does far worse: 198 of 1,078 features against
their fellows (18.4 %) with no frequency given and 97 (9.0 %) at one drawn at random. The mean of a few features does
not take that platform's motion out; a rate from that set does not speak for this reading.

**Completeness** (wobbles planted in the stage's own centroids, a direction and a frequency drawn at random): on the 78
recorded tracks that can be read, 2, 12, 29, 51 and 75 % are found at 0.05, 0.1, 0.2, 0.4 and 0.8 px with no frequency
given, and 13, 26, 51, 72 and 87 % at the frequency given; on the labelled set's 421, whose tracks are quieter, 54, 76,
87, 95 and 99 % with none given. `needed_px` is NEEDED = 2.2 times the amplitude that would just stand at the level,
along the quieter coordinate at the band's middle: of the 3,275 wobbles planted in both sets, 71 % of those at 0.75 to
1 times it are found, 83 % at 1 to 1.5 times, 89 % at 1.5 to 2 times, 99 % over 3 times.

**The known birds.** The five flyers through the stage, the scene registered (a camera that does not move, so the
scene's path is nought and the track is the object's): flyer 1 3.41 ± 0.17 Hz (the paper's 3.36), 0.18 px, the codec's
12.00 Hz said apart; flyer 2 4.41 ± 0.05 (4.49), 0.36 px; flyer 3 10.00 ± 0.12 (10.04), 0.15 px; flyer 4 8.50 ± 0.22,
twice the 4.19-4.25 Hz the stage's own windows read on it (the paper's 3.85), 0.11 px; flyer 5 7.93 ± 0.64, twice its
3.92, 0.21 px; chance 0.002-0.003 each. The roadmap's "within 0.1 Hz" holds for three of the five by this reading;
two beat in the position at twice the rate. Four of the five move more than their backgrounds give a beating
brightness (0.8-4.2 px for a unit of brightness against a reach of 0.11-0.67); flyer 3 does not (0.50 against 0.59),
and its reading says "the object may not move at all". PR135's six, each against the other five: 7.92, 7.37, 7.84,
7.17, 7.69 and 7.74 Hz against their brightness's 7.85, 7.39, 8.02, 7.09, 7.90 and 7.74, by 0.46-0.72 px, chance 0.002
each, all six within their errors and beyond their backgrounds' reach (2.2-5.9 px for a unit of brightness against
0.17-0.54).
Of the 27 reference objects with a beat that can be read, as the picture has it, 19 carry it in their position at 1
in 100 (PR085 at 7.41 ± 0.06, PR088's object 2 at 10.53 ± 0.12 by 0.37 px over 59 stretches, PR41 at 6.44 ± 0.01 by
0.92 px); 8 do not, PR144's object, which has no beat of its own, among them. PR44, whose position carried its beat
at 3.09 ± 0.02 Hz by 0.91 px before held pictures were left unread, is now NO POWER (above). GL6's lead (PR085, frames 2983-3548: a line in the brightness with the track bending at the same rate) is that
reading. With the scene registered the position moves at 7.34 ± 0.04 Hz by 0.24 px, chance 0.002, 4.8 px for a unit
of brightness where its background gives 0.41 at most. The stage calls no beat on that stretch (its one window at
7.28 Hz is not kept); the band search holds the same line (section 59.2).

**Cost.** One REML fit a coordinate (300 points at most) and the draws: 1.2 s at the median and 1.4 s at the 90th
centile a track on one CPU of Cannon's; PR088's object 2 (3,558 frames, 59 stretches) 5.4 s.

**What it does not do, and its traps.** It does not say a rhythm is a wingbeat: a swinging payload moves a position
too (PR105). As the picture has it, it does not say whose motion it is. A rhythm at a codec line cannot be told from
the codec's. With two members only, the difference holds both members' rhythms. The scene's path is one translation of
the whole picture: a scene that turns or zooms leaves a residue. The lever's bound rests on drawn scenes, and the
background's level is read 25 px from the object (or at its own apertures), not under it. The saved curves of the
controls harness do not hold the centroid, so the harness cannot hold this reading: the goldens do (the flyers and
PR135, `tests/test_golden.py`).

### 59.2 A line in a look-alike band, held against the background's apertures (`beatlines`)

**What it answers.** The headline reads a curve's single strongest peak. On a target the camera holds, that peak is
often a slow wander at 1.5-3 Hz, and a real line in a faster band is then never judged for itself (the row's case,
PR089 frames 481-720: 10.50 Hz at 4.4 % behind the drift, the verdict "no beat"). Built: only the reading. The row's
other half, a verdict taken from the battery of tests, is the headline rule, and is not here.

**The reading** (`beatlines.search`, from the curves; `band_lines[name]`). The object's curve and each background
aperture's -- each against its running mean, the backgrounds in the object's brightness, as the stage reads them -- in
stretches of 4 s, half overlapping. The object's running mean is held at LEVEL_FLOOR = 0.5 of its median or more:
where the object fades to nothing for a moment the running mean nears nought and the share explodes. On PR088's
object 2, as its case file measures it, two stretches reached 116 times its brightness and alone made a "line" at
8.09 Hz, 64 % of its brightness (found by the gate, 2026-11-14; `test_beat` holds it). Where the running mean never
falls so far the curve is the stage's own. Reading every curve as a share of the median instead was tried and
dropped: it weighs the bright stretches over the faint, and on the saved curve sets it said a line that is not the
stage's beat on 7 objects more (a harmonic of flyer 1's beat among them) and on 2 fewer. The stretches' power spectra are averaged (Welch), and each frequency is divided by
the mean of its neighbours within SIDE_HZ = 2.5 Hz (or eight resolutions), its own lobe left out: how it stands over its
own continuum, whatever the continuum's level or slope. In each band of the look-alike table that does not cover the
whole band (at 30 frames a second: the lantern's 4.7-8.7 Hz, the bus as heard, the lamp on it, the candles'), the
object's strongest is its line.

**Its chance, in two parts.** How a frequency with no line stands does not depend on the curve's noise, only on the
reading. So DRAWS = 2,000 curves of grain alone, of the track's length, are searched the same way, and the chance is the
share of them whose strongest in the band stands as high, times the number of bands (the band's width and the bands are
paid for). The background apertures then say whether this clip is such a curve: their standing at the frequencies
searched, two resolutions apart, pooled, is held to the drawn curves' by their medians and their 90th centiles, and
where the background stands higher the object's standing is taken down by as much (`background_over_grain`; POOL_MIN =
20 frequencies, or NO POWER). A line is one where the chance is under LINE_P = 0.01, it stands over every background
aperture's strongest in the band, and no background aperture beats half as strongly there in the object's brightness
(`flicker.SHARED`, the stage's own rule for a beat the background shares). Two forms failed first and are not in the
code: a gamma fitted to the pool by its mean and variance (a few lines in the pool widen it without limit: a line
standing 174 times read as chance 0.39), and an F distribution fitted to the pool's two quantiles (1.3-8 % false lines
on curves of 90-150 frames).

**The null.** Drawn curves with no line (400 a row): at 60, 90, 150, 240 and 600 frames, for grain alone, a wander with
grain and a wander with little grain, a line is given 0 to 1.0 % of the time, all bands together. Each background
aperture searched as the object against the other three (the control by construction, `false_alarm` in every
measurement): 15 lines in 5,772 band searches (0.26 %) over the 459 saved curve sets (the controls harness's 27 and the
labelled infrared set's 432, judged again from their curves under the stage's rule). On real objects that are not
birds: on the 27 controls' 29 objects, one line that is not the stage's own beat, on v030 (a helicopter in visible
light with an anti-collision strobe): 10.34 Hz at 0.7 % of its brightness, 7.8 times its neighbours, chance 0.002,
where the stage calls no beat. It showed only once the running mean was held off nought (above): that object fades
with its strobe. On the labelled set's non-birds a line
is said on 5 of the 286 the search could read (1.7 %; exact 95 % 0.6-4.0 %): 2 of 80 airplanes, 3 of 162 drones and 0
of 44 helicopters. IR_AIRPLANE_001 (8.13 Hz at 1.0 %, the line the paper's rule calls a beat there; that camera's
platform shakes at 8.2-8.3 Hz, section 59.1) and IR_AIRPLANE_074 (10.22 Hz at 1.3 %) hold a line beside the stage's
strongest rhythm. On IR_DRONE_024 (9.84 Hz at 0.4 %), IR_DRONE_026 (8.09 Hz at 0.7 %) and IR_DRONE_072 (5.34 Hz at
1.9 %) the line is the stage's own strongest rhythm, which its tests did not hold to be a beat (`the_peak`). So these
are rhythms that are in the brightness, not chance; what makes them is not the search's to say, and the stage's call
on all five stays "no beat". That 1.7 % is the rate at which this reading and the call part on objects known not to
be birds. The held-out third of the release videos was not touched: the reading was built on drawn curves and read on
these sets.

**Completeness** (drawn: a wander of 8 %, grain of 2 % a frame): a line of 2, 3, 4.4 and 6 % is found 9, 39, 68 and 85 %
of the time at 150 frames and 32, 76, 78 and 87 % at 240.

**What it says.** Where a band holds a line that is not the stage's own beat (within a resolution of it or of its
double), the notes say "a line at f Hz, a % of its brightness, in the N-M Hz band, which the background beside it does
not show (chance p)", and whether the stage calls a beat; the report's bottom line says it in a reader's words. Where
the line is the stage's own beat, nothing more is said. Where it is the stage's strongest rhythm and the stage did not call it a beat
(`the_peak`), the note says that the stage's own tests did not hold it, and that the finding says why. On the 27
controls (v030 apart, above) no band holds a line that is not the stage's
own beat; where a control's beat lies inside a band, the search holds the same line (flyers 2, 3 and 4, PR135's six,
AIRPLANE_064, DRONE_059), at the paper's frequency where the stage reports its clearest window's (flyer 2: 4.48 Hz
against the stage's 4.25 and the paper's 4.49; flyer 4: 3.88 against 4.19 and 3.85). On the labelled set's birds it adds
a second line beside the beat on two (IR_BIRD_053, 6.47 Hz beside its 3.06; IR_BIRD_067, 5.91 beside its 2.44).

**Where it parts from the call on the release videos read so far** (the stage run whole on each, 2026-11-13). PR089's
object 3 (frames 483-667): the stage calls no beat, its strongest rhythm standing 9.3 times where 9.4 is needed over
the drift; the search holds it as a line, 10.50 Hz at 5.0 % of the brightness, 8.1 times its neighbours where the
background's apertures stand 3.4 at most, chance 0.008. PR089's objects 0, 2 and 4 hold no line. PR085 (frames
2983-3548, GL6's stretch): the stage calls no beat; the search holds 7.34 Hz at 5.0 %, 18.5 times its neighbours
(the background's 2.2), chance 0.002, within the codec's 7.5 Hz by its error and said so. The fourteen reference case
files are read by the gate (below, and the strand's notes).

### 59.3 The shape of a beat that sits on a look-alike (T2; `beatshape`)

**What it answers.** A beat near 10 Hz at 29.97 frames a second sits on a third of the frame rate, where a chain's
rhythm, a held-picture cadence and the folded lines of mains and aircraft power all land, and where a small bird beats
(section 9; the bird paper's Table 1 has PR077's object and PR088's object 2 there). Frequency cannot tell them apart.
Three readings of the beat's shape, for a beat of the object's own marked with a look-alike a supply or the sensor
chain makes (`chain_marked`: every mark but the flames' and the rotors', which are the object's own); none decides.

1. **Its depth along the track** (`depth_along`). Pieces of DEPTH_S = 2 s end to end (DEPTH_PIECES = 24 of them, evenly
   spread, on a longer track: short enough that a wander inside a piece does not lower its depth), each fitted as the
   steadiness reading fits its pieces, the depths compared in units of their errors; p is the share of 200 beats of
   one steady depth, planted at the beat in the pieces' own residuals, whose depths come apart as far. A lamp's
   flicker and a gain's rhythm are a fixed share of the brightness wherever the object is; a wing's depth changes with
   its aspect -- **and so does the rhythm of held pictures**: IR_DRONE_059, the labelled set's false alarm at a third
   of the frame rate (a 20-a-second source on a 30-a-second grid, section 44), runs from 2.6 to 14.4 % over its five
   pieces (p 0.005). So a depth that changes excludes a lamp and a gain, not held pictures; the cadence itself is the
   held-picture test's to find.
2. **Its wander**: `flicker.steadiness` (section 18), as read already.
3. **Its width outside a fixed core** (`width_outside_core`, from the object's stamps). A brighter point covers more
   pixels above any threshold, so a pixel area that beats in step with the brightness follows the brightness (the bird
   paper's caution on PR135). What separates them is the light outside a core of CORE_PX = 3 px that is the same on
   every frame: its share in the outer of two rings of equal area, between the core and the aperture's own ring, does
   not change where the picture of the object is multiplied, and does where it changes shape. That share, as a curve,
   is read at the beat by the harmonic F-test (`flicker.line_test`, a frequency given beforehand, WIDTH_P = 0.01). The
   reading plants its own test of power: every stamp stretched about its middle by 1 + 0.1 cos(2 pi f t); where that
   does not show, or the light outside the core stands under WIDTH_SNR = 10 times its own frame-to-frame scatter (a
   point), or pixels outside the core sit at the picture's floor or ceiling on a twentieth of the frames, it is NO
   POWER and says which.

**Pieces where the object is not all there.** A piece whose own median brightness is under DEPTH_LEVEL = 0.5 of the
stretch's is left out (`left_out`): its depth over a running mean near nought is not a depth (PR088's object 2 in its
case file: one piece at a hundredth of the median, a "depth" of 690 %). Under two pieces left, the depth is not read.

**Held to** (`test_beat`, drawn): a beat of one depth is said to change 0 times in 12; one whose depth doubles along 10
s, 7 times in 8; a blob 3 px in sigma whose brightness alone beats by 20 % has no line in its width outside the core
(p 0.04) where the planted change shows (p 2e-9), though its pixel area beats in step (p 3e-10); one whose width beats
by 8 % has (p 7e-11); a point and a blob clipped beyond its core are NO POWER.

**On objects whose nature is known** (the stage run whole on each, 2026-11-13; the curves of the labelled set judged
again). Galileo flyer 3, a bird at 10.03 Hz: its depth runs from 27 to 30 % over 2 pieces, no more than a steady
beat's does (chance 0.60; a third piece, where the bird is under half its median brightness, left out); its frequency wanders (chance 0.005 of a clock's); its width is a point. PR135's six
(7.1-8.0 Hz): depths that do not change (chance 0.07-0.94, 2 pieces each), frequencies that wander at 1 in 100 on four
of the six (0.005-0.025 over all six), widths not read (a point, or pixels outside the core clipped on 7-35 % of the
frames). IR_DRONE_059, a held-picture cadence at 10.00 Hz: its depth changes (2.6-14.4 %, chance 0.005), its frequency
holds (0.06), its width is not read (clipped). On the labelled set's curves the depth also changes on IR_DRONE_023
and IR_DRONE_098 (cadences at 10 Hz), on three helicopters' beats (IR_HELICOPTER_051, 054 and 055) and on one bird's
(IR_BIRD_027's object 1, of four birds read). So the depth does not sort a bird from a cadence; the width was read on
none of these, all points or clipped cores; and the steadiness is the one of the three that parted the known birds
from the known cadence here. Seven birds and one cadence are not a calibration, and the three readings stay readings.
The two objects of the bird paper's Table 1 were read with all three for the maintainer: the numbers are fields of
the stage's output (`morphology[name]`), and they decide nothing.

**Cost.** The depth 1.6 s for a 10-s track and 5 s for PR088's object 2; the width a few hundredths of a second.

### 59.4 The look-alike mark's base rate (E11; `flicker.marked_share`)

The share of the band a beat is looked for in where a beat would be marked by `at_lookalikes`: the union of every
line's reach and every band's pieces (a band that covers the band marks nothing), over the band's width. From the table
alone it is 69.5 % of 1.5-12 Hz at 29.97 and 30 frames a second -- one piece, 4.7-12 Hz, the lantern's band and the folded
lamp on the bus -- and all of 1.5-24 Hz at 59.94 and 60 (the 2026-10-28 measurement, rebuilt); 60 % at 24 and 23.976,
73 % at 25, 87.5 % at 50. Read as a beat is, with its resolution, it is wider: 71 % at 0.2 Hz, 74 % at 0.5 Hz. The stage
keeps the table's own (`lookalike_share`) and each beat's (`beat[..]["lookalike_share"]`), and says it where a mark is
said: in the finding ("at this frame rate such marks cover 71% of the frequencies a beat is looked for at, so a mark
is weak evidence") and in the mark's note.

## 60. One rigid body or several, and do the members keep their places: two calibrated readings in `mcdonald groups` (M7, B23, E21, S14; added 2026-11-13)

`groups` has called a group rigid or shuffling since 0.2 by two numbers set by hand: every pair's separation within
RIGID = 2.0 times the members' position noise, or the median pair past SHUFFLE = 3.0 times it and a pixel. The call
stands. Beside it the stage now makes two readings whose lines come from nulls, each with "cannot say" among its
answers (`groups.one_body`, `groups.places`; the fields `one_body` and `places`, two lines of the stage's result, and
an entry of its no-power list where a reading cannot say).

**What each answers.**

- *One rigid body, or several* (`one_body`; the pure-mathematics survey's M7). P points of one rigid body seen from
  far off satisfy x = M X + t on every frame (an affine camera: weak perspective), so the 2F x P matrix of their
  positions, each frame's mean over the points taken off, is M S: of rank 3 at most, 2 for a flat body or one that
  does not turn in depth (Tomasi & Kanade 1992). A shift, roll, zoom or shear of the picture, frame by frame, changes
  M and not the rank. Independent objects have no such bound. The reading takes what is left off the best rank-3
  fit (Eckart & Young), as time series along the member-space directions the fit did not take: 2 (P - 4) of them, so
  five members at least; with four members the fit is of rank 2 and a failure means "several, or one solid body
  turning"; three points are a triangle and any triangle is an affine picture of any other, so nothing is asked.
- *Do the members keep their places* (`places`; the economics survey's E21 on the seismology survey's S14). Every
  pair's separation, divided by the group's size on that frame (the root mean square of all the separations) where
  there are three members or more, so that a zoom, a roll or a shift of the whole picture changes nothing; quoted in
  pixels at the group's mean size. Each is read about a straight line in time, as `rigidity` reads it: a steady change
  of aspect is not a change of places. Two members have one separation and no size to divide by: it is read as it is,
  and the words say a zoom would change it too.

**When a reading says the group moved.** Three things must hold together, each with a null of its own:

1. *It keeps going.* The KPSS statistic (Kwiatkowski, Phillips, Schmidt & Shin 1992): the squared partial sums of the
   residuals over n², over their long-run variance in a Bartlett window of l = int(4 (n/100)^(1/4)) frames; about a
   level for what is left off the rank (pooled over its series), about a trend for a separation. Its null is drawn
   from the series itself: DRAWS = 999 times, its residuals are laid out again as blocks of l + 1 consecutive frames
   in a shuffled order (a moving-block bootstrap; for the rank, added back to the fitted body and fitted again), and
   p is the share of draws whose statistic reaches the measured one; for the separations, each draw's largest pair,
   so that the group has one rate whatever its number of pairs. The draws keep the jitter's own size and its own
   colour up to a block's length, whatever they are, and lose what lasts longer. p < ALPHA = 0.01.
2. *It is large against the jitter.* The wander (what is left off the rank; a separation's rms about its line) over
   the jitter read at the frame scale stands past RANK_LINE = 2.5 (3.0 at rank 2) or PAIR_LINE = 3.3. The jitter is
   read on the series itself -- for a separation that is a double difference, across the two members and then in
   time, which takes the camera's shake out (S14) -- as sqrt((g0 - gk) / 10) from second differences k frames apart
   (white jitter gives g0 = 6 s² and an autocovariance gk = -4 s² at any k; `_noise`'s reading, at k = 1), the largest
   over k = 1, 2, 3. The lines are the 99th percentiles on drawn rigid groups that carry the detector's real errors
   (below).
3. *It is large in pixels.* Past PX_FLOOR = 1 px for a separation, and past what a pixel on every member's place
   would leave off the rank, sqrt((P - 1 - r) / P) px. A member that crosses the pixel grid slowly can turn its
   whole error into a slow wander that no reading at the frame scale sees; 1.05 px is the 99th percentile of the
   planted dots' own error (rms an axis), and it is the pixel `rigidity`'s rule already asked for.

And for a separation a fourth: *it does not return.* The augmented Dickey-Fuller t ratio (a constant, a trend, l
lagged differences) is not under MacKinnon's (2010) 5 % line. A pair WANDERS with all four. A pair KEEPS its
separation where the wander is not large by 2 and 3: that is a measured bound, quoted with the answer, not a test
that failed to reject; unless the lines themselves are wider than the separation (a pair closer together than the
detector's own errors: cannot say). A large wander that does not keep going, or that returns (a cycle), is "cannot
say": the tests disagree. The group wanders with any pair and keeps its places with every pair. For the rank:
SEVERAL with 1 to 3 (five members or more); large and not going, "cannot say" (one body that flexes, or several
holding station); else ONE RIGID BODY. Both readings need TEST_MIN_FRAMES = 60 frames that the members share
(members are taken longest-followed first while that holds, MOST_MEMBERS = 8 at most).

**Why it is not the residual in pixels against rigid bodies drawn with the jitter's measured colour** (the form M7
and B23 proposed). Measured before anything was built:

- The colour cannot be measured where it matters. An AR(1) jitter moves the lag-1 correlation of a member's second
  differences from -2/3 (white) to -1/2 (a walk). PR135's six read -0.22 to -0.41, outside that range altogether:
  each bird's centroid moves with its wings every four frames. A drone show on a camera that repeats its pictures
  reads -0.49 to -0.65 and a jitter of 0.011 to 0.017 px for separations that hold to 0.06-0.09 px.
- A stationarity test alone is too sharp: the drone show's figure changes by 0.1 to 0.4 px over 600 frames on patches
  60-100 px across, its members jitter by 0.01-0.03 px against one another, and KPSS sees the change at p = 0.001.
  It is a change, and no rearrangement.
- ADF alone cannot say "keeps": a walk buried in ten times its step of jitter "returns" 63 to 95 % of the time
  (table below). So ADF only keeps a large, going wander that comes back from being called a wander.

**The published lines, as built** (drawn series with a trend added; 20,000 walks and white series a length, 4,000 of
each other; session 23's job 1219):

| frames (lags) | ADF: a walk "returns" (5 % stated) | ADF: white / AR(1) 0.6 / 0.8 returns | KPSS about a trend: white "keeps going" (5 % stated; at 1 %) | KPSS: AR(1) 0.6, at 5 % | KPSS: a walk keeps going | a walk under 10 x its step of jitter: ADF returns / KPSS goes |
|---|---|---|---|---|---|---|
| 60 (3) | 4.8 % | 75 / 33 / 14 % | 4.5 % (0.3 %) | 17 % | 71 % | 63 / 13 % |
| 100 (4) | 4.4 % | 95.5 / 65 / 29 % | 4.5 % (0.4 %) | 15 % | 82 % | 78 / 27 % |
| 150 (4) | 4.5 % | 100 / 95 / 63 % | 4.9 % (0.6 %) | 17 % | 92 % | 94 / 48 % |
| 300 (5) | 5.0 % | 100 / 100 / 99 % | 5.1 % (0.8 %) | 14 % | 98 % | 95 / 83 % |
| 600 (6) | 5.0 % | 100 / 100 / 100 % | 5.0 % (0.9 %) | 12.5 % | 99.8 % | 94 / 97 % |

With the lags chosen by AIC (as most packages do) ADF's 5 % ran at 13.6 % on 50 frames and 7.4 % on 150, so the lag is
fixed by the rule. A coloured jitter triples KPSS's rate against its table: hence the null drawn from the series' own
blocks.

**The lines, from the detector's own errors.** The biology survey (2026-11-01) planted 384 dots of known straight
paths in real frames of 12 clips (PR135, PR077, PR079, PR085, PR097, PR113, PR141, PR149, PR23, PR44, Galileo flyers 2
and 5), encoded them again with each clip's own settings and found them again with `forensics.source_candidates`; 277
were found on 60 frames in a row or more. Their errors (found less planted) have memory and slips: rms 0.16 px an axis
at the median, 0.58 at the 95th percentile, 1.05 at the 99th. Drawn: groups that keep their places under a shift, a
roll and a zoom, and rigid bodies turning up to 60 degrees in depth, each member carrying one dot's error series;
8,000 groups for each of 2, 3, 4, 5, 6 and 8 members and 60, 100, 150 and 180 frames (job 1220). The 99th percentile
of the largest pair's wander over its jitter:

| members | 60 | 100 | 150 | 180 frames |
|---|---|---|---|---|
| 2 | 2.22 | 2.21 | 2.10 | 2.79 |
| 3 | 2.53 | 2.36 | 2.44 | 2.45 |
| 4 | 2.69 | 2.50 | 2.55 | 2.86 |
| 5 | 2.75 | 2.58 | 2.84 | 3.00 |
| 6 | 2.90 | 2.62 | 3.05 | 3.11 |
| 8 | 2.98 | 2.76 | 3.27 | 3.26 |

Off rank 3 the same ratio's 99th percentile is 1.65 to 2.40, off rank 2 (four members) 2.32 to 2.97. With the pixel
floor as well, the largest pair is large in at most 0.4 % of such groups (eight members, 60 frames) and in none of
8,000 from 100 frames on; what is left off the rank in at most 0.08 %. Other jitters, the largest pair's 99th
percentile: white 1.04-1.18; AR(1) with a lag-1 correlation of 0.3 1.16-1.43, of 0.6 1.43-1.93, of 0.8 2.08-2.99;
pictures held two or three frames 1.19-1.76. Read at one frame's lag from the two members' own noise, as `rigidity`
reads it, the same groups reach 2.7 at the 95th percentile and 4.0 at the 99th (three members, 60 frames).

**The readings on drawn groups** (session 23's job on Harvard's cluster, 60409733: 100,480 groups, 320 for each of 314
kinds; 2, 3, 4, 5, 6 and 8 members; 60, 150 and 300 frames; 999 draws a reading, as in the stage).

*Groups that have not moved*: formations that keep their places under a shift, a roll of up to 20 degrees and a zoom of
up to 10 %, each place also changing steadily by about a pixel; and rigid bodies about 40 px across turning up to 60
degrees about a random axis, with a zoom and a pan.

| jitter | formations: "wander" | "keep their places" | formations and bodies of five or more: "several" | "one rigid body" |
|---|---|---|---|---|
| white, 0.3 px | 0 of 5,760 | 99.7 % | 0 of 5,760 | 100 % |
| AR(1), lag-1 correlation 0.3 | 0 of 5,760 | 99.7 % | 0 of 5,760 | 100 % |
| AR(1), 0.6 | 0 of 5,760 | 99.8 % | 0 of 5,760 | 100 % |
| AR(1), 0.8 | 0 of 5,760 | 99.9 % | 0 of 5,760 | 100 % |
| pictures held two or three frames (0.1 px a picture) | 0 of 5,760 | 99.9 % | 0 of 5,760 | 100 % |
| the planted dots' own errors (60 and 150 frames) | 0 of 3,840 | 99.8 % | 0 of 3,840 | 100 % |

So "wander" was called on none of 32,640 formations and "several" on none of 32,640 formations and bodies of five
members or more: under 0.01 % at 95 % confidence, where each of the three parts was set at 1 %. The rest of the formations (0.1-0.3 %) read "cannot
say". Two things the table does not hide. A rigid body that turns in depth changes its members' distances in the
picture, and `places` reads "wander" for 39 to 49 % of the turning bodies: so the stage adds to a wander that the
first reading did not call several "one rigid body that turns would change them so" (`places.one_body_not_ruled_out`),
and with fewer than five members it always does. And four members of a solid body that turns are not a flat body:
61 to 65 % of them read "cannot say (several, or one solid body turning)".

*Members that move on their own* (white jitter of 0.3 px; each member on a smooth path of its own, a walk in its
velocity, so many pixels rms about its place; or walking a white step every frame). Share called, at 60 / 150 / 300
frames:

| each member | "wander", 2 members | 3 | 6 | 8 | "several", 5 members | 6 | 8 |
|---|---|---|---|---|---|---|---|
| drifts 1 px | 2 / 2 / 2 % | 2 / 4 / 2 | 16 / 19 / 22 | 27 / 28 / 29 | 7 / 5 / 6 % | 3 / 4 / 4 | 0 / 0 / 1 |
| drifts 2 px | 23 / 32 / 32 | 31 / 39 / 45 | 85 / 93 / 93 | 97 / 100 / 100 | 47 / 61 / 64 | 70 / 81 / 74 | 88 / 92 / 91 |
| drifts 4 px | 53 / 66 / 73 | 65 / 84 / 85 | 99 / 100 / 100 | 100 / 100 / 100 | 65 / 85 / 93 | 80 / 96 / 98 | 93 / 96 / 98 |
| drifts 8 px | 59 / 87 / 89 | 87 / 97 / 98 | 100 / 100 / 100 | 100 / 100 / 100 | 65 / 91 / 97 | 82 / 96 / 99 | 89 / 98 / 98 |
| walks 0.1 px a frame | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 1 | 0 / 0 / 3 | 0 / 0 / 1 | 0 / 0 / 0 | 0 / 0 / 0 |
| walks 0.3 px a frame | 1 / 7 / 41 | 1 / 12 / 63 | 2 / 54 / 98 | 6 / 74 / 100 | 1 / 36 / 84 | 1 / 57 / 95 | 1 / 73 / 98 |
| walks 1 px a frame | 4 / 30 / 70 | 8 / 53 / 86 | 32 / 91 / 100 | 46 / 99 / 100 | 14 / 67 / 85 | 25 / 89 / 98 | 31 / 95 / 98 |

With the planted dots' errors in place of white jitter, members drifting 4 px read "wander" 87 % of the time at 60
frames and 94.5 % at 150, and "several" 79 and 92 %. The miss the other way: members that each drift 2 px are said to
keep their places 29 to 33 % of the time (all members and lengths), 4 px 7 to 9 %, 8 px 1 to 2 %. A drift of a pixel
is under the floor and is not called, by design.

**Today's rule on the same groups** (`rigidity`; 301,440 groups, the same job). Formations that keep their places read
`rigid` true 100 % of the time with white jitter and with a lag-1 correlation of 0.3, 53 % at 0.6, 1.4 % at 0.8, 9 %
with held pictures and 71 % with the planted dots' errors (92 % of groups of two, 46 to 52 % of groups of eight); the rest read
"neither", and "shuffling" 0.1 % (planted errors) or never. Bodies turning in depth read "shuffling" 8 to 14 % of the
time. Members drifting 4 px read "shuffling" 91 %, 8 px 99 %, 2 px 35 %. So the rule's "shuffling" is safe on
formations and its "rigid" is lost to a coloured jitter (B23's trap, and W1's before it): the call stands, and the
report's sentences still read it (IDEAS RG3).

**The controls** (what each is known to be; session 23's notes have every number).

| group | known to be | members, frames together | `rigid` (today's rule) | one rigid body or several | do they keep their places |
|---|---|---|---|---|---|
| PR135's flock, frames 1240-1392, the bird paper's six tracks | six birds | 6, 153 | false | **several**: 1.48 px left off rank 3 (the survey's 1.47), 3.7 times the jitter, at most 1 draw in 1,000 | **wander**: 8 of 15 separations, by up to 15.5 px, 3 to 17 times their jitter |
| the same, as the stage follows it | | 6, 91 | false | **several**: 1.21 px, 3.0 times | **wander**: 7 of 15, up to 13.6 px |
| the same, about one bird's track (three within reach) | | 3, 91 | false | cannot say: three members | wander: 3 of 3, up to 5.1 px (a rigid body turning not ruled out) |
| Svanström IR_BIRD_027 | birds, labelled | 4, 104 | false | cannot say: not one flat body (2.49 px, 12.9 times), so several or one solid body turning | wander: 4 of 6, up to 7.5 px |
| Svanström IR_BIRD_018, 035, 038, 044 | two birds each | 2; 132, 62, 206, 142 | false | cannot say: two members | wander: 2.7, 1.7, 3.9 and 2.3 px, 5 to 11 times the jitter |
| a drone show on the Galileo Project's infrared cameras: 20 groups of six neighbours in five windows of 241 to 600 frames on two cameras (tracks of 2026-10-19, a centroid reader of that analysis, not the stage's) | a formation flown by computer, its figure changing slowly | 6; 241-600 | true on 7, "neither" on 13 | **one rigid body** on all 20: 0.02 to 0.19 px left | **keep their places** on all 20: at most 0.09 to 0.45 px about a steady change |
| PR105's three points in a vertical line, frames 1075-2155 (session 19's reader; 444 frames with all three, not consecutive) | three unresolved points in a line that stays near the picture's vertical (measured 2026-11-09/10) | 3, 444 | "neither" | cannot say: three members | **keep their places**: at most 2.9 px, 1.5 to 1.9 times the jitter (the faint middle point jitters 1.4 px) |
| PR097 about its object 1, frames 3755-3880 (the stage on the video) | not settled: four points within 6 px, separate birds by their beats | 2, 62 | true | cannot say: two members | keep their places: at most 0.37 px, 1.1 times the jitter (a reading, not a control) |
| drawn: rigid bodies, formations, members that drift | by construction | 2-8; 60-300 | the paragraph above | the tables above | the tables above |

Not read, and why: AARO's two Puerto Rico lanterns (frames 1640-2231: one dark blob of two lobes, 0 points a frame), PR098's
two lines of two or three points (the points touch: one point a frame or none), PR105 as the stage follows it (the
lower points are too faint: one point, or two for 78 frames, which keep to 0.47 px), four of the eight Svanström
clips with two birds labelled (the second bird is out of reach or not a point), two clips of several labelled drones
(one point), PR097's dark objects 7 and 8 (one point a frame about each), PR47's three out-of-focus rings (they touch;
a reader written for them held three rings on 666 of 3,590 frames, in runs of 20 at most: not used). So no lantern group and no rigid row but PR105's has been read; and no
real object of several lights known to be one body (an aircraft at night) is among the controls. PR135's exercise
page, the one place its flock goes through this stage in a whole run, holds its answers with the readings in
(`tests/test_golden.py --exercises 04`: 16 checks pass).

**What it is not, and how it fails.**

- The rank can only say that the members are *not* one body. A group whose figure stretches or shears as a whole (a
  flock strung out along its course, turning together) is of rank 3 too: PR135's six leave only 1.2 to 1.5 px off rank
  3 while their separations wander by 9 to 15 px. The second half of Tomasi and Kanade's method, the metric that makes
  the motion matrices scaled rotations, would tell a stretch from a turn; it was tried and dropped, because a body that
  turns little does not fix the metric (drawn rigid bodies fail it as often as PR135 does). And a formation that holds
  station passes as one body: the words say "as the parts of one rigid body would".
- The affine camera is the far field. A body whose depth is not small against its range changes shape in the picture
  as it turns (perspective), by about its size in pixels times depth over range: 1 px for a 100-px body at a hundred
  times its depth. Near, large bodies can read "several" on a long, clean track. Not measured on a real one.
- A wander is told from jitter by being smooth. A member that takes a white step every frame (a random walk) has
  steps as large as its jitter reading (0.95 of a step at a lag of three frames) while its wander about a line over
  F frames is sqrt(F / 15) steps: a ratio of 0.27 sqrt(F), 3.3 at 150 frames, whatever the step. So white-step walks
  are not called wandering on tracks under a few hundred frames (the table's middle rows), and a smooth drift of a
  few pixels is. Recorded birds drift smoothly: PR135's pairs read 3 to 17 times their jitter.
- "Keep their places" is a bound, not a proof: nothing wandered about a steady change by more than PAIR_LINE times
  the jitter and a pixel. A steady change is allowed, so two members parting at a constant rate keep their places by
  this reading, as by `rigidity`'s; the pair's `separation_px` and the stage's figure show it.
- The lines are the package's detector on twelve clips' frames. Another detector's errors (a hand's marks; a member
  tracker of one's own, as on the drone show) are held only by the draws from the series' own blocks and the pixel.
- Members are read where the stage follows them as separate points. Two lobes that touch (AARO's two lanterns), points
  that merge (PR098's lines), or points too faint for the member detector (PR105's lower two) give no reading at all.
- A member lost and found again under another number is two short members; identities swapped where two members cross
  make both wander. The readings are no better than the following.
- 60 frames is the least, 8 members the most (the lines were drawn for 2 to 8), and the draws are seeded
  (TEST_SEED), so one group reads the same every time.
- Judgement left in it, said in the code: the lag rule and the block of l + 1; ADF's 5 % beside the others' 1 %; the
  pixel floor taken at the planted dots' 99th percentile; 60 frames; 8 members.

## 61. Body lengths against a sourced class table, a turn as a load factor, edge crossings set aside, and which unknown to ask for (Av11, Av10, A16, D8; added 2026-11-13)

The four additions ROADMAP 0.4 still listed for `kinematics`. Three are built, each a reading that needs none of k, R,
θ and v_own (or says what each is worth), and each with its NO POWER; the fourth was measured and set aside. None moves
a number an existing report gives: each reading is a new field with its own `power` and `why`, and adds nothing to the
stage's no-power list, which every report's count would then carry (as tau's reading does, section 33).

### 61.1 The class table (`class_envelopes.csv`, `envelopes.py`)

What known kinds of flying object do, one row a member of a class (a species, an aircraft type) or a rule, **each number
with the source it was read from beside it** (`envelopes.unsourced()` is empty, and the suite holds it so): 33 rows, twelve
classes and the wind's row. Birds in two sizes from radar and ornithodolite airspeeds (Alerstam et al. 2007, PLoS Biology 5:e197, Protocol
S1; Pennycuick, Åkesson & Hedenström 2013, J. R. Soc. Interface 10:20130419) with the RSPB's body lengths; airliners,
light aircraft, fighters and helicopters from type certificate data sheets (EASA's), the FAA Aircraft Characteristics
Database and the services' fact sheets; the US Department of Defense's five groups of unmanned aircraft, each as a
typical aircraft's size at the group's defining airspeed (the Army's 2010 roadmap, Table 2-2: under 100 knots, under 250,
under 250, any, any); two camera multirotors from their maker's manuals; balloons, which have no speed of their own; and
a strong jet stream's wind (NOAA: "more than 275 mph", 123 m/s), the most a tail wind is taken to add. Limit loads:
14 CFR 25.337(b) (2.5), 23.337(a) as it stood before 2017 (3.8 normal, 4.4 utility, 6.0 acrobatic), 27.337(a) (3.5), the
F-16 fact sheet's nine g, a camera multirotor's tilt limit (1 / cos 35° = 1.22: the flight controller's, not the
airframe's), and for small birds the largest measured, an Anna's hummingbird's dive ("nearly nine times", Clark 2009).

Four rules turn a source's figure into the table's, each on the cautious side for an exclusion. *An approach speed is
1.3 stall speeds* (14 CFR 97.3's definition of the approach category), so a type's least flying speed is its approach
speed over 1.3 (`STALL_OVER_APPROACH`; a transport's reference speed is 1.23 stall speeds, so this errs low). *A Mach
limit is taken at the speed of sound at sea level* (340.3 m/s), more than the type reaches at any height. *A bird's
speeds are its mean cruising airspeed less and plus two of its standard deviations*, and its length the low end of the
range given; birds dive faster than they cruise (the hummingbird's 27.3 m/s is 385 of its lengths a second, the row that
sets the small birds' top; a peregrine's stoop 31-39 m/s by radar, Alerstam 1987, is not in the table for want of a
length read from a source). *A row counts only for what it has*: the 737-800, 777-300ER and Embraer 175 give the
airliners their lengths and approach speeds, and no greatest speed, because none was read from a type certificate.

What a class's range is: its speed in body lengths a second from the least over its members of (least speed / length) to
the most of (greatest speed / length), length nose to tail. Airliners 0.8-7.4, light aircraft 3.0-10.8, fighters 2.9-45,
helicopters 0-5.7, the unmanned groups 13-57, 21-108, 9-38, 0-7.3 and 0-11, camera multirotors 0-55, large birds 8.7-52,
small birds 0-390, balloons 0 (they drift). Small fast bodies of every kind share the top of the scale: **the table is no
classifier**, and the readings below say which classes a number does not exclude.

Not verified, and so not in the table or marked in it: the greatest speeds of the three types above; the MQ-9's speed
(its current fact sheet gives none); an F/A-18's and a UH-60's limit loads; the Raven's and the Shadow's lengths and the
toy balloon's diameter are from secondary pages and say so in their rows; the af.mil and navy.mil fact sheets were read
as Internet Archive captures. The table's sources were gathered on 2026-11-13 by a web session whose every number came
with the sentence it was read in; a row is edited with its source, or not at all.

### 61.2 Speed in body lengths a second, as a lower bound (Av11; `envelopes.body_lengths`)

The rate in the picture over the object's length in the picture is its speed in its own lengths, free of k, R and the
field of view (section 5). **Which way it errs**: let the body have length L along its travel and speed v at the aspect
angle θ. The picture shows v sin θ, and the body's length along its travel as L sin θ; whatever else of the body shows
(wings, a rotor) can only make the largest extent larger. So

    rate / extent  <=  v sin θ / (L sin θ)  =  v / L,

a **lower bound** on the true speed in body lengths, exact where the body's own length is what shows longest (a slender
body at any aspect: the two foreshortenings cancel), and far under it for a body pointing nearly at the camera with its
wings across (0.08 of it at 5°, on the drawn bodies). It is not an upper bound at any aspect. Three conditions, each said
with the reading: the camera stood still (else the rate over the size is v_own / D for a body standing still, B7:
`stages.platform_of`, and the reading is NO POWER where it says the camera moved, or that the picture behind held still
on screen, which a camera following the object draws too); all of the object shows; and the length is the object's, not
the blur's. For an object `point_blur` finds no wider than a point the unit is blur widths, the sentence says the true
figure is higher if all of the object shows, and **no class is read from a blur** (H6).

*Against the classes* (`against_classes`). A lower bound excludes only from above. A class whose range holds the number
is `within`; one that flies faster in its own lengths is `faster` and not excluded (a body moving partly along the line of
sight reads slow); one the number is above gets the least tail wind that would carry one of its members to it, N L −
v_max (`with_wind`: the camera sees the speed over the ground, the table has speeds through the air); only where that
passes a strong jet stream's 123 m/s is the class `outside`. A balloon's row is then the wind it would need: N times its
diameter.

*The length.* The stage reads the bound from a length given (`--size-px`). Where none was given and the camera stage
measured the object's length at half its peak in place of the tracker's default spot (N5, `report.extent`), the report
makes the same reading from that (`Case.body_lengths`). It never takes the half-peak width, nor the default spot, and the
known aircraft below say why.

*Held to known answers.* The Galileo Project's aircraft (section 53: 209 single-camera clips, 22 types from a Cessna 172
to a 777-300ER, the type's length and the triangulated speed known; rebuilt from the session's saved table of rates and
sizes): with the camera stage's length the reading is 0.72 of the true speed over the true length (0.52-0.85, ten to
ninety in a hundred; 0.84 of the true figure across the line of sight), above the truth in 1 % of clips, and the
airliners are `within` on 209 of 209: no class was called outside (a one-sided 95 % bound on a false exclusion of 1.4 %).
With the half-peak width it is **not a bound**: above the truth in 75 % of 158 clips (in infrared the bright part of an
aircraft is smaller than the aircraft), and one aircraft's own class was called outside (an E135 at 15.5 a second for a
true 4.2). With the default 9-px spot it is above the truth in 22 %. The five Galileo flyers (known birds over a camera
that stands still, at a nominal 9 px): 2.2 to 16 a second, the birds never excluded. The labelled infrared set (section 44:
432 tracks of airplanes, birds, drones and helicopters with hand-labelled boxes) is filmed by a camera that follows its
objects, so the reading is NO POWER there; were that ignored, the rate over the box's longer side is 0.1 to 1 lengths a
second (a following camera reads low, the safe side for a lower bound) and no object's own kind is called outside, 0 of
432.

### 61.3 A turn as a load-factor curve (Av10; `envelopes.load_curve`, `figures.load_curve`)

A level turn at the rate Ω and the true airspeed V takes a load factor n = √(1 + (ΩV/g)²). The track gives Ω, the rate
its heading turns (not ω, the angular rate across the view: section 5), an angle in the picture and so free of k and R; it
does not give V. So the reading is a curve, and for
each class with a sourced limit load the fastest it could have flown the turn, V_max = g √(n_max² − 1) / Ω: at 1 rad/s a
body held to a transport's 2.5 g flew no faster than 22.5 m/s, 1.8 g at a bird's 15 m/s and 20 g at 200 (the aviation
survey's two). `could` is false where even the cautious V_max is under the class's least flying speed (it cannot fly
that slowly: the turn was not its); `binds` says whether the limit is reached inside the speeds the class flies at at
all; where a size gave body lengths a second (61.2), a body within the limit is no longer than V_max / N
(`length_max_m`), set beside the class's own lengths and left to the reader, the length in the picture carrying no error.

*The turn rate* (`turn_rate`). From a loop read whole (M4's ellipse, section 33): the ellipse's rate, the same in every
view, with its error from the nine-number fit under the track's own covariance (`against_wander` now returns
`omega_err_rad_per_s`); the cautious V_max is at 1.645 errors under it. From a bend: the heading the arc sweeps, 4 atan(2 s
/ L) for a sagitta s over a chord L (exact for a circle's arc), over the track's time. A short arc does not fix the
turn's plane: the picture's heading turns at cos i / (sin²φ + cos²i cos²φ) of the turn's own rate, so with the plane's
normal isotropic and the phase uniform the turn's own rate is **0.439 to 10.0 times the picture's** nine times in ten
(`TILT_RATE`; the same grid as `TILT_OWN`, recomputed by the suite), and the cautious V_max is at 0.439 of it. On 200
drawn arcs of 30° at random tilts the band held the true rate on 179.

*Conditions, each said*: a level turn (a pull-up or a dive adds or takes up to 1 g); the camera stood still and did not
turn; the speed is the true airspeed. **NO POWER** where `platform_of` says the camera moved, and where the picture
behind held still on screen (the camera may have turned, and its turn bends the track as the object's does: E3's and the
checklist's camera row's own no-power); where the camera held the object in view; where the track does not bend beyond
its scatter; and where it **swings about more than a bend does with no loop claimed**. That last is PR077's object 1, the
track that "loops through 705°": its ellipse is a back and forth 212 by 23 px that fails the minor-axis test, a sagitta is
a formula for a small bend and measures nothing on a path that doubles back, so the reading gives no turn rate there and
says so. That is the honest answer; a load factor from it would have been the camera's sway.

*Held to.* Drawn loops (420° tilted 40°: 0.800 rad/s for 0.800, the truth inside the error), drawn bends, and the one
recorded loop over a camera known to stand still, Galileo flyer 4 (a bird): 156° at 0.449 rad/s (0.29-0.61), 26° a
second, a circle in 14 s; at a bird's 15 m/s that is 1.2 g, inside what birds are measured to bear, and an airliner held
to 2.5 g could have flown it only below 77 m/s. The labelled infrared set (432 tracks; its camera follows its objects, so the reading
is NO POWER there) was read with that condition ignored on purpose, to see what the rule keeps out: a turn rate on 301
tracks (289 bends, 12 loops; 99 swing about, 32 do not bend), a median 0.7° a second for the airplanes, 4.8 for the
birds, 7.5 for the drones and 0.9 for the helicopters, at most 96; and no object's own kind "could not have flown it", 0
of 301. The cautious figure is what does it (a bend's speed limit is taken at 0.439 of the picture's rate), so the
reading errs toward saying nothing: a class is ruled out only by a turn far tighter than any in that set. The figure (`<tag>_load.png`, in the house style: both axes logarithmic,
the turn's curve red with its band, each class a bar at its limit across the speeds it flies at, named in a legend under
the plot) is drawn where the reading has power.

### 61.4 Edge crossings: tried and set aside (A16)

The idea (section 33's "not built"): an object leaving the frame has its brightness cut over the time its width takes to
cross the edge, so the crossing time times the track's rate is its length across the edge, independent of the tracker's
idea of its size. Measured before building it into a stage:

- *Drawn frames* (a slab of known length crossing the frame's edge at a known speed, blurred, summed over the exposure
  and the pixel, with noise; an error-function edge fitted to its summed brightness inside the frame; 61 cases). The
  crossing recovers the **blurred image's** extent across the edge, √(L²/12 + blur² + 1/12 + v²/12), not the body's: 1.09
  of it (median) where the crossing spans three frames or more, 9 % long because an error function is not a ramp's
  shape, with a stated error that is not honest at low noise (pulls +3.1); under a frame and a half across it fails
  (0.25); and a body of half a pixel reads the blur or does not fit. **A frame's edge is no different from a line drawn
  anywhere in the picture** (4.26 px against 4.20 on the same frames): the frame, a redaction box and an overlay all
  cut the picture after the lens has blurred it. The crossing is the image's own profile read slowly, which
  `report.extent` and the camera stage's length already read from single frames.
- *The census.* Of the 81 recorded tracks of the tether null (AARO's 45, the reference objects' 30, six goldens) none
  ends within 12 px of a frame edge; the four nearest (PR141 object 1 at 14 px, PR149 at 16, PR43 at 21, an AARO object
  at 22) move 8 to 21 px a frame outward, so their crossing is over within a frame or two. PR113's object crosses at
  142 px a frame. In the labelled infrared set 41 track ends on 39 of 432 tracks reach an edge (32 birds, 9 drones, a
  median 0.7 px a frame outward), 22 of them with the crossing recorded.

So no row: its conditions are met by no recorded PURSUE or AARO track, and where they are met it measures what the
report already has. What would be different is an edge *in the scene* (a mast, the horizon, a cloud's edge), which cuts
the light before the blur and so can show a body smaller than the blur; no recorded track has one, and the idea stays
open under that name. Not measured: the 22 recorded crossings of the labelled set, from their frames.

### 61.5 Which unknown to ask for: the value of information (D8; `kinematics.value_of_information`)

The ledger says which of the four a case lacks. This says which is worth asking for first: for a stated yes-or-no
question about the object's own speed (under 30 m/s? under the speed of sound?), the mutual information of the answer
with each missing unknown (Lindley 1956) -- how many bits of the question's uncertainty it would settle if a source gave
it, to a stated precision (10 % for k, R and v_own, 5° for θ) -- with the chance now and where it would lie once the
unknown was known. The object's own speed is |v_rel + v_own| with v_rel = hypot(ωR, Ṙ) and ω = v_px / k.

That needs a measure over what is not known, and M2 binds it (the same region is 31 % or 97 % subsonic by the choice of
measure alone). So it is computed under two named measures, 200,000 seeded draws each, cut to the region the speed cap
allows: *evenly* (the field of view over the ladder's 0.7-54°, the range, the range rate and the camera's speed each
uniform) and *invariant* (k, R and the camera's speed log-uniform, the directions isotropic). **An unknown is named first
only where both measures put it first**, each clear of the next by three of the draws' own errors (the bits recomputed on
five parts of the draws: numerical noise, not a finding); otherwise the row says the two disagree and ranks nothing. A
field of view that is a guess counts as missing. It ranks what to ask for. It says nothing of the object.

*Held to answers worked by hand.* One unknown: with ω 0.1 rad/s across the line of sight from a still camera and the
range between 10 m and 10 km, P(v < 30 m/s) is ln 30 / ln 1000 = 0.492 log-uniform and 290 / 9990 = 0.029 evenly (the
suite's draws: both to three figures), and the range settles all of it but the one bin the threshold falls in; with the
range known and the direction free, √(1 − (ωR/v₀)²) = 0.745 isotropic and 0.022 evenly. Two unknowns (k and R, no cap):
the bits of each against a one-dimensional quadrature, to 0.02 bits under both measures.

*In the report.* Under the table of the four unknowns: a paragraph that says what the table is and is not, one sentence a
question (which unknown would settle the most, with the share of the question's bits under the two measures; or that the
two disagree; or that one of them leaves nothing to settle), and the table itself, a row an unknown: the chance now, where
it would lie once known (5-95 % over what the unknown could be) and the share settled, under each measure. The case's
JSON carries it as `value_of_information`, as do `run --json` and `report --json`; `mcdonald kinematics` prints the
sentences and gives the field from what it was told.

*On the fourteen reference case files* (31 objects, their case files as they stand, read by this code). Thirty have all
four missing, and **their tables are one table, to the second figure, whatever the clip**: with nothing known the reading
is the measures' own. Under the speed of sound: 6.0 % of the even draws and 75-79 % of the invariant ones answer yes; the
camera's own speed would settle the most under both (0.015 of 0.33 bits, and 0.36-0.44 of about 0.8: "4 to 58 % of that
question"), the range next (0.008 and 0.07-0.10), and the angular scale and the aspect angle nothing by themselves (under
0.002 bits each: a field of view is worth nothing without a range to go with it). Under 30 m/s the even measure leaves a
chance under one in ten thousand, so nothing is left to settle there, while the invariant one gives 31-39 % and names the
camera's speed (0.41-0.58 bits): the two disagree, the sentence says so, and nothing is ranked. PR113, whose graticule
gives k, has the range first for the speed of sound under both (0.022 and 0.283 bits, the camera's speed 0.014 and 0.276).
Were the camera known to stand still (v_own = 0 given; PR135's and PR149's objects and PR113 worked through), the range
would lead both questions under both measures (0.59-0.82 bits of the invariant draws' question against at most 0.007 for
k or θ). So the reading's order, for a case with nothing known, is the camera's own speed, then the range, and a field of
view or an aspect angle only with those. It becomes a case's own where a stage bounds something. Whether a table that is
the measures' own wherever nothing is known earns its place in every report is the maintainer's to say.

*What it is not.* A probability of anything about the object: the chances are shares of draws under a named measure,
and the two measures give 6 % and 77 % for the same clip. The camera's own speed is drawn from standing still to the
speed cap, which is what makes it lead; a narrower prior for a known kind of platform would change the order, and none is
assumed. The precision an unknown is given to (10 %, 5°) and the two questions are stated choices, not thresholds.

## 62. Planted objects: what the search could have found (ROADMAP 0.6, objective 4; added 2026-11-13)

**What it is.** A search that lists what it found, and not what it could have found, reports no completeness. `mcdonald
plant` is the injection half of injection and recovery (Christiansen et al. 2013 for Kepler; Margot et al. 2021 made
the recovery rate the headline number of a radio search). It writes objects of known place, contrast, width, motion
and light into a stretch of a video's decoded frames, encodes the stretch again as the video is encoded, and writes a
truth table that says where every object is on every frame. Find, the link, `flicker` and `run` are then run on the
planted video as on any other, and what they make of it is held against the table (`plant.recovered`). The seed of
it is `planted` (section 13's encoding control), which is left as it was: the reference case files hold its numbers.

**A planted video is a test article, never footage.** Nothing else in this package writes detail that was not in
the record. So the file says what it is four ways: its name has `planted` in it; its container's comment begins
`mcdonald plant: a test video, not footage` and counts the objects written in; its truth table lies beside it; and
`clip.planted` is in every command's envelope and every case made from it, with a line above the report's
conclusion. The command refuses to write one beside the video it was made from, in the storage folder's videos or
anywhere in the reference-data folder.

**How an object is written in** (`plant.stamp`).
- *Into the luma plane, in the file's own codes.* The stretch is decoded to the planes the file holds (yuv420p), with
  no conversion; the object is added to the luma and the planes go to the encoder as they are. A contrast is asked in
  grey levels of the extracted frames (DN, what every stage reads) and divided by the stretch the extraction applies
  (255/219 on a studio-range video, section 50). The table gives three contrasts: the one asked; the one *written*
  (the median over the object's frames of the most any pixel was changed by: less than asked where the picture's
  floor or ceiling cut it); and the one left *after the encoder* (`contrast_after`: the planted video less the
  control at the object, the median over up to 8 of the frames it is seen on). The third is what Find was given. At
  a release video's few megabits a second it is close to the second; at a tenth of a megabit, a faint point is mostly
  quantised away (two copies written at 25 DN into a labelled infrared clip could not be seen in five frames of six),
  and a completeness read against the contrast written would blame the search for what the encoder did.
- *A point* is a Gaussian of a given sigma. *A body* is a disc of a given width with its rim blurred by the sigma; it
  hides what is behind it. With `exposure` either is drawn out along its own motion. The default is a sharp picture
  in every frame, which flatters a fast object: a real one is a dash wherever the shutter is open long (section 30).
- *It clips where the video clips*: at the highest and lowest luma codes the stretch's sampled frames reach, and at
  least the nominal white and black of its declared range. A dark object on a dark scene is cut at the floor, and the
  contrast written is then less than asked (PR113: 160 DN asked, 77 written on a scene at 95 codes).
- *Under the overlay.* Nothing is written where the stretch's static masks (`forensics.static_masks`) say symbology or a
  redaction block is; the table gives the hidden share on each frame. **Moving symbology is not in those masks**: a
  planted object is drawn over a scrolling tape's strokes, where a real object would pass under them.
- *Its light*: constant (the null for `flicker`); a steady beat; a beat whose frequency wanders (an Ornstein-Uhlenbeck
  walk: a wingbeat is not a clock); the twinkle of a point through turbulent air (a log-normal series whose spectrum
  is flat to a corner and falls as f^(-8/3) past it, through a detector's time constant: IDEAS.md W29); a strobe.
- *Its path*: a line at constant velocity on the screen; held still on the screen; a line with a drawn wander of a
  given size and memory (`kriging.simulate`, section 32's covariance with no jitter: the truth, not a measurement);
  a recorded track moved elsewhere in the frame (`place_recorded`: turned about the centre or moved whole, clear of
  the overlay and 80 px or more from the original), which carries the camera's own motion and the object's own
  irregular steps; or with the scene, which Find should not list.
- *Groups*: a formation (members keep their places) or a flock (each member its own beat and its own wander).
- *Each object's draws come from a generator of its own*, seeded by the seed and its number, so an object is the same
  whatever is planted after it. The crowding measurement below rests on that.

**The scene's own motion** is measured as the frames go by (`plant._Scene`: each frame registered to a reference frame
by `propose.onto`, the registration Find uses; the reference renewed every 15 frames or 24 px, because frame to
frame half a pixel reads as a quarter). Where an object is planted *with* the scene the shift is then finished by
least squares on the picture's own gradients (`flicker.lk_shift`, at half the resolution): a correlation peak alone
is good to about half a pixel a frame on a soft scene, and a bright point that jitters so about the scene is a faint
mover that Find lists (it did, on the drawn video; with the finish its steps scatter by 0.07 px and Find does not).
Every object's speed is given on the screen and against the scene. Find
lists what moves against the background, so completeness is tabulated by the second. Where the scene has too little
texture to register, or fits as well unshifted (PR135's sensor pattern, section 2), the scene reads as held still and
the two speeds are the same.

**How the stretch is encoded, and what that leaves unmatched.** All 144 PURSUE files were written by one encoder that
is not x264 (their streams are tagged `Elemental H.264`), and none carries its settings. What a decoder can read back
is repeated by libx264: the profile, the pixel format and declared levels, the exact frame rate, the number of
reference frames, the number of B frames between anchors, the bit rate *of this stretch* (its packets' sizes over its
length; a busy stretch of PR113 runs at 5.5 Mb/s in a file of 3.0), and an I frame forced wherever the video has one,
the stretch begun at the I frame at or before the first frame asked for. One encoder thread, so that one seed gives
one file, byte for byte (`planted`'s finding of 2026-10-17) -- with one build of libx264: the same seed on two
computers whose ffmpeg links two builds (the packaged `core 164 r3108` and one built from source) gave two different
files, the control too. The truth table names the build that wrote the file (`settings.encoder_build`).

**Not matched:** the first encoder itself (its motion search, its mode decisions, its rate control); the quantiser it
ran at (a second encode at the first one's bit rate runs gentler: the noise the first spent its bits on is gone); and
where the P and B frames fall between I frames, which this ffmpeg cannot force and which Elemental moves about (in
the pilot 55 % of PR144's frames got the picture type the video gives them, 72 % of PR113's, 90 % of PR135's, 97 % of
PR149's and 99 % of PR44's; a regular stream such as the drawn test's gets 100 %). The truth table records all of it
(`settings`: `types`, `types_made`, `types_same`, `bit_rate`, `bit_rate_made`, `not_recovered`). The control for all
three is the `_none` file: the same stretch through the same encoder with nothing planted. Every completeness number
is of a second-generation picture, and each video's table gives beside it what the second encode alone does to
Find's list.

**How a search is held against the table** (`plant.recovered`, `tools/plant_chain.py`).
- *Found*: a row of Find's list is on the object's path by `tools/find_rank.py`'s rule: over 70 % of the frames they
  share within 12 px, or a third of the row's own width if that is more, on two frames or more. Its place on the
  list, strength and score are kept; "shown" is a place among the first 30, what `look --propose --more` and the
  window give a person.
- *Followed*: the link from that row's own marks, as "This is it" runs it, covers half or more of the object's frames
  within 6 px of the truth.
- *Chance*: the planted paths held against the control's list, where they were not planted.
- *Other rows*: rows on no planted path. Each is on the control's list too (a feature of the scene, or clutter), or new.
- *The second encode alone*: the original stretch's list against the control's.
- *The beat*: `flicker` on the followed track of 60 frames or more. A beat called on a constant object is a false
  alarm; a planted beat is recovered where the beat called is within two resolutions of it (or of its double).
- Cells carry Wilson's 95 % interval (`plant.wilson`), which is honest at 0 of n and n of n.

**What a planted object can and cannot stand for.**
- It tests whether an object *like the ones drawn* would have been found *in these frames*. A grid of contrasts, widths
  and speeds is not the population of the sky; a completeness is a function of the cell, to be weighted by whatever
  population a question assumes.
- *It flatters Find where Find fails* (IDEAS.md B22: on 127 hand-labelled objects Find has 73 % where planted single
  dots said 77 %, but 58 % of members of several-object videos against 82 % alone, and 29 % of objects held still).
  So groups are planted as well as single points, objects held still and objects with the scene are planted as rows
  of their own, and wherever a video has a recorded track the real object's recovery is given beside its planted
  copy's.
- *A planted beat does not glide* (B13): a wandering beat is not a bird that stops flapping. The census's weight for
  birds comes from footage of known birds, not from this.
- *It sits on the real scene and its motion.* Planted in real frames a constant dot reads 1.9 times the amplitude near
  a beat's frequency that it reads on `planted`'s still background (B35: 0.54-2.42 over 8 videos). Every number here
  is from real frames in their own order; `planted.dots` is the still control and says so.
- It is a Gaussian or a disc. It has no wing, no shape that turns, no glint, no trail, and its position has no
  jitter but what the encoder and the detector give it (section 32's jitter on real objects is 8 times the bound;
  planted dots reach 2-3 times).
- It never passes through the first encoder, the display, the screen recording or the sensor. And it meets *one
  encoder more than it should*: an object's contrast in a release video is what its first encoder left of it, and a
  copy planted at that contrast is then encoded again. Where the bit rate is low this makes a planted copy fainter
  than the object it copies (read `contrast_after`).

**How it fails.** A scene too dark or too bright for the contrast asked (read `contrast_written`, not `contrast`). A
scene with no texture: every path is "against the scene" at its screen speed. A stretch that starts mid-GOP with no
I frame before it in reach (the stretch then begins on a forced I frame the video does not have there). A video whose
frame size is odd, which the encoder refuses (the command says so). Many objects at once: see the crowding
measurement, and keep to what it allows. A recorded path that cannot be placed clear of the overlay
(`path.frames_clear` says how much of it is).

**How many objects one planted video can hold** (measured 2026-11-13). Twelve probes, drawn first so that they are
the same objects in every run, with more and more fillers planted round them, on PR135 frames 1201-1480 (a sky, the
scene read as held still) and on PR149 frames 1-240 (the sea, a still camera). Each cell: probes on Find's list, among
its first 30 rows, followed over half their frames.

| in the frame at once | PR135 | PR149 |
|---|---|---|
| 12 (the probes alone) | 12, 12, 12 | 9, 8, 8 |
| 16 (12 fillers taking turns) | 12, 12, 12 | 9, 8, 8 |
| 24 | 12, 12, 12 | 9, 8, 8 |
| 48 | 10, 6, 9 | 9, 8, 7 |
| 70 (PR135), 107 (PR149) | 7, 6, 5 | 6, 5, 5 |
| 48, the fillers at 160 DN | 8, 6, 5 | 9, 7, 8 |

Up to 24 at once every probe fares as it does alone, though its score moves by up to a factor of four and its place
by a few rows (Find's score counts what else moves the same way; it keeps ten peaks a frame of each polarity). On the
sea three probes are not listed even alone and a fourth is row 268: the four that move 1 px a frame. So a draw keeps
to a few at a time (`plant.AT_ONCE`, 4; the pilot used 6 units, about a dozen points), no two nearer than 60 px
(`plant.APART`), and an object's place "among the rows shown" is counted with the other planted objects' rows set
aside (`rank_alone`).

**Two objects near each other are one row** (measured 2026-11-13, on the drawn video of `tests/test_plant.py`). A dark
point planted alone is Find's first row, on 68 of its 72 frames. Planted again with a bright point whose path
crosses it (a median 25 px apart, within 6 px for a few frames), it is not on the list at all: `propose.distinct`
folds a lower-scored row into a better one that runs within 30 px of it at the median, which is right for the dark
undershoot that trails a bright object and for pieces of one object, and cannot tell those from a second object. Two
bright points the same way leave the second as two short rows, before and after the crossing. This is the mechanism
the biology survey suspected behind B22's 58 % for members of groups, shown here on a pair whose only difference is
the neighbour. Find is not changed by this section; the finding is IDEAS.md's PL2.

**The pilot** (2026-11-13/14; `tools/plant_chain.py`, `tools/plant_tables.py`). Five videos chosen to span the
corpus -- PR113 frames 301-800 (a pan over terrain under a scrolling tape), PR149 1-500 (the sea, a still camera),
PR135 1201-1700 (the flock's stretch, 720p), PR44 3001-3500 (a long quiet video), PR144 99-598 (the camera follows its
object, the scene 15 px a frame) -- each planted ten times with 30 units (13 points, a body, one held still, 4 flocks,
3 formations, 2 steady beats, 3 birds, a twinkle, a strobe, one with the scene; 6 at once, 60 px apart, up to 90
frames each): 50 planted videos, 2,748 planted points. Each cell: found / planted, with Wilson's 95 % interval.

| kind | on Find's list | among the 30 rows shown | followed over half its frames |
|---|---|---|---|
| constant point | 365/650 = 56 % (52-60) | 54 % | 49 % (45-53) |
| body | 31/50 = 62 % (48-74) | 56 % | 46 % |
| steady beat | 51/100 = 51 % (41-61) | 49 % | 46 % |
| bird (a wandering beat on a wandering path) | 77/150 = 51 % (43-59) | 51 % | 47 % |
| strobe | 31/50 = 62 % (48-74) | 58 % | 58 % |
| member of a flock | 338/906 = 37 % (34-41) | 34 % | 28 % |
| member of a formation | 174/683 = 25 % (22-29) | 25 % | 22 % |
| held still on the screen | 5/50 = 10 % (4-21) | 10 % | 10 % |
| twinkle, with the scene | 2/50 = 4 % (1-13) | 0 % | 4 % |
| a feature of the scene | 0/50 = 0 % (0-7) | 0 % | 0 % |

A flock is listed (any member) in 66 % (59-72) of the 200 planted, as a row that says it holds two points or more in
34 %, with every member in 11 %; a formation 49 %, 27 % and 2 %.

| constant points moving 1 px a frame or more against the scene | on Find's list |
|---|---|
| 0-15 grey levels written | 11 % (6-20) |
| 15-30 | 51 % (41-60) |
| 30-60 | 73 % (65-81) |
| 60-120 | 96 % (90-98) |
| over 120 | 100 % (95-100) |

| constant points of 30 grey levels or more, by speed against the scene | on Find's list |
|---|---|
| under 0.3 px a frame | 40 % (22-61) |
| 0.3-1 | 53 % (42-63) |
| 1-3 | 81 % (71-88) |
| 3-10 | 94 % (87-98) |
| over 10 | 89 % (82-94) |

By video, the constant points on Find's list: PR113 35 % (27-43), PR149 52 % (44-61), PR135 68 % (59-75), PR44
60 % (51-68), PR144 66 % (58-74). PR113 is the hard one twice over: a third of its frame is overlay, and one global
registration does not find its pan (it reads 0.04 px a frame), so there "against the scene" is "on the screen".

Reliability: a planted path is "found" in the control, where nothing was planted, 5 times in 2,748 (at most 0.4 %).
`flicker` calls a beat on 1 of 369 followed constant points (0.3 %, at most 2 %) and on 1 of 26 strobes; a planted
beat 3-12 times a second and 15-60 % deep is called at its frequency on 143 of 286 followed tracks of 60 frames or
more (50 %, 44-56). The second encode alone, with nothing planted, keeps 14 to 22 of the original's first 30 rows and
16 of its 18 fair or strong rows; its weak tail mostly changes. The picture types the encoder gave were the video's
on 55 % (PR144) to 99 % (PR44) of the frames.

**A planted copy against the object it copies** (IDEAS.md B22; measured 2026-11-13/14 on the labelled infrared set of
section 44: every clip with several labelled objects and every fourth with one, a 150-frame window each; 126 clips,
185 hand-labelled objects). Each object's copy is a constant point of its contrast and width (`planted.look`), on its
own labelled path moved elsewhere in the frame. Find's rate, by `find_rank`'s rule, with Wilson's 95 % interval:

| | the labelled object | in the control (encoded again) | its planted copy |
|---|---|---|---|
| all 185 | 82 % (75-87) | 83 % (77-87) | 69 % (62-75) |
| the 107 copies placed clear and written at 0.8 of their contrast or more | 80 % (72-87) | 82 % | 74 % (65-81) |
| of those, under 0.5 px a frame against the scene (62) | 74 % (62-83) | | 60 % (47-71) |
| of those, 0.5 px a frame or more (45) | 89 % (77-95) | | 93 % (82-98) |

A second encode alone changes whether a labelled object is listed for 8 of 185 (4 %). What the table says: a copy
that could not be written whole is no copy (27 of 185 landed on a brighter patch than their objects and were cut at
the ceiling); a fair copy that moves is listed a little more often than its object, the biology survey's "planted
dots flatter Find" (it had 77 % planted against 73 % true); and a fair copy that crawls on a still scene is listed
less often than its object, because a constant point that barely moves changes nothing from frame to frame where a
real bird or drone flaps and turns, and because at these clips' tenth of a megabit a second the second encoder takes
most of a faint point away. So a completeness from constant points is too high for what moves, too low for what
crawls, and the object's own rate for neither. In this set "one of several" objects is listed as often as one alone
(82 and 81 %): its several objects are mostly not in the frame together, so it does not test the fold above; the
pilot's planted flocks do, and lose most of their members.

**What it costs.** A planted video of 500 frames with 30 units (about 55 points), through Find, the link and `flicker`:
about 1,200 CPU-seconds on merlin and 720 on arthur (the pilot; peak memory 2.9 GB at 1080p). Of that, Find is 41 %;
the planting with its two one-thread encodes 36 %; the frames and masks 6 %; the link and `flicker` 17 %. The
control's and the original's Find run once a stretch whatever the number of seeds; the whole `run` is 270 CPU-s an
object on merlin. So "thousands a video" is about 13 CPU-seconds a planted point on arthur: 2,000 points on each of
the 144 videos is of the order of 1,000 CPU-hours, a day or two of arthur, and Find on a graphics card (IDEAS.md G2)
would save at most two fifths of it.

### 62.1 The plants through `mcdonald batch`: the completeness table per video (ROADMAP 0.6, objective 4; added 2026-11-16)

**What it is.** The planted videos go through the batch as any video does, so that what the table says is what the
batch does on the catalog, rule for rule: Find in windows of 400 frames that overlap by 30; the batch's rule for an
object (section 54: seen on 40 frames or more in one window, background all round on 0.3 of them or more, not a
scrolling tape); the same object in two windows made one; each object followed from Find's own seeds. Three of the
batch's options are set for the plants, as section 54 provided for them: `--keep 400` (each window keeps 400 of Find's
rows, so that an object pushed down the list by the others planted beside it is still there to count: its place is
then taken with the other planted rows set aside, and held to the 30 the catalog keeps), `--only track,report` (each
object followed and reported, nothing more measured: this is a completeness of the search and the link) and `--most
40` (a stretch with fifty planted objects can have more lasting spots than the catalog's twelve). The controls -- each
stretch encoded again with nothing planted, and the stretch of the video itself -- go through a second batch with
`--most 0` (Find alone). `mcdonald plant --table PLANTED --control CONTROLS` then holds each planted video's folder
against its truth table (`plant.completeness`, `plant.recovered_batch`) and writes `plants.md`, `.tsv` (one row a
planted object) and `.json` into the planted batch's folder.

**What a planted object is held to**, each level a part of the one before:

- *on Find's list*: a row of some window's list lies on its path (the pilot's rule, `on_path`), among all 400 kept;
- *in the rows a window keeps*: that row's place, the rows above it that are other planted objects set aside, is
  among the first 30;
- *an object of the batch's rule*: such a row passes the rule (`batch.refusals`); on the catalog it would be a row of
  the table, measured or listed past the cap;
- *followed over half its frames*: the object's link, as the batch ran it, lies within 6 px of the planted object on
  half its frames or more (the pilot's rule). This is the headline, as the pilot's fork F4 chose.

Where a planted object is no object, the table says why: not listed, past the rows kept, or the rule's reasons for its
longest row ("brief", "edge"). The rule's two numbers are parameters of `batch.refusals` and `batch.long_lived` for this
alone; the batch runs with SEEN and ROUND as before. The control's objects by the same rule are the rows the batch
would give the stretch with nothing in it to find; a planted path on one of them is chance; an object of the planted
video on no planted path is held against them.

**The run** (2026-11-16, the code of main 133deba; arthur, 4 CPUs a video, no graphics card). Eight PURSUE videos
chosen to span the corpus (the pilot's five, PR051's long sky, PR088 at a quarter of a megabit a second, PR141 at
1472 x 828), one stretch of 1000 frames each (PR144: its 837), ten seeds each: 80 planted videos, 79,000 frames, 3,856
planted objects. Each draw is 28 units (24 on PR144) of the pilot's mix -- 11 constant points, 3 flocks, 3 formations,
3 birds, 2 steady beats, 2 bodies, one each held still, strobing, with the scene and twinkling -- up to 120 frames
each, 4 in the frame at once, the grids of section 62 (contrast 10-160 grey levels, sigma 1-4 px, 0.3-30 px a frame).

| video (frames) | planted | on Find's list | an object of the rule | followed | plain bright points that move: followed | the control's objects (of them the video's own) |
|---|---|---|---|---|---|---|
| PR051 (1-1000) | 481 | 24 % | 10 % | 8 % (6-11) | 6/20 | 0 |
| PR088 (1-1000) | 480 | 55 % | 28 % | 25 % (22-29) | 18/25 | 0 |
| PR113 (301-1300) | 488 | 31 % | 16 % | 15 % (12-18) | 21/36 | 0 |
| PR135 (661-1700) | 479 | 50 % | 27 % | 26 % (22-30) | 21/25 | 7 (6) |
| PR141 (1-1000) | 486 | 37 % | 16 % | 15 % (12-18) | 15/29 | 6 (4) |
| PR144 (1-837) | 452 | 49 % | 26 % | 24 % (20-28) | 34/48 | 5 (5) |
| PR149 (1-1000) | 492 | 38 % | 22 % | 21 % (18-25) | 24/35 | 5 (4) |
| PR44 (2978-4000) | 498 | 43 % | 23 % | 21 % (18-25) | 31/37 | 2 (2) |
| all | 3,856 | 41 % (39-42) | 21 % (19-22) | 19 % (18-21) | 170/255 = 67 % (61-72) | 25 in 7,900 frames (21) |

"Plain bright points that move" are the constant points written at 30 grey levels or more, moving half a pixel a frame
or more against the scene, on screen 80 frames or more: what a search should find. By kind over all eight, followed:
constant points 30 % (27-33), bodies 31 %, birds 28 %, strobes 21 %, steady beats 19 %, members of flocks 15 % and of
formations 16 % (a group has a member followed in 85 of 240 flocks and 81 of 240 formations), held still 2 %, with the
scene and twinkling 0 of 70 each. The constant points by contrast as written: 2 % under 15 grey levels, 13 % at
15-30, 31 % at 30-60, 58 % at 60-120, 52 % over 120. Those of 30 grey levels or more, by speed against the scene: 33 %
under 0.5 px a frame, 52 % at 0.5-2, 79 % at 2-5, 69 % at 5-20, and 13 % over 20, where an object crosses the frame
in fewer than 40 frames. Find lists constant points about as the pilot found (per video 26-67 %, the pilot's five
within 8 points of their pilot values).

**Where the batch loses them.** Of the 3,856: 2,281 (59 %) are on no row of Find's list in any window, even among
400; 90 are listed only past the 30 rows kept; 687 are listed and refused by the rule, 626 of them as seen on fewer
than 40 frames and 61 as edges; 798 are objects of the rule, of which 747 are followed and 51 are not. No object on a
planted path was past the run's cap. The brief ones are seen on 19 frames at the median, of the 41 their objects spent
on screen: Find sees a slow or faint object on some frames and not on others, and the rule counts the frames it was
seen on. Joining a planted object's rows within a window would not help: the frames of all of an object's kept rows in
one window together reach 40 for 3 more objects in 3,856. The loss is Find's own (section 3), then the rule's 40 frames.

**Where nothing was planted.** The controls give 25 objects in 7,900 frames (3.2 a thousand frames; 20 fair or
strong), and the videos' own stretches 26, of which 22 are objects of the controls too (21 of the controls' 25 are the
videos'). So the control's objects are the scenes' own lasting spots, kept through the second encode (PR135's flock,
PR149's sea, the moving camera of PR144), not rows the encode made: what the second encode alone does to the batch's
objects is 4 of the videos' 26 one way and 4 of the controls' 25 the other. Of the 3,856 planted paths, 14 lie on a row of a control's list by chance and 1 on an object
of the rule there. In the planted videos the rule makes 283 objects on no planted path: 185 are objects of the control
too; of the 98 others, 36 lie 12-30 px from a member of a planted flock or formation (a group listed as one spot between
its members, the fold of PL2) and 62 are near no planted object (0.8 a thousand frames).

**The rule at other settings** (measured, not changed; `batch.refusals` with its numbers given, over the same rows;
the catalog's rows from its own Find files of 2026-11-13/14, where today's rule gives its 1,715 to the object):

| the rule | planted objects taken (of 3,856) | plain bright points that move (of 255) | objects of the controls (7,900 frames) | rows of the catalog (144 videos, 881,996 frames) |
|---|---|---|---|---|
| seen on 10 frames | 1,254 (33 %) | 193 (76 %) | 43 | 3,854 |
| seen on 20 frames | 1,067 (28 %) | 183 (72 %) | 34 | 2,786 |
| seen on 30 frames | 888 (23 %) | 180 (71 %) | 27 | 2,181 |
| **seen on 40 frames (the batch's)** | **798 (21 %)** | **174 (68 %)** | **25** | **1,715** |
| seen on 60 frames | 587 (15 %) | 152 (60 %) | 16 | 1,168 |
| 40 frames from first to last sight | 910 (24 %) | 184 (72 %) | 27 | 2,386 |
| 60 frames from first to last sight | 793 (21 %) | 179 (70 %) | 21 | 1,705 |
| seen on 40, 12 rows a window kept | 795 (21 %) | 174 (68 %) | 24 | 1,572 |
| seen on 40, 400 rows a window kept | 799 (21 %) | 174 (68 %) | 27 | - |
| seen on 40, no background asked round it | 859 (22 %) | 176 (69 %) | 34 | 3,084 |
| seen on 40, background round half of it | 717 (19 %) | 160 (63 %) | 20 | 1,239 |

The rows a window keeps do not matter to the plants (12 to 400 take the same objects within 4). The 40 frames do:
halving them takes a third more planted objects, most of them faint points and members of groups (the plain bright
points that move gain 9 of 255), and puts 1,071 more rows in the catalog's table. The controls cannot set the number:
their objects are the videos' own, so a lower rule's extra objects in them are not false alarms by any test made here.
The maintainer kept the 40 frames on 2026-11-17 (IDEAS.md PL6).

**What `--card` changes here: nothing.** No stage of `--only track,report` computes on the graphics card (the card's
stages are `layers`, `integrity`, `flicker`'s camera shake and `tether`, section 52). The same two planted videos run in
one job given the card (`--slurm --card 2`) gave Find's files and all 19 followed tracks byte for byte, every case
`computed_on` none, and the same times within what neighbouring jobs move them (344 s against 336 s; 556 against 605);
the job held the card ten minutes for nothing. The card has a part with `--only track,flicker,report` (section 62.2).

**What it cost.** Planting: 60-214 s a 1000-frame video on 2 CPUs (5.2 CPU-hours for the 80; 2.7 GB at most at 1080p).
The batch: a planted video 171-657 s on 4 CPUs at the median by video, Find 83-314 s of it and the links the rest (up
to 40 objects; 2.3 GB at most); a control or a stretch of the video itself 77-368 s. In all about 51 CPU-hours as the
jobs held them (6 planting, 40 the planted batch, 4 the controls), 1 h 40 min of wall time on 36-48 of arthur's CPUs:
0.58 CPU-hours a planted 1000-frame video and 0.54 a stretch's two controls. One stretch of every PURSUE video with
three seeds would be about 330 CPU-hours (7 hours on 48 CPUs), with ten about 910.

**Found on the way: the frames read back.** `plant` reads back the frames each object is on, to say how much of its
contrast the second encode left (`contrast_after`) and to draw the truth table's picture. It asked ffmpeg for all of
them in one `select`, which ffmpeg refuses past about 100 terms; nothing came back, without a word. A 1000-frame
stretch asks for about 300: 2,892 of the run's 3,856 objects had no `contrast_after` and their pictures were blank. The
frames are now read 64 at a time (`plant.SELECT_MOST`, a test holds it); the 80 truth tables were read again with the
fix (the 964 values that existed came out the same, the originals kept as `*_truth.orig.json`).

### 62.2 The planted beats through the batch, and what the graphics card changes (ROADMAP 0.6, objective 4; added 2026-11-17)

**What it is.** The 80 planted videos of section 62.1 again, through `mcdonald batch --keep 400 --most 40 --only
track,flicker,report`: each object the batch makes is followed and `flicker` is measured on it, as the catalog's batch
measures it; the controls and the videos' own stretches the same way (`--most 40`), for beats where nothing was
planted. Find's files were taken from 62.1's run (a unit with no state takes a window whose file is there as searched;
Find depends on the video, `--window`, `--overlap` and `--keep`, not on the stages after it), so the objects are 62.1's
to the row: 798 objects of the rule, 747 followed. The maintainer kept the rule's 40 frames on 2026-11-17 (IDEAS.md
PL6). The run is on the CPU, the reference; the card is measured apart, below.

**How a beat is held** (`plant.beat_of`, `beat_right`, `beat_tables`). For each planted object the batch followed over
half its frames, `flicker`'s word on the object whose link lies on it most: a beat called (`beats` true: the object's
own), none, or "could not tell" (`beats` none; counted in the cell, not as called). A planted beat -- steady, or
wandering as a bird's -- is recovered where a line called lies within two resolutions of its frequency or of its
double, or the line's double within two of it (the pilot's rule, section 62). A beat called on a constant object
(points, bodies, the members of formations) is a false one; a strobe is counted apart. For a group the lines are its
members' that beat.

**What it found**, over all eight videos (`plants.md` of the run, the section "The beat"):

| light planted | followed and measured | a beat called | could not tell | at its frequency |
|---|---|---|---|---|
| constant | 473 | 3 (0.6 %, at most 2 %) | 61 | - |
| a steady beat | 30 | 18 (60 %, 42-75) | 8 | 18 (60 %, 42-75) |
| a beat that wanders (birds and flocks) | 227 | 128 (56 %, 50-63) | 38 | 125 (55 %, 49-61) |
| a strobe | 17 | 0 (0-18 %) | 4 | - |

No twinkle was followed (they move with the scene, and Find does not list them). The beating ones are recovered at
their frequency by depth: 37 % (27-49) at 0.15 of their brightness, 56 % (46-65) at 0.3, 74 % (63-82) at 0.6; by
frequency: 62 % under 6 Hz, 66 % at 6-9 Hz, 42 % (33-52) at 9-12 Hz, where a 30-frame video has fewer than three and a
half frames a cycle; by contrast as written: 39-48 % at 15-60 grey levels (and 2 of 2 under 15), 58-62 % above. By video, at their frequency:
PR141 35 %, PR135 45 %, PR44 48 %, PR144 56 %, PR051 61 %, PR113 64 %, PR149 65 %, PR088 71 %; a false beat on a
constant object 1 in 22 on PR051, 1 in 44 on PR113, 1 in 80 on PR135, none on the other five. The pilot, with `flicker`
run by hand on followed tracks of 60 frames or more, had 50 % (44-56) of its planted beats at their frequency and 1 false
beat in 369 constant points; through the batch, with its own links and every followed object measured, 56 % (50-62) and
3 in 473.

**Where nothing was planted.** `flicker` calls a beat on 4 of the controls' 27 measured objects (could not tell on 3)
and on 4 of the 26 of the videos' own stretches, and all 4 of the controls' beating objects beat in the stretch itself
too: PR135's flock (2) and two objects of PR44. So no beat here is made by the second encode; those beats are the
videos' own (PR135's are the bird paper's flock).

**What the card changes** (the two probe videos, PR135 seed 1 and PR44 seed 1, measured on the CPU and in one job given
the card, `--slurm --card 2`). With these options the card takes only `flicker`'s camera-shake pass, which runs for an
object that beats (the case says `computed_on` the card there, and nothing elsewhere). On the 16 objects of 32 that
beat, `flicker` took 6-30 s on the card against 16-79 s on 4 CPUs; on the 16 that did not, the same time. A unit took
407 s against 504 (PR135) and 372 s against 566 (PR44). Every track is the same byte for byte, every call the same,
every beat's frequency and amplitude the same, every report's conclusion the same. What moved is in two readings beside
the beat, the beat in the position (`position_beat`, section 59.1: 198 values) and the scene's shift (`scene_shift`: 112
values), each by at most 6e-5 of itself: the card's transforms are not the CPU's (section 52). Over the whole run
`flicker` was 10,233 s of the units' time, 6,292 s of it on the 203 objects that beat (29 s each at the median, 4.5 s on
the others): on the card that part would take about a third as long, which is about a seventh of the run's time.

**What it cost.** The 80 planted videos: 30.6 CPU-hours as the jobs held them (4 CPUs a video, 52-525 s a video at the
median by video, 2.9 GB at most), one hour of wall time on 36-44 of arthur's CPUs; the controls and stretches 2.3. Find
was not run again: in 62.1 it was 19.8 CPU-hours of these videos.

**Why the beats at 9-12 Hz are found less** (a reading of the saved cases, 2026-11-17; nothing changed). Planted
beats at 9-12.5 Hz are recovered at their frequency on 42 of 96 (44 %), against 101 of 157 (64 %) under 9 Hz, and no
single limit explains it. About a quarter is `flicker`'s top: it hears a beat up to 0.8 of the Nyquist frequency, 12 Hz
at 30 frames a second, but of the picture rate where it reads a cadence of held pictures, and on 9 objects of PR44 it
reads 14.2 pictures a second and stops at 5.7 Hz; 5 of the misses are refused for that alone. The draw gives a beat up
to 12 Hz and writes it on every frame, held or not, so on PR44 such a beat is one no real object there could show,
and the refusal is right. About half is the draw's mix: the beats drawn at 9-12.5 Hz are mostly members of flocks and
seldom deep (2 of 34 flocks at a depth of 0.6), and the rates under 9 Hz by depth and kind predict 54 % there,
against 45 % found inside the top. What remains is in flock members near another planted point (within 20 px: 3 of 21
at 9-12.5 Hz, 11 of 16 under 9 Hz), whose background apertures beat too, so that the floor they are held to is higher
(0.063 of their brightness against 0.038). The second encode does not take a fast beat away: read from the saved
curves, 0.8-0.94 of the planted amplitude reaches the curve at every frequency up to 14 Hz. No miss is a beat called at
an alias or a harmonic, and the misses are no shorter than the hits. The same draws recur across the eight videos
(an object's light is seeded by the seed and its number), so the 1,482 beating objects hold 780 distinct draws of
frequency and depth, and a cell is smaller than its count.

## 63. What the sensors' own backgrounds do: the corpus noise model, its tail, and a false discovery rate over the pass (ROADMAP 0.6, objective 6; S3, E24, D7; added 2026-11-15)

**What it answers.** The flicker stage holds an object's beat against the four background apertures beside it, each
read as if it were the object (`flicker.controls_judged`): the beat must stand ABOVE = 3 times their median strongest,
and its own drift and continuum nulls are drawn curves. Four apertures cannot say how strong a line noise alone makes,
and a drawn null of 2,000 curves cannot say a p under 1/2,001. `mcdonald noise` (`mcdonald.noisemodel`) reads every
background aperture of a whole pass instead -- the curves `mcdonald batch` (§54) leaves in each object's
`<tag>_flicker.csv` -- and gives three readings: a beat's strength as a centile of the backgrounds' at its frequency in
its stratum; a line's p past the corpus's largest, by a fitted tail; and a false discovery rate over the pass's objects.
**They are readings and tools: no call of the stage and no sentence of the report reads them.**

**The data, and its trap.** The model of record (`noise/` in the reference-data folder) is made from session 23's
catalog run of all 144 PURSUE videos (2026-11-13/14), whose flicker fields were made by abdc399 (main 3459561 + the
batch command): before the clip's own background was made the chance of windows apart (§13, N3's revision of
2026-11-13) and before §59's readings. The noise model reads only the background apertures' curves and the stage's own
`peak`, which did not change; the pass's calls (which rows are "Beats like a bird") are abdc399's, and N3's revision
can move a call that rests on windows apart, not one whose whole track passes. Of 786 objects, 602 have curves (88
were not followed; 96 stopped in `flicker` before its CSV is written: 54 lost against what is behind them on over a
tenth of their frames, 39 under 60 frames, 3 not brighter than their ring), in 94 videos; 7,064 background-aperture
columns, 6,654 of them read by the stage.

**The curves as the stage read them** (`as_judged`). Each curve over the stretch `flicker.judge` judged it on: each
track's span, the background apertures with their own member (or the member seen longest); where a track was lost, its
stretch trimmed to the frames either side and the lost frames filled across in its curve and in its apertures', which
go no further than it does; where the lost frames were the troughs of its own beat, the stretch recorded and nothing
filled; each background aperture in its object's brightness (`scale`). Which frames were lost is read from the fields,
not judged again from the CSV's values (rounded to 0.01). On the whole catalog every curve's `flicker.peak` gives back
the case's own `fields.curves[name]`: the frequency exactly, the amplitude to within 1.2e-5 of itself.

**The readings** (`reading`), with the stage's functions: the strongest line in the band and its amplitude as a share of
the brightness (`flicker.peak`); its ratio over a power law fitted to its own spectrum and that ratio's drawn null
(`flicker.continuum`, up to the stage's `top_hz`), and from them the **standing**, the ratio over the drawn null's 99th
centile (1 is the 1 % line, whatever the curve's length and continuum); the strongest amplitude in each half-hertz bin
from 1.5 Hz; and the same bins in each 2-s window of `noise_pdf`'s.

**What is dropped, by rule** (`dropped_because`, each from the stage's own numbers, none from a look at a spectrum):
the four apertures about a group's member seen longest (placed without regard to its fellows: a batch gives the stage
no tracks to avoid; each member's own four are placed clear of them and kept); an aperture where something reaches
flicker.DROP of the object's brightness on more than flicker.LOST_MAX of its frames (another object, the object's
glare, a bright part of the scene passing); and the apertures of a row followed onto another row's track (`same_as`:
the same apertures again). On the pass: 1,578, 360 and 402 dropped, 4,314 kept, 2,028 of them in the 66 videos with
objects outside the held-out third (65 with a kept aperture).

**What the corpus's background looks like** (`noise/noise_strength.png`). In the share of the object's brightness the
backgrounds' strongest line has a median of 2.2 %, and it falls with the object's contrast (its brightness over its
ring, a pixel): 4.2 % at contrast 3-10, 3.1 % at 10-30, 1.9 % from 30. The share is the scene's grey levels over the
object's brightness, so the model works in **grey levels a pixel of the aperture** (amplitude times contrast), where the
object's brightness is taken out. Even there the backgrounds of faint objects are quieter: 0.43 grey levels at the
median under contrast 20, 0.73 at 20-30, about 1.0 from 45 -- a faint object is found only where the scene is quiet.
Each video weighs the same (kept apertures a video: median 18, the most 217). Median and 99th centile at 2, 5, 8 and
11 Hz, at about 30 frames a second, over every length:

| contrast, aperture (videos) | median, grey levels | 99th centile |
|---|---|---|
| under 20, 4-px disc (13) | 0.49, 0.18, 0.16, 0.13 | 3.4, 2.4, 3.0, 1.6 |
| under 20, 6-px capped disc (16) | 0.59, 0.29, 0.24, 0.21 | 2.5, 1.8, 1.9, 1.1 |
| 20-40, 4-px disc (27) | 0.62, 0.22, 0.20, 0.16 | 2.5, 2.0, 1.6, 1.1 |
| 20-40, 6-px capped disc (27) | 0.69, 0.34, 0.25, 0.22 | 4.2, 2.3, 3.0, 2.0 |
| 20-40, wider disc (14) | 0.65, 0.25, 0.17, 0.20 | 14.3, 5.1, 1.6, 0.9 |
| 40 or more, 4-px disc (25) | 0.67, 0.43, 0.32, 0.28 | 7.2, 2.5, 3.0, 5.3 |
| 40 or more, 6-px capped disc (32) | 1.00, 0.50, 0.33, 0.28 | 6.0, 2.5, 2.9, 2.5 |
| 40 or more, wider disc (14) | 0.74, 0.25, 0.17, 0.20 | 17.4, 5.6, 7.5, 5.8 |

The background is red: three to four times as strong at 2 Hz as at 11 at the median. Its 99th centile is five to
twenty times its median, and the wide discs' at low frequency the most (the scene's own texture passing through a
large aperture). The pass's named beats lie over the 99th centile in most strata (the figure's red points).

**The strata** (fixed on the 66 videos outside the held-out third before any of its objects was read): the frame rate
(about 30 a second, 96 % of the objects, or another), the contrast (under 20, 20-40, 40 or more grey levels: the
controls harness's top edge and a round number below), the aperture (the stage's three kinds: 4-px disc, 6-px capped
disc, wider) and the length (60-149, 150-299, 300 or more frames: the harness's edges). Their measured effects on the
median in grey levels: contrast 2.3 times, aperture 1.6, length 1.25. A stratum of fewer than STRATUM_MIN_VIDEOS = 10
videos (a judgement, as the harness's STRATUM_MIN is) falls back, dropping length, then aperture, never contrast or
rate; the reading says which it used, and where none has ten, gives no centile and says so (26 of the pass's 1,655
beats, all in videos at another frame rate).

**A beat's centile** (`Model.centile`, `mcdonald noise --model`): its amplitude at its frequency's bin, in grey levels,
against the backgrounds' at that bin in its stratum, its own video's backgrounds left out: the mean over the reference
videos of each one's share under it, with a 95 % interval resampling the videos (E10). A beat the stage read in a 2-s
window is held against the backgrounds' windows. PR41's bird of the bird paper (its reference case file, 6.43 Hz, 11.6 %
by the paper's rule) is at the **97.3rd centile (92.0-100)** (`tests/test_noise.py` holds it).

**Its validation.**
- *Planted beats in real background curves* (`scripts/validate_planted.py` of the strand's folder): six apertures a
  video of the 61 videos with a reading, at 2.5, 4, 6, 8 and 11 Hz, planted at the stratum's own 50th, 90th and 99th
  centile (divided by the running mean's gain at that frequency, `flicker._gain`, so that they read at that level with
  no noise), read as the stage reads a curve, its own video left out: 1,594 plants a level. At the 90th they come back
  at the **90.9th** at the median (88.3-93.9 between the quartiles; 96 % within ten points); at the 99th, at the
  **99.3rd** (98.1-100); at the 50th, at the 65.9th (51-82), since a weak line's reading carries the grain under it (the
  read amplitude over the planted one is 1.37 at the median there, 1.00 at the 99th). The same at every frequency.
  Leaving the video's own backgrounds in moves a centile by under half a point at the median: the leak is small here,
  and the rule stands.
- *The labelled infrared set* (Svanström et al. 2021, 432 tracks from their saved curves and the stage's fields of
  record; another sensor, none of it in the model): the beats of the stage's own (`strong`) sit at the 99.5th centile
  at the median on birds, the 84th on airplanes, the 90th on drones and the 98th on helicopters. The centile ranks the
  birds' beats over most airplanes' and drones', not over helicopters'. The 30 named birds: 49.7 to 100, all but one at
  the 91.9th or more; the three non-birds named in the fields kept with the curves (HELICOPTER_024, HELICOPTER_043, and
  DRONE_059, which the stage no longer names since 2026-11-13, §44) at the 99.5th, 99.8th and 100th: what the floor and
  the stage's other tests decide is not what the centile says.
- *The reference case files* (31 objects, by the papers' rule): every named bird at the 92nd centile or more (PR079's
  92.2, the rest 96-100).

**The tail (E24).** The statistic is the standing squared, a line's power over its own continuum in units of the drawn
null's 1 % line: under Gaussian noise its tail is exponential (a generalised Pareto of shape 0), where the amplitude's
is lighter. Its rate at the 1 % line is flat across every stratum (1.2-1.5 %; the drawn null passes 1.28 % of the
backgrounds at 0.01, 5.4 % at 0.05, 10.7 % at 0.10: §39's correction holds on the corpus), so it is pooled. Up to a
threshold the p is the backgrounds' own share, (k + 1)/(n + 1); past it, the threshold's share times a generalised
Pareto fitted to the excesses (`tail_fit`, `tail_p`). **The threshold is chosen by a rule** (`threshold`): the lowest
of eleven candidate quantiles (80th to 99th) whose fitted shape lies inside the 95 % interval, over resampled videos, of
the shape at every higher candidate, and whose own interval holds every higher candidate's. On the 66 videos: the
**92.5th centile** (power 0.593, 153 of 2,028 above), shape **+0.107** (-0.049 to +0.278), scale 0.227; the largest
2.16. A positive shape: the sensors' backgrounds have a heavier tail than Gaussian noise.

The model is built on those 66 videos alone (`--only`). Made first with every video's backgrounds, a third of the
null was one held-out video (pr063's large groups, 1,410 of 4,314 kept apertures) and the fit's shape was +0.26; so the
held-out third's 2,286 backgrounds were held back to check the tail instead (decided before any object's p was read).
Checks (`scripts/validate_tail.py`):

| | p <= 0.10 | 0.05 | 0.01 | 0.001 |
|---|---|---|---|---|
| the 66's backgrounds, each video left out and the fit made again | 9.9 % | 5.1 % | 0.79 % (0.41-1.19 by video) | 0.20 % |
| the held-out third's backgrounds, never in the model (28 videos) | 9.8 % | 5.0 % | 1.31 % (0.84-2.24) | 0.17 % |
| the same without pr063 | 10.5 % | 6.2 % | 1.48 % (0.65-2.59) | 0.11 % |
| two halves of the 66, each fitted and the other tested | 8.7, 11.6 % | 4.0, 6.4 % | 0.72, 0.88 % | 0.09, 0.11 % |
| the labelled set's 1,556 backgrounds (another camera) | 13.7 % | 7.8 % | 1.74 % | 0.39 % |

Leaving one video out moves the shape between +0.049 and +0.122. The model's p carries to videos it never saw from the
same release; on another camera it runs about 1.5 times high (the labelled set's largest power is 2.51 against the
pass's 2.16): **the tail is the pass's sensors', and a model of another set is made from that set**.

**How far into the tail it can be trusted.** `p_cautious` takes the shape at the top of its interval, the scale at the
threshold held: the heaviest tail the backgrounds allow. Power 1.0: p 0.015, cautious 0.026; 2.0: 6.5e-4 and 4.5e-3;
**2.5, just past the corpus's largest: 1.9e-4 and 2.4e-3, ten times apart**; 5: 2.1e-6 and 2.8e-4; 10: 1e-8 and
2.9e-5; 20: 2.8e-11 and 2.6e-6. So the p is a measurement down to about one in 2,000 (the corpus's own count); it is
an extrapolation that holds within ten times to a power of about 2.5 (a line about 1.6 times the drawn null's 1 % line
in amplitude), and past that only its order is known. Of the held-out third's backgrounds, 4 lie past the model's
largest (0.17 %), where the point fit expects 0.05 % and the cautious fit 0.4 %: the truth lies between them. A line
of power 10 -- PR41's, PR099's and PR135's birds -- is past anything the corpus's backgrounds did by a p somewhere
between 1e-8 and 3e-5.

**The false discovery rate over the pass (D7)** (`pass_pvalues`, `fdr_over`, `bh`, `by`, `per_video`; `mcdonald noise
--fdr`). The unit is a row of the batch's table; a row's p is its members' smallest times their count (Bonferroni,
whatever their dependence). Each object's p is its whole stretch's power against the model, its own video's backgrounds
left out. Not the stage's continuum p, for three reasons: it is over the stretch the beat is reported from, often the
clearest of a track's 2-s windows, so the look across windows is unpaid; it cannot go under 1/2,001, and
Benjamini-Yekutieli over 602 rows asks for 0.05 k / (602 x 6.98), 3.6e-4 at k = 30 -- under that floor, so by the
drawn null alone Benjamini-Yekutieli keeps nothing at q 0.05 over the whole pass; and it assumes Gaussian noise, where
the corpus's tail is heavier. Both drawn-null p's are computed beside it, and the cautious p too. The held-out third
was looked at once, apart (`tools/sweep/looks.tsv`). Over the 66 videos (411 rows, 38 of them "Beats like a bird"):

| p | BH q 0.05 (bird rows) | BY q 0.05 | BH q 0.10 | BY q 0.10 | videos, q 0.05 / 0.10 |
|---|---|---|---|---|---|
| the model's | 44 (25) | 33 (20) | 54 (28) | 36 (21) | 8 / 9 |
| the cautious | 27 (18) | 11 (9) | 36 (21) | 15 (12) | 6 / 8 |
| the drawn null, whole stretch | 51 (28) | 31 (20) | 55 (28) | 31 (20) | 9 / 11 |
| the stage's own continuum p | 54 (29) | 28 (18) | 66 (32) | 30 (20) | 9 / 11 |

The bird rows Benjamini-Yekutieli keeps at q 0.05 on the model's p (20): PR073 object 3, PR085's 10, PR088's 5, 6, 10,
PR099's 6, 9, 10, PR135's 1 and 2 (the flock), PR41's 1-7, PR44's 6, 8, 9; Benjamini-Hochberg adds PR077's 2, PR088's 7,
PR092's 3, PR097's 7 and PR099's 12 (25), and at q 0.10 PR088's 3, PR097's 12 and PR44's 12 (28). On the cautious p,
Benjamini-Yekutieli keeps 9: PR099's 6 and 9, PR135's 1 and 2, PR41's 1, 2, 4, 5, PR44's 6. **Ten of the 38 bird rows
survive nothing even at q 0.10**: PR052's 6 (p 0.20), PR077's 6 (0.071), PR088's 4 (0.022) and 11 (0.050), PR097's 9
(0.064), PR099's 1 (0.083) and 3 (0.025), PR100's 5 (0.24), PR102's 1 (0.019), PR41's 8 (0.031). Each beats in some 2-s
windows, or passes the stage's whole-track test on its amplitude and drift, without one line over its whole stretch
that stands past the backgrounds': the stage's call rests on what this p does not see. The held-out third (191 rows of
28 videos, one bird row, PR152's object 9 at 5.04 Hz and 9.5 %, p 0.27): nothing survives, under any p, at either q,
per row or per video. Over all 94 videos the model's p keeps 40 rows (22 bird rows) by Benjamini-Hochberg and 31 (19)
by Benjamini-Yekutieli at q 0.05.

The 19 rows Benjamini-Hochberg keeps at q 0.05 that are not named a bird lie in PR085 (four, 7.1-7.5 Hz beside the
codec's 7.49-Hz line, not held to be the object's own), PR094 (one, 1.66 Hz), PR097 (three), PR135 (six of the flock's
other rows, 7.2-7.4 Hz, not held their own) and PR44 (five, 3.0-3.1 Hz, four of them its own and coming back, at
5.6-7.0 %: under BIRD_FLOOR). **The model's p says a line stands out of the sensors' noise. It does not say whose line
it is**: the codec's rhythm, a beat the background shares and the floor stay the stage's to judge, and a discovery
here is a line, not a bird.

**How it fails, and its traps.**
- *The pass's own calls are abdc399's*, and the model's backgrounds are that run's apertures: a model of another pass
  (another release, another rule's apertures) is made from it.
- *A background aperture can hold a real rhythm* the drop rules miss: a member of a group outside its own four, a
  feature of the scene that beats. Such an aperture fattens the tail; the tail checks bound how much (the held-out
  third's 1.31 % at 0.01).
- *One video can be the null.* pr063's large groups gave a third of all kept apertures; a centile weighs videos the
  same, but the pooled p does not, which is why the model is the 66 videos'. A model of a batch where one video
  dominates its own videos' apertures needs the same check.
- *The centile is of a selected line.* An object's beat is its strongest (or its clearest window's); the backgrounds'
  bin is the strongest in half a hertz: a beat that is the strongest of a wide band reads a few points high against
  them. The p pays the look across the band (the continuum's own); the centile does not.
- *A faint plant reads high* (the 50th's 65.9): the centile of a weak beat is an upper bound on its strength's.
- *The whole-track p misses what comes and goes.* A wingbeat that wanders, or flaps in bouts, has no one line over its
  stretch; ten of the pass's 38 bird rows are so. A window-level p with the look across windows paid (§13's ONCE_P,
  CHANCE_P) is the reading for them, and is not built here.
- *Frame rates other than about 30 a second* have no stratum of ten videos (seven videos of the pass): no centile.

**What it does not do.** It changes no call, no floor and no sentence. Whether a report quotes a beat's centile or its
p, and whether ABOVE or BIRD_FLOOR is held to the corpus's levels, is the maintainer's: the sentence proposed is in the
strand's notes. It reads no frame: a model of a pass needs that pass's CSVs, and the planting in real frames (§62) is
the completeness side of the same question.

## 64. The pass's objects held against known classes: defects first, then a tail probability per class (ROADMAP 0.6, objective 5; IDEAS T12, P9, Av14, D9; added 2026-11-15)

**What it is.** `mcdonald rank BATCH_DIR` (`mcdonald.rank`) reads a finished batch (section 54) and writes a list: every
object of every video on the same axes, the record's defects taken out first, and each remaining object held against
each labelled control class as a tail probability -- the share of that class's objects at least as far from the class's
middle as the object -- within the object's own stratum of quality, with the measurement that set it apart. It is model
criticism (IDEAS P9), not anomaly detection: no number here is a score for "anomaly", no object is called anomalous,
and nothing in a report changes. A small p-value says "unlike these labelled tracks, by this measure". A control class's
population is not the sky's, so it never says "unlike birds".

**Why the order matters (D9).** Unsupervised outlier scores rank bad records first: a track that slid off its spot, an
object on the display's overlay, a group read as one blend, a spot fixed on the sensor -- each is "unlike" everything,
for reasons that are the record's. So the defects come out before any ranking, each by a test the package already has,
and the classes are compared only within strata of quality.

**Rows to objects.** A batch row is a spot that lasted (section 54). A row followed onto another row's track
(`same_as`, `several.same_things`: within 2 px on 10 frames or more and on half the frames both have) is folded into
the row it is counted through. A group (`groups` found several points moving together) is one row whose members were
measured inside its case; it stays one object of the kind "group". The control classes are of single objects, so a
group has NO POWER against them (E5).

**The defects** (`rank.RULES`; the first that fires is the one listed):

| rule | the test | where its line comes from |
|---|---|---|
| not followed | the link found no track from Find's marks (the report: "No conclusion") | the batch's own state |
| failed | a stage stopped, or the case could not be read | the batch's own state |
| added | `integrity` FLAGs the object on any test but the overlay's (the report's row "added": Inconsistent) | section 9's verdicts |
| overlay | `integrity`'s layer-order test on the overlay FLAGs it | section 9 |
| blend | a group whose brightness `flicker` read in one aperture over its points | the stage's fields |
| sensor | the object's own track within 1 px of one place on half its frames or more, where the background moved (`forensics.on_the_sensor`'s test, FIXED = 0.5) | that test's own rule; a camera locked on the object to a pixel passes it too |
| scene | the report's own row: it does not move against the background (its rate there rounds to zero) | the checklist |
| masked | the track on the package's static masks of its case's own clip (`forensics.static_masks`: graphics, the burned-in symbology; blocks, redaction) on a quarter of its frames or more (`--masks`; 40 frames on an exact step, read in one ffmpeg pass a video through the package's PNG path) | **judgement**: the quarter |
| lost | the track sheet finds no compact spot under the track (contrast under 25 grey levels, `weak_frames`) on over half its detected frames (`verify`'s `frames` is the case's padded clip, so detected/frames is not this test) | **judgement**: the half |
| held | `flicker` refused because the pictures are held | the stage's no-power |
| looked | a look at the track strip (`--looked`: key, reason, who) found a record, not an object | a person's, or an agent's said so |

**The axes** (`rank.AXES`). Every measurement every object has, in fixed units; missing is missing, never zero. Three
kinds. *Scored* -- scale-free, and measured by the same code on the controls: the strongest line's amplitude in the
brightness and its frequency (`flicker`'s `beat` field keeps the strongest line whether or not it is called a beat), the
brightness's robust spread over its median, the brightness's frame-to-frame spread over that of the background
apertures beside it (both read from the case's `<tag>_flicker.csv`), the size's change along the track (`camera`'s
size trend, as a log ratio), the rate against the background in the object's own widths a second, and the spread of the
per-second rate against the background over its median. *Shown* -- in the table, kept out of the score: rates in pixels
a second (they carry the sensor's angular scale, k, which differs from camera to camera), the path's bend and a
straight line's miss on the screen (they carry the camera's motion), and the line's height over its slow wander (it
grows with the track's length, and the controls' tracks are short). *Quality* -- the object's width, its contrast, its
frames, the frame rate and the share of held pictures: the strata and E5's range.

**The controls on the same axes, by the same procedure.** The labelled infrared set's own table (section 44) is
`flicker` alone on the label boxes, and the boxes were made differently by class (key frames for birds and airplanes,
frame by frame for drones and helicopters: the set's README). So the known objects went through `mcdonald batch` itself,
with the very code that made the catalog: the 365 clips of the labelled set, the five Galileo flyers, and AARO's resolved
cases in the segments the blind run opened (section 46). Find on every frame, the 40-frame rule, Follow from Find's
marks, every stage of `run`. Each batch object was then matched to the known object it lies on (`rank.match`:
`same_things`' rule turned on the labelled box -- within the box plus 2 px on 10 frames or more and on half the frames
both have; of several pieces on one known object the longest stands for it). A control, like a corpus object, is
dropped from its class if it has a defect or is a group. So a class is "what Find found and Follow followed of that
kind of object", which is the population a corpus object was drawn through too. `tools/rank_controls.py` makes the
table; it says how many of each class were found (completeness on the controls).

**The p-value** (`rank.pvalues`, `against`, `pvalue`). Full conformal, Mondrian over strata. For an object and a class:
the class's objects in the object's stratum that have every scored axis the object has (where fewer than 19 have them
all, the axis the fewest have is let go, one at a time); each axis transformed (log where the axis is a ratio or a
rate); for the bag of those members and the object together, the median and the robust spread (1.4826 times the
median absolute deviation) of each axis; each one's score the largest |value - median| / spread over the axes;
p = (members scoring at least the object's + 1) / (n + 1). The strata are two, cut at the scored controls' median contrast
(157 grey levels): on the controls the brightness axes fall with contrast (Spearman -0.27 to -0.44, the drones' spread
over the background's) more than with width, as section 63's corpus model finds for a line's amplitude. Because the middle and the spread are taken from the bag
with the object in it, the score treats the object and the members alike, and for an object drawn like the class the
p-value is uniform on its steps of 1/(n+1); ties count against the object, so it errs high. The axis that gave the
object's largest distance is the measure that drove it (Av14), with its direction; the axis alone gives the same tail
(`axis_p`).

**NO POWER, with its reason** (E5): the object has no contrast (no stratum); fewer than 19 of the class's objects are in
its stratum (19 is the fewest for which p = 0.05 is possible at all); its width, contrast or frame rate lies outside the
class's range there, widened by a tenth at each end (**judgement**: so 29.97 frames a second is inside a class filmed at
30, and 24 is not); no scored measurement is shared; it is a group.

**The list.** Each object's largest p-value over the classes with power is the class it is least unlike; an object is
"unlike every class that could tell" at level a when that p is at most a. If the object belongs to any one of the
classes, that class's p-value is valid, so the largest is too (the intersection-union rule): the count at level a is a
count of objects each of which, were it of one of these classes, would come out so at most a of the time. The list is
ordered by that p, ties by the score's size. The corpus summary counts them raw, after Benjamini-Hochberg, and after
Benjamini-Yekutieli (any dependence), gives the share with a 95 % interval from a bootstrap over whole videos (E10: one
video's objects are not independent), and the counts by stratum, release and grade, where an excess among the faint and
small would be the record's quality, not the objects (D9).

**Calibration on held-out controls** (`rank.calibrate`). Each control object is held out with every object of its own
video and held against its own class (and every other class): the held-out p-values against its own class must be
uniform. The same held-out p-values against the other classes say how well the axes tell the classes apart.

**A check on known objects outside the classes** (`rank.checks`). AARO's resolved objects (balloons, birds, lanterns,
aircraft, one wind-borne object) and the Galileo flyers (birds on another camera) are not classes -- each kind has far
fewer than 19 objects -- but known, ordinary objects held against the four classes exactly as a corpus object is. How
often one comes out unlike every class is the list's false-alarm rate on objects of a kind the classes do not hold.

**Measured on the catalog run** (2026-11-15; the catalog of section 54, made by abdc399; the controls through the same
snapshot; the rank strand's notes have every job). The labelled set's 365 clips through `mcdonald batch`: 366 objects,
309 of its 432 labelled objects found and followed -- airplanes 46 of 82 (56 %), birds 83 of 125 (66 %), drones 150 of
168 (89 %), helicopters 30 of 57 (53 %) -- and 57 batch objects on no labelled object. Of the 309, integrity flags 12
as "added" (3.9 %, the rule's false alarms on known objects) and the report says one does not move against the
background; ten are groups; the static masks take none. Usable: drones 144, birds 68, airplanes 45, helicopters 30.
Their quality is narrow: width median 5 px (helicopters to 15), contrast 80-220 grey levels (drones 151-169), every clip
30 frames a second and 90-320 frames long; almost none has a rate against the background (sky behind: 15 of 287), so
those two axes are let go against every class. The flyers: 5 of 5 found, two flagged "added"; at 60 frames a second
they are outside every class's frame rate, so they check nothing.

*Calibration*: held out with its video, each class's p-values against itself: at or under 0.05 / 0.10 / 0.50 --
airplanes 6.5 / 9.7 / 48 % of 31, birds 6.4 / 14.9 / 51 % of 47, drones 4.9 / 9.7 / 51 % of 144, helicopters 5.6 /
11.1 / 44 % of 18 (the largest gap from uniform 0.01-0.10). Against the other classes at 0.05: birds unlike drones
57 % of 51, unlike helicopters 11 %, unlike airplanes 0 % of 18; drones unlike birds 5 % of 130; airplanes unlike drones
13 %, unlike birds 10 %; helicopters unlike birds 21 % of 14, drones 20 % of 20, airplanes 12 % of 16. So the axes tell a
bird from a drone and little else: these classes differ in the brightness of short, small clips by little.

*Rows to objects and defects*: 786 rows, 90 folded by `same_as`, 696 objects (603 single, 93 groups). Defects, the
first rule each: not followed 88, lost 16, overlay 8, sensor 7 (PR29 #1 and #2, PR092 #10, PR066 #2-#5), added 6,
masked 4 (PR42 #12 and PR134 #10 the overlay's "N", PR092 #11 onto the reticle's centre, PR059 #3 beside overlay text:
all four right by the strip) -- 129. The track sheet's weak shares, the "lost" rule's reading: 95 % of tracks under
0.25, then 13 in 0.25-0.5, 5 in 0.5-0.75, 12 above; a cut at 0.75 would take 5 fewer.

*Strata, compared* (the catalog's 481 single objects without a defect; the decision rests on the controls'
calibration and on how many objects keep power, and the count at 0.05 moves little):

| scheme | objects with power | unlike every class at 0.05 | held-out at 0.05 (air, bird, drone, heli) |
|---|---:|---:|---|
| no strata, range contrast and fps | 437 | 7 | 0.05, 0.07, 0.06, 0.03 |
| no strata, range contrast, fps and width | 367 | 5 | 0.05, 0.08, 0.06, 0.04 |
| width in two (at 5 px), range contrast and fps | 177 | 8 | 0.05, 0.08, 0.05, none |
| **contrast in two (at 157), range width, contrast and fps** | **312** | **5** | **0.06, 0.06, 0.05, 0.05** |
| contrast in three, range all three | 312 | 5 | 0.07, 0.09, 0.05, none |
| width in three, range contrast and fps | 170 | 2 | 0.04, 0.06, 0.05, none |

(These counts are from before the two conditional axes; the chosen scheme's own numbers follow.)

*The list* (rank_v3, the package's rules alone): 305 objects have a p-value against at least one class; 90 groups and
172 single objects have none -- for 159 of those 172, being wider than a class's range at its contrast is one of
the reasons, and in the faint stratum airplanes (13) and helicopters (8) are too few. Against how many classes an object
has power: none 172, one 150, two 121, three 23, all four 11. The class least unlike: birds 243, helicopters 31,
drones 24, airplanes 7. At 0.05, **18 of 305 are unlike every class that could tell (5.9 %; 3.3-8.7 % when whole videos
are drawn again)**; at 0.10, 26 (8.5 %; 5.2-12.1). **None survives Benjamini-Hochberg or Benjamini-Yekutieli at 0.05 or
0.10**: with n near 43 in a class's stratum the smallest p-value is about 0.02, under the 0.05/305 the first rank needs.
The measure that drove the 18: the brightness's spread 6, its frame-to-frame spread over the background's 4, the line's
amplitude 4, the size's change 4. By stratum, 14 of 258 faint and 4 of 47 bright; by grade 18 of 298 "Low" and 0 of 7
"Very low"; by release 4 of 47 (01), 10 of 165 (02), 1 of 19 (04), 1 of 15 (05), 2 of 59 (06). The held-out third
(tools/sweep/holdout.tsv, counted apart): 2 of 87 objects in 25 videos, against 16 of 218 in the other 50. It is not a
blind test of this section's choices: the strata and the two conditional axes were chosen with the whole catalog in
view (tools/sweep/looks.tsv has the line).

*A look at the top twenty* (an agent's, from the track strips and the frames with the track drawn). Seven of the
twenty are records, not objects, which no rule of the package caught: the overlay's "N" of the north pointer (PR061 #9
and #10), the north pointer's triangle (PR084 #12), a faint spot whose track then slides onto the overlay's corner bracket
(PR092 #8 and #4), a track that starts on a black redaction block (PR099 #7, PR096 #6). Integrity's overlay test has no
power where the object is the overlay ("the object never crosses the symbology"), and the static masks miss them too
(PR092's clip has no graphics mask at all; PR099's block is not dark on 95 % of the sampled frames; the north pointer
moves). With those seven set aside as looked (`--looked`, rank_v4): **12 of 298 unlike every class that could tell at
0.05 (4.0 %; 1.9-6.3 %)**, 19 at 0.10, none after either correction. What the rest of the top twenty most likely are:
steady bright lights on a featureless sky (PR133 #6, #2, #3, probably one light in three stretches), a dark spot over the
sea's waves (PR148 #10) and over clouds (PR081 #6), a bright point in a picture crossed by bands of analog noise (PR051
#1, its strong rhythm likely the bands), the bird paper's PR44 bird (#6, #8: its beat is stronger than any labelled
helicopter's, drone's or airplane's, and the labelled birds of its contrast are too few to compare), a known non-bird
control of the harness (PR055 #6), a bright ground feature in a redacted ground scene (PR22 #5), a many-lobed bright shape
crossing the sea fast (PR100 #2: several points the group test did not split, or a resolved body), dark spots in heavy
compression blocks (PR060 #11 and #5), two points moving side by side read as one spot (PR49 #11), a body that grows and
changes shape (PR051 #11). None is a class the controls hold that lies outside their range in a way a person would call
strange; most are known kinds outside the controls (lights, ground features, objects over the sea) or the record's.

*A check on known objects of other kinds* (`rank.checks`). AARO's resolved segments through `mcdonald batch` with the
same code: 53 batch objects, 28 of the blind run's 51 tracks "on the object" matched -- aircraft 5 of 6, balloons 20 of 36
(the balloons of PR-004, PR-005, PR-006 and PR-010, each in several stretches, of PR-009 and the foil balloon; Al
Taqaddum's and Mt. Etna's none), birds 1 of 2, the weak cases 2 of 4, the lanterns and the wind-borne object none -- and 25 objects on no
described object. Five matched are defects (overlay 2, added 2, masked 1). With the flyers, 22 known objects of other
kinds are usable; 12 of them have no class with power (wider than every class at their contrast, or at 60 frames a
second), and **none of the 10 that have one -- eight balloon tracks of four balloons and two aircraft tracks (Western
United States) -- comes out unlike every class at 0.05**: their largest p-values run from 0.23 to 0.89. It is a small
check (four balloons), and it says the list does not put an ordinary balloon or airliner at its top where the classes
can speak; where they cannot, it says nothing.

**How it fails, and its traps.**

- *It finds the record before the object.* The look found seven defects in twenty that no test caught; the rules are
  a floor, not a filter. A person's look at the strip comes before any reading of a row, and `--looked` records it.
- *The controls are narrow.* Small, bright objects in ten-second clips at 30 frames a second, from a ground camera that
  follows them. Most PURSUE objects are wider or fainter: 172 of 477 single objects have no class with power, and most of
  the rest only birds. "Unlike every class that could tell" is often "unlike the labelled birds". A wider set of labelled
  controls (aircraft and balloons in airborne infrared at the corpus's widths) is what would give the list power.
- *A class's tracks are not the sky's.* The bird paper's PR44 bird beats more strongly than any labelled bird of the
  short clips, and the labelled birds' strongest line is mostly noise. A small p-value against a class says the object
  is unlike these labelled tracks by one measure.
- *Few objects per class make coarse p-values.* About 1/44 in the faint stratum: no correction for 300 objects can keep
  anything. The summary says so rather than lowering the bar.
- *The scores track quality* (D9): the counts by stratum, grade and release are printed beside the list; here they show
  no excess among the faint (14 of 258 against 4 of 47 bright).
- *Conformal validity is exchangeability.* A corpus object is never exchangeable with the controls in every respect (a
  different camera, platform and code path to its track); the p-value is valid only for an object drawn as the class's
  objects were. E5's range and the strata keep the comparison inside the controls' own conditions, not more.
- *The held-out third was seen.* The choices of this section were made with it in view.
- *What is judgement* (decisions for the maintainer): the quarter of the masked rule, the half of the lost rule, the
  tenth of E5's margin, the two strata and their cut at the median, the largest-distance score (one far-out axis) over a
  sum of squares (several moderately far).

**What it costs.** The catalog's records: 3 s (one CPU). The static masks: one task a video, 2 CPUs, about 2 GB at
1080p, seconds to a minute a video. The labelled set through `mcdonald batch`: 365 clips at 30-60 s each on 4 CPUs (peak
0.76 GB), about 25 minutes as 16 at a time. AARO's 17 segments: about ten minutes an object at 1080p (PR-004's ten objects 71 minutes), peak about 4 GB.
The ranking itself: seconds.

## 65. The background as a dense field: where each layer is, and how its motion changes across one (ROADMAP 0.6, objective 3; IDEAS A14; added 2026-11-16)

**What it answers.** Where in the picture each layer of the background is, and how the motion of a layer changes
across the picture. Section 1's `layers` places 128-px templates every 96 px: on a 1080p frame about 80, enough for a
consensus or two (the motion groups), not for a map. `mcdonald layers --dense [N]` (`mcdonald.dense`) places the same
templates every 16 px on N pairs (default 24) of the pairs `layers` found moving with a consensus: about 36 times as
many, a third of a second a 1080p pair on the graphics card (about 45 CPU cores' worth). It is the work the card was
for (ROADMAP 0.6, objective 3: "the dense fields").

**It is a reading, and changes nothing else.** The dense field has its own cache (`bg_dense_*.npz` beside the frames),
its own files (`<tag>_dense.csv`, a row a pair; `<tag>_dense_map.csv`, a row a kept template with its layer;
`<tag>_dense.png`) and its own entry in the fields (`dense`) and the result ("dense field"). Every other number, line
and file of `layers` is the same with it or without it, to the byte (test_measurement holds this). No other stage and no
report reads it; `run` does not ask for it.

**The design** is the maintainer's (2026-11-16), from the measurements of 2026-11-15 (the session's A14 strand, probes
on PR135, PR113, PR051 and PR144, 4-5 pairs each):

1. *What for, first:* the background's layers, and the parallax between and within them. The other uses measured
   gave nothing to stand on: the ring about a small object that `mcdonald comotion` reads only fits templates of 32 px, and a
   fifth to a half of an empty pair's 32-px templates pass the keep rule; the scene behind a sensor's fixed pattern
   (section 41) was read by no size or stride better than chance on PR135.
2. *Templates of 128 px every 16 px.* The keep rule stays honest at 128 px (no false keeps on PR144, PR135 or across
   clips; 1-5 % on the half-turn of clips with a sensor pattern). At 64 px 1-22 % of an empty pair's templates pass,
   at 32 px 19-46 %. Every 8 px would cost four times as much for templates that overlap seven-eighths.
3. *Which matches count:* the keep rule of `forensics.good` (a peak of 0.5 or more, 0.05 or more above the runner-up),
   with each clip held against two empty pairs and the peak floor raised where they keep more than 1 % of their
   templates. At an equal false-keep rate a raised peak floor kept the most real matches of the masks measured (a gap
   floor, a texture floor, an information floor, forward-backward agreement): forward-backward agreement lost half the
   real rows at 128 px.

**A pair.** Pairs are taken evenly over those `layers` read as MOVED with a consensus (`how`, `lay`): held, unmoved,
lost or unread pairs have no motion to map. The search reaches 24 px (`MARGIN`) past the faster of the pair's groups
(`layers_of`'s consensus plus its group gap), never past `layers`' own reach; the masks are `layers`' own, the tracked
object's disc among them. The zone of +-4 px about zero is left out, as in `layers`' first pass.

**The two empty pairs and the floor** (`floor_of`). Each pair's first frame is matched, with the same templates, masks
and reach, against two frames that cannot hold its scene:
- *its second frame turned half a turn* (rows and columns reversed): the same texture and the same sensor, nothing in
  its place. Where the sensor has a fixed pattern (stripes) the turned pattern matches itself away from zero, which a
  real pair cannot do; this empty pair over-counts there, and so is the stricter of the two on such clips;
- *a frame of another clip*: with `--null-from VIDEO`, that video's middle frame (masked by its own static masks, cut to
  the clip's size about its middle); without, the clip's second frame with its phases drawn at random (`scrambled`:
  the same power at every scale of detail and every direction, nothing where it was, none of the sensor's pattern in
  place; masked pixels set to the rest's median first; seeded by the pair's first frame). The scrambled frame stands
  for another clip so that one clip can be measured alone (a person with one video). On the reference clips neither it
  nor another clip's frame came near binding (the table below).
The floor is the lowest of 0.50, 0.51, ..., 0.99 at which neither empty pair, its templates over all the clip's pairs
together, keeps more than 1 % (`NULL_SHARE`). Where none does, nothing of the clip's dense field is read, and it says so.

**Layers and the map** (`pair_layers`, `grow`). A layer is the largest group of kept rows whose shifts follow one
motion that changes evenly across the picture (an affine field: a shift and its rate of change across and down). It is
seeded by `forensics.consensus` (`layers_of`'s tolerances, 6 px across and 2.5 px down over k frames), then fitted,
and its rows found again within the tolerances of the fitted motion, until they stop changing (at most six rounds). A
second layer is sought among the rest the same way. A layer needs 288 rows (`MIN_ROWS`): at a stride of 16 px a
picture holds 36 rows where `layers` places one, and 8 templates make a consensus there. A second layer is one only
where its motion is 12 px or more over k frames from the first's where it lies (`layers_of`'s rule, twice the
tolerance). Which of the two has more rows can change from pair to pair as the picture moves; which moves faster on the
screen does not while the parallax keeps its sign, so the summary names them the faster and the slower. The map
(`<tag>_dense_map.csv`) gives every kept template its layer: 1 the larger, 2 the smaller, 0 neither. That each layer
lies in a part of the picture of its own is measured by its neighbours (`neighbours`): of the rows next to each other on
the grid, both in a layer, the share in the same one, against the share chance gives (each layer's share squared, summed).

**The change across a layer** (`fit`, `parts`). The affine fit's rate of change, a 2 x 2 matrix in px over k frames per
100 px, is given in the four parts it is made of (Koenderink and van Doorn 1976): the spreading (the divergence: a
zoom, or a surface coming nearer), the turning (the curl: a roll of the camera), and the stretching with its axis (the
deformation: what a surface whose range changes across the picture gives as the camera moves past it). These are
readings of the field, not of the camera: a roll and a tilted surface can both turn and stretch it, and nothing here
tells them apart. Where there are two layers, each one's motion is fitted again on its rows whose templates reach no
row of the other layer (half a template, 64 px, across or down: `_inside`): a template that straddles the line between
them reads a blend. On a drawn shear of 15 px/s per 100 px beside a second layer the straddling rows read it 3.5 % low
(14.47); without them, 15.00.

**Errors.** Neighbouring rows share most of their pixels (a 128-px template moved 16 px keeps seven-eighths of them),
so the rows' scatter about the fit overstates how many independent readings there are by about (128/16)^2, and a pair's
error from that scatter is multiplied by 8 (`OVERLAP`). Even so it is a floor: on PR144 the readings of pairs 10 frames
apart differ by 1.5 to 3.4 times it (the spreading 1.8, the turning 3.4, the stretching 1.5; the robust scatter of
successive differences over the root of two), part of which is the camera's own change between pairs. So the clip's
numbers take their errors from the pairs' scatter about their median (`median_error`: the median absolute deviation as
a sigma, times 1.2533 over the root of the pairs), which does not depend on that factor; a pair's own error stays in its
row of `<tag>_dense.csv`.

**Card and CPU.** The dense field is `shift_field` at another stride, so it runs on the graphics card wherever `layers`
does (`forensics.pooled_or_on_card`: the pairs in this process with the frames read ahead, the card doing the
matching), and on a pool of CPUs elsewhere. The empty frames are made on the CPU either way, so both match the same
arrays. On PR144 (24 pairs, 1080p) and PR113 (8 pairs) card and CPU chose the same pairs and the same templates;
1 row of 104,812 took a shift more than 0.01 px from the CPU's (another peak, its own height 0.016 apart); the floors,
the layers and every count are the same, and the clip's numbers agree to about a part in a million. A run on the card
and one on the CPU keep their caches apart, as `layers`' templates do (section 52), and a case says which computed it.

**How it is held.** test_measurement: a drawn clip of two layers, the upper one sheared (`test_zz_scene_dense_field_...`):
both layers in every pair, the second 226 px/s from the first where it lies against the 228 drawn, the faster above and
the slower centred where it was drawn, neighbours 99.3 % together against 52 % by chance, the shear read as -15.02 and
15.00 against 15, the files written, the reading read back from its cache, and every other field, line and file of
`layers` unchanged; the floor and the scrambled frame on their own (`test_zz_scene_dense_floor_...`). Each check fails
on a small change to the code it holds (taking out the straddling rows' refit, the floor's worse-of-two, the half turn,
the neighbours' count, the turning's sign, the scrambled frame's power, the second layer's separation, the keep rule's
gap); the factor of 8 is not held by a drawn clip (on drawn texture a right error and a wrong one both pass), and is
set by PR144 above. test_gpu: on a drawn clip, the card's code (NumPy standing in, and arthur's card in a job given it)
against the CPU: the same pairs and templates, the pair's and both empty pairs', each shift within 0.01 px and each
peak within 1e-4, the same floor and every kept template in the same layer.

**What the reference clips gave** (300 frames from the middle of each, k = 5, 24 pairs, on arthur's card, 2026-11-16):

| clip | picture | pairs measured / with a layer | floor | empty pairs keep: turned, scrambled, another clip's | matches kept a pair (`layers`' own) | two layers | card, s |
|---|---|---|---|---|---|---|---|
| PR144 | 1920 x 1080 | 24 / 24 | 0.50 | 0.2 %, 0.0 %, 0.3 % | 2,984 (82) | 7 pairs, 94 px/s apart | 24 |
| PR113 | 1920 x 1080 | 24 / 16 | 0.74 | 1.0 %, 0.0 %, 0.0 % | 787 (26) | none | 11 |
| PR149 | 1920 x 1028 | 24 / 18 | 0.50 | 0.3 %, 0.0 %, 0.0 % | 501 (12) | none | 24 |
| PR43 | 1920 x 1080 | 15 / 15 | 0.50 | 0.0 %, 0.0 %, 0.1 % | 2,281 (63) | none | 11 |
| PR44 | 1920 x 1080 | 24 / 22 | 0.50 | 0.0 %, 0.0 %, 0.0 % | 438 (12) | none | 9 |
| PR077 | 1280 x 720 | 12 / 0 | 0.54 | 0.9 %, 0.0 %, 0.0 % | 182 (6) | none | 5 |
| PR097 | 1280 x 720 | 23 / 0 | 0.50 | 0.2 %, 0.1 %, 0.1 % | 148 (5) | none | 8 |
| PR099 | 1280 x 720 | 9 / 2 | 0.50 | 0.4 %, 0.1 %, 0.0 % | 272 (8) | none | 6 |
| PR135, PR41, PR079, PR085, PR088, PR141 | | 0 | | | | | |

The empty pairs' shares are at the clip's floor; "another clip's" is PR144's middle frame (PR113's for PR144). The six
clips of the last row held still on the screen through these 300 frames, by `layers`' reading: no pair moved with a
consensus, so there was nothing to map, and the dense field says so. A layer needs 288 kept matches; on PR077 and
PR097 no pair had that many (a median of 182 and 148 kept), on PR099 two of nine.

- *A second layer only where there is one.* PR144, sea and cloud tops, is the one clip of the fourteen with two layers:
  `layers` puts two motion groups in 29 % of these pairs and the one against the other at 97 px/s. The dense field found
  two in 7 of its 24 pairs, 94 px/s apart (median), each pair's neighbouring matches 97.5-99.8 % in their own layer
  against 50-72 % by chance. In frames 585-834 (the window of the 2026-11-15 probes, and of the figure) it found two in
  5 of 24, 91 px/s apart, against `layers`' 91: the faster (the sea) in the upper part of the picture and the slower (the
  cloud tops) below. In the 73 pairs it mapped on the other clips it found no second layer.
- *The floor.* The half-turn set it wherever it was raised: on PR113 (to 0.74; the half-turn kept 1.0 % there, the
  other two none) and PR077 (to 0.54). The scrambled frame kept at most 0.1 % anywhere, another clip's frame at most
  0.3 % (on PR144); neither came near binding. The scrambled frame has none of a real scene's edges and keeps a little
  less than another clip's frame does, so where a clip's floor could hinge on the second empty pair, `--null-from` with
  another video is the stricter test.
- *What PR144's larger layer does across the picture* (px/s per 100 px; the median of 24 pairs and its error from their
  scatter). In frames 585-834 it spreads by +0.8 +/- 0.3, turns by -4.7 +/- 0.9 and stretches by +2.1 +/- 0.4: the sea's
  speed falls down the picture, by about 5 px/s per 100 px in the figure's pair (frame 797). In frames 268-567 it spreads
  by +1.2 +/- 0.1, turns by -2.0 +/- 1.2 and stretches by +1.3 +/- 0.2. So the change across the picture is there, and
  is not the same along the clip, as the camera's own motion is not. The probes of 2026-11-15 read it at 5-20 times an
  error from the rows' scatter, which was too small by the overlap; these errors carry the pairs' own spread.

**What it costs.** On arthur's card (an RTX 5070 Ti) the 24 pairs of a 1080p clip and their 48 empty pairs took 9-24 s, a 720p
clip's 5-8 s, with the search reaching 24 px past each pair's motion (a wider reach costs more: about 0.3 s a 1080p
field at a reach of 150 px). The CPU's arithmetic is about 45 times one core's time: on PR144 the same 24 pairs took
143 s with 16 CPU cores, `layers`' own passes included. The job's largest process held 2.6 GB. The map file is about 100 kB a pair at 1080p.

**What it does not do.** It changes no number of `layers` and no sentence of a report; `run` and the window do not ask
for it. It names no layer: "faster" and "slower" are on the screen, and which is the sea and which the cloud is the
person's (`--names` names `layers`' own classes, not these). It gives no range: a layer's shift is the camera's
rotation plus its motion over the layer's range, and neither the parallax between layers nor the change across one
turns into a distance without the camera's own motion (section 33's unknowns). It does not follow a layer from pair
to pair; each pair is mapped alone. Smaller templates, a ring about the object and the scene behind a sensor's pattern
were measured and left out (the design above).

## 66. Cameras on the ground: lines of sight with their own time and camera (`mcdonald drift --rays`; ROADMAP 0.5.8, item 1; added 2026-11-17)

**What it is.** Section 34's route "from the aircraft's own track" fits a straight path at a steady velocity to rays that
cross (`drift.fit_track`), and until now the only way in was `--platform` and `--los`: one camera that moves, its
readings keyed by the frames of one video, every azimuth resting on one reference. Cameras standing on the ground see
an object at once from places kilometres apart, and their rays cross with no turn at all. The Galileo Project's three
sites near Las Vegas (section 53) went in by a workaround kept outside the package: the sites written as one aircraft
that jumps between them, each site's reading at a 1/60-s bin put on frame 3 x bin + site at 180 frames a second, a
grey placeholder for the video, one azimuth reference for all. `mcdonald.sightlines` is the input of their own:

```bash
mcdonald drift --rays rays.csv --cameras cameras.csv --winds model_1.json,model_2.json --ground-m 600 \
  --flicker a.json,b.json --out CASE --json
# rays.csv     time_utc,camera,az_deg,el_deg            a row a reading; t_unix_s or t_s for the time, dep_deg for
#                                                        the depression; lat,lon,alt_m here if there is no cameras file
# cameras.csv  camera,lat,lon,alt_m
#   --pointing-err AZ,EL   how well each camera's pointing is known, deg (by default the errors of --los-sigma)
#   --reference shared     one azimuth reference for every camera (--az-ref-err), as an aircraft's display has
```

**The input.** A reading is a row: its own time (seconds from any zero, unix seconds, or an ISO time, UTC where it
names no zone), its camera's name, an azimuth, and an elevation or a depression. A camera's place is in its rows or,
once, in a cameras file; a camera that moves gives its place in every row. Several cameras may read at the same
instant. No video is asked for: `video` is now optional for the whole command, and only the inputs timed by a video's
frames (`--platform`, `--los`, the ranges, the tracks) need it or `--fps`, and say so without. A call that gives a
video does what it did: the drift files of section 34's four known answers are the same to the byte before and
after. `sightlines.rays` returns the dict `drift.rays` returns, with four more keys (`camera`, an index a reading;
`cameras`, the names; `epoch`, the unix time of t = 0 where the times are absolute; `reference`), and `fit_track`
takes one more keyword (`pointing_err`). Where the times are absolute, `--when` (the hour of the model winds) is by
default the rays' own mean time, the time the path's point is quoted at, and the command says so (the workaround
gave the median time: on none of the 239 Galileo objects do the two pick different hours).

**What a camera has of its own**, and an aircraft's display has once for all its rays:

- *Its place, and the two gates* (`drift.path_off_line`, `drift.range_bound`). The path gate asks how far the places
  the rays start from leave one straight path at a steady speed. One camera standing still leaves it by nothing, and
  is refused: "one camera standing still cannot range what it sees". Two cameras reading together leave it by half
  their distance. The gate's 20 m (2 x `POSITION_ERR`) is section 34's judgement, unchanged, so two cameras under 40 m
  apart are refused whatever their angles. The range's bound is taken from the camera it is largest for (the
  aircraft's route takes the reading nearest the mean time, which among cameras is any one of them), and it counts
  the cameras' pointing: two cameras 45 m apart, 8 km from the object, cross at a third of a degree, their rays'
  scatter alone bounds the logarithm of the range at 0.03, and a pointing error of 0.3 deg in each makes that 1.3 (the
  tests). The words name cameras, their distance apart and the angle their lines of sight cross at; `los_turn_deg`
  is the most any one camera's own line turned (the workaround's was the jump between cameras, and over three
  interleaved sites `np.unwrap` ran it to 4,487 deg on one run).
- *Its pointing* (`sightlines.pointing`, `--pointing-err`). `drift.az_reference` adds one constant to every azimuth:
  the display's true north. One constant turns every ray the same way, and the angle at which two cameras' rays
  cross hardly moves. A calibrated camera has its own error, and two cameras' errors change that angle itself, and
  with it the range and everything that scales with it. Carried: a constant in azimuth and a constant in elevation
  for each camera. Over the few degrees an object crosses in a frame, any small rotation of the camera, and a lens
  model that is off there, move all of its rays alike in the two angles; a clock that is off moves them alike along
  the track, which over a short track is such a constant too. As in section 34 the path stays the six-parameter
  fit, which takes every camera's pointing as right, and what is carried is the error of doing so: the path moves by
  S = (J'J)^-1 J'B for one degree (J the fit's Jacobian, B what a degree in one camera's azimuths or elevations does
  to the residuals; exact for the least-squares path while the offsets are small), and the covariance S diag(known^2) S'
  is added to the rays' own. The rays' own reading of each offset is reported beside (the offsets fitted with the
  path, each held to what is taken as known) and never used to tighten it. With `inf` nothing is taken as known,
  the rays' reading and its error stand in, and for two cameras that leaves the velocity open.
- *Its scatter* (`sightlines.own_scatter`). Section 34's rule (whose errors the path carries), camera by camera: a
  camera's degrees of freedom are its two residuals a reading less its share of the six parameters. On the 239
  Galileo runs the largest of a run's cameras' rms residuals is 1.95 times the smallest in azimuth (median; over 3
  times on a third of runs) and 1.38 times in elevation, and 72 runs have cameras under different cases of the rule.
  The scatter is read about the six-parameter path, so an offset the path cannot take up counts twice, once as
  scatter and once in the pointing: the errors are wide rather than narrow where cameras disagree.
- *Its share of the bootstrap* (`sightlines.resample`). Which camera read how often is the design, not chance: each
  resample draws each camera's own readings. Drawn from all readings alike, 1 resample in 160 holds none of a camera
  that read 5 times beside one that read 121, and is one camera's fit: the velocity's error came out 10 times the
  covariance's and the height's 40 times; by camera, 1.3 to 2.3 and 1.1 to 1.8 (the tests' scene, three seeds).
- *No wind of its own.* `aircraft_wind` reads the wind an aircraft flies through from its turn. A camera on a roof
  flies through none, and none is looked for.

**How large a camera's pointing error is, measured on the Galileo rays.** At an instant two cameras give four angles
for a point's three coordinates and three cameras six. One or three combinations of the angles say nothing of where the
point is, only whether the rays meet, with no path model at all. Their means over an object are read as each camera's
constant offsets seen through the geometry, and the likelihood of the offsets' size is summed over objects (a working
note of 2026-11-17; aggregate numbers only, the data are the Galileo Project's).
- The rays do not meet. From two sites they pass each other at 0.24 deg for a cloud (the median object's mean; 0.97
  for one in ten), 0.30 for an aircraft and 0.69 for two different clouds matched, while within an object that angle
  scatters by 0.03 deg for a cloud. With no offset allowed the likelihood falls by a factor beyond counting, and
  with none in elevation nearly as far: both angles are needed.
- The size has a heavy tail, so no one number is right. The median object is best fitted by 0.25-0.30 deg (one size
  for both angles; 0.30-0.40 in azimuth and 0.15-0.25 in elevation apart); a quarter of objects ask for 0.5-0.7 or
  more, a tenth for 1.0. Read as one Gaussian the tail sets the size: 0.70 deg in azimuth and 0.40 in elevation, set
  on the days of even rank (89 aircraft and clouds) and read as the same two numbers on the 110 of the odd days.
- What the offsets are is not decided here. Two cameras of one site's ring, where their frames overlap, disagree
  by 0.3-5.5 deg in azimuth (the frames' far edges: the lens model, or a box cut by the edge); two sites see
  different parts of a cloud; an aircraft's miss grows with how fast its line of sight turns (rank correlation +0.30,
  p 0.006; a quarter of a second of clock would make the median miss), a cloud's does not.
- So the default, each camera's pointing as well known as one of its readings is given to be (`--los-sigma`, 0.3 and
  0.1 deg), is the median object's in azimuth and half of it in elevation. **It is section 34's judgement carried
  over, not this measurement**, and which number the Galileo runs should be given is the maintainer's to say (the
  runs below give three).

**Held on drawn cameras** (cameras standing as the three sites do, about 10 and 2 km apart, watching a drawn drifter
2.5-5.5 km up for 40-80 s; each camera's rays with a white error and a constant offset of its own in each angle; 400
draws a row; two errors hold the true east and north velocity, climb and height this many times in 100):

| what was drawn, and how it was fitted | cameras | east | north | climb | height |
|---|---|---|---|---|---|
| offsets of 0.3 and 0.1 deg, taken as known to that; errors given 0.3 and 0.1 (the defaults), scatter 0.03 | three | 97.8 | 98.8 | 99.5 | 95.2 |
| | two, 10 km apart | 97.8 | 97.8 | 98.2 | 92.8 |
| | two, 2 km apart | 96.8 | 97.8 | 99.0 | 95.8 |
| the same draws, fitted with one shared azimuth reference (0.3 deg) | three | 94.8 | 94.8 | 96.2 | 30.8 |
| | two, 10 km apart | 89.0 | 90.0 | 90.8 | 26.2 |
| | two, 2 km apart | 73.2 | 75.0 | 84.2 | 10.2 |
| offsets of 0.3 and 0.1 deg known; errors given equal to the scatter drawn (0.03) | three | 99.0 | 98.5 | 99.5 | 94.2 |
| | two, 10 km apart | 98.0 | 97.2 | 98.2 | 94.2 |
| | two, 2 km apart | 96.5 | 97.0 | 99.0 | 94.8 |
| offsets of 0.03 deg in each angle, known; errors given 0.03 | three | 98.2 | 96.5 | 98.2 | 94.5 |
| | two, 10 km apart | 98.0 | 95.5 | 97.5 | 94.8 |
| | two, 2 km apart | 96.2 | 97.2 | 96.8 | 94.8 |
| offsets of 0.1 deg drawn, taken as 0.3 and 0.1 (the defaults) | three | 99.0 | 99.5 | 100.0 | 98.2 |
| | two, 2 km apart | 99.0 | 99.0 | 99.2 | 98.8 |
| no offsets; each camera's scatter drawn from 0.015, 0.05 and 0.15 deg; each camera's own scatter | three | 96.2 | 96.8 | 95.8 | 94.5 |
| | two, 2 km apart | 94.8 | 96.8 | 96.0 | 94.8 |
| the same draws, one pooled scatter | three | 93.5 | 96.0 | 96.2 | 95.0 |
| | two, 2 km apart | 94.5 | 93.8 | 95.0 | 95.8 |

With each camera's pointing carried, two errors hold the true height 93-96 times in 100 and the velocity and the climb
96-100: the velocity's are a little wide, because an offset the path cannot take up is counted as scatter too. With one
shared reference, the aircraft's model, the same rays' errors hold the height 10-31 times in 100 and the velocity of two
cameras 2 km apart 73-75: the error that model leaves out is the one that sets the range. A binomial error on 400 draws
is 1.1 at 95. The covariance's errors alone were read (no bootstrap), as section 34's coverage was. One pooled scatter
holds the truth as often as each camera's own on these draws (93-96 against 94-97), so drawn cameras do not decide
between them; each camera's own was kept because the Galileo cameras' scatters differ as they do (above).

**Held to the 239 Galileo runs** (section 53's objects, run at the v0.5.7 tag on 2026-11-17 by the workaround; the
same selection of rays, the same winds and flicker envelopes):

- *The same fit.* Given by `--rays --reference shared` with the workaround's own times (each site's reading a third
  or two of a bin late) and its `--when`, every number the two drift files have in common is the same to the last
  bit on 239 of 239 objects, the readings' numbers in `frames` excepted. The tests hold the same on drawn cameras.
- *What the stagger was worth.* With each reading at its own time, the fitted speed moves by at most 0.14 m/s (5
  parts in 10,000, a 283-m/s aircraft), a climb by 0.12 m/s, the velocity's error by 4 %; the one shared reference's
  pull moves most, on short tracks (0.36 to 0.011 m/s a degree on a 3.3-s track: a site read always a 180th of a
  second late turns a constant shift of position into a velocity of about shift x 6 dt / T^2). One verdict moves: a
  mismatched pair at 1.0 m/s goes from drifting to cannot say at the edge of the hold-still rule (drifting needs
  0.7 m/s, holding still 0.7).
- *Each camera's own pointing.* Verdicts as drifting (tentative) / cannot say / not drifting; a site as one camera,
  as the workaround had one ray a site; the winds' hour from the rays' mean time:

| group | n | v0.5.7, one shared reference | each camera's own, 0.3 and 0.1 deg (the default) | 0.3 and 0.2 | 0.7 and 0.4 |
|---|---|---|---|---|---|
| aircraft below 3 km | 60 | 0 / 9 / 51 | 0 / 26 / 34 | 0 / 32 / 28 | 0 / 56 / 4 |
| aircraft above 8 km | 20 | 0 / 7 / 13 | 0 / 14 / 6 | 0 / 19 / 1 | 0 / 20 / 0 |
| clouds, three sites | 59 | 37 / 21 / 1 | 40 / 18 / 1 | 32 / 26 / 1 | 27 / 31 / 1 |
| clouds, two sites | 60 | 27 / 28 / 5 | 28 / 29 / 3 | 29 / 28 / 3 | 26 / 31 / 3 |
| mismatched low pairs | 40 | 21 / 19 / 0 | 20 / 20 / 0 | 20 / 20 / 0 | 20 / 20 / 0 |

  The fitted path is the same in every column; only its errors differ. Two errors of an aircraft's velocity go from
  3.0-4.0 m/s (medians, by group) to 8.8-9.9 at the default, 11-12 at 0.3 and 0.2 and 23-25 at 0.7 and 0.4; of a
  cloud's from 2.2 to 2.3-2.4, 2.6-2.7 and 3.0-4.5; of an aircraft's height from 10-39 m to 133-172, 155-246 and
  343-491. No aircraft is called drifting in any column.
- *Every verdict that moves at the default* (35 objects against v0.5.7). 24 aircraft go from not drifting to cannot
  say: T2 failed them (they need 93-250 m/s through the air), and now cannot say because two errors of their
  velocity pass 5 m/s (5.4-31 m/s). One of them, and two aircraft that were already cannot say, lose T1's pass the
  same way (two errors of the climb over 8 m/s). Five clouds go from cannot say to drifting: they need 4.6-11.2 m/s,
  and the tolerance, wider by the fit's two errors, now reaches that. One cloud goes from drifting to cannot say (it
  needs 6.8-7.8 m/s, and the tolerance is 7.65 where it was 7.78: the fit's two errors are 0.13 smaller with each
  camera's own scatter). Two "clouds" go from not drifting to cannot say: one climbing at 25.8 m/s whose climb is now known to
  7.6, one at 19 m/s whose two errors are now 5.6. One mismatched pair moves as with the true times, above.
- *The stated errors against known speeds.* The 80 aircraft carry transponders, and the Galileo catalog gives each
  one's speed from them. The fitted speed misses it by 5.5 m/s (median; 30 m/s for one in ten). Two stated errors
  hold it on 50 % of the aircraft with one shared reference, on 66 % with each camera's own pointing at the default,
  72 % at 0.3 and 0.2 and 78 % at 0.7 and 0.4 (84 % with 2 m/s allowed for the transponder and a speed that
  changes along the track). Nothing was set on these speeds. The shared reference's errors were half too small; no
  one size of pointing error reaches 95, the sizes' tail again.
- *One camera.* The site with most rays alone, on the first 121 of the 239 objects (a run takes up to 460 s, the
  bootstrap fitting a flat cost): T1 and T2 cannot say on 121 of 121, each reading "all N lines of sight start from
  one place. One camera standing still cannot range what it sees".
- *T2's gate, measured and not changed.* T2 cannot say wherever two errors of the velocity exceed 5 m/s
  (`VELOCITY_FIX`), before it asks whether the body is a flier's 10 m/s beyond the whole tolerance, which already
  holds those two errors. Asked in the other order, as the far-wind rule already is, T2 fails 80 of the 80 aircraft
  in every column (54 at v0.5.7), and one to three "clouds" that move at 19-64 m/s. The least clear aircraft moves at
  60 m/s with two errors of 8-13 and needs 58 m/s against a tolerance of 12-18.

**Judgements** (each for the maintainer to confirm): the default for what is known of a camera's pointing (above);
the path gate's 20 m kept for cameras; the bootstrap by camera; the range's bound from the worst camera with the
pointing counted; the winds' hour from the rays' mean time; `frames` in the path's fields as the readings' numbers.

**How it fails.**
- A camera's offset is taken as constant over the track. A track that crosses much of a frame, or passes from one
  camera of a ring to the next (a step of a degree at the Galileo frames' edges), is not one constant; give each
  physical camera its own name.
- The offsets' size is one number for every camera and object, and the measured sizes have a heavy tail: for the
  median object the errors are right or wide, for one object in four they are narrow.
- A clock error is carried only as the constant it looks like over a short track. Cameras whose clocks disagree by a
  quarter of a second put a fast object's rays a quarter of a second apart along its path.
- Two different objects matched across cameras give rays that still cross somewhere (section 53's mismatched pairs).
  Nothing here sees that. The misfit and the rays' own reading of each camera's pointing are the only signs, and
  they are reported, not judged.
- T2's rule is section 34's: it cannot say where two errors of the velocity exceed 5 m/s, however fast the body. With
  each camera's pointing carried, a 120-m/s aircraft known to 10 m/s meets that gate (below).
