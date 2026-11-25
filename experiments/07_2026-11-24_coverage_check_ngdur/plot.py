"""Coverage check figures: prior-predictive trajectories and scalar targets vs data and bands."""
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
spec = importlib.util.spec_from_file_location('exp07', HERE.parent / '07_2026-11-24_no_syph_calibration' / 'run.py')
exp07 = sys.modules['exp07'] = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exp07)
TARGETS = exp07.TARGETS

OUT = HERE / 'outputs'
FIG = HERE / 'figures'
FIG.mkdir(exist_ok=True)
ts = pd.read_parquet(OUT / 'timeseries.parquet')
per_draw = pd.read_csv(OUT / 'per_draw_means.csv')
priors = pd.read_csv(OUT / 'priors.csv')
sti_data = pd.read_csv(REPO / 'data' / 'zimbabwe_sti_data.csv')
hiv_data = pd.read_csv(REPO / 'data' / 'zimbabwe_hiv_calib.csv')

DATA_COL = {  # target -> (data frame, column)
    'hiv_prev_15_49': (hiv_data, 'hiv_prevalence'),
    'ng_prev_f': (sti_data, 'ng_prevalence'),
    'ct_prev_f_25_30': (sti_data, 'ct_prevalence_f_25_30'),
    'tv_prev_f': (sti_data, 'tv_prevalence'),
    'ng_new_inf_per_yr': (sti_data, 'ng_new_infections'),
    'ct_new_inf_per_yr': (sti_data, 'ct_new_infections'),
    'tv_new_inf_per_yr': (sti_data, 'tv_new_infections'),
}
INK, SIM, BAND = '#1f1f1f', '#9a9a9a', '#2a6fdb'
scale = lambda t: 100 if 'prev' in t else 1e-3
unit = lambda t: '%' if 'prev' in t else 'thousands / yr'

# --- Fig 1: trajectories ---------------------------------------------------
fig, axes = plt.subplots(2, 4, figsize=(16, 7), constrained_layout=True)
for ax, (t, ((lo, hi), (d, key, win, _how))) in zip(axes.flat, TARGETS.items()):
    s = scale(t)
    sub = ts[(ts.disease == d) & (ts.result_name == key) & ts.year.between(1990, 2025)]
    wide = sub.pivot(index='year', columns='draw_idx', values='value') * s
    ax.plot(wide.index, wide.values, color=SIM, lw=0.6, alpha=0.35)
    q = wide.quantile([0.05, 0.5, 0.95], axis=1).T
    ax.plot(q.index, q[0.05], color=INK, lw=1, ls='--')
    ax.plot(q.index, q[0.95], color=INK, lw=1, ls='--', label='5–95% of draws')
    ax.fill_between([win[0], win[1]], lo * s, hi * s, color=BAND, alpha=0.25, lw=0, label='target band')
    df, col = DATA_COL[t]
    ax.plot(df.time, df[col] * s, 'o', color=INK, ms=3, label='data')
    ax.set_xlim(1990, 2025)  # 2026 is a partial year (STOP=2026)
    ax.set_ylim(0, min(np.nanpercentile(wide.values, 99) * 1.1, max(hi * s * 4, np.nanmax(df[col]) * s * 1.5)))
    ax.set_title(f'{t}  ({unit(t)})', fontsize=10)
    ax.spines[['top', 'right']].set_visible(False)
axes.flat[0].legend(fontsize=8, frameon=False, loc='upper left')

# Coverage table in the spare panel
ax = axes.flat[-1]; ax.axis('off')
rows = []
for t, ((lo, hi), _) in TARGETS.items():
    v = per_draw[t].dropna()
    q5, q50, q95 = np.percentile(v, [5, 50, 95])
    rows.append([t, f'{lo*scale(t):.4g}–{hi*scale(t):.4g}', f'{q5*scale(t):.3g} / {q50*scale(t):.3g} / {q95*scale(t):.3g}',
                 f'{((v >= lo) & (v <= hi)).mean():.0%}'])
tab = ax.table(cellText=rows, colLabels=['target', 'band', 'prior pred 5/50/95%', 'in band'], loc='center', cellLoc='left')
tab.auto_set_font_size(False); tab.set_fontsize(7.5); tab.scale(1, 1.4)
fig.suptitle(f'Exp 07 prior predictive: {per_draw.draw_idx.nunique()} LHS draws × 1 seed, 10k agents (shading = target band over fit window)')
fig.savefig(FIG / 'fig_coverage_trajectories.png', dpi=130)

# --- Fig 2: parameters of draws in band, per target -------------------------
pars = [c for c in priors.columns if c != 'draw_idx']
m = priors.merge(per_draw, on='draw_idx')
fig, axes = plt.subplots(len(TARGETS), len(pars), figsize=(2.1 * len(pars), 1.6 * len(TARGETS)),
                         constrained_layout=True, sharex='col')
for i, (t, ((lo, hi), _)) in enumerate(TARGETS.items()):
    inb = (m[t] >= lo) & (m[t] <= hi)
    for j, p in enumerate(pars):
        ax = axes[i, j]
        ax.scatter(m[p], m[t] * scale(t), s=5, color=SIM)
        ax.scatter(m.loc[inb, p], m.loc[inb, t] * scale(t), s=8, color=BAND)
        ax.axhspan(lo * scale(t), hi * scale(t), color=BAND, alpha=0.15, lw=0)
        ax.tick_params(labelsize=6)
        if i == len(TARGETS) - 1: ax.set_xlabel(p, fontsize=7)
        if j == 0: ax.set_ylabel(t, fontsize=7)
fig.suptitle('Target vs prior parameter (blue = draw lands in band)')
fig.savefig(FIG / 'fig_coverage_params.png', dpi=110)

print(pd.DataFrame(rows, columns=['target', 'band', 'prior_pred_5_50_95', 'frac_in_band']).to_string(index=False))
print('\nsustained (any seed) per disease:', {d: m[f'min_seeds_sustained'].ge(1).mean() for d in ['all']})
