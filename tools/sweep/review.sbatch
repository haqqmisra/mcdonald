#!/bin/bash
#SBATCH --job-name=sweep_review
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=3G
#SBATCH --time=03:00:00
#SBATCH --output=logs/%x_%A_%a.out
# The beat pass, step 6 (tools/sweep/README.md): one object of strict.tsv (row = task id + 2, past its header) measured
# again by the bird paper's rule (`mcdonald flicker --beat-rule paper`: the continuum null, the background at the beat's
# own frequency, and constant dots planted and encoded like the clip) -> review/ID_oNN.json, which `summary.py` reads.
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"
M=${MCDONALD:-mcdonald}
IFS=$'\t' read -r id obj _ < <(sed -n "$((SLURM_ARRAY_TASK_ID + 2))p" strict.tsv)
video=$(awk -F'\t' -v p="$id" '$1==p{print $2}' clips.tsv)
row=$(awk -F'\t' -v o="$obj" '$1==o' objects/$id.tsv)
frames=$(awk -F'\t' -v p="$id" '$1==p{print $3}' clips.tsv)
a=$(echo "$row" | cut -f4); b=$(echo "$row" | cut -f5); pol=$(echo "$row" | cut -f6)
n0=$(( a - 30 > 1 ? a - 30 : 1 )); n1=$(( b + 30 < frames ? b + 30 : frames ))
track=$(ls cases/$id/obj/$obj/*_autotrack.csv | head -1)
d=""; [ "$pol" = dark ] && d=--dark
mkdir -p review/$id
$M flicker "$video" --track "$track" --n0 $n0 --n1 $n1 $d --beat-rule paper --out review/$id/$obj --procs 2 --json < /dev/null \
  > review/${id}_$obj.json 2> logs/${id}_${obj}_review.err
