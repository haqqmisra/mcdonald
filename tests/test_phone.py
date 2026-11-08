"""Does `mcdonald phone` read a phone's own record of its clip, find it by its key, refuse what it cannot read, and does
the record's zoom go into the scale and the camera stages only where the pictures agree with it?

A synthetic iPhone file, built here: a short clip drawn frame by frame (a blob whose size and offset from the centre
follow a zoom curve -- 6.0, a slip to 4.0 and back -- over a textured sky), encoded by ffmpeg, and a timed-metadata
track added to its moov box the way an iPhone writes one (QuickTime `mebx`, a `keys` table naming
`com.apple.quicktime.live-photo-info`, a 136-byte value a frame in ExifTool's layout), after another `mebx` track with
another key so that the record cannot be found by its number; an illuminance track beside it; the container's tags
(maker, model, lens, 35-mm tag, both creation times) written by ffmpeg as `mdta` keys. Then:

- the record read back with ffmpeg alone, field for field, found by its key;
- no power, with why: a clip with no such track, a copy made again (which drops it), a value of an unknown layout, a
  timed-metadata track that holds other keys only;
- the provenance flags (a file written long after the phone's own time, H.264 from an iPhone, the 35-mm tag against
  the zoom record) and k from the lens and the zoom;
- the check on the pictures (`camera.record_check`) on drawn sizes -- agrees, disagrees, no power -- and on the clip:
  the right record agrees and puts the track on one scale; a record shifted in time disagrees and is not used;
- `run_case`: the phone's clip gets the record, k from it ("the phone's record", not ASSUMED) and the ledger's k
  constrained; `--no-phone` refuses it; a clip with no phone's tags gets no phone row at all (its case as it was).

    python3 tests/test_phone.py        # or: pytest tests/

No video data needed; needs ffmpeg.
"""
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from mcdonald import camera, phone  # noqa: E402

FAIL = []
W, H, FPS = 192, 144, 30
ZOOM0, F35 = 6.0, 26.0          # the record's usual zoom, and the 35-mm tag (at the record's lowest zoom)
SIZE0 = 16.0                    # the blob's width at half its peak at ZOOM0, px
OFFSET = (34.0, -22.0)          # its place from the frame's centre at ZOOM0, px


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def zoom_of(n, shift=0):
    """The drawn zoom at frame n (from 1): 6.0, down to 4.0 over frames 31-40, held, back up over 46-55, 6.0 after."""
    n = n - shift
    if n <= 30:
        return ZOOM0
    if n <= 40:
        return ZOOM0 - 2.0 * (n - 30) / 10.0
    if n <= 45:
        return 4.0
    if n <= 55:
        return 4.0 + 2.0 * (n - 45) / 10.0
    return ZOOM0


N = 80


# ---- the boxes ---------------------------------------------------------------------------------------
def box(kind, *parts):
    body = b"".join(parts)
    return struct.pack(">I4s", 8 + len(body), kind) + body


def full(kind, version=0, flags=0, *parts):
    return box(kind, struct.pack(">I", (version << 24) | flags), *parts)


def mebx_trak(track_id, keys, sizes, offset, n, timescale=600, delta=20):
    """A timed-metadata track: `keys` {local id: key name}; `sizes` each sample's length; all samples in one chunk
    at `offset`."""
    key_boxes = b"".join(box(struct.pack(">I", lid), box(b"keyd", b"mdta", name.encode())) for lid, name in keys.items())
    entry = box(b"mebx", b"\0" * 6, struct.pack(">H", 1), box(b"keys", key_boxes))
    stsd = full(b"stsd", 0, 0, struct.pack(">I", 1), entry)
    stts = full(b"stts", 0, 0, struct.pack(">III", 1, n, delta))
    stsc = full(b"stsc", 0, 0, struct.pack(">IIII", 1, 1, n, 1))
    stsz = full(b"stsz", 0, 0, struct.pack(">II", 0, n), b"".join(struct.pack(">I", s) for s in sizes))
    stco = full(b"stco", 0, 0, struct.pack(">II", 1, offset))
    dinf = box(b"dinf", full(b"dref", 0, 0, struct.pack(">I", 1), full(b"url ", 0, 1)))
    minf = box(b"minf", full(b"nmhd"), dinf, box(b"stbl", stsd, stts, stsc, stsz, stco))
    dur = n * delta
    mdhd = full(b"mdhd", 0, 0, struct.pack(">IIIIHH", 0, 0, timescale, dur, 0x55C4, 0))
    hdlr = full(b"hdlr", 0, 0, b"mhlr", b"meta", b"\0" * 12, b"\0")
    matrix = struct.pack(">9I", 0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000)
    tkhd = full(b"tkhd", 0, 1, struct.pack(">IIIII", 0, 0, track_id, 0, dur * 1), b"\0" * 8,
                struct.pack(">HHHH", 0, 0, 0, 0), matrix, struct.pack(">II", 0, 0))
    return box(b"trak", tkhd, box(b"mdia", mdhd, hdlr, minf))


def add_tracks(path, tracks):
    """Add timed-metadata tracks to a QuickTime file whose moov box is its last: `tracks` [(keys, [sample bytes])], each
    a track of its own, its samples in an mdat after the moov."""
    buf = Path(path).read_bytes()
    i, moov_at = 0, None
    while i + 8 <= len(buf):
        size, kind = struct.unpack(">I4s", buf[i:i + 8])
        if kind == b"moov":
            moov_at = i
        i += size
    assert moov_at is not None and moov_at + struct.unpack(">I", buf[moov_at:moov_at + 4])[0] == len(buf), "moov is not last"
    moov = buf[moov_at:]
    kids, j = [], 8
    while j < len(moov):
        size, kind = struct.unpack(">I4s", moov[j:j + 8])
        kids.append((kind, moov[j:j + size]))
        j += size
    mvhd = next(b for k, b in kids if k == b"mvhd")
    next_id = struct.unpack(">I", mvhd[-4:])[0]

    def build(offsets):
        traks = [mebx_trak(next_id + t, keys, [len(s) for s in samples], offsets[t], len(samples))
                 for t, (keys, samples) in enumerate(tracks)]
        new_mvhd = mvhd[:-4] + struct.pack(">I", next_id + len(tracks))
        body = b"".join(new_mvhd if k == b"mvhd" else b for k, b in kids) + b"".join(traks)
        return box(b"moov", body)

    draft = build([0] * len(tracks))
    data_at = moov_at + len(draft) + 8
    offsets, at = [], data_at
    for _, samples in tracks:
        offsets.append(at)
        at += sum(len(s) for s in samples)
    final = build(offsets)
    assert len(final) == len(draft)
    mdat = box(b"mdat", b"".join(b"".join(s) for _, s in tracks))
    Path(path).write_bytes(buf[:moov_at] + final + mdat)


def value(n, zoom, shift=(0.0, 0.0), extra=56, exposure=0.01):
    """One LivePhotoInfo value in ExifTool's layout, the 56 bytes after it zero."""
    f = [3, exposure, 0, 3, shift[0], shift[1], -2.0, -1.5, zoom, 1.0, 4, 0, -1, 0, 0, 0, 0, 0, 0, 0,
         0.0, 0.0, 0.0, 0.5, n, 7000 + n, 50000 + n]
    return struct.pack(phone.LAYOUT, *f) + b"\0" * extra


def item(local, payload):
    return struct.pack(">II", 8 + len(payload), local) + payload


# ---- the clip --------------------------------------------------------------------------------------
def draw(n, zoom=zoom_of):
    """Frame n: a textured sky zoomed about the centre by zoom(n) / ZOOM0, and the blob on it."""
    s = zoom(n) / ZOOM0
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    cx, cy = W / 2, H / 2                                  # the frame's centre as the package counts it (`camera`)
    u, v = (xx - cx) / s, (yy - cy) / s                    # the sky's own coordinates
    sky = 90 + 12 * np.sin(u / 7.0) * np.cos(v / 9.0) + 8 * np.sin((u + v) / 13.0)
    sig = SIZE0 * s / 2.3548
    bx, by = cx + OFFSET[0] * s, cy + OFFSET[1] * s
    blob = 150 * np.exp(-((xx - bx) ** 2 + (yy - by) ** 2) / (2 * sig ** 2))
    g = sky + blob + np.random.default_rng(n).normal(0, 1.0, (H, W))
    return np.clip(g, 0, 255).astype(np.uint8), (bx, by)


def make_clip(path, tags=True):
    """The drawn clip as an MJPEG QuickTime file, its tags those an iPhone writes (`tags`); returns the true track."""
    frames, track = [], {}
    for n in range(1, N + 1):
        g, xy = draw(n)
        frames.append(g)
        track[n] = xy
    meta = []
    if tags:
        meta = ["-movflags", "use_metadata_tags",
                "-metadata", "com.apple.quicktime.make=Apple", "-metadata", "com.apple.quicktime.model=iPhone 15",
                "-metadata", "com.apple.quicktime.software=18.1",
                "-metadata", "com.apple.quicktime.camera.lens_model=iPhone 15 back camera 6.0mm f/1.6",
                "-metadata", f"com.apple.quicktime.camera.focal_length.35mm_equivalent={F35:g}",
                "-metadata", "com.apple.quicktime.creationdate=2026-01-02T03:04:05-0400",
                "-metadata", "creation_time=2026-01-02T17:00:00Z"]
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(FPS),
                        "-i", "-", "-c:v", "mjpeg", "-q:v", "2", "-pix_fmt", "yuvj420p", *meta, "-f", "mov", str(path)],
                       input=b"".join(f.tobytes() for f in frames), capture_output=True)
    assert r.returncode == 0, r.stderr.decode()
    return track


def phone_clip(path, zoom=zoom_of, value_bytes=136, keys_first=True):
    """A drawn clip with an iPhone's tracks: an orientation track first (another key), the record, the light."""
    track = make_clip(path)
    rec = [item(1, value(n, zoom(n), (0.5 * n, -0.25 * n))[:value_bytes] if value_bytes < 80 else
                value(n, zoom(n), (0.5 * n, -0.25 * n), extra=value_bytes - 80)) for n in range(1, N + 1)]
    orient = [item(1, struct.pack(">h", 90)) for _ in range(N)]
    lux = [item(1, struct.pack(">I", 2_500_000 + 10 * n)) for n in range(1, N + 1)]
    tracks = [({1: "com.apple.quicktime.video-orientation"}, orient)] if keys_first else []
    tracks += [({1: phone.KEY}, rec), ({1: phone.LUX_KEY}, lux)]
    add_tracks(path, tracks)
    return track


# ---- the tests ---------------------------------------------------------------------------------------
def test_the_record_found_by_its_key_and_read(tmp):
    v = tmp / "IMG_0001.MOV"
    phone_clip(v)
    tr = phone.tracks(v)
    check([t["format"] for t in tr][-3:] == ["mebx"] * 3 and tr[-2]["keys"] == {1: phone.KEY},
          "the file's tracks as it describes them: three timed-metadata tracks after the picture, the record's key in the second",
          str([(t["id"], t["format"], t["keys"]) for t in tr]))
    from mcdonald.clip import probe
    info = probe(v)
    idx = phone.stream_of(v, phone.KEY, info["streams"])
    check(idx is not None and info["streams"][idx[0]].get("codec_tag_string") == "mebx" and idx[0] == len(info["streams"]) - 2,
          "found by its key, not by a stream's number: ffmpeg's stream index of the track whose key table names it", str(idx))
    rec = phone.read(v, info)
    z = [r["zoom"] for r in rec["rows"]]
    check(rec["records"] == N and [r["frame"] for r in rec["rows"]] == list(range(1, N + 1)),
          "a record for every frame, numbered as the frames are extracted", f"{rec['records']} records")
    check(max(abs(a - zoom_of(n)) for n, a in zip(range(1, N + 1), z)) < 1e-6
          and max(abs(r["shift_long"] - 0.5 * r["frame"]) for r in rec["rows"]) < 1e-5
          and max(abs(r["shift_short"] + 0.25 * r["frame"]) for r in rec["rows"]) < 1e-5,
          "the zoom (field 8) and the camera's shift (fields 4 and 5) read back as written, through ffmpeg alone")
    check(rec["value_bytes"] == [136] and len(rec["rows"][0]["fields"]) == phone.FIELDS,
          "the 136-byte values read in ExifTool's layout, 27 fields")
    check(abs(rec["zoom"]["least"] - 4.0) < 1e-6 and rec["zoom"]["most"] == ZOOM0 and rec["zoom"]["runs"] == [(31, 40), (46, 55)],
          "the zoom's range and where it moves", str(rec["zoom"]))
    check(abs(rec["rows"][9]["lux"] - 2500.1) < 1e-9, "the light from the illuminance track, in lux (thousandths, big-endian)",
          str(rec["rows"][9]["lux"]))
    out = phone.write_csv(rec, tmp / "img_0001")
    back = phone.read_csv(out)
    check(back == {r["frame"]: r["zoom"] for r in rec["rows"]}, "<tag>_phone.csv holds the zoom on every frame, exactly")
    dx, dy = phone.upright(1.0, 2.0, 270)
    check((dx, dy) == (2.0, -1.0), "a phone held upright (ffmpeg's rotation 270, a quarter turn clockwise for display): the "
                                   "content moves +field 5 across and -field 4 up and down, as the clouds did on the clip the "
                                   "fields were read from")
    check(phone.upright(1.0, 2.0, 0) == (-1.0, -2.0), "with no turn the content moves against the camera's shift")


def test_no_power_with_why(tmp):
    from mcdonald.clip import probe
    plain = tmp / "plain.mov"
    make_clip(plain, tags=False)
    try:
        phone.read(plain)
        check(False, "a clip with no timed-metadata track: no power")
    except phone.NoRecord as e:
        check("no timed-metadata track" in str(e), "a clip with no timed-metadata track: no power, and why", str(e))
    v = tmp / "IMG_0002.MOV"
    phone_clip(v)
    copy = tmp / "copy.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-c:v", "mjpeg", "-q:v", "3", str(copy)], check=True)
    try:
        phone.read(copy)
        check(False, "a copy made again drops the track: no power")
    except phone.NoRecord as e:
        check("no timed-metadata track" in str(e), "a copy made again (ffmpeg to MP4) drops the track: no power", str(e))
    odd = tmp / "IMG_0003.MOV"
    phone_clip(odd, value_bytes=40)
    try:
        phone.read(odd)
        check(False, "values of an unknown layout: no power")
    except phone.NoRecord as e:
        check("unknown layout" in str(e) and "40 bytes" in str(e), "values too short for the layout known: no power, an "
                                                                   "unknown layout, nothing guessed", str(e))
    other = tmp / "IMG_0004.MOV"
    make_clip(other)
    add_tracks(other, [({1: "com.apple.quicktime.video-orientation"}, [item(1, struct.pack(">h", 90))] * N)])
    try:
        phone.read(other)
        check(False, "a timed-metadata track with other keys only: no power")
    except phone.NoRecord as e:
        check("none holds" in str(e), "a timed-metadata track with other keys only: no power, another layout", str(e))
    f = phone.measure(plain, probe(plain))
    check(not f.fields["found"] and f.no_power and f.no_power[0][0] == "phone's record",
          "the stage's own call says no power for the phone's record")
    check(not phone.is_phones(probe(plain)) and phone.is_phones(probe(other)),
          "only a phone's clip (its own tags or a timed-metadata track) is asked for the record")
    bad = phone.unpack(struct.pack(phone.LAYOUT, 3, 0.01, 0, 3, 0, 0, 0, 0, 900.0, 1, 4, 0, -1, 0, 0, 0, 0, 0, 0, 0,
                                   0.0, 0.0, 0.0, 0.5, 0, 0, 0))
    check(bad is None, "a zoom of 900 reads outside the layout known: refused, not read")


def test_provenance_and_k(tmp):
    from mcdonald.clip import probe
    v = tmp / "IMG_0005.MOV"
    phone_clip(v)
    info = probe(v)
    rec = phone.read(v, info)
    p = phone.provenance(v, info, rec)
    check(p["make"] == "Apple" and p["model"] == "iPhone 15" and p["focal_35mm"] == F35 and "6.0mm" in (p["lens"] or ""),
          "the device, the lens and the 35-mm tag, from the container's own keys", json.dumps({k: p[k] for k in ("make", "model", "lens", "focal_35mm")}))
    flags = " | ".join(p["flags"])
    check("written 9.9 h after" in flags, "a file written hours after the phone's own creation time is said to be a copy "
                                          "written later", flags[:160])
    check("35-mm tag (26 mm) is one number" in flags and "39 mm" in flags,
          "the 35-mm tag against the zoom record: the tag at the lowest zoom (4.0), so 39 mm at the usual 6.0")
    k, how, share = phone.k_at(rec, p, W, H, 1)
    want = F35 * ZOOM0 / 4.0 * math.hypot(W, H) / phone.FULL_FRAME_DIAG_MM
    check(abs(k - want) < 1e-6 and "the phone's record" in how and share >= phone.K_SHARE,
          "k from the lens and the zoom: the tag at the lowest zoom, times the zoom at the frame, over the diagonal",
          f"{k:.1f} px/rad, to within {share:.0%}")
    k40 = phone.k_at(rec, p, W, H, 40)[0]
    check(abs(k40 / k - 4.0 / ZOOM0) < 1e-9, "at a frame of the slip, k in the record's zoom there")
    check(phone.k_at(rec, dict(p, focal_35mm=None), W, H, 1) is None, "no 35-mm tag: no k from the record")


def shapes_of(sizes):
    return {n: dict(length_px=float(s), width_px=float(s), cx=0.0, cy=0.0, peak=1.0, pixels=1) for n, s in sizes.items()}


def test_the_check_on_drawn_sizes():
    curve = {n: zoom_of(n) for n in range(1, N + 1)}
    rng = np.random.default_rng(3)
    follow = shapes_of({n: SIZE0 * curve[n] / ZOOM0 * math.exp(rng.normal(0, 0.03)) for n in curve})
    c = camera.record_check(curve, follow, H)
    check(c["verdict"] == "agrees" and abs(c["slope"] - 1) < 0.1 and c["r"] > 0.9, "sizes that follow the record: it agrees",
          c["why"])
    flat = shapes_of({n: SIZE0 * math.exp(rng.normal(0, 0.03)) for n in curve})
    c = camera.record_check(curve, flat, H)
    check(c["verdict"] == "disagrees", "sizes that hold while the record says x1.5: it disagrees", c["why"])
    late = {n: zoom_of(n, shift=25) for n in curve}
    c = camera.record_check(late, follow, H)
    check(c["verdict"] == "disagrees", "a record 25 frames late against its pictures: its slope's interval is wholly "
                                       "outside 1 +- the margin, so it disagrees", c["why"])
    held = {n: ZOOM0 for n in curve}
    c = camera.record_check(held, follow, H)
    check(c["verdict"] == "no power" and "holds" in c["why"], "a record whose zoom holds: no power to check it", c["why"])
    noisy = shapes_of({n: SIZE0 * curve[n] / ZOOM0 * math.exp(rng.normal(0, 0.6)) for n in curve})
    c = camera.record_check(curve, noisy, H)
    check(c["verdict"] == "no power" and "too unsteady" in c["why"], "sizes too noisy to tell: no power", c["why"])
    tiny = shapes_of({n: 3.0 * curve[n] / ZOOM0 for n in curve})
    c = camera.record_check(curve, tiny, H)
    check(c["verdict"] == "no power" and "blur" in c["why"], "an object under the blur at the lowest zoom: no power", c["why"])
    track = {n: (W / 2 + OFFSET[0] * curve[n] / ZOOM0, H / 2 + OFFSET[1] * curve[n] / ZOOM0) for n in curve}
    steps = camera.record_steps(curve, track)
    one = camera.to_one_scale(track, steps, W, H)
    spread = max(np.ptp([p[0] for p in one.values()]), np.ptp([p[1] for p in one.values()]))
    check(len(steps) == 20 and spread < 1e-6, "the record's zoom taken out about the frame's centre: a still point holds still",
          f"{len(steps)} steps, spread {spread:.2g} px")
    no = camera.record_steps(curve, track, dict(verdict="disagrees"))
    check(no and not any(s["applied"] for s in no), "a record the pictures disagree with: no step applied")


def test_the_camera_stage_on_the_clip(tmp):
    from mcdonald import forensics as vf
    v = tmp / "IMG_0006.MOV"
    true = phone_clip(v)
    clip = vf.Clip(v, str(tmp / "frames6"))
    rec = phone.read(v, clip.info)
    curve = phone.zoom_curve(rec)
    f = camera.measure(clip, true, size=SIZE0, record=curve, out=str(tmp / "img_0006"), tag="img_0006")
    rc = f.fields["record"]
    check(rc["check"]["verdict"] == "agrees" and rc["used"], "the right record: the blob's size follows it, and it is used",
          rc["check"]["why"])
    import csv
    with open(f.files[0], newline="") as fh:
        rows = list(csv.DictReader(fh))
    one = [(float(r["x_first_scale"]), float(r["y_first_scale"])) for r in rows]
    raw = [(float(r["x"]), float(r["y"])) for r in rows]
    check(one and max(np.ptp([p[0] for p in one]), np.ptp([p[1] for p in one])) < 0.05
          and np.ptp([p[0] for p in raw]) > 10,
          "the track on one scale: the blob, still in the sky, holds still once the record's zoom is out",
          f"raw spread {np.ptp([p[0] for p in raw]):.1f} px, one scale {np.ptp([p[0] for p in one]):.3f} px")
    check("phone's record" in f.result and any("own record" in n for n in f.notes), "the stage says the record and its check")
    wrong = {n: ZOOM0 * 4.0 / zoom_of(n) for n in curve}       # a field that moves the other way: another layout's
    g = camera.measure(clip, true, size=SIZE0, record=wrong)
    check(g.fields["record"]["check"]["verdict"] == "disagrees" and not g.fields["record"]["used"]
          and any(t == "phone's record" for t, _ in g.no_power),
          "a record that is not this clip's zoom: the pictures disagree, it is said so and not used",
          g.fields["record"]["check"]["why"])


def test_run_case(tmp):
    from mcdonald import stages
    from mcdonald.report import Case
    v = tmp / "IMG_0007.MOV"
    true = phone_clip(v)
    trk = tmp / "track.csv"
    trk.write_text("frame,x,y\n" + "".join(f"{n},{x:.3f},{y:.3f}\n" for n, (x, y) in true.items()))
    only = ["ingest", "track", "scale", "kinematics", "camera"]
    case, clip, files = stages.run_case(str(v), track=str(trk), workdir=str(tmp / "frames7"), out=str(tmp / "case7"),
                                        only=only, size=SIZE0, say=lambda *a: None)
    ing, sf = case.stages["ingest"]["fields"], case.stages["scale"]["fields"]
    check(ing.get("phone", {}).get("found") and any(str(f).endswith("_phone.csv") for f in files),
          "run: a phone's clip has its record read at ingest, into <tag>_phone.csv")
    check(sf["k_px_per_rad"] and "the phone's record" in sf["k_from"] and "ASSUMED" not in sf["k_from"]
          and sf["phone_check"]["verdict"] == "agrees",
          "run: k from the phone's record, checked on the pictures, sourced and not assumed", sf["k_from"][:120])
    led = {r["symbol"]: r for r in case.ledger()}
    check(led["k"]["status"] == "constrained" and "the phone's record" in led["k"]["by"],
          "the unknowns ledger: k constrained, by the phone's record")
    check(any(n == stages.PHONE_NOTE for n in case.notes), "run: the kinematics stage's track put on one scale first, and said")
    cam = case.stages["camera"]["fields"]
    check(cam["record"]["used"] and cam["k_px_per_deg"] and abs(cam["k_px_per_deg"] - sf["k_px_per_rad"] * math.pi / 180) < 1e-9,
          "run: the camera stage takes the zoom on every frame and the same k")
    check(any(c.startswith("mcdonald camera ") and "--phone" in c for c in case.commands),
          "run: the camera stage's command says --phone")
    prefix = next(str(f)[:-len("_phone.csv")] for f in files if str(f).endswith("_phone.csv"))
    case.write(prefix)
    case_json = f"{prefix}_case.json"
    again, _ = stages.add_known(case_json, workdir=str(tmp / "frames7"), say=lambda *a: None, range_m=500.0)
    s2 = again.stages["scale"]["fields"]
    check(abs(s2["k_px_per_rad"] - sf["k_px_per_rad"]) < 1e-9 and "the phone's record" in s2["k_from"]
          and again.stages["kinematics"]["fields"].get("v_px_per_s") == case.stages["kinematics"]["fields"].get("v_px_per_s"),
          "a range given afterwards: the phone's k and the one-scale track again, the rate as before")
    case2, _, _ = stages.run_case(str(v), track=str(trk), workdir=str(tmp / "frames7"), out=str(tmp / "case7b"), only=only,
                                  size=SIZE0, say=lambda *a: None, no_phone=True)
    i2, s3 = case2.stages["ingest"]["fields"], case2.stages["scale"]["fields"]
    check(i2["phone"]["refused"] and not i2["phone"]["found"] and s3["k_px_per_rad"] is None
          and any(c.startswith("mcdonald run ") and "--no-phone" in c for c in case2.commands),
          "run --no-phone: the record refused and said so, no k from it")
    plain = tmp / "plain7.mov"
    make_clip(plain, tags=False)
    case3, _, _ = stages.run_case(str(plain), track=str(trk), workdir=str(tmp / "frames7p"), out=str(tmp / "case7p"),
                                  only=only, size=SIZE0, say=lambda *a: None)
    st = case3.stages
    check("phone" not in st["ingest"]["fields"] and not st["ingest"]["no_power"] and "phone_k" not in st["scale"]["fields"]
          and "phone_check" not in st["scale"]["fields"] and "record" not in st["camera"]["fields"]
          and not any("-phone" in c for c in case3.commands) and not any(n == stages.PHONE_NOTE for n in case3.notes),
          "a clip with no phone's tags: no phone row anywhere, its case as it was")


def main():
    if not shutil.which("ffmpeg"):
        print("  SKIP  no ffmpeg on this machine")
        return 0
    root = Path(tempfile.mkdtemp(prefix="phone_"))
    try:
        for name, fn in list(globals().items()):
            if name.startswith("test_") and callable(fn):
                print(name)
                if fn.__code__.co_argcount:
                    d = root / name
                    d.mkdir()
                    fn(d)
                else:
                    fn()
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print(f"\n{len(FAIL)} failed" if FAIL else "\nall passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
