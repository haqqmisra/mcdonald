<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/haqqmisra/mcdonald/main/docs/logo-dark.png">
  <img alt="mcDonald UAP Toolkit" src="https://raw.githubusercontent.com/haqqmisra/mcdonald/main/docs/logo-light.png" width="420">
</picture>

**mcdonald** is a frame-by-frame analysis toolkit for measuring the kinematics of an unknown
object in a single-camera video.

> "Science is in default for having failed to mount any truly adequate studies of this problem."
>
> — James E. McDonald

**Status:** early test version (0.2.13), tried on Linux and macOS, and on Windows so far only by its automatic tests.

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
command line prints the command to update with.

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

The window opens with a start screen over it. Open a video, choose the segment with the object,
and press **Find, follow and measure the object**: the computer finds what moves, takes the most
likely thing as the object, follows it, measures how it moved and writes a report, asking nothing
on the way; three lights under the button show the steps as they are done. The report then
appears under the button, the video still in sight: its conclusion, the numbers found, and
"Full report" for the whole of it; look at its track sheet and press "I looked" if the ring is
on the object in every frame. Turn on **Advanced** (under the
button before it is pressed, or View → Advanced) to do the three steps one at a time, to choose
the object yourself from the list "Find the object" shows, or to mark it by hand. If a video has
more than one object, tick each of them on that list and press "Follow and measure the ticked
ones": each is followed and measured in turn and gets its own report.

The command-line interface is designed for developers, advanced users, and AI agents. To start
the command-line interface and see a summary of options:

```bash
mcdonald
```

### Prompting an agent

You can invoke an AI agent to assist at any point in the analysis, whether before or after a
human has looked at the video. Here is a sample prompt that you can pass to your favorite
command-line AI model:

> Please use the mcdonald toolkit to analyze the PR144 video released under PURSUE. Run
> `mcdonald readme` to get started.

## Support

**mcdonald** is free and open source. To support its development, you can donate through
[Project Janus](https://www.zeffy.com/en-US/donation-form/project-janus) at Blue Marble Space,
a 501(c)(3) nonprofit. Donations are tax-deductible as allowed by law.

## License

Copyright (c) 2026 Jacob Haqq Misra. Released under the [BSD 3-Clause License](https://github.com/haqqmisra/mcdonald/blob/main/LICENSE).
