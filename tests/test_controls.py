"""Does the flicker stage still hear the controls as it did? One of everything, from saved curves (ROADMAP.md 0.5.0).

The controls harness. Each control is what `flicker.judge` was given when the control was measured from its video -- the
curves of the object, of its background apertures and of its lights, its size and track, the fields measured before the
judging and the planted dots of the encoding control (`tools/controls/save_controls.py`) -- kept in the reference-data
folder's `controls/curves/` and judged again here under both beat rules, with no video: minutes, not hours. What a control
is, and what it must give, is `tests/golden/controls.csv`:

- **birds keep their beats** -- the Galileo flyers (60 frames a second, a camera that does not move), PR135's flock, and
  birds of the labelled infrared set (Svanström et al. 2021), a distant one among them, the size bin nearest PURSUE's;
- **non-birds get none** -- a drone, an airplane and a helicopter of the labelled set (a distant one of each), the
  WA9ONY-5 balloon, PR23, PR055 and PR071: the report never says "Beats like a bird" of them;
- **the strobe helicopters keep their trains** (V_HELICOPTER_054 and _030, item 13);
- **the false alarms of record stay as they are, with their causes** -- DRONE_059, named at 10.00 Hz, a third of the
  frame rate: a third of its frames are held (a 20-a-second source in a 30-a-second file?) and the held-pictures test
  (M3) misses the cadence by a hair, so the holds' own rhythm is heard as a beat; and HELICOPTER_043 (a fence line and
  poles passing behind it): the non-birds the report names a bird on the whole set. A change that removes one is an
  improvement to be checked and written down, not a silent pass. Since the floor went to 7 % (method section 43) a third:
  HELICOPTER_024, a 3.53-Hz beat at 7.8 % that the capped point disc hears;
- **NO POWER stays NO POWER** where the stage could not decide.

Each is held, rule by rule, to the outcome the manifest records (its `<rule>_beats`, `_named`, `_hz`, `_train` columns,
written by `save_controls.py --record` from the saved curves): a change to the judging that moves any of them fails here,
and the manifest's diff, made again with `--record`, is the record of what moved.

Beside each control the exact bound its outcome gives (the biology survey's B28): one silent negative control bounds the
false-alarm rate only under 97.5 %, four under 60 % (Clopper-Pearson, 95 %). So the sample is a regression -- it holds the
stage to what it did -- and the rates come from the whole set: `controls/svanstrom_tracks.csv`, the table of all 432
labelled tracks (`tools/controls/run_set.py`, `summarise.py`), whose rates of record are held here (RECORD) with their exact
and by-clip intervals. Every sampled track's replay must also give its own row of that table.

It prints, too, which of test_golden's checks and which exercise answers are controls -- an answer from outside the tool
-- and which are regressions that follow the tool (B28), and the exotica list (the SETI survey's T9): one of everything the
harness should hold, what is in hand and what is missing.

    python3 tests/test_controls.py          # needs $MCDONALD_DATA (or data/mcdonald beside the repository)
    python3 tests/test_controls.py --only flyer1,pr23     # those saved controls alone, and the checks that need none

Without the saved curves it says SKIP for each and still checks what needs no data (the bounds, the lists).
"""
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "controls"))
sys.path.insert(0, str(ROOT / "tools" / "sweep"))

import reference_data  # noqa: E402

FAIL, SKIP, PASS = [], [], []
RULES = ("stage", "paper")


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    (PASS if cond else FAIL).append(label)
    return cond


ONLY = None          # `--only NAME,NAME`: the saved controls judged in this run (the rest skipped, and said); default all


def manifest(every=False):
    """The manifest's rows -- those `--only` names, unless `every`."""
    with open(reference_data.GOLDEN / "controls.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(l for l in f if not l.startswith("#")))
    return rows if every or ONLY is None else [r for r in rows if r["name"] in ONLY]


# The labelled set's rates of record: the whole-set run of 2026-11-07 (mcdonald 0.4.3 + session 18's tools, every one of
# the 432 tracks under both rules; tools/controls/run_set.py, summarise.py), k of n tracks. "bird" is the run of
# 2026-10-19's reading (the object's own beat at 2-25 Hz that comes back); "named" is what the report says today ("Beats
# like a bird": the same at BIRD_FLOOR of the brightness or more, the camera's shake not at the beat) -- at BIRD_FLOOR 0.07
# since the floor's merge (method section 43), the two tracks with a beat between 7 and 8 % measured again so that their
# shake was read. Held to the table in the reference-data folder: a regression on the table. The rate is the set's.
RECORD = {
    "stage": {
        "BIRD: bird": (31, 125), "BIRD: named": (30, 125), "non-bird: bird": (18, 307), "non-bird: named": (3, 307),
        "AIRPLANE: bird": (7, 82), "DRONE: bird": (3, 168), "HELICOPTER: bird": (8, 57), "AIRPLANE: named": (0, 82),
        "DRONE: named": (1, 168), "HELICOPTER: named": (2, 57), "BIRD DISTANT: named": (5, 57), "non-bird DISTANT: named": (1, 100),
        "BIRD: answered": (110, 125), "non-bird: answered": (288, 307),
    },
    "paper": {
        "BIRD: bird": (30, 125), "BIRD: named": (27, 125), "non-bird: bird": (25, 307), "non-bird: named": (2, 307),
        "AIRPLANE: bird": (11, 82), "DRONE: bird": (7, 168), "HELICOPTER: bird": (7, 57), "AIRPLANE: named": (0, 82),
        "DRONE: named": (0, 168), "HELICOPTER: named": (2, 57), "BIRD DISTANT: named": (6, 57), "non-bird DISTANT: named": (0, 100),
        "BIRD: answered": (108, 125), "non-bird: answered": (287, 307),
    },
}


def bound(k, n):
    """Clopper-Pearson's 95 % interval for k of n (summarise.cp)."""
    from summarise import cp
    return cp(k, n)


def test_bounds():
    """B28's arithmetic, which needs no data: four silent negative controls bound the rate only under 60 %; the labelled
    set's 11 of 286 non-bird clips called (2026-10-19) gives 1.9-6.8 %."""
    print("\nthe exact bound a control's outcome gives (B28)")
    lo, hi = bound(0, 4)
    check(lo == 0.0 and abs(hi - 0.6024) < 5e-4, "no false alarm in four negative controls bounds the rate only under 60 %",
          f"0 of 4: under {100 * hi:.1f} %")
    lo, hi = bound(0, 1)
    check(abs(hi - 0.975) < 1e-9, "one silent negative control bounds it under 97.5 %", f"{100 * hi:.1f} %")
    lo, hi = bound(11, 286)
    check(abs(lo - 0.0194) < 5e-4 and abs(hi - 0.0678) < 5e-4,
          "the labelled set's 11 of 286 non-bird clips called (2026-10-19) gives 1.9-6.8 %", f"{100 * lo:.2f}-{100 * hi:.2f} %")
    from summarise import upper
    check(abs(upper(0, 286) - 0.01042) < 5e-5 and upper(0, 300) > 0.0099,
          "none in 286 bounds a false-alarm rate only under 1.04 % (exact, one-sided 95 %): no count on about 300 tracks "
          "shows \"under 1 %\"", f"{100 * upper(0, 286):.2f} %")
    from summarise import kappa
    po, pe, k = kappa(list("aabbbbbbbb"), list("abbbbbbbbb"))
    check(abs(po - 0.9) < 1e-9 and abs(k - (0.9 - pe) / (1 - pe)) < 1e-9 and k < po,
          "agreement corrected for chance (Cohen's kappa) is lower than raw agreement on a rare call", f"raw {po:.2f}, kappa {k:.2f}")


EXPECT = {      # kind -> (what is held, a function of the outcome judged again)
    "bird": ("it keeps its own beat, at a wingbeat's rate (whether the report names a bird is the record's)",
             lambda o: o["beats"] is True and o["hz"] is not None and WINGBEAT[0] <= o["hz"] <= WINGBEAT[1]),
    "flock": ("every member beats, each its own", lambda o: o["beats"] is True and len(o["strong"]) >= 2),
    "non-bird": ("the report never says \"Beats like a bird\"", lambda o: not o["named"]),
    "strobe": ("its light flashes in a train", lambda o: o["train"]),
    "false alarm": ("a false alarm of the whole set, held as the record has it", lambda o: True),
    "no power": ("NO POWER: no beat decided", lambda o: o["beats"] is None),
    "miss": ("measured, and no bird named (a bird the test does not hear: gliding, most likely)",
             lambda o: o["beats"] is not None and not o["named"]),
}
WINGBEAT = (2.0, 25.0)      # report.WINGBEAT_HZ
WHAT = ("beats", "named", "hz", "amplitude", "train")      # the manifest's record of each, rule by rule (save_controls.RECORD)


def as_recorded(o):
    """An outcome in the manifest's words (save_controls.said)."""
    from save_controls import said
    return {k: said(o, k) for k in WHAT}


def agrees(o, r, rule):
    """The outcome judged again is the manifest's record: the call, the train, the beat's hertz to a thousandth."""
    got = as_recorded(o)
    if any(got[k] != r.get(f"{rule}_{k}", "") for k in ("beats", "named", "train")):
        return False
    a, b = got["hz"], r.get(f"{rule}_hz", "")
    return (a == "") == (b == "") and (a == "" or abs(float(a) - float(b)) < 1e-3)


_BOXES = {}


def boxes():
    """{clip_object: the label box's median width, px} from the labelled set's track index (empty without it)."""
    if not _BOXES:
        path = reference_data.root() / "svanstrom2021" / "tracks" / "index.tsv"
        if path.exists():
            with open(path, newline="", encoding="utf-8") as f:
                _BOXES.update({f"{r['clip']}_{r['object']}": float(r["w_med"]) for r in csv.DictReader(f, delimiter="\t")})
    return _BOXES


def where(r, saved):
    """The strata a control sits in (summarise.STRATA): its track's length, its size (the label's box where it has one, else
    twice the stage's extent, else a point), its contrast and its frame rate -- the controls at the easy end of the range
    (the Galileo flyers: 60 a second, long tracks) say little of the test's power on PURSUE's short, faint, 30-a-second
    tracks (spectrum bias)."""
    from summarise import offers, stratum
    name = saved["fields"]["tracks"][0]
    o = offers(saved, name)
    box = boxes().get(r.get("track") or "")
    size = box if box else (2 * o["extent_px"] if o["extent_px"] else None)
    said_size = (f"{size:.0f} px" + (" (its box)" if box else " (twice the stage's extent)")) if size else "a point (no extent read)"
    return (f"offers: {o['frames_measured']} frames ({stratum('frames', o['frames_measured'])}), {said_size} "
            f"({stratum('size', size) if size else 'under 14 px wide'}), contrast {o['contrast_gl']} grey levels "
            f"({stratum('contrast', o['contrast_gl'])}), {o['fps']:g} a second"
            + (f", the set's {r['distance'].lower()} bin" if r.get("distance") else "")
            + ("" if stratum("frame rate", o["fps"]) == "30 a second" else ": no stratum of the labelled set, so no rate of its own"))


_JUDGED = {}


def judged(name, saved, rule):
    """The control's outcome judged again from its saved curves under `rule` (once a run: two tests read it)."""
    from run_set import outcome, replay
    if (name, rule) not in _JUDGED:
        _JUDGED[name, rule] = outcome(replay(saved, rule).fields)
    return _JUDGED[name, rule]


def outcome_said(o):
    return (f"beats {o['beats']}, " + (f"{o['hz']:.2f} Hz {100 * o['amplitude']:.1f} %"
                                        + ("" if o.get("comes_back", True) else " in one stretch") + ", " if o.get("hz") else "")
            + f"named {o['named']}" + (", a train" if o["train"] else ""))


def test_saved_controls():
    """Each control judged again from its saved curves, under both rules: what its kind holds, and the outcome the
    manifest records (`save_controls.py --record`) -- the call, the train and the hertz to a thousandth."""
    print("\nthe controls, judged again from their saved curves (no video)")
    from run_set import read_gz
    folder = reference_data.controls() / "curves"
    kept = {"bird": [0, 0], "negative": [0, 0]}
    for r in manifest():
        path = folder / f"{r['name']}.json.gz"
        if not path.exists():
            print(f"  SKIP  {r['name']}: {path} is not on this computer")
            SKIP.append(r["name"])
            continue
        saved = read_gz(path)
        what, held = EXPECT[r["kind"]]
        for rule in RULES:
            o = judged(r["name"], saved, rule)
            ok, same = held(o), agrees(o, r, rule)
            check(ok and same, f"{r['name']} ({r['what']}), {rule}'s rule: {what}",
                  outcome_said(o) + ("" if same else "; the record: " + ", ".join(f"{k} {r.get(f'{rule}_{k}')}" for k in WHAT)))
            if rule == "stage" and r["outside"] == "yes":
                if r["kind"] in ("bird", "flock"):
                    kept["bird"][0] += bool(ok)
                    kept["bird"][1] += 1
                elif r["kind"] == "non-bird":
                    kept["negative"][0] += bool(o["named"])
                    kept["negative"][1] += 1
        print("        " + where(r, saved))
        if r["outside"] != "yes":
            print("        what it is, nobody outside the tool says: a regression, which bounds no rate")
        elif r["kind"] == "non-bird":
            print(f"        alone, a silent negative control bounds the false-alarm rate only under {100 * bound(0, 1)[1]:.1f} % (exact, 95 %)")
        elif r["kind"] in ("bird", "flock"):
            print(f"        alone, a bird kept bounds the share of birds the test hears only over {100 * bound(1, 1)[0]:.1f} % (exact, 95 %)")
        elif r["kind"] == "false alarm":
            print("        chosen because it is a false alarm: its rate is the whole set's (below)")
    k, n = kept["negative"]
    if n:
        print(f"\n  the sample's {n} negative controls whose label is the set's (or a filmed launch's), {k} named a bird: the "
              f"false-alarm rate under {100 * bound(k, n)[1]:.0f} % (exact, 95 %) -- a regression; the rate is the whole set's")
    k, n = kept["bird"]
    if n:
        print(f"  its {n} birds labelled from outside the tool, {k} kept: the bird test hears at least "
              f"{100 * bound(k, n)[0]:.0f} % of such (exact, 95 %) -- chosen because they beat, so no rate at all")


def test_sample_against_the_table():
    """Each sampled track of the labelled set gives, judged again, its own row of the whole-set table: the sample and the
    rates of record are one measurement."""
    print("\nthe labelled set's sample against the whole-set table")
    from run_set import read_gz
    table = reference_data.controls() / "svanstrom_tracks.csv"
    if not table.exists():
        print(f"  SKIP  {table} is not on this computer")
        SKIP.append("the whole-set table")
        return
    rows = {f"{r['clip']}_{r['object']}": r for r in csv.DictReader(open(table, newline="", encoding="utf-8"))}
    for r in manifest():
        if r["source"] != "svanstrom":
            continue
        path = reference_data.controls() / "curves" / f"{r['name']}.json.gz"
        if not path.exists():
            continue
        saved, t = read_gz(path), rows.get(r["track"])
        got = {rule: judged(r["name"], saved, rule) for rule in RULES}
        check(t is not None and all(str(int(got[rule]["named"])) == str(t[f"{rule}_named"]) for rule in RULES)
              and all((got[rule]["hz"] is None and t[f"{rule}_hz"] == "") or
                      (got[rule]["hz"] is not None and t[f"{rule}_hz"] != "" and abs(got[rule]["hz"] - float(t[f"{rule}_hz"])) < 1e-3)
                      for rule in RULES),
              f"{r['track']}: the table's row", "" if t is None else
              ", ".join(f"{rule} named {t[f'{rule}_named']} {t[f'{rule}_call']}" for rule in RULES))


def test_rates_of_record():
    """The labelled set's whole-set rates, from the table, against RECORD: each with its exact interval over tracks and
    its interval resampling clips (a clip's tracks are not independent, E10)."""
    print("\nthe rates of record: the labelled set's whole-set table (432 tracks)")
    from summarise import rates
    table = reference_data.controls() / "svanstrom_tracks.csv"
    if not table.exists():
        print(f"  SKIP  {table} is not on this computer")
        SKIP.append("the rates of record")
        return
    rows = list(csv.DictReader(open(table, newline="", encoding="utf-8")))
    R = rates(rows)
    check(R["tracks"] == R["of"] == 432, "every labelled track measured under both rules", f"{R['tracks']} of {R['of']}")
    for rule in RULES:
        for key, want in RECORD[rule].items():
            q = R[rule][key]
            check(want is not None and (q["k"], q["n"]) == tuple(want),
                  f"{rule}'s rule, {key}: {q['k']} of {q['n']} ({100 * q['k'] / q['n']:.1f} %)",
                  f"exact {100 * q['cp'][0]:.1f}-{100 * q['cp'][1]:.1f} %, by clip {100 * q['clips'][0]:.1f}-{100 * q['clips'][1]:.1f} %"
                  + ("" if want is None or (q["k"], q["n"]) == tuple(want) else f"; the record says {want[0]} of {want[1]}"))
        print(f"        among the tracks already called (bird or once), the beat's amplitude separates the birds' calls from the "
              f"false ones: AUC {R[rule]['amplitude AUC']:.2f} (over the calls only); over every track with an amplitude "
              f"{R[rule]['amplitude AUC, measured']:.2f}, and among those with no beat at all {R[rule]['amplitude AUC, no beat']:.2f}")
        print(f"        coverage, the share answered (not NO POWER), by class: " + ", ".join(
            f"{c.lower()}s {R[rule][f'{c}: answered']['k']} of {R[rule][f'{c}: answered']['n']}"
            for c in ("BIRD", "AIRPLANE", "DRONE", "HELICOPTER")))
        rr = R[rule]["refusal ratio"]
        if rr["lr"] is not None:
            print(f"        a refusal is {rr['lr']:.1f} times as likely on a bird as on anything else (by clip "
                  f"{rr['clips'][0]:.1f}-{rr['clips'][1]:.1f})" + (": the interval holds 1, so NO POWER is not shown to "
                  "carry class information" if rr["clips"][0] <= 1 <= rr["clips"][1] else ""))
        for key in ("non-bird: named", "AIRPLANE: named", "DRONE: named", "HELICOPTER: named"):
            q = R[rule][key]
            print(f"        false alarms, {key}: {q['k']} of {q['n']}, {100 * q['share']:.1f} %, under {100 * q['upper']:.1f} % "
                  "(exact, one-sided 95 %)")
        S = R[rule]["strata"]
        few = [k for k, q in S.items() if q["too_few"] and q["n"]]
        print(f"        by what a clip offers ({rule}'s rule; birds named, non-birds named):")
        for key, q in S.items():
            if not q["n"]:
                continue
            print(f"          {key}: {q['k']} of {q['n']}" + (" -- too few to state a rate" if q["too_few"] else
                                                                f", {100 * q['share']:.1f} % ({100 * q['cp'][0]:.1f}-{100 * q['cp'][1]:.1f})"))
        from summarise import STRATA, stratum
        for dim, (col, bins) in STRATA.items():
            n = sum(S[f"{dim}: {lab}: {who}"]["n"] for lab in [b[0] for b in bins] + ["not read"] for who in ("birds", "non-birds"))
            check(n == R["tracks"], f"{rule}'s rule: the strata of {dim} hold every track once", f"{n} of {R['tracks']}; "
                  f"{sum(1 for k in few if k.startswith(dim + ':'))} cells too few to state a rate")
    a = R["agreement"]
    print(f"        the two rules on one set of tracks (a bird call or not): raw agreement {100 * a['raw']:.1f} %, kappa "
          f"{a['kappa']:.2f}, positive agreement {100 * a['positive']:.1f} %")


# test_golden's checks (and --full's, and the exercise pages'): a control has its answer from outside the tool -- a label,
# a data bar, a laser, a header, a launch filmed, a documented hand measurement; a regression holds the tool to what it
# said before, and finds a change, not an error (the biology survey's B28 and X7). Every test_ function of test_golden.py
# is here (test_golden_classified holds it so).
GOLDEN_KINDS = {
    "test_pr113_two_clicks": ("control", "the Technical Note's two documented clicks and its hand-measured 142 px/frame"),
    "test_pr144_window": ("regression", "the tool's own numbers of 2026-09-19"),
    "test_pr144_full": ("regression", "the tool's published numbers (method section 4)"),
    "test_pr43_streak_by_motion": ("regression", "the link's own frames since 0.4.0"),
    "test_pr43_speed_band": ("regression", "the band on the reference case's track"),
    "test_checklist_on_the_case_files": ("regression", "the checklist's answers on the case files the tool made"),
    "test_the_birds_bands_held_to_their_tracks": ("regression", "the bands on the birds' tracks"),
    "test_projective_held_to_the_jitter": ("regression", "the projective test against the measured jitter"),
    "test_flyer5_wingbeat": ("regression", "the paper's wingbeat, measured the paper's way; the flyer is known a bird by its beat"),
    "test_galileo_flyers_beat": ("regression", "the paper's wingbeats; known birds by the beat the gates were tuned on (X7)"),
    "test_pr135_flock": ("regression", "the paper's frequencies, measured with the tool"),
    "test_pr23_no_bird": ("regression", "the fix of 2026-10-09; what PR23's object is, nobody outside the tool says"),
    "test_wa9ony5_no_beat": ("control", "a balloon: its launch was filmed"),
    "test_wa9ony5_swing": ("control", "the payload's line, 'a little over one metre', from its maker"),
    "test_pr071_string": ("regression", "the line seen by eye; its object unidentified"),
    "test_pr055_nothing_tied": ("regression", "unidentified; the clouds seen by eye"),
    "test_audio_cases": ("control", "aircraft of known type in known phases of flight (DVIDS)"),
    "test_flyover_cases": ("control", "known aircraft over a camera, and ADS-B for the approaches"),
    "test_pr051_zoom_with_no_blank": ("control", "the data bar's FVW and SLR, read by eye"),
    "test_pr051_scene_path_against_the_data_bar": ("control", "the data bar's target motion"),
    "test_pr051_released_track_against_the_scene": ("regression", "the released-track null on the tool's own scene path"),
    "test_puerto_rico_k_from_the_data_bar": ("control", "the display's positions and ground point"),
    "test_puerto_rico_lanterns_tau_against_their_range": ("control", "the range from the display"),
    "test_puerto_rico_lanterns_over_the_doubling": ("control", "the range from the display"),
    "test_yemen_line_of_sight_against_the_laser": ("control", "the laser's range"),
    "test_flir1_frame_rate": ("control", "the MPEG header's field rate"),
    "test_flir1_zoom_and_release": ("control", "the readout, read by eye"),
    "test_flir1_readout": ("control", "the readout's ticks, read by eye"),
    "test_flir1_events": ("control", "the stretches read by hand"),
    "test_flir1_fields": ("control", "the display's fields of view"),
    "test_flir1_glyphs": ("regression", "held at what it reads now (10 of 11)"),
    "test_flir1_versions": ("control", "the two files' own frames and headers"),
    "test_atflir_navy": ("control", "the readouts' ticks read by hand"),
    "test_svanstrom_helicopter_lights": ("control", "the set's helicopter labels; the lights seen by eye"),
    "test_held_pictures_known_cadences": ("control", "cadences known from the recordings"),
    "test_pr43_dash_fitted_whole": ("regression", "PR43's dash fitted whole (method 45), as the tool read it on 2026-11-07"),
    "test_aaro_blind": ("regression", "the one press's labels on AARO's cases as recorded on 2026-11-07; AARO's answers, from "
                        "outside, are scored beside them (method 46), not held"),
    "test_exercises": ("regression", "each page's answer is what the tool said when the page was written (below)"),
}

EXERCISE_KINDS = {   # docs/exercises: what a page's answer is held to
    "01": ("regression", "PR44's beat, as the tool measures it: the bird is known by its beat"),
    "02": ("regression", "PR149's speed bound from the ship as a ruler: the ship's size is from outside, the answer the tool's"),
    "03": ("regression", "PR113 with a known field of view: the field is the Technical Note's, the answer the tool's"),
    "04": ("regression", "PR135's count, as the tool counts it"),
}


def test_golden_classified():
    """Every check of test_golden (and every exercise page) is called a control or a regression, so a new one is too."""
    print("\nwhich golden checks are controls, and which are regressions that follow the tool (B28)")
    names = re.findall(r"^def (test_\w+)\(", (HERE / "test_golden.py").read_text(encoding="utf-8"), re.M)
    missing = [n for n in names if n not in GOLDEN_KINDS]
    gone = [n for n in GOLDEN_KINDS if n not in names]
    check(not missing and not gone, "every test_golden check is called a control or a regression",
          f"not classified: {missing}" if missing else (f"no longer in test_golden: {gone}" if gone else f"{len(names)} checks"))
    pages = sorted(p.name[:2] for p in (ROOT / "docs" / "exercises").glob("[0-9][0-9]-*.md"))
    check(pages == sorted(EXERCISE_KINDS), "every exercise page is called a control or a regression", str(pages))
    c = [n for n, (k, _) in GOLDEN_KINDS.items() if k == "control"]
    print(f"        controls ({len(c)}): " + ", ".join(n[5:] for n in c))
    print(f"        regressions ({len(GOLDEN_KINDS) - len(c)}): " + ", ".join(n[5:] for n, (k, _) in GOLDEN_KINDS.items() if k != "control"))
    print("        the exercise pages: all four answers follow the tool -- they find a change, not an error")


# The exotica list (the SETI survey's T9, after Breakthrough Listen's Exotica catalog: one of every kind, run after every
# change; the aviation survey's flares, Av13): (kind, the controls of tests/golden/controls.csv that hold it -- none where it
# is missing --, and what holds it elsewhere or what is wanted).
EXOTICA = [
    ("a flapping bird, still camera, 60 fps", ("flyer1", "flyer2", "flyer3", "flyer4", "flyer5"), ""),
    ("a flock, members out of step", ("pr135_flock",), ""),
    ("a bird of the labelled set, distant (under 5 px), medium and close", ("sv_bird_distant", "sv_bird_medium", "sv_bird_close"), ""),
    ("a bird the test does not hear (gliding, most likely)", ("sv_bird_miss",), ""),
    ("a drone, distant and close", ("sv_drone_distant", "sv_drone_close"), ""),
    ("an airplane, distant and medium", ("sv_airplane_distant", "sv_airplane_medium"), ""),
    ("a helicopter, distant and close", ("sv_helicopter_distant", "sv_helicopter_close"), ""),
    ("an anti-collision strobe's train", ("v054", "v030"), ""),
    ("a propeller's line folded into the band", ("sv_airplane_064",), "a candidate, not a finding"),
    ("held pictures' own rhythm heard as a beat (one frame in three held: fps/3)", ("sv_drone_059",),
     "named a bird today; M3's cadence test misses it"),
    ("a background crossing behind the object", ("sv_helicopter_043",), ""),
    ("a helicopter's own modulation heard in the capped point disc, over the floor", ("sv_helicopter_024",), ""),
    ("a balloon whose payload swings", ("wa9ony5",), "and test_golden's swing"),
    ("an object lost against a hot roof", ("pr23",), ""),
    ("unidentified: a sphere among clouds, an object with a line below it", ("pr055", "pr071"), ""),
    ("a track the stage cannot decide (NO POWER)", ("sv_no_power",), ""),
    ("a codec's cadence, held pictures", (), "test_golden's held_pictures_known_cadences; no saved beat curve yet"),
    ("sky lanterns (flames), infrared, airborne", (), "test_golden's Puerto Rico lanterns (tau, range); no saved beat curve yet"),
    ("a helicopter hovering, its rotor's held beat", (), "test_drift's Santa Barbara UH-1H; no saved beat curve yet"),
    ("a balloon with its payload resolved, in the thermal infrared", (), "missing: a sounding-balloon launch filmed in the infrared"),
    ("a flare: illumination (minutes, under a canopy) and decoy (seconds, falling)", (), "missing: footage with a known flare"),
    ("an insect near the lens", (), "missing: a clip with the insect known (Galileo flyer 1's insect is a candidate)"),
    ("a gliding or soaring bird, known to glide", (), "missing: the labelled set's misses looked at by eye, or a known glider"),
    ("a drone with its light at night, and its own flash rate", (), "missing: footage taken for it"),
    ("a visible-band airplane at night, with ADS-B", (), "missing: aircraft near an airport, filmed for it"),
    ("an airborne helicopter and aircraft, from the flyers' cameras", (), "missing: expected from the Galileo cameras"),
    ("a wind farm's obstruction lights, in step", (), "missing: a clip that shows them"),
    ("a satellite or a star (autokinesis)", (), "missing: a known pass"),
    ("sea glint; a ship's lights", (), "missing: a clip with a known ship"),
    ("the sensor's own: fixed-pattern defects, overlay strokes", (), "missing: the codec's and the display's, saved as curves"),
]


def test_exotica():
    """The exotica list: every control it names is in the manifest, and every control of the manifest is on it."""
    print("\nthe exotica list (T9): one of everything the harness should hold")
    names = {r["name"] for r in manifest(every=True)}
    for kind, held, note in EXOTICA:
        status = "held" if held else ("elsewhere" if not note.startswith("missing") else "missing")
        print(f"        {status:<9} {kind}" + (f": {', '.join(held)}" if held else "") + (f" ({note.removeprefix('missing: ')})" if note else ""))
    listed = {n for _, held, _ in EXOTICA for n in held}
    check(listed <= names and names <= listed, "every control on the list is in the manifest, and every one in the manifest on it",
          f"not in the manifest: {sorted(listed - names)}; not on the list: {sorted(names - listed)}" if listed != names else
          f"{sum(bool(h) for _, h, _ in EXOTICA)} kinds held here, {sum(not h and not n.startswith('missing') for _, h, n in EXOTICA)} "
          f"elsewhere, {sum(n.startswith('missing') for _, h, n in EXOTICA)} missing")


def test_holdout_ledger():
    """B17: the ledger of looks beside the held-out third, its 2026-10-18 look entered; and the agreement stated as a
    difference with a by-video interval, on a table made for the test (the held-out third is not looked at here)."""
    print("\nthe held-out third: the ledger of looks, and agreement as a difference (B17)")
    from agreement import agreement
    from holdout import held_out
    rows = list(csv.DictReader((l for l in open(ROOT / "tools" / "sweep" / "looks.tsv", encoding="utf-8") if not l.startswith("#")),
                               delimiter="\t"))
    check(all(set(r) == {"date", "commit", "gates", "set", "who", "seen"} and all(v is not None for v in r.values()) for r in rows)
          and any(r["date"] == "2026-10-18" and r["commit"] == "ffa9f3f" for r in rows),
          "the ledger of looks: date, commit, gates, set, who, what was seen; the look of 2026-10-18 on ffa9f3f entered",
          f"{len(rows)} lines")
    held = sorted(held_out())
    open_ = [f"OPEN{k}" for k in range(40)]
    table = []
    for v in held + open_:          # made for the test: every video 20 objects, a fifth of the held-out ones' called
        for j in range(20):
            table.append(dict(id=v, beats=str(j < (4 if v in held[:21] else 1))))
    A = agreement(table, set(held))
    d = A["difference"]
    check(abs(A["held"]["share"] - 0.125) < 1e-9 and abs(A["tuning"]["share"] - 0.05) < 1e-9 and d["lo"] < 0.075 < d["hi"],
          "a difference held out minus tuning, with its interval resampling videos, holds the true difference",
          f"{100 * A['held']['share']:.1f} % against {100 * A['tuning']['share']:.1f} %, {100 * d['lo']:+.1f} to {100 * d['hi']:+.1f} points")


def main():
    global ONLY
    if "--only" in sys.argv:
        ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(","))
        print(f"the saved controls judged in this run: {', '.join(sorted(ONLY))} (the rest are not)")
    test_bounds()
    test_saved_controls()
    test_sample_against_the_table()
    test_rates_of_record()
    test_golden_classified()
    test_exotica()
    test_holdout_ledger()
    print(f"\n{len(PASS)} PASS, {len(FAIL)} FAIL, {len(SKIP)} SKIP")
    if FAIL:
        print(f"{len(FAIL)} FAILED: {', '.join(FAIL)}")
    else:
        print("ALL PASS" + (f" ({len(SKIP)} skipped: {', '.join(SKIP)})" if SKIP else ""))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
