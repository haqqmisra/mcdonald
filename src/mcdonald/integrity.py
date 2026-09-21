#!/usr/bin/env python3
"""Has a clip been altered -- and was the object in it added afterwards?

  video_integrity.py VIDEO|ID [--track CSV | --auto-track] [options]

Pixel forensics cannot prove a clip genuine. It can show whether the clip, and
the object, behave like the output of one sensor chain, and it can catch an
object pasted, AI-inserted or animated onto footage that already existed. What
it cannot exclude is a composite made upstream of the symbology by someone who
modelled exposure, shake, gain and parallax; that is a custody question.

WHAT THE RECORD SAYS   the release's own alteration / recreation disclosure, the
                       catalog base rate, the container (encoder, dates, GOP)
IS THE CLIP A SENSOR'S repeated frames and their catch-up steps; contrast
                       transients (flat fields, gain resets, zoom blanks) and the
                       zoom ratio across them; a static detector pattern; rigid
                       scene motion in one or two layers. Generated video has none.
WAS THE OBJECT ADDED   (needs a track) each asks: imagery, or something laid over it?
  cadence      frozen on repeated frames, doubled on catch-up steps
  transient    attenuated with the scene while the symbology is not
  layer order  under the symbology it crosses; enters from under a block or
               at the frame edge rather than appearing in the open
  smear        stretched along its screen velocity in proportion to its speed
  shake        its screen acceleration follows the background's, unit slope
  halo         the sharpening ring deepens with its amplitude
  pattern      the detector's static pattern continues under its footprint
SELF-TEST              a synthetic disc, animated on a smooth path over the same
                       frames, goes through the same tests. It should fail them.
                       That is what gives a PASS its meaning on this clip.

Each test reports PASS (behaves as imagery), FLAG (behaves as an overlay),
INCONCLUSIVE, or NO POWER (the clip cannot decide it; say so, do not drop it).
Writes <tag>_integrity_report.{md,json,png} into the case directory
(--out DIR; default ./<tag>).
First worked on DOW-UAP-PR144 (U.S. DoW PURSUE release 06); docs/method.md gives
the method, the traps and the validation record.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.signal import fftconvolve

from . import catalog, forensics as vf
from .progress import to_stderr
from .report import Found, emit, inputs_of, plain, said_to_stderr

_G = {}
PASS, FLAG, INC, NOP = "PASS", "FLAG", "INCONCLUSIVE", "NO POWER"


# ---- the record and the container ---------------------------------------------------------
def record_report(rec):
    """What the releasing body said, if this clip came from a catalog.

    A clip with no catalog record gets no provenance section at all. The point
    is not tidiness: the disclosure rate ("n of m videos carry an alteration
    statement") describes one release, and printing it beside someone else's
    clip would attach a statistic to imagery it says nothing about."""
    cat = catalog.active()
    out = {"catalog": cat.name}
    if isinstance(cat, catalog.NullCatalog):
        return out
    flagged, total = cat.disclosure_rate()
    out.update(catalog_videos=total, catalog_with_disclosure=flagged)
    if rec:
        out.update(title=rec.get("title"), release=rec.get("release"),
                   redacted=rec.get("redacted"), disclosure=cat.disclosure(rec))
    return out


def container_report(clip):
    fmt, st = clip.info["format"], clip.info["stream"]
    fr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                         "frame=key_frame,pict_type,pkt_size", "-of", "csv=p=0", str(clip.video)],
                        capture_output=True, text=True).stdout.split()
    types = [f.split(",") for f in fr]
    keys = [i + 1 for i, f in enumerate(types) if f[0] == "1"]
    sizes = {t: int(np.mean([int(f[1]) for f in types if f[2] == t])) for t in "IPB" if any(f[2] == t for f in types)}
    enc = sorted(set(re.findall(rb"(Elemental[ \w.()]+|x264 - core \d+|Lavf[\d.]+|Lavc[\d.]+ \w+|HandBrake [\d.]+|"
                                rb"Adobe [\w ]+|DaVinci Resolve[\w .]*)", open(clip.video, "rb").read(4_000_000))))
    return {"format_tags": fmt.get("tags", {}), "video_tags": st.get("tags", {}), "codec": st.get("codec_name"),
            "bit_rate": int(fmt.get("bit_rate", 0)), "keyframes": keys[:40], "mean_bytes": sizes,
            "encoder_strings": [e.decode(errors="replace") for e in enc],
            "other_streams": [s["codec_name"] for s in clip.info["streams"] if s["codec_type"] != "video"]}


# ---- scene motion, every frame pair ----------------------------------------------------------
def _init(video, workdir, n0, n1, masks, rows, trk, reach, zero):
    masks = {k: v for k, v in masks.items() if k in ("blocks", "graphics", "colour")}
    _G.update(clip=vf.Clip(video, workdir, n0, n1), masks=masks, rows=rows, reach=reach, zero=zero,
              pos=vf.interp_track(trk) if trk else None)


def _bad(n):
    clip = _G["clip"]
    rgb = clip.rgb(n)
    bad = vf.frame_mask(rgb, _G["masks"], _G["rows"], n)
    if _G["pos"]:
        cx, cy = _G["pos"](n)
        yy, xx = np.ogrid[:clip.H, :clip.W]
        bad = bad | ((xx - cx) ** 2 + (yy - cy) ** 2 < 28 ** 2)
    return rgb.mean(2), bad


def _pair1(a):
    ga, ba = _bad(a)
    gb, bb = _bad(a + 1)
    lay = vf.layers_of(vf.shift_field(ga, gb, ba, bb, a=a, stride=192, reach=_G["reach"], zero=_G["zero"]), minn=5)
    return a, {c: lay[c] for c in ("striated", "isotropic", "all")}


def _pair5(a):
    ga, ba = _bad(a)
    gb, bb = _bad(a + 5)
    f, still = vf.shift_field_auto(ga, gb, ba, bb, a=a, stride=144, reach=5 * _G["reach"])
    lay = vf.layers_of(f)
    return a, lay["inliers"], lay["groups"], lay.get("group_gap", 0.0), lay["n_good"], lay["n_tpl"], float(still)


def per_frame_background(clip, masks, rows, trk, reps, procs=10, max_shift=45.0, progress=None, stop=None):
    """{n: (shift n -> n+1, class)}, one texture class preferred throughout so
    that consecutive pairs refer to the same layer."""
    def run(zero, what):
        return dict(vf.pooled(procs, _pair1, [n for n in range(clip.n0, clip.n1) if n + 1 not in reps], _init,
                              (clip.video, clip.dir, clip.n0, clip.n1, masks, rows, trk, int(max_shift) + 20, zero),
                              8, progress, stop, what))
    res, note = run(2, "per-frame background: frame pairs"), ""
    if np.mean([r["all"] is not None for r in res.values()]) < 0.3:
        res = run(-1, "per-frame background, again with zero shift allowed (the scene is nearly still): frame pairs")
        note = "scene nearly still on screen: zero shift allowed, so a static pattern could lock the estimate"
    count = {c: sum(r[c] is not None for r in res.values()) for c in ("striated", "isotropic")}
    first = max(count, key=count.get)
    bg = {}
    for n, r in res.items():
        for c in (first, "isotropic" if first == "striated" else "striated", "all"):
            if r[c] is not None:
                bg[n] = (r[c][0], c)
                break
    for n in reps:
        bg[n - 1] = (np.zeros(2), "repeat")
    return bg, note


def double_steps(bg):
    sp = {n: float(np.hypot(*v)) for n, (v, c) in bg.items() if c != "repeat"}
    out = []
    for n in sorted(sp):
        nb = [sp[m] for m in range(n - 6, n + 7) if m in sp and m != n and bg[m][1] == bg[n][1]]
        if len(nb) >= 6 and sp[n] > 8 and 1.7 < sp[n] / np.median(nb) < 2.3:
            out.append(n)
    return out


# ---- the object ----------------------------------------------------------------------------
class Obj:
    """The object as the tests see it: a clip (real or with a synthetic insert),
    a track, and its polarity."""

    def __init__(self, clip, trk, size, dark):
        self.clip, self.trk, self.size, self.dark = clip, trk, size, dark
        self.pos = vf.interp_track(trk)

    def img(self, n):
        g = self.clip.grey(n)
        return 255.0 - g if self.dark else g

    def cut(self, n, r, centre=None):
        cx, cy = centre or self.trk[n]
        xi, yi = int(round(cx)), int(round(cy))
        if yi < r or xi < r or yi > self.clip.H - r - 1 or xi > self.clip.W - r - 1:
            return None
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        return self.img(n)[yi - r:yi + r + 1, xi - r:xi + r + 1], np.hypot(xx - (cx - xi), yy - (cy - yi)), xx - (cx - xi), yy - (cy - yi)


def t_cadence(o, reps, dbl, bg):
    d = [np.hypot(o.trk[n][0] - o.trk[n - 1][0], o.trk[n][1] - o.trk[n - 1][1]) for n in reps if n in o.trk and n - 1 in o.trk]
    if len(d) < 5:
        return NOP, f"{len(d)} repeated frames inside the track", {}
    rel = lambda m: np.hypot(*(np.array(o.trk[m + 1]) - np.array(o.trk[m]) - bg[m][0]))
    ratios = []
    for n in dbl:
        nbr = [rel(m) for m in range(n - 5, n + 6) if m != n and m not in dbl and m in bg and bg[m][1] == bg[n][1]
               and m in o.trk and m + 1 in o.trk]
        if n in o.trk and n + 1 in o.trk and len(nbr) >= 4 and np.median(nbr) > 2:
            ratios.append(rel(n) / np.median(nbr))
    med = float(np.median(d))
    txt = f"moves {med:.3f} px across {len(d)} repeated frames (max {max(d):.2f})"
    if ratios:
        txt += f"; on {len(ratios)} catch-up steps its step against the background is {np.median(ratios):.2f}x its neighbours'"
    ok = med < 0.2 and (len(ratios) < 10 or 1.5 < np.median(ratios) < 2.5)
    return (PASS if ok else FLAG if med > 0.5 else INC), txt, {"repeat_disp": med, "double_ratio": float(np.median(ratios)) if ratios else None}


def t_transient(o, runs, masks, rows, max_shift):
    bp = lambda g: ndimage.gaussian_filter(g, 2.0) - ndimage.gaussian_filter(g, 25.0)
    clip, res = o.clip, []
    H, W = clip.H, clip.W
    for a, b in runs:
        if not (min(o.trk) < a and b < max(o.trk)) or a - 1 not in o.trk:
            continue
        c0 = o.cut(a - 1, 40)
        if c0 is None:
            continue
        amp0 = c0[0][c0[1] <= 3].max() - np.median(c0[0])
        g0 = clip.grey(a - 1)
        h0 = bp(g0)
        h0[vf.frame_mask(clip.rgb(a - 1), masks, rows, a - 1, grow=6)] = 0
        t = h0[int(.28 * H):int(.74 * H), int(.26 * W):int(.73 * W)]
        after = min(n for n in o.trk if n > b)
        for n in range(a, b + 1):
            m = min(int(max_shift * (n - a + 1) + 30), int(.24 * W))
            my = min(m, int(.24 * H))
            h = bp(clip.grey(n))
            h[vf.frame_mask(clip.rgb(n), masks, rows, n, grow=6)] = 0
            img = h[int(.28 * H) - my:int(.74 * H) + my, int(.26 * W) - m:int(.73 * W) + m]
            num = fftconvolve(img, t[::-1, ::-1], mode="valid")
            e = np.sqrt(np.maximum(vf.boxsum(img * img, *t.shape), 1e-6))
            py, px = np.unravel_index(np.argmax(num / e), num.shape)
            keep = float((img[py:py + t.shape[0], px:px + t.shape[1]] * t).sum() / (t * t).sum())
            w = (n - (a - 1)) / (after - (a - 1))
            ex = (1 - w) * np.array(o.trk[a - 1]) + w * np.array(o.trk[after])
            c = o.cut(n, 40, tuple(ex))
            if c is None:
                continue
            d = ndimage.gaussian_filter(c[0] - np.median(c[0]), 1.5)
            d[c[1] > 15] = -99
            res.append((n, keep, float(d.max() / max(amp0, 1))))
    if not res:
        return NOP, "no contrast transient inside the track", {}
    r = np.array(res)
    sk, ck = float(np.median(np.clip(r[:, 1], 0, None))), float(np.median(r[:, 2]))
    txt = (f"{len(r)} transient frames: the scene keeps {sk:.2f} of its contrast (1/{1 / max(sk, 1e-3):.0f}), "
           f"the object at most {ck:.2f} (1/{1 / max(ck, 1e-3):.0f}) and stays on its path")
    v = PASS if ck <= max(3 * sk, 0.15) else FLAG if (ck >= 0.5 and sk <= 0.25) else INC
    return v, txt, {"scene_kept": sk, "object_kept": ck, "frames": r[:, 0].astype(int).tolist()}


def t_overlay(o, masks):
    ref = masks["ref_rgb"]
    ov = masks["graphics_raw"]
    yy, xx = np.mgrid[:o.clip.H, :o.clip.W]
    rows = []
    for n, (x, y) in sorted(o.trk.items()):
        x0, x1, y0, y1 = int(x) - 12, int(x) + 13, int(y) - 12, int(y) + 13
        if y0 < 0 or x0 < 0 or not ov[y0:y1, x0:x1].any():
            continue
        m = ov & ((xx - x) ** 2 + (yy - y) ** 2 <= (0.45 * o.size) ** 2)
        if m.sum() < 6:
            continue
        now, was = o.clip.rgb(n)[m], ref[m]
        rows.append((n, int(m.sum()), float((now.max(1) - now.min(1)).mean()), float((was.max(1) - was.min(1)).mean()),
                     float(now.mean()), float(was.mean())))
    if not rows:
        return NOP, "the object never crosses the symbology", {}
    r = np.array(rows)
    coloured = np.median(r[:, 3]) > 30
    if coloured:
        ratio = float(np.median(r[:, 2] / np.maximum(r[:, 3], 1)))
        v = PASS if ratio > 0.6 else FLAG if ratio < 0.3 else INC
        txt = f"crosses coloured symbology in {len(r)} frames; the symbology keeps {ratio:.2f} of its colour there"
    else:
        level = 0.0 if o.dark else 255.0
        r = r[np.abs(level - r[:, 5]) >= 40]                 # symbology at the object's own level decides nothing
        if len(r) == 0:
            return NOP, "the symbology it crosses is at the object's own level", {}
        ratio = float(np.median(np.abs(r[:, 4] - r[:, 5]) / np.abs(level - r[:, 5])))
        v = PASS if ratio < 0.4 else FLAG if ratio > 0.7 else INC
        txt = f"crosses uncoloured symbology in {len(r)} frames; its pixels move {ratio:.2f} of the way to the object's level"
    return v, txt, {"frames": r[:, 0].astype(int).tolist(), "ratio": ratio}


def t_appearance(o, masks, runs):
    blocks = masks["blocks_raw"]
    dist = ndimage.distance_transform_edt(~blocks)
    ns = sorted(o.trk)
    out, verdicts = [], []
    for end, n, nb in (("first seen", ns[0], ns[1:6]), ("last seen", ns[-1], ns[-6:-1])):
        x, y = o.trk[n]
        step = np.median([np.hypot(o.trk[b][0] - o.trk[a][0], o.trk[b][1] - o.trk[a][1]) / max(b - a, 1)
                          for a, b in zip([n] + list(nb)[:-1], nb)]) if len(nb) > 1 else 0
        reach = 2.5 * step + o.size + 8
        edge = min(x, y, o.clip.W - x, o.clip.H - y)
        if (end == "first seen" and n <= o.clip.n0 + 5) or (end == "last seen" and n >= o.clip.n1 - 5):
            out.append(f"{end} at the {'start' if end == 'first seen' else 'end'} of the clip")
        elif any(abs(n - a) <= 3 or abs(n - b) <= 3 for a, b in runs):
            out.append(f"{end} next to a contrast transient (n = {n})")
        elif dist[int(y), int(x)] <= reach:
            out.append(f"{end} {dist[int(y), int(x)]:.0f} px from a redaction block (n = {n}): under the block")
        elif edge <= reach:
            out.append(f"{end} {edge:.0f} px from the frame edge (n = {n})")
        else:
            out.append(f"{end} in the open at n = {n} ({x:.0f},{y:.0f}): does the track start late / stop early, or does the object?")
            verdicts.append(INC)
    return (INC if verdicts else PASS), "; ".join(out), {}


def t_smear(o, runs):
    rows = []
    for n in sorted(o.trk):
        if not all(k in o.trk for k in (n - 1, n + 1)):
            continue
        s1 = np.array(o.trk[n]) - np.array(o.trk[n - 1])
        s2 = np.array(o.trk[n + 1]) - np.array(o.trk[n])
        v = (s1 + s2) / 2
        sp = float(np.hypot(*v))
        if sp < 1 or abs(np.hypot(*s1) - np.hypot(*s2)) > 0.35 * max(sp, 2.0):
            continue
        c = o.cut(n, int(2 * o.size))
        if c is None:
            continue
        sub, rr, dx, dy = c
        bgl = np.median(sub[(rr >= 1.5 * o.size) & (rr <= 1.9 * o.size)])
        pk = sub[rr <= 0.35 * o.size].max()
        if pk - bgl < 25:
            continue
        m = (sub >= bgl + 0.5 * (pk - bgl)) & (rr <= 1.4 * o.size)
        lab, _ = ndimage.label(m)
        L = lab[sub.shape[0] // 2, sub.shape[1] // 2]
        if L == 0:
            continue
        m = lab == L
        u = v / sp
        rows.append((n, sp, 4 * (dx[m] * u[0] + dy[m] * u[1]).std(), 4 * (-dx[m] * u[1] + dy[m] * u[0]).std()))
    if len(rows) < 15:
        return NOP, f"{len(rows)} usable frames", {}, None
    a = np.array(rows)
    cuts = [a[0, 0] - 1] + [r[1] for r in runs] + [a[-1, 0] + 1]
    best = None
    for lo, hi in zip(cuts[:-1], cuts[1:]):                  # one gain state at a time
        e = a[(a[:, 0] > lo) & (a[:, 0] < hi)]
        if len(e) >= 15 and (best is None or np.ptp(e[:, 1]) > np.ptp(best[:, 1])):
            best = e
    if best is None or np.ptp(best[:, 1]) < 6:
        span = 0 if best is None else np.ptp(best[:, 1])
        return NOP, f"its screen speed spans only {span:.1f} px/frame within one gain state", {}, best
    d = best[:, 2] - best[:, 3]
    p = np.polyfit(best[:, 1], d, 1)
    r = float(np.corrcoef(best[:, 1], d)[0, 1])
    txt = (f"extent along minus across its screen velocity = {p[0]:.2f} x speed {p[1]:+.1f} px, r = {r:+.2f} "
           f"(N = {len(best)}, {best[:, 1].min():.0f}-{best[:, 1].max():.0f} px/frame, n = {int(best[0, 0])}-{int(best[-1, 0])})")
    if p[0] > 0.1 and r > 0.6:
        return PASS, txt + f": an exposure of ~{p[0]:.2f} frame", {"slope": float(p[0]), "r": r}, best
    return INC, txt + ": no smear. A very short exposure does this too, and so does a pasted sprite", {"slope": float(p[0]), "r": r}, best


def t_shake(o, bg, reps, dbl):
    rows = []
    for n in sorted(o.trk):
        if not all(k in o.trk for k in (n - 1, n + 1)) or not all(k in bg for k in (n - 1, n)):
            continue
        if bg[n][1] != bg[n - 1][1] or bg[n][1] == "repeat" or any(k in dbl or k in reps for k in (n - 2, n - 1, n, n + 1)):
            continue
        ac = np.array(o.trk[n + 1]) - 2 * np.array(o.trk[n]) + np.array(o.trk[n - 1])
        ab = bg[n][0] - bg[n - 1][0]
        if max(abs(ac).max(), abs(ab).max()) < 6:
            rows.append((n, ac[0], ac[1], ab[0], ab[1], bg[n][1] == "striated"))
    if len(rows) < 40:
        return NOP, f"{len(rows)} usable frames", {}, None
    a = np.array(rows)
    out, best = [], None
    for comp, ia, ib in (("x", 1, 3), ("y", 2, 4)):
        r = float(np.corrcoef(a[:, ia], a[:, ib])[0, 1])
        sig = r * np.sqrt((len(a) - 2) / max(1 - r * r, 1e-9))
        s1 = float(np.polyfit(a[:, ib], a[:, ia], 1)[0])
        s2 = float(1 / np.polyfit(a[:, ia], a[:, ib], 1)[0]) if abs(r) > 0.05 else np.inf
        out.append((comp, r, sig, s1, s2))
        if best is None or sig > best[2]:
            best = (comp, r, sig, s1, s2)
    txt = "; ".join(f"{c}: r = {r:+.2f} ({sig:.1f} sigma), slopes {s1:.2f} and {s2:.2f}" for c, r, sig, s1, s2 in out)
    txt += f" (N = {len(a)}). Unit slope with noise in both gives slopes of r and 1/r."
    if a[:, 5].mean() > 0.5:
        txt += " Over striated texture the component along the striations is poorly measured."
    comp, r, sig, s1, s2 = best
    if sig >= 3 and s1 <= 1.3 and s2 >= 0.7:
        v = PASS
    elif sig < 2:
        v, txt = INC, txt + " No shared shake found: a steady camera, a noisy background, or an independent path."
    else:
        v = INC
    return v, txt, {"best": comp, "r": r, "sigma": float(sig)}, a[:, [0, 2 if comp == "y" else 1, 4 if comp == "y" else 3]]


def t_halo(o):
    rows = []
    s = o.size
    for n in sorted(o.trk):
        c = o.cut(n, int(2.5 * s))
        if c is None:
            continue
        sub, rr = c[0], c[1]
        bgl = np.median(sub[(rr >= 1.67 * s) & (rr <= 2.33 * s)])
        ring = sub[(rr >= 0.67 * s) & (rr <= 1.06 * s)]
        rows.append((n, sub[rr <= 0.28 * s].max(), sub[rr <= 0.22 * s].mean() - bgl, bgl - ring.mean(), ring.min()))
    h = np.array(rows)
    un = (h[:, 1] < 245) & (h[:, 4] > 12) & (h[:, 2] > 25)
    if un.sum() < 40 or np.ptp(h[un, 2]) < 30:
        return NOP, f"{un.sum()} frames with an unsaturated core and an unclipped ring", {}
    r = float(np.corrcoef(h[un, 2], h[un, 3])[0, 1])
    sig = r * np.sqrt((un.sum() - 2) / max(1 - r * r, 1e-9))
    ratio = float(np.median(h[un, 3] / h[un, 2]))
    txt = (f"ring depth against core amplitude r = {r:+.2f} ({sig:.1f} sigma) over {un.sum()} unsaturated frames, "
           f"depth/amplitude {ratio:.3f}")
    if ratio < 0.005:
        return NOP, txt + ": no sharpening ring to speak of", {"r": r}
    return (PASS if (r > 0.3 and sig > 3) else INC), txt, {"r": r, "ratio": ratio}


def t_pattern(o, pat, power, masks):
    """Covariance of each frame's high-passed footprint with the static pattern
    estimated from the OTHER half of the clip, under the object and beside it."""
    if pat is None:
        return NOP, "no static pattern estimate: the scene does not sweep the detector for long enough", {}
    s = o.size
    obj, ctl = [], []
    offs = [(70, 0), (-70, 0), (0, 70), (0, -70), (50, 50), (-50, -50)]
    bad = masks["graphics"] | masks["blocks"]
    r = int(1.4 * s)
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    rr = np.hypot(xx, yy)
    ring = rr <= 1.3 * s
    for n in pat["frames"]:
        if n not in o.trk:
            continue
        x, y = o.trk[n]
        xi, yi = int(round(x)), int(round(y))
        if not (90 < xi < o.clip.W - 90 and 90 < yi < o.clip.H - 90) or not np.isfinite(power[yi, xi]) or power[yi, xi] < 0.05:
            continue
        P = pat["H2" if pat["half_of"][n] == 1 else "H1"]
        g = o.clip.grey(n)
        hp = g - ndimage.gaussian_filter(g, 2.0)

        def cov(cx, cy):
            sl = (slice(cy - r, cy + r + 1), slice(cx - r, cx + r + 1))
            if bad[sl].any():
                return None
            gg, hh = g[sl], hp[sl].copy()
            ok = ring & (gg > 8) & (gg < 247) & np.isfinite(P[sl])
            if ok.sum() < 40:
                return None
            for k in range(int(1.3 * s) + 1):                   # take out the azimuthal mean: the object itself
                m = ok & (np.round(rr) == k)
                if m.any():
                    hh[m] -= hh[m].mean()
            return float((hh[ok] * P[sl][ok]).mean())
        c = cov(xi, yi)
        cs = [v for v in (cov(xi + dx, yi + dy) for dx, dy in offs) if v is not None]
        if c is not None and cs:
            obj.append(c)
            ctl.append(float(np.mean(cs)))
    if len(obj) < 20:
        return NOP, f"the object sits on a measurable static pattern in only {len(obj)} frames", {}
    mo, so = np.mean(obj), np.std(obj) / np.sqrt(len(obj))
    mc, sc = np.mean(ctl), np.std(ctl) / np.sqrt(len(ctl))
    txt = (f"pattern covariance under the object {mo:.3f} +- {so:.3f} DN^2, beside it {mc:.3f} +- {sc:.3f} "
           f"({len(obj)} frames)")
    if mc < 5 * sc:
        return NOP, txt + ": the pattern is too weak beside it as well", {}
    v = PASS if (mo > 0.5 * mc and mo > 3 * so) else FLAG if mo < 0.25 * mc else INC
    return v, txt, {"under": float(mo), "beside": float(mc)}


# ---- a synthetic insert ------------------------------------------------------------------------
class Insert:
    """The clip with a disc animated over it on a smooth path: on top of the
    symbology and the blocks, at full strength through transients, moving
    through repeated frames, never smeared, with a fixed dark ring, and with
    its surroundings (1.6 diameters) regenerated smooth, as generative fill or
    a feathered paste would leave them -- without the detector's pixel pattern."""

    def __init__(self, clip, trk, size, dark, power):
        self.clip, self.size, self.dark = clip, size, dark
        self.n0, self.n1, self.W, self.H, self.fps, self.video = clip.n0, clip.n1, clip.W, clip.H, clip.fps, clip.video
        ns = np.arange(min(trk), max(trk) + 1)
        pos = vf.interp_track(trk)
        xy = ndimage.gaussian_filter1d(np.array([pos(n) for n in ns]), 10, axis=0)
        best = None
        offs = [(dx, dy) for dx in (-400, -250, -160, 0, 160, 250, 400) for dy in (-250, -120, 0, 120, 250) if np.hypot(dx, dy) >= 150]
        for off in offs:                                  # stay in frame; prefer where the static pattern is measurable
            p = xy + off
            inside = (p[:, 0] > 40) & (p[:, 0] < clip.W - 40) & (p[:, 1] > 40) & (p[:, 1] < clip.H - 40)
            score = inside.mean()
            if power is not None:
                pw = np.nan_to_num(power[np.clip(p[:, 1].astype(int), 0, clip.H - 1), np.clip(p[:, 0].astype(int), 0, clip.W - 1)])
                score += 2 * (pw > 0.05).mean()
            if best is None or score > best[0]:
                best = (score, p, inside)
        self.trk = {int(n): (float(x), float(y)) for n, (x, y), ok in zip(ns, best[1], best[2]) if ok}
        r = int(1.5 * size)
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        self._grid = (yy, xx)

    def rgb(self, n):
        a = self.clip.rgb(n)
        if n not in self.trk:
            return a
        a = a.copy()
        x, y = self.trk[n]
        xi, yi = int(round(x)), int(round(y))
        yy, xx = self._grid
        rr = np.hypot(xx - (x - xi), yy - (y - yi))
        core = np.clip((0.5 * self.size - rr) / 1.2 + 0.5, 0, 1)
        ring = np.clip(1 - np.abs(rr - 0.85 * self.size) / (0.25 * self.size), 0, 1) * (1 - core)
        r = yy.shape[0] // 2
        sl = (slice(yi - r, yi + r + 1), slice(xi - r, xi + r + 1))
        lvl = 0.0 if self.dark else 255.0
        fill = np.clip((1.6 * self.size - rr) / 2.0, 0, 1)[..., None]      # the region a fill or a feathered paste rewrites
        smooth = np.stack([ndimage.gaussian_filter(a[sl][..., k], 3.0) for k in range(3)], -1)
        patch = a[sl] * (1 - fill) + smooth * fill
        patch = patch * (1 - core[..., None]) + lvl * core[..., None]
        patch = np.clip(patch + (25.0 if self.dark else -25.0) * ring[..., None], 0, 255)
        a[sl] = patch
        return a

    def grey(self, n):
        return self.rgb(n).mean(2)


# ---- report ------------------------------------------------------------------------------------
def object_tests(o, reps, dbl, bg, runs, masks, rows, pat, power, max_shift):
    res, extra = {}, {}
    res["cadence"] = t_cadence(o, reps, dbl, bg)
    res["transient"] = t_transient(o, runs, masks, rows, max_shift)
    res["layer order: symbology"] = t_overlay(o, masks)
    res["layer order: first and last seen"] = t_appearance(o, masks, runs)
    v, txt, d, extra["smear"] = t_smear(o, runs)
    res["smear"] = (v, txt, d)
    v, txt, d, extra["shake"] = t_shake(o, bg, reps, dbl)
    res["shake"] = (v, txt, d)
    res["halo"] = t_halo(o)
    res["static pattern"] = t_pattern(o, pat, power, masks)
    return res, extra


def figure(out, clip, series, reps, runs, power, trk, real, fake):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    BLUE, ORANGE, INK, INK2, GRID, SURF = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                         "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "figure.facecolor": SURF,
                         "axes.facecolor": SURF, "savefig.facecolor": SURF})
    fig, ax = plt.subplots(2, 2, figsize=(12, 7.6), gridspec_kw=dict(left=0.06, right=0.94, top=0.88, bottom=0.08, hspace=0.42, wspace=0.22))
    fig.text(0.06, 0.955, f"{out.name.split('_')[0].upper()}: integrity checks", fontsize=13, weight="bold")
    fig.text(0.06, 0.92, "Blue: the tracked object. Orange: a synthetic disc animated over the same frames, which should fail.",
             fontsize=9.2, color=INK2)

    def dress(a, title, xl, yl):
        a.set_title(title, loc="left", fontsize=9.8, weight="bold", pad=6)
        a.set_xlabel(xl); a.set_ylabel(yl)
        a.grid(color=GRID, lw=0.8); a.set_axisbelow(True); a.tick_params(length=0)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)

    a = ax[0, 0]
    t = clip.t(series[:, 0])
    a.plot(t, series[:, 2], color=INK2, lw=1.2)
    for lo, hi in runs:
        a.axvspan(clip.t(lo) - 0.02, clip.t(hi) + 0.02, color=ORANGE, alpha=0.18, lw=0)
    if reps:
        a.plot(clip.t(np.array(reps)), np.full(len(reps), series[:, 2].max() * 1.04), "|", color=BLUE, ms=7, mew=1.2)
    dress(a, f"Scene contrast; {len(reps)} repeated frames (ticks), {len(runs)} transients (shaded)", "time  [s]", "scene sd  [DN]")

    a = ax[0, 1]
    if power is not None:
        im = a.imshow(np.sqrt(np.clip(np.nan_to_num(power), 0, None)), cmap="Blues", vmin=0, vmax=1.2, interpolation="nearest")
        if trk:
            p = np.array([trk[n] for n in sorted(trk)])
            a.plot(p[:, 0], p[:, 1], color=ORANGE, lw=1.2)
        a.set_xticks([]); a.set_yticks([])
        cb = fig.colorbar(im, ax=a, fraction=0.03, pad=0.02)
        cb.set_label("static pattern  [DN rms]", color=INK2)
        cb.outline.set_visible(False)
    else:
        a.text(0.5, 0.5, "not measurable:\nthe scene does not sweep the detector", ha="center", va="center", color=INK2, transform=a.transAxes)
        a.set_xticks([]); a.set_yticks([])
    a.set_title("Where the detector's static pattern is measurable (track in orange)", loc="left", fontsize=9.8, weight="bold", pad=6)

    for a, key, title, xl, yl in ((ax[1, 0], "smear", "Exposure smear", "screen speed  [px/frame]", "extent along minus across  [px]"),
                                  (ax[1, 1], "shake", "Shared camera shake", "background acceleration  [px/frame²]", "object acceleration  [px/frame²]")):
        for ex, col, lab in ((fake, ORANGE, "synthetic insert"), (real, BLUE, "tracked object")):
            d = ex.get(key) if ex else None
            if d is not None and len(d):
                xs, ys = (d[:, 1], d[:, 2] - d[:, 3]) if key == "smear" else (d[:, 2], d[:, 1])
                a.scatter(xs, ys, s=16, color=col, edgecolor=SURF, linewidth=0.6, label=lab)
        if key == "shake":
            lim = 2.0
            a.plot([-lim, lim], [-lim, lim], color=INK2, lw=1.0)
            a.set_xlim(-lim, lim); a.set_ylim(-lim, lim)
        dress(a, title, xl, yl)
        if a.get_legend_handles_labels()[0]:
            a.legend(frameon=False, fontsize=8.6, loc="lower right")
    fig.savefig(out, dpi=130)


def examine(clip, rec=None, track=None, size=9.0, dark=False, rows=None, max_shift=45.0, selftest=True, out=None,
            tag=None, procs=10, say=print, progress=None, stop=None):
    """The integrity tests as a stage: what the record says, whether the clip behaves as
    one sensor's output, and -- with a track -- whether the object behaves as imagery or
    as something laid over it, beside a synthetic insert put through the same tests.
    `size` and `dark` are the object's: the tests look at its pixels, and a bright 9 px
    default on a dark 21 px object measures nothing. Writes <out>_integrity_report
    .{md,json,png}; the whole report is in `fields`, and `carry` is its text.
    `progress(text, done, total)` is told each step as it starts and, where a step can
    count, how far it has got (the run takes ~15 min on a 30-s clip); `stop` is asked
    between items, and `progress.Stopped` is raised if it says yes."""
    tag = tag or clip.video.stem.lower()
    stage = progress = progress or (lambda *a: None)
    if track:
        R_obj = dict(size_px=float(size), dark=bool(dark))
    video = clip.video
    R = {"video": str(video), "frames": [clip.n0, clip.n1], "size": [clip.W, clip.H], "fps": clip.fps}
    R["record"], R["container"] = record_report(rec), container_report(clip)
    if track:
        R["object_described_as"] = R_obj

    masks = vf.static_masks(clip, progress=progress)
    series = vf.frame_series(clip, masks, procs, progress, stop)
    reps, runs = vf.repeats(series), vf.transients(series)

    trk = track
    if trk:
        trk = {n: p for n, p in trk.items() if clip.n0 <= n <= clip.n1}

    bg, note = per_frame_background(clip, masks, rows, trk, set(reps), procs, max_shift, progress, stop)
    dbl = double_steps(bg)
    moving = sorted(n for n, (v, c) in bg.items() if c != "repeat" and np.hypot(*v) >= 3)
    stage("the symbology's mask, refined on the frames that move")
    masks = vf.refine_graphics(clip, masks, moving)
    rig = np.array([r[1:] for r in vf.pooled(procs, _pair5, np.linspace(clip.n0, clip.n1 - 5, 30).astype(int).tolist(), _init,
                                             (video, clip.dir, clip.n0, clip.n1, masks, rows, trk, int(max_shift) + 20, 4),
                                             1, progress, stop, "rigid scene motion: sampled frame pairs")])
    stage("static pattern")
    live = [n for n in clip.frames() if n not in reps and not any(a <= n <= b for a, b in runs)]
    cuts = [clip.n0 - 1] + [b for _, b in runs] + [clip.n1 + 1]
    lo, hi = max(zip(cuts[:-1], cuts[1:]), key=lambda q: q[1] - q[0])
    epoch = [n for n in live if lo < n < hi and n in moving]
    pat = power = None                                     # a scene held still would pass for a static pattern
    if len(epoch) >= 80:
        pat = vf.static_pattern(clip, epoch, masks, trk, rows=rows, procs=procs, progress=progress, stop=stop)
        even, odd, epoch = pat["A"], pat["B"], pat["frames"]
        power = vf.pattern_power(even, odd)
        m = np.isfinite(even) & np.isfinite(odd) & ~masks["blocks"] & ~masks["graphics"]
    stage("zoom across transients")
    zooms = []
    for a, b in runs:
        if a - 2 >= clip.n0 and b + 6 <= clip.n1:
            s, z, off, z1 = vf.zoom_ratio(clip, a - 2, b + 6, masks)
            zooms.append({"frames": [a, b], "scale": s, "zncc": round(z, 3), "zncc_same_scale": None if np.isnan(z1) else round(z1, 3),
                          "offset_px": [round(float(off[0]), 1), round(float(off[1]), 1)]})
    R["scene"] = {"repeated_frames": len(reps), "catch_up_steps": len(dbl), "transients": runs, "zoom_across_transients": zooms,
                  "background_note": note, "background_pairs_measured": round(np.mean([c != "repeat" for _, c in bg.values()]), 3),
                  "rigid_inliers_median": round(float(np.median(rig[:, 0])), 3), "two_motion_groups_share": round(float(np.mean(rig[:, 1] == 2)), 3),
                  "good_templates_share": round(float(np.median(rig[:, 3] / np.maximum(rig[:, 4], 1))), 3),
                  "good_templates_median": float(np.median(rig[:, 3])),
                  "scene_still_share": round(float(np.mean(rig[:, 5])), 3),
                  "static_pattern_split_half_r": round(float(np.corrcoef(even[m], odd[m])[0, 1]), 3) if pat else None,
                  "static_pattern_area_share": round(float(np.nanmean(power[m] > 0.05)), 3) if pat else None,
                  "pattern_frames": len(epoch)}

    real = fake = None
    if trk:
        stage("object tests")
        o = Obj(clip, trk, size, dark)
        res, real = object_tests(o, reps, dbl, bg, runs, masks, rows, pat, power, max_shift)
        R["object"] = {k: {"verdict": v[0], "finding": v[1], **v[2]} for k, v in res.items()}
        if selftest:
            stage("self-test: synthetic insert")
            ins = Insert(clip, trk, size, dark, power)
            fo = Obj(ins, ins.trk, size, dark)
            fres, fake = object_tests(fo, reps, dbl, bg, runs, masks, rows, pat, power, max_shift)
            R["selftest"] = {k: {"verdict": v[0], "finding": v[1]} for k, v in fres.items()}

    stage("report")
    if out:
        json.dump(R, open(f"{out}_integrity_report.json", "w"), indent=1, default=plain)
        figure(Path(f"{out}_integrity_report.png"), clip, series, reps, runs, power, trk, real, fake)
    rc, sc, ct = R["record"], R["scene"], R["container"]
    L = [f"# {tag.upper()}: integrity report", "",
         f"`{video.name}`, {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}. Generated by "
         "`mcdonald integrity`; read docs/method.md before quoting it.", "", "## The record", ""]
    if rc.get("title"):
        L.append(f"- Record: {rc['title']}" + (f" (release {rc['release']})" if rc.get("release") else ""))
        L.append(f"- Disclosure: {('**' + rc['disclosure'] + '**') if rc.get('disclosure') else 'none in the release text'} "
                 f"({rc['catalog_with_disclosure']} of {rc['catalog_videos']} videos in the {rc['catalog']} catalog "
                 "carry an alteration or recreation statement).")
    elif rc.get("catalog_videos"):
        L.append(f"- No record for this file in the {rc['catalog']} catalog ({rc['catalog_videos']} videos), "
                 "so nothing is known here about how it was released.")
    else:
        L.append("- No catalog is configured, so this report says nothing about the clip's provenance: "
                 "whether it was released with an alteration statement, and by whom, has to be established "
                 "separately. Pixel tests cannot substitute for that.")
    L.append(f"- Container: {ct['codec']}, {ct['bit_rate'] / 1e6:.1f} Mb/s, encoder {ct['video_tags'].get('encoder') or ct['encoder_strings'] or 'unnamed'}, "
             f"created {ct['format_tags'].get('creation_time', 'n/a')}; keyframes at {ct['keyframes'][:8]}. A transcode says nothing about the source.")
    L += ["", "## Is this a sensor's output?", "",
          f"- Repeated frames: {sc['repeated_frames']}; catch-up double steps found: {sc['catch_up_steps']}.",
          f"- Contrast transients: {sc['transients'] or 'none'}" + "".join(
              (f"; across n = {z['frames'][0]}-{z['frames'][1]} the scale is x{z['scale']:.2f} (ZNCC {z['zncc']}, offset {z['offset_px']} px)"
               if z["zncc"] >= 0.6 else f"; across n = {z['frames'][0]}-{z['frames'][1]} no scale matches (best ZNCC {z['zncc']})") for z in zooms) + ".",
          (f"- Scene motion: {sc['rigid_inliers_median']:.0%} of good templates move as one or two rigid groups "
           f"(two groups in {sc['two_motion_groups_share']:.0%} of sampled pairs); {sc['good_templates_share']:.0%} of templates find a clean match."
           if sc["good_templates_median"] >= 15 else
           f"- Scene motion: not measurable. Only {sc['good_templates_median']:.0f} templates per pair find a clean match (little unmasked texture)."),
          (f"- Static pattern: split-half r = {sc['static_pattern_split_half_r']} between alternate 25-frame blocks, measurable over {sc['static_pattern_area_share']:.0%} "
           f"of the frame (from {sc['pattern_frames']} frames in which the scene sweeps the detector)." if sc["static_pattern_split_half_r"] is not None
           else f"- Static pattern: not measurable. The scene sweeps the detector in only {sc['pattern_frames']} frames, and a scene held still would pass for one.")]
    if sc["scene_still_share"] > 0.3:
        L.append(f"- The scene is held nearly still on screen in {sc['scene_still_share']:.0%} of sampled pairs, so the shake and catch-up tests have little to work with.")
    if note:
        L.append(f"- Note: {note}.")
    if masks["still_scene"]:
        L.append("- More than 30 % of the frame never changes, so static, sharp pixels were not treated as symbology (only coloured symbology is masked).")
    if trk:
        L += ["", "## Was the object added?", "", "| test | verdict | finding | synthetic insert |", "|---|---|---|---|"]
        for k, v in R["object"].items():
            s = R.get("selftest", {}).get(k, {})
            L.append(f"| {k} | **{v['verdict']}** | {v['finding']} | {s.get('verdict', '')}{': ' + s['finding'] if s else ''} |")
        L += ["", "PASS: behaves as sensor imagery. FLAG: behaves as something laid over it. NO POWER: this clip cannot decide the test. "
              "A PASS means most where the synthetic insert fails the same test on the same frames.", "",
              "No result here excludes a composite made upstream of the symbology by someone who modelled exposure, shake, gain and parallax."]
    if out:
        Path(f"{out}_integrity_report.md").write_text("\n".join(L) + "\n")
    text = "\n".join(L) + "\n"
    verdicts = {k: v["verdict"] for k, v in R.get("object", {}).items()}
    npw = [(k, v["finding"]) for k, v in R.get("object", {}).items() if v["verdict"] in (NOP, INC)]
    if not trk:
        npw.append(("was the object added?", "no track, so none of the object tests could be run"))
    files = []
    if out:
        files = [f"{out}_integrity_report.md", f"{out}_integrity_report.json", f"{out}_integrity_report.png"]
        say(f"wrote {out}_integrity_report.{{md,json,png}}")
    result = dict(object_verdicts=verdicts, report=f"{out}_integrity_report.md") if out else dict(object_verdicts=verdicts)
    return Found("integrity", result, json.loads(json.dumps(R, default=plain)), no_power=npw, files=files, carry=text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("video")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--track")
    ap.add_argument("--auto-track", action="store_true")
    ap.add_argument("--size", type=float, help="the object's diameter, px (default 9; with --marks, the scale the "
                    "marks chose)")
    ap.add_argument("--dark", action="store_true", help="the object is darker than the scene (with --marks, the "
                    "polarity the marks chose)")
    ap.add_argument("--seed")
    ap.add_argument("--marks", metavar="JSON",
                    help="a _marks.json from `mcdonald mark`: link the track from the hand marks, which give it the "
                    "detector's scale, its polarity and the velocity. The way to track an object too fast "
                    "for --auto-track to acquire")
    ap.add_argument("--mask-rows")
    ap.add_argument("--max-shift", type=float, default=45)
    ap.add_argument("--no-selftest", action="store_true")
    ap.add_argument("--out", metavar="DIR", help="case directory for results "
                    "(default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--procs", type=int, default=10)
    ap.add_argument("--json", action="store_true",
                    help="print the report as JSON on stdout, every test a field (the envelope every command prints); "
                         "everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        found, clip = _main(args)
    if args.json:
        emit(found.envelope("integrity", inputs_of(args), clip, said=lines))
    return 0


def _main(args):
    video, tag, rec = vf.resolve(args.video)
    clip = vf.Clip(video, args.workdir, args.n0, args.n1)
    out = vf.out_prefix(args.out, tag)
    rows = vf.parse_rows(args.mask_rows)
    trk = vf.read_track(args.track) if args.track else None
    size, dark = (9.0 if args.size is None else args.size), args.dark
    if (args.marks and not trk) or args.auto_track:
        masks = vf.static_masks(clip)
        if args.marks and not trk:
            from . import autolink
            link = autolink.link_from_marks_file(clip, args.marks, out, masks=masks, rows=rows, procs=args.procs)
            if link:                                   # what the marks said the object is, unless told otherwise
                trk, size, dark = link.track, (link.size if args.size is None else size), (dark or link.dark)
        else:
            from . import layers as bg_layers          # the research repo's name for it
            seed = [float(v) for v in args.seed.split(",")] if args.seed else None
            trk = bg_layers.auto_track(clip, masks, rows, size, dark, seed, out, args.procs, progress=to_stderr())
    found = examine(clip, rec, trk, size, dark, rows, args.max_shift, not args.no_selftest, out, tag, args.procs,
                    say=lambda line: None,                # what it wrote is said here, after the report, as it always was
                    progress=to_stderr())
    if args.marks and trk and not args.track:             # the link wrote these on the way: they are this command's files too
        found.files[:0] = [f"{out}_autotrack.csv", f"{out}_autotrack_strip.png"]
    print(found.carry, end="")
    print(f"\nwrote {out}_integrity_report.{{md,json,png}}")
    return found, clip


if __name__ == "__main__":
    raise SystemExit(main())
