# Handoff: `mcdonald tether` (2026-10-07)

What it is, what was done to make it fit for a release, what it still cannot do, and what
to check before shipping.

## What it is

Is something tied to the object — a line, a payload — and does it swing? A hanging
point is a pendulum, T = 2π√(L/g), so the swing's period read off the video gives the
line in metres with no range and no field of view: the balloon analogue of PR135's
wingbeat. Module `src/mcdonald/tether.py`; a stage of `mcdonald run` after `flicker`;
`docs/method.md` §6 for the method, `docs/tether-validation.md` for the evidence.

## What the release work changed (prototype → candidate)

- **Two passes over the frames, not six.** One pass makes both stacks (on the object, and
  on the track run backwards); one pass measures every candidate's single-frame support
  and follows the best twelve. Frames are cached as uint8 with packed masks while the
  window fits in 600 MB. PR071 (227 frames): 460 s → ~190 s at the default radius.
- **The overlay's strokes are masked** (`stroke_mask`: a grey opening along either axis
  against a 9×9 one; thin, bright, ≥ 20 DN over its surroundings), within 600 px of the
  object. A tracking gate's box *is* tied to the object by the tracker and its edges passed
  every test on PR071 until this.
- **The noise is local.** The stack's noise is the std of the DoG on the inner annulus
  (1.2–8 object sizes), with each farther ring's own std as a floor: over 40 sizes the
  smeared frame edges set a global noise of 1.7 DN against 0.4 near the object and the
  string vanished; by MAD the flat sky gave 0.1 DN and admitted everything.
- **Candidates the control does not show are selected before the cap**, up to 200; the
  frame's edges and the display's fields are sharp on both stacks and were the forty
  strongest things in a 40-size stack.
- **A feature hugging the object (< 2.5 sizes) needs support on 60 % of single frames**,
  not 30 %: a crumpled balloon's glint at 1.2 sizes (WA9ONY, 42 %) is the object's own.
  The object's footprint (`object_extent`, through pixels covered on 95 % of frames)
  also pushes the inner radius out; the 95 % rule is *not* used for the search area,
  where a gate's masked strokes sweep the neighbourhood and 95 % dropped PR071's string.
- **Following is the arbiter.** Every kept candidate is followed; one that moves with the
  scene (`groups.with_the_group`) is the scene's, one that jumps by its gate is not one
  thing, and an unsupported one is accepted only when it moves with the object, smoothly
  (≤ 4 % of its separation a frame) and consistently (angle scatter ≤ 30°).
- **The swing.** Repeated frames left out; the sinusoid with a drift is the estimator (a
  periodogram's peak on a short window slides to the cap); its period carries a block
  bootstrap error; claimed from 2 cycles, tentative from 1.5. "Steady" is said when the
  periodogram's power is negligible, whatever the window.
- **Tests.** `tests/test_tether.py`: 24 portable checks (period → line; steady; too few
  cycles; repeats; the control; the object's size and extent; strokes). `tests/test_golden.py`:
  PR071 (string, steady), PR055 (nothing tied), WA9ONY-5 (2.4–2.8 s, 1.4–1.95 m, tentative;
  needs `MCDONALD_FOOTAGE`). The case report's bottom line names a companion and its swing.

## Results that must not move

| clip | companion | swing |
|---|---|---|
| WA9ONY-5 (85.8–90.0 s) | dark, 3.2 sizes, −14°, 17 × noise vs 1.0 on the control | 2.59 ± 0.02 s, 14.1°, 1.7 cycles, tentative → 1.66 ± 0.02 m (known ≈ 1.5) |
| PR071 (367–603) | dark line, 1.6 sizes, −14°, on 64 % of frames, jitter 3 px | steady −18 ± 5°: none |
| PR055 (1068–1300) | none: the stack's features move with the clouds | — |

Run with the default radius (40 sizes) and with `--r-max 6`; both must give these.

## What it cannot do yet

- A payload too faint for single frames that swings more than its own size: it smears in
  the stack by its swing and the follower has nothing to hold. A search over the
  pendulum's own motion (period, amplitude, phase as free parameters, the frames
  re-stacked along the predicted path) would find it; not written. This is the case that
  matters for a sounding balloon's radiosonde at range.
- A thin *bright* line on the object is masked with the overlay's strokes
  (`--no-stroke-mask`).
- No GUI panel: `mcdonald-gui`'s Measure form does not expose it; `run` does.
- One calibration with ground truth, at 1.7 cycles. A second, longer one (a sounding
  balloon's train filmed at close range with the sonde's own GPS) would settle the
  pivot-at-the-centre reading and the 1.5-cycle bar.

## The low-resolution half: `wobble`, tried and parked (2026-10-08)

`tether` needs the payload resolved; most sensor clips resolve only the balloon. A pendulum has
two ends, and the balloon recoils against its payload at the mass ratio m_payload / M_balloon
(the balloon's inertia is mostly the air it displaces): for a 2 m sounding balloon under a
0.15–0.4 kg train swinging ±3 m, ±0.15–0.4 m at the payload's 10–15 s period — ±1.5–4 px at
10 km, ±0.7–2 px at 20 km. On WA9ONY-5 the balloon's centroid does wobble at the payload's
period, 178° out of phase, at 0.16 of its swing (a crude check against the trees).

A command was built on branch `wobble-experimental` (not on main, not registered): the
object's sub-pixel centroid against scene features followed by template matching from
keyframes, two random halves of them as the control, repeats dropped, a detrended residual,
a periodogram tested against block-bootstrap surrogates with an amplitude floor and an
ellipse fit. Its synthetic test finds a planted ±1.5 px recoil at 8.0 s under pointing jitter
(7.85 s, 1.47 px, 107° ellipse, p = 0.003) and rejects the null (p = 0.31).

It is parked because the measurement needs a scene that is rigid to ~0.3 px over 10–15 s, and
no PURSUE balloon-hypothesis clip has one: PR071 and WA9ONY register to the screen (blank sky);
PR26's haze gives nothing to follow; PR055's clouds disagree by 1.9 px between two halves of
their features; PR086's sea by 8.5 px under a 70 px/frame slew; PR40's object is too faint to
centroid; PR28 is a halo over cloud with a polarity switch. In every case the stage says why it
cannot measure rather than returning a number. The rule agreed for inclusion was a working
PURSUE demonstration; there is none, so it stays off the release.

## Before shipping

- `python3 tests/test_tether.py`; `tests/test_measurement.py`, `tests/test_reduction.py`,
  `tests/test_cli.py` (all passed 2026-10-07); `tests/test_golden.py` with the catalog
  and `MCDONALD_FOOTAGE` set.
- `tests/test_gui.py` had one failure on 2026-10-07 unrelated to this work ("Stop during
  layers ends it there"), seen offscreen; check it on a desktop before blaming it.
- Version bump and the fresh-venv check are not done here.
