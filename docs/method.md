# Video-forensics toolkit — background layers and clip integrity (method note)

Two questions come up on almost every PURSUE sensor clip, and both were first
answered by hand on DOW-UAP-PR144 (the `pr144_velocity_size` and
`pr144_integrity` workups). The tools below are those workups made independent
of the clip, and are the measurement core of this package.

| question | tool | needs |
|---|---|---|
| Everything below, in order, into one report | `mcdonald run` | the clip; a track for the object stages |
| How fast does the object move **against the background**, and is there one background? | `mcdonald layers` | the clip; a track for the object's rate |
| Has the clip been **altered**? Was the **object added**? | `mcdonald integrity` | the clip; a track for the object tests |
| Is the track on the object in **every frame**? | `mcdonald tracksheet` | the clip and the track(s) |
| Where is the boresight, and what is the sensor's azimuth? | `mcdonald symbology` | the clip |
| What does the motion permit in m/s -- and what is missing? | `mcdonald kinematics` | a track; k and R if they exist |
| Does the object move WITH the texture around it or THROUGH it? | `mcdonald comotion` | the clip, a track, the object's diameter |
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
  many templates, not single templates.

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
  gives slopes of r and 1/r; check that they straddle 1.
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
- **A "static detector pattern" that is really the scene.** The temporal mean
  of high-passed frames keeps whatever does not move. Use only frames in which
  the scene sweeps the detector (≥ 3 px/frame). Split the frames by alternate
  25-frame blocks, not odd/even: a striated sea moving along its striations
  leaks into odd and even frames alike (PR148: split-half r fell from 0.99 to
  0.41 with both fixes). For the test under the object, take the pattern from
  the other half of the clip.
- **Corner brackets.** They mark the *next narrower* field of view. They are
  not a fixed angle and do not grow by the zoom ratio. `zoom_ratio()` fits the
  zoom from the imagery (PR144: ×5.9, where the brackets had been read as
  ×2.97). For a same-scale transient it uses a small template, a wide search
  and a gentle high-pass, because sea texture decorrelates in ~0.3 s.
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
  and the report says when the fit is not.
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
FOV together, because numerator and denominator scale alike with range.

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
on it is not a result.

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

## 6. `mcdonald tether` — a hanging point is a clock (added 2026-10-07)

A sounding balloon carries its radiosonde 25–55 m below it; a hobby balloon a few grams
a metre or two below; the Lake Huron object of 2023-02-12 (PR071) had, in the pilots'
words, "strings hanging off". A hanging point is a pendulum, and its period is set by
gravity and the line alone: T = 2π√(L/g). Read T off the video in seconds and L is in
metres with no range and no field of view — the balloon analogue of PR135's wingbeat,
and the one signature in the sky that nothing but a tethered payload has.

**Does anything move with the object?** Every frame, overlay masked, shifted so the
tracked position lands at the centre, and averaged. A thing tied to the object adds up
at its offset; the scene and the overlay smear by however far the object moved on the
screen. Three tests then say what a sharp feature is:

1. *The control.* The same frames stacked on the track run backwards in time have the
   same set of positions and the wrong one each frame. A thing tied to the object
   smears there; whatever only looked sharp because the object hardly moved stays
   sharp. On PR055 the two residual peaks of the first stack reappeared in the control
   identically — they were the frame's edges.
2. *Single frames.* A thing tied to the object is there at its offset on single frames,
   at the same place to within a few pixels across its own spread. Cloud texture is
   dark *somewhere* in a patch on many frames, but spread over the patch (PR055: 11–14
   px of scatter); PR071's string sits at 4.
3. *With the object, or with the scene.* The feature followed frame by frame moves with
   the object rather than with the background's own shift — `groups`' test. It is the
   one that catches a piece of cloud drifting steadily past, which passes the first two.

The overlay's thin bright strokes (reticle arms, a tracking gate's box, brackets) are
masked before any of this, by a morphological opening: a tracking gate *is* tied to the
object — by the tracker, late — and its edges passed every test on PR071 until they
were masked.

**Does it swing?** The companion's separation vector from the object gives the swing
angle, which needs no scale and survives any camera motion short of a roll. Repeated
frames are left out. A Lomb–Scargle periodogram starts it, but the estimator is a
sinusoid with a drift fitted to the angle: on a window of a few cycles a periodogram's
peak slides up to whatever cap the window sets, and a peak at the longest period asked
is never a period. The period's error is a block bootstrap of the fit's residuals
(they are correlated frame to frame; single draws would say the period is known to a
thousandth). A swing is claimed from 2 cycles of the window and reported as tentative
from 1.5.

**Validation** (`docs/tether-validation.md`, the figure `docs/tether-validation.png`):
- WA9ONY-5, a 13 g pico payload under a mylar balloon, 2021-07-13, filmed at 1080p30
  for 4.3 s of free flight; the builder's own assembly video says "a little over one
  metre of cable" to the balloon. The swing: 2.59 ± 0.02 s, amplitude 14.1°, 1.7 cycles
  (tentative) → 1.66 ± 0.02 m. The pivot of a balloon's pendulum is the balloon's
  centre, not its neck (its inertia is mostly the air it displaces), so the pendulum is
  the line plus the balloon's radius plus the payload's own offset ≈ 1.5 m. Consistent;
  the error quoted is statistical, and the 1.7 cycles are why it is tentative.
- PR071: a dark line 1.6 object sizes below the object, 14° left of straight down, on
  64% of single frames, jitter 3 px; followed for 7.9 s it holds −18 ± 5°. No swing, so
  no length: a line held by drag, or stiff.
- PR055: the stack's strongest features (cloud streaks 7–22 sizes out) pass the control
  and even the single-frame test; followed, they move with the clouds, not the sphere
  (449 px apart by the end). Nothing tied.

**How it fails.** A payload too faint for single frames that swings more than its own
size smears in the stack by its swing and evades the follower too; that needs a search
over the pendulum's own motion (period, amplitude, phase), not written. A thin *bright*
line on the object is masked with the overlay's strokes (`--no-stroke-mask`). A line
held at a steady angle gives no length. And a tracking gate's edges can still pass as
"tied to the object" when they are too wide for the stroke mask; they are reported,
with their jitter, not hidden.

## 7. The astronomer's tests in `mcdonald flicker` (added 2026-10-15)

The flicker stage's own tests were each worked out on one clip that fooled it (the docstring's items 1-6). Astronomy
has named statistics for the same questions, with known null distributions, and a survey of the astronomy
literature (a working note kept with the PURSUE analyses, not part of this package) ranked the four that fit the
stage. They are now computed beside the
stage's tests on every run and reported with them; they do not yet decide (`flicker.GATE_ASTRO`), so that no number
changes until the goldens have been read with them on.

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

The slower nulls -- the background apertures through every window, and the planting -- are run by the command and by
`mcdonald run` (`--no-nulls` to skip them: about as long again as the stage's own windows) and left out of
`measure()` unless asked (`nulls=True`).

## 8. The seismologist's tests in `mcdonald flicker` (added 2026-10-15)

Seismology is the science of one sensor listening to a continuous noisy record of a source it cannot control, and its
literature, surveyed in a companion working note (not part of this package), adds the tests below to the astronomer's of §7.
Six of its ports are in the stage, computed beside the stage's own tests on every run and reported with them; they do
not yet decide (`flicker.GATE_SEIS`), so that no number changes until the goldens have been read with them on.

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


## 10. `mcdonald audio` -- what the sound track records (added 2026-10-16)

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
  67.75 Hz at 30 frames a second is 7.75 Hz, where birds beat.

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
the video, so a second look opens at once. The page says what the tool reads, so it shares the tool's limits: a
59.94-Hz field-rate buzz is still read as mains (above).

**Tested.** `tests/test_audio.py` (43 checks, portable): a four-bladed propeller with its second tone, a six-bladed one
heard alone with and without it, a lone line 1.2 % off, the codec's frames at the file's rate and at another, the
mains and the bus as clocks, a wandering series, noise alone (20 records of 20 s: no tones), a 2.8-s record, the
fold, the six traps the corpus pass found (sidebands, a wandering hum, odd harmonics, two encodes, retimed mains, the
frame rate's harmonics without it), what the window says (plainly, without the trade's words), and the command end
to end with silence as exit 5. `test_gui.py`'s `drive_sound` (11 checks) drives the window's page on a drawn propeller
and a silent video. `test_golden.py`'s
`test_audio_cases` (21 checks): PR117-PR119, PR106, PR107, PR113, PR39, six DVIDS C-130 cabin tracks of known type and
phase of flight, a UH-60 cabin, the Apollo 14 tape and an MQ-9 heard from the ground as negative controls
(`aircraft_audio/`).

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
  nothing at 60.00 -- the NTSC field rate's sync buzz, not mains -- and two supplies, 399.1 and 401.3 Hz. In 4-s
  windows the tool cannot yet tell the field rate, 60/1.001 Hz, from 60-Hz mains, and reads such a buzz as mains.)

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

**The corpus.** All 149 PURSUE video and audio records (`analysis/tools/audio_corpus.py` in the PURSUE analysis):
122 sound tracks are digital silence and 27 carry sound. Of the 27, three name an airframe (PR117-PR119, the T56
gunship), three carry an aircraft's 400-Hz power (PR106, PR107, PR111), two are double encodes (PR36, PR39), PR113 is a
tape dub with mains, the bus and its NTSC clock, and the NASA, Ruppelt and IIR records are ground recordings: mains
hum (four as clocks, five through a transport), sidebands, and one possibly retimed transfer (D008).
