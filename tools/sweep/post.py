"""The beat pass's objects followed and measured: every object of one video linked from Find's own marks and put
through the flicker stage. ROADMAP.md 0.3, objective 9 (`post.sbatch` of the whole-video pass, 2026-10-12/14).

    python3 tools/sweep/post.py ID           # in the pass's working folder, after every window of ID is proposed

Runs `collect.py` (objects/ID.tsv), then for each object, 30 frames either side of where it was seen:
`mcdonald mark --link` from the marks Find proposed for it (cases/ID/obj/oNN/, beat/ID/oNN_mark.json), and `mcdonald
flicker` on the track that links (beat/ID/oNN_flicker.json; dark objects measured dark). An object already measured is
left as it is, so a stopped run starts again where it stopped. The command is $MCDONALD, else `mcdonald`."""
import csv
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDGE = 30          # frames either side of where Find saw the object


def run(cmd, out, err):
    with open(out, "w", encoding="utf-8") as o, open(err, "w", encoding="utf-8") as e:
        return subprocess.run(cmd, stdout=o, stderr=e, stdin=subprocess.DEVNULL).returncode


def main(argv=None):
    pid = (argv or sys.argv[1:])[0]
    M = shlex.split(os.environ.get("MCDONALD", "mcdonald"))
    clips = {r[0]: r for r in csv.reader(open("clips.tsv", encoding="utf-8"), delimiter="\t")}
    video, frames = clips[pid][1], int(clips[pid][2])
    subprocess.run([sys.executable, str(HERE / "collect.py"), pid], check=True)
    os.makedirs(f"beat/{pid}", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    for row in csv.reader(open(f"objects/{pid}.tsv", encoding="utf-8"), delimiter="\t"):
        obj, tag, rank, a, b, pol = row[0], row[1], int(row[2]), int(row[3]), int(row[4]), row[5]
        done = Path(f"beat/{pid}/{obj}_flicker.json")
        if done.exists() and done.stat().st_size:
            continue
        n0, n1 = max(1, a - EDGE), min(frames, b + EDGE)
        p = next(q for q in json.load(open(f"prop/{pid}/{tag}.json", encoding="utf-8"))["results"]["proposals"] if q["rank"] == rank)
        sets = [f"--set=object@{f}={x},{y}" for f, (x, y) in p["mark_at"].items()]
        case = f"cases/{pid}/obj/{obj}"
        run(M + ["mark", video, "--no-window", "--link", "--json", "--n0", str(n0), "--n1", str(n1), "--out", case, *sets,
                 "--why", f"proposal {rank} of {pid} window {tag} ({pol}, frames {a}-{b}); whole-video beat pass: every "
                          "long-lived object is followed"],
            f"beat/{pid}/{obj}_mark.json", f"logs/{pid}_{obj}_mark.err")
        track = next(iter(sorted(Path(case).glob("*_autotrack.csv"))), None)
        if track is None:
            print(f"{pid} {obj}: no link", flush=True)
            continue
        run(M + ["flicker", video, "--track", str(track), "--n0", str(n0), "--n1", str(n1), *(["--dark"] if pol == "dark" else []),
                 "--out", case, "--procs", "2", "--json"],
            f"beat/{pid}/{obj}_flicker.json", f"logs/{pid}_{obj}_flicker.err")
        print(f"{pid} {obj} done", flush=True)
    print(f"{pid} post done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
