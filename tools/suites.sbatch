#!/bin/bash
#SBATCH --job-name=mcdonald_suites
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=01:30:00
#SBATCH --output=logs/%x_%j.out
# The test suites, on a machine with a queue: they start process pools (and test_gui an X server of its
# own, Xvfb), so they are not something to run on a login node or beside someone else's work.
#     mkdir -p logs && sbatch tools/suites.sbatch                 # the five that need no video data
#     sbatch tools/suites.sbatch golden                           # and test_golden, which needs the corpus
# On four CPUs: measurement ~6 min, reduction and published under a minute, cli ~5, gui ~6, golden ~15.
# A suite that fails does not stop the ones after it; the job fails if any did.

set -uo pipefail
cd "$SLURM_SUBMIT_DIR"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

if type module &>/dev/null; then
    module load python ffmpeg || true          # site-specific; merlin has no modules
fi

suites="test_measurement test_reduction test_published test_cli test_gui"
[ "${1:-}" = "golden" ] && suites="$suites test_golden"
failed=""
for s in $suites; do
    echo "== $s  ($(date +%H:%M:%S))"
    srun python3 -u tests/$s.py > "logs/${s}_${SLURM_JOB_ID}.log" 2>&1 || failed="$failed $s"
    echo "   $(grep -c '  PASS' "logs/${s}_${SLURM_JOB_ID}.log") PASS, $(grep -c '  FAIL' "logs/${s}_${SLURM_JOB_ID}.log") FAIL, $(grep -c '  SKIP' "logs/${s}_${SLURM_JOB_ID}.log") SKIP"
    grep '  FAIL' "logs/${s}_${SLURM_JOB_ID}.log" | cut -c1-200
done
[ -z "$failed" ] || { echo "FAILED:$failed"; exit 1; }
echo "ALL SUITES PASS"
