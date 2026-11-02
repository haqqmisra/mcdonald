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
0.25. A range bound takes the farthest range in the box, a height bound the lowest height. A thing whose band reaches
the line is neither below nor above it, and gets no bound.

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
less the sides' mean carries 1.5 times one line's noise variance, the difference 2 times). The largest ratio within the
band (two or more cycles in the dash, beads at least two blurs apart) is an F ratio with 2N degrees of freedom on each
side for N dashes; its chance, multiplied by the frequencies looked at, under 1e-3 is a flicker.

**What it assumes, and says on every run.** The object moves straight during one exposure at the track's speed; the
dash is the object's (a camera turning during the exposure smears the scene too); the beads are the object's light and
not the scene behind it, which the side lines take out.

**Validated.** Rendered frames, a point drawn step by step while a 180-degree shutter is open (`tests/test_streak.py`):
steady at 51 px a frame, the exposure 0.50 of a frame and no flicker (false alarm 0.33); blinking at 360 Hz, beads every
4.27 px, 365 Hz at a false alarm of 4e-28; at 2 px a frame, no dash long enough; at 20 px a frame through a 3.5-px blur
read off 24 points of the scene, 0.52 at the blur read and at 2 px alike; at 10 px a frame, a dash under twice the blur,
0.52. **PR43** (its case file's track, frames 50-75, 2026-10-29): its points read a blur of 3.6 px (43 spots on 12
frames); the dash, 6.5-7.0 px at 18.5 px a frame, gives 15.6 ms (0.47 of a frame) at that blur and 14.7 ms at 2 px --
the median of the frames' own ratios; the ratio of the medians is 12 ms -- the centroid's jitter (the speed band's
nugget, 5.7 px) spreads the frames' speeds. Under three of its own blurs, it has no light curve: the bead search made at
an assumed 2 px (none, false alarm 5.8e-3) does not stand.

**What it cannot do.** Read a dash under three blurs long, beads under two blurs apart, or a flicker slower than two
cycles over the dash.

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
- *the average velocity over the stretch*, (f(t1) - f(t0)) / T on the latent path -- the displacement over the time,
  the nugget out -- with its honest standard error from the joint posterior of the two ends. Against the line's
  white-noise error this is 0.03-0.8 times as large on curving tracks (the line charges the bend to noise) and up
  to 1.5 times larger where a straight track has a correlated wobble: the white assumption is wrong both ways;
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
  when every wind that counts leaves it within their own spread plus two errors of the fitted velocity; fails when
  even the smallest is 10 m/s or more beyond that (it flies); and cannot say between, or when two errors of the
  velocity exceed 5 m/s (T2 cannot then tell a drifter from a slow flier).
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
- *T3, the beat.* Is its brightness free of a beat at a wingbeat's or a rotor's rate? From `mcdonald flicker`: a beat
  of its own that holds across the video fails (a wingbeat or a rotor). "Holds" is flicker's headline rule (§13,
  `comes_back`): the whole track beats, or passing windows that do not overlap agree. A beat in one stretch of many is
  not counted, since a lantern's or a candle's flame, or chance over many windows, can make one, and the test passes on
  the whole stretch (until 2026-10-22 it could not say); an envelope without the record is read from its finding ("that
  is one stretch"). No beat passes, with the smallest beat the clip could have shown (the injections' floor, else the
  rule's own threshold, three times the background's).
- *T4, other evidence.* Does other evidence in the video, where there is any, agree with drift? Few videos show a strike
  or anything shed, so this test runs only on whichever of its parts the inputs allow. It fails when a part fails,
  passes when a part passes and none fails, and cannot say otherwise; only its tracer part bears on the airspeed.
  - *T4a, a tracer.* Does it move with something that moves with the air at its own depth? Light pieces it sheds stop in
    the air within about a second, so a flier at airspeed V leaves them behind at V sin δ on the screen. The pieces'
    speed against the remains, in L per second (a straight line in time to their difference, its error from a
    moving-block bootstrap), divided by sin δ bounds the airspeed in the object's own lengths per second, with no field
    of view, range or wind. Fixed-wing drones cruise at two or more of their lengths a second, birds at four or more: a
    bound under 2 passes; pieces leaving at 2 L/s or more fail. L is taken at its smallest (the rate kindest to a
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

An average is no limit on a speed that changed, so a track that changed its speed is said twice, on average over the
stretch (the line's rate or the band's average, the larger: a path that doubles back has a line slower than its speed)
and at its fastest (`upper_bound_fastest_m_per_s`, the band's fastest, §32; on a track too short for a band that is not
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

The rows, in a fixed order, and what each reads:

| row | reads | Yes | No | Can't tell / Partly |
|---|---|---|---|---|
| repeated frames or sudden changes of brightness | `survey` | so many of each | every frame new | -- |
| did the camera move | `layers`' held-still share over about a second (`still_again_share`): 90 % or more held, 10 % or less moved | the background moved across the picture | the picture held still | Partly: held in some pairs, moved in the rest |
| does the object move against the background | `Case.rate` | the rate, against the background or across a picture that held still | under half a pixel a second | Can't tell where the rate is the picture's and the camera moved: the rate against the background was not measured |
| straight at a steady speed | the speed band's `constant`, the turn's `turned`, the loop | the band held, the path straight | the speed's range along the track and the bend; "(the camera moved, so some of this may be its motion)" where it did | Can't tell under the frames a band needs |
| coming toward the camera | tau from its size (section 33), the projective fit, the depth bound, the size's trend | its size grows or its path fits an approach, with the time to the camera's distance | the depth bound, under the hypothesis | Can't tell where its size held, could not be read, or its path fits only roughly |
| beats as a wingbeat would | `flicker`'s beats, by the headline's rule (section 13) | the rate, the object's own; a flock's members each their own | no rhythm of its own; or a beat outside the wingbeat band, said | Can't tell where the picture shakes at that rate; Partly in one stretch, or under BIRD_FLOOR |
| could something other than a bird beat like this | the look-alikes (section 9) | always, where a beat is the object's own: a tumbling body, a blinking light; a flame's band or a rotor's look where marked | -- | -- |
| flashes in a train | `flicker`'s blink (section 19) | the flashes a minute and the rule they meet | no train | -- |
| a single thing | `groups` | one point on most frames | so many things moving together, keeping their places or changing them | -- |
| anything moving with it | `tether` (section 6) | the companion, its distance in object widths, its swing or its steady angle; a fellow member | nothing within the ring | Can't tell under the frames it needs |
| moves through what is round it | `comotion` | MOVES THROUGH | CARRIED | INCONCLUSIVE, NO POWER |
| added to the video afterwards | `integrity`'s object tests (section 2) | checks that flag it, named | the checks that could decide pass, the rest said | Can't tell where none could decide |
| a real speed and size | the four unknowns (ROADMAP 0.4 objective 6) | the speed and size, "a guess" where k is | what it needs: the field of view, the distance | Partly: a bound from a thing of known size or a farthest range, a least speed at a given distance, or a turn rate with no distance |
| a person picked out the object | `identified_by` | marks placed by hand | an agent's, typed, the computer's suggestion taken, or snapped marks: "every measurement of the object rests on that choice" | -- |
| a person checked the track | `verify`'s `reviewed` | the sheet looked at | -- | Not yet |

A row whose stage did not run has no row: the table says nothing it did not check. The paragraph that was at the top
is folded under the table (`<details>`: a link on the window's report page, a fold on GitHub, expanded in the PDF), not
gone; the conclusion's sentence stays first, so the exercise pages, which quote it, stand. The window's report card has
the same rows above its numbers, the answer in a word and why in the tooltip; `mcdonald run --json` carries them as
`results.checklist`. The rows are read from the stages' fields, as the conclusion and the bottom line are, so a case file
from an earlier version gets its checklist when its report is opened or written again. Measured: the rows' own words are
97 % at tier 4, 12 words a sentence; test_gui holds them to the window's plain words (no px, clip, velocity, provisional).
What the checklist is not: a grade (S17), reason codes ranked by their weight (E7), or Louange's items (F56), which are
still to do.

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
