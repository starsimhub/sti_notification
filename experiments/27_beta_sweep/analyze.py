"""Generate diagnostic figures for exp 27."""
import json, pickle
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
OUT = HERE / 'outputs'
FIG = HERE / 'figures'
FIG.mkdir(exist_ok=True)

df = pd.DataFrame(json.load(open(OUT / 'results.json'))['per_run'])
df = df[df['status'] == 'ok'].copy()
df['sustained'] = df['new_inf_2030_2040_mean'] > 0

# Panel 1: sweep summary — β vs metrics, 4-panel
fig, axes = plt.subplots(2, 2, figsize=(11, 7))
metrics = [
    ('fsw_prev_2019',   'FSW prev 2019',     (0.20, 0.40)),
    ('nontrep_f_2016',  'nontrep_f 2016',    (0.01, 0.03)),
    ('trep_f_2016',     'trep_f 2016',       (0.05, 0.10)),
    ('overall_prev_f_2035_2040_mean', 'overall prev_f 2035-40 (sustainability)', None),
]
for ax, (col, title, band) in zip(axes.flat, metrics):
    grouped = df.groupby('beta_m2f')[col].agg(['mean', 'std', 'min', 'max']).reset_index()
    ax.errorbar(grouped['beta_m2f'], grouped['mean'],
                yerr=[grouped['mean'] - grouped['min'],
                      grouped['max'] - grouped['mean']],
                fmt='o-', capsize=4, color='C0', label='3-seed range')
    if band is not None:
        ax.axhspan(band[0], band[1], color='C2', alpha=0.2, label='loose target')
    ax.set_xlabel('syph.beta_m2f')
    ax.set_ylabel(col)
    ax.set_title(title)
    ax.legend(fontsize=8)
fig.suptitle('Exp 27 — β sweep at exp 24 base (time_to_undetectable=15y)\n'
             'Only β=0.20 sustains; nontrep_f stays at ~13.5%')
fig.tight_layout()
fig.savefig(FIG / 'sweep_summary.png', dpi=130)
print(f'wrote {FIG / "sweep_summary.png"}')

# Panel 2: time series — overall prev_f and FSW prev for each β, faceted
series = pickle.load(open(OUT / 'series.pkl', 'rb'))
betas_sorted = sorted({k[0] for k in series.keys()})
fig2, axes = plt.subplots(len(betas_sorted), 2, figsize=(11, 2.2 * len(betas_sorted)),
                          sharex=True)
for i, beta in enumerate(betas_sorted):
    for ax in axes[i]:
        ax.set_xlim(1985, 2040)
    keys = [k for k in series if k[0] == beta]
    for k in keys:
        s = series[k]
        axes[i, 0].plot(s['years'], s['overall_prev_f'], alpha=0.7, label=f'seed {k[1]}')
        axes[i, 1].plot(s['years'], s['fsw_prev'], alpha=0.7, label=f'seed {k[1]}')
    axes[i, 0].axhline(0.03, color='C2', linestyle='--', label='ZIMPHIA-loose')
    axes[i, 1].axhspan(0.20, 0.40, color='C2', alpha=0.2, label='target')
    axes[i, 0].set_ylabel(f'β={beta}\noverall prev_f')
    axes[i, 1].set_ylabel(f'β={beta}\nFSW prev')
    if i == 0:
        axes[i, 0].set_title('overall prevalence_f')
        axes[i, 1].set_title('FSW prevalence')
    if i == len(betas_sorted) - 1:
        axes[i, 0].set_xlabel('year')
        axes[i, 1].set_xlabel('year')
    axes[i, 0].legend(fontsize=6, loc='upper left')
fig2.suptitle('Exp 27 trajectories — only β=0.20 stays endemic; lower β collapses to extinction',
              fontsize=10)
fig2.tight_layout()
fig2.savefig(FIG / 'trajectories_by_beta.png', dpi=130)
print(f'wrote {FIG / "trajectories_by_beta.png"}')

# Panel 3: nontrep_f vs trep_f scatter, colored by β, with target band
fig3, ax = plt.subplots(figsize=(7, 5))
for beta in betas_sorted:
    sub = df[df['beta_m2f'] == beta]
    ax.scatter(sub['nontrep_f_2016'], sub['trep_f_2016'],
               label=f'β={beta}', s=60)
ax.axvspan(0.01, 0.03, color='C2', alpha=0.1)
ax.axhspan(0.05, 0.10, color='C2', alpha=0.1)
ax.axvline(0.01, color='C2', linestyle='--', alpha=0.5)
ax.axvline(0.03, color='C2', linestyle='--', alpha=0.5)
ax.axhline(0.05, color='C2', linestyle='--', alpha=0.5)
ax.axhline(0.10, color='C2', linestyle='--', alpha=0.5)
ax.set_xlabel('nontrep_f at 2016')
ax.set_ylabel('trep_f at 2016')
ax.set_title('Loose ZIMPHIA target box is in lower-left; no β lands there')
ax.legend()
fig3.tight_layout()
fig3.savefig(FIG / 'nontrep_vs_trep.png', dpi=130)
print(f'wrote {FIG / "nontrep_vs_trep.png"}')
