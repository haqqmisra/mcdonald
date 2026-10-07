"""Is something tethered to the object -- a line or a payload that moves with it -- and does it swing?

A sounding balloon carries its radiosonde 25-55 m below it on a line; a hobby balloon a
few grams a metre or two below. A pilot's "strings hanging off" (the Lake Huron object
of 2023-02-12, PR071) is the same thing. Nothing else in the sky is a body with a point
hanging under it, and a hanging point is a pendulum: its period is set by gravity and
the line, T = 2 pi sqrt(L/g), so T read off the video in seconds gives L in metres with
no range and no field of view, and the line's length in pixels then scales the whole
image. That is the balloon analogue of PR135's wingbeat.

The question is asked in two parts (`stack` with `candidates` and `support`, then `follow`
and `swing`):

1. **Does anything move with the object?** Every frame, overlay masked, is shifted so
   the tracked position lands at the centre and the frames are averaged: a thing tied
   to the object adds up at its offset; the scene and the overlay smear by however far
   the object moved on the screen. A candidate is a compact feature of that stack, `Z_MIN`
   times its noise, between `r_min` and `r_max` object sizes of the centre. Three things
   then say whether it is the object's:
   - *the control*: the same frames stacked on the track run backwards in time have the
     same set of positions and the wrong one each frame, so a thing tied to the object
     smears there while anything that only looked sharp because the object hardly moved
     stays sharp (PR055's edge peaks reappeared there identically). `z_control` at most
     `CONTROL` of `z`.
   - *single frames*: a thing tied to the object is there at its offset on single frames,
     `FRAME_Z` times the frame's noise (by MAD over a wide crop, so the overlay's lines do
     not set it), on `SUPPORT` of them, and at the same place to within `JITTER_PX`
     across its own spread (along a line the darkest point wanders, and that is not a
     jitter). Cloud texture is dark *somewhere* in a patch on many frames, but spread
     over the patch (PR055: 11-14 px); PR071's string sits at 4.
   - *with the object or with the scene*: the candidate followed frame by frame (below)
     moves with the object rather than with the background's own shift
     (`groups.with_the_group`), when the object moves at least `STILL` px against the
     scene. The one test that catches a piece of cloud drifting steadily past.
   A payload that swings more than a patch is at its mean offset on few single frames:
   the strongest features the control does not show are followed anyway, and one that
   moves smoothly (`SMOOTH`) and with the object is kept.
   A tracking gate's box *is* tied to the object -- by the tracker, late -- and its
   edges can pass (PR071's, at 5-8 px of jitter); they are reported, not hidden, and the
   figure shows them for what they are. When the object moves less than `STILL` px on
   the screen, nothing can be told apart and the stage says so.
2. **Does it swing?** The companion -- the one kept, or an offset given with --seed --
   is followed: in a gate about where it was last, the compact feature of its polarity.
   The separation vector from the object gives the swing angle (0 = straight down the
   image, + = to the right), which needs no scale and survives any camera motion short
   of a roll. A Lomb-Scargle periodogram starts it; the estimator is a sinusoid with a
   drift fitted to the angle, kept when it is clean (residual under half the amplitude)
   and covers `MIN_CYCLES` cycles of the window -- a periodogram's peak on a window of a
   few cycles slides up to whatever cap the window sets, and a peak at the longest
   period asked is never a period. `line_length_m` = g T^2 / 4 pi^2. The pivot of a
   balloon's pendulum is the balloon's centre, not its neck: on the one calibration
   with ground truth (WA9ONY-5, a 13 g pico payload "a little over one metre" below the
   balloon, 2021-07-13, 1.7 cycles) the swing gave 2.57 s and 1.64 m, the line plus the
   balloon's radius and the payload's own offset.

What it cannot do: a payload too faint for single frames that swings more than its own
size evades the stack (it smears by its swing) and the follower both; that needs a
search over the pendulum's own motion, not done here. A line held at a steady angle by
drag (PR071: no swing in 8 s) gives no length. And the companion's pixel offset is in
pixels for the reasons every separation is; only the period is a metre.
"""
import csv

import numpy as np
from scipy.ndimage import gaussian_filter

from . import forensics as vf
from .progress import counted, to_stderr
from .report import Found, emit, inputs_of, said_to_stderr

R_MIN = 1.2          # x the object's size: the first ring a companion is looked for in (inside is the object)
R_MAX = 40.0         # x the object's size: a radiosonde hangs 10-35 diameters below a sounding balloon
Z_MIN = 5.0          # a candidate is at least this many times the stack's noise (DoG units)
CONTROL = 0.6        # ... and the reversed-track control shows at most this share of it at the same place
STILL = 20.0         # px moved on the screen below which nothing can be told from the overlay or the scene
SIGMA = 1.2          # DoG inner scale, px: a line or a point a few px across
SIGMA_OUT = 6.0      # DoG outer scale, px
MIN_CYCLES = 1.5     # a period is claimed from this many cycles seen: a clean sinusoid over 1.5 fixes it to ~10%
SWING_POWER = 0.3    # Lomb-Scargle normalised power below which the angle is called steady
GATE = 0.25          # per frame, the companion may move this share of its separation from where it was predicted
MIN_SWING_FRAMES = 20
G = 9.80665


def stack(clip, track, masks, rows=None, reverse=False, radius=None, progress=None, stop=None, label="Stack"):
    """(mean image, count) of the clip's frames centred on the track: pixel (R, R) is the
    object. With `reverse`, frame n is placed by the position of the track's mirror frame."""
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    R = int(radius or max(clip.W, clip.H))
    S = 2 * R + 1
    acc, cnt = np.zeros((S, S), np.float64), np.zeros((S, S), np.float64)
    pos = [track[n] for n in ns]
    for i, n in enumerate(counted(ns, progress, stop, label)):
        rgb = clip.rgb(n)
        g = vf.grey_of(rgb).astype(np.float64)
        bad = vf.frame_mask(rgb, masks, rows, n, grow=2)
        w = (~bad).astype(np.float64)
        x, y = pos[len(ns) - 1 - i] if reverse else pos[i]
        ox, oy = int(round(R - x)), int(round(R - y))
        x0, y0 = max(ox, 0), max(oy, 0)
        x1, y1 = min(ox + clip.W, S), min(oy + clip.H, S)
        if x1 <= x0 or y1 <= y0:
            continue
        sub = g[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        ws = w[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
        acc[y0:y1, x0:x1] += sub * ws
        cnt[y0:y1, x0:x1] += ws
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)
    return m, cnt


def object_size(m, cnt, R, cap=200):
    """The object's own size in the stack, px: the width at half its central contrast,
    measured along four directions and averaged. None when there is no central contrast."""
    c = m[R, R]
    ring = m[R - cap:R + cap + 1, R - cap:R + cap + 1]
    bg = np.nanmedian(ring)
    if not np.isfinite(c) or not np.isfinite(bg) or abs(c - bg) < 3:
        return None
    half = bg + 0.5 * (c - bg)
    widths = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for k in range(1, cap):
            v = m[R + k * dy, R + k * dx]
            if not np.isfinite(v) or (v - half) * np.sign(c - bg) < 0:
                widths.append(k)
                break
        else:
            widths.append(cap)
    return 2.0 * float(np.mean(widths))


def _dog(m):
    mm = np.where(np.isfinite(m), m, np.nanmedian(m))
    return gaussian_filter(mm, SIGMA) - gaussian_filter(mm, SIGMA_OUT)


def candidates(m, cnt, mc, size, R, r_min=R_MIN, r_max=R_MAX, top=40, z_min=Z_MIN, control=CONTROL):
    """Compact features of the object stack `m` between r_min and r_max object sizes of the
    centre, scored against the stack's own noise and against the reversed-track stack `mc`
    at the same place. [{...}], strongest first, `top` at most; the verdict `co_moving` is
    filled in by `support` once the frames have been looked at."""
    dog, dogc = _dog(m), _dog(mc)
    S = m.shape[0]
    yy, xx = np.mgrid[0:S, 0:S]
    rr = np.hypot(xx - R, yy - R)
    from scipy.ndimage import binary_erosion
    covered = binary_erosion(cnt >= max(3, 0.6 * cnt.max()), iterations=int(3 * SIGMA_OUT))   # the edge of the stacked area is a step the DoG answers to
    valid = covered & (rr >= r_min * size) & (rr <= r_max * size)
    if valid.sum() < 100:
        return [], float("nan")
    sig = float(np.std(dog[valid]))
    sigc = float(np.std(dogc[valid])) or sig
    z = np.where(valid, np.abs(dog) / sig, 0.0)
    out = []
    order = np.argsort(z.ravel())[::-1][:20000]
    for i in order:
        y, x = divmod(int(i), S)
        if z[y, x] < z_min:
            break
        if any(np.hypot(x - c["_x"], y - c["_y"]) < 3 * SIGMA_OUT for c in out):
            continue
        zc = float(abs(dogc[y, x]) / sigc)
        dx, dy = x - R, y - R
        out.append(dict(_x=x, _y=y, dx_px=float(dx), dy_px=float(dy), r_px=float(np.hypot(dx, dy)),
                        r_over_size=float(np.hypot(dx, dy) / size),
                        direction_deg=float(np.degrees(np.arctan2(dx, dy))),
                        sign="dark" if dog[y, x] < 0 else "bright",
                        contrast_dn=float(m[y, x] - np.nanmedian(m[max(y - 30, 0):y + 31, max(x - 30, 0):x + 31])),
                        z=float(z[y, x]), z_control=zc, frames=int(cnt[y, x]),
                        not_on_control=bool(zc <= control * z[y, x]), seen_on_frames=None, co_moving=False))
        if len(out) >= top:
            break
    return out, sig


SUPPORT = 0.3        # a companion is seen on at least this share of single frames at its offset ...
FRAME_Z = 2.5        # ... at this many times the frame's own noise there
STRONG = 2.0         # x Z_MIN: a stack feature this strong is kept even when single frames cannot show it
SMOOTH = 0.08        # x its distance: a followed companion moves at most this much a frame (a pendulum's payload,
                     # 2.5 s and 14 deg on 170 px, 2 %); texture caught in the gate jumps by the gate
JITTER_PX = 6.0      # px, across its own spread: a thing tied to the object is at the same place on every frame to
                     # within this (PR071's string: 4; WA9ONY's payload sweeps an arc, 4 across it); texture that happens
                     # to be dark somewhere in the patch is spread over it (PR055's clouds: 11-14); a tracking gate's box is
                     # centred on the object by the tracker, late, and its edges jitter by the lag (PR071: 5-8)


def support(clip, track, masks, rows, cands, progress=None, stop=None):
    """Fill in `seen_on_frames` (the share of frames on which the feature is there at its offset,
    FRAME_Z times the frame's noise in a patch about it, with the same sign) and the verdict
    `co_moving`: not on the control, and either seen on SUPPORT of the frames or STRONG x Z_MIN."""
    if not cands:
        return cands
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    w = int(4 * SIGMA_OUT)
    hits = np.zeros(len(cands)); seen = np.zeros(len(cands)); where = [[] for _ in cands]
    for n in counted(ns, progress, stop, "Frames"):
        rgb = clip.rgb(n)
        g = vf.grey_of(rgb).astype(np.float64)
        bad = vf.frame_mask(rgb, masks, rows, n, grow=2)
        ox, oy = track[n]
        # the frame's own noise, once: the DoG over a wide crop about the object, by MAD, so the
        # overlay's lines and the object itself (a small share of it) do not set it
        X0, Y0 = int(max(ox - 256, 0)), int(max(oy - 256, 0))
        X1, Y1 = int(min(ox + 256, clip.W)), int(min(oy + 256, clip.H))
        wide = g[Y0:Y1, X0:X1].copy()
        wide[bad[Y0:Y1, X0:X1]] = np.nan
        dw = _dog(wide)[3 * int(SIGMA_OUT):-3 * int(SIGMA_OUT), 3 * int(SIGMA_OUT):-3 * int(SIGMA_OUT)]
        dw = dw[np.isfinite(dw)]
        noise = float(1.4826 * np.median(np.abs(dw - np.median(dw)))) if dw.size else 0.0
        if noise <= 0:
            continue
        for k, c in enumerate(cands):
            x, y = int(round(ox + c["dx_px"])), int(round(oy + c["dy_px"]))
            if not (w <= x < clip.W - w and w <= y < clip.H - w):
                continue
            sub = g[y - w:y + w + 1, x - w:x + w + 1].copy()
            sub[bad[y - w:y + w + 1, x - w:x + w + 1]] = np.nan
            if not np.isfinite(sub).sum() > 0.8 * sub.size:
                continue
            d = _dog(sub)
            core = d[w - 2:w + 3, w - 2:w + 3]
            v = core.min() if c["sign"] == "dark" else core.max()
            seen[k] += 1
            hit = (abs(v) / noise >= FRAME_Z) and ((v < 0) == (c["sign"] == "dark"))
            hits[k] += hit
            if hit:                                       # where in the patch the feature is on this frame
                dd = np.where(np.isfinite(d), d, 0.0)
                iy, ix = np.unravel_index(int(np.argmin(dd) if c["sign"] == "dark" else np.argmax(dd)), dd.shape)
                where[k].append((ix - w, iy - w))
    for k, c in enumerate(cands):
        c["seen_on_frames"] = float(hits[k] / seen[k]) if seen[k] else None
        pts = np.array(where[k]) if len(where[k]) >= 3 else None
        # across its own spread: along a line the extreme wanders freely, and is not a jitter
        c["jitter_px"] = float(np.sqrt(max(np.linalg.eigvalsh(np.cov(pts.T)).min(), 0.0))) if pts is not None else None
        steady = c["jitter_px"] is None or c["jitter_px"] <= JITTER_PX
        c["co_moving"] = bool(c["not_on_control"] and ((c["seen_on_frames"] or 0) >= SUPPORT or c["z"] >= STRONG * Z_MIN)
                              and steady)
    return cands


def follow(clip, track, masks, rows, seed, dark=None, size=None, progress=None, stop=None):
    """The companion frame by frame from an offset `seed` (dx, dy) on the first frame:
    {frame: (x, y, contrast)}. The feature of its polarity (`dark` None: whichever is
    stronger at the seed) nearest where it was predicted, within GATE of the separation."""
    from .propose import background_shift
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    off = np.array(seed, float)
    got, bg, last = {}, {}, None
    for n in counted(ns, progress, stop, "Swing"):
        rgb = clip.rgb(n)
        g = vf.grey_of(rgb).astype(np.float64)
        bad = vf.frame_mask(rgb, masks, rows, n, grow=2)
        if last is None:
            bg[n] = (0.0, 0.0)
        else:
            d = background_shift(last[1], g.astype(np.float32), ~(bad | last[2]))
            bg[n] = (bg[last[0]][0] + d[0], bg[last[0]][1] + d[1])
        last = (n, g.astype(np.float32), bad)
        ox, oy = track[n]
        px, py = ox + off[0], oy + off[1]
        gate = max(GATE * np.hypot(*off), 4 * SIGMA_OUT)
        x0, y0 = int(max(px - gate - 3 * SIGMA_OUT, 0)), int(max(py - gate - 3 * SIGMA_OUT, 0))
        x1, y1 = int(min(px + gate + 3 * SIGMA_OUT + 1, clip.W)), int(min(py + gate + 3 * SIGMA_OUT + 1, clip.H))
        if x1 - x0 < 8 or y1 - y0 < 8:
            continue
        sub = g[y0:y1, x0:x1].copy()
        sub[bad[y0:y1, x0:x1]] = np.nan
        d = _dog(sub)
        if dark is None:
            cy, cx = int(round(py - y0)), int(round(px - x0))
            cy, cx = min(max(cy, 0), d.shape[0] - 1), min(max(cx, 0), d.shape[1] - 1)
            dark = bool(d[cy, cx] < 0)
        resp = -d if dark else d
        yy, xx = np.mgrid[y0:y1, x0:x1]
        inside = np.hypot(xx - px, yy - py) <= gate
        # keep away from the object itself
        inside &= np.hypot(xx - ox, yy - oy) >= max(0.6 * (size or 0), 2 * SIGMA_OUT)
        resp = np.where(inside, resp, -np.inf)
        if not np.isfinite(resp).any():
            continue
        k = int(np.argmax(resp))
        iy, ix = divmod(k, resp.shape[1])
        if resp[iy, ix] <= 0:
            continue
        # centroid of the half-max patch about the peak
        m = (resp >= 0.5 * resp[iy, ix]) & np.isfinite(resp)
        m &= np.hypot(xx - (x0 + ix), yy - (y0 + iy)) <= 2 * SIGMA_OUT
        w = np.where(m, resp, 0.0)
        cx_, cy_ = float((xx * w).sum() / w.sum()), float((yy * w).sum() / w.sum())
        got[n] = (cx_, cy_, float(sub[iy, ix] - np.nanmedian(sub)))
        off = np.array([cx_ - ox, cy_ - oy])
    return got, dark, bg


def with_the_object(companion, track, bg):
    """(moves with the object rather than the scene, the object's own motion against the scene in px):
    over the frames followed, the companion's displacement is nearer the object's than the
    background's (groups.with_the_group). Under STILL px the two cannot be told apart."""
    from .groups import with_the_group, _against
    ns = [n for n in sorted(companion) if n in track and n in bg]
    if len(ns) < 2:
        return None, 0.0
    moved = _against(track, bg, ns)
    return (bool(with_the_group({n: companion[n][:2] for n in ns}, track, bg)) if moved >= STILL else None), moved


def swing(track, companion, fps):
    """The companion's separation and angle, frame by frame, and whether the angle swings:
    dict of fields (see the module doc)."""
    ns = sorted(n for n in companion if n in track)
    if len(ns) < MIN_SWING_FRAMES:
        return dict(frames=len(ns), finding=f"the companion was followed on {len(ns)} frames, fewer than {MIN_SWING_FRAMES}")
    t = np.array([(n - ns[0]) / fps for n in ns])
    sx = np.array([companion[n][0] - track[n][0] for n in ns])
    sy = np.array([companion[n][1] - track[n][1] for n in ns])
    sep = np.hypot(sx, sy)
    ang = np.degrees(np.arctan2(sx, sy))
    span = t[-1] - t[0]
    step = np.hypot(np.diff(sx), np.diff(sy)) / np.maximum(np.diff(np.array(ns, float)), 1)
    out = dict(frames=len(ns), first=ns[0], last=ns[-1], span_s=float(span), separation_px=float(np.median(sep)),
               separation_range_px=[float(sep.min()), float(sep.max())],
               step_over_separation=float(np.median(step) / max(np.median(sep), 1e-6)),
               angle_mean_deg=float(ang.mean()), angle_sd_deg=float(ang.std()))
    out["smooth"] = bool(out["step_over_separation"] <= SMOOTH)
    if span < 1.0 or len(ns) < 10:
        out["finding"] = "too short to ask whether the angle swings"
        return out
    from scipy.signal import lombscargle
    trend = np.polyval(np.polyfit(t, ang, 1), t)
    P = np.linspace(0.5, max(0.6, 1.2 * span / MIN_CYCLES), 600)
    pw = lombscargle(t, ang - trend, 2 * np.pi / P, normalize=True)
    k = int(np.argmax(pw))
    period, power = float(P[k]), float(pw[k])
    out.update(period_s=period, power=power, cycles=float(span / period))
    # the sinusoid itself, with a drift: on a window of a few cycles this is the estimator, the
    # periodogram only its starting point (a peak slides up to whatever cap the window sets)
    amp, per_fit, resid = None, None, None
    try:
        from scipy.optimize import curve_fit

        def model(tt, A, T, ph, c, s):
            return A * np.sin(2 * np.pi * tt / T + ph) + c + s * (tt - tt.mean())

        p, cov = curve_fit(model, t, ang, p0=[ang.std() * 1.4, period, 0.0, ang.mean(), 0.0], maxfev=20000)
        amp, per_fit = float(abs(p[0])), float(abs(p[1]))
        resid = float(np.std(ang - model(t, *p)))
        if amp > 90 or not (0.5 <= per_fit <= span / MIN_CYCLES) or not np.isfinite(cov[1, 1]) or resid > 0.5 * amp:
            out.update(fit_rejected=dict(period_s=per_fit, amplitude_deg=amp, residual_deg=resid))
            amp, per_fit = None, None
        else:
            out.update(amplitude_deg=amp, period_fit_s=per_fit, period_fit_err_s=float(np.sqrt(abs(cov[1, 1]))),
                       residual_deg=resid)
    except Exception:                               # the fit is one estimator; the periodogram stands without it
        pass
    at_edge = period >= 0.9 * P[-1]
    by_periodogram = power >= SWING_POWER and out["cycles"] >= MIN_CYCLES and not at_edge
    if per_fit is None and not by_periodogram:
        out["swings"] = False
        out["line_length_m"] = None
        if at_edge or out["cycles"] < MIN_CYCLES:
            why = (f"a swing, if it is one, is slower than {span / MIN_CYCLES:.1f} s a cycle, and {span:.1f} s show fewer than "
                   f"{MIN_CYCLES:g} of them")
        else:
            why = f"steady to +-{ang.std():.1f} deg over {span:.1f} s"
        out["finding"] = f"the companion's angle does not swing: {why}; no line length from it"
        return out
    T = per_fit if per_fit is not None else period
    out["cycles"] = float(span / T)
    L = G * T ** 2 / (4 * np.pi ** 2)
    out.update(swings=True, period_used_s=float(T), line_length_m=float(L))
    out["finding"] = (f"the companion swings: period {T:.2f} s" + (f", amplitude {amp:.1f} deg" if amp else "")
                      + f", {out['cycles']:.1f} cycles -> a pendulum of {L:.2f} m from its pivot "
                      "(the balloon's centre, not its neck: the line is shorter by the balloon's radius)")
    return out


def measure(clip, track, masks=None, rows=None, size=None, seed=None, dark=None, r_min=R_MIN, r_max=R_MAX,
            out=None, progress=None, stop=None):
    """The stage. Writes <out>_tether.png, <out>_tether_candidates.csv and, when a companion is
    followed, <out>_tether_companion.csv."""
    masks = masks if masks is not None else vf.static_masks(clip)
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    if len(ns) < 5:
        return Found("tether", fields=dict(frames=len(ns)), no_power=[("tether", "fewer than 5 frames of the track are in the clip")])
    xy = np.array([track[n] for n in ns])
    moved = float(np.hypot(*(xy.max(0) - xy.min(0))))
    radius = int(min(max(clip.W, clip.H), (r_max + 2) * (size or 40)))
    m, cnt = stack(clip, track, masks, rows, radius=radius, progress=progress, stop=stop, label="Stack")
    R = radius
    est = object_size(m, cnt, R)
    size = size or est or 10.0
    mc, _ = stack(clip, track, masks, rows, reverse=True, radius=radius, progress=progress, stop=stop, label="Control")
    cands, sig = candidates(m, cnt, mc, size, R, r_min, r_max)
    cands = support(clip, track, masks, rows, cands, progress, stop)
    cands = sorted(cands, key=lambda c: (not c["co_moving"], -(c["seen_on_frames"] or 0), -c["z"]))
    cands = [c for c in cands if c["co_moving"]][:8] + [c for c in cands if not c["co_moving"]][:3]
    fields = dict(frames=len(ns), moved_on_screen_px=moved, object_size_px=float(size), object_size_measured=est is not None,
                  stack_noise_dn=sig, r_min=r_min, r_max=r_max,
                  candidates=[{k: v for k, v in c.items() if not k.startswith("_")} for c in cands])
    files, npw, notes = [], [], []
    if moved < STILL:
        npw.append(("tether: a thing on the object or on the screen",
                    f"the object moves only {moved:.0f} px on the screen over these frames: what is tied to it "
                    "cannot be told from the overlay or the scene, which stay as sharp"))
    sw, followed, best = None, {}, None
    if seed is not None:
        polarity = dark
        followed, polarity, bg = follow(clip, track, masks, rows, seed, polarity, size, progress, stop)
        sw = swing(track, followed, clip.fps)
        sw["with_the_object"], sw["object_against_scene_px"] = with_the_object(followed, track, bg)
        sw["seed"], sw["dark"] = [float(seed[0]), float(seed[1])], bool(polarity)
    else:
        # the stack's co-moving features first, then the strongest the control does not show (a payload that
        # swings is at its mean offset on few single frames): each is followed, and the first that moves with
        # the object -- not with the scene -- and smoothly is the companion. The others are marked.
        tried = [c for c in cands if c["co_moving"]][:3] + [c for c in cands if c["not_on_control"] and not c["co_moving"]][:3]
        for c in tried:
            got, pol, bg = follow(clip, track, masks, rows, (c["dx_px"], c["dy_px"]), c["sign"] == "dark", size, progress, stop)
            w = swing(track, got, clip.fps)
            w["with_the_object"], w["object_against_scene_px"] = with_the_object(got, track, bg)
            w["seed"], w["dark"] = [float(c["dx_px"]), float(c["dy_px"])], bool(pol)
            c["followed_frames"] = w["frames"]
            if w["with_the_object"] is False:
                c["co_moving"], c["scene"] = False, True
                sw = sw or w
                continue
            if c["co_moving"] or (w.get("smooth") and w["frames"] >= max(MIN_SWING_FRAMES, 0.5 * len(ns))):
                c["co_moving"], c["followed"] = True, True
                best, followed, sw = c, got, w
                break
        cands = sorted(cands, key=lambda c: (not c["co_moving"], -(c["seen_on_frames"] or 0), -c["z"]))
        fields["candidates"] = [{k: v for k, v in c.items() if not k.startswith("_")} for c in cands]
    fields["companion"] = {k: v for k, v in best.items() if not k.startswith("_")} if best else None
    fields["swing"] = sw
    if best is None and seed is None:
        finding = (f"nothing moves with the object between {r_min:g} and {r_max:g} object sizes of it at "
                   f"{Z_MIN:g} x the stack's noise ({sig:.1f} DN)" if np.isfinite(sig) else "the stack is too small to ask")
        if cands:
            finding += (f"; the {len(cands)} strongest feature(s) are as sharp on the reversed track, or not there on single "
                        "frames: the frame or the scene, not the object")
    elif best is not None:
        finding = (f"a {best['sign']} feature moves with the object {best['r_px']:.0f} px ({best['r_over_size']:.1f} object "
                   f"sizes) away at {best['direction_deg']:+.0f} deg from straight down, {best['z']:.1f} x the noise "
                   f"({best['z_control']:.1f} on the reversed track), there on {100 * (best['seen_on_frames'] or 0):.0f}% of single frames")
    else:
        finding = f"companion followed from the given offset {tuple(round(v) for v in seed)}"
    if best is None and sw and sw.get("with_the_object") is False:
        finding = (f"the stack's feature(s) move with the scene, not the object (the object moves "
                   f"{sw['object_against_scene_px']:.0f} px against the scene over the window); nothing tied to the object")
    elif sw:
        finding += "; " + sw["finding"]
        if sw.get("with_the_object") is None and sw.get("object_against_scene_px", STILL) < STILL:
            npw.append(("tether: with the object or with the scene",
                        f"the object moves only {sw['object_against_scene_px']:.0f} px against the scene over the window: "
                        "a thing of the scene at that offset cannot be told from a thing tied to the object"))
    fields["finding"] = finding
    if sw and sw.get("swings") is None and sw["frames"] >= MIN_SWING_FRAMES:
        npw.append(("tether: swing", sw["finding"]))
    if out:
        with open(f"{out}_tether_candidates.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["dx_px", "dy_px", "r_px", "r_over_size", "direction_deg", "sign", "contrast_dn", "z", "z_control", "frames", "seen_on_frames", "jitter_px", "co_moving"])
            for c in cands:
                w.writerow([round(c["dx_px"], 1), round(c["dy_px"], 1), round(c["r_px"], 1), round(c["r_over_size"], 2),
                            round(c["direction_deg"], 1), c["sign"], round(c["contrast_dn"], 1), round(c["z"], 1),
                            round(c["z_control"], 1), c["frames"], "" if c["seen_on_frames"] is None else round(c["seen_on_frames"], 2),
                            "" if c.get("jitter_px") is None else round(c["jitter_px"], 1), c["co_moving"]])
        files.append(f"{out}_tether_candidates.csv")
        if followed:
            with open(f"{out}_tether_companion.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["frame", "x_px", "y_px", "dx_px", "dy_px", "angle_deg", "contrast_dn"])
                for n, (x, y, c) in sorted(followed.items()):
                    dx, dy = x - track[n][0], y - track[n][1]
                    w.writerow([n, round(x, 2), round(y, 2), round(dx, 2), round(dy, 2), round(np.degrees(np.arctan2(dx, dy)), 2), round(c, 1)])
            files.append(f"{out}_tether_companion.csv")
        figure(m, mc, R, size, cands, track, followed, sw, clip.fps, f"{out}_tether.png")
        files.append(f"{out}_tether.png")
        print(f"wrote {', '.join(files)}")
    result = dict(finding=finding)
    return Found("tether", result, fields, files=files, no_power=npw, notes=notes, carry=followed or None)


def figure(m, mc, R, size, cands, track, followed, sw, fps, path):
    """Left: the object-centred stack with the candidates ringed (solid: moves with the object;
    dashed: as sharp on the reversed track). Middle: the reversed-track control. Right: the
    companion's angle, frame by frame, with the fitted swing when there is one."""
    from . import figures
    plt = figures.setup()
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4))
    crop = int(min(R, max(60, (max((c["r_px"] for c in cands), default=0) + 4 * size), 6 * size)))
    for ax, img, title in ((axes[0], m, "stacked on the object"), (axes[1], mc, "control: track run backwards")):
        sub = img[R - crop:R + crop + 1, R - crop:R + crop + 1]
        lo, hi = np.nanpercentile(sub, [1, 99])
        ax.imshow(sub, cmap="gray", vmin=lo, vmax=hi, extent=(-crop, crop, crop, -crop))
        ax.set_title(title)
        ax.set_xlabel("px from the object")
    for c in cands:
        axes[0].add_patch(plt.Circle((c["dx_px"], c["dy_px"]), 2.5 * SIGMA_OUT, fill=False, lw=1.2,
                                     ec="tab:red" if c["co_moving"] else "tab:orange", ls="-" if c["co_moving"] else "--"))
    ax = axes[2]
    if followed and sw and "angle_mean_deg" in sw:
        ns = sorted(n for n in followed if n in track)
        t = np.array([(n - ns[0]) / fps for n in ns])
        ang = np.degrees(np.arctan2(*np.array([(followed[n][0] - track[n][0], followed[n][1] - track[n][1]) for n in ns]).T))
        ax.plot(t, ang, ".", ms=3, color="tab:blue", label="companion")
        if sw.get("swings") and sw.get("amplitude_deg"):
            T = sw["period_used_s"]
            ax.set_title(f"swing: T = {T:.2f} s -> L = {sw['line_length_m']:.2f} m")
        else:
            ax.set_title("angle from straight down")
        ax.set_xlabel("s")
        ax.set_ylabel("deg (+ right)")
    else:
        ax.text(0.5, 0.5, "no companion followed", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
    figures.save(fig, path, tight=True)


def said(fields):
    """What `mcdonald tether` prints, from the fields."""
    L = [f"object {fields['object_size_px']:.0f} px across" + ("" if fields.get("object_size_measured") else " (assumed)")
         + f", moved {fields['moved_on_screen_px']:.0f} px on the screen over {fields['frames']} frames; "
         f"stack noise {fields['stack_noise_dn']:.1f} DN"]
    for c in fields.get("candidates", []):
        L.append(f"  {c['sign']:6s} feature {c['r_px']:6.0f} px ({c['r_over_size']:5.1f} sizes) at {c['direction_deg']:+5.0f} deg: "
                 f"z {c['z']:5.1f} on the object, {c['z_control']:5.1f} on the reversed track, on "
                 f"{100 * (c['seen_on_frames'] or 0):3.0f}% of frames, jitter "
                 + (f"{c['jitter_px']:.0f} px" if c.get("jitter_px") is not None else "n/a") + " -> "
                 + ("moves with the object" if c["co_moving"] else ("the scene's, once followed" if c.get("scene") else "not the object's")))
    sw = fields.get("swing")
    if sw and "separation_px" in sw:
        L.append(f"  companion followed on {sw['frames']} frames ({sw['span_s']:.1f} s): {sw['separation_px']:.0f} px from the object, "
                 f"moving {100 * sw['step_over_separation']:.1f}% of that a frame, "
                 f"angle {sw['angle_mean_deg']:+.1f} +- {sw['angle_sd_deg']:.1f} deg"
                 + (f"; periodogram peak {sw['period_s']:.2f} s (power {sw['power']:.2f}, {sw['cycles']:.1f} cycles)" if "period_s" in sw else ""))
    L.append(fields.get("finding", ""))
    return L


# ---- CLI ----------------------------------------------------------------------------
def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", required=True, help="CSV with frame and x/y columns: the object, as linked")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--size", type=float, help="the object's size, px (default: measured in the stack)")
    ap.add_argument("--seed", help="DX,DY: follow a companion from this offset (px) from the object on the first frame")
    ap.add_argument("--dark", action="store_true", help="the companion is darker than what is round it")
    ap.add_argument("--bright", action="store_true", help="... or brighter (default: whichever is stronger at the seed)")
    ap.add_argument("--r-min", type=float, default=R_MIN, help=f"inner ring, object sizes (default {R_MIN:g})")
    ap.add_argument("--r-max", type=float, default=R_MAX, help=f"outer ring, object sizes (default {R_MAX:g})")
    ap.add_argument("--mask-rows")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        found, clip = _main(args)
    code = vf.EXIT_NOTHING if any(t.startswith("tether: a thing") or t == "tether" for t, _ in found.no_power) else 0
    if args.json:
        emit(found.envelope("tether", inputs_of(args), clip, said=lines, exit_code=code, error=None))
    return code


def _main(args):
    video, tag, _ = vf.resolve(args.video)
    track = vf.read_track(args.track)
    n0 = args.n0 if args.n0 is not None else min(track)
    n1 = args.n1 if args.n1 is not None else max(track)
    clip = vf.Clip(video, args.workdir, n0, n1)
    out = vf.out_prefix(args.out, tag)
    print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
    seed = tuple(float(v) for v in args.seed.split(",")) if args.seed else None
    dark = True if args.dark else (False if args.bright else None)
    found = measure(clip, track, rows=vf.parse_rows(args.mask_rows), size=args.size, seed=seed, dark=dark,
                    r_min=args.r_min, r_max=args.r_max, out=out, progress=to_stderr())
    print("\n".join(said(found.fields)))
    return found, clip


if __name__ == "__main__":
    raise SystemExit(main())
