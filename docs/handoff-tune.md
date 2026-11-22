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

**The window strand** (`tune-window`, an agent): see "The window" below.

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

## The window

*(filled in when the window strand reports)*

## Checks on the merged tree

*(filled in at the end)*

## Decisions for Jacob, each with a recommendation

*(filled in at the end)*
