# Handoff: `mcdonald slew` (built on branch `slew` 2026-10-19, merged to main 2026-10-20)

**What it is.** k from the camera's own slew (ROADMAP V2): the scene's horizontal shift from `layers`, regressed on
the north pointer's turn from `symbology`, with the platform's share of the turn (the hold) as a term in time, gives
k cos(depression). Module `src/mcdonald/slew.py`, docstring first; method `docs/method.md` §17; test
`tests/test_slew.py` (seconds, synthetic series); end-to-end self-test `tools/slew_selftest.py` (a rendered pan through
`symbology`, `layers` and `slew`, about 4 minutes on four CPUs). Registered in `cli.py`; added to the suites' lists.
Jacob asked for it on 2026-10-19 ("build it on a branch, start with PR148", "use /slurm"), and on 2026-10-20 to
merge it to main and keep going ("we can hold off on the push and version release"): merged, not pushed, not released.

## State of the evidence

- **The fit works where the pointer can carry it.** Rendered pan, k cos(e) = 519.6 px/deg: 484 (16-84 % 459-585),
  524 in a window 1.2 s longer; a diagonal slew 485 (bracket flagged); a 0.5-deg slew and a pointer blind to the
  slew NO POWER; a pointer on a 1.07-deg grid refused. Runs and logs in `/hugespace/local/tmp/slew/selftest_{a..e}`.
- **What decided the rules** (each in the code beside the constant): the pointer is a staircase (PR148's "N" moves in
  3.25-px steps across), so theta is regressed on the scene (reverse fit) and the forward fit is the check; a lever
  under 0.55 of the grid step can put c 15-26 % off (synthetic staircases, eight phases each); `layers` gives no
  consensus where a slew eases in or out (1-4 px in five frames), so short gaps are bridged; windows span a whole
  slew, because half a slew looks like a changing hold; a floor stands only beside a registered slew, because a pointer
  referenced to the platform's heading gives a floor at any k.
- **PR148: NO POWER.** Case note in the uap repository, `analysis/cases/pr148/pr148_slew.md`; runs in
  `/hugespace/local/tmp/slew/run7` (pointer at NCC >= 0.7) and `run55` (0.55, path-filtered). The first slew (11-18 s,
  2200 px across) registers with the right sign in both (c 1123 and 1789 px/deg) and fails every check; the glyph is
  smeared into another shape for the two seconds before the slew starts; the hold goes from +0.33 to -0.48 deg/s over
  the minute.

## Changed outside the new module

- `symbology`: `--search DX,UP,DOWN` (and `measure(search=)`), the template's search box; the default is unchanged.
  An edge-of-search rejection was tried and taken back the same day: PR148's low-radius readings at the top of its arc
  were inside the search, at NCC 0.58-0.70, not at its edge.
- `scale.py`'s docstring lists the slew as route 4 of 5.

## Next

1. **The known-answer test**: a clip whose data bar gives the sensor's azimuth and field of view beside a pointer --
   PR051's MTS-B bar (`BRG`, `FVW`/`SLR`) -- settles the pointer's convention (dial, projected north or heading) and
   checks c against FVW/SLR. Until then every c carries the dial assumption.
2. The other pointer clips the ROADMAP names: PR43, PR48, PR060, PR061 (coloured pointers, chroma: no grid problem
   expected), PR144, PR149.
3. A lag check (the pointer drawn late against the picture): a scan of the time offset found the rendered pan's at
   0-0.1 s with a sharp minimum and PR148's flat; worth adding to the stage once a clip registers.
4. A reader for monochrome glyphs that the codec smears (PR148 9.2-11.3 s): the template's NCC falls to 0.55-0.65
   and its readings go wrong by a degree for a second at a time.
