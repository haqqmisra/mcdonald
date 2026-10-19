# Handoff: `mcdonald aspect` (branch `aspect`, 2026-10-18)

**What it is.** A stage that asks whether an object looks the same from every side: does its brightness or size
follow its heading? It needs no range, no field of view and no beat. A sphere does not change with heading; a winged
flyer banking through its turns does. Method: `docs/method.md` §14; module docstring `src/mcdonald/aspect.py`.

**State.**
- Branch `aspect` from main 76edc50, worktree `/models/mcdonald-aspect`. Not merged, not released.
- **Files.** `src/mcdonald/aspect.py` (new); `cli.py` (one line); `tests/test_aspect.py` (new, portable, 5 tests,
  all pass); `docs/method.md` §14 (appended; the `stabilize` branch has §13).
- It does not need `stabilize`, but on a filmed screen it runs on the held video `stabilize` writes, with
  `--still`.

**Validated.**
- Synthetic: a round blob on wandering loops is not called. A 25 % heading effect is read as 25.2 %. A straight track
  and a clean circle each say they have no power.
- PR121 (the case): see §14 and `analysis/cases/pr117/README.md` in the uap repo. The case was first worked with the
  uap repo's `analysis/tools/oman_heading.py`, the stage's prototype.

**On the real clips (2026-10-18, held videos from the `stabilize` branch, `--still --dark --depression 45`).**
- PR121 #1: 5.0 % / 2.8 %, p 0.45, null 95th percentiles 9.3 / 7.3 %; R^2 0.29; bank under 5.3 deg, V under 0.47 m/s.
- PR121 #5: 3.5 % / 6.6 %, p 0.70; null 95th percentiles 12.1 / 11.8 %; R^2 0.34. Its size against heading reads
  p 0.012 here and p 0.11 in the case script: not a result over four looks.
- Controls: round 0.3-0.4 %, and the planted 15 % read as 14.4-15.6 %.
- PR117: no power. The time slides admit 26 / 19 %, and a planted 15 % at 2theta is not recovered (24 % noise a
  frame).
- Note: the stage takes every frame of the held video, including those `stabilize` marked lost (it does not read
  their `ok` flag). Unwrapped turning is sensitive to that (PR121 #1: +907 deg here, +1268 deg on good frames only).
  A `--frames-ok` reader of the stabilize CSV would fix it.

**Open.**
- The bound assumes a flat thermal planform of uniform temperature. A body hot underneath and cold on top would add
  terms.
- The sensor's depression angle is an input, never measured.
- No GUI page.
- It could join `flicker`'s report as the glider's complement (ROADMAP 0.5).
- A control on real footage is still needed: the Svanström labelled infrared birds, or the Galileo flyers that turn,
  should be *called*. Until then a positive result is untested on birds.
