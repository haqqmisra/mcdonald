"""The readings `flicker.judge` makes beside its call, gathered: what each adds to the fields, the notes and the result.

Four readings stand beside the flicker stage's beat and change none of it (2026-11-13; docs/method.md section 59;
ROADMAP.md 0.3 objectives 4 and 5): the look-alike mark's base rate (E11, `flicker.marked_share`), a line in a
look-alike band held against the background's apertures (`beatlines`), the shape of a beat that sits on a look-alike
the sensor chain can make (T2, `beatshape`), and the beat in the position (K2, `beatpos`), which needs the track and is
`flicker.measure`'s. `beside` is the one call `flicker._judge` makes for the first three, `said` the one that puts their
sentences after everything the stage said before.
"""
import numpy as np
from scipy import ndimage


def beside(fields, obj, strong, use, seg, bgs, mine, scale, fps, lines, top, stamps=None, say=print):
    """The readings from the curves, into `fields`: `lookalike_share` and each beat's own (E11); `band_lines`, each
    object's `beatlines.search` against the apertures beside it (its own, where it is a member with apertures of its
    own); and `morphology`, for a beat of the object's own marked with a look-alike the sensor chain or a supply makes
    (`beatshape.chain_marked`): its depth along the track, its steadiness as read already, and its width outside a fixed
    core where the stamps are given. The arguments are `flicker._judge`'s own: the objects measured, those whose beat is
    their own, the curves as the spectra read them (`use`) and each curve's stretch (`seg`), the background apertures and
    each member's own, the brightness the backgrounds are measured in, the codec's lines and the band's top. A reading
    that cannot be made does not undo the stage's answer: it is said, and left out."""
    from . import beatlines, beatshape, flicker
    table = fields.get("lookalikes") or []
    fields["lookalike_share"] = flicker.marked_share(table, top)
    found, shape = {}, {}
    for n in obj:
        b = fields["beat"][n]
        b["lookalike_share"] = flicker.marked_share(table, top, b["resolution_hz"], b.get("hz_err"))["share"]
        s0, s1 = seg[n]
        r = flicker.deviation(use[n][s0:s1], fps)
        level = np.asarray(use[n][s0:s1], float)
        med = float(np.median(level))
        # the band search reads the curve as a share of its running mean, as the stage does, with that mean held at
        # beatlines.LEVEL_FLOOR of the object's median or more: where the object fades to nothing for a moment the running
        # mean nears nought and the share explodes (PR088's object 2 in its case file: 116 times its brightness on two
        # stretches, which alone made a "line" at 8.09 Hz). Where it never fades so far, the curve is the stage's own
        rb = r
        if med > 0:
            trend = ndimage.uniform_filter1d(level, flicker.trend_frames(fps), mode="nearest")
            if trend.min() < beatlines.LEVEL_FLOOR * med:
                rb = (level - trend) / np.maximum(trend, beatlines.LEVEL_FLOOR * med)
                rb = rb - rb.mean()
        try:
            sc = float(np.median(use[n][s0:s1])) if mine.get(n) else scale
            R = [flicker.deviation(use[c][s0:s1], fps, sc) for c in (mine.get(n) or bgs)
                 if c in seg and seg[c][0] <= s0 and seg[c][1] >= s1 and not any(v is None for v in use[c][s0:s1])]
            found[n] = beatlines.search(rb, R, fps, table, top, flicker.LOW, lines, beat=b if n in strong else None,
                                        peak=None if n in strong else b)
        except Exception as e:
            say(f"  ! the band search was not read ({n}): {type(e).__name__}: {e}")
        try:
            marks = beatshape.chain_marked(b)
            if marks and n in strong:
                st = (fields.get("steadiness") or {}).get(n) or {}
                m = dict(hz=b["hz"], marks=marks, depth=beatshape.depth_along(r, fps, b["hz"], level=level),
                         steadiness={k: st.get(k) for k in ("p", "wanders", "wander_share", "pieces", "why")}, width=None)
                if stamps and n in stamps:
                    ring = (fields.get("ring_px") or {}).get(n) or flicker.RING
                    cut = stamps[n][s0:s1]
                    dark = bool(np.median([np.median(c) for c in cut if c is not None] or [0.0]) < 0)
                    m["width"] = beatshape.width_outside_core(cut, r, fps, b["hz"], ring_in=float(ring[0]), top=top, dark=dark)
                shape[n] = m
        except Exception as e:
            say(f"  ! the beat's shape was not read ({n}): {type(e).__name__}: {e}")
    fields["band_lines"] = found
    if shape:
        fields["morphology"] = shape


def said(fields, names, strong, beats, notes, result):
    """The readings' sentences appended to the stage's `notes` and their lines to its `result`, after everything the stage
    said before: a line a band holds that is not the stage's own beat, and the three readings of a beat's shape."""
    from . import beatlines, beatshape
    several = len(names) > 1
    for n, f in (fields.get("band_lines") or {}).items():
        s = beatlines.said(n, f, several, calls=bool(beats is True and n in strong))
        if s:
            notes.append(s)
            for b in [b for b in beatlines.lines_of(f) if not b["the_beat"]]:
                result[f"line in a band{', ' + n if several else ''}, {b['hz']:.2f} Hz"] = (
                    f"{b['amplitude']:.1%} of its brightness, {b['stands']:.1f} times its neighbours, in the band of {b['band']} "
                    f"({b['hz_band'][0][0]:.1f}-{b['hz_band'][-1][1]:.1f} Hz); the background's apertures {max(b['background']):.1f} at most "
                    f"there, {beatlines._chance_said(b['p'])}")
    for n, m in (fields.get("morphology") or {}).items():
        notes.append(beatshape.said(n, m, several))
        d, w = m.get("depth") or {}, m.get("width") or {}
        result[f"shape of the beat{', ' + n if several else ''}"] = "; ".join(
            ([f"depth {d['least']:.1%}-{d['most']:.1%} in {d['pieces']} pieces, chance {d['p']:.3f} of a steady beat's"] if d.get("power") else
             [f"depth not read ({d.get('why')})"])
            + ([f"width outside a {beatshape.CORE_PX:g}-px core: chance {w['width']['p']:.3f} of no line at the beat"] if w.get("power") else
               [f"width not read ({w.get('why')})"] if w else []))


def printed(fields):
    """What `mcdonald flicker` prints of the readings, from the fields (`flicker.said`): the position's rhythm and how the
    camera's motion stood, each band's line with the background apertures' own standing, and the shape of a beat that
    sits on a look-alike."""
    from . import beatlines, beatpos, beatshape
    L = []
    for name, r in (fields.get("position_beat") or {}).items():
        L.append(f"  {name}, the beat in the position: {beatpos.line_said(r)}")
        wb = (r.get("at_beat") or {}).get("without_brightness") or {}
        if wb.get("px_per_brightness") is not None and wb.get("reach_px") is not None:
            L.append(f"      {wb['px_per_brightness']:.2f} px for a unit of brightness change, where a brightness beating over its background "
                     f"(level {wb['background_level']:.3f} of its brightness) gives {wb['reach_px']:.2f} at most; {wb['share']:.0%} of the "
                     f"rhythm goes with the brightness, chance {wb['p']:.3f} of the rest")
        c = r.get("codec")
        if c:
            L.append(f"      at the codec's {c['at_the_codec_line_hz']:g} Hz: {c['hz']:.2f} Hz, {c['stands']:.1f} times its level"
                     + (" -- the video's own, left out" if c["line"] else ""))
    for name, f in (fields.get("band_lines") or {}).items():
        if not f.get("power"):
            L.append(f"  {name}, a line in a look-alike band: not read -- {f.get('why')}")
            continue
        fa = f.get("false_alarm") or {}
        L.append(f"  {name}, a line in a look-alike band ({f['stretches']} stretches, resolution {f['resolution_hz']:.2f} Hz; the background "
                 f"apertures stand {f['background_over_grain']:.2f} times grain's; each searched as the object, {fa.get('lines', 0)} of "
                 f"{fa.get('searched', 0)} bands held a line):")
        for b in f["bands"]:
            L.append(f"      {b['band']} {b['hz_band'][0][0]:.1f}-{b['hz_band'][-1][1]:.1f} Hz: {b['hz']:.2f} Hz, {b['amplitude']:.1%}, "
                     f"{b['stands']:.1f} times its neighbours (the background's {max(b['background']):.1f}), {beatlines._chance_said(b['p'])}"
                     + (" -- shared by the background" if b["shared"] else "") + (" -- a line" if b["line"] else "")
                     + (", the stage's own beat" if b["line"] and b["the_beat"] else ""))
    for name, m in (fields.get("morphology") or {}).items():
        d, w = m.get("depth") or {}, m.get("width") or {}
        L.append(f"  {name}, the shape of its {m['hz']:.2f}-Hz beat ({len(m['marks'])} look-alikes of the chain or a supply): depth "
                 + (f"{d['least']:.1%}-{d['most']:.1%} in {d['pieces']} pieces of {d['piece_s']:.1f} s, {d['stat']:.1f} apart in their errors against "
                    f"{d['steady_99']:.1f} for 99 in 100 steady beats, p {d['p']:.3f}" if d.get("power") else f"not read ({d.get('why')})")
                 + "; width outside a " + f"{beatshape.CORE_PX:g}-px core "
                 + (f"{w['width']['amplitude']:.1%} at the beat, p {w['width']['p']:.3f} (a planted {w['planted']['change']:.0%} change p "
                    f"{w['planted']['p']:.2g}); pixel area p {w['area']['p']:.2g}" if w.get("power") and w.get("area") else
                    f"p {w['width']['p']:.3f}" if w.get("power") else f"not read ({w.get('why')})" if w else "not read (no stamps)"))
    return L
