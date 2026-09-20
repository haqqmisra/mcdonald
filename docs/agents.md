# Doing the whole job from the command line, with no window

For an agent: something that reads text and JSON, can open an image file, and
cannot click. Everything the marking window does has a command, and this is
the job done with commands only, on the clip the package's own tests use for
it — DOW-UAP-PR113, where two marks reproduce the published 142 px/frame.
Every command and number below was run on 2026-09-20 with `mcdonald` 0.2.0.

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
  mark at a candidate's coordinates, the link will report that it passes
  "within 0.0 px of all marks". That is circular: the mark *is* the detector's
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
export MCDONALD_CATALOG=/path/to/pursue_index/records.csv    # only to use record ids; a path to a video always works
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
   "detector": {"size_px": 21.0, "dark": true, "min_resp": 5.0},
   "px_from_each_mark": {"408": 0.03, "411": 0.04},
   "px_at_which_the_link_from_the_mark_before_arrives": {"411": 0.04},
   "disputed_frames": [], "lost_after": null, "lost_going_back_from": null,
   "searched": [400, 420], "stopped": false,
   "summary": "4 of 4 frames linked, 408–411, at 21 px, dark; …",
   "concerns": []}}
},
"needs": ["a look at cases/pr113/pr113_autotrack_strip.png: nothing here can know whether the marks were on the object, …"],
"notes": ["2 of 2 marks were placed by an agent, not by a person looking at the frame. …"]
```

141.4 px/frame against the published 142. (The 0.03 px residuals are the
circular case above: these two marks were the detector's own positions.)

`concerns` is what the summary says in prose, as sentences you can test for:
a mark with no link under it, the track more than 6 px from a mark, a forward
link that does not arrive at the next mark, frames where the forward and
backward links disagree, gaps, a link that was stopped. Any of them means look
before going on. After a loss, mark the object where it reappears and run the
command again.

## 4. Measure

Every measuring command takes the marks file, and links from it first:

```bash
mcdonald run PR113 --marks cases/pr113/pr113_marks.json --n0 400 --n1 420 --out cases/pr113 --json
mcdonald layers PR113 --marks cases/pr113/pr113_marks.json --n0 400 --n1 420 --out cases/pr113 --json
```

`run` writes `<tag>_case.md` and `_case.json`, and with `--json` prints the case
in the envelope: `results.bottom_line`, `results.stages` (each stage's results
as fields), `results.identified_by`, and — never dropped — `no_power` (what
this clip cannot decide, as `[test, why]`) and `needs` (what would close the
gap). A test that had no power has not passed. `run` makes a track sheet and
marks the object stages provisional until someone asserts `--i-looked`; do not
pass it unless you opened the sheet.

## The envelope

Every command takes `--json` and prints one object, alone on stdout;
everything written for a person goes to stderr.

| field | |
|---|---|
| `command`, `mcdonald` | which command, which version |
| `inputs` | the options it ran with |
| `clip` | `video`, `width`, `height`, `fps`, `fps_exact` (the rational; never round it), `n0`, `n1`, `duration_s` |
| `files` | what it wrote |
| `results` | what it found; per command |
| `no_power` | `[test, why]`: what this clip cannot decide |
| `needs` | what would close the gap |
| `notes` | things worth knowing that are not results |
| `exit`, `error` | the exit code, and the sentence that went with it |

`look`, `mark --no-window` and `run` have their results as fields. For
`layers`, `integrity`, `tracksheet`, `symbology`, `comotion` and `kinematics`
the envelope is made round the command: `results.said` is what it printed, as
lines, `files` is what it wrote, and a JSON report it wrote (integrity's) is
included under its file name. Their numbers are still in the prose; that is
the next thing to be done.

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
its click is `--set`; its `l` is `--link`; its `s` is what `--no-window`
writes; File → Open marks is `--load`. If a person opens a marks file you
wrote, the window shows each of your marks as `agent`, with your reason.
