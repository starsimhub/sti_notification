"""Exp 13: exp 12's 200 combinations, rerun with SimpleBV p_clear=1 and the VDS presenter target (Chirenje 2018)."""
import importlib.util
import os
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
COMBOS = HERE.parent / '12_2026-11-25_mix_and_match' / 'outputs' / 'combos.csv'
combos = pd.read_csv(COMBOS)
os.environ.setdefault('N_DRAWS', str(len(combos)))

spec = importlib.util.spec_from_file_location('exp10', HERE.parent / '10_2026-11-25_v4_calibration' / 'run.py')
exp10 = sys.modules['exp10'] = importlib.util.module_from_spec(spec)  # workers unpickle run_one by module name
spec.loader.exec_module(exp10)
exp10.generate_prior_draws = lambda *_a, **_k: combos[[c for c in combos.columns if not c.startswith('src_')]]
exp10.OUT_DIR = HERE / 'outputs'

if __name__ == '__main__':
    exp10.main()
