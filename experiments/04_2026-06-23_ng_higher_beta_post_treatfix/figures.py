"""Figures for exp 04 (NG higher β, post stisim treatment-fix) SUMMARY.md.

Same figure shapes as exp 03, with corrected column references (exp 03's
figures.py used `<col>_mean` suffixes that don't exist in ensemble_summary,
silently dropping the robust-ensemble bars to NaN).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / 'outputs'
FIG_DIR = HERE / 'figures'
FIG_DIR.mkdir(parents=True, exist_ok=True)


TARGETS = {
    'hiv_prev_2010_2020':  (0.115, 0.155, 'HIV whole-pop prev 2010-20'),
    'trep_f_2016':         (0.020, 0.040, 'syph trep F 2016 (ZIMPHIA)'),
    'nontrep_f_2016':      (0.005, 0.015, 'syph nontrep F 2016 (ZIMPHIA)'),
    'hiv_trep_ratio_2016': (3.0,   6.0,   'HIV+/HIV- trep ratio 2016'),
    'fsw_prev_2019':       (0.40,  0.70,  'FSW prev 2019'),
    'primary_share':       (0.45,  0.65,  'primary syph share'),
    'secondary_share':     (0.25,  0.45,  'secondary syph share'),
}


def load():
    p1 = pd.read_json(OUT_DIR / 'phase1_results.jsonl', lines=True)
    p2 = pd.read_json(OUT_DIR / 'phase2_results.jsonl', lines=True)
    draws_used = pd.read_csv(OUT_DIR / 'draws_used.csv')
    candidates = pd.read_csv(OUT_DIR / 'phase2_candidates.csv')
    selection = json.loads((OUT_DIR / 'phase1_selection.json').read_text())
    summary = pd.read_csv(OUT_DIR / 'ensemble_summary.csv')
    return p1, p2, draws_used, candidates, selection, summary


def fig_acceptance_flow(p1, candidates, draws_used):
    sus_p1 = int(p1['passes'].apply(lambda d: bool(d.get('sustained', False))).sum())
    stages = [
        ('500 LHS draws',                                      len(p1)),
        ('all-5-STIs sustained (single-seed)',                  sus_p1),
        ('sustained AND n_pass >= 5 candidates',                len(candidates)),
        ('robust ensemble (3/3 sustained\n+ mean n_pass >= 4)', len(draws_used)),
    ]
    labels = [s[0] for s in stages]
    counts = [s[1] for s in stages]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    bars = ax.barh(range(len(stages)), counts,
                   color=['#bbb', '#88a', '#558', '#225'])
    ax.set_yticks(range(len(stages)))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel('Number of draws')
    ax.set_title('Acceptance funnel — exp 04 (NG higher β, post treatment-fix)')
    for i, b in enumerate(bars):
        ax.text(b.get_width() + max(counts) * 0.01,
                b.get_y() + b.get_height() / 2,
                str(counts[i]), va='center')
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'acceptance_funnel.png', dpi=160)
    plt.close(fig)


def fig_per_disease_sustain(p1, draws_used, summary):
    diseases = ['hiv', 'syph', 'ng', 'ct', 'tv']
    p1_rates = {d: p1[f'sustained_{d}'].mean() for d in diseases}
    robust_ids = set(draws_used['draw_idx'])
    sub = summary[summary['draw_idx'].isin(robust_ids)]
    # `sustained_<d>` is the mean across 3 seeds, so >=0.999 means 3/3 sustained
    ens_rates = {d: (sub[f'sustained_{d}'] >= 0.999).mean() for d in diseases}

    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(diseases))
    w = 0.4
    ax.bar(x - w/2, [p1_rates[d]*100 for d in diseases], w,
           label=f'Phase 1 single-seed (n={len(p1)})', color='#88a')
    ax.bar(x + w/2, [ens_rates[d]*100 for d in diseases], w,
           label=f'robust ensemble (n={len(sub)})', color='#225')
    ax.set_xticks(x)
    ax.set_xticklabels([d.upper() for d in diseases])
    ax.set_ylabel('% of draws sustaining late projection window')
    ax.set_ylim(0, 105)
    ax.set_title('Per-disease sustainability — exp 04 (NG β higher)')
    ax.legend(loc='lower left')
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'per_disease_sustainability.png', dpi=160)
    plt.close(fig)


def fig_rejection_reasons(p1):
    diseases = ['hiv', 'syph', 'ng', 'ct', 'tv']
    rejected = p1[~p1['passes'].apply(lambda d: bool(d.get('sustained', False)))]
    fig, ax = plt.subplots(figsize=(7, 4))
    counts = {d: int((~rejected[f'sustained_{d}']).sum()) for d in diseases}
    bars = ax.barh(range(len(diseases)),
                   [counts[d] for d in diseases],
                   color=['#5c5', '#9c5', '#c63', '#5cc', '#c5c'])
    ax.set_yticks(range(len(diseases)))
    ax.set_yticklabels([d.upper() for d in diseases])
    ax.invert_yaxis()
    ax.set_xlabel(f'Number of rejected Phase 1 draws extinguishing this STI (out of {len(rejected)})')
    ax.set_title('Rejection reasons — which STI(s) extinguished?\n(draws can fail >=1 disease and appear in multiple bars)')
    for i, d in enumerate(diseases):
        pct = counts[d] / len(rejected) * 100 if len(rejected) else 0
        ax.text(counts[d] + len(rejected) * 0.01,
                i, f'{counts[d]} ({pct:.0f}%)', va='center')
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'rejection_reasons.png', dpi=160)
    plt.close(fig)


def fig_pass_bands(p1, draws_used, summary):
    bands = ['sustained', 'primary_band', 'secondary_band', 'early_lat_band',
             'hiv_trep_ratio_band', 'fsw_band', 'nontrep_band', 'trep_band',
             'hiv_pos_trep_band']
    p1_hits = {b: p1['passes'].apply(lambda d: bool(d.get(b, False))).mean() for b in bands}
    robust_ids = set(draws_used['draw_idx'])
    sub = summary[summary['draw_idx'].isin(robust_ids)]
    # `pass_<band>` is the mean across 3 seeds; >=0.5 means majority of seeds passed
    ens_hits = {b: (sub[f'pass_{b}'] >= 0.5).mean() for b in bands}

    fig, ax = plt.subplots(figsize=(8, 4.5))
    y = np.arange(len(bands))
    ax.barh(y - 0.2, [p1_hits[b]*100 for b in bands], 0.4,
            label=f'Phase 1 single-seed (n={len(p1)})', color='#88a')
    ax.barh(y + 0.2, [ens_hits[b]*100 for b in bands], 0.4,
            label=f'robust ensemble (n={len(draws_used)})', color='#225')
    ax.set_yticks(y)
    ax.set_yticklabels(bands)
    ax.invert_yaxis()
    ax.set_xlabel('% of draws passing band')
    ax.set_title('Target-band hit rates — Phase 1 vs robust ensemble')
    ax.legend(loc='lower right')
    ax.set_xlim(0, 100)
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'pass_band_hit_rates.png', dpi=160)
    plt.close(fig)


def fig_endpoint_distributions(p1, draws_used, summary):
    robust_ids = set(draws_used['draw_idx'])
    sub_summary = summary[summary['draw_idx'].isin(robust_ids)]
    cols = list(TARGETS.keys())
    n = len(cols)
    fig, axs = plt.subplots(2, 4, figsize=(15, 7))
    axs = axs.flatten()
    for i, col in enumerate(cols):
        ax = axs[i]
        lo, hi, name = TARGETS[col]
        v_p1 = p1[col].dropna()
        if len(v_p1):
            ax.hist(v_p1, bins=30, color='#ddd', edgecolor='none',
                    label=f'Phase 1 (n={len(v_p1)})')
        v_ens = sub_summary[col].dropna() if col in sub_summary.columns else pd.Series([])
        if len(v_ens):
            ax.hist(v_ens, bins=15, color='#225', alpha=0.85,
                    label=f'ensemble (n={len(v_ens)})')
        ax.axvspan(lo, hi, color='#2c2', alpha=0.18, label='target band')
        ax.set_title(name, fontsize=10)
        ax.set_xlabel(col, fontsize=8)
        if i == 0:
            ax.legend(fontsize=7, loc='upper right')
    for j in range(n, len(axs)):
        axs[j].axis('off')
    fig.suptitle('Headline endpoints — Phase 1 (grey) vs robust ensemble (dark) vs target band (green)')
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'endpoint_distributions.png', dpi=160)
    plt.close(fig)


def fig_ng_beta_comparison(draws_used):
    """exp 04 vs exp 03 NG β posterior, as the headline change."""
    exp03 = pd.read_csv(
        HERE.parent / '03_2026-06-22_calibration_bv_in_vds' / 'outputs' / 'draws_used.csv'
    )
    col = 'log_ng.beta_m2f'
    fig, ax = plt.subplots(figsize=(7.5, 4))
    bins = np.linspace(-4, 0, 25)
    ax.hist(np.exp(exp03[col]), bins=np.exp(bins), alpha=0.55, color='#88a',
            label=f'exp 03 ensemble (n={len(exp03)})', edgecolor='#446')
    ax.hist(np.exp(draws_used[col]), bins=np.exp(bins), alpha=0.85, color='#225',
            label=f'exp 04 ensemble (n={len(draws_used)})', edgecolor='black')
    ax.axvline(0.020, color='#888', linestyle=':', alpha=0.7,
               label='exp 03 prior floor (0.020)')
    ax.axvline(0.10, color='#225', linestyle=':',
               label='exp 04 prior floor (0.10)')
    ax.set_xscale('log')
    ax.set_xlabel(r'NG $\beta_{m2f}$ (log scale)')
    ax.set_ylabel('Draws')
    ax.set_title('NG β posterior shifts up after stisim treatment-fix')
    ax.legend(loc='upper left', fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'ng_beta_posterior_shift.png', dpi=160)
    plt.close(fig)


def main():
    p1, p2, draws_used, candidates, selection, summary = load()
    print(f'Phase 1 sims: {len(p1)}')
    print(f'Candidates: {len(candidates)}')
    print(f'Robust ensemble: {len(draws_used)}')
    fig_acceptance_flow(p1, candidates, draws_used)
    fig_per_disease_sustain(p1, draws_used, summary)
    fig_rejection_reasons(p1)
    fig_pass_bands(p1, draws_used, summary)
    fig_endpoint_distributions(p1, draws_used, summary)
    fig_ng_beta_comparison(draws_used)
    figs = sorted(FIG_DIR.glob('*.png'))
    print(f'\nWrote {len(figs)} figures:')
    for f in figs:
        print(f'  {f.name}')


if __name__ == '__main__':
    main()
