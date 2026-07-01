"""Validation-run inspection figure.

5 cells (SOC + POC + POC+CS + POC+PN + POC+BP) x 5 draws x K=5 seeds.
Reads results/scenarios_smoke_timeseries.parquet and
results/scenarios_smoke.kavg.csv. Writes figures/fig_validation_overview.png.

Layout (5 rows x 5 cols, ~14 in x 14 in):
  Row 1  prevalence TS by year (per disease, lines per cell)
  Row 2  new-infections TS by year (per disease, lines per cell)
  Row 3  cumulative new infections 2027-40 by cell (bars per disease)
  Row 4  cumulative successful treatments 2027-40 by cell (bars per disease)
  Row 5  cumulative unnecessary treatments 2027-40 by cell (bars per disease)
Plus a PN cascade panel (bars) below.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl

REPO = Path(__file__).resolve().parent.parent
TS = REPO / 'results' / 'scenarios_smoke_timeseries.parquet'
KAVG = REPO / 'results' / 'scenarios_smoke.kavg.csv'
FIG_DIR = REPO / 'figures'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

DISEASES = ['ng', 'ct', 'tv', 'syph']
DNAME = {'ng': 'Gonorrhoea', 'ct': 'Chlamydia', 'tv': 'Trichomoniasis',
         'syph': 'Syphilis'}
CELL_ORDER = [
    ('SOC', 'SOC', '#444444'),
    ('POC_c-baseline_p-baseline_b-none', 'POC', '#1f77b4'),
    ('POC_c-high_p-baseline_b-none', 'POC+CS', '#2ca02c'),
    ('POC_c-baseline_p-high_b-none', 'POC+PN', '#d62728'),
    ('POC_c-baseline_p-baseline_b-high', 'POC+BP', '#9467bd'),
]


def set_font(size=9):
    if Path(FONT).exists():
        sc.fonts(add=FONT)
        sc.options(font='Libertinus Sans', fontsize=size)
    else:
        sc.options(fontsize=size)


def _ts_panel(ax, ts, disease, result_name, scale=1.0, ylabel=None):
    s = ts[(ts.disease == disease) & (ts.result_name == result_name)]
    for cell, label, color in CELL_ORDER:
        sub = s[s.cell == cell]
        g = sub.groupby('year').value
        med = g.median() / scale
        lo, hi = g.quantile(0.25) / scale, g.quantile(0.75) / scale
        yr = med.index.values
        ax.fill_between(yr, lo.values, hi.values, color=color, alpha=0.10, lw=0)
        ax.plot(yr, med.values, color=color, lw=1.2, label=label)
    ax.axvline(2027, color='#999', ls=':', lw=0.8)
    ax.set_xlim(2010, 2040); ax.set_ylim(bottom=0)
    ax.tick_params(labelsize=7)
    ax.spines[['top', 'right']].set_visible(False)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8.5)


def _bar_panel(ax, kavg, col, scale=1.0, ylabel=None):
    if col not in kavg.columns:
        ax.set_visible(False); return
    x = np.arange(len(CELL_ORDER))
    med, lo, hi = [], [], []
    for cell, _, _ in CELL_ORDER:
        v = kavg.loc[kavg.cell == cell, col] / scale
        med.append(v.median()); lo.append(v.quantile(0.25)); hi.append(v.quantile(0.75))
    med, lo, hi = np.array(med), np.array(lo), np.array(hi)
    yerr = np.vstack([med - lo, hi - med])
    colors = [c for _, _, c in CELL_ORDER]
    ax.bar(x, med, color=colors, alpha=0.85)
    ax.errorbar(x, med, yerr=yerr, fmt='none', ecolor='#444',
                elinewidth=0.7, capsize=2, zorder=4)
    ax.set_xticks(x)
    ax.set_xticklabels([lab for _, lab, _ in CELL_ORDER], fontsize=6.5,
                       rotation=30, ha='right')
    ax.set_ylim(bottom=0)
    ax.tick_params(axis='y', labelsize=7)
    ax.spines[['top', 'right']].set_visible(False)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=8.5)


def main():
    set_font(9)
    ts = pd.read_parquet(TS)
    kavg = pd.read_csv(KAVG)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    ndis = len(DISEASES)  # 4 (ng/ct/tv/syph; hiv excluded)
    fig, axes = pl.subplots(6, ndis, figsize=(11.5, 16),
                            gridspec_kw=dict(height_ratios=[1, 1, 1, 1, 1, 0.9]))

    # Row 1: prevalence TS
    for ax, d in zip(axes[0], DISEASES):
        _ts_panel(ax, ts, d, 'prevalence', scale=0.01,  # store as %
                  ylabel='prevalence (%)' if d == 'ng' else None)
        ax.set_title(DNAME[d], fontsize=10, pad=3)
    axes[0, ndis - 1].legend(fontsize=6.3, frameon=False, loc='upper right')

    # Row 2: new infections TS (thousands/yr)
    for ax, d in zip(axes[1], DISEASES):
        _ts_panel(ax, ts, d, 'new_infections', scale=1e3,
                  ylabel='new inf (thousands/yr)' if d == 'ng' else None)

    # Row 3: cumulative new infections 2027-40 (millions)
    for ax, d in zip(axes[2], DISEASES):
        _bar_panel(ax, kavg, f'{d}_new_inf', scale=1e6,
                   ylabel='cumul. new inf 2027-40\n(millions)' if d == 'ng' else None)

    # Row 4: cumulative successful treatments 2027-40 (millions)
    for ax, d in zip(axes[3], DISEASES):
        _bar_panel(ax, kavg, f'{d}_new_treated_success', scale=1e6,
                   ylabel='successful tx 2027-40\n(millions)' if d == 'ng' else None)

    # Row 5: cumulative unnecessary treatments 2027-40 (millions)
    for ax, d in zip(axes[4], DISEASES):
        _bar_panel(ax, kavg, f'{d}_new_treated_unnecessary', scale=1e6,
                   ylabel='unnecessary tx 2027-40\n(millions)' if d == 'ng' else None)

    # Row 6: PN cascade — only the first 4 panels; hide the 5th
    pn_panels = [
        ('pn_new_index_total',     'PN triggers'),
        ('pn_new_notified',        'Partners notified'),
        ('pn_new_attending',       'Partners attending'),
        ('pn_new_attended_no_sti', 'False alarms\n(attended, no STI)'),
    ]
    for ax, (col, title) in zip(axes[5], pn_panels):
        _bar_panel(ax, kavg, col, scale=1e6,
                   ylabel='2027-40 (millions)' if col == pn_panels[0][0] else None)
        ax.set_title(title, fontsize=9, pad=3)

    fig.text(0.5, 0.008,
             'Validation run: 5 cells x 5 draws (exp 06 top 5) x K=5 seeds, 10k agents. '
             'Lines/bars = median across draws after K=5 seed averaging; band/whiskers = 25-75 IQR. '
             'With n=5, IQR endpoints are exactly the 2nd and 4th sorted values, so a skewed '
             'ensemble (e.g. one cold draw) can leave the median visibly off-centre within the IQR. '
             'Dotted vertical = intervention start (2027). HIV not shown (paired seeds make it '
             'identical across cells).',
             ha='center', fontsize=6.4, color='#666')
    fig.subplots_adjust(left=0.07, right=0.99, top=0.97, bottom=0.045,
                        wspace=0.32, hspace=0.45)
    out = FIG_DIR / 'archive' / 'fig_validation_overview.png'; out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    print(f'wrote {out}')


if __name__ == '__main__':
    main()