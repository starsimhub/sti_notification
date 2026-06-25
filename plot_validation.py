"""Validation-run inspection figure.

5 cells (SOC + POC + POC+CS + POC+PN + POC+BP) x 5 draws x K=5 seeds.
Two-row 5-column panel:
  Top    new-infections TS by year, one line per cell, model median across 5 draws
  Bottom cumulative new infections 2027-2040 by cell (median + min-max range)

Reads results/scenarios_smoke_timeseries.parquet (K=5 averaged) and
results/scenarios_smoke.kavg.csv. Run from repo root.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl

REPO = Path(__file__).resolve().parent
TS = REPO / 'results' / 'scenarios_smoke_timeseries.parquet'
KAVG = REPO / 'results' / 'scenarios_smoke.kavg.csv'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

DISEASES = ['ng', 'ct', 'tv', 'syph', 'hiv']
DNAME = {'ng': 'Gonorrhoea', 'ct': 'Chlamydia', 'tv': 'Trichomoniasis',
         'syph': 'Syphilis', 'hiv': 'HIV'}
CELL_ORDER = [
    ('SOC', 'SOC', '#444444', '-'),
    ('POC_c-baseline_p-baseline_b-none', 'POC', '#1f77b4', '-'),
    ('POC_c-high_p-baseline_b-none', 'POC+CS', '#2ca02c', '-'),
    ('POC_c-baseline_p-high_b-none', 'POC+PN', '#d62728', '-'),
    ('POC_c-baseline_p-baseline_b-high', 'POC+BP', '#9467bd', '-'),
]


def set_font(size=9):
    if Path(FONT).exists():
        sc.fonts(add=FONT)
        sc.options(font='Libertinus Sans', fontsize=size)
    else:
        sc.options(fontsize=size)


def main():
    set_font(9)
    ts = pd.read_parquet(TS)
    kavg = pd.read_csv(KAVG)

    fig, axes = pl.subplots(2, 5, figsize=(13, 5.5))

    # --- Top row: new-infections TS (median + min-max across 5 draws) ---
    for ax, d in zip(axes[0], DISEASES):
        s = ts[(ts.disease == d) & (ts.result_name == 'new_infections')]
        for cell, label, color, ls in CELL_ORDER:
            sub = s[s.cell == cell]
            g = sub.groupby('year').value
            med = g.median() / 1e3
            lo, hi = g.min() / 1e3, g.max() / 1e3
            yr = med.index.values
            ax.fill_between(yr, lo.values, hi.values, color=color, alpha=0.10, lw=0)
            ax.plot(yr, med.values, color=color, lw=1.2, ls=ls, label=label)
        ax.axvline(2027, color='#999', ls=':', lw=0.8)  # intervention year
        ax.set_title(DNAME[d], fontsize=10, pad=3)
        ax.set_xlim(2010, 2040); ax.set_ylim(bottom=0)
        ax.tick_params(labelsize=7)
        ax.spines[['top', 'right']].set_visible(False)
        if d == 'ng':
            ax.set_ylabel('new infections (thousands/yr)', fontsize=8.5)
    axes[0, 4].legend(fontsize=6.5, frameon=False, loc='upper right')

    # --- Bottom row: cumulative new-infections 2027-2040, by cell ---
    x = np.arange(len(CELL_ORDER))
    for ax, d in zip(axes[1], DISEASES):
        col = f'{d}_new_inf'
        if col not in kavg.columns:
            ax.set_visible(False); continue
        med, lo, hi = [], [], []
        for cell, _, _, _ in CELL_ORDER:
            vals = kavg.loc[kavg.cell == cell, col] / 1e6  # millions
            med.append(vals.median())
            lo.append(vals.min())
            hi.append(vals.max())
        med, lo, hi = np.array(med), np.array(lo), np.array(hi)
        yerr = np.vstack([med - lo, hi - med])
        colors = [c for _, _, c, _ in CELL_ORDER]
        ax.bar(x, med, color=colors, alpha=0.85)
        ax.errorbar(x, med, yerr=yerr, fmt='none', ecolor='#444', elinewidth=0.8,
                    capsize=2, zorder=4)
        ax.set_xticks(x)
        ax.set_xticklabels([l for _, l, _, _ in CELL_ORDER], fontsize=7, rotation=30, ha='right')
        ax.set_ylim(bottom=0)
        ax.tick_params(axis='y', labelsize=7)
        ax.spines[['top', 'right']].set_visible(False)
        if d == 'ng':
            ax.set_ylabel('cumulative new inf 2027-40 (millions)', fontsize=8.5)

    fig.text(0.5, 0.012,
             'Validation run: 5 cells x 5 draws (exp 06 top 5) x K=5 seeds. '
             'Top: annual new infections, line = K=5-then-cross-draw median, band = cross-draw min-max. '
             'Dotted vertical = intervention start (2027). '
             'Bottom: cumulative new infections 2027-40 (median + min-max across 5 draws).',
             ha='center', fontsize=6.8, color='#666')
    fig.subplots_adjust(left=0.06, right=0.995, top=0.94, bottom=0.16, wspace=0.32, hspace=0.45)
    out = REPO / 'results' / 'fig_validation_overview.png'
    fig.savefig(out, dpi=200)
    print(f'wrote {out}')


if __name__ == '__main__':
    main()