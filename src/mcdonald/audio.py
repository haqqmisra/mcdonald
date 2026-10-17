"""What a video's sound track records: is there sound, which steady tones are in it, and what each one says.

An accident investigator reads a cockpit recording's spectrum for the engines, propellers and rotors that were
turning (the NTSB's "Sound Spectrum Study"); forensic audio reads the mains hum as a clock (electric network
frequency). A UAP video that carries sound can be read the same way, and the pixels cannot give what it gives:

- **the codec's own frames.** An AAC encoder works in frames of 1,024 samples, so near-silence carries faint lines
  at multiples of 46.875 Hz (48 kHz) or 43.07 Hz (44.1 kHz), an MP3 encoder at multiples of 1/1,152 of its rate.
  They are named first, because they look like machinery and are not (PURSUE's PR39: five AAC lines at 48 kHz). A
  family from a rate the file is not at is an earlier encode.
- **a supply, as a clock.** The mains (50 or 60 Hz) and an aircraft's 400-Hz bus hold their frequency, so a
  harmonic series on one gives the speed the file plays at against real time: a retimed clip moves its hum. The
  aircraft bus may stray 393-407 Hz in steady state (MIL-STD-704, from memory), the mains about 0.2 % at most
  (taken wide). PR106 and PR107 carry the bus at 399.7 Hz; PR113 the 60-Hz mains and its NTSC tape's 29.97-Hz
  frame buzz.
- **a propeller or rotor, as the platform.** A propeller with B blades turning at R rpm sounds at its blade-pass
  B R / 60 and its harmonics. Both C-130 propellers turn at about 1,020 rpm in flight, so a T56 C-130 (four blades)
  hums at 68 Hz and a C-130J (six) at 102 -- a fifth apart. PR117-PR119, phone captures of an AC-130's sensor
  display over the Gulf of Oman in 2021, hum at 67.75 Hz with its harmonics: a four-bladed gunship in flight,
  not the AC-130J of AARO's description (the aviation methods survey, with controls from DVIDS cabin audio). Each
  airframe also carries a second steady tone at a fixed ratio to its blade-pass in flight (8.13x on the T56, 5.39x
  on the C-130J), and that is the check: PR117-PR119's is at 8.129x.
- **where each folds through the frame rate.** The airframe shakes a phone at its blade-pass, a lamp flickers at
  twice the mains: folded through the video's frame rate (`flicker.alias`) each lands somewhere in the band a
  beat is looked for in -- PR117's 67.75 Hz at 30 frames a second at 7.75 Hz, where birds beat. These are the
  clip's own look-alikes, heard rather than assumed (`lookalike_entries`, for `flicker.lookalikes`).

How. The first audio stream is decoded to mono at `FS` (ffmpeg), at most `MAX_S` of it. Each `WIN_S` window
(`HOP_S` apart) is a Hann periodogram; a bin's *excess* is its level in dB over the running median of the
`MEDIAN_HZ` either side, so a tone stands out of whatever noise is under it. A **line** is a peak at least
`EXCESS_DB` over that median, in `BAND`, found in at least `STEADY_SHARE` of the windows at the same frequency
(within `SAME_HZ`), its frequency refined between bins. The lines are then explained, in order, by
the codec's frame families, the video's frame rate, an aircraft bus, the mains, and any other harmonic series
(`families`). A steady series is read against the known airframes of `PROPELLERS` (`propeller`), with the
airframe's second tone looked for in every window where it should be (`companion`); a lone line near an airframe's
blade-pass is read as it only with that second tone, and is otherwise "near", no reading.

What it cannot do, and the traps:
- **The blade count is not in the series.** Four blades at R and six at 2R/3 make the same lines. The reading
  rests on the shaft speed being known -- in flight, a governed propeller's -- and `propeller` gives every
  (blades, rpm) pair the series allows beside any airframe it matches.
- **The ground is different.** On the ground a propeller turns slower: C-130Js loading and taxiing hummed at
  65.75-75 Hz on the DVIDS controls, near a T56's 68 in flight. A match says "in flight"; a phase of flight from
  elsewhere (the report, the pictures) has to say the aircraft was airborne.
- **Silence is an answer.** Most PURSUE sensor videos carry a sound track that is digital silence; that is NO
  POWER, not "nothing heard".
- **A phone's own processing** (gain control, noise suppression) changes levels, not frequencies; an absent line
  is weak evidence.
- The resolution is 1/`WIN_S`; a record shorter than two windows is read as three half-length windows, at a
  coarser resolution, and says so.
"""
import json
import subprocess
from fractions import Fraction
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy import ndimage

from .report import Found

FS = 16000            # Hz: the analysis rate; every line looked for is under BAND's top
WIN_S = 4.0           # s: one window (0.25-Hz bins)
HOP_S = 2.0           # s: windows start this far apart
MIN_S = 1.0           # s: shorter than this is not read
MAX_S = 900.0         # s: at most this much of a long recording is read (from --from)
SILENT_DBFS = -90.0   # a track whose loudest sample is under this is digital silence
BAND = (12.0, 4000.0)  # Hz: lines are looked for here (from 12 Hz: an H-60's main rotor beats at 17.2)
MEDIAN_HZ = 25.0      # Hz either side: the running median a bin's excess is measured over
EXCESS_DB = 12.0      # dB over that median: a peak
SAME_HZ = 0.6         # Hz: peaks of different windows this close are one line
STEADY_SHARE = 0.5    # a line is in at least this share of the windows
STEADY_SD = 0.002     # its frequency's spread across windows is at most this share of it (or 0.15 Hz) to be steady
CODEC_TOL = 0.3       # Hz: a codec's frame products are exact
CODEC_FRAMES = (("AAC", 1024), ("MP3", 1152))
CODEC_RATES = (48000, 44100, 32000, 24000, 22050, 16000)
CODEC_K = 64          # up to this multiple of a frame rate
CODEC_MIN = 3         # members a codec family needs, CODEC_LOW_N of them at k <= CODEC_LOW (chance coincidences on a
CODEC_LOW, CODEC_LOW_N = 8, 2   # record with many lines -- PR113's 79 -- otherwise make families of two)
FRAME_TOL = 0.1       # Hz: a line at k x the video's frame rate (the family needs k = 1: 2x and 6x 29.97 are where
                      # 60-Hz hum sits, as on the Gemini 7 audio)
FRAME_K = 140         # the frame rate's comb is claimed to here (4.2 kHz at 29.97): an NTSC chain's sync buzz runs high
                      # (AARO's 2004 FLIR video: 59.94-Hz harmonics to the 39th, 2.34 kHz)
FRAME_REL = 5e-5      # past k = 8, a comb harmonic sits within this share of k x the fitted frame rate (or FRAME_TOL / 2)
FIELD = 60 / 1.001    # Hz: NTSC's field rate, 59.94 -- 0.06 Hz from 60-Hz mains, so one line in a 4-s window (bins 0.25 Hz)
CROSS_A, CROSS_B = 8, 2   # an earlier encode's frame products mixed with this one's: a fr1 +- b fr2, a <= CROSS_A,
                          # b <= CROSS_B, needing its own b fr2 heard and CODEC_MIN lines in all (PR36: 187.5 - 86.13 = 101.37)
SIDEBAND_TOL = 0.15   # Hz: two lines symmetric about a supply's harmonic within this are its sidebands ...
SIDEBAND_HZ = (0.5, 20.0)  # ... at this offset: the hum modulated (Apollo 14's tapes: 60.15 +- 7.5 Hz)
HUM_DB = 15.0         # a line within 1 % of 50 or 60 Hz this strong that wanders is mains hum through a transport
SHIFTED = 0.06        # a steady series within this share of 50 or 60 Hz (but outside 1 %) may be mains retimed
SERIES_TOL = 0.003    # a series member sits within this share of k F (and at least 0.25 Hz)
SERIES_K = 16
SERIES_MIN = 3        # members to call a series, among its first SERIES_LOW harmonics, one at k <= 2
SERIES_LOW = 6
SUPPLY_TOL = 0.0005   # a supply's harmonic sits within this share of k f0 (and at least SUPPLY_FLOOR); a supply is exact,
SUPPLY_FLOOR = 0.1    # Hz; and wider let chance lines in among many (FLIR's 103: 60.25 x 8 beside 60.32 x 3, 5, 9)
SUPPLY_SD = 0.0015    # ... and holds its frequency across windows to this share of it (or 0.06 Hz): a supply is steady
                      # (PR113's mains: 0.01 % at 1,140 Hz); PR107's wandering lines near 100, 200, 300 Hz are not mains
MAINS = ((50.0, 40), (60.0, 40))            # nominal, highest harmonic looked for
SUPPLY_LOW, SUPPLY_LOW_N_K = 3, 10            # a supply needs a member at k <= 3 and two at k <= 10
MAINS_STRAY = 0.002   # a grid strays at most about this share of its nominal frequency (taken wide)
FIELD_RATE_IF = 0.012  # Hz: "mains" this close to 59.94 may be an NTSC chain's field rate instead (no video to say which)
GRID_REL = 0.0008     # a grid holds its nominal to well within this (US interconnections count excursions over 36-90 mHz
                      # as events); mains further off is a local supply -- a generator, an inverter, a ship's service
                      # power (60 Hz +-3 %) -- or a retimed copy (FLIR's odd-harmonic 60.32 Hz)
BUS = (400.0, 10)
BUS_RANGE = (393.0, 407.0)                  # MIL-STD-704 normal steady state (from memory)
PULLDOWN = 400 / 1.001  # Hz: a 400-Hz supply heard 0.1 % slow, as an NTSC pull-down (30 -> 29.97) slows a sound track
PULLDOWN_PPM = 50.0     # a bus this close to PULLDOWN is either a supply running there or 400.000 pulled down: either way
                        # said (PR106, PR107, PR111 and PR113 sit within 30 ppm of it)
REFINE_S = 30.0       # s: a piece read at once, for the clocks' fine frequencies (0.033-Hz resolution; longer, a supply's
                      # own wander smears it: Puerto Rico's bus drifts 398.415 -> 398.380 Hz in 2 minutes)
REFINE_PIECES = 3     # pieces, spread over the record; a supply counts where it is found in most of them
REFINE_DB = 10.0      # dB over the zoomed band's median: a line in the full-record spectrum
REFINE_TOP = 4        # peaks kept a harmonic in the zoomed band
REFINE_SAME = 0.02    # Hz: per-harmonic estimates (hz / k) this close to a group's median are one supply (or 1/T on a short
                      # record); two supplies 0.2 Hz apart -- PR107's 399.60 and 399.82 -- are one line in a 4-s window
REFINE_MIN_K = 3      # harmonics a supply found in the full record needs
MATCH = 0.015         # a series within this share of an airframe's blade-pass in flight matches it
COMPANION_TOL = 0.0015  # an airframe's second tone sits within this share of its ratio x the blade-pass heard ...
                        # (measured: within 0.05 %; a wider search lets noise peaks in on short records)
COMPANION_DB = 8.0     # ... as a peak this far over the local median (it is looked for where it should be, so lower
COMPANION_SHARE = 0.3  # than a line's EXCESS_DB) in at least this share of the windows,
COMPANION_SPREAD, COMPANION_SPREAD_HZ = 0.0015, 0.3  # its frequency spread across them at most 0.15 % (or 0.3 Hz):
                      # real second tones spread 0.02-0.11 %, noise in a +-0.4 % band about 0.23 % (1.3 Hz at 550)
SINGLE_MATCH = 0.0075  # a lone line (no harmonics) within this share of an airframe's blade-pass, AND its second tone
                       # heard, is read as that airframe; without the tone it is only near (PR113's 68.92, PR39's 101.37)
BLADES = (2, 3, 4, 5, 6, 8)

# Known airframes: what their propellers sound like. Each entry carries its sources; add one only with them.
PROPELLERS = [
    dict(name="C-130 with T56 engines and four-bladed 54H60 propellers (C-130B/E/H, AC-130H/U/W, MC/HC/EC-130, P-3)",
         plain=("a C-130 with four-bladed propellers", "T56 engines: the older C-130s, and the AC-130H, U and W gunships"),
         blades=4, rpm=1020.0,
         measured_flight_hz=(68.00, 68.25), measured_ground_hz=(66.25, 70.75),
         companion=dict(ratio=8.129, what="a steady tone at 8.13 x the blade-pass (553 Hz at 68 Hz)",
                        measured="8.127-8.130 in flight on DVIDS 387408/387446 (41 windows each)"),
         sources="AOPA, 'Lockheed Martin C-130H Hercules' (2017): 1,021 rpm; T56 13,820 rpm through 13.54:1. "
                 "Measured on DVIDS 387408/387446 (AFSOC AC-130H/U, 2011): 68.00-68.25 Hz in flight; 66.25-66.75 "
                 "taxiing, 70.25-70.75 at engine start"),
    dict(name="C-130J with AE2100 engines and six-bladed Dowty R391 propellers (C-130J, AC-130J, MC/HC/KC-130J)",
         plain=("a C-130J with six-bladed propellers", "the newer C-130s, and the AC-130J gunship"),
         blades=6, rpm=1020.0,
         measured_flight_hz=(102.0, 102.0), measured_ground_hz=(65.75, 75.0),
         companion=dict(ratio=5.390, what="a steady tone at 5.39 x the blade-pass (550 Hz at 102 Hz)",
                        measured="5.390 in flight on six DVIDS C-130J/AC-130J clips; on the ground it scatters (7.4-8.2)"),
         sources="EASA TCDS P.087 (R391: maximum continuous 1,020.7 rpm); Lockheed Martin Service News v26n3 (one "
                 "1,020-rpm setting in flight but flight idle). Measured on DVIDS 826283 (AC-130J live fire) and "
                 "1012667 (C-130J cockpit): 102.0 Hz in flight; 65.75-75 Hz loading and taxiing, 102 on the "
                 "takeoff roll"),
    dict(name="H-60 helicopter with a four-bladed main rotor at 258 rpm (UH-60, MH-60, HH-60)",
         plain=("an H-60 helicopter", "the Black Hawk and its kin"),
         blades=4, rpm=258.0, kind="rotor",
         measured_flight_hz=(17.20, 17.28), measured_ground_hz=(17.20, 17.28),
         companion=dict(ratio=4.611, what="the tail rotor's blade-pass at 4.61 x the main rotor's (79.5 Hz at 17.2 Hz)",
                        measured="4.605-4.614 on five DVIDS UH-60 clips (878819, 694543, 833893, 911411, 920268)"),
         sources="Main rotor 258 rpm, four-bladed main and tail rotors (YUH-60A specification, as given by This Day in "
                 "Aviation). Measured on DVIDS UH-60 clips: main rotor blade-pass 17.20-17.28 Hz (its x4, 68.8-69.1 Hz, "
                 "is near a T56's 68), tail rotor 79.2-79.7 Hz; the rotor runs at its governed speed on the ground too"),
]
# Not in the table, for want of a sourced propeller speed: the MQ-9. Heard from the ground in flight (DVIDS 776121) its
# blade-pass sweeps 67-76 Hz with Doppler, over a T56's 68, but its second tone sits at an integer 9.00 x (611 Hz at 68)
# -- a ratio Doppler cannot move. Hence the rule that a blade-pass alone identifies nothing.


# ---- reading the file ---------------------------------------------------------------------------------
def probe(path):
    """The file's streams: {audio: [{codec, sample_rate, channels}], fps: Fraction or None, duration_s}."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
                       capture_output=True, encoding="utf-8", errors="replace")
    d = json.loads(r.stdout or "{}") if r.returncode == 0 else {}
    if not d:
        raise FileNotFoundError(f"{Path(path).name}: ffprobe cannot read it")
    audio = [dict(codec=s.get("codec_name"), sample_rate=int(s.get("sample_rate") or 0), channels=s.get("channels"))
             for s in d.get("streams", []) if s.get("codec_type") == "audio"]
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"
              and s.get("disposition", {}).get("attached_pic", 0) == 0), None)
    fps = Fraction(v["r_frame_rate"]) if v and v.get("r_frame_rate") not in (None, "0/0") else None
    return dict(audio=audio, fps=fps, duration_s=float(d.get("format", {}).get("duration") or 0))


def decode(path, t0=0.0, seconds=None, fs=FS):
    """The first audio stream, mono, at fs, from t0 for at most `seconds`: float32 samples."""
    cmd = ["ffmpeg", "-nostdin", "-v", "error"]
    if t0:
        cmd += ["-ss", f"{t0:.3f}"]
    cmd += ["-i", str(path)]
    if seconds:
        cmd += ["-t", f"{seconds:.3f}"]
    cmd += ["-map", "0:a:0", "-ac", "1", "-ar", str(fs), "-f", "f32le", "-"]
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode:
        raise FileNotFoundError(f"{Path(path).name}: ffmpeg could not decode its sound: "
                                f"{p.stderr.decode(errors='replace').strip().splitlines()[-1:]}")
    return np.frombuffer(p.stdout, dtype="<f4")


def loudness(x):
    """(peak dBFS, mean (RMS) dBFS); -inf for exact zeros."""
    x = np.asarray(x, float)
    peak, rms = (float(np.max(np.abs(x))), float(np.sqrt(np.mean(x ** 2)))) if len(x) else (0.0, 0.0)
    db = lambda v: 20 * np.log10(v) if v > 0 else float("-inf")
    return db(peak), db(rms)


# ---- the spectrum and its lines -----------------------------------------------------------------------
def windows(n, fs=FS, win_s=WIN_S, hop_s=HOP_S):
    """(start samples, window length). A record shorter than two windows is read as three half-length windows,
    half overlapping (so a tone's steadiness can still be judged, at a coarser resolution); one shorter than two
    seconds as one window."""
    w = int(round(win_s * fs))
    if n < 2 * w:
        if n < 2 * fs:
            return [0], n
        w = n // 2
        return [0, w // 2, n - w], w
    return list(range(0, n - w + 1, int(round(hop_s * fs)))), w


def excess(seg, fs=FS, top=BAND[1]):
    """(frequencies, the periodogram in dB, its excess in dB over the running median of MEDIAN_HZ either side),
    up to a little past `top`."""
    seg = np.asarray(seg, float)
    n = len(seg)
    P = np.abs(np.fft.rfft((seg - seg.mean()) * np.hanning(n))) ** 2
    f = np.fft.rfftfreq(n, 1 / fs)
    keep = f <= top + 2 * MEDIAN_HZ
    f, P = f[keep], P[keep]
    L = 10 * np.log10(P + 1e-30)
    size = max(3, int(round(2 * MEDIAN_HZ / (f[1] - f[0]))) | 1)
    return f, L, L - ndimage.median_filter(L, size=size, mode="nearest")


def _peaks(f, L, ex, band=BAND, above=EXCESS_DB):
    """[(hz refined between bins, excess dB)] of the local maxima standing `above` in `band`."""
    df = f[1] - f[0]
    half = max(1, int(round(0.5 / df)))        # a Hann window's main lobe: wider, and a weaker tone 1 Hz from a strong
                                               # one is lost (PR36's codec line at 101.37 hid a tone at 102.3)
    out = []
    for i in np.flatnonzero((f >= band[0]) & (f <= band[1]) & (ex > above)):
        lo, hi = max(0, i - half), min(len(ex), i + half + 1)
        if ex[i] < ex[lo:hi].max() or i == 0 or i == len(L) - 1:
            continue
        a, b, c = L[i - 1], L[i], L[i + 1]
        d = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
        out.append((float(f[i] + np.clip(d, -0.5, 0.5) * df), float(ex[i])))
    return out


def lines(x, fs=FS, band=BAND, above=EXCESS_DB, win_s=WIN_S, hop_s=HOP_S):
    """The steady tones of a record: ([{hz, hz_sd, excess_db, windows, share, steady}] strongest first, the number of
    windows read, the frequency resolution, and every window's peaks of COMPANION_DB or more as (hz, dB, window) --
    what `companion` looks in). A tone is a peak `above` the local median found at the same frequency (SAME_HZ) in
    STEADY_SHARE of the windows; silent windows are left out."""
    x = np.asarray(x, float)
    starts, w = windows(len(x), fs, win_s, hop_s)
    found, weak, used = [], [], 0
    for k, s in enumerate(starts):
        seg = x[s:s + w]
        if not len(seg) or np.max(np.abs(seg)) < 10 ** (SILENT_DBFS / 20):
            continue
        f, L, ex = excess(seg, fs, band[1])
        pk = [(hz, e, k) for hz, e in _peaks(f, L, ex, band, min(above, COMPANION_DB))]
        weak += pk
        found += [p for p in pk if p[1] > above]
        used += 1
    groups, cur = [], []
    for p in sorted(found):
        if cur and p[0] - cur[-1][0] > SAME_HZ:
            groups.append(cur)
            cur = []
        cur.append(p)
    if cur:
        groups.append(cur)
    out = []
    for g in groups:
        best = {}
        for hz, e, k in g:                        # one peak a window: its strongest
            if k not in best or e > best[k][1]:
                best[k] = (hz, e)
        hzs = np.array([v[0] for v in best.values()])
        exs = np.array([v[1] for v in best.values()])
        share = len(best) / used if used else 0.0
        if used > 1 and share < STEADY_SHARE:
            continue
        hz = float(np.median(hzs))
        sd = float(np.std(hzs)) if len(hzs) > 1 else None
        out.append(dict(hz=round(hz, 3), hz_sd=None if sd is None else round(sd, 3), excess_db=round(float(np.median(exs)), 1),
                        windows=len(best), share=round(share, 2),
                        steady=sd is None or sd <= max(0.15, STEADY_SD * hz)))
    out.sort(key=lambda d: -d["excess_db"])
    return out, used, 1.0 / (min(w, len(x)) / fs) if len(x) else None, weak


# ---- what the lines are -------------------------------------------------------------------------------
def _fit_f0(members):
    """The fundamental that fits [(k, hz, weight)] best: sum k hz w / sum k^2 w."""
    num = sum(k * hz * w for k, hz, w in members)
    den = sum(k * k * w for k, _, w in members)
    return num / den


def _held(L, rel=SUPPLY_SD):
    """A line steady enough to be a supply's: its spread across windows (None when read in one) within rel."""
    return L["hz_sd"] is None or L["hz_sd"] <= max(0.06, rel * L["hz"])


def _supply(ls, nominal, kmax, lo, hi, tol=SUPPLY_TOL):
    """The best harmonic series on a fundamental in [lo, hi] (a supply's): (f0, [(k, line)]) or None. Candidates
    are each line over k; a member is within tol of k f0 and holds its frequency (`_held`)."""
    ls = [L for L in ls if _held(L)]
    best = None
    for L in ls:
        for k in range(1, kmax + 1):
            f0 = L["hz"] / k
            if not lo <= f0 <= hi:
                continue
            byk = {}
            for M in ls:
                j = int(round(M["hz"] / f0))
                if 1 <= j <= kmax and abs(M["hz"] - j * f0) <= max(SUPPLY_FLOOR, tol * M["hz"]):
                    if j not in byk or M["excess_db"] > byk[j]["excess_db"]:
                        byk[j] = M                      # one line a harmonic (PR-017: two lines both "x4")
            mem = sorted(byk.items())
            ks = [j for j, _ in mem]
            # a supply is heard low down: a harmonic at k <= SUPPLY_LOW and two at k <= SUPPLY_LOW_N_K, or its
            # fundamental alone (judged by the caller); chance fits among many lines sit high (Puerto Rico's "50.43 Hz
            # mains" at x5, 15, 22, 30, 33; PR-017's at x26, 27)
            ok = ks == [1] or (min(ks or [99]) <= SUPPLY_LOW and sum(k <= SUPPLY_LOW_N_K for k in ks) >= 2)
            score = (len(ks), sum(M["excess_db"] for _, M in mem))
            if mem and ok and (best is None or score > best[0]):
                best = (score, f0, mem)
    if best is None:
        return None
    _, f0, mem = best
    f0 = _fit_f0([(j, M["hz"], M["excess_db"]) for j, M in mem])
    return f0, sorted(mem, key=lambda m: m[0])


def _series(ls, tol=SERIES_TOL, kmax=SERIES_K, nmin=SERIES_MIN, lo=15.0, hi=500.0):
    """Harmonic series among `ls`, greedily: [(F, [(k, line)])], each the fundamental explaining most lines, the
    largest such F where several explain the same ones (so 67.75 and not 33.875), and needing a member at k <= 2."""
    left = list(ls)
    out = []
    while len(left) >= nmin:
        best = None
        for L in left:
            for k in range(1, 5):
                F = L["hz"] / k
                if not lo <= F <= hi:
                    continue
                byk = {}
                for M in left:
                    j = int(round(M["hz"] / F))
                    if 1 <= j <= kmax and abs(M["hz"] - j * F) <= max(0.25, tol * M["hz"]):
                        if j not in byk or M["excess_db"] > byk[j]["excess_db"]:
                            byk[j] = M                  # one line a harmonic: its strongest
                mem = sorted(byk.items())
                ks = set(byk)
                if len([j for j in ks if j <= SERIES_LOW]) < nmin or min(ks) > 2:
                    continue
                score = (len(ks), F)
                if best is None or score > best[0]:
                    best = (score, F, mem)
        if best is None:
            break
        _, F, mem = best
        F = _fit_f0([(j, M["hz"], M["excess_db"]) for j, M in mem])
        out.append((F, sorted(mem, key=lambda m: m[0])))
        taken = {id(M) for _, M in mem}
        left = [M for M in left if id(M) not in taken]
    return out


def _rates(fps):
    """The frame rates a video tagged `fps` may really run at: the tag, and its NTSC twin (30 <-> 30/1.001)."""
    out = [fps]
    n = round(fps)
    if abs(fps - n) < 0.001 and n:
        out.append(n / 1.001)
    elif abs(fps * 1.001 - round(fps * 1.001)) < 0.001:
        out.append(round(fps * 1.001))
    return out


def _frame_comb(ls, fps):
    """The video's frame rate heard in its sound: a line at the rate itself (k = 1), its harmonics, and the comb they
    make to FRAME_K, fitted from the lines themselves (a tag of 30 on an NTSC chain's 29.97: FLIR, PR113). Its 2nd
    harmonic is the NTSC field rate, 59.94, which a 4-s window cannot tell from 60-Hz mains. {fps, hz, ntsc, field_hz,
    members} or None."""
    free = [L for L in ls if L["is"] is None]
    best = None
    for rate in _rates(fps):
        k1 = [L for L in free if abs(L["hz"] - rate) <= FRAME_TOL]
        if not k1:
            continue
        L1 = max(k1, key=lambda L: L["excess_db"])
        fr, mem = L1["hz"], {1: L1}
        for kmax, tol in ((4, None), (8, None), (FRAME_K, FRAME_REL)):
            for L in free:
                j = int(round(L["hz"] / fr))
                if not 1 <= j <= kmax or (j in mem and mem[j] is not L and mem[j]["excess_db"] >= L["excess_db"]):
                    continue
                lim = FRAME_TOL if tol is None or j <= 8 else max(FRAME_TOL / 2, tol * L["hz"])
                if abs(L["hz"] - j * fr) <= lim and (j <= 8 or _held(L)):
                    mem[j] = L
            fr = _fit_f0([(j, L["hz"], L["excess_db"]) for j, L in mem.items()])
        if best is None or len(mem) > len(best[1]):
            best = (fr, mem)
    if best is None:
        return None
    fr, mem = best
    ntsc = abs(fr * 1.001 - round(fr * 1.001)) < abs(fr - round(fr))
    return dict(fps=round(fps, 4), hz=round(fr, 4), ntsc=ntsc, field_hz=round(2 * fr, 4) if 2 in mem else None,
                members=[dict(k=k, hz=L["hz"]) for k, L in sorted(mem.items())], _lines=list(mem.values()))


def families(ls, sample_rate=None, fps=None, peaks=(), nwin=0):
    """Explain the lines, in order: the codec's frame families, the video's frame rate, an aircraft's 400-Hz bus,
    the mains, then any other harmonic series. Each line gets `is` (the first family it belongs to) and `also`
    (others it fits). Returns {codec, frame, bus, mains, series} and the lines, labelled."""
    for L in ls:
        L["is"], L["also"] = None, []

    def claim(L, label):
        if L["is"] is None:
            L["is"] = label
        elif label != L["is"] and label not in L["also"]:
            L["also"].append(label)

    fams = dict(codec=[], frame=None, bus=None, mains=None, series=[])
    cands = []
    for codec, frame in CODEC_FRAMES:
        for rate in CODEC_RATES:
            fr = rate / frame
            mem = [(int(round(L["hz"] / fr)), L) for L in ls
                   if 1 <= round(L["hz"] / fr) <= CODEC_K and abs(L["hz"] - round(L["hz"] / fr) * fr) <= CODEC_TOL]
            cands.append((len(mem), rate == sample_rate, codec, rate, fr, mem))
    taken = set()
    for _, own, codec, rate, fr, mem in sorted(cands, key=lambda c: (c[0], c[1]), reverse=True):
        mem = [(k, L) for k, L in mem if id(L) not in taken]       # a sub-rate's lines are a stronger family's
        if len(mem) < CODEC_MIN or sum(k <= CODEC_LOW for k, _ in mem) < CODEC_LOW_N:
            continue
        label = f"{codec} frames at {rate / 1000:g} kHz"
        fams["codec"].append(dict(what=label, frame_hz=round(fr, 4), sample_rate=rate, this_files_rate=own,
                                  members=[dict(k=k, hz=L["hz"]) for k, L in sorted(mem, key=lambda m: m[0])]))
        for _, L in mem:
            claim(L, label)
            taken.add(id(L))
    fams["codec_cross"] = []
    for c in list(fams["codec"]):
        fr1 = c["frame_hz"]
        for codec, frame in CODEC_FRAMES:
            for rate in CODEC_RATES:
                fr2 = rate / frame
                if abs(fr2 - fr1) < 0.5 or any(abs(q["frame_hz"] - fr2) < 0.01 for q in fams["codec"]):
                    continue
                mem = []
                for L in ls:
                    if L["is"] is not None:
                        continue
                    for a in range(0, CROSS_A + 1):
                        hit = next(((a, b, sg) for b in range(1, CROSS_B + 1) for sg in (1, -1)
                                    if abs(L["hz"] - (a * fr1 + sg * b * fr2)) <= CODEC_TOL), None)
                        if hit:
                            mem.append((hit, L))
                            break
                own = [m for m in mem if m[0][0] == 0]
                if own and len(mem) >= CODEC_MIN:
                    label = f"{codec} frames at {rate / 1000:g} kHz, an earlier encode, mixed with {c['what']}"
                    fams["codec_cross"].append(dict(what=label, frame_hz=round(fr2, 4), sample_rate=rate, with_hz=fr1,
                                                    members=[dict(a=a, b=sg * b, hz=L["hz"]) for (a, b, sg), L in mem]))
                    for _, L in mem:
                        claim(L, label)
    if fps:
        comb = _frame_comb(ls, float(fps))
        if comb:
            for L in comb.pop("_lines"):
                claim(L, "the video's frame rate" + (" (its field rate, 59.94 Hz: video sync buzz, not mains)"
                                                    if comb["ntsc"] and abs(L["hz"] - 2 * comb["hz"]) < FRAME_TOL else ""))
            fams["frame"] = comb
    free = [L for L in ls if L["is"] is None]
    nominal, kmax = BUS
    bus_ok = lambda got: got and (len(got[1]) >= 2 or (got[1][0][0] == 1 and got[1][0][1]["excess_db"] >= 20))
    got = _supply(free, nominal, kmax, *BUS_RANGE)
    fams["bus_possible"] = None
    if bus_ok(got):
        f0, mem = got
        fams["bus"] = dict(f0_hz=round(f0, 3), members=[dict(k=k, hz=L["hz"]) for k, L in mem],
                           speed=round(f0 / nominal, 5),
                           speed_range=(round(f0 / BUS_RANGE[1], 4), round(f0 / BUS_RANGE[0], 4)))
        for _, L in mem:
            claim(L, "an aircraft's 400-Hz power")
    elif fams["frame"]:
        # a line on two combs is evidence for neither (sonar's harmonic line association): 3 x 400/1.001 = 20 x 59.94,
        # so where the video's field comb is heard a bus's 3rd, 6th and 9th harmonics are its lines too (PR113, FLIR).
        # A bus that stands only with them is possible, not shown.
        comb_ids = {id(L) for L in ls if L["is"] == "the video's frame rate" or str(L["is"]).startswith("the video's frame rate")}
        both = _supply([L for L in ls if L["is"] is None or id(L) in comb_ids], nominal, kmax, *BUS_RANGE)
        if bus_ok(both):
            f0, mem = both
            fams["bus_possible"] = dict(f0_hz=round(f0, 3), members=[dict(k=k, hz=L["hz"], shared=id(L) in comb_ids) for k, L in mem],
                                        why="its harmonics at x" + ", x".join(str(k) for k, L in mem if id(L) in comb_ids)
                                            + " are also the video's frame comb's, and those left do not make a supply")
            for k, L in mem:
                if id(L) not in comb_ids:
                    claim(L, "possibly an aircraft's 400-Hz power (x%d)" % k)
    free = [L for L in ls if L["is"] is None]
    best = None
    for nominal, kmax in MAINS:
        got = _supply(free, nominal, kmax, nominal * 0.99, nominal * 1.01)
        if got and len(got[1]) >= 2 and (best is None or len(got[1]) > len(best[1][1])):
            best = (nominal, got)
    if best and fams["frame"] and abs(best[1][0] - 2 * fams["frame"]["hz"]) <= 0.03:
        best = None                                 # the video's field rate, whose comb the frame family already holds
    if best:
        nominal, (f0, mem) = best
        fams["mains"] = dict(nominal_hz=nominal, f0_hz=round(f0, 3), members=[dict(k=k, hz=L["hz"]) for k, L in mem],
                             speed=round(f0 / nominal, 5),
                             speed_range=(round(f0 / (nominal * (1 + MAINS_STRAY)), 4),
                                          round(f0 / (nominal * (1 - MAINS_STRAY)), 4)),
                             field_rate_if=(nominal == 60.0 and abs(f0 - FIELD) <= FIELD_RATE_IF),
                             grid=abs(f0 / nominal - 1) <= GRID_REL)
        for _, L in mem:
            claim(L, f"{nominal:g}-Hz mains")
    # sidebands: two lines symmetric about a supply's harmonic are the hum modulated (a tape transport's flutter),
    # not two machines -- the Apollo 14 debriefing tapes' 52.6 and 67.7 Hz about 60.15
    fams["sidebands"] = []
    sups = [(fams.get("mains"), "the mains"), (fams.get("bus"), "the 400-Hz power")]
    # every hum's fundamental, not only the mains family's: a record can hold two (Mercury-Redstone 4's 60.13 and
    # 60.78), and a fundamental alone is enough to look for its sidebands
    for L in ls:
        if any(abs(L["hz"] - n) <= 0.01 * n for n, _ in MAINS) and L["excess_db"] >= HUM_DB \
                and not (fams.get("mains") and abs(L["hz"] - fams["mains"]["f0_hz"]) < 0.05):
            sups.append((dict(f0_hz=L["hz"]), "the mains hum"))
    for sup, name in sups:
        if not sup:
            continue
        f0 = sup["f0_hz"]
        for k in range(1, 9):
            h = k * f0
            for L in [L for L in ls if L["is"] is None]:
                d = abs(L["hz"] - h)
                if not SIDEBAND_HZ[0] <= d <= SIDEBAND_HZ[1] or L["is"] is not None:
                    continue
                mirror = 2 * h - L["hz"]
                M = next((M for M in ls if M is not L and abs(M["hz"] - mirror) <= SIDEBAND_TOL), None)
                # the mirror heard as a line, or in COMPANION_SHARE of the windows among the weaker peaks (one sideband
                # can be a line while its mirror is not, and the line alone would then be read as something else)
                share = len({w for hz, e, w in peaks if abs(hz - mirror) <= max(SIDEBAND_TOL, 0.25)}) / nwin if nwin else 0
                if M is None and share < COMPANION_SHARE:
                    continue
                lo, hi = sorted((L["hz"], mirror if M is None else M["hz"]))
                fams["sidebands"].append(dict(of=name, k=k, harmonic_hz=round(h, 3), offset_hz=round(d, 2), hz=(lo, hi),
                                              mirror_as="line" if M is not None else f"peaks in {100 * share:.0f}% of windows"))
                for X in (L, M):
                    if X is not None:
                        claim(X, f"a sideband of {name} (x{k}), at -+{d:.2f} Hz: the hum modulated")
    # mains hum carried through a tape or disc transport: near 50 or 60 Hz, strong, but wandering -- no clock
    fams["hum"] = None
    if not fams.get("mains"):
        for nominal, _ in MAINS:
            cand = [L for L in ls if L["is"] is None and abs(L["hz"] - nominal) <= 0.01 * nominal
                    and L["excess_db"] >= HUM_DB and not _held(L)]
            if cand:
                L = max(cand, key=lambda L: L["excess_db"])
                mem = [L] + [M for M in ls if M["is"] is None and M is not L and 2 <= round(M["hz"] / L["hz"]) <= 5
                             and abs(M["hz"] - round(M["hz"] / L["hz"]) * L["hz"]) <= max(1.0, 0.01 * M["hz"])]
                fams["hum"] = dict(nominal_hz=nominal, hz=L["hz"], hz_sd=L["hz_sd"], members=[M["hz"] for M in mem])
                for M in mem:
                    claim(M, f"{nominal:g}-Hz hum through a transport (it wanders)")
                break
    free = [L for L in ls if L["is"] is None]
    for F, mem in _series(free):
        # steady: its lowest member, and at least half of them (a rotor's high harmonics drift as it manoeuvres;
        # PR107's wandering 99.6 Hz is the lowest member, and wanders)
        steady = mem[0][1]["steady"] and sum(L["steady"] for _, L in mem) >= len(mem) / 2
        ks = [k for k, _ in mem]
        odd = len(ks) >= 3 and 1 in ks and all(k % 2 for k in ks)        # a square or switched wave, not a rotor
        near_mains = next((n for n, _ in MAINS if 0.01 * n < abs(F - n) <= SHIFTED * n), None)
        fams["series"].append(dict(f0_hz=round(F, 3), members=[dict(k=k, hz=L["hz"], excess_db=L["excess_db"]) for k, L in mem],
                                   steady=steady, odd_only=odd,
                                   mains_if=None if not (steady and near_mains) else dict(nominal_hz=near_mains, speed=round(F / near_mains, 4)),
                                   propeller=propeller(F, peaks, nwin) if steady and not odd else None))
        for _, L in mem:
            claim(L, f"a harmonic series on {F:.2f} Hz")
    # a known airframe's blade-pass heard as a single line, its harmonics too weak to make a series (an AC-130J in
    # flight: 102 Hz alone in most windows)
    matched = {m["airframe"] for s in fams["series"] if s["propeller"] for m in s["propeller"]["matches_in_flight"]
               if m.get("identified")}
    fams["single"], fams["near"] = [], []
    for a in PROPELLERS:
        bpf = a["blades"] * a["rpm"] / 60
        cand = [L for L in ls if a["name"] not in matched and L["steady"] and L["is"] is None
                and abs(L["hz"] - bpf) <= MATCH * bpf]
        if not cand:
            continue
        L = max(cand, key=lambda L: L["excess_db"])
        comp = companion(a, L["hz"], peaks, nwin)
        entry = dict(airframe=a["name"], hz=L["hz"], blade_pass_hz=round(bpf, 2), off=round((L["hz"] - bpf) / bpf, 4),
                     companion=comp, within_ground_range_of=propeller(L["hz"])["within_ground_range_of"])
        short = a["name"].split(" with ")[0]
        if abs(entry["off"]) <= SINGLE_MATCH and comp and comp["found_hz"]:
            fams["single"].append(entry)
            claim(L, f"the blade-pass of {short}")
            for M in ls:                            # its harmonics, too few or too weak to have made a series
                j = int(round(M["hz"] / L["hz"]))
                if M is not L and 2 <= j <= SERIES_LOW and abs(M["hz"] - j * L["hz"]) <= max(0.25, SERIES_TOL * M["hz"]):
                    claim(M, f"the blade-pass of {short} (x{j})")
        else:
            fams["near"].append(entry)
    # an airframe's second tone, once heard, is that and not an unexplained line
    for m in [m for s in fams["series"] if s["propeller"] for m in s["propeller"]["matches_in_flight"]
              if m.get("identified")] + fams["single"]:
        c = m.get("companion")
        if c and c["found_hz"]:
            for L in ls:
                if abs(L["hz"] - c["found_hz"]) <= max(0.5, 0.003 * L["hz"]):
                    claim(L, f"the second tone of {m['airframe'].split(' with ')[0]}")
    return fams, ls


# ---- the clocks again, at full resolution ---------------------------------------------------------------
def _zoom(xw, fs, lo, hi, df):
    """(frequencies, dB) of the windowed record `xw` between lo and hi, every df Hz (a chirp-z zoom of its DFT)."""
    from scipy.signal import zoom_fft
    m = max(16, int(np.ceil((hi - lo) / df)) + 1)
    Z = zoom_fft(xw, [lo, hi], m=m, fs=fs, endpoint=True)
    return np.linspace(lo, hi, m), 10 * np.log10(np.abs(Z) ** 2 + 1e-30)


def _zoom_peaks(f, L, top=REFINE_TOP, above=REFINE_DB, sep=0.0):
    """[(hz, dB over the band's median)] of the band's strongest local maxima, `sep` Hz apart at least."""
    med = np.median(L)
    cand = []
    for i in np.flatnonzero((L[1:-1] >= L[:-2]) & (L[1:-1] > L[2:]) & (L[1:-1] - med >= above)) + 1:
        a, b, c = L[i - 1], L[i], L[i + 1]
        d = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
        cand.append((float(f[i] + np.clip(d, -0.5, 0.5) * (f[1] - f[0])), float(L[i] - med)))
    keep = []
    for p in sorted(cand, key=lambda p: -p[1]):
        if all(abs(p[0] - q[0]) > sep for q in keep):
            keep.append(p)
        if len(keep) >= top:
            break
    return keep


def _supplies(xw, fs, T, lo, hi, kmax, on_comb=lambda hz: False, min_k=REFINE_MIN_K):
    """Supplies whose fundamental lies in [lo, hi], from the whole record: each harmonic k's band [k lo, k hi] zoomed,
    its strongest peaks divided by k, and those per-harmonic values grouped (REFINE_SAME); a group needs min_k
    harmonics, none of them on another family's comb (`on_comb`). Strongest group first:
    [{f0_hz, ks, sd_hz, db}]."""
    res = 1.0 / T
    pad = max(1.0, 10 * res)              # a band wide enough that its median is the noise, not the line's own lobe
    est = []
    for k in range(1, kmax + 1):
        f, L = _zoom(xw, fs, k * lo - pad, k * hi + pad, res / 4)
        for hz, db in _zoom_peaks(f, L, sep=2 * res):
            if lo <= hz / k <= hi and not on_comb(hz):
                est.append((hz / k, k, db))
    est.sort()
    same = max(REFINE_SAME, res)
    groups = []
    for e in est:                         # against each group's median, so near values do not chain two supplies into one
        g = next((g for g in groups if abs(e[0] - np.median([q[0] for q in g])) <= same), None)
        if g is None:
            groups.append([e])
        else:
            g.append(e)
    out = []
    for g in groups:
        byk = {}
        for v, k, db in g:
            if k not in byk or db > byk[k][1]:
                byk[k] = (v, db)
        if len(byk) < min_k or all(k % 2 == 0 for k in byk):
            continue                      # even harmonics only: a family at twice the frequency, not this one's
        vals = np.array([v for v, _ in byk.values()])
        # inverse variance: a harmonic's estimate of the fundamental has variance ~ 1 / (k^2 SNR), so a strong line
        # outweighs a noise peak that happened to fall in the group at a high k
        w = np.array([k * k * 10 ** (db / 10) for k, (_, db) in byk.items()])
        out.append(dict(f0_hz=round(float(np.sum(vals * w) / np.sum(w)), 4), ks=sorted(byk),
                        sd_hz=round(float(np.std(vals)), 4), db=round(float(np.mean([d for _, d in byk.values()])), 1)))
    return sorted(out, key=lambda d: (-len(d["ks"]), -d["db"]))


def _pieces(x, fs, piece_s, n_max):
    """Windowed pieces of the record (Hann), up to n_max of piece_s seconds spread over it; [(xw, T)]."""
    n = len(x)
    L = min(n, int(piece_s * fs))
    k = 1 if n < 1.5 * L else min(n_max, max(1, int(n // L)))
    starts = np.linspace(0, n - L, k).astype(int) if k > 1 else [max(0, (n - L) // 2)]
    out = []
    for s0 in starts:
        seg = x[s0:s0 + L]
        if np.max(np.abs(seg)) < 10 ** (SILENT_DBFS / 20):
            continue
        out.append(((seg - seg.mean()) * np.hanning(L), L / fs))
    return out


def _combined(per_piece, same):
    """Supplies found piece by piece, [[{f0_hz, ks, db}]], combined: those found in most pieces, each with its median
    f0 and the harmonics heard in any. Most harmonics first."""
    allsup = [(d, i) for i, sups in enumerate(per_piece) for d in sups]
    groups = []
    for d, i in sorted(allsup, key=lambda q: q[0]["f0_hz"]):
        g = next((g for g in groups if abs(d["f0_hz"] - np.median([q[0]["f0_hz"] for q in g])) <= same), None)
        (groups.append([(d, i)]) if g is None else g.append((d, i)))
    need = max(1, (len(per_piece) + 1) // 2)
    out = []
    for g in groups:
        if len({i for _, i in g}) < need:
            continue
        f0s = [d["f0_hz"] for d, _ in g]
        out.append(dict(f0_hz=round(float(np.median(f0s)), 4), ks=sorted({k for d, _ in g for k in d["ks"]}),
                        sd_hz=round(float(np.std(f0s)), 4), pieces=len({i for _, i in g}),
                        db=round(float(np.mean([d["db"] for d, _ in g])), 1)))
    return sorted(out, key=lambda d: (-len(d["ks"]), -d["db"]))


def refine(x, fams, fs=FS, piece_s=REFINE_S, n_pieces=REFINE_PIECES):
    """The clocks again, at full resolution, where a 4-s window's 0.25-Hz bins blend lines: the frame rate's field line
    apart from 60-Hz mains (59.94 against 60.00), and one 400-Hz supply apart from two (PR107's 399.60 and 399.82;
    FLIR's 399.10 and 401.27). Read in pieces of piece_s seconds (a supply's own wander smears a longer one), up to
    n_pieces of them, a supply counting where most pieces find it. Adds `refined` to the frame, bus (or bus_possible)
    and mains families and moves their f0 (and speed range) to it; a bus also says how far it sits from 400 and from
    400/1.001 (`pulldown_if`), and names a second supply where there is one. Returns fams."""
    x = np.asarray(x, float)
    pieces = _pieces(x, fs, piece_s, n_pieces)
    if not pieces or pieces[0][1] < 4.0:
        return fams
    T = pieces[0][1]
    same = max(REFINE_SAME, 1.0 / T)
    fr = fams.get("frame")
    if fr:
        got = _combined([[g for g in _supplies(xw, fs, t, fr["hz"] - 0.06, fr["hz"] + 0.06, 8, min_k=2)
                          if abs(g["f0_hz"] - fr["hz"]) <= 0.03] for xw, t in pieces], same / 4)
        if got:
            fr["refined"] = dict(hz=got[0]["f0_hz"], ks=got[0]["ks"], pieces=got[0]["pieces"], resolution_hz=round(1 / T, 4))
            fr["hz"] = got[0]["f0_hz"]
            fr["ntsc"] = abs(fr["hz"] * 1.001 - round(fr["hz"] * 1.001)) < abs(fr["hz"] - round(fr["hz"]))
            if fr.get("field_hz"):
                fr["field_hz"] = round(2 * fr["hz"], 4)
    on_comb = (lambda hz: abs(hz - round(hz / fr["hz"]) * fr["hz"]) <= max(2.0 / T, 5e-5 * hz)) if fr else (lambda hz: False)
    for key in ("bus", "bus_possible"):
        b = fams.get(key)
        if not b:
            continue
        sup = _combined([_supplies(xw, fs, t, BUS_RANGE[0], BUS_RANGE[1], BUS[1], on_comb) for xw, t in pieces], same)
        if not sup:
            continue
        most = len(sup[0]["ks"])
        near = [d for d in sup if len(d["ks"]) >= most - 2]
        main = min(near, key=lambda d: abs(d["f0_hz"] - b["f0_hz"]))   # the supply the 4-s reading heard
        others = [d for d in sup if d is not main and len(d["ks"]) > REFINE_MIN_K]     # a second supply, more surely
        ppm4 = (main["f0_hz"] / BUS[0] - 1) * 1e6
        ppmp = (main["f0_hz"] / PULLDOWN - 1) * 1e6
        b["refined"] = dict(f0_hz=main["f0_hz"], ks=main["ks"], sd_hz=main["sd_hz"], pieces=main["pieces"],
                            resolution_hz=round(1 / T, 4), ppm_from_400=round(ppm4), ppm_from_pulldown=round(ppmp),
                            pulldown_if=abs(ppmp) <= PULLDOWN_PPM, second=others[0] if others else None)
        b["f0_hz_4s"], b["f0_hz"] = b["f0_hz"], main["f0_hz"]
        b["speed"] = round(main["f0_hz"] / BUS[0], 5)
        b["speed_range"] = (round(main["f0_hz"] / BUS_RANGE[1], 4), round(main["f0_hz"] / BUS_RANGE[0], 4))
    m = fams.get("mains")
    if m:
        nom = m["nominal_hz"]
        sup = _combined([_supplies(xw, fs, t, m["f0_hz"] - 0.1, m["f0_hz"] + 0.1, 10, on_comb) for xw, t in pieces], same)
        if sup:
            main = sup[0]
            m["refined"] = dict(f0_hz=main["f0_hz"], ks=main["ks"], sd_hz=main["sd_hz"], pieces=main["pieces"],
                                resolution_hz=round(1 / T, 4))
            m["f0_hz_4s"], m["f0_hz"] = m["f0_hz"], main["f0_hz"]
            m["speed"] = round(main["f0_hz"] / nom, 5)
            m["speed_range"] = (round(main["f0_hz"] / (nom * (1 + MAINS_STRAY)), 4), round(main["f0_hz"] / (nom * (1 - MAINS_STRAY)), 4))
            m["field_rate_if"] = nom == 60.0 and not fr and abs(main["f0_hz"] - FIELD) <= FIELD_RATE_IF
            m["grid"] = abs(main["f0_hz"] / nom - 1) <= GRID_REL
    return fams


def companion(a, F, peaks=(), nwin=0, tol=COMPANION_TOL):
    """An airframe's second tone where its measured ratio to the blade-pass puts it, looked for among every window's
    peaks of COMPANION_DB or more (`peaks`, from `lines`): found where it is in COMPANION_SHARE of the `nwin` windows,
    its median frequency within tol of ratio x F. {what, expected_hz, found_hz, ratio_heard, share, measured}."""
    c = a.get("companion")
    if not c:
        return None
    exp = c["ratio"] * F
    near = {}
    for hz, e, k in peaks:
        if abs(hz - exp) <= max(0.5, COMPANION_TOL * exp) and (k not in near or e > near[k][1]):
            near[k] = (hz, e)
    share = len(near) / nwin if nwin else 0.0
    hzs = np.array([v[0] for v in near.values()])
    hz = float(np.median(hzs)) if near else None
    spread = float(np.std(hzs)) if len(hzs) > 1 else 0.0
    # a tone holds its frequency from window to window; noise's peaks in the search band scatter across it (pure noise
    # puts an 8-dB peak in a +-0.4 % band in about a quarter of the windows, centred on average)
    # two windows at least (a short record's one noise peak is a third of its windows), three for the spread to count
    found = (hz is not None and len(near) >= 2 and share >= COMPANION_SHARE and abs(hz / F - c["ratio"]) <= tol * c["ratio"]
             and (len(near) >= 3 or nwin <= 3) and spread <= max(COMPANION_SPREAD_HZ, COMPANION_SPREAD * exp))
    return dict(what=c["what"], expected_hz=round(exp, 2), found_hz=round(hz, 2) if found else None,
                ratio_heard=round(hz / F, 4) if hz else None, share=round(share, 2), spread_hz=round(spread, 3),
                measured=c["measured"])


def propeller(F, peaks=(), nwin=0, blades=BLADES, airframes=PROPELLERS, match=MATCH):
    """What a harmonic series on F can be as a propeller or rotor: every (blades, rpm) it allows -- the series
    cannot tell them apart -- and each known airframe whose blade-pass in flight it matches within `match`, with its
    second tone looked for among the lines `ls` (`companion`), and whether F also falls in that airframe's (or
    another's) measured ground range."""
    allows = [dict(blades=b, rpm=round(60 * F / b, 1)) for b in blades]
    matches, ground = [], []
    for a in airframes:
        bpf = a["blades"] * a["rpm"] / 60
        off = (F - bpf) / bpf
        if abs(off) <= match:
            c = companion(a, F, peaks, nwin)
            matches.append(dict(airframe=a["name"], blades=a["blades"], rpm_flight=a["rpm"], blade_pass_hz=round(bpf, 2),
                                off=round(off, 4), shaft_rpm_here=round(60 * F / a["blades"], 1), sources=a["sources"],
                                companion=c, identified=bool(c and c["found_hz"])))
        lo, hi = a["measured_ground_hz"]
        if lo - 0.5 <= F <= hi + 0.5:
            ground.append(dict(airframe=a["name"], measured_ground_hz=a["measured_ground_hz"]))
    return dict(allows=allows, matches_in_flight=matches, within_ground_range_of=ground)


def shaft_orders(x, rpm, fs=FS, orders=24):
    """The mean excess (dB) at each order 1..orders of a shaft turning at `rpm`, over the record's windows: a
    B-bladed propeller stands at multiples of B."""
    starts, w = windows(len(x), fs)
    shaft = rpm / 60.0
    acc, n = np.zeros(orders), 0
    for s in starts:
        seg = np.asarray(x[s:s + w], float)
        if not len(seg) or np.max(np.abs(seg)) < 10 ** (SILENT_DBFS / 20):
            continue
        f, L, ex = excess(seg, fs, shaft * orders + 5)
        for o in range(1, orders + 1):
            m = np.abs(f - o * shaft) <= 0.75
            acc[o - 1] += ex[m].max() if m.any() else 0.0
        n += 1
    return [round(float(v / n), 1) for v in acc] if n else None


def lookalike_entries(fields, fps):
    """The clip's own heard rhythms, folded through fps into the band a beat is looked for in: entries in
    `flicker.lookalikes`' form ({hz, what, source}), for its table."""
    from .flicker import LOW, TOP, alias
    if not fps or not fields:
        return []
    top = TOP * float(fps) / 2
    out, seen = [], set()

    def add(hz, what):
        a = alias(hz, float(fps))
        key = round(a, 2)
        if LOW <= a <= top and key not in seen:
            seen.add(key)
            out.append(dict(hz=round(a, 3), what=f"{what}, heard in the clip's sound and folded through {float(fps):.5g} "
                                                 "frames a second", source=f"{hz:.2f} Hz (sound)"))
    fam = fields.get("families") or {}
    for s in fam.get("series", []):
        for m in s["members"]:
            add(m["hz"], f"a harmonic series on {s['f0_hz']:.2f} Hz (x{m['k']})" + (": a propeller or rotor's" if s["steady"] else ""))
    for m in fam.get("single", []):
        add(m["hz"], f"the blade-pass of {m['airframe'].split(' with ')[0]}")
    if fam.get("bus"):
        for k in (1, 2):
            add(k * fam["bus"]["f0_hz"], "the aircraft's 400-Hz power" + (", or a lamp on it" if k == 2 else ""))
    if fam.get("mains"):
        for k in (1, 2):
            add(k * fam["mains"]["f0_hz"], f"the {fam['mains']['nominal_hz']:g}-Hz mains" + (", or a lamp on it" if k == 2 else ""))
    return sorted(out, key=lambda d: d["hz"])


@lru_cache(maxsize=32)
def heard(path, fps, max_s=MAX_S):
    """The rhythms a file's sound carries, folded through fps (`lookalike_entries`), for `flicker.lookalikes`: []
    where there is no sound track, or it is silence."""
    f = measure(path, fps=Fraction(fps).limit_denominator(100000) if fps else None, max_s=max_s).fields
    return tuple(f.get("lookalikes") or ())


# ---- the stage ----------------------------------------------------------------------------------------
def measure(path, t0=0.0, seconds=None, fps=None, rpm=None, max_s=MAX_S, out=None):
    """Read the sound track of `path` (from t0, for `seconds`, at most max_s): a Found. `fps` overrides the
    video's frame rate (an audio-only file has none); `rpm` asks for the shaft-order profile at that speed."""
    info = probe(path)
    rate = fps if fps else info["fps"]
    fields = dict(audio_streams=info["audio"], fps=None if rate is None else float(rate),
                  fps_exact=None if rate is None else str(rate), duration_s=round(info["duration_s"], 2))
    no_power, needs, files = [], [], []
    if not info["audio"]:
        fields["finding"] = "No sound track: nothing to hear."
        no_power.append(("audio", "the file has no sound track"))
        return Found("audio", {"Sound": fields["finding"]}, fields, no_power=no_power)
    span = min(max_s, seconds or max_s, max(0.0, info["duration_s"] - t0) or max_s)
    x = decode(path, t0, span)
    peak, rms = loudness(x)
    fields.update(sample_rate=info["audio"][0]["sample_rate"], codec=info["audio"][0]["codec"],
                  read_s=round(len(x) / FS, 2), from_s=t0, peak_dbfs=round(peak, 1), mean_dbfs=round(rms, 1))
    if info["duration_s"] - t0 > span + 1:
        fields["read_part"] = f"the first {span:g} s from {t0:g} s of {info['duration_s']:.0f} s"
    if peak < SILENT_DBFS:
        fields["silent"] = True
        fields["finding"] = "The sound track is digital silence: nothing to hear."
        no_power.append(("audio", "the sound track is digital silence"))
        return Found("audio", {"Sound": fields["finding"]}, fields, no_power=no_power)
    fields["silent"] = False
    if len(x) < MIN_S * FS:
        fields["finding"] = f"Only {len(x) / FS:.1f} s of sound: too short to read."
        no_power.append(("audio", f"under {MIN_S:g} s of sound"))
        return Found("audio", {"Sound": fields["finding"]}, fields, no_power=no_power)
    ls, used, res, peaks = lines(x)
    fields.update(windows=used, resolution_hz=None if res is None else round(res, 3), lines=ls)
    fams, ls = families(ls, fields["sample_rate"], rate, peaks, used)
    try:
        refine(x, fams)
    except Exception as e:                          # the 4-s reading stands without it
        fams["refine_error"] = str(e)
    fields["families"] = fams
    if rpm:
        fields["shaft"] = dict(rpm=rpm, orders_db=shaft_orders(x, rpm))
    fields["lookalikes"] = lookalike_entries(fields, rate)
    if rate is None:
        needs.append("the video's frame rate (--fps) to fold the heard rhythms into the beat band")
    if used and res and res > 1.0 / WIN_S + 1e-6:
        fields["short"] = True
    fields["finding"] = finding(fields)
    if out is not None and ls:
        try:
            files.append(figure(x, fields, f"{out}_audio.png"))
        except Exception as e:                      # a figure is never worth a failed measurement
            fields["figure_error"] = str(e)
    return Found("audio", {"Sound": fields["finding"]}, fields, no_power=no_power, needs=needs, files=files)


def finding(fields):
    """One paragraph: what the sound says, from the fields."""
    fam = fields.get("families") or {}
    ls = fields.get("lines") or []
    if not ls:
        return (f"Sound ({fields.get('peak_dbfs')} dBFS peak), but no steady tone {EXCESS_DB:g} dB over the noise "
                f"in half the {fields.get('windows')} windows.")
    say = [f"{len(ls)} steady tone{'s' if len(ls) != 1 else ''}."]
    for c in fam.get("codec", []):
        say.append(f"{len(c['members'])} are the codec's ({c['what']}, multiples of {c['frame_hz']:g} Hz)"
                   + ("" if c["this_files_rate"] else " -- not this file's rate: an earlier encode") + ".")
    for c in fam.get("codec_cross", []):
        say.append(f"{len(c['members'])} more are products of an earlier encode ({c['what'].split(',')[0]}, "
                   f"{c['frame_hz']:g} Hz) mixed with this one's frames: the file was encoded at least twice.")
    if fam.get("frame"):
        fr = fam["frame"]
        txt = f"The video's frame rate is heard ({fr.get('hz', fr['fps']):.4f} Hz" + (", NTSC's 30/1.001" if fr.get("ntsc") else "")
        if fr.get("field_hz"):
            txt += (f"; with its field rate, {fr['field_hz']:.3f} Hz: video sync buzz, which a 4-s window cannot tell "
                    "from 60-Hz mains")
        say.append(txt + f"; {len(fr['members'])} lines of its comb).")
    if fam.get("bus"):
        b = fam["bus"]
        say.append(f"An aircraft's 400-Hz power, at {b['f0_hz']:.3f} Hz: the clip plays at {b['speed_range'][0]:.3f}-"
                   f"{b['speed_range'][1]:.3f} of real speed (the bus's steady-state range).")
        r = b.get("refined") or {}
        if r.get("pulldown_if"):
            say.append(f"It sits at 400/1.001 ({r['ppm_from_pulldown']:+d} ppm): either the supply runs there, or a 400.000-Hz "
                       "supply is heard 0.1 % slow, as an NTSC pull-down (30 to 29.97 frames a second) slows a sound track.")
        if r.get("second"):
            sc = r["second"]
            say.append(f"A second 400-Hz supply, at {sc['f0_hz']:.3f} Hz (x{', x'.join(map(str, sc['ks']))}): two generators "
                       "on separate buses, heard apart only in the whole record.")
    if fam.get("bus_possible"):
        b = fam["bus_possible"]
        say.append(f"Lines at x{', x'.join(str(m['k']) for m in b['members'] if not m['shared'])} of {b['f0_hz']:.3f} Hz may be "
                   f"an aircraft's 400-Hz power, but {b['why']}: possible, not shown.")
    if fam.get("mains"):
        m = fam["mains"]
        say.append((f"{m['nominal_hz']:g}-Hz mains, at {m['f0_hz']:.3f} Hz: recorded or copied on ground power; the "
                    f"clip plays at {m['speed_range'][0]:.4f}-{m['speed_range'][1]:.4f} of real speed."
                    if m.get("grid", True) else
                    f"A {m['nominal_hz']:g}-Hz power hum at {m['f0_hz']:.3f} Hz ({100 * (m['f0_hz'] / m['nominal_hz'] - 1):+.2f} %, "
                    f"x{', x'.join(str(q['k']) for q in m['members'])}): further off than a grid strays, so a local supply (a "
                    "generator, an inverter, a ship's power) or a copy retimed by that much.")
                   + (" At 59.94 Hz it may instead be an NTSC chain's field rate (the file has no video to tell)."
                      if m.get("field_rate_if") else ""))
    for sb in fam.get("sidebands", []):
        say.append(f"Lines at {sb['hz'][0]:.2f} and {sb['hz'][1]:.2f} Hz are sidebands of {sb['of']} (x{sb['k']}, "
                   f"-+{sb['offset_hz']:.2f} Hz): the hum modulated at {sb['offset_hz']:.2f} Hz, as by a tape transport.")
    if fam.get("hum"):
        h = fam["hum"]
        say.append(f"Mains hum near {h['nominal_hz']:g} Hz ({h['hz']:.2f} Hz, wandering +-{h['hz_sd']:.2f} Hz): recorded or "
                   "copied on ground power through a tape or disc transport, whose wow it carries -- no clock.")
    for s in fam.get("series", []):
        p = s["propeller"]
        head = f"A harmonic series on {s['f0_hz']:.2f} Hz (x{', x'.join(str(m['k']) for m in s['members'])})"
        if s.get("odd_only"):
            say.append(head + ": odd harmonics only, the mark of a square or switched electrical waveform (a tone, an "
                       "inverter), not of a rotating machine.")
            continue
        if s.get("mains_if"):
            mi = s["mains_if"]
            head += (f" -- {100 * (mi['speed'] - 1):+.1f}% from {mi['nominal_hz']:g} Hz: if it is the mains, the record plays "
                     f"at {mi['speed']:.3f} of real speed")
        if p is None:
            say.append(head + ": its tones wander, so it is neither a governed propeller nor a supply.")
            continue
        txt = (head + ": something turning steadily (a propeller, rotor, fan or pump); as a propeller, "
               + ", ".join(f"{a['blades']} blades at {a['rpm']:.0f} rpm" for a in p["allows"] if a["blades"] in (3, 4, 6))
               + " or others -- the series alone cannot say which.")
        for m in p["matches_in_flight"]:
            if m.get("identified"):
                txt += (f" In flight it is {m['airframe']}: {m['blade_pass_hz']:g} Hz expected, {100 * m['off']:+.1f}%.")
                txt += _companion_said(m.get("companion"))
            else:
                txt += (f" It matches the blade-pass in flight of {m['airframe'].split(' with ')[0]} ({m['blade_pass_hz']:g} Hz, "
                        f"{100 * m['off']:+.1f}%), but not identified: that airframe's second tone is not heard, and other "
                        "airframes share a blade-pass (an MQ-9 heard from the ground hums at 67-76 Hz, its second tone at "
                        "9.00 x)." + _companion_said(m.get("companion")))
        for g in p["within_ground_range_of"]:
            if not any(m["airframe"] == g["airframe"] for m in p["matches_in_flight"]):
                txt += (f" On the ground it could also be {g['airframe'].split(' with ')[0]} "
                        f"(measured {g['measured_ground_hz'][0]:g}-{g['measured_ground_hz'][1]:g} Hz there): "
                        "a phase of flight decides.")
        say.append(txt)
    for m in fam.get("near", []):
        say.append(f"A steady line at {m['hz']:.2f} Hz is {100 * m['off']:+.1f}% from the blade-pass in flight of "
                   f"{m['airframe'].split(' with ')[0]} ({m['blade_pass_hz']:g} Hz), but alone, without that airframe's "
                   "second tone: no reading.")
    for m in fam.get("single", []):
        txt = (f"A single steady line at {m['hz']:.2f} Hz, {100 * m['off']:+.1f}% from the blade-pass in flight of "
               f"{m['airframe']} ({m['blade_pass_hz']:g} Hz), with its harmonics too weak to hear; it is read as that "
               "airframe because its second tone is there too." + _companion_said(m.get("companion")))
        others = [g for g in m["within_ground_range_of"] if g["airframe"] != m["airframe"]]
        if others:
            txt += (f" On the ground it could also be {others[0]['airframe'].split(' with ')[0]}: a phase of flight decides.")
        say.append(txt)
    other = [L for L in ls if L["is"] is None]
    if other:
        say.append("Unexplained: " + ", ".join(f"{L['hz']:.2f} Hz" for L in other[:6]) + (" ..." if len(other) > 6 else "") + ".")
    la = fields.get("lookalikes") or []
    if la:
        say.append(f"Folded through {fields['fps']:.5g} frames a second, these sit at "
                   + ", ".join(f"{d['hz']:.2f}" for d in la) + " Hz in the beat band.")
    if fields.get("short"):
        say.append(f"(Shorter than two {WIN_S:g}-s windows: read in three half-length ones, resolution "
                   f"{fields['resolution_hz']:.2f} Hz.)")
    return " ".join(say)


def plain_name(airframe, which=0):
    """An airframe of the table, as the window names it: "a C-130 with four-bladed propellers" (which=1: its kinds)."""
    a = next((a for a in PROPELLERS if a["name"] == airframe), None)
    return a["plain"][which] if a and a.get("plain") else ("" if which else airframe.split(" with ")[0])


def _listed(values, most=8, unit=""):
    """1.2, 3.4 and 5.6 Hz; past `most`, the first ones and 'and more'."""
    v = list(values)
    if len(v) > most:
        return ", ".join(v[:most]) + f"{unit}, and more"
    return (", ".join(v[:-1]) + " and " + v[-1] if len(v) > 1 else v[0]) + unit


def plainly(fields):
    """What the sound says, for someone outside the field: (the headline, [a sentence each]). The window's words
    (its page of the sound, `sound_qt`), written from the same fields as `finding`, which stays the measurement's."""
    if not fields.get("audio_streams"):
        return "This video has no sound track.", []
    if fields.get("silent"):
        return ("This video's sound is silent: there is nothing to hear.",
                ["Nothing in it can say where, or on what, the video was recorded."])
    ls = fields.get("lines")
    if ls is None:
        return f"There is too little sound to read ({fields.get('read_s', 0):g} seconds).", []
    fam = fields.get("families") or {}
    series = fam.get("series", [])
    named = []                                         # (airframe, hum heard, its second tone)
    for s in series:
        for m in (s.get("propeller") or {}).get("matches_in_flight", []):
            c = m.get("companion") or {}
            if m.get("identified") and c.get("found_hz"):
                named.append((m["airframe"], s["f0_hz"], c))
    for m in fam.get("single", []):
        named.append((m["airframe"], m["hz"], m.get("companion") or {}))
    bus, mains, hum, sidebands = fam.get("bus"), fam.get("mains"), fam.get("hum"), fam.get("sidebands", [])
    turning = [s for s in series if s.get("propeller") and not s.get("odd_only") and not s.get("mains_if")
               and not any(m.get("identified") for m in s["propeller"].get("matches_in_flight", []))]
    retimed = [s for s in series if s.get("mains_if")]
    other = [L for L in ls if L.get("is") is None]
    nothing = False
    if named:
        head = f"The sound names the aircraft: {plain_name(named[0][0])}, in flight."
    elif bus and mains and mains.get("grid", True):
        head = "The sound was recorded on an aircraft, then copied on the ground."
    elif bus and mains:
        head = ("The sound was recorded on an aircraft, then copied on equipment whose power hum is not public power's: "
                "a generator's of its own, or the copy runs at the wrong speed.")
    elif bus:
        head = "The sound was recorded on an aircraft: it holds the hum of an aircraft's electrical power."
    elif mains and mains.get("grid", True):
        head = "The sound was recorded, or copied, on the ground: it holds the hum of mains power."
    elif mains:
        head = (f"The sound holds a power hum {100 * abs(mains['f0_hz'] / mains['nominal_hz'] - 1):.1f} % off public power's: "
                "either the power was a generator's of its own, or the recording plays at the wrong speed.")
    elif hum:
        head = "The sound holds a hum of mains power that wavers: it was copied through a tape or record player."
    elif sidebands:
        head = "The sound holds a hum that a tape machine's motor makes rise and fall: it was copied from tape."
    elif retimed:
        head = "The sound holds a hum close to mains power's: the recording may not play at its true speed."
    elif turning:
        head = "Something turning at a steady speed is heard: a propeller, a rotor, a fan or a pump."
    elif (fam.get("frame") or {}).get("field_hz"):
        head = "The sound has passed through video equipment: it holds the hum that video's own timing makes."
    elif fam.get("codec_cross") and not other:
        head = "The sound holds nothing of its own: only what saving it, twice, left behind."
    elif not ls:
        return ("There is sound, but no steady tone in it.",
                ["What is heard, such as voices, wind or noise, does not name a machine or a power supply."])
    else:
        head, nothing = "There is sound, with steady tones in it, but they name nothing known.", True
    rest = []
    for airframe, hz, c in named:
        kinds = plain_name(airframe, 1)
        rest.append(f"Two tones agree: the propellers' hum at {hz:.2f} Hz, and a second tone at {c['ratio_heard']:.3f} "
                    f"times that ({c['found_hz']:.1f} Hz). Either alone would not be enough. So whatever recorded the "
                    f"sound was aboard such an aircraft, or close to one" + (f" ({kinds})." if kinds else "."))
    if bus:
        lo, hi = bus["speed_range"]
        rest.append(f"An aircraft's electrical power hums at 400 Hz, and is held between {BUS_RANGE[0]:g} and "
                    f"{BUS_RANGE[1]:g} Hz. Here it is at {bus['f0_hz']:.2f} Hz: the video plays at its true speed, give or "
                    f"take {100 * (hi - lo) / 2:.1f} %.")
        r = bus.get("refined") or {}
        if r.get("pulldown_if"):
            rest.append("That is 400 slowed by exactly one part in a thousand, the change made when video moves from 30 to "
                        "29.97 frames a second. So either the power ran at that, or the video plays a tenth of a percent slow.")
        if r.get("second"):
            rest.append(f"A second power hum is heard, at {r['second']['f0_hz']:.2f} Hz: two generators, each on its own line.")
    if fam.get("bus_possible"):
        rest.append(f"Some tones fit an aircraft's electrical power, at {fam['bus_possible']['f0_hz']:.2f} Hz, but others it "
                    "would need sit where the video's own hum is, so it is possible, not certain.")
    if mains:
        lo, hi = mains["speed_range"]
        rest.append(f"Mains power hums at {mains['nominal_hz']:g} Hz. Here it is at {mains['f0_hz']:.3f} Hz: the video "
                    f"plays at {100 * lo:.2f} to {100 * hi:.2f} % of its true speed." if mains.get("grid", True) else
                    f"A power hum is heard at {mains['f0_hz']:.2f} Hz, {100 * abs(mains['f0_hz'] / mains['nominal_hz'] - 1):.1f} % "
                    f"{'above' if mains['f0_hz'] > mains['nominal_hz'] else 'below'} {mains['nominal_hz']:g}: further off than "
                    "public power ever runs, so it is a local generator's (a ship's, say) or the recording was sped or slowed.")
        if mains.get("field_rate_if"):
            rest.append("It could also be the hum of video's own timing, 59.94 a second, which sits right beside mains power's.")
    if fam.get("frame"):
        fr = fam["frame"]
        rate = fr.get("hz") or fields.get("fps") or fr["fps"]
        rest.append(f"The video's own rate of {rate:.4g} frames a second is heard in the sound: video equipment hums at "
                    "it, so the sound has passed through some."
                    + (f" So is twice that, {fr['field_hz']:.2f} a second: that hum is video's timing, not mains power, though "
                       "it sits close to it." if fr.get("field_hz") else ""))
    for sb in sidebands:
        rest.append(f"The hum rises and falls {sb['offset_hz']:.2f} times a second, as the motor of a tape machine makes "
                    "it do.")
    if hum:
        rest.append(f"Mains hum near {hum['nominal_hz']:g} Hz ({hum['hz']:.2f} Hz) wavers by {hum['hz_sd']:.2f} Hz, as "
                    "a tape or record player makes it waver, so it cannot say how fast the video plays.")
    for s in retimed:
        mi = s["mains_if"]
        rest.append(f"A hum at {s['f0_hz']:.2f} Hz is {100 * (mi['speed'] - 1):+.1f} % from {mi['nominal_hz']:g} Hz: "
                    f"if it is mains hum, the recording plays at {100 * mi['speed']:.1f} % of its true speed.")
    if turning:
        rest.append(("Something turns at a steady speed: a tone at " if len(turning) == 1 else
                     "Things turn at steady speeds: tones at ")
                    + _listed([f"{s['f0_hz']:.2f}" for s in turning], unit=" Hz")
                    + (" and its multiples." if len(turning) == 1 else ", each with its multiples."))
        for s in turning:
            for m in s["propeller"].get("matches_in_flight", []):
                rest.append(f"The tone at {s['f0_hz']:.2f} Hz is where {plain_name(m['airframe'])} hums in flight, but "
                            "the second tone that would name it is not heard, and other aircraft hum there too: an MQ-9 "
                            "drone, heard from the ground, hums at 67 to 76 Hz. So no aircraft is named.")
    for s in series:
        if s.get("odd_only"):
            rest.append(f"An electrical tone at {s['f0_hz']:.2f} Hz (only its odd multiples), such as a warning tone or "
                        "a power converter: not a turning machine.")
        elif s.get("propeller") is None and not s.get("mains_if"):
            rest.append(f"Tones at {s['f0_hz']:.2f} Hz and its multiples wander: neither a power supply nor a machine "
                        "held at one speed.")
    for m in fam.get("near", []):
        rest.append(f"A steady tone at {m['hz']:.2f} Hz is close to where {plain_name(m['airframe'])} hums, but it is "
                    "alone: not enough to name it.")
    if fam.get("codec"):
        rest.append("Some tones are left by saving the sound in a compressed form, not by anything that was recorded.")
    if fam.get("codec_cross"):
        rest.append("Some come from an earlier saving, at another rate: the sound was saved at least twice.")
    if other:
        rest.append(("They are at " if nothing else "Tones that name nothing known: ")
                    + _listed([f"{L['hz']:.1f}" for L in other], 6, " Hz") + ".")
    la = fields.get("lookalikes") or []
    if la:
        rest.append(f"At this video's {fields['fps']:.4g} frames a second, these tones would look like a steady flicker "
                    f"of the object's brightness at {_listed([format(d['hz'], '.2f') for d in la], unit=' times a second')}. "
                    "A flicker at one of those rates may come from the same machine, not from wings.")
    if fields.get("read_part"):
        rest.append(f"Only the first {fields['read_s']:g} seconds of the sound were read, of {fields['duration_s']:.0f}.")
    return head, rest


def _companion_said(c):
    """The second tone, said."""
    if not c:
        return ""
    if c["found_hz"] is None:
        return (f" Its second tone ({c['what']}) is not heard near {c['expected_hz']:.1f} Hz"
                + (f" (a peak there in {100 * c['share']:.0f}% of the windows, at {c['ratio_heard']:.3f} x)" if c.get("ratio_heard") else "")
                + ".")
    return (f" Its second tone is there: {c['found_hz']:.2f} Hz, {c['ratio_heard']:.3f} x the blade-pass "
            f"(measured {c['measured']}).")


def said(fields):
    """What `mcdonald audio` prints, from the fields."""
    out = []
    if fields.get("audio_streams"):
        a = fields["audio_streams"][0]
        out.append(f"sound: {a['codec']}, {a['sample_rate']} Hz, {a['channels']} ch"
                   + (f"; read {fields['read_s']:g} s" if fields.get("read_s") is not None else "")
                   + (f" ({fields['read_part']})" if fields.get("read_part") else "")
                   + (f"; peak {fields['peak_dbfs']} dBFS, mean {fields['mean_dbfs']} dBFS" if fields.get("peak_dbfs") is not None else ""))
    for L in fields.get("lines", [])[:16]:
        out.append(f"  {L['hz']:9.2f} Hz  +{L['excess_db']:4.1f} dB  in {L['windows']} of {fields['windows']} windows"
                   + (f", +-{L['hz_sd']:.2f} Hz" if L.get("hz_sd") is not None else "")
                   + ("" if L["steady"] else " (wanders)")
                   + (f"  -- {L['is']}" if L.get("is") else "")
                   + (f" (or {', '.join(L['also'])})" if L.get("also") else ""))
    if len(fields.get("lines", [])) > 16:
        out.append(f"  ... and {len(fields['lines']) - 16} more")
    sh = fields.get("shaft")
    if sh and sh.get("orders_db"):
        out.append(f"  shaft at {sh['rpm']:g} rpm, orders 1-{len(sh['orders_db'])} (dB): "
                   + " ".join(f"{i + 1}:{v:+.0f}" for i, v in enumerate(sh["orders_db"])))
    out.append(fields.get("finding", ""))
    return out


def figure(x, fields, path):
    """The mean excess spectrum up to just past the highest explained line, the lines marked by family."""
    from matplotlib.figure import Figure
    from . import figures as fg
    fg.setup()                                         # the house style; the figure itself is not pyplot's, so that
    ls = fields["lines"]                               # the window may draw it in a thread (no Qt canvas is made)
    fam = fields.get("families") or {}             # the second tone that named an airframe, which is not always a line
    named = [m for s in fam.get("series", []) for m in (s.get("propeller") or {}).get("matches_in_flight", [])
             if m.get("identified")] + list(fam.get("single", []))
    seconds = sorted({round(m["companion"]["found_hz"], 2) for m in named if (m.get("companion") or {}).get("found_hz")})
    top = min(BAND[1], max(200.0, 1.15 * max(L["hz"] for L in ls), 1.1 * max(seconds, default=0)))
    starts, w = windows(len(x))
    acc, n = None, 0
    for s in starts:
        seg = np.asarray(x[s:s + w], float)
        if np.max(np.abs(seg)) < 10 ** (SILENT_DBFS / 20):
            continue
        f, L, ex = excess(seg, FS, top)
        acc = ex if acc is None else acc + ex
        n += 1
    sel = (f >= BAND[0]) & (f <= top)
    fig = Figure(figsize=(fg.FigureSize.NOTE, 3.2))
    ax = fig.subplots()
    ax.plot(f[sel], (acc / n)[sel], color=fg.PRIMARY, lw=0.9, zorder=3)
    kinds = [("series", "a harmonic series", fg.SERIES[0]), ("power", "a supply (mains, 400-Hz bus)", fg.SERIES[1]),
             ("codec", "the codec's frames", fg.MUTED), ("frame", "the video's frame rate", fg.SERIES[2])]
    def kind(L):
        lab = L.get("is") or ""
        return ("series" if lab.startswith("a harmonic") else "power" if ("power" in lab or "mains" in lab)
                else "codec" if "frames at" in lab else "frame" if "frame rate" in lab else None)
    used = set()
    for L in ls:
        k = kind(L)
        if k is None:
            continue
        col = dict((a, c) for a, _, c in kinds)[k]
        ax.axvline(L["hz"], color=col, lw=1.0, ls=(0, (4, 2)), zorder=1)
        used.add(k)
    for hz in seconds:
        ax.axvline(hz, color=fg.SERIES[3], lw=1.2, ls=(0, (1, 1.5)), zorder=2)
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color=c, lw=1.2, ls=(0, (4, 2)), label=lab) for a, lab, c in kinds if a in used]
    if seconds:
        handles.append(Line2D([], [], color=fg.SERIES[3], lw=1.2, ls=(0, (1, 1.5)), label="the second tone that names it"))
    if handles:
        ax.legend(handles=handles, frameon=True, facecolor=fg.SURFACE, edgecolor="none", framealpha=0.92, fontsize=8,
                  loc="upper right").set_zorder(5)     # over the dashed lines, which a busy record draws through it
    ax.set_xlim(BAND[0], top)
    ax.set_xlabel("Frequency (Hz)", fontweight="bold")
    ax.set_ylabel("Above Local Median (dB)", fontweight="bold")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fg.save(fig, path)
    return path


# ---- CLI ----------------------------------------------------------------------------------------------
# ---- a source passing the microphone: speed and closest range from its Doppler curve ----------------------
SOUND_C = 343.0        # m/s: the speed of sound at 20 C; c = 331.3 + 0.606 T
FLY_FS = 4000          # Hz: the rate a pass is read at (its tones lie under 1 kHz)
FLY_WIN, FLY_HOP = 0.5, 0.05   # s: spectrogram window and hop for following a sweeping tone
FLY_STEP = 1.5         # Hz: a followed tone moves at most this far between frames
FLY_REL = 0.012        # a harmonic is looked for within this share of k x the tone (or of the fitted curve)
FLY_DB = 8.0           # dB over the frame's local median: a point of the track
FLY_GAP_S = 0.3        # s: a followed tone may fade this long (six frames) and be picked up again: near the closest
                       # point the ground's reflection puts nulls in it (the Lloyd's mirror); stopping at 0.25 s lost
                       # recessions, which the fit needs (checked against ADS-B on AeroSonicDB)
FLY_SCALE = 0.3        # Hz: the robust (soft-L1) loss's scale, on f / k


def doppler(t, f0, v, r0, tau0, c=SOUND_C):
    """The frequency heard at t from a source of rest frequency f0 passing at constant speed v on a straight line,
    closest (r0) at emission time tau0, in still air: f0 / (1 + (v/c) s/R), s = v (tau - tau0), R = sqrt(s^2 + r0^2),
    tau the emission time of what is heard at t = tau + R/c (solved in closed form). Ferguson (1992, JASA 92:1403)."""
    T = np.asarray(t, float) - tau0
    a = c * c - v * v
    u = (c * c * T - np.sqrt(np.maximum(c ** 4 * T * T - a * (c * c * T * T - r0 * r0), 0))) / a
    s_ = v * u
    return f0 / (1 + (v / c) * s_ / np.sqrt(s_ * s_ + r0 * r0))


def _fly_spectrogram(x, fs=FLY_FS):
    n = int(FLY_WIN * fs)
    N = 1 << int(np.ceil(np.log2(n * 8)))
    w = np.hanning(n)
    f = np.fft.rfftfreq(N, 1 / fs)
    T, S = [], []
    for s0 in range(0, len(x) - n + 1, int(FLY_HOP * fs)):
        T.append((s0 + n / 2) / fs)
        S.append(10 * np.log10(np.abs(np.fft.rfft(x[s0:s0 + n] * w, N)) ** 2 + 1e-20))
    return np.array(T), f, np.array(S)


def _refined(S, f, i, j):
    a, b, c = S[i, j - 1], S[i, j], S[i, j + 1]
    d = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) else 0.0
    return f[j] + np.clip(d, -0.5, 0.5) * (f[1] - f[0])


def _follow(T, f, S, lo, hi, ctx=40.0):
    """A sweeping tone followed by continuity: from the strongest point in [lo, hi], frame by frame either way, the
    strongest peak within FLY_STEP Hz of the last, until it is lost for FLY_GAP_S. [(t, hz)]."""
    cx = (f >= lo - ctx) & (f <= hi + ctx)
    E = S - np.median(S[:, cx], axis=1, keepdims=True)
    sel = np.flatnonzero((f >= lo) & (f <= hi))
    i0, j0 = np.unravel_index(np.argmax(E[:, sel]), (len(T), len(sel)))
    j0 = sel[j0]
    pts = {i0: j0}
    for step in (1, -1):
        j, miss, i = j0, 0, i0 + step
        while 0 <= i < len(T) and miss < int(round(FLY_GAP_S / FLY_HOP)):
            w = np.flatnonzero((np.abs(f - f[j]) <= FLY_STEP) & (f >= lo) & (f <= hi))
            jj = w[np.argmax(E[i, w])]
            if E[i, jj] >= FLY_DB:
                pts[i], j, miss = jj, jj, 0
            else:
                miss += 1
            i += step
    return [(T[i], _refined(S, f, i, j)) for i, j in sorted(pts.items()) if 0 < j < len(f) - 1]


def _near(T, f, S, centre, rel=FLY_REL, ctx=40.0, span=None):
    """[(t, hz)]: per frame (within `span`, if given), the strongest peak within rel of centre(t), FLY_DB over the
    local median."""
    out = []
    for i, t in enumerate(T):
        if span is not None and not span[0] <= t <= span[1]:
            continue
        c = centre(t)
        sel = np.flatnonzero(np.abs(f - c) <= rel * c)
        if not len(sel):
            continue
        j = sel[np.argmax(S[i, sel])]
        if 0 < j < len(f) - 1 and S[i, j] - np.median(S[i, np.abs(f - c) <= ctx]) >= FLY_DB:
            out.append((t, _refined(S, f, i, j)))
    return out


def _fly_fit(tracks, c, f0=None, start=None):
    """Robust least squares of `doppler` to [(k, [(t, hz)])] on hz / k: (f0, v, r0, tau0), f0 held if given."""
    from scipy.optimize import least_squares
    t = np.concatenate([[p[0] for p in tr] for _, tr in tracks])
    y = np.concatenate([[p[1] / k for p in tr] for k, tr in tracks])
    hi, lo = np.percentile(y, 95), np.percentile(y, 5)
    starts = [start] if start is not None else [[2 * hi * lo / (hi + lo), max(5.0, c * (hi - lo) / (hi + lo)), r, t[np.argmin(np.abs(y - (hi + lo) / 2))]]
                                                for r in (50, 150, 400, 1000, 2500)]
    lb, ub = [1.0, 1.0, 5.0, t.min() - 30], [1e4, 0.8 * c, 2e4, t.max() + 30]
    best = None
    for p0 in starts:
        p0 = [min(max(v, l + 1e-6), u - 1e-6) for v, l, u in zip(p0, lb, ub)]
        if f0 is None:
            r = least_squares(lambda p: doppler(t, *p, c=c) - y, p0, bounds=(lb, ub), loss="soft_l1", f_scale=FLY_SCALE)
            x = r.x
        else:
            r = least_squares(lambda p: doppler(t, f0, *p, c=c) - y, p0[1:], bounds=(lb[1:], ub[1:]), loss="soft_l1", f_scale=FLY_SCALE)
            x = np.r_[f0, r.x]
        if best is None or r.cost < best[0]:
            best = (r.cost, x, r)
    _, x, r = best
    resid = doppler(t, *x, c=c) - y
    rms = float(1.4826 * np.median(np.abs(resid)))
    try:
        cov = np.linalg.inv(r.jac.T @ r.jac) * rms ** 2
        err = list(np.sqrt(np.diag(cov)))
    except np.linalg.LinAlgError:
        err = [float("nan")] * len(r.x)
    if f0 is not None:
        err = [0.0] + err
    return x, err, rms, t


def flyover(x, lo, hi, fs=FLY_FS, rest_hz=None, temp_c=None, ks=(1, 2, 3), iters=3, retrack_base=True):
    """A source passing the microphone, from one sweeping tone: its speed, its closest range and when it passed.
    The tone in [lo, hi] (Hz) is followed through the record, its harmonics k x it with it, the Doppler curve of a
    straight, constant-speed pass fitted (robustly), then every harmonic re-tracked about the fitted curve and refitted.
    With `rest_hz` (the source's known tone at rest: an identified airframe's blade-pass) f0 is held; without it, f0 is
    fitted too, and over a partial pass it trades against v and r0 -- `profile` gives v and r0 at f0 held at each of
    several values, with the residual each leaves. c from temp_c (default 20 C). Needs a microphone that does not
    ride with the source: a cabin's own propellers have no Doppler.
    {f0_hz, v_ms, v_kn, r0_m, r0_ft, cpa_s, err, rms_hz, points, ks, cpa_inside, held, c, profile}."""
    c = SOUND_C if temp_c is None else 331.3 + 0.606 * temp_c
    T, f, S = _fly_spectrogram(np.asarray(x, float), fs)
    base = _follow(T, f, S, lo, hi)
    if len(base) < 20:
        return None
    tb, fb = np.array([p[0] for p in base]), np.array([p[1] for p in base])
    tracks = [(1, base)]
    for k in ks:
        if k != 1:
            tr = _near(T, f, S, lambda t, k=k: k * np.interp(t, tb, fb), span=(tb.min(), tb.max()))
            if len(tr) > 5:
                tracks.append((k, tr))
    def fit_any(tracks, start=None):
        """Held f0 as given; free, started from the curve's asymptotes (f0 the harmonic mean of the highest and lowest
        heard, v from their spread). Not from the lowest residual of an f0 scan: along the f0-v trade the residual is
        nearly flat, so its minimum is set by noise -- against ADS-B (AeroSonicDB) a scan's choice put 59 % of passes
        within 0.6-1.2 of the altitude, the asymptotes' 75 %."""
        return _fly_fit(tracks, c, rest_hz, start=start)

    prm, err, rms, t = fit_any(tracks)
    for _ in range(iters):
        # every harmonic re-tracked about the fitted curve (retrack_base=False keeps the followed tone as followed:
        # against ADS-B the two did alike)
        tracks = ([] if retrack_base else [(1, base)]) + \
                 [(k, tr) for k in ks if retrack_base or k != 1
                  for tr in [_near(T, f, S, lambda t, k=k, p=tuple(prm): k * doppler(t, *p, c=c))] if len(tr) > 5]
        if not tracks:
            break
        prm, err, rms, t = fit_any(tracks, start=list(prm))
    f0, v, r0, tau0 = (float(q) for q in prm)
    cpa = tau0 + r0 / c
    out = dict(f0_hz=round(f0, 3), v_ms=round(v, 1), v_kn=round(v * 1.94384, 0), r0_m=round(r0, 0), r0_ft=round(r0 / 0.3048, 0),
               cpa_s=round(cpa, 2), err=dict(f0_hz=round(err[0], 3), v_ms=round(err[1], 1), r0_m=round(err[2], 0)),
               rms_hz=round(rms, 3), points=int(len(t)), ks=[k for k, _ in tracks], cpa_inside=bool(t.min() < cpa < t.max()),
               held=rest_hz is not None, c=round(c, 1), span_s=(round(float(t.min()), 2), round(float(t.max()), 2)))
    if rest_hz is None:
        prof = []
        y = np.concatenate([[p[1] / k for p in tr] for k, tr in tracks])
        for g in np.linspace(0.8 * np.percentile(y, 3), 1.2 * np.percentile(y, 97), 21):
            q, _, r_, _ = _fly_fit(tracks, c, float(g), start=list(prm))
            prof.append(dict(f0_hz=round(float(g), 2), v_ms=round(float(q[1]), 1), r0_m=round(float(q[2]), 0), rms_hz=round(r_, 3)))
        out["profile"] = prof
    return out


def pass_of(video, lo, hi, t0=0.0, seconds=None, rest_hz=None, temp_c=None):
    """`flyover` on a video's or a sound file's own sound, from `t0` s for `seconds` (to the end, if not given), its
    times given in the recording's own: what `mcdonald audio --flyover` and the window's sound page both ask for."""
    x = decode(video, t0, seconds, fs=FLY_FS)
    r = flyover(x, lo, hi, rest_hz=rest_hz, temp_c=temp_c)
    if r:
        r["cpa_s"] = round(r["cpa_s"] + t0, 2)
        r["span_s"] = tuple(round(v + t0, 2) for v in r["span_s"])
    return r


def profile_fits(r):
    """The profile's rest tones that fit about as well as the best: residual within 20 % of it, plus 0.05 Hz (a real
    pass's track scatters 0.3-0.5 Hz, from wind and the aircraft's own wander)."""
    return [p for p in (r or {}).get("profile", []) if p["rms_hz"] <= 1.2 * r["rms_hz"] + 0.05]


def flyover_said(r):
    """One paragraph for a pass."""
    if r is None:
        return "No sweeping tone was followed long enough to fit a pass."
    txt = (f"A pass: the tone at rest {r['f0_hz']:.2f} Hz{' (held)' if r['held'] else ''}, moving at {r['v_ms']:.0f} m/s "
           f"({r['v_kn']:.0f} kn), closest at {r['r0_m']:.0f} m ({r['r0_ft']:.0f} ft), heard closest at {r['cpa_s']:.1f} s; "
           f"{r['points']} points on x{', x'.join(map(str, r['ks']))}, residual {r['rms_hz']:.2f} Hz, sound at {r['c']:g} m/s.")
    if not r["cpa_inside"]:
        txt += " The closest approach is outside the stretch heard, so the range is an extrapolation."
    if r.get("profile"):
        ok = profile_fits(r)
        if len(ok) > 1:
            txt += (f" With the rest tone free, f0 from {ok[0]['f0_hz']:.1f} to {ok[-1]['f0_hz']:.1f} Hz fits as well (within "
                    f"20 % of the best residual and 0.05 Hz), and with it v from {min(p['v_ms'] for p in ok):.0f} to {max(p['v_ms'] for p in ok):.0f} m/s "
                    f"and r0 from {min(p['r0_m'] for p in ok):.0f} to {max(p['r0_m'] for p in ok):.0f} m: hold the rest tone "
                    "(--rest, from an identified airframe) to pin them.")
    return txt


def main():
    import argparse
    from . import clip as vc
    from .report import emit, inputs_of, said_to_stderr

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", help="a video or a sound file, or a PURSUE record id")
    ap.add_argument("--from", dest="t0", type=float, default=0.0, help="start this many seconds in (default 0)")
    ap.add_argument("--seconds", type=float, help="read this many seconds (default: all, up to --max-s)")
    ap.add_argument("--max-s", type=float, default=MAX_S, help=f"read at most this much of a long recording (default {MAX_S:g} s)")
    ap.add_argument("--fps", type=lambda s: Fraction(s), help="frame rate to fold the heard rhythms through (default: the "
                                                               "video's own; needed for a sound file)")
    ap.add_argument("--rpm", type=float, help="also give the excess at each order of a shaft turning at this speed")
    ap.add_argument("--flyover", metavar="LO-HI", help="instead: fit a source passing the microphone (a ground recording of "
                    "an aircraft) from the sweeping tone between LO and HI Hz, over --from/--seconds: its speed and closest range")
    ap.add_argument("--rest", type=float, help="with --flyover: the tone's frequency at rest, if known (an identified "
                    "airframe's blade-pass: 68.0 for a T56 C-130 in flight), held instead of fitted")
    ap.add_argument("--temp-c", type=float, help="with --flyover: air temperature, for the speed of sound (default 20 C)")
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
    if args.flyover:
        lo, hi = (float(v) for v in args.flyover.split("-"))
        with said_to_stderr(args.json) as told:
            video, tag, _ = vc.resolve(args.video)
            r = pass_of(video, lo, hi, args.t0, args.seconds, rest_hz=args.rest, temp_c=args.temp_c)
            print(f"{Path(video).name}")
            print(flyover_said(r))
        found = Found("audio", {"Pass": flyover_said(r)}, dict(flyover=r, finding=flyover_said(r)),
                      no_power=[] if r else [("audio", "no sweeping tone to fit")])
        code = vc.EXIT_NOTHING if found.no_power else 0
        if args.json:
            env = found.envelope("audio", inputs_of(args), None, said=told, exit_code=code, error=None)
            env["inputs"]["video"] = str(video)
            emit(env)
        return code
    with said_to_stderr(args.json) as told:
        video, tag, _ = vc.resolve(args.video)
        out = vc.out_prefix(args.out, tag)
        found = measure(video, args.t0, args.seconds, args.fps, args.rpm, args.max_s, out=out)
        print(f"{Path(video).name}")
        print("\n".join(said(found.fields)))
    code = vc.EXIT_NOTHING if found.no_power else 0
    if args.json:
        env = found.envelope("audio", inputs_of(args), None, said=told, exit_code=code, error=None)
        env["inputs"]["video"] = str(video)
        emit(env)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
