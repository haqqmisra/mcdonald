# Handoff: a light that flashes in a train (branch `blinks`, 2026-10-20)

Started 2026-10-20 at Jacob's word ("go ahead and build the comb check in mcdonald"). The question came from a UAPSAC
council member: helicopters have blinking lights with known properties, so might a rotor's beat and a light's flicker
show as two peaks? The PURSUE analysis that answered it is in the uap repository: `analysis/methods/helicopter_lights.md`,
`analysis/sweeps/svanstrom/heli_lights.py`, and the SI-style figure `heli_lights_fig.png`. The answer: in visible video,
yes. The light is a comb (40-100 flashes a minute and its harmonics); in thermal video, no light shows. Method §19 has
the whole of it; ROADMAP 0.5's Aircraft line has the status.

## What is on the branch

- `flicker.lights`, `reach`, `light_reach`: each tracked thing's 3 brightest and 3 reddest pixels on every frame, in a
  disc that covers its silhouette; read in `_apertures` beside the sum, so the frame is read once. Light controls at
  four places at least twice that disc away (`curves(lit=, litring=)`, named "background light dx,dy").
- `flicker.flashes`, `blinks`, `deflash`, `blink_reading`, `said_blink`: the flashes, the fold (Z^2, 4 harmonics,
  0.6-3 Hz, 2,000 random sets), the fundamental rule (BLINK_FUND), the rule's rate band, the controls, and the beat with
  the flashes taken out. `measure` calls `blink_reading` after `judge`, so a stage that ends early still gets it.
- `report.Case.blink_said`: the bottom line's sentence. The headline is untouched.
- Constants: LIGHT_K, LIGHT_SIGMA, LIGHT_FLOOR, BLINK_*.

## Tests and runs (all through Slurm)

- `test_measurement.test_a_light_that_flashes_in_a_train` (11 checks; `_Flasher`, a dark body carrying a red or white
  light). `test_golden.test_svanstrom_helicopter_lights` (5 checks).
- All 14 suites plus golden pass on the branch (job 8577: measurement 418, golden 77, gui 712, ...).
- The known-answer sweep: every labelled Svanström track (836) through the branch's `flicker`. Exactly the two known
  lights flash; there are no false trains, and none in the thermal tracks. Working files and the per-track JSON are in
  `/scratch/mcdonald/blinks-sweep-2026-10-20/`. The summary is the uap repository's
  `analysis/sweeps/svanstrom/blinks_sweep_summary.py`; V_BIRD_020_o2 failed on a frame its labels name and its clip
  lacks.

## Traps paid for

- **The fold's strongest is a harmonic.** Flashes in step at 1/P are in step at k/P too, as tightly, so the planted
  1.00-Hz train read 3.00. The fix takes the lowest rate within 0.8 of the strongest.
- **The extent is the core's.** The first sweep found nothing at all: V_054's extent is 8.5 px, and its lights sit
  14-35 px out. `reach` reads the whole silhouette.
- **A merge window longer than the gap.** At 0.35 s the flashes of a 2.5-Hz train merged into one. It is 0.15 s now.
- **A robust scatter of zero.** A grey frame's red excess is exactly 0 between flashes. LIGHT_FLOOR holds the scatter to
  one grey level.
- **The highest frame of a flat-topped flash scatters the timing.** Time a flash by its centroid.

## Open

1. A visible-band airplane or drone with its light caught, at night especially. The Svanström set has none, so the
   rate band's other half and the 180-a-minute overlap rule have no real known answer yet.
2. Mid-wave infrared: no known answer. Most PURSUE pods are mid-wave.
3. A formation's synchronised lights (wind-farm obstruction lights are synchronised within 0.05 s). Read the train
   across a group's members.
4. Run it on the PURSUE EO clips (PR49's 10 objects, PR106) and on Table 1's beats (the bird paper) for the record.
5. Merge to main and release: Jacob's word.
