"""Hit-count distribution + nontrep vs trep scatter for exp 30."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
rows = [json.loads(l) for l in (HERE / 'outputs' / 'results.jsonl').open()]
df = pd.DataFrame(rows)
df = df[df['status'] == 'ok'].copy()

# Panel 1: hit-count distribution
counts = df['n_pass'].value_counts().sort_index()
fig, ax = plt.subplots(figsize=(8, 4))
colors = ['gray'] * 7 + ['C2'] + ['C2']
ax.bar(counts.index, counts.values, color=[colors[i] for i in counts.index])
ax.set_xlabel('targets passed (of 7)')
ax.set_ylabel('number of draws')
ax.set_title('Exp 30 hit-count: 0/300 draws pass 6+; 3 draws pass 5/7')
for i, v in enumerate(counts.values):
    ax.text(counts.index[i], v + 2, str(int(v)), ha='center', fontsize=9)
fig.tight_layout()
fig.savefig(HERE / 'figures' / 'hit_count_dist.png', dpi=130)
print('wrote figures/hit_count_dist.png')

# Panel 2: nontrep_f vs trep_f scatter, colored by n_pass
fig2, ax = plt.subplots(figsize=(8, 6))
for n in range(6):
    sub = df[df['n_pass'] == n]
    if len(sub) == 0:
        continue
    alpha = 0.3 if n < 3 else 0.7
    ax.scatter(sub['nontrep_f_2016'], sub['trep_f_2016'],
               alpha=alpha, s=30 + 10*n, label=f'n_pass={n} ({len(sub)})')
# Highlight 5-pass draws
five = df[df['n_pass'] == 5]
ax.scatter(five['nontrep_f_2016'], five['trep_f_2016'],
           s=200, marker='*', color='red', label=f'5/7 ({len(five)})', zorder=5)
ax.axvspan(0.01, 0.03, color='C2', alpha=0.15, label='target box')
ax.axhspan(0.05, 0.10, color='C2', alpha=0.15)
ax.axvline(0.01, color='C2', linestyle='--', alpha=0.4)
ax.axvline(0.03, color='C2', linestyle='--', alpha=0.4)
ax.axhline(0.05, color='C2', linestyle='--', alpha=0.4)
ax.axhline(0.10, color='C2', linestyle='--', alpha=0.4)
ax.set_xlabel('nontrep_f at 2016')
ax.set_ylabel('trep_f at 2016')
ax.set_title('Exp 30 — 300 draws: no draws inside the ZIMPHIA loose target box')
ax.legend(loc='upper right', fontsize=8)
fig2.tight_layout()
fig2.savefig(HERE / 'figures' / 'nontrep_vs_trep.png', dpi=130)
print('wrote figures/nontrep_vs_trep.png')

# Panel 3: FSW vs nontrep, separated by sustained
fig3, ax = plt.subplots(figsize=(8, 5))
sus = df[df['new_inf_2030_2040_mean'] > 0]
dec = df[df['new_inf_2030_2040_mean'] == 0]
ax.scatter(dec['fsw_prev_2019'], dec['nontrep_f_2016'],
           color='gray', alpha=0.4, s=22, label=f'decay (n={len(dec)})')
ax.scatter(sus['fsw_prev_2019'], sus['nontrep_f_2016'],
           color='C3', alpha=0.7, s=32, label=f'sustain (n={len(sus)})')
ax.axvspan(0.20, 0.40, color='C2', alpha=0.15)
ax.axhspan(0.01, 0.03, color='C2', alpha=0.15)
ax.set_xlabel('FSW prev 2019')
ax.set_ylabel('nontrep_f 2016')
ax.set_title('FSW concentration vs general spillover — no sustained draws in lower box')
ax.legend()
fig3.tight_layout()
fig3.savefig(HERE / 'figures' / 'fsw_vs_nontrep.png', dpi=130)
print('wrote figures/fsw_vs_nontrep.png')
