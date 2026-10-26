<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/haqqmisra/mcdonald/main/docs/logo-dark.png">
  <img alt="mcDonald UAP Toolkit" src="https://raw.githubusercontent.com/haqqmisra/mcdonald/main/docs/logo-light.png" width="420">
</picture>

**mcdonald** is a frame-by-frame analysis toolkit for measuring the kinematics of an unknown
object in a single-camera video.

> "Science is in default for having failed to mount any truly adequate studies of this problem."
>
> — James E. McDonald

**Status:** early test version (0.3.9), tried on Linux and macOS, and on Windows so far only by its automatic tests.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23652954.svg)](https://doi.org/10.5281/zenodo.23652954)

## Install

1. Prerequisite: make sure **ffmpeg** is installed:
   `brew install ffmpeg` (Mac), `winget install Gyan.FFmpeg` (Windows),
   `sudo apt install ffmpeg` or `sudo dnf install ffmpeg` (Linux).
2. Install **mcdonald** (needs Python 3.10 or newer):

   ```bash
   python3 -m pip install mcdonald
   ```

3. Check your setup, which also provides instructions on what to do next:

   ```bash
   mcdonald setup
   ```

When a newer version is out, `mcdonald-gui` offers to update itself when it starts, and the
command line prints the command to update with. To ask at any time: **Help → Check for updates**
in the window, or `mcdonald setup` on the command line.

New to Python or the terminal? [docs/install.md](https://github.com/haqqmisra/mcdonald/blob/main/docs/install.md) walks through each step in
detail.

## Use

**mcdonald** has a graphical interface and a command-line interface. The software is intended
to be driven by human users and/or AI agents.

The graphical interface is designed to prompt human users through the steps of analysis. To
start the graphical interface:

```bash
mcdonald-gui
```

The command-line interface is designed for developers, advanced users, and AI agents. To start
the command-line interface and see a summary of options:

```bash
mcdonald
```

### Sharing an analysis

To hand a video's analysis to someone else -- a colleague, or an agent -- so that they pick up where you left off,
use **File → Share for review…**: write what you would like them to look at (the stretches of frames, and what is
there), add your name and a note, and press **Save a file to send**. That writes one small file, ending in
`.mcdonald`, with your marks, tracks, each object's results and your note. The video itself is not in it: their
copy of mcdonald finds the same video by its catalog name (downloading it if it is not on their computer) and
checks it is the same file.

They open it with **File → Open a shared file…** (or by dropping it on the window, or `mcdonald mark FILE`). The
window opens the same part of the same video, with your marks and every object's track drawn, and a card on the
right with your note, a button for each stretch you named (it plays the stretch and stops at its end), and a box
for their answer -- which saves a file to send back, with your note and theirs. Where the file holds measured
objects, **Measure it again** measures each again as its report says and tells you whether the numbers come back the
same. An agent makes the same file with `mcdonald share make`, reads one with `mcdonald share show`, and measures it
again with `mcdonald share rerun`.

### Prompting an agent

You can invoke an AI agent to assist at any point in the analysis, whether before or after a
human has looked at the video. Here is a sample prompt that you can pass to your favorite
command-line AI model:

> Please use the mcdonald toolkit to analyze the PR144 video released under PURSUE. Run
> `mcdonald readme` to get started.

### Exercises

To learn **mcdonald** on real videos, try the
[exercises](https://github.com/haqqmisra/mcdonald/tree/main/docs/exercises). Each one gives the
steps in the window and on the command line, and the answer you should get. Start with
[Birdwatching (PR44)](https://github.com/haqqmisra/mcdonald/blob/main/docs/exercises/01-pr44.md).
When you finish one, please
[tell us how it went](https://github.com/haqqmisra/mcdonald/issues/new?template=exercise-result.yml).

## Support

**mcdonald** is free and open source. To support its development, you can
[donate to the mcDonald UAP Toolkit](https://www.zeffy.com/en-US/donation-form/project-janus-mcdonald-uap-toolkit)
through Blue Marble Space, a 501(c)(3) nonprofit. Donations are tax-deductible as allowed by law.

Development of **mcdonald** is supported by a grant from
[Emergent Ventures](https://www.mercatus.org/emergent-ventures) at the Mercatus Center.
The plan to version 1.0 is in [ROADMAP.md](https://github.com/haqqmisra/mcdonald/blob/main/ROADMAP.md).

## License

Copyright (c) 2026 Jacob Haqq Misra. Released under the [BSD 3-Clause License](https://github.com/haqqmisra/mcdonald/blob/main/LICENSE).
