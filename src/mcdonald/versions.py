"""`mcdonald versions` — several copies of one clip, set side by side: which keeps the most of the recording, where
they differ in their frames, and what each one's container says about it.

A released clip is rarely the recording. It is a copy of a copy, each re-encoded, and the copies differ in ways that
change measurements. The Navy's 2004 FLIR1 has three in circulation (2026-10-20): a 2007 leak (an MPEG-1 VCD file),
the official 2020 release on DVIDS (which AARO shows, also as a 1920 x 1080 upscale), and a Wikimedia Commons
re-encode of that. The official file is a low-bitrate H.264 that holds 24 % of its 8 x 8 blocks still from one frame to
the next (the 2007 copy: 7 %) and keeps 0.65 of the 2007 copy's fine detail; it was relabelled from 29.97 to 30 frames
a second without being resampled, and it repeats a frame twice (at 985 and 1986). A track or a flicker measured on
it measures the encoder.

For each copy: its container's word (codec, size, frame rate as an exact fraction, frame count, bit rate); its frames
decoded to one raster (the smallest copy's, so that no copy is credited with detail an upscale invented) and, frame by
frame, the picture's mean level in the middle of the frame, how much it changed from the frame before, and its fine
detail (the rms of a Laplacian). From those:

- **lag and drift** against the first copy: the shift that best lines up the frame-to-frame changes of the two, over
  the whole clip and in windows -- a copy that drops or repeats a frame somewhere shifts by one there;
- **held frames**: frames that barely differ from the one before, where the copy's neighbours do; runs held in every
  copy belong to the recording (FLIR1's 1232-1235, its switch from the television camera to the infrared), runs held
  in one copy only belong to that copy's encoder;
- **detail kept**: each copy's median fine detail, against the best copy's;
- **the frame rate**: a copy whose header gives a different rate for the same frames was relabelled, not resampled.

The best source is the copy with the most detail and the fewest held frames of its own; the report says which, and
why. What this cannot do: find a copy nobody has; say which copy is nearest the recording when all are re-encodes of
one lost file (it says which keeps most); or line up copies cut to different parts of the recording with no overlap.
"""
import csv
import json
import subprocess
from pathlib import Path

import numpy as np
from scipy import ndimage

from . import clip as vclip
from .report import Found

MAX_W = 480            # px: the common raster is at most this wide (the smallest copy's, or narrower)
MAX_LAG = 90           # frames either way a copy may be shifted against the first
WINDOW = 300           # frames: the lag is found again in windows this long, to see it drift
HELD_SHARE = 0.2       # a frame that changes less than this share of its neighbours' change is held
HELD_FLOOR = 0.35      # DN: and less than this in all
STILL_DN = 0.25        # DN: an 8 x 8 block whose mean |change| from the frame before is under this was held by the encoder
GOOD_R = 0.8           # a window whose frame-to-frame changes line up this well or better is trusted for the lag


def raster(infos):
    """The common raster (w, h): the smallest copy's frame, no wider than MAX_W, even sides."""
    w, h = min((i["width"], i["height"]) for i in infos)
    if w > MAX_W:
        h, w = int(round(h * MAX_W / w)), MAX_W
    return max(2, w // 2 * 2), max(2, h // 2 * 2)


def series(video, w, h, every_frame=None):
    """Frame by frame, decoded to w x h grey: (the middle's mean level, its mean |change| from the frame before, its fine
    detail, the share of its 8 x 8 blocks that did not change). Streamed through ffmpeg, a few frames at a time, so that
    a long clip is never held in memory."""
    opts = every_frame or vclip.every_frame()
    cmd = ["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:v:0", "-vf", f"scale={w}:{h}:flags=area", *opts,
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    y0, y1, x0, x1 = h // 7, 6 * h // 7, w // 9, 8 * w // 9
    size, prev, rows = w * h, None, []
    try:
        while True:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            g = np.frombuffer(buf, np.uint8).reshape(h, w).astype(np.float32)[y0:y1, x0:x1]
            lap = g - 0.25 * (np.roll(g, 1, 0) + np.roll(g, -1, 0) + np.roll(g, 1, 1) + np.roll(g, -1, 1))
            still = np.nan
            if prev is not None:
                d = np.abs(g - prev)
                bh, bw = d.shape[0] // 8, d.shape[1] // 8
                still = float((d[:bh * 8, :bw * 8].reshape(bh, 8, bw, 8).mean(axis=(1, 3)) < STILL_DN).mean())
            rows.append((float(g.mean()), np.nan if prev is None else float(np.abs(g - prev).mean()),
                         float(np.sqrt((lap[2:-2, 2:-2] ** 2).mean())), still))
            prev = g
    finally:
        p.stdout.close()
        p.wait()
    return np.array(rows, float).reshape(-1, 4)


def best_lag(ref, s, max_lag=MAX_LAG):
    """(lag, r): the shift of `s` against `ref` (both mean-level series) that best correlates their frame-to-frame
    changes; s[i + lag] lines up with ref[i]."""
    a, b = np.diff(ref), np.diff(s)
    best = (0, -np.inf)
    for lag in range(-max_lag, max_lag + 1):
        i0, j0 = max(0, -lag), max(0, lag)
        n = min(len(a) - i0, len(b) - j0)
        if n < 30:
            continue
        x, y = a[i0:i0 + n], b[j0:j0 + n]
        if x.std() == 0 or y.std() == 0:
            continue
        r = float(np.corrcoef(x, y)[0, 1])
        if r > best[1]:
            best = (lag, r)
    return best


def drift(ref, s, lag, window=WINDOW):
    """The lag found again in windows along the first copy: [(first frame, last frame, lag, r)], from 1, the windows
    WINDOW frames long (a quarter of a shorter clip, at least 60) and half overlapping. A copy that drops or repeats a
    frame shifts there."""
    window = min(window, max(60, len(ref) // 4))
    out = []
    for a in range(0, len(ref) - window // 2, window // 2):
        b = min(len(ref), a + window)
        lo, hi = max(0, a + lag - 15), min(len(s), b + lag + 15)
        if hi - lo < b - a or b - a < 60:
            continue
        sub_ref, sub_s = ref[a:b], s[lo:hi]
        best = (None, -np.inf)
        for k in range(0, hi - lo - (b - a) + 1):
            x, y = np.diff(sub_ref), np.diff(sub_s[k:k + (b - a)])
            if x.std() == 0 or y.std() == 0:
                continue
            r = float(np.corrcoef(x, y)[0, 1])
            if r > best[1]:
                best = (lo + k - a, r)
        if best[0] is not None:
            out.append((a + 1, b, int(best[0]), round(best[1], 3)))
    return out


def lag_at(c, i):
    """A copy's lag at the first copy's frame i (from 1): its window's (the nearest window's middle), else its lag over
    the whole clip."""
    good = [w for w in (c.get("drift") or []) if w[3] >= GOOD_R]
    if not good:
        return c["lag"]
    return min(good, key=lambda d: abs(0.5 * (d[0] + d[1]) - i))[2]


def lag_steps(c, ref=None, s=None):
    """Where a copy's lag steps, from its windows that line up well (r >= GOOD_R): [{near, by, what}]. s[i + lag] lines
    up with the first copy's frame i, so a lag that grows is a frame the copy repeats or inserts there, and one that
    falls a frame it dropped. A window that lines up poorly (a fade, a window astride the step) is left out: FLIR1's first
    and last made five and four frames "dropped" that the others did not. With the two copies' level series (`ref`,
    `s`), the step is then placed to the frame between the good windows either side (`locate`)."""
    out, d = [], [w for w in (c.get("drift") or []) if w[3] >= GOOD_R]
    for a, b in zip(d, d[1:]):
        if b[2] != a[2]:
            near = int(round(0.5 * (a[0] + a[1] + b[0] + b[1]) / 2))
            if ref is not None and s is not None:
                near = locate(ref, s, a[0] + (a[1] - a[0]) // 2, b[0] + (b[1] - b[0]) // 2, a[2], b[2]) or near
            by = b[2] - a[2]
            out.append(dict(near=near, by=int(by), what=(f"{'a frame' if abs(by) == 1 else f'{abs(by)} frames'} "
                                                        + ("repeated or inserted" if by > 0 else "dropped"))))
    return out


def locate(ref, s, i0, i1, l1, l2):
    """The first copy's frame (from 1) between i0 and i1 where the copy's lag goes from l1 to l2: the split that best
    has each frame's change of level matched by the copy's at l1 before it and at l2 after (each series in its own
    standard deviations, as the copies' gains differ). None where the frames between give nothing to split on."""
    da, db = np.diff(ref), np.diff(s)
    da, db = da / (np.nanstd(da) or 1.0), db / (np.nanstd(db) or 1.0)
    idx = [i for i in range(i0, i1) if 0 <= i + l1 < len(db) and 0 <= i + l2 < len(db) and i < len(da)]
    if len(idx) < 10:
        return None
    m1 = np.nan_to_num(np.abs(np.array([da[i] - db[i + l1] for i in idx])))
    m2 = np.nan_to_num(np.abs(np.array([da[i] - db[i + l2] for i in idx])))
    cost = [m1[:j].sum() + m2[j:].sum() for j in range(len(idx) + 1)]
    j = int(np.argmin(cost))
    return int(idx[min(j, len(idx) - 1)]) + 1


def held(diff):
    """Frames (from 1) that barely differ from the one before, where their neighbours do."""
    d = np.asarray(diff, float)
    loc = ndimage.median_filter(np.nan_to_num(d, nan=np.nanmedian(d)), size=21, mode="nearest")
    return [int(i) + 1 for i in np.flatnonzero((d < HELD_SHARE * loc) & (d < HELD_FLOOR))]


def runs(frames):
    """[n, n+1, n+2, m] -> [(n, n+2), (m, m)]."""
    out = []
    for f in frames:
        if out and f == out[-1][1] + 1:
            out[-1][1] = f
        else:
            out.append([f, f])
    return [tuple(r) for r in out]


def compare(videos, names=None, out=None, tag="versions", progress=None):
    """Several copies of a clip, the first the one the others are set against. A Found."""
    videos = [Path(v) for v in videos]
    names = list(names or []) + [v.name for v in videos[len(names or []):]]
    infos = [vclip.probe(v) for v in videos]
    w, h = raster(infos)
    S = []
    for i, v in enumerate(videos):
        if progress:
            progress("Versions", i, len(videos))
        S.append(series(v, w, h))
    copies = []
    for v, nm, info, s in zip(videos, names, infos, S):
        st = info["stream"]
        num = lambda x: int(x) if str(x or "").isdigit() else None
        copies.append(dict(name=nm, file=str(v), codec=st.get("codec_name"), width=info["width"], height=info["height"],
                           fps=str(info["fps"]), fps_note=info["fps_note"], frames_in_header=info["nb_frames"] or None,
                           frames_decoded=int(len(s)), bit_rate=num(st.get("bit_rate")) or num(info["format"].get("bit_rate")),
                           detail=float(np.median(s[:, 2])) if len(s) else None,
                           still=float(np.nanmedian(s[:, 3])) if len(s) > 1 else None,
                           held=held(s[:, 1]) if len(s) else []))
    ref = S[0][:, 0]
    for c, s in zip(copies, S):
        lag, r = best_lag(ref, s[:, 0]) if len(s) else (0, np.nan)
        c.update(lag=int(lag), r=round(float(r), 4), drift=drift(ref, s[:, 0], lag) if len(s) else [])
        c["lag_steps"] = lag_steps(c, ref, s[:, 0]) if c is not copies[0] and len(s) else []
        c["held_runs"] = runs(c["held"])
    # held in every copy (at the same place in the first copy's frames) belongs to the recording
    in_ref = lambda c, f: f - lag_at(c, f)               # a copy's frame f is the first copy's frame f - lag there
    sets = [set(in_ref(c, f) for f in c["held"]) for c in copies]
    common = sorted(set.intersection(*sets)) if sets else []
    for c, s_ in zip(copies, sets):
        c["held_own"] = len(s_ - set(common))
    best_detail = max(c["detail"] or 0 for c in copies) or 1.0
    for c in copies:
        c["detail_share"] = round((c["detail"] or 0) / best_detail, 3)
    best = max(copies, key=lambda c: (c["detail_share"] - 0.002 * c["held_own"]))
    rate = {}
    for c in copies:
        rate.setdefault(c["fps"], []).append(c["name"])
    res, notes = {}, []
    res["raster"] = f"{w}x{h} for every copy (the smallest's, at most {MAX_W} wide)"
    for c in copies:
        res[c["name"]] = (f"{c['codec']} {c['width']}x{c['height']} at {c['fps']}, {c['frames_decoded']} frames"
                          + (f" ({c['bit_rate'] // 1000} kb/s)" if c["bit_rate"] else "")
                          + f"; detail {c['detail_share']:.2f} of the best; {100 * (c['still'] or 0):.0f} % of its "
                          f"blocks held from frame to frame; {len(c['held'])} held frames, {c['held_own']} of them its "
                          "own" + ("" if c is copies[0] else
                                                               f"; lag {c['lag']:+d} against {copies[0]['name']} "
                                                               f"(r {c['r']:.2f})")
                          + ("; " + ", ".join(f"{x['what']} near frame {x['near']}" for x in c["lag_steps"])
                             if c["lag_steps"] else ""))
    res["held in every copy"] = (", ".join(f"{a}-{b}" if a != b else f"{a}" for a, b in runs(common))
                                 + " (frames of the first copy): the recording's own" if common else "none")
    res["best source"] = (f"{best['name']}: {best['detail_share']:.2f} of the detail and {best['held_own']} held frames "
                          "of its own")
    if len(rate) > 1:
        lens = {c["name"]: c["frames_decoded"] for c in copies}
        notes.append("The copies' headers give different frame rates (" + "; ".join(f"{k}: {', '.join(v)}" for k, v in rate.items())
                     + ") for the same frames (" + ", ".join(f"{k} {v}" for k, v in lens.items()) + "): a copy was "
                     "relabelled, not resampled, and its times are off by the ratio.")
    weak = [c["name"] for c in copies if c["detail_share"] < 0.75]
    if weak:
        notes.append(f"{', '.join(weak)} keep{'s' if len(weak) == 1 else ''} under three quarters of the best copy's fine "
                     "detail: measure on the best copy.")
    fields = dict(raster=[w, h], copies=copies, held_in_every_copy=common, best=best["name"])
    files = write(out, tag, fields, S) if out else []
    return Found("versions", res, fields, files=files, notes=notes)


def write(out, tag, fields, S):
    """<out>_versions.json and <out>_versions.csv (frame by frame, each copy lined up on the first's frames)."""
    j = Path(f"{out}_versions.json")
    j.write_text(json.dumps(fields, indent=1, default=str), encoding="utf-8")
    c = Path(f"{out}_versions.csv")
    with open(c, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["frame"] + [f"{cp['name']}_{k}" for cp in fields["copies"] for k in ("level", "change", "detail")])
        for i in range(len(S[0])):
            row = [i + 1]
            for cp, s in zip(fields["copies"], S):
                k = i + lag_at(cp, i + 1)
                row += [f"{v:.3f}" for v in s[k][:3]] if 0 <= k < len(s) else ["", "", ""]
            wr.writerow(row)
    return [str(j), str(c)]


def said(fields):
    L = []
    for c in fields["copies"]:
        L.append(f"{c['name']}: {c['codec']} {c['width']}x{c['height']}, {c['fps']} fps, {c['frames_decoded']} frames; "
                 f"detail {c['detail_share']:.2f}; blocks held {100 * (c['still'] or 0):.0f} %; held frames "
                 f"{len(c['held'])} ({c['held_own']} its own)"
                 + ("" if c is fields["copies"][0] else f"; lag {c['lag']:+d} (r {c['r']:.2f})"))
    L.append(f"best source: {fields['best']}")
    return L


def main():
    import argparse
    from . import forensics as vf
    from .report import emit, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("videos", nargs="+", help="two or more copies of one clip; the first is the one the others are set against")
    ap.add_argument("--names", help="a short name for each copy, comma separated (default: the file names)")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true", help="print the measurement as JSON on stdout")
    args = ap.parse_args()
    if len(args.videos) < 2:
        ap.error("give two or more copies")
    with said_to_stderr(args.json) as lines:
        paths, tag = [], None
        for v in args.videos:
            p, t, _ = vf.resolve(v)
            paths.append(p)
            tag = tag or t
        out = vclip.out_prefix(args.out, tag)
        found = compare(paths, args.names.split(",") if args.names else None, out=out, tag=tag)
        print("\n".join(said(found.fields)))
        for n in found.notes:
            print(n)
        for f in found.files:
            print(f"wrote {f}")
    if args.json:
        emit(found.envelope("versions", inputs_of(args), None, said=lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
