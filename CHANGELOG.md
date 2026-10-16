# Changelog

Every version that went out, newest first. The version is written in one place,
`src/mcdonald/__init__.py`; each release from 0.2.4 on is a git tag and is on PyPI.

## Unreleased (branch astro-flicker)

- The flicker stage reports the seismologist's tests beside its own and the astronomer's (Jacob, 2026-10-15, "Start with
  the flicker upgrade", from `analysis/seismology_methods_survey.md`, its ranked ports 1, 3, 4, 6, 8 and 11; item 8 of
  the module's docstring). None of them decides yet -- `GATE_SEIS` is off, so no published or golden number changes --
  and each is in the fields, printed by `mcdonald flicker`, and said in the notes where it disagrees with a beat the stage
  called:
  - `fields["seis"][track]["line"]` and `["line_windows"]`: the multitaper spectrum (Thomson 1982; four Slepian tapers)
    with the harmonic F-test at the stage's beat -- the chance of one stationary sinusoid there against a continuum
    smooth over the tapers' bandwidth, grain and drift alike, in closed form (F with 2 and 6 degrees of freedom), and
    the chance of one as strong anywhere in the band -- over the stretch the beat is reported from, and again in
    windows of 2 s along it. On grain alone it calls a line at 1 in 100 frequencies, as it should. On the goldens it
    taught something: over a whole track no wingbeat is a stationary line (PR135's member A, 24 % at 7.85 Hz and 311x
    its band, has a chance of 0.78 over its 150 frames), because a bird's rate wanders and its energy spreads across
    the bandwidth, which the F-test's one-sinusoid model counts as continuum -- while in 2-s windows every golden has
    the line (the best window's chance from 6e-4 down to 2e-5). So the stretch's reading is said as what it is, a
    stationary line or none ("a wingbeat's rate wanders"; a hum, a display or a codec's rhythm is one), and the
    windows decide: a track disagrees only with no line in the stretch or in any window. The stationary lines of the
    band are listed too -- member A carries one at 11.59 Hz the Hann spectrum never flagged.
  - `["coherence"]`: the object's curve against each background aperture's, and against the frame's own level and
    contrast (the camera's channels: InSight's comodulation, Charalambous et al. 2021), at the beat -- the
    magnitude-squared coherence by multitaper eigencoefficients in 2-s windows (Thomson & Chave 1991), the level chance
    clears with a probability of 0.01 given the looks, and the phase with its jackknife error. `shared` asks this with
    an amplitude rule; this answers with a chance.
  - `["noise"]` and `<case>_noise.png`: the noise as a distribution (McNamara & Buland 2004's probabilistic power spectral
    density) -- the amplitude spectrum of every 2-s window of every background aperture, their 50th, 90th and 99th
    centiles at every frequency, and the centile the object's own windows' amplitude at the beat sits at, with the share
    of its windows over their 99th. The figure draws the bands with the object's median window spectrum over them.
  - `["sompi"]`: the record as a linear system's output (the Sompi method, Hori et al. 1989; Kumazawa et al. 1990;
    Nakano et al. 1998 on a volcano's long-period events): an autoregressive model at orders 4-12, whose roots that
    hold still across the orders -- within 4 % of one frequency at 70 % of them -- and stand over what the lines leave
    of the record are its lines, a frequency and a growth or decay (Q) each, from a few cycles. Forward prediction
    alone: a decaying line run backwards grows, and a forward-backward fit cancels the decay. On 40 frames a planted
    3-Hz line decaying with Q 20 reads 3.00 Hz, Q about 18; grain alone gives no line.
  - `fields["short_record"]`: with it, a track too short for the stage's spectrum (20 to 59 frames) is read anyway --
    the strongest peak and the Sompi line -- in the fields and a note, "a reading, not a beat: nothing holds it against
    the background". The stage's answer is as before (no power, under the 60 frames a beat needs). A member seen
    briefly beside a longer one likewise. The sweep's Tier 3 records (40-58 frames) get a number where they had none.
  - `["comb"]`: the lines of the window the beat is clearest in, under 0.01, read as a comb -- harmonic tremor, Hotovec
    et al. 2013: a fundamental and overtones at its exact multiples -- the fundamental whose multiples hold the most
    lines within two resolutions with the fewest missing, a line's half never preferred to the line; the stage's `HALF`
    rule reads the same thing from two peaks' heights. None with fewer than two lines on it.
  - `["glide"]`: the fundamental followed along the whole track in windows of 1 s, an eighth apart, about the stage's
    fundamental, and the double about its double, each standing where its window's F-test says so (three tapers): a line
    through it (slope, range, r2), whether the double moves at twice the fundamental where both stand, and where the
    fundamental was taken from the double's half. A planted rate that settles from 4.8 to 3.9 Hz over 3.5 s reads
    -0.10 Hz/s over the track; a steady beat holds within half a hertz; a constant point has nothing that stands.
  - `fields["in_step"]`, for a group's strong members over their common frames at the median of their beats: each
    curve band-passed about it, its instantaneous phase, and the modulus of the members' mean unit phasor over the
    frames -- the phase coherence a phase-weighted stack weights by (Schimmel & Paulssen 1997), 1 in step -- against 200
    copies slid round in time, and the array F-statistic (Melton & Bailey 1957; Blandford 1974): the members' mean
    curve's power at the beat over their residuals', F with 8 and 8(N-1) degrees of freedom under no shared component.
    `common` asks pairs by their cross-spectrum's phase; this asks all of them at once, with a chance. Two points in
    step: coherence 1.00, F past 1e-9; opposite: 0.03, F nought.
  - `fields["fold"][track]["phase_inside" / "phase_outside"]` and a column of `<case>_fold.png`: the fold's question by
    phase -- each pixel of the stamps band-passed about the beat, its phase against the aperture curve's, and the
    coherence of the two over the frames -- 0.75 within the aperture and 0.38 beyond twice it for a point's own beat,
    1.00 everywhere for a gain the whole frame shares.
  - `["onebit"]`: the curve's strongest again with every sample its sign alone (one-bit normalisation, Bensen et al.
    2007): a glint, a level step or a burst of gain cannot outweigh the rest; a beat in the linear reading and not in
    this one was a few frames.
  - `flicker.GATE_SEIS` (off) makes the line test decide: a strong track with no line at its beat under `MT_P`, over
    the stretch or in any 2-s window of it, is set aside, and the finding says so. With it on, the goldens' beats
    stand (see `seis_flicker_goldens/` in the reference-data folder, `tests/reference_data.py`).
  Four tests in test_measurement (`_Flyer` for the glide; `_Gained` for the coherence; a 40-frame `_Beating` for the
  short record). The tether's swing by Sompi, semblance for the velocity search and the corpus noise models are the
  survey's next items, not in this round.
- The flicker stage reports the astronomer's tests beside its own (Jacob, 2026-10-15, from
  `analysis/astronomy_methods_survey.md`, its ranked ports 1-4; item 7 of the module's docstring). None of them decides
  yet -- `GATE_ASTRO` is off, so no published or golden number changes -- and each is in the fields, printed by
  `mcdonald flicker`, and said in the notes where it disagrees with a beat the stage called:
  - `fields["astro"][track]["lombscargle"]`: the strongest beat again by the generalised Lomb-Scargle periodogram
    (VanderPlas 2018; the same numbers as astropy's exact method, checked where astropy is installed) over the frames
    that are samples -- a held picture (`pictures`' `held_k`) or a frame the object was lost on is a missing sample, not
    a sample -- with Baluev's (2008) false-alarm probability over the band, and the sampling's own rhythms read off its
    spectral window (every third frame kept: a line at a third of the frame rate), so that a peak at one is named an
    alias of the sampling as a peak at the codec's line is the codec's.
  - `["scramble"]`: the curve's strongest held against 200 copies of itself scrambled in 0.25-s chunks (Thompson et al.
    2018's scrambled runs; Theiler et al. 1992): the chunks keep the grain, the codec's quantisation and the jitter from
    one frame to the next, their order destroys every rhythm; `p` is the share that stand as high. Said only above
    1/0.25 s, where the scrambling does not also destroy the slow wander the drift test is for.
  - `["common_mode"]`: the frame's own level and contrast (from the frames small, every tracked thing masked out) and
    the background apertures' common mode (the first two components of their standardised curves; SysRem, Tamuz et
    al. 2005) regressed out of the object's curve -- a camera's gain changing, or a display's brightness as a phone
    films it, scales the whole frame, and an aperture's contrast over its ring follows it only by whatever that
    contrast happens to be, in either sign -- with the object's beat before and after, the share of its curve they
    account for (and the frame's alone), and the mode's own strongest frequency (the codec's, where it is).
    `["pixel_phase"]` likewise for where within its pixel the object sits. Each of these is computed over the stretch
    the beat is reported from (`astro[track]["frames"]`), a window or the whole track.
  - `fields["controls"]` and `fields["false_alarm"]`: every background aperture put through the object's own tests as if
    it were the object (the Robovetter's principle: data known to hold no signal, through the whole pipeline, so what
    passes is a false alarm by construction), over the whole track always and through every window with the slower
    nulls.
  - `fields["injection"]`: beats planted in the background apertures at 2, 5, 10 and 20 % of the object's brightness and
    four frequencies across the band, clear of the codec's lines, each judged as the object is: the share recovered, and
    the smallest amplitude recovered at every frequency (completeness; Christiansen et al. 2013). With the slower nulls.
  - `fields["fold"]` and `<case>_fold.png`: the frames folded on the beat (epoch folding; Kepler's difference image,
    Bryson et al. 2013) into a bright half and a dim half of its cycle, the object's stamp (`stamp`, kept from every
    frame by `curves`) averaged over each, and their difference: the share of the change within the aperture against
    the aperture's share of the picture, where it peaks, and how much the rest of the frame changes with it. A beat of
    the object's sits in the aperture; the codec's in blocks; a gain's over the whole scene. Drawn for every beat the
    stage calls the object's own.
  - The slower nulls (the background apertures through every window, and the planting) are run by `mcdonald flicker`
    and `mcdonald run` (`--no-nulls` to skip them) and by `measure(..., nulls=True)`; a test need not.
  - `spectrum` and `peak` are now `deviation` + `_spec` and `_peak` underneath (the same numbers); `drift` and
    `windows` take a `scale`, so a background aperture can be judged as the object is.
  - Tests: five in test_measurement (`test_the_lomb_scargle_periodogram_and_its_false_alarm_probability`,
    `..._scrambled_copies...`, `..._common_mode`, `test_the_fold_puts_the_beat_where_it_is`,
    `test_the_background_apertures_are_judged_and_planted_beats_recovered`), with a `_Gained` clip whose whole frame
    swings in brightness. The goldens (PR135's flock, flyer 5, Galileo flyers 1-4) keep their beats; what the new
    fields say of each is in the pull request.

## Unreleased (branch guard-at-the-beat)

- The flicker stage no longer refuses a track whose "lost" frames are the troughs of its own beat (Jacob,
  2026-10-15). A dark object beating at 25-60 % of its brightness falls under a quarter of its level for a frame or
  two at every trough, so the guard built for PR23's hot roof marked a fifth of its frames lost and refused the
  clearest beaters in PR097. Now, where the lost frames come in 3 runs or more whose median length is 3 frames or less, and
  at least 65 % of them fall in the lower half of the curve's own strongest beat (its frequency read off the curve filled
  across, its phase off the curve as it is, band-passed within 1 Hz of that frequency; chance would give 50 %), the frames are kept and measured as they are, and the finding, notes, `--json`
  (`lost_at_beat`) and the printed summary say so. A crossing (one run of several frames, PR23) is left out as before,
  and a track lost on more than 10 % of its frames for any other reason is still refused. Test:
  `test_a_beating_point_under_its_ring_at_every_trough_is_measured` in test_measurement.

## 0.2.20 (2026-10-15)

- A crash in the window on a Mac, from 0.2.19: Measure stopped the program right after the track sheet's question
  (on GitHub's Mac runner in three runs of three; 0.2.18 and 0.2.17 passed). Python's cycle collector runs in
  whichever thread is allocating, and it freed a closed Preferences page -- 0.2.19's page referred back to itself --
  in Measure's thread; a Qt widget destroyed outside the thread that made it is a crash. The page no longer refers
  back to itself, and while there is a window the collector runs only in the window's thread, from a timer, as
  pyqtgraph does (`mark_qt.Collector`): any other widget caught in such a cycle is now freed safely too. Tests:
  `drive_collector` (no collection outside the window's thread through the whole drive; 76 on 0.2.19) and a check
  in `drive_preferences` that the page is freed when it closes.
  The Windows runner, which had crashed at the same place now and then since 0.2.15, passed three runs of three.
- A shared file's stretch, played from its card, stops on its last frame even when the window was held up while it
  played; it went past it (the Mac runner: frames 3-9 stopped on 10), since the player's catching up stopped only
  at the end of the part. Tests: in `drive_sharing`, the window held up on purpose (stopped on 21 before).

## 0.2.19 (2026-10-15)

- The file dialogs open where the person last looked (Jacob, 2026-10-15: "when I open a shared file (or video), can
  the file chooser remember where I last looked?"): **File → Open a shared file…** starts in the folder the last
  shared file came from, **File → Open marks…** in the last marks folder, and the video dialogs (File → Open, and
  "where is this video on this computer?" when a shared file's video is not found) in the folder the last video was
  chosen from, as File → Open already did. A remembered folder that is no longer there is ignored. Tests:
  `drive_remembered_folders` in test_gui.
- Boxes in the right column are only as tall as what they hold (Jacob, 2026-10-15: "Only make the box as tall as
  needed for the content. General design principle for mcDonald"): the "Saving the frames as pictures" and
  "Downloading" cards filled the column's whole height while a video opened, and in a tall window the three steps of
  Advanced grew with the spare room (175 pixels for 120). Opened, "Mark the object by hand" still lets its table of
  marks take the room. Tests: `drive_boxes_fit` and a check in `drive_one_window` in test_gui (`too_tall`, which
  every framed card of the column is held to).
- **Edit → Preferences…** (Ctrl+,) in place of the Preferences menu (Jacob, 2026-10-15); on a Mac, Qt puts it in
  the application menu as mcDonald → Settings, where a Mac's own programs keep it. The page has a section for each
  setting, for more to be added: **where data is saved** (the folder, the room there, and Change…, as on the first
  screen; it says that nothing already saved is moved) and **CPU cores**, as before. Its way back, and Help's
  pages', says "Back" rather than "Back to the video" when no video is open. Tests: `drive_preferences` in test_gui.
- A video downloaded and then saved as pictures shows the two waits one under the other, as the steps they are
  (Jacob, 2026-10-15): once the download is done its card stays, quiet -- grey, a tick, "Downloaded PR113", where
  the video is kept -- and the frames' card comes under it; both go when the frames are saved, or at once if the
  person stops (no segment chosen, Cancel, an error). Tests: in `drive_getting_in` in test_gui.

## 0.2.18 (2026-10-15)

- One file to send someone so that they go on where you left off (Jacob, 2026-10-15): **File → Share for review…**
  writes `<tag>_<who>_<date>.mcdonald` -- the video's results (marks still saying who placed them, tracks, every
  object's folder), the part to open, the stretches to look at, and a thread of notes, each with who wrote it and
  whether a person or an agent did. The video is not in it: it is named by catalog name, file name, size and
  SHA-256, and found (or downloaded) on the other computer, which says whether it is the same file. **File → Open a
  shared file…**, a drop, the first screen's third button, or `mcdonald mark FILE` opens it into a folder of its own,
  with the part, the marks, every object's track, and a card in the right column: the thread (newest first), a
  button per stretch that plays it and stops at its end, the attached figures, and a box whose button saves the
  answer as a file to send back. `mcdonald share make|show|open` does the same from the command line, `--object
  LABEL=TRACK.csv` for an agent with tracks alone. Unpacking takes only data and pictures and refuses a name that
  would land outside its folder. Tests: `tests/test_share.py` (16), and `drive_sharing` in test_gui (8).

## 0.2.17 (2026-10-12)

- The window: no right column until a video is open, so "Measure the object" is not on the home page. Choosing
  the segment, the player is on the left and what is asked -- the segment, how many objects, what else is known,
  the space it needs, Open -- is a card on the right, "Select the video segment".
- A brightness beat at a wingbeat's rate (one bird, or a flock) is labelled "Beats like a bird" in place of
  "Tentative conclusion": in the report, the command line's summary and --json, and the window's card, where its
  badge is a drawn bird.
- A most for the CPU cores: `mcdonald --cpus N`, and Preferences -> CPU cores in the window, remembered. Every
  stage's workers stay within it.
- Fixed: the flicker stage heard a video's hold cadence as a beat. PR34 is 10 pictures a second shown at 30 fps,
  each picture held three frames; the stage reported "a beat at 5.02 Hz (and at 10.03, its double), 31% of its
  brightness, 6 of 8 windows" -- the cadence and its half -- "clear of the codec's rhythm", as the codec check
  looks only at the encoder's anchor frames. The stage now finds the held frames from the frames it already reads
  (`pictures`: a frame is held where it differs from the one before by under 0.2 of the typical change between
  pictures, the 80th percentile -- held frames differ by the encoder's noise, 0.01-0.05 grey levels on PR34, and can
  be most of them), carries the picture rate, and hears a beat only below 0.8 of that rate's Nyquist frequency
  (PR34: 10.2 pictures a second, beats heard up to 4.1 Hz; no beat). `fields["pictures"]` = {rate, held, top_hz};
  the finding says when a strongest peak is above it. PR44 (15 pictures a second) keeps its 3.06 Hz.
- Fixed: a beat heard near the Nyquist frequency. PR27 passed six 2-s windows at 13.5 Hz, 0.9 of the 15-Hz limit,
  on frame-to-frame noise with no rhythm in the curve. A beat -- of the whole track or of a window -- now passes only
  up to 0.8 of the Nyquist frequency (12 Hz at 30 fps; `TOP`), and windows carry `above_top`. PR27: no beat.
  PR41 (6.43 Hz), PR099 (4.90 Hz), PR44 (3.06 Hz) and PR088 (10.3 Hz) are unchanged.
- Not done, and why: a check of the brightness folded on the frame number (a pattern of the recording chain repeats
  with the frame count) was tried for PR088 and withdrawn -- a real beat whose period is near a whole number of
  frames folds just as strongly (a pure 10.28-Hz sine over PR088's 74 frames: 1.32 of its std; PR088: 1.01).

## 0.2.16 (2026-10-10)

- Every CPU: a worker for each CPU this process may use (a batch job's allocation), as far as free memory
  allows (about 100 MiB and 200 bytes a pixel each), where every stage used 10; --procs on groups, flicker,
  tether and symbology too. groups, flicker and symbology's pointer reading now read their frames on a pool,
  tether's on threads, and the static masks on threads. Nothing measured changes: the same numbers to the
  bit on any number of workers.
- New: every case the flicker stage flags with a beat of its own comes with `<case>_beat.png`
  (`figures.beat`), in the style of the PR135 paper's Fig. 2: for each track that beats, its
  brightness deviation over 4.5 s about the stretch reported, beside the background aperture as the
  control, and amplitude spectra over the whole track -- the object's, every background aperture's,
  the codec's rhythm marked, and, where the beat reported comes from a 2-s window, that window's
  spectrum dashed and the window shaded, so a beat heard in one stretch looks like one (PR094's
  4.97 Hz does; PR41's 6.44 Hz stands in the whole track too). Listed in the stage's files, so the
  report shows it under flicker, and among the report's figures. Nothing measured changes.
- Fixed: the flicker stage's aperture was 4 px with its ring at 7-10 px whatever the object's size, so on
  things 15-100 px across the ring lay on the thing, its brightness over the ring came out near nothing,
  and the stage called something anyone could see "lost" and looked for no beat (PR056, PR086, PR116,
  PR47; PR052). The object's extent is now read off its own frames -- its radial profile, a median on
  each ring so that roofs and wave crests beside it do not count -- and a thing wider than the 4-px
  aperture is measured whole: an aperture 1.2 times its extent, a ring and background apertures beyond
  it, re-centred each frame on its own centroid. A point keeps the 4-px aperture, ring and background
  apertures exactly (PR23, PR135's six, Galileo's flyers: unchanged). `fields` carry `extent_px`,
  `aperture_px`, `ring_px` per track, `background_px` and `recentred`; a note says when it happened.
  PR086, PR056, PR116 and PR47 are now tested (no beat of their own); PR41 keeps its 6.43 Hz, measured
  at 12 % of its brightness where the point aperture read 3 %.

## 0.2.15 (2026-10-09)

- Fixed: the flicker stage called PR23 "a bird" from a beat at 2.1 Hz that was one dip -- the
  object lost against a hot roof for seven frames -- read through the running mean, which makes a
  peak near 2 Hz of any slow change. Frames where the object is lost against what is behind it are
  now left out (and listed); a beat must stand over the curve's own slow wander and jitter, fitted
  to its spectrum (one in a hundred curves that only wander pass); a strongest that is only the
  band's edge is no beat; a fundamental is named only from a peak of its own; and the beat reported
  is one that passed. The running mean is the paper's 0.5 s at any frame rate (15 frames at 30 fps
  as before; 30 at 60, where it was 15). Held against PR135's six birds and the five Galileo flyers
  (all keep their beats) and PR23, a pico balloon, PR055 and PR071 (none has one).
- `tests/test_tether.py` runs with the other portable suites: in `tools/suites.sbatch`, on the
  Mac and Windows runners, and in the READMEs' install checks. Nothing measured changes.
- Fixed: the Measure form's own button never asked the track-sheet question (every report made
  through Advanced → Measure → Measure was provisional since 0.2.14); the Advanced line comes back
  under the one button when its run ends short, where its sentence points at it.
- The window's look, reviewed before more testers: dialog buttons without the desktop theme's icons,
  the program named mcDonald in every title, the Mark menu in sentence case, one accent for the
  chosen segment and a proposed path, the frame said once on the control bar, the wait card
  counting frames.
- What is known of the video is asked for: on the segment step, folded under the count ("Do you
  know anything else about this video?": how wide the camera sees, how far away the object is, a
  thing of known size measured on the player, the speeds a report gave), remembered for the video
  and used by the one press; and on the report card when the report could not give a real speed
  ("Add what you know", then "Work out the speed", nothing measured again). On the command line,
  `mcdonald report CASE --fov ... --range ...` (and `--forget`) does the same; the numbers are
  `run`'s when told the same from the start. A case keeps what it was told (`known`).
- A speed from a thing of known size is now the report's conclusion and is in its bottom line,
  where both had said that nothing converts to a speed.

## 0.2.14 (2026-10-08)

- One window: pages over the video in place of pop-up windows (the start screen is the one
  dialog, and the home page); one button that finds the object, follows it and measures it,
  with Advanced revealing the three steps; the report leads with its conclusion.
- More than one object in a video: ticks on Find's rows, or `run --each DIR` on folders
  `object-1`, `object-2` …; a case and a report for each, one list of them, and every track
  drawn on the video in its own colour.
- How many objects are looked for: the segment step asks, and `run --each --objects N` holds the
  count against what was followed; a group of points is split into its members, each followed
  over its own frames, and a flock of birds is named in the report.
- `mcdonald tether`: is something tied to the object, and does it swing? A pendulum period
  becomes metres of line; a stage of `run`.
- The window's look audited: one accent colour, one button style, a column to read in.

## 0.2.13 (2026-10-05)

- Find sees the slow crawlers in a still scene: a still-scene pass in `look --propose`.

## 0.2.12 (2026-09-29)

- The beat (a periodic brightness or size change) is measured in windows along the track,
  named by its fundamental, and shown in the report.

## 0.2.11 (2026-09-27)

- The link follows an object by its motion when no spot size holds it (PR43's streak links).
- The link's gate at the marks grows with the spot size.
- Registration: the ZNCC variance is computed in float64, and the second pass runs once a
  window, not once a pair.
- Ready for Windows: every file UTF-8, a download that cannot start says why, and a Windows CI job.
- Help -> About and the README say where to donate (Project Janus at Blue Marble Space).

## 0.2.10 (2026-09-26)

- Six speedups that give the same numbers: Follow 74 s -> 8 s, Measure a quarter shorter, the
  window's start halved.
- The window fits the screen and remembers its size, shows notes as a toast, lists recent
  videos and takes dropped files, and never waits on the network.

## 0.2.9 (2026-09-26)

- Step 2's track-check lines, shortened.

## 0.2.8 (2026-09-26)

- Progress lines name every step in one to three words.
- Open by catalog name: the question on two lines, with the three ways to write a name.

## 0.2.7 (2026-09-25)

- The applications-menu entry starts this install's window, not the first one on the PATH.

## 0.2.6 (2026-09-25)

- `mcdonald setup` adds the window to the applications menu.

## 0.2.5 (2026-09-25)

- `pip install mcdonald` gives the window too: PySide6 is a dependency.

## 0.2.4 (2026-09-25)

- First release on PyPI: `pip install mcdonald`, no git needed. The repository went public.

## 0.2.3 (2026-09-25)

- Help -> About: version, release date, what it is, the quote, the license.

## 0.2.2 (2026-09-25)

- mcdonald updates itself: the window asks, the command line prints the command.

## 0.2.1 (2026-09-25)

- The version goes up with every change sent out, written in one place.

## 0.2.0 (2026-09-20 to 2026-09-24)

- The reduction: symbology, kinematics, scale, co-motion, figures, and the `mcdonald run`
  driver from a video to a case report.
- `tests/test_published.py` walks every published number it can reproduce.
- The marking window (`mcdonald mark`, `mcdonald-gui`): find the object, mark it, link a track,
  play the clip, measure from the window, with progress and Stop on every long step.
- The command line does the whole marking job with no window: `look`, `mark --set`, `--json`
  everywhere, exit codes.

## 0.1.0 (2026-09-19)

- The measurement nucleus as an installable package: background layers, clip integrity, the
  track sheet, and the catalog adapter.
