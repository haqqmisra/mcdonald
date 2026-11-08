"""The control population a report weighs its beat against: what known things gave on the same test.

One so far, the labelled infrared set (Svanström et al. 2021: 365 clips of thermal infrared video, 30 frames a second, a
box on every frame): its 432 tracks of 60 frames or more -- 125 birds, 82 airplanes, 168 drones, 57 helicopters -- each
measured by `flicker` as `mcdonald run` measures an object, under the stage's rule and the paper's (session 18's controls
harness on 0.4.3, `tools/controls/`; the data folder's `controls/svanstrom_tracks.csv`). `controls_beat.csv`, beside this
file, is that table cut to what the report reads (`make`): each track's clip and class, what it offers the test (its
frames, frame rate and contrast), and under each rule the call, the beat's frequency and amplitude, whether it comes
back, whether the scene's shake sits at it, and the amplitude a beat needs to be found on it.

What it gives (`weigh`): how many times as common an answer of the checklist's beat row was on the birds as on the rest --
a likelihood ratio -- with an interval from resampling clips, since the tracks of one clip are not independent (bird
clips and the rest resampled apart, BOOT times, a fixed seed). An answer that fewer than MIN_TRACKS tracks gave has no
ratio (NO POWER); one whose interval holds 1 carries no weight. The ratio is read under the rule the case was measured
by and at the report's BIRD_FLOOR as it stands, so a change to the floor changes the weights with it.

What it does not give. The set is one camera's thermal video at 30 frames a second, mostly 300-frame tracks of birds 1-5
widths of a pixel to tens: a clip unlike it (another frame rate, a short track, a flock) is outside the population the
weights were measured on, and the report's grade says so (`report.Case.grade`). The weights are of the beat alone: the
stage's tests of the beat -- the whole track, the windows, the continuum, the background -- read one curve and pass
together far more often than apart (1 of 288 answered non-birds passes all five against 0.0034 % if they were
independent; phi 0.7-0.9 between them; the diagnostic survey, 2026-11-07), so they are one reading and weigh once.
"""
import csv
import math
from functools import lru_cache
from pathlib import Path

TABLE = Path(__file__).with_name("controls_beat.csv")
SET = "432 labelled tracks of thermal infrared video"   # what the weights were measured on, in the report's words
OTHERS = "aircraft, drones and helicopters"
MIN_TRACKS = 10      # an answer fewer tracks gave has no ratio: the harness's STRATUM_MIN, a judgement call (a rate near a half on
                     # under ten has an exact interval over 60 points wide); on 0.4.3 it leaves "in one stretch" (5 tracks) and
                     # "the camera may make it" (1) without one
BOOT = 2000          # resamples of clips for each interval
SEED = 7
RULES = ("stage", "paper")
COLUMNS = ("clip", "object", "cls", "distance", "frames_measured", "fps", "contrast_gl")
PER_RULE = ("call", "hz", "amplitude", "comes_back", "shaken", "needs")
WINGBEAT_HZ = (2.0, 25.0)   # report.WINGBEAT_HZ, here so that the table is read without the report

# the checklist's beat row, answer by answer (`report.Case.checklist` sets each row's `kind`)
KINDS = {
    "named": "a beat at a wingbeat's rate that comes back, strong enough to name a bird",
    "faint": "a beat at a wingbeat's rate that comes back, too faint to name a bird",
    "once": "a beat at a wingbeat's rate in one stretch only",
    "none": "no rhythm of its own, on a track that could have shown a bird's",
    "deaf": "no rhythm of its own, on a track too noisy to show a bird's",
    "band": "a rhythm of its own outside a wingbeat's rate",
    "refused": "a test that could not decide",
    "shaken": "a beat the camera's shake may make",
}


def make(src, out=TABLE):
    """`controls_beat.csv` from the harness's whole table (the data folder's `controls/svanstrom_tracks.csv`): the columns
    the report reads, the shake as 0/1. Run after the harness measures the set again: `python3 -m mcdonald.controls SRC`."""
    with open(src, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    cols = list(COLUMNS) + [f"{r}_{c}" for r in RULES for c in PER_RULE]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            got = [r[c] for c in COLUMNS]
            for rule in RULES:
                got += [r[f"{rule}_call"], r[f"{rule}_hz"], r[f"{rule}_amplitude"], r[f"{rule}_comes_back"],
                        "1" if r[f"{rule}_shaken_px"] not in ("", None) else "0", r[f"{rule}_needs"]]
            w.writerow(got)
    return out


@lru_cache(maxsize=1)
def tracks():
    """The table's rows, the numbers as numbers (None where empty)."""
    num = lambda x: float(x) if x not in ("", None) else None
    with open(TABLE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("frames_measured", "fps", "contrast_gl") + tuple(f"{rule}_{c}" for rule in RULES for c in ("hz", "amplitude", "needs")):
            r[k] = num(r[k])
        for rule in RULES:
            r[f"{rule}_comes_back"] = r[f"{rule}_comes_back"] == "True"
            r[f"{rule}_shaken"] = r[f"{rule}_shaken"] == "1"
        r["bird"] = r["cls"] == "BIRD"
    return rows


def kind(r, rule, floor):
    """The beat row's answer for one track of the set, as `report.Case.checklist` gives it for an object measured so (a
    KINDS key): the harness's call -- `bird` (its own beat at 2-25 Hz that comes back), `once`, `other`, `none`, `refused`
    -- with the amplitude against the floor, the shake, and the track's power at the floor."""
    c, a, need = r[f"{rule}_call"], r[f"{rule}_amplitude"], r[f"{rule}_needs"]
    if c == "refused":
        return "refused"
    if c in ("bird", "once") and r[f"{rule}_shaken"]:
        return "shaken"
    if c == "bird":
        return "named" if a is not None and a >= floor else "faint"
    if c == "once":
        return "once"
    if c == "other":
        return "band"
    return "deaf" if need is not None and need > floor else "none"


def _ratio(bird, others):
    kb, nb = sum(k for k, _ in bird), sum(n for _, n in bird)
    ko, no = sum(k for k, _ in others), sum(n for _, n in others)
    pb, po = kb / nb, ko / no
    return (pb / po if po else math.inf if pb else float("nan")), kb, nb, ko, no


@lru_cache(maxsize=64)
def weigh(what, rule="stage", floor=None):
    """The weight of one answer of the beat row (a KINDS key) on the labelled set, under `rule` at `floor` (the report's
    BIRD_FLOOR when None): dict(kind, lr -- how many times as common on birds as on the rest --, lo, hi (95 %, clips
    resampled), birds=[k, n], others=[k, n], weight: "for" a bird (lo > 1), "against" (hi < 1), "none" (the interval holds
    1), or "no power" (fewer than MIN_TRACKS tracks gave it), and said: the weight in the report's words)."""
    if floor is None:
        from .report import BIRD_FLOOR as floor
    rule = rule if rule in RULES else "stage"
    by = {}
    for r in tracks():
        by.setdefault((r["bird"], r["clip"]), [0, 0])
        by[(r["bird"], r["clip"])][0] += kind(r, rule, floor) == what
        by[(r["bird"], r["clip"])][1] += 1
    bird = [v for (b, _), v in sorted(by.items()) if b]
    others = [v for (b, _), v in sorted(by.items()) if not b]
    lr, kb, nb, ko, no = _ratio(bird, others)
    # the clips resampled at once (numpy, a fixed seed): a third of a second a kind in pure Python was a cost on every
    # process that writes a report, the window's tests among them
    import numpy as np
    rng = np.random.default_rng(SEED)
    B, O = np.array(bird, float), np.array(others, float)
    ib, io = rng.integers(0, len(B), (BOOT, len(B))), rng.integers(0, len(O), (BOOT, len(O)))
    pb = B[ib, 0].sum(1) / B[ib, 1].sum(1)
    po = O[io, 0].sum(1) / O[io, 1].sum(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        got = np.where(po > 0, pb / np.where(po > 0, po, 1.0), np.where(pb > 0, np.inf, np.nan))
    got = np.sort(got[~np.isnan(got)])
    lo, hi = ((float(got[int(0.025 * len(got))]), float(got[max(0, int(0.975 * len(got)) - 1)])) if len(got) else (None, None))
    weight = ("no power" if kb + ko < MIN_TRACKS else "for" if lo is not None and lo > 1 else
              "against" if hi is not None and hi < 1 else "none")
    d = dict(kind=what, rule=rule, floor=floor, lr=lr, lo=lo, hi=hi, birds=[kb, nb], others=[ko, no], weight=weight)
    d["said"] = said(d)
    return d


def _times(x):
    return f"{x:.0f}" if x >= 10 else f"{x:.1f}"


def said(w):
    """A weight in the report's words: how much more common the answer was on birds, or on the rest, with its least
    at 95 %; or why it carries none."""
    n = w["birds"][0] + w["others"][0]
    on = f"On {SET}"
    if w["weight"] == "no power":
        return f"{on}, {n} track{'s' if n != 1 else ''} gave this answer: too few to weigh it, so it carries no weight."
    if w["weight"] == "for":
        upper = "" if w["hi"] is None or math.isinf(w["hi"]) else f" and at most {_times(w['hi'])}"
        return (f"{on}, it was about {_times(w['lr'])} times as common on birds as on {OTHERS} "
                f"(at least {_times(w['lo'])} times{upper}, at 95 % confidence).")
    if w["weight"] == "against":
        if not w["lr"] or not w["hi"]:                # no bird gave it: a ratio of nothing, and no least to say
            return f"{on}, no bird gave this answer, and {w['others'][0]} of the {w['others'][1]} others did."
        top = "" if not w["lo"] else f" and at most {_times(1 / w['lo'])}"
        return (f"{on}, it was about {_times(1 / w['lr'])} times as common on {OTHERS} as on birds "
                f"(at least {_times(1 / w['hi'])} times{top}, at 95 % confidence).")
    return (f"{on}, {w['birds'][0]} of {w['birds'][1]} birds and {w['others'][0]} of {w['others'][1]} others gave this answer: "
            "not enough to say it favours either, so it carries no weight.")


def population(rule="stage", floor=None):
    """For the discriminant plot: [(is a bird, the beat's frequency, its amplitude, kind)] of every track the stage measured
    a beat on (a refusal before any peak has none)."""
    if floor is None:
        from .report import BIRD_FLOOR as floor
    return [(r["bird"], r[f"{rule}_hz"], r[f"{rule}_amplitude"], kind(r, rule, floor)) for r in tracks()
            if r[f"{rule}_hz"] is not None and r[f"{rule}_amplitude"] is not None]


OWN = ("named", "faint", "once", "band", "shaken")     # the kinds whose peak is a rhythm of the track's own


def screen(hz, amplitude, rule="stage", floor=None):
    """The object's beat against the labelled tracks that had a rhythm of their own at a wingbeat's rate (the discriminant
    plot's band, `figures.beat_controls`): how many birds and how many of the rest beat at least as strongly, and the
    words that rest on it (the ideas bank's S20) -- "consistent with" the birds where at least one in twenty of theirs
    reaches it (a judgement call), the rest "not screened out" where any of theirs does, and "screened out" only where
    none of the others the test could judge (refusals left out) does, with the exact one-sided bound that leaves (none in
    288: under 1.04 %). dict(birds=[k, n], others=[k, n], said); None outside a wingbeat's rate."""
    if floor is None:
        from .report import BIRD_FLOOR as floor
    if amplitude is None or not (WINGBEAT_HZ[0] <= hz <= WINGBEAT_HZ[1]):
        return None
    own = [(r["bird"], r[f"{rule}_amplitude"]) for r in tracks() if kind(r, rule, floor) in OWN and r[f"{rule}_amplitude"] is not None
           and r[f"{rule}_hz"] is not None and WINGBEAT_HZ[0] <= r[f"{rule}_hz"] <= WINGBEAT_HZ[1]]
    kb = sum(1 for b, a in own if b and a >= amplitude)
    nb = sum(1 for b, _ in own if b)
    ko = sum(1 for b, a in own if not b and a >= amplitude)
    no = sum(1 for b, _ in own if not b)
    n_all = sum(1 for r in tracks() if not r["bird"] and kind(r, rule, floor) != "refused")   # the others the test could judge
    said = (f"Of the labelled tracks with a rhythm of their own at a wingbeat's rate, {kb} of {nb} birds and {ko} of {no} "
            f"aircraft, drones and helicopters beat at least this strongly. ")
    birds = "consistent with the birds" if nb and kb / nb >= 0.05 else "stronger than nearly every bird's"
    if ko:
        said += f"So its beat is {birds}, and the others are not screened out by it."
    else:
        bound = 1 - 0.05 ** (1 / n_all)              # none of all the others: the exact one-sided 95 % bound
        said += (f"So its beat is {birds}. None of the {n_all} others the test could judge beat so strongly, so on this "
                 f"test they are screened out, though up to {100 * bound:.1f} in 100 might be, at 95 % confidence.")
    return dict(birds=[kb, nb], others=[ko, no], said=said)


def inside(fps=None, frames=None, flock=False):
    """Where a clip lies outside the population the weights were measured on: [why, in the report's words]; empty where
    nothing said is outside it. The set is 30 frames a second throughout; its tracks are 60-329 frames, 279 of the 307
    non-birds 300 or more, and under 150 frames it holds 17 non-bird tracks, too few to say a false-alarm rate there (an
    exact bound of 16 %; the diagnostic survey's DXC5); it holds no flocks."""
    out = []
    if fps is not None and abs(fps - 30.0) > 1.0:
        out.append(f"the video runs at {fps:.0f} frames a second, and every labelled track at 30")
    if frames is not None and frames < 150:
        out.append(f"its track is {frames:.0f} frames long, and the labelled tracks are mostly 300: under 150 frames there are too few "
                   "of them to say how often they are wrong")
    if flock:
        out.append("it is one of a flock, and the labelled tracks are of single objects")
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        sys.exit("python3 -m mcdonald.controls SVANSTROM_TRACKS_CSV   (writes controls_beat.csv beside this file)")
    print(make(sys.argv[1]))
