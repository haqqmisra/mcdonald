# Handoff: the bird-headline gate, then a beat sweep of every PURSUE sensor video (2026-10-10)

**State.** 0.2.16 is released (tag `v0.2.16`, on PyPI 2026-10-10): the flicker aperture follows the object's
size (`c24ac95`), every beat of its own is drawn as `<case>_beat.png` (`31477ab`), and the parallel stages
(`cd58cf9`). All seven suites passed on that code (job 2367, golden included). A pinned install for batch work:
`/scratch/mcdonald/venv-0.2.16/bin/mcdonald` -- **never batch from the editable tree**: a run crashed on
2026-10-09 when `flicker.py` was edited under it (forkserver children import the module fresh).

What came before, and why: `docs/handoff-flicker-pr23.md` (the PR23 false bird, 0.2.15),
`docs/agent-run-birds-sweep-2026-10-09.md` (the 18-clip sweep, the aperture problem),
`/hugespace/local/research/uap/analysis/bird_flicker_sweep.md` (every clip's result, PR41, the PR135
calibration, PR159 Tremonton, PR19's streak).

Where it stands: of the ~125 PURSUE sensor videos, **20 have been beat-tested**; two beat (PR135's six birds,
7.1-7.9 Hz; PR41, 6.43 Hz on the whole track). The sweep chose clips the ledger already called possible birds,
so a bird nobody labelled would have been missed -- hence step 2.

## 1. Decide: the bird headline from one stretch (Jacob)

`report.py` names "a bird is the leading explanation" whenever the flicker stage's beat passes -- and since
0.2.15 a beat passes on the clearest 2-s window even where the whole track does not. Two cases show what that
does:

| clip | whole track | windows passing | what the report says |
|---|---|---|---|
| PR094 (0.2.15) | 2.44 Hz, under its drift | 2 of 54, overlapping (one ~2.2 s stretch), 3 % | "a bird ... 4.97 Hz" |
| PR052 (0.2.16, newly measurable) | 2.14 Hz, 5 %, under its drift | 6 of 79, overlapping (one ~2.5 s stretch), 12 % | "a bird ... 5.78 Hz" |
| PR41 (keep) | 6.43 Hz, 80x over drift | 12 of 98 | bird |

PR094's light curve over its stretch is a step and three dips, not a beat; PR052 is digitally altered
(edge-enhanced, cut and zoomed). Proposed: name a bird only where the whole track beats, **or** windows that
do not overlap (two at least) pass at one frequency; a beat heard in one stretch is still reported, as
"a beat in one stretch, frames a-b", without the headline. Controls: PR41, PR135's six, Galileo flyers 1-5
keep the headline; PR094 and PR052 lose it; PR23 stays no beat. The beat figure already shades the window and
dashes its spectrum, so a lone-window beat looks like one.

## 2. Sweep every untested sensor video

The list: `/hugespace/local/research/uap/analysis/beat_sweep_todo.csv` -- 126 rows (ledger rows R01-R05
plus R06), `tested` = yes on 20, **106 to do**. Check the list first: the LLE phone videos and anything
non-sensor (genAI recreations PR005/PR006 if present) may not belong.

How each clip was done in the 18-clip sweep (scripts in `/scratch/mcdonald/birds/`, point them at
`venv-0.2.16`):

1. **Where is the object.** `mcdonald look VIDEO --tiles 40` overview; read the AARO description for its
   timestamps (R02's are only on DVIDS: `og:description`, curl works -- build the URL from the id,
   `https://www.dvidshub.net/video/<id>`; DVIDS answers 202 and nothing when hit fast: go slowly).
2. **Propose** over a segment of 5-30 s: `propose.sbatch` (an array over a jobs file; ~2 GB peak, ~12 min
   for 650 1080p frames). Open the sheet and decide by eye; an object the sensor holds still is invisible
   to Find -- use `look --frame N --size S [--dark]` (PR116).
3. **Mark** with `--set` and a `--why` (`bin/accept.py PR RANK N0 N1 "why" [case] [--dark]`; several fragments
   of one object: `bin/multi.py`, but fragments of different sizes do not link together -- use one). Check
   the track strip.
4. **Measure**: `run.sbatch` (`mcdonald run --skip integrity`, ~1.7 GB, 15-80 min) or just
   `mcdonald flicker VIDEO --track ... --n0 --n1 [--dark]` (minutes). `bin/flick.py <case>` prints the flicker
   stage. Throttle arrays (`%3`-`%4`) and `--nice` long ones so Jacob's own jobs get through.

Traps met on the way (each cost a run):
- **Content cadence.** Check repeated frames first (`bin/cadence.py VIDEO n0 n1`): PR29 is ~10-11 pictures/s
  at 30 fps, PR007 9/s (a hand-held imager), PR159 is film scanned frame by frame and shot at 16 fps (give
  the shooting rate). The band ends at half the picture rate.
- **Edge-enhanced footage** (PR052, R02 "digitally altered") sums to ~0 over any aperture.
- **Lost frames that are real** (PR159: the object fades out) versus false (an overlay box, a reticle line
  crossing -- trim the segment short of it, PR47).
- A tool "bird" call is only as good as its windows: look at the beat figure.

## 3. Smaller tool items, not started

- Flicker on held frames: drop repeated frames (the survey already counts them) and use the content's rate --
  PR29 is lost on 21/174 frames because of its holds.
- Hand-held shake on a point: the 5-frame smoothing slides a 4-px aperture off a 5-px speck (PR007); the
  link's own positions with a small search fixed most of it (`flicker_scaled.py`, `raw_track`, `search`).
- The beat figure's sixth row repeats SERIES[0] (five colours; PR135 has six members).
- The 8-CPU timing run of `cd58cf9` (see `docs/handoff-ui.md`) is still to do when the machine is free.
- The platforms CI (macOS, Windows) was not run for 0.2.16; it runs on pushes to its own branches.
