"""Is the object one thing, or several moving together -- and do they keep their places?

A linked track follows one position a frame. When what was marked is a group -- PR135's
"6X SMALL SPHERICAL OBJECTS GROUPED TOGETHER", the "fleet" clips -- that position is the
brightest member or a blend of several, `propose` lists the group as one thing, and
nothing says there is more than one. The PR135 agent (2026-09-22, its items 3, 8 and 22)
had to write its own member tracker to ask the question that tells a flock from a
formation: **do the members keep their relative positions?** A rigid formation holds
every separation, give or take how well a position is measured; birds do not, and
PR135's six "keep reshuffling".

Method (`members`, then `rigidity`):

1. **Spots near the track.** On every frame of the track, the detector at a small scale
   (a member of a group is a point, and the object's own size is the group's) in a
   window about the track's position, `radius` px. Only spots answering at least
   `LIKE` of the strongest in that window count: a member of a group is like the
   others; and only those with background all round them (`propose.all_round`, as
   Find asks it): the small detector fires on the rim of a disc too, all the way round,
   and six such spots would be read as a rigid group of six. The detector is the
   package's one (`forensics.source_candidates`, every spot).
2. **Not on the sensor.** A spot at the same place on the screen on half the frames,
   while the group moves, is a defect of the sensor (PR135 has eleven, among its 18
   longest tracks), and is left out -- `forensics.on_the_sensor`.
3. **Members, frame to frame.** The group's own shift between two frames is the offset
   that brings the most spots onto spots (a vote, as the agent's `group_shift`); each
   member is predicted by that shift and half its own last motion within the group, and
   spots are assigned to members by least total distance (Hungarian), within a gate of
   `GATE` px and `GATE_GROW` more a frame the member was not seen. A spot left over is a
   new member; a member not seen for `MAX_MISS` frames has ended. Identities can be
   lost where two members merge into one spot: a member that ends and one that starts
   are not joined up.
4. **Rigid, or not.** For every two members seen together on `MIN_SHARED` frames or
   more, the separation, frame by frame, and how much it wanders about a straight line
   in time (which a slow zoom or a change of aspect gives a rigid group). That is held
   against what the members' own position noise alone would give (each member's jitter
   about a 7-frame running median): a rigid group's pairs wander by about that; a group
   whose members change places, by many times it. `rigid` is true when every such pair
   wanders by at most RIGID times the noise, false when the median pair wanders by more
   than SHUFFLE times it and by more than a pixel, and None between, or with fewer than
   two members long enough to ask.

What it cannot do: say what the members are. Rigid or shuffling is a property of the
formation in the image; birds, a formation of aircraft or drifting debris each still
need the rest of the case. And the separations are in pixels, not metres, for the
reasons they always are.
"""
import csv

import numpy as np
from scipy.optimize import linear_sum_assignment

from . import forensics as vf
from .progress import counted, to_stderr
from .report import Found, emit, inputs_of, said_to_stderr

RADIUS = 120.0       # px about the track's position that members are looked for in: PR135's six span 155 px,
                     # and at 60 the outer ones are lost
SIZE = 5.0           # the detector's scale for a member: a point
LIKE = 0.3           # a member answers at least this share of the strongest spot in the window
MIN_RESP = 10.0      # and at least this, whatever the strongest
GATE, GATE_GROW = 4.0, 1.5
MAX_MISS = 5
MIN_FRAMES = 30      # a member followed this long counts
MIN_SHARED = 30      # two members seen together this long are compared
RIGID, SHUFFLE = 2.0, 3.0
ALL_ROUND = 0.1      # a member has some background all round it (propose.all_round): the rim of a disc has none
                     # (0.0), and PR135's members, close together, go down to 0.23
STILL = 20.0         # px: a track that moves less against the background cannot tell the scene near it from members
POINT_SIZE = 9.0     # `run` asks this of an object linked as a spot no wider: a larger one has a rim of its own


def spots_near(clip, n, xy, masks, rows=None, radius=RADIUS, size=SIZE, dark=False, rgb=None, bad=None):
    """[(x, y, response)] of the spots within `radius` of xy on frame n, strongest first,
    those answering at least LIKE of the strongest (and MIN_RESP)."""
    rgb = clip.rgb(n) if rgb is None else rgb
    bad = vf.frame_mask(rgb, masks, rows, n, grow=6) if bad is None else bad
    pad = int(radius + 4 * size)
    x0, y0 = max(int(xy[0]) - pad, 0), max(int(xy[1]) - pad, 0)
    x1, y1 = min(int(xy[0]) + pad + 1, clip.W), min(int(xy[1]) + pad + 1, clip.H)
    g = rgb[y0:y1, x0:x1].mean(2)
    got = vf.source_candidates(g, bad[y0:y1, x0:x1], size, dark, n_max=None, min_resp=MIN_RESP)
    got = [(x + x0, y + y0, v) for x, y, v in got if np.hypot(x + x0 - xy[0], y + y0 - xy[1]) <= radius]
    if not got:
        return []
    top = max(v for _, _, v in got)
    from .propose import all_round
    return [(x, y, v) for x, y, v in got if v >= LIKE * top and all_round(g, x - x0, y - y0, -1 if dark else 1, size) >= ALL_ROUND]


def group_shift(prev, cur, guess, reach=15.0, tol=2.0):
    """The group's shift from `prev` to `cur` (arrays of x, y): of every spot-to-spot offset
    within `reach` of `guess` (the track's own step), the one that brings the most spots of
    prev within `tol` of one of cur -- refined as the mean of those matches."""
    if not len(prev) or not len(cur):
        return np.asarray(guess, float)
    offs = (cur[None, :, :] - prev[:, None, :]).reshape(-1, 2)
    offs = offs[np.hypot(*(offs - guess).T) <= reach]
    if not len(offs):
        return np.asarray(guess, float)
    best, score = np.asarray(guess, float), -1.0
    for o in offs:
        d = np.hypot(*(prev[:, None, :] + o - cur[None, :, :]).transpose(2, 0, 1)).min(1)
        sc = (d <= tol).sum() - 1e-3 * np.hypot(*(o - guess))
        if sc > score:
            best, score = o, sc
    d = np.hypot(*(prev[:, None, :] + best - cur[None, :, :]).transpose(2, 0, 1))
    i, j = np.nonzero(d <= tol)
    return (cur[j] - prev[i]).mean(0) if len(i) else best


def members(clip, track, masks, rows=None, radius=RADIUS, size=SIZE, dark=False, progress=None, stop=None):
    """(followed points {id: {frame: (x, y, response)}}, spots {frame: [...]}, on the sensor count,
    the background's own displacement since the first frame {frame: (dx, dy)})."""
    from .propose import background_shift
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    spots, bg, last = {}, {}, None
    for n in counted(ns, progress, stop, "Groups"):
        rgb = clip.rgb(n)
        bad = vf.frame_mask(rgb, masks, rows, n, grow=6)
        g = rgb.mean(2).astype(np.float32)
        if last is None:
            bg[n] = (0.0, 0.0)
        else:
            d = background_shift(last[1], g, ~(bad | last[2]))
            bg[n] = (bg[last[0]][0] + d[0], bg[last[0]][1] + d[1])
        last = (n, g, bad)
        spots[n] = spots_near(clip, n, track[n], masks, rows, radius, size, dark, rgb, bad)
    fixed = vf.on_the_sensor({n: [(x, y) for x, y, _ in s] for n, s in spots.items()},
                             windows={n: (track[n][0], track[n][1], radius) for n in spots})
    spots = {n: [q for i, q in enumerate(s) if (n, i) not in fixed] for n, s in spots.items()}

    tracks, live, nid = {}, {}, 0                   # live: id -> [pos, rel_vel, misses]
    prev_n = None
    for n in ns:
        cur = np.array([(x, y) for x, y, _ in spots[n]]).reshape(-1, 2)
        if prev_n is None or not live:
            for k, (x, y, v) in enumerate(spots[n]):
                tracks[nid] = {n: (x, y, v)}
                live[nid] = [np.array([x, y]), np.zeros(2), 0]
                nid += 1
            prev_n = n
            continue
        ids = list(live)
        pos = np.array([live[i][0] for i in ids])
        guess = np.subtract(track[n], track[prev_n])
        seen = np.array([tracks[i][prev_n][:2] for i in ids if prev_n in tracks[i]]).reshape(-1, 2)
        shift = group_shift(seen, cur, guess)
        pred = pos + shift * (n - prev_n) / max(n - prev_n, 1) + 0.5 * np.array([live[i][1] for i in ids])
        taken = set()
        if len(cur):
            D = np.hypot(*(pred[:, None, :] - cur[None, :, :]).transpose(2, 0, 1))
            for a, b in zip(*linear_sum_assignment(D)):
                i = ids[a]
                if D[a, b] <= GATE + GATE_GROW * live[i][2]:
                    x, y, v = spots[n][b]
                    new = np.array([x, y])
                    live[i][1] = (new - live[i][0] - shift) / (1 + live[i][2])
                    live[i][0], live[i][2] = new, 0
                    tracks[i][n] = (x, y, v)
                    taken.add(b)
        for a, i in enumerate(ids):
            if n not in tracks[i]:
                live[i][0] = pred[a]
                live[i][2] += 1
                if live[i][2] > MAX_MISS:
                    del live[i]
        for b, (x, y, v) in enumerate(spots[n]):
            if b not in taken:
                tracks[nid] = {n: (x, y, v)}
                live[nid] = [np.array([x, y]), np.zeros(2), 0]
                nid += 1
        prev_n = n
    return tracks, spots, len(fixed), bg


def _noise(t):
    """A member's position noise: the rms, per axis, of its jitter about a 7-frame running median."""
    ns = sorted(t)
    xy = np.array([t[n][:2] for n in ns])
    if len(xy) < 7:
        return None
    med = np.array([np.median(xy[max(0, k - 3):k + 4], axis=0) for k in range(len(xy))])
    return float(np.sqrt(((xy - med) ** 2).mean()))


def rigidity(tracks):
    """Fields: the members followed long enough, their position noise, and every pair seen
    together long enough -- separation, how much it wanders about a line in time, and that
    against the noise -- and `rigid`, as the module says."""
    long = {i: t for i, t in tracks.items() if len(t) >= MIN_FRAMES}
    noise = {i: _noise(t) for i, t in long.items()}
    pairs = []
    ids = sorted(long)
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            A, B = long[ids[a]], long[ids[b]]
            both = sorted(set(A) & set(B))
            if len(both) < MIN_SHARED:
                continue
            s = np.array([np.hypot(A[n][0] - B[n][0], A[n][1] - B[n][1]) for n in both])
            t = np.array(both, float)
            fit = np.polyval(np.polyfit(t, s, 1), t)
            wander = float(np.sqrt(((s - fit) ** 2).mean()))
            expect = float(np.hypot(noise[ids[a]] or 0, noise[ids[b]] or 0)) or 1e-9     # a separation's own noise
            pairs.append(dict(members=[ids[a], ids[b]], frames=len(both), first=both[0], last=both[-1],
                              separation_px=float(s.mean()), separation_range_px=float(s.max() - s.min()),
                              wander_px=wander, noise_px=expect, wander_over_noise=wander / expect))
    if not pairs:
        rigid, why = None, (f"fewer than two members were followed together for {MIN_SHARED} frames, so whether they "
                            "keep their places cannot be asked")
    else:
        r = np.array([p["wander_over_noise"] for p in pairs])
        w = np.array([p["wander_px"] for p in pairs])
        if r.max() <= RIGID:
            rigid, why = True, (f"every pair of members keeps its separation to within {RIGID:g} times what the "
                                f"members' own position noise gives (at most {r.max():.1f} times): a rigid group")
        elif np.median(r) > SHUFFLE and np.median(w) > 1.0:
            rigid, why = False, (f"the separations wander by {np.median(w):.1f} px about a steady change, "
                                 f"{np.median(r):.1f} times what position noise gives (the median pair): the members "
                                 "change places, as a flock does and a formation does not")
        else:
            rigid, why = None, (f"the pairs wander by {np.median(r):.1f} times the position noise (the median pair, "
                                f"{r.min():.1f} to {r.max():.1f}): neither clearly held nor clearly shuffling")
    return dict(members_followed=len(long), noise_px={str(i): v for i, v in noise.items()}, pairs=pairs,
                rigid=rigid, finding=why)


def measure(clip, track, masks=None, rows=None, radius=RADIUS, size=SIZE, dark=False, out=None, say=print,
            progress=None, stop=None):
    """The stage: how many points the tracked thing is, frame by frame, and if more than one,
    whether they keep their places. Writes <out>_members.csv and <out>_members.png."""
    masks = masks if masks is not None else vf.static_masks(clip)
    tracks, spots, fixed, bg = members(clip, track, masks, rows, radius, size, dark, progress, stop)
    moved = _against(track, bg, sorted(spots))
    tracks = {i: t for i, t in tracks.items() if with_the_group(t, track, bg)} if moved >= STILL else tracks
    counts = np.array([sum(n in t for t in tracks.values() if len(t) >= MIN_FRAMES) for n in sorted(spots)])
    fields = dict(frames=len(spots), radius_px=radius, detector_size_px=size, dark=dark,
                  points_per_frame=None if not len(counts) else dict(median=float(np.median(counts)),
                                                                     max=int(counts.max()), min=int(counts.min())),
                  on_the_sensor=fixed, member_tracks=len(tracks), track_against_background_px=moved,
                  scene_told_apart=bool(moved >= STILL))
    if not len(counts):
        return Found("groups", fields=dict(fields, several=None, rigid=None),
                     no_power=[("groups", "no frame of the track is in the clip")])
    if counts.max() == 0:
        why = (f"no point-like thing near the track moves with it for {MIN_FRAMES} frames: not a group of points "
               "(a thing wider than a point, with no background all round a spot on it, is not one)")
        return Found("groups", dict(finding=why), dict(fields, several=False, rigid=None, finding=why))
    several = bool(np.median(counts) >= 2)
    fields["several"] = several
    rig = rigidity(tracks) if several else dict(members_followed=None, noise_px={}, pairs=[], rigid=None,
                                                finding="one point on most frames: a single thing, not a group")
    fields.update(rig)
    result = dict(points=f"{np.median(counts):g} a frame moving with the track (median; {counts.min()}-{counts.max()}), "
                         f"within {radius:g} px of it" + (f", {fixed} spots on the sensor left out" if fixed else ""),
                  finding=rig["finding"])
    notes = [] if moved >= STILL else [
        f"The track moves only {moved:.0f} px against the background over these frames, so points of the scene near "
        "it cannot be told from members of a group by their motion: every point followed near it is counted."]
    files = []
    if out:
        with open(f"{out}_members.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["frame", "member", "x_px", "y_px", "response"])
            for i, t in sorted(tracks.items()):
                if len(t) >= MIN_FRAMES:
                    for n, (x, y, v) in sorted(t.items()):
                        w.writerow([n, i, round(x, 2), round(y, 2), round(v, 1)])
        files.append(f"{out}_members.csv")
        if several:
            figure(tracks, track, f"{out}_members.png")
            files.append(f"{out}_members.png")
        say(f"wrote {', '.join(files)}")
    npw = [] if rig["rigid"] is not None or not several else [("groups: rigid or not", rig["finding"])]
    long = {i: {n: xyv[:2] for n, xyv in t.items()} for i, t in tracks.items() if len(t) >= MIN_FRAMES}
    return Found("groups", result, fields, files=files, no_power=npw, notes=notes, carry=long if several else None)


def _step(p, a, b):
    return np.subtract(p[b][:2], p[a][:2])


def _against(track, bg, ns):
    """How far the track moves against the background from the first of `ns` to the last."""
    return float(np.hypot(*(_step(track, ns[0], ns[-1]) - _step(bg, ns[0], ns[-1])))) if len(ns) > 1 else 0.0


def with_the_group(t, track, bg):
    """Whether a followed point moves with the track rather than with the background (the scene's
    own shift, `propose.background_shift`, frame to frame): over the frames it was followed, its
    displacement is nearer the track's than the background's. A point of the scene the group
    passes moves with the scene, however the camera pans; a member of a flock moves with the
    group, give or take its shuffling (PR135's: up to half of the group's motion on the screen)."""
    ns = [n for n in sorted(t) if n in track and n in bg]
    if len(ns) < 2:
        return False
    own = _step(t, ns[0], ns[-1])
    return bool(np.hypot(*(own - _step(track, ns[0], ns[-1]))) < np.hypot(*(own - _step(bg, ns[0], ns[-1]))))


def figure(tracks, track, path):
    """Each member followed long enough, as its place relative to the track, frame by frame."""
    from . import figures
    plt = figures.setup()
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(10, 4.6))
    for i, t in sorted(tracks.items()):
        if len(t) < MIN_FRAMES:
            continue
        ns = [n for n in sorted(t) if n in track]
        dx = [t[n][0] - track[n][0] for n in ns]
        dy = [t[n][1] - track[n][1] for n in ns]
        ax.plot(dx, dy, ".", ms=2, label=str(i))
        bx.plot(ns, np.hypot(dx, dy), lw=1)
    ax.invert_yaxis()
    ax.set_aspect("equal", "datalim")
    ax.set_xlabel("x from the track, px")
    ax.set_ylabel("y from the track, px")
    ax.set_title("each member, where it is in the group")
    bx.set_xlabel("frame")
    bx.set_ylabel("px from the track")
    bx.set_title("a rigid group keeps these; a flock does not")
    figures.save(fig, path, tight=True)


def said(fields):
    """What `mcdonald groups` prints, from the fields."""
    L = []
    p = fields.get("points_per_frame")
    if p:
        L.append(f"points moving with the track, within {fields['radius_px']:g} px of it: {p['median']:g} a frame "
                 f"(median; {p['min']}-{p['max']})" + (f"; {fields['on_the_sensor']} spots on the sensor left out"
                                              if fields["on_the_sensor"] else ""))
    for q in fields.get("pairs", []):
        L.append(f"  members {q['members'][0]} and {q['members'][1]}: {q['frames']} frames together "
                 f"({q['first']}-{q['last']}), {q['separation_px']:.1f} px apart (range {q['separation_range_px']:.1f}), "
                 f"wandering {q['wander_px']:.2f} px = {q['wander_over_noise']:.1f} x the position noise")
    L.append(fields.get("finding", ""))
    return L


# ---- CLI ----------------------------------------------------------------------------
def main():
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--track", required=True, help="CSV with frame and x/y columns: the group, as linked")
    ap.add_argument("--workdir")
    ap.add_argument("--n0", type=int)
    ap.add_argument("--n1", type=int)
    ap.add_argument("--radius", type=float, default=RADIUS, help=f"px about the track to look for members in (default {RADIUS:g})")
    ap.add_argument("--size", type=float, default=SIZE, help=f"the detector's scale for a member, px (default {SIZE:g})")
    ap.add_argument("--dark", action="store_true", help="the members are darker than what is round them")
    ap.add_argument("--mask-rows")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    with said_to_stderr(args.json) as lines:
        found, clip = _main(args)
    code = 0 if found.fields.get("several") is not None else vf.EXIT_NOTHING
    if args.json:
        emit(found.envelope("groups", inputs_of(args), clip, said=lines, exit_code=code,
                            error=None if not code else found.no_power[0][1]))
    return code


def _main(args):
    video, tag, _ = vf.resolve(args.video)
    track = vf.read_track(args.track)
    n0 = args.n0 if args.n0 is not None else min(track)
    n1 = args.n1 if args.n1 is not None else max(track)
    clip = vf.Clip(video, args.workdir, n0, n1)
    out = vf.out_prefix(args.out, tag)
    print(f"{video.name}: {clip.W}x{clip.H}, {clip.fps:.3f} fps, frames {clip.n0}-{clip.n1}")
    found = measure(clip, track, rows=vf.parse_rows(args.mask_rows), radius=args.radius, size=args.size,
                    dark=args.dark, out=out, progress=to_stderr())
    print("\n".join(said(found.fields)))
    return found, clip


if __name__ == "__main__":
    raise SystemExit(main())
