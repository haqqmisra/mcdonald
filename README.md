<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/logo-dark.png">
  <img alt="mcDonald UAP Toolkit" src="docs/logo-light.png" width="420">
</picture>

**mcdonald** is a frame-by-frame analysis toolkit for measuring the kinematics of an unknown
object in a single-camera video.

> "Science is in default for having failed to mount any truly adequate studies of this problem."
>
> — James E. McDonald

**Status:** early test version (0.2.1), tried on Linux and macOS; Windows is next.

## Install

1. Prerequisite: make sure **ffmpeg** is installed:
   `brew install ffmpeg` (Mac), `winget install Gyan.FFmpeg` (Windows),
   `sudo apt install ffmpeg` or `sudo dnf install ffmpeg` (Linux).
2. Install **mcdonald** (needs Python 3.10 or newer):

   ```bash
   python3 -m pip install "mcdonald[gui] @ git+https://github.com/haqqmisra/mcdonald"
   ```

3. Check your setup, which also provides instructions on what to do next:

   ```bash
   mcdonald setup
   ```

New to Python or the terminal? [docs/install.md](docs/install.md) walks through each step in
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

### Prompting an agent

You can invoke an AI agent to assist at any point in the analysis, whether before or after a
human has looked at the video. Here is a sample prompt that you can pass to your favorite
command-line AI model:

> Please use the mcdonald toolkit to analyze the PR144 video released under PURSUE. Run
> `mcdonald readme` to get started.

## License

Copyright (c) 2026 Jacob Haqq Misra. Released under the [BSD 3-Clause License](LICENSE).
