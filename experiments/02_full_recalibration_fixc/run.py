"""
Exp 02 — Full recalibration on Fix C.

Thin wrapper around calibration/artifacts/scripts/run_ensemble.py:
parameterises out-dir to this experiment's outputs/ and invokes the
two-phase pipeline.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PIPELINE = REPO / 'calibration' / 'artifacts' / 'scripts' / 'run_ensemble.py'
OUT = HERE / 'outputs'

if __name__ == '__main__':
    env = os.environ.copy()
    cmd = [
        sys.executable, str(PIPELINE),
        '--phase', 'all',
        '--out-dir', str(OUT),
        '--n-draws', '2000',
        '--seed', '46',           # fresh LHS seed (calibration/zimbabwe used 45)
        '--target-size', '200',
        '--n-seeds', '3',
        '--n-workers', '60',
    ]
    print('Running:', ' '.join(cmd), flush=True)
    sys.exit(subprocess.call(cmd, env=env, cwd=str(REPO)))
