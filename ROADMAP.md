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
  summarised in the ideas bank at the end of this file; and four clips of a drone show from
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
  workstation with 128 GB of memory and a 16 GB GPU (ordered), two years of the AI coding
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
| **0.5** | Controls: what known things look like | drones, helicopters, aircraft, balloons, gliding birds and insects each with control footage (or an honest note that none exists), a signature test, and its false-alarm rate; the controls harness in the suites |
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
   **Open threads from that work, so none is lost** (`docs/handoff-beat-controls.md` has each in
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
  *Since 2026-10-21 (on main, merged from `blinks`; method §19; `docs/handoff-blinks.md`):* the strobe train is built as `flicker`'s item 13. The flashes are
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
- **Balloons.** The payload's swing (`tether`: a hanging point is a clock; on hold, since it
  needs the payload resolved) and the balloon's recoil against it (tried, parked: every PURSUE
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
2. **The ideas bank exhausted.** Every port in the bank below shipped, tried and set aside
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
| PR135's birds (Scientific Reports) | submitted | 0.3's look-alike and morphology tests, for the revision; the thermal-imaging citations the paper lacks (infrared survey §8); the bird test's miss and false-alarm rates on the labelled infrared set (I1: run 2026-10-19, and the chain-rate table for Table 1's beats, both in the PURSUE analyses; the revision waits for the reviews); the bird-strike record's height distribution for the objects' height (Av2) |
| The corpus beat census | not started | 0.3, 0.6 |
| A drone show in infrared | not started | 0.5 |
| Birds, drones, airplanes and helicopters told apart in one infrared band (the labelled set) | not started | 0.5 (I1, I2) |
| Known answers: the toolkit run blind on AARO's resolved cases | not started | 0.5 |
| Gliding birds in PURSUE | depends on a candidate holding | 0.5 |
| What the pixels constrain, case by case | not started | 0.4, 1.0 |
| The software paper (JOSS) | at 1.0 | 0.9, 1.0 |
| The methods paper (RAS Techniques and Instruments; open-access fee funded) | at 1.0 | 0.4, 0.5, 0.8 |

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

The fourteen surveys' ranked ports, grouped by the release each is scheduled in. The "from"
column is the survey and its rank there (A astronomy, S seismology, T SETI, K kriging and
Gaussian processes, V film and the visual arts, P philosophy of science and evidence, I
infrared observations of birds and other aerial objects, Av aviation: flight test, accident
investigation, targeting, collision avoidance and the bird-strike record, D information theory
and data science, Ac acoustics, E economics, finance and banking, M pure mathematics, B biology, F frame-by-frame analysis in single-camera video, MEO the AARO Middle East Object case of 2026-10-28, `analysis/cases/aaro_middle_east_object`
in the uap repository), so an
entry can be traced back to the note it came from. P12, a check for copied reports among a
release's documents before they are counted as independent, belongs to the PURSUE pipeline,
not here; so do Av1 and Av15, a question and the evidentiary requests for the council.
*Shipped* means on `main` at 0.2.20 with its gate off; *parked* means tried and set aside for
the reason given. New ideas go at the bottom of the release they belong to, with a
"from" of their own.

The information-theory survey's D1-D7 belong to 0.3, and D1
changes results, because the codec mark at the resolution has kept the 2-s windows from passing
anything between 7.0 and 8.0 Hz on the IBBBP clips, which are nearly all of PURSUE.

The economics, finance and banking survey's E1-E24 (2026-10-28) were all put on the roadmap by
the maintainer on 2026-10-29. E1-E4 are one piece of work on the speed band and `camera`,
measured on the 46 recorded tracks, and come first in 0.4; E3 is the one with a case-level
consequence (PR144's break is the camera's; PR135's simultaneous turns get a test). E24 is two
ports, one row each (flap and glide as regimes in 0.5, the noise models' tail in 0.6).

The pure-mathematics survey's M1-M12 (2026-10-29) were all put on the roadmap by the maintainer
the same day. It lends theorems rather than methods: what the group of unknowns leaves unchanged
(Klein), exact characterisations (balanced words), and the rule that "drawn evenly" needs a
named measure (Bertrand, Haar). M1 changes reports now (the projective test's "fits" on tracks
tens of nuggets off it) and comes first; M3 is the one with a case-level consequence (PR149's
"no beat" covers 0-9.3 Hz) and is brought forward from 0.8 to 0.4. Three notes are not ports: a
windowed Schwarzian derivative as a break locator, the pixel-phase line at the frame rate times
the speed's distance from a whole pixel, and Cauchy's projected size in the region's size range.

The biology survey's B1-B45 (2026-11-01) were put on the roadmap the same day, ranked by what changes a report. Six fields were
read and each place tested on recorded data; the claims that would change a report were then rebuilt independently, and "measured
twice" in a row means a second measurement made without sight of the first. It lends checks on the instrument more than methods for
objects. B1, B2 and B5 are stated rates that are not what the code does: a 1 % that runs at 5 %, a 95 % that covers about 70 %, and a
1 % that runs at 8 %, the stage's full rule staying close to its stated rate. B3 and B4 are the largest practical gain, a scene on
clips that say NO POWER. B8 concerns a reference clip's picture and is open. B9 is a reading whose cause is not settled: the
instrument is excluded, and a wing is not shown. What the data refused stays in the survey, a working note kept with the PURSUE
analyses, and not here.

The single-camera survey (2026-11-01; F1-F76, the promising ones below) is the first to ask not what a field can lend but who has
already done this job. It read seven fields: UAP studies, the geometry of a moving point, aerial video, forensic video, the sky's
observers, motion inside a frame, and trackers. Each place was tested on recorded data, and the claims that would change a report
were then rebuilt independently: of 25 readings 11 stood, 11 changed, 2 fell and 1 proved two questions, and all 8 defects were real.
It lends prior art and its citations more than methods. F1 and F2 change reports now: PR113 reads about 103 deg/s on the ladder's
vertical scale, not 121, and the bead test's stated 1e-3 runs at 7.5 % or more. What the data refused stays in the survey, a working
note kept with the PURSUE analyses, and not here.

| release | port | from | lands in | status |
|---|---|---|---|---|
| 0.3 | nulls by scrambled surrogates and time slides; injection-recovery as reliability and completeness | A1 | `flicker`, sweep | shipped; its gate decided off 2026-10-17 -- a reading (decision 6) |
| 0.3 | common-mode removal (the frame's level, the apertures' shared component) | A2 | `flicker` | shipped; its gate decided off 2026-10-17 -- a reading (decision 6) |
| 0.3 | fold-and-difference images at the beat | A3 | `flicker`, `figures` | shipped |
| 0.3 | Lomb-Scargle with the window function and a false-alarm probability; held and lost frames as missing | A4 | `flicker` | shipped; its gate decided off 2026-10-17 -- a reading (decision 6) |
| 0.3 | multitaper spectrum, harmonic F-test, coherence with error bars | S1 | `flicker` | shipped; its gate decided off 2026-10-17 -- a reading (decision 6) |
| 0.3 | the noise as a distribution (per clip) | S3 | `flicker`, `figures` | shipped |
| 0.3 | short records: Sompi frequencies with decay | S4 | `flicker` | shipped |
| 0.3 | the comb, the gliding fundamental, ridge tracking | S6 | `flicker` | shipped |
| 0.3 | phase coherence and the array F-statistic for members in step | S8 | `flicker` | shipped |
| 0.3 | one-bit second reading | S11 | `flicker` | shipped |
| 0.3 | the beat as a damped oscillator against red noise; its stability over time | A17 | `flicker` | to do |
| 0.3 | the look-alike table per clip (frame-rate aliases of mains, aircraft power, pulldown, held pictures) | T1 | `flicker`, sweep | shipped 2026-10-16 (`flicker.lookalikes`, docs/method.md section 9) |
| 0.3 | the 10-Hz morphology tests (depth along the track, wander, fixed-core width) | T2 | analysis, then `flicker` | to do |
| 0.3 | trail OFF and in-gate OFF apertures | T3 | `flicker`, `layers` | to do |
| 0.3 | the beat's footprint fitted on the fold (compact and centred, or a row, column or line) | T5 | `flicker` | to do |
| 0.3 | the verification checklist in the report | T10 | `report` | shipped 2026-11-01 as the checklist under the conclusion (`Case.checklist`): each test a question in plain words, answered Yes / No / Partly / Can't tell / Not yet, why in a line; the window's card has the same rows. Ravi's ask. The grade (S17) and Louange's items (F56) still to do |
| 0.3 | clock-steadiness of a beat | T11 | `flicker` | on main since 2026-10-20 (from `beat-controls`): `steadiness`, as D2 |
| 0.3 | the beat in the position (the track's hole effect) | K2 | `flicker`, `groups` | to do |
| 0.3 | a quality grade A-D on the report and the lists | S17 | `report`, `several` | to do |
| 0.3 | levels: clipped as a flat top; range and out-of-range share; extraction with headroom | V1 | `forensics`, `integrity`, `clip` | to do |
| 0.3 | "no beat" as a likelihood ratio, (1 − α)/(1 − c), from the planted beats and the controls at a bird's expected amplitude; untestable is a ratio of about 1 | P1 | `flicker`, `report` | to do |
| 0.3 | the lot, listed: the hypotheses each conclusion compared and the classes it did not consider; a table of observed properties against hypotheses | P2 | `report` | to do |
| 0.3 | weight beside the verdict: the share of applicable tests that had power, computed by the tool, never by the analyst | P3 | `report`, `several` | to do |
| 0.3 | the readings' independence: which inputs each beat reading shares; "robust" only across readings that share none | P4 | `flicker`, `report` | to do |
| 0.3 | the auxiliaries each hypothesis needs: measured, as given, assumed, or a rescue with or without independent support | P5 | `report`, case file | to do |
| 0.3 | a gated verdict states its gate and the value at which it would flip | P6 | `report` | to do |
| 0.3 | every printed number with its measurand and its model's inputs (an audit) | P11 | `report`, `several` | to do |
| 0.3 | the sky's rhythms in the look-alike table, as bands: rotorcraft blade-pass 10-30 Hz (odd blade counts doubled), turboprop blade-pass, a multirotor's wandering lines, flame puffing at 1.5/√D Hz, a cryocooler's drive; with the line's wander | I2 | `flicker.lookalikes` | on main since 2026-10-20 (from `beat-controls`): `LOOKALIKE_BANDS`, with the 400-Hz bus as heard |
| 0.3 | the scene's registration shift: its spectrum at the beat (a cooler's or gimbal's jitter moves the whole frame) | I3 | `forensics.shift_field`, `flicker` | on main since 2026-10-20 (from `beat-controls`): `flicker --scene-shift`, Lucas-Kanade, not `shift_field` |
| 0.3 | rigidity read against lanterns on night clips (a lantern group drifts rigid; a flock rearranges) | I10 | `groups`, `report` | on main since 2026-10-20 (from `beat-controls`): the bottom line, wherever a flame's band marks a beat |
| 0.3 | Johnson's criteria before any shape word: line pairs beyond the clip's point-spread floor (detection 1.0, orientation 1.4, recognition 4.0, identification 6.4); below orientation the only shape is the optics' | Av4 | `forensics`, `report` | to do; the floor from the clip's smallest object until V9's PSF |
| 0.3 | the accident investigator's tests in the hypothesis table: existence, influence and importance for each class, the influence checklist as its auxiliaries; the verbal probabilities fixed once on the IPCC scale ("likely" above 66 %) | Av5 | `report`, docs | to do, with P2, P5, P6 |
| 0.3 | every frequency with its error (a bootstrap in the record's own residuals, never below the Cramer-Rao bound); `peak`'s codec mark and `common`'s independence as z-tests against it, not the resolution 1/T, which blinds 2-s windows from 7.0 to 8.0 Hz on 93 of 112 sensor videos; planted beats placed in that slice and its completeness reported | D1 | `flicker` | shipped 2026-10-17 (`hz_error`, `at_line`, `common`'s `apart_z`, `sliced`; docs/method.md section 12) |
| 0.3 | steadiness against a clock control: the halves' frequency difference against steady beats planted in the record's own residuals (a codec, mains or mechanical line is a clock; a wingbeat wanders 2-5 %); NO POWER on short records | D2 | `flicker` | on main since 2026-10-20 (from `beat-controls`), with T11 and I2; A17 to do |
| 0.3 | the codec slice's worklist re-run through D1 and D2, the continuum null and the planted-dot control: PR085's other bouts (o02, o04, o08, o11), PR098's four (o06, o08, o09, o58), PR084 o05 | D3 | sweep, cases | done 2026-10-17, through D1, the continuum null and the encoding control (D2 waits with objective 4): by the stage's rule none is called -- the codec mark was not what refused them, their windows fail the background's floor; by the paper's rule seven are (PR085 o04/o08/o11 beside its 7.37-Hz bird, PR098 o06/o08/o58), candidates for a look; written up with the PURSUE analyses |
| 0.3 | lost frames by mechanism: lost-or-not regressed on the background at the predicted position, the object's level and its beat's phase decides keep or drop; a censored (Tobit) fit for the amplitude where the troughs are kept | D4 | `flicker` | to do, with objective 1 |
| 0.3 | the gates chosen without leakage: a held-out third of the videos fixed before the gate work, the gates frozen on the controls and the rest, run once on it; a specification curve (apertures, detrends, windows, the lost-frame rule, the photometry) for each beat claim | D5 | process, sweep | held-out third drawn 2026-10-17 (`tools/sweep/holdout.tsv`: 42 of 126, by release, a hash anyone can repeat); the specification curve to do, with objective 3 |
| 0.3 | analytic completeness from the error exponent (the frames a beat of given amplitude needs in the clip's noise) beside the planted beats, as a check on them | D6 | `flicker`, `report` | shipped in `flicker` 2026-10-17 (`analytic`, in the fields and `mcdonald flicker`); a sentence in the report to do |
| 0.3 | a false discovery rate across the pass on per-object p-values (one per video, or Benjamini-Yekutieli) | D7 | sweep summary | to do |
| 0.3 | the verdict hides a beat behind the drift. The headline reads the single strongest peak, which on a held target is often a slow 1.5-3 Hz wander. The line then gets judged by one rule, 3x the median of the background apertures' strongest peaks, while the battery (continuum null, Lomb-Scargle, multitaper F, one-bit, the background's own windows, coherence) says yes. Wanted: a line search per band (the wingbeat bands, as the look-alike table has them), each line judged against the same search on the background apertures pooled over the clip, so the band is paid for; the verdict to come from the battery, with the 3x rule as one item in it and not the gate; the report to name a line under the headline when one band holds it. Case: uap PURSUE PR089, PR088's bird C continued. Frames 481-720: 10.50 +- 0.02 Hz at 4.4 %; continuum null 0.001; LS false alarm 5.6e-3; multitaper F chance 4.3e-4; windows at the background's 100th centile; not coherent with the scene. Verdict "no beat", because 3x needed 5.4 %. On 11 main-object segments the headline peak was a 1.5-3 Hz drift, and C's 9.7-10.8 Hz line (14.7-31.8x its continuum, beyond the clip's pooled background null) was found only by the band search. Uap `analysis/cases/pr089/README.md`, `analysis/tools/pr089_c_envelope.py` | uap PR089, 2026-10-23 | `flicker`, `report` | to do |
| 0.3 | the aperture for a faint or smeared point: a size reading the sea cannot inflate, and a disc near the point default. (1) `extent` on single frames fails on a faint, smeared object over banded sea: on PR089's bird C after a sensor blank it read nothing on 7 of 11-12 frames and 43-66 px on others, so `sizes` gave a 48-50 px radius and a 58-60 px aperture to a dot 5-9 px across, and nothing could be measured. Wanted: the size read on the median of the object's stamps over the track (`stamp`), across its direction of travel so a smear does not count, and a reading that is mostly missing or scattered said and replaced by the point aperture. (2) For a point-like thing (extent <= ~10 px) the disc that hears its beat best is often near APERTURE rather than APERTURE_OVER x extent -- a choice per stretch, or a small set of discs paid for as trials, may be the right form: C's real 10.5 Hz line over its continuum, disc 4 / 5 / 8 px, 45.4x / 42.3x / 29.8x (frames 1-720), 30.5x / 35.4x / 38.5x (918-1422), 14.9x / 16.1x / 13.5x (1659-2072); after the blank a planted 4.5 % beat clears the clip's null 90 / 75 % of the time in 4 / 8 px on one stretch and 50 / 0 % on another, but 17 / 60 % on a third, so the best disc varies and 8 px is not always worse. Tried and rejected: a capsule shaped to the smear (radius 2-3 px, the measured 8-11 px tail behind), worse than the 4-5 px disc on every stretch (best 27.4x on 1-720), and a fixed 12-px disc. It changes the numbers the default aperture gives, so (2) waits for Jacob's decision; (1) is a fix. Uap `analysis/cases/pr089/README.md` ("The aperture for C"), `analysis/tools/pr089_aperture_sweep.py`, `pr089_aperture_eval.py` | uap PR089, 2026-10-23 | `flicker`, `report` | done in 0.3.9. (1) merged to main 2026-10-24 (8bdc21b). (2) built on branch `rcap-floor` (eddc582, 4ed4b86, 672fe60; unmerged): the disc capped at POINT_DISC 6 px for an extent over 5 and under 10 px (Jacob: 10, so PR41's 10-px bird keeps its 12-px disc and its 11.6 % beat), on the smoothed track, the ring and background apertures beyond 1.2 x the extent; a bird named only from a beat of BIRD_FLOOR 8 % or more (fixed before the test). Held-out test (uap `analysis/sweeps/svanstrom/README.md`): known-beat birds named 15 -> 19 of 38, Svanstrom birds 30 -> 28 of 125, false calls 12 -> 2 of 307, held-out non-birds none; all suites and golden pass. Rotor look-alike note built 2026-10-25 on branch `rotor-note` (on rcap-floor; flicker item 14, `beat[..]["rotor"]`, report's bottom line): coherence with the background at the beat >= 0.75 or the fold's offset >= 3.5 px, 6 of 8 helicopter calls, 0 of 30 + 1 of 20 birds; said, not gated -- to be held to helicopters it was not chosen on. Merged to main as 961441d (2026-10-25). Re-measuring PR089 on it (uap `analysis/cases/pr089/README.md`, "Re-measured with mcdonald main 961441d") found C called on two stretches 0.3.8 called none, and the 6-px disc lifting its beat's folded double (30 - 21.0 = 9.0 Hz) over the beat, which the stage then named; fixed (98f2cc4: a strongest f with a peak of its own at (fps - f)/2 is that beat's folded double). All of it released in 0.3.9 |
| 0.3 | the look-alike mark's base rate beside it: the share of the bird band that carries a mark at the clip's frame rate, so a mark is read as the weak evidence it is | E11 | `flicker`, `report` | to do, 0.3.x; measured 2026-10-28: 70 % of 1.5-12 Hz at 29.97 and 30 frames a second, all of it at 59.94 and 60 |
| 0.3 | the factor count for common modes (the Marchenko-Pastur edge, Bai-Ng's criteria) in place of the fixed `COMMON_K` = 2; the scene's number of independent motions | E18 | `flicker`, `layers` | to do, 0.3.x |
| 0.4 | k from a slew: the north pointer against the scene's shift | V2 | `scale`, `symbology`, `layers` | built 2026-10-19 (`mcdonald slew`, method §17; merged to main 2026-10-20, unreleased): synthetic pans within 7 %, PR148 NO POWER (glyph unreadable at the slew's start, a hold that is not steady); the known-answer test on a clip with the sensor's azimuth and field in its data bar (PR051) and the other pointer clips to do. Zoom states merged to main 2026-10-21 (`mcdonald zoom`, unreleased): windows cut at every blank burst, claims compared within a state, and across a measured step the ratio of c against the imagery's -- the objective's "validated on a clip with a zoom transient": PR27 267 -> 517 px/deg across x2.000, PR057a 276 -> 584 across x2.001, both agreeing (`tools/zoom_check.py`). PR051's known answer (2026-10-28, the data bar read every 0.5 s): its upload's pointer is a dial drawn in 0.2-0.5 deg steps that runs up to 0.6 deg behind the bar's azimuth and catches up (0.11-0.17 deg rms against it), too coarse frame by frame for the slew's lever in NAR's 11 s: NO POWER is right; its scene moves on, and `layers` loses the jumps of a picture that repeats (see the handoff) |
| 0.4 | focus: sharp-means-far; the defocus disc's profile and shape | V5 | `forensics`, `kinematics` | sharp-means-far built 2026-10-27 (`mcdonald focus`, method §28): rendered points and a defocused disc; the near-thing test built 2026-10-28 as the edge with the core's paleness (MEO11, branch `metallic-orbs`, merged 2026-10-29); a real clip with a known range, to do. A step of `run` (and the window's plain form, "What kind of camera was it?") since 2026-10-29, started by the camera's band |
| 0.4 | horizon geometry: range below it, height above it | V12 | `kinematics` | built 2026-10-27 (`mcdonald horizon`, method §27): the line found from a point and followed, both bounds at their band's conservative corner (refraction 0-0.25); closed forms and rendered scenes; a real sea horizon with a known height and range to do. A step of `run` (and the window's Measure form) since 2026-10-29, where a height and a point on the horizon are given |
| 0.4 | the haze bound for dark objects | V15 | `kinematics` | built 2026-10-27 (`mcdonald haze`, method §29): linear light (BT.709), the visibility or a reference in the frame, a factor of four; rendered frames; a daytime EO clip with a known range to do. A step of `run` (and the window's Measure form) since 2026-10-29, where a visibility or a dark reference is given |
| 0.4 | the streak as a sub-frame light curve | V14 | `forensics`, `flicker` | built 2026-10-27 (`mcdonald streak`, method §30): the exposure from the dash, beads tested as an F ratio against the lines beside it; rendered dashes. PR43 read 2026-10-28 (its case file's track, frames 50-75, 12 dashes): exposure 11.5 ms, 0.34 of a frame, at the default 2-px blur; no beads (134 Hz at 3.8x, false alarm 5.8e-3). With the clip's own blur measured (2026-10-29): 3.6 px from 43 of its points, and the blur taken back exactly (`streak.motion_px`; subtracting it whole had read every dash short): 15.6 ms, 0.47 of a frame (14.7 at 2 px; 12 ms by the medians' ratio, the centroid's jitter spreading the frames' speeds); under three of its own blurs, no light curve, so the bead search made at 2 px does not stand. `streak` reads the blur off the scene by default |
| 0.4 | the admissible region in (R, Ṙ) with sampled speed and size distributions | A10 | `kinematics` | built 2026-10-28 (`kinematics.admissible_region`, `Case.admissible`, `figures.admissible`; method §33): the stages' range bounds, a speed cap (Mach 3), the size through k and the extent, τ's line; drawn evenly for the speed, aspect and size the clip allows; `<tag>_admissible.png` among the report's figures where ω is known |
| 0.4 | edge-crossing fits: crossing time times angular rate against angular size | A16 | `kinematics` | to do (needs the frames at the edge and a track that reaches it; method §33, not built) |
| 0.4 | the time-distance diagram along the track | A13 | `figures` | built 2026-10-28: the lower panel of `<tag>_speed.png` (the distance run from the kriged rate, its band, the average's line, the track's own path) |
| 0.4 | the dimensionless numbers (smear, turn, obliquity, parallax) and the projective constant-velocity test | the kinematic notes | `kinematics`, `report` | built 2026-10-28 (`projective.py`; method §33): the projective test with t_z, T, v ≈ R / T and the aspect angle from the vanishing point with k (the obliquity), the turn radius in body widths on a sourced scale, the smear number -- rows of the summary and a paragraph of the bottom line; PR43 passes the test (T 0.91 s, 35° at 65.6°) and did not turn (about 1,900 body widths). The parallax number is `comotion`'s to give (to do) |
| 0.4 | v(t) with a band; the average speed's honest error; acceleration as a likelihood ratio | K1 | `kinematics`, `report` | built 2026-10-28 (`kriging.py`, `kinematics.speed_band`; method §32): a line, a Matérn-3/2 wander and a nugget by REML on each coordinate; the rate at every frame with its sd, the average over the stretch with its error, the velocity's change over the stretch with its sigma, the likelihood ratio against a line with white jitter; a not-uniform track described in the report instead of refused; `<tag>_speed.csv` and `.png`. On the recorded tracks the nugget is 0.1-1.5 px and the band 2-9x tighter than the scatter of single pairs of frames; PR43's streak 12-31 px/frame against the Note's 7-33 |
| 0.4 | conditional simulation: planted tracks with the measured covariance | K8 | tests | built 2026-10-28 (`kriging.simulate`, `kinematics.simulate_track`: the wander and its rate drawn together, a velocity and an acceleration on top; `test_reduction`): the band's ±2 sd holds the drawn rate 94 %, the average's z unit, no false alarm on sixteen lines with jitter, a planted 200 px/s² seen every time. Unconditional so far; conditioning on a recorded track (a planted object on a real path) with 0.6's planting tool |
| 0.4 | each template's own error from its correlation peak | K9 | `layers`, `comotion` | built 2026-10-28 (`forensics.peak_information`, `weighted_shift`; method §31): the peak's curvature calibrated on drawn textures, a template sure only across its streaks counted across them, the pair's error in the layers CSV and along `slew`'s chain; the same day, the vote of the templates sure only across their streaks where fewer than three are sure both ways (`consensus`, `VOTE_LEAD`), the field with zero left out read first from the one search, a tinted picture no longer masked by its tint: PR051's chain whole over 4.5-13.5 s at 0.91-0.93 of its data bar, every pair measured |
| 0.4 | the object's track regressed on the scene's shift (how much of the motion is the scene's) | K10 | `integrity`, `comotion` | to do |
| 0.4 | turbulence as a witness of range | T16, F61 | `groups` or new | refused 2026-11-01 (the single-camera survey): jitter rises with range on aircraft of known range (rho 0.53) and a spot drawn through the clip's own codec does the same; the excess does not rise (rho -0.004, p 0.88, 97 windows), on AOT it is flat at 2.4-3.2 px from the flying camera, and on Svanström's distance bins it falls (rho -0.10). The air predicts at most 0.03 px on these lenses and, on a slant path, no range: variance at 20 km is 1.1 times that at 2 km. Near-horizontal paths on a long lens stay untested |
| 0.4 | τ from looming or from the light curve; the aspect θ = atan(ωτ) with no range; validated on Galileo aircraft with ADS-B | I6 | `kinematics` | built 2026-10-28 (`kinematics.looming_fit`, `tau_from_light_curve`, `aspect_from_tau`; method §33); fed by the flicker stage since 2026-10-29 (`flicker.tau_reading`, `kinematics.tau_of`: the size and the ring's level on every frame, the looming law with the blur's offset, rules set on drawn series and the 31 objects of the reference case files, none of which claims a tau; the light curve conditional only), into the case (a summary row, θ from τ and the rate at the last frame in the ledger, τ's line in the admissible region, the card's "Time to the camera"); held on rendered approaches through the stage; the Galileo aircraft wait for the ADS-B data Jacob has asked for |
| 0.4 | a turn as a load-factor curve, n = √(1 + (ωV/g)²): the turn rate from the track, the speed unknown, against each class's limit | Av10 | `kinematics`, `figures` | to do |
| 0.4 | speed in body lengths per second with a sourced class table (aircraft types, the DoD drone groups, birds); for an unresolved object, blur widths per second as its lower bound | Av11 | `kinematics`, `report` | to do |
| 0.4 | the value of information per unknown, per clip: how much knowing k, R, θ or v_own would change the report's answer (e.g. P(v < 30 m/s)); the council's asks ranked by it | D8 | `kinematics`, `report` | to do |
| 0.4 | `integrity`'s zoom across each transient fitted by `forensics.zoom_fit` (the whole picture, the overlay zeroed, the scale by prominence, "unknown" where it has not found it) in place of `zoom_ratio`, which looks within 60 px of the boresight and read x1.0 at every switch of AARO's Puerto Rico clip | the zoom handoff (`docs/handoff-zoom-slew.md`, Open) | `integrity` | done 2026-10-27, the maintainer's decision (`integrity.transient_zooms`, through `zoom.fit_all` and `zoom.confirm`): PR144's x5.8 kept (x5.804 at ZNCC 0.87, by the new strong-fit rule), its other transient no step |
| 0.4 | a marginal zoom fit made trustworthy by a second, independent pair of frames either side (a frame or two further out) agreeing on the scale, without lowering the bar for traps: Puerto Rico's 142.6-s switch fits x1/3.096 (the readout's 1/3) but leads the next scale by only x1.14, as PR27's 89-s haze trap does | the zoom handoff (`docs/handoff-zoom-slew.md`, Open) | `forensics`, `zoom` | done 2026-10-27 (`zoom.confirm`): two of the pairs 1-3 frames out must pass every rule on their own and agree within 3 %; Puerto Rico's 142.6 s a step, PR27's 89-s haze (x3.127 from every pair) unknown. With it a strong fit (ZNCC >= 0.5, twice its rival's) leads whatever the prominences (PR144) |
| 0.4 | the PURSUE pointer sweep re-run with `slew` and its zoom states, in place of the uap repository's `pointer_slew_states.py`: every clip's states, its claims per state, and the c-ratio check at each measured step (the fixed-FOV-ladder question, x2.00 and x5.8-5.9 so far) | the zoom handoff (`docs/handoff-zoom-slew.md`, Open) | sweep, `slew`, `zoom` | done 2026-10-27 (`tools/pointer_sweep.py`, 127 clips): 95 measured steps of 573 bursts, the ladder x2.00 (45) and x5.9 (18), then x2.33 (9), x3.13 (3); slew's claims PR27 267 -> 517 and PR057a 276 -> 584 (each agreeing with its imaged x2), PR134 205, PR101 141 (to be looked at); PR076's refused |
| 0.4 | `slew`'s figure as one row per zoom state (the windows of a state together, the c-ratio check across each step) in place of one row per window, which is 64 inches tall on PR27 | the zoom handoff (`docs/handoff-zoom-slew.md`, Open) | `slew`, `figures` | done 2026-10-27: a row for the clip (the scene's path, the boundaries, each state's c), then a row a state (PR27's 20 inches, from 64) |
| 0.4 | `camera` and `zoom` read each other: `zoom`'s measured steps given to `camera` as events and taken out of a track as zooms; `events`' picture steps given to `zoom.plan` as its bursts | the camera handoff (`docs/handoff-camera.md`, Open) | `camera`, `zoom`, `events` | done 2026-10-27: `camera --zoom` (and `run`'s camera stage) takes the imagery's steps out of a track and checks them on the object; `zoom` fits the picture's steps with no blank (`events.picture_steps`, `zoom --events`): PR051's leak x0.498 against its data bar's x1/1.999. FLIR1's no-blank zoom is not found by `zoom` (its sky steps neither level nor contrast); `camera` finds it from the object |
| 0.4 | the released-track null on a second clip, one with a lock loss and a readable line-of-sight rate before it: in PURSUE only PR051 (the MTS-B breaks lock, and its north pointer gives the azimuth at unit gain) | the camera handoff (`docs/handoff-camera.md`, Open) | `camera`, `slew` | done 2026-10-28 on PR051 (`camera --scene`, method §20): the ground held still while the gate held the object, so the camera was not turning against it; the object then crossed the ground at 0.0079 deg/s for 1.8 s and became a dash at 0.11 deg/s, the camera unmoved at either, so the release explains neither (golden `test_pr051_released_track_against_the_scene`). GIMBAL and GOFAST stay locked, PR111's azimuth is redacted |
| 0.4 | the parallax ladder's nearest height for a still object: `kinematics.parallax_ladder` gives `own_speed_needed_m_s` as \|v_G + (k − 1) v_A\|, which is k v_O, the ground point's residual, not the speed the object needs of its own (v_O = \|v_G + (k − 1) v_A\| / k), and it picks the k that makes that residual smallest, not v_O. On PR043 with N. Long's homography (Table 2: v_G 2350 m/s toward 69.6°, aircraft 76.4 m/s on 272.7° at 1611 m) it prints "922.0 m/s of its own" at k 29.29, where the object needs 31.5 m/s [29.1 m/s at k 34.3, 1564 m: 31.5 is 922/29.29, the speed at the old k, not the least over k]: it overstates the case against a slow or still object by the factor k. Fix: divide by k, take the k that makes \|v_G + (k − 1) v_A\| / k smallest, correct the docstring's "\|v_G\| sin(the angle off)" to match, and add a test with a known v_O. Known answer for the test: the ladder's other rows reproduce Long's Fig. 4 (30 m/s of its own at 1559–1569 m, his "bird above 1560 m") | Long's homography draft (2026-10-28) | `kinematics` | done 2026-11-02, after Long's revision (2026-11-01; Table 2 and the PR043 heights unchanged): `closest` is the least \|v_G + (k − 1) v_A\| / k in closed form (the nearest point to zero of the segment from v_A to v_G), with its height; PR043 29.1 m/s at 1564 m, where it printed 922.9; `k` None where the ground moves the aircraft's way and faster (PR023 on the same table: no nearest height, never under the aircraft's 6.54 m/s). The other rows against his Fig. 4: 30 m/s at 1559 and 1568 m, Mach 1 at 1338 m (his 1340), Mach 5 at 432 m (his 434). `test_reduction.test_the_parallax_ladder` holds all of it and an object built to move 10 m/s at k 4 |
| 0.4 | the stare's moving-things picture: over a stretch where the ground holds still, each frame minus the median, darkest and brightest kept. The object's own shadow, if it flies low, draws a second trail beside its own; with the sun's direction, the heights at which it would show are a bound (the Middle East Object: one trail only, so not within about 10 m of the ground) | MEO3 | `forensics`, `kinematics` | to do, with MEO7 |
| 0.4 | the sun from a shadow: three marks on a vertical caster (its top, its foot, its shadow's tip). The tip-to-top line is the sun's direction on the picture, with no camera model; with the depression (read, or swept) it gives the sun's height, and with the north pointer its bearing. Then, for each object: is its bright side the sun's, and what share of a matte ball would be lit at that phase angle? (The Middle East Object: lit side predicted at 325-341°, seen at 316°; a matte ball would be 72-95 % lit, the object is mostly dark) | MEO7 | `mark_qt`, `kinematics`, `report` | to do |
| 0.4 | the depression from right angles on the ground: two adjacent edges of a horizontal rectangle (a roof, a container's rim, a compound's walls) marked, refined on the brightness step, and sin² e = −tan α₁ tan α₂ once the roll is out. An oblique rectangle gives e almost free of the roll, an aligned one gives the roll, so the two together test the display's horizon line as the roll. A route to objective 5's depression from the pixels; its error, and the foreshortening by sin e, carried into every bearing read off the ground (the Middle East Object: e = 24.0°, 16-84 %: 23.4-25.0°, from a container; the horizon line held as the roll to 0.1°) | MEO10 | `scale`, `mark_qt`, `kinematics` | to do, with MEO7 |
| 0.4 | the depth-of-field bound against a like reference (V5 made concrete): the object's blur fitted with an exact blurred-disc model (a noncentral chi-square, its clipped core left out), on the side away from any bright patch and across its motion; the same on a compact, dark, in-focus thing in the same frames (a person), never on an edge that may not be a step. Reported two ways: assuming nothing of the camera's blur (b ≤ 4σ_obj) and assuming the reference's (b ≤ 4√(σ_obj² − σ_ref²)), as r/R ≥ 1/(1 + b s/A) against the aperture, with the two biases named (coding softens movers; turbulence blurs only the ground). The Middle East Object: as sharp as a person on the road (σ 1.30-1.42 px against 1.45); r ≥ 0.17-0.32 R at A = 10 cm | MEO11 | `focus`, `kinematics` | built 2026-10-28 on branch `metallic-orbs` (`focus`'s edge, method §28): the scene's points stand in for the like reference, and the core's paleness closes the small-thing-far-out-of-focus trap; the Middle East Object reproduced (σ 1.27); with no points the bound assuming nothing alone (PR062); to do: a marked reference (a person), the ground's edges along the streaming as the reference where points smear (PR062, `orb_edge_reference.py`), the defocus-over-image bound D ≤ A × image / disc, and softness against size as the object's distance changes |
| 0.4 | the band backtested on its own track: the one-step innovations (the residuals whitened by the fitted covariance), their coverage (Kupiec), clustered misses (Christoffersen), Ljung-Box, ARCH and the tails; a traffic light, and a reason when it fails | E1 | `kinematics`, `report` | done 2026-10-29 (session 11): `kriging.Model.innovations`, `kinematics.backtest`, a Basel-zone light with its reasons; drawn with the band's own covariance green 93-98 %; recorded 4 green, 38 yellow, 2 red (5/37/2 with M8), 7.0 % of one-step predictions outside. Measured 2026-10-28 on the 46 recorded tracks: 926 of 18,996 points outside (4.87 % against 5 %), Kupiec fails 6 of 88 axes, Christoffersen 20, Ljung-Box 54 (the birds' wingbeat left in), 84 green and 4 yellow |
| 0.4 | breaks beyond the wander: a sup-Wald scan with the track's own fitted covariance as the null (15 % trimmed, the ends NO POWER), an interval on the date, a camera event inside it as the match rule; the break common to a group's members | E2 | `camera`, `kinematics`, `groups` | to do, with E1; measured 2026-10-28: 22 of 44 tracks (1 of 40 drawn), where `rate_steps` gives 1,267 stretches; PR135's six at 44.556 s and PR097's objects 1-4 at 126.19 s, p ≤ 0.0005 each, none of PR097's alone |
| 0.4 | the event study against the scene: each break's abnormal change (the object's minus the scene's) with a Newey-West error; the per-frame scene from `layers`' overlapping shifts (Denton), held pictures kept on the clock; NO POWER where `layers` holds the scene; event-induced dispersion for a group's common change | E3 | `camera`, `layers`, `groups` | to do, with E1; measured 2026-10-28: PR144's break at 23.27 s the camera's (object −41.2, scene −53.7, abnormal +12.5 ± 20.4 px/s), the scene NO POWER on 13 of 14 reference case files, PR135's common reversal (193 px/s) with no extra spread (17th centile of ordinary moments); its pointer checked 2026-10-29: from about 0 to +0.15-0.22 deg/s then (p 0.008), the sign agreeing, dated only to 43.2-44.5 s by a glyph drawn in whole pixels; 1,236 px/deg (68 %: 955-1,750), so the camera's turn is all of the change at a field of about 1°; the MTS-B's corner brackets (0.8, from uap PR135) put PR135 in a state whose next zoom-in is x2, so NAR (0.643°: all of it at a look down of 29-61°) or the wide field (7.2°: a fifth at most); the mode word, the elevation and FVW/SLR are under the redaction boxes |
| 0.4 | jumps named: a glitch, an excursion or a step, against a familywise threshold simulated on the track's own frames and gaps, with a scale floor for quantised tracks | E4 | `kinematics`, `autolink` | done 2026-10-29 (session 11): `kinematics.jumps`, the threshold drawn on the track's own frames and gaps (familywise 1 %), glitches and excursions left out, steps kept and named; 0-1.5 % named on clean drawn tracks, a 4-px glitch found 85 %, a 4-px step 79 %, 3-px 24 %; PR149's two glitches left out (its depth bound 4.6 -> 0.62 % a second). Measured 2026-10-28: the normal table with a short local MAD flagged 20 % of drawn tracks; simulated, 0-2.5 %, a 3-px step found 38 % of the time |
| 0.4 | the model-free nugget, √(−γ₁(Δ²x)/4), and ρ₁(Δ²) beside the band's: a check on REML's, and a flag for a beat in the track (Roll's bid-ask estimator on second differences) | E6 | `kinematics` | to do; measured 2026-10-28: a median 0.80 of REML's, PR144 1.00, PR135's members 0.39-0.73; Roll's own estimator, on first differences, had the wrong sign on 80 of 88 axes |
| 0.4 | "constant" as an upper bound: the largest change of speed the band could have missed (the pile-up problem) | E12 | `kinematics`, `report` | done 2026-10-29 (session 11): `kinematics.change_bound`, against a steady change (holds 96-98 % on drawn lines); no recorded band says constant, 11 carry the bound; the simulated Stock-Watson form not built |
| 0.4 | stale prices in `slew` and `readout`: Dimson's summed slope over lags and the Hoffmann-Rosenbaum-Yoshida lead-lag, so the pointer's lag is measured and the slope checked against it | E14 | `slew`, `readout`, `camera` | to do; PR051's upload pointer first |
| 0.4 | the zoom as a regression discontinuity: a bandwidth, a robust interval, placebo cutoffs (how often the fit finds a step where there is none) | E15 | `forensics.zoom_fit`, `zoom` | to do |
| 0.4 | the zoom ladder pooled across a sensor's clips (the fixed effects of price indices; credibility shrinkage): a k with a stated prior on a clip where the camera never moved | E16 | `scale`, the data folder | to do; the pointer sweep's ladder (x2.00, x5.9) is its input |
| 0.4 | the routes to k combined with their errors, after a test that they agree | E17 | `scale` | to do |
| 0.4 | the model confidence set of motion models (a line, constant velocity in projection, a turn) under dependent errors: "what survives" as a computed set | E22 | `kinematics`, `projective` | to do |
| 0.4 | the traffic light for stochastic checks in the suites: a check on drawn data passes, warns or fails by a binomial zone rather than one threshold, so the suites do not flap | E20 | tests | to do; the band's drawn-track checks (K8) first, then wherever a suite checks a rate |
| 0.4 | the projective test held to the track's own noise: the model's residual against the nugget (or a GLS fit with a wander held short of the span), "fits" on the card only within a few nuggets, otherwise "describes its trend to N px"; 24 of the 25 recorded tracks it passes today miss it by 8-1,078 nuggets (PR135's members "fit, going away"; PR077's 705° loop "passes, no closing seen"), only PR43 holds | M1 | `projective`, `report`, `report_qt` | done 2026-10-29 (handoff-v04 session 9): the jitter read twice, the band's nugget and its covariance's nugget fitted to the model's residual, the larger taken; "fits" within 4 of it (drawn constant-velocity tracks: at most 5 % called trend-only, none with white jitter); 24 of the 25 recorded tracks describe their trend (4.6-234), PR43 fits (1.0). The GLS form with the wander held short is not built |
| 0.4 | the admissible region's extent as the clip's fact; a distribution over it only under a named measure, the invariant one (log-uniform range, isotropic direction) beside the uniform one, since the same region is 31 % or 97 % subsonic by the choice (Bertrand's paradox); the isotropic deprojection said with it (the true speed over ωR above 2 one time in 7.5, above 10 one time in 200) | M2 | `kinematics.admissible_region`, `admissible_said`, the region's figure | done 2026-10-29 (session 9): the extent exact and said first as the clip's; the region drawn evenly in R and Ṙ and with the range log-uniform and the direction isotropic, both said (2-20 km at 0.01 rad/s: 31 % and 97 % subsonic); the isotropic odds on the transverse-speed row |
| 0.4 | held pictures tested, not counted: the band's top lowered only for a cadence on the track's own frames (a balanced word: the least balance share over 2-12-frame windows against a random word's, then the held share by GOP place), otherwise the frame grid's top with the held frames as missing; the source's rate and cadence from the slope's continued fraction. Brought forward from 0.8: 211 of PURSUE's 214 ten-second windows that lower the band hold no cadence; the Galileo flyers' holds are the encoder's (top 24 Hz, not 5-13); PR149's "no beat" covers 0-9.3 Hz. Known cadences to test on: PR051's YouTube copy (doubled), Svanström V_HELICOPTER_020-024 (25 on 30) | M3 | `flicker.pictures`, `integrity`, `layers.repeating` | done 2026-10-29 (session 11): `flicker.cadence` (balance at 0.85 over 2-12-frame windows against 200 random words, then the GOP's places, which must beat the cadence at its best); the census's counts reproduced; PR44, PR141's two, PR149 and PR097 object 8 back at the grid's 12 Hz; PR055's sphere stays lowered |
| 0.4 | the turn as an ellipse past about 150° of arc (the affine image of uniform circular motion: r/D exact, the tilt, ω, and the speed and acceleration in body widths with no foreshortening); on a short arc the sagitta with the tilt's band in the words (the picture's radius 0.15-8.5 times the true one; "did not turn" fails for 1-4 % of orientations) | M4 | `projective.turn`, `said`, `report` | done 2026-10-29 (session 11): read whole past 150° of phase and heading, the minor axis 3 errors from zero, the rms at most 0.8 of a free quadratic's; drawn 180-540° arcs read 25.0 for 25; PR077 object 1 a loop of 23.5 ± 0.3 widths; the sagitta's words carry the tilt's band (0.152-8.50) |
| 0.4 | "no closing seen" as a bound on abs(Ż/Z) from the band's speed change (v_end/v_start = ((T + L)/T)²), and t_z's error from the same algebra in place of the residual bootstrap | M5 | `projective`, `kinematics`, the ledger | done 2026-10-29 (session 9), but for t_z's error: `projective.depth_bound`, its error along the track floored by a free quadratic's; θ bounded and the region a wedge where the track fits, said as a condition where it describes its trend; PR23 under 1.6 % a second, PR149 under 4.6 % (the survey's 1.0 and 4.5 % took the error along the change). t_z's error: done 2026-10-29 (session 11), not by the same algebra (measured ~6x too wide about the fit's T, biased long about the band's dv) but by a sandwich, the fit's residual given a REML covariance (`projective.tz_err`): 68-76 % / 91-98 % at ±1 / ±1.96 where the bootstrap held 39-71 % / 70-95 %; PR43 T 0.91 s, 95 % 0.72-1.10. Before: t_z's error from the same algebra in place of the bootstrap: not done |
| 0.4 | field rotation in a pan: a rotation fitted per frame pair in `layers` (the full pinhole rotation where k is known); the roll over the pointer's Δθ is sin ε, with no k, and a pan at depression is not one translation | M6 | `layers`, `slew` | prototype in the survey: on the PTZ soccer camera the roll follows the pan (r 0.74-0.88) at half its dataset's model, drawn pairs read to 0.003°; a turret with a known elevation next |
| 0.4 | a quasi-periodic kernel for a bird's band: the Matérn times cos 2πf₀τ beside it (a covariance by Schur's product theorem and Bochner's), so the wingbeat is held as covariance, not left in the innovations | M8 | `kriging`, `kinematics.speed_band` | done 2026-10-29 (session 11): `kriging.beat32` (and a first harmonic), fitted where a rhythm is left and kept only where the backtest improves; the birds failed E1 alone (PR135's members Ljung-Box p 1e-27 to 1e-52); a beat kept on 19 of 22 tracks, none of the birds green (the camera's turn at 44.5 s is left: E2) |
| 0.5 | flap bouts: change-point segmentation of the band envelope | S5 | `flicker` | to do |
| 0.5 | small rate changes along the track by stretching | S15 | `flicker` | to do |
| 0.5 | the four gliding tests (bouts, slow modulation, circling, skimming) | the gliding theory | new | to do; a labelled sample of non-beating birds from the Svanström run (0.5 above) |
| 0.5 | double-difference separations for a formation's rigidity | S14 | `groups` | to do |
| 0.5 | differential image motion within a group | A18 | `groups` | to do |
| 0.5 | polarisation of the jitter (platform or own) | S16 | `groups`, `integrity` | to do |
| 0.5 | pulse-train fold with the strobe as positive control | T14 | `flicker` | built (item 13, 2026-10-21); a visible airplane/drone known answer to do |
| 0.5 | a known lamp measured at its alias | T13 | analysis | to do, if a clip exists |
| 0.5 | the exotica list and harness: one of everything after every change | T9 | tests, sweep | to do |
| 0.5 | the discriminant plot with the control populations; screening language | S20 | `figures`, `report` | to do |
| 0.5 | kriged flow at the object within its layer, with an edge flag | K3 | `comotion` | to do |
| 0.5 | the tether's bootstrap block length | K7 | `tether` | to do |
| 0.5 | azimuthal renormalisation around the core (a tether or plume in glare) | A19 | `tether` | to do |
| 0.5 | a search over the pendulum's own motion for a payload too faint for single frames | the tether notes | `tether` | to do |
| 0.5 | the balloon's recoil against its payload (`wobble`) | the tether notes | -- | parked: refused by every PURSUE clip tried, each for a stated reason |
| 0.5 | the insect tests: defocus, platform motion, Strouhal, the sensor's time constant | the insect note | `forensics`, `flicker` | to do |
| 0.5 | `flicker` on the labelled infrared set (Svanström 2021): the bird test's miss rate on 79 bird clips, its false-alarm rate on 286 drone, airplane and helicopter clips | I1 | sweep, `flicker` | run 2026-10-19 in the PURSUE analyses (0.5 above); the harness to do, on the new workstation |
| 0.5 | path sinuosity on the layer-removed track (straight flyers against erratic ones) | I7 | `kinematics`, `groups` | to do |
| 0.5 | AARO's resolved cases run blind, the report's conclusion against AARO's | the AARO data | sweep, tests | to do |
| 0.5 | the bird class's height prior from the FAA strike record (strikes fall by about a third per 1,000 ft above 500 ft, most of them at night), returned with its caveats for a stated height; a prior, never a test | Av2 | `kinematics`, `report` | to do |
| 0.5 | wind as a known quantity (the platform's own ground speed and heading over a turn, or reanalysis by date and area), and the balloon test it allows: ground velocity against the wind at height | Av7 | `kinematics`, `comotion`, case file | to do |
| 0.5 | wind-farm rotors and synchronised obstruction lights in the PURSUE wind-farm clips as slow-periodic and strobe positive controls | Av12 | sweep, `flicker` | lights not seen in PR48/PR058's infrared (2026-10-21); rotors to do |
| 0.5 | flares in the exotica list: illumination (minutes under a canopy, slow descent, swing) and decoy (seconds, ejected, falling) | Av13 | tests, look-alike table | to do, with T9 |
| 0.5 | the ground-held canvas: `layers`' per-pair shifts chained into one ground-fixed mosaic of the new pictures, graphics masked, the hold checked on raw ground tiles matched between pictures (2.3 px/s on the Middle East Object). What `stabilize` does for a filmed screen's drawing, done for the ground; the base for MEO2 and MEO3 | MEO1 | `stabilize`, `layers` | to do |
| 0.5 | smoke and dust as a wind vane at the ground: from a marked source, the streak's direction on each held picture (its brightest ray), and its puffs' motion (each picture minus the stack's median) for a speed. "Direction only" when the puffs move no more than the hold's floor, since a steady plume keeps its shape in any steady wind. A surface tracer beside `drift`'s T1, and weaker, since the object may be far above it. The smoke is picked by a mark, never as "what changes most", which finds things with height (the Middle East Object: streak at 189-198°, the object's path at 185-191°, speed not measured) | MEO2 | `drift`, `comotion` | to do, with MEO1 |
| 0.5 | the lit side, frame by frame: the bright part's direction and distance from the dark part's centre, the dark part's elongation and axis, and their relation to the speed on the screen (smear, or shape). A lit side that holds its direction is sunlight on something that does not tumble. The bright part is measurable only where it rises above the background, so its offset is biased to the rim | MEO4 | `forensics`, `tracksheet` | to do, with MEO7 |
| 0.5 | look-alikes from known answers: beside an object's enlargements, the moments of resolved cases that look like it (the Middle East Object's dark body with a bright upper-left patch is AARO's known foil balloon at 3.5-9.5 s). A gallery, not a classifier: a shared look is a lead, and the report says so | MEO9 | `report`, `figures`, the AARO data | to do, with AARO's resolved cases run blind |
| 0.5 | inside the controls' population, or NO POWER: a gated reading's inputs (size, contrast, frame rate, the chain) placed against those of the controls it was set on (banking's population stability), a verdict only inside | E5 | `flicker`, `report` | to do, with D14 |
| 0.5 | reason codes: at most four, ranked by weight of evidence, under the report's conclusion, in plain words (the rule US lenders follow when they decline) | E7 | `report`, window | to do, after the controls |
| 0.5 | the probability of backtest overfitting for each gate and floor (combinatorially symmetric cross-validation), rerun after every change | E9 | sweep tools | to do; `BIRD_FLOOR` and `POINT_DISC` first |
| 0.5 | a bootstrap over videos in every rate over tracks, since a video's objects are not independent | E10 | controls harness, corpus statement | to do; measured 2026-10-28: design effects 0.95-1.6 on the Svanström calls |
| 0.5 | matched controls: each false-alarm rate also in the case's own cell of size, contrast and frame rate | E13 | controls harness | to do |
| 0.5 | a challenger for every gate: the simplest rule that could do its job, and the gate's margin over it (model-risk practice: SR 11-7, now SR 26-2) | E19 | D14's cards, controls harness | to do |
| 0.5 | rigidity as cointegration: unit-root and stationarity tests (ADF and KPSS) on the separations, four outcomes with NO POWER among them, in place of `groups`' RIGID and SHUFFLE thresholds | E21 | `groups` | to do |
| 0.5 | flap and glide as two regimes (Hamilton's switching model), bout lengths censored at the clip's ends | E24 | `flicker` | to do, with S5 and the gliding tests |
| 0.5 | one rigid thing or several: the group's centred positions' residual off rank 3 (2 for a flat body) against drawn rigid bodies of the same size, frames and jitter (Tomasi and Kanade's rank theorem; Eckart-Young); a multi-light object told from a group | M7 | `groups`, `several` | to do; PR135's six are several (1.47 px off rank 3, where a rigid body leaves 0.27) |
| 0.5 | the scene read where templates fail: the odd part of the frames' cross-spectrum in blocks (anything that stays put has a real cross-spectrum, however it breathes), with a shuffled-frame null and a shift-and-add test on the pictures. Of the 13 reference case files that say NO POWER, 7 get a scene, and PR149 past its track; PR41 25-32 px/frame, following the north marker at r 0.92, with 60 frames added at that velocity showing a surface; PR144 within about 1 % of `layers`; still-camera clips none. The shuffled null alone does not hold a coder's artefacts, so the stack is part of the test. Gives E3 its index and `slew` a scene: PR088 object 2 brackets c at 652-1,349 px/deg on a clip with no k | B4 | `layers`, `slew`, `camera` | measured twice; the report's words for a scene read this way are the maintainer's |
| 0.5 | the drift test's real rate: 7.3-8.6 % of empty apertures in real frames pass the stated 1 % (3,057 in 121 videos, 286 in 13), inflation factor 1.7-2.0 in every tranche. The cause is the curve model's shape at 1.5-4.5 Hz, not how the null is read: curves drawn from an aperture's own fit pass 1.3 %. The full rule holds at 0.36 % against the stated 0.15 %, every false alarm at 1.5-2.8 Hz. Say the real rate, and a beat's false rate by frequency | B5 | `flicker`, `report`, sweep | to do; measured twice |
| 0.5 | the beat in the position against the beat in the light, a test for K2: in fixed segments, the object's centre of light and its brightness at its own frequency. Of 30 beating objects, 15 lock within 45 degrees of +90, all at +87 to +108 (mean 94, sd 7, 8 clips); 9 lock elsewhere, 6 not at all. Sensor lag (it would flip about 180 degrees on a reversal; the data move 23), a fixed delay, the encoder, interlace and shake do not make it; a passed test's p is a rank (the off-beat null passes 7-12 %). The axis is fixed in the picture but no single world vertical, so it is not shown to be a wing. A second reading independent of the photometry, not a better gate | B9 | `flicker`, `report` | measured three times; a tumbling control and the rolling readout are still to do |
| 0.5 | a lag between a group's members: each member's delay behind the others, by least squares against its own wander, the null drawn on the group's own shared path. A camera has no odd part in the cross-covariance, so it can dilute a lag and cannot make one, while a lag that follows the row is the readout. Resolves 0.5 frames rms on PR135's path, reads zero on one object seen twice (PR141) and 86 ms in a public pigeon-flock set. PR135's six read 0.29 frames, inside the null, so their shared turn is not passed between them, whatever the field of view; the one exit left is a cue reaching all six within about 15 ms | B10 | `groups` | measured here |
| 0.5 | the census in videos: every rate over objects with an interval that resamples videos. 75 of 1,154 objects (6.5 %) beat, in 20 of 87 videos: ICC 0.33, design effect 9.2, about 125 effective, 2.8-11.3 % by video, one video holding 29 % of the beats. The 25 reference beats are about 13 independent flocks and birds. The corpus statement counts videos. Sharpens E10 and D7 | B12 | sweep, corpus statement, docs | measured twice |
| 0.5 | the held-out third's agreement stated as a difference with a by-video interval (6.8 % against 6.3 %, difference -8 to +11 points; 2.1 % without one video), a ledger of looks (date, commit, gate, set), and a new held-out set for the gates changed since the look of 2026-10-18. Sharpens D5 | B17 | `tools/sweep` | measured here |
| 0.5 | members of a group always go through the in-step test, even when measured one by one, and a case file records it: the reference files skip the groups stage, so nothing asked. PR097's objects 1 and 3 correlate +0.87 in the beat's band over 4.2 s (PR135's six a median 0.13), which that length cannot settle: two independent birds at one rate look locked 37 % of the time at 5 s, and about 28 s is needed | B18 | `flicker`, `groups`, `tools/rerun_cases.py` | to do; a flag, not a finding |
| 0.5 | widths per beat on a fixed camera, the insect tests' Strouhal check with its constant: labelled birds read 3.28 in fitted widths (5-95 %: 1.64-5.54). A row beside the beat. A gate at 2 widths a second on the bird rule removed the labelled set's 2 false calls with no bird lost; the division by the beat adds little as a classifier (AUC 0.89 against 0.93). No power on a moving platform; cruising drones untested | B19 | `flicker`, `report` | measured here |
| 0.5 | a Strouhal number with no range and no size: twice the wobble times the beat over the image speed, on an unresolved object. Still-camera flyers 0.02-0.06; a beat aliased from 50 Hz would read several times too high on its true frequency. Sharpens the insect tests | B20 | `kinematics`, `flicker` | measured here |
| 0.5 | how many in a blob: the beat band's relative variance against single objects, number-and-brightness style. Sums of N real curves read 1.7, 3.4, 6.7, 10 for 2, 4, 8, 12 (AUC against one 0.74, 0.94, 1.00); PR135's real six read 8-10. Tells many from one, not two from one, and gives the wingbeat test its completeness against flock size | B21 | `flicker`, `groups` | measured here |
| 0.5 | M7's line scaled for coloured jitter before it is built: second differences read the jitter 1.28 times low on planted truth and the drawn line has 6 % of room, so at a lag-1 correlation of 0.3 every rigid body is called several. Scale by about 1.7 or draw the measured colour; PR135's six stand, 1.47 px against 0.48 | B23 | `groups` | to do; the scale computed, not yet run on drawn bodies |
| 0.5 | the bird rule's operating point stated with its cost: at one object in twelve a bird, the stage rule prices a false bird at a third of a missed one and the 8 % floor at 1.5. Set the floor from a null on unseen sets | B24 | `flicker`, `report` | to do |
| 0.5 | a mock community beside every unresolved share: 390 of the labelled set's 432 tracks of wholly known objects stay unassigned (90 %), against 83 % indeterminate in the release, so the share reads the reference and not the sky | B25 | `report`, docs | to do; measured here |
| 0.5 | a beat within 3.5 times its floor may read high: planted beats that barely pass read up to 1.5 times their truth; past 3.5 times they read true | B26 | `flicker`, `report` | to do; measured here |
| 0.5 | a blind audit: about 100 objects, flagged, unflagged, planted beats and planted nulls, shown with the call and the video's name hidden, scored by two scorers apart. It gives chance-corrected agreement, a real miss rate and the scorer's own bias; only the 36 flagged objects of 1,409 have ever had a look | B27 | controls harness, `tools/sweep` | to try; not run |
| 0.5 | the exact bound beside each control: no false alarm in four negative controls bounds the rate only under 60 %, and the labelled set's 11 of 286 clips gives 1.9-6.8 %, so the goldens are a regression and the rate comes from the labelled set. Exercise answers marked as regressions where they follow the tool. Chance-corrected agreement for every rule compared on one set of tracks (stage against paper: 95.8 % raw, kappa 0.80) | B28 | `tests/test_golden`, docs/exercises, sweep | measured here |
| 0.5 | a bird or a bat: bats beat at 4-13 Hz, the same band, and the report's sentence names tumbling and blinking but not them; no test here tells them apart | B29 | `report` | to do; literature |
| 0.5 | the wander's range by labelled class, once tracks are vetted against the labels: at 10 s drones' range is unresolved (AUC 0.79-0.89 against birds and airplanes), bird against airplane 0.52-0.57 | B33 | `kinematics`, sweep | to try; 198 unvetted tracks, the rig not excluded as the cause |
| 0.5 | the blur kernel, exponential tail or box, as a fact about the sensor: on a bolometer `streak` says there is no shutter. At 120 px/s or more a rule calls 208 of 275 fast Boson tracks, 0 of 9 turrets, 0 of 69 planted boxes. The time constant is about 7.6 ms after the chain's loss, for `flicker`'s low-pass and the insect bound. A turret object with its own trail fools the arrow (PR148 89 %) and only the 3-15 ms window refuses it, so the false rate is provisional. Sharpens V7 | F20, F21 | `streak`, `integrity`, `flicker` | to do; measured twice |
| 0.5 | an arrow from one frame on a bolometer, the tail pointing back along the path: right on 91 % of frames at 2-4 px/frame, 98-99 % above, boxes 50-54 %, keyframes alike, so no temporal prediction makes it. A proposer for Find and Follow, never on a turret alone | F22 | `propose`, `autolink` | to do; measured twice |
| 0.5 | a second locator, for reproducibility: the band's error on the mean rate is repeatability given the locator. From drawn click errors on 30 objects a Kinovea-style template moves the mean past that error on 14 of 28, a Tracker-style one on 5 of 22, while the per-frame band holds; Follow on 1 of 27 at 1 px, 4 of 27 at 2-5 px, through the spot size the marks choose. And a floor under that error: two clean drawn lines miss by 5 and 7 errors, 0.1 px end to end. Sharpens P7 | F31, F32 | `autolink`, `kinematics`, `report` | measured here |
| 0.5 | the chain's own memory read off a fast thing: a ghost one frame back of 0.27 on PR43, on an I frame too, 0.00 on PR23, 0.21 on PR077 object 1, split by speed to tell it from a wake. A recursive filter's low-pass that `flicker`'s amplitude floor does not know (gain 0.25 leaves 0.60 at Nyquist). Sharpens S9 | F33 | `integrity`, `flicker` | measured here |
| 0.5 | sinuosity against its null: path over chord read against the curve a straight track of the same speed over jitter draws, not a fixed 3.0. On 44 recorded tracks speed over jitter alone explains 58 % of log S; PR077 object 1 stands 7 times over the curve. Sharpens I7 | F34 | `kinematics`, `groups` | measured here |
| 0.5 | a drawn spot through the clip's own codec as the control for any jitter or nugget claim: on 97 aircraft windows the spot jitters 0.018 px before the codec and 0.078 after, the real aircraft 0.064 | F35 | `planted`, `kriging`, `forensics` | measured here |
| 0.5 | residual autocorrelation reported beside `drift`'s track fit: at the measured lag-1 its 2-sigma covers 94 %, at 0.8, an operator's wander, 73 %. A moving-block bootstrap of the readings is no fix | F36 | `drift` | measured here |
| 0.5 | what was near the line of sight, with the chance of it: the Sun, Moon, planets, bright stars and catalogued satellites for a time, a place and a direction, each with its rate at a random line of sight (bright bodies at night 2.6 % within 2 deg; any catalogued satellite 25 %, sunlit with rate and direction 0.02 %). An ADS-B match is held to another day's traffic (4.5 % within 2 deg), and a light that stays put is tested as a star. A position alone never identifies | F37, F38, F39 | new `sky`, `report` | measured here |
| 0.5 | a blind bench for the rays, because nothing holds `drift`'s track fit to scenarios it did not see: drawn scenarios with truth, declared anomalies and a pointing-error ladder, a refusal scored as a refusal, on an own generator | F57 | `planted`, `tools` | to do |
| 0.5 | the Huey as a 3-D known answer for the fixed-point test, a golden from its track through frames 13419-14220: hovering it holds to 0.5 m rms within 5 m of the stored site across the ground, and leaving it misses by 3-11 m. Not rebuilt, and not yet a truth: its height reads 39-43 m above the site against 12-31 m from the pilot, and two routes to its range disagree (215-236 m against 267-270 m), so those are settled first | F40 | `tests/golden` | to do |
| 0.5 | a number of sigma from a scanning tool needs its null: IPACO's tilted-column thread sum, position and tilt scanned, gives 3 sigma on 79-99 % of plain sky patches and 5 sigma on 1-7 % (6,000 patches, three sensors). On PR071's string it reads 3.2-3.9 against 1.4-1.8 on the reversed track, which `tether`'s control already gives, so a line sum joins `tether` only with that null beside it. Not rebuilt | F52 | `tether` | to try |
| 0.5 | a plate solve for a clip with stars, an optional extra: on real star frames a triangle solve gives k to 0.01 % through H.264 CRF 28 and at half scale, and refuses at CRF 33 and on a poorer frame. One of two frames solved, by a solver of our own, and its 10 matches are a judgement still to be set by a null. A long-wave camera shows no stars, and no planet in 450 stacked frames | F53 | new `sky` | to try |
| 0.6 | `plant`: synthetic objects and look-alikes through the whole chain | T4 | new | to do |
| 0.6 | recovery rate and the search's negative half | T6 | sweep | to do |
| 0.6 | the aperture pass rate against the object pass rate across the pass | T8 | sweep | to do |
| 0.6 | anomaly ranking over the pass | T12 | sweep | to do |
| 0.6 | completeness from the pass's own record | S19 | sweep | to do |
| 0.6 | corpus noise models | S3 | sweep | to do |
| 0.6 | a dense flow field of the scene with a validity mask | A14 | `layers`, `comotion` | to do, GPU |
| 0.6 | where and when to measure the shift field next (the kriging variance as a design) | K11 | `layers` | to do |
| 0.6 | anomaly ranking as model criticism: a tail probability under each control population, never a score for "anomaly" | P9 | sweep | to do, with T12 |
| 0.6 | corpus statements carry the net: the releases, their selection, the triage pass and the depth of the search | P10 | sweep, `several` | to do |
| 0.6 | the anomaly ranking says which method flagged each object (flight-data monitoring's methods disagree) | Av14 | sweep | to do, with T12 |
| 0.6 | conformal p-values per control class for the anomaly ranking, within strata of release and quality (unsupervised scores track data quality) | D9 | sweep | to do, with P9, T12, Av14 |
| 0.6 | an ordinal-pattern reading of the beat (unchanged by any AGC or gamma) and the complexity-entropy plane as neutral features | D10 | `flicker`, sweep | to do |
| 0.6 | audit sampling: frames drawn at random for a person to check on a whole-video case file (59 with no error bound its error rate at 5 %), weighted toward the frames that move the answer; samples of what each gate refused | E8 | the window, `batch` | to do |
| 0.6 | tail p-values past the corpus's largest by extreme value theory (peaks over a threshold), for the noise models | E24 | sweep | to do, with S3 |
| 0.6 | the count of bird videos stated as presence times detection: on 79 clips known to hold birds the bird rule names one in 21 (27 %, 18-37), so one video in twelve is a floor, about 30 % if that rate carried over. A planted beat does not glide, so the census's weight for birds comes from this | B13 | sweep, corpus statement, docs | measured here |
| 0.6 | planted dots flatter Find where it really fails: on 127 hand-labelled objects it has 73 % against a planted 77 %, but 58 % of objects in several-object clips against 82 % alone, and 29 % of those held still. Plant groups as well as single dots, and state a labelled-set figure beside the planted one. A fresh encode changes Find's answer on 12 % of objects | B22 | `planted`, `propose`, sweep | to do; measured here |
| 0.6 | `scrambled` withheld under 4 Hz, where 16 % of background curves pass at 1 %; above it the bar stands 1.65 times higher with the beat in the chunks (Narcissus). A reading only, in the safe direction | B34 | `flicker` | to do; measured here |
| 0.6 | the planting tool's first row: the same dots on a clip's real frames read a median 1.9 times the still control's amplitude near the beat (0.54-2.42, 8 clips); no verdict moved but PR079's at 2.33 Hz | B35 | `planted` | measured here |
| 0.6 | a per-point quality in the track's CSV from the detector's response (0.50 px at response 5-9, 0.16 past 47), which a weighted nugget can read; contrast moves the error a factor of 4, local texture 1.9, picture type 5-10 % | B36 | `forensics`, `kinematics`, `kriging` | to try; about 40,400 dot-frames |
| 0.6 | a row's time in the track where the readout is known: a bias of v_y rho/H in speed, 2 % at 20 px/frame in 1080 rows, 4 % in 512, and an offset of up to rho frames between objects at different rows. Not measured here: one phone clip gives the readout's direction (p 0.005, 765 frames) and only a wide range for its length. Follows B41's readout | F59 | `kinematics`, `groups` | to do |
| 0.7 | the object as its own template; pieces stitched across gaps | S2 | `autolink`, `propose` | to do |
| 0.7 | the link gate in error units, growing with the gap | K4 | `autolink` | to do |
| 0.7 | thresholds by the frame's own noise; a false-spot rate; chain likelihoods | S7 | `forensics`, `propose`, `autolink` | to do |
| 0.7 | error bars on filled track points | K6 | `forensics`, `tracksheet` | to do |
| 0.7 | pickers for appearance, disappearance and ingress | S10 | `autolink`, `kinematics` | to do |
| 0.7 | the pathological-motion map (the sea's glitter as a region) | V4 | `propose` | to do |
| 0.7 | difference imaging with a calibrated significance | A5 | `integrity`, `propose` | to do |
| 0.7 | shift-and-stack over a velocity grid; semblance for the velocity search | A6, S8, T15 | `propose` | to do |
| 0.7 | a per-frame source catalog with a resolved-or-not test | A11 | `forensics` | to do |
| 0.7 | a calibrated streak detector | A12 | `forensics` | to do |
| 0.7 | learned point trackers and segmenters as proposers | the workstation note, F54, F62 | GPU extra | tried 2026-11-01 (the single-camera survey); never the judge. CoTracker3 at its working 384x512 loses a 5-px dot (308-364 px off) and holds it in a crop (0.18-0.95 px); in a 2x crop it reaches the link on 4 of 9 benchmark cases while beating a do-nothing null, adds no case the link loses and fails PR43 (2 on, 18 off), and its licence is non-commercial: not adopted. SAM 2.1 tiny in a crop holds the same dot to 0.52-0.65 px at 5.8 s a frame, reaches the link on PR149 (23 on, 1 off) and fails PR43 (5 on, 11 off); Apache-2.0, two cases only, the licensable route if one is ever wanted |
| 0.7 | blind marks: frames the tool chooses, marked with nothing drawn, and their distance to the track reported | P7 | `mark_qt`, `tracksheet` | to do |
| 0.7 | an airborne benchmark with known ranges (the open Airborne Object Tracking set: aircraft, helicopters and birds seen from an aircraft, GPS ranges for the planned aircraft): Find on dim airborne points; range from span and the blur-width bound checked at known range | Av8 | tests, benchmark | to do |
| 0.7 | a hidden-Markov track-before-detect bank after a close-minus-open filter (detect-and-avoid practice) | Av9 | `propose` | to try, beside A6 |
| 0.7 | hold-aware linking and the hold composite. Holds are read on the object's own patch: its patch repeats while the frame around it changes, which `pictures()`' whole-frame rule cannot see. Each hold is collapsed to one picture, with its frames averaged as repeats; links run over pictures, not frames; the pictures are stacked aligned on the object and rotated to its motion. The object at each new picture, and the trail behind it at the frame-rate spacing, are reported apart. Case: uap PURSUE PR39. Its object holds 2-3 frames (~10-15 pictures/s at 30 fps, jumps of 60-70 px at a mean 20 px/frame) while whole-frame differences stay at 0.06-0.20 DN; follow failed on Jacob's marks; fainter copies trail at ~20 px. Uap `analysis/cases/pr39/` (README, `pr39_composite.png`, `pr39_spacetime.png`) | uap PR39, 2026-10-23 | `autolink`, `flicker.pictures`, `figures` | to do |
| 0.7 | spots ranked by their prominence (the 0-dimensional persistence of the frame's peaks), which no gain curve can change | M10 | `propose` | to do, with the benchmark |
| 0.7 | who is who after a near-miss: the second-best assignment (Murty's ranking) and its cost gap, "members 3 and 4 may have swapped at frame N" | M11 | `several`, `autolink` | to do (PR135's members pass within 8 px, PR097's 2 and 3 within 3.7) |
| 0.7 | one exclusive assignment among a group's tracks after each is linked, a detection to one object: in drawn flocks with 10 % of detections missing, `assemble` takes a neighbour 4.4 times an object in 150 frames, an assignment 0.03. Marks still win at a crossing. Sharpens M11 | B37 | `several`, `autolink` | measured here; drawn flocks only |
| 0.7 | `find_rank` to count swaps, with the wrong-object frames from the nearest recorded track: its 12-px "off" cannot see a swap between members closer than that (PR097's 1-3). No flock is in its cases yet, so add one | B38 | `tools/find_rank.py` | to do; measured twice |
| 0.7 | the half-peak centroid locks on narrow spots: at sigma 1.1 px planted dots read 0.085 px whatever the contrast, ten times a weighted centroid. A second pass for spots under about 1.5 px | B39 | `forensics`, `autolink` | measured here |
| 0.7 | two flappers in one blob told apart by where each beat lives: a lock-in map at each frequency, separation read to a quarter of the blur on drawn blends of real curves | B40 | `flicker`, `several` | to try; no real blend yet |
| 0.7 | PR142's recorded track is not one thing: 33 of its 131 rows are off the object, and of the link's 8 off frames 4 are the record's. Curate it, and hold every record to a continuity test with a speed limit from the case. Rank stays 1; no user number moves | F7 | `tests/golden`, `tools/find_rank.py` | to do; measured twice |
| 0.7 | Find's 41x41 blanking hides neighbours at the peaks (4.77 of PR135's six at half-width 20, 5.95 at 6), and narrowing it is not the fix: the whole of Find at half-width 6 takes the shortlist from 3 of 6 to 1 of 6 and the top score from 47.7 to 17.5, chains mixing neighbours. What keeps chains apart at a narrow blanking is to try, with `find_rank --link` first | F8 | `propose` | to try; measured twice |
| 0.7 | a learned detector for things held still only, as an optional proposer and never the judge. On Svanström's distant clips MSHNet ties Find on moving things (0.84 against 0.84, 12 clips) and its gain is all under 0.3 px/frame, which Find does not claim to see (helicopters 1.00 against 0.02). MSHNet has no licence on code or weights, so a fresh implementation and fresh training, or nothing | F43 | `propose` (optional extra) | to try; measured twice |
| 0.7 | how many marks a dim object needs: a 5-px dot at 30 grey levels links 25 of 60 frames, 41 px off, from two marks, and 51 of 60 at 0.25 px from seven. The report could say so. Sharpens S7, K4 | F42 | `autolink` | to try |
| 0.7 | a row clock for a propeller-like line on a rolling sensor: the phase along a track crossing 60 rows or more says which alias family a line belongs to. Planted power only: a 3 % line at 68 Hz is found on 41 of 60, and on 174 real tracks forward and reversed readout agree (148 against 147), so no signal yet | F55 | `flicker` | to try |
| 0.8 | the data bar and mode annunciator readers; the zoom chain | the old roadmap | `symbology` | the zoom chain's steps from the imagery built 2026-10-21 (`mcdonald zoom`, merged to main, unreleased); its readout and the annunciator to do |
| 0.8 | the clock: frame stamps, tears, variable frame rate | S9 | `clip`, `integrity`, `flicker` | to do; earlier if a clip needs it |
| 0.8 | the comparagram and a robust gain map between frames | V3 | `flicker`, `integrity` | to do |
| 0.8 | the noise level function per clip | V13 | `flicker`, `integrity` | to do |
| 0.8 | the shutter's slope bound; the sinc on fast beats | V7 | `integrity`, `flicker` | to do |
| 0.8 | the row-phase test for filmed screens | V10 | `flicker` | to do |
| 0.8 | block-grid alignment; the rhythm of synthesised frames | V16 | `integrity` | to do |
| 0.8 | comodulation per band and window | S12 | `flicker`, `integrity` | to do |
| 0.8 | the photometry's self-noise from three channels | S13 | `flicker` | to do |
| 0.8 | the metrics table and glitch catalogue | S18 | `integrity` | to do |
| 0.8 | the slanted-edge point-spread function; the sharpening ring | V9 | `forensics`, `flicker` | to do |
| 0.8 | brightness through clipped frames, from the diameter | A8 | `flicker` | to do |
| 0.8 | the response of size and position to a known flux change; the position floor | A7 | `groups`, `flicker` | to do |
| 0.8 | the ghost test | V8 | `forensics` | to do |
| 0.8 | a destriping pass before registration | A15 | `forensics` | to do |
| 0.8 | block integration and a fitted disappearance (occultation practice) | A9 | `clip`, `kinematics` | to do |
| 0.8 | two-channel coincidence for split-screen clips | T7 | `flicker`, `groups` | to do |
| 0.8 | channel balance in colour clips | T17 | `flicker` | to do |
| 0.8 | frame noise from the variogram's nugget | K5 | `forensics`, `propose` | to do |
| 0.8 | the operator's actions as interventions: the clip cut at zooms, polarity flips, focus changes, slews and mode changes read from the record, and each candidate's response scored | P8 | `integrity` or new, `symbology` | begun 2026-10-20 on branch `flir1`: `mcdonald camera` finds zoom steps from the object (applied only where its position confirms them) and sets the rate's steps beside the camera's events; `mcdonald events` finds the overlay's own (readouts' changes, clocks, the gate's strokes, the picture's steps, held frames; method §22), and `camera --events auto` takes them; FLIR1's azimuth ticks found to the half frame, its zoom readout's change at 2238 |
| 0.8 | readouts in whole steps timed to the frame (the slew rate from an ATFLIR's azimuth ticks), and what a held readout cannot rule out | -- | new, `readout` | built 2026-10-20 on branch `flir1`, merged 2026-10-21 (method §21): FLIR1 0.2466 +- 0.0051 deg/s (0.2518 before a tick timed on the grey was timed on the text's strokes); the values are read by a person off its strip; `symbology --method atflir` places the ATFLIR's fields itself (method §23) |
| 0.4 | the released-track null: a departure against the camera's own rate before | -- | `camera` | built 2026-10-20 on branch `flir1`, merged 2026-10-21 (method §20): FLIR1's fastest stretch +1.5 sigma over the pod's slew with the field's 10 %, +4.3 with it exact |
| 0.8 | copies of one clip set side by side: detail kept, blocks the encoder held, held frames (the recording's and each copy's), the lag and its steps (a frame repeated or dropped), a relabelled rate, the best source | -- | new, `versions` | built 2026-10-20 on branch `flir1`, merged 2026-10-21 (method §24): FLIR1's 2007 copy is the best of four |
| 0.8 | integrity's layer-order test on symbology drawn frame by frame (a moving gate, text held for a stretch) | -- | `integrity`, `forensics.ridges` | built 2026-10-20 on branch `flir1`, merged 2026-10-21 (method §25): decides only where object and symbology are on opposite sides of the picture's level |
| 0.4 | the field of view as the display gives it, stretch by stretch: changes of field taken out of the track like zooms and checked on the object's size where it can | -- | `camera`, `atflir` | built 2026-10-20 on branch `flir1`, merged 2026-10-21 (method §20, §23): FLIR1's `2.0` over 2158-2209 is MFOV x2 (1.5 deg), not NAR x2; its object, at the blur there, cannot check it ("no power"), the three x2 zooms it confirms |
| 0.4.x | `flicker.continuum` reads its noise curves as it reads the curve: through the same running mean, each with its own peak left out of its own fit. With the null true the stated 1 % runs at 4.6-5.2 %; with both changes 0.3-0.8 % on white curves and 2.2 % on red ones, so red curves want a second look. Six of the 27 reference lines leave the 1 % level (PR077 object 2, PR097 objects 3, 4 and 8, PR099 object 2, PR141 object 1) | B1 | `flicker` | to do; measured twice |
| 0.4.x | the speed band held to planted truth: straight dots planted in real frames, re-encoded and found by the detector, lie within 1.96 stated errors on 68-72 % of components (white jitter of the same size 94-96 %). The detector's error has a memory of about 2.3 frames, the Matérn takes it, and `vbar` is read on the latent path, so it counts as the object's own path. A GLS slope, with the larger of its error and the band's, covers 97.4 % on clips held apart. The errors are small (median 0.07 % of the speed) and the card's headline speed does not move, but 87 % of those straight dots are called "not constant", and under 1 px/frame the range said is 0.57-1.67 of the truth. E1's backtest cannot see this: the innovations look perfect | B2 | `kinematics`, `kriging`, `planted` | to do; measured twice |
| 0.4.x | the scene under the sensor's pattern, the one-line form: each pixel's mean over a block of frames taken out before `layers`' templates, on pairs held still. PR099 object 3 reads 0 on raw frames and 24.6-28.0 px/frame so; PR144, a clip that already works, does not move | B3 | `layers` | measured twice |
| 0.4.x | the speed along the path with its interval, from paths drawn from the band's own posterior, beside the net displacement the report calls the average: they differ by over 1.5 times on 25 of 44 tracks, 49 times on PR41. `Case.upper_bound`'s "doubles back" takes a net speed too (PR077 object 1: 9.1 and 5.7 px/s against a path speed near 150). The plain fastest reads 0.72-0.99 of the truth on drawn tracks and its stated 95 % covers 79-92 %; drawn paths read 1.00 and 91-94 % | B6 | `kinematics`, `report` | to do; measured twice for the defect |
| 0.4.x | the speed in body lengths said to be free of k, R and the field of view but not of the camera's own motion: rate over size is v_own/D for a still object, so a 1-m thing seen from an aircraft at 100 m/s scores up to 100 lengths a second. The row says so, and is NO POWER on a moving platform unless the track is against a scene at the object's own depth | B7 | `kinematics`, `stages`, docs | to do; a wording defect |
| 0.4.x | a pixel aspect on `run`, and PR113 read with it. Its file holds a 720x480 raster stretched to 1080p. Symbols read 1.755 wide to tall on the rotating ladder, independent of any ring; the scene reads 1.35 over nine frame pairs, near the 1.33 of a 4:3 picture, so symbols and scene do not share a stretch, and the ladder's scale is 36.47 px/deg rather than 35.4. An object in the scene then reads about 125 px/frame on the vertical scale where one square pixel gives 142. Open: why the two stretches differ, the scene's x scale, and shear from a sloping ground | B8 | `stages`, `kinematics`, `scale` | to try; measured twice |
| 0.4.x | a beat names a bird's span and speed: a bird flies 3.3 spans a wingbeat at any size (86 species, a factor of 1.25), span 0.54 m at 7.6 Hz, 1.39 m at 3.1 Hz, so `as a bird` takes its band from the object's own beat, a factor of about 3 end to end where 0.2-2 m is a factor of 10. Any such relation carries the tree (Pagel's lambda 0.96; slope -0.216 +- 0.022 against least squares' -0.301; scatter x1.40 for a bird of unknown order). A beat names a size, never a kind: no barcode gap in 152 species | B11 | `report`, `figures`, docs | measured here |
| 0.4.x | a track on near-whole pixels named: the Rayleigh length of the positions' fractional parts beside the nugget, the yard flagged above 0.3. PR135's six, PR088 object 2 and PR097 objects 1-4 read 0.62-0.90, the other tracks at most 0.22; `grid_of` answers 0.01 for them. It is the tracker's and not the video's (0.10-0.17 px rms off the grid), and about half of PR135's nugget variance is this | B14 | `kinematics`, `projective`, case files | measured twice |
| 0.4.x | the position floor from the picture, not a fixed 0.1 px: the Cramér-Rao bound from the spot and the noise beside it, times 3 (constant dots through the clip's own encoder: 1.8-4.7, the encoder itself a factor 1.19). Nuggets stand 8 times over the bound at the median and better locators do not lower them, so the card's jitter is mostly the object | B15 | `projective`, `kinematics` | measured here |
| 0.4.x | the released-track null's error from the speed band: on tracks drawn with a recorded track's own wander and no departure, the fastest stretch beats the camera 97 % of the time and the whole departure 74 %, on white jitter 2 %. PR051's 43 sigma stands, its wander being short. Sharpens E3 | B16 | `camera`, `kinematics` | to do; measured here |
| 0.4.x | the body-length class table with what each limit was measured under, and its one honest output, a largest body: a flyer of w widths a second is no longer than about 54/w m. Real power on 3 of 46 tracks, none over the 385 a second of a hummingbird's dive, so the table excludes nothing and PSF work (V9) is what opens it. Sourced ceilings beside SPEEDS_OF_ITS_OWN: a bird's cruise 8-23 m/s (138 species), a peregrine's dive about 70 m/s as reported and 89-112 m/s in a model, a free-tailed bat 44.5 m/s over 2-4 min, and moths at a passerine's ground speed on a third of its airspeed, so a ground speed alone separates none of them. Sharpens Av11 | B30 | `kinematics`, `report`, docs | measured here |
| 0.4.x | say when the wander's range is not measured: past a third of the track the band's `range_s` is "longer than the track", only s^2/ell^3 being known (52 % of coordinates past the track). Name the band in the method as the OUf of the ctmm family, which wins or ties on 38 of 44 tracks; two time scales change no net speed | B31 | `kriging`, `kinematics`, docs | measured here |
| 0.4.x | closing speed in body widths a second, k/a from the looming fit's coefficient, with k and no range, wherever a tau is read; and T's band under the steady-speed condition said beside the band under a tau-dot from -1/2 to -2: PR43's T of 0.76 s runs 0.50-1.30 s across what its track allows | B32 | `kinematics`, `projective` | to try; no recorded object has it yet |
| 0.4.x | `run` takes the picture's stretch. One k on a stretched picture reads 10 deg/s as 13.33 across, with no warning. PR113 holds two stretches of two things: symbols 1.753 wide to tall (1.751-1.755, 322 frames), scene 1.29 (1.24-1.38, 15 pairs of a real roll; known stretches come back within 2 %). At 36.25 px/deg on the vertical scale the object reads 124-126 px/frame, about 103 deg/s (+-7) where the report prints 121, and the field 39-40 by 30 deg where it prints 54. 142.3 px/frame stands in file pixels. Sharpens B8 | F1 | `kinematics`, `scale`, `stages`, `report` | to do; measured twice |
| 0.4.x | a scale drawn on the display is the scene's only where the scene moves with it, so test that before a graticule is called measured. PR113's upright real-time pass reads slope 0.88, total least squares 1.16, r 0.78, n 37: the ladder's vertical scale carries to the scene to about +-15 %. Rolled stretches test little, a ladder showing attitude | F24 | `scale`, `report` | to do; measured twice |
| 0.4.x | the bead test's stated 1e-3 is not its rate: steady dashes pass on 7.5 % with no codec (6 of 80), and through x264 on 28-47 % on real frames and 77-100 % on flat sky, because a codec flattens the side lines the F ratio rests on. Set the threshold on steady dashes through the clip's own codec, sum spectra in hertz, keep the band off the blur's roll-off. PR43's result (none) does not change. Sharpens V14 | F2 | `streak` | to do; measured twice |
| 0.4.x | `integrity.py:123` raises KeyError on a stream with no codec name: `mcdonald integrity` exits 1 on a .mov with a timecode track, and under `run` the stage is lost. 1 of 76 corpus files | F3 | `integrity` | to do; measured twice |
| 0.4.x | `drift`'s refusal reads where the fit landed: `VELOCITY_FIX` passes straight flights on 1.0 % of runs at the default sigma and 6.7 % at a tighter one, each a phantom flying beside the aircraft at 1-2 % of the true range; T2 then says "it flies" of a body drifting with the wind, 4 of 4. The next row's gates take over the refusal | F4 | `drift` | to do; measured twice |
| 0.4.x | range's NO POWER as a number, for each motion model on any clip with an own-ship path: the exact Cramér-Rao bound on ln R at the maximum-likelihood fit (Nardone, Lindgren & Gong 1984), with two gates. The path must leave the model's basis by more than its reading error: rounded straight flights pass 14.5-40 % without that gate. The model must hold: an object that rounds a corner gives a small bound on a wrong fit (truth within 2 bounds on 13-25 %), and an F test of K=3 over K=2 refuses 87-98 % of those, its rate still to calibrate. Spearman with the error 0.925 planted in the model, 0.80-0.82 on one real turn, about four independent numbers. A floor: a hovering helicopter reads 20-24 % short | F10 | `drift`, `kinematics` | to do; measured twice |
| 0.4.x | `drift --platform --los` crashes on 6 or 7 readings (`:923` admits 6, `:653` needs 8 distinct, IndexError at `:664`); 8 readings keep about 5 of 2,000 draws. The guard and the bootstrap should agree, and too few should read cannot say. No recorded case is this short | F5 | `drift` | to do; measured twice |
| 0.4.x | a model wind counts at any height: a file with only a 100-m level counts at 3,960 m and T2 passes or fails on it, where observed winds have a guard. The same guard for model files. Upper winds before about 2021, which Open-Meteo lacks, from NCEP/NCAR Reanalysis 1 by OPeNDAP, no account. No recorded case is far outside its levels. Sharpens Av7 | F6 | `drift` | to do; measured twice |
| 0.4.x | the band against known answers: on 19 aircraft, 33,609 frames, its 95 % holds 64 % of frames [54, 73], median track 68 %, with truth in pixels; an apparent 46 % is the pinhole k's error, not the band's. The shortfall is all in narrow bands (under 0.15 px/s 45 %, over 0.6 px/s 93 %), and a truth error of 0.05-0.1 px/s gives 67-72 %, B2's rate, so it is one shortfall. The widening is a floor, about 1 px/s gives 96 %, not a factor. Sharpens B2 | F9 | `kinematics`, `tools`, method §32 | to do; measured twice |
| 0.4.x | `streak` reads the frame less the median of its neighbours, as `follow_by_motion` does: rms falls 3.2 times on real sky and 8 on cloud, nothing on flat sky; PR43's dash scatter about a line falls from 6.4 to 1.9 px. Needs a still or registered scene | F11 | `streak` | to do; measured twice |
| 0.4.x | a joint fit of the dash, the trailed point-spread function of Vereš et al. 2012: centre, length, direction, width and flux from one frame, the length capped by the frame step. On the same picture it beats the half-peak length by 1.8-5.9 times in every family drawn, inside and outside its own (5.03 against 1.97 px rms, 1,526 dashes), and 3.5 times on real blur of known path. NO POWER under 4 px. Its centres (PR43 1.9 px against the track's 3.3) are a better track point, and its flux a second clock on T (0.63 s against 0.76). Sharpens V14 | F12, F41, F51 | `streak`, `autolink`, `kriging`, `projective` | to do; measured twice |
| 0.4.x | the shutter as a range and a line, not one number: PR43's dash is 0.37 of the frame step at 12-17 px/frame and 0.78 at 27-41, the gap near 8.5 px at every speed, so 0.49 is the ramp's middle. Exposure change, scene motion, interlace, codec grid and reader bias refused; the cause is open. Sharpens V14 | F27 | `streak`, `report` | measured here |
| 0.4.x | a held-range profile through the rays, own-ship from the display's airspeed and bank (as in West's Sitrec; Sitrec2's licence bars its code, so the mathematics is written afresh), with the nose-to-velocity term in a banked turn: for each range the steady velocity and what it misses by, flat reported as no power. GOFAST with its range withheld: 12.5 km, 9.6 (8.1-12.8) with that term, against 8.06 km displayed; bank +-3 deg alone 8.1-60 km. GIMBAL: a steady object in the jet's air is at about 8 NM or beyond (95 %), best near 15 NM, which does not choose between a manoeuvre and a cruise. Bands and refusals, never a range | F13 | new `traverse`, `drift` | to do; measured twice |
| 0.4.x | the least speed under a steady velocity, V(R) = J + R w, which needs no range. FLIR1: the fit's least speed through the jet's air is 135 m/s; 95 % it exceeds about 80 m/s with the bank at zero, about 50 m/s with the bank free, on a stretch chosen for being steady. A bound on a stated assumption, not a floor on the object: the curvature is 1.2 sigma | F14 | new `traverse`, `report` | to do; measured twice |
| 0.4.x | the height-speed curve in place of one height: the constant-height family on the rays, with its least-residual and least-speed heights. On AARO's Puerto Rico clip the least line speed is 2.13 m/s at 195 m on the whole clip, 3.83 at 210 m on 22-234 s, 4.4-4.5 on the halves, so AARO's 3.6 m/s sits inside, and the path is no line at any height. SCU's table reproduces within 1 mph and spans 3-36 mph at 253 m: its error omits the height | F15 | `drift`, `figures`, `kinematics` | to do; measured twice |
| 0.4.x | the platform's imprint on a candidate track: its acceleration regressed on the aircraft's, slope 1 - k, a shifted series the null. Puerto Rico at sea level slope -1.09, 42 % of the acceleration (null 95 %: 20 %); zero at 270 m, the height the straight fit picks (268 m) | F29 | new `traverse`, `drift` | measured here |
| 0.4.x | the parallax ladder's least speed in closed form, \|A x G\| / \|G - A\|: the ladder is the constant-height family at one instant (worst k gap 0.0005 over 400 scenes; a climbing aircraft 0.6 %). On the ladder PR43's least speed is 29.10 m/s at k 34.26 (1564 m), and the 31.5 in the ladder's row is the speed at k 29.29; a constant-velocity fit over the track reads about 14 m/s at 87 m, the two unreconciled, both scaled by a borrowed own speed. Sharpens that row's fix | F16 | `kinematics` | to do; measured twice |
| 0.4.x | is this a fixed thing at some range, from the cameras structure from motion recovers, with no k and no data bar. A translation check comes first (99th percentile 7.46 on a fixed camera), and the line is drawn at the object's own depth from held-out half-solves, since a camera error grows with inverse depth. PR43 is not fixed, by 2.4-8 times, and with no cameras misses the epipole by 157 px (129-176). PR23 is NO POWER, which does not show it fixed. A closing aircraft on a steady bearing passes, so a pass reads consistent with, never fixed | F17 | `kinematics` or new `fixedpoint`, `report` | to try; measured twice |
| 0.4.x | k and the aircraft's path from the pictures by bundle adjustment, never a printed focal length: COLMAP read 1,107 px for about 4,000 on a fixed camera with no warning. On the Santa Barbara orbit it gives 7,240 px on 159 frames and 5,390-5,680 on 80, silently, with the path to 2.47 m rms over 381 m, needing the whole arc, and the surface 10 m short at 300 m. Field times arc holds at 48 deg² and above and is lost at 10 and below. PR23's depth sign comes from outside the fit. Numpy and scipy, pycolmap an optional extra | F23, F30 | new `sfm`, `scale` | to try; measured twice |
| 0.4.x | height over speed from a still camera whose pointing is known, by giving `projective.fit` a known up, reported as a ladder of hypothesised speeds (the V/H of aerial reconnaissance, Brown 1965). On 240 aircraft against ADS-B: 2.7 % median held out, far tracks 2.1 %, near arrivals 13.6 %. It needs the radial term (11.7 % without) and says NO POWER under 3-4 deg of arc. An airliner's speed schedule gives range only for an airliner | F18 | `projective`, `report` | to do; measured twice |
| 0.4.x | k and roll from the sky on a fixed camera: the Moon's or the Sun's arc against its ephemeris, no ADS-B and no stars, the fit's rms saying how far to trust it. The Moon fits to 0.232 px over 44.8 min, five minutes to 1.23 %. It gives the local scale along the arc, not a focal length: -0.5 to -1.2 % against a lens fitted to aircraft, by which lens pair is held, at a place no aircraft track reached. The radial term comes from elsewhere. Skyfield an optional extra | F19 | `scale`, new `sky` | to do; measured twice |
| 0.4.x | k and the camera's place from known points in the picture, the way Chelyabinsk's casual videos were calibrated: crossings of known plan on a broadcast frame give f to 2-5 % and the place to 0.6-1.6 m, or f to 0.3-1.3 % with the place known. A 5-px click costs 0.5 %, a map error of 0.5-1 m costs 4-6 %. A narrow field with its points to one side reads +17 %, and the place, 6 m out, says so | F28 | `scale`, new `sky` | measured here |
| 0.4.x | no bare rate: `fit_v_px` returns its error and degrees of freedom, and the report and card print a rate with an interval by Student's t. PR113's 142.3 px/frame, in file pixels, is +- 8.5 on the line alone (2 dof), +- 11 with fields and first click | F26 | `kinematics`, `report`, `tracksheet` | measured here |
| 0.4.x | the checklist's items that T10 lacks, from Louange's procedure (Sturrock et al. 1998) and IPACO: a second independent source named or absent, copies from the original, a crop against the camera's sizes, a flare's line through the optical centre. S17's A-D collide with GEIPAN's A-D, identified to unexplained, so use other letters. Sharpens T10 | F56 | `report` | to do |
| 0.8 | readouts' values suggested from the clip's own clock (its seconds' digits as templates), beside the sheet a person reads | -- | `glyphs`, `atflir` | built 2026-10-20 on branch `flir1`, merged 2026-10-21 (method §23); suggestions only |
| 0.8 | a single segment's change in a readout on a 1080 rendition of a standard-definition display (GOFAST's 38 -> 39, GIMBAL's 49 -> 48): each look's strokes matched frame by frame as `readout` does once a person has read the looks, or the stroke a digit gains or loses drawn from the clock's own templates | the camera handoff (`docs/handoff-camera.md`, Open) | `events`, `atflir`, `glyphs` | to do; a halved cell, a per-segment statistic and 16 times the kept pixels each found none of them (method §22) |
| 0.8 | the field of view's mnemonic suggested as a word: letters that match one another within the margin at a VCD's blur (FLIR1's `NAR` reads `N??`), and letters in no fixed text (MFOV's M, WFOV's W) | the camera handoff (`docs/handoff-camera.md`, Open) | `glyphs`, `atflir` | to do; a person reads it meanwhile (three looks on FLIR1) |
| 0.8 | boxes of scene told from boxes of text in `events`: PR27's one box is its breakwater, and its false changes went from 19 to 40 over 600 frames once the noise was read from the quiet frames | the camera handoff (`docs/handoff-camera.md`, Open) | `events` | to do; `events` stays out of `run` until then |
| 0.8 | `camera --events auto` looked at again on FLIR1's exit, now that `events` finds the field of view's mnemonic and the bottom line's readouts as boxes | the camera handoff (`docs/handoff-camera.md`, Open) | `camera`, `events` | to do |
| 0.8 | thermal crossover at a wink-out: the object's last level against the background it crosses into | I4 | `flicker.lost`, `integrity` | to do |
| 0.8 | the narcissus test: a dark, display-fixed feature against the optical centre, zoom, focus and NUC events | I5 | `forensics.defect_map` | to do |
| 0.8 | midway-equalization non-uniformity correction (IPOL) beside the destriping pass | I8 | `forensics`, `layers` | to do, with A15 |
| 0.8 | glare's orientation against the camera's roll | I9 | `symbology`, `forensics` | to do |
| 0.8 | a data-compatibility step for any read display series: biases, scale factors and time lags fitted jointly, robust to misreads (flight-test practice) | Av6 | `symbology` | to do, with the readers |
| 0.8 | the file's own sound, where it has any: codec families named, a mains or 400-Hz bus series as a clock, a propeller's blade-pass by shaft order as the platform, and their aliases into the look-alike table | Av3 | `audio` (new), `flicker` | on main since 2026-10-17 (built 2026-10-16): `mcdonald audio`, reporting; its lines join flicker's table; airframes C-130 (T56), C-130J, H-60, each named only with its second tone; planted-tone completeness 76-92 % at +18 dB, no airframe read as another (docs/method.md §11); in the window as Measure → The sound of this video… (`sound_qt`); the MQ-9 into the table once its propeller speed is sourced; the NTSC field rate is no longer read as mains (Ac1) |
| 0.8 | the video's frame comb from its own k = 1 line (30 and 30/1.001 both tried), claimed before the mains; mains only off the comb, flagged when no grid holds it; the clocks re-read at full resolution in 30-s pieces, splitting families under 0.25 Hz apart (two supplies; field rate beside mains) | Ac1 | `audio` | on main since 2026-10-17 (2026-10-16, acoustics survey): FLIR's 59.94 is its field rate, PR113's mains 60.011, FLIR's odd-harmonic 60.32 Hz off-grid |
| 0.8 | a line on two combs counts for neither (3 x 400/1.001 = 20 x 59.94): a bus standing only on shared lines is possible, not shown; every bus said against 400 and 400/1.001 (an NTSC pull-down) | Ac2 | `audio` | on main since 2026-10-17: PR113's bus possible; PR106/PR107/PR111 at 400/1.001 or with a second supply at 399.82 |
| 0.8 | a clock's phase as an edit detector (ENF forensics): steps that scale with frequency are timing, a fold finds periodic joins | Ac3 | `audio`, `integrity` | to do; prototyped in the acoustics survey (PR113: +0.12 ms every 20.00 s) |
| 0.8 | the band edge: a brick wall below the final codec's means an earlier encode | Ac4 | `audio`, `integrity` | to do; PR106's 11.18-kHz wall in the survey |
| 0.8 | planted tones put through the file's own encode before they are read (completeness with the codec's masking) | Ac5 | tests, the analysis harness | measured in the survey (-2 to -9 points at +18 dB); the harness change is the analysis repo's |
| 0.8 | impulses: a clip's cut edges, gunfire with a sourced rate table (GAU-23/A at most 200 a minute; 105 mm at most 10) | Ac6 | `audio` | to do |
| 0.9 | harmonic-sum detection over a family, for completeness at 9-12 dB | Ac7 | `audio` | to do |
| 0.8 | a source passing the microphone: its speed and closest range from the Doppler curve of its tones (Ferguson 1992), the rest tone held when the airframe is known, the f0-v trade reported when it is not | Ac8 | `audio --flyover` | on main since 2026-10-17: DVIDS C-130H passes at 212-244 kn, 291-465 m with 68.06 Hz held; against ADS-B (AeroSonicDB, 75 accepted passes) closest range / altitude 0.92, 16-84 % 0.66-1.19; next the Lloyd's mirror for height |
| 0.9 | one propeller speed or several: line multiplicity and the beat (synchrophasing) | Ac9 | `audio` | to do |
| 0.8 | council asks from the sound: the recorders' own audio channels; any 30 -> 29.97 conform; grid logs for PR113's copy date; the T56 reduction gear's tooth counts (to derive 8.129) | Ac10 | council | to do |
| 0.8 | registration by mutual information where the record shows a polarity flip, an AGC step or two channels on a split screen | D11 | `layers`, `integrity` | to do, with P8, T7 |
| 0.8 | the same footage twice: frame fingerprints across the releases and outside copies, and the copy tree (which copy was made from which) | D12 | `integrity`; the PURSUE pipeline | to do |
| 0.8 | who follows whom: Granger causality between the object's offset and the scene's shift (gimbal lock and loss of lock; a display mark follows nothing) | D13 | `integrity` or new | to try, with P8 |
| 0.8 | gain ramps, not modes: stretches where the whole picture's level and spread change smoothly over a few frames, flagged so that a colour cast is not called another camera and photometry across them is not trusted (on the Middle East Object an automatic gain over a dark grove turned the sand white and the trees blue, read at first as "a blue display mode") | MEO5 | `integrity`, `events` | to do, with P8 |
| 0.8 | the title card against the daylight: a card's time in Z said against the scene (sunlit, crisp shadows) and the stated region. "2156Z" on the Middle East Object is about 01:00 local, so it is the report's time, not the filming's | MEO6 | `readout`, `report` | to do |
| 0.8 | brightness references in the frame: beside an object's level, the same frame's marked references (sunlit asphalt, sand, a person, shade), so that "as dark as shade" or "brighter than sand" is a number (the Middle East Object: body 1-6, asphalt 98, sand 182, shade 1, of 255) | MEO8 | `flicker`, `report` | to do, with V1 |
| 0.8 | the zoom state from the corner brackets: on the MTS-B the bracket box marks the next zoom-in's view, its half-width 0.244-0.249 of the frame from the reticle where the next step is x2 and 0.082 where it is x5.9 (PR27's wide, x2 and NAR states; PR051's NAR, ULTN and 2X; PR135), so a clip's rung on the ladder (7.2°, 3.6°, 0.643°, 0.321°, 0.161°) is narrowed with no slew and no data bar -- a short list of fields for E16's prior where the camera never moved. PR135: 0.249, so not the 3.6° state; with its pointer check, NAR makes its members' common reversal the camera's at a look down of 29-61°, the wide field leaves the camera at most a fifth. Uap `analysis/cases/pr135/pr135_pointer_slew.md` ("The field of view, tried"), `analysis/cases/pr135/pointer_slew/brackets.py` | uap PR135, 2026-10-29 | `symbology`, `scale`, `zoom` | to do; measured on four frames by a script outside the package |
| 0.8 | an interlaced source's fields as samples at twice the frame rate, the beat band to the field rate's Nyquist; interlace found in the pixels, since every flagged file in the data folder says "progressive" | M9 | `flicker`, `integrity` | to do |
| 0.8 | a true rate behind an alias from its residues at two clocks (fields and frames, or two sensors), by the robust Chinese remainder theorem | M12 | `flicker.lookalikes` | to do, when a case needs it |
| 0.8 | the sensor's readout time from pairs of fixed things under a pan: the lag between them against the row. 1.11 frames over 256 rows on the Boson (68 %: 0.94-1.22), none across columns; uncorrected, 37 % of camera-only pairs show a false lag. Any timing across rows is corrected by it, a member's lag above all | B41 | `integrity`, `groups` | measured here |
| 0.8 | the ghost grid: an earlier encoding's block grid survives an upscale at 8r px, so a file names its upstream raster, the way shared errors group manuscripts. 13 of 29 PURSUE videos show one in both axes, 8 a 1.5x upscale of 1280x720 (PR27, PR41, PR057a, PR079, PR118, PR144, PR148, PR149). No ghost does not mean native; fetch the base where the release has one; a spectral cut-off did not confirm it clip by clip. Sharpens D12 | B42 | `versions`, PURSUE pipeline | to do; measured here, PR113's raster twice |
| 0.8 | the same footage twice, first half: seed and extend on bit strings of picture change, the false-match rate fitted to the corpus run backwards. Finds PR122 inside PR121 blind (as AARO states) and same-speed repeats inside PR051, a titled edit with three copies, and PR113. Nothing is counted twice and no reference measurement lies in a repeat. It misses copies with changed geometry, so this is a lower bound. Sharpens D12 | B43 | `integrity`, PURSUE pipeline | measured twice for PR051 and PR113 |
| 0.8 | the corpus statement says how complete its class list is: sample coverage (Good-Turing, Chao-Jost) on a named label list, with the warning that it covers classified objects only: 36 labelled videos, 8 classes, 11 % (2-19 %) that the next is new, and the same 17 AARO videos read 17 % or 65 % by how the labels are lumped | B44 | `share`, docs, corpus statement | measured here |
| 0.8 | slowed copies inside a clip: lines of steady slope in each frame against the rest of the file. PR113 holds its transit three times, once at 1/20 speed; PR051 has 1/3 and 1/2 speed passages with different redaction boxes on the same frames. A rate or beat read there is off by the slowing. 2 clips of 32, 1 false alarm on empty sky; it needs a floor on scene detail. Sharpens B43, D12 | F44 | `integrity`, `segments` | measured here |
| 0.8 | the record inside the file: DVIDS's XMP box (a date, a country, a VIRIN, the release's text) read into `integrity`'s record and held against the title. PR099's title says 25 SEP 19, its XMP the 23rd, its VIRIN the 24th; PR055's says Afghanistan, its XMP the United States | F45 | `integrity`, `catalog` | measured here |
| 0.8 | the clock's status said: "exact rational 30" is the header's fraction, a transcode's rate and not a measured one, and SWGDE 19-V-005 says frame timing should not be conducted on transcodes. Presentation times read and a gap flagged where a track crosses one: FLIR1's 2007 MPEG has three, up to 0.1 s by its end. Sharpens S9 | F46 | `clip`, `integrity`, `report` | measured here |
| 0.8 | fields as positions as well as samples: PR113's eight field positions read to 0.3 px from the release's slow replay, where its track has four; the track's own fields give 142.6 px/frame, the others 133.4. `idet` calls the clip progressive; a comb on a moving thing shows the fields. Sharpens M9 | F47 | `clip`, `autolink`, `integrity` | measured here |
| 0.8 | rhythms of the whole picture in its frame steps, not only held frames: lines at 3, 5, 6, 10 and 12 Hz on 25 clips, likely earlier encoders'. Six of 25 published beats lie within 0.12 Hz of such a line (chance 1.2), each next to it and none on it, and `flicker`'s background test passes them all. A lead, not shown | F48 | `integrity`, `flicker` | measured here |
| 0.8 | the container report names every data track, the MISB ST 0601 key, ST 0604 stamps, ISO 6709 tags and SEI strings, and says when there are none: a census of 1,091 files, 60.6 GB, found no KLV anywhere. The telemetry is not hiding in the files | F49 | `integrity`, `clip` | measured here |
| 0.8 | a budget block in the report in the GUM's form: each input, Type A or B, its degrees of freedom and what fills it, with "not known" a legal value, so a missing term is named as a NO POWER is. PR113's table is the worked example | F58 | `report` | to do |
| 0.8 | an earlier encoder's GOP from frame sizes, for the record: PR44 and PR141 31 frames, PR41 29. A planted GOP comes back on 4 of 6 and a null on 0 of 6, the threshold set on that null of six, with no power on PR144, and a held picture makes the same line (PR113). Sharpens Ac4, V16 | F50 | `clip`, `integrity` | to try |
| 0.9 | mark colours everyone can read; a colour-vision test in the suite | V6 | `mark_qt`, tests | to do |
| 0.9 | the Marey composite (the track in one figure) | V11 | `figures` | to do |
| 0.9 | a model card for every stage that bears a gate (its use, completeness and false alarms per control class, where it has no power, its traps); a datasheet for the 1.0 catalog recording the net | D14 | docs | to do, with P10 |
| 0.9 | "carried along" in `comotion` has a fifth class: a thing under its own power on the line from the camera to a background point (motion camouflage), at (1 - r/R) of the platform's speed across the line; and a bearing held in a world frame says the object's speed across the line is the platform's, at any range | B45 | `comotion`, docs | to do; a derivation, no recorded case |
| 0.9 | the citation debt, one list, corrected against the code: `drift.fit_track` owes Nardone, Lindgren & Gong 1984 and Hammel & Aidala 1985, `parallax_ladder` Kumar et al. 1994 and West's Sitrec, `streak.motion_px` Vereš et al. 2012, `projective.fit` Aidala & Hammel 1983, height over speed Brown 1965; about fifty rows in all, for the method note and the JOSS paper's State of the Field | F60 | `docs/method.md`, the JOSS paper | to do |
| 1.0 | the case files as vintages (each release's numbers kept, revisions studied); the census weighted by completeness (Horvitz-Thompson) | E23 | `share rerun`, corpus statement | to do |
| later | a horizon refraction ray tracer (the mirage null) | A20 | new | deferred unless a horizon case needs it |
