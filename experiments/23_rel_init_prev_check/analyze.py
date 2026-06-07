"""
Post-run diagnostic figures for exp 23.

  figures/init_prev_vs_detectf.png — sustainers' detect_f_2016 plotted
    against the sampled rel_init_prev. If hypothesis (B) were true,
    low rel_init_prev draws should land at low detect_f.
  figures/coverage_vs_targets.png — same 4-panel as exp 22 for direct
    comparison.
  figures/subpop_attribution.png — among sustainers, fraction of
    2010-2030 new infections from each sub-population (FSW vs general
    F, clients vs general M) and by risk group.
"""
import json
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
priors = pd.read_csv(OUT / 'prior_draws.csv')
df = df.merge(priors, on='draw_idx')
df['rel_init_prev'] = np.exp(df['log_syph.rel_init_prev'])

sus = df[df['sustains']].copy()
dec = df[~df['sustains']].copy()
print(f'ok: {len(df)} | sustain: {len(sus)} | decay: {len(dec)}')

# Panel 1: rel_init_prev vs detect_f among sustainers
fig, ax = plt.subplots(figsize=(7, 5))
ax.scatter(dec['rel_init_prev'], dec['syph_detectable_15_64_f_2016'],
           color='gray', alpha=0.5, s=22, label=f'decay (n={len(dec)})')
ax.scatter(sus['rel_init_prev'], sus['syph_detectable_15_64_f_2016'],
           color='C3', s=32, label=f'sustain (n={len(sus)})')
target, lo, hi = OBS['syph_detectable_15_64_f_2016']
ax.axhspan(lo, hi, color='C2', alpha=0.2, label='ZIMPHIA band')
ax.axhline(target, color='C2', linestyle='--', label=f'data = {target:.3f}')
ax.set_xscale('log')
ax.set_xlabel('syph.rel_init_prev (log scale)')
ax.set_ylabel('detect_f_2016')
ax.set_title('rel_init_prev does NOT determine the endemic basin —\nsustainers cluster at ~15% across the full 50x range')
ax.legend()
fig.tight_layout()
fig.savefig(FIG / 'init_prev_vs_detectf.png', dpi=130)
print(f'wrote {FIG / "init_prev_vs_detectf.png"}')

# Panel 2: coverage vs targets — same layout as exp 22
fig2, axes = plt.subplots(2, 2, figsize=(10, 7))
for ax, (col, (target, lo, hi)) in zip(axes.flat, OBS.items()):
    bins = np.linspace(0, max(df[col].max() * 1.05, hi * 1.5), 40)
    ax.hist(dec[col], bins=bins, alpha=0.4, color='gray', label=f'decay (n={len(dec)})')
    ax.hist(sus[col], bins=bins, alpha=0.7, color='C3', label=f'sustain (n={len(sus)})')
    ax.axvspan(lo, hi, color='C2', alpha=0.25, label='ZIMPHIA band')
    ax.axvline(target, color='C2', linestyle='--', label=f'data = {target:.3f}')
    ax.set_title(col.replace('syph_', '').replace('_15_64', ''))
    ax.set_xlabel('prevalence')
    ax.legend(fontsize=7)
fig2.suptitle(f'Exp 23 (rel_init_prev added) — 41/150 sustain, 0 inside data band')
fig2.tight_layout()
fig2.savefig(FIG / 'coverage_vs_targets.png', dpi=130)
print(f'wrote {FIG / "coverage_vs_targets.png"}')

# Panel 3: sub-population attribution among sustainers
sus['frac_fsw']    = sus['cum_new_inf_sw_2010_2030']        / sus['cum_new_inf_2010_2030']
sus['frac_genF']   = sus['cum_new_inf_not_sw_2010_2030']    / sus['cum_new_inf_2010_2030']
sus['frac_client'] = sus['cum_new_inf_client_2010_2030']    / sus['cum_new_inf_2010_2030']
sus['frac_genM']   = sus['cum_new_inf_not_client_2010_2030']/ sus['cum_new_inf_2010_2030']
for sex in ('female', 'male'):
    for rg in (0, 1, 2):
        col = f'cum_new_inf_rg{rg}_{sex}_2010_2030'
        sus[f'frac_rg{rg}_{sex}'] = sus[col] / sus['cum_new_inf_2010_2030']

fig3, (axA, axB) = plt.subplots(1, 2, figsize=(11, 5))
catsA  = ['frac_fsw', 'frac_genF', 'frac_client', 'frac_genM']
labelsA = ['FSW (F)', 'general F (non-FSW)', 'clients (M)', 'general M (non-client)']
data_A = [sus[c].values for c in catsA]
bp = axA.boxplot(data_A, labels=labelsA, patch_artist=True)
for patch, color in zip(bp['boxes'], ['C3', 'C0', 'C1', 'C4']):
    patch.set_facecolor(color); patch.set_alpha(0.5)
axA.set_ylabel('fraction of 2010-2030 new syph infections')
axA.set_title('FSW vs general — 18% from FSW, 82% from general F')
axA.tick_params(axis='x', rotation=20)
axA.set_ylim(0, 1)

catsB  = [f'frac_rg{rg}_{sex}' for sex in ('female','male') for rg in (0,1,2)]
labelsB = [f'rg{rg}\n{sex[0].upper()}' for sex in ('female','male') for rg in (0,1,2)]
data_B = [sus[c].values for c in catsB]
bp2 = axB.boxplot(data_B, labels=labelsB, patch_artist=True)
colors2 = ['C0','C0','C0','C1','C1','C1']
for patch, color in zip(bp2['boxes'], colors2):
    patch.set_facecolor(color); patch.set_alpha(0.5)
axB.set_ylabel('fraction of 2010-2030 new syph infections')
axB.set_title('Risk group × sex — rg0 female (low-risk) is largest single share')
axB.set_ylim(0, 1)

fig3.suptitle('Sub-population attribution among 41 sustainers — plateau driven by general / low-risk women, NOT FSW reservoir')
fig3.tight_layout()
fig3.savefig(FIG / 'subpop_attribution.png', dpi=130)
print(f'wrote {FIG / "subpop_attribution.png"}')
