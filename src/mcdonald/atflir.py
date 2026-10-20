"""`mcdonald symbology --method atflir` — the Navy's ATFLIR display read as fields: where its readouts are, when each of
them changes, and -- once a person has read each look of each field off a sheet -- what they said frame by frame.

The ATFLIR (the AN/ASQ-228 targeting pod) prints its pointing and its state as text round the picture: the pod's
azimuth (`8° L`), its elevation (`-5°`), the zoom (`Z 2.0`, or `1.0` beside a `ZOOM` written down the left on the 2004
software), the field of view (`NAR`, `MFOV`, `WFOV`), the camera (`IR`, `TV`), the aircraft's altitude, its Mach and a
clock. It draws no north pointer, so `symbology`'s other methods find nothing on it; its pointing is in the text. The
fields sit in the same places on the three ATFLIR clips the Navy released -- FLIR1 (2004, 352 x 240), GIMBAL and GOFAST
(2015, 1920 x 1080 renditions of a standard-definition display) -- as shares of the square picture the text is drawn
round, so the reader finds that picture and looks in each field's place. The zoom has two places; the one with text
in it is taken.

Each field is then followed through the clip as `mcdonald events` follows a box of text (`events.changes_of`): its
looks, the stretches over which it holds each, and its changes timed to the half frame, with any dithering counted.
The values are not read from the pixels -- at 352 x 240 a glyph is 7 px high and the copies blur it to 4-px strokes --
but each field's looks are drawn on a sheet (`<tag>_atflir_looks.png`), lettered A, B, C ..., and a person gives what
each says (`--read "az:A=-8,B=-7;zoom:A=1,B=2"`; signed, right of the nose +). With that, each field is a timeline,
and the azimuth's ticks give the pod's slew rate as `mcdonald readout` gives it (FLIR1: 0.2466 +- 0.0051 deg/s).

What it cannot do: read a field the copy has blurred past telling its looks apart; know the layout of a display it
has not seen (other pods print their own; `mcdonald events` finds their text without one); or say what the pod was
pointed at -- an azimuth is the pod's, relative to the aircraft's nose.
"""
import csv
from fractions import Fraction
from pathlib import Path

import numpy as np

from . import events as ev
from . import forensics as vf
from .report import Found

# (x0, y0, x1, y1) as shares of the picture's box, from FLIR1, GIMBAL and GOFAST (2026-10-20); a field with two places
# is looked for in both, and the one with text in it taken
LAYOUT = {
    "az": [(0.44, 0.035, 0.60, 0.09)],
    "el": [(0.05, 0.43, 0.19, 0.51)],
    "zoom": [(0.12, 0.035, 0.27, 0.09), (0.04, 0.24, 0.15, 0.30)],
    "fov": [(0.12, 0.012, 0.24, 0.045)],               # from just under the picture's top edge, which FLIR1 draws
    "mode": [(0.45, 0.012, 0.56, 0.045)],
}
NAMES = {"az": "the pod's azimuth", "el": "its elevation", "zoom": "the zoom", "fov": "the field of view",
         "mode": "the camera (IR or TV)"}
SAMPLE = 25


def picture_box(clip, frames=None):
    """The square picture the ATFLIR's text is drawn round: the columns and rows, of the median of a sample of frames,
    that are not the display's black surround in most of the frame -- lit, or changing from frame to frame -- (x0, y0,
    x1, y1). FLIR1's 2007 copy: 52-296 by 14-230 of 352 x 240; GOFAST's 1920 x 1080: 475-1434 by 60-1025; GIMBAL's,
    whose sky at the top is as black as the surround, from its bottom edge and its width."""
    frames = frames or np.linspace(clip.n0, clip.n1, min(SAMPLE, clip.n1 - clip.n0 + 1)).astype(int).tolist()
    st = np.stack([clip.grey(n) for n in frames])
    med = np.median(st, 0)
    # lit, or alive: a dark sky at the top of the picture is barely above the surround's black (GIMBAL's), but it moves
    # and is noisy, where a digital surround does not change from frame to frame
    lit = (med > max(12.0, float(np.percentile(med, 5)) + 8.0)) | (st.std(0) > 1.5)
    cols = np.flatnonzero(lit.mean(0) > 0.4)
    if not len(cols):
        return None
    rows = np.flatnonzero(lit[:, cols[0]:cols[-1] + 1].mean(1) > 0.4)
    if not len(rows):
        return None
    x0, y0, x1, y1 = int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1
    # the picture is square on the display: where it comes out much shorter than its width (a sky at its top as black
    # as the surround: GIMBAL's, 861 rows of 960), it is taken from its bottom edge up, its width's height
    tall = (x1 - x0) * pixel_aspect(clip)
    if y1 - y0 < 0.93 * tall:
        y0 = max(0, int(round(y1 - tall)))
    return x0, y0, x1, y1


def pixel_aspect(clip):
    """A pixel's width over its height on the display (the stream's sample aspect ratio; FLIR1's VCD copy: 200:219)."""
    try:
        a = Fraction(str((clip.info.get("stream") or {}).get("sample_aspect_ratio", "1:1")).replace(":", "/"))
        return float(a) if a > 0 else 1.0
    except (AttributeError, ValueError, ZeroDivisionError):
        return 1.0


def field_boxes(clip, box, frames=None, polarity=1):
    """Each field's box in the frame, from the layout: {field: (x0, y0, x1, y1)}, the place with the most strokes in it
    taken where a field has two."""
    frames = frames or np.linspace(clip.n0, clip.n1, min(SAMPLE, clip.n1 - clip.n0 + 1)).astype(int).tolist()
    st = np.percentile(np.stack([vf.strokes(clip.grey(n), polarity, clip.H) for n in frames]), 75, axis=0)
    on = st > max(12.0, 4.0 * float(np.median(np.abs(st - np.median(st)))) * 1.4826)
    X0, Y0, X1, Y1 = box
    w, h = X1 - X0, Y1 - Y0
    out = {}
    for name, places in LAYOUT.items():
        best = None
        for fx0, fy0, fx1, fy1 in places:
            b = (int(X0 + fx0 * w), int(Y0 + fy0 * h), int(round(X0 + fx1 * w)), int(round(Y0 + fy1 * h)))
            ink = float(on[b[1]:b[3], b[0]:b[2]].mean()) if b[3] > b[1] and b[2] > b[0] else 0.0
            if best is None or ink > best[0]:
                best = (ink, b)
        if best and best[0] > 0.02:
            out[name] = best[1]
    return out


def letters(k):
    """0 -> A, 25 -> Z, 26 -> AA."""
    s = ""
    k += 1
    while k:
        k, r = divmod(k - 1, 26)
        s = chr(65 + r) + s
    return s


def parse_read(text):
    """`az:A=-8,B=-7;zoom:A=1` -> {"az": {"A": -8.0, "B": -7.0}, "zoom": {"A": 1.0}}."""
    out = {}
    for part in (text or "").split(";"):
        part = part.strip()
        if not part:
            continue
        field, _, rest = part.partition(":")
        vals = {}
        for kv in rest.split(","):
            k, _, v = kv.partition("=")
            if k.strip():
                vals[k.strip().upper()] = float(v)
        out[field.strip()] = vals
    return out


def measure(clip, read=None, out=None, tag="", box=None):
    """The ATFLIR stage: the picture's box, the fields' boxes, each field's looks, stretches and changes, the sheet to
    read them off, and with `read` ({field: {look letter: value}}) each field's timeline and the azimuth's slew rate."""
    from . import readout
    frames = list(clip.frames())
    sample = np.linspace(clip.n0, clip.n1, min(SAMPLE, len(frames))).astype(int).tolist()
    box = box or picture_box(clip, sample)
    if not box:
        return Found("atflir", no_power=[("atflir", "no picture box found: the display's black surround is not there")])
    fb = field_boxes(clip, box, sample)
    if not fb:
        return Found("atflir", dict(picture=f"({box[0]},{box[1]})-({box[2]},{box[3]})"), dict(picture_box=list(box)),
                     no_power=[("atflir", "no text in any of the ATFLIR's fields: this is not its display, or the copy "
                                          "has lost the text")])
    glyph = max(5, round(7 * (box[3] - box[1]) / 215))
    series = {k: ev.BoxSeries(b, k, glyph=glyph) for k, b in fb.items()}
    pols = {k: vf.text_polarity(clip.grey(sample[len(sample) // 2])[b[1]:b[3], b[0]:b[2]]) for k, b in fb.items()}
    for n in frames:
        g = clip.grey(n)
        for k, s in series.items():
            x0, y0, x1, y1 = s.box
            s.push(n, vf.strokes(g[y0:y1, x0:x1], pols[k], clip.H))
    fields, res, needs, notes, files = {}, {}, [], [], []
    for k, s in series.items():
        ch, runs, nl, _ = ev.changes_of(s)
        tk = ev.ticks(ch)
        looks = sorted({r[2] for r in runs})
        name = {j: letters(i) for i, j in enumerate(looks)}
        f = dict(box=list(s.box), looks=len(looks), stretches=[[a, b, name[j]] for a, b, j in runs],
                 changes=[dict(frame=t["frame"], **{"from": name[t["from"]]}, to=name[t["to"]],
                               dither_frames=t["dither_frames"]) for t in tk])
        vals = (read or {}).get(k)
        if vals:
            f["values"] = [[a, b, vals.get(name[j])] for a, b, j in runs]
            missing = sorted({name[j] for _, _, j in runs} - set(vals))
            if missing:
                needs.append(f"{NAMES[k]}'s looks {', '.join(missing)} read off the sheet (--read {k}:{missing[0]}=...)")
        fields[k] = f
        res[NAMES[k]] = (f"{len(looks)} look{'s' if len(looks) != 1 else ''}, {len(tk)} change{'s' if len(tk) != 1 else ''}"
                         + (": " + ", ".join(f"{c['from']}->{c['to']} at {c['frame']:.1f}" for c in f["changes"][:8])
                            + (" ..." if len(tk) > 8 else "") if tk else ""))
    rate = None
    if "az" in fields and "values" in fields["az"]:
        # the azimuth's ticks between stretches whose values were given, in readout's form, and the rate they make
        st = [(a, b, v) for a, b, v in fields["az"]["values"] if v is not None and b - a >= 2]
        merged = []
        for a, b, v in st:
            if merged and merged[-1][2] == v:
                merged[-1] = (merged[-1][0], b, v)
            else:
                merged.append((a, b, v))
        if len(merged) >= 3:
            tk = readout.ticks(clip, tuple(fields["az"]["box"]), merged)
            rate = readout.rate(tk, clip.fps, last_frame=clip.n1)
            fields["az"]["ticks"] = tk
            fields["az"]["rate"] = rate
            if rate.get("rate_per_s") is not None:
                res["azimuth rate"] = (f"{rate['rate_per_s']:+.4f} +- {rate['rate_err_per_s']:.4f} deg/s over "
                                       f"{rate['ticks_used']} ticks (residuals {rate['residual_rms']:.3f} deg)"
                                       + ("; it holds to the end, where the next tick was not yet due"
                                          if rate.get("holds_to_end") else ""))
    if not read:
        needs.append("each field's looks read off the sheet: --read \"az:A=...,B=...;zoom:A=...\" (signed: right of the "
                     "nose +)")
    out_fields = dict(picture_box=list(box), fields=fields)
    if out:
        files = write(out, clip, series, fields)
    return Found("atflir", dict(picture=f"({box[0]},{box[1]})-({box[2]},{box[3]})", **res), out_fields, needs=needs,
                 files=files, notes=notes)


def write(out, clip, series, fields):
    """<out>_atflir_looks.png (each field's looks, lettered, with the frames each holds) and <out>_atflir.csv."""
    from PIL import Image, ImageDraw
    from .figures import pil_font
    tiles = []
    font = pil_font(12, bold=True)
    for k, f in fields.items():
        x0, y0, x1, y1 = f["box"]
        scale = max(2, int(round(48 / max(1, y1 - y0))))
        seen = {}
        for a, b, L in f["stretches"]:
            seen.setdefault(L, (a, b))
        for L, (a, b) in sorted(seen.items()):
            g = clip.grey((a + b) // 2)[y0:y1, x0:x1]
            g = np.clip((g - g.min()) / (np.ptp(g) + 1e-6) * 255, 0, 255).astype(np.uint8)
            im = Image.fromarray(g).resize(((x1 - x0) * scale, (y1 - y0) * scale), Image.NEAREST)
            cv = Image.new("L", (max(im.width, 150), im.height + 18), 0)
            cv.paste(im, (0, 18))
            ImageDraw.Draw(cv).text((2, 1), f"{k} {L}  {a}-{b}", fill=255, font=font)
            tiles.append(cv)
    if not tiles:
        return []
    W = max(t.width for t in tiles)
    cols = max(1, 1400 // W)
    rows = -(-len(tiles) // cols)
    H = max(t.height for t in tiles)
    sheet = Image.new("L", (cols * W, rows * H), 0)
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * W, (i // cols) * H))
    png = Path(f"{out}_atflir_looks.png")
    sheet.save(png)
    path = Path(f"{out}_atflir.csv")
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["field", "first", "last", "look", "value"])
        for k, f in fields.items():
            vals = {(a, b): v for a, b, v in f.get("values", [])}
            for a, b, L in f["stretches"]:
                w.writerow([k, a, b, L, "" if vals.get((a, b)) is None else vals[(a, b)]])
    return [str(png), str(path)]


def said(fields):
    L = [f"the picture: ({fields['picture_box'][0]},{fields['picture_box'][1]})-({fields['picture_box'][2]},"
         f"{fields['picture_box'][3]})"]
    for k, f in fields.get("fields", {}).items():
        L.append(f"{NAMES[k]} at ({f['box'][0]},{f['box'][1]})-({f['box'][2]},{f['box'][3]}): {f['looks']} looks, "
                 f"{len(f['changes'])} changes")
        r = f.get("rate")
        if r and r.get("rate_per_s") is not None:
            L.append(f"  its ticks give {r['rate_per_s']:+.4f} +- {r['rate_err_per_s']:.4f} a second over {r['ticks_used']}")
    return L
