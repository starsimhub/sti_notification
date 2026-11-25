"""Exp 12 ensemble figure: the retained draws against data and target bands, with the envelope of all combinations."""
import importlib.util
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
spec = importlib.util.spec_from_file_location('exp10', HERE.parent / '10_2026-11-25_v4_calibration' / 'run.py')
exp10 = sys.modules['exp10'] = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exp10)
T = exp10.TARGETS

OUT, FIG = HERE / 'outputs', HERE / 'figures'
FIG.mkdir(exist_ok=True)
ts = pd.read_parquet(OUT / 'timeseries.parquet')
m = pd.read_csv(OUT / 'priors.csv').merge(pd.read_csv(OUT / 'per_draw_means.csv'), on='draw_idx')
keep = m[m.acceptable].sort_values('mae').head(30).draw_idx.tolist()
STRONG = '#1f4fa8'
sti = pd.read_csv(REPO / 'data' / 'zimbabwe_sti_data.csv')
hiv = pd.read_csv(REPO / 'data' / 'zimbabwe_hiv_calib.csv')
INK, ENV, BAND, SIM = '#1f1f1f', '#d9d9d9', '#2a6fdb', '#9a9a9a'


def series(d, key):
    sub = ts[(ts.disease == d) & ts.year.between(1990, 2029)]
    if isinstance(key, list):  # weighted young-women series
        return sum(w * sub[sub.result_name == k].pivot(index='year', columns='draw_idx', values='value') for k, w in key)
    return sub[sub.result_name == key].pivot(index='year', columns='draw_idx', values='value')


# (title, disease, key, scale, unit, targets on it, data (frame, column))
PANELS = [
    ('HIV prevalence 15-49', 'hiv', 'prevalence_15_49', 100, '%', ['hiv_prev_15_49'], None),
    ('HIV prevalence, whole pop', 'hiv', 'prevalence', 100, '%', ['hiv_prev_2000s', 'hiv_prev_2010s'], (hiv, 'hiv_prevalence')),
    ('HIV new infections', 'hiv', 'new_infections', 1e-3, 'k/yr', ['hiv_inf_2000s', 'hiv_inf_2010s'], (hiv, 'hiv_new_infections')),
    ('HIV deaths', 'hiv', 'new_deaths', 1e-3, 'k/yr', ['hiv_deaths_2000s', 'hiv_deaths_2010s'], (hiv, 'hiv_new_deaths')),
    ('NG prevalence, adults', 'ng', 'prevalence', 100, '%', ['ng_prev'], (sti, 'ng_prevalence')),
    ('CT prevalence, women 25-30 (not fitted)', 'ct', 'prevalence_f_25_30', 100, '%', [], (sti, 'ct_prevalence_f_25_30')),
    ('TV prevalence, adults', 'tv', 'prevalence', 100, '%', ['tv_prev'], (sti, 'tv_prevalence')),
    ('NG prevalence, women 18-24', 'ng', exp10.YOUNG, 100, '%', ['ng_prev_f_18_24_stich'], None),
    ('CT prevalence, women 18-24', 'ct', exp10.YOUNG, 100, '%', ['ct_prev_f_18_24_stich'], None),
    ('TV prevalence, women 18-24', 'tv', exp10.YOUNG, 100, '%', ['tv_prev_f_18_24_stich'], None),
    ('NG new infections', 'ng', 'new_infections', 1e-3, 'k/yr', ['ng_new_inf_per_yr'], (sti, 'ng_new_infections')),
    ('CT new infections', 'ct', 'new_infections', 1e-3, 'k/yr', ['ct_new_inf_per_yr'], (sti, 'ct_new_infections')),
    ('TV new infections', 'tv', 'new_infections', 1e-3, 'k/yr', ['tv_new_inf_per_yr'], (sti, 'tv_new_infections')),
]

fig, axes = plt.subplots(4, 4, figsize=(18, 14), constrained_layout=True)
for ax, (title, d, key, s, unit, tgts, data) in zip(axes.flat, PANELS):
    wide = series(d, key) * s
    q = wide.quantile([0.05, 0.95], axis=1).T
    ax.fill_between(q.index, q[0.05], q[0.95], color=ENV, lw=0, label='5-95% of all 200 combinations')
    for di in keep:
        if di in wide:
            ax.plot(wide.index, wide[di], color=STRONG, lw=0.8, alpha=0.6)
    for t in tgts:
        (lo, hi), (_d, _k, win, _h) = T[t]
        ax.fill_between([win[0], win[1] + 0.99], lo * s, hi * s, color=BAND, alpha=0.3, lw=0)
    if data is not None:
        df, col = data
        ax.plot(df.time, df[col] * s, 'o', color=INK, ms=2.5, label='data')
    top = np.nanmax(wide[[k for k in keep if k in wide]].values)
    ax.set_ylim(0, max(top, max([T[t][0][1] for t in tgts] or [0]) * s) * 1.2)
    ax.set_xlim(1990, 2029)
    ax.set_title(f'{title} ({unit})', fontsize=10)
    ax.spines[['top', 'right']].set_visible(False)
axes.flat[0].plot([], [], color=STRONG, lw=1, label=f'retained {len(keep)} draws (K=5 seed means)')
axes.flat[0].legend(fontsize=7, frameon=False, loc='upper right')
for ax in axes.flat[len(PANELS):]:
    ax.axis('off')
ax = axes.flat[-2]
rows = [[v.replace('_', ' '), f"{m.loc[m.draw_idx.isin(keep), v].median():.2f}", f"{dv:.2f}"] for v, dv in exp10.VALIDATION_DATA.items()]
tab = ax.table(cellText=rows, colLabels=['validation (not fitted)', 'model median', 'data'], loc='center', cellLoc='left')
tab.auto_set_font_size(False); tab.set_fontsize(8); tab.scale(1, 1.6)
fig.suptitle(f'Exp 12 calibrated ensemble (Starsim 4): {int(m.acceptable.sum())}/{len(m)} combinations acceptable; top {len(keep)} shown')
fig.savefig(FIG / 'fig_ensemble.png', dpi=110)
print('wrote', FIG / 'fig_ensemble.png')
