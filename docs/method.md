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
| How many pixels is a degree, from the camera's own slew? | `mcdonald slew` | the pointer (`symbology`) and the scene (`layers`) |
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
with ratios within a fifth. On noise with a power-law spectrum and no line it passes about once in a hundred, as a
null at 0.01 should. What it cannot see is a slow change that the running mean turns into a bump near 1/DETREND_S: its
noise curves are not taken through the running mean. That is the drift test's trap, and the reason the stage's own rule
keeps the drift test.

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
the drift test's 1 in 100 over the band. With the background apertures' own flicker it is ABOVE times that, where that
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

**PR144 (2026-10-20): NO POWER.** The orange pointer is read on all 837 frames (radius 310.95 +- 0.92 px; steps of
0.18 deg) and turns from 176.8 to 170.8 deg, steadily but for a 0.7-deg bump at 14-16 s; the camera pans after the
contact the whole time, mostly in elevation (306 px rms down against 232 across beyond the hold). The largest group
mixes sea and cloud tops (two groups in 32 % of pairs); the sea alone reads 2872 px/deg (16-84 % 2341-4246) with the
forward fit at 836, refused; the cloud tops' slews are mostly vertical. The zoom check (k before and after the x5.9
step) needs a slew in the wide view, which lasts 2.5 s and has none.

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

The scene "moves at the beat" where its shift stands SHIFT_STANDS times over the band; a scene without the detail to
register (SHIFT_TEXTURE) is not read. Phase correlation was tried first, in the PURSUE analyses, and dropped: its peak
locked onto PR135's fixed pattern at zero shift and pulls a sub-pixel shift toward whole pixels. The fixed pattern
does not move with a real jitter and pulls this reading toward nothing by its share of the picture's detail, which is
not measured; the planted test moves the scene and the pattern together, so its recovery is an upper bound. On a
synthetic scene jittered 0.3 px at a 6-Hz beat it reads 0.300 px; held still, 0.0002 px, its planted 0.05 px coming
back at 0.998; on a featureless sky it is not read.

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
0.58 in their two commonest intervals). Kept as it was; the misreads are written into `pictures`' docstring.
