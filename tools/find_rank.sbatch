#!/bin/bash
#SBATCH --job-name=find_rank
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=logs/%x_%j.out
# Where is the recorded object on Find's list? (tools/find_rank.py). Arguments go through:
#     mkdir -p logs && sbatch tools/find_rank.sbatch --link
#     sbatch -c 8 --time=01:00:00 tools/find_rank.sbatch PR113 --work /scratch/$USER/find-rank
# About 2.2 CPU-seconds a 1080p frame for Find, and the link's detector on top: all eight cases
# with --link are an hour and a quarter on four CPUs. No --account or --partition here: they
# differ per site (sbatch -A ... -p ..., or SBATCH_ACCOUNT / SBATCH_PARTITION).

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

# numpy and scipy thread on their own; the package's pools are processes. One thread each.
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

if type module &>/dev/null; then
    module load python ffmpeg || true          # site-specific; merlin has no modules
fi

srun python3 -u tools/find_rank.py "$@"
