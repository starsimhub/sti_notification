"""Exp 11 coverage figures: prior-predictive trajectories vs data and target bands; targets vs their parameters; joint coverage."""
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
sti = pd.read_csv(REPO / 'data' / 'zimbabwe_sti_data.csv')
hiv = pd.read_csv(REPO / 'data' / 'zimbabwe_hiv_calib.csv')
INK, ENV, BAND, SIM = '#1f1f1f', '#d9d9d9', '#2a6fdb', '#9a9a9a'


def series(d, key):
    sub = ts[(ts.disease == d) & ts.year.between(1990, 2025)]
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
    ('CT prevalence, women 25-30', 'ct', 'prevalence_f_25_30', 100, '%', ['ct_prev_f_25_30'], (sti, 'ct_prevalence_f_25_30')),
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
    q = wide.quantile([0.05, 0.5, 0.95], axis=1).T
    ax.fill_between(q.index, q[0.05], q[0.95], color=ENV, lw=0, label='5-95% of draws')
    ax.plot(q.index, q[0.5], color=SIM, lw=1, label='median')
    for t in tgts:
        (lo, hi), (_d, _k, win, _h) = T[t]
        ax.fill_between([win[0], win[1] + 0.99], lo * s, hi * s, color=BAND, alpha=0.3, lw=0)
        frac = m[t].between(lo, hi).mean()
        ax.text(win[0], hi * s, f'{frac:.0%} in band', fontsize=7, color=BAND, va='bottom')
    if data is not None:
        df, col = data
        ax.plot(df.time, df[col] * s, 'o', color=INK, ms=2.5, label='data')
    ax.set_xlim(1990, 2025)
    ax.set_ylim(0, max(np.nanpercentile(wide.values, 97), max(T[t][0][1] for t in tgts) * s) * 1.15)
    ax.set_title(f'{title} ({unit})', fontsize=10)
    ax.spines[['top', 'right']].set_visible(False)
axes.flat[0].legend(fontsize=7, frameon=False, loc='upper right')
for ax in axes.flat[len(PANELS):]:
    ax.axis('off')

# Joint coverage within each pathogen, in the spare panels
groups = {
    'HIV (prev, deaths, 15-49)': ['hiv_prev_15_49', 'hiv_prev_2000s', 'hiv_prev_2010s', 'hiv_deaths_2000s', 'hiv_deaths_2010s'],
    'HIV + infections': ['hiv_prev_15_49', 'hiv_prev_2000s', 'hiv_prev_2010s', 'hiv_deaths_2000s', 'hiv_deaths_2010s', 'hiv_inf_2000s', 'hiv_inf_2010s'],
    'NG (prev, young)': ['ng_prev', 'ng_prev_f_18_24_stich'],
    'NG + incidence': ['ng_prev', 'ng_prev_f_18_24_stich', 'ng_new_inf_per_yr'],
    'CT (25-30, young)': ['ct_prev_f_25_30', 'ct_prev_f_18_24_stich'],
    'TV (adults, young)': ['tv_prev', 'tv_prev_f_18_24_stich'],
}
dist = lambda t: m[f'dist_{t}']
rows = []
for g, ts_ in groups.items():
    in_band = np.logical_and.reduce([dist(t) == 0 for t in ts_])
    near = np.logical_and.reduce([dist(t) <= exp10.ACCEPT.get(t, 0.5) for t in ts_])
    rows.append([g, int(in_band.sum()), int(near.sum())])
ax = axes.flat[-2]; ax.axis('off')
tab = ax.table(cellText=rows, colLabels=['pathogen targets', 'all in band', 'all within tol'], loc='center', cellLoc='left')
tab.auto_set_font_size(False); tab.set_fontsize(8); tab.scale(1, 1.5)
n = m.draw_idx.nunique()
fig.suptitle(f'Exp 11 prior predictive on Starsim 4: {n} LHS draws × 1 seed, 10k agents (blue = target band over its window)')
fig.savefig(FIG / 'fig_coverage_trajectories.png', dpi=110)

# Each target against its own pathogen's parameters
PARS = {'hiv': ['hiv.beta_m2f', 'hiv.rel_init_prev', 'log_hiv.rel_death'], 'ng': ['log_ng.beta_m2f', 'log_ng.dur_asymp2clear'],
        'ct': ['log_ct.beta_m2f'], 'tv': ['log_tv.beta_m2f']}
tlist = [t for t in T]
fig, axes = plt.subplots(len(tlist), 3, figsize=(10, 2.0 * len(tlist)), constrained_layout=True)
for i, t in enumerate(tlist):
    d = T[t][1][0]
    (lo, hi), _ = T[t]
    for j in range(3):
        ax = axes[i, j]
        if j >= len(PARS[d]):
            ax.axis('off'); continue
        p = PARS[d][j]
        inb = m[t].between(lo, hi)
        ax.scatter(m[p], m[t], s=4, color=SIM)
        ax.scatter(m.loc[inb, p], m.loc[inb, t], s=6, color=BAND)
        ax.axhspan(lo, hi, color=BAND, alpha=0.15, lw=0)
        ax.set_ylim(0, max(hi * 4, np.nanpercentile(m[t], 50) * 1.2))
        ax.tick_params(labelsize=6)
        ax.set_xlabel(p, fontsize=7)
        if j == 0: ax.set_ylabel(t, fontsize=7)
fig.savefig(FIG / 'fig_coverage_params.png', dpi=100)

print(pd.DataFrame(rows, columns=['group', 'all_in_band', 'all_within_tol']).to_string(index=False))
print()
for t in tlist:
    (lo, hi), _ = T[t]
    v = m[t].dropna()
    print(f'{t:24s} band {lo:.4g}-{hi:.4g} | 5/50/95% {np.percentile(v, 5):.4g} / {np.percentile(v, 50):.4g} / {np.percentile(v, 95):.4g} | in band {v.between(lo, hi).mean():.0%}')
print('\nvalidation (median, 5-95%):')
for v, dval in exp10.VALIDATION_DATA.items():
    x = m[v].dropna()
    print(f'  {v:30s} {x.median():.3f} ({x.quantile(.05):.3f}-{x.quantile(.95):.3f}) | data {dval:.3f}')
