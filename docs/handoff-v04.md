# Handoff: ROADMAP 0.4 -- session 13 (2026-10-30 to 11-01) on top: 0.4.0 finished locally, waiting for Jacob's word; sessions 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2 and 1 below as the record

## Session 13 (2026-10-30 to 11-01): 0.4.0 finished, committed locally, waiting for Jacob's word

### The release (2026-11-01, morning; read this first)

Jacob said go. Done: dated 2026-11-01, ROADMAP's 0.4 marked, the parallax ladder moved to 0.4.x, the case files installed in the data folder (0.3.0 set backed up in `/hugespace/local/mcdonald-cases-2026-10-31/old-0.3.0/`, every checksum
verifies), golden 195 and share 25 against them. **The first Windows run since 0.3.9 (run 101) failed:** printed commands wrote the video's path bare, and the band's repeat check asked for exact equality. Fixed in 93aa1ff: the path quoted, the check held to
one part in a billion, where it then passed with no difference, so that was rounding. **On 93aa1ff: Mac run 102 and Windows run 103 green; reduction 558, cli 133, slew 65, gui 763.**

**What is left is the public step, and the auto-mode classifier refused it from this session ("Create Public Surface"), so Jacob runs it:** the tag and push, then the GitHub Release (it is the Release that gives Zenodo its DOI). Nothing has gone out: no tag exists, GitHub's main is e60238f.

```bash
git -C /hugespace/models/mcdonald tag -a v0.4.0 93aa1ff -m "mcdonald 0.4.0: the unknowns"
git -C /hugespace/models/mcdonald push origin main v0.4.0
gh release create v0.4.0 --repo haqqmisra/mcdonald --title "mcdonald 0.4.0" --notes-file /hugespace/local/mcdonald-cases-2026-10-31/release-notes-0.4.0.md
```

**After that:** the publish, site and suites runs; PyPI has 0.4.0; a fresh venv (`pip install "mcdonald[gui]==0.4.0"`, `mcdonald setup --no-desktop`); Zenodo's version DOI into CITATION.cff, as e60238f did; the testers.

### Where it stood before the release (2026-11-01, 01:30)

**0.4.0 is finished and held for Jacob: nothing is pushed or tagged.** main is 97+ commits ahead of GitHub, with 705c6e0 the version commit and handoff commits after it. **Tested on 705c6e0's snapshot:** all 21 suites pass (gui
763, golden 195 PASS 0 SKIP, measurement 540, reduction 558, cli 133, camera 151, drift 92, slew 65, audio 54, published 32, zoom 31, share 25, horizon 25, tether 24, focus 19, waves 14, stabilize 13, aspect 10, sweep 10, haze 9, streak 8;
jobs 15868-15888) and all four exercises pass, 30 of 30, FAILED none (15867). **The 14 reference case files are remade from their recorded commands and rerun to their numbers under `--strict`, 31 of 31 objects, no difference,
first try** (arrays 15866, 15892; 2 h 20 and 2 h 05 on the NVMe). Against the 0.3.0 set no label moves, no beat moves, the camera-shake gate fires on none (`compare.py`). The lanterns' 2.72 Hz false beat is gone on the final code. All of
Jacob's twelve answers are built. Every agent has finished; the nine worktrees and branches are merged and removed.

**The new case files are not in the data folder yet:** they, their README, the recipe and `install_cases.sh` are in `/hugespace/local/mcdonald-cases-2026-10-31/` (and `/scratch/mcdonald/v04-s13/main/cases/out`). The 0.3.0 set stays in place until
Jacob says.

**On Jacob's word, in this order:**
1. Set the date to the push day in `__init__.py`, CITATION.cff and the CHANGELOG (they say 2026-10-31; a test holds them together), and run reduction and cli.
2. `bash /hugespace/local/mcdonald-cases-2026-10-31/install_cases.sh` (backs up the 0.3.0 set, installs, refreshes SHA256SUMS with the two stale lines, verifies).
3. ROADMAP's 0.4 marked released, session 11's "Where 0.4.0 is cut" closed; the parallax ladder's fix is still on hold for N. Long, so it needs Jacob's word whether 0.4.0 goes without it.
4. `git push origin main`, tag `v0.4.0` (PyPI by trusted publishing, the website on the tag).
5. Push to `macos-ci` and `windows-ci` (see the memory: two runs, watch by sha, logs on `ci-logs`). Then Zenodo's version DOI, as for 0.3.10, and the testers.

**For 0.4.x, noted in this session:** a stage for dash centres; `tools/` for the remake recipe; the last "platform" wording; PR097's pooled reading; tau across a track's stretches; a `slew` band; `residual_jitter` on the whole track (moves `fits`, needs M1's null);
the camera, horizon and focus stages through the lens; `tau_said`'s R / |Rdot|; §33 saying the size route reads T; haze with the object as its own reference; a03's false zoom; the size route's band; Find and Follow at far range; AOT goldens (`aot/data`, `aot/clips`,
34 GB, kept); flyers 2-4's line in the picture's right half, unexplained; the Svanström platform's 6.1-6.2 Hz line.

### How the session went

Jacob: "Next handoff is in docs/handoff-v04.md as usual. Jobs go through /slurm. Spawn agents if needed to utilize the machine's capacity ...". Nine agents from session 12's briefs, then three maintenance stops; `/hugespace` moved to an NVMe at the second.

Jacob: "Next handoff is in docs/handoff-v04.md as usual. Jobs go through /slurm. Spawn agents if needed to utilize the
machine's capacity, I don't have other compute jobs planned today, and I just upgraded to an Ultra account"; then, at
18:05, "Can we pause everything for system maintainance? Doesn't have to be immediate, but in 1 hour". **So this section
is a pause, not an end:** main is 4467237 plus this handoff, no agent had committed, nothing is merged.

### Third hold (2026-10-31, 19:47; read this first)

main is 705c6e0 plus this note: 0.4.0 in `__init__.py`, CITATION.cff, both READMEs, the CHANGELOG and the exercise pages, **committed locally, not pushed, not tagged**. All branches are merged and
all of Jacob's answers are built. The whole set was held after under 4 minutes, so nothing is lost. **Held from `snap_r1` = 705c6e0:** `exall_r1` 15867 and 21 suites `r1_*` 15868-15888 (all
of it on 0.4.0); `remake` 15866 (the 14 case files, array 0-13%3, from their recorded commands, out in `main/cases/out`); `rerun` 15892 (strict, runs after the remake by a dependency); `lant_fl`
15893 (the lanterns' 2.72 Hz beat on the final code; by the rule it should go: p 0.0215 over 130 windows gives 0.30 against 0.01). `remake.py` and `keep_tests.py` now start over cleanly after a
requeue. **To go on:** check the machine, then
`squeue -u jacob -h -t PD -o '%F|%r' | grep -i held | cut -d'|' -f1 | sort -u | xargs -r -n1 scontrol release`
**Then, when the rerun is done:** compare old and new case files (calls, frequencies), `cases/README.md`, refresh SHA256SUMS (with `README.md` and `aaro/resolved_cases.csv`, whose lines were already stale), and **stop: Jacob sees it
before any push or tag.** PR088 object 2 (3,678 frames) sets the pace; a task's limit is 8 h. Then the 0.4.0 release list: ROADMAP's 0.4 marked, push, tag `v0.4.0`, the Mac and Windows runners, delete the merged worktrees.

### Jacob's answers (2026-10-31, evening, by multiple choice)

| asked | answer | done |
|---|---|---|
| frame 75 | **merge the link fix and drop it** | merged; the reference case at the remake |
| the camera-shake gate | **in 0.4.0** | merged |
| `--range`'s "relative to the camera's platform" | **change it** to "as the camera held it" | done, with "the least its speed as the camera held it can be" |
| loops | **as built, 1 of 11** | stands |
| the depth bound | **keep what is on main** | stands |
| exercise 4's page | **move it** | moved: five birds and one it will not name |
| `ONCE_P` | **0.01** | stands |
| `BALANCED` | **0.85 at 5 %** | stands |
| Galileo text in public files | **keep it all: "the Loeb et al. paper is on arXiv now"** | stands |
| card words | **all four approved**: the Turn row, Camera shake, Range limit, Lens | stand |
| PR43's measurement of record | **track points, 0.76 s** | a dash-centres stage goes on the 0.4.x list |
| the release | **stop and show Jacob first** | finish the remake, version, CHANGELOG, commit locally, report; no push, no tag |

The smaller items take the agents' recommendations without a question: PR097's pooled reading, tau across a track's stretches and a `slew` band to 0.4.x; no 10-s floor on the light's reading without a
null; `--range-max` keeps its label and "the largest step as the fastest"; two ranges for t_z's error. **Still say "platform", left for 0.4.x:** the admissible region's text and figure ("the speed relative
to the platform"), the card's row "Relative speed, across", and the bottom line's "*relative* speed, which already includes the platform's own motion". **Jacob's own, in uap:** "the lanterns fade" in the case README
(this clip contradicts it), AIRPLANE_064's "four-bladed propeller" (it sits on a line of the picture's shift), the Puerto Rico 1657.

### Scene shift, part 1 (2026-10-31, afternoon; table `/scratch/mcdonald/v04-s13/sceneshift/runs/part1_table.md`; the agent's reading, 37 of 47 objects read)

**No recorded bird's beat is shown to come from its sensor's motion. PR135's six read clear in both forms, and every PURSUE beat at 6 Hz or more reads clear.** But
the reading as built (`SHIFT_STANDS` 10) falsely says "the sensor moves at the beat" on nine birds: PR44, PR079, PR088 object 1, PR097 object 8 and flyers 1-5. So **a gate on
it as built would remove real birds, and will not be built.** Why it is read as a fault: the shake there is 0.0004-0.0038 px against aot's five at 0.37-1.12 px; the
shake's spectrum is red, so `stands` over the whole band passes 19-56 % of frequencies under 5 Hz; the nine's brightness is under the coherence level; and their
brightness per px of shake is 39-627 against aot's 0.14-1.7. Part 2 tests a local line, the shake's size and coherence. **Not cleared:** flyers 2, 3, 4 have a real small line in
the shake at their own beats (0.001-0.004 px; leakage of the bird into the registration, or a camera line, untested), and fixed pattern pulls the reading toward nothing by
an unmeasured share. Part 4: no recorded reference command gives both `--marks` and `--track`, so the polarity bug reaches none. **The earlier machine note:** `/hugespace` is an NVMe
since 2026-10-31 at the same paths; all 3,549 reference files checksum clean but `README.md` and `aaro/resolved_cases.csv`, byte-identical to the old drive and edited before the
move: their lines in SHA256SUMS were already stale, and want refreshing with the remake.

### `sceneshift` ready, not merged (13ff7e2, branch `sceneshift`, on main de3be44): Jacob's word first

`SHIFT_STANDS` is gone. A bird is not named where the picture's shift has a line at the beat, at least `SHIFT_LOCAL` 15 times its neighbours within 1.5 Hz, **and** the beat is no bigger
than a shake that size can make, `SHIFT_PER_PX` 5. **Fired on 5 of 5 AOT aircraft, 2 of 15 Svanström aircraft and drones, 0 of 37 recorded birds, 0 of 36 labelled birds.** Line test: about 1
in 200 of 18,000 drawn paths; both rules at a random frequency on real cameras: 0 of 14,800 (PURSUE + Galileo), 1.6 % of 20,400 (Svanström), 14 % of 2,000 (AOT): on a camera with real lines a
real bird landing on one can lose its name, and the report says why. `SHIFT_PER_PX` 5 is judgement in the gap between 3.4 and 36, set from the low side by six aircraft, five of them one
data set; IR_BIRD_012 is kept only by the line test, 13.5 against 15. No reference headline moves (read on recorded commands, not by the strict rerun); every bird's report gains a
technical note, and a bird costs 2-6x the plain run. Flyers 2-4's line is no shake of the sensor (the right half reads it ten times the left), cause not found; the rule leaves them
alone by size. **Svanström AIRPLANE_064, the uap README's "four-bladed propeller" candidate, sits on a line of the picture's own shift** (0.044 px, 60 times its neighbours, coherence 0.91): the
uap note is Jacob's. Why so small a shake makes so large a beat is not worked out: the size test is a ratio, not a prediction. No real bird on a badly shaking camera was tested. Suites on the
merged tree: reduction 558, cli 133, golden 195, gui 763, measurement 534, drift 92, published 32, share 25. `c1ca3da` keeps the marks' polarity with `--track`; no reference command is affected.

**The trial branch `candidate`** (worktree `mcdonald-candidate`, c844a55) is main + `sceneshift` + `dive43`, so that both can go in at once; delete it after.

### `dive43` ready, not merged (9293f6f, branch `dive43`, on d6b994e): Jacob's word first

`autolink.went_back`: on a thing expected to move 4 of its widths or more, a peak half a width or more behind its last position is not the thing. The tree's suites: reduction 555,
cli 132, golden 195, gui 763, measurement 529 (+6). **PR43 on the merged tree:** T 0.91 -> 0.76 s, 16-84 % 0.43-1.39 -> 0.73-0.80, v/R 1.10 -> 1.31 /s, jitter 8.00 -> 2.90 px, misfit
1.04 -> 1.29 and still fits; 24 frames, 50-74; along the track 10.6-43.0 px/frame; the card's words do not move. **Its limit:** a real step refused on 0.28 % of tracks (4 of 1,414), but
only 4 % of 303 planted residues refused, as most sit among real steps: it catches a clear case like frame 75, not the general problem, and looks at nothing ahead of the
last position. PR43 is the only real track that takes this path by itself; `find_rank`'s pass could not have differed (the commit says so). The 1 % limit and (4, 0.5) under it are
judgement. **Jacob's:** merge it given that limit (recommended); drop frame 75 from the reference case at the strict rerun (recommended), when `track.pop(75)` and method's 25-point
PR43 figures change; dash centres as the measurement of record (T 0.73, no recommendation). **Open:** dash length against rate; `streak`'s 15.6 ms unsupported, no bug shown; the jump
test's 8 % miss not fully explained; whether `projective.fit` ignores `jumps`' drop. Keep `dive43/keep_base/` (421 MB): the only kept seed set the project now has.

### Second hold (2026-10-31, 08:56; read this first)

Jacob asked for a second maintenance stop and said to hold at once. main is d6b994e plus this note: seven branches merged (`beats`, `dive51`,
`balanced`, `lanterns`, `size-depth`, `lens`, `thresholds`), and **all 21 suites pass on merged main** (reduction 555, cli 132, gui 763,
camera 151, measurement 523, golden 195 PASS 0 SKIP, share 25, published 32, and the 13 others, jobs 15557-64 and 15574-86). `aot` is finished.

**Held, nothing cancelled** (`drain.log`): `exall_m4` 15573 (all four exercises on d6b994e, requeued after a few minutes; its partial `exm4/keep` was
removed, as the harness cannot restart over it); `ss_read` 15587 (beats' scene-shift reading, restart-safe; no task had finished); dive43's
15598-15605 (`run_merged`, the five suites on its branch merged onto main, `q43`, `t_leave2`). To go on, as below, release from `squeue`; a task
held by `requeuehold` shows the reason "job requeued in held state", so match on `held` and not only `JobHeld`:
`squeue -u jacob -h -t PD -o '%F|%r' | grep -i held | cut -d'|' -f1 | sort -u | xargs -r -n1 scontrol release`

**Then:** resume `beats` (part 1 of the scene shift is the first thing wanted, and it must still submit the 4 long objects and aot's five, listed in its
notes) and `dive43` (its branch merged onto main, then the suites). The case-file remake waits for Jacob's calls on frame 75, `--range`'s wording and
the scene shift.

### To resume (read this first)

1. **Slurm:** the drain (`/scratch/mcdonald/v04-s13/main/drain.py`, log `drain.log`) ended at 19:05:29 with nothing running: 815
   tasks in 18 jobs and arrays held, none cancelled, and **none requeued** (everything that had started finished in time, so no
   running work was lost). To go on:
   `squeue -u jacob -h -t PD -o '%F %r' | awk '$2 ~ /JobHeld/ {print $1}' | sort -u | xargs -r -n1 scontrol release`
   -- from `squeue`, not `held.txt`, which misses arrays where `scontrol hold` returned 1 because some tasks had finished
   (14166, 14183, 14330). Lanterns has no job held: its script is fixed and untested, a two-minute job to resubmit. Check `bash ~/.claude/skills/slurm/scripts/status.sh` first.
2. **The agents:** if this same session continues, resume each by message (`/scratch/mcdonald/v04-s13/AGENTS.md`). If it
   does not, a new session cannot reach them: start each afresh from `BRIEF-common.md`, `tasks/<name>.md`, its
   `<name>/notes.md` and its worktree. Their held jobs may be useless to a new agent; read the notes first.
3. **Keep:** the seven worktrees below with their uncommitted edits, `/scratch/mcdonald/v04-s13/` whole, every `snap*` in it
   (held jobs import them).

### Who is where (each agent's `notes.md` is the record; none has committed)

| agent | worktree / branch | task (`/scratch/mcdonald/v04-s13/tasks/`) |
|---|---|---|
| beats | `mcdonald-beats` / `beats` | no "a rhythm of its own" from one 2-s window against its own cross-checks; plus exercise 4's sensitivity (below) |
| balanced | `mcdonald-balanced` / `balanced` | `BALANCED` from a null with a stated rate, the census rerun |
| lens | `mcdonald-lens` / `lens` | k1 as a known, the projective test through it, M1's null rerun |
| thresholds | `mcdonald-thresholds` / `thresholds` | M4's 150°/3σ/0.8 from a null; M5's t_z error on the real tracks |
| sizedepth | `mcdonald-size-depth` / `size-depth` | the camera stage's size trend; `depth_bound` from the geometric mean |
| lanterns | `mcdonald-lanterns` / `lanterns` | the lanterns' light route over 54-117 s |
| dive43 | none (scratch only) | PR43's (b)-(d) |
| dive51 | `mcdonald-dive51` / `dive51` | `--range-max`, PR051's release null |
| aot | none (scratch only) | Amazon's AOT set as known ranges (stand-in C), added to the list today |

Queue when paused: 912 tasks, 480 CPU-hours at their time limits, ~340 of them beats' arrays (`bt_null`, `bt_ctl`). The first
hours went to my bisect holding all 20 CPUs (dive43's jobs waited behind it); agents hand back when they have only queued
jobs left, so a message is what restarts them.

### Done on main or in uap

- **The uap case notes** (uap d3df4ce, only those paths; Jacob's 416 changes untouched): the Yemen README's "The sea as a
  ruler" (k 2,468 px/deg, 0.86-1.03 m, at most 2.0 m) and its Frames line corrected; a new `santa_barbara_hoist_2018/rotor_k/`
  (README, session 11's scripts, the ring's picture), a folder because that case's README has Jacob's uncommitted test-numbering
  note. The Puerto Rico README's 1657 stays his.
- **The case files' recipe, rebuilt:** `cases-2026-10-16/18` went with the old /scratch. `/scratch/mcdonald/v04-s13/main/remake.py`
  (and `remake.sbatch`) unpacks a file, measures each object by the command its report records (`rerun.rerun_object`),
  and packs the new folder under the old part, stretches, names and thread. Preflight on 4467237: PR43 6.5 min, PR113
  4.7 min, 4 CPUs, both made. The bird videos are untimed. Still to do after the merges: all 14, then `share rerun --strict`
  on the new files. This recipe should move somewhere that survives a drive: `tools/`, if Jacob agrees.

### Exercise 4 bisected: not a 0.4 change

Session 12's candidates were all wrong. Page 04 alone, kept cases (`/scratch/mcdonald/v04-s13/main/x4/<sha>/keep`, logs
`main/logs/x4_*`, jobs 14142-49, 14198-200): **v0.3.9 and c5b27db pass 16 of 16; a745c87 (0.3.10's "Four stages read a clip
that leaves little to see") fails 3; v0.3.10 fails the same 3; 82f6c13 and everything later fail 5** (objects 2 and 6 in the
rate only, as `layers` moved). Object 4's own track is byte-identical across a745c87 and its curve entry the same
(7.815 Hz, 12.1 %, stands 52.13). What moved is upstream: autolink's `Places`/stays-put changed object 1's backward tail on
frames 1240-1258 (before its first mark, 1281), so `groups` found the members from 1259 and not 1240-1241 (members 3, 4, 8
became 8, 9, 10), and in the group's stage member 10's `whole_passes` went True to False: the beat's source fell from "the
whole track" (7.82 Hz) to "the clearest of 2 windows of 2 s" (7.99 Hz, 1309-1368), "too little to name a bird".

**Answered by agent beats** (`beats/notes.md`, uncommitted in its worktree): `flicker.measure` puts one set of background
apertures about the member seen longest. a745c87 cut two fellows from 118 frames to 99, so that became member 10 itself: the
apertures moved to its own side, where other birds cross them, the floor went 0.027 -> 0.048, and the same curve (7.815 Hz,
12.05 %) went from pass to fail. So a member's verdict did depend on a fellow's span: a real bug, and a second one beside it
(`scale` was the first-listed member's brightness). Its item 16 gives each member its own apertures, and every verdict is
then the same on both lists and in either order. **Object 4 is not won back and no rule was loosened:** measured alone it
fails on both lists, 0.1205 against 0.1332 (10 % short), or 0.1449 clear of its fellows. Its old "Beats like a bird" leaned on
a fellow's apertures. PR135's six together keep every call. **Jacob's: page 04 moves** (objects 1 and 4 at least; group 2
and object 5 wait on job 14407). The agent ran a few short experiments at nice 90 where the brief says 100; it said so.

### PR43's last point (agent dive43; `dive43/notes.md`, section "Results of the six jobs"; the agent's reading, not yet checked by me)

**Frame 75 of PR43's track is false:** no dash on it, its forced flux matches frame 76's, and the object had left the picture
at frame 74 (the kymograph's path stops at the edge; I looked at that one). Frame 74 is real. **One point set the 8-px jitter:**
without it rms 8.30 -> 3.75 px, T 0.91 -> 0.77 s, the ratio to a free quadratic 1.065 -> 0.58. **So session 11's "26 frames cannot
tell, leaning to a speed-up" came from frame 75 and no longer stands:** over what was tested the controls support "its rise is
perspective". Power redrawn, likelihood ratio for perspective over 350 against constant acceleration, about 9 against an
exponential on the track's points; the over-128 on dash centres rests on the agent's choice of frames. Codec control: a planted T
0.77 reads 0.75-0.81, flat reads flat (a comparable x264 chain, 8 paths, one seed, not PR43's own). Flat light refused (0 of 2000
draws); T from light 0.51 s (95 % 0.33-0.81) against the track's 0.73, the clocks agreeing within the noise. **Not proof against
every speed-up:** one following the same law is not excluded by the track, and the light clock assumes a steady source.

**Open:** the dash's length does not follow the rate (m/v 0.4 to 1.0, a fixed 7-px gap), and neither the chain nor the fit causes
it; this matters most, as a growing lit share could fake about 2 of the 3.78-times flux rise. `streak`'s 15.6 ms is not
supported, but no bug is shown. `focus` gives no power (the object's width is not measured), so part (d) has hand floors only.
**Why nothing caught frame 75:** `jumps` missed it by 8 % (L 8.77 against 9.50), and the link took it inside the gate by under
2 px, from the agent's assumed prediction.

**Jacob's:** drop frame 75 by rerunning the link once it refuses such a step, not by hand-editing the case file (the agent's
recommendation, and mine). It moves T, its error, v/R, the jitter, the reference report and the golden PR43 checks, so it comes
before the strict rerun. Dash centres as the measurement of record is a separate question. No worktree yet; nothing changed.

### Merged after the pause

- **`beats`** (98d05c5, merge on main): the one-stretch rule `ONCE_P` 0.01 from a null of 11,400 drawn tracks (0.82 % keep a beat,
  worst family 2.8 %) and each group member on its own apertures. Counts read from the logs: measurement 516, reduction 496, cli
  127, drift 92, published 32, share 25, golden 181 PASS 0 SKIP, gui 755. **Jacob's:** page 04 objects 1 and 4 (the agent
  recommends moving the page; the count does not change); `ONCE_P` (0.05 would keep PR088 object 1 and 8 of 11 labelled birds at
  2.25 % of null tracks; kept 0.01 because one stretch never names a bird); the new finding words `unheld_said`, not on the
  card; the member apertures read about 3x as many apertures on a group (recommended kept). Page 04 was not rerun on the final
  commit; the merged tree's exercises do that.

- **`dive51`** (838bbab, merged): `--range-max`, method §36; PR051's write-up in `dive51/notes.md` section 4. reduction 517, cli 130,
  golden 181, gui 759, measurement 508. **Corrects session 10's sentence:** "at most about 80 m/s" is a fit to one stretch, not a limit
  on the dash, and 5.8 m/s holds only against the line of sight as held. **Jacob's (its section 6):** the label from a limit
  ("Subsonic motion" under the speed of sound, by judgement); the words on the form and card; whether `--range`'s own "relative to
  the camera's platform" should change, **before the strict rerun**, because it changes reports; which number to quote for PR051;
  the largest step as "fastest" on a short track; measuring the width whenever `--range-max` is given. One change reaches reports
  without the known (small fields and rates keep their figures). The figure's grey has no test.

- **`balanced`** (9feaf14, merged): 0.85 stays, now a stated rate (4.75 % at 60 frames, 0.7 % at 120, none of 2,000 from 300, the worst of
  random, in-runs and by-place words), on a `balance` reading with a bug fixed (PR34's "0.84" was it: 0.924). No reference call or band
  top moves. reduction 494, cli 127, measurement 515, golden 181, gui 755. **Jacob's:** the new reading goes beyond calibrating a
  constant (recommended kept); 5 % is a judgement from NUGGETS (a single 1 % line would be about 0.89-0.90); the null's definition,
  with rate control left out of the stated rate, the weakest part (up to 15 % at shares 0.67-0.8); PR44 and DOD_110982722 are the same
  kind of word with the line between them; flyer 3 at 0.841, just under the line, protected by nothing but an untested I-frame veto.

- **`lanterns`** (e933e60, merged): no change to `src`; golden +13 (194). The stage says nothing false over 54-117 s; size route -113 ± 31 s against
  -111 off the stage; the lanterns switch and go dark for 5.1 s rather than fade. **Jacob's:** tau across all of a track's stretches
  (recommended 0.4.x); a 10-s floor on the light's reading (recommended not without a null); a `slew` band holding the spread between
  windows; "the lanterns fade" in the uap README, which this clip contradicts (nothing in uap touched); whether the vendored curves
  may come from a scratch script's track. **To check on the merged tree:** the stage's 2.72 Hz beat on the lanterns (5 of 130 windows)
  was measured before `beats`; a known non-bird should not keep it.

- **`size-depth`** (2e3744b, 98a10ce, merged): the size's trend in the camera stage; (c) built as `projective.depth_read`, because the geometric form alone
  failed its truths (61 % at r 2.4, 1 of 15 whole arrivals). Whole arrivals 3 given, 3 held, against main's 4 given, 0 held. reduction
  504, cli 127, golden 182, gui 755, camera 146, measurement 508, published 32. **Jacob's:** the geometric form with a tenth share and three
  refusals in place of the plain form chosen; the DEPTH constants are read from tables, not found by a formal search; PR097 objects
  1, 2, 6 lose their bounds and PR077 object 2 gains a weak one (recommended kept); the new report words.

**Before any push (Jacob's):** `method.md`, the CHANGELOG, docstrings and comments on main now say "airliner arrivals in a Galileo
Project camera" and quote their numbers (1.7-4.9 Hz, T 10-14 s, x2.8-3.5). I checked: no site, aircraft or clip time, so the rule holds,
and the public text already had "Sphere airliner" and "Galileo aircraft whose ranges ADS-B gives". But these are results from data
kept private until Loeb et al., so whether they may be public before that paper is Jacob's call. Nothing is pushed.

- **`lens`** (54346f9, merge 56a6fa2): `--lens-k1`, method §37 (both branches had claimed §36). The first merge with real conflicts, so tested on the
  resolved tree before committing: counts as predicted from the branches. M1's null at most 4.8 % with k1 out and in, which says little
  (its far path stays near the axis); 16 off-axis cases added failed at 10.2 %, fixed by `lens.carried` to 4.3 %. **All 15 arrivals still
  miss through k1**, and T worsens from 1.02 to 1.06 of the truth. **Jacob's:** the new words; k in the report becoming the lens's scale along
  the track; judgement calls (`SEGMENTS` 20, `REACH`, "beats the quadratic" at ratio 1). **Left:** the camera, horizon and focus stages keep a
  pinhole's k, so one report can show two scales 5-10 % apart; `lens_could` is a new key in every miss, which `rerun --strict` will see.
- **`thresholds`** (8355ee1, merged): **M4 as built failed a null** (a wander read as a loop up to 67 % of the time). Now a likelihood ratio against
  the wander, worst drawn 5.1 % and 6.0 %. **Of the 11 recorded loops only PR097 object 3 stays** (and flyer 4, at ± 15); the rest "swing about".
  M5: two ranges, the truth within 1/1.96/3 errors 43/67/80 % on 54 real stretches (was 4/6/15). PR43's 16-84 % goes to 0.43-1.39, nearly all of
  it frame 75. **Jacob's:** accept so few loops, or trade the rate for more; PR097's four share one motion and the line cuts through them (one at
  2.998 errors; a pooled reading in 0.4.x recommended); the card's "it swings about, N widths either side"; the new sentences; two ranges against
  a long wander alone. **Left:** `residual_jitter` still reads the middle 450 points; fixing it moves `fits` and needs M1's null.

### Found by the pause (from the agents' notes; nothing built yet)

- **thresholds:** `thr_null` 14167_6-11 were due to end about 18:30; if requeued they restart and overwrite, and partial
  copies are in `thresholds/runs/partial_1900/`.
- **aot (finished; no code; `aot/notes.md`):** 21 AOT encounters. **False birds: "A bird is the leading explanation" on 5 of 21 known aircraft on
  labelled tracks (a03, a05, a07, s02, s03). Every beat sits on its flight's camera shake (3.50-3.67 Hz, 19 of 20 flights shake at 3.47-3.72),
  and `flicker --scene-shift` says so on 5 of 5, but `run` and the window never ask it.** `beats` cannot stop these. **Agent beats is on it,
  branch `sceneshift` from 56a6fa2: first whether any recorded bird's beat sits on its sensor's motion, then `SHIFT_STANDS` from a null, then
  the gate; nothing merges without Jacob's word, and the case-file remake waits for this.** Also: tau by size on linked tracks claims on 2 of 13, right
  sign, values false (11.2 s against 3.76; 1.27 against 3.69); on near stretches the size route reads T, not tau; light 5 of 21, sign right on all;
  straight and steady held (0 of 21); haze held, 11 of 11 from the aircraft itself; `size-depth`'s narrower bound misses r02 (5.2 against 5.9; the
  old form gave 6.0), stated on a condition the turning camera breaks. Bugs: `run --marks M --track T` drops the polarity (with beats); a false
  zoom on a03; `tau_said` says R / |Rdot| where the route reads Z / |Zdot|. Keep `aot/clips` and `aot/data` (34 GB) until the scene shift is settled.

### Open, in order

1. Release, resume the agents, read their notes; merge as each finishes (text-only conflicts expected: CHANGELOG end, method
   sections, `report.py`'s imports).
2. All 21 suites on the merged tree, all four exercises, the M1 null where the jitter or the projective fit moved.
3. Jacob's calls: frame 75; exercise 4's page if the margin is real; any new card words in the agents' notes.
4. Remake the 14 case files, strict rerun, `cases/README.md` and SHA256SUMS; the census dive.
5. The release, on Jacob's word (session 11's items 2-5 otherwise unchanged; the parallax ladder still waits on N. Long).

---

## Session 12 (2026-10-30, daytime): PR44's rate over the whole track, the card's two rows -- alone, no agents

Jacob: "Next handoff is in docs/handoff-v04.md as usual. Jobs go through /slurm. Spawn agents if needed to utilize the
machine's capacity", then, as the agents were being launched: "looks like I'm almost out of credits, we shouldn't spawn
agents". None ran. I took the two smallest items of session 11's open list 1 myself. **The briefs written for seven
agents are kept for a later session** in `/scratch/mcdonald/v04-s12/`: `BRIEF-common.md` (session 11's rules, updated:
main a76ee84, the 21 suites' counts, "thresholds from a null", Galileo privacy), `WHO.md` (who touches what), and the
seven tasks as I would brief them are the open list below (weight -- now done --, beats, balanced, lens, thresholds,
sizedepth, lanterns). `suites/` holds this session's `snap.sh`, `all.sh`, `one.sbatch` (logs `suites/logs/s12*`).

### Done on main (8092417, then 4637564)

- **PR44's rate, read again: not window lengths but where the windows exist.** Session 11 thought the windows were of
  mixed length (5 and 30 frames) counting one each. From the two kept runs' `pr44_layers.csv` (`v04-s12/main/pr44_windows.py`):
  the windows are one-second means centred on every frame; weighting them by their pairs gives 21.7 and 28.0 -- nothing
  moves. A window needs 24 of its 30 pairs with a background reading; the background was read on 299 track pairs at
  f7f7fad and 221 at 82f6c13 (of 414), so the median is over different stretches while the bird flies 20-40 px/s along
  a still background.
- **Built: `layers.over_track`** -- the one-second windows over the whole track, every second once: each pair against
  a running median (±half a second) of the layer's readings, carried across the frames where it was not read (a few
  5-frame pairs read 40-47 px, something moving). `report.Case.rate` uses its median (old case files keep the windows'
  median); the layers line says both. **PR44: 32.3 and 32.6 on the two builds; the page now quotes 33.**
- **First built as a net rate, and taken back the same day.** 8092417 used the time-weighted net rate over the track
  (PR44 25.7/26.0, the picture's line fit 25.3; what session 11 promised Jacob, "near 25"). Exercise 4 then showed it
  wrong: PR135's relative motion turns back with the camera, and member 7 fell from 99 to 8 px/s, member 8 from 86 to
  15. 4637564 is the windows over the whole track instead; PR135's eight rates are then exactly a76ee84's (read along
  its whole track). **Jacob's:** PR44's number is 33, not the ~25 he was told -- the typical second of a meandering
  bird, not its net drift; the card's "Speed, in the picture" (25.3) is the line fit, so the two differ on PR44.
- **Jacob's card words:** a loop (M4's ellipse) "it loops, radius N widths"; a constant band "steady: changed by at
  most N px/frame" (E12's bound). Help's "Read the report" says both.
- Tests (snapshots, Slurm, niced 100): gui 755 (754 + the loop), golden 181 PASS 0 SKIP (42 min), measurement 508 (+5),
  reduction 494, cli 127 (jobs 14134-41). Exercises 1-3 pass on the final tree (14139, 21 min on 10 CPUs).
- **Exercise 4 (PR135, the count) was already stale at a76ee84**, before today's change (job 14129, the page alone at
  a76ee84; 14133 after: the same lines): 5 of 8 first lines differ. Objects 2 and 6 in the rate only (109 and 142
  against the page's 106 and 82). **Object 4 lost its bird:** "No physical conclusion ... its brightness beats at 8.0
  Hz for one stretch, frames 1309-1368, and not elsewhere along its track: ... too little to name a bird" where the
  page has "Beats like a bird ... 7.8 Hz ... about 75 pixels a second". Object 1's flock is "2 of its 3 members" at
  7.1-7.6 Hz; object 5's rate 120. The count is the exercise's answer, so this is for a bisect (exercise 4 alone, ~30
  min on 10 CPUs: v0.3.10 against a76ee84; the candidates are 82f6c13's layers, M3's held pictures, E4's jumps, M8)
  and Jacob's call before the page moves. Not done.

### Not done, and why

- **The uap case notes** (the Yemen scale and ceiling, the Huey's rotor k): `~/research/uap` has 416 uncommitted
  changes (the drift paper's five tests: the Yemen and Santa Barbara drift JSONs, figures, `santa_barbara_hoist_2018/README.md`
  itself), so I did not edit or commit there. The text to add is in this handoff's session 11 "Deep dive 3" and
  stand-in A (the Santa Barbara row).

### Open, in the order I would take them (session 11's list 1 less what was done)

1. The 0.4.0 report-changers, each an agent's brief in `v04-s12/` if credits allow: **beats** (no "a rhythm of its own"
   from one 2-s window when flicker's own cross-checks disagree; the Galileo arrivals privately; the controls keep their
   beats), **balanced** (`BALANCED` from a null with a stated rate; PR34, PR051's YouTube copy, Svanström 020-024),
   **lens** (k1 as a known, the projective test through it, M1's null rerun), **thresholds** (M4's 150°/3σ/0.8 from a
   null; M5's t_z error: 2-D sandwich, GLS, the Yemen and Galileo misses), **sizedepth** (the camera stage's size
   trend; `depth_bound` from the geometric mean), **lanterns** (the light route over 54-117 s). Then the M1 null where
   the jitter or the projective fit moved, and all four exercises again.
0. Before them, cheap: **exercise 4's bisect** (above) -- why PR135's object 4 lost its bird -- and Jacob's word on
   the page.
2. Session 11's items 2-5 unchanged (the strict rerun of the 14 case files after item 1; the release; the uap notes;
   the dives; the 0.4.x list).

---

## Session 11 (2026-10-29/30, overnight): the cut's report-changers in parallel, drift merged, known ranges

Jacob: "Next handoff is in docs/handoff-v04.md as usual. Jobs go through /slurm. Spawn agents if needed to utilize the
capacity of the Slurm queue overnight." Session 10's open list, taken in parallel: I did items 1 and 2 on main (the
card's words, `drift` merged); six agents took the rest, each in its own worktree (or the uap repository) with its own
Slurm jobs, under one brief (`/scratch/mcdonald/v04-s11/BRIEF-common.md`: worktree only, everything through Slurm,
niced 100, snapshots, no handoff or ROADMAP edits, notes in `/scratch/mcdonald/v04-s11/<name>/notes.md`). Scratch
`/scratch/mcdonald/v04-s11/` (`suites/` the shared job scripts: `snap.sh`, `all.sh`, `one.sbatch`; `logs/`).

| who | worktree / branch | items |
|---|---|---|
| me | main | (1) the card's "roughly, to within N pixels" (8e9817e); (2) `drift` merged as §34 (b8d2a8d on its branch, merge 79a6e62) |
| band | `mcdonald-band` / `band` | E4 jumps named, E1 the band backtested with a traffic light (M8 if birds fail), E12 "constant" a bound |
| proj | `mcdonald-turn-tz` / `turn-tz` | M5's t_z error from the depth algebra, M4 the turn as an ellipse, PR43's power check |
| held | `mcdonald-held-pictures` / `held-pictures` | M3 held pictures tested, not counted |
| ranges | `mcdonald-known-ranges` / `known-ranges` | stand-in A: the bounds against Puerto Rico, Santa Barbara, Yemen |
| adsb | uap `analysis/corpus/galileo_aircraft/` | stand-in B: adsb.lol's eleven days, filtered to the site, geometry per clip, a first match |
| yemen | uap `analysis/cases/hellfire_yemen/size_ceiling/` | deep dive 3: the size ceiling from the sea's motion streaks |

### Jacob's answers (2026-10-30, by multiple choice, at the session's end) -- the next session starts here

| asked | his answer | to do |
|---|---|---|
| PR44's exercise (22 -> 28 px/s since 82f6c13) | **time-weight, then the page** | weight each window of `layers`' `px_per_s` by the frames it covers (both builds should land near the image's 25.3); change `docs/exercises/01-pr44.md` to the new number; a report-changer, before the strict rerun; then all four exercises |
| the false beats on airliners (galtau's finding 1) | **in 0.4.0** | no "a rhythm of its own" from one 2-s window when the stage's own cross-checks disagree; held against the Galileo arrivals (privately) and against drawn data in the tests; the flicker controls must keep their beats |
| the band's light rule | **keep as built** | -- |
| `BALANCED = 0.85` | "Is 0.85 an arbitrary choice? If so, let's find a way to better justify the choice. If 0.85 was determined through testing, then it is fine to keep for now." | It was the survey's line by judgement in the census's gap (real cadences 0.88-1.00, PR34's one window 0.84; non-cadences 0.78 and under), not calibrated. **Calibrate it:** set it from a stated false-alarm rate on random and encoder-held words of each share and length (as NUGGETS was set on a null), check it against the known cadences (PR34, PR051's YouTube copy, Svanström 020-024), say the rate in §35 |
| the card's Turn row for a loop | **"it loops, radius N widths"** | `report_qt._turned`; Help; test_gui |
| the band's proposed card rows | **"steady: changed by at most N px/frame"** only (no "Its error, checked" row) | `report_qt` "Along the track" for a constant band, from E12's bound; test_gui |
| `slew --platform/--los` | **keep** | -- |
| M4's thresholds and M5's sandwich | **revisit both** | before the strict rerun: M4's 150°, 3σ, 0.8 from a null of drawn arcs, wobbles and drifting lines (as NUGGETS was); M5's t_z error -- the sandwich against the 2-D sandwich (74/96 against 68/91 with memory), a GLS fit, and the real tracks where its band missed (Yemen's laser, the Galileo arrivals: 20-85σ) |
| the Yemen scale and the Huey's rotor k | **into the case notes and the paper** | write both into the uap case notes (`hellfire_yemen/README.md`, `santa_barbara_hoist_2018/README.md`); the paper's text is his |
| `layers --k 1` and the background-step route to k | **0.4.x** | -- |
| galtau's (a) lens term, (b) the camera stage's "size holds steady", (c) `depth_bound` past twice the mean, (d) the 105-px edge margin | **(a)-(c) in 0.4.0, (d) 0.4.x** | (a) the lens's k1 as a known, the projective test drawn through it, M1's null rerun; (b) the size's trend, not only its steps; (c) the bound from the band's mean taken geometrically (proj's note: r - 1/r = dv/v̄) or said as none with its reason |
| an email to the Galileo Project | not chosen; Jacob's note on the sites instead (in the uap note, private) | the fit's +14 m is then likelier MSL heights from part of the fleet: test per aircraft |
| PR34's video | **kept in `pursue/`** | done: `/models/data/mcdonald/pursue/DOD_111689011.mp4`, its README row and SHA256SUMS line |

### Where main stands (eaa5300: 16 commits since 3d149b0, 53 unpushed; nothing pushed, no version raised)

`8e9817e` the card's words; `b8d2a8d` + `79a6e62` drift; `6cb9b3e` held pictures (cb545f7); `1a945bc` t_z and the turn
(9e48055, cb7fb5c); `db98c91` the band (1a1abd6, fa47032, cdc5e2f); `eaa5300` known ranges (cf5441c, c25e1de, 5e42fc6);
then this handoff and the ROADMAP's seven rows marked done. Each merge's message gives its branch's suites and numbers.
Conflicts were text only (CHANGELOG items at the end of Unreleased, method sections appended -- the held pictures'
became §35 behind drift's §34 -- and report.py's imports).

**All 21 suites on eaa5300**, from a snapshot of the tracked files, one Slurm job each (niced 100; `suites/all.sh`; logs
`suites/logs/m4_*`, jobs 13999-14019): gui 754 (WxAgg skipped as before), **golden 181 PASS, 0 SKIP (38 min)**,
measurement 503, reduction 494, camera 135, cli 127, drift 92, slew 65, audio 54, published 32, zoom 31, share 25,
horizon 25, tether 24, focus 19, waves 14, stabilize 13, aspect 10, sweep 10, haze 9, streak 8 -- all pass, every job exit
0. Earlier: the card's commit (gui 754, reduction 449, cli 126; 13589-91), the drift merge (drift 92, cli 126,
reduction 449, gui 754; 13628-31), the three merges before known-ranges (db98c91: all 21 pass, `m3_*`).

### Done on main by me

- **The card's words** (8e9817e): `report_qt._straight` "roughly, to within N pixels"; Help's "Read the report"; test_gui;
  method §33, the CHANGELOG's M1 item. The report and summary keep "describes its trend to N px". gui 754, reduction
  449, cli 126 (jobs 13589-91).
- **`drift` merged** (b8d2a8d: the worktree's uncommitted work committed on its branch as it stood; merge 79a6e62):
  method §34 (its §26 on the branch), the CHANGELOG item at the end of Unreleased, README-technical's list and "§14-30
  and §34", tests/README. Conflicts text only. drift 92, cli 126, reduction 449, gui 754 (jobs 13628-31). The `drift`
  worktree (`/hugespace/models/mcdonald-drift`) is left in place, clean, at b8d2a8d.

### Exercise 1 (PR44) fails on main: bisected to 82f6c13

Agent held found it: `test_golden --exercises` on PR44's page fails on main 3d149b0 as on its branch -- the report's
first line says "the object moved about **28** pixels a second against the background" where the page quotes **22**
(the beat, 3.1 Hz, the same). Bisected with the page's check alone (jobs 13942-46, ~25 min each on 4 CPUs): v0.3.10,
d99a347, b8b54f1 and f7f7fad give 22; **82f6c13** (session 4: "layers on a picture that repeats ... a hold unmoved
inside the zero zone", built for PR051) gives 28. That commit raised `AT_ZERO` from 0.5 to 4 px (a pair whose
templates agree, REPEAT_SHARE 0.8, on a shift inside 4 px is an unmoved hold) and made the zero-left-out field read
first, where a second pass had given up (PR44's pictures are mostly held two frames).
- **What moved** (the two runs kept, jobs 14020-21, `/scratch/mcdonald/v04-s11/main/bisect/keep_*`): not the
  background -- both read it still (f7f7fad 75 % of pairs held over 5 frames, the rest still over 30; 82f6c13 98 %; every
  layer's shift 0.01-0.07 px per 5 frames). The object moves 25.3 px/s in the image (`v_px_per_s`). At f7f7fad 239 of
  420 frames had no background reading (no group); at 82f6c13 the second pass reads them. The reported number is the
  **median over windows** of the object's rate against the background (`report.Case.rate`, `px_per_s["all"]["median"]`),
  and the windows are of mixed length (5 and 30 frames) and count one each: 137 windows, median 21.8 (16-84 % 20.4-34.2)
  before; 121, median 28.0 (22.2-40.0) after, the newly read stretches being where the bird flies faster (frames
  8256-8269: ~36 px/s). A second "isotropic" layer now appears (13 windows, 41.9 px/s relative) -- also still in the
  image (0.05 px per 5 frames): a split of the still scene, not a moving one. **Neither number is a wrong reading; the
  statistic is fragile.**
- **For 0.4.0 (the exercise must pass before the release), Jacob's:** (a) change the page to 28, the tool's number now;
  (b) weight the windows by the frames they cover (time-weighted, both builds should land near the image's 25), then
  change the page to that -- my recommendation, as a report-changer under the cut, before the strict rerun; (c) leave
  layers and the page and look further. Exercises 2-4 were not run tonight.

### E4, E1 with M8, E12: the speed band held to account (agent band; 1a1abd6, fa47032, cdc5e2f, merged db98c91; method §32)

- **E4, jumps named** (`kinematics.jumps`, `jumps_said`; `BAND_CLIP_Z` gone): each increment's rate against a robust
  local scale (floored at 0.1 px a coordinate, as JITTER_FLOOR, and at the grid the track is written on), the
  threshold drawn from 400 white tracks on the track's own frames and gaps (familywise 1 %); named a glitch, an
  excursion or a step; glitches and excursions left out of the fit, steps kept and named; the stage's "jumps" line, the
  CSV header, steps marked on the speed figure. Drawn (200 a row): named on 0-1.5 % of clean tracks over nine kinds; a
  4-px glitch found 85 % (168 of 170 called glitches), a 4-px step 79 %, 3-px 24 %. Recorded: 25 of 45 tracks have a
  jump named, 12 lose points. **PR149's two glitches (frames 36, 76) left out: its change of speed now seen (25 ± 4
  px/s, 5.6σ; was 1.7σ), its depth bound 4.6 % -> 0.62 % a second.**
- **E1, the backtest** (`kriging.Model.innovations`, `kinematics.backtest`: Kupiec, Christoffersen, Ljung-Box, ARCH,
  Jarque-Bera; a Basel-zone light and plain reasons in the stage line, the summary row, the CSV header). Drawn with the
  band's own covariance: green 93-98 %. Recorded (44 with a backtest): 7.0 % of one-step predictions miss; 4 green, 38
  yellow, 2 red (PR088 object 2, golden PR144) alone; 5/37/2 with M8. Ljung-Box fails 56 of 88 coordinates alone, 37
  with M8.
- **M8 was needed: the birds fail E1** (PR135's six, Ljung-Box p 1e-27 to 1e-52). `kriging.beat32` (the Matérn times
  cos 2πfτ, plus a first harmonic where that is what is left), fitted where a rhythm is left, kept only where the
  backtest improves and the beat's envelope spans two periods; the band's rate stays the wander's (the flight speed,
  not the bob). A beat kept on 19 of 22 tracks; PR135's members at 7.2-8.0 Hz (p rises to 1e-2...1e-10) but none
  turns green -- what is left is slow, the camera's turn at 44.5 s (E2's break). Flyer 3 clean of its beat but yellow
  for its tails; flyer 1's beat tried and dropped (red with it). Only PR097 object 3 turns green. Drawn 4-Hz beat:
  yellow 40/40 alone, green 37/40 with M8; a beat held on 3 of 60 drawn AR(1) tracks (the rate unmoved).
- **E12, "constant" a bound** (`kinematics.change_bound`, `bound_said`): "a steady change of its speed of more than X
  px/s over the T s would have shown (95 %)"; a band whose change is within its noise gets the larger of its own bound
  and the quadratic's. Holds a steady change 96-98 % on drawn lines, 196 of 197 for wandering bands; no recorded band
  says constant, 11 carry the bound.
- **Verdicts that move** (base -> final): a speed change at >= 3σ newly seen on PR149, PR051's release and PR097 object
  4, no longer on V030; PR097 object 3's depth bound no longer given (its beat held, the change's band reaches the
  speed); no projective verdict moves. **M1's null rerun** (job 13800, all 32 cases at 400 draws, the far 30/60-point
  ones session 9 could not finish): at most 4.8 % past NUGGETS 4 (the far object, 60 points, φ 0.9); PR43 still fits
  at 1.0.
- **Tests on the branch:** reduction 479, cli 126, golden 152 PASS 0 SKIP, gui 754, measurement 491, camera 134, share
  25, horizon 25. Golden 38 -> 46-50 min on 4 CPUs (the M8 fits). One gui run (13840) passed every check, then the
  harness's 565-s budget for the PySide6 child ran out on the saturated machine; unchanged, it passed in 7 min.
- **Jacob's:** steps kept, not modelled as level shifts (most named steps are fast real motion: PR071, PR051, V030; the
  cost FLIR1 exit's nugget 1.3 -> 2.4 px); the jump floor 0.1 px; the light's rule (Basel zones at 95 % plus yellow
  whenever any other test fails at p < 0.01 -- yellow then covers almost every recorded track and the reasons carry the
  news; the alternative, yellow only for coverage and clustering, not built); M8 kept only where the backtest improves;
  E12 against a steady change (a wander too small to see can still move the end speeds past the bound, 4 of 56 drawn;
  the simulated Stock-Watson form would cover it at hundreds of REML fits a band: not built); **card words proposed,
  nothing on the card changed:** a row "Its error, checked": "sound" / "right on average" / "too narrow"; and for a
  constant band "steady: changed by at most N px/frame" in place of "steady, ±...".
- **Open:** `autolink` does not use the jump test on its own output; on long tracks the covariance is fitted on the
  middle 450 points and is too narrow at the ends (PR088 object 2 misses 11.9 %, red).

### M5's other half and M4 (agent proj; 9e48055, cb7fb5c, merged 1a945bc; method §33)

- **t_z's error** (`projective.tz_err`, new field `t_z_err`): the brief's "same algebra" was measured first and fails as
  an error -- centred on the fit's T it is ~6x too wide (0.20 s against a true scatter of 0.033 s, 100 % at one sigma);
  centred on the band's own dv it is biased long (PR43 T 2.2 s against 0.91: the band's end rates 377/782 px/s against
  the fit's 318/1167). Built: a sandwich, the fit's residual along the line given a REML covariance (as the band fits a
  track) carried through least squares, (J'J)^-1 J'SJ (J'J)^-1. `t_z_band` stays 16-84 % (t_z ± the error), so no words
  change; `boot=0` still switches it off, `seed`/`BOOT` gone. Coverage on drawn approaches (100 a case), bootstrap ->
  sandwich at 16-84 / 2.5-97.5: closing 30 points white 70/94 -> 76/96; AR(1) 0.6 39/70 -> 68/91; 15 points 61/80 ->
  70/94; 60 points 65/95 -> 69/98; receding 71/92 -> 76/98; PR43's own model white 68/94 -> 72/97, φ 0.3 57/88 -> 70/91.
  Its limit: 15 points at φ 0.6, 54/86 (a profile interval in 1/T no better; a 2-D sandwich 74/96 against 68/91, kept
  as an option). **PR43: T 0.91 s, 16-84 % 0.81-1.01, 95 % 0.72-1.10** (t_z 3.380 ± 0.098 s; the bootstrap ~±0.07); v/R
  1.06 /s (95 % 0.88-1.34). "fits" unmoved on all 46 recorded tracks (job 13675): the M1 null holds without a rerun.
- **The turn as an ellipse** (`projective.turn`): read whole only when the phase swept and the fitted heading both pass
  150°, the minor axis is 3 of its errors from zero (it goes round, not back and forth), and its rms is at most 0.8 of a
  free quadratic's (heading alone let flat ellipses over short arcs in: 600-2,000 widths on four tracks; the minor-axis
  gate removed FLIR1's exit and Svanström V030). Drawn arcs, true r/D 25: 180° 24.8/25.1/25.7 (sagitta 15-150); 286°
  25.0 untilted and at 70° (sagitta 11.9; 38-755); 360°, 540° 25.0 (sagitta thousands); cos i to 0.01, ω to two
  decimals. A circle drifting at half its speed is a loop; a cycloid or a wave is not. Under 150° the sagitta, its
  words with the tilt's band (from a 4000 x 4000 grid: the picture's radius 0.152-8.50 times the turn's; >= 10x
  straighter 4.25 % of the time, >= 40x 1.06 %; test_reduction recomputes them).
- **Recorded:** PR077 object 1 from "a hair off straight, about 117 widths" to a loop of **23.5 ± 0.3 widths**, 585° at
  1.01 rad/s, plane 84°; loops too (all on moving cameras): PR41 13.1, PR085 7.6, PR088 object 1 3.2, PR097 objects 1-4
  2.0-2.1 (all four together at 1.7 rad/s: the camera's loop), PR099 object 3 10.5, PR135 objects 1 and 4 41 and 43
  (the flock's slew). PR135's other members stay on the sagitta (22-35) with the tilt band; PR43 stays "a hair off
  straight", now "... 118 to 6,560 body widths nine times in ten".
- **Tests on the branch:** reduction 463, cli 126, golden 148 PASS 0 SKIP, gui 754.
- **PR43 dive, part (a), power** (no code): PR43's frame times and line at its jitter, noise three ways (the band's
  nugget, scaled to 8 px, its own residual block-resampled), 200 draws each. Drawn perspective: "fits, closing" 100 %,
  T 0.86-0.97 s. A constant speed-up matched to PR43's 197 -> 1012 px/s: **"fits, closing" 32-70 %, T 0.88-1.00 s --
  the same as PR43's.** Half or three-quarters strength: ~86-100 %, T 2.1 and 1.3 s. PR43's projective fit is worse
  than a free quadratic (rms ratio 1.065), past 98-99 % of perspective draws but at the 2-12th percentile of matched
  speed-ups (likelihood ratio ~4-11 for a speed-up). **26 frames at 8 px cannot tell perspective from a speed-up, and
  the shape leans mildly toward a speed-up**; "its rise is perspective" is not shown. Not modelled: a streak-centroid
  error that grows with the dash. Tables in `/scratch/mcdonald/v04-s11/proj/notes.md`.
- **Jacob's:** the sandwich in place of "the same algebra" (the ROADMAP's M5 row and the survey's §1.2 to re-word);
  M4's thresholds by judgement (150° phase and heading, 0.8, 3σ) -- keep; the new report words (the loop sentence;
  "that radius is the picture's: ... nine times in ten"; "did not turn ... unless its plane held the line of sight
  ..."); **the card's Turn row for a loop: "its path bends, radius N widths" (as built) or "it loops, radius N
  widths"?**; loops on moving cameras are not held to the track's jitter and say "or the camera's own motion" -- keep
  for 0.4.0, revisit with `camera --scene`.
- **Open:** `kinematics.looming_fit` keeps its own residual bootstrap (the sandwich would fit it); `depth_bound`'s
  `_T_from` splits the band's mean arithmetically where the model's is geometric (r - 1/r = dv/v̄ exactly; ~0.9 % at
  PR149's edge, and the exact form would give a weak bound on the 37 tracks that get none: a report change, not made);
  the ellipse's 600-point ω scan could miss on tracks of many tens of turns (none recorded).

### M3, held pictures tested, not counted (agent held; cb545f7, merged 6cb9b3e; method §35)

`flicker.cadence(w, fps, types)`: the held/new word must be balanced (at every window of 2-12 frames at least
`BALANCED` 0.85 of windows within one frame of the word's share, and above the 99th percentile of 200 seeded random words
of the same share and length; `balance`, `least_balance`, `random_balance`), then the GOP's places (`places`, read
lazily through the new `clip.picture_types`, only for a balanced word); the source's rate from the slope, its period
from the continued fraction (`every`, `convergents`), named only when the word is exact. Only a cadence lowers `rate`
and `top_hz`; holds in runs or at random stay `held_k`, missing samples to Lomb-Scargle. The stage's line says how the
pictures are held (`said_pictures`); the look-alike table and "above the highest frequency" name a cadence only for one.
`integrity` and `layers.repeating` unchanged (they read repeats wherever they fall and set no rate; §35 says why).

- **Census** (job 13736, the survey's change series read by the committed code, 300-frame windows; the survey's counts
  exactly): PURSUE 694 windows, 214 lowered before, 3 a cadence now (PR055 at 16.0 and 15.7 pictures a second, PR051 at
  9.9); AARO 1,028/339/40 (all DOD_110982722); Galileo 33/25/0; PR051's two copies 79/70/51 (the YouTube copy at 28-30);
  Svanström 650/227/10 (V_HELICOPTER_020-024 at 24.7-25.2). PR34, where the old rule was made: 34 of 35 windows a cadence
  at 9.85-10.37 (the 35th 0.84, just under); its video is in `/scratch/mcdonald/v04-s11/held/runs/pr34/` (198 MB).
- **Reference case files whose top moves to the grid's 12 Hz:** PR44 5.96 ("more evenly than at random": 0.78 against
  0.21-0.54 for random words), PR141's two objects 9.52, 9.45 (at random), PR149 9.33 (at random: its "no beat" now
  covers 0-12 Hz), PR097 object 8 10.74 (in runs; the survey did not list it). The other 26 objects hold under a tenth.
  The same command on main and the branch (jobs 13680-84): every call, frequency, error and finding identical; only
  what is read over the band moves (the look-alike table, continuum/scramble/false-alarm numbers: PR141's visible copy
  continuum p 0.65 -> 0.23, still no beat; the cases README quotes 0.65).
- **Controls:** PR055's sphere stays lowered (a cadence at 16.0, top 6.4 Hz); the Galileo flyers' tops go to 24 Hz and
  every golden beat passes.
- **The GOP check, changed from the survey's:** compared against the cadence's own slope only, it called PR34-like
  in-step cadences "the encoder's" on long words with a few misreads (1,288 misses for the cadence against 36 for the
  GOP); so the GOP must beat the cadence at its best (its slope or any convergent). In a regular GOP the two cannot be
  told apart and such words stay cadences; it still vetoes holds following an irregular GOP's I frames; on the census
  it vetoes nothing.
- **Tests on the branch:** measurement 503 (491 + 12), golden 159 PASS 0 SKIP (146 + 8 held-picture + 5 flyer band
  checks; 45 min), gui 754, reduction 449, cli 126.
- **Jacob's:** `BALANCED = 0.85` (the survey's line by judgement: real cadences 0.88-1.00, PR34's one window 0.84;
  nearest non-cadences PR44 0.78, flyers 0.56-0.68; at ~0.75 PR44 would count again) -- keep; PR44 is not a cadence
  (mostly held two frames, some one or three, ~15 a second), so its top goes to 12 Hz, its 3.059 Hz beat unchanged;
  the words, in flicker's and run's output only (not the card): "the video holds pictures in a cadence (N% ...), so it
  carries X pictures a second, and a beat is heard only up to Y Hz" / "... at random / in runs / more evenly than at
  random ..., not in a cadence: they are missing samples, not a slower clock, and a beat is heard up to 12.0 Hz".

### Stand-in A: the bounds against the drift paper's three clips of known range (agent ranges; cf5441c, c25e1de, 5e42fc6, merged eaa5300)

| clip | check | the stage says | the truth | holds? |
|---|---|---|---|---|
| Puerto Rico | k, data bar, 82-107 s | 1727 px/deg (band ±1-2 %) | 1657 ± 79 (the same readings regressed the other way: 1725) | yes (+0.9σ) |
| Puerto Rico | k, 82-100 / 82-117 / 100-117 s | 1720 / 1773 / 1844 | as above | yes / yes / **no** (the ground point jumps from the hills to the sea over 100-117 s) |
| Puerto Rico | tau, size route, frames 1640-2231 | no closing claimed; size shrinking -0.0127 ± 0.0066 /s | receding, -0.0103 /s (tau ~-97 s) | yes |
| Puerto Rico | tau, light route (run on its own; the stage skips it for a resolved object) | +0.0054 ± 0.0080, no claim (+85 s "closing" if the background's level is not divided out) | -0.0206 | the gate holds; the curve does not follow the range (the flames' own light changed more) |
| Puerto Rico | `focus`, dark-edge route | object-to-ground ratio at least 0.11-0.34 (lens 5-20 cm); no floor in metres | 0.59-0.66 | yes, 2-5x loose -- `focus`'s first real known range |
| Yemen | projective test on the line of sight (pointer azimuth, laser depression; a camera that does not turn) | fits, closing, T 80.7 s (75.9-87.2) | 92.6 s | right verdict; T 13 % short, its band misses |
| Yemen | depth bound, same | at most 2.07 %/s | 1.08 %/s | yes, twice as wide |
| Yemen | aspect, v/R (with that camera's k) | 53°, 0.0182 /s | 57°, 0.0172 /s | yes |
| Yemen | the object's own track (held on the reticle) | held: no projective test, no bound | -- | yes (after the fix) |
| Yemen | tau, size route | no claim (before the fix: "size held, 80 px" for a 22 x 10 px object) | +100 s | no false claim |
| Yemen | tau, light route (on its own) | +0.063 ± 0.034 before the missile; "22 s" at 3.0σ once it is in the ring | +0.020 (+102 s) | the 4σ gate holds, narrowly |
| Santa Barbara | k from the rotor disc (14.63 m at 297 m) | 86-99 px/deg (±7 %) | no independent k; the disc's shape agrees with the 50° look-down | consistent |
| Santa Barbara | tau, size route; `focus` | no claim (past flicker's 80-px limit); NO POWER (no sharp points) | closing, tau 170-190 s | nothing false; no test |

`horizon`, `haze`, `streak` stay unchecked (no sea horizon from a known height, no daylight haze, no dash of known
exposure in the three).

- **Built:** `slew --platform CSV --los CSV` (the files `drift` reads; ~120 lines, 6 tests): from the aircraft's
  position and the ground point, the line of sight's azimuth and depression and the platform's own share of the turn
  frame by frame, so nothing is fitted for an orbiting aircraft; with azimuth and depression alone it acts as a pointer.
  Golden: `test_puerto_rico_k_from_the_data_bar`, `test_puerto_rico_lanterns_tau_against_their_range`,
  `test_yemen_line_of_sight_against_the_laser` (vendored files, seconds; `puerto_rico_scene_layers.csv` 44 KB,
  `puerto_rico_lantern_curves.csv` 18 KB). **Two bugs fixed that can change reports:** `kinematics.HELD_FLOOR_PX` 0.1 px
  (a track that never moves is held; it crashed) and `kinematics.TAU_CAP_PX` 80 (a size at flicker's 80-px cap is no
  size). Method §17 says the case's 1657 was pulled ~3 % low by regressing on the noisier side.
- **Tests on the branch** (its final tree): golden 160 PASS 0 SKIP (40.8 min), reduction 450, cli 127, gui 754,
  measurement 491, slew 65, camera 136.
- **Not finished:** the light route over the lanterns' full doubling of range (54-117 s; the Find job waited behind the
  night's arrays and was cancelled: only 1640-2231 measured, range x1.2); Santa Barbara's rotor diameter from scratch
  scripts (a frame stack and an ellipse fit, 243-280 px), not a stage.
- **Jacob's:** the names `--platform`/`--los` on `slew` (one file format for `slew` and `drift`) -- keep; the uap Puerto
  Rico README's 1657 (his to update; nothing in uap touched); `HELD_FLOOR_PX`, `TAU_CAP_PX` by judgement (corner cases;
  no tau verdict of session 7's 31 objects changes); fitted results from the private uap case now in the tests with
  attribution (the lanterns' path, the Yemen relative-motion line, the lantern curves measured on the case's track --
  all of public videos; the lanterns' path could come from the drift stage's own fit now); the rotor's k (86-99
  px/deg) gives the drift paper's Huey the field of view its Tests 1-2 lacked -- his call; the projective band missing
  a real truth (80.7 against 92.6 s) is for the GLS form of M1.

### Stand-in B: the Galileo clips against adsb.lol (agent adsb; uap b3cffc3, 287a05f, eda324e, `analysis/corpus/galileo_aircraft/`)

**Private: the outputs pin the camera site, whose coordinates stay in the uap repository until Loeb et al. (2026) is out;
this section gives no position.** Nothing in mcdonald was touched or run.

- **Downloaded and filtered:** 41.4 GB (12 prod releases: the "07-25" folder's clips start 07-24 23:45 UTC, so 07-24 too)
  streamed through a filter, the tars deleted; 12 MB kept (`adsb_kept/`, one CSV.gz a day, every point within 40 km of
  the site during a clip ± 10 min; ODbL 1.0, attribution in the README). 105-399 aircraft a day. **2026-05-05 has no
  traces** in either release: rebuilt from its heatmaps (10-s slices, barometric heights, no callsigns; the decoding
  checked against 02-02, where both exist). Heights: geometric for 99-100 % of points but 05-05 (barometric at cruise
  was off by up to 2,550 ft). 149 clips are 900 s at 60 fps; three 02-26 clips are broken (no moov atom); the burned-in
  clock counts frames and runs 0.095 s before the file name's time.
- **Geometry:** the site's height 556 ± 10 m above the ellipsoid (SRTM + EGM96, nothing sent to a service); an
  airport's final approach passes close by (30-68 airliners a day at a few hundred metres' height), so 2,309
  aircraft-slots within 15 km (`tables/`).
- **The cameras fitted** (an own detector and linker: 0.5-s frame means, tracks started only from straight steady
  motion; each camera's pointing, focal length, one distortion term, a clock offset): **the lens 13.10-13.21 px/deg at
  the centre (+2-3 % on the published 1.36 mrad/px), k1 -0.41 to -0.45, 50.2° across (published 50°).** On 02-02 cam-1
  34 tracks 0.87 px rms, cam-3 58 tracks 0.96 px, cam-5 29 tracks 0.91 px; a left-out track predicted to 1.05-1.22 px
  median, 2.7-3.0 px at most. The mount did not move February to September (cam-1 within 0.2° on six days, cam-5 on
  four, cam-3 on two; 02-02's cam-1 model puts all 12 tracks of 02-05 within 8 px at clock offset 0, none at ±2 s). Cams
  1-5 sit at (n-1) x 360/7 in azimuth, 28-32° up: a ring of seven. The Sun, with no ADS-B: cam-3's model puts it within
  1.2-5.2 px in nine frames. The site's height left free improves the fit (0.96 -> 0.74 px) at +14 m: the mount ~19 m
  over the SRTM ground, or MSL heights from some aircraft -- open.
- **Known ranges: 242 tracks, 50,536 points** (`match/truth/`: the aircraft, slant range and range rate at every point);
  76 under 5 km, 69 whose range changes by more than 1.5x in view; **the smallest tau 10-26 s** (arrivals in cam-3 closing
  from ~4.5 to ~2 km in ~25 s: looming with the answer known); distant traffic (tau 90-400 s) the no-looming control.
- **Not working:** 05-05 matches on no camera (no clock offset -20 to +20 s, no height scale -4 to +12 %: re-aimed, or the
  heatmaps too coarse -- undecided); cams 6-8 unfitted and some camera-days too few tracks (one clip a camera-day was
  processed); only 2 of the full-rate `galileo/det` tracks are aircraft (the rest birds and insects).
- **Jacob's:** `adsb_kept/` and the truth files stay private until the paper (then ODbL's same licence and attribution);
  whether to ask the Galileo Project for the mount's height and whether anything changed before 05-05.
- **Next (started tonight as agent galtau):** the truth tracks through mcdonald -- tau by looming and light, T and the
  depth bound, k and the speed band, focus -- cam-3's 02-02 arrivals the looming set, cam-1's distant traffic the control.

### Deep dive 3: the Yemen object's size ceiling (agent yemen; uap adb72af, `analysis/cases/hellfire_yemen/size_ceiling/`)

**A result, by another route than planned.** The streaks are **not motion blur** (they lie ~8° off the sea's step and
wander 22-45°; doubling the motion adds 1-4 px to them; they shorten as the step grows): they are the sea's own
elongated texture, so the streak bound has nothing to work with. But the sea **steps** 25-34 px a frame between
consecutive frames while the turret holds the object (108-596): a frame-wide masked cross-correlation held on the
reticle peaks in every pair (NCC median 0.84). With the sea's angular rate from the geometry (the laser's ranges,
fit3d's line, the sea at H/sin(depression)), k = 30 x step / rate:

- **k = 2,468 px/deg** (copy pixels, frames 556-590) if the object stood still over the sea; 2,365-2,511 if it drifted
  with any of the 72 archived winds. Systematics at their worst together -6.3 % to +6.5 % (the sea's own motion up to 3
  m/s ±3.3 %, pixel aspect ±1.3 %, keystone ±1 %, scatter ±0.8 %); statistical 0.4 %.
- **Scale 3.8-4.6 cm/px at 5,884 m; the object's 22.3 x 10.3-px outline 0.86-1.03 m long, 0.40-0.48 m wide.** The field
  of view: the copy's 328 rows span 0.123-0.148° (0.136° fits; 0.10° does not).
- **The ceiling, assuming nothing of the object:** the airspeed is the one input the picture does not give; over 0-260
  kn and all 72 winds the object is **at most 2.0 m long** (0.60-1.47 m at 100-240 kn). A Samad-2 seen from 40.5° above
  is at least 2.83 m at half contrast: it would need the aircraft flying backwards at 150-158 kn.
- **Checks:** the steps' direction 45° falling to 38° against the geometry's 41° to 34.5° (a constant 3.2° offset, 0.1-0.9°
  of it the copy's own tilt from the corner brackets; the 7° swing reproduced); the step grows 1.33x where 1.31x is
  expected; one k fits all 17 blocks to 1.7 % rms with no trend (no zoom); the line's turn rate against the pointer
  0.997; the sea's range from the geometry against the laser's sea readings within 0.9 %; before the laser (2-107) k
  2,405-2,524; the missile's 3.8-6.0-px width 0.16-0.25 m (the 0.18-m body fits). Held pictures at 33, 300, 413 (the
  case notes said none in 1-790: hidden under the re-recording's noise).
- **Uncertain:** the pixel aspect (square to 3 %); the sea's own drift (if the whole 3.2° offset were drift, ~5 m/s,
  6 % on k; low cloud at 10 m/s would move k ~11 %); the length is the apparent extent at half contrast, blur included.
- **Against the paper** (the text is Jacob's): "nothing in the copy sets an upper limit" -- the sea's step sets one.
  No test of the paper changes (none uses the scale).
- **For mcdonald (0.4.x, nothing built):** `layers --k 1` finds the same step in every pair (879 px/s median, agreeing
  pair by pair to ~0.1 px); 0.3's "NO POWER" came from the default `--k 5`, over which the sea moves 125-175 px -- a
  one-frame baseline when the scene moves fast is the cheap fix. The real gap is a route to k for a held line of sight
  whose background lies at another range (`slew`'s X = a + cθ + bt cannot separate c from b here): the geometry as
  knowns (the held object's relative motion, the background's range, the aircraft's heading, airspeed and wind);
  `ceiling.py`, `geometry_sea.py` are the prototype. A re-recording's own scale drift is measurable from the symbology
  (2.6 % over 16 s here).
- **Jacob's:** whether this scale goes into the case notes or the paper; whether the background-step route to k is
  wanted in 0.4.x.

### The Galileo aircraft through mcdonald (agent galtau; uap 094b514, `analysis/corpus/galileo_aircraft/mcdonald_vs_truth/`)

Private outputs (the truth pins the site); no aircraft, place or clip time here. mcdonald unchanged (no worktree). Main
at eaa5300 from a snapshot, through Slurm (jobs 14032-14101; a ~2000-frame case peaks at 3.3-3.9 GB, a 4604-frame
segment's track sheet past 6.2 GB). **Cases:** 15 airliner arrivals in one camera on one day, each closing from ~3.8-4.1
to ~0.9 km over 30-40 s (the truth's tau 23-30 s at mid-track, 11-13 s at the last frame), and 4 controls at 5.5-15 km;
the truth on every frame from the adsb agent's geometry through its camera model. **Find did not propose the arrivals**
(they loom more than they move): marks were placed at the model's pixel as an agent's, mcdonald linked them, then `run
--fov 50.2 --fov-px 640 --band lwir`.

| reading | mcdonald | truth | held? |
|---|---|---|---|
| tau, size route | none on all 19 ("its size was read on 0 frames") | closing, tau 11-13 s | nothing false, nothing read: `flicker.extent` refuses an object within 105 px of an edge, and every arrival's path lies in that margin (60 % of a 640 x 512 frame) |
| tau, size off the object's own image (scripts: the camera stage's `length_px`, the patch above half its peak) | closing, 0.63-0.90 of the truth (median 0.71), band 1-2 % | 11-13 s | right sign, 10-37 % short, 10-40σ out: the measured size grows faster than 1/R (the looming law gives 4-11 % of it) |
| tau, light route (a condition) | 11 of 15 arrivals: mid-track 0.75-1.13 of the truth (median 0.99), 7 within 2σ, 9 within 15 %; none on 4 (a beat found) | 23-30 s | **held, mostly** |
| tau, light route, controls | c1 "+52 ± 4 s" closing, c4 "-137 ± 13 s", none on c2, c3 | +617 s, -280 s | right signs, 10x and 2x short; the stage's "if the change were its range's alone" covers it |
| straight and steady, whole tracks | "describes its trend" on all 15 arrivals (8.7-19.2 jitters); "fails" on c1, c2, c4 | approaches slowing 0.2-0.5 m/s²; straight crossings | right about the picture, but the words cannot name **the lens**: a straight steady path through the Boson's barrel (k1 -0.45) misses by 1.4-1.8 px on the arrivals, 1.5-6 px on the crossings, and exactly fits through a pinhole |
| T the stage computes but withholds | 0.94-1.22 of Z/-Ż (median 1.02) | 10-12.4 s | within 6 % on 12 of 15 |
| first two thirds of a1-a5 (`kinematics --n1`) | a2, a5 fit, closing: T 22.34 ± 0.14, 19.83 ± 0.04 s; aspect 13.5°, 12.9° | 19.35, 22.80 s; 12.5°, 13.9° | T within 13-15 %, aspect within 1°, but the band misses by 20-85σ -- the Yemen laser's pattern |
| depth bound | none on whole tracks (the ends taken as v̄ ∓ dv/2 go negative when the image speed grows 13x); 15 and 20 %/s where given | 4.5, 4.8 %/s | held, 3-4x wide |
| k from the assumed 50.2° | 11.92 px/deg (the pinhole formula) | the lens 13.2 at the centre, 11.3-13.2 along these tracks | 10 % low at the centre; -5 to +10 % where the aircraft were, by chance |
| the speed band over k | 1.04-1.12 of the true angular rate over each track (0.94-1.04 with the lens's local scale); the last frame within 10 % on 9 of 15 | 0.1-2.6 deg/s | held over the track; the last frame fragile (the link hops between a large aircraft's hot parts: 19-56 % low or 75-215 % high on six) |
| focus | NO POWER on every case (too few points: sky) | -- | nothing false; no test |

**Found, each Jacob's to decide (no fix made):** (1) **false beats on airliners** -- four of 15 headlines report a 1.7-4.9
Hz beat from one 2-s window near the track's end (a 4-px point's aperture, no extent read, on a 25-px aircraft whose
track hops); one (a2) says "a rhythm of its own and not the video's" though the stage's own astronomer's and
seismologist's checks disagree, the other three are qualified ("too little to name a bird"); (2) the camera stage says
the size "holds steady" while its own `length_px` grows 5x (it looks only for steps); (3) the projective words cannot
name the lens: a lens term (k1) as a known, with the M1 null rerun; (4) the t_z band too narrow on real tracks (model
error under NUGGETS absorbed into the fit, not the residual: with the Yemen line, for the GLS form of M1); (5)
`depth_bound` gives nothing when the image speed changes by more than twice its mean (the band's own end rates instead
are not robust here, 0.5-1.67 of the truth: cf. proj's geometric-mean note); (6) `tau_of` tries the light route with no
size read at all, though the aircraft is 6-30 px across (it worked here); (7) the extent's 105-px margin cannot simply
go (padded, the far ring reads cloud: a false "receding, -44 s" on a1); (8) the linker refuses marks spread over a
looming object (one spot size for every mark). **Left:** focus needs sharp points (stars at night); two of the four
controls clean (c1's link trimmed by hand where a faster object captured it; c3 linked for 2 s); a size route that works
on these aircraft is not built. Notes `/scratch/mcdonald/v04-s11/galtau/notes.md` (no site), `runs/` kept (617 MB).

### Open, in the order I would take them

1. **The 0.4.0 work Jacob's answers add** (the table above), all report-changers before the strict rerun: PR44's
   time-weighted median and its page; the false beats on airliners; galtau's (a)-(c); M4's thresholds and M5's error
   revisited; the card's "it loops" and "steady: changed by at most"; `BALANCED` calibrated. Then all four exercises
   (`test_golden --exercises`, ~1 h on 10 CPUs) and the M1 null where the jitter or the projective fit moves.
2. **What 0.4.0 still needs under the cut** (session 10's list): (8) the parallax ladder's fix, on hold for N. Long;
   (10) the known-range checks left: `horizon`, `haze`, `streak` (none of tonight's clips can), the lanterns' light
   route over their full doubling of range (54-117 s), focus on sharp points of known range (stars); (11) `share rerun
   --strict` on the 14 case files and the recipe's remake -- every report with a track changes (jumps named, the
   light, E12's bound, loops, t_z's band, the held pictures' band top on PR44, PR141, PR149, PR097 object 8, and the
   above); (12) the release.
3. **The uap case notes:** the Yemen scale and ceiling, the Huey's rotor k (Jacob's answer); the Puerto Rico README's
   1657 (ranges' note: pulled ~3 % low).
4. **The dives:** PR43's (b)-(d) (its brightness as a second clock, the dash's length against the rate, v = R/T with
   focus's bound) -- part (a) says 26 frames cannot tell perspective from a speed-up; PR051's release null with a
   farthest-range known (`--range` takes a value; a `--range-max` known is the small build it needs); the census from
   the strict rerun.
5. **0.4.x, noted tonight:** `layers` on a fast scene with a one-frame baseline and the background-step route to k
   (Jacob: 0.4.x); flicker's 105-px edge margin (galtau's (d)); a size route for looming aircraft; Find on objects that
   loom more than they move; the linker with marks of growing size; `looming_fit`'s bootstrap to the sandwich;
   `autolink` using the jump test; the band's covariance at the ends of long tracks (PR088 object 2 red); the GLS form
   of M1; E2 (PR135's camera turn at 44.5 s left in every bird's innovations); the Galileo cams 6-8, 05-05 and the other
   camera-days.

**Left behind:** the four worktrees made tonight (`mcdonald-band`, `-turn-tz`, `-held-pictures`, `-known-ranges`) removed
and their branches deleted, all merged; the `drift` worktree left as it was (clean now, at b8d2a8d, merged). Scratch `/scratch/mcdonald/v04-s11/` kept:
`BRIEF-common.md` (the agents' brief), `suites/` (the job scripts and every log), each agent's folder with
`notes.md`, scripts, runs and logs, `main/` (the merge messages, `resolve_drift.py`, the bisect's scripts and logs and
the two kept PR44 cases without their frames); PR34's video moved to `pursue/` (Jacob). Every snapshot removed; nothing in `/tmp`; the frame cache `~/Documents/mcdonald/frames` untouched.
Everything that ran the package went through Slurm.

---

## Session 10 (2026-10-29): a step back -- Jacob's answers, where 0.4.0 stands, its cut, known ranges without the Galileo ADS-B, the drift paper, four deep dives

Jacob: "Next handoff is in docs/handoff-v04.md as usual. Jobs go through /slurm. This time, let's step back a bit
before continuing": (1) outstanding questions, by multiple choice; (2) a progress report on 0.4.0; (3) a plan for the
Galileo Project's ADS-B data coming late; (4) whether anything in 0.4.0 improves the wind-borne drift paper's
results; (5) a science result with 0.4.0, and which cases deserve a deep dive. **No code changed and nothing ran the
package** (no Slurm job). This section, the ROADMAP (decision 8 and objective 3's validation line), and a private note
in the uap repository (`analysis/corpus/galileo_aircraft/README.md`, which holds the Galileo site's coordinates;
**they never go in this repository** -- they come from a paper not yet published) are the session's output. Committed
locally, not pushed.

### Jacob's answers (by multiple choice)

| asked | his answer | to build |
|---|---|---|
| the card's words where the straight-and-steady model misses by more than NUGGETS jitters (session 9's "describes its trend to N pixels", my words) | **"roughly, to within N pixels"** | `report_qt._straight`, Help's "Read the report", test_gui's check. The card only was asked: the report's sentence keeps "describes its trend" |
| the plain form's new questions (the height over the sea, the horizon's click, how far one could see, the camera's kind): before or after the speed questions | **after, as built** | nothing |
| `mcdonald drift` (uncommitted files in the `drift` worktree, which sits on f74b4d4, 115 commits behind main) | **merged for 0.4.0** | commit it on its branch, merge; its method section becomes §34 (main's §26 is the Middle East Object; the paper cites no section number); its inputs are vendored in `tests/golden/{hellfire,puerto_rico,santa_barbara}_drift/`, the videos already in the data folder |
| where 0.4.0 is cut | **whatever changes a report goes in, the rest goes to 0.4.x** | ROADMAP decision 8; the list below |
| which deep dives go with 0.4.0 | **all four**: PR43, the census of the 14 case files, the Yemen object's size ceiling, PR051's release null | below |
| the Galileo ADS-B | the site's coordinates are in **Loeb et al. (2026, submitted)**; he gave them | match the clips to a public ADS-B archive ourselves (below) |

### Where 0.4.0 stands (main c4803f3: 37 commits since v0.3.10, 39 items in CHANGELOG's Unreleased, nothing pushed)

| objective | built | held against | left |
|---|---|---|---|
| 1. k from the camera's own motion | `slew` (§17) with zoom states; `zoom` with no blank and over streaming ground; `camera --zoom`; K9's per-template errors; `layers` on a picture that repeats; the pointer sweep (127 clips: the ladder x2.00, x5.9) | synthetic pans within 7 %; across measured zoom steps PR27 267 -> 517 and PR057a 276 -> 584 px/deg (x2.00, agreeing); PR051's scene over its pointer 2160 px/deg against the bar's 2230, by hand | **no external known answer through `slew` itself** (PR051's dial stalls: NO POWER is right); E14-E17, M6 to 0.4.x |
| 2. range and size without motion | `horizon` §27, `focus` §28 (and the dark edge), `haze` §29, `streak` §30; each a step of `run` and asked in the plain form | rendered scenes; the Middle East Object's blur (σ 1.27 against the hand fit's 1.30-1.42) | **no bound held against a real known range** |
| 3. what survives the missing variables | the admissible region (M2), the projective test held to its jitter (M1), "no closing seen" a bound (M5), the dimensionless numbers, tau from the flicker stage, the time-distance diagram | drawn tracks and approaches; the 46 recorded tracks (24 of the 25 the models pass describe their trend; PR43 fits) | M4 and M5's t_z error in 0.4.0; E22, A16, Av10, Av11, D8, K10 to 0.4.x; **tau on a real closing object** (none of the 31 recorded objects claims one) |
| 4. a speed with a band | K1, K8, K9 (§32) | drawn tracks (the band holds 94 %); the 46 recorded tracks | E1 (with M8 if the birds fail it), E4, E12 in 0.4.0; E2, E3, E6, E20 to 0.4.x |
| 5. what is known, extended | `--range`, `--range-ratio`, `--ground-speed`, `--own-ship`, `--height`, `--horizon`, `--visibility`, `--band` and the rest of `stages.KNOWN` | test_reduction, test_horizon | the sensor's azimuth and depression as knowns (the Puerto Rico check below needs them: in 0.4.0 if it does), a farthest range (PR051 below), a field of view from a geolocation, a range from a correlated track (the ADS-B match), a stereo pair: 0.4.x |
| 6. the unknowns ledger | the report, the summary, the card's four rows, `run`'s steps, the plain form, in Jacob's words | test_reduction, test_gui | done |
| M3, held pictures (from 0.8) | -- | the survey's census | in 0.4.0 (it changes three case files' "no beat" coverage) |
| the parallax ladder's fix | -- | -- | in 0.4.0, on hold for N. Long's revision; if everything else is done first, ask Jacob whether 0.4.0 waits for it |

### What 0.4.0 still needs, under the cut

Report-changers, all before the strict rerun: (1) the card's "roughly, to within N pixels"; (2) E1, the band
backtested on its own track with a traffic light, and M8's quasi-periodic kernel if the birds' bands fail it; (3) E4,
jumps named in place of the one-pass 4-sigma clip (it feeds the band); (4) E12, "constant" as an upper bound on the
change it could have missed; (5) M3; (6) M4, the turn as an ellipse past about 150°; (7) M5's other half, t_z's error
from the depth algebra (only PR43 fits, so it reaches PR43's T: the PR43 dive needs it); (8) the parallax ladder's fix,
on hold. Then: (9) `drift` merged; (10) each bound held against real clips of known range (next part); (11) `share
rerun --strict` on the 14 case files and the recipe's remake, which is the census dive's input; (12) the release:
version, CHANGELOG, README-technical, the macOS and Windows runners, the tag (PyPI, the website), the case files.

### Known ranges without the Galileo Project's ADS-B

What waits on a known range: tau by looming and by light, θ = atan(ωτ), the straight-and-steady test's T, the depth
bound, the focus, haze and horizon bounds, and k through mcdonald's own routes against a truth. Three stand-ins, in the
order I would take them:

- **A. The drift paper's three videos** (in the data folder; the uap case notes have every reading). *Puerto Rico*
  (AARO): the display prints the aircraft's position, height and heading and the line of sight's ground point in
  every frame (read every 2.5 s; its azimuth agrees with the computed one to 0.3° rms); the case work calibrated 1,657
  px/deg from the ground point against the scene's motion; the lanterns' path from 39 lines of sight puts them 2.1-4.5
  km away through a 157° turn in 95 s. So k by mcdonald's route (the line of sight's azimuth and depression given in
  place of a pointer) against 1,657, and tau's light route against the known R(t) (the range doubles: the flux should
  fall about 4.6 times; flames flicker, so a hard test). *Santa Barbara*: the OH-58A's position (0.01") and height,
  the stored hoist site the turret held (3,114 ft), the UH-1H hovering 40-90 ft over it, so the range in every frame to
  within the hover's offset, and a body of known size (main rotor 14.6 m): k from the known size, then focus on a
  resolved thing at a known range, and looming against the orbit's change of range. *Yemen*: the laser's S and G and
  the north pointer, the object 5.84 km off with a relative motion of 100.5 m/s: from the range's steps its tau is
  of order 100-170 s, while its length changes with its aspect (22.3 px, 14.6 at the smallest), so the check is
  that tau claims no looming the laser does not see; and the depth bound against the laser's range rate.
- **B. The Galileo clips against a public ADS-B archive** (possible now: Jacob gave the site). adsb.lol's daily
  `globe_history` dumps (ODbL, free, no account; GitHub releases `adsblol/globe_history_2026`, about 3.9 GB a day)
  hold **all eleven clip days** (checked with the GitHub API); OpenSky's history (free for research, on request) is the
  cross-check. The clips' names carry UTC to the millisecond. Steps in the uap note: keep the traces within ~40 km
  of the site, find the aircraft in the clips, fit each Boson camera's pointing and k from the first matches, then
  range and range rate every frame. Airliners a few km off close slowly, so this checks k, focus and the light curve
  more than looming.
- **C. Amazon's AOT set** (Registry of Open Data on AWS, CDLA-Permissive 1.0, no account:
  `s3://airborne-obj-detection-challenge-training/part{1,2,3}/`): `range_distance_m` every frame for the planned
  aircraft, and `valid_encounters_maxRange700_maxGap3_minEncLen30` listing encounters within 700 m lasting 3 s or more;
  2448x2048 visible at 10 Hz, by day. Closing encounters for looming tau and T, a dark aircraft against the sky for
  haze, focus. A subset of about 20 encounters (several GB each) on `/scratch`. Not checked: whether the own aircraft's
  position and attitude are in the metadata.

None gives a sea horizon from a known height (Yemen looks 40° down, the lanterns are looked down on, the hoist site is
inland): `horizon`'s check stays open.

### The drift paper against 0.4.0 (what the tools show; the text is Jacob's)

`manuscript/hellfire_yemen/` in the uap repository (its Overleaf repo up to date, 7863d2b): Tests 1-3 (the height,
the winds, the beat) and Test 4 (the tracer, the remains) on the Yemen clip, with the Puerto Rico lanterns and the
Santa Barbara Huey as controls. **No outcome or verdict changes under 0.4.0 as built.** Where it bears:

- **The object's size.** The paper has the scale at least 3.2 cm/px from the missile (the object at least 0.7 m) and
  "nothing in the copy sets an upper limit". In 0.3 no route to k reached the copy (`layers` no consensus over the
  streaking sea, `waves` too little texture, `zoom` matched weakly). The candidate is the sea's motion streaks (deep
  dive 3). 0.4.0's `layers` changes were for streaky ground (PR051): worth one re-run on this copy, though I expect the
  shift along a motion streak to stay unreadable.
- **The rates' errors.** Tests 4a and 4b fit lines and quadratics with a moving-block bootstrap; the speed band (§32)
  would give the track's own-covariance error and the acceleration as a likelihood ratio, and E12 "steady" as a bound.
  The outcomes sit far from their lines (0.82 against 1.30 lengths/s; -0.08 ± 0.06 against 0.37 lengths/s²): errors
  change, outcomes do not. Test 2's relative motion (100.5 ± 0.6 m/s, reduced χ² 7.3) is fitted to display readings,
  not to a track in pixels, so the band does not apply to it as built.
- **The Huey's "cannot say" on Tests 1 and 2.** No field of view, so no angle off the lines of sight. The known-size
  route (the rotor at the hoist site's range) gives k and so the angle; Tests 1 and 2 could then run from the
  aircraft's track and would be expected to pass a hover in calm air, as the paper's Discussion argues -- measured, not
  argued.
- **Test 3.** The Yemen copy's 41 % floor is the sea's own flicker; nothing in 0.4.0 lowers it. M3 lowers a band's
  top only for a cadence (integrity found no repeats on frames 600-760). A beat in the track's position (E6's flag, M8)
  would be a second channel; not built.
- **The other way round:** the paper's three videos are 0.4.0's best known-range clips (stand-in A).

### The four deep dives (Jacob chose all four)

1. **PR43: perspective, not a speed-up.** Its dash, a reference case file whose rate rises from about 7 to 33
   px/frame over frames 50-75, and a case of the Technical Note's first submission (R1 uses PR113 and PR149): the only
   recorded track the straight-and-steady model fits (at 1.0 of its 8-px jitter; T 0.91 s; θ 35-39° at an assumed
   65.6°). (a) Power: tracks with a real speed-up drawn at its jitter and length -- how often does the projective model
   "fit" them (E22's set on one track); (b) its brightness as a second clock -- an unresolved steady thing closing as
   1/(t_z - t) brightens as (t_z - t)^-2 (the flicker stage's level, the gain out); (c) the dash's length against the
   rate (`streak`: 15.6 ms at the 3.6-px blur); (d) then v = R/T along one line, with focus's bound on R. Needs M5's
   t_z error. Either result serves: "its rise is perspective", or "26 frames cannot tell perspective from a speed-up".
2. **What the pixels constrain, case by case** (the ROADMAP's science deliverable fed by 0.4): from the strict rerun,
   for every object the ledger, the band, straight-and-steady and the depth bound, the admissible region under both
   measures; the Technical Note's two cases first (PR113, k from its graticule; PR149, "no closing seen" now under 4.6
   % a second). After every report-changer.
3. **The Yemen object's size ceiling.** The sea's streaks can be no longer than a frame's motion (the exposure is at
   most 1/30 s); the laser geometry, the heading (144.9°), the airspeed (179-190 kn) and the winds give the sea's
   angular rate against the held line of sight; so the streak's length floors the sea's speed in pixels, hence k,
   hence ceils the scale and the size. First check that the streaks point where the sea should move (if not, they are
   not motion and it stops); the length less the blur by `streak.motion_px` (the copy's blur 2.2-3.8 px); the sea's
   own texture length along a streak bounded by its width across. Inputs in `analysis/cases/hellfire_yemen/`
   (`geometry.json`, the stage's JSON) and the clip in `/models/data/mcdonald/hellfire_yemen/`. A session to know.
4. **PR051's release null, written up.** Session 5's numbers (the camera not turning while the gate held or during the
   dash; the drift 0.0079 deg/s, the dash 0.11) plus the ground as the farthest range: at the slant range 41.7 km the
   drift is at most 5.8 m/s across the line of sight, and the dash, if it is the object's, at most about 80 m/s. Needs a
   farthest-range known (`--range` takes a value, not a bound). The companion note (`velocity_limits/overleaf/
   pr051_note/`) reads Segment 2 as a display artifact of the mode change; the tool says only that the camera did not
   turn in either segment.

### Open, in the order I would take them

1. The card's words (item 1 of the cut): small, then test_gui.
2. `drift` merged (item 9): commit on its branch, merge, §34, its suite with the rest. Early, so its 115 commits of
   drift do not grow.
3. The report-changers: M5's t_z error, M4, E4 then E1 (with M8 if needed), E12, M3.
4. Known ranges, stand-in A, then B (the eleven adsb.lol days through a Slurm job), then C; each bound's real check
   into its method section and a golden where the data may be shared.
5. The dives in this order: PR43 (after M5), Yemen's size ceiling (any time; it changes no report), PR051 (with the
   farthest-range known), then the census from the strict rerun.
6. The strict rerun and the remake; the release.
7. Session 9's items 4 and 6 (the GLS form of M1; `streak`'s speed per frame from the band, the sweep's open items,
   `camera --scene` into `run`, Find/Follow on a saturated bloom, `slew` on a dial that stalls) to 0.4.x unless a
   dive needs one.

**Left behind:** no job run, nothing in `/tmp`; no scratch folder made. The uap note is committed by itself (the uap
working tree had uncommitted changes this session did not make; left alone).

---

## Session 9 (2026-10-29): the projective test held to the track's own jitter (M1), "no closing seen" a bound (M5), the admissible region under a named measure (M2)

Jacob: "see docs/handoff-v04.md and remember to use /slurm". Session 8's list opens with Jacob's look (item 1), then
two items that wait on data that is not here (a real clip of known range for each bound; tau on the ADS-B aircraft).
The ROADMAP's 0.4 objective 3 names the pure-mathematics survey's M1 **first, because it changes reports now**, and
every report change has to land before the case files' strict rerun (item 3). So this session took **M1, then M5 and
M2**, the survey's other "hours" ports to objective 3, all in `projective`/`kinematics`. On main, **committed locally,
not pushed**; no version bumped; CHANGELOG's Unreleased has three new items (M1, M5, M2). The queue was empty at the start (no job imported the checkout), so the edits were made on main's
checkout. Scratch: `/scratch/mcdonald/v04-s10/` (`scripts/` the measurements, `runs/` their output, `logs/`,
`suites/` the job scripts and logs; the snapshots the jobs ran from removed at the end).

### What was built

| what | where | tested by |
|---|---|---|
| **M1: the projective test held to the track's own jitter.** The three models were compared only with one another; the one chosen (projective where `closing` is True, constant speed where False) is now held to the jitter, read twice -- the speed band's nugget, and the nugget of the band's covariance fitted to the model's own residual -- the larger taken, each axis at least 0.1 px. `fits` within NUGGETS = 4; otherwise the verdict is "describes its trend to N px" (card: "... pixels"), and no T, θ, v/R or t_z band is given (the bootstrap is skipped). New fields `jitter_px`, `jitter_from`, `misfit`, `fits`; `fit(band=)` takes the stage's band (fitted itself when None, `{}` for none) | `projective.fit`, `residual_jitter`, `band_of`, `NUGGETS`, `JITTER_FLOOR`, `trend_px`, `held_to`, `said`; the summary's row; `report_qt._straight`; `Case.survives` (tau's agreement only where it fits); Help's "Read the report" | test_reduction (fits on drawn pinhole tracks; a far object under a 2-px camera sway passes the models but describes its trend, 12.5 jitters; an exact track held to the floor; no jitter under 10 points with no band; the stage's row and bottom line); test_gui (the card's "describes its trend to N pixels"); test_golden (PR43 fits, 1.0; PR077 object 1 and PR135 members 5, 6 describe their trend) |
| **M5: "no closing seen" a bound.** Under the projective model v_end/v_start = ((T + L)/T)², so the band's change of velocity along the track (±1.96 σ) bounds \|T\| from below on both sides and \|Ż/Z\| = 1/\|T\| from above: "if it flew straight at a steady speed, its depth changed by less than X % a second ... at least T₁ s from the camera's plane if closing and T₂ s if receding". Its error is the band's per-axis error taken along the track, floored by a free quadratic's curvature error (a band whose REML fits the wander to nothing reads dv as 0 ± 0.0006 px/s: the bound missed the truth 6 in 40 before the floor, none after). Where the track fits: the summary's θ row "θ ≥ X°" and the ledger's θ "bounded" (tan θ > ω / b, with k), and the admissible region a wedge (\|Ṙ\| ≤ bR); where it describes its trend, said as a condition of the trend and nothing else | `projective.depth_bound`, `depth_said`, `pct`, `DEPTH_Z`; `fit`'s `depth`; `kinematics.speed_band`'s new `dv_xy`, `dv_err_xy`; `admissible_region(rate_max=)`; `Case.depth_rate_max`, the ledger's and summary's θ | test_reduction (20 drawn approaches: the bound holds the truth 19 times; the far object's sentence; the floor; the ledger's θ ≥ 81° and the wedge on a far drawn object that fits); test_golden (PR23 under 1.6 % a second, PR149 under 4.6 %, both said of the trend) |
| **M2: the admissible region under a named measure.** The extent exact (the least speed at the nearest range; the most the cap, or where tau's line or the wedge meets the farthest range) and said first, "that much is the clip's"; then the region drawn evenly in R and Ṙ (as before: the uniform samples unchanged, the same seed stream) and, beside it, with the range log-uniform and the direction isotropic (`invariant`); the size range as the extent's, not the draw's; the figure's caption the same. The isotropic odds on the transverse-speed row ("within 15 % half the time, more than twice it one time in 7.5, more than ten times one time in 200") | `kinematics.admissible_region` (`invariant`, `measure`, the exact `speed_max`/`speed_min`), `admissible_said`; `figures.admissible`; `report.ISOTROPIC` | test_reduction (the survey's table: 2-20 km at 0.01 rad/s, 31 % and 97 % under the speed of sound, medians 525 and 84 m/s, the sentence's order; the wedge's invariant draw stays inside it; the odds are the formula's) |

### What the numbers say (scripts and output in `/scratch/mcdonald/v04-s10/`)

**The recorded tracks** (`scripts/misfit.py`, `runs/misfit_*.jsonl`: the 14 case files' objects and the golden tracks,
46 with a band, 25 the models pass): under the final rule PR43 fits at 1.0 times its jitter (8 px: the streak's
centroid is noisy); the other 24 describe their trend at 4.6 (FLIR1's exit) to 234 (PR077's loop) times theirs --
FLIR1's fields 6.6, PR23 6.8, PR149 10.5, the Galileo flyer 3 15, PR097's four 15-18, PR071 30, PR135's members 66-69,
PR051's release 71. Even a free quadratic misses most of them by as much: the wander is the camera's or the object's
on scales from half a second up (PR071 18 px at a 0.6-s range, PR23 5-7 px at 0.3-0.7 s), so counting a short wander
as noise would not have made them fit.

**The null** (`scripts/null_m1.py`, `null_compare.py`; jobs 13543 and 13555, 400 drawn pinhole tracks a case, an
object closing half a second after its last frame and one far off, 15-60 points, half a pixel of jitter white or
AR(1) at φ 0.3/0.6/0.9; both jobs hit their 45-min limit before the far 30- and 60-point cases): the band's nugget
alone reads low on the steep closing track (60 points, φ 0.6: 80 % past three jitters, 40 % past four); the
residual's alone reads low on short tracks with memory (12-14 % past three at φ 0.6). The larger of the two: at most
5 % past four in every case run (the 60-point closing track at φ 0.6 and 0.9: 5.0 and 4.0 %; far 15 points at φ 0.6:
3.0 %), at most 1 % past five, none with white jitter; at three it was 12 and 52 %. Hence NUGGETS 4.

**The depth bound** (`scripts/m5_check.py`): drawn approaches and retreats at constant velocity (|Ż/Z| 0.0004 to
0.02 a second, 40 draws each) held the truth 40, 40, 38 and 36 times at 95 %. PR23: under 1.6 % a second over 6.8 s
(−1 ± 26 px/s on 248), at least 64 s from the camera's plane closing, 68 receding; PR149: under 4.6 % over 2.7 s
(−72 ± 45 on 607), at least 206 s closing and 22 receding. Both describe their trend, so both are said as conditions.

### Tests at the end

From a snapshot of the tracked files (`git ls-files -z | xargs -0 cp --parents`), one Slurm job a suite
(`suites/one.sbatch`, `suites/all.sh`: niced 100, 4 CPUs for gui/golden/measurement/camera, 2 for the rest),
`MCDONALD_DATA` set, `TMPDIR` `/scratch/tmp/s10`; logs `suites/logs/r1_*`: **all 20 pass, every job exit 0** --
gui 754 (753 + the card's "describes its trend": 1; the WxAgg backend skipped as before), reduction 449 (436 + 13),
**golden 146 PASS, 0 SKIP** (140 + PR43 fits to its jitter, PR077 and PR135's two describe their trend, PR23's and
PR149's bounds: 6; 34 min on 4 CPUs, inside the 45-min limit but not by much), measurement 491, camera 134, cli 126,
slew 59, audio 54, published 32, zoom 31, share 25, horizon 25, tether 24, focus 19, waves 14, stabilize 13, aspect 10,
sweep 10, haze 9, streak 8. After the snapshot only text changed (the CHANGELOG, ROADMAP, method §33 and one
docstring's numbers); reduction and cli, which read the docs, ran again from a final snapshot (`r2_*`): reduction 449, cli 126, both pass.
Everything that ran the package went through srun or sbatch; nothing ran on the desktop.

### Left behind

Nothing in `/tmp`; `/scratch/tmp/s10` removed; the snapshots (`snap`, `snap1`, `snap2`) removed;
`/scratch/mcdonald/v04-s10/` kept (`scripts/`, `runs/`, `logs/`, `suites/`, this draft); the frame cache
`~/Documents/mcdonald/frames` untouched. No worktree made. Jacob's other worktrees untouched.

### Open, in the order I would take them

1. Jacob's look at the plain form's four new questions (session 8's item 1), and now at "describes its trend to N
   pixels" on the card -- my words, from the survey's.
2. `share rerun --strict` on the 14 case files and the recipe's remake for 0.4.0: every report with a passing track
   changes again (24 of 25 now describe their trend; PR23's and PR149's "no closing seen" become bounds; every
   admissible-region sentence has its two draws), on top of session 8's list.
3. The rest of objective 3 from the survey: M4 (the turn as an ellipse past ~150°: "about N widths" honest; session
   7's item 9's second half) and M5's other half (t_z's error from the same algebra in place of the residual
   bootstrap, which runs a quarter narrow; only PR43 fits, so it reaches one recorded case).
4. The honest form of M1: a GLS fit of the projective curve under the band's covariance with the wander's range held
   short of the span, so that a bird's wobble counts as noise and a bend over the whole track does not (jitter with a
   third of a second's memory is called trend-only up to 52 % of the time at three jitters, 4 % at four).
5. A real clip with a known range for each bound (session 8's item 2); tau on the Galileo aircraft when the ADS-B
   data comes (item 4).
6. Session 8's items 5-7: `streak`'s speed per frame from the band; the sweep's open items; `camera --scene` into
   `run`; Find/Follow on a saturated bloom; `slew` on a dial that stalls.

---

## Session 8 (2026-10-29): the ledger finished in the window and in `run`; PR43's dash read through its own blur; Jacob's answers built; focus a step

Jacob: "see docs/handoff-v04.md and remember to use /slurm". Session 7's item 1 waits on Jacob's word (below, still
open), so this session took **item 2, the ledger finished** -- the report card, the bounds in `run`, R from a range
ratio -- and **the streak half of item 5** (PR43's dash with the clip's own blur). On main, **committed locally, not
pushed** (nothing pushed or released until 0.4.0); no version bumped; CHANGELOG's Unreleased has four new items.

**Built in a worktree**, `/hugespace/models/mcdonald-s9` (branch `v04-s9` off e670858), fast-forwarded into main at the
end and removed: Jacob's `orbs_propose` array (`metallic_orbs/jobs/propose_array.sbatch`, 41 tasks) runs `mcdonald look`
from this checkout, a task starting every few minutes. The card and the range ratio (report.py, report_qt.py and their
tests) were edited on main's checkout before I saw the array -- whole-file edits, each complete and checked; everything
after went to the worktree. Scratch: `/scratch/mcdonald/v04-s9/` (`look/` the cards drawn off screen, `scripts/`
`card_look.py`, `one_drive.py` (one of test_gui's drives alone), `pr43_blur.py`; `runs/` PR43's readings; `logs/`;
`suites/` the job script and logs; the snapshots removed).

### What was built

| what | where | tested by |
|---|---|---|
| **the four unknowns on the card**: Scale, Range, Aspect and Camera's speed on every card with a speed in the picture -- the value (", assumed" on a guessed field of view), a bound ("2.5 km to 57 km", "at most 1.2 km"), or "not known" written quietly (muted, not bold); the tooltip the ledger's route and "What would give it: ..." | `report_qt.facts`, `unknown`, `_bound`, `UNKNOWNS`, `NOT_KNOWN` | test_gui (one-press drive: 3 checks) |
| **R from a range ratio**: a reference of known length is at L k / l, the object R_obj / R_ref times as far; in the summary's range row, the ledger (as assumed as k is: "assumed" on a guessed FOV), the admissible region's bounds; beside the reference the size needs no k (S = p (R_obj/R_ref) L / l); without the ratio or without k, the range row says what the reference would give | `Case.ranged`, `range_bounds`, `ledger`, `summary` | test_reduction (the four unknowns: 3 new checks) |
| k's row no longer suggests a reference gives k ("no graticule, field of view or slew"; with a reference: "gives the speed across the line of sight without it (k cancels)") -- PR149's card said "no graticule, reference, ..." with a reference given | `Case.ledger` | test_reduction |
| **`horizon` and `haze` as steps of `run`** (and so of the window's Measure form): `--height` + a point (`--horizon N,X,Y`, or the first horizon mark in `--marks`) runs horizon; `--visibility` or `--haze-reference N,X,Y,M` runs haze; each its command's own call with its command's own k ((FOV px) / FOV, or the graticule -- not the case's pinhole k, so the numbers are the command's), the command recorded, the bound into the ledger and the admissible region; planned (a jewel each) only where what it needs is given; a height with no point is NO POWER saying so; what cannot go together refused before anything is measured | `stages.KNOWN` (4 rows), `OPTIONAL`, `ORDER`, `planned(**known)`, `check_known`, `horizon_point`, `haze_reference`, `run_case`; `haze.parse_visibility`; `measure_qt.STAGE_WORDS`, the plan; `COMMAND` | test_horizon (`test_a_step_of_run`, 6 checks on a rendered sea clip through `run_case`); test_reduction (planned); test_gui (the form's rows, `run --help`) |
| **`streak` takes the blur back exactly** (`motion_px`: the inverse of a box's half-peak width through a Gaussian blur) instead of subtracting it whole, and **reads the blur off the scene's points** by default (`scene_blur` = `forensics.point_blur`; `--blur` gives it; 2 px, said, with too few points) | `streak.motion_px`, `scene_blur`, `BLUR_ASSUMED`, `main` | test_streak (the old exposure 0.462 -> 0.500; 3 new checks) |

**The choice made for item 2 ("a page or `run` stages for the bounds"): `run` stages fed by known quantities** -- the
pattern Jacob set for what is known (2026-10-09: asked before the one press or after it, never during; new knowns go in `stages.KNOWN`), with no new
page or pop-up, the one press asking nothing; the window reaches them through the Measure form's technical fields and a
horizon mark. Jacob's word may move it. **`focus` is not a step**: branch `metallic-orbs` (06cc313, not in main) is
reworking it (a dark edge read with no points, `--ground-scale`); wire it after that merges, the same way (a `--band`
or `--pupil` row). **`slew` is not a step** (it needs a pointer read every frame and the scene's chain; `--case`
remains its route).

**The card, drawn off screen** (`look/pr43_fov.png`, PR113, PR149 from session 7's unpacked case files, 0.3.0's): PR43
at 65.6°: Scale "1490 px/rad, assumed", Range / Aspect / Camera's speed "not known" (muted) between the found rows;
PR113: Scale "2028 px/rad" (graticule); PR149: all four not known, its speed across from the ship. The words were mine
("not known", "assumed", "What would give it"); Jacob chose others the same day (below).

### PR43's dash through its own blur (session 7's item 5, the streak half)

`forensics.point_blur` on PR43's frames 50-75 (its case file's track): **3.6 px** at half the peak, from 43 compact
spots on 12 frames (4 on the sensor left out). Reading the dash at 3.6 px showed the subtraction was wrong, not only the
blur: a box of motion drawn through a Gaussian is the box's length at half its peak once it is a couple of blurs long,
so "the length less a blur" read every dash short -- test_streak's own half-frame shutter at 0.46, a 20-px/frame dash
through 3.5 px at 0.34. With `motion_px`: **PR43's exposure 15.6 ms, 0.47 of a frame, at its blur; 14.7 ms at 2 px**
(11.5 before) -- the median of the frames' ratios; the medians' ratio gives 12 ms (the centroid's jitter, the speed
band's 5.7-px nugget, spreads the frames' speeds: a kriged speed per frame would be the better divisor, not done). At
3.6 px the dash (7.0 px) is under three blurs: **no light curve, so session 2's "no beads at 134 Hz" made at 2 px does
not stand.** ROADMAP row 757 and method §30 say so.

**Item 5's other half, `horizon` on PR149's ship, cannot be done**: PR149 looks about 29° down at the ship (the uap
case note, `pr149_transit.md`), no horizon in the frame, and the platform's altitude is not known (1-5 km). A sea
horizon with a known height and range is still wanted (AARO's or the Galileo clips).

### Tests at the end

From a snapshot of the worktree's tracked files (`git ls-files -z | xargs -0 cp --parents`), one Slurm job a suite
(`suites/one.sbatch`, niced 100, 4 CPUs for gui/golden/measurement/camera, 2 for the rest), `MCDONALD_DATA` set,
`TMPDIR` `/scratch/tmp/s9`; logs in `/scratch/mcdonald/v04-s9/suites/logs/`: **all 20 pass** -- measurement 491, reduction 432 (429 + the range ratio's 3), gui 750 (747 + the card's four unknowns' 3; the WxAgg backend skipped as before), camera 134, cli 126, **golden 140 PASS, 0 SKIP**, slew 59, audio 54, published 32, zoom 31, share 25, tether 24, horizon 23 (17 + `test_a_step_of_run`'s 6), waves 14, stabilize 13, aspect 10, focus 10, sweep 10, haze 9, streak 5. The streak fix came after that snapshot: from a second one, streak 8 (5 + the blur's 3), reduction 432, cli 126, horizon 23 and haze 9 again (the `_2` logs).

**After Jacob's answers** (the second commit, from a third snapshot; logs `r2_*`, and `r3_*` for the suites the Help
text, README and CHANGELOG reach, run again from the last snapshot): **all 20 pass** -- gui 753 (750 + the horizon's
click and the card's questions: 3), reduction 433 (+ no bend at all), horizon 24 (+ given afterwards), golden 140 PASS
0 SKIP, measurement 491, cli 126, the rest as above.

**A slip**: one `python3 -c` spot check of `motion_px` (six numbers, about a second) ran on the desktop, not through
Slurm; everything else went through srun/sbatch. Jacob's own jobs (`orbs_firstlook`, `orbs_propose`, `math_*`) ran
alongside, untouched.

**Left behind:** nothing in `/tmp`; `/scratch/tmp/s9` removed; the snapshots and PR43's extracted frames (`v04-s9/frames/`) removed; `/scratch/mcdonald/v04-s9/` kept (732 KB: the looks, scripts, runs and logs); the frame cache `~/Documents/mcdonald/frames` untouched; the worktree `mcdonald-s9` and its branch removed after the fast-forward (the second round's worktree `mcdonald-s9b` likewise). Jacob's other worktrees (`drift`, `rotor-note`, `fold-double`, `metallic-orbs`, `v04-window`) untouched.

### Jacob's answers (2026-10-29, the same session, by multiple choice), and what was built from them

| asked | his answer | built |
|---|---|---|
| how the window reaches the horizon and haze bounds | **also in the plain form** ("Do you know anything else about this video?", segment step and report card), not only Advanced Mode's Measure form | `known_qt.KnownForm`: "How high was the camera over the sea?" (meters / feet), "Where is the sea's horizon?" (a click on the video: `start_point` on the main view, `Screen.start_point` on the segment step's player; the frame on the screen and the point, or a drag's middle; Clear), "How far could you see that day?" (kilometers / miles; `--visibility` takes `mi`); height and horizon go together; kept for the video (`remembered`: AFTER + LATER) and shown in the Measure form; the one press uses them; on the card "Work out the speed" does the two steps on the track already followed (`stages.LATER`, `add_known` via `horizon_step` / `haze_step`, the same calls `run_case` makes; `mcdonald report CASE --height --horizon --visibility`) |
| the ledger's status words | **keep** (constrained / assumed / bounded / missing, the headers) | nothing to change |
| the card's words for the four unknowns | **"unknown" / "To find it: ..." / ", a guess"** | `report_qt.NOT_KNOWN`, `unknown` |
| card "coming closer" against report "closing on the camera" | **the card uses the report's words** | "fits, closing on the camera" / "fits, receding"; "Time to the camera" "... s ago, receding"; Help's "Read the report" says so |

The three new questions sit **after** the existing ones, under a line "These say how far away the object can be, with
no speed at all: over the sea, or in the haze of a day." -- his preview drew them first, as a sketch; the card opens on
"Its real speed needs ...", so the speed's questions lead. A word from him moves them. Found on the way: a drawn track
with no bend at all left the turn's 95 % bound empty and **`projective.said` raised** (the kinematics stage failed
quietly in `run`, loudly in `add_known`): now "no bend at all: it did not turn" (test_reduction).

### Focus as a step, after `metallic-orbs` was merged (the same day; Jacob's two answers)

Jacob merged `metallic-orbs` (7359594) and chose, by multiple choice: **the camera's band starts the focus step** (not
every case with a scale -- its floor rests on "focused far"), and **the plain form asks it too**. Built: KNOWN rows
`band`, `pupil`, `focus_at` (`--focus-at`, the command's `--focus`), `ground_scale`; `stages.OPTIONAL["focus"]`,
`focus_step` (the command's own call and k, the object's polarity and the mask rows), in `run_case` after the haze and
in `add_known` (LATER); `NOTES_OF` tells each step's notes apart (horizon's and focus's both begin "k comes from an
assumed field of view"); `check_known` refuses an unknown band, an unreadable pupil or focus distance, and the pupil,
focus distance or ground scale without a band; the jewel "How far away it is at least, from how sharp it is beside
the scene's own points"; the plain form's "What kind of camera was it?" (don't know / daylight / near infrared /
short-wave infrared / heat (mid-wave) / heat (long-wave) -- his list, with short-wave infrared added since the band
exists; described on the card as "a heat (mid-wave) camera"). Tests: test_horizon (the step's numbers are the
command's; given afterwards and forgotten; the refusals), test_reduction (the plan), test_gui (the card's question
against `mcdonald report CASE --band mwir`). **All 20 suites pass** from a snapshot of it (logs `r5_*`): gui 753 (1 skip,
WxAgg), reduction 436, horizon 25, focus 19 (the merged branch's), golden 140 PASS 0 SKIP, measurement 491, cli 126, the
rest as above.

### Open, in the order I would take them

1. Jacob's look at the plain form's four new questions in the window (their place, the click on the horizon, the
   camera's list).
2. A real clip with a known range for each bound: a sea horizon with the camera's height, a daytime EO clip for the
   haze, and the focus (the Galileo aircraft with ADS-B would serve the focus and tau both).
3. `share rerun --strict` on the 14 case files and the recipe's remake for 0.4.0 (every report changes: the band, the
   survivors, tau, now the card's rows and the ledger's range from a ratio where a case has one).
4. tau on real objects (session 7's item 4): the Galileo aircraft when the ADS-B data comes.
5. `streak`'s speed per frame from the speed band rather than the centroid's differences (PR43's 12-16 ms spread).
6. The sweep's open items (session 2's item 3); the parallax ladder when Long's revision is in (PR043 on hold).
7. `camera --scene` into `run` and the window; Find/Follow on a saturated bloom; `slew` on a dial that stalls; session
   4's item 6; session 7's item 9 (the residual bootstraps a quarter narrow, `projective.turn` past a quarter turn).

---

## Session 7 (2026-10-28/29, overnight): the window's plain words for the band and the survivors; tau from a stage

Jacob: "see docs/handoff-v04.md and remember to use /slurm". Took session 6's open list in its order: **item 1 (the
window) and item 2 (tau from a stage)**. On main, **committed locally, not pushed** (e78e092 the window; the tau
commit after it; nothing pushed or released until 0.4.0). No version bumped; CHANGELOG's Unreleased has two new items.
Everything that ran the package went through Slurm (srun for the looks, sbatch for the controls and the suites). This
session's scratch is `/scratch/mcdonald/v04-s8/` (`cases/` the reference case files unpacked, `pr43_fov`, `pr144_now`,
`pr135_now` with their speed step done again by this code; `look/` the card drawn off screen before and after;
`scripts/` the looks, the rendered approach `looming_clip.py`, the drawn sweeps `wander3.py`/`.jsonl`; `controls/` the
tau control over the 31 objects -- `objects.json`, `one.py`, `array.sbatch`, `out1/` the first rules, `out2/` the
second, `out/` the final; `suites/` one.sbatch and the logs; `snap*/` the snapshots the jobs ran from).

### Item 1: the window, in plain words (e78e092)

The card cut every value at its first bracket, so the band's "± e" and its range never reached it, and the three rows
of section 33 showed under the report's own names ("Constant velocity, as a pinhole draws it": "passes: closing, T =
0.91 s, θ = 39°"). Now `report_qt.facts` gives the rows, each with the summary's `how` as its tooltip:

| row | values | from |
|---|---|---|
| Along the track (under the speed) | "steady, ±e px/frame" / "A to B px/frame" (the least to the most) | `kin.band_said` in the tip; PR43 at 65.6°: 11.6 to 31.4 |
| Turn | "did not turn" / "a hair off straight" / "its path bends, radius N widths" | the image path: camera or lens can bend it, said in the tip and the report |
| Straight and steady | "fits, coming closer" / "fits, going away" / "fits, no closing seen" / "does not fit" | `projective` |
| Moves in a frame | "2.5 of its widths" | the smear |
| Time to the camera (item 2) | "in 2.0 s" / "7.3 s ago, going away" | `Case.tau()` |

The value column takes the room the labels leave (a short value no longer wraps in three lines). Help -> Getting
started's "Read the report" says what the rows are; the speed step's jewel says it measures them. **My words, not
Jacob's**: the card says "coming closer" where the report says "closing on the camera"; the report keeps session 6's
wording ("the track itself says this", "a hair off straight", "did not turn", "closing on the camera") -- **still
awaiting Jacob's word**, as session 6 asked.

### Item 2: tau from a stage (method §33, "From a stage")

| what | where | tested by |
|---|---|---|
| the size (`extent`, every frame up to EACH_MAX 300) and the ring's median level (`flicker.level`) read with the brightness; NaN where tried and nothing read; "object size"/"object level" in `<tag>_flicker.csv` | `flicker.curves(each=)`, `_apertures`, `judge(each=)` | test_measurement (the columns) |
| `tau_of`: the looming law **with the blur's offset** (s = a/(t_z - t) + c; without c a rendered disc closing at 2.0 s read 3.3), t_z refined between grid points (the bootstrap band had collapsed on the grid); the rules TAU_MIN_PX 4, TAU_COVER 0.6, TAU_ODD 3 MAD slips (mirror-padded: "nearest" made a first slip its own median), TAU_Z 4 (sigma widened by the lag-1 n_eff), TAU_GROW 2 px, QUAD_SLACK, FAR, TAU_REL 0.3; no bound from a size that holds (the blur's share is unknown: the bound I first drew said "at least 12 s" of a thing 2-6 s out) | `kinematics.tau_of`, `_trend`, `looming_fit(offset=True)` | test_reduction (8 checks) |
| the light curve, conditional: unresolved, not beating, 10 % at TAU_Z, gain out by the ring's level; said as "would give tau = x s at the track's middle if the change were its range's alone" (gamma: long by up to 2.2) -- never the route | `tau_of` | test_reduction, test_measurement |
| the stage's `tau` field (a track each) and its result line; a group member carries its own. **No NO POWER for tau**: I first listed one wherever no track had a size, and two of test_measurement's checks showed what it does -- the flicker stage's NO POWER list is the beat's (callers read "nothing refused" from it, the CLI's error is its first entry), and most objects are points, so every flicker stage and every report's count would carry it; the summary's row says why instead | `flicker.tau_reading`, `tau_said`, `of_member` | test_measurement |
| into the case: the summary row "time to contact"; θ from τ and **ω at the last frame** (the band's v_end / k -- the track's average put a drawn approach at 2° for 6°) in the summary and the ledger (constrained); τ's line in the admissible region (with ω at the last frame); the bottom line's sentence beside the path's own T ("which agrees" / "does not agree") | `Case.tau`, `tau_reading`, `omega_last`, `ledger`, `admissible`, `survives` | test_measurement (rendered: 1.95 ± 0.13 s for 2.03, θ 6° for 6.1°; receding -7.27 ± 0.19 for -6.97; held: none, the row saying why; a point: light only, 3.83 s for 4.02) |

**Calibration.** Drawn (`scripts/wander3.py`, 4 s at 30 fps, rounded sizes): looming at tau 2 s found 40/40 (median
1.97, pulls sd 1.25: the band is a quarter narrow); at tau 6 or 16 s never (grows under 2 px -- the size route reaches
a thing that closes in about the track's own length); a wandering size passes 1/100 (0.3-s memory), 2/100 (1 s; 3 of
the test's 40), 8/100 (drifting as slowly as the record is long -- no size rule tells that from an approach, hence the
path's T beside it). **The 31 objects of the 14 reference case files** (`controls/`): with z 3 and no coverage or
slip rules 7 claimed a tau (PR097's four dots sized on 20-50 of 126 frames at 7-55 px; PR149; PR135 object 2; PR44 at
-22 s); with the final rules **none**: 10 never sized (or on under ten frames), 9 sized on too few of the frames tried,
12 hold (PR44's bird at 3.1 sigma). Every recorded object in the set is a point or a small blob whose size the far ring
reads unsteadily: the size route has not yet been seen to work on a real video -- the Galileo aircraft with ADS-B are
where it can be.

### Tests at the end

From a snapshot of the working tree with every tracked file (`git ls-files -z | xargs -0 cp --parents`; a first
snapshot of `src tests pyproject.toml` alone failed test_cli's readme and test_reduction's exercises checks for want of
the READMEs and docs/), one Slurm job a suite (`suites/one.sbatch`, niced 100), `MCDONALD_DATA` set, `TMPDIR`
`/scratch/tmp/s8`; logs in `/scratch/mcdonald/v04-s8/suites/logs/`: **all 20 pass** -- measurement 491 (483 + tau's 8),
reduction 429 (422 + tau's 7), gui 747 (the WxAgg backend skipped as before; the card's 3 checks were added in e78e092,
job 13028: 748 -- the count differs by grep, not by a check), camera 134, cli 126, golden **140 PASS, 0 SKIP**, slew 59,
audio 54, published 32, zoom 31, share 25, tether 24, horizon 17, waves 14, stabilize 13, aspect 10, focus 10, sweep 10,
haze 9, streak 5. The round before it (with tau's NO POWER) failed two of test_measurement's checks -- the reason it
was taken out. Jacob's own jobs (`orbs_test_*`, `pr062_*`, `econ_smoke`) ran alongside, untouched.

**Left behind:** nothing in `/tmp`; `/scratch/tmp/s8` emptied; the extracted frames (`v04-s8/frames/`) removed;
`/scratch/mcdonald/v04-s8/` kept (the cases, looks, scripts, controls and logs; the snapshots removed); the frame cache
`~/Documents/mcdonald/frames` untouched (the controls extracted into their own folders and removed them).

### Open, in the order I would take them

1. **Jacob's word on the wording** (session 6's and mine): the report's "the track itself says this", "a hair off
   straight", "did not turn", "closing on the camera"; the card's "Along the track", "Straight and steady" ("fits,
   coming closer"), "Turn" ("its path bends, radius N widths"), "Moves in a frame", "Time to the camera" ("in 2.0 s").
2. The ledger, finished (session 3's item 2): the report card, a page or `run` stages for the bounds, R from a range
   ratio; Jacob's word on the ledger's wording -- no answer yet. (θ from τ is in the ledger now.)
3. `share rerun --strict` on the 14 case files and the recipe's remake for 0.4.0 (every report changes: the band, the
   survivors, now the flicker stage's tau, its CSV columns and the "time to contact" row).
4. tau on real objects: the Galileo aircraft when the ADS-B data comes; before that, any PURSUE clip where something
   visibly closes (none of the 14 case files' objects does). The per-frame `extent` is the weak part: its far ring
   reaches neighbours and bands (see the controls) -- a size read off the object's own stamp, like `stacked_extent`'s
   `local`, may hold better and is the thing to try first if the aircraft fail.
5. The new bounds on real clips (session 2's item 4): PR149's ship for `horizon`, PR43's dash for `streak`.
6. The sweep's open items (session 2's item 3).
7. The parallax ladder's nearest height when Long's revision is in; PR043 on hold.
8. `camera --scene` into `run` and the window; `Find`/`Follow` on a saturated bloom; `slew` on a dial that stalls;
   session 4's item 6.
9. Noted: the residual bootstrap of `looming_fit` (and the projective test's) ignores the residuals' correlation, so
   the band is about a quarter narrow on drawn series; `projective.turn` on an arc of more than a quarter turn reads the
   radius short (a drawn 286° arc: 14 widths for 25) -- the sagitta formula is for a small bend; session 6's item 9.

---

## Session 6 (2026-10-28, late night): the speed band (objective 4) and what survives the missing variables (objective 3)

Jacob: "see docs/handoff-v04.md". Took session 5's open list in its order: **item 1, both objectives, without ADS-B**
-- objective 4 first (K1, K8), then objective 3's parts that need no range. On main, **committed locally, not pushed**
(4526270 the work, then the test fix below; nothing pushed or released until 0.4.0). No version bumped; CHANGELOG's
Unreleased has two new items. This session's scratch is `/scratch/mcdonald/v04-s7/` (`logs/` the reduction suite's
runs as the work went, `suites/` the one-job-a-suite script `one.sbatch` and `logs/` of the snapshot runs, `cases/` the
band over every object of the 14 case files and the golden tracks (`band_cases.py`, `band_table.md`), `try/` the PR055,
PR23 and PR43 figures looked at, `snap/` the snapshot the suites ran from).

### Objective 4: the speed band (K1, K8; method §32)

| what | where | tested by |
|---|---|---|
| **universal kriging in a few functions**: a linear mean, a Matérn-3/2 wander, a nugget; REML (three starts on a 60-evaluation budget, the best run to convergence; a warm restart), Dubrule's closed-form leave-one-out, predictions of the latent path and its rate with the mean's own uncertainty, joint covariances, a draw of the wander and its rate together | `kriging.py` (new; numpy + scipy, dense) | the band's tests |
| **`kinematics.speed_band`**: each coordinate against wall-clock time (exact repeats dropped first; a point 4 of its own LOO sigmas off dropped once; over 450 points fitted on the middle and read in windows of 450): the rate at every kept frame with its sd; the average velocity over the stretch, (f(t1) - f(t0)) / T on the latent path, with its honest error; the velocity's change as a vector, its magnitude, turn and mean acceleration with its sigma; Δln L over a line with white jitter (`constant` under BAND_DLNL 10); the nugget and what one pair of frames reads against it; `series` frame by frame | `kinematics` (`BAND_*`, `band_said`, `pm` -- every value to its error's precision, `simulate_track`) | `test_reduction`: three tests, 41 checks |
| the stage records `band`, says it in two result lines (`speed band`, `speed change`), writes `<tag>_speed.csv` and `<tag>_speed.png` (the rate with ±1/±2 sd, each pair's reading, the average; **the time-distance diagram as the lower panel**, A13); a not-uniform track is described, not refused (the note, the caveat on body lengths and the scale bar, the Reduction's print); `uniform` and `v_px` unchanged | `stages.kinematics(out=)`, `_speed_files`; `figures.speed_band`; `report_figures` | the same; `test_cli` 66 as before |
| the report: the pixel-velocity row carries the average's error and the band's range ("the speed ran from A to B px/s along the track, V ± e on average"); the bottom line says "The object's speed in the image changed: from ... to ... (least, most), V ± e on average; its velocity changed by ... (turn)" where not uniform, "(constant within ±x px/s)" or "(between a and b along the track)" where it is | `report.summary`, `bottom_line` | `test_the_speed_band_in_the_stage_and_the_report` |
| `mcdonald kinematics --out DIR` (its files; default ./<tag> as every command) | `kinematics_cli` | `test_cli` (`--out` given, so the planted clip's folder no longer lands in the cwd: the fix after the snapshot) |

**Held (K8).** Sixteen tracks drawn from the covariance (`simulate_track`: the wander and its rate drawn together, a
velocity and an acceleration on top): the ±2 sd band holds the drawn rate 94 % of the time, z sd 1.05, the average's
z sd 1.03; sixteen lines with jitter: constant within the band 16 of 16, the velocity never said to have changed, the
nugget 0.50 for 0.5 planted; a planted 200 px/s² seen 8 of 8 at 3 sigma or more, read 197. Over 30 draws at five
(theta, T) combinations the coverage was 0.938-0.967 (`cover.py`, run on the desktop by mistake before the Slurm rule
was recalled -- nothing of it kept). On the recorded tracks: the nugget is the survey's (PR055 0.59 px for 0.50, PR071
0.21 for 0.33 with 5 slips clipped, PR144 0.75 for 0.80, PR23 0.61 for 0.65, the balloon 0.45 for 0.44), the band
2.5-9x tighter than the scatter of single pairs; PR43's streak (test_golden) 12-31 px/frame along the track against the
Note's 7-33, the velocity's change 3.1 sigma over 0.83 s; flyer 5 holds to 0.08 px and speeds up 104-174 px/s.

**The band over the 14 case files' 22 objects and the golden tracks** (`cases/band_table.md`, one Slurm job): every
track but PR113's four points has a band; nuggets 0.01-0.84 px on the spot-filter tracks, 2.5-3.0 on PR141's two (IR,
76 points), 5.7 on PR43's streak; **every one of them wanders** (Δln L 56-3,816: none is a line with white jitter, as
the survey found); the line's `uniform` is True on 10 of 45 while the band says the speed varied by 2-10x along most
of them. The line's v_px and the band's average differ most where the track curves (PR144's golden 29 vs 42 px/s;
PR071 2.2 vs 7.3; PR051's release 19 vs 133). PR051's release track: pairs every second frame, so no pair scatter;
the dash's jump gives a nugget of 1.6 px in y and a band of ±150. **`share rerun --strict` was not run**: the reports
of every case change (new rows, the band's words, a new figure), so the strict comparison will list differences until
the case files are remade for 0.4.0, as the recipe says they are at a release ([[reference-case-files-recipe]]).

**Two things the band says that the words had to learn.** (1) The mean acceleration is a vector's change: PR055's
sphere runs 68 -> 80 px/s in speed but its velocity changed by 144 px/s (152° of direction), so the words say "its
velocity changed by ... (so many degrees of direction)" and not "accelerated". (2) The band can be as wide as a pair's
jitter where the wander's range is short (PR071's hand track, 0.6 s: ±13 against ±12): the rate itself changes faster
than one pair can tell, and the honest comparison is against the pair readings' scatter (`pairs_sd_px_per_s`), not the
nugget alone -- the first wording claimed "tighter than one pair" and was wrong on PR071.

### Objective 3 without ADS-B: what survives the missing variables (method §33)

| what | where | tested by |
|---|---|---|
| **the projective constant-velocity test**: a straight image track whose distance from its vanishing point goes as 1/(t_z - t); five parameters (the line, the vanishing point on it, a scale, t_z) by a grid in t_z either side of the track (to 20 track lengths) and least squares; held against constant image speed (4) and a free quadratic (6); passes closing/receding with t_z's residual-bootstrap band, T = t_z - t_last, v ≈ R / T (exact with k and the frame's centre, the secants' ratio), with k the aspect angle ψ from the vanishing point; passes with no closing seen; fails | `projective.fit` (new module), `FAR`, `CLOSING_GAIN`, `QUAD_SLACK` | `test_reduction` (a drawn pinhole track closing: t_z 2.5 found, ψ within 1°, v/R within 10 %; far: no closing; curved: fails); `test_golden` PR43 |
| **the turn radius in body widths**: the sagitta across the principal line, Π_L = 8 D s / L²; did not turn (s within 3 sigma: the radius at least L² / 8 D s_95), a hair off straight (Π_L < HAIR 0.01), a turn; the scale from the kinematic notes (quadcopter 15, pigeon 33, airliner 60, fighter 47-121) | `projective.turn`, `smear`, `said` | a drawn arc of 500 px by a 10-px object -> 48 (50); a straight track -> at least 8,590 |
| **tau** from looming (s = a / (t_z - t), the same grid and bootstrap; d ln s/dt beside it) and from a light curve with the gain taken out by a background aperture; θ = atan(ω τ) | `kinematics.looming_fit`, `tau_from_light_curve`, `aspect_from_tau` | a rendered disc growing as 1/(t_z - t) read by `flicker.extent` in whole pixels (t_z 3.96 for 4.0); a 1/R² light curve under a sinusoidal gain (tau 2.98 for 3.02); without the background the gain leaks in |
| **the admissible region in (R, Rdot)**: the stages' range bounds (a range given; else focus's floor, horizon's and haze's ceilings), a speed cap V_CAP (Mach 3), the size through k and the extent, tau's line; drawn evenly for the 5-95 % of speed, aspect and size, the share under Mach 1, the least (ωR at the floor) and the most | `kinematics.admissible_region`, `admissible_said`, `BOUND_WORDS`; `Case.range_bounds`, `Case.admissible`, `Case.survives`; `figures.admissible`; `<tag>_admissible.png` among the report's figures wherever ω is known | analytic checks (the rim is the cap, a size ceiling cuts R, tau makes it one line, crossed bounds empty); the figures test now expects three where k is known |
| the stage records `projective`, `turn`, `smear`, `width_px` (the size given, else the blur's width, else the spot size the track was followed at: `extent_px`, passed by `run` and `add_known`; `height` for the frame's centre); nothing for a held track; NO POWER "turn" with no width; the summary's rows ("turn radius in body widths", "constant velocity, as a pinhole draws it", "smear"); the bottom line's paragraph "Without a range, a field of view or the platform's speed, the track itself says this. ..." with the region's sentence only where a stage bounds the range | `stages.kinematics(height=, extent_px=)`, `report.summary`, `bottom_line`, `kinematics_cli` | `test_what_survives_reaches_the_stage_and_the_report` |

**PR43 on its case file's 25-point track** (the research repository's note did it on its own 18 detections,
2026-08-05): straight to 1.5 px rms, t_z 3.38 s (3.33-3.45) against the note's 3.34, T 0.91 s against 0.80, the
vanishing point (483, 488) inside the frame against (573, 545), ψ 35° at a 65.6° field read linearly (39° with the
pinhole k `AngularScale.from_fov` gives: 1,489 px/rad) against the note's 33.8; the turn 4.0 ± 0.4 px over 505 px, about
1,870 body widths (the note: > 1,936): a hair off straight -- the first wording called it "a turn, so not inertial
motion" at 9 sigma, which is right arithmetic and wrong words for 4 px on a streak's centroid; the smear 4.75 widths
a frame. The bottom line's paragraph for it is in `try/` (run with an assumed 65.6° field).

**Not built, said in §33:** edge-crossing fits (A16: the frames at the edge); the parallax number (`comotion`'s and
`layers`' to give: valid only over a world-fixed textured background); tau is not fed by any stage (no per-frame size
or brightness series is recorded -- the flicker stage's extent is one number a track), so it reaches a report only
where a caller computes it, and its validation on real objects waits for the Galileo ADS-B data.

### Tests at the end

From a `git archive` snapshot of 4526270 (`/scratch/mcdonald/v04-s7/snap`), one Slurm job a suite (`suites/one.sbatch`),
`MCDONALD_DATA` set, `TMPDIR` on `/scratch/tmp/s7`; logs in `/scratch/mcdonald/v04-s7/suites/logs/`: all 20 pass --
measurement 483, reduction 422 (350 + the band's 41 + what survives' 31), gui 744 (1 skip, the WxAgg backend), camera
134, cli 126, slew 59, audio 54, published 32, zoom 31, share 25, tether 24, horizon 17, waves 14, stabilize 13,
aspect 10, focus 10, sweep 10, haze 9, streak 5, and **golden 133 PASS, 0 SKIP** -- the same 133 as session 5, because
`test_pr43_speed_band` was not yet in `main`'s explicit list (test_golden runs a list, not every `test_`): listed
after the snapshot, it passes 7 of 7 run alone from the checkout (`suites/logs/pr43_band2_*.out`: 11.6-31.4 px/frame
against the Note's 7-33, 3.1 sigma, t_z 3.38 s (3.30-3.44), T 0.91 s, psi 35.0°, vp (483, 488), 1,871 body widths),
and the golden suite from the checkout with it listed is **140 PASS, 0 SKIP** (`suites/logs/ck_test_golden_*.out`, 30b028e). `test_cli` ran again from the checkout after
its `--out` fix (126 PASS: the planted clip's `kinematics` run no longer leaves `planted/` in the cwd). Jacob's own
jobs (`pr062_firstlook`, `pr063_firstlook`, the `propose` arrays, `orbs_test_focus`) ran alongside, untouched; the
golden rerun was submitted niced behind them.

**Left behind:** nothing in `/tmp`; `/scratch/tmp/s7` empty (the suites cleaned up); `/scratch/mcdonald/v04-s7/`
kept (14 MB: the logs, the band table, the three cases' figures in `try/`; the snapshot removed -- it is 4526270); the
frame cache `~/Documents/mcdonald/frames` as session 5 left it (145 folders; nothing extracted this session: every run
was on tracks); the Slurm queue has only Jacob's own jobs. A coverage script ran on the desktop once by mistake
(`tmp/cover.py` in the job's folder, 4 min): everything after it went through srun/sbatch.

### Open, in the order I would take them

1. **The window** (the two audiences): the report card shows the summary's values, so the band's "± e" and "ran from A
   to B" reach it through the pixel-velocity row, and the full report page has the new rows, paragraph and figures; but
   nothing in the window names the speed band or the constant-velocity test in plain words (`window-text-in-plain-words`),
   and the Measure panel's jewels know nothing of them (they are the kinematics stage's, so no new jewel). Jacob's word
   on the wording: "the track itself says this", "a hair off straight", "did not turn", "closing on the camera".
2. **tau from a stage**: a per-frame size series (the `extent` the flicker stage reads on EXTENT_FRAMES frames, read on
   every frame along the track) and the object's and background apertures' curves (`<tag>_flicker.csv` has them) given
   to `looming_fit` / `tau_from_light_curve`, into the kinematics fields (`looming`), the ledger's θ row ("bounded by
   tau": I6) and the admissible region's line. Held on a rendered approaching object through the whole chain. Then the
   Galileo aircraft when the ADS-B data comes (session 5's note on what is on the drive).
3. The ledger, finished (session 3's item 2): the report card, a page or `run` stages for the bounds, R from a range
   ratio; Jacob's word on the wording -- no answer yet.
4. `share rerun --strict` on the 14 case files and the recipe's remake for 0.4.0 (above: every report changes).
5. The new bounds on real clips (session 2's item 4): PR149's ship for `horizon`, PR43's dash for `streak`.
6. The sweep's open items (session 2's item 3).
7. The parallax ladder's nearest height when Long's revision is in; PR043 on hold.
8. `camera --scene` into `run` and the window; `Find`/`Follow` on a saturated bloom (session 5's item 6); `slew` on a
   dial that stalls (session 5's item 7); session 4's item 6.
9. Noted: the projective test's residual bootstrap is along the line only (the across-line error of the line's angle
   is second order); the admissible region's "drawn evenly" is uniform in area, said in the words -- a log-uniform
   prior in R would be the scale-free alternative; `BAND_NMAX` 450 fits the covariance on a long track's middle only.

---

## Session 5 (2026-10-28, night): the released-track null on PR051, against the scene -- and the 9 % shortfall read

Jacob: "see docs/handoff-v04.md". Took session 4's open list in its order: **item 1, both halves**. The released-track
null on PR051 is built (`camera --scene`) and a golden check; the 9 % shortfall of the scene's chain against the data
bar is read (below: it sits between the bar's target grid and everything in the picture, which agrees with itself).
On main, **committed locally, not pushed** (abb8523 the work; nothing pushed or released until 0.4.0). No version
bumped; CHANGELOG's Unreleased has the item. This session's scratch is `/scratch/mcdonald/v04-s6/` (`mov_frames/` the
leak's frames 900-1279 and `look/` the sheets they were read from, `centroid_track.py` the track's maker, `runs/`
the upload's `layers`, the linker, the camera stage, `slew/` and `north/`, `shortfall.py` and `scene_look.py` the
readings, `logs/`, `suites/logs/`, `tests/`, `snap/` the snapshot the suites ran from).

### The null, in the form the clip allows

The MTS-B draws no azimuth readout a `readout` could time, and its north pointer lags in steps (session 2). But the
ground is in the picture, and the ground is the camera's own record: while a camera holds a drifting object the
ground slides through the picture at the object's rate against it, the other way; let go, the object keeps its motion
and crosses the ground at that rate. So `camera --scene LAYERS_CSV` (method §20, the bullet "Against the scene")
takes the track relative to the scene's path (`slew.scene_path` of a `layers` CSV over the same frames, one stretch
at a time), fits the rate steps on that, and reads the camera's rate before the release as the scene's drift over the
frames it held the object (`camera_before`), and after it too; the comparison needs no readout and no scale (one k on
both sides). Added with it: every stretch after the release compared and the first named beside the fastest; the
departure as a whole (`departure`: a line from the release to the track's end or its first jump of more than twice
the object's width) said first, since a jittery centroid cuts a track into many short stretches (PR051's: thirty) and
the null is about the departure, not its pieces; the direction each stretch takes against the one the release would
send it (only where the scene drifted at 2 px/s or more, `BEFORE_MIN`); `--pixel-aspect` (square pixels first).
The FLIR1 readout form and its fields are unchanged (its golden as before).

### What PR051 says (the numbers are in method §20, the test and the commit)

- **Which copy, which frames.** The research repository's case note (`analysis/cases/pr051/pr051_untracked.md`
  §48.3) rules: measure on Corbell's upload, not the Sitrec `.mov` (whose re-export wanders by up to 10 px and
  overstates scene motion). Upload frame = 2 x leak frame + 2140; every frame is doubled and the odd frames carry
  the pictures (checked: even n is a copy of n - 1). The event: the gate holds the object solid to 4437, blinks from
  4438 (the display's own lock-lost flag, the note's §48.1), the object walks out of it from ~4440, the gate goes out
  and the mode drops `RPOINT` for `RATE` at 4546, the dash at 4553-4567, the operator's slew from 4605. Frames
  4200-4700 are in the cache `~/Documents/mcdonald/frames/yt_nKtJslcHlCQ_1080p60_h264/` now, beside 181-860.
- **The scene.** `layers --n0 4201 --n1 4661 --k 2 --step 2 --max-shift 60` with 13 boxes (the data bar's blocks, the
  heading tape, the N, the reticle, the gate, the object's drift path and the dash's corridor; in `runs/up_layers.sbatch`
  and the golden test): held still over 2 frames in 99 % of pairs and still over 60 too; the chain whole 4201-4603
  at 0.3 square px/s before the release and 0.6 after; the operator's slew at 4605-4633 (no consensus) and the two
  big steps at 4637 and 4651. The note's "tracker chasing, unresolved" over the leak's 1105-1169 is nothing: the
  ground held.
- **The track.** `tests/golden/pr051_release_track.csv`, a thresholded intensity-weighted centroid as the note
  measured the released copy (`centroid_track.py`; the overlay, the reticle's arms and the gate's corners blanked;
  a 180-px window that follows, 1240 x 220 along the row for the dash), odd frames 4201-4549 and 4553-4567, the
  header saying so. mcdonald's own linker (`mark --set object@4301=905,545 --set object@4521=768,352 --no-window
  --link`, bright spots 71 px wide) agrees over the drift to a median 0.0 px, MAD 0.5, but does not hold the bloom
  inside the gate's brackets (lost before 4421) nor the dash: a track to keep in mind when Find/Follow meet a
  saturated bloom in a bracket.
- **The result** (`camera --track ... --scene ... --after 4439 --fov 0.080 --pixel-aspect 1.33333 --size 71`; 0.080
  deg = FVW 58.5 m at 22.5 NM across the 4:3 sensor's 1440 square px, k 18000): the camera was not turning against
  the ground while it held the object (0.3 +- 0.0 square px/s); the departure as a whole, 4439-4549 to the dash's jump
  at 4553, crosses the ground at **0.0079 +- 0.0002 deg/s** (143 square px/s, heading 328 deg, up and to the left),
  +43 sigma; the dash's centroid 4561-4567 at 0.11 +- 0.014 deg/s after a jump of 475 px; after the release the scene
  drifts 0.6 px/s. **The release explains neither the drift nor the dash.** Not said by the tool: the range (SLR is the
  ground's), so no speed -- at the ground's 41.7 km the drift would be 5.8 m/s across the line of sight (the note's
  "8 knots" from the released copy's slower read).
- Golden: `test_pr051_released_track_against_the_scene` (8 checks, ~3 min: `layers` then the stage from the cache).

### The 9 % shortfall, read (`shortfall.py`; session 4's chain `v04-s5/runs/s5_pr051`, session 2's `truth.npz`)

The chain over 5.0-13.5 s is 0.913 of the bar's expected path at a pixel aspect of 4/3 (0.932 over 5.0-9.5), and by
thirds 0.94, 0.90, 0.89: it falls further behind along the window. Three readings:

1. **Not the timing.** The bar's path read at t +- 0.25 or 0.5 s moves the ratio by under 2 % (0.896-0.913); the
   picture's frames shifted by a quarter second either way, 0.887-0.920. A steady rate does not care where the clock
   sits.
2. **The aspect, in part.** At 1.30 (what the pointer-convention fit preferred for this framing, gain held at 1) the
   ratio is 0.936; at 1.25, 0.974. Two to three points of the nine.
3. **The picture agrees with itself; the bar does not agree with the picture.** The pointer (the a1b and a1 series,
   square px at 4/3) turns at 0.260 deg/s over 4.5-14 s against the bar's azimuth rate (ACFT to TGT A) of 0.273:
   0.953 of it (0.977 at an aspect of 1.30). The scene over the pointer with the hold out -- `slew`'s own quantity --
   gives **c = 2160 px/deg at 4/3 and 2140 at 1.30, against the truth 2230: 3-4 % under**; the scene over the bar's
   azimuth gives 2020 (9 % under). So the pointer and the scene say the line of sight turned 0.253-0.260 deg/s and
   the bar's grid says 0.273: the TGT A solution marches 5-9 % faster across the line of sight than the sensor's own
   azimuth as drawn and than the ground in the picture (the same solution that coasts stale in the 4X stretch, the
   note's §46.1). What is left over after the aspect is the bar's, not the chain's, and the data bar's expected path
   should be quoted as "the bar's grid" with that caveat; the golden check's 10 % / 15 % tolerances stand.

`slew --hold-rate 0.074` on the whole chain (`runs/slew.sbatch`): with the pointer read every second frame (the a1b/a1
series, `--step 2`) and the chain at k 2, the pointer smoothed with the chain's kernel never covers 0.6 of it
(`MIN_COVER`: half, every frame) and every window has 0 samples -- the series must be read every frame for a k-2
chain. A `symbology --method template --step 1` over 271-841 was run (`runs/north/`) and `slew` tried again on it:
with the hold given, **7-14 s claims c = 2843 px/deg (16-84 % 1969-2855; the forward fit 2112; the truth 2230
inside the band, the point a quarter high) with the pointer's rate and the scene's at r 0.05** -- the lag: the dial's
turn over the window is the slew's, its rate is not; 4.5-14 and 5-13.5 s are refused (the slopes 38-45 % apart, the
bootstrap +-29-32 %); without the hold every window is NO POWER (c at least 324-362). The rates gate (r 0.5, method
§17) would refuse 7-14 s, and I tried applying it with the hold given too -- but a steady pan, which `--hold-rate` is
for, has no rates to correlate, and `test_slew`'s "the hold given: c comes back" fails under it (c None against 2200):
reverted, nothing committed of it, noted in method §17 as known and open. The pointer read every frame at `--min-ncc
0.5` solves 515 of 571 (411 kept by `clean_pointer`; at the default 0.7, 126). So PR051 still gives no k from its
slew, and the reason is now exact: a dial that stalls beyond its grid. The test to add is for that stall.

### Tests at the end

From a `git archive` snapshot of abb8523 (`/scratch/mcdonald/v04-s6/snap`), one Slurm job a suite, `MCDONALD_DATA`
set, `TMPDIR` on `/scratch/tmp/s6`; logs in `/scratch/mcdonald/v04-s6/suites/logs/`: all 20 pass -- measurement 483,
reduction 350, gui 744 (1 skip, the WxAgg backend), camera 134 (103 + the scene test's 31), cli 126, camera's golden
below, slew 59, audio 54, published 32, zoom 31, share 25, tether 24, horizon 17, waves 14, stabilize 13, aspect 10,
focus 10, sweep 10, haze 9, streak 5, and **golden 133 PASS, 0 SKIP** (125 + PR051's released track's 8). The
`slew` gate that was tried and reverted (above) never entered the snapshot; `test_slew` on the checkout with it
failed one check, without it the suite is the snapshot's.

**Left behind:** nothing in `/tmp`; the suites' temporary folders on `/scratch/tmp/s6` removed; `/scratch/mcdonald/
v04-s6/` kept (the snapshot removed -- it is abb8523); the frame cache has the upload's 4200-4700 now; the Slurm queue
is empty of mine.

### Open, in the order Jacob chose (2026-10-28, after session 5)

Jacob, 2026-10-28: 0.4.0 is about half way, the k half done and objective 3 untouched. **Next: objectives 3 and 4**
("what survives the missing variables" and "a speed with a band for every track"), in a new session, starting now
without ADS-B: **he has asked the Galileo Project for the ADS-B data and does not have it yet**, so the validation of
tau and the aspect on Galileo aircraft is the last step, slotted in when it arrives. **PR043 and the parallax ladder's
fix are on hold until N. Long has finished revising his homography** (the row stays "to do, for 0.4.0").

1. **Objective 4 first, then 3 -- my suggested order, since 4 is self-contained and 3's figure wants its band**
   (Jacob's words were "3 and 4"; a word from him reorders it).
   - **The speed band (K1; ROADMAP row 762):** v(t) with a band from the track's own covariance -- a Matérn-3/2 kernel
     with a nugget for the centroid's jitter, fitted by REML, the instantaneous velocity kriged from it; the average
     speed's honest error; acceleration as a likelihood ratio, not a refusal; non-uniform motion described, not
     averaged. The survey that tested it on the recorded tracks is `~/research/uap/analysis/methods/
     kriging_methods_survey.md` ("The answer, first", §1.1-1.2, §3.1, §6 Ranked ports; its scripts and results in
     `kriging_survey/` beside it): the kriged velocity up to 13x tighter than frame differences (median 8x; under 3x
     on PR23 and two others), the nugget 0.1-1.5 px, the hole effect of a wingbeat in the position (§1.5). K9's pair
     errors are the weights. Where: `kinematics` (`fit_v_px` is already universal kriging with a pure nugget) and
     `report`; scipy is enough (PyKrige is in the user site, not a dependency). Tracks to hold it on: `tests/golden/
     *_track.csv`, the 14 reference case files in `/models/data/mcdonald/cases/` (22 objects).
   - **Planted tracks with the measured covariance (K8; row 763):** conditional simulation as the validation -- the
     band's coverage on tracks drawn from the fitted covariance, with and without a planted acceleration; the
     likelihood ratio's false-alarm rate from them. In `tests/`.
   - **Objective 3 without ADS-B** (rows 758-761, 765; I6 at 767): (a) the dimensionless numbers as report facts --
     the turn radius in body widths (the track's curvature over the object's width, no range; neither PR43's nor
     PR113's object turned), the smear number (`streak`), the obliquity from the vanishing point, the parallax number
     (`comotion`); (b) the projective constant-velocity test (a straight image track whose distance from the vanishing
     point goes as 1/(t_z - t)); (c) the admissible region in (R, Rdot) with the speed and size distributions it
     implies, the Technical Note's fan as the standard figure of a case, fed by the bounds the four commands and the
     ledger already give; (d) edge-crossing fits and the time-distance diagram; (e) tau from looming (angular size over
     its rate) or the light curve (d ln F/dt = -2 Rdot/R, the gain out), theta = atan(omega tau), built and held on
     drawn scenes (a rendered approaching object) and on any reference case that looms -- **its validation on Galileo
     aircraft waits for the ADS-B data**.
   - What is on the drive for the aircraft when the data comes: the Dalek clips in `/models/data/galileo_project/
     IR-Dalek-Hideout/` (153 clips, 33 GB; the five bird flyers were cut from them) and `IR-Dalek-Sphere/` (2); the
     0.5 controls name "the Galileo airliners" among 21 infrared aircraft with known answers (`~/research/uap/galileo/`
     has the bird work's scripts, no README) -- find which clips hold them and match the ADS-B (range, speed, heading,
     altitude against the camera's clock); no ADS-B file is on the machine today.
2. **The ledger, finished** (session 3's item 2): the window's report card, a page or `run` stages for the bounds, R
   from a range ratio, theta bounded by tau (I6); Jacob's word on the wording (session 2) -- no answer yet.
3. The new bounds on real clips (session 2's item 4): PR149's ship for `horizon`, PR43's dash for `streak`.
4. The sweep's open items (session 2's item 3): the small zoom ratios and PR101's claim, before either is quoted.
5. The speed band (K1, K8); the parallax ladder's nearest height when Long's revision is in.
6. `camera --scene` into `run` (a case whose `layers` CSV is there, with `--after` as a known quantity) and the window
   -- the two audiences; and `Find`/`Follow` on a saturated bloom inside a bracket (above).
7. **`slew` on a dial that stalls** (above): a test for a pointer that holds still beyond its grid's step and catches
   up, so a known-hold claim from the totals is refused where the rates do not follow -- without gating a steady pan.
8. Noted, not done: session 4's item 6 (a sharp template wrong by a bump, `still_score` unused, the vote's cluster
   tolerance); a `layers` pair held still is zero in the path, so the capture's jitter stays in a track (method §20,
   how it fails).

---

## Session 4 (2026-10-28, evening): PR051's 10-13 s read and fixed -- the chain whole over 4.5-13.5 s

Jacob: "see: docs/handoff-v04.md". Took session 3's open list in its order: **item 1, PR051's 10-13 s, read and
fixed**; the released-track null (its second half) not started. On main, **committed locally, not pushed** (82f6c13;
nothing pushed or released until 0.4.0). No version bumped; CHANGELOG's Unreleased has four new items. This session's
scratch is `/scratch/mcdonald/v04-s5/` (`none_probe.py` with its five readings in `logs/`, `masked_probe.py`,
`mask_diag.py`, `own_shift_chain.py`, `compare.py`, `cmp_pr135.py`, `runs/` PR051 and PR135 with the new code
(`s5a_*` a first try before `moved` counted the templates placed), `look/` crops, `suites/logs/`, `tests/`).

### What the no-consensus pairs' fields said

Thirty pairs over 9.4-13.3 s had no consensus (24 held and measured again over 60, 6 moved). Their fields
(`none_probe.py fields`, `masked_probe.py`, `vote`; the probe reads the frame cache `~/Documents/mcdonald/frames`)
were three things, none of them K9's, and a fourth turned up on the way:

1. **The masks took half the picture.** With `layers`' own masks each pair kept 14-29 templates of the 66-85 the
   boxes alone leave, the sharp ones first. The static mask (18.6 %) was all chroma -- the static-and-sharp share is
   0.000 on this clip -- and each frame's own chroma mask added the rest (48 % of frame 603 masked). The upload's
   bright terrain (grey over 120, a fifth of the frame) carries a colour tint of 46-54 DN in 60-84 % of its pixels:
   18.7 % of the frame cast, just under the fifth that calls a clip colour. Interlace was ruled out (`comb`: the odd
   and even lines of every frame agree within 0.2 px).
2. **The holds jitter.** A repeated capture reads 0.5-1.9 px from the last (a hold's own field: 74-80 of ~80
   templates in one group), and `AT_ZERO` 0.5 sent eleven of them to a second pass over 60 frames, where a scene
   moving 600 px has no match.
3. **The big steps have no sharp templates.** Catch-ups of 70-140 px along the streaks (603, 611, 621, 639, 653 and
   their like) leave 0-2 templates sure both ways and 60+ sure only across; the zero-allowed fallback then found a
   false near-zero group (3-5 sharp at zero plus the streaks' self-match, 16 of 79 members) and the pair was "held".
   The ridge templates' own argmaxes cluster: the largest cluster 26 against the next 13 (603), 22 against 9 (611),
   28 against 9 (639), 32 against 10 (653) -- leads of 2.0-3.4 sigma of a split vote -- within 1-4 px of the sharp
   templates where there are any, and the mean correlation map over all templates (`global`) agrees to within its
   own 10-px breadth.
4. **Zero allowed on a moving streaky pair blends.** A same-position ZNCC of 0.9 or more (the old "held still")
   holds through a 15-35 px step along the streaks, and the zero-allowed field then splits between the streaks'
   self-match at zero and the step: the sure route blended them (615-617: a group of 7.1 px, n 67, for a step of
   18; 629: 4.1 px) and the vote would have picked zero (629: 49 against 29). Only the zero-left-out field is clean
   there (18.08, n 56), and on a true hold that field keeps 0-6 templates (the peaks sit on the zone's rim).

### What was built (82f6c13)

| what | where | tested by |
|---|---|---|
| **a tint is not symbology**: `tinted` where most of the brightest fifth of the sampled frames carries a cast; no chroma mask then, static-and-sharp kept; the flag travels with the masks to every worker | `forensics.static_masks` (`TINT_FIFTH`, `TINT_SHARE`), `frame_mask`; the slimmed mask dicts in `layers`, `integrity`, `autolink`, `groups`, `static_pattern`; method §3 | `test_measurement` (`test_a_redaction_block...`: a tinted drawn picture with a white glyph, a green gate on the same picture) |
| **both fields from one search**, the zero-left-out one read first wherever a fifth of the templates placed are sure or it has a consensus (`moved`); `second_pass` the same in one round; `still_score` no longer consulted (kept, unused) | `forensics.shift_field(zeros=)`, `_peak`, `moved`, `shift_field_auto`; `layers._again_part`, `second_pass`, `_window` | the held-still tests as before; PR135 to the bit |
| **the vote along the streaks** where fewer than three templates are sure both ways: the largest cluster of every template's shift, leading the next cluster a ridge's length away by `VOTE_LEAD` 2 sigmas; ridge members carry along-information equal to the cluster's scatter (>= `VOTE_FLOOR_PX`), the group's error along floored at it | `forensics.consensus`, `_vote`, `_ridge_axes`; method §31 | `test_measurement` K9 test (drawn streaks with no sharp patch: +/-1.0 along; split 13 px: none) |
| **a hold unmoved inside the zero zone** (`AT_ZERO` 4 px) with nearly every template in one group (`REPEAT_SHARE` 0.8) | `layers.repeating` | the repeat test (1.5-px holds unmoved; 8 of 38 at zero not) |
| the golden check through 13.5 s: `layers` 301-811, nearly every pair measured, 5.0-9.5 s within 10 %, 5.0-13.5 s within 15 % | `tests/test_golden.py` (`test_pr051_scene_path_against_the_data_bar`, ~6 min now) | golden |

**What changed on real clips:** PR135 150-305's layers CSV is the same to the bit (151 pairs, errors 0.007 px).
PR051 (`--k 2 --step 2`, the boxes; `runs/s5_pr051`, `compare.py`): every pair over 4.5-13.5 s has a consensus
(49 % steps, 67 % unmoved, 2 steps bridged where 126 were; `held still ... 69 %` in the stage's line), the new
run's steps within 1 px of the probe's readings pair by pair, and the chain whole in one stretch over 4.5-13.5 s --
at **0.93 of the data bar over 5.0-9.5 s and 0.91 through 13.5 s** (`own_shift_chain.py`: with the unmoved pairs at
their own shift instead of zero, 0.94 and 0.89-0.92: the holds' creep, median +0.2 px, is 1 % of it). Session 3's
0.94-0.95 over 5.0-9.5 s was a broken chain bridged at its neighbours' rate, which over-counts inside a hold (the
`s5a` run, bridged 46, read 1.03 over the whole). **The shortfall is now steady, not lost steps**, and its cause is
open: the bar's half-second readings scatter from 0.57 to 1.43 of the chain (digits read by eye), the line of sight
is taken at a fixed 7 deg true, and the first half second (4.5-5.0 s) has 17 px of motion in the picture against
242 in the bar -- the picture against the data bar's own timing (the overlay's clock and the imagery may not be
synchronous in this upload). To look at: the ACFT/TGT readings against the pointer's own azimuth, and the bar's
expected path with the timing shifted by a hold.

**Tests at the end** (d4a14c8 -- 82f6c13 the work, c610121 and d4a14c8 two test fixes found by the suites: a hand-made
masks dict without `tinted` crashed `autolink`'s workers, the PR051 check had counted every frame row as a pair, and
the K9 test's drawn streaks gave 2 sure templates in the full suite's RNG order where the sure route needs 3 -- they
are drawn from a generator of their own now, seed 2, 5 sure). From a `git archive` snapshot, one Slurm job a suite,
`MCDONALD_DATA` set; logs in `/scratch/mcdonald/v04-s5/suites/logs/` (`test_measurement3.out` the final measurement
run, `golden_pr051.out` the PR051 check rerun alone after the fix): all 20 pass -- measurement 483 (477 + the tint's
3, the holds' 2, the vote's 1), reduction 350, gui 744 (1 skip, the WxAgg backend), cli 126, camera 114, slew 59,
audio 54, published 32, zoom 31, share 25, tether 24, horizon 17, waves 14, stabilize 13, aspect 10, focus 10,
sweep 10, haze 9, streak 5, and **golden 125 PASS, 0 SKIP** (118 + PR051's scene path's 7: nearly every pair
measured, both windows whole, 0.932 and 0.913 of the bar, the path's error +/-5 and +/-10 square px).

**Left behind:** nothing in `/tmp`; the suites' temporary folders on `/scratch/tmp/s5` removed; `/scratch/mcdonald/
v04-s5/` kept (the probes and their readings, the runs, the logs; the snapshot removed -- it is d4a14c8); the frame
caches as session 3 left them, plus the new `layers` cache in `v04-s3/pr051_wd` (`bg_layers_k2_s2_271_841_fc8902e095.npz`,
the new rules' key). The Slurm queue is empty of mine.

### Open, in the order I would take them

1. **The released-track null on PR051** (session 1's item 3): the scene through the leak's breaklock, now that the
   chain holds through catch-up steps of any size. And the 9 % shortfall above, read against the bar's timing
   before `slew --hold-rate` is tried again on 7-14 s (the pointer's lag, session 2, stands).
2. **The ledger, finished** (session 3's item 2): the window's report card, a page or `run` stages for the bounds, R
   from a range ratio, theta bounded by tau (I6); Jacob's word on the wording (session 2) -- no answer yet.
3. The sweep's open items (session 2's item 3).
4. The new bounds on real clips (session 2's item 4).
5. The speed band (K1, K8), objectives 3 and 5, the parallax ladder's nearest height (session 2's item 5).
6. Noted, not done: a sharp template wrong by a bump on its ridge (§31); `still_score` unused; the vote's cluster
   tolerance (6 px) against a 13-px period leaves votes between modes in no cluster -- fine while the lead is
   measured, a thing to know if a clip's period is nearer 12.

---

## Session 3 (2026-10-28, afternoon): K9 built, PR051's scene path a golden check

Jacob: "see docs/handoff-v04.md". Took session 2's open list in its order: **item 1, K9, is built and checked**, and
PR051's scene path against the data bar is a golden check. On main, **committed locally, not pushed** (nothing pushed
or released until 0.4.0). No version bumped; CHANGELOG's Unreleased has the item. This session's scratch is
`/scratch/mcdonald/v04-s4/` (`probe/` the peak probe and its three readings, `runs/` PR051 and PR135 with the new code,
`suites/`, `tests/`); `/scratch` is the new drive (session 2's note holds: every older path is gone).

### What was done

| what | where | tested by |
|---|---|---|
| **each template's own error** from its peak's curvature (`SHIFT_COLS` + `wxx wyy wxy ridge`): the least-squares covariance 2(1-pk)/N K^-1, scaled 3.5x in sigma (drawn textures) with a 0.02-px floor, kept as the information matrix | `forensics.peak_information`, `PEAK_ERR_SCALE`, `PEAK_FLOOR_PX`; method §31 | `test_measurement` (`test_each_template_weighed_by_its_own_error`, 8 checks) |
| **a template sure only across its ridge**: runner-up within `good`'s gap -> information across the line to it alone, `ridge` = the runner-up's distance; `ridged` picks them; in `consensus` they are members across their ridge (within the tolerance) and along it within ridge + tolerance, count towards the 8, fix nothing along; 3 sure both ways needed; a shift unconstrained along some line is none | `forensics.ridged`, `consensus(w=, ridge=)`, `layers_of` | the same test (36 of 40 drawn-streak templates ridged, 4 sure: found; no sharp patch: none) |
| **the weighted shift**: GLS over the group by each member's information, scaled to the members' pull (>= 1), Huber 2.5; the covariance | `forensics.weighted_shift` | the same (rigid +/-0.004 px; half the templates 1.5 px off: +/-0.12) |
| the pair's error in the layers CSV (`err_x_px`, `err_y_px`), `shift_error_px` in the fields and `said`; an unmoved pair keeps its own field's covariance; the cache key has the rule | `layers.measure` | end to end in the same test |
| the chain weighs each step's pairs by their errors and carries the path's own (6th value with `err=`); `read_layers(errors=True)`; each slew window's `scene_path_err_px` | `slew.read_layers`, `scene_path`, `series`, `measure` | the same test's chain check; `test_slew` 59 |
| `comotion.local_flow`: the annulus's weighted mean where within 3 px of the median, `err` beside `sd` | `comotion.local_flow` | -- (no golden; the median kept where they disagree) |
| **PR051's scene path against the data bar**, 5.0-9.5 s: one stretch, 1740 against 1848 square px (x0.942), the path's own error +/-7 | `tests/test_golden.py` (`test_pr051_scene_path_against_the_data_bar`, ~3 min: `layers` 301-571 `--k 2 --step 2` with the 13 boxes, chained in square px against TGT A's motion across the line of sight computed from `pr051_databar_track.csv` in the test) | golden |
| the second pass's L-frame shifts scaled consistently (information by (L/k)^2, the ridge by k/L) | `forensics.scaled_shifts`; `layers._again`, `second_pass` | `test_measurement`'s held-still tests as before |

**The probe that fixed the numbers** (`/scratch/mcdonald/v04-s4/probe/peak_probe.py`, `probe_*.out`): on drawn
textures with white noise in both frames the curvature's least-squares error understates the residual by 3.5 in sigma
at every noise level (band-passed pixels are not independent), and the parabola alone is 0.02 px at zero noise; on
PR135's held pairs (a real scene) the templates scatter nine times the prediction (0.05-0.16 px over 5 frames), hence
the group's pull scaling; on PR051's pairs 55 of 69 templates have their runner-up at (+/-13, 0) -- 13 px along the
streaks, just outside the 12-px zone -- at the peak's own height, their dx scattering 96-110 where the sharp ones
(gap 0.08-0.16) agree within a pixel: that is what "counted across its streaks" means in numbers.

**What changed on real clips:** PR135 150-305's layers CSV differs by at most 0.02 px a pair (members up by 1-4 where
ridge templates joined, errors 0.007 px); PR144's goldens are as they were; PR051 (`--k 2 --step 2`, the boxes): 37 % of
pairs with a consensus (12 % before), 53 % of pairs unmoved between catch-ups (16 %: more pairs reach a consensus, so
more windows qualify as repeating), the whole scene 520 px/s median in 186 windows (344 in 42), the chain in one
stretch over 5.0-9.5 s at 95 % of the bar (`compare.py` in `v04-s4/`), then at half the bar's rate over 10-13 s.

**Tests at the end** (f7f7fad, from a `git archive` snapshot, one Slurm job a suite, `MCDONALD_DATA` set; logs in
`/scratch/mcdonald/v04-s4/suites/logs/final/`): all 20 pass -- measurement 477 (469 + the new test's 8), reduction
350, gui 744 (1 skip, the WxAgg backend), cli 126, camera 114, slew 59, audio 54, published 32, zoom 31, share 25,
tether 24, horizon 17, waves 14, stabilize 13, aspect 10, focus 10, sweep 10, haze 9, streak 5, and **golden 121
PASS, 0 SKIP** (118 + PR051's scene path's 3; peak 3.9 GB at 4 CPUs). The same three suites passed on the checkout
before the commit (golden 118 then, before the new test was added).

**Left behind:** nothing in `/tmp`; the suites' temporary folders on `/scratch/tmp` removed; `/scratch/mcdonald/v04-s4/`
kept (the probe, the runs, the logs; the snapshot removed -- it is f7f7fad); the frame caches as session 3 left them
(`v04-s3/pr051_wd`, `v04-s3/pr135_frames`, `~/Documents/mcdonald/frames`). The Slurm queue has only Jacob's own
arrays (`regime`, `orb_sweep`), untouched.

### Open, in the order I would take them

1. **PR051's 10-13 s.** Every other catch-up step there has no consensus at all (`over_frames` 60 in the CSV: held
   over 2, measured again over 60, none) -- `v04-s4/runs/k9_pr051/` has the CSV, the cache
   `/scratch/mcdonald/v04-s3/pr051_wd/bg_layers_k2_s2_271_841_*.npz` the templates: read those pairs' fields (the
   probe's `show_pair` does it). Then the released-track null (session 1's item 3), which needs the scene through the
   breaklock.
2. **The ledger, finished** (session 2's item 2): the window's report card, a page or `run` stages for the bounds, R
   from a range ratio, θ bounded by τ (I6); Jacob's word on the wording (session 2, below) -- no answer yet.
3. The sweep's open items (session 2's item 3).
4. The new bounds on real clips (session 2's item 4).
5. The speed band (K1, K8) -- K9's pair errors are the weights it wanted; then objectives 3 and 5; the parallax
   ladder's nearest height (session 2's item 5).
6. A sharp template wrong by a bump on its ridge (PR051 439-441: two of the 13 "good" read 77 and 89 against 108)
   is caught only by the group's tolerance and the Huber weight, not by its own error; fine for now, noted in §31.

---

## Session 2 (2026-10-28): where things stand

Jacob: "Keep going with the next 0.4.0 session handoff". Worked from session 1's "Open" list, in its order. On main,
**committed locally, not pushed** (Jacob, 2026-10-27: nothing pushed or released until 0.4.0): fd88370 (the code and
its docs) and the handoff commit after it. No version bumped; CHANGELOG's Unreleased has the new items.

**First, before anything else: `/scratch` is a new, empty drive.** The 3.6-TB scratch disk was taken out on
2026-10-27 (its `/etc/fstab` line is marked `#REMOVED-2026-10-27#`) and a 1.8-TB one mounted at `/scratch` on
2026-10-28, empty. **Every `/scratch/...` path in session 1 below, in the older handoffs and in the memory notes is
gone**: session 1's PR051 runs and its 12 hand-drawn overlay boxes (`/scratch/mcdonald/pr051-2026-10-27/`), its suite
logs (`v04-dev/`), the sweep's list and results (`pointer-sweep-2026-10-27/`, `out_v04/summary.md`), and older
recipes (the reference case files' `cases-2026-10-16/18`, the flicker controls, the censuses). What survived is on
`/hugespace` (the slew chains in `/hugespace/local/tmp/slew/`, the frame cache `~/Documents/mcdonald/frames`) and in
`/models/data/mcdonald`. This session's work is in `/scratch/mcdonald/v04-s2/` on the new drive: `diag/` (PR051's
scripts and readings), `seq*/` (frame sequences, symlinks), `sweep/` (the re-run), `suites/` (the test logs).

### What was done

| what | where | tested by |
|---|---|---|
| PR051's pointer and picture, frame by frame, against the data bar read every 0.5 s (below) | `/models/data/mcdonald/pr051/pr051_databar_track.csv` (README, SHA256SUMS); scripts in `/scratch/mcdonald/v04-s2/diag/` | -- (a finding; no code changed) |
| **the four unknowns** on every report (objective 6, first form): k, R, θ, v_own -- constrained, assumed, bounded or missing, the route, and the datum that would close each; in the JSON as `ledger` | `report.Case.ledger`, `_ledger`, `LEDGER_CLOSES` | `test_reduction` (`test_the_four_unknowns_say_where_each_stands`) |
| `--case CASE_JSON` on `horizon`, `haze`, `focus`, `slew`: the measurement recorded in a case `run` made, its report written again with the bound in the table | `report.into_case`, `case_option`, `command_line` | `test_reduction` (the round trip through a written case) |
| PR43's streak read (item 4) | `/scratch/mcdonald/v04-s2/pr43/` | -- (a reading) |
| the pointer sweep re-run with session 1's code (item 2; its results had gone with `/scratch`) | `/scratch/mcdonald/v04-s2/sweep/` (`list.tsv` rebuilt from the uap `clips.csv`), copied to `/hugespace/local/tmp/slew/sweep/pass5/`; pass 5 written into the uap `analysis/corpus/pointer_sweep/README.md` (uap 336273c, those two files only) | the same counts as session 1 to the burst: 95 measured steps of 573, the x2.00 / x5.9 ladder, PR27 267 -> 517 and PR057a 276 -> 584 (both agreeing with their imaged x2), PR134 205, PR101 141 |

**Tests at the end** (fd88370, from a `git archive` snapshot, one Slurm job a suite, `MCDONALD_DATA` set; logs in `/scratch/mcdonald/v04-s2/suites/logs/`): all 20 pass -- measurement 461, reduction 350, gui 744 (1 skip, the WxAgg backend), cli 126, camera 114, slew 59, audio 54, published 32, zoom 31, share 25, tether 24, horizon 17, waves 14, stabilize 13, aspect 10, focus 10, sweep 10, haze 9, streak 5, and **golden 118 PASS, 0 SKIP** (peak 4.3 GB at 4 CPUs, 19 min).

**Left behind:** nothing in `/tmp`; the suites' temporary folders on `/scratch/tmp` removed; `/scratch/mcdonald/v04-s2/` (39 MB) kept; the frame cache `~/Documents/mcdonald/frames` as session 1 left it (the upload's frames 181-860; every run of this session read it or used its own work directory). The Slurm queue is empty.

### PR051: why its slew gives no k, read against the data bar

Session 1 left PR051's NAR stretch at NO POWER with the pointer's rate and the scene's anti-correlated, and asked
first for "the pointer's own steps against the picture's jumps, frame by frame". Done, on the cached frames 181-860
of Corbell's upload (`diag/framewise.py`, `jumps.py`, `isox.py`, `truth.py`, `rebuild.py`), and then against the data
bar itself: the aircraft's position (ACFT, 0.1") and TGT A's grid (MGRS, 1 m) read every 0.5 s over 3-14 s give the
line of sight's true azimuth (grid convergence -1.11°) and the scene's expected path (TGT A's motion across the line
of sight over FVW, times 1440 square px).

- **The picture repeats and catches up.** Every frame is doubled (59.94 over 29.97), and beyond that the content is
  often the same picture again with new capture noise (a zero shift to 0.05 px), then moves on by 10-110 px; at other
  times it moves a few pixels every unique frame. The whole capture also jitters by a few pixels a line (analog
  timebase), overlay and all.
- **The pointer is a dial drawn in steps that lags.** Over 4.5-14 s the bar's azimuth turns 2.55° and the pointer
  2.23°; the pointer holds still for up to 2 s while the azimuth moves 0.6°, then catches up in 0.2-0.5° steps
  (one step of the display's grid is about 0.35-0.4° at its radius in the 4:3 picture). Against the bar it is off by
  0.17° rms, 0.11° rebuilt straight between its steps: a stall is not a grid, so no rebuild recovers it. Its mean
  rate is right (0.25-0.26°/s against the bar's 0.26), as the 80-s convention check found (gain 0.965).
- **So `slew`'s NO POWER is right, and the anti-correlation is the lag**: the scene moves on (the bar says 445 square
  px/s; the aircraft gives the hold, 0.074°/s, near session 1's 0.068) while the pointer sits still, then the pointer
  jumps while the scene does not. Over NAR's 11 s the pointer's swing beyond a steady rate is about one of its steps.
- **The scene can be measured, and `layers` does not yet.** With zero shift allowed on unique pairs, `shift_field`'s
  striated templates (the terrain is streaks) measure each step (frames 439-441: 108 px, 9 templates agreeing, against
  phase correlation's 110 and TGT A's 99 -- and the picture by eye). But where a step has no consensus (22 of 329
  unique pairs, most in 9.5-11 s), bridging at the neighbours' velocity loses the jump, and the path came to 2,793
  of the bar's 4,145 square px over 4.5-14 s (83 % of the bar where it measured). `layers` itself, on a sequence of
  the content changes alone, still called 81 % of pairs held still.
- What it does not give: c from the totals with the hold given came out 1,600-1,900 px/deg against the truth 2,230,
  and frame by frame 1,000-1,600 -- neither a measurement; no claim was made.

The data-bar track is now reference data, the known answer for any scene measurement on this stretch (its expected
path is 445 square px/s over 4.5-14 s) and for the pointer's path.

### The four unknowns (objective 6), as built

`Case.ledger()` writes from the stages' fields, as `summary()` does: k from `scale` (constrained, or "assumed" where
`scale` says ASSUMED -- every `--fov` without `--fields`), else from `slew` (constrained with a depression given;
bounded by c; bounded by a floor only where `floor_stands`); R given, else bounded by `horizon`'s `range_max_m`,
`haze`'s `bound_m` (to its factor of four) and `focus`'s `floor_m`; θ given or from a range rate; v_own given (the
parallax inputs). The markdown's "## The four unknowns" sits after "## Summary of variables" and before "## Missing
quantities"; the window's report page shows the full report, so it reaches the window too, but the report card
(`report_qt._fill`) shows only the summary's values, and the four bound commands have no page in the window: both are
open (two audiences).

### Later the same day: repeated frames in `layers` (Jacob's decision)

Jacob, 2026-10-28, on my recommendation (tell repeats from a slow scene before measuring a held pair again; a census of
repeated frames first, as `integrity` takes one): **"Go with your recommendation on repeated frames in layers."** Built
on a branch in a worktree (`v04-repeats`, b8b54f1, fast-forwarded into main after the suites), because the probes ran from
the main checkout. What it became, and why not the census first:

- **A per-pair sub-pixel test cannot be the rule.** A one-step Lucas-Kanade shift, tile by tile
  (`/scratch/mcdonald/v04-s3/lk_probe.py`, `lk_probe.txt`), reads PR051's true holds at 0.04-0.09 px (z 2-5) and PR135's
  island, which moved 1.6 px in those 5 frames, at 0.04-0.07 (z 2-4): its fixed pattern swallows the drift. And
  `forensics.repeats` finds exact copies only; PR051's holds are new captures of the same picture, noise in every pixel.
- **The order of the pairs can.** `layers.repeating`: in a window where the held pairs and the catch-ups (12 px or more
  over k frames) alternate four times or more, with under a third of the pairs in between, a held pair whose own field
  (zero allowed) agrees on zero is UNMOVED -- zero, not measured again. With it, `held_but_moved`: a pair called held
  whose own field agrees on more than 5 px moved and keeps that (a streaky scene moving along its streaks keeps its
  same-place correlation high; PR051's 439-441 step was found, 108 px, and thrown away).
- **Checked**: `test_measurement`'s new test (drawn sequences; end to end on a lossless repeating picture: 204 px of 210,
  312 without the rule); PR135 150-305's layers CSV byte-identical before and after; PR051's NAR stretch with whole-frame
  pairs (`--k 2 --step 2 --max-shift 100`): a consensus in 12 % of pairs (5 % before), 16 % unmoved, the chain whole over
  5-7 s at 71 % of the data bar's motion, then broken again (runs in `/scratch/mcdonald/v04-s3/runs/`, `compare.py`).
- **What PR051 now waits on is templates, not repeats**: on its streaky terrain most pairs have 4-8 good templates, under
  the 8 a consensus needs (my scratch run that tracked the bar asked for 4). The floor protects every clip and was not
  lowered; K9 -- each template weighed by its own error, a striated one counted across its streaks -- is the way.
  So the golden check of PR051's scene path against the data bar waits for K9.
- **Tests** (b8b54f1 from a snapshot, one Slurm job a suite, logs `/scratch/mcdonald/v04-s3/suites/logs/`): all 20 pass,
  measurement 469 (461 + the new test's 8), golden 118 PASS 0 SKIP, the rest as in the morning.

**The ledger's words, put to Jacob the same day** (he asked which to look at): the status words (constrained / assumed
/ bounded / missing -- "constrained" covers measured and given; "known" is the plain alternative), the column headers
("where it stands", "by", "what would close it"), the "what would close it" texts (FVW / SLR, "range rate", "track" --
the most technical; the window shows the full report), the section's title and place (after the summary of variables),
and the bounded rows (a slew's c as "at least ... px/deg"; two range bounds in one cell). No answer yet.

### Open, in the order I would take them

1. **K9**, layers' per-template error from its peak's curvature (`shift_field` already computes kxx, kyy, kxy and keeps
   only their ratio and axis): a 2x2 covariance a template, a weighted consensus, a pair's error in the CSV, weights in
   `slew`. PR051 is now the reason in numbers: its pairs have 4-8 good templates, mostly striated, under the
   consensus's 8; then PR051's scene path against `pr051_databar_track.csv` as a golden check (it needs no pointer).
2. **The ledger, finished**: the window (the report card; a page for the bounds or `run` stages for them), R from a
   range ratio, θ bounded by τ (I6) when it comes; and Jacob's word on its wording (above).
3. The sweep's open items (session 1's item 2; pass 5 is now written): look at the scatter of small ratios (x1.09-1.78: PR49's x1.735 then x0.529 a second apart, PR108's three within five seconds, PR116, PR091, PR054, PR27's x0.852 at 127.7 s -- some may be a continuous zoom) and at PR101's claim (141 +- 17) before quoting it; and the hint in pass 5 that PR27's wide field at x11.8 (0.61 deg) is 5 % from PR051's NAR (0.6427 deg) -- a shared ladder would put a field on every clip that zooms to or from a state of it.
4. The new bounds on real clips (session 1's item 4): `streak` on PR43 with the clip's own blur (`forensics.point_blur`,
   as `focus` measures it), `horizon` on a sea horizon of known height and range, `focus` and `haze` on a daytime clip
   with a known range.
5. The speed band (K1, K8), then objectives 3 and 5.
   Also for 0.4.0: the parallax ladder's nearest height for a still object (ROADMAP's ideas bank, the last 0.4 row,
   from Long's homography draft): `kinematics.parallax_ladder` reports k v_O as the object's own speed and picks k
   by it (PR043: 922 m/s printed where 31.5 is needed); the row has the fix and the test's known answer.
6. The released-track null on PR051 (session 1's item 3): it needs the scene measured through the leak's breaklock,
   which waits on K9 first.

---

# Session 1 (2026-10-27), the record -- finishing k, PR051 as a known answer, the range bounds without motion

Jacob asked (2026-10-27): "Let's do all of the above for the 0.4 release. Let's first focus on everything needed for 3
finish k and evaluate on PR051. 5 is also important. Go ahead with the first session, prompt when needed, and then work
until we need to handoff to another session. Submit jobs through /slurm". "Above" is the path to 0.4 given that morning
(the order: 1 layers' per-template error K9; 2 the unknowns ledger as a skeleton; 3 finish k -- PR051, the pointer sweep
re-run, camera and zoom reading each other; 4 the speed band, kriging K1 with planted tracks K8; 5 the range bounds
without motion -- horizon, haze, focus, the streak; 6 then objectives 3 and 5, the admissible region and tau/aspect on
Galileo aircraft with ADS-B, and more kinds of known quantity). This session did 3 and 5; 1, 2, 4 and 6 are next.

Decision asked and given: **`integrity` switches its zoom across transients to `zoom_fit`** ("Switch to zoom_fit").

## Where the work is

Built in a worktree (`/hugespace/models/mcdonald-v04`, branch `v04-k` off main at e60238f), because Slurm jobs import
the main checkout's code at each start and a half-finished edit there would have broken them (it nearly did: see "What
went wrong"). At the end it was committed and **main fast-forwarded to it, locally; the worktree and the branch were
removed. Not pushed, no version bumped** (CHANGELOG has an Unreleased section). **Jacob, 2026-10-27: "just commit, we'll
hold on pushing until 0.4.0"** -- the 0.4 sessions commit to main locally and nothing is pushed or released until 0.4.0. Scratch job scripts under `/scratch/mcdonald/pr051-2026-10-27/` and `/scratch/mcdonald/v04-dev/` still name
the worktree's `src`: point them at the main checkout to run them again.

**Tests at the end (2026-10-27, the final code):** every suite one job each (`/scratch/mcdonald/v04-dev/suites/`): the
17 of `tools/suites.sbatch` passed mid-session, and the ones touched after (measurement 461, reduction 344, cli 126,
zoom 31, camera 114, slew 59, horizon 17, focus 10, haze 9, streak 5) passed again on the final code, with **golden 118
PASS, 0 SKIP** (PR051's zoom among them). `tools/zoom_check.py`: all passed (PR27's and PR057a's steps and slews,
Puerto Rico's three switches, the 142.6-s one now a step confirmed by two pairs; PR27's traps unknown).

## What was built (each with its tests; method sections in `docs/method.md`)

| what | where | tested by |
|---|---|---|
| a zoom with no blank: the scan's own steps of level or contrast (`events.picture_steps`, shared with `events`) and `zoom --events CSV`, fitted as bursts; a measured one a boundary (`kind` "picture"), the rest kept in `picture_steps` | `zoom.picture_candidates`, `plan`, `measure`; method §17 | `test_zoom` (end to end through `zoom.measure` from rendered frames); PR051's leak x0.498 vs the data bar's x1/1.999 |
| the zoom fit's window variance in float64; a window with no detail no match | `forensics._zoom_score`, `ZOOM_FLAT` | `test_zoom` (a frame flat in part; fails on the old code: ZNCC 10.46, a false x0.136) |
| a marginal fit confirmed by pairs 1-3 frames out (two passing on their own, within 3 %) | `zoom.marginal`, `zoom.confirm` | `test_zoom` (the rule, with fit_all stood in for); `tools/zoom_check.py`: Puerto Rico 142.6 s now a step |
| a strong fit (ZNCC >= 0.5 and twice its rival's) leads whatever the prominences | `forensics.ZOOM_STRONG`, `ZOOM_ZNCC_LEAD`, `zoom_fit_scenes` | PR144's x5.8 (see below); `zoom_check` |
| `integrity` across transients through `zoom.fit_all` + `zoom.confirm` (Jacob's decision) | `integrity.transient_zooms` | PR144: step x5.804 (ZNCC 0.87), its second transient no step x0.995 (/scratch/mcdonald/v04-dev/pr144_izoom3_*.out) |
| `camera --zoom` and `run`'s camera stage reading `<tag>_zoom.json`: imaged steps taken out of the track, checked on the object; other bursts camera events | `camera.imaged_steps`, `first_new`, `burst_events`; `stages` camera | `test_camera` (`test_zoom_from_the_picture`) |
| `slew`: one row a state (a "no step" join had counted windows twice); the figure a row for the clip, then a row a state; a state under 0.5 s no longer crashes `slews` | `slew.measure`, `figure`, `slews` | `test_slew` (the figure's height; five frames); PR27 unchanged (267 -> 517, x1.932 vs x2.000) |
| `mcdonald horizon` | `horizon.py`, method §27 | `test_horizon` |
| `mcdonald focus` | `focus.py`, method §28 | `test_focus` |
| `mcdonald haze` | `haze.py`, method §29 | `test_haze` |
| `mcdonald streak` | `streak.py`, method §30 | `test_streak` |
| the pointer sweep tool | `tools/pointer_sweep.py`, `tools/pointer_sweep.sbatch` | PR27 through it: 267 -> 517 px/deg, x1.932 vs x2.000, agree |

README-technical lists the four new commands and `zoom --events`, `camera --zoom`; tests/README.md the four new
suites; `tools/suites.sbatch` runs them; ROADMAP's ideas-bank rows for these are updated; CHANGELOG has an Unreleased
section.

## PR051 (the user's ask): what it gives, and where

Reference data (`/models/data/mcdonald/pr051/`, README, SHA256SUMS): Corbell's upload and Sitrec's .mov (watermarked:
a local reference, not to be redistributed, as `ptzslam_soccer/` is), the released copy in `pursue/`, and three
readings tables. The known answers, read off the data bar by eye:

- **The first framing of the upload (t 3-35 s) has three fields**: NAR to 14.0 s, FVW / SLR = **0.6427 deg +- 0.15 %**
  (649-657 m at 31.23-31.64 NM); ULTN from 14.25 s, 0.3212 deg (x2.001); 2X of ULTN from 17.0 s, 0.1610 (x1.995). In
  NAR, k = 1440 / 0.6427 = **2240 px/deg** in square pixels (the 4:3 sensor stretched to 1920), and the depression
  5.1-5.4 deg (HAT 17,072 ft over SLR), so **c = k cos e = 2230 +- 10 px/deg** is what `slew` should read there.
- **The leak's electronic zoom out at its frames 1331-1341** (2X -> ULTN, no blank, FVW 119 -> 238-239 m): `mcdonald zoom`
  measures **x0.498 = 1/2.008 against x1/1.999**, the first real known answer for a zoom with no blank.
- The upload's NAR -> ULTN switch at 13.85-14.21 s (with a blank) comes out unknown (x0.99 at ZNCC 0.15: streaky
  terrain sweeping during the blank); its ULTN -> 2X at 16.9 s is not found (neither level nor contrast steps).

What it took to get `slew` going on it (each a trap worth knowing):

1. **The overlay is not masked by itself.** The analog capture jitters the whole picture, so no pixel holds within 2
   grey levels (`static_masks` finds 0 %), and the clip reads as colour, so the colour route is off too. Unmasked,
   `layers` read the scene held still in 88 % of pairs. Boxed by hand (12 boxes; `/scratch/mcdonald/pr051-2026-10-27/
   run_nar2.sbatch` has them), it moves: 401 px/s median in the upload's pixels.
2. **The content jumps.** Beyond the regular doubling (59.94 over 29.97), the scene moves in jumps every few unique
   frames, so most 2-frame pairs fall inside a hold. `layers --k 2` left `slew` 20-23 samples (it needs 30). `--k 8
   --max-shift 25` (a 200-px search over 4 unique frames, about one jump cycle) is the run in `nar3/`.
3. **The pointer is mislocated at 4-6 s** (over bright ground: radius 315 +- 19 px); from 7 s it holds (310.5 +- 0.3).

**The result: NO POWER, a floor c >= 1087 px/deg**, which the truth (2230) clears -- the stage refuses correctly, as it
did on Puerto Rico, but PR051 does not yet give k from its slew. Why: even at `--k 8`, 72 % of pairs are "held still"
and left out (in this upload a held pair is real: the content did not update), so the scene chains whole only over
5.1-8.3 s, and the pointer is clean only from 7 s. The pointer's rate does change (-0.13, +0.43, +0.24 deg/s over 7-9,
9-11.3, 11.3-14.2 s, square pixels), so there is lever once the scene chains over 7-14 s. Built for it: **`slew
--hold-rate`** (the platform's share known: here about +0.068 deg/s in the pointer's sense, from the aircraft's 70.9
m/s across the line of sight at 58.1 km, read off ACFT at 5 and 10 s -- blurry digits, good to ~10 %). Runs and logs:
`/scratch/mcdonald/pr051-2026-10-27/` (`nar/` unmasked, `nar2/` boxed at k 2, `nar3/` boxed at k 8, `nar3/held/` with
the hold given; `zoom_v04/` the zoom runs; `look/` the crops the data bar was read from).

**Tried at the end: the held pairs as real zeros** (`nar3/zeroheld/`: the 487 pairs `layers` read still over 8 frames
and could not re-measure over 60 set to 0, a scratch edit of the CSV). The scene then chains unbroken over 7-14.2 s
(421 samples). With the hold fitted: no registration, a floor of 270. With `--hold-rate 0.068`: **c 549 px/deg
(16-84 % 183-538), refused** -- forward and reverse 71 % apart, the bootstrap +-32 % -- against the truth 2230; and the
pointer's rate and the scene's *anti*-correlate (r -0.52, best at +6 frames). So the pointer and the picture do not move
together frame by frame in this edit of the footage: whether the upload's frames were re-timed (its slowed passages
elsewhere), the overlay drawn on a cadence of its own, or the jumps sit in the picture alone, is the first thing to look
at -- the pointer's own steps against the picture's jumps, frame by frame. No false claim was made at any point.

**Next for PR051's k**: a sequence of the upload's content changes alone (drop every frame whose picture, the overlay
masked, is within noise of the one before), each frame timed at its first appearance; `symbology` and `layers --k 1`
on it, the CSVs' `t_s` from that timing; then `slew --window 7:14.2 --hold-rate 0.068 --pixel-aspect 1.3333` and
without the hold. The ACFT position should be read more carefully (every second over 5-14 s) for the hold.

## The pointer sweep

`tools/pointer_sweep.py` over the 127 sensor clips of the uap repository's `analysis/corpus/pointer_sweep/clips.csv`
(list at `/scratch/mcdonald/pointer-sweep-2026-10-27/list.tsv`: zoom on every clip, slew on the 17 whose pointer and
scene chains exist under `/hugespace/local/tmp/slew/`). A first pass with main's code was stopped at 56 clips when the
float64 bug turned up (its results are in `out/`, made with the bug). **Re-run with the v04 code** (job 12274, all 127
clips, `out_v04/`, `summary.md` and `summary.json` there; `python3 tools/pointer_sweep.py collect <out>` remakes them):

- **573 bursts: 95 measured steps, 56 no step, 422 unknown.** All 95 steps are at blank bursts; no step of the picture
  with no blank was measured anywhere in PURSUE (they come out no step or not measured).
- **The ladder: the MTS-B steps by x2 and by x5.9.** Folded so a zoom in and out count alike: x2.003 (45 steps, 1.87-2.06),
  x5.89 (18, 5.76-6.32), x2.33 (9, 2.19-2.36), x3.13 (3), x7.5 (2), and a scatter of ones and twos between x1.09 and x1.76
  that should be looked at before anything is said of them. PR051's data bar says why x2: its 2X and 4X are electronic,
  and NAR -> ULTN is x2.00 too.
- **slew's claims, by state:** PR27 267 +- 3 -> 517 +- 50 across x2.003 (c x1.932, agree), PR057a 276 +- 18 -> 584 +- 26
  across x2.001 (x2.119, agree), PR134 205 +- 11, PR101 141 +- 17. PR076's claim of the first pass (no rate correlation)
  is refused now. PR101 was "not trusted" in the uap sweep note (2.6 scatters, rates at r 0.51-0.55): look at its window
  before quoting it.
- Not yet written into the uap repository's `analysis/corpus/pointer_sweep/README.md` (pass 5): that repository had
  another session's uncommitted work in it at the end of this one, and was left alone.

## What went wrong, so it is not done again

- **Editing the main checkout under running Slurm jobs.** The sweep's array tasks and the PR051 job import
  `/hugespace/models/mcdonald/src` at each start; a half-written `zoom.py` (a constant not yet defined) sat there for a
  minute. Work moved to the worktree and main was restored at once; no task was seen to fail of it (PR40's crash was a
  real `slews` bug). Develop in a worktree whenever jobs run from a checkout.
- **A forkserver pool needs the main guard** in a scratch script (the PR144 check failed once for it), as the memory
  says.
- **Test scenes that are wrong, not the code**: a view that jumped 600 px at the zoom; a star on the object; an
  expectation of 0.22 for BT.709's 128 (it is 0.26). Each time the test was fixed, not the code -- check which.

## Open, in the order I would take them

1. PR051's k from its slew: the content-change sequence above; if it registers, a golden check (`tests/test_golden.py`:
   the NAR window's c against 2230 +- 10 %). PR051's zoom answer (x0.498 against x1/1.999) wants a golden check now:
   `zoom.measure` on the .mov, the step at frames 1331-1341.
2. Write the sweep's pass 5 into the uap repository's `analysis/corpus/pointer_sweep/README.md` (above; the numbers are
   in `out_v04/summary.md`), look at the scatter of small ratios (x1.09-1.76) and at PR101's claim, and put a field on
   every clip that zooms to or from the x2 / x5.9 ladder's states from PR27's wide 267 px/deg.
3. The released-track null on PR051 (ROADMAP row): the breaklock at the released copy's frames 4601-4605 (the leak's
   ~1150-1205); the camera's rate before needs the scene registered while the gate tracked (the leak, masked as above).
4. The new bounds on real clips: `horizon` (a sea horizon, a known height and a surface target at a known range -- PR149's
   ship if its altitude can be had), `focus` and `haze` (a daytime EO clip with a known range: AARO's resolved cases),
   `streak` on PR43 (its track from `/models/data/mcdonald/cases/pr43.mcdonald`).
5. Then the session plan's 1, 2, 4: layers' per-template error (K9), the unknowns ledger on every report (objective 6),
   the speed band (K1, K8).
6. Not done: the defocus disc's flat-topped profile as the near-thing test (`focus` says so); `zoom` seeing FLIR1's
   no-blank zoom (its sky steps nothing; `camera` covers it).
