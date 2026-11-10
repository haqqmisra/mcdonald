"""The companion gate of `mcdonald tether`, held against a null (docs/method.md, section 6; set in 0.5.2, 2026-11-10).

A track that nothing in the picture keeps step with can have no companion. Each recorded track is run through the
stage's own passes three times: on itself, on itself run backwards in time, and on itself shifted by half its length
(the same frames, the same ring about a place the object is not at). Whatever the gate then calls a companion on a null
track is false, unless it is the real object or what the real track's own run followed with it. The gate's numbers
(`tether.CONTROL`, `SIGHT`, `HOLD`, `FOLLOWED`, `STEADY`, `SCENE`) were set from the count this prints, with the known
companions (WA9ONY-5's payload, PR071's string, PR105's lower point, AARO's PR-004 on its eight tracks) kept.

    python3 tools/tether_null.py collect TASKS.json INDEX --out DIR [--frames DIR]   # one video's tracks, frames read
    python3 tools/tether_null.py table DIR                                           # every followed candidate a row
    python3 tools/tether_null.py gate DIR [--scan] [--control 0.6 --followed 0.3 --steady 1.5 --scene 0.5]

TASKS.json is [[name, {"set": .., "video": path, "objs": [{"name": .., "track": path, "n0": .., "n1": .., "size": ..,
"r_max": .., "mask_rows": ..}]}]]; paths are absolute or relative to the reference-data folder (`$MCDONALD_DATA`). The
list of 2026-11-10, its tracks and the rows it gave are there, in `tether_null/` (its README). `collect` reads frames, so
it goes through the queue, a video a task; `table` and `gate` read what it saved, and take seconds. Each way of every
follower is saved, so `tether.merge_ways`, `tether.followed_how` and the gate can be changed and held to the same null
with no frame read again; a change to `tether.Follower` or to the stack needs `collect` again.
"""
import argparse
import glob
import itertools
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE.parent / "tests"))
from mcdonald import forensics as vf, tether  # noqa: E402

FOLLOWED_EACH = 30                 # candidates followed on each track: the gate is asked of more than the stage follows
KINDS = ("real", "rev", "shift")
# the companions known to be there, which the gate must keep: (set, video, object) -> (r_px, tolerance) or None for any
KNOWN = {("kit", "wa9ony5", "balloon"): None, ("kit", "pr071", "object"): None, ("kit", "pr105", "upper_1075_2155"): (26.0, 6.0)}
KNOWN.update({("aaro", "dod_111300649", f"object-{i}"): (31.0, 6.0) for i in range(1, 9)})


def data(path):
    import reference_data
    return str(path) if os.path.isabs(str(path)) else str(reference_data.root() / path)


def null_track(track, ns, kind):
    """The track itself, run backwards in time, or shifted by half its length: the same places, at the wrong times."""
    if kind == "real":
        return dict(track)
    if kind == "rev":
        return {n: track[ns[len(ns) - 1 - i]] for i, n in enumerate(ns)}
    h = len(ns) // 2
    return {n: track[ns[(i + h) % len(ns)]] for i, n in enumerate(ns)}


def one(clip, masks, track, rows, size, r_min, r_max, strokes=True, procs=None):
    """The stage's passes on one track, every candidate kept whatever the control says, the strongest followed."""
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    radius = int(min(0.75 * max(clip.W, clip.H), (r_max + 2) * (size or 40)))
    frames = tether.Frames(clip, masks, track, min(radius, tether.STROKE_REGION), rows, strokes, procs=procs)
    m, cnt, mc, repeats = tether.stack_both(clip, track, frames, radius=radius)
    est = tether.object_size(m, cnt, radius)
    size_used = size or est or 10.0
    extent = tether.object_extent(m, cnt, radius, size_used)
    r_min_used = r_min if r_min is not None else max(tether.R_MIN, (extent + 2 * tether.SIGMA_OUT) / size_used)
    cands, sig = tether.candidates(m, cnt, mc, size_used, radius, r_min_used, r_max, control=1e9)
    cands, _, _ = tether.examine(clip, track, frames, cands, size_used, follow=())
    by_seen = sorted(range(len(cands)), key=lambda k: (-(cands[k]["seen_on_frames"] or 0), -cands[k]["z"]))
    by_z = sorted(range(len(cands)), key=lambda k: -cands[k]["z"])
    follow = list(dict.fromkeys(by_seen[:FOLLOWED_EACH * 2 // 3] + by_z[:FOLLOWED_EACH]))[:FOLLOWED_EACH]
    cands, gots, bg = tether.examine(clip, track, frames, cands, size_used, follow=follow, keep=r_min_used * size_used)
    followed, series = [], {}
    for k in follow:
        c = cands[k]
        for w in (0, 1):                                 # each way's own chain: the merge is replayed from them
            g = c["_ways"][w]
            series[f"way{w}_{k}"] = np.array([[n, *g[n]] for n in sorted(g)]) if g else np.zeros((0, 5))
        followed.append(dict({kk: v for kk, v in c.items() if not kk.startswith("_")}, k=k))
    series["bg"] = np.array([[n, *bg[n]] for n in sorted(bg)]) if bg else np.zeros((0, 3))
    series["track"] = np.array([[n, *track[n]] for n in ns])
    series["repeats"] = np.array(sorted(repeats))
    xy = np.array([track[n] for n in ns])
    return dict(frames=len(ns), repeats=len(repeats), size=size_used, size_measured=est, extent=extent, r_min=r_min_used, r_max=r_max,
                stack_noise=sig, moved=float(np.hypot(*(xy.max(0) - xy.min(0)))), n_cands=len(cands), fps=clip.fps, followed=followed), series


def collect(a):
    tasks = json.load(open(a.tasks))
    name, t = tasks[a.index]
    procs = int(os.environ.get("SLURM_CPUS_PER_TASK", "2"))
    for o in t["objs"]:
        out = os.path.join(a.out, t["set"], name, o["name"])
        os.makedirs(out, exist_ok=True)
        if os.path.exists(f"{out}/done"):
            print(name, o["name"], "already done", flush=True)
            continue
        track = vf.read_track(data(o["track"]))
        n0, n1 = o.get("n0") or min(track), o.get("n1") or max(track)
        clip = vf.Clip(data(t["video"]), os.path.join(a.frames or os.path.join(a.out, "frames"), name), n0, n1)
        ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
        if len(ns) < 30:
            print(name, o["name"], "fewer than 30 frames", flush=True)
            continue
        track = {n: track[n] for n in ns}
        masks, rows = vf.static_masks(clip), vf.parse_rows(o.get("mask_rows"))
        size, r_min = o.get("size"), None
        for kind in KINDS:
            t0 = time.time()
            info, series = one(clip, masks, null_track(track, ns, kind), rows, size, r_min, o.get("r_max", tether.R_MAX), procs=procs)
            if kind == "real":                           # the nulls search the same ring, about a place with no object at it
                size, r_min = info["size"], info["r_min"]
            json.dump(info, open(f"{out}/{kind}.json", "w"), indent=1)
            np.savez_compressed(f"{out}/{kind}.npz", **series)
            print(name, o["name"], kind, f"{len(ns)} frames, {info['n_cands']} candidates, {len(info['followed'])} followed, {time.time() - t0:.0f} s", flush=True)
        open(f"{out}/done", "w").write("ok\n")


def table(a):
    """Every followed candidate a row, its chain merged and read by the package as it now is."""
    rows = []
    for done in sorted(glob.glob(f"{a.dir}/*/*/*/done")):
        d = os.path.dirname(done)
        set_, video, obj = d.split(os.sep)[-3:]
        real = np.load(f"{d}/real.npz")
        rtrack = {int(n): np.array([x, y]) for n, x, y in real["track"]}
        ways_of = lambda z, c: [{int(r[0]): tuple(r[1:]) for r in z[f"way{w}_{c['k']}"]} for w in (0, 1)]
        rchains = {}
        for c in json.load(open(f"{d}/real.json"))["followed"]:
            m, _ = tether.merge_ways((c["dx_px"], c["dy_px"]), ways_of(real, c))
            rchains[c["k"]] = {n: np.array(v[:2]) for n, v in m.items()}
        for kind in KINDS:
            info, z = json.load(open(f"{d}/{kind}.json")), np.load(f"{d}/{kind}.npz")
            T = {int(n): (x, y) for n, x, y in z["track"]}
            bg = {int(n): (x, y) for n, x, y in z["bg"]}
            for c in info["followed"]:
                m, runs = tether.merge_ways((c["dx_px"], c["dy_px"]), ways_of(z, c))
                got = {n: (T[n][0] + v[0], T[n][1] + v[1]) for n, v in m.items()}
                row = dict(set=set_, video=video, obj=obj, kind=kind, frames=info["frames"], size=info["size"], moved=info["moved"],
                           **{k: c[k] for k in ("k", "dx_px", "dy_px", "r_px", "r_over_size", "direction_deg", "sign", "z", "z_control",
                                                "dog_dn", "seen_on_frames", "jitter_px")},
                           **tether.followed_how(sorted(T), got, runs, T, bg, [int(v) for v in z["repeats"]]),
                           strength=float(np.median([v[2] for v in m.values()])) if m else None)
                if kind != "real" and m:                 # the real object, or what the real track's run followed with it?
                    fs = sorted(m)
                    q = np.array([np.array(got[n]) - rtrack[n] for n in fs])
                    row["is_object"] = float((np.hypot(q[:, 0], q[:, 1]) <= max(info["size"], 12.0)).mean())
                    row["same_as_real"] = max((sum(np.hypot(*(q[i] - rc[n])) <= 6.0 for i, n in enumerate(fs) if n in rc) / len(fs)
                                               for rc in rchains.values()), default=0.0)
                rows.append(row)
    json.dump(rows, open(f"{a.dir}/rows.json", "w"))
    print(len(rows), "rows from", len({(r["set"], r["video"], r["obj"]) for r in rows}), "tracks ->", f"{a.dir}/rows.json")


def passes(r, control, followed, steady, scene, hold=True):
    """`tether.judge`'s rule on a row, each number open to change; `hold` False counts every frame seen, not the held ones."""
    return (r["z"] >= tether.Z_MIN and r["z_control"] <= control * r["z"]
            and (r["held_on" if hold else "followed_on"] or 0) >= followed
            and r["followed_jitter_px"] is not None and r["followed_jitter_px"] <= steady
            and not ((r["scene_share"] or 0) >= scene and r["scene_moved_px"] >= tether.STILL)
            and not ((r["screen_share"] or 0) >= scene and r["screen_moved_px"] >= tether.STILL))


def own(r):
    """A null-track row that is the real object, or what the real track's own run followed with it: not a false companion."""
    return (r.get("is_object") or 0) >= 0.3 or (r.get("same_as_real") or 0) >= 0.3


def count(rows, rule, hold=True):
    tracks = sorted({(r["set"], r["video"], r["obj"]) for r in rows})
    by = {}
    for r in rows:
        if passes(r, *rule, hold=hold):
            by.setdefault((r["set"], r["video"], r["obj"], r["kind"]), []).append(r)
    real = {t: by.get((*t, "real"), []) for t in tracks}
    null = {(t, k): [r for r in by.get((*t, k), []) if not own(r)] for t in tracks for k in KINDS[1:]}
    kept = [t for t in KNOWN if t in real and any(KNOWN[t] is None or abs(r["r_px"] - KNOWN[t][0]) <= KNOWN[t][1] for r in real[t])]
    return tracks, real, null, kept, sum(own(r) for v in by.values() for r in v)


def line(r):
    f = lambda v, n=2: "n/a" if v is None else "%.*f" % (n, v)
    return ("%4.0f px at %4.0f deg, %-6s z %4.1f, control %.2f | seen on %s, held on %s in %s stretches, to %s px, %s x the noise | "
            "scene %s (%3.0f px), screen %s (%3.0f px)" % (
                r["r_px"], r["direction_deg"], r["sign"], r["z"], r["z_control"] / r["z"], f(r["followed_on"]), f(r["held_on"]), r["stretches"],
                f(r["followed_jitter_px"]), f(r["strength"], 1), f(r["scene_share"]), r["scene_moved_px"], f(r["screen_share"]), r["screen_moved_px"]))


def gate(a):
    rows = json.load(open(f"{a.dir}/rows.json"))
    rule = (a.control, a.followed, a.steady, a.scene)
    known = [t for t in KNOWN if any((r["set"], r["video"], r["obj"]) == t for r in rows)]
    if a.scan:
        print("%-58s %10s %8s %s" % ("the gate", "real with", "known", "null tracks with a false companion (backwards, shifted)"))
        variants = [("as set: control %g, held on %g, smooth to %g px, scene %g" % rule, rule, True),
                    ("every frame seen counted, not the held ones", rule, False),
                    ("no test against the scene or the screen", (*rule[:3], 1e9), True),
                    ("no smooth path asked", (rule[0], rule[1], 1e9, rule[3]), True),
                    ("no control", (1e9, *rule[1:]), True)]
        variants += [("control %g" % c, (c, *rule[1:]), True) for c in (0.3, 0.45, 0.8) if c != rule[0]]
        variants += [("held on %g of the frames" % f, (rule[0], f, *rule[2:]), True) for f in (0.2, 0.25, 0.4, 0.5) if f != rule[1]]
        variants += [("smooth to %g px" % s, (rule[0], rule[1], s, rule[3]), True) for s in (1.0, 2.5) if s != rule[2]]
        variants += [("scene %g" % s, (*rule[:3], s), True) for s in (0.3, 0.7) if s != rule[3]]
        for name, v, hold in variants:
            tracks, real, null, kept, _ = count(rows, v, hold)
            k = [kk for (t, kk), w in null.items() if w]
            print("%-58s %4d of %-3d %3d/%-3d %3d of %d (%d, %d)" % (name, sum(bool(w) for w in real.values()), len(tracks), len(kept), len(known),
                                                                    len(k), len(null), k.count("rev"), k.count("shift")))
        return
    tracks, real, null, kept, owned = count(rows, rule)
    print("the gate: control %g, held on %g of the frames, smooth to %g px, under %g of the scene's or the screen's motion" % rule)
    print(f"\nreal tracks with a companion: {sum(bool(v) for v in real.values())} of {len(tracks)}; the known ones kept: {len(kept)} of {len(known)}")
    for t, v in real.items():
        if v:
            best = sorted(v, key=lambda r: (-round(r["held_on"], 1), r["r_px"]))[0]
            print("  %-4s %-14s %-16s %s%s" % (*t, line(best), "   [known]" if t in KNOWN else ""))
    k = [kk for (t, kk), w in null.items() if w]
    print(f"\nnull tracks with a false companion: {len(k)} of {len(null)} ({k.count('rev')} run backwards, {k.count('shift')} shifted)")
    for (t, kk), v in null.items():
        for r in v:
            print("  %-4s %-14s %-16s %-5s %s" % (*t, kk, line(r)))
    print(f"\nfeatures on null tracks that are the real object or its own companion, not counted: {owned}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="what", required=True)
    c = sub.add_parser("collect")
    c.add_argument("tasks")
    c.add_argument("index", type=int)
    c.add_argument("--out", required=True)
    c.add_argument("--frames", help="where the frames are extracted (default: OUT/frames)")
    for name in ("table", "gate"):
        p = sub.add_parser(name)
        p.add_argument("dir")
    p.add_argument("--scan", action="store_true", help="the count under each number changed in turn")
    p.add_argument("--control", type=float, default=tether.CONTROL)
    p.add_argument("--followed", type=float, default=tether.FOLLOWED)
    p.add_argument("--steady", type=float, default=tether.STEADY)
    p.add_argument("--scene", type=float, default=tether.SCENE)
    a = ap.parse_args()
    dict(collect=collect, table=table, gate=gate)[a.what](a)


if __name__ == "__main__":
    for _s in (sys.stdout, sys.stderr):
        _s.reconfigure(encoding="utf-8", errors="replace")
    main()
