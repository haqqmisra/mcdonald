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
  ten PURSUE videos, the five Galileo Project flyers, the pico-balloon launch, and the two
  folders of flicker goldens. No case files yet.
- **The research record**, kept with the PURSUE analyses outside the repository: a beat sweep
  of all 126 PURSUE videos with an object to look at (85 beat-tested; a whole-video pass over
  122 clips followed 1,576 objects), with ten videos holding objects that beat at wingbeat
  rates -- PR135's six and nineteen more in nine other videos, about 8 % of the sensor videos;
  a first look at gliding birds; a search still running for what the pass could not measure;
  five surveys of methods from other fields (astronomy, seismology, SETI, geostatistics, film
  and the visual arts) with 84 ranked ports, summarised in the ideas bank at the end of this
  file; and four clips of a drone show from the same infrared cameras as the flyers.
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

The wingbeat test is the package's one result so far that changed what a video is taken to
show. This release makes it a calibrated detector with its false-alarm rate written down,
and puts the cases the two papers rest on into files anyone can open and rerun.

**Objectives.**

1. **Goldens green.** Narrow the lost-at-the-troughs rule so that PR23 and the balloon pass
   as before while PR097's dots keep their beats; run golden, not only the no-video suites,
   before any release. Release what is on `main`.
2. **The gates decided by evidence.** For each of the astronomer's and the seismologist's
   tests: judged on the goldens (PR135's six, the five flyers, PR41, PR44, PR099), the
   controls (PR23, the balloon, PR055, PR071) and the sweep's own background apertures (the
   false-alarm rate by construction) and planted beats (completeness), each gate goes on, stays
   off, or becomes a reported reading. The bird headline rule -- the whole track beats, or two
   windows that do not overlap pass at one frequency -- is the maintainer's call, pending.
3. **The look-alike table on every beat.** The rhythms a sensor chain can make -- the frame
   rate's aliases of 50 and 60 Hz mains and 400 Hz aircraft power, pulldown and held-picture
   cadences, the codec's lines -- marked on every beat the way the codec's lines are now, with
   the clock-steadiness of the beat beside it (a supply's line does not wander; a wingbeat
   does). The morphology tests for a beat near 10 Hz (its depth along the track, its wander,
   the fixed-core width) written down, since the bird paper's Table 1 has two such objects.
4. **A second, gain-proof reading: the beat in the position.** A periodic part of a track
   makes its variogram dip at the period (the hole effect). From the track alone, with no
   photometry, the five flyers give their beats within 0.1 Hz. A light-weighted centroid does
   not move when the gain changes, so this reading cannot be made by the camera's gain. On a
   moving camera it needs registration, or members' differences.
5. **The report's grade and checklist.** A quality grade (A-D) by what is constrained; the
   verification checklist beside it (what was excluded, what was not screened out, what could
   not be tested); "possibly not an object" as a stated outcome.
6. **Levels.** "Clipped" as a flat top, not a grey value; the out-of-range share in
   integrity's record; extraction with headroom once the goldens are re-measured. The one
   port that changes a verdict the package already gives (PR135's members sized rather than
   "clipped"), and the smallest.
7. **The reference cases as files.** A `.mcdonald` file in the data folder for every video the
   two papers rest on: PR113 and PR149 (the Technical Note), PR43 (the full paper's third
   case), PR135 and the nine other bird videos of the Scientific Reports Table 1 (PR41, PR44,
   PR077, PR079, PR085, PR088, PR097, PR099, PR141), and PR144 (the method note's clip) --
   marks, tracks, each object's report, and a note saying what to look at. A check that a case
   file reruns to its numbers (open it, run each object, compare the report's fields), so that
   "reproduce our analysis" is one command. The videos the data folder does not yet hold are
   named in its README with their source.
8. **The sweep's tools in the repository.** The scripts the beat sweep was done with (propose
   over windows, pick with a recorded reason, link, flicker, the cadence and frame-phase
   checks, the strict gate) become `tools/sweep/`, so the corpus statement can be re-run by
   anyone with the videos. This is the seed of 0.6's batch mode.
9. **A public project's housekeeping.** The no-data suites on every push and pull request on
   GitHub's free Linux runners; the funder acknowledged in the README; the donation route
   unchanged.

**Hypothesis-driven:** the bird test, finished. **Hypothesis-neutral:** the whole-video pass
with calibrated nulls, and its completeness.

**Could feed:** the Scientific Reports revision (the look-alike and morphology tests);
a note on the corpus beat census (how many videos beat, and what the search could not have
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
   the product of crossing time and angular rate against angular size.
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

- **Drones** (footage in hand: four clips of a drone show on the same infrared cameras as the
  flyers, 60 frames a second). Predict first, then measure: rotor blade-pass frequencies and
  where they alias through the frame rate (the look-alike table of 0.3 turned round); a
  formation's rigidity by double-difference separations and the group's common motion; the
  choreography (moves in step across the whole group, where birds are out of step); light
  cadences; a steady hover with no beat; the thermal signature of a warm core.
- **Helicopters** (control footage expected from the same cameras): main-rotor and tail-rotor
  blade-pass rates and their aliases; the exhaust plume; size and aspect.
- **Aircraft** (expected likewise): anti-collision strobe trains, caught whole by folding the
  light curve on the pulse period with the strobe as the positive control; navigation lights;
  constant velocity on a straight line; contrails; engine heat.
- **Balloons.** The payload's swing (`tether`: a hanging point is a clock; on hold, since it
  needs the payload resolved) and the balloon's recoil against it (tried, parked: every PURSUE
  clip refused it for a stated reason). What remains for a point source: no self-propulsion,
  so motion with the local wind field (`comotion`, kriged within the object's layer); a
  constant angular rate on a straight line; a mylar balloon's mirror in the infrared. The
  honest outcome may be that a point-source balloon has no range-free signature. If so, say
  so, and close it.
- **Gliding and flap-gliding birds.** The flicker test finds flappers and misses gliders by
  construction; seabirds glide most of the time. Four tests from the gliding theory: flap
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

**Needs:** the helicopter and aircraft footage; hand marks on the long gliding candidates;
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
| PR135's birds (Scientific Reports) | submitted | 0.3's look-alike and morphology tests, for the revision |
| The corpus beat census | not started | 0.3, 0.6 |
| A drone show in infrared | not started | 0.5 |
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

Still open:

6. **The bird headline rule and the flicker gates** (0.3).
7. **The catalog's case files** (1.0): made by the batch run with an agent's picks and the
   maintainer's look, or by hand.

## The ideas bank

The five surveys' ranked ports, grouped by the release each is scheduled in. The "from"
column is the survey and its rank there (A astronomy, S seismology, T SETI, K kriging and
Gaussian processes, V film and the visual arts), so an entry can be traced back to the note it
came from. *Shipped* means on `main` at 0.2.20 with its gate off; *parked* means tried and set
aside for the reason given. New ideas go at the bottom of the release they belong to, with a
"from" of their own.

| release | port | from | lands in | status |
|---|---|---|---|---|
| 0.3 | nulls by scrambled surrogates and time slides; injection-recovery as reliability and completeness | A1 | `flicker`, sweep | shipped; gate to decide |
| 0.3 | common-mode removal (the frame's level, the apertures' shared component) | A2 | `flicker` | shipped; gate to decide |
| 0.3 | fold-and-difference images at the beat | A3 | `flicker`, `figures` | shipped |
| 0.3 | Lomb-Scargle with the window function and a false-alarm probability; held and lost frames as missing | A4 | `flicker` | shipped; gate to decide |
| 0.3 | multitaper spectrum, harmonic F-test, coherence with error bars | S1 | `flicker` | shipped; gate to decide |
| 0.3 | the noise as a distribution (per clip) | S3 | `flicker`, `figures` | shipped |
| 0.3 | short records: Sompi frequencies with decay | S4 | `flicker` | shipped |
| 0.3 | the comb, the gliding fundamental, ridge tracking | S6 | `flicker` | shipped |
| 0.3 | phase coherence and the array F-statistic for members in step | S8 | `flicker` | shipped |
| 0.3 | one-bit second reading | S11 | `flicker` | shipped |
| 0.3 | the beat as a damped oscillator against red noise; its stability over time | A17 | `flicker` | to do |
| 0.3 | the look-alike table per clip (frame-rate aliases of mains, aircraft power, pulldown, held pictures) | T1 | `flicker`, sweep | to do |
| 0.3 | the 10-Hz morphology tests (depth along the track, wander, fixed-core width) | T2 | analysis, then `flicker` | to do |
| 0.3 | trail OFF and in-gate OFF apertures | T3 | `flicker`, `layers` | to do |
| 0.3 | the beat's footprint fitted on the fold (compact and centred, or a row, column or line) | T5 | `flicker` | to do |
| 0.3 | the verification checklist in the report | T10 | `report` | to do |
| 0.3 | clock-steadiness of a beat | T11 | `flicker` | to do |
| 0.3 | the beat in the position (the track's hole effect) | K2 | `flicker`, `groups` | to do |
| 0.3 | a quality grade A-D on the report and the lists | S17 | `report`, `several` | to do |
| 0.3 | levels: clipped as a flat top; range and out-of-range share; extraction with headroom | V1 | `forensics`, `integrity`, `clip` | to do |
| 0.4 | k from a slew: the north pointer against the scene's shift | V2 | `scale`, `symbology`, `layers` | to do, first |
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
| 0.5 | flap bouts: change-point segmentation of the band envelope | S5 | `flicker` | to do |
| 0.5 | small rate changes along the track by stretching | S15 | `flicker` | to do |
| 0.5 | the four gliding tests (bouts, slow modulation, circling, skimming) | the gliding theory | new | to do |
| 0.5 | double-difference separations for a formation's rigidity | S14 | `groups` | to do |
| 0.5 | differential image motion within a group | A18 | `groups` | to do |
| 0.5 | polarisation of the jitter (platform or own) | S16 | `groups`, `integrity` | to do |
| 0.5 | pulse-train fold with the strobe as positive control | T14 | `flicker` | to do |
| 0.5 | a known lamp measured at its alias | T13 | analysis | to do, if a clip exists |
| 0.5 | the exotica list and harness: one of everything after every change | T9 | tests, sweep | to do |
| 0.5 | the discriminant plot with the control populations; screening language | S20 | `figures`, `report` | to do |
| 0.5 | kriged flow at the object within its layer, with an edge flag | K3 | `comotion` | to do |
| 0.5 | the tether's bootstrap block length | K7 | `tether` | to do |
| 0.5 | azimuthal renormalisation around the core (a tether or plume in glare) | A19 | `tether` | to do |
| 0.5 | a search over the pendulum's own motion for a payload too faint for single frames | the tether notes | `tether` | to do |
| 0.5 | the balloon's recoil against its payload (`wobble`) | the tether notes | -- | parked: refused by every PURSUE clip tried, each for a stated reason |
| 0.5 | the insect tests: defocus, platform motion, Strouhal, the sensor's time constant | the insect note | `forensics`, `flicker` | to do |
| 0.6 | `plant`: synthetic objects and look-alikes through the whole chain | T4 | new | to do |
| 0.6 | recovery rate and the search's negative half | T6 | sweep | to do |
| 0.6 | the aperture pass rate against the object pass rate across the pass | T8 | sweep | to do |
| 0.6 | anomaly ranking over the pass | T12 | sweep | to do |
| 0.6 | completeness from the pass's own record | S19 | sweep | to do |
| 0.6 | corpus noise models | S3 | sweep | to do |
| 0.6 | a dense flow field of the scene with a validity mask | A14 | `layers`, `comotion` | to do, GPU |
| 0.6 | where and when to measure the shift field next (the kriging variance as a design) | K11 | `layers` | to do |
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
| 0.8 | the data bar and mode annunciator readers; the zoom chain | the old roadmap | `symbology` | to do |
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
| 0.9 | mark colours everyone can read; a colour-vision test in the suite | V6 | `mark_qt`, tests | to do |
| 0.9 | the Marey composite (the track in one figure) | V11 | `figures` | to do |
| later | a horizon refraction ray tracer (the mirage null) | A20 | new | deferred unless a horizon case needs it |
