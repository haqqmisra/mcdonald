# The beat sweep's tools

ROADMAP.md 0.3, objective 9: the whole-video beat pass of the PURSUE videos (2026-10-12/14), which followed every
long-lived thing Find proposes in each video and put it through the flicker stage, as scripts anyone with the videos
can run again. The pass's own scripts lived beside its outputs; these are those scripts, with every path to them taken
out: a video is found by the release's file name in the package's catalog and downloaded into the storage folder the
first time (`MCDONALD_HOME`), and the command is `mcdonald` (or `$MCDONALD`).

## Running it

    tools/sweep/sweep.sh WORK                     # all 126 videos: 7.5 GB of video, some 200 GB of frames, a day or two on 20 CPUs
    tools/sweep/sweep.sh WORK --ids PR23,PR073     # a few

`sweep.sh` cuts the videos into windows and submits each step through Slurm, after the one before. On a shared
machine run it inside an allocation (`srun -c 1 tools/sweep/sweep.sh WORK`), since its first step reads the videos.

| step | file | what it does |
|---|---|---|
| 1 | `windows.py` | finds each video (downloading it if need be) and cuts it into windows of 400 frames that overlap by 30, so a thing that crosses a cut is whole in one: `WORK/clips.tsv`, `WORK/windows.tsv` |
| 2 | `extract.sbatch` | every frame of each video into the package's frame folder, whole and once, before any window: windows that overlap and extract at once can leave a gap the package does not see |
| 3 | `propose.sbatch` | Find over each window, everything it kept (`mcdonald look --propose --more`): `prop/ID/wNN.json` |
| 4 | `post.sbatch`, `post.py`, `collect.py` | each video's proposals seen on 40 frames or more, the same thing in two windows merged (`objects/ID.tsv`); each object followed from Find's own marks (`mcdonald mark --link`) and measured (`mcdonald flicker`, 30 frames either side): `beat/ID/oNN_flicker.json` |
| 5 | `summary.py` | `summary.tsv` (every object measured), the candidates, and `strict.tsv`: passing windows that come back apart at one frequency, or a whole track over its drift at 5 % or more |
| 6 | `review.sbatch` | each object of the strict list measured again by the bird paper's rule (`--beat-rule paper`: the continuum null, the background at the beat, and constant dots planted and encoded like the clip); `summary.py` again puts its call beside the stage's |
| -- | `cadcheck.py` | for an object of interest: its brightness on anchor against B frames, on held against changed pictures, and by frame number modulo 2-8 -- whether the encoder or the video's cadence makes its beat |

What a person adds is the look: the strict list is where the pass's candidates came from, and each was then looked at
by eye -- the object in the strip, the beat in the figure, the members of a group followed one by one where the stage
had measured a blend. Those looks, and the tracks they produced, are in the reference case files of the two papers
(the reference-data folder's `cases/`, which `tools/rerun_cases.py` reruns to their numbers).

## The held-out third

| file | what it is |
|---|---|
| `videos.tsv` | The sweep's 126 videos: the PURSUE videos with an object to look at, by the release's file name, and whether the whole-video pass followed objects in each. |
| `holdout.py`, `holdout.tsv` | The held-out third (the ideas bank's D5): 42 videos drawn on 2026-10-17, before the gate work, by a hash anyone can repeat. They are not looked at until the gates are frozen on the controls and the rest; then the gates run on them once. `python3 tools/sweep/holdout.py` draws again and checks the table; `--list` prints the ids for a script to skip. `summary.py` leaves them out, and counts them, until it is told `--held-out`. |

## The bird floor and how overfit a gate is

ROADMAP.md 0.5.0 (the ideas bank's B24, E9 and E19; `docs/method.md` section 43). Both read a per-track table of a
labelled set -- `clip`, `object`, `cls` (BIRD or not), and for each beat rule `{rule}_call`, `{rule}_amplitude`,
`{rule}_hz` and `{rule}_shaken_px` -- the table the controls harness writes for the Svanström set, or any set measured the
same way. Python's standard library only; run them again after any change to `flicker` or the conclusion's rule.

| file | what it does |
|---|---|
| `floor.py` | `set`: `report.BIRD_FLOOR` from the null -- the smallest floor at which no more than 1 % of the non-bird tracks are named a bird, as a median over resamples of their clips, the larger beat rule's, rounded up to 0.5 % -- with the rates at it (by-clip and exact intervals) and the cost it implies (B24). `test`: a frozen floor once on a set it was not set on, against a one-sided binomial test of its stated rate. `challenger`: the floor against the simplest rule that could do its job, the amplitude alone (E19). `strata`: a frozen floor's miss and false-alarm rates by what a clip offers -- track length, size, the track's power -- beside the pooled rate, as a description, never an input to the floor. |
| `pbo.py` | The probability of backtest overfitting by combinatorially symmetric cross-validation (E9): the clips in 16 blocks, every half of them, the candidate chosen on one half ranked on the other. `floor`: BIRD_FLOOR's candidates, 0-20 % by 0.5 %, chosen by the best U = TPR - 11 FPR or (`--alpha`) by `floor.py`'s own rule. `configs`: any gate's candidates from a long table (`config`, `clip`, `cls`, `named`), such as the capped disc's sizes (`flicker.POINT_DISC`). |
