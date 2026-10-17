#!/bin/bash
# The whole-video beat pass from the start, through Slurm (tools/sweep/README.md):
#     tools/sweep/sweep.sh WORK [--ids PR098,PR149] [--videos LIST.tsv]
# Finds the videos and cuts them into windows (windows.py), then submits each step after the one before: every video's
# frames (extract.sbatch), Find over every window (propose.sbatch), each video's objects followed and measured
# (post.sbatch), and the summary (summary.py). The review of the strict list comes after, when its length is known (the
# command is printed). MCDONALD (the command; default `mcdonald`), MCDONALD_HOME (the storage folder) and NICE (default
# 1000) as for any run.
set -euo pipefail
SWEEP=$(cd "$(dirname "$0")" && pwd)
export SWEEP
WORK=$1
shift
python3 "$SWEEP/windows.py" "$WORK" "$@"
cd "$WORK"
mkdir -p logs
nc=$(wc -l < clips.tsv)
nw=$(wc -l < windows.tsv)
NICE=${NICE:-1000}
e=$(sbatch --parsable --nice="$NICE" --array=0-$((nc - 1))%4 "$SWEEP/extract.sbatch")
p=$(sbatch --parsable --nice="$NICE" --dependency=afterok:"$e" --array=0-$((nw - 1))%10 "$SWEEP/propose.sbatch")
q=$(sbatch --parsable --nice="$NICE" --dependency=afterany:"$p" --array=0-$((nc - 1))%8 "$SWEEP/post.sbatch")
s=$(sbatch --parsable --nice="$NICE" --dependency=afterany:"$q" -n 1 -c 1 --mem=1G --time=00:30:00 -J sweep_summary \
    -o logs/%x_%j.out --wrap "python3 $SWEEP/summary.py")
echo "submitted: extract $e, propose $p (${nw} windows), post $q (${nc} videos), summary $s"
echo "then, in $WORK: sbatch --nice=$NICE --array=0-\$((\$(wc -l < strict.tsv) - 2)) $SWEEP/review.sbatch; and python3 $SWEEP/summary.py again"
