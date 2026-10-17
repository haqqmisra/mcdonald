"""Checks for `mcdonald audio`: planted tones come back as what they are -- a four-bladed propeller with its second
tone, a six-bladed one heard as a single line, a supply as a clock, the codec's frames as the codec -- and what is not
there is not found: noise gives no tones, a wandering series is neither a propeller nor a supply, a lone line near a
blade-pass without its second tone is no reading, and silence is NO POWER. What the window says of it is plain
(`plainly`). Portable: no video data.

    python3 tests/test_audio.py
"""
import json
import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from mcdonald import audio as A  # noqa: E402

RNG = np.random.default_rng(20261016)
FAIL = []
FS = A.FS


def check(cond, label, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'  ' + detail if detail else ''}")
    if not cond:
        FAIL.append(label)
    return cond


def tones(parts, seconds=20.0, noise=1.0, fs=FS, wander=0.0):
    """Noise plus sinusoids [(hz, amplitude)]; `wander` frequency-modulates every tone by that share, slowly."""
    t = np.arange(int(seconds * fs)) / fs
    x = RNG.normal(0, noise, len(t))
    for hz, amp in parts:
        if wander:
            dev = wander * hz * np.sin(2 * np.pi * 0.11 * t + RNG.uniform(0, 6.3))
            phase = 2 * np.pi * np.cumsum(hz + dev) / fs
        else:
            phase = 2 * np.pi * hz * t + RNG.uniform(0, 6.3)
        x += amp * np.sin(phase)
    return x.astype(np.float32)


def read(x, fps=None, rate=48000):
    ls, used, res, peaks = A.lines(x)
    fams, ls = A.families(ls, rate, fps, peaks, used)
    return ls, fams


def test_a_four_bladed_propeller_in_flight():
    """PR117's case: 67.75 Hz and its harmonics, with the T56's second tone at 8.13x."""
    print("a four-bladed propeller in flight, with its second tone")
    F = 67.75
    x = tones([(F, 0.30), (2 * F, 0.20), (3 * F, 0.12), (4 * F, 0.08), (8.129 * F, 0.10)])
    ls, fams = read(x)
    s = fams["series"]
    check(len(s) == 1 and abs(s[0]["f0_hz"] - F) < 0.05, "one series, on the blade-pass",
          ", ".join(f"{q['f0_hz']:.3f}" for q in s))
    p = s[0]["propeller"] if s else None
    m = p["matches_in_flight"] if p else []
    check(len(m) == 1 and m[0]["blades"] == 4, "it is the four-bladed T56 airframe in flight", f"{[q['blades'] for q in m]}")
    c = m[0]["companion"] if m else None
    check(c is not None and c["found_hz"] and abs(c["ratio_heard"] - 8.129) < 0.01, "and its second tone is found at 8.13x",
          f"{c}")
    check(p and any("C-130J" in g["airframe"] for g in p["within_ground_range_of"]),
          "the C-130J on the ground is named as the case a phase of flight must exclude")
    check(p and {a["blades"] for a in p["allows"]} >= {3, 4, 6}, "every blade count the series allows is listed")


def test_a_six_bladed_propeller_heard_alone():
    """An AC-130J in flight: 102 Hz with harmonics too weak for a series; read as the J only with its second tone."""
    print("a six-bladed propeller heard as a single line")
    x = tones([(102.06, 0.25), (550.12, 0.12)])
    ls, fams = read(x)
    check(len(fams["single"]) == 1 and fams["single"][0]["airframe"].startswith("C-130J"),
          "with its second tone at 5.39x it is read as the C-130J", f"{[m['airframe'][:6] for m in fams['single']]}")
    x = tones([(102.06, 0.25)])
    ls, fams = read(x)
    check(not fams["single"] and len(fams["near"]) == 1, "without it, the same line is only near: no reading")
    x = tones([(103.2, 0.25), (5.39 * 103.2, 0.12)])           # +1.2 %: outside the lone line's 0.75 %
    ls, fams = read(x)
    check(not fams["single"], "a lone line 1.2% off is not read as the airframe even with a tone at the ratio")


def test_the_codecs_frames_are_the_codec():
    """AAC's frame products (multiples of 46.875 Hz at 48 kHz) look like machinery and must be named first."""
    print("the codec's frames are the codec")
    fr = 48000 / 1024
    x = tones([(k * fr, 0.15) for k in (2, 3, 4, 5)], noise=0.5)
    ls, fams = read(x)
    c = fams["codec"]
    check(len(c) == 1 and c[0]["sample_rate"] == 48000 and c[0]["this_files_rate"], "one family, at the file's own rate",
          ", ".join(q["what"] for q in c))
    check(not fams["series"] and not fams["single"], "and no series or propeller is made of its lines")
    x = tones([(k * 44100 / 1024, 0.15) for k in (2, 3, 5)], noise=0.5)
    ls, fams = read(x)
    check(any(q["sample_rate"] == 44100 and not q["this_files_rate"] for q in fams["codec"]),
          "a family at another rate is an earlier encode")


def test_a_supply_is_a_clock():
    """PR113's 60-Hz mains (60.011 Hz, odd harmonics) and PR107's 400-Hz bus (399.7 Hz) give their fundamentals."""
    print("a supply is a clock")
    x = tones([(k * 60.011, 0.2 / k ** 0.5) for k in (1, 3, 5, 7, 9)])
    ls, fams = read(x)
    m = fams["mains"]
    check(m is not None and m["nominal_hz"] == 60.0 and abs(m["f0_hz"] - 60.011) < 0.01, "the mains, at its frequency",
          f"{m and m['f0_hz']}")
    check(m is not None and m["speed_range"][0] < 60.011 / 60 < m["speed_range"][1], "and the clip's speed range holds it")
    x = tones([(399.7, 0.15), (3 * 399.7, 0.15), (5 * 399.7, 0.1)])
    ls, fams = read(x)
    b = fams["bus"]
    check(b is not None and abs(b["f0_hz"] - 399.7) < 0.05, "the aircraft's 400-Hz power, at its frequency", f"{b and b['f0_hz']}")


def test_what_wanders_is_neither():
    """PR107's lines near 100, 200, 300 Hz wander by tenths of a hertz: neither mains nor a governed propeller."""
    print("what wanders is neither a supply nor a propeller")
    x = tones([(99.8, 0.3), (199.6, 0.2), (299.4, 0.15)], wander=0.004)
    ls, fams = read(x)
    check(fams["mains"] is None, "not mains")
    check(all(s["propeller"] is None for s in fams["series"]), "and no propeller reading",
          f"{[(s['f0_hz'], s['steady']) for s in fams['series']]}")


def test_noise_gives_nothing():
    """The false-alarm rate: twenty records of noise alone, 20 s each, give no tones at all."""
    print("noise gives nothing")
    n = 0
    for _ in range(20):
        ls, used, res, peaks = A.lines(tones([], seconds=20.0))
        n += len(ls)
    check(n == 0, "no steady tone in 20 records of noise", f"{n}")


def test_a_short_record_is_read_coarsely():
    """PR119 is 2.8 s: three half-length windows, a coarser resolution, the tone still found."""
    print("a short record is read coarsely")
    x = tones([(67.8, 0.4)], seconds=2.8)
    starts, w = A.windows(len(x))
    check(len(starts) == 3 and w == len(x) // 2, "three half-length windows", f"{len(starts)} of {w / FS:.2f} s")
    ls, used, res, peaks = A.lines(x)
    check(any(abs(L["hz"] - 67.8) < 0.5 for L in ls), "and the tone is found", f"{[L['hz'] for L in ls]}")


def test_the_fold():
    """67.75 Hz at 30 frames a second sits at 7.75 Hz, where birds beat; at 29.97, 7.81."""
    print("the heard rhythms folded through the frame rate")
    fields = dict(families=dict(series=[dict(f0_hz=67.75, steady=True, members=[dict(k=1, hz=67.75)])]))
    a30 = [d["hz"] for d in A.lookalike_entries(fields, 30.0)]
    a2997 = [d["hz"] for d in A.lookalike_entries(fields, 30000 / 1001)]
    check(7.75 in a30, "7.75 Hz at 30 frames a second", f"{a30}")
    check(any(abs(h - 7.81) < 0.01 for h in a2997), "7.81 Hz at 29.97", f"{a2997}")


def test_what_looks_like_an_airframe_but_is_not():
    """The traps the corpus pass found: the mains' sidebands (Apollo 14's tapes: 60.15 -+ 7.5 Hz, the upper one at
    67.7, with a tone at its 8.13x) are no T56; a hum that wanders is no clock; odd harmonics only (PR111's 243.78)
    are an electrical waveform; two encodes' frame products mix (PR36: 187.5 - 86.13 = 101.37); a series 3 % from
    60 Hz (Apollo 12's 58.07) may be retimed mains; and 2x and 6x 29.97 without 29.97 are not the frame rate."""
    print("what looks like an airframe, a clock or a machine, and is not")
    m = 60.146
    x = tones([(m, 0.4), (3 * m, 0.2), (m - 7.52, 0.15), (m + 7.52, 0.15), (8.129 * (m + 7.52), 0.08)])
    ls, fams = read(x)
    check(fams["sidebands"] and not fams["single"] and not any((s.get("propeller") or {}).get("matches_in_flight") for s in fams["series"]),
          "the mains' sidebands are labelled, and no airframe is read from them",
          f"{[(sb['harmonic_hz'], sb['offset_hz']) for sb in fams['sidebands']]}; single {len(fams['single'])}")
    x = tones([(60.06, 0.4), (60.06 - 7.5, 0.12), (60.06 + 7.5, 0.18), (8.129 * (60.06 + 7.5), 0.08)])
    ls, fams = read(x)
    check(not fams["single"] and not any(q.get("identified") for s in fams["series"] for q in (s.get("propeller") or {}).get("matches_in_flight", [])),
          "with only the hum's fundamental heard, its sidebands are still no airframe (the planted-tone study's case)",
          f"sidebands {[(sb['harmonic_hz'], sb['offset_hz'], sb.get('mirror_as')) for sb in fams['sidebands']]}")
    x = tones([(60.1, 0.5), (180.3, 0.2)], wander=0.006)
    ls, fams = read(x)
    check(fams["mains"] is None and fams["hum"] is not None, "a wandering hum near 60 Hz is hum through a transport, not a clock",
          f"{fams['hum']}")
    x = tones([(k * 243.78, 0.3 / k) for k in (1, 3, 5, 7)])
    ls, fams = read(x)
    s = fams["series"]
    check(len(s) == 1 and s[0]["odd_only"] and s[0]["propeller"] is None, "odd harmonics only: an electrical waveform, no propeller")
    fr1, fr2 = 46.875, 44100 / 1024
    x = tones([(k * fr1, 0.2) for k in (2, 3, 4, 5)] + [(2 * fr2, 0.15), (4 * fr1 - 2 * fr2, 0.15), (fr1 + 2 * fr2, 0.15),
                                                        (5 * fr1 - 2 * fr2, 0.15)], noise=0.5)
    ls, fams = read(x)
    cc = fams.get("codec_cross") or []
    check(len(cc) == 1 and cc[0]["sample_rate"] == 44100 and all(L["is"] for L in ls),
          "an earlier 44.1-kHz encode's products mixed with the 48-kHz frames are named, and nothing is left over",
          f"{[c['what'] for c in cc]}; unexplained {[L['hz'] for L in ls if not L['is']]}")
    x = tones([(58.07, 0.4), (116.14, 0.2), (174.21, 0.15)])
    ls, fams = read(x)
    s = fams["series"]
    check(len(s) == 1 and s[0]["mains_if"] and abs(s[0]["mains_if"]["speed"] - 0.968) < 0.002,
          "a steady series 3 % below 60 Hz is offered as mains retimed (0.968 of real speed)", f"{s and s[0].get('mains_if')}")
    x = tones([(59.94, 0.3), (179.82, 0.2)])
    ls, fams = read(x, fps=30000 / 1001)
    check(fams["frame"] is None, "2x and 6x 29.97 Hz without 29.97 are not the video's frame rate")


def test_a_blade_pass_alone_identifies_nothing():
    """An MQ-9 heard from the ground hums over a T56's 68 Hz with its own second tone at 9.00x: the blade-pass matches,
    but without the T56's 8.13x tone nothing is identified. An H-60's rotors (17.23 Hz, tail at 4.61x) are identified."""
    print("a blade-pass alone identifies nothing; a rotor with its tail rotor does")
    F = 68.0
    x = tones([(F, 0.3), (2 * F, 0.2), (3 * F, 0.12), (9.0 * F, 0.1)])
    ls, fams = read(x)
    m = [q for s in fams["series"] for q in (s.get("propeller") or {}).get("matches_in_flight", [])]
    check(m and not any(q["identified"] for q in m) and not fams["single"],
          "the T56's blade-pass with a 9.00x tone matches but is not identified", f"{[(q['airframe'][:6], q['identified']) for q in m]}")
    x = tones([(k * 17.23, 0.3 / k ** 0.5) for k in (1, 2, 3, 4)] + [(79.45, 0.2)])
    ls, fams = read(x)
    m = [q for s in fams["series"] for q in (s.get("propeller") or {}).get("matches_in_flight", [])]
    check(any(q["airframe"].startswith("H-60") and q["identified"] for q in m),
          "an H-60's main rotor with its tail rotor at 4.61x is identified", f"{[(q['airframe'][:6], q['identified']) for q in m]}")


# the trade's words the window does not use (tests/test_gui.py's TRADE_WORDS, and this tool's own)
TRADE = ("clip", "fps", "codec", "harmonic", "blade-pass", "sideband", "doppler", "companion", "dbfs", "encode", "bus",
         "airframe", "series", "alias")


def plain(x, fps=30.0):
    """What the window would say of a drawn sound: `plainly` on the fields `measure` makes."""
    ls, used, res, peaks = A.lines(x)
    fams, ls = A.families(ls, 48000, fps, peaks, used)
    f = dict(audio_streams=[dict(codec="aac", sample_rate=48000, channels=1)], fps=fps, silent=False, read_s=len(x) / FS,
             duration_s=len(x) / FS, windows=used, lines=ls, families=fams)
    f["lookalikes"] = A.lookalike_entries(f, fps)
    return A.plainly(f)


def test_what_the_window_says():
    """The window's page of the sound (sound_qt) leads with one plain sentence, written from the same fields as the
    finding: the aircraft named only with its second tone, the power a recording was made on, and nothing where
    nothing is -- in words without the trade's."""
    print("what the window says, plainly")
    said = []
    F = 68.0
    got = plain(tones([(F, 0.3), (2 * F, 0.2), (3 * F, 0.12), (8.129 * F, 0.1)]))
    said.append(got)
    check(got[0] == "The sound names the aircraft: a C-130 with four-bladed propellers, in flight."
          and any("8.12" in r or "8.13" in r for r in got[1]), "a T56 with its second tone: the aircraft, named first", got[0])
    got = plain(tones([(F, 0.3), (2 * F, 0.2), (3 * F, 0.12), (9.0 * F, 0.1)]))
    said.append(got)
    check(got[0].startswith("Something turning at a steady speed") and any("MQ-9" in r and "no aircraft is named" in r
                                                                           for r in got[1]),
          "the same hum with an MQ-9's second tone: something turning, and no aircraft named", got[0])
    got = plain(tones([(399.7, 0.15), (3 * 399.7, 0.15), (5 * 399.7, 0.1)]))
    said.append(got)
    check(got[0].startswith("The sound was recorded on an aircraft") and any("399.70 Hz" in r for r in got[1]),
          "an aircraft's power: recorded on an aircraft, at its true speed give or take", got[0])
    got = plain(tones([(399.7, 0.15), (3 * 399.7, 0.15), (5 * 399.7, 0.1)] + [(k * 60.011, 0.2 / k ** 0.5) for k in (1, 3, 5, 7)]))
    said.append(got)
    check(got[0] == "The sound was recorded on an aircraft, then copied on the ground.",
          "an aircraft's power under mains power: recorded aboard, copied on the ground", got[0])
    got = plain(tones([]))
    said.append(got)
    check(got[0] == "There is sound, but no steady tone in it.", "noise: no steady tone", got[0])
    got = A.plainly(dict(audio_streams=[dict(codec="aac", sample_rate=48000, channels=1)], silent=True))
    said.append(got)
    check(got[0].startswith("This video's sound is silent"), "silence", got[0])
    got = A.plainly(dict(audio_streams=[]))
    check(got[0] == "This video has no sound track.", "no sound track", got[0])
    words = " ".join(h + " " + " ".join(r) for h, r in said).lower()
    import re
    found = [w for w in TRADE if re.search(r"\b" + re.escape(w) + r"s?\b", words)]
    check(not found, "in words without the trade's", ", ".join(found))


def _wav(path, x, fs=48000):
    peak = float(np.max(np.abs(x)))
    y = np.clip(x / (peak * 1.25), -1, 1) if peak > 1e-6 else np.zeros_like(x)     # silence stays silence
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(fs)
        w.writeframes((y * 32767).astype("<i2").tobytes())


def test_the_command():
    """`mcdonald audio --json` on a drawn clip with a propeller's sound, and on one whose sound is silence."""
    print("the command, end to end")
    with tempfile.TemporaryDirectory() as d:
        t = np.arange(int(12 * 48000)) / 48000
        x = RNG.normal(0, 1, len(t)) + sum(a * np.sin(2 * np.pi * k * 68.0 * t) for k, a in ((1, 0.3), (2, 0.2), (3, 0.12)))
        x += 0.1 * np.sin(2 * np.pi * 8.129 * 68.0 * t)
        _wav(os.path.join(d, "s.wav"), x)
        _wav(os.path.join(d, "z.wav"), np.zeros(int(6 * 48000)))
        for name, wav, secs in (("prop.mp4", "s.wav", 12), ("quiet.mp4", "z.wav", 6)):
            subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size=160x120:rate=30:d={secs}",
                            "-i", os.path.join(d, wav), "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                            os.path.join(d, name)], check=True)
        env = {**os.environ, "PYTHONPATH": os.path.join(HERE, "..", "src")}
        r = subprocess.run([sys.executable, "-m", "mcdonald.cli", "audio", os.path.join(d, "prop.mp4"), "--json", "--out", d],
                           capture_output=True, text=True, env=env)
        e = json.loads(r.stdout) if r.stdout.strip() else {}
        s = (e.get("results", {}).get("families") or {}).get("series") or []
        check(r.returncode == 0 and e.get("command") == "audio", "it runs and prints the envelope", f"exit {r.returncode}")
        check(len(s) == 1 and abs(s[0]["f0_hz"] - 68.0) < 0.1 and s[0]["propeller"]["matches_in_flight"],
              "the drawn propeller is found and matched", f"{[q['f0_hz'] for q in s]}")
        check(any(abs(d_["hz"] - 8.0) < 0.05 for d_ in e.get("results", {}).get("lookalikes", [])),
              "its fold at 30 frames a second (8 Hz) is a look-alike")
        check(e.get("results", {}).get("said") and e.get("files"), "with what it said, and its figure")
        r = subprocess.run([sys.executable, "-m", "mcdonald.cli", "audio", os.path.join(d, "quiet.mp4"), "--json", "--out", d],
                           capture_output=True, text=True, env=env)
        e = json.loads(r.stdout) if r.stdout.strip() else {}
        check(r.returncode == 5 and e.get("no_power"), "silence is NO POWER, exit 5", f"exit {r.returncode}, {e.get('no_power')}")


def main():
    for t in (test_a_four_bladed_propeller_in_flight, test_a_six_bladed_propeller_heard_alone,
              test_the_codecs_frames_are_the_codec, test_a_supply_is_a_clock, test_what_wanders_is_neither,
              test_noise_gives_nothing, test_a_short_record_is_read_coarsely, test_the_fold,
              test_what_looks_like_an_airframe_but_is_not, test_a_blade_pass_alone_identifies_nothing,
              test_what_the_window_says, test_the_command):
        t()
    print(f"\n{'OK' if not FAIL else 'FAILED'}: {len(FAIL)} failing check(s)" + ("" if not FAIL else "\n  " + "\n  ".join(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
