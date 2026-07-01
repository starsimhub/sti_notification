"""Slide 12: all metrics across all 11 layered scenarios, per disease.

3 main rows x 4 disease columns:
  Row 1: prevalence (2040)
  Row 2: incidence (cum 2027-40, millions)
  Row 3: over-treatment + under-treatment (grouped pairs per scenario)
Plus a bottom aggregate strip for over-notification (which has no per-disease
breakdown in current instrumentation).

Scenarios (in order, following the Slide 9->10->11 layering):
  1. SOC
  2. POC alone
  3-5. + PN low/mod/high
  6-8. + PN mod + BP low/mod/high
  9-11. + PN mod + BP mod + CS low/mod/high

  conda run -n starsim python plot_slide12.py
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

REPO = Path(__file__).resolve().parent
KAVG = REPO / 'results' / 'scenarios.kavg.csv'
FIGS = REPO / 'figures'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

DISEASES = [('ng', 'Gonorrhoea'), ('ct', 'Chlamydia'),
            ('tv', 'Trichomoniasis'), ('syph', 'Syphilis')]
YEARS = 2040 - 2027

# 11 scenarios in layering order.
SCENARIOS = [
    ('SOC',       'SOC'),
    ('POC',       'POC_c-baseline_p-baseline_b-none'),
    ('+PN L',     'POC_c-baseline_p-low_b-none'),
    ('+PN M',     'POC_c-baseline_p-moderate_b-none'),
    ('+PN H',     'POC_c-baseline_p-high_b-none'),
    ('+BP L',     'POC_c-baseline_p-moderate_b-low'),
    ('+BP M',     'POC_c-baseline_p-moderate_b-moderate'),
    ('+BP H',     'POC_c-baseline_p-moderate_b-high'),
    ('+CS L',     'POC_c-low_p-moderate_b-moderate'),
    ('+CS M',     'POC_c-moderate_p-moderate_b-moderate'),
    ('+CS H',     'POC_c-high_p-moderate_b-moderate'),
]
# Layer colours: SOC gray outside, then a light-to-dark gradient across layers.
# Grouped so viewers can see PN-only / +BP / +CS families visually.
SCENARIO_C = {
    'SOC':   '#666666',
    'POC':   '#fed9a6',
    '+PN L': '#fdd0a2', '+PN M': '#fdae6b', '+PN H': '#e6772d',
    '+BP L': '#dc7d3f', '+BP M': '#c15c1e', '+BP H': '#a63603',
    '+CS L': '#8c2d04', '+CS M': '#6a1d02', '+CS H': '#450d00',
}

# Colours for over-tx vs under-tx bars within a scenario group
OVER_C_A = 0.85    # alpha for the "over-tx" bar (saturated arm colour)
OVER_C_B = 0.35    # alpha for the "under-tx" bar (paler arm colour)


def med(k, cell, col):
    return float(np.median(k.loc[k.cell == cell, col]))


def draw_metric_row(fig, gs_row, k, metric_fn, ylabel, value_fmt='{:.3f}',
                    is_pct=False, ymax_pad=1.15):
    """One row of 4 disease subplots, each with 11 scenario bars."""
    labels = [s[0] for s in SCENARIOS]
    colors = [SCENARIO_C[l] for l in labels]
    x = np.arange(len(SCENARIOS))
    for c, (d, dname) in enumerate(DISEASES):
        ax = fig.add_subplot(gs_row[c])
        vals = np.array([metric_fn(k, s[1], d) for s in SCENARIOS])
        ax.bar(x, vals, color=colors, width=0.75, zorder=3,
               edgecolor='white', linewidth=0.4)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7.5, rotation=60, ha='right')
        ax.tick_params(axis='y', labelsize=8)
        ax.set_ylim(0, max(vals.max() * ymax_pad, 1e-6))
        ax.spines[['top', 'right']].set_visible(False)
        if c == 0:
            ax.set_ylabel(ylabel, fontsize=10)
        # bar-tops disease-name only on first row (row title supplied by
        # calling code via ax.set_title)


def draw_over_under_row(fig, gs_row, k):
    """Row 3: paired over-treatment (saturated) + under-treatment (light)
    bars per scenario, in each disease subplot."""
    labels = [s[0] for s in SCENARIOS]
    x = np.arange(len(SCENARIOS))
    bar_w = 0.36
    for c, (d, dname) in enumerate(DISEASES):
        ax = fig.add_subplot(gs_row[c])
        over_vals = np.array([
            med(k, s[1], f'{d}_new_treated_unnecessary') / 1e6 / YEARS
            for s in SCENARIOS])
        under_vals = np.array([
            (med(k, s[1], f'{d}_new_inf')
             - med(k, s[1], f'{d}_new_treated_success')) / 1e6 / YEARS
            for s in SCENARIOS])
        for i, l in enumerate(labels):
            cc = SCENARIO_C[l]
            ax.bar(x[i] - bar_w / 2, over_vals[i], width=bar_w, color=cc,
                   alpha=OVER_C_A, zorder=3, edgecolor='white', linewidth=0.4)
            ax.bar(x[i] + bar_w / 2, under_vals[i], width=bar_w, color=cc,
                   alpha=OVER_C_B, zorder=3, edgecolor='white', linewidth=0.4)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7.5, rotation=60, ha='right')
        ax.tick_params(axis='y', labelsize=8)
        ymax = max(over_vals.max(), under_vals.max())
        ax.set_ylim(0, max(ymax * 1.15, 1e-6))
        ax.spines[['top', 'right']].set_visible(False)
        if c == 0:
            ax.set_ylabel('events / yr (M)', fontsize=10)


def draw_over_notif_strip(fig, gs, k):
    """Aggregate over-notification rate (no per-disease breakdown available).
    Index-side false-alarm: fraction of female-index PN triggers with no STI."""
    ax = fig.add_subplot(gs)
    labels = [s[0] for s in SCENARIOS]
    colors = [SCENARIO_C[l] for l in labels]
    vals = np.array([
        100 * med(k, s[1], 'pn_new_index_no_sti_f')
        / med(k, s[1], 'pn_new_index_total_f')
        for s in SCENARIOS])
    x = np.arange(len(SCENARIOS))
    ax.bar(x, vals, color=colors, width=0.75, zorder=3,
           edgecolor='white', linewidth=0.4)
    for i, v in enumerate(vals):
        ax.text(x[i], v + 0.7, f'{v:.0f}%', ha='center', va='bottom',
                fontsize=8, color=SCENARIO_C[labels[i]])
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylim(0, max(vals) * 1.20)
    ax.set_ylabel('over-notification\n(index no-STI rate, %)', fontsize=10)
    ax.tick_params(axis='y', labelsize=8)
    ax.spines[['top', 'right']].set_visible(False)
    ax.set_title('Aggregate over-notification (no per-disease breakdown '
                 'available; index-side false-alarm rate)',
                 fontsize=10.5, pad=6)


def main():
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=11)
    k = pd.read_csv(KAVG)

    fig = pl.figure(figsize=(15, 11.5))
    outer = GridSpec(4, 1, figure=fig, height_ratios=[3, 3, 3, 1.4],
                     left=0.055, right=0.99, top=0.88, bottom=0.06,
                     hspace=0.75)

    row_specs = [outer[r].subgridspec(1, 4, wspace=0.30) for r in range(3)]

    # Row 1: prevalence
    draw_metric_row(fig, row_specs[0], k,
                    metric_fn=lambda k, cell, d: med(k, cell, f'{d}_prev_end'),
                    ylabel='prevalence (2040)')
    # Disease names on row 1
    for c, (d, dname) in enumerate(DISEASES):
        ax = fig.axes[c]
        ax.set_title(dname, fontsize=12.5, pad=8)

    # Row 2: incidence
    draw_metric_row(fig, row_specs[1], k,
                    metric_fn=lambda k, cell, d: (
                        med(k, cell, f'{d}_new_inf') / 1e6 / YEARS),
                    ylabel='new inf / yr (M)')

    # Row 3: over-tx + under-tx grouped
    draw_over_under_row(fig, row_specs[2], k)

    # Row 4: aggregate over-notification strip
    draw_over_notif_strip(fig, outer[3], k)

    fig.suptitle('All metrics across the 11 layered scenarios',
                 fontsize=14, y=0.960)
    fig.text(0.5, 0.930,
             'Rows 1-3 are per-disease (prev / incidence / over-tx + under-tx). '
             'Bottom strip: aggregate over-notification (PN false-alarm rate).',
             ha='center', fontsize=9.5, color='#666', style='italic')
    # Global legend for over-tx vs under-tx (row 3)
    fig.legend(handles=[
        mpatches.Patch(facecolor='#666', alpha=OVER_C_A, label='over-treatment'),
        mpatches.Patch(facecolor='#666', alpha=OVER_C_B, label='under-treatment'),
    ], fontsize=9, frameon=False, loc='upper right',
        bbox_to_anchor=(0.99, 0.955),
        handlelength=1.2, handletextpad=0.4, ncol=2)

    FIGS.mkdir(exist_ok=True)
    p = FIGS / 'fig_slide12.png'
    fig.savefig(p, dpi=200)
    print('wrote', p)


if __name__ == '__main__':
    main()
