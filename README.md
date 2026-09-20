# McDonald UAP Toolkit

Measurement tools for single-sensor video of unidentified objects.

Point it at a clip and it will tell you how the background moves and in how many
layers, whether the clip behaves like the output of one sensor chain, whether
the object in it behaves like imagery or like something laid over imagery, and
whether your track is actually on the object in every frame.

It will also, frequently, tell you that a question cannot be answered from the
clip you have. That is the intended behaviour, not a shortfall. Most released
sensor video does not contain enough information to state a speed, and a tool
that always returns a number is worse than useless on this subject.

> Named for James E. McDonald, who argued that the subject deserved ordinary
> scientific instruments rather than either credulity or dismissal.

**Status: alpha (0.1.0).** Three tools and the library under them. The wider
pipeline — symbology reduction, angular scale, the kinematic reduction — is not
here yet; see [Roadmap](#roadmap).

---

## Install

```bash
git clone https://github.com/haqqmisra/mcdonald.git
cd mcdonald
python3 -m pip install -e .
```

Python ≥ 3.10, plus **ffmpeg and ffprobe on your PATH** — the toolkit reads
video through them and cannot install them for you:

```bash
sudo dnf install ffmpeg      # Fedora / RHEL
sudo apt install ffmpeg      # Debian / Ubuntu
brew install ffmpeg          # macOS
```

Then verify the install measures correctly before you trust a number from it:

```bash
python3 tests/test_measurement.py
```

That builds synthetic scenes whose answers are known by construction — a known
rigid shift, two backgrounds moving at different rates, planted repeated frames,
an object on a known path — and checks the library recovers each one. It needs
no video data and takes about a minute. It should end `ALL PASS`.

## Use

```bash
# How does the background move -- and is it one background?
mcdonald layers CLIP.mp4 --auto-track --validate

# Has the clip been altered? Was the object added?
mcdonald integrity CLIP.mp4 --track track.csv

# Is my track on the object in every frame?
mcdonald tracksheet CLIP.mp4 --track track.csv
```

`CLIP` is a path to any video file. Results go to a **case directory** —
`--out DIR`, otherwise `./<name>/` under your working directory. Nothing is ever
written next to the installed code.

A track CSV needs a frame column (`frame`, `n` or `frame_n`) and an x/y column
pair in video pixels (`x_px,y_px` or `x,y`). `--auto-track` will attempt one for
you, but **look at the track sheet before building anything on it**: on the clip
this toolkit was developed against, the first automatic tracker spent seven
frames locked to a cloud feature 100 px from the object.

Long clips: `--n0/--n1` take a frame window and keep the absolute numbering.
Frames are extracted losslessly and are ~2 MB each, so point `--workdir`
somewhere with room if `/tmp` is small or a tmpfs.

### Reading the results

`docs/method.md` is the method note: what each measurement means, how each one
fails, and the traps the library is built around. Read it before quoting a
number. The short version of the three that matter most:

1. **Never quote a rate "against the background" without naming the layer.** Sea
   and cloud tops moved 98 px/s apart on the clip this came from; a single
   consensus returns a blend and names neither.
2. **Pixels per second become metres per second only through an angular scale
   *k* and a range *R*.** Neither is usually recoverable from a clip. A speed
   quoted without both sourced is not a measurement.
3. **NO POWER is a verdict.** A clip that cannot decide a test has not passed
   it, and those tests are reported, never dropped.

### Provenance, optionally

The tools run on any file and say nothing about where it came from. If you have
a catalog of releases, point the toolkit at it and the integrity report will
quote the releasing body's own words — including any alteration statement —
alongside the pixel tests:

```bash
export MCDONALD_CATALOG=/path/to/pursue_index/records.csv
mcdonald integrity PR144            # record ids resolve once a catalog is set
```

One backend ships, for the U.S. DoW PURSUE releases (war.gov/UFO) via a local
mirror's `records.csv`. Writing another is a subclass with one method; see
`src/mcdonald/catalog.py`. With no catalog, the report states plainly that it
knows nothing about provenance rather than defaulting to someone else's.

This matters more than it looks. On a disclosed digital recreation, every pixel
test returned NO POWER or INCONCLUSIVE — **the record identified the clip, not
the pixels.** Custody and disclosure are not things pixel forensics can replace.

## What it cannot do

`integrity` shows whether a clip and the object in it behave like the output of
one sensor chain. It catches an object pasted, AI-inserted or animated onto
footage that already existed. **It cannot exclude a composite made upstream of
the symbology by someone who modelled exposure, shake, gain and parallax.**
Nothing in the pixels can; that is a custody question — the original recording
with its metadata, and the mission report. Say so whenever you quote a result.

The synthetic-insert self-test is what gives a PASS its meaning: the tool
animates a fake object over the same frames and runs the same tests on it. If
the fake passes too, that test has no discriminating power on your clip,
whatever its verdict says. Note the honest limit: no clip with a *known real*
insert was available to validate against, so the synthetic stands in for one,
and it models a naive overlay rather than a match-moved physical composite.

## Roadmap

Working (0.1): background layers, clip integrity, track verification, the
shared library, an optional catalog.

Next: symbology reduction (north pointer, boresight, corner brackets, mode
annunciator), angular scale (field-of-view routes, zoom chains, in-frame scale
bars), the kinematic reduction (image-plane velocity → line-of-sight rate →
the relative-velocity fan), object-versus-texture-field co-motion, a unified
figure style, and a `mcdonald run` driver that takes a clip through every stage
into one report.

## License

MIT. See `LICENSE`.
