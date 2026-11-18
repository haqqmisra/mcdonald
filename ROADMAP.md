# Roadmap to 1.0

Rewritten on 2026-11-17 at version 0.5.7 and taken by the maintainer that day ("Take it"). It replaces the plan
written on 2026-10-16 at version 0.2.20, which is kept whole as
[docs/history/roadmap-2026-10-16.md](docs/history/roadmap-2026-10-16.md). Where the code, the tests, the method notes
or the ideas bank cite "ROADMAP 0.3 objective 2" or "decision 6", they mean that file; its decisions are carried
below under their old numbers. This file is the plan; [CHANGELOG.md](CHANGELOG.md) is what happened.

The goal of 1.0 has not moved: **every PURSUE video has a reproducible case file, and every idea we have for getting
information out of those videos has been tried, shipped or set aside with a written reason.** The 1.0 software paper
goes to the Journal of Open Source Software (JOSS), which accepts the repository from 2027-03-25.

## Where this starts (0.5.7, 2026-11-17)

- **The package.** 38 commands, 86 modules and about 69,000 lines (24,000 a month ago); 31 test files; 65 method
  notes. A window with one button, a command line for agents, a case file to send. Releases 0.3.0 (2026-10-19), 0.4.0
  (2026-11-01), 0.5.0 (2026-11-08) and 0.5.7 (2026-11-15), on PyPI and Zenodo, with macOS and Windows runs before
  each tag.
- **Of the old plan:** 0.3 (the beat held to account, the reference cases as files) and 0.4 (the unknowns) are
  released. 0.5.0 (the controls harness, the bird floor from a null, AARO's resolved cases run blind) is released.
  Most of what the old 0.6 asked for is built and released too: `batch` (all 144 PURSUE videos run once: 786 rows,
  696 objects), the graphics card under `layers`, `integrity` and `flicker`, `plant`, `rank` and `noise`. Not begun:
  finding without a hand (old 0.7), most of the displays (old 0.8), the walkthrough (old 0.9).
- **In 0.5.8 (2026-11-17), since this was written:** Find sooner with the same list; `layers --dense` and its option in
  the window; the planted objects through `batch`, with a table of what was found and of the beats, video by video;
  and the drift paper's release, below.
- **Known answers in hand.** The Yemen clip, AARO's Puerto Rico lanterns and the Santa Barbara helicopter (the drift
  paper's three); AARO's fourteen resolved cases; the labelled infrared set (432 tracks of birds, drones, airplanes
  and helicopters); the five Galileo Project flyers; and since 2026-11-12 the Galileo Project's triangulated objects
  near Las Vegas, whose range, height and velocity are known: 40,785 objects, 13,697 of them aircraft with ADS-B
  tracks and about 3,000 clouds moving with the wind.
- **Papers.** The kinematic limits note (AIAA JAIS) and the bird paper (Scientific Reports) are in review. The
  wind-drift paper is drafted and cites 0.4.3. N. Long's paper on kinematics from georeferenced imagery was revised
  on 2026-11-01.
- **Machines.** The workstation and its graphics card are on the desk; Harvard's Cannon runs every suite in minutes.
  Compute no longer sets the order of work.

## What the first month taught

1. **Known answers found the defects; surveys found the ideas.** Every set of footage with a known answer changed
   what a report says: the lanterns and the helicopter set the beat rule in `drift`, AARO's balloons found four
   defects in `tether`, the labelled set gave the bird floor, PR051's data bar found three rules in `drift`, and the
   triangulated objects found seven (N1-N7). No survey port did as much for what a report can be trusted to say.
2. **Building outran reading.** Nine agents built in one day what takes a person weeks to read. The open decisions
   and the changed sentences waiting for the maintainer are spread over five handoff files. A report-changer is not
   finished until he has read it.
3. **Papers set the order.** The work that mattered most was pulled by a paper that needed it: the bird paper's
   controls, the Technical Note's unknowns, the drift paper's tests.
4. **A theme a minor version did not hold.** 0.5.7 carries most of the old 0.6. Version numbers below name a state
   to reach, not a theme to work inside.
5. **The ideas bank grows faster than it empties.** It holds 452 rows: 128 shipped, 62 measured, and 184 theme rows
   still open. "Exhausted" needs a rule for closing rows (decision 13).

## Principles

Kept from 2026-10-16, in the maintainer's words:

- **In James McDonald's spirit.** Treat the subject with ordinary scientific instruments: reconstruct what the record
  shows, bound what can be bounded, eliminate the conventional explanations symmetrically, and state the residue
  without overclaiming. Presume nothing either way.
- **NO POWER is an answer.** A test that cannot decide a question says so and names what is missing.
- **Controls before claims.** Every class gets what birds got: footage of the thing, its predicted signature, the
  test, and the test's false-alarm rate on everything else.
- **Two approaches, both kept:** hypothesis-driven (a known class's signature, searched for) and hypothesis-neutral
  (everything the pixels record, with calibrated nulls).
- **The unknowns first:** the scale *k*, the range *R*, the aspect *θ* and the platform's velocity.
- **Expect the unexpected.** A finding that reproduces from a case file is a paper whenever it comes.
- **Two audiences, one job.** Everything the window does has a command, and everything a command does, the window
  can do or show.
- **No number changes silently.** **A threshold comes from a null**, with its rate stated.
- **Plain words in the window; the report leads with its conclusion; no pop-ups; boxes only as tall as what they hold.**
- **Nothing invents detail.** A learned tracker may propose; it never judges.
- **A graphics card is never required of a user.** The CPU is the reference.

Added on 2026-11-17:

- **A paper pins a release.** Each paper cites one version, and every number in it is held by a test or a golden in
  that version, so a later release cannot move a submitted number unseen.
- **A known answer is worth more than a new test.** When footage of a known object arrives, it is run blind before
  anything else is built, and what it breaks is fixed first.
- **Nothing is released that the maintainer has not read.** Open questions and changed sentences wait in one file.

## The releases at a glance

| version | state to reach | done when |
|---|---|---|
| **0.5.8** | The drift paper's release | every number of the drift paper, on its three videos and on the triangulated clouds and aircraft, comes out of the released package by a documented command; each rule of the wind test has a measured rate |
| **0.6** | Known answers at scale | the triangulated objects are a standing test of drift, size, speed and the beat; new footage of known objects goes in by one route and is run blind; every word a report's conclusion can use has a rate on things that are and things that are not |
| **0.7** | The catalog, object by object | `batch`'s table has a row an object; completeness per video from planted objects; the object the record describes found first on a stated share of a benchmark; a provisional case file for every PURSUE video |
| **0.8** | The displays and the sensor's record | the data bars that are not redacted are read to the frame; what the pixels record of the sensor and the file is in `integrity` for every clip |
| **0.9** | The walkthrough | a new person on each platform completes it from the docs alone; the same steps run as a test; the file formats declared stable; the JOSS checklist met |
| **1.0** | The catalog closed | a looked-at case file for every PURSUE video in the data package; the ideas bank closed by its rule; JOSS submitted |

Patch releases go on as now. A paper may ask for a release of its own at any point, as 0.5.8 does.

## 0.5.8 -- the drift paper's release

*Open-source tests for wind-borne drift in airborne sensor video, applied to an object struck off Yemen* cites 0.4.3.
Since then the wind test from the lines of sight gained a model's own error, the hold-still rule, the wind's change
with height, the heading box's offset and the rays' own scatter, and the beat test a rule against chance. The paper
is to add the triangulated clouds (which should drift) and aircraft (which should not) as two populations beside its
two controls.

**Measured on 2026-11-17, at the v0.5.7 tag** (239 objects, lines of sight from two or three sites; the beat test on
envelopes of 0.5.3, still to be made again):

| group | n | drifting (tentative) | cannot say | not drifting |
|---|---|---|---|---|
| aircraft with ADS-B tracks | 80 | 0 | 16 | 64 |
| clouds | 119 | 64 | 49 | 6 |
| two different clouds matched (a false low point) | 40 | 21 | 19 | 0 |

No aircraft is called a drifter. Of the six clouds called not drifting, two climb or dive at over 20 m/s and are not
clouds, one needs 20 m/s through the air, and three beat on the old envelopes. The slowest aircraft here needs 53 m/s
through the air, so nothing in the set flies between a cloud and that.

**The maintainer's word, 2026-11-17:** build items 1, 2, 4 and 5; measure item 3 first and bring him the choice; the
release goes out when these are done and the graphics-card session then running has finished, which is enough card
work for it.

**Built on 2026-11-17 and released as 0.5.8** (CHANGELOG.md; method sections 34 and 66 to 69). All five items below,
and from what they found: the wind test from the lines of sight fails a body 10 m/s beyond its whole tolerance before
it asks how well the velocity is fixed, and takes a model's wind error as 2 m/s; the wind test from the ranges has a
rule with the model's error in it and is no longer a strong test; `flicker` reads a beat against the track's own
jitter; and the beat test says the band it listened in. The table as the paper will quote it, with each ring camera
a camera of its own and its pointing known to 0.7 and 0.4 degrees: no aircraft of 80 called drifting and all 80 not
drifting; 44 of 119 clouds drifting, 74 cannot say, 1 not drifting (two things matched as one). Set for after it,
each measured first: a gate for a path that misses its lines of sight, a hold-still rule against the winds' middle,
`flicker`'s held pictures asked of the object's own frames, the jitter read window by window.

**What the package lacked for it, as written before the work:**

1. **Fixed cameras as an input of their own.** The lines of sight of several sites go into `mcdonald drift` today by
   a workaround kept outside the package: the sites are written as one aircraft that jumps between them on frames
   at 180 a second, with a grey placeholder for the video. A reader cannot repeat that from the release. Wanted:
   rays with a time and a camera's name, no video needed, and each camera with its own azimuth reference (today all
   rays share one). Held to the 239 runs above.
2. **Planted fliers in the package.** How slow a flier the wind test would have caught, on a case's own geometry
   and winds: bodies given 5 to 50 m/s through the air in eight directions, seen along the real lines of sight with
   the fit's real errors. The paper's figure of this for the lanterns comes from a script outside the package, made
   under the tolerance of 0.4.3 (7.2 m/s, now 10.5). And since no known flier in hand is slower than 53 m/s, plants
   are the only test of the range where birds and small drones fly. Every "consistent with drift" would then state
   the slowest flier it excludes.
3. **The wind test from the ranges, held to the same standard.** The Yemen clip's own route. It passes when the
   winds' difference across the heading lies the way the motion does and the airspeed needed is one the aircraft
   has. It has no term for a model's error, none for the wind's change with height, and no measured rate; the
   route from the lines of sight has all three. Wanted: the model's error on a difference of winds between two
   heights, measured against weather balloons, the rule stated with it, and the rate at which it passes drifters
   and fliers at 10, 25 and 50 m/s. **It may change what the Yemen clip's wind test says, so the maintainer decides
   before it is built.**
4. **The model's wind error held on days it was not set on.** The 3 m/s was chosen on the same clouds it is scored
   on: 119 clouds from 16 dates, 108 of them from nine days of late May, one place, one model. Wanted: its rate on
   dates left out before looking, with errors from a bootstrap over days, and its rate against weather balloons
   elsewhere (measured once in the air survey: a median of about 2 m/s, 5-6 at the 95th percentile).
5. **The beat test's inputs made again** by the cited release's `flicker`, on every camera's clip.

After the paper, not for it: a command that fetches a place's archived winds; a few dozen triangulated objects as
goldens in the repository, if the Galileo Project agrees to their release; `drift` in the window and in the case
file, which the two-audiences rule has asked for since 0.4.0; a finer model of the wind's error by height, place and
season (IDEAS W7); a reader for PR051's data bar (0.8).

## 0.6 -- Known answers at scale

The old plan gave each class of object its own controls as footage arrived. The triangulated objects, and the
footage of known objects expected in the coming weeks, make that one job with one route in.

1. **The triangulated objects as a standing test.** A fixed sample, chosen once and split into a part to set rules
   on and a part to score them on, run after every change to `drift`, `kinematics`, `report.extent`, `flicker` and
   `rank`: drift's verdicts; the speed across the line of sight and the size against ADS-B; the beat's false alarms
   on clouds and aircraft; two cameras at once. They are also the controls `rank` lacks at the corpus's own widths:
   aircraft seen as points and small blobs at 2 to 40 km.
2. **One route in for new footage.** A table of truth for a set (what each object is, and what is known of its
   range, size and speed), a blind run through `mcdonald run`, and a scorecard, as `tools/aaro_blind.py` does for
   AARO's cases. A part of every new set is put aside before anyone looks, as the held-out third of PURSUE was.
3. **The classes, as footage allows:** a drone's rotors and a formation's choreography; a helicopter's rotor from
   the air; an aircraft's strobes at night; a balloon with something under it; flames; gliding birds (after the
   maintainer's look at the by-eye controls); a background crossing behind the object.
4. **Planted objects through the whole chain**, on the 80 planted videos now and the 144 when the maintainer says:
   completeness per video, and the rule for what counts as an object set against it.
5. **Rates in the report's own cell.** Each conclusion's false-alarm and miss rate at the case's own size, contrast
   and frame rate, with errors over videos, not tracks.

**Needs:** the new footage; the Galileo Project's word on what of theirs may be published; airborne infrared of
aircraft and helicopters.

## 0.7 -- The catalog, object by object

1. **A row an object.** Today one bird can be seven rows and a flock one. Pieces of one track joined across a gap;
   a group split into its members with no count given; objects in view for under 40 frames measured, not only counted.
2. **Finding without a hand.** The benchmark first (every recorded track and hand mark), then the methods of the
   old plan's 0.7, each held to it: the link gate in units of the track's own error, thresholds from the frame's
   own noise, objects held still on a still scene, shift-and-stack for what is below a single frame's threshold.
3. **The audit in the window:** frames drawn for a person to check, so a case file says how much of it was looked at.
4. **A provisional case file for every PURSUE video**, and the reference case files made again once.

## 0.8 -- The displays and the sensor's record

As the old plan's 0.8, in this order: readers for the data bars that are not redacted, PR051's first, because a
read bar opens `drift`'s strong tests and the scale on more of PURSUE; the clock (frame stamps, interlace, variable
rate); levels and gain; photometry under them.

## 0.9 -- The walkthrough

As the old plan's 0.9: the walkthrough as a document and as a test on the three platforms; `mcdonald check`; the
case-file format and the JSON fields declared stable; the JOSS paper drafted. The site and the exercises exist.

## 1.0 -- The catalog closed

A looked-at case file for every PURSUE video, in the data folder and a Zenodo data package; the corpus statement
(how many videos beat, which unknowns each constrains, what the search could not have found); the ideas bank closed
by decision 13's rule; JOSS submitted.

## Papers

| paper | status | waits on |
|---|---|---|
| Wind-borne drift (Scientific Reports draft) | drafted; cites 0.4.3; the triangulated controls designed, not written | **0.5.8** |
| Kinematic limits (AIAA JAIS Technical Note) | in review | nothing here |
| PR135's birds (Scientific Reports) | in review | the reviews; then the amplitude floor (decision 7) |
| Kinematics from georeferenced imagery (N. Long and others) | revised 2026-11-01 | nothing here |
| Known answers from three cameras: what a single camera gets right | not started | 0.6 |
| The corpus statement, with completeness | not started | 0.7 |
| Birds, drones, airplanes and helicopters in one infrared band | not started | 0.6 |
| The methods paper (RAS Techniques and Instruments) | at 1.0 | 0.6-0.8 |
| The software paper (JOSS) | at 1.0, from 2027-03-25 | 0.9, 1.0 |

The other rows of the old table (a drone show in infrared, gliding birds, the metallic orbs, PR117's cabin sound)
stand as they were.

## What every release is held to

- Every suite; the goldens (the real clips at their published numbers); `tools/find_rank.py --link` after any change
  to Find or the link; the controls harness after any change to `flicker`; `tests/test_drift.py`'s known answers
  after any change to `drift`; macOS and Windows runs on the release commit, before the tag.
- A new measurement ships with its method note, a planted-signal test, a golden, and its rate on the controls.
- No number changes silently. A version with every release.
- NO POWER stays an answer, and nothing invents detail.
- Every feature in both shells, tested in both.
- Plain words in the window; the conclusion first; no pop-ups; boxes as tall as their content.

## Working rules

1. **Public.** Everything in the repository is suitable for public release, and nothing in it depends on files
   outside it but its data folder.
2. **Data.** Footage, goldens and case files go in the data folder beside the repository, listed in its README with
   `SHA256SUMS`, and are published to Zenodo with releases.
3. **Research.** Notes, sweeps and manuscripts are worked outside the repository; the toolkit's documents cite a
   working note by description, never by path.
4. **Compute.** Every run of the package on the development machines goes through the job scheduler, niced, from a
   snapshot of the source.

## Decisions

Carried from the plan of 2026-10-16, where each is written in full: (1) 1.0 lands when the catalog is closed; (2)
the docs are MkDocs on GitHub Pages; (3) a card is never required and is used to the full; (5) for a single point no
range-free sign of a balloon survives, and an object with something under it has a test; (6) the flicker gates stay
readings, and a bird is named only from a beat that comes back; (7) the amplitude floor on the bird headline waits
for the bird paper's reviews; (8) report-changers before additions; (11) the review of 2026-11-02. Decisions 9 and
10 (how the catalog's case files are made; when the reference case files are made again) stay open and belong to 0.7.

Decided on 2026-11-17 with this rewrite ("Take it"):

12. **The order above:** the drift paper's release first, then known answers at scale, then the catalog.
13. **How the ideas bank closes.** Every report-changer is shipped or refused. Every theme row is marked once, by
    the maintainer, one survey at a sitting: before 1.0, after 1.0, or never, with the reason. "Exhausted" means no
    row is unmarked and none marked "before 1.0" is open.
14. **One file of open questions.** The questions and changed sentences that wait for the maintainer, now spread
    over five handoffs, are gathered in one file, each with its choices and a recommendation, and a release goes
    out only when the ones it touches are answered.

## The ideas bank

In [IDEAS.md](IDEAS.md): 452 rows on 2026-11-17, each with the survey it came from, the module it lands in and what
became of it. The surveys themselves are working notes kept outside this repository.
