"""
Post-run diagnostic figures for exp 22.

Loads outputs/results.jsonl and outputs/series.pkl, produces:
  figures/coverage_vs_targets.png  — distribution of summary metrics among
    sustainers vs decayers, with data targets + acceptance bands.
  figures/bifurcation_scatter.png  — detect_f_2016 vs prev_f_2035-40,
    colored by sustainability flag. Shows the hot/extinct bifurcation
    and the absence of any draw in the data band.
  figures/sustainer_trajectories.png — prev_f time series for sustainers
    overlaid with the 2016 data target.
"""
import json, pickle
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
OUT = HERE / 'outputs'
FIG = HERE / 'figures'
FIG.mkdir(exist_ok=True)

OBS = {
    'syph_detectable_15_64_f_2016': (0.010, 0.004, 0.016),
    'syph_detectable_15_64_m_2016': (0.006, 0.0024, 0.0096),
    'syph_seroprev_15_64_f_2016':   (0.030, 0.012, 0.048),
    'syph_anc_2000_2015':           (0.020, 0.008, 0.032),
}

df = pd.DataFrame([json.loads(l) for l in (OUT / 'results.jsonl').open()])
df = df[df['status'] == 'ok'].reset_index(drop=True)
sus = df[df['sustains']]
dec = df[~df['sustains']]

print(f'ok: {len(df)} | sustain: {len(sus)} | decay: {len(dec)}')

# Coverage vs targets panel
fig, axes = plt.subplots(2, 2, figsize=(10, 7))
for ax, (col, (target, lo, hi)) in zip(axes.flat, OBS.items()):
    bins = np.linspace(0, max(df[col].max() * 1.05, hi * 1.5), 40)
    ax.hist(dec[col], bins=bins, alpha=0.4, color='gray', label=f'decay (n={len(dec)})')
    ax.hist(sus[col], bins=bins, alpha=0.7, color='C3', label=f'sustain (n={len(sus)})')
    ax.axvspan(lo, hi, color='C2', alpha=0.25, label='ZIMPHIA band (±60%)')
    ax.axvline(target, color='C2', linestyle='--', label=f'data = {target:.3f}')
    ax.set_title(col.replace('syph_', '').replace('_15_64', ''))
    ax.set_xlabel('prevalence')
    ax.legend(fontsize=7)
fig.suptitle(f'Exp 22 v3 (low-ANC proof-of-concept) — 44/150 sustain, 0 inside data band',
             fontsize=11)
fig.tight_layout()
fig.savefig(FIG / 'coverage_vs_targets.png', dpi=130)
print(f'wrote {FIG / "coverage_vs_targets.png"}')

# Bifurcation scatter: detect_f at 2016 vs prev_f in 2035-40
fig2, ax = plt.subplots(figsize=(7, 5))
ax.scatter(dec['syph_detectable_15_64_f_2016'], dec['prev_f_2035_2040_mean'],
           c='gray', alpha=0.5, s=22, label=f'decay (n={len(dec)})')
ax.scatter(sus['syph_detectable_15_64_f_2016'], sus['prev_f_2035_2040_mean'],
           c='C3', s=30, label=f'sustain (n={len(sus)})')
target, lo, hi = OBS['syph_detectable_15_64_f_2016']
ax.axvspan(lo, hi, color='C2', alpha=0.2)
ax.axvline(target, color='C2', linestyle='--', label=f'detect_f data = {target:.3f}')
ax.set_xlabel('syph detectable_f at 2016')
ax.set_ylabel('mean prev_f 2035-2040')
ax.set_title('Bifurcation: hot endemic (~15%) or extinction — no draws bracket data')
ax.legend()
fig2.tight_layout()
fig2.savefig(FIG / 'bifurcation_scatter.png', dpi=130)
print(f'wrote {FIG / "bifurcation_scatter.png"}')

# Trajectory plot
series = pickle.load((OUT / 'series.pkl').open('rb'))
fig3, ax = plt.subplots(figsize=(8, 5))
plotted_sus = 0
for idx in sus['draw_idx']:
    if idx not in series:
        continue
    yrs, vals = series[idx]['syph_prevalence_f']
    ax.plot(yrs, vals, color='C3', alpha=0.35, lw=0.8)
    plotted_sus += 1
plotted_dec = 0
for idx in dec['draw_idx'].sample(min(30, len(dec)), random_state=0):
    if idx not in series:
        continue
    yrs, vals = series[idx]['syph_prevalence_f']
    ax.plot(yrs, vals, color='gray', alpha=0.25, lw=0.6)
    plotted_dec += 1
ax.axhline(0.030, color='C2', linestyle='--', label='ZIMPHIA seroprev 2016 = 3%')
ax.axhline(0.010, color='C2', linestyle=':', label='ZIMPHIA detectable 2016 = 1%')
ax.set_xlim(1985, 2040)
ax.set_xlabel('year')
ax.set_ylabel('syph prevalence_f')
ax.set_title(f'Syph prev_f trajectories — {plotted_sus} sustainers (red), {plotted_dec} decayers (gray)')
ax.legend()
fig3.tight_layout()
fig3.savefig(FIG / 'sustainer_trajectories.png', dpi=130)
print(f'wrote {FIG / "sustainer_trajectories.png"}')
