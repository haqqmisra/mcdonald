# Changelog

Every version that went out, newest first. The version is written in one place,
`src/mcdonald/__init__.py`; each release from 0.2.4 on is a git tag and is on PyPI.

## 0.3.2 (2026-10-19)

**Known issue, on Windows only**, found by the Windows runner as this went out: opening another video while the
last one's frames are still being saved as pictures, or in a window `mcdonald mark VIDEO` made while its segment is
still being chosen, fails two of the window's checks there (Linux and the Mac pass them). Not yet understood; to be
fixed in 0.3.3. Opening one video at a time is unaffected, as is opening another while the segment is chosen in a
window opened from its own menu.

Four things in the window (Jacob, 2026-10-19):

- **Where the sound plays**, in Edit → Preferences…: "Play the sound on" lists System default and then each output
  ffplay can play to, by the names its SDL gives them, with "Play a test sound" (a short tone there, and the page says
  whether it played). Remembered. SDL opens the output named in `SDL_AUDIO_DEVICE_NAME`, by its own name to the letter,
  so the names come from the SDL library ffplay is linked against (asked in a process of its own), and where SDL is
  built into ffplay -- the Windows builds -- from the sound endpoints' names in the registry; on a Mac where the library
  is not found, from system_profiler. One the player refuses (unplugged since, or named otherwise) is played around:
  the sound starts again on the system default. One chosen that is not connected now stays the choice, and the page
  says so. Checked in two containers with two pretend outputs: Ubuntu 24.04 (SDL2 2.30) and Fedora 44 (sdl2-compat
  2.32 over SDL3 3.4), each output reached and an unknown name played around.
- **The graphics card (GPU)**, in Preferences too: the cards that can compute -- dedicated ones first, named as sold
  -- and "None: the CPU only"; greyed out where there is none, saying so, and naming a card that is there but cannot
  compute. A card can compute where Vulkan lists it as a GPU (Linux, Windows), where it is NVIDIA's with CUDA's
  library, or where Metal runs on it (macOS). A server's management chip, a virtual machine's screen and a card on
  Windows' basic driver are not counted at all. On merlin the FirePro 2270 (TeraScale 2, on the radeon driver) is
  found and not offered: the only Vulkan device there is llvmpipe, the CPU. Nothing uses a graphics card yet: the
  choice is remembered for when something does (`gpu.py`).
- **A control that cannot be used is grey.** The window's palette gave every state the same colours, so a disabled
  menu entry (Undo with nothing to undo), drop-down or button without its own style looked like one that could be
  used; they now take the grey the quiet buttons already used when disabled.
- **Opening another video while one is on its way in stops that one first.** File → Open, a drop or a recent video
  while the last one's segment was being chosen, or its frames saved, opened the new one inside the old one's wait --
  and the old one then came back over it once its own wait was over. Now the old one's question is answered no, or its
  wait cancelled, and the new one opens once it has gone. The window is also drawn empty, saying what it is opening,
  before the next file is looked at: the old video's last frame stayed on the screen until the next page was drawn.

**The command beside the bar** (Jacob, 2026-10-19: "when the progress bar is working, I'd also like a colored oval
box to display the CLI command being invoked; not the full command, just the first word after mcdonald"). Wherever the
window shows a moving bar, an indigo oval to its left names the command that does the same from a terminal: `look`
while Find looks, `mark` while it follows, and while it measures the stage under way's own command (`tracksheet`,
`layers`, `groups`, `flicker`, `tether`, `integrity`...; `run` for the parts that have none) -- on the three steps, the
one-press card and the queue of several objects alike; `mark` while a video is downloaded or its frames saved, `audio`
while its sound is read, `share` while a shared folder is measured again. The window calls the code those commands
call, not the commands, so the oval is the name to look up. `stages.COMMAND` holds a command for each stage, and
`run_case(started=)` says which stage has begun.

Three new commands, merged from their branches on 2026-10-19 (command line only so far; no page in the window yet;
README-technical has an example of each and what each cannot do):

- **`mcdonald stabilize`** holds a screen filmed by a phone still: one homography a frame from the display's own
  drawing, and the display's video written out (frame n = frame n) for every other command to run on. `--to-clip`
  carries a track made on that video back onto the clip. The fifth tranche's six Oman clips hold. `docs/method.md` §14.
- **`mcdonald aspect`** asks whether an object looks the same from every side: does its brightness or size follow its
  heading? A sphere's do not. It needs no range, field of view or beat. `docs/method.md` §15.
- **`mcdonald waves`** reads the sea as a ruler: metres per pixel from the dispersion of the waves a clip shows, with
  no field of view, range or telemetry, along the line of sight unless the depression is given. PR149 passes; most
  PURSUE sea is refused, saying why. `docs/method.md` §16.

## 0.3.1 (2026-10-19)

From a tester's runs on a Mac with 0.2.20 (PR44, opened at 30-56 s; 2026-10-18 and 19):

- **The report can be saved as one file.** "Save as PDF…" at the top of the report's page in the window (and of the
  list of a video's objects) writes the whole report as a PDF with its pictures in it, where the person says; before,
  the page had only "Open the folder" and "Back to the video". `mcdonald report CASE.json --pdf [FILE]` writes the
  same file (`<tag>_report.pdf` beside the case unless a file is named; with `--index`, the list's). The PDF is the
  page's words in the page's order, set for paper by the same function the page uses (`paper.dress`): every folded
  part open, each picture no wider than the text, a long picture in page-high strips, and a track sheet too large for
  paper named, not printed. Letter or A4 by where the computer is.
- **The report says the segment chosen**, at its top, in the video's time as the segment step shows it ("Segment:
  0:30.00 to 0:56.00 of the video, 26.0 s (frames 901–1681)"), and the frames measured where they are fewer: an object
  is measured over the frames round its track. The case file keeps it (`segment`, outside what `share rerun`
  compares); the list of several objects says it too.
- **A report and its card say the same.** The tester's cards said "A bird is the leading explanation" and the report
  "doesn't say bird at all". A card reads its case file by the running version's rules; the report is the file written
  when the case was measured, and a report from before 0.2.14 names no bird (the same segment measured again on 0.2.20
  finds no beat at all, so most likely those cases were older). The report's page now writes the report again from its
  case file wherever this version would word it otherwise (`report.written_again`, what `mcdonald report CASE.json`
  does), and a case keeps the version that measured it (`measured_by`): the report and the card say "Measured with
  mcdonald X, and read with Y ... Measure it again to have this version's own numbers" where they differ.
- **The list of several objects leads each object with its report's conclusion**, where a bird is named; it showed
  only the bottom line, which never names one.
- **The size-and-speed figure has the birds on it, and no k.** A band for a bird's size (about 0.2-2 m across the
  wings) is drawn with the weather balloon and the fighter jet, and in the accent, said as the object's own, where its
  brightness beats like a bird's. The axes are named in words -- size, speed across the line of sight, distance to the
  object -- and a known scale is named by its field of view: the equations with k and ωR are gone from it (they stay
  in the report's table of variables).

## 0.3.0 (2026-10-19)

ROADMAP.md's 0.3, "the beat, held to account; the reference cases as files", as the maintainer scoped it on 2026-10-17:
the goldens green; the flicker gates decided by evidence; a case file for every video of the two papers that reruns to
its numbers; the beat sweep reproducible from the repository's tools; and every frequency with its error. The roadmap
itself is new (`ROADMAP.md`, 2026-10-16): one theme a minor version to 1.0. What 0.3 leaves for 0.3.x: the sky's rhythms
in the look-alike table, the beat in the position, the report's grade and checklist, and levels.

### The beat, held to account

- **Every frequency has its error, and the codec's mark and the members' independence are held to it**, not to the
  resolution (ROADMAP 0.3, objective 2; the information-theory survey's D1 and D6; docs/method.md section 12). Until now
  a peak within 1/T of a codec line was "at the codec's line": 0.5 Hz on a 2-s window, so on the 93 of 112 sensor videos
  whose codec puts a line at 7.49-7.5 Hz no window passed from 7.0 to 8.0 Hz, the middle of the bird band, and the
  planted beats were moved off the line, so their completeness never showed it.
  - `flicker.hz_error`: a block bootstrap in the curve's own residual (200 resamplings in 0.5-s blocks), never under the
    Cramer-Rao bound or the spectrum's own step. Planted in grain, the truth falls within three errors 97-100 % of the
    time above the detection threshold. Every object's peak, window, pair and reported beat carries `hz_err`, and
    `mcdonald flicker` and the finding print it ("7.39 ± 0.02 Hz").
  - The codec's mark (`at_line`): within 3 errors of the line, which has no width of its own. A rhythm on the line is
    marked every time; a strong beat 0.25 Hz beside it in a 2-s window, 0-7 % of the time (100 % before). The rhythms
    locked to every k-th frame in the look-alike table are held to the same error; a supply's, a heard and a held
    picture's rhythm keep the resolution. The one-bit reading and the multitaper's lines use the same mark.
  - Members apart (`common`): by more than 3 of their combined errors over all the pairs judged at once (Sidak: 3.75
    for fifteen pairs), or out of step, as before. Each pair says `apart_z`, `z_needed` and its resolution.
  - `flicker.sliced` (with the slower nulls): beats of 10 and 20 % planted 0.1-0.4 Hz either side of each codec line
    in a 2-s window of each background aperture, and 1 Hz off it as the control, with what the old mark recovers
    beside it (`by_resolution`). `flicker.analytic` (D6): the amplitude a beat needs, in closed form from the noise,
    the frames and the band's look-elsewhere, beside the planted beats (`injection.analytic`, `slice.analytic`) and
    each object (`fields["analytic"]`), with how long a clip must be for a beat of 5, 10 and 20 %.
  - Windows record what the old mark said of them (`codec_by_resolution_hz`, `passes_by_resolution`), and each beat
    how many windows passed by it (`windows_passing_by_resolution`).
  - Moved numbers. PR135 (the golden): the whole-track frequencies are unchanged and now carry errors of 0.02-0.11 Hz
    against a resolution of 0.20. The windows that pass went from 0 to 9, 3, 9 and 7 of 14 for A, B, E and F (the
    four within half a hertz of the line) and from 4 to 14 and 10 for C and D. Where a window is clearer than the whole
    track the stage reports it, so E is reported at 7.90 ± 0.07 Hz (its whole track 7.69 ± 0.03, the paper's 7.64), C
    at 8.02, D 7.09, F 7.74. The golden now holds the paper's whole-track rates to the stage's whole-track peaks (all
    within 0.06 Hz). B's one-bit reading is clear of the line; F's still is not. One pair went the other way: D-F, 0.475
    Hz apart, 3.5 of their errors, under 3.75, and 38 degrees in phase, is no longer apart by frequency (the flock is
    still theirs). The saved-curve controls give the same calls as before: the Galileo birds and PR135 beat; PR23,
    PR055, PR071, WA9ONY-5 and PR144 do not. On real data the mark cuts both ways: strong beats beside the line are
    freed, weak ones whose frequency is poorly known are held (PR073 o00's 8-Hz windows, ±0.24 Hz).
  - The codec slice's worklist (D3), through the new mark, the continuum null and the encoding control: by the stage's
    rule none of its ten objects is called -- the mark was not what refused them, their windows fail the background's
    floor; by the paper's rule seven are (PR085 o04/o08/o11, PR098 o06/o08/o58), candidates for a look.
- **The flicker gates decided, and the bird headline held to a beat that comes back** (the maintainer, 2026-10-17:
  ROADMAP.md's decision 6, on a gate study of 760 saved curve sets with the held-out third left out; docs/method.md
  sections 7, 8 and 13). `GATE_ASTRO` and `GATE_SEIS` stay off and their tests stay reported readings: the
  astronomer's gate lost 4 of 27 known birds' beats and none of the 3 false alarms among 2,887 background apertures
  judged as the object, the seismologist's lost 3 birds to remove 2 of them, and alone each passes 58 % of those
  apertures. The report now names a bird (or a flock) only from a beat that **comes back** -- the whole track beats,
  or two passing windows that do not overlap agree within 0.5 Hz (`flicker.apart_windows`; each beat's `whole_passes`,
  `windows_apart`, `comes_back`). A beat in one stretch is said as one, in the conclusion, the summary and the bottom
  line, and the flicker finding adds "that is one stretch". On the same curve sets the rule keeps 25 of the 27 birds'
  headlines (it loses PR085's and PR088's Table 1 bout-flappers, which the paper's rule calls over the whole track)
  and drops 17 of the pass's 46 one-stretch calls. A case from before the rule has no mark and reads as before. Run
  once, after the decisions, on the held-out third (441 objects in 29 videos, never tuned on): the stage calls 27 (6.1
  %, against 6.4 % on the tuning set); their background apertures pass as the object 3 times in 1,657 (0.18 %, against
  0.10 %), and neither gate would have removed one; the headline rule keeps 7 of the 27 and drops 20 one-stretch
  calls, 15 of them in LLE-PR002, a phone video the whole-video pass had marked as likely noise.
- **The held-out third** (the ideas bank's D5): `tools/sweep/holdout.py` drew 42 of the sweep's 126 videos on
  2026-10-17, by release, with a hash anyone can repeat (`tools/sweep/holdout.tsv`), before any of the gate work; the
  videos the gate work needs by name (goldens, controls, reference cases, the codec slice's worklist, the headline
  rule's two examples) were not eligible.
- **The bird paper's method, in the flicker stage** (the maintainer, 2026-10-16: "It is fine to use the paper's aperture
  and nulls"; docs/method.md section 10). The reference case files measured with the toolkit's own defaults called 11
  of the 19 Table 1 objects beside PR135's six at the paper's frequency and refused 8, which the paper had measured its
  own way. Each piece of that way is now the stage's:
  - `--aperture R[,R1,R2[,BG]]` (`flicker.fixed`; a row of the known-quantities table, so `run`, `flicker` and the
    Measure form all have it): a disc of the object's own size and its ring, never re-centred, in place of the aperture
    that follows the object's size -- where a flock's members fly close, that one takes in its neighbours.
  - The continuum null (`flicker.continuum`, `fields["continuum"]`, printed by `mcdonald flicker`): the peak against a
    power law fitted to the curve's own spectrum, against 2,000 noise curves of that continuum; its original code
    reproduces the review that judged Table 1 exactly, and the port agrees with it on every verdict.
  - The planted-dot encoding control (`mcdonald.planted`, new; `fields["encoding"]`): constant dots like the object,
    planted in the clip's own frames and grain, encoded with libx264 like the clip (on one thread, so that it gives one
    answer) and measured as it is; the encoder makes a beat only where the dots carry a line at it and the beat is under
    three times that line. It decides where one object's beat sits at the codec's rhythm, which the stage had left
    undecided ("nothing tells the two apart"): measured alone, PR135's B (7.38 Hz against the codec's 7.49) is its own,
    the dots reaching 0.4 % there against its 22.5 %. About 20 s, in that case only; without libx264 it says so and
    decides nothing.
  - `--avoid TRACK.csv[,...]` (`flicker.clear_offsets`): the background apertures keep clear of the other tracked
    things in the frame; measured one by one, PR135's E and F had theirs on neighbouring birds. Only when asked, so
    that an object in a queue still gives what it gives alone.
  - `--beat-rule stage|paper` (`flicker.RULE`, per measurement): how a whole curve's beat is judged (`whole_passes`).
    `paper` is the paper's: the continuum null, the background apertures' amplitude at the beat's own frequency, and the
    encoding control; the 2-s windows keep the stage's tests under both. **The stage's rule stays the default, decided
    by the controls** (1,201 saved curve sets): the background apertures judged as the object pass 0.15 % of 4,700
    times by the stage's rule and 2.0 % by the paper's. The paper's rule is for an object someone has looked at, as the
    paper used it.
  `mcdonald run` records `--aperture`, `--beat-rule` and `--avoid` in its command, so a case reruns as it was made.
- **The astronomer's tests** (from the astronomy methods survey, its ports 1-4; module docstring item 7), each in the
  fields, printed by `mcdonald flicker` and said in the notes where it disagrees with a beat the stage called:
  - `fields["astro"][track]["lombscargle"]`: the strongest beat again by the generalised Lomb-Scargle periodogram
    (VanderPlas 2018; astropy's exact method's numbers) over the frames that are samples -- a held picture or a frame
    the object was lost on is a missing sample -- with Baluev's (2008) false-alarm probability over the band, and the
    sampling's own rhythms read off its spectral window.
  - `["scramble"]`: the curve's strongest held against 200 copies of itself scrambled in 0.25-s chunks (Thompson et al.
    2018; Theiler et al. 1992), said above 4 Hz, where the scrambling does not also destroy the slow wander.
  - `["common_mode"]` and `["pixel_phase"]`: the frame's own level and contrast and the background apertures' common
    mode (SysRem, Tamuz et al. 2005), and where within its pixel the object sits, regressed out of the object's curve,
    with its beat before and after.
  - `fields["controls"]` and `["false_alarm"]`: every background aperture put through the object's own tests as if it
    were the object, so what passes is a false alarm by construction; `["injection"]`: beats planted in them at 2, 5,
    10 and 20 % across the band, the completeness. With the slower nulls, which `mcdonald flicker` runs unless told
    `--no-nulls` (`mcdonald run` does not: the method note had said it did).
  - `fields["fold"]` and `<case>_fold.png`: the frames folded on the beat into a bright and a dim half (epoch folding;
    Kepler's difference image), their difference saying where in the picture the brightness that beats is.
- **The seismologist's tests** (from the seismology methods survey, its ports 1, 3, 4, 6, 8 and 11; item 8), likewise
  reported: the multitaper spectrum with the harmonic F-test at the beat, over the stretch and in 2-s windows
  (`fields["seis"][track]["line"]`, `["line_windows"]`: a wingbeat's wandering rate is no stationary line over a whole
  track, and is one within 2 s); the coherence with each background aperture and the frame's level and contrast
  (`["coherence"]`); the noise as a distribution and the centile the object's windows sit at (`["noise"]`,
  `<case>_noise.png`); the Sompi method's lines, a frequency and a decay from a few cycles (`["sompi"]`), which also
  reads a track of 20-59 frames too short for the stage (`fields["short_record"]`); the comb and the glide of the
  fundamental (`["comb"]`, `["glide"]`); members' phases held together, with the array F-statistic
  (`fields["in_step"]`); the fold by phase (`phase_inside`, `phase_outside`); and the one-bit reading (`["onebit"]`).
- **The look-alikes** (the SETI methods survey's first port; docs/method.md section 9): a lamp on 50-Hz mains, an
  aircraft's lights on its 400-Hz power and a video at 30 frames a second fold to 10 Hz (9.19-10.39 at 29.97), where
  small birds beat. `flicker.lookalikes` is the table for a clip -- the supplies and their lamps folded through the
  frame rate (`flicker.alias`), a rhythm locked to every third to sixth frame, the held pictures' cadence, and the
  rhythms its own sound carries (`audio.heard`) -- in `fields["lookalikes"]`; a beat at one is marked with it, not
  refused, and the finding and the notes say what tells a supply's line from a wingbeat.
- **Frames lost at the troughs of the object's own beat are kept**, where they are its troughs (the maintainer,
  2026-10-15; PR097's dark dots, beating at 25-60 % of their brightness, fall under a quarter of their level at every
  trough, and the guard built for PR23's hot roof refused the clearest of them). In two halves, calibrated on the 142
  objects of the whole-video pass that the stage had refused for lost frames: troughs are suspected from six short runs
  or more in the lower half of the curve's own strongest beat (`flicker.lost_at_beat`, `LOST_RUNS` 6), and kept for good
  only where the beat the stage then finds is theirs, within 1 Hz of their frequency or its double
  (`flicker.at_the_troughs`); for every other track the frames are lost, as before. PR097's dots keep their beats
  (6.94, 6.69 and 2.34 Hz); PR23's roof crossing and the WA9ONY-5 balloon say what they said before.

### The reference cases, and reproducing them

- **`mcdonald share rerun FILE.mcdonald`** (`mcdonald.rerun`): every object of a shared file measured again by the very
  command its report records -- the same marks or track, frames, known quantities, polarity, aperture, beat rule, the
  other objects kept clear of, skipped stages -- into a fresh folder, and the new report held against the file's,
  number for number (paths by their file name; a float within one part in a billion); exit 1 where it does not rerun,
  and with `--strict` a report that tracked nothing does not count. The check every reference case is held to, so that
  anyone who installed the package can reproduce a case; `tools/rerun_cases.py` in the repository is the same, looking
  in the reference-data folder too. In the window, a shared file with measured objects has **Measure it again** on its
  card: the objects measured in a thread behind a wait's card, and the card then says whether the numbers come back the
  same.
- **The reference case files** (ROADMAP 0.3, objective 8): a `.mcdonald` file in the reference-data folder's `cases/`
  for each of the 14 videos the two papers rest on -- PR113, PR149, PR43 and PR144 (the Technical Note), PR135 and the
  nine other bird videos of the Scientific Reports Table 1 -- measured the paper's way and made with this release; each
  reruns to its numbers under `mcdonald share rerun --strict` (the folder's README has the table against the papers).
  The reference-data folder holds the nine other Table 1 videos (PR41, PR44, PR077, PR079, PR085, PR088, PR097, PR099,
  PR141) for them.

### The beat sweep, from the repository's tools

- **`tools/sweep/`** (ROADMAP 0.3, objective 9): `sweep.sh WORK` runs the whole-video beat pass through Slurm from
  nothing but the package and the videos. `windows.py` finds each video by the release's file name in the package's
  catalog (downloading it into the storage folder the first time) and cuts it into windows of 400 frames overlapping by
  30; every frame is extracted once (`extract.sbatch`); Find runs over every window (`propose.sbatch`); each video's
  proposals become objects, each linked from Find's own marks and put through the flicker stage (`post.sbatch`,
  `post.py`, `collect.py`); `summary.py` writes the candidates and the strict list, leaving the held-out third out
  until told `--held-out`; `review.sbatch` measures the strict list again by the paper's rule; `cadcheck.py` asks
  whether the encoder or the cadence makes a beat. Run on PR23 and PR073, it cuts the pass's own windows and finds its
  objects exactly.

### The sound: `mcdonald audio`

- **`mcdonald audio VIDEO`** (`mcdonald.audio`; the aviation survey's Av3, brought forward from 0.8 at the maintainer's
  word; docs/method.md section 11): what a video's sound track records, read as an accident investigator reads a
  cockpit recording -- the codec's frame products (named first: they look like machinery), the video's frame comb and
  field rate, an aircraft's 400-Hz power or the mains as a clock on the playback speed (read at full resolution from
  up to three 30-s pieces, a line on two combs counting for neither, every bus said against 400 and 400/1.001),
  sidebands and a tape's wow, any other harmonic series as something turning steadily, and, against a small table of
  airframes whose propellers' speed in flight is sourced (the T56 C-130, the C-130J, the H-60), the airframe, named only
  with its second tone at a measured ratio: an MQ-9 heard from the ground puts its blade-pass over a T56's. Silence is
  NO POWER (exit 5). On PURSUE: PR117-PR119, phone captures of an AC-130's display, are a T56 gunship in flight (67.76
  Hz, second tone at 8.129x), not the AC-130J of AARO's description; PR106/PR107 carry the bus at 399.66/399.74 Hz;
  PR113 carries the NTSC field rate (59.944 Hz) and the mains (60.011 Hz) apart. Planted in 35 real tracks (3,150
  runs): found at +18 dB 76-92 %, at +24 dB 79-97 %; no airframe ever read as another; decoys read as an airframe in 4
  of 1,260 runs. Every heard rhythm is folded through the frame rate into flicker's look-alike table: PR117's propeller
  sits at 7.75 Hz, where birds beat.
- `--flyover LO-HI [--rest HZ] [--temp-c C]` (`audio.flyover`, `audio.pass_of`): a source passing the microphone, its
  speed and closest range from the Doppler curve of its tones (Ferguson 1992). Against ADS-B on AeroSonicDB (148
  fixed-wing propeller passes): 75 pass its own checks, and their closest range over their altitude is 0.92 (16-84 %
  0.66-1.19).
- In the window: **Measure → The sound of this video…**, a page that leads with one plain sentence, the picture of the
  sound (saved in the results folder) and, folded, the command's own words and **A source passing the microphone**
  (the flyover, worked out in a thread, `mcdonald audio --flyover`'s answer to the letter); a **Measure the sound** card
  in the right column when the video has sound, teal until measured, then ticked and grey; and the sound played with
  the picture (ffplay, which comes with ffmpeg) in the player and while choosing the segment, from the frame on the
  screen and at the player's speed, its speaker beside the stop button.

### The window

- Measure's optional part offers to keep the apertures beside the object clear of the other objects followed in the
  video (the command line's `--avoid`), shown only where there are others and not ticked unless asked. With
  **Measure it again** and the flyover above, what this release added to the commands the window does too.

### Tests and CI

- The no-video suites run on GitHub's Linux runners on every push to main and every pull request
  (`.github/workflows/suites.yml`), and on demand on Mac and Windows: nine suites, as `tools/suites.sbatch` runs them,
  with `test_audio` (it had never run there) and the new `test_sweep`. On this release's tree, through Slurm:
  measurement 389, reduction 201, published 32, tether 24, audio 54, cli 105, share 25, sweep 10, gui 653 checks, and
  golden 70 on the real clips; and the Mac and Windows runners before the tag.

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
