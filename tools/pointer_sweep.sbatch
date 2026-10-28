#!/bin/bash
#SBATCH -J pointer_sweep
#SBATCH -n 1
#SBATCH -c 2
#SBATCH --mem=3G
#SBATCH --time=01:30:00
#SBATCH --nice=5000
# The k-from-slew sweep with zoom states (tools/pointer_sweep.py), one clip an array task, rows of $LIST from 0:
#     mkdir -p $OUT/logs && sbatch --array=0-N%10 -o $OUT/logs/%x_%a.out \
#         --export=ALL,LIST=list.tsv,OUT=/scratch/... tools/pointer_sweep.sbatch
#     python3 tools/pointer_sweep.py collect $OUT
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONPATH="$SLURM_SUBMIT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
/usr/bin/time -v python3 -u tools/pointer_sweep.py one "$LIST" "$SLURM_ARRAY_TASK_ID" "$OUT"
