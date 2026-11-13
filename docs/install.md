# Installing mcdonald

For someone who has not installed a Python program before. It takes about ten minutes, and a
terminal is needed only for this: after it, the program is a window like any other.

What gets installed: **Python** (the language mcdonald is written in), **ffmpeg** (which reads
video), and **mcdonald** itself. At the end, `mcdonald setup` checks all three and says what to
do next.

> On a Mac and on Windows these steps have so far been run only by automatic tests on GitHub's machines, not by a person.
> If a step here does not match what you see, say which step and what you saw.

---

## macOS

1. **Open Terminal**: Applications → Utilities → Terminal.
2. **Homebrew**, which installs the other two. If `brew --version` prints a version, skip this.
   Otherwise paste the line from [brew.sh](https://brew.sh) and follow what it prints. It may
   ask for your password, and at the end it may ask you to run two more lines: run them.
3. **Python and ffmpeg**:

   ```bash
   brew install python ffmpeg
   ```

4. **mcdonald**:

   ```bash
   python3 -m pip install mcdonald
   ```

   If pip says `externally-managed-environment`, install it in a place of its own instead:

   ```bash
   python3 -m venv ~/mcdonald-env
   ~/mcdonald-env/bin/pip install mcdonald
   ~/mcdonald-env/bin/mcdonald setup
   ```

   and start it as `~/mcdonald-env/bin/mcdonald-gui`.
5. **Check**: `mcdonald setup`. If its *downloads* line says the certificate is not trusted, and
   your Python came from python.org rather than Homebrew, there is one more step. Open
   Applications → Python 3.x and double-click **Install Certificates.command**, then run
   `mcdonald setup` again.
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
   py -m pip install mcdonald
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
   python3 -m pip install --user mcdonald
   ```

   (`externally-managed-environment`: use a venv, as under macOS step 4.)
3. **Check**: `mcdonald setup`. On a Linux desktop it also puts mcdonald in the applications menu.
4. **Start it**: from the applications menu, or `mcdonald-gui`.

---

## A graphics card (optional)

mcdonald never needs a graphics card (GPU). If the computer has one made by NVIDIA, the slowest steps can run on it
and finish many times sooner. They give the same measurement as on the CPU. This works on Linux and Windows. On a
Mac, and with a card from AMD or Intel, every step runs on the CPU for now.

1. **The card's driver** from NVIDIA has to be installed. If the card already shows pictures at its full resolution,
   it usually is. `nvidia-smi` in a terminal prints the card's name when the driver is there.
2. **The add-on.** In the window, open **Edit → Preferences…** (on a Mac, mcDonald → Settings). Beside the
   graphics card's name there is a button, **Install the add-on**. It downloads 1.4 to 1.8 GB, which takes a few
   minutes, and mcDonald stays open meanwhile. The card is used from the next step on. In a terminal, the same is:

   ```bash
   mcdonald setup --install-gpu
   ```

   Both choose the build for the card's driver, and replace nothing that is already installed.
3. **Check**: `mcdonald setup` has a line "graphics card" that names the card in use, and Preferences lets you
   choose it.

The add-on is CuPy, a library that does on a card what NumPy does on the CPU, with NVIDIA's CUDA libraries (CUDA is
NVIDIA's software for computing on a card). It runs on any NVIDIA card from the GeForce GTX 900 series (2014) on.
It takes 1.9 to 2.8 GB on the disk. Four things to know:

- To install it by hand instead: `python3 -m pip install "mcdonald[gpu]"` (on Windows, `py -m pip install
  "mcdonald[gpu]"`), in the venv mcdonald is in, if it is in one. That is the build for CUDA 12, which runs on every
  card the add-on supports.
- A computer whose driver is new and whose card is from the RTX 2000 series or later can use CUDA 13 instead:
  `pip install "mcdonald[gpu-cuda13]"`. Install one of the two, never both. The button and
  `mcdonald setup --install-gpu` choose CUDA 13 on such a computer.
- A computer that already has NVIDIA's CUDA toolkit needs only CuPy itself: `pip install cupy-cuda12x`, or
  `cupy-cuda13x` for CUDA 13.
- The first step that uses the card takes some seconds longer, once: CuPy builds its small programs for the card and
  keeps them.

To choose among several cards, or to keep everything on the CPU, use **Edit → Preferences…** in the window (on a
Mac, mcDonald → Settings). On the command line it is `mcdonald --gpu NAME` or `mcdonald --gpu none`. On a shared
computer with a job scheduler, a job uses the card only if it was given one (for Slurm, `--gres=gpu:1`).

---

## What `mcdonald setup` checks

| line | what it means | when it says NO |
|---|---|---|
| Python | the version running mcdonald | install Python 3.10 or newer |
| ffmpeg | ffmpeg and ffprobe are found | install ffmpeg (above), then open a new terminal |
| the window | PySide6 is installed, and there is a screen | install mcdonald again, as above; the command line works without it |
| graphics card | which card the slow steps run on, or why none is used | never: every step also runs on the CPU (see "A graphics card", above) |
| storage | the folder where videos and their frames are saved, and the room there | set `MCDONALD_HOME`, or change it on the window's first screen |
| catalog | the PURSUE list is there | — |
| downloads | the website of DVIDS, the Defense Visual Information Distribution Service, answers | the internet connection, or (Mac) the certificates |

## Updating

When a newer version is out, the window offers to update itself when it starts: press
**Update now**, and it closes, updates, and opens again. To do it by hand, run the same pip line
again with `--upgrade`. Each update has a new version number (`mcdonald setup` prints the one
you have, and so does Help → About mcdonald):

```bash
python3 -m pip install --upgrade mcdonald
```

## Where files go

Downloaded videos, and each video's frames saved as pictures, go in one folder:
`Documents/mcdonald`, unless you choose another on the window's first screen or set
`MCDONALD_HOME`. A whole video's frames can take several gigabytes. A short segment, the
stretch of video you choose to measure, takes much less.
