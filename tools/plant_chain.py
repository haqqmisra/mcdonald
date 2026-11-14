"""One planted video through the chain, timed and scored: the unit of the planting pilot (ROADMAP.md 0.6, objective 4).

    python3 tools/plant_chain.py VIDEO --n0 1 --n1 400 --draw 20 --seed 1 --out DIR --link --flicker
    python3 tools/plant_chain.py VIDEO --n0 1 --n1 400 --draw 6 --fill 42 --fill-at-once 42 --out DIR   # crowding
    sbatch tools/plant_chain.sbatch VIDEO --n0 1 --n1 400 --draw 20 --seed 1 --out DIR --link --flicker

`mcdonald plant` writes the planted video and its truth table; this puts it through what a search does and holds each
step against the table:

1. **Find** (`propose.find`, as `mcdonald look --propose` runs it) on the planted video, on the control (the same
   stretch encoded the same way with nothing planted) and, with --original, on the video's own frames. Each planted
   object: on the list or not, at which place, how strong (`plant.recovered`). Each other row of the planted video's
   list: on the control's list too (a feature of the scene, or clutter), or new. The control's list against the
   original's: what a second encode alone changes (the biology survey's 12 %, IDEAS.md B22).
2. **The link** (--link), from the marks Find's row would place, as the window's "This is it" does: how many of the
   object's frames it follows, how far from the truth, how many frames off it.
3. **`flicker`** (--flicker) on each linked track of 60 frames or more: a beat called or not, and at what frequency,
   against the light the object was given. A constant object is the null: any beat called on it is a false alarm.
4. **`run`** (--run N) on the first N linked objects: the report's label.

Every step is timed, wall and CPU (this process and its children), into `<stem>_chain.json` beside the truth table:
the cost model reads those. Until `mcdonald batch` can take a planted video and its truth table as a unit, this is the
pilot's driver; it is a tool, not part of the package, and nothing here is tuned on what it finds.

Frames go to --work (default: the storage folder, MCDONALD_HOME) and are removed when the unit is done unless
--keep-frames. Process pools follow the CPUs this process may use, so under Slurm the allocation decides.
"""
import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import autolink, plant, propose  # noqa: E402
from mcdonald import forensics as vf  # noqa: E402
from mcdonald.progress import cpus  # noqa: E402

KEEP = 400          # rows of Find's list that are kept and scored (`tools/find_rank.py` keeps as many)
SHOWN = 30          # the rows `look --propose --more` and the window's "Show more" give


class Clock:
    """Wall and CPU seconds of each step: the CPU time is this process's and its finished children's (a pool's
    workers and ffmpeg count once they have ended, which every step here waits for)."""

    def __init__(self):
        self.steps = {}

    def cpu(self):
        t = os.times()
        return t.user + t.system + t.children_user + t.children_system

    def step(self, name):
        clock = self

        class _Step:
            def __enter__(self):
                self.w, self.c = time.time(), clock.cpu()

            def __exit__(self, *a):
                d = clock.steps.setdefault(name, dict(wall_s=0.0, cpu_s=0.0, times=0))
                d["wall_s"] += time.time() - self.w
                d["cpu_s"] += clock.cpu() - self.c
                d["times"] += 1
        return _Step()


def find(video, work, procs, clock, name, n0=None, n1=None):
    """(clip, masks, Find's rows as dicts with their Proposal) for a video, the frames extracted into `work`."""
    with clock.step(f"{name}: frames"):
        clip = vf.Clip(video, Path(work) / Path(video).stem, n0, n1)
    with clock.step(f"{name}: masks"):
        masks = vf.static_masks(clip)
    with clock.step(f"{name}: find"):
        props = propose.find(clip, masks, procs=procs, keep=KEEP)
    return clip, masks, props


def as_rows(props, shift=0):
    """Find's rows as `look --propose --json` gives them, with the track's frames moved by `shift`."""
    out = []
    for p in props:
        d = p.to_dict()
        if shift:
            d["track"] = {str(int(n) + shift): xy for n, xy in d["track"].items()}
        out.append(d)
    return out


def same_rows(a, b):
    """How many of list a's rows are on a row of list b (`plant.on_path`, either way round): [index in b or None]."""
    tb = [({int(n): xy for n, xy in r["track"].items()}, r) for r in b]
    out = []
    for r in a:
        ta = {int(n): xy for n, xy in r["track"].items()}
        hit = next((j for j, (t, q) in enumerate(tb, 1)
                    if plant.on_path(ta, t, float(q.get("size_px") or 0.0)) or plant.on_path(t, ta, float(r.get("size_px") or 0.0))), None)
        out.append(hit)
    return out


def link_one(clip, masks, prop, truth_track, procs, cache, clock):
    """The link from a row's own marks, held against the planted path: dict(frames, first, last, size, dark, on --
    linked frames within 6 px of the truth --, off -- more than 12 px from it --, median_px, covered -- the share of
    the object's frames that are linked and within 6 px --, said)."""
    with clock.step("planted: link"):
        last = list(autolink.link_from_marks(clip, prop.seeds(), masks=masks, procs=procs, cache=cache))[-1]
    tr = last.track
    shared = [n for n in tr if n in truth_track]
    d = np.array([np.hypot(tr[n][0] - truth_track[n][0], tr[n][1] - truth_track[n][1]) for n in shared]) if shared else np.zeros(0)
    return last, dict(frames=len(tr), first=min(tr, default=None), last=max(tr, default=None), size=last.size, dark=last.dark,
                      shared=len(shared), on=int((d <= 6.0).sum()), off=int((d > 12.0).sum()),
                      beyond=len(tr) - len(shared),                    # linked frames on which the object was not there
                      median_px=float(np.median(d)) if len(d) else None,
                      covered=float((d <= 6.0).sum() / max(len(truth_track), 1)), said=last.say[:300])


def flicker_one(clip, track, dark, procs, clock):
    """`flicker` on one linked track, as `run` asks it: dict(beats, hz, amplitude, source, strong, finding) or
    dict(error)."""
    from mcdonald import flicker
    quiet = lambda *a, **k: None
    with clock.step("planted: flicker"):
        try:
            f = flicker.measure(clip, {"object": track}, dark=bool(dark), out=None, say=quiet, procs=procs)
        except Exception as e:                              # a unit goes on: the row says what happened
            return dict(error=f"{type(e).__name__}: {e}"[:300])
    F = f.fields
    b = (F.get("beat") or {}).get("object") or {}
    c = (F.get("curves") or {}).get("object") or {}
    return dict(beats=F.get("beats"), hz=b.get("hz"), double_hz=b.get("double_hz"), amplitude=b.get("amplitude"),
                source=b.get("source"), whole_hz=c.get("hz"), whole_amplitude=c.get("amplitude"), stands=c.get("stands"),
                strong=F.get("strong"), frames=F.get("frames"), resolution_hz=F.get("resolution_hz"),
                finding=str(F.get("finding") or "")[:300], no_power=[list(x) for x in f.no_power][:4])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--draw", type=int, default=0)
    ap.add_argument("--kinds", default="dot")
    ap.add_argument("--contrast")
    ap.add_argument("--sigma")
    ap.add_argument("--speed")
    ap.add_argument("--polarity", default="both")
    ap.add_argument("--at-once", type=int, default=plant.AT_ONCE)
    ap.add_argument("--life", type=int, default=plant.LIFE)
    ap.add_argument("--apart", type=float, default=plant.APART)
    ap.add_argument("--fill", type=int, default=0, help="more objects round the drawn ones, which stay as they were: the crowding measurement")
    ap.add_argument("--fill-at-once", type=int, default=plant.AT_ONCE)
    ap.add_argument("--fill-life", type=int, default=plant.LIFE)
    ap.add_argument("--fill-contrast")
    ap.add_argument("--plants", help="the objects, as a list in a file, in place of a draw")
    ap.add_argument("--twin", action="append", default=[], metavar="CSV",
                    help="a recorded track of a real object in this stretch (frame, x, y; with a `letter` column, one track a "
                         "letter): a copy of it -- its path moved elsewhere in the frame, its contrast and width -- is planted too")
    ap.add_argument("--no-none", action="store_true", help="do not write the control (another seed of the same stretch has it)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--work", help="where the frames go (default: the storage folder)")
    ap.add_argument("--original", action="store_true", help="Find on the video's own frames too")
    ap.add_argument("--no-control", action="store_true", help="do not run Find on the control")
    ap.add_argument("--link", action="store_true")
    ap.add_argument("--link-most", type=int, default=1000, help="link at most this many found objects")
    ap.add_argument("--flicker", action="store_true")
    ap.add_argument("--run", type=int, default=0, metavar="N", help="the whole `run` on the first N linked objects")
    ap.add_argument("--keep-frames", action="store_true")
    ap.add_argument("--procs", type=int, default=None)
    args = ap.parse_args()

    from mcdonald import storage
    clock = Clock()
    t_start = time.time()
    procs = args.procs if args.procs is not None else cpus()
    video, tag, _ = vf.resolve(args.video)
    out = Path(args.out)
    work = Path(args.work) if args.work else storage.frames()
    nums = lambda s: tuple(float(v) for v in s.split(","))
    drawn = dict(k=args.draw, kinds=tuple(args.kinds.split(",")), polarity=args.polarity, at_once=args.at_once, life=args.life,
                 apart=args.apart)
    for name in ("contrast", "sigma", "speed"):
        if getattr(args, name):
            drawn[name] = nums(getattr(args, name))
    if args.fill:
        drawn["fill"] = dict(k=args.fill, kinds=("dot",), polarity=args.polarity, at_once=args.fill_at_once, life=args.fill_life,
                             apart=args.apart, **({"contrast": nums(args.fill_contrast)} if args.fill_contrast else {}))
    plants = None
    if args.plants:
        d = json.loads(Path(args.plants).read_text())
        plants = d if isinstance(d, list) else d["plants"]
    print(f"{procs} process{'es' if procs != 1 else ''}; frames in {work}", flush=True)
    twins = []
    if args.twin:
        with clock.step("twins: the recorded objects' look"):
            twins = twins_of(args.twin, video, work, args.n0, args.n1)
        drawn["extra"] = twins
        for t in twins:
            print(f"  a copy of the recorded object {t['of']}: {'dark' if t['dark'] else 'bright'}, {t['contrast']:.0f} DN, "
                  f"sigma {t['sigma']:.2f} px, on its path moved elsewhere", flush=True)
    with clock.step("plant"):
        made = plant.make(video, args.n0, args.n1, plants, out, tag, args.seed, None if plants is not None else drawn,
                          null=not args.no_none, say=print)
    truth = made["truth_data"]
    st = truth["stretch"]
    stem = Path(made["truth"]).name[:-len("_truth.json")]
    result = dict(video=Path(video).name, tag=tag, stretch=st, seed=args.seed, procs=procs, host=os.uname().nodename,
                  mcdonald=truth["mcdonald"], settings={k: truth["settings"][k] for k in ("bit_rate", "bit_rate_made", "types_same", "bframes", "gop")},
                  overlay=truth["overlay"], levels=truth["levels"], planted=len(truth["plants"]), skipped=truth["skipped"],
                  scene_speed=(truth.get("scene") or {}).get("speed_px_per_frame"),
                  scene_held_still=(truth.get("scene") or {}).get("held_still"))
    dirs = []

    # 1. Find, on the planted video, the control and the original
    clip, masks, props = find(made["planted"], work, procs, clock, "planted")
    dirs.append(clip.dir)
    rows = as_rows(props)
    (out / f"{stem}_rows.json").write_text(json.dumps(rows))          # Find's list, kept: the tables hold it against any control
    rec = plant.recovered(truth, rows)
    for r in rec["plants"]:
        r["shown"] = bool(r["found"] and r["rank_alone"] <= SHOWN)       # among the 30 rows a person is shown, the other plants' rows aside
    result["find"] = dict(rows=len(rows), found=rec["found"], strengths=_strengths(rows))
    real = dict(plants=[dict(id=t["id"], kind="recorded", contrast=t["contrast"], sigma=t["sigma"], dark=t["dark"],
                             track=t["recorded"], frames_on=len(t["recorded"])) for t in twins])
    if twins:                                               # the real objects themselves, on the planted video's list
        result["recorded"] = dict(planted=_brief(plant.recovered(real, rows)))
    print(f"Find: {rec['found']} of {rec['planted']} planted objects on the list of {len(rows)} ({result['find']['strengths']})", flush=True)
    control = None
    if made["none"] and not args.no_control:
        cclip, cmasks, cprops = find(made["none"], work, procs, clock, "control")
        dirs.append(cclip.dir)
        control = as_rows(cprops)
        (out / f"{stem}_control_rows.json").write_text(json.dumps(control))
        phantom = plant.recovered(truth, control)            # the planted paths held against a video they are not in: chance
        in_control = same_rows([rows[o["rank"] - 1] for o in rec["others"]], control)
        for o, j in zip(rec["others"], in_control):
            o["in_control"] = j
        result["control"] = dict(rows=len(control), strengths=_strengths(control), phantoms_found=phantom["found"],
                                 others=len(rec["others"]), others_in_control=sum(j is not None for j in in_control),
                                 others_new=[o for o in rec["others"] if o["in_control"] is None][:60])
        if twins:
            result["recorded"]["control"] = _brief(plant.recovered(real, control))
        print(f"control: {len(control)} rows; {phantom['found']} planted paths 'found' in it by chance; of the planted video's "
              f"{len(rec['others'])} other rows, {result['control']['others_in_control']} are in the control too", flush=True)
    if args.original:
        oclip, omasks, oprops = find(video, work, procs, clock, "original", st["n0"], st["n1"])
        orig = as_rows(oprops, shift=1 - st["n0"])
        dirs.append(oclip.dir)
        result["original"] = dict(rows=len(orig), strengths=_strengths(orig))
        if twins:
            result["recorded"]["original"] = _brief(plant.recovered(real, orig))
        if control is not None:                              # what a second encode alone does to Find's list
            again = same_rows(orig, control)
            back = same_rows(control, orig)
            top = lambda rows_, hit, k: dict(n=len(rows_[:k]), kept=sum(j is not None for j in hit[:k]))
            result["original"].update(
                in_control=sum(j is not None for j in again), control_in_original=sum(j is not None for j in back),
                top30=top(orig, again, SHOWN), top8=top(orig, again, 8),
                fair_or_strong=dict(n=sum(r["strength"] != "weak" for r in orig),
                                    kept=sum(j is not None for r, j in zip(orig, again) if r["strength"] != "weak")),
                rows=[dict(rank=i, strength=r["strength"], score=r["score"], frames=r["frames"], in_control=j)
                      for i, (r, j) in enumerate(zip(orig, again), 1)][:60])
            print(f"original: {len(orig)} rows, {result['original']['in_control']} of them in the control too "
                  f"(top 30: {result['original']['top30']})", flush=True)

    # 2-4. the link, flicker and run, for the planted objects Find has
    by_id = {p["id"]: p for p in truth["plants"]}
    cache, linked = {}, 0
    for r in rec["plants"]:
        if not (args.link and r["found"]) or linked >= args.link_most:
            continue
        prop = props[r["rank"] - 1]
        path_ = {int(n): tuple(xy) for n, xy in by_id[r["id"]]["track"].items()}
        try:
            last, r["link"] = link_one(clip, masks, prop, path_, procs, cache, clock)
        except Exception as e:
            r["link"] = dict(error=f"{type(e).__name__}: {e}"[:300])
            continue
        linked += 1
        if args.flicker and len(last.track) >= 60:
            r["flicker"] = flicker_one(clip, last.track, last.dark, procs, clock)
        if args.run and linked <= args.run and last.track:
            r["run"] = run_one(made["planted"], clip, last, out / f"run-{r['id']}", work, clock)
    result["plants"] = rec["plants"]
    result["others"] = len(rec["others"])
    result["timings"] = clock.steps
    result["wall_s"] = time.time() - t_start
    result["frames"] = st["frames"]
    (out / f"{stem}_chain.json").write_text(json.dumps(result, indent=1, default=plant._plain))
    print(f"wrote {out / (stem + '_chain.json')}", flush=True)
    for name, d in clock.steps.items():
        print(f"  {name:22s} {d['wall_s']:8.1f} s wall  {d['cpu_s']:8.1f} s CPU  x{d['times']}", flush=True)
    if not args.keep_frames:
        for d in dirs:
            shutil.rmtree(d, ignore_errors=True)
    return 0


def twins_of(files, video, work, n0, n1):
    """A copy of each recorded object for `plant.make`: its path as recorded (placed elsewhere by `plant.place_recorded`),
    its contrast, width and polarity as `planted.look` reads them on the video's own frames (the polarity the one that
    gives the larger contrast). Frames are the planted video's: the stretch begins at the I frame at or before n0."""
    import csv
    from mcdonald import planted
    st = plant.settings(video, n0, n1)
    a = st["n0"]
    clip = vf.Clip(video, Path(work) / Path(video).stem, a, st["n1"])
    out = []
    for k, f in enumerate(files):
        rows = list(csv.DictReader(ln for ln in open(f, encoding="utf-8") if ln.strip() and not ln.startswith("#")))
        xc, yc = next((x, y) for x, y in (("x_px", "y_px"), ("x", "y")) if x in rows[0])
        tracks = {}
        for r in rows:
            if r[xc] not in ("", "nan") and a <= int(float(r["frame"])) <= st["n1"]:
                tracks.setdefault(r.get("letter") or "", {})[int(float(r["frame"]))] = (float(r[xc]), float(r[yc]))
        for j, (letter, tr) in enumerate(sorted(tracks.items())):
            if len(tr) < 3:
                continue
            bright, dark = planted.look(clip, tr, False), planted.look(clip, tr, True)
            con, sig, _ = dark if dark[0] > bright[0] else bright
            out.append(dict(id=9001 + 100 * k + j, kind="twin", of=f"{Path(f).stem}{' ' + letter if letter else ''}", shape="point",
                            sigma=float(sig), contrast=float(con), dark=bool(dark[0] > bright[0]), light=dict(kind="constant"),
                            group=(9001 + 100 * k) if len(tracks) > 1 else None,
                            path=dict(kind="recorded", place="auto", track={str(n - a + 1): list(xy) for n, xy in sorted(tr.items())}),
                            first=min(tr) - a + 1, last=max(tr) - a + 1,
                            recorded={str(n - a + 1): list(xy) for n, xy in sorted(tr.items())}))
    return out


def _brief(rec):
    return [dict(id=r["id"], found=r["found"], rank=r["rank"], strength=r["strength"], score=r["score"], px=r["px"], shared=r["shared"])
            for r in rec["plants"]]


def _strengths(rows):
    return {s: sum(r["strength"] == s for r in rows) for s in ("strong", "fair", "weak")}


def run_one(video, clip, link, out, work, clock):
    """`mcdonald run` on one linked track (its report's label and the beat's row), as a command of its own."""
    import subprocess
    out.mkdir(parents=True, exist_ok=True)
    prefix = out / Path(video).stem.lower()
    autolink.save_track(clip, link, str(prefix))
    cmd = [sys.executable, "-m", "mcdonald.cli", "run", str(video), "--track", f"{prefix}_autotrack.csv", "--size", f"{link.size:g}",
           *(["--dark"] if link.dark else []), "--n0", str(min(link.track)), "--n1", str(max(link.track)), "--workdir", str(clip.dir),
           "--out", str(out), "--json"]
    with clock.step("planted: run"):
        r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace")
    try:
        d = json.loads(r.stdout)
    except ValueError:
        return dict(error=(r.stderr or "")[-300:], exit=r.returncode)
    res = d.get("results") or {}
    beat = next((c for c in res.get("checklist") or [] if c.get("key") == "beat"), {})
    return dict(label=(res.get("conclusion") or {}).get("label"), headline=(res.get("conclusion") or {}).get("headline"),
                beat=dict(answer=beat.get("answer"), said=beat.get("said")), planted=(d.get("clip") or {}).get("planted"),
                no_power=len(d.get("no_power") or []), exit=d.get("exit"))


if __name__ == "__main__":
    sys.exit(main())
