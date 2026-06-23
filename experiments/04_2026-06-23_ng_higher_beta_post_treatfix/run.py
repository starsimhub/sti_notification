"""Driver — re-fire the per-disease-sustainability calibration with the
stisim fix/ng-tx patch (rel_treat NaN defense) in place, and the NG
`beta_m2f` prior shifted upward.

Identical sweep to experiments/03_2026-06-22_calibration_bv_in_vds (same 16
of 17 priors, same LHS seed, same per-disease sustainability filter), but:

  * stisim must be on `fix/ng-tx` (731bc1d or later). The fix restores
    `GonorrheaTreatment` to actually clear infections; exp 03's ensemble
    sustained NG only because the bug made treatment a no-op.
  * NG `beta_m2f` prior log-uniform [0.10, 0.60] (was [0.020, 0.299]).
    The new floor is above the highest beta any retained exp 03 draw
    used, on the expectation that even those sustain only marginally
    under working treatment.

See README.md for the question. In-process rather than subprocess so the
prior override takes hold before generate_prior_draws reads calib_pars.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / 'calibration' / 'artifacts' / 'scripts'))
sys.path.insert(0, str(REPO_ROOT))

# Override NG prior before anything else imports calib_pars and reads it
from priors import calib_pars  # noqa: E402
calib_pars['ng.beta_m2f'] = ('NG β (M→F)', 0.10, 0.60, True)

import run_ensemble  # noqa: E402


def main():
    out_dir = HERE / 'outputs'
    sys.argv = [
        'run_ensemble.py',
        '--out-dir', str(out_dir),
        '--n-draws', '500',
        '--target-size', '50',
        '--n-seeds', '3',
        '--n-workers', '60',
        '--seed', '45',          # SAME LHS seed as exp 02 + exp 03
        *sys.argv[1:],
    ]
    print('exp 04 (2026-06-23) — NG β prior shifted up, stisim fix/ng-tx')
    print(f'  NG prior override: ng.beta_m2f = {calib_pars["ng.beta_m2f"]}')
    print(f'  cmd: {" ".join(sys.argv)}')
    print()
    run_ensemble.main()


if __name__ == '__main__':
    main()
