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
   the rotation-only self-calibration from the frames' own homographies needs no pointer.
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
   gain is removed) gives θ = atan(ωτ), and the fan collapses to one line -- validated first
   on Galileo aircraft, whose ranges ADS-B gives. The citation for the fan's one-sidedness is
   the sonar and IRST literature on bearings-only target motion analysis (Nardone & Aidala
   1981: no range without an observer manoeuvre; Ṙ/R is observable first).
4. **A speed with a band for every track.** The track's own covariance fitted (a Matérn
   kernel with a nugget for the centroid's jitter), the instantaneous velocity kriged from it
   (up to 13× tighter than frame differences on the recorded tracks), the average speed's
   honest error, and acceleration as a likelihood ratio rather than a refusal -- validated on
   planted tracks simulated with the fitted covariance. Non-uniform motion described, not
   averaged.
5. **What is known, extended.** The platform's speed, heading and altitude, the sensor's
   depression and azimuth, a field of view from a geolocation, a range from a correlated
   track, each entered as a known quantity with its source recorded, so that an outside
   solution (a geolocated terrain, a flight log, a mission report's range) reduces the case
   in the toolkit rather than beside it. The range ratio for a reference object; a stereo pair
   where one exists.
6. **The unknowns ledger.** Every report says, for k, R, θ and v_own: constrained, bounded or
   missing; by which route; and which released datum would close it. The Technical Note's
   census becomes a per-case table that 1.0 sums over the corpus.

**Hypothesis-driven:** none; this is the framework. **Hypothesis-neutral:** every bound the
pixels allow, on every case.

**Could feed:** a follow-up note to the Technical Note (what the pixels do constrain, case by
case); the methods paper's kinematics chapter.

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
  formation's rigidity by double-difference separations and the group's common motion; the
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
draw and the words "consistent with", "not screened out" and "excluded" can rest on.

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
   over the corpus. What the sweeps produce by hand today.
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
   whole corpus, so a beat's strength is a centile of what the sensors do, not a fixed number.

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
   a calibrated significance.
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
cadence.

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
   variable-rate clip turns up.
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
   whole catalog.
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

Still open:

8. **The catalog's case files** (1.0): made by the batch run with an agent's picks and the
   maintainer's look, or by hand.
9. **The reference case files after the `flir1` merge** (2026-10-21): `share rerun --strict` on them now
   differs by additions only (the camera stage, `kinematics`' `held` and `noise_px`, the ladder's 0.7 deg
   row, a camera "no power" in the bottom line's count where a track is under 8 frames); no number of
   theirs changes. Decision 7 accepted the same for `beat-controls` until 1.0; whether it covers this
   merge, or the files are remade, is the maintainer's to say. (`camera` stays a stage of `run`: decided
   2026-10-21.)

## The ideas bank

The nine surveys' ranked ports, grouped by the release each is scheduled in. The "from"
column is the survey and its rank there (A astronomy, S seismology, T SETI, K kriging and
Gaussian processes, V film and the visual arts, P philosophy of science and evidence, I
infrared observations of birds and other aerial objects, Av aviation: flight test, accident
investigation, targeting, collision avoidance and the bird-strike record, D information theory
and data science), so an
entry can be traced back to the note it came from. P12, a check for copied reports among a
release's documents before they are counted as independent, belongs to the PURSUE pipeline,
not here; so do Av1 and Av15, a question and the evidentiary requests for the council.
*Shipped* means on `main` at 0.2.20 with its gate off; *parked* means tried and set aside for
the reason given. New ideas go at the bottom of the release they belong to, with a
"from" of their own.

The information-theory survey's D1-D7 belong to 0.3, and D1
changes results, because the codec mark at the resolution has kept the 2-s windows from passing
anything between 7.0 and 8.0 Hz on the IBBBP clips, which are nearly all of PURSUE.

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
| 0.3 | the verification checklist in the report | T10 | `report` | to do |
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
| 0.3 | the aperture for a faint or smeared point: a size reading the sea cannot inflate, and a disc near the point default. (1) `extent` on single frames fails on a faint, smeared object over banded sea: on PR089's bird C after a sensor blank it read nothing on 7 of 11-12 frames and 43-66 px on others, so `sizes` gave a 48-50 px radius and a 58-60 px aperture to a dot 5-9 px across, and nothing could be measured. Wanted: the size read on the median of the object's stamps over the track (`stamp`), across its direction of travel so a smear does not count, and a reading that is mostly missing or scattered said and replaced by the point aperture. (2) For a point-like thing (extent <= ~10 px) the disc that hears its beat best is often near APERTURE rather than APERTURE_OVER x extent -- a choice per stretch, or a small set of discs paid for as trials, may be the right form: C's real 10.5 Hz line over its continuum, disc 4 / 5 / 8 px, 45.4x / 42.3x / 29.8x (frames 1-720), 30.5x / 35.4x / 38.5x (918-1422), 14.9x / 16.1x / 13.5x (1659-2072); after the blank a planted 4.5 % beat clears the clip's null 90 / 75 % of the time in 4 / 8 px on one stretch and 50 / 0 % on another, but 17 / 60 % on a third, so the best disc varies and 8 px is not always worse. Tried and rejected: a capsule shaped to the smear (radius 2-3 px, the measured 8-11 px tail behind), worse than the 4-5 px disc on every stretch (best 27.4x on 1-720), and a fixed 12-px disc. It changes the numbers the default aperture gives, so (2) waits for Jacob's decision; (1) is a fix. Uap `analysis/cases/pr089/README.md` ("The aperture for C"), `analysis/tools/pr089_aperture_sweep.py`, `pr089_aperture_eval.py` | uap PR089, 2026-10-23 | `flicker` | (1) built on branch `extent-stack` (76e7fda, narrowed in bdce895 so a frame too small for any stamp keeps the point's disc: on the Svanstrom set the first version changed 32 of 432 calls, 23 of them that way): all suites and golden pass, no golden number moves; Svanstrom 3 of 432 calls change, bird and false-call rates as on main; known-beat birds (PURSUE Table 1 cases, PR089 C, Galileo flyers) 17 -> 21 of 38 found (PR097 objects 1, 3-5 had 17-39 px apertures), unmerged. (2) studied 2026-10-24 (uap `analysis/sweeps/svanstrom/README.md`, "The aperture study"): the ring decides, not the disc -- 4 px with its ring at 7-10 px loses PR135 5-6 and PR097 1, 4 to refusals, at 9-14 px keeps them. Best: Rcap, `sized`'s ring and background offset with the disc capped at 6 px, 26 of 38 known beats (default 21; +PR085, PR097 2, PR089 C s030 and s033), but Svanstrom false calls 12 -> 16 of 307, all close helicopters at 1.6-7.8 % (under the candidate 8 % floor). Waits for Jacob: Rcap as default, with or without an amplitude floor, or as an option |
| 0.4 | k from a slew: the north pointer against the scene's shift | V2 | `scale`, `symbology`, `layers` | built 2026-10-19 (`mcdonald slew`, method §17; merged to main 2026-10-20, unreleased): synthetic pans within 7 %, PR148 NO POWER (glyph unreadable at the slew's start, a hold that is not steady); the known-answer test on a clip with the sensor's azimuth and field in its data bar (PR051) and the other pointer clips to do. Zoom states merged to main 2026-10-21 (`mcdonald zoom`, unreleased): windows cut at every blank burst, claims compared within a state, and across a measured step the ratio of c against the imagery's -- the objective's "validated on a clip with a zoom transient": PR27 267 -> 517 px/deg across x2.000, PR057a 276 -> 584 across x2.001, both agreeing (`tools/zoom_check.py`) |
| 0.4 | focus: sharp-means-far; the defocus disc's profile and shape | V5 | `forensics`, `kinematics` | to do |
| 0.4 | horizon geometry: range below it, height above it | V12 | `kinematics` | to do |
| 0.4 | the haze bound for dark objects | V15 | `kinematics` | to do |
| 0.4 | the streak as a sub-frame light curve | V14 | `forensics`, `flicker` | to do |
| 0.4 | the admissible region in (R, Ṙ) with sampled speed and size distributions | A10 | `kinematics` | to do |
| 0.4 | edge-crossing fits: crossing time times angular rate against angular size | A16 | `kinematics` | to do |
| 0.4 | the time-distance diagram along the track | A13 | `figures` | to do |
| 0.4 | the dimensionless numbers (smear, turn, obliquity, parallax) and the projective constant-velocity test | the kinematic notes | `kinematics`, `report` | to do (parked once as a paper figure; right as a report fact) |
| 0.4 | v(t) with a band; the average speed's honest error; acceleration as a likelihood ratio | K1 | `kinematics`, `report` | to do |
| 0.4 | conditional simulation: planted tracks with the measured covariance | K8 | tests | to do |
| 0.4 | each template's own error from its correlation peak | K9 | `layers`, `comotion` | to do |
| 0.4 | the object's track regressed on the scene's shift (how much of the motion is the scene's) | K10 | `integrity`, `comotion` | to do |
| 0.4 | turbulence as a witness of range | T16 | `groups` or new | to try; speculative |
| 0.4 | τ from looming or from the light curve; the aspect θ = atan(ωτ) with no range; validated on Galileo aircraft with ADS-B | I6 | `kinematics` | to do |
| 0.4 | a turn as a load-factor curve, n = √(1 + (ωV/g)²): the turn rate from the track, the speed unknown, against each class's limit | Av10 | `kinematics`, `figures` | to do |
| 0.4 | speed in body lengths per second with a sourced class table (aircraft types, the DoD drone groups, birds); for an unresolved object, blur widths per second as its lower bound | Av11 | `kinematics`, `report` | to do |
| 0.4 | the value of information per unknown, per clip: how much knowing k, R, θ or v_own would change the report's answer (e.g. P(v < 30 m/s)); the council's asks ranked by it | D8 | `kinematics`, `report` | to do |
| 0.4 | `integrity`'s zoom across each transient fitted by `forensics.zoom_fit` (the whole picture, the overlay zeroed, the scale by prominence, "unknown" where it has not found it) in place of `zoom_ratio`, which looks within 60 px of the boresight and read x1.0 at every switch of AARO's Puerto Rico clip | the zoom handoff (`docs/handoff-zoom-slew.md`, Open) | `integrity` | to do; it changes the numbers `integrity`'s report gives, so it waits for Jacob's decision |
| 0.4 | a marginal zoom fit made trustworthy by a second, independent pair of frames either side (a frame or two further out) agreeing on the scale, without lowering the bar for traps: Puerto Rico's 142.6-s switch fits x1/3.096 (the readout's 1/3) but leads the next scale by only x1.14, as PR27's 89-s haze trap does | the zoom handoff (`docs/handoff-zoom-slew.md`, Open) | `forensics`, `zoom` | to do |
| 0.4 | the PURSUE pointer sweep re-run with `slew` and its zoom states, in place of the uap repository's `pointer_slew_states.py`: every clip's states, its claims per state, and the c-ratio check at each measured step (the fixed-FOV-ladder question, x2.00 and x5.8-5.9 so far) | the zoom handoff (`docs/handoff-zoom-slew.md`, Open) | sweep, `slew`, `zoom` | to do |
| 0.4 | `slew`'s figure as one row per zoom state (the windows of a state together, the c-ratio check across each step) in place of one row per window, which is 64 inches tall on PR27 | the zoom handoff (`docs/handoff-zoom-slew.md`, Open) | `slew`, `figures` | to do |
| 0.4 | `camera` and `zoom` read each other: `zoom`'s measured steps given to `camera` as events and taken out of a track as zooms; `events`' picture steps given to `zoom.plan` as its bursts | the camera handoff (`docs/handoff-camera.md`, Open) | `camera`, `zoom`, `events` | to do; FLIR1's zoom has no blank, so `zoom` does not see it and `camera` finds it from the object |
| 0.4 | the released-track null on a second clip, one with a lock loss and a readable line-of-sight rate before it: in PURSUE only PR051 (the MTS-B breaks lock, and its north pointer gives the azimuth at unit gain) | the camera handoff (`docs/handoff-camera.md`, Open) | `camera`, `slew` | waits on PR051, parked in the uap repository since 2026-08-27 (the maintainer's call); GIMBAL and GOFAST stay locked, PR111's azimuth is redacted |
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
| 0.7 | learned point trackers and segmenters as proposers | the workstation note | GPU extra | to try; never the judge |
| 0.7 | blind marks: frames the tool chooses, marked with nothing drawn, and their distance to the track reported | P7 | `mark_qt`, `tracksheet` | to do |
| 0.7 | an airborne benchmark with known ranges (the open Airborne Object Tracking set: aircraft, helicopters and birds seen from an aircraft, GPS ranges for the planned aircraft): Find on dim airborne points; range from span and the blur-width bound checked at known range | Av8 | tests, benchmark | to do |
| 0.7 | a hidden-Markov track-before-detect bank after a close-minus-open filter (detect-and-avoid practice) | Av9 | `propose` | to try, beside A6 |
| 0.7 | hold-aware linking and the hold composite. Holds are read on the object's own patch: its patch repeats while the frame around it changes, which `pictures()`' whole-frame rule cannot see. Each hold is collapsed to one picture, with its frames averaged as repeats; links run over pictures, not frames; the pictures are stacked aligned on the object and rotated to its motion. The object at each new picture, and the trail behind it at the frame-rate spacing, are reported apart. Case: uap PURSUE PR39. Its object holds 2-3 frames (~10-15 pictures/s at 30 fps, jumps of 60-70 px at a mean 20 px/frame) while whole-frame differences stay at 0.06-0.20 DN; follow failed on Jacob's marks; fainter copies trail at ~20 px. Uap `analysis/cases/pr39/` (README, `pr39_composite.png`, `pr39_spacetime.png`) | uap PR39, 2026-10-23 | `autolink`, `flicker.pictures`, `figures` | to do |
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
| 0.9 | mark colours everyone can read; a colour-vision test in the suite | V6 | `mark_qt`, tests | to do |
| 0.9 | the Marey composite (the track in one figure) | V11 | `figures` | to do |
| 0.9 | a model card for every stage that bears a gate (its use, completeness and false alarms per control class, where it has no power, its traps); a datasheet for the 1.0 catalog recording the net | D14 | docs | to do, with P10 |
| later | a horizon refraction ray tracer (the mirage null) | A20 | new | deferred unless a horizon case needs it |
