"""The planting pilot's tables: completeness and reliability from the chain runs' records (tools/plant_chain.py).

    python3 tools/plant_tables.py DIR [DIR ...] --out pilot      # writes pilot.md and pilot.json

Reads every `*_chain.json` under the folders given. For each video and for all of them together:

- **completeness**: of the objects planted, the share Find lists (on its path by `plant.on_path`'s rule, among the
  400 rows kept), the share among the 30 rows a person is shown, and the share the link then follows over half the
  object's frames or more -- by kind, and for the plain kinds by contrast as written, by width and by speed against
  the scene, each with Wilson's 95 % interval;
- **reliability**: how often a planted path is "found" in the control, where it was not planted (the rule's chance
  rate); how many rows the planted video's list has that are on no planted path and not on the control's list either
  (rows the planting made); what the second encode alone does to the original's list; and `flicker` on the followed
  objects -- a beat called on a constant object is a false alarm, a planted beat is recovered where the beat called
  is within two resolutions of it;
- **cost**: CPU-seconds a frame for each step, and a second-by-second account an object.

Arithmetic over small saved tables: no video is read. Nothing here is tuned; the cells are fixed before the runs.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import plant  # noqa: E402

CONTRAST = ((0, 15), (15, 30), (30, 60), (60, 120), (120, 1e9))        # DN as written
AFTER = ((0, 5), (5, 15), (15, 30), (30, 60), (60, 120), (120, 1e9))    # DN after the encoder (the planted video less the control)
SPEED = ((0, 0.3), (0.3, 1.0), (1.0, 3.0), (3.0, 10.0), (10.0, 1e9))    # px a frame against the scene
PLAIN = ("dot", "body", "still")                                        # constant light: the kinds the grid is read on
BEATING = ("beat", "bird", "flock")


def cell(v, edges):
    if v is None:
        return None
    for lo, hi in edges:
        if lo <= v < hi:
            return f"{lo:g}-{hi:g}" if hi < 1e8 else f"over {lo:g}"
    return None


def load(dirs):
    """The units, and for each one that ran no control of its own, the control of another seed of the same stretch
    (it is the same file: one stretch, one encoding, nothing planted) held against its truth table and its rows."""
    units = []
    for d in dirs:
        for f in sorted(Path(d).rglob("*_chain.json")):
            u = json.loads(f.read_text())
            u["file"] = str(f)
            units.append(u)
    controls = {}
    for u in units:
        f = Path(u["file"].replace("_chain.json", "_control_rows.json"))
        if u.get("control") and f.exists():
            controls[(u["tag"], u["stretch"]["n0"], u["stretch"]["n1"])] = f
    for u in units:
        key = (u["tag"], u["stretch"]["n0"], u["stretch"]["n1"])
        if u.get("control") or key not in controls:
            continue
        truth_f, rows_f = Path(u["file"].replace("_chain.json", "_truth.json")), Path(u["file"].replace("_chain.json", "_rows.json"))
        if not (truth_f.exists() and rows_f.exists()):
            continue
        truth, rows, control = json.loads(truth_f.read_text()), json.loads(rows_f.read_text()), json.loads(controls[key].read_text())
        rec = plant.recovered(truth, rows)
        phantom = plant.recovered(truth, control)
        others = [dict(o, in_control=j) for o, j in zip(rec["others"], _same_rows([rows[o["rank"] - 1] for o in rec["others"]], control))]
        u["control"] = dict(rows=len(control), strengths={s: sum(r["strength"] == s for r in control) for s in ("strong", "fair", "weak")},
                            phantoms_found=phantom["found"], others=len(others),
                            others_in_control=sum(o["in_control"] is not None for o in others),
                            others_new=[o for o in others if o["in_control"] is None][:60], borrowed=str(controls[key]))
    return units


def _same_rows(a, b):
    tb = [({int(n): xy for n, xy in r["track"].items()}, r) for r in b]
    out = []
    for r in a:
        ta = {int(n): xy for n, xy in r["track"].items()}
        out.append(next((j for j, (t, q) in enumerate(tb, 1)
                         if plant.on_path(ta, t, float(q.get("size_px") or 0.0)) or plant.on_path(t, ta, float(r.get("size_px") or 0.0))), None))
    return out


def rows_of(units):
    out = []
    for u in units:
        for r in u["plants"]:
            link = r.get("link") or {}
            fl = r.get("flicker") or {}
            hz, res = r.get("hz"), fl.get("resolution_hz") or 0.5
            called = fl.get("beats") is True
            out.append(dict(r, video=u["tag"], seed=u["seed"], shown=bool(r.get("shown")),
                            followed=bool(link.get("covered", 0) >= 0.5),
                            linked="link" in r and "error" not in link, covered=link.get("covered"),
                            link_px=link.get("median_px"), link_off=link.get("off"), link_beyond=link.get("beyond"),
                            contrast_cell=cell(r.get("contrast_written"), CONTRAST),
                            after_cell=cell(r.get("contrast_after"), AFTER),
                            speed_cell=cell(r.get("speed_scene") if r.get("speed_scene") is not None else r.get("speed"), SPEED),
                            flickered="flicker" in r and "error" not in fl, beat_called=called,
                            beat_right=bool(called and hz and fl.get("hz") and
                                            min(abs(fl["hz"] - hz), abs((fl.get("double_hz") or 1e9) - hz), abs(fl["hz"] - 2 * hz)) <= 2 * res),
                            beat_hz=fl.get("hz")))
    return out


def share(rows, key):
    k, n = sum(bool(r[key]) for r in rows), len(rows)
    lo, hi = plant.wilson(k, n)
    return dict(n=n, k=k, share=k / n if n else None, low=lo, high=hi)


def said(c):
    return "-" if not c["n"] else f"{c['k']}/{c['n']} = {100 * c['share']:.0f} % ({100 * c['low']:.0f}-{100 * c['high']:.0f})"


def table(rows, by, keys=("found", "shown", "followed")):
    cells = {}
    for r in rows:
        cells.setdefault(r.get(by), []).append(r)
    order = sorted(cells, key=lambda v: (v is None, _first_number(v)))
    return [dict({by: v}, **{k: share(cells[v], k) for k in keys}) for v in order]


def _first_number(v):
    try:
        return (0, float(str(v).replace("over ", "").split("-")[0]))
    except ValueError:
        return (1, str(v))


def markdown_table(tab, by, title, keys=("found", "shown", "followed"),
                   heads=("on Find's list", "among the 30 rows shown", "followed over half its frames")):
    L = [f"**{title}**", "", f"| {by} | " + " | ".join(heads) + " |", "|---|" + "---|" * len(keys)]
    for c in tab:
        L.append(f"| {c[by]} | " + " | ".join(said(c[k]) for k in keys) + " |")
    return L + [""]


def groups_of(rows):
    """One row a planted group (a flock, a formation, the copies of a recorded group): its members, how many of them
    Find lists, whether any is, whether the row that has one says it holds several points, and whether the link followed
    any member over half its frames."""
    by = {}
    for r in rows:
        if r.get("group") is not None:
            by.setdefault((r["video"], r["seed"], r["group"]), []).append(r)
    return [dict(video=k[0], seed=k[1], group=k[2], kind=v[0].get("kind"), members=len(v), found_members=sum(r["found"] for r in v),
                 found=any(r["found"] for r in v), as_group=any(r["found"] and (r.get("points") or 0) >= 2 for r in v),
                 all_found=all(r["found"] for r in v), followed=any(r["followed"] for r in v)) for k, v in sorted(by.items())]


def recorded(units):
    """The real objects of the videos that have a recorded track, and their planted copies: each found or not on the
    original's list, the control's and the planted video's (IDEAS.md B22's check, on the same videos)."""
    out = []
    for u in units:
        rec = u.get("recorded")
        if not rec:
            continue
        twins = {r["id"]: r for r in u["plants"] if r.get("kind") == "twin"}
        for i, r in enumerate(rec.get("planted") or []):
            pick = lambda name: (rec.get(name) or [{}] * (i + 1))[i]
            t = twins.get(r["id"], {})
            out.append(dict(video=u["tag"], id=r["id"], original=pick("original").get("found"), original_rank=pick("original").get("rank"),
                            control=pick("control").get("found"), control_rank=pick("control").get("rank"),
                            beside_plants=r["found"], beside_plants_rank=r["rank"], copy=t.get("found"), copy_rank=t.get("rank"),
                            copy_contrast=t.get("contrast_written"), copy_frames=t.get("frames")))
    return out


def reliability(units, rows):
    with_control = [u for u in units if u.get("control")]
    planted_c = sum(u["planted"] for u in with_control)
    chance = sum(u["control"]["phantoms_found"] for u in with_control)
    lo, hi = plant.wilson(chance, planted_c)
    out = dict(chance=dict(k=chance, n=planted_c, low=lo, high=hi),
               control_rows=[dict(video=u["tag"], seed=u["seed"], rows=u["control"]["rows"], **u["control"]["strengths"])
                             for u in with_control if not u["control"].get("borrowed")],
               new_rows=[dict(video=u["tag"], seed=u["seed"], planted=u["planted"], others=u["control"]["others"],
                              in_control=u["control"]["others_in_control"],
                              new=u["control"]["others"] - u["control"]["others_in_control"],
                              new_not_weak=sum(o.get("strength") != "weak" for o in u["control"]["others_new"]))
                         for u in with_control],
               second_encode=[dict(video=u["tag"], seed=u["seed"], types_same=u["settings"].get("types_same"),
                                   rows=u["original"]["rows"] if isinstance(u["original"]["rows"], int) else sum(u["original"]["strengths"].values()),
                                   in_control=u["original"].get("in_control"),
                                   top30=u["original"].get("top30"), top8=u["original"].get("top8"),
                                   fair_or_strong=u["original"].get("fair_or_strong"), control_rows=u["control"]["rows"])
                              for u in units if u.get("original") and u.get("control")])
    fl = [r for r in rows if r["flickered"]]
    const = [r for r in fl if r.get("light") in (None, "constant")]
    beat = [r for r in fl if r.get("light") in ("beat", "wander")]
    out["flicker"] = dict(
        constant=share(const, "beat_called"), beating_called=share(beat, "beat_called"), beating_right=share(beat, "beat_right"),
        twinkle=share([r for r in fl if r.get("light") == "twinkle"], "beat_called"),
        strobe=share([r for r in fl if r.get("light") == "strobe"], "beat_called"),
        too_short=sum(1 for r in rows if r["linked"] and not r["flickered"]),
        steady=share([r for r in beat if r.get("light") == "beat"], "beat_right"),
        wandering=share([r for r in beat if r.get("light") == "wander"], "beat_right"))
    return out


def cost(units):
    steps = {}
    for u in units:
        for name, d in u["timings"].items():
            s = steps.setdefault(name, dict(cpu_s=0.0, wall_s=0.0, frames=0, times=0, units=0))
            s["cpu_s"] += d["cpu_s"]
            s["wall_s"] += d["wall_s"]
            s["times"] += d["times"]
            s["frames"] += u["frames"]
            s["units"] += 1
    for name, s in steps.items():
        s["cpu_s_per_frame"] = s["cpu_s"] / max(s["frames"], 1)
        s["cpu_s_each"] = s["cpu_s"] / max(s["times"], 1)
        s["wall_s_each"] = s["wall_s"] / max(s["times"], 1)
    return steps


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    units = load(args.dirs)
    if not units:
        sys.exit("no *_chain.json under " + ", ".join(args.dirs))
    rows = rows_of(units)
    videos = sorted({u["tag"] for u in units})
    L = ["# The planting pilot: completeness and reliability", "",
         f"{len(units)} planted videos of {len(videos)} videos, {len(rows)} planted objects (a group's members each count). "
         "Each cell: found / planted = share (Wilson's 95 % interval).", ""]
    result = dict(units=len(units), objects=len(rows), videos={})
    for name, part_u in [("all", units)] + [(v, [u for u in units if u["tag"] == v]) for v in videos]:
        part = [r for r in rows if name == "all" or r["video"] == name]
        plain = [r for r in part if r.get("kind") in PLAIN]
        dots = [r for r in part if r.get("kind") == "dot"]
        tabs = dict(kind=table(part, "kind"), contrast=table(dots, "contrast_cell"), after=table(dots, "after_cell"),
                    speed=table(dots, "speed_cell"),
                    sigma=table(dots, "sigma"), dark=table(dots, "dark"))
        loud = [r for r in dots if (r.get("contrast_written") or 0) >= 30]
        tabs["speed_loud"] = table(loud, "speed_cell")
        tabs["contrast_moving"] = table([r for r in dots if (r.get("speed_scene") or r.get("speed") or 0) >= 1.0], "contrast_cell")
        tabs["after_moving"] = table([r for r in dots if (r.get("speed_scene") or r.get("speed") or 0) >= 1.0], "after_cell")
        frames = sum(u["frames"] for u in part_u)
        L += [f"## {name}", "", f"{len(part_u)} planted videos, {frames} frames, {len(part)} objects; "
              f"the scene moved {np.median([u.get('scene_speed') or 0 for u in part_u]):.2f} px a frame at the median.", ""]
        L += markdown_table(tabs["kind"], "kind", "By kind")
        gr = groups_of(part)
        if gr:
            tabs["groups"] = [dict(kind=k, groups=share([g for g in gr if g["kind"] == k], "found"),
                                   as_group=share([g for g in gr if g["kind"] == k], "as_group"),
                                   every_member=share([g for g in gr if g["kind"] == k], "all_found"),
                                   followed=share([g for g in gr if g["kind"] == k], "followed"),
                                   members=dict(n=sum(g["members"] for g in gr if g["kind"] == k),
                                                k=sum(g["found_members"] for g in gr if g["kind"] == k)))
                              for k in sorted({g["kind"] for g in gr})]
            L += ["**Groups** (a group is listed where any member is; \"as a group\": the row says it holds two points or more)", "",
                  "| kind | groups listed | listed as a group | every member listed | a member followed | members listed |", "|---|---|---|---|---|---|"]
            for c in tabs["groups"]:
                L.append(f"| {c['kind']} | {said(c['groups'])} | {said(c['as_group'])} | {said(c['every_member'])} | {said(c['followed'])} | "
                         f"{c['members']['k']}/{c['members']['n']} |")
            L.append("")
        rc = recorded(part_u)
        if rc:
            tabs["recorded"] = rc
            yn = lambda v, r: "-" if v is None else (f"row {r}" if v else "not listed")
            L += ["**The recorded objects and their planted copies** (B22's check on the same video)", "",
                  "| object | in the original | in the control | beside the plants | its copy |", "|---|---|---|---|---|"]
            for r in rc:
                L.append(f"| {r['video']} {r['id']} | {yn(r['original'], r['original_rank'])} | {yn(r['control'], r['control_rank'])} | "
                         f"{yn(r['beside_plants'], r['beside_plants_rank'])} | {yn(r['copy'], r['copy_rank'])} "
                         f"({r['copy_contrast']} DN, {r['copy_frames']} frames) |")
            L.append("")
        L += markdown_table(tabs["contrast"], "contrast_cell", "Constant points, by contrast as written (grey levels)")
        L += markdown_table(tabs["after"], "after_cell", "Constant points, by contrast after the encoder (grey levels; the planted video less the control)")
        kept = {}
        for r in dots:
            if r.get("contrast_after") is not None and r.get("contrast_written"):
                kept.setdefault(r["contrast_cell"], []).append(r["contrast_after"] / r["contrast_written"])
        if kept:
            tabs["encoder_keeps"] = {k: dict(n=len(v), median=float(np.median(v)), low=float(np.percentile(v, 16)), high=float(np.percentile(v, 84)))
                                     for k, v in kept.items()}
            L += ["**What the encoder leaves of a constant point's contrast** (after / written: the median, and the 16th to 84th centile)", "",
                  "| written | objects | share left |", "|---|---|---|"]
            for k in sorted(kept, key=_first_number):
                c = tabs["encoder_keeps"][k]
                L.append(f"| {k} | {c['n']} | {c['median']:.2f} ({c['low']:.2f}-{c['high']:.2f}) |")
            L.append("")
        L += markdown_table(tabs["speed"], "speed_cell", "Constant points, by speed against the scene (px a frame)")
        L += markdown_table(tabs["speed_loud"], "speed_cell", "The same for points of 30 grey levels or more")
        L += markdown_table(tabs["contrast_moving"], "contrast_cell", "By contrast, for points moving 1 px a frame or more against the scene")
        L += markdown_table(tabs["after_moving"], "after_cell", "The same by contrast after the encoder")
        L += markdown_table(tabs["sigma"], "sigma", "Constant points, by sigma (px)")
        L += markdown_table(tabs["dark"], "dark", "Constant points, dark (True) or bright")
        rel = reliability(part_u, part)
        c, f = rel["chance"], rel["flicker"]
        L += ["**Reliability**", "",
              f"- A planted path found in the control, where nothing was planted: {c['k']} of {c['n']}"
              + (f" (at most {100 * c['high']:.1f} %)" if c["n"] else "") + ".",
              "- Rows on the planted video's list that are on no planted path and not on the control's list: "
              + "; ".join(f"{r['video']} seed {r['seed']}: {r['new']} of {r['others']} ({r['new_not_weak']} fair or strong)" for r in rel["new_rows"][:8]) + ".",
              "- What the second encode alone changes (the stretch encoded again with nothing planted; "
              "the encoder gave the share of frames in brackets the picture type the video gives them): "
              + "; ".join(f"{r['video']} [{100 * (r['types_same'] or 0):.0f} %]: {r['in_control']} of the original's {r['rows']} rows are on the control's list, "
                          f"{r['top30']['kept']} of its first {r['top30']['n']}, {r['top8']['kept']} of its first {r['top8']['n']}"
                          + (f", {r['fair_or_strong']['kept']} of its {r['fair_or_strong']['n']} fair or strong rows" if r["fair_or_strong"]["n"] else ", none of them fair or strong")
                          for r in rel["second_encode"]) + ".",
              f"- `flicker`, on followed objects of 60 frames or more: a beat called on a constant object {said(f['constant'])}; "
              f"on a twinkling one {said(f['twinkle'])}; on a strobe {said(f['strobe'])}; a planted beat called {said(f['beating_called'])}, "
              f"and at its frequency {said(f['beating_right'])} (steady {said(f['steady'])}, wandering {said(f['wandering'])}). "
              f"{f['too_short']} followed objects were too short for a beat.", ""]
        result["videos"][name] = dict(tables=tabs, reliability=rel, units=len(part_u), objects=len(part), frames=frames)
    steps = cost(units)
    L += ["## Cost", "", "| step | CPU-s a frame | CPU-s each time | wall s each time | times |", "|---|---|---|---|---|"]
    for name, s in steps.items():
        L.append(f"| {name} | {s['cpu_s_per_frame']:.3f} | {s['cpu_s_each']:.1f} | {s['wall_s_each']:.1f} | {s['times']} |")
    result["cost"] = steps
    Path(f"{args.out}.md").write_text("\n".join(L) + "\n")
    Path(f"{args.out}.json").write_text(json.dumps(result, indent=1, default=plant._plain))
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
