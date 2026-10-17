#!/bin/bash
#SBATCH --job-name=sweep_post
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=3G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%A_%a.out
# The beat pass, step 4 (tools/sweep/README.md): one video of clips.tsv (row = task id + 1) -- its windows' proposals as
# objects, each followed from Find's own marks and measured by the flicker stage (`post.py`).
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"
IFS=$'\t' read -r id _ < <(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" clips.tsv)
python3 -u "$SWEEP/post.py" "$id"
