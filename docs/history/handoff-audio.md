# Handoff: `mcdonald audio` — the sound track, on branch `audio`

Written 2026-10-16, at the end of the session that built `mcdonald audio` and its page in the window. Everything
here is on branch `audio` (worktree `/models/mcdonald-audio`). It is **not merged to main and not pushed**: Jacob
reviews it first. The branch merges cleanly onto main as of 07d2a3b (checked with `git merge-tree`).

**Since then:** merged onto main on 2026-10-17 (e5752be) and released in 0.3.0 on 2026-10-19; the branches `audio` and
`audio-player` are deleted. Jacob has heard the sound play with the picture: "I listened, it works!"

## Where things stand

- **The command.** `mcdonald audio VIDEO [--json] [--out DIR]` reads a video's sound track (up to 15 minutes; the
  method is `docs/method.md` §11). In order, it reads:
  - the codec's frame families, and an earlier encode's cross-products;
  - the frame rate (it needs k = 1);
  - the 400-Hz bus and the mains, as clocks;
  - sidebands, and hum through a tape transport;
  - harmonic series;
  - airframes from a sourced table (T56 C-130, C-130J, H-60). An airframe is named only when its second tone is
    heard, because an MQ-9 heard from the ground hums over a T56's 68 Hz.

  `flicker` adds the heard rhythms, folded through the frame rate, to its look-alike table (`audio.heard`).
- **The window.** Measure → The sound of this video… (`sound_qt.py`) works like this:
  - A wait's card goes at the top of the right column while a thread reads the sound. Cancel takes the card away,
    and nothing opens.
  - Then a page over the video shows the plain headline and sentences (`audio.plainly`), the figure (saved as
    `<tag>_audio.png` in the results folder) and, folded, the command's own words.
  - The reading is kept per video (`QtMarker._sound`), so a second look opens at once.
  - The row is in `actions.ACTIONS`; `sound` is in `PAGE_OK`.
  - Seen on PR117 (named a T56 C-130), PR113 (recorded on an aircraft, copied on the ground) and a silent PURSUE
    clip, offscreen and through Slurm.
- **The sound with the picture, and its card** (Jacob, 2026-10-16/17; merged from branch `audio-player`):
  - `speaker.py` has no toolkit in it: `sound_of`, the ffplay command, and `Speaker`.
  - `mark_qt.SoundControl` is shared by the main player and the segment chooser: the speaker button, the check in a
    thread (kept per video in `QtMarker._sound_of`), `play`/`stop`/`resume`, and `follow` for the chooser, which
    waits for late frames (its sound is started again when the two drift 0.3 s apart).
  - `sound_qt.SoundCard`: "Measure the sound" in the right column, only when the video has sound; teal until read,
    then ticked and grey.
  - Untested here: the sound itself through speakers (no sound card on the Slurm node). The tests check what ffplay
    is asked to play. Jacob's ears are the check: on 2026-10-19 he listened, and it works.
- **Tests.**
  - `test_audio` 54 portable checks, including `test_what_the_window_says`.
  - `test_golden`'s `test_audio_cases`: 25 checks.
  - `test_gui`'s `drive_sound`: 31 checks, on a drawn propeller and a silent video. Run it alone with
    `tools/drive_one.py drive_sound`.
- **Data.**
  - `/models/data/mcdonald/aircraft_audio/`: DVIDS C-130, UH-60 and MQ-9 tracks, and the Apollo 14 tape as a
    negative control.
  - `/models/data/mcdonald/pursue/`: PURSUE clips with sound.
  - The corpus runs are in the private analysis repo.

## Open, in order of value

1. **Done (acoustics session, same day): NTSC field-rate buzz is read as mains.** Fixed as below (frame comb from its
   own line before the mains, shared lines count for neither, the clocks re-read in 30-s pieces); see CHANGELOG and
   docs/method.md §11, "The clocks at full resolution". Also added there: `--flyover` (a passing source's speed and
   closest range). What follows is the item as it was written. An acoustics survey the same day found it, fitting harmonic by harmonic
   over the whole record.
   - 59.94 Hz (60/1.001) leaks into recordings as sync buzz. A 4-s window cannot tell it from 60.00.
   - The frame family is built at the container's 30.000 fps, so it drops the 29.97 comb from k = 3 up.
   - AARO's FLIR video reads as "mains" and is not. PR113's 59.988 is a blend of the field rate (59.944) and the
     mains (60.011).
   - The fixes (that survey's Ac1 and Ac2):
     - test against the frame and field comb before the mains, with a zoomed pass at full-record resolution;
     - a line shared by two families counts for neither (3 × 399.6 = 20 × 59.94);
     - flag a bus at 400/1.001.

   The window's page says whatever the tool reads, so it will follow the fix: today, for the FLIR video it would say
   "recorded on an aircraft, then copied on the ground", which is wrong.
2. **The MQ-9 into the airframe table**, once its propeller speed is sourced (its blade-pass is 67–76 Hz from the
   ground, with a second tone at 9.00×).
3. **A DHC-8 control** for AARO's Puerto Rico video (a CBP aircraft): its bus is heard (398.4 Hz), but no propeller.
4. **Merged onto main (2026-10-17, Jacob's word), released in 0.3.0 (2026-10-19).** The two doc conflicts were
   settled as planned: in `docs/method.md` main's "bird paper's method" stays §10 and `mcdonald audio` is §11;
   `README-technical.md` keeps both examples. test_audio (54 checks) ran on the Mac and Windows runners for the first
   time before the release (runs 68 to 71), and runs in the Linux suites on every push.

## Traps paid for

- **A picture drawn in a thread** must not go through pyplot. With a display and Qt loaded, pyplot may choose the Qt
  backend and make a canvas off the main thread. `audio.figure` draws on a plain `matplotlib.figure.Figure`.
- **A page's ReadingView text starts with a newline** when it opens with a table (the headline's card). Compare with
  `lstrip()`.
- **One check in `test_cli` failed once** in the full suites, "the helper leaves nothing behind": the update helper
  deleted its folder a moment after the check. It is untouched by this branch, and it passed 105/105 on a rerun.
