"""Does `mcdonald waves` read the sea's scale from its dispersion, and say when it cannot?

Synthetic seas only (`waves.synth`), small and quick: a broad wind sea at a known scale must
come back within a quarter on a one-second record (the stepped-phase fit) and on a four-second
record seen obliquely (the periodogram-shell fit, along the waves); a narrow swell must be
refused, and the same frames shuffled in time must be refused.

    python3 tests/test_waves.py        # or: pytest tests/

No video data needed.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import waves  # noqa: E402

FAIL = []
N = 256


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def along_truth(m_x, q, theta_deg):
    return float(waves.m_along(m_x, q, np.radians(theta_deg)))


def test_a_wind_sea_on_one_second_is_read_by_the_stepped_phase():
    S, t, rep = waves.synth(0.08, 1.0, U=(15, 5), N=N, n_frames=26, fps=26.0, seed=3)
    res = waves.measure_patch(S, t, rep, shell=False, n_shuffle=1)
    fr = res["rates"]
    check(fr["ok"] and not fr["no_power"], "one second of wind sea: the rates fit claims", f"{fr.get('no_power')}")
    check(fr["ok"] and 0.75 < fr["m"] / 0.08 < 1.33, "its scale is within a quarter", f"{fr['m'] / 0.08:.2f}x")
    check(fr["ok"] and abs(fr["U"][0] - 15) < 6 and abs(fr["U"][1] - 5) < 6, "and its drift within 6 px/s", f"{fr['U']}")


def test_a_wind_sea_on_four_seconds_seen_obliquely_is_read_by_the_shell():
    S, t, rep = waves.synth(0.2, 2.0, U=(10, 0), N=320, n_frames=104, fps=26.0, seed=4)
    res = waves.measure_patch(S, t, rep, rates=False, n_shuffle=1)
    fs = res["shell"]
    tr = along_truth(0.2, 2.0, fs["theta_deg"])
    check(not fs["no_power"], "four seconds, q 2: the shell claims", f"{fs['no_power']}")
    check(0.75 < fs["m_along"] / tr < 1.33, "the scale along the waves is within a quarter", f"{fs['m_along'] / tr:.2f}x")
    check(fs["band_along"][0] <= tr <= fs["band_along"][1], "and the band holds the truth",
          f"{fs['band_along'][0]:.3f}-{fs['band_along'][1]:.3f} vs {tr:.3f}")


def test_a_narrow_swell_is_refused():
    S, t, rep = waves.synth(0.2, 1.0, U=(10, 5), N=N, n_frames=130, fps=26.0, spectrum="swell", swell_bw=0.03,
                            swell_spread_deg=3.0, seed=5)
    res = waves.measure_patch(S, t, rep, n_shuffle=1)
    fs = res["shell"]
    tr = along_truth(0.2, 1.0, fs["theta_deg"])
    check(bool(fs["no_power"]), "a narrow swell: the shell refuses",
          f"{','.join(w[0] for w in fs['no_power']) or 'claims'}: m_along {fs['m_along'] / tr:.2f}x, band "
          f"{fs['band_along'][0] / tr:.2f}-{fs['band_along'][1] / tr:.2f}, |k| span x{fs['k_span']:.1f}, on {fs['score']:.2f} "
          f"drift {fs['drift_only']:.2f} null {fs['null']:.2f}")


def test_shuffled_frames_are_refused():
    S, t, rep = waves.synth(0.2, 2.0, U=(10, 0), N=N, n_frames=104, fps=26.0, seed=4)
    rng = np.random.default_rng(0)
    res = waves.measure_patch(S[rng.permutation(len(t))], t, None, n_shuffle=1)
    fs = res["shell"]
    check(bool(fs["no_power"]), "the frames shuffled in time: the shell refuses", ",".join(w[0] for w in fs["no_power"]))


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            print(name)
            fn()
    print(f"\n{'ALL PASS' if not FAIL else f'{len(FAIL)} FAILED: ' + ', '.join(FAIL)}")
    sys.exit(1 if FAIL else 0)
