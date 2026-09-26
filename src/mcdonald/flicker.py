"""Does the object's brightness beat -- and is the beat the object's, or the video's?

"Is it birds?" is asked of most clips of several points, and a bird's wings beat: seen
from afar a flapping bird flickers a few to ten or so times a second. The PR135 agent
(2026-09-22, its items 21, 23 and 24) measured it by hand, and found the two traps that
each fake a result -- both built in here, with a third it asked for:

1. **Pixel phase.** A small aperture re-centred on the rounded position of a point that
   moves a fraction of a pixel a frame takes in more or less of it as the fraction turns:
   planted dots of constant brightness "flickered" 3-6 Hz before any encoding. So the
   aperture is a disc APERTURE px across in radius, its weights the share of each pixel
   inside it (supersampled SUPER times each way), centred on the track smoothed over
   SMOOTH frames, less the median of a ring RING about it (`brightness`).
2. **The codec's rhythm.** A clip's anchor frames (I and P) are coded afresh and the B
   frames between them from them; a point's brightness can follow that. PR135 has a P
   every 4th frame: 30/4 = 7.49 Hz, which is where its points flicker. The rhythm is
   read from the clip itself (`clip.gop`), marked, and a peak within the resolution of
   it is said to be there.
3. **The same frames, several members.** A rhythm of the video beats every member at
   the same frequency and in step. Members over one common window at frequencies
   further apart than the resolution, or at one frequency out of step, are not a
   rhythm of the video (PR135: 7.00 Hz against 7.74-7.82, phases 84-175 deg apart).
   That is the pass condition where there are members (`common`).

And a control that rides along, which is also the test of whether there is a beat at all:
the same photometry on BACKGROUND apertures about the object, which share the frames, the
codec, the grain and the camera but not the object, measured in the object's brightness.
The object beats only if its strongest beat is ABOVE times theirs (the median of their
strongest): a peak standing over its own band is not enough, because the grain makes
those everywhere. And a beat they share at the object's frequency is not the object's.

Each curve is taken relative to its own running mean over DETREND frames (so a slow
change is not a beat), windowed (Hann), and zero-padded 16 times; what is reported is
the strongest peak between LOW Hz and just under Nyquist, its amplitude as a share of the
brightness, how far it stands over the median of the band, and the resolution, 1/T.

What it cannot do: say that a beat is a wingbeat. A tumbling or rotating body beats too,
and so does a light that blinks. A beat that survives the controls is the object's own;
what makes it is the rest of the case.
"""
import csv

import numpy as np
from scipy import ndimage

from . import forensics as vf
from .clip import gop as read_gop
from .progress import counted, to_stderr
from .report import Found, emit, inputs_of, said_to_stderr

APERTURE = 4.0       # px, radius
SUPER = 8            # each pixel's share of the aperture, from SUPER x SUPER points in it
RING = (7.0, 10.0)   # px, the background ring
SMOOTH = 5           # frames the track is smoothed over, so the aperture does not chase centroid noise
DETREND = 15         # frames of running mean each curve is taken against
LOW = 1.5            # Hz: slower than this is a trend, not a beat
PAD = 16
ABOVE = 3.0          # a beat is the object's only at this many times the background apertures' own (their median
                     # strongest, in the object's brightness): planted dots of constant brightness, encoded as
                     # PR135 is, beat 5-7 % at 2-4 Hz and stand 46-123 times their band -- the grain does that
MIN_FRAMES = 60      # two seconds at 30 fps: fewer, and no frequency is worth quoting
BACKGROUND = [(0, 25), (25, 0), (0, -25), (-25, 0)]     # px, the background apertures about the object
APART_DEG = 45.0     # members at one frequency but this far out of step are not in step
SHARED = 0.5         # a background aperture that beats this strongly at the object's frequency shares its beat


def brightness(g, x, y, r=APERTURE, ring=RING, dark=False):
    """The aperture's sum over the ring's median, for a thing centred at (x, y) to a fraction of
    a pixel; None where the ring leaves the frame. Dark things are measured as dark: the sum is
    of how much darker they are."""
    H, W = g.shape
    R = int(np.ceil(ring[1])) + 1
    ix, iy = int(np.floor(x)), int(np.floor(y))
    if ix - R < 0 or iy - R < 0 or ix + R + 1 > W or iy + R + 1 > H:
        return None
    s = g[iy - R:iy + R + 1, ix - R:ix + R + 1].astype(float)
    yy, xx = np.mgrid[iy - R:iy + R + 1, ix - R:ix + R + 1].astype(float)
    off = (np.arange(SUPER) + 0.5) / SUPER - 0.5
    w = np.zeros(s.shape)
    for dy in off:
        for dx in off:
            w += np.hypot(xx + dx - x, yy + dy - y) <= r
    w /= SUPER * SUPER
    rr = np.hypot(xx - x, yy - y)
    bg = float(np.median(s[(rr >= ring[0]) & (rr <= ring[1])]))
    v = float(((s - bg) * w).sum())
    return -v if dark else v


def smoothed(track, ns):
    """The track at every frame of `ns`, filled in where it has gaps and smoothed over SMOOTH frames."""
    have = sorted(track)
    x = np.interp(ns, have, [track[n][0] for n in have])
    y = np.interp(ns, have, [track[n][1] for n in have])
    return ndimage.uniform_filter1d(x, SMOOTH, mode="nearest"), ndimage.uniform_filter1d(y, SMOOTH, mode="nearest")


def spectrum(f, fps, scale=None):
    """(frequencies, complex spectrum, the band's mask, Hann weights' sum, rms) of a curve taken
    against its own running mean, as a share of that mean -- or of `scale`, for a background
    aperture, whose own mean is near nothing: it is measured in the object's brightness."""
    f = np.asarray(f, float)
    trend = ndimage.uniform_filter1d(f, DETREND, mode="nearest")
    r = (f - trend) / (scale if scale else trend)
    r -= r.mean()
    w = np.hanning(len(r))
    F = np.fft.rfft(r * w, PAD * len(r))
    fr = np.fft.rfftfreq(PAD * len(r), 1 / fps)
    band = (fr >= LOW) & (fr <= 0.95 * fps / 2)
    return fr, F, band, float(w.sum()), float(r.std())


def peak(f, fps, lines=(), scale=None):
    """The strongest beat of a curve: frequency, amplitude (a share of the brightness), how it
    stands over the median of the band, its half-power width, and whether it is within the
    resolution of one of the codec's `lines`."""
    fr, F, band, wsum, rms = spectrum(f, fps, scale)
    P = np.abs(F) ** 2
    k = int(np.argmax(np.where(band, P, -1)))
    res = fps / len(f)
    half = fr[band][P[band] >= P[k] / 2]
    near = [L for L in lines if abs(fr[k] - L) <= res]
    return dict(hz=float(fr[k]), amplitude=float(2 * np.sqrt(P[k]) / wsum), stands=float(P[k] / np.median(P[band])),
                half_power_hz=[float(half.min()), float(half.max())], resolution_hz=float(res), rms=rms,
                at_the_codec_line_hz=near[0] if near else None)


def curves(clip, tracks, ns, dark=False, progress=None, stop=None):
    """{name: brightness on each frame of ns} for each track, and for BACKGROUND apertures about
    the first -- None where the aperture leaves the frame or a mask covers it."""
    pos = {name: smoothed(t, ns) for name, t in tracks.items()}
    first = next(iter(pos.values()))
    for dx, dy in BACKGROUND:
        pos[f"background {dx:+d},{dy:+d}"] = (first[0] + dx, first[1] + dy)
    out = {name: [] for name in pos}
    for k, n in enumerate(counted(ns, progress, stop, "Flicker")):
        g = clip.rgb(n).mean(2)
        for name, (x, y) in pos.items():
            out[name].append(brightness(g, x[k], y[k], dark=dark and not name.startswith("background")))
    return out


def common(spectra, members, fps, n):
    """Whether members over the same frames beat as one: pairs, each at its own peak, with the
    phase between them at the first one's -- and `independent`: two at frequencies further
    apart than the resolution, or at one frequency more than APART_DEG out of step."""
    res = fps / n
    pairs = []
    for a in range(len(members)):
        for b in range(a + 1, len(members)):
            A, B = spectra[members[a]], spectra[members[b]]
            fr, Fa, band = A["fr"], A["F"], A["band"]
            X = Fa * np.conj(B["F"])
            k = int(np.argmax(np.where(band, np.abs(X), -1)))
            apart = abs(A["peak"]["hz"] - B["peak"]["hz"])
            phase = float(np.degrees(np.angle(X[k])))
            pairs.append(dict(members=[members[a], members[b]], hz=[A["peak"]["hz"], B["peak"]["hz"]],
                              apart_hz=apart, cross_hz=float(fr[k]), phase_deg=phase,
                              independent=bool(apart > res or abs(phase) > APART_DEG)))
    return pairs


def measure(clip, tracks, dark=False, out=None, say=print, progress=None, stop=None):
    """The stage: each track's beat, the background apertures' about the first, the codec's rhythm,
    and -- with two tracks or more -- whether they beat as one. `tracks` is {name: {frame: (x, y)}}:
    the object's track, or the members of a group (groups.members). Writes <out>_flicker.csv."""
    g = read_gop(clip.video, clip.fps) if getattr(clip, "video", None) else None
    lines = (g or {}).get("lines_hz") or []
    names = list(tracks)
    ns = sorted(set.intersection(*[set(n for n in t if clip.n0 <= n <= clip.n1) for t in tracks.values()]))
    ns = list(range(ns[0], ns[-1] + 1)) if ns else []
    fields = dict(frames=len(ns), first=ns[0] if ns else None, last=ns[-1] if ns else None, codec=g,
                  aperture_px=APERTURE, tracks=names)
    if len(ns) < MIN_FRAMES:
        return Found("flicker", fields=dict(fields, beats=None, finding=None),
                     no_power=[("flicker", f"{len(ns)} frames in common, under the {MIN_FRAMES} a beat needs")])
    raw = curves(clip, tracks, ns, dark, progress, stop)
    spectra, per = {}, {}
    scale = None
    for name, f in raw.items():                            # the object's (or members') first, then the background's
        ok = [v for v in f if v is not None]
        bg = name.startswith("background")
        if len(ok) < len(f) or not ok or (not bg and np.median(ok) <= 0) or (bg and not scale):
            per[name] = None
            continue
        if not bg and scale is None:
            scale = float(np.median(ok))                   # the background apertures are measured in this
        fr, F, band, _, _ = spectrum(f, clip.fps, scale if bg else None)
        spectra[name] = dict(fr=fr, F=F, band=band, peak=peak(f, clip.fps, lines, scale if bg else None))
        per[name] = spectra[name]["peak"]
    obj = [n for n in names if per.get(n)]
    bgs = [n for n in raw if n.startswith("background") and per.get(n)]
    fields["curves"] = per
    if not obj:
        return Found("flicker", fields=dict(fields, beats=None, finding=None),
                     no_power=[("flicker", "the object is not brighter than the ring about it on every frame, "
                                           "or its aperture leaves the frame")])
    res = clip.fps / len(ns)
    if not bgs:
        return Found("flicker", fields=dict(fields, beats=None, finding=None),
                     no_power=[("flicker", "no background aperture beside the object could be measured, so there is "
                                           "nothing to hold its beat against")])
    floor = float(np.median([per[b]["amplitude"] for b in bgs]))       # the scene's and the codec's own flicker
    fields["noise_floor"] = floor
    strong = [n for n in obj if per[n]["amplitude"] >= ABOVE * floor]
    # the background shares the beat if, at the object's own frequency, it beats half as strongly or more
    def at(name, hz):
        S = spectra[name]
        k = int(np.argmin(np.abs(S["fr"] - hz)))
        return float(2 * np.abs(S["F"][k]) / np.hanning(len(ns)).sum())
    shared = [b for b in bgs if any(at(b, per[n]["hz"]) >= SHARED * per[n]["amplitude"] for n in strong)]
    pairs = common(spectra, obj, clip.fps, len(ns)) if len(obj) > 1 else []
    fields["pairs"] = pairs
    at_line = [n for n in strong if per[n]["at_the_codec_line_hz"] is not None]
    npw, notes = [], []
    if not strong:
        beats, why = False, (f"no beat reaches {ABOVE:g} times what the background beside it does ({floor:.1%} of the "
                             f"object's brightness, the median of their strongest) in {len(ns)} frames "
                             f"({len(ns) / clip.fps:.1f} s, resolution {res:.2f} Hz)")
    elif shared:
        beats, why = None, (f"the background beside it beats at the same frequency ({', '.join(shared)}): "
                            "not the object's own")
        npw.append(("flicker", why))
    elif len(obj) > 1:
        if any(p["independent"] for p in pairs if set(p["members"]) <= set(strong)):
            beats, why = True, ("members over the same frames beat at different frequencies or out of step, which a "
                                "rhythm of the video cannot do: the beat is theirs")
        else:
            beats, why = None, ("the members beat as one, at one frequency and in step: a rhythm of the video would do "
                                "that" + (f", and it is at the codec's {at_line and per[at_line[0]]['at_the_codec_line_hz']:g} Hz"
                                          if at_line else ""))
            npw.append(("flicker", why))
    elif at_line:
        beats, why = None, (f"it beats at {per[at_line[0]]['hz']:.2f} Hz, within the resolution of the codec's "
                            f"{per[at_line[0]]['at_the_codec_line_hz']:g} Hz, and there is one thing, so nothing tells the "
                            "two apart")
        npw.append(("flicker", why))
    else:
        beats, why = True, (f"it beats at {per[strong[0]]['hz']:.2f} Hz, {per[strong[0]]['amplitude']:.0%} of its brightness, "
                            "clear of the codec's rhythm and not shared by the background beside it")
    fields.update(beats=beats, finding=why, resolution_hz=res)
    notes.append("A beat that is the object's own says it varies; it does not say it is a wingbeat. A tumbling or "
                 "rotating body beats too, and so does a light that blinks.")
    result = {n: f"{per[n]['hz']:.2f} Hz, {per[n]['amplitude']:.1%}, {per[n]['stands']:.0f}x the band"
              + (f" (at the codec's {per[n]['at_the_codec_line_hz']:g} Hz)" if per[n]["at_the_codec_line_hz"] else "")
              for n in obj}
    result["finding"] = why
    files = []
    if out:
        with open(f"{out}_flicker.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["frame", "t_s"] + list(raw))
            for k, n in enumerate(ns):
                w.writerow([n, round((n - 1) / clip.fps, 4)] + ["" if raw[c][k] is None else round(raw[c][k], 2) for c in raw])
        files.append(f"{out}_flicker.csv")
        say(f"wrote {out}_flicker.csv")
    return Found("flicker", result, fields, files=files, no_power=npw, notes=notes)


def said(fields):
    """What `mcdonald flicker` prints, from the fields."""
    L = []
    g = fields.get("codec")
    if g:
        L.append(f"the codec: an I frame every {g['i_period']:g}, an anchor every {g['anchor_period']:g}"
                 + (f"; its rhythm at {', '.join(f'{v:g}' for v in g['lines_hz'])} Hz" if g["lines_hz"] else
                    "; no rhythm of its anchors under Nyquist"))
    if fields.get("frames"):
        L.append(f"frames {fields['first']}-{fields['last']}: {fields['frames']}, resolution "
                 f"{fields.get('resolution_hz') or 0:.2f} Hz")
    for name, p in (fields.get("curves") or {}).items():
        if p:
            L.append(f"  {name}: {p['hz']:.2f} Hz, {p['amplitude']:.1%} of {'the object' if name.startswith('background') else 'its'}"
                     f" brightness, {p['stands']:.0f} times the "
                     f"band's median" + (f"  -- at the codec's {p['at_the_codec_line_hz']:g} Hz" if p["at_the_codec_line_hz"] else ""))
        else:
            L.append(f"  {name}: not measured (not brighter than its ring on every frame, or off the frame)")
    for q in fields.get("pairs") or []:
        L.append(f"  {q['members'][0]} x {q['members'][1]}: {q['hz'][0]:.2f} and {q['hz'][1]:.2f} Hz, "
                 f"{q['phase_deg']:+.0f} deg apart at {q['cross_hz']:.2f}" + ("  (independent)" if q["independent"] else ""))
    if fields.get("finding"):
        L.append(fields["finding"])
    return L


# ---- CLI ----------------------------------------------------------------------------
def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", help="CSV with frame and x/y columns: the object")
    ap.add_argument("--members", help="a groups _members.csv (frame, member, x_px, y_px): each member's beat, and "
                                      "whether they beat as one")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--dark", action="store_true", help="the object is darker than what is round it")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    if not args.track and not args.members:
        ap.error("give --track, or --members")
    with said_to_stderr(args.json) as lines:
        found, clip = _main(args)
    code = 0 if found.fields.get("finding") is not None else vf.EXIT_NOTHING
    if args.json:
        emit(found.envelope("flicker", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


def read_members(path, n0=None, n1=None):
    """{member: {frame: (x, y)}} from a groups _members.csv."""
    out = {}
    for r in csv.DictReader(open(path)):
        n = int(r["frame"])
        if (n0 is None or n >= n0) and (n1 is None or n <= n1):
            out.setdefault(f"member {r['member']}", {})[n] = (float(r["x_px"]), float(r["y_px"]))
    return out


def _main(args):
    video, tag, _ = vf.resolve(args.video)
    tracks = read_members(args.members, args.n0, args.n1) if args.members else {"object": vf.read_track(args.track)}
    frames = [n for t in tracks.values() for n in t]
    clip = vf.Clip(video, args.workdir, args.n0 if args.n0 is not None else min(frames),
                   args.n1 if args.n1 is not None else max(frames))
    out = vf.out_prefix(args.out, tag)
    print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
    found = measure(clip, tracks, dark=args.dark, out=out, progress=to_stderr())
    print("\n".join(said(found.fields)))
    return found, clip


if __name__ == "__main__":
    raise SystemExit(main())
