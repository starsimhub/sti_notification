"""Exp 09 screen: exp 07's calibration machinery (wide priors) at 300 draws x 1 seed, to 2026, on the corrected demography."""
import importlib.util, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for k, v in dict(N_DRAWS='300', K_SEEDS='1', STOP='2026', N_AGENTS='10000').items():
    os.environ.setdefault(k, v)

spec = importlib.util.spec_from_file_location(
    'exp07', HERE.parent / '07_2026-11-24_no_syph_calibration' / 'run.py')
exp07 = sys.modules["exp07"] = importlib.util.module_from_spec(spec)  # workers unpickle run_one by module name
spec.loader.exec_module(exp07)
exp07.OUT_DIR = HERE / 'outputs'
exp07.OUT_DIR.mkdir(exist_ok=True)

if __name__ == '__main__':
    exp07.main()
