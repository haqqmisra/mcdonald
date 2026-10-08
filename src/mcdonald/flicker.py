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

The beat is looked for in windows of WINDOW_S seconds along the track as well as over
the whole of it (Jacob, 2026-09-29, a Galileo Project bird, "flyer 5": one spectrum over its
5.9 s -- a faint approach and then two seconds of bright flapping at a rate that changes --
peaked at 5.11 Hz, between the paper's 3.90 and 7.80; over the flapping alone the same
curve gives 7.88 and 3.94). Each window is held to the same tests; the clearest that passes
(the highest peak over its band) gives the frequency where it is clearer than the whole
track's. And a peak with another at half its frequency at least HALF as strong is the
double of a beat: a wingbeat's brightness changes twice a stroke, so its second harmonic
is often the stronger. The fundamental is what is reported, with its double named.

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
WINDOW_S = 2.0       # s: the windows a beat is looked for in along the track, an eighth of a window apart, the last one always
HALF = 0.5           # a peak at half the strongest's frequency, this share of it or more, makes the strongest a double


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


def harmonics(f, fps, scale=None):
    """The strongest beat of a curve as a fundamental and its double: (fundamental Hz, double Hz or
    None, the share of the strongest that a peak at half its frequency has, the share at double).
    With a peak at half at least HALF of the strongest, the strongest is the double and the
    fundamental the half; else the strongest is the fundamental, and a double is named where a
    peak at twice it has at least HALF of it."""
    fr, F, band, wsum, _ = spectrum(f, fps, scale)
    P = np.abs(F) ** 2
    k = int(np.argmax(np.where(band, P, -1)))
    res = fps / len(f)

    def share(hz):
        m = band & (np.abs(fr - hz) <= 1.5 * res)
        return float(np.sqrt(P[m].max() / P[k])) if m.any() and P[k] > 0 else 0.0
    half, double = share(fr[k] / 2), share(fr[k] * 2)
    if half >= HALF:
        return float(fr[k] / 2), float(fr[k]), half, double
    return float(fr[k]), (float(fr[k] * 2) if double >= HALF else None), half, double


def windows(raw, name, bgs, ns, fps, lines):
    """The object's beat in windows of WINDOW_S along the track, each held to the tests the whole
    track is: [{first, last, hz, amplitude, stands, resolution_hz, floor, shared, at_the_codec_line_hz,
    fundamental_hz, double_hz, passes}]. Windows where an aperture leaves the frame are left out."""
    n = len(ns)
    W = max(MIN_FRAMES, int(round(WINDOW_S * fps)))
    step = max(1, W // 8)
    starts = list(range(0, n - W + 1, step))
    if starts and starts[-1] != n - W:
        starts.append(n - W)                                   # the last window too: the flapping may be at the track's end
    out = []
    for s in starts:
        f = raw[name][s:s + W]
        if any(v is None for v in f) or np.median(f) <= 0:
            continue
        scale = float(np.median(f))
        p = peak(f, fps, lines)
        floors, shared = [], False
        for b in bgs:
            g = raw[b][s:s + W]
            if any(v is None for v in g):
                continue
            floors.append(peak(g, fps, (), scale)["amplitude"])
            fr, F, _, wsum, _ = spectrum(g, fps, scale)
            if 2 * np.abs(F[int(np.argmin(np.abs(fr - p["hz"])))]) / wsum >= SHARED * p["amplitude"]:
                shared = True
        if not floors:
            continue
        floor = float(np.median(floors))
        fund, dbl, _, _ = harmonics(f, fps)
        out.append(dict(first=int(ns[s]), last=int(ns[s + W - 1]), hz=p["hz"], amplitude=p["amplitude"], stands=p["stands"],
                        resolution_hz=p["resolution_hz"], floor=floor, shared=shared, at_the_codec_line_hz=p["at_the_codec_line_hz"],
                        fundamental_hz=fund, double_hz=dbl,
                        passes=bool(p["amplitude"] >= ABOVE * floor and not shared and p["at_the_codec_line_hz"] is None)))
    return out


def curves(clip, tracks, ns, dark=False, progress=None, stop=None, about=None):
    """{name: brightness on each frame of ns} for each track, and for BACKGROUND apertures about
    the track `about` (the first, if not named) -- None where the aperture leaves the frame or a
    mask covers it."""
    pos = {name: smoothed(t, ns) for name, t in tracks.items()}
    first = pos[about] if about in pos else next(iter(pos.values()))
    for dx, dy in BACKGROUND:
        pos[f"background {dx:+d},{dy:+d}"] = (first[0] + dx, first[1] + dy)
    out = {name: [] for name in pos}
    for k, n in enumerate(counted(ns, progress, stop, "Flicker")):
        g = vf.grey_of(clip.rgb(n))
        for name, (x, y) in pos.items():
            out[name].append(brightness(g, x[k], y[k], dark=dark and not name.startswith("background")))
    return out


def common(raw, seg, members, ns, fps, lines=()):
    """Whether members beat as one, over the frames each pair has in common (a flock's members come and go --
    PR135, 2026-10-08 -- so each pair is taken over its own overlap, MIN_FRAMES or more): pairs, each at its own
    peak there, with the phase between them at the cross-spectrum's peak -- and `independent`: two at frequencies
    further apart than the resolution, or at one frequency more than APART_DEG out of step."""
    pairs = []
    for a in range(len(members)):
        for b in range(a + 1, len(members)):
            ma, mb = members[a], members[b]
            lo, hi = max(seg[ma][0], seg[mb][0]), min(seg[ma][1], seg[mb][1])
            if hi - lo < MIN_FRAMES:
                continue
            fa, fb = raw[ma][lo:hi], raw[mb][lo:hi]
            if any(v is None for v in fa) or any(v is None for v in fb):
                continue
            pa, pb = peak(fa, fps, lines), peak(fb, fps, lines)
            fr, Fa, band, _, _ = spectrum(fa, fps)
            _, Fb, _, _, _ = spectrum(fb, fps)
            X = Fa * np.conj(Fb)
            k = int(np.argmax(np.where(band, np.abs(X), -1)))
            apart = abs(pa["hz"] - pb["hz"])
            phase = float(np.degrees(np.angle(X[k])))
            pairs.append(dict(members=[ma, mb], hz=[pa["hz"], pb["hz"]], frames=[int(ns[lo]), int(ns[hi - 1])],
                              apart_hz=apart, cross_hz=float(fr[k]), phase_deg=phase,
                              independent=bool(apart > fps / (hi - lo) or abs(phase) > APART_DEG)))
    return pairs


def measure(clip, tracks, dark=False, out=None, say=print, progress=None, stop=None):
    """The stage: each track's beat, the background apertures' about the first, the codec's rhythm,
    and -- with two tracks or more -- whether they beat as one. `tracks` is {name: {frame: (x, y)}}:
    the object's track, or the members of a group (groups.members). Writes <out>_flicker.csv."""
    g = read_gop(clip.video, clip.fps) if getattr(clip, "video", None) else None
    lines = (g or {}).get("lines_hz") or []
    names = list(tracks)
    # Each track over its own frames. A group's members come and go -- PR135's flock, 2026-10-08: one seen from
    # frame 1240, another from 1283 -- and the frames they all share can be none; so the curves are read over
    # the union, and each is measured over its own span, the pairs over what each pair has in common.
    spans = {}
    for name, t in tracks.items():
        fs = [n for n in t if clip.n0 <= n <= clip.n1]
        if fs:
            spans[name] = (min(fs), max(fs))
    fields = dict(frames=0, first=None, last=None, codec=g, aperture_px=APERTURE, tracks=names, spans=spans)
    if not spans:
        return Found("flicker", fields=dict(fields, beats=None, finding=None),
                     no_power=[("flicker", "no track on the frames that are open")])
    lo, hi = min(a for a, _ in spans.values()), max(b for _, b in spans.values())
    ns = list(range(lo, hi + 1))
    fields.update(frames=len(ns), first=lo, last=hi)
    if max(b - a + 1 for a, b in spans.values()) < MIN_FRAMES:
        return Found("flicker", fields=dict(fields, beats=None, finding=None),
                     no_power=[("flicker", f"{len(ns)} frames{' in common' if len(names) > 1 else ''}, under the {MIN_FRAMES} a beat needs")])
    # the background apertures go with the track seen longest (a group's first member may be seen briefly:
    # PR135's object 2, 42 frames of its first), and the stretch reported is that track's
    first = max(spans, key=lambda name: spans[name][1] - spans[name][0])
    raw = curves(clip, tracks, ns, dark, progress, stop, about=first)
    k0 = {name: (a - lo, b - lo + 1) for name, (a, b) in spans.items()}
    for name in names:                                     # outside its own span a track's position is its end's held: not measured
        a, b = k0.get(name, (0, 0))
        raw[name] = [None] * a + raw[name][a:b] + [None] * (len(ns) - b)
    for name in list(raw):                                 # the background apertures go with the member seen longest
        if name.startswith("background"):
            a, b = k0.get(first, (0, 0))
            raw[name] = [None] * a + raw[name][a:b] + [None] * (len(ns) - b)
    # each curve's own stretch: the ends where an aperture leaves the frame are trimmed away (a bird flying out at
    # the frame's top, flyer 5's last frames); only a curve with a hole in the middle is refused below
    seg = {}
    for name, f in raw.items():
        idx = [k for k, v in enumerate(f) if v is not None]
        if idx:
            seg[name] = (idx[0], idx[-1] + 1)
    if first in seg:
        s0, s1 = seg[first]
        if (s0, s1) != k0[first]:
            fields["trimmed"] = dict(start=s0 - k0[first][0], end=k0[first][1] - s1)
        fields.update(frames=s1 - s0, first=ns[s0], last=ns[s1 - 1])       # the stretch reported: the object's (the member seen longest)
    if not seg or max(b - a for a, b in seg.values()) < MIN_FRAMES:
        return Found("flicker", fields=dict(fields, beats=None, finding=None),
                     no_power=[("flicker", f"{fields['frames']} frames with the object's aperture inside the frame, under the {MIN_FRAMES} a beat needs")])
    spectra, per = {}, {}
    scale = None
    for name, f in raw.items():                            # the object's (or members') first, then the background's
        bg = name.startswith("background")
        s = seg.get(name)
        own = f[s[0]:s[1]] if s else []
        ok = [v for v in own if v is not None]
        if len(ok) < len(own) or len(own) < MIN_FRAMES or (not bg and np.median(ok) <= 0) or (bg and not scale):
            per[name] = None
            continue
        if not bg and scale is None:
            scale = float(np.median(ok))                   # the background apertures are measured in this
        fr, F, band, wsum, _ = spectrum(own, clip.fps, scale if bg else None)
        spectra[name] = dict(fr=fr, F=F, band=band, wsum=wsum, peak=peak(own, clip.fps, lines, scale if bg else None))
        per[name] = spectra[name]["peak"]
    obj = [n for n in names if per.get(n)]
    bgs = [n for n in raw if n.startswith("background") and per.get(n)]
    fields["curves"] = per
    fields["short"] = [n for n in names if n in seg and seg[n][1] - seg[n][0] < MIN_FRAMES]     # members too brief for a beat
    if not obj:
        return Found("flicker", fields=dict(fields, beats=None, finding=None),
                     no_power=[("flicker", "the object is not brighter than the ring about it on every frame, "
                                           "or its aperture leaves the frame")])
    res = clip.fps / max(1, fields["frames"])         # of the stretch reported: the object's (the member seen longest)
    if not bgs:
        return Found("flicker", fields=dict(fields, beats=None, finding=None),
                     no_power=[("flicker", "no background aperture beside the object could be measured, so there is "
                                           "nothing to hold its beat against")])
    floor = float(np.median([per[b]["amplitude"] for b in bgs]))       # the scene's and the codec's own flicker
    fields["noise_floor"] = floor
    # the beat in windows along the track, and what is reported for each object: the clearest window that passes
    # where it is clearer than the whole track, else the whole track -- as a fundamental with its double named
    fields["windows"], fields["beat"] = {}, {}
    for n in obj:
        s0, s1 = seg[n]
        own = {m: raw[m][s0:s1] for m in [n] + bgs}
        wins = windows(own, n, bgs, ns[s0:s1], clip.fps, lines)
        fields["windows"][n] = wins
        passing = [w for w in wins if w["passes"]]
        best = max(passing, key=lambda w: w["stands"]) if passing else None
        fund, dbl, _, _ = harmonics(own[n], clip.fps)
        whole = dict(first=ns[s0], last=ns[s1 - 1], hz=fund, double_hz=dbl, amplitude=per[n]["amplitude"], stands=per[n]["stands"],
                     resolution_hz=per[n]["resolution_hz"], source="the whole track")
        if best is not None and best["stands"] > per[n]["stands"]:
            use = dict(first=best["first"], last=best["last"], hz=best["fundamental_hz"], double_hz=best["double_hz"],
                       amplitude=best["amplitude"], stands=best["stands"], resolution_hz=best["resolution_hz"],
                       source=f"the clearest of {len(passing)} windows of {WINDOW_S:g} s that beat, of {len(wins)}")
        else:
            use = whole
        clear = [w for w in passing if best is not None and w["stands"] >= 0.5 * best["stands"]]     # the clear windows' range
        use["hz_range"] = [min(w["fundamental_hz"] for w in clear), max(w["fundamental_hz"] for w in clear)] if clear else None
        use["windows_passing"] = len(passing)
        use["windows"] = len(wins)
        fields["beat"][n] = use
    strong = [n for n in obj if per[n]["amplitude"] >= ABOVE * floor or fields["beat"][n]["windows_passing"]]
    # the background shares the beat if, at the object's own frequency, it beats half as strongly or more
    def at(name, hz):
        S = spectra[name]
        k = int(np.argmin(np.abs(S["fr"] - hz)))
        return float(2 * np.abs(S["F"][k]) / S["wsum"])
    shared = [b for b in bgs if any(at(b, per[n]["hz"]) >= SHARED * per[n]["amplitude"] for n in strong)]
    pairs = common(raw, seg, obj, ns, clip.fps, lines) if len(obj) > 1 else []
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
        elif not pairs:
            beats, why = None, (f"no two members share the {MIN_FRAMES} frames it takes to hear whether they beat as one")
            npw.append(("flicker", why))
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
        b = fields["beat"][strong[0]]
        beats, why = True, (f"it beats at {b['hz']:.2f} Hz" + (f" (and at {b['double_hz']:.2f}, its double)" if b["double_hz"] else "")
                            + f", {b['amplitude']:.0%} of its brightness, over frames {b['first']}–{b['last']}"
                            + (f" ({b['source']})" if b["source"] != "the whole track" else "")
                            + ", clear of the codec's rhythm and not shared by the background beside it")
    fields.update(beats=beats, finding=why, resolution_hz=res)
    notes.append("A beat that is the object's own says it varies; it does not say it is a wingbeat. A tumbling or "
                 "rotating body beats too, and so does a light that blinks.")
    result = {n: f"{fields['beat'][n]['hz']:.2f} Hz" + (f" (and {fields['beat'][n]['double_hz']:.2f}, its double)" if fields["beat"][n]["double_hz"] else "")
              + f", {fields['beat'][n]['amplitude']:.1%}, {fields['beat'][n]['stands']:.0f}x the band, frames "
              f"{fields['beat'][n]['first']}–{fields['beat'][n]['last']}"
              + (f" (at the codec's {per[n]['at_the_codec_line_hz']:g} Hz)" if per[n]["at_the_codec_line_hz"] else "")
              for n in obj}
    result["finding"] = why
    files = []
    if out:
        with open(f"{out}_flicker.csv", "w", newline="", encoding="utf-8") as f:
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
    for name, b in (fields.get("beat") or {}).items():
        L.append(f"  {name}, in windows of {WINDOW_S:g} s along the track: {b['windows_passing']} of {b['windows']} beat"
                 + (f", at {b['hz_range'][0]:.2f}-{b['hz_range'][1]:.2f} Hz" if b.get("hz_range") else "")
                 + f"; reported: {b['hz']:.2f} Hz" + (f" and its double {b['double_hz']:.2f}" if b["double_hz"] else "")
                 + f", {b['amplitude']:.1%}, {b['stands']:.0f}x, frames {b['first']}-{b['last']} ({b['source']})")
    for q in fields.get("pairs") or []:
        L.append(f"  {q['members'][0]} x {q['members'][1]}: {q['hz'][0]:.2f} and {q['hz'][1]:.2f} Hz, "
                 f"{q['phase_deg']:+.0f} deg apart at {q['cross_hz']:.2f}"
                 + (f" over frames {q['frames'][0]}-{q['frames'][1]}" if q.get("frames") else "")
                 + ("  (independent)" if q["independent"] else ""))
    if fields.get("short"):
        L.append(f"  too brief for a beat (under {MIN_FRAMES} frames): " + ", ".join(fields["short"]))
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
    for r in csv.DictReader(open(path, newline="", encoding="utf-8")):
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
