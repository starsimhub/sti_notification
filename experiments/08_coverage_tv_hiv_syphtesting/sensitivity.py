"""Spearman rank correlation between prior draws and key outputs."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import sciris as sc
import numpy as np
from scipy.stats import spearmanr

RESULTS = Path(__file__).parent / 'results'

dfs = sc.load(RESULTS / 'coverage_dfs.obj')
draws = sc.load(RESULTS / 'coverage_draws.obj')

par_names = list(draws[0].keys())
par_matrix = np.array([[d[p] for p in par_names] for d in draws])

targets = [
    ('hiv.prevalence', 2005, 'HIV'),
    ('ng.prevalence', 2010, 'NG'),
    ('ct.prevalence_f_25_30', 2010, 'CT'),
    ('tv.prevalence', 2010, 'TV'),
    ('syph.prevalence_f', 2016, 'Syph'),
    ('syph.serological_prevalence_f', 2016, 'SeroF'),
    ('syph.pregnant_prevalence', 2010, 'ANC'),
    ('syph_hiv_coinfection.syph_prev_has_hiv', 2016, 'SH+'),
]

out_vals = {}
for col, year, label in targets:
    out_vals[label] = np.array([df[df['time'] == year][col].values[0] for df in dfs])

labels = [t[2] for t in targets]
hdr = 'Parameter'.ljust(35) + ''.join(l.rjust(7) for l in labels)
print(hdr)
print('-' * len(hdr))

for i, pname in enumerate(par_names):
    cells = pname.ljust(35)
    for label in labels:
        rho, _ = spearmanr(par_matrix[:, i], out_vals[label])
        star = '*' if abs(rho) > 0.3 else ' '
        cells += ('%+.2f%s' % (rho, star)).rjust(7)
    print(cells)
