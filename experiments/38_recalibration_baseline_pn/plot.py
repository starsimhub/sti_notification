"""
Plots for exp 38 SUMMARY:
1. n_pass distribution (single-seed phase 1 + mean across 3 seeds phase 2)
2. Per-target pass rate (exp 36 vs exp 38)
3. Ensemble distributions vs target bands (whisker plot per metric)
4. PN priors: distribution among robust draws vs uniform prior
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent
EXP36 = ROOT.parent / '36_ensemble_robust_extend'

ph1 = pd.read_json(ROOT / 'outputs/phase1_results.jsonl', lines=True)
ph1['sustained_int'] = ph1['passes'].apply(lambda d: int(d.get('sustained', False)))
es = pd.read_csv(ROOT / 'outputs/ensemble_summary.csv')
priors = pd.read_csv(ROOT / 'outputs/phase1_priors.csv')
robust = es[(es['pass_sustained'] == 1.0) & (es['n_pass_mean'] >= 4)]
old = pd.read_csv(EXP36 / 'outputs/full_summary.csv')
old_robust = old[(old['pass_sustained'] == 1.0) & (old['n_pass_mean'] >= 4)]

FIG = ROOT / 'figures'
FIG.mkdir(exist_ok=True)


def fig_n_pass():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    ax.hist(ph1['n_pass'], bins=np.arange(0, 11) - 0.5, color='steelblue',
            edgecolor='white')
    ax.set(xlabel='n_pass (single seed)',
           ylabel='draws',
           title=f'Phase 1: 1500 LHS draws\n'
                 f'sustained: {ph1.sustained_int.sum()}/{len(ph1)} '
                 f'({ph1.sustained_int.mean() * 100:.0f}%)')
    ax.axvline(5, color='crimson', ls='--', alpha=0.7, label='primary filter (n_pass≥5)')
    ax.legend()

    ax = axes[1]
    ax.hist(es['n_pass_mean'], bins=np.arange(0, 7, 0.33), color='seagreen',
            edgecolor='white')
    ax.set(xlabel='n_pass_mean (3 seeds)',
           ylabel='candidates',
           title=f'Phase 2: 272 candidates × 3 seeds\n'
                 f'robust: {len(robust)}/{len(es)} '
                 f'(sustained 3/3 AND mean n_pass≥4)')
    ax.axvline(4, color='crimson', ls='--', alpha=0.7, label='robust gate (mean≥4)')
    ax.legend()

    fig.tight_layout()
    fig.savefig(FIG / 'n_pass_distribution.png', dpi=140)
    plt.close(fig)


def fig_pass_rates():
    labels = ['fsw_band', 'nontrep_band', 'trep_band', 'hiv_pos_trep_band',
              'primary_band', 'secondary_band', 'early_lat_band',
              'hiv_trep_ratio_band']
    nice_labels = ['FSW prev\n2019', 'Nontrep F\n2016', 'Trep F\n2016',
                   'HIV+ trep\n2016', 'Primary\nshare', 'Secondary\nshare',
                   'Early-latent\nshare', 'HIV+/-\ntrep ratio']
    old_rates = [old_robust[f'pass_{c}'].mean() * 100 for c in labels]
    new_rates = [robust[f'pass_{c}'].mean() * 100 for c in labels]

    fig, ax = plt.subplots(figsize=(11, 4.5))
    x = np.arange(len(labels))
    w = 0.4
    ax.bar(x - w / 2, old_rates, width=w, color='steelblue', label='exp 36 (no PN, no scaling)')
    ax.bar(x + w / 2, new_rates, width=w, color='seagreen', label='exp 38 (baseline PN + scaling)')
    ax.set(xticks=x, ylabel='% of robust ensemble in band', ylim=(0, 105),
           title='Per-target band-pass rate: exp 36 (n=125) vs exp 38 (n=93)')
    ax.set_xticklabels(nice_labels, fontsize=9)
    ax.legend(loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / 'pass_rates_vs_exp36.png', dpi=140)
    plt.close(fig)


def fig_ensemble_vs_bands():
    metrics = [
        ('fsw_prev_2019',        (0.20, 0.40),  'FSW prev 2019'),
        ('nontrep_f_2016',       (0.01, 0.05),  'Nontrep F 2016'),
        ('trep_f_2016',          (0.05, 0.10),  'Trep F 2016'),
        ('hiv_pos_trep_2016',    (0.05, 0.09),  'HIV+ trep 2016'),
        ('hiv_trep_ratio_2016',  (3.0, 6.0),    'HIV+/HIV- trep ratio'),
        ('primary_share',        (0.45, 0.65),  'Primary share'),
        ('secondary_share',      (0.25, 0.45),  'Secondary share'),
    ]
    fig, axes = plt.subplots(2, 4, figsize=(13, 6))
    axes = axes.flatten()
    for ax, (col, band, label) in zip(axes, metrics):
        vals = robust[col].dropna()
        ax.boxplot(vals, vert=True, widths=0.5, patch_artist=True,
                   boxprops=dict(facecolor='seagreen', alpha=0.5))
        ax.axhspan(band[0], band[1], color='crimson', alpha=0.18, label='target band')
        ax.set(title=label, ylabel='', xticks=[])
        med = vals.median()
        ax.scatter([1], [med], color='black', zorder=5, s=20)
        ax.text(1.4, med, f'med={med:.3f}', va='center', fontsize=8)
        ax.legend(fontsize=7, loc='best')
    axes[-1].axis('off')
    fig.suptitle(f'Exp 38 robust ensemble (n={len(robust)}) vs target bands',
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(FIG / 'ensemble_vs_bands.png', dpi=140)
    plt.close(fig)


def fig_pn_priors():
    rb = priors.merge(robust[['draw_idx']], on='draw_idx')
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
    for ax, col, lo, hi in [
        (axes[0], 'pn.p_notify_stable', 0.05, 0.50),
        (axes[1], 'pn.p_notify_casual', 0.02, 0.20),
    ]:
        ax.hist(priors[col], bins=15, color='lightgray', edgecolor='white',
                label='LHS prior (n=1500)', density=True)
        ax.hist(rb[col], bins=15, color='seagreen', alpha=0.7, edgecolor='white',
                label=f'robust subset (n={len(rb)})', density=True)
        ax.set(xlabel=col, ylabel='density', xlim=(lo, hi))
        ax.legend(fontsize=8)
    fig.suptitle('PN priors: robust subset is indistinguishable from uniform prior\n'
                 '(max |r| ~0.06 across all outcomes — weakly identifiable)',
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / 'pn_prior_identifiability.png', dpi=140)
    plt.close(fig)


if __name__ == '__main__':
    fig_n_pass()
    fig_pass_rates()
    fig_ensemble_vs_bands()
    fig_pn_priors()
    print('Figures saved to', FIG)
