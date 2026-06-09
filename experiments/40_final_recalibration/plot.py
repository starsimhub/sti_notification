"""
Plots for exp 40 SUMMARY:
1. n_pass dist (Phase 1 single seed + Phase 2 three-seed mean)
2. Per-target pass rate (exp 36 vs exp 38 vs exp 40) — shows where exp 40
   moved the needle
3. Robust ensemble distributions vs target bands
4. Identifiability of the 3 new priors (HIV init + marital decay knobs)
5. HIV calibration: ensemble vs UNAIDS over time — the headline win
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent
EXP36 = ROOT.parent / '36_ensemble_robust_extend'
EXP38 = ROOT.parent / '38_recalibration_baseline_pn'

ph1 = pd.read_json(ROOT / 'outputs/phase1_results.jsonl', lines=True)
ph1['sustained_int'] = ph1['passes'].apply(lambda d: int(d.get('sustained', False)))
es = pd.read_csv(ROOT / 'outputs/ensemble_summary.csv')
priors = pd.read_csv(ROOT / 'outputs/phase1_priors.csv')
robust = es[(es['pass_sustained'] == 1.0) & (es['n_pass_mean'] >= 4)]

old36 = pd.read_csv(EXP36 / 'outputs/full_summary.csv')
r36 = old36[(old36['pass_sustained'] == 1.0) & (old36['n_pass_mean'] >= 4)]
old38 = pd.read_csv(EXP38 / 'outputs/ensemble_summary.csv')
r38 = old38[(old38['pass_sustained'] == 1.0) & (old38['n_pass_mean'] >= 4)]

FIG = ROOT / 'figures'
FIG.mkdir(exist_ok=True)


def fig_n_pass():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    ax.hist(ph1['n_pass'], bins=np.arange(0, 11) - 0.5, color='steelblue',
            edgecolor='white')
    ax.set(xlabel='n_pass (single seed)', ylabel='draws',
           title=f'Phase 1: 5000 LHS draws\n'
                 f'sustained: {ph1.sustained_int.sum()}/{len(ph1)} '
                 f'({ph1.sustained_int.mean() * 100:.0f}%)')
    ax.axvline(5, color='crimson', ls='--', alpha=0.7,
               label='primary filter (n_pass≥5)')
    ax.legend()

    ax = axes[1]
    ax.hist(es['n_pass_mean'], bins=np.arange(0, 7, 0.33), color='seagreen',
            edgecolor='white')
    ax.set(xlabel='n_pass_mean (3 seeds)', ylabel='candidates',
           title=f'Phase 2: 767 candidates × 3 seeds\n'
                 f'robust: {len(robust)}/{len(es)} '
                 f'(sustained 3/3 AND mean n_pass≥4)')
    ax.axvline(4, color='crimson', ls='--', alpha=0.7,
               label='robust gate (mean≥4)')
    ax.legend()

    fig.tight_layout()
    fig.savefig(FIG / 'n_pass_distribution.png', dpi=140)
    plt.close(fig)


def fig_pass_rates():
    labels = ['fsw_band', 'nontrep_band', 'trep_band', 'hiv_pos_trep_band',
              'primary_band', 'secondary_band', 'early_lat_band',
              'hiv_trep_ratio_band']
    nice = ['FSW prev\n2019', 'Nontrep F\n2016', 'Trep F\n2016',
            'HIV+ trep\n2016', 'Primary\nshare', 'Secondary\nshare',
            'Early-latent\nshare', 'HIV+/-\ntrep ratio']
    rates_36 = [r36[f'pass_{c}'].mean() * 100 for c in labels]
    rates_38 = [r38[f'pass_{c}'].mean() * 100 for c in labels]
    rates_40 = [robust[f'pass_{c}'].mean() * 100 for c in labels]

    fig, ax = plt.subplots(figsize=(12, 4.5))
    x = np.arange(len(labels))
    w = 0.27
    ax.bar(x - w, rates_36, width=w, color='lightsteelblue',
           label=f'exp 36 baseline (n={len(r36)})')
    ax.bar(x, rates_38, width=w, color='steelblue',
           label=f'exp 38 +baseline PN +scaling (n={len(r38)})')
    ax.bar(x + w, rates_40, width=w, color='seagreen',
           label=f'exp 40 +marital decay +HIV +CT (n={len(robust)})')
    ax.set(xticks=x, ylabel='% of robust ensemble in band', ylim=(0, 105),
           title='Per-target band-pass rate across recalibration attempts')
    ax.set_xticklabels(nice, fontsize=9)
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG / 'pass_rates_across_attempts.png', dpi=140)
    plt.close(fig)


def fig_ensemble_vs_bands():
    metrics = [
        ('fsw_prev_2019',        (0.20, 0.40),  'FSW prev 2019'),
        ('nontrep_f_2016',       (0.01, 0.05),  'Nontrep F 2016'),
        ('trep_f_2016',          (0.05, 0.10),  'Trep F 2016'),
        ('hiv_pos_trep_2016',    (0.05, 0.09),  'HIV+ trep 2016'),
        ('hiv_trep_ratio_2016',  (3.0, 6.0),    'HIV+/HIV- trep ratio'),
        ('hiv_prev_2010_2020',   (0.09, 0.13),  'HIV whole-pop 2010-20'),
        ('primary_share',        (0.45, 0.65),  'Primary share'),
        ('secondary_share',      (0.25, 0.45),  'Secondary share'),
    ]
    fig, axes = plt.subplots(2, 4, figsize=(13, 6))
    axes = axes.flatten()
    for ax, (col, band, label) in zip(axes, metrics):
        vals = robust[col].dropna()
        ax.boxplot(vals, vert=True, widths=0.5, patch_artist=True,
                   boxprops=dict(facecolor='seagreen', alpha=0.5))
        ax.axhspan(band[0], band[1], color='crimson', alpha=0.18,
                   label='target band')
        ax.set(title=label, ylabel='', xticks=[])
        med = vals.median()
        ax.scatter([1], [med], color='black', zorder=5, s=20)
        ax.text(1.4, med, f'med={med:.3f}', va='center', fontsize=8)
        ax.legend(fontsize=7, loc='best')
    fig.suptitle(f'Exp 40 robust ensemble (n={len(robust)}) vs target bands\n'
                 f'(HIV whole-pop now in band; syph absolute prevs unchanged from exp 38)',
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / 'ensemble_vs_bands.png', dpi=140)
    plt.close(fig)


def fig_new_priors_identifiable():
    rb = priors.merge(robust[['draw_idx']], on='draw_idx')
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.5))
    for ax, col, lo, hi in [
        (axes[0], 'hiv.rel_init_prev',                       0.3, 1.5),
        (axes[1], 'structuredsexual.stable_act_decay',       0.02, 0.20),
        (axes[2], 'structuredsexual.client_marital_act_mult', 0.3, 1.0),
    ]:
        ax.hist(priors[col], bins=15, color='lightgray', edgecolor='white',
                label='LHS prior (n=5000)', density=True)
        ax.hist(rb[col], bins=15, color='seagreen', alpha=0.7,
                edgecolor='white',
                label=f'robust subset (n={len(rb)})', density=True)
        ax.set(xlabel=col.split('.')[-1], ylabel='density', xlim=(lo, hi))
        ax.legend(fontsize=8)
    fig.suptitle('New priors: robust subset distribution vs LHS prior\n'
                 'All three deviate from uniform → identifiable; calibrator uses them',
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(FIG / 'new_prior_identifiability.png', dpi=140)
    plt.close(fig)


def fig_hiv_calibration_win():
    """Headline: HIV prev medians vs UNAIDS. Bar comparison across attempts."""
    fig, ax = plt.subplots(figsize=(7.5, 4))
    bars = {
        'exp 36\n(no PN, no scaling)': r36['hiv_prev_2010_2020'].median(),
        'exp 38\n(+baseline PN +scaling)': r38['hiv_prev_2010_2020'].median(),
        'exp 40\n(+marital decay\n+HIV recalib)': robust['hiv_prev_2010_2020'].median(),
    }
    err = {
        'exp 36\n(no PN, no scaling)': r36['hiv_prev_2010_2020'].quantile([0.1, 0.9]).values,
        'exp 38\n(+baseline PN +scaling)': r38['hiv_prev_2010_2020'].quantile([0.1, 0.9]).values,
        'exp 40\n(+marital decay\n+HIV recalib)': robust['hiv_prev_2010_2020'].quantile([0.1, 0.9]).values,
    }
    x = np.arange(len(bars))
    meds = [bars[k] * 100 for k in bars]
    errs_lo = [(bars[k] - err[k][0]) * 100 for k in bars]
    errs_hi = [(err[k][1] - bars[k]) * 100 for k in bars]
    ax.bar(x, meds, color=['lightsteelblue', 'steelblue', 'seagreen'],
           yerr=[errs_lo, errs_hi], capsize=5, edgecolor='black', linewidth=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(list(bars.keys()), fontsize=9)
    ax.axhspan(9, 13, color='crimson', alpha=0.18,
               label='UNAIDS 2010-2020 (~9-13%)')
    ax.set_ylabel('HIV whole-pop prevalence 2010-2020 mean (%)')
    ax.set_title('HIV calibration progress: exp 40 moves into UNAIDS band')
    ax.legend(loc='upper right', fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / 'hiv_calibration_progress.png', dpi=140)
    plt.close(fig)


if __name__ == '__main__':
    fig_n_pass()
    fig_pass_rates()
    fig_ensemble_vs_bands()
    fig_new_priors_identifiable()
    fig_hiv_calibration_win()
    print('Figures saved to', FIG)
