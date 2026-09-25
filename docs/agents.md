# Doing the whole job from the command line, with no window

For an agent: something that reads text and JSON, can open an image file, and
cannot click. Everything the marking window does has a command, and this is
the job done with commands only, on the clip the package's own tests use for
it — DOW-UAP-PR113, where two marks reproduce the published 142 px/frame.
Every command and number below was run on 2026-09-20 with `mcdonald` 0.2.0.

First, `mcdonald setup --json`: whether ffmpeg, the storage folder, the catalog and the
download route are there (`ready` true), and for each that is not, what would fix it.

Read `docs/method.md` for what the measurements mean and how each one fails.
This page is about driving the tools, and about one thing that is yours to
get right: **which judgments are yours, and how they are recorded.**

## The judgment that is yours

The package's founding claim is that no detector can say which thing in the
frame is the object, and someone looking can. When a person clicks the object,
that is a hand mark. When you place the mark, *you* made that judgment, and the
files say so: a mark placed with `--set` is recorded as `agent: <your reason>`
(`MarkSet.how`), it is never counted as a hand mark (`by_hand()` excludes it),
and that travels into the marks CSV, the automatic track's header, and the top
of any case report built on it — "Which thing is the object was decided by an
agent, not by a person looking at the frames."

That is not a penalty; it is the record. Three things follow from it.

- **Say why.** `--why` is recorded with every mark you set. "candidate 1 of 6
  at 21 px dark on 408; the only compact dark source that moves against the
  graticule" is a reason someone can check. No `--why` leaves a record that
  says only that an agent did it, and the command tells you so.
- **A mark copied from the detector cannot check the detector.** If you set a
  mark at a candidate's coordinates, the link will report that "the track
  passes within 0.0 pixels of all 2 marks". That is circular: the mark *is* the detector's
  position. It still does the mark's real work — it says *which* candidate,
  and a pair gives the velocity — but the residuals carry no information. A
  position you read off the enlarged view yourself is independent; say in
  `--why` which you did.
- **`concerns: []` is not a verdict.** A link with no concerns is one the
  numbers found nothing wrong with. Whether the marks were on the object is
  the one thing nothing here can know, which is why `needs` always asks for a
  look at the track strip. Look at it (it is a PNG), and if you cannot tell,
  say that rather than proceeding.

## 1. See the clip

```bash
# record ids such as PR113 are looked up in the PURSUE list the package carries; a video
# not on this computer yet is downloaded first (progress on stderr). A path always works.
mcdonald look PR113 --out cases/pr113 --json
```

Writes `pr113_look_overview_1_5291.png`: 40 evenly spaced frames of the whole
clip, each labelled `frame N   t s`. It does **not** extract the clip (one pass
of ffmpeg, selecting frames by number; about 11 s for this 5291-frame 1080p
clip). `results.frames_shown` lists them. Narrow it with `--n0/--n1`, as many
times as it takes:

```bash
mcdonald look PR113 --n0 380 --n1 440 --tiles 40 --out cases/pr113 --json
```

An object of 25 px in a 1920 px frame is 5 px in an overview tile. The overview
is for finding *when*; the next step is for finding *where*.

### Or ask what moves

```bash
mcdonald look PR149 --n0 1 --n1 120 --propose --out cases/pr149 --json
```

extracts those frames, looks for what moves against the background
(`mcdonald.propose`: the window's Track → Find the object), and writes
`…_look_proposals_1_120.png` — a row for each thing, best first, with a strip of
the clip's own pixels along it. `results.proposals[]` has each as fields:
`rank`, `strength` (`strong`, `fair`, `weak`), `score`, `says`, `frames`,
`dark`, `size_px`, `velocity_px_per_frame`, `against_background_px_per_frame`,
`going_the_same_way` (other things moving likewise at the same time: a layer,
terrain under a pan, a heading tape), `background_all_round` (0 to 1: how much
of the way round it the frame shows background — a compact thing is 0.3 to
0.9, the edge of a redaction block or a stroke of a scrolling symbol near 0),
`track`, `mark_at` and `to_accept`, the `mcdonald mark --set …` command that takes
it; `points`, how many compact points it holds (2 or more: a group, whose marks
would follow the middle of it — ask `mcdonald groups` once it is linked, below);
and `scrolling_tape`, true for one of a row of marks that slide across the
screen together, the numbers of a heading or altitude tape. On PR149 the first
is the contact, `strong`; the rest are the ship's masts, `weak`. The list is the
best few; `--more` lists everything that was kept, up to 30, eight rows to a
sheet (`…_2.png` and on). Where every row says `weak` — PR113, a four-frame transit — the order is
little evidence: look at all of the strips, and give a range with a second or
two either side of the object and not much more.

It proposes; it does not decide. **Open the sheet.** If one of the rows is the
object, run its `to_accept` with the `--why` finished in your own words — what
you saw in the strip that makes it the object. The marks are then yours
(`agent:`), as any `--set` mark is: you looked and said yes. If none is, say so
and go on to the next section. A `weak` first row is a reason to look harder,
not to accept: on PR113 the weak rows above the real transit are a scrolling
heading tape and terrain under a pan.

## 2. Ask the detector about a frame

```bash
mcdonald look PR113 --frame 408 --size 21 --dark --out cases/pr113 --json
```

Writes the frame at its own size with the candidates ringed and numbered
(`…_look_f00408_21px_dark.png` — a position in that file is a position in the
clip), and a sheet with every candidate enlarged and captioned
(`…_candidates.png`), which is the one to open. As numbers:

```json
"results": {
 "frame": 408, "t_s": 13.5667,
 "detector": {"size_px": 21.0, "dark": true, "min_resp": 5.0, "static_masks_from_frames": [378, 438]},
 "candidates": [
  {"rank": 1, "x": 1010.88, "y": 313.01, "response": 43.7},
  {"rank": 2, "x": 966.4,  "y": 364.05, "response": 39.2}, ...]
}
```

Each candidate also has `tpl_box`, a box round it for `mcdonald symbology --method
template --tpl-box` (if it is the north pointer's glyph), and `stays_put_on_screen`:
it is on one of `sensor_defects.defects`, the places where a spot holds still
on the screen while the scene moves — a hot pixel of the sensor, symbology the
masks missed, or an object the sensor follows to within a pixel (PR135's
tracking segment has 62). Where the scene holds still they are not looked for,
since the scene's own points would hold still too (`scene_moved`). A row of
candidates across the frame is offered as `caption_rows`: a burned-in caption,
for `--mask-rows`.

On this frame #1 is a compact dark blob and #2 is a graticule tick. **Rank is
the detector's response, not likelihood of being the object** — in the test
clip the strongest candidate is a decoy that never moves. The detector is tuned
to one size and misses an object much larger or smaller outright (at the 9 px
default PR113's object is 71 px from the nearest candidate): try `--size` 5, 9,
15, 21, 31, 45, with and without `--dark`. Compare frames: the object is the
candidate that *moves* in a way the symbology and the scene do not.

The static masks (burned-in symbology, redaction blocks) are built from the
frames `--n0..--n1`, by default 30 either side of `--frame`; those frames are
extracted losslessly once (the command says what that costs first).

**Where the frames go.** Every command keeps a clip's frames in
`$MCDONALD_HOME/frames/<video stem>/` (`~/Documents/mcdonald` when
`MCDONALD_HOME` is not set; downloaded videos go beside them in `videos/`), or in
`--workdir DIR` if given, and reuses them: a second command, or a second batch
job, on the same frames extracts nothing. A lossless 1080p frame is most of a
megabyte, so a whole clip is a gigabyte or more. For batch jobs, set
`MCDONALD_HOME` (or `--workdir`) to a directory on disk that every job can see,
the same one for every job on a clip, and remove the frames when the work is
done. The cost line says where the frames will go and whether that directory
is in memory.

To read a position yourself, or to check one:

```bash
mcdonald look PR113 --frame 411 --at 702,604 --size 21 --dark --out cases/pr113
```

`…_at_702_604.png` is 96 px about that place, enlarged six times without
interpolation, with a scale in the clip's coordinates along its top and left
edges and a cross at the place asked about. Pixel centres are at integers: the
block drawn for pixel (x, y) is centred on (x, y).

## 3. Place marks, and link

```bash
mcdonald mark PR113 --n0 400 --n1 420 --no-window --link --json --out cases/pr113 \
    --set object@408=1010.9,313.0 --set object@411=702.4,604.2 \
    --why "candidate 1 of 6 at 21 px dark on 408, and the matching dark source on 411: the only compact dark source that moves against the graticule"
```

They are recorded as an agent's. If you are a person who read the positions off
`look`, add `--typed`: they are then recorded as typed by a person, and a report
built on them says a person decided, and how.

One mark is a seed; a second gives the velocity, which an object this fast
cannot be linked without. Marks accumulate in `<tag>_marks.json` across calls
(`--unset object@408` removes one), so marks with different reasons are
different calls. Classes: `object`, `object2`, `boresight`, `north`,
`reference`, `horizon`. `--n0/--n1` is the range the link searches, back from
the first mark and on from the last; without them it is 30 frames either side
of the marks, and the command says so.

It writes what the window's save writes — `_marks.json`, `_marks.csv`,
`_marks.png` (the contact strip: every mark drawn back onto the pixels, which
is how a coordinate gets checked rather than trusted) — and with `--link`,
`_autotrack.csv` and `_autotrack_strip.png`. What came back here:

```json
"results": {
 "speed_px_per_frame": 141.41, "velocity_px_per_frame": [-102.833, 97.067],
 "marks": {"object": {"408": {"x": 1010.9, "y": 313.0, "placed_by": "agent", "how": "agent: candidate 1 of 6 …"}, …}},
 "link": {"object": {
   "frames_linked": 4, "first": 408, "last": 411,
   "detector": {"size_px": 21.0, "dark": true, "min_resp": 5.0, "object_response_at_marks": 31.7,
                "like": 0.5, "floor": 15.9},
   "px_from_each_mark": {"408": 0.03, "411": 0.04},
   "px_at_which_the_link_from_the_mark_before_arrives": {"411": 0.04},
   "disputed_frames": [], "lost_after": null, "lost_going_back_from": null,
   "searched": [400, 420], "stopped": false,
   "summary": "4 of 4 frames linked, 408–411, looking for dark spots 21 pixels wide; …",
   "concerns": []}}
},
"needs": ["a look at cases/pr113/pr113_autotrack_strip.png: nothing here can know whether the marks were on the object, …"],
"notes": ["2 of 2 marks were placed by an agent, not by a person looking at the frame. …"]
```

141.4 px/frame against the published 142. (The 0.03 px residuals are the
circular case above: these two marks were the detector's own positions.)

The link is given the detector's 25 strongest spots a frame, and between two
marks the weaker ones within 10 px of the line between them too; it takes only
spots answering at least half as strongly as the object does at the weakest of
its marks (`floor`). The spot size is chosen from the marks: the size whose spot
sits nearest them, climbing while a larger one is nearer or answers more strongly
at them (a matched filter answers most at the object's own size, which a mark a
few pixels off its centre does not stop).

`concerns` is what the summary says in prose, as sentences you can test for:
a mark with no link under it, the track more than 6 px from a mark, a forward
link that does not arrive at the next mark, frames where the forward and
backward links disagree, gaps, a link that was stopped -- and where the frames it
disagrees on pass over burned-in symbology, a redaction block or a defect of the
sensor, it says that too (PR135's disputed 213-225 were the group crossing the
north pointer's "N"). Any of them means look before going on. After a loss, mark the object where it reappears and run the
command again.

## 4. Measure

Every measuring command takes the marks file, and links from it first:

```bash
mcdonald run PR113 --marks cases/pr113/pr113_marks.json --n0 400 --n1 420 --out cases/pr113 --json
mcdonald layers PR113 --marks cases/pr113/pr113_marks.json --n0 400 --n1 420 --out cases/pr113 --json
```

`run` writes `<tag>_case.md` and `_case.json`, and with `--json` prints the case
in the envelope: `results.bottom_line`, `results.stages` (the lines the report
prints), `results.fields` (each stage's findings as numbers),
`results.identified_by`, and — never dropped — `no_power` (what this clip
cannot decide, as `[test, why]`) and `needs` (what would close the gap). A test
that had no power has not passed. `run` makes a track sheet and marks the
object stages provisional until someone asserts `--i-looked`; do not pass it
unless you opened the sheet. Opened later, the case need not be measured again:

```bash
mcdonald report cases/pr113/pr113_case.json --i-looked
```

reads the case back from its file, records the sheet as looked at, and writes
the report again; `mcdonald report CASE.json` alone writes it again as it was.
The report shows the pictures each step drew under it (the track sheet, the
strips, the layers figure), as links a Markdown viewer follows.

`run` also reads the overlay (`symbology`: the boresight, the north pointer's
angle and how it turns, the corner brackets). A pointer drawn in white or grey
is found by its shape, which needs a box round it: where it finds none by colour
it says so in `no_power` after 20 frames, and `fields.symbology.glyphs_to_try`
lists the glyphs a template follows at a fixed radius from the boresight, each
with the `--tpl-box` for `mcdonald symbology --method template`. Which one is
north is yours to say (`look --frame N --size 5` rings them); on PR135 the "N"
and a hot pixel are listed.

With a track, `run`'s layers stage is the whole `layers` measurement — the
object against each background layer, about a second per frame pair — so allow
minutes, or `--skip layers,integrity` for a quick pass. Tell it what the layers
are (`--names "striated=sea,isotropic=cloud tops"`) if you know; the bottom line
names them. Linked from marks, the stages that look at the object's pixels (the
sheet, integrity) are told the size and polarity the marks chose; with `--track`
say `--size` and `--dark` yourself if the object is not a bright 9 px source.

### How much of a ground speed is the aircraft's?

A speed given for the object along the ground -- a report's "480 mph" -- may be
mostly the aircraft's own motion, seen through an object nearer than the ground.
With the aircraft's speed, `kinematics` (and `run`) give the ladder:

```bash
mcdonald kinematics PR135 --track cases/pr135/pr135_autotrack.csv \
    --ground-speed 480mph,265 --own-ship 150kias@15000ft,85 --json
```

`fields.parallax.rows`: for each speed the object might have of its own (0, 5,
10 … 100 m/s), the `k` = h_A / (h_A - h_O) that give the ground speed, and
`h_ratio` = h_O / h_A (in metres with the aircraft's height). With the aircraft's
heading and the ground motion's bearing each row is one or two k; without them,
the range every direction allows. A still object has to move along the ground
exactly against the heading; `stationary_off_deg` is how far it is from that, and
the still row's `closest` the speed of its own it would still need. An indicated
airspeed (`kias@height`) is turned into true airspeed in the standard atmosphere,
with the band a day 15 C colder or warmer gives. Neither number is in the video:
without them it is a `no_power` entry that names which is missing.

### Is it several points?

A linked track is one position a frame. If what you marked is a group -- a
cluster of points, "6X small objects grouped together" -- ask:

```bash
mcdonald groups PR135 --track cases/pr135/pr135_autotrack.csv --out cases/pr135 --json
```

It looks for points within `--radius` (120 px) of the track on every frame,
leaves out what stays put on the sensor and what moves with the background
rather than the track, follows each member, and holds every pair's separation
against the members' own position noise: `rigid` true is a formation that keeps
its places, false is members that change places (as a flock does). On PR135
1240-1401 it follows six members, each within 0.3 px of the agent's own
hand-checked tracks, and says false. `run` asks it of every track linked as a
spot of 9 px or less; a larger thing has a rim of its own and is not asked.
It cannot say what the members are.

### Does it flicker?

```bash
mcdonald flicker PR135 --members cases/pr135/pr135_members.csv --out cases/pr135 --json
mcdonald flicker PR144 --track cases/pr144/pr144_autotrack.csv --out cases/pr144 --json
```

Each member's (or the object's) brightness, frame by frame, in an aperture that
does not beat by itself as the object moves a fraction of a pixel a frame, and
its strongest beat. It is held against three things that fake one: apertures of
background beside the object (a beat must be 3 times theirs, and not shared by
them), the codec's own rhythm (`codec.lines_hz`, read from the clip's frame
types: PR135 has an anchor every 4th frame, 7.49 Hz), and, with members, whether
they beat as one (a rhythm of the video does; members at different frequencies,
or out of step, over the same frames, do not). `beats` true is a beat that is
the object's own; it does not say what makes it (wings, tumbling, a blinking
light). It needs 60 frames in common. `run` measures it on the members `groups`
found, or on the object.

## The envelope

Every command takes `--json` and prints one object, alone on stdout;
everything written for a person goes to stderr. That includes progress: a long
step is a line, `[   42 s] step 5 of 9 · layers: comparing pairs of frames`, and where
stderr is not a terminal its count follows every ten seconds (`57 of 196, about
3:40 left`). A stage that is minutes long is not hung while that count moves.

| field | |
|---|---|
| `command`, `mcdonald` | which command, which version |
| `inputs` | the options it ran with |
| `clip` | `video`, `width`, `height`, `fps`, `fps_exact` (the rational; never round it), `n0`, `n1`, `duration_s`, `encoding`: `codec`, `profile`, `pix_fmt`, `reorder_depth` (B frames), `bit_rate`, `container`, and `gop` from the first 150 frames' types -- `types`, `i_period`, `anchor_period`, `lines_hz` (where the codec's rhythm beats: a brightness or a step at one of them may be the codec's) |
| `files` | what it wrote |
| `results` | what it found; per command |
| `no_power` | `[test, why]`: what this clip cannot decide |
| `needs` | what would close the gap |
| `notes` | things worth knowing that are not results |
| `exit`, `error` | the exit code, and the sentence that went with it |

Every command has its results as fields: numbers, with the unit in the name
(`v_px_per_s`, `median` under `px_per_s`), never a sentence to be parsed. What
the command printed for a person is beside them as `results.said`, line by
line, and it is written *from* the fields, so the two cannot disagree. Each
measuring command is a command line over one function (`layers.measure`,
`integrity.examine`, `tracksheet.sheet`, `symbology.measure`,
`comotion.measure`, `stages.kinematics`), and `run` calls the same functions:
`results.fields.kinematics.v_px_per_s` from `run` and `results.v_px_per_s` from
`kinematics` are the same number to the last digit, and `tests/test_cli.py`
holds them to it.

| command | `results` |
|---|---|
| `layers` | `px_per_s.{striated,isotropic,all}` each `{median, p16, p84, min, max, windows}` (one-second windows); `tracked` says whether those are the object's rate against the layer or the layer's own screen speed; `layer_against_layer`; `object_over_parallax.{ratio, directions_apart_deg}`; `motion_groups`; `names` |
| `kinematics` | `v_px_per_s`, `direction_deg`, `uniform` (false: do not quote `v_px_per_s`), `fit`, `omega_rad_per_s`, `relative_speed_m_per_s`, `lower_bound_m_per_s`, `body_lengths_per_s` (the body's own length only if the object is resolved: for a point, `--size-px` is its blur), `resolution` (in `run` and the window, where there are frames and a `--size-px`: `blur_fwhm_px`, how wide a point is drawn, from the clip's sharpest `spots`; `object_fwhm_px`; `resolved`, the object over 1.5 times the blur -- false puts the speed in body lengths in NO POWER, null means not measured: fewer than 8 spots, as on a clip of plain sea or sky; `mcdonald kinematics` has no frames and gives none), `scale_bar_m_per_s`, `missing` |
| `flicker` | `codec.{types, i_period, anchor_period, b_frames, lines_hz, i_hz}`, `frames`, `first`, `last`, `resolution_hz`, `noise_floor` (the background apertures' own beat, in the object's brightness), `curves.{name: {hz, amplitude, stands, half_power_hz, resolution_hz, at_the_codec_line_hz}}` for each track and background aperture, `pairs[]` (members: `hz`, `apart_hz`, `phase_deg`, `independent`), `beats` (true: the object's own; false: nothing past the background; null: shared, in step, or at the codec's rhythm with nothing to tell them apart), `finding` |
| `groups` | `points_per_frame.{median, min, max}` (moving with the track), `several` (false: one thing, or nothing point-like), `members_followed`, `on_the_sensor`, `track_against_background_px` and `scene_told_apart` (under 20 px, points of the scene cannot be told from members, and all are counted), `noise_px`, `pairs[]` each with `separation_px`, `separation_range_px`, `wander_px` (about a straight line in time) and `wander_over_noise`, `rigid` (true: every pair within 2 times the noise; false: the median pair over 3 times and 1 px; null: neither, or too few), `finding`; in `run`, `skipped_because_size_px` for a thing larger than a point |
| `comotion` | `verdict`, `finding`, `pairs`, `whole.{rel_D, rel_D_per_s, obj_D, flow_D, dt, …}`, `legs`, `sweep`, `flow_near_zero_zone` |
| `symbology` | `boresight.{x, y, how}`, `method`, `trial` (a method chosen by `auto` is tried on 20 frames first: `{frames, solved}`, and none solved ends it there), `frames_solved`, `radius`, `radius_is_fixed` (false: the angles are unreliable), `position_step_px` and `theta_step_deg` (hue places the glyph to half a pixel; the template, whose peak is placed between pixels by a parabola, and chroma, a centroid, have no step: null -- unless `drawn_at_whole_pixels`, the template finding the glyph on whole pixels in 90 % of frames, as PR135's "N" is: then the step is the video's, 1 px), `theta_deg_per_px_of_boresight` (theta is only as good as the boresight), `rotation[]` each with `dtheta_dt`, `dtheta_dt_se` (the fit's standard error), `resolvable_deg_per_s` (the larger of one step over the window and twice `dtheta_dt_se`: a slower rotation is not seen), `resolvable_by` (`one step` or `scatter`) and `sense`, `corner_brackets` |
| `tracksheet` | `frames`, `detected`, `interpolated`, `outside_every_track`, `contrast_dn.{median, minimum}`, `weak_frames` (a tracked position with no source under it) |
| `integrity` | the whole of `_integrity_report.json`: `record`, `container`, `scene`, `object.{test}.{verdict, finding, …}`, `selftest`, and `object_described_as.{size_px, dark}` |
| `run` | `bottom_line`, `identified_by`, `stages` (the report's lines), `fields` (each stage's fields, as above) |

A stage that could not decide is in `no_power`, not missing: `layers` on a
window shorter than a second has `px_per_s` all null *and* says so there.
`comotion` with no usable pair and `symbology` with no pointer found exit 5.

## Exit codes

| | |
|---|---|
| 0 | done |
| 1 | a bug: a Python traceback, which should be reported, not worked round |
| 2 | the command line was wrong: an unknown command or option, a `--set` that cannot be read or is not on the clip |
| 3 | this machine lacks something: ffmpeg, or a window to open |
| 4 | the input is not there, is not a video, or is a record id that resolves to none or several |
| 5 | nothing to work on: no marks, no object marked for `--link`, or the link acquired nothing |

With `--json` the envelope is printed for 2–5 as well, with `exit` and `error`
set. After a 5 from `--link` the marks are still saved; `no_power` holds what
the linker said.

## What a person can do that you cannot, and the other way about

Nothing, by design: a thing the window can do and the command line cannot is a
bug, and the reverse. The window's overview, candidates and loupe are `look`;
its Find the object is `look --propose`;
its click is `--set`; its `l` is `--link`; its `s` is what `--no-window`
writes; File → Open marks is `--load`; its Measure menu is `run`, the form in
it is `run`'s options (both are made from `stages.KNOWN`), and the question it
asks under the track sheet is `--i-looked`. If a person opens a marks file you
wrote, the window shows each of your marks as `agent`, with your reason.
