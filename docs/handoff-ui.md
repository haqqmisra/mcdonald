# Handoff: two ways in — the command line alone, and the window alone

Written 2026-09-20 at the end of the session that built the Qt marking window,
brought current at the end of the UI session the same day, again at the end of
the third session that day ("the measurements"), on 2026-09-21 after Jacob
first used Measure with a real hand (progress; Find the object), **and again at
the end of a second session on 2026-09-21, in which he asked for two things: a
real video player where the window asks which part of the clip to open, and for
everything the window says to be in plain words.** Both are done, committed and
pushed. **Later that day he tried Find: "worked on PR144 but not on PR113"**
(fixed, `4051656`), **and then PR055: "Find the object worked, but linking did
not"** — finished on the morning of 2026-09-22. **He tried PR055 again that
morning: "The object is located correctly, but linking seemed to find a
different track"**, and saved his session — the first section below, the same
day; he confirmed the fix ("Great, the linking for PR055 works now!"). **Later
that day the detector's 25 spots a frame were put to him (Next 1d): "every
spot" was tried on every recorded clip and was worse, and an edge-band bug in
the detector was found that the link leans on — both reverted, nothing of
either committed; see Decisions.** **That evening an AI agent ran the
command line alone on PR135 and wrote up what it found**
(`docs/agent-run-pr135-2026-09-22.md`); its worst item, `layers` reading a slow
scene as still, is fixed (the first section below), and the rest is triaged
there. **On 2026-09-23 the report's small items were done** (the first section
below): `symbology` fails fast and says how far along it is, how finely it
reads the angle and how much the boresight moves it; the `--why` header; where
the frames go. **Later on 2026-09-23 Jacob chose five things, in this order, and
they are done** (the first section below): the template's peak between pixels,
a point's blur measured (14 b), the detector's edge bug with the link looking
near where the object should be (Next 1d), and two new stages, `groups` and
`flicker`. PR148 links for the first time. He also said that Ravi will test on
macOS and Gary Nolan on Windows, once he says the polish is done. **That evening
he asked for every leftover to be finished** ("Go ahead and finish the leftovers"),
the parallax ladder included, and dropped the report in plain words ("I'd prefer
to use my own words when the time comes"): the first section below. The next
session starts from "Next". He has used the window end to end on PR144 (a part opened, Find, This is
it, link, Measure, a report), said the player "has a nice feel", and confirmed
PR113. He also set up Slurm on this machine on 2026-09-21, and the heavy checks
now go through it (`tools/*.sbatch`). Everything below was checked on this
machine unless it says otherwise.
`docs/handoff-gui.md` is the record of how the window got here; this is the
brief for what comes next. **On the night of 2026-09-26 Jacob asked for a roadmap of the
remaining scoped items: the roadmap section below; the older "Next" list further down is
superseded by it.** **On the evening of 2026-09-29 he said Galileo flyer 1 "actually has 4
different objects appearing" and asked whether mcdonald could find them all: the flyer 1 section
below -- it can now, and Find has a still-scene pass for it.** **On 2026-10-06 he asked whether the
window could find, follow and measure several objects at once, chose a queue of cases, and asked
for everything to run through Slurm: the second section below.** **On 2026-10-07 he set three design principles for the window -- no pop-up windows, one button that does the whole job, the report's conclusion first -- and they are built: the first section below.**

## 0.2.14 released (2026-10-08)

Jacob, after the count: "Great, works for me! Nice progress. This session is long so I should probably clear. Let's
commit and push this out as the next release." Main pushed (`12496ea`: the two sections below, the one window and
the count); then the version to 0.2.14 and the date to 2026-10-08 in `__init__.py` and both READMEs' status lines,
reduction and cli on the release tree (jobs rel_test_reduction and rel_test_cli: reduction 187, cli 99, all pass; the six suites had passed on `12496ea` as job 2080, and the bump
is strings), the release commit `0870b22` tagged `v0.2.14` and the tag pushed at 23:35:00 UTC for `publish.yml`
(trusted publishing). **On PyPI by 23:46 UTC** (`pip install mcdonald==0.2.14` from a fresh venv, `/scratch/mcdonald/venv-0.2.14`: version 0.2.14, released 2026-10-08, and its `mcdonald setup --offline --no-desktop` says "Ready."). It carries everything since 0.2.13: the window as one window with one button and
the conclusion first, the flicker stage on a flock's members, and the count of objects looked for. Testers on
0.2.13 are offered it at their next start. Not in it: the other session's untracked files (CHANGELOG.md,
CITATION.cff, CONTRIBUTING.md, wobble.py and its test) were left as they were.

## How many objects (2026-10-08, afternoon)

**Jacob: "Would it be helpful if the user told mcdonald at the start how many objects to look for?" -- then "Let's add
that, and then finish adding any other improvements before I test again."** My answer had been: yes, as an optional
hint -- the line the one press drew at "fair" was a guess of mine, and it had hidden flyer 1's second bird and left
PR135 as two groups -- and the count should drive how many rows the run takes, split a group into its members where
fewer things were found than asked for, and be held against what was followed, never forcing a thing out of noise.

**Built:**
- **The segment step asks** ("How many objects are you looking for?", a spin box that reads "I don't know" at 0,
  `RangeChooser.count`; a tooltip and a muted "Leave it if you don't know."). `choose_range` remembers it for the video
  (`objects/<video>`, like the part) and `QtMarker.load` reads it into `objects_expected` (`remembered_objects`), so
  the one press and the queue see it; a new video resets it with the rest.
- **The one press** (`AutoRun._found`): with a count, the first N rows of Find's list in rank order, weak ones too,
  through the queue whenever N is two or more (so a single group found can still be split); without, the rule as
  before. Its last line is the count against what was followed (`several.tally`'s sentence) when a count was given.
- **The queue** (`several.run_each(objects=N)`): after each thing, where fewer things than N are in the folder (a
  group whose members were made objects counts through them) and this one's case found a group of points (`is_group`:
  `groups` said several, two or more members followed, `<tag>_members.csv` there), its members seen on 60 frames or
  more (`flicker.MIN_FRAMES`: PR135's birds found again after the group's jump, 32 frames each, are not made objects
  twice) become the next `object-N` folders (`split_group`): the member's positions as `<tag>_autotrack.csv` (written,
  so the link cannot wander to the bird beside it), marks every ten frames and the last (`MARK_EVERY`; how: "member 8
  of object 1, one of the 3 points of that group followed on their own because 6 objects were looked for and fewer
  things were found"), and `<tag>_group.json` (`object`, `member`, `siblings`, `members` csv). `things()` reads it into
  `Thing.group`; `Thing.track` is the written track. The group's own case stays: its report is the flock's.
- **A member's case** (`run_case(..., flicker_of=, siblings=)`): the written track is its track (the link is not run),
  the groups stage is skipped (it would find the fellows again), the flicker stage is read from the group's
  (`flicker.of_member`: the member's beat over its own frames, its own where a pair with a fellow is independent; "as
  one with …" in step; "seen on 32 frames, under the 60 a beat needs"; fields carry `of_group`), and the tether stage's
  companion, where it sits at a fellow's offset (`stages.fellow_member`: median offset over shared frames, within 4 px
  or 30% and 20°), becomes `fellow_member` with the finding "the bright feature 24 px (4.9 object sizes) away that
  moves with the object is member 4 of the group it is in, not something tied to it" -- also on the group's own case
  (members from `groups`' carry), so no flock headline ends with "something moves with it" any more.
- **The list** (`several.index(objects=)`): first line in bold, "You looked for 6 objects: 6 were followed, 6 of them
  the members of 2 groups (objects 1, 2)." -- "; 1 was not found" / ", 2 more than you looked for" as the case is;
  the group's row names its members ("a group of points: its members are objects 4, 5, 6"), a member's row its group
  (`group: {object, member}`); the count is kept in the list's json (`asked`, `tally`) and read again by
  `report --index` (`asked_before`).
- **The command line**: `run --each DIR --objects N` (refused without `--each`, and under 1); its envelope has
  `asked` and `tally`; `look --propose --objects N` prints the N accept commands ("to take the 3 likeliest:") and says
  when fewer things were found than N.
- Docs: README (the sentence on the one press), README-technical (the panel paragraph; `run --each --objects`),
  docs/agents.md ("How many objects" paragraph; the envelope row), tests/README.
- Tests: test_reduction `test_how_many_objects_are_looked_for` (a drawn group of three on 120 frames: `is_group`,
  `tally`, `split_group` -- the member's track to the digit, its marks, its fellows -- `index`'s first line and the
  group's and members' rows, `of_member` its own / too brief / in step and the member's report leading with the bird,
  `fellow_member` at each member's offset and not elsewhere, the bottom line's sentence); test_cli (`--objects 3` on
  the two discs: the first line, the fields, remembered by `report --index`; `--objects` without `--each` exit 2);
  test_gui (the box on the segment step, "I don't know", 3 remembered and shown again; a count of 1 takes the first
  row alone; 3 on two things found: the queue, and the sentence under the button and on the list).

**Checked:** job 2080, all six suites on this tree -- measurement 237, reduction 186 (the count, the split, the member's stages), published 32, cli 98 (--objects on the two discs), gui 560 (the box, a count of one and of three; WxAgg skipped), golden 25 (WA9ONY-5 swing skipped) -- ALL SUITES PASS; before it, reduction 187 and cli 99 alone (jobs r10), and the gui twice: a drawn test clip has no video file, so `remembered_objects` gives None for it, and a list in the chooser's test had the name of the way-in check's.

**PR135, as he will test it** (the window under Xvfb, frames 1240–1389, the box at 6, one press;
`/scratch/mcdonald/pr135-count/`, driver `pr135_press.py` of the session): it ends with nine objects and the line under the button "You looked for 6 objects: 7 were followed, 6 of them the members of 2 groups (objects 1, 2), 1 more than you looked for." Find listed three things; the run took all three (the count asks for six). Objects 1 and 2 are the two groups, each "A flock of birds is the leading explanation: its 3 members each beat at …" -- and no longer "something moves with it" (the next bird is now named a fellow member). Object 3 is the third row, a bright spot followed 67 frames (1240–1306) at 115 px/s, "something moves with it": one more than asked, said as such. Objects 4–6 are object 1's members 8, 4 and 3 (the paper's E, F, D) and 7–9 object 2's members 7, 9 and 8 (A, C, B), each "A bird is the leading explanation: its brightness beats at …" -- 3.9 (and 7.8, its double), 7.5, 6.9, 7.8, 7.8 and 7.5 Hz -- with the member's own track drawn on the video in its colour (nine tracks drawn; the six colours go round). It took 48 minutes on four CPUs beside another job: Find over 150 frames, three cases with a link each, six member cases without. `after.png` there is the window at the end; `cases/pr135/` the folders and the list.

**Decisions that were mine, for Jacob to confirm or reverse:**
1. The count is a hint, never a demand: fewer rows than N gives the rows there are and "N were not found"; more
   members than N are all followed and said as "more than you looked for".
2. Only members seen on 60 frames or more become objects (the beat's length), longest first; the group's own case and
   report stay, and are counted through the members.
3. A member's flicker is the group's stage read for it, not a measurement alone (alone, three of PR135's birds are
   vetoed by the codec's line or the bird beside them); its groups stage is skipped; its tether stage knows its fellows.
4. With a count of two or more the one press always goes through the queue, even for one row, so a lone group can be
   split; a count of one takes the first row alone.
5. The count is remembered per video, like the part, and shown again on the segment step.

**Left:** Find still lists the flock as two groups (the count works round it; six things in Find's list is proposer
work, gated by the recorded tracks); a member's report card is like any object's (nine cards on PR135 at 6: the
column scrolls); `--objects` on the command line reaches the queue only, so an agent takes the N rows with
`look --propose --objects N`'s commands first.

## One window, one button, the conclusion first (2026-10-07)

Jacob asked for three things, in his order: **(1)** "New design principle: minimize pop-up windows whenever
possible. mcdonald GUI should open with the main window and the small pop-up for loading a case superimposed,
similar to how Adobe, Microsoft, etc. products work. After that, keep everything inside the main window,
including clip selection." **(2)** "Users should begin with an all-in-one button press option that goes through
all steps without asking for any confirmations. In many cases, the mcdonald high ranking choices are correct.
Users can choose an 'advanced' mode that reveals the step-by-step options available by default now." **(3)**
"The Report should be prettier and have the tentative conclusion (or lack thereof) at the top. We can tweak this
later once 1) and 2) are complete." All three are done, committed, not pushed, not released (0.2.14 is still
pending at his word, with the queue of cases and tether).

**(1) One window.** `QtMarker` can now be made with nothing in it (`QtMarker()`), and `load(clip, ms, out)` puts a
video into it in place; `unload` takes one out. Its middle is a `QStackedWidget`: a home page (the icon and
"No video is open…"), the video's own page (the frame, controls, timeline and the work area, built per video by
`_build_video`), and `Page`s over it. `mark_qt.Page` is what used to be a dialog beside the window: a title, a
"Back to the video" button, Esc, and a body. Pages now: the segment chooser (`RangeChooser(Page)`, with its own
Open and Cancel and `keep=True`, driven by a local `QEventLoop` in `choose_range` so `open_session` stays
synchronous), the wait while frames are saved or a video downloads (`BusyPage`, shaped like the
`QProgressDialog` it replaces: `setValue/value/maximum/wasCanceled/cancel`, so the loops are unchanged), the
report (`measure_qt.show_report`), the objects list (`several_qt.show_list`), the overview, the strip after a save,
and the two Help pages. The track sheet's question is a panel *under* the video (`measure_qt.SheetPanel`, in the
work area as the track's check is), so the video stays in sight while it is answered; closing it unanswered is
still "no". `show_page` closes any other page unless it is waiting for an answer (`keep`); `page_closed` takes
the page out of the stack and hands it to Python after Qt's own `close()` is over (not `deleteLater`: a test or
a panel may still hold it and ask it things; `setParent(None)` deferred by a zero timer). While a page is in
front the video's own keys are off (`_pages_changed`: `ANYTIME` needs no video, `PAGE_OK` works over a page --
save, report, find, measure, auto bring the video back -- everything else needs the video in front), because
space on the report page must not play the video behind it; with no video, only `ANYTIME` is live and the side
panel is grey. `gui.main` makes the empty window, shows it, and runs the start screen (`StartScreen`, still a
dialog -- the "small pop-up for loading a case") over it as a modal; Esc on it is `CLOSED` and leaves the empty
window, Quit (code 1 now) leaves the program. `open_session(..., window=w)` loads into a given window; without
one it makes and shows one first (so `mcdonald mark CLIP` opens the window and asks inside it too); File → Open
loads in place where it used to make a second window and close the first. The windows of their own that
remain, on purpose: the desktop's file and folder dialogs, the catalog-name prompt, the alerts (`complain`,
`confirm`, unsaved marks, the update offer) and About -- the OS's own prompts, as Adobe's and Microsoft's are.
`beside()` (the tool-window dialog) is gone.

**(2) One button.** `src/mcdonald/auto_qt.py`: `AutoRun` presses the three steps in turn, with the same code
behind each -- Find on everything that is open (the segment is the person's choice already), the first row of
its list taken by `FindPanel.accept_proposal(0, by=...)` with the marks recorded as "proposed … taken by the
window's one-press run as the first thing on Find's list, with nobody looking", the link from those marks
(Follow), and `MeasurePanel.start(ask=False)`, which passes `i_looked=False`: nothing is asked, and the report
says its numbers are not yet sure until someone looks at the sheet and says so on the report page's banner,
exactly as a queue of several objects does. The report then opens. Where a step gives it nothing -- nothing
found, nothing followed, a part too short -- it ends with a sentence that says so and points at Advanced.
`AutoCard` is the button at the top of the side panel ("Find, follow and measure the object", key `a`, a row of
`actions.ACTIONS` in the Track menu), the moving bar and "Step k of 3, …" under it (read off the three step
cards: `say_steps` writes those, then `AutoCard.say`), "Stop" while it runs, "Open the report" and "Measure
again" after. **Advanced** (a row of View, `check=True`; the arrow line under the button; remembered in QSettings
`panel/advanced`) shows the three step cards and "Mark the object by hand"; off by default. A mark placed by
hand turns Advanced on (its table and buttons are there). Help → Getting started has a new second entry, "One
press", naming `{auto}` and `{advanced}`.

**Later that day, after a first look: "in the simple 'one button' mode, we do not need the 'Which one is the
object?' or other inset frames popping up. Otherwise the user will be confused and think they need to make a
choice."** The run is quiet now: `AutoRun._find` does not show Find's panel (it looks and lists off screen),
`QtMarker._strips_ready` keeps the link's pictures without putting the check under the video while the run goes
(step 2 then says "Press “Check the track” to see the pictures along it"), and `Toast.quiet` holds every note over
the video from the run's start to its end. The card says which step it is on, the video shows the marks and the
track as they come, and the report is the one thing that opens. Advanced afterwards has "Show what Find found"
and "Check the track". The strip and Find's list still come by themselves when the steps are pressed one at a
time, as before. (`drive_one_button` +3 checks.)

**Then: "Can you run one more modern design audit to clean up according to what contemporary users will expect
for polished software? I'll check again after that."** Gone through as a reviewer of a 2026 desktop program would,
from the pictures and the code; what fell short, and what was done:
- **Two accents.** Selections and menu hover were Qt's blue, actions teal. One accent now: the palette's Highlight is
  `ACCENT` (dark text on it), as the buttons are.
- **The primary button's style, written seven times** with four paddings. One `mark_qt.PRIMARY` (and `QUIET` for a
  button that is not the thing to do now), used by every module; `measure_qt.MAIN` is an alias.
- **The segment chooser's Open and Cancel** wore the desktop theme's icons (a folder, a red circle) that nothing else
  in the window has, and Open was not marked as the thing to do: icons off, Open in `PRIMARY`, and **Enter opens**
  while the player has the focus (a `QShortcut` on the preview alone, so a frame number being typed keeps its
  Enter); the Shortcuts tip says so.
- **The empty home page** had only a line of text once the start screen was put away: it has "Open a video…" and
  "Open by catalog name…" now, the same two as the start screen.
- **An empty status-bar strip** ran along the bottom: it carries the video's name, segment, frame rate and size at the
  right (`where_label`), always, and the marking status at the left as before.
- **Report and Help text ran the window's width** (150-character lines at 1500 px): `mark_qt.ReadingView`, a text
  browser in a centred column no wider than 1000 px (`column()`), used by the report page, the objects list and both
  Help pages.
- **The one-button card's blurb** was five lines; three now. "← Back to the video" has its arrow.
- **Window title** was "mcdonald — planted": "planted — mcdonald" now, the document first and the program after,
  as desktop programs title their windows; a star after the name for unsaved marks.
- **The conclusion's headline** repeated the list of missing quantities that the paragraph under it gives: dropped
  from the headline. "9 test(s)" is a real plural in the bottom line now.
- Left as they are, on purpose: the dark theme (the frame must be the brightest thing on the screen; Jacob's choice
  of 2026-09-20), the menu bar without a toolbar (the side panel is the toolbar), the matplotlib window.
- Checked: the five suites (job 1776: measurement 235, reduction 170, published 32, cli 95, gui 543 and the WxAgg skip, all pass), then the two Help-page drivers alone for the reading view's margin; pictures of every page after the changes in /scratch/mcdonald/shots-2026-10-07/, looked at. Committed, not pushed.

**Then, after Galileo flyer 2 ("Find/Follow/Measure worked great"), four more, all done:**
- **"After I choose the segment, the progress bar should appear on the right column, not in the middle."** The wait
  while frames are saved, or a video downloads, is `mark_qt.BusyCard` now, at the top of the right column
  (`QtMarker.busy_slot`, above the side panel and outside it, so that it is live while the panel is grey), with the
  bar and a Cancel; the home page in the middle says "Saving the frames as pictures. The bar on the right says how
  far it has got." while it lasts. The card has the QProgressDialog's shape (`setValue/value/maximum/wasCanceled/
  cancel`), so the loops are unchanged; alone, with no window, it is a small window of its own. `BusyPage` is gone.
- **"Three colored indicators for (1) Find (2) Follow (3) Measure to light up when complete, in addition to the
  progress bar."** `auto_qt.StepLights` under the one button: three badges like the step cards' -- grey to do, a teal
  ring while under way, teal with a tick when done -- read off the window in `AutoCard.say` (marks on the object,
  a track followed, a report), the run's stage as the one under way.
- **"Once the 1-button mode is chosen, Advanced should no longer be an option."** `AutoRun.used` is set when the
  button is pressed (and Advanced turned off, if it was on); the "Advanced: one step at a time" line under the
  button is hidden from then on for that video (`reset`, at a new video, brings it back); View → Advanced stays
  in the menu for later, disabled only while the run goes.
- **"In the report, for a case like this the tentative conclusion should flag birds as a leading hypothesis based
  on the wingbeat rate."** `report.WINGBEAT_HZ = (2, 25)`: a beat of the object's own in that band puts "A bird is
  the leading explanation: its brightness beats at 3.4 Hz (and at 6.8 Hz, its double), the rate of a wingbeat, a
  rhythm of its own and not the video's (a tumbling body or a blinking light would beat too, and nothing here tells
  them apart)" first in the headline, and the label is "Tentative conclusion" whatever the sheet says -- a
  hypothesis is tentative by nature. The band: gulls and crows near 3 Hz, pigeons near 8, small birds to the low
  twenties; below it a blinking light (an aircraft's strobe, about once a second); above it nothing 60 frames a
  second resolves. The flicker stage's own note stands: it cannot tell a wingbeat from a tumbling body or a blink.
- **"The report should be a much shorter box with only the tentative conclusion, with the rest of the information
  hidden with a 'Show more' arrow."** The report page shows the title, the clip line, the provisional note if any,
  and the Conclusion card, then "▸ Show more" (`mcdonald:more`), which brings the rest in the report's order
  (`measure_qt.render` cuts at "## Summary of variables"; `page.more` holds the choice through re-renders, the
  banner's button included). The file on disk is whole, as `mcdonald run` writes it.
- Checked: the five suites (job 1814: measurement 235, reduction 171, published 32, cli 95, gui 547 and the WxAgg skip, all pass; +1 reduction for the bird line, +4 gui for the lights, the hidden Advanced line and the folded report), the smoke script and the one-window, extraction, one-button and measuring drivers alone; pictures of the wait card, the lights and the folded report in /scratch/mcdonald/shots-2026-10-07/, looked at. Committed, not pushed.

**Then ("Looks good!"), four more, done:**
- **"We can remove the time elapsed and time left in this step status indicators"** and **"Step 1 of 3 / 2 of 3 / 3
  of 3 -- can be removed, since the Find / Follow / Measure buttons now indicate this."** The one-button card's line
  is now the step's own line with the clock taken out (`AutoCard.say` drops the "elapsed" part and "about N:NN
  left"): "Motion search — 4 of 20", "Linking forward", "Step 2 of 12 · Survey — 4 of 24" (the measure's own count
  of its steps stays). The step cards under Advanced keep their clocks.
- **"The report should open in the right-hand column, underneath the 'Measure the Object' box, so that the video is
  still visible in the main window."** and **"Do a modern GUI audit for the report in its new place. Imagine how the
  Apple developers would choose to present content, using minimal words and even icons."** `src/mcdonald/report_qt.py:
  ReportCard`, under the one button in the right column, as an inspector would show it: a small caption REPORT; a
  badge and the label -- ✓ teal for a conclusion, ? amber for a tentative one, ≈ for no physical conclusion, – for
  none, … for none yet; the one sentence; when nobody has checked the track by eye, an amber line "⚠ Track not yet
  checked by eye" with "I looked" (`stages.confirm_sheet`, as the page's banner and `report --i-looked`); the numbers
  found as label-and-value rows in the fewest words ("Followed 11 frames, 1–11", "Speed, in the picture 41.4 px/frame
  (1242 px/s)", "Size, in the picture 15 px", "Beat 3.4 Hz", "Against the sea …"; `report_qt.SHORT`, only rows with a
  value); "More", folded, with the bottom line's paragraph and "Missing: …"; and two quiet buttons, "Full report"
  (the whole report as a page over the video, `measure_qt.show_report`, unfolded again -- the card is the short
  form) and "Folder". The card reads the case back from its `_case.json` and shows whenever the video has a report
  (`refresh` at every `say_steps`, re-reading only when the file's mtime changed); it appears when the measuring
  ends in place of the page, the video still in sight, and the one-button card says nothing more then (its "Open the
  report" button is gone; step 3's and Measure → Show the report open the full page). "I looked" on the page
  refreshes the card and the other way round.
- Checked: the five suites (job 1827: measurement 235, reduction 171, published 32, cli 95, gui 549 and the WxAgg skip, all pass; +2 gui), the smoke script and the plain-words, menus, one-button, measuring, several and finding drivers alone; pictures of the card -- folded, More open, and the full page -- in /scratch/mcdonald/shots-2026-10-07/, looked at. Committed, not pushed.

**Then ("the new report format looks good!"), two more, done:**
- **"When I am done and I open a new video, and I am selecting the segment, the right-hand column should reset
  rather than showing the output of the previous video."** `open_clip` unloads the video that was open as soon as
  the next file is chosen (after the marks are settled), before the segment page: the column is grey and empty
  and the middle is the home page while the next is chosen; cancelled on its page, the window stays empty, as at
  the start. (Before, the old video stayed loaded under the page until the new one replaced it, so that a cancel
  came back to it.)
- **"I am trying this on Galileo Flyer 1. So far it found 1 track but not the other 3."** The one-press run took
  Find's first row only; the other three were the queue of cases under Advanced (the ticks). Now the run takes
  **every row of Find's list worth following -- the first whatever it scores, and any other that is at least
  fair** (`Proposal.strength`: score ≥ 4) -- and with more than one it does what the ticks do: each row a folder
  of its own (`FindPanel.take_rows`, the marks recorded as "taken by the window's one-press run as one of the things
  on Find's list worth following, with nobody looking"), `several.run_each` on them in turn with nothing asked
  and nothing shown (`QtMarker.take_several(quiet=True)`: the several panel is made but not shown, Advanced not
  turned on), the lights Find ✓ then Follow and Measure both under way, and in the column **a report card for
  each object** ("OBJECT 2 · REPORT", `ReportCard(window, thing=…)`; `refresh_report_cards` at every `say_steps`
  from `several.things` of the video's folder; "I looked", "Full report" and "Folder" are that object's). With
  one row worth following the run is as before (the window's own case). Pressed again on a video whose folder
  already holds objects, it measures them again (`SeveralPanel.start(again=True)`). On flyer 1 that is the
  paper's bird, the spot and the second bird (the shortlist's three); the streak is weak and stays behind Advanced
  (Show more, tick it). Decision, mine: "fair" as the line, so that PR113's weak rows (a tape, redaction edges)
  do not each become a report.
- Also: a frame decoded for a video that has since been unloaded no longer reaches a timeline that is gone
  (`_timeline_state` guards; `_stop_all` disconnects the old store).
- Checked: the five suites (job 1846: measurement 235, reduction 171, published 32, cli 95, gui 554 and the WxAgg skip, all pass; +5 gui: the reset column, the two-object run on TwoPlanted with a card each and I looked on one), the smoke script and the one-window, one-button, several, measuring and plain-words drivers alone; pictures of the two-object run under way and its two cards in /scratch/mcdonald/shots-2026-10-07/ (12, 13), looked at. Committed, not pushed.

**Then (2026-10-08, flyer 1 again): "I see reports for 2 objects, but neither of the tracks shows up on the
video."** The queue's marks and tracks are in the objects' folders, and the window only ever drew its own link.
Now each object's automatic track (`object-N/<tag>_autotrack.csv`, written when its link ends) is read as soon as
it is there or changes (`QtMarker._refresh_object_tracks`, from `refresh_report_cards` at every `say_steps`, by the
file's mtime) and drawn on the video: a dotted line in the object's own colour (`mark_qt.OBJECTS`, by number) and,
on each of its frames, a box with its number (`Box(colour=…)`; `object_boxes`). The tracks appear one by one as the
queue goes. A click on a report card goes to the frame where that track starts (`ReportCard.first_frame`). On
flyer 1 two reports came where the handoff expected three: the second bird was below "fair" in that run; the
line is `Proposal.strength` (score ≥ 4), a decision of mine, and Advanced's ticks take any row.

**Then (2026-10-08): "even the initial pop-up window could be embedded into the main window."** Done: the start
screen is the home page now (`mark_qt.HomePage`: the icon and the name, Jacob's two sentences, "Open a video…" and
"Open by catalog name…", the videos opened last with the frames chosen then, where the data goes with Change…,
in a column no wider than 620 px). `StartScreen`, `choose_start` and `CLOSED` are gone; `gui.main` makes the
window, shows it, hands it the update check (`QtMarker.watch_update`: offered when it comes, never waited for;
yes closes the window for the helper) and opens a video named on the command line into it. Nothing pops up at
the start any more; the only windows of their own left are the desktop's file dialogs, the alerts and About.
His sentence with "kinematics" in it is kept word for word (the label is marked "technical" for the plain-words
test). Decision 1 under "Decisions that were mine" is overtaken.

**Then (2026-10-08, PR135 -- the paper's six objects): "Object 1 Report pops up while Object 2 is still working.
Maybe this is okay. But it does not find the bird wingbeat, and it looks like the track of Object 1 may skip to
another one of the objects partway through the track. Only two of the five objects are found. Because we have
published a somewhat high-profile paper on PR135, others who use mcdonald will want to see that the 'automatic
find/follow/measure' feature can reproduce what we did in the paper. Is this possible?"**

What his run had done (`/scratch/mcdonald/pr135/`, frames 1240–1389, the one press): Find listed three things,
two of them groups ("it holds about 3 points"), and the run took the two that were at least fair. Held against
the paper's six tracks (`pr135_tracks.csv`, letters A–F, in `/scratch/mcdonald/pr135-auto/paper/`): object 1's
track sits on E to frame 1357 and on D from 1358 (the jump he saw: the group's middle moved); object 2's on B,
flipping to C now and then (B and C are 11 px apart). `groups` had found the birds -- object 1's members on D, F
and E, then E, A, F after the jump; object 2's on A, B and C -- each on the right bird to 6 px. The flicker stage
then said nothing at all: with members it took the frames *all* members share, and with members seen from 1240,
1274, 1283 and 1358 that was none ("0 frames in common"), so no beat was looked for. The one line in the report
was "9 tests had no power".

**The probe, headless (`/scratch/mcdonald/pr135-auto/probe.sbatch`, job 2008):** the flicker stage on each
paper track alone finds every frequency -- A 7.85, B 7.40, C 8.02 (a 2-s window; 7.85 whole), D 7.09, E 7.67,
F 7.61 Hz, against the paper's 7.85, 7.38, 7.85, 7.11, 7.64, 7.60 -- and then vetoes three with the controls
written for a lone object: B is within resolution of the codec's 7.49 Hz line, and E and F have the neighbouring
bird in the "background beside it" aperture 25 px away. On the six paper tracks *as members of one group* the
stage says "members over the same frames beat at different frequencies or out of step, which a rhythm of the
video cannot do: the beat is theirs", with the six beats above: the paper's own control (its cross-spectra), and
the right test for a flock. So the group path -- Find's group, the link, `groups`' members, flicker on them --
is the path that reproduces the paper, and what stood in its way was the flicker stage's frames-in-common rule.

**Done:**
- `flicker.measure` reads the curves over the union of the tracks' spans and measures each member over its own
  span (`spans`, `seg`; the background apertures go with the member seen longest; a member under 60 frames is listed as
  "too brief for a beat"); `common` takes each pair over the frames both have, MIN_FRAMES or more, with the
  pair's own resolution, and says which frames (`pairs[].frames`); no two members sharing 60 frames is said
  ("no two members share the 60 frames it takes to hear whether they beat as one"). A single track is measured
  exactly as before (its own span is the whole), so flyer 5 and the drawn clips give what they gave.
- The report: the summary's beat row for a group says "6 members: 7.1–8.0 Hz, each member's own, out of step
  with the others"; the bottom line lists the members' frequencies; and the conclusion, where two or more
  members beat in the wingbeat band, leads with "A flock of birds is the leading explanation: its 6 members each
  beat at 7.1–8.0 Hz, the rate of a wingbeat, each its own and out of step with the others (a rhythm of the video
  would beat them as one; tumbling bodies or blinking lights would beat too)", labelled tentative -- "5 of its 6
  members" where one beats outside the band, and "; 3 more were seen too briefly to tell" where members were.
- Tests: test_measurement, members that come and go (the second seen from frame 61 only: both measured over
  their own frames, the pair over the 90 they share; two that never share 60 frames: each measured, nothing said
  of their beating as one); test_reduction, the flock in the conclusion, the summary and the bottom line.
- The one-press run on his two objects' marks again (`run --each` on a copy, `/scratch/mcdonald/pr135-auto/case/`):
  both objects say it. Object 1 (`groups`' members 3, 4 and 8, on the paper's D, F and E to 0.3 px): "A flock of
  birds is the leading explanation: its 3 members each beat at 3.9–7.5 Hz, the rate of a wingbeat, each its own and
  out of step with the others (…; 3 more were seen too briefly to tell)" -- D 6.90 Hz (the clearest 2-s window),
  F 7.49, E 3.90 with 7.8 named as its double; the pairs D×E and F×E independent over frames 1274–1357 (D×F within
  resolution and 39° apart, so not); members 14–16 (E, A and F again from the jump at 1358, 32 frames each) too brief.
  Object 2 (members 7, 8 and 9 on A, B and C): "its 3 members each beat at 7.5–7.8 Hz" -- A 7.80, B 7.46, C 7.78 Hz,
  every pair independent over 1283–1385; member 1 (A, 1240–1281, 42 frames) too brief. Against the paper's 7.85,
  7.38, 7.85, 7.11, 7.64 and 7.60 Hz for A–F: A, B, C, D and F within 0.2 Hz, E as the harmonic pair 3.9/7.8 (flyer
  5's reading). So the one press on frames 1240–1389 now gives each of the paper's six birds its wingbeat, in two
  reports rather than one; 4:46 on four CPUs for the two objects from their marks (job 2023).

**Checked** (through Slurm, niced): job 2022, reduction, measurement and golden on the per-member flicker (172, 237, 25 +
the WA9ONY-5 swing skip); then job 2024, all six suites on this tree with the headline's last wording -- measurement 237,
reduction 173, published 32, cli 95, gui 556 (WxAgg skipped), golden 25 -- ALL SUITES PASS; the two PR135 objects
re-measured from their marks (job 2023, 4:46) and their reports rendered again with the last wording (job 2029).

**Not done, and how it stands.** Find still lists the flock as two groups, not six things, and the group's
middle track can move from one bird to another (object 1, frame 1358), which reassigns the members' numbers
there (D, F, E became E, A, F; each piece is still measured on its own frames, and a piece under 60 frames is
dropped). To list six things, the proposer would have to split a chain whose residual holds several compact
points; to keep a bird's track whole, each member would be linked from its own positions as marks (the linker's
"between marks" mode on marks every ten frames on one bird) and the pieces folded where they overlap. Both are
proposer and linker work, gated by the recorded tracks (`tools/find_rank.py --link`); the six paper tracks are
written as mcdonald tracks in `/scratch/mcdonald/pr135-auto/paper/` for that, and `members.csv` there is the six
as one group. Also: the members' own tracks are not drawn on the video (the objects' are, since this morning);
`object-N/<tag>_members.csv` has them. And on a group the tether stage's companion is a fellow member -- both
PR135 reports end their headline with "something moves with it" (a bright feature 4.9 object sizes away: the next
bird); the stage could leave the companion out where `groups` found several and the companion sits on a member.

**(3) The report.** `report.Case.conclusion()` → `(label, headline)`: "Conclusion", "Tentative conclusion" while
the track sheet is unconfirmed, "No physical conclusion" where the object's motion was measured in the picture
but cannot become a real speed (no k, no R -- most clips), "No conclusion" (no track, nothing measured), "No
conclusion yet" (stopped). The headline is one sentence from the stages' fields (the relative speed in m/s if
there is one, else the pixel rate and what it needs; the beat; a tether; integrity's flags). The report leads
with `## Conclusion`: `**label.** headline`, then the bottom line's paragraph; `## Bottom line` is gone, the rest
of the order unchanged (Summary of variables, Missing quantities, Figures, Measurements folded, the marks,
Reproduce). `run --json` and `report --json` carry `results.conclusion` (`label`, `headline`) beside
`bottom_line`; `run` prints the label and headline above the bottom line at the end. The window's report page
draws the conclusion block as a card (a band behind it, under the teal heading). "Prettier" beyond that is the
tweak he said comes later.

**Decisions that were mine, for Jacob to confirm or reverse.**
1. The start screen stays a dialog (he asked for "the small pop-up for loading a case superimposed"); the
   segment chooser, the waits and everything after are pages or panels inside the window.
2. The one-press run searches **all** the frames that are open, not Find's ±300 round the current frame: the
   person chose the segment, and a longer wait beats a silent miss. (Find's panel keeps its own default.)
3. The run takes the **first row** of Find's list, whatever its strength, as he said ("high ranking choices
   are correct").
4. The run asks **nothing**, so its report is provisional until the sheet is looked at -- the same honesty as the
   queue of several objects, and why the headline reads "Tentative conclusion" (or "No physical conclusion")
   on a one-press run until the banner's button is pressed.
5. Advanced is off by default and remembered; a mark placed by hand turns it on.
6. While a page is in front, the video's own keys are off; `save`, `report`, `find`, `measure`, `auto` and the
   File/Help rows stay live. Esc closes a page.
7. The track sheet question is under the video (the video in sight), not a page over it.
8. The report's section order after the conclusion is as it was; "Bottom line" as a heading is gone (its
   paragraph is under the conclusion). The envelope's `bottom_line` field stays.
9. Only "Conclusion" (not "Tentative") when the sheet is confirmed, whoever placed the marks: the
   identification is already on the report's face.
10. **A flock in the conclusion** (round 9, PR135): two or more members beating in the wingbeat band, each its
   own (`beats` true on the members' independence), make "A flock of birds is the leading explanation" the
   headline, before a lone bird's; a member seen under 60 frames is listed as too brief and left out of the
   count; the background apertures sit beside the member seen longest, and that member's stretch is the one the
   report quotes as "frames".

**Checked** (everything through Slurm, niced). The five suites that need no corpus, through Slurm, niced: job 1700 on the tree before the last three test fixes (measurement 235, reduction 170, published 32, cli 95, gui 537 with 3 failures that were the tests' own expectations: the suite's long-lived rig counted as a second window, the Advanced setting remembered from the rig's drivers, and step 2 rightly saying "check the track" after a one-press run), then `tests/test_gui.py` alone (`logs/test_gui_gui2.log`): **540 PASS, 0 FAIL** and the WxAgg skip -- +27 this session (`drive_one_window` 9, `drive_one_button` 15, the rest in the drivers that changed), reduction +4, cli +1. golden not run: nothing that measures changed, and `test_golden` does not read the report's text. Pictures of the real window under Xvfb -- the empty window with the start screen over it, the chooser page, the simple panel, the one-press run at each step, the report page, Advanced on -- are in `/scratch/mcdonald/shots-2026-10-07/`, looked at.

**Left, and known.**
- The report's look is a first pass: the conclusion card, the same page otherwise. "Prettier" is his tweak to
  come; the headline wording too.
- A page closed is kept alive for whoever holds it and freed by Python; a report page's document goes with it.
  If memory ever shows, pages could be deleted when nothing but the window holds them.
- The several panel's rows and Measure's form are unchanged; the one-press run uses Measure's form as it
  stands (the slow checks: layers on, integrity off), as the queue does.
- `tools/drive_one.py drive_the_finder` alone stops at once (`marked[-1]`, an empty list): that driver expects
  the marks earlier drivers put on the same rig, as it has since it was written; in the suite it passes. Not
  changed. `drive_one_button`, `drive_one_window`, `drive_finding`, `drive_several` do run alone.
- "Check the track" (Advanced, step 2) now brings the video to the front from under a page, as Find and Measure
  do; before, pressed with the report in front, it built the strip where nobody could see it.
- `CHANGELOG.md`, `CITATION.cff`, `CONTRIBUTING.md` are still untracked in the root, not mine; the changelog's
  Unreleased list does not know this section.

## More than one object in a video: a queue of cases (2026-10-06)

Jacob: "Is there a way for the GUI to find/follow/measure multiple objects at once?" As things stood: Find
lists everything that moves; "This is it" takes one row, always as "object"; Follow follows "object" and
"object #2" (the second only from clicks); Measure measures "object" alone, one report to a results folder.
Offered two ways to build it -- a queue of cases, or many objects inside one case -- he chose **"Yes, do 1. A
queue of cases"**, and said **"please run everything through slurm"** (below).

**What it is.** A case stays what it was: one video, one object, one report. Several objects are several
cases, each in a folder of its own under the video's results folder (`object-1`, `object-2` ...), made in turn,
with one page that lists them.

- **The core, no interface in it: `src/mcdonald/several.py`.** `place` writes one thing's marks into the next
  free `object-N` (as a save writes them: json, csv, the strip); `run_each` runs `stages.run_case` on every
  `object-N` in turn, each over the frames its marks are on and two seconds either side (`stages.around`, the
  rule Measure already had, now in one place), with `i_looked=False`, progress with the object's number in
  front, `stop` asked before each object and inside each, and the list written again after each; `index`
  writes `<tag>_objects.md` and `.json` from what is in the folders (chosen as, followed, bottom line, track
  sheet looked at or not, the report); `listed` brings a case's line up to date when its sheet is confirmed.
  One that has a report from the same marks, measured to its end, is not measured again (`again`). A marks file
  may say which frames the thing was *seen* on (`MarkSet.seen`, a new optional key, written for Find's marks),
  and a case then covers those too: Find's marks keep off the frame's edge, and a thing is seen on more frames
  than it is marked on.
- **The command line: `mcdonald run VIDEO --each DIR`** (and `--again`), `mcdonald report DIR --index`, and
  `report CASE.json --i-looked` now refreshes the list its case is on. `docs/agents.md` has the section ("More
  than one object in the video") and the envelope rows; `README-technical.md` the same under Use.
- **The window: `find_qt` and `several_qt`.** Every row of Find's list has a tick, "one of several"; with rows
  ticked a bar under the list says how many and has the one teal button, **"Follow and measure the ticked
  ones"**. Pressed, each ticked row gets a folder with its marks (recorded as proposed, in the words "This is
  it" records), Find is put away, and `SeveralPanel` opens under the video: a row for each object (Find's
  strip, small; what it was chosen as; how it stands), **Stop**, **Measure the rest (n)**, **Open the list**
  (the page, with reports opening from it as reports do), and on each row **Open its report** and **Open in
  the window** -- which brings that object's marks into the main window, moves the folder it saves to into
  the object's, and starts Follow there, for a track that needs a hand. The three step cards say how the
  objects stand while the window has no object of its own ("2 objects chosen from what Find showed ...", the
  queue's step under way in step 3, "2 of 2 reports are ready"), step 3 has **Show the objects**, and Measure
  → **The objects of this video…** opens the list. Help → Getting started says the way in.

**Decisions that were mine, for Jacob to confirm or reverse.**
1. **Nobody is asked about a track sheet while the queue runs.** The single-object Measure stops and asks; a
   queue that did would not be one to leave running. Every report is therefore "not yet sure" until someone
   opens it, looks at its sheet, and presses the banner's button (or `report … --i-looked`); the rows and the
   list say which have been. Nothing skips the look; it is moved to afterwards.
2. **The objects are numbered in the order of Find's list**, from the first `object-N` not yet there, so
   nothing measured earlier is written over. The marks' record keeps Find's own row number ("proposed: 2 of 5
   …").
3. **Measure's form is used for every object**: what is known of the video, and which slow checks to make
   (layers on, integrity off, as Measure starts).
4. **The window's own marks, track and report are not touched** by a queue. An object in the list is a
   folder; "Open in the window" is the way to work on one by hand.
5. **One tick box a row and one button**, beside "This is it", which is unchanged. One row ticked is allowed
   (a queue of one).
6. **The background step is not shared between objects.** I had said I would check: `layers`' templates are
   made with the object's track in hand and the cache key has the track in it (since 2026-09-20, on purpose),
   so each case measures its own. Left alone; a later speed-up if the wait matters.
7. **No "time left" for the queue**: a step can count, the queue cannot.

**The Galileo clips moved.** Jacob flattened the Zenodo package on the morning of 2026-10-06: the five clips, their
paper tracks and `galileo_clips.csv` are in `~/research/uap/zenodo_pr135/` itself now, beside the paper's files,
not in `galileo_dalek_clips/`. golden's flyer 5 case skipped and the first window run on flyer 1 failed at once
for it. `tests/test_golden.py` and `tools/find_rank.py` look in the package and in `galileo_dalek_clips/` under
it if that exists, and `MCDONALD_GALILEO` overrides both.

**The window itself on flyer 1** (Slurm job 1321, 4 CPUs, under Xvfb; `/scratch/mcdonald/flyer1/gui/harness.py`, its
log `harness_1321.out`, its pictures in `gui/shots/`, all looked at): Find on all 1705 frames (6:08), the five rows
as the still-scene pass gives them, "Show more", the first four ticked -- "4 ticked. Each will be followed and
measured in turn, and get its own report." -- the button, and 48:09 later "4 of 4 reports are ready": object 1
(the paper's bird) followed on 1013 frames 693-1705, **its beat 3.37 Hz** (the paper's 3.36), 16.7 px/s; object 2
(the spot) 63 frames 1642-1705; object 3 (the second bird) 905 frames 801-1705; object 4 (the streak) 13 frames
1215-1227. The step cards read "4 objects chosen from what Find showed, each in a folder of its own" / "Each one was
followed when its turn came." / "4 of 4 reports are ready. Press “Show the objects” for the list." The list page
and object 1's report page, with its banner, are in the pictures. One thing the run showed and that was then
changed: a case was measured over its *marks'* frames and two seconds either side, and Find's marks keep 70 px in
from the frame's edge, so object 1's case began at 693 where Find had seen the bird from 638. The marks file now
carries the frames the thing was seen on (`MarkSet.seen`, written by `several.place` for Find's marks, read by
`run_each`), so a case covers them; the four cases under `gui/case/` are from before that change.

**Checked** (everything through Slurm). `tests/test_cli.py: test_several_objects_are_a_case_each` (12 checks) and
`tests/test_gui.py: drive_several` (18) on a drawn video with two discs (`test_measurement.TwoPlanted`), both
holding an object measured in the queue to the object measured alone with `run --marks`, to the digit; the
several panel in the plain-words walk; the Qt child's deadline 420 -> 540 s for the new driver. Six suites on the
final tree, Slurm job 1335: measurement 235, reduction 166, published 32, **cli 94** (+12), **gui 513** (+18) + the
WxAgg skip, golden 19 -- all pass (an earlier run, job 1315, had one GUI failure, the playback-timing check that
fails under load, and golden skipping flyer 5 for the moved clips; both gone in jobs 1322 and 1335).

**Everything through Slurm, since this session.** One-off checks go through `srun -n 1 -c 4 --mem=6G
--time=15:00 …` (it blocks like any command), longer ones through `sbatch` with a waiter. Two things learnt on
the way: a runner script that starts a pool needs the main guard (Python 3.14's forkserver ran the script's
body a second time and Find's pool never came up: 0 proposals in 240 s), and a single Qt driver runs alone
under `xvfb-run -a` with `QT_QPA_PLATFORM=xcb` and its own `XDG_CONFIG_HOME`: **`tools/drive_one.py NAME`** does
that for any driver of test_gui.py, given what its parameters ask for (its docstring has the `srun … xvfb-run …`
line). `TMPDIR=/scratch/tmp/mcq1` (short, for the pools' sockets).

**Left, and known.** The list's rows show no picture for an object that was not chosen in this session (the
strip is Find's, kept in memory). Things ticked while a queue runs wait for "Measure the rest". Two objects'
files have the same names in different folders (`object-1/<tag>_case.md`, `object-2/<tag>_case.md`): the
folder is what tells them apart. Not released: 0.2.13 is on PyPI; this is for 0.2.14 at Jacob's word
("This is all great", 2026-10-07; not pushed).

**Where the next session could start -- Jacob wants "more GUI improvements" (2026-10-07).** Things seen in
this session's pictures of the real window, none of them asked for yet:
- Step 1's line still says "3 found" after "Show more" has shown five; it counts the shortlist.
- A queue's rows have no picture for an object chosen on an earlier day, and the description under a row is
  Find's line cut short; a row could show its first and last frame instead.
- Which slow checks and which known facts a queue uses come silently from Measure's form; the panel could say
  so, with a way to change them before it starts.
- The report's list page ("Open the list") and the report page are two viewers with the same bones
  (`measure_qt.show_report`, `several_qt.show_list`); one viewer with a title and a click rule would do.
- The Find panel's bar under the list, the Measure form and the several panel each take the work area in
  turn; a tab or a crumb line would say which is open and let the person go back without the menus.
- On a 1500 px window the video is a 640 px frame at 1:1 with black either side (01_open.png): a video
  narrower than the view could be shown larger by default.
- Keys: the several panel has none (the actions table gives it a menu entry only); Stop and "Measure the
  rest" could have them, as Measure's do.
`tools/drive_one.py` runs any one GUI driver alone under Xvfb through Slurm, which is the loop for this work.

**Not mine, left as found:** three files appeared untracked in the repository's root on the evening of 2026-10-06
-- `CHANGELOG.md`, `CITATION.cff`, `CONTRIBUTING.md` -- after this session's work began. They are not committed
here; whoever wrote them commits them. Another session committed two **tether** commits on top of this work on
2026-10-07 (`e9e31d6`, `6ecb146`: "is something tied to the object, and does it swing?", a stage of `run`) with no
section in this file; their messages are the record. Unpushed on main, oldest first: `fdb9b6b` (this section),
the two tether commits, and `71f7448` (the cleanup). Scratch from this session is cleared (`/scratch/tmp/mcq1` empty); the
flyer 1 evidence stays under `/scratch/mcdonald/flyer1/` (the four cases by hand under `A B C D`, the window's
four under `gui/case/`, the pictures under `gui/shots/`, the frames under `/scratch/mcdonald/frames/`).

## 0.2.13 released (2026-10-05)

Jacob: "Go ahead and push, then make the next release." Main pushed (`8d6f1b9`, the flyer 1 section below);
then the version to 0.2.13 and the date to 2026-10-05 in `__init__.py` and both READMEs' status lines, the
six suites on the release tree (Slurm job 1280: measurement 235, reduction 166, published 32, cli 82, gui 495 +
the WxAgg skip, golden 19, all pass), the release commit `da5d020` tagged `v0.2.13` and the tag pushed at
02:06:54 UTC for `publish.yml` (trusted publishing). **On PyPI at 02:07:49 UTC** (`mcdonald-0.2.13-py3-none-any.whl`
and the sdist); checked from a fresh venv (`/scratch/mcdonald/venv-0.2.13`): `pip install mcdonald==0.2.13`
gives 0.2.13, released 2026-10-05, source "pypi", and `mcdonald setup --offline --no-desktop` says "Ready.".
It carries the still-scene pass and everything the section below records. Testers on 0.2.12 are offered it at
their next start (`update.py` reads PyPI). Jacob tests next; flyers 2-4 are the controls still to try.

## Galileo flyer 1: four things in one clip, and Find's still-scene pass (2026-09-29, evening)

Jacob: "The 'Galileo Flyer 1' video of a bird actually has 4 different objects appearing. See if you can use
mcdonald to find them all."

**What is in the clip.** 1705 frames, 28.4 s at 60 fps, 640 x 512, a camera that does not move (the K-baseline
registration finds no shift on any frame, and a second finds nothing clear). Checked with a detector of my own
that owes nothing to `propose` (a median background over +-75 frames, compact peaks, nearest-neighbour chains:
`/scratch/mcdonald/flyer1/truth/truth.py`, `tracks.csv`): four things, and nothing else above noise --

- **A, the paper's bird**: a 5 px bright spot crawling down and to the right at 0.26 px/frame (16 px/s), from
  (80, 23) at frame 611 to (244, 256) at 1705; the paper's track (660-1584) lies on it to 1.3 px.
- **B, a second bird along the top edge**: fainter (SNR 22 to A's 53), 18-38 px below the top, right to left at
  0.20 px/frame from (631, 18) at 736 to (437, 19) at 1705.
- **C, a streak**: a bright dash drawn out along its motion, crossing the frame left to right at 56 px/frame in
  frames 1218-1227, with a faint trail behind it.
- **D, a spot**: bright, coming in at the top right at 1639 and moving down and right at 3.9 px/frame to
  (382, 239) at 1705.

**Find as it was (0.2.12) had two of them.** Over the whole clip (`mcdonald look CLIP --n0 1 --n1 1705 --propose
--more`, Slurm job 1251, 1:34 on 8 CPUs; the run is kept in `/scratch/mcdonald/flyer1/before/`): D first, fair
7.2; C second, weak 2.7, and a piece of it third; and the paper's bird only as two fragments of three and four
frames, scored 0.0 -- "moves 0 pixels each frame against the background" -- at 717-724 and 919-924; B not on the
list at all. The cause, measured at frame 1000: the double difference compares a frame with the frames K = 2
before and after it, and a thing that has moved 0.6 px in that time -- a fraction of its width -- leaves 7 grey
levels of residual at the bird (below `peaks`'s floor once smoothed) and 4 at B; at 30 frames either side, 103
and 59. The fragments were the bird's flaps. And B could never have been proposed: it runs 18 px from the top,
inside the 30 px band `not_scene` closes at the frame's edge for the registered residual's sake.

**The change (`propose.py`, the docstring's step 1 and the table at its foot; `tests/test_measurement.py`
`test_a_crawler_in_a_still_scene_is_proposed`, 12 checks on a drawn still sky at 60 fps with a sensor's pattern
and noise, two crawlers, one of them 18 px from the top; `tools/find_rank.py` with two Galileo cases).** Each
item below was found on a clip, not thought up; the order is the order they came in.

1. **A still-scene pass** (`still_peaks`, `half_second`, `EDGE_STILL`, `STILL_SHIFT`). Where the scene holds still
   -- `onto` shifted neither neighbour by more than a quarter of a pixel over K frames, *and* `still_again` found
   nothing clear over a second -- the frame is compared again with the frames half a second either side (30 at
   60 fps, 15 at 30), unshifted, with the edge band 12 px in rather than 30. Asked for exactly no shift, the pass ran
   on a quarter of flyer 1's frames and its chains never lasted: on a still noisy sky `onto` shifts one frame in
   three by 0.03-0.23 px, because a fraction of a pixel of linear interpolation smooths the noise and "fits
   better" (job 1259 came back with the 0.2.12 list). A quarter of a pixel is the tolerance.
2. **Its peaks are chained apart, and held to what the pass is for** (`lasting`, `STILL_SPEED`). They carry a
   twelfth field saying which pass they came from; `search` chains the two populations separately and keeps of
   the still pass's chains the ones that last the half second and crawl under a pixel a frame. What the pass is
   for is in the frame at least that long and too slow for the residual at K; what else it finds is the sky's own
   dim change over half a second (4-5 grey levels, lining up by chance three frames at a time at any speed:
   thirty weak rows on flyer 1 before the rule) and, under a still camera, a sea. **Why apart: PR149**, a still
   camera over a sea, the contact crossing at 20 px/frame, a ship drifting at 0.98 px/frame. Its sea's
   half-second residual is ten peaks a frame at 105-125 grey levels where the K pass's are 12-25; mixed in
   (job 1254) the contact's `stands_out` halved (19.95 -> 10.01) and wave pieces lent Find's marks frames, five of
   its link's frames off the recorded track. Chained apart, the K pass's rows and everything said of them are as
   they were.
3. **A still row stands out among its own residual's peaks** (`describe.typical`): held against the K pass's,
   PR149's ship's parts stood out five times and came first at 24.95. Where a frame has none of one residual's
   peaks, the other's are the measure (a still sky: two birds and little else).
4. **Company for a slow flow** (`score`): company needed a pixel a frame of speed to count, so the ship's seven
   parts at 0.98 px/frame were nobody's company. A direction now needs either that speed or a way of 30 px
   made *at its speed over its frames* -- at its speed, not its extent: six scattered peaks on PR144 with an
   extent of 830 px at 1.4 px/frame counted as the followed object's company and halved it (41.10 -> 20.55).
   And company is counted **before** the fold, as it always was: counted again among the rows left, PR113's
   terrain under its pan lost most of its company and four of its rows went above the transit (5th of 114 in
   job 1258; it is 1st again).
5. **`still_again` will not take a moving thing for the background where it can tell.** A drawn crawler in a
   sky with nothing else sharp in it peaked at 0.21 of the whitened energy against 0.03 at zero shift, was read as
   the background's drift, and cancelled itself out of the still pass: the peak must now stand *below* the peak
   at zero (`background_shift(zero=1)` returns that as a fourth value; `forensics.sensor_defects` unpacks it).
   Drawn again bright (60 grey levels) on white pattern noise it peaked below zero and clear, and one global shift
   cannot tell a faint scene drifting from one clean bright thing moving. Two tells were tried and dropped -- the
   area the shift betters as a share of what it spoils (PR135 7.5 % against 17 %; the crawler 0.3 % against 58 %;
   but the drawn drifting scene of `test_propose_measures_a_slow_background_again` 1.4 % against 14 %, right at
   the line), and the same shift turned a right angle as a null (1.6 for both real drift and drawn drift, 1.1 for
   the crawler) -- neither separates by enough to lean on. What keeps a real bird out is what a real frame is: a
   sensor's pattern at every scale, temporal noise and a codec, under which flyer 1's bird, up to 175 grey levels,
   holds under 1 % of the whitened energy against 11 % at zero. The test's crawlers are drawn faint (30) on a
   Boson's noise (2 grey levels), and `still_again` finds nothing clear over their sky.
6. **The score.** Motion against the background is how fast *or* how far over the frames seen, whichever says
   more (`moved`: 3 px a frame, or 60 px in all -- the bird's 388 px in 18 s is motion); the path is the track's
   extent (a bounding box's diagonal) rather than its first point to its last, taken afresh after the fold from
   all a row was lent (before, a row lent 900 frames kept the path of its best 130-frame piece, and PR144's
   wandering track lost a quarter of its score to end-to-end). **The evidence stays the chain's own points**
   (`Proposal.seen`): the committed code scored once, before the fold, so frames a piece was lent never counted;
   scored again after it, a three-frame piece on PR113 348-471 lent six frames went from 0.54 to 2.16 and above
   the transit (job 1262, then run on the committed code to see it had always been 0.54).
7. **A proposal's marks keep off the detector's edge band** (`seeds`): 70 px in where it can, else 15 px in --
   the band the smallest spot detector closes -- before falling back to wherever the thing was. B's first offered
   mark was at x = 627, 13 px from the right edge; the link found nothing under it and linked nothing (its
   message named the mark and said what to do; `--unset object@786` and it linked).
8. **A piece lends a row its frames only if it lies on it for four frames or more, or runs at its speed**
   (`_fold`). A piece lends *every* frame it has, not only the shared ones, and once the path was taken from all a
   row was lent, a ten-frame row of terrain under PR113's pan took a chain that ran along its line through its two
   or three shared frames at another speed, had an extent of 488 px from it, and went above the transit with
   three others (6th of 114 on the final-code check, job 1260). At the row's speed alone was too strict: PR144's
   object turns, and its pieces run at different speeds while lying on one another for forty frames
   (`test_the_object_is_proposed_with_no_marks_to_go_on` holds that fold, 2-199). With either the transit is 1st
   again on 380-440 (1.10, next 0.60), and flyer 1's birds, whose 130-frame pieces overlap by forty, assemble as
   before.
9. **Words.** A crawler is said in tenths: "moves 0.4 pixels each frame against the background, 388 in all".

**Find now** (`look --n0 1 --n1 1705 --propose --more` on the final code, 4:19 on 4 CPUs; the sheet is
`/scratch/mcdonald/flyer1/flyer1_…_look_proposals_1_1705.png`, the earlier runs' under `before/`, `run2/` …
`run6/`): five rows, and the four things are the first four --
1. **A strong 13.1** (frames 638-1701, seen in 1023, 0.4 px a frame, 383 in all; 1.3 px from the paper's track),
2. **D fair 7.2** (1645-1703), 3. **B weak 3.2** (786-1702, seen in 874, 0.2 px a frame, 201 in all; "more like an
edge or a line than a spot" -- its `background_all_round` is 0.15-0.36, the measure's floor for a spot this faint,
not a finding), 4. **C weak 2.7** (1220-1227, 56 px a frame), 5. a three-frame piece of C at 0.0. The default list
is the best three and anything within a quarter of the best (3.3): A, D and B are on it, C is under "Show more"
(`--more`), 0.6 below the line. Before the last round of changes (job 1253, the still peaks still mixed in) the
same four led at 24.5 / 15.3 / 6.3 / 1.8 with six trail pieces after them; the scores moved because a still row's
`stands_out` is now measured among the still pass's own peaks. About 4 minutes on 4 CPUs, against 1:34 on 8 before
the change: the still pass doubles the residual work on a still scene.

**Taken and linked**, each into its own case folder (`/scratch/mcdonald/flyer1/{A,B,C,D}/`, `accept.sh`: the
`to_accept` commands with my own `--why` after looking at the strips): A 1063 of 1064 frames, 642-1705, as a
5 px bright spot, within 0.7 px of all 10 marks (`--n0 600`; the default range stops 30 frames before the first
mark); D 63 of 64, 1642-1705; C 13 of 13, 1215-1227, held as a spot (not by its motion, as PR43 was); B nothing
at the first try (item 5 above), then 846 of 846, 860-1705, within 1.2 px of 9 marks. Every strip looked at:
each track sits on its thing in every tile.

**Measured** (`mcdonald run --marks`, job 1257, four case reports `<dir>/<tag>_case.md`, the track sheets looked
at and the reports written again with `--i-looked`): **A beats at 3.36 Hz -- the paper's 3.36 Hz for flyer 1 to
the hundredth** -- 16 % of its brightness, 322 times the band, over the whole track 642-1705, 32 of 64 windows
passing, "clear of the codec's rhythm and not shared by the background beside it"; the bottom line says "Its
brightness beats at 3.4 Hz: the object's own, not the video's"; it moves 17 px/s, not uniformly (it slows to a
stop at the end, as the paper's track does). B moves 12.6 px/s, uniformly, at 275 deg (leftward), and **no beat
is found**: its strongest, 5.6 Hz at 11 % of its brightness, does not reach 3 times what the background beside it
does (6.8 %) -- B is faint (SNR 22 to A's 53) and runs 18-38 px from the top edge; honest, not a finding either
way. D moves 236 px/s (3.9 px/frame) with no beat in its 1.1 s (resolution 0.94 Hz); C 3203 px/s in the image,
too few frames for a beat. A took 974 s on 4 CPUs, B 901 (layers, a second a frame pair); D 106, C 85.

**Held against every recorded track** (`tools/find_rank.py --link` from a snapshot of the final code, Slurm job 1269,
8 CPUs, 55 min; `/scratch/mcdonald/flyer1/snapshot/logs/find_rank_1269.out`). Every PURSUE case at its recorded
rank and its recorded link; the one score that moved, PR144's, moved up with the path as extent:

| case | the recorded object on Find's list | its link from Find's marks |
|---|---|---|
| PR149 1-120 | 1 of 155, strong 19.95 (next 3.64), 0.5 px | 70 frames 16-96, 41 shared at 0.2 px, 1 off (as recorded) |
| PR144 300-500 | 1 of 400, strong **41.10** (was 28.61; next 1.38), 0.4 px | 199 frames 300-500, 0.0 px, 0 off (as recorded) |
| PR142 130-290 | 1 of 121, strong 21.10 (next 0.58), 1.4 px | 103 frames 157-259, 0.9 px, 8 off (as recorded) |
| PR148 140-440 | 1 of 400, strong 16.15 (next 7.06), 1.2 px | 176 frames 142-325, 0.5 px, 1 off (as recorded) |
| PR113 380-440 | 1 of 121, weak 1.10 (next 0.60), 3.1 px | 4 of 4, 408-411, 0.0 px (as recorded) |
| PR113 348-471 | 1 of 254, weak 1.10 (next 0.55), 3.1 px | the same |
| PR055 957-1418 | 1 of 400, strong 11.83 (next 1.45), 1.3 px | 142 frames 1157-1298, 0.7 px, 0 off (as recorded) |
| PR055 1007-1418 | 1 of 364, strong 11.83 (next 1.46), 1.4 px | the same |
| PR055 90-350 | 1 of 219, fair 7.98 (next 3.35), 12.0 px (a 74 px disc) | nothing, the closest spot 18 px at 21 px (as recorded: SIZES stop at 71) |
| **flyer1 1-1705** | **1 of 5, strong 13.14** (next 7.22), on 885 of the paper's 925 frames at 1.3 px | **1071 frames 634-1705, 1.3 px on the 925 they share, 0 off** |
| **flyer5 1-857** | **1 of 1, strong 10.24**, on 110 of 123 at 2.7 px | **353 frames 369-721, 2.9 px, 0 off** (Jacob's own GUI run of 2026-09-29: 369-721, 2.9 px) |

Three earlier full runs on intermediate code are the record of what each rule cost before it was settled (jobs
1254: PR149 halved and 5 link frames off; 1258: PR113 380-440 5th and 348-471 5th; 1262: 348-471 2nd), and the
committed code was run on PR113 348-471 by hand (`debug/pr113_old.py`) to see that the row above the transit had
always scored 0.54 there. `find_rank` has the two Galileo cases (`MCDONALD_GALILEO` is the clips' folder,
`~/research/uap/zenodo_pr135/galileo_dalek_clips` by default; the paper's tracks in clip frames; a case whose
clip is missing is skipped and said), and a job needs `MCDONALD_CATALOG` and `MCDONALD_HOME` exported and to be
run from a snapshot (`rsync src tools tests/golden`, `PYTHONPATH=snap/src`), so that the working tree can move
while it runs -- the pools are forkserver processes and an edited `propose.py` would reach them.

**Suites** (job 1270, the final code, 4 CPUs, 8 min): measurement **235** (+12, the crawler test), reduction 166,
published 32, cli 82, gui 495 + the WxAgg skip, golden 19 -- all pass.

**Left, and known.** C stays behind "Show more" on the whole clip (its trail counts as its company; its 8 frames
are weak evidence by the score's own standard, and it is second on a part of the clip that has only it). The
still pass is blind for the half second at each end of the frames searched, since it needs frames that far
either side. The window's Find text is unchanged (Jacob's words); the technical README's Find paragraph says the
pass. `stands_out` for B is 1.0 -- among two birds and little else, the fainter is "typical" -- which is the
measure's floor, not a finding. Not released: 0.2.12 is on PyPI; this is a 0.2.13 candidate for Jacob's word.
The frames (1705, 0.2 GB) are in `/scratch/mcdonald/frames/flyer1_...`, the case folders as above, the truth
pass and diagnostics in `/scratch/mcdonald/flyer1/{truth,debug}/`.

## 0.2.12 released; Ravi's first report from the Mac (2026-09-29)

Jacob: "Sure go ahead, and then I will test and report back. Also, Ravi was able to install mcdonald on
macOS and launch the GUI. He sent a screenshot that I put in correspondence/."

**Ravi's screenshot** (`/hugespace/local/research/uap/correspondence/Screenshot 2026-09-28 at 2.54.21 PM.png`,
2996 x 1774, a Retina Mac): the window titled "mcdonald — pr144", PR144 open at frame 130 of a 5.8-s
part, the proposal's path drawn through six marks, Find's card "6 marks on the object, chosen from what
Find showed", Follow's "Track checked: on the object", and Measure running -- "Step 9 of 11 · Groups — 70
of 70 · 0:34 elapsed" -- saving to `/Users/rkoppara/Documents/mcdonald/pr144`. So on a Mac, by a person:
pip install, the window, a catalog video, Find, This is it, the follow, the check, Measure, the storage
folder under Documents; the transport icons drawn, the panel of steps and the timeline as here. Nothing
in the picture to fix. Not yet seen from him: the report page, the Retina sharpness of Find's strips,
Gatekeeper's prompts, the ⌘ keys.

**Released: v0.2.12 on PyPI, 2026-09-29** -- `4a6bbe3`, tagged and pushed at 11:47, uploaded 2026-09-29T15:48:25 UTC; the five suites on the release tree (job 1250) and golden on the same code (job 1248) all pass. Checked from a fresh venv (`/scratch/mcdonald/venv-0.2.12`): `pip install mcdonald==0.2.12` gives 0.2.12, source "pypi", and `mcdonald setup --offline --no-desktop` says Ready, the menu entry untouched this time. It carries the two flyer-5 changes: the beat looked
for in windows along the track and named by its fundamental, and the beat in the report's summary and
bottom line. Jacob tests next and reports back.

## From Jacob's flyer 5 run: the wingbeat, in a window, by its fundamental (2026-09-29)

Jacob: "I just tested the GUI on flyer5. It found, followed, and measured, but it did not find a beat
frequency of birds. This is one of the bird control images." Flyer 5 is one of the five Galileo
Project Dalek IR bird clips of the PR135 paper's Fig. 3 (`~/research/uap/zenodo_pr135/galileo_dalek_clips/`,
640 x 512, 60 fps, HEVC stream copies of the source; the paper's per-frame track and its beat, 3.90 Hz
with the double at 7.80, over source frames 52322-52456 = clip frames 602-736). His save is
`/scratch/mcdonald/flyer5_2026-02-05t15_00_02.697z-…/`: Find's one proposal, followed as a 5-px bright
spot 369-721 (353 frames), the same bird as the paper's track to 2.9 px median, Measure through every
stage. Two things were wrong, neither the photometry:

1. **The report hid the beat.** The stage had found one -- "it beats at 5.11 Hz, 7 % of its brightness,
   clear of the codec's rhythm and not shared by the background beside it" -- but the report kept it
   under the folded Measurements; the summary table and the bottom line said nothing of it, so the
   report read as no beat. Now the summary's last row (after the Technical Note's variables) is
   "brightness beat, f_b", with the frequency, its double, the frames, and that a wingbeat, a tumbling
   body and a blinking light all beat; a stage that found none puts its reason there; and the bottom
   line says "Its brightness beats at 3.9 Hz (and at 7.9 Hz, its double): the object's own, not the
   video's." test_reduction holds all three.
2. **5.11 Hz was between the paper's two.** One spectrum over the whole 5.9-s track -- a faint approach
   (brightness 1,200) and then two seconds of bright flapping (5,200) at a rate that changes -- smears
   into a peak between the harmonics; over the paper's frames the same curve gives 7.88 and 3.94. The
   stage now looks for the beat in 2-s windows along the track as well (`flicker.windows`, an eighth of
   a window apart, the last window always), each held to the same tests (3 x the background apertures'
   own beat in the window, not shared at that frequency, not at a codec line), takes the clearest that
   passes where it is clearer than the whole track, and names a harmonic pair by its fundamental
   (`flicker.harmonics`: a peak at half the strongest at least half as strong makes the strongest the
   double -- a wingbeat's brightness changes twice a stroke, so the second harmonic is often the stronger
   peak). Flyer 5 on the window's own track: **3.94 Hz and its double 7.88, 9.7 %, 399 x the band, over
   frames 602-721, 11 of 17 windows beating at 3.94-3.97 Hz**; on the paper's track (golden, new):
   3.92 and 7.84. The ends where the aperture leaves the frame are trimmed rather than refused (the
   paper's track runs to the frame's top; `trimmed`). PR135's members and the drawn 8-Hz dot are
   reported from the whole track as before, with no double named; a drawn bird (`_Flyer`: faint then
   bright, the double stronger, the rate settling 4.8 -> 3.9 Hz) reads 3.92 and its double from a
   window over the flapping.

His case run again through `run` on the same frames and track (job 1249, `/scratch/mcdonald/layers-ab/flyer5/run/`): the summary's row "brightness beat, f_b: 3.9 Hz (and 7.9 Hz, its double), the object's own, over frames 602-721" and the bottom line's sentence. All six suites pass (job 1248): measurement 223 (+4), reduction 166 (+3), published 32, cli 82, gui 495, golden 19 (+2, flyer 5 on the paper's track: 3.92 and 7.84). Committed, not pushed and not released: Jacob's word for 0.2.12. The other four flyers (3.36, 4.49, 10.04 and 3.85/7.69 Hz in the paper's table) are there to
try next; flyer 3's 10 Hz is above the 7.5-Hz Nyquist of a 15-fps clip but well under 30 at 60 fps.

## 0.2.11 released, after Jacob's PR43 run (2026-09-27, evening)

Jacob: "PR43 works great. Take a look if you want, and then go ahead and make the next release." His
save (`/scratch/mcdonald/pr43/`, 17:04-17:07): the track followed by motion, 26 rows 50-75, "distance
from each mark -- 57: 1.4 px, 71: 0.3 px"; then Measure through every stage -- layers, symbology's
north file, the size-speed and track-frame figures, the case -- with the report's first row "pixel
velocity 20.3 px/frame (609 px/s), fitted to 25 points of the track against wall-clock time; the motion
is not uniform, so this does not describe it" (28.67 px = 5.8 % of span) and the bottom line saying the
same: the tool's honest answer for a thing that speeds up across the frame. Nothing to fix from it.

Meanwhile another session of the same day put a Sponsor button and a Support section in the README
(`.github/FUNDING.yml`; donations through Project Janus at Blue Marble Space) and the same in Help ->
About (`cd193f0`, `7dbf001`), and pushed main -- so every commit of the two nights was on origin
before the release. The five suites were run again on the release tree (job 1247: measurement 219,
reduction 163, published 32, cli 82, gui 495; golden 17 on the same code, job 1245).

**Released: v0.2.11 on PyPI, 2026-09-27** (`6df3622`; `__version__`, `__released__`, both READMEs'
status lines -- the short one now says Windows has been tried so far only by its automatic tests;
`git push origin main v0.2.11`). On PyPI 53 s after the tag (uploaded 22:56:58 UTC). Checked from a fresh venv (`/scratch/mcdonald/venv-0.2.11`, Python 3.14): `pip install mcdonald==0.2.11` gives 0.2.11, source "pypi", both commands, the 144-video catalog and the four documents in the wheel, and `mcdonald setup --offline` says Ready. (That setup, run without `--no-desktop`, rewrote the applications-menu entry to the venv's launcher; it was put back at once by `python3 -m mcdonald.cli setup --offline` from the working copy -- Exec is `~/.local/bin/mcdonald-gui` again. Next time: `--no-desktop`, or XDG_DATA_HOME at a temporary folder, as test_cli does.) It carries everything since 0.2.10: the follow by motion,
the 71-px size and the mark gate, the range ratio, integrity's kept frame, the float64 ZNCC norm and
the shared second-pass windows, UTF-8 everywhere and the download sentence, Show in video without the
note, the donations link. Every tester's window offers it within a day; Ravi's report on 0.2.10 is
still the next thing to wait for, and Gary after him.

## From Jacob's PR43 run: Follow finds nothing on a thing drawn out into a line (2026-09-27)

Jacob: "no luck on Follow it, although Find seemed to work. I saved so you can see" -- the follower's
sentence: "No spot size from 5 to 71 pixels puts a spot within 6 pixels of the marks ... (the closest
was 61 pixels away, at 5 pixels, bright). Neither the first mark nor the last has a spot near it."
His save is `/scratch/mcdonald/pr43/` (his storage folder here is `/scratch/mcdonald`): two marks,
proposed, frames 57 and 71, from Find's first proposal -- "bright, about 7 pixels wide; frames 57-74
(seen in 16); moves 17 pixels each frame against the background; more like an edge or a line than a
spot". PR43 is a thermal aerial view of ground with a river and a compound (88 frames, release 01).

What is there (`/scratch/mcdonald/layers-ab/pr43/`: `scene.png`, `change.png`, `path_crops.png`,
Find's strip under `find/`): the largest frame-to-frame change in the clip is a dotted streak running
down-right from about (940, 760) to the bottom edge -- one dot a frame, about 20 px apart -- and the
proposal's path lies along it. So Find was right; the thing is real and fast. In the frames it is a
short bright dash, drawn out along its motion: the exposure smears it. The follower's spot detector,
a disc against its surround, has nothing spot-like there: at the object's own position (from the
change map, to a few px) the nearest spot at 5 px is 10 px away and 465th of 701, at 9 px 31 px away,
and at 15 px and above nothing within 100 px, on frame 57 and on 71 alike. A line-shaped filter along
the motion (6 x 1.3 and 9 x 1.5 px) does no better: the streak ranks 87th to 425th among about 2,000
line-like peaks of the ground's own rocks and ridges on each frame. Only its motion separates it from
the ground -- which is what Find uses and the follower does not.

Done now: the window says so first, before the follower's sentence, when every mark came from a
proposal that Find itself called "more like an edge or a line than a spot" (`QtMarker._streak_reason`):
"What Find found is drawn out into a line, not a spot -- it moves fast enough to smear along its path --
and the follower looks for spots, so it cannot hold this one yet." test_gui holds it, and that a hand
mark among the marks leaves the follower's own sentence alone. test_gui 495, all pass (Slurm job 1241).

**Then Jacob: "Sure, see if you can improve the tool to work on PR43!" -- done, the same day: a follow by
motion** (`autolink.follow_by_motion`, `_Motion`), the link's second way, taken when no spot size holds
the marks. The motion image of a frame is the frame less the median of its four neighbours brought onto
its background (`propose.onto`; a repeated neighbour left out by `forensics.repeats`' rule): bright only
where a thing is in that frame and in none of theirs, whatever their smears overlap -- the two-sided
difference tried first vanished where consecutive dashes overlap, and one-sided differences show the
neighbours' ghosts. Every mark must have motion within 12 px of it -- a click's error on a dash; Find's marks sat 1-3 px
from it here -- there must be two marks, and the thing must move at least its own width a frame (a
slow wide disc's motion is only its rim, a radius off: the spot link from centre marks is its way);
else the link declines and the sentence says which mark has no motion near it, or that the thing is
too slow for its width, before "Nothing was linked". The polarity is whichever answers more strongly
at the marks, and from each mark both
ways the peak nearest the prediction (a step-sized window, 1.2 steps, so a repeated frame or a double
step is inside it) is taken while it is at least 5 x the noise and a quarter of the object's own median
peak (the like gate: a static flicker at 6 x lured a first draft off the track); two misses in a row
and the pass ends. The marks' own frames keep their re-centred positions, a frame two passes reach
takes the stronger, `source` is `motion` throughout, `size` a nominal width (1.5 x the blob's), and
the summary starts "followed by its motion, not as a spot". `write_track_csv` says how in its header.
PR43 from Find's two marks (job 1242, 84 s): **25 of 26 frames, 50-75, a bright thing about 8 px
wide, within 1.4 px of both marks, the pass from one mark arriving 0.3 px from the next**; the strip
shows the dash centred in every cell; 609 px/s by a straight line with 20 px rms -- the motion is not
uniform across the frame, which kinematics says. Held by test_measurement (`StreakClip`: a dash 16 x
3 px crossing 20 px a frame over ground full of specks, marks 8-10 px off it: 22 of 22 frames to the
dash's centre, the header, and a disc still linked as a spot without this way) and by golden's new
PR43 case (the frames, the dash at 65 to 4 px, both marks to 3 px, 22 px a frame between them).
docs/agents.md and docs/method.md say what the second way is. All six suites pass on the final code (job 1245): measurement 219 (+7), reduction 162, published 32, cli 82, gui 495, golden 17 (+5, PR43: 25 frames 50-75, the dash at 65 to 4 px, both marks to 3 px, 22.0 px a frame between them). The recorded tracks (job 1243): the eight recorded cases link line for line as the table of 2026-09-23 has them -- they never reach the second way. The enlarged PR055 part shows why the entry rules matter: under a first draft's 40-px reach with no width rule it was "followed" 171 frames 44 px from the record, wild steps of 106 px; under the final rules (job 1246) it is declined -- "the marks on frames 187, 213, 224, 246, 257, 293, 315 have no motion within 12 pixels" -- and nothing is linked, as before.

## From Jacob's PR43 run: Show in video without the note (2026-09-27)

Jacob, testing PR43: "after Find the Object, if I click 'Show in video' then the popup covers almost
the entire track and area of interest. I don't think we need the popup." The popup was the note
(the toast over the foot of the video since the polish) that said what the dashed line was and that
it was not a mark until chosen -- two sentences that, on a laptop's video area, covered the very path
they described. `QtMarker.show_proposal` sets no note now and clears any that is showing, so the video
is bare but for the dashed path; the button's tip still says what it does. test_gui: Show goes to
where the path starts, draws it, places nothing, and no note covers the video. test_gui 493, all pass (Slurm job 1239).

## The gate at the marks grows with the spot size (2026-09-27, later in the morning)

What the 71-px size showed (the section below): the enlarged PR055 copy was stopped not by the size
list but by the link's gate at the marks, 6 px whatever the spot size, while Find's mark on the
74-px disc was 13 px from its centre. `autolink.mark_gate(size, tol)`: 6 px for spots up to 30 px,
a fifth of the size above it (6.2 at 31, 9 at 45, 14.2 at 71). It is used wherever the 6 px was: the
size sweep's qualification and its strongest-spot response, the "no spot near it at any size"
diagnosis and its sentence, `object_response` at the chosen size, and a link's `concerns` about a
track that runs past a mark. The recorded clips' objects are 7-24 px, under the knee, and the sweep
only reaches a large size by climbing through the small ones, so they should not move -- the rule
Jacob set for the size applies to this too, and the same gate run held it: job 1233, every one of the eight recorded cases links exactly as the table has it. And the enlarged copy still does not: on frame 327 the recorded centre is (1365.5, 453.0), the 71-px detector's spot (1353.7, 447.5) is 13 px left of it, and Find's mark (1335.0, 443.0) 32 px left of it -- a third of the disc's width; mark and spot are 19 px apart, outside 14.2, and at 45 px the spot is 10 px from the mark, outside 9. The last of Find's marks is the poor one, as the tool's own sentence says ("the mark on frame 327 is the one with no spot near it"). **From marks on the disc's centre it links**: ten of the recorded track's own entries between frames 210 and 329, `mcdonald mark PR055 --n0 90 --n1 350 --set ... --link --no-window` (job 1238): **155 of 155 frames, 179-333, dark spots 71 px wide, the track within 18 px of all ten marks** (the 71-px spot sits about 13 px from the disc's centre throughout). So the size and the gate together do what Jacob asked, for a hand that marks the disc; Find's own marks on this case do not link because its first and last are off the object (187: 130 px from the record; 327: 32 px), and the tool names the mark to redo. Two earlier tries taught the same: marks at the record's ends (97 and 343, the disc at the frame's edge) or interpolated across frames the record does not cover do not qualify either -- the sweep judges the first and last marks. The runs are in `/scratch/mcdonald/layers-ab/link327/`. test_measurement
holds the gate's values; all six suites pass on this code (job 1234, but for a float comparison in
the new test itself, fixed and rerun: job 1235, 212 pass).

## The decisions answered, and what they set going (2026-09-27, morning)

Jacob: "I don't understand the decisions, can you prompt me and then start on those plus integrity?"
Asked in plain words, four questions; his answers, and what was done on each:

1. **Spot size 71 px for the link: yes, "if the recorded clips hold".** `autolink.SIZES` is
   (5, 9, 15, 21, 31, 45, 71). The gate is the recorded-track run from the kept seeds,
   `tools/find_rank.sbatch --link --seeds <linkgate-20260922/keep> --keep <keep-sizes71>`
   (Slurm job 1231, from `/scratch/mcdonald/replay-cases/`, frames in `/scratch/mcdonald/find-rank`):
   every recorded case must link as the table of 2026-09-23 has it, and PR055 90-350 -- the
   three-times-enlarged copy, a 74-px disc that linked with nothing up to 45 -- may now link. **The gate held** (job 1231, 45 min): every one of the eight recorded cases links exactly as the table has it -- PR149 70 frames, 1 off; PR144 199, 0.0 px; PR142 103, 8 off; PR148 176, 0.5 px; PR113 4 frames both windows; PR055 142 frames both windows -- so 71 stays. **But the enlarged copy still does not link**, and the size was not what stopped it: "no spot size from 5 to 71 pixels puts a spot within 6 pixels of the marks (the closest was 10 pixels away, at 45 pixels); the mark on frame 327 is the one with no spot near it." Find's mark on a 74-px disc sits 13 px from its centre, and the link's gate at the marks is 6 px whatever the size -- right for a 9-px spot, a sixth of the width for this one. The next step, under the same rule (the recorded clips must hold): a gate that grows with the size.
2. **The range ratio: add the field.** One row of `stages.KNOWN` after the reference object's
   length -- "range ratio R_obj / R_ref" in the form, `--range-ratio` on `run` -- carried in the
   kinematics `ref` and its fields; the stage's line says "at 2 times the reference's range (the
   range ratio given)" where it said "a ceiling", the Reduction's scale-bar line likewise, and the
   report's row shows the speed with "at R_obj/R_ref = 2 (given)" where it showed "× R_obj/R_ref"
   for the reader to apply -- which it still does when the ratio is not given. The form is fourteen
   fields; test_gui's check that the form has a field for every KNOWN row covers it, test_reduction
   holds the row, the scaling, the line and both forms of the report's row.
3. **Groups, flicker and symbology stay in every Measure.** Nothing changed.
4. **The four window conventions stay** (the 900-frame question even with the frames on disk; the
   six-across sheet in its own window; an unanswered sheet is no; the window's words, the default
   ranges, the link's numbers and `run`'s extra options). Under Decisions below, every *not asked*
   item is now confirmed.

And **integrity's kept frame** (the audit's §4.4, exact): `integrity._frame` keeps the last frame's
grey, mask and band-passed array for the next pair, whose first frame it is (a worker gets eight pairs
in a row): three PR113 pairs 3.73 -> 2.62 s single-process, the same arrays, held by a drawn test
(three pairs cold and warm identical, the drift read to 0.01 px). All six suites pass on this code, the 71-px size included (Slurm job 1232): measurement 210 (+1), reduction 162 (+4), published 32, cli 82, gui 493 + the WxAgg skip, golden 12 -- PR113 141.4 px/frame from two clicks still chooses its size right with 71 on offer, PR144 599.379 / 500.254 / 99.1534.

## The audit's §5.2 and §5.4, done (2026-09-26, later that night)

Jacob: "don't worry about a new release yet, but let's keep going with the two audit findings."
Both done, one commit; the record with every number is the audit's §0 ("The registration's two
decisions"). In short: **§5.2** -- `shift_field` normalises the ZNCC from float64 summed-area tables
of the whole frame (`forensics.integral`, `box_of`; `zncc(norm=)`). The float32 cumulative sums
over the 618-px search window reach 2.6 × 10⁷ on PR113's sky, where a float32 step is 2, so a flat
patch's sum of squares came out as 0 or 2.3 for a truth of 1.7 or 1.3, and sky "correlated" at
13.66 at shifts anywhere in the reach -- 98 "good" rows of 165 on pair 400/405 that agreed on
nothing; now 16, peaks 0.999, the zero consensus from 25 templates where 9 were. PR144's textured
pair: 153 of 160 shifts identical, the consensus identical. **§5.4** -- a held-still pair's second
pass is one 30-frame window shared by the pairs nearest it (`layers.window_start`, every L/2
frames), measured in a second round on the same pool ("Layers again"): 4 windows on PR113 380-440
where 21 pairs each had one; `layers` 6:22 -> 2:38 there, 8:45 -> 2:47 on PR135's slow scene,
the same held-still shares and verdicts; PR144 (no still pairs) 9:58 -> 8:08 from §5.2's box sums.
The whole `run` on PR113: the case report and the integrity report identical to the word, 3:40 ->
3:16. Before/after runs, the A/B pair scripts and their rows: `/scratch/mcdonald/layers-ab/`; the
committed source they ran against: `/scratch/mcdonald/before-390e73f/`. Not done, still on the
list: integrity's per-worker cache of the last filtered frame (stage 5, item 15). Held, on the final code: Slurm job 1230, 4 CPUs -- measurement 209 (+7: the float64 sums, the trap drawn, the shared windows), reduction 158, published 32, cli 82, gui 493 + the WxAgg skip, golden 12 (PR113 141.4 px/frame from two clicks; PR144 300-500 sea 599.379, cloud tops 500.254, layer against layer 99.1534, ratio 6.0168, group gap 97.22) -- all pass.

## Stage 1 of the roadmap, done while Ravi tries 0.2.10 (2026-09-26, night)

Jacob: "Let's work on everything that we can until we hear back from Ravi." That is stage 1
of the roadmap below, the four items that need no one's word. Each, and what holds it:

1. **The Mac at the rig's own deadlines.** `MCDONALD_TEST_PATIENCE` is out of the Mac job
   (`5f94728`). Run 8, 0.2.10 at 1x: test_gui **42 s** against 842 s with the multiplier, every
   timing check passing; the one failure was a size check that asked for 1040 x 700 on the
   runner's 1024 x 677 screen. Then two more checks met the runner on a slower run (10: test_gui
   73 s): '.' and '>' lost, the window not yet active when the key was pressed. The rig now
   resizes to what fits the screen, gives the window ten seconds to become active (three
   before) and says in the log when it did not, and its pixels-on-screen check waits for the
   draw. Run 12, the rig so
   fixed: **all five suites pass on the Mac at 1x** -- reduction 158, published 21 (+4 skipped:
   no recorded tracks there), cli 79, measurement 202, gui 438 + the GTK and wx skips; test_gui
   68 s. One more met the small screen after that: the ruler check allowed 1.5 px on a drag
   sent as whole view pixels, which at that screen's scale land 2 px from the nominal frame
   points; it now expects the length of the drag the view received, to 0.1 px. Run 15, the final commit: all five pass again (gui 438, 64 s). Runs 8-15 are all in
   `logs/` on the `ci-logs` branch, as before.
2. **A download that cannot start says why** (`storage.Unreachable`, `certificate_fix`,
   `why_unreachable`): the certificate sentence for python.org's Python on a Mac, "could not
   reach DVIDS (...)" with the reason, or the HTTP answer, inside `clip.resolve`'s sentence for
   both shells, where urllib's "<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] ...>" was;
   `mcdonald setup` says the same sentence from the same place. A connection lost part way is
   `Incomplete`. (The roadmap's item 2 overstated the old behaviour; corrected there.)
3. **Windows, read first and then run on GitHub's runner.** Read: every text file the package
   writes or reads went through the platform's default encoding, cp1252 on Windows -- and the
   shipped catalog does not decode under cp1252 at all (byte 0x9d at position 1187), so the
   first screen and every catalog name would have failed there; the case report has θ and →,
   so `run` would have failed writing it. Every text open names UTF-8 now (the catalog
   utf-8-sig with errors replaced), ffmpeg's output is decoded as UTF-8, and the commands print
   UTF-8 on every stream (`cli.utf8_streams`) so that a pipe on Windows never stops a command
   over an arrow. test_reduction holds the files under the C locale (ASCII); test_cli pipes
   --help through an ASCII stream. The `windows` job in `platforms.yml` (windows-latest, Git's
   bash, ffmpeg from Chocolatey, the five suites; `git push -f origin HEAD:windows-ci` runs it
   alone, macos-ci the Mac's alone). Run 9 (Windows Server 2025, 4 CPUs): **`mcdonald setup`
   Ready** -- Python 3.12.10, ffmpeg 9.0.2, PySide6 6.11.2, storage in Documents, the catalog's
   144 videos, DVIDS answering -- and **test_reduction 158 of 158 in 26 s**; then the job's own
   script stopped it (a grep for FAIL/SKIP lines that found none, under the runner's
   exit-on-error shell; both jobs tolerate that now). Run 11, the script fixed: every suite
   ran through -- reduction 158, published 21 + 4, measurement 202, all pass; test_cli stopped at
   its 51st check reading the case report with the platform default (the suites' own reads), and
   test_gui had 2 of 388 wrong: the case label shows the case folder resolved, and Windows' temp
   folder is `RUNNER~1` unresolved; a dropped file's path came back from Qt as `C:/x/y`. The
   suites read and write UTF-8 themselves now (47 places), the label check resolves too, and
   `_dropped` gives the platform's own form (`str(Path(...))`). **Run 13: all five suites pass on
   Windows** -- reduction 158, published 21 + 4, cli 79, measurement 202, gui 388 + the GTK and wx
   skips; 4 min 25 s of suites. What differs there is known and small: the pools start by spawn
   (a Measure's pools about 20 s slower, the audit's §5.3), and test_gui runs 388 checks against
   493 here (the Linux-only ones: the menu entry, Xvfb, the backends). docs/install.md's note
   says both platforms have been run by GitHub's machines, not yet by a person.
4. **The replay cases are safe from the 30-day rule**: `keep_final` (with `final_rank_997.txt`)
   and the link-gate `keep` are copied, identical, to `/scratch/mcdonald/replay-cases/
   {leftovers-20260923,linkgate-20260922}/`; the originals under `/scratch/tmp/claude-1000` stay
   until the rule takes them (about 2026-10-22).

Suites on this machine, 4 CPUs (Slurm jobs 1218 and 1219, the second on the final code but for
the ruler line): measurement 202, reduction 158 (+7), published 32, cli 82 (+2), gui 493 (+1) + the
WxAgg skip -- all pass; test_gui again on the final code (job 1221): 493, the ruler at 50.2 px for a
drag of 50.2; golden (job 1220): 12, PR113 141.4 px/frame from two clicks, all pass. Nothing of
this session's is in `/tmp`; `/scratch/mcdonald/replay-cases/` is new (624 MB). Windows on the final commit (run 16): the
five suites pass again -- reduction 158, published 21 + 4, cli 79, measurement 202, gui 388 + 3 skips,
4 min 30 s of suites; and the Mac (run 15) the same.
The version is not raised; nothing is pushed to main. Ravi's word is still the gate for 0.2.11.

## Roadmap: the remaining scoped items, in order (2026-09-26, night)

Jacob: "Plan out a roadmap for completing the remaining scoped items." Everything scoped
since 2026-09-20 was read back against the code first (the audit's §5 and its "not done
by choice"; this file's "Next", its Decisions and every "not done"; the agent's triage
table), so that only what is still open is here. Already done and so left out: the
agent's items 7, 8, 10, 11, 20, 22, 23 and 9 (a)(c) went in the leftovers commit;
playing backward exists (Shift+Space); `mcdonald readme` is the README in the terminal;
the audit's rows 1-11 are 0.2.10; the report in plain words is dropped (his words). What
is left falls behind three gates -- a tester's report, Jacob's word, and the measurement
gates (golden, the recorded-track table) -- and the order below puts what needs no one's
word first.

**Stage 1 -- now, needing no one's word (one session; the Windows job is the long pole).**

1. **Done (the section above).** **The Mac on 0.2.10.** The last Mac run (7, `3f92568`) is older than the polish, so
   the test rig without `qWait` has never run there (test_gui 842 s at PATIENCE 3).
   `git push -f origin HEAD:macos-ci`; read `logs/8-*/suites/times.txt` on `ci-logs`.
   Then one more run from a macos-ci-only commit with `MCDONALD_TEST_PATIENCE` unset, and
   if test_gui passes, drop the line from the workflow (the audit's "retire it if it
   holds"; the knob itself stays, for a slow machine). Two runs of about 25 min; nothing
   on this machine.
2. **Done.** **A failed download says why.** `storage.download` lets urllib's error through, and
   `clip.resolve` puts it in its sentence for both shells: "X is not on this computer,
   and could not be downloaded from URL: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]
   certificate verify failed: unable to get local issuer certificate (_ssl.c:1000)>".
   (Corrected the same night: it was written above as a wrong sentence in the window and a
   traceback on the command line; neither is so -- the sentence is right, its tail is
   urllib's.) `setup` already has the fix (python.org's Python on a Mac: run "Install
   Certificates.command"; else `pip install --upgrade certifi`). Put it in one place
   (`storage`) and say it from both shells, in place of a `curl` fallback (a second
   downloader to keep; not worth it). Held by test_reduction with a `urlopen` that raises
   `SSLCertVerificationError`, and test_gui with an address that does not answer. An hour.
   Ravi, if on python.org's Python, meets this the first time he opens by catalog name.
3. **Done: the five suites pass there (run 13).** **Windows on GitHub's runner, before Gary.** A `windows-latest` job beside `suites` in
   `platforms.yml`: setup-python 3.12, ffmpeg (`choco install ffmpeg`; Chocolatey is on
   the image), `pip install ".[gui,dev]"`, `mcdonald setup`, the five suites on the
   runner's own desktop, logs to `ci-logs` by the same action; started the same way (a
   push to `macos-ci` runs both jobs; the branch's name is documented and stays). Expect
   what the Mac run gave, of the Windows kind: `shlex.quote` on backslash paths in
   `_flags` and the command lines the report prints; `%TEMP%` and the frames folder; the
   `.exe` console scripts and the update helper; `mcdonald setup`'s ffmpeg-on-PATH
   sentence; the pools under spawn with no preload (2.9 s a pool, about 8 pools a Measure
   -- the audit's §5.3 kept-alive pool is the fix, written only if the run shows it
   matters); test_gui's timing at whatever the runner is. Read install.md's Windows
   section against what the runner needed. A day, in 20-minute rounds; free minutes (the
   repository is public).
4. **Done.** **Keep the replay cases alive.** `keep_final` (2026-09-23 21:45, 373 MB), `keep5` and
   the link-gate `keep` are deleted 30 days untouched by the scratch tmpfiles rule
   (`~/.config/user-tmpfiles.d/claude-scratch.conf`) -- around 2026-10-22. Before then,
   copy `keep_final` and the link-gate `keep` (the seeds a detector change needs) under
   `/scratch/mcdonald/find-rank/`, outside the rule. Minutes; it protects stage 5.

**Stage 2 -- Ravi's report (gate: Jacob passes it on).**

5. **What only a real Mac hand can show**, in the order he meets them: Gatekeeper and the
   Documents-folder prompt; ⌘ keys and the menu roles; `QDesktopServices` opening the
   report's pictures and the folder; Retina -- Find's strips and the check's pictures are
   1x pixmaps with no `devicePixelRatio` (checked; the transport icons are drawn shapes
   now), so if he says the pictures look soft, that is the fix; the menu bar's "Python"
   (an app bundle's name: out of scope under decision 4; say so if he asks). Fix what he
   found, then
6. **Release 0.2.11**: items 2, 3's fixes and 5. `__version__` and `__released__`, both
   READMEs' status lines, `git push origin main v0.2.11`; every tester's window offers it
   within a day.

**Stage 3 -- Gary on Windows (gate: Jacob says; after Ravi, his order).**

7. Send install.md's Windows section and ask for the same three things: `mcdonald setup`'s
   output, whether `mcdonald-gui` opens, PR149 end to end -- or what broke, with the words
   on the screen.
8. From his first run: the kept-alive pool if the pools cost him minutes (audit §5.3); a
   Start-menu shortcut only if he asks (`setup` says the menu is Linux's); then a release.

**Stage 4 -- Jacob's decisions, in one message (any time after stage 1; each is small once answered).**

9. **Done, both (the section above).** The audit's §5.2 (the float64 ZNCC variance: more correct on flat-sky templates, not
   bit-identical) and §5.4 (layers' still-pair second pass: 70 % of layers on a still
   clip, 264 of 486 s on PR113 -- leave, or revisit the stride).
10. **Answered 2026-09-27: yes, behind the gate (the section above).** PR055's x3 copy: add 71 to `autolink.SIZES` (5, 9, 15, 21, 31, 45)? It changes what
    every link from marks chooses among.
11. **Answered 2026-09-27: added (the section above).** The Measure form: a range-ratio field (R_obj/R_ref; `kinematics.scale_bar_speed`
    takes it, the form assumes 1, a ceiling) on a form of thirteen fields already -- too
    many, and should the parallax two fold away?
12. **Answered 2026-09-27: all confirmed; the extra stages stay in every Measure.** The decisions marked *not asked* under Decisions, still his to confirm or reverse: a
    clip over 900 frames asked about even when all on disk; the window's vocabulary;
    Find's and Measure's default ranges; `run`'s `--names/--dark-below/--size/--dark`;
    the six-across sheet; an unanswered sheet is no; `groups`, `flicker` and `symbology`
    as stages of every run; the link's numbers (`LIKE` 0.5, `NEAR` 10, `TIGHT` 2,
    `STRONGER` 5 %, `END_GAP` 2); the track-sheet question as its own window; and the two
    left by choice, the report's white figures on the dark page and no bundled app.
13. **His own hand on 0.2.10**: recent videos and a dropped file, the toast, the window
    remembered; the report page's pictures and "I have looked at the track sheet now";
    the parallax fields; symbology in every Measure; PR149 with the ruler.

**Stage 5 -- the measurement work he picks (gate: stage 4; each held by golden and the recorded tracks).**

14. **Done (the section above).** **ZNCC in float64** (audit §4.5). A correctness change first: a baseline from the
    committed source, `layers` on PR113 380-440, PR144 300-500 and PR135 (the slow scene)
    before and after -- which template rows survive `good()`, the shift field, the
    held-still verdicts -- then golden; `integrity` shares `shift_field_auto`, so its
    numbers on the same clips too. Half a day and the jobs. Ship as a version.
15. **Done 2026-09-27.** **`integrity`'s per-worker cache of the last filtered frame** (audit §4.4: 0.3 s off
    each consecutive pair, exact). An hour, with 14; held by test_measurement and golden.
16. **Done 2026-09-27: 71 px, and the mark gate a fifth of the size above 30 px; both held by the recorded tracks; the enlarged copy links from marks on its centre (the sections above).** **`SIZES` + 71**: `tools/find_rank.py --replay --pick` on `keep_final` (a minute) says
    whether any recorded case's size choice moves, then golden, then the x3 copy by hand.
    An hour and the gates; a moved case is a decision, not a fix.
17. **Done another way: the stride stays, the window is shared (the section above).** **Layers' stride**, if revisit: time and hold on PR135 (the reason for the second
    pass) and PR113; PR135's report must say the same. A day.
18. **Done 2026-09-27.** **The range-ratio field**, if yes: one row in `stages.KNOWN` gives the form's field
    and `run --range-ratio` both; test_cli and test_gui compare the shells with `run`.
    Two hours.

Not on the roadmap, for the record: the case report in plain words (his words); a bundled
or signed app (decision 4, no money); frames as PNG and the FFT-bound registration (the
audit: right as they are). Throughout: a version with every release and a push only when
he says; the suites on every change (`tools/suites.sbatch`, 4 CPUs, niced), golden and
`find_rank --link` when measuring code moves; this file current at each session's end.


## An audit before the next release: the window, and where the time goes (2026-09-26)

Jacob, while Ravi tries 0.2.9: "please do an audit of the GUI and computational
efficiency for the next release. This should look and feel like modern software."
**The audit is `docs/audit-2026-09-26.md`**; nothing in the package was changed.
Every screen was opened on PR113 380-440 offscreen in a 4-CPU Slurm job (a laptop
stand-in), photographed and timed, the same clip went through `mcdonald run` with
every stage timed, and the functions the time goes to were profiled and, where a
faster way existed, prototyped and checked against the shipped function for
identical output. Pictures, logs and scripts: `/scratch/mcdonald/audit-2026-09-26/`.

What it found, in the order the audit would do it (its §1): six exact speedups --
static masks made three times a Measure and 12 of their 23 s in `mean(2)`/`max(2)`;
pool start-up 2.9 s a stage under Python 3.14's forkserver (a preload makes it
0.05 s); the spot detector by FFT (21 s a frame at 45 px -> 0.4 s, the same spots;
Follow 74 s -> ~15 s); grey and chroma by channel arithmetic (bit-identical,
5-15x); bandpass once a registration pair; `scipy.signal` off the window's import
(first screen 2.65 -> 1.23 s) -- then the window: a fixed 1500x920 that does not fit
a MacBook Air, Find and Measure taking half the window's height from the video,
the empty loupe, Find's strips cut on the GUI thread, geometry not remembered, no
drag-and-drop or recent list, the sheet window 1980 px wide, status-bar sentences
cut off. Measure's floor is the layers registration (315 of 640 s here; 70 % of it
the still-pair second pass from the PR135 fix), left alone. Decisions for Jacob are
its §5; nothing is done until he picks.

**Then, the same evening, Jacob: "Go ahead and do the six exact speedups, then run the
suites."** Done (the audit's §0 says what changed by file, and the numbers): on the 4-CPU
job, `mcdonald run` with integrity 640 -> 486 s, Find 102 -> 79 s, Follow 74 -> 7.9 s,
Measure to the sheet 72 -> 41 s, the window's import 2.1 -> 1.3 s, static masks 23 -> 13.5 s
and 2.6 -> 1.6 GB. Held by the suites (measurement 202, reduction 151, published 32, cli 80, gui 478 + the WxAgg skip, golden 12 -- all pass, Slurm jobs 1207 and 1208; the five suites in 9:36 where the last run before (job 1104, 2026-09-25) took 14:23, the pools' start-up being most of the difference), by `find_rank --link` on every case
(Slurm job 1205, 1 h 11 min on 4 CPUs: every row identical to the recorded table of 2026-09-23 -- PR149 1 of 138, strong 19.95, 70 frames linked, 40 on the track, 1 off; PR144 1 of 400, strong 28.61, 199 frames, 0.0 px, 0 off; PR142 1 of 119, strong 21.10, 103 frames, 8 off; PR148 1 of 400, strong 16.15, 176 frames 142-325, 0.5 px, 1 off; PR113 380-440 1 of 116 and 348-471 1 of 241, weak 1.10, 4 frames 408-411, 0.0 px; PR055 957-1418 1 of 400 and 1007-1418 1 of 338, strong 11.83, 142 frames 1157-1298, 0 off; PR055 90-350 1 of 213, fair 7.98 (next 2.78), and links nothing, the closest spot 10 px at 45 px, as before), and by a bit-for-bit comparison of the new and the committed code on real
PR113 frames (identical but for a few plateau-twin spots among the weakest; §0).
`progress.context()` is now the one place every pool is made (forkserver with the
worker modules preloaded; spawn on Windows), `run_case` takes `masks=`, and
`integrity.examine` takes `masks=` and `series=`. The version is not raised: that goes
with the push, when Jacob says the release is ready.

**And then: "Go ahead and finish the remaining items from the audit."** Done, the audit's §0
second part: the window fits the screen (1296 x 810 on a 1440 x 900 laptop) and remembers
its size, place and panel; the work area takes what Find or Measure needs and the video the
rest; Find says it is looking and shows no empty list; the loupe says what it is for; the
panel of steps has no title bar; the notes are a toast over the video's foot in place of the
status bar's cut-off sentences; Find's strips are cut on the search thread; the first screen
lists recent videos and takes a dropped file (the main window too) and never waits on the
update check; the track-sheet window fits the screen with its tiles sized to it and opens on
the track's row, the sheet's title fitting its width; the transport icons are drawn shapes;
the test rig no longer waits with qWait (test_gui 3:27 -> 1:47, 492 pass, 0 fail, the WxAgg skip, Slurm job 1214, 1:47). All six suites on the final code: measurement 202, reduction 151, published 32, cli 80, gui 492, golden 12, all pass, in 7:25 (job 1216). Pictures at
1440 x 900: `/scratch/mcdonald/audit-2026-09-26/shots_polish/`.

**Released: v0.2.10 on PyPI, 2026-09-26** ("raise, tag, and push!"): the three commits above, the version in
its three places (`__init__.py`, the two READMEs' status lines), `git push origin main v0.2.10`, on PyPI about
80 s after the tag. Every tester's window offers it within a day.

Two traps paid for on the way: **`QTest.qWait` holds the GIL** -- a thread got 0.04 M
loops/s under it against 7 M under `app.exec()` -- so a harness that waits with it
(test_gui's `settle`/`wait_for`, and the audit's first run) starves the very threads
it waits for; wait with `processEvents()` + `time.sleep(0.002)`. And **Python 3.14
starts pool workers by forkserver** (this machine): a script that uses the package's
pools needs the `if __name__ == "__main__":` guard or fails with "bootstrapping
phase"; the entry points and the test scripts have it. And a script fed to `python -`
(stdin) has no main file at all, so under forkserver its pool workers die at start and
the pool waits for ever -- run such checks from a file.

## The polish, begun: the first screen, downloads, one storage folder (2026-09-24)

Jacob is testing the window to make it as easy to use as possible, before Ravi.
Three things so far, each asked for and done:

- **The first screen** (`mark_qt.choose_start`) is titled "mcDonald UAP Toolkit"
  and says, in his words: "mcdonald measures the kinematics of an unknown object
  in a single-camera video" / "Start by opening a video by filename or by catalog
  name. (Current catalog includes all PURSUE cases.)" The old paragraph (it
  starts with you; Help -> Getting started) went. "kinematics" is on the
  plain-words test's list, but that test does not read this dialog; the word is
  his (`dd304d9`).
- **The PURSUE videos ship, and download when named.** `src/mcdonald/
  pursue_videos.csv` (130 kB, written by `tools/ship_catalog.py` from the mirror's
  records.csv): the 144 videos' title, release, blurb, the mirror's file name, a
  direct DVIDS file address and its size. It is the catalog when
  `MCDONALD_CATALOG` is unset (`catalog.ShippedCatalog`; `none` is no catalog; a
  records.csv still wins, and the window's remembered one too). A record whose
  file is not on the computer is downloaded by `clip.resolve` into
  `<storage>/videos/<mirror name>`, through a `.part`, and must come to the
  catalog's size: on a command line with progress on stderr, in the window after
  a question (size, where, room) and behind a progress bar with Cancel; no is
  `clip.Declined`, which the window treats as nothing happened. The 59 records
  that named a DVIDS page were resolved to the page's one .mp4; 18 are a few kB
  larger than the mirror's copies (container only: PR113's frames are the
  mirror's, bit for bit, by framemd5, and so are PR119's after a real download),
  and 9 (FBI-UAP-PR001-006, NASA-UAP-D023-025; yt-dlp downloads in the mirror)
  are other encodings: **a download of those is not the mirror's frames.**
- **One storage folder** (`mcdonald.storage`): `$MCDONALD_HOME`, else
  Documents/mcdonald, with `videos/` and `frames/`. **Frames are no longer in
  the temporary directory** (on Fedora, memory) -- the command line's too; `--
  workdir` still wins. The first screen shows it with the room free and a
  Change… (remembered as `storage` in QSettings, put in the environment by
  `mark_qt.use_remembered_storage` so the Measure run sees it, and it clears the
  remembered `cases`, so a video's results go there too). The command line's
  results stay in the working directory.

Tests: test_measurement's catalog test now sets `none` for "no catalog", and
three new ones (the list ships; a download is whole or nothing, declined or
stopped; frames in the storage folder); test_gui's getting-in drives Change…
and a download said no and yes to (a file:// address); test_cli puts
`MCDONALD_HOME` in its own temporary directory. Run on this machine outside
Slurm (Jacob: "that's fine for now"), `MCDONALD_HOME=/scratch/tmp/mcdonald-
suites`: measurement 181, reduction 134, published 32, cli 58, gui 456 + the
WxAgg skip, golden 12. A second gui run while golden ran failed one timing
check ("Stop during layers": layers finished all 19 pairs first); on a quiet
machine it passed again.

- **The icon on the first screen**: the icon another session made (`5877def`,
  already every window's icon) is drawn at 64 px beside the two lines. The logo
  with its words (`docs/logo-*.png`) is not in the package, and has a dark and
  a light version; the icon alone needed neither.

## On a Mac at last (GitHub's runner); the repository public; two READMEs (2026-09-25, late)

Jacob: "Run any macOS-specific tests on the software before I share it with Ravi."
Nothing here is a Mac, so `.github/workflows/platforms.yml` runs them on GitHub's
`macos-latest` (arm64, macOS 26, 5 virtual CPUs): job `suites` (setup-python 3.12 as
python.org's, brew ffmpeg, `pip install ".[gui,dev]"`, `mcdonald setup`, then reduction,
published, cli, measurement, gui on the runner's own desktop) and job `homebrew`
(Homebrew's Python: pip outside a venv refused, as install.md says; a venv; `mcdonald
setup`; `mcdonald-gui` screenshotted at 15 s). **Start it** with `git push -f origin
HEAD:macos-ci` (a commit tried on a Mac before main) or Run workflow by hand. **Read it**
with git: each job pushes its logs to branch `ci-logs`, `logs/<run>-<sha>/<job>/`
(`times.txt`, `failed.txt`, each suite's log, `gui.png`). The GitHub API is not used: `gh`
is not installed, and taking the token from the git credentials was refused.

What the Mac found, each fixed and each something Ravi would have met at once:
1. **ffmpeg 9 (Homebrew's now) has no `-vsync`**: every extraction failed ("Option not
   found"), and the range player's reader silently. `clip.every_frame()` gives
   `-fps_mode passthrough`, or `-vsync 0` for an ffmpeg older than 5.1 (Ubuntu 22.04's
   4.4); extract, look's thumbnails and `reel.Reel` use it. Here (ffmpeg 8.1) the
   player's sound-track check passes with it, and on the Mac too.
2. **No font**: `/Library/Fonts` has had no Arial since 10.15, so no contact strip, track
   strip or sheet, and the window's save said "Nothing was saved" (a missing font is an
   OSError). `figures.pil_font` now also tries `/System/Library/Fonts/Supplemental/Arial`
   (bold is "Arial Bold.ttf") and last matplotlib's own DejaVu Sans, which every install
   has, Windows included. And `tracksheet` opened Fedora's Liberation path by name; it
   goes through `pil_font` now (same font here, same picture).
3. Two test checks expected "Ctrl" where a Mac rightly says ⌘ (Keys, Getting started).
4. The runner is slow: test_gui took 939 s there against 331 s here, and at its usual
   deadlines the PySide6 child was ended just after Measure's gate and looked like a hang.
   `MCDONALD_TEST_PATIENCE` multiplies every test_gui deadline; the workflow sets 3.

Runs: 1 (2ab1126) cli/measurement/gui broken by 1 and 2; 2 (ec4626e) measurement 181 all
pass, the sheet's font; 3 (2d8da7d) cli 61 all pass, gui 2 left; 4 (8e81d69) gui 414 + 1
(the Getting started ⌘); 5 (47ac843): **all pass** -- reduction 139, published 21 + 4 skipped (no recorded tracks there), cli 61, measurement 181, gui 415 + GTK3, GTK4, wx skipped; 23 minutes of suites. Linux, run directly (the queue was full of
`galdet`; Jacob: "you can run that outside of slurm"): reduction 139, published 32, cli 61,
measurement 181, gui 470 + the WxAgg skip; cli again 61 after setup's new lines.
Not fixed: the Mac menu bar says "Python" rather than mcdonald (the bundle's name; the
Dock icon is right). GTK and wx skip on the runner (not installed), as expected.

**Then Jacob made the repository public** and asked for the README to be split: "make the
current README.md file named something to indicate it is intended for AI or extreme
technical users, and then we can write a much shorter README that is displayed on the
GitHub landing page and after `mcdonald setup`". `README-technical.md` is the old one with
a first line saying who it is for; `README.md` is new, about 90 lines, in plain words:
the logo (dark or light as GitHub's theme asks), what it does, three install lines, the
window's three steps in its own words, open only the part with the object, what the
report can and cannot say, and "give an AI agent README-technical.md". `mcdonald setup`
ends with both addresses (a link, since a pip install has no repository to name a file
in; printing the README into the terminal was the other reading, not done). install.md
lost its collaborator/`gh auth login` note.

**The licence** (Jacob, same evening): BSD 3-Clause, copyright "Jacob Haqq Misra" (his spelling,
now pyproject's author too), in LICENSE and pyproject (`102b722`).

**After his README edits** (357f8cc, f40ce9d): bare `mcdonald` names `mcdonald-gui` first;
**`mcdonald readme`** prints README-technical.md, and `readme method|agents|install` the docs it
names, from the install itself (setup.py copies them into `mcdonald/docs/` at build time,
MANIFEST.in into a source archive; an editable install reads the repository's), so the
README's agent prompt is "Run `mcdonald readme` to get started" and needs no GitHub.

**Two rules now that it is distributed** (Jacob, 2026-09-25): (1) **the version goes up with
every change sent out** -- pip's `--upgrade` from GitHub installs only a newer number (at a
same number it says "already satisfied" and keeps the old code; tried). It is written once,
`mcdonald/__init__.py`; pyproject reads it; test_reduction holds both READMEs' status lines to
it. 0.2.1 is the first. (2) **main is the release**: "be careful not to push to the public
repo until we are ready for others to try the features". Work is committed locally and
pushed only when he says it is ready, with the version raised in the same push.

**Sent to Ravi (macOS) on 2026-09-25, at 0.2.1; 0.2.2 pushed before he started.** Jacob will
pass on his feedback; start the next session from it.

**0.2.2: it updates itself** (Jacob asked, 2026-09-25). `mcdonald.update`: a copy pip installed
from GitHub (direct_url.json has `vcs_info`; a working copy or a CI build from a checkout
never checks) reads `__version__` from main's `src/mcdonald/__init__.py` on
raw.githubusercontent.com, at most once a day (state in the user cache dir, `update.json`).
The window (`gui.main`, joined ≤3 s before the first screen) asks "Update now / Not now /
Don't ask again"; a yes starts a stdlib-only helper that waits for the window's process to end
(Windows: the running .exe is locked), runs `python -m pip install --upgrade
"mcdonald[gui] @ git+…"`, and opens the window again, or shows pip's last lines. The command
line only prints one stderr line once a day, after the command. `MCDONALD_NO_UPDATE_CHECK=1`
turns it off. So **main's version number is now what testers' copies compare against**: a push
with a higher number makes every tester's window offer it the next day. test_cli holds it
(a file:// "main", a fake pip). Also: Find's busy line lost "What it finds is listed under
the video as it goes" (his request).

**0.2.3: Help -> About** (Jacob, 2026-09-25, pushed so he could try the update on his laptop):
version, `__released__` (beside `__version__` in `__init__.py`; bump both), the README's one
sentence, the McDonald quote, the repository link and the copyright/license line.
The words are `actions.ABOUT`, `QUOTE`, `COPYRIGHT`; test_reduction holds each to README.md
word for word, so a README edit there fails until About follows.
**Jacob tried the update on his laptop, 0.2.2 -> 0.2.3 from the prompt: "works great!"**

**0.2.4: from Jacob's PR23 run** (2026-09-25). (1) The player's controls jittered left and
right while playing: the time label grew and shrank with its digits (proportional figures)
past its 170 px minimum, and the stretches on either side re-centred the buttons. It is now
fixed at the widest it can say (every digit tried); the range player's `where` is sized by the
layout, not its text. test_gui checks the buttons' x over frames. (2) **The report had no
v_px with a good track**: the run was stopped during layers (`/scratch/mcdonald/pr23`), so
kinematics never ran -- almost certainly by the panel's ✕, which closed it and so stopped the
measuring. Now the ✕ only puts it away while it measures, the panel hides itself once
Measure starts (he asked: step 3 has the bar), step 3's button reads "Stop measuring" (as
Follow's does), and the report of a stopped run says "stopped during layers" / "before
kinematics" (`Case.stopped_in`, a `STOPPED_BEFORE` note from `run_case`) on the v_px row and
in the bottom line instead of "needs a track". (3) Measure's integrity check starts unticked
(`measure_qt.OFF_AT_FIRST`); `mcdonald run` still runs it unless `--skip integrity`.

**0.2.4 also moves to PyPI** (Jacob, 2026-09-25: "add this as well for the next release").
`pip install "mcdonald[gui]"` -- no git, which most Windows computers lack. The install lines
(both READMEs, docs/install.md, `mcdonald setup`) say so; README.md's links are absolute so
PyPI's page shows the logo and finds install.md and LICENSE. `.github/workflows/publish.yml`
builds, checks the tag equals `__version__`, twine-checks, installs the wheel, and uploads by
trusted publishing (no token) on a `v*` tag: **a release is now `git push origin main vX.Y.Z`
after tagging**. `update.installed_from()`: no direct_url.json + INSTALLER pip = "pypi" (asks
pypi.org/pypi/mcdonald/json, upgrades `mcdonald[gui]`); vcs_info = "github" (main, as before,
for 0.2.1-0.2.3 copies); anything else (editable, a wheel file) is not checked. Tried: an
index install has no direct_url.json, a wheel file has archive_info. Jacob's part, once:
a PyPI account (2FA), and a pending trusted publisher (owner haqqmisra, repo mcdonald,
workflow publish.yml, environment pypi). **Done, and released: v0.2.4 on PyPI 2026-09-25**, about 70 s after
the tag was pushed; `pip install "mcdonald[gui]"` into a fresh venv gives 0.2.4, source "pypi",
and `mcdonald setup` says Ready.

**0.2.5: `pip install mcdonald` is the whole thing** (Jacob, 2026-09-25: "I'd rather that everyone
gets both"). PySide6-Essentials is a dependency, not the `gui` extra; the extra is kept, empty,
so `mcdonald[gui]` (0.2.1-0.2.4's update commands, instructions already sent) still installs
with no warning (tried). Install lines everywhere are `pip install mcdonald`; a PyPI copy updates
with `pip install --upgrade mcdonald`. The command-line-only case now carries ~100 MB of Qt it
does not use; that was his call. **Released: v0.2.5 on PyPI 2026-09-25**; a fresh `pip install mcdonald` has the window and updates from PyPI.

**0.2.6: `mcdonald setup` puts it in the applications menu** (Jacob, 2026-09-25: "then it doesn't
need to be under help"). On Linux with DISPLAY or WAYLAND_DISPLAY, setup calls
`gui.desktop_entry()` itself (rewriting it each time, so the Exec path follows the install);
headless it says "not added: no desktop here"; `--no-desktop` skips it; `--desktop` is kept,
hidden, for instructions already sent. The Help item and `add_to_desktop` are gone;
`mcdonald-gui --desktop-entry` stays. test_cli points XDG_DATA_HOME at a temporary folder:
without it the suite would write the person's own menu. **Released: v0.2.6 on PyPI.** Then 0.2.7:
the entry's Exec was the PATH's mcdonald-gui -- on Jacob's machine his working
copy's, from a venv's setup; `gui.own_script()` now takes the one beside this Python, then
this scheme's and the user scheme's scripts folders, the PATH's last. Tried in a venv. **Released: v0.2.7 on PyPI**; from a fresh venv, Exec is that venv's.
0.2.8: Open by catalog name asks on two lines, with one example of each form
(DOW-UAP-PR23, 06:PR144, PR149); every progress line under Find, Follow and Measure is a
1-3 word technical name (Static masks, Motion search, Spot size, Layers, ...), on stderr
too. **Released: v0.2.8 on PyPI.**
0.2.9: step 2's lines around the track check are short -- 'Making track pictures…',
'Check the track below the video', 'Track checked: on the object' -- without the linker's
summary after them (Jacob: the old line was needlessly long and confusing). **Released: v0.2.9 on PyPI.**

**What was left before Ravi (done):** send him docs/install.md (macOS) or just the repository's page, and
ask for the output of `mcdonald setup`, whether `mcdonald-gui` opens, and PR149 end to
end (Find, This is it, the check, Measure, the report) -- or whatever breaks, with the
words on the screen. What the runner cannot tell: a real person's Gatekeeper and
permissions prompts (Documents folder access), python.org's certificates (setup names the
fix), the ⌘ keys and menu roles under a real hand, `QDesktopServices` opening the report's
pictures and the folder.

## The polish is done: what is left before Ravi (2026-09-25, night)

Jacob: "Other than that, I think this is ready! Please finish all of the above,
and then let me know what is remaining in order to share with Ravi. Ravi is on
macOS but I confirmed that he can run pip install."

Done in this last round: the stripes stop once a bar advances (`Stripes.set_fraction`:
a plain fill, its timer stopped); both players have to the start, a frame back,
play/pause, a frame on, to the end and stop (icons; stop = pause and frame 1,
Shift+Home in the chooser; `QtMarker.stop_play`, `RangeChooser.stop`); the README
has "What it needs, and how long it takes" (disk, memory, and each step's time on
this 2012 Xeon); the optional fields' line is "Leave empty what you do not know."
A clean install was checked: a fresh venv, `pip install .` and then `.[gui]` --
the wheel carries pursue_videos.csv and the 8 icons, both commands are made, and
`mcdonald setup` reads right. The repository is **private** (GitHub answers 404
unauthenticated): docs/install.md now says how a collaborator signs in (`brew
install gh`, `gh auth login`) or uses SSH.

**Left before Ravi, in order:**
1. Add Ravi as a collaborator on github.com/haqqmisra/mcdonald (or make it public).
2. Send him docs/install.md (macOS), and ask for three things back: the output of
   `mcdonald setup`, whether `mcdonald-gui` opens, and PR149 end to end (Find,
   This is it, the check, Measure, the report) -- or whatever breaks, with the
   words on the screen.
3. Optional, before him: one GitHub Actions run on macOS (free minutes; `workflow_dispatch`
   only) of test_reduction, test_published, test_cli -- the first time any of it
   runs on a Mac. Not written yet.
What has never run on a Mac, for him to meet first: python.org Python's certificates
(setup names the fix); Homebrew Python's externally-managed pip (install.md: a
venv); the process pools under spawn (Find, Follow, Measure all use them); the
menu roles and the ⌘ keys; `QDesktopServices` opening the report's pictures and
the folder; Qt's media icons. (Light mode is not a worry: `application()` sets the
Fusion style and its own dark palette everywhere.)

## One bar a step, on the right; Measure waits for the check; a ruler; PR149 (2026-09-25, evening)

- Step 3 was lit as next while step 2 was still following (a growing track counted
  as followed). Now `followed` needs the follow ended, and Measure is next only
  once the track is answered yes (`track_ok is True`); between the follow's end and
  its pictures step 2 says it is making them.
- **One progress bar a step, in the step's card**: Find's and Measure's own bars
  and times are hidden (kept, and still set, for the tests); `FindPanel.progress()`
  and `MeasurePanel.progress()` give (fraction, line) and `say_steps` puts them in
  steps 1 and 3, the panels calling it on each tick. Step 2's `Stripes` now fill:
  0-20 % while the spot size is chosen (sizes tried), then 20-100 % as the open
  frames are run through (`_follow_fraction`, from the link's n_lo/n_hi); the
  masks alone are stripes with no fill. While Measure waits for the sheet, step 3
  says so, with no bar.
- The suggested example is PR149 (the catalog prompt, its menu tip, `mcdonald
  setup`'s next steps, the README's install lines); the README's worked PR113
  examples stay.
- Stepping a frame: the players' ±1 buttons are words now ("◂ 1 frame", "1 frame
  ▸"); the skip icons read as "to the start". Keys unchanged.
- **A ruler** (Jacob, working PR149: "use the GUI to figure out the pixel length"
  of the ship): "Measure on the video" beside ref_px, size_px and diameter in
  Measure's optional fields (`measure_qt.RULED`) -- the next drag on the video is
  a line with its length (`FrameView.ruler`, `measured`; `QtMarker.start_ruler`),
  put in the field, which is scrolled to; the next click is a mark again. PR149
  frame 21, stern to bow: 924.8 px (the Note's 920). KNOWN is now fov, range_m,
  ref_px, ref_m, graticule, then the rest. Not done: a field for the range ratio
  R_obj/R_ref (kinematics takes it; the form assumes 1, a ceiling).
- cli 61, gui 470 (Slurm job 1141).

## Find and Measure in the window; the moving bar (2026-09-25, later)

- **Find and Measure open under the video**, in a work area (`QtMarker.work`, in a
  vertical QSplitter under the video and its controls; `show_work(panel)`): each
  is a QFrame now, not a dialog, with a ✕ in its heading row that closes it as
  closing its window did (Find stops looking; Measure stops and answers an open
  sheet with no). Opening one hides the other without stopping it;
  `work_changed()` gives the room back to the video when none is open. Measure's
  body scrolls between its heading and its button; its report still opens (it
  is a window, as asked) unless the panel was closed (`MeasurePanel.closed`,
  not visibility, since Find can hide it). Find's strips are 120 px high
  (`STRIP_HEIGHT`) so six fit; its text and step 1's say "under the video".
  Measure's track-sheet question is still a window of its own (not asked).
- **Step 2's bar moves** while it follows: `mark_qt.Stripes`, diagonal teal
  stripes on a 40 ms timer that runs only while shown (a fraction can fill it;
  unused yet). test_gui checks that it moves and stops.
- gui 468 + WxAgg skip (Slurm job 1140).

## Check the track under the video; the report reordered, with two figures; `mcdonald setup` (2026-09-25)

- **Check the track is in the main window**, not a window of its own: a teal-edged
  panel between the video and the controls (`check_slot`; `track_strip` is now a
  QFrame there, `close()` hides it), with the question, the pictures at 110 px
  (`TrackStrip(height=)`), and No / Yes. While it waits, step 2 says "Answer
  under the video…" and its button is not the teal one (`Step.show_stage(press=)`).
  A new follow hides it.
- Measure again: step 3 says "The report is being regenerated…" and hides Open
  the report while it measures. `KNOWN` starts with fov, then range_m (the form,
  `run --help` and `run_case` keywords alike). The track sheet's second line is gone.
- **The report, in the order Jacob gave**: the title and one line (file, size,
  fps, frames, "Generated by mcdonald 0.2.0" -- no method.md); the provisional
  note, if the sheet is unconfirmed, as the one line kept from the old "What the
  clip is"; **Summary of variables** (v_px, then v_px against the striated and
  the isotropic background from `layers`, then FOV …; no "Read from the video");
  **Missing quantities** (was "What would close it"); **Figures**; Bottom line;
  **Measurements**, folded, which now also holds the record (provenance), the
  notes and each stage's no-power lines -- "What the clip is" and "What this clip
  cannot decide" are gone as sections, nothing dropped; **Where the marks came
  from**, folded, which now opens with the identification sentence (off the top,
  as asked); **Reproduce on command line**, folded. The version line and the
  custody caveat at the foot are gone. The report page opens and closes each
  folded part on its own (`mcdonald:details/N`), links teal, no gap under
  pictures.
- **The two figures** (`figures.report_figures`, drawn in `run_case` before the
  report, listed in `Case.figures` and the JSON), after the PR144 working note's
  two panels: a frame from the middle of the track with its path, dots each half
  second (a quarter of a short track), the rate and against what (`Case.rate`:
  the layers' all-group median, else the image), and the object enlarged; and
  size S = pR/k and speed ωR against range -- one line at the measured or
  assumed k with a weather balloon and a fighter jet marked on it, or with k
  unknown three equal lines (FOV 3, 10, 30°; none favoured, unlike the PR144
  note's 10°, which had a reason there), Mach 1, and a given R marked.
  test_reduction draws both.
- **`mcdonald setup`** (`setup_cli.py`; runs before the ffmpeg check every other
  command does): Python, ffmpeg (with this system's install line), the window
  (PySide6, a screen), storage (and room), catalog, downloads (one HEAD to the
  smallest DVIDS video; a certificate failure says what to run on a Mac); then
  what to type next. `--desktop`, `--offline`, `--json`; exit 3 when ffmpeg or
  Python is missing. The README's Install is now three steps (ffmpeg, the pip
  line from GitHub with `[gui]`, `mcdonald setup`), the developer install and
  tests under "Working on the code"; `docs/install.md` walks macOS, Windows and
  Linux (unverified on the first two: Ravi and Gary will be the first).
- A trap met here: a Bash call with `PATH=<dir without bash>` prefixed spawned
  some 1,600 shells from the tool's shell snapshot before it was killed by pid.
  Test a missing tool from inside Python (`os.environ["PATH"]`), as test_cli does.
- Suites on the final code: measurement 181, reduction 139, published 32, golden 12
  (Slurm job 1104); gui 466 + WxAgg skip (job 1111); cli 61 (run here). Three
  checks were moved with the report: Measurements is opened on the page before its
  pictures are looked for, and `report --i-looked` changes the top only by the
  provisional line and Missing quantities only by the sheet's need.

## The report's summary of variables; Measure's optional fields in the trade's terms (2026-09-24, late)

- Measure: "Provide additional information about this video (optional)"; its
  fields may use technical terms (Jacob): `Known.term` is the form's label (FOV,
  R, l_px, L, v_own …), the plain words stay as the tooltip with the command
  line's flag, and `drive_plain_words` skips widgets under objectName
  "technical".
- The report: "I don't need to write this myself anymore" -- the report is ours
  to word now. At its top, under the identification sentence, **Summary of
  variables** (`Case.summary`): the Technical Note's variables, pixel velocity
  first, then FOV, k, ω, p, R, θ/Ṙ, v_own, ωR, S, |v_obj − v_own|, v_obj, each
  with its value (bold) or "—" and how it was found or what would give it; f and
  W × H above the table. FOV is k's linear extrapolation across the frame (the
  Note's "≈54°" for PR113) or the assumed one; p is the size given, the measured
  half-peak width, or the spot size followed. For it `scale` now records
  fov_deg/fov_from and `kinematics` range_m, range_rate_m_per_s, theta_deg,
  size_px and fps. test_reduction holds it to PR113's published numbers (54.2°,
  2028 px/rad = 35.4 px/deg, ω 2.09 rad/s for a 141 px/frame track).
- The frame annotations (each non-hand mark's record) moved from above the
  bottom line to **Where the marks came from**, near the end, in
  `<details>`; the report page shows it as a teal link that opens and closes
  it. The identification sentence stays on top (the package's founding claim),
  with an agent's reason in it and a pointer down.
- Suites: measurement 181, published 32, golden 12 (local, the user's leave);
  reduction 138, cli 58, gui 465 + WxAgg skip on the final code (Slurm job 1103).

## Following shown, the track checked yes or no, Measure and the report (2026-09-24, night)

His points after trying the steps, each done:
- Find: "It only offers:" gone; "since it started" is "elapsed" (Find and Measure).
- "It is not clear that 'following' starts automatically": step 2 is drawn busy
  while it follows -- a moving bar (`Step.busy`) and "Following the object… " with
  what the link says as it goes.
- "Mark the object by hand ... moves everything out of the window and a
  horizontal scrollbar appears": the panel never scrolls sideways now (the spot
  settings in two rows, the pointer's line wraps); it scrolls down.
- "Is this the object in every picture? The user has no way to answer": the strip
  ("Check the track") asks "Is the box on the object in every picture?" with
  "No, it goes off the object" and a teal "Yes, it is on the object"
  (`QtMarker.answer_track`, `track_ok`). Until it is answered step 2 stays next
  and Measure waits; no opens marking by hand and says to click the object where
  the box is wrong and Follow again; "Check the track" in step 2 shows it again.
  A new follow asks again. (This is the window's own check; Measure's track-sheet
  question, the report's gate, is still asked -- not merged, as it is recorded in
  the report.)
- Measure's window: "Measure the object" and one muted line; "Frames to measure"
  and "Slow checks" as quiet cards; the thirteen fields folded under "What you
  know about this video (optional)" (it counts those given); the bar, the step
  and "Show details" (the log, folded) only once it runs; Stop only while it
  runs; one teal Measure ("Measure again" after), and "Open the report". Its
  track-sheet question is a heading with a teal yes.
- The report page (`measure_qt.render`): a header ("Report — PR113", the path
  muted, Open the folder); an amber banner with "I have looked at the track sheet
  now" when the sheet is unconfirmed; the Markdown with room round it, headings
  sized (section headings teal), 135 % lines, tables ruled and page-wide, and
  code blocks and long paths wrapping -- the page scrolled sideways before. The
  report's words are unchanged: he will word the report himself.
gui 465 + WxAgg skip. Seen end to end on PR113 380-460 (Find, This is it,
following, the strip's yes, Measure without the slow checks, the sheet's yes,
the report).

## Segments, the steps panel, Find and the first screen (2026-09-24, evening)

His words: the catalog prompt suggests "such as PR113 or PR144" (not PR001, which
only showed the RELEASE:NAME form; the command line's help keeps it); the
chooser is "Select a segment of the video (<file>)" / "Select the segment of the
video with the object", "Play segment", "Open this segment" -- and "segment"
everywhere a person reads it there ("Segment to open", the tips, Shortcuts).

"Now, make the same modern GUI improvements to the next part. Most users will
want to use the auto-find features and only resort to clicking as a last
resort. It should be evident to a new user what steps they need to take." And,
while that was under way: the version on the first screen, and the first
screen in the same style.
- **The main window's side panel is three steps** (`mark_qt.Step`): 1 Find the
  object, 2 Follow it, 3 Measure (with "Open the report" when there is one).
  Each is a card with a number, a line on what it does, its button, and a line
  on how it stands; the one to do next is outlined in the icon's teal
  (`ACCENT`) with a teal button, a done one has a tick, one not reached is
  quiet and its button disabled. `QtMarker.say_steps` works it out from the
  marks (their `kind`: proposed or by hand), the Find panel, the link and the
  report file, and is called from marks_changed, the link's reports and the
  Find panel. Buttons: "Find the object" ("Show what Find found" once it has
  found and nothing is chosen), "Follow the object" / "Stop following" /
  "Follow again", "Measure"; the keys are in their tips. The link's words are
  step 2's state line (`link_label`).
- **"Mark the object by hand" is folded away** beneath the steps: the six mark
  buttons (moved from under the picture), the loupe, the velocity, the table
  of marks, the spot settings. It opens by itself the first time a mark is put
  by hand; the status bar's "marking: object, N marks" shows only while it is
  open.
- **Under the picture**: the time (bold) over the length, the frame muted; step
  back, play, step on as media icons; the speed a menu; the frame box. −10/+10
  and first/last are keys only (as in the chooser).
- **Find**: "Which one is the object?" and one muted line (if none is, "Mark the
  object by hand" in the main window); "This is it" teal, "Show in video"
  plain; the strength a chip, the description muted; Stop and the progress bar
  only while it looks; "Look again" after.
- **The first screen**: the icon, "mcDonald UAP Toolkit" large and "version
  0.2.0" (`mcdonald.__version__`) muted; his two lines; "Open a video…" teal and
  "Open by catalog name…" beside it; the save folder in a quiet box with
  Change…; Quit small at the foot.
Checked end to end on PR113 380-460, offscreen: Find's first row was the
transit (141 px/frame; the note's 142), This is it followed it on 408-411, and
the steps went done, done, Measure next. test_gui checks the steps' progress
and the by-hand section opening at the first click: gui 462 + WxAgg skip, cli 58.

## His wording, and the part chooser made calmer (2026-09-24, later)

Jacob's words for the first screen ("Data will be saved to … This can require
several GB."; a full stop after "video"), the Change… dialog ("choose a folder
to save data"), the download question (no "the government website that
published it"; "will be saved to"; "(N GB free)"), and PURSUE in capitals
wherever a person reads the catalog's name (`Catalog.label`; `name`, which the
reports' JSON records, is still "pursue").

Then: "Once I get to the next part of selecting the clip, it seems like it
could get overwhelming for a new user. Before I make specific suggestions, see
if you can improve this based on modern GUI principles." The RangeChooser was
six lines of text at one weight, thirteen controls in one row, and the part set
by two frame numbers apart from the bar. Now:
- a heading, and one muted line of guidance; the file's facts are the
  heading's tip;
- the part is dragged on the bar (`Timeline.trim`: a handle at each end,
  `trimmed(a, b)`, the picture follows the handle), with Set start / Set end
  and the frame boxes (prefixed "frame") for exactness, in a "Part to open"
  box with the part in time, seconds and frames;
- one transport row: the time (bold) over the length, the frame muted; step
  back, play (large), step on, as the style's media icons; the speed a menu;
  "Shortcuts" (its tip, or a click) lists the keys. −10/+10, first/last and
  play backward are keys only now (all the old keys still work);
- the cost in a few words ("Needs about 58 MB of space (868 GB free)", amber
  "Too large…" when it will not fit), the full sentence and the folder in its
  tip; "Open this part" is the default button.
test_gui drives the handles (the end cannot pass the start) and the speed
menu: gui 460 + WxAgg skip; measurement 181, cli 58.

## The leftovers, finished (2026-09-23, evening)

Asked how much was left, Jacob said to finish all of it: the rest of the agent's
report (Next 0), the parallax ladder with its inputs optional (his choice of the
two offered), and Next 1b, 3-7. Next 3b (the report and the Measure log in plain
words) is **dropped**: he will write those words himself. One commit (the one that carries this file),
with all six suites run on a snapshot of it (Slurm job 998, test_cli again as
1016 after two fixes): measurement 168, reduction 134, published 32, cli 52, gui
449 + the old WxAgg skip, golden 12 (cli 58 in 1016). Find's table on the final code (job 997,
`tools/find_rank.py --link`) is the 2026-09-23 table unchanged on all eight
cases -- same ranks, same links -- and PR055 90-350 is now first (below).

**The agent's report (`docs/agent-run-pr135-2026-09-22.md`), the rest of it:**

- **`propose` had `layers`' trap** (item 19's twin). Its background shift is a
  phase correlation kept only if it fits better than none; on PR135 150-320
  every frame but one was "held still", and each proposal's "against the
  background" was against the screen. A background still or nearly (under
  `SLOW` 0.5 px/frame) over K is measured again over a second
  (`propose.still_again`): no shift within 2 px of none, a peak `CLEAR` (2x)
  above the next. PR135: -9.3, -3.0 px/s (hand -9.0, -4.2; before, 0). The
  residual is registered as before -- only the speed changed -- and on the eight
  recorded cases nothing moved (jobs 971/979 against 972: same ranks, same
  links; PR055's scores 11.63 -> 11.83). `integrity` was looked at: its
  frame-to-frame registration already says when a pattern could hold it and
  when the scene is nearly still. `groups` sums frame-to-frame phase
  correlations, which read a slow banded scene short (~0.2 of 0.6 px over 2
  frames on PR135); it only decides "moves with the track, not the
  background", which a 7 px/frame group is either way. Not changed.
- **8, a proposal that holds several points.** `Proposal.points`
  (`propose.points_in`): spots that go with it to its next frame, all moved
  alike, with sky between them. PR135's group (195-279) 2; the recorded single
  objects of PR149, PR142, PR148 0, 1, 1 -- PR149's contact is two spots 10 px
  apart with the contact between them (0.94-1.06 as bright half way; PR135's
  points 0.15 or less). `says` and the sheet add "it holds about N points …
  `mcdonald groups` follows each".
- **22, a defect map.** `forensics.defect_map`: spots fixed on the screen (1 px,
  half the frames, 16 frames of the window) while the scene moves -- or where
  that cannot be measured (sea with no texture but the sensor's) unless the
  masks call the scene still. PR135: 62 in the tracking segment 400-1150, all
  of the agent's hot pixels among them; 13 in 150-320; 53 in 1240-1401,
  where the scene could not be measured. It is a list of places, not
  a mask: symbology the masks missed and an object followed to a pixel are on it
  too (PR135's "N" is). `look --frame` rings those candidates grey
  (`stays_put_on_screen`), and a link's concerns name one under disputed frames
  (made only when a command asks for concerns: ~15 s). Cached beside the frames.
- **23, `encoding` in every envelope's `clip`** (and every case): codec,
  profile, pix_fmt, reorder depth, bit rates, container, and `gop` from 150
  frames (`clip.encoding`, 0.7 s; ffprobe now skips the loop filter and the
  inverse transform, the types the same). `run`'s ingest says the GOP.
- **7** the proposals sheet in pages of 8 (`…_2.png`); **10** `look --frame`
  offers a row of candidates across the frame as `caption_rows` for
  `--mask-rows` (PR135 frame 100: 674-699); **11** a link's concerns say when
  disputed frames pass over symbology, a block or a defect; **20** `layers` and
  `integrity` say when a `_marks.json` sits in the case directory and they were
  not given it (notes, not used by default: which marks is the caller's).
- **9 (a) and (c).** `look --frame` prints a `--tpl-box` for every candidate
  (PR135's "N" on 830: 763,202,786,225, the agent's was 762,202,785,225).
  `symbology --method auto`, finding nothing by colour in 20 frames, lists
  `glyphs_to_try`: glyphs a template follows at a fixed radius from the
  boresight over those frames, each with its box -- it does not choose (a hot
  pixel and a fixed tick keep a radius too). **PR135 itself: 10 s** (the "N",
  and a hot pixel), where it was 8 minutes for nothing. **PR148's pointer**
  through the template peak with the listed box (661,613,684,636): 549/598
  frames, r 301.14 +/- 1.21 px about the frame centre (method.md's 295.3 was
  about another boresight), not drawn at whole pixels, +0.030 deg/s, the
  scatter's bound 0.014.
- **1 and 15, the parallax ladder** (Jacob: build it, inputs optional).
  `kinematics --ground-speed SPEED[,BEARING] --own-ship SPEED[,HEADING[,ALT]]`,
  the same two in `run` and the Measure form (`stages.KNOWN`: two more fields).
  v_G = k v_O - (k-1) v_A: for each speed of its own (0 … 100 m/s) the k and
  h_O/h_A that give the ground speed -- a range without the two directions, one
  or two k with them, and for a still object the nearest k and the speed it
  would still need across. `kias@alt` is turned into TAS (ISA, with the +/-15 C
  band). Without both: `no_power` naming what is missing -- now in every
  kinematics stage, which is one more NO POWER line in every report.

**Next 1b, 3-7:**

- **1b (iii) was the rank tool's, not the proposer's.** PR055's enlarged copy
  (a 74 px disc) was Find's first two rows all along, 13 and 15 px from the
  recorded centre; `find_rank.on` held everything to 12 px. It allows a third
  of the thing's width now: **1 of 213, fair 7.98 (next 2.78)**. A second double
  difference at 16 frames was built for it and tried (job 990: PR055 both ways,
  PR113, PR144 -- identical lists) and taken out. **Its link fails**: no spot
  size up to 45 px is within 6 px of the marks (closest 10 px, at 45). The
  detector's `SIZES` stop at 45; a 71 would be a decision about the detector.
- **1b (i), a pan over featureless sky: nothing to fix from the scene.** On
  PR113 380-440 neither the phase correlation nor `shift_field_auto` (which the
  last handoff said would see it) finds any motion: the sky has no texture.
- **1b (iv), symbology that moves:** a proposal in a row of 4+ at one velocity
  along their own motion, over 120 px, is said to be a scrolling tape
  (`scrolling_tape`, `is_tape`); a cluster is not. Said, not scored.
- **3** the report shows each step's pictures under it (Markdown image links,
  so any viewer does); the window's report page fits them to 820 px and opens
  one whole on a click. **5** `symbology` is a stage of `run` (after survey).
  **6** `report.Case.load`; `mcdonald report CASE.json [--i-looked]`, and the
  report page's button "I have looked at the track sheet now": the case read
  back, the sheet recorded as looked at, both files written again, nothing
  measured. **4** closing the window mid-measure waits (up to a minute, the
  window answering) for the step to end and the report to be written.
- **7:** the contact strip's cross is centred on its pixel (tested with a red
  pixel); the part of each video last chosen and the folder last saved to are
  remembered (QSettings); the modal dialogs are driven by a test (the player,
  the start dialog, the catalog question); `mark --set --typed` records a
  person's typed marks as a person's, and the report says so; `layers
  --validate` and `--composite` are fields. **Left on purpose:** `Case.result`
  keeps its formatted lines beside `fields` -- it is what the report prints,
  and `_num` reads a hand-built case in two tests; changing it moves every
  pinned sentence for no reader's gain.

## Five things Jacob chose (2026-09-23, the rest of the day)

Asked what to decide, he said: "Let's do 1, 2, 4, and then 3 (groups) and 3
(flickering)" -- the sub-pixel peak, the blur, the edge bug with the local link,
groups, flicker. Commits, each with all six suites run on it alone before it
was pushed: `ac5bf7e` (job 857), `8035967` (866), `c05f222` (903, with golden),
`942f4b9` (911, with golden), `b49b26d` (912, with golden).

- **The template's peak between pixels** (`ac5bf7e`). A parabola through the NCC
  peak, across and down. It found PR135's "N" within 0.04 px of a whole pixel on
  all 600 frames: the overlay is *drawn* at whole pixels, so the step is the
  video's. `drawn_at_whole_pixels` says so and keeps the 1 px step; where there
  is no step, `resolvable_deg_per_s` is twice the fit's standard error
  (`dtheta_dt_se`). PR135 (jobs 850/851): nothing its report said changes.
  PR148's pointer, the other template reading, was not run (no `--tpl-box` for
  it is recorded).
- **A point's blur** (`8035967`, item 14 b). `forensics.point_blur` fits a
  Gaussian to the clip's sharpest compact spots (sensor defects and clipped
  spots left out) and to the object; `run` gives `kinematics` a NO POWER for a
  speed in body lengths of an object no wider than 1.5 blurs (4 if it is
  clipped). PR135: *not measured* -- 24 of its 25 sharp spots are defects or
  clipped, and its points are clipped, as the agent found; before those two
  rules it read a 1.7 px "blur" off hot pixels and called the group resolved.
  PR055: a point 2.3 px, the disc 19.6, resolved.
- **The edge bug, and the link near where the object should be** (Next 1d).
  `source_candidates` leaves the edge band out before it looks (it stopped at
  the first spot in it), and with `n_max=None` gives every spot: the 25
  strongest exactly as before, then the rest, each the peak of its own size.
  The link from marks takes the 25 strongest, and between two marks the weaker
  ones within `NEAR` = 10 px of the line between them; all of them answering
  at least `LIKE` = 0.5 of the object at its weakest mark. The size is chosen
  as before but climbs to a size that answers more strongly at the marks
  (`STRONGER`, a matched filter peaks at the object's size: Find's mark on
  PR113's 408 is 5.3 px off the object, and held the choice at 15 px), or
  qualifies it with a spot within `TIGHT` = 2 px of both end marks among every
  spot (PR148). `END_GAP` 8 -> 2. Every value was chosen on the recorded
  tracks with `tools/find_rank.py --replay` (new: `--pick`, and `--keep` keeps
  every size at the end marks). Every spot everywhere, the obvious version,
  was tried and was worse (PR149 8 off and 30 disputed, PR142 36 off, PR055
  onto cloud to 1418); so was the 25 with no likeness floor at 21 px (drawn
  clips: 12 checks, the link over sky texture).

  | clip (Find's marks) | before (`8035967`, replayed) | now (Slurm job 885, replayed) |
  |---|---|---|
  | PR055 1007-1418, 957-1418 | 142 frames, 1157-1298, 0 off | the same |
  | PR113 380-440, 348-471 | 4 frames, 408-411, 0.0 px, 21 px dark | the same (at `END_GAP` 8: a 5th frame, 414, a spot 58 px from where the transit would be) |
  | PR144 300-500 | 201 frames, 3 off, 5 disputed, 0.3 px, 5 px | 199 frames, **0 off, 0 disputed, 0.0 px**, 9 px |
  | **PR148 140-440** | **nothing** (no size put a spot near the marks) | **176 frames, 142-325, 0.5 px on the 146 recorded, 1 off**, 9 px dark |
  | PR149 1-120 | 37 frames, 21 on the recorded track, 0 off | 70 frames, **40** on it, 1 off (76: 25.9 px, beside the mark on 77, where the clip repeats frames) |
  | PR142 130-290 | 98 frames, 7 off, 1 disputed | 103 frames, 8 off, 8 disputed |

  PR148 is the one the 25 spots were put to Jacob for. The detector bug is
  fixed with it, which the link had been leaning on.
- **`groups`** (a new command, and a stage of `run` for a thing linked as a spot
  of 9 px or less). Points within 120 px of the track that have some
  background all round them, that are not fixed on the sensor
  (`forensics.on_the_sensor`, now shared with the blur), and that move with the
  track rather than the background (`propose.background_shift`); each followed
  by Hungarian assignment against the group's shift; every pair's separation
  held against the members' own position noise. PR135 1240-1401 (the agent's
  window): **6 points a frame, each of the six within 0.3 px of the agent's
  hand-checked tracks A-F on 99-100 % of frames; "the members change places"
  (the median pair wanders 5.2 times the position noise)**. PR144: one point, a
  single thing. `propose` still lists a group as one thing (item 8): not done.
- **`flicker`** (a new command, and a stage of `run`, on the members `groups`
  found or on the object). A 4 px aperture with sub-pixel weights on the track
  smoothed over 5 frames (the agent's pixel-phase trap); the codec's rhythm
  from the clip's frame types (`clip.gop`: PR135, PR113 an anchor every 4th
  frame, 7.49 Hz; PR144 every 2nd); background apertures beside the object as
  the noise floor -- a beat must be 3 times theirs -- and as a control; members
  over the same frames at different frequencies or out of step. **PR135: six
  members at 6.98-7.83 Hz, 14-23 %, 60-178 deg apart: "the beat is theirs".
  The agent's own control -- six constant dots planted on a PR135 frame and
  encoded like it (`/scratch/tmp/pr135_mc/codec_ctrl/ctrl.mp4`) -- no beat: its
  5-7 % "beats" at 2-4 Hz stand 46-123 times their band, the grain's doing,
  and the floor (7.2 %) is what catches it.** A beat over the band alone would
  have called the control a flock. PR144: no beat.

Not done, of what the agent asked for with these: `propose` saying that a
proposal holds several points (8); a defect map for `look`, `propose` and the
linker (22: `on_the_sensor` is the function it would use); `gop` in every
envelope's `clip` (23: it is in `flicker`'s fields only).

## The agent's small items (2026-09-22 late night to 2026-09-23 morning)

From the triage below, in its order. Commits `673f5a5` (4, 9, 5, 12), `09e71e1`
(17, 18) and `3503a2c` (14 a); each with all five suites green on 4 CPUs
(Slurm jobs 589, 812, 825); `test_golden` not run — none touches `run`.

- **9, `symbology --method auto` fails fast.** A method `auto` chooses (hue, or
  template with `--tpl-box`; chroma is chosen only once it has solved the first
  frame) is tried on 20 frames spread over the clip first (`TRIAL`); if it
  solves none, the stage ends with a NO POWER entry that says what finds a white
  or grey pointer (`--method template --tpl-box`, and that `look --frame` rings
  the glyph). A method named on the command line is not second-guessed. Field
  `trial = {frames, solved}`. On a drawn 300-frame clip with a white pointer: 21
  frames read, not 101. *Not done:* the agent's (a), `auto` finding a monochrome
  glyph by itself (the brightest compact glyph at a fixed radius), and (c), `look
  --frame` printing a `--tpl-box`. Not run on PR135 itself.
- **4, progress.** `north_series` goes through `progress.counted`; the command
  line prints the `[ n s]` lines.
- **12.** The automatic track's header has one "NOT placed by a hand" line per
  reason, naming the frames, not one per mark.
- **5.** `docs/agents.md` says where the frames go (`$TMPDIR/mcdonald/<stem>` or
  `--workdir`), that jobs share them, and to set `TMPDIR` to disk for batch jobs.
- **2 was already so**: `look --frame` prints its cost line before extracting.
  It gives the size, not the time; the time is mostly ffmpeg decoding from the
  clip's start up to the last frame, which nothing estimates. Left.
- **17 and 18, what the angle is worth.** New fields: `position_step_px` (template
  1, hue 0.5, chroma null — a centroid), `theta_step_deg` (= step / r),
  `theta_deg_per_px_of_boresight` (= 1 / r), and for each rotation window
  `resolvable_deg_per_s` (one step over the window). `said` prints all three;
  `cross_los_sense` now calls a rate below one step "no measurable rotation"
  (before: below 1e-3 deg/s, whatever the method). For PR135 (r = 198): 0.29 deg a
  step and per pixel of boresight, which is its 1.3 deg against the hand tool's
  ~4 px away. *Not done:* a sub-pixel peak on the template's NCC surface (the
  agent's suggestion) — it would change the numbers of every template reading
  (PR148's pointer), so it is Jacob's to ask for.
- **14: Jacob chose (a), done** (`3503a2c`; suites green, Slurm job 825): wherever the speed
  in body lengths is printed — `kinematics`' reduction, the stage's result line,
  and a note in the report that names the size given — it says it is the body's
  length only if the object is resolved, and for a point is a speed in blur
  widths. The field is unchanged. (b) is still open. What was put to him:
  `body_lengths_per_s` for a point the detector sizes at its own blur. `kinematics` is given a track and a size and has no frames to
  measure a blur from; any threshold on `size_px` alone would be asserted, not
  measured. Two ways: (a) always say beside it that it means the body only if
  the object is resolved; (b) where there are frames (`run`, the window),
  measure the blur (the size of the static specks or stars) and put it in
  NO POWER when the object's size is within it. (a) is a sentence; (b) is a
  measurement with its own trap (a clip may have no point sources to measure).

## "`layers` registers the fixed-pattern banding" — an agent on PR135 (2026-09-22, evening)

Jacob had an agent (Claude Code, no display, jobs through Slurm) take PR135
(R06, an MQ-9, a group of six hot points) through the command line alone. Its
report is `docs/agent-run-pr135-2026-09-22.md`, 25 items; its own scripts and
outputs are in `/hugespace/local/research/uap/analysis/cases/pr135/`. Its first
priority, item 19: on frames 150–320 (an island held, drifting ~10 px/s on
screen) `layers --auto-track` said the scene moved 0.01–0.05 px per 5 frames,
and the island's own hot building (which the auto-track took) moved **10 px/s
"against the background"** — though it *is* the background.

**The effect is real; the cause the agent gave is not.** It blamed the column
stripes. Taking them out (each frame's column and row median) changed nothing:
still 0.0–0.1 px. What happens is in `shift_field_auto`: over 5 frames the
scene moves ~1.6 px, inside the ±4 px `shift_field` leaves out about zero, so
the pair falls back to "held still" (zero allowed) — and there the pattern that
stays on the sensor, fine speckle as much as stripes (its temporal mean is two
thirds of a frame's texture), holds the estimate at zero. Over 30 frames the
same pairs read −9.0 to −9.6 px, where the agent's hand tool had −9.0.
`glance` had always said "held still … read them as 'no more than'"; **`layers.
measure` threw the flag away**, and so did every report built on it.

**What changed** (`layers.py`; nothing in `forensics`):

1. A pair held still over k frames is **measured again over a second** (`round(fps)`
   frames, centred on it), with templates every 48 px instead of 96 — over
   featureless sea the pattern still wins at zero, zero is left out, and only
   textured templates are left (at 96, 6–7 on PR135, under the 8 a consensus
   needs). Its shifts are given as k-frame shifts, like every other row.
2. **Only shifts a still pair can have are kept** (≤ 5 px per k frames): the
   second round frame 300 takes in the slew at 312 (36 px), which its five
   frames do not.
3. Each template row says how its pair was measured (`MOVED`, `AGAIN`, `STILL`)
   and over how many frames; the CSV has `over_frames`; the fields have
   `held_still` (share of pairs, and share still over the second too); `said`
   prints it; over half the pairs still over a second is a NO POWER entry. The
   template cache's name carries all of it.

**PR135 150–320, `layers --auto-track`, 4 CPUs** (Slurm job 569, 15 min; the
agent's run was 8.5):

| | before (`46d63af`, replayed from the agent's cache) | now |
|---|---|---|
| the scene's screen speed | 0.3 px/s (−0.1, −0.3) | **−9.4, −2.6 px/s** (hand: −9.0, −4.2) |
| the building "against the background" | 10 px/s | **0–1 px/s** |
| pairs held still over 5 frames | not said | 98 %; still over a second too: 0 % |

`test_measurement: test_a_slow_scene_is_not_held_by_a_pattern_on_the_sensor`
draws it: a scene drifting 0.3 px a frame behind fixed speckle and stripes
reads (−0.18, −0.19) over 5 frames, truth (−1.50, −0.70); the fix gives
(−1.52, −0.70); a scene that is still is still, and marked so.
All six suites pass (Slurm job 576: measurement 141, reduction 97, published
32, cli 51, gui 441 + the old WxAgg skip, golden 12). No golden case prints a
held-still line: PR144 and PR113 never take the new path, so their numbers
cannot have moved.

*Not done:* `propose` and `integrity` register their own way (phase
correlation; `shift_field_auto` with a wider reach) and were not looked at for
this; the agent's point that `propose`'s "against the background" is "against
the screen" on a banded clip is unchecked. A slow scene costs `layers` about
twice the time now.

**The rest of the agent's report, triaged** (`docs/agent-run-pr135-2026-09-22.md`;
"checked" means looked at in the code this session, not fixed):

| item | what | state |
|---|---|---|
| 19 | `layers` reads a slow scene as still | **fixed, above** |
| 4 | `symbology` says nothing for minutes | **done 2026-09-23** |
| 9 | `symbology --method auto` falls to hue and grinds the whole clip before exit 5 | **done 2026-09-23**: 20 frames first, fail fast (a) and (c) not done |
| 5 | the frame cache follows `TMPDIR` | **done 2026-09-23** (`docs/agents.md`) |
| 2, 12 | a cost line before `look --frame`; `--why` once in the CSV header | 2 was already so (size, not time); **12 done 2026-09-23** |
| 7, 10, 11, 20 | the proposals sheet in pages; a caption row proposed as `--mask-rows`; a disputed stretch that crosses symbology said so; `layers` using a `_marks.json` it finds | not checked; each small, each an agent's convenience |
| 17, 18 | the template's angle resolution (1 px / r) unstated; θ as good as the boresight | **done 2026-09-23**, as fields and printed lines; the sub-pixel peak is Jacob's |
| 14 | `body_lengths_per_s` for an unresolved point | **(a) done 2026-09-23** (said wherever printed); (b), measuring the blur, open |
| 1, 15 | a parallax ladder (own-ship speed, h_O/h_A) in `kinematics` | new science; the agent's top feature. For Jacob: its inputs (own-ship speed, heading, line-of-sight azimuth) are not in the video |
| 3, 8, 22 | groups (a class, members split out of a proposal, rigid vs. shuffling); a map of sensor defects | new features |
| 21, 23, 24 | flicker photometry with the codec's cadence (`gop` in `clip`), a sub-pixel aperture, and a common-window cross-spectrum as the pass condition | new feature; the agent's scripts are in `/hugespace/local/research/uap/analysis/cases/pr135/` |
| 6, 13, 16 | `look --propose` found the group; `kinematics` matched the hand workup; `symbology` template 600/600 | worked |

## "Linking seemed to find a different track" — PR055 again (2026-09-22)

Jacob opened PR055 1007–1418, pressed Find, took the first row ("1 of 3 things
… dark, about 24 pixels wide; frames 1181–1291 (seen in 103)"), linked, and
saved: `~/Documents/mcdonald/pr055/`. Find's ten marks were on the disc (its
`_marks.png`), and so was the link *between* them — within 1.9 px of every mark,
forward and backward agreeing on all 111 frames. What was wrong was the rest:
351 frames linked, 1007–1408, and **209 of them were cloud**. The session was
reproduced exactly (the same ten marks from Find; the same 351 points, to
0.007 px of his CSV), so everything below is his case, not a likeness of it.

**Why.** `link_track` looks for the object within a gate about where it
should be: 25 px, and **12 px more for every frame it has not been seen on**.
That was made for the blind tracker, which does not know the velocity; a link
from marks does, and used it anyway. Going back from 1181 the disc came out of
cloud at 1157; before that the detector has no spot on it (fading, it drops to
22nd of the 25 spots a frame keeps, then off the list). Fifteen frames on, the
gate was 205 px, a dark patch of cloud 188 px from the disc was inside it, the
velocity was reset from that jump, and the link followed cloud back to 1007.
Going on from 1291, the disc runs into dark cloud at ~1298; a patch 36 px from
where it was heading was inside the 37 px gate a frame later, and from there
it jumped 70 px and then 172 px, to cloud again. The strengths do not tell them apart: the fading disc answers
the detector at 48–79, the patches at 48–77 (the clear disc at 100–130).

**What changed** (`autolink`, nothing in `forensics`, nothing in the blind
tracker):

1. `gate_for`: a link from marks grows its gate by **0.3 of the object's own
   speed** per frame unseen, never more than link_track's 12. PR055 (2.5 px a
   frame): 0.8. PR113 (142): 12, as before. From one mark there is no speed,
   and the gate is link_track's own.
2. **Past the first mark and the last, the link waits 8 frames, not 40**,
   before it says the object was lost there (`END_GAP`). Nothing checks what it
   finds out there but the strip; if the object comes back, a mark on it is a
   new seed, as it always was.
3. `tools/find_rank.py --keep DIR` keeps each case's marks and the detector's
   spots on every frame (~30 MB a case); **`--replay DIR` links again from them
   in about a second a case**, reading no frame. The link line now says how
   many frames are *off* the recorded track and the fastest step, because a
   median hid this: last session's table said "0.9 px on the 91 shared" for a
   link that was 23 of those 91 frames off.

Both numbers were chosen on every clip with a recorded track, in the middle of
where they change nothing: from 0.25 to 0.4 of the speed every case links the
same frames (0.2 loses one of PR149's, 0.5 takes one off it); an end wait
from 2 to 12 frames links the same frames everywhere, and at 15 PR055 creeps
on along cloud. `test_measurement: test_a_link_that_loses_the_object_does_not_
take_the_next_thing_it_sees` is PR055's two ends and PR149's ship, drawn, and
was run with the fix taken out: it fails both ways.

**The table** (Slurm job 250 kept the cases; before = `5cc1982`, the commit
Jacob had; after = this change, replayed):

| clip | link before | link now |
|---|---|---|
| **PR055 1007–1418 (Jacob's)** | 351 frames, 1007–1408; 23 of the 91 recorded frames more than 12 px off; fastest step 38 px a frame for a disc moving 2.5 | **142 frames, 1157–1298**, 0 off, 0.7 px median on the 68 shared; "lost before frame 1157 … lost after frame 1298" |
| PR055 957–1418 | 401 frames, 957–1408; 23 off | the same 142 frames |
| PR149 1–120 | 47 frames; **4 on things 100–160 px from the contact**, where it crosses the ship | 37 frames, 0 off, all 21 on-track frames kept; says it does not reach the marks on 34, 46, 54, 61, 69, 77 |
| PR142 130–290 | 98 frames, 7 off | unchanged (4 on the faint copy at 159, 172, 235, 242; 3 are recorded rows that are not the object) |
| PR144 300–500 | 201 of 201, 3 off (the disputed 384–390) | unchanged |
| PR113 380–440, 348–471 | 4 of 4, 0.0 px | unchanged; now also says lost before 408 and after 411 |
| PR148 140–440 | nothing (the detector's 25 spots) | unchanged |
| PR055 90–350 (×3 copy) | not on Find's list | — |

1157 is where the recorded track has the disc coming out of cloud (A186 → C1156,
"grey and soft first"); from ~1276 it fades dark-on-dark and by 1300 it is gone. The link is now
the disc, the whole of what can be seen of it on this leg, and nothing else.

**Now the detector's 25 spots a frame is three clips' limit, not one** — for
Jacob, "Next", 1d. `forensics.source_candidates` keeps the 25 strongest spots in
the whole frame. PR148: the object is never among them on many frames. PR149:
while the contact crosses the ship it is not among them (nearest kept spot
100–180 px away). PR055: the disc, fading, is 22nd, then gone. On PR149 and
PR055 the link used to take something else there; now it leaves a gap, and says
which mark it did not reach or where it lost the object. A link from marks could look for spots *near where the
object should be* instead of the frame's 25 strongest (the blind tracker would
keep its 25): the positions it measures would not move, and the gaps would
fill wherever the object is there to be seen. It changes what every linked
track is measured with, so it is his decision.

## "Find the object worked, but linking did not" — PR055 (2026-09-21 evening to 2026-09-22 morning)

Jacob opened PR055 whole (957–1418: the scene at its true size, a black disc 24
px across drifting 1.5 px a frame), pressed Find, took the first row, and the
link from its marks found nothing. Reproduced, and then held against every
clip with a recorded track — which turned up three more ways a proposal's
marks can be marks the linker cannot use, each on a different clip. **All of it
is about the marks**: Find's job is to hand the linker ten marks the package's
own detector has a spot under, within its 6 px.

1. **A slow thing's residual is its rim.** For a thing that moves less than its
   own width in 2k frames, "brighter or darker than both neighbours" is true
   at its leading and trailing edges, not its centre: PR055's marks were 11 px
   from the recorded centre and "about 5 pixels wide", and no spot size put a
   spot within 6 px of them. `propose.thing_at` now finds the compact thing in
   the *frame* that a peak belongs to — a small scale space about the peak, the
   strongest difference of Gaussians within a radius — and `_own_centres` uses
   those centres and that width for a proposal wherever they make a steadier
   track than the peaks (a small fast thing is the same either way). Drawn
   discs 8 to 72 px across, asked at their rim: centre within 4 px, width
   within 10 %. PR055: 1.3 px from the recorded track, "about 24 pixels wide".
2. **A point where the thing has faded is left out.** PR055's disc goes into a
   dark gap between clouds at ~1300 and cannot be seen in it; the chain ran six
   frames into the gap, the "thing" there was the gap (104 px wide, still), the
   last mark went on it, and the linker — which chooses its detector at the
   first and last marks — linked nothing. A point whose response is under 0.3
   of the median goes; and a later piece is joined to a thing only if it is
   *like* it (same polarity, width within two steps of the ladder).
3. **Beside it is not on it** (PR142). The object drags a fainter copy of
   itself a frame behind, 20 px back along the track. The copy's chain ran
   "within 30 px" of the object's, was folded into its row, and lent it frames
   — and the proposal's first two marks went on the copy, where the linker
   found nothing. Now only a piece that runs *on* a row (≤ 8 px) may lend it
   frames. Measured on the frames both have a point on; where they interleave,
   against the line between the row's points on either side — not a position
   interpolated by time, because
4. **a clip with repeated frames moves nothing on one frame and two steps on
   the next** (PR149), so interpolation put the same object 15–19 px "from"
   itself and left it in three rows (23 of 43 recorded frames covered, from
   38). And `_own_centres` judges smoothness against the line of each point's
   neighbours, not one parabola: PR142's object crosses 1800 px in a hundred
   uneven frames under a moving camera, and against a parabola whole stretches
   of a good track were thrown out. A stray point goes one at a time, on a
   median's scale.
5. **Pieces of one thing end as one row whatever order their scores put them
   in** (PR144: last, first and middle by score; the first joined neither, the
   middle joined the last, which then ran over the first to the pixel — two
   strong rows). `distinct` folds again until nothing more folds.
6. **The linker says which mark.** "No spot size … puts a spot within 6 pixels
   of the marks" now goes on: "The mark on frame 1316 is the one with no spot
   near it: go to that frame, and if the object cannot be seen there, delete
   that mark and link again" (or "neither the first mark nor the last", or
   "each has a spot near it, but not at the same spot size").

**The table, on the final code** (`tools/find_rank.py --link`, Slurm job 184,
2 CPUs, 2026-09-22 morning; "before" is `4051656`, the commit Jacob had when he
tried PR055):

| clip | Find: the recorded object is | before | link from its marks, now |
|---|---|---|---|
| PR149 1–120 | 1 of 137, strong 20 (next 0.5); on 37 of 43 recorded frames, 0.5 px | 1, strong 28 | 47 of 81 frames, 0.1 px median on the 25 shared; **misses the marks on 34, 54, 61** (see below) |
| PR144 300–500 | 1 of 400, strong 29 (next 0.5); 156 of 718, 0.4 px | 1, strong 27 | 201 of 201, 0.3 px |
| PR142 130–290 | 1 of 119, strong 21 (next 0.6); 75 of 131, 1.4 px | 1, strong 15 | 98 of 99, 0.9 px; **linked nothing before** |
| PR148 140–440 | 1 of 400, strong 16 (next 5.1); 128 of 252, 1.2 px | 1, strong 12 | **nothing, before and now** (see below) |
| PR113 380–440 | 1 of 116, weak 1.1 (next 0.57); 4 of 4, 3.1 px | 1, weak 1.1 | 4 of 4, 0.0 px |
| PR113 348–471 | 1 of 241, weak 1.1 (next 0.55) | 1 | 4 of 4, 0.0 px |
| PR055 957–1418 | 1 of 400, strong 12 (next 0.4); 52 of 91, 1.3 px | 1, strong 12, **but linked nothing** | 401 of 452 frames, 0.9 px on the 91 shared; runs on past where the disc is visible |
| PR055 90–350 (the ×3 copy, a 72 px disc) | not on the list | not on the list | — |

PR055, PR142 and PR144 are what Jacob would see fixed. PR113 is unchanged.
Two rows are honest failures, not of this work:

- **PR148 links nothing from Find's marks, before and now.** Find is 1.2 px
  from the recorded track; the package's detector (`forensics.
  source_candidates`) keeps the 25 strongest spots of a frame, and on PR148 —
  a ship, sea texture, a heading tape — the object is not among them on many
  frames: on frames 150 and 320 the nearest kept spot is 120–140 px away with
  the object plainly there (grey 44 against 95, nothing masked). *Not changed:
  that limit is in the code every linked track is measured with, and raising
  it is a decision about the detector, not about Find.* For Jacob.
- **PR149's link misses three of its ten marks** (34, 54, 61) and has one mark
  with no track under it: the contact crosses the ship there. The proposal
  itself is on the track; the link's behaviour on that stretch was the same in
  the first handoff's trial ("from two marks 51 frames apart it left the
  contact where that crosses the ship"). And one proposal point (frame 76) is
  22 px off — a stray a fast thing's loose gate lets in, not a seed.
- **PR055's link runs 957–1408 where the disc is seen in about 250 frames**:
  the linker looks on past the last mark and finds dark cloud to follow. The
  strip is where a person sees that. Nothing new; worth a "lost after" that
  looks at contrast, some day.

**Slurm** (Jacob set it up on 2026-09-21; his `slurm` skill has the facts).
`progress.cpus()` sizes every pool by the CPUs the process may run on
(affinity mask, `SLURM_CPUS_PER_TASK`), so a job's pools fit its allocation;
`autolink.default_procs` too. `tools/find_rank.py` is the table above as a
command (the recorded tracks are outside the repository: `MCDONALD_TRACKS`),
`tools/find_rank.sbatch` and `tools/suites.sbatch` run it and the suites as
jobs written to move to a cluster (no account/partition, `-n 1`, threads
pinned, `srun`). `logs/` is git-ignored. Both were run for this commit from a
snapshot of the tree.

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
   of the long steps in progress lines ("step 5 of 9 · Layers", on stderr
   too: since 2026-09-25 each is a 1–3 word technical name, at Jacob's ask), and the sentences the window shares with the
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

- **Answered 2026-09-22, then reversed on the evidence the same day: the link
  keeps the detector's 25 strongest spots a frame.** Asked whether a link from
  marks should be given every spot, Jacob chose every spot, marks only (my
  recommendation). Built (N_MAX) and re-run on every recorded clip (Slurm job
  350), it was worse: PR149 6 frames off its track and 3 disputed (from 0 and
  0), PR144 11 disputed (from 5), PR055 13 faint frames more at its ends, and
  PR148 **still nothing**. The link takes the spot nearest the prediction
  whatever its strength; with every spot, weak ones win wherever the object is
  a little off it (a repeated frame on PR149 puts it 32 px off). Shown the
  table, he chose to go back to 25. Nothing of it was committed.
- **Found on the way, and not fixed: the detector stops at the first spot near
  the edge of the frame — and the link depends on it.** `source_candidates`
  ends its search when the strongest spot left lies in the band 3 sizes wide at
  the edge (`break` where it means "skip"), and every weaker spot in the frame
  goes with it: 12 spots on a PR148 frame instead of 25. Without the bug,
  PR148's object is a spot within 1 px of both end marks — but 69th to 460th of
  900–2,258 specks of sea texture, so no count limit links it. Jacob said fix
  it and commit if the tests pass. Fixed (band left out before looking), and
  re-run (Slurm jobs 370, 371): PR149, PR144, PR055 unchanged; PR142 103 frames
  from 98, 8 off from 7; **PR113 from Find's marks chose 15 px instead of 21,
  3.6 px off the recorded track, 139.8 px/frame instead of 141.4** (published
  142); and **`test_measurement` failed 12 checks**: on the drawn clips the link
  ran on over sky texture where the object is not (1–46 for 11–30, 112 px off).
  The bug has been keeping every frame's list short, and the link — which takes
  the spot nearest the prediction, however weak — has been leaning on that.
  Reverted; nothing committed. The fix has to come with a rule that lets the
  link tell the object from texture (its strength and size at the marks), and
  `pick_detector`'s climb has to be looked at again (it stops at 15 px on PR113
  once 15 has a full list). `tools/find_rank.py --seeds` (kept) is how to test
  it: Find's saved marks, the detector run again, no Find.

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
- *New on 2026-09-23, not asked:* `groups` and `flicker` are stages of `run`,
  and so of the window's Measure, on every track (groups only for a thing linked
  at 9 px or less), not options -- about 0.4 s a frame between them, which the
  Measure panel now says past a minute; a track under 60 frames gives flicker a
  NO POWER line in every short case (PR113's four frames). The link's new
  numbers (`LIKE` 0.5, `NEAR` 10, `TIGHT` 2, `STRONGER` 5 %, `END_GAP` 2) are
  mine, from the recorded tracks, as `SHARE` and `END_GAP` were.
- *New on 2026-09-23 evening, not asked:* `symbology` is a stage of every `run`
  and Measure (after survey); the parallax ladder is two more rows of `KNOWN`
  (so two more Measure fields), and its NO POWER line is in every report without
  them; the defect map is a list of places named, never a mask taken out of a
  frame; a `--set` mark stays an agent's unless `--typed` says a person typed
  it; `find_rank.on` allows a third of a thing's width; the double difference at
  16 frames was built, found nothing more, and was taken out; `Case.result`
  stays as it is.
- *Not asked, confirmed 2026-09-27:* Measure starts on the frames round the track, not everything
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
- *Not asked; confirmed 2026-09-27:* `run` gained `--names` and `--dark-below` (layers' own), so the bottom line
  can say "against the sea", and `--size/--dark`.
- The window's track sheet is laid out six tiles across (`measure_qt.
  sheet_layout`), not the command line's thirty: thirty is one 11,520 px row to
  scroll sideways. What the sheet measures does not depend on it, and the test
  that compares the window's case with the command line's compares fields.
- A sheet closed without an answer is "no". The default button is "No, or I
  cannot tell".

## Next, in the order I would do it

*Superseded on 2026-09-26 by the Roadmap at the top of this file; kept for the record.*

Everything that was on this list on 2026-09-23 is done or answered (the first
section); what the record of each item said is in the git history of this file.
What is left:

1. **Jacob's word on the polish, then Ravi (macOS) and Gary Nolan (Windows).**
   For a Mac: the menu roles (only "Save and quit" may move to the application
   menu), single-letter shortcuts in a native menu bar, tool windows,
   `QStandardPaths`, the process pools under spawn, `QDesktopServices.openUrl`
   (the report page now opens pictures with it too), `gui.desktop_entry`
   refusing with a sentence. For Windows as well: backslashes and drive letters
   in `_flags` and the case folder, `spawn` (chosen on win32 in
   `autolink._Workers`), ffmpeg on the PATH, a deep `%TEMP%` (a long `TMPDIR`
   broke the pools here: "AF_UNIX path too long"). Nothing has run on either.
   Downloads (2026-09-24) use urllib: a python.org Python on macOS has no
   certificates until its "Install Certificates.command" is run, and then every
   download fails with CERTIFICATE_VERIFY_FAILED -- say so, or fall back to
   `curl`, which macOS and Windows 10+ both have.
   **How it ships (Jacob, 2026-09-24): no money spent.** Testers install with
   pip from GitHub (the repo is private: add them as collaborators, or make it
   public) and ffmpeg from brew/winget. CI: a GitHub Actions workflow run by
   hand, within the free minutes (private repo: 2,000/month, macOS counts x10,
   Windows x2; the $0 spending limit stops it rather than charging), running
   reduction, published and cli on macOS and Windows, measurement and gui if
   time allows. No Apple developer account, no signing certificate; a bundled
   app, if ever, unsigned, with the one-time "Open Anyway"/"Run anyway" said.
   Next session: Jacob wants to polish the GUI first, before sharing with Ravi.
2. **Jacob's hand**: the player, Find and the progress bar he has used; the new
   things he has not -- the report page's pictures and its "I have looked at the
   track sheet now", the two parallax fields in the Measure form (the form is
   now thirteen fields: too many?), symbology in every Measure.
3. **PR055's enlarged copy does not link** from Find's marks: the detector's
   sizes stop at 45 px and the disc is 74. Adding 71 to `autolink.SIZES` is a
   change to what every link from marks chooses among -- hold it against
   `find_rank --replay --pick` on `keep_final` (below) and golden.
4. The decisions above (Decisions) marked *not asked* -- his to confirm or reverse.

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
- **Find's marks are for the linker, and "on the object" is not enough.** A
  mark on the rim of the thing (PR055), on a faint copy of it (PR142) or where
  it has faded (PR055 again) is 1–20 px from the thing and the linker's gate
  is 6 px. Rank tables must link, too: `tools/find_rank.py --link`.
- **Interpolating by time is wrong on a clip with repeated frames.** PR149
  moves 0 px on one frame and 40 on the next; a position "at frame n" from
  its neighbours is one step off. Compare on frames both have a point on, or
  against the line between points, never against a time-interpolated one.
- **One pass over a list whose order is by score can leave one thing in two
  rows.** Fold until nothing more folds (PR144).
- **A 4-CPU job at default priority blocks a whole array of 1-CPU tasks.**
  Job 64 sat on "Resources" waiting for two more CPUs while two sat idle and
  Jacob's pending tasks, which needed one each, waited behind it. Ask for what
  is free (`sinfo -o %C`), or `--nice` it below his; he said, later, that mine
  may go first — ask, each time.
- **`test_gui` in a 2-CPU job skips everything**: "hung before a window opened",
  every backend. Four CPUs and it passes. One playback-timing check ("in 0.45 s
  at 1x it advances 0.45 s of frames") failed once in a 4-CPU job on a loaded
  machine and passed on the rerun: it measures wall-clock time.
- **Keep the per-frame peaks of a Find and replay the rest.** The residual of
  every frame is the slow half (~3.5 s a frame on one core); chains, joining,
  scoring and folding are seconds. Every rule above was found and checked
  that way, on one desktop core, while Jacob's jobs had the rest.
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
- **A median distance hides a link that jumped.** "0.9 px on the 91 shared" was
  PR055's link, 23 of those 91 frames off and 209 frames on cloud where nothing
  was recorded to compare. Count the frames off, and look at the fastest step
  against the median one (`tools/find_rank.py` does both now).
- **A gate made for not knowing the velocity is too wide for a link that
  knows it.** 12 px more per unseen frame is right for the blind tracker and
  gave a disc moving 2.5 px a frame a 205 px gate after fifteen frames. And
  strength does not rescue it: fading, PR055's disc answers the detector
  exactly as the cloud does.
- **Keep the candidates and replay the linker.** A link is seconds once the
  detector's spots are kept (`--keep`, `--replay`); the detector is the hour.
  Every number in the gate change was chosen by sweeping replays over all the
  cases, and each is in the middle of a range that changes nothing.
- **Reproduce the person's case exactly before believing a fix for it.** Job
  250 ran Find on Jacob's range and got his ten marks and his 351 points to
  0.007 px; only then was the replay his case and not a likeness of it.
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

- **2026-09-23 evening (the leftovers):** one commit, pushed. Suites as above
  (jobs 998 and 1016, from a snapshot). Find's table on the final code (job
  997) is kept with every spot for replays:
  `/scratch/tmp/claude-1000/-hugespace-models-mcdonald/leftovers-20260923/keep_final`
  (373 MB; `final_rank_997.txt` beside it) -- `python3 tools/find_rank.py
  --replay <that>`; the older `keep5` and `linkgate-20260922/keep` stay as the
  last handoff says. Removed: the session's frames, snapshots and the suites'
  frames under `/scratch/tmp/mcl*`, and the defect maps it cached in the agent's
  PR135 frame folder. `/tmp` holds nothing of this session's (`/tmp/mcdonald`
  is Jacob's three folders, as before; the nineteen `/tmp/pymp-*` are older).
  `MCDONALD_CATALOG` is not set in this shell: a Slurm job that resolves ids
  (find_rank, golden) needs it exported
  (`/hugespace/local/research/uap/pursue_index/records.csv`) -- the first
  rank jobs of the session had to be resubmitted with it.

- `main` is pushed and clean. Commits since the first session of 2026-09-21:
  `46e91e1` (the player), `ed21a1b` (plain words), `4051656` (Find on PR113: a
  spot or an edge; Show more), `ba03db7` (handoff: PR113 confirmed), `d0b989b`
  (Find's marks for the linker: PR055, PR142, PR144, PR149; the linker says
  which mark; pools follow the allocation; `tools/find_rank.py` and the two
  sbatch scripts), `5cc1982` (handoff: /tmp cleared), and the one that carries
  this file (2026-09-22: the link's gate and end wait; `find_rank --keep/
  --replay`).
- **2026-09-22, the link-gate session:** suites all passing on the final tree,
  Slurm job 284 (4 CPUs, from a snapshot): `test_measurement` 138 (was 131:
  PR055's two ends and PR149's ship, drawn, and the same with the fix taken
  out), `test_reduction` 97, `test_published` 32, `test_cli` 51, `test_gui` 441
  (WxAgg skips), `test_golden` 12 — PR113 from two clicks on the same four
  frames, 0.005 px from the vendored track, 141.4 px/frame; PR144 599.379 /
  500.243 / 99.1534, unchanged. Logs in `logs/` (git-ignored). The table at the top:
  Slurm job 250 (3 CPUs, from a snapshot, niced) kept the cases; the "now"
  column is `find_rank.py --replay` on the final tree. Job 250 was cancelled
  during its last case, PR055 90–350, which Find does not list either way.
- Suites, all passing on the final tree, as Slurm job 185 (4 CPUs, from a
  snapshot): `test_measurement` 131 checks (was 115: the slow disc, the faded
  point, the unlike piece, beside-not-on, the winding track, the stray point,
  the three pieces, which mark, pools), `test_reduction` 97, `test_published`
  32, `test_cli` 51, `test_gui` 441 with only WxAgg skipping. `test_golden` was
  run on 2026-09-21 and no measuring module has changed since (`progress.
  pooled` only caps the pool's size).
- The table at the top: Slurm job 184 on the same snapshot.
- Real trials of the window by Jacob: Measure on PR113 (2026-09-21 morning);
  Find on PR144 end to end, and on PR113 ("it works now"); the player ("a nice
  feel"); Find on PR055, where the link failed (fixed `d0b989b`); PR055 again on
  2026-09-22, where the link ran past the disc onto cloud — the fix at the top,
  not yet in his hands. His saved case is `~/Documents/mcdonald/pr055/`
  (untouched: its `_autotrack.csv` is still the old link until he links and
  saves again), and his frames for it are `/tmp/mcdonald/DOD_111719732`
  (1007–1418, his, left in place).
- Environment: as before, plus Slurm 24.05 on this machine (`~/.claude/skills/
  slurm` is Jacob's, and says what to do; `bash ~/.claude/skills/slurm/
  scripts/status.sh` first). `MCDONALD_CATALOG` is **not** exported in a fresh
  shell: `export MCDONALD_CATALOG=/hugespace/local/research/uap/pursue_index/
  records.csv`. The recorded tracks for the table are in
  `/hugespace/local/research/uap/analysis/` (`MCDONALD_TRACKS`).
- `/tmp` at the end of the session: **empty of mcdonald.** Jacob asked for the
  files in `/tmp` to be removed, so the whole shared frame cache went — his
  PR113 (5291 frames, 2.1 GB), PR144 98–194 and PR055 957–1418 included; the
  next open of any of them extracts again (the player asks which part, so
  that is minutes, not the whole clip). The session's own frames for the table
  (1.6 GB, six clips), snapshots and logs were removed too. The two Slurm
  jobs' output (the table, the suites) is kept in `logs/` in the repository,
  which is git-ignored.
- `/tmp` at the end of the 2026-09-22 link-gate session: what the session put
  there is gone — `test_golden`'s PR113 400–420 and PR144 300–500 frames, and
  the socket directory of the job that was cancelled. `/tmp/mcdonald` holds
  only Jacob's: `DOD_111719732` 1007–1418 (412 frames, 279 MB, from his PR055
  trial) and an empty `DOD_111689022` (PR35), both made before the session
  began, both left. Later that day the edge-bug jobs' `test_golden` frames
  (PR113, PR144) and a pool's socket directory were removed too;
  `DOD_111985782` (PR135, 14:14) is from Jacob's own PR135 work, and left. On `/scratch` (a hard drive, not RAM) the frames and
  snapshots are removed and **the kept cases are left**:
  `/scratch/tmp/claude-1000/-hugespace-models-mcdonald/linkgate-20260922/keep`,
  252 MB, eight cases (PR055 90–350 was not reached). `python3
  tools/find_rank.py --replay <that>` re-links them all in about ten seconds —
  good for any change to `autolink`, not for a change to the detector or to
  Find. Jacob's tmpfiles rule deletes it after 30 days untouched.
- `/tmp` after the PR135 `layers` session (2026-09-22, evening): `test_golden`'s
  PR113 and PR144 frames removed; `/tmp/mcdonald` holds the same three as
  before (`DOD_111689022`, `DOD_111719732`, `DOD_111985782`). The agent's PR135
  frames and its template cache stay in `/scratch/tmp/pr135_mc` (a hard disk);
  the two caches this session added there are removed. Empty `/tmp/pymp-*`
  directories were left: Jacob's `eth_table` array was running beside them.
- `/tmp` after the agent's-small-items session (2026-09-23): this session left
  nothing there. `/tmp/mcdonald` holds the same three as before:
  `DOD_111689022` (empty), `DOD_111719732` (279 MB, Jacob's PR055) and
  `DOD_111985782` (24 MB, Jacob's PR135). Nineteen empty `/tmp/pymp-*`
  directories (2026-09-15 to 09-22, none from this session) are left alone:
  Jacob's `eth_table` array (job 87) is running. `/scratch/tmp/pr135_mc` (the
  agent's) and the link-gate `keep` cases are as before.
- **2026-09-23, the five things Jacob chose** (the first section): commits
  `ac5bf7e` (the template's peak), `8035967` (the blur), `c05f222` (the edge
  bug and the local link), `942f4b9` (groups) and `b49b26d` (flicker), each
  with its suites run on it alone (Slurm jobs 857, 866, 903, 911, 912; the
  last three with golden). Suites now (job 912): measurement 163, reduction
  120, published 32, cli 54, gui 442 + the old WxAgg skip, golden 12 -- PR113
  141.4 px/frame from two clicks, PR144 599.379 / 500.243 / 99.1534. `/tmp` after it: this session left nothing there;
  `/tmp/mcdonald` holds the same three folders (Jacob's); the nineteen empty
  `/tmp/pymp-*` are not this session's. On `/scratch`: **the eight recorded
  cases kept with every spot**, `/scratch/tmp/claude-1000/-hugespace-models-
  mcdonald/polish-20260923/keep5` (341 MB) -- `python3 tools/find_rank.py --replay
  <that>` re-links all eight in about a minute with whatever `autolink` is,
  and `--pick` chooses the size again; the replay of the committed code is
  `final_replay.txt` beside it. A change to the *detector* needs the spots
  found again: `sbatch tools/find_rank.sbatch --link --seeds <linkgate-20260922/keep>
  --keep NEW` (Find's marks from 09-22, about an hour on 4 CPUs), so that older
  folder (252 MB) is kept too. Keep `TMPDIR` short for it (a long one broke the
  pools: "AF_UNIX path too long"). Everything else of the session's there
  (frames, snapshots, worktrees, the suites' frames in `/scratch/tmp/mcg*`) was
  removed. Jacob's tmpfiles rule deletes what is left after 30 days untouched.
- Not done, on purpose: the ×3 copy of PR055 (k); the case report in plain words
  ("Next", 3b); playing backward in the main window; macOS and Windows (Jacob's
  word first). Done since: a link that stops when the thing fades (PR055); the
  detector's edge bug and the link near the marks' path (PR148 links).
