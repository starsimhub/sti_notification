"""Coverage + invisible-reservoir diagnostic for exp 16."""

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

TARGETS = {
    'hiv_prev_2000_2010':     (0.116, 'HIV prev 2000-10'),
    'hiv_prev_2010_2020':     (0.092, 'HIV prev 2010-20'),
    'ng_prev_2005_2015':      (0.020, 'NG prev 2005-15'),
    'ct_prev_f2530':          (0.120, 'CT F25-30 (2010)'),
    'tv_prev_2005_2015':      (0.111, 'TV prev 2005-15'),
    'syph_detectable_f_2016': (0.010, 'Syph detect F 2016 *'),
    'syph_detectable_m_2016': (0.006, 'Syph detect M 2016 *'),
    'syph_seroprev_f_2016':   (0.030, 'Syph sero F 2016'),
    'syph_seroprev_m_2016':   (0.024, 'Syph sero M 2016'),
    'syph_anc_2000_2015':     (0.020, 'Syph ANC 2000-15'),
    'syph_prev_hivpos_2016':  (0.029, 'Syph|HIV+ 2016 †'),
    'syph_prev_hivneg_2016':  (0.004, 'Syph|HIV- 2016 †'),
}


def load():
    rows = []
    with (OUTPUTS / 'results.jsonl').open() as f:
        for l in f:
            rows.append(json.loads(l))
    df = pd.DataFrame(rows)
    return df[df['status'] == 'ok'].copy()


def plot_coverage_grid():
    df = load()
    fig, axes = plt.subplots(3, 4, figsize=(16, 9))
    axes = axes.ravel()
    for ax, (col, (data, label)) in zip(axes, TARGETS.items()):
        vals = df[col].dropna().values
        if len(vals) == 0:
            ax.set_title(f'{label}\n(no values)', fontsize=9)
            continue
        ax.hist(vals, bins=30, color='steelblue', alpha=0.75)
        ax.axvline(data, color='C3', linestyle='--', linewidth=1.5, label=f'Data {data:.3f}')
        # Loose bracket band
        ax.axvspan(0.5 * data, 2 * data, color='C2', alpha=0.15, label='0.5x–2x data')
        n_bracket = ((vals >= 0.5 * data) & (vals <= 2 * data)).sum()
        ax.set_title(f'{label}\n{n_bracket}/{len(vals)} in band',
                     fontsize=10)
        ax.set_xlabel('Value')
        ax.set_ylabel('Count')
        ax.legend(fontsize=7, loc='upper right')
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Exp 16 coverage — 100 prior draws, patched stisim\n'
                 '* = new detectable-prevalence mapping  † = still uses syph.infected (caveat)',
                 fontsize=12)
    sc.figlayout()
    fig.savefig(FIGURES / 'coverage.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "coverage.png"}')


def plot_invisible_reservoir():
    df = load()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Scatter: prevalence_f vs detectable_f. Hot-branch draws should sit
    # high on prevalence_f but low on detectable_f.
    ax = axes[0]
    ax.scatter(df['prevalence_f_2016'], df['syph_detectable_f_2016'],
               c='steelblue', alpha=0.55, s=20)
    lim = max(df['prevalence_f_2016'].max(), df['syph_detectable_f_2016'].max(), 0.01) * 1.05
    ax.plot([0, lim], [0, lim], 'k:', linewidth=0.8, label='y=x (no reservoir)')
    ax.axhline(0.010, color='C3', linestyle='--', linewidth=1, label='Data detectable F (1.0%)')
    ax.axhspan(0.005, 0.03, color='C2', alpha=0.15, label='0.5–3% bracket band')
    ax.set_xlabel('prevalence_f 2016 (all infected stages)')
    ax.set_ylabel('detectable_prevalence_f 2016')
    ax.set_xlim(0, lim); ax.set_ylim(0, lim)
    ax.set_title('Invisible reservoir: prevalence vs detectable\n'
                 'Distance from y=x = late-latent that ZIMPHIA misses')
    ax.legend(fontsize=8, loc='lower right')
    ax.spines[['top', 'right']].set_visible(False)

    # Histogram of the invisible reservoir size across draws
    ax = axes[1]
    ax.hist(df['invisible_reservoir_f_2016'].dropna(), bins=30,
            color='darkred', alpha=0.7)
    ax.axvline(df['invisible_reservoir_f_2016'].median(),
               color='black', linestyle='--', linewidth=1.5,
               label=f'Median {df["invisible_reservoir_f_2016"].median():.3f}')
    ax.set_xlabel('prevalence_f − detectable_prevalence_f at 2016')
    ax.set_ylabel('Count of draws')
    ax.set_title('Invisible-to-survey late-latent reservoir size')
    ax.legend(fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)

    sc.figlayout()
    fig.savefig(FIGURES / 'invisible_reservoir.png', dpi=120, bbox_inches='tight')
    print(f'Saved {FIGURES / "invisible_reservoir.png"}')


if __name__ == '__main__':
    plot_coverage_grid()
    plot_invisible_reservoir()
