"""Heatmaps for the exp 07 PN × condom grid (CT, draw 773)."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
df = pd.read_csv(HERE / 'outputs' / 'grid.csv')

prev = df.pivot(index='pn_mult', columns='condom_cov', values='ct_prev_window_mean')
inc = df.pivot(index='pn_mult', columns='condom_cov', values='ct_new_inf_window') / 1e6

fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for ax, grid, title, fmt, cmap in (
        (axes[0], prev, 'CT prevalence (2030–34 mean)', '{:.3f}', 'viridis_r'),
        (axes[1], inc, 'CT incidence — new infections (millions)', '{:.2f}', 'magma_r')):
    im = ax.imshow(grid.values, cmap=cmap, aspect='auto', origin='lower')
    ax.set_xticks(range(len(grid.columns)))
    ax.set_xticklabels([f'{c:g}' for c in grid.columns])
    ax.set_yticks(range(len(grid.index)))
    ax.set_yticklabels([f'×{i}' for i in grid.index])
    ax.set_xlabel('condom coverage of diagnosed')
    ax.set_ylabel('PN coverage multiplier')
    ax.set_title(title)
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            ax.text(j, i, fmt.format(grid.values[i, j]), ha='center', va='center',
                    color='white', fontsize=10, fontweight='bold')
    fig.colorbar(im, ax=ax, shrink=0.85)

fig.suptitle('Exp 07 — PN × condoms (CT, draw 773): combine for lowest prevalence AND incidence\n'
             '(prevalence ≈ additive; incidence super-additive — PN enlarges the treated pool condoms protect)',
             fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.93])
(HERE / 'figures').mkdir(exist_ok=True)
fig.savefig(HERE / 'figures' / 'fig1_pn_x_condom_heatmap.png', dpi=150, bbox_inches='tight')
print('wrote fig1_pn_x_condom_heatmap.png')
