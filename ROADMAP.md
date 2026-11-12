# Roadmap to 1.0

Written 2026-10-16 at version 0.2.20, from a planning session with the maintainer. This file is
the plan; [CHANGELOG.md](CHANGELOG.md) is what happened. Each minor version below (0.3, 0.4, …)
is one theme with a test for being done. Patch versions go on being released whenever something
is fixed or finished, as now, and every push to `main` is a release with a new number. The
order is the expected order, not a promise: a new tranche of videos, a tester's report, or
control footage arriving can move a theme forward or back, and so can a finding nobody
planned for -- the wingbeat test was not on any plan, and it is now in about one PURSUE video
in twelve. What does not move is the standard every release is held to ("What every release
is held to", below).

The goal of 1.0 is fixed: **every PURSUE video has a reproducible case file, and every idea we
have for getting information out of those videos has been tried, shipped or set aside with a
written reason.** The 1.0 software paper goes to the Journal of Open Source Software (JOSS).

## Where this starts (0.2.20, 2026-10-16)

- **The package.** Thirteen stages from a video file to a case report (`ingest`, `survey`,
  `symbology`, `track`, `verify`, `layers`, `scale`, `kinematics`, `groups`, `flicker`,
  `tether`, `integrity`, `report`), some 24,000 lines in 43 modules. A window with one button
  that does the whole job and leads with its conclusion; a command line with JSON output for
  agents and advanced users; one file to send someone (`.mcdonald`); several objects as a queue
  of cases; what the person knows of a video asked before the run and on the report card.
  Seven test suites, about 1,200 checks, with the published numbers and the real clips held as
  goldens; macOS and Windows runners on GitHub; PyPI on a tag.
- **Unreleased on `main`.** The astronomer's and the seismologist's tests in `flicker`
  (Lomb-Scargle with its false-alarm probability, scrambled surrogates, common-mode removal,
  the fold, the background apertures as controls, planted beats; the multitaper F-test,
  coherence, the noise distribution, Sompi, the comb, the glide, one-bit), all reporting, none
  deciding yet (`GATE_ASTRO` and `GATE_SEIS` off). And a change that keeps frames lost at the
  troughs of an object's own beat, which broke three golden checks (PR23's hot roof, the
  balloon's "beat"): the first thing 0.3 fixes.
- **The data folder** beside the repository (see its `README.md` and `tests/reference_data.py`):
  nineteen PURSUE videos (the two papers' cases), the five Galileo Project flyers, the
  pico-balloon launch, the two folders of flicker goldens, and the outside control footage
  below (`svanstrom2021/`, `aaro/`). No case files yet.
- **The research record**, kept with the PURSUE analyses outside the repository: a beat sweep
  of all 126 PURSUE videos with an object to look at (85 beat-tested; a whole-video pass over
  122 clips followed 1,576 objects), with ten videos holding objects that beat at wingbeat
  rates -- PR135's six and nineteen more in nine other videos, about 8 % of the sensor videos;
  a first look at gliding birds; a search still running for what the pass could not measure;
  nine surveys of methods from other fields (astronomy, seismology, SETI, geostatistics, film
  and the visual arts, the philosophy of science and evidence, the literature on infrared
  observations of birds and other aerial objects, aviation, and information theory and data
  science) with 135 ranked ports,
  summarised in the ideas bank, since 2026-11-02 its own file, [IDEAS.md](IDEAS.md); and four clips of a drone show from
  the same infrared cameras as the flyers.
- **Control footage from outside** (2026-10-16, in the data folder): the Svanström et al. 2021
  labelled infrared set (79 bird, 157 drone, 74 airplane and 55 helicopter clips of about 10 s,
  30 frames a second, 8-bit, a box on every frame; CC0), and every report and video AARO has
  published (34 videos, 61 documents), among them the cases it resolved (birds, balloons, sky
  lanterns, a balloon cluster, aircraft, Go Fast) with its stated answer.
- **Papers.** The kinematic framework, *Limits on Kinematic Inference from the PURSUE Airborne
  Sensor Videos* (AIAA Journal of Aerospace Information Systems, Technical Note, in review;
  arXiv), and the bird paper, *Six objects reported at 480 mph … show brightness flicker at
  bird wingbeat rates* (Scientific Reports, submitted; arXiv; reproduction package on Zenodo,
  DOI 10.5281/zenodo.23021686). The cases in them are the reference cases of this roadmap.
- **Funding.** Emergent Ventures (Mercatus Center) awarded a grant in October 2026: a 48-core
  workstation with 128 GB of memory and a 16 GB GPU (on the desk since 2026-11-11), two years of the AI coding
  agent the package is developed with, and the open-access fee of a methods paper. Donations
  continue through Project Janus at Blue Marble Space.
- **People.** A colleague has run the window end to end on macOS; Windows has so far been run
  only by the automatic tests. The maintainer reviews every change and makes the release
  decisions.

## Principles

- **In James McDonald's spirit.** Treat the subject with ordinary scientific instruments:
  reconstruct what the record shows, bound what can be bounded, eliminate the conventional
  explanations symmetrically, and state the residue without overclaiming. Presume nothing
  either way.
- **NO POWER is an answer.** A test that cannot decide a question says so and names what is
  missing. A tool that always returns a number is worse than useless on this subject.
- **Controls before claims.** The bird result came from footage of known birds. Every other
  class (drones, helicopters, aircraft, balloons, gliders, insects, the sensor's own artefacts)
  gets the same treatment: footage of the thing, its predicted signature, the test, and the
  test's false-alarm rate on everything else.
- **Two approaches, both kept.** *Hypothesis-driven*: a predicted signature of a known class,
  built on controls, searched for in the corpus (the wingbeat, a rotor's lines, a strobe's
  cadence, a tether's swing, a glider's cycles). *Hypothesis-neutral*: everything the pixels
  record -- every object's track, light curve and size, the scene's motion, the sensor's
  record -- extracted for every video with calibrated nulls, and the anomalies ranked. Each
  release says which of its work is which.
- **The unknowns first.** The velocity equation of the Technical Note has four unknowns no
  PURSUE video supplies -- the angular scale *k*, the range *R*, the aspect angle *θ* (or the
  range rate) and the platform's velocity *v_own*. Any method that constrains one of them,
  or that says something true without them, comes first.
- **Expect the unexpected.** Nobody planned to find birds. The ideas bank is open, the surveys
  will grow, and a finding that reproduces from a case file is a paper whenever it comes.
- **Two audiences, one job.** Everything the window does has a command, and everything a
  command does, the window can do or show. Agents with no screen and people with no terminal
  both do the whole job.
- **No number changes silently.** Goldens, the recorded tracks and the published values hold
  every change; a moved number is said in the changelog with the reason it is right.
- **Plain words in the window; the report leads with its conclusion; no pop-ups; boxes only as
  tall as what they hold.**
- **Nothing invents detail.** No generative "enhancement", super-resolution or learned
  restoration, ever. A learned tracker may propose; it never judges.
- **A GPU is never required of a user, and the development machine's is used to the full from
  the start** (the maintainer, 2026-10-16). The CPU path is the reference and the goldens run
  on both; the GPU is where the work too costly for a CPU goes -- planted objects by the
  thousand, dense motion fields, error models -- and that work starts when the workstation
  arrives, not at 0.6.

## The releases at a glance

| version | theme | done when |
|---|---|---|
| **0.3** | The beat, held to account; the reference cases as files | goldens green; the flicker gates decided by evidence; a case file for every video of the two papers that reruns to its numbers; the beat sweep reproducible from the repository's tools |
| **0.4** | The unknowns: *k*, *R*, *θ*, *v_own* | *k* measured from the camera's own motion; the motion-free bounds on range; a speed with an honest band for every track; every report says which unknowns are constrained, by what, and what would close the rest |
| **0.5** | Controls: what known things look like | **0.5.0** (cut small on 2026-11-02, decision 11): the controls harness in the suites; the bird floor set on a null; AARO's 14 resolved cases run blind; reason codes and the grade beside the checklist; levels. **0.5.x**: drones, helicopters, aircraft, balloons, gliding birds and insects each with control footage (or an honest note that none exists), a signature test, and its false-alarm rate |
| **0.6** | Every frame of every video | a batch mode that runs the whole catalog unattended on the workstation, with completeness per video from planted objects; the GPU path complete, used to the full, never required of a user |
| **0.7** | Finding without a hand | the object the record describes found first, with no mark, on a stated share of the benchmark, and "nothing found" rather than a wrong thing on the rest |
| **0.8** | The sensor's record, and the displays | everything the pixels record about the sensor, the display and the file, in integrity's record for every clip; the remaining on-screen displays read |
| **0.9** | The walkthrough and the documentation | a new person on each platform completes the walkthrough from the docs alone; the same steps run as a test on the three runners; the JOSS checklist met |
| **1.0** | The catalog closed | a case file for every PURSUE video in the data package; the ideas bank exhausted; JOSS submitted |

## 0.3 -- The beat, held to account; the reference cases as files

**Released as 0.3.0 on 2026-10-19**, as the maintainer scoped it on 2026-10-17: the four "done when" conditions and
objective 2 (CHANGELOG.md has what went in). Objectives 4 (the sky's rhythms, the scene shift's spectrum, lantern
rigidity, clock steadiness, the 10-Hz shape tests), 5, 6 and 7 continue as 0.3.x patches, and D5's specification curve
and D7's false discovery rate with them.

The wingbeat test is the package's one result so far that changed what a video is taken to
show. This release makes it a calibrated detector with its false-alarm rate written down,
and puts the cases the two papers rest on into files anyone can open and rerun.

**Objectives.**

1. **Goldens green.** Narrow the lost-at-the-troughs rule so that PR23 and the balloon pass
   as before while PR097's dots keep their beats; run golden, not only the no-video suites,
   before any release. Release what is on `main`. The rule's principled form is Rubin's: a
   trough is lost because of the object's own value, a crossing because of what is behind it,
   and a regression of lost-or-not on the two decides which; where the troughs are kept, the
   amplitude comes from a censored fit, not from filling across them, which reads 0.68 of it
   at 14 % of frames lost (D4).
2. **Frequencies with their errors; the codec mark at its true width.** `flicker` compares
   frequencies at the resolution 1/T, 7-13 times coarser than what the records know (PR135's
   members: 0.017-0.033 Hz against 0.22 Hz). On the 2-s windows 1/T is 0.5 Hz, and nearly every
   PURSUE clip is IBBBP-coded with its anchor line at 7.5 Hz, so the windows have passed nothing
   from 7.0 to 8.0 Hz -- the middle of the bird band -- on 93 of the 112 sensor videos: PR085's
   bird was refused for it and found again by hand, and the planted beats were moved out of the
   slice, so completeness never showed it. Every frequency gets its error (a bootstrap in the
   record's own residuals, never below the Cramer-Rao bound); the codec mark and `common`'s
   independence become z-tests against it (D1); planted beats go into the slice and its
   completeness is reported, with the analytic completeness beside it (D6). Then the slice's
   worklist is re-run (D3).
3. **The gates decided by evidence.** For each of the astronomer's and the seismologist's
   tests: judged on the goldens (PR135's six, the five flyers, PR41, PR44, PR099), the
   controls (PR23, the balloon, PR055, PR071) and the sweep's own background apertures (the
   false-alarm rate by construction) and planted beats (completeness), each gate goes on, stays
   off, or becomes a reported reading. The bird headline rule -- the whole track beats, or two
   windows that do not overlap pass at one frequency -- is the maintainer's call, pending.
   The decision is made without leakage (D5): a third of the videos, chosen before the gate
   work starts, is not looked at until the gates are frozen on the controls and the rest;
   then they run on it once, and its call rate is reported beside the others'. Each beat claim
   carries its specification curve, and the corpus count its false discovery rate (D7).
4. **The look-alike table on every beat.** The rhythms a sensor chain can make -- the frame
   rate's aliases of 50 and 60 Hz mains and 400 Hz aircraft power, pulldown and held-picture
   cadences, the codec's lines -- marked on every beat the way the codec's lines are now, with
   the clock-steadiness of the beat beside it (a supply's line does not wander; a wingbeat
   does), measured against a clock control: steady beats planted in the record's own noise
   (D2; the Galileo birds and PR135's members wander 2-5 % between halves, more than a clock
   can). The morphology tests for a beat near 10 Hz (its depth along the track, its wander,
   the fixed-core width) written down, since the bird paper's Table 1 has two such objects.
   The table also takes the rhythms of things in the sky, which the infrared survey found fold
   into the bird band at 29.97 frames a second. These are bands, not lines: rotorcraft
   blade-pass at 10-30 Hz (doubled for an odd blade count), turboprop blade-pass at 50-150 Hz,
   a multirotor's rotors (whose folded line wanders by hertz with every correction), flames
   (candles near 10 Hz, puffing at 1.5/√D Hz, so 5-9 Hz for a lantern's fuel cell), and a
   cooled sensor's cryocooler drive. Beside it goes the spectrum of the scene's own
   registration shift at the beat: a cooler's or gimbal's jitter moves the whole frame, and
   a wingbeat does not. Flames are the one per-object, own-phase look-alike that the members'
   phase argument does not exclude; on night clips the report reads `groups`' rigidity against
   it (lanterns drift as a rigid group, a flock rearranges).
   *Status 2026-10-20 (on main, merged from `beat-controls`):* built, as readings (method §18): the bands
   -- the bus as heard, flames, rotors, propellers, a cooler's drive -- the clock-steadiness reading
   (D2), the scene's registration shift at the beat (`--scene-shift`), and a flame's mark said in the
   bottom line with `groups`' rigidity beside it. Still to do: the 10-Hz morphology tests.
   **Open threads from that work, so none is lost** (`docs/history/handoff-beat-controls.md` has each in
   full): (a) merged 2026-10-20; (b) the reference case files do not `share rerun --strict` since
   the merge (new fields) -- accepted until 1.0, remake them on the way there; (c) the
   amplitude floor on the bird headline (below, 0.5) -- deferred until the bird paper's reviews;
   (d) `pictures()`' misreads of two chains outside PURSUE -- tried, dropped, written down (0.8);
   since 2026-10-29 a test that tells a cadence from the encoder's holds, which reaches PURSUE
   too, so it moved to 0.4 (M3);
   (e) the 10-Hz morphology tests for PR077 and PR088's object 2, which the chain-rate table
   left open (PR077: steady as a clock, on 10.00 Hz); (f) a check for a background crossing
   behind the object (0.5).
5. **A second, gain-proof reading: the beat in the position.** A periodic part of a track
   makes its variogram dip at the period (the hole effect). From the track alone, with no
   photometry, the five flyers give their beats within 0.1 Hz. A light-weighted centroid does
   not move when the gain changes, so this reading cannot be made by the camera's gain. On a
   moving camera it needs registration, or members' differences.
6. **The report's grade and checklist.** A quality grade (A-D) by what is constrained; the
   verification checklist beside it (what was excluded, what was not screened out, what could
   not be tested); "possibly not an object" as a stated outcome.
7. **Levels.** "Clipped" as a flat top, not a grey value; the out-of-range share in
   integrity's record; extraction with headroom once the goldens are re-measured. The one
   port that changes a verdict the package already gives (PR135's members sized rather than
   "clipped"), and the smallest.
8. **The reference cases as files.** A `.mcdonald` file in the data folder for every video the
   two papers rest on: PR113 and PR149 (the Technical Note), PR43 (the full paper's third
   case), PR135 and the nine other bird videos of the Scientific Reports Table 1 (PR41, PR44,
   PR077, PR079, PR085, PR088, PR097, PR099, PR141), and PR144 (the method note's clip) --
   marks, tracks, each object's report, and a note saying what to look at. A check that a case
   file reruns to its numbers (open it, run each object, compare the report's fields), so that
   "reproduce our analysis" is one command. The videos the data folder does not yet hold are
   named in its README with their source.
9. **The sweep's tools in the repository.** The scripts the beat sweep was done with (propose
   over windows, pick with a recorded reason, link, flicker, the cadence and frame-phase
   checks, the strict gate) become `tools/sweep/`, so the corpus statement can be re-run by
   anyone with the videos. This is the seed of 0.6's batch mode.
10. **A public project's housekeeping.** The no-data suites on every push and pull request on
   GitHub's free Linux runners; the funder acknowledged in the README; the donation route
   unchanged.

**Hypothesis-driven:** the bird test, finished. **Hypothesis-neutral:** the whole-video pass
with calibrated nulls, and its completeness.

**Could feed:** the Scientific Reports revision (the look-alike and morphology tests; the
thermal-imaging literature the paper does not yet cite, listed in the infrared survey's §8:
wingbeat modulation noted in thermal video since 2006, measured from silhouettes in bats,
birds detected to 3 km in a narrow thermal field); the members' frequencies with their errors,
their wander against a clock, and the corpus count's false discovery rate (the information-theory
survey); a note on the corpus beat census (how many videos beat, and what the search could not have
found).

**Needs:** the maintainer's word on the headline rule and the gates; the nine bird videos
added to the data folder.

## 0.4 -- The unknowns: *k*, *R*, *θ*, *v_own*

The Technical Note's equations: ω = v_px f / k, and ω R = |v_obj − v_own| sin θ. The pixels
give v_px, f and the frame size; a physical speed needs k, R, θ (or the range rate) and
v_own, and no PURSUE video gives the set. This release adds routes to them and bounds that
need none of them, each a measurement with its error and its traps, and makes every report
say where a case stands on each.

**Released as 0.4.0 on 2026-11-01**, as the maintainer cut it on 2026-10-29 (item 8 below): every report-changer, each bound held
against clips of known range, and the 14 reference case files remade and rerun to their numbers. The parallax ladder's fix did not wait
for N. Long's revision: it moved to 0.4.x (the maintainer, 2026-11-01), and was done on 2026-11-02 when the revision came. The rest of this section's open items are 0.4.x.

**0.4.1** (built 2026-11-01/02, released with the next push): the checklist under the conclusion, the parallax ladder's still row and the
aircraft's climb, a phone's clip running (the phone scope's WP0, WP8 and WP3's report line). **0.4.2 is a correctness release with nothing
new in it** (the review of 2026-11-02, decision 11): the biology and single-camera surveys of 2026-11-01 found stated rates that are not
what the code does and a reference case misread, and those land before any addition -- the continuum null's 1 % (B1) and the drift null's
stated rate (B5) in `flicker`; the speed band's 95 % that covered about 70 % (B2, F9), the path speed beside the net speed the report
called the average (B6), and the body-lengths row that was not free of the camera's motion (B7); PR113's picture stretched unevenly, so
its rate is about 103 deg/s on a 40 by 30 degree field rather than 121 on 54 (F1, B8); the bead test's stated 1e-3 (F2); `drift`'s
refusal that read where the fit landed, its crash on 6 or 7 readings and a model wind counted at any height (F4-F6); and the checklist's
camera row, which answered No from the share the first line calls not measured. **0.4.3 is the scene under the sensor's pattern** (B3,
B4, branch `scene`, the maintainer's four decisions of 2026-11-02), after which the reference case files are remade once. The additions
(E2, E3, E6, E14-E17, E20, E22, M6, A16, Av10, Av11, D8, K10, the phone scope's WP1 and WP4 first) are 0.4.x, as cases need them.
**Built on 2026-11-07 (session 18, on branch `s18`; method sections 42, 45, 48, 49, 51):** the phone scope's WP1 and WP4 (a
phone's own record of its zoom as a route to k, checked on the clip's own pictures); E2, E3 and B16 (a change of velocity
dated beyond the track's wander and set against the scene); E6, E22 and E20 (the jitter read without a model, the motion
models that survive as a computed set, and a traffic light for the suites' checks on drawn data); E14-E17 (the pointer as a
stale price, one k from the routes that agree, the zoom as a regression discontinuity, the zoom ladder pooled); and the
single-camera survey's F11 and F12/F41/F51 (the dash read less its neighbours and fitted whole). E15 on real clips is open.
Still 0.4.x: M6, A16, Av10, Av11, D8, K10, the phone scope's WP2 and WP3.

**Objectives.**

1. **k from the camera's own motion -- first.** During a slew the scene moves by the camera's
   rotation: the scene's shift in pixels (`layers`) regressed on the north pointer's change
   in angle (`symbology`) has slope k cos ε, and the intercept and residual carry the
   platform's parallax. A fifth route in `scale`, beside the graticule, the known-size
   reference, the zoom chain and the assumed field of view -- and the first that is a
   measurement rather than an assumption on a clip with no graticule. Validated on a clip
   with a zoom transient (k before and after must differ by the zoom chain's ratio), on the
   slews of the pointer-drawing clips (PR43, PR48, PR060, PR061, PR144, PR148, PR149), and on
   a synthetic pan. Traps: the slew's rate must be large against the parallax rate; a fast
   slew smears the scene, so the usable stretches are the slew's start and end; the
   pointer's convention (true north or the nose) must be known. On wide fields (phone video)
   the rotation-only self-calibration from the frames' own homographies needs no pointer, but it
   needs a lens term: without one it measures an effective focal length (the known soccer camera
   reads 0.41-0.43 of the true f, fitting better there than at the true f, and plumb lines give the
   cause), and with one free the answer holds only to a factor of about 1.4 (the single-camera
   survey, F25). On turrets the lens term and parallax appear to end it by about 7 deg, measured once.
   Four ports from finance for it (the economics survey, 2026-10-28): the pointer's lag
   measured the way a stale price's is (Dimson's summed slope, the Hoffmann-Rosenbaum-Yoshida
   lead-lag) and the slope checked against it, since PR051's upload pointer runs behind its
   data bar (E14); the zoom's ratio as a regression discontinuity, with a bandwidth, a robust
   interval and placebo cutoffs that say how often the fit finds a step where there is none
   (E15); the zoom ladder pooled across a sensor's clips, giving a k with a stated prior on a
   clip where the camera never moved (E16); and one k combined from the routes that agree,
   with its error (E17). The other half of the rotation, from pure mathematics (the
   pure-mathematics survey, 2026-10-29): a camera that pans by δ while it looks down at ε also
   turns about its line of sight by δ sin ε, so the scene rotates in the picture, and k is not
   in it. A rotation fitted per frame pair in `layers` then gives sin ε from the pictures and
   the pointer alone, and k from the shift over Δθ cos ε; and a pan at a steep look down is not
   one translation (12 px between the centre and the edge for 1° at 45°), a candidate cause of
   the slews whose scene groups mix (M6). On the PTZ soccer camera the roll follows the pan
   (r 0.74-0.88) at half the size the dataset's own camera model gives, while drawn pairs read
   it to 0.003°: open, and a turret with a known elevation is the next check.
2. **Range and size without motion.** Sharp-means-far: the defocus bound from the object's
   blur against the scene's, and the bokeh disc's profile and shape. Horizon geometry: a range
   bound for a thing below the horizon, a height for one above it, from the horizon's dip.
   The haze bound for a dark object in daytime: contrast against a daylight sky. The streak as
   a sub-frame light curve and size (PR43). Each with its stated error (the haze bound's is a
   factor of four) and the condition it assumes (focus at infinity, a dark object).
3. **What survives the missing variables.** The admissible region in (R, Ṙ) with the speed
   and size distributions it implies -- the Technical Note's fan generalised into the standard
   figure of a case. The dimensionless numbers reported as facts: the turn radius in body
   widths (neither PR43's nor PR113's object manoeuvred, with no range, field of view or
   platform speed), the smear number, the obliquity from the vanishing point, the parallax
   number. The projective constant-velocity test (a straight image track whose distance from
   the vanishing point goes as 1/(t_z − t)). Edge-crossing fits at the frame's edges, giving
   the product of crossing time and angular rate against angular size. The aspect angle with
   no range: the time to contact τ = R/Ṙ from a resolved object's looming (its angular size
   over that size's rate) or from an unresolved one's light curve (d ln F/dt = −2Ṙ/R once the
   gain is removed) gives θ = atan(ωτ), and the fan collapses to one line -- validated on clips
   whose range is known: Galileo aircraft against a public ADS-B archive (adsb.lol's daily
   dumps, OpenSky's history), the planned encounters of Amazon's AOT set (GPS ranges within
   700 m, closing), and the drift stage's three videos (the Yemen MQ-9's laser ranges, AARO's
   Puerto Rico lanterns from the aircraft's turn, the Santa Barbara hoist from a stored site).
   Each bound of objective 2 is held to the same clips. The citation for the fan's one-sidedness is
   the sonar and IRST literature on bearings-only target motion analysis (Nardone & Aidala
   1981: no range without an observer manoeuvre; Ṙ/R is observable first). `drift.fit_track`
   is that literature's batch fit in angle from a grid of starting ranges (Nardone,
   Lindgren & Gong 1984; in three dimensions Hammel & Aidala 1985), uncited until now. Which motion
   models survive, as a computed set: the model confidence set of a line, constant velocity
   in projection and a turn, with errors that are not independent (E22).
   **And what pure mathematics says of it** (the pure-mathematics survey, 2026-10-29, measured
   on the 46 recorded tracks and on drawn ones; M1, M2, M4 and M5). The projective test held to
   the track's own noise: it now compares its three models only with one another, and 24 of the
   25 recorded tracks it passes miss its model by 8 to 1,078 times their nugget (PR135's members
   "fit, going away"; PR077's object, which loops through 705°, "passes, no closing seen"), so
   "fits" waits on a residual within a few nuggets and otherwise says "describes its trend to N
   px" (M1, first: it changes reports now). The admissible region's extent as the clip's fact,
   and any distribution over it only under a named measure, the invariant one (log-uniform range,
   isotropic direction) beside the uniform one, because the same region is 31 % or 97 % subsonic
   by that choice alone (Bertrand's paradox; M2). The turn as an ellipse, the affine image of
   uniform circular motion, once the arc passes about 150°: the radius in body widths exact, the
   tilt, the turn rate, and the speed and acceleration in body widths with no foreshortening;
   below that the sagitta, with the tilt's band said (the picture's radius 0.15-8.5 times the
   true one; "did not turn" fails for 1-4 % of orientations) (M4). And "no closing seen" as a
   bound on Ż/Z from the band's speed change, since v_end/v_start = ((T + L)/T)² under constant
   velocity (PR23's object under 1.0 % a second, PR149's contact under 4.5 %), with t_z's error
   from the same algebra in place of the residual bootstrap (M5).
4. **A speed with a band for every track.** The track's own covariance fitted (a Matérn
   kernel with a nugget for the centroid's jitter), the instantaneous velocity kriged from it
   (up to 13× tighter than frame differences on the recorded tracks), the average speed's
   honest error, and acceleration as a likelihood ratio rather than a refusal -- validated on
   planted tracks simulated with the fitted covariance. Non-uniform motion described, not
   averaged.
   **Then held to account, as a bank holds its risk model** (the economics survey,
   2026-10-28, measured on the 46 recorded tracks; E1-E4 are one piece of work). The band's
   one-step innovations backtested on its own track -- the share outside (Kupiec), whether the
   misses cluster (Christoffersen), what is left in them (Ljung-Box, ARCH, the tails) -- with
   a traffic light, so a band says when it is not honest and why (E1: 4.87 % outside ±1.96
   against 5 %, but clustered on 20 of 88 axes, and the birds' wingbeat left in the
   innovations). A model-free nugget beside the fitted one, which flags a beat in the track
   (E6: PR135's members 0.39-0.73 of the fitted nugget, PR144 1.00). Jumps named as a glitch,
   an excursion or a step against a simulated false-alarm rate, in place of the one-pass
   4-sigma clip (E4). "Constant" given as an upper bound on the change it could have missed
   (E12). Non-uniform motion dated: a break beyond the wander, tested against the track's own
   covariance, with an interval on its date, and a break common to a group's members dated to
   the frame (E2: 22 of 44 tracks, where `camera.rate_steps` cuts the same tracks into 1,267
   pieces). Each break then set against the scene's change at the same moment, as an event
   study sets a stock against its market, with NO POWER where `layers` holds the scene still,
   as on 13 of the 14 reference case files; for a group, whether the change spreads the
   members more than ordinary moments do (E3: PR144's break at 23.27 s is the camera's slew;
   PR135's six reverse together at 44.556 s with no extra spread, which is what a gimbal slew
   adds to everything in the picture; its north pointer starts to turn then, the way that
   agrees, so how much of the change is the camera's depends on the field of view; the corner
   brackets leave NAR, where it is all of it at a look down of about 30-60°, or the wide
   field, where it is a fifth at most, and the mode is under the redaction). On a bird, the
   band holds the wingbeat as covariance rather than leaving it in the innovations: the Matérn
   times a cosine at the beat beside it, a valid kernel by Schur's product theorem (M8).
5. **What is known, extended.** The platform's speed, heading and altitude, the sensor's
   depression and azimuth, a field of view from a geolocation, a range from a correlated
   track, each entered as a known quantity with its source recorded, so that an outside
   solution (a geolocated terrain, a flight log, a mission report's range) reduces the case
   in the toolkit rather than beside it. The range ratio for a reference object; a stereo pair
   where one exists.
6. **The unknowns ledger.** Every report says, for k, R, θ and v_own: constrained, bounded or
   missing; by which route; and which released datum would close it. The Technical Note's
   census becomes a per-case table that 1.0 sums over the corpus.

**Brought forward from 0.8: held pictures tested, not counted** (M3; the pure-mathematics
survey's census of all 725 videos in the data folder, 2026-10-29). `flicker.pictures` lowers
the beat band's top wherever a tenth of the frames repeat. A rate conversion or a slower sensor
holds frames in a balanced word (Morse and Hedlund's mechanical words), an encoder's holds keep
to its group of pictures, and holds in runs or at random are missing samples, not a slower
clock. So the top comes down only for a cadence on the track's own frames (the least balance
share over windows of 2-12 frames against a random word's, then the held share by GOP place),
with the source's rate and cadence from the slope's continued fraction; otherwise it stays at
the frame grid's, the held frames handed to Lomb-Scargle as missing, as they are now. In PURSUE
211 of the 214 ten-second windows that lower the band today hold no cadence (PR055's sphere, at
16 pictures a second, is the exception); the Galileo flyers' 45-78 % holds are the HEVC
encoder's (their top 24 Hz, not 5-13); three reference case files had the band cut (PR44 to
5.96 Hz, PR141 to 9.5, PR149 to 9.3), with no reported beat changed but PR149's "no beat"
covering 0-9.3 Hz. Clips of known cadence for the tests: PR051's YouTube copy (a 29.97 source
doubled) and the Svanström set's V_HELICOPTER_020-024 (25 on 30). It belongs to the beat, not
the unknowns, and comes in 0.4 because it changes what the reference cases' "no beat" covers.

**Hypothesis-driven:** none; this is the framework. **Hypothesis-neutral:** every bound the
pixels allow, on every case.

**Could feed:** a follow-up note to the Technical Note (what the pixels do constrain, case by
case); the methods paper's kinematics chapter; the reference cases' changes of velocity
attributed to the object or the camera, or said to be undecidable (E3).

**Needs:** the pointer-drawing clips in the data folder; layers' per-template error (the
curvature of its correlation peak) so the regression's weights are right.

## 0.5 -- Controls: what known things look like

Every prosaic class gets what birds got. The order follows the footage.

**Cut small on 2026-11-02** (the review of that day, decision 11), because the workstation 0.6 needs has not arrived and the controls work
already done by hand -- the labelled set's run, the strobe trains, the Santa Barbara and Red Balloon controls, the metallic-orb class --
is where the report-changers have come from. **0.5.0 is:** the controls harness in the suites (the labelled set's tracks in the data
folder and a sampled suite of them, one clip of everything, the saved curves that hold the birds' beats and the non-birds' silence, with
the exact bound beside each control, B28, and the held-out ledger, B17); the bird floor set on a null on sets it has not seen (B24), with
its probability of overfitting (E9) and a challenger (E19); AARO's fourteen resolved cases run blind through `mcdonald run`, the report's
conclusion against AARO's; the report's reason codes (E7) and its grade (S17) beside the checklist 0.4.1 built, and the discriminant
plot they rest on (S20); and levels (V1), the one port that changes a verdict the package already gives. **The rest of this section is
0.5.x**, as footage and hand marks allow: drones, helicopters, aircraft, balloons, flames, gliding and flap-gliding birds, insects, and
the sensor's own artefacts. The harness in 0.5.0 lifts the hold of 2026-10-20 ("waits for the new workstation") for a sampled suite on the
present machine, not the whole set: the maintainer's to confirm.

**Built on 2026-11-07 (session 18, on branch `s18`; method sections 43, 44, 46, 47, 50), every item of the cut:** the
controls harness (`tests/test_controls.py`, 27 controls from saved curves, each with its exact bound; the labelled set's 432
tracks in the data folder and the whole set as a Slurm tool; the ledger of looks), run on this machine as the cut proposed --
the hold's lift for the sampled suite still the maintainer's to confirm; the bird floor set from a null at a stated 1 in 100
(7 %, tested once on the visible-band clips), its probability of overfitting and its challenger; AARO's fourteen resolved
cases run blind (coverage 0 of 14: no public description gives a scale; no disagreement, no false bird); the reason codes,
the grade and the discriminant plot beside the checklist, with the checklist's rows saying only what their tests decided
(the diagnostic-accuracy survey of 2026-11-07); and levels (clipped as a flat top, the clip's levels in integrity's record).
**Released as 0.5.0 on 2026-11-08.** Two surveys of 2026-11-07 -- the air and the sea (W1-W42) and judging a test
(Dx1-Dx40) -- are in IDEAS.md, their rows that change reports marked; six are the maintainer's decisions (the handoff lists them).

**0.5.2 is a correctness patch for `tether`** (the maintainer, 2026-11-10; IDEAS.md's H1-H4), found on 2026-11-09/10 by running the
stage on AARO's known cases and on three PURSUE objects with something under them: it claims pendulums from noise (two released
reference reports, both of birds, carry one), its follower leaves the companion, it reports companions that are scene or
symbology, and it says "nothing tied to the object" of a stem that starts at the object. Nothing new in it; the reference case
files are remade after it. **Built on 2026-11-10** (CHANGELOG, method section 6): the companion found again from where the stack
put it and never followed away, the swing's period held against a slow wander at a rate measured on drawn wanders (1 in 100 at
the worst), the companion gate set against a null (a false companion on 2 of 160 tracks that nothing keeps step with), and the
finding saying the ring it searched. Its version commit is dated 2026-11-10 (the maintainer's word, that day); the Mac and Windows runs,
the tag and the push follow, and the reference case files are remade then. **After it, in 0.5.x:** the test the balloon class had lacked, "does something hang under it?" (H5,
with AARO's known balloon PR-004 and the WA9ONY-5 launch as its positives); `drift`'s corrections and PR051 as a known answer of
its own-track route (DR1-DR5); and `glide` (GL1), once the maintainer has looked at its by-eye controls.

**Classes, signatures and tests.**

- **The labelled infrared set first** (in the data folder: Svanström et al. 2021, 365 clips,
  30 frames a second, 8-bit h264, a box on every frame -- stored as MATLAB `groundTruth`
  objects, which need a one-time conversion before they can serve as tracks). `flicker` on
  every clip, the boxes as tracks: the 79 bird clips (rooks, jackdaws, gulls) give the bird
  test's own miss rate, and the 157 drone, 74 airplane and 55 helicopter clips give its
  false-alarm rate, under conditions close to PURSUE's (AGC'd, compressed, about 5 px for the
  "distant" bin). It also answers whether a helicopter's rotor shows in the light curve at
  all. Run through the scheduler at low priority; the first measurement of this release.
  *Run 2026-10-19 with 0.3.1, in the PURSUE analyses (the Svanström sweep and its README):* the
  labels read with scipy alone (a reader of MATLAB's MCOS subsystem; copy it into `tools/`, do
  not point at it); 432 tracks under both rules. "Beats like a bird" on 24-27 % of bird tracks
  and 3.9-7.8 % of the rest (airplanes 9-15 %, drones 0-4 %, helicopters 9-11 %). The beat's
  amplitude separates true calls from false ones (AUC 0.96: birds' a median 15-18 % of their
  brightness, false ones 1.8-2.3 %); an 8 % floor set on birds and airplanes left 2 of 307
  non-bird tracks called, the held-out drones and helicopters included -- chosen after seeing
  the data, so a candidate gate: fix it, then run it once on sets it has not seen. Deferred
  (Jacob, 2026-10-20) until the bird paper's reviews. Lessons for the harness: tracks are
  1-based (`clip.py`); the camera tracks its target on a pan-and-tilt platform; `pictures()`
  misreads its chain. **The harness itself -- the tracks in the data folder, a sampled suite --
  waits for the new workstation (Jacob, 2026-10-20).**
- **Drones** (footage in hand: four clips of a drone show on the same infrared cameras as the
  flyers, 60 frames a second; 157 clips of three models in the labelled set). Predict first,
  then measure: rotor blade-pass frequencies and where they alias through the frame rate (the look-alike table of 0.3 turned round); a
  formation's rigidity by double-difference separations (or as cointegration of the
  separations, E21, or by the rank of the group's centred positions, which is 3 at most for
  one rigid body, M7) and the group's common motion; the
  choreography (moves in step across the whole group, where birds are out of step); light
  cadences; a steady hover with no beat; the thermal signature of a warm core.
- **Helicopters** (55 ground-based clips in the labelled set; airborne footage expected from
  the same cameras as the flyers): main-rotor and tail-rotor blade-pass rates and their
  aliases (the IR modulation is the rotor rate times the blade count, doubled for an odd
  count, 10-30 Hz); the exhaust plume; size and aspect.
- **Aircraft** (74 clips in the labelled set; more expected likewise): anti-collision strobe
  trains, caught whole by folding the light curve on the pulse period with the strobe as the positive control; navigation lights;
  constant velocity on a straight line; contrails; engine heat.
  *Since 2026-10-21 (on main, merged from `blinks`; method §19; `docs/history/handoff-blinks.md`):* the strobe train is built as `flicker`'s item 13. The flashes are
  read in the brightest and reddest pixels as well as the sum, folded by Z^2 against random sets, and the comb's beat
  is marked. Its positive controls are two Svanström visible helicopters (V_054, V_030), and there were no false
  trains in the other 835 labelled tracks. Run since (2026-10-21, the uap repository's `analysis/sweeps/blinks/`):
  - PURSUE's EO clips (PR49, PR106) and every Table 1 beat: no train. The beats' own brightness curves have no flash at
    all, so no Table 1 beat is a light's harmonic.
  - 21 infrared aircraft with known answers (AARO's resolved aircraft, the Galileo airliners): no train, as expected.
  - Wind-farm obstruction lights are not seen in PR48's or PR058's infrared, so the group reading waits.
  - A black-hot display (hot is dark) is read with `--black-hot` (0.3.3).

  Open:
  - **A visible-band airplane and drone with a light at night, as known answers** (Jacob, 2026-10-21: "possibly").
    - The source is footage taken for it: aircraft near an airport at night, with ADS-B for the type, whose
      anti-collision lights flash 40-100 times a minute (14 CFR 25.1401(c)).
    - A drone needs its light's own rate, measured close or from its maker: 14 CFR 107.29 sets none, only "a flash
      rate sufficient to avoid a collision", visible 3 statute miles.
    - Done when one airplane train and one drone train come out at their known rates, with no new false trains on the
      Svanström set. That is the first real positive for the upper half of the band and for the 180-a-minute overlap
      rule.
  - Flash trains across a group's members (a formation's synchronised lights, a lit wind farm), once a clip shows them:
    a band under 0.6 Hz (L-864 flashes 20-40 a minute) and a reading of whether the members flash in step.
- **Balloons.** The payload's swing (`tether`: a hanging point is a clock; on hold from 2026-10-10, since it
  needs the payload resolved, and taken up again on 2026-11-10, when a known balloon and three PURSUE objects were
  found with something resolved under them: IDEAS.md's H1-H5) and the balloon's recoil against it (tried, parked: every PURSUE
  clip refused it for a stated reason). What remains for a point source: no self-propulsion,
  so motion with the local wind field (`comotion`, kriged within the object's layer); a
  constant angular rate on a straight line; a mylar balloon's mirror in the infrared. The
  honest outcome may be that a point-source balloon has no range-free signature. If so, say
  so, and close it. In the thermal infrared a polyethylene envelope is largely transparent, so
  a balloon may show only as its payload, a compact warm point.
- **Flames: sky lanterns and flares.** The one look-alike that flickers in the bird band
  object by object, each at its own rate and phase (puffing at about 1.5/√D Hz; lanterns
  5-9 Hz). Predicted signature: drift with the wind and a slow climb, a rigid group, a hot
  clipped core, the flame's sharp pinch-off in the waveform. Footage: AARO's Puerto Rico case
  (two lanterns, infrared, airborne) is the one known example in hand. *Since 2026-10-20 (on main,
  from `beat-controls`):* a beat inside a flame's band is marked, and the bottom line says that
  neither the beat nor members out of step clear a flame, with `groups`' rigidity beside it.
- **A background crossing.** The labelled set's one helicopter false call that a floor would
  keep (21 % at 2.1 Hz) was a fence line and poles passing behind it, which background
  apertures 25 px away do not see. Wanted: the scene behind the object's own path, read where
  the object is not -- on a moving camera that needs the scene registered first. Design first.
- **Known answers: AARO's resolved cases.** Every video AARO has published with a stated
  resolution (birds, migratory birds, balloons and a balloon cluster, a foil balloon, sky
  lanterns, Go Fast, and the cases it resolved as aircraft), run blind through `mcdonald run`
  with only what the video and its public description give. The report's conclusion is
  compared with AARO's, and every disagreement is read for which side's evidence is
  stronger. The unresolved videos of the same series join 0.6's catalog runs. The data
  folder's `aaro/resolved_cases.csv` is the manifest, checked by hand against AARO's reports:
  14 videos with a known answer, 2 weak ones (not anomalous, unidentified), 14 unresolved, and
  PR-003 held out (AARO labels it both resolved and unresolved).
- **Gliding and flap-gliding birds.** The flicker test finds flappers and misses gliders by
  construction; seabirds glide most of the time. *A labelled sample for it* (the Svanström run,
  2026-10-19): 39 bird tracks in 35 clips (8 close, 5 medium, 26 distant) where a 10 % beat
  would have been found and none was -- gliding gulls, most likely, unconfirmed -- with the
  same set's no-beat airplanes (58), drones (122) and helicopters (31) as the matched null; and
  8 bird tracks whose own beat sat at 1.7-1.9 Hz, four of them at 1.69, just under the wingbeat
  floor, where a slow wander peaks once the 0.5-s running mean is taken out: slow modulation
  read by the wrong tool. A look at the 13 close and medium tracks confirms or refutes gliding;
  10-s clips are too short for a soaring circle's roll and heading periods (2.5-15 s), and the
  camera's own tracking turns the image's heading away from the bird's. Four tests from the gliding theory: flap
  bouts recurring once per soaring cycle; slow modulation of brightness, size and elongation
  at the roll and heading periods (0.05-0.4 Hz) against a continuum null; circling in the
  ground-stabilised track; skimming with a mirror in the sea. Candidates with long tracks
  (PR098's three-point cluster, whose spacing cycles at 4.6 s; PR061, PR068, PR34 once marked
  by hand); controls to find or to make.
- **Insects near the lens.** The beat alone cannot tell them from birds (an insect's wingbeat
  folds into the same band); the tests that can: defocus growing as aperture over distance,
  platform motion (nothing keeps station beside an aircraft), the Strouhal check of beat
  against size and speed, and the sensor's time constant bounding the true rate.
- **The sensor's own artefacts** -- fixed-pattern defects, the codec's rhythm, held pictures,
  overlay strokes -- are controls already; they join the harness.

**The harness.** One clip of everything, run after every change (the saved-curve harness
that holds the birds' beats and the non-birds' silence now, grown to every class), with the
discriminant plot it produces: the case against the control populations, which the report can
draw and the words "consistent with", "not screened out" and "excluded" can rest on. Its
numbers are held as banks hold their models (the economics survey, 2026-10-28): every rate
over tracks with a bootstrap over videos, since a video's objects are not independent (E10);
each false-alarm rate also in the case's own cell of size, contrast and frame rate (E13); each
gate and floor with its probability of overfitting, rerun after every change (E9), and a
challenger, the simplest rule that could do its job, with the gate's margin over it (E19); a
clip outside the population a gate was set on -- a phone video, a new sensor, another frame
rate -- gets NO POWER from that gate, not a verdict (E5). The report's conclusion then lists
its reasons, at most four, ranked by weight of evidence, as a lender must when it declines
(E7).

**Hypothesis-driven:** all of it. **Hypothesis-neutral:** the discriminant populations.

**Could feed:** a note on a drone show in infrared at 60 frames a second; gliding birds in
PURSUE if a candidate holds; birds, drones and aircraft told apart in a single infrared band
as a methods result.

**Needs:** airborne helicopter and aircraft footage (the labelled set is ground-based,
320×256); hand marks on the long gliding candidates and on the AARO videos' objects;
balloon footage with a resolved payload (a sounding-balloon launch filmed in the thermal
infrared is the calibration still to get).

## 0.6 -- Every frame of every video

The workstation makes whole-video runs routine. This release turns the sweeps that were run by
hand into a command, and spends the new capacity on the one thing that was too costly before:
knowing what the search could not have found.

**Objectives.**

1. **Batch.** `mcdonald batch` over a list or the catalog: every video through Find on every
   frame, link, measure and report; resumable; one folder per video with its objects, its
   index and its `.mcdonald` file; runs as a scheduler array or a local pool; a results table
   over the corpus. What the sweeps produce by hand today. A case file "looked at by a
   person" says how much was looked at: frames drawn at random for the person to check (59
   with no error bound the track's error rate at 5 %), weighted toward the frames that move
   the answer, and samples of what each gate refused (E8).
2. **The workstation.** One worker per core within the memory budget (64 workers need about
   26 GB at 1080p); the next round of the parallel work (integrity's whole-video preamble run
   alongside the rest; the static pattern's large parts; the rule that a pool's job sends back
   small things); whole-video timings in the README's table.
3. **The GPU, used to the full and never required.** Array versions of the band-pass, the
   correlation shift field and the matched filters, the CPU path the reference and the goldens
   run on both, with the move to single precision checked against them. The gain on the
   existing stages is expected to be small; the point is what is too costly on the CPU, and
   that work (the plants, the dense fields, the error models) begins as soon as the
   workstation is on the desk -- 0.4's and 0.5's validation runs are its first customers --
   so that by 0.6 the GPU path is complete rather than begun. On GitHub's runners, which have
   no GPU, the CPU path is what is tested; the GPU path is held to the goldens on the
   workstation.

   *Begun 2026-11-12, the workstation's second day* (`mcdonald.gpu`, `docs/method.md` §52, `tests/test_gpu.py`). The
   three array versions are built and held: the band-pass (the CPU's to the last bit), the correlation shift field
   (the same templates, a pair's agreed shift within 0.0001 px on PR113) and the spot detector's matched filter.
   `layers` and `integrity`'s background passes run on the card, in one process with the frames read ahead by threads:
   a ninth of the time four cores take, a little over half the time all 88 threads take. The correlations were single
   precision on the CPU already, so there was no move to single precision to check; what differs is the transform and
   its order, a few 1e-7 in the maps. The card is CuPy's (NVIDIA, through CUDA; the `gpu` extra), chosen by
   `--gpu`, `MCDONALD_GPU` or Preferences, used inside a batch job only where the job was given it, and only where a
   stage says so. A case says what computed it, and `rerun` measures it again the same way. On GitHub's runners the
   card's code is run with NumPy standing in for it. *Still to do for "complete":* Find and Follow on the card (the
   spot detector's routine is there, the stages still run on pools), `flicker`'s camera-shake pass, `stabilize`, the
   third pass of `layers`; a Mac's card (Metal has no double precision: the routines that sum in double need
   another way there); and the work the card is for -- the plants, the dense field, the error models (objective 4,
   A14).
4. **Planted objects at scale.** `plant`: synthetic objects and synthetic look-alikes written
   into frames and re-encoded with the clip's own settings, through the whole chain (Find,
   link, flicker, report), thousands per clip -- completeness and reliability per video, the
   sweep's negative half with its search volume, and thresholds tuned on the corpus's own
   frames rather than on guesses.
5. **Anomaly ranking over the pass.** Every object of every video on the same axes; the
   defects and blends come out first, and what is left after them is the residue worth a
   person's time. One of everything, kept as a list.
6. **Corpus noise models.** The distribution of every background aperture's spectrum over the
   whole corpus, so a beat's strength is a centile of what the sensors do, not a fixed number;
   past the corpus's largest, a tail p-value by extreme value theory (E24).

**Hypothesis-driven:** the plants. **Hypothesis-neutral:** the pass, the ranking, the noise.

**Could feed:** the corpus statement (how many beat; what was and was not findable).

**Needs:** the workstation; the data folder grown to every PURSUE video.

## 0.7 -- Finding without a hand

The funding plan's first promise: automatic tracking good enough to trust without hand marks.
The window's gate stays -- someone looks at the track sheet, and a report is provisional until
they do -- but the mark that says *which thing is the object* should rarely be needed.

**Objectives.**

1. **The benchmark.** Every recorded track becomes a case: the eleven cases Find is held to
   now, every case file with hand marks, the whole-video pass's objects as weak labels, and the
   maintainer's marks on the long clips. Rank-one rate, link agreement and false-object rate,
   reported with every change.
2. **The methods.** The object as its own template, stitched across gaps and followed by what
   it looks like; the link gate in units of the track's own error, growing with the gap (the
   gate is five to eight times too wide at short gaps now, and too narrow at long ones);
   thresholds set by the frame's own noise with a false-spot rate; chains judged against
   chance; the pathological-motion map, so the sea's glitter is a region with its own
   threshold rather than a thousand candidates; objects held still on a still scene, which Find
   is blind to today; shift-and-stack over a velocity grid for things below the single-frame
   threshold; pickers for appearance and disappearance with error bars; difference imaging with
   a calibrated significance. Two from pure mathematics: spots ranked by their prominence (the
   0-dimensional persistence of the frame's peaks), which no gain curve can change (M10); and
   who is who after a near-miss said with the second-best assignment's cost gap (Murty's
   ranking), "members 3 and 4 may have swapped at frame N" (M11).
3. **Learned proposers, behind the GPU extra.** Point trackers and video segmenters trained on
   ordinary video, used to *propose* tracks, checked against the benchmark, and never the
   judge.

**Hypothesis-neutral:** all of it.

**Could feed:** nothing directly; everything after it.

**Needs:** 0.6's plants for the completeness numbers; the benchmark's marks.

## 0.8 -- The sensor's record, and the displays

*Note (2026-10-20):* `flicker.pictures()` misreads two chains outside PURSUE -- an encoder that
skips a still sky makes fresh pictures look held (the Svanström set, 0.10-0.18 of frames, where
none are), and one that re-encodes held pictures makes them look new (the Galileo Sphere chain,
0.50 for 0.59). Reading holds by the object's own motion lost PURSUE's real ones (PR149) and was
dropped (method §18 has the table). A fix belongs here, chain by chain, each with a clip of known
cadence. *2026-10-29:* the pure-mathematics survey found the fix and the clips (a cadence is a
balanced word; the encoder's holds keep to its GOP), and its census found the misread reaches
PURSUE, so it moved to 0.4 (M3).

Everything the pixels record about the sensor, the display and the file, extracted for every
clip whether or not there is an object in it.

**Objectives.**

1. **The displays.** Readers for the data bar and the mode annunciator where they are not
   redacted (the ATFLIR angle-and-range block in PR111; the MX-15 symbology; the "Tracking"
   overlays), the zoom chain from the corner brackets, the pointer's convention per sensor;
   optical character recognition as a proposer verified by a person; the symbology library
   grows one display at a time, each with its golden. (These are the old roadmap's "mode
   annunciator and data bar".)
2. **The clock.** Frame stamps read; tears and variable frame rate flagged; real times into
   every spectrum and fit. The one port that is a correctness fix; it comes earlier if a
   variable-rate clip turns up. An interlaced source's fields read as samples at twice the
   frame rate, so a beat is heard to the field rate's Nyquist frequency, with interlace found in
   the pixels, since every flagged file in the data folder says "progressive" (M9); and a true
   rate behind an alias from its residues at two clocks, fields and frames or two sensors, by
   the robust Chinese remainder theorem (M12).
3. **Levels and gain.** The comparagram (the gain's map between frames, linear or not); the
   noise level function per clip and the object's grain against it; the shutter's slope bound
   and its correction of beats near the Nyquist frequency; the row-phase test for a screen
   filmed by a phone (the fifth tranche's monitor clips, and testers' own video); block-grid
   alignment and the rhythms of synthesised frames; comodulation per band and window; the
   sensor's self-noise from its own frames; a metrics table and glitch catalogue in
   integrity's record.
4. **Photometry under them.** The point-spread function from a slanted edge where there are no
   points; the sharpening ring and the annulus outside it; brightness through clipped frames
   from the diameter; the ghost test (an object as a scaled reflection of a bright source
   through the optical centre).

**Hypothesis-neutral:** all of it.

**Could feed:** the methods paper (what each test measures and when a clip cannot answer).

**Needs:** clips with unredacted displays in the data folder.

## 0.9 -- The walkthrough and the documentation

The release candidate. Someone who has never seen the package installs it from the docs,
does the basics, and gets the published numbers.

**Objectives.**

1. **The walkthrough.** A set of basic tests a person walks through, each with its expected
   output and pictures: install and `mcdonald setup`; PR113 in two clicks (142 px/frame); PR144
   in the window (Find, Follow, Measure, the report); PR135 with the one button ("Beats like a
   bird"); a shared file sent and answered; the command line as an agent does it. The same
   steps driven by a test (`tests/test_walkthrough.py`), so that the walkthrough *is* the
   platform check on the Linux, macOS and Windows runners and in testers' hands. And
   `mcdonald check`: the smallest known-answer run (a drawn clip with no download, then one
   short real one), for a tester to send back one line.
2. **The docs site.** Recommended: MkDocs on GitHub Pages -- free, kept in the repository,
   built by Actions on a tag, versioned if wanted; readthedocs is free for open source too and
   reads the same Markdown, so the choice can be made late. Pages: installing, the walkthrough,
   the window, the command line and the agent's guide, the methods ("what each number means
   and when a clip cannot answer"), the case-file format, the data folder, contributing, this
   roadmap and the changelog; the API reference from the docstrings. JOSS asks for
   documentation in the repository, not a site; the site is for people.
3. **Housekeeping.** The session handoffs and agent-run logs out of `docs/` into
   `docs/history/`; each release archived by the GitHub-Zenodo integration with a DOI in
   `CITATION.cff`; the JOSS paper (`paper.md` and its bibliography) drafted: statement of need,
   the state of the field, the research it has been used for, and the AI-use disclosure.
4. **Stability.** The case-file format (`mcdonald-share/1`), the commands' JSON fields and the
   report's fields declared stable; anything to be removed deprecated here first.

**Could feed:** the JOSS paper.

**Needs:** testers on macOS and Windows with the walkthrough in hand.

## 1.0 -- The catalog closed

**Objectives.**

1. **A case file for every PURSUE video.** The 126 videos with an object to look at today (the
   112 sensor videos of the Technical Note, the sixth tranche's ten sensor clips, four
   law-enforcement phone videos) and every video a later tranche adds before the release: its
   objects, tracks, report with its grade, its unknowns ledger and its conclusion, made by the
   batch run and looked at by a person, each reproducible by opening the file and rerunning.
   In the data folder, and in a Zenodo data package whose manifest the data folder's
   `SHA256SUMS` is. And `mcdonald share open PR135` fetching the published case from that
   package, so the analysis of any PURSUE video is one command away.
2. **The ideas bank exhausted.** Every port in the bank ([IDEAS.md](IDEAS.md)) shipped, tried and set aside
   with a written reason (as the surveys' "poor fits" sections already do), or deferred past
   1.0 with a reason.
3. **The corpus statement.** How many videos beat; how many are constrained in which
   unknowns; what the releases could and could not have shown, with completeness -- the
   Technical Note's census and the bird paper's Table 1 reproduced by the package over the
   whole catalog. The census weighted by each video's completeness (Horvitz-Thompson), and
   the case files kept as vintages, so that what changed between releases is itself studied
   (E23).
4. **The papers.** JOSS submitted at 1.0 (the repository is eligible from 2027-03-25, six
   months after it went public); the methods paper drafted from the methods chapter; the
   corpus statement as a paper if it earns one.

**Done when:** the data package lists a case file for every video in the catalog; the corpus
tables reproduce from `batch`; JOSS is submitted.

## Beyond 1.0

New tranches as they come (the catalog registers itself; `batch` runs the new videos); other
archives and other sensors (other governments' releases, civilian video, the phone videos,
which are not sensor videos); more than one camera (range by parallax on an array that sees
the same sky; two sites); the methods paper's publication; a tutorial for people who want to
extend the tool; whatever reviewers and users ask for.

## Science deliverables

Papers come when a method gives novel insight into a video, not on a schedule. The rule: a
finding becomes a paper when the toolkit reproduces it from a case file and the controls hold.

| paper | status | fed by |
|---|---|---|
| Kinematic limits (AIAA JAIS Technical Note) | in review | 0.4's ledger for a follow-up |
| PR135's birds (Scientific Reports) | submitted 2026-10-06; reviews pending | 0.3's look-alike and morphology tests, for the revision; the thermal-imaging citations the paper lacks (infrared survey §8); the bird test's miss and false-alarm rates on the labelled infrared set (I1: run 2026-10-19, and the chain-rate table for Table 1's beats, both in the PURSUE analyses; the revision waits for the reviews); the bird-strike record's height distribution for the objects' height (Av2) |
| The corpus beat census | not started | 0.3, 0.6 |
| A drone show in infrared | not started | 0.5 |
| Birds, drones, airplanes and helicopters told apart in one infrared band (the labelled set) | not started | 0.5 (I1, I2) |
| Known answers: the toolkit run blind on AARO's resolved cases | not started | 0.5 |
| Gliding birds in PURSUE | depends on a candidate holding | 0.5 |
| What the pixels constrain, case by case | not started | 0.4, 1.0 |
| The software paper (JOSS) | at 1.0 | 0.9, 1.0 |
| The methods paper (RAS Techniques and Instruments; open-access fee funded) | at 1.0 | 0.4, 0.5, 0.8 |
| Wind-borne drift: the Yemen Hellfire clip, with the Santa Barbara hoist and AARO's Puerto Rico lanterns as controls (Scientific Reports draft, the maintainer's; the uap repository's `manuscript/hellfire_yemen/`) | drafted 2026-10-21, in revision 2026-11-02 | 0.4.0's `drift` stage (§34); its F4-F6 guards and Test 4b's band in 0.4.2; the drift paper cites the installed release; a second screen of PURSUE (2026-11-09/10: DR1-DR6 in IDEAS.md) found one clip its strong tests run on, PR051 from its unredacted upload's data bar |
| Estimation of target kinematics from georeferenced imagery (N. Long, R. Kopparapu, J. Haqq-Misra) | revised 2026-11-01 | 0.4.1's parallax ladder, whose known answers are its Table 2 and Fig. 4 |
| Metallic orbs: at least three classes in the pixels, and the known foil balloon's look (the uap repository's `analysis/corpus/metallic_orbs/`) | a class note, 2026-10-29; not for the drift paper "at the moment" (the maintainer) | 0.4.0's `focus`, `zoom` and `symbology` |
| Cabin sound identifies the aircraft in the Gulf of Oman gunship videos (PR117) | a methods subsection for a longer paper (2026-10-17) | 0.3.0's `audio` (§11) |

## What every release is held to

- The seven suites; golden (the real clips at their published numbers); the published-values
  suite; `tools/find_rank.py --link` on the recorded tracks after any change to Find or the
  link; the controls harness (the birds keep their beats, the non-birds get none) after any
  change to `flicker`; the macOS and Windows runners on the release commit, before the tag.
- A new measurement ships with its method note (what it measures, how it fails, its traps), a
  planted-signal test, a golden, and its false-alarm rate on the controls.
- No number changes silently. A version with every release, written in one place; a patch for
  fixes and small things, a minor version when a theme is done.
- NO POWER stays an answer, and nothing invents detail.
- The two audiences: every feature in both shells, tested in both.
- Plain words in the window; the conclusion first; no pop-ups; boxes as tall as their content.

## Working rules

1. **Public.** Everything in the repository is suitable for public release, and nothing in it
   depends on files outside it but its data folder.
2. **Data.** Footage, goldens, reference outputs and case files -- anything too large for git
   or that users may need -- go in the data folder beside the repository, listed in its
   README with `SHA256SUMS`, and are published to Zenodo with releases.
3. **Research.** Notes, sweeps, manuscripts and the processing of new tranches are worked
   outside the repository, with the PURSUE analyses; what the toolkit should keep is copied
   in, and the toolkit's documents cite a working note by description, never by path.
4. **Compute.** On the development machines every run of the package goes through the job
   scheduler (`tools/*.sbatch` is the pattern), niced; benchmarks from a snapshot of the
   source; never under running tests.

## Decisions

Decided by the maintainer on 2026-10-16, the day the roadmap was written:

1. **When 1.0 is.** The funding plan put a stable 1.0 at six months and the whole catalog at
   twelve; this roadmap folds the catalog into 1.0, so **1.0 lands when the catalog is
   closed**, and the JOSS clock (eligible from 2027-03-25) waits for it.
2. **Docs hosting: MkDocs on GitHub Pages.**
3. **The GPU.** Never necessary for a user to run mcdonald; **plan on using the GPU's capacity
   to the full from the start** (the principle above, and 0.6).
4. **0.4 and 0.5** come in whichever order the footage and the hand marks allow.
5. **Balloons.** The tether and the recoil stay parked; if no range-free signature survives
   0.5, the negative is written down and the class closed.
   *Amended 2026-11-10.* For a single point the negative stands and is written down (IDEAS.md's W9: no range-free
   sign of drifting survives in one track at a clip's scales). The class is not closed: an object with something
   under it has a test, whether it hangs (H5), with a known balloon that passes it and three PURSUE objects that do,
   and `tether` is taken up again, its defects first (0.5.2). The recoil stays parked.

6. **The bird headline rule and the flicker gates** (0.3), decided on 2026-10-17 on the gate
   study's evidence (760 saved curve sets, the held-out third left out): `GATE_ASTRO` and
   `GATE_SEIS` stay off and their tests stay reported readings -- each cost known birds' beats
   (4 and 3 of 27) for no measurable fall in false alarms; and the report names a bird only from
   a beat that comes back -- the whole track beats, or two windows apart agree -- which keeps 25
   of the 27 birds' headlines and drops 17 of the pass's 46 one-stretch calls
   (docs/method.md, sections 7, 8 and 13).

7. **Three of the `beat-controls` branch's questions** (2026-10-20): the reference case files not
   rerunning `--strict` once it merges is accepted until 1.0; the amplitude floor on the bird
   headline waits for the bird paper's reviews; the lantern band's mark stays on the bird beats it
   holds -- a flame is a look-alike mcdonald notes and handles.

8. **Where 0.4.0 is cut** (2026-10-29). Everything that changes what an existing report says
   lands in 0.4.0, before the reference case files' strict rerun: E1's backtest and traffic light
   (with M8 if the birds' bands fail it), E4's named jumps, E12's "constant" as a bound, M3, M4,
   M5's error on t_z. So does a check of each bound against a real clip of known range. The parallax
   ladder's fix was in this list on hold for N. Long's revision, and went to 0.4.x (2026-11-01; done 2026-11-02).
   Everything that only adds goes to 0.4.x: E2, E3, E6, E14-E17, E20, E22,
   M6, A16, Av10, Av11, D8, K10, T16 and the rest of objective 5's knowns. `mcdonald drift`, the
   wind-borne drift stage on its own branch, is merged for 0.4.0, so the version its paper cites
   can be installed.

11. **The review of 2026-11-02** (the maintainer: "Go ahead with all five of those changes"), on a review of this file, the
   progress since 2026-10-16, the fourteen surveys and the case work: (1) **0.4.2 is a correctness release** with nothing new in it
   (the list in the 0.4 section above), before any addition, and the reference case files are remade once after it; (2) **0.4.3 is
   the scene pair** (B3, B4); (3) **0.5 comes before 0.6 and is cut small** (the 0.5 section above: 0.5.0 the harness, the bird floor
   from a null, AARO's resolved cases blind, reason codes and the grade, levels; the classes 0.5.x), the 0.6 to 0.9 order unchanged
   once the workstation arrives; (4) **the ideas bank leaves this file** for [IDEAS.md](IDEAS.md), with a `kind` column that tells
   report-changers, theme work and measured findings apart, and this file keeps each release's objectives and done-when; (5)
   **housekeeping**: all 144 release videos in the data folder (the batch run needs them), the finished session handoffs and agent-run
   logs in `docs/history/`, the merged worktrees and branches removed, and the science-deliverables table brought current. Left as
   they were, on purpose: the 1.0 definition, the JOSS clock, the principles, the working rules, and the rule that a threshold comes
   from a null.

Still open:

9. **The catalog's case files** (1.0): made by the batch run with an agent's picks and the
   maintainer's look, or by hand.
10. **The reference case files after the `flir1` merge** (2026-10-21): `share rerun --strict` on them now
   differs by additions only (the camera stage, `kinematics`' `held` and `noise_px`, the ladder's 0.7 deg
   row, a camera "no power" in the bottom line's count where a track is under 8 frames); no number of
   theirs changes. Decision 7 accepted the same for `beat-controls` until 1.0; whether it covers this
   merge, or the files are remade, is the maintainer's to say. (`camera` stays a stage of `run`: decided
   2026-10-21.)

## The ideas bank

In [IDEAS.md](IDEAS.md) since 2026-11-02 (decision 11), with the two surveys of 2026-11-07 (W, Dx: 82 rows) added: 315 rows at the split -- 62 shipped, 14 report-changer, 198 theme, 39 measured, 1 parked, 1 refused; by release, 21 in 0.3, 32 in 0.4, 2 in 0.5, 22 in 0.6, 26 in 0.7, 63 in 0.8, 7 in 0.9, 1 in 1.0, 12 in 0.4.2, 2 in 0.4.3, 55 in 0.4.x, 12 in 0.5.0, 59 in 0.5.x, 1 in later; the twelve of 0.4.2 shipped that evening; 18 rows of 2026-11-09/10 since (H, DR, GL: 4 in 0.5.2, 14 in 0.5.x). Each row
names the survey it came from and its rank there, the module it lands in and what became of it; a `kind` column
separates the report-changers that go first in a patch release from the theme work of a minor version, and both
from findings measured and kept. The surveys themselves are working notes kept with the PURSUE analyses, outside
this repository. The 1.0 test ("the ideas bank exhausted") reads over that file.
