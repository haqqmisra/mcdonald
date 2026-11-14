"""A chain's rhythm or a wing's? Three readings of a beat that sits on a look-alike (the 10-Hz morphology tests, T2).

A beat near 10 Hz at 29.97 frames a second sits on a third of the frame rate, where a display's or a chain's rhythm, a
held-picture cadence and the folded lines of mains and aircraft power all land -- and where a small bird beats (ROADMAP.md
0.3 objective 4; `docs/history/handoff-beat-controls.md`, thread (e); the bird paper's Table 1 has two such objects,
PR077's and PR088's object 2). Frequency cannot tell them apart. Three readings of the beat's shape can speak to it, each
with a null, and none of them decides:

1. **Its depth along the track** (`depth_along`). A lamp's flicker and a chain's rhythm are a fixed share of the
   brightness wherever the object is; a wing's depth changes with the bird's aspect and falls away in a glide. The whole
   stretch is cut in pieces of DEPTH_S seconds, each fitted by least squares (`flicker._piece_fit`, as the steadiness
   reading fits its pieces), and the pieces' depths are compared in units of their errors. The same is done to
   DEPTH_RUNS beats of one steady depth -- the pieces' mean -- planted at the beat's frequency in the pieces' own
   residuals: the share of them whose depths come apart as far is p.
2. **Its wander** is `flicker.steadiness` (item 12), read already: a clock does not wander, a wingbeat does.
3. **Its width outside a fixed core** (`width_outside_core`). A brighter point covers more pixels above any threshold,
   so a size that beats in step with the brightness follows the brightness. What separates them is the light outside a
   core of CORE_PX pixels that is the same on every frame (the bird paper's test on PR135): its share in the outer of two
   rings of equal area changes only where the picture of the object changes shape, not where it is multiplied. A
   brightness that only scales leaves it still; a wing spreading does not. The reading plants a change of width of
   WIDTH_PLANT in the object's own stamps, to say whether one would have shown: a point has too little light outside
   its core, and the reading then has no power.

`chain_marked` says which beats are read: those marked with a look-alike a sensor chain or a supply makes (not a
flame's or a rotor's band, which are the object's own). Method section 59.
"""
import math

import numpy as np
from scipy import ndimage

DEPTH_S = 2.0          # s: the pieces a beat's depth is read in along the track
DEPTH_PIECES = 24      # pieces at most: of a longer stretch this many are read, evenly spread along it
DEPTH_RUNS = 200       # beats of one steady depth planted per reading ...
DEPTH_P = 0.01         # ... and the share of them under which the depth changes more than a steady beat's does
DEPTH_LEVEL = 0.5      # a piece whose own median brightness is under this share of the stretch's is left out: the object is
                       # not all there, and a depth over its running mean is not a depth (PR088's object 2: one piece at 0.01, a "depth" of 690 %)
CORE_PX = 3.0          # px: the core left out of the width reading on every frame (the bird paper's 2.5 or 3)
WIDTH_P = 0.01         # the harmonic F-test's chance, at the beat, under which the width has a line there
WIDTH_PLANT = 0.1      # the change of width planted at the beat in the object's own stamps: would one have shown?
WIDTH_SNR = 10.0       # the light outside the core over its own frame-to-frame scatter that the reading needs
WIDTH_CLIP = (2.0, 250.0)   # grey levels at or past which a pixel is at the picture's floor or ceiling
OWN = ("candle flames", "sky lantern", "rotor", "rotor, odd blades", "propeller", "multirotor", "cryocooler")   # the bands of things
#                        in the sky (and the cooler's, which marks nothing): every other look-alike is a supply's or the chain's


def chain_marked(beat):
    """The look-alikes of a beat (and of its double) that a supply or the sensor chain makes: [what]."""
    out = []
    for d in (beat.get("lookalike") or []) + (beat.get("double_lookalike") or []):
        if d.get("source") not in OWN and d["what"] not in out:
            out.append(d["what"])
    return out


def _amp(t, y, fps, f0):
    """(amplitude, its error, frequency, parameters, residual) of one piece: `flicker._piece_fit`'s sinusoid and quadratic,
    the amplitude's error from the residual's level near the beat (2 sigma^2 / n)."""
    from . import flicker
    f, p, resid, _ = flicker._piece_fit(t, y, fps, f0)
    T = float(t.max() - t.min())
    fr = np.arange(max(0.5, f - 1.5), min(fps / 2, f + 1.5), 0.5 / T)
    fr = fr[np.abs(fr - f) > 2 / T]
    s2 = float(np.mean(np.abs(np.exp(-2j * np.pi * np.outer(fr, t)) @ resid) ** 2 / len(t))) if len(fr) else float(resid.var())
    return float(np.hypot(p[3], p[4])), math.sqrt(2.0 * max(s2, 1e-300) / len(t)), f, p, resid


def _depths(parts, fps, f0):
    """The depth of each piece of `parts` [(t, y)], its error, their weighted mean and how far apart they are in units
    of their errors (a chi-square about the mean), and each piece's fit."""
    got = [_amp(tt, yy, fps, f0) for tt, yy in parts]
    a, e = np.array([g[0] for g in got]), np.array([g[1] for g in got])
    if not np.all(np.isfinite(e)) or np.any(e <= 0):
        return a, e, None, None, got
    w = 1 / e ** 2
    mean = float(np.sum(w * a) / np.sum(w))
    return a, e, mean, float(np.sum(w * (a - mean) ** 2)), got


def depth_along(r, fps, hz, runs=DEPTH_RUNS, seed=0, level=None):
    """Does the beat at `hz` in the deviation curve r keep one depth along the track? {power, why, pieces, piece_s,
    covered (the share of the stretch the pieces hold), depth (a piece), err, mean, least, most, stat, steady_99, p,
    changes}. The stretch is cut in pieces of DEPTH_S seconds, end to end -- DEPTH_PIECES of them, evenly spread, where it
    holds more -- short enough that a wingbeat's wander inside a piece does not lower its depth. p is the share of `runs`
    beats of one steady depth, planted at hz in the pieces' own residuals (resampled in blocks of
    `flicker.BOOT_BLOCK_S`), whose pieces' depths come apart as far as the beat's do, the beat counted among them;
    `changes` is p < DEPTH_P. `level`, the brightness on the frames of r, leaves out a piece whose own median is under
    DEPTH_LEVEL of the whole stretch's (`left_out`, their number). Under two pieces nothing is read."""
    from . import flicker
    r = np.asarray(r, float)
    n = len(r)
    out = dict(power=False, why=None, pieces=None, piece_s=None, covered=None, depth=None, err=None, mean=None, least=None,
               most=None, stat=None, steady_99=None, p=None, changes=None, left_out=0)
    L = max(flicker.MIN_FRAMES, int(round(DEPTH_S * fps)))
    if not hz or n < 2 * L:
        out["why"] = f"too short to compare its depth along the track: {n} frames, and two pieces need {2 * L}"
        return out
    pieces = min(n // L, DEPTH_PIECES)
    starts = np.round(np.linspace(0, n - L, pieces)).astype(int) if n // L > pieces else np.arange(pieces) * L
    if level is not None:
        lv = np.asarray(level, float)
        whole = float(np.median(lv))
        keep = [a for a in starts if whole > 0 and np.median(lv[a:a + L]) >= DEPTH_LEVEL * whole]
        out["left_out"] = int(len(starts) - len(keep))
        starts, pieces = np.asarray(keep, int), len(keep)
        if pieces < 2:
            out["why"] = (f"too few pieces where the object is all there to compare its depth: {pieces} of {len(keep) + out['left_out']} "
                          f"hold half its median brightness or more")
            return out
    t = np.arange(n) / fps
    parts = [(t[a:a + L], r[a:a + L]) for a in starts]
    a, e, mean, stat, got = _depths(parts, fps, hz)
    out.update(pieces=int(pieces), piece_s=L / fps, covered=float(pieces * L / n), depth=[float(v) for v in a],
               err=[float(v) for v in e], least=float(a.min()), most=float(a.max()))
    if stat is None:
        out["why"] = "a piece's depth could not be read"
        return out
    out.update(mean=mean, stat=stat, power=True)
    unit = lambda tt: (tt - tt.mean()) / ((tt.max() - tt.min()) / 2)
    trends = [np.column_stack([np.ones_like(tt), unit(tt), unit(tt) ** 2]) @ g[3][:3] for (tt, _), g in zip(parts, got)]
    resid = np.concatenate([g[4] for g in got])
    m = len(resid)
    B = min(m, max(2, int(round(flicker.BOOT_BLOCK_S * fps))))
    nb = -(-m // B)
    rng = np.random.default_rng(seed)
    steady = []
    for _ in range(runs):
        e2 = resid[((rng.integers(0, m, nb)[:, None] + np.arange(B)[None, :]) % m).ravel()[:m]]
        ph = rng.uniform(0, 2 * np.pi)
        again = [(tt, tr + mean * np.cos(2 * np.pi * hz * tt + ph) + e2[k * L:(k + 1) * L]) for k, ((tt, _), tr) in enumerate(zip(parts, trends))]
        s = _depths(again, fps, hz)[3]
        steady.append(np.inf if s is None else s)
    steady = np.array(steady)
    p = float((1 + np.sum(steady >= stat)) / (1 + len(steady)))
    out.update(steady_99=float(np.quantile(steady[np.isfinite(steady)], 0.99)) if np.isfinite(steady).any() else None, p=p,
               changes=bool(p < DEPTH_P))
    return out


def _rings(half, ring_in):
    """(distance from the stamp's middle, the core, the inner ring, the outer ring, the background's ring) for a stamp of
    2 * half + 1 px: the two rings of equal area between CORE_PX and the aperture's own ring (or the stamp's edge)."""
    yy, xx = np.mgrid[-half:half + 1, -half:half + 1]
    rr = np.hypot(xx, yy)
    r2 = float(min(ring_in, half - 3))
    r1 = math.sqrt((CORE_PX ** 2 + r2 ** 2) / 2)
    return rr, rr < CORE_PX, (rr >= CORE_PX) & (rr < r1), (rr >= r1) & (rr < r2), (rr >= r2) & (rr <= half), (r1, r2)


def _outer_share(S, rings):
    """Each stamp's share of its light outside the core that lies in the outer ring, and that light itself, over the
    background ring's median: (share, light outside the core, light in the core)."""
    rr, core, inner, outer, back, _ = rings
    bg = np.median(S[:, back], axis=1)
    c = S - bg[:, None, None]
    fin, fout, fc = c[:, inner].sum(axis=1), c[:, outer].sum(axis=1), c[:, core].sum(axis=1)
    tot = fin + fout
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(tot > 0, fout / tot, np.nan), tot, fc


def _dev(v, fps):
    """A series against its running mean, as a share of it (`flicker.deviation`), its gaps filled across first."""
    from . import flicker
    v = np.asarray(v, float)
    ok = np.isfinite(v)
    v = np.interp(np.arange(len(v)), np.flatnonzero(ok), v[ok])
    return flicker.deviation(v, fps)


def width_outside_core(stamps, r, fps, hz, ring_in=7.0, top=None, dark=False):
    """Does the object's width beat, read where its brightness cannot make it seem to? `stamps` are the object's stamps
    on the frames of the deviation curve r (`flicker.stamp`: the object at the middle, a dark one turned up), `ring_in`
    its aperture's ring's inner radius. {power, why, core_px, rings_px, outside_share (its light outside the core, of all
    of it), snr, width: {amplitude, p, line, phase_deg (against the brightness)}, area: {amplitude, p, line, phase_deg},
    planted: {change, amplitude, p, shows}}. `width` is the share of the light outside the core that lies in the outer
    ring, as a deviation curve, read at the beat by the harmonic F-test (`flicker.line_test`, a frequency given
    beforehand); `area` the count of pixels over half the object's typical peak, the size a brightness makes beat;
    `planted` the width's reading with every stamp stretched about its middle by 1 + WIDTH_PLANT cos(2 pi hz t): where
    that does not show, the reading has no power."""
    from . import flicker
    out = dict(power=False, why=None, core_px=CORE_PX, rings_px=None, outside_share=None, snr=None, width=None, area=None, planted=None)
    have = [k for k, s in enumerate(stamps) if s is not None]
    if not hz or len(have) < flicker.MIN_FRAMES or len(have) < 0.9 * len(stamps):
        out["why"] = "the object's stamp leaves the frame on too many frames"
        return out
    S = np.array([stamps[k] for k in have], float)
    half = S.shape[1] // 2
    if min(ring_in, half - 3) - CORE_PX < 2.0:
        out["why"] = f"its aperture's ring starts {ring_in:g} px out: no room for two rings outside a core of {CORE_PX:g} px"
        return out
    rings = _rings(half, ring_in)
    out["rings_px"] = [CORE_PX, float(rings[5][0]), float(rings[5][1])]
    raw = -S if dark else S
    outside = ~rings[1] & (rings[0] < rings[5][1])
    clipped = np.mean(((raw[:, outside] <= WIDTH_CLIP[0]) | (raw[:, outside] >= WIDTH_CLIP[1])).any(axis=1))
    share, tot, core = _outer_share(S, rings)
    scatter = 1.4826 * np.median(np.abs(np.diff(tot) - np.median(np.diff(tot)))) / math.sqrt(2)
    snr = float(np.median(tot) / scatter) if scatter > 0 else float("inf")
    out.update(outside_share=float(np.median(tot) / max(np.median(tot + core), 1e-9)), snr=snr, clipped_share=float(clipped))
    if clipped > 0.05:
        out["why"] = f"pixels outside its core are at the picture's floor or ceiling on {clipped:.0%} of the frames"
        return out
    if not np.isfinite(snr) or snr < WIDTH_SNR or np.isfinite(share).mean() < 0.9:
        out["why"] = (f"too little of its light lies outside a core of {CORE_PX:g} px to read a width there (it stands "
                      f"{max(snr, 0):.1f} times over its own frame-to-frame scatter, and {WIDTH_SNR:g} are needed): a point")
        return out
    rb = np.asarray(r, float)[have] if len(r) == len(stamps) else None
    t = np.asarray(have) / fps

    def at(v):
        d = _dev(v, fps)
        lt = flicker.line_test(d, fps, hz, top=top)
        ph = None
        if rb is not None:
            z = lambda q: np.sum((q - q.mean()) * np.hanning(len(q)) * np.exp(-2j * np.pi * hz * t))
            ph = float(np.degrees(np.angle(z(d) / z(rb))))
        return dict(amplitude=lt["amplitude"], p=lt["p"], line=bool(lt["p"] is not None and lt["p"] < WIDTH_P), phase_deg=ph)
    out["width"] = at(share)
    peak = np.median(np.sort(S.reshape(len(S), -1), axis=1)[:, -3:].mean(axis=1) - np.median(S[:, rings[4]], axis=1))
    area = ((S - np.median(S[:, rings[4]], axis=1)[:, None, None] >= 0.5 * peak) & (rings[0] < rings[5][1])).sum(axis=(1, 2)).astype(float)
    out["area"] = at(area) if area.std() > 0 else None
    # a change of width planted in the object's own stamps: each stretched about its middle, its light kept where it is brightest
    yy, xx = np.mgrid[-half:half + 1, -half:half + 1].astype(float)
    z = 1.0 + WIDTH_PLANT * np.cos(2 * np.pi * hz * t)
    P = np.array([ndimage.map_coordinates(s, [half + yy / q, half + xx / q], order=1, mode="nearest") for s, q in zip(S, z)])
    pl = at(_outer_share(P, rings)[0])
    out["planted"] = dict(change=WIDTH_PLANT, amplitude=pl["amplitude"], p=pl["p"], shows=pl["line"])
    out["power"] = bool(pl["line"])
    if not pl["line"]:
        out["why"] = (f"a change of width of {WIDTH_PLANT:.0%} at the beat, planted in its own stamps, does not show (chance "
                      f"{pl['p']:.2f}): its width outside the core is too noisy to read")
    return out


def said(name, m, several=False):
    """The three readings in a few sentences, for the stage's notes: what each says, and that none decides."""
    who = f" ({name})" if several else ""
    parts = []
    d, s, w = m.get("depth") or {}, m.get("steadiness") or {}, m.get("width") or {}
    if d.get("power"):
        parts.append(f"Its depth runs from {d['least']:.1%} to {d['most']:.1%} of its brightness over {d['pieces']} pieces of {d['piece_s']:.1f} s, "
                     + (f"more than a steady beat's does (chance {d['p']:.3f}). A lamp's flicker keeps one depth. A wing's changes with its "
                        "aspect, and so does the rhythm of held pictures." if d["changes"] else
                        f"no more than a steady beat's does (chance {d['p']:.2f}). So its depth cannot tell it from a lamp's flicker."))
    elif d.get("why"):
        parts.append(f"Its depth along the track was not read: {d['why']}.")
    if s.get("p") is not None:
        parts.append("Its frequency " + (f"wanders more than a clock's can (chance {s['p']:.3f})." if s.get("wanders") else
                                         f"holds as a clock's does (chance {s['p']:.2f})."))
    if w.get("power"):
        ww = w["width"]
        parts.append(f"Its width outside a fixed core of {CORE_PX:g} pixels " + (f"beats with it (chance {ww['p']:.3f}). Its picture changes "
                     "shape, which a brightness that only rises and falls cannot do." if ww["line"] else
                     f"does not beat (chance {ww['p']:.2f}), where a change of width of {WIDTH_PLANT:.0%} would have shown. The beat is in "
                     "its brightness, not in its shape."))
    elif w.get("why"):
        parts.append(f"Its width outside a fixed core was not read: {w['why']}.")
    marks = m.get("marks") or []
    return (f"The beat at {m['hz']:.2f} Hz{who} sits where a camera's own electronics or a power supply can make one"
            + (f" ({len(marks)} such look-alike{'s' if len(marks) != 1 else ''}, listed with the beat)" if marks else "")
            + ". Three readings of its shape come next, and none of them decides. " + " ".join(parts))
