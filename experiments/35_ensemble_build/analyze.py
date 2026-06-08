"""Exp 35 figures — seed robustness distribution."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
df = pd.read_csv(HERE / 'outputs' / 'ensemble_summary.csv')
FIG = HERE / 'figures'
FIG.mkdir(exist_ok=True)

# Panel 1: histogram of pass_sustained across draws
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

ax = axes[0]
sust_dist = df['pass_sustained'].value_counts().sort_index()
labels = [f'{int(v*3)}/3' for v in sust_dist.index]
colors = ['#d62728', '#ff7f0e', '#1f77b4', '#2ca02c']
ax.bar(labels, sust_dist.values, color=[colors[int(v*3)] for v in sust_dist.index])
for i, v in enumerate(sust_dist.values):
    ax.text(i, v + 1, str(int(v)), ha='center', fontsize=10)
ax.set_xlabel('seeds sustained (of 3)')
ax.set_ylabel('number of draws')
ax.set_title('Single-seed selection bias: 39/175 robustly sustain')

# Panel 2: nontrep_f vs FSW prev colored by robustness
ax = axes[1]
for s_lvl, color, lbl in [(0.0, 'gray', '0/3'),
                          (0.33, '#d62728', '1/3'),
                          (0.67, '#ff7f0e', '2/3'),
                          (1.0, '#2ca02c', '3/3 robust')]:
    sub = df[np.isclose(df['pass_sustained'], s_lvl, atol=0.05)]
    ax.scatter(sub['fsw_prev_2019'], sub['nontrep_f_2016'],
               c=color, alpha=0.6, s=40, label=f'{lbl} (n={len(sub)})')
ax.axvspan(0.20, 0.40, color='C2', alpha=0.12, label='FSW band')
ax.axhspan(0.01, 0.05, color='C2', alpha=0.12)
ax.set_xlabel('FSW prev 2019 (seed-mean)')
ax.set_ylabel('nontrep_f 2016 (seed-mean)')
ax.set_title('Robust draws cluster at upper end of sustained basin')
ax.legend(fontsize=9)

fig.tight_layout()
fig.savefig(FIG / 'seed_robustness.png', dpi=130)
print('wrote figures/seed_robustness.png')
