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
macOS and Gary Nolan on Windows, once he says the polish is done. The next
session starts from "Next". He has used the window end to end on PR144 (a part opened, Find, This is
it, link, Measure, a report), said the player "has a nice feel", and confirmed
PR113. He also set up Slurm on this machine on 2026-09-21, and the heavy checks
now go through it (`tools/*.sbatch`). Everything below was checked on this
machine unless it says otherwise.
`docs/handoff-gui.md` is the record of how the window got here; this is the
brief for what comes next.

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

0. **The agent's report (PR135), by the triage at the top.** 4, 9, 5, 2, 12,
   17, 18 and 14 (a) done on 2026-09-23 morning; the sub-pixel peak, 14 (b),
   groups (3) and flicker (21, 24) that afternoon. Left, in the order I would do
   it: whether `propose`'s registration has the same trap as `layers` had; `propose`
   saying a proposal holds several points (8); a per-clip defect map (22);
   `gop` in every envelope (23); the agent's conveniences 7, 10, 11, 20;
   `symbology --method auto` run on PR135 itself, to see the trial end it;
   PR148's pointer through the new template peak. The parallax ladder (1, 15)
   is Jacob's to choose: its inputs are not in the video.
0a. **Before Ravi (macOS) and Gary Nolan (Windows).** Jacob wants more polish
   first, and will say when. For Windows, beyond the Mac list (2): paths with
   backslashes and drive letters in `_flags` and the case folder, the pools'
   `spawn` (already chosen on win32 in `autolink._Workers`), ffmpeg on the
   PATH, `gui.desktop_entry`, and `TMPDIR` -- a long one broke the pools here
   on 2026-09-23 ("AF_UNIX path too long"), which Windows does not have but a
   deep `%TEMP%` may do something like.
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
1a. ~~Have Jacob try Find on PR113 again.~~ **He did, the same day: "Great, it
   works now!"** Which part he had open the first time was never said, so which
   of the two fixes was his case is not known; both stay.
1c. ~~**Jacob's hand on PR055 again.**~~ *Done 2026-09-22*: Find was right and
   the link ran onto cloud, which the section at the top fixes. **He opened his
   saved `pr055` again after `f77b85b` and linked: "Great, the linking for
   PR055 works now!"** Where a link stops when the thing has faded (8 frames
   past an end mark) is the code's answer; he has seen it on PR055.
1d. ~~**For Jacob: the detector's 25 spots a frame**~~ — *done 2026-09-23*: the
   edge bug fixed, and between marks the link looks near their path (the first
   section; PR148 links). *Before that, decided 2026-09-22: 25 stays*
   (Decisions: every spot was tried and was worse). What is left of
   it: **PR148's object is a faint speck among thousands in sea texture**, and
   nothing in the link tells it from them but position. A cue of likeness —
   the object's own strength and size at the marks — is the next idea, and would
   have to be held against PR055, whose fading disc answers like cloud. And
   PR149's crossing is not the 25 either: on 44–58 no spot is near the contact.
   **The edge bug (Decisions) goes with it**: fix the two together, since the
   link leans on the bug's short lists. My recommendation: for a link from marks, look near where the
   object should be, not at the frame's 25 strongest spots; the blind tracker
   unchanged. Then PR148 would link at all, and PR149's crossing and PR055's
   fading would fill in where the object can be seen. Measure it with
   `tools/find_rank.py --replay` against the table above, plus `test_golden`.
1b. **The proposer's limits, in the order I would attack them.** *(ii) is done
   — the table is at the top, and `tools/find_rank.py` repeats it — and (iii)
   is half done: PR055 at its true size is found (`thing_at`); the ×3 copy,
   a 72 px disc, still cancels in the k = 2 difference.* (i) Global
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
