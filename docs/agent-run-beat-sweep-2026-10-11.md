# Agent run: beat sweep of every PURSUE sensor video (2026-10-10/11, mcdonald 0.2.16)

What was run: `look --propose --more` over 401 windows covering the 126 clips of
`uap/analysis/beat_sweep_todo.csv` (whole clip up to 1200 frames; four 300-frame windows spread over
longer clips), then for each clip an agent picked the object from the proposal sheets (or, where
Find saw nothing, from `look --frame` candidates), `mark --set --link`, and `flicker` on the track.
All on merlin through Slurm from the pinned `/scratch/mcdonald/venv-0.2.16`. Working files:
`/scratch/mcdonald/sweep/` (`bin/beat.sh`, `bin/held.sh`, `bin/reflick.sh`, `results.tsv`, `review.tsv`).
Results and science: `uap/analysis/beat_sweep_all.md`.

Throughput: propose is ~2 s per 1080p frame on 2 CPUs (1.8 GB peak); 113 k frame-equivalents took
~13 h at four jobs. Exit 5 ("nothing moves") is a valid answer that `set -e` batch scripts treat as
a failure -- worth saying in `readme agents`.

## Flicker: false beats the tool reported (each checked by eye)

1. **Content cadence by near-duplicate frames (PR34).** Tool: "beats at 5.02 Hz (and 10.03, its
   double), 31 %, 6 of 8 windows, clear of the codec's rhythm". The clip is 10 pictures/s re-encoded to
   30 fps: frame differences go 1.06, .02, .01, 1.31, 0, .05, .89, ... -- the repeats are 0.01-0.05 DN,
   not 0, so a zero-difference repeat test misses them, and the codec check looks only at anchors.
   Fix: count a frame as held when its difference is under ~0.2x the median of the larger half of
   differences (`/scratch/mcdonald/sweep/bin/cadence2.py`), and veto a beat within a bin of the content
   rate or its half.
2. **[WITHDRAWN 2026-10-11 -- the fold cannot tell a real beat near a whole number of frames from a chain pattern; PR088 is a candidate, not an artefact.]** **Brightness locked to frame number (PR088).** 10.2-10.3 Hz, 22-26 %, three windows; content is a
   full 29 changes/s, but the light curve folded on frame mod 3 is +1113 / -105 / +69. A beat whose
   period is an exact integer number of frames and whose phase is fixed to the frame count is the
   chain's, not the object's. Fix: fold on frame mod p, p = 2..8 (`bin/phaselock.py`); PR099 and PR41
   give <= 0.3 of the curve's std at p = 2, 3, PR088 1.0 at 3 and 1.3 at 6.
3. **Lone stretches (PR071, PR073, PR078, PR057a)** -- the handoff's open question, now with four more
   cases: one window (or one run of overlapping windows) barely over drift (6.0-7.7x where 5.8-6.7 was
   needed). PR057a's two windows are at unrelated frequencies (7.72 and 14.12 Hz). PR073's 8.0-8.5 Hz
   sits one 0.5-Hz bin from the codec's 7.5 Hz anchor rhythm, which the 2-s window cannot resolve.
   The proposed gate (whole track, or two non-overlapping windows at one frequency) removes all four
   and keeps PR099, PR44, PR41, PR135.
4. **Near Nyquist (PR27, 13.5 Hz; PR057a, 14.1 Hz):** windows pass on frame-to-frame noise that has
   no visible rhythm in the light curve. Suggest a band top of ~0.8 x Nyquist for window calls.

## Flicker: sensitivity

5. **The aperture depends on the segment.** PR41's own track: extent 10 px over 2100-2836 (aperture 12,
   beats at 6.43 Hz) but 17 px over 2331-2631 (aperture 20.4). With 20 px on a 7-px point over water
   the background apertures read 8-11 % of the object's brightness, and the 6.42 Hz peak (16x over
   drift) is vetoed. Not the only reason that segment fails -- none of the 12 beating windows of the
   full run lie in it (the bird stops flapping) -- but the extent estimate should be checked on
   water/whitecap backgrounds, where the radial-profile median does not fall cleanly.
6. A positive control at 10 s is fine: 2536-2836 (a flapping bout) beats at 6.47 Hz, 42x over drift.
   Negatives on a 10-s window are "no beat in this stretch", not "no beat".

## Find / link

7. **Find is blind to an object held still on a still scene** (PR46, PR143, PR109, PR070, PR119): the
   object is on the reticle for the whole clip and nothing moves. `look --frame` + `--set` worked every
   time (`bin/held.sh`: candidate nearest a point read off the frame, on 3-5 frames).
8. **Static ground features rank strong/fair** on terrain and city clips (PR030, PR22, PR053, PR064,
   PR084, PR065): spots creeping 0.3-0.7 px/frame against a background the registration nearly holds.
   Requiring >= 1 px/frame against the background removes them but also loses held objects (PR21).
9. **Proposal -> link handoff fails** on two strong, long proposals (PR074, 106 frames, dark; PR076,
   98 frames): "no spot size from 5 to 71 pixels puts a spot within 6 px of the marks". The proposal's
   positions are not where the linker's detector finds anything; `tools/find_rank.py --link` should
   flag these before an agent accepts them.
10. **Hand-held and phone captures** (PR117-127, LLE-PR00x, PR007): shake breaks objects into 4-20-frame
    fragments; links then cover 30-70 frames at best.

## Census (object count, transit/held) from proposals alone

Fixed rules (object = strong/fair, background all round >= 0.3, not a tape, <= 2 going the same way,
seen >= 10 frames; transit = screen track spans >= 25 % of the frame or reaches an edge while moving):
**29 % agreement with the JAIS kinematic class (32/112), 54 % with one/multiple (61/112)**. Misses:
no object found on 21 clips (fast streaks under 10 frames, held objects on still scenes), and
spurious held "objects" from items 8 and 10. Propose is a candidate list for a person, as its
docstring says; it is not a census.

## Added after the sweep (2026-10-11)

- Item 2 withdrawn (above). Items 1 and 4 fixed on branch `flicker-correctness` (`pictures`, `TOP`); see CHANGELOG.
- Content-rate analysis is still to do: a clip that holds pictures is now only refused above 0.8 of its picture
  rate's Nyquist frequency; a real beat below that can still be masked by a stronger artefact line above it.
- The aperture size depends on the segment measured (PR41: extent 10 px over 2100-2836, 17 px over 2331-2631).
- "Too short" (under 60 frames) should read differently from "no beat" wherever a person sees it (PR37).
- Identity across a close pass: PR099's two ~6-Hz tracks meet within 85 px at frame 3600 and nothing warned
  that they may be one bird.
- A whole-video, many-object mode (what `/scratch/mcdonald/sweep/pr099/collect.py` did by hand).
- `forensics.repeats` has PR34's flaw too (the local median of differences is a held frame's when most frames are
  held); left alone here because integrity's and the survey's goldens count repeats with it.
