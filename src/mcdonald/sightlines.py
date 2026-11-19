"""Lines of sight that carry their own time and their camera: cameras on the ground as an input of `mcdonald drift`.

`mcdonald drift` reads T1 (the height) and T2 (the winds) from lines of sight that cross: `drift.fit_track` fits a
straight path at a steady velocity to rays, each an azimuth and a depression at a known place and time. Until
2026-11-17 the only way in was an aircraft's own track (`--platform`, `--los`): one camera that moves, its readings
keyed by the frame of one video, every azimuth resting on one reference (the display's true north). Several cameras
standing on the ground see the same object at once from places kilometres apart, and their rays fix a path with no
turn at all. This module is their way in (`--rays`, `--cameras`):

    time, camera, az_deg, el_deg (or dep_deg) [, lat, lon, alt_m]      one row a reading

- A reading has its own time (seconds from any zero, a unix time or an ISO time), so no video and no frame rate are
  needed, and several cameras may read at the same instant.
- A camera has a name and a place: in the rows, or once in a cameras file (camera, lat, lon, alt_m). A camera that
  moves gives its place in every row.
- Each camera has its own pointing error, a constant in azimuth and one in elevation (`pointing`): a calibrated
  camera's rotation is known only so well, and over the few degrees an object crosses, any small rotation of the
  camera, or a lens model that is off there, moves all of its rays alike in the two angles. Two cameras' errors are
  not one error: one constant added to every azimuth (`drift.az_reference`, the aircraft's case) turns every ray the
  same way and hardly moves the angle at which two rays cross, while each camera's own error changes that angle
  itself, and with it the range. What is carried is the error of taking every camera's pointing as right, as the
  aircraft's route carries its one reference: the path stays the six-parameter fit.
- Each camera's rays have their own scatter (`own_scatter`): `drift.own_scatter`'s rule, camera by camera.
- The bootstrap over the readings resamples each camera's own (`resample`): which camera read how often is the
  design, not chance.
- The gates that say whether the rays fix a path at all are the aircraft route's (`drift.path_off_line`,
  `drift.range_bound`), read for cameras: the places the rays start from must leave one straight path at a steady
  speed (one place, for a camera standing still) by more than their own error, and the range from every camera must
  be known to better than a factor e with the pointing errors counted.

- The misfit gate (`asked`, `MISFIT`; since 2026-11-19, method section 92): one straight path may pass through
  every camera's rays only if some camera's pointing is far further off than it is taken as known to be. Then the
  cameras are not following one body on one straight path, and T1 and T2 are refused ("no single straight path fits
  these lines of sight") where they used to judge the path fitted all the same.

`rays(..., reference="shared")` keeps the cameras' names and times and fits as the aircraft's route does (one
azimuth reference for all, one scatter, the plain bootstrap): for cameras that do share one reference, and for
holding this input to runs made before it existed.

Method: docs/method.md sections 66 and 92.
"""
import math
import re
from datetime import datetime, timezone

import numpy as np

TIME_KEYS = (("t_s", "time_s"), ("t_unix_s", "unix_s"), ("time_utc", "time", "utc"))    # seconds, unix seconds, ISO


def _unix(text):
    """An ISO 8601 time as unix seconds: 2026-05-27T21:30:05.25Z, with an offset, or with none (taken as UTC)."""
    m = re.fullmatch(r"\s*(\d{4}-\d\d-\d\d)[T ](\d\d:\d\d(?::\d\d)?)(\.\d+)?\s*(Z|[+-]\d\d:?\d\d)?\s*", str(text))
    if not m:
        raise ValueError(f"{text!r} is not a time (2026-05-27T21:30:05.25Z)")
    day, clock, frac, zone = m.groups()
    d = datetime.fromisoformat(f"{day}T{clock if clock.count(':') == 2 else clock + ':00'}")
    off = 0.0
    if zone and zone != "Z":
        z = zone.replace(":", "")
        off = (1 if z[0] == "+" else -1) * (int(z[1:3]) * 3600 + int(z[3:5]) * 60)
    return d.replace(tzinfo=timezone.utc).timestamp() - off + (float(frac) if frac else 0.0)


def read_cameras(path):
    """camera, lat, lon (decimal degrees, west and south negative), alt_m (or alt_ft) above the sea -> {name: place}."""
    from .drift import _num, read_rows
    out = {}
    for r in read_rows(path):
        alt = _num(r, "alt_m")
        if alt is None:
            alt = _num(r, "alt_ft") * 0.3048
        out[str(r.get("camera") or r.get("name")).strip()] = (float(r["lat"]), float(r["lon"]), alt)
    return out


def read_sightlines(path, cameras=None):
    """The readings of a rays file, a dict each: time (s), absolute (whether the time is a unix time), camera, lat,
    lon, alt (the camera's place), az and dep (deg; true azimuth, depression below the horizontal). Columns:
    - the time: `t_s` (seconds from any zero), `t_unix_s` (unix seconds) or `time_utc` (ISO 8601, UTC where it names
      no zone);
    - `camera`, the camera's name (a file without the column is one camera's);
    - `az_deg`, and `el_deg` (elevation above the horizontal) or `dep_deg` (depression below it);
    - the camera's place, `lat`, `lon`, `alt_m` (or `alt_ft`), in the rows or in `cameras` (`read_cameras`)."""
    from .drift import _num, read_rows
    rows = read_rows(path)
    if not rows:
        raise ValueError(f"{path}: no readings")
    kind, key = next(((i, k) for i, keys in enumerate(TIME_KEYS) for k in keys if k in rows[0]), (None, None))
    if key is None:
        raise ValueError(f"{path}: no time column (t_s, t_unix_s or time_utc)")
    out = []
    for r in rows:
        name = str(r.get("camera") or "camera 1").strip()
        dep = _num(r, "dep_deg")
        if dep is None:
            el = _num(r, "el_deg")
            if el is None:
                raise ValueError(f"{path}: a reading without el_deg or dep_deg")
            dep = -el
        if r.get("lat") not in (None, ""):
            alt = _num(r, "alt_m")
            if alt is None:
                alt = _num(r, "alt_ft") * 0.3048
            place = (float(r["lat"]), float(r["lon"]), alt)
        elif cameras and name in cameras:
            place = cameras[name]
        else:
            raise ValueError(f"{path}: no place for the camera {name!r} (lat, lon, alt_m in the rows, or a cameras file)")
        t = _unix(r[key]) if kind == 2 else float(r[key])
        out.append(dict(time=t, absolute=kind != 0, camera=name, lat=place[0], lon=place[1], alt=place[2],
                        az=float(r["az_deg"]), dep=dep))
    return out


def rays(readings, reference="camera"):
    """The readings as the dict `drift.fit_track` fits, with `drift.rays`' keys (t, A, az, dep, platform, rot, and
    `frames`, here the readings' numbers in time order from 1, since no video numbers them) and four more:
    - `camera`, each reading's camera as an index into `cameras`, the names in the order they first read;
    - `epoch`, the unix time of t = 0 where the times are absolute (the whole second at or before the first
      reading), else None;
    - `reference`: "camera", each camera its own pointing error (`pointing`); "shared", one azimuth reference for
      all, as the aircraft's route has it.
    Readings at the same instant keep the order they were given in."""
    from .drift import ecef, enu_rows
    if reference not in ("camera", "shared"):
        raise ValueError("reference is 'camera' or 'shared'")
    order = sorted(range(len(readings)), key=lambda i: readings[i]["time"])
    S = [readings[i] for i in order]
    absolute = bool(S and S[0].get("absolute"))
    epoch = float(math.floor(S[0]["time"])) if absolute else None
    names = []
    for r in S:
        if r["camera"] not in names:
            names.append(r["camera"])
    P = np.array([(r["lat"], r["lon"], r["alt"]) for r in S], float).reshape(-1, 3)
    return dict(frames=np.arange(1, len(S) + 1), t=np.array([r["time"] - (epoch or 0.0) for r in S], float),
                A=np.array([ecef(*p) for p in P]).reshape(-1, 3), az=np.array([r["az"] for r in S], float),
                dep=np.array([r["dep"] for r in S], float), platform=P,
                rot=np.array([enu_rows(la, lo) for la, lo, _ in P]).reshape(-1, 3, 3),
                camera=np.array([names.index(r["camera"]) for r in S], int), cameras=tuple(names), epoch=epoch,
                reference=reference)


def own(R):
    """Whether the rays came from cameras that each have their own pointing error."""
    return "camera" in R and R.get("reference", "camera") != "shared"


def when(R, t):
    """The UTC time of `t` on the rays' own clock, as `--when` takes it (to the second), or None where their times
    are not absolute."""
    if R.get("epoch") is None:
        return None
    return datetime.fromtimestamp(round(R["epoch"] + t), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def resample(cam, rng):
    """One bootstrap resample of the readings, each camera's own drawn with replacement: indices, in time order."""
    return np.sort(np.concatenate([rng.choice(np.flatnonzero(cam == c), int(np.sum(cam == c))) for c in np.unique(cam)]))


def own_scatter(fun, cam):
    """`drift.own_scatter`'s rule, camera by camera: whose errors the fit's covariance is read with, from its weighted
    residuals `fun` (the n azimuths, then the n depressions, each over the error given). A camera whose rays fit
    worse than the errors given has them scaled up by its own misfit; one whose rays fit as well as they allow keeps
    them; one whose rays fit better than they allow (the lower tail of chi-square under `drift.OWN_P`) is read with
    its rays' own scatter, each axis its own, widened by Student's t, never under `drift.OWN_LEAST` of the errors
    given nor over them. A camera's degrees of freedom are its two residuals a reading less its share of the six
    parameters, by its share of the readings. Returns (scale, sources, p): the scale of each residual's squared
    error, and for each camera where its errors came from and the chance of a fit as close."""
    from scipy.stats import chi2 as chi2_dist, norm, t as t_dist
    from .drift import OWN_LEAST, OWN_P
    n = len(cam)
    scale, sources, ps = np.ones(2 * n), [], []
    for c in range(int(cam.max()) + 1 if n else 0):
        i = np.flatnonzero(cam == c)
        if not len(i):
            sources.append(None)
            ps.append(None)
            continue
        share = len(i) / n
        dof = max(1.0, 2 * len(i) - 6 * share)
        fa, fd = fun[i], fun[n + i]
        chi2 = float(fa @ fa + fd @ fd) / dof
        if chi2 >= 1.0:
            scale[i] = scale[n + i] = chi2
            sources.append("the errors given, scaled up by the rays' misfit")
            ps.append(None)
            continue
        p = float(chi2_dist.cdf(chi2 * dof, dof))
        ps.append(p)
        if p >= OWN_P:
            sources.append("the errors given")
            continue
        tq = float(t_dist.ppf(0.975, dof) / norm.ppf(0.975))
        axis = max(1.0, len(i) - 3 * share)
        scale[i] = min(1.0, max(float(fa @ fa) / axis * tq ** 2, OWN_LEAST ** 2))
        scale[n + i] = min(1.0, max(float(fd @ fd) / axis * tq ** 2, OWN_LEAST ** 2))
        sources.append("the rays' own scatter")
    return scale, sources, ps


def _offsets(R, sig):
    """What one degree added to a camera's azimuths, or to its depressions, does to the fit's weighted residuals:
    a column for each camera's azimuth and one for its depression (2n by 2K; the residual falls by the column)."""
    n, K = len(R["t"]), len(R["cameras"])
    B = np.zeros((2 * n, 2 * K))
    for c in range(K):
        i = np.flatnonzero(R["camera"] == c)
        B[i, 2 * c] = np.cos(np.radians(R["dep"][i])) / sig[0]
        B[n + i, 2 * c + 1] = 1.0 / sig[1]
    return B


def pointing(fit, R, sig, scale, known):
    """What each camera's own pointing error does to the path. A camera's pointing is a rotation known only so well,
    and across the few degrees an object crosses in its frame a small rotation (or a lens model that is off there)
    moves all of its rays alike: a constant in azimuth and a constant in elevation, the camera's own. The rays'
    scatter cannot show them, and the path fitted to the rays moves with them: by S = (J'J)^-1 J'B for one degree,
    J the fit's Jacobian and B what a degree does to the residuals (`_offsets`), exact for the least-squares path
    while the offsets are small. The path itself stays the six-parameter fit, which takes every camera's pointing
    as right; what is carried is the error of doing so. `known` (az, el; deg) is how well each camera's pointing is
    known beforehand, and the covariance it leaves in the six parameters is S diag(known^2) S'. Where an angle's
    `known` is inf nothing is taken as known of it, and the rays' own reading stands in (its fitted value and its
    error, as `drift.az_reference` does), or None where the rays cannot read it.

    The rays' own reading of the offsets is reported beside, never used to tighten what is taken as known: the
    offsets fitted with the path, each held to `known` (the same rays, the same errors `scale`; one linear step
    from the fit). Two cameras' rays read only the part of their offsets that makes the rays miss each other; three
    read more.

    Returns dict(cov, pull, fitted_deg, fitted_err_deg), `pull` the 6 by 2K matrix S and the two readings K by 2
    (azimuth, elevation; an elevation offset is minus the depression's); or None where nothing can be carried."""
    K = len(R["cameras"])
    k = np.tile(np.asarray(known, float), K)
    J, B, w = fit.jac, _offsets(R, sig), 1.0 / scale
    try:
        S = np.linalg.solve(J.T @ J, J.T @ B)
        prior = np.where(np.isfinite(k), 1.0 / np.maximum(k, 1e-12) ** 2, 0.0)
        M = np.block([[(J.T * w) @ J, -(J.T * w) @ B], [-(B.T * w) @ J, (B.T * w) @ B + np.diag(prior)]])
        d = 1.0 / np.sqrt(np.diag(M))                      # metres beside metres a second beside degrees: scaled first
        if not np.all(np.isfinite(d)) or np.linalg.cond(M * np.outer(d, d)) > 1e12:
            raise np.linalg.LinAlgError
        C = np.linalg.inv(M * np.outer(d, d)) * np.outer(d, d)
        z = C @ np.r_[-(J.T * w) @ fit.fun, (B.T * w) @ fit.fun]
    except np.linalg.LinAlgError:
        if not np.all(np.isfinite(k)):
            return None
        return dict(cov=(S * k ** 2) @ S.T, pull=S, fitted_deg=None, fitted_err_deg=None)
    q, sd = z[6:], np.sqrt(np.maximum(np.diag(C)[6:], 0.0))
    if np.all(np.isfinite(k)):
        cov = (S * k ** 2) @ S.T
    else:                                                  # left to the rays: their reading and its error
        cov = S @ (C[6:, 6:] + np.outer(q, q)) @ S.T
    sign = np.tile([1.0, -1.0], K)                         # an elevation offset is minus the depression's
    return dict(cov=cov, pull=S, fitted_deg=(q * sign).reshape(K, 2), fitted_err_deg=sd.reshape(K, 2))


MISFIT = 19.0           # T1 and T2 are refused where one straight path asks a camera's pointing to be off by more than
#                         this many times what it is taken as known to. From a null (2026-11-19, method section 92): 6,073
#                         aircraft of the Galileo catalog, none of them in the drift paper's sample, each with its
#                         transponder's own track within 1.5 km of the cameras' position, so single bodies by a record the
#                         cameras did not make. Their misfit is log-normal up to its 99.5th percentile (median 1.9, sigma
#                         0.75 in the logarithm), and that law puts one single body in a thousand over 19.4. Seen over 19:
#                         12 of the 6,073 (0.20 %), the excess being cameras that are asked tens of degrees. The three
#                         objects known to be two things matched as one read 29, 41 and 58. It is in units of what is
#                         taken as known (0.7 and 0.4 deg for those cameras), so it belongs to that statement of it
ASKED_MIN = 9           # a camera with fewer readings than a path is fitted from (`drift.READINGS_MIN`) is not asked: its
#                         few rays hardly move the path, and an offset fitted to them is their own scatter


def asked(fit, R, sig, plane, tm, known):
    """The pointing that one straight path asks of the cameras. The six-parameter fit takes every camera's pointing
    as right, and `pointing` carries the error of doing so. Here the same rays are fitted again with each camera's
    two offsets as parameters too (a constant added to its azimuths and one to its elevations), each offset held to
    what is taken as known of it (`known`: a Gaussian prior of that size), the rays at the errors given (`sig`, not
    scaled by their misfit). Lines of sight to one body on one straight path ask for offsets of the size the cameras
    really have. Lines of sight to two different things matched as one, or to a body that does not move as the model
    says, can be brought onto one straight path only by offsets many times that size, however small the rays' own
    scatter. So the size of the largest offset asked, in units of what is taken as known, is read as the misfit: it
    says in degrees how wrong the cameras would have to be for the fitted path's model to hold.

    The reduced chi-square and the rms about the six-parameter path do not serve: a real aircraft seen by cameras
    whose clocks and lens models are a little off misses a straight path by more than one cloud matched with a fast
    object does (method section 92). `drift.model_test`'s p does not either: it is under 0.01 on half the clouds.

    Returns dict(asked_deg, times, rms_deg, params), or None where nothing is taken as known of the pointing (an
    inf: there is nothing to hold the offsets against) or the fit does not run: `asked_deg` K by 2 (azimuth,
    elevation: the error each camera's pointing would have, added to its readings to bring them onto the path),
    `times` each camera's larger offset in units of `known`, `rms_deg` the rays' rms about that path (azimuth,
    elevation) and `params` its six parameters."""
    from scipy.optimize import least_squares
    from .drift import _path_angles, _residuals
    K, cam = len(R["cameras"]), R["camera"]
    k = np.tile(np.asarray(known, float), K)
    if not np.all(np.isfinite(k)) or np.any(k <= 0):
        return None

    def shifted(q):
        o = q[6:].reshape(K, 2)
        return dict(R, az=R["az"] + o[cam, 0], dep=R["dep"] + o[cam, 1])

    def res(q):
        return np.r_[_residuals(shifted(q), sig, plane, tm)(q[:6]), q[6:] / k]
    try:
        g = least_squares(res, np.r_[fit.x, np.zeros(2 * K)], x_scale=[1000, 1000, 100, 10, 10, 1] + [1.0] * (2 * K))
    except ValueError:
        return None
    if not np.all(np.isfinite(g.x)):
        return None
    o = g.x[6:].reshape(K, 2)
    S = shifted(g.x)
    a, e, _ = _path_angles(g.x[:6], S, plane, tm)
    rms = [float(np.sqrt(np.mean(((a - S["az"] + 180) % 360 - 180) ** 2))), float(np.sqrt(np.mean((e - S["dep"]) ** 2)))]
    deg = o * np.array([1.0, -1.0])                        # an elevation offset is minus the depression's
    return dict(asked_deg=deg, times=np.max(np.abs(o) / np.asarray(known, float), axis=1), rms_deg=rms,
                params=g.x[:6].tolist())


def misfit(ask, R, known):
    """The misfit's fields from `asked`: the camera that is asked the most (of those with ASKED_MIN readings or
    more), how many times what is taken as known that is (`misfit`), in which angle and by how many degrees, and
    whether the gate holds (`misfit_gate`: at or under MISFIT). None for each where nothing was asked."""
    none = dict(misfit=None, misfit_camera=None, misfit_deg=None, misfit_angle=None, misfit_rms_deg=None,
                misfit_gate=None)
    if ask is None:
        return none
    n = np.array([int(np.sum(R["camera"] == c)) for c in range(len(R["cameras"]))])
    ok = np.flatnonzero(n >= ASKED_MIN)
    if not len(ok):
        return none
    c = int(ok[np.argmax(ask["times"][ok])])
    z = float(ask["times"][c])
    j = int(np.argmax(np.abs(ask["asked_deg"][c]) / np.asarray(known, float)))
    return dict(misfit=z, misfit_camera=R["cameras"][c], misfit_deg=float(ask["asked_deg"][c, j]),
                misfit_angle=("azimuth", "elevation")[j], misfit_rms_deg=ask["rms_deg"], misfit_gate=bool(z <= MISFIT))


def geometry(R, p, plane, tm):
    """Where the rays start from, in the words' numbers: how many places (`places`), the farthest two apart
    (`baseline_m`), the largest angle at which two places' lines of sight to the path's point at the mean time cross
    (`los_cross_deg`), and the most any one camera's own line of sight turned (`los_turn_deg`)."""
    from .drift import _path_points
    P = np.unique(np.round(R["A"], 2), axis=0)
    X = _path_points(np.asarray(p, float), np.array([tm]), tm, plane)[0]
    u = X - P
    u = u / np.maximum(np.linalg.norm(u, axis=1), 1e-9)[:, None]
    d = np.linalg.norm(P[:, None] - P[None], axis=-1)
    turn = 0.0
    for c in range(len(R["cameras"])):
        a = np.unwrap(np.radians(R["az"][R["camera"] == c]))
        if len(a):
            turn = max(turn, float(np.degrees(a.max() - a.min())))
    return dict(places=int(len(P)), baseline_m=float(d.max()),
                los_cross_deg=float(np.degrees(np.arccos(np.clip(u @ u.T, -1.0, 1.0))).max()), los_turn_deg=turn)


def range_bound(cov, p, R, plane, tm):
    """`drift.range_bound` from the camera it is largest for: the bound on the logarithm of the range from each
    camera at its reading nearest the mean time, through the covariance `cov`."""
    from .drift import range_bound as bound
    n, worst = len(R["t"]), 0.0
    for c in range(len(R["cameras"])):
        i = np.flatnonzero(R["camera"] == c)
        if len(i):
            Rc = {key: (v[i] if isinstance(v, np.ndarray) and len(v) == n else v) for key, v in R.items()}
            worst = max(worst, bound(cov, p, Rc, plane, tm))
    return worst


def carried(fit, R, sig, plane, tm, scale, sources, ps, cov, out, known):
    """`drift.fit_track`'s fields where each camera has its own pointing: the errors with the pointing carried
    (`pointing`), the range's bound with it, the cameras one by one, and the geometry. `out` holds the fields from
    the rays' scatter and the bootstrap; `known` (az, el; deg) is how well a camera's pointing is known beforehand."""
    from .drift import _path_angles
    n, K, p = len(R["t"]), len(R["cameras"]), fit.x
    geo = geometry(R, p, plane, tm)
    ref = pointing(fit, R, sig, scale, known) if cov is not None else None
    ask = asked(fit, R, sig, plane, tm, known)             # the misfit gate: what one straight path asks of the cameras
    a, e, rr = _path_angles(p, R, plane, tm)
    cams = []
    for c in range(K):
        i = np.flatnonzero(R["camera"] == c)
        cams.append(dict(
            name=R["cameras"][c], readings=int(len(i)), lat=float(R["platform"][i[0], 0]), lon=float(R["platform"][i[0], 1]),
            alt_m=float(R["platform"][i[0], 2]), errors_from=sources[c], chi2_p_low=ps[c],
            sigma_deg=[float(sig[0] * math.sqrt(scale[i[0]])), float(sig[1] * math.sqrt(scale[n + i[0]]))],
            rms_az_deg=float(np.sqrt(np.mean(((a[i] - R["az"][i] + 180) % 360 - 180) ** 2))),
            rms_dep_deg=float(np.sqrt(np.mean((e[i] - R["dep"][i]) ** 2))),
            range_m=[float(rr[i].min()), float(rr[i].max())],
            pointing_asked_deg=None if ask is None else [float(x) for x in ask["asked_deg"][c]]))
    one = set(sources)
    new = dict(cameras=cams, reference="camera", pointing_known_deg=[float(known[0]), float(known[1])], **geo,
               errors_from=sources[0] if len(one) == 1 else "each camera's own",
               chi2_p_low=max(ps) if len(one) == 1 and all(x is not None for x in ps) else None,
               sigma_deg=[float(sig[0] * math.sqrt(np.mean(scale[:n]))), float(sig[1] * math.sqrt(np.mean(scale[n:])))],
               velocity_err_rays_m_s=out["velocity_err_m_s"], climb_err_rays_m_s=out["climb_err_m_s"],
               height_err_rays_m=out["height_err_m"], range_bound_rays=out["range_bound"], **misfit(ask, R, known))
    if ref is None:
        new.update(velocity_err_pointing_m_s=None, velocity_err_m_s=float("inf"), climb_err_m_s=float("inf"),
                   height_err_m=float("inf"), range_bound=float("inf"))
        return new
    C, S = ref["cov"], ref["pull"]
    part = np.sqrt(np.maximum(np.diag(C), 0.0))
    vref = float(math.hypot(part[3], part[4]))
    for c in range(K):
        cams[c].update(pull_m_s=[float(math.hypot(S[3, 2 * c + j], S[4, 2 * c + j])) for j in (0, 1)],
                       pull_climb_m_s=[float(abs(S[5, 2 * c + j])) for j in (0, 1)],
                       pointing_fitted_deg=None if ref["fitted_deg"] is None else [float(x) for x in ref["fitted_deg"][c]],
                       pointing_fitted_err_deg=None if ref["fitted_deg"] is None else [float(x) for x in ref["fitted_err_deg"][c]])
    err = np.sqrt(np.diag(cov))
    new.update(velocity_err_pointing_m_s=vref, velocity_err_m_s=float(math.hypot(out["velocity_err_m_s"], vref)),
               v_err_m_s=[float(math.hypot(err[3], part[3])), float(math.hypot(err[4], part[4]))],
               climb_err_m_s=float(math.hypot(out["climb_err_m_s"], part[5])),
               height_err_m=float(math.hypot(out["height_err_m"], part[2])),
               range_bound=range_bound(cov + C, p, R, plane, tm))
    return new


def shared(R, p, plane, tm):
    """The fields that name the cameras where they share one azimuth reference (`reference="shared"`): the fit and
    its errors are the aircraft route's."""
    cams = [dict(name=R["cameras"][c], readings=int(np.sum(R["camera"] == c))) for c in range(len(R["cameras"]))]
    geo = geometry(R, p, plane, tm)
    return dict(cameras=cams, reference="shared", places=geo["places"], baseline_m=geo["baseline_m"],
                los_cross_deg=geo["los_cross_deg"])


# ---- the words ------------------------------------------------------------------------------------
def _known(path):
    """How well each camera's pointing is taken as known, as a clause."""
    k = path.get("pointing_known_deg")
    if not k:
        return ""
    one = lambda x, angle: f"to {x:g} deg in {angle}" if math.isfinite(x) else f"not at all in {angle}"   # noqa: E731
    return f"each camera's pointing is taken as known {one(k[0], 'azimuth')} and {one(k[1], 'elevation')}"


def one_place(path):
    """Why rays from so nearly one place fix no path (the path gate's words where the rays came from cameras)."""
    from .drift import PATH_GATE, POSITION_ERR
    n = len(path["cameras"])
    if path.get("places") == 1:
        who = "one camera standing still" if n == 1 else f"{n} cameras standing at one place"
        return (f"all {path['readings']} lines of sight start from one place. {who.capitalize()} cannot range what "
                f"{'it sees' if n == 1 else 'they see'} (the line of sight turned {path['los_turn_deg']:.0f} deg)")
    return (f"the lines of sight start from places within {path['path_off_line_m']:.0f} m of one straight path at a "
            f"steady speed. That is within their own error ({PATH_GATE:g} x {POSITION_ERR:.0f} m), and lines of sight "
            f"from so nearly one place cannot range what they see")


def no_one_path(path):
    """The misfit gate's words: why these lines of sight are not one body on one straight path."""
    k = path["pointing_known_deg"][0 if path["misfit_angle"] == "azimuth" else 1]
    return (f"no single straight path fits these lines of sight. For one to pass through them all, the pointing of "
            f"{path['misfit_camera']} would have to be {abs(path['misfit_deg']):.1f} deg off in {path['misfit_angle']}. "
            f"That is {path['misfit']:.0f} times the {k:g} deg it is taken as known to, and more than {MISFIT:g} times "
            f"is refused. The cameras may be following different objects, or the object did not keep a straight path "
            f"at a steady speed")


def open_range(path):
    """The range gate's words where the rays came from cameras."""
    b = path["range_bound"]
    tail = f". {_known(path).capitalize()}" if path.get("reference") == "camera" else ""
    return (f"the lines of sight do not fix its range: it is known to no better than a factor of "
            f"{math.exp(min(b, 20.0)):.1f} (the bound on its logarithm at the fit, {min(b, 1e6):.2f}). The cameras stand "
            f"{path['baseline_m']:.0f} m apart at most, and their lines of sight cross at {path['los_cross_deg']:.1f} deg"
            f"{tail}")


def open_velocity(path, velocity_fix):
    """T2's words where the rays came from cameras and do not fix the velocity."""
    ev = path["velocity_err_m_s"]
    head = f"the lines of sight do not fix its velocity ({path['speed_m_s']:.1f} m/s, two errors {2 * ev:.1f})"
    ref, alone = path.get("velocity_err_pointing_m_s"), path.get("velocity_err_rays_m_s")
    if path.get("reference") == "camera" and ref is not None and alone is not None and math.isfinite(ev) \
            and 2 * alone <= velocity_fix:
        c = max(path["cameras"], key=lambda c: max(c.get("pull_m_s") or [0.0, 0.0]))
        return (f"{head}. {_known(path).capitalize()}. An error of one degree at {c['name']} alone moves the velocity "
                f"by {max(c['pull_m_s']):.1f} m/s. The cameras' lines of sight cross at {path['los_cross_deg']:.1f} deg")
    return (f"{head}. The cameras stand {path['baseline_m']:.0f} m apart at most, and their lines of sight cross at "
            f"{path['los_cross_deg']:.1f} deg")


def said(g):
    """The path's lines for a person, where the rays came from cameras."""
    from .drift import _one_in
    L = []
    cams = g["cameras"]
    above = f", {g['above_ground_m']:.0f} m above the ground" if g.get("above_ground_m") is not None else ""
    names = ", ".join(f"{c['name']} {c['readings']}" for c in cams)
    apart = (f"; standing {g['baseline_m']:.0f} m apart at most, their lines of sight crossing at "
             f"{g['los_cross_deg']:.1f} deg" if g.get("places", 1) > 1 else "; all from one place")
    at = f", mean time {g['time_utc']} UTC" if g.get("time_utc") else ""
    L.append(f"\nthe path from {g['readings']} lines of sight of {len(cams)} camera{'s' if len(cams) != 1 else ''} "
             f"({names}{apart}{at}): "
             f"{g['speed_m_s']:.2f} m/s toward {g['toward_deg']:.1f} deg (two errors {2 * g['velocity_err_m_s']:.2f}), "
             f"climb {g['climb_m_s']:+.2f} +- {g['climb_err_m_s']:.2f} m/s, {g['height_m']:.0f} m above the sea{above}; "
             f"reduced chi-square {g['chi2_dof']:.2f}, rms {g['rms_az_deg']:.2f} deg azimuth, {g['rms_dep_deg']:.2f} "
             f"elevation; {g['range_m'][0] / 1e3:.1f}-{g['range_m'][1] / 1e3:.1f} km from the cameras; the range's bound "
             f"{min(g['range_bound'], 1e6):.3f} (a factor of {math.exp(min(g['range_bound'], 20.0)):.2f}), an accelerating "
             f"path over a straight one p {g['model_p'] if g['model_p'] is None else round(g['model_p'], 3)}; "
             f"{g['boots']} of {g['boots_of']:,} resamples fitted")
    if g.get("reference") != "camera":
        return L
    L.append("\n| camera | lines of sight | their errors, azimuth and elevation (deg) | from | one degree of its azimuth moves "
             "the velocity by (m/s) | one degree of its elevation (m/s) |")
    L.append("|---|---|---|---|---|---|")
    for c in cams:
        pull = c.get("pull_m_s") or [float("nan")] * 2
        L.append(f"| {c['name']} | {c['readings']} | {c['sigma_deg'][0]:.3f}, {c['sigma_deg'][1]:.3f} | {c['errors_from']} | "
                 f"{pull[0]:.2f} | {pull[1]:.2f} |")
    tight = [c for c in cams if c["errors_from"] == "the rays' own scatter"]
    if tight:
        L.append(f"\n{'every camera' if len(tight) == len(cams) else ', '.join(c['name'] for c in tight)}'s lines of sight fit "
                 f"better than the errors given for them allow (1 fit in "
                 f"{_one_in(max(c['chi2_p_low'] or 0.0 for c in tight))} would, by chance). So their errors come from their own "
                 "scatter about the path")
    if g.get("velocity_err_pointing_m_s") is None:
        L.append(f"\n{_known(g).capitalize()} beforehand. The lines of sight cannot read it themselves, so the velocity "
                 "and the climb are open")
        return L
    L.append(f"\n{_known(g).capitalize()} beforehand. That is a constant error of its own in each angle, which all of "
             f"its lines of sight share. The errors above carry it. From the lines of sight's scatter alone, two errors of the velocity are "
             f"{2 * g['velocity_err_rays_m_s']:.2f} m/s and the climb's error is {g['climb_err_rays_m_s']:.2f} m/s")
    if cams[0].get("pointing_fitted_deg") is not None:
        L.append("the lines of sight themselves, held to that, read each camera's pointing as: " + "; ".join(
            f"{c['name']} {c['pointing_fitted_deg'][0]:+.2f} +- {c['pointing_fitted_err_deg'][0]:.2f} deg in azimuth, "
            f"{c['pointing_fitted_deg'][1]:+.2f} +- {c['pointing_fitted_err_deg'][1]:.2f} in elevation" for c in cams))
    if g.get("misfit") is not None:
        k = g["pointing_known_deg"][0 if g["misfit_angle"] == "azimuth" else 1]
        L.append(f"\nDo the lines of sight follow one straight path? For one to pass through them all, the camera asked "
                 f"the most, {g['misfit_camera']}, would have its pointing {abs(g['misfit_deg']):.2f} deg off in "
                 f"{g['misfit_angle']}: {g['misfit']:.1f} times the {k:g} deg it is taken as known to. "
                 + (f"That is within the {MISFIT:g} times allowed" if g["misfit_gate"] else
                    f"That is over the {MISFIT:g} times allowed, so no path is read from them"))
    return L
