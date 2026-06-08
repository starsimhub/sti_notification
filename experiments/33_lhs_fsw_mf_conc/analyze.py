"""Exp 33 figures — hit-count, nontrep vs trep, HIV+ trep vs ratio,
parameter region of top draws."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
rows = [json.loads(l) for l in (HERE / 'outputs' / 'results.jsonl').open()]
df = pd.DataFrame(rows)
df = df[df['status'] == 'ok'].copy()
priors = pd.read_csv(HERE / 'outputs' / 'prior_draws.csv')

FIG = HERE / 'figures'
FIG.mkdir(exist_ok=True)


# Panel 1: hit-count distribution
counts = df['n_pass'].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(8, 4))
colors = ['gray'] * 7 + ['C2', 'C2', 'C2']
ax.bar(counts.index, counts.values,
       color=[colors[i] if i < len(colors) else 'C2' for i in counts.index])
ax.set_xlabel('targets passed (of 9)')
ax.set_ylabel('number of draws')
n_7plus = int((df['n_pass'] >= 7).sum())
n_6 = int((df['n_pass'] == 6).sum())
ax.set_title(f'Exp 33 hit-count: {n_7plus}/300 pass 7+/9; {n_6} pass 6/9')
for i, v in enumerate(counts.values):
    ax.text(counts.index[i], v + 2, str(int(v)), ha='center', fontsize=9)
fig.tight_layout()
fig.savefig(FIG / 'hit_count_dist.png', dpi=130)
print('wrote figures/hit_count_dist.png')


# Panel 2: nontrep vs trep — colored by SUSTAINED vs DECAYED
sustained = df['passes'].apply(lambda p: p.get('sustained', False))
df['_sustained'] = sustained

fig2, ax = plt.subplots(figsize=(8, 6))
decayed = df[~df['_sustained']]
sust = df[df['_sustained']]
ax.scatter(decayed['nontrep_f_2016'], decayed['trep_f_2016'],
           alpha=0.4, s=30, color='gray', label=f'decayed (n={len(decayed)})')
ax.scatter(sust['nontrep_f_2016'], sust['trep_f_2016'],
           alpha=0.7, s=40, color='C3', label=f'sustained (n={len(sust)})')
six = df[df['n_pass'] == 6]
ax.scatter(six['nontrep_f_2016'], six['trep_f_2016'],
           s=300, marker='*', color='red', label=f'6/9 ({len(six)})',
           zorder=5, edgecolor='black', linewidth=1)
ax.axvspan(0.01, 0.05, color='C2', alpha=0.15, label='target band (relaxed)')
ax.axhspan(0.05, 0.10, color='C2', alpha=0.15)
for x in (0.01, 0.05):
    ax.axvline(x, color='C2', linestyle='--', alpha=0.4)
for y in (0.05, 0.10):
    ax.axhline(y, color='C2', linestyle='--', alpha=0.4)
ax.set_xlabel('nontrep_f at 2016')
ax.set_ylabel('trep_f at 2016')
n_in_box_sust = ((sust['nontrep_f_2016'] >= 0.01) & (sust['nontrep_f_2016'] <= 0.05) &
                 (sust['trep_f_2016'] >= 0.05) & (sust['trep_f_2016'] <= 0.10)).sum()
ax.set_title(f'Exp 33: no SUSTAINED draws in box ({n_in_box_sust}/{len(sust)})\n'
             '(box draws are dying epidemics transiting through band)')
ax.legend(loc='upper right', fontsize=9)
fig2.tight_layout()
fig2.savefig(FIG / 'nontrep_vs_trep.png', dpi=130)
print('wrote figures/nontrep_vs_trep.png')


# Panel 3: HIV+ trep vs HIV+/HIV- ratio  — NEW
df_r = df.dropna(subset=['hiv_trep_ratio_2016'])
fig3, ax = plt.subplots(figsize=(8, 6))
for n in range(7):
    sub = df_r[df_r['n_pass'] == n]
    if len(sub) == 0:
        continue
    alpha = 0.3 if n < 4 else 0.7
    ax.scatter(sub['hiv_pos_trep_2016'], sub['hiv_trep_ratio_2016'],
               alpha=alpha, s=20 + 8*n, label=f'n_pass={n} ({len(sub)})')
six = df_r[df_r['n_pass'] == 6]
ax.scatter(six['hiv_pos_trep_2016'], six['hiv_trep_ratio_2016'],
           s=300, marker='*', color='red', label=f'6/9 ({len(six)})', zorder=5)
# Target bands
ax.axvspan(0.05, 0.09, color='C2', alpha=0.15, label='target box (ZIMPHIA)')
ax.axhspan(3.0, 6.0, color='C2', alpha=0.15)
# ZIMPHIA point estimate
ax.scatter([0.071], [3.7], marker='X', s=300, color='black',
           label='ZIMPHIA 2015-16', zorder=6)
ax.set_xlabel('HIV+ trep+ prev at 2016')
ax.set_ylabel('HIV+/HIV- trep ratio at 2016')
ax.set_title('HIV-stratification: ratio is reachable, absolute level is hot')
ax.set_xscale('log')
ax.legend(loc='lower right', fontsize=8)
fig3.tight_layout()
fig3.savefig(FIG / 'hiv_strat.png', dpi=130)
print('wrote figures/hiv_strat.png')


# Panel 4: per-target pass rate
targets = ['fsw_band','nontrep_band','trep_band','primary_band','secondary_band',
           'early_lat_band','sustained','hiv_pos_trep_band','hiv_trep_ratio_band']
pass_rates_all = []
pass_rates_5plus = []
df5 = df[df['n_pass'] >= 5]
for t in targets:
    pass_rates_all.append(100 * df['passes'].apply(lambda p: p[t]).sum() / len(df))
    pass_rates_5plus.append(100 * df5['passes'].apply(lambda p: p[t]).sum() / len(df5))
fig4, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(targets))
ax.bar(x - 0.2, pass_rates_all, 0.4, label=f'all 300 draws', color='C0', alpha=0.7)
ax.bar(x + 0.2, pass_rates_5plus, 0.4, label=f'5+/9 cluster (n={len(df5)})',
       color='C2', alpha=0.85)
ax.set_xticks(x)
ax.set_xticklabels([t.replace('_band', '').replace('_', '\n') for t in targets],
                   fontsize=8)
ax.set_ylabel('% of draws passing')
ax.set_title('Per-target pass rate: hard targets are trep, nontrep, fsw, HIV+ absolute')
ax.axhline(50, color='gray', linestyle=':', alpha=0.5)
ax.legend()
fig4.tight_layout()
fig4.savefig(FIG / 'per_target_pass.png', dpi=130)
print('wrote figures/per_target_pass.png')


# Panel 5: Lorenz curve(s) from top draws — superspreader concentration
def lorenz_from_events(events_path):
    if not events_path.exists():
        return None, None
    with events_path.open() as f:
        d = json.load(f)
    counts = sorted(d['src_count'].values(), reverse=True)
    if not counts:
        return None, None
    cum = np.cumsum(counts)
    if cum[-1] == 0:
        return None, None
    pop_share = np.arange(1, len(cum) + 1) / len(cum)
    trans_share = cum / cum[-1]
    return pop_share, trans_share


top_n_pass = df.sort_values('n_pass', ascending=False).head(6)['draw_idx'].tolist()
fig5, ax = plt.subplots(figsize=(7, 6))
for di in top_n_pass:
    p, t = lorenz_from_events(HERE / 'outputs' / 'events' / f'events_{di:04d}.json')
    if p is None:
        continue
    np_row = int(df[df['draw_idx'] == di]['n_pass'].iloc[0])
    ax.plot(p, t, alpha=0.7, label=f'draw {di} (n_pass={np_row})')
ax.plot([0, 1], [0, 1], 'k--', alpha=0.4, label='equality')
ax.set_xlabel('cumulative share of source agents (sorted desc)')
ax.set_ylabel('cumulative share of transmissions')
ax.set_title('Transmission concentration (Lorenz) — top draws')
ax.legend(fontsize=8, loc='lower right')
ax.set_xlim(0, 1)
ax.set_ylim(0, 1.02)
fig5.tight_layout()
fig5.savefig(FIG / 'lorenz_top_draws.png', dpi=130)
print('wrote figures/lorenz_top_draws.png')


# Panel 6: parameter region of top draws (prior values for 5+/9 cluster)
df5p = df[df['n_pass'] >= 5].merge(priors, on='draw_idx')
param_cols = [c for c in priors.columns if c != 'draw_idx']
fig6, axes = plt.subplots(4, 4, figsize=(14, 10))
for ax, col in zip(axes.flat, param_cols):
    all_vals = priors[col]
    top_vals = df5p[col]
    if col.startswith('log_'):
        all_vals = np.exp(all_vals); top_vals = np.exp(top_vals)
        label = col[4:]
    else:
        label = col
    ax.hist(all_vals, bins=15, alpha=0.4, color='gray', label='all 300', density=True)
    ax.hist(top_vals, bins=15, alpha=0.7, color='C2',
            label=f'5+/9 (n={len(df5p)})', density=True)
    ax.set_title(label.split('.')[-1], fontsize=9)
    ax.tick_params(labelsize=7)
for ax in axes.flat[len(param_cols):]:
    ax.axis('off')
axes[0, 0].legend(fontsize=7)
fig6.suptitle('Exp 33 — parameter region of the 5+/9 cluster vs all draws', y=1.01)
fig6.tight_layout()
fig6.savefig(FIG / 'param_region_top.png', dpi=130, bbox_inches='tight')
print('wrote figures/param_region_top.png')

print()
print(f'figures in {FIG}/')
