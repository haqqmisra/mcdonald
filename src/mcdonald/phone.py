"""`mcdonald phone` -- what a phone wrote down about its own clip: the zoom and the camera's shift on every frame,
and what the file says of the device, the lens, the software and its own history.

An iPhone's video carries timed-metadata tracks beside the picture (QuickTime `mebx`: Core Media metadata, a sample
a frame). One of them, keyed `com.apple.quicktime.live-photo-info`, holds 27 numbers a frame. Apple documents none
of them. ExifTool unpacks them (`VfVVf6c4lCCcclf4Vvv`, little-endian, the first 80 bytes of each value) and names
them no more than "LivePhotoInfo"; what they mean was worked out on one clip that cannot be shared (a witness's,
2026-11-01), against its own pictures:

- field 1, the exposure time (s);
- fields 4 and 5, the camera's shift since the first frame, in the coded picture's pixels at the zoom of the
  moment (4 along the coded picture's long side, 5 along its short side; the picture's content moves the other
  way): the clouds in the picture slid by about what field 5 stepped;
- fields 6 and 7, a shift of the frame's own;
- field 8, the video zoom factor of the camera the phone presents (on a two-camera iPhone 2.0 is the main lens at
  the "1x" its screen shows, 1.0 the ultra-wide): the object's height over the horizon followed it through the
  clip's zoom slips, at a slope near 1 and r near 1.

So the zoom on every frame is in the file. The file's one lens number, its 35-mm equivalent focal length, is a
single value for the whole clip; on that clip it fitted the record's lowest zoom, where the record sat well above
it on most of the frames. A reader who takes the tag at face value is out by the ratio in every angle.

`read` finds the track by its key in the file's own key table (the `keys` box of the `mebx` sample description),
not by a stream's number, and takes the bytes with ffmpeg alone (`-map 0:<n> -c copy -f data`): no ExifTool. Each
record is checked against the one layout known (its length, a zoom inside the range a phone has, an exposure
under a second); a record of any other shape is NO POWER, an unknown layout, never a guess. A clip with no such
track -- any camera but an iPhone, and a copy made again by an app or a converter, which drop the track -- is NO
POWER for these rows, with why.

What the record gives the rest of the package:

- `scale`: k from the lens and the zoom (`k_at`): the tag's focal length, taken at the record's lowest zoom, times
  the record's zoom at the frame over that zoom, over the picture's diagonal (the 35-mm equivalent is a diagonal
  angle, CIPA DC-008). Sourced as "the phone's record", with its error: the share between the diagonal's reading and
  the width's, and the crop a stabiliser takes, at the least `K_SHARE`.
- `camera`: the zoom on every frame, so that a zoom inside the track is known rather than inferred, the track and
  the object's size put on one scale. Checked on the clip's own pictures first (`camera.record_check`): where the
  record's zoom moves, the object's size must follow it; a record that disagrees with its pictures is said so and
  not used.

`provenance` reads what the container says: the maker, the model, the software, the lens, the 35-mm tag, the
two creation times (the file's own and the phone's), the codec, and any encoder that wrote it again.
"""
import argparse
import json
import math
import re
import struct
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

KEY = "com.apple.quicktime.live-photo-info"
LUX_KEY = "com.apple.quicktime.scene-illuminance"
# ExifTool's unpack of the value (Image::ExifTool::QuickTime, 'live-photo-info'), little-endian: 27 fields from the
# first 80 bytes. The one clip read carries 136 bytes a value; the 56 after the 80 are not read by anyone yet.
LAYOUT = "<IfII6f4bi2B2bi4fI2H"
FIELDS = 27
VALUE_MIN = struct.calcsize(LAYOUT)               # 80 bytes
ZOOM_FIELD, SHIFT_LONG, SHIFT_SHORT, STEP_LONG, STEP_SHORT, EXPOSURE_FIELD = 8, 4, 5, 6, 7, 1
ZOOM_RANGE = (0.5, 30.0)                          # a phone's video zoom factor, outside which the layout is not this one
EXPOSURE_MAX = 1.0                                # s: a video frame's exposure is under a second
# The 35-mm equivalent focal length is the lens's angle across the picture's diagonal, as on a 36 x 24 mm frame
# (43.27 mm across): CIPA DC-008. A reader who spreads it over the width (36 mm) gets k 4.7 % higher on a 16:9 picture;
# a stabiliser's crop (an iPhone's standard video stabilisation crops some of each side) narrows the field the tag was
# written for. K_SHARE, the share k may be off by, is the larger of the two readings' difference and this floor: a
# JUDGEMENT from the one clip read, where the tag at the record's lowest zoom agreed within it with two measurements
# free of the tag (the picture's keystone as the phone turned, and the object's path fitted with k free).
FULL_FRAME_DIAG_MM = math.hypot(36.0, 24.0)
K_SHARE = 0.10
# provenance: a creation time the container wrote this long after the phone's own is a copy written later
COPY_AFTER_S = 120.0


class NoRecord(Exception):
    """The clip has no phone record that can be read: the reason is the message."""


# ---- the file's boxes ----------------------------------------------------------------------------
def _boxes(buf, start=0, end=None):
    """(type, payload start, payload end) of each box in buf[start:end]."""
    end = len(buf) if end is None else end
    i = start
    while i + 8 <= end:
        size, kind = struct.unpack(">I4s", buf[i:i + 8])
        head = 8
        if size == 1:
            if i + 16 > end:
                return
            size = struct.unpack(">Q", buf[i + 8:i + 16])[0]
            head = 16
        elif size == 0:
            size = end - i
        if size < head or i + size > end:
            return
        yield kind, i + head, i + size
        i += size


def _child(buf, start, end, kind):
    return next(((a, b) for k, a, b in _boxes(buf, start, end) if k == kind), None)


def _moov(path):
    """The bytes of the file's moov box, read without the rest: None where there is none."""
    with open(path, "rb") as f:
        f.seek(0, 2)
        size_all = f.tell()
        at = 0
        while at + 8 <= size_all:
            f.seek(at)
            head = f.read(16)
            if len(head) < 8:
                return None
            size, kind = struct.unpack(">I4s", head[:8])
            if size == 1 and len(head) >= 16:
                size = struct.unpack(">Q", head[8:16])[0]
            elif size == 0:
                size = size_all - at
            if size < 8:
                return None
            if kind == b"moov":
                f.seek(at)
                return f.read(size)
            at += size
    return None


def _mebx_keys(buf, a, b):
    """The keys of a `mebx` sample description: {local id: key name}."""
    out = {}
    # the sample entry: 6 reserved bytes and a data reference index, then its boxes
    keys = _child(buf, a + 8, b, b"keys")
    if not keys:
        return out
    for kind, ka, kb in _boxes(buf, *keys):
        local = struct.unpack(">I", kind)[0]
        keyd = _child(buf, ka, kb, b"keyd")
        if keyd and keyd[1] - keyd[0] >= 4:
            out[local] = buf[keyd[0] + 4:keyd[1]].decode("utf-8", "replace")
    return out


def tracks(path):
    """Every track of a QuickTime or MP4 file as the file describes it: [{id, handler, format, keys}], `id` the
    track's own number (ffprobe's stream id), `format` its sample description's four letters, `keys` {local id: key}
    for a timed-metadata (`mebx`) track. [] where the file has no moov box this reader can walk."""
    try:
        buf = _moov(path)
    except OSError:
        return []
    if not buf:
        return []
    out = []
    for kind, a, b in _boxes(buf, 8):
        if kind != b"trak":
            continue
        row = dict(id=None, handler=None, format=None, keys={})
        tkhd = _child(buf, a, b, b"tkhd")
        if tkhd:
            v = buf[tkhd[0]]
            off = tkhd[0] + (4 + 16 if v == 1 else 4 + 8)
            row["id"] = struct.unpack(">I", buf[off:off + 4])[0]
        mdia = _child(buf, a, b, b"mdia")
        if mdia:
            hdlr = _child(buf, *mdia, b"hdlr")
            if hdlr:
                row["handler"] = buf[hdlr[0] + 8:hdlr[0] + 12].decode("latin-1")
            stsd = None
            minf = _child(buf, *mdia, b"minf")
            stbl = _child(buf, *minf, b"stbl") if minf else None
            stsd = _child(buf, *stbl, b"stsd") if stbl else None
            if stsd:
                for fk, fa, fb in _boxes(buf, stsd[0] + 8, stsd[1]):
                    row["format"] = fk.decode("latin-1")
                    if fk == b"mebx":
                        row["keys"] = _mebx_keys(buf, fa, fb)
                    break
        out.append(row)
    return out


def stream_of(path, key=KEY, streams=None):
    """(ffmpeg's stream index, the key's local id) of the track whose key table holds `key`, found by the key and
    not by a stream's number: None where no track holds it. `streams` is ffprobe's list (`clip.info["streams"]`),
    read here where not given; a track is matched to its stream by the track's own id."""
    for t in tracks(path):
        local = next((i for i, k in t["keys"].items() if k == key), None)
        if local is None:
            continue
        if streams is None:
            r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
                               capture_output=True, encoding="utf-8", errors="replace")
            streams = json.loads(r.stdout or "{}").get("streams", []) if r.returncode == 0 else []
        for s in streams:
            sid = s.get("id")
            try:
                sid = int(str(sid), 0)
            except (TypeError, ValueError):
                continue
            if sid == t["id"]:
                return int(s["index"]), local
    return None


# ---- the samples ---------------------------------------------------------------------------------
def samples(path, index):
    """The samples of stream `index`, as [(time in s, bytes)], with ffmpeg alone: the bytes by a stream copy
    (`-map 0:<n> -c copy -f data`), each sample's time and length from ffprobe's packets."""
    data = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", f"0:{index}", "-c", "copy", "-f", "data", "-"],
                          capture_output=True)
    if data.returncode != 0:
        raise NoRecord(f"ffmpeg could not copy stream {index} out: "
                       + (data.stderr.decode(errors="replace").strip().splitlines() or ["no reason given"])[-1])
    pk = subprocess.run(["ffprobe", "-v", "error", "-select_streams", str(index), "-show_entries", "packet=pts_time,size",
                         "-of", "csv=p=0", str(path)], capture_output=True, encoding="utf-8", errors="replace")
    rows = []
    for line in pk.stdout.split():
        t, _, n = line.partition(",")
        try:
            rows.append((float(t), int(n)))
        except ValueError:
            continue
    raw, out, at = data.stdout, [], 0
    if sum(n for _, n in rows) != len(raw):
        raise NoRecord(f"stream {index}'s {len(raw)} bytes are not its {len(rows)} samples' "
                       f"{sum(n for _, n in rows)}: the samples cannot be told apart")
    for t, n in rows:
        out.append((t, raw[at:at + n]))
        at += n
    return out


def items(sample):
    """The items of one metadata sample, [(local key id, value bytes)]: each a 4-byte length (itself counted), a
    4-byte local key id, the value (big-endian heads, as every QuickTime box)."""
    out, i = [], 0
    while i + 8 <= len(sample):
        n, local = struct.unpack(">II", sample[i:i + 8])
        if n < 8 or i + n > len(sample):
            break
        out.append((local, sample[i + 8:i + n]))
        i += n
    return out


def unpack(value):
    """One LivePhotoInfo value as its 27 fields (ExifTool's numbering, from 0), or None where it is too short for
    the layout known, or reads outside it (a zoom no phone has, an exposure of a second or more, a NaN)."""
    if len(value) < VALUE_MIN:
        return None
    f = struct.unpack(LAYOUT, value[:VALUE_MIN])
    z, e = f[ZOOM_FIELD], f[EXPOSURE_FIELD]
    if not (math.isfinite(z) and ZOOM_RANGE[0] <= z <= ZOOM_RANGE[1]) or not (math.isfinite(e) and 0 < e < EXPOSURE_MAX):
        return None
    if not all(math.isfinite(f[i]) for i in (SHIFT_LONG, SHIFT_SHORT, STEP_LONG, STEP_SHORT)):
        return None
    return f


# ---- the record ----------------------------------------------------------------------------------
def _frame_of(t, start, fps):
    """The frame (counted from 1, as the frames are extracted) shown at time t."""
    return int(round((t - start) * fps)) + 1


def upright(dl, ds, rotation):
    """The picture's content moves (dx, dy), in the upright picture's pixels, for a camera shift of (dl, ds) along
    the coded picture's long and short sides. The content moves against the camera; the display rotation turns
    the coded axes into the upright picture's. `rotation` as `clip.probe` gives it, ffmpeg's anticlockwise degrees: 270
    is a picture turned a quarter clockwise for display (x = H - 1 - v, y = u), a phone held upright, and was read on the
    one clip: the clouds moved by +field 5 across and -field 4 up and down. The others follow from the turn, and no clip
    has checked them."""
    r = int(round(rotation or 0)) % 360
    cu, cv = -dl, -ds                                 # the content's move along the coded axes
    if r == 270:
        return -cv, cu
    if r == 90:
        return cv, -cu
    if r == 180:
        return -cu, -cv
    return cu, cv


def read(path, info=None):
    """The phone's record of a clip: a dict with `rows` [{frame, t_s, zoom, shift_long, shift_short, step_long,
    step_short, exposure_s, lux, fields}], the stream it came from, and `zoom` (the range and the frames it moves
    on). `info` is `clip.probe`'s (the streams, the frame rate, the rotation), read here where not given. Raises
    NoRecord with why, where there is none to read."""
    if info is None:
        from .clip import probe
        info = probe(path)
    streams = info.get("streams") or []
    fps = float(info["fps"])
    video = info.get("stream") or {}
    start = float(video.get("start_time") or 0.0)
    if Path(path).suffix.lower() not in (".mov", ".mp4", ".m4v", ".qt") and not tracks(path):
        raise NoRecord(f"{Path(path).name} is not a QuickTime or MP4 file, the only kind a phone's record is kept in")
    found = stream_of(path, KEY, streams)
    if found is None:
        mebx = [s for s in streams if (s.get("codec_tag_string") or "") == "mebx"]
        if mebx:
            raise NoRecord(f"the file has {len(mebx)} timed-metadata track{'s' if len(mebx) != 1 else ''} (mebx), and none "
                           f"holds {KEY}: another phone's, or another version's, layout")
        raise NoRecord("no timed-metadata track: a camera other than an iPhone, or a copy made again by an app or a "
                       "converter, which drops it")
    index, local = found
    rows, bad, shapes_ = [], 0, set()
    for t, s in samples(path, index):
        for lid, value in items(s):
            if lid != local:
                continue
            shapes_.add(len(value))
            f = unpack(value)
            if f is None:
                bad += 1
                continue
            rows.append(dict(frame=_frame_of(t, start, fps), t_s=round(t - start, 6), zoom=float(f[ZOOM_FIELD]),
                             shift_long=float(f[SHIFT_LONG]), shift_short=float(f[SHIFT_SHORT]),
                             step_long=float(f[STEP_LONG]), step_short=float(f[STEP_SHORT]),
                             exposure_s=float(f[EXPOSURE_FIELD]), fields=list(f)))
    if not rows:
        raise NoRecord(f"stream {index} holds {KEY}, but none of its values reads in the one layout known (values of "
                       f"{', '.join(str(n) for n in sorted(shapes_)) or 'no'} bytes): an unknown layout, so nothing is read")
    if bad > len(rows):
        raise NoRecord(f"stream {index}: {bad} of its {bad + len(rows)} values do not read in the one layout known: an "
                       "unknown layout, so nothing is read")
    lux = _lux(path, streams, start, fps)
    for r in rows:
        r["lux"] = lux.get(r["frame"])
    rows.sort(key=lambda r: r["frame"])
    z = np.array([r["zoom"] for r in rows])
    moves = [rows[i]["frame"] for i in range(1, len(rows)) if abs(z[i] - z[i - 1]) > 1e-4]
    return dict(stream=index, key=KEY, records=len(rows), unread=bad, value_bytes=sorted(shapes_), rows=rows,
                rotation=int(info.get("rotation") or 0),
                zoom=dict(least=float(z.min()), most=float(z.max()), usual=float(np.median(z)),
                          share_at_usual=float(np.mean(np.abs(z - np.median(z)) < 1e-3)), frames_moving=len(moves),
                          runs=_runs(moves)))


def _lux(path, streams, start, fps):
    """{frame: the scene's light level} from the phone's illuminance track, where it has one ({} where not)."""
    found = stream_of(path, LUX_KEY, streams)
    if found is None:
        return {}
    out = {}
    try:
        for t, s in samples(path, found[0]):
            for lid, value in items(s):
                if lid == found[1] and len(value) == 4:      # thousandths of a lux, big-endian (2567000 for 2567.0)
                    out[_frame_of(t, start, fps)] = struct.unpack(">I", value)[0] / 1000.0
    except NoRecord:
        return {}
    return out


def _runs(frames):
    """Frames in runs [(first, last)], a gap of more than 3 frames ending one."""
    out = []
    for n in frames:
        if out and n - out[-1][1] <= 3:
            out[-1][1] = n
        else:
            out.append([n, n])
    return [tuple(r) for r in out]


def zoom_curve(record):
    """{frame: zoom} of a record."""
    return {r["frame"]: r["zoom"] for r in record["rows"]}


# ---- what the container says ---------------------------------------------------------------------
def _when(text):
    """An ISO time in the container's spellings, as UTC; None where it cannot be read."""
    if not text:
        return None
    s = str(text).strip().replace("Z", "+00:00")
    s = re.sub(r"([+-]\d\d)(\d\d)$", r"\1:\2", s)
    try:
        t = datetime.fromisoformat(s)
    except ValueError:
        return None
    return (t if t.tzinfo else t.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def _tags_of(path):
    """The container's own tags that ffprobe does not show: the lens and its 35-mm tag are kept in the video track's
    metadata (`meta` box, `mdta` keys) on an iPhone. {key: value} of every `mdta` key with a UTF-8 or numeric value
    found in the moov box."""
    try:
        buf = _moov(path)
    except OSError:
        return {}
    if not buf:
        return {}
    out = {}

    def walk(a, b, depth=0):
        for kind, ka, kb in _boxes(buf, a, b):
            if kind == b"meta":
                _meta(ka, kb)
            elif kind in (b"trak", b"udta", b"mdia", b"minf") and depth < 4:
                walk(ka, kb, depth + 1)

    def _meta(a, b):
        # QuickTime's meta has no version field; ISO's has 4 bytes of one. Try both.
        for start in (a, a + 4):
            keys = _child(buf, start, b, b"keys")
            ilst = _child(buf, start, b, b"ilst")
            if not keys or not ilst:
                continue
            names, i = [], keys[0] + 8                   # version, flags, entry count
            while i + 8 <= keys[1]:
                n = struct.unpack(">I", buf[i:i + 4])[0]
                if n < 8:
                    break
                names.append(buf[i + 8:i + n].decode("utf-8", "replace"))
                i += n
            for kind, ia, ib in _boxes(buf, *ilst):
                idx = struct.unpack(">I", kind)[0]
                data = _child(buf, ia, ib, b"data")
                if not data or not 1 <= idx <= len(names):
                    continue
                typ = struct.unpack(">I", buf[data[0]:data[0] + 4])[0] & 0xFFFFFF
                val = buf[data[0] + 8:data[1]]
                if typ == 1:
                    out[names[idx - 1]] = val.decode("utf-8", "replace")
                elif typ in (21, 22) and len(val) in (1, 2, 4, 8):
                    out[names[idx - 1]] = int.from_bytes(val, "big", signed=typ == 21)
                elif typ == 23 and len(val) == 4:
                    out[names[idx - 1]] = struct.unpack(">f", val)[0]
            return

    walk(8, len(buf))
    return out


def provenance(path, info=None, record=None):
    """What the container says about the device, the lens, the software and the file's own history:
    {make, model, software, lens, focal_35mm, created_file, created_phone, codec, encoders, flags}, `flags` a list
    of sentences -- each a thing to know about this file, not a verdict on the clip."""
    if info is None:
        from .clip import probe
        info = probe(path)
    fmt = (info.get("format") or {}).get("tags") or {}
    vtags = (info.get("stream") or {}).get("tags") or {}
    own = _tags_of(path)
    get = lambda *names: next((src[n] for n in names for src in (own, fmt, vtags) if src.get(n) not in (None, "")), None)
    make = get("com.apple.quicktime.make", "make")
    model = get("com.apple.quicktime.model", "model")
    software = get("com.apple.quicktime.software", "software")
    lens = get("com.apple.quicktime.camera.lens_model")
    f35 = get("com.apple.quicktime.camera.focal_length.35mm_equivalent")
    try:
        f35 = float(f35) if f35 is not None else None
    except (TypeError, ValueError):
        f35 = None
    created_file, created_phone = fmt.get("creation_time"), get("com.apple.quicktime.creationdate")
    codec = (info.get("stream") or {}).get("codec_name")
    encoders = sorted({v for v in (fmt.get("encoder"), vtags.get("encoder")) if v and re.match(r"(Lavf|Lavc|HandBrake)", str(v))})
    flags = []
    tf, tp = _when(created_file), _when(created_phone)
    if tf and tp:
        late = (tf - tp).total_seconds()
        if abs(late) > COPY_AFTER_S:
            flags.append(f"the file was written {_span(late)} {'after' if late > 0 else 'before'} the phone's own creation "
                         f"time ({created_file} against {created_phone}): a copy written later -- a share or an export -- "
                         "and not the camera's own write")
    apple = (make or "").lower() == "apple"
    if apple and codec == "h264":
        flags.append("H.264, where an iPhone records HEVC unless set to its \"Most Compatible\" format: that setting, or a "
                     "copy made again")
    if software and not re.fullmatch(r"\d+(\.\d+)*", str(software).strip()):
        flags.append(f"the software tag names {software}, not a phone's system version: the file was written by it")
    if encoders:
        flags.append(f"written again by {', '.join(encoders)} (an encoder's own tag)")
    if apple and record is None:
        flags.append("an iPhone's file with no frame-by-frame record (LivePhotoInfo): a copy made again, which drops it")
    if f35 and record:
        z = record["zoom"]
        if z["most"] - z["least"] > 1e-3:
            flags.append(f"the 35-mm tag ({f35:g} mm) is one number for the whole clip, and the record's zoom goes from "
                         f"{z['least']:.3g} to {z['most']:.3g}: it is read as the lens at the lowest zoom (as on the one clip "
                         f"it was checked on), so at the usual zoom ({z['usual']:.3g}, {z['share_at_usual']:.0%} of the frames) "
                         f"the lens is {f35 * z['usual'] / z['least']:.0f} mm")
    return dict(make=make, model=model, software=software, lens=lens, focal_35mm=f35, created_file=created_file,
                created_phone=created_phone, codec=codec, encoders=encoders, flags=flags)


def _span(s):
    s = abs(s)
    return f"{s / 3600:.1f} h" if s >= 3600 else f"{s / 60:.0f} min" if s >= 60 else f"{s:.0f} s"


# ---- the angular scale ---------------------------------------------------------------------------
def k_at(record, prov, width, height, frame):
    """k (px/rad) at `frame` from the phone's record: the 35-mm tag's focal length, read at the record's lowest
    zoom, times the zoom at the frame over that zoom, over the picture's diagonal. (k, how, share) or None where the
    file has no 35-mm tag or the record has no zoom at the frame (the nearest frame's is taken within 2 frames)."""
    f35 = (prov or {}).get("focal_35mm")
    if not f35 or not record:
        return None
    curve = zoom_curve(record)
    z = curve.get(frame)
    if z is None:
        near = [n for n in curve if abs(n - frame) <= 2]
        if not near:
            return None
        z = curve[min(near, key=lambda n: abs(n - frame))]
    least = record["zoom"]["least"]
    f = f35 * z / least
    diag = math.hypot(width, height)
    k = f * diag / FULL_FRAME_DIAG_MM
    # the width's reading: the 35-mm tag spread over the picture's long side as over 36 mm
    k_long = f * max(width, height) / 36.0
    share = max(K_SHARE, abs(k_long - k) / k)
    how = (f"the phone's record: the lens's 35-mm equivalent, {f35:g} mm (the file's tag, read at the record's lowest zoom "
           f"{least:.3g}), times the zoom at frame {frame} ({z:.3g}), {f:.1f} mm, over the picture's diagonal of "
           f"{diag:.0f} px")
    return float(k), how, float(share)


# ---- the record written down ---------------------------------------------------------------------
def write_csv(record, prefix):
    """<prefix>_phone.csv: a row a frame -- the zoom, the camera's shift (along the coded picture's long and short
    sides, and as the picture's content moves upright), the exposure, the light, and the 27 fields as read."""
    path = Path(f"{prefix}_phone.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    rot = record.get("rotation", 0)
    with open(path, "w") as f:
        f.write("frame,t_s,zoom,shift_long_px,shift_short_px,content_dx_px,content_dy_px,exposure_s,lux,"
                + ",".join(f"f{i:02d}" for i in range(FIELDS)) + "\n")
        for r in record["rows"]:
            dx, dy = upright(r["shift_long"], r["shift_short"], rot)
            f.write(f"{r['frame']},{r['t_s']:.6f},{r['zoom']:.17g},{r['shift_long']:.6g},{r['shift_short']:.6g},"
                    f"{dx:.6g},{dy:.6g},{r['exposure_s']:.6g},{'' if r['lux'] is None else f'{r['lux']:.6g}'},"
                    + ",".join(f"{v:.9g}" if isinstance(v, float) else str(v) for v in r["fields"]) + "\n")
    return str(path)


def read_csv(path):
    """The zoom record back from a <prefix>_phone.csv: {frame: zoom}."""
    import csv
    with open(path, newline="") as f:
        return {int(r["frame"]): float(r["zoom"]) for r in csv.DictReader(f)}


# ---- the stage -----------------------------------------------------------------------------------
def is_phones(info):
    """Does the container say a camera made it: an iPhone's maker or model tag, or a timed-metadata (`mebx`) track? Only
    such a clip gets a phone's row in a case: on any other the record is not asked of it, and its case is as it was. An
    editor's export carries other `com.apple.quicktime.*` tags (a title, an author: one clip in the data folder, a
    combined clip made in Apple's editor) and is not a camera's file."""
    fmt = (info.get("format") or {}).get("tags") or {}
    return (any(fmt.get(k) for k in ("com.apple.quicktime.make", "com.apple.quicktime.model"))
            or any((s.get("codec_tag_string") or "") == "mebx" for s in info.get("streams") or []))


def measure(video, info=None, out=None, refused=False):
    """The phone's record and what the container says, as a Found ("phone"): its fields the record's summary (not
    its rows: those go to <out>_phone.csv) and the provenance; `carry` (the record or None, the provenance). NO POWER
    for the record, with why, where there is none to read; `refused` (`--no-phone`): the record is not read, and the
    case says so."""
    from .report import Found
    if info is None:
        from .clip import probe
        info = probe(video)
    record, why = None, None
    if refused:
        why = "not read: refused (--no-phone)"
    else:
        try:
            record = read(video, info)
        except NoRecord as e:
            why = str(e)
    prov = provenance(video, info, record)
    fields = dict(found=record is not None, refused=bool(refused), why=why, provenance=prov)
    res, npw, files = {}, [], []
    who = " ".join(v for v in (prov["make"], prov["model"]) if v) or "the phone"
    if record:
        z = record["zoom"]
        fields.update({k: record[k] for k in ("stream", "key", "records", "unread", "value_bytes", "rotation", "zoom")})
        fields["frames"] = [record["rows"][0]["frame"], record["rows"][-1]["frame"]]
        res["phone's record"] = (f"{record['records']} frames of {who}'s own record ({KEY.rsplit('.', 1)[-1]}, stream "
                                 f"{record['stream']}): the zoom, the camera's shift and the exposure on every frame")
        res["phone's zoom"] = (f"{z['least']:.3g} to {z['most']:.3g}, {z['usual']:.3g} on {z['share_at_usual']:.0%} of the frames"
                               + (f"; it moves over frames {', '.join(f'{a}-{b}' for a, b in z['runs'])}" if z["runs"] else
                                  ", on every frame"))
        if out:
            files.append(write_csv(record, out))
            fields["csv"] = files[-1]
    else:
        npw.append(("phone's record", why))
    for label, key in (("device", None), ("lens", "lens"), ("35-mm tag", "focal_35mm"), ("software", "software")):
        v = who if key is None else prov.get(key)
        if v is not None and (key is not None or prov["make"] or prov["model"]):
            res[label] = f"{v:g} mm" if key == "focal_35mm" else str(v)
    if prov["flags"]:
        res["provenance"] = "; ".join(prov["flags"])
    return Found("phone", res, fields, no_power=npw, files=files, carry=(record, prov))


def said(fields):
    """What `mcdonald phone` prints for a person."""
    p = fields.get("provenance") or {}
    L = [f"device: {' '.join(v for v in (p.get('make'), p.get('model')) if v) or 'not named'}"
         + (f"; software {p['software']}" if p.get("software") else "")
         + (f"; lens {p['lens']}" if p.get("lens") else "")
         + (f"; 35-mm tag {p['focal_35mm']:g} mm" if p.get("focal_35mm") else "")]
    if p.get("created_phone") or p.get("created_file"):
        L.append(f"created: {p.get('created_phone') or 'no phone time'} (the phone's), {p.get('created_file') or 'none'} "
                 "(the file's)")
    if fields.get("found"):
        z = fields["zoom"]
        L.append(f"the phone's record: {fields['records']} frames ({fields['frames'][0]}-{fields['frames'][1]}), from stream "
                 f"{fields['stream']}, found by its key {fields['key']}")
        L.append(f"zoom {z['least']:.3g} to {z['most']:.3g}, {z['usual']:.3g} on {z['share_at_usual']:.0%} of the frames"
                 + (f"; it moves over frames {', '.join(f'{a}-{b}' for a, b in z['runs'])}" if z["runs"] else ", on every frame"))
    else:
        L.append(f"no power: the phone's record: {fields.get('why')}")
    L += [f"to know: {f}" for f in p.get("flags") or []]
    return L


def main():
    from .clip import EXIT_NOTHING, out_prefix, resolve, probe
    from .report import emit, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(prog="mcdonald phone", description=(
        "What a phone wrote down about its own clip: an iPhone's frame-by-frame record (its LivePhotoInfo track: the "
        "zoom, the camera's shift and the exposure on every frame), read with ffmpeg alone into <tag>_phone.csv, and "
        "what the file says of the device, the lens, the software and its own history. A clip with no such record "
        "(any other camera, or a copy made again) is no power, with why. `mcdonald run` reads it too, and takes the "
        "angular scale and the zoom on every frame from it."))
    ap.add_argument("video")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true", help="print the record's summary and the provenance as JSON on stdout")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        video, tag, _ = resolve(args.video)
        info = probe(video)
        prefix = out_prefix(args.out, tag, None)
        found = measure(video, info, prefix)
        print("\n".join(said(found.fields)))
        for f in found.files:
            print(f"wrote {f}")
    code = 0 if found.fields["found"] else EXIT_NOTHING
    if args.json:
        emit(found.envelope("phone", inputs_of(args), None, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
