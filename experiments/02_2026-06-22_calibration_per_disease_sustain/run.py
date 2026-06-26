"""Driver for exp 04 — calibration with per-disease sustainability.

Thin shim around the institutional pipeline at
``calibration/artifacts/scripts/run_ensemble.py``. All scientific
logic lives there; this file records the experiment-specific sizing
in code (``EXP_ARGS`` below) so the same run reproduces.

Differs from exp 03 only in that ``_pipeline.extract_calibration_summary``
now computes a per-disease sustainability flag (HIV/syph/NG/CT/TV
must all sustain through 2030-2040), instead of the syph-only flag
exp 03 used. The pipeline change is in
``calibration/artifacts/scripts/_pipeline.py`` and is part of this
experiment's commit.

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
    '--n-draws', '1000',     # same as exp 03; stricter filter is the only change
    '--target-size', '50',   # smaller target reflecting the stricter filter
    '--n-seeds', '3',
    '--n-workers', '60',
    '--seed', '45',
]


def main():
    extra = sys.argv[1:]
    cmd = [sys.executable, str(PIPELINE), *EXP_ARGS, *extra]
    print('exp 04 — calibration with per-disease sustainability')
    print('cmd:', ' '.join(cmd))
    print()
    subprocess.run(cmd, check=True)


if __name__ == '__main__':
    main()
