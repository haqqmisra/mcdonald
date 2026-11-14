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
cosine left out), each read the same way: not white noise, which finds beats everywhere. The variogram's hole is read
beside it (`hole`), against the same draws. Where the brightness beats, the same average is read at the beat's own
frequency, at its double and at its half, a frequency given beforehand each (`at_beat`).

Whose motion it is. A track in the picture is the object's motion less the camera's, and a camera that shakes puts
its shake in every track. So the reading is the object's own only where the camera's motion is out: the track taken
against the registered scene (`scene_shift`'s path), or against the other members of its group, whose mean position
moves with the camera (`of_stage`). Otherwise the reading is given as the picture has it, with no power to say whose
motion it is, and says what would give it. The video's own rhythm is in a position too: where an encoder holds part of
the picture on its predicted frames, a centroid stops and starts at the codec's rate, so the codec's lines are left out
of the search and said (`codec`).

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
COVER = 0.6            # the share of a stretch's frames that must have a position
FIT_MAX = 300          # points the covariance is fitted on, the middle of the track (one REML fit a coordinate)
DRAWS = 1000           # tracks drawn from the fitted covariance, with no rhythm, that the reading is held against
SEED = 20261113        # their seed: the same track gives the same reading twice
ALPHA = 0.01           # a periodic part is one where fewer than this share of the drawn tracks stand as high anywhere in the band
PAD = 8                # the spectrum's zero padding
Z_AGREE = 3.0          # the position's and the brightness's frequencies agree within this many of their combined errors
NEAR_RES = 1.0         # resolutions of a stretch either side of a frequency given beforehand that are "at" it
FLOOR_PX = 1e-3        # px: the least jitter a drawn track is given (a track written on a grid can fit none)
OTHERS_COVER = 0.8     # a fellow member is held against where it is in view on this share of the member's own frames
REPEAT_PX = 0.02       # px: on a picture the video holds, a centroid that moved less than this from the frame before is the
#                        same picture read again, a missing sample; one that moved more was coded afresh (an encoder that
#                        skips a still sky holds the frame's thumbnails and not the object: Galileo's flyers, 45-78 % "held")


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


def reading(frames, x, y, fps, top=None, held=(), lines=(), beat=None, draws=DRAWS, seed=SEED, hole=True):
    """The periodic part of one series of positions (the docstring above): dict(power, why, frames, points, stretches,
    stretch_s, hz, hz_err, p, stands, needed, line, amplitude_px (x, y), needed_px, axis, where (the stretches it stands
    in), fit, hole, codec, at_beat, draws). `lines` are the codec's lines (Hz), left out of the search within NEAR_RES
    resolutions and read apart (`codec`). `beat`, where the brightness beats, is {"hz", "hz_err", "double_hz"}
    (`flicker`'s `beat[name]`): the reading is then made at those frequencies too (`at_beat`). power False, with `why`,
    where the series is too short or too broken to read."""
    f0, P = dense(frames, x, y, held)
    out = dict(power=False, why=None, frames=[f0, f0 + len(P) - 1] if len(P) else None,
               points=int(np.isfinite(P[:, 0]).sum()) if len(P) else 0)
    top = float(top) if top else TOP * fps / 2
    n = len(P)
    if out["points"] < MIN_POINTS:
        out["why"] = f"{out['points']} frames with a position, under the {MIN_POINTS} a rhythm needs"
        return out
    w = trend_frames(fps)
    segs = [(a, b) for a, b in stretches(n, fps) if np.isfinite(P[a:b, 0]).mean() >= COVER]
    if not segs:
        out["why"] = f"no stretch of {SEG_S:g} s has a position on {COVER:.0%} of its frames"
        return out
    t = np.arange(n) / fps
    okp = np.isfinite(P[:, 0])
    theta = [_fit(t, P[:, c]) for c in (0, 1)]
    out["fit"] = {name: dict(wander_px=math.sqrt(th[0]), range_s=th[1], jitter_px=math.sqrt(th[2])) for name, th in zip("xy", theta)}
    R = P - _running(P, w)                                   # the track against its own running mean
    R = R - np.nanmean(R, axis=0)
    rng = np.random.default_rng(seed)
    L = segs[0][1] - segs[0][0]
    res = fps / L
    lags = np.arange(1, max(3, int(round(fps / LOW))) + 1)
    lags = lags[lags < L // 2]
    S = Sd = H = Hd = fr = None                              # the stretches' standardized spectra and holes, summed: the track's, the draws'
    per_seg, drawn = [], np.zeros(2)
    # the draws are made three stretches at a time (two stretches' length), each block drawn from the one fitted
    # covariance on its own frames: beyond the running mean's reach the stretches of a wander are independent, and one
    # Cholesky of the whole of a long track would cost its cube
    for i in range(0, len(segs), 3):
        blk = segs[i:i + 3]
        a0, b0 = blk[0][0], blk[-1][1]
        D = [_draws(t[a0:b0], okp[a0:b0], theta[c], rng, draws) for c in (0, 1)]
        D = [d - _running(d, w) for d in D]
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
    at_codec = np.zeros(len(fr), bool)
    for c in lines or ():
        at_codec |= np.abs(fr - c) <= NEAR_RES * res
    search = band & ~at_codec
    if not search.any():
        out["why"] = "the codec's lines fill the band a rhythm is looked for in"
        return out
    j = np.flatnonzero(search)[int(np.argmax(S[search]))]
    stat = float(S[j])
    null = Sd[search].max(axis=0)
    p = float((1 + np.sum(null >= stat)) / (1 + draws))
    hz = float(fr[j])
    lvl = float(np.quantile(null, 1 - ALPHA))
    amp = _amplitude(R, fps, hz, per_seg)
    near = search & (np.abs(fr - hz) <= NEAR_RES * res)
    where = ([[int(f0 + a), int(f0 + b - 1)] for a, b, Z, _ in per_seg if Z[near].max() >= max(lvl, 0.5 * stat)] if K > 1 else
             [[int(f0 + segs[0][0]), int(f0 + segs[0][1] - 1)]])
    # the smallest rhythm that would have stood at the level, along the quieter coordinate, at the band's middle frequency:
    # what the track's own wander and jitter leave room to hear
    need = [float(np.sqrt(max(lvl - 1.0, 0.0) * np.median(np.mean([e[c][search] for *_, e in per_seg], axis=0)))) for c in (0, 1)]
    out.update(power=True, stretches=K, stretch_s=L / fps, hz=hz, p=p, stands=stat, needed=lvl, line=bool(p < ALPHA),
               amplitude_px=[float(amp[0]), float(amp[1])], needed_px=float(min(need)), axis="y" if amp[1] >= amp[0] else "x",
               where=where, draws=int(draws), resolution_hz=float(res), top_hz=top)
    out["hz_err"] = _hz_err(R, fps, hz, per_seg, int(amp[1] >= amp[0]))
    if at_codec.any() and (band & at_codec).any():
        k = np.flatnonzero(band & at_codec)[int(np.argmax(S[band & at_codec]))]
        out["codec"] = dict(hz=float(fr[k]), stands=float(S[k]), line=bool(S[k] >= lvl), lines_hz=[float(c) for c in lines])
    if hole and H is not None:
        H, Hd = H / K, Hd / K
        mu, sd = Hd.mean(axis=1), Hd.std(axis=1)
        sd = np.where(sd > 0, sd, np.inf)
        fh = fps / hs
        ok = (fh >= LOW) & (fh <= top) & np.array([all(abs(f - c) > NEAR_RES * res for c in lines or ()) for f in fh])
        if ok.any():
            z, zd = (H - mu) / sd, (Hd - mu[:, None]) / sd[:, None]
            i = np.flatnonzero(ok)[int(np.argmax(z[ok]))]
            out["hole"] = dict(lag_frames=int(hs[i]), hz=float(fh[i]), depth=float(H[i]), drawn=float(mu[i]),
                               p=float((1 + np.sum(zd[ok].max(axis=0) >= z[i])) / (1 + draws)))
    if beat and beat.get("hz"):
        out["at_beat"] = _at_beat(beat, S, Sd, fr, search, res, R, fps, per_seg, draws)
    return out


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


def _at_beat(beat, S, Sd, fr, search, res, R, fps, per_seg, draws):
    """The reading at the brightness beat: the average spectrum's strongest within NEAR_RES resolutions (or Z_AGREE of
    the beat's error, if more) of the beat, of its double and of its half -- frequencies given beforehand, so the band
    is not searched; the chance is the least of the three, times the number tried. dict(hz (the brightness's), tried,
    at ("the beat", "its double", "its half": where the position stood highest), at_hz, position_hz, position_hz_err,
    amplitude_px, p, line, stands, z (the two frequencies apart, in their combined errors), agrees)."""
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
    return dict(hz=float(beat["hz"]), tried=[g[2] for g in got], at=what, at_hz=c, position_hz=hz, position_hz_err=err,
                amplitude_px=[float(amp[0]), float(amp[1])], p=p, line=bool(p < ALPHA), stands=-stat, z=z,
                agrees=bool(p < ALPHA and (z is None or z <= Z_AGREE)))


# ---- the stage's reading: whose motion ---------------------------------------------------------------------------
def still_held(frames, xy, held):
    """The frames among `held` (frames whose picture the video repeats, `flicker.pictures`' held_k as frame numbers) on
    which the centroid `xy` ([n, 2] over `frames`) also stood still: within REPEAT_PX of the frame before. Those are the
    picture read again, and are left out as missing samples."""
    frames = np.asarray(frames, int)
    xy = np.asarray(xy, float)
    step = np.r_[np.inf, np.hypot(*np.diff(xy, axis=0).T)]
    still = {int(n) for n, s in zip(frames, step) if s < REPEAT_PX}
    return sorted(still & {int(n) for n in held})


def of_stage(ns, fps, moves, fields, scene=None, draws=DRAWS):
    """{name: the reading of each track `flicker.measure` measured}, from its own centroid on every frame (`moves`,
    [{name: (x, y)}] over the frames ns, as `curves` collects them) and the stage's fields (the spans, the held pictures,
    the codec's lines, the band's top, each beat). The camera's motion is taken out where it can be, and `how` says how:
    "scene" -- less the registered scene's path (`scene`: {"frames", "path" [(dy, dx)]}, from `scene_shift`); "members" --
    less the mean position of the other members in view with it; else "picture", the track as the picture has it, with
    `own` None: nothing says whose motion a rhythm in it is. `own` is True where a rhythm stands with the camera's motion
    out, False where none does."""
    ns = list(ns)
    lo = ns[0]
    spans = fields.get("spans") or {}
    pic = fields.get("pictures") or {}
    held = [ns[k] for k in (pic.get("held_k") or []) if 0 <= k < len(ns)]
    lines = (fields.get("codec") or {}).get("lines_hz") or []
    top = fields.get("top_hz") or pic.get("top_hz")
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
        r = reading(f, series[:, 0], series[:, 1], fps, top=top, held=still_held(f, v, held), lines=lines, beat=b, draws=draws)
        r["how"] = how
        r["against"] = len(others) if how == "members" else None
        r["own"] = None if (how == "picture" or not r["power"]) else bool(r["line"] or (r.get("at_beat") or {}).get("line"))
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
        what = f"no rhythm (the strongest {r['hz']:.2f} Hz, chance {r['p']:.2f}; {r['needed_px']:.2f} px would have shown)"
    return f"{what}; {HOW[r['how']]}" + ("" if r["how"] != "picture" else ", so whose motion it is cannot be told")


def said(name, r, several=False):
    """One reading in a sentence or two, for the stage's notes: what the track carries, at what chance, whether it is the
    brightness's rhythm, and whose motion it can be said to be."""
    who = f" ({name})" if several else ""
    if not r.get("power"):
        return f"The beat in the position{who} was not read: {r.get('why')}."
    ab = r.get("at_beat")
    amp = lambda a: f"{math.hypot(*a):.2f} px"
    took = {"scene": "with the scene's own motion taken out", "members": "against the other objects in view with it",
            "picture": "as the picture has it"}[r["how"]]
    if ab and ab["line"]:
        head = (f"Its position{who}, {took}, moves at {_pm(ab['position_hz'], ab['position_hz_err'])} by {amp(ab['amplitude_px'])}"
                f" (chance {ab['p']:.3f} against its own wander, at a frequency given beforehand), "
                + ("the rate of its brightness beat" if ab["at"] == "the beat" else
                   f"{'twice' if ab['at'] == 'its double' else 'half'} the rate of its brightness beat")
                + ("" if ab["agrees"] else f", though the two differ by {ab['z']:.1f} of their errors"))
    elif r["line"]:
        head = (f"Its position{who}, {took}, moves at {_pm(r['hz'], r['hz_err'])} by {amp(r['amplitude_px'])} (chance {r['p']:.3f} "
                "against its own wander)" + (f", which is not the rate of its brightness beat ({ab['hz']:.2f} Hz)" if ab else ""))
    else:
        head = (f"Its position{who}, {took}, carries no rhythm beyond its own wander (the strongest, at {r['hz']:.2f} Hz, comes by "
                f"chance {r['p']:.2f} of the time); one of about {r['needed_px']:.2f} px would have shown"
                + (f". Its brightness beat at {ab['hz']:.2f} Hz is not in its position" if ab else ""))
    tail = ""
    if r["how"] == "picture" and (r["line"] or (ab and ab["line"])):
        tail = (" The camera's own motion was not taken out, so this may be the camera's. It is the object's own only on a "
                "camera that held still; the scene registered, or a second object in view, would show it")
    elif r["how"] != "picture" and (r["line"] or (ab and ab["line"])):
        tail = " A camera's gain cannot move a position, so this rhythm is not the gain's"
    c = r.get("codec")
    if c and c.get("line"):
        tail += f". The position also moves at the codec's own rate ({c['hz']:.2f} Hz), which is the video's and is left out"
    return head + "." + (tail + "." if tail else "")
