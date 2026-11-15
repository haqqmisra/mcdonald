#!/usr/bin/env python3
"""The controls' table of `mcdonald rank` (docs/method.md section 64): known objects through `mcdonald batch`, matched to
what is known about them, on the same axes as a batch's objects.

The known objects go through `mcdonald batch` exactly as the corpus did (the same snapshot of the code, Find on every
frame, the 40-frame rule, Follow from Find's marks, every stage of `run`), one batch folder a population:

    mcdonald batch --list ir.txt --out ctl/ir            # the labelled infrared set's 365 clips
    mcdonald batch --list galileo.txt --out ctl/galileo  # the five Galileo flyers
    mcdonald batch --list aaro.txt --out ctl/aaro        # AARO's resolved cases, the segments the blind run opened

and this script matches each batch's objects to the known objects (`rank.match`: on the known track's box, plus 2 px,
on 10 frames or more and on half the frames both have) and writes the table:

    python3 tools/rank_controls.py --ir ctl/ir --galileo ctl/galileo --aaro ctl/aaro --out rank_controls.tsv

- **The labelled infrared set** (Svanström, Alonso-Fernandez & Englund 2021; the data folder's `svanstrom2021/tracks/`):
  each labelled object's boxes, frame by frame. Its four classes are the scored classes.
- **The Galileo flyers** (the data folder's `galileo/`, tracks in tests/golden/flyerN_paper_track.csv, source frames,
  `galileo_clips.csv` giving each clip's first source frame): birds on another camera (640x512, 60 frames a second), a
  check population, not a scored class (five objects).
- **AARO's resolved cases** (the data folder's `aaro/blind/` files, `tests/golden/aaro_blind.json` saying which of each
  run's objects were on the described object): balloons, birds, lanterns, aircraft and one wind-borne object, a check
  population (AARO's answers are an imperfect reference, and no class reaches the 19 a p-value of 0.05 needs).

Run it through Slurm: it reads every case of three batch folders. It writes the table and, beside it, `<out>.md`: how
many known objects of each class Find found and Follow followed (completeness on the controls), and what was left over.
"""
import argparse
import csv
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

from mcdonald import rank  # noqa: E402
from mcdonald.forensics import read_track  # noqa: E402

GOLDEN = HERE / "tests" / "golden"
FLYER_HALF = 3.0      # px: the flyers' tracks are centres with no box; a bird of a few pixels, its half-width (stated)
AARO_HALF = 3.0       # px: the blind run's tracks are the same tracker's centres on the same video (stated)
AARO_CLASS = {"birds": "bird", "migratory birds": "bird", "balloon": "balloon", "foil balloon": "balloon",
              "balloon cluster": "balloon", "sky lanterns": "lantern", "not anomalous (wind-borne)": "wind-borne",
              "aircraft": "aircraft", "aircraft + sensor artefact": "aircraft",
              "not anomalous (aircraft-like)": "aircraft-like (weak)", "not anomalous (unidentified)": "unidentified (weak)"}


def ir_truths(data):
    """The labelled set's objects with a track: [dict(video, name, cls, track={frame: (x, y, w/2, h/2)})]."""
    base = Path(data) / "svanstrom2021"
    out = []
    with open(base / "tracks" / "index.tsv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if not r["track"]:
                continue
            tr = {}
            with open(base / r["track"], newline="", encoding="utf-8") as g:
                for t in csv.DictReader(ln for ln in g if not ln.startswith("#")):
                    tr[int(t["frame"])] = (float(t["x_px"]), float(t["y_px"]), float(t["w_px"]) / 2, float(t["h_px"]) / 2)
            out.append(dict(video=r["clip"], name=f"{r['clip']}_{r['object']}", cls=r["cls"].lower(), track=tr,
                            distance=r["distance"]))
    return out


def galileo_truths(offset=0):
    """The five flyers' golden tracks in the clips' own frames (source frame - first source frame + offset)."""
    out = []
    with open(GOLDEN / "galileo_clips.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            p = GOLDEN / f"flyer{r['flyer']}_paper_track.csv"
            t = read_track(p)
            f0 = int(r["src_frame0"])
            out.append(dict(video=Path(r["clip"]).stem, name=f"flyer{r['flyer']}", cls="bird",
                            track={n - f0 + offset: (x, y, FLYER_HALF, FLYER_HALF) for n, (x, y) in t.items()}))
    return out


def aaro_truths(data):
    """Each blind run's objects that were on the described object, with their tracks from the blind case files."""
    rec = json.loads((GOLDEN / "aaro_blind.json").read_text(encoding="utf-8"))
    blind = Path(data) / "aaro" / "blind"
    out = []
    for case in rec["cases"]:
        for file, objs in case["runs"]["first"]["files"].items():
            with zipfile.ZipFile(blind / file) as z, tempfile.TemporaryDirectory() as td:
                for k, o in objs.items():
                    if not o.get("on_object"):
                        continue
                    name = next((n for n in z.namelist() if f"/{k}/" in n and n.endswith("_autotrack.csv")), None)
                    if name is None:
                        continue
                    p = Path(td) / "t.csv"
                    p.write_bytes(z.read(name))
                    t = read_track(p)
                    video = Path(name).name[:-len("_autotrack.csv")].upper()
                    out.append(dict(video=video, name=f"{case['case']}:{file}:{k}", cls=AARO_CLASS.get(case["aaro_class"], case["aaro_class"]),
                                    track={n: (x, y, AARO_HALF, AARO_HALF) for n, (x, y) in t.items()}))
    return out


def completeness(truths, matched, recs):
    by = {}
    for t in truths:
        by.setdefault(t["cls"], [0, 0])[0] += 1
    for t, r, on, sh in matched:
        by[t["cls"]][1] += 1
    return by


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ir", help="the labelled infrared set's batch folder")
    ap.add_argument("--galileo", help="the Galileo flyers' batch folder")
    ap.add_argument("--aaro", help="AARO's resolved cases' batch folder")
    ap.add_argument("--data", default=None, help="the reference data folder (default $MCDONALD_DATA)")
    ap.add_argument("--out", required=True, help="the controls' table to write (TSV)")
    ap.add_argument("--masks", action="store_true", help="find each track on the overlay or a redaction block (`rank.add_masks`: "
                                                         "reads 40 frames of each case from its video), as the corpus's are")
    a = ap.parse_args(argv)
    data = a.data or os.environ["MCDONALD_DATA"]
    rows, lines = [], ["# The controls' table: what was matched", ""]
    for name, folder, truths_of, source, scored in (
            ("labelled infrared set", a.ir, lambda: ir_truths(data), "svanstrom2021", True),
            ("Galileo flyers", a.galileo, None, "galileo", False),
            ("AARO's resolved cases", a.aaro, lambda: aaro_truths(data), "aaro", False)):
        if not folder:
            continue
        head, recs = rank.records(folder, say=print)
        if a.masks:
            with tempfile.TemporaryDirectory(prefix="rank-masks-", dir=os.environ.get("TMPDIR")) as td:
                rank.add_masks(recs, td, say=print)
        if truths_of is None:                     # the flyers: the frame offset the tracks agree with best
            best = None
            for off in (-1, 0, 1, 2):
                tr = galileo_truths(off)
                m, left = rank.match(recs, tr)
                if best is None or sum(x[2] for x in m) > best[0]:
                    best = (sum(x[2] for x in m), off, tr, m, left)
            _, off, truths, matched, left = best
            lines.append(f"Galileo flyers: the golden tracks agree best at a frame offset of {off}.")
        else:
            truths = truths_of()
            matched, left = rank.match(recs, truths)
        rows += rank.control_rows(matched, source, scored)
        comp = completeness(truths, matched, recs)
        lines += [f"## {name} ({folder})", "", f"{len(recs)} batch objects; {len(truths)} known objects with a track; "
                  f"{len(matched)} matched; {len(left)} batch objects on no known object.", "",
                  "| class | known | found and followed | share |", "|---|---:|---:|---:|"]
        lines += [f"| {c} | {n} | {k} | {k / n:.0%} |" for c, (n, k) in sorted(comp.items())]
        d = {}
        for c in rank.control_rows(matched, source, scored):
            if c["defect"]:
                d[c["defect"]] = d.get(c["defect"], 0) + 1
        lines += ["", "Matched objects with a defect (kept in the table, left out of their class): "
                  + (", ".join(f"{k} {v}" for k, v in sorted(d.items())) or "none"), ""]
    rank.write_controls(a.out, rows)
    Path(a.out).with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {a.out} ({len(rows)} rows) and {Path(a.out).with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
