"""The labelled infrared set's boxes as tracks: Svanström et al. (2021), converted once (ROADMAP.md 0.5, the controls harness).

    python3 tools/controls/svanstrom_labels.py                 # writes $MCDONALD_DATA/svanstrom2021/tracks/
    python3 tools/controls/svanstrom_labels.py --out DIR       # somewhere else
    python3 tools/controls/svanstrom_labels.py --show FILE.mat # what a label file holds

The set (the reference-data folder's svanstrom2021/: 365 thermal clips, 320x256 at exactly 30 frames a second, about 10 s
each; 79 bird, 74 airplane, 157 drone and 55 helicopter clips) keeps its labels as MATLAB `groundTruth` objects (Video
Labeler, R2019b): MCOS class instances that `scipy.io.loadmat` does not decode and Octave cannot read. `filewrapper` reads
them with scipy alone. The object sits in the file's `__function_workspace__`, a MAT stream of its own whose FileWrapper
cell array carries the saved object, a struct with `LabelData`: one row per video frame, an [x y w h] box (or none, or
several) per class. Every label file has exactly one row per frame of its video.

What is written, once (the tests and `tools/controls/run_set.py` read it, never this script):

- `tracks/<clip>_o<k>.csv`, one per labelled object of the clip's own class seen on MIN_FRAMES frames or more: frame,
  x_px, y_px, w_px, h_px -- the box's centre in the package's pixel coordinates and its size. Frames are the package's,
  1-based (`clip.py`: ffmpeg's numbering, t = (n - 1) / fps): row i of LabelData (0-based) is frame i + 1. The first run of
  2026-10-19 wrote them 0-based, a frame early, which on a track whose labels follow the platform's 2-3 Hz wobble put a
  periodic centring error into the aperture; it was stopped and run again.
- The centre is (x + w/2 - 1.5, y + h/2 - 1.5): (x, y) is the box's first pixel, 1-based, and on 48 sampled tracks the
  spatial convention (- 1) left the contrast centroid a median 0.5 px up and to the left of the centre; with - 1.5, the
  centres sit 0.5-2 px from the centroid on 46 of 48 (two distant helicopters 3-5 px).
- `tracks/index.tsv`: every labelled object, written or not (one shorter than MIN_FRAMES is listed with no track), with
  its class, the set's distance bin (CLOSE, MEDIUM, DISTANT: "distant" is under 5 px wide), its frames, its median box,
  how many boxes a frame of the clip held (a flock is not mistaken for one bird), its polarity read from its pixels and
  the clip's other tracks, which the background apertures keep clear of (`flicker --avoid`).

Frames with several boxes of the clip's class are linked into objects by nearest neighbour: a box joins the object whose
last box is closest, within LINK_PX and GAP_FRAMES; each object is its own track. Two things the set does that the tracks
carry, and a reader should know:

- **The camera follows its target** on a pan-and-tilt platform (a FLIR Breach PTQ-136, a Boson 320). The object stays
  near the middle and the scene moves behind it.
- **The labels were made differently by class** (the air-and-sea survey, 2026-11-07): the median share of a track's frames
  on an exact straight line while the object moves -- key frames with straight lines between -- is 86 % on birds, 95 % on
  airplanes, 5 % on drones and 5 % on helicopters (drones and helicopters labelled frame by frame, the boxes wobbling
  0.2-1 px at about 2-2.6 Hz with the image). On bird and airplane tracks the aperture follows a straight line between key
  frames, not the object: any difference between birds and drones in centring or jitter may be the labels'.
- **A fresh picture on every frame**: wherever the object's box changes clearly from frame to frame it changes on every
  frame; the encoder skips only faint, low-contrast blocks. Before 2026-10-29 (M3) `flicker.pictures` read these clips as
  about 24.7 pictures a second with 18 % held and lowered the band's top to about 9.9 Hz; the harness's table keeps each
  track's reading, so a return of that misreading shows.

The polarity is read from the pixels, never from the class: the sign of (the box's mean - the median of a 4-px ring round
it) on every 5th labelled frame; dark where under half are bright (4 birds, 2 drones and 11 helicopters on 2026-10-19).

Needs ffmpeg (the polarity reads frames) and openpyxl (the distance bins are in the set's spreadsheet). Run it through the
job scheduler on a shared machine: it decodes all 365 clips, about five minutes on one CPU."""
import argparse
import csv
import io
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tests"))

import reference_data  # noqa: E402

CLASSES = ("AIRPLANE", "BIRD", "DRONE", "HELICOPTER")
LINK_PX = 25.0       # px: a box further than this from every object's last box starts an object of its own ...
GAP_FRAMES = 15      # ... as does one more than this many frames after the object's last box
MIN_FRAMES = 60      # flicker's own floor (2 s at 30 frames a second): a shorter object is listed, and no track is written
CENTRE = 1.5         # px taken from x + w/2 (and y + h/2): 1-based first pixel to the package's centre (the docstring)
RING_PX = 4          # px: the ring the polarity is read against, round the box
EVERY = 5            # the polarity is read on every this-many-th labelled frame
W, H = 320, 256      # the infrared clips' frames


def dataset(root=None):
    """The set's Data folder in the reference-data folder."""
    return Path(root or reference_data.root()) / "svanstrom2021" / "Drone-detection-dataset" / "Data"


def filewrapper(path):
    """The FileWrapper cell array of a MATLAB `groundTruth` .mat (an MCOS object), read with scipy alone.

    `loadmat` gives the object's bytes as `__function_workspace__`: a MAT-file of its own, with no 128-byte header and its
    version and endian marks at the front. Given a header, scipy's own version-5 reader reads its one variable, a struct
    whose `MCOS` field holds the cell array the object's properties are kept in."""
    import scipy.io as sio
    from scipy.io.matlab._mio5 import MatFile5Reader
    ws = sio.loadmat(path)["__function_workspace__"].tobytes()
    fake = b"MATLAB 5.0 MAT-file".ljust(116) + b"\x00" * 8 + ws[0:4] + ws[8:]
    r = MatFile5Reader(io.BytesIO(fake), squeeze_me=False, struct_as_record=True)
    r.initialize_read()
    r.mat_stream.seek(128)
    hdr, _ = r.read_var_header()
    v = r.read_var_array(hdr, process=True)
    return v[0, 0]["MCOS"][0]["arr"].ravel()


def label_data(path):
    """The groundTruth's LabelData as {class: [array (k, 4) of [x y w h] boxes, one per video frame]}."""
    arr = filewrapper(path)
    gt = next(c for c in arr if getattr(c, "dtype", None) is not None and c.dtype.names
              and "LabelData" in c.dtype.names)[0, 0]
    ld = gt["LabelData"].ravel()
    return {c: [np.asarray(r[c], float).reshape(-1, 4) for r in ld] for c in CLASSES if c in ld.dtype.names}


def link(boxes):
    """Per-frame boxes -> objects [{frame index (0-based): box}], each box joining the object whose last box is nearest,
    within LINK_PX and GAP_FRAMES; one object takes at most one box a frame."""
    objs = []
    for n, bb in enumerate(boxes):
        free = list(range(len(objs)))
        for b in bb:
            c = b[:2] + b[2:] / 2
            best, bd = None, LINK_PX
            for k in free:
                last = objs[k][max(objs[k])]
                d = float(np.hypot(*(last[:2] + last[2:] / 2 - c)))
                if d < bd and n - max(objs[k]) <= GAP_FRAMES:
                    best, bd = k, d
            if best is None:
                objs.append({n: b})
            else:
                objs[best][n] = b
                free.remove(best)
    return objs


def bins(data):
    """{clip: distance bin} for the infrared clips, from the set's Video_dataset_description.xlsx."""
    import openpyxl
    ws = openpyxl.load_workbook(data / "Video_dataset_description.xlsx", read_only=True).worksheets[0]
    out = {}
    for row in ws.iter_rows(values_only=True, min_row=2):
        if row[0] == "IR" and row[2] is not None:
            out[f"IR_{row[1]}_{int(row[2]):03d}"] = (row[3] or "").strip()
    return out


def probe(video):
    """(frames, frame rate as ffprobe gives it) of a clip, its packets counted."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=nb_read_packets,r_frame_rate", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True, check=True)
    rate, n = r.stdout.strip().split(",")
    return int(n), rate


def frames(video):
    """Every frame of an infrared clip as grey levels, (n, H, W)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W).astype(float)


def bright_share(F, rows):
    """The share of every EVERY-th labelled frame on which the box is brighter than the ring round it (`rows`: frame,
    x_px, y_px, w_px, h_px, the frame 1-based); 1.0 where none can be read."""
    signs = []
    for frame, x, y, bw, bh in rows[::EVERY]:
        n = frame - 1
        if n >= len(F):
            continue
        x0, x1 = int(max(0, x - bw / 2 - RING_PX)), int(min(F.shape[2], x + bw / 2 + RING_PX + 1))
        y0, y1 = int(max(0, y - bh / 2 - RING_PX)), int(min(F.shape[1], y + bh / 2 + RING_PX + 1))
        yy, xx = np.mgrid[y0:y1, x0:x1]
        inbox = (abs(xx - x) <= bw / 2) & (abs(yy - y) <= bh / 2)
        P = F[n, y0:y1, x0:x1]
        if (~inbox).sum() < 4 or inbox.sum() < 1:
            continue
        signs.append(np.sign(P[inbox].mean() - np.median(P[~inbox])))
    return float(np.mean(np.array(signs) > 0)) if signs else 1.0


def clip_rows(mat, data, dist):
    """The index rows and the tracks of one clip: ([row], {track name: [(frame, x, y, w, h)]})."""
    clip = mat.name.replace("_LABELS.mat", "")
    cls = clip.split("_")[1]
    video = mat.with_name(clip + ".mp4")
    nfr, rate = probe(video)
    ld = label_data(mat)
    boxes = ld[cls]
    others = sum(sum(len(b) for b in ld[c]) for c in ld if c != cls)
    per = [len(b) for b in boxes]
    objs = sorted(link(boxes), key=len, reverse=True)
    rows, tracks = [], {}
    for k, o in enumerate(objs):
        fr = sorted(o)
        wh = np.array([o[n][2:] for n in fr])
        row = dict(clip=clip, cls=cls, distance=dist.get(clip, ""), object=f"o{k}",
                   video=str(video.relative_to(data.parent.parent)), frames=nfr, rate=rate, label_rows=len(boxes),
                   first=fr[0] + 1, last=fr[-1] + 1, labelled=len(fr), max_boxes=max(per), multi_frames=sum(p > 1 for p in per),
                   objects=len(objs), other_class_boxes=others, w_med=round(float(np.median(wh[:, 0])), 3),
                   h_med=round(float(np.median(wh[:, 1])), 3), track="", bright_share="", dark="", avoid="")
        if len(fr) >= MIN_FRAMES:
            name = f"{clip}_o{k}"
            tracks[name] = [(n + 1, o[n][0] + o[n][2] / 2 - CENTRE, o[n][1] + o[n][3] / 2 - CENTRE, o[n][2], o[n][3]) for n in fr]
            row["track"] = f"tracks/{name}.csv"
        rows.append(row)
    if tracks:
        F = frames(video)
        for row in rows:
            if row["track"]:
                share = bright_share(F, tracks[Path(row["track"]).stem])
                row.update(bright_share=f"{share:.2f}", dark=int(share < 0.5),
                           avoid=",".join(r["track"] for r in rows if r["track"] and r is not row))
    return rows, tracks


def write_track(path, clip, cls, obj, mat, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        f.write(f"# {clip} {cls} object {obj}: Svanstrom et al. 2021 groundTruth boxes ({mat}), centre = (x + w/2 - {CENTRE:g}, "
                f"y + h/2 - {CENTRE:g}) in the package's pixels, frames 1-based; written by tools/controls/svanstrom_labels.py\n")
        w = csv.writer(f)
        w.writerow(["frame", "x_px", "y_px", "w_px", "h_px"])
        for n, x, y, bw, bh in rows:
            w.writerow([n, f"{x:.2f}", f"{y:.2f}", f"{bw:g}", f"{bh:g}"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", help="where tracks/ goes (default: the reference-data folder's svanstrom2021/)")
    ap.add_argument("--show", metavar="MAT", help="print what one label file's FileWrapper holds, and stop")
    a = ap.parse_args(argv)
    if a.show:
        for i, c in enumerate(filewrapper(a.show)):
            if isinstance(c, np.ndarray) and c.dtype == object:
                print(i, "cell", c.shape, [x.shape for x in c.ravel()[:5]])
            elif isinstance(c, np.ndarray) and c.dtype.names:
                print(i, "struct", c.shape, c.dtype.names)
            elif isinstance(c, np.ndarray) and c.size > 1 and c.dtype.kind in "fiu" and not (c.dtype == np.uint8 and i == 0):
                print(i, c.dtype, c.shape, c.ravel()[:8])
        return 0
    data = dataset()
    out = Path(a.out) if a.out else data.parent.parent
    (out / "tracks").mkdir(parents=True, exist_ok=True)
    dist = bins(data)
    rows = []
    for mat in sorted((data / "Video_IR").glob("IR_*_LABELS.mat")):
        got, tracks = clip_rows(mat, data, dist)
        for r in got:
            if r["track"]:
                write_track(out / r["track"], r["clip"], r["cls"], r["object"], mat.name, tracks[Path(r["track"]).stem])
        rows += got
        print(got[0]["clip"], got[0]["cls"], got[0]["distance"], got[0]["frames"], "objects", len(got),
              "tracks", sum(bool(r["track"]) for r in got), file=sys.stderr, flush=True)
    with open(out / "tracks" / "index.tsv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    n = sum(bool(r["track"]) for r in rows)
    print(f"{len(rows)} labelled objects in {len({r['clip'] for r in rows})} clips; {n} tracks of {MIN_FRAMES} frames or more "
          f"written to {out / 'tracks'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
