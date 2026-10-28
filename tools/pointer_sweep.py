#!/usr/bin/env python3
"""The k-from-slew sweep, re-run with the clip's zoom states (ROADMAP 0.4; docs/method.md §17, "Zoom states").

Two passes over a list of clips, one Slurm array task a clip (tools/pointer_sweep.sbatch):

- **zoom**, every clip in the list: `mcdonald zoom`, its bursts of blank frames and the scale across each. The
  ratios at the measured steps are the ladder question: if the MTS-B steps between fixed fields, the ratios of every
  clip fall on a short list (x2.00 on PR27 and PR057a; x5.8-5.9 on PR057a and PR144 so far).
- **slew**, the clips whose pointer and scene have been read (a row with a _north.csv and a _layers.csv):
  `mcdonald slew --zoom`, so windows are cut at every burst, claims are compared within a zoom state, and across a
  measured step the ratio of the states' c is set against the imagery's.

The list is a TSV, one clip a row: `tag  video  [north.csv  layers.csv  [pixel-aspect]]` ("-" for none). Nothing
here reads another project's files: the list names the videos and series, wherever they are.

    python3 tools/pointer_sweep.py one LIST.tsv I OUT      # row I (from 0): OUT/<tag>/{zoom,slew}.json
    python3 tools/pointer_sweep.py collect OUT             # OUT/summary.md and OUT/summary.json
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path


def rows(path):
    out = []
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        f = line.split("\t") + ["-"] * 4
        out.append(dict(tag=f[0], video=f[1], north=None if f[2] == "-" else f[2],
                        layers=None if f[3] == "-" else f[3], aspect=None if f[4] in ("-", "") else f[4]))
    return out


def run(cmd, to):
    """A mcdonald command with --json, its envelope saved to `to`; what it said to a person goes to the job's log."""
    print("+ " + " ".join(cmd), flush=True)
    p = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    Path(to).write_text(p.stdout)
    return p.returncode


def one(args):
    r = rows(args.list)[args.i]
    out = Path(args.out) / r["tag"]
    out.mkdir(parents=True, exist_ok=True)
    mc = [sys.executable, "-m", "mcdonald.cli"]
    zj = out / "zoom.json"
    if not zj.exists() or args.again:
        run(mc + ["zoom", r["video"], "--out", str(out), "--json"], zj)
    if r["north"] and r["layers"]:
        z = sorted(out.glob("*_zoom.json"))
        cmd = mc + ["slew", r["video"], "--north", r["north"], "--layers", r["layers"], "--out", str(out), "--json"]
        cmd += ["--zoom", str(z[0])] if z else ["--no-zoom"]
        if r["aspect"]:
            cmd += ["--pixel-aspect", r["aspect"]]
        run(cmd, out / "slew.json")
    return 0


def results(path):
    try:
        return json.loads(Path(path).read_text())["results"]
    except (OSError, ValueError, KeyError):
        return None


def fmt(v, f=".0f"):
    return "" if v is None or (isinstance(v, float) and not math.isfinite(v)) else format(v, f)


def collect(args):
    out = Path(args.out)
    clips, bursts, states, checks = [], [], [], []
    for d in sorted(p for p in out.iterdir() if p.is_dir() and p.name != "logs"):
        z, s = results(d / "zoom.json"), results(d / "slew.json")
        if z is None:
            clips.append(dict(tag=d.name, zoom=None))
            continue
        clips.append(dict(tag=d.name, zoom=True, n_bursts=len(z.get("bursts", [])), slew=s is not None))
        for b in z.get("bursts", []):
            bursts.append(dict(tag=d.name, t_s=b["t_s"], verdict=b["verdict"], s=b.get("s"), zncc=b.get("zncc"),
                               prominence=b.get("prominence"), why=b.get("why")))
        if s is None:
            continue
        for st in s.get("states", []):
            states.append(dict(tag=d.name, state=st["state"], t_s=st["t_s"], magnification=st["magnification"],
                               chain=st["chain"], claims=st["windows_claiming"], windows=len(st["windows"]),
                               c=st["c_px_per_deg"], c_err=st["c_err_px_per_deg"], floor=st["c_at_least_px_per_deg"],
                               below_floor=st["c_below_a_floor"]))
        for c in s.get("zoom_checks", []):
            checks.append(dict(tag=d.name, **c))
    (out / "summary.json").write_text(json.dumps(dict(clips=clips, bursts=bursts, states=states, checks=checks),
                                                 indent=1))
    L = [f"# Pointer sweep with zoom states: {len(clips)} clips", ""]
    steps = sorted((b for b in bursts if b["verdict"] == "step"), key=lambda b: b["s"])
    L += [f"## Measured zoom steps ({len(steps)} of {len(bursts)} bursts; {sum(b['verdict'] == 'no step' for b in bursts)} "
          f"no step, {sum(b['verdict'] == 'unknown' for b in bursts)} unknown)", "",
          "| clip | t (s) | scale | ZNCC | prominence (MADs) |", "|---|---|---|---|---|"]
    L += [f"| {b['tag']} | {b['t_s'][0]:.1f}-{b['t_s'][1]:.1f} | x{b['s']:.3f} | {fmt(b['zncc'], '.2f')} | "
          f"{fmt(b['prominence'], '.1f')} |" for b in steps]
    L += ["", "## Slew, by zoom state", "", "| clip | state | t (s) | magnification | chain | windows claiming | c (px/deg) "
          "| floor (px/deg) |", "|---|---|---|---|---|---|---|---|"]
    L += [f"| {r['tag']} | {r['state']} | {r['t_s'][0]:.1f}-{r['t_s'][1]:.1f} | x{r['magnification']:.3f} | {r['chain']} | "
          f"{r['claims']} of {r['windows']} | {fmt(r['c'])}{' +- ' + fmt(r['c_err']) if r['c'] else ''}"
          f"{' (under a floor)' if r['below_floor'] else ''} | {fmt(r['floor'])} |" for r in states]
    L += ["", "## Across measured steps", "", "| clip | states | kind | c ratio or c expected | imaged | agree |",
          "|---|---|---|---|---|---|"]
    for c in checks:
        if not c.get("compared"):
            L.append(f"| {c['tag']} | {c['states'][0]}-{c['states'][1]} | not compared | | | {c.get('why', '')} |")
        elif c["kind"] == "claims":
            L.append(f"| {c['tag']} | {c['states'][0]}-{c['states'][1]} | claims | x{c['c_ratio']:.3f} | "
                     f"x{c['imaged_ratio']:.3f} | {'yes' if c['agree'] else 'NO'} |")
        else:
            L.append(f"| {c['tag']} | {c['states'][0]}-{c['states'][1]} | claim vs floor | {c['c_expected']:.0f} vs >= "
                     f"{c['c_at_least']:.0f} | x{c['imaged_ratio']:.3f} | {'yes' if c['agree'] else 'NO'} |")
    missing = [c["tag"] for c in clips if c["zoom"] is None]
    if missing:
        L += ["", f"No zoom result: {', '.join(missing)}"]
    (out / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("one")
    a.add_argument("list")
    a.add_argument("i", type=int)
    a.add_argument("out")
    a.add_argument("--again", action="store_true", help="make zoom.json again even if it is there")
    b = sub.add_parser("collect")
    b.add_argument("out")
    args = ap.parse_args()
    return one(args) if args.cmd == "one" else collect(args)


if __name__ == "__main__":
    raise SystemExit(main())
