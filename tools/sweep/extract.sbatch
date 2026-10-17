#!/bin/bash
#SBATCH --job-name=sweep_extract
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=03:00:00
#SBATCH --output=logs/%x_%A_%a.out
# The beat pass, step 2 (tools/sweep/README.md): every frame of one video of clips.tsv (row = task id + 1) into the
# package's frame folder ($MCDONALD_HOME/frames/<video>/f%05d.png, as mcdonald.clip extracts them), whole and once,
# before any window runs: windows that overlap and extract at once can leave a gap that Clip.extracted(), which looks
# only at a window's end frames, does not see. A .complete file marks a whole extraction.
set -uo pipefail
cd "$SLURM_SUBMIT_DIR"
IFS=$'\t' read -r id video frames size fps < <(sed -n "$((SLURM_ARRAY_TASK_ID + 1))p" clips.tsv)
D="$(python3 -c 'from mcdonald import storage; print(storage.frames())')/$(basename "${video%.*}")"
mkdir -p "$D"
[ -f "$D/.complete" ] && { echo "$id: already whole"; exit 0; }
ffmpeg -nostdin -v error -y -threads 2 -i "$video" $(python3 -c 'from mcdonald.clip import every_frame; print(" ".join(every_frame()))') \
  -start_number 1 "$D/f%05d.png" || exit 1
touch "$D/.complete"
echo "$id: $(ls "$D" | grep -c '^f[0-9]*\.png$') frames in $D (the video has $frames)"
