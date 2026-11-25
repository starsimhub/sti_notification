"""Exp 07: trajectories of the draws acceptable at ACCEPT_TOL=1.0 vs target bands and data."""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run  # noqa: E402

OUT, FIG = HERE / 'outputs', HERE / 'figures'
FIG.mkdir(exist_ok=True)
REPO = HERE.parent.parent
ts = pd.read_parquet(OUT / 'timeseries.parquet')
tol1 = pd.read_csv(OUT / 'per_draw_means_tol1.csv')
tol05 = pd.read_csv(OUT / 'per_draw_means.csv')
priors = pd.read_csv(OUT / 'priors.csv')
keep1 = tol1[tol1.acceptable].draw_idx.tolist()
keep05 = tol05[tol05.acceptable].draw_idx.tolist()
sti_data = pd.read_csv(REPO / 'data' / 'zimbabwe_sti_data.csv')
hiv_data = pd.read_csv(REPO / 'data' / 'zimbabwe_hiv_calib.csv')
HIV_TS = OUT / 'hiv_ts_tol1.parquet'  # from rerun_hiv_ts.py; has new_deaths
hiv_ts = pd.read_parquet(HIV_TS) if HIV_TS.exists() else None

DATA_COL = {'ng_prev_f': 'ng_prevalence', 'ct_prev_f_25_30': 'ct_prevalence_f_25_30', 'tv_prev_f': 'tv_prevalence',
            'ng_new_inf_per_yr': 'ng_new_infections', 'ct_new_inf_per_yr': 'ct_new_infections',
            'tv_new_inf_per_yr': 'tv_new_infections'}
INK, ENV, STRONG, WEAK, BAND = '#1f1f1f', '#d9d9d9', '#1f4fa8', '#8fb3ea', '#2a6fdb'
scale = lambda t: 100 if 'prev' in t else 1e-3
unit = lambda t: '%' if 'prev' in t else 'thousands / yr'

fig, axes = plt.subplots(3, 4, figsize=(16, 11), constrained_layout=True)
for ax, (t, ((lo, hi), (d, key, win, _how))) in zip(axes.flat, run.TARGETS.items()):
    s = scale(t)
    sub = ts[(ts.disease == d) & (ts.result_name == key) & ts.year.between(1990, 2029)]
    wide = sub.pivot(index='year', columns='draw_idx', values='value') * s
    q = wide.quantile([0.05, 0.95], axis=1).T
    ax.fill_between(q.index, q[0.05], q[0.95], color=ENV, lw=0, label='5–95% of all 500 draws')
    ax.fill_between([win[0], win[1]], lo * s, hi * s, color=BAND, alpha=0.22, lw=0, label='target band (fit window)')
    for di in keep1:
        strong = di in keep05
        ax.plot(wide.index, wide[di], color=STRONG if strong else WEAK, lw=2 if strong else 1.2, zorder=3 if strong else 2)
    if t in DATA_COL:
        ax.plot(sti_data.time, sti_data[DATA_COL[t]] * s, 'o', color=INK, ms=3, label='data', zorder=4)
    top = np.nanmax(wide[keep1].values) if keep1 else hi * s
    ax.set_ylim(0, max(top, hi * s) * 1.25)
    ax.set_xlim(1990, 2029)  # 2030 is a partial year (STOP=2030)
    ax.set_title(f'{t}  ({unit(t)})', fontsize=10)
    ax.spines[['top', 'right']].set_visible(False)
axes.flat[0].plot([], [], color=STRONG, lw=2, label=f'acceptable at tol 0.5 (n={len(keep05)})')
axes.flat[0].plot([], [], color=WEAK, lw=1.2, label=f'acceptable at tol 1.0 only (n={len(keep1) - len(keep05)})')
axes.flat[0].legend(fontsize=7.5, frameon=False, loc='upper right')
axes.flat[0].text(0.02, 0.02, 'HIV data are whole-population;\ntarget is ages 15–49, so not shown', transform=axes.flat[0].transAxes, fontsize=7, color='#555555')

# HIV row (not fitted except 15-49 prevalence): whole-pop prevalence, infections, deaths vs data
HIV_PANELS = [('prevalence', 'hiv_prevalence', 100, 'HIV prevalence, whole pop (%)'),
              ('new_infections', 'hiv_new_infections', 1e-3, 'HIV new infections (thousands / yr)'),
              ('new_deaths', 'hiv_new_deaths', 1e-3, 'HIV deaths (thousands / yr)')]
for ax, (rname, dcol, s, title) in zip(axes[2], HIV_PANELS):
    if hiv_ts is not None:
        src = hiv_ts[hiv_ts.result_name == rname]
    else:
        src = ts[(ts.disease == 'hiv') & (ts.result_name == rname)]
    wide = src[src.year.between(1990, 2029)].pivot(index='year', columns='draw_idx', values='value') * s
    for di in keep1:
        if di in wide:
            strong = di in keep05
            ax.plot(wide.index, wide[di], color=STRONG if strong else WEAK, lw=2 if strong else 1.2, zorder=3 if strong else 2)
    if not len(wide.columns):
        ax.text(0.5, 0.5, 'not saved by run.py;\nrerun_hiv_ts.py pending', ha='center', transform=ax.transAxes, color='#555555')
    ax.plot(hiv_data.time, hiv_data[dcol] * s, 'o', color=INK, ms=3, zorder=4)
    ax.set_ylim(0, None); ax.set_xlim(1990, 2029)
    ax.set_title(title + '  — not fitted', fontsize=10)
    ax.spines[['top', 'right']].set_visible(False)
axes[2, 3].axis('off')

# Per-draw table in the spare panel
ax = axes[1, 3]; ax.axis('off')
m = tol1[tol1.acceptable].merge(priors, on='draw_idx')
rows = [[int(r.draw_idx), 'yes' if r.draw_idx in keep05 else '', f'{r.mae:.2f}',
         f'{np.exp(r["log_ng.beta_m2f"]):.3f}', f'{np.exp(r["log_ng.dur_asymp2clear"]):.1f}',
         f'{r.ng_prev_f*100:.1f}', f'{r.ct_prev_f_25_30*100:.1f}', f'{r.tv_prev_f*100:.1f}', f'{r.hiv_prev_15_49*100:.1f}']
        for _, r in m.sort_values('mae').iterrows()]
tab = ax.table(cellText=rows, colLabels=['draw', 'tol .5', 'mae', 'NG β', 'NG dur', 'NG%', 'CT%', 'TV%', 'HIV%'],
               loc='center', cellLoc='center')
tab.auto_set_font_size(False); tab.set_fontsize(7); tab.scale(1.05, 1.3)
fig.suptitle(f'Exp 07: the {len(keep1)} draws acceptable at ACCEPT_TOL=1.0 (K=5 seed means, 10k agents)')
fig.savefig(FIG / 'fig_epi_acceptable_tol1.png', dpi=130)
print('wrote', FIG / 'fig_epi_acceptable_tol1.png', '| draws:', keep1, '| tol0.5:', keep05)
