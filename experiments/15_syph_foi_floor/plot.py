"""Figures for exp 15: per-rate bifurcation histograms + policy summary."""

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

DATA = 0.010   # syph_prev_f target


def load():
    rows = []
    with (OUTPUTS / 'results.jsonl').open() as f:
        for line in f:
            rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    return df[df['status'] == 'ok'].copy()


def plot_bifurcation_grid():
    df = load()
    rates = sorted(df['import_rate'].unique())
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharex=True, sharey=True)
    axes = axes.ravel()
    bins = np.linspace(0, 0.35, 50)

    for ax, rate in zip(axes, rates):
        sub = df[df['import_rate'] == rate]
        vals = sub['syph_prev_f_2020_2025'].values
        median_imp_frac = sub['import_fraction'].median()
        ax.hist(vals, bins=bins, color='steelblue', alpha=0.75)
        ax.axvline(DATA, color='C3', linestyle='--', linewidth=1.5,
                   label=f'Data ({DATA*100:.1f}%)')
        ax.set_title(
            f'Imports = {rate}/month  '
            f'(median import fraction = {median_imp_frac*100:.1f}%)',
            fontsize=11)
        ax.set_xlabel('Female syph prevalence, mean 2020–2025')
        ax.set_ylabel('Count of NROY draws (n=50)')
        ax.legend(fontsize=8, loc='upper right')
        ax.spines[['top', 'right']].set_visible(False)

    fig.suptitle('Per-rate bifurcation: every non-zero import rate forces 100% of draws onto the hot branch',
                 fontsize=13)
    sc.figlayout()
    fig.savefig(FIGURES / 'bifurcation_by_rate.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "bifurcation_by_rate.png"}')


def plot_policy_summary():
    """One figure showing the two-criterion tradeoff: median syph_late
    vs median import_fraction, across rates. The 1% data line and the
    5% policy ceiling overlaid."""
    df = load()
    agg = df.groupby('import_rate').agg(
        median_syph_late=('syph_prev_f_2020_2025', 'median'),
        q25_syph_late=('syph_prev_f_2020_2025', lambda x: x.quantile(0.25)),
        q75_syph_late=('syph_prev_f_2020_2025', lambda x: x.quantile(0.75)),
        median_import_frac=('import_fraction', 'median'),
        pct_extinct=('syph_prev_f_2020_2025', lambda x: (x <= 0.001).mean() * 100),
        pct_near_data=('syph_prev_f_2020_2025', lambda x: ((x > 0.005) & (x < 0.03)).mean() * 100),
        pct_hot=('syph_prev_f_2020_2025', lambda x: (x > 0.05).mean() * 100),
    ).reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    ax.plot(agg['import_rate'], agg['median_syph_late'] * 100, 'o-',
            color='steelblue', markersize=7, label='Median late-window syph prev')
    ax.fill_between(agg['import_rate'],
                    agg['q25_syph_late'] * 100,
                    agg['q75_syph_late'] * 100,
                    color='steelblue', alpha=0.2, label='IQR')
    ax.axhline(DATA * 100, color='C3', linestyle='--', linewidth=1.5, label='Data (1.0%)')
    ax.set_xlabel('Imports per month per 10k')
    ax.set_ylabel('Female syph prev, mean 2020–2025 (%)')
    ax.set_title('Hot branch hardens monotonically with import rate')
    ax.legend(fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)

    ax = axes[1]
    width = 0.25
    x = np.arange(len(agg))
    ax.bar(x - width, agg['pct_extinct'], width, color='darkred',
           alpha=0.8, label='% extinct')
    ax.bar(x,         agg['pct_near_data'], width, color='C2',
           alpha=0.8, label='% near data (0.5–3%)')
    ax.bar(x + width, agg['pct_hot'], width, color='steelblue',
           alpha=0.8, label='% on hot branch (>5%)')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{r}\n({f*100:.1f}% imp)'
                        for r, f in zip(agg['import_rate'], agg['median_import_frac'])],
                       fontsize=9)
    ax.set_xlabel('Imports per month (median import fraction)')
    ax.set_ylabel('% of 50 NROY draws')
    ax.set_title('Draws by regime: imports collapse the bifurcation into the hot mode')
    ax.legend(fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'policy_summary.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "policy_summary.png"}')


if __name__ == '__main__':
    plot_bifurcation_grid()
    plot_policy_summary()
