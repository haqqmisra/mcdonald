"""`python3 -m mcdonald ...` runs the same command line as `mcdonald ...` (for an agent or a script that has the package on
PYTHONPATH but not the console script on PATH, e.g. a checkout or a snapshot run through Slurm)."""
import sys

from mcdonald.cli import main

if __name__ == "__main__":
    sys.exit(main())
