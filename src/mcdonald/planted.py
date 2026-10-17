"""Constant dots planted in a clip's own frames and put through its own encoder: does the encoding make a point flicker?

The bird paper's control (DOW-UAP-PR135, its Methods, "Video compression"; the bird sweep's `codec_planted_control.py`,
2026-10-14/15, which judged every object of its Table 1 by it), ported into the toolkit on 2026-10-16 (ROADMAP.md 0.3).
A clip coded with B frames between its anchors has a rhythm of its own: PR135 has a P frame every fourth frame, 30/4 =
7.49 Hz, which is where its six points beat. The codec check (`clip.gop`) can say that a beat sits at that rhythm; it
cannot say whether the encoder makes it. This can:

1. The object is measured on its track: its contrast (its peak over the local median, in its own polarity), its width
   (a Gaussian sigma off its second moment) and its speed on the screen.
2. K dots of that contrast and width, of constant brightness, are planted on a background made from a real frame of
   the clip -- median-filtered, so that the object itself is gone -- plus the clip's own frame-to-frame grain, moving
   at the object's speed (0.75 to 1.25 times it, in different directions, bouncing off a margin), on paths that keep
   clear of the overlay's blocks and of textured patches (a dot crossing a cloud's edge flickers before any encoding).
3. The frames are encoded with libx264 to the clip's own structure -- its GOP, its B frames, a fixed P/B pattern and
   its bit rate -- decoded, and every dot measured, before encoding and after, with the photometry the object was
   measured with (its aperture and ring) and the stage's spectrum.

`dots` does 1-3 once; `at_beat` reads the result at any frequency: the clean dots' largest amplitude within NEAR Hz of
the beat after encoding, the object's amplitude over that, and whether any clean dot has a line there by the continuum
null. The encoder makes the beat only where a clean dot has a line at it and the object's beat is under ABOVE times the
dots' there (`clears` is False). Where the dots carry the encoder's own line, the ratio decides: on PR097 (2026-10-16)
they have one at 7.4 Hz of 1.3 %, the encoder's anchors imprinted on a constant point, where the object beats at 15.6 %
-- twelve times; PR135's six beat at 12-26 % where the dots reach 0.6-1.7 %. Where the dots have no line at the beat,
what they reach there is the noise of their record, and the encoder makes no rhythm at that frequency, whatever the ratio:
PR085's 7.37 Hz is 2.9 times the dots' noise there, and the review that judged Table 1 accepted it for that reason (the
control's question is the encoder's rhythm; whether the object beats at all is the continuum null's and the background's). A dot is clean where, before encoding, its own
spectrum's median is under CLEAN of its brightness -- its path was clear, and the aperture alone does not make it
flicker (the pixel-phase control rides along).

Needs ffmpeg with libx264 (it has on merlin, on Homebrew's and on the Gyan builds for Windows); without it the control
says so and decides nothing. About 10-30 s for 150 frames at 1280x720. The encoder runs on one thread: libx264 on
several, with a target bit rate, is not bit-exact from one run to the next, and the reference cases' rerun check found
the control's numbers moving between two runs of the same file (2026-10-17) -- a control must give one answer.

This is the seed of the planting tool of ROADMAP.md's 0.6: synthetic objects and look-alikes written into a clip's
frames and re-encoded with its settings, through the whole chain.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy import ndimage

K = 6            # dots planted
N = 150          # frames they are planted on (5 s at 30 frames a second)
MARGIN = 40      # px: a dot bounces off a margin this far in from the frame's edge
CLEAN = 0.01     # a dot is clean where, before encoding, its spectrum's median is under this share of its brightness
NEAR = 0.5       # Hz: "at the object's beat"
ABOVE = 3.0      # the object's beat must be this many times the clean dots' largest at it


def has_x264():
    """Is there an ffmpeg with the libx264 encoder?"""
    if shutil.which("ffmpeg") is None:
        return False
    out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, encoding="utf-8", errors="replace").stdout
    return " libx264 " in out


def settings(clip):
    """The clip's encoding as libx264 is told it: {rate, gop, bframes, bit_rate}. The bit rate is the stream's, else the
    container's, else the file's size over its length."""
    from .clip import encoding, gop
    enc = encoding(str(clip.video), clip.fps) or {}
    g = enc.get("gop") or gop(clip.video, clip.fps) or {}
    gop_len = int(round(g.get("i_period") or 60))
    anchor = g.get("anchor_period") or 1
    bframes = max(0, int(round(anchor)) - 1) if g.get("b_frames") else 0
    rate = enc.get("bit_rate") or enc.get("container_bit_rate")
    info = getattr(clip, "info", None) or {}
    if not rate:
        dur = info.get("duration")
        rate = int(8 * Path(clip.video).stat().st_size / float(dur)) if dur else 4_000_000
    fps = str(info.get("fps") or clip.fps)                 # the exact rate, 30000/1001, as the clip has it
    return dict(rate=fps, gop=gop_len, bframes=bframes, bit_rate=int(rate))


def look(clip, track, dark):
    """The object's contrast (DN over the local median, in its own polarity), its Gaussian sigma (px) and its speed (px a
    frame), from about 20 frames of its track."""
    ns = sorted(n for n in track if clip.n0 <= n <= clip.n1)
    con, wid = [], []
    yy, xx = np.mgrid[-12:13, -12:13]
    for n in ns[::max(1, len(ns) // 20)]:
        g = clip.grey(n).astype(float)
        s = 255.0 - g if dark else g
        x, y = (int(round(v)) for v in track[n])
        p = s[y - 12:y + 13, x - 12:x + 13]
        if p.shape != (25, 25):
            continue
        q = np.clip(p - np.median(p), 0, None)
        con.append(float(q.max()))
        q = np.where(q > 0.3 * q.max(), q, 0)
        if q.sum() > 0:
            wid.append(float(np.sqrt(((xx ** 2 + yy ** 2) * q).sum() / q.sum() / 2)))
    xy = np.array([track[n] for n in ns], float)
    speed = float(np.median(np.hypot(*np.diff(xy, axis=0).T) / np.maximum(np.diff(ns), 1))) if len(ns) > 1 else 0.0
    return (float(np.median(con)) if con else 0.0, float(np.clip(np.median(wid) if wid else 1.5, 0.8, 4.0)), speed)


def _local_sd(img, size):
    """The standard deviation in every size x size patch, from two box filters."""
    m = ndimage.uniform_filter(img, size)
    return np.sqrt(np.maximum(ndimage.uniform_filter(img * img, size) - m * m, 0))


def _reflect(p0, v, n, length):
    lo, hi = float(MARGIN), float(length - MARGIN)
    q = (p0 + v * n - lo) % (2 * (hi - lo))
    return lo + (q if q <= hi - lo else 2 * (hi - lo) - q)


def dots(clip, track, dark=False, ap=None, k=K, n=N, seed=1, say=lambda *a: None):
    """K constant dots, like the object, planted in N frames of the clip's own background and grain, encoded like the
    clip and decoded: {look, settings, starts, velocities, before, after (each a list of K brightness curves),
    background_frame, grain} -- or {skipped: why}. `ap` is the object's aperture (`flicker.sized` or `fixed`), which the
    dots are measured in."""
    from . import flicker
    if not getattr(clip, "video", None):
        return dict(skipped="no video file to read the clip's encoding from")
    if not has_x264():
        return dict(skipped="this ffmpeg has no libx264 encoder, so the clip's encoding cannot be repeated")
    r, ring = (ap[0], ap[1]) if ap else (flicker.APERTURE, flicker.RING)
    con, sig, speed = look(clip, track, dark)
    if con <= 0:
        return dict(skipped="the object has no contrast to plant dots with")
    st = settings(clip)
    ns = sorted(m for m in track if clip.n0 <= m <= clip.n1)
    mid = ns[len(ns) // 2]
    base = clip.grey(mid).astype(np.float32)
    grain = 0.0
    for d in range(1, 6):                                    # the next frame that is a new picture: its difference is grain
        if clip.n0 <= mid + d <= clip.n1:
            grain = float(np.std(ndimage.gaussian_filter(clip.grey(mid + d).astype(np.float32) - base, 0.7)) / np.sqrt(2))
            if grain > 0.3:
                break
    grain = max(grain, 0.3)
    bg = ndimage.median_filter(base, 9)
    H, W = bg.shape
    boxes = ndimage.binary_dilation(base < 5, iterations=4)
    sd = _local_sd(bg[::4, ::4].astype(float), 8)
    sd_ok = 1.5 * float(np.median(sd))
    sp = max(speed, 0.2) * np.linspace(0.75, 1.25, k)
    starts, vel = [], []
    for t in np.linspace(0, 2 * np.pi, 48, endpoint=False):
        for c in ((0.35 * W, 0.35 * H), (0.65 * W, 0.35 * H), (0.35 * W, 0.65 * H), (0.65 * W, 0.65 * H)):
            if len(starts) == k:
                break
            v = (sp[len(starts)] * np.cos(t), sp[len(starts)] * np.sin(t))
            ok = True
            for m in range(0, n, 3):
                x, y = _reflect(c[0], v[0], m, W), _reflect(c[1], v[1], m, H)
                ix, iy = int(x), int(y)
                if boxes[max(0, iy - 15):iy + 16, max(0, ix - 15):ix + 16].any() or \
                        sd[min(iy // 4, sd.shape[0] - 1), min(ix // 4, sd.shape[1] - 1)] > sd_ok:
                    ok = False
                    break
            if ok:
                starts.append(c)
                vel.append(v)
    if not starts:
        return dict(skipped="no path across the frame keeps clear of the overlay and of textured patches")
    sign = -1.0 if dark else 1.0
    R = int(np.ceil(4 * sig)) + 2
    py, px = np.mgrid[-R:R + 1, -R:R + 1]
    rng = np.random.default_rng(seed)
    before = [[] for _ in starts]
    tmp = Path(tempfile.mkdtemp(prefix="mcdonald-planted-"))
    enc = tmp / "dots.mp4"
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}",
           "-framerate", st["rate"], "-i", "-", "-c:v", "libx264", "-threads", "1", "-profile:v", "high", "-pix_fmt", "yuv420p",
           "-g", str(st["gop"]), "-bf", str(st["bframes"]), "-b_strategy", "0", "-x264-params", "b-adapt=0:scenecut=0",
           "-b:v", str(st["bit_rate"]), "-maxrate", str(int(st["bit_rate"] * 1.1)), "-bufsize", str(st["bit_rate"] * 2), str(enc)]
    say(f"  planting {len(starts)} constant dots ({con:.0f} DN, sigma {sig:.2f} px, {speed:.2f} px a frame) and encoding them "
        f"like the clip: GOP {st['gop']}, {st['bframes']} B frames, {st['bit_rate'] / 1e6:.2f} Mb/s")
    try:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        for m in range(n):
            img = bg + rng.normal(0, grain, bg.shape).astype(np.float32)
            for j, (c, v) in enumerate(zip(starts, vel)):
                x, y = _reflect(c[0], v[0], m, W), _reflect(c[1], v[1], m, H)
                ix, iy = int(round(x)), int(round(y))
                img[iy - R:iy + R + 1, ix - R:ix + R + 1] += sign * con * np.exp(-((px - (x - ix)) ** 2 + (py - (y - iy)) ** 2) / (2 * sig * sig))
            frame = np.clip(np.round(img), 0, 255).astype(np.uint8)
            g = frame.astype(float)
            for j, (c, v) in enumerate(zip(starts, vel)):
                before[j].append(flicker.brightness(g, _reflect(c[0], v[0], m, W), _reflect(c[1], v[1], m, H), r, ring, dark))
            p.stdin.write(frame.tobytes())
        p.stdin.close()
        err = p.stderr.read().decode("utf-8", "replace")
        if p.wait() != 0:
            return dict(skipped=f"the encoder failed: {err.strip()[-300:]}")
        from .clip import every_frame
        dec = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-threads", "1", "-i", str(enc), *every_frame(), "-f", "rawvideo",
                              "-pix_fmt", "gray", "-"], capture_output=True)
        raw = np.frombuffer(dec.stdout, np.uint8)
        frames = raw[:(len(raw) // (W * H)) * W * H].reshape(-1, H, W)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    after = [[] for _ in starts]
    for m in range(min(n, len(frames))):
        g = frames[m].astype(float)
        for j, (c, v) in enumerate(zip(starts, vel)):
            after[j].append(flicker.brightness(g, _reflect(c[0], v[0], m, W), _reflect(c[1], v[1], m, H), r, ring, dark))
    return dict(look=dict(contrast=con, sigma=sig, speed=speed), settings=st, grain=grain, background_frame=int(mid),
                starts=[list(map(float, c)) for c in starts], velocities=[list(map(float, v)) for v in vel],
                aperture_px=float(r), ring_px=[float(ring[0]), float(ring[1])], before=before, after=after)


def at_beat(D, hz, amp, fps, top=None):
    """What the planted dots `D` (`dots`) say of a beat at `hz` of amplitude `amp` (a share of the brightness):
    {hz, amplitude, dots: [{clean, before_median, after_strongest_hz, after_at_beat, line}], clean, at_beat_max, ratio,
    line_at_beat, clears} -- or {skipped}. `line_at_beat`: a clean dot has a line there (its strongest within NEAR Hz of the
    beat, under the continuum null's CONTINUUM_P) -- the encoder's own rhythm. `clears`: the encoder does not make the
    beat -- no clean dot has a line at it, or the object's beat is ABOVE times or more the clean dots' largest there."""
    from . import flicker
    if D.get("skipped"):
        return dict(skipped=D["skipped"])
    top = top or flicker.TOP * fps / 2
    rows = []
    for b, a in zip(D["before"], D["after"]):
        b = [v for v in b if v is not None]
        a = [v for v in a if v is not None]
        if len(b) < flicker.MIN_FRAMES or len(a) < flicker.MIN_FRAMES or np.median(a) <= 0:
            rows.append(dict(clean=False, why="left the frame or lost its contrast"))
            continue
        rb, ra = flicker.deviation(b, fps), flicker.deviation(a, fps)
        fr, F, band, wsum, _ = flicker._spec(rb, fps)
        Ab = 2 * np.abs(F) / wsum
        med_b = float(np.median(Ab[band & (fr <= top)]))
        fr, F, band, wsum, _ = flicker._spec(ra, fps)
        Aa = 2 * np.abs(F) / wsum
        inb = band & (fr <= top)
        near = inb & (np.abs(fr - hz) <= NEAR)
        cn = flicker.continuum(ra, fps, top=top, runs=500)
        line = bool(cn["p"] is not None and cn["p"] <= flicker.CONTINUUM_P and abs(cn["hz"] - hz) <= NEAR)
        rows.append(dict(clean=bool(med_b < CLEAN), before_median=med_b, after_strongest_hz=float(fr[inb][np.argmax(Aa[inb])]),
                         after_at_beat=float(Aa[near].max()) if near.any() else 0.0, line=line))
    clean = [r for r in rows if r.get("clean")]
    if not clean:
        return dict(hz=float(hz), amplitude=float(amp), dots=rows, clean=0,
                    skipped="no planted dot came through clean (each crossed something, or its aperture made it flicker)")
    mx = max(r["after_at_beat"] for r in clean)
    ratio = float(amp / mx) if mx > 0 else float("inf")
    line = any(r["line"] for r in clean)
    return dict(hz=float(hz), amplitude=float(amp), dots=rows, clean=len(clean), at_beat_max=float(mx), ratio=ratio,
                line_at_beat=line, clears=bool(not line or ratio >= ABOVE))
