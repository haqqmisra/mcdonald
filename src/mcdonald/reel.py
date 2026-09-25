"""A clip to be watched before any of it is extracted: frames by number, from an ffmpeg pipe.

The package measures on lossless frames on disk, and a whole 1080p clip of them is a
gigabyte or more. So someone opening a clip is asked which part of it -- and to answer
they have to watch it first: play it, go back, step a frame at a time round the place
where something happens. `Reel` is what they watch. It has no window in it; the range
chooser (`mark_qt.RangeChooser`) is a player over it, as `mcdonald look CLIP` is the
same look for something with no display.

How. One ffmpeg at a time, started *at* a frame by seeking to half a frame before its
time, writing raw RGB at a reduced width to a pipe that one thread reads in order.
Going forward is reading on, at some 300 frames a second for 1080p at 960 wide. Going
anywhere else is a new ffmpeg, about half a second, of which a quarter is ffmpeg
starting at all. Going backward cannot be read from a pipe, so a miss behind the
position starts a chunk earlier and reads up to it, and the chunk before that is
fetched before it is needed: steps back, and playing backward, are served from memory.
Someone who has stopped on a frame may step either way, so a player that is not playing
asks for what is `around`, and the half chunk behind is fetched once what is ahead is in.
What is kept is what is nearest the frame wanted, counting a frame behind the direction
of travel as three times as far: least recently used would throw away, on turning
round, exactly the frames about to be shown.

Frame numbers are the package's: 1-based, frame n at (n - 1) / fps. `-ss` before `-i`
is accurate to the frame when ffmpeg is decoding, and the first frame out is the first
whose time is not before the seek, so a seek to (n - 1.5) / fps gives frame n -- as long
as the frames come at a constant rate from time zero. `exact` says whether the file
claims so. One frame out per frame in (`-vsync 0`, `-fps_mode passthrough` since ffmpeg 5.1:
`clip.every_frame`) matters as much: left to itself ffmpeg writes a constant rate, and
in a file with a sound track it finds the first frame half a frame late for that and
fills the gap with a copy -- so the first frame is right and every one after it is a
frame out. Checking the first frame of each seek did not show that; checking fourteen in
a row did. (Without a sound track it does not happen, which is why the test clip has one.) Where it does, the numbers are the ones extraction will give: checked on
PR113 against its extracted frames 100, 408, 2500 and 5000, and pinned by
tests/test_measurement.py on a 30000/1001 clip. Where it does not, they are good to a
frame or so, which is enough to choose a range by, and the chooser says "about".
"""
import subprocess
import threading
from fractions import Fraction
from pathlib import Path

from .clip import every_frame


class Reel:
    NEAR = 60                   # frames it is quicker to read through than to seek past: 0.2 s against 0.5
    AHEAD = 45                  # read this far past the frame wanted, going forward
    CHUNK = 60                  # going backward, a miss starts this far before it

    def __init__(self, video, info, width=960, budget_mb=256, on_frame=None):
        """`info` is clip.probe()'s. `on_frame(n)` is called, on the reading thread, for
        every frame as it arrives."""
        self.video, self.fps = Path(video), Fraction(info["fps"])
        self.total = info["nb_frames"] or int(round(info["duration"] * float(self.fps)))
        self.last = self.total                        # lowered, if the file ends before it said it would
        self.w = max(2, min(int(width), info["width"]) // 2 * 2)
        self.h = max(2, int(round(self.w * info["height"] / info["width"] / 2)) * 2)
        self.size = self.w * self.h * 3
        s = info.get("stream", {})
        self.exact = (s.get("avg_frame_rate") in (None, s.get("r_frame_rate"))
                      and float(s.get("start_time") or 0) == 0.0)
        self.error = None                             # why there is no picture, once that is known
        self.on_frame = on_frame
        self._have, self._keep = {}, max(budget_mb * 2 ** 20 // self.size, 2 * self.CHUNK + self.AHEAD)
        self._cv = threading.Condition()
        self._want, self._dir, self._around = None, +1, False
        self._proc, self._pos, self._began, self._closed = None, None, None, False
        self._hunt, self._back = None, self.CHUNK     # looking for an end that came before the header said
        self.seeks = 0                                # how many times ffmpeg was started: what a test can count
        self._thread = threading.Thread(target=self._run, daemon=True, name="mcdonald-reel")
        self._thread.start()

    # -- what a player asks ---------------------------------------------------------------------
    def want(self, n, direction=+1, around=False):
        """Frame n is wanted, and the frames after it (or, going backward, before it) soon.
        `around`: and those just behind it as well, for someone stopped here."""
        with self._cv:
            self._want, self._dir = max(1, min(int(n), self.last)), (1 if direction >= 0 else -1)
            self._around = bool(around)
            self._cv.notify()

    def get(self, n):
        """Frame n as h * w * 3 bytes of RGB, or None if it has not been read yet."""
        with self._cv:
            return self._have.get(n)

    def nearest(self, n, lo, hi):
        """The frame in memory nearest n within lo..hi, or None: what to show while n is on its way."""
        with self._cv:
            near = [k for k in self._have if lo <= k <= hi]
        return min(near, key=lambda k: abs(k - n)) if near else None

    def cached(self):
        with self._cv:
            return sorted(self._have)

    def close(self):
        with self._cv:
            self._closed = True
            self._end()
            self._cv.notify()

    # -- the reading thread ---------------------------------------------------------------------
    def _job(self):
        """What to do next, with the lock held: None, "read", or a frame to start ffmpeg at."""
        n, d = self._want, self._dir
        if self.error:
            return None
        if self._hunt is not None:                    # read to the end of the file, whatever is wanted meanwhile
            return "read" if self._proc is not None else self._hunt
        if n is None:
            return None
        n, have = min(n, self.last), self._have
        if n not in have:
            return self._reach(n, n if d > 0 else max(1, n - self.CHUNK))
        if d > 0:                                     # going forward: the first frame not yet here, up to AHEAD on
            m = next((k for k in range(n + 1, min(n + self.AHEAD, self.last) + 1) if k not in have), None)
            if m is not None:
                return self._reach(m, m)
            if self._around and n > 1 and n - 1 not in have:
                return self._reach(n - 1, max(1, n - self.CHUNK // 2))
            return None
        lo = n                                        # going backward: keep a chunk in hand below the position
        while lo - 1 in have:
            lo -= 1
        if lo == 1 or n - lo >= self.CHUNK:
            return None
        return self._reach(lo - 1, max(1, lo - self.CHUNK))

    def _reach(self, m, start):
        """Read on, if that comes to frame m soon; else start ffmpeg at `start`."""
        return "read" if self._proc is not None and self._pos <= m <= self._pos + self.NEAR else start

    def _run(self):
        while True:
            with self._cv:
                job = self._job()
                while not self._closed and job is None:
                    self._cv.wait()
                    job = self._job()
                if self._closed:
                    return
                if job != "read":
                    self._start(job)
                proc, pos = self._proc, self._pos
            try:
                data = proc.stdout.read(self.size)    # not under the lock: this is where the time goes
            except (OSError, ValueError):             # closed under us
                data = b""
            with self._cv:
                if self._closed or proc is not self._proc:
                    continue
                if len(data) < self.size:             # the file has ended, or ffmpeg could not read it
                    self._end()
                    self._ended(pos)
                    continue
                self._have[pos] = data
                while len(self._have) > self._keep:
                    del self._have[max(self._have, key=self._far)]
                self._pos = pos + 1
                if self._pos > self.last:
                    self._end()
                    self._hunt = None
            if self.on_frame:
                self.on_frame(pos)

    def _far(self, k):
        """How far frame k is from the one wanted, a frame behind the direction of travel
        counting three times: what is furthest is what memory gives up first."""
        along = (k - (self._want or k)) * self._dir
        return along if along >= 0 else -3 * along

    def _start(self, n):
        self._end()
        t = max(0.0, float((n - Fraction(3, 2)) / self.fps))
        self._proc = subprocess.Popen(["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{t:.6f}", "-i", str(self.video),
                                       "-an", "-sn", "-dn", "-vf", f"scale={self.w}:{self.h}", *every_frame(),
                                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._pos = self._began = n
        self.seeks += 1

    def _end(self):
        if self._proc is not None:
            self._proc.kill()
            self._proc.stdout.close()
            self._proc.wait()
            self._proc = None

    def _ended(self, pos):
        """ffmpeg stopped before frame `pos`. If it had given frames, that is the end of the
        file -- which can come before its header said, where the count is from a duration
        that the sound track set. If it gave none the end is somewhere before where it
        started: go back and read up to it. None from frame 1 is a file with no picture."""
        if pos > self._began:
            self.last, self._hunt, self._back = min(self.last, pos - 1), None, self.CHUNK
        elif self._began <= 1:
            self.error = f"ffmpeg could not read frames from {self.video.name}"
        else:
            self._hunt, self._back = max(1, self._began - self._back), self._back * 4
        if self._want is not None:
            self._want = min(self._want, self.last)
