"""Driver — re-fire the per-disease-sustainability calibration with the
BV-in-VDS model edit.

Identical sweep to experiments/02_2026-06-22_calibration_per_disease_sustain
(same 17 priors, same LHS seed, same per-disease sustainability filter), but
runs against the current `model.py`, which now routes symptomatic BV through
VDS (`SimpleBV` + `bv_care` clause in `interventions.seeking_care_vds`). That
edit changes care-seeking volume for some agents, so calibrated betas may
shift slightly.

See README.md for the question. Thin shim around the institutional pipeline.
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
    '--n-draws', '500',      # half of exp 02 to halve wall time; same priors + LHS seed
    '--target-size', '50',
    '--n-seeds', '3',
    '--n-workers', '60',
    '--seed', '45',          # SAME LHS seed as exp 02 for direct draw-by-draw comparability
]


def main():
    extra = sys.argv[1:]
    cmd = [sys.executable, str(PIPELINE), *EXP_ARGS, *extra]
    print('exp 03 (2026-06-22) — calibration re-fire with BV-in-VDS model')
    print('cmd:', ' '.join(cmd))
    print()
    subprocess.run(cmd, check=True)


if __name__ == '__main__':
    main()
