"""Driver for exp 03 — calibration on stisim rc1.5.7.

Thin shim around the institutional pipeline at
``calibration/artifacts/scripts/run_ensemble.py``. All scientific
logic — prior sampling, sim build, summary extraction, candidate
selection, multi-seed re-run — lives there. This file just records
the experiment-specific sizing in code (under ``EXP_ARGS`` below) so
the same script reruns reproducibly.

Run with no arguments to use the defaults. Override anything via the
underlying CLI by passing extra args, e.g.::

    python run.py --n-workers 30   # if the VM is busy
    python run.py --phase 2 --candidates-csv outputs/phase2_candidates.csv

See README.md for the question and success criteria.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
PIPELINE = REPO_ROOT / 'calibration' / 'artifacts' / 'scripts' / 'run_ensemble.py'
OUT_DIR = HERE / 'outputs'


EXP_ARGS = [
    '--out-dir', str(OUT_DIR),
    '--n-draws', '1000',     # half the calibrated baseline; ~45 min on 60 workers
    '--target-size', '100',  # half the calibrated baseline ensemble target
    '--n-seeds', '3',        # multi-seed re-run for the sustainability check
    '--n-workers', '60',     # tune to the VM at run time if needed
    '--seed', '45',          # LHS seed; arbitrary but pinned
]


def main():
    extra = sys.argv[1:]  # forward any extra args (e.g. --phase 2)
    cmd = [sys.executable, str(PIPELINE), *EXP_ARGS, *extra]
    print('exp 03 — calibration on rc1.5.7')
    print('cmd:', ' '.join(cmd))
    print()
    subprocess.run(cmd, check=True)


if __name__ == '__main__':
    main()
