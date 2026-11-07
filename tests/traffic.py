"""The traffic light for checks on drawn data (E20; the economics survey of 2026-10-28, §5.5; docs/method.md section 42).

A check that counts an event over random draws -- a band's misses, a test's false alarms, a planted signal found --
and holds the count to one fixed threshold flaps: a change that only reorders the draws, another machine's rounding,
or a stated rate that is right moves the count across the line by chance. A bank's supervisor reads a value-at-risk
model's exceptions the same way (the Basel Committee 1996): the count against its binomial distribution at the stated
rate, green while that many or fewer come 95 % of the time from a model that is right, yellow past that, red past
99.99 %. The suites do the same: a check states its rate and its draws, a count in the green passes, one in the yellow
prints a WARN line and does not fail, and only a red fails.

    import traffic
    traffic.rate(check, "a clean track has a jump named about one time in a hundred", named, 40, 0.01)

`check` is the suite's own (it prints PASS or FAIL and keeps the count); the yellow is printed here and kept in
`WARNS`. The draws must be independent -- whole tracks or clips, each its own draw: frames within one track are not
(their errors run together, and a binomial zone over them is far too narrow).

A two-sided check (a coverage that may be too wide as well as too narrow) holds the count of events that should not
happen to the zone above and the count of those that should to the same zone below. The zones are Basel's own: a count
is yellow from the first count k whose probability of k or fewer reaches 95 % (250 days at 1 %: green 0-4, yellow 5-9,
red 10 and more), and a count at or under the expected one is always green (with few draws at a small rate, none at
all is already likelier than 95 %)."""
from scipy import stats

ZONES = (0.95, 0.9999)   # the cumulative binomial probability at which a count turns yellow, then red (Basel 1996)
WARNS = []


def zone(k, n, p, zones=ZONES):
    """The zone of k events in n independent draws at the stated rate p, counted from above (too many): ("green",
    "yellow" or "red", P(X <= k) under the stated rate)."""
    c = float(stats.binom.cdf(k, n, p))
    if k <= n * p or c < zones[0]:
        return "green", c
    return ("yellow" if c < zones[1] else "red"), c


def light(k, n, p, two_sided=False, zones=ZONES):
    """The traffic light of k events in n draws at the stated rate p: zone() from above, and with two_sided from below
    too (too few: the n - k other draws held to the rate 1 - p the same way), the worse of the two. Returns (light,
    the cumulative probability on the side that set it, "above" or "below")."""
    up = zone(k, n, p, zones)
    if not two_sided:
        return up[0], up[1], "above"
    down = zone(n - k, n, 1.0 - p, zones)
    order = ("green", "yellow", "red")
    return (up[0], up[1], "above") if order.index(up[0]) >= order.index(down[0]) else (down[0], down[1], "below")


def bounds(n, p, zones=ZONES):
    """(the last green count, the last yellow count) from above for n draws at the rate p: the zone's edges, for words."""
    k = 0
    while zone(k, n, p, zones)[0] == "green" and k < n:
        k += 1
    g = k - 1 if zone(k, n, p, zones)[0] != "green" else n
    while k <= n and zone(k, n, p, zones)[0] == "yellow":
        k += 1
    return g, k - 1


def rate(check, label, k, n, p, detail="", two_sided=False, zones=ZONES):
    """A check of a rate on drawn data by its traffic light: `check(ok, label, detail)` is the suite's own (green
    passes, red fails); a yellow prints WARN and passes. Returns the light."""
    got, c, side = light(k, n, p, two_sided, zones)
    g, y = bounds(n, p, zones)
    said = (f"{k} of {n} at a stated {100 * p:.3g} %: {got} (green to {g}, yellow to {y}"
            + (", and as far the other way" if two_sided else "") + f"; P(X {'<=' if side == 'above' else '>='} {k}) = {c:.4f})")
    detail = f"{detail}  [{said}]" if detail else f"[{said}]"
    if got == "yellow":
        print(f"  WARN  {label}  {detail}")
        WARNS.append(label)
        return got
    check(got == "green", label, detail)
    return got
