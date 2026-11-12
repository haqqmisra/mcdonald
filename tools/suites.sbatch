#!/bin/bash
#SBATCH --job-name=mcdonald_suites
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=01:30:00
#SBATCH --output=logs/%x_%j.out
# The test suites, on a machine with a queue: they start process pools (and test_gui an X server of its
# own, Xvfb), so they are not something to run on a login node or beside someone else's work.
#     mkdir -p logs && sbatch tools/suites.sbatch                 # the fourteen that need no video data
#     sbatch tools/suites.sbatch golden                           # and test_golden, which needs the footage:
#         it reads the reference-data folder ($MCDONALD_DATA, else data/mcdonald beside the repository; see
#         tests/reference_data.py) and skips, saying so, any case whose video is not there.
# On four CPUs (2026-09-26): measurement ~4 min, reduction ~1, published and tether seconds, cli ~1.5, gui ~3.5, golden ~5 with the frames on disk.
#
# On a graphics card (2026-11-12): the same suites with the card's arithmetic where a stage has it (docs/method.md, the
# graphics card's section), which is how the goldens are held on both. The job has to be given the card:
#     sbatch --gres=gpu:1 tools/suites.sbatch golden
# Without --gres=gpu:1 every suite runs on the CPU, card or no card (`gpu.given`), and test_gpu checks the card's code
# with NumPy standing in for it. Each run says which it was: the line after this one in the job's log.
# A suite that fails does not stop the ones after it; the job fails if any did.

set -uo pipefail
cd "$SLURM_SUBMIT_DIR"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
# This checkout's code, also in the subprocesses some checks start (`python -m mcdonald.cli`, as the window's "measure it
# again" does): otherwise they import the installed package, which in a worktree is another branch's (2026-10-20, flir1).
export PYTHONPATH="$SLURM_SUBMIT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

if type module &>/dev/null; then
    module load python ffmpeg || true          # site-specific; merlin has no modules
fi

# every figure any suite draws, in its process or a subprocess, is held to the house style (Jacob, 2026-11-07): what
# figures.save cannot clear -- text over a line, over other text, off the figure -- is written here, and fails the job
export MCDONALD_FIGURE_CLASHES="$SLURM_SUBMIT_DIR/logs/figure_clashes_${SLURM_JOB_ID}.txt"
rm -f "$MCDONALD_FIGURE_CLASHES"

python3 -c "from mcdonald import gpu; print('==', gpu.said())"
suites="test_measurement test_reduction test_published test_tether test_audio test_cli test_share test_sweep test_stabilize test_aspect test_waves test_slew test_zoom test_horizon test_focus test_haze test_streak test_camera test_gpu test_gui"
[ "${1:-}" = "golden" ] && suites="$suites test_golden"
failed=""
for s in $suites; do
    echo "== $s  ($(date +%H:%M:%S))"
    srun python3 -u tests/$s.py > "logs/${s}_${SLURM_JOB_ID}.log" 2>&1 || failed="$failed $s"
    echo "   $(grep -c '  PASS' "logs/${s}_${SLURM_JOB_ID}.log") PASS, $(grep -c '  FAIL' "logs/${s}_${SLURM_JOB_ID}.log") FAIL, $(grep -c '  SKIP' "logs/${s}_${SLURM_JOB_ID}.log") SKIP"
    grep '  FAIL' "logs/${s}_${SLURM_JOB_ID}.log" | cut -c1-200
done
if [ -s "$MCDONALD_FIGURE_CLASHES" ]; then
    echo "== figures with text over a line, over other text, or off the figure ($(wc -l < "$MCDONALD_FIGURE_CLASHES")):"
    sort "$MCDONALD_FIGURE_CLASHES" | uniq -c | sort -rn | head -20
    failed="$failed figure-clashes"
fi
[ -z "$failed" ] || { echo "FAILED:$failed"; exit 1; }
echo "ALL SUITES PASS"
