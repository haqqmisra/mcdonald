# The controls harness's tools

ROADMAP.md 0.5.0, its first item: the labelled infrared set's tracks in the data folder, the whole set through `flicker`
as a tool that runs through the job scheduler, and the sampled suite (`tests/test_controls.py`) that holds one of
everything from saved curves in minutes. The method is docs/method.md section 44.

| file | what it does |
|---|---|
| `svanstrom_labels.py` | reads the set's MATLAB `groundTruth` labels with scipy alone (`filewrapper`, an MCOS reader) and writes them once as tracks: `$MCDONALD_DATA/svanstrom2021/tracks/` (432 tracks and `index.tsv`, with each object's polarity from its pixels and the clip's other tracks to avoid). Done on 2026-11-07; run again only to check it |
| `run_set.py` | one clip's tracks through `flicker.measure`, as `mcdonald run` measures an object, under the stage's rule and the paper's; keeps everything `flicker.judge` was given (`curves.json.gz`) and checks that judging it again with no video gives the same call (`replay`) |
| `svanstrom.sbatch` | `run_set.py` as a job array, a clip a task: `sbatch --array=0-364%6 --nice=100 tools/controls/svanstrom.sbatch RUNS` from a snapshot of the repository. About a minute a track on two CPUs: 432 tracks, an hour and a half six abreast (2026-11-07: 13:29-15:03) |
| `summarise.py` | the table of every track (`svanstrom_tracks.csv`: its columns are in the data folder's `controls/README.md`), and the rates by class and distance with their exact and by-clip intervals, each false-alarm rate with its exact one-sided upper bound, the coverage (the share answered) by class and how much likelier a refusal is on a bird, the rates by stratum of what a clip offers (length, size, contrast, distance, frame rate), the two rules' agreement (Cohen's kappa) and the amplitude's separation of true calls from false ones (AUC); `--json` for the rates; `--rejudge` judges every track again from its saved curves, no video |
| `save_controls.py` | the suite's saved curves: the package's own controls measured from their videos (the Galileo flyers, PR135's flock, PR23, PR055, PR071, the WA9ONY-5 balloon, the two strobe helicopters) and the labelled set's sample copied from a whole-set run, each replay checked before it is written. `tests/golden/controls.csv` lists them |

## Making the saved curves again

After a change that moves what the curves are -- the photometry, the aperture, the track's smoothing, the lights -- and
not what is judged from them, the saved curves are stale: the suite replays the old curves through the new judging. Then:

    sbatch --array=0-364%6 --nice=100 tools/controls/svanstrom.sbatch RUNS        # the whole set again
    python3 tools/controls/summarise.py RUNS --out $MCDONALD_DATA/controls/svanstrom_tracks.csv
    python3 tools/controls/save_controls.py $MCDONALD_DATA/controls/curves --set RUNS
    (cd $MCDONALD_DATA && sha256sum controls/svanstrom_tracks.csv controls/curves/*)   # into SHA256SUMS, replacing the old lines

and RECORD in `tests/test_controls.py` moves with the table, each number said in the CHANGELOG. A change to the judging
alone needs no video: the suite says what moved, and

    python3 tools/controls/save_controls.py $MCDONALD_DATA/controls/curves --record      # the sample's record, in tests/golden/controls.csv
    python3 tools/controls/summarise.py $MCDONALD_DATA/controls/set --rejudge --procs 4 --json RATES.json --out TABLE.csv

give the new record and the whole set's new rates (RECORD) from the saved curves, through the job scheduler.

## The held-out third

`tools/sweep/looks.tsv` is the ledger of looks (B17): one line each time a gate meets a held-out set. `tools/sweep/agreement.py`
states a look's agreement as a difference with a by-video interval. Running it on the held-out third's calls is a look:
write the line first.
