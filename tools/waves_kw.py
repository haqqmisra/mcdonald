"""Look at the sea's (k, omega) spectrum before fitting anything: the periodogram of every bin
within +-SLICE deg of the texture's dominant direction, binned by |k|, as an image, with the
deep-water dispersion curve for a known scale drawn over it (at zero drift and at the drift
the patch's phase correlation reads). The same for the direction square to it.

    python3 tools/waves_kw.py VIDEO --n0 1 --n1 130 --patch X0,Y0,N --truth M,Q --out PNG
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from mcdonald import waves  # noqa: E402
from mcdonald.figures import setup, save  # noqa: E402

SLICE = 20.0


def phase_corr_drift(S, t):
    """Mean translation of the texture (px/s) between consecutive frames, by phase correlation."""
    n, N, _ = S.shape
    win = np.outer(np.hanning(N), np.hanning(N))
    F = [np.fft.fft2((s - s.mean()) * win) for s in S]
    vs = []
    for i in range(n - 1):
        X = F[i + 1] * np.conj(F[i])
        c = np.real(np.fft.ifft2(X / (np.abs(X) + 1e-6 * np.abs(X).max())))
        c = np.fft.fftshift(c)
        iy, ix = np.unravel_index(np.argmax(c), c.shape)
        vs.append(((ix - N // 2) / (t[i + 1] - t[i]), (iy - N // 2) / (t[i + 1] - t[i])))
    return np.median(np.array(vs), 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--n0", type=int, default=1)
    ap.add_argument("--n1", type=int, required=True)
    ap.add_argument("--patch", required=True)
    ap.add_argument("--truth")
    ap.add_argument("--lam-min", type=float, default=6.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hold", action="store_true")
    a = ap.parse_args()
    x0, y0, N = (int(v) for v in a.patch.split(","))
    import subprocess
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                          "-of", "csv=p=0", a.video], capture_output=True, text=True).stdout.strip().split(",")
    W, H = int(out[0]), int(out[1])
    num, den = out[2].split("/")
    fps = int(num) / int(den)
    S = []
    for n, f in waves.stream_grey(a.video, a.n0, a.n1, W, H):
        S.append(f[y0:y0 + N, x0:x0 + N].astype(np.float32))
    S = np.array(S)
    frames = np.arange(a.n0, a.n0 + len(S))
    rep = waves.repeats_of({0: S})
    S = S[~rep]
    t = (frames[~rep] - 1) / fps
    S = waves.detrended(S, t)
    if a.hold:
        S, held = waves.hold_sea(S, t)
        print(f"held: drift {held['drift_px_s']} px/s, gradient rms {held['gradient_rms_per_s']:.3f}/s, peak {held['peak']:.2f}")
        S = waves.detrended(S, t)
    U_reg = phase_corr_drift(S, t)
    print(f"{len(S)} new frames over {t[-1] - t[0]:.2f} s; phase-correlation drift ({U_reg[0]:.1f}, {U_reg[1]:.1f}) px/s")
    b = waves.bins_of(S, a.lam_min, N / 3.0, top=1.0, t=t)
    ang = np.arctan2(b.ky, b.kx)
    th0 = 0.5 * np.angle(np.sum(b.amp ** 2 * np.exp(2j * ang)))
    print(f"dominant direction (axial) {np.degrees(th0):.0f} deg from +x")
    nu, E, share, Wfun = waves.periodogram(b, t)
    rate, coh = waves.phase_rates(b, t)
    truth = tuple(float(v) for v in a.truth.split(",")) if a.truth else None
    plt = setup(9)
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), constrained_layout=True)
    edges = np.exp(np.linspace(np.log(2 * np.pi / (N / 3.0)), np.log(2 * np.pi / a.lam_min), 25))
    kc = np.sqrt(edges[:-1] * edges[1:])
    for row, (th, lab) in enumerate(((th0, "along the dominant direction"), (th0 + np.pi / 2, "square to it"))):
        d = (ang - th + np.pi / 2) % np.pi - np.pi / 2
        sel = np.abs(d) < np.radians(SLICE)
        # the slice's bins, signed by the side of th they lie on (so the branches do not fold)
        side = np.sign(np.cos(ang - th))
        img = np.full((len(kc), len(nu)), np.nan)
        for i, (lo, hi) in enumerate(zip(edges[:-1], edges[1:])):
            m_ = sel & (b.k >= lo) & (b.k < hi)
            if m_.sum() >= 2:
                # fold the bins on the far side: their rate is the mirror (conjugate), nu -> -nu
                rows = np.where(side[m_][:, None] > 0, share[m_], share[m_][:, ::-1])
                img[i] = (rows * (b.amp[m_] ** 2)[:, None]).sum(0) / (b.amp[m_] ** 2).sum()
        ax = axes[row, 0]
        pc = ax.pcolormesh(nu, kc, np.nan_to_num(img), cmap="magma", shading="nearest", vmin=0, vmax=np.nanmax(img))
        fig.colorbar(pc, ax=ax, fraction=0.04, pad=0.02).set_label("Energy Share", fontweight="bold")
        if truth:
            m, q = truth
            kk = np.linspace(kc.min(), kc.max(), 200)
            K = np.hypot(kk * np.cos(th) / m, kk * np.sin(th) / (m * q))
            Om = np.sqrt(waves.G * K)
            kU = kk * (np.cos(th) * U_reg[0] + np.sin(th) * U_reg[1])
            ax.plot(-Om, kk, color="C0", lw=1.2, label="Known Scale, No Drift")
            ax.plot(Om, kk, color="C0", lw=1.2, ls="--")
            ax.plot(-Om - kU, kk, color="C2", lw=1.2, label="Known Scale + Measured Drift")
            ax.plot(Om - kU, kk, color="C2", lw=1.2, ls="--")
            ax.plot(-kU, kk, color="w", lw=0.8, ls=":", label="Drift Alone")
            ax.legend(loc="upper right", fontsize=7)
        ax.set_yscale("log")
        ax.set_xlim(-30, 30)
        ax.set_xlabel("Rate (rad/s)", fontweight="bold")
        ax.set_ylabel("|k| (rad/px)", fontweight="bold")
        ax.set_title(f"Periodogram {lab} ({np.degrees(th) % 180:.0f} deg)", fontweight="bold", fontsize=9)
        ax2 = axes[row, 1]
        r_ = np.where(side[sel] > 0, rate[sel], -rate[sel])
        sc = ax2.scatter(r_, b.k[sel], c=coh[sel], s=5, cmap="viridis", vmin=0, vmax=1)
        fig.colorbar(sc, ax=ax2, fraction=0.04, pad=0.02).set_label("Coherence", fontweight="bold")
        if truth:
            ax2.plot(-Om - kU, kk, color="C2", lw=1.2)
            ax2.plot(Om - kU, kk, color="C2", lw=1.2, ls="--")
            ax2.plot(-kU, kk, color="k", lw=0.8, ls=":")
        ax2.set_yscale("log")
        ax2.set_xlim(-30, 30)
        ax2.set_xlabel("Phase Rate (rad/s)", fontweight="bold")
        ax2.set_ylabel("|k| (rad/px)", fontweight="bold")
        ax2.set_title(f"Per-Bin Rates {lab}; median coherence {np.median(coh[sel]):.2f}", fontweight="bold", fontsize=9)
    fig.suptitle(f"{Path(a.video).stem} frames {a.n0}-{a.n1}, patch x{x0} y{y0} N{N}: drift ({U_reg[0]:.1f}, {U_reg[1]:.1f}) px/s",
                 fontweight="bold")
    save(fig, a.out, dpi=110)


if __name__ == "__main__":
    main()
