"""The beat in the position: does the object's track carry a rhythm, and is it the rhythm of its brightness?

Every beat `flicker` reports is read from brightness, and a camera's gain, a display or a lamp can make brightness
beat. A second reading needs none of them (IDEAS.md K2, ROADMAP.md 0.3 objective 5; the kriging survey's section 1.5): a
bird's body rises and falls with each stroke, so its position carries the wingbeat, and a light-weighted centroid does
not move when every pixel is multiplied by a gain. Geostatistics calls the mark a periodic part leaves in a variogram
the hole effect (Journel & Huijbregts 1978): the variogram dips at the period.

What is read (`reading`). The series is the object's own centroid on every frame (`flicker.centred`, the one
`scene_shift` puts beside the scene's), less its running mean over DETREND_S, in stretches of SEG_S seconds, half
overlapping. Each stretch's spectrum, the two coordinates together, is divided by what the track's own wander and jitter
draw there, and by its own median over the band; the stretches are averaged, and the strongest frequency of that
average between LOW and the band's top is the track's periodic part. Its chance is read off DRAWS tracks that keep the
track's fitted covariance and carry no rhythm (a line, a Matérn-3/2 wander and a nugget fitted by REML, `kriging.py`; M8's
cosine left out), each read the same way: not white noise, which finds beats everywhere. The variogram's hole can be
read beside it (`hole=True`), against the same draws; it is not the stage's reading, because on the same tracks it found
fewer planted wobbles and many more rhythms where there are none (method section 59). Where the brightness beats, the
same average is read at the beat's own frequency, at its double and at its half, a frequency given beforehand each
(`at_beat`).

Whose motion it is. A track in the picture is the object's motion less the camera's, and a camera that shakes puts
its shake in every track. So the reading is the object's own only where the camera's motion is out: the track taken
against the registered scene (`scene_shift`'s path), or against the other members of its group, whose mean position
moves with the camera (`of_stage`). Otherwise the reading is given as the picture has it, with no power to say whose
motion it is, and says what would give it. The video's own rhythm is in a position too: where an encoder holds part of
the picture on its predicted frames, a centroid stops and starts at the codec's rate (Galileo flyer 1: 12 Hz, a fifth of
its frame rate, stronger than its wingbeat). So a peak at one of the codec's lines, within its own frequency error, is
said apart (`codec`) and the next strongest is the track's.

It reports and decides nothing: no beat, bird or headline is changed by it (method section 59).
"""
import math

import numpy as np
from scipy import linalg, ndimage

from . import kriging

LOW = 1.5              # Hz: as `flicker.LOW`, slower than this is a trend
TOP = 0.8              # of the Nyquist frequency, as `flicker.TOP`, where no top is given
DETREND_S = 0.5        # s: the running mean a series is taken against, as `flicker.DETREND_S`
SEG_S = 4.0            # s: the stretch a spectrum is read over; a wingbeat wanders 2-5 % over 4.5 s (`flicker.steadiness`)
MIN_POINTS = 60        # frames a reading needs, as `flicker.MIN_FRAMES`
COVER = 0.7            # the share of a stretch's frames that must have a position. Under it the reading is not made: features followed on
                       # real backgrounds got a rhythm 4 times in 20 between 0.4 and 0.7, against 11 in 194 above (the members' route)
FIT_MAX = 300          # points the covariance is fitted on, the middle of the track (one REML fit a coordinate)
DRAWS = 1000           # tracks drawn from the fitted covariance, with no rhythm, that the reading is held against
SEED = 20261113        # their seed: the same track gives the same reading twice
ALPHA = 0.01           # a periodic part is one where fewer than this share of the drawn tracks stand as high anywhere in the band
PAD = 8                # the spectrum's zero padding
Z_AGREE = 3.0          # the position's and the brightness's frequencies agree within this many of their combined errors
NEEDED = 2.2           # a rhythm this many times the amplitude that would just stand at the level is found three times in four
#                        with no frequency given, nine in ten at one given beforehand: measured on wobbles planted in the stage's
#                        own centroids of 83 recorded tracks and the labelled set's 432 (3,400 plants, 2026-11-13; method section 59)
NEAR_RES = 1.0         # resolutions of a stretch either side of a frequency given beforehand that are "at" it
CLEAR_RES = 4.0        # resolutions either side of a peak at a codec line that are left out when the next strongest is looked
#                        for: its lobe (two, under a Hann window) and as much again, for a rhythm that wanders
WINDOW_LINE = 0.01     # a line of the samples' own spectral window is one where it stands this high (nought's is 1). A brightness's bar is
                       # 0.1 (`flicker.WINDOW_LINE`); a position needs a lower one, because a held picture is more than a missing sample:
                       # the fresh pictures beside it show the scene at another time than their frames' (one held in ten gives 0.012)
WINDOW_CHANCE = 20.0   # and this many times what frames missing at random give, (1 - share) / (n share), so that chance gaps make no line
FLOOR_PX = 1e-3        # px: the least jitter a drawn track is given (a track written on a grid can fit none)
OTHERS_COVER = 0.8     # a fellow member is held against where it is in view on this share of the member's own frames
LEVER_K = 5.2          # the pixels a unit of brightness change moves the stage's centroid, over the background's level beside the
#                        object, that a brightness beating over an uneven background with no motion stays under 99 times in
#                        100: 576 drawn scenes (a point 1.2 or 2.5 px in sigma, its brightness beating by 20 %, over a texture of
#                        1.5, 3 or 6 px at 0.05 to 0.5 of its peak, still or sliding 0.35 or 1 px a frame under it; 2026-11-13,
#                        method section 59): median 0.65, 90th centile 2.4, 99th 5.2, most 6.6
REPEAT_PX = 0.02       # px: on a picture the video holds, a centroid that moved less than this from the frame before, or less
REPEAT_SHARE = 0.25    # than this share of its typical step on fresh frames, is the same picture read again, a missing sample;
#                        one that moved more was coded afresh (an encoder that skips a still sky holds the frame's thumbnails
#                        and not the object: Galileo's flyers, 45-78 % "held"). Read on the saved centroids (2026-11-13): on true
#                        holds 70-100 % of held frames are under the share (PR44, PR055, four labelled clips), 1-13 % of fresh ones


def dense(frames, x, y, held=()):
    """(first frame, [n, 2] positions on every frame from the first to the last, NaN where there is none): the series on
    its own frame grid. A frame in `held` (a picture the video repeats) and a position that repeats the frame before
    exactly are missing samples, not samples (`kinematics._band_points`' rule)."""
    f = np.asarray(frames, int)
    xy = np.c_[np.asarray(x, float), np.asarray(y, float)]
    ok = np.isfinite(xy).all(axis=1)
    f, xy = f[ok], xy[ok]
    if len(f) == 0:
        return 0, np.empty((0, 2))
    order = np.argsort(f)
    f, xy = f[order], xy[order]
    out = np.full((int(f[-1] - f[0]) + 1, 2), np.nan)
    out[f - f[0]] = xy
    rep = np.r_[False, np.all(out[1:] == out[:-1], axis=1)]
    out[rep] = np.nan
    for n in held:
        if 0 <= n - f[0] < len(out):
            out[int(n - f[0])] = np.nan
    return int(f[0]), out


def _against_trend(v, w):
    """v (frames down, NaN where there is no sample) against its own running mean over w frames: the residual, NaN where
    there was no sample. The gaps are first filled across in a straight line, each from the samples either side of it,
    so that the mean of a window is taken about its middle whatever is missing from it. Without that, a steady motion
    sampled with a regular gap (a picture held every third frame) leaves a residual at the gaps' own rate: the mean of
    the samples that are there sits off the window's middle by turns (IR_DRONE_059: 0.5 px at 10 Hz, a third of the
    frame rate, from holds alone)."""
    v = np.asarray(v, float)
    one = v.ndim == 1
    v = v[:, None] if one else v
    ok = np.isfinite(v[:, 0])
    k = np.flatnonzero(ok)
    if len(k) == 0:
        return v[:, 0] * np.nan if one else v * np.nan
    filled = v.copy()
    if len(k) < len(v):
        rows = np.flatnonzero(~ok)
        right = np.clip(np.searchsorted(k, rows), 0, len(k) - 1)
        left = np.clip(right - 1, 0, len(k) - 1)
        a, b = k[left], k[right]
        span = np.where(b > a, b - a, 1)
        t = np.clip((rows - a) / span, 0.0, 1.0)[:, None]
        filled[rows] = np.where((rows < k[0])[:, None], v[k[0]], np.where((rows > k[-1])[:, None], v[k[-1]], (1 - t) * v[a] + t * v[b]))
    out = filled - ndimage.uniform_filter1d(filled, w, axis=0, mode="nearest")
    out[~ok] = np.nan
    return out[:, 0] if one else out


def _running(v, w):
    """The running mean of v over w frames along its first axis, the missing (NaN) left out of it; NaN where the whole
    window is missing."""
    ok = np.isfinite(v)
    s = ndimage.uniform_filter1d(np.where(ok, v, 0.0), w, axis=0, mode="nearest")
    c = ndimage.uniform_filter1d(ok.astype(float), w, axis=0, mode="nearest")
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(c > 1e-9, s / c, np.nan)


def trend_frames(fps):
    """The running mean's length in frames, as `flicker.trend_frames`."""
    return max(3, int(DETREND_S * fps + 0.5))


def stretches(n, fps):
    """[(a, b)] the stretches a series of n frames is read in: SEG_S seconds each, half overlapping, the last one
    ending at the series' end; the whole series where it is shorter than a stretch and a half."""
    L = int(round(SEG_S * fps))
    if n < 1.5 * L:
        return [(0, n)]
    out = [(a, a + L) for a in range(0, n - L + 1, L // 2)]
    if out[-1][1] < n:
        out.append((n - L, n))
    return out


def sampling_lines(present, fps, top):
    """The frequencies (Hz, between LOW and `top`) at which the samples that are there keep a rhythm of their own: the
    lines of their spectral window under a Hann taper, |sum of w exp(-2 pi i f t) over the samples|^2 over (sum of w)^2,
    that stand at WINDOW_LINE or more, and WINDOW_CHANCE times what the same number of frames missing at random gives.
    A full set of frames has none; one frame in three missing has one at a third of the frame rate, at 0.25; one in five,
    two (a fifth of the frame rate and twice that), at 0.06."""
    m = np.asarray(present, float)
    n = len(m)
    if m.sum() < 3 or m.all():
        return []
    w = m * np.hanning(n)
    F = np.abs(np.fft.rfft(w, PAD * n)) ** 2 / w.sum() ** 2
    fr = np.fft.rfftfreq(PAD * n, 1.0 / fps)
    band = (fr >= LOW) & (fr <= top)
    bar = max(WINDOW_LINE, WINDOW_CHANCE * (1.0 - m.mean()) / m.sum())
    peak = np.r_[False, (F[1:-1] >= F[:-2]) & (F[1:-1] > F[2:]), False] & band & (F >= bar)
    return [round(float(f), 3) for f in fr[peak]]


def _fit(t, v):
    """(s2, ell, tau2) of one coordinate against time: the line, wander and nugget by REML (`kriging.Model`), on the
    middle FIT_MAX points. A coordinate the fit cannot factor gets the line's white jitter."""
    ok = np.isfinite(v)
    t, v = t[ok], v[ok]
    if len(t) > FIT_MAX:
        a = (len(t) - FIT_MAX) // 2
        t, v = t[a:a + FIT_MAX], v[a:a + FIT_MAX]
    m = kriging.Model(t, v, float(t.mean()))
    if m.pc is None:
        return 0.0, 1.0, max(m.white[0], FLOOR_PX ** 2)
    s2, ell, tau2 = m.theta[:3]
    return float(s2), float(ell), float(max(tau2, FLOOR_PX ** 2))


def _draws(t, ok, theta, rng, draws):
    """[n, draws] series with the covariance theta on the frames that have a position (`ok`), NaN on the others."""
    tt = t[ok]
    K = kriging.matern32(tt[:, None] - tt[None, :], theta[0], theta[1]) if theta[0] > 0 else np.zeros((len(tt), len(tt)))
    K[np.diag_indices_from(K)] += theta[2] + kriging.JITTER * (theta[0] + theta[2])
    try:
        L = linalg.cholesky(K, lower=True, check_finite=False)
    except linalg.LinAlgError:
        L = np.sqrt(theta[0] + theta[2]) * np.eye(len(tt))
    out = np.full((len(t), draws), np.nan)
    out[ok] = L @ rng.standard_normal((len(tt), draws))
    return out


def _spectra(r, fps):
    """(frequencies, |F|^2, weights' sum) of the columns of r (residuals, NaN where missing) under a Hann window."""
    n = r.shape[0]
    ok = np.isfinite(r)
    w = np.hanning(n)[:, None] * ok
    F = np.fft.rfft(np.where(ok, r, 0.0) * w, PAD * n, axis=0)
    return np.fft.rfftfreq(PAD * n, 1.0 / fps), np.abs(F) ** 2, w.sum(axis=0)


def _vario(r, lags):
    """The variogram of the columns of r at whole `lags`: half the mean squared difference over the pairs present."""
    out = np.empty((len(lags),) + r.shape[1:])
    for i, h in enumerate(lags):
        d = r[h:] - r[:-h]
        with np.errstate(invalid="ignore"):
            out[i] = 0.5 * np.nanmean(d * d, axis=0)
    return out


def _hole(g, lags):
    """How deep the variogram g (at `lags` 1, 2, ...) dips at each lag h against half of it: (g(h/2) - g(h)) / (g(h/2) +
    g(h)), 1 for a sinusoid of period h, 0 for jitter, under 0 for a wander; for the lags from 2 up."""
    hs = np.asarray(lags)[1:]
    half = hs / 2.0
    lo, hi = np.floor(half).astype(int), np.ceil(half).astype(int)
    gh = 0.5 * (g[np.maximum(lo, 1) - 1] + g[np.maximum(hi, 1) - 1])
    with np.errstate(invalid="ignore", divide="ignore"):
        return hs, (gh - g[1:]) / (gh + g[1:])


def reading(frames, x, y, fps, top=None, held=(), lines=(), beat=None, bright=None, background=None, draws=DRAWS, seed=SEED,
            hole=False):
    """The periodic part of one series of positions (the docstring above): dict(power, why, frames, points, stretches,
    stretch_s, hz, hz_err, p, stands, needed, line, amplitude_px (x, y), needed_px, axis, where (the stretches it stands
    in), fit, hole, codec, at_beat, draws). `lines` are the codec's lines (Hz): a peak within `flicker.Z_LINE` of its own
    frequency error of one is the video's, said apart (`codec`), and the track's periodic part is the strongest that is
    not; where every peak is at a line, the reading is that line's and `line` is False. Where the video holds its
    pictures by a rule (`sampling_lines`, given back as `sampling_lines_hz`), the reading is not made: power False.
    `beat`, where the brightness
    beats, is {"hz", "hz_err", "double_hz"}
    (`flicker`'s `beat[name]`): the reading is then made at those frequencies too (`at_beat`). `bright`, the object's
    brightness on the same frames (NaN where there is none), and `background`, the level of the background beside it over
    that brightness (`background_level`), let a rhythm found there be held against what a brightness beating over an
    uneven background makes of a position (`at_beat["without_brightness"]`). power False, with `why`, where the series is too
    short or too broken to read."""
    f0, P = dense(frames, x, y, held)
    out = dict(power=False, why=None, frames=[f0, f0 + len(P) - 1] if len(P) else None,
               points=int(np.isfinite(P[:, 0]).sum()) if len(P) else 0)
    top = float(top) if top else TOP * fps / 2
    n = len(P)
    if out["points"] < MIN_POINTS:
        out["why"] = f"{out['points']} frames with a position, under the {MIN_POINTS} a rhythm needs"
        return out
    okp = np.isfinite(P[:, 0])
    # the samples' own rhythm. A video made from a slower source holds pictures by a rule (20 a second on a grid of 30:
    # every third), and the fresh ones run on the source's clock: a steady motion read at the frames' times then steps at
    # that rate (IR_DRONE_059: 0.34 px at 10.00 Hz, the "beat" of its brightness too). Taking a cosine out at the rule's
    # lines and searching the rest was built and measured: background features followed on such clips got a rhythm 7
    # times in 14 (the flyers') and 32 in 68 (the labelled set's), against 11 in 194 on full sets of frames. So the
    # reading is not made there, and says why
    sampled = sampling_lines(okp, fps, top)
    if sampled:
        out.update(sampling_lines_hz=sampled,
                   why=(f"the video holds its pictures at a steady rate ({', '.join(f'{v:.2f}' for v in sampled[:3])} Hz), and the "
                        "positions left between them keep that rhythm, so one of the object's own cannot be told from it"))
        return out
    w = trend_frames(fps)
    segs = [(a, b) for a, b in stretches(n, fps) if np.isfinite(P[a:b, 0]).mean() >= COVER]
    if not segs:
        out["why"] = f"no stretch of {SEG_S:g} s has a position on {COVER:.0%} of its frames"
        return out
    t = np.arange(n) / fps
    lines = sorted(set(float(c) for c in lines or ()))
    theta = [_fit(t, P[:, c]) for c in (0, 1)]
    out["fit"] = {name: dict(wander_px=math.sqrt(th[0]), range_s=th[1], jitter_px=math.sqrt(th[2])) for name, th in zip("xy", theta)}
    R = _against_trend(P, w)                                 # the track against its own running mean
    R = R - np.nanmean(R, axis=0)
    rng = np.random.default_rng(seed)
    L = segs[0][1] - segs[0][0]
    res = fps / L
    lags = np.arange(1, max(3, int(round(fps / LOW))) + 1)
    lags = lags[lags < L // 2]
    S = Sd = H = Hd = fr = None                              # the stretches' standardized spectra and holes, summed: the track's, the draws'
    per_seg = []
    # the draws are made three stretches at a time (two stretches' length), each block drawn from the one fitted
    # covariance on its own frames: beyond the running mean's reach the stretches of a wander are independent, and one
    # Cholesky of the whole of a long track would cost its cube
    for i in range(0, len(segs), 3):
        blk = segs[i:i + 3]
        a0, b0 = blk[0][0], blk[-1][1]
        D = [_draws(t[a0:b0], okp[a0:b0], theta[c], rng, draws) for c in (0, 1)]
        D = [_against_trend(d, w) for d in D]
        for a, b in blk:
            rs = R[a:b]
            fr, Pw, ws = _spectra(rs, fps)
            band = (fr >= LOW) & (fr <= top)
            Z, Zd, e_at = np.zeros(len(fr)), np.zeros((len(fr), draws)), []
            for c in (0, 1):
                _, Pd, _ = _spectra(D[c][a - a0:b - a0], fps)
                e0 = Pd.mean(axis=1)
                e_at.append(e0 * (2.0 / ws[c]) ** 2 if ws[c] > 0 else np.full(len(fr), np.inf))
                e0 = np.where(e0 > 0, e0, np.inf)
                Z += Pw[:, c] / e0
                Zd += Pd / e0[:, None]
            m, md = np.median(Z[band]), np.median(Zd[band], axis=0)
            m = m if m > 0 else 1.0
            Z, Zd = Z / m, Zd / np.where(md > 0, md, 1.0)
            S, Sd = (Z, Zd) if S is None else (S + Z, Sd + Zd)
            per_seg.append((a, b, Z, [e * m for e in e_at]))     # e: the squared amplitude that stands 1 over the stretch's median
            if hole and len(lags) >= 4:
                hs, h = _hole(_vario(rs, lags).sum(axis=1), lags)
                _, hd = _hole(sum(_vario(D[c][a - a0:b - a0], lags) for c in (0, 1)), lags)
                H, Hd = (h, hd) if H is None else (H + h, Hd + hd)
    K = len(per_seg)
    S, Sd = S / K, Sd / K
    band = (fr >= LOW) & (fr <= top)
    null = Sd[band].max(axis=0)
    lvl = float(np.quantile(null, 1 - ALPHA))
    # the track's periodic part: its strongest frequency that is not the codec's own. A peak is at a codec line where it
    # lies within Z_LINE of its own frequency error of it (`flicker.at_line`, as a brightness's peak is held): the line
    # has no width, and a wingbeat a fifth of a hertz from it is not at it (PR135's members, 7.1-7.9 Hz about 7.49)
    from . import flicker
    left, codec = band.copy(), None
    for _ in range(1 + len(lines or ())):
        j = np.flatnonzero(left)[int(np.argmax(S[left]))]
        hz = float(fr[j])
        amp = _amplitude(R, fps, hz, per_seg)
        err = _hz_err(R, fps, hz, per_seg, int(amp[1] >= amp[0]))
        at = flicker.at_line(hz, err, list(lines or ()), res)
        if at is None:
            break
        if codec is None:
            codec = dict(hz=hz, hz_err=err, stands=float(S[j]), line=bool(S[j] >= lvl), at_the_codec_line_hz=float(at))
        left &= np.abs(fr - hz) > CLEAR_RES * res
        if not left.any():
            break
    stat = float(S[j])
    p = float((1 + np.sum(null >= stat)) / (1 + draws))
    near = band & (np.abs(fr - hz) <= NEAR_RES * res)
    where = ([[int(f0 + a), int(f0 + b - 1)] for a, b, Z, _ in per_seg if Z[near].max() >= max(lvl, 0.5 * stat)] if K > 1 else
             [[int(f0 + segs[0][0]), int(f0 + segs[0][1] - 1)]])
    # the smallest rhythm that is found three times in four (NEEDED times what would just stand at the level), along the
    # quieter coordinate, at the band's middle frequency: what the track's own wander and jitter leave room to hear
    need = [NEEDED * float(np.sqrt(max(lvl - 1.0, 0.0) * np.median(np.mean([e[c][band] for *_, e in per_seg], axis=0)))) for c in (0, 1)]
    out.update(power=True, stretches=K, stretch_s=L / fps, hz=hz, hz_err=err, p=p, stands=stat, needed=lvl,
               line=bool(p < ALPHA and at is None), at_the_codec_line_hz=at,
               amplitude_px=[float(amp[0]), float(amp[1])], needed_px=float(min(need)), axis="y" if amp[1] >= amp[0] else "x",
               where=where, draws=int(draws), resolution_hz=float(res), top_hz=top)
    if codec:
        out["codec"] = codec
    if hole and H is not None:
        H, Hd = H / K, Hd / K
        mu, sd = Hd.mean(axis=1), Hd.std(axis=1)
        sd = np.where(sd > 0, sd, np.inf)
        fh = fps / hs
        ok = (fh >= LOW) & (fh <= top)
        if ok.any():
            z, zd = (H - mu) / sd, (Hd - mu[:, None]) / sd[:, None]
            i = np.flatnonzero(ok)[int(np.argmax(z[ok]))]
            out["hole"] = dict(lag_frames=int(hs[i]), hz=float(fh[i]), depth=float(H[i]), drawn=float(mu[i]),
                               p=float((1 + np.sum(zd[ok].max(axis=0) >= z[i])) / (1 + draws)))
    if beat and beat.get("hz"):
        out["at_beat"] = _at_beat(beat, S, Sd, fr, band, res, R, fps, per_seg, draws, lines)
        if out["at_beat"] and out["at_beat"]["line"] and bright is not None:
            out["at_beat"]["without_brightness"] = _without(bright, background, frames, f0, n, w, out["at_beat"], Sd, fr, band, res, R,
                                                            fps, per_seg, draws)
    return out


def _standing(R, fps, per_seg):
    """The stretches' averaged spectrum of the residuals R, each coordinate over what the track's wander and jitter draw
    there and over the stretch's own median, as `reading` made the track's (from the stretches' kept levels)."""
    S = None
    for a, b, _, e in per_seg:
        _, Pw, ws = _spectra(R[a:b], fps)
        Z = sum(Pw[:, c] * (2.0 / ws[c]) ** 2 / np.where(e[c] > 0, e[c], np.inf) for c in (0, 1) if ws[c] > 0)
        S = Z if S is None else S + Z
    return S / len(per_seg)


def _without(bright, level, frames, f0, n, w, ab, Sd, fr, band, res, R, fps, per_seg, draws):
    """A rhythm found at the beat, held against the one thing besides motion that makes it. A light-weighted centroid is
    the object's light and what is behind it weighed together, so a brightness that beats over an uneven background
    leans the centroid toward the background as it dims: a rhythm in the position with no motion at all. Two readings
    of it. (1) The lever: the position's amplitude at the rhythm over the brightness's own amplitude at that frequency
    (`px_per_brightness`, pixels for a unit of brightness change). On drawn scenes with no motion the lever grows with the
    background's level over the object's brightness (`level`, `background_level`), and stays under LEVER_K times it 99
    times in 100: `reach_px` is that, and `beyond_background` says whether the rhythm is more (None where the
    background's level is not known). (2) In each stretch each coordinate is regressed on the
    brightness (against its own running mean, at no lag) and what is left is read at the same frequency against the same
    drawn tracks: {share (of the rhythm's standing that went with the brightness), stands, p, line}. That takes out a lean
    that keeps its direction -- a neighbour's light, a scene that rides with the object -- and not one whose direction
    changes as the background slides under the object, which is why the lever is the reading that is held to a null."""
    f = np.asarray(frames, int)
    v = np.full(n, np.nan)
    b = np.asarray(bright, float)
    ok = np.isfinite(b) & (f - f0 >= 0) & (f - f0 < n)
    v[f[ok] - f0] = b[ok]
    with np.errstate(invalid="ignore", divide="ignore"):
        trend = _running(v[:, None], w)[:, 0]
        d = (v - trend) / np.where(np.abs(trend) > 0, trend, np.nan)
    Rw = R.copy()
    depth = 0.0
    for a, z, *_ in per_seg:
        okd = np.isfinite(d[a:z])
        if okd.sum() >= 10:
            wn = np.hanning(z - a) * okd
            F = (np.where(okd, d[a:z] - d[a:z][okd].mean(), 0.0) * wn * np.exp(-2j * np.pi * ab["position_hz"] * np.arange(z - a) / fps)).sum()
            depth += (2 * abs(F) / max(wn.sum(), 1e-12)) ** 2
        for c in (0, 1):
            both = np.isfinite(R[a:z, c]) & okd
            if both.sum() >= 10:
                x = d[a:z][both] - d[a:z][both].mean()
                if np.sum(x * x) > 0:
                    slope = float(np.sum(x * R[a:z, c][both]) / np.sum(x * x))
                    Rw[a:z, c] = R[a:z, c] - slope * np.where(okd, d[a:z] - d[a:z][both].mean(), 0.0)
    depth = math.sqrt(depth / len(per_seg))
    S2 = _standing(Rw, fps, per_seg)
    near = band & (np.abs(fr - ab["position_hz"]) <= NEAR_RES * res)
    left = float(S2[near].max())
    p = min(1.0, len(ab["tried"]) * float((1 + np.sum(Sd[near].max(axis=0) >= left)) / (1 + draws)))
    lever = float(math.hypot(*ab["amplitude_px"]) / depth) if depth > 0 else None
    reach = LEVER_K * float(level) if level is not None and np.isfinite(level) else None
    return dict(brightness_amplitude=float(depth), px_per_brightness=lever, background_level=None if reach is None else float(level),
                reach_px=reach, beyond_background=None if reach is None else bool(lever is None or lever > reach),
                share=float(max(0.0, 1.0 - left / ab["stands"])) if ab["stands"] > 0 else None, stands=left, p=p, line=bool(p < ALPHA))


def _amplitude(R, fps, hz, per_seg):
    """The amplitude at hz, a coordinate (px): the root of the stretches' mean squared amplitude there."""
    amp = np.zeros(2)
    for a, b, *_ in per_seg:
        rs = R[a:b]
        ok = np.isfinite(rs)
        wn = np.hanning(b - a)[:, None] * ok
        F = (np.where(ok, rs, 0.0) * wn * np.exp(-2j * np.pi * hz * np.arange(b - a) / fps)[:, None]).sum(axis=0)
        amp += (2 * np.abs(F) / np.maximum(wn.sum(axis=0), 1e-12)) ** 2
    return np.sqrt(amp / len(per_seg))


def _hz_err(R, fps, hz, per_seg, c):
    """The error of the line's frequency: `flicker.hz_error` (a sinusoid fitted, its residual resampled in blocks, never
    under the Cramer-Rao bound) on the coordinate c, over the stretch where the line stands highest and half a stretch
    either side of it, the gaps filled across."""
    from . import flicker
    a, b, *_ = max(per_seg, key=lambda s: float(np.interp(hz, np.fft.rfftfreq(PAD * (s[1] - s[0]), 1.0 / fps), s[2])))
    L = b - a
    a, b = max(0, a - L // 2), min(len(R), b + L // 2)
    v = R[a:b, c]
    ok = np.isfinite(v)
    if ok.sum() < MIN_POINTS // 2:
        return None
    v = np.interp(np.arange(len(v)), np.flatnonzero(ok), v[ok])
    try:
        return float(flicker.hz_error(v - v.mean(), fps, hz)["hz_err"])
    except Exception:
        return None


def _at_beat(beat, S, Sd, fr, search, res, R, fps, per_seg, draws, lines=()):
    """The reading at the brightness beat: the average spectrum's strongest within NEAR_RES resolutions (or Z_AGREE of
    the beat's error, if more) of the beat, of its double and of its half -- frequencies given beforehand, so the band
    is not searched; the chance is the least of the three, times the number tried. dict(hz (the brightness's), tried,
    at ("the beat", "its double", "its half": where the position stood highest), at_hz, position_hz, position_hz_err,
    amplitude_px, p, line, stands, z (the two frequencies apart, in their combined errors), at_the_codec_line_hz (the
    frequency given is within Z_LINE of the brightness's own error of a codec line, so a rhythm there may be the video's:
    said, not refused), agrees (a line, and the two frequencies within Z_AGREE of their errors)."""
    cands = [("the beat", float(beat["hz"]))]
    if beat.get("double_hz"):
        cands.append(("its double", float(beat["double_hz"])))
    if beat["hz"] / 2 >= LOW:
        cands.append(("its half", float(beat["hz"]) / 2))
    reach = max(NEAR_RES * res, Z_AGREE * (beat.get("hz_err") or 0.0))
    got = []
    for what, c in cands:
        near = search & (np.abs(fr - c) <= reach)
        if not near.any():
            continue
        k = np.flatnonzero(near)[int(np.argmax(S[near]))]
        got.append((float((1 + np.sum(Sd[near].max(axis=0) >= S[k])) / (1 + draws)), -float(S[k]), what, c, float(fr[k])))
    if not got:
        return None
    p, stat, what, c, hz = min(got)
    p = min(1.0, p * len(got))
    amp = _amplitude(R, fps, hz, per_seg)
    err = _hz_err(R, fps, hz, per_seg, int(amp[1] >= amp[0]))
    be = (beat.get("hz_err") or 0.0) * (c / beat["hz"])
    z = abs(hz - c) / math.hypot(err or 0.0, be) if (err or be) else None
    from . import flicker
    at = flicker.at_line(c, be or None, list(lines or ()), res)      # by the brightness's own error: it is the better known
    return dict(hz=float(beat["hz"]), tried=[g[2] for g in got], at=what, at_hz=c, position_hz=hz, position_hz_err=err,
                amplitude_px=[float(amp[0]), float(amp[1])], p=p, line=bool(p < ALPHA), stands=-stat, z=z,
                at_the_codec_line_hz=at, agrees=bool(p < ALPHA and (z is None or z <= Z_AGREE)))


# ---- the stage's reading: whose motion ---------------------------------------------------------------------------
def codec_lines(codec, top):
    """The frequencies of the video's own rhythm that a position can carry (Hz, up to `top`), from `clip.gop`'s record: the
    anchors' lines (`lines_hz`, a brightness's too), and the I frames' own rate with its multiples where that is LOW or
    more -- a GOP of five frames at 60 a second refreshes the whole picture 12 times a second, and what the encoder held
    between moves then (Galileo flyer 1). A longer GOP's rate is a trend, and is left alone."""
    codec = codec or {}
    out = [float(c) for c in codec.get("lines_hz") or []]
    i_hz = codec.get("i_hz")
    if i_hz and i_hz >= LOW:
        out += [k * float(i_hz) for k in range(1, int(top / i_hz) + 1)]
    return sorted(set(round(c, 3) for c in out if c <= top))


def background_level(raw, name, a, b):
    """The level of the background beside an object over its own brightness: the root mean square of its background
    apertures' brightness (the member's own, where it has them; each the aperture's sum over its ring's median, as the
    object's is) over the object's median brightness, on the places a..b of the stage's frames. An even background gives
    its grain; an uneven one, how much of the light in an aperture is not the object's. None where either is missing."""
    own = (raw or {}).get(name)
    if own is None:
        return None
    mine = [c for c in raw if c.startswith(f"background of {name} ")] or [c for c in raw if c.startswith("background") and " of " not in c]
    vals = np.array([q for c in mine for q in raw[c][a:b] if q is not None], float)
    obj = np.array([q for q in own[a:b] if q is not None], float)
    if not len(vals) or not len(obj) or np.median(obj) <= 0:
        return None
    return float(np.sqrt(np.mean(vals ** 2)) / np.median(obj))


def still_held(frames, xy, held):
    """The frames among `held` (frames whose picture the video repeats, `flicker.pictures`' held_k as frame numbers) on
    which the centroid `xy` ([n, 2] over `frames`) also stood still: it moved less than REPEAT_SHARE of its typical step
    on the fresh frames (or REPEAT_PX, for an object that hardly moves). Those are the picture read again, and are left
    out as missing samples. On held pictures the centroid's step is a twentieth of a fresh frame's or less (PR44, PR055,
    the labelled set's 20-a-second clips: 0.01-0.13 px against 0.3-4.9), not nought, because the aperture it is read in
    has moved on with the track; where an encoder only skips a still sky the object's own pixels are coded afresh and
    its step on a "held" frame is a fresh frame's (the Galileo flyers)."""
    frames = np.asarray(frames, int)
    xy = np.asarray(xy, float)
    step = np.r_[np.inf, np.hypot(*np.diff(xy, axis=0).T)]
    is_held = np.isin(frames, np.asarray(list(held), int)) if len(held) else np.zeros(len(frames), bool)
    fresh = step[~is_held & np.isfinite(step)]
    still = step < max(REPEAT_PX, REPEAT_SHARE * float(np.median(fresh))) if len(fresh) else step < REPEAT_PX
    return [int(n) for n in frames[is_held & still]]


def of_stage(ns, fps, moves, fields, scene=None, raw=None, draws=DRAWS):
    """{name: the reading of each track `flicker.measure` measured}, from its own centroid on every frame (`moves`,
    [{name: (x, y)}] over the frames ns, as `curves` collects them) and the stage's fields (the spans, the held pictures,
    the codec's lines, the band's top, each beat). The camera's motion is taken out where it can be, and `how` says how:
    "scene" -- less the registered scene's path (`scene`: {"frames", "path" [(dy, dx)]}, from `scene_shift`); "members" --
    less the mean position of the other members in view with it; else "picture", the track as the picture has it, with
    `own` None: nothing says whose motion a rhythm in it is. `own` is True where a rhythm stands with the camera's motion
    out and is larger than a brightness beating over an uneven background makes one (`within_background` False), False
    where none stands, None where nothing can say. `raw`, the stage's curves ({name: brightness on each frame of ns}), gives each track its
    brightness for `reading`'s `bright`."""
    ns = list(ns)
    lo = ns[0]
    spans = fields.get("spans") or {}
    pic = fields.get("pictures") or {}
    held = [ns[k] for k in (pic.get("held_k") or []) if 0 <= k < len(ns)]
    top = fields.get("top_hz") or pic.get("top_hz") or TOP * fps / 2
    lines = codec_lines(fields.get("codec"), top)
    xy = {}
    for name, (a, b) in spans.items():
        if b - a + 1 < MIN_POINTS:
            continue
        v = np.array([(m or {}).get(name, (np.nan, np.nan)) for m in moves[a - lo:b - lo + 1]], float).reshape(-1, 2)
        if len(v) == b - a + 1:
            xy[name] = (np.arange(a, b + 1), v)
    path = None
    if scene and scene.get("path") is not None and len(scene["path"]):
        path = dict(zip([int(n) for n in scene["frames"]], np.asarray(scene["path"], float)))
    out = {}
    for name, (f, v) in xy.items():
        how, series = "picture", v
        if path is not None:
            sc = np.array([path.get(int(n), (np.nan, np.nan)) for n in f], float)
            if np.isfinite(sc[:, 0]).mean() >= COVER:
                how, series = "scene", v - sc[:, ::-1]           # the path is (dy, dx)
        if how == "picture" and len(xy) > 1:
            others = []
            for other, (fo, vo) in xy.items():
                if other == name:
                    continue
                o = np.full_like(v, np.nan)
                both = (f >= fo[0]) & (f <= fo[-1])
                o[both] = vo[f[both] - fo[0]]
                if np.isfinite(o[:, 0]).mean() >= OTHERS_COVER:
                    others.append(o)
            if others:
                how, series = "members", v - np.mean(others, axis=0)     # NaN where any of them is out of view
        b = (fields.get("beat") or {}).get(name)
        own = (raw or {}).get(name)
        bright = (np.array([np.nan if q is None else q for q in own[f[0] - lo:f[-1] - lo + 1]], float)
                  if own is not None and len(own) >= f[-1] - lo + 1 else None)
        r = reading(f, series[:, 0], series[:, 1], fps, top=top, held=still_held(f, v, held), lines=lines, beat=b, bright=bright,
                    background=background_level(raw, name, f[0] - lo, f[-1] - lo + 1), draws=draws)
        r["how"] = how
        r["against"] = len(others) if how == "members" else None
        ab = r.get("at_beat") or {}
        found = bool(r.get("line") or ab.get("line"))
        # a rhythm at the brightness beat is held to what the background can make of a beating brightness (True, False, or
        # None where the lever was not read); one found where the brightness has no beat needs no such holding
        beyond = (ab.get("without_brightness") or {}).get("beyond_background") if ab.get("line") else (True if r.get("line") else None)
        # its own: True where a rhythm stands with the camera's motion out and is more than an uneven background under a
        # beating brightness gives; False where none stands; None where nothing can say (the picture's, within that reach,
        # or the reach not read)
        video = bool(ab.get("line") and ab.get("at_the_codec_line_hz") is not None)      # at one of the video's own lines: may be the video's
        r["own"] = None if (how == "picture" or not r["power"]) else (False if not found else (True if beyond is True and not video else None))
        r["within_background"] = bool(found and beyond is False)
        out[name] = r
    return out


def _pm(hz, err):
    return f"{hz:.2f} Hz" if not err else f"{hz:.2f} ± {err:.2f} Hz"


HOW = {"scene": "the scene's motion taken out", "members": "against the other objects in view", "picture": "as the picture has it"}


def line_said(r):
    """One reading as the stage's result line: the rhythm in the position, its chance, and how the camera's motion stood."""
    if not r.get("power"):
        return "not read: " + (r.get("why") or "")
    ab = r.get("at_beat")
    if ab and ab["line"]:
        what = (f"{_pm(ab['position_hz'], ab['position_hz_err'])}, {math.hypot(*ab['amplitude_px']):.2f} px, chance {ab['p']:.3f}: "
                + {"the beat": "the brightness beat's rate", "its double": "twice the brightness beat's rate",
                   "its half": "half the brightness beat's rate"}[ab["at"]])
    elif r["line"]:
        what = f"{_pm(r['hz'], r['hz_err'])}, {math.hypot(*r['amplitude_px']):.2f} px, chance {r['p']:.3f}"
    else:
        what = f"no rhythm (the strongest {r['hz']:.2f} Hz, chance {r['p']:.2f}; {r['needed_px']:.2f} px would have shown three times in four)"
    return f"{what}; {HOW[r['how']]}" + ("" if r["how"] != "picture" else ", so whose motion it is cannot be told")


def said(name, r, several=False):
    """One reading in a few sentences, for the stage's notes: what the track carries, at what chance, whether it is the
    brightness's rhythm, and whose motion it can be said to be."""
    who = f" ({name})" if several else ""
    if not r.get("power"):
        return f"The beat in the position{who} was not read: {r.get('why')}."
    ab = r.get("at_beat")
    amp = lambda a: f"{math.hypot(*a):.2f} pixels"
    took = {"scene": "with the scene's own motion taken out", "members": "measured against the other objects in view",
            "picture": "as the picture has it"}[r["how"]]
    null = "a track with only its own wander and jitter"
    if ab and ab["line"]:
        rate = {"the beat": "the rate of its brightness beat", "its double": "twice the rate of its brightness beat",
                "its half": "half the rate of its brightness beat"}[ab["at"]]
        head = (f"Its position{who}, {took}, rises and falls at {_pm(ab['position_hz'], ab['position_hz_err'])} by {amp(ab['amplitude_px'])}, "
                f"{rate}. By chance {null} would show that {ab['p']:.3f} of the time."
                + ("" if ab["agrees"] else f" The two rates differ by {ab['z']:.1f} of their errors."))
    elif r["line"]:
        head = (f"Its position{who}, {took}, rises and falls at {_pm(r['hz'], r['hz_err'])} by {amp(r['amplitude_px'])}. By chance {null} "
                f"would show that {r['p']:.3f} of the time." + (f" That is not the rate of its brightness beat, {ab['hz']:.2f} Hz." if ab else ""))
    else:
        head = (f"Its position{who}, {took}, shows no rhythm beyond its own wander and jitter. The strongest, at {r['hz']:.2f} Hz, comes "
                f"by chance {r['p']:.2f} of the time. One of about {r['needed_px']:.2f} pixels would have shown three times in four."
                + ("" if not ab else
                   f" At the rate of its brightness beat, {ab['hz']:.2f} Hz, its position moves by {amp(ab['amplitude_px'])} at most, "
                   f"which chance gives {ab['p']:.2f} of the time. So the beat is not shown in its position."))
    tail = ""
    wb = (ab or {}).get("without_brightness")
    if ab and ab["line"] and wb and wb.get("px_per_brightness") is not None and wb.get("reach_px") is not None:
        lever = f"{wb['px_per_brightness']:.2f} pixels for each unit of brightness change"
        tail += (f" That is {lever}. A brightness beating over a background as uneven as this one moves a measured position "
                 f"{wb['reach_px']:.2f} at most, so this is more." if wb["beyond_background"] else
                 f" That is {lever}. A brightness beating over a background as uneven as this one can move a measured position "
                 f"{wb['reach_px']:.2f}, so the object may not move at all.")
        if not wb["line"]:
            tail += f" The rhythm goes in step with its brightness: with that taken out, none is left (chance {wb['p']:.2f})."
    if r["how"] == "picture" and (r["line"] or (ab and ab["line"])):
        tail += (" The camera's own motion was not taken out, so this may be the camera's shake. It is the object's own only if the "
                 "camera held still. The scene registered, or a second object in view, would show which.")
    elif r.get("own") is True:
        tail += " A camera's gain can change a brightness, but it cannot move a position."
    c = r.get("codec")
    if ab and ab["line"] and ab.get("at_the_codec_line_hz"):
        tail += (f" That rate is within the beat's error of one of the video's own rhythms ({ab['at_the_codec_line_hz']:.2f} Hz: its coding, "
                 "or the pictures it holds), so the rhythm may be the video's.")
    elif c and c.get("line") and not (ab and ab["line"] and abs(c["hz"] - ab["position_hz"]) <= r["resolution_hz"]):
        tail += (f" The position also moves at one of the video's own rhythms ({c['hz']:.2f} Hz: its coding, or the pictures it holds), "
                 "which is left out.")
    return head + tail
