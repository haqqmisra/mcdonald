# Handoff: the fine-tuning round on branch `tune` (2026-11-22)

Jacob, 2026-11-22, after analysing PR169 (DOD_112158018) in the window at 0.5.9:

> Let's fine-tune some parts of mcdonald. Other sessions are also developing, so go ahead and coordinate. Nobody
> should do a version push until I confirm, as I will want to do some GUI tweaks before the next version.
>
> I analyzed PR169 with the GUI. It finds the single object as two different objects. Is it possible for find to
> understand that this is one object with a single track?
>
> I tried "open a new clip" and specifying 1 as the number of objects; but it still found 2. However, this could be
> because the old report was still present. It may be helpful for the user to have a way to "clear" the memory of a
> specific case, if they want to start over.
>
> Once these are resolved, then I think Exercise 1 should be replaced by PR169, as it is much shorter and a good case
> to highlight.
>
> The Yes/No questions and answers should only appear on the full report and not on the summary box on the
> right-hand pane; it is too long/cluttered otherwise.

- Everything is on the branch **`tune`** (worktree `/hugespace/models/mcdonald-tune`), made from `main` 6aa845b
  (0.5.9 and the site's commits). **Nothing is pushed, tagged or versioned: the version is still 0.5.9, and the
  version push waits for Jacob's word** (the other sessions were told: `amateur`/`am-sky` and `audio-paper`).
- **`main` was fast-forwarded to `tune` on 2026-11-22, late afternoon** (local only), on Jacob's word as the
  audio-paper session relayed it ("work with the other agents to merge the tune branch"). The tested commit is
  5691539; the commits after it on `tune` change this file alone. A window opened before the merge runs the old code
  until it is started again (one had been open, idle, since 2026-11-20).
- The same Find change is on **`tune-06`** (worktree `/hugespace/models/mcdonald-tune-06`), made from `amateur`
  0c55fa5, so that the 0.6 line has it when it is next brought together. `amateur`, `dev-0.6` and `audio-paper`
  were not touched.
- Scratch: `/scratch/mcdonald/tune-2026-11-22/` (`COORDINATOR.md`, the rules; `briefs/window.md`; `find/`, `runs/`,
  `ex1/`, `scripts/`, `snap/`).
- **Decisions for Jacob are at the end.**

## What happened on PR169, and why

PR169 is 13.6 s of one bird that an infrared camera follows through two turns. Find's rows are chains at a steady
velocity. Where the bird turns it is slow on the screen, the search loses it, and the chain after the turn is not
where the chain before was heading. So Find listed three rows (frames 261-406, 68-251, 3-39), all at least "fair", and
the one press followed every row that is at least fair: three objects, three reports. The list afterwards said that
object 2 was object 1 and counted object 3, which shares no frame with object 1, as a second object: "2 were
followed".

The second run, asked for 1 object, was not a new run. A folder with `object-N` folders in it makes the button say
"Measure again", and that press measured the three old folders again whatever count was given
(`auto_qt.AutoRun._next`).

## On `tune` now

| what | where | held to |
|---|---|---|
| **Find lists an object once where it turns** (TU1). Two rows that could be one object -- alike, one after the other, 60 frames apart at most -- are put to the package's own link, started from the end of the earlier with no mark ahead of it. Where it arrives on the later row's first mark, and back from the later on the earlier's last, the better row is lent the other's frames and the other leaves the list. The row says so ("found 3 separate times (frames 3–39, 68–251, 261–406) and taken as one object, because the spot can be followed from each into the next"), has `pieces`, and its marks are placed in every stretch | `propose.joined`, `link_reaches`, `one_after_another`, `Proposal.seeds`/`pieces`; `search(join=True)`; method §110 | PR169: one row, frames 3-406; the link from its marks follows 396 of 408 frames, 1-408, within 1 px of each of Jacob's three tracks of 2026-11-21. The Find benchmark's development part (441 clips): 566 pairs asked, 25 joined, each one object; first row 190 -> 190 (infrared) and 163 -> 164 (visible), no object's place lower; flyers 5 of 5; Find 4 % longer. `find_rank --link`: the 11 cases' lines the same. 11 checks on drawn clips (a spot that turns; one that is gone while it turns; another that comes up beside it) |
| **Exercise 1 is PR169** (TU5): the whole 14-second video, about 5 to 10 minutes in place of 25 to 35 | `docs/exercises/01-pr169.md` (01-pr44.md removed), the exercises' list, README, the site's menu, the issue form | `test_golden --exercises 01` (below) |
| **The shipped list of PURSUE videos has release 08's three** (PR166, PR168, PR169), so a tester can open PR169 by name | `src/mcdonald/pursue_videos.csv` (`tools/ship_catalog.py`); the three videos added to `/models/data/mcdonald/pursue/` with its README and SHA256SUMS | each size on DVIDS equals the mirror's copy; LLE-UAP-PR004's title follows the release's own change |
| The beat figure's title no longer runs off the figure where a beat has a double ("5.93 Hz (double 11.86)") | `figures.py` | seen on PR169 |

The window strand's rows are in "The window" below.

## The numbers behind the Find change

All in `/scratch/mcdonald/tune-2026-11-22/runs/` (`join-v2-main` is the setting kept; `join-v1-main` the first
pre-filter; `join-v2-main/g150` the longer gap; `join-v2-06` the 0.6 line), scripts in `scripts/` (`join_eval.py`
runs Find once a clip and keeps the list before and after the step and every pair asked; `join_pairs.py` holds the
pairs against the labels; `dupes.py` counts what the one press would follow twice). Development part only: the
held-out third was not run.

| | main's Find (`tune`) | the 0.6 line's Find (`tune-06`) |
|---|---|---|
| pairs asked / joined | 566 / 25 | 581 / 27 |
| joined, on the same labelled object | 20 | 20 |
| joined, other | 5: one bird whose label changes number (V_BIRD_015), one followed by eye across 12 unlabelled frames (V_BIRD_008), two from unlabelled frames onto the labelled track (V_AIRPLANE_020, V_BIRD_014), two rows on one group of ground lights (IR_AIRPLANE_049) | 7: the same five, and two pairs of weak rows on nothing that stay in place (IR_BIRD_002, V_HELICOPTER_003) |
| first row on the object, infrared | 190 -> 190 of 294 | 212 -> 212 |
| first row on the object, visible | 163 -> 164 of 286 | 167 -> 168 |
| shortlist, infrared / visible | 238 -> 239 / 248 -> 248 | 253 -> 254 / 245 -> 245 |
| an object's place lower | none | none |
| first row's output on nothing, infrared | 0.0277 -> 0.0281 a frame (30 positions, one clip whose first row was on ground lights before) | 0.0166 -> 0.0170 (the same clip) |
| first row's output on nothing, visible | 0.0228 -> 0.0228 | 0.0224 -> 0.0224 |
| labelled objects the one press would follow twice | 23 -> 18 of 418 | 20 -> 16 of 445 |
| the step's share of Find's time | 4.1 % | 4.9 % |

What is still followed twice, of those 18: ten helicopters and an airplane found as several parts at the same time
(a different problem: parts of one large body), and seven small objects whose pieces are more than 60 frames apart
or have frames between them where the spot is not seen.

Two bounds were each tried at one other value (method §110): the reach from the rows' own speeds (too tight for a
camera that centres its target again: 20 joins in place of 25), and a gap of 150 frames (38 joins, but a helicopter
lost its shortlist row to a join across 64 frames), so 60 stands.

## The window (the strand `tune-window`, an agent's; merged as 11798aa and 5dbea30)

Its own notes, with every job and every sentence a person reads, are
`/scratch/mcdonald/tune-2026-11-22/window/NOTES.md`; the method notes are sections 111 and 112.

| what | where | held to |
|---|---|---|
| **The report's card without the Yes/No rows** (TU4): the conclusion, the track's banner, "Add what you know", the numbers found, More, Full report, Folder. The table of tests is in the full report, as before; `run --json` and `report --json` keep `checklist` | `report_qt.ReportCard` | test_gui; seen on PR169 in the real window (the card fits the column: `/scratch/mcdonald/tune-2026-11-22/ex1/window-merged-fresh/window_*.png`) |
| **`mcdonald clear DIR`** (TU3): a case's results set aside in `earlier/<date>_<time>/` inside the results folder -- every file named for the case and every `object-N` folder; nothing deleted unless `--delete`; `--dry-run` lists; the zoom states and a shared file's thread stay | `clear.py` (`set_aside`), `cli.COMMANDS`; method §111 | test_cli (the folder's listing before is the dated folder's after); a copy of Jacob's PR169 folder: 2 files and 3 object folders set aside |
| **Start over in the window** (TU3): a quiet button at the foot of the one button's card, and File → Start this segment over…; it asks in the card ("Start over? The marks, tracks and reports saved for this segment will be set aside in a folder named earlier. Nothing is deleted, and the video stays open." / Keep them / Start over); after it the window is as when the video was first opened, and one line says where the results went | `auto_qt.AutoCard`, `QtMarker.start_over`/`begin_again`, `actions` | test_gui; PR169 in the real window: 26 files into `earlier/2026-11-22_1224`, the button back to Begin, no marks, no track, no card |
| **The one press keeps to the count said** (TU2): where everything saved is the press's own choice and the count said now is another (or more objects are saved than are looked for), the button says Begin and the press starts over by itself, then says where the old results went. A person's or an agent's choice is never set aside this way | `auto_qt.AutoRun.outdated`, `_next`; the table of cases in method §111 | test_gui; a copy of Jacob's own folder (three objects, the list saying 1), opened with 1 said: Begin, the old results set aside, Find afresh, one object and one report |
| **Two found objects said to be the same one** (TU6; Jacob during the round): on each object's card a quiet "Same object as…" (a choice of the other objects, Join them, Cancel, in the card); at Find's list, with two or more rows ticked, "They are one object"; `mcdonald run VIDEO --each DIR --same 1,2`. The lower-numbered object keeps all their marks, each recorded as it was, with who said they are one and when; the old folders are set aside; the one object is followed and measured; its report says above the conclusion that it was made one on a person's say and what the track did where the marks of one meet the next's ("passes through the marks of both", or "The track does not join them", with the frames), and "No test here checks that they are one object. Look at the track sheet." | `several.join`, `MarkSet.joined`, `stages.seams`, `report.made_one_said`, `report_qt.ReportCard`, `find_qt`, `run.py`; method §112 | test_cli, test_gui; Jacob's three PR169 objects of 2026-11-21 made one from the command line (below) |

Found by the agent on the way, not changed: the count is remembered for a video, not for a segment; a clip of 900
frames or fewer whose frames are saved opens without the segment step, so the count can only be said again through
File → Another segment of this video…; `several.index` writes the list again under the count said now, which is how
a list came to record a count its objects were not chosen for.

## After the round was reported: two more requests (2026-11-22, afternoon)

Jacob: "Can you also polish up the report? In particular, can you make the plots more embedded into the report? Right
now the white border of the plot makes it look like it was pasted in. Either make a transparent background for the
figures that shows up against the background, or just make the background color of the report white. Second request:
make sure any of the yellow box "hover over" text is one short sentence at most".

| what | where | held to |
|---|---|---|
| **The report's page is a sheet of paper in the window** (TU8): dark ink on white, the saved PDF's colours, so a plot's white is the page's and nothing frames it. (A transparent plot would have put its black ink on the dark page: the plots are drawn for paper.) Each picture is centred, with its caption close under it in smaller, quieter type. The list of objects and the sound's page are paper too; Help and the rest of the window stay dark | `mark_qt.ReadingView(paper=True)`, `paper.dress` (`SHEET`, `INK`, `FAINT`), `measure_qt.render`, `several_qt`, `sound_qt`; commit f0684d7 | test_gui 836 -> 841 (job 19297): the page white behind dark ink, a plot's corner pixel the page's colour, every picture centred, the list and the sound's page paper, Help not; seen on PR169's report in the real window (`scripts/report169.py`, `ex1/report-i/*.png` in the scratch folder) |
| **The conclusion as one card**: one frame round its lines in place of a band behind each paragraph, which had left stripes of page between them (plain to see on white); on the page and in the PDF | `paper.dress`; commit fea90ac | test_gui 841, test_cli 164, test_share 31 (job 19302); seen on the page and in the PDF's first page |
| **Every tooltip in the window is one short sentence at most** (TU7; the window strand's Job D): 15 words at most, one line, no second sentence, no chain of clauses on a colon or a semicolon, no table or list; a key or a command's option in parentheses at its end is not counted. 238 tooltips read, 178 rewritten. A menu row's long `help` stays where long is right (the status bar, Help → Keys and mouse, `mark --help`) and has a short form for the hover (`actions.TIPS`, `actions.tip`). The report card's rows now say what each number is, not how it was found (`report_qt.GLOSS`); the full report says how | `actions`, `stages.tip`, `known_qt.TIPS`, `report_qt`, `mark_qt`, `measure_qt` (`STAGE_WORDS`), `find_qt`, `several_qt`, `share_qt`, `sound_qt`, `auto_qt`; commit 0cfa22a, merged as 012a05a | test_gui: at every check of every driver each of the package's windows is walked (every widget, action, table cell, list row and choice) and no tooltip seen may break the rule (26 checks), and with no window the rule is held on every `setToolTip` string in the source and every table of tips (5 checks). On PR169 in the real window, four states: 74 different tooltips, none breaks it (`scripts/tips169.py`). **The table of every tooltip before and after, for Jacob to read and change: `/scratch/mcdonald/tune-2026-11-22/tips/tooltips.tsv`** |
| **The window draws its figures as files on Linux too**: inside the Qt window's process `figures.setup` now takes matplotlib's Agg whatever display there is. With a display it had taken the Qt backend, and every figure built a hidden window and toolbar of matplotlib's on the thread that measures (found by the tooltip walk, which met their tooltips; reading them while one was made left a stopped measuring hanging once in three runs). No figure changes; a Mac and Windows always drew this way | `figures.setup` | test_gui: after the window measured, the backend is Agg and no window of matplotlib's exists |

**Checks after the afternoon's work.**

- `tune` 5691539 (the commit `main` is fast-forwarded to): every suite with the footage, job 19321: ALL SUITES
  PASS, 29 suites, 4,451 checks, 0 FAIL (test_gui 873 with 1 SKIP, test_cli 164, test_measurement 722, test_golden
  266).
  Before it, on 012a05a (the white page, the card, the tooltips; job 19313): ALL SUITES PASS, 29 suites, test_gui
  872 with 1 SKIP; and test_gui alone with the figures' fix (job 19315): 873 with 1 SKIP. Against the round's end
  (51b3528, job 19230, test_gui 836): the paper page's 5 checks, the tooltips' 31 and the figures' 1; every other suite
  the same count.
- `tune-06` d02cd36 (the same work on the 0.6 line; 350231f adds one tooltip's words): ALL SUITES PASS, 32 suites, on
  CPUs (job 19318) and on the card (job 19319): test_gui 879 with 1 SKIP on both, test_golden 266, test_gpu 203 with 1
  SKIP and 276. One tooltip of that line's own broke the new rule and was shortened (Preferences' "Find searches the
  frames" box).
- The window strand's own run on `tune-tips` 0cfa22a (job 19312): ALL SUITES PASS, 29 suites.
- In the real window on a virtual screen, PR169: the report's page (`ex1/report-i/*.png`) and 74 different tooltips
  over four states, none over the rule (`scripts/tips169.py`).

**For Jacob, from the afternoon:**

- The tooltips' words are yours: the table is `/scratch/mcdonald/tune-2026-11-22/tips/tooltips.tsv` (where, before,
  after). A tooltip changed to more than 15 words, to two sentences or to a chain on a colon or a semicolon fails
  test_gui; relax `tip_breaks` in tests/test_gui.py if the rule should be looser.
- The report card's rows now say on hover what each number is, not how it was found (the full report says how). If
  you would rather they say nothing, `report_qt.gloss` can return "".
- The segment step's Shortcuts button still shows its table of keys in a box when pressed (not on hover).
- The jewels under a working bar name on hover only the bar under way ("…, 2 of 3"); they listed every bar.
- The tooltips' box is yellow because Qt draws tooltips with a palette of its own; the window's dark colours for it
  (`ToolTipBase`, `ToolTipText` in `mark_qt.application`) are not used. `QToolTip.setPalette` would make it the
  window's. Not changed: you did not ask.
- Not fixed, seen by the window strand: a Preferences page opened while an earlier look for devices is still running
  can show that look's result (the test now waits; the window does not).

## The next day: the card's conclusion in one sentence (2026-11-23)

Jacob, with the merged window open: "This is looking good! For the summary on the right-hand pane, underneath the
"Beats like a bird" headline: the text is too long, and all of this text is already included in the full report. Can
you condense this down to a single short sentence? This should be for all verdicts. -- Also the line "It's real speed
needs": is it possible to shorten this sentence to save some space?"

- **One short sentence under the label** (IDEAS TU9). `report.Case.in_short`, made in the same pass as the label and
  the full conclusion (`Case._concluded` returns the three; `conclusion()` is its first two, as before, so no caller
  changed). The rule for which sentence: the beat where a bird is named; else how the object moved; else the first of
  whatever else was found. Each as the card says it:

  | Label | The card's sentence |
  |---|---|
  | Beats like a bird | Its brightness rises and falls 5.9 times a second, the rate of a wingbeat. |
  | Beats like a bird (a flock) | Its 6 members each beat 7.1–8.0 times a second, the rate of a wingbeat. |
  | No physical conclusion | The object moved about 72 pixels a second across the picture. (or "in the picture, as the camera held it", or "against the background") |
  | Indeterminate, range needed | The object crossed the view at about 130° a second. |
  | Indeterminate, angle needed; Supersonic motion | At the given 3 km, it moves at least 6,800 m/s across the line of sight (Mach 20). |
  | Subsonic or Supersonic motion, an angle given | At the given 100 m, it moves about 260 m/s as the camera held it (Mach 0.76). |
  | Subsonic motion, a farthest range | No farther than the given 5 km, it moves at most 260 m/s across the line of sight (Mach 0.76). |
  | Subsonic motion, a reference object | No farther than the reference object, it moved at most 115 m/s across the line of sight (Mach 0.34). |
  | the same, with a range ratio | At 2 times the reference object's distance, it moved about 115 m/s across the line of sight (Mach 0.34). |
  | Conclusion, the camera held it at a given distance | At the given 100 m, it is about 1.1 m across. |
  | Conclusion, a speed alone | The object moved about 250 m/s as the camera held it, with the given range and scale. |
  | Conclusion, a beat that names no bird | Its brightness beats 7.1 times a second, too faintly to name a bird. (or "in one stretch only, too little to name a bird", or "but the whole picture shakes at that rate too") |
  | No conclusion yet | The measuring was stopped during layers, so the steps after it did not run. |
  | No conclusion | No object was tracked, so nothing here measures one. (or "No step produced a result.", "Nothing was measured about the object.") |

  At most 20 words (`report.IN_SHORT_WORDS`; the speeds at a distance are the longest, 17 to 20), one sentence, no
  colon or semicolon chain (`report.short_breaks`). The full report is unchanged, to the letter.
- **"Its real speed needs…"**: was "Its real speed needs the horizontal field of view and the distance to the object,
  or the physical length of a reference in the picture. Do you know any of these?" (31 words, seven lines beside the
  button). Now "Its real speed needs the field of view and the distance, or a reference object of known size." (17
  words, four lines), and with one of the two given, "…needs the distance, or…" or "…needs the field of view, or…".
  The button beside it asks, and its form names each quantity in full, so the question went.
- **Measured on PR169's card** in the real window on a virtual screen (`scripts/card169.py`, the same saved results
  under both codes): the sentence 180 -> 36 pixels tall, the box 142 -> 88, the card 827 -> 629.
- **For agents:** `conclusion.in_short` in `run --json`, `report --json` and the objects' list, beside `label` and
  `headline` (docs/agents.md).
- **Held by:** test_reduction's last check by name (`test_with_every_conclusion_goes_one_short_sentence`) walks every
  conclusion the suite makes, 51 different sentences over every label, and exact words beside the existing checks of
  each verdict; test_gui reads every report card it shows, at every check, with the tooltips; test_cli holds the new
  field. Adding the reduction check moved no other check to another part: its name sorts last.
- **Not on the card any more, and Jacob's to weigh:** the conclusion's other sentences. Most are detail (the
  look-alikes, the size at a distance). One is a warning: "N integrity checks flag it as possibly added to the video".
  The card's rows do not carry it, and the Yes/No rows that did came off the card on 2026-11-22. The one press skips
  integrity, so the window meets it only after Advanced Mode's Measure with integrity ticked. Decision 12 below.

## Checks on the merged tree

**`tune` 5dbea30** (everything of the round; a snapshot in `/scratch/mcdonald/tune-2026-11-22/snap/tune-e`).

- *Every suite, with the footage* (job 19230, 4 CPUs): ALL SUITES PASS, 29 suites, 4,414 checks, 0 FAIL. Against
  `main` 6aa845b (job 18275, 4,340 checks): test_measurement 711 -> 722 (the joining step's 11), test_cli 140 -> 164
  (`clear` 15, `--same` 9), test_gui 797 -> 836 with 1 SKIP on both (WxAgg, not installed); every other suite the
  same count: test_reduction 734, test_drift 373, test_controls 118, test_published 32, test_tether 78, test_audio
  65, test_share 31, test_sweep 20, test_batch 74, test_stabilize 13, test_aspect 10, test_waves 14, test_slew 95,
  test_zoom 39, test_horizon 39, test_focus 19, test_haze 9, test_streak 20, test_camera 152, test_beat 72,
  test_gpu 137, test_unknowns 105, test_plant 83, test_noise 29, test_rank 65, test_golden 266.
- *Exercise 1 as its page writes it* (`test_golden.py --exercises 01`, job 18992; on `tune-06`, job 19166): ALL PASS
  on both lines -- the line `look` prints, "396 of 408 frames linked, 1–408", and the report's first lines.
- *The real window on a virtual screen* (`scripts/window169.py` in the scratch folder; jobs 19168, 19169, 19274):
  - PR169 opened new, Begin: Find 34 s, Follow 10 s, Measure 106 s on 8 CPUs; one object, no object folders, a track
    on 396 frames (1-408), one card, "Beats like a bird", 5.9 Hz and its double; the card without the Yes/No rows.
  - Start over after it: the question in the card; on yes 26 files into `earlier/<date>_<time>`, no marks, no
    track, no card, the button "Begin", and the line that says where the results went.
  - A copy of Jacob's own folder of 2026-11-21 (three objects, its list saying 1), opened with 1 said: the button
    says Begin, the press sets the three aside, looks again, and ends with one object and one report.
- *Jacob's three objects made one from the command line* (`run PR169 --each pr169 --same 1,2,3` on a copy, job
  19243): one object, 25 marks, frames 1-408, "You looked for 1 object: 1 was followed."; the three old folders whole
  under `earlier/`; the list and the report say who made them one and what the track did where their marks meet.
- The window strand's own runs on its branch: A and B, job 18831, all 29 suites; C, test_cli 164 and test_gui 836
  (jobs 19184, 19185).

**`tune-06` 7f2b709** (`amateur` 0c55fa5 and the whole round; snapshot `snap/tune06-c`).

- *Every suite, with the footage, on CPUs* (job 19231): ALL SUITES PASS, 32 suites, 0 FAIL. Against `amateur`
  cb20ba9's own final run (job 18213): test_measurement 840 -> 851, test_cli 150 -> 174, test_gui 803 -> 842 with 1
  SKIP on both; the others as there (test_reduction 755, test_drift 382, test_controls 177, test_tether 92,
  test_focus 33, test_edits 40, test_stars 34, test_phone 53, test_gpu 203 with 1 SKIP, test_golden 266).
- *On the card* (RTX 5070 Ti; job 19232, and the footage suite again in job 19295): 31 suites pass (test_gpu 276,
  test_gui 842 with 1 SKIP) and test_golden 266, 0 FAIL. In job 19232 the footage suite was killed for memory after
  127 passes: the job had been given 6 GB to get through a crowded queue, and this line's footage suite needs more
  (its tether cache); run alone with 10 GB it passes.
- *The Find benchmark's development part* on this line's Find: the right-hand column of the table above.
- PR169: one row, the same ten marks as on `tune`; exercise 1's page passes (job 19166).

## Decisions for Jacob, each with a recommendation

1. **Bringing `tune` into your window.** *Done since: `main` was fast-forwarded to `tune` on your word, relayed by the
   audio-paper session; start the window again to run it.* As first written: your desktop icon runs the main
   checkout, and `tune` was not merged into `main`: the other sessions treat a merge into `main` as your word, and so
   did this one. To try it first without
   merging: `PYTHONPATH=/hugespace/models/mcdonald-tune/src ~/.venvs/py314/bin/mcdonald-gui`. To take it:
   `git -C /hugespace/models/mcdonald merge --ff-only tune` with the window closed (it is a fast-forward: `main` has
   not moved since 6aa845b). *Recommendation:* try it on PR169, then merge, and make your GUI tweaks on `main`.
2. **The version.** Nothing is versioned. Exercise 1's page names **0.5.10** as the first version that can do it
   (two places in `docs/exercises/01-pr169.md`), and the README, CITATION and CHANGELOG ("## Unreleased") are as
   test_reduction will ask for at a version commit. *Recommendation:* 0.5.10 for this round with your tweaks (a small
   release from `main`), and 0.6.0 for the 0.6 line when you have read it; say if it should be another number and the
   page follows.
3. **The 0.6 line.** `tune-06` (from `amateur` 0c55fa5) holds the whole round with its conflicts resolved
   (`propose.py`'s step goes after that line's `order`, under `gpu.on(None)`; `stages.py` and `report.py` keep both
   lines' additions). *Recommendation:* when `amateur` goes into `dev-0.6`, fast-forward to `tune-06` instead (it is
   `amateur` plus this round), or merge `main` into the 0.6 line after decision 1 and take `tune-06`'s side.
4. **`mcdonald batch` and the joining step.** `batch` asks for its lists with `join=False`, because what is one
   object in a batch is its own recorded rule (`make_of`) and the tables made so far are held to it. A turning bird
   in a batch is still two objects. *Recommendation:* turn it on at the batch rule's next version, measured on the
   pass first (how many objects of the 144-video pass become one).
5. **The checklist's two rows about the background** read against each other on PR169, the exercise's own report:
   "Did the camera move? **Can't tell**" beside "Does the object move against the background? **Yes** -- about 72
   pixels a second across the picture, which held still", while the conclusion says its motion against the
   background is not measured. This is the open point of the amateur handoff's decision 8 (8 reference objects read
   the same way). *Recommendation:* Can't tell on both rows, as recommended there; it is a report-changer, so your
   word. The exercise page quotes only the conclusion, which does not change.
6. **What Find still lists twice** (method §110): pieces more than 60 frames apart or with unseen frames between
   (seven small objects of the development part), and a large body found as several parts at once (ten helicopters
   and an airplane). The first kind is what "Same object as…" is for. *Recommendation:* the second kind is the next
   Find strand if you want one (parts that keep their places are one body: `groups` has the test for points).
7. **A test for a join made by a person** (method §112's "How it fails"). The report of two objects made one says
   what the anchored link did at the seam, which is weak evidence, and that no test checks they are one. The test of
   §110 would be one: follow on from the first object's last marks with no mark ahead, and see whether the track
   arrives on the second's first mark. *Recommendation:* build it next (`stages.seams` asking `propose.link_reaches`'s
   question of marks); the sentence then says "followed on from object 1's marks alone, the track arrives on object
   2's first mark" or that it does not.
8. **The window strand's five judgement calls** (method §112, "Judgement calls") and its change to my brief for the
   count: the press starts over by itself only where everything saved is the press's own choice, never a person's
   marks or an agent's folders. *Recommendation:* accept them as built.
9. **The words.** New sentences a person reads: the row's "found 3 separate times (frames 3–39, 68–251, 261–406) and
   taken as one object, because the spot can be followed from each into the next"; the step's "Checking which of the
   spots found are one object"; Start over's question and its line after; "Same object as…", "This is the same
   object as", "Join them", "They are one object"; the report's paragraph for objects made one. All were run through
   sciencespeak's checker. They are yours to change.
10. **Small things done on the way, to know of.** The beat figure's right-hand title is set from the right where a
    beat has a double (it ran off the figure; it changes that picture in any case with a double). The shipped list
    of PURSUE videos has release 08's three, and LLE-UAP-PR004's title follows the release's own change. The three
    videos are in `/models/data/mcdonald/pursue/`. PR44's exercise page is removed, not kept as a fifth exercise
    (exercises 2 to 4 still teach choosing a segment).
11. **Not done.** The held-out third of the Find benchmark was not run (it is scored once, at a release). The Mac and
    Windows runs were not made (nothing was pushed). The C-TAP benchmark is rerun at a release, not here.
12. **An integrity flag and the card** (2026-11-23). With the card's conclusion now one sentence, a report whose
    integrity checks flag the object ("N integrity checks flag it as possibly added to the video") no longer says so
    on its card; the full report does, in its conclusion and its checklist. The one press skips integrity, so this
    is met only after Advanced Mode's Measure with integrity ticked. *Recommendation:* where a check flags the
    object, let that be the card's sentence, whatever the label: nothing else on the card matters as much if the
    object may have been added to the video. It is one line in `Case._concluded` (`short = flagged or named or
    moved or also[0]`). Not done, because it would put a sentence under the label that is not about the label.
13. **The card's words** (2026-11-23). The table in "The next day" above has each label's sentence. The speeds at a
    given distance are the longest (17 to 20 words) because each keeps what it is a speed of ("across the line of
    sight", "as the camera held it") and its Mach number. Without the Mach number each is two words shorter. The
    box's line could lose its second half ("…needs the field of view and the distance.", three lines in place of
    four), at the cost of not saying that a reference object of known size is another way.

## The release candidate, 0.5.10 (2026-11-23)

Jacob, after the card's change: "Unless there are major outstanding problems, I think we will finally be ready to push
and version release". Taken as: get the main line ready and say what stands in the way; the push and the tag wait for
his word. The other sessions were asked: none was asked to release, none has anything waiting for the main line, and
the 0.6 line stays held for his reading (the amateur session), so this is a patch of the main line.

- **Branch `release-0.5.10`** (worktree `/hugespace/models/mcdonald-release`) = `tune` + one release commit: the
  version and the date in `__init__.py`, CITATION.cff, both READMEs, the CHANGELOG's heading, ROADMAP's line.
  Exercise 3's page no longer quotes the card's line word for word, so it holds for 0.4.2 and for 0.5.10.
- **On `tune` since the card's commit:** 0f7e9e5, the amateur session's e62ff68 picked onto the main line: the
  witness's phone clip is "clip W" in comments, docstrings, check labels and `docs/handoff-phone.md`, with no file
  name, place, date or folder name (Jacob's decision of 2026-11-22, applied on the 0.6 line the day before; public
  history keeps the old text). No code or number changes.
- **The old Exercise 1 address** (`exercises/01-pr44/`, and `docs/exercises/01-pr44.md` on GitHub) stops existing
  with this release. Jacob chose no forwarding page (the marketing session asked him: the posts are rewritten for
  PR169).
- **The date** is the day it goes out: if the push is on another day, it changes in the four places first
  (`__released__`, CITATION.cff, the CHANGELOG's heading, ROADMAP's line), with test_reduction on the result.

## Released: 0.5.10, 2026-11-23

Jacob's word, in this session, three times: "Go, release when all pass" (a question that named each step), then,
after the Mac's failure, "Release when Windows passes", then, after Windows' own, "release now". The amateur session
had relayed the same the hour before; a relayed word was not taken as the word for a push.

- **`main` = `origin/main` = tag `v0.5.10` = 03fc2ee** (annotated, "mcdonald 0.5.10"), pushed about 11:02. GitHub
  release 0.5.10 with the CHANGELOG's entry as its notes. PyPI: publish run 40 green, `mcdonald-0.5.10` wheel and
  source archive. Site: run 37 green; `exercises/01-pr169/` answers, `exercises/01-pr44/` is gone, as he chose.
  Zenodo's version DOI: 10.5281/zenodo.24471817 (in CITATION.cff with this commit).
- **The commits since 30d27b6:** 91cde5d the card's one sentence (TU9); 0f7e9e5 clip W; c950175 the version;
  55db510 and 03fc2ee, one fix each from the Mac's and Windows' runs (below).
- **Linux, the release commit c950175** (snapshot `snap/rel-a`): every suite with the footage, job 22696: ALL SUITES
  PASS, 29 suites, 4,464 checks, 1 SKIP (WxAgg, not installed): test_reduction 744 (734 + 10), test_gui 875 (873 + 2),
  test_cli 165 (164 + 1), test_golden 266, test_measurement 722, test_drift 373, test_controls 118, test_tether 78,
  the rest as on 5691539. All four exercise pages as they write themselves (job 22692): pass. The wheel and the
  source archive build and pass `twine check --strict`; the wheel installs in a new environment, every module
  imports, and with only the shipped list PR169 downloads from its public address (3,325,618 bytes, the local copy's
  hash) and opens; `mkdocs build --strict` passes (`scripts/rel_build.sh`, `rel_try169.sh` in the scratch folder).
- **A trap that cost a run:** the first three suite jobs of the morning (22687, 22689, 22691) were submitted from
  snapshots without `MCDONALD_DATA=/models/data/mcdonald`. A snapshot has no data folder beside it, so the footage
  checks skipped and the job still said ALL SUITES PASS. Caught from the counts (test_drift 359 for 373, test_tether
  75 for 78, test_golden's skips naming the snapshot's own folder), cancelled, and run again with the folder named.
- **Mac run 128 and Windows run 129, on c950175: one failed check each, in test_cli, and every other suite passed.**
  - *Mac:* the check of `clear VIDEO --n0 --n1` compared the answer's real path with the temporary folder as Python
    spells it, which on a Mac is a link (/var/folders for /private/var/folders). Reproduced on Linux with `TMPDIR`
    set to a link (the same check fails, 164 pass); with both sides resolved 165 of 165 pass. The test's fault:
    55db510.
  - *Windows:* `clear --dry-run --json` listed what would stay in another order (extra, notes.txt, "PLANTED
    report.pdf", ...). `clear.remembered` sorted the folder's paths, and a Windows path sorts without regard to case
    (PureWindowsPath gives the run's order exactly). It now sorts by the name as text, the same everywhere; on Linux
    and a Mac nothing changes: 03fc2ee. `sorted()` of paths is used in some twenty other places of the package; none
    is known to print a list that mixes cases, and none was changed.
- **On the released commit 03fc2ee:** the Linux lanes on arthur (job 22701) had passed test_cli 165, test_gui 875
  and 20 more suites with no failure when the tag went on, and their footage lane was still running; Windows run 131
  (03fc2ee) and Mac run 130 (55db510, one commit before: the Windows fix changes nothing on a Mac) were under way.
  Their ends are recorded below when they come in.
- **A new environment from PyPI** (`/scratch/mcdonald/venv-0.5.10`, `mcdonald[gui]==0.5.10`): 0.5.10, `setup
  --no-desktop` Ready, PR169 downloads and opens. Jacob's menu entry untouched.
- **What Jacob asked for after it (2026-11-23):** the suites job fails loudly where `golden` is asked for and the data
  folder is missing; each suite's PASS and SKIP counts are compared with the last known-good ones by the job itself;
  and release tests run on arthur in side-by-side lanes by default (`mcdonald-test --on arthur --golden`, not the one
  sequential job). Found on the way: the Mac's job has a 60-minute limit and its suites took 55.6 minutes in run 128.
- **The 0.6 line** is held for his reading (amateur 8135977, dev-0.6 779d04d); its unpushed history was rewritten on
  his word, so the hashes of that line written earlier in this file (0c55fa5, 7f2b709, d02cd36, 350231f, 0a9b3d7) no
  longer exist. `tune-06` 0a60dcc holds TU9 on the old amateur line, for whoever merges the main line into it. The
  C-TAP benchmark is offered after a release that changes Find, as this one does.
