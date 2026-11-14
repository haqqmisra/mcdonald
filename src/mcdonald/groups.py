"""Is the object one thing, or several moving together -- and do they keep their places?

A linked track follows one position a frame. When what was marked is a group -- PR135's
"6X SMALL SPHERICAL OBJECTS GROUPED TOGETHER", the "fleet" clips -- that position is the
brightest member or a blend of several, `propose` lists the group as one thing, and
nothing says there is more than one. The PR135 agent (2026-09-22, its items 3, 8 and 22)
had to write its own member tracker to ask the question that tells a flock from a
formation: **do the members keep their relative positions?** A rigid formation holds
every separation, give or take how well a position is measured; birds do not, and
PR135's six "keep reshuffling".

Method (`members`, then `rigidity`):

1. **Spots near the track.** On every frame of the track, the detector at a small scale
   (a member of a group is a point, and the object's own size is the group's) in a
   window about the track's position, `radius` px. Only spots answering at least
   `LIKE` of the strongest in that window count: a member of a group is like the
   others; and only those with background all round them (`propose.all_round`, as
   Find asks it): the small detector fires on the rim of a disc too, all the way round,
   and six such spots would be read as a rigid group of six. The detector is the
   package's one (`forensics.source_candidates`, every spot).
2. **Not on the sensor.** A spot at the same place on the screen on half the frames,
   while the group moves, is a defect of the sensor (PR135 has eleven, among its 18
   longest tracks), and is left out -- `forensics.on_the_sensor`.
3. **Members, frame to frame.** The group's own shift between two frames is the offset
   that brings the most spots onto spots (a vote, as the agent's `group_shift`); each
   member is predicted by that shift and half its own last motion within the group, and
   spots are assigned to members by least total distance (Hungarian), within a gate of
   `GATE` px and `GATE_GROW` more a frame the member was not seen. A spot left over is a
   new member; a member not seen for `MAX_MISS` frames has ended. Identities can be
   lost where two members merge into one spot: a member that ends and one that starts
   are not joined up.
4. **Rigid, or not.** For every two members seen together on `MIN_SHARED` frames or
   more, the separation, frame by frame, and how much it wanders about a straight line
   in time (which a slow zoom or a change of aspect gives a rigid group). That is held
   against what the members' own position noise alone would give (each member's jitter
   from its second differences, `_noise`): a rigid group's pairs wander by about that; a group
   whose members change places, by many times it. `rigid` is true when every such pair
   wanders by at most RIGID times the noise, false when the median pair wanders by more
   than SHUFFLE times it and by more than a pixel, and None between, or with fewer than
   two members long enough to ask.

5. **Two calibrated readings beside it** (2026-11-13, `one_body` and `places`; docs/method.md section 60). One
   rigid body or several: what is left off the best rank-3 fit of the group's centred positions (Tomasi & Kanade's
   rank theorem; rank 2 with four members). Do the members keep their places: every separation over the group's
   size, about a straight line in time. Each says the group moved only where the wander keeps going (a KPSS
   statistic against the series' own blocks drawn again), stands over a line set on drawn rigid groups that carry
   the detector's real errors, and is over a pixel; a separation that returns to its line (ADF) is not said to
   wander. Each can answer "cannot say". `rigid` stands as it was.

What it cannot do: say what the members are. Rigid or shuffling is a property of the
formation in the image; birds, a formation of aircraft or drifting debris each still
need the rest of the case. And the separations are in pixels, not metres, for the
reasons they always are.
"""
import csv

import numpy as np
from scipy.optimize import linear_sum_assignment

from . import forensics as vf
from .progress import PROCS_HELP, pooled, to_stderr
from .report import Found, emit, inputs_of, said_to_stderr

RADIUS = 120.0       # px about the track's position that members are looked for in: PR135's six span 155 px,
                     # and at 60 the outer ones are lost
SIZE = 5.0           # the detector's scale for a member: a point
LIKE = 0.3           # a member answers at least this share of the strongest spot in the window
MIN_RESP = 10.0      # and at least this, whatever the strongest
GATE, GATE_GROW = 4.0, 1.5
MAX_MISS = 5
MIN_FRAMES = 30      # a member followed this long counts
MIN_SHARED = 30      # two members seen together this long are compared
RIGID, SHUFFLE = 2.0, 3.0
ALL_ROUND = 0.1      # a member has some background all round it (propose.all_round): the rim of a disc has none
                     # (0.0), and PR135's members, close together, go down to 0.23
STILL = 20.0         # px: a track that moves less against the background cannot tell the scene near it from members
POINT_SIZE = 9.0     # `run` asks this of an object linked as a spot no wider: a larger one has a rim of its own


def spots_near(clip, n, xy, masks, rows=None, radius=RADIUS, size=SIZE, dark=False, rgb=None, bad=None):
    """[(x, y, response)] of the spots within `radius` of xy on frame n, strongest first,
    those answering at least LIKE of the strongest (and MIN_RESP)."""
    rgb = clip.rgb(n) if rgb is None else rgb
    bad = vf.frame_mask(rgb, masks, rows, n, grow=6) if bad is None else bad
    pad = int(radius + 4 * size)
    x0, y0 = max(int(xy[0]) - pad, 0), max(int(xy[1]) - pad, 0)
    x1, y1 = min(int(xy[0]) + pad + 1, clip.W), min(int(xy[1]) + pad + 1, clip.H)
    g = vf.grey_of(rgb[y0:y1, x0:x1])
    got = vf.source_candidates(g, bad[y0:y1, x0:x1], size, dark, n_max=None, min_resp=MIN_RESP)
    got = [(x + x0, y + y0, v) for x, y, v in got if np.hypot(x + x0 - xy[0], y + y0 - xy[1]) <= radius]
    if not got:
        return []
    top = max(v for _, _, v in got)
    from .propose import all_round
    return [(x, y, v) for x, y, v in got if v >= LIKE * top and all_round(g, x - x0, y - y0, -1 if dark else 1, size) >= ALL_ROUND]


def group_shift(prev, cur, guess, reach=15.0, tol=2.0):
    """The group's shift from `prev` to `cur` (arrays of x, y): of every spot-to-spot offset
    within `reach` of `guess` (the track's own step), the one that brings the most spots of
    prev within `tol` of one of cur -- refined as the mean of those matches."""
    if not len(prev) or not len(cur):
        return np.asarray(guess, float)
    offs = (cur[None, :, :] - prev[:, None, :]).reshape(-1, 2)
    offs = offs[np.hypot(*(offs - guess).T) <= reach]
    if not len(offs):
        return np.asarray(guess, float)
    best, score = np.asarray(guess, float), -1.0
    for o in offs:
        d = np.hypot(*(prev[:, None, :] + o - cur[None, :, :]).transpose(2, 0, 1)).min(1)
        sc = (d <= tol).sum() - 1e-3 * np.hypot(*(o - guess))
        if sc > score:
            best, score = o, sc
    d = np.hypot(*(prev[:, None, :] + best - cur[None, :, :]).transpose(2, 0, 1))
    i, j = np.nonzero(d <= tol)
    return (cur[j] - prev[i]).mean(0) if len(i) else best


_G = {}


def _init(clip, ns, track, masks, rows, radius, size, dark):
    _G.update(clip=clip, ns=ns, track=track, masks=masks, rows=rows, radius=radius, size=size, dark=dark, last=None)


def _read(n):
    """Frame n as `members` reads it: (rgb, what of it is not scene, grey)."""
    rgb = _G["clip"].rgb(n)
    return rgb, vf.frame_mask(rgb, _G["masks"], _G["rows"], n, grow=6), vf.grey_of(rgb).astype(np.float32)


def _frame(i):
    """The track's i-th frame: (frame, the background's shift onto it from the track's frame before -- None
    on the first -- and its spots near the track). A worker is given the frames in runs, and keeps the one
    before for the next."""
    from .propose import background_shift
    ns, n = _G["ns"], _G["ns"][i]
    rgb, bad, g = _read(n)
    d = None
    if i:
        last = _G["last"]
        if last is None or last[0] != ns[i - 1]:
            _, b0, g0 = _read(ns[i - 1])
            last = (ns[i - 1], g0, b0)
        d = background_shift(last[1], g, ~(bad | last[2]))
    _G["last"] = (n, g, bad)
    return n, d, spots_near(_G["clip"], n, _G["track"][n], _G["masks"], _G["rows"], _G["radius"], _G["size"], _G["dark"],
                            rgb, bad)


def members(clip, track, masks, rows=None, radius=RADIUS, size=SIZE, dark=False, progress=None, stop=None, procs=None):
    """(followed points {id: {frame: (x, y, response)}}, spots {frame: [...]}, on the sensor count,
    the background's own displacement since the first frame {frame: (dx, dy)}). The frames are
    read on `procs` processes (`progress.pooled`; 0: in this one), and followed here, in order."""
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    keep = {k: masks[k] for k in ("blocks", "graphics", "colour", "tinted") if k in masks}
    spots, bg, last = {}, {}, None
    for n, d, got in pooled(procs, _frame, range(len(ns)), _init, (clip, ns, {n: track[n] for n in ns}, keep, rows, radius,
                                                                   size, dark), 8, progress, stop, "Groups",
                            pixels=clip.W * clip.H):
        bg[n] = (0.0, 0.0) if d is None else (bg[last][0] + d[0], bg[last][1] + d[1])
        spots[n], last = got, n
    fixed = vf.on_the_sensor({n: [(x, y) for x, y, _ in s] for n, s in spots.items()},
                             windows={n: (track[n][0], track[n][1], radius) for n in spots})
    spots = {n: [q for i, q in enumerate(s) if (n, i) not in fixed] for n, s in spots.items()}

    tracks, live, nid = {}, {}, 0                   # live: id -> [pos, rel_vel, misses]
    prev_n = None
    for n in ns:
        cur = np.array([(x, y) for x, y, _ in spots[n]]).reshape(-1, 2)
        if prev_n is None or not live:
            for k, (x, y, v) in enumerate(spots[n]):
                tracks[nid] = {n: (x, y, v)}
                live[nid] = [np.array([x, y]), np.zeros(2), 0]
                nid += 1
            prev_n = n
            continue
        ids = list(live)
        pos = np.array([live[i][0] for i in ids])
        guess = np.subtract(track[n], track[prev_n])
        seen = np.array([tracks[i][prev_n][:2] for i in ids if prev_n in tracks[i]]).reshape(-1, 2)
        shift = group_shift(seen, cur, guess)
        pred = pos + shift * (n - prev_n) / max(n - prev_n, 1) + 0.5 * np.array([live[i][1] for i in ids])
        taken = set()
        if len(cur):
            D = np.hypot(*(pred[:, None, :] - cur[None, :, :]).transpose(2, 0, 1))
            for a, b in zip(*linear_sum_assignment(D)):
                i = ids[a]
                if D[a, b] <= GATE + GATE_GROW * live[i][2]:
                    x, y, v = spots[n][b]
                    new = np.array([x, y])
                    live[i][1] = (new - live[i][0] - shift) / (1 + live[i][2])
                    live[i][0], live[i][2] = new, 0
                    tracks[i][n] = (x, y, v)
                    taken.add(b)
        for a, i in enumerate(ids):
            if n not in tracks[i]:
                live[i][0] = pred[a]
                live[i][2] += 1
                if live[i][2] > MAX_MISS:
                    del live[i]
        for b, (x, y, v) in enumerate(spots[n]):
            if b not in taken:
                tracks[nid] = {n: (x, y, v)}
                live[nid] = [np.array([x, y]), np.zeros(2), 0]
                nid += 1
        prev_n = n
    return tracks, spots, len(fixed), bg


NOISE_PAIRS = 10     # pairs of side-by-side second differences on consecutive frames a member's noise needs


def _noise_median(t):
    """The rms, per axis, of a member's jitter about a 7-frame running median: low on a moving member (see `_noise`)."""
    ns = sorted(t)
    xy = np.array([t[n][:2] for n in ns])
    if len(xy) < 7:
        return None
    med = np.array([np.median(xy[max(0, k - 3):k + 4], axis=0) for k in range(len(xy))])
    return float(np.sqrt(((xy - med) ** 2).mean()))


def _noise(t):
    """A member's position noise, per axis (the two pooled), read from its second differences on consecutive frames
    (E6's reading, `kinematics.second_differences`, here as sqrt((gamma_0 - gamma_1) / 10)): white jitter of variance s^2
    gives the second differences gamma_0 = 6 s^2 and gamma_1 = -4 s^2, so (gamma_0 - gamma_1) / 10 is s^2 whatever the
    member's speed, and a slow part of them -- a group turning on screen -- adds alike to both and cancels. It replaced
    (2026-11-07) the rms about a 7-frame running median, which read a member's jitter by the group's speed and the track's
    length: 0.5 px read 0.48 at rest and 0.17-0.28 at 1.2-2.4 px a frame (the median of a ramp is its middle sample, and the
    windows cut short at the ends leave sqrt(7 v^2 / 2 N)), so a rigid formation drifting across the picture read "neither"
    and, at 0.75-1 px of jitter, "shuffling" (the air-and-sea survey's W-TU11). Under NOISE_PAIRS pairs (a member seen on
    frames too far apart) the running median's reading stands in (`_noise_median`), as it did before."""
    ns = sorted(t)
    f = np.array(ns, float)
    xy = np.array([t[n][:2] for n in ns], float)
    if len(f) < 4:
        return None
    g = np.diff(f)
    d1 = np.diff(xy, axis=0)
    d2 = d1[1:] - d1[:-1]
    ok1 = (g[:-1] == 1) & (g[1:] == 1)                  # a second difference over three consecutive frames
    ok2 = ok1[:-1] & ok1[1:]                            # and the one after it too
    if int(ok2.sum()) < NOISE_PAIRS:
        return _noise_median(t)
    p, q = d2[:-1][ok2], d2[1:][ok2]
    mu = (p.sum(axis=0) + q.sum(axis=0)) / (2.0 * len(p))
    g1 = float(((p - mu) * (q - mu)).mean())            # the two axes pooled
    g0 = float(d2[ok1].var(axis=0).mean())
    return float(np.sqrt(max((g0 - g1) / 10.0, 0.0)))


def rigidity(tracks):
    """Fields: the members followed long enough, their position noise, and every pair seen
    together long enough -- separation, how much it wanders about a line in time, and that
    against the noise -- and `rigid`, as the module says."""
    long = {i: t for i, t in tracks.items() if len(t) >= MIN_FRAMES}
    noise = {i: _noise(t) for i, t in long.items()}
    pairs = []
    ids = sorted(long)
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            A, B = long[ids[a]], long[ids[b]]
            both = sorted(set(A) & set(B))
            if len(both) < MIN_SHARED:
                continue
            s = np.array([np.hypot(A[n][0] - B[n][0], A[n][1] - B[n][1]) for n in both])
            t = np.array(both, float)
            fit = np.polyval(np.polyfit(t, s, 1), t)
            wander = float(np.sqrt(((s - fit) ** 2).mean()))
            expect = float(np.hypot(noise[ids[a]] or 0, noise[ids[b]] or 0)) or 1e-9     # a separation's own noise
            pairs.append(dict(members=[ids[a], ids[b]], frames=len(both), first=both[0], last=both[-1],
                              separation_px=float(s.mean()), separation_range_px=float(s.max() - s.min()),
                              wander_px=wander, noise_px=expect, wander_over_noise=wander / expect))
    if not pairs:
        rigid, why = None, (f"fewer than two members were followed together for {MIN_SHARED} frames, so whether they "
                            "keep their places cannot be asked")
    else:
        r = np.array([p["wander_over_noise"] for p in pairs])
        w = np.array([p["wander_px"] for p in pairs])
        if r.max() <= RIGID:
            rigid, why = True, (f"every pair of members keeps its separation to within {RIGID:g} times what the "
                                f"members' own position noise gives (at most {r.max():.1f} times): a rigid group")
        elif np.median(r) > SHUFFLE and np.median(w) > 1.0:
            rigid, why = False, (f"the separations wander by {np.median(w):.1f} px about a steady change, "
                                 f"{np.median(r):.1f} times what position noise gives (the median pair): the members "
                                 "change places, as a flock does and a formation does not")
        else:
            rigid, why = None, (f"the pairs wander by {np.median(r):.1f} times the position noise (the median pair, "
                                f"{r.min():.1f} to {r.max():.1f}): neither clearly held nor clearly shuffling")
    return dict(members_followed=len(long), noise_px={str(i): v for i, v in noise.items()}, pairs=pairs,
                rigid=rigid, finding=why)


# ---- two calibrated readings beside `rigid` (2026-11-13; docs/method.md section 60) ------------------------------------
# One rigid body or several (the rank of the group's centred positions: IDEAS M7, with B23's warning about coloured
# jitter), and whether the members keep their places (unit-root and stationarity tests on the separations, E21, each
# separation a double difference, S14). Each reading says the group "moved" only where three things hold together, and
# each of the three is set by a null of its own:
#
#   it keeps going -- a KPSS statistic (do the partial sums of what is left run away, against its own long-run variance)
#     beyond ALPHA of the same statistic on the series' own blocks drawn again in a shuffled order (a moving-block
#     bootstrap: the draws keep the jitter's own size and its own colour up to a block's length, whatever they are, and
#     lose only what lasts longer than a block);
#   it is large against the jitter -- what is left stands more than PAIR_LINE (a separation) or RANK_LINE (off the
#     rank) times over the jitter read at the frame scale: the levels that drawn rigid groups carrying the detector's
#     real errors (the biology survey's dots planted in real frames of 12 clips and found again) pass ALPHA of the time;
#   it is large in pixels -- more than PX_FLOOR, the error the detector makes on 99 of 100 of those planted dots: a
#     member that crosses the pixel grid slowly can turn all of its error into a slow wander, which no reading at the
#     frame scale sees.
#
# None is enough alone. The first, alone, calls a drone show that holds its figure to under half a pixel "several"
# (the figure does change, by 0.1 to 0.4 px over 600 frames, and members that jitter by 0.01-0.03 px against one
# another let a test see that). The second rests on a frame-scale reading of the jitter, which a jitter with a long
# memory fools (B23). The third knows nothing of a faint member's larger jitter. Why the form first proposed (M7,
# B23) was not built -- the residual in pixels against rigid bodies drawn with an AR(1) jitter of the measured colour:
# that colour cannot be measured on the groups that matter (PR135's birds move with their wings every four frames,
# the drone show's camera holds its pictures): section 60.
ALPHA = 0.01             # each part of "moved" is held to this rate on its own null
ADF_ALPHA = 0.05         # a separation that wanders as a random walk "returns to its line" this often (MacKinnon 2010)
DRAWS = 999              # block-bootstrap draws: the least p is 0.001
TEST_SEED = 23           # the draws' seed: the same group reads the same every time
TEST_MIN_FRAMES = 60     # frames the members share under which neither reading is made (section 60's power table)
MOST_MEMBERS = 8         # the longest-followed members read: 28 pairs (the lines below were drawn for 2 to 8)
# The three lines below are from drawn groups that keep their places, or are one rigid body, each member carrying the
# error series of one of the biology survey's planted dots (277 dots found again on 60 frames or more, in real frames
# of 12 clips): 8,000 groups for each of 2, 3, 4, 5, 6 and 8 members and 60, 100, 150 and 180 frames (session 23's job
# 1220). With white jitter the same ratios stay under 1.25, with an AR(1) jitter of lag-1 correlation 0.6 under 2.3.
PAIR_LINE = 3.3          # a separation's wander over its jitter: the largest pair's 99th percentile on such groups is 3.27 at most
RANK_LINE = {3: 2.5, 2: 3.0}   # what is left off rank 3 (rank 2, four members) over its jitter: 99th percentile 2.40 (2.97) at most
PX_FLOOR = 1.0           # px: the detector's own error on a planted dot stays under this 99 times in 100 (1.05 px, rms an axis)
JITTER_LAGS = (1, 2, 3)  # frames apart the jitter's second differences are taken: the largest reading stands
# MacKinnon (2010, "Critical values for cointegration tests", table 2, one series, constant and trend):
# the critical value is b0 + b1 / n + b2 / n^2 + b3 / n^3 on n observations. Held on 20,000 drawn walks a length
# (60 to 600 frames, the lag rule's lags): 0.8-1.0 % under the 1 % line, 4.4-5.0 % under the 5 % line (section 60).
ADF_LINE = {0.01: (-3.95877, -9.0531, -28.428, -134.155), 0.05: (-3.41049, -4.3904, -9.036, -45.374),
            0.10: (-3.12705, -2.5856, -3.925, -22.380)}
# Kwiatkowski, Phillips, Schmidt & Shin (1992), table 1: the statistic's upper tail about a level, and about a trend
# (white series about a trend pass the 5 % line 4.5-5.1 % of the time at 60 to 600 frames; the stage draws its own null)
KPSS_LINE = {False: {0.10: 0.347, 0.05: 0.463, 0.025: 0.574, 0.01: 0.739},
             True: {0.10: 0.119, 0.05: 0.146, 0.025: 0.176, 0.01: 0.216}}
ONE_BODY, SEVERAL, KEEP, WANDER, CANNOT = "one rigid body", "several", "keep their places", "wander", "cannot say"


def lag_rule(n):
    """Frames of memory the long-run variance and the ADF regression allow for: KPSS's l4, int(4 (n / 100)^(1/4))."""
    return int(4.0 * (n / 100.0) ** 0.25)


def kpss(Y, trend, lag=None):
    """The KPSS statistic of each column of Y (frames x series), about a level or about a straight line in time:
    the sum of the squared partial sums of the residuals over n^2, over the residuals' long-run variance (a Bartlett
    window of `lag` frames; `lag_rule` by default). Returns (the statistics, the sums before the division, the
    long-run variances): a pooled statistic of several series is sums.sum() / variances.sum(). A stationary series
    with no memory past `lag` passes KPSS_LINE[trend][alpha] alpha of the time on a long record."""
    Y = np.asarray(Y, float)
    Y = Y[:, None] if Y.ndim == 1 else Y
    n = len(Y)
    lag = lag_rule(n) if lag is None else lag
    t = np.arange(n, dtype=float) - (n - 1) / 2.0
    R = Y - Y.mean(0)
    if trend:
        R = R - np.outer(t, t @ R / (t @ t))
    num = (np.cumsum(R, axis=0) ** 2).sum(0) / n ** 2
    s2 = (R ** 2).sum(0) / n
    for k in range(1, lag + 1):
        s2 = s2 + 2.0 * (1.0 - k / (lag + 1.0)) * (R[k:] * R[:-k]).sum(0) / n
    s2 = np.maximum(s2, 1e-300)
    return num / s2, num, s2


def adf(y, lag=None):
    """The augmented Dickey-Fuller t ratio of a series, with a constant and a trend and `lag` lagged differences
    (`lag_rule` by default): how strongly each step pulls the series back toward its line. Returns (the ratio, the
    observations the regression used). Under a unit root -- a series that goes where its steps take it -- the ratio
    lies under `adf_line(n, alpha)` alpha of the time."""
    y = np.asarray(y, float)
    lag = lag_rule(len(y)) if lag is None else lag
    dy = np.diff(y)
    Yv = dy[lag:]
    n = len(Yv)
    tt = np.arange(n, dtype=float) - (n - 1) / 2.0
    X = np.column_stack([y[lag:-1], np.ones(n), tt] + [dy[lag - k:len(dy) - k] for k in range(1, lag + 1)])
    if n <= X.shape[1] + 1:
        return None, n
    beta = np.linalg.lstsq(X, Yv, rcond=None)[0]
    e = Yv - X @ beta
    cov = float(e @ e) / (n - X.shape[1]) * np.linalg.pinv(X.T @ X)
    return float(beta[0] / np.sqrt(max(cov[0, 0], 1e-300))), n


def adf_line(n, alpha=ADF_ALPHA):
    b = ADF_LINE[alpha]
    return b[0] + b[1] / n + b[2] / n ** 2 + b[3] / n ** 3


def jitter_read(V, frames):
    """The jitter of each column of V (a row a frame of `frames`, which may have gaps), read at the frame scale: for
    second differences taken k frames apart, white jitter of variance s^2 gives a variance g0 = 6 s^2 and an
    autocovariance k frames on gk = -4 s^2, so sqrt((g0 - gk) / 10) is s whatever slow motion the column has (as
    `_noise` reads a member, at k = 1). Here the largest over k of JITTER_LAGS stands: a camera that repeats each
    picture for two or three frames, or a jitter with a few frames' memory, reads low at k = 1 (the drone show's
    members: 0.011-0.017 px for separations that hold to 0.06-0.09). NaN where no k has NOISE_PAIRS pairs."""
    V = np.asarray(V, float)
    n = np.asarray(frames, int) - int(frames[0])
    full = np.full((int(n[-1]) + 1, V.shape[1]), np.nan)
    full[n] = V
    best = np.full(V.shape[1], np.nan)
    for k in JITTER_LAGS:
        if len(full) < 3 * k + 1:
            continue
        d2 = full[2 * k:] - 2.0 * full[k:-k] + full[:-2 * k]
        ok = np.isfinite(d2).all(1)
        both = ok[k:] & ok[:-k]
        if int(both.sum()) < NOISE_PAIRS:
            continue
        mu = d2[ok].mean(0)
        g0 = ((d2[ok] - mu) ** 2).mean(0)
        gk = ((d2[k:][both] - mu) * (d2[:-k][both] - mu)).mean(0)
        best = np.fmax(best, np.sqrt(np.maximum((g0 - gk) / 10.0, 0.0)))
    return best


def _blocks(n, lag, rng, draws=DRAWS):
    """draws x n row numbers: blocks of lag + 1 consecutive rows, started anywhere, laid end to end (a block keeps
    every autocovariance the KPSS statistic's long-run variance looks at)."""
    b = min(lag + 1, n)
    k = int(np.ceil(n / b))
    starts = rng.integers(0, n - b + 1, size=(draws, k))
    return (starts[:, :, None] + np.arange(b)[None, None, :]).reshape(draws, k * b)[:, :n]


def shared(long):
    """The members the two readings are made on, and the frames they share: members taken longest-followed first,
    each kept while the frames all of them share stay at TEST_MIN_FRAMES or more, MOST_MEMBERS at most.
    Returns (ids, frames, x, y), x and y a row a frame and a column a member."""
    keep, frames = [], None
    for i in sorted(long, key=lambda i: (-len(long[i]), i)):
        f = set(long[i]) if frames is None else frames & set(long[i])
        if frames is None or len(f) >= TEST_MIN_FRAMES:
            keep.append(i)
            frames = f
        if len(keep) == MOST_MEMBERS:
            break
    keep, frames = sorted(keep), sorted(frames or ())
    x = np.array([[long[i][n][0] for i in keep] for n in frames], float).reshape(len(frames), len(keep))
    y = np.array([[long[i][n][1] for i in keep] for n in frames], float).reshape(len(frames), len(keep))
    return keep, frames, x, y


def _off_rank(W, r):
    """(the best rank-r fit of W, what is left along the member-space directions the fit did not take -- frames x
    2 (P - 1 - r): the centring emptied one direction -- and the rms of what is left, over all of W)."""
    F, P = len(W) // 2, W.shape[1]
    U, s, Vt = np.linalg.svd(W, full_matrices=False)
    e = U[:, r:P - 1] * s[r:P - 1]
    return (U[:, :r] * s[:r]) @ Vt[:r], np.hstack([e[:F], e[F:]]), float(np.sqrt((s[r:] ** 2).sum() / W.size))


def _too_few(P, F):
    """Why neither reading can be made, or None."""
    if P < 2:
        return "fewer than two members were followed long enough, so there is no distance between members to read"
    if F < TEST_MIN_FRAMES:
        return f"the members were followed together on {F} frames, under the {TEST_MIN_FRAMES} this reading needs"
    return None


def _odds(p, draws=DRAWS):
    """A draw's p in words: "about 1 time in 250"; "at most 1 time in 1,000" where no draw reached it."""
    return f"{'at most' if p <= 1.0 / (1 + draws) else 'about'} 1 time in {round(1.0 / p):,}"


def one_body(ids, frames, x, y, rng=None, draws=DRAWS):
    """One rigid body, or several? P points of one rigid body, seen from far off (an affine camera), have positions
    x = M X + t on each frame; with each frame's mean over the points taken off, the 2F x P matrix of positions has
    rank 3 at most, 2 for a flat body or one that does not turn in depth (Tomasi & Kanade 1992). Any shift, roll, zoom
    or shear of the picture, frame by frame, changes M and not the rank. So: what is left off the best rank-3 fit
    (rank 2 with four members: three points fit any motion), as time series along the directions the fit did not take;
    whether those keep going (their pooled KPSS statistic about a level, against the same on DRAWS bodies drawn as that
    fit plus what was left, its blocks in a shuffled order, and fitted again); and whether what is left is larger than
    the detector's own errors make it (over RANK_LINE times the jitter read at the frame scale, and over what PX_FLOOR
    on every member's place would leave). It can only say that the members are not one body: a group whose figure
    stretches or shears as a whole is of rank 3 too. Fields: outcome (ONE_BODY, SEVERAL or CANNOT), members, frames,
    rank, off_rank_px, jitter_px, ratio, floor_px, kpss, p, finding."""
    P, F = len(ids), len(frames)
    out = dict(outcome=CANNOT, members=[int(i) for i in ids], frames=F, rank=None, off_rank_px=None, jitter_px=None,
               ratio=None, floor_px=None, kpss=None, p=None, alpha=ALPHA)
    if _too_few(P, F):
        return dict(out, finding=_too_few(P, F))
    if P < 4:
        return dict(out, finding=f"{P} members were followed together. Three points can be made to fit any rigid "
                                 "body, so one rigid body or several cannot be asked of fewer than four")
    r = 3 if P >= 5 else 2
    W = np.vstack([x - x.mean(1, keepdims=True), y - y.mean(1, keepdims=True)])
    Wr, e, rms = _off_rank(W, r)
    jit = jitter_read(e, frames)
    if not np.isfinite(jit).all():
        return dict(out, rank=r, off_rank_px=rms, finding="the members were not seen on enough frames in a row to read "
                                                          "their jitter, the scatter of a position from frame to frame")
    jit = float(np.sqrt((jit ** 2).sum() / (2.0 * P)))
    lag = lag_rule(F)
    _, num, s2 = kpss(e, False, lag)
    stat = float(num.sum() / s2.sum())
    rng = np.random.default_rng(TEST_SEED) if rng is None else rng
    E, more = W - Wr, 0
    for i in _blocks(F, lag, rng, draws):
        _, es, _ = _off_rank(Wr + np.vstack([E[:F][i], E[F:][i]]), r)
        _, a, b = kpss(es, False, lag)
        more += a.sum() / b.sum() >= stat
    p = (1 + more) / (1 + draws)
    ratio = rms / max(jit, 1e-9)
    floor = PX_FLOOR * float(np.sqrt((P - 1.0 - r) / P))        # what PX_FLOOR on every member's place would leave
    out.update(rank=r, off_rank_px=rms, jitter_px=jit, ratio=ratio, floor_px=floor, kpss=stat, p=p,
               ratio_line=RANK_LINE[r])
    body = "one rigid body" if r == 3 else "one flat rigid body"
    left = (f"What is left after the best {body[4:]} is taken out is {rms:.2f} pixels, {ratio:.1f} times their jitter "
            f"(the scatter of a position from frame to frame, {jit:.2f} pixels)")
    large = ratio > RANK_LINE[r] and rms > floor
    if large and p < ALPHA:
        grows = f"It keeps growing, which a rigid body with that jitter does {_odds(p, draws)}"
        if r == 3:
            return dict(out, outcome=SEVERAL, finding=f"the {P} members do not move as one rigid body: they are "
                                                      f"several objects. {left}. {grows}")
        return dict(out, finding=f"the 4 members do not move as one flat rigid body. {left}. {grows}. They are several "
                                 "objects, or one solid body turning: four points cannot tell these apart")
    if large:
        return dict(out, finding=f"the {P} members move against one another by more than their jitter, and come back. "
                                 f"{left}. That is one body that flexes, or several objects holding station")
    return dict(out, outcome=ONE_BODY, finding=f"the {P} members move as the parts of {body} would. {left}. That is "
                "no more than the detector's own errors can make it. A formation that holds its shape reads the same")


def places(ids, frames, x, y, rng=None, draws=DRAWS):
    """Do the members keep their places? Every pair's separation, over the group's size on that frame where there
    are three members or more (a zoom, a roll or a shift of the picture then changes nothing; the separations are
    quoted at the group's mean size), read four ways: how far it wanders about a straight line in time (a steady change
    of aspect is allowed, as in `rigidity`); the jitter of the separation itself at the frame scale (a double
    difference: across the two members, which takes the camera's shake out, then in time); whether it keeps going (the
    KPSS statistic about a trend, against DRAWS draws of its own blocks in a shuffled order, the largest pair's of each
    draw: one rate for the whole group); and whether it returns (the ADF t ratio under MacKinnon's line).

    A separation is `large` where it wanders by more than PAIR_LINE times its jitter and by more than PX_FLOOR. A pair
    KEEPs its separation where the wander is not large: that is what was seen, to within the wander quoted, and needs
    no test -- unless the lines themselves are wider than the separation (a pair closer together than the detector's
    own errors: CANNOT). A pair WANDERs where the wander is large, keeps going, and does not return. A large wander
    that does not keep going, or one that returns (a cycle), is CANNOT: the two tests disagree. The group WANDERs with
    any pair, KEEPs with every pair."""
    P, F = len(ids), len(frames)
    out = dict(outcome=CANNOT, members=[int(i) for i in ids], frames=F, scaled=P >= 3, pairs=[], alpha=ALPHA,
               adf_alpha=ADF_ALPHA, ratio_line=PAIR_LINE, floor_px=PX_FLOOR)
    if _too_few(P, F):
        return dict(out, finding=_too_few(P, F))
    a, b = np.triu_indices(P, 1)
    D = np.hypot(x[:, a] - x[:, b], y[:, a] - y[:, b])
    if P >= 3:
        G = np.sqrt((D ** 2).mean(1, keepdims=True))
        D = D / G * float(G.mean())
    t = np.arange(F, dtype=float) - (F - 1) / 2.0
    U = D - D.mean(0)
    U = U - np.outer(t, t @ U / (t @ t))
    wander = np.sqrt((U ** 2).mean(0))
    jit = jitter_read(D, frames)
    if not np.isfinite(jit).all():
        return dict(out, finding="the members were not seen on enough frames in a row to read their jitter")
    lag = lag_rule(F)
    stat = kpss(D, True, lag)[0]
    rng = np.random.default_rng(TEST_SEED) if rng is None else rng
    more = np.zeros(len(stat))
    for i in _blocks(F, lag, rng, draws):
        more += kpss(U[i], True, lag)[0].max() >= stat
    p = (1 + more) / (1 + draws)
    ratio = wander / np.maximum(jit, 1e-9)
    tau = [adf(D[:, c], lag)[0] for c in range(D.shape[1])]
    line = adf_line(F - 1 - lag)
    calls = []
    for c in range(D.shape[1]):
        large = bool(ratio[c] > PAIR_LINE and wander[c] > PX_FLOOR)
        going = bool(p[c] < ALPHA)
        back = tau[c] is not None and tau[c] < line
        fine = max(PAIR_LINE * jit[c], PX_FLOOR) < D[:, c].mean()          # the lines are finer than the separation
        calls.append(WANDER if large and going and not back else KEEP if not large and fine else CANNOT)
        out["pairs"].append(dict(members=[int(ids[a[c]]), int(ids[b[c]])], separation_px=float(D[:, c].mean()),
                                 wander_px=float(wander[c]), jitter_px=float(jit[c]), ratio=float(ratio[c]),
                                 kpss=float(stat[c]), p=float(p[c]), adf=tau[c], adf_line=float(line),
                                 large=large, keeps_going=going, returns=bool(back), outcome=calls[-1]))
    n = len(calls)
    zoom = "" if P >= 3 else ". A zoom of the camera would change their distance too"
    jitter = "their jitter, the scatter of a position from frame to frame"
    top = max(out["pairs"], key=lambda q: q["wander_px"])
    w = [q for q in out["pairs"] if q["outcome"] == WANDER]
    if w:
        said = (f"{len(w)} of the {n} distances between members wander and do not come back, by up to" if P >= 3 else
                "The distance between the two members wanders and does not come back, by")
        return dict(out, outcome=WANDER, finding=f"the members do not keep their places. {said} "
                    f"{top['wander_px']:.1f} pixels about a steady change. That is "
                    f"{max(q['ratio'] for q in w):.0f} times {jitter}{zoom}")
    most = (f"at most {top['wander_px']:.2f} pixels about a steady change, "
            f"{max(q['ratio'] for q in out['pairs']):.1f} times {jitter}{zoom}")
    if all(c == KEEP for c in calls):
        said = (f"None of the {n} distances between members wanders" if P >= 3 else
                "The distance between the two members does not wander")
        return dict(out, outcome=KEEP, finding=f"the members keep their places. {said} by more than the detector's "
                                               f"own errors can make it. It is {most}")
    close = sum(not q["large"] for q in out["pairs"]) - sum(c == KEEP for c in calls)
    large = sum(q["large"] for q in out["pairs"])
    why = (f"{large} of the {n} distances between members wander by more than the detector's own errors can make "
           "them, but they come back or stop" if large else
           f"{close} of the {n} pairs are closer together than the detector's own errors can move them")
    return dict(out, finding=f"whether the members keep their places cannot be said. {why}. The wander is {most}")


def readings(tracks):
    """The two calibrated readings of a group's followed members ({id: {frame: (x, y, ...)}}): dict(one_body=...,
    places=...), each made on the members `shared` keeps and the frames they share, each with draws of its own from
    TEST_SEED. `places` also says whether a wander could be one rigid body turning (`one_body_not_ruled_out`)."""
    ids, frames, x, y = shared({i: t for i, t in tracks.items() if len(t) >= MIN_FRAMES})
    body, place = one_body(ids, frames, x, y), places(ids, frames, x, y)
    # One rigid body that turns in depth changes its members' distances in the picture too (drawn bodies turning up to
    # 60 degrees: "wander" for 28 to 58 % of them), so a wander says "several" only with the first reading.
    place["one_body_not_ruled_out"] = turn = bool(place["outcome"] == WANDER and body["outcome"] != SEVERAL)
    if turn:
        place["finding"] += (". One rigid body that turns would change them so, and the members move as one would"
                             if body["outcome"] == ONE_BODY else
                             ". One rigid body that turns in depth would change them too, and "
                             + ("fewer than five members" if len(ids) < 5 else "the other reading") + " cannot tell")
    return dict(one_body=body, places=place)


def measure(clip, track, masks=None, rows=None, radius=RADIUS, size=SIZE, dark=False, out=None, say=print,
            progress=None, stop=None, procs=None):
    """The stage: how many points the tracked thing is, frame by frame, and if more than one,
    whether they keep their places. Writes <out>_members.csv and <out>_members.png."""
    masks = masks if masks is not None else vf.static_masks(clip)
    tracks, spots, fixed, bg = members(clip, track, masks, rows, radius, size, dark, progress, stop, procs)
    moved = _against(track, bg, sorted(spots))
    tracks = {i: t for i, t in tracks.items() if with_the_group(t, track, bg)} if moved >= STILL else tracks
    counts = np.array([sum(n in t for t in tracks.values() if len(t) >= MIN_FRAMES) for n in sorted(spots)])
    fields = dict(frames=len(spots), radius_px=radius, detector_size_px=size, dark=dark,
                  points_per_frame=None if not len(counts) else dict(median=float(np.median(counts)),
                                                                     max=int(counts.max()), min=int(counts.min())),
                  on_the_sensor=fixed, member_tracks=len(tracks), track_against_background_px=moved,
                  scene_told_apart=bool(moved >= STILL))
    if not len(counts):
        return Found("groups", fields=dict(fields, several=None, rigid=None),
                     no_power=[("groups", "no frame of the track is in the clip")])
    if counts.max() == 0:
        why = (f"no point-like feature near the track moves with it for {MIN_FRAMES} frames: not a group of points "
               "(an object wider than a point, with no background all round a spot on it, is not one)")
        return Found("groups", dict(finding=why), dict(fields, several=False, rigid=None, finding=why))
    several = bool(np.median(counts) >= 2)
    fields["several"] = several
    rig = rigidity(tracks) if several else dict(members_followed=None, noise_px={}, pairs=[], rigid=None,
                                                finding="one point on most frames: a single object, not a group")
    fields.update(rig)
    result = dict(points=f"{np.median(counts):g} a frame moving with the track (median; {counts.min()}-{counts.max()}), "
                         f"within {radius:g} px of it" + (f", {fixed} spots on the sensor left out" if fixed else ""),
                  finding=rig["finding"])
    if several:                                         # the two calibrated readings, beside `rigid` (section 60):
        read = readings(tracks)                         # a single object's record has neither, and stays as it was
        fields.update(read)
        result.update({"one rigid body or several": read["one_body"]["finding"],
                       "do the members keep their places": read["places"]["finding"]})
    notes = [] if moved >= STILL else [
        f"The track moves only {moved:.0f} px against the background over these frames, so points of the scene near "
        "it cannot be told from members of a group by their motion: every point followed near it is counted."]
    files = []
    if out:
        with open(f"{out}_members.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["frame", "member", "x_px", "y_px", "response"])
            for i, t in sorted(tracks.items()):
                if len(t) >= MIN_FRAMES:
                    for n, (x, y, v) in sorted(t.items()):
                        w.writerow([n, i, round(x, 2), round(y, 2), round(v, 1)])
        files.append(f"{out}_members.csv")
        if several:
            figure(tracks, track, f"{out}_members.png")
            files.append(f"{out}_members.png")
        say(f"wrote {', '.join(files)}")
    npw = [] if rig["rigid"] is not None or not several else [("groups: rigid or not", rig["finding"])]
    if several:
        npw += [(f"groups: {what}", read[k]["finding"]) for k, what in (("one_body", "one rigid body or several"),
                                                                       ("places", "do the members keep their places"))
                if read[k]["outcome"] == CANNOT]
    long = {i: {n: xyv[:2] for n, xyv in t.items()} for i, t in tracks.items() if len(t) >= MIN_FRAMES}
    return Found("groups", result, fields, files=files, no_power=npw, notes=notes, carry=long if several else None)


def _step(p, a, b):
    return np.subtract(p[b][:2], p[a][:2])


def _against(track, bg, ns):
    """How far the track moves against the background from the first of `ns` to the last."""
    return float(np.hypot(*(_step(track, ns[0], ns[-1]) - _step(bg, ns[0], ns[-1])))) if len(ns) > 1 else 0.0


def with_the_group(t, track, bg):
    """Whether a followed point moves with the track rather than with the background (the scene's
    own shift, `propose.background_shift`, frame to frame): over the frames it was followed, its
    displacement is nearer the track's than the background's. A point of the scene the group
    passes moves with the scene, however the camera pans; a member of a flock moves with the
    group, give or take its shuffling (PR135's: up to half of the group's motion on the screen)."""
    ns = [n for n in sorted(t) if n in track and n in bg]
    if len(ns) < 2:
        return False
    own = _step(t, ns[0], ns[-1])
    return bool(np.hypot(*(own - _step(track, ns[0], ns[-1]))) < np.hypot(*(own - _step(bg, ns[0], ns[-1]))))


def figure(tracks, track, path):
    """Each member followed long enough, as its place relative to the track, frame by frame. In the house style
    (figures.setup)."""
    from . import figures
    plt = figures.setup()
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10.5, 4.8), constrained_layout=True)
    for i, t in sorted(tracks.items()):
        if len(t) < MIN_FRAMES:
            continue
        ns = [n for n in sorted(t) if n in track]
        dx = [t[n][0] - track[n][0] for n in ns]
        dy = [t[n][1] - track[n][1] for n in ns]
        ax.plot(dx, dy, "o", ms=2, label=f"member {i}")      # the names the beat figure and the report use
        bx.plot(ns, np.hypot(dx, dy), lw=1.6)
    ax.invert_yaxis()
    ax.set_aspect("equal", "datalim")
    ax.set_xlabel("Across, from the track (pixels)")
    ax.set_ylabel("Down, from the track (pixels)")
    ax.set_title("Place of each member")
    bx.set_xlabel("Frame")
    bx.set_ylabel("Distance from the track (pixels)")
    bx.set_title("Distance of each member")
    handles, labels = ax.get_legend_handles_labels()
    if handles:                                    # which colour is which member: under both panels, clear of every line
        fig.legend(handles, labels, loc="outside lower center", ncol=min(len(labels), 6), markerscale=2.5)
    figures.save(fig, path, dpi=200)
    plt.close(fig)


def said(fields):
    """What `mcdonald groups` prints, from the fields."""
    L = []
    p = fields.get("points_per_frame")
    if p:
        L.append(f"points moving with the track, within {fields['radius_px']:g} px of it: {p['median']:g} a frame "
                 f"(median; {p['min']}-{p['max']})" + (f"; {fields['on_the_sensor']} spots on the sensor left out"
                                              if fields["on_the_sensor"] else ""))
    for q in fields.get("pairs", []):
        L.append(f"  members {q['members'][0]} and {q['members'][1]}: {q['frames']} frames together "
                 f"({q['first']}-{q['last']}), {q['separation_px']:.1f} px apart (range {q['separation_range_px']:.1f}), "
                 f"wandering {q['wander_px']:.2f} px = {q['wander_over_noise']:.1f} x the position noise")
    L.append(fields.get("finding", ""))
    for k, what in (("one_body", "one rigid body or several"), ("places", "do the members keep their places")):
        if fields.get(k):
            L.append(f"{what}: {fields[k]['outcome']} -- {fields[k]['finding']}")
    return L


# ---- CLI ----------------------------------------------------------------------------
def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", required=True, help="CSV with frame and x/y columns: the group, as linked")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--radius", type=float, default=RADIUS, help=f"px about the track to look for members in (default {RADIUS:g})")
    ap.add_argument("--size", type=float, default=SIZE, help=f"the detector's scale for a member, px (default {SIZE:g})")
    ap.add_argument("--dark", action="store_true", help="the members are darker than what is round them")
    ap.add_argument("--mask-rows")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>; with --n0/--n1, the segment's own folder in it, <tag>/segment-<n0>-<n1>)")
    ap.add_argument("--procs", type=int, default=None, help=PROCS_HELP)
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        found, clip = _main(args)
    code = 0 if found.fields.get("several") is not None else vf.EXIT_NOTHING
    if args.json:
        emit(found.envelope("groups", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


def _main(args):
    video, tag, _ = vf.resolve(args.video)
    track = vf.read_track(args.track)
    n0 = args.n0 if args.n0 is not None else min(track)
    n1 = args.n1 if args.n1 is not None else max(track)
    clip = vf.Clip(video, args.workdir, n0, n1)
    out = vf.out_prefix(args.out, tag, vf.named(args.n0, args.n1, clip))
    print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
    found = measure(clip, track, rows=vf.parse_rows(args.mask_rows), radius=args.radius, size=args.size,
                    dark=args.dark, out=out, progress=to_stderr(), procs=args.procs)
    print("\n".join(said(found.fields)))
    return found, clip


if __name__ == "__main__":
    raise SystemExit(main())
