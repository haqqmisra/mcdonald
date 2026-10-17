#!/bin/bash
#SBATCH --job-name=sweep_propose
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=03:00:00
#SBATCH --output=logs/%x_%A_%a.out
# The beat pass, step 3 (tools/sweep/README.md): Find over one window of windows.tsv (row = task id + 1), every thing it
# kept (`mcdonald look --propose --more`) -> prop/ID/wNN.json and cases/ID/wNN/. A window already done exits at once; exit 5
# ("nothing moves") is an answer. 2 CPUs and 4 GB: a 720p window of 400 frames peaked at 0.8 GB (2026-10-13), a 1080p
# window of 322 frames went over 1.5 GB (2026-10-17).
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"
M=${MCDONALD:-mcdonald}
IFS=$'\t' read -r id tag n0 n1 < <(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" windows.tsv)
video=$(awk -F'\t' -v p="$id" '$1==p{print $2}' clips.tsv)
mkdir -p prop/$id cases/$id logs
[ -s prop/$id/$tag.json ] && exit 0
$M look "$video" --propose --more --n0 $n0 --n1 $n1 --procs 2 --out cases/$id/$tag --json < /dev/null \
  > prop/$id/$tag.json.part 2> logs/${id}_${tag}_propose.err
rc=$?
if [ $rc -eq 0 ] || [ $rc -eq 5 ]; then mv prop/$id/$tag.json.part prop/$id/$tag.json; else exit $rc; fi
