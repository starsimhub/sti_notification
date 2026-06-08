"""Exp 36 figures — ensemble structure across thresholds."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
df = pd.read_csv(HERE / 'outputs' / 'full_summary.csv')
FIG = HERE / 'figures'
FIG.mkdir(exist_ok=True)

# Panel 1: ensemble cascade — n draws at each filter
filters = [
    ('all 545\n3-seed coverage', df),
    ('sustained 3/3', df[df['pass_sustained']==1.0]),
    ('+ n_pass\n≥ 4', df[(df['pass_sustained']==1.0) & (df['n_pass_mean']>=4)]),
    ('+ n_pass\n≥ 4.5', df[(df['pass_sustained']==1.0) & (df['n_pass_mean']>=4.5)]),
    ('+ n_pass\n≥ 5', df[(df['pass_sustained']==1.0) & (df['n_pass_mean']>=5)]),
]
labels = [f[0] for f in filters]
counts = [len(f[1]) for f in filters]
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
ax = axes[0]
colors = ['gray', '#1f77b4', '#2ca02c', '#ff7f0e', '#d62728']
bars = ax.bar(labels, counts, color=colors)
for bar, c in zip(bars, counts):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 8,
            str(int(c)), ha='center', fontsize=11, fontweight='bold')
ax.set_ylabel('number of draws')
ax.set_title('Ensemble candidates by quality filter')
ax.axhline(100, color='C2', linestyle='--', alpha=0.6, label='100-target')
ax.legend()

# Panel 2: scatter — FSW prev vs nontrep_f, colored by quality tier
ax = axes[1]
sus3 = df[df['pass_sustained']==1.0].copy()
sus3['tier'] = pd.cut(sus3['n_pass_mean'],
                       bins=[0, 4, 4.5, 5, 10],
                       labels=['<4', '4-4.5', '4.5-5', '≥5'])
tier_colors = {'<4': 'gray', '4-4.5': '#1f77b4', '4.5-5': '#ff7f0e', '≥5': '#d62728'}
for t, c in tier_colors.items():
    sub = sus3[sus3['tier']==t]
    ax.scatter(sub['fsw_prev_2019'], sub['nontrep_f_2016'],
               c=c, alpha=0.7, s=50, label=f'n_pass {t} (n={len(sub)})')
ax.axvspan(0.20, 0.40, color='C2', alpha=0.12, label='FSW target band')
ax.axhspan(0.01, 0.05, color='C2', alpha=0.12)
ax.set_xlabel('FSW prev 2019 (3-seed mean)')
ax.set_ylabel('nontrep_f 2016 (3-seed mean)')
ax.set_title('Sustained 3/3 cluster: 125-draw ensemble (mean n_pass≥4)')
ax.legend(fontsize=9, loc='upper left')

fig.tight_layout()
fig.savefig(FIG / 'ensemble_cascade.png', dpi=130)
print('wrote figures/ensemble_cascade.png')

# Panel 3: per-target hit rate across thresholds
fig2, ax = plt.subplots(figsize=(11, 5))
target_cols = ['fsw_band','primary_band','secondary_band','hiv_trep_ratio_band',
               'hiv_pos_trep_band','trep_band','nontrep_band']
labels = ['FSW', 'primary', 'secondary', 'HIV ratio', 'HIV+ abs', 'trep', 'nontrep']
clusters = [
    ('3/3 only (n=145)', df[df['pass_sustained']==1.0]),
    ('+ n_pass≥4 (n=125)', df[(df['pass_sustained']==1.0) & (df['n_pass_mean']>=4)]),
    ('+ n_pass≥5 (n=23)', df[(df['pass_sustained']==1.0) & (df['n_pass_mean']>=5)]),
]
x = np.arange(len(target_cols))
w = 0.27
for i, (lbl, sub) in enumerate(clusters):
    rates = []
    for t in target_cols:
        c = f'pass_{t}'
        if c in sub.columns and len(sub) > 0:
            rates.append(100 * (sub[c] == 1.0).sum() / len(sub))
        else:
            rates.append(0)
    ax.bar(x + (i-1)*w, rates, w, label=lbl, alpha=0.85)
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=10)
ax.set_ylabel('% of draws hitting target in all 3 seeds')
ax.set_title('Per-target hit rate by ensemble filter')
ax.set_ylim(0, 105)
ax.axhline(50, color='gray', linestyle=':', alpha=0.5)
ax.legend(fontsize=9)
fig2.tight_layout()
fig2.savefig(FIG / 'per_target_by_cluster.png', dpi=130)
print('wrote figures/per_target_by_cluster.png')
