# Handoff: `mcdonald audio` — the sound track, on branch `audio`

Written 2026-10-16, at the end of the session that built `mcdonald audio` and its page in the window. Everything
here is on branch `audio` (worktree `/models/mcdonald-audio`). It is **not merged to main and not pushed**: Jacob
reviews it first. The branch merges cleanly onto main as of 07d2a3b (checked with `git merge-tree`).

## Where things stand

- **The command.** `mcdonald audio VIDEO [--json] [--out DIR]` reads a video's sound track (up to 15 minutes; the
  method is `docs/method.md` §10). In order, it reads:
  - the codec's frame families, and an earlier encode's cross-products;
  - the frame rate (it needs k = 1);
  - the 400-Hz bus and the mains, as clocks;
  - sidebands, and hum through a tape transport;
  - harmonic series;
  - airframes from a sourced table (T56 C-130, C-130J, H-60). An airframe is named only when its second tone is
    heard, because an MQ-9 heard from the ground hums over a T56's 68 Hz.

  `flicker` adds the heard rhythms, folded through the frame rate, to its look-alike table (`audio.heard`).
- **The window** (this session's last commit). Measure → The sound of this video… (`sound_qt.py`) works like this:
  - A wait's card goes at the top of the right column while a thread reads the sound. Cancel takes the card away,
    and nothing opens.
  - Then a page over the video shows the plain headline and sentences (`audio.plainly`), the figure (saved as
    `<tag>_audio.png` in the results folder) and, folded, the command's own words.
  - The reading is kept per video (`QtMarker._sound`), so a second look opens at once.
  - The row is in `actions.ACTIONS`; `sound` is in `PAGE_OK`.
  - Seen on PR117 (named a T56 C-130), PR113 (recorded on an aircraft, copied on the ground) and a silent PURSUE
    clip, offscreen and through Slurm.
- **Tests.**
  - `test_audio` 43 portable checks, including `test_what_the_window_says`.
  - `test_golden`'s `test_audio_cases`: 21 checks.
  - `test_gui`'s `drive_sound`: 11 checks, on a drawn propeller and a silent video. Run it alone with
    `tools/drive_one.py drive_sound`.
- **Data.**
  - `/models/data/mcdonald/aircraft_audio/`: DVIDS C-130, UH-60 and MQ-9 tracks, and the Apollo 14 tape as a
    negative control.
  - `/models/data/mcdonald/pursue/`: PURSUE clips with sound.
  - The corpus runs are in the private analysis repo.

## Open, in order of value

1. **NTSC field-rate buzz is read as mains.** An acoustics survey the same day found it, fitting harmonic by harmonic
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
4. **Merge and release**, when Jacob says so. Before merging:
   - check main's `flicker.py` and `cli.py`, both touched here;
   - then bump the version (a release needs a newer number).

## Traps paid for

- **A picture drawn in a thread** must not go through pyplot. With a display and Qt loaded, pyplot may choose the Qt
  backend and make a canvas off the main thread. `audio.figure` draws on a plain `matplotlib.figure.Figure`.
- **A page's ReadingView text starts with a newline** when it opens with a table (the headline's card). Compare with
  `lstrip()`.
- **One check in `test_cli` failed once** in the full suites, "the helper leaves nothing behind": the update helper
  deleted its folder a moment after the check. It is untouched by this branch, and it passed 105/105 on a rerun.
