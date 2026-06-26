"""Quick figures for exp 03 SUMMARY.md.

Uses only the phase{1,2}_results.jsonl + draws_used.csv that the
LHS pipeline writes — no re-run required. For publication-grade
time-series + age×sex snapshots, run
calibration/artifacts/scripts/extract_summary.py on draws_used.csv.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / 'outputs'
FIG_DIR = HERE / 'figures'
FIG_DIR.mkdir(parents=True, exist_ok=True)


# Target bands (matched to TARGET_BANDS in _pipeline.py)
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


def fig_acceptance_flow(p1, candidates, draws_used, selection):
    """Funnel: 1000 LHS -> sustained -> n_pass>=5 -> robust 3-seed."""
    stages = [
        ('1000 LHS draws',                len(p1)),
        ('sustained (single-seed)',       int((p1['passes'].apply(lambda d: d.get('sustained', False))).sum())),
        ('n_pass >= 5 (candidates)',      len(candidates)),
        ('robust ensemble (3/3 sustained\n+ mean n_pass >= 4)',  len(draws_used)),
    ]
    labels = [s[0] for s in stages]
    counts = [s[1] for s in stages]

    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.barh(range(len(stages)), counts, color=['#bbb', '#88a', '#558', '#225'])
    ax.set_yticks(range(len(stages)))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel('Number of draws')
    ax.set_title('Acceptance funnel — exp 03 calibration on stisim rc1.5.7')
    for i, b in enumerate(bars):
        ax.text(b.get_width() + max(counts) * 0.01, b.get_y() + b.get_height() / 2,
                str(counts[i]), va='center')
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'acceptance_funnel.png', dpi=160)
    plt.close(fig)


def fig_pass_bands(p1, draws_used):
    """Pass-band hit rates: single-seed Phase 1 vs robust ensemble."""
    bands = ['sustained', 'primary_band', 'secondary_band', 'early_lat_band',
             'hiv_trep_ratio_band', 'fsw_band', 'nontrep_band', 'trep_band',
             'hiv_pos_trep_band']
    p1_hits = {b: p1['passes'].apply(lambda d: bool(d.get(b, False))).mean() for b in bands}

    # For the ensemble, the per-draw passes from Phase 2 are stored in ensemble_summary
    summary = pd.read_csv(OUT_DIR / 'ensemble_summary.csv')
    robust_ids = set(draws_used['draw_idx'])
    sub = summary[summary['draw_idx'].isin(robust_ids)]

    # ensemble_summary contains per-band mean across seeds
    ens_hits = {}
    for b in bands:
        col = f'{b}_mean'
        if col in sub.columns:
            ens_hits[b] = float((sub[col] >= 0.5).mean())  # majority across seeds
        else:
            ens_hits[b] = float('nan')

    fig, ax = plt.subplots(figsize=(8, 4.5))
    y = np.arange(len(bands))
    ax.barh(y - 0.2, [p1_hits[b]*100 for b in bands], 0.4,
            label='Phase 1 single-seed (n=1000)', color='#88a')
    ax.barh(y + 0.2, [ens_hits[b]*100 for b in bands], 0.4,
            label='robust ensemble (n=53)', color='#225')
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


def fig_endpoint_distributions(p1, draws_used):
    """Headline endpoint distributions with target bands."""
    summary = pd.read_csv(OUT_DIR / 'ensemble_summary.csv')
    robust_ids = set(draws_used['draw_idx'])
    sub_summary = summary[summary['draw_idx'].isin(robust_ids)]

    cols = list(TARGETS.keys())
    n = len(cols)
    fig, axs = plt.subplots(2, 4, figsize=(15, 7))
    axs = axs.flatten()
    for i, col in enumerate(cols):
        ax = axs[i]
        lo, hi, name = TARGETS[col]
        # Phase 1 distribution (light grey background)
        v_p1 = p1[col].dropna()
        if len(v_p1):
            ax.hist(v_p1, bins=30, color='#ddd', edgecolor='none',
                    label=f'Phase 1 (n={len(v_p1)})')
        # Ensemble distribution (mean over seeds for each draw)
        ens_col = f'{col}_mean' if f'{col}_mean' in sub_summary.columns else col
        v_ens = sub_summary[ens_col].dropna() if ens_col in sub_summary.columns else pd.Series([])
        if len(v_ens):
            ax.hist(v_ens, bins=15, color='#225', alpha=0.85,
                    label=f'ensemble (n={len(v_ens)})')
        # Target band
        ax.axvspan(lo, hi, color='#2c2', alpha=0.18, label='target band')
        ax.set_title(name, fontsize=10)
        ax.set_xlabel(col, fontsize=8)
        if i == 0:
            ax.legend(fontsize=7, loc='upper right')
    # hide unused subplot if any
    for j in range(n, len(axs)):
        axs[j].axis('off')
    fig.suptitle('Headline endpoint distributions — Phase 1 (grey) vs robust ensemble (dark) vs target band (green)')
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'endpoint_distributions.png', dpi=160)
    plt.close(fig)


def fig_n_pass_distribution(p1, draws_used):
    """Per-draw n_pass: Phase 1 single-seed vs ensemble seed-mean."""
    summary = pd.read_csv(OUT_DIR / 'ensemble_summary.csv')
    robust_ids = set(draws_used['draw_idx'])

    fig, ax = plt.subplots(figsize=(7, 4))
    vc = p1['n_pass'].value_counts().sort_index()
    ax.bar(vc.index - 0.2, vc.values, 0.4, color='#bbb',
           label=f'Phase 1 (n={len(p1)})')
    if 'n_pass_mean' in summary.columns:
        ens = summary[summary['draw_idx'].isin(robust_ids)]['n_pass_mean']
        bins = np.arange(0, 10) - 0.5
        h, _ = np.histogram(ens, bins=bins)
        x = np.arange(0, 9)
        ax.bar(x + 0.2, h, 0.4, color='#225', label=f'robust ensemble (n={len(ens)})')
    ax.set_xlabel('n_pass (target bands cleared)')
    ax.set_ylabel('Number of draws')
    ax.set_title('n_pass distribution')
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / 'n_pass_distribution.png', dpi=160)
    plt.close(fig)


def main():
    p1, p2, draws_used, candidates, selection, summary = load()
    print(f'Phase 1 sims: {len(p1)}')
    print(f'Candidates (Phase 2 in): {len(candidates)}')
    print(f'Robust draws (final ensemble): {len(draws_used)}')
    print()
    fig_acceptance_flow(p1, candidates, draws_used, selection)
    fig_pass_bands(p1, draws_used)
    fig_endpoint_distributions(p1, draws_used)
    fig_n_pass_distribution(p1, draws_used)
    figs = sorted(FIG_DIR.glob('*.png'))
    print(f'Wrote {len(figs)} figures:')
    for f in figs:
        print(f'  {f.name}')


if __name__ == '__main__':
    main()
