"""The synthetic ladder for `mcdonald waves`: one synthetic sea per way the ruler could fail,
each measured by both estimators with their nulls, and a summary table of bias, band and refusals.

    python3 tools/waves_ladder.py --case 3 --out DIR      # one rung (a Slurm array task)
    python3 tools/waves_ladder.py --summary DIR           # the table over the JSONs there
    python3 tools/waves_ladder.py --list
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from mcdonald import waves  # noqa: E402

CASES = [
    # name, synth kwargs; the truth is m_x, q, U inside
    ("wind_still", dict(m_x=0.05, q=1.0, U=(0, 0))),
    ("wind_m025_U60", dict(m_x=0.025, q=1.0, U=(0, 60))),
    ("wind_m02_U40_20", dict(m_x=0.2, q=1.0, U=(40, 20))),
    ("wind_m06_U100", dict(m_x=0.6, q=1.0, U=(0, 100))),
    ("swell_only_1s", dict(m_x=0.2, q=1.0, U=(20, 10), spectrum="swell")),
    ("swell_wind_1s", dict(m_x=0.2, q=1.0, U=(20, 10), spectrum="both", swell_share=0.7)),
    ("affine_small", dict(m_x=0.2, q=1.0, U=(20, 0), affine=((0.05, 0), (0, 0.05)))),
    ("affine_large", dict(m_x=0.2, q=1.0, U=(20, 0), affine=((0.2, 0.1), (0.1, 0.2)))),
    ("rotation_2dps", dict(m_x=0.2, q=1.0, U=(10, 0), rot_deg_s=2.0)),
    ("oblique_q2", dict(m_x=0.2, q=2.0, U=(30, 0))),
    ("oblique_q2_persp", dict(m_x=0.2, q=2.0, U=(30, 0), persp=0.15)),
    ("nonlin_03", dict(m_x=0.2, q=1.0, U=(20, 10), nonlin=0.3)),
    ("nonlin_06", dict(m_x=0.2, q=1.0, U=(20, 10), nonlin=0.6)),
    ("repeats_jitter", dict(m_x=0.2, q=1.0, U=(20, 10), repeat=0.2, jitter=0.3)),
    ("pr149_like_4s", dict(m_x=0.2, q=2.1, U=(30, 5), n_frames=120, fps=30.0, repeat=0.2)),
    ("pr148_like_10s", dict(m_x=0.2, q=1.4, U=(1, -1), n_frames=300, fps=30.0, spectrum="both", swell_share=0.7, swell_m=12.0)),
    ("swell_only_10s", dict(m_x=0.2, q=1.0, U=(20, 10), n_frames=300, fps=30.0, spectrum="swell")),
    ("h264", dict(m_x=0.2, q=1.0, U=(20, 10), h264_kbps=630)),
    ("noise_1", dict(m_x=0.2, q=1.0, U=(20, 10), noise=1.0)),
    ("spread_5", dict(m_x=0.2, q=1.0, U=(20, 10), spread_deg=5.0)),
    ("spread_90_bothways", dict(m_x=0.2, q=1.0, U=(20, 10), spread_deg=90.0)),
    ("wind_still_q2_4s", dict(m_x=0.2, q=2.0, U=(0, 0), n_frames=120, fps=30.0)),
]


def h264_roundtrip(S, kbps, fps):
    """The frames through libx264 at kbps and back, as a sensor clip's codec would leave them."""
    n, H, W = S.shape
    g = np.clip(128 + 32 * S, 0, 255).astype(np.uint8)
    with tempfile.TemporaryDirectory(dir="/hugespace/local/tmp/waves") as d:
        mp4 = Path(d) / "s.mp4"
        p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
                            "-r", f"{fps}", "-i", "-", "-c:v", "libx264", "-b:v", f"{kbps}k", "-pix_fmt", "yuv420p",
                            "-g", "15", str(mp4)], input=g.tobytes(), capture_output=True)
        if p.returncode:
            raise RuntimeError(p.stderr.decode())
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                             capture_output=True, check=True).stdout
    back = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
    return (back - 128) / 32


HOLD, MARGIN = False, 48


def run_case(i, out):
    name, kw = CASES[i]
    kw = dict(kw)
    if HOLD:
        kw["N"] = kw.get("N", 384) + 2 * MARGIN
    kbps = kw.pop("h264_kbps", None)
    t0 = time.time()
    S, t, rep = waves.synth(**kw)
    if kbps:
        S = h264_roundtrip(S, kbps, kw.get("fps", 26.0))
    res = waves.measure_patch(S, t, rep, hold=HOLD, margin=MARGIN if HOLD else 0)
    truth = dict(m_x=kw["m_x"], q=kw.get("q", 1.0), U=list(kw.get("U", (0, 0))))
    rec = dict(case=i, name=name, kw={k: (list(v) if isinstance(v, tuple) else v) for k, v in kw.items()},
               truth=truth, seconds=time.time() - t0)
    for key in ("rates", "shell"):
        if key in res:
            r = {k: v for k, v in res[key].items() if k not in ("profile", "profile_free", "m_grid", "on", "pg")}
            r["profile"] = [float(x) for x in res[key]["profile"]] if "profile" in res[key] else None
            rec[key] = r
    rec["n_frames"], rec["span_s"], rec["n_bins"] = res["n_frames"], res["span_s"], res["n_bins"]
    rec["quadrants"], rec["hold"] = res.get("quadrants"), res.get("hold")
    Path(out).mkdir(parents=True, exist_ok=True)
    (Path(out) / f"{i:02d}_{name}.json").write_text(json.dumps(rec, indent=1, default=float))
    print(f"case {i} {name}: {rec['seconds']:.0f} s")
    for line in waves.said_patch(res, (truth["m_x"], truth["q"])):
        print(line)


def summary(out):
    rows = []
    for p in sorted(Path(out).glob("*.json")):
        r = json.loads(p.read_text())
        tm, tq, tU = r["truth"]["m_x"], r["truth"]["q"], r["truth"]["U"]
        fr, fs = r.get("rates", {}), r.get("shell", {})
        def rat(x):
            return f"{x / tm:.2f}" if x else "-"

        def along(f):
            th = f.get("theta_deg", f.get("dominant_deg"))
            if th is None or not f.get("m_along"):
                return "-"
            tr = 1.0 / np.sqrt(np.cos(np.radians(th)) ** 2 / tm ** 2 + np.sin(np.radians(th)) ** 2 / (tm * tq) ** 2)
            return f"{f['m_along'] / tr:.2f}"
        rows.append((r["name"], r["n_frames"], f"{r['span_s']:.1f}",
                     rat(fr.get("m")) if fr.get("ok") else "nofit", along(fr) if fr.get("ok") else "-",
                     (f"{fr['band_m'][0] / tm:.2f}-{fr['band_m'][1] / tm:.2f}" + ("o" if fr.get("band_open") else "")) if fr.get("ok") else "-",
                     f"{fr.get('explained', float('nan')):.2f}/{fr.get('drift_only', float('nan')):.2f}/{fr.get('null_explained', float('nan')):.2f}" if fr.get("ok") else "-",
                     (",".join(w[0] for w in fr.get("no_power", [])) or "claims") if fr.get("ok") else "-",
                     f"{fr['q']:.2f}/({fr['U'][0]:.0f},{fr['U'][1]:.0f})" if fr.get("ok") else "-",
                     rat(fs.get("m")), along(fs),
                     f"{fs['band_m'][0] / tm:.2f}-{fs['band_m'][1] / tm:.2f}" + ("o" if fs.get("band_open") else ""),
                     f"{fs['q']:.2f}/{tq:.2f}",
                     f"({fs['U'][0]:.0f},{fs['U'][1]:.0f})/({tU[0]:.0f},{tU[1]:.0f})",
                     f"{fs['score']:.2f}/{fs['drift_only']:.2f}/{fs['null']:.2f}",
                     f"x{fs['k_span']:.1f}",
                     ",".join(w[0] for w in fs["no_power"]) or "claims"))
    hdr = ("case", "n", "T s", "rates m/true", "along", "rates band", "expl/drift/null", "rates verdict", "rates q/U", "shell m/true", "along", "shell band", "q/true", "U/true",
           "on/drift/null", "k span", "shell verdict")
    print("| " + " | ".join(hdr) + " |")
    print("|" + "---|" * len(hdr))
    for row in rows:
        print("| " + " | ".join(str(x) for x in row) + " |")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", type=int)
    ap.add_argument("--out", default="/hugespace/local/tmp/waves/ladder")
    ap.add_argument("--summary", metavar="DIR")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--hold", action="store_true", help="hold the sea (affine registration) before measuring")
    a = ap.parse_args()
    HOLD = a.hold
    if a.list:
        for i, (n, kw) in enumerate(CASES):
            print(i, n, kw)
    elif a.summary:
        summary(a.summary)
    else:
        run_case(a.case, a.out)
