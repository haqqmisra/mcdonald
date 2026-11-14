"""A line in a look-alike band, held against the background's apertures: the band search as a reading.

The flicker stage's headline reads a curve's single strongest peak. On a target the camera holds, that peak is often a
slow wander at 1.5-3 Hz, and a real line in a faster band is then never judged for itself (IDEAS.md, the row "uap PR089,
2026-10-23": 10.50 Hz at 4.4 % of the brightness over frames 481-720, behind a slow drift). This reads each band of the
look-alike table for its own strongest line, and holds it against the same search on the background apertures beside
the object.

What is read (`search`). Each curve -- the object's and every background aperture's, each against its running mean, the
backgrounds in the object's brightness as the stage reads them -- is cut in stretches of SEG_S seconds, half overlapping.
The stretches' power spectra are averaged, and each frequency is divided by the mean of its neighbours within SIDE_HZ,
its own lobe left out: how it stands over its own continuum, whatever the continuum's level or slope. In each band of
the table that does not cover the whole band, the object's strongest is its line.

Its chance has two parts. How a frequency with no line stands does not depend on the curve's noise, only on the
reading, so DRAWS curves of grain alone, of the track's length, are searched the same way, and the chance is the share of
them whose strongest in the band stands as high: the band's width is paid for, and the number of bands (Bonferroni).
The background apertures then say whether this clip is such a curve: their standing at the frequencies searched,
pooled, is held to the drawn curves' (by their medians and their 90th centiles), and where the background stands higher
the object's standing is taken down by as much. A line is one where the chance is under LINE_P, it stands over every
background aperture's strongest in the band, and no background aperture beats half as strongly at its frequency (a rhythm
they share is the video's: `flicker.SHARED`, the stage's own rule).

It reports and decides nothing: the stage's call, the headline rule and the gates are as they were (method section 59).
The other half of the IDEAS row -- the verdict taken from the battery of tests -- is the headline rule, and is not here.
"""
import numpy as np
from scipy import ndimage

SEG_S = 4.0            # s: the stretch a spectrum is read over, as `beatpos.SEG_S`
SIDE_HZ = 2.5          # Hz: a frequency is held against the mean of its neighbours within this, or SIDE_RES resolutions if more
SIDE_RES = 8.0
LOBE_RES = 2.0         # resolutions either side of a frequency that are its own lobe (Hann), left out of its neighbours
PAD = 8
DRAWS = 2000           # curves of grain alone the search is repeated on, for the chance
SEED = 20261113        # their seed: the same curve gives the same reading twice
LINE_P = 0.01          # a band holds a line where curves with no line stand as high there this seldom, the search paid for
POOL_MIN = 20          # the background's frequencies, two resolutions apart, that its standing is read from (four apertures, five each)
SHARED = 0.5           # a background aperture that beats this strongly at the line, in the object's brightness, shares it (`flicker.SHARED`)
SAME_RES = 1.0         # resolutions: a line within this of the stage's beat (or its double) is that beat, not another line
LEVEL_FLOOR = 0.5      # the running mean an object's curve is read as a share of is held at this share of its median or more


def _stretches(n, fps):
    L = int(round(SEG_S * fps))
    if n < 1.5 * L:
        return [(0, n)]
    out = [(a, a + L) for a in range(0, n - L + 1, L // 2)]
    if out[-1][1] < n:
        out.append((n - L, n))
    return out


def standing(r, fps):
    """(frequencies, how each stands over its neighbours, resolution, the amplitude spectrum, the number of stretches) of
    a deviation curve r, or of each row of several: the stretches' power spectra averaged (Welch), each frequency over
    the mean of its neighbours within SIDE_HZ (or SIDE_RES resolutions), its own lobe left out; the amplitude the root
    of the averaged power."""
    r = np.atleast_2d(np.asarray(r, float))
    segs = _stretches(r.shape[1], fps)
    L = segs[0][1] - segs[0][0]
    res = fps / L
    fr = np.fft.rfftfreq(PAD * L, 1.0 / fps)
    df = fr[1]
    lobe, side = int(round(LOBE_RES * res / df)), int(round(max(SIDE_HZ, SIDE_RES * res) / df))
    foot = np.ones(2 * side + 1)
    foot[side - lobe:side + lobe + 1] = 0.0
    w = np.hanning(L)
    P = np.zeros((r.shape[0], len(fr)))
    for a, b in segs:
        x = r[:, a:b] - r[:, a:b].mean(axis=1, keepdims=True)
        P += np.abs(np.fft.rfft(x * w, PAD * L, axis=1)) ** 2
    P /= len(segs)
    near = ndimage.correlate1d(P, foot / foot.sum(), axis=1, mode="reflect")
    Q, A = P / np.where(near > 0, near, np.inf), 2.0 * np.sqrt(P) / w.sum()
    return (fr, Q[0], res, A[0], len(segs)) if Q.shape[0] == 1 else (fr, Q, res, A, len(segs))


def search(r, R, fps, table, top, low=1.5, lines=(), beat=None, peak=None, draws=DRAWS, seed=SEED):
    """The band search on the object's deviation curve r, held against the background apertures' R (a list of deviation
    curves over the same frames, in the object's brightness): dict(power, why, stretches, resolution_hz, bands: [{band (its
    short name), what, hz_band (its pieces in the band a beat is looked for in), hz, amplitude, stands, p, background (each
    aperture's strongest standing in the band), shared (a background aperture beats SHARED as strongly there, in the
    object's brightness: the stage's own rule for a beat the background shares), line,
    at_the_codec_line_hz, the_beat (it is the beat the stage calls the object's own, or its double), the_peak (it is the
    stage's strongest peak, which the stage did not call a beat)}], pool (the background frequencies read),
    background_over_grain (how the background's frequencies stand against the drawn curves': the factor the object's
    standing is taken down by, 1 or more), false_alarm (each background aperture searched as the object, against the
    others: how many bands held a line, of how many)). `table` is `flicker.lookalikes`' (the bands not covering the whole
    band are searched); `beat` the stage's {"hz", "double_hz", "resolution_hz"} where it calls the beat the object's own,
    `peak` the same where it reports a strongest peak and does not."""
    out = dict(power=False, why=None, bands=[])
    bands = [d for d in table if d.get("band") is not None and not d.get("covers")]
    if not bands:
        out["why"] = "no look-alike band lies inside the band a beat is looked for in at this frame rate"
        return out
    r = np.asarray(r, float)
    R = [np.asarray(b, float) for b in R if b is not None and len(b) == len(r) and np.all(np.isfinite(b))]
    if not R:
        out["why"] = "no background aperture was measured on every frame, so there is nothing to hold a line against"
        return out
    fr, Q, res, A, K = standing(r, fps)
    QB, AB = zip(*[standing(b, fps)[1::2][:2] for b in R])
    QB, AB = list(QB), list(AB)
    masks = []
    for d in bands:
        m = np.zeros(len(fr), bool)
        for a, b in d["band"]:
            m |= (fr >= max(a, low)) & (fr <= min(b, top))
        masks.append(m)
    inband = np.any(masks, axis=0)                           # the bands searched, together
    step = max(1, int(round(2 * res / fr[1])))               # two resolutions apart: the frequencies taken as independent (Hann)
    grid = np.flatnonzero(inband)[::step]
    out.update(stretches=K, resolution_hz=float(res))
    if len(grid) * len(QB) < POOL_MIN:
        out["why"] = (f"{len(grid) * len(QB)} background frequencies to hold a line against, under the {POOL_MIN} it needs: "
                      "the track is too short")
        return out
    QW = standing(np.random.default_rng(seed).standard_normal((draws, len(r))), fps)[1]     # grain alone, searched the same way
    drawn = [QW[:, m].max(axis=1) if m.any() else None for m in masks]
    g50, g90 = np.quantile(QW[:, grid], [0.5, 0.9])

    def judged(q, amp, others, amps):
        pool = np.concatenate([o[grid] for o in others])       # the background's standing where the bands are searched
        b50, b90 = np.quantile(pool, [0.5, 0.9])
        over = float(max(1.0, b50 / g50, b90 / g90))           # the background stands this much higher than grain alone does
        rows = []
        for d, m, null in zip(bands, masks, drawn):
            if null is None:
                continue
            k = np.flatnonzero(m)[int(np.argmax(q[m]))]
            p = min(1.0, len(bands) * float((1 + np.sum(null >= q[k] / over)) / (1 + len(null))))
            near = np.abs(fr - fr[k]) <= res
            rows.append(dict(band=d["source"], what=d["what"], hz_band=[[float(max(a, low)), float(min(b, top))] for a, b in d["band"]
                                                                        if min(b, top) > max(a, low)],
                             hz=float(fr[k]), stands=float(q[k]), p=p, k=int(k),
                             background=[float(o[m].max()) for o in others],
                             shared=bool(any(a[near].max() >= SHARED * amp[k] for a in amps))))
        return rows, over, len(pool)
    rows, over, npool = judged(Q, A, QB, AB)
    for row in rows:
        k = row.pop("k")
        row["amplitude"] = float(A[k])
        row["line"] = bool(row["p"] < LINE_P and not row["shared"] and row["stands"] > max(row["background"]))
        row["at_the_codec_line_hz"] = next((float(c) for c in lines or () if abs(row["hz"] - c) <= res), None)
        at = lambda b: bool(b and any(v and abs(row["hz"] - v) <= SAME_RES * max(res, b.get("resolution_hz") or 0.0)
                                      for v in (b.get("hz"), b.get("double_hz"))))
        row["the_beat"], row["the_peak"] = at(beat), at(peak)
    fa = [0, 0]
    if len(QB) >= 3:                                         # the control by construction: each background aperture as the object
        for i, q in enumerate(QB):
            got = judged(q, AB[i], QB[:i] + QB[i + 1:], AB[:i] + AB[i + 1:])[0]
            fa[0] += sum(1 for g in got if g["p"] < LINE_P and not g["shared"] and g["stands"] > max(g["background"]))
            fa[1] += len(got)
    out.update(power=True, bands=rows, pool=int(npool), background_over_grain=over, draws=int(draws),
               false_alarm=dict(lines=fa[0], searched=fa[1]))
    return out


def _chance_said(p):
    return "chance under 0.001" if p < 0.001 else f"chance {p:.3f}"


def lines_of(found):
    """The lines a search holds, one a frequency (a line found in several overlapping bands is one line, named by the
    narrowest band that holds it), strongest first."""
    rows = [b for b in (found or {}).get("bands") or [] if b.get("line")]
    out = []
    for b in sorted(rows, key=lambda b: sum(z - a for a, z in b["hz_band"])):
        if not any(abs(b["hz"] - o["hz"]) <= (found.get("resolution_hz") or 0.0) for o in out):
            out.append(b)
    return sorted(out, key=lambda b: -b["stands"])


def said(name, found, several=False, calls=None):
    """The reading in a few sentences, for the stage's notes; None where no band holds a line that is not the beat the
    stage calls the object's own. `calls`: whether the stage calls a beat of the object's own (True), so the sentences can
    say where the two differ: a line the stage never judged (it reads the strongest peak only), or its strongest peak
    itself, which its tests did not hold."""
    rows = [b for b in lines_of(found) if not b["the_beat"]]
    if not rows:
        return None
    who = f" ({name})" if several else ""
    parts = []
    for b in rows:
        lo, hi = b["hz_band"][0][0], b["hz_band"][-1][1]
        parts.append(f"a line at {b['hz']:.2f} Hz, {b['amplitude']:.1%} of its brightness, in the {lo:.1f}-{hi:.1f} Hz band, which "
                     f"the background beside it does not show ({_chance_said(b['p'])})"
                     + (f", at the codec's {b['at_the_codec_line_hz']:g} Hz" if b.get("at_the_codec_line_hz") else ""))
    s = f"Its brightness{who} has " + "; and ".join(parts) + "."
    if any(b.get("the_peak") for b in rows):
        s += " It is the stage's strongest rhythm, which the stage's own tests did not hold to be a beat: the finding says why."
    elif not calls:
        s += " The stage's rule does not call it a beat: it reads the strongest rhythm of the whole band, and this line is not it."
    return s + " A line is not a wingbeat. The look-alikes that share its band are listed with the beat."
