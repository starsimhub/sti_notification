"""Exp 08: exp 07's calibration rerun with transmission-beta priors narrowed to where exp 07 put each target in band."""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'exp07', HERE.parent / '07_2026-11-24_no_syph_calibration' / 'run.py')
exp07 = sys.modules['exp07'] = importlib.util.module_from_spec(spec)  # workers unpickle run_one by module name
spec.loader.exec_module(exp07)

NARROWED = {  # exp 07 in-band ranges (sustained draws, dist <= 0.5) plus a margin
    'hiv.beta_m2f': ('HIV β (M→F)', 0.010, 0.022, False),
    'ng.beta_m2f':  ('NG β (M→F)',  0.05,  0.40,  True),
    'ct.beta_m2f':  ('CT β (M→F)',  0.06,  0.17,  True),
    'tv.beta_m2f':  ('TV β (M→F)',  0.05,  0.17,  True),
}
for k, v in NARROWED.items():
    assert k in exp07.calib_pars, k
    exp07.calib_pars[k] = v
exp07.OUT_DIR = HERE / 'outputs'
exp07.OUT_DIR.mkdir(exist_ok=True)

if __name__ == '__main__':
    exp07.main()
