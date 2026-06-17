"""Dose-response figure for the exp 05 PN ladder (CT, draw 773)."""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
df = pd.read_csv(HERE / 'outputs' / 'ladder.csv')
lad = df[df.rung != 'EPT'].copy()
ept = df[df.rung == 'EPT']

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
x = lad.mean_notified_per_index

ax1.plot(x, lad.ct_prev_window_mean, 'o-', color='#2e7d32', label='PN ladder')
for _, r in lad.iterrows():
    ax1.annotate(r.rung, (r.mean_notified_per_index, r.ct_prev_window_mean),
                 textcoords='offset points', xytext=(4, 6), fontsize=8)
if len(ept):
    ax1.plot(ept.mean_notified_per_index, ept.ct_prev_window_mean, 'D',
             color='#d1495b', ms=9, label='EPT (attend→1.0)')
ax1.set_xlabel('mean concurrent partners notified per index')
ax1.set_ylabel('CT prevalence (2030–34 mean)')
ax1.set_title('Prevalence keeps falling with PN coverage\n(no early plateau; EPT ≈ ×5)')
ax1.legend(fontsize=9); ax1.margins(0.1)

ax2.plot(x, lad.cohort_reinf_rate, 's-', color='#d1495b', label='cohort reinfection rate')
ax2b = ax2.twinx()
ax2b.plot(x, lad.ct_new_inf_window / 1e6, '^--', color='#888',
          label='CT incidence (M, right)')
ax2.set_xlabel('mean concurrent partners notified per index')
ax2.set_ylabel('cohort reinfection rate / 100', color='#d1495b')
ax2b.set_ylabel('CT new infections, window (millions)', color='#888')
ax2.set_ylim(0, 1); ax2b.set_ylim(0, 14)
ax2.set_title('…but incidence & reinfection are flat\n(PN shortens duration, not transmission)')

fig.suptitle('Exp 05 — PN intensity ladder (CT, draw 773, POC arm)', fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.95])
(HERE / 'figures').mkdir(exist_ok=True)
fig.savefig(HERE / 'figures' / 'fig1_pn_ladder.png', dpi=150, bbox_inches='tight')
print('wrote', HERE / 'figures' / 'fig1_pn_ladder.png')
