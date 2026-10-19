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

Where the sound plays (Jacob, 2026-10-19: "a drop-down menu for the user to choose the audio device, in case they want
to adjust to something other than the system default"). ffplay plays through SDL, and SDL opens the output named in
SDL_AUDIO_DEVICE_NAME wherever the program asks for none, as ffplay does: SDL2, and sdl2-compat over SDL3 (Fedora's),
alike. The name must be SDL's own, to the letter -- one it does not know is no sound at all ("audio open failed") -- so
`outputs` asks the SDL library ffplay is linked against for them. Where SDL is built into ffplay (the Windows builds)
they come from where SDL's own come from, the sound endpoints' names in the registry ("Speakers (Realtek(R) Audio)");
on a Mac where the library is not found, from system_profiler. An output the player then refuses -- unplugged since, or
named otherwise -- is played around: the sound starts again on the system's own, and `refused` keeps it for the session.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

from . import audio

PROGRAM = "ffplay"
SPEEDS_OK = (0.5, 2.0)          # one atempo's range in every ffmpeg since 2.x; slower or faster is a chain of them
DEVICE_VAR = "SDL_AUDIO_DEVICE_NAME"          # SDL's: the output it opens where the program asks for none (ffplay never asks)
REFUSAL = ("audio open failed", "SDL_OpenAudio")       # what ffplay says when SDL will not open the output named
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0     # no console over the window
refused = set()                 # outputs ffplay would not open, this session: the sound is played around them


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


def outputs(program=None):
    """The sound outputs ffplay can be told to play to, by SDL's own names and in SDL's order; [] where they cannot be
    listed, and then the system's own is the only choice there is."""
    program = program or available()
    if program is None:
        return []
    lib = sdl_library(program)
    names = _sdl_outputs(lib) if lib else None
    if names is not None:
        return names
    if sys.platform == "win32":
        return _windows_outputs()
    if sys.platform == "darwin":
        return _mac_outputs()
    return []


def sdl_library(program):
    """The SDL library `program` (ffplay) is linked against, or None: where SDL is built into it, as in the Windows
    builds, or where it cannot be found."""
    path = os.path.realpath(program)
    if sys.platform == "win32":
        dll = os.path.join(os.path.dirname(path), "SDL2.dll")         # a "shared" build has it beside ffplay.exe
        return dll if os.path.exists(dll) else None
    tool = "otool" if sys.platform == "darwin" else "ldd"
    if shutil.which(tool):
        try:
            r = subprocess.run([tool, "-L", path] if tool == "otool" else [tool, path],
                               capture_output=True, encoding="utf-8", errors="replace", timeout=10)
            for line in r.stdout.splitlines():
                m = re.search(r"(/\S*libSDL2[-.]\S*)", line)
                if m and os.path.exists(m.group(1)):
                    return m.group(1)
        except (OSError, subprocess.SubprocessError):
            pass
    if sys.platform == "darwin":                      # Homebrew's, beside the ffplay it put there: <prefix>/lib
        for root in (os.path.dirname(os.path.dirname(program)), os.path.dirname(os.path.dirname(path))):
            lib = os.path.join(root, "lib", "libSDL2-2.0.0.dylib")
            if os.path.exists(lib):
                return lib
    import ctypes.util
    return ctypes.util.find_library("SDL2-2.0" if sys.platform.startswith("linux") else "SDL2")


_LIST = """
import ctypes, json, sys
lib = ctypes.CDLL(sys.argv[1])
lib.SDL_GetAudioDeviceName.restype = ctypes.c_char_p
names = []
if lib.SDL_Init(0x10) == 0:                           # SDL_INIT_AUDIO
    for i in range(max(0, lib.SDL_GetNumAudioDevices(0))):
        name = lib.SDL_GetAudioDeviceName(i, 0)
        if name:
            names.append(name.decode("utf-8", "replace"))
    lib.SDL_Quit()
print(json.dumps(names))
"""


def _sdl_outputs(lib):
    """SDL's own list of outputs, from `lib`, asked in a Python of its own (SDL started in the window's process would
    be the window's to stop, and takes the quit signals); None if it could not be asked."""
    try:
        r = subprocess.run([sys.executable, "-I", "-c", _LIST, str(lib)], capture_output=True, encoding="utf-8",
                           errors="replace", timeout=15, creationflags=NO_WINDOW)
        names = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None
    return [n for n in names if isinstance(n, str) and n] if isinstance(names, list) else None


def dedupe(names):
    """Names as SDL lists them: the second of two the same is "name (2)", the third "name (3)"."""
    seen, out = {}, []
    for n in names:
        seen[n] = seen.get(n, 0) + 1
        out.append(n if seen[n] == 1 else f"{n} ({seen[n]})")
    return out


# the sound endpoints' names, as Windows keeps them: a description ("Speakers") and its device's ("Realtek(R) Audio"),
# which together are the name SDL's WASAPI reads (PKEY_Device_FriendlyName: "Speakers (Realtek(R) Audio)")
RENDER = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render"
DESCRIPTION, INTERFACE = "{a45c254e-df1c-4efd-8020-67d146a850e0},2", "{b3f8fa53-0004-438e-9003-51a46e139bfc},6"


def _windows_outputs():
    try:
        import winreg
        render = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, RENDER)
    except (ImportError, OSError):
        return []
    names, i = [], 0
    with render:
        while True:
            try:
                key = winreg.EnumKey(render, i)
            except OSError:
                break
            i += 1
            try:
                with winreg.OpenKey(render, key) as dev:
                    if winreg.QueryValueEx(dev, "DeviceState")[0] & 0xF != 1:      # DEVICE_STATE_ACTIVE: there, and on
                        continue
                    with winreg.OpenKey(dev, "Properties") as props:
                        desc = winreg.QueryValueEx(props, DESCRIPTION)[0]
                        try:
                            where = winreg.QueryValueEx(props, INTERFACE)[0]
                        except OSError:
                            where = ""
            except OSError:
                continue
            names.append(f"{desc} ({where})" if where else str(desc))
    return dedupe(names)


def _mac_outputs():
    try:
        r = subprocess.run(["system_profiler", "SPAudioDataType", "-json"], capture_output=True, encoding="utf-8",
                           errors="replace", timeout=30)
        top = json.loads(r.stdout or "{}").get("SPAudioDataType") or []
    except (OSError, subprocess.SubprocessError, ValueError, AttributeError):
        return []
    return dedupe([d["_name"] for t in top for d in t.get("_items") or []
                   if isinstance(d, dict) and d.get("_name") and "coreaudio_device_output" in d])


def environment(device):
    """What ffplay is started with to play to `device`: None (the window's own environment) for the system's own."""
    return dict(os.environ, **{DEVICE_VAR: device}) if device else None


def tone(program=None):
    """What plays a short tone, 0.8 s of 660 Hz faded in and out: Preferences' "Play a test sound"."""
    return [program or available() or PROGRAM, "-nodisp", "-autoexit", "-loglevel", "error", "-nostats", "-f", "lavfi",
            "-i", "sine=frequency=660:duration=0.8", "-af", "afade=t=in:d=0.04,afade=t=out:st=0.65:d=0.15"]


def try_output(device, program=None, timeout=10):
    """The tone on `device` (None: the system's own), waited for: True once it has played, False if the player would
    not open the output (which is then `refused`), None with no ffplay."""
    if (program or available()) is None:
        return None
    try:
        r = subprocess.run(tone(program), stdin=subprocess.DEVNULL, capture_output=True, env=environment(device),
                           timeout=timeout, creationflags=NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return False
    if any(x in (r.stderr or b"").decode("utf-8", "replace") for x in REFUSAL):
        if device:
            refused.add(device)
        return False
    refused.discard(device)                           # there again (plugged back in): played to from now on
    return True


class Speaker:
    """One video's sound, started and stopped with the picture. `play` stops what was playing first, so a change of
    speed or a jump is the sound started again from the new place. `device` is the output it plays to (None: the
    system's own); one the player will not open is played around, on the system's own (`refused`)."""

    def __init__(self, video, program=None, device=None):
        self.video, self.program, self.device = str(video), program, device
        self.proc, self.last, self.on = None, None, None       # `on`: the output the sound is going to now
        self._lock = threading.RLock()                # the GUI's play and stop, and the thread that hears a refusal

    def play(self, t, until=None, speed=1.0):
        with self._lock:
            self.stop()
            device = self.device if self.device and self.device not in refused else None
            self.last = command(self.video, t, until, speed, self.program)
            try:
                self.proc = subprocess.Popen(self.last, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                             stderr=subprocess.PIPE if device else subprocess.DEVNULL,
                                             env=environment(device), creationflags=NO_WINDOW)
            except OSError:                           # ffplay gone since it was found
                self.proc = None
                return False
            self.on = device
            if device:
                threading.Thread(target=self._watch, args=(self.proc, device, t, until, speed, time.monotonic()),
                                 daemon=True, name="mcdonald-speaker").start()
            return True

    def _watch(self, proc, device, t, until, speed, started):
        """What ffplay says while it plays to `device`: if it could not open it, the sound starts again on the
        system's own, from where the picture has got to."""
        for line in iter(proc.stderr.readline, b""):
            if any(x.encode() in line for x in REFUSAL):
                refused.add(device)
                with self._lock:
                    if self.proc is proc:             # still the one that was to play
                        self.play(t + (time.monotonic() - started) * speed, until, speed)
                break
        try:
            proc.stderr.close()
        except OSError:
            pass

    def playing(self):
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
        with self._lock:
            p, self.proc = self.proc, None
            if p is not None and p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
