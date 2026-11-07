#!/bin/bash
#SBATCH --job-name=controls_set
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=3G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x_%A_%a.out
# The labelled infrared set through `flicker`, a clip a task (tools/controls/run_set.py), under both beat rules:
#     python3 tools/controls/run_set.py RUNS --list                     # 365 clips
#     mkdir -p logs && sbatch --array=0-364%6 --nice=100 tools/controls/svanstrom.sbatch RUNS
#     python3 tools/controls/summarise.py RUNS                          # the table and the rates, when it is done
# Every argument after RUNS goes to run_set.py (--per 2 for two clips a task, --tracks DIR ...). Run it from a snapshot of
# the repository (git archive, or a copy of every tracked file), not a tree being edited: each task imports the package
# again. Throttle the array (%6 here) on a shared machine. A task that finds a track's replay.json there skips it, so a
# stopped run is started again with the same command. No --account or --partition: they differ per site.

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

# numpy and scipy thread on their own; the package's pools are processes. One thread each.
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export MCDONALD_HOME="${MCDONALD_HOME:-$(dirname "$1")/home}"     # the package's storage, out of the user's own

if type module &>/dev/null; then
    module load python ffmpeg || true          # site-specific; merlin has no modules
fi

RUNS=$1; shift
python3 -u tools/controls/run_set.py "$RUNS" --task "$SLURM_ARRAY_TASK_ID" --procs "${SLURM_CPUS_PER_TASK:-1}" "$@"
