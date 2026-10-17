"""A video's sound, played beside the window's own player, and whether there is any to play.

The window shows frames on its own clock (`QtMarker._tick`: a frame the decoder is late with is skipped, never waited
for), so sound played at true speed from the same moment stays with the picture. The segment chooser waits for a late
frame instead (a frame skipped there is a frame nobody looked at), so its sound starts once the picture moves and is
started again from the frame on the screen when the two drift apart (`mark_qt.SoundControl.follow`). The sound is played by ffplay, which
comes with ffmpeg wherever the install notes get it (Homebrew, the Windows build, apt, dnf): `-nodisp` (no window of
its own), `-vn` (the sound only), from the frame on the screen, at the window's speed (`atempo`, which keeps the pitch).
Qt's own player is in PySide6's Addons, another ~175 MB the package does not install (pyproject.toml), so there is no
new dependency. Without ffplay there is no sound, and the window says so; nothing else changes.

`sound_of` says whether a video has sound worth playing or reading: no sound track, a track of digital silence (most
sensor videos), or sound. No toolkit is imported here: the window binds it, and the tests drive it without one.
"""
import shutil
import subprocess
import sys

from . import audio

PROGRAM = "ffplay"
SPEEDS_OK = (0.5, 2.0)          # one atempo's range in every ffmpeg since 2.x; slower or faster is a chain of them


def available():
    """ffplay, if it is installed: the path, or None."""
    return shutil.which(PROGRAM)


def tempo(speed):
    """The atempo chain that plays at `speed` with the pitch kept: '' at true speed."""
    speed, parts = float(speed), []
    while speed < SPEEDS_OK[0] - 1e-9:
        parts.append(SPEEDS_OK[0])
        speed /= SPEEDS_OK[0]
    while speed > SPEEDS_OK[1] + 1e-9:
        parts.append(SPEEDS_OK[1])
        speed /= SPEEDS_OK[1]
    if abs(speed - 1.0) > 1e-9:
        parts.append(speed)
    return ",".join(f"atempo={p:.6g}" for p in parts)


def command(video, t, until=None, speed=1.0, program=None):
    """What plays the sound of `video` from `t` seconds (to `until`, if given) at `speed`."""
    cmd = [program or available() or PROGRAM, "-nodisp", "-autoexit", "-vn", "-sn", "-loglevel", "error", "-nostats",
           "-ss", f"{max(0.0, t):.3f}"]
    if until is not None:
        cmd += ["-t", f"{max(0.0, until - t):.3f}"]
    af = tempo(speed)
    if af:
        cmd += ["-af", af]
    return cmd + [str(video)]


def sound_of(video):
    """'none' (no sound track), 'silent' (digital silence all through what `audio` reads), or 'sound'."""
    try:
        if not audio.probe(str(video))["audio"]:
            return "none"
        x = audio.decode(str(video), 0.0, audio.MAX_S)          # as `audio` reads it, so the two agree on silence
    except Exception:                                 # unreadable, or no ffmpeg: nothing to play
        return "none"
    if not len(x):
        return "silent"
    return "silent" if audio.loudness(x)[0] < audio.SILENT_DBFS else "sound"


class Speaker:
    """One video's sound, started and stopped with the picture. `play` stops what was playing first, so a change of
    speed or a jump is the sound started again from the new place."""

    def __init__(self, video, program=None):
        self.video, self.program, self.proc, self.last = str(video), program, None, None

    def play(self, t, until=None, speed=1.0):
        self.stop()
        self.last = command(self.video, t, until, speed, self.program)
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0     # no console over the window
        try:
            self.proc = subprocess.Popen(self.last, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL, creationflags=flags)
        except OSError:                               # ffplay gone since it was found
            self.proc = None
        return self.proc is not None

    def playing(self):
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
        p, self.proc = self.proc, None
        if p is not None and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
