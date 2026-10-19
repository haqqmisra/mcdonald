# Handoff: `mcdonald waves` (branch `waves`, worktree `/models/mcdonald-waves`, 2026-10-19)

**What it is.** The sea as a ruler: metres per pixel from the dispersion of the waves the clip shows,
omega^2 = g|K|, with no field of view, range or telemetry. Module `src/mcdonald/waves.py`, docstring first.
Registered in `cli.py` as `mcdonald waves`. Not merged, not released, no test file yet.

**Where it came from.** The prototype in the uap repo (`analysis/tools/waves_proto/`, copied from
`/hugespace/local/tmp/oman/waves/` on 2026-10-19) and the handoff `analysis/methods/wave_ruler_handoff.md`
there, which also sets the pass criterion: PR149 and one more known case within +-25 % on m_x, nulls apart.

## State of the evidence (2026-10-19, evening)

- **The physics is in the footage.** `tools/waves_kw.py` draws each patch's (|k|, rate) periodogram along the
  texture's dominant direction with a known scale's dispersion curve over it. PR148 (vessel 218 px = 30-60 m): the
  energy ridge lies on the 0.2 m/px, q 1.4 curve over |k| 0.08-0.6 rad/px, one branch bright, the opposite faint; the
  same in a 3-s window. PR149 (hull 920 px: 0.163-0.228 m/px, q 1.9-2.3): the ridge sits on the curve, over |k|
  0.06-0.4 in the far patches, a narrow swell band (0.08-0.15) off the bow. Figures `/hugespace/local/tmp/waves/kw/`,
  copies in the uap repo's `analysis/cases/pr14{8,9}/`.
- **The dominant direction is the line of sight on every patch (81-109 deg from x)**: thermal texture is the
  along-look slope (the IR-physics note), so only the scale along the look is fixed and m_x and q trade along a
  ridge. The stage reports `m_along` with its band; `--q` (1/sin depression, never under 1) pins m_x.
- **PR149, q held at 2.1: pass.** The three patches clear of the ship's wake read 0.218, 0.222 and 0.260 m/px against
  0.20-0.22 expected at their range (they sit above the ship, so a little farther), bands 0.18-0.35, shuffled null 0.02
  against 0.30-0.33 on the shell; the stage's one number 0.222 (0.184-0.353), the patches agreeing to x1.19. The four
  patches in the wake and bow wave read 1.5-2x high and are refused (a drift gradient across the patch; the lit bins
  sharing one rate). With q free the same patches give m_x 0.16-0.22 with q 2.8-3.5 and m_along 0.46-0.64 (bands x2-3).
- **PR148, q free: consistent.** Four of five patches claim, m_x 0.19-0.38 with q 1.0-2.65, the along-look scale
  0.26-0.44 m/px; the vessel allows 0.14-0.28 and its depression is unknown, so this is a factor-of-two check, no more.
- **PR120's one second of sea: refused on every patch** (too short for the shell; the stepped phase explains 0.3-0.8
  of the rates and the quadrants' drifts disagree). The prototype's 0.044-0.068 m/px is not confirmed. See the uap
  repo, `analysis/cases/pr117/README.md`, "The sea as a ruler on PR120's sea second".
- **What broke the first fits, and the fixes.** (1) A zero-rate line through every |k| (what does not propagate):
  `detrended` (the mean frame, then a 4-s running mean on records of 8 s or more) and the shell share masked within one
  resolution element of zero. (2) The codec's 7.5-Hz cadence (GOP anchor period 4; the envelope's `encoding.gop.lines_hz`
  already knows it): masked beyond `CODEC_FRAC` 0.45 of Nyquist. (3) Dilution by bins that hold no wave: each bin's
  weight carries how tonal its periodogram is. (4) One strong wave leaking through the taper into every bin, each lit
  at the one rate (Weichert et al. 2023): refused when the lit bins' rates spread under 1.5 resolution elements
  (`one_rate`). (5) Frame-to-frame phase correlation cannot register a dispersive texture (peak 0.06): `hold_sea` is
  kept but off; PR149's sea is in fact held by the sensor.
- **The synthetic ladder** (`tools/waves_ladder.py`, 22 rungs; `/hugespace/local/tmp/waves/ladder/`): the stepped-phase
  fit on clean one-second wind seas reads 0.95-1.1x and refuses a 100 px/s drift, a narrow swell at 1 and 10 s, a
  drift gradient, a two-way sea; it still claims at 0.62x with jittered frame times, 0.75x with a 0.6 radiance
  nonlinearity and 1.34x through H.264 at 630 kb/s. The shell fit reads 1.00-1.03x at 4-10 s (q 2 included) and is
  refused at 1 s. Known hole: a swell of 20 % bandwidth on a 256-px, 5-s synthetic is not refused and reads 0.23x
  (`tests/test_waves.py` tests the monochromatic swell, which is refused; the suite's 8 checks pass, Slurm job 7071,
  3.6 min on 2 CPUs).
- **Literature** (`research_notes/Ocean wave dispersion as image scale/` and `reports/Ocean wave dispersion as image
  scale.md` in the uap repo). Precedent: Spencer, Shah & Guha 2006, IEEE TIP. Chen 2019 is the coherence-weighted
  phase-rate fit; Serafino 2010 the normalised scalar product; Weichert 2023 on leakage; Stole-Hentschel 2023: five
  peak wavelengths in the window, wavenumber resolution over record length. The IR note: the slope-to-radiance gain
  changes sign at 10-30 deg depression; harmonics travel at the parent's speed (the scale reads low by their order);
  the camera's own motion gives a flow gradient V cos(delta)/H across the patch. Our claim: the joint scale +
  foreshortening + drift fit for an oblique, moving, uncalibrated thermal camera.

## Running things

Everything through Slurm (`-c 2 --mem=3-4G`, 1-6 min a patch; peaks 2.2 GB synthetic, 2.9 GB a PR148 patch).
- `sbatch --array=0-21%8 /hugespace/local/tmp/waves/ladder.sbatch` (and `ladder_held.sbatch`);
  `python3 tools/waves_ladder.py --summary DIR` for the table.
- `/hugespace/local/tmp/waves/pr149.sbatch` (`N1=`, `HOLD=1`), `pr148.sbatch`, `kw.sbatch`/`kw2.sbatch`.
- The stage itself: `mcdonald waves VIDEO --n0 --n1 [--patch X0,Y0,N ...] [--held STABILIZE_CSV] [--static A-B]
  [--q Q] [--truth M,Q] --out DIR [--json]`.

## Next

1. Sources of q: the symbology's depression where it is shown; the horizon; a vessel's proportions. Without one the
   stage says only m_along.
2. The codec mask from the envelope's own GOP lines instead of a fixed share of Nyquist; the 20 %-bandwidth swell.
3. The three soft spots of the one-second fit (jittered times, nonlinearity, H.264): a planted control at the fitted
   scale would say when the record is one of them.
4. PR144, PR123-125: not yet run (PR144's slew was already noted to defeat a dispersion scale in the uap notes).
5. Merge: after Jacob's 0.3.x work lands and he agrees; `tests/test_waves.py` into `tools/suites.sbatch`; a golden for
   PR149's far patches.
