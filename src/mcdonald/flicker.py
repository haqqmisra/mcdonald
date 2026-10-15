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

Two more, from PR23 (2026-10-09: a look-down clip over a town, called "a bird" at 2.1 Hz),
neither of which the apertures beside the object can catch:

4. **The object lost against what is behind it.** It crossed a hot roof: for seven frames its
   brightness over the ring fell from about 4,800 to nothing and below, and that one dip was
   the whole beat. Where the object's brightness falls under DROP of its own level
   it is lost (`lost`): those frames are filled across before any spectrum (trimmed, at the
   ends), no window that holds one is used, and past LOST_MAX of them no beat is looked for.
5. **Its own slow change.** Taking a curve against its running mean is a filter that passes
   little under 1/DETREND_S, so a brightness that only wanders slowly comes out peaked just
   above that (2 Hz: 64% of random walks through these steps peak at 1.5-2.5 Hz). So the
   strongest beat is held against the slow wander and frame-to-frame jitter that best account
   for the curve's own spectrum (`drift`): it is a beat only where it stands further over
   them than 99 in 100 curves made of that wander and jitter, read the same way, do at their
   strongest. And a strongest that is only the band's edge, the spectrum still rising below
   LOW, is the flank of something slower and no beat (`peak`: WA9ONY-5's balloon, at 1.53 Hz).

Each curve is taken relative to its own running mean over DETREND_S (so a slow change is
not a beat: the paper's 0.5 s, 15 frames at 30 fps and 30 at 60 -- until 2026-10-09 it was 15
frames at any rate, which at 60 fps put the drift's peak at 4 Hz, on Galileo's birds),
windowed (Hann), and zero-padded 16 times; what is reported is
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
is often the stronger. The fundamental is what is reported, with its double named. The
other peak must be one of its own -- clear of the strongest's lobe, in the band, and over
the curve's drift there -- or every 2-s window with a beat under 2.5 Hz finds its "half" on
the flank of the beat itself (PR23's windows all did, and named fundamentals under 1.5 Hz).

And one from the bird sweep (2026-10-10):

6. **An aperture smaller than the thing.** A fixed 4-px aperture with its ring at 7-10 px put the ring on objects
   15-100 px across, their brightness over it came out near nothing, and trap 4 called them lost (PR056, PR086,
   PR116, PR052, PR47). The object's extent is read off its own frames (`extent`, `sizes`): a point no wider than
   APERTURE keeps APERTURE, RING and BACKGROUND exactly; a wider thing gets an aperture APERTURE_OVER times its
   extent, a ring and background apertures beyond it, and the aperture re-centred each frame on its own centroid
   (`sized`, `centred`).

And the astronomer's tests (2026-10-15, from `analysis/astronomy_methods_survey.md`, its items 1-4), each
reported beside the stage's own in `fields["astro"]`, `controls`, `false_alarm`, `injection` and `fold`:

7. **Named statistics with known nulls.** The strongest beat again by the Lomb-Scargle periodogram
   (VanderPlas 2018) over the frames that are samples -- a held picture or a frame the object was lost on is
   a missing sample, not a sample -- with Baluev's (2008) false-alarm probability and the sampling's own
   rhythms read off its spectral window (`ls_peak`); the curve's strongest held against copies of itself
   scrambled in chunks, which keep the grain and destroy every rhythm (`scrambled`; Thompson et al. 2018's
   scrambled runs); the background apertures' common mode regressed out of the object's curve (`common_mode`;
   SysRem, Tamuz et al. 2005) and the pixel phase likewise (`pixel_phase`); every background aperture put
   through the object's own tests, so that what passes is a false alarm by construction (`controls_judged`);
   beats planted in them and recovered, for completeness (`injected`; Christiansen et al. 2013); and the frames
   folded on the beat into a bright half and a dim half whose difference shows where the brightness that beats
   is (`fold`; epoch folding, and Kepler's difference image, Bryson et al. 2013). With GATE_ASTRO the first two
   decide as well as report; until the goldens have been read with them, they report.

What it cannot do: say that a beat is a wingbeat. A tumbling or rotating body beats too,
and so does a light that blinks. A beat that survives the controls is the object's own;
what makes it is the rest of the case.
"""
import csv
from functools import lru_cache

import numpy as np
from scipy import ndimage

from . import forensics as vf
from .clip import gop as read_gop
from .progress import PROCS_HELP, pooled, to_stderr
from .report import Found, emit, inputs_of, said_to_stderr

APERTURE = 4.0       # px, radius
SUPER = 8            # each pixel's share of the aperture, from SUPER x SUPER points in it
RING = (7.0, 10.0)   # px, the background ring
SMOOTH = 5           # frames the track is smoothed over, so the aperture does not chase centroid noise
DETREND_S = 0.5      # s of running mean each curve is taken against (`trend_frames`)
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
LOBE = 2.0           # resolutions either side of a peak that are its own lobe (Hann): another peak is further away than that
DROP = 0.25          # the object is lost against what is behind it where its brightness over the ring is under this share of its
                     # own level (`lost`; PR23's roof: 4,800 to -1,054..345 -- a 25 % beat dips to 0.75, a 60 % one to 0.4)
LOST_MAX = 0.1       # lost on more than this share of its frames, and no beat is looked for
RUNS = 1000          # the curves that only wander and jitter which the strongest beat is held against ...
BEYOND = 0.99        # ... and the share of them it must stand further over their mean than they do, each at its own strongest
TOP = 0.8            # a beat is heard only up to this share of the Nyquist frequency -- of the frame rate, or of the
                     # picture rate where pictures are held (PR27, 2026-10-11: six windows "beat" at 13.5 Hz on frame-to-frame
                     # noise, 0.9 of the 15-Hz Nyquist; PR34: a clip of 10 pictures a second shown at 30 fps "beat" at 5.02 Hz,
                     # its hold cadence's half, and at 10.03, the cadence itself)
HELD = 0.2           # a frame is a held picture where it differs from the one before by under this share of the typical
                     # change between pictures -- the 80th percentile of the changes, not their median, as a held picture's
                     # difference is the encoder's noise (0.01-0.05 grey levels on PR34) and can be most of them
HELD_MIN = 0.1       # under this share of frames held, the pictures are taken to change on every frame
THUMB = 4            # frames are compared on THUMB x THUMB block means (`_apertures`)
ALSO = 6.0           # a half or a double stands this many times over the drift fitted without it, where it is, to be a peak
CLIP = 10.0          # a frequency standing this many times over the drift fitted to a spectrum is a peak's, and is left out of the fit
# The aperture follows the object's size (the bird sweep, 2026-10-10): a fixed 4-px aperture with its ring at 7-10 px
# put the ring ON an object 15-100 px across (PR056, PR086, PR116, PR052, PR47), its brightness over the ring came out
# near nothing, and the stage called a thing anyone could see "lost". The object's extent is read off its own frames
# (`extent`); a point no wider than APERTURE keeps APERTURE, RING and BACKGROUND exactly; a wider thing gets an
# aperture APERTURE_OVER times its extent, a ring beyond it, background apertures beyond that, and the aperture
# re-centred each frame on the thing's own centroid (a wide thing's centroid is steady; a point's is not, which is
# why a point keeps the smoothed track: trap 1).
EXTENT_FRAMES = 20   # frames the extent is read on, spread over the track
EXTENT_DROP = 0.1    # the extent: where the object's radial profile falls to this share of its centre's height
EXTENT_SIGMA = 3.0   # the centre must stand this far over the far ring's own scatter to have an extent
EXTENT_MAX = 80.0    # px: no extent is read past this
APERTURE_OVER = 1.2  # a wider thing's aperture, as a multiple of its extent
# The astronomer's tests (2026-10-15; item 7 above). Each is reported beside the stage's own; GATE_ASTRO makes the
# first two decide as well (off until the goldens have been read with them on: no number changes silently).
GATE_ASTRO = False
FAP_MAX = 0.01       # a Lomb-Scargle peak is a beat only with a false-alarm probability (Baluev 2008) under this ...
P_MAX = 0.01         # ... and only where under this share of the curve's own chunk-scrambled copies stand as high
SCRAMBLE_S = 0.25    # s: the chunks a curve is scrambled in; the scramble says nothing of frequencies under 1/SCRAMBLE_S
SCRAMBLES = 200      # scrambled copies
COMMON_K = 2         # components of the background apertures' common mode the object's curve is held against
INJECT_AMPL = (0.02, 0.05, 0.1, 0.2)   # beats planted in the background apertures, as shares of the object's brightness ...
INJECT_N = 4         # ... at this many frequencies spread over the band ...
INJECT_MAX = 300     # ... on at most this many frames of each (the middle of its stretch)
STAMP = 16           # px: the half-size of the stamp of the object kept from every frame, for the fold
FOLD_BINS = 8        # the beat's cycle is folded into this many bins
WINDOW_LINE = 0.1    # a rhythm of the sampling (a line of its spectral window) is reported where it stands this high (nought's is 1)


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


def extent(g, x, y, dark=False):
    """The object's radius (px) about (x, y) in grey frame g, off its radial profile: the median contrast on each
    1-px ring about it (a median, so roofs or wave crests on part of a ring do not count -- PR23, PR056), and the
    first radius where that falls to EXTENT_DROP of the centre's height over the far background. For a Gaussian blob
    that is about the radius holding 90 % of its light. None where the stamp leaves the frame or nothing stands out."""
    H, W = g.shape
    S = int(EXTENT_MAX) + 25
    ix, iy = int(round(x)), int(round(y))
    if ix - S < 0 or iy - S < 0 or ix + S + 1 > W or iy + S + 1 > H:
        return None
    s = g[iy - S:iy + S + 1, ix - S:ix + S + 1].astype(float)
    yy, xx = np.mgrid[-S:S + 1, -S:S + 1]
    rr = np.hypot(xx + ix - x, yy + iy - y)
    q = -s if dark else s
    ring = np.floor(rr).astype(int)
    prof = np.array([np.median(q[ring == k]) for k in range(int(EXTENT_MAX) + 21)])
    far = float(np.median(prof[int(EXTENT_MAX):]))
    top = float(prof[:3].max()) - far
    ann = q[(rr >= EXTENT_MAX) & (rr <= EXTENT_MAX + 20)]
    if top <= EXTENT_SIGMA * 1.4826 * float(np.median(np.abs(ann - np.median(ann)))):
        return None                                          # nothing stands out of the far ring's own scatter
    below = np.flatnonzero(prof[:int(EXTENT_MAX) + 1] - far < EXTENT_DROP * top)
    return float(below[0]) if len(below) else EXTENT_MAX


def sized(r):
    """(aperture radius, ring, background offset, re-centred?) for an object whose contrast lies within r px:
    APERTURE, RING and BACKGROUND's 25 px for a point no wider than APERTURE, larger for a wider thing."""
    if r is None or r <= APERTURE:
        return APERTURE, RING, 25, False
    R = APERTURE_OVER * r
    ring = (R + 3.0, R + 6.0 + 0.25 * R)
    return R, ring, int(np.ceil(2 * ring[1] + 5)), True


def centred(g, x, y, r, ring, dark=False):
    """The object's own centroid near (x, y): contrast over the ring's median within r, weighted (twice)."""
    H, W = g.shape
    R = int(np.ceil(ring[1])) + 1
    for _ in range(2):
        ix, iy = int(round(x)), int(round(y))
        if ix - R < 0 or iy - R < 0 or ix + R + 1 > W or iy + R + 1 > H:
            break
        s = g[iy - R:iy + R + 1, ix - R:ix + R + 1].astype(float)
        yy, xx = np.mgrid[iy - R:iy + R + 1, ix - R:ix + R + 1].astype(float)
        rr = np.hypot(xx - x, yy - y)
        b = float(np.median(s[(rr >= ring[0]) & (rr <= ring[1])]))
        w = np.clip((b - s) if dark else (s - b), 0, None) * (rr <= r)
        if w.sum() <= 0:
            break
        x, y = float((w * xx).sum() / w.sum()), float((w * yy).sum() / w.sum())
    return x, y


def smoothed(track, ns):
    """The track at every frame of `ns`, filled in where it has gaps and smoothed over SMOOTH frames."""
    have = sorted(track)
    x = np.interp(ns, have, [track[n][0] for n in have])
    y = np.interp(ns, have, [track[n][1] for n in have])
    return ndimage.uniform_filter1d(x, SMOOTH, mode="nearest"), ndimage.uniform_filter1d(y, SMOOTH, mode="nearest")


def trend_frames(fps):
    """The running mean's length in frames: DETREND_S at this frame rate."""
    return max(3, int(DETREND_S * fps + 0.5))


def deviation(f, fps, scale=None):
    """A curve taken against its own running mean over DETREND_S, as a share of that mean -- or of `scale`, for a
    background aperture, whose own mean is near nothing: it is measured in the object's brightness -- about nought.
    Every spectrum here is of this."""
    f = np.asarray(f, float)
    trend = ndimage.uniform_filter1d(f, trend_frames(fps), mode="nearest")
    r = (f - trend) / (scale if scale else trend)
    return r - r.mean()


def _spec(r, fps):
    """(frequencies, complex spectrum, the band's mask, Hann weights' sum, rms) of a deviation curve."""
    r = np.asarray(r, float)
    w = np.hanning(len(r))
    F = np.fft.rfft(r * w, PAD * len(r))
    fr = np.fft.rfftfreq(PAD * len(r), 1 / fps)
    band = (fr >= LOW) & (fr <= 0.95 * fps / 2)
    return fr, F, band, float(w.sum()), float(r.std())


def spectrum(f, fps, scale=None):
    """(frequencies, complex spectrum, the band's mask, Hann weights' sum, rms) of a curve taken
    against its own running mean, as a share of that mean -- or of `scale`, for a background
    aperture, whose own mean is near nothing: it is measured in the object's brightness."""
    return _spec(deviation(f, fps, scale), fps)


def peak(f, fps, lines=(), scale=None):
    """The strongest beat of a curve: frequency, amplitude (a share of the brightness), how it
    stands over the median of the band, its half-power width, whether it is within the
    resolution of one of the codec's `lines`, and whether it is only the band's `edge`: the
    strongest within its lobe of the band's first (or last) frequency, with more beyond it -- the
    flank, or a side lobe, of something slower than LOW Hz: a balloon's payload swinging (WA9ONY-5,
    1.53 Hz), a sea's swell under the object (PR144) -- and no peak at all."""
    return _peak(deviation(f, fps, scale), fps, lines)


def _peak(r, fps, lines=()):
    """`peak`, of a deviation curve."""
    fr, F, band, wsum, rms = _spec(r, fps)
    P = np.abs(F) ** 2
    k = int(np.argmax(np.where(band, P, -1)))
    res = fps / len(r)
    half = fr[band][P[band] >= P[k] / 2]
    near = [L for L in lines if abs(fr[k] - L) <= res]
    below, above = (fr > 0) & (fr < LOW), fr > 0.95 * fps / 2
    edge = ((fr[k] - LOW <= LOBE * res and below.any() and P[below].max() >= P[k])
            or (0.95 * fps / 2 - fr[k] <= LOBE * res and above.any() and P[above].max() >= P[k]))
    return dict(hz=float(fr[k]), amplitude=float(2 * np.sqrt(P[k]) / wsum), stands=float(P[k] / np.median(P[band])),
                half_power_hz=[float(half.min()), float(half.max())], resolution_hz=float(res), rms=rms,
                at_the_codec_line_hz=near[0] if near else None, edge=bool(edge))


def lost(f, fps):
    """Where the object is lost against what is behind it -- its brightness over the ring under DROP
    of its own level, or nothing or less: a mask over the curve f. Its level is the running upper
    quartile over WINDOW_S, which a gap of up to three quarters of that does not pull down (a running
    median over a second is pulled down by any gap over half a second, and finds none of it)."""
    f = np.asarray(f, float)
    level = ndimage.percentile_filter(f, 75, size=max(3, int(round(WINDOW_S * fps)) | 1), mode="nearest")
    return (f <= 0) | (f < DROP * level)


def filled(f, mask):
    """The curve f with the frames under `mask` filled across from those either side."""
    f = np.asarray(f, float).copy()
    k = np.arange(len(f))
    if mask.any() and (~mask).sum() >= 2:
        f[mask] = np.interp(k[mask], k[~mask], f[~mask])
    return f


def _steps(X, fps):
    """The spectra (complex, padded) of the rows of X -- curves as a share of their level, about 0 -- through
    the steps a curve is taken through (`spectrum`), with the running mean subtracted rather than divided by:
    the same, for a curve that changes by a small share of itself."""
    R = X - ndimage.uniform_filter1d(X, trend_frames(fps), axis=-1, mode="nearest")
    R = R - R.mean(axis=-1, keepdims=True)
    return np.fft.rfft(R * np.hanning(X.shape[-1]), PAD * X.shape[-1], axis=-1)


def _batches(n, runs):
    m = max(1, min(200, int(4e6 // (PAD * n))))            # a long track's padded spectra are big: so many at a time
    return [min(m, runs - i) for i in range(0, runs, m)]


@lru_cache(maxsize=16)
def _units(n, fps):
    """The mean spectra, through those steps, of n frames of a random walk of unit step and of unit white
    grain: what a curve that only wanders, and one that only jitters, give at each frequency."""
    rng, rw, w = np.random.default_rng(1), 0.0, 0.0
    for m in _batches(n, RUNS):
        rw = rw + (np.abs(_steps(np.cumsum(rng.normal(0, 1, (m, n)), axis=1), fps)) ** 2).sum(axis=0)
        w = w + (np.abs(_steps(rng.normal(0, 1, (m, n)), fps)) ** 2).sum(axis=0)
    return rw / RUNS, w / RUNS


def _fit(P, rw, w, nat, rounds=3, iters=12):
    """(a, b) for each row of P: the wander's and the jitter's variance a frame whose spectrum a rw + b w
    is most likely to have given the row's (Whittle's likelihood, by reweighted least squares), at the
    frequencies `nat`, less those that stand CLIP times over the fit -- a peak's, which are not drift."""
    P = P[:, nat]
    X1, X2 = rw[nat][None, :], w[nat][None, :]
    keep = np.ones(P.shape, bool)
    for r in range(rounds + 1):
        E = np.broadcast_to(np.where(keep, P, 0).sum(1, keepdims=True) / np.maximum(keep.sum(1, keepdims=True), 1), P.shape)
        for _ in range(iters):
            W = keep / np.maximum(E, 1e-300) ** 2
            S11, S12, S22 = (W * X1 * X1).sum(1), (W * X1 * X2).sum(1), (W * X2 * X2).sum(1)
            T1, T2 = (W * X1 * P).sum(1), (W * X2 * P).sum(1)
            det = S11 * S22 - S12 ** 2
            a = (S22 * T1 - S12 * T2) / np.where(det > 0, det, np.inf)
            b = (S11 * T2 - S12 * T1) / np.where(det > 0, det, np.inf)
            a, b = (np.where(b < 0, T1 / np.maximum(S11, 1e-300), np.maximum(a, 0)),
                    np.where(a < 0, T2 / np.maximum(S22, 1e-300), np.maximum(b, 0)))
            a, b = np.maximum(a, 0), np.maximum(b, 0)
            E = np.maximum(a[:, None] * X1 + b[:, None] * X2, 1e-300)
        if r < rounds:
            keep = P <= CLIP * E
    return a, b


def drift(f, fps, runs=RUNS, scale=None):
    """The strongest beat of a curve against its own slow change: {over: how far it stands over E, the
    spectrum of the wander and jitter that best account for the curve's (`_fit`), where it is; needed: how
    far BEYOND of `runs` curves made of that wander and jitter stand over theirs, read the same way, each at
    its own strongest; passes; wander, jitter: as shares of the brightness a frame}.

    Fitted to the spectrum rather than read off the curve's frame-to-frame steps, because a beat is in
    those steps too: flyer 5's beat, read as wander, hid its own half. And each of the curves made is read
    as this one was, its own wander and jitter fitted, so that how well 2 s of a curve tell drift from a beat
    is in the answer: read off the steps, or fitted with the strongest left out, 4-10 in 100 curves that only
    wandered passed for one in a hundred. The curves are made the same way every time (one seed), so a curve
    gives one answer. `scale`, as `spectrum`'s: a background aperture is measured in the object's brightness."""
    f = np.asarray(f, float)
    n = len(f)
    fr, F, band, _, _ = spectrum(f, fps, scale)
    P = np.abs(F) ** 2
    rw, w = _units(n, fps)
    nat = np.arange(PAD, int(np.flatnonzero(band)[-1]) + 1, PAD)             # every frequency the curve resolves, past nought
    k = int(np.argmax(np.where(band, P, -1)))
    a, b = (float(v[0]) for v in _fit(P[None, :], rw, w, nat))
    rng, z = np.random.default_rng(0), []
    for m in _batches(n, runs):
        Q = np.abs(np.sqrt(a) * _steps(np.cumsum(rng.normal(0, 1, (m, n)), axis=1), fps)
                   + np.sqrt(b) * _steps(rng.normal(0, 1, (m, n)), fps)) ** 2
        j = np.argmax(np.where(band, Q, -1), axis=1)
        aq, bq = _fit(Q, rw, w, nat)
        z.append(Q[np.arange(m), j] / np.maximum(aq * rw[j] + bq * w[j], np.finfo(float).tiny))
    needed = float(np.quantile(np.concatenate(z), BEYOND))
    over = float(P[k] / max(a * rw[k] + b * w[k], np.finfo(float).tiny))
    return dict(over=over, needed=needed, passes=bool(over >= needed), wander=float(np.sqrt(a)), jitter=float(np.sqrt(b)))


def harmonics(f, fps, scale=None, drift_too=False):
    """The strongest beat of a curve as a fundamental and its double: (fundamental Hz, double Hz or
    None, the share of the strongest that a peak at half its frequency has, the share at double).
    With a peak at half at least HALF of the strongest, the strongest is the double and the
    fundamental the half; else the strongest is the fundamental, and a double is named where a
    peak at twice it has at least HALF of it. Either is a peak of its own: a local maximum in the
    band, further from the strongest than its lobe, and -- with `drift_too` -- standing ALSO times
    over the curve's drift there, fitted (`_fit`) to the rest of the spectrum: the frequencies asked
    about are left out of the fit, or a real half props up the drift it is held against (flyer 5's
    3.9 Hz, 4 times over a fit it was in and 30 over one it was not)."""
    fr, F, band, wsum, _ = spectrum(f, fps, scale)
    P = np.abs(F) ** 2
    k = int(np.argmax(np.where(band, P, -1)))
    n = len(f)
    res = fps / n
    top = np.r_[False, (P[1:-1] >= P[:-2]) & (P[1:-1] >= P[2:]), False]
    if drift_too:
        rw, w = _units(n, fps)
        nat = np.arange(PAD, int(np.flatnonzero(band)[-1]) + 1, PAD)

    def share(hz):
        m = band & top & (np.abs(fr - hz) <= 1.5 * res) & (np.abs(fr - fr[k]) > LOBE * res)
        if m.any() and drift_too:
            a, b = (float(v[0]) for v in _fit(P[None, :], rw, w, nat[np.abs(fr[nat] - hz) > LOBE * res]))
            m &= P >= ALSO * (a * rw + b * w)
        return float(np.sqrt(P[m].max() / P[k])) if m.any() and P[k] > 0 else 0.0
    half, double = share(fr[k] / 2), share(fr[k] * 2)
    if half >= HALF:
        return float(fr[k] / 2), float(fr[k]), half, double
    return float(fr[k]), (float(fr[k] * 2) if double >= HALF else None), half, double


def windows(raw, name, bgs, ns, fps, lines, gone=(), top=None, scale=None):
    """The object's beat in windows of WINDOW_S along the track, each held to the tests the whole
    track is: [{first, last, hz, amplitude, stands, resolution_hz, floor, shared, at_the_codec_line_hz,
    over_drift, drift_needed, edge, fundamental_hz, double_hz, passes}]. Windows where an aperture leaves the
    frame, or that hold a frame where the object was lost (`gone`: indices into the curves), are left out. A window
    passes only below `top` Hz (`pictures`; TOP of the frame rate's Nyquist frequency if not given). With `scale`,
    the curve is a background aperture's, measured in the object's brightness (`controls_judged`)."""
    top = TOP * fps / 2 if top is None else top
    n = len(ns)
    W = max(MIN_FRAMES, int(round(WINDOW_S * fps)))
    step = max(1, W // 8)
    starts = list(range(0, n - W + 1, step))
    if starts and starts[-1] != n - W:
        starts.append(n - W)                                   # the last window too: the flapping may be at the track's end
    out = []
    for s in starts:
        f = raw[name][s:s + W]
        if any(v is None for v in f) or (scale is None and np.median(f) <= 0) or any(s <= k < s + W for k in gone):
            continue
        sc = scale if scale else float(np.median(f))
        p = peak(f, fps, lines, scale)
        floors, shared = [], False
        for b in bgs:
            g = raw[b][s:s + W]
            if any(v is None for v in g):
                continue
            floors.append(peak(g, fps, (), sc)["amplitude"])
            fr, F, _, wsum, _ = spectrum(g, fps, sc)
            if 2 * np.abs(F[int(np.argmin(np.abs(fr - p["hz"])))]) / wsum >= SHARED * p["amplitude"]:
                shared = True
        if not floors:
            continue
        floor = float(np.median(floors))
        d = drift(f, fps, scale=scale)
        fund, dbl, _, _ = harmonics(f, fps, scale, drift_too=True)
        out.append(dict(first=int(ns[s]), last=int(ns[s + W - 1]), hz=p["hz"], amplitude=p["amplitude"], stands=p["stands"],
                        resolution_hz=p["resolution_hz"], floor=floor, shared=shared, at_the_codec_line_hz=p["at_the_codec_line_hz"],
                        over_drift=d["over"], drift_needed=d["needed"], edge=p["edge"], fundamental_hz=fund, double_hz=dbl,
                        above_top=bool(p["hz"] > top),
                        passes=bool(p["amplitude"] >= ABOVE * floor and not shared and p["at_the_codec_line_hz"] is None
                                    and d["passes"] and not p["edge"] and p["hz"] <= top)))
    return out


_G = {}


def _init(clip, pos, dark, ap=None, thumbs=False, stamps=False):
    _G.update(clip=clip, pos=pos, dark=dark, ap=ap or {}, thumbs=thumbs, stamps=stamps)


def stamp(g, x, y, dark=False, half=STAMP):
    """The frame about (x, y), 2 * half + 1 px square, shifted (bilinear) so that (x, y) is its centre pixel exactly;
    None where it leaves the frame. A dark thing is turned up, so every stamp's contrast is the thing's own. Kept from
    every frame for the fold (`fold`)."""
    H, W = g.shape
    ix, iy = int(np.floor(x)), int(np.floor(y))
    R = half + 2
    if ix - R < 0 or iy - R < 0 or ix + R + 1 > W or iy + R + 1 > H:
        return None
    s = g[iy - R:iy + R + 1, ix - R:ix + R + 1].astype(np.float32)
    s = ndimage.shift(s, (iy - y, ix - x), order=1, mode="nearest")[2:-2, 2:-2]
    return -s if dark else s


def _apertures(job):
    """Frame n's brightness in every aperture, k being its place in the frames the positions are of. An aperture
    sized for a wider thing (`sized`) is re-centred on the thing's own centroid first."""
    k, n = job
    g = vf.grey_of(_G["clip"].rgb(n))
    out, cut = [], {}
    for name, (x, y) in _G["pos"].items():
        dark = _G["dark"] and not name.startswith("background")
        r, ring, _, recentre = _G["ap"].get(name, (APERTURE, RING, 25, False))
        cx, cy = centred(g, x[k], y[k], r, ring, dark) if recentre else (x[k], y[k])
        out.append(brightness(g, cx, cy, r=r, ring=ring, dark=dark))
        if _G.get("stamps") and not name.startswith("background"):
            cut[name] = stamp(g, cx, cy, dark)
    if _G.get("thumbs"):                                     # the picture, small, for `pictures`: is it a new one?
        H, W = (g.shape[0] // THUMB) * THUMB, (g.shape[1] // THUMB) * THUMB
        t = g[:H, :W].reshape(H // THUMB, THUMB, W // THUMB, THUMB).mean((1, 3))
        out.append(np.clip(np.round(t), 0, 255).astype(np.uint8))
    if _G.get("stamps"):                                     # the object on this frame, for the fold
        out.append(cut)
    return out


def sizes(clip, tracks, ns, dark=False):
    """{name: (extent px or None, sized(extent))}: each track's extent, the median over EXTENT_FRAMES frames spread
    over its span (`extent`), and the aperture that follows from it."""
    out = {}
    for name, t in tracks.items():
        x, y = smoothed(t, ns)
        have = [k for k, n in enumerate(ns) if min(t) <= n <= max(t)]
        pick = [have[int(i)] for i in np.linspace(0, len(have) - 1, min(EXTENT_FRAMES, len(have)))] if have else []
        rs = [extent(vf.grey_of(clip.rgb(ns[k])), x[k], y[k], dark) for k in pick]
        rs = [r for r in rs if r is not None]
        r = float(np.median(rs)) if rs else None
        out[name] = (r, sized(r))
    return out


def curves(clip, tracks, ns, dark=False, progress=None, stop=None, about=None, procs=None, ap=None, thumbs=None, stamps=None):
    """{name: brightness on each frame of ns} for each track, and for background apertures about
    the track `about` (the first, if not named) -- None where the aperture leaves the frame or a
    mask covers it. `ap` is {track: sized(...)} (`sizes`); without it every aperture is APERTURE, its
    ring RING and the background apertures BACKGROUND, as before. The frames are read on `procs`
    processes (`progress.pooled`; 0: in this one). With a list as `thumbs`, each frame's picture, small, is put in it
    as well (`pictures`), from the same reading of the frame; with a dict as `stamps`, each track's stamp of the object
    on each frame (`stamp`), {name: [stamp or None per frame of ns]}, for the fold."""
    ap = dict(ap or {})
    pos = {name: smoothed(t, ns) for name, t in tracks.items()}
    about = about if about in pos else next(iter(pos))
    first = pos[about]
    r, ring, off, _ = ap.get(about, (APERTURE, RING, 25, False))
    for dx, dy in BACKGROUND:
        name = f"background {dx:+d},{dy:+d}"           # named by the default offsets whatever the size, so the CSV keeps its columns
        pos[name] = (first[0] + dx * off / 25, first[1] + dy * off / 25)
        ap[name] = (r, ring, off, False)
    out = {name: [] for name in pos}
    for got in pooled(procs, _apertures, list(enumerate(ns)), _init, (clip, pos, dark, ap, thumbs is not None, stamps is not None),
                      8, progress, stop, "Flicker", pixels=clip.W * clip.H):
        for name, v in zip(pos, got[:len(pos)]):
            out[name].append(v)
        extra = list(got[len(pos):])
        if thumbs is not None:
            thumbs.append(extra.pop(0))
        if stamps is not None:
            cut = extra.pop(0)
            for name in tracks:
                stamps.setdefault(name, []).append(cut.get(name))
    return out


def pictures(thumbs, fps):
    """How many new pictures a second the frames carry: {rate, held (share of frames), top_hz}. A held frame repeats the
    picture before it (HELD of the typical change between pictures); `top_hz` is the highest frequency a beat is
    heard at, TOP of the Nyquist frequency of the frame rate or, where pictures are held, of the picture rate; `held_k`,
    which frames (their places in the frames read) repeat the one before -- missing samples to the Lomb-Scargle
    periodogram (`ls_peak`), however few."""
    d = np.array([np.mean(np.abs(a.astype(np.int16) - b.astype(np.int16))) for a, b in zip(thumbs[:-1], thumbs[1:])])
    if len(d) < 2:
        return dict(rate=fps, held=0.0, top_hz=TOP * fps / 2, held_k=[])
    typical = float(np.percentile(d, 80))                    # a change between pictures while under 80% of frames are held
    held_k = [int(i) + 1 for i in np.flatnonzero(d < HELD * typical)] if typical > 0 else []
    held = float(np.mean(d < HELD * typical)) if typical > 0 else 0.0
    rate = fps * (1 - held) if held >= HELD_MIN else fps
    return dict(rate=float(rate), held=held, top_hz=float(TOP * rate / 2), held_k=held_k)


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


# ---- the astronomer's tests (item 7; 2026-10-15) -------------------------------------------------------------
def lombscargle(t, y, freqs):
    """The generalised (floating-mean) Lomb-Scargle periodogram of y sampled at t, at `freqs` (Hz): the share of
    y's variance a sinusoid at each frequency, with its own mean, accounts for -- the "standard" normalisation, 0 to 1
    (Zechmeister & Kuerster 2009; VanderPlas 2018, sec. 6). Built for samples that are not evenly spaced: a frame left
    out is a missing sample, not a sample. Every sample weighs alike."""
    t, y, freqs = np.asarray(t, float), np.asarray(y, float), np.asarray(freqs, float)
    n = len(t)
    out = np.zeros(len(freqs))
    if n < 4:
        return out
    y = y - y.mean()
    yy = float((y * y).sum()) / n
    if yy <= 0:
        return out
    step = max(1, int(2e6 // n))                            # so many frequencies at a time: the cos/sin matrix is step x n
    for a in range(0, len(freqs), step):
        ph = 2 * np.pi * freqs[a:a + step, None] * t[None, :]
        c, s = np.cos(ph), np.sin(ph)
        C, S = c.mean(1), s.mean(1)
        YC, YS = (c * y).mean(1), (s * y).mean(1)
        CC, SS, CS = (c * c).mean(1) - C * C, (s * s).mean(1) - S * S, (c * s).mean(1) - C * S
        D = CC * SS - CS * CS
        ok = D > 1e-9 * np.maximum(CC * SS, np.finfo(float).tiny)
        num = SS * YC ** 2 + CC * YS ** 2 - 2 * CS * YC * YS
        out[a:a + step] = np.where(ok, num / (yy * np.where(ok, D, 1.0)), 0.0)
    return np.clip(out, 0.0, 1.0)


def window(t, freqs):
    """The spectral window of the sampling t: |sum exp(2 pi i f t)|^2 / N^2 -- 1 at nought and at every rhythm of
    the sampling (every third frame kept: 1 at fps/3), small between. A peak of the periodogram at one of its lines is
    the sampling's, as a beat at the codec's line is the codec's."""
    t, freqs = np.asarray(t, float), np.asarray(freqs, float)
    n = len(t)
    out = np.zeros(len(freqs))
    if n == 0:
        return out
    step = max(1, int(2e6 // n))
    for a in range(0, len(freqs), step):
        ph = 2 * np.pi * freqs[a:a + step, None] * t[None, :]
        out[a:a + step] = (np.cos(ph).sum(1) ** 2 + np.sin(ph).sum(1) ** 2) / n ** 2
    return out


def fap_baluev(z, t, fmin, fmax):
    """The false-alarm probability of the strongest Lomb-Scargle peak, of power z (standard normalisation), found between
    fmin and fmax Hz on samples at t: how often noise alone makes one as high somewhere in that band. Baluev 2008's
    alias-free bound (his eq. 6; VanderPlas 2018 sec. 7.4.2), as astropy computes it, with the band's width where
    astropy takes the whole range from nought."""
    from scipy.special import gammaln
    t = np.asarray(t, float)
    N = len(t)
    if N < 5 or z <= 0 or fmax <= fmin:
        return 1.0
    NH, NK = N - 1, N - 3
    W = (fmax - fmin) * np.sqrt(4 * np.pi * np.var(t))
    z = min(float(z), 1 - 1e-12)
    gam = np.sqrt(2 / NH) * np.exp(gammaln(NH / 2) - gammaln((NH - 1) / 2))
    tau = gam * W * (1 - z) ** (0.5 * (NK - 1)) * np.sqrt(0.5 * NH * z)
    cdf = 1 - (1 - z) ** (0.5 * NK)
    return float(np.clip(1 - cdf * np.exp(-tau), 0.0, 1.0))


def ls_peak(r, fps, keep=None, top=None):
    """The strongest beat of a deviation curve by the Lomb-Scargle periodogram over the frames `keep` (a held picture,
    or a frame the object was lost on, is a missing sample, not a sample), between LOW and `top` Hz: {hz, power, fap,
    kept, dropped, resolution_hz, window_lines_hz, window_at_peak, at_a_window_line}. The sampling's own rhythms are
    read off its spectral window (`window`) up to the frame rate's Nyquist frequency, above WINDOW_LINE; a peak within
    the resolution of one is an alias of the sampling. On every frame of an even cadence there are none, and the peak
    sits where the Hann-windowed spectrum's does; the probability is what the spectrum alone cannot give."""
    r = np.asarray(r, float)
    n = len(r)
    keep = np.ones(n, bool) if keep is None else np.asarray(keep, bool)
    t = np.arange(n) / fps
    tk, yk = t[keep], r[keep]
    fmax = min(0.95 * fps / 2, top) if top else 0.95 * fps / 2
    df = fps / (PAD * n)
    nothing = dict(hz=None, power=None, fap=None, kept=int(len(tk)), dropped=int(n - len(tk)), resolution_hz=None,
                   window_lines_hz=[], window_at_peak=None, at_a_window_line=None)
    if len(tk) < 8 or fmax <= LOW + 2 * df:
        return nothing
    freqs = np.arange(LOW, fmax, df)
    P = lombscargle(tk, yk, freqs)
    k = int(np.argmax(P))
    span = float(tk[-1] - tk[0])
    res = 1 / span if span > 0 else fps / n
    wf = np.arange(df, 0.95 * fps / 2, df)
    Wn = window(tk, wf)
    tops = np.r_[False, (Wn[1:-1] >= Wn[:-2]) & (Wn[1:-1] > Wn[2:]), False] & (Wn >= WINDOW_LINE) & (wf > 2 * res)
    lines = [float(v) for v in wf[tops]]
    return dict(hz=float(freqs[k]), power=float(P[k]), fap=fap_baluev(P[k], tk, LOW, fmax), kept=int(len(tk)),
                dropped=int(n - len(tk)), resolution_hz=float(res), window_lines_hz=lines,
                window_at_peak=float(window(tk, [freqs[k]])[0]),
                at_a_window_line=bool(any(abs(freqs[k] - L) <= res for L in lines)))


def scrambled(r, fps, top=None, runs=SCRAMBLES, chunk_s=SCRAMBLE_S, seed=0):
    """The curve's strongest beat held against copies of itself scrambled in chunks of `chunk_s` (surrogate data,
    Theiler et al. 1992, in the form Kepler's vetting used, Thompson et al. 2018): a chunk keeps the grain, the codec's
    quantisation and the jitter from one frame to the next, and the chunks' order destroys every rhythm slower than a
    chunk. So the share of copies whose strongest stands as high over the band as the curve's does (`stands`, as
    `peak` reads it) is the chance of a peak that high from the grain alone: {p, stands, needed (the 99th centile of
    theirs), runs, chunk_s, valid_above_hz}. It says nothing of frequencies under 1/chunk_s, where the scrambling also
    destroys the slow wander the drift test is for. The same copies every time (one seed)."""
    r = np.asarray(r, float)
    n = len(r)
    L = max(2, int(round(chunk_s * fps)))
    fr, F, band, _, _ = _spec(r, fps)
    if top:
        band = band & (fr <= top)
    if band.sum() < 2:
        return dict(p=None, stands=None, needed=None, runs=0, chunk_s=L / fps, valid_above_hz=fps / L)
    P = np.abs(F) ** 2
    obs = float(P[band].max() / np.median(P[band]))
    chunks = [np.arange(a, min(a + L, n)) for a in range(0, n, L)]
    rng, w, z = np.random.default_rng(seed), np.hanning(n), []
    for m in _batches(n, runs):
        X = np.stack([r[np.concatenate([chunks[j] for j in rng.permutation(len(chunks))])] for _ in range(m)])
        Q = np.abs(np.fft.rfft(X * w, PAD * n, axis=-1)[:, band]) ** 2
        z.append(Q.max(1) / np.maximum(np.median(Q, axis=1), np.finfo(float).tiny))
    z = np.concatenate(z)
    return dict(p=float((np.sum(z >= obs) + 1) / (len(z) + 1)), stands=obs, needed=float(np.quantile(z, 0.99)),
                runs=int(len(z)), chunk_s=L / fps, valid_above_hz=fps / L)


def common_mode(r, R, k=COMMON_K, scene=None):
    """The object's deviation curve r less what the whole frame does: the scene's level and contrast (`scene`: rows
    over the same frames, each a deviation curve -- the mean and the spread of the frame, small, from `thumbs`), and
    what the background apertures' curves R (rows) share -- their common mode, the first k components of the
    standardised rows (SysRem, Tamuz et al. 2005, and TFA, Kovacs et al. 2005, with every aperture weighted alike,
    which is a principal-component fit) -- regressed out of r with a constant. The gain a camera changes, or a
    display's brightness as a phone films it, scales the whole frame: its contrast follows the gain exactly, where an
    aperture's contrast over its ring follows it by whatever that contrast happens to be, in either sign, as the aperture
    crosses the scene -- which is why the scene's own curves come first. A beat the background does not have loses
    about (k + 2)/n of its variance to chance alignment and no more. Returns (the residual, {components, r2: the share
    of r's variance all of it accounts for, r2_scene: the scene's level and contrast alone, share_of_controls: the share
    of the apertures' variance the components hold, mode: the first component, over the frames})."""
    r, R = np.asarray(r, float), np.asarray(R, float)
    n = len(r)
    k = int(max(0, min(k, R.shape[0] if R.ndim == 2 else 0, n // 10)))
    S = np.asarray(scene, float) if scene is not None and len(scene) else np.zeros((0, n))
    if (k == 0 and not len(S)) or (k and R.shape[1] != n) or (len(S) and S.shape[1] != n):
        return r.copy(), dict(components=0, r2=0.0, r2_scene=0.0, share_of_controls=0.0, mode=None)
    var = float(r.var())

    def fit(X):
        beta, *_ = np.linalg.lstsq(np.c_[np.ones(n), X.T], r, rcond=None)
        return r - np.c_[np.ones(n), X.T] @ beta

    def stand(Z):
        Z = Z - Z.mean(1, keepdims=True)
        sd = Z.std(1, keepdims=True)
        return Z / np.where(sd > 0, sd, 1.0)
    rows = [stand(S)] if len(S) else []
    r2_scene = float(max(0.0, 1 - fit(rows[0]).var() / var)) if rows and var > 0 else 0.0
    s, mode, share = np.zeros(0), None, 0.0
    if k:
        Z = stand(R)
        _, s, Vt = np.linalg.svd(Z, full_matrices=False)
        rows.append(Vt[:k])
        mode, tot = Vt[0], float((s ** 2).sum())
        share = float((s[:k] ** 2).sum() / tot) if tot > 0 else 0.0
    resid = fit(np.vstack(rows))
    return resid, dict(components=k, r2=float(max(0.0, 1 - resid.var() / var)) if var > 0 else 0.0, r2_scene=r2_scene,
                       share_of_controls=share, mode=mode)


def pixel_phase(r, x, y):
    """The share of a deviation curve that follows where within its pixel the object sits -- the pixel phase, dx = x -
    round(x) and dy likewise, to second order (Spitzer's intra-pixel decorrelation, Knutson et al. 2008; Deming et al.
    2015's pixel-level form): (the residual curve, r2). The disc aperture's sub-pixel weights (trap 1) should leave
    nothing here; this measures what they left. For a point: a wider thing's aperture is re-centred on its own
    centroid, which these positions are not."""
    r, x, y = (np.asarray(v, float) for v in (r, x, y))
    dx, dy = x - np.round(x), y - np.round(y)
    X = np.c_[np.ones(len(r)), dx, dy, dx * dx, dy * dy, dx * dy]
    beta, *_ = np.linalg.lstsq(X, r, rcond=None)
    resid = r - X @ beta
    var = float(r.var())
    return resid, (float(max(0.0, 1 - resid.var() / var)) if var > 0 else 0.0)


def passes_astro(A):
    """Whether a track's astronomer's tests allow its beat (GATE_ASTRO): a Lomb-Scargle false-alarm probability under
    FAP_MAX, a peak that is not a line of the sampling, and under P_MAX of its scrambled copies as high -- where the
    scramble can speak (above 1/SCRAMBLE_S)."""
    ls, sc = A.get("lombscargle") or {}, A.get("scramble") or {}
    if ls.get("fap") is not None and ls["fap"] > FAP_MAX:
        return False
    if ls.get("at_a_window_line"):
        return False
    if sc.get("p") is not None and sc["p"] > P_MAX and (ls.get("hz") or 0) >= sc["valid_above_hz"]:
        return False
    return True


def disagreements(strong, astro, far):
    """Where the astronomer's tests disagree with a beat the stage called: sentences for the notes, or none."""
    off = []
    for n in strong:
        A = astro.get(n) or {}
        ls, sc, cm = A.get("lombscargle") or {}, A.get("scramble") or {}, A.get("common_mode")
        if ls.get("fap") is not None and ls["fap"] > FAP_MAX:
            off.append(f"{n}: the Lomb-Scargle false-alarm probability of its peak is {ls['fap']:.2g}")
        if ls.get("at_a_window_line"):
            off.append(f"{n}: its peak, {ls['hz']:.2f} Hz, is at a rhythm of the sampling")
        if sc.get("p") is not None and sc["p"] > P_MAX and (ls.get("hz") or 0) >= sc["valid_above_hz"]:
            off.append(f"{n}: {sc['p']:.2f} of its chunk-scrambled copies stand as high")
        if cm and cm.get("r2", 0) >= 0.5 and cm.get("after_amplitude", 0) < 0.5 * (cm.get("before_amplitude") or 0):
            off.append(f"{n}: the scene's own change and the background apertures' common mode account for {cm['r2']:.0%} of its "
                       "curve and halve its beat")
    if far and far["whole"][0]:
        off.append(f"{far['whole'][0]} of {far['whole'][1]} background apertures pass the object's own tests themselves")
    return off


def controls_judged(use, seg, bgs, ns, fps, lines, scale, top, gone=(), windows_too=False):
    """Each background aperture put through the object's own tests, as if it were the object -- held against the others
    -- so that what passes is a false alarm by construction (the Robovetter's inverted and scrambled runs, Thompson et
    al. 2018: data known to hold no signal, through the whole pipeline): ({name: {passes, hz, amplitude, over_drift,
    drift_needed, windows_passing, windows}}, {whole: [passing, judged], windows: [passing, all]}). The windows take
    as long again as the object's did, and are run only with `windows_too`."""
    out, whole, wins = {}, [0, 0], [0, 0]
    gone = list(gone)
    for b in bgs:
        others = [c for c in bgs if c != b and c in seg]
        if not others or b not in seg:
            continue
        s0, s1 = seg[b]
        f = use[b][s0:s1]
        if any(v is None for v in f) or s1 - s0 < MIN_FRAMES:
            continue
        amps = [peak(use[c][s0:s1], fps, (), scale)["amplitude"] for c in others if not any(v is None for v in use[c][s0:s1])]
        if not amps:
            continue
        floor = float(np.median(amps))
        p = peak(f, fps, lines, scale)
        d = drift(f, fps, scale=scale)
        ok = bool(p["amplitude"] >= ABOVE * floor and d["passes"] and not p["edge"] and p["hz"] <= top
                  and p["at_the_codec_line_hz"] is None)
        row = dict(passes=ok, hz=p["hz"], amplitude=p["amplitude"], over_drift=d["over"], drift_needed=d["needed"],
                   windows_passing=None, windows=None)
        if windows_too:
            own = {m: use[m][s0:s1] for m in [b] + others}
            W = windows(own, b, others, ns[s0:s1], fps, lines, gone=[k - s0 for k in gone if s0 <= k < s1], top=top, scale=scale)
            kw = sum(1 for w in W if w["passes"])
            row.update(windows_passing=kw, windows=len(W))
            wins[0] += kw
            wins[1] += len(W)
        out[b] = row
        whole[0] += int(ok)
        whole[1] += 1
    return out, dict(whole=whole, windows=wins)


def injected(use, seg, bgs, fps, lines, scale, top, amplitudes=INJECT_AMPL, n_hz=INJECT_N, seed=0):
    """Beats planted in the background apertures' curves -- which have the frames, the grain, the codec and the camera,
    and no object -- at `amplitudes` (shares of the object's brightness) and n_hz frequencies across the band, clear of
    the codec's lines, each put through the whole track's tests as the object is (injection and recovery: Christiansen
    et al. 2013, for Kepler): {amplitudes, hz, recovered: [[the share of trials, by amplitude then frequency]], trials,
    frames, complete_from: the smallest amplitude recovered in three trials of four or more at every frequency, or
    None}. A beat is recovered where the curve passes and its strongest is within two resolutions of the frequency
    planted. On at most INJECT_MAX frames of each aperture, the middle of its stretch."""
    fmax = min(top, 0.95 * fps / 2)
    hzs = [float(v) for v in np.linspace(LOW + 1.0, fmax - 1.0, n_hz)] if fmax - LOW > 3.0 else []
    rng = np.random.default_rng(seed)
    rec = np.zeros((len(amplitudes), len(hzs)))
    trials, frames = 0, None
    for b in bgs:
        others = [c for c in bgs if c != b and c in seg]
        if not others or b not in seg or not hzs:
            continue
        s0, s1 = seg[b]
        if s1 - s0 > INJECT_MAX:
            mid = (s0 + s1) // 2
            s0, s1 = mid - INJECT_MAX // 2, mid - INJECT_MAX // 2 + INJECT_MAX
        if s1 - s0 < MIN_FRAMES or any(v is None for v in use[b][s0:s1]):
            continue
        amps = [peak(use[c][s0:s1], fps, (), scale)["amplitude"] for c in others if not any(v is None for v in use[c][s0:s1])]
        if not amps:
            continue
        floor = float(np.median(amps))
        f = np.asarray(use[b][s0:s1], float)
        frames = len(f)
        t = np.arange(len(f)) / fps
        res = fps / len(f)
        if trials == 0:                                      # planted frequencies clear of the codec's lines
            hzs = [hz + (3 * res if any(abs(hz - L) <= 2 * res for L in lines) else 0.0) for hz in hzs]
        trials += 1
        for i, a in enumerate(amplitudes):
            for j, hz in enumerate(hzs):
                g = f + a * scale * np.sin(2 * np.pi * hz * t + rng.uniform(0, 2 * np.pi))
                p = peak(g, fps, lines, scale)
                if (p["amplitude"] < ABOVE * floor or p["edge"] or p["hz"] > top or p["at_the_codec_line_hz"] is not None
                        or abs(p["hz"] - hz) > 2 * res):
                    continue
                if drift(g, fps, scale=scale)["passes"]:
                    rec[i, j] += 1
    if trials:
        rec /= trials
    complete = next((float(a) for i, a in enumerate(amplitudes) if (rec[i] >= 0.75).all()), None) if trials and hzs else None
    return dict(amplitudes=[float(a) for a in amplitudes], hz=[round(h, 3) for h in hzs], recovered=rec.round(3).tolist(),
                trials=trials, frames=frames, complete_from=complete)


def scene_curves(thumbs, positions, lo, hi, fps, ap=APERTURE):
    """The frame's level and contrast -- the mean and the spread of each frame, small (`thumbs`, THUMB px to one), with
    every tracked thing masked out of it (a box about each `positions` entry, the aperture and 8 px about, so that a
    bright point's own beat is not read as the scene's) -- over the places lo..hi of the frames, each as a deviation
    curve (`deviation`): rows for `common_mode`'s `scene`. None where the thumbs do not cover the stretch."""
    if not thumbs or len(thumbs) < hi or any(thumbs[k] is None for k in range(lo, hi)):
        return None
    level, spread = [], []
    for k in range(lo, hi):
        t = np.asarray(thumbs[k], float)
        m = np.ones(t.shape, bool)
        for x, y in (positions or {}).values():
            if k < len(x):
                cx, cy, h = x[k] / THUMB, y[k] / THUMB, (ap + 8) / THUMB + 1
                y0, y1 = int(max(0, np.floor(cy - h))), int(min(t.shape[0], np.ceil(cy + h) + 1))
                x0, x1 = int(max(0, np.floor(cx - h))), int(min(t.shape[1], np.ceil(cx + h) + 1))
                m[y0:y1, x0:x1] = False
        if m.sum() < 16:
            return None
        level.append(float(t[m].mean()))
        spread.append(float(t[m].std()))
    return np.stack([deviation(level, fps), deviation(spread, fps)])


def ap_of(fields, name):
    """The aperture radius a track was measured with (fields["aperture_px"]: one number before 2026-10-10, since then one a track)."""
    a = fields.get("aperture_px")
    return float(a.get(name, APERTURE)) if isinstance(a, dict) else float(a or APERTURE)


def fold(r, hz, fps, stamps, thumbs=None, ap=APERTURE, at=None, controls=()):
    """The frames folded on the beat (epoch folding, as pulsar data is read; and Kepler's difference image, Bryson et
    al. 2013): the deviation curve r in FOLD_BINS bins of the beat's cycle, the brightest bin's half of the cycle
    against the other half, and the mean picture of the object over the bright half less that over the dim half --
    where in the picture the brightness that beats is. A beat of the object's folds into the object's pixels; the
    codec's rhythm into blocks over the frame; a change of gain into the whole scene; a neighbour's beat beside it.
    `stamps` are the object's stamps (`stamp`) for the frames of r, `thumbs` the frames small (`_apertures`; THUMB px
    to one), `at` the object's place and reach in a thumb (x, y, half-width, half-height), `controls` the background
    apertures' deviation curves over the same frames. Returns ({hz, bins, bright_frames, dim_frames, amplitude,
    controls_amplitude, in_aperture_share, area_share, concentration, offset_px, object_peak, scene_rms, at}, (the
    bright stamp, the dim stamp, their difference, the whole frame's difference)) -- the pictures None where there
    were too few stamps."""
    r = np.asarray(r, float)
    n = len(r)
    ph = (np.arange(n) / fps * hz) % 1.0
    b = np.minimum((ph * FOLD_BINS).astype(int), FOLD_BINS - 1)
    bins = [float(r[b == i].mean()) if (b == i).any() else 0.0 for i in range(FOLD_BINS)]
    ph0 = (int(np.argmax(bins)) + 0.5) / FOLD_BINS
    dist = np.abs(((ph - ph0 + 0.5) % 1.0) - 0.5)
    bright, dim = dist < 0.25, dist >= 0.25
    out = dict(hz=float(hz), bins=bins, bright_frames=int(bright.sum()), dim_frames=int(dim.sum()), amplitude=None,
               controls_amplitude=None, in_aperture_share=None, area_share=None, concentration=None, offset_px=None,
               object_peak=None, scene_rms=None, at=[float(v) for v in at] if at else None)
    pics = (None, None, None, None)
    if bright.sum() < 2 or dim.sum() < 2:
        return out, pics
    out["amplitude"] = float(0.5 * (r[bright].mean() - r[dim].mean()))
    cs = [np.asarray(c, float) for c in controls if len(c) == n]
    if cs:
        out["controls_amplitude"] = float(np.median([0.5 * (c[bright].mean() - c[dim].mean()) for c in cs]))
    ok = np.array([s is not None for s in stamps]) if stamps is not None and len(stamps) == n else np.zeros(n, bool)
    if (ok & bright).sum() >= 2 and (ok & dim).sum() >= 2:
        A = np.stack([np.asarray(stamps[k], float) for k in range(n) if ok[k]])
        S = A.shape[-1] // 2
        yy, xx = np.mgrid[-S:S + 1, -S:S + 1]
        rr = np.hypot(xx, yy)
        ring = (rr >= min(ap + 3, S - 2)) & (rr <= S)
        A = A - np.median(A[:, ring], axis=1)[:, None, None]      # each stamp's contrast over its own ring
        mb, md = A[bright[ok]].mean(0), A[dim[ok]].mean(0)
        diff = mb - md
        inside = rr <= ap
        tot = float(np.abs(diff).sum())
        share = float(np.abs(diff)[inside].sum() / tot) if tot > 0 else 0.0
        area = float(inside.mean())
        sm = ndimage.gaussian_filter(diff, 1.0)
        near = np.abs(sm) * (rr <= 2 * ap)                       # the change's centroid within twice the aperture: a clipped
        cx, cy = (float((near * xx).sum() / near.sum()), float((near * yy).sum() / near.sum())) if near.sum() > 0 else (0.0, 0.0)
        out.update(in_aperture_share=share, area_share=area, concentration=float(share / area) if area > 0 else None,
                   offset_px=float(np.hypot(cx, cy)), object_peak=float(sm[S, S]))   # core beats as a ring about the object
        pics = (mb, md, diff, None)
    if thumbs is not None and len(thumbs) == n and all(t is not None for t in thumbs):
        T = np.stack([np.asarray(t, float) for t in thumbs])
        scene = T[bright].mean(0) - T[dim].mean(0)
        mask = np.ones(scene.shape, bool)
        if at:
            x0, y0, hw, hh = at
            ys, xs = np.mgrid[0:scene.shape[0], 0:scene.shape[1]]
            mask &= ~((np.abs(xs - x0) <= hw) & (np.abs(ys - y0) <= hh))
        if mask.sum() > 16:
            out["scene_rms"] = float(np.sqrt(np.mean(scene[mask] ** 2)))
        pics = (pics[0], pics[1], pics[2], scene)
    return out, pics


def said_astro(fields):
    """What `mcdonald flicker` prints of the astronomer's tests, from the fields."""
    L = []
    for name, A in (fields.get("astro") or {}).items():
        ls, sc, cm, pp = A.get("lombscargle") or {}, A.get("scramble") or {}, A.get("common_mode"), A.get("pixel_phase")
        if ls.get("hz") is not None:
            L.append(f"  {name}, over frames {A['frames'][0]}-{A['frames'][1]}, Lomb-Scargle on {ls['kept']} frames" + (f" ({ls['dropped']} held or lost, left out)" if ls["dropped"] else "")
                     + f": {ls['hz']:.2f} Hz, power {ls['power']:.2f}, false-alarm probability {ls['fap']:.1e}"
                     + (f"; the sampling's own rhythm at {', '.join(f'{v:.1f}' for v in ls['window_lines_hz'])} Hz" if ls["window_lines_hz"] else "")
                     + (" -- the peak is at it" if ls.get("at_a_window_line") else ""))
        if sc.get("p") is not None:
            L.append(f"  {name}, scrambled in {sc['chunk_s']:.2f}-s chunks: {sc['p']:.3f} of {sc['runs']} copies stand as high "
                     f"({sc['stands']:.0f}x the band; {sc['needed']:.0f}x would be 1 in 100), said above {sc['valid_above_hz']:.1f} Hz")
        if cm:
            L.append(f"  {name}, the scene's level and contrast and the background's common mode ({cm['components']} components) account "
                     f"for {cm['r2']:.0%} of its curve (the scene alone {cm.get('r2_scene', 0):.0%}); "
                     f"without them {cm['after_hz']:.2f} Hz, {cm['after_amplitude']:.1%} (before {cm['before_amplitude']:.1%})"
                     + (f"; the mode itself peaks at {cm['mode_hz']:.2f} Hz" + (" -- the codec's" if cm.get("mode_at_the_codec_line_hz") else "")
                        if cm.get("mode_hz") is not None else ""))
        if pp:
            L.append(f"  {name}, the pixel phase accounts for {pp['r2']:.0%} of its curve; without it {pp['after_hz']:.2f} Hz, {pp['after_amplitude']:.1%}")
    far = fields.get("false_alarm")
    if far and far["whole"][1]:
        L.append(f"  the background apertures through the object's own tests: {far['whole'][0]} of {far['whole'][1]} beat over the whole track"
                 + (f", {far['windows'][0]} of {far['windows'][1]} of their windows" if far["windows"][1] else ""))
    inj = fields.get("injection")
    if inj and inj.get("trials"):
        L.append(f"  beats planted in the background apertures ({inj['trials']} apertures, {inj['frames']} frames, at "
                 + ", ".join(f"{h:.1f}" for h in inj["hz"]) + " Hz), recovered: "
                 + "; ".join(f"{a:.0%} of the brightness in {np.mean(row):.0%} of trials" for a, row in zip(inj["amplitudes"], inj["recovered"]))
                 + (f" -- complete from {inj['complete_from']:.0%}" if inj.get("complete_from") is not None else " -- none at every frequency"))
    for name, fo in (fields.get("fold") or {}).items():
        if fo.get("amplitude") is None:
            continue
        L.append(f"  {name}, folded on {fo['hz']:.2f} Hz: bright half over dim {fo['amplitude']:.1%}"
                 + (f" (the background beside it {fo['controls_amplitude']:.1%})" if fo.get("controls_amplitude") is not None else "")
                 + (f"; the difference picture holds {fo['in_aperture_share']:.0%} of its change within the aperture, "
                    f"{fo['concentration']:.1f}x the aperture's share of it, peaking {fo['offset_px']:.1f} px off the object"
                    if fo.get("concentration") is not None else "")
                 + (f"; the rest of the frame changes {fo['scene_rms']:.2f} levels rms" if fo.get("scene_rms") is not None else ""))
    return L


def measure(clip, tracks, dark=False, out=None, say=print, progress=None, stop=None, procs=None, nulls=False):
    """The stage: each track's beat, the background apertures' about the first, the codec's rhythm,
    and -- with two tracks or more -- whether they beat as one. `tracks` is {name: {frame: (x, y)}}:
    the object's track, or the members of a group (groups.members). Writes <out>_flicker.csv. `nulls` runs the slower
    controls as well: the background apertures through every window, and beats planted in them (the stage's command
    and `mcdonald run` do; a test need not)."""
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
    sz = sizes(clip, tracks, ns, dark)
    ap = {name: s for name, (_, s) in sz.items()}
    fields.update(extent_px={n: e for n, (e, _) in sz.items()}, aperture_px={n: s[0] for n, s in ap.items()},
                  ring_px={n: list(s[1]) for n, s in ap.items()}, background_px=ap[first][2],
                  recentred=[n for n, s in ap.items() if s[3]])
    wide = [n for n, s in ap.items() if s[3]]
    if wide:
        say("  aperture follows the object: " + "; ".join(
            f"{n} {sz[n][0]:.1f} px across in radius -> aperture {ap[n][0]:.1f} px, ring {ap[n][1][0]:.0f}-{ap[n][1][1]:.0f} px,"
            f" re-centred each frame" for n in wide))
    thumbs, stamps = [], {}
    pos = {name: smoothed(t, ns) for name, t in tracks.items()}
    raw = curves(clip, tracks, ns, dark, progress, stop, about=first, procs=procs, ap=ap, thumbs=thumbs, stamps=stamps)
    fields["pictures"] = pictures(thumbs, clip.fps)
    if fields["pictures"]["held"] >= HELD_MIN:
        say(f"  the video holds pictures: {fields['pictures']['held']:.0%} of frames repeat the one before, so it carries "
            f"{fields['pictures']['rate']:.1f} pictures a second, and a beat is heard only up to {fields['pictures']['top_hz']:.1f} Hz")
    found = judge(raw, ns, clip.fps, lines, fields, first, out=out, say=say, positions=pos, stamps=stamps, thumbs=thumbs, nulls=nulls)
    if wide:
        found.notes.append("The object is wider than the point-sized aperture, so the aperture follows it: " + "; ".join(
            f"{n} falls to {EXTENT_DROP:.0%} of its height {sz[n][0]:.1f} px out, so its aperture is {ap[n][0]:.1f} px, "
            f"its ring {ap[n][1][0]:.0f}-{ap[n][1][1]:.0f} px, re-centred each frame on its own centroid" for n in wide)
            + f"; the background apertures are {ap[first][2]} px from it.")
    return found


def judge(raw, ns, fps, lines, fields, first, out=None, say=print, positions=None, stamps=None, thumbs=None, nulls=False):
    """The stage from the curves on (`measure` reads them): `raw` is {name: brightness on each frame of
    ns, None where it was not measured} for each track in fields["tracks"] and for the background
    apertures, which go with the track `first`; fields has the codec, the tracks' spans and the stretch.
    `positions` is {track: (x, y) over ns} (`smoothed`), `stamps` {track: [stamp per frame]} and `thumbs` the frames
    small (`curves`), for the astronomer's tests (item 7); each is optional, and the test that needs it is left out
    without it. `nulls` runs the slower of them (`controls_judged`'s windows, `injected`)."""
    names, lo = fields["tracks"], ns[0]
    k0 = {name: (a - lo, b - lo + 1) for name, (a, b) in fields["spans"].items()}
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
    # where a track is lost against what is behind it (PR23, 2026-10-09: a hot roof), its ends are trimmed as well,
    # and the frames between are filled across in every curve measured with it -- `use`, which the spectra are taken
    # of; `raw` is what was measured, and is what the CSV keeps
    use, gone, too_lost = dict(raw), {}, {}
    for name in names:
        if name not in seg:
            continue
        s0, s1 = seg[name]
        own = raw[name][s0:s1]
        if any(v is None for v in own) or np.median(own) <= 0:
            continue                                       # refused below, as before
        bad = lost(own, fps)
        if not bad.any():
            continue
        a, b = 0, len(own)
        while a < b and bad[a]:
            a += 1
        while b > a and bad[b - 1]:
            b -= 1
        gone[name] = [s0 + k for k in range(a, b) if bad[k]]
        fields.setdefault("lost", {})[name] = [int(ns[s0 + k]) for k in np.flatnonzero(bad)]
        if bad.sum() > LOST_MAX * len(own):
            too_lost[name] = (int(bad.sum()), len(own))
        seg[name] = (s0 + a, s0 + b) if b > a else None
        if seg[name] is None:
            del seg[name]
            continue
        for m in [name] + ([c for c in raw if c.startswith("background")] if name == first else []):
            if m not in seg:
                continue
            f = list(use[m])
            if m != name:                                  # the apertures beside it go no further than it does
                seg[m] = (max(seg[m][0], seg[name][0]), min(seg[m][1], seg[name][1]))
            m0, m1 = seg[m]
            part = f[m0:m1]
            if gone[name] and not any(v is None for v in part):
                mask = np.isin(np.arange(m0, m1), gone[name])
                f[m0:m1] = filled(part, mask).tolist()
            use[m] = f
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
    for name, f in use.items():                            # the object's (or members') first, then the background's
        bg = name.startswith("background")
        s = seg.get(name)
        own = f[s[0]:s[1]] if s else []
        ok = [v for v in own if v is not None]
        if len(ok) < len(own) or len(own) < MIN_FRAMES or (not bg and np.median(ok) <= 0) or (bg and not scale) or name in too_lost:
            per[name] = None
            continue
        if not bg and scale is None:
            scale = float(np.median(ok))                   # the background apertures are measured in this
        fr, F, band, wsum, _ = spectrum(own, fps, scale if bg else None)
        spectra[name] = dict(fr=fr, F=F, band=band, wsum=wsum, peak=peak(own, fps, lines, scale if bg else None))
        per[name] = spectra[name]["peak"]
    obj = [n for n in names if per.get(n)]
    bgs = [n for n in raw if n.startswith("background") and per.get(n)]
    fields["curves"] = per
    fields["short"] = [n for n in names if n in seg and seg[n][1] - seg[n][0] < MIN_FRAMES]     # members too brief for a beat
    if not obj:
        if too_lost:
            name, (k, n) = next(iter(too_lost.items()))
            why = (f"the object is lost against what is behind it on {k} of its {n} frames (its brightness over the ring "
                   f"under {DROP:.0%} of its own, or none), more than {LOST_MAX:.0%} of them: no beat is looked for")
        else:
            why = "the object is not brighter than the ring about it on every frame, or its aperture leaves the frame"
        return Found("flicker", fields=dict(fields, beats=None, finding=None), no_power=[("flicker", why)])
    res = fps / max(1, fields["frames"])         # of the stretch reported: the object's (the member seen longest)
    if not bgs:
        return Found("flicker", fields=dict(fields, beats=None, finding=None),
                     no_power=[("flicker", "no background aperture beside the object could be measured, so there is "
                                           "nothing to hold its beat against")])
    floor = float(np.median([per[b]["amplitude"] for b in bgs]))       # the scene's and the codec's own flicker
    fields["noise_floor"] = floor
    # the beat in windows along the track, and what is reported for each object: the clearest window that passes
    # where it is clearer than the whole track, or where the whole track does not pass, else the whole track -- as a
    # fundamental with its double named. The whole track passes where its strongest beat is ABOVE the background's
    # and stands over its own drift (`drift`).
    fields["windows"], fields["beat"] = {}, {}
    pic = fields.get("pictures") or dict(rate=fps, held=0.0, top_hz=TOP * fps / 2)
    top = pic["top_hz"]
    fields["top_hz"] = top
    whole_ok = {}
    for n in obj:
        s0, s1 = seg[n]
        own = {m: use[m][s0:s1] for m in [n] + bgs}
        d = drift(own[n], fps)
        per[n].update(over_drift=d["over"], drift_needed=d["needed"])
        per[n]["above_top"] = per[n]["hz"] > top
        whole_ok[n] = per[n]["amplitude"] >= ABOVE * floor and d["passes"] and not per[n]["edge"] and per[n]["hz"] <= top
        wins = windows(own, n, bgs, ns[s0:s1], fps, lines, gone=[k - s0 for k in gone.get(n, [])], top=top)
        fields["windows"][n] = wins
        passing = [w for w in wins if w["passes"]]
        best = max(passing, key=lambda w: w["stands"]) if passing else None
        fund, dbl, _, _ = harmonics(own[n], fps, drift_too=True)
        whole = dict(first=ns[s0], last=ns[s1 - 1], hz=fund, double_hz=dbl, amplitude=per[n]["amplitude"], stands=per[n]["stands"],
                     resolution_hz=per[n]["resolution_hz"], source="the whole track")
        if best is not None and (best["stands"] > per[n]["stands"] or not whole_ok[n]):
            pick = dict(first=best["first"], last=best["last"], hz=best["fundamental_hz"], double_hz=best["double_hz"],
                        amplitude=best["amplitude"], stands=best["stands"], resolution_hz=best["resolution_hz"],
                        source=f"the clearest of {len(passing)} windows of {WINDOW_S:g} s that beat, of {len(wins)}")
        else:
            pick = whole
        clear = [w for w in passing if best is not None and w["stands"] >= 0.5 * best["stands"]]     # the clear windows' range
        pick["hz_range"] = [min(w["fundamental_hz"] for w in clear), max(w["fundamental_hz"] for w in clear)] if clear else None
        pick["windows_passing"] = len(passing)
        pick["windows"] = len(wins)
        fields["beat"][n] = pick
    strong = [n for n in obj if whole_ok[n] or fields["beat"][n]["windows_passing"]]
    fields["strong"] = strong
    # ---- the astronomer's tests (item 7; 2026-10-15): each beside the stage's own, in the fields -----------------
    held_k = set(pic.get("held_k") or [])
    astro = {}
    for n in obj:
        b = fields["beat"][n]
        s0, s1 = b["first"] - lo, b["last"] - lo + 1         # the stretch the beat is reported from (a window, or the whole track)
        if not (seg[n][0] <= s0 < s1 <= seg[n][1]):
            s0, s1 = seg[n]
        r = deviation(use[n][seg[n][0]:seg[n][1]], fps)[s0 - seg[n][0]:s1 - seg[n][0]]
        gone_n = set(gone.get(n, []))
        keep = np.array([k not in held_k and k not in gone_n for k in range(s0, s1)])
        A = dict(frames=[int(ns[s0]), int(ns[s1 - 1])], lombscargle=ls_peak(r, fps, keep, top=top), scramble=scrambled(r, fps, top=top),
                 common_mode=None, pixel_phase=None)
        cs = [c for c in bgs if c in seg]
        lo_, hi_ = max([s0] + [seg[c][0] for c in cs]), min([s1] + [seg[c][1] for c in cs])
        if cs and hi_ - lo_ >= MIN_FRAMES and not any(v is None for c in cs for v in use[c][lo_:hi_]):
            rr = deviation(use[n][seg[n][0]:seg[n][1]], fps)[lo_ - seg[n][0]:hi_ - seg[n][0]]
            scene = scene_curves(thumbs, positions, lo_, hi_, fps, ap_of(fields, n)) if thumbs else None
            resid, cm = common_mode(rr, np.stack([deviation(use[c][seg[c][0]:seg[c][1]], fps, scale)[lo_ - seg[c][0]:hi_ - seg[c][0]]
                                                  for c in cs]), scene=scene)
            mode = cm.pop("mode")
            before, after = _peak(rr, fps, lines), _peak(resid, fps, lines)
            own = _peak(mode, fps, lines) if mode is not None else None
            cm.update(frames=[int(ns[lo_]), int(ns[hi_ - 1])], before_hz=before["hz"], before_amplitude=before["amplitude"],
                      after_hz=after["hz"], after_amplitude=after["amplitude"], after_stands=after["stands"],
                      mode_hz=own["hz"] if own else None, mode_at_the_codec_line_hz=own["at_the_codec_line_hz"] if own else None)
            A["common_mode"] = cm
        if positions and n in positions:
            x, y = positions[n]
            resid, r2 = pixel_phase(r, x[s0:s1], y[s0:s1])
            q = _peak(resid, fps, lines)
            A["pixel_phase"] = dict(r2=r2, after_hz=q["hz"], after_amplitude=q["amplitude"])
        astro[n] = A
    fields["astro"] = astro
    gated = []
    if GATE_ASTRO:                                           # the first two decide as well (off until the goldens are read with it)
        gated = [n for n in strong if not passes_astro(astro[n])]
        strong = [n for n in strong if n not in gated]
        fields["strong"], fields["gated"] = strong, gated
    ctrl, far = controls_judged(use, seg, bgs, ns, fps, lines, scale, top, gone=gone.get(first, ()), windows_too=nulls)
    fields["controls"], fields["false_alarm"] = ctrl, far
    if nulls:
        fields["injection"] = injected(use, seg, bgs, fps, lines, scale, top)
    folds, drawn = {}, []
    if stamps:
        for n in obj:
            b = fields["beat"][n]
            a, c = b["first"] - lo, b["last"] - lo + 1       # the stretch the beat is reported from, as places in ns
            s0, s1 = seg[n]
            if not (s0 <= a < c <= s1) or n not in stamps:
                continue
            r = deviation(use[n][s0:s1], fps)[a - s0:c - s0]
            ctrls = [deviation(use[cc][a:c], fps, scale) for cc in bgs
                     if cc in seg and seg[cc][0] <= a and seg[cc][1] >= c and not any(v is None for v in use[cc][a:c])]
            at = None
            if positions and n in positions:
                x, y = positions[n]
                at = (float(np.median(x[a:c])) / THUMB, float(np.median(y[a:c])) / THUMB,
                      (float(np.ptp(x[a:c])) / 2 + ap_of(fields, n) + 8) / THUMB, (float(np.ptp(y[a:c])) / 2 + ap_of(fields, n) + 8) / THUMB)
            numbers, pics = fold(r, b["hz"], fps, stamps[n][a:c], thumbs[a:c] if thumbs else None, ap=ap_of(fields, n), at=at, controls=ctrls)
            folds[n] = numbers
            if n in strong:
                drawn.append((n, numbers, pics))
    fields["fold"] = folds
    # the background shares the beat if, at the object's own frequency over the whole track, it beats half as strongly
    # or more -- asked of every object with a beat, wherever the beat reported comes from, as is the codec's rhythm
    def at(name, hz):
        S = spectra[name]
        k = int(np.argmin(np.abs(S["fr"] - hz)))
        return float(2 * np.abs(S["F"][k]) / S["wsum"])
    shared = [b for b in bgs if any(at(b, per[n]["hz"]) >= SHARED * per[n]["amplitude"] for n in strong)]
    pairs = common(use, seg, obj, ns, fps, lines) if len(obj) > 1 else []
    fields["pairs"] = pairs
    at_line = [n for n in strong if per[n]["at_the_codec_line_hz"] is not None]
    npw, notes = [], []
    if not strong:
        over = [n for n in obj if per[n]["amplitude"] >= ABOVE * floor]
        if gated:
            b = fields["beat"][gated[0]]
            beats, why = False, (f"what beats at {b['hz']:.2f} Hz, {b['amplitude']:.0%} of its brightness, does not pass the "
                                 f"astronomer's tests: " + "; ".join(disagreements(gated, astro, None)) + ": no beat of its own")
        elif over and per[over[0]]["above_top"]:
            p = per[over[0]]
            held = (f"it holds pictures ({pic['held']:.0%} of frames repeat the one before) and carries {pic['rate']:.1f} "
                    "a second, so " if pic["held"] >= HELD_MIN else "")
            beats, why = False, (f"its strongest, at {p['hz']:.2f} Hz, is above the highest frequency this video can carry as "
                                 f"a beat: {held}a beat is heard only up to {top:.1f} Hz ({TOP:g} of the Nyquist frequency), "
                                 f"and nothing below that beats: no beat of its own in {fields['frames']} frames")
        elif over and per[over[0]]["edge"]:
            p = per[over[0]]
            beats, why = False, (f"its strongest, at {p['hz']:.2f} Hz, is only the edge of the band a beat is looked for in: "
                                 f"its brightness changes more slowly than {LOW:g} Hz, which is not a beat, and no window of "
                                 f"{WINDOW_S:g} s along the track beats: no beat of its own in {fields['frames']} frames")
        elif over:
            p = per[over[0]]
            beats, why = False, (f"what peaks at {p['hz']:.2f} Hz, {p['amplitude']:.0%} of its brightness, is no more than "
                                 f"a brightness that only wanders slowly makes there once its running mean is taken out "
                                 f"(it stands {p['over_drift']:.1f} times over that, where {p['drift_needed']:.1f} would be a "
                                 f"beat), and no window of {WINDOW_S:g} s along the track beats: no beat of its own in "
                                 f"{fields['frames']} frames")
        else:
            beats, why = False, (f"no beat reaches {ABOVE:g} times what the background beside it does ({floor:.1%} of the "
                                 f"object's brightness, the median of their strongest) in {len(ns)} frames "
                                 f"({len(ns) / fps:.1f} s, resolution {res:.2f} Hz)")
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
    if beats is True:                                      # where the astronomer's tests disagree with the stage, the notes say so
        off = disagreements(strong, astro, far)
        if off:
            notes.append("The astronomer's checks disagree with the beat: " + "; ".join(off) + ". They are reported with the "
                         "measurement and do not yet decide it.")
    if fields.get("lost"):
        where = "; ".join(_frames(v) + (f" ({n})" if len(names) > 1 else "") for n, v in fields["lost"].items())
        why += f"; frames {where}, where it was lost against what is behind it, are left out"
        notes.append(f"Lost against what is behind it (its brightness over the ring under {DROP:.0%} of its own level, "
                     f"or none) on frames {where}: left out of the spectra -- filled across from the frames either side, or "
                     "trimmed at the ends -- and no window holding one is used. What a crossing does to the contrast is "
                     "the background's, not the object's.")
    fields.update(beats=beats, finding=why, resolution_hz=res)
    notes.append("A beat that is the object's own says it varies; it does not say it is a wingbeat. A tumbling or "
                 "rotating body beats too, and so does a light that blinks.")
    result = {n: ("" if n in strong else "strongest peak ")
              + f"{fields['beat'][n]['hz']:.2f} Hz" + (f" (and {fields['beat'][n]['double_hz']:.2f}, its double)" if fields["beat"][n]["double_hz"] else "")
              + f", {fields['beat'][n]['amplitude']:.1%}, {fields['beat'][n]['stands']:.0f}x the band, frames "
              f"{fields['beat'][n]['first']}–{fields['beat'][n]['last']}"
              + (f" (at the codec's {per[n]['at_the_codec_line_hz']:g} Hz)" if per[n]["at_the_codec_line_hz"] else "")
              + ("" if n in strong else "; no beat of its own")
              for n in obj}
    result["finding"] = why
    files = []
    if out:
        with open(f"{out}_flicker.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["frame", "t_s"] + list(raw))
            for k, n in enumerate(ns):
                w.writerow([n, round((n - 1) / fps, 4)] + ["" if raw[c][k] is None else round(raw[c][k], 2) for c in raw])
        files.append(f"{out}_flicker.csv")
        say(f"wrote {out}_flicker.csv")
        if beats is True:                    # a beat the stage calls the object's own is drawn with its controls (PR41, 2026-10-10)
            try:
                from . import figures
                files.append(figures.beat(f"{out}_beat.png", fps, ns, use, seg, scale, fields["beat"], strong, bgs,
                                          lines, trend=trend_frames(fps)))
                say(f"wrote {out}_beat.png")
            except Exception as e:           # a figure that cannot be drawn does not undo the measurement
                say(f"  ! the beat figure was not drawn: {type(e).__name__}: {e}")
            if drawn:
                try:
                    from . import figures
                    files.append(figures.fold(f"{out}_fold.png", drawn, fps))
                    say(f"wrote {out}_fold.png")
                except Exception as e:
                    say(f"  ! the fold figure was not drawn: {type(e).__name__}: {e}")
    return Found("flicker", result, fields, files=files, no_power=npw, notes=notes)


def _frames(ks):
    """Frame numbers as runs: [131, 132, 133, 138] -> "131–133 and 138"."""
    runs = []
    for k in sorted(ks):
        if runs and k == runs[-1][1] + 1:
            runs[-1][1] = k
        else:
            runs.append([k, k])
    said = [f"{a}–{b}" if b > a else f"{a}" for a, b in runs]
    return ", ".join(said[:-1]) + " and " + said[-1] if len(said) > 1 else said[0]


def of_member(group, name, folder, track=None):
    """A member of a group followed on its own (`several.split_group`): its flicker stage, read from
    the group's (`group`: that stage's fields), where it was measured over its own frames beside its
    fellows. The beat is its own where it is out of step with another member's, or at another frequency
    -- the test a flock allows that one thing alone does not (PR135, 2026-10-08: alone, three of the
    paper's six birds are vetoed by the codec's line or the bird beside them). Nothing is read from the
    video here."""
    beat = (group.get("beat") or {}).get(name)
    pairs = [q for q in group.get("pairs") or [] if name in q["members"]]
    span = (group.get("spans") or {}).get(name)
    frames = len(track) if track else (span[1] - span[0] + 1 if span else 0)
    fields = dict(codec=group.get("codec"), frames=frames, first=span[0] if span else None, last=span[1] if span else None,
                  tracks=["object"], curves={"object": (group.get("curves") or {}).get(name)}, pairs=pairs,
                  resolution_hz=(beat or {}).get("resolution_hz"),
                  aperture_px=(lambda a: a.get(name) if isinstance(a, dict) else a)(group.get("aperture_px")),
                  of_group=dict(folder=folder, member=name, members=len(group.get("beat") or {}), beats=group.get("beats")))
    npw, notes = [], [f"Measured with the other members of its group ({folder}), each over its own frames, in the group's "
                      "flicker stage: a beat is its own where it is at another frequency, or out of step, from a fellow's, "
                      "which a rhythm of the video cannot do."]
    with_ = lambda q: q["members"][1] if q["members"][0] == name else q["members"][0]
    strong = group.get("strong")                           # a case from before 2026-10-09 has none: its beats passed then
    if not beat or (strong is not None and name not in strong):
        if name in (group.get("short") or []):
            why = f"seen on {frames} frames, under the {MIN_FRAMES} a beat needs"
        else:
            why = ("no beat in the group's flicker stage: not brighter than the ring about it on every frame, or nothing past "
                   "the background beside it and its own slow change")
        npw.append(("flicker", why))
        return Found("flicker", dict(finding=why), dict(fields, beat={}, beats=None, finding=why), no_power=npw, notes=notes)
    apart = [q for q in pairs if q["independent"]]
    shown = f"{beat['hz']:.2f} Hz" + (f" (and at {beat['double_hz']:.2f}, its double)" if beat.get("double_hz") else "")
    if apart:
        beats = True
        why = (f"it beats at {shown}, {beat['amplitude']:.0%} of its brightness, over frames {beat['first']}–{beat['last']}; "
               f"out of step with, or at another frequency from, {', '.join(with_(q) for q in apart)} of its group: the beat is its own")
    elif pairs:
        beats = None
        why = (f"it beats at {shown}, as one with {', '.join(with_(q) for q in pairs)} of its group, at one frequency and in step: "
               "a rhythm of the video would do that")
        npw.append(("flicker", why))
    else:
        beats = None
        why = f"it beats at {shown}, and no other member shares the {MIN_FRAMES} frames it takes to hear whether the beat is its own"
        npw.append(("flicker", why))
    result = {"object": f"{shown}, {beat['amplitude']:.1%}, {beat['stands']:.0f}x the band, frames {beat['first']}–{beat['last']}",
              "finding": why}
    return Found("flicker", result, dict(fields, beat={"object": beat}, beats=beats, finding=why), no_power=npw, notes=notes)


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
                     f"band's median" + (f", {p['over_drift']:.1f} times what its drift makes there ({p['drift_needed']:.1f} needed)"
                                         if p.get("over_drift") is not None else "")
                     + (f"  -- at the codec's {p['at_the_codec_line_hz']:g} Hz" if p["at_the_codec_line_hz"] else ""))
        else:
            L.append(f"  {name}: not measured (not brighter than its ring on every frame, lost against what is behind it too "
                     "often, or off the frame)")
    for name, ks in (fields.get("lost") or {}).items():
        L.append(f"  {name}: lost against what is behind it on frames {_frames(ks)}, left out")
    for name, b in (fields.get("beat") or {}).items():
        L.append(f"  {name}, in windows of {WINDOW_S:g} s along the track: {b['windows_passing']} of {b['windows']} beat"
                 + (f", at {b['hz_range'][0]:.2f}-{b['hz_range'][1]:.2f} Hz" if b.get("hz_range") else "")
                 + ("; reported: " if name in fields.get("strong", [name]) else "; no beat of its own, the strongest: ")
                 + f"{b['hz']:.2f} Hz" + (f" and its double {b['double_hz']:.2f}" if b["double_hz"] else "")
                 + f", {b['amplitude']:.1%}, {b['stands']:.0f}x, frames {b['first']}-{b['last']} ({b['source']})")
    for q in fields.get("pairs") or []:
        L.append(f"  {q['members'][0]} x {q['members'][1]}: {q['hz'][0]:.2f} and {q['hz'][1]:.2f} Hz, "
                 f"{q['phase_deg']:+.0f} deg apart at {q['cross_hz']:.2f}"
                 + (f" over frames {q['frames'][0]}-{q['frames'][1]}" if q.get("frames") else "")
                 + ("  (independent)" if q["independent"] else ""))
    if fields.get("short"):
        L.append(f"  too brief for a beat (under {MIN_FRAMES} frames): " + ", ".join(fields["short"]))
    L += said_astro(fields)
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
    ap.add_argument("--procs", type=int, default=None, help=PROCS_HELP)
    ap.add_argument("--no-nulls", action="store_true", help="skip the slower controls: the background apertures through "
                                                            "every window as if each were the object, and beats planted in them")
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
    found = measure(clip, tracks, dark=args.dark, out=out, progress=to_stderr(), procs=args.procs, nulls=not args.no_nulls)
    print("\n".join(said(found.fields)))
    return found, clip


if __name__ == "__main__":
    raise SystemExit(main())
