# tests

Two suites, answering two different questions.

## `test_measurement.py` — does this install measure correctly?

Portable. Needs no video data, takes about a minute, and is the one to run
after installing.

```bash
python3 tests/test_measurement.py        # or: pytest tests/test_measurement.py
```

Every check builds a scene whose answer is known by construction and asks the
library to recover it: a known rigid shift, two backgrounds moving at
different rates, striated versus isotropic texture, planted repeated frames, a
compact source on a known path, a redaction block that must be masked beside a
dark scene that must not be. It also checks the packaging contract — that a
run never writes into the installed package, that the catalog is genuinely
optional, and that ffmpeg is present.

The two-layer check is the one worth watching. It prints what a single
consensus over both layers *would* have said, which is the wrong number this
whole library exists to avoid.

## `test_golden.py` — do the real clips still give the published numbers?

Needs the video files, which are not distributed with the package. Skips
cleanly and says why when they are absent.

```bash
export MCDONALD_CATALOG=~/research/uap/pursue_index/records.csv
python3 tests/test_golden.py             # ~5 min: a 200-frame window of PR144
python3 tests/test_golden.py --full      # tens of minutes: the whole clip
```

The default run measures frames 300–500 of PR144 and compares against a
baseline recorded on 2026-09-19. `--full` runs the documented whole-clip
command and compares against the published values in `docs/method.md` § 4.

The object track is vendored in `golden/pr144_track.csv`, so only the video
has to be found.

### Changing a baseline

A golden number changes only when the measurement genuinely should have
changed. If one moves, find out why before updating it: these are consensus
medians over dozens of templates, and a broken mask or a mis-set zero-exclusion
zone moves them by tens of pixels per second, not by ones. Record the reason in
the commit message — some of these numbers have been published.
