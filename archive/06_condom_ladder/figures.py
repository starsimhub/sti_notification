"""Figures for exp 06 condom ladder + head-to-head with the exp 05 PN ladder.

  fig1_condom_ladder.png      — CT prevalence + incidence vs condom coverage
  fig2_pn_vs_condom_plane.png — CT prevalence-vs-incidence plane: the two
                                levers move orthogonally from the shared base
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
cond = pd.read_csv(HERE / 'outputs' / 'ladder.csv')
pn = pd.read_csv(REPO / 'experiments' / '05_pn_ladder' / 'outputs' / 'ladder.csv')
pn_lad = pn[pn.rung != 'EPT'].copy()

# fig1 — condom dose-response
fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(cond.coverage, cond.ct_prev_window_mean, 'o-', color='#1f6fb2',
        label='CT prevalence (left)')
axb = ax.twinx()
axb.plot(cond.coverage, cond.ct_new_inf_window / 1e6, '^--', color='#d1495b',
         label='CT incidence (M, right)')
ax.set_xlabel('condom/counselling coverage of the diagnosed')
ax.set_ylabel('CT prevalence (2030–34 mean)', color='#1f6fb2')
axb.set_ylabel('CT new infections, window (millions)', color='#d1495b')
ax.set_title('Exp 06 — condoms for the diagnosed:\nboth prevalence AND incidence fall')
fig.tight_layout()
fig.savefig(HERE / 'figures' / 'fig1_condom_ladder.png', dpi=150, bbox_inches='tight')
plt.close(fig)
print('wrote fig1_condom_ladder.png')

# fig2 — prevalence vs incidence plane, both trajectories
fig, ax = plt.subplots(figsize=(7.5, 6))
ax.plot(pn_lad.ct_new_inf_window / 1e6, pn_lad.ct_prev_window_mean, 'o-',
        color='#2e7d32', label='PN ladder (×0→×8)')
for _, r in pn_lad.iterrows():
    ax.annotate(r.rung, (r.ct_new_inf_window / 1e6, r.ct_prev_window_mean),
                textcoords='offset points', xytext=(5, 3), fontsize=8, color='#2e7d32')
ax.plot(cond.ct_new_inf_window / 1e6, cond.ct_prev_window_mean, 's-',
        color='#1f6fb2', label='condom ladder (cov 0→1)')
for _, r in cond.iterrows():
    ax.annotate(f'{r.coverage:g}', (r.ct_new_inf_window / 1e6, r.ct_prev_window_mean),
                textcoords='offset points', xytext=(5, -10), fontsize=8, color='#1f6fb2')
ax.set_xlabel('CT incidence — new infections, window (millions)')
ax.set_ylabel('CT prevalence (2030–34 mean)')
ax.set_title('PN vs condoms move CT orthogonally (draw 773)\n'
             'PN ↓ prevalence at flat incidence; condoms ↓ incidence')
ax.legend()
fig.tight_layout()
fig.savefig(HERE / 'figures' / 'fig2_pn_vs_condom_plane.png', dpi=150, bbox_inches='tight')
plt.close(fig)
print('wrote fig2_pn_vs_condom_plane.png')
