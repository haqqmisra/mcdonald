# Handoff: two ways in — the command line alone, and the window alone

Written 2026-09-20 at the end of the session that built the Qt marking window,
brought current at the end of the UI session the same day, again at the end of
the third session that day ("the measurements"), on 2026-09-21 after Jacob
first used Measure with a real hand (progress; Find the object), **and again at
the end of a second session on 2026-09-21, in which he asked for two things: a
real video player where the window asks which part of the clip to open, and for
everything the window says to be in plain words.** Both are done, committed and
pushed. **Later that day he tried Find: "worked on PR144 but not on PR113"** —
the section below. He has now used the window end to end on PR144 (a part
opened, Find, This is it, link, Measure, a report); what he has not said is how
the player, the progress bar and the new words were in his hands.
Everything below was checked on this machine unless it says otherwise.
`docs/handoff-gui.md` is the record of how the window got here; this is the
brief for what comes next.

## "Find the object worked on PR144 but not on PR113" (2026-09-21, later the same day)

Jacob's first hand on Find. On PR144 (he opened 98–194) it was the first of
three rows; he took it, linked and measured, and has a case report. On PR113 it
"did not work". Which part he had open is not known — nothing was saved — so
both ways it can fail there were reproduced and both dealt with.

1. **The object was on the list and out of sight.** On PR113 every row is
   `weak`, and the recorded object was **6th of 135 on 380–440 and 11th of 294 on
   348–471, in a window that shows eight rows.** One picture of the strips of
   what outranked it said why, as the last handoff's trap said it would: the
   edges of redaction blocks that shift, the rim of the picture, and the strokes
   of the scrolling heading tape. Each is a compact peak in the residual that
   moves; none is a compact thing in the frame. `propose.all_round` measures
   that in the frame's own pixels — a core the peak's half-width against the
   sixteen sectors of a ring round it, the worst sector's contrast as a share of
   the best — and the score is multiplied by (0.1 + it). Recorded objects:
   0.31–0.83; the median of the clutter: 0.00 on four clips, 0.10 and 0.16 on
   the other two. Nothing was tuned on PR113 but the number of sectors, and
   that was chosen on all six clips and three drawn shapes (8 lets a thin stroke
   through at 0.58; 24 lets noise pull PR149's contact down to 0.38).

   **"Next, 1b (ii)" is done, and is the measure to repeat after any change to
   `propose.py`:** the place of the recorded object on the list, for every clip
   that has a recorded track, before → after.

   | clip | what it is | before | after |
   |---|---|---|---|
   | PR149 1–120 | a contact crossing at 20 px/frame, a ship in frame | 1 of 197, strong 36 (2nd: 3.1) | 1, strong 28 (2nd: 0.3) |
   | PR144 300–500 | the sensor follows the object | 1 of 509, strong 28 | 1, strong 27 |
   | PR142 130–290 | a small bright thing at 19 px/frame | 1 of 125, strong 27 | 1, strong 15 |
   | PR148 140–440 | a dark thing at 7 px/frame, then 3 | 1 of 608, strong 30 | 1, strong 12 |
   | PR113 380–440 | the four-frame transit | **6 of 135**, weak 1.6 | **1**, weak 1.1 (2nd: 0.55) |
   | PR113 348–471 | the same, the frames Measure would take | **11 of 294** | **1** (2nd: 0.69) |
   | PR113 108–708 | the same, what Find takes of a whole clip; not looked at beforehand | — | **1** of 400 |
   | PR055 90–350 | a black disc 72 px across at 4.5 px/frame | not on the list | **not on the list** |

   Taken from the first row on PR113 380–440 and linked, as the window does it:
   marks on 408 and 411, 4 of 4 frames, 0.00 px from the vendored track.
   **PR055 is a different limit, and now has a clip to its name**: a thing that
   moves less than its own size in 2k frames is at no place *only* at frame n,
   so the double difference cancels it ("Next, 1b (iii)"). More than one k.

   Where the recorded tracks are: `tests/golden/` (PR144, PR113) and
   `/hugespace/local/research/uap/analysis/` — `pr149_transit.csv`,
   `pr142_transit.csv`, `pr148_transit.csv` (frame, x_px, y_px) and
   `pr055_track.csv` (frame_A, x_A, y_A, visible; the clip holds the scene twice,
   zoomed ×3 at frames 97–343 and whole 970 frames later). "On" the track: more
   than 70 % of the frames they share within 12 px. The harness kept a crop of
   the frame round every peak, so a cue could be tried on all six clips in
   seconds without reading a frame again; it was in the session's scratch
   directory and is gone — five minutes to write again, six to run.

2. **What is further down can be asked for.** The panel keeps 30 things and
   shows the best few as before; "Show N more that the computer thinks less
   likely" shows the rest (strips are made once for a thing now, not at every
   refresh: eight rows of 1080p were 3.3 s on the GUI thread each time, measured). `mcdonald look
   --propose --more` is the same for an agent, and `--json` has
   `background_all_round`.

3. **A part too short to look in says so.** Someone who isolates "the segment of
   interest" in the new player opens 408–411, and Find, which compares each
   frame with the ones two before and two after, had nothing to compare and
   said "Nothing here moves". It now says the part is too short, how many frames
   it needs, and what to do; and the range chooser's guide asks for a second or
   two before the object comes and after it goes — which `layers` and Measure's
   "frames round the track" want as well.

Every row on PR113 still says weak, and should: four frames are little evidence.

## The player, and plain words (2026-09-21, second session)

1. **Which part of the clip? Watch it to say** (`46e91e1`). The range chooser
   was a slider over single stills labelled "about frame N". It is now a player:
   play, play backward, slower and faster, step a frame or ten, drag the bar,
   "Start here" and "End here" at the frame on the screen, "Play this part",
   the span and the cost as before. Nothing is extracted to watch it.
   `mcdonald/reel.py` (no window in it) reads frames from an ffmpeg pipe under
   the package's frame numbers: reading on is ~300 frames/s at 960 wide, a jump
   is a new ffmpeg (~0.5 s, half of it ffmpeg starting at all), going backward
   is served in chunks of 60 fetched before they are needed (206 steps back at
   30 a second on PR113 never waited; backward play runs at true speed), memory
   is bounded at ~170 frames and gives up what is furthest from the frame
   wanted. The keys for moving about are the main window's, from the same rows
   of `actions.ACTIONS`; `[`, `]`, `p` and shift+space are its own; every
   button's tip names its key, because a dialog has no menu.

   The numbers had to be earned: **the first version was right on the first
   frame of every seek and one frame out on every frame after it** (see Traps).

   `open_session` now also asks which part **when a clip is all on disk already
   but is over 900 frames** (`mark_qt.LONG`). That was Jacob's case on PR113:
   5291 frames left by an earlier run, so nothing was asked, everything opened,
   and Measure began hours of `layers`. *Mine, not asked* (see Decisions).

   The agent's counterpart already existed: `mcdonald look CLIP [--n0 --n1]`
   tiles a clip without extracting it.

2. **Plain words** (the commit that carries this). Jacob: "Make sure that all
   text that the user sees in the GUI follows /simplespeak" — his skill for
   writing in everyday words, scored against three word lists. Asked how far,
   **he chose the window's own text, and not (yet) the case report or the lines
   each stage prints into the Measure log**, which are the measurement's words,
   shared with the command line and pinned by tests. That is "Next, 3b".

   What was rewritten: every menu entry and its line of help, the key list,
   Help → Getting started (which now opens with "Four words": frame, mark,
   track, link — the four words of the trade the window keeps), every label,
   tip, note, dialog and title of the main window, the start dialog, the range
   chooser, the Find and Measure panels, the Measure form's labels, help and
   units (`stages.KNOWN`, so `mcdonald run --help` reads the same), the names
   of the long steps in progress lines ("step 5 of 9 · layers: comparing pairs
   of frames", on stderr too), and the sentences the window shares with the
   command line: the link's summary (`autolink._summary`), what Find says of a
   thing (`Proposal.describe`), the cost of a range, "no such file", ffmpeg
   missing. The vocabulary, to hold to: **a video, not a clip; a spot the
   computer found, not a detector's candidate; spot size, not scale; pixels, not
   px; speed and direction, not velocity; the results folder and the report, not
   the case folder and the case report; "saved as pictures", not extracted;
   step, not stage; orange, not amber/disputed.** Kept as names: the kinds of
   mark (hand, snapped, agent, proposed), the mark classes (boresight, north,
   reference, horizon — each said in plain words in its line of help), the
   stages' names where they label parts of the report (layers, integrity), and
   the report's headings, quoted exactly so that they can be found.

   *Not* rewritten, on purpose: what a mark's record says (`how`, shown as a
   tip in the marks table). It is written into the files and quoted by the
   report, so it is the files' wording; `MarkSet.kind` reads its first word.

   Measured with the skill's own script on text read off the live widgets (the
   menus, tips, labels, both Help pages, both panels, the chooser): words on
   the simple list (tier 2) **80.1 % → 96.0 %**, on the plain-adult list (tier
   3) 88.5 % → 98.1 %, allowing the window's few terms and everyday computer
   words (frame, pixel, video, click, folder, zoom, menu…). What is left is
   single letters (keys), units, and words like "brightness" and "streaked".
   `tests/test_gui.py: drive_plain_words` reads the same widgets and fails on
   the trade's words coming back (95 hits in the old text, none now), because
   text drifts back one tooltip at a time.

## What Jacob found, and what was done about it (2026-09-21)

He started `mcdonald-gui`, opened PR113, marked, linked, pressed Measure — "and
then I could not tell if it was hanging or just taking a long time". What his
case folder showed: he had the *whole clip* open, 5291 frames, so Measure had
begun 5286 frame pairs of `layers`, two and a half hours, with `integrity` after
it, behind one line of text. It was working. He closed it.

1. **Progress, in both shells** (`a2f57a4`). `mcdonald/progress.py`: `pooled` is
   `Pool.map` through `imap` — same results, same order, `test_golden` unchanged
   at 599.379 / 500.243 / 99.1534 — which calls `progress(text, done, total)`
   after every item and asks `stop()` between them, raising `Stopped`. Every
   long loop goes through it or `counted`: layers' pairs, integrity's per-frame
   background and the rest, the sheet's tiles, `frame_series`, `static_masks`,
   co-motion. `run_case` names the stage ("stage 5 of 9 · layers: frame pairs").
   The panel has a bar that counts, runs busy for a step that cannot count and
   stands still while it is the person's turn; the time gone; the time left in
   the step; and Stop now ends a stage at its next item. The command line
   prints the same on stderr (`progress.to_stderr`). That closes "Next, 4".
2. **Measure defaults to the frames round the track** (`measure_qt.around`: the
   track and 2 s either side), beside "all N frames that are open", with the
   cost of each said — in hours when it is hours. PR113's 408–411 becomes
   348–471: minutes.
3. **The window can look first** (the commit that carries this).
   `mcdonald/propose.py`, no interface in it; Track → Find the object (`f`,
   `find_qt.py`) and `mcdonald look --propose` over it. Its docstring is the
   method; in one line: a double difference on the globally registered
   background → compact residual peaks → chains at constant screen velocity,
   gated generously along the track and tightly across it → marked down where
   several go the same way at once (a layer, terrain under a pan, a scale that
   scrolls) → a score that orders a list. It yields as it goes, a block of frames
   at a time, so rows appear while it is still looking. "This is it" places up to
   ten marks along the proposal, as one undo step, and starts the link.

   **It proposes; it does not decide**, and the record says so: `how =
   "proposed: k of n …; accepted at the window by a person looking at its
   strip"`, `MarkSet.kind() == "proposed"`, never in `by_hand()`, and
   `Case._identified` puts "the detector's proposal, which a person looking at
   its strip accepted: the suggestion and the positions are the detector's, the
   yes was theirs" above the bottom line. An agent that takes one does it with
   `mark --set … --why`, so its marks are an agent's, as always.
   This is a fourth kind of mark, beside hand, snapped and agent. *Asked on
   2026-09-21, second session: Jacob chose to keep it* (see Decisions).

   Held against recorded tracks, which is the only reason to believe it:

   | clip | what it is | the recorded object is | taken, and linked by the package's detector |
   |---|---|---|---|
   | PR149 1–120 | a contact crossing at 20 px/frame, a ship in frame | proposal 1, `strong` (36), the only strong one; 69 frames, median 0.4 px from the hand workup | 20.12 px/frame for the published 20.2 |
   | PR144 300–500 | the sensor follows the object; only the background moves | proposal 1, `strong` (31), 177 of 177 frames on the vendored track | — |
   | PR113 380–440 | a four-frame transit of a dark blob, past a scrolling heading tape, under a pan the registration cannot see | proposal **6**, `weak` (1.6) | the vendored track exactly (0.00 px), 142.30 px/frame |

   So: where the object is the main thing moving against the background it is
   first and alone; in a hard clip it is on a list of weak rows, or may not be,
   and the click is what it always was. On PR149 1–240 the second strong
   proposal is the same contact after the sensor slews to follow it (171–238),
   which the recorded transit track does not cover but AARO's description does.

   Two things learned on the way that are about the *linker*, not the proposer:
   from two marks 51 frames apart it left PR149's contact where that crosses the
   ship and gave 16.3 px/frame; from ten it is off the hand track in 1 frame of
   22 (`Proposal.seeds` says why ten). And the package's detector sees that
   contact in about 37 frames where the proposer's residual sees it in 69.

## Where things stand (2026-09-20, end of the measurements session)

**Both audiences can now do the whole job alone.** The audit's two ✘ rows in §3
— measure, and read the results — are closed: Measure → Measure this clip makes
a case from the window and shows the report. And the agent's last gap is
closed: every command's `--json` has its numbers as fields.

How, in one paragraph: `run.py` was taken apart. Each stage is now a function
with no interface in it that returns a `report.Found` (fields, the report's
lines, no_power, needs, files): `layers.measure` and `layers.glance`,
`integrity.examine`, `tracksheet.sheet`, `comotion.measure`,
`symbology.measure`, and `stages.survey / scale / kinematics`. Each command's
`main()` is argparse over one of them and prints prose *written from the
fields*; `stages.run_case` runs them in order into a `Case`; `mcdonald run` is
argparse over `run_case`, and the window's Measure panel (`measure_qt.py`) is a
form over it. `cli._enveloped` and the `sys.argv` swapping are gone.

**The refactor was checked against a baseline, not assumed.** Before anything
was edited, the committed source was exported (`git archive HEAD`) and every
measuring command and three `run`s were run from it on the two Technical Note
windows (PR144 300–500 with the vendored track; PR113 400–420 from the two
documented clicks), from work directories of symlinked frames so that no cache
was shared. Then the same from the refactored source. `layers`, `kinematics`,
`comotion`, `symbology`, `tracksheet`: prose identical line for line,
`_layers.csv`, `_north.csv` and the track sheet JPEG byte-identical.
`integrity`: `_integrity_report.md` byte-identical and the JSON identical but
for one new field. `comotion` with an annulus that holds templates (D = 60):
prose and CSV identical, 36.5 D at 8.76 D/s. Inside `run`, integrity's JSON is
unchanged on PR144 and changed on PR113 only as item 2 below says it should.
The case reports differ from the baseline only where listed next.

### Found on the way: six things that were wrong, each fixed

1. **`mcdonald run` called the sea's screen speed the object's rate.** On PR144
   300–500 its bottom line read "The object moves 340 px/s against the
   striated" — with the vendored track, and *also with no track at all*. 340 is
   the striated layer's screen speed over one frame pair (n0 → n0+5), which
   `run` computed inline and `Case.bottom_line` printed under the object's
   name. The object against the sea on those frames is 599 px/s (and 500
   against the cloud tops): `mcdonald layers` said so all along. No test
   covered the sentence. Now: the bottom line reads the stages' fields, calls a
   rate the object's only where a stage measured the object, and says "No
   object was tracked" when none was (`test_reduction` pins all three); and
   with a track `run`'s layers stage *is* `layers.measure`.
2. **`run` and `integrity --marks` looked for a bright 9 px object whatever the
   marks had chosen.** The link knows the detector's size and polarity; only
   its track was passed on. On PR113 (21 px, dark) integrity's smear test had
   "0 usable frames" and halo "0 frames"; told 21 px dark they have 2 and 4
   (still NO POWER on a four-frame transit, and rightly). `run_case` and
   `integrity` now take them from the link (`autolink.link_from_marks_file`
   returns the Link); `run` has `--size/--dark` for a `--track`.
3. **`run --workdir` was not passed to the verify and integrity stages** (they
   were other modules' `main()` behind a swapped `sys.argv`, given only some of
   the options), so those stages opened the clip in the shared cache and
   extracted there. Gone with the refactor: one Clip is handed to every stage.
4. **The `layers` template cache did not know what it was made from.** Its name
   had k, step, n0, n1 and *whether* there was a track: a second run with a
   different track, `--mask-rows` or `--max-shift` silently reused the first's
   templates. And `test_golden`'s PR144 window had been finding templates left
   in `/tmp/mcdonald` on 2026-09-19 — 25 s instead of five minutes, testing the
   masks, the classes and the consensus and no registration at all. Now the
   name carries a hash of reach, rows and the track; `layers --fresh` measures
   again; `test_golden` passes it.
5. **The report's "Reproduce" section did not reproduce**: no `--n0/--n1`, no
   `--mask-rows`, no `--step 2` on the co-motion line, no size or polarity.
   `run_case` now writes each command with what it was actually given.
6. **Exit 1 for a result that is not a bug.** `comotion` with no usable pair and
   `symbology` with no pointer returned 1, which `clip.EXIT_CODES` reserves for
   a traceback. They exit 5 now, with the sentence in the envelope, and
   `kinematics` on a track too short exits 5 rather than 4.

### Decisions: three put to Jacob and answered; the rest are mine, to confirm

- **Answered 2026-09-21: a mark taken from a proposal stays a fourth kind,
  `proposed`** — not a hand mark (the position and the suggestion were the
  detector's), not an agent's (a person said yes), never in `by_hand()`, and
  the report says so on its face. He was offered "count it as `snapped`" and
  chose to keep it.
- **Answered 2026-09-21: plain words cover the window's own text**, not the
  case report or the stages' printed lines, for now ("Next, 3b").
- **Answered 2026-09-21: commits** — each finished step to `main` and pushed,
  for that session. (Ask again next session; it has been the same answer four
  times.)
- *New on 2026-09-21, not asked:* a clip of more than 900 frames is asked about
  (which part?) even when all of it is on disk; the window calls a clip "a
  video" and a candidate "a spot"; the table's first column is "what", not
  "class"; `save_all`'s first line is "saved N marks in …" (it was "wrote …").
- *Not asked:* Measure starts on the frames round the track, not everything
  open; Find starts on everything open unless that is more than 900 frames, then
  on 300 either side of the frame in view.

- **With a track, `run`'s layers stage is the whole `layers` measurement** —
  about a second per frame pair, so minutes where it was seconds. It is what
  `run`'s docstring always claimed ("the same code the standalone subcommand
  runs") and it is the toolkit's headline number, but it changes how long `run`
  takes. `--skip layers` is the quick run; without a track it is still the
  one-pair look (`layers.glance`). **Put to Jacob on 2026-09-20, against "only
  on request behind a flag": he chose to keep the full measurement.** He also
  chose, for this session, each finished step committed to `main` and pushed.
- *Not asked, so still mine:* `run` gained `--names` and `--dark-below` (layers' own), so the bottom line
  can say "against the sea", and `--size/--dark`.
- The window's track sheet is laid out six tiles across (`measure_qt.
  sheet_layout`), not the command line's thirty: thirty is one 11,520 px row to
  scroll sideways. What the sheet measures does not depend on it, and the test
  that compares the window's case with the command line's compares fields.
- A sheet closed without an answer is "no". The default button is "No, or I
  cannot tell".

## Next, in the order I would do it

1. **Jacob's hand on the player, on Find, and on Measure again.** He has used
   Measure once (above). He has not used the player, Find, or the progress bar.
   For the player: `mcdonald-gui`, PR113, and find the four-frame transit at
   408–411 by watching (it is a dark blob crossing right to left in 0.13 s —
   play at ⅛ speed, or step). Things I would watch: whether 960 wide is enough
   to see a small object (it is `RangeChooser(width=…)`, and memory goes with
   its square); whether half a second for a jump feels slow; whether he wants
   the last part he chose remembered between starts (it is not). `mcdonald-gui`, PR149,
   frames 1–240, `f`. Things I would watch: a minute and a half with the event
   loop running against 65 s from the command line — the linking is pure Python
   on a thread beside the GUI; whether "weak" rows are worth showing at all;
   whether ten proposed marks are more than he wants to see in the table; and
   whether the Measure form's eleven fields are too many at once.
1a. **Ask Jacob which part of PR113 he had open** when Find "did not work", and
   have him try it again. If it was a short part, item 3 above was his case; if a
   long one, item 1.
1b. **The proposer's limits, in the order I would attack them.** *(ii) is done
   — the table is at the top — and (iii) now has a clip: PR055.* (i) Global
   registration: one translation by phase correlation. A pan over a featureless
   sky (PR113) is invisible to it, and what saves PR113 is the "going the same
   way" cue, not the registration. `shift_field_auto` would see it, at ~1 s a
   pair. (ii) It has been held against three clips. `pursue_index/
   video_kinematics_triage.csv` and the analysis folder have more recorded
   tracks (PR142, PR148, PR055); a table of "rank of the recorded object" over
   all of them is the honest measure, and would say what the score should
   weigh. (iii) k = 2: a thing slower than its own size in two frames, against
   the background, cancels itself. (iv) Symbology that moves (PR113's tape) is
   only marked down, not recognised.
2. **A Mac.** Unchanged from before, plus the new panel: the menu roles (only
   "Save and quit" may move to the application menu), single-letter shortcuts
   in a native menu bar (`m` is one more), tool windows, `QStandardPaths`, the
   process pools under spawn (the stages' pools now start from a thread of the
   window, as the link's always did), `QDesktopServices.openUrl` for Open the
   case folder. `gui.desktop_entry` refuses on macOS with a sentence; what a Mac
   person double-clicks is undecided.
3b. **The report and the Measure log, in plain words.** The window now speaks
   plainly and then shows a report that says "NO POWER", "provisional",
   "px/frame against the striated layer". Jacob left it out of the plain-words
   pass for now because it is the measurement's own text: `report.py` and each
   stage's `Found` lines write it, `mcdonald run` prints the same, `test_reduction`
   pins its sentences, and `docs/agents.md` quotes it. It wants its own session:
   decide the level first (the skill's tier 3, plain adult English, is the
   likely one — it is a scientific record), keep every number and every NO POWER
   entry, and take a before/after of the fields (they must not move; only the
   prose may). `drive_plain_words` deliberately does not read the report page or
   the log.
3. **The report, for someone who cannot open a folder of PNGs with confidence.**
   The report page shows `_case.md`; the figures it rests on (`_layers.png`, the
   integrity figure, the track sheet, the strips) are files behind "Open the
   folder". Showing them in the page, under the stage they belong to, is the
   obvious next thing (`Found.files` already says which stage wrote which).
4. ~~**Stopping.**~~ Done 2026-09-21: `progress.pooled`. What is left of it:
   closing the *window* mid-measure sets the stop, and the step ends at its next
   item on a daemon thread, which nothing waits for.
5. **`symbology` is not a stage of `run`** and never was: a case report has no
   north-pointer reading in it. `symbology.measure` returns a `Found` like the
   others, so adding it is a few lines in `run_case` — and a decision about
   where it goes in the report.
6. **A `Case` cannot be read back from `_case.json`.** So "I have now looked at
   the sheet" means measuring again. With fields in the file it could be
   reloaded, the verify stage amended, and the report rewritten.
7. Smaller, noticed and not done: `contact_strip` still draws a mark a third of
   a pixel up and left at zoom 3 (`look.crop_view` is right and pinned); the
   cases folder and the last range are not remembered between starts;
   `mark --set` always records an agent; the start dialog and the catalog
   chooser are modal and no test drives them; `layers --validate` and
   `--composite` print and are not in the fields; `Case.result` still holds
   formatted strings beside `fields` (the report is printed from them), and
   `Case._num` still parses them for a hand-built case.

**Jacob's decisions (2026-09-20), which §5 asked for** — unchanged:

1. "GUI only" covers the **whole job, staged**. *(Now built.)*
2. An agent **may** decide which thing is the object, **recorded as the
   agent's**: `how = "agent: <why>"`, excluded from `by_hand()`, and a report
   built on it says so on its face.
3. Platforms for the person at the window: **Linux and macOS.** macOS is
   *unverified*: nothing here has run on a Mac.
4. Installation: **`pip install` once is acceptable**; no bundled app for now.
5. Commits: each finished step straight to `main` and pushed, *asked once per
   session*.

---

## 0. The brief, in Jacob's words

> In the next session, I'd like to focus on UI improvements. The tool should be
> usable with CLI only (in case users want their AI agents to do the work) but
> also in GUI-mode only (for human users with no AI).

Two audiences, then, and each must be able to do the *whole job* without the
other's interface:

- **an agent at a command line** — no display, cannot click, reads text and
  JSON, can look at an image file if one is written for it;
- **a person at a window** — no terminal, no flags, no AI to ask what the keys
  are.

His verdict on the window as it stands: "a nice feel", "all works great". So
this is not a rescue. It is finding out how far each audience actually gets
today, and closing the distance.

## 1. Where the package stands

`mcdonald` 0.2.0, eight commands (`mcdonald --help`): `run`, `mark`, `layers`,
`integrity`, `tracksheet`, `symbology`, `comotion`, `kinematics`.

The one input the package needs from outside itself is **which thing in the
frame is the object** (`handoff-gui.md` §1). Today that arrives as hand marks
from `mcdonald mark`, which has two windows over one `MarkSet`:

| | |
|---|---|
| `mark.py` | `MarkSet` (all state, with per-mark provenance `how`), `contact_strip`, the matplotlib `Marker`, `save_all`, `status_line`, `choose_gui`, `main` |
| `mark_qt.py` | the Qt window: timeline, true-speed playback, overview, detector candidates, loupe, undo, link (`l`), snap, nudge, extraction progress |
| `autolink.py` | marks → detector choice → candidates on a process pool → `link_track` both ways from every mark → residuals, arrivals, disputed frames. **No Qt in it.** |
| `--marks FILE` | `layers`, `integrity`, `run` link the track from a marks file first |

The pattern that made all of this testable, and the thing to keep: **one core
with no interface in it, thin shells over it, and one list of checks run
against every shell** (`tests/test_gui.py`'s rigs). Both of the new audiences
are, in that sense, just two more shells.

## 2. Audit: the command line alone (an agent)

*As it stood at the start of the UI session. Since closed: every row — the
six measuring commands' numbers became fields in the measurements session.
`docs/agents.md` is the worked session, and lists each command's fields.*

Walked through the PR113 job — find the object, mark it, link, measure — asking
at each step what an agent with no display can do *today*.

| step | today | gap |
|---|---|---|
| open a clip | ✔ path or catalog id; ffmpeg checked up front, exit code 3 with instructions if missing | — |
| **look at the clip** | ✘ nothing writes an image an agent could open to find the object. `tracksheet` needs a track first; the overview, the candidates overlay and the loupe exist only inside the Qt window | **the largest gap.** An agent cannot see |
| ask the detector | ✘ `forensics.frame_candidates` is Python only; no command prints a frame's candidates | no `candidates` command, no JSON |
| **place marks** | ✘ `mark` always opens a window (`mark.py` is the only `plt.show()` in the package, and `mark_qt` the only Qt). ✔ *but* a marks file is four lines and can simply be written: `{"classes": {"object": {"408": [1009, 313], "411": [702, 604]}}}` loads and links (checked; whole numbers are coerced) | no `mark --set … --no-window`; the file format is undocumented outside `MarkSet.to_dict` |
| link | ✔ `layers/integrity/run --marks FILE`; on PR113 all 4 frames where `--auto-track` gets 1 | the link is only reachable *through* another command; no `mcdonald link` of its own |
| check the link | ◐ `<tag>_autotrack_strip.png` is written, and an agent that can view images can look at it; the CSV header carries residuals, arrivals, disputed frames | nothing machine-readable says "this link is suspect" |
| measure | ✔ all six measuring commands run headless | — |
| **read the results** | ◐ `run` → `<tag>_case.json`, `integrity` → `_integrity_report.json`. `layers`, `kinematics`, `comotion`, `symbology` print prose and write CSV/PNG | **no `--json` anywhere**; an agent parses prose, as `tests/test_golden.py` does with regexes |
| know it failed | ◐ exit 2 unknown command, 3 no ffmpeg; anything else is a Python traceback and exit 1 | no table of exit codes; expected failures (no such clip, no track) are not distinguished from bugs |
| learn the tool | ✔ `--help` everywhere, `docs/method.md` for meaning | nothing written *for* an agent: no worked session, no statement of which judgments are the agent's to make |

**The question underneath the table, and it is Jacob's to answer (§5):** the
package's founding claim is that no detector can say which thing is the
object — a person looking can. If an agent places the marks, *the agent* is
making that judgment. The honest treatment already has a home: `MarkSet.how`.
A mark an agent chose must say so ("agent: candidate 2 of 9 at 21 px dark on
frame 408"), `by_hand()` must go on excluding it, and every file downstream
already carries `how` through. Do not let an agent's marks pass as hand marks.

## 3. Audit: the window alone (a person)

*As it stood at the start of the UI session. Since closed: start it, open a
clip (by id, and a second one), choose a frame window, choose where results go,
continue earlier work, find out what the keys are, told when something is
wrong — and, in the measurements session, measure and read the results
(Measure → Measure this clip; `measure_qt.py`). Every row is closed.*

Same job, asking what someone with no terminal can do *today*.

| step | today | gap |
|---|---|---|
| **start it** | ✘ `[project.scripts]` has only `mcdonald`; no `[project.gui-scripts]`, no desktop entry. Starting the window means typing `mcdonald mark` | **they cannot get in.** And PySide6 is an optional extra they must know to ask for |
| open a clip | ✔ with no clip named, a file dialog | ✘ no opening by catalog id (PR113), which is how the corpus is actually addressed; ✘ no opening a *second* clip without restarting |
| choose a frame window | ✘ `--n0/--n1` are flags only; the window opens the whole clip and extracts all of it (PR148: 1793 frames, 1.3 GB) | no range chooser; no warning of the cost before it starts |
| choose where results go | ✘ `--out` is a flag only; default `./<tag>` relative to a working directory the person never chose and cannot see | nothing on screen says where `s` writes |
| continue earlier work | ✘ `--load` is a flag only (it does reload `./<tag>/<tag>_marks.json` by itself if it is there) | no File → Open marks |
| **find out what the keys are** | ✘ **there is no menu bar at all** (0 `QMenu`/`QAction` in `mark_qt.py`). The key list is in `--help` and a docstring. A few buttons have tooltips | **the second largest gap.** `l`, `o`, `c`, `t`, `[` `]`, shift+click and ctrl+arrows are undiscoverable |
| mark, link, check | ✔ this is what the window is, and it is good | — |
| told when something is wrong | ✘ one dialog in the whole window (unsaved marks). ffmpeg missing, not a video, extraction failed, the link raised: all go to a terminal this person does not have | errors need dialogs with the same instructions the CLI prints |
| **measure** | ✘ `layers`, `integrity`, `tracksheet`, `symbology`, `comotion`, `kinematics`, `run`: no window of any kind | **the largest gap.** The window ends where the measurements begin |
| read the results | ✘ `<tag>_case.md` is a file on disk | no report viewer |

## 4. What follows, in the order I would do it

The rule to hold to: **a thing a person can do in the window and an agent
cannot do from the command line is a bug, and the other way about.** Build each
capability once, in a module with no interface in it, and give it two shells.

1. **One table of actions.** Every window action — key, name, one line of
   help, the function it calls — in one place, from which the menus, the
   Help → Keys page and the `--help` epilog are all generated. Today the key
   list exists three times by hand (`mark.py` docstring, `mark_qt.py`
   docstring, `keyPressEvent`) and they will drift. Cheap, and it makes 2 easy.
2. **The window, for someone who has only the window.** Menu bar (File, Edit,
   View, Track, Help) from that table; Help → Keys; File → Open clip / Open by
   catalog id / Open marks / Save / Save as; the case directory shown and
   changeable; a frame-range chooser that says what extraction will cost;
   error dialogs carrying the CLI's own messages; `[project.gui-scripts]
   mcdonald-gui` and a desktop entry. None of this is deep, all of it is
   between this person and the door.
3. **The command line, for something that cannot click.**
   `mcdonald look CLIP` → an overview sheet (the `o` tiles) as one PNG;
   `--frame N` → that frame with the candidates ringed and numbered, plus the
   same as JSON; `--at x,y` → the loupe's crop. `mcdonald mark CLIP --set
   object@408=1009,313 --set object@411=702,604 [--link] --no-window` → the
   same three files the window saves, plus the autotrack. Marks placed this
   way carry `how` (§2). Then `--json` on every command, one shape: inputs,
   files written, results, `no_power`, `needs` — `report.Case` already has that
   structure, so reuse it rather than invent another. And a table of exit
   codes, with expected failures told apart from bugs.
4. **The measurements, from the window.** A "Measure" menu that runs the same
   stage functions `run.py` calls, off the GUI thread with the progress
   pattern `extract_with_progress` and the link already use, and shows
   `<tag>_case.md` in a viewer. This is the big one; do it after 1–3 so that it
   is a shell over something already callable, not a fork of `run.py`.
5. **Two short documents.** `docs/agents.md`: PR113 done start to finish with
   commands only, what each JSON field means, and which judgments are the
   agent's and must be recorded as such. And a first-run page inside the
   window's Help for the person.

Testing: extend the rig idea. A `CliRig` that does "place a mark", "link",
"save" through subprocess calls, run against the *same* checks as `MplRig` and
`QtRig`, would hold the command line to the windows' standard — and the saved
files of all three can be compared, as the two windows' already are.

## 5. Decisions to put to Jacob before writing code

*Answered 2026-09-20; the answers are at the top.*

1. **How much of the job does "GUI only" cover?** Marking and linking (step 2
   above is then nearly the whole of it), or the measurements and the report
   too (step 4, several sessions)?
2. **May an agent decide which thing is the object,** or only operate the tools
   on marks a person placed? If it may: is `how = "agent: …"` with exclusion
   from `by_hand()` the right record, and should a report built on agent marks
   say so on its face?
3. **Which platforms matter for the person at the window?** The Qt window has
   never been run on Windows or macOS. If those are the audience, that comes
   before polish.
4. **How do they install it?** `pip install "mcdonald[gui]"` assumes a terminal
   once. If that is unacceptable the answer is an installer or a bundled app
   (PyInstaller / briefcase), which is its own piece of work and brings the
   licence question (`handoff-gui.md` §4) to a head, since a bundle ships Qt.

## 6. Traps already paid for

All in `handoff-gui.md` §0 ("New traps") and §8. The ones that bear on this
work:

- **Send events where real ones go** (`fig.canvas.callbacks`,
  `QApplication.sendEvent`), never to a handler. Four matplotlib defects and
  the GIL/`qWait` confusion were found, or hidden, by exactly this.
- **`QTest.qWait()` holds the GIL**; worker threads starve under it. Wait in
  `qWait(10)` slices (`QtRig.wait_for`).
- **Qt aborts without a display**; it does not raise. `choose_gui` checks first.
  A `mcdonald-gui` launcher must too, and must say so in a dialog if it can.
- **Never fork** from the window: the pool is `forkserver`/`spawn`, and the
  children import `__main__` by path — a console-script or gui-script launcher
  is fine, `python -` is not (`autolink` then runs inline).
- **Pixel centres at integers.** Any new view of a frame (an agent's annotated
  PNG included) has to agree with the red-pixel test's convention, or
  coordinates read off it are half a pixel out.
- **A check printed inside `redirect_stdout` is a check nobody sees.**
- **Counting checks:** count `  PASS` lines; the `ALL PASS` line is not one.
- **A `QKeyEvent` sent straight to a widget never meets the shortcut map.**
  Every key in the Qt window is now a `QAction` shortcut, so the rig sends keys
  with `QTest.keyClick` to the focus widget, and makes the window active first:
  an X server with no window manager activates nothing by itself, and shortcuts
  are live only in the active window (or a `Qt.Tool` child of it — which is why
  the strips and the Help page are tool windows). A synthetic key has no
  keyboard layout behind it: send `<` as `<`, not as shift+`,`.
- **Two `QAction`s with one shortcut cancel each other silently.** Qt calls it
  ambiguous and runs neither. `drive_every_key` fails naming both rows.
- **Text into a `QTextBrowser` is HTML.** An unescaped `<` (a key, here) ate a
  line of the Help page. `html.escape`.
- **`textwrap` breaks at hyphens**, so `mcdonald-gui` became `mcdonald-` /
  `gui` in `--help`. `break_on_hyphens=False`.
- **A clip is not required to know its video's name.** The linker asks a clip
  for n0, n1, W, H, fps, rgb, grey, and the test clips give no more. Reaching for
  `clip.video` in shared code broke the window's save under test; pass the
  MarkSet's.
- **A trial script needs `if __name__ == "__main__":`.** Without it every
  forkserver child re-runs the script, window and all, and the link fails with
  Python's "bootstrapping phase" error. Met again this session.
- **A planted object leaves the frame.** `PlantedClip` moves 41 px a frame in a
  540 px frame: after frame 12 every frame is the same, and a link of 11 frames
  is the right answer. Two "failures" in `test_cli.py` were this.
- **A mark copied from the detector cannot check the detector**, whoever copied
  it. An agent that sets marks at candidates' coordinates gets "within 0.0 px of
  all marks", which is circular. `docs/agents.md` says so; nothing enforces it.
- **An editable install runs whatever is in the tree at that moment.** A
  "before" baseline started as `mcdonald …` picks up every edit made while it
  runs (this session's first baseline had to be thrown away for that). Export
  the committed source — `git archive HEAD src | tar -x -C somewhere` — set
  `PYTHONPATH` to it and run `python3 -m mcdonald.cli`; snapshot the "after" the
  same way if you mean to go on editing while it measures.
- **A private work directory costs nothing: symlink the frames.** `Clip` asks
  only whether the first and last frame of the window exist, so a directory of
  symlinks into `/tmp/mcdonald/<stem>` is a work directory that extracts
  nothing, shares no `.npz` cache, and cannot grow the shared one. (The same
  fact is why a shared cache holding 90–340, asked for 300–500, extracts
  300–500 again.)
- **A cache beside the frames outlives the code that made it.** `layers`'
  templates did; see "Found on the way", 4. A test documented as five minutes
  that takes 25 s is not testing what it says.
- **`pkill -f pattern` kills the shell that runs it**, when the pattern is in
  that shell's own command line. Kill by pid.
- **A pixmap cannot be taller than 32767 px**, and a track sheet of a long clip
  at six tiles across would be. `measure_qt.sheet_layout` widens it instead,
  and the sheet window says so rather than showing an empty box if it is null.
- **A signal emitted from a thread to a panel that has gone raises
  RuntimeError** in that thread. The measuring thread's `say`, `progress` and
  `done` go through `tell()`, which lets it end quietly.
- **The Measure panel is a plain dialog, not a tool window**, on purpose: the
  tool windows keep the main window's single-letter shortcuts live while they
  have the focus, which is right for a strip and wrong for a form in which
  someone types "sea".
- **A Python thread is starved by a harness that turns the event loop in
  `qWait` slices, and much less by a real one.** Find on PR149 1–120 took 239 s
  driven that way, 107 s under `app.exec()` with a `QTimer` doing the watching,
  65 s from the command line. Time anything threaded the second way before
  believing it is slow, or fast.
- **A queued signal arrives after the thread that sent it has ended.** Waiting
  for `not panel.running()` is not waiting for the panel to have heard: one run
  in two, the bar was not yet full. Wait for what the slot sets.
- **A proposer tuned on one clip is tuned to it.** While the gates were being
  got right PR113's transit went 67th → 3rd → off the list → 6th, and PR149 and
  PR144 never moved from 1st. After any change to `propose.py`, run all three
  against their recorded tracks (the table above) and write the ranks down.
- **What moves in PR113 is mostly symbology**: a heading tape that scrolls with
  the pan, its numbers and ticks, and a pointer. The static masks are for what
  stays put; nothing masks what glides. Look at strips before reasoning about
  scores — it took one picture to see it and an hour of numbers had not.
- **An isotropic gate lets a fast chain collect strays.** At 140 px/frame a
  radius of 6 + 0.15 v is 27 px, and PR113's chain picked up terrain 60 px to one
  side of where the object was going, past the redaction block it had gone
  behind. Generous along, tight across (`propose.off_path`) — and a velocity
  from two residual centroids a frame apart needs slack of its own, or the true
  third point is 13 px "off" a line that was wrong.
- **`0 == False`, so `v not in (None, False)` drops a zero.** `stages._flags`
  lost `--n0 0`-like values that way; test identity, not membership.
- **ffmpeg, left to itself, copies the first frame after a seek, and every
  frame after it is then one out.** Writing raw video to a pipe it keeps a
  constant rate, finds the first frame half a frame late, and fills the gap.
  `-vsync 0`. It only happens in a file with a sound track (four drawn clips
  without one could not show it), so `test_measurement`'s reel clip has one.
- **Checking the first frame of each seek proved nothing about the second.**
  The reel's first trial compared one frame per seek with PR113's extracted
  frames and was "exact"; fourteen in a row showed the offset. Check runs.
- **A test that passes is not yet a test of the fix: run it with the fix taken
  out.** The reel test, as first written, passed without `-vsync 0`.
- **Least recently used is the wrong thing to forget when travel can turn
  round.** Playing forward and then stepping back, LRU threw away exactly the
  frames about to be shown. The reel forgets what is furthest from the frame
  wanted, a frame behind the direction of travel counting three times.
- **Space presses whichever button has the focus.** In the player every button
  is `NoFocus` (the dialog's Open and Cancel too), the spin boxes take the focus
  only on a click and give it back when editing ends, and the keys are
  `QShortcut`s on the dialog — so space plays, and the arrows step, wherever
  the last click was.
- **The word lists do not know what a computer is.** "video", "click", "folder",
  "menu", "zoom", "pixel" are on none of the simple lists, and "approximately"
  is on one. The skill says so: the lists are a first filter, and an everyday
  concrete word passes. Score with `--allow` for those, and read what is left.
- **Read the window's words off the window.** Most of them are f-strings made at
  run time; a grep of the source finds half. `drive_plain_words` walks the live
  widgets (text, tips, status tips, placeholders, titles, QActions, the Help
  pages) — and so did the scoring.
- **A word the person reads may be a word a file keeps.** `MarkSet.kind` reads
  the first word of `how` ("snapped", "proposed", "agent:"); the report quotes
  `how`. The window's note about a snapped mark is now its own plain sentence,
  and the record is left in the files' words.
- **A list with a cut-off hides its own failures.** The object was 11th and the
  window showed eight: to the person that is "it did not work", and nothing on
  the screen said there was an 11th. Show the best few, and say how many more.
- **Rank against every recorded track, not the one that failed.** The cue that
  fixed PR113 was tried on six clips before it was believed, and the one number
  in it that was chosen (sixteen sectors) was chosen on all of them. PR055 turned
  up as a miss that nobody had looked for.
- **Keep what a trial needs to be run again in seconds.** The slow half of Find
  is the residual of every frame; kept once, with a crop round each peak, a new
  cue is a second per clip to try. Without that, each idea is six minutes.
- **An editable install changes under a running pool.** Workers started after an
  edit import the edited module while the parent runs the old one. It did no
  harm here (the new `_frame` only adds a field); it would have with a changed
  meaning.
- Use **Technical Note clips** for real trials: PR113 (`--n0 400 --n1 420`, marks
  408 → (1009, 313), 411 → (702, 604), must give 142 px/frame) and PR144
  (`--n0 300 --n1 500`, vendored track in `tests/golden/`). PR148 is a poor
  demo: its object is far larger than the default detector scale.

## 7. First moves

1. Read the top of this file, then `src/mcdonald/reel.py` and
   `mark_qt.RangeChooser` (the player), `actions.py` (the window's words, and
   the vocabulary to hold to), `propose.py` (its docstring is the method and its
   measured limits), `find_qt.py`, and `progress.py`.
2. Run the suites (§8). `test_gui` is about two and a half minutes, `test_golden`
   about seven.
3. Put the decisions that are still mine ("Decisions", above) to Jacob — the
   newest first: asking about a long clip that is already on disk, and the
   window's vocabulary.
4. Ask him how the player, Find and the progress bar were in his hands ("Next",
   1), whether he wants the report in plain words next ("Next", 3b), and do
   "Next", 1b (ii) — the rank of the recorded object over every clip that has a
   recorded track — before changing anything in the proposer's score.

## 8. State at handoff

- `main` is pushed and clean. Commits of 2026-09-21 after the first session:
  `46e91e1` (the player: `reel.py`, the range chooser, a long clip on disk is
  asked about), `ed21a1b` (plain words) and the one that carries this file (Find
  on PR113: a spot or an edge, Show more, a part too short). Before them:
  `2c32192` (Find the object, `look --propose`, the `proposed` kind of mark),
  `a2f57a4` (progress in both shells; Stop ends a step; Measure defaults to the
  frames round the track), `8acd5e9` (run.py taken apart; fields in every
  `--json`; six fixes) and `aa0b9d6` (Measure from the window; Getting started).
- Suites, all passing on the final tree: `test_measurement` 115 checks (was
  101: the reel; a spot or an edge), `test_reduction` 97, `test_published` 32,
  `test_cli` 51 (two minutes; `--more`, `background_all_round`), `test_gui` 441
  with only WxAgg skipping (was 422: the player, the long-clip rule, plain
  words, Show more, a part too short; about two and a half minutes),
  `test_golden` 12 on the corpus, unchanged numbers (599.379 / 500.243 /
  99.1534) — run before the Find work, which touched no measuring module.
- Real trials of the window. Jacob's: Measure on PR113 (the first session of
  2026-09-21). Mine, under Xvfb with a real event loop and looked at in
  screenshots: the player on PR113 — first picture 0.44 s, a jump to frame 400
  0.56 s, 60 frames played in 2.01 s, 82 played backward in 2.74 s, "Start
  here" 400, "End here" 420, "Play this part" stopping on 420; the main window,
  the Measure form and Getting started in their new words. Earlier: the Measure
  panel in the middle of a run; Find on PR149.
- The proposer against recorded tracks: the table at the top of this file, six
  clips, run on the final `propose.py`. It replaces the three-clip table under
  "What Jacob found".
- Environment: as before (Fedora 44, Python 3.14.7, PySide6-Essentials 6.11.2,
  ffmpeg 8.1.2, editable install, no linter). `MCDONALD_CATALOG` is **not**
  exported in a fresh shell:
  `export MCDONALD_CATALOG=/hugespace/local/research/uap/pursue_index/records.csv`
  The simplespeak skill and its word lists are Jacob's, outside the repository
  (`~/.claude/skills/simplespeak`); nothing in the package or its tests needs
  them — `drive_plain_words` has its own short list of the trade's words.
- `/tmp` at the end of the session. As found: **Jacob's own PR113, all 5291
  frames (2.1 GB, in memory)**, and, from his trial of Find, **his PR144 98–194**
  (97 frames and a layers template), both left exactly as they were — his to
  clear — and an empty folder for PR149. The six clips' frames for the rank table
  (1.6 GB) were in the session's scratch directory, removed at the end. `test_golden` extracted PR144 300–500 there
  (201 frames and its layer templates); removed at the end, as it was not there
  at the start, and PR113's folder was checked to hold its 5291 frames and
  nothing else. The session's prototypes, logs and
  screenshots were in its scratch directory, removed at the end. His case
  folder `~/Documents/mcdonald/pr113` is untouched.
- Not done, on purpose: the report and the Measure log in plain words ("Next",
  3b — his choice, for now); remembering the last part chosen between starts;
  playing backward in the *main* window (its frames are PNGs on disk, so it
  would be a few lines, and nobody has asked); an FFT route through
  `source_candidates` (`handoff-gui.md` §0.2); any run on macOS or Windows.
