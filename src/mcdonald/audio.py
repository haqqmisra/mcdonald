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
SUPPLY_TOL = 0.0012   # a supply's harmonic sits within this share of k f0 (and at least 0.3 Hz)
SUPPLY_SD = 0.0015    # ... and holds its frequency across windows to this share of it (or 0.06 Hz): a supply is steady
                      # (PR113's mains: 0.01 % at 1,140 Hz); PR107's wandering lines near 100, 200, 300 Hz are not mains
MAINS = ((50.0, 40), (60.0, 40))            # nominal, highest harmonic looked for
SUPPLY_LOW, SUPPLY_LOW_N_K = 3, 10            # a supply needs a member at k <= 3 and two at k <= 10
MAINS_STRAY = 0.002   # a grid strays at most about this share of its nominal frequency (taken wide)
BUS = (400.0, 10)
BUS_RANGE = (393.0, 407.0)                  # MIL-STD-704 normal steady state (from memory)
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
                if 1 <= j <= kmax and abs(M["hz"] - j * f0) <= max(0.3, tol * M["hz"]):
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
        fr = float(fps)
        mem = [(int(round(L["hz"] / fr)), L) for L in ls
               if 1 <= round(L["hz"] / fr) <= 8 and abs(L["hz"] - round(L["hz"] / fr) * fr) <= FRAME_TOL]
        if any(k == 1 for k, _ in mem):
            fams["frame"] = dict(fps=round(fr, 4), members=[dict(k=k, hz=L["hz"]) for k, L in sorted(mem, key=lambda m: m[0])])
            for _, L in mem:
                claim(L, "the video's frame rate")
    free = [L for L in ls if L["is"] is None]
    nominal, kmax = BUS
    got = _supply(free, nominal, kmax, *BUS_RANGE)
    if got and (len(got[1]) >= 2 or (got[1][0][0] == 1 and got[1][0][1]["excess_db"] >= 20)):
        f0, mem = got
        fams["bus"] = dict(f0_hz=round(f0, 3), members=[dict(k=k, hz=L["hz"]) for k, L in mem],
                           speed=round(f0 / nominal, 5),
                           speed_range=(round(f0 / BUS_RANGE[1], 4), round(f0 / BUS_RANGE[0], 4)))
        for _, L in mem:
            claim(L, "an aircraft's 400-Hz power")
    free = [L for L in ls if L["is"] is None]
    best = None
    for nominal, kmax in MAINS:
        got = _supply(free, nominal, kmax, nominal * 0.99, nominal * 1.01)
        if got and len(got[1]) >= 2 and (best is None or len(got[1]) > len(best[1][1])):
            best = (nominal, got)
    if best:
        nominal, (f0, mem) = best
        fams["mains"] = dict(nominal_hz=nominal, f0_hz=round(f0, 3), members=[dict(k=k, hz=L["hz"]) for k, L in mem],
                             speed=round(f0 / nominal, 5),
                             speed_range=(round(f0 / (nominal * (1 + MAINS_STRAY)), 4),
                                          round(f0 / (nominal * (1 - MAINS_STRAY)), 4)))
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
        say.append(f"The video's frame rate ({fam['frame']['fps']:g} Hz) is heard.")
    if fam.get("bus"):
        b = fam["bus"]
        say.append(f"An aircraft's 400-Hz power, at {b['f0_hz']:.2f} Hz: the clip plays at {b['speed_range'][0]:.3f}-"
                   f"{b['speed_range'][1]:.3f} of real speed (the bus's steady-state range).")
    if fam.get("mains"):
        m = fam["mains"]
        say.append(f"{m['nominal_hz']:g}-Hz mains, at {m['f0_hz']:.3f} Hz: recorded or copied on ground power; the "
                   f"clip plays at {m['speed_range'][0]:.4f}-{m['speed_range'][1]:.4f} of real speed.")
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
    elif bus and mains:
        head = "The sound was recorded on an aircraft, then copied on the ground."
    elif bus:
        head = "The sound was recorded on an aircraft: it holds the hum of an aircraft's electrical power."
    elif mains:
        head = "The sound was recorded, or copied, on the ground: it holds the hum of mains power."
    elif hum:
        head = "The sound holds a hum of mains power that wavers: it was copied through a tape or record player."
    elif sidebands:
        head = "The sound holds a hum that a tape machine's motor makes rise and fall: it was copied from tape."
    elif retimed:
        head = "The sound holds a hum close to mains power's: the recording may not play at its true speed."
    elif turning:
        head = "Something turning at a steady speed is heard: a propeller, a rotor, a fan or a pump."
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
    if mains:
        lo, hi = mains["speed_range"]
        rest.append(f"Mains power hums at {mains['nominal_hz']:g} Hz. Here it is at {mains['f0_hz']:.3f} Hz: the video "
                    f"plays at {100 * lo:.2f} to {100 * hi:.2f} % of its true speed.")
    if fam.get("frame"):
        rate = fields.get("fps") or fam["frame"]["fps"]
        rest.append(f"The video's own rate of {rate:.4g} frames a second is heard in the sound: video equipment hums at "
                    "it, so the sound has passed through some.")
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
    ap.add_argument("--out", metavar="DIR", help="case directory for results (default: ./<tag>, or $MCDONALD_CASES/<tag>)")
    ap.add_argument("--json", action="store_true",
                    help="print the measurement as JSON on stdout, its numbers as fields (the envelope every command "
                         "prints); everything else goes to stderr")
    args = ap.parse_args()
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
