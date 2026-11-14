"""What known kinds of flying object do, each number with its source, and a track held against them (method section 61).

Two readings of a track that need no range and no field of view, and one table they are both read against:

- **Speed in body lengths a second** (IDEAS.md Av11; `body_lengths`). The rate in the picture over the object's length in
  the picture is its speed in its own lengths, free of the angular scale k and of the range R, because both scale alike
  with range. It is a **lower bound** on the true figure, v / L with L the body's length along its travel: the picture
  shows the speed across the line of sight, v sin(theta), and the body's length along its travel foreshortened by the same
  sin(theta), and whatever else of the body shows (wings, a rotor) can only make the extent larger. So the ratio is at most
  v / L, and equals it where the body's own length is what shows longest. It holds on a camera that stood still, for an
  object whose whole body shows and is wider than the picture's blur; where the camera moved it is NO POWER (the rate
  over the size is then the camera's speed over the object's length: `stages.platform_of`), and for an object no wider
  than a point it is a speed in blur widths and no class is read from it.
- **A turn as a load factor** (IDEAS.md Av10; `load_curve`). A level turn at the rate omega and the true airspeed V takes a
  load factor n = sqrt(1 + (omega V / g)^2): the lift over the weight. The track gives omega (the rate its heading turns,
  an angle in the picture, so it needs no k and no R) and not V, so the reading is a curve, and for each class's limit
  load the fastest it could have flown the turn, V = g sqrt(n^2 - 1) / omega. A class whose least flying speed is above
  that could not have flown it.

The table is `class_envelopes.csv` beside this file: one row a member of a class (a species, an aircraft type) or a rule
(a limit load, a defining speed), with the source of its size, of its speed and of its limit load written beside them.
Neither reading names what an object is. Each says which classes a number does not exclude, and "not excluded" is weak
evidence: small fast bodies of every kind share the high end of the scale.
"""
import csv
import functools
import math
from pathlib import Path

TABLE = Path(__file__).with_name("class_envelopes.csv")
G = 9.80665                 # m/s², standard gravity
NUMBERS = ("length_m", "span_m", "speed_min_m_s", "speed_max_m_s", "load_limit_g")
SOURCED = (("size_source", ("length_m", "span_m")), ("speed_source", ("speed_min_m_s", "speed_max_m_s")),
           ("load_source", ("load_limit_g",)))        # each number's column of sources: a row with the number has the source
WIND_CLASS = "wind"         # the table's row for a strong jet stream: the most a tail wind is taken to add to a class's speed
# A turn read from a short arc: the picture's heading turns at cos i / (sin²φ + cos²i cos²φ) times the turn's own rate, i
# the tilt of the turn's plane from facing the camera and φ where on its circle the arc lies. With the plane's normal
# isotropic and φ uniform the turn's own rate is 0.439 to 10.0 times the picture's nine times in ten (median 1.14; a 4000
# x 4000 grid, recomputed by tests/test_unknowns.py), the same geometry as `projective.TILT_OWN`.
TILT_RATE = (0.439, 10.0)


@functools.lru_cache(maxsize=4)
def rows(path=None):
    """The table's rows as dicts, its numbers as floats (None where a cell is empty). Lines that start with # are the
    file's own notes."""
    out = []
    with open(path or TABLE, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(line for line in f if not line.startswith("#")):
            row = {k: (v or "").strip() for k, v in r.items()}
            for k in NUMBERS:
                row[k] = float(row[k]) if row.get(k) else None
            out.append(row)
    return tuple(out)


def unsourced(path=None):
    """[(class, member, column)]: every number of the table with no source beside it. Empty is the rule: a class table
    is worth its citations (the tests hold it to this)."""
    bad = []
    for r in rows(path):
        for src, cols in SOURCED:
            bad += [(r["class"], r["member"], c) for c in cols if r[c] is not None and not r.get(src)]
        if not any(r[c] is not None for c in NUMBERS):
            bad.append((r["class"], r["member"], "no number"))
    return bad


# The least speed a fixed-wing type can fly at, from its approach reference speed: 14 CFR 97.3 defines the approach
# category "based on a speed of VREF, if specified, or if VREF is not specified, 1.3 Vso at the maximum certificated
# landing weight", so the stall speed is the approach speed over 1.3 (a transport's VREF is 1.23 times its reference stall
# speed by 14 CFR 25.125, so 1.3 errs low, the cautious side: a class is said not to fly a turn only under this).
STALL_OVER_APPROACH = 1.0 / 1.3


def least_speed(r):
    """A row's least flying speed, m/s: its `speed_min_m_s`, or the stall speed where that is an approach speed. None
    where the row gives none."""
    v = r["speed_min_m_s"]
    return None if v is None else v * (STALL_OVER_APPROACH if r.get("speed_min_is") == "approach" else 1.0)


@functools.lru_cache(maxsize=4)
def classes(path=None):
    """{class: dict(members; per_s (lo, hi): its speed in body lengths a second, lo the least over its members of the
    least speed over the length (0 where no row gives a least speed), hi the most of the greatest speed over the length;
    speed_m_s (lo, hi); length_m (lo, hi); load_limit_g and load_source, the largest limit a row of the class gives;
    bodies: [(member, length, greatest speed)], the rows with both)}, in the table's order, the wind's row left out
    (`strongest_wind`). A row counts only for what it has a number for: a type whose greatest speed was not read from its
    source still gives the class its length and its least speed."""
    out = {}
    for r in rows(path):
        if r["class"] == WIND_CLASS:
            continue
        c = out.setdefault(r["class"], dict(members=[], bodies=[], load_limit_g=None, load_source=None, _lo=[], _v=[], _L=[]))
        c["members"].append(r["member"])
        L, least, top = r["length_m"], least_speed(r), r["speed_max_m_s"]
        if L and top is not None:
            c["bodies"].append((r["member"], L, top))
        if L:
            c["_L"].append(L)
        if L and least is not None:
            c["_lo"].append(least / L)
        c["_v"] += [v for v in (least, top) if v is not None]
        if r["load_limit_g"] is not None and (c["load_limit_g"] is None or r["load_limit_g"] > c["load_limit_g"]):
            c["load_limit_g"], c["load_source"], c["load_member"] = r["load_limit_g"], r["load_source"], r["member"]
    for c in out.values():
        b, lo, v, Ls = c["bodies"], c.pop("_lo"), c.pop("_v"), c.pop("_L")
        c["per_s"] = (min(lo) if lo else 0.0, max(top / L for _, L, top in b)) if b else None
        c["speed_m_s"] = (min(v), max(v)) if b else None
        c["length_m"] = (min(Ls), max(Ls)) if Ls else None
    return out


def strongest_wind(path=None):
    """(m/s, source): the strongest wind the table gives, the most a tail wind can add to a class's speed over the ground.
    (None, None) where the table has no such row."""
    w = [(r["speed_max_m_s"], r["speed_source"]) for r in rows(path) if r["class"] == WIND_CLASS and r["speed_max_m_s"]]
    return max(w) if w else (None, None)


# ---- Av11: speed in body lengths a second -----------------------------------------------------------------------------
def against_classes(per_s, path=None):
    """A speed of at least `per_s` body lengths a second (across the line of sight, relative to a camera that stood still)
    held against each class's own range: dict(within: the classes whose range holds it; faster: those that fly faster in
    their own lengths, which a body moving partly along the line of sight still fits; with_wind: [(class, m/s)] those it is
    above in still air, with the least tail wind that would carry one of their members to it; outside: those it is above
    even with the strongest wind the table gives; wind_max_m_s). A lower bound excludes only from above: nothing is
    excluded for being slow."""
    wind, _ = strongest_wind(path)
    out = dict(within=[], faster=[], with_wind=[], outside=[], wind_max_m_s=wind)
    for name, c in classes(path).items():
        if not c["per_s"]:
            continue
        lo, hi = c["per_s"]
        if per_s <= hi:
            out["within" if per_s >= lo else "faster"].append(name)
            continue
        need = min(per_s * L - top for _, L, top in c["bodies"])         # the least tail wind that brings a member to it
        if wind is not None and need <= wind:
            out["with_wind"].append((name, float(need)))
        else:
            out["outside"].append(name)
    return out


def body_lengths(v_px_per_s, size_px, size_from=None, resolved=None, platform=None, path=None):
    """The object's speed in its own lengths a second, as a bound, held against the class table (Av11).

    `v_px_per_s` is the track's rate in the picture, `size_px` the object's length there and `size_from` where that came
    from; `resolved` is `forensics.point_blur`'s answer (True: wider than the picture's blur; False: a point; None: not
    measured); `platform` is `stages.platform_of`'s dict (moving True, None or False). Returns dict(power, why (where
    there is none), per_s, bound ("at least"), unit ("body lengths" or "blur widths"), size_px, size_from, resolved,
    platform, classes (`against_classes`' dict, or None: none is read from a blur), conditions: [what the bound rests on]).

    NO POWER: with no size; where the camera moved (the rate over the size then holds the camera's own speed over the
    object's length); and where the picture behind held still on screen, which a camera following the object draws too."""
    out = dict(power=False, why=None, per_s=None, bound="at least", unit="body lengths", size_px=size_px, size_from=size_from,
               resolved=resolved, platform=platform, classes=None, conditions=[])
    if not size_px or v_px_per_s is None:
        out["why"] = "needs the object's length in the picture (--size-px), or a track to take its rate from"
        return out
    out["per_s"] = float(v_px_per_s) / float(size_px)
    moving = (platform or {}).get("moving", False)
    if moving is not False:
        out["why"] = ((platform.get("why") or "the camera moved") + ": the rate over the size is not the object's own speed in "
                      "its lengths" + ("" if moving else " unless the camera stood still"))
        return out
    out["power"] = True
    out["conditions"] = ["the camera stood still", "the speed is across the line of sight, relative to the camera: the true "
                         "speed can only be more", "all of the object shows"]
    if resolved is False:
        out.update(unit="blur widths")
        out["conditions"].append("the object is no wider than a point here, so the length is the blur's: no class is read")
        return out
    if resolved is None:
        out["conditions"].append("the length is the object's own, not the blur's (not measured here)")
    out["classes"] = against_classes(out["per_s"], path)
    return out


def _n(v):
    """A count of body lengths as the report writes it: two figures under 10, whole numbers above."""
    return f"{v:.2g}" if v < 10 else f"{v:,.0f}"


def _listed(names):
    names = list(names)
    return ", ".join(names[:-1]) + (" and " if len(names) > 1 else "") + names[-1] if names else ""


def lengths_said(b):
    """`body_lengths` in the trade's words, for the stage's result line and the summary's row: (value or None, how)."""
    if not b:
        return None, "not read"
    if not b["power"]:
        return None, "NO POWER: " + b["why"] + (f" ({_n(b['per_s'])} a second as the picture has it)" if b.get("per_s") else "")
    head = f"at least {_n(b['per_s'])} {b['unit']} a second"
    how = (f"the rate over its length in the picture ({b['size_px']:g} px, {b['size_from'] or 'given'}): no k, R or field of view. "
           "A lower bound: the picture shows the speed across the line of sight, and a body's length along its travel is "
           "foreshortened by the same factor, so the ratio is at most the true speed over the true length; it holds if "
           + "; ".join(b["conditions"]))
    c = b.get("classes")
    if not c:
        return head, how
    parts = []
    if c["within"]:
        parts.append("in the range of " + _listed(c["within"]))
    if c["faster"]:
        parts.append("below the range of " + _listed(c["faster"]) + " (not excluded: a body moving partly along the line of "
                     "sight reads slow)")
    if c["with_wind"]:
        parts.append("above the still-air range of " + _listed(f"{n} (needs a tail wind of {w:.0f} m/s or more)" for n, w in c["with_wind"]))
    if c["outside"]:
        parts.append("outside the range of " + _listed(c["outside"])
                     + (f" even with a strong jet stream behind it ({c['wind_max_m_s']:.0f} m/s)" if c.get("wind_max_m_s") else ""))
    return head, how + ". Against the class table (envelopes.py, each row sourced): " + "; ".join(parts)


def lengths_plain(b):
    """`body_lengths` as the report's sentences (sciencespeak): [] where there is no reading."""
    if not b or not b.get("power"):
        return []
    blur = b["unit"] == "blur widths"
    S = [f"The object crossed the picture at {_n(b['per_s'])} times its own "
         + ("blur width" if blur else "length") + " each second.",
         "That ratio needs no range and no field of view, because distance scales the speed and the size alike."]
    if blur:
        return S + ["The object is no wider than a point of light is drawn here, so the true body is smaller than the blur.",
                    "Its speed in body lengths (how many of its own lengths it covers each second) is then higher than "
                    "this, if all of the object shows.",
                    "No kind of object is read from a blur."]
    S += [f"So its speed is at least {_n(b['per_s'])} body lengths a second, if the camera stood still and all of the object shows.",
          "It is a lower limit because the picture shows only the motion across the line of sight."]
    c = b.get("classes") or {}
    if c.get("within"):
        S.append(f"That is in the range of {_listed(c['within'])}.")
    if c.get("faster"):
        S.append(f"It is below the range of {_listed(c['faster'])}.")
        S.append("That does not exclude them, because an object moving partly toward or away from the camera reads slow.")
    if c.get("with_wind"):
        S.append("It is above the still-air range of " + _listed(f"{n} ({w:.0f} m/s)" for n, w in c["with_wind"]) + ".")
        S.append("The speed in brackets is the tail wind each would need to reach it.")
    if c.get("outside"):
        S.append(f"It is outside the range of {_listed(c['outside'])}, even with a strong jet stream as a tail wind.")
    if c:
        S.append("These ranges come from published sizes and speeds, and sharing a range does not identify the object.")
    return S


# ---- Av10: a turn as a load-factor curve ------------------------------------------------------------------------------
def load_factor(omega_rad_per_s, v_m_s):
    """The load factor of a level turn at the rate omega and the true airspeed V: sqrt(1 + (omega V / g)^2)."""
    return math.sqrt(1.0 + (float(omega_rad_per_s) * float(v_m_s) / G) ** 2)


def speed_at(omega_rad_per_s, n):
    """The fastest a body held to the load factor n can fly a level turn at the rate omega: g sqrt(n^2 - 1) / omega (m/s).
    None for n at most 1 (no turn at all is flown at 1 g) or no turn rate."""
    if not omega_rad_per_s or n is None or n <= 1.0:
        return None
    return G * math.sqrt(n * n - 1.0) / abs(float(omega_rad_per_s))


def turn_rate(turn, span_s):
    """The rate the track's heading turned, rad/s, from `projective.turn`'s dict and the track's length in seconds:
    dict(how, omega_rad_per_s, lo, hi (the turn's own rate, nine times in ten), heading_deg) or dict(why) where there is
    none to read.

    A loop read whole (`how` "loop"): the ellipse's rate, the same in every view, with its error under the track's own
    covariance (lo and hi 1.645 of it either side). A bend (`how` "bend"): the heading swept by the arc through the
    sagitta s over the chord L, 4 atan(2 s / L), over the time, and the tilt's band on it (TILT_RATE), since a short arc
    does not fix the turn's plane. None where the track did not bend, and none where it swings about more than a bend
    does with no loop claimed (PR077's object 1, 705 degrees of back and forth): a sagitta is a formula for a small bend,
    and on a path that doubles back it measures nothing."""
    if not turn:
        return dict(why="no turn was read from the track")
    e = turn.get("ellipse") if turn.get("how") == "ellipse" else None
    if e:
        w, err = e["omega_rad_per_s"], e.get("omega_err_rad_per_s")
        return dict(how="loop", omega_rad_per_s=w, omega_err_rad_per_s=err, heading_deg=e["arc_deg"],
                    lo=max(w - 1.645 * err, 0.0) if err is not None else w, hi=w + 1.645 * err if err is not None else w)
    if turn.get("swings"):
        return dict(why="the path swings from side to side more than a bend does and no loop is claimed, so it has no one "
                        "turn rate to read")
    if not turn.get("bent"):
        return dict(why="the path does not bend beyond its own scatter, so there is no turn to read a load from")
    if not span_s or span_s <= 0 or not turn.get("length_px"):
        return dict(why="the track's length in time is not known")
    swept = 4.0 * math.atan(2.0 * turn["sagitta_px"] / turn["length_px"])
    w = swept / float(span_s)
    return dict(how="bend", omega_rad_per_s=w, lo=TILT_RATE[0] * w, hi=TILT_RATE[1] * w, heading_deg=math.degrees(swept))


def load_curve(turn, span_s, platform=None, lengths=None, path=None):
    """A turn as a load-factor curve (Av10): the turn rate from the track, the speed unknown, against each class's limit.

    `turn` is `projective.turn`'s dict, `span_s` the track's length in time, `platform` `stages.platform_of`'s dict, and
    `lengths` a `body_lengths` reading where there is one. Returns dict(power, why, how, omega_rad_per_s, lo, hi,
    heading_deg, platform, limits: [dict(cls, load_limit_g, source, v_max_m_s (the fastest that class could have flown the
    turn at the rate read), v_max_most_m_s (at the least rate the band allows: the most the speed could be), flies_m_s
    (the class's own least and greatest speeds), binds (the limit is reached inside the speeds the class flies at), could
    (False where even v_max_most is under the class's least speed: it could not have flown the turn), and with `lengths`
    length_max_m (the longest body that covers that many of its lengths a second and stays within the limit, v_max_most /
    per_s), lengths_m (the class's own) and too_long (every member is longer: said beside the numbers and left to the
    reader, since the length in the picture carries no error here))], conditions).

    NO POWER where the camera moved or may have turned (a camera's own turn bends a track as the object's does), and where
    the track gives no turn rate (`turn_rate`)."""
    out = dict(power=False, why=None, platform=platform, limits=[], conditions=[])
    moving = (platform or {}).get("moving", False)
    rate = turn_rate(turn, span_s)
    out.update({k: v for k, v in rate.items() if k != "why"})
    if "why" in rate:
        out["why"] = rate["why"]
        return out
    if moving is not False:
        out["why"] = ("the camera moved, and its own turn bends the track as the object's does" if moving else
                      "the picture behind the object held still on screen, which a camera following the object draws too: "
                      "the camera may have turned, and its turn bends the track as the object's does")
        return out
    per_s = lengths["per_s"] if lengths and lengths.get("power") and lengths.get("classes") is not None else None
    for name, c in classes(path).items():
        n = c["load_limit_g"]
        v = speed_at(rate["omega_rad_per_s"], n)
        if v is None:
            continue
        most = speed_at(rate["lo"], n) if rate["lo"] > 0 else None        # the slowest turn the band allows: the fastest flight
        flies = c["speed_m_s"]
        row = dict(cls=name, load_limit_g=n, source=c["load_source"], v_max_m_s=v, v_max_most_m_s=most,
                   flies_m_s=list(flies) if flies else None,
                   binds=bool(most is not None and flies and most < flies[1]),
                   could=not (most is not None and flies and flies[0] > most))
        if per_s and most is not None:                                    # it covers at least per_s of its lengths a second
            row["length_max_m"] = most / per_s
            row["lengths_m"] = list(c["length_m"]) if c["length_m"] else None
            row["too_long"] = bool(row["binds"] and c["length_m"] and c["length_m"][0] > row["length_max_m"])   # where the limit, not the class's own top speed, is what holds it
        out["limits"].append(row)
    out["power"] = True
    out["conditions"] = ["the camera stood still and did not turn", "the turn was level (a pull up or a dive adds or takes up "
                         "to 1 g)", "the speed is the true airspeed"]
    out["conditions"].append("the turn rate is the loop's own, the same at any tilt" if rate["how"] == "loop" else
                             f"the turn's plane is not known from a short arc: its own rate is {TILT_RATE[0]:g} to "
                             f"{TILT_RATE[1]:g} times the picture's nine times in ten")
    return out


def _mps(v):
    return "no limit" if v is None else f"{v:.2g} m/s" if v < 10 else f"{v:,.0f} m/s"


def load_said(c):
    """`load_curve` in the trade's words: (value or None, how)."""
    if not c:
        return None, "not read"
    if not c["power"]:
        return None, "NO POWER: " + c["why"]
    w = c["omega_rad_per_s"]

    def one(r):
        most = r["v_max_most_m_s"] if r.get("v_max_most_m_s") is not None else r["v_max_m_s"]
        fl = r.get("flies_m_s")
        out = f"{r['cls']} ({r['load_limit_g']:g} g): {_mps(r['v_max_m_s'])}" + (f", at most {_mps(most)}" if most != r["v_max_m_s"] else "")
        if not r["could"]:
            out += f" -- under the {fl[0]:.0f} m/s they fly from: could not have flown it"
        elif not r.get("binds") and fl:
            out += f" (past the {fl[1]:.0f} m/s they reach: no limit on them)"
        if r.get("too_long"):
            out += (f"; at its lengths a second a body within that limit is no longer than {r['length_max_m']:.3g} m, and they "
                    f"are {r['lengths_m'][0]:.3g} m or more")
        return out
    return (f"n(V) = √(1 + ({w:.3g} V / g)²)",        # Ω here: ω is the angular rate across the view in the same table
            f"the track's heading turned {c['heading_deg']:.0f}° at {w:.3g} rad/s ({'a loop read whole' if c['how'] == 'loop' else 'a bend'}; "
            f"the turn's own rate {c['lo']:.3g} to {c['hi']:.3g} rad/s): a level turn at that rate and the airspeed V takes "
            "a load factor n = √(1 + (ΩV/g)²), Ω the rate its heading turns (not ω, the angular rate across the view), so a "
            "body held to a limit could have flown it no faster than g√(n² − 1)/Ω -- " + "; ".join(one(r) for r in c["limits"]) + ". It holds if " + "; ".join(c["conditions"]))


def load_plain(c):
    """`load_curve` as the report's sentences (sciencespeak): [] where there is no reading."""
    if not c or not c.get("power") or not c.get("limits"):
        return []
    w, bend = c["omega_rad_per_s"], c["how"] == "bend"
    most = lambda r: r["v_max_most_m_s"] if r.get("v_max_most_m_s") is not None else r["v_max_m_s"]   # the cautious figure
    S = [f"The object's heading turned through {c['heading_deg']:.0f}° at about {math.degrees(w):.2g}° a second.",
         "In a turn a flying body carries more than its weight, and the load factor is how many times its weight it carries.",
         "The load grows with speed, and the speed is not known.",
         "So the turn gives each kind of object a speed limit, from the greatest load it is known to bear."]
    for r in [r for r in c["limits"] if r["could"] and r.get("binds")][:4]:
        S.append(f"{r['cls'].capitalize()} bear at most {r['load_limit_g']:g} times their weight, so one could have flown "
                 f"this turn only below {_mps(most(r))}.")
    for r in (r for r in c["limits"] if not r["could"]):
        S.append(f"{r['cls'].capitalize()} bear at most {r['load_limit_g']:g} times their weight, which holds this turn "
                 f"to {_mps(most(r))}.")
        S.append("They cannot fly that slowly, so the turn was not theirs.")
    free = [r["cls"] for r in c["limits"] if r["could"] and not r.get("binds")]
    if free:
        S.append(f"The turn is gentle enough for {_listed(free)} at any speed they fly.")
    for r in [r for r in c["limits"] if r.get("too_long") and r["could"]][:3]:
        S.append(f"At its body lengths a second, one of the {r['cls']} within that limit would be under {r['length_max_m']:.2g} m "
                 f"long, and they are {r['lengths_m'][0]:.2g} m or more.")
    S.append("This holds for a level turn seen by a camera that stood still.")
    if bend:
        S.append("A short arc does not show how the turn was tilted, so each speed is the most that tilt allows.")
    return S
