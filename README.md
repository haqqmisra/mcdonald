<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/logo-dark.png">
  <img alt="mcDonald UAP Toolkit" src="docs/logo-light.png" width="420">
</picture>

mcDonald measures how an unknown object moves in a video taken by one camera. You show
it the object; it follows the object through the video and writes a report of what the
video can tell you about its motion, and what it cannot.

Often the honest answer is that the video does not hold enough to give a speed. The
report says so rather than making a number up.

> Named for James E. McDonald, who argued that the subject deserved ordinary scientific
> instruments rather than either belief or dismissal.

**Status:** early test version (0.2.0), tried on Linux and macOS; Windows is next.

## Install

1. **ffmpeg**, which mcdonald uses to read video:
   `brew install ffmpeg` (Mac), `winget install Gyan.FFmpeg` (Windows),
   `sudo apt install ffmpeg` or `sudo dnf install ffmpeg` (Linux).
2. **mcdonald** (needs Python 3.10 or newer):

   ```bash
   python3 -m pip install "mcdonald[gui] @ git+https://github.com/haqqmisra/mcdonald"
   ```

3. **Check your computer**, which also says what to do next:

   ```bash
   mcdonald setup
   ```

New to Python or the terminal? [docs/install.md](docs/install.md) goes through each step
slowly, for each kind of computer.

## Use

Start the window:

```bash
mcdonald-gui
```

Open a video from your computer, or one of the PURSUE videos by its name (for example
`PR149`; it is downloaded the first time). Choose the part of the video with the object
in it. Then there are three steps, and the window shows which one is next:

1. **Find the object.** The computer lists the things that move against the background.
   Press *This is it* on the object, or click on the object yourself.
2. **Follow it.** The computer follows the object through every frame. Then it shows
   you small pictures along the track: check that the box is on the object in every one.
3. **Measure.** Fill in anything you know that the picture cannot tell (all of it is
   optional), and the report opens when it is done.

Help → Getting started in the window says the same, with the keys.

### Before you start

- **Open only the part of the video with the object in it**, with a second or two
  either side. Every frame opened is saved to disk (about 0.75 MB a frame for HD video),
  and some measurements take a second or two per frame. The window says how long a step
  will take before it starts, and each step can be stopped.
- Videos and frames are saved in `Documents/mcdonald`. You can choose another folder on
  the window's first screen.

## What the report can and cannot tell you

- A speed in metres per second needs the camera's field of view and the distance to the
  object. A video rarely shows either, so the report usually gives motion in pixels and
  says what else would be needed.
- If the background moves in more than one layer (sea and clouds, for example), the
  report gives the object's motion against each layer, not a blend of the two.
- The report checks whether the object looks like part of the camera's picture or like
  something added to it later. No check of the pixels can rule out a careful fake made
  before the video was released. Only the original recording and its records can.

## More

- [README-technical.md](README-technical.md): every command, how each step works, and
  the tests. **If you want an AI agent to work with mcdonald, give it this file.**
- [docs/method.md](docs/method.md): what each measurement means and how each one can
  go wrong. Read it before quoting a number.
- [docs/agents.md](docs/agents.md): the whole job from the command line, with no window.

## License

BSD 3-Clause ([LICENSE](LICENSE)): use it, change it and share it, in your own work too, as long as
the copyright notice goes with it. Its third clause means a version you change may not use
the author's name to promote it without permission.
