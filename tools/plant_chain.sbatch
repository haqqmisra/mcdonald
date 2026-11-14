#!/bin/bash
#SBATCH --job-name=plant_chain
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x_%j.out
# One planted video through the chain (tools/plant_chain.py); its arguments go through:
#     mkdir -p logs && sbatch tools/plant_chain.sbatch PR149 --n0 1 --n1 400 --draw 20 --seed 1 --out DIR --link --flicker
# Memory: the static masks of a 1080p stretch peak near 2.8 GB, and Find's pool takes about 0.5 GB a worker at 1080p.
# No --account or --partition here: they differ per site (sbatch -A ... -p ..., or SBATCH_ACCOUNT / SBATCH_PARTITION).
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
if type module &>/dev/null; then
    module load python ffmpeg || true          # site-specific
fi
srun /usr/bin/time -v python3 -u tools/plant_chain.py "$@"
