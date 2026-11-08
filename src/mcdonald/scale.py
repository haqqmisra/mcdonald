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
3. **A zoom chain** (`zoom_chain`, `mcdonald zoom`): fit the ratio between two
   fields of view from the imagery across a zoom transient, and propagate.
   Anchors a narrow field to a wide one, but needs one of them from elsewhere
   (`slew` gives one, and checks its c across each step against the ratio).
4. **The camera's own slew** (`slew`, `mcdonald slew`): the scene's shift in
   pixels regressed on the north pointer's turn over a slew is k cos(depression).
   A measurement wherever a clip draws a pointer and pans; without the
   depression a lower bound on k, so W / c is a ceiling on the field of view.
   It assumes the pointer is an azimuth dial and the image level.
5. **An assumed field of view.** An assumption, and everything downstream
   inherits that. Say so in the caption.

**Never a route: the corner brackets.** They mark the *next* narrower field of
view, not the current one and not a fixed angle. Reading a zoom ratio off them
gave x2.97 on PR144 where fitting the imagery gave x5.9 — a factor of two in
every derived speed. `forensics.zoom_fit` fits it properly.

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
    """Zoom ratios fitted from the imagery across each contrast transient: `forensics.zoom_fit` from two frames
    before it to six after (the whole picture searched, the overlay zeroed). `boresight` is not used: the fit
    searches the whole earlier picture (AARO's Puerto Rico clip moved 300-400 px during its blanks).

    Use this, never the corner brackets. Returns one entry per transient with the fitted scale, the ZNCC that earned
    it and the verdict -- "step", "no step" or "unknown"; an unknown means the fit did not find the scale, not that
    the scale is 1. `mcdonald zoom` does this better: it finds the settled frames either side, merges bursts close
    together and takes each side's fixed pattern out."""
    out = []
    for (n0, n1) in transients:
        if n0 - 2 >= clip.n0 and n1 + 6 <= clip.n1:
            z = vf.zoom_fit(clip, n0 - 2, n1 + 6, masks)
            z.pop("scores", None)
            out.append(dict(transient=(n0, n1), **z))
    return out


def k_from_reference(ref_px, ref_len_m, range_m):
    """k implied by a known-size object at a known range: k = p R / S.

    Needs the reference's range, which is usually no more available than the
    object's. Included because when a mission report gives one, this is the
    cleanest k there is."""
    return float(ref_px) * float(range_m) / float(ref_len_m)


# deg: the fields of view a scale is shown for when none is known. A targeting pod's narrow field is far under the rest
# (the Navy's ATFLIR in NAR, 0.70 deg, and 0.35 at its x2: FLIR1, 2026-10-20), and a gimballed turret's wide one
# near the top.
FOV_LADDER = (0.7, 3, 10, 30, 54)


def fov_ladder(v_px, width_px, fov_candidates=FOV_LADDER, ranges_m=(3000, 5000, 10000)):
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


# ---- one k from the routes that agree (E17; the economics survey's §3.4, 2026-11-07) -----------------------------
# Bates & Granger (1969) combined forecasts with weights inverse to their error variances; the forecast combination puzzle
# (Smith & Wallis 2009) is that weights estimated from the data often do worse than equal ones, because they carry error
# too. Here the weights are each route's own stated error, not fitted, and nothing is combined before a test that the
# routes agree: combining two routes that disagree hides a mistake in one of them.
AGREE_ALPHA = 0.05     # the agreement test's level: the chance that routes measuring one k, each within its stated error,
                       # are called in disagreement. It is the chi-square's own rate where each route's error is what it says
                       # (Gaussian in log k); method 49 measures it on drawn slews, whose bootstrap errors are the ones the stage
                       # states, and the words give the measured rate where the two differ
KINDS = ("measurement", "floor", "prior")


def route(name, k_px_per_deg, err_px_per_deg=None, kind="measurement", shares=(), detail=""):
    """One route to k, in px per degree (square pixels, up the picture where they are not square): a `measurement` (a
    graticule, a slew with its depression, a reference of known size at a range given, a data bar's field of view) with
    its 1-sigma error where the route states one; a `floor` (a slew's c = k cos(depression) with the depression unknown,
    or a floor where the pointer did not register the turn: k is at least it); or a `prior` (an assumed field of view:
    compared with what is measured, never combined). `shares`: the inputs it rests on that another route may rest on too
    (a zoom ratio, a depression): routes that share one are not independent, and only the more precise enters the test."""
    if kind not in KINDS:
        raise ValueError(f"a route is one of {KINDS}, not {kind}")
    return dict(name=name, k_px_per_deg=float(k_px_per_deg), err_px_per_deg=None if err_px_per_deg is None else float(err_px_per_deg),
                kind=kind, shares=tuple(shares), detail=detail)


def _sig(r):
    """A route's error in log k."""
    return r["err_px_per_deg"] / r["k_px_per_deg"] if r.get("err_px_per_deg") else None


def combine(routes, alpha=AGREE_ALPHA):
    """The routes a case has to k, tested for agreement and combined where they agree (method 49).

    In log k, where a route's error is a share of it: the measurements with a stated error, one of each group that shares
    an input (the most precise), are set against their weighted mean, chi^2 = sum((ln k_i - mean) / sigma_i)^2 on n - 1
    degrees of freedom; they agree where its chance is alpha or more, and the combined k is the mean with error
    1 / sqrt(sum(1 / sigma_i^2)). Where they do not agree, nothing is combined, and every pair further apart than the
    two-sided alpha allows is named. A floor is cleared where k is not below it by more than the one-sided alpha allows
    (each measurement where they disagree, the combined k where they agree); a floor not cleared is a disagreement too. A
    prior is set against the result and said; it never enters it. A measurement with no stated error cannot be tested:
    it stands alone where it is the only one, and is left out of a test with others, which says so.

    Returns dict(verdict -- "none", "one route", "agree" or "disagree" --, k_px_per_deg and err_px_per_deg (None where
    they disagree or nothing is measured), used, chi2, dof, p, pairs [dict(a, b, z)], disagree [names], floors
    [dict(name, k, z, clears)], priors [dict(name, k, z)], left_out [(name, why)])."""
    from scipy.stats import chi2 as chi2_dist, norm
    meas = [r for r in routes if r["kind"] == "measurement"]
    out = dict(verdict="none", k_px_per_deg=None, err_px_per_deg=None, used=[], chi2=None, dof=0, p=None, pairs=[],
               disagree=[], floors=[], priors=[], left_out=[], alpha=alpha)
    with_err = [r for r in meas if _sig(r)]
    for r in meas:
        if not _sig(r) and len(meas) > 1:
            out["left_out"].append((r["name"], "its error is not stated: tested against the others with none (the strictest the test "
                                               "can be), not weighed into the combination"))
    with_err.sort(key=_sig)
    used, taken = [], set()
    for r in with_err:                                   # the most precise of each group that shares an input
        if taken & set(r["shares"]):
            out["left_out"].append((r["name"], "it shares an input (" + ", ".join(sorted(taken & set(r["shares"])))
                                    + ") with a more precise route, so the two are not independent: checked against it, not added"))
            continue
        taken |= set(r["shares"])
        used.append(r)
    zc2, zc1 = float(norm.ppf(1 - alpha / 2)), float(norm.ppf(1 - alpha))
    for i, a in enumerate(with_err):                     # every pair, shared or not, for the words
        for b in with_err[i + 1:]:
            z = abs(math.log(a["k_px_per_deg"] / b["k_px_per_deg"])) / math.hypot(_sig(a), _sig(b))
            out["pairs"].append(dict(a=a["name"], b=b["name"], z=float(z), apart=bool(z > zc2)))
    bare = [r for r in meas if not _sig(r)]
    for a in bare:                                       # an error not stated: taken as none against each that states one
        for b in with_err:
            z = abs(math.log(a["k_px_per_deg"] / b["k_px_per_deg"])) / _sig(b)
            out["pairs"].append(dict(a=a["name"], b=b["name"], z=float(z), apart=bool(z > zc2)))
    if len(used) >= 2:
        x = np.log([r["k_px_per_deg"] for r in used])
        w = 1.0 / np.array([_sig(r) for r in used]) ** 2
        mean = float((w * x).sum() / w.sum())
        chi2 = float((w * (x - mean) ** 2).sum())
        p = float(chi2_dist.sf(chi2, len(used) - 1))
        out.update(used=[r["name"] for r in used], chi2=chi2, dof=len(used) - 1, p=p)
        if p >= alpha:
            k = math.exp(mean)
            out.update(verdict="agree", k_px_per_deg=k, err_px_per_deg=k / math.sqrt(w.sum()))
        else:
            out["verdict"] = "disagree"
            out["disagree"] = sorted({n for q in out["pairs"] if q["apart"] for n in (q["a"], q["b"])}) or [r["name"] for r in used]
    elif used or meas:
        one = used[0] if used else meas[0]
        out.update(verdict="one route", used=[one["name"]], k_px_per_deg=one["k_px_per_deg"], err_px_per_deg=one["err_px_per_deg"])
    if bare and with_err and out["verdict"] != "disagree":   # the routes with no stated error must agree with the rest too
        apart = [q for q in out["pairs"] if q["apart"] and (q["a"] in {r["name"] for r in bare})]
        if apart:
            out.update(verdict="disagree", k_px_per_deg=None, err_px_per_deg=None,
                       disagree=sorted({n for q in apart for n in (q["a"], q["b"])}))
        elif out["verdict"] == "one route":
            out.update(verdict="agree", used=out["used"])
    if out["verdict"] == "agree":
        against = [dict(name="the combined k", k_px_per_deg=out["k_px_per_deg"], err_px_per_deg=out["err_px_per_deg"])]
    elif out["verdict"] == "one route":
        against = [r for r in meas if r["name"] == out["used"][0]]
    else:
        against = [r for r in with_err if r["name"] in out["disagree"]]
    for f in (r for r in routes if r["kind"] == "floor"):
        worst = None
        for m in against:
            s = math.hypot(_sig(m) or 0.0, _sig(f) or 0.0)
            gap = math.log(f["k_px_per_deg"] / m["k_px_per_deg"])
            z = gap / s if s > 0 else (math.inf if gap > 0 else -math.inf)
            if worst is None or z > worst[0]:
                worst = (z, m["name"])
        clears = worst is None or worst[0] <= zc1
        out["floors"].append(dict(name=f["name"], k_px_per_deg=f["k_px_per_deg"], z=None if worst is None else float(worst[0]),
                                  against=None if worst is None else worst[1], clears=bool(clears)))
        if not clears:
            out["disagree"] = sorted((set(out["disagree"]) | {f["name"], worst[1]} | (set(out["used"]) if worst[1] == "the combined k"
                                                                                       else set())) - {"the combined k"})
            out.update(verdict="disagree", k_px_per_deg=None, err_px_per_deg=None)
    for pr in (r for r in routes if r["kind"] == "prior"):
        z = None
        if out["k_px_per_deg"] and _sig(dict(out, kind="measurement")) is not None:
            z = math.log(pr["k_px_per_deg"] / out["k_px_per_deg"]) / _sig(dict(out))
        under = [f["name"] for f in (r for r in routes if r["kind"] == "floor")      # an assumption below a floor is contradicted
                 if math.log(f["k_px_per_deg"] / pr["k_px_per_deg"]) / (_sig(f) or 1e-12) > zc1]
        out["priors"].append(dict(name=pr["name"], k_px_per_deg=pr["k_px_per_deg"], z=None if z is None else float(z),
                                  under_floor=under))
    return out


def norm_z(alpha):
    """The two-sided normal deviate at alpha."""
    from scipy.stats import norm
    return float(norm.ppf(1 - alpha / 2))


def combined_said(c):
    """The combination in one or two sentences, for the report and the stage's lines."""
    fmt = lambda v: f"{v:.0f}" if v >= 100 else f"{v:.3g}"
    if c["verdict"] == "none":
        s = "no route measures k"
        for pr in c["priors"]:
            if pr.get("under_floor"):
                s += f"; {pr['name']} gives {fmt(pr['k_px_per_deg'])} px/deg, below {' and '.join(pr['under_floor'])}: the assumption is contradicted"
        for f in c["floors"]:
            s += f"; {f['name']}: at least {fmt(f['k_px_per_deg'])} px/deg"
        return s
    if c["verdict"] == "one route":
        s = f"one route measures k: {c['used'][0]}, {fmt(c['k_px_per_deg'])} px/deg" + (
            f" +/- {fmt(c['err_px_per_deg'])}" if c["err_px_per_deg"] else "")
    elif c["verdict"] == "agree" and c["chi2"] is None:
        near = "; ".join(f"{q['a']} and {q['b']} are {q['z']:.1f} of the error apart" for q in c["pairs"])
        s = (f"the routes agree ({near}; {norm_z(c['alpha']):.2f} allowed): k = {fmt(c['k_px_per_deg'])} +/- "
             f"{fmt(c['err_px_per_deg'])} px/deg from {c['used'][0]}")
    elif c["verdict"] == "agree":
        s = (f"{len(c['used'])} routes agree ({', '.join(c['used'])}; chi^2 {c['chi2']:.2f} on {c['dof']}, chance "
             f"{c['p']:.2f}, {c['alpha']:g} needed): k = {fmt(c['k_px_per_deg'])} +/- {fmt(c['err_px_per_deg'])} px/deg combined")
    else:
        apart = [q for q in c["pairs"] if q["apart"]]
        s = ("the routes DISAGREE, so they are not combined: " + "; ".join(f"{q['a']} and {q['b']} are {q['z']:.1f} of their "
                                                                           "combined errors apart" for q in apart)
             if apart else f"the routes DISAGREE (chi^2 {c['chi2']:.2f} on {c['dof']}, chance {c['p']:.3f}), so they are not combined"
             if c["chi2"] is not None else "the routes DISAGREE, so they are not combined")
    for f in c["floors"]:
        if not f["clears"]:
            s += f"; {f['name']} ({fmt(f['k_px_per_deg'])} px/deg at least) is above {f['against']} by {f['z']:.1f} of their errors"
    for pr in c["priors"]:
        if pr["z"] is not None:
            s += f"; {pr['name']} gives {fmt(pr['k_px_per_deg'])} px/deg, {pr['z']:+.1f} of the measured k's error from it (a prior, not combined)"
        if pr.get("under_floor"):
            s += f"; {pr['name']} gives {fmt(pr['k_px_per_deg'])} px/deg, below {' and '.join(pr['under_floor'])}: the assumption is contradicted"
    for name, why in c["left_out"]:
        s += f"; {name}: {why}" if why.startswith("its error") else f"; {name} left out: {why}"
    return s


# ---- the zoom ladder pooled across a sensor's clips (E16; the economics survey's §3.3, 2026-11-07) ----------------------
# International price comparison fits log price = country effect + product effect across rarely observed pairs (Summers'
# country-product-dummy regression), and finance shrinks each stock's noisy beta towards the cross-section (Vasicek 1973;
# Blume 1975), as insurers do with credibility (Buhlmann 1967). A sensor's zoom changes its field by a few fixed ratios (the
# MQ-9 MTS-B's x2.00 and x5.9, the pointer sweep of 2026-10-20): each step measured in any clip is a reading of its rung, so
# the rung's ratio is known far better than any one step, and a k carried through it gains the rung's error, not a single
# step's -- a chain whose error does not grow with each link. What it does not give is a k on a clip that measured none: only
# a prior, from the sensor's other clips, and said as one.
RUNG_GAP = 0.03        # |ln s| apart by more than this starts a new rung: the sweep's 95 steps fall in rungs 0.5-2 % wide (in ln)
                       # with gaps of 5 % and more between them (x2.000 and x2.303; x5.916 and x7.509)


def ladder(steps, gap=RUNG_GAP):
    """A sensor's zoom ladder from its measured steps, pooled: `steps` [(clip, s)] or [(clip, s, err_log)] (a step in or out,
    s or 1/s alike; err_log a step's own error in ln s where its fit states one, `zoom --rd`'s). The steps fall into rungs by
    |ln s| (a new rung where two sorted neighbours are more than `gap` apart); each rung's ratio is the mean of its |ln s|
    (inverse-variance where every step states an error), its error the standard error, its spread the steps' standard
    deviation, and tau^2 -- the spread beyond the steps' own errors, the between-clip variance credibility needs -- where they
    state them. Returns [dict(ratio, ln_ratio, ln_err, ln_sd, tau, n, clips, members)] from the smallest rung up."""
    rows = sorted((abs(math.log(st[1])), st[0], (st[2] if len(st) > 2 else None)) for st in steps if st[1] and st[1] > 0)
    rungs, cur = [], []
    for r in rows:
        if cur and r[0] - cur[-1][0] > gap:
            rungs.append(cur)
            cur = []
        cur.append(r)
    if cur:
        rungs.append(cur)
    out = []
    for g in rungs:
        v = np.array([x[0] for x in g])
        e = [x[2] for x in g]
        n = len(v)
        sd = float(v.std(ddof=1)) if n > 1 else None
        if all(x for x in e):
            w = 1 / np.array(e) ** 2
            m, se = float((w * v).sum() / w.sum()), float(1 / math.sqrt(w.sum()))
            tau2 = max(sd ** 2 - float(np.mean(np.array(e) ** 2)), 0.0) if sd is not None else None
        else:
            m, se, tau2 = float(v.mean()), (sd / math.sqrt(n) if sd is not None else None), None
        out.append(dict(ratio=math.exp(m), ln_ratio=m, ln_err=se, ln_sd=sd, tau=None if tau2 is None else math.sqrt(tau2), n=n,
                        clips=len({x[1] for x in g}), members=[(x[1], math.exp(x[0])) for x in g]))
    return out


def credible(s, err_log, rung):
    """A clip's own measured step shrunk towards its rung by credibility: Z = tau^2 / (tau^2 + err^2), the step's weight, and
    the rest the rung's (Buhlmann 1967). With no tau (the steps state no errors, or the rung's spread is all their error) the
    rung's ratio stands. Returns dict(ratio, ln_err, Z)."""
    x = math.log(s) if s >= 1 else -math.log(s)
    tau = rung.get("tau")
    if not tau or not err_log:
        z = 0.0
    else:
        z = tau ** 2 / (tau ** 2 + err_log ** 2)
    m = z * x + (1 - z) * rung["ln_ratio"]
    err = math.sqrt((z * err_log) ** 2 + ((1 - z) * (rung["ln_err"] or 0.0)) ** 2) if err_log else rung["ln_err"]
    return dict(ratio=math.exp(m) if s >= 1 else math.exp(-m), ln_err=err, Z=z)


def carry(k_px_per_deg, k_err, rungs_up, rungs_down=()):
    """k measured in one state carried to another through the sensor's pooled rungs (`ladder`'s rows): times each rung zoomed
    in, over each zoomed out. Its error in ln k adds each rung's pooled error, not a single step's. Returns (k, err) -- a
    PRIOR on the other state where it is used on a clip that measured nothing itself, and to be said as one."""
    ln = math.log(k_px_per_deg) + sum(r["ln_ratio"] for r in rungs_up) - sum(r["ln_ratio"] for r in rungs_down)
    var = (k_err / k_px_per_deg) ** 2 + sum((r["ln_err"] or 0.0) ** 2 for r in list(rungs_up) + list(rungs_down))
    k = math.exp(ln)
    return k, k * math.sqrt(var)
