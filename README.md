<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/haqqmisra/mcdonald/main/docs/logo-dark.png">
  <img alt="mcDonald UAP Toolkit" src="https://raw.githubusercontent.com/haqqmisra/mcdonald/main/docs/logo-light.png" width="420">
</picture>

**mcdonald** is a frame-by-frame analysis toolkit for measuring the kinematics of an unknown
object in a single-camera video.

> "Science is in default for having failed to mount any truly adequate studies of this problem."
>
> — James E. McDonald

**Status:** early test version (0.5.4), tried on Linux and macOS, and on Windows so far only by its automatic tests.

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

When a newer version is out, `mcdonald-gui` offers to update itself when it starts. The command
line prints the command to update with. To check at any time, use **Help → Check for updates** in
the window, or `mcdonald setup` on the command line.

A graphics card is never needed. If the computer has one from NVIDIA, an optional add-on runs the slowest steps
on it. They finish several times sooner and give the same measurement. See
[A graphics card (optional)](https://github.com/haqqmisra/mcdonald/blob/main/docs/install.md#a-graphics-card-optional).

New to Python or the terminal? [docs/install.md](https://github.com/haqqmisra/mcdonald/blob/main/docs/install.md) walks through each step in
detail.

## Use

**mcdonald** has a graphical interface and a command-line interface. People and AI agents can
both use it.

The graphical interface leads a person through the steps of an analysis. To start it:

```bash
mcdonald-gui
```

The command-line interface is for developers, advanced users and AI agents. To start it and see
a summary of its options:

```bash
mcdonald
```

### Sharing an analysis

To hand a video's analysis to someone else, such as a colleague or an agent, use **File → Share for review…**.
Write what you would like them to look at: the stretches of frames, and what is there. Add your name and a note,
and press **Save a file to send**. That writes one small file, ending in `.mcdonald`. It holds your marks (the
points placed on the object, frame by frame), each object's track (its position in each frame, joined up), each
object's results and your note. The video itself is not in the file. Their copy of mcdonald finds the same video
by its catalog name, downloads it if it is not on their computer, and checks that it is the same file.

They open it with **File → Open a shared file…**, by dropping it on the window, or with `mcdonald mark FILE`. The
window opens the same part of the same video, with your marks and every object's track drawn. A card on the right
shows your note, a button for each stretch you named and a box for their answer. Each stretch's button plays that
stretch and stops at its end. Their answer saves a file to send back, with your note and theirs. Where the file
holds measured objects, **Measure it again** measures each object again as its report says. It then tells you
whether the numbers come back the same. An agent makes the same file with `mcdonald share make`, reads one with
`mcdonald share show`, and measures it again with `mcdonald share rerun`.

### Prompting an agent

An AI agent can help at any point in the analysis, before or after a person has looked at the
video. Here is a sample prompt to give your favorite command-line AI model:

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
