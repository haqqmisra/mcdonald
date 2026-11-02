# Agent run: the bird sweep over 18 PURSUE clips (2026-10-09/10)

**Status:** open, nothing changed in the code. Found by running the released **0.2.15**
(`/scratch/mcdonald/venv-0.2.15`, not the editable tree) on the 18 clips the ledger lists with "bird"
among their prosaic hypotheses, through Slurm. Everything is in `/scratch/mcdonald/birds/`:
`<case>/` per clip, `<case>_run.json`, `<case>_accept.txt` (link summary), `logs/`.
Marks are an agent's (`--set` with `--why`), each object checked on the proposals sheet and the track strip.

## What 0.2.15's flicker did with them

| outcome | clips |
|---|---|
| tested, no beat of its own | PR067a, PR067b, PR058, PR100, PR35 (10 fps), PR098 (one member) |
| **beats: a real one** | **PR41: 6.43 Hz on the whole 24.6-s track (34.5x over drift, 9.7 needed), 40 of 98 windows** -- see below |
| tested, near miss | PR068a: 3.64 Hz, 20.5 %, stands 6.9 over drift where 7.4 is needed, 2.8 s only |
| **"bird is the leading explanation"** | **PR094: 4.97 Hz, 3.2 %, from 2 of 54 windows** -- see 2 below |
| no beat looked for: "lost" on > 10 % of frames | PR29, PR007a, PR007b, PR056, PR086, PR116, PR052, PR47 -- see 1 below |
| too short (< 60 frames) | PR087 (18), PR40 (53); PR19 (14-frame streak) would not link |

So 8 of 18 clips never got a beat test, and every one of those 8 is a false "lost".

## 1. "Lost" fires on objects that are plainly there

`flicker.lost()` calls a frame lost when the object's brightness over the ring falls under 25 % of its
own level. On these clips the object is visible and steady on the "lost" frames. Three separate causes:

**a. The aperture does not scale with the object.** `APERTURE = 4.0` px and `RING = (7, 10)` px are fixed.
For an object wider than ~14 px the ring lies on the object itself, so object-minus-ring goes to ~0.
PR086 (35-45 px round object, 59/168 lost), PR116 (50-100 px dark mass, 53/291), PR052 (45 px link size,
257/606), PR056 (15-24 px, 29/134), PR47 (three ~17 px rings with bright rims and dark centres: the
aperture alternates between rim and centre, 41/245). The link already knows the size (`size_px`, 15-45 here); the
aperture and ring should follow it, or flicker should say no power for an object much larger than the
aperture instead of calling it lost.

**b. Hold-and-jump cadence.** PR29 is ~10 fps content at 30 fps: each picture is held 3 (sometimes 4)
frames, then the object jumps ~11 px (frame differences exactly 0.00 between). The core brightness is
flat (203 +/- 2 DN over frames 95-124), but `SMOOTH = 5` frames of track smoothing puts the aperture
between the held positions at every jump, and the lost frames come every 3rd frame (97, 98, 101, 102,
105, 108, 111 ...). The survey already counts repeated frames; flicker should work on the unique
pictures (and then the band ends at the content's Nyquist, 5 Hz on PR29, not 15).

**c. Hand-held shake / faint specks.** PR007 (10 fps hand-held thermal, 5 px dark specks): 58/100 and
33/71 lost. The 5-frame smoothing is 0.5 s at 10 fps, and the camera's shake moves the speck several
px within that, so the 4-px aperture slides off. `--dark` does reach flicker (`brightness(dark=)`), so it
is not polarity.

**d. Wave crests in the ring.** PR056 4402-4411: core 221-229 DN throughout, but bright wave crests pass
through the 7-10 px ring (ring 45 -> 126 DN). Edge-enhanced footage also morphs the object's shape.

A deep real pulse (PR056 is described as "pulsing") and a dropout look the same to this rule. Whatever
the fix, the report should not read "lost against what is behind it" when the object's own core is flat.

## 2. A bird headline from 2 of 54 windows at 3 %

PR094: the whole track does not pass (2.44 Hz, under its drift). Two overlapping 2-s windows (5297-5356,
5304-5363, i.e. one ~2.2 s stretch) pass at 4.94-4.97 Hz, 2.8-3.2 %, and per change 5 of 0.2.15 the
clearest passing window is reported because the whole track does not pass. The report then leads with
"A bird is the leading explanation". The light curve over that stretch is a ~+5 % / -5 % step plus three
isolated 12-15 % dips, not a periodic beat; outside it, peaks are 2.7 and 5.0 Hz at ~3x their band. No
codec line at 5 Hz (lines 7.5 Hz) and no hold cadence (frame differences 0.01-0.57, no zeros in a pattern).
With ~7 independent 2-s windows in 428 frames and a 1 % per-window false rate after the drift test, one
passing stretch somewhere is not rare. Suggested: require the passing windows to cover a real share of the
track (or two non-overlapping windows) and an amplitude floor before the conclusion names a bird; a lone
window could be reported as "a beat in one stretch" without the headline.

## 3. The editable install changes under a running job

A run started from the editable `/models/mcdonald` tree crashed mid-way when `flicker.py` was edited
(`AttributeError: module 'mcdonald.flicker' has no attribute '_init'` in the forkserver children: they
import the module fresh). Batch runs should use a pinned venv; `run`'s envelope could record the git
state (dirty or not) next to `mcdonald: 0.2.x`.

## Smaller things

- `look --propose` finds nothing on an object the sensor holds still (PR116: every row is reticle or
  blocking); `look --frame N` found it as candidate 1. The proposer could say "nothing moves against the
  background; the object may be held: try --frame".
- Multi-fragment marks fail where the fragments have different sizes (PR086: proposals at 19-35 px;
  "no spot size puts a spot within 6 px of the marks"); a single fragment linked 168 frames.
- PR098 `groups`: "every pair of members keeps its separation to within 2x the position noise" --
  a rigid formation, which is a useful discriminator against a flock; worth surfacing in the conclusion.

## PR41: the one real beat, and what it says about the aperture

PR41 (R01, faint white point over water held centred, 737 frames at 30 fps): 6.43 Hz on the whole track,
40 of 98 windows passing, the background apertures nothing at that frequency. Checked outside the tool:
the beat holds at 6.40-6.46 Hz in every 5-8 s segment; the object's centroid bobs vertically at the
same frequency (0.75-1.13 px, band median ~0.07 px) while five background patches move <= 0.01-0.1 px at
6.42 Hz (no camera jitter); no hold cadence; codec rhythm 7.5 Hz.

The 4-px aperture reports **3.2 %** on the whole track; a whole-object aperture (r < 12 px, fixed smoothed
centre, ring 16-22 px) gives **9-17 %** in every segment. The small aperture undercounts the amplitude and,
in 2-s windows, loses the beat between frames 2340 and 2600 where the big aperture still has 12 %. Same
root as 1a: the aperture should follow the object's size.
