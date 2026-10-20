"""`mcdonald readout` — a number the overlay prints, timed to the frame: when each of its ticks comes, the
rate they add up to, and what a readout that holds still cannot rule out.

Many sensors print the line of sight's angles in whole degrees (the Navy's ATFLIR prints its azimuth as
`8° L`). One reading says little: the true value is anywhere within half a step of it. Its ticks say much
more. The tick from v to v + 1 is where the true value crosses v + 1/2, so a tick timed to the frame is a
reading good to the frame's duration, and a straight line through the tick times of a steady turn gives its
rate far more finely than the step. On FLIR1 eight ticks over 28 s give the pod's slew as 0.2518 +- 0.0042
deg/s, residuals 0.09 deg. That is the rate that matters when the tracker lets go: the object drifts out of
the picture at no more than it (`mcdonald camera --los-rate`).

The converse matters as much. A readout that holds still for a time T after its last tick fits any rate up to
a step over T, and to the end of a clip it may hold whatever the camera does. FLIR1's readout reads `8° L`
from frame 2210 to the end. At the rate before, the next tick would not have come before frame ~2318, after
the end, so the readout cannot say whether the pod stopped. A published analysis took its holding still as
the pod's.

**Reading the digits is yours.** A template of a readout made from its own frames, at 352 x 240, tells one
value from the next reliably once someone has said which frames show which value. It cannot read the value
off a single frame. So the command works in two passes:

1. `mcdonald readout VIDEO --box x0,y0,x1,y1` writes a strip of the box every `--every` frames, labelled
   with frame numbers (`<tag>_readout_strip.png`). Look at it, and write down the value on each stretch.
2. `... --values "1-256:4,271-706:3,..."` (first frame-last frame:value, one per stretch, frames well inside
   each; signed, so that right of the nose is + and left is -) times each tick to the frame, between the
   stretches either side of it. Each frame near a tick goes to the stretch whose template it is closer to.
   The tick is the change point that gives the fewest frames to the wrong side, and the frames that dither
   between the two values are counted.

The rate is a straight line through the ticks of the longest run that steps one way by one step at a time;
a run that goes back and forth is reported, not fitted.
"""
import csv
import math
from pathlib import Path

import numpy as np

from .report import Found

EDGE = 10              # frames left out at each end of a stretch when its template is made (if it is long enough)
NEAR = 45              # frames either side of a tick over which its dithering is counted


def parse_box(text):
    x0, y0, x1, y1 = (int(round(float(v))) for v in text.split(","))
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"--box {text}: it is x0,y0,x1,y1 with x1 > x0 and y1 > y0")
    return x0, y0, x1, y1


def parse_values(text):
    """`1-256:4,271-706:3` -> [(1, 256, 4.0), (271, 706, 3.0)], in frame order."""
    out = []
    for part in (text or "").split(","):
        part = part.strip()
        if not part:
            continue
        span, _, v = part.rpartition(":")
        a, _, b = span.partition("-")
        out.append((int(a), int(b), float(v)))
    out.sort()
    for (a0, b0, _), (a1, b1, _) in zip(out, out[1:]):
        if a1 <= b0:
            raise ValueError(f"--values: the stretches {a0}-{b0} and {a1}-{b1} overlap")
    return out


def crops(clip, box, frames):
    """The box on each frame, each made zero-mean and unit-variance: a template compares shapes, not the
    picture's brightness, which the sensor's gain moves."""
    x0, y0, x1, y1 = box
    c = np.stack([clip.grey(n)[y0:y1, x0:x1].astype(float) for n in frames])
    c -= c.mean(axis=(1, 2), keepdims=True)
    return c / (c.std(axis=(1, 2), keepdims=True) + 1e-6)


def strip(clip, box, every=15, out=None, scale=4):
    """A PNG of the box every `every` frames, each labelled with its frame number, to read the values off."""
    from PIL import Image, ImageDraw
    from .figures import pil_font
    x0, y0, x1, y1 = box
    frames = list(range(clip.n0, clip.n1 + 1, max(1, int(every))))
    w, h = (x1 - x0) * scale, (y1 - y0) * scale
    cols = max(1, min(len(frames), 1600 // max(w, 1)))
    rows = (len(frames) + cols - 1) // cols
    lab = 16
    im = Image.new("L", (cols * w, rows * (h + lab)), 0)
    d = ImageDraw.Draw(im)
    f = pil_font(12, bold=True)
    for k, n in enumerate(frames):
        c = clip.grey(n)[y0:y1, x0:x1].astype(float)
        c = np.clip((c - c.min()) / (np.ptp(c) + 1e-6) * 255, 0, 255).astype(np.uint8)
        X, Y = (k % cols) * w, (k // cols) * (h + lab)
        im.paste(Image.fromarray(c).resize((w, h), Image.NEAREST), (X, Y + lab))
        d.text((X + 2, Y + 1), str(n), fill=255, font=f)
    path = Path(f"{out}_readout_strip.png") if out else None
    if path:
        im.save(path)
    return path, frames


def ticks(clip, box, stretches):
    """Each tick between consecutive stretches: [{from, to, tick_frame, misread_frames, dither_frames, ...}].

    The frames from the middle of one stretch to the middle of the next are each given to the nearer of the
    two stretches' templates; the tick is the change point with the fewest frames on the wrong side
    (`misread_frames`), at the half frame between, and `dither_frames` is how far apart the first frame that
    looks new and the last that looks old are, within NEAR frames of it."""
    tpl = []
    for a, b, _ in stretches:
        core = range(a + EDGE, b - EDGE + 1) if b - a > 3 * EDGE else range(a, b + 1)
        tpl.append(crops(clip, box, core).mean(0))
    out = []
    for k in range(len(stretches) - 1):
        (a0, b0, v0), (a1, b1, v1) = stretches[k], stretches[k + 1]
        f = np.arange((a0 + b0) // 2, (a1 + b1) // 2 + 1)
        c = crops(clip, box, f)
        new = ((c - tpl[k + 1]) ** 2).mean(axis=(1, 2)) < ((c - tpl[k]) ** 2).mean(axis=(1, 2))
        wrong = np.array([new[:j].sum() + (~new[j:]).sum() for j in range(len(f) + 1)])
        j = int(np.argmin(wrong))
        near = slice(max(0, j - NEAR), j + NEAR)
        fn, fo = f[near][new[near]], f[near][~new[near]]
        first_new = int(fn.min()) if len(fn) else int(f[min(j, len(f) - 1)])
        last_old = int(fo.max()) if len(fo) else int(f[max(j - 1, 0)])
        out.append({"from": v0, "to": v1, "tick_frame": float(f[0] + j - 0.5), "misread_frames": int(wrong[j]),
                    "first_new": first_new, "last_old": last_old,
                    "dither_frames": int(max(0, last_old - first_new + 1)),
                    "crossing": 0.5 * (v0 + v1)})
    return out


def rate(tk, fps, step=1.0, last_frame=None):
    """The rate the ticks add up to: a straight line through the crossings of the longest run that steps one way
    by one `step` at a time (crossing value against tick time). With `last_frame`, also when the readout would
    next tick at that rate after its last one, and the fastest rate its hold to `last_frame` allows."""
    runs, cur = [], []
    for t in tk:
        d = t["to"] - t["from"]
        if abs(abs(d) - step) < 1e-9 and (not cur or np.sign(d) == np.sign(cur[-1]["to"] - cur[-1]["from"])):
            cur.append(t)
        else:
            if cur:
                runs.append(cur)
            cur = [t] if abs(abs(d) - step) < 1e-9 else []
    if cur:
        runs.append(cur)
    run = max(runs, key=len) if runs else []
    res = dict(ticks_used=len(run), run=[run[0]["tick_frame"], run[-1]["tick_frame"]] if run else None,
               not_monotonic=[t for t in tk if t not in run])
    if len(run) < 2:
        res.update(rate_per_s=None, why="fewer than two ticks in one direction")
        return res
    t = np.array([r["tick_frame"] for r in run]) / float(fps)
    th = np.array([r["crossing"] for r in run])
    if len(run) >= 3:
        p, cov = np.polyfit(t, th, 1, cov=True)
        err = float(math.sqrt(cov[0, 0]))
    else:
        p, err = np.polyfit(t, th, 1), float("nan")
    resid = th - np.polyval(p, t)
    res.update(rate_per_s=float(p[0]), rate_err_per_s=err, residual_rms=float(resid.std()),
               last_tick_frame=run[-1]["tick_frame"], last_tick_dither_frames=run[-1]["dither_frames"])
    if last_frame is not None:
        last = tk[-1]
        # the last crossing sits mid-dither where the readout dithered
        at = 0.5 * (last["first_new"] + last["last_old"]) if last["dither_frames"] else last["tick_frame"]
        due = at + step / abs(p[0]) * fps
        held = (last_frame - at) / float(fps)
        res.update(next_tick_due_frame=float(due), holds_to_end=bool(due > last_frame),
                   held_s=float(held), rate_a_hold_allows_per_s=float(step / held) if held > 0 else None)
    return res


def measure(clip, box, stretches, step=1.0, out=None, tag="", every=15):
    """The readout stage: the ticks and their rate, or -- with no stretches -- only the strip to read them off."""
    files = []
    if not stretches:
        path, _ = strip(clip, box, every, out=out)
        return Found("readout", dict(strip=str(path)), dict(strip=str(path), ticks=[], rate=None), files=[path],
                     needs=["the readout's value on each stretch, read off the strip: --values first-last:value,..."])
    tk = ticks(clip, box, stretches)
    r = rate(tk, clip.fps, step, last_frame=clip.n1)
    res, npw, notes = {}, [], []
    res["ticks"] = ", ".join(f"{t['from']:g}->{t['to']:g} at {t['tick_frame']:.1f}"
                             + (f" (dithers {t['dither_frames']})" if t["dither_frames"] else "") for t in tk)
    if r["rate_per_s"] is None:
        npw.append(("readout rate", r["why"]))
    else:
        res["rate"] = (f"{r['rate_per_s']:+.4f} +- {r['rate_err_per_s']:.4f} a second over {r['ticks_used']} ticks, "
                       f"residuals {r['residual_rms']:.3f}")
        if r.get("holds_to_end"):
            res["holding still"] = (f"after its last tick the readout holds for {r['held_s']:.1f} s, to the end; at the "
                                    f"rate before, the next tick was due at frame {r['next_tick_due_frame']:.0f}, after "
                                    "the end -- so its holding still cannot tell a camera that stopped from one that "
                                    "kept turning")
            notes.append("The readout holds still to the end of the clip, but at its own rate before it would not "
                         "have ticked again before the end: it cannot say whether the camera stopped.")
        elif r.get("held_s") is not None and r["held_s"] > 0:
            res["holding still"] = (f"after its last tick the readout holds for {r['held_s']:.1f} s; any rate up to "
                                    f"{r['rate_a_hold_allows_per_s']:.3f} a second fits that hold")
    fields = dict(box=list(box), stretches=[dict(first=a, last=b, value=v) for a, b, v in stretches], step=step,
                  ticks=tk, rate=r)
    if out:
        p = Path(f"{out}_readout_ticks.csv")
        with open(p, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["from", "to", "tick_frame", "t_s", "misread_frames", "first_new",
                                               "last_old", "dither_frames", "crossing"])
            w.writeheader()
            for t in tk:
                w.writerow(dict(t, t_s=round((t["tick_frame"] - 1) / clip.fps, 4)))
        files.append(p)
    return Found("readout", res, fields, no_power=npw, files=files, notes=notes)


def said(fields):
    L = [f"tick {t['from']:g} -> {t['to']:g} at frame {t['tick_frame']:.1f}"
         + (f", dithering over {t['dither_frames']} frames" if t["dither_frames"] else "")
         + (f", {t['misread_frames']} frames read the other way" if t["misread_frames"] else "")
         for t in fields.get("ticks", [])]
    r = fields.get("rate")
    if r and r.get("rate_per_s") is not None:
        L.append(f"rate {r['rate_per_s']:+.4f} +- {r['rate_err_per_s']:.4f} a second over {r['ticks_used']} ticks "
                 f"(residuals {r['residual_rms']:.3f})")
        if r.get("holds_to_end"):
            L.append(f"it holds still to the end: at that rate the next tick was due at frame "
                     f"{r['next_tick_due_frame']:.0f}, after the end, so the hold cannot say whether the camera stopped")
        elif r.get("rate_a_hold_allows_per_s"):
            L.append(f"after its last tick it holds {r['held_s']:.1f} s: any rate up to {r['rate_a_hold_allows_per_s']:.3f} "
                     "a second fits that")
    if r and r.get("not_monotonic"):
        L.append("not in the run fitted: " + ", ".join(f"{t['from']:g}->{t['to']:g} at {t['tick_frame']:.0f}"
                                                        for t in r["not_monotonic"]))
    if fields.get("strip"):
        L.append(f"read the value on each stretch off {fields['strip']} and give them as --values first-last:value,...")
    return L


def main():
    import argparse
    from . import clip as vclip
    from . import forensics as vf
    from .report import emit, inputs_of, said_to_stderr
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--box", required=True, help="the readout's box in the frame, x0,y0,x1,y1 px (`mcdonald look "
                    "VIDEO --frame N` shows where it is)")
    ap.add_argument("--values", help="first-last:value for each stretch, comma separated, frames well inside each "
                    "(omit it for the strip to read them off)")
    ap.add_argument("--every", type=int, default=15, help="the strip's spacing, frames (default 15)")
    ap.add_argument("--step", type=float, default=1.0, help="the readout's step (default 1)")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--workdir")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true", help="print the measurement as JSON on stdout")
    args = ap.parse_args()
    try:
        box, stretches = parse_box(args.box), parse_values(args.values)
    except ValueError as e:
        ap.error(str(e))
    with said_to_stderr(args.json) as lines:
        video, tag, _ = vf.resolve(args.video)
        n0 = args.n0 or (stretches[0][0] if stretches else None)
        n1 = args.n1 or (max(b for _, b, _ in stretches) if stretches else None)
        if stretches and args.n1 is None:
            n1 = None                       # to the end: whether the last reading holds to the end is part of the answer
        clip = vclip.Clip(video, args.workdir, n0, n1)
        out = vclip.out_prefix(args.out, tag)
        print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
        found = measure(clip, box, stretches, args.step, out, tag, every=args.every)
        print("\n".join(said(found.fields)))
        for w in found.no_power:
            print(f"no power: {w[1]}")
        for f in found.files:
            print(f"wrote {f}")
    code = vclip.EXIT_NOTHING if found.no_power else 0
    if args.json:
        emit(found.envelope("readout", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
