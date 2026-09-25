# Installing mcdonald

For someone who has not installed a Python program before. It takes about ten minutes, and a
terminal is needed only for this: after it, the program is a window like any other.

What gets installed: **Python** (the language mcdonald is written in), **ffmpeg** (which reads
video), and **mcdonald** itself. At the end, `mcdonald setup` checks all three and says what to
do next.

> Written before anyone had installed it on a Mac or on Windows. If a step here does not
> match what you see, say which step and what you saw.

> **While the repository is private**, pip can fetch it only for someone GitHub knows is allowed:
> ask Jacob to add you as a collaborator (you get an email; accept it), then sign in once from the
> terminal. The easiest way on a Mac is GitHub's own tool: `brew install gh`, then `gh auth login`
> (choose GitHub.com, HTTPS, and "Login with a web browser"). After that the pip line below works
> as written. (With an SSH key on GitHub instead, write `git+ssh://git@github.com/haqqmisra/mcdonald`
> in place of `git+https://github.com/haqqmisra/mcdonald`.)

---

## macOS

1. **Open Terminal**: Applications → Utilities → Terminal.
2. **Homebrew**, which installs the other two. If `brew --version` prints a version, skip this.
   Otherwise paste the line from [brew.sh](https://brew.sh) and follow what it prints (it may
   ask for your password, and to run two more lines at the end: run them).
3. **Python and ffmpeg**:

   ```bash
   brew install python ffmpeg
   ```

4. **mcdonald**:

   ```bash
   python3 -m pip install "mcdonald[gui] @ git+https://github.com/haqqmisra/mcdonald"
   ```

   If pip says `externally-managed-environment`, install it in a place of its own instead:

   ```bash
   python3 -m venv ~/mcdonald-env
   ~/mcdonald-env/bin/pip install "mcdonald[gui] @ git+https://github.com/haqqmisra/mcdonald"
   ~/mcdonald-env/bin/mcdonald setup
   ```

   and start it as `~/mcdonald-env/bin/mcdonald-gui`.
5. **Check**: `mcdonald setup`. If *downloads* says the certificate is not trusted and your
   Python came from python.org rather than Homebrew, open Applications → Python 3.x and
   double-click **Install Certificates.command**, then run `mcdonald setup` again.
6. **Start it**: `mcdonald-gui`.

## Windows

1. **Open PowerShell**: Start menu → type *PowerShell* → open it.
2. **Python and ffmpeg**:

   ```powershell
   winget install Python.Python.3.12
   winget install Gyan.FFmpeg
   ```

   Then **close PowerShell and open it again**, so that it finds what was just installed.
3. **mcdonald**:

   ```powershell
   py -m pip install "mcdonald[gui] @ git+https://github.com/haqqmisra/mcdonald"
   ```

   If pip warns that its `Scripts` folder "is not on PATH", the commands below will not be
   found: run them as `py -m mcdonald.cli setup` and `py -m mcdonald.gui` instead.
4. **Check**: `mcdonald setup`.
5. **Start it**: `mcdonald-gui`.

## Linux

1. **Python and ffmpeg**: Python 3.10 or newer is usually there already (`python3 --version`).
   ffmpeg: `sudo dnf install ffmpeg` (Fedora, with RPM Fusion enabled) or `sudo apt install ffmpeg`
   (Debian, Ubuntu).
2. **mcdonald**:

   ```bash
   python3 -m pip install --user "mcdonald[gui] @ git+https://github.com/haqqmisra/mcdonald"
   ```

   (`externally-managed-environment`: use a venv, as under macOS step 4.)
3. **Check, and add it to the applications menu**: `mcdonald setup --desktop`.
4. **Start it**: from the applications menu, or `mcdonald-gui`.

---

## What `mcdonald setup` checks

| line | what it means | when it says NO |
|---|---|---|
| Python | the version running mcdonald | install Python 3.10 or newer |
| ffmpeg | ffmpeg and ffprobe are found | install ffmpeg (above), then open a new terminal |
| the window | PySide6 is installed, and there is a screen | install with `[gui]`, as above; the command line works without it |
| storage | the folder where videos and their frames are saved, and the room there | set `MCDONALD_HOME`, or change it on the window's first screen |
| catalog | the PURSUE list is there | — |
| downloads | the DVIDS website answers | the internet connection, or (Mac) the certificates |

## Updating

Run the same pip line again with `--upgrade`:

```bash
python3 -m pip install --upgrade "mcdonald[gui] @ git+https://github.com/haqqmisra/mcdonald"
```

## Where things go

Downloaded videos, and each video's frames saved as pictures, go in one folder,
`Documents/mcdonald` unless you choose another on the window's first screen (or set
`MCDONALD_HOME`). A whole video's frames can be several GB; a short segment much less.
