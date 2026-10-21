# Handoff: branch `flir1` -- the frame rate of a field-rate MPEG, `camera` (and its fields of view, also from `run`), `readout`, `events` (text against a border, noise from the quiet frames), the ATFLIR's fields (and suggested readings, letters among them), `versions` (2026-10-20)

Built in one day at Jacob's request ("proceed with all work on mcDonald in a branch") after the Navy's 2004 FLIR1
was run through 0.3.2 as a test (`docs/agent-run-nimitz-flir1-2026-10-20.md`). The same day the first handoff's "Open"
list was worked through and its "Choices" tried on the PURSUE reference cases. That evening the second handoff's two
FLIR1 findings went to the uap case note, and its Open list was worked through (below). That night the third Open list
was worked through too ("The third Open list", below). Worktree `/models/mcdonald-flir1`, branch `flir1` off main at
171e0c0. **Merged to main 2026-10-21** (Jacob: "yes, merge onto main"); the branch and its worktree are removed.

## What is on the branch

| what | where | tested by |
|---|---|---|
| the frame rate: `avg_frame_rate` where `r_frame_rate` is twice it (MPEG-1/2 field-rate headers), with `fps_note` in the record, the ingest stage and the report; `audio` folds through it too | `clip.frame_rate`, `clip.probe`, `audio.probe`, `report.clip_block`, `stages` ingest | `test_camera` (an MPEG-1 drawn with ffmpeg, and its FFV1 copy); FLIR1 golden. 125 reference clips scanned: none changes |
| the frame count of a file whose header gives none: its video packets counted (not the container's duration, which sound outlasts); a window to the end that comes out shorter ends there, kept in `last_frame.json` beside the frames | `clip.frame_count`, `Clip._ended_early`, `reel` | `test_camera` (an MKV, an MPEG program stream, a count three frames long); FLIR1 ends at 2289 (was 2294 from the duration) |
| `mcdonald camera`: zoom steps from the object, applied only where its offset confirms them (or a ratio is given); the object's own size steps reported with why; the rate's steps (PELT, Schwarz) with a jump test at each break; set beside the camera's events, given or `--events auto`; the released-track null | `camera.py`, method §20; a `camera` stage of `run` after `kinematics`, its report summed up past 6 stretches | `test_camera`; FLIR1 golden |
| `mcdonald readout`: a strip to read a readout off, its ticks timed to the frame on the text's strokes, the rate, and whether holding still to the end can say the camera stopped | `readout.py`, method §21 | `test_camera`; FLIR1 golden (1 L -> 2 L at 1437.5) |
| `mcdonald events`: the overlay's text boxes and each one's changes (to the half frame, dithers counted), clocks, the strokes round the object, the picture's steps, held frames, contrast collapses | `events.py`, method §22; `camera --events auto` | `test_camera` (a drawn readout, clock, gate, gain step, held frames); FLIR1 golden |
| `symbology --method atflir`: the ATFLIR's fields (azimuth, elevation, zoom, field of view, camera) placed from its picture's box, each one's looks and changes, a sheet to read them off, and with `--read` their values and the azimuth's slew; the field's mnemonic read as a word, and with the zoom the picture's field frame by frame in `camera --fields` form; a change of the mnemonic's look flagged as a change of scale | `atflir.py`, `symbology._atflir`, method §23 | `test_camera` (a drawn display, its mnemonic and zoom changing); goldens: FLIR1's mnemonic changes, GIMBAL and GOFAST against hand-read ticks |
| `camera --fields`: the field across the picture stretch by stretch as the display gives it; each change taken out of the track like a zoom (about `--centre`), set among the camera's events, and checked on the object's size: confirms, contradicts, no power (under 1.5 blurs, `--blur`), unclear; runs of changes with no tracked frame between checked as one | `camera.field_steps`, `camera.field_at`, method §20 | `test_camera` (a zoom then a change of field at the blur; a field the picture did not follow; changes across untracked frames); FLIR1 golden |
| suggested readings: the clip's clock's last digit, once read on one frame, as ten templates in the display's own font (its ticks found by folding at the clip's second); each look of each field read glyph by glyph beside the sheet, `?` where no digit matches well or a glyph is shorter than the digits | `glyphs.py`; `symbology --method atflir --clock X0,Y0,X1,Y1 --clock-at FRAME:DIGIT`; method §23 | `test_camera` (a drawn clock and readout); FLIR1 golden |
| `mcdonald versions`: copies of one clip -- detail, blocks held, held frames (the recording's, or an upload every copy shares, and each copy's), the lag and its steps, a relabelled rate, the best source; `--width` to compare at up to the smallest copy's full width | `versions.py`, method §24 | `test_camera` (two drawn copies); FLIR1 golden (the 2007 copy against DVIDS's) |
| `integrity`'s layer order on symbology drawn frame by frame (a moving gate, text held for a stretch), decided only where object and symbology are on opposite sides of the picture's level | `integrity._overlay_drawn`, `forensics.ridges/strokes/overlay_level`, method §25 | `test_measurement` (five drawn cases); FLIR1's exit |
| `kinematics.fit_v_px`: `held` (span under 5 px, residual within twice the noise) is uniform | `kinematics.py`, `stages.kinematics` | `test_camera` |
| the size/speed figure and the scale stage's ladder add 0.7 deg (a targeting pod's narrow field) | `figures.FOVS`, `scale.FOV_LADDER` | `test_reduction` |
| `run --fields`, `--fov-px`: rows of `stages.KNOWN` (so the window's Measure form and `run_case` too); the camera stage takes the fields, the scale stage's k is over `--fov-px` at the fields' first field; `--fields` refused with `--fov`/`--graticule`; `--fov-px` can be given afterwards, and a field of view given afterwards now moves the camera stage's degrees (it was left in the old scale) | `stages.parse_fields`, `check_known`, `field_of`, `scale(fov_px)`, `add_known`; `camera.angular`, `in_degrees`, `rescale` | `test_camera` (a drawn case run whole; `--fov-px` and `--fov` given afterwards) |
| `events` looks for text everywhere but the dark itself and a ring round it, with the lines along the dark taken out (was: everywhere but `blocks`, the dark grown 8 px, which took in FLIR1's `NAR` and all of GIMBAL's top line); a word blurred into one band is text | `events.text_strokes`, `events._band` | `test_camera` (a drawn border, a readout under its top edge, a redaction box on a moving scene); FLIR1 golden (the mnemonic's box) |
| `events.change_score` reads each cell's noise again from its quiet frames (those more than 6 from a change found): a readout ticking every 20 frames had raised even the lower part of its distribution | `events.change_score` | GIMBAL/GOFAST goldens (`atflir`): GIMBAL 12 of 13, none false |
| letters for the suggested readings, from text a person has read once (`--letters BOX=TEXT`, and the words given in `--read` for the field of view and the camera); a word the blur joined cut at the display's pitch; each field read by the ATFLIR's grammar (the azimuth's digits, then L or R); joined glyphs cut at the pitch when read; a far fainter slot is no glyph | `glyphs.letter_templates`, `pitch_cut`, `with_letters`, `read(among, last, unit_width)`; `atflir.GRAMMAR`, `parse_letters`, `measure(fixed=)` | `test_camera` (drawn `HELP`, a joined `CAFE`, a readout 37L/38L/39H); FLIR1 golden |

The FLIR1 numbers the goldens hold:
- **the frame rate:** 30000/1001;
- **the zoom:** frame 2235 (counted from 1). The size gives ×1.91, the offset ×2.08, and with ×2 given the centre
  is (178.1, 122.1);
- **a rate step at the zoom;**
- **the readout:** −0.2466 ± 0.0051 deg/s over 8 ticks (was −0.2518 ± 0.0042: see below), holding to the end, with
  the next tick due at frame 2296;
- **the fastest stretch:** 0.293 deg/s, z +1.5 with the field's 10 % (+4.3 exact; was +1.3 and +4.0);
- **events:** the azimuth's 13 ticks from the box found, 12 to the frame; the zoom readout at 2237.5; held 529-534 and
  1233-1236; the field of view's mnemonic a box, changing at 2166.5 (NAR to MFOV);
- **versions:** the 2007 copy best; DVIDS's keeps 0.65 of its detail, holds 24 % of its blocks (7 %), and repeats a
  frame at 985 and at 1986.
- **fields** (2070-2250, frames from 1): NAR x1 0.7, x2 0.35 from 2085, x1 from 2140, x2 from 2156, MFOV x2 1.5 from
  2158, WFOV 6 from 2209, NAR x1 from 2218, x2 from 2235. The three x2 zooms are confirmed (x1.79, x0.56, x1.91), the
  four changes of field are no power, and the released-track null is unchanged. `atflir` times the mnemonic's
  changes at 2166.5 and 2219.5;
- **glyphs:** the clock's last digit (box 160,218-188,231; 5 on frame 1) folds at 29.977 frames, first tick 22.6; ten
  templates; the azimuth's digit is suggested right on 10 of 11 hand-read stretches, wrong on none, `?` on 1 (was 8,
  1 and 2); with letters from `RTCL`, `OPR`, `DCLTR` and `LTD/R`, its side right on 10 of 11, `?` on 1 (a glyph trimmed
  under 0.7 of the digits' height), none wrong; through `atflir` with `NAR` read too, a side on 22 of its looks and
  never the wrong one;
- **GIMBAL / GOFAST** (1-300): picture boxes about 963 px square, all five fields placed; GIMBAL's azimuth 12 of 13
  ticks within 2 frames and none where no tick is (was 9, against ticks read off a strip of every tenth frame: they
  are now the frames that hold a field of each value, read off every frame); GOFAST's 5 of 6, none where no tick is
  (one before), and its elevation 3 of 3.

## The two FLIR1 findings: carried to the uap case note (uap commit 528cc68)

1. **The 1 L -> 2 L tick**, 40 frames late on the grey, is at 1436.5 on the strokes (frames from 0 in the case note;
   1437.5 from 1). The case's own `nimitz_flir1_readouts.py` now compares strokes too. The note's slew is 0.2466 ±
   0.0051 deg/s, the fastest stretch +1.5 σ (+4.3 exact) and 19 % over the slew, and Model 4 0.92 of it.
2. **The zoom readout's 2.0 over 2158-2209 (from 1) is a change of field, not a missing zoom.** The ATFLIR has three
   fields: NAR 0.7°, MFOV 3° and WFOV 6°, with ×2 in NAR and MFOV (Metabunk's "ATFLIR FOV" thread, from Navy
   documents). The mnemonic at the top left reads `NAR` everywhere but 2165-2218 (from 0), where it is a four-letter
   one: Mick West read it as MFOV, then WFOV. The picture's own changes, timed on the sky's noise (1.2 → 2.6 DN at
   2157), the gate's width and the object's size, lead the symbology by 1-3 frames:
   - NAR ×2 at 2155;
   - **MFOV ×2 (1.5°) from 2157**, the label at 2165 after four broken or dark frames;
   - **WFOV (6°) from 2208**, after one transient frame at 2207: the gate's bars go 10 → 5 px apart, and the zoom
     readout shows 1.0 at 2209;
   - **NAR ×1 from 2217**, the label at 2219;
   - NAR ×2 at 2234.

   In angle the object holds at 0.020-0.023° on every NAR stretch. Its 4.4 px at MFOV ×2 are ≤ 0.027°, at the blur.
   So the note's (e) ("grows from 0.013° to 0.020° at the release") is withdrawn: the 0.013° was MFOV read at NAR's
   scale. **The track is lost at the switch back to NAR (2217), not at 2207.** The object comes back 8.6 px (0.025°,
   one WFOV pixel) off the boresight, and the new gate grows round the boresight. Metabunk posters said so (Spindle,
   Agent K). The exit's rates are unchanged; the case's `exit_fit.py` now uses each frame's field. The new case
   tool is `nimitz_flir1_fov.py`, with output in `fov_steps.json`.

   `atflir` had timed the mnemonic's two changes (2167, 2220 from 1) the first time it ran. Nobody read that line of
   its sheet.

## Choices tried on the PURSUE reference cases (2026-10-20)

`mcdonald camera` on 22 objects of the 14 reference case files, each on its own track as `run` calls the stage (Slurm
8186, then 8220 after the fixes), and `share rerun --strict` on PR113, PR149, PR144, PR43 and PR41 (8272):

- **Zoom steps.** Before the fixes, five of PR135's six birds, PR077, PR097's object 3 and PR43's streak "zoomed", and
  the false zooms were taken out of the tracks (one stretch: 386 ± 183 px/s). Now a step's sides must hold frame by
  frame and only a confirmed step is applied: none of the 22 is, nine are reported as the objects' own size steps (none
  about the frame's centre, none with a jump), and FLIR1's still is. **Recommendation: keep.**
- **The rate steps.** 4-42 stretches an object; a panning camera's smooth rate is cut into many, and with no camera
  event known none of them means anything by itself. `run`'s report now sums them up past 6 (each is in the CSV) and
  says no event was known. **Recommendation: keep `camera` in `run`** -- it is cheap (it reads the frames once), it is
  where a zoom inside a track is caught, and its size steps flag a blob that takes in its neighbours (PR135) -- but it
  is Jacob's call; dropping it is one line in `stages.STAGES`.
- **`share rerun --strict` now differs by additions only**: the camera stage; `kinematics`' `held` and `noise_px`; the
  ladder's 0.7 deg row; and, where a track is under 8 frames (PR113), a camera "no power" that raises the bottom line's
  count by one. No number of theirs changes. The reference case files will need making again after the merge, or
  strict reruns told to allow additions (Jacob's call). PR41 (a bird, 54 min) the same: its beat unchanged. (Those
  reruns saw integrity's no-crossing line reworded; it is back to its old words since.)
- **The noise floor (0.25 px), the 4-frame stretch, EVENT_NEAR 3, ZOOM_MIN 1.35, OUTLIER_MAX 0.30, JUMP_SIGMA 5** are
  judgments, set on FLIR1, the synthetic scenes and the reference cases above.
- **`--scale-err` 10 % for an assumed field.** On FLIR1 it decides the verdict (+1.5 σ with it, +4.3 without); both are
  printed.
- **`events`' thresholds** (6-frame windows; 8 sigmas of each cell's noise, read from the lower part of its
  distribution; TOGETHER 3 boxes; WITH_PICTURE 2 frames) were set on FLIR1 (against its 13 hand-read ticks) and GIMBAL
  (9 of its 13 ticks in 300 frames; the whole-series median found 6). `tests/test_camera.py` holds a drawn scene. A
  PURSUE display (MTS-B) should be scored before relying on them there.

### Choices made this evening (judgments, each set on FLIR1, the drawn scenes and the clips named)

- `camera.BLUR_FLOOR` 1.5 blurs, `AGREE` 25 %, `CHANGE_MIN` x1.5, and the default blur (stroke step + 1: 4 px up to 576
  rows). On FLIR1 the NAR ×2 → MFOV ×2 change predicts a 3.6-4.3 px image, under the 6-px floor, so it is no power.
  A 1080 rendition of a standard-definition display blurs far more than 5-6 px: give `--blur` there.
- `atflir.ATFLIR_FIELDS` (NAR 0.7, MFOV 3, WFOV 6, halved at ×2) are the maker's numbers as Metabunk read them from
  Navy documents. They are not measured here, so camera's `SCALE_ERR` (10 %) applies to them.
- `glyphs`: `MIN_SCORE` 0.55, `MIN_MARGIN` 0.04, `SHORT` 0.7 of the digits' height, `CONTRAST` 1.8 (FLIR1's clock
  folds at 2.7), `RULE` 0.8 (rows lit across 80 % of a box are a border). On FLIR1, letters (`L`, `R`) still match
  digits at 0.72-0.89, inside the range true digits score. A person sees that on the sheet.
- `versions --width` defaults to 480, as before.

### Choices made tonight (judgments, each set on the clips named)

- `events.RING` 1 px at 240 rows round the dark, `RULE_GLYPHS` 3 (a line that long is a rule), a line taken out where
  half of it or more lies within the ring and two stroke steps of the dark; `_band`: a glyph high (2 % of the frame to
  1.3 glyphs), two glyphs wide, filling 0.6 of its own box and 0.8 of the box's strokes. Set on FLIR1, GIMBAL and
  GOFAST, and checked on PR27 and PR144 (the same boxes as before). Taking the lines out everywhere, not only along the
  dark, made six false boxes on PR27, so it is not done.
- `change_score`: one pass more from the quiet frames, more than `WIN` from a change found; a third pass found a change
  where none is on GIMBAL.
- `glyphs.FAINT` 0.4, `SHALLOW` 0.8 (a pitch cut follows only a real dip), and `atflir.GRAMMAR`. The grammar is
  ATFLIR's; a display without one in `atflir` gets digits and letters matched as one set, which FLIR1 shows is poor
  (its digits right fell from 8 to 1), so `glyphs.read`'s `among`/`last` are the way to say another display's.

## The second Open list, worked through (2026-10-20 evening)

- **Whether FLIR1's picture zoomed at 2158: settled.** The pod changed field (above). The gate test the handoff
  proposed works where the gate is redrawn (×2 at 2084/2155/2235, ×½ at 2140, ÷2+ at 2208 where its bars meet at the
  blur). But the tracker also resizes its gate (2165-2180, 2219-2233), so the gate alone is no scale. Two scale tests
  failed and are not in the toolkit. The sky's drift against the known slew locked onto the MPEG-1 block grid (±8
  px). The noise grain's spectrum ran the wrong way to be a calibrated test.
- **Values read by a person:** `glyphs` (above). It works on the drawn scene. On FLIR1 it suggests the azimuth's
  digit right on 8 of 11 stretches; letters can come out as digits.
- **`atflir`'s test:** a drawn display was already in `test_camera` (the old handoff was stale). It now has a mnemonic
  and a zoom step. GIMBAL and GOFAST are goldens against ticks read by hand off strips, at today's recall.
- **`events` in `run`, scored on an MTS-B display: decision kept, not a stage.** On PR27 (frames 1-600) every readout
  is under a redaction box. `events` found one "text box", and it was the scene (a breakwater). That gave 19 false
  readout events in 20 s, about one a second, so a random rate step would fall within 3 frames of one about a quarter
  of the time. A guard on frame-to-frame stillness does not separate the two: the scene box moves 0.14, FLIR1's text
  boxes 0.13-0.22, and GIMBAL's 0.02-0.13, because PR27's camera mostly stares. `camera --events auto` stays for
  clips where a person has looked at the boxes it found.
- **The released-track null on another clip: not done.** No PURSUE clip besides PR051 has a lock loss with a readable
  line-of-sight rate. PR111 is an ATFLIR clip, but its azimuth is under a redaction box. PR051 (MTS-B, a break-lock,
  and a north pointer that gives the azimuth at unit gain) is parked, and it was not reopened. It is Jacob's call.
- **Versions of PURSUE clips:** uap `analysis/corpus/renditions/` (commit 0006c43). For PR135, PR097, PR141, PR113 and
  PR149, DVIDS's base file and its 1920 × 1080 rendition carry the same frames at lag 0. At the base's width the base
  keeps the more detail (the rendition 0.73-0.98 of it; PR113 the same). No rendition holds anything above its base's
  resolution: its excess over a plain upscale is its encoder's noise, which an upscale of the base re-encoded at the
  same bit rate reproduces. The base files the papers used are the right sources.
- Found on the way: `events` misses FLIR1's field mnemonic. `forensics.static_masks` takes the strip under the
  picture's top edge (rows 12-21, the rule and the text) as a solid block, and `find_boxes` leaves blocks out.
  `atflir` finds the mnemonic by its layout.

## The third Open list, worked through (2026-10-20, night)

- **`camera --fields` from `run`: done.** A case-file key, as the handoff proposed, is a row of `stages.KNOWN`:
  `--fields` and `--fov-px`. The case keeps them in its ingest's `known` and its commands, so `report` and `share
  rerun` repeat them. Found on the way and fixed: `add_known` (`mcdonald report CASE --fov`, the report card's "Add what
  you know") worked out the scale and kinematics again and left the camera stage's degrees in the old scale, or in
  none. `--fov-px` also moves the scale stage's k now; before, `run --fov 0.7` on FLIR1 put the 0.7 deg across all
  352 px of the frame, 1.44 times the 244 px the picture spans.
- **`static_masks`' blocks swallowing text drawn against a border: done, in `events`, not in `static_masks`.** Every
  other reader of `blocks` (layers, autolink, propose, integrity, events' picture level) wants symbology masked, so
  their masks are untouched; only `events.find_boxes` wanted the text, and it now judges `text_strokes`. The same fault
  was worse on GIMBAL than on FLIR1: the sky above its clouds is black on 95 % of frames, so its whole top line, the
  azimuth among it, was inside `blocks`. `events.find` with nothing given, five clips (Slurm 8613; PR27 frames 1-600,
  the others as their goldens):

  | clip | before | now |
  |---|---|---|
  | FLIR1 azimuth | 12 of 13 ticks to the frame | 12 of 13; the mnemonic a box (changing at 2166.5), the bottom line's readouts too |
  | GIMBAL azimuth | its box short of the `L`; 9 to the frame, 10 changes where no tick is | 12 of 13 to the frame, none false |
  | GOFAST azimuth / elevation | 5 of 6, 1 false / 3 of 3 | 6 of 6, 1 false / 3 of 3 |
  | PR27 (its one box is scene, a breakwater) | 19 events | **40** |
  | PR144 | 17 events | 19 |

  PR27's box is the same one; the quiet frames (next item) double its false changes. `events` is not a stage of `run`
  and `camera --events auto` is for clips where a person has looked at the boxes, so this sharpens that decision and
  changes no default; but it is a cost.
- **`glyphs` on letters: done for the azimuth's side, not for the mnemonic.** Letters come from text a person has read
  once (fixed text with `--letters`, the words given in `--read`), cut at the display's pitch where the blur joined
  them. They cannot be matched beside the digits everywhere: sharper than the clock's digits, they outscore them on
  true digits (all glyphs as one set, FLIR1's digits right fell from 8 of 11 to 1, `O` taking 0, 2, 3 and 6). So
  `atflir` reads each field by the ATFLIR's grammar. FLIR1's azimuth side comes out right on 10 of the 11 hand-read
  stretches, `?` on the other and wrong on none (it read as 8, 1 or `?` before). An experiment that read the side
  without the glyph-height test had all 11; `read` keeps the test. Cutting joined glyphs at the pitch also lifted its digits to 10 of 11, none wrong.
  The mnemonic is still a person's to read: `NAR` suggests `N??` (its letters match one another within the margin),
  and MFOV `N???` (no `M` was given, and the nearest letter stands in).
- **A one-segment change at 1080 rows: mostly done, and not by the routes proposed.** A statistic over segment-sized
  strips of the two windows' difference changed nothing on GIMBAL or GOFAST, nor did keeping 4 or 16 times the
  pixels (`KEEP_PX` 2400, 9600). The cause was the noise estimate (above). With the quiet frames, `atflir` gives GIMBAL
  12 of 13 and `events` GOFAST's 38 -> 39 too. Still missed by `atflir`: GOFAST's 38 -> 39 and GIMBAL's 49 -> 48, single
  segments. Folding a readout's cadence was not tried: GOFAST's azimuth ticks at 13, 85, 133, 151, 241, 259, no cadence.
  GIMBAL's hand-read ticks were themselves off by up to 4 frames (read off a strip of every tenth frame); the golden
  now has them read off every frame.
- **The released-track null on a second clip:** not done. PR051 is still parked, and was not reopened.

## Tests (2026-10-21, Slurm job 8687, `sbatch tools/suites.sbatch golden`)

All suites pass on the branch: measurement 398, reduction 212, published 32, tether 24, audio 54, cli 109, share 25,
sweep 10, stabilize 13, aspect 10, waves 8, slew 35, **camera 114**, gui 698 (1 skip), and **golden 109**. The evening's
run (8427) was 90 in camera and 106 in golden. On the way (8612) one golden check failed: the azimuth's side "right on
all 11", which an experiment had given by reading the side without `read`'s glyph-height test. With the test it is 10
of 11 and none wrong, and the check says so (8683, golden alone, passed). Run 8687 also has the size/speed figure's
lines over `--fov-px`, added after 8612.

## Open

Since 2026-10-21 each item is on `ROADMAP.md`: the reference case files as Decisions' open item 9, the rest as
rows of the ideas bank whose "from" is this handoff.


- **The reference case files.** `share rerun --strict` on them now differs by additions (the camera stage,
  `kinematics`' `held` and `noise_px`, the ladder's 0.7 deg row, a camera "no power" in the bottom line's count where a
  track is under 8 frames). Remake them, or let strict reruns allow additions: Jacob's call, still open. `camera` stays
  a stage of `run` (Jacob, 2026-10-21).
- **`camera` and `zoom`.** Main's `mcdonald zoom` (merged the same day) finds the MTS-B's zoom states from bursts of
  blank frames and fits each; `camera` finds a zoom inside a track from the object's size and offset, which FLIR1's
  needs (it has no blank). Neither reads the other yet: `zoom`'s steps could be `camera`'s events (`--events`), and
  `events`' picture steps `zoom`'s bursts (`docs/handoff-zoom-slew.md`).
- **A single segment's change on a 1080 rendition** (GOFAST's 38 -> 39 and GIMBAL's 49 -> 48 under `atflir`). Ideas not
  tried: a template of each look's strokes matched frame by frame as `readout` does, once a person has read the looks;
  or the stroke a digit gains or loses drawn from the clock's own templates (8 -> 9 is the 8 less its lower-left stroke).
- **Reading the mnemonic.** Letters that match one another within `MIN_MARGIN` at this blur; and `M`, `F`, `V`, `W` are
  in no fixed text on FLIR1 (`MFOV` and `WFOV` are on screen for 52 and 10 frames). A person reads it; three looks.
- **`events` boxes of scene.** PR27's one box is its breakwater, and its false changes doubled with the quiet frames.
  Nothing tells a box of scene from one of text yet but `unsteady` (long back-and-forth runs), which it is not.
- **`camera --events auto` on FLIR1 now sees more boxes** (the mnemonic's, the bottom line's): its exit's events should
  be looked at again before relying on them there.
- **The released-track null on a second clip:** PR051, if Jacob wants the parked case opened for it.
