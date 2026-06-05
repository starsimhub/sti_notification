"""Figures for exp 14: ESS comparison + weight allocation across the bifurcation."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sciris as sc

HERE = Path(__file__).parent
OUTPUTS = HERE / 'outputs'
FIGURES = HERE / 'figures'
FIGURES.mkdir(parents=True, exist_ok=True)

VARIANTS = ['A_gaussian_alive_only', 'B_gaussian_nan', 'C_studentt_nan']
LABELS = {
    'A_gaussian_alive_only': 'A: Gaussian,\nalive-only',
    'B_gaussian_nan': 'B: Gaussian,\nNaN-for-extinct',
    'C_studentt_nan': 'C: Student-t df=3,\nNaN-for-extinct',
}


def plot_ess_comparison():
    with (OUTPUTS / 'summary.json').open() as f:
        summary = json.load(f)
    variants = summary['variants']

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    labels = [LABELS[v['variant']] for v in variants]
    ess = [v['ess'] for v in variants]
    ess_ratio = [v['ess_ratio'] * 100 for v in variants]
    gap = [v['gap_ratio'] for v in variants]

    ax = axes[0]
    colors = ['#cccccc', '#cc6666', '#5588cc']
    bars = ax.bar(labels, ess_ratio, color=colors, alpha=0.85)
    for b, e, n in zip(bars, ess, [v['n_in_weighting'] for v in variants]):
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.1,
                f'ESS={e:.1f}\n/ {n}', ha='center', fontsize=9)
    ax.axhline(5.0, color='C3', linestyle='--', linewidth=1, label='5% usability bar')
    ax.set_ylabel('ESS / N (%)')
    ax.set_title('Effective sample size by reweighting scheme')
    ax.legend(fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)

    ax = axes[1]
    bars = ax.bar(labels, gap, color=colors, alpha=0.85)
    for b, g in zip(bars, gap):
        ax.text(b.get_x() + b.get_width()/2, b.get_height() * 1.05,
                f'{g:.0f}x', ha='center', fontsize=9)
    ax.axhline(1.0, color='C2', linestyle='--', linewidth=1, label='gap = 1x (no collapse)')
    ax.set_yscale('log')
    ax.set_ylabel('Alive-pool / posterior predictive (log scale)')
    ax.set_title('Weight-collapse diagnostic: late-window syph')
    ax.legend(fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'ess_comparison.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "ess_comparison.png"}')


def plot_weight_allocation():
    """For each variant, show how weight is distributed across the
    bimodal histogram of syph_prev_f_2020_2025."""
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    bins = np.linspace(0, 0.27, 60)

    for ax, variant in zip(axes, VARIANTS):
        df = pd.read_csv(OUTPUTS / f'weighted_{variant}.csv')
        vals = df['syph_prev_f_2020_2025'].values
        w = df['weight'].values

        unweighted_counts, _ = np.histogram(vals, bins=bins)
        weighted_counts, _ = np.histogram(vals, bins=bins, weights=w)

        unweighted_norm = unweighted_counts / max(1, unweighted_counts.sum())
        weighted_norm = weighted_counts / max(1e-12, weighted_counts.sum())

        ax.bar(bins[:-1], unweighted_norm, width=np.diff(bins), color='grey',
               alpha=0.4, align='edge', label=f'unweighted ({len(df)} draws)')
        ax.bar(bins[:-1], weighted_norm, width=np.diff(bins), color='steelblue',
               alpha=0.7, align='edge', label='posterior weight')

        ax.axvline(0.010, color='C3', linestyle='--', linewidth=1.5, label='Data 1.0%')
        ax.set_ylabel('Density')
        ax.set_title(LABELS[variant].replace('\n', ' '))
        ax.legend(fontsize=9, loc='upper right')
        ax.spines[['top', 'right']].set_visible(False)

    axes[-1].set_xlabel('Female syphilis prevalence, mean 2020–2025')
    fig.suptitle('Where each likelihood places its posterior weight',
                 fontsize=13)
    sc.figlayout()
    fig.savefig(FIGURES / 'weight_allocation.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "weight_allocation.png"}')


if __name__ == '__main__':
    plot_ess_comparison()
    plot_weight_allocation()
