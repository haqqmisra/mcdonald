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

