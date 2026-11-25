"""Exp 11 coverage check: exp 10's v4 calibration machinery at all 500 LHS draws x 1 seed, to 2026."""
import importlib.util, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for k, v in dict(N_DRAWS='500', K_SEEDS='1', STOP='2026', N_AGENTS='10000').items():
    os.environ.setdefault(k, v)

spec = importlib.util.spec_from_file_location(
    'exp10', HERE.parent / '10_2026-11-25_v4_calibration' / 'run.py')
exp10 = sys.modules["exp10"] = importlib.util.module_from_spec(spec)  # workers unpickle run_one by module name
spec.loader.exec_module(exp10)
exp10.OUT_DIR = HERE / 'outputs'
exp10.OUT_DIR.mkdir(exist_ok=True)

if __name__ == '__main__':
    exp10.main()
