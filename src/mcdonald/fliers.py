"""Planted fliers: how slow a flier would `mcdonald drift`'s wind test have caught, on this case's own geometry and winds?

T2 from the lines of sight (`drift.fit_track`, `drift.track_winds`, `drift.test_wind_track`) passes a body whose velocity
over the ground lies within a tolerance of the winds at its height, fails one a flier's margin beyond it, and cannot say
between. What that means for one case depends on its geometry, on its rays' errors and on how far its winds disagree,
and no rule of the test says it in metres a second. So bodies are planted: each at the place and height the case's rays
fixed, at the case's own climb, moving over the ground with the air plus an airspeed in one of several directions. Each
is seen from the real observer positions at the real times, with errors as the real fit has them, and goes through the
same fit and the same T2 the case got. What comes back is a table of outcomes by airspeed, and three numbers for a
person: how often a body drifting with the wind passes here (the test's power to recognise a drifter), the fastest
airspeed at which any planted body still passes, and the slowest from which every one fails.

The judgement calls (docs/method.md, section 67, argues each):

    the air     `air="path"`: the plants ride the fitted path's own velocity. That is the air where the object drifts
                (a control: AARO's lanterns, a cloud), and the winds' real miss of that air is then in every plant.
                `air="winds"`: each plant rides one of the winds T2 counted at the case's height, taken in turn, which
                needs no belief about the object. Left unsaid (None), the air is the path's where the case itself
                passed T2 -- the verdict then says it may have drifted, and the plants say what that pass excludes --
                and the winds' otherwise, since a body that did not pass has no claim to be the air. "path" is refused
                where the case failed T2. Riding each wind is the harsher world: where the winds disagree by more than
                the weakest of them blows, a body drifting exactly with any one of them cannot pass (T2's hold-still
                rule), though one between them can, as the lanterns do.
    the errors  each plant's rays carry the real rays' own misses about the fitted path, every miss kept at its reading
                (so a poorer camera, or a poorer stretch, stays where it was) with its sign drawn afresh, and enlarged by
                sqrt(2n / (2n - 6)) for the six parameters the fit took out of them (the wild bootstrap). Misses that
                run on from reading to reading are not kept, as the fit's own errors do not keep them.
    the draws   DRAWS sign draws for each airspeed and direction, and as many plants at zero airspeed as at any
                other, so each rate is over DIRECTIONS x DRAWS plants (32: a rate is known to 9 in 100 at the worst).
    the fit     each plant's fit resamples its readings as often as the case's did (`boots_of`), since the number of
                resamples is itself one of the fit's gates (`drift.BOOT_MIN`); about 6 s a plant at 2,000.
    the check   the case's own rays, planted again as they are, must come out as the case did (`case_again`).

The table and the sentence are made from rows of one form (`summary`), so the route from the ranges (`drift.fit_line`,
`drift.test_wind`) can be planted by a function of its own that returns such rows.
"""
import math

import numpy as np

from . import drift
from .drift import CANNOT, FAIL, PASS

SPEEDS = (0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0)   # m/s through the air; zero is the drifter itself
DIRECTIONS = 8          # directions of flight through the air, evenly round the compass from north
DRAWS = 4               # draws of the rays' errors for each airspeed and direction. A judgement: with 8 directions a rate
#                         is over 32 plants, known to 0.09 at the worst (a rate of a half) and to 0.03 where it is 1 in 32
BETWEEN, HOLD, FAR, OPEN, UNFIXED, NO_WIND = ("beyond the winds, not by a flier's margin", "holding still fits as well",
                                              "no wind near its height", "the velocity is not fixed",
                                              "the rays fix no path", "no wind at its height")
AIRS = ("path", "winds")
WHY = {BETWEEN: "the winds leave it beyond the test's tolerance, but not by a flier's margin",
       HOLD: "holding still over the ground fits as well as drifting",
       FAR: "no wind was read near its height",
       OPEN: "the lines of sight do not fix its velocity",
       UNFIXED: "the lines of sight fix no path",
       NO_WIND: "no wind bears on its height"}

_S = {}                 # what every plant of one case shares, in each worker


def winds_at(winds, height_m):
    """The winds at a height: `winds` is a list of wind dicts (label, w, counts, note; taken as they are at any height)
    or the keyword arguments of `drift.track_winds` (model, when, observed, own, ground_m), read at `height_m`."""
    return drift.track_winds(height_m, **winds) if isinstance(winds, dict) else list(winds)


def misses(R, path):
    """The real rays' misses about the fitted path, in the fit's own measure: (azimuth times the cosine of the
    depression, depression), deg, a pair for each reading."""
    plane, tm = drift.Plane(*path["map_origin"]), path["mean_time_s"]
    a, e, _ = drift._path_angles(np.asarray(path["params"], float), R, plane, tm)
    return ((R["az"] - a + 180) % 360 - 180) * np.cos(np.radians(R["dep"])), R["dep"] - e


def planted_rays(R, path, v, miss):
    """The rays `R` with their lines of sight turned onto a planted body: one at the fitted path's place and height at
    the readings' mean time, with the path's climb, moving over the ground at `v` (east, north, m/s), seen from the
    same observer positions at the same times, each line of sight off the body by `miss` (as `misses` gives them)."""
    plane, tm = drift.Plane(*path["map_origin"]), path["mean_time_s"]
    q = np.asarray(path["params"], float)[:6].copy()
    q[3:5] = v
    a, e, _ = drift._path_angles(q, R, plane, tm)
    dep = e + miss[1]
    return dict(R, az=(a + miss[0] / np.maximum(np.cos(np.radians(dep)), 1e-6)) % 360, dep=dep)


def because(t2):
    """Why T2 could not say, as one of six classes (None where it passed or failed)."""
    if t2["outcome"] != CANNOT:
        return None
    if "needs_m_s" not in t2:
        return NO_WIND if "winds" in t2 else OPEN if "speed_m_s" in t2 else UNFIXED
    if t2["wind_change_m_s"] > drift.VELOCITY_FIX:
        return FAR
    if t2["needs_m_s"][1] <= t2["tolerance_m_s"] and not t2["drift_beats_hold"]:
        return HOLD
    return BETWEEN


def _start(shared):
    _S.clear()
    _S.update(shared)


def _one(job):
    """One plant through the case's own fit and T2. `job`: k (its number, which with the seed gives its draws),
    airspeed, toward (deg; None at zero), air (the index of the air it rides), draw; or as_it_is, the case's own rays
    planted again with their misses as they are."""
    S = _S
    R, path, n = S["R"], S["path"], len(S["R"]["t"])
    if job.get("as_it_is"):
        rng = np.random.default_rng(S["seed"])              # as `drift.measure` starts the case's own fit
        v, miss = np.asarray(path["v_m_s"], float), S["miss"]
    else:
        rng = np.random.default_rng([S["seed"], 67, job["k"]])
        sign = rng.integers(0, 2, n) * 2.0 - 1.0            # a reading's two misses keep each other's company
        grow = math.sqrt(2 * n / max(1, 2 * n - 6))
        miss = (S["miss"][0] * sign * grow, S["miss"][1] * sign * grow)
        th = math.radians(job["toward"] or 0.0)
        v = np.asarray(S["airs"][job["air"]]["w"], float) + job["airspeed"] * np.array([math.sin(th), math.cos(th)])
    fit = drift.fit_track(planted_rays(R, path, v, miss), S["sig"], S["ground_m"], rng, nboot=S["nboot"],
                          az_ref_err=S["az_ref_err"])
    t2 = drift.test_wind_track(fit, winds_at(S["winds"], fit["height_m"]) if fit else [], readings=n)
    row = dict(airspeed_m_s=job.get("airspeed"), toward_deg=job.get("toward"),
               air=None if job.get("as_it_is") else S["airs"][job["air"]]["label"], draw=job.get("draw"),
               outcome=t2["outcome"], because=because(t2), needs_m_s=t2.get("needs_m_s"),
               tolerance_m_s=t2.get("tolerance_m_s"), ground_m_s=[round(float(v[0]), 2), round(float(v[1]), 2)])
    if fit:
        row.update(fitted_m_s=[round(fit["v_m_s"][0], 2), round(fit["v_m_s"][1], 2)],
                   velocity_err_m_s=round(fit["velocity_err_m_s"], 2) if math.isfinite(fit["velocity_err_m_s"]) else None,
                   height_m=round(fit["height_m"], 0))
    return row


def plan(speeds, directions, draws, airs, seed):
    """The plants: for each airspeed, `draws` draws in each of `directions` directions (at zero, where there is no
    direction, as many plants). Each rides one of the `airs` airs, taken in turn through shuffled rounds of them, so
    that every air is ridden as often as any other, to within one, at each airspeed."""
    rng = np.random.default_rng([seed, 67])
    per = directions * draws
    jobs = []
    for s in speeds:
        turn = np.concatenate([rng.permutation(airs) for _ in range(-(-per // airs))])[:per]
        for d in range(draws):
            for i in range(directions):
                jobs.append(dict(k=len(jobs), airspeed=float(s), toward=360.0 * i / directions if s > 0 else None,
                                 air=int(turn[d * directions + i]), draw=d))
    return jobs


def none(why, route="lines of sight"):
    """The result where nothing could be planted, with the reason."""
    return dict(route=route, plants=0, why=why, sentence=f"No bodies were planted: {why}.")


def plant_track(R, path, winds, sig=(0.3, 0.1), ground_m=None, az_ref_err=None, case_t2=None, speeds=SPEEDS,
                directions=DIRECTIONS, draws=DRAWS, air=None, seed=20261021, nboot=None, procs=None, progress=None):
    """Planted fliers on the route from the lines of sight. `R` the case's rays (`drift.rays`), `path` its fitted path
    (`drift.fit_track`), `winds` its winds (`winds_at`), `sig`, `ground_m`, `az_ref_err` as the case's fit had them,
    `case_t2` the case's own T2 where it is known. `speeds` m/s through the air (zero is added: the drifter itself),
    `directions` and `draws` as in the module's notes, `air` "path" or "winds" (None: the path's where `case_t2`
    passed, else the winds'), `nboot` the resamples of each plant's
    fit (None: as many as the case's). `procs` worker processes (0: in this process). The same seed gives the same
    result, however many processes. Returns the dict that goes into the drift JSON as `planted_fliers`."""
    from .progress import pooled
    if air not in AIRS + (None,):
        raise ValueError(f"air is one of {AIRS}, not {air!r}")
    if path is None:
        n = len(R["t"])
        return none(drift.too_few(n) if n < drift.READINGS_MIN else "there are no lines of sight to fit")
    why = drift.unfixed(path)
    if why:
        return none(f"the lines of sight fix no path to plant them on ({why})")
    counted = [w for w in winds_at(winds, path["height_m"]) if w["counts"]]
    if not counted:
        return none("no wind that bears on its height was given, and the wind test judges a body against the winds")
    chosen = "asked for"
    if air is None:
        passed = case_t2 is not None and case_t2["outcome"] == PASS
        air = "path" if passed else "winds"
        chosen = "the case passed the wind test" if passed else "the case did not pass the wind test"
    if air == "path":
        if case_t2 is not None and case_t2["outcome"] == FAIL:
            return none("the object itself failed the wind test, so its own motion is not the air's. Plant them in the "
                        "winds given instead (--plant-air winds)")
        airs = [dict(label="the path's own", w=[float(x) for x in path["v_m_s"]])]
    else:
        airs = [dict(label=w["label"], w=[float(x) for x in w["w"]]) for w in counted]
    speeds = sorted({0.0} | {abs(float(s)) for s in speeds})
    nboot = int(path["boots_of"] if nboot is None else nboot)
    shared = dict(R=R, path=path, miss=misses(R, path), winds=winds, sig=tuple(sig), ground_m=ground_m,
                  az_ref_err=az_ref_err, nboot=nboot, seed=seed, airs=airs)
    jobs = [dict(as_it_is=True)] + plan(speeds, directions, draws, len(airs), seed)
    rows = pooled(procs, _one, jobs, init=_start, initargs=(shared,), progress=progress,
                  what=f"planting {len(jobs) - 1} bodies, each through the fit and the wind test", pixels=1)
    again, rows = rows[0], rows[1:]
    again = dict(outcome=again["outcome"], needs_m_s=again["needs_m_s"], tolerance_m_s=again["tolerance_m_s"],
                 as_the_case=None if case_t2 is None else bool(again["outcome"] == case_t2["outcome"]
                                                              and again["needs_m_s"] == case_t2.get("needs_m_s")))
    out = dict(route="lines of sight", air=air, air_chosen_by=chosen, airs=[dict(a, w=[round(x, 2) for x in a["w"]]) for a in airs],
               speeds_m_s=speeds, directions_deg=[360.0 * i / directions for i in range(directions)], draws=draws,
               plants=len(rows), plants_each_speed=directions * draws, resamples=nboot, seed=seed, case_again=again)
    out.update(summary(rows, air=air, airs=len(airs)))
    out["runs"] = rows
    return out


def summary(rows, air="path", airs=1):
    """The table and the numbers for a person, from the plants' rows (each with airspeed_m_s, outcome, because):
    `table`, a row for each airspeed with how many plants passed, could not be judged and failed, and why those that
    could not; `drifter`, the plants at zero airspeed, whose pass rate is the test's power to recognise a drifter
    here; `passes_up_to_m_s`, the fastest airspeed above zero at which any plant passed (None: none did);
    `fails_from_m_s`, the slowest airspeed from which every plant failed, at it and at every faster one tried (None:
    not even the fastest); `cannot_say_m_s`, the slowest and the fastest airspeed above zero at which any plant could not
    be judged (None: none); and `sentence`. The route is not in it: rows from the ranges' route sum up the same way."""
    table = []
    for s in sorted({r["airspeed_m_s"] for r in rows}):
        at = [r for r in rows if r["airspeed_m_s"] == s]
        oc = [r["outcome"] for r in at]
        why = {}
        for r in at:
            if r["because"]:
                why[r["because"]] = why.get(r["because"], 0) + 1
        table.append(dict(airspeed_m_s=s, plants=len(at), passes=oc.count(PASS), cannot_say=oc.count(CANNOT),
                          fails=oc.count(FAIL), cannot_say_because=why))
    zero = next((t for t in table if t["airspeed_m_s"] == 0), None)
    fly = [t for t in table if t["airspeed_m_s"] > 0]
    up_to = max((t["airspeed_m_s"] for t in fly if t["passes"]), default=None)
    fails_from = None
    for t in reversed(fly):
        if t["fails"] < t["plants"]:
            break
        fails_from = t["airspeed_m_s"]
    open_at = [t["airspeed_m_s"] for t in fly if t["cannot_say"]]
    out = dict(table=table, drifter=None if zero is None else dict(
        plants=zero["plants"], passes=zero["passes"], pass_rate=round(zero["passes"] / zero["plants"], 3),
        cannot_say_because=zero["cannot_say_because"]), passes_up_to_m_s=up_to, fails_from_m_s=fails_from,
        cannot_say_m_s=[min(open_at), max(open_at)] if open_at else None)
    out["sentence"] = sentence(out, air, airs)
    return out


def sentence(s, air="path", airs=1):
    """The summary in words a reader outside the field follows: which air the bodies were planted in, what would have
    failed, what is not told from a drifter, and how often a drifter passes here."""
    fly = [t for t in s["table"] if t["airspeed_m_s"] > 0]
    if air == "path":
        out = ["Bodies were planted in air that moved as the object did."]
    elif airs > 1:
        out = ["Bodies were planted in air that moved as one of the winds given says."]
    else:
        out = ["Bodies were planted in air that moved as the wind given says."]
    if not fly:
        out.append("None of them flew through the air.")
    elif s["fails_from_m_s"] is not None:
        out.append(f"On this geometry and these winds, a body flying {s['fails_from_m_s']:g} m/s or more through the air "
                   "would have failed the wind test whichever way it flew.")
    else:
        out.append(f"On this geometry and these winds, no planted speed, up to {fly[-1]['airspeed_m_s']:g} m/s through the "
                   "air, failed the wind test whichever way the body flew.")
    if s["cannot_say_m_s"] is not None:
        lo, hi = s["cannot_say_m_s"]
        whole = all(t["cannot_say"] in (0, t["plants"]) for t in fly)
        out.append(("At " + (f"{lo:g}" if lo == hi else f"{lo:g} to {hi:g}") + " m/s the wind test could not say"
                    + ("." if whole else " for some or all of the planted bodies.")))
    z = s["drifter"]
    if fly and s["passes_up_to_m_s"] is not None:
        out.append(f"At {s['passes_up_to_m_s']:g} m/s or less it is not told from a drifter: at least one body planted that "
                   "slow passed.")
    elif fly and z and z["passes"]:
        out.append(f"No planted flier passed as a drifter, down to the slowest tried, {fly[0]['airspeed_m_s']:g} m/s.")
    if z and z["passes"]:
        out.append(f"A planted body that drifted with the air passed {z['passes']} times in {z['plants']}.")
    elif z:
        top = max(z["cannot_say_because"], key=z["cannot_say_because"].get) if z["cannot_say_because"] else None
        out.append(f"No planted body passed, not even one that drifted with the air ({z['plants']} tried)"
                   + (f": {WHY[top]}." if top else "."))
    return " ".join(out)


def said(f):
    """The printed lines for `drift.said`, from the result of `plant_track`."""
    if not f.get("plants"):
        return [f"\nplanted fliers: {f['sentence']}"]
    if f["air"] == "path":
        rides = "with the air as the object's own fitted path gives it"
    elif len(f["airs"]) > 1:
        rides = f"with one of the {len(f['airs'])} winds counted, taken in turn"
    else:
        rides = "with the one wind counted"
    L = [f"\nplanted fliers: {f['plants']} bodies at the fitted place and height. Each moved {rides}, plus a speed through "
         f"the air in {len(f['directions_deg'])} directions ({f['draws']} draws each). Each was seen along the real lines of "
         f"sight with the real fit's errors, their signs drawn afresh, and went through the same fit ({f['resamples']:,} "
         "resamples) and the same T2.",
         "", "| airspeed, m/s | planted | passes | cannot say | fails |", "|---|---|---|---|---|"]
    for t in f["table"]:
        L.append(f"| {t['airspeed_m_s']:g} | {t['plants']} | {t['passes']} | {t['cannot_say']} | {t['fails']} |")
    c = f["case_again"]
    if c["as_the_case"] is False:
        L.append(f"\nWARNING: the case's own rays, planted again as they are, came out differently from the case (T2 "
                 f"{c['outcome']}, needing {c['needs_m_s']} m/s): the plants are not to be trusted")
    L.append(f"\n{f['sentence']}")
    return L
