"""The angular scale k, and the one route that does not need it.

Everything in `kinematics` that converts pixels to metres needs k, and on most
released sensor video k is the binding unknown. This module is about where a
value for it can legitimately come from, in descending order of how much it
assumes:

1. **A graticule the sensor draws.** Read px per labelled degree directly.
   A measurement. Rare.
2. **A known-size object in the frame** (`measure_reference`). Not a k at all —
   it makes k unnecessary, because an image displacement divided by the
   reference's image length is a displacement in reference lengths and the
   field of view cancels. What survives is the *ratio* of ranges, which the
   clip cannot supply. This is the strongest route the PURSUE corpus offers
   and it still yields a bound, not a speed.
3. **A zoom chain** (`zoom_chain`): fit the ratio between two known fields of
   view from the imagery across a zoom transient, and propagate. Anchors a
   narrow field to a wide one, but needs one of them from elsewhere.
4. **An assumed field of view.** An assumption, and everything downstream
   inherits that. Say so in the caption.

**Never route 5: the corner brackets.** They mark the *next* narrower field of
view, not the current one and not a fixed angle. Reading a zoom ratio off them
gave x2.97 on PR144 where fitting the imagery gave x5.9 — a factor of two in
every derived speed. `forensics.zoom_ratio` fits it properly.

The reference-object route has a hidden assumption worth stating every time it
is used: the scale is read at the *reference's* field angle and the
*reference's* range, and applied to an object that is at neither. Both the
PR149 and PR148 bounds sit on it. It is why those results are ceilings.
"""
import math

import numpy as np
from scipy import ndimage

from . import forensics as vf


def measure_reference(g, seed, angles=None, half_width=7, extent=170,
                      offsets=np.arange(-6, 26, 1.0), dark=True, bad=None,
                      profile_window=None, smooth=3):
    """Projected length of an elongated reference object, along its own axis.

    A ship, a runway, a vehicle: something whose real size is known. The axis
    is fitted rather than assumed — a hull a few degrees off the assumed angle
    measures short, and the error goes straight into the speed — by scoring
    each candidate (angle, lateral offset) on the mean level along it and
    taking the darkest (or brightest) line. The length is then read from a
    half-maximum crossing of the mean profile across a narrow band.

    seed is any point on the object. Returns the endpoints, the length in
    pixels, and the levels the threshold came from, so the measurement can be
    checked rather than believed."""
    angles = np.arange(-30, 30.1, 0.5) if angles is None else np.asarray(angles, float)
    sx, sy = float(seed[0]), float(seed[1])
    s = np.arange(-extent, extent + 0.5, 0.5)
    win = (s > -extent * 0.7) & (s < extent * 0.3) if profile_window is None else \
        (s > profile_window[0]) & (s < profile_window[1])
    sign = 1.0 if dark else -1.0

    best = None
    for a in angles:
        ax = np.array([math.cos(math.radians(a)), math.sin(math.radians(a))])
        nr = np.array([-ax[1], ax[0]])
        for o in offsets:
            P = np.array([sx, sy])[:, None] + ax[:, None] * s[None, :] + nr[:, None] * o
            v = ndimage.map_coordinates(g, [P[1], P[0]], order=1)
            sc = sign * float(v[win].mean())
            if best is None or sc < best[0]:
                best = (sc, float(a), float(o))
    _, ang, off = best
    ax = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
    nr = np.array([-ax[1], ax[0]])

    band, msk = [], []
    for o in np.arange(off - half_width, off + half_width + 1, 1.0):
        P = np.array([sx, sy])[:, None] + ax[:, None] * s[None, :] + nr[:, None] * o
        band.append(ndimage.map_coordinates(g, [P[1], P[0]], order=1))
        if bad is not None:
            msk.append(ndimage.map_coordinates(bad.astype(float), [P[1], P[0]], order=0))
    band = np.array(band)
    if bad is not None:
        band = np.where(np.array(msk) > 0, np.nan, band)
    p = np.nanmean(band, 0)
    nan = np.isnan(p)
    if nan.all():
        return None
    if nan.any():                      # a whole station masked out: bridge it
        p[nan] = np.interp(s[nan], s[~nan], p[~nan])
    p = ndimage.uniform_filter1d(p, smooth)

    edge = int(len(s) * 0.15)
    background = float(np.median(np.r_[p[:edge], p[-edge:]]))
    body = float(np.percentile(p[win], 20 if dark else 80))
    thr = (background + body) / 2
    inside = np.nonzero((p < thr) if dark else (p > thr))[0]
    if len(inside) < 3:
        return None
    i, j = int(inside[0]), int(inside[-1])

    def crossing(idx, di):
        a_, b_ = p[idx], p[idx + di]
        f = (thr - a_) / (b_ - a_) if b_ != a_ else 0.0
        return s[idx] + di * 0.5 * f

    lo = crossing(i, -1) if 0 < i else s[i]
    hi = crossing(j, 1) if j < len(s) - 1 else s[j]
    o_ = np.array([sx, sy]) + nr * off
    return dict(length_px=float(hi - lo), angle_deg=ang, offset=off,
                end_a=tuple(o_ + ax * lo), end_b=tuple(o_ + ax * hi),
                background=background, body=body, threshold=float(thr))


def reference_series(clip, frames, seeds, masks=None, rows=None, **kw):
    """measure_reference over several frames. The scatter is the error bar.

    A reference measured once is a number with no uncertainty attached, which
    is how a 5 % length error becomes an unflagged 5 % speed error."""
    out = []
    for n in frames:
        seed = seeds[n] if isinstance(seeds, dict) else seeds
        bad = vf.frame_mask(clip.rgb(n), masks, rows, n) if masks else None
        m = measure_reference(clip.grey(n), seed, bad=bad, **kw)
        if m:
            out.append((n, float(clip.t(n)), m["length_px"], m["angle_deg"]))
    a = np.array(out, float).reshape(-1, 4)
    if not len(a):
        return None, None
    stats = dict(n=len(a), length_px=float(np.median(a[:, 2])),
                 sd=float(a[:, 2].std()), frac_sd=float(a[:, 2].std() / max(np.median(a[:, 2]), 1e-9)),
                 angle_deg=float(np.median(a[:, 3])))
    return a, stats


def zoom_chain(clip, transients, masks, boresight=None):
    """Zoom ratios fitted from the imagery across each contrast transient.

    Use this, never the corner brackets. Returns one entry per transient with
    the fitted scale and the ZNCC that earned it; a low ZNCC means the fit did
    not find the scale, not that the scale is 1."""
    out = []
    for (n0, n1) in transients:
        z = vf.zoom_ratio(clip, n0, n1, masks, boresight)
        if z:
            out.append(dict(frames=(n0, n1), **z))
    return out


def k_from_reference(ref_px, ref_len_m, range_m):
    """k implied by a known-size object at a known range: k = p R / S.

    Needs the reference's range, which is usually no more available than the
    object's. Included because when a mission report gives one, this is the
    cleanest k there is."""
    return float(ref_px) * float(range_m) / float(ref_len_m)


def fov_ladder(v_px, width_px, fov_candidates, ranges_m=(3000, 5000, 10000)):
    """What each candidate field of view would imply, as a table.

    The honest presentation when the FOV is unknown: show the ladder, so the
    reader sees how much rides on the one number nobody has. Rows are
    (FOV, k, omega, and the relative speed at theta = 90 deg for each range).

    Do not collapse this to a single row by picking a "likely" FOV. The spread
    across plausible fields is usually larger than any effect being argued
    about."""
    out = []
    for f in fov_candidates:
        k = (width_px / 2.0) / math.tan(math.radians(f) / 2.0)
        om = v_px / k
        out.append(dict(fov_deg=f, k=k, omega=om,
                        speeds={R: om * R for R in ranges_m}))
    return out
